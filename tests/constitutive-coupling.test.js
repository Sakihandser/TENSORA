const test=require('node:test'),assert=require('node:assert/strict');
const {blastRing}=require('./helpers/blast-ring'),{rockCard}=require('./helpers/rock-card');
const {runBlastCore}=require('../server'),{removeRun}=require('../blast-runner');
for(const productEOS of [0,1])test(`upstream products EOS ${productEOS}, air and JH2 execute together with SI inputs`,async t=>{
 const model=blastRing({sectors:24,rings:4,outer:.5});
 model.materials[0].blastConstitutive=rockCard();
 const h=await runBlastCore(model,{
  rockModel:3,planeMode:1,sourceMode:1,productEOS,airEOS:0,fracture:true,
  chargeRadius:.05,productDensity:1320,productEnergy:7.38e9/1320,
  jwlA:586e9,jwlB:21.6e9,jwlR1:5.81,jwlR2:1.77,jwlOmega:.282,
  airDensity:1.25,airPressure:1e5,airGamma:1.4,
  gasCells:64,duration:3e-5,frames:4,boundary:2
 });
 t.after(()=>removeRun(h.id));
 assert.equal(h.gasBackendCommit,'b4f71a7748770dfa6ce4d678754c463c09262fb7');
 assert.equal(h.gasBackendABI,1);assert.equal(h.solidConstitutiveVersion,2);
 assert.equal(h.solverInputUnits,'m-kg-s-Pa-J/kg');
 const j=model.materials[0].blastConstitutive.jh2,p=h.jh2KernelInputs[0],G=model.materials[0].elasticModulus/(2*(1+model.materials[0].poissonRatio));
 assert.equal(p.materialNo,1);assert.equal(p.density,model.materials[0].density);
 const expected=[G,2*G,j.A,j.B,j.M,j.N,j.C,j.rate0,j.maxStrength,j.T/j.pHEL,j.pHEL,j.normalizationStress||1.5*(j.HEL-j.pHEL),j.D1,j.D2,j.K1,j.K2,j.K3,j.beta,0,1e30];
 p.parameters.forEach((v,i)=>assert.ok(Math.abs(v-expected[i])<=1e-14*Math.max(1,Math.abs(expected[i])),`native JH2 slot ${i+1}`));
 assert.equal(h.gasKernelInputs.referenceDensity,1320);assert.equal(h.gasKernelInputs.specificEnergy,7.38e9/1320);
 if(productEOS===1){assert.equal(h.gasKernelInputs.A,586e9);assert.equal(h.gasKernelInputs.B,21.6e9);}
 assert.equal(h.gasConstitutiveVersion,2);assert.ok(h.gasDiagnostics.substeps>0);
 for(const f of h.frames){
  assert.ok(f.pressure>0&&Number.isFinite(f.pressure));
  assert.ok(f.gasInternalEnergy>0);assert.ok(f.elements.every(e=>e.every(Number.isFinite)));
  assert.ok(Math.abs((f.gasInternalEnergy+f.gasKineticEnergy+f.gasWallWork-h.initialGasEnergy)/h.initialGasEnergy)<1e-8);
 }
});
