'use strict';
const fs=require('node:fs/promises'),path=require('node:path'),{spawn}=require('node:child_process');
const {normalize,materialFor}=require('./deformation-settings');
const python=path.join(__dirname,'third_party','phast','runtime-win-x64','python.exe');
function prepareFracture(model,raw){
 const s=normalize(raw);
 if(s.solver!=='phast'||s.finiteStrain||s.planeMode!==1)throw Error('PhAST 断裂路径目前要求小变形平面应变。');
 const displacement=s.fractureLoading==='displacement';
 if(displacement&&model?.nodes?.some(n=>(n.fixUx&&n.forceX)||(n.fixUy&&n.forceY)))throw Error('位移加载方向与固定约束冲突，请调整载荷节点或约束。');
 const validationModel=displacement&&Array.isArray(model?.nodes)
   ? {...model,nodes:model.nodes.map(n=>({...n,fixUx:n.fixUx||Boolean(n.forceX),fixUy:n.fixUy||Boolean(n.forceY)}))}
   : model;
 // Reuse the established geometric/constraint validation without calling CCX.
 require('./deformation-runner').deck(validationModel,{...s,solver:'calculix',model:'elastic',maxIncrements:s.increments,materials:undefined});
 if(model.nodes.length>10000||model.nodes.length*(s.increments+1)>1000000)throw Error('断裂任务最多 1 万节点，节点数乘保存帧数最多 100 万。');
 const materials=new Map((model.materials||[]).map(m=>[m.materialNo,m])),cards={};let nu,length;
 let maxEdge=0;
 const nodes=new Map(model.nodes.map(n=>[n.nodeNo,n]));
 for(const e of model.elements){
   const card=materialFor(s,materials.get(e.materialNo)?.id??String(e.materialNo??'legacy'));
   if(card.model!=='phaseField')throw Error('PhAST 断裂路径要求所有实体材料选择 AT2 相场断裂，不与塑性本构混算。');
   if(nu!==undefined&&(Math.abs(nu-e.poissonRatio)>1e-12||Math.abs(length-card.fractureLength)>1e-12))throw Error('当前 PhAST 多材料路径要求相同泊松比和相场长度；E 和断裂能可逐材料设置。');
   nu=e.poissonRatio;length=card.fractureLength;cards[e.materialNo??'legacy']=card;
   for(const [a,b]of [[e.node1,e.node2],[e.node2,e.node3],[e.node3,e.node1]]){const p=nodes.get(a),q=nodes.get(b);maxEdge=Math.max(maxEdge,Math.hypot(p.x-q.x,p.y-q.y));}
 }
 const used=new Set(model.elements.flatMap(e=>[e.node1,e.node2,e.node3]));
 if(model.nodes.some(n=>!used.has(n.nodeNo)))throw Error('断裂网格含未连接节点，请重新生成网格。');
 return {model,settings:s,materialSettings:cards,warnings:maxEdge>length/2?['网格边长大于相场长度的一半，请加密裂纹区域并做网格收敛检查。']:[]};
}
let active=false;
async function runFracture(model,raw,{signal,onProgress,timeoutMs=300000}={}){
 if(active)throw Error('已有断裂任务正在运行。');
 const request=prepareFracture(model,raw);active=true;const start=Date.now();let dir;
 try{
  await fs.access(python).catch(()=>{throw Error('项目内缺少 PhAST 运行时，请恢复 third_party/phast/runtime-win-x64 目录。');});
  const base=path.join(__dirname,'calculation-data/deformation');await fs.mkdir(base,{recursive:true});dir=await fs.mkdtemp(path.join(base,'fracture-'));
  const file=path.join(dir,'request.json');await fs.writeFile(file,JSON.stringify(request));
  onProgress?.({phase:'preparing',fraction:0,completedIncrements:0,elapsedMs:0,estimatedRemainingMs:null});
  let log='';
  try{await new Promise((resolve,reject)=>{
   if(signal?.aborted)return reject(Error('计算已取消。'));
   const key=Object.keys(process.env).find(name=>name.toUpperCase()==='PATH')||'Path';
   const system=process.env.SystemRoot||'C:\\Windows';
   const env={...process.env,[key]:[path.join(system,'System32'),system].join(path.delimiter),PYTHONUTF8:'1'};
   const child=spawn(python,['-u',path.join(__dirname,'scripts/phast-bridge.py'),file],{cwd:dir,windowsHide:true,env,stdio:['ignore','pipe','pipe']});let pending='',stopped='';
   const stop=msg=>{stopped=msg;child.kill();},abort=()=>stop('计算已取消。'),timer=setTimeout(()=>stop('计算超时。'),timeoutMs);signal?.addEventListener('abort',abort,{once:true});
   const consume=line=>{if(line.startsWith('TENSORA_PROGRESS ')){try{const p=JSON.parse(line.slice(17));onProgress?.({...p,elapsedMs:Date.now()-start});}catch{/* Full log retained for diagnosis. */}}};
   child.stdout.on('data',b=>{const t=b.toString('utf8');log=(log+t).slice(-2000000);pending+=t;let i;while((i=pending.indexOf('\n'))>=0){consume(pending.slice(0,i));pending=pending.slice(i+1);}});
   child.stderr.on('data',b=>{log=(log+b.toString()).slice(-2000000);});const cleanup=()=>{clearTimeout(timer);signal?.removeEventListener('abort',abort);};
   child.on('error',e=>{cleanup();reject(e);});child.on('close',code=>{cleanup();if(code||stopped)reject(Error(stopped||'PhAST: '+log.slice(-1800)));else resolve();});
  });}finally{await fs.writeFile(path.join(dir,'solver.log'),log);}
  const r=JSON.parse(await fs.readFile(path.join(dir,'result.json'),'utf8'));r.runId=path.basename(dir);r.completedAt=new Date().toISOString();r.warnings=request.warnings;
  if(!r.frames?.length||r.frames.some(f=>Object.values(f.damage).some(v=>!Number.isFinite(v[0])||v[0]<0||v[0]>1)))throw Error('PhAST 损伤结果无效。');
  await fs.writeFile(path.join(dir,'result.json'),JSON.stringify(r));onProgress?.({phase:r.completed?'complete':'partial',fraction:r.frames.at(-1).time,completedIncrements:r.frames.length-1,elapsedMs:Date.now()-start,estimatedRemainingMs:0});return r;
 }finally{active=false;}
}
module.exports={prepareFracture,runFracture,python};
