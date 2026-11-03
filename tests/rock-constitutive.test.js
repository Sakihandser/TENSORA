const {rockCard}=require('./helpers/rock-card');
const test=require('node:test'),assert=require('node:assert/strict'),path=require('node:path'),fs=require('node:fs'),{spawnSync}=require('node:child_process');
const Cards=require('../blast-materials'),Settings=require('../blast-settings'),Codec=require('../blast-frame-codec');
const root=path.resolve(__dirname,'..'),exe=path.join(__dirname,'native/x64/Release/rock-verification.exe');
test.before(()=>{const inputs=['tests/native/RockVerification.cpp','tests/native/RockVerification.vcxproj','TensoraCore/RockConstitutive.h','TensoraCore/OpenRadiossJH2.h'];if(fs.existsSync(exe)&&fs.existsSync(path.join(path.dirname(exe),'openradioss_jh2.dll'))&&inputs.every(f=>fs.statSync(path.join(root,f)).mtimeMs<=fs.statSync(exe).mtimeMs))return;
 const r=spawnSync('C:/Program Files/Microsoft Visual Studio/2022/Community/MSBuild/Current/Bin/MSBuild.exe',['tests/native/RockVerification.vcxproj','/p:Configuration=Release','/p:Platform=x64','/v:minimal','/nologo'],{cwd:root,encoding:'utf8',windowsHide:true});assert.equal(r.status,0,r.stdout+r.stderr);});
function driver(mode,n){const r=spawnSync(exe,[mode,String(n??400)],{encoding:'utf8',windowsHide:true});assert.equal(r.status,0,r.stderr);return JSON.parse(r.stdout);}
test('JH2 HEL normalization, pressure and rate strengthening match independent equations',()=>{const x=driver('strength');assert.equal(x.sigmaHEL,1.2e9);const expected=1.2e9*.76*((100e6+54e6)/3.7e9)**.62;assert.ok(Math.abs(x.intactConfined/expected-1)<1e-12);assert.ok(x.intactConfined>x.intact0);assert.ok(Math.abs(x.fast/x.intactConfined-(1+.005*Math.log(1e5)))<1e-12);assert.ok(x.failed<x.intactConfined);assert.ok(Math.abs(x.failureStrain-(.005*((100e6+54e6)/3.7e9)**.7))<1e-14);});
test('compression shock viscosity dissipates energy and introduces no expansion traction',()=>{const x=driver('shock-viscosity');assert.ok(x.power>0);assert.ok(x.trace<0);assert.equal(x.expansion,0);});
test('JH2 compression develops plastic dissipation, irreversible damage and a converged material path',()=>{const coarse=driver('path',400),fine=driver('path',800);assert.ok(fine.damage>0&&fine.damage<=1);assert.ok(fine.plasticWork>0&&fine.plasticStrain>0);assert.ok(Math.abs(fine.q/coarse.q-1)<.02);const u=driver('unload');assert.ok(u.state.damage>=u.oldDamage);assert.ok(u.state.plasticStrain>=u.oldPlastic);});

test('JH2 first yield returns to current strength before updating damage',()=>{
 const x=driver('yield-onset');
 assert.ok(x.firstDamage>0 && x.firstDamage<1e-5,`damage after a 1e-8 relative yield excess: ${x.firstDamage}`);
 assert.ok(x.firstPlastic>0 && x.firstPlastic<1e-9);
 assert.ok(x.state.damage>=x.firstDamage);
 assert.ok(x.state.plasticStrain>=x.firstPlastic);
});
test('JH2 bulking obeys the published quadratic energy equation and enters the next pressure update',()=>{
 const x=driver('bulking'),mu=.01,K=25.7e9;
 const eos=K*mu-4500e9*mu**2+300000e9*mu**3;
 assert.ok(x.energy>0&&x.damage>0);
 const expected=Math.sqrt((K*mu)**2+2*K*x.energy)-K*mu;
 assert.ok(Math.abs(x.bulking/expected-1)<1e-10);
 assert.ok(Math.abs(x.pressureBefore-eos)<1e-5);
 assert.ok(Math.abs(x.pressureAfter-eos-x.bulking)<1e-5);
});
test('JH2 hydrostatic tension caps pressure without inventing deviatoric plastic strain or damage',()=>{const x=driver('tension');assert.ok(x.damage<1e-8);assert.ok(x.plasticStrain<1e-16);assert.ok(x.plasticWork<1e-10);assert.ok(Math.abs(x.pressure+54e6)<1);assert.ok(x.q<1e-6);});
test('JH2 shear loading and holding match an independent scalar reference update',()=>{
 // Constant pressure + pure shear reduces the published 3D return to a scalar
 // recurrence, independently of the C++ tensor and plane-stress implementation.
 const G=51.166364e9/(2*(1+.168181818)),p=20e6,sigma=4.5e9,fail=.005*((p+54e6)/3.7e9)**.7;
 let q=0,d=0,ep=0;const samples=[];
 for(let i=0;i<600;i++){
  const gamma=i<400?.02/400:0,rate=gamma/(Math.sqrt(3)*1e-8),r=1+.005*Math.log(Math.max(1,rate));
  const intact=sigma*.76*((p+54e6)/3.7e9)**.62*r,failed=sigma*Math.min(.25,.25*(p/3.7e9)**.62*r);
  const trial=q+Math.sqrt(3)*G*gamma,next=Math.min(trial,(1-d)*intact+d*failed),dep=(trial-next)/(3*G);
  ep+=dep;d=Math.min(1,d+dep/fail);q=next;
  if([159,160,161,180,399,599].includes(i))samples.push({q,d,ep});
 }
 const x=driver('shear-reference');assert.equal(x.samples.length,samples.length);
 x.samples.forEach((x,i)=>{const r=samples[i];assert.ok(Math.abs(x.q/r.q-1)<1e-10);assert.ok(Math.abs(x.damage-r.d)<1e-10);assert.ok(Math.abs(x.plasticStrain-r.ep)<1e-12);assert.ok(Math.abs(x.pressure-p)<1e-6);});
 assert.ok(samples.at(-1).d>0 && samples.at(-1).ep>0);
});
test('material cards preserve SI units, distinguish hydrostatic T from ft and reject unstable EOS',()=>{const card=rockCard(44e6),m={materialNo:1,name:'sandstone',blastConstitutive:card};assert.equal(card.jh2.T,44e6);assert.equal(Cards.validate(m,{rockModel:0}).model,3);assert.equal(m.tensileStrength,undefined);assert.ok(Cards.rows({materials:[m]},{rockModel:0}).startsWith('1 3 '));assert.throws(()=>Cards.validate({...m,blastConstitutive:{...card,jh2:{...card.jh2,K3:0}}},{rockModel:3}),/tangent/);assert.equal(Cards.thesisPreset,undefined);assert.equal(Settings.normalize({rockModel:3,gasFracture:1}).rockModel,3);});
test('extended constitutive frames preserve three-dimensional stress, plastic strain and storage work',()=>{const meta={nodeCount:3,elementCount:1,frameScalarCount:16,cellScalarCount:10};const a=new Float64Array(Codec.frameBytes(meta)/8);for(let i=0;i<a.length;i++)a[i]=i+1;const f=Codec.decode(a,meta);assert.equal(f.plasticWork,13);assert.equal(f.crackVolume,14);assert.equal(f.elements[0].length,10);assert.equal(f.elements[0][7],36);assert.equal(Codec.summary(new Uint8Array(a.buffer),meta).gasStorageWork,15);});
test('a saved model keeps its constitutive card when the local library has a different card',()=>{
 const vm=require('node:vm'),{sceneWorkflowHarness}=require('./helpers/scene-workflow');const h=sceneWorkflowHarness({name:'card roundtrip',regions:[]}),c=h.context;
 c.card=rockCard();c.card.jh2.T=57e6;
 vm.runInContext(`materialLibrary=[{id:'rock',name:'rock',elasticModulus:50,poissonRatio:.2,density:2600,blastConstitutive:{law:1}}];
   scene.regions=[{id:'R1',regionKind:'structure',materialId:'rock',material:{id:'rock',name:'rock',elasticModulus:40,poissonRatio:.2,density:2600,blastConstitutive:card}}];syncRegionMaterialSnapshots();`,c);
 const m=c.materialSnapshotForRegion(h.scene.regions[0]);assert.equal(m.blastConstitutive.jh2.T,57e6);assert.equal(m.elasticModulus,50);
});
test('axial discharge frame layout retains typed displacement offsets and finite vent diagnostics',()=>{
 const meta={nodeCount:3,elementCount:1,frameScalarCount:24,cellScalarCount:10},a=Float64Array.from({length:Codec.frameBytes(meta)/8},(_,i)=>i+1),f=Codec.decode(a,meta);
 assert.equal(f.gasVentedMass,21);assert.equal(f.gasVentedEnergy,22);assert.equal(f.gasProductMass,23);assert.equal(f.gasAirMass,24);assert.equal(f.u[0],25);assert.equal(f.elements[0][0],37);assert.equal(Codec.summary(new Uint8Array(a.buffer),meta).gasVentedEnergy,22);
 a[21]=NaN;assert.throws(()=>Codec.decode(a,meta),/Non-finite/);
});
test('geometry diagnostics distinguish planar collapse from transverse thickening and preserve old frame layouts',()=>{
 for(const count of [24,28]){
  const meta={nodeCount:3,elementCount:1,frameScalarCount:count,cellScalarCount:10,geometryDiagnosticsVersion:1};
  const a=Float64Array.from({length:Codec.frameBytes(meta)/8},(_,i)=>i+1),f=Codec.decode(a,meta),summary=Codec.summary(new Uint8Array(a.buffer),meta);
  assert.equal(f.minimumPlanarJacobian,21);assert.equal(f.maximumThicknessStretch,23);assert.equal(f.maximumPlaneStressResidual,24);assert.equal(f.u[0],count+1);
  assert.equal(summary.minimumThicknessStretch,22);assert.equal(f.gasVentedMass,count===28?25:undefined);
  a[22]=NaN;assert.throws(()=>Codec.decode(a,meta),/Non-finite/);
 }
});
