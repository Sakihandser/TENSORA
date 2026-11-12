'use strict';
// 3D blast workflow: MFEM initial equilibrium -> OpenCourant Starter/Engine ->
// OpenCourant anim_to_vtk -> nodal frames for the TENSORA 3D viewer.
// All mechanics are computed by the external executables; this module only
// stages files, launches processes, and reads their native outputs.
const fs=require('node:fs/promises');
const {existsSync,createReadStream}=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const readline=require('node:readline');
const {spawn}=require('node:child_process');
const {buildDecks}=require('./blast3d-deck');
const {tetData,principalValues}=require('./solid3d');

const OPENCOURANT=path.join(__dirname,'third_party','opencourant','runtime-win-x64');
const MFEM=path.join(__dirname,'third_party','mfem','runtime-win-x64','mfem_prestress.exe');
const RUNS=path.join(__dirname,'calculation-data','blast3d');
const KEEP_RUNS=6;
const FIELD_KEYS=['ux','uy','uz','umag','vx','vy','vz','vmag','sxx','syy','szz','sxy','syz','sxz','vm','pressure','s1',
  'exx','eyy','ezz','exy','eyz','exz','equivalentStrain','e1','plasticStrain','damage','failureDamage','eroded'];

function available(){
  return {opencourant:existsSync(path.join(OPENCOURANT,'exec','starter_win64.exe'))&&existsSync(path.join(OPENCOURANT,'exec','engine_win64.exe')),
    mfem:existsSync(MFEM)};
}

// Intel Fortran runtimes and the hm_reader expect ASCII paths. The project may
// live in a CJK folder, so jobs run in an ASCII temp folder with a junction.
async function asciiWork(prefix){
  const parents=[process.env.TENSORA_BLAST3D_TMP,os.tmpdir(),process.env.PUBLIC&&path.join(process.env.PUBLIC,'Documents')];
  for(const parent of parents){
    if(!parent||!/^[\x20-\x7e]+$/.test(parent))continue;
    const work=await fs.mkdtemp(path.join(parent,prefix)).catch(()=>null);
    if(work)return work;
  }
  throw Error('三维爆破需要可写的英文临时目录，可通过 TENSORA_BLAST3D_TMP 指定。');
}
function environment(runtime,threads){
  const pathKey=Object.keys(process.env).find(name=>name.toUpperCase()==='PATH')||'Path';
  const system=process.env.SystemRoot||'C:\\Windows';
  return {...process.env,RAD_CFG_PATH:path.join(runtime,'hm_cfg_files'),RAD_H3D_PATH:path.join(runtime,'extlib','h3d','lib','win64'),
    KMP_STACKSIZE:'400m',OMP_NUM_THREADS:String(threads),
    [pathKey]:[path.join(runtime,'extlib','hm_reader','win64'),path.join(runtime,'extlib','intelOneAPI_runtime','win64'),
      path.join(runtime,'extlib','h3d','lib','win64'),path.join(system,'System32'),system].join(path.delimiter)};
}
function execute(command,args,{cwd,env,signal,timeoutMs,log,onLine}){
  return new Promise((resolve,reject)=>{
    signal?.throwIfAborted();
    const child=spawn(command,args,{cwd,env,windowsHide:true,stdio:['ignore','pipe','pipe']});
    let buffer='',timedOut=false,failure;
    const consume=chunk=>{
      log?.write(chunk);
      buffer+=chunk.toString('latin1');
      const lines=buffer.split(/\r?\n/);buffer=lines.pop();
      for(const line of lines)onLine?.(line);
    };
    child.stdout.on('data',consume);child.stderr.on('data',consume);
    const kill=()=>{
      if(!child.pid)return;
      const taskkill=path.join(process.env.SystemRoot||'C:\\Windows','System32','taskkill.exe');
      const killer=spawn(taskkill,['/F','/T','/PID',String(child.pid)],{windowsHide:true,stdio:'ignore'});
      killer.on('error',()=>child.kill());
    };
    const timer=setTimeout(()=>{timedOut=true;kill();},timeoutMs);
    signal?.addEventListener('abort',kill,{once:true});
    child.once('error',error=>{failure=error;});
    child.once('close',code=>{
      clearTimeout(timer);signal?.removeEventListener('abort',kill);
      if(signal?.aborted)return reject(signal.reason||Error('计算已取消。'));
      if(timedOut)return reject(Error('计算超时。'));
      if(failure)return reject(failure);
      resolve(code);
    });
  });
}

// ---------------------------------------------------------------- MFEM stage
async function runPrestress(work,mesh,decks,{signal,timeoutMs,log}){
  const {force,fixed,rockTet,partOfVolume,materials}=decks;
  const slots=[],slotOf=new Map();
  const elementIndex=new Int32Array(mesh.tets.length).fill(-1);
  const rows=[];
  mesh.tets.forEach((tet,i)=>{
    if(!rockTet[i])return;
    const part=partOfVolume.get(String(mesh.tetVolumes[i]));
    if(!slotOf.has(part.materialId)){
      const m=materials.find(item=>item.id===part.materialId);
      slotOf.set(part.materialId,slots.length+1);
      slots.push({lambda:m.E*m.nu/((1+m.nu)*(1-2*m.nu)),mu:m.E/(2*(1+m.nu))});
    }
    const nodes=[...tet];
    if(tetData(nodes.map(n=>mesh.nodes[n])).orientation<0)[nodes[1],nodes[2]]=[nodes[2],nodes[1]];
    elementIndex[i]=rows.length;
    rows.push(`${slotOf.get(part.materialId)} 4 ${nodes.join(' ')}`);
  });
  const rockNodes=new Uint8Array(mesh.nodes.length);
  mesh.tets.forEach((tet,i)=>{if(rockTet[i])for(const n of tet)rockNodes[n]=1;});
  const ess=[];
  let fixedRock=0;
  for(let i=0;i<mesh.nodes.length;i++)for(let d=0;d<3;d++){
    // Nodes outside the rock carry no stiffness in the static stage.
    if(!rockNodes[i]||fixed[i*3+d]){ess.push(i*3+d);if(rockNodes[i])fixedRock++;}
  }
  if(fixedRock<6)throw Error('“先静力平衡”需要足够的位移约束以消除刚体位移，请在三维计算页添加约束或改选“起爆时突然施加外载荷”。');
  const meshText=['MFEM mesh v1.0','','dimension','3','','elements',String(rows.length),...rows,'','boundary','0','','vertices',String(mesh.nodes.length),'3',
    ...mesh.nodes.map(p=>p.map(v=>v.toPrecision(17)).join(' ')),''].join('\n');
  const forces=[];
  for(let i=0;i<force.length;i++)forces.push(rockNodes[Math.floor(i/3)]?force[i]:0);
  const data=[String(slots.length),...slots.map(s=>`${s.lambda} ${s.mu}`),String(ess.length),ess.join(' '),'1e-10 50000',forces.join(' ')].join('\n');
  await Promise.all([fs.writeFile(path.join(work,'prestress.mesh'),meshText),fs.writeFile(path.join(work,'prestress.dat'),data)]);
  const code=await execute(MFEM,[work],{cwd:work,env:process.env,signal,timeoutMs,log});
  const text=await fs.readFile(path.join(work,'prestress.out'),'utf8').catch(()=>'');
  const lines=text.trim().split(/\r?\n/);
  const [converged,iterations,finalNorm]=lines[0]?.split(/\s+/).map(Number)||[];
  if(code!==0||converged!==1)throw Error(`MFEM 初始平衡求解失败（退出码 ${code}，迭代 ${iterations??'-'} 次）。请检查约束是否足以消除刚体位移。`);
  const stress=new Float64Array(rows.length*6);
  for(let k=0;k<rows.length;k++){
    const values=lines[k+1].split(/\s+/).map(Number);
    stress.set(values,k*6);
  }
  if(!stress.every(Number.isFinite))throw Error('MFEM 初始应力含非有限数值。');
  return {stress,elementIndex,iterations,finalNorm};
}

// ------------------------------------------------------------- VTK reading
// anim_to_vtk writes legacy ASCII VTK: POINTS, CELLS, POINT_DATA and CELL_DATA.
async function readVtk(file){
  const stream=createReadStream(file,{encoding:'latin1'});
  const lines=readline.createInterface({input:stream,crlfDelay:Infinity});
  const out={time:null,points:null,ids:null,cells:null,cellIds:null,pointData:{},cellData:{}};
  let mode=null,target=null,remaining=0,section=null,array=null,offset=0,width=1;
  for await (const raw of lines){
    const line=raw.trim();
    if(!line)continue;
    if(remaining>0){
      const values=line.split(/\s+/);
      for(const v of values){
        if(offset>=array.length)break;
        array[offset++]=Number(v);
      }
      if(offset>=array.length){
        remaining=0;
        if(mode==='points')out.points=array;
        else if(mode==='cells')out.cells=array;
        else if(mode==='types'){/* not needed */}
        else if(section==='field')(out.fieldData??={})[target]={width,values:array};
        else (section==='point'?out.pointData:out.cellData)[target]={width,values:array};
      }
      continue;
    }
    const words=line.split(/\s+/);
    const key=words[0].toUpperCase();
    if(key==='POINTS'){mode='points';array=new Float64Array(Number(words[1])*3);offset=0;remaining=1;}
    else if(key==='CELLS'){mode='cells';array=new Float64Array(Number(words[2]));offset=0;remaining=1;}
    else if(key==='CELL_TYPES'){mode='types';array=new Float64Array(Number(words[1]));offset=0;remaining=1;}
    else if(key==='POINT_DATA'){section='point';out.pointCount=Number(words[1]);}
    else if(key==='CELL_DATA'){section='cell';out.cellCount=Number(words[1]);}
    else if(key==='SCALARS'){mode='data';target=words[1];width=Number(words[3]||1);}
    else if(key==='LOOKUP_TABLE'){const count=section==='point'?out.pointCount:out.cellCount;array=new Float64Array(count*width);offset=0;remaining=1;}
    else if(key==='VECTORS'){mode='data';target=words[1];width=3;array=new Float64Array((section==='point'?out.pointCount:out.cellCount)*3);offset=0;remaining=1;}
    else if(key==='TENSORS'){mode='data';target=words[1];width=9;array=new Float64Array((section==='point'?out.pointCount:out.cellCount)*9);offset=0;remaining=1;}
    else if(key==='FIELD'){mode='field';section='field';}
    else if(mode==='field'&&words.length===4&&/^\d+$/.test(words[1])&&/^\d+$/.test(words[2])){
      target=words[0];width=Number(words[1]);array=new Float64Array(width*Number(words[2]));offset=0;remaining=1;
    }
  }
  if(out.fieldData?.TIME)out.time=out.fieldData.TIME.values[0];
  return out;
}

// anim_to_vtk prefixes solid element fields with "3DELEM_".
function pick(data,names){
  const keys=Object.keys(data),norm=k=>k.toLowerCase().replace(/^3delem_/,'');
  for(const name of names){const hit=keys.find(k=>norm(k)===name.toLowerCase());if(hit)return data[hit];}
  return null;
}

// Convert one VTK frame to nodal fields on TENSORA's node numbering.
function frameFields(vtk,model){
  const n=model.nodeCount;
  const fields=Object.fromEntries(FIELD_KEYS.map(k=>[k,new Float32Array(n)]));
  const pointIds=pick(vtk.pointData,['NODE_ID']);
  if(!pointIds)throw Error('anim_to_vtk 输出缺少 NODE_ID。');
  const disp=pick(vtk.pointData,['Displacement']),vel=pick(vtk.pointData,['Velocity']);
  for(let p=0;p<pointIds.values.length;p++){
    const i=pointIds.values[p]-1;
    if(i<0||i>=n)continue;
    if(disp){fields.ux[i]=disp.values[p*3];fields.uy[i]=disp.values[p*3+1];fields.uz[i]=disp.values[p*3+2];}
    if(vel){fields.vx[i]=vel.values[p*3];fields.vy[i]=vel.values[p*3+1];fields.vz[i]=vel.values[p*3+2];}
    fields.umag[i]=Math.hypot(fields.ux[i],fields.uy[i],fields.uz[i]);
    fields.vmag[i]=Math.hypot(fields.vx[i],fields.vy[i],fields.vz[i]);
  }
  // Element values -> volume-weighted nodal averages for surface contours.
  const cellIds=pick(vtk.cellData,['ELEMENT_ID']);
  const tensors={s:pick(vtk.cellData,['Stress']),e:pick(vtk.cellData,['Strain'])};
  const scalar={vm:pick(vtk.cellData,['Von_Mises']),pressure:pick(vtk.cellData,['Pressure']),damage:pick(vtk.cellData,['Damage']),
    failureDamage:pick(vtk.cellData,['MAX_DAMAGE_ELEMENT']),plasticStrain:pick(vtk.cellData,['Plastic_Strain']),alive:pick(vtk.cellData,['EROSION_STATUS'])};
  const averaged=['sxx','syy','szz','sxy','syz','sxz','exx','eyy','ezz','exy','eyz','exz','vm','pressure','damage','failureDamage','plasticStrain','alive'];
  const weight=new Float64Array(n),sums=Object.fromEntries(averaged.map(k=>[k,new Float64Array(n)]));
  const element=new Map();
  if(cellIds)for(let c=0;c<cellIds.values.length;c++)element.set(cellIds.values[c],c);
  const tensorKeys={s:['sxx','syy','szz','sxy','syz','sxz'],e:['exx','eyy','ezz','exy','eyz','exz']};
  // VTK symmetric tensors are row-major 3x3; shear strain is the tensor component (gamma/2).
  const order=[0,4,8,1,5,2];
  const values={};
  for(let e=0;e<model.tets.length;e++){
    const tet=model.tets[e];
    if(!tet)continue;
    const c=cellIds?element.get(e+1):undefined;
    if(c===undefined)continue;
    const w=model.volumes[e];
    for(const key of averaged)values[key]=NaN;
    for(const [kind,data] of Object.entries(tensors))if(data&&data.width===9)tensorKeys[kind].forEach((key,k)=>{values[key]=data.values[c*9+order[k]];});
    for(const [key,data] of Object.entries(scalar))if(data)values[key]=data.values[c*data.width];
    for(const id of tet){
      weight[id]+=w;
      for(const key of averaged)if(Number.isFinite(values[key]))sums[key][id]+=w*values[key];
    }
  }
  for(let i=0;i<n;i++)if(weight[i]>0)for(const key of averaged)if(key!=='alive')fields[key][i]=sums[key][i]/weight[i];
  if(scalar.alive)for(let i=0;i<n;i++)if(weight[i]>0)fields.eroded[i]=1-sums.alive[i]/weight[i];
  for(let i=0;i<n;i++){
    if(tensors.s){
      const sx=fields.sxx[i],sy=fields.syy[i],sz=fields.szz[i],txy=fields.sxy[i],tyz=fields.syz[i],txz=fields.sxz[i];
      if(!scalar.vm)fields.vm[i]=Math.sqrt(((sx-sy)**2+(sy-sz)**2+(sz-sx)**2)/2+3*(txy**2+tyz**2+txz**2));
      if(!scalar.pressure)fields.pressure[i]=-(sx+sy+sz)/3;
      fields.s1[i]=principalValues([sx,sy,sz,txy,tyz,txz])[0];
    }
    if(tensors.e){
      const ex=fields.exx[i],ey=fields.eyy[i],ez=fields.ezz[i],gxy=fields.exy[i],gyz=fields.eyz[i],gxz=fields.exz[i];
      fields.equivalentStrain[i]=Math.sqrt(2*((ex-ey)**2+(ey-ez)**2+(ez-ex)**2)/9+4*(gxy**2+gyz**2+gxz**2)/3);
      fields.e1[i]=principalValues([ex,ey,ez,gxy,gyz,gxz])[0];
    }
  }
  const present=FIELD_KEYS.filter(key=>{
    if(['ux','uy','uz','umag'].includes(key))return !!disp;
    if(['vx','vy','vz','vmag'].includes(key))return !!vel;
    if(tensorKeys.s.includes(key)||key==='s1')return !!tensors.s;
    if(tensorKeys.e.includes(key)||key==='equivalentStrain'||key==='e1')return !!tensors.e;
    if(key==='vm'||key==='pressure')return !!tensors.s||!!scalar[key];
    if(key==='eroded')return !!scalar.alive&&(model.erosion??model.failure);
    if(key==='damage')return !!scalar.damage&&model.materialDamage;
    if(key==='failureDamage')return !!scalar.failureDamage&&model.failure;
    return !!scalar[key];
  });
  return {fields,present};
}

async function pruneRuns(){
  const entries=await fs.readdir(RUNS,{withFileTypes:true}).catch(()=>[]);
  const runs=[];
  for(const entry of entries)if(entry.isDirectory()&&entry.name.startsWith('run-')){
    const stat=await fs.stat(path.join(RUNS,entry.name)).catch(()=>null);
    if(stat)runs.push({name:entry.name,time:stat.mtimeMs});
  }
  runs.sort((a,b)=>b.time-a.time);
  for(const run of runs.slice(KEEP_RUNS))await fs.rm(path.join(RUNS,run.name),{recursive:true,force:true}).catch(()=>{});
}

// Engine progress lines: " NC=  223500 T= 1.9946E-05 DT= 8.9243E-11 ERR=  0.0% ..."
const ENGINE_LINE=/NC=\s*(\d+)\s+T=\s*([-+0-9.Ee]+)\s+DT=\s*([-+0-9.Ee]+)/;

async function runBlast3d(payload,{signal,onProgress,timeoutMs=60*60*1000}={}){
  const state=available();
  if(!state.opencourant)throw Error('项目内缺少 OpenCourant 运行时，请恢复 third_party/opencourant/runtime-win-x64。');
  const solid=payload?.solid;
  const started=Date.now();
  const progress=(phase,fraction,extra={})=>onProgress?.({phase,fraction,elapsedMs:Date.now()-started,...extra});
  progress('preparing',0);
  let decks=buildDecks(solid,payload?.settings);
  const s=decks.settings,mesh=solid.mesh;
  await fs.mkdir(RUNS,{recursive:true});
  await pruneRuns();
  const dir=await fs.mkdtemp(path.join(RUNS,'run-'));
  const runId=path.basename(dir);
  const log=(await fs.open(path.join(dir,'solver.log'),'w')).createWriteStream();
  const work=await asciiWork('tensora-blast3d-');
  const runtime=path.join(work,'runtime');
  let prestress=null;
  try{
    await fs.symlink(OPENCOURANT,runtime,'junction');
    if(s.initialState==='prestress'&&decks.meta.applyLoads){
      if(!state.mfem)throw Error('项目内缺少 MFEM 初始平衡程序 third_party/mfem/runtime-win-x64/mfem_prestress.exe。');
      progress('prestress',0);
      log.write('=== MFEM initial equilibrium ===\n');
      prestress=await runPrestress(work,mesh,decks,{signal,timeoutMs:30*60*1000,log});
      decks=buildDecks(solid,payload.settings,{prestress});
      progress('prestress',1,{iterations:prestress.iterations});
    }
    await Promise.all([fs.writeFile(path.join(work,'model_0000.rad'),decks.starter),fs.writeFile(path.join(work,'model_0001.rad'),decks.engine)]);
    const env=environment(runtime,s.threads);
    const exec=name=>path.join(runtime,'exec',name);
    progress('starter',0);
    log.write('\n=== OpenCourant Starter ===\n');
    const starterCode=await execute(exec('starter_win64.exe'),['-i','model_0000.rad','-np','1','-nt',String(s.threads)],{cwd:work,env,signal,timeoutMs:20*60*1000,log});
    const restart=(await fs.readdir(work)).some(name=>/^model_0000_\d+\.rst$/i.test(name));
    if(starterCode!==0||!restart){
      const out=await fs.readFile(path.join(work,'model_0000.out'),'latin1').catch(()=>'');
      await fs.copyFile(path.join(work,'model_0000.out'),path.join(dir,'model_0000.out')).catch(()=>{});
      const errors=out.split(/\r?\n/).map((line,i,all)=>/ERROR ID/.test(line)?all.slice(i,i+4).join(' ').replace(/\s+/g,' ').trim():null).filter(Boolean).slice(0,4);
      throw Error(`OpenCourant Starter 未通过模型检查（退出码 ${starterCode}）。${errors.join('；')||'请查看任务日志 '+runId+'。'}`);
    }
    progress('engine',0);
    log.write('\n=== OpenCourant Engine ===\n');
    let lastTime=0;
    const engineCode=await execute(exec('engine_win64.exe'),['-i','model_0001.rad','-nt',String(s.threads)],{cwd:work,env,signal,timeoutMs,log,onLine:line=>{
      const m=line.match(ENGINE_LINE);
      if(m){const t=Number(m[2]);if(Number.isFinite(t)&&t>=lastTime){lastTime=t;progress('engine',Math.min(1,t/s.endTime),{time:t,cycle:Number(m[1]),dt:Number(m[3])});}}
    }});
    const engineOut=await fs.readFile(path.join(work,'model_0001.out'),'latin1').catch(()=>'');
    await fs.writeFile(path.join(dir,'model_0001.out'),engineOut);
    const normal=/NORMAL TERMINATION/i.test(engineOut);
    const animations=(await fs.readdir(work)).filter(name=>/^modelA\d{3,}$/.test(name)).sort();
    if(!animations.length)throw Error(`OpenCourant Engine 没有输出动画帧（退出码 ${engineCode}）。请查看任务日志 ${runId}。`);
    progress('processing',0);
    const tets=mesh.tets.map((tet,i)=>decks.partOfVolume.has(String(mesh.tetVolumes[i]))?tet:null);
    const volumes=mesh.tets.map(tet=>Math.abs(tetData(tet.map(n=>mesh.nodes[n])).volume));
    const model={nodeCount:mesh.nodes.length,tets,volumes,failure:decks.meta.materials.some(m=>m.failure),
      erosion:decks.meta.materials.some(m=>m.failure||m.erodes),materialDamage:decks.meta.materials.some(m=>['jh2','hjc'].includes(m.law))};
    const frames=[];
    let present=null;
    for(let k=0;k<animations.length;k++){
      signal?.throwIfAborted();
      const vtkName=animations[k]+'.vtk';
      const vtkStream=(await fs.open(path.join(work,vtkName),'w')).createWriteStream();
      let code;
      try{code=await execute(exec('anim_to_vtk_win64.exe'),[animations[k]],{cwd:work,env,signal,timeoutMs:10*60*1000,log:vtkStream});}
      finally{await new Promise(resolve=>vtkStream.end(resolve));}
      if(code!==0)throw Error('anim_to_vtk 转换失败：'+animations[k]);
      const vtk=await readVtk(path.join(work,vtkName));
      await fs.rm(path.join(work,vtkName),{force:true});
      const {fields,present:keys}=frameFields(vtk,model);
      present??=keys;
      const time=Number.isFinite(vtk.time)?vtk.time:k*decks.meta.animDt;
      const stats={};
      for(const key of present){let min=Infinity,max=-Infinity;for(const v of fields[key]){if(v<min)min=v;if(v>max)max=v;}stats[key]=[min,max];}
      const buffer=Buffer.concat(present.map(key=>Buffer.from(fields[key].buffer)));
      await fs.writeFile(path.join(dir,`frame-${String(k).padStart(4,'0')}.bin`),buffer);
      frames.push({index:k,time,stats});
      progress('processing',(k+1)/animations.length);
    }
    // The Engine also reports NORMAL TERMINATION when it stops early (e.g. after
    // element inversion), so completion is judged on the simulated time and on
    // finite, physically bounded fields.
    const reached=frames.length&&frames.at(-1).time>=s.endTime-0.5*decks.meta.animDt;
    const diverged=frames.findIndex(f=>Object.entries(f.stats).some(([key,[min,max]])=>!Number.isFinite(min)||!Number.isFinite(max)
      ||(['ux','uy','uz','umag'].includes(key)&&Math.max(Math.abs(min),Math.abs(max))>1e3)
      ||(['sxx','syy','szz','sxy','syz','sxz','vm','pressure'].includes(key)&&Math.max(Math.abs(min),Math.abs(max))>1e15)));
    if(diverged===0)throw Error('OpenCourant 计算从第一帧起发散，请检查材料参数、网格质量和载荷。');
    if(diverged>0)frames.splice(diverged);
    const completed=normal&&reached&&diverged<0;
    const message=diverged>0?`第 ${diverged+1} 帧起数值发散（单元翻转或时间步过小），只保留此前 ${diverged} 帧。`
      :!normal?'OpenCourant Engine 未正常结束，只保留已经输出的帧。'
      :!reached?`OpenCourant Engine 在 ${(frames.at(-1).time*1e6).toFixed(1)} μs 提前停止（通常为单元严重畸变），未达到设定时长。`:null;
    const summary={ok:true,runId,solver:'OpenCourant 20261011 (OpenRadioss continuation)',prestressSolver:prestress?'MFEM 4.10':null,
      completed,termination:completed?null:{code:engineCode,message},
      settings:{...s,explosive:s.explosive?{id:s.explosive.id,name:s.explosive.name}:undefined},meta:decks.meta,
      prestress:prestress?{iterations:prestress.iterations,finalNorm:prestress.finalNorm}:null,
      fields:present,nodeCount:mesh.nodes.length,frames,elapsedMs:Date.now()-started};
    await fs.writeFile(path.join(dir,'summary.json'),JSON.stringify(summary));
    await Promise.all(['model_0000.rad','model_0001.rad','model_0000.out'].map(name=>fs.copyFile(path.join(work,name),path.join(dir,name)).catch(()=>{})));
    progress('complete',1);
    return summary;
  }finally{
    log.end();
    await fs.unlink(runtime).catch(()=>{});
    if(!process.env.TENSORA_KEEP_BLAST3D_WORK)await fs.rm(work,{recursive:true,force:true,maxRetries:3}).catch(()=>{});
  }
}

const RUN_ID=/^run-[A-Za-z0-9_-]{4,40}$/;
async function readFrame(runId,index){
  if(!RUN_ID.test(runId)||!Number.isSafeInteger(index)||index<0)throw Error('无效的三维爆破结果请求。');
  return fs.readFile(path.join(RUNS,runId,`frame-${String(index).padStart(4,'0')}.bin`));
}
async function readSummary(runId){
  if(!RUN_ID.test(runId))throw Error('无效的三维爆破结果请求。');
  return JSON.parse(await fs.readFile(path.join(RUNS,runId,'summary.json'),'utf8'));
}

module.exports={runBlast3d,readFrame,readSummary,readVtk,frameFields,available,FIELD_KEYS,RUNS};
