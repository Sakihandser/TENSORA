'use strict';
// Fluid–structure interaction workflow:
//   two-way : SU2 8.6 multizone (flow + FEA + mesh deformation, block Gauss–Seidel);
//   one-way : SU2 flow with rigid walls -> MFEM 4.10 elasticity under the wall loads.
// All flow, structural and coupling computations are done by these external
// programs; this module stages files, launches them and reads their outputs.
const fs=require('node:fs/promises');
const {existsSync}=require('node:fs');
const path=require('node:path');
const {buildFsiInputs,mfemInput}=require('./fsi-deck');
const {prepare}=require('./fsi-model');
const {readVtk,execute}=require('./blast3d-runner');
const {runSph,openCourantAvailable}=require('./fsi-sph');

const SU2=path.join(__dirname,'third_party','su2','runtime-win-x64','SU2_CFD.exe');
const MFEM=path.join(__dirname,'third_party','mfem','runtime-win-x64','mfem_fsi.exe');
const RUNS=path.join(__dirname,'calculation-data','fsi');
const KEEP_RUNS=8;
const FLUID_FIELDS=['pressure','vx','vy','vz','vmag','vorticity','q','density','temperature','mach','cp'];
const SOLID_FIELDS=['sxx','syy','szz','sxy','syz','sxz','vm'];
const COMMON_FIELDS=['ux','uy','uz','umag'];

function available(){return {su2:existsSync(SU2),mfem:existsSync(MFEM),opencourant:openCourantAvailable()};}

// SU2 ASCII restart / surface CSV: "PointID","x","y",... rows.
async function readCsv(file){
  const text=await fs.readFile(file,'latin1');
  const rows=text.split(/\r?\n/).filter(line=>line.trim());
  const header=rows.shift().split(',').map(h=>h.replace(/"/g,'').trim());
  const columns=Object.fromEntries(header.map(h=>[h,new Float64Array(rows.length)]));
  rows.forEach((row,i)=>row.split(',').forEach((v,k)=>{if(k<header.length)columns[header[k]][i]=Number(v);}));
  return {header,columns,count:rows.length};
}
const field=(vtk,name)=>vtk.pointData[Object.keys(vtk.pointData).find(k=>k.toLowerCase()===name.toLowerCase())];
const flowPressure=(restart,vtk)=>restart.columns.Pressure||(vtk&&field(vtk,'Pressure')?.values);

async function pruneRuns(runsDirectory){
  const entries=await fs.readdir(runsDirectory,{withFileTypes:true}).catch(()=>[]);
  const runs=[];
  for(const entry of entries)if(entry.isDirectory()&&entry.name.startsWith('run-')){
    const stat=await fs.stat(path.join(runsDirectory,entry.name)).catch(()=>null);
    if(stat)runs.push({name:entry.name,time:stat.mtimeMs});
  }
  runs.sort((a,b)=>b.time-a.time);
  for(const run of runs.slice(KEEP_RUNS))await fs.rm(path.join(runsDirectory,run.name),{recursive:true,force:true}).catch(()=>{});
}

// Element (cell-constant) stresses -> area/volume-weighted nodal averages.
function nodalAverage(model,cells,values,width,n){
  const sums=new Float64Array(n*width),weight=new Float64Array(n);
  cells.forEach((c,k)=>{
    const p=model.cells[c].map(id=>model.nodes[id]);
    let w;
    if(model.dimension===2)w=Math.abs((p[1][0]-p[0][0])*(p[2][1]-p[0][1])-(p[1][1]-p[0][1])*(p[2][0]-p[0][0]))/2;
    else{
      const u=[0,1,2].map(i=>p[1][i]-p[0][i]),v=[0,1,2].map(i=>p[2][i]-p[0][i]),t=[0,1,2].map(i=>p[3][i]-p[0][i]);
      w=Math.abs(u[0]*(v[1]*t[2]-v[2]*t[1])-u[1]*(v[0]*t[2]-v[2]*t[0])+u[2]*(v[0]*t[1]-v[1]*t[0]))/6;
    }
    for(const id of model.cells[c]){weight[id]+=w;for(let j=0;j<width;j++)sums[id*width+j]+=w*values[k*width+j];}
  });
  return {sums,weight};
}

function emptyFields(n,keys){return Object.fromEntries(keys.map(k=>[k,new Float32Array(n).fill(NaN)]));}

// Fill nodal fields of one saved instant from SU2 outputs.
function su2Frame(model,inputs,{flowVtk,flowRestart,solidVtk,solidRestart}){
  const n=model.nodes.length,dim=model.dimension,split=inputs.split;
  const fields=emptyFields(n,[...COMMON_FIELDS,...FLUID_FIELDS,...SOLID_FIELDS,'flowUx','flowUy','flowUz']);
  const fluidNodes=split.fluid.nodes,solidNodes=split.solid.nodes;
  // SU2 restart keeps full-precision coordinates. Compressible runs write
  // conserved variables in the restart and pressure and velocity in the VTK.
  const fx=flowRestart.columns.x,fy=flowRestart.columns.y,fz=flowRestart.columns.z;
  const pressure=flowPressure(flowRestart,flowVtk),vel=['Velocity_x','Velocity_y','Velocity_z'].map(k=>flowRestart.columns[k]);
  const vort=flowVtk&&field(flowVtk,'Vorticity'),dens=flowVtk&&field(flowVtk,'Density'),temp=flowVtk&&field(flowVtk,'Temperature'),
    mach=flowVtk&&field(flowVtk,'Mach'),cp=flowVtk&&field(flowVtk,'Pressure_Coefficient'),
    vtkVel=flowVtk&&field(flowVtk,'Velocity'),q=flowVtk&&field(flowVtk,'Q_Criterion');
  const vortAxes=dim===3&&flowVtk?['x','y','z'].map(axis=>field(flowVtk,'Vorticity_'+axis)):null;
  for(let i=0;i<fluidNodes.length;i++){
    const g=fluidNodes[i],p=model.nodes[g];
    if(fx&&fy){
      fields.flowUx[g]=fields.ux[g]=fx[i]-p[0];
      fields.flowUy[g]=fields.uy[g]=fy[i]-p[1];
      if(dim===3&&fz)fields.flowUz[g]=fields.uz[g]=fz[i]-p[2];
      if(dim===2)fields.uz[g]=0;
    }
    fields.pressure[g]=pressure?.[i]??NaN;
    for(let d=0;d<3;d++){
      const key=['vx','vy','vz'][d];
      fields[key][g]=dim===2&&d===2?0:vel[d]?vel[d][i]:vtkVel?vtkVel.values[i*3+d]:NaN;
    }
    fields.vmag[g]=Math.hypot(fields.vx[g],fields.vy[g],fields.vz[g]);
    if(vort)fields.vorticity[g]=vort.width===3?Math.hypot(vort.values[i*3],vort.values[i*3+1],vort.values[i*3+2])*(dim===2?Math.sign(vort.values[i*3+2])||1:1):vort.values[i];
    else if(vortAxes?.every(Boolean))fields.vorticity[g]=Math.hypot(...vortAxes.map(axis=>axis.values[i]));
    if(q)fields.q[g]=q.values[i];
    if(dens)fields.density[g]=dens.values[i];
    if(temp)fields.temperature[g]=temp.values[i];
    if(mach)fields.mach[g]=mach.values[i];
    if(cp)fields.cp[g]=cp.values[i];
  }
  // Solid: displacements (restart: full precision) and nodal stresses (VTK).
  const disp=['Displacement_x','Displacement_y','Displacement_z'].map(k=>solidRestart?.columns[k]);
  const vtkDisp=solidVtk&&field(solidVtk,'Displacement');
  const stress={sxx:'Sxx',syy:'Syy',szz:'Szz',sxy:'Sxy',syz:'Syz',sxz:'Sxz',vm:'Von_Mises_Stress'};
  const stressData=Object.fromEntries(Object.entries(stress).map(([k,name])=>[k,solidVtk&&field(solidVtk,name)]));
  for(let i=0;i<solidNodes.length;i++){
    const g=solidNodes[i];
    for(let d=0;d<3;d++){
      const key=['ux','uy','uz'][d];
      fields[key][g]=disp[d]?disp[d][i]:vtkDisp?vtkDisp.values[i*3+d]:0;
      if(d===2&&dim===2)fields.uz[g]=0;
    }
    for(const [key,data] of Object.entries(stressData))fields[key][g]=data?data.values[i]:(key==='szz'||key==='syz'||key==='sxz')&&dim===2?0:NaN;
  }
  for(let i=0;i<n;i++){
    if(Number.isFinite(fields.ux[i]))fields.umag[i]=Math.hypot(fields.ux[i],fields.uy[i],fields.uz[i]||0);
  }
  return fields;
}

function presentFields(fields,{compressible,dimension}){
  return Object.keys(fields).filter(key=>{
    if(dimension===2&&['uz','vz','syz','sxz'].includes(key))return false;
    if(!compressible&&['density','temperature','mach'].includes(key))return false;
    return fields[key].some(v=>Number.isFinite(v));
  });
}

// SU2 prints "Error in ...", a dashed rule, then the message lines.
async function su2Error(dir){
  await new Promise(resolve=>setTimeout(resolve,100));
  const lines=(await fs.readFile(path.join(dir,'solver.log'),'latin1').catch(()=>'')).split(/\r?\n/);
  const at=lines.findIndex(line=>/^Error in /.test(line.trim()));
  if(at<0)return '';
  const message=[];
  for(const line of lines.slice(at+1,at+8)){
    const text=line.trim();
    if(/^-+$/.test(text))continue;
    if(/Error Exit/.test(text))break;
    if(text)message.push(text);
  }
  return message.length?`SU2：${message.join(' ')}`:'';
}

// Screen rows "|  time|  outer|  bgs0|  bgs1| minvol|" (two-way) or "| inner| rms...|" (one-way).
const ROW=/^\|\s*(-?\d+)\|\s*(-?\d+)\|\s*([-+0-9.eE]+)\|\s*([-+0-9.eE]+)\|/;

// Explicit transient path: OpenCourant SPH fluid + Lagrangian structure (3D).
async function runFsiSph(payload,{signal,onProgress,timeoutMs,runsDirectory}){
  if(!payload?.solid)throw Error('SPH 显式流固耦合只用于三维模型，请开启“三维计算”。');
  if(!available().opencourant)throw Error('项目内缺少 OpenCourant 运行时，请恢复 third_party/opencourant/runtime-win-x64。');
  const started=Date.now();
  const progress=(phase,fraction,extra={})=>onProgress?.({phase,fraction,elapsedMs:Date.now()-started,...extra});
  progress('preparing',0);
  await fs.mkdir(runsDirectory,{recursive:true});
  await pruneRuns(runsDirectory);
  const dir=await fs.mkdtemp(path.join(runsDirectory,'run-'));
  const runId=path.basename(dir);
  const log=(await fs.open(path.join(dir,'solver.log'),'w')).createWriteStream();
  try{
    const result=await runSph(payload,{dir,runId,log,signal,progress,timeoutMs});
    const summary={ok:true,runId,engine:'sph',solver:'OpenCourant 20261011 SPH 显式流固耦合',dimension:3,
      settings:{...result.settings,engine:'sph'},meta:{...result.meta,converged:null},completed:result.completed,termination:result.termination,
      fields:result.meshFields,particleFields:result.particleFields,particleCount:result.particleCount,
      nodeCount:payload.solid.mesh.nodes.length,frames:result.frames,history:[],elapsedMs:Date.now()-started};
    await fs.writeFile(path.join(dir,'summary.json'),JSON.stringify(summary));
    progress('complete',1);
    return summary;
  }finally{log.end();}
}

async function runFsi(payload,{signal,onProgress,timeoutMs=2*60*60*1000,runsDirectory=RUNS}={}){
  if(payload?.settings?.engine==='sph')return runFsiSph(payload,{signal,onProgress,timeoutMs,runsDirectory});
  const state=available();
  if(!state.su2)throw Error('项目内缺少 SU2 运行时，请恢复 third_party/su2/runtime-win-x64/SU2_CFD.exe。');
  const started=Date.now();
  const progress=(phase,fraction,extra={})=>onProgress?.({phase,fraction,elapsedMs:Date.now()-started,...extra});
  progress('preparing',0);
  const {model,settings:prepared}=prepare(payload);
  const inputs=buildFsiInputs(model,prepared,payload?.fluid);
  const s=inputs.settings;
  if(s.engine==='oneway'&&!state.mfem)throw Error('项目内缺少 MFEM 单向耦合程序 third_party/mfem/runtime-win-x64/mfem_fsi.exe。');
  await fs.mkdir(runsDirectory,{recursive:true});
  await pruneRuns(runsDirectory);
  const dir=await fs.mkdtemp(path.join(runsDirectory,'run-'));
  const runId=path.basename(dir);
  const log=(await fs.open(path.join(dir,'solver.log'),'w')).createWriteStream();
  const work=path.join(dir,'work');
  try{
    await fs.mkdir(work);
    await Promise.all(Object.entries(inputs.files).map(([name,text])=>fs.writeFile(path.join(work,name),text)));
    const env={...process.env,TMP:work,TEMP:work,OMP_NUM_THREADS:String(s.threads)};
    const history=[];
    let frames=[],present=null,mfem=null;
    const writeFrame=async(fields,time,index)=>{
      present??=presentFields(fields,{compressible:inputs.meta.compressible,dimension:model.dimension});
      const stats={};
      for(const key of present){let min=Infinity,max=-Infinity;for(const v of fields[key])if(Number.isFinite(v)){if(v<min)min=v;if(v>max)max=v;}stats[key]=[min,max];}
      await fs.writeFile(path.join(dir,`frame-${String(index).padStart(4,'0')}.bin`),Buffer.concat(present.map(key=>Buffer.from(fields[key].buffer))));
      frames.push({index,time,stats});
    };
    if(s.engine==='su2'){
      progress('su2',0);
      log.write('=== SU2 multizone FSI ===\n');
      const total=s.analysis==='transient'?s.steps:s.outerIterations;
      const code=await execute(SU2,['-t',String(s.threads),'config.cfg'],{cwd:work,env,signal,timeoutMs,log,onLine:line=>{
        const m=line.match(ROW);
        if(!m)return;
        const timeIter=Number(m[1]),outer=Number(m[2]),bgsFluid=Number(m[3]),bgsSolid=Number(m[4]);
        history.push({timeIter,outer,bgsFluid,bgsSolid});
        const done=s.analysis==='transient'?timeIter+outer/s.outerIterations:outer+1;
        progress('su2',Math.min(1,done/total),{timeIter,outer,bgsFluid,bgsSolid,time:s.analysis==='transient'?(timeIter+1)*s.timeStep:undefined});
      }});
      const names=await fs.readdir(work);
      const pairs=[];
      for(const name of names){
        const m=name.match(/^flow_0(?:_(\d+))?\.vtk$/);
        if(!m)continue;
        const suffix=m[1]?`_${m[1]}`:'';
        if(names.includes(`solid_1${suffix}.vtk`))pairs.push({iter:m[1]?Number(m[1]):s.outerIterations,suffix});
      }
      pairs.sort((a,b)=>a.iter-b.iter);
      if(!pairs.length)throw Error(`SU2 没有输出结果（退出码 ${code}）。${await su2Error(dir)||'请查看任务日志 '+runId+'。'}`);
      progress('processing',0);
      for(let k=0;k<pairs.length;k++){
        signal?.throwIfAborted();
        const {suffix,iter}=pairs[k];
        const [flowVtk,solidVtk,flowRestart,solidRestart]=await Promise.all([
          readVtk(path.join(work,`flow_0${suffix}.vtk`)),readVtk(path.join(work,`solid_1${suffix}.vtk`)),
          readCsv(path.join(work,`restart_flow_0${suffix}.csv`)).catch(()=>null),readCsv(path.join(work,`restart_solid_1${suffix}.csv`)).catch(()=>null)]);
        if(!flowRestart)throw Error('SU2 流体结果文件缺失。');
        const fields=su2Frame(model,inputs,{flowVtk,flowRestart,solidVtk,solidRestart});
        await writeFrame(fields,s.analysis==='transient'?(iter+1)*s.timeStep:null,k);
        progress('processing',(k+1)/pairs.length);
      }
      const last=history.at(-1);
      const converged=s.analysis==='steady'&&last?Math.max(last.bgsFluid,last.bgsSolid)<=Math.max(s.convergence,-8)+1e-9:null;
      if(code!==0&&s.analysis==='transient'&&(frames.at(-1)?.time??0)<s.steps*s.timeStep*0.999)
        inputs.meta.stoppedEarly=true;
      inputs.meta.exitCode=code;inputs.meta.converged=converged;
    }else{
      // ------------------------------------------------ one-way: SU2 -> MFEM
      progress('su2',0);
      log.write('=== SU2 flow (rigid walls) ===\n');
      const inner=Number(inputs.files['config_flow.cfg'].match(/INNER_ITER= (\d+)/)[1]);
      const code=await execute(SU2,['-t',String(s.threads),'config_flow.cfg'],{cwd:work,env,signal,timeoutMs,log,onLine:line=>{
        const m=line.match(/^\|\s*(\d+)\|\s*([-+0-9.eE]+)\|/);
        if(!m)return;
        const it=Number(m[1]),res=Number(m[2]);
        history.push({timeIter:0,outer:it,bgsFluid:res,bgsSolid:NaN});
        progress('su2',Math.min(1,(it+1)/inner),{inner:it,residual:res});
      }});
      if(!existsSync(path.join(work,'flow.vtk'))||!existsSync(path.join(work,'restart_flow.csv')))throw Error(`SU2 流场计算没有输出结果（退出码 ${code}）。${await su2Error(dir)||'请查看任务日志 '+runId+'。'}`);
      const [flowVtk,flowRestart]=await Promise.all([readVtk(path.join(work,'flow.vtk')),readCsv(path.join(work,'restart_flow.csv'))]);
      progress('mfem',0);
      // Wall pressure and SU2 skin friction (tau = Cf * q_ref) at the interface vertices.
      const q=inputs.meta.dynamicPressure;
      const cf=field(flowVtk,'Skin_Friction_Coefficient');
      // Same p_inf as FREESTREAM_PRESSURE (rho*R*T when the reference pressure is 0).
      const reference=inputs.meta.freestreamPressure||0;
      const pressure=flowPressure(flowRestart,flowVtk);
      const loads=new Map();
      const interfaceNodes=new Set(inputs.split.interfaceFluid.flat());
      inputs.split.fluid.nodes.forEach((g,i)=>{
        if(!interfaceNodes.has(g))return;
        if(!Number.isFinite(pressure?.[i]))throw Error('SU2 结果缺少有效的流固界面压力。');
        const values=[pressure[i]-reference];
        for(let d=0;d<model.dimension;d++)values.push(cf&&q>0?cf.values[i*3+d]*q:0);
        loads.set(g,values);
      });
      const {mesh,data,obliqueRollers}=mfemInput(model,inputs.split,inputs.materials,loads,s);
      await fs.writeFile(path.join(work,'fsi.mesh'),mesh);await fs.writeFile(path.join(work,'fsi.dat'),data);
      log.write('\n=== MFEM elasticity under fluid loads ===\n');
      const mcode=await execute(MFEM,['.'],{cwd:work,env,signal,timeoutMs:30*60*1000,log});
      const text=await fs.readFile(path.join(work,'fsi.out'),'utf8').catch(()=>'');
      const rows=text.trim().split(/\r?\n/);
      const [ok,iterations,finalNorm,,essential]=rows[0]?.split(/\s+/).map(Number)||[];
      if(mcode!==0||ok!==1)throw Error(`MFEM 结构求解失败（退出码 ${mcode}，迭代 ${iterations??'-'} 次）。请检查结构约束是否足以消除刚体位移。`);
      const resultant=rows[1].split(/\s+/).map(Number);
      const nv=inputs.split.solid.nodes.length,dim=model.dimension;
      const fields=su2Frame(model,inputs,{flowVtk,flowRestart,solidVtk:null,solidRestart:null});
      const displacement=rows.slice(2,2+nv).map(r=>r.split(/\s+/).map(Number));
      inputs.split.solid.nodes.forEach((g,i)=>{
        fields.ux[g]=displacement[i][0];fields.uy[g]=displacement[i][1];fields.uz[g]=dim===3?displacement[i][2]:0;
        fields.umag[g]=Math.hypot(fields.ux[g],fields.uy[g],fields.uz[g]);
      });
      // Fluid nodes keep zero displacement (rigid walls in the flow solution).
      inputs.split.fluid.nodes.forEach(g=>{if(!inputs.split.solid.map.has(g)){fields.ux[g]=0;fields.uy[g]=0;fields.uz[g]=0;fields.umag[g]=0;}});
      const width=dim===2?3:6,stress=new Float64Array(inputs.split.solidCells.length*width);
      rows.slice(2+nv,2+nv+inputs.split.solidCells.length).forEach((r,k)=>r.split(/\s+/).map(Number).forEach((v,j)=>{stress[k*width+j]=v;}));
      const {sums,weight}=nodalAverage(model,inputs.split.solidCells,stress,width,model.nodes.length);
      const order=dim===2?['sxx','syy','sxy']:['sxx','syy','szz','sxy','sxz','syz'];
      const nu=new Float64Array(model.nodes.length);
      inputs.split.solidCells.forEach(c=>{const m=inputs.materials.find(x=>x.id===String(model.cellMaterials[c]));for(const id of model.cells[c])nu[id]=m.nu;});
      for(const g of inputs.split.solid.nodes){
        if(!(weight[g]>0))continue;
        order.forEach((key,j)=>{fields[key][g]=sums[g*width+j]/weight[g];});
        if(dim===2){fields.syz[g]=0;fields.sxz[g]=0;fields.szz[g]=s.plane==='strain'?nu[g]*(fields.sxx[g]+fields.syy[g]):0;}
        const [a,b,c,xy,yz,xz]=['sxx','syy','szz','sxy','syz','sxz'].map(k=>fields[k][g]);
        fields.vm[g]=Math.sqrt(((a-b)**2+(b-c)**2+(c-a)**2)/2+3*(xy**2+yz**2+xz**2));
      }
      await writeFrame(fields,null,0);
      mfem={iterations,finalNorm,essentialDofs:essential,resultant,obliqueRollers};
      inputs.meta.exitCode=code;inputs.meta.converged=history.length?history.at(-1).bgsFluid<=s.convergence+1e-9:null;
    }
    if(!frames.length)throw Error('没有读取到有效结果帧。');
    const finite=frames.every(f=>Object.values(f.stats).every(([a,b])=>a===Infinity||(Number.isFinite(a)&&Number.isFinite(b))));
    if(!finite)throw Error('结果含非有限数值（计算发散）。请减小时间步、增大松弛或检查边界条件。');
    const resultSettings=payload.solid?{...s,volumeRoles:prepared.volumeRoles||{}}:s;
    const summary={ok:true,runId,engine:s.engine,solver:s.engine==='su2'?'SU2 8.6.0 多区流固耦合':'SU2 8.6.0 流场 + MFEM 4.10 结构',
      dimension:model.dimension,settings:resultSettings,meta:inputs.meta,mfem,history:history.slice(-4000),
      fields:present,nodeCount:model.nodes.length,frames,elapsedMs:Date.now()-started,
      zones:{fluid:inputs.split.fluid.nodes.length,solid:inputs.split.solid.nodes.length}};
    await fs.writeFile(path.join(dir,'summary.json'),JSON.stringify(summary));
    // Keep the solver inputs for inspection.
    await Promise.all(Object.keys(inputs.files).map(name=>fs.copyFile(path.join(work,name),path.join(dir,name)).catch(()=>{})));
    progress('complete',1);
    return summary;
  }finally{
    log.end();
    if(!process.env.TENSORA_KEEP_FSI_WORK)await fs.rm(work,{recursive:true,force:true,maxRetries:3}).catch(()=>{});
  }
}

const RUN_ID=/^run-[A-Za-z0-9_-]{4,40}$/;
async function readFrame(runId,index,{runsDirectory=RUNS}={}){
  if(!RUN_ID.test(runId)||!Number.isSafeInteger(index)||index<0)throw Error('无效的流固耦合结果请求。');
  return fs.readFile(path.join(runsDirectory,runId,`frame-${String(index).padStart(4,'0')}.bin`));
}
async function readSummary(runId){
  if(!RUN_ID.test(runId))throw Error('无效的流固耦合结果请求。');
  return JSON.parse(await fs.readFile(path.join(RUNS,runId,'summary.json'),'utf8'));
}

module.exports={runFsi,readFrame,readSummary,available,RUNS,FLUID_FIELDS,SOLID_FIELDS};
