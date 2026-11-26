// 2D structural dynamics results: contour of the selected field on the deformed
// mesh snapshot, mode-shape animation, frame playback, mode table, curves and a
// node probe. Frames are streamed from /api/dynamics-runs/<run>/frames/<k>.
let dynamicsResult=null,dynamicsFrame=null,dynamicsPlayback=null,dynamicsTicket=0,dynamicsProbe=null,dynamicsAnimationPhase=0;
const dynamicsFrameCache=new Map();
let dynamicsCamera={zoom:1,panX:0,panY:0,bounds:null},dynamicsDrag=null;

function dynamicsFieldRange(key){
  const r=dynamicsResult;if(!r)return [0,0];
  if($dyn('dynFixedColor').checked&&r.analysis!=='modal'){
    let lo=Infinity,hi=-Infinity;for(const f of r.frames){const s=f.stats[key];if(s){lo=Math.min(lo,s[0]);hi=Math.max(hi,s[1]);}}
    if(Number.isFinite(lo))return [lo,hi];
  }
  return dynamicsResult.frames[dynamicsFrame?.index??0]?.stats[key]||[0,0];
}
function dynamicsColor(v,min,max){
  if(!Number.isFinite(v))return '#c5ccd1';
  if(min<0&&max>0){const m=Math.max(-min,max)||1,t=Math.min(1,Math.abs(v)/m);
    const a=[244,246,244],b=v<0?[47,111,179]:[180,35,24];return `rgb(${a.map((c,i)=>Math.round(c+(b[i]-c)*t)).join(',')})`;}
  const t=Math.min(1,Math.max(0,max>min?(v-min)/(max-min):0));
  return `hsl(${220*(1-t)},80%,${48+4*Math.sin(Math.PI*t)}%)`;
}
function autoDynamicsScale(){
  const r=dynamicsResult;if(!r)return 1;
  if(r.analysis==='explicit')return 1;
  const g=r.geometry;let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
  for(const p of g.nodes){minX=Math.min(minX,p[0]);minY=Math.min(minY,p[1]);maxX=Math.max(maxX,p[0]);maxY=Math.max(maxY,p[1]);}
  const size=Math.max(maxX-minX,maxY-minY,1e-9);
  const peak=r.analysis==='modal'?Math.max(...r.frames.filter((_,i)=>!r.modes?.[i]?.rigid).map(f=>f.stats.umag?.[1]||0),0)
    :Math.max(...r.frames.map(f=>f.stats.umag?.[1]||0),0);
  if(!(peak>0))return 1;
  const scale=0.1*size/peak;
  return Number(scale.toPrecision(2));
}
function syncDynamicsFrameControls(){
  const r=dynamicsResult,slider=$dyn('dynFrame');
  const has=Boolean(r);
  for(const id of ['dynExport','dynExportCurve'])$dyn(id).disabled=!has;
  slider.disabled=!has||r.frames.length<2;
  $dyn('dynPrevious').disabled=slider.disabled||slider.value==='0';
  $dyn('dynNext').disabled=slider.disabled||slider.value===slider.max;
  $dyn('dynPlay').disabled=!has||(r.analysis!=='modal'&&r.frames.length<2);
  $dyn('dynPlay').textContent=dynamicsPlayback!==null?'暂停':r?.analysis==='modal'||r?.analysis==='harmonic'?'振型动画':'播放';
  $dyn('dynFrameTitle').textContent=r?.analysis==='modal'?'模态阶数':r?.analysis==='harmonic'?'激励频率':'时间帧';
  $dyn('dynFrameLabel').textContent=has&&dynamicsFrame?DynamicsUI.frameLabel(r,dynamicsFrame.index):'';
}
async function setDynamicsResult(summary){
  stopDynamicsPlayback();dynamicsFrameCache.clear();dynamicsProbe=null;dynamicsResult=summary;dynamicsFrame=null;
  dynamicsCamera={zoom:1,panX:0,panY:0,bounds:null};
  const select=$dyn('dynField');select.replaceChildren();
  for(const key of summary.fields)select.add(new Option(`${DynamicsUI.fieldLabel(summary,key)}${DynamicsUI.UNITS[key]?` (${DynamicsUI.UNITS[key]})`:''}`,key));
  select.value=summary.analysis==='explicit'&&summary.fields.includes('vm')?'vm':'umag';
  const curve=$dyn('dynCurve');curve.replaceChildren();
  for(const c of DynamicsUI.curves(summary))curve.add(new Option(c.label,c.key));
  curve.disabled=!curve.options.length;
  const slider=$dyn('dynFrame');slider.max=String(summary.frames.length-1);
  // Modal: first elastic mode; harmonic: response peak; time histories: last frame.
  let start=summary.frames.length-1;
  if(summary.analysis==='modal')start=Math.max(0,(summary.modes||[]).findIndex(m=>!m.rigid));
  if(summary.analysis==='harmonic')start=summary.frames.reduce((best,f,i)=>(f.stats.umag?.[1]||0)>(summary.frames[best].stats.umag?.[1]||0)?i:best,0);
  slider.value=String(start);
  $dyn('dynScale').value=String(autoDynamicsScale());
  renderDynamicsModeTable();
  $dyn('dynRunInfo').textContent=DynamicsUI.runInfo(summary);
  const notice=$dyn('dynResultNotice');notice.textContent=summary.termination?.message||'';notice.hidden=!notice.textContent;
  $dyn('dynProbeClear').disabled=true;$dyn('dynProbeCanvas').hidden=true;
  $dyn('dynProbeInfo').textContent='单击云图中的位置选择最近节点，显示该节点所选结果场随时间、频率或模态的变化。';
  await showDynamicsFrame(start);
}
function clearDynamicsResult(){
  stopDynamicsPlayback();dynamicsTicket++;dynamicsResult=null;dynamicsFrame=null;dynamicsProbe=null;dynamicsFrameCache.clear();
  $dyn('dynField').replaceChildren();$dyn('dynCurve').replaceChildren();$dyn('dynRunInfo').textContent='';
  $dyn('dynModeCard').hidden=true;$dyn('dynResultNotice').hidden=true;
  syncDynamicsFrameControls();renderDynamicsResults();
}
async function showDynamicsFrame(index){
  const ticket=++dynamicsTicket;
  const data=await DynamicsUI.loadFrame(dynamicsResult,index,dynamicsFrameCache);
  if(ticket!==dynamicsTicket)return;
  dynamicsFrame=data;
  $dyn('dynFrame').value=String(index);
  document.querySelectorAll('#dynModeTable tbody tr').forEach(row=>row.classList.toggle('active',dynamicsResult.analysis==='modal'&&Number(row.dataset.index)===index));
  syncDynamicsFrameControls();
  renderDynamicsResults();renderDynamicsCurve();renderDynamicsProbe();
}
function renderDynamicsModeTable(){
  const r=dynamicsResult,card=$dyn('dynModeCard'),table=$dyn('dynModeTable');
  card.hidden=!r?.modes?.length;table.replaceChildren();
  if(card.hidden)return;
  const axes=r.dimension===2?['X','Y']:['X','Y','Z'];
  const head=document.createElement('thead'),row=document.createElement('tr');
  for(const text of ['阶次','频率 (Hz)','周期 (s)',...axes.map(a=>`${a} 向质量占比`),...axes.map(a=>`${a} 向累计`)]){const th=document.createElement('th');th.textContent=text;row.append(th);}
  head.append(row);
  const body=document.createElement('tbody');
  DynamicsUI.modeRows(r).forEach((m,i)=>{
    const tr=document.createElement('tr');tr.dataset.index=String(i);if(m.rigid)tr.className='rigid';
    const cells=[String(m.mode),m.rigid?'刚体模态':DynamicsUI.fmt(m.frequency,6),m.period?DynamicsUI.fmt(m.period,4):'—',
      ...m.ratio.map(v=>Number.isFinite(v)?`${v.toFixed(2)}%`:'—'),...m.cumulative.map(v=>`${v.toFixed(1)}%`)];
    for(const text of cells){const td=document.createElement('td');td.textContent=text;tr.append(td);}
    if(r.analysis==='modal')tr.addEventListener('click',()=>{stopDynamicsPlayback();showDynamicsFrame(i).catch(e=>{$dyn('dynResultStatus').textContent=e.message;});});
    body.append(tr);
  });
  table.append(head,body);
}
function dynamicsDisplayScale(){
  const scale=Number($dyn('dynScale').value);
  if(!Number.isFinite(scale)||scale<0)return 0;
  return dynamicsPlayback!==null&&dynamicsResult?.analysis==='modal'?scale*Math.sin(dynamicsAnimationPhase):scale;
}
function renderDynamicsResults(){
  if(currentPageKey()!=='dynamics-results')return;
  const canvas=$dyn('dynCanvas'),box=canvas.getBoundingClientRect(),dpr=window.devicePixelRatio||1;
  if(!box.width||!box.height)return;
  canvas.width=Math.round(box.width*dpr);canvas.height=Math.round(box.height*dpr);
  const g=canvas.getContext('2d');g.setTransform(dpr,0,0,dpr,0,0);g.fillStyle='#f2f7f9';g.fillRect(0,0,box.width,box.height);
  const legend=$dyn('dynLegend');legend.replaceChildren();
  const r=dynamicsResult,frame=dynamicsFrame;
  if(!r||!frame){$dyn('dynResultStatus').textContent='请先在结构动力学设置页运行计算。';return;}
  if(r.dimension!==2){$dyn('dynResultStatus').textContent='三维动力学结果在三维工作区中显示；请开启“三维计算”。';return;}
  const geo=r.geometry,key=$dyn('dynField').value,values=frame.fields[key];
  const ux=frame.fields.ux,uy=frame.fields.uy,scale=dynamicsDisplayScale();
  const phase=r.analysis==='harmonic'&&dynamicsPlayback!==null;
  // Harmonic animation uses the displacement phase: u(t) = |u| sin(ωt + φ).
  const disp=(i,d)=>{
    const amp=(d?uy:ux)[i]||0;
    if(!phase)return amp*scale;
    const ph=(d?frame.fields.phy:frame.fields.phx)?.[i]||0;
    return scale*DynamicsUI.harmonicDisplacement(amp,ph,dynamicsAnimationPhase);
  };
  const coords=geo.nodes.map((p,i)=>[p[0]+disp(i,0),p[1]+disp(i,1)]);
  if(!dynamicsCamera.bounds){
    let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
    const peak=Math.max(...r.frames.map(f=>f.stats.umag?.[1]||0))*Math.abs(Number($dyn('dynScale').value)||0);
    for(const p of geo.nodes){minX=Math.min(minX,p[0]-peak);minY=Math.min(minY,p[1]-peak);maxX=Math.max(maxX,p[0]+peak);maxY=Math.max(maxY,p[1]+peak);}
    dynamicsCamera.bounds={minX,minY,maxX,maxY};
  }
  const b=dynamicsCamera.bounds;
  const k=Math.min((box.width-70)/Math.max(b.maxX-b.minX,1e-9),(box.height-70)/Math.max(b.maxY-b.minY,1e-9))*dynamicsCamera.zoom;
  const cx=(b.minX+b.maxX)/2,cy=(b.minY+b.maxY)/2;
  const P=p=>[box.width/2+dynamicsCamera.panX+(p[0]-cx)*k,box.height/2+dynamicsCamera.panY-(p[1]-cy)*k];
  dynamicsCamera.inverse=s=>[(s[0]-box.width/2-dynamicsCamera.panX)/k+cx,-(s[1]-box.height/2-dynamicsCamera.panY)/k+cy];
  dynamicsCamera.project=P;dynamicsCamera.coords=coords;
  const [min,max]=dynamicsFieldRange(key);
  if($dyn('dynShowUndeformed').checked&&scale!==0){
    g.strokeStyle='#9fb3bf80';g.lineWidth=.6;
    for(const t of geo.triangles){g.beginPath();t.forEach((n,j)=>{const q=P(geo.nodes[n]);if(j)g.lineTo(...q);else g.moveTo(...q);});g.closePath();g.stroke();}
  }
  const mesh=$dyn('dynShowMesh').checked;
  for(const t of geo.triangles){
    const v=(values[t[0]]+values[t[1]]+values[t[2]])/3;
    g.beginPath();t.forEach((n,j)=>{const q=P(coords[n]);if(j)g.lineTo(...q);else g.moveTo(...q);});g.closePath();
    g.fillStyle=dynamicsColor(v,min,max);g.fill();
    if(mesh){g.strokeStyle='#23405260';g.lineWidth=.4;g.stroke();}else{g.strokeStyle=g.fillStyle;g.lineWidth=.6;g.stroke();}
  }
  // Rigid walls of explicit runs.
  for(const wall of r.meta?.walls||[]){
    const tx=-wall.normal[1],ty=wall.normal[0],c=P(wall.point),span=Math.max(box.width,box.height)*2;
    g.strokeStyle='#2f4858';g.lineWidth=3;g.beginPath();g.moveTo(c[0]-tx*span,c[1]+ty*span);g.lineTo(c[0]+tx*span,c[1]-ty*span);g.stroke();
  }
  if(dynamicsProbe){const q=P(coords[dynamicsProbe.node]);g.strokeStyle='#d9480f';g.lineWidth=2;g.beginPath();g.arc(q[0],q[1],6,0,2*Math.PI);g.stroke();}
  const unit=DynamicsUI.UNITS[key]||'';
  const low=document.createElement('span'),ramp=document.createElement('span'),high=document.createElement('span');
  low.textContent=`${DynamicsUI.fmt(min,4)} ${unit}`;high.textContent=`${DynamicsUI.fmt(max,4)} ${unit}`;
  ramp.className=min<0&&max>0?'deformation-legend-ramp dyn-diverging':'deformation-legend-ramp dyn-ramp';
  legend.append(low,ramp,high);
  $dyn('dynZoomReadout').textContent=`${Math.round(dynamicsCamera.zoom*100)}%`;
  const stats=r.frames[frame.index].stats;
  $dyn('dynResultStatus').textContent=[DynamicsUI.frameLabel(r,frame.index),`${DynamicsUI.fieldLabel(r,key)} ${DynamicsUI.fmt(stats[key]?.[0],4)} 至 ${DynamicsUI.fmt(stats[key]?.[1],4)} ${unit}`,
    `变形显示 ${Number($dyn('dynScale').value)}×`].join(' · ');
}
function renderDynamicsCurve(){
  const r=dynamicsResult,canvas=$dyn('dynCurveCanvas');
  if(!r||currentPageKey()!=='dynamics-results')return;
  const curve=DynamicsUI.curves(r).find(c=>c.key===$dyn('dynCurve').value);
  const marker=r.analysis==='modal'?r.frames[dynamicsFrame?.index??0]?.mode:r.frames[dynamicsFrame?.index??0]?.value;
  if(!curve){DynamicsUI.drawChart(canvas,[]);return;}
  DynamicsUI.drawChart(canvas,curve.multi||[{label:curve.label,x:curve.x,y:curve.y}],{unit:curve.unit,xLabel:curve.bars?'模态阶数':DynamicsUI.axisLabel(r),log:curve.log,bars:curve.bars,marker});
}
function renderDynamicsProbe(){
  const r=dynamicsResult,canvas=$dyn('dynProbeCanvas');
  if(!r||!dynamicsProbe?.series||currentPageKey()!=='dynamics-results')return;
  const key=$dyn('dynField').value,values=dynamicsProbe.series.values[key];
  if(!values)return;
  const x=r.analysis==='modal'?r.frames.map(f=>f.mode):dynamicsProbe.series.axis;
  canvas.hidden=false;
  DynamicsUI.drawChart(canvas,[{label:DynamicsUI.fieldLabel(r,key),x,y:values.map(v=>v[0])}],{unit:DynamicsUI.UNITS[key]||'',xLabel:DynamicsUI.axisLabel(r),
    log:r.analysis==='harmonic'&&!key.startsWith('ph')&&values.every(v=>v[0]>=0),marker:r.analysis==='modal'?r.frames[dynamicsFrame.index].mode:r.frames[dynamicsFrame.index].value});
  const p=r.geometry.nodes[dynamicsProbe.node];
  $dyn('dynProbeInfo').textContent=`节点 ${r.geometry.nodeNo?.[dynamicsProbe.node]??dynamicsProbe.node+1} · (${DynamicsUI.fmt(p[0],5)}, ${DynamicsUI.fmt(p[1],5)}) m · ${DynamicsUI.fieldLabel(r,key)}`;
}
async function pickDynamicsProbe(event){
  const r=dynamicsResult;if(!r||!dynamicsCamera.coords)return;
  const box=$dyn('dynCanvas').getBoundingClientRect(),s=[event.clientX-box.left,event.clientY-box.top];
  let best=-1,distance=Infinity;
  dynamicsCamera.coords.forEach((p,i)=>{const q=dynamicsCamera.project(p),d=(q[0]-s[0])**2+(q[1]-s[1])**2;if(d<distance){distance=d;best=i;}});
  if(best<0||distance>400)return;
  const selected={node:best,series:null};
  dynamicsProbe=selected;renderDynamicsResults();
  try{
    selected.series=await DynamicsUI.loadProbe(r,[best]);
    if(dynamicsProbe!==selected||dynamicsResult!==r)return;
    $dyn('dynProbeClear').disabled=false;renderDynamicsProbe();
  }catch(error){if(dynamicsProbe===selected)$dyn('dynProbeInfo').textContent=error.message;}
}
function stopDynamicsPlayback(){
  if(dynamicsPlayback!==null){cancelAnimationFrame(dynamicsPlayback);clearTimeout(dynamicsPlayback);}
  dynamicsPlayback=null;dynamicsAnimationPhase=0;
  if(dynamicsResult)syncDynamicsFrameControls();
}
function playDynamics(){
  const r=dynamicsResult;if(!r)return;
  if(dynamicsPlayback!==null){stopDynamicsPlayback();renderDynamicsResults();return;}
  const speed=Number($dyn('dynSpeed').value)||1;
  if(r.analysis==='modal'||r.analysis==='harmonic'){
    // One oscillation per 1.6 s at 1×.
    let last=performance.now();
    const tick=now=>{
      dynamicsAnimationPhase+=(now-last)/1000*2*Math.PI/1.6*speed;last=now;
      renderDynamicsResults();
      dynamicsPlayback=requestAnimationFrame(tick);
    };
    dynamicsPlayback=requestAnimationFrame(tick);syncDynamicsFrameControls();return;
  }
  const slider=$dyn('dynFrame');
  if(slider.value===slider.max)slider.value='0';
  const step=async()=>{
    try{await showDynamicsFrame(Number(slider.value));}catch(error){$dyn('dynResultStatus').textContent=error.message;stopDynamicsPlayback();return;}
    if(dynamicsPlayback===null)return;
    if(slider.value===slider.max){if(!$dyn('dynLoop').checked){stopDynamicsPlayback();return;}slider.value='0';}
    else slider.stepUp();
    dynamicsPlayback=setTimeout(step,Math.max(30,160/speed));
  };
  dynamicsPlayback=setTimeout(step,0);syncDynamicsFrameControls();
}
async function exportDynamicsResult(){
  const r=dynamicsResult;if(!r)return;
  const handle=await chooseExportFile(uiText('TENSORA-动力学结果.json'),'application/json','.json');
  if(!handle)return;
  await writeExportFile(handle,async writer=>{
    await writer.write(`{"summary":${JSON.stringify(r)},"frames":[`);
    for(let i=0;i<r.frames.length;i++){
      const data=await DynamicsUI.loadFrame(r,i,null);
      const fields=Object.fromEntries(Object.entries(data.fields).map(([k,v])=>[k,Array.from(v,x=>Number.isFinite(x)?x:null)]));
      await writer.write((i?',':'')+JSON.stringify({value:r.frames[i].value,label:DynamicsUI.frameLabel(r,i),fields}));
    }
    await writer.write(']}');
  });
  $dyn('dynResultStatus').textContent='动力学结果已导出。';
}
async function exportDynamicsCurve(){
  const r=dynamicsResult;if(!r)return;
  const curve=DynamicsUI.curves(r).find(c=>c.key===$dyn('dynCurve').value);
  const series=curve?(curve.multi||[curve]).map(s=>({...s,unit:curve.unit})):[];
  if(dynamicsProbe?.series){
    const key=$dyn('dynField').value,node=r.geometry.nodeNo?.[dynamicsProbe.node]??dynamicsProbe.node+1;
    series.push({label:`节点 ${node} ${DynamicsUI.fieldLabel(r,key)}`,unit:DynamicsUI.UNITS[key],
      x:r.analysis==='modal'?r.frames.map(f=>f.mode):dynamicsProbe.series.axis,y:dynamicsProbe.series.values[key].map(v=>v[0])});
  }
  if(!series.length)throw Error('没有可导出的曲线。');
  const lines=[];
  for(const s of series){lines.push(`# ${uiText(s.label)}`,`${uiText(DynamicsUI.axisLabel(r))},${uiText(s.label)}${s.unit?' ('+s.unit+')':''}`);s.x.forEach((x,i)=>lines.push(`${x},${s.y[i]}`));lines.push('');}
  const handle=await chooseExportFile(uiText('TENSORA-动力学曲线.csv'),'text/csv','.csv');
  if(!handle)return;
  await writeExportFile(handle,writer=>writer.write('﻿'+lines.join('\n')));
}
function zoomDynamicsView(factor,point){
  const old=dynamicsCamera.zoom;dynamicsCamera.zoom=Math.min(200,Math.max(.05,old*factor));
  if(point){const box=$dyn('dynCanvas').getBoundingClientRect(),f=dynamicsCamera.zoom/old;
    dynamicsCamera.panX=(dynamicsCamera.panX-(point.x-box.width/2))*f+(point.x-box.width/2);
    dynamicsCamera.panY=(dynamicsCamera.panY-(point.y-box.height/2))*f+(point.y-box.height/2);}
  renderDynamicsResults();
}
function initializeDynamicsResults(){
  const guard=fn=>async(...args)=>{try{await fn(...args);}catch(error){$dyn('dynResultStatus').textContent=error.message;}};
  $dyn('dynFrame').addEventListener('input',guard(()=>{stopDynamicsPlayback();return showDynamicsFrame(Number($dyn('dynFrame').value));}));
  for(const [id,step] of [['dynPrevious',-1],['dynNext',1]])$dyn(id).addEventListener('click',guard(()=>{stopDynamicsPlayback();const s=$dyn('dynFrame');s.stepUp(step);return showDynamicsFrame(Number(s.value));}));
  $dyn('dynPlay').addEventListener('click',playDynamics);
  $dyn('dynField').addEventListener('change',()=>{renderDynamicsResults();renderDynamicsProbe();});
  for(const id of ['dynShowMesh','dynShowUndeformed','dynFixedColor'])$dyn(id).addEventListener('change',renderDynamicsResults);
  $dyn('dynScale').addEventListener('change',()=>{dynamicsCamera.bounds=null;renderDynamicsResults();});
  $dyn('dynAutoScale').addEventListener('click',()=>{$dyn('dynScale').value=String(autoDynamicsScale());dynamicsCamera.bounds=null;renderDynamicsResults();});
  $dyn('dynCurve').addEventListener('change',renderDynamicsCurve);
  $dyn('dynExport').addEventListener('click',guard(exportDynamicsResult));
  $dyn('dynExportCurve').addEventListener('click',guard(exportDynamicsCurve));
  $dyn('dynProbeClear').addEventListener('click',()=>{dynamicsProbe=null;$dyn('dynProbeCanvas').hidden=true;$dyn('dynProbeClear').disabled=true;
    $dyn('dynProbeInfo').textContent='单击云图中的位置选择最近节点，显示该节点所选结果场随时间、频率或模态的变化。';renderDynamicsResults();});
  const canvas=$dyn('dynCanvas'),point=e=>{const b=canvas.getBoundingClientRect();return {x:e.clientX-b.left,y:e.clientY-b.top};};
  canvas.addEventListener('wheel',e=>{if(!dynamicsResult)return;e.preventDefault();zoomDynamicsView(Math.exp(-e.deltaY*.0012),point(e));},{passive:false});
  canvas.addEventListener('pointerdown',e=>{if(!dynamicsResult||![0,1].includes(e.button))return;dynamicsDrag={id:e.pointerId,...point(e),moved:0};canvas.setPointerCapture(e.pointerId);});
  canvas.addEventListener('pointermove',e=>{if(dynamicsDrag?.id!==e.pointerId)return;const p=point(e);dynamicsCamera.panX+=p.x-dynamicsDrag.x;dynamicsCamera.panY+=p.y-dynamicsDrag.y;
    dynamicsDrag.moved+=Math.abs(p.x-dynamicsDrag.x)+Math.abs(p.y-dynamicsDrag.y);dynamicsDrag.x=p.x;dynamicsDrag.y=p.y;canvas.classList.add('dragging');renderDynamicsResults();});
  canvas.addEventListener('pointerup',e=>{const drag=dynamicsDrag;dynamicsDrag=null;canvas.classList.remove('dragging');if(drag&&drag.moved<4)pickDynamicsProbe(e);});
  canvas.addEventListener('pointercancel',()=>{dynamicsDrag=null;canvas.classList.remove('dragging');});
  canvas.addEventListener('dblclick',()=>{dynamicsCamera={zoom:1,panX:0,panY:0,bounds:null};renderDynamicsResults();});
  $dyn('dynFit').addEventListener('click',()=>{dynamicsCamera={zoom:1,panX:0,panY:0,bounds:null};renderDynamicsResults();});
  $dyn('dynZoomIn').addEventListener('click',()=>zoomDynamicsView(1.25));
  $dyn('dynZoomOut').addEventListener('click',()=>zoomDynamicsView(.8));
  window.addEventListener('resize',()=>{if(currentPageKey()==='dynamics-results'){renderDynamicsResults();renderDynamicsCurve();renderDynamicsProbe();}});
  window.addEventListener('tensora-dynamics-disabled',stopDynamicsPlayback);
  syncDynamicsFrameControls();
}
