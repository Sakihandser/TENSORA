// File/parameter audit only. Never starts the native solver or advances a state.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{createHash}=require('node:crypto');
const root=path.resolve(__dirname,'..'),apply=process.argv.includes('--apply');
const out=path.resolve(root,'../检查报告-2026-10-28/本构调用审计');fs.mkdirSync(out,{recursive:true});
const expectedSettings={sourceMode:1,rockModel:3,productEOS:1,airEOS:0,airDensity:1.25,productDensity:1320,productEnergy:7.38e9/1320,
 jwlA:586e9,jwlB:21.6e9,jwlR1:5.81,jwlR2:1.77,jwlOmega:.282,airGamma:1.4,airPressure:100000,radius:.008,chargeRadius:.005,detonationVelocity:6690};
const jh2={A:.76,N:.62,B:.25,M:.62,C:.005,rate0:1,HEL:4.5e9,pHEL:3.7e9,D1:.005,D2:.7,maxStrength:.25,K1:25.7e9,K2:-4500e9,K3:300000e9,normalizationStress:4.5e9};
const modelArg=process.argv.indexOf('--models');
const modelDirectory=modelArg>=0?path.resolve(process.argv[modelArg+1]):fs.readdirSync(root).some(x=>/^论文-.*\.json$/u.test(x))?root:path.resolve(root,'../论文复现');
const files=fs.readdirSync(modelDirectory).filter(x=>/^论文-(均质板|W45|W90)-\d+-\d+\.json$/u.test(x)).sort();assert.equal(files.length,12);
const records=[];
for(const name of files){
 const file=path.join(modelDirectory,name),raw=fs.readFileSync(file),m=JSON.parse(raw),changes=[];let cards=0;
 // Older scenes omit airEOS; their existing normalizer supplies ideal air (0).
 if(m.blastSettings.airEOS===undefined){assert.ok(apply,`${name}: explicit airEOS required`);changes.push({path:'scene.blastSettings.airEOS',before:null,after:0});m.blastSettings.airEOS=0;}
 for(const [k,v]of Object.entries(expectedSettings))assert.equal(m.blastSettings[k],v,`${name}: ${k}`);
 const [,x,y]=name.match(/-(\d+)-(\d+)\.json$/);assert.equal(m.blastSettings.confineX,Number(x)*1e6);assert.equal(m.blastSettings.confineY,Number(y)*1e6);
 function visit(v,at){if(!v||typeof v!=='object')return;
  if(v.blastConstitutive?.law===3){
   const j=v.blastConstitutive.jh2;for(const[k,n]of Object.entries(jh2))assert.equal(j[k],n,`${name} ${at}: ${k}`);
   const soft=v.density===2340,hard=v.density===2660;assert.ok(soft||hard,`${name}: unknown paper material density`);
   assert.equal(j.T,soft?44e6:54e6);const G=soft?9.98e9:21.9e9,K=soft?12.67e9:25.7e9;
   for(const[k,n]of Object.entries({G,K}))if(j[k]!==n){if(!apply)assert.equal(j[k],n,`${name}: direct ${k}`);changes.push({path:at+'.blastConstitutive.jh2.'+k,before:j[k]??null,after:n});j[k]=n;}
   cards++;
  }
  for(const[k,n]of Object.entries(v))if(n&&typeof n==='object')visit(n,at+'.'+k);
 }
 visit(m,'scene');assert.ok(cards>0);
 const after=changes.length?Buffer.from(JSON.stringify(m)):raw;
 if(apply&&changes.length){const temp=file+'.parameter-audit.tmp';fs.writeFileSync(temp,after);assert.ok(fs.readFileSync(file).equals(raw),'Model changed during audit: '+file);fs.renameSync(temp,file);}
 records.push({name,file,cards,changes,beforeSha256:createHash('sha256').update(raw).digest('hex'),sha256:createHash('sha256').update(after).digest('hex')});
 console.log(name,changes.length?'updated direct K/G':'verified');
}
const sourceFiles=fs.readdirSync(modelDirectory).filter(n=>/\.(pdf|png)$/iu.test(n)).map(name=>({file:path.join(modelDirectory,name),sha256:createHash('sha256').update(fs.readFileSync(path.join(modelDirectory,name))).digest('hex')}));
fs.writeFileSync(path.join(out,apply?'论文模型参数修正清单.json':'论文模型参数复核清单.json'),JSON.stringify({mode:apply?'apply':'read-only',recomputed:false,sourceFiles,expectedSettings,jh2,records,
 sourcePriority:'Thesis PETN/JH2 tables for the 12 thesis scenes; separate supplemental image TNT remains a separate library entry; image supplies air density 1.25 kg/m3.',
 unverifiedByThesis:['beta=0 and referenceLength=0 were not supplied in the thesis tables.','Axial ventEnds=2 and effective length=50 mm remain inherited assumptions; homogeneous numerical slice is 2 mm, heterogeneous section refers to 1:1 physical geometry. No equivalence to this axial vent model has been verified.','JWL API Cv=1 is an unused temperature-API constructor placeholder; rho-e pressure/bulk do not depend on it.']},null,2));
