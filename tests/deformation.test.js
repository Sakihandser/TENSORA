'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {deck,runDeformation,parseFrd,parseStaProgress,convergedStaRows,diagnoseDeformationStop}=require('../deformation-runner');
const {normalize}=require('../deformation-settings');
function model(stress=2e6){return {modelName:'uniaxial patch',nodes:[{nodeNo:1,x:0,y:0,fixUx:true,fixUy:true},{nodeNo:2,x:1,y:0,fixUy:true,forceX:stress/2},{nodeNo:3,x:1,y:1,forceX:stress/2},{nodeNo:4,x:0,y:1,fixUx:true}],elements:[{elementNo:1,node1:1,node2:2,node3:3,elasticModulus:200e9,poissonRatio:.3},{elementNo:2,node1:1,node2:3,node3:4,elasticModulus:200e9,poissonRatio:.3}]};}
const near=(a,b,tol=1e-4)=>assert.ok(Math.abs(a-b)<=tol*Math.max(Math.abs(b),1e-12),`${a} != ${b}`);
test('settings reject invalid constitutive and increment combinations',()=>{for(const s of [{planeMode:2},{model:'blast'},{increments:0},{hardening:-1},{model:'neoHooke',finiteStrain:false}])assert.throws(()=>normalize(s));});
test('adapter preserves equivalent loads, rejects malformed models, isolates blast settings',()=>{
 const m=model();m.elementNodeLoads=[{elementNo:1,forceX2:1e6}];m.blastSettings={pressure:1e99};const {input}=deck(m,{});assert.match(input,/2,1,1000000/);assert.doesNotMatch(input,/2,1,2000000/);assert.doesNotMatch(input,/1e\+99/);
 m.nodes[1].nodeNo=1;assert.throws(()=>deck(m,{}));
});
test('real CalculiX analytic elasticity, plane strain, J2 yielding, finite deformation',async()=>{
 const elastic=await runDeformation(model(),{model:'elastic',finiteStrain:false,increments:4});const a=elastic.frames.at(-1);near(a.displacement[2][0],1e-5);near(a.displacement[3][1],-3e-6);near(a.stress[1][0],2e6);
 const strain=await runDeformation(model(),{model:'elastic',finiteStrain:false,planeMode:1,increments:4});near(strain.frames.at(-1).displacement[2][0],.91e-5);near(strain.frames.at(-1).stress[1][2],.3*2e6);
 const plastic=await runDeformation(model(300e6),{finiteStrain:false,increments:10});const p=plastic.frames.at(-1);near(p.displacement[2][0],.0515);near(p.plasticStrain[1][0],.05);assert.equal(plastic.settings.model,'plastic');assert.equal(plastic.frames.length,10);
 const finite=await runDeformation(model(300e6),{finiteStrain:true,increments:20});assert.ok(finite.frames.at(-1).displacement[2][0]>.0515);assert.ok(finite.frames.at(-1).plasticStrain[1][0]>.05);
});
test('incomplete output never becomes a completed result',()=>{assert.throws(()=>parseFrd('',model()),/未完成/);});
test('budget exhaustion and nonconvergence are distinct; rejected iterates are never accepted as history',()=>{
 assert.equal(diagnoseDeformationStop('*ERROR in nonlingeo: max. # of increments reached',201).code,'increment-limit');
 assert.equal(diagnoseDeformationStop('*ERROR: increment size smaller than minimum',201).code,'nonconvergence');assert.equal(diagnoseDeformationStop('Job finished',0),null);
 const sta='1 1 1 3 0.25 0.25 0.25\n1 2 1 3 0.5 0.5 0.25\n1 3 1U 6 0.5 0.5 0.1\n';assert.equal(convergedStaRows(sta).length,2);
 const m=model();const block=t=>['  100CL  101'+t.toExponential(5).padStart(12),...['DISP','STRESS','TOSTRAIN','PE'].flatMap(key=>[' -4  '+key,...m.nodes.map(n=>' -1'+String(n.nodeNo).padStart(10)+(key==='PE'?[.1]:key==='DISP'?[t,0,0]:[t,t,0,0,0,0]).map(v=>v.toExponential(5).padStart(12)).join(''))])].join('\n');
 const text=[block(.25),block(.5),block(.6)].join('\n');assert.throws(()=>parseFrd(text,m),/未完成/);
 const frames=parseFrd(text,m,{allowPartial:true,convergedTimes:convergedStaRows(sta).map(r=>r.fraction),hasPlastic:true});assert.equal(frames.length,2);assert.equal(frames.at(-1).time,.5);assert.equal(frames.at(-1).displacement[1][0],.5);
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
