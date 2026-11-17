// 3D fluid–structure interaction stages of the 3D workspace. The setup stage
// assigns volume roles, the fluid and fluid boundary faces on the shared
// tetrahedral mesh and posts them to /api/fsi-runs, where SU2 (and MFEM for
// the one-way path) compute the response. The result stage shows the saved
// frames in the shared viewer.
export const FSI_FIELD_LABELS={pressure:'流体压力 p',vmag:'流速大小 |v|',vx:'流速 X 分量 vx',vy:'流速 Y 分量 vy',vz:'流速 Z 分量 vz',
  vorticity:'涡量大小 |ω|',q:'Q 判据',cp:'压力系数 Cp',density:'流体密度 ρ',temperature:'流体温度 T',mach:'马赫数 Ma'};
const FSI_UNITS={pressure:'Pa',vmag:'m/s',vx:'m/s',vy:'m/s',vz:'m/s',vorticity:'1/s',q:'1/s²',cp:'1',density:'kg/m³',temperature:'K',mach:'1'};
export const fsiFieldUnit=key=>FSI_UNITS[key];
const KIND_LABELS={inlet:'速度入口',outlet:'压力出口',wall:'无滑移壁面',slip:'滑移壁面 / 对称面',farfield:'远场'};
const KIND_COLORS={inlet:0x1b7f3b,outlet:0xc2410c,wall:0x2f4858,slip:0x7a8f99,farfield:0x6d28d9};
const ROLE_LABELS={solid:'结构',fluid:'流体',void:'不参与计算'};
const STORAGE_KEY='fem.fsi3d.settings.v1';
const FORM={engine:'solid3dFsiEngineSelect',analysis:'solid3dFsiAnalysis',structure:'solid3dFsiStructure',turbulence:'solid3dFsiTurbulence',
  referencePressure:'solid3dFsiReference',outerIterations:'solid3dFsiOuter',fluidIterations:'solid3dFsiFluidIter',solidIterations:'solid3dFsiSolidIter',
  relaxation:'solid3dFsiRelaxation',relaxationFactor:'solid3dFsiRelaxFactor',convergence:'solid3dFsiConvergence',timeStep:'solid3dFsiDt',
  steps:'solid3dFsiSteps',frames:'solid3dFsiFrames',threads:'solid3dFsiThreads'};
const TEXT_KEYS=new Set(['engine','analysis','structure','turbulence','relaxation']);
const FLOW_NUMERICS=['solid3dFsiFlowCfl','solid3dFsiFlowOrder'];
// OpenCourant SPH engine inputs (saved with the form, read only for engine 'sph').
const SPH_FORM={endTime:'solid3dFsiSphEnd',frames:'solid3dFsiSphFrames',timeStepScale:'solid3dFsiSphDtScale',soundSpeed:'solid3dFsiSphSound',
  massScaling:'solid3dFsiSphMassScaling',minTimeStep:'solid3dFsiSphMinDt'};
const SPH_VECTORS={initialVelocity:['solid3dFsiSphVx','solid3dFsiSphVy','solid3dFsiSphVz'],gravity:['solid3dFsiSphGx','solid3dFsiSphGy','solid3dFsiSphGz']};
const SPH_IDS=[...Object.values(SPH_FORM),...Object.values(SPH_VECTORS).flat()];

export function createFsiPanel(ctx){
  const $=id=>document.getElementById(id);
  let roles={},faces={},fluids=[],fluidId=null,embeddedFluid=null,run=null,frame=null,frameIndex=-1,request=null,playback=null,loadTicket=0;
  const cache=new Map();
  let recording=false;

  // ------------------------------------------------------------ settings
  // Volumes keep the role the user chose; otherwise a volume with a material is a
  // structure and one without a material is fluid (decided when asked, not frozen).
  const roleOf=id=>roles[String(id)]||(ctx.volumeMaterial(String(id))?'solid':'fluid');
  const allRoles=()=>Object.fromEntries((ctx.getMesh()?.volumes||[]).map(v=>[String(v.id),roleOf(v.id)]));
  function readSettings(){
    const settings={};
    if($('solid3dFsiEngineSelect').value==='sph'){
      settings.engine='sph';settings.threads=Number($('solid3dFsiThreads').value);
      for(const [key,id] of Object.entries(SPH_FORM))settings[key]=key==='massScaling'?$(id).value:Number($(id).value);
      for(const [key,ids] of Object.entries(SPH_VECTORS))settings[key]=ids.map(id=>Number($(id).value));
    }else{
      for(const [key,id] of Object.entries(FORM))settings[key]=TEXT_KEYS.has(key)?$(id).value:Number($(id).value);
      if(settings.analysis==='steady'){
        if($(FLOW_NUMERICS[0]).value!=='')settings.flowCfl=$(FLOW_NUMERICS[0]).valueAsNumber;
        if($(FLOW_NUMERICS[1]).value==='first')settings.flowFirstOrder=true;
      }
    }
    settings.volumeRoles=allRoles();
    settings.boundaries={};
    for(const [id,b] of Object.entries(faces))settings.boundaries[`S${id}`]={...b};
    return settings;
  }
  const FORM_IDS=[...Object.values(FORM),...SPH_IDS,...FLOW_NUMERICS];
  function snapshot(){return {form:Object.fromEntries(FORM_IDS.map(id=>[id,$(id).value])),roles,faces,fluidId,...(embeddedFluid?{fluid:embeddedFluid}:{})};}
  function restore(data){
    if(!data||typeof data!=='object')return;
    $(FLOW_NUMERICS[0]).value='';
    $(FLOW_NUMERICS[1]).value='second';
    for(const [id,value] of Object.entries(data.form||{}))if(FORM_IDS.includes(id)&&typeof value==='string')$(id).value=value;
    roles=data.roles&&typeof data.roles==='object'?{...data.roles}:{};
    faces={};
    for(const [id,b] of Object.entries(data.faces||{}))if(b&&KIND_LABELS[b.kind])faces[String(id)]={...b};
    if(typeof data.fluidId==='string')fluidId=data.fluidId;
    embeddedFluid=data.fluid?window.FluidLibrary.entry(data.fluid):null;
    syncForm();renderLists();
  }
  function persist(){try{localStorage.setItem(STORAGE_KEY,JSON.stringify({form:snapshot().form,fluidId}));}catch{/* storage unavailable */}}

  // ------------------------------------------------------------ view
  function syncForm(){
    const sph=$('solid3dFsiEngineSelect').value==='sph';
    $('solid3dFsiSphBlock').hidden=!sph;$('solid3dFsiSu2Block').hidden=sph;
    $('solid3dFsiSphMinDtRow').hidden=$('solid3dFsiSphMassScaling').value!=='custom';
    const oneway=$('solid3dFsiEngineSelect').value==='oneway';
    if(oneway){$('solid3dFsiAnalysis').value='steady';$('solid3dFsiStructure').value='linear';}
    $('solid3dFsiAnalysis').disabled=oneway;$('solid3dFsiStructure').disabled=oneway;
    const transient=$('solid3dFsiAnalysis').value==='transient';
    for(const id of FLOW_NUMERICS)$(id).parentElement.hidden=transient;
    for(const id of ['solid3dFsiDtRow','solid3dFsiStepsRow','solid3dFsiFramesRow'])$(id).hidden=!transient;
    for(const id of ['solid3dFsiOuterRow','solid3dFsiSolidRow','solid3dFsiRelaxRow','solid3dFsiRelaxFactorRow'])$(id).hidden=oneway;
    const kind=$('solid3dFsiKind').value;
    $('solid3dFsiVelocityRow').hidden=!['inlet','farfield'].includes(kind);
    $('solid3dFsiPressureRow').hidden=kind!=='outlet';
    $('solid3dFsiDirectionRow').hidden=kind!=='farfield';
    const fluid=selectedFluid();
    $('solid3dFsiReferenceRow').hidden=fluid?.model!=='idealgas';
    $('solid3dRunFsi').textContent=sph?'运行 SPH 显式流固耦合':'运行三维流固耦合';
  }
  function availableFluids(){return window.FluidLibrary.forModel(fluids,embeddedFluid);}
  function selectedFluid(){const available=availableFluids();return available.find(f=>f.id===fluidId)||available[0]||null;}
  async function refreshFluids(){
    try{const response=await fetch('/api/fluids',{cache:'no-store'});if(!response.ok)throw Error();fluids=(await response.json()).fluids||[];}
    catch{fluids=[];}
    const select=$('solid3dFsiFluid'),fluid=selectedFluid();
    select.replaceChildren(...availableFluids().map(f=>new Option(f.name,f.id)));
    if(fluid)select.value=fluid.id;
    $('solid3dFsiFluidInfo').textContent=fluid?window.FluidLibrary.describe(fluid):'流体材料库为空，请先在“流体材料库”中添加流体。';
    syncForm();
  }
  function renderLists(){
    const mesh=ctx.getMesh();
    const host=$('solid3dFsiRoles');host.replaceChildren();
    if(!mesh){const p=document.createElement('p');p.textContent='请先在“计算”页生成四面体网格。';host.append(p);}
    else for(const volume of mesh.volumes){
      const id=String(volume.id);
      const label=document.createElement('label');
      const material=ctx.materialName(id);
      label.textContent=`体域 ${id}${material?` · ${material}`:''}`;
      const select=document.createElement('select');
      for(const [value,text] of Object.entries(ROLE_LABELS))select.add(new Option(text,value));
      select.value=roleOf(id);
      select.addEventListener('change',()=>{roles[id]=select.value;ctx.draw();});
      label.append(select);host.append(label);
    }
    if(mesh){
      const surfaces=new Set(mesh.surfaces.map(s=>String(s.id)));
      for(const id of Object.keys(faces))if(!surfaces.has(id))delete faces[id];
      for(const id of Object.keys(roles))if(!mesh.volumes.some(v=>String(v.id)===id))delete roles[id];
    }
    const list=$('solid3dFsiBoundaryList');list.replaceChildren();
    const entries=Object.entries(faces);
    if(!entries.length){const item=document.createElement('li');item.textContent='尚未指定流体边界（未指定的流体外表面按无滑移壁面处理）。';list.append(item);}
    for(const [id,b] of entries){
      const item=document.createElement('li');
      item.textContent=`面 ${id} → ${KIND_LABELS[b.kind]}`+(b.kind==='outlet'?`，${b.pressure} Pa`:['inlet','farfield'].includes(b.kind)?`，${b.velocity} m/s`:'')
        +(b.kind==='farfield'?`，方向 (${b.direction.map(v=>Number(v.toFixed(3))).join(', ')})`:'');
      list.append(item);
    }
  }
  async function refreshStatus(){
    try{
      const state=await (await fetch('/api/fsi-status',{cache:'no-store'})).json();
      $('solid3dFsiEngine').textContent=`SU2 8.6 多区流固耦合${state.su2?'':'（未找到运行时）'} · MFEM 4.10 单向评估${state.mfem?'':'（未找到程序）'}`;
    }catch{/* keep the static description */}
  }
  function faceColor(surfaceId){const b=faces[String(surfaceId)];return b?KIND_COLORS[b.kind]:null;}
  function volumeTint(volumeId){const role=roleOf(volumeId);return role==='fluid'?0x8fc9e3:role==='void'?0xcfd8dc:null;}
  function show(){refreshStatus();refreshFluids();renderLists();syncForm();updateResultControls();}

  // ------------------------------------------------------------ run
  async function runFsi(button){
    if(request)return;
    const solid=ctx.solidPayload();
    const fluid=selectedFluid();
    if(!fluid)throw Error('请先在流体材料库中添加并选择流体。');
    const settings=readSettings();
    if(!Object.values(allRoles()).includes('fluid'))throw Error('请至少把一个体域设为“流体”。');
    if(!Object.values(allRoles()).includes('solid'))throw Error('请至少把一个体域设为“结构”。');
    persist();
    const controller=new AbortController(),progress=$('solid3dFsiProgress'),text=$('solid3dFsiProgressText');
    request=controller;button.disabled=true;$('solid3dCancelFsi').disabled=false;
    progress.value=0;progress.hidden=false;text.textContent='';
    const phases={preparing:'准备模型',su2:'SU2 求解',mfem:'MFEM 结构求解',starter:'OpenCourant Starter 检查模型',engine:'OpenCourant Engine 显式求解',processing:'读取结果',complete:'完成'};
    const sph=settings.engine==='sph';
    ctx.status('正在提交三维流固耦合计算…');
    try{
      const response=await window.fetchSpecialtyRun(controller,'./api/fsi-runs',{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/x-ndjson'},
        body:JSON.stringify({solid,settings,fluid})});
      if(!response.ok&&!response.headers.get('content-type')?.includes('ndjson')){const body=await response.json().catch(()=>({}));throw Error(body.error||'三维流固耦合计算失败');}
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
            const weight={preparing:0,su2:.03,mfem:.85,starter:.02,engine:.05,processing:.9,partial:1,complete:1}[message.phase]??0;
            const span={su2:settings.engine==='oneway'?.82:.87,mfem:.05,engine:.85,processing:.1}[message.phase]||0;
            progress.value=Math.min(1,weight+span*(message.fraction||0));
            const parts=[phases[message.phase]||message.phase];
            if(sph&&message.time!=null)parts.push(`t = ${message.time.toPrecision(4)} s / ${settings.endTime} s`);
            if(sph&&message.dt)parts.push(`Δt = ${message.dt.toExponential(2)} s`);
            if(message.timeIter!=null&&settings.analysis==='transient')parts.push(`时间步 ${message.timeIter+1} / ${settings.steps}`);
            if(message.outer!=null&&settings.engine==='su2')parts.push(`耦合迭代 ${message.outer+1}`);
            if(message.inner!=null)parts.push(`流场迭代 ${message.inner+1}`);
            parts.push(`已用 ${(message.elapsedMs/1000).toFixed(1)} s`);
            text.textContent=parts.join(' · ');
          }else if(message.type==='error')throw Error(message.error);
          else if(message.type==='result')result=message.result;
        }
      }
      if(!result)throw Error('三维流固耦合计算没有返回结果。');
      await setRun(result);
      ctx.status(result.termination?.message||(result.engine==='sph'?'SPH 显式流固耦合计算完成。'
        :result.engine==='oneway'?'三维单向流固耦合计算完成。':result.meta?.converged===false?'三维流固耦合达到迭代上限（未达到收敛判据）。':'三维流固耦合计算完成。'));
      ctx.setPage('fsi-results');
    }catch(error){
      if(controller.signal.aborted||error.message==='计算已取消。')ctx.status('三维流固耦合计算已取消。');else throw error;
    }finally{request=null;button.disabled=false;$('solid3dCancelFsi').disabled=true;progress.hidden=true;}
  }

  // ------------------------------------------------------------ results
  async function setRun(summary){
    stopPlayback();cache.clear();run=summary;frame=null;frameIndex=-1;
    $('solid3dFsiScale').value='1';
    const slider=$('solid3dFsiFrame');slider.max=String(summary.frames.length-1);slider.value=slider.max;
    updateResultControls();
    await showFrame(summary.frames.length-1);
  }
  async function loadFrame(index,summary=run){
    if(summary===run&&cache.has(index))return cache.get(index);
    const response=await fetch(`./api/fsi-runs/${summary.runId}/frames/${index}`,{cache:'no-store'});
    if(!response.ok)throw Error('流固耦合结果帧已清理，请重新计算。');
    const all=new Float32Array(await response.arrayBuffer()),n=summary.nodeCount;
    const expected=summary.fields.length*n+(summary.engine==='sph'?summary.particleFields.length*summary.particleCount:0);
    if(all.length!==expected)throw Error('流固耦合结果帧数据不完整。');
    const nodeFields={},flowGeometry={};
    summary.fields.forEach((key,k)=>{
      const target=key.startsWith('flowU')?flowGeometry:nodeFields;
      target[key]=all.subarray(k*n,(k+1)*n);
    });
    // SPH runs append one block per particle field after the mesh fields.
    let particles=null;
    if(summary.engine==='sph'){
      const P=summary.particleCount,base=summary.fields.length*n,values={};
      summary.particleFields.forEach((key,k)=>{values[key]=all.subarray(base+k*P,base+(k+1)*P);});
      const positions=new Float32Array(P*3);
      for(let i=0;i<P;i++){positions[i*3]=values.px[i];positions[i*3+1]=values.py[i];positions[i*3+2]=values.pz[i];}
      particles={count:P,positions,values};
    }
    const displacementVector=new Float32Array(n*3);
    for(let i=0;i<n;i++)for(let d=0;d<3;d++){const v=nodeFields[['ux','uy','uz'][d]]?.[i];displacementVector[i*3+d]=Number.isFinite(v)?v:0;}
    const stats=summary.frames[index].stats;
    const data={index,nodeFields,flowGeometry,displacementVector,particles,maxVelocity:stats.vmag?.[1]||0,maxDisplacement:stats.umag?.[1]||0,maxVonMises:stats.vm?.[1]||0,time:summary.frames[index].time};
    if(summary===run){
      cache.set(index,data);
      if(cache.size>4)cache.delete(cache.keys().next().value);
    }
    return data;
  }
  async function showFrame(index){
    const ticket=++loadTicket;
    const data=await loadFrame(index);
    if(ticket!==loadTicket)return;
    frame=data;frameIndex=index;
    const f=run.frames[index];
    $('solid3dFsiSummary').textContent=[run.frames.length>1?`帧 ${index+1} / ${run.frames.length}`:'',f.time!=null?`t = ${f.time.toPrecision(5)} s`:'',
      `最大位移 ${(f.stats.umag?.[1]||0).toExponential(3)} m`,f.stats.vm?`最大 von Mises ${f.stats.vm[1].toExponential(3)} Pa`:'',
      f.stats.vmag?`最大流速 ${f.stats.vmag[1].toExponential(3)} m/s`:'',f.stats.pressure?`压力 ${f.stats.pressure[0].toExponential(3)} 至 ${f.stats.pressure[1].toExponential(3)} Pa`:''].filter(Boolean).join(' · ');
    ctx.draw();
    updateFrameActions();
  }
  function stopPlayback(){clearTimeout(playback);playback=null;$('solid3dPlayFsi').textContent='播放 / 暂停';}
  function play(){
    if(playback!==null){stopPlayback();return;}
    const slider=$('solid3dFsiFrame');
    if(slider.value===slider.max)slider.value='0';
    const step=async()=>{
      try{await showFrame(Number(slider.value));}catch(error){ctx.status(error.message);stopPlayback();return;}
      if(playback===null)return;
      if(slider.value===slider.max){
        if(!$('solid3dFsiLoop').checked){stopPlayback();return;}
        slider.value='0';
      }else slider.stepUp();
      playback=setTimeout(step,Math.max(40,200/Number($('solid3dFsiSpeed').value)));
    };
    playback=setTimeout(step,0);
  }
  function updateResultControls(){
    const available=Boolean(run);
    updateFrameActions();
    $('solid3dExportFsi').disabled=!available;
    $('solid3dFsiExportVtk').disabled=!available;
    if(!available)$('solid3dFsiSummary').textContent='请在三维流固耦合设置页运行计算。';
    const m=run?.meta,s=run?.settings;
    if(run?.engine==='sph'){
      $('solid3dFsiRunInfo').textContent=[
        `${run.solver} · ${s.endTime} s · ${run.frames.length} 帧`,
        `流体：${m.fluid.name} · ${m.particles.toLocaleString()} 个 SPH 粒子 · 粒子间距 ${m.spacing.toExponential(3)} m · 流体质量 ${m.fluidMass.toPrecision(4)} kg`,
        `数值声速 ${m.soundSpeed.toPrecision(4)} m/s（真实声速 ${m.physicalSoundSpeed.toPrecision(4)} m/s）· 特征流速 ${m.characteristicSpeed.toPrecision(3)} m/s`,
        `结构四面体 ${m.structureTets.toLocaleString()} · 约束节点 ${m.restrainedNodes.toLocaleString()} · 接触面段 ${m.structureSegments.toLocaleString()} · 刚性壁三角面 ${m.wallTriangles.toLocaleString()}`,
        `时间步估计：流体粒子 ${m.particleTimeStep.toExponential(2)} s · 结构 ${m.structureTimeStep.toExponential(2)} s`,
        m.minTimeStep>0?`质量缩放：最小时间步 ${m.minTimeStep.toExponential(2)} s，增加质量 ${(m.engine?.addedMass??0).toExponential(3)} kg（结构质量 ${m.structureMass.toExponential(3)} kg），重力只作用于流体`:'未使用质量缩放',
        m.inertiaFactor>1.1?`注意：质量缩放使最细结构单元的惯性放大约 ${m.inertiaFactor.toPrecision(3)} 倍，结构动力响应失真，结果只适合准静态评估。可加粗结构网格、选用更软的结构材料或关闭质量缩放（计算更慢）。`:'',
        m.engine?`OpenCourant ${m.engine.cycles.toLocaleString()} 个循环 · 能量误差 ${m.engine.energyError}`:'',
        `材料：${m.materials.map(x=>`${x.name}（E ${(x.E/1e9).toPrecision(4)} GPa，ν ${x.nu}，ρ ${x.density} kg/m³）`).join('；')}`,
        run.completed?'':run.termination?.message||'',
        `计算用时 ${(run.elapsedMs/1000).toFixed(1)} s · 任务 ${run.runId}`].filter(Boolean).join('\n');
      return;
    }
    $('solid3dFsiRunInfo').textContent=m?[
      `${run.solver} · ${s.analysis==='transient'?`瞬态（Δt = ${s.timeStep} s，${s.steps} 步）`:'稳态'}`,
      `流体：${m.fluid.name}（${m.compressible?'可压缩理想气体':'不可压缩'}）· 结构：${s.structure==='neohookean'?'Neo-Hookean 大变形':'线弹性小变形'}`,
      `流体四面体 ${m.fluidCells.toLocaleString()} · 结构四面体 ${m.solidCells.toLocaleString()} · 流固界面 ${m.interfaceFaces.toLocaleString()} 个三角面`,
      run.termination?.message,
      run.mfem?`MFEM PCG ${run.mfem.iterations} 次迭代 · 界面载荷合力 (${run.mfem.resultant.map(v=>v.toExponential(3)).join(', ')}) N`:(!run.termination&&s.analysis==='steady'?(m.converged?'界面残差达到收敛判据。':'达到耦合迭代上限，未达到收敛判据。'):''),
      `计算用时 ${(run.elapsedMs/1000).toFixed(1)} s · 任务 ${run.runId}`
    ].filter(Boolean).join('\n'):'';
  }
  function updateFrameActions(){
    const multiple=run?.frames.length>1,slider=$('solid3dFsiFrame');
    for(const id of ['solid3dFsiFrameRow','solid3dFsiFrameActions','solid3dFsiSpeedRow','solid3dFsiVideoRow'])$(id).hidden=!multiple;
    slider.disabled=$('solid3dPlayFsi').disabled=!multiple||recording;
    $('solid3dFsiPrevious').disabled=slider.disabled||slider.value==='0';
    $('solid3dFsiNext').disabled=slider.disabled||slider.value===slider.max;
    $('solid3dFsiExportVideo').disabled=slider.disabled||!FsiVideo.supported(ctx.canvas);
  }
  async function exportVideo(){
    if(recording)return;
    const expected=run,slider=$('solid3dFsiFrame'),restore=Number(slider.value);
    stopPlayback();recording=true;updateFrameActions();
    let saved=false;
    try{
      saved=await FsiVideo.save({canvas:ctx.canvas,frameCount:run.frames.length,fps:Number($('solid3dFsiVideoFps').value),
        caption:index=>`${$('solid3dDisplay').selectedOptions[0]?.textContent||''} · t = ${ResultProbe.formatValue(expected.frames[index].time)} s`,
        async renderFrame(index,capture){
          if(run!==expected)throw Error('结果已切换，视频导出中止。');
          slider.value=String(index);
          await showFrame(index);
          await ctx.captureFsiVideoFrame(capture);
        },
        progress:(index,count)=>ctx.status(`正在导出视频 ${index} / ${count}`)
      });
    }finally{
      recording=false;
      if(run===expected){slider.value=String(restore);await showFrame(restore);}
      updateFrameActions();
    }
    if(saved)ctx.status('已导出 WebM 视频。');
  }
  async function exportRun(){
    if(!run)throw Error('还没有三维流固耦合结果。');
    const handle=await window.chooseExportFile(window.uiText('TENSORA-三维流固耦合结果.json'),'application/json','.json');
    if(!handle)return;
    await window.writeExportFile(handle,async writer=>{
      await writer.write(`{"summary":${JSON.stringify(run)},"frames":[`);
      for(let i=0;i<run.frames.length;i++){
        const data=await loadFrame(i);
        const fields=Object.fromEntries(Object.entries({...data.nodeFields,...data.flowGeometry}).map(([k,v])=>[k,Array.from(v,x=>Number.isFinite(x)?x:null)]));
        const particles=data.particles?Object.fromEntries(Object.entries(data.particles.values).map(([k,v])=>[k,Array.from(v,x=>Number.isFinite(x)?x:null)])):undefined;
        await writer.write((i?',':'')+JSON.stringify({time:data.time,fields,particles}));
      }
      await writer.write(']}');
    });
    ctx.status('三维流固耦合结果已导出。');
  }

  // ------------------------------------------------------------ events
  const guard=fn=>async event=>{try{await fn(event);}catch(error){ctx.status(error.message);}};
  for(const id of [...Object.values(FORM),...FLOW_NUMERICS])$(id).addEventListener('change',()=>{syncForm();persist();});
  for(const id of SPH_IDS)$(id).addEventListener('change',()=>{syncForm();persist();});
  $('solid3dFsiKind').addEventListener('change',syncForm);
  $('solid3dFsiFluid').addEventListener('change',event=>{fluidId=event.target.value;refreshFluids();persist();});
  $('solid3dFsiAssign').addEventListener('click',guard(()=>{
    const face=ctx.selectedFace();if(face==null)throw Error('请先在视窗中点选流体外表面。');
    const kind=$('solid3dFsiKind').value,entry={kind};
    if(kind==='inlet'||kind==='farfield'){entry.velocity=Number($('solid3dFsiVelocity').value);if(!(entry.velocity>=0))throw Error('流速输入无效。');}
    if(kind==='outlet'){entry.pressure=Number($('solid3dFsiPressure').value);if(!Number.isFinite(entry.pressure))throw Error('出口压力输入无效。');}
    if(kind==='farfield'){
      entry.direction=['X','Y','Z'].map(a=>Number($('solid3dFsiDir'+a).value));
      if(!entry.direction.every(Number.isFinite)||!(Math.hypot(...entry.direction)>0))throw Error('来流方向不能为零向量。');
    }
    faces[String(face)]=entry;renderLists();ctx.draw();
  }));
  $('solid3dFsiClearFace').addEventListener('click',()=>{const face=ctx.selectedFace();if(face!=null){delete faces[String(face)];renderLists();ctx.draw();}});
  $('solid3dFsiClearAll').addEventListener('click',()=>{faces={};renderLists();ctx.draw();});
  $('solid3dRunFsi').addEventListener('click',guard(event=>runFsi(event.target)));
  $('solid3dCancelFsi').addEventListener('click',e=>window.cancelSpecialtyRun(request,e.currentTarget,ctx.status));
  $('solid3dFsiFrame').addEventListener('input',guard(()=>{stopPlayback();return showFrame(Number($('solid3dFsiFrame').value));}));
  $('solid3dPlayFsi').addEventListener('click',play);
  for(const [name,step] of [['Previous',-1],['Next',1]])$('solid3dFsi'+name).addEventListener('click',guard(()=>{
    stopPlayback();const slider=$('solid3dFsiFrame');slider.stepUp(step);return showFrame(Number(slider.value));
  }));
  $('solid3dFsiExportVideo').addEventListener('click',guard(exportVideo));
  $('solid3dExportFsi').addEventListener('click',guard(exportRun));
  $('solid3dFsiExportVtk').addEventListener('click',guard(async()=>{
    const {nodes,tets,tetVolumes}=ctx.getMesh(),summary=run,roles=summary.settings.volumeRoles;
    if(await FsiExport.saveSeries({run:summary,nodes,cells:tets,role:i=>roles[String(tetVolumes[i])],loadFrame:i=>loadFrame(i,summary)})){
      ctx.status('已导出。解压后在 ParaView 中打开 fsi.pvd。');
    }
  }));
  window.addEventListener('tensora-fsi-fluids-changed',()=>{if(!$('solid3dPage').hidden)refreshFluids();});
  window.addEventListener('tensora-fsi-fluid-selected',event=>{fluidId=event.detail?.id||fluidId;refreshFluids();persist();});
  try{const saved=JSON.parse(localStorage.getItem(STORAGE_KEY)||'null');if(saved)restore(saved);}catch{/* ignore */}
  syncForm();

  return {
    show,faceColor,volumeTint,snapshot,restore,stopPlayback,
    // Inputs for the pre-run check panel.
    context(){
      let settings=null;try{settings=readSettings();}catch{/* incomplete field */}
      return {settings,fluid:selectedFluid(),roles:allRoles(),faces:{...faces}};
    },
    frame:()=>frame,hasRun:()=>Boolean(run),run:()=>run,loadFrame,
    goToFrame(index){
      if(recording)return;
      stopPlayback();$('solid3dFsiFrame').value=String(index);
      showFrame(index).catch(error=>ctx.status(error.message));
    },
    fields:()=>run?(run.engine==='sph'?[...run.fields,'pressure','density']:run.fields):[],
    particles:()=>frame?.particles||null,
    // SPH runs: fluid and cavity volumes are represented by the particles, not by their initial surfaces.
    sphHiddenVolumes:()=>run?.engine==='sph'?new Set(Object.entries(run.settings.volumeRoles||{}).filter(([,r])=>r!=='solid').map(([v])=>v)):null,
    meshChanged(){
      request?.abort();stopPlayback();++loadTicket;run=null;frame=null;cache.clear();roles={};
      const slider=$('solid3dFsiFrame');slider.max=slider.value='0';
      renderLists();updateResultControls();
    },
    abort(){request?.abort();stopPlayback();}
  };
}
