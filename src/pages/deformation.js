// Independent specialty: no blast controls, history or shared result workspace.
let deformationEnabled=false,deformationResult=null,deformationController=null,deformationTicket=0;
let deformationCamera={zoom:1,panX:0,panY:0,bounds:null},deformationDrag=null;
function fitDeformationView(){deformationCamera={zoom:1,panX:0,panY:0,bounds:null};renderDeformation();}
function zoomDeformationView(factor,point){
  const box=document.getElementById('deformationCanvas').getBoundingClientRect(),p=point||{x:box.width/2,y:box.height/2},old=deformationCamera.zoom,next=Math.max(.1,Math.min(100,old*factor)),ratio=next/old;
  deformationCamera.panX=p.x-box.width/2-ratio*(p.x-box.width/2-deformationCamera.panX);
  deformationCamera.panY=p.y-box.height/2-ratio*(p.y-box.height/2-deformationCamera.panY);
  deformationCamera.zoom=next;renderDeformation();
}
let deformationProgress=null,deformationProgressTimer=null;
function updateDeformationProgress(update={}){
  const previous=deformationProgress||{fraction:0,completedIncrements:0};
  deformationProgress={...previous,...update,receivedAt:performance.now()};
  renderDeformationProgress();
}
function renderDeformationProgress(){
  const p=deformationProgress,host=document.getElementById('deformationProgressPanel');if(!p){host.hidden=true;return;}host.hidden=false;
  const elapsed=p.elapsedMs+(p.running?performance.now()-p.receivedAt:0),seconds=ms=>`${Math.ceil(Math.max(0,ms)/1000)} s`;
  const phases={preparing:'正在准备计算',solving:'正在求解',processing:'正在整理结果',complete:'计算完成',partial:'未完成目标载荷（可查看已收敛过程）',cancelled:'计算已取消。',failed:'计算失败'};
  host.dataset.state=p.phase;
  const bar=document.getElementById('deformationProgress');bar.value=Math.max(0,Math.min(1,p.fraction));
  document.getElementById('deformationProgressPhase').textContent=phases[p.phase]||phases.preparing;
  document.getElementById('deformationProgressPercent').textContent=`${(bar.value*100).toFixed(1)}%`;
  const eta=p.running&&p.phase==='solving'&&Number.isFinite(p.estimatedRemainingMs)?Math.max(0,p.estimatedRemainingMs-(performance.now()-p.receivedAt)):null;
  document.getElementById('deformationProgressDetails').textContent=`已完成 ${p.completedIncrements} 个增量 · 已用 ${seconds(elapsed)}`+(p.running&&['preparing','solving'].includes(p.phase)?(eta!==null?` · 预计剩余约 ${seconds(eta)}`:' · 正在估算剩余时间…'):'');
  document.getElementById('deformationProgressError').textContent=p.error||'';
}
async function readDeformationRunResponse(response,onProgress){
  if(!response.ok||!response.headers.get('content-type')?.includes('application/x-ndjson'))return response.json();
  const reader=response.body.getReader(),decoder=new TextDecoder();let pending='',result;
  function consume(line){if(!line.trim())return;const message=JSON.parse(line);if(message.type==='error')throw Error(message.error);if(message.type==='progress')onProgress(message);if(message.type==='result')result=message.result;}
  try{
    while(true){const {value,done}=await reader.read();pending+=decoder.decode(value,{stream:!done});let end;while((end=pending.indexOf('\n'))>=0){consume(pending.slice(0,end));pending=pending.slice(end+1);}if(done)break;}
    consume(pending);if(!result)throw Error('计算进度连接中断，请重新计算。');return result;
  }finally{reader.releaseLock();}
}
const deformationFields={planeMode:['deformationPlane',Number],finiteStrain:['deformationFinite',null],increments:['deformationIncrements',Number],maxIncrements:['deformationMaxIncrements',Number],loadFactor:['deformationLoadFactor',Number]};
function deformationMaterials(){
  const found=new Map();
  for(const r of scene.regions||[]){if(isAirRegion(r))continue;const m=materialSnapshotForRegion(r);if(m?.id)found.set(m.id,m);}
  return [...found.values()];
}
function renderDeformationMaterials(){
  const host=document.getElementById('deformationMaterialCards');host.replaceChildren();
  const materials=deformationMaterials(),settings=DeformationSettings.normalize(scene.deformationSettings||{});
  if(!materials.length){const p=document.createElement('p');p.className='blast-note';p.textContent='请先为实体区域分配材料。';host.append(p);return;}
  const saved={...(settings.materials||{})};
  for(const m of materials){
    // Old global cards are migrated once to independent material entries.
    const card=Object.hasOwn(saved,m.id)?saved[m.id]:DeformationSettings.normalizeMaterial(settings.materials?{}:settings);saved[m.id]=card;
    const section=document.createElement('section');section.className='deformation-material-card';section.dataset.deformationMaterial=m.id;
    const title=document.createElement('h3');title.textContent=m.name||m.id;const identity=document.createElement('p');identity.className='blast-note';identity.textContent=m.id;section.append(title,identity);
    const grid=document.createElement('div');grid.className='blast-form-grid';
    const label=document.createElement('label');label.className='blast-select-field';const text=document.createElement('span');text.textContent='材料本构';const select=document.createElement('select');select.dataset.deformationProperty='model';
    for(const [value,name]of [['plastic','J2 塑性 · 线性各向同性硬化'],['elastic','弹性 · 可启用几何非线性']]){const option=document.createElement('option');option.value=value;option.textContent=name;select.append(option);}select.value=card.model;label.append(text,select);grid.append(label);
    for(const [key,name,scale]of [['yieldStress','初始屈服应力 (MPa)',1e6],['hardening','塑性硬化模量 dσ/dεp (MPa)',1e6],['criticalPlasticStrain','损伤起始等效塑性应变',1]]){
      const label=document.createElement('label');label.className='number-field';const span=document.createElement('span');span.textContent=name;const input=document.createElement('input');input.type='number';input.step='any';input.min=key==='hardening'?'0':'0.000001';input.value=card[key]/scale;input.dataset.deformationProperty=key;input.dataset.scale=scale;input.disabled=card.model==='elastic';label.append(span,input);grid.append(label);
    }
    section.append(grid);section.addEventListener('change',()=>{
      for(const el of section.querySelectorAll('input'))el.disabled=select.value==='elastic';
      try{scene.deformationSettings=readDeformationControls();document.getElementById('deformationStatus').textContent='材料参数已更新，运行后生效。';}catch(e){document.getElementById('deformationStatus').textContent=e.message;}
    });host.append(section);
  }
  scene.deformationSettings={...settings,materials:saved};
}
function readDeformationControls(){
  const s={};for(const [key,[id,convert]] of Object.entries(deformationFields)){const el=document.getElementById(id);s[key]=convert?convert(el.value):el.checked;}
  s.materials={...(scene.deformationSettings?.materials||{})};
  for(const section of document.querySelectorAll('[data-deformation-material]')){
    const card={};for(const el of section.querySelectorAll('[data-deformation-property]'))card[el.dataset.deformationProperty]=el.tagName==='SELECT'?el.value:(el.value.trim()===''?NaN:Number(el.value)*Number(el.dataset.scale));
    s.materials[section.dataset.deformationMaterial]=DeformationSettings.normalizeMaterial(card);
  }
  return DeformationSettings.normalize(s);
}
function restoreDeformationControls(){
  const s=DeformationSettings.normalize(scene.deformationSettings||{});
  for(const [key,[id,convert]] of Object.entries(deformationFields)){const el=document.getElementById(id);if(!convert)el.checked=s[key];else el.value=['yieldStress','hardening'].includes(key)?s[key]/1e6:s[key];}
  renderDeformationMaterials();
}
function clearDeformationResult(){stopDeformationPlayback();deformationTicket++;deformationController?.abort();clearInterval(deformationProgressTimer);deformationProgress=null;renderDeformationProgress();deformationResult=null;resetDeformationResultSync();fitDeformationView();restoreDeformationControls();renderDeformation();}
function setDeformationEnabled(enabled){
  deformationEnabled=Boolean(enabled);document.getElementById('enableDeformationModule').checked=deformationEnabled;
  document.getElementById('professionalSummary').textContent='基础'+(blastModuleEnabled?' + 爆破':'')+(deformationEnabled?' + 损伤变形':'');
  document.querySelectorAll('[data-professional="deformation"]').forEach(el=>el.hidden=!deformationEnabled);
  try{localStorage.setItem('fem.deformation.enabled',String(deformationEnabled));}catch{}
  if(!deformationEnabled){stopDeformationPlayback();deformationController?.abort();if(currentPageKey().startsWith('deformation'))setPage('calculation');}
}
function initializeDeformation(){
  let enabled=false;try{enabled=localStorage.getItem('fem.deformation.enabled')==='true';}catch{}
  setDeformationEnabled(enabled);restoreDeformationControls();
  initializeDeformationResultSync();
  initializeDeformationPlayback();
  document.getElementById('deformationRecommendedSteps').addEventListener('click',()=>{
    document.getElementById('deformationIncrements').value=40;document.getElementById('deformationMaxIncrements').value=400;
    scene.deformationSettings=readDeformationControls();document.getElementById('deformationStatus').textContent='已设置 40 个初始增量和 400 个最大增量；收敛仍取决于模型与目标载荷。';
  });
  document.getElementById('viewPartialDeformation').addEventListener('click',()=>setPage('deformation-results'));
  window.addEventListener('femlanguagechange',renderDeformationProgress);
  document.getElementById('enableDeformationModule').addEventListener('change',e=>setDeformationEnabled(e.target.checked));
  for(const [id] of Object.values(deformationFields))document.getElementById(id).addEventListener('change',()=>{try{scene.deformationSettings=readDeformationControls();document.getElementById('deformationStatus').textContent='参数已更新，运行后生效。';}catch(e){document.getElementById('deformationStatus').textContent=e.message;}});
  document.getElementById('startDeformation').addEventListener('click',async()=>{
    if(deformationController)return;const ticket=++deformationTicket,controller=new AbortController();deformationController=controller;
    stopDeformationPlayback();
    const status=document.getElementById('deformationStatus');document.getElementById('startDeformation').disabled=true;document.getElementById('cancelDeformation').disabled=false;
    const started=performance.now();
    document.getElementById('viewPartialDeformation').hidden=true;
    updateDeformationProgress({phase:'preparing',fraction:0,completedIncrements:0,elapsedMs:0,estimatedRemainingMs:null,running:true,error:''});
    deformationProgressTimer=setInterval(renderDeformationProgress,500);
    try{
      const settings=readDeformationControls();scene.deformationSettings=settings;
      if(!scene.mesh?.elements?.length)throw Error('请先生成网格。');
      const payload=buildCalculationInputExport(),model=calculationInputPayloadToDirectModel(payload);model.planeMode=settings.planeMode;
      model.materials.forEach((m,i)=>{m.id=payload.materials[i].id;});
      status.textContent='CalculiX 正在进行增量非线性求解…';
      const response=await fetch('./api/deformation-runs',{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/x-ndjson'},body:JSON.stringify({model,settings}),signal:controller.signal});
      const result=await readDeformationRunResponse(response,p=>{if(ticket===deformationTicket)updateDeformationProgress({...p,phase:p.phase==='complete'?'processing':p.phase,running:true});});if(!response.ok||!result.ok)throw Error(result.error||'求解失败');
      if(ticket!==deformationTicket)return;stopDeformationPlayback();deformationResult=result;
      const partial=result.completed===false;
      updateDeformationProgress({phase:partial?'partial':'complete',fraction:result.frames.at(-1).time,completedIncrements:result.frames.length,elapsedMs:performance.now()-started,running:false,error:partial?result.termination.message:''});
      document.getElementById('viewPartialDeformation').hidden=!partial;
      const slider=document.getElementById('deformationFrame');slider.max=result.frames.length-1;slider.value=slider.max;
      baseResultSource='deformation';syncDeformationToBaseResults();fitDeformationView();
      updateDeformationPlaybackControls();
      status.textContent=partial?result.termination.message:`求解完成 · ${result.frames.length} 个增量 · ${result.runId}`;setPage('deformation-results');
    }catch(e){if(ticket===deformationTicket){status.textContent=e.name==='AbortError'?'计算已取消。':e.message;updateDeformationProgress({phase:e.name==='AbortError'?'cancelled':'failed',elapsedMs:performance.now()-started,running:false,error:status.textContent});}}
    finally{clearInterval(deformationProgressTimer);if(deformationController===controller)deformationController=null;document.getElementById('startDeformation').disabled=false;document.getElementById('cancelDeformation').disabled=true;}
  });
  document.getElementById('cancelDeformation').addEventListener('click',()=>deformationController?.abort());
  document.getElementById('generateDeformationMesh').addEventListener('click',async e=>{
    const status=document.getElementById('deformationStatus');if(calculationWorkflowRunning)return;
    const count=Number(document.getElementById('deformationMeshLimit').value);if(!Number.isInteger(count)||count<3){status.textContent='节点上限须为不小于 3 的整数。';return;}
    calculationWorkflowRunning=true;e.target.disabled=true;
    try{status.textContent='正在生成网格…';await autoGenerateAnalysisMesh({regenerateNodes:true,adaptive:false,maxNodes:count});status.textContent=`网格就绪：${scene.analysisNodes.length} 节点 / ${scene.mesh?.elements?.length||0} 单元`;}catch(error){status.textContent=error.message;}finally{calculationWorkflowRunning=false;e.target.disabled=false;render();}
  });
  for(const id of ['deformationFrame','deformationField','deformationScale'])document.getElementById(id).addEventListener('input',()=>{
    if(id==='deformationFrame')stopDeformationPlayback();
    syncDeformationToBaseResults();
    if(activeResultChannel==='deformation'){
      if(id==='deformationScale')setResultDeformationScale(Number(document.getElementById(id).value));
      if(id==='deformationField')setResultView(deformationFieldViews[document.getElementById(id).value]);
      renderResultView();
    }else if(resultChannels.deformation&&id==='deformationField')resultChannels.deformation.mode=deformationFieldViews[document.getElementById(id).value];
    renderDeformation();
  });
  const canvas=document.getElementById('deformationCanvas'),point=e=>{const b=canvas.getBoundingClientRect();return {x:e.clientX-b.left,y:e.clientY-b.top};};
  canvas.addEventListener('wheel',e=>{if(!deformationResult)return;e.preventDefault();zoomDeformationView(Math.exp(-e.deltaY*.0012),point(e));},{passive:false});
  canvas.addEventListener('pointerdown',e=>{if(!deformationResult||![0,1].includes(e.button))return;e.preventDefault();deformationDrag={id:e.pointerId,...point(e)};canvas.setPointerCapture(e.pointerId);canvas.classList.add('dragging');});
  canvas.addEventListener('pointermove',e=>{if(deformationDrag?.id!==e.pointerId)return;const p=point(e);deformationCamera.panX+=p.x-deformationDrag.x;deformationCamera.panY+=p.y-deformationDrag.y;deformationDrag={id:e.pointerId,...p};renderDeformation();});
  const release=()=>{deformationDrag=null;canvas.classList.remove('dragging');};
  canvas.addEventListener('pointerup',release);canvas.addEventListener('pointercancel',release);canvas.addEventListener('lostpointercapture',release);
  canvas.addEventListener('dblclick',fitDeformationView);
  document.getElementById('deformationFit').addEventListener('click',fitDeformationView);
  document.getElementById('deformationZoomIn').addEventListener('click',()=>zoomDeformationView(1.25));
  document.getElementById('deformationZoomOut').addEventListener('click',()=>zoomDeformationView(.8));
  window.addEventListener('resize',renderDeformation);
  document.getElementById('exportDeformation').addEventListener('click',async()=>{if(!deformationResult)return;try{const handle=await chooseExportFile(uiText('损伤变形结果.json'),'application/json','.json');if(handle)await writeExportFile(handle,w=>w.write(JSON.stringify(deformationResult)));}catch(e){document.getElementById('deformationResultStatus').textContent=e.message;}});
}
function deformationValue(frame,id,field,s){
  if(field==='displacement'){const v=frame.displacement[id]||[];return Math.hypot(v[0]||0,v[1]||0);}
  if(field==='plasticStrain'||field==='damage'){if(s.model!=='plastic')return 0;const v=frame.plasticStrain[id]?.[0]||0;return field==='damage'?v/s.criticalPlasticStrain:v;}
  if(field==='strain'){const [x=0,y=0,z=0,xy=0,yz=0,zx=0]=frame.strain[id]||[];return Math.sqrt(2*((x-y)**2+(y-z)**2+(z-x)**2)/9+4*(xy**2+yz**2+zx**2)/3);}
  const [x=0,y=0,z=0,xy=0,yz=0,zx=0]=frame.stress[id]||[];
  return Math.sqrt(((x-y)**2+(y-z)**2+(z-x)**2)/2+3*(xy**2+yz**2+zx**2))/1e6;
}
function renderDeformation(){
  if(currentPageKey()!=='deformation-results')return;
  const canvas=document.getElementById('deformationCanvas'),box=canvas.getBoundingClientRect(),ctx=canvas.getContext('2d'),dpr=window.devicePixelRatio||1;
  if(!box.width||!box.height)return;canvas.width=box.width*dpr;canvas.height=box.height*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);ctx.fillStyle='#f2f7f9';ctx.fillRect(0,0,box.width,box.height);
  const summary=document.getElementById('deformationResultStatus');if(!deformationResult){summary.textContent='请在损伤变形面板运行计算。';return;}
  const r=deformationResult,frame=r.frames[Number(document.getElementById('deformationFrame').value)]||r.frames.at(-1),field=document.getElementById('deformationField').value,scale=Number(document.getElementById('deformationScale').value);
  const notice=document.getElementById('deformationResultNotice');notice.hidden=r.completed!==false;notice.textContent=r.completed===false?r.termination.message:'';
  const cardFor=e=>r.materialSettings?.[e.materialNo??'legacy']||DeformationSettings.materialFor(r.settings,r.model.materials?.find(m=>m.materialNo===e.materialNo)?.id??String(e.materialNo??'legacy'));
  if(['plasticStrain','damage'].includes(field)&&!r.model.elements.some(e=>cardFor(e).model==='plastic')){summary.textContent='本次为弹性模型，没有塑性应变或损伤起始指标。';return;}
  if(!Number.isFinite(scale)||scale<0)return;
  const nodes=new Map(r.model.nodes.map(n=>[n.nodeNo,n])),coords=new Map();let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity,peak=0;
  for(const n of nodes.values()){const u=frame.displacement[n.nodeNo]||[0,0],p={x:n.x+u[0]*scale,y:n.y+u[1]*scale};coords.set(n.nodeNo,p);minX=Math.min(minX,p.x);minY=Math.min(minY,p.y);maxX=Math.max(maxX,p.x);maxY=Math.max(maxY,p.y);}
  for(const e of r.model.elements)for(const id of [e.node1,e.node2,e.node3])peak=Math.max(peak,deformationValue(frame,id,field,cardFor(e)));
  const colorPeak=document.getElementById('deformationFixedColor').checked?deformationPlaybackColorPeak(r,field):peak;
  deformationCamera.bounds||={minX,maxX,minY,maxY};const b=deformationCamera.bounds;
  const k=Math.min((box.width-80)/Math.max(b.maxX-b.minX,.0001),(box.height-80)/Math.max(b.maxY-b.minY,.0001))*deformationCamera.zoom;
  const project=p=>[box.width/2+deformationCamera.panX+(p.x-(b.minX+b.maxX)/2)*k,box.height/2+deformationCamera.panY-(p.y-(b.minY+b.maxY)/2)*k];
  for(const e of r.model.elements){const ids=[e.node1,e.node2,e.node3],card=cardFor(e),v=ids.reduce((sum,id)=>sum+deformationValue(frame,id,field,card),0)/3;ctx.beginPath();ids.forEach((id,i)=>{const p=project(coords.get(id));if(i)ctx.lineTo(...p);else ctx.moveTo(...p);});ctx.closePath();ctx.fillStyle=`hsl(${240-240*Math.max(0,Math.min(1,colorPeak?v/colorPeak:0))},75%,55%)`;ctx.fill();if(r.model.elements.length<10000){ctx.strokeStyle='#23405250';ctx.lineWidth=.4;ctx.stroke();}}
  if(document.getElementById('deformationShowLoads').checked)drawDeformationPlaybackLoads(ctx,r,frame,coords,project);
  const unit=field==='stress'?' MPa':field==='displacement'?' m':'';
  document.getElementById('deformationZoomReadout').textContent=`${Math.round(deformationCamera.zoom*100)}%`;
  const legend=document.getElementById('deformationLegend');legend.replaceChildren();const low=document.createElement('span'),ramp=document.createElement('span'),high=document.createElement('span');low.textContent='0'+unit;ramp.className='deformation-legend-ramp';high.textContent=colorPeak.toExponential(4)+unit;legend.append(low,ramp,high);
  summary.textContent=`${r.model.modelName} · CalculiX · 载荷比例 ${(frame.time*r.settings.loadFactor).toFixed(4)} · 节点峰值 ${peak.toExponential(4)}${unit} · 变形显示 ${scale}×`;
}
