'use strict';
// Structural dynamics workspace: modal, harmonic and implicit transient analyses on
// CalculiX 2.22, explicit impact on OpenCourant 20261011. This module only creates
// the run folder, dispatches to the adapters and stores their nodal frames.
const fs=require('node:fs/promises');
const {existsSync}=require('node:fs');
const path=require('node:path');
const DS=require('./dynamics-settings');
const {fromPayload,modelStats}=require('./dynamics-model');
const Calculix=require('./dynamics-calculix');
const Explicit=require('./dynamics-explicit');
const B3=require('./blast3d-runner');

const RUNS=process.env.TENSORA_DYNAMICS_RUNS_DIR||path.join(__dirname,'calculation-data','dynamics'),DEFAULT_RUNS=RUNS;
const KEEP_RUNS=8;
const FIELD_ORDER=['ux','uy','uz','umag','vx','vy','vz','vmag','sxx','syy','szz','sxy','syz','sxz','vm','pressure','peeq','damage','phx','phy','phz'];
const PLANAR_ONLY=new Set(['uz','vz','syz','sxz','phz']);

function available(){
  return {calculix:existsSync(Calculix.executable),opencourant:B3.available().opencourant};
}

async function pruneRuns(RUNS){
  const entries=await fs.readdir(RUNS,{withFileTypes:true}).catch(()=>[]);
  const runs=[];
  for(const entry of entries)if(entry.isDirectory()&&entry.name.startsWith('run-')){
    const stat=await fs.stat(path.join(RUNS,entry.name)).catch(()=>null);
    if(stat)runs.push({name:entry.name,time:stat.mtimeMs});
  }
  runs.sort((a,b)=>b.time-a.time);
  for(const run of runs.slice(KEEP_RUNS-1))await fs.rm(path.join(RUNS,run.name),{recursive:true,force:true}).catch(()=>{});
}

// Writes each frame as consecutive Float32 blocks of the fields present in the first frame.
function frameWriter(dir,dimension,nodeCount){
  let present=null;
  const frames=[];
  async function write(fields,value,extra){
    present??=FIELD_ORDER.filter(key=>fields[key]&&!(dimension===2&&PLANAR_ONLY.has(key)));
    const stats={},blocks=[];
    for(const key of present){
      const values=fields[key]||new Float32Array(nodeCount).fill(NaN);
      if(values.length!==nodeCount)throw Error('结果帧节点数不一致。');
      let min=Infinity,max=-Infinity;
      for(let i=0;i<nodeCount;i++){const v=values[i];if(Number.isFinite(v)){if(v<min)min=v;if(v>max)max=v;}}
      stats[key]=Number.isFinite(min)?[min,max]:[0,0];
      blocks.push(Buffer.from(values.buffer,values.byteOffset,values.byteLength));
    }
    const index=frames.length;
    await fs.writeFile(path.join(dir,`frame-${String(index).padStart(4,'0')}.bin`),Buffer.concat(blocks));
    frames.push({index,value,stats,...extra});
  }
  return {write,frames,fields:()=>present||[]};
}

async function runDynamics(payload,{signal,onProgress,timeoutMs=2*60*60*1000,runsDirectory=DEFAULT_RUNS}={}){
  const RUNS=runsDirectory;
  const started=Date.now();
  const progress=(phase,fraction,extra={})=>onProgress?.({phase,fraction,elapsedMs:Date.now()-started,...extra});
  progress('preparing',0);
  const s=DS.normalize(payload?.settings);
  const model=fromPayload(payload);
  if(model.dimension===2&&s.analysis==='explicit'&&s.planeMode!==1)throw Error('二维显式动力学按平面应变单层薄片计算，请把二维假设设为平面应变。');
  const state=available();
  const solver=DS.ANALYSES.find(a=>a.id===s.analysis).solver;
  if(solver==='calculix'&&!state.calculix)throw Error('项目内缺少 CalculiX 求解器 third_party/calculix/bin/ccx.exe。');
  if(solver==='opencourant'&&!state.opencourant)throw Error('项目内缺少 OpenCourant 运行时，请恢复 third_party/opencourant/runtime-win-x64。');
  await fs.mkdir(RUNS,{recursive:true});
  await pruneRuns(RUNS);
  const dir=await fs.mkdtemp(path.join(RUNS,'run-'));
  const runId=path.basename(dir);
  const nodeCount=model.coords.length;
  const writer=frameWriter(dir,model.dimension,nodeCount);
  await fs.writeFile(path.join(dir,'request.json'),JSON.stringify({settings:s,dimension:model.dimension})).catch(()=>{});
  const adapter=solver==='calculix'?Calculix:Explicit;
  const outcome=await adapter.run(model,s,{dir,signal,timeoutMs,progress,writeFrame:writer.write});
  const frames=writer.frames;
  if(!frames.length)throw Error('没有有效结果帧。');
  const stats=modelStats(model,1);
  const summary={ok:true,runId,analysis:s.analysis,dimension:model.dimension,solver:outcome.solver,cpuThreads:outcome.cpuThreads,
    settings:s,nodeCount,fields:writer.fields(),frames,modes:outcome.modes||null,history:outcome.history||{},meta:{...outcome.meta,
      nodes:nodeCount,elements:model.elements.length,mass:stats.mass,modelSize:stats.diagonal,
      materials:outcome.meta?.materials||model.materials.map(m=>({name:m.name,E:m.E,nu:m.nu,rho:m.rho}))},
    completed:!outcome.termination,termination:outcome.termination||null,elapsedMs:Date.now()-started};
  // 2D results carry their own mesh so the result page does not depend on later edits.
  if(model.dimension===2)summary.geometry={nodes:model.coords.map(p=>[p[0],p[1]]),triangles:model.elements,
    nodeNo:model.nodeNo,materials:Array.from(model.elementMaterial),materialNames:model.materials.map(m=>m.name)};
  await fs.writeFile(path.join(dir,'summary.json'),JSON.stringify(summary));
  progress(summary.completed?'complete':'partial',1);
  return summary;
}

const RUN_ID=/^run-[A-Za-z0-9_-]{4,40}$/;
async function readFrame(runId,index,{runsDirectory:RUNS=DEFAULT_RUNS}={}){
  if(!RUN_ID.test(runId)||!Number.isSafeInteger(index)||index<0)throw Error('无效的动力学结果请求。');
  return fs.readFile(path.join(RUNS,runId,`frame-${String(index).padStart(4,'0')}.bin`));
}
async function readSummary(runId,{runsDirectory:RUNS=DEFAULT_RUNS}={}){
  if(!RUN_ID.test(runId))throw Error('无效的动力学结果请求。');
  return JSON.parse(await fs.readFile(path.join(RUNS,runId,'summary.json'),'utf8'));
}
// Values of every saved field at selected nodes, frame by frame (time, frequency or mode).
async function readProbe(runId,nodeList,options={}){
  const summary=await readSummary(runId,options),n=summary.nodeCount;
  const nodes=String(nodeList??'').split(',').filter(Boolean).map(Number);
  if(!nodes.length||nodes.length>64||nodes.some(v=>!Number.isSafeInteger(v)||v<0||v>=n))throw Error('测点节点编号无效。');
  const RUNS=options.runsDirectory||DEFAULT_RUNS;
  const fieldCount=summary.fields.length,minBytes=fieldCount*n*4,frameCount=summary.frames.length;
  const values=Object.fromEntries(summary.fields.map(key=>[key,new Array(frameCount)]));
  const readOne=async k=>{
    const file=path.join(RUNS,runId,`frame-${String(k).padStart(4,'0')}.bin`);
    const handle=await fs.open(file,'r');
    try{
      const {size}=await handle.stat();
      if(size<minBytes)throw Error('动力学结果帧不完整，请重新计算。');
      if(size<=65536||nodes.length>=n/8){
        const buffer=await handle.readFile();
        for(let f=0;f<fieldCount;f++){
          const base=f*n,row=new Array(nodes.length);
          for(let j=0;j<nodes.length;j++)row[j]=buffer.readFloatLE((base+nodes[j])*4);
          values[summary.fields[f]][k]=row;
        }
      }else{
        const slot=Buffer.allocUnsafe(4);
        for(let f=0;f<fieldCount;f++){
          const base=f*n,row=new Array(nodes.length);
          for(let j=0;j<nodes.length;j++){
            const {bytesRead}=await handle.read(slot,0,4,(base+nodes[j])*4);
            if(bytesRead<4)throw Error('动力学结果帧不完整，请重新计算。');
            row[j]=slot.readFloatLE(0);
          }
          values[summary.fields[f]][k]=row;
        }
      }
    }finally{await handle.close();}
  };
  const concurrency=Math.min(8,frameCount||1);
  let next=0;
  await Promise.all(Array.from({length:concurrency},async()=>{while(next<frameCount){const k=next++;await readOne(k);}}));
  return {ok:true,nodes,fields:summary.fields,axis:summary.frames.map(frame=>frame.value),values};
}

module.exports={runDynamics,readFrame,readSummary,readProbe,available,RUNS,FIELD_ORDER};
