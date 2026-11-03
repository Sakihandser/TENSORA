// Data/source checks only: no native time integration, material update or blast run.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {createHash}=require('node:crypto'),Cards=require('../blast-materials'),Settings=require('../blast-settings'),Gas=require('../gas-eos'),{rockCard}=require('./helpers/rock-card');
const root=path.resolve(__dirname,'..');
test('available solid and gas models include the added material kernels',()=>{
 assert.deepEqual(Cards.availableIds,[1,3,6]);assert.deepEqual(Gas.productIds,[1,0,3,4]);assert.deepEqual(Gas.ids,[0,3,4]);
 for(const law of [0,2,4,5,7,8,9,10,11,12,13,14])assert.throws(()=>Cards.validate({blastConstitutive:{law}},{rockModel:law}),/已移除/);
 for(const productEOS of [2,5,6])assert.ok(Gas.constraints({sourceMode:1,productEOS,airEOS:0}).errors.length);
 for(const airEOS of [5,6])assert.ok(Gas.constraints({sourceMode:1,productEOS:1,airEOS}).errors.length);
});
test('the original JH2 numeric slots are unchanged and explicit K/G use an extension tag',()=>{
 const card=rockCard();card.jh2.G=21.9e9;card.jh2.K=25.7e9;
 const row=Cards.rows({materials:[{materialNo:7,name:'granite',blastConstitutive:card}]},{rockModel:3}).trim().split(/\s+/);
 assert.equal(row.length,25);assert.equal(row[0],'7');assert.equal(row[1],'3');
 assert.equal(Number(row[8]),4.5e9);assert.equal(Number(row[9]),3.7e9);assert.equal(Number(row[15]),-4500e9);assert.equal(Number(row[16]),300000e9);
 assert.deepEqual(row.slice(22),['ELAS1','21900000000','25700000000']);
});
test('frontend JWL and gas display units are multiplied once to produce SI settings',()=>{
 const src=fs.readFileSync(path.join(root,'src/core/blast-dynamics.js'),'utf8'),literal=src.match(/const BLAST_FIELDS = (\{[\s\S]*?\});/)[1];
 const fields=vm.runInNewContext('('+literal+')');
 for(const key of ['jwlA','jwlB'])assert.equal(fields[key][1],1e9);
 assert.equal(fields.productEnergy[1],1e6);assert.equal(fields.airPressure[1],1e6);
 for(const key of ['productDensity','airDensity','jwlR1','jwlR2','jwlOmega','airGamma'])assert.equal(fields[key][1],1);
});
test('PETN and air library records preserve the thesis volumetric energy and EOS coefficients',()=>{
 const e=JSON.parse(fs.readFileSync(path.join(root,'explosives/library.json'))).explosives.find(x=>x.name==='PETN').settings;
 const a=JSON.parse(fs.readFileSync(path.join(root,'gases/library.json'))).gases.find(x=>x.name==='空气').settings;
 assert.equal(e.productDensity,1320);assert.equal(e.jwlA,586e9);assert.equal(e.jwlB,21.6e9);assert.equal(e.jwlR1,5.81);assert.equal(e.jwlR2,1.77);assert.equal(e.jwlOmega,.282);
 assert.ok(Math.abs(e.productEnergy*e.productDensity-7.38e9)<1e-5);
 assert.equal(a.airGamma,1.4);assert.equal(a.airPressure,100000);
 assert.equal(Settings.normalize({...e,...a,sourceMode:1,rockModel:3}).productEOS,1);
});
test('all compiled EOS headers match the fixed GitHub source manifest',()=>{
 const dir=path.join(root,'third_party/singularity-eos-runtime'),m=JSON.parse(fs.readFileSync(path.join(dir,'manifest.json')));
 for(const f of m.files)assert.equal(createHash('sha256').update(fs.readFileSync(path.join(dir,f.file))).digest('hex'),f.sha256,f.file);
 assert.ok(m.files.some(f=>f.origin==='singularity-eos/eos/eos_jwl.hpp'));
 assert.ok(m.files.some(f=>f.origin==='singularity-eos/eos/eos_ideal.hpp'));
});
test('EOS calls have no local pressure formula or local constitutive fallback',()=>{
 const cpp=fs.readFileSync(path.join(root,'TensoraCore/GasDynamics.cpp'),'utf8'),adapter=fs.readFileSync(path.join(root,'TensoraCore/GasConstitutive.h'),'utf8');
 assert.ok(cpp.includes('EvaluateUpstreamEOS(1,parameters,rho,e)'));
 assert.ok(adapter.includes('upstream_eos::Runtime().evaluate('));assert.ok(adapter.includes('upstream_eos::Runtime().energy('));
 assert.ok(!cpp.includes('const double referenceEnergy='));assert.ok(!adapter.includes('c.model==6'));
 assert.ok(!fs.existsSync(path.join(root,'TensoraCore/SolidConstitutive.h')));
});
test('the supplemental TNT card is separate from thesis PETN and converts kPa and kJ/m3 to SI',()=>{
 const library=JSON.parse(fs.readFileSync(path.join(root,'explosives/library.json'))).explosives;
 const t=library.find(x=>x.name==='TNT').settings,p=library.find(x=>x.name==='PETN').settings;
 assert.equal(t.productDensity,1620);assert.equal(t.detonationVelocity,6930);
 assert.equal(t.jwlA,3.7377e8*1000);assert.equal(t.jwlB,3.7471e6*1000);
 assert.equal(t.jwlR1,4.15);assert.equal(t.jwlR2,.9);assert.equal(t.jwlOmega,.35);
 assert.ok(Math.abs(t.productEnergy*t.productDensity-7e9)<1e-5);assert.notEqual(t.productDensity,p.productDensity);
});
test('paper library cards preserve direct shear moduli through normalization and sidecar serialization',()=>{
 const materials=JSON.parse(fs.readFileSync(path.join(root,'materials/materials.json'))).materials;
 for(const [id,G,K]of [['thesis43-granite',21.9e9,25.7e9],['thesis43-sandstone',9.98e9,12.67e9]]){
  const m=materials.find(x=>x.id===id),card=Cards.normalize(m.blastConstitutive);
  assert.equal(card.jh2.G,G);assert.equal(card.jh2.K,K);assert.equal(card.jh2.K1,25.7e9);
  const row=Cards.rows({materials:[{...m,materialNo:1,blastConstitutive:card}]},{rockModel:3}).trim().split(/\s+/);
  assert.equal(Number(row[23]),G);assert.equal(Number(row[24]),K);
 }
 const cpp=fs.readFileSync(path.join(root,'TensoraCore/BlastDynamics.cpp'),'utf8');
 assert.ok(cpp.includes('row>>p.inputShearModulus>>p.inputBulkModulus'));
 const bridge=fs.readFileSync(path.join(root,'third_party/singularity-eos-runtime/bridge.cpp'),'utf8');
 assert.ok(bridge.includes('singularity::JWL eos(params[2],params[3],params[4],params[5],params[6],params[1],1.)'));
 assert.ok(bridge.includes('eos.BulkModulusFromDensityInternalEnergy(rho,energy)'));
});
