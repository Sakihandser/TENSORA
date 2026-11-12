'use strict';
// 3D blast workspace: OpenCourant decks, MFEM initial equilibrium and result frames.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const test=require('node:test');
const solid3d=require('../solid3d');
const {buildDecks,normalizeSettings,pulseFunction}=require('../blast3d-deck');
const blast3d=require('../blast3d-runner');

const JH2={law:3,jh2:{A:0.76,N:0.61,B:0.55,M:0.61,C:0.005,rate0:1,HEL:4.5e9,pHEL:2.9e9,T:20e6,D1:0.005,D2:0.7,maxStrength:0.5,
  K1:25e9,K2:-20e9,K3:20e9,beta:1,referenceLength:0,normalizationStress:0,G:0,K:0}};
const rock=(extra={})=>({id:'rock',name:'granite',density:2650,elasticModulus:50,poissonRatio:0.25,...extra});
let meshPromise;
// Block 2 x 2 x 1 m with a 0.05 m borehole from z=0.4 to the top face.
function boreholeMesh(){
  meshPromise??=solid3d.meshSolid({meshSize:0.12,shapes:[
    {type:'box',featureId:'b',dx:2,dy:2,dz:1,x:-1,y:-1,z:0,operation:'add'},
    {type:'cylinder',featureId:'h',radius:0.05,height:0.6,x:0,y:0,z:0.4,operation:'cut'}]});
  return meshPromise;
}
function faces(mesh){
  const all=f=>f.triangles.flat().map(n=>mesh.nodes[n]);
  const ids=pred=>mesh.surfaces.filter(f=>all(f).every(pred)).map(f=>f.id);
  return {hole:ids(([x,y])=>Math.hypot(x,y)<0.051),bottom:ids(p=>Math.abs(p[2])<1e-9),top:ids(p=>Math.abs(p[2]-1)<1e-9),
    sides:mesh.surfaces.filter(f=>all(f).every(([x])=>Math.abs(Math.abs(x)-1)<1e-9)||all(f).every(([,y])=>Math.abs(Math.abs(y)-1)<1e-9)).map(f=>f.id)};
}
function solid(mesh,material,conditions){
  return {mesh,settings:{materials:[material],volumeMaterials:Object.fromEntries(mesh.volumes.map(v=>[v.id,material.id])),conditions}};
}
const native=blast3d.available();
const skipNative=!native.opencourant&&'OpenCourant runtime is not installed';
const readFrame=async(summary,index)=>{
  const buffer=await blast3d.readFrame(summary.runId,index),n=summary.nodeCount;
  const all=new Float32Array(buffer.buffer,buffer.byteOffset,buffer.byteLength/4);
  return Object.fromEntries(summary.fields.map((key,k)=>[key,all.subarray(k*n,(k+1)*n)]));
};

test('settings validation rejects incomplete blast sources',()=>{
  assert.throws(()=>normalizeSettings({sourceMode:'pressure',peakPressure:1e8,pulseDuration:1e-4}),/孔壁/);
  assert.throws(()=>normalizeSettings({sourceMode:'jwl'}),/炸药/);
  assert.throws(()=>normalizeSettings({sourceMode:'pressure',wallSurfaces:['1'],peakPressure:1e8,pulseDuration:1e-4,frames:500}),/保存帧数/);
  assert.throws(()=>normalizeSettings({sourceMode:'pressure',wallSurfaces:['1'],peakPressure:1e8,pulseDuration:1e-4,volumeRoles:{1:'air'}}),/角色/);
  const pulse=pulseFunction({pulseShape:'sine',pulseDuration:1e-4,endTime:1e-3});
  assert.equal(pulse[0][1],0);assert.ok(Math.abs(pulse[32][1]-1)<1e-12);assert.equal(pulse.at(-1)[1],0);
});

test('deck maps materials, borehole pressure, restraints and the absorbing layer to OpenCourant cards',async()=>{
  const mesh=await boreholeMesh(),f=faces(mesh);
  const decks=buildDecks(solid(mesh,rock({blastConstitutive:JH2}),[{type:'fixed',surface:f.bottom[0],axes:[false,false,true]}]),
    {sourceMode:'pressure',wallSurfaces:f.hole,peakPressure:2e8,pulseDuration:1e-4,endTime:6e-4,frames:13,initialState:'none',absorbingSurfaces:f.sides});
  for(const card of ['/BEGIN','/MAT/JOHN_HOLM/1','/PROP/SOLID/1','/TETRA4/1','/SURF/SEG/','/PLOAD/','/BCS/','/DAMP/','/END'])assert.match(decks.starter,new RegExp(card.replace(/\//g,'\\/')));
  assert.match(decks.engine,/\/ANIM\/ELEM\/DAMG/);
  assert.equal(decks.meta.elements,mesh.tets.length);
  assert.equal(decks.meta.source.segments,mesh.surfaces.filter(s=>f.hole.includes(s.id)).reduce((n,s)=>n+s.triangles.length,0));
  assert.ok(decks.meta.absorbingLayer.thickness>0&&decks.meta.absorbingLayer.alphaMax>0);
  // Card rows keep the fixed 10/20-column layout.
  const nodeRow=decks.starter.split('\n')[decks.starter.split('\n').indexOf('#  node_ID                 Xc                  Yc                  Zc')+1];
  assert.equal(nodeRow.length,70);
  assert.throws(()=>buildDecks(solid(mesh,rock({blastConstitutive:{law:6}}),[]),{sourceMode:'pressure',wallSurfaces:f.hole,peakPressure:1e8,pulseDuration:1e-4}),/Mohr/);
});

test('rock material cards validate parameters and convert Drucker–Prager input',()=>{
  const Cards=require('../blast3d-cards');
  assert.deepEqual(Cards.MODELS.map(m=>m.id),['elastic','jh2','hjc','dp','jc']);
  assert.throws(()=>Cards.validate({model:'jc',n:1.2}),/0 < n ≤ 1/);
  assert.throws(()=>Cards.validate({model:'jc',tMelt:200}),/Tm > Tr/);
  assert.equal(Cards.validate({model:'jc'}).a,Cards.DEFAULTS.jc.a);
  assert.throws(()=>Cards.validate({model:'jh2',HEL:1e9,pHEL:2e9}),/HEL > pHEL/);
  assert.throws(()=>Cards.validate({model:'hjc',pl:1e6}),/Pl > Pc/);
  assert.throws(()=>Cards.validate({model:'elastic',failure:{enabled:true,strainStart:1e-3,strainEnd:1e-4}}),/ε₁ < ε₂/);
  assert.throws(()=>Cards.normalizeLibraryCard({id:'x',name:'',card:{}}),/名称/);
  // phi = 30 deg, c = 1 MPa: alpha = 6 sin(phi)/(sqrt(3)(3-sin(phi))), k = 6 c cos(phi)/(sqrt(3)(3-sin(phi))).
  const dp=Cards.druckerPrager(Cards.validate({model:'dp',cohesion:1e6,friction:30,tension:0.5e6}));
  assert.ok(Math.abs(dp.alpha-0.69282)<1e-5&&Math.abs(dp.k-1.2e6)<1);
  assert.ok(Math.abs(dp.A0-dp.k**2)<1e-3&&Math.abs(dp.A1-2*dp.k*dp.alpha)<1e-6&&dp.pMin===-0.5e6);
  assert.equal(Cards.fromBlastConstitutive({law:3,jh2:{A:0.9,N:0.6,B:0.2,M:0.6,C:0.005,rate0:1,HEL:4e9,pHEL:3e9,T:1e7,D1:0.005,D2:0.7,maxStrength:0.3,K1:20e9,K2:0,K3:0,beta:1,G:0}}).model,'jh2');
  assert.equal(Cards.fromBlastConstitutive(null).model,'elastic');
});

test('linked cards select the OpenCourant material law, failure card and result outputs',async()=>{
  const Cards=require('../blast3d-cards');
  const mesh=await boreholeMesh(),f=faces(mesh);
  const base={sourceMode:'pressure',wallSurfaces:f.hole,peakPressure:2e8,pulseDuration:1e-4,endTime:3e-4,frames:4,initialState:'none'};
  const deck=card=>buildDecks(solid(mesh,rock(),[]),{...base,rockCards:{rock:Cards.normalize(card)}});
  const hjc=deck({model:'hjc'}),dp=deck({model:'dp',failure:{enabled:true}}),elastic=deck({model:'elastic'});
  assert.match(hjc.starter,/\/MAT\/JOHNSON_HOLMQUIST_CONCRETE\/1/);assert.match(hjc.engine,/\/ANIM\/ELEM\/DAMG/);
  assert.match(dp.starter,/\/MAT\/DPRAG1\/1[\s\S]*\/FAIL\/TENSSTRAIN\/1/);assert.match(dp.engine,/\/ANIM\/BRICK\/DAMA/);
  for(const d of [hjc,dp,elastic])assert.match(d.engine,/\/ANIM\/BRICK\/TENS\/STRAIN/);
  assert.doesNotMatch(elastic.engine,/DAMG|BRICK\/DAMA/);
  assert.equal(dp.meta.materials[0].card.model,'dp');
  assert.throws(()=>buildDecks(solid(mesh,rock({blastConstitutive:{law:6}}),[]),base),/Drucker/);
  // Johnson-Cook writes the LAW2 radioss2025 layout; the cutoff is a negative Pmin.
  const jc=deck({model:'jc',a:250e6,b:500e6,n:0.3,C:0.02,epsMax:0.2,tension:1.5e9});
  const lines=jc.starter.split('\n'),at=lines.indexOf('/MAT/PLAS_JOHNS/1');
  assert.ok(at>0);
  const fields=row=>row.match(/.{1,20}/g).map(Number);
  assert.deepEqual([fields(lines[at+5].slice(0,40)),Number(lines[at+5].slice(40,50)),Number(lines[at+5].slice(60,80))],[[50e9,0.25],0,-1.5e9]);
  assert.deepEqual(fields(lines[at+7]),[250e6,500e6,0.3,0.2,0]);
  assert.equal(jc.meta.materials[0].law,'jc');assert.equal(jc.meta.materials[0].erodes,true);
  assert.doesNotMatch(jc.engine,/DAMG|BRICK\/DAMA/);
});

test('OpenCourant accepts a Johnson–Cook card and reports plastic strain and eroded elements',{skip:skipNative},async()=>{
  const Cards=require('../blast3d-cards');
  const mesh=await boreholeMesh(),f=faces(mesh);
  const steel={id:'steel',name:'steel',density:7850,elasticModulus:200,poissonRatio:0.29};
  const summary=await blast3d.runBlast3d({solid:solid(mesh,steel,[{type:'fixed',surface:f.bottom[0],axes:[false,false,true]}]),
    settings:{sourceMode:'pressure',wallSurfaces:f.hole,peakPressure:3e9,pulseDuration:5e-5,endTime:1e-4,frames:3,initialState:'none',threads:4,
      rockCards:{steel:Cards.normalize({model:'jc',a:250e6,b:500e6,n:0.3,C:0.02,m:1,tMelt:1800,tRef:293,rhoCp:3.6e6,epsMax:0.05})}}});
  for(const key of ['plasticStrain','eroded','vm'])assert.ok(summary.fields.includes(key),key);
  assert.ok(!summary.fields.includes('damage')&&!summary.fields.includes('failureDamage'));
  const last=summary.frames.at(-1).stats;
  assert.ok(last.plasticStrain[1]>0.01,`peak plastic strain ${last.plasticStrain[1]}`);
  // von Mises stays near the JC flow stress (strain-rate hardening, no damage).
  assert.ok(last.vm[1]<2e9,`peak von Mises ${last.vm[1]}`);
});

test('strain tensor, principal values, failure damage and failed elements reach the result frames',{skip:skipNative},async()=>{
  const Cards=require('../blast3d-cards');
  const mesh=await boreholeMesh(),f=faces(mesh);
  const summary=await blast3d.runBlast3d({solid:solid(mesh,rock(),[{type:'fixed',surface:f.bottom[0],axes:[false,false,true]}]),
    settings:{sourceMode:'pressure',wallSurfaces:f.hole,peakPressure:3e8,pulseDuration:1e-4,endTime:3e-4,frames:4,initialState:'none',threads:4,
      rockCards:{rock:Cards.normalize({model:'dp',failure:{enabled:true}})}}});
  for(const key of ['exx','eyy','ezz','exy','eyz','exz','equivalentStrain','e1','s1','plasticStrain','failureDamage','eroded'])assert.ok(summary.fields.includes(key),key);
  assert.ok(!summary.fields.includes('damage'),'DP has no constitutive damage variable');
  const frame=await readFrame(summary,summary.frames.length-1),last=summary.frames.at(-1).stats;
  assert.ok(last.failureDamage[1]>0&&last.failureDamage[1]<=1+1e-6);
  assert.ok(last.e1[1]>Cards.DEFAULTS.failure.strainStart,'tensile strain exceeds the damage onset near the hole');
  for(let i=0;i<frame.e1.length;i++){
    const ex=frame.exx[i],ey=frame.eyy[i],ez=frame.ezz[i];
    assert.ok(frame.e1[i]>=Math.max(ex,ey,ez)-1e-9,'largest principal strain bounds the normal strains');
    assert.ok(frame.equivalentStrain[i]>=0);
  }
});

test('OpenCourant pushes the borehole wall outward and returns stress, velocity and JH2 damage frames',{skip:skipNative},async()=>{
  const mesh=await boreholeMesh(),f=faces(mesh);
  const summary=await blast3d.runBlast3d({solid:solid(mesh,rock({blastConstitutive:JH2}),[{type:'fixed',surface:f.bottom[0],axes:[false,false,true]}]),
    settings:{sourceMode:'pressure',wallSurfaces:f.hole,peakPressure:2e8,pulseDuration:1e-4,endTime:3e-4,frames:7,initialState:'none',absorbingSurfaces:f.sides,threads:4}});
  assert.equal(summary.completed,true);
  assert.equal(summary.frames.length,7);
  assert.ok(Math.abs(summary.frames.at(-1).time-3e-4)<2e-5);
  for(const key of ['umag','vmag','sxx','vm','pressure','damage','plasticStrain'])assert.ok(summary.fields.includes(key),key);
  const frame=await readFrame(summary,1);
  let outward=0,count=0;
  mesh.nodes.forEach(([x,y,z],i)=>{const r=Math.hypot(x,y);if(Math.abs(r-0.05)<1e-3&&z>0.45&&z<0.95){count++;if(frame.ux[i]*x+frame.uy[i]*y>0)outward++;}});
  assert.ok(count>10&&outward===count,`${outward}/${count} wall nodes move outward at the pressure peak`);
  const last=summary.frames.at(-1).stats;
  assert.ok(last.damage[1]>0.5&&last.damage[1]<=1);
  assert.ok(summary.frames.every(fr=>Object.values(fr.stats).every(([a,b])=>Number.isFinite(a)&&Number.isFinite(b))));
});

test('MFEM initial equilibrium keeps a confined block at rest in OpenCourant',{skip:skipNative||(!native.mfem&&'MFEM driver is not built')},async()=>{
  const mesh=await boreholeMesh(),f=faces(mesh);
  const conditions=[{type:'fixed',surface:f.bottom[0],axes:[true,true,true]},...f.sides.map(id=>({type:'pressure',surface:id,pressure:10e6}))];
  const run=initialState=>blast3d.runBlast3d({solid:solid(mesh,rock(),conditions),
    settings:{sourceMode:'pressure',wallSurfaces:f.hole,peakPressure:1,pulseDuration:1e-4,endTime:2e-4,frames:3,initialState,threads:4}});
  const prestressed=await run('prestress'),sudden=await run('sudden');
  assert.ok(prestressed.prestress.iterations>0);
  const speed=async summary=>{const v=(await readFrame(summary,2)).vmag;return Math.max(...v);};
  const quiet=await speed(prestressed),loud=await speed(sudden);
  assert.ok(quiet<1e-5,`prestressed peak velocity ${quiet}`);
  assert.ok(loud>1e-2,`sudden loading peak velocity ${loud}`);
  // Confinement is carried as total stress, including the EOS pressure part.
  const stress=await readFrame(prestressed,0);
  const centre=mesh.nodes.findIndex(([x,y,z])=>Math.abs(x)>0.3&&Math.abs(x)<0.7&&Math.abs(y)<0.3&&z>0.2&&z<0.4);
  assert.ok(stress.sxx[centre]< -5e6,`sxx ${stress.sxx[centre]}`);
});

test('a coupled JWL charge detonates and loads the surrounding rock',{skip:skipNative},async()=>{
  const mesh=await solid3d.meshSolid({meshSize:0.08,shapes:[
    {type:'box',featureId:'b',dx:1.2,dy:1.2,dz:1,x:-0.6,y:-0.6,z:0,operation:'add'},
    {type:'cylinder',featureId:'c',radius:0.05,height:0.5,x:0,y:0,z:0.5,operation:'add'}]});
  const charge=[...mesh.volumes].sort((a,b)=>a.elements-b.elements)[0].id;
  const library=JSON.parse(fs.readFileSync(path.join(__dirname,'..','explosives','library.json'),'utf8'));
  const summary=await blast3d.runBlast3d({solid:solid(mesh,rock({blastConstitutive:JH2}),[]),
    settings:{sourceMode:'jwl',explosive:library.explosives[0],volumeRoles:{[charge]:'charge'},endTime:1e-4,frames:3,initialState:'none',threads:4}});
  assert.equal(summary.meta.materials.find(m=>m.role==='charge').law,'jwl');
  assert.ok(summary.frames.at(-1).stats.pressure[1]>1e8,'detonation pressure reaches the rock');
});
