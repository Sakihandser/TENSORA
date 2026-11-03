// Run exported direct models without editing material constants or filtering
// damage. Manifest paths are relative to the manifest, not the current shell.
// node scripts/verify-blast-cases.cjs cases.json output-directory
// cases.json: [{"name":"W45-0-0","model":"W45-direct.json","settings":{...}}]
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {runBlastCore}=require('../server'),{readBlastFrame,removeRun}=require('../blast-runner');
async function main(){
 if(process.argv.includes('--help')){console.log('Usage: node scripts/verify-blast-cases.cjs cases.json output-directory\nManifest: [{name, model: "relative/direct-model.json", settings: {...}}]');return;}
 if(!process.argv[2]||!process.argv[3])throw Error('Supply a case manifest and output directory. Use --help.');
 const manifest=path.resolve(process.argv[2]),out=path.resolve(process.argv[3]),jobs=JSON.parse(fs.readFileSync(manifest,'utf8'));
 if(!Array.isArray(jobs)||!jobs.length)throw Error('The case manifest must be a nonempty array.');
 const names=new Set();for(const job of jobs){if(typeof job.name!=='string'||!job.name||/[\\/:*?"<>|]/.test(job.name)||names.has(job.name))throw Error('Each case needs a unique filename-safe name.');names.add(job.name);}
 fs.mkdirSync(out,{recursive:true});
 for(const job of jobs){
  const source=path.resolve(path.dirname(manifest),job.model),raw=fs.readFileSync(source),m=JSON.parse(raw),start=Date.now();
  const modelHash=crypto.createHash('sha256').update(raw).digest('hex');let last=0;
  const h=await runBlastCore(m,job.settings,{lazy:true,onProgress:p=>{if(Date.now()-last>30000){console.log(job.name,`${(100*p.fraction).toFixed(1)}%`);last=Date.now();}}});
  try{
   const firstFailure=new Float64Array(m.elements.length).fill(-1),history=[];let final;
   for(let k=0;k<h.frames.length;k++){
    const f=await readBlastFrame(h.id,k),materials={};let radius=0;
    for(let i=0;i<m.elements.length;i++){
     const e=m.elements[i],d=f.elements[i][6],g=materials[e.materialNo]??={area:0,damagedArea:0,integratedDamage:0};
     g.area+=e.area;g.integratedDamage+=e.area*d;
     if(d>.95){g.damagedArea+=e.area;radius=Math.max(radius,Math.hypot(e.centroidX-h.settings.x,e.centroidY-h.settings.y));if(firstFailure[i]<0)firstFailure[i]=f.time;}
    }
    history.push({time:f.time,pressure:f.pressure,damageRadius:radius,materials});final=f;
   }
   const metadata={...h};delete metadata.id;delete metadata.frameBaseUrl;delete metadata.downloadUrl;
   fs.writeFileSync(path.join(out,job.name+'.json'),JSON.stringify({name:job.name,model:source,modelHash,seconds:(Date.now()-start)/1000,metadata,history},null,2));
   fs.writeFileSync(path.join(out,job.name+'-cells.json'),JSON.stringify({nodes:m.nodes.map(n=>[n.x,n.y]),materials:m.materials,elements:m.elements.map((e,i)=>[...e.nodeNumbers,final.elements[i][6],firstFailure[i],e.materialNo])}));
   console.log('DONE',job.name,JSON.stringify(history.at(-1)));
  }finally{await removeRun(h.id);}
 }
}
if(require.main===module)main().catch(e=>{console.error(e);process.exitCode=1;});
