const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),{spawnSync}=require('node:child_process');
const Cards=require('../blast-materials'),Settings=require('../blast-settings'),Gas=require('../gas-eos');
const {runBlastCore}=require('../server'),{removeRun}=require('../blast-runner'),{blastRing}=require('./helpers/blast-ring');
const root=path.resolve(__dirname,'..'),native=path.join(__dirname,'native/x64/Release');
const mc={law:6,mc:{friction:30,dilation:5,cohesion:5e6,tension:1e6,softening:1,residualFriction:25,residualDilation:2,residualCohesion:2e6,peakStrain:.001,residualStrain:.02}};
test.before(()=>{
 for(const project of ['GasVerification','RockVerification']){
  const r=spawnSync('C:/Program Files/Microsoft Visual Studio/2022/Community/MSBuild/Current/Bin/MSBuild.exe',[`tests/native/${project}.vcxproj`,'/p:Configuration=Release','/p:Platform=x64','/v:minimal','/nologo'],{cwd:root,encoding:'utf8',windowsHide:true,maxBuffer:8e6});assert.equal(r.status,0,r.stdout+r.stderr);
 }
});
test('Noble-Abel and Stiffened Gas match original implementations, inverse energy and SI/CGS units',()=>{
 const r=spawnSync(path.join(native,'gas-verification.exe'),['new-eos'],{encoding:'utf8',windowsHide:true});assert.equal(r.status,0,r.stderr);assert.equal(JSON.parse(r.stdout).samples,32);
});
test('solid kernels retain multiaxial stress, engineering shear and softening history over 400 steps',()=>{
 const r=spawnSync(path.join(native,'rock-verification.exe'),['new-materials'],{encoding:'utf8',windowsHide:true});assert.equal(r.status,0,r.stderr||r.stdout);const h=JSON.parse(r.stdout);assert.equal(h.samples,400);assert.ok(h.plastic>0);
});
test('new model cards round-trip SI values and reject unsupported combinations',()=>{
 assert.deepEqual(Cards.normalize(mc),mc);
 assert.equal(Cards.rows({materials:[{materialNo:8,blastConstitutive:mc}]},{rockModel:6,planeMode:1}).trim(),'8 6 30 5 5000000 1000000 1 25 2 2000000 0.001 0.02');
 assert.throws(()=>Cards.validate({blastConstitutive:mc},{rockModel:6,planeMode:0}),/平面应变/);
 assert.throws(()=>Settings.normalize({sourceMode:1,productEOS:3,productCovolume:.001,productDensity:1000}),/bρ/);
 assert.throws(()=>Settings.normalize({sourceMode:1,airEOS:4,ventEnds:1}),/封堵/);
 assert.equal(Gas.active('Covolume',3),true);assert.equal(Gas.active('PressureOffset',4),true);assert.equal(Gas.active('Attraction',3),false);
 for(const name of [...Object.values(Gas.names),...Cards.availableIds.map(i=>Cards.names[i])])assert.doesNotMatch(name,/上游|直接调用/);
});
for(const law of [1,6])for(const productEOS of [3,4])test(`new solid ${law} and product/gas EOS ${productEOS} execute in a coupled blast`,async t=>{
 const model=blastRing({sectors:24,rings:4,outer:.5});model.materials[0].blastConstitutive=law===6?mc:{law:1};
 const h=await runBlastCore(model,{rockModel:law,planeMode:1,sourceMode:1,productEOS,airEOS:productEOS,fracture:true,
  chargeRadius:.05,productDensity:1320,productEnergy:5e6,productGamma:1.4,productCovolume:1e-4,productPressureOffset:1e6,productEnergyShift:1e4,
  airDensity:1.25,airPressure:1e5,airGamma:1.4,airCovolume:1e-4,airPressureOffset:1e4,airEnergyShift:1e3,
  gasCells:64,duration:5e-5,frames:5,boundary:2,ventEnds:0});
 t.after(()=>removeRun(h.id));assert.deepEqual(h.supportedSolidLaws,[1,3,6]);assert.equal(h.settings.productEOS,productEOS);
 assert.ok(h.gasDiagnostics.substeps>0);
 for(const f of h.frames){assert.ok(f.pressure>0&&Number.isFinite(f.pressure));assert.ok(f.elements.every(e=>e.every(Number.isFinite)));assert.ok(Math.abs((f.gasInternalEnergy+f.gasKineticEnergy+f.gasWallWork-h.initialGasEnergy)/h.initialGasEnergy)<1e-8);}
});
