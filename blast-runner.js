// 2D blast runs: OpenCourant/MFEM results -> independently compressed FEMBLT02 frames on local disk.
const fs=require("node:fs/promises"),nativeFs=require("node:fs"),path=require("node:path"),os=require("node:os");
const {randomUUID}=require("node:crypto"),{gzip,gunzip,createGzip}=require("node:zlib"),{promisify}=require("node:util"),{once}=require("node:events");
const zip=promisify(gzip),unzip=promisify(gunzip);
const ResultExport=require('./result-export'),deflate=promisify(require('node:zlib').deflateRaw);
const Settings=require("./blast-settings"),Codec=require("./blast-frame-codec");
const runs=new Map();
const ownedDirectories=new Set();
process.once("exit",()=>{
  for(const directory of ownedDirectories)try{nativeFs.rmSync(directory,{recursive:true,force:true});}catch{}
});
let activeRuns=0;
async function removeRun(id){const run=runs.get(id);if(!run)return;runs.delete(id);await fs.rm(run.directory,{recursive:true,force:true});ownedDirectories.delete(run.directory);}
async function pruneRuns(){
  for(const [id,run] of runs)if(Date.now()-run.createdAt>12*3600*1000 && !run.readers)await removeRun(id);
  while(runs.size>=8){const candidate=[...runs].find(([,run])=>!run.readers);if(!candidate)throw new Error("All blast history slots are in use.");await removeRun(candidate[0]);}
}
async function readBlastFrame(id,index,materialize=false){
  const run=runs.get(id);if(!run || !Number.isInteger(index) || index<0 || index>=run.manifest.frames.length)throw new Error("Blast history expired or frame does not exist. Run the simulation again.");
  run.readers++;
  try{return Codec.decode(await unzip(await fs.readFile(path.join(run.directory,`${index}.bin.gz`))),run.manifest,materialize);}
  finally{run.readers--;}
}
// 2D blast on the bundled OpenCourant/MFEM solvers (blast2d-opencourant.js).
async function runOpenCourantBlastImpl(model,inputSettings={},options={}){
  const Blast2d=require('./blast2d-opencourant');
  await pruneRuns();
  const directory=await fs.mkdtemp(path.join(os.tmpdir(),"fem-blast-")),id=randomUUID();
  ownedDirectories.add(directory);
  try{
    let bytes=0;const summaries=[];
    // Monotonic fraction; remaining time is estimated from the solving/saving rate.
    let lastFraction=0,rateStart=null;
    const onProgress=options.onProgress&&(p=>{
      const fraction=Math.max(lastFraction,Math.min(1,p.fraction||0));lastFraction=fraction;
      if(rateStart===null&&fraction>0&&p.phase!=='complete')rateStart={seconds:p.elapsedSeconds,fraction};
      const rate=rateStart&&fraction>rateStart.fraction?(fraction-rateStart.fraction)/Math.max(1e-9,p.elapsedSeconds-rateStart.seconds):0;
      options.onProgress({...p,fraction,remainingSeconds:fraction>=1?0:rate>0?(1-fraction)/rate:null});
    });
    const result=await Blast2d.runBlast2d(model,inputSettings,{signal:options.signal,onProgress});
    const metadata=result.metadata;
    let peakStress=0,peakDynamicStress=0;
    for(let i=0;i<result.frames.length;i++){
      const raw=result.frames[i],frame=Codec.summary(raw,metadata);
      if(Object.values(frame).some(value=>!Number.isFinite(value)))throw new Error("Invalid blast frame summary.");
      const compressed=await zip(raw,{level:1});bytes+=compressed.length;
      if(bytes>4*1024**3)throw new Error("Compressed blast history exceeds 4 GiB. Reduce saved frames or duration.");
      await fs.writeFile(path.join(directory,`${i}.bin.gz`),compressed);summaries.push(frame);
      if(options.onFrame)await options.onFrame(frame,metadata,i,raw);
      peakStress=Math.max(peakStress,frame.maxStress);peakDynamicStress=Math.max(peakDynamicStress,frame.maxDynamicStress);
    }
    const settings=Settings.normalize(inputSettings);
    const manifest={ok:true,...metadata,id,settings,frames:summaries,peakStress,peakDynamicStress,storage:"compressed-frame-files",compressedBytes:bytes,
      frameBaseUrl:`./api/blast-runs/${id}/frames/`,downloadUrl:`./api/blast-runs/${id}/download`};
    runs.set(id,{directory,manifest,model,readers:0,createdAt:Date.now()});
    await fs.writeFile(path.join(directory,"manifest.json"),JSON.stringify(manifest));
    if(options.lazy)return manifest;
    if(Codec.frameBytes(metadata)*metadata.frameCount>128*1024*1024)throw new Error("Use lazy:true for histories larger than 128 MiB.");
    const materialized=[];for(let i=0;i<summaries.length;i++)materialized.push(await readBlastFrame(id,i,true));
    return {...manifest,frames:materialized};
  }catch(error){
    runs.delete(id);await fs.rm(directory,{recursive:true,force:true});ownedDirectories.delete(directory);
    throw error;
  }
}
async function runOpenCourantBlast(...args){
  if(activeRuns>=1)throw new Error("已有二维爆破任务正在计算，请等待其完成或取消后再开始。");
  activeRuns++;try{return await runOpenCourantBlastImpl(...args);}finally{activeRuns--;}
}
// Point histories: node displacement / velocity and element cell values at every saved frame.
const PROBE_LIMIT=64;
function parseProbeIndices(text,count){
  if(text==null||text==='')return [];
  const values=String(text).split(',').map(Number);
  if(values.length>PROBE_LIMIT||values.some(v=>!Number.isSafeInteger(v)||v<0||v>=count))throw new Error("Invalid probe indices.");
  return [...new Set(values)];
}
async function probeBlastHistory(id,nodeIndices,elementIndices){
  const run=runs.get(id);if(!run)throw new Error("Blast history expired. Run the simulation again.");
  const {nodeCount,elementCount}=run.manifest;
  const nodes=parseProbeIndices(nodeIndices,nodeCount),elements=parseProbeIndices(elementIndices,elementCount);
  const result={ok:true,cellScalarCount:run.manifest.cellScalarCount??7,times:[],pressure:[],
    nodes:nodes.map(index=>({index,u:[],v:[]})),elements:elements.map(index=>({index,cells:[]}))};
  run.readers++;
  try{
    for(let i=0;i<run.manifest.frames.length;i++){
      const frame=Codec.decode(await unzip(await fs.readFile(path.join(run.directory,`${i}.bin.gz`))),run.manifest);
      result.times.push(frame.time);result.pressure.push(frame.pressure);
      result.nodes.forEach(entry=>{const k=entry.index;entry.u.push([frame.u[2*k],frame.u[2*k+1]]);entry.v.push([frame.v[2*k],frame.v[2*k+1]]);});
      result.elements.forEach(entry=>entry.cells.push(Array.from(frame.elements[entry.index])));
    }
  }finally{run.readers--;}
  return result;
}
async function serveBlastHistory(url,response){
  const match=/^\/api\/blast-runs\/([a-f0-9-]+)\/(?:frames\/(\d+)|download|report|probe)$/.exec(url.pathname);if(!match)return false;
  const run=runs.get(match[1]);
  if(!run){response.writeHead(404,{"Content-Type":"application/json"});response.end(JSON.stringify({ok:false,error:"Blast history expired. Run the simulation again."}));return true;}
  if(url.pathname.endsWith('/probe')){
    try{
      const body=JSON.stringify(await probeBlastHistory(match[1],url.searchParams.get('nodes'),url.searchParams.get('elements')));
      response.writeHead(200,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'});response.end(body);
    }catch(error){response.writeHead(400,{'Content-Type':'application/json; charset=utf-8'});response.end(JSON.stringify({ok:false,error:error.message}));}
    return true;
  }
  run.readers++;
  try{
    if(match[2]!==undefined){
      const index=Number(match[2]);if(index>=run.manifest.frames.length){response.writeHead(404);response.end();return true;}
      const file=path.join(run.directory,`${index}.bin.gz`),stat=await fs.stat(file);
      response.writeHead(200,{"Content-Type":"application/octet-stream","Content-Encoding":"gzip","Content-Length":stat.size,"Cache-Control":"no-store"});
      await new Promise((resolve,reject)=>{const input=nativeFs.createReadStream(file);input.on("error",reject);response.on("close",()=>{input.destroy();resolve();});response.on("finish",resolve);input.pipe(response);});
    }else if(url.pathname.endsWith('/report')){
      const selected=Number(url.searchParams.get('frame')??run.manifest.frames.length-1);
      if(!Number.isInteger(selected)||selected<0||selected>=run.manifest.frames.length){response.writeHead(400,{'Content-Type':'application/json'});response.end(JSON.stringify({error:'Invalid export frame.'}));return true;}
      const entries=ResultExport.blastDocuments(run.model,run.manifest,i=>readBlastFrame(match[1],i),selected);
      response.writeHead(200,{'Content-Type':'application/zip','Content-Disposition':'attachment; filename="blast-results.zip"','Cache-Control':'no-store'});
      for await(const bytes of ResultExport.archive(entries,raw=>deflate(raw,{level:1}))){
        if(response.destroyed)break;
        if(!response.write(bytes))await new Promise((resolve,reject)=>{
          const cleanup=()=>{response.off('drain',drain);response.off('close',close);response.off('error',fail);};
          const drain=()=>{cleanup();resolve();},close=()=>{cleanup();reject(new Error('Download closed.'));},fail=error=>{cleanup();reject(error);};
          response.once('drain',drain);response.once('close',close);response.once('error',fail);
        });
      }
      response.end();
    }else{
      response.writeHead(200,{"Content-Type":"application/gzip","Content-Disposition":"attachment; filename=blast-history.json.gz"});
      const gzipStream=createGzip({level:1});gzipStream.on("error",()=>response.destroy());gzipStream.pipe(response);
      response.on("close",()=>gzipStream.destroy());
      const write=async text=>{if(gzipStream.destroyed)throw new Error("Download closed.");if(!gzipStream.write(text))await once(gzipStream,"drain");};
      await write(JSON.stringify({...run.manifest,model:run.model,frames:undefined}).replace(/}$/,',"frames":['));
      for(let i=0;i<run.manifest.frames.length;i++)await write((i ? "," : "")+JSON.stringify(await readBlastFrame(match[1],i,true)));
      gzipStream.end("]}");await new Promise(resolve=>{response.on("finish",resolve);response.on("close",resolve);});
    }
  }catch(error){response.destroy(error);}finally{run.readers--;}
  return true;
}
module.exports={runOpenCourantBlast,readBlastFrame,serveBlastHistory,probeBlastHistory,removeRun};
