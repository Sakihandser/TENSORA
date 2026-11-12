'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {deck,runDeformation,parseFrd,parseStaProgress,convergedStaRows,diagnoseDeformationStop}=require('../deformation-runner');
const {normalize}=require('../deformation-settings');
const {meshSolid,deformationModelFromSolid}=require('../solid3d');
function model(stress=2e6){return {modelName:'uniaxial patch',nodes:[{nodeNo:1,x:0,y:0,fixUx:true,fixUy:true},{nodeNo:2,x:1,y:0,fixUy:true,forceX:stress/2},{nodeNo:3,x:1,y:1,forceX:stress/2},{nodeNo:4,x:0,y:1,fixUx:true}],elements:[{elementNo:1,node1:1,node2:2,node3:3,elasticModulus:200e9,poissonRatio:.3},{elementNo:2,node1:1,node2:3,node3:4,elasticModulus:200e9,poissonRatio:.3}]};}
const near=(a,b,tol=1e-4)=>assert.ok(Math.abs(a-b)<=tol*Math.max(Math.abs(b),1e-12),`${a} != ${b}`);
async function uniaxialSolid(stress){
 const mesh=await meshSolid({shapes:[{type:'box',dx:1,dy:1,dz:1}],meshSize:.6});
 const face=(axis,value)=>mesh.surfaces.find(surface=>surface.triangles.every(triangle=>triangle.every(id=>mesh.nodes[id][axis]===value))).id;
 const material={id:'sample',elasticModulus:200,poissonRatio:.3};
 return deformationModelFromSolid(mesh,{materials:[material],volumeMaterials:{[mesh.volumes[0].id]:material.id},conditions:[
   ...[0,1,2].map(axis=>({type:'fixed',surface:face(axis,0),axes:[0,1,2].map(i=>i===axis)})),
   {type:'traction',surface:face(0,1),fx:stress,fy:0,fz:0}
 ]});
}
test('settings reject invalid constitutive and increment combinations',()=>{for(const s of [{planeMode:2},{model:'blast'},{increments:0},{hardening:-1},{model:'neoHooke',finiteStrain:false}])assert.throws(()=>normalize(s));});
test('adapter preserves equivalent loads, rejects malformed models, isolates blast settings',()=>{
 const m=model();m.elementNodeLoads=[{elementNo:1,forceX2:1e6}];m.blastSettings={pressure:1e99};const {input}=deck(m,{});assert.match(input,/2,1,1000000/);assert.doesNotMatch(input,/2,1,2000000/);assert.doesNotMatch(input,/1e\+99/);
 m.nodes[1].nodeNo=1;assert.throws(()=>deck(m,{}));
});
test('restraints must span all planar rigid modes on every connected solid',()=>{
 const m=model();
 for(const n of m.nodes){n.fixUx=n.y===0;n.fixUy=n.x===0;}
 assert.throws(()=>deck(m,{}),/Rz/);
 m.nodes[1].fixUy=true;
 assert.doesNotThrow(()=>deck(m,{}));
 m.nodes.push(...m.nodes.map(n=>({...n,nodeNo:n.nodeNo+4,x:n.x+2,fixUx:false,fixUy:false})));
 m.elements.push(...m.elements.map(e=>({...e,elementNo:e.elementNo+2,node1:e.node1+4,node2:e.node2+4,node3:e.node3+4})));
 assert.throws(()=>deck(m,{}),/节点 5.*X、Y/);
});
test('a large cutback budget is accepted and only affects saved-frame frequency',()=>{
 const m=model(),count=600;
 // Add connected elastic patches with independent supports for deck validation.
 const nodes=m.nodes,elements=m.elements;
 m.nodes=[];m.elements=[];
 for(let i=0;i<count;i++){
   m.nodes.push(...nodes.map(n=>({...n,nodeNo:n.nodeNo+4*i,x:n.x+2*i})));
   m.elements.push(...elements.map(e=>({...e,elementNo:e.elementNo+2*i,node1:e.node1+4*i,node2:e.node2+4*i,node3:e.node3+4*i})));
 }
 const output=deck(m,{increments:40,maxIncrements:10000});
 assert.match(output.input,/\*STEP,INC=10000/);
 assert.match(output.input,/\*STATIC\n0\.025,1,1e-8,0\.025/);
 assert.ok(output.outputFrequency>1);
 assert.ok(m.nodes.length*(Math.floor(10000/output.outputFrequency)+1)<=1_500_000);
});
test('real CalculiX analytic elasticity, plane strain, J2 yielding, finite deformation',async()=>{
 const elastic=await runDeformation(model(),{model:'elastic',finiteStrain:false,increments:4});const a=elastic.frames.at(-1);near(a.displacement[2][0],1e-5);near(a.displacement[3][1],-3e-6);near(a.stress[1][0],2e6);
 const strain=await runDeformation(model(),{model:'elastic',finiteStrain:false,planeMode:1,increments:4});near(strain.frames.at(-1).displacement[2][0],.91e-5);near(strain.frames.at(-1).stress[1][2],.3*2e6);
 const plastic=await runDeformation(model(300e6),{finiteStrain:false,increments:3});const p=plastic.frames.at(-1);near(p.displacement[2][0],.0515);near(p.plasticStrain[1][0],.05);assert.equal(plastic.settings.model,'plastic');assert.equal(plastic.frames.length,3);
 const finite=await runDeformation(model(300e6),{finiteStrain:true,increments:20});assert.ok(finite.frames.at(-1).displacement[2][0]>.0515);assert.ok(finite.frames.at(-1).plasticStrain[1][0]>.05);
});
test('real CalculiX solves a 3D tetrahedral model using the assigned shared J2 card',async()=>{
 const mesh=await meshSolid({shapes:[{type:'box',dx:1,dy:.2,dz:.2}],meshSize:.2});
 const face=x=>mesh.surfaces.find(surface=>surface.triangles.every(triangle=>triangle.every(id=>mesh.nodes[id][0]===x))).id;
 const material={id:'steel',elasticModulus:200,poissonRatio:.3};
 const solid=deformationModelFromSolid(mesh,{materials:[material],volumeMaterials:{[mesh.volumes[0].id]:material.id},
   conditions:[{type:'fixed',surface:face(0)},{type:'force',surface:face(1),fx:200000,fy:0,fz:0}]});
 const settings={finiteStrain:true,increments:3,maxIncrements:20,materials:{steel:{model:'plastic',yieldStress:2e6,hardening:1e9,criticalPlasticStrain:.001}}};
 assert.match(deck(solid,settings).input,/\*ELEMENT,TYPE=C3D4/);
 const run=await runDeformation(solid,settings);
 assert.equal(run.completed,true);
 const {deformationFrame3d,initiationThresholds}=await import('../src/pages/solid3d-deformation.js');
 const plotted=deformationFrame3d(run,run.frames.length-1,initiationThresholds(run));
 assert.ok(plotted.maxDisplacement>.001);
 assert.ok(plotted.nodeFields.peeq.some(value=>value>.001));
 assert.ok(plotted.nodeFields.damageInitiation.some(value=>value>1));
 assert.ok(plotted.nodeFields.szz.every(Number.isFinite));
});
test('CalculiX hyperelastic cards preserve SI values in plane stress, plane strain and 3D',async()=>{
 const {normalizeLibraryCard}=require('../deformation-settings');
 const axialStress=1000;
 const solid=await uniaxialSolid(axialStress);
 const tensileNode=solid.nodes.find(node=>node.x===1&&node.y===1&&node.z===1).nodeNo;
 for(const {card} of [
   normalizeLibraryCard({id:'neo',name:'Neo-Hooke',card:{model:'neoHooke',c10:500000,d1:2e-7}}),
   normalizeLibraryCard({id:'mr',name:'Mooney–Rivlin',card:{model:'mooneyRivlin',c10:300000,c01:200000,d1:2e-7}})
 ]){
   const settings={...card,increments:2,maxIncrements:10};
   const plane=model(axialStress),input=deck(plane,settings).input;
   const keyword=card.model==='neoHooke'?'NEO HOOKE':'MOONEY-RIVLIN';
   const row=card.model==='neoHooke'?'500000,2e-7':'300000,200000,2e-7';
   assert.ok(input.includes(`*HYPERELASTIC,${keyword}\n${row}\n`));
   assert.throws(()=>deck(plane,{...settings,finiteStrain:false}),/超弹性/);
   // Small-strain limit: shear modulus 1 MPa and bulk modulus 10 MPa.
   const E=9*10e6*1e6/(3*10e6+1e6),nu=(3*10e6-2*1e6)/(2*(3*10e6+1e6));
   const ps=(await runDeformation(plane,settings)).frames.at(-1);
   near(ps.displacement[2][0],axialStress/E,.005);
   near(ps.displacement[3][1],-nu*axialStress/E,.005);
   const pe=(await runDeformation(plane,{...settings,planeMode:1})).frames.at(-1);
   near(pe.displacement[2][0],(1-nu**2)*axialStress/E,.005);
   const spatial=await runDeformation(solid,{...settings,materials:{sample:card}});
   assert.equal(spatial.completed,true);
   const end=spatial.frames.at(-1);
   near(end.displacement[tensileNode][0],axialStress/E,.005);
   near(end.displacement[tensileNode][2],-nu*axialStress/E,.005);
 }
 assert.throws(()=>normalize({model:'neoHooke',d1:0}),/超弹性/);
 assert.throws(()=>normalize({model:'mooneyRivlin',c01:-1}),/超弹性/);
});
test('native J2 multilinear hardening reads stress in Pa and strain as a fraction',async()=>{
 const hardeningCurve=[[250e6,0],[275e6,.02],[325e6,.04]],settings={hardeningCurve,finiteStrain:false,increments:6};
 assert.throws(()=>normalize({...settings,hardeningCurve:[[250e6,0],[275e6,0]]}),/应变递增/);
 const {normalizeLibraryCard}=require('../deformation-settings');
 const {card}=normalizeLibraryCard({id:'curve',name:'Measured hardening',card:{model:'plastic',hardeningCurve}});
 assert.deepEqual(card.hardeningCurve,hardeningCurve);
 const plane=model(300e6);
 assert.match(deck(plane,settings).input,/\*PLASTIC\n250000000,0\n275000000,0\.02\n325000000,0\.04/);
 const run=await runDeformation(plane,settings);
 assert.equal(run.completed,true);
 near(run.frames.at(-1).plasticStrain[2][0],.03);
 near(run.frames.at(-1).displacement[2][0],.0315);
 const solid=await uniaxialSolid(300e6);
 const node=solid.nodes.find(node=>node.x===1&&node.y===1&&node.z===1).nodeNo;
 const spatial=await runDeformation(solid,{...settings,materials:{sample:card}});
 assert.equal(spatial.completed,true);
 near(spatial.frames.at(-1).plasticStrain[node][0],.03);
 near(spatial.frames.at(-1).displacement[node][0],.0315);
});
test('native Code_Aster returns 3D Mazars damage and the degraded tensile stress',
 {skip:process.env.TENSORA_TEST_ASTER!=='1'},async()=>{
 const {runMazars}=require('../aster-deformation-runner');
 const model={dimension:3,materials:[{materialNo:1,id:'concrete'}],nodes:[
   {nodeNo:1,x:0,y:0,z:0,fixUx:true,fixUy:true,fixUz:true,forceX:0,forceY:0,forceZ:0},
   {nodeNo:2,x:1,y:0,z:0,fixUy:true,fixUz:true,forceX:1,forceY:0,forceZ:0},
   {nodeNo:3,x:0,y:1,z:0,fixUx:true,fixUz:true,forceX:0,forceY:0,forceZ:0},
   {nodeNo:4,x:0,y:0,z:1,fixUx:true,fixUy:true,forceX:0,forceY:0,forceZ:0}
 ],elements:[{elementNo:1,node1:1,node2:2,node3:3,node4:4,materialNo:1,elasticModulus:3e10,poissonRatio:.2}]};
 const settings={solver:'aster',finiteStrain:false,fractureLoading:'displacement',fractureDisplacement:.0004,increments:4,
   materials:{concrete:{model:'mazars'}}};
 const result=await runMazars(model,settings);
 const first=result.frames[0],last=result.frames.at(-1);
 assert.equal(result.damageEvolution,true);
 assert.ok(Math.abs(first.damage[2][0])<1e-12);
 assert.ok(last.damage[2][0]>.9&&last.damage[2][0]<1);
 near(last.displacement[2][0],.0004);
 near(last.strain[2][0],.0004);
 near(last.stress[2][0],(1-last.damage[2][0])*3e10*.0004);
 assert.ok(last.stress[2][0]<first.stress[2][0]);
});
test('bundled OOFEM transfers 3D displacement, stress and crack-band damage in SI',async()=>{
 const {runCrackBand}=require('../oofem-fracture-runner');
 const card={model:'crackBand',tensileStrength:3e6,crackBandEnergy:500};
 const settings={solver:'oofem',finiteStrain:false,increments:4};
 const elastic=await uniaxialSolid(1000);
 const force=await runCrackBand(elastic,{...settings,materials:{sample:card}});
 const tip=elastic.nodes.find(node=>node.x===1&&node.y===1&&node.z===1).nodeNo;
 near(force.frames.at(-1).stress[tip][0],1000);
 near(force.frames.at(-1).displacement[tip][0],1000/200e9);
 assert.equal(force.frames.at(-1).damage[tip][0],0);
 const model={dimension:3,materials:[{materialNo:1,id:'sample'}],nodes:[
   {nodeNo:1,x:0,y:0,z:0,fixUx:true,fixUy:true,fixUz:true,forceX:0,forceY:0,forceZ:0},
   {nodeNo:2,x:.1,y:0,z:0,fixUy:true,fixUz:true,forceX:1,forceY:0,forceZ:0},
   {nodeNo:3,x:0,y:.1,z:0,fixUx:true,fixUz:true,forceX:0,forceY:0,forceZ:0},
   {nodeNo:4,x:0,y:0,z:.1,fixUx:true,fixUy:true,forceX:0,forceY:0,forceZ:0}
 ],elements:[{elementNo:1,node1:1,node2:2,node3:3,node4:4,materialNo:1,elasticModulus:3e10,poissonRatio:.2}]};
 const fractured=await runCrackBand(model,{...settings,increments:24,materials:{sample:card},fractureLoading:'displacement',fractureDisplacement:.00004});
 const last=fractured.frames.at(-1);
 assert.equal(fractured.damageEvolution,true);
 assert.equal(fractured.frames.length,24);
 assert.ok(last.damage[2][0]>.7&&last.damage[2][0]<1);
 near(last.displacement[2][0],.00004);
 near(last.stress[2][0],(1-last.damage[2][0])*3e10*.0004);
 assert.ok(last.stress[2][0]<fractured.frames[5].stress[2][0]);
});
test('incomplete output never becomes a completed result',()=>{assert.throws(()=>parseFrd('',model()),/未完成/);});
test('budget exhaustion and nonconvergence are distinct; rejected iterates are never accepted as history',()=>{
 assert.equal(diagnoseDeformationStop('*ERROR in nonlingeo: max. # of increments reached',201).code,'increment-limit');
 assert.equal(diagnoseDeformationStop('*ERROR: increment size smaller than minimum',201).code,'nonconvergence');assert.equal(diagnoseDeformationStop('Job finished',0),null);
 const sta='1 1 1 3 0.25 0.25 0.25\n1 2 1 3 0.5 0.5 0.25\n1 3 1U 6 0.5 0.5 0.1\n';assert.equal(convergedStaRows(sta).length,2);
 const m=model();const block=t=>['  100CL  101'+t.toExponential(5).padStart(12),...['DISP','STRESS','TOSTRAIN','PE'].flatMap(key=>[' -4  '+key,...m.nodes.map(n=>' -1'+String(n.nodeNo).padStart(10)+(key==='PE'?[.1]:key==='DISP'?[t,0,0]:[t,t,0,0,0,0]).map(v=>v.toExponential(5).padStart(12)).join(''))])].join('\n');
 const text=[block(.25),block(.5),block(.6)].join('\n');assert.throws(()=>parseFrd(text,m),/未完成/);
 const frames=parseFrd(text,m,{allowPartial:true,convergedTimes:convergedStaRows(sta).map(r=>r.fraction),hasPlastic:true});assert.equal(frames.length,2);assert.equal(frames.at(-1).time,.5);assert.equal(frames.at(-1).displacement[1][0],.5);
 const sampled=block(.123456).replace(/^(  100C[^\n]+)/m,'$1           4                     0    1           1')+'\n'+
   block(1).replace(/^(  100C[^\n]+)/m,'$1           4                     0    2           1');
 assert.deepEqual(parseFrd(sampled,m,{hasPlastic:true,convergedTimes:[.05,.1,.1234564,.6,1]}).map(f=>f.time),[.1234564,1]);
});
test('equal elastic properties do not merge distinct plastic cards or elastic materials',async()=>{
 const base=model(300e6),multi={modelName:'three materials',nodes:[],elements:[],materials:[]};
 for(let i=0;i<3;i++){
   multi.materials.push({materialNo:i+1,id:['A','B','C'][i]});
   multi.nodes.push(...base.nodes.map(n=>({...n,nodeNo:n.nodeNo+4*i,x:n.x+2*i})));
   multi.elements.push(...base.elements.map(e=>({...e,elementNo:e.elementNo+2*i,node1:e.node1+4*i,node2:e.node2+4*i,node3:e.node3+4*i,materialNo:i+1})));
 }
 const settings={finiteStrain:false,increments:10,materials:{A:{model:'plastic',yieldStress:250e6,hardening:1e9,criticalPlasticStrain:.1},B:{model:'plastic',yieldStress:200e6,hardening:4e9,criticalPlasticStrain:.25},C:{model:'elastic'}}};
 const input=deck(multi,settings).input;assert.equal((input.match(/\*MATERIAL,NAME=/g)||[]).length,3);assert.equal((input.match(/\*PLASTIC/g)||[]).length,2);
 const result=await runDeformation(multi,settings),f=result.frames.at(-1);near(f.displacement[2][0],.0515);near(f.displacement[6][0],.0265);near(f.displacement[10][0],.0015);near(f.plasticStrain[1][0],.05);near(f.plasticStrain[5][0],.025);near(f.plasticStrain[9][0],0);
 assert.equal(result.materialSettings[1].criticalPlasticStrain,.1);assert.equal(result.materialSettings[2].criticalPlasticStrain,.25);
 const missing=structuredClone(settings);delete missing.materials.B;assert.throws(()=>deck(multi,missing),/缺少材料/);
});
test('already cancelled request never starts solver',async()=>{const c=new AbortController();c.abort();await assert.rejects(runDeformation(model(),{},{signal:c.signal}),/取消/);});
test('progress counts converged load only, ignoring failed attempts and partial rows',()=>{
 const source='SUMMARY OF JOB INFORMATION\n STEP INC ATT ITRS TOT TIME STEP TIME INC TIME\n'+
 '1 1 1 2 0.1E+00 0.1E+00 0.1E+00\n1 2 1U 10 0.5E+00 0.5E+00 0.4E+00\n1 2 2 3 0.2D+00 0.2D+00 0.1D+00\n1 3 1';
 assert.deepEqual(parseStaProgress(source),{fraction:.2,completedIncrements:2});assert.equal(parseStaProgress('header only'),null);
});
test('real solver emits live converged progress and completes after result processing',async()=>{
 const updates=[];await runDeformation(model(),{finiteStrain:true,increments:1000,maxIncrements:1000},{onProgress:p=>updates.push(p)});
 const live=updates.filter(p=>p.phase==='solving'&&p.fraction>0&&p.fraction<1);assert.ok(live.length>0,'no live STA progress received');
 assert.ok(live.some(p=>p.completedIncrements>=2&&p.estimatedRemainingMs>0));
 assert.equal(updates[0].phase,'preparing');assert.equal(updates.at(-2).phase,'processing');assert.equal(updates.at(-1).phase,'complete');assert.equal(updates.at(-1).fraction,1);
 for(let i=1;i<updates.length;i++)assert.ok(updates[i].fraction>=updates[i-1].fraction);
});
module.exports={model};
