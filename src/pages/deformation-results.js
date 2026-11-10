// Present the same nonlinear snapshot in the standard results workspace.
// This adapter never applies a nonlinear snapshot to the static scene or solver.
let baseResultSource='static',deformationSyncedResult=null,deformationSyncedFrame=-1;
const deformationFieldViews={displacement:'deformation',stress:'stress',strain:'strain',plasticStrain:'plasticStrain',damage:'damage'};
function syncBaseResultSourceAvailability(){
  document.getElementById('baseResultSourcePanel').hidden=!deformationEnabled||activeResultChannel==='blast';
}
function drawDeformationBaseScalar(key){
  const data=calculationResultData;if(!data?.deformation)return;
  const range={min:0,max:data.fracture&&key==='damage'?1:Math.max(data.ranges[key]?.max||0,1e-30)},factor=resultDisplacementFactor(data);
  for(const e of data.elements)drawResultElement(e.nodes.map(n=>deformedResultNode(n,factor)),resultColorForScalar(e[key],range),'rgba(30,41,59,.2)');
}
function setDeformationBaseLegend(data,key){
  const title=key==='damage'?(data.fracture?'相场损伤 d（0–1，参与刚度退化）':'损伤起始指标'):'等效塑性应变 PEEQ',max=data.fracture&&key==='damage'?1:data.ranges[key]?.max||0;
  resultUi.legend.replaceChildren();
  const heading=document.createElement('div');heading.className='legend-title';heading.textContent=title;
  const ramp=document.createElement('div');ramp.className='legend-ramp';const values=document.createElement('div');values.textContent=`0 → ${max.toExponential(4)}`;
  const note=document.createElement('p');note.textContent=data.fracture?'相场损伤参与刚度退化；裂纹以弥散损伤带表示，不是张开的离散裂面。':'应力与应变为节点外推值的单元平均；损伤起始指标不代表刚度退化。';resultUi.legend.append(heading,ramp,values,note);
}
function deformationResultCard(result,element){
  return result.materialSettings?.[element.materialNo??'legacy']||DeformationSettings.materialFor(result.settings,result.model.materials?.find(m=>m.materialNo===element.materialNo)?.id??String(element.materialNo??'legacy'));
}
function buildDeformationResultSnapshot(r,index){
  const frame=r.frames[index],input={...r.model,planeMode:r.settings.planeMode,elements:r.model.elements.map(e=>({...e,nodeNumbers:e.nodeNumbers||[e.node1,e.node2,e.node3]}))};
  const mean=(ids,field,component)=>ids.reduce((sum,id)=>sum+(frame[field][id]?.[component]||0),0)/ids.length;
  const nodeDisplacements=input.nodes.map(n=>{const [ux=0,uy=0]=frame.displacement[n.nodeNo]||[];return {nodeNo:n.nodeNo,ux,uy,magnitude:Math.hypot(ux,uy)};});
  const elementResults=input.elements.map(e=>{
    const ids=e.nodeNumbers,card=deformationResultCard(r,e),elemental=frame.elementFields?.[e.elementNo],
      [sx,sy,sz,xy,yz,zx]=elemental?.stress||[0,1,2,3,4,5].map(i=>mean(ids,'stress',i)),[ex,ey,ez,exy,eyz,ezx]=elemental?.strain||[0,1,2,3,4,5].map(i=>mean(ids,'strain',i));
    const plasticStrain=card.model==='plastic'?mean(ids,'plasticStrain',0):0;
    return {elementNo:e.elementNo,stressXx:sx,stressYy:sy,stressZz:sz,stressXy:xy,stressYx:xy,strainXx:ex,strainYy:ey,strainZz:ez,strainXy:exy,strainYx:exy,
      equivalentStress:Math.sqrt(((sx-sy)**2+(sy-sz)**2+(sz-sx)**2)/2+3*(xy**2+yz**2+zx**2)),
      equivalentStrain:Math.sqrt(2*((ex-ey)**2+(ey-ez)**2+(ez-ex)**2)/9+4*(exy**2+eyz**2+ezx**2)/3),
      ...(r.fracture?{}:{plasticStrain}),damage:r.fracture?(elemental?.damage??mean(ids,'damage',0)):plasticStrain/card.criticalPlasticStrain,safetyCode:4,safetyText:'NOT_APPLICABLE'};
  });
  const data=buildCalculationResultData(input,{nodeDisplacements,elementResults,planeMode:r.settings.planeMode,generatedAt:r.completedAt||r.model.generatedAt||''},{deformationFrame:true,runId:r.runId,frameIndex:index,loadFactor:frame.time*r.settings.loadFactor});
  data.deformation=true;data.loadFactor=frame.time*r.settings.loadFactor;data.frameIndex=index;data.runId=r.runId;
  data.settings=r.settings;data.materialSettings=r.materialSettings;
  data.fracture=Boolean(r.fracture);data.solver=r.solver||'CalculiX';data.damageScope=r.damageScope;
  data.completed=r.completed!==false;data.termination=r.termination||null;data.runInfo.partial=!data.completed;
  data.result.completed=data.completed;data.result.termination=data.termination;
  data.ranges.damage=rangeForValues(data.elements.map(e=>e.damage));data.ranges.plasticStrain=rangeForValues(data.elements.map(e=>e.plasticStrain));
  return data;
}
function syncDeformationToBaseResults(){
  const r=deformationResult;if(!r)return;
  const index=Math.max(0,Math.min(r.frames.length-1,Number(document.getElementById('deformationFrame').value)||0));
  if(deformationSyncedResult!==r||deformationSyncedFrame!==index){
    const previous=resultChannels.deformation?.data;const data=buildDeformationResultSnapshot(r,index);
    if(previous&&typeof gpuMeshRenderer!=='undefined')gpuMeshRenderer.release?.(previous);
    resultChannels.deformation={...resultChannels.deformation,data,mode:resultChannels.deformation?.mode||'deformation',needsFit:resultChannels.deformation?.needsFit||deformationSyncedResult!==r};
    deformationSyncedResult=r;deformationSyncedFrame=index;
    if(activeResultChannel==='deformation'){calculationResultData=data;resultPanelCache={};resultLegendCache={};resetResultDeformationScale(data);setResultDeformationScale(Number(document.getElementById('deformationScale').value));}
  }
  const slider=document.getElementById('baseDeformationFrame');slider.max=r.frames.length-1;slider.value=index;
  document.getElementById('baseDeformationInfo').textContent=`${r.solver||'CalculiX'} · ${r.runId} · 结果帧 ${index+1} / ${r.frames.length} · 载荷比例 ${(r.frames[index].time*r.settings.loadFactor).toFixed(4)}`;
  document.getElementById('baseDamageLabel').textContent=r.fracture?'相场损伤 d（0–1，参与刚度退化）':'损伤起始指标';
  document.getElementById('basePlasticStrainLabel').hidden=activeResultChannel!=='deformation'||Boolean(r.fracture);
  document.getElementById('baseDeformationScope').textContent=r.fracture?'PhAST 单元应力与应变直接采用上游输出；相场损伤参与刚度退化。':'应力与应变为节点外推值的单元平均；损伤起始指标不代表刚度退化。';
  const notice=document.getElementById('baseDeformationNotice');notice.textContent=[r.completed===false?r.termination.message:'',...(r.warnings||[])].filter(Boolean).join('\n');notice.hidden=!notice.textContent;
  if(activeResultChannel==='deformation'){setResultStatus(document.getElementById('baseDeformationInfo').textContent);renderResultView();}
}
function selectBaseResultSource(source){
  stopDeformationPlayback();
  baseResultSource=source==='deformation'&&deformationEnabled?'deformation':'static';
  if(baseResultSource==='deformation')syncDeformationToBaseResults();
  activateResultWorkspace(baseResultSource);resizeResultCanvas();
  if(resultChannels[baseResultSource]?.needsFit){fitResultViewToData();resultChannels[baseResultSource].needsFit=false;}
  if(baseResultSource==='static')loadCalculationResultsFromProjectFolder({quietMissing:true});
  else renderResultView();
}
function resetDeformationResultSync(){
  if(resultChannels.deformation?.data&&typeof gpuMeshRenderer!=='undefined')gpuMeshRenderer.release?.(resultChannels.deformation.data);
  resultChannels.deformation=null;deformationSyncedResult=null;deformationSyncedFrame=-1;
  updateDeformationPlaybackControls();document.getElementById('deformationResultNotice').hidden=true;document.getElementById('baseDeformationNotice').hidden=true;
  document.getElementById('baseDeformationFrame').value=0;document.getElementById('baseDeformationFrame').max=0;document.getElementById('baseDeformationInfo').textContent='请在损伤变形面板运行计算。';
  if(activeResultChannel==='deformation'){calculationResultData=null;setResultStatus('请在损伤变形面板运行计算。');renderResultView();}
}
function initializeDeformationResultSync(){
  document.getElementById('viewDeformationInBase').addEventListener('click',()=>{baseResultSource='deformation';syncDeformationToBaseResults();setPage('results');});
  document.getElementById('baseResultSource').addEventListener('change',e=>selectBaseResultSource(e.target.value));
  document.getElementById('baseDeformationFrame').addEventListener('input',e=>{stopDeformationPlayback();document.getElementById('deformationFrame').value=e.target.value;syncDeformationToBaseResults();renderDeformation();});
}
