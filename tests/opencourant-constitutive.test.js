'use strict';
// OpenCourant constitutive cards shared by blast (2D/3D) and damage & deformation:
// RHT (/MAT/USER01 user library), CDPM2 (LAW124), Drucker–Prager cap (LAW81), and
// the explicit quasi-static deformation path.
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const Cards=require('../blast3d-cards');
const Settings=require('../deformation-settings');
const OC=require('../opencourant-deformation-runner');
const B3=require('../blast3d-runner');
const solid3d=require('../solid3d');

const native=B3.available().opencourant;
const rhtLibrary=fs.existsSync(B3.USER_LIBRARIES.rht);
const base={id:3,name:'concrete',rho:2314,E:33e9,nu:0.2};

// Structured rectangle of TRI3 elements; bottom on rollers, uniform pressure on top.
function rectangle({nx=6,ny=12,W=0.1,H=0.2,p=1e6,E=33e9,nu=0.2}={}){
  const nodes=[],elements=[],id=(i,j)=>j*(nx+1)+i+1;
  for(let j=0;j<=ny;j++)for(let i=0;i<=nx;i++)nodes.push({nodeNo:id(i,j),x:W*i/nx,y:H*j/ny,forceX:0,
    forceY:j===ny?-p*W/nx*((i===0||i===nx)?.5:1):0,fixUx:j===0&&i===0,fixUy:j===0});
  let k=0;
  for(let j=0;j<ny;j++)for(let i=0;i<nx;i++){
    elements.push({elementNo:++k,node1:id(i,j),node2:id(i+1,j),node3:id(i+1,j+1),materialNo:1,elasticModulus:E,poissonRatio:nu});
    elements.push({elementNo:++k,node1:id(i,j),node2:id(i+1,j+1),node3:id(i,j+1),materialNo:1,elasticModulus:E,poissonRatio:nu});
  }
  return {modelName:'rectangle',nodes,elements,materials:[{materialNo:1,id:'c',name:'concrete',density:2400,elasticModulus:E,poissonRatio:nu}]};
}
const ocSettings=(model,extra={})=>({solver:'opencourant',planeMode:1,increments:4,loadFactor:1,materials:{c:{model:'opencourant',oc:{model}}},...extra});

test('RHT writes the 38-constant USER01 card of the OpenCourant user material',()=>{
  const m=Cards.materialLines({model:'rht'},base);
  assert.equal(m.lines[0],'/MAT/USER01/3');
  const constants=m.lines.slice(3).join(' ').trim().split(/\s+/).map(Number);
  assert.equal(constants.length,38);
  assert.equal(constants[0],base.rho);assert.equal(Number(m.lines[2]),base.rho);
  assert.equal(constants[1],Cards.DEFAULTS.rht.G);assert.equal(constants[9],Cards.DEFAULTS.rht.fc);assert.equal(constants[37],Cards.DEFAULTS.rht.alpha0);
  for(const line of m.lines)assert.ok(line.length<=100,line);
  assert.equal(m.userLibrary,'rht');assert.equal(m.damage,'usr3');
  assert.ok(Math.abs(m.K-Cards.DEFAULTS.rht.A1/Cards.DEFAULTS.rht.alpha0)<1);
  assert.deepEqual(Cards.damageAnimations([m]),['/ANIM/ELEM/USER3']);
  // Tensile-cutoff admissibility of rht_validate: the README's rejected and accepted sets.
  assert.throws(()=>Cards.validate({model:'rht',Q0:0.8,B:0.01,fsRatio:0.13,ftRatio:0.1}),/拉伸截断/);
  assert.doesNotThrow(()=>Cards.validate({model:'rht',Q0:0.8,B:0,fsRatio:0.13,ftRatio:0.1}));
  assert.throws(()=>Cards.validate({model:'rht',N:1.2}),/N ≤ 1/);
});

test('CDPM2 and the Drucker–Prager cap map their inputs to LAW124 and LAW81',()=>{
  const c=Cards.materialLines({model:'cdpm2',ft:3e6,gf:150},base);
  assert.equal(c.lines[0],'/MAT/CDPM2/3');assert.equal(c.damage,'damg');
  const wf=Number(c.lines.at(-1).slice(0,20));
  assert.ok(Math.abs(wf-150/(0.225*3e6))<1e-12,'bilinear softening: Gf = 0.225 ft wf');
  const flags=c.lines[5];assert.equal(Number(flags.slice(50,60)),1);assert.equal(Number(flags.slice(70,80)),2);
  // phi = 30 deg, c = 1 MPa: tan(beta) = 6 sin(phi)/(3 - sin(phi)) = 1.2, c_q = 6 c cos(phi)/(3 - sin(phi)).
  const cone=Cards.capCone(Cards.validate({model:'dpcap',cohesion:1e6,friction:30,dilation:0}));
  assert.ok(Math.abs(Math.tan(cone.beta*Math.PI/180)-1.2)<1e-12);
  assert.ok(Math.abs(cone.cq-6e6*Math.cos(Math.PI/6)/2.5)<1e-6);assert.equal(cone.psi,0);
  const d=Cards.materialLines({model:'dpcap',capPressure:100e6,capHardening:2000e6},base);
  assert.equal(d.lines[0],'/MAT/LAW81/3');
  const fct=d.lines.indexOf('/FUNCT/800003');assert.ok(fct>0);
  assert.deepEqual(d.lines[fct+5].match(/.{20}/g).map(Number),[1,21]);
  assert.equal(Cards.materialLines({model:'dpcap',capHardening:0},base).functions.length,0);
  assert.throws(()=>Cards.validate({model:'cdpm2',ft:50e6}),/ft < fc/);
  assert.throws(()=>Cards.validate({model:'dpcap',dilation:50}),/ψ ≤ φ/);
});

test('deformation cards carry an OpenCourant law and the quasi-static run removes rate effects',()=>{
  const card=Settings.normalizeMaterial({model:'opencourant',oc:{model:'rht'}});
  assert.equal(card.oc.model,'rht');
  assert.throws(()=>Settings.normalizeMaterial({model:'opencourant',oc:{model:'rht',N:3}}),/RHT/);
  assert.throws(()=>Settings.normalize({solver:'opencourant',quasiStaticFactor:1}),/准静态/);
  const q=OC.quasiStaticCard(card.oc);assert.equal(q.betaC,0);assert.equal(q.betaT,0);
  assert.equal(OC.quasiStaticCard(Cards.normalize({model:'cdpm2'})).rate,0);
  assert.equal(OC.quasiStaticCard(Cards.normalize({model:'jh2'})).C,0);
});

test('the 2D quasi-static deck is a plane-strain slab with a load ramp and adaptive dynamic relaxation',()=>{
  const model=rectangle();
  const d=OC.buildDecks(model,ocSettings('cdpm2'));
  assert.match(d.starter,/\/MAT\/CDPM2\/1/);assert.match(d.starter,/\/BRICK\/1/);
  assert.match(d.starter,/\n        24/,'HEPH brick (Isolid 24)');
  assert.match(d.engine,/\/ADYREL\n0 /);assert.match(d.engine,/\/ANIM\/ELEM\/DAMG/);
  assert.match(d.starter,/\/CLOAD\//);assert.doesNotMatch(d.starter,/\/IMPDISP\//);
  assert.equal(d.geometry.elements.length,3*model.elements.length);
  // Every slab node is fixed out of plane.
  for(const code of d.starter.matchAll(/^   (\d)(\d)(\d) 000/gm))assert.equal(code[3],'1');
  assert.ok(d.rampTime>0&&Math.abs(d.rampTime-100*d.modelSize/d.waveSpeed)<1e-12);
  const disp=OC.buildDecks(model,ocSettings('rht',{fractureLoading:'displacement',fractureDisplacement:2e-4}));
  assert.match(disp.starter,/\/IMPDISP\//);assert.doesNotMatch(disp.starter,/\/CLOAD\//);
  assert.match(disp.engine,/\/ANIM\/ELEM\/USER3/);
  assert.ok(disp.warnings.some(w=>/应变率增强/.test(w)));
  assert.throws(()=>OC.buildDecks(model,ocSettings('cdpm2',{planeMode:0})),/平面应变/);
  assert.throws(()=>OC.buildDecks(model,{...ocSettings('cdpm2'),materials:{c:{model:'plastic'}}}),/OpenCourant 本构卡/);
  assert.throws(()=>OC.buildDecks({...model,materials:[{...model.materials[0],density:0}]},ocSettings('cdpm2')),/密度/);
});

test('OpenCourant quasi-static 3D elasticity reproduces the uniaxial analytical solution',{skip:!native&&'OpenCourant runtime is not installed'},async()=>{
  const mesh=await solid3d.meshSolid({meshSize:0.025,shapes:[{type:'box',featureId:'b',dx:0.1,dy:0.1,dz:0.2,x:0,y:0,z:0,operation:'add'}]});
  const all=f=>f.triangles.flat().map(n=>mesh.nodes[n]),ids=pred=>mesh.surfaces.filter(f=>all(f).every(pred)).map(f=>f.id);
  const model=solid3d.deformationModelFromSolid(mesh,{materials:[{id:'c',name:'concrete',density:2400,elasticModulus:33,poissonRatio:0.2}],
    volumeMaterials:Object.fromEntries(mesh.volumes.map(v=>[v.id,'c'])),
    conditions:[{type:'fixed',surface:ids(p=>Math.abs(p[2])<1e-9)[0],axes:[false,false,true]},{type:'pressure',surface:ids(p=>Math.abs(p[2]-0.2)<1e-9)[0],pressure:1e6}]});
  const bottom=model.nodes.filter(n=>Math.abs(n.z)<1e-9);bottom[0].fixUx=bottom[0].fixUy=true;bottom[1].fixUy=true;
  const threads=Math.min(2,require('node:os').availableParallelism());
  const r=await OC.runOpenCourantDeformation(model,{solver:'opencourant',threads,increments:4,loadFactor:1,materials:{c:{model:'opencourant',oc:{model:'elastic'}}}});
  assert.equal(r.completed,true);assert.equal(r.frames.length,5);assert.equal(r.cpuThreads,threads);
  const f=r.frames.at(-1),top=model.nodes.filter(n=>Math.abs(n.z-0.2)<1e-9);
  const uz=top.reduce((a,n)=>a+f.displacement[n.nodeNo][2],0)/top.length,expected=-1e6*0.2/33e9;
  assert.ok(Math.abs(uz/expected-1)<0.01,`uz ${uz} vs ${expected}`);
  assert.ok(r.meta.energyRatio<0.01,`kinetic/internal energy ${r.meta.energyRatio}`);
});

test('displacement-controlled 2D CDPM2 and RHT runs evolve bounded damage',{skip:!(native&&rhtLibrary)&&'OpenCourant runtime or RHT library missing'},async()=>{
  for(const law of ['cdpm2','rht']){
    const r=await OC.runOpenCourantDeformation(rectangle({nx:4,ny:8}),ocSettings(law,{fractureLoading:'displacement',fractureDisplacement:6e-4}));
    assert.equal(r.completed,true,law);assert.equal(r.damageEvolution,true);
    const damage=r.frames.map(f=>Math.max(...Object.values(f.elementFields).map(e=>e.damage)));
    assert.equal(damage[0],0);
    assert.ok(damage.at(-1)>0.1&&damage.at(-1)<=1,`${law} damage ${damage.at(-1)}`);
    for(let k=1;k<damage.length;k++)assert.ok(damage[k]>=damage[k-1]-1e-6,`${law} damage does not heal`);
  }
});

test('3D blast loads the RHT user library and reports its damage variable',{skip:!(native&&rhtLibrary)&&'OpenCourant runtime or RHT library missing'},async()=>{
  const mesh=await solid3d.meshSolid({meshSize:0.12,shapes:[
    {type:'box',featureId:'b',dx:2,dy:2,dz:1,x:-1,y:-1,z:0,operation:'add'},
    {type:'cylinder',featureId:'h',radius:0.05,height:0.6,x:0,y:0,z:0.4,operation:'cut'}]});
  const all=f=>f.triangles.flat().map(n=>mesh.nodes[n]),ids=pred=>mesh.surfaces.filter(f=>all(f).every(pred)).map(f=>f.id);
  const material={id:'c',name:'concrete',density:2314,elasticModulus:35,poissonRatio:0.2};
  const summary=await B3.runBlast3d({solid:{mesh,settings:{materials:[material],volumeMaterials:Object.fromEntries(mesh.volumes.map(v=>[v.id,'c'])),
    conditions:[{type:'fixed',surface:ids(p=>Math.abs(p[2])<1e-9)[0],axes:[false,false,true]}]}},
    settings:{sourceMode:'pressure',wallSurfaces:ids(([x,y])=>Math.hypot(x,y)<0.051),peakPressure:3e8,pulseDuration:1e-4,endTime:2e-4,frames:3,initialState:'none',threads:4,
      rockCards:{c:Cards.normalize({model:'rht'})}}});
  assert.equal(summary.completed,true);
  assert.ok(summary.fields.includes('damage')&&summary.fields.includes('plasticStrain'));
  const last=summary.frames.at(-1).stats;
  assert.ok(last.damage[1]>0.5&&last.damage[1]<=1+1e-6,`RHT damage ${last.damage[1]}`);
  assert.equal(summary.meta.materials[0].userLibrary,'rht');
});

test('2D blast slabs use a linked library card (DP cap) instead of the legacy 2D card',{skip:!native&&'OpenCourant runtime is not installed'},async()=>{
  const {runOpenCourantBlast,removeRun}=require('../blast-runner');
  const {blastRing}=require('./helpers/blast-ring');
  const model=blastRing({sectors:24,rings:6});
  for(const m of [...model.materials,...model.elements]){m.elasticModulus=35e9;m.poissonRatio=.2;m.density=2314;}
  for(const m of model.materials)m.blastCard=Cards.normalize({model:'dpcap'});
  const h=await runOpenCourantBlast(model,{x:0,y:0,radius:.1,chargeRadius:.1,pressure:300e6,pulse:1e-4,duration:2e-4,frames:3,planeMode:1,boundary:2,rockModel:1,sourceMode:0},{lazy:true});
  try{
    assert.equal(h.completed,true);
    assert.deepEqual(h.materials.map(m=>[m.law,m.card,m.source]),[['dpcap','/MAT/LAW81/1','library']]);
  }finally{await removeRun(h.id);}
});
