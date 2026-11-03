'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{createHash}=require('node:crypto');
const root=path.resolve(__dirname,'..'),dest=path.resolve(root,'..'),cache=path.join(root,'tmp/paper-plane-stress');
const backup=path.join(dest,'模型修订备份-2026-11-03',new Date().toISOString().replace(/[:.]/g,'-'));fs.mkdirSync(backup,{recursive:true});
const changes=[];const hash=b=>createHash('sha256').update(b).digest('hex');
for(const kind of ['均质板','W45'])for(const stress of [0,20]){
 const name=`论文-${kind}-平面应力-${stress}-${stress}`,file=path.join(dest,name+'.json'),raw=fs.readFileSync(file),s=JSON.parse(raw);fs.writeFileSync(path.join(backup,name+'.json'),raw);
 const before={shockViscosity:s.blastSettings.shockViscosity,gf:s.blastSettings.gf};s.blastSettings.shockViscosity=0;s.blastSettings.gf=519.7;
 function visit(v){if(!v||typeof v!=='object')return;if(v.blastConstitutive?.law===3&&[2340,2660].includes(v.density)){const soft=v.density===2340;v.fractureEnergy=soft?82.51:519.7;if('notes'in v)v.notes+=(v.notes.includes('参考断裂能')?'':' 参考断裂能Gf='+(soft?'82.51 J/m²（Materials 2023,16,1056,表4砂岩NSCB平均）':'519.7 J/m²（Xia等2020表4花岗岩）')+'；属于其他试样文献参考值，当前上游JH2不使用该独立参数。');}for(const val of Object.values(v))if(val&&typeof val==='object')visit(val);}
 visit(s);s.paperModelProvenance={...s.paperModelProvenance,revision:'2026-11-03-no-artificial-viscosity',shockViscosity:0,fractureEnergyReferences:{granite:{value:519.7,unit:'J/m2',source:'https://doi.org/10.1155/2020/8194801',table:4},sandstone:{value:82.51,unit:'J/m2',source:'https://doi.org/10.3390/ma16031056',table:4}},fractureEnergyUsedByJH2:false};
 const out=Buffer.from(JSON.stringify(s));fs.writeFileSync(file+'.revision.tmp',out);assert.ok(fs.readFileSync(file).equals(raw));fs.renameSync(file+'.revision.tmp',file);
 const dfile=path.join(cache,name+'-direct.json'),d=JSON.parse(fs.readFileSync(dfile));visit(d);fs.writeFileSync(dfile,JSON.stringify(d));fs.writeFileSync(path.join(cache,name+'-settings.json'),JSON.stringify(s.blastSettings));
 changes.push({name,file,beforeSha256:hash(raw),sha256:hash(out),before,after:{shockViscosity:0,gf:519.7},materialReferenceFractureEnergies:d.materials.map(m=>({name:m.name,fractureEnergy:m.fractureEnergy})),backup:path.join(backup,name+'.json')});
}
for(const file of ['论文平面应力模型-参数核对与不确定项.md','论文平面应力模型-参数与验证清单.json'])fs.copyFileSync(path.join(dest,file),path.join(backup,file));
fs.writeFileSync(path.join(cache,'revision-changes.json'),JSON.stringify({backup,changes},null,2));console.log(JSON.stringify({backup,changes:changes.map(c=>({name:c.name,...c.after}))}));
