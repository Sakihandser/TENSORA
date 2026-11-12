'use strict';

const fs=require('node:fs/promises');
const path=require('node:path');
const {spawn}=require('node:child_process');
const {normalize,materialFor}=require('./deformation-settings');
const {tetData}=require('./solid3d');

const root=path.join(__dirname,'third_party','oofem','oofem_3.0_AMD64');
const executable=path.join(root,'bin','oofem.exe');

function prepareCrackBand(model,raw){
  const settings=normalize(raw);
  if(model?.dimension!==3||settings.solver!=='oofem'||settings.finiteStrain)throw Error('OOFEM 裂带断裂需要三维小变形设置。');
  const cards=new Map(model.materials.map(material=>[material.materialNo,materialFor(settings,material.id)]));
  if([...cards.values()].some(card=>card.model!=='crackBand'))throw Error('OOFEM 裂带计算要求所有体域使用裂带材料卡。');
  const displacement=settings.fractureLoading==='displacement';
  const coordinates=new Map();
  let peak=0;
  for(const node of model.nodes){
    const {nodeNo,x,y,z,forceX,forceY,forceZ}=node;
    if(!Number.isSafeInteger(nodeNo)||nodeNo<=0||coordinates.has(nodeNo)||![x,y,z,forceX,forceY,forceZ].every(Number.isFinite))throw Error('节点编号、坐标或载荷无效。');
    if(displacement&&((node.fixUx&&forceX)||(node.fixUy&&forceY)||(node.fixUz&&forceZ)))throw Error('位移加载方向与固定约束冲突，请调整载荷节点或约束。');
    coordinates.set(nodeNo,[x,y,z]);
    peak=Math.max(peak,Math.abs(forceX),Math.abs(forceY),Math.abs(forceZ));
  }
  if(!peak)throw Error('模型没有非零载荷。');
  const conditions=['BoundaryCondition 1 loadTimeFunction 1 d 0.0'];
  const values=new Map();
  function prescribed(value){
    if(!values.has(value)){
      values.set(value,conditions.length+1);
      conditions.push(`BoundaryCondition ${conditions.length+1} loadTimeFunction 2 d ${value}`);
    }
    return values.get(value);
  }
  const nodes=model.nodes.map(node=>{
    const forces=[node.forceX,node.forceY,node.forceZ];
    const fixed=[node.fixUx,node.fixUy,node.fixUz];
    const bc=forces.map((force,axis)=>fixed[axis]?1:displacement&&force?prescribed(force/peak*settings.fractureDisplacement):0);
    let line=`node ${node.nodeNo} coords 3 ${coordinates.get(node.nodeNo).join(' ')} bc 3 ${bc.join(' ')}`;
    if(!displacement&&forces.some(Boolean)){
      const id=conditions.length+1;
      conditions.push(`NodalLoad ${id} loadTimeFunction 2 components 3 ${forces.join(' ')}`);
      line+=` load 1 ${id}`;
    }
    return line;
  });
  const materials=new Map();
  const elements=model.elements.map(element=>{
    const {elementNo,node1,node2,node3,node4,materialNo,elasticModulus:E,poissonRatio:nu}=element;
    const ids=[node1,node2,node3,node4];
    if(!ids.every(id=>coordinates.has(id))||new Set(ids).size!==4)throw Error('单元编号或连接无效。');
    if(tetData(ids.map(id=>coordinates.get(id))).orientation<0)[ids[1],ids[2]]=[ids[2],ids[1]];
    if(!materials.has(materialNo)){
      const {tensileStrength,crackBandEnergy}=cards.get(materialNo);
      // OOFEM computes the regularized softening law from Gf and element size.
      materials.set(materialNo,`idm1 ${materialNo} d 0 E ${E} n ${nu} tAlpha 0 damlaw 0 e0 ${tensileStrength/E} gf ${crackBandEnergy} equivstraintype 4`);
    }
    return `ltrspace ${elementNo} nodes 4 ${ids.join(' ')} crosssect 1 mat ${materialNo}`;
  });
  const budget=Math.floor(1500000/nodes.length);
  const outputFrequency=settings.increments<=budget?1:Math.ceil(settings.increments/(budget-1));
  const output=outputFrequency===1?'tstep_all':`tstep_step ${outputFrequency} tsteps_out {${settings.increments}}`;
  const deck=[
    'model.out','TENSORA native crack band, SI units',
    // Integer solver times avoid a duplicate final increment from accumulated roundoff.
    `StaticStructural nsteps ${settings.increments} deltat 1 solverType "nrsolver" maxiter 100 nmodules 1`,
    `vtkxml ${output} vars 3 1 4 52 primvars 1 1 stype 1`,
    'domain 3d','OutputManager',
    `ndofman ${nodes.length} nelem ${elements.length} ncrosssect 1 nmat ${materials.size} nbc ${conditions.length} nic 0 nltf 2`,
    ...nodes,...elements,'simplecs 1',...materials.values(),...conditions,
    'ConstantFunction 1 f(t) 1.0',`PiecewiseLinFunction 2 nPoints 2 t 2 0.0 ${settings.increments} f(t) 2 0.0 ${settings.loadFactor}`
  ].join('\n')+'\n';
  return {deck,settings,outputFrequency,materialSettings:Object.fromEntries(cards)};
}

function readArray(xml,name,count){
  const pattern=name?new RegExp(`<DataArray\\b[^>]*\\bName="${name}"[^>]*>([^<]*)</DataArray>`):/<Points>\s*<DataArray\b[^>]*>([^<]*)<\/DataArray>/;
  const body=xml.match(pattern)?.[1].trim();
  const values=body?body.split(/\s+/).map(Number):null;
  if(values?.length!==count||!values.every(Number.isFinite))throw Error('OOFEM 输出缺少完整的节点场。');
  return values;
}

function readFrame(xml,model,time){
  const count=model.nodes.length,points=readArray(xml,null,count*3);
  const displacement=readArray(xml,'DisplacementVector',count*3);
  const stress=readArray(xml,'IST_StressTensor',count*9);
  const strain=readArray(xml,'IST_StrainTensor',count*9);
  const damage=readArray(xml,'IST_DamageScalar',count);
  const frame={time,displacement:{},stress:{},strain:{},damage:{}};
  const tensor=(field,index)=>[0,4,8,1,5,2].map(offset=>field[index*9+offset]);
  for(let i=0;i<count;i++){
    const {nodeNo,x,y,z}=model.nodes[i];
    // The single OOFEM region enumerates mesh nodes in their input order.
    if([x,y,z].some((value,axis)=>Math.abs(points[i*3+axis]-value)>6e-7*Math.abs(value)+1e-15))throw Error('OOFEM 输出节点顺序与输入网格不一致。');
    if(damage[i]<-1e-8||damage[i]>1+1e-8)throw Error('OOFEM 裂带损伤结果无效。');
    frame.displacement[nodeNo]=displacement.slice(i*3,i*3+3);
    frame.stress[nodeNo]=tensor(stress,i);
    frame.strain[nodeNo]=tensor(strain,i);
    frame.damage[nodeNo]=[Math.min(1,Math.max(0,damage[i]))];
  }
  return frame;
}

async function runCrackBand(model,raw,{signal,onProgress}={}){
  signal?.throwIfAborted();
  const {deck,settings,outputFrequency,materialSettings}=prepareCrackBand(model,raw);
  const started=Date.now();
  const progress=(phase,fraction)=>onProgress?.({phase,fraction,elapsedMs:Date.now()-started});
  progress('preparing',0);
  const base=path.join(__dirname,'calculation-data','deformation');
  await fs.mkdir(base,{recursive:true});
  const dir=await fs.mkdtemp(path.join(base,'oofem-'));
  await fs.writeFile(path.join(dir,'model.in'),deck);
  await fs.writeFile(path.join(dir,'request.json'),JSON.stringify({model,settings}));
  signal?.throwIfAborted();
  const logFile=path.join(dir,'solver.log');
  const log=await fs.open(logFile,'w');
  let code;
  try{
    progress('solving',0);
    code=await new Promise((resolve,reject)=>{
      const key=Object.keys(process.env).find(name=>name.toUpperCase()==='PATH')||'Path';
      const system=process.env.SystemRoot||'C:\\Windows';
      const env={...process.env,[key]:[path.join(root,'lib'),path.join(system,'System32'),system].join(path.delimiter)};
      const child=spawn(executable,['-f','model.in'],{cwd:dir,env,signal,windowsHide:true,stdio:['ignore',log.fd,log.fd]});
      const timer=setTimeout(()=>child.kill(),30*60*1000);
      let failure;
      child.once('error',error=>{failure=error;});
      child.once('close',status=>{clearTimeout(timer);if(failure)reject(failure);else resolve(status);});
    });
  }finally{await log.close();}
  signal?.throwIfAborted();
  const runId=path.basename(dir);
  const diagnostic=await fs.readFile(logFile,'utf8');
  if(code!==0||!diagnostic.includes('ANALYSIS FINISHED')||/no convergence|failed to converge|convergence not reached/i.test(diagnostic))throw Error(`OOFEM 求解失败，请查看任务日志 ${runId}。`);
  progress('processing',1);
  const collection=await fs.readFile(path.join(dir,'model.out.m0.pvd'),'utf8');
  const records=[...collection.matchAll(/<DataSet\s+timestep="([^"]+)"[^>]*\sfile="(model\.out\.m0\.\d+\.vtu)"/g)];
  if(!records.length||Number(records.at(-1)[1])!==settings.increments)throw Error('求解未完成全部载荷增量；不发布部分结果。');
  const frames=[];
  let previousTime=0;
  for(const [,time,file] of records){
    const fraction=Number(time)/settings.increments;
    if(!Number.isFinite(fraction)||fraction<=previousTime||fraction>1+1e-8)throw Error('OOFEM 输出缺少完整的节点场。');
    frames.push(readFrame(await fs.readFile(path.join(dir,file),{encoding:'utf8',signal}),model,fraction));
    previousTime=fraction;
  }
  const result={ok:true,completed:true,runId,solver:'OOFEM 3.0',model,settings,frames,outputFrequency,materialSettings,damageEvolution:true};
  await fs.writeFile(path.join(dir,'result.json'),JSON.stringify(result));
  progress('complete',1);
  return result;
}

module.exports={prepareCrackBand,runCrackBand};
