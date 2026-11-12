'use strict';

const fs=require('node:fs/promises');
const {existsSync}=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const {spawn}=require('node:child_process');
const {normalize,materialFor}=require('./deformation-settings');
const {tetData}=require('./solid3d');

const nativeRoot=path.join(__dirname,'third_party','code-aster','runtime-win-x64');
const nativePython=path.join(nativeRoot,'python.exe');

function nativeEnvironment(runtime,work){
  const library=path.join(runtime,'Library');
  const asterLibrary=path.join(library,'lib','aster');
  const lib=existsSync(asterLibrary)?asterLibrary:path.join(library,'lib');
  const pathKey=Object.keys(process.env).find(name=>name.toUpperCase()==='PATH')||'Path';
  const system=process.env.SystemRoot||'C:\\Windows';
  return {...process.env,
    [pathKey]:[runtime,path.join(library,'bin'),path.join(system,'System32'),system].join(path.delimiter),
    CONDA_PREFIX:runtime,ASTER_ROOT:runtime,RUNASTER_ROOT:library,ASTER_LIBDIR:lib,ASTER_ELEMENTSDIR:lib,
    ASTER_DATADIR:path.join(library,'share','aster'),ASTER_LOCALEDIR:path.join(library,'share','locale','aster'),
    PYTHONHOME:runtime,PYTHONPATH:[lib,path.join(runtime,'Lib','site-packages'),'.'].join(path.delimiter),
    PYTHONNOUSERSITE:'1',PYTHONUTF8:'1',PYTHONIOENCODING:'utf-8',OMP_NUM_THREADS:'1',TEMP:work,TMP:work};
}

async function prepareNativeWork(dir){
  const parents=[process.env.TENSORA_ASTER_TMP,os.tmpdir(),process.env.PUBLIC&&path.join(process.env.PUBLIC,'Documents')];
  let work;
  for(const parent of parents){
    if(!parent||!/^[\x20-\x7e]+$/.test(parent))continue;
    work=await fs.mkdtemp(path.join(parent,'tensora-aster-')).catch(()=>null);
    if(work)break;
  }
  if(!work)throw Error('Code_Aster 需要可写的英文临时目录，可通过 TENSORA_ASTER_TMP 指定。');
  const runtime=path.join(work,'runtime');
  const cleanup=async()=>{
    await fs.unlink(runtime).catch(()=>{});
    await fs.rm(work,{recursive:true,force:true,maxRetries:3}).catch(()=>{});
  };
  try{
    // The Windows Fortran file reader requires an ASCII path to its element catalogue.
    await fs.symlink(nativeRoot,runtime,'junction');
    await Promise.all(['job.export','job.comm','mesh.mail','request.json'].map(file=>fs.copyFile(path.join(dir,file),path.join(work,file))));
    return {work,runtime,cleanup};
  }catch(error){await cleanup();throw error;}
}

const exportFile=`P time_limit 1800
P memory_limit 2048
P mpi_nbcpu 1
P ncpus 1
F comm job.comm D 1
F mmed mesh.mail D 20
F libr request.json D 21
F libr frames.json R 80
`;
function prepareMazars(model,raw){
  const settings=normalize(raw);
  if(model.dimension!==3||settings.solver!=='aster'||settings.finiteStrain)throw Error('Code_Aster Mazars 需要三维小变形设置。');
  const cards=new Map(model.materials.map(material=>[material.materialNo,materialFor(settings,material.id)]));
  if([...cards.values()].some(card=>card.model!=='mazars'))throw Error('Code_Aster 计算要求所有体域使用 Mazars 材料卡。');
  const ids=new Set(),coordinates=new Map();
  const lines=['TITRE','TENSORA Mazars damage, SI units','FINSF','COOR_3D'];
  let maxForce=0;
  for(const node of model.nodes){
    const {nodeNo,x,y,z,forceX,forceY,forceZ}=node;
    if(!Number.isSafeInteger(nodeNo)||nodeNo<=0||ids.has(nodeNo)||![x,y,z,forceX,forceY,forceZ].every(Number.isFinite))throw Error('节点编号、坐标或载荷无效。');
    if(settings.fractureLoading==='displacement'&&((node.fixUx&&forceX)||(node.fixUy&&forceY)||(node.fixUz&&forceZ)))throw Error('位移加载方向与固定约束冲突，请调整载荷节点或约束。');
    maxForce=Math.max(maxForce,Math.abs(forceX),Math.abs(forceY),Math.abs(forceZ));
    ids.add(nodeNo);coordinates.set(nodeNo,[x,y,z]);
    lines.push(`N${nodeNo} ${x} ${y} ${z}`);
  }
  if(!maxForce)throw Error('模型没有非零载荷。');
  lines.push('FINSF','TETRA4');
  const materialSettings={};
  const groups=new Map();
  for(const element of model.elements){
    const {elementNo,node1,node2,node3,node4,materialNo,elasticModulus,poissonRatio}=element;
    const nodes=[node1,node2,node3,node4];
    if(!nodes.every(id=>ids.has(id))||new Set(nodes).size!==4)throw Error('单元编号或连接无效。');
    if(tetData(nodes.map(id=>coordinates.get(id))).orientation<0)[nodes[1],nodes[2]]=[nodes[2],nodes[1]];
    lines.push(`E${elementNo} ${nodes.map(id=>'N'+id).join(' ')}`);
    const group=`M${materialNo}`;
    if(!groups.has(group)){
      groups.set(group,[]);
      materialSettings[group]={elasticModulus,poissonRatio,card:cards.get(materialNo)};
    }
    groups.get(group).push(`E${elementNo}`);
  }
  lines.push('FINSF');
  for(const [group,elements] of groups){lines.push('GROUP_MA',group,...elements,'FINSF');}
  lines.push('FIN');
  const frameBudget=Math.floor(1500000/model.nodes.length);
  const outputFrequency=settings.increments<=frameBudget?1:Math.ceil(settings.increments/(frameBudget-1));
  return {meshText:lines.join('\n')+'\n',settings,materialSettings,maxForce,outputFrequency};
}

async function runMazars(model,raw,{signal,onProgress}={}){
  signal?.throwIfAborted();
  if(!existsSync(nativePython))throw Error('项目内缺少 Code_Aster 运行时，请恢复 third_party/code-aster/runtime-win-x64 目录。');
  const started=Date.now();
  const progress=(phase,fraction)=>onProgress?.({phase,fraction,elapsedMs:Date.now()-started});
  progress('preparing',0);
  const {meshText,settings,materialSettings,maxForce,outputFrequency}=prepareMazars(model,raw);
  const base=path.join(__dirname,'calculation-data','deformation');
  await fs.mkdir(base,{recursive:true});
  const dir=await fs.mkdtemp(path.join(base,'aster-'));
  const write=(file,data)=>fs.writeFile(path.join(dir,file),data);
  await Promise.all([
    write('job.export',exportFile),write('mesh.mail',meshText),
    fs.copyFile(path.join(__dirname,'scripts','aster-mazars.comm'),path.join(dir,'job.comm')),
    write('request.json',JSON.stringify({model,settings,materialSettings,maxForce,outputFrequency}))
  ]);
  signal?.throwIfAborted();
  const log=await fs.open(path.join(dir,'solver.log'),'w');
  let stage;
  let exitCode;
  try{
    stage=await prepareNativeWork(dir);
    const command=path.join(stage.runtime,'python.exe');
    const args=['-m','run_aster.run_aster_main','job.export'];
    progress('solving',0);
    signal?.throwIfAborted();
    exitCode=await new Promise((resolve,reject)=>{
      const child=spawn(command,args,{cwd:stage.work,env:nativeEnvironment(stage.runtime,stage.work),windowsHide:true,stdio:['ignore',log.fd,log.fd]});
      const abort=()=>{
        if(!child.pid)return;
        const taskkill=path.join(process.env.SystemRoot||'C:\\Windows','System32','taskkill.exe');
        const killer=spawn(taskkill,['/F','/T','/PID',String(child.pid)],{windowsHide:true,stdio:'ignore'});
        killer.on('error',()=>child.kill());
      };
      const timer=setTimeout(abort,30*60*1000);
      signal?.addEventListener('abort',abort,{once:true});
      let failure;
      child.once('error',error=>{failure=error;});
      child.once('close',code=>{
        clearTimeout(timer);signal?.removeEventListener('abort',abort);
        if(failure)reject(failure);else resolve(code);
      });
    });
    if(exitCode===0)await fs.copyFile(path.join(stage.work,'frames.json'),path.join(dir,'frames.json'));
  }finally{
    await log.close();
    await stage?.cleanup();
  }
  signal?.throwIfAborted();
  const runId=path.basename(dir);
  if(exitCode!==0)throw Error(`Code_Aster 求解失败，请查看任务日志 ${runId}。`);
  progress('processing',1);
  const frames=JSON.parse(await fs.readFile(path.join(dir,'frames.json'),{encoding:'utf8',signal}));
  if(!frames.length||Math.abs(frames.at(-1).time-1)>1e-8)throw Error('求解未完成全部载荷增量；不发布部分结果。');
  const result={ok:true,completed:true,runId,solver:'Code_Aster 18.1.11',model,settings,frames,outputFrequency,damageEvolution:true,
    materialSettings:Object.fromEntries(Object.entries(materialSettings).map(([group,{card}])=>[group.slice(1),card]))};
  await write('result.json',JSON.stringify(result));
  progress('complete',1);
  return result;
}

module.exports={runMazars};
