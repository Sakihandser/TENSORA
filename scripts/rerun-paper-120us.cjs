// Rebuild direct inputs from the current thesis scenes, then compute final damage.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),paper=path.resolve(root,'../论文复现'),out=path.join(paper,'复算-0.12ms-2026-10-28');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
fs.mkdirSync(out,{recursive:true});
async function main(){
 const {runBlastCore}=require('../server'),{readBlastFrame,removeRun}=require('../blast-runner');
 const allJobs=fs.readdirSync(paper).filter(f=>/^论文-(均质板|W45|W90)-\d+-\d+\.json$/u.test(f)).sort();assert.equal(allJobs.length,12);
 const group=process.argv[2],jobs=group?allJobs.filter(f=>f.startsWith('论文-'+group+'-')):allJobs;
 assert.ok(jobs.length);
 const audit={date:'2026-10-28',duration:0.00012,originalScenesModified:false,binaries:{},cases:[]};
 for(const f of ['TensoraCore.exe','openradioss_jh2.dll','singularity_eos.dll'])audit.binaries[f]=hash(fs.readFileSync(path.join(root,'TensoraCore/x64/Release',f)));
 for(const file of jobs){
  const source=path.join(paper,file),raw=fs.readFileSync(source),s=JSON.parse(raw),name=path.basename(file,'.json');
  assert.equal(s.pointLoads.length+s.distributedLoads.length+s.bodyLoads.length,0,'Conversion supports the unloaded thesis scenes only');
  const regions=s.regions.filter(r=>r.isStructure),mats=[],matById=new Map();
  for(const r of regions){const p=r.materialProperties;if(!matById.has(r.materialId)){const materialNo=mats.length+1;matById.set(r.materialId,materialNo);mats.push({materialNo,name:r.materialName,...p,elasticModulus:p.elasticModulus*1e9,yieldStrength:(p.yieldStrength||0)*1e6,tensileStrength:(p.tensileStrength||0)*1e6,compressiveStrength:(p.compressiveStrength||0)*1e6});}}
  const index=new Map(s.analysisNodes.map((n,i)=>[n.id,i+1]));
  const nodes=s.analysisNodes.map((n,i)=>({nodeNo:i+1,x:n.x,y:n.y,fixUx:n.mechanicalState==='static',fixUy:n.mechanicalState==='static',dofUx:n.dof.ux,dofUy:n.dof.uy,forceX:0,forceY:0,materialNo:matById.get(n.materialId)||0,regionNo:regions.findIndex(r=>r.id===n.regionId)+1}));
  const elements=s.mesh.elements.map((e,i)=>{const nn=e.analysisNodeIds.map(id=>index.get(id));assert.ok(nn.every(Number.isInteger));const mat=mats[matById.get(e.materialId)-1];assert.ok(mat);return {elementNo:i+1,node1:nn[0],node2:nn[1],node3:nn[2],nodeNumbers:nn,area:e.area,centroidX:e.centroid.x,centroidY:e.centroid.y,materialNo:mat.materialNo,elasticModulus:mat.elasticModulus,poissonRatio:mat.poissonRatio,density:mat.density,yieldStrength:0,tensileStrength:0,compressiveStrength:0};});
  const model={header:'FEM_CALCULATION_BINARY_V1',modelName:name,materials:mats,nodes,elements,elementNodeLoads:[]};
  const settings={...s.blastSettings,duration:.00012,frames:2,timeLimitSeconds:7200};
  const expected={sourceMode:1,rockModel:3,productEOS:1,airEOS:0,productDensity:1320,productEnergy:7.38e9/1320,jwlA:586e9,jwlB:21.6e9,jwlR1:5.81,jwlR2:1.77,jwlOmega:.282,airPressure:1e5,airGamma:1.4,radius:.008,chargeRadius:.005,detonationVelocity:6690};
  for(const[k,v]of Object.entries(expected))assert.equal(settings[k],v,`${name}: ${k}`);
  const [,cx,cy]=name.match(/-(\d+)-(\d+)$/);assert.equal(settings.confineX,+cx*1e6);assert.equal(settings.confineY,+cy*1e6);
  for(const mat of mats){const j=mat.blastConstitutive.jh2,soft=mat.density===2340;assert.ok(soft||mat.density===2660);for(const[k,v]of Object.entries({A:.76,N:.62,B:.25,M:.62,C:.005,rate0:1,pHEL:3.7e9,normalizationStress:4.5e9,T:soft?44e6:54e6,D1:.005,D2:.7,maxStrength:.25,K1:25.7e9,K2:-4500e9,K3:300000e9,G:soft?9.98e9:21.9e9,K:soft?12.67e9:25.7e9}))assert.equal(j[k],v,`${name} ${mat.name}: ${k}`);}
  const record={name,source,sourceHash:hash(raw),nodes:nodes.length,elements:elements.length,settings,materials:mats,spacing:s.analysisNodePlacement.spacing};audit.cases.push(record);
  fs.writeFileSync(path.join(out,group?`参数与运行审计-${group}.json`:'参数与运行审计.json'),JSON.stringify(audit,null,2));
  const dest=path.join(out,name+'.json');
  if(fs.existsSync(dest)){const prev=JSON.parse(fs.readFileSync(dest));assert.equal(prev.sourceHash,record.sourceHash);console.log('EXISTS',name);continue;}
  console.log('START',name);const start=Date.now();let last=0,h;
  try{
   h=await runBlastCore(model,settings,{lazy:true,onProgress:p=>{if(Date.now()-last>30000){console.log(name,(p.fraction*100).toFixed(1)+'%',p.phase);last=Date.now();}}});
   const f=await readBlastFrame(h.id,h.frames.length-1),initial=await readBlastFrame(h.id,0);assert.ok(Math.abs(f.time-.00012)<1e-13);
   const stats={};let radius=0;
   const damage=elements.map((e,i)=>{const d=f.elements[i][6];assert.ok(Number.isFinite(d)&&d>=0&&d<=1);assert.ok(d+1e-12>=initial.elements[i][6]);assert.ok(f.elements[i].every(Number.isFinite));const a=stats[e.materialNo]??={area:0,damagedArea:0,integratedDamage:0};a.area+=e.area;a.integratedDamage+=d*e.area;if(d>.95){a.damagedArea+=e.area;radius=Math.max(radius,Math.hypot(e.centroidX-settings.x,e.centroidY-settings.y));}return d;});
   const metadata={...h};delete metadata.id;delete metadata.frameBaseUrl;delete metadata.downloadUrl;
   fs.writeFileSync(path.join(out,name+'-cells.json'),JSON.stringify({time:f.time,nodes:nodes.map(n=>[n.x,n.y]),materials:mats,elements:elements.map((e,i)=>[...e.nodeNumbers,damage[i],e.materialNo])}));
   fs.writeFileSync(dest,JSON.stringify({...record,seconds:(Date.now()-start)/1000,metadata,final:{time:f.time,pressure:f.pressure,damageRadius:radius,materials:stats},checks:{damageFiniteAndInRange:true,damageNondecreasingFromInitial:true,allFinalElementValuesFinite:true}},null,2));
   console.log('DONE',name,JSON.stringify({seconds:(Date.now()-start)/1000,radius,stats}));
  }catch(e){fs.writeFileSync(path.join(out,name+'-ERROR.txt'),e.stack);console.error('FAILED',name,e);}finally{if(h)await removeRun(h.id);}
 }
}
main().catch(e=>{console.error(e);process.exitCode=1;});
