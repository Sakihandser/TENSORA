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
    while(true){
      const {value,done}=await reader.read(),chunk=decoder.decode(value,{stream:!done});
      const lines=chunk.split('\n');
      if(lines.length===1)pending+=chunk;
      else{
        consume(pending+lines[0]);
        for(let i=1;i<lines.length-1;i++)consume(lines[i]);
        pending=lines.at(-1);
      }
      if(done)break;
    }
    consume(pending);if(!result)throw Error('计算进度连接中断，请重新计算。');return result;
  }finally{reader.releaseLock();}
}
const deformationFields={solver:['deformationSolver',String],fractureLoading:['fractureLoading',String],fractureDisplacement:['fractureDisplacement',Number],planeMode:['deformationPlane',Number],finiteStrain:['deformationFinite',null],increments:['deformationIncrements',Number],maxIncrements:['deformationMaxIncrements',Number],loadFactor:['deformationLoadFactor',Number]};
function syncFractureControls(){
  const active=document.getElementById('deformationSolver').value==='phast';
  document.getElementById('fractureSettings').hidden=!active;
  document.getElementById('deformationMaxIncrements').disabled=active;
  document.getElementById('deformationScopePrimary').textContent=active?'PhAST AT2 相场损伤 d 会参与刚度退化，历史场约束损伤不可逆。裂纹以连续弥散损伤带表示，不包含离散裂面接触、碎块碰撞或单元删除。':'当前提供 PEEQ / 起始阈值指标，达到 1 表示达到用户定义的塑性应变阈值。这是后处理评估，不参与本构积分；尚不提供损伤演化、刚度退化、单元删除或裂纹扩展。';
  document.getElementById('deformationScopeSecondary').textContent=active?'当前接入小变形脆性断裂、平面应变及准静态加载；不与 J2 塑性或有限变形混算。相场长度与网格分辨率共同影响裂纹宽度，结果需要网格收敛验证。':'有限变形应力为 Cauchy 应力，应变遵循 CalculiX 原生输出定义。等效塑性应变为外推到节点的场量。塑性与损伤指标只适用于 J2 塑性模型。';
  document.getElementById('deformationMeshNote').textContent=active?'复用结构中的三角形网格，PhAST 使用 T3 单元。输入采用 m、N、Pa、J/m²，厚度固定 1 m。当前相场路径最多支持 1 万节点。':'共享结构几何、材料及三角形网格，使用 CalculiX CPS3 / CPE3 单元。请在结构绘制中配置材料、约束与载荷。单位：m、N、Pa；厚度固定 1 m。';
  const modelOption=document.getElementById('deformationField').querySelector('option[value="damage"]');
  document.getElementById('deformationField').querySelector('option[value="plasticStrain"]').disabled=Boolean(deformationResult?.fracture);
  modelOption.textContent=deformationResult?.fracture?'相场损伤 d（0–1，参与刚度退化）':'损伤起始指标 PEEQ / 阈值';
}
function deformationMaterials(){
  const found=new Map();
  for(const r of scene.regions||[]){if(isAirRegion(r))continue;const m=materialSnapshotForRegion(r);if(m?.id)found.set(m.id,m);}
  return [...found.values()];
}
function deformationCardForModel(settings,id){
  const linked=linkedDeformationMaterial(id);
  const override=settings.materials&&Object.hasOwn(settings.materials,id)?settings.materials[id]:null;
  return {linked,override,card:override||linked?.card||DeformationSettings.normalizeMaterial(settings)};
}
function renderDeformationMaterials(){
  const host=document.getElementById('deformationMaterialCards');host.replaceChildren();
  const materials=deformationMaterials(),settings=DeformationSettings.normalize(scene.deformationSettings||{});
  if(!materials.length){const p=document.createElement('p');p.className='blast-note';p.textContent='请先为实体区域分配材料。';host.append(p);return;}
  for(const m of materials){
    const {linked,override,card}=deformationCardForModel(settings,m.id);
    const section=document.createElement('section');section.className='deformation-material-card';section.dataset.deformationMaterial=m.id;
    const title=document.createElement('h3');title.textContent=m.name||m.id;
    const identity=document.createElement('p');identity.className='blast-note';
    identity.textContent=linked?(override?'当前模型覆盖材料库参数':'自动使用关联材料卡'):(override?'当前模型材料参数':'未关联材料库，使用当前模型默认值');
    if(linked)identity.append(' · ',linked.name);
    section.append(title,identity,createDeformationCardFields(card,{allowMazars:false}));
    if(linked&&override){
      const reset=document.createElement('button');reset.type='button';reset.textContent='恢复使用关联材料卡';
      reset.addEventListener('click',()=>{
        const overrides={...scene.deformationSettings.materials};delete overrides[m.id];
        scene.deformationSettings={...scene.deformationSettings,materials:overrides};
        renderDeformationMaterials();
      });
      section.append(reset);
    }
    section.addEventListener('change',()=>{
      try{
        const current=readDeformationControls();
        current.materials[m.id]=readDeformationCard(section);
        scene.deformationSettings=current;
        if(linked&&!override)renderDeformationMaterials();
        else identity.textContent=linked?'当前模型覆盖材料库参数':'当前模型材料参数';
        document.getElementById('deformationStatus').textContent='材料参数已更新，运行后生效。';
      }catch(e){document.getElementById('deformationStatus').textContent=e.message;}
    });
    host.append(section);
  }
}
function linkedDeformationMaterial(materialId){
  const id=materialById(materialId)?.deformationMaterialId;
  return deformationMaterialLibrary.find(entry=>entry.id===id);
}
function createDeformationCardFields(card,{allowMazars=true}={}){
    const grid=document.createElement('div');grid.className='blast-form-grid';
    const label=document.createElement('label');label.className='blast-select-field';const text=document.createElement('span');text.textContent='材料本构';const select=document.createElement('select');select.dataset.deformationProperty='model';
    for(const [value,name]of [['plastic','J2 塑性 · 各向同性硬化'],['elastic','弹性 · 可启用几何非线性'],['neoHooke','Neo-Hooke'],['mooneyRivlin','Mooney–Rivlin'],['phaseField','AT2 相场脆性断裂（PhAST）'],['crackBand','裂带断裂（三维 OOFEM）'],['mazars','Mazars 混凝土损伤（三维 Code_Aster）']]){const option=document.createElement('option');option.value=value;option.textContent=name;option.disabled=['crackBand','mazars'].includes(value)&&!allowMazars;select.append(option);}select.value=card.model;label.append(text,select);grid.append(label);
    const fields=[
      ['yieldStress','初始屈服应力 (MPa)',1e6,['plastic']],
      ['hardening','塑性硬化模量 dσ/dεp (MPa)',1e6,['plastic']],
      ['criticalPlasticStrain','损伤起始等效塑性应变',1,['plastic']],
      ['fractureEnergy','断裂能 Gc (J/m²)',1,['phaseField']],
      ['fractureLength','相场长度 l₀ (m)',1,['phaseField']],
      ['c10','超弹性系数 C10 (MPa)',1e6,['neoHooke','mooneyRivlin']],
      ['c01','超弹性系数 C01 (MPa)',1e6,['mooneyRivlin']],
      ['d1','可压缩性参数 D1 (MPa⁻¹)',1e-6,['neoHooke','mooneyRivlin']],
      ['epsd0','损伤起始应变 EPSD0',1,['mazars']],
      ['tensileStrength','单轴抗拉强度 (MPa)',1e6,['crackBand']],
      ['crackBandEnergy','裂带断裂能 Gf (J/m²)',1,['crackBand']],
      ...['ac','at','bc','bt','k'].map(key=>[key,key.toUpperCase(),1,['mazars']])
    ];
    const controls=fields.map(([key,name,scale,models])=>{
      const label=document.createElement('label');label.className='number-field';
      const span=document.createElement('span');span.textContent=name;
      const input=document.createElement('input');input.type='number';input.step='any';input.min='0';
      input.value=(card[key]??DeformationSettings.hyperelasticDefaults[key]??DeformationSettings.mazarsDefaults[key]??DeformationSettings.crackBandDefaults[key])/scale;
      input.dataset.deformationProperty=key;input.dataset.scale=scale;
      label.append(span,input);grid.append(label);
      return {input,label,models};
    });
    const curveLabel=document.createElement('label');curveLabel.className='number-field';
    const curveText=document.createElement('span');curveText.textContent='硬化曲线（可选，每行：真应力 MPa, 塑性应变）';
    const curve=document.createElement('textarea');curve.rows=3;curve.dataset.deformationProperty='hardeningCurve';
    curve.value=(card.hardeningCurve??[]).map(([stress,strain])=>`${stress/1e6}, ${strain}`).join('\n');
    curveLabel.append(curveText,curve);grid.append(curveLabel);
    controls.push({input:curve,label:curveLabel,models:['plastic']});
    const update=()=>{
      for(const {input,label,models} of controls)input.disabled=label.hidden=!models.includes(select.value);
      if(select.value==='plastic'&&curve.value.trim()){
        for(const {input} of controls.slice(0,2))input.disabled=true;
      }
    };
    curve.addEventListener('input',update);
    select.addEventListener('change',update);update();
    return grid;
}
function readDeformationCard(section){
  const card={};
  for(const el of section.querySelectorAll('[data-deformation-property]')){
    if(el.dataset.deformationProperty==='hardeningCurve'){
      if(!el.disabled&&el.value.trim())card.hardeningCurve=el.value.trim().split(/\r?\n/).filter(line=>line.trim()).map(line=>{
        const cells=line.split(/[,，]/).map(cell=>cell.trim());
        return cells.map((cell,i)=>cell?Number(cell)*(i===0?1e6:1):NaN);
      });
      continue;
    }
    const value=el.tagName==='SELECT'?el.value:(el.value.trim()===''?NaN:Number(el.value)*Number(el.dataset.scale));
    if(!el.disabled||Number.isFinite(value))card[el.dataset.deformationProperty]=value;
  }
  return DeformationSettings.normalizeMaterial(card);
}
let selectedDeformationLibraryCard=null;
function renderDeformationLibraryList(){
  const list=document.getElementById('deformationLibraryList');
  list.replaceChildren();
  if(!deformationMaterialLibrary.length){
    const empty=document.createElement('p');empty.className='blast-note';empty.textContent='暂无已保存的材料卡。';list.append(empty);
  }
  for(const entry of deformationMaterialLibrary){
    const button=document.createElement('button');button.type='button';button.dataset.deformationCard=entry.id;
    button.setAttribute('aria-pressed',String(entry.id===selectedDeformationLibraryCard));
    const name=document.createElement('strong');name.textContent=entry.name;
    const links=document.createElement('small');
    const linked=materialLibrary.filter(material=>material.deformationMaterialId===entry.id);
    linked.forEach((material,index)=>{
      if(index)links.append(' · ');
      links.append(material.name);
    });
    if(!linked.length)links.textContent='未关联基础材料';
    button.append(name,links);
    list.append(button);
  }
}
function renderDeformationLibrary(selectedId=selectedDeformationLibraryCard){
  const record=selectedId===''?null:deformationMaterialLibrary.find(entry=>entry.id===selectedId)||deformationMaterialLibrary[0];
  selectedDeformationLibraryCard=record?.id??(selectedId===''?'':null);
  renderDeformationLibraryList();
  document.getElementById('deformationLibraryEditorTitle').textContent=record?'编辑材料卡':'新建材料卡';
  document.getElementById('deformationLibraryName').value=record?.name||'';
  document.getElementById('deformationLibrarySource').value=record?.sourceUrl||'';
  document.getElementById('deformationLibraryNotes').value=record?.notes||'';
  document.getElementById('deformationLibraryFields').replaceChildren(createDeformationCardFields(record?.card||DeformationSettings.normalizeMaterial()));
}
function renderDeformationAssociations(){
  const base=document.getElementById('deformationAssociationMaterial'),card=document.getElementById('deformationAssociationCard');
  const baseId=base.value;
  base.replaceChildren(...materialLibrary.map(entry=>new Option(entry.name,entry.id)));
  if(materialLibrary.some(entry=>entry.id===baseId))base.value=baseId;
  const linked=materialById(base.value)?.deformationMaterialId;
  card.replaceChildren(new Option('不关联',''));
  for(const entry of deformationMaterialLibrary)card.add(new Option(entry.name,entry.id));
  if(linked&&!deformationMaterialLibrary.some(entry=>entry.id===linked))card.add(new Option(linked,linked));
  card.value=linked||'';
  document.getElementById('saveDeformationAssociation').disabled=!materialStorageConnected||!base.value;
}
function renderDeformationLibraryStorage(){
  const notice=document.getElementById('deformationLibraryStorage');
  notice.textContent=materialStorageConnected?'':materialWriteUnavailable;
  notice.hidden=materialStorageConnected;
  document.getElementById('saveDeformationLibraryCard').disabled=!materialStorageConnected;
}
async function saveDeformationLibraryChange(endpoint,data){
  if(!materialStorageConnected)throw Error(materialWriteUnavailable);
  const response=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  if(response.status===404||response.status===405)throw Error(legacyMaterialServiceMessage);
  const payload=await response.json();
  if(!response.ok)throw Error(payload.error||`HTTP ${response.status}`);
  applyProjectMaterials(payload);
  const base=materialById(materialUi.id.value);
  renderDeformationMaterialLink(base?.deformationMaterialId);
  renderDeformationMaterials();
}
function initializeDeformationLibrary(){
  const status=document.getElementById('deformationLibraryStatus');
  const base=document.getElementById('deformationAssociationMaterial'),card=document.getElementById('deformationAssociationCard');
  const associationStatus=document.getElementById('deformationAssociationStatus');
  document.getElementById('deformationLibraryList').addEventListener('click',e=>{
    const button=e.target.closest('[data-deformation-card]');
    if(!button)return;
    status.textContent='';
    renderDeformationLibrary(button.dataset.deformationCard);
    document.querySelector('#deformationLibraryList [aria-pressed="true"]')?.focus();
  });
  document.getElementById('newDeformationLibraryCard').addEventListener('click',()=>{
    status.textContent='';renderDeformationLibrary('');document.getElementById('deformationLibraryName').focus();
  });
  document.getElementById('deformationLibraryForm').addEventListener('submit',async e=>{
    e.preventDefault();
    const button=document.getElementById('saveDeformationLibraryCard');button.disabled=true;
    try{
      const record=DeformationSettings.normalizeLibraryCard({
        id:selectedDeformationLibraryCard||'def-'+crypto.randomUUID(),
        name:document.getElementById('deformationLibraryName').value,
        sourceUrl:document.getElementById('deformationLibrarySource').value,
        notes:document.getElementById('deformationLibraryNotes').value,
        card:readDeformationCard(document.getElementById('deformationLibraryFields')),
      });
      await saveDeformationLibraryChange('./api/deformation-materials',record);
      renderDeformationLibrary(record.id);
      renderDeformationAssociations();
      status.textContent='材料卡已保存。';
    }catch(e){status.textContent=e.message;}
    finally{button.disabled=!materialStorageConnected;}
  });
  base.addEventListener('change',()=>{associationStatus.textContent='';renderDeformationAssociations();base.focus();});
  card.addEventListener('change',()=>{associationStatus.textContent='';});
  document.getElementById('deformationAssociationsForm').addEventListener('submit',async e=>{
    e.preventDefault();
    const button=document.getElementById('saveDeformationAssociation');button.disabled=true;
    try{
      await saveDeformationLibraryChange('./api/deformation-material-links',{materialId:base.value,cardId:card.value||null});
      renderDeformationLibraryList();
      associationStatus.textContent='材料关联已保存。';
    }catch(e){associationStatus.textContent=e.message;}
    finally{button.disabled=!materialStorageConnected||!base.value;}
  });
}
function readDeformationControls(){
  const s={...scene.deformationSettings,materials:{...scene.deformationSettings?.materials}};
  for(const [key,[id,convert]] of Object.entries(deformationFields)){const el=document.getElementById(id);s[key]=convert?convert(el.value):el.checked;}
  return DeformationSettings.normalize(s);
}
function restoreDeformationControls(){
  const s=DeformationSettings.normalize(scene.deformationSettings||{});
  // Legacy files can carry a customized card shared by all their materials.
  if(!s.materials&&(s.hardeningCurve||['model','yieldStress','hardening','criticalPlasticStrain'].some(key=>s[key]!==DeformationSettings.defaults[key]))){
    const card=DeformationSettings.normalizeMaterial(s);
    scene.deformationSettings={...s,materials:Object.fromEntries(deformationMaterials().map(m=>[m.id,card]))};
  }
  for(const [key,[id,convert]] of Object.entries(deformationFields)){const el=document.getElementById(id);if(!convert)el.checked=s[key];else el.value=['yieldStress','hardening'].includes(key)?s[key]/1e6:s[key];}
  renderDeformationMaterials();
  syncFractureControls();
}
function clearDeformationResult(){stopDeformationPlayback();deformationTicket++;deformationController?.abort();clearInterval(deformationProgressTimer);deformationProgress=null;renderDeformationProgress();deformationResult=null;resetDeformationResultSync();fitDeformationView();restoreDeformationControls();renderDeformation();}
function setDeformationEnabled(enabled){
  deformationEnabled=Boolean(enabled);document.getElementById('enableDeformationModule').checked=deformationEnabled;
  document.getElementById('professionalSummary').textContent='基础'+(blastModuleEnabled?' + 爆破':'')+(deformationEnabled?' + 损伤变形':'');
  document.querySelectorAll('[data-professional="deformation"]').forEach(el=>el.hidden=!deformationEnabled);
  try{localStorage.setItem('fem.deformation.enabled',String(deformationEnabled));}catch{}
  if(!deformationEnabled){
    window.dispatchEvent(new Event('tensora-solid3d-deformation-disabled'));
    stopDeformationPlayback();deformationController?.abort();baseResultSource='static';
    if(activeResultChannel==='deformation'){
      activateResultWorkspace('static');
      if(currentPageKey()==='results')loadCalculationResultsFromProjectFolder({quietMissing:true});
    }
    if(currentPageKey().startsWith('deformation'))setPage('calculation');
  }
  syncBaseResultSourceAvailability();
}
function initializeDeformation(){
  let enabled=false;try{enabled=localStorage.getItem('fem.deformation.enabled')==='true';}catch{}
  setDeformationEnabled(enabled);restoreDeformationControls();
  initializeDeformationLibrary();
  initializeDeformationResultSync();
  initializeDeformationPlayback();
  document.getElementById('deformationSolver').addEventListener('change',syncFractureControls);
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
      const saved=readDeformationControls();scene.deformationSettings=saved;
      if(!scene.mesh?.elements?.length)throw Error('请先生成网格。');
      for(const section of document.querySelectorAll('[data-deformation-material]'))readDeformationCard(section);
      if(scene.analysisNodePlacement||scene.mesh.metadata?.stale){
        await ensureCalculationMeshReadyForExport({adaptive:false,maxNodes:Math.min(200000,scene.analysisNodes.length)});
        controller.signal.throwIfAborted();
      }
      const settings={...saved};
      const payload=buildCalculationInputExport(),model=calculationInputPayloadToDirectModel(payload);model.planeMode=settings.planeMode;
      model.materials.forEach((m,i)=>{m.id=payload.materials[i].id;});
      settings.materials=Object.fromEntries(model.materials.map(m=>[m.id,deformationCardForModel(saved,m.id).card]));
      if(settings.solver==='phast'&&(settings.finiteStrain||settings.planeMode!==1))throw Error('PhAST 断裂路径目前要求小变形平面应变。');
      status.textContent=settings.solver==='phast'?'PhAST 正在进行相场断裂求解…':'CalculiX 正在进行增量非线性求解…';
      const response=await fetch('./api/deformation-runs',{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/x-ndjson'},body:JSON.stringify({model,settings}),signal:controller.signal});
      const result=await readDeformationRunResponse(response,p=>{if(ticket===deformationTicket)updateDeformationProgress({...p,phase:p.phase==='complete'?'processing':p.phase,running:true});});if(!response.ok||!result.ok)throw Error(result.error||'求解失败');
      if(ticket!==deformationTicket||!deformationEnabled)return;stopDeformationPlayback();deformationResult=result;
      syncFractureControls();
      const partial=result.completed===false;
      updateDeformationProgress({phase:partial?'partial':'complete',fraction:result.termination?.convergedFraction??result.frames.at(-1).time,completedIncrements:result.completedIncrements??(result.frames.length-(result.fracture?1:0)),elapsedMs:performance.now()-started,running:false,error:[partial?result.termination.message:'',...(result.warnings||[])].filter(Boolean).join('\n')});
      document.getElementById('viewPartialDeformation').hidden=!partial;
      const slider=document.getElementById('deformationFrame');slider.max=result.frames.length-1;slider.value=slider.max;
      baseResultSource='deformation';syncDeformationToBaseResults();fitDeformationView();
      updateDeformationPlaybackControls();
      if(result.fracture)document.getElementById('deformationField').value='damage';
      status.textContent=partial?result.termination.message:`求解完成 · ${result.frames.length} 个结果帧 · ${result.runId}`;setPage('deformation-results');
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
  if(field==='damage'&&frame.damage)return frame.damage[id]?.[0]||0;
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
  const notice=document.getElementById('deformationResultNotice');notice.textContent=[r.completed===false?r.termination.message:'',...(r.warnings||[])].filter(Boolean).join('\n');notice.hidden=!notice.textContent;
  const cardFor=e=>r.materialSettings?.[e.materialNo??'legacy']||DeformationSettings.materialFor(r.settings,r.model.materials?.find(m=>m.materialNo===e.materialNo)?.id??String(e.materialNo??'legacy'));
  if(['plasticStrain','damage'].includes(field)&&!(field==='damage'&&r.fracture)&&!r.model.elements.some(e=>cardFor(e).model==='plastic')){summary.textContent='本次模型没有塑性应变或损伤起始指标。';return;}
  if(!Number.isFinite(scale)||scale<0)return;
  const nodes=new Map(r.model.nodes.map(n=>[n.nodeNo,n])),coords=new Map();let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity,peak=0;
  for(const n of nodes.values()){const u=frame.displacement[n.nodeNo]||[0,0],p={x:n.x+u[0]*scale,y:n.y+u[1]*scale};coords.set(n.nodeNo,p);minX=Math.min(minX,p.x);minY=Math.min(minY,p.y);maxX=Math.max(maxX,p.x);maxY=Math.max(maxY,p.y);}
  for(const e of r.model.elements)for(const id of [e.node1,e.node2,e.node3])peak=Math.max(peak,deformationValue(frame,id,field,cardFor(e)));
  const colorPeak=r.fracture&&field==='damage'?1:document.getElementById('deformationFixedColor').checked?deformationPlaybackColorPeak(r,field):peak;
  deformationCamera.bounds||={minX,maxX,minY,maxY};const b=deformationCamera.bounds;
  const k=Math.min((box.width-80)/Math.max(b.maxX-b.minX,.0001),(box.height-80)/Math.max(b.maxY-b.minY,.0001))*deformationCamera.zoom;
  const project=p=>[box.width/2+deformationCamera.panX+(p.x-(b.minX+b.maxX)/2)*k,box.height/2+deformationCamera.panY-(p.y-(b.minY+b.maxY)/2)*k];
  for(const e of r.model.elements){const ids=[e.node1,e.node2,e.node3],card=cardFor(e),v=ids.reduce((sum,id)=>sum+deformationValue(frame,id,field,card),0)/3;ctx.beginPath();ids.forEach((id,i)=>{const p=project(coords.get(id));if(i)ctx.lineTo(...p);else ctx.moveTo(...p);});ctx.closePath();ctx.fillStyle=`hsl(${240-240*Math.max(0,Math.min(1,colorPeak?v/colorPeak:0))},75%,55%)`;ctx.fill();if(r.model.elements.length<10000){ctx.strokeStyle='#23405250';ctx.lineWidth=.4;ctx.stroke();}}
  if(document.getElementById('deformationShowLoads').checked)drawDeformationPlaybackLoads(ctx,r,frame,coords,project);
  const unit=field==='stress'?' MPa':field==='displacement'?' m':'';
  document.getElementById('deformationZoomReadout').textContent=`${Math.round(deformationCamera.zoom*100)}%`;
  const legend=document.getElementById('deformationLegend');legend.replaceChildren();const low=document.createElement('span'),ramp=document.createElement('span'),high=document.createElement('span');low.textContent='0'+unit;ramp.className='deformation-legend-ramp';high.textContent=colorPeak.toExponential(4)+unit;legend.append(low,ramp,high);
  document.getElementById('deformationDamageScope').textContent=r.fracture?'相场损伤参与刚度退化；裂纹以弥散损伤带表示，不是张开的离散裂面。':'云图按三角形节点平均值着色；上方显示节点峰值。损伤起始指标不表示损伤演化或刚度退化。';
  summary.textContent=`${r.model.modelName} · ${r.solver||'CalculiX'} · 载荷比例 ${(frame.time*r.settings.loadFactor).toFixed(4)} · 节点峰值 ${peak.toExponential(4)}${unit} · 变形显示 ${scale}×`;
  if(typeof drawDeformationProbeMarkers==='function'){
    const cx=(b.minX+b.maxX)/2,cy=(b.minY+b.maxY)/2;
    drawDeformationProbeMarkers(ctx,{scale,project,inverse:s=>({x:(s.x-box.width/2-deformationCamera.panX)/k+cx,y:-(s.y-box.height/2-deformationCamera.panY)/k+cy})});
  }
}
