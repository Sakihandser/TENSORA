'use strict';
// CalculiX 2.22 adapter of the dynamics workspace: modal analysis (*FREQUENCY),
// harmonic response (*STEADY STATE DYNAMICS on the modal basis) and implicit
// transient dynamics (*DYNAMIC, alpha method, Rayleigh *DAMPING). TENSORA only
// writes the input deck, launches the bundled ccx.exe (PaStiX / ARPACK, threaded
// through OMP_NUM_THREADS and CCX_NPROC_*) and reads the .dat / .frd output.
const fs=require('node:fs/promises');
const path=require('node:path');
const {spawn}=require('node:child_process');
const {createReadStream}=require('node:fs');
const {createInterface}=require('node:readline');
const DS=require('./dynamics-settings');
const {meshCpuThreads,threadedEnvironment}=require('./cpu-threads');

const executable=path.join(__dirname,'third_party','calculix','bin','ccx.exe');
// Quadratic edge order of C3D10 (nodes 5..10) in CalculiX.
const EDGES3=[[0,1],[1,2],[2,0],[0,3],[1,3],[2,3]];
const STRESS_KEYS=['sxx','syy','szz','sxy','syz','sxz'];

function fmt(v){
  if(!Number.isFinite(v))throw Error('CalculiX 卡片数值无效。');
  if(v===0)return '0';
  const text=String(Number(v.toPrecision(12)));
  return text.length<=20?text:v.toExponential(10);
}
const vonMises=(a,b,c,xy,yz,xz)=>Math.sqrt(((a-b)**2+(b-c)**2+(c-a)**2)/2+3*(xy*xy+yz*yz+xz*xz));

// Rigid-body modes appear when the restraints cannot remove every rigid motion.
function rigidModeCount(m){
  const {count,nodePart}=DS.components(m.elements,m.coords.length);
  const spatial=m.dimension===3,dofs=spatial?6:3;
  if(!m.fixed.some(Boolean))return dofs*count;
  const parts=Array.from({length:count},()=>({origin:null,size:0,basis:[]}));
  // Local coordinates make the constraint rank invariant to the model origin and units.
  for(let i=0;i<m.coords.length;i++){
    const part=parts[nodePart[i]];
    if(!part)continue;
    const p=m.coords[i],origin=part.origin??=p;
    for(let d=0;d<m.dimension;d++)part.size=Math.max(part.size,Math.abs(p[d]-origin[d]));
  }
  for(let i=0;i<m.coords.length;i++){
    const part=parts[nodePart[i]];
    if(!part||part.basis.length===dofs)continue;
    for(let d=0;d<m.dimension;d++){
      if(!m.fixed[3*i+d])continue;
      const scale=part.size||1;
      const [x,y,z]=m.coords[i].map((v,k)=>(v-part.origin[k])/scale);
      // A restraint removes a component of translation + rotation cross position.
      const row=spatial?[[1,0,0,0,z,-y],[0,1,0,-z,0,x],[0,0,1,y,-x,0]][d]
        :d===0?[1,0,-y]:[0,1,x];
      for(const unit of part.basis){
        let dot=0;
        for(let k=0;k<dofs;k++)dot+=row[k]*unit[k];
        for(let k=0;k<dofs;k++)row[k]-=dot*unit[k];
      }
      const norm=Math.hypot(...row);
      if(norm>1e-10)part.basis.push(row.map(v=>v/norm));
    }
  }
  return parts.reduce((sum,part)=>sum+dofs-part.basis.length,0);
}

// 2D models are written as one layer of 3D wedges (C3D6 / C3D15) of thickness t.
// CalculiX's own plane elements expand internally through MPCs, and their concentrated
// loads are not carried correctly into *STEADY STATE DYNAMICS, so the extrusion is
// explicit: plane strain fixes every out-of-plane displacement, plane stress keeps a
// thin free layer (fixed only at the mid-plane against rigid z motion). Loads are per
// unit thickness and reported masses are divided by t.
function layerThickness(m){
  let min=Infinity;
  for(const e of m.elements)for(let a=0;a<3;a++){const p=m.coords[e[a]],q=m.coords[e[(a+1)%3]];min=Math.min(min,Math.hypot(p[0]-q[0],p[1]-q[1]));}
  return Number((0.5*min).toPrecision(3));
}

// Solid mesh written to CalculiX: nodes, connectivity, restraints and nodal loads.
// The first N nodes are always the TENSORA model nodes (results are read on them).
function solidMesh(m,s){
  const quadratic=s.elementOrder==='quadratic',N=m.coords.length;
  const nodes=m.coords.map(p=>[...p]);
  const fixed=[],loads=[];
  const fix=(node,d)=>fixed.push([node,d]);
  if(m.dimension===3){
    const midOf=new Map();
    const mid=(i,j)=>{const a=i<j?i:j,b=i<j?j:i,key=a*N+b;let id=midOf.get(key);if(id===undefined){const pa=nodes[a],pb=nodes[b];id=nodes.length;nodes.push([(pa[0]+pb[0])/2,(pa[1]+pb[1])/2,(pa[2]+pb[2])/2]);midOf.set(key,id);
      for(let d=0;d<3;d++)if(m.fixed[a*3+d]&&m.fixed[b*3+d])fix(id,d);}return id;};
    const elements=m.elements.map(e=>quadratic?[...e,...EDGES3.map(([a,b])=>mid(e[a],e[b]))]:[...e]);
    for(let i=0;i<N;i++)for(let d=0;d<3;d++){if(m.fixed[i*3+d])fix(i,d);else if(m.force[i*3+d])loads.push([i,d,m.force[i*3+d]]);}
    return {nodes,elements,fixed,loads,type:quadratic?'C3D10':'C3D4',thickness:null};
  }
  const t=layerThickness(m),strain=s.planeMode===1;
  for(let i=0;i<N;i++)nodes.push([m.coords[i][0],m.coords[i][1],t]);          // top layer N..2N-1
  const edgeMid=new Map(),vertical=new Map();
  const add=(p,fixXY)=>{nodes.push(p);const id=nodes.length-1;fixXY.forEach((on,d)=>{if(on)fix(id,d);});if(strain)fix(id,2);return id;};
  const inPlane=(i,j,top)=>{
    const a=i<j?i:j,b=i<j?j:i,key=(a*N+b)*2+top;
    let id=edgeMid.get(key);
    if(id===undefined){const pa=m.coords[a],pb=m.coords[b];id=add([(pa[0]+pb[0])/2,(pa[1]+pb[1])/2,top?t:0],[0,1].map(d=>m.fixed[a*3+d]&&m.fixed[b*3+d]));edgeMid.set(key,id);}
    return id;
  };
  const vert=i=>{if(!vertical.has(i)){const id=add([m.coords[i][0],m.coords[i][1],t/2],[0,1].map(d=>m.fixed[i*3+d]));if(!strain)fix(id,2);vertical.set(i,id);}return vertical.get(i);};
  const elements=m.elements.map(([a,b,c])=>{
    const corners=[a,b,c,a+N,b+N,c+N];
    if(!quadratic)return corners;
    return [...corners,inPlane(a,b,0),inPlane(b,c,0),inPlane(c,a,0),inPlane(a,b,1),inPlane(b,c,1),inPlane(c,a,1),vert(a),vert(b),vert(c)];
  });
  for(let i=0;i<N;i++){
    for(const node of [i,i+N]){for(let d=0;d<2;d++)if(m.fixed[i*3+d])fix(node,d);if(strain)fix(node,2);}
    // Linear plane stress: hold the bottom face against rigid z motion; the layer thins freely upward.
    if(!strain&&!quadratic)fix(i,2);
    // Unit-thickness load F carried by the layer: t*F, split 1/2-1/2 (linear) or 1/6-2/3-1/6 (quadratic).
    for(let d=0;d<2;d++){
      const f=m.force[i*3+d];if(!f||m.fixed[i*3+d])continue;
      if(quadratic){loads.push([i,d,f*t/6],[i+N,d,f*t/6],[vert(i),d,f*t*2/3]);}
      else loads.push([i,d,f*t/2],[i+N,d,f*t/2]);
    }
  }
  return {nodes,elements,fixed,loads,type:quadratic?'C3D15':'C3D6',thickness:t};
}

function deck(m,s){
  const spatial=m.dimension===3,quadratic=s.elementOrder==='quadratic';
  for(const mat of m.materials)if(!(mat.rho>0))throw Error(`${mat.name}：动力学计算需要材料密度。`);
  const solid=solidMesh(m,s);
  const lines=['*HEADING','TENSORA structural dynamics; SI units','*NODE'];
  solid.nodes.forEach((p,i)=>lines.push(`${i+1},${fmt(p[0])},${fmt(p[1])},${fmt(p[2])}`));
  const byMaterial=m.materials.map(()=>[]);
  for(let e=0;e<m.elementMaterial.length;e++)byMaterial[m.elementMaterial[e]]?.push(e);
  m.materials.forEach((mat,k)=>{
    const ids=byMaterial[k];
    if(!ids.length)return;
    lines.push(`*ELEMENT,TYPE=${solid.type},ELSET=M${k+1}`);
    for(const e of ids){
      const row=[e+1,...solid.elements[e].map(n=>n+1)];
      // Data lines hold at most 16 entries; C3D15 continues on a second line.
      if(row.length<=16)lines.push(row.join(','));else lines.push(row.slice(0,16).join(',')+',',row.slice(16).join(','));
    }
  });
  m.materials.forEach((mat,k)=>{
    lines.push(`*MATERIAL,NAME=M${k+1}`,'*ELASTIC',`${fmt(mat.E)},${fmt(mat.nu)}`,'*DENSITY',fmt(mat.rho));
    // *DAMPING (ALPHA, BETA) is a global Rayleigh damping read under a material card (direct integration).
    if(k===0&&s.analysis==='transient'&&s.transientMethod==='direct'&&(s.rayleighAlpha>0||s.rayleighBeta>0))lines.push(`*DAMPING,ALPHA=${fmt(s.rayleighAlpha)},BETA=${fmt(s.rayleighBeta)}`);
  });
  m.materials.forEach((mat,k)=>{if(byMaterial[k].length)lines.push(`*SOLID SECTION,ELSET=M${k+1},MATERIAL=M${k+1}`);});
  const unique=new Set(solid.fixed.map(([n,d])=>`${n+1},${d+1},${d+1}`));
  if(unique.size){
    lines.push('*BOUNDARY');
    for(const constraint of unique)lines.push(constraint);
  }
  const loads=solid.loads.map(([n,d,f])=>[n+1,d+1,f]);
  const output='';
  const rigid=rigidModeCount(m);
  const meta={elementType:solid.type,quadratic,solverNodes:solid.nodes.length,rigidModes:rigid,loadedDofs:loads.length,fixedDofs:unique.size,
    sectionThickness:spatial?null:solid.thickness,plane:spatial?null:s.planeMode===1?'strain':'stress'};
  if(s.analysis==='modal'){
    // Unrestrained models: two spare pairs absorb spurious negative eigenvalues.
    meta.requestedModes=s.modes+(rigid?rigid+2:0);
    lines.push('*STEP','*FREQUENCY,STORAGE=YES',String(meta.requestedModes),`*NODE FILE${output}`,'U',`*EL FILE${output}`,'S','*END STEP');
  }else if(s.analysis==='harmonic'){
    if(!loads.length)throw Error('谐响应分析需要模型中的载荷作为简谐力幅值，请在结构上施加载荷。');
    const modes=s.harmonicModes+rigid;
    meta.requestedModes=modes;
    lines.push('*STEP','*FREQUENCY,STORAGE=YES',String(modes),'*END STEP',
      '*STEP','*STEADY STATE DYNAMICS',`${fmt(s.freqMin)},${fmt(s.freqMax)},${s.freqPoints},1`,
      '*MODAL DAMPING',`1,${modes},${fmt(s.dampingRatio)}`,'*CLOAD');
    for(const [n,d,f] of loads)lines.push(`${n},${d},${fmt(f)}`);
    lines.push(`*NODE FILE${output}`,'PU',`*EL FILE${output}`,'S','*END STEP');
  }else{
    if(!loads.length)throw Error('瞬态动力学需要模型中的载荷，请在结构上施加载荷（时程由载荷曲线给定）。');
    const steps=Math.ceil(Number((s.endTime/s.timeStep).toPrecision(14)));
    const every=Math.max(1,Math.ceil(steps/(s.frames-1)));
    const samples=DS.loadSamples(s.load,s.endTime);
    meta.steps=steps;meta.timeStep=s.transientMethod==='modal'?s.endTime/steps:s.timeStep;
    meta.outputEvery=every;meta.loadSamples=samples;
    lines.push('*AMPLITUDE,NAME=LOADHIST');
    for(let i=0;i<samples.length;i+=4)lines.push(samples.slice(i,i+4).map(([t,v])=>`${fmt(t)},${fmt(v)}`).join(','));
    if(s.transientMethod==='modal'){
      // Mode superposition: the eigenmodes are extracted once, then the modal equations are integrated.
      const modes=s.transientModes+rigid;
      meta.requestedModes=modes;
      lines.push('*STEP','*FREQUENCY,STORAGE=YES',String(modes),'*END STEP',
        `*STEP,INC=${steps+100}`,'*MODAL DYNAMIC',`${fmt(meta.timeStep)},${fmt(s.endTime)}`);
      if(s.rayleighAlpha>0||s.rayleighBeta>0)lines.push('*MODAL DAMPING,RAYLEIGH',`,,${fmt(s.rayleighAlpha)},${fmt(s.rayleighBeta)}`);
    }else lines.push(`*STEP,INC=${steps+100}`,'*DYNAMIC,DIRECT',`${fmt(s.timeStep)},${fmt(s.endTime)}`);
    lines.push('*CLOAD,AMPLITUDE=LOADHIST');
    for(const [n,d,f] of loads)lines.push(`${n},${d},${fmt(f)}`);
    lines.push(`*NODE FILE${output},FREQUENCY=${every}`,'U,V',`*EL FILE${output},FREQUENCY=${every}`,'S','*END STEP');
  }
  return {input:lines.join('\n')+'\n',meta};
}

// ---------------------------------------------------------------- output
function number(text){
  const n=Number(text);
  if(Number.isFinite(n))return n;
  const s=String(text).trim();
  return s?Number(s.replace(/[dD]/,'E')):NaN;
}
// Streams an FRD file and calls onSet({key,value,blocks}) for every result set.
// Only the first `count` nodes (the corner nodes of the TENSORA mesh) are kept.
async function readFrdSets(file,count,onSet,signal){
  const stream=createReadStream(file,{encoding:'latin1',signal});
  const lines=createInterface({input:stream,crlfDelay:Infinity});
  let current=null,block=null;
  const flush=async()=>{if(current){const done=current;current=null;await onSet(done);}};
  try{
    for await(const line of lines){
      if(line.startsWith('  100C')){
        const key=line.slice(6,12).trim(),value=number(line.slice(12,24));
        if(!current||current.key!==key){await flush();current={key,value,blocks:{}};}
        block=null;continue;
      }
      if(!current)continue;
      if(line.startsWith(' -4')){
        const name=line.slice(3).trim().split(/\s+/)[0];
        block={name,width:0,values:null,seen:0};
        current.blocks[name]=block;continue;
      }
      if(block&&line.startsWith(' -1')){
        const id=Number(line.slice(3,13));
        if(!(id>=1&&id<=count))continue;
        const len=line.length;
        const width=Math.floor((len-12)/12);
        if(width<=0)continue;
        if(!block.values){block.width=width;block.values=new Float64Array(count*width).fill(NaN);}
        const cols=Math.min(width,block.width),base=(id-1)*block.width,out=block.values;
        for(let k=0,p=13;k<cols;k++,p+=12)out[base+k]=number(line.slice(p,p+12));
        block.seen++;
      }else if(line.startsWith(' -3'))block=null;
    }
    await flush();
  }finally{stream.destroy();}
}

// Eigenvalue table, participation factors and effective modal mass from the .dat file.
function parseModalDat(text){
  const lines=text.split(/\r?\n/);
  const table=(title,width)=>{
    const at=lines.findIndex(line=>line.includes(title));
    if(at<0)return [];
    const rows=[];
    for(let i=at+1;i<lines.length;i++){
      const t=lines[i].trim();
      if(!t){if(rows.length)break;continue;}
      const parts=t.split(/\s+/);
      if(!/^\d+$/.test(parts[0])){if(rows.length)break;continue;}
      rows.push(parts.slice(0,width+1).map(number));
    }
    return rows;
  };
  const eigen=table('E I G E N V A L U E   O U T P U T',4);
  const participation=table('P A R T I C I P A T I O N   F A C T O R S',6);
  const effective=table('E F F E C T I V E   M O D A L   M A S S',6);
  const totalAt=lines.findIndex(line=>line.includes('T O T A L   E F F E C T I V E   M A S S'));
  let total=null;
  if(totalAt>=0)for(let i=totalAt+1;i<lines.length;i++){const parts=lines[i].trim().split(/\s+/);if(parts.length>=6&&parts.every(p=>Number.isFinite(number(p)))){total=parts.slice(0,6).map(number);break;}}
  return {eigen,participation,effective,total};
}

// Eigenpairs in solver order. With an unrestrained structure the shift-invert Lanczos
// can return a large negative eigenvalue besides the near-zero rigid-body modes; such a
// pair is not a vibration mode and is marked `spurious` (dropped from the results).
function modeTable(dat,rigid){
  const pairs=dat.eigen.map(r=>({mode:r[0],eigenvalue:r[1],frequency:r[3]}));
  const maxEigen=pairs.reduce((max,f)=>Math.max(max,f.eigenvalue),0);
  const maxFrequency=pairs.reduce((max,f)=>Math.max(max,Math.abs(f.frequency)),0);
  const threshold=Math.max(1e-3,1e-4*maxFrequency);
  const spuriousPair=f=>f.eigenvalue<0&&Math.abs(f.eigenvalue)>1e-6*maxEigen;
  const nearZero=pairs.filter(f=>!spuriousPair(f)&&Math.abs(f.frequency)<threshold);
  nearZero.sort((a,b)=>Math.abs(a.eigenvalue)-Math.abs(b.eigenvalue));
  const rigidPairs=new Set(nearZero.slice(0,rigid));
  const partByMode=new Map(dat.participation.map(r=>[r[0],r]));
  const effByMode=new Map(dat.effective.map(r=>[r[0],r]));
  return pairs.map(f=>{
    const p=partByMode.get(f.mode),e=effByMode.get(f.mode);
    const spurious=spuriousPair(f);
    const isRigid=rigidPairs.has(f);
    return {mode:f.mode,frequency:isRigid||spurious?0:f.frequency,period:!isRigid&&!spurious&&f.frequency>0?1/f.frequency:null,rigid:isRigid,spurious,
      participation:p?p.slice(1,4):null,effectiveMass:e?e.slice(1,4):null,rotationalMass:e?e.slice(4,7):null};
  });
}
// Keeps the rigid-body modes and the first `count` elastic modes (indices into the table).
function keptModes(table,count){
  const kept=[];let elastic=0;
  table.forEach((mode,i)=>{if(mode.spurious)return;if(mode.rigid)kept.push(i);else if(elastic<count){kept.push(i);elastic++;}});
  return kept;
}

// --------------------------------------------------------------- execution
function staTime(text,step=null){
  let latest=0;
  for(const line of text.split(/\r?\n/)){
    const p=line.trim().split(/\s+/);
    if(p.length!==7||!p.slice(0,4).every(v=>/^\d+$/.test(v)))continue;
    if(step!==null&&Number(p[0])!==step)continue;
    const t=number(p[5]);if(Number.isFinite(t)&&t>latest)latest=t;
  }
  return latest;
}
function runProcess(dir,env,{signal,timeoutMs,onPoll}){
  return new Promise((resolve,reject)=>{
    if(signal?.aborted)return reject(Error('计算已取消。'));
    const child=spawn(executable,['-i','job'],{cwd:dir,env,windowsHide:true,stdio:['ignore','pipe','pipe']});
    let log='',stopped=null;
    const kill=()=>{
      if(!child.pid)return;
      if(process.env.SystemRoot){const k=spawn(path.join(process.env.SystemRoot,'System32','taskkill.exe'),['/F','/T','/PID',String(child.pid)],{windowsHide:true,stdio:'ignore'});k.on('error',()=>child.kill());}
      else child.kill();
    };
    const stop=(code,message)=>{if(!stopped){stopped={code,message};kill();}};
    const abort=()=>stop('cancelled','计算已取消。');
    signal?.addEventListener('abort',abort,{once:true});
    const timer=setTimeout(()=>stop('timeout','计算超时。'),timeoutMs);
    const poll=onPoll?setInterval(onPoll,500):null;
    const append=b=>{log=(log+b.toString('latin1')).slice(-2_000_000);};
    child.stdout.on('data',append);child.stderr.on('data',append);
    const cleanup=()=>{clearTimeout(timer);clearInterval(poll);signal?.removeEventListener('abort',abort);};
    child.on('error',error=>{cleanup();reject(error);});
    child.on('close',code=>{cleanup();resolve({code,log,stopped});});
  });
}
function solverError(log,code){
  const line=log.match(/\*ERROR[^\r\n]*/i)?.[0];
  if(line)return 'CalculiX：'+line.replace(/^\*ERROR\s*/i,'').trim();
  if(/singular|zero pivot/i.test(log))return 'CalculiX：刚度矩阵奇异，请检查约束与材料。';
  return code?`CalculiX 计算失败（退出码 ${code}）。`:null;
}

// Runs one CalculiX dynamics job. `writeFrame(fields,value)` stores nodal Float32 fields.
async function run(m,s,{dir,signal,timeoutMs,progress,writeFrame}){
  const {input,meta}=deck(m,s);
  const threads=meshCpuThreads(s.threads,m.elements.length,1500);
  const count=String(threads);
  const env={...threadedEnvironment(threads),CCX_NPROC_STIFFNESS:count,CCX_NPROC_RESULTS:count,CCX_NPROC_EQUATION_SOLVER:count,PASTIX_NUM_THREADS:count};
  await fs.writeFile(path.join(dir,'job.inp'),input);
  progress('solving',0);
  let offset=0,pending='',lastTime=0,reading=false;
  const targetStep=s.transientMethod==='modal'?2:1;
  const onPoll=s.analysis==='transient'?async()=>{
    if(reading)return;reading=true;
    try{
      const handle=await fs.open(path.join(dir,'job.sta'),'r');
      try{
        const buffer=Buffer.alloc(65536);const {bytesRead}=await handle.read(buffer,0,buffer.length,offset);offset+=bytesRead;
        pending+=buffer.toString('latin1',0,bytesRead);
        const end=pending.lastIndexOf('\n');
        if(end>=0){const t=staTime(pending.slice(0,end),targetStep);pending=pending.slice(end+1);if(t>lastTime)lastTime=t;}
      }finally{await handle.close();}
      progress('solving',Math.min(1,lastTime/s.endTime),{time:lastTime});
    }catch{/* status file not written yet */}
    finally{reading=false;}
  }:()=>progress('solving',0);
  let {code,log,stopped}=await runProcess(dir,env,{signal,timeoutMs,onPoll});
  // The bundled multithreaded PaStiX occasionally aborts with a Windows exception
  // (e.g. 0xC0000374 heap corruption); the same deck is then solved again on one thread.
  const ucode=code==null?0:(code>>>0);
  if(!stopped&&code!==0&&ucode>=0xC0000000&&threads>1){
    meta.singleThreadRetry=`0x${ucode.toString(16).toUpperCase()}`;
    await fs.writeFile(path.join(dir,'solver-crash.log'),log);
    await Promise.all(['job.sta','job.frd','job.dat','job.eig','job.cvg'].map(name=>fs.rm(path.join(dir,name),{force:true}).catch(()=>{})));
    offset=0;pending='';lastTime=0;
    const single={...threadedEnvironment(1),CCX_NPROC_STIFFNESS:'1',CCX_NPROC_RESULTS:'1',CCX_NPROC_EQUATION_SOLVER:'1',PASTIX_NUM_THREADS:'1'};
    ({code,log,stopped}=await runProcess(dir,single,{signal,timeoutMs,onPoll}));
  }
  await fs.writeFile(path.join(dir,'solver.log'),log);
  if(stopped?.code==='cancelled')throw Error(stopped.message);
  const failure=stopped?.message||solverError(log,code);
  const N=m.coords.length,spatial=m.dimension===3;
  const frames=[];
  let modes=null,termination=null;
  progress('processing',0);
  const frd=path.join(dir,'job.frd');
  // Thin plane-stress sections: report masses and mass-normalized shapes per unit thickness.
  const t=meta.sectionThickness||1;
  const perUnitThickness=list=>{for(const mode of list){
    if(mode.effectiveMass)mode.effectiveMass=mode.effectiveMass.map(v=>v/t);
    if(mode.rotationalMass)mode.rotationalMass=mode.rotationalMass.map(v=>v/t);
    if(mode.participation)mode.participation=mode.participation.map(v=>v/Math.sqrt(t));
  }return list;};
  if(s.analysis==='modal'){
    if(failure)throw Error(failure);
    const dat=parseModalDat(await fs.readFile(path.join(dir,'job.dat'),'latin1'));
    const table=perUnitThickness(modeTable(dat,meta.rigidModes));
    if(!table.length)throw Error('CalculiX 没有输出特征频率。');
    const kept=keptModes(table,s.modes);
    meta.spuriousModes=table.filter(mode=>mode.spurious).length;
    meta.totalEffectiveMass=dat.total?dat.total.slice(0,3).map(v=>v/t):null;
    modes=kept.map(i=>table[i]);
    const keptMap=new Map(kept.map((idx,pos)=>[idx,pos+1]));
    let k=0;
    await readFrdSets(frd,N,async set=>{
      const disp=set.blocks.DISP,stress=set.blocks.STRESS;
      if(!disp||!stress)return;
      const index=k++;
      const modeNo=keptMap.get(index);
      if(modeNo===undefined)return;
      if(disp.seen<N||stress.seen<N)throw Error('CalculiX 振型输出不完整。');
      const mode=table[index];
      const fields=nodalFields(N,disp,stress,null,Math.sqrt(t));
      if(!fields.umag.every(Number.isFinite)||!fields.vm.every(Number.isFinite))throw Error('CalculiX 模态输出出现非有限数值。');
      await writeFrame(fields,mode.frequency,{mode:modeNo,rigid:mode.rigid});
      frames.push(index);progress('processing',frames.length/kept.length);
    },signal);
    if(frames.length<kept.length)throw Error('CalculiX 振型输出不完整。');
    // Renumber the kept modes 1..n in frequency order (solver numbers stay in `solverMode`).
    modes.forEach((mode,i)=>{mode.solverMode=mode.mode;mode.mode=i+1;});
  }else if(s.analysis==='harmonic'){
    if(failure)throw Error(failure);
    const dat=parseModalDat(await fs.readFile(path.join(dir,'job.dat'),'latin1'));
    modes=perUnitThickness(modeTable(dat,meta.rigidModes)).filter(mode=>!mode.spurious);
    modes.forEach((mode,i)=>{mode.solverMode=mode.mode;mode.mode=i+1;});
    await readFrdSets(frd,N,async set=>{
      const pdisp=set.blocks.PDISP,stress=set.blocks.STRESS,stressI=set.blocks.STRESSI;
      if(!pdisp||pdisp.seen<N||(stress&&stress.seen<N)||(stressI&&stressI.seen<N))return;
      const fields=harmonicFields(N,pdisp,stress,stressI);
      if(!fields.umag.every(Number.isFinite)||(fields.vm&&!fields.vm.every(Number.isFinite)))throw Error('CalculiX 谐响应输出出现非有限数值。');
      await writeFrame(fields,set.value,{});
      frames.push(set.value);progress('processing',Math.min(1,(set.value-s.freqMin)/(s.freqMax-s.freqMin)));
    },signal);
    if(!frames.length)throw Error('CalculiX 没有输出谐响应结果。');
  }else{
    if(s.transientMethod==='modal'&&!failure){
      const dat=parseModalDat(await fs.readFile(path.join(dir,'job.dat'),'latin1').catch(()=>''));
      modes=perUnitThickness(modeTable(dat,meta.rigidModes)).filter(mode=>!mode.spurious);
      modes.forEach((mode,i)=>{mode.solverMode=mode.mode;mode.mode=i+1;});
      if(!modes.length)modes=null;
    }
    // Initial state at rest.
    const zero=nodalFields(N,null,null,null,1,true);
    await writeFrame(zero,0,{});frames.push(0);
    await readFrdSets(frd,N,async set=>{
      const disp=set.blocks.DISP,velo=set.blocks.VELO,stress=set.blocks.STRESS;
      if(!disp||!stress||disp.seen<N||stress.seen<N)return;
      const fields=nodalFields(N,disp,stress,velo);
      if(![fields.umag,fields.vm].every(a=>a.every(Number.isFinite)))throw Error(`t = ${set.value} s 的结果出现非有限数值，计算发散。`);
      const time=set.value;
      await writeFrame(fields,time,{});
      frames.push(time);progress('processing',Math.min(1,time/s.endTime));
    },signal).catch(error=>{if(signal?.aborted)throw error;termination={code:'frame-error',message:error.message};});
    if(frames.length<2)throw Error(failure||termination?.message||'CalculiX 没有输出瞬态结果。');
    // ASCII FRD timestamps have six significant digits.
    const reached=frames.at(-1)>=s.endTime*(1-5e-6);
    if(failure||!reached)termination??={code:'solver-stop',message:(failure||'CalculiX 提前停止')+`，只保留到 t = ${frames.at(-1).toPrecision(4)} s 的结果。`};
  }
  return {solver:'CalculiX 2.22',cpuThreads:meta.singleThreadRetry?1:threads,modes,meta,termination,
    spatialFields:spatial};
}

function nodalFields(N,disp,stress,velo,scale=1,withVelocity=Boolean(velo)){
  const ux=new Float32Array(N),uy=new Float32Array(N),uz=new Float32Array(N),umag=new Float32Array(N);
  const sxx=new Float32Array(N),syy=new Float32Array(N),szz=new Float32Array(N),sxy=new Float32Array(N),syz=new Float32Array(N),sxz=new Float32Array(N),vm=new Float32Array(N);
  const f={ux,uy,uz,umag,sxx,syy,szz,sxy,syz,sxz,vm};
  let vx,vy,vz,vmag;
  if(withVelocity){vx=new Float32Array(N);vy=new Float32Array(N);vz=new Float32Array(N);vmag=new Float32Array(N);f.vx=vx;f.vy=vy;f.vz=vz;f.vmag=vmag;}
  if(disp){
    const dv=disp.values,dw=disp.width;
    for(let i=0;i<N;i++){
      const b=i*dw,x=(dw>0?dv[b]:0)*scale,y=(dw>1?dv[b+1]:0)*scale,z=(dw>2?dv[b+2]:0)*scale;
      ux[i]=x;uy[i]=y;uz[i]=z;umag[i]=Math.hypot(x,y,z);
    }
  }
  if(stress){
    const sv=stress.values,sw=stress.width;
    for(let i=0;i<N;i++){
      const b=i*sw;
      const a=(sw>0?sv[b]:0)*scale,c=(sw>1?sv[b+1]:0)*scale,e=(sw>2?sv[b+2]:0)*scale;
      const xy=(sw>3?sv[b+3]:0)*scale,yz=(sw>4?sv[b+4]:0)*scale,xz=(sw>5?sv[b+5]:0)*scale;
      sxx[i]=a;syy[i]=c;szz[i]=e;sxy[i]=xy;syz[i]=yz;sxz[i]=xz;
      vm[i]=vonMises(a,c,e,xy,yz,xz);
    }
  }
  if(velo){
    const vv=velo.values,vw=velo.width;
    for(let i=0;i<N;i++){
      const b=i*vw,x=vw>0?vv[b]:0,y=vw>1?vv[b+1]:0,z=vw>2?vv[b+2]:0;
      vx[i]=x;vy[i]=y;vz[i]=z;vmag[i]=Math.hypot(x,y,z);
    }
  }
  return f;
}
// Steady-state fields: displacement amplitude and phase (PDISP), stress amplitude
// |S + i S_I| per component and the exact von Mises peak over one period.
function harmonicFields(N,pdisp,stress,stressI){
  const ux=new Float32Array(N),uy=new Float32Array(N),uz=new Float32Array(N),umag=new Float32Array(N);
  const phx=new Float32Array(N),phy=new Float32Array(N),phz=new Float32Array(N);
  const f={ux,uy,uz,umag,phx,phy,phz};
  const pv=pdisp.values,pw=pdisp.width;
  for(let i=0;i<N;i++){
    const b=i*pw,x=pw>0?pv[b]:0,y=pw>1?pv[b+1]:0,z=pw>2?pv[b+2]:0;
    ux[i]=x;uy[i]=y;uz[i]=z;umag[i]=Math.hypot(x,y,z);
    phx[i]=pw>3?pv[b+3]:0;phy[i]=pw>4?pv[b+4]:0;phz[i]=pw>5?pv[b+5]:0;
  }
  if(!stress)return f;
  const sxx=new Float32Array(N),syy=new Float32Array(N),szz=new Float32Array(N),sxy=new Float32Array(N),syz=new Float32Array(N),sxz=new Float32Array(N),vm=new Float32Array(N);
  Object.assign(f,{sxx,syy,szz,sxy,syz,sxz,vm});
  const sv=stress.values,sw=stress.width,iv=stressI?.values,iw=stressI?.width||0;
  for(let i=0;i<N;i++){
    const sb=i*sw,ib=i*iw;
    const r0=sw>0?sv[sb]:0,r1=sw>1?sv[sb+1]:0,r2=sw>2?sv[sb+2]:0,r3=sw>3?sv[sb+3]:0,r4=sw>4?sv[sb+4]:0,r5=sw>5?sv[sb+5]:0;
    const i0=iv&&iw>0?iv[ib]:0,i1=iv&&iw>1?iv[ib+1]:0,i2=iv&&iw>2?iv[ib+2]:0,i3=iv&&iw>3?iv[ib+3]:0,i4=iv&&iw>4?iv[ib+4]:0,i5=iv&&iw>5?iv[ib+5]:0;
    sxx[i]=Math.hypot(r0,i0);syy[i]=Math.hypot(r1,i1);szz[i]=Math.hypot(r2,i2);
    sxy[i]=Math.hypot(r3,i3);syz[i]=Math.hypot(r4,i4);sxz[i]=Math.hypot(r5,i5);
    // Squared von Mises stress of re*cos(t) - im*sin(t) is a quadratic
    // form on the unit circle. Its peak is the larger of its two eigenvalues.
    const a0=r0-r1,a1=r1-r2,a2=r2-r0,b0=i0-i1,b1=i1-i2,b2=i2-i0;
    const rr=0.5*(a0*a0+a1*a1+a2*a2)+3*(r3*r3+r4*r4+r5*r5);
    const ii=0.5*(b0*b0+b1*b1+b2*b2)+3*(i3*i3+i4*i4+i5*i5);
    const ri=0.5*(a0*b0+a1*b1+a2*b2)+3*(r3*i3+r4*i4+r5*i5);
    vm[i]=Math.sqrt((rr+ii+Math.hypot(rr-ii,2*ri))/2);
  }
  return f;
}

module.exports={deck,run,readFrdSets,parseModalDat,modeTable,rigidModeCount,harmonicFields,executable};
