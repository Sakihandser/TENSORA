// 3D blast stages of the 3D workspace. The setup page assembles the shared 3D
// model (mesh, volume materials, restraints and loads) with blast settings and
// sends it to /api/blast3d-runs, where MFEM (initial equilibrium) and
// OpenCourant (explicit dynamics) compute the response. The result page streams
// saved frames from the server and shows them in the shared 3D viewer.
const FIELD_ORDER=['ux','uy','uz','umag','vx','vy','vz','vmag','sxx','syy','szz','sxy','syz','sxz','vm','pressure','damage','plasticStrain'];
export const BLAST_FIELD_LABELS={vx:'X 速度 Vx',vy:'Y 速度 Vy',vz:'Z 速度 Vz',vmag:'速度量 |v|',pressure:'压力 p（压为正）',s1:'最大主应力 σ1',
  e1:'最大主应变 ε1',plasticStrain:'等效塑性应变',damage:'本构损伤 D（JH2 / HJC）',failureDamage:'拉伸失效损伤',eroded:'失效单元体积比例'};
export const BLAST_UNIT_FIELDS=new Set(['damage','failureDamage','eroded']);
const FIELD_UNITS={ux:'m',uy:'m',uz:'m',umag:'m',vx:'m/s',vy:'m/s',vz:'m/s',vmag:'m/s',s1:'Pa',damage:'1',failureDamage:'1',eroded:'1',plasticStrain:'1',
  e1:'1',exx:'1',eyy:'1',ezz:'1',exy:'1',eyz:'1',exz:'1',equivalentStrain:'1'};
export const blastFieldUnit=key=>FIELD_UNITS[key]||(key.startsWith('s')||key==='vm'||key==='pressure'?'Pa':'1');
const ROLE_LABELS={rock:'岩体',charge:'装药（JWL）',void:'不参与计算'};
const STORAGE_KEY='fem.blast3d.settings.v1';

export function createBlastPanel(ctx){
  const $=id=>document.getElementById(id);
  let roles={},wallFaces=new Set(),absorbFaces=new Set(),explosives=[],library={materials:[],cards:[]};
  let run=null,frame=null,frameIndex=-1,request=null,playback=null,loadTicket=0;
  const cache=new Map();

  // ------------------------------------------------------------ settings
  const numeric=(id,name,{min=-Infinity,positive=false}={})=>{
    const value=Number($(id).value);
    if(!Number.isFinite(value)||value<min||(positive&&!(value>0)))throw Error(`${name} 输入无效`);
    return value;
  };
  function readSettings(){
    const sourceMode=$('solid3dBlastSource').value;
    const settings={sourceMode,
      endTime:numeric('solid3dBlastEnd','计算时长',{positive:true})*1e-6,
      frames:Math.round(numeric('solid3dBlastFrames','保存帧数',{min:2})),
      initialState:$('solid3dBlastInitial').value,
      timeStepScale:numeric('solid3dBlastDtScale','时间步安全系数',{positive:true}),
      threads:Math.round(numeric('solid3dBlastThreads','CPU 线程数',{min:1})),
      absorbingSurfaces:[...absorbFaces],absorbingThickness:numeric('solid3dBlastLayer','吸收层厚度',{min:0}),
      volumeRoles:{...roles},rockCards:rockCards()};
    if(sourceMode==='pressure'){
      Object.assign(settings,{wallSurfaces:[...wallFaces],peakPressure:numeric('solid3dBlastPeak','峰值压力',{positive:true})*1e6,
        pulseDuration:numeric('solid3dBlastDuration','脉冲时长',{positive:true})*1e-6,pulseShape:$('solid3dBlastShape').value});
      if(settings.pulseShape==='exponential')settings.riseTime=numeric('solid3dBlastRise','上升时间',{positive:true})*1e-6;
    }else{
      const explosive=explosives.find(e=>e.id===$('solid3dBlastExplosive').value);
      if(!explosive)throw Error('请在爆破库中添加炸药并选择。');
      settings.explosive=explosive;
      settings.detonationTime=numeric('solid3dBlastDetTime','起爆时间',{min:0})*1e-6;
      if($('solid3dBlastDetMode').value==='custom')settings.detonationPoint=['X','Y','Z'].map(axis=>numeric('solid3dBlastDet'+axis,'起爆点 '+axis));
    }
    return settings;
  }
  // Rock material cards: base material -> linked blast-library card (materials.json).
  async function refreshCards(){
    try{
      const payload=await (await fetch('/api/materials',{cache:'no-store'})).json();
      library={materials:payload.materials||[],cards:payload.blastMaterials||[]};
    }catch{library={materials:window.PROJECT_MATERIAL_LIBRARY?.materials||[],cards:window.PROJECT_MATERIAL_LIBRARY?.blastMaterials||[]};}
    renderCards();
  }
  function rockMaterials(){
    const mesh=ctx.getMesh(),ids=new Set();
    for(const volume of mesh?.volumes||[])if((roles[String(volume.id)]||'rock')==='rock'){const id=ctx.volumeMaterial(String(volume.id));if(id)ids.add(String(id));}
    return [...ids].map(id=>{
      const material=library.materials.find(entry=>String(entry.id)===id);
      const card=material?.blastMaterialId?library.cards.find(entry=>entry.id===material.blastMaterialId):null;
      return {id,material,card};
    });
  }
  function rockCards(){
    return Object.fromEntries(rockMaterials().filter(entry=>entry.card).map(entry=>[entry.id,entry.card.card]));
  }
  function renderCards(){
    const host=$('solid3dBlastCards');if(!host)return;
    host.replaceChildren();
    const entries=rockMaterials();
    if(!entries.length){const item=document.createElement('li');item.textContent='生成网格并为岩体体域分配材料后显示。';host.append(item);return;}
    for(const {material,card,id} of entries){
      const item=document.createElement('li');
      const name=material?.name||id;
      if(card)item.textContent=`${name} → ${card.name}（${window.Blast3dCards?.describe(card.card)||card.card.model}）`;
      else{
        const law=material?.blastConstitutive?.law;
        item.className=law===6?'warning':'';
        item.textContent=law===3?`${name} → 未关联材料卡，沿用基础材料的 JH2 参数`:law===6?`${name} → 未关联材料卡；Mohr–Coulomb 不适用于三维，请关联材料卡`
          :`${name} → 未关联材料卡，按线弹性计算（无损伤）`;
      }
      host.append(item);
    }
  }
  window.addEventListener('tensora-blast-materials-changed',refreshCards);
  const formIds=['solid3dBlastSource','solid3dBlastPeak','solid3dBlastDuration','solid3dBlastShape','solid3dBlastRise','solid3dBlastDetMode',
    'solid3dBlastDetX','solid3dBlastDetY','solid3dBlastDetZ','solid3dBlastDetTime','solid3dBlastInitial','solid3dBlastLayer','solid3dBlastEnd',
    'solid3dBlastFrames','solid3dBlastDtScale','solid3dBlastThreads'];
  function snapshot(){
    return {form:Object.fromEntries(formIds.map(id=>[id,$(id).value])),explosiveId:$('solid3dBlastExplosive').value,
      roles,wallFaces:[...wallFaces],absorbFaces:[...absorbFaces]};
  }
  function restore(data){
    if(!data||typeof data!=='object')return;
    for(const [id,value] of Object.entries(data.form||{}))if(formIds.includes(id)&&typeof value==='string')$(id).value=value;
    if(typeof data.explosiveId==='string')$('solid3dBlastExplosive').dataset.wanted=data.explosiveId;
    roles=data.roles&&typeof data.roles==='object'?{...data.roles}:{};
    wallFaces=new Set((data.wallFaces||[]).map(String));absorbFaces=new Set((data.absorbFaces||[]).map(String));
    syncForm();renderLists();
  }
  function persist(){try{localStorage.setItem(STORAGE_KEY,JSON.stringify({form:snapshot().form}));}catch{/* storage unavailable */}}

  // ------------------------------------------------------------ view
  function syncForm(){
    const jwl=$('solid3dBlastSource').value==='jwl';
    $('solid3dBlastPressure').hidden=jwl;$('solid3dBlastJwl').hidden=!jwl;
    $('solid3dBlastRiseRow').hidden=$('solid3dBlastShape').value!=='exponential';
    $('solid3dBlastDetPoint').hidden=$('solid3dBlastDetMode').value!=='custom';
  }
  function renderLists(){
    const mesh=ctx.getMesh();
    const surfaces=new Set((mesh?.surfaces||[]).map(face=>String(face.id)));
    for(const set of [wallFaces,absorbFaces])for(const id of [...set])if(mesh&&!surfaces.has(id))set.delete(id);
    $('solid3dBlastWallList').textContent=wallFaces.size?[...wallFaces].map(id=>'面 '+id).join('、'):'未选择';
    $('solid3dBlastAbsorbList').textContent=absorbFaces.size?[...absorbFaces].map(id=>'面 '+id).join('、'):'未选择（外边界保持原约束，会反射应力波）';
    const host=$('solid3dBlastRoles');host.replaceChildren();
    if(!mesh){const p=document.createElement('p');p.textContent='请先在“计算”页生成四面体网格。';host.append(p);return;}
    for(const volume of mesh.volumes){
      const id=String(volume.id);
      if(!roles[id])roles[id]='rock';
      const label=document.createElement('label');
      const material=ctx.materialName(id);
      label.textContent=`体域 ${id}${material?` · ${material}`:''}`;
      const select=document.createElement('select');
      for(const [value,text] of Object.entries(ROLE_LABELS))select.add(new Option(text,value));
      select.value=roles[id];
      select.addEventListener('change',()=>{roles[id]=select.value;renderCards();ctx.draw();});
      label.append(select);host.append(label);
    }
    for(const id of Object.keys(roles))if(!mesh.volumes.some(v=>String(v.id)===id))delete roles[id];
  }
  async function refreshExplosives(){
    try{
      const response=await fetch('/api/explosives',{cache:'no-store'});
      if(!response.ok)throw Error();
      explosives=(await response.json()).explosives||[];
    }catch{explosives=[];}
    const select=$('solid3dBlastExplosive'),wanted=select.dataset.wanted||select.value;
    select.replaceChildren(...explosives.map(e=>new Option(e.name,e.id)));
    if(explosives.some(e=>e.id===wanted))select.value=wanted;
  }
  async function refreshStatus(){
    try{
      const state=await (await fetch('/api/blast3d-status',{cache:'no-store'})).json();
      $('solid3dBlastEngine').textContent=`OpenCourant 显式动力学${state.opencourant?'':'（未找到运行时）'} · MFEM 初始平衡${state.mfem?'':'（未找到程序）'}`;
    }catch{/* keep the static description */}
  }
  // Face tint used by the shared 3D draw routine on the setup page.
  function faceColor(surfaceId){
    const id=String(surfaceId);
    if(wallFaces.has(id))return 0xd9480f;
    if(absorbFaces.has(id))return 0x3b82c4;
    return null;
  }
  function volumeTint(volumeId){return roles[String(volumeId)]==='charge'?0xc92a2a:roles[String(volumeId)]==='void'?0xcfd8dc:null;}
  function show(){refreshStatus();refreshExplosives();renderLists();refreshCards();syncForm();updateResultControls();}

  // ------------------------------------------------------------ run
  async function runBlast(button){
    if(request)return;
    const payload=ctx.solidPayload();
    const settings=readSettings();
    if(settings.sourceMode==='pressure'&&!settings.wallSurfaces.length)throw Error('请在视窗中点选孔壁面，再点击“把选中面设为孔壁”。');
    if(settings.sourceMode==='jwl'&&!Object.values(roles).includes('charge'))throw Error('JWL 模式需要把装药所在体域设为“装药”。');
    persist();
    const controller=new AbortController(),progress=$('solid3dBlastProgress'),text=$('solid3dBlastProgressText');
    request=controller;button.disabled=true;$('solid3dCancelBlast').disabled=false;
    progress.value=0;progress.hidden=false;text.textContent='';
    const phases={preparing:'准备模型',prestress:'MFEM 初始静力平衡',starter:'OpenCourant Starter 检查模型',engine:'OpenCourant Engine 显式求解',processing:'读取动画帧',complete:'完成'};
    ctx.status('正在提交三维爆破计算…');
    try{
      const response=await fetch('./api/blast3d-runs',{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/x-ndjson'},
        signal:controller.signal,body:JSON.stringify({solid:payload,settings})});
      if(!response.ok&&!response.headers.get('content-type')?.includes('ndjson')){const body=await response.json().catch(()=>({}));throw Error(body.error||'三维爆破计算失败');}
      const reader=response.body.getReader(),decoder=new TextDecoder();
      let buffer='',result=null;
      for(;;){
        const {value,done}=await reader.read();
        if(done)break;
        buffer+=decoder.decode(value,{stream:true});
        const lines=buffer.split('\n');buffer=lines.pop();
        for(const line of lines){
          if(!line.trim())continue;
          const message=JSON.parse(line);
          if(message.type==='progress'){
            const weight={preparing:0,prestress:.05,starter:.1,engine:.15,processing:.9,complete:1}[message.phase]??0;
            const span={prestress:.05,engine:.75,processing:.1}[message.phase]||0;
            progress.value=Math.min(1,weight+span*(message.fraction||0));
            const time=message.time!=null?` · t = ${(message.time*1e6).toFixed(1)} μs`:'';
            const dt=message.dt?` · Δt = ${message.dt.toExponential(2)} s`:'';
            text.textContent=`${phases[message.phase]||message.phase}${time}${dt} · 已用 ${(message.elapsedMs/1000).toFixed(1)} s`;
          }else if(message.type==='error')throw Error(message.error);
          else if(message.type==='result')result=message.result;
        }
      }
      if(!result)throw Error('三维爆破计算没有返回结果。');
      await setRun(result);
      ctx.status(result.completed?'三维爆破计算完成。':result.termination.message);
      ctx.setPage('blast-results');
    }catch(error){
      if(controller.signal.aborted)ctx.status('三维爆破计算已取消。');else throw error;
    }finally{request=null;button.disabled=false;$('solid3dCancelBlast').disabled=true;progress.hidden=true;}
  }

  // ------------------------------------------------------------ results
  async function setRun(summary){
    stopPlayback();cache.clear();run=summary;frame=null;frameIndex=-1;
    const slider=$('solid3dBlastFrame');slider.max=String(summary.frames.length-1);slider.value=slider.max;
    updateResultControls();
    await showFrame(summary.frames.length-1);
  }
  async function loadFrame(index){
    if(cache.has(index))return cache.get(index);
    const response=await fetch(`./api/blast3d-runs/${run.runId}/frames/${index}`,{cache:'no-store'});
    if(!response.ok)throw Error('三维爆破结果帧已清理，请重新计算。');
    const buffer=await response.arrayBuffer(),n=run.nodeCount;
    const all=new Float32Array(buffer);
    const nodeFields={};
    run.fields.forEach((key,k)=>{nodeFields[key]=all.subarray(k*n,(k+1)*n);});
    const displacementVector=new Float32Array(n*3);
    for(let i=0;i<n;i++){displacementVector[i*3]=nodeFields.ux?.[i]||0;displacementVector[i*3+1]=nodeFields.uy?.[i]||0;displacementVector[i*3+2]=nodeFields.uz?.[i]||0;}
    const stats=run.frames[index].stats;
    const data={nodeFields,displacementVector,maxDisplacement:stats.umag?.[1]||0,maxVonMises:stats.vm?.[1]||0,time:run.frames[index].time};
    cache.set(index,data);
    if(cache.size>4)cache.delete(cache.keys().next().value);
    return data;
  }
  async function showFrame(index){
    const ticket=++loadTicket;
    const data=await loadFrame(index);
    if(ticket!==loadTicket)return;
    frame=data;frameIndex=index;
    const f=run.frames[index],peak=f.stats.vm?.[1];
    $('solid3dBlastSummary').textContent=`帧 ${index+1} / ${run.frames.length} · t = ${(f.time*1e6).toFixed(2)} μs`
      +(peak!=null?` · 最大 von Mises ${peak.toExponential(3)} Pa`:'')
      +(f.stats.damage?` · 最大损伤 ${f.stats.damage[1].toFixed(3)}`:'')
      +(f.stats.failureDamage?` · 最大失效损伤 ${f.stats.failureDamage[1].toFixed(3)}`:'')
      +(run.completed===false?` · ${run.termination.message}`:'');
    ctx.draw();
  }
  function stopPlayback(){clearTimeout(playback);playback=null;$('solid3dPlayBlast').textContent='播放 / 暂停';}
  function play(){
    if(playback!==null){stopPlayback();return;}
    const slider=$('solid3dBlastFrame');
    if(slider.value===slider.max)slider.value='0';
    const step=async()=>{
      try{await showFrame(Number(slider.value));}catch(error){ctx.status(error.message);stopPlayback();return;}
      if(playback===null)return;
      if(slider.value===slider.max){stopPlayback();return;}
      slider.stepUp();playback=setTimeout(step,160);
    };
    playback=setTimeout(step,0);
  }
  function updateResultControls(){
    const available=Boolean(run);
    $('solid3dBlastFrame').disabled=!available;
    $('solid3dPlayBlast').disabled=!available||run.frames.length<2;
    $('solid3dExportBlast').disabled=!available;
    if(!available)$('solid3dBlastSummary').textContent='请在三维爆破设置页运行模拟。';
    const meta=run?.meta;
    $('solid3dBlastRunInfo').textContent=meta?[
      `${run.solver}${run.prestressSolver?' + '+run.prestressSolver+` 初始平衡（${run.prestress.iterations} 次 PCG 迭代）`:''}`,
      `${meta.elements.toLocaleString()} 个四面体 · ${meta.usedNodes.toLocaleString()} 个节点 · ${meta.materials.map(m=>({elastic:'线弹性',jh2:'JH2',hjc:'HJC',dp:'Drucker–Prager',jc:'Johnson–Cook',jwl:'JWL'}[m.law])+(m.failure?' + 拉伸失效':'')).join(' / ')}`,
      meta.source.mode==='pressure'?`孔壁压力：峰值 ${(meta.source.peakPressure/1e6).toFixed(2)} MPa，${(meta.source.pulseDuration*1e6).toFixed(1)} μs，${meta.source.segments} 个加载三角面`
        :`JWL 起爆：${meta.source.explosive}，起爆点 (${meta.source.detonationPoint.map(v=>v.toFixed(4)).join(', ')}) m`,
      meta.absorbingLayer?`吸收层：厚 ${meta.absorbingLayer.thickness.toFixed(3)} m，${meta.absorbingLayer.bands} 层，α_max ${meta.absorbingLayer.alphaMax.toExponential(2)} 1/s`:'无吸收层',
      `计算用时 ${(run.elapsedMs/1000).toFixed(1)} s · 任务 ${run.runId}`
    ].join('\n'):'';
  }
  async function exportRun(){
    if(!run)throw Error('还没有三维爆破结果。');
    const handle=await window.chooseExportFile(window.uiText('TENSORA-三维爆破结果.json'),'application/json','.json');
    if(!handle)return;
    await window.writeExportFile(handle,async writer=>{
      await writer.write(`{"summary":${JSON.stringify(run)},"frames":[`);
      for(let i=0;i<run.frames.length;i++){
        const data=await loadFrame(i);
        const fields=Object.fromEntries(Object.entries(data.nodeFields).map(([k,v])=>[k,Array.from(v)]));
        await writer.write((i?',':'')+JSON.stringify({time:data.time,fields}));
      }
      await writer.write(']}');
    });
    ctx.status('三维爆破结果已导出。');
  }

  // ------------------------------------------------------------ events
  const guard=fn=>async event=>{try{await fn(event);}catch(error){ctx.status(error.message);}};
  for(const id of ['solid3dBlastSource','solid3dBlastShape','solid3dBlastDetMode'])$(id).addEventListener('change',syncForm);
  for(const id of formIds)$(id).addEventListener('change',persist);
  $('solid3dBlastAddWall').addEventListener('click',guard(()=>{
    const face=ctx.selectedFace();if(face==null)throw Error('请先在视窗中点选孔壁所在的面。');
    absorbFaces.delete(String(face));wallFaces.add(String(face));renderLists();ctx.draw();
  }));
  $('solid3dBlastClearWall').addEventListener('click',()=>{wallFaces.clear();renderLists();ctx.draw();});
  $('solid3dBlastAddAbsorb').addEventListener('click',guard(()=>{
    const face=ctx.selectedFace();if(face==null)throw Error('请先在视窗中点选外边界面。');
    wallFaces.delete(String(face));absorbFaces.add(String(face));renderLists();ctx.draw();
  }));
  $('solid3dBlastClearAbsorb').addEventListener('click',()=>{absorbFaces.clear();renderLists();ctx.draw();});
  $('solid3dRunBlast').addEventListener('click',guard(event=>runBlast(event.target)));
  $('solid3dCancelBlast').addEventListener('click',()=>request?.abort());
  $('solid3dBlastFrame').addEventListener('input',guard(()=>{stopPlayback();return showFrame(Number($('solid3dBlastFrame').value));}));
  $('solid3dPlayBlast').addEventListener('click',play);
  $('solid3dExportBlast').addEventListener('click',guard(exportRun));
  try{const saved=JSON.parse(localStorage.getItem(STORAGE_KEY)||'null');if(saved)restore(saved);}catch{/* ignore */}
  syncForm();

  return {
    show,faceColor,volumeTint,snapshot,restore,stopPlayback,
    frame:()=>frame,hasRun:()=>Boolean(run),fields:()=>run?.fields||[],run:()=>run,
    goToFrame(index){
      if(!run)return;
      stopPlayback();$('solid3dBlastFrame').value=String(index);
      return showFrame(index).catch(error=>ctx.status(error.message));
    },
    meshChanged(){
      request?.abort();stopPlayback();run=null;frame=null;cache.clear();roles={};
      const slider=$('solid3dBlastFrame');slider.max=slider.value='0';
      renderLists();updateResultControls();
    },
    abort(){request?.abort();stopPlayback();}
  };
}
export {FIELD_ORDER};
