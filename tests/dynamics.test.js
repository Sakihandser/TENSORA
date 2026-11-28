'use strict';
// Structural dynamics: settings, deck generation and real CalculiX / OpenCourant runs
// compared with closed-form results (cantilever frequencies, static limit and
// resonance amplitude of the harmonic response, step-load overshoot, impact momentum).
const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const test=require('node:test');
const DS=require('../dynamics-settings');
const {fromPayload}=require('../dynamics-model');
const Calculix=require('../dynamics-calculix');
const Explicit=require('../dynamics-explicit');
const runner=require('../dynamics-runner');
const {solidPayload,planeModel}=require('./helpers/dynamics-models');

const runsDirectory=fs.mkdtempSync(path.join(os.tmpdir(),'tensora-dynamics-tests-'));
test.after(()=>fs.promises.rm(runsDirectory,{recursive:true,force:true,maxRetries:3}));
const run=(payload,options={})=>runner.runDynamics(payload,{...options,runsDirectory});
const probe=(id,nodes)=>runner.readProbe(id,nodes,{runsDirectory});

const STEEL3D={id:'steel',name:'steel',elasticModulus:210,poissonRatio:0.3,density:7850,yieldStrength:235};
const STEEL2D={id:'steel',name:'steel',E:2.1e11,nu:0.3,rho:7850,yieldStrength:235e6};
// Euler–Bernoulli cantilever: f1 = (1.875^2 / 2 pi) sqrt(EI / (rho A)) / L^2, depth 0.1 m, length 1 m.
const F1=(1.875**2/(2*Math.PI))*Math.sqrt(2.1e11*0.1**2/12/7850);
const STATIC=1000/(3*2.1e11*0.1**4/12);       // tip deflection of the 0.1 x 0.1 m beam under 1 kN
const STATIC_PLANE=1000/(3*2.1e11*0.1**3/12); // per unit thickness, plane stress

function cantilever3d(load=0){
  const payload=solidPayload([{n:[20,2,2],size:[1,0.1,0.1]}],STEEL3D);
  const conditions=[];
  payload.mesh.nodes.forEach((p,i)=>{if(p[0]===0)conditions.push({type:'fixedNode',node:i,axes:[true,true,true]});});
  const tip=payload.mesh.nodes.map((p,i)=>Math.abs(p[0]-1)<1e-9?i:-1).filter(i=>i>=0);
  if(load)for(const i of tip)conditions.push({type:'pointForce',node:i,fx:0,fy:0,fz:-load/tip.length});
  payload.settings.conditions=conditions;
  return payload;
}
function cantilever2d(load=0){
  const model=planeModel([{n:[40,4],size:[1,0.1]}],STEEL2D);
  model.nodes.forEach(n=>{if(n.x===0){n.fixUx=true;n.fixUy=true;}});
  const tip=model.nodes.filter(n=>Math.abs(n.x-1)<1e-9);
  if(load)tip.forEach(n=>{n.forceY=-load/tip.length;});
  return model;
}

test('settings normalize every analysis and reject invalid input',()=>{
  assert.equal(DS.normalize({}).analysis,'modal');
  assert.equal(DS.normalize({analysis:'harmonic',freqMin:1,freqMax:100}).freqPoints,20);
  assert.throws(()=>DS.normalize({analysis:'harmonic',freqMin:100,freqMax:10}),/扫频终点/);
  assert.throws(()=>DS.normalize({analysis:'transient',endTime:1,timeStep:1e-7}),/时间步数/);
  const s=DS.normalize({analysis:'explicit',bodies:{1:{velocity:[1,2,3]}},walls:[{point:[0,0,0],normal:[0,0,2]}],cards:{a:{model:'plastic',yieldStress:2e8,tangentModulus:1e9}}});
  assert.deepEqual(s.walls[0].normal,[0,0,1]);
  assert.deepEqual(s.bodies['1'].velocity,[1,2,3]);
  assert.throws(()=>DS.normalize({analysis:'explicit',walls:[{normal:[0,0,0]}]}),/法向/);
  const r=DS.rayleighFromRatio(0.05,10,100);
  for(const f of [10,100])assert.ok(Math.abs(r.alpha/(4*Math.PI*f)+r.beta*Math.PI*f-0.05)<1e-12);
});

test('load histories sample every shape',()=>{
  const half=DS.normalizeLoad({shape:'halfsine',duration:0.01,factor:2});
  assert.ok(Math.abs(DS.loadValue(half,0.005)-2)<1e-12);
  assert.equal(DS.loadValue(half,0),0);
  assert.equal(DS.loadValue(half,0.01),0);
  assert.equal(DS.loadValue(half,0.02),0);
  const pulse=DS.normalizeLoad({shape:'pulse',duration:0.01,rise:0.001});
  assert.equal(DS.loadValue(pulse,0.005),1);
  assert.equal(DS.loadValue(pulse,-0.001),0);
  const tri=DS.normalizeLoad({shape:'pulse',duration:0.01,rise:0.005});
  assert.equal(DS.loadValue(tri,0.005),1);
  assert.throws(()=>DS.normalizeLoad({shape:'pulse',duration:0.01,rise:0.006}),/一半/);
  const samples=DS.loadSamples(DS.normalizeLoad({shape:'sine',frequency:50}),0.1);
  assert.ok(samples.length>100&&samples.every(([t],i)=>i===0||t>samples[i-1][0]));
  const table=DS.normalizeLoad({shape:'table',table:[[0,0],[1,2]]});
  assert.equal(DS.loadValue(table,0.5),1);
});

test('parts are the connected pieces of the mesh, numbered by their first node',()=>{
  const parts=DS.components([[3,4,5],[0,1,2],[1,2,6]],7);
  assert.equal(parts.count,2);
  assert.deepEqual(parts.elementPart,[1,0,0]);
});

test('CalculiX decks: quadratic tetrahedra, wedge extrusion for 2D, steady-state and transient steps',()=>{
  const solid=fromPayload({solid:cantilever3d(1000)});
  const modal=Calculix.deck(solid,DS.normalize({analysis:'modal',modes:4}));
  assert.match(modal.input,/\*ELEMENT,TYPE=C3D10/);
  assert.match(modal.input,/\*FREQUENCY,STORAGE=YES\n4\n/);
  const transient=Calculix.deck(solid,DS.normalize({analysis:'transient',transientMethod:'direct',endTime:0.01,timeStep:0.001,frames:6,rayleighBeta:1e-5,load:{shape:'halfsine',duration:0.005}}));
  assert.match(transient.input,/\*DAMPING,ALPHA=0,BETA=0.00001/);
  assert.match(transient.input,/\*DYNAMIC,DIRECT\n0.001,0.01/);
  assert.match(transient.input,/\*CLOAD,AMPLITUDE=LOADHIST/);
  const superposed=Calculix.deck(solid,DS.normalize({analysis:'transient',transientModes:12,endTime:0.01,timeStep:0.001,frames:6,rayleighBeta:1e-5}));
  assert.match(superposed.input,/\*FREQUENCY,STORAGE=YES\n12\n\*END STEP\n\*STEP,INC=\d+\n\*MODAL DYNAMIC\n0.001,0.01\n\*MODAL DAMPING,RAYLEIGH\n,,0,0.00001/);
  assert.doesNotMatch(superposed.input,/\*DAMPING,ALPHA/);
  const plane=fromPayload({model:cantilever2d(1000)});
  const harmonic=Calculix.deck(plane,DS.normalize({analysis:'harmonic',planeMode:0,freqMin:5,freqMax:100}));
  assert.match(harmonic.input,/\*ELEMENT,TYPE=C3D15/);
  assert.match(harmonic.input,/\*STEADY STATE DYNAMICS\n5,100,20,1/);
  assert.equal(harmonic.meta.plane,'stress');
  assert.throws(()=>Calculix.deck(fromPayload({model:cantilever2d(0)}),DS.normalize({analysis:'harmonic'})),/载荷/);
  const free=fromPayload({solid:solidPayload([{n:[2,2,2],size:[1,1,1]}],STEEL3D)});
  assert.equal(Calculix.rigidModeCount(free),6);
});

test('OpenCourant decks: parts, initial velocities, contact pairs and rigid walls',()=>{
  const payload=solidPayload([{n:[2,2,2],size:[0.1,0.1,0.1]},{n:[2,2,2],size:[0.1,0.1,0.1],origin:[0.12,0,0]}],STEEL3D);
  const m=fromPayload({solid:payload});
  const s=DS.normalize({analysis:'explicit',bodies:{1:{velocity:[5,0,0]}},walls:[{point:[0.3,0,0],normal:[1,0,0],friction:0.2}],
    cards:{steel:{model:'plastic',yieldStress:235e6,tangentModulus:1e9,failureStrain:0.5}}});
  const d=Explicit.buildDecks(m,s);
  assert.equal(d.meta.parts,2);
  assert.equal(d.meta.contacts,2);
  assert.match(d.starter,/\/INIVEL\/TRA\//);
  assert.match(d.starter,/\/RWALL\/PLANE\//);
  assert.match(d.starter,/\/MAT\/PLAS_JOHNS\//);
  assert.match(d.starter,/\/TH\/RWALL\/1/);
  assert.deepEqual(d.meta.walls[0].normal,[-1,0,0]);      // oriented toward the model
  assert.throws(()=>Explicit.buildDecks(m,DS.normalize({analysis:'explicit',walls:[{point:[0.05,0,0],normal:[1,0,0]}]})),/穿过模型/);
  // 2D: plane-strain slab with in-plane initial velocity only.
  const plane=fromPayload({model:planeModel([{n:[2,2],size:[0.1,0.1]}],STEEL2D)});
  const slab=Explicit.buildDecks(plane,DS.normalize({analysis:'explicit',planeMode:1,bodies:{1:{velocity:[1,2,3]}}}));
  assert.match(slab.starter,/\/BRICK\//);
  assert.equal(slab.meta.bodies[0].velocity[2],0);
});

test('modal analysis matches the cantilever frequency (3D quadratic tetrahedra and 2D plane stress)',async()=>{
  const solid=await run({solid:cantilever3d(),settings:{analysis:'modal',modes:4}});
  assert.equal(solid.frames.length,4);
  assert.ok(Math.abs(solid.modes[0].frequency-F1)/F1<0.01,`3D f1 ${solid.modes[0].frequency}`);
  assert.ok(Math.abs(solid.modes[1].frequency-F1)/F1<0.01);
  const plane=await run({model:cantilever2d(),settings:{analysis:'modal',planeMode:0,modes:3}});
  assert.ok(Math.abs(plane.modes[0].frequency-F1)/F1<0.01,`2D f1 ${plane.modes[0].frequency}`);
  // Effective modal masses are per unit thickness (beam mass 785 kg/m).
  assert.ok(plane.modes[0].effectiveMass[1]>0.55*785&&plane.modes[0].effectiveMass[1]<0.65*785);
  assert.ok(plane.geometry.triangles.length===320);
});

test('free–free modal analysis reports six rigid-body modes',async()=>{
  const free=await run({solid:solidPayload([{n:[10,2,2],size:[1,0.1,0.1]}],STEEL3D),settings:{analysis:'modal',modes:2,elementOrder:'linear'}});
  assert.ok(free.modes.filter(m=>m.rigid).length>=5);
  assert.equal(free.modes.filter(m=>!m.rigid).length,2);
  assert.ok(free.modes.every(m=>!m.spurious));
  assert.ok(free.modes.at(-1).frequency>100);
  assert.equal(free.frames.length,free.modes.length);
});

test('rigid modes depend on independent restraint directions in each connected body',()=>{
  const boxes=[{n:[2,2,2],size:[1,1,1]},{n:[2,2,2],size:[1,1,1],origin:[2,0,0]}];
  const solid=fromPayload({solid:solidPayload(boxes,STEEL3D)});
  assert.equal(Calculix.rigidModeCount(solid),12);
  // Every point on the first body's x axis is pinned. Rotation about that axis survives.
  solid.coords.forEach(([x,y,z],i)=>{if(x<=1&&y===0&&z===0)solid.fixed.fill(1,3*i,3*i+3);});
  assert.equal(Calculix.rigidModeCount(solid),7);
  const plane=fromPayload({model:cantilever2d()});
  plane.fixed.fill(0);
  plane.coords.forEach(([x],i)=>{if(x===0)plane.fixed[i*3+1]=1;});
  assert.equal(Calculix.rigidModeCount(plane),2);
  // A soft elastic mode can also fall below the numerical near-zero threshold.
  const dat={eigen:[[1,0,0,0],[2,1e-8,0,1e-4],[3,4e7,0,1000]],participation:[],effective:[]};
  const modes=Calculix.modeTable(dat,1);
  assert.deepEqual(modes.map(m=>m.rigid),[true,false,false]);
  assert.equal(modes[1].period,10000);
});

test('harmonic response: static limit and resonance amplitude 1/(2 zeta)',async()=>{
  const plane=await run({model:cantilever2d(1000),settings:{analysis:'harmonic',planeMode:0,freqMin:2,freqMax:200,freqPoints:10,dampingRatio:0.02,harmonicModes:6}});
  const first=plane.frames[0],peak=plane.frames.reduce((a,f)=>f.stats.umag[1]>a.stats.umag[1]?f:a);
  assert.ok(Math.abs(first.stats.umag[1]-STATIC_PLANE)/STATIC_PLANE<0.03,`static ${first.stats.umag[1]}`);
  assert.ok(Math.abs(peak.value-F1)/F1<0.01);
  assert.ok(Math.abs(peak.stats.umag[1]/(STATIC_PLANE/0.04)-1)<0.1,`peak ${peak.stats.umag[1]}`);
  assert.ok(plane.fields.includes('phy')&&plane.fields.includes('vm'));
});

test('harmonic von Mises peak includes phases between sample angles',()=>{
  const block=values=>({width:6,values});
  const angle=Math.PI/24;
  const peak=(real,imaginary)=>Calculix.harmonicFields(1,block([0,0,0,0,0,0]),block(real),block(imaginary)).vm[0];
  assert.ok(Math.abs(peak([Math.cos(angle),0,0,0,0,0],[Math.sin(angle),0,0,0,0,0])-1)<1e-7);
  // Normal and shear terms in quadrature: VM² = 4 cos²(t) + 3 sin²(t).
  assert.equal(peak([2,0,0,0,0,0],[0,0,0,1,0,0]),2);
  assert.equal(peak([2,2,2,0,0,0],[3,3,3,0,0,0]),0);
  // Non-finite solver output is preserved as NaN rather than silently zeroed.
  assert.ok(Number.isNaN(peak([NaN,0,0,0,0,0],[0,0,0,0,0,0])));
});

test('readProbe positional fast path reads exact values on large binary frames',async()=>{
  const runId='run-probe-large';
  const dir=path.join(runsDirectory,runId);
  fs.mkdirSync(dir,{recursive:true});
  const n=5000,fields=['ux','uy','vm'],frameCount=3;
  const summary={ok:true,runId,analysis:'transient',dimension:2,nodeCount:n,fields,
    frames:Array.from({length:frameCount},(_,k)=>({index:k,value:k*0.01,stats:{}}))};
  fs.writeFileSync(path.join(dir,'summary.json'),JSON.stringify(summary));
  for(let k=0;k<frameCount;k++){
    const arr=new Float32Array(fields.length*n);
    for(let f=0;f<fields.length;f++)for(let i=0;i<n;i++)arr[f*n+i]=k*100+f*10+i*0.001;
    fs.writeFileSync(path.join(dir,`frame-${String(k).padStart(4,'0')}.bin`),Buffer.from(arr.buffer));
  }
  const res=await probe(runId,'0,1234,4999');
  assert.deepEqual(res.nodes,[0,1234,4999]);
  assert.deepEqual(res.axis,[0,0.01,0.02]);
  assert.ok(Math.abs(res.values.vm[2][1]-(200+20+1234*0.001))<1e-3);
  assert.ok(Math.abs(res.values.ux[1][2]-(100+0+4999*0.001))<1e-3);
});

test('large plane-strain decks write every boundary without exceeding the JS argument limit',()=>{
  const model=fromPayload({model:planeModel([{n:[140,100],size:[1,1]}],STEEL2D)});
  const {input,meta}=Calculix.deck(model,DS.normalize({analysis:'modal',planeMode:1}));
  assert.ok(meta.fixedDofs>125000);
  assert.equal(input.split('*BOUNDARY\n')[1].split('*STEP')[0].trimEnd().split('\n').length,meta.fixedDofs);
});

test('both transient methods finish on the specified time for a fractional last increment',async()=>{
  for(const transientMethod of ['direct','modal']){
    const settings={analysis:'transient',transientMethod,transientModes:6,endTime:0.0103,timeStep:0.002,frames:10};
    const result=await run({model:cantilever2d(1000),settings});
    assert.equal(result.completed,true,result.termination?.message);
    const times=result.frames.map(f=>f.value);
    assert.ok(times.every((t,i)=>!i||t>times[i-1]));
    assert.equal(times.at(-1),settings.endTime,transientMethod);
    assert.deepEqual((await probe(result.runId,'0')).axis,times);
  }
});

test('implicit transient: a suddenly applied load overshoots to about twice the static deflection (mode superposition and direct)',async()=>{
  const peaks=[];
  for(const transientMethod of ['modal','direct']){
    const result=await run({solid:cantilever3d(1000),settings:{analysis:'transient',transientMethod,transientModes:20,endTime:0.024,timeStep:0.0004,frames:31,load:{shape:'step'}}});
    assert.equal(result.completed,true);
    const tip=Math.min(...result.frames.map(f=>f.stats.uz[0]));
    assert.ok(tip<-1.8*STATIC&&tip>-2.1*STATIC,`${transientMethod} peak ${tip}`);
    assert.ok(result.fields.includes('vmag'));
    peaks.push(tip);
  }
  assert.ok(Math.abs(peaks[0]/peaks[1]-1)<0.02,`modal ${peaks[0]} direct ${peaks[1]}`);
});

test('explicit impact: equal blocks exchange momentum and a bar loses its kinetic energy on a rigid wall',async()=>{
  const blocks=solidPayload([{n:[3,3,3],size:[0.1,0.1,0.1]},{n:[3,3,3],size:[0.1,0.1,0.1],origin:[0.105,0,0]}],STEEL3D);
  const collision=await run({solid:blocks,settings:{analysis:'explicit',explicitEndTime:0.0004,explicitFrames:9,threads:1,
    bodies:{1:{velocity:[10,0,0]},2:{velocity:[-10,0,0]}}}});
  assert.equal(collision.completed,true,collision.termination?.message);
  const last=blocks.mesh.nodes.length-1;
  const series=await probe(collision.runId,`0,${last}`);
  assert.equal(series.values.vx[0][0],10);
  assert.ok(series.values.vx.at(-1)[0]<0&&series.values.vx.at(-1)[1]>0,'blocks rebound');
  const ke=collision.history.kinetic.y;
  assert.ok(Math.abs(ke[0]-0.5*2*7.85*100)/785<0.01);
  const bar=solidPayload([{n:[6,2,2],size:[0.3,0.06,0.06]}],STEEL3D);
  const wall=await run({solid:bar,settings:{analysis:'explicit',explicitEndTime:0.002,explicitFrames:6,threads:1,bodies:{1:{velocity:[40,0,0]}},
    walls:[{point:[0.31,0,0],normal:[-1,0,0]}],cards:{steel:{model:'plastic',yieldStress:235e6,tangentModulus:1e9}}}});
  assert.ok(wall.history.wall1.y.some(v=>v>0),'wall force recorded');
  assert.ok(wall.history.plastic.y.at(-1)>0.5*wall.history.kinetic.y[0],'plastic work absorbs the impact');
  assert.ok(wall.fields.includes('peeq'));
});

test('2D explicit collision runs on the plane-strain slab',async()=>{
  const model=planeModel([{n:[5,5],size:[0.1,0.1]},{n:[5,5],size:[0.1,0.1],origin:[0.105,0]}],STEEL2D);
  const result=await run({model,settings:{analysis:'explicit',planeMode:1,explicitEndTime:0.0004,explicitFrames:9,threads:1,
    bodies:{1:{velocity:[10,0,0]},2:{velocity:[-10,0,0]}}}});
  assert.equal(result.completed,true,result.termination?.message);
  assert.ok(Math.abs(result.history.kinetic.y[0]-0.5*157*100)/7850<0.01);   // per unit thickness
  assert.ok(!result.fields.includes('uz'));
  await assert.rejects(run({model,settings:{analysis:'explicit',planeMode:0}}),/平面应变/);
});
