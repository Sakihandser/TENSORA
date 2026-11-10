'use strict';
// Input/output adapter only. Equilibrium, constitutive integration and increments run in upstream CCX.
const fs=require('node:fs/promises'),path=require('node:path'),{spawn}=require('node:child_process');
const {createReadStream}=require('node:fs'),{createInterface}=require('node:readline');
const {normalize,materialFor}=require('./deformation-settings');
const {validateStaticRestraints}=require('./static-restraints');
const executable=path.join(__dirname,'third_party/calculix/bin/ccx.exe');
const OUTPUT_NODE_FRAME_BUDGET=1_500_000;
function deck(model,raw){
  const s=normalize(raw),nodes=model?.nodes,elements=model?.elements;
  if(s.solver!=='calculix')throw Error('相场断裂材料须选择 PhAST 求解器。');
  if(!Array.isArray(nodes)||!nodes.length||!Array.isArray(elements)||!elements.length)throw Error('请先生成实体网格。');
  if(nodes.length>200000||elements.length>400000)throw Error('当前变形模块最多支持 20 万节点 / 40 万单元。');
  const ids=new Set(),eids=new Set(),finite=v=>Number.isFinite(v),positive=v=>Number.isSafeInteger(v)&&v>0;
  for(const n of nodes){if(!positive(n.nodeNo)||ids.has(n.nodeNo)||![n.x,n.y,n.forceX??0,n.forceY??0].every(finite))throw Error('节点编号、坐标或载荷无效。');ids.add(n.nodeNo);}
  const lines=['*HEADING','TENSORA independent deformation analysis; SI units','*NODE',...nodes.map(n=>`${n.nodeNo},${n.x},${n.y},0`)];
  const groups=new Map(),nodeMap=new Map(nodes.map(n=>[n.nodeNo,n])),materials=new Map((model.materials||[]).map(m=>[m.materialNo,m])),materialSettings={};
  for(const e of elements){
    if(!positive(e.elementNo)||eids.has(e.elementNo)||![e.node1,e.node2,e.node3].every(n=>ids.has(n))||new Set([e.node1,e.node2,e.node3]).size!==3)throw Error('单元编号或连接无效。');eids.add(e.elementNo);
    const a=nodeMap.get(e.node1),b=nodeMap.get(e.node2),c=nodeMap.get(e.node3);
    if(Math.abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))<1e-20)throw Error('存在退化三角形。');
    if(!finite(e.elasticModulus)||e.elasticModulus<=0||!finite(e.poissonRatio)||e.poissonRatio<=-1||e.poissonRatio>=.5)throw Error('实体材料弹性参数无效。');
    const materialId=materials.get(e.materialNo)?.id??String(e.materialNo??'legacy');
    const card=materialFor(s,materialId);
    if(card.model==='phaseField')throw Error('相场断裂材料须选择 PhAST 求解器。');
    materialSettings[e.materialNo??'legacy']=card;
    const key=JSON.stringify([materialId,e.elasticModulus,e.poissonRatio,card]);if(!groups.has(key))groups.set(key,{elements:[],card});groups.get(key).elements.push(e);
  }
  let i=0;for(const {elements:es,card} of groups.values()){
    const e=es[0],name=`M${++i}`,E=e.elasticModulus,nu=e.poissonRatio;
    lines.push(`*ELEMENT,TYPE=${s.planeMode?'CPE3':'CPS3'},ELSET=${name}`);
    for(const e of es){const a=nodeMap.get(e.node1),b=nodeMap.get(e.node2),c=nodeMap.get(e.node3);const ccw=(b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x)>0;lines.push(`${e.elementNo},${e.node1},${ccw?e.node2:e.node3},${ccw?e.node3:e.node2}`);}
    lines.push(`*MATERIAL,NAME=${name}`);
    lines.push('*ELASTIC',`${E},${nu}`);if(card.model==='plastic')lines.push('*PLASTIC',`${card.yieldStress},0`,`${card.yieldStress+card.hardening},1`);
    lines.push(`*SOLID SECTION,ELSET=${name},MATERIAL=${name}`,'1');
  }
  lines.push('*BOUNDARY');
  validateStaticRestraints(nodes,elements);
  for(const n of nodes){if(n.fixUx)lines.push(`${n.nodeNo},1,1`);if(n.fixUy)lines.push(`${n.nodeNo},2,2`);}
  // Direct-model forceX/Y already contain point + distributed + body loads.
  // elementNodeLoads are a duplicate element representation, never add them again.
  const loads=new Map(nodes.map(n=>[n.nodeNo,[n.forceX||0,n.forceY||0]]));
  lines.push(`*STEP,INC=${s.maxIncrements}${s.finiteStrain?',NLGEOM':''}`,'*STATIC',`${1/s.increments},1,1e-8,${1/s.increments}`,'*CLOAD');
  let loaded=false;for(const [id,f] of loads)for(let d=0;d<2;d++)if(f[d]){lines.push(`${id},${d+1},${f[d]*s.loadFactor}`);loaded=true;}
  if(!loaded)throw Error('模型没有非零载荷。');
  const hasPlastic=Object.values(materialSettings).some(c=>c.model==='plastic');
  // CCX always writes the final successful increment of a completed step.
  // Reserve a slot for it even when it does not land on a sampling increment.
  const frameBudget=Math.floor(OUTPUT_NODE_FRAME_BUDGET/nodes.length);
  const outputFrequency=s.maxIncrements<=frameBudget?1:Math.ceil(s.maxIncrements/(frameBudget-1));
  lines.push(`*NODE FILE,OUTPUT=2D,FREQUENCY=${outputFrequency}`,'U,RF',`*EL FILE,OUTPUT=2D,FREQUENCY=${outputFrequency}`,hasPlastic?'S,E,PEEQ':'S,E','*END STEP');
  // CCX numeric fields have a 20-character limit, including exponent and sign.
  const input=lines.map(line=>line.startsWith('*')||line.startsWith('TENSORA')?line:line.split(',').map(v=>v.length>20&&Number.isFinite(Number(v))?Number(v).toExponential(12).toUpperCase():v).join(',')).join('\n')+'\n';
  return {input,settings:s,materialSettings,hasPlastic,outputFrequency};
}
function frdParser(model,{allowPartial=false,convergedTimes=null,hasPlastic=false}={}){
  const ids=new Set(model.nodes.map(n=>n.nodeNo)),frames=[];
  let frame=null,field=null,counts=null,outputIndex,staIndex=0;
  const number=v=>Number(v.replace(/[dD]/,'E'));
  function saveFrame(){
    if(!frame||!Number.isFinite(frame.time)||counts.displacement!==ids.size||counts.stress!==ids.size||counts.strain!==ids.size||
      (hasPlastic&&counts.plasticStrain!==ids.size))return;
    if(convergedTimes){
      // FRD counts outputs, while STA counts increments. Match by load
      // fraction and allow for the lower precision in the FRD time field.
      const delta=i=>Math.abs(convergedTimes[i]-frame.time);
      while(staIndex+1<convergedTimes.length&&delta(staIndex+1)<delta(staIndex))staIndex++;
      const time=convergedTimes[staIndex];
      if(time===undefined||delta(staIndex)>Math.max(1e-12,Math.abs(time)*6e-6))return;
      frame.time=time;
      staIndex++;
    }
    frames.push(frame);
  }
  function consume(line){
    if(line.startsWith('  100C')){
      const time=number(line.slice(12,24).trim());
      const [, , index]=line.slice(24).trim().split(/\s+/);
      if(!frame||outputIndex!==index||Math.abs(frame.time-time)>1e-10){
        saveFrame();
        frame={time,displacement:{},stress:{},strain:{},plasticStrain:{}};
        counts={displacement:0,stress:0,strain:0,plasticStrain:0};
        outputIndex=index;
      }
      field=null;
    }
    if(line.startsWith(' -4')){const name=line.trim().split(/\s+/)[1];field={DISP:'displacement',STRESS:'stress',TOSTRAIN:'strain',PE:'plasticStrain'}[name]||null;}
    if(frame&&field&&line.startsWith(' -1')){
      const id=Number(line.slice(3,13));if(!ids.has(id))return;
      const values=[];for(let p=13;p<line.length;p+=12){const v=number(line.slice(p,p+12).trim());if(Number.isFinite(v))values.push(v);}
      if(!Object.hasOwn(frame[field],id))counts[field]++;
      frame[field][id]=values;
    }
  }
  function finish(){
    saveFrame();
    if(!frames.length||(!allowPartial&&frames.at(-1).time<.999999))throw Error('求解未完成全部载荷增量；不发布部分结果。');
    return frames;
  }
  return {consume,finish};
}
function parseFrd(text,model,options){
  const parser=frdParser(model,options);
  for(const line of text.split(/\r?\n/))parser.consume(line);
  return parser.finish();
}
async function readFrd(file,model,options,signal){
  const parser=frdParser(model,options);
  const stream=createReadStream(file,{encoding:'utf8',signal});
  const lines=createInterface({input:stream,crlfDelay:Infinity});
  try{
    for await(const line of lines)parser.consume(line);
    return parser.finish();
  }finally{stream.destroy();}
}
function convergedStaRows(text){
  const rows=[];for(const line of text.split(/\r?\n/)){
    const p=line.trim().split(/\s+/);if(p.length!==7||!p.slice(0,4).every(v=>/^\d+$/.test(v))||Number(p[0])!==1)continue;
    const fraction=Number(p[5].replace(/[dD]/,'E'));if(Number.isFinite(fraction)&&fraction>0&&fraction<=1.000001)rows.push({fraction:Math.min(1,fraction),completedIncrements:Number(p[1])});
  }return rows;
}
function diagnoseDeformationStop(log,exitCode=0){
  if(/max\.\s*# of increments reached/i.test(log))return {code:'increment-limit',message:'达到最大允许增量数，尚未完成目标载荷。请增加最大允许增量数后重新计算。'};
  if(/increment size smaller than minimum|too many cutbacks/i.test(log))return {code:'nonconvergence',message:'自动切步后仍未收敛，尚未完成目标载荷。请检查载荷、约束与材料设置；仅增加增量上限不一定能解决。'};
  if(exitCode||/\*ERROR|Job failed/i.test(log))return {code:'solver-error',message:'CalculiX 计算失败：'+(log.match(/\*ERROR[^\r\n]*/i)?.[0]||`exit ${exitCode}`)};
  return null;
}
let active=false;
// Only successful STA rows count. Failed/cut-back attempts carry a nonnumeric ATT.
function parseStaProgress(text){
  let latest=null;
  for(const line of text.split(/\r?\n/)){
    const parts=line.trim().split(/\s+/);
    if(parts.length!==7||!parts.slice(0,4).every(p=>/^\d+$/.test(p)))continue;
    const fraction=Number(parts[5].replace(/[dD]/,'E'));
    if(Number(parts[0])!==1||!Number.isFinite(fraction)||fraction<0||fraction>1.000001)continue;
    if(!latest||fraction>latest.fraction)latest={fraction:Math.min(1,fraction),completedIncrements:Number(parts[1])};
  }
  return latest;
}
async function runDeformation(model,raw,{signal,timeoutMs=30*60*1000,onProgress}={}){
  if(active)throw Error('已有损伤变形任务正在运行。');
  const started=Date.now();
  const report=(phase,p={})=>onProgress?.({phase,elapsedMs:Date.now()-started,...p});
  report('preparing',{fraction:0,completedIncrements:0,estimatedRemainingMs:null});
  const {input,settings,materialSettings,hasPlastic,outputFrequency}=deck(model,raw);active=true;
  let dir;
  try{
    await fs.access(executable);
    const base=path.join(__dirname,'calculation-data/deformation');await fs.mkdir(base,{recursive:true});dir=await fs.mkdtemp(path.join(base,'run-'));
    await fs.writeFile(path.join(dir,'job.inp'),input);await fs.writeFile(path.join(dir,'request.json'),JSON.stringify({model,settings}));
    let capturedLog='';
    const outcome=await new Promise((resolve,reject)=>{
      if(signal?.aborted)return reject(Error('计算已取消。'));
      const child=spawn(executable,['-i','job'],{cwd:dir,windowsHide:true,env:{...process.env,OMP_NUM_THREADS:'2'},stdio:['ignore','pipe','pipe']});let log='',stopped='';
      const stop=reason=>{stopped=reason;child.kill();},abort=()=>stop('计算已取消。');signal?.addEventListener('abort',abort,{once:true});
      const timer=setTimeout(()=>stop('计算超时。'),timeoutMs);
      let offset=0,pending='',last={fraction:0,completedIncrements:0},reading=false,tracking=true;
      const poll=async()=>{
        if(reading)return;reading=true;
        try{
          // Read only appended status bytes, not the growing FRD result file.
          const handle=await fs.open(path.join(dir,'job.sta'),'r');
          try{const buffer=Buffer.alloc(65536);const {bytesRead}=await handle.read(buffer,0,buffer.length,offset);offset+=bytesRead;pending+=buffer.toString('utf8',0,bytesRead);
            const end=pending.lastIndexOf('\n');if(end>=0){const next=parseStaProgress(pending.slice(0,end));pending=pending.slice(end+1);if(next&&next.fraction>last.fraction)last=next;}
          }finally{await handle.close();}
          const elapsedMs=Date.now()-started;
          if(tracking)report('solving',{...last,estimatedRemainingMs:last.completedIncrements>=2&&last.fraction>0&&last.fraction<1?elapsedMs*(1-last.fraction)/last.fraction:null});
        }catch{/* Status-file sharing delays must not interrupt a valid solve. */}
        finally{reading=false;}
      };
      const progressTimer=onProgress?setInterval(poll,500):null;
      report('solving',{fraction:0,completedIncrements:0,estimatedRemainingMs:null});
      const append=b=>{log=(log+b.toString()).slice(-2_000_000);capturedLog=log;};child.stdout.on('data',append);child.stderr.on('data',append);
      const cleanup=()=>{tracking=false;clearTimeout(timer);clearInterval(progressTimer);signal?.removeEventListener('abort',abort);};
      child.on('error',e=>{cleanup();reject(e);});child.on('close',code=>{cleanup();if(stopped)reject(Error(stopped));else resolve({log,exitCode:code});});
    }).catch(async error=>{await fs.writeFile(path.join(dir,'solver.log'),capturedLog);throw error;});
    const {log,exitCode}=outcome;await fs.writeFile(path.join(dir,'solver.log'),log);
    const rows=convergedStaRows(await fs.readFile(path.join(dir,'job.sta'),'utf8').catch(()=>''));
    const termination=diagnoseDeformationStop(log,exitCode);
    if(termination){termination.runId=path.basename(dir);termination.convergedFraction=rows.at(-1)?.fraction||0;await fs.writeFile(path.join(dir,'diagnostic.json'),JSON.stringify(termination,null,2));}
    if(termination?.code==='solver-error'||(termination&&!rows.length))throw Error(termination.message);
    report('processing',{fraction:termination?rows.at(-1).fraction:1,estimatedRemainingMs:null});
    let frames;
    try{frames=await readFrd(path.join(dir,'job.frd'),model,{allowPartial:Boolean(termination),convergedTimes:rows.length?rows.map(r=>r.fraction):null,hasPlastic},signal);}
    catch(error){if(signal?.aborted)throw Error('计算已取消。');throw Error(termination?.message||error.message);}
    const completedIncrements=rows.at(-1)?.completedIncrements??frames.length;
    const result={ok:true,completed:!termination,termination,completedIncrements,outputFrequency,completedAt:new Date().toISOString(),solver:'CalculiX 2.22',settings,materialSettings,model,frames,runId:path.basename(dir),damageScope:'PEEQ / material criticalPlasticStrain is an initiation indicator only; no damage evolution or stiffness degradation.'};
    await fs.writeFile(path.join(dir,'result.json'),JSON.stringify(result));report(termination?'partial':'complete',{fraction:termination?termination.convergedFraction:1,completedIncrements,estimatedRemainingMs:termination?null:0});return result;
  }finally{active=false;}
}
module.exports={deck,parseFrd,parseStaProgress,convergedStaRows,diagnoseDeformationStop,runDeformation,executable};
