// 2D blast on the bundled OpenCourant (+ MFEM equilibrium) solvers.
const test=require('node:test'),assert=require('node:assert/strict');
const B2=require('../blast2d-opencourant');
const {runOpenCourantBlast,readBlastFrame,removeRun}=require('../blast-runner');
const {blastRing}=require('./helpers/blast-ring');

const solverReady=B2.available().opencourant&&B2.available().mfem;
const jh2={law:3,jh2:{A:.76,N:.62,B:.25,M:.62,C:.005,rate0:1,HEL:4.5e9,pHEL:3.7e9,T:54e6,D1:.005,D2:.7,maxStrength:.25,
  K1:25.7e9,K2:-4500e9,K3:300000e9,beta:0,referenceLength:0,normalizationStress:0,G:21.9e9,K:0}};
const base={x:0,y:0,radius:.1,chargeRadius:.1,pressure:10e6,pulse:1e-4,duration:4e-4,frames:9,planeMode:1,boundary:0,rockModel:1,sourceMode:0,shockViscosity:0};
const radialDisplacement=(model,frame,i)=>{const n=model.nodes[i],r=Math.hypot(n.x,n.y);return (frame.u[2*i]*n.x+frame.u[2*i+1]*n.y)/r;};

test('each TRI3 becomes three positive QUAD4 cells that tile the triangle',()=>{
  const model=blastRing({sectors:24,rings:4});
  const mesh=B2.buildMesh(model,base);
  assert.equal(mesh.quads.length,3*model.elements.length);
  for(let t=0;t<mesh.tris.length;t++){
    const areas=[0,1,2].map(j=>mesh.quadArea[3*t+j]);
    assert.ok(areas.every(a=>a>0));
    assert.ok(Math.abs(areas.reduce((a,b)=>a+b)-mesh.tris[t].area)<1e-12*mesh.tris[t].area+1e-18);
  }
  // Shared edges share their midpoint node: vertices + edges + centroids.
  assert.equal(mesh.PX.length,model.nodes.length+mesh.edges.size+model.elements.length);
});

test('triangle strain from the quad field is exact for linear displacement',()=>{
  const model=blastRing({sectors:16,rings:3}),mesh=B2.buildMesh(model,base);
  const ux=mesh.PX.map((x,i)=>2e-3*x-1e-3*mesh.PY[i]),uy=mesh.PX.map((x,i)=>5e-4*x+3e-3*mesh.PY[i]);
  for(let t=0;t<mesh.tris.length;t++){
    const [exx,eyy,gxy]=B2.triangleStrain(mesh,ux,uy,mesh.tris[t],t);
    assert.ok(Math.abs(exx-2e-3)<1e-12&&Math.abs(eyy-3e-3)<1e-12&&Math.abs(gxy-(-1e-3+5e-4))<1e-12);
  }
});

test('the cavity, outer boundary and edge overrides are classified on the real mesh',()=>{
  const model=blastRing({sectors:24,rings:4}),s=B2.normalizeSettings({...base,boundary:2});
  const mesh=B2.buildMesh(model,s),b=B2.classifyBoundary(mesh,model,s);
  assert.equal(b.wall.length,24);assert.equal(b.outer.length,24);
  assert.ok([...b.modeOf.values()].every(mode=>mode===2));
  assert.throws(()=>B2.classifyBoundary(mesh,model,{...s,radius:.2}),/炮孔/);
  assert.throws(()=>B2.classifyBoundary(mesh,model,{...s,x:.5}),/爆源中心/);
});

test('options without an OpenCourant counterpart are rejected instead of approximated',()=>{
  assert.throws(()=>B2.normalizeSettings({...base,planeMode:0}),/平面应力/);
  assert.throws(()=>B2.normalizeSettings({...base,ventEnds:1}),/轴向/);
  assert.throws(()=>B2.normalizeSettings({...base,gasFracture:1}),/裂隙/);
  assert.throws(()=>B2.normalizeSettings({...base,sourceMode:1,productEOS:3,airEOS:0}),/EOS/);
  assert.throws(()=>B2.normalizeSettings({...base,sourceMode:1,productEOS:1,airEOS:4}),/EOS/);
});

test('settings saved by the removed legacy core load as plane strain with supported EOS only',()=>{
  const Settings=require('../blast-settings');
  const old={...base,planeMode:0,kinematics:0,dt:1e-7,gasCells:192,shockViscosity:1,ventEnds:2,gasFracture:1,fracture:true,gf:100,productEOS:3,airEOS:4,productCovolume:1e-3};
  const s=Settings.migrate(old);
  assert.equal(s.planeMode,1);assert.equal(s.airEOS,0);assert.equal(s.productEOS,0);
  for(const key of ['kinematics','dt','gasCells','shockViscosity','ventEnds','gasFracture','fracture','gf','productCovolume'])assert.ok(!(key in s),key);
  assert.equal(Settings.migrate({...base,productEOS:1,jwlA:1e11,jwlB:1e9,detonationVelocity:6000,sourceMode:1}).productEOS,1);
  assert.doesNotThrow(()=>B2.normalizeSettings(s));
});

test('the charge fraction integrates the circle area on a cut cell',()=>{
  const s={x:0,y:0,chargeRadius:1};
  assert.equal(B2.chargeFraction([[-.1,-.1],[.1,-.1],[.1,.1],[-.1,.1]],s),1);
  assert.equal(B2.chargeFraction([[2,2],[3,2],[3,3],[2,3]],s),0);
  // Square [0,2]x[0,2] contains a quarter disc of area pi/4.
  assert.ok(Math.abs(B2.chargeFraction([[0,0],[2,0],[2,2],[0,2]],s)-Math.PI/16)<.01);
});

test('a slow wall-pressure pulse reproduces the plane-strain Lamé thick-cylinder solution',{skip:!solverReady},async()=>{
  // Free annulus a=0.1 m, b=1 m, E=20 GPa, nu=0.2. A 20 ms half-sine is much slower than the
  // ~1 ms breathing period; mass damping removes the residual oscillation. At the peak
  // (t = 10 ms) u_r(r) = (1+nu)/E * p a^2/(b^2-a^2) * ((1-2nu) r + b^2/r).
  const sectors=32,rings=10,model=blastRing({sectors,rings}),p=10e6,E=20e9,nu=.2,a=.1,b=1;
  const lame=r=>(1+nu)/E*p*a*a/(b*b-a*a)*((1-2*nu)*r+b*b/r);
  const history=await runOpenCourantBlast(model,{...base,pressure:p,pulse:.02,duration:.02,frames:3,boundary:1,damping:3000},{lazy:true});
  try{
    assert.equal(history.solverBackend,'OpenCourant');assert.equal(history.completed,true);
    const peak=await readBlastFrame(history.id,1);assert.ok(Math.abs(peak.time-.01)<1e-5);
    const mean=ids=>ids.reduce((s,i)=>s+radialDisplacement(model,peak,i),0)/ids.length;
    const wall=mean([...Array(sectors).keys()]),edge=mean([...Array(sectors).keys()].map(k=>rings*sectors+k));
    // Measured: -3.7% at the 32-sided polygonal wall, -0.9% at the outer edge.
    assert.ok(Math.abs(wall/lame(a)-1)<.06,`wall ${wall} m vs Lamé ${lame(a)} m`);
    assert.ok(Math.abs(edge/lame(b)-1)<.03,`outer edge ${edge} m vs Lamé ${lame(b)} m`);
  }finally{await removeRun(history.id);}
});

test('MFEM equilibrium under confinement is injected by /INIBRI and suppresses the startup wave',{skip:!solverReady},async()=>{
  const model=blastRing({sectors:32,rings:10});
  const settings={...base,pressure:0,confineX:10e6,confineY:10e6,boundary:2,duration:2e-4,frames:5};
  const peakVelocity=async history=>{let vmax=0;for(let k=0;k<history.frames.length;k++)for(const v of (await readBlastFrame(history.id,k)).v)vmax=Math.max(vmax,Math.abs(v));return vmax;};
  const pre=await runOpenCourantBlast(model,{...settings,loadMode:0},{lazy:true});
  let preVelocity,suddenVelocity;
  try{
    assert.equal(pre.prestressSolver,'MFEM 4.10');assert.ok(pre.preloadEnergy>0);
    // Far from the hole the Kirsch field tends to the applied confinement, and stays there.
    for(const k of [0,pre.frames.length-1]){
      const frame=await readBlastFrame(pre.id,k);
      const far=model.elements.map((e,i)=>({i,r:Math.hypot(e.centroidX,e.centroidY)})).filter(e=>e.r>.9).map(e=>frame.elements[e.i]);
      const mean=far.reduce((a,e)=>a+e[3]+e[4],0)/(2*far.length);
      assert.ok(Math.abs(mean+10e6)<.6e6,`frame ${k} far-field mean stress ${mean}`);
    }
    preVelocity=await peakVelocity(pre);
  }finally{await removeRun(pre.id);}
  const sudden=await runOpenCourantBlast(model,{...settings,loadMode:1},{lazy:true});
  try{suddenVelocity=await peakVelocity(sudden);}finally{await removeRun(sudden.id);}
  // Residual motion comes from the MFEM full-integration quad vs. OpenCourant one-point
  // HEPH brick discretizations (measured about 7% of the sudden-loading motion).
  assert.ok(preVelocity<.15*suddenVelocity,`prestressed ${preVelocity} m/s vs sudden ${suddenVelocity} m/s`);
});

test('quiet boundaries remove outgoing energy compared with a free outer boundary',{skip:!solverReady},async()=>{
  const model=blastRing({sectors:32,rings:10});
  const run=async boundary=>{const h=await runOpenCourantBlast(model,{...base,boundary,duration:8e-4,frames:9},{lazy:true});try{return h.frames.at(-1).kineticEnergy;}finally{await removeRun(h.id);}};
  const free=await run(1),quiet=await run(2);
  assert.ok(quiet<.25*free,`quiet ${quiet} J vs free ${free} J`);
});

test('a JWL charge with an air gap detonates in ALE and drives the JH2 wall outward',{skip:!(solverReady&&B2.available().gmsh)},async()=>{
  const model=blastRing({sectors:48,rings:12,blastConstitutive:jh2});
  for(const n of model.nodes){n.x*=.05;n.y*=.05;}for(const e of model.elements)e.area*=.0025;
  for(const m of [...model.materials,...model.elements]){m.elasticModulus=51.166e9;m.poissonRatio=.168;m.density=2660;}
  const settings={...base,radius:.005,chargeRadius:.004,rockModel:3,boundary:2,duration:1e-5,frames:5,sourceMode:1,productEOS:1,productDensity:1620,
    productEnergy:4.320987654320988e6,productGamma:1.35,detonationVelocity:6930,jwlA:373.77e9,jwlB:3.7471e9,jwlR1:4.15,jwlR2:.9,jwlOmega:.35,
    airDensity:1.25,airPressure:1e5,airGamma:1.4};
  const history=await runOpenCourantBlast(model,settings,{lazy:true});
  try{
    assert.equal(history.frameScalarCount,12);assert.ok(Math.abs(history.source.chargeAreaRatio-1)<.01);
    assert.ok(history.aleElements>0&&history.initialGasEnergy>0);
    const last=history.frames.at(-1);
    assert.ok(last.gasWallRadius>.0051,`wall radius ${last.gasWallRadius}`);
    assert.ok(Math.max(...history.frames.map(f=>f.pressure))>100e6);
    assert.ok(last.gasWallWork>0&&last.kineticEnergy>0);
  }finally{await removeRun(history.id);}
});
