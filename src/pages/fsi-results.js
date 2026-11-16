// 2D fluid–structure interaction results: contours of the SU2 flow field and
// of the SU2/MFEM structural response on the shared mesh, deformed geometry,
// velocity arrows, frame playback for transient runs and interface
// convergence history. Values are read from the saved solver frames.
let fsiResult=null,fsiResultModel=null,fsiFrameCache=new Map(),fsiFrame=null,fsiFrameIndex=0,fsiPlayback=null,fsiLoadTicket=0;
let fsiCamera={zoom:1,panX:0,panY:0},fsiDrag=null;
const FSI_FIELD_INFO={
  pressure:['流体压力 p','Pa','fluid'],vmag:['流速大小 |v|','m/s','fluid'],vx:['流速 X 分量 vx','m/s','fluid'],vy:['流速 Y 分量 vy','m/s','fluid'],vz:['流速 Z 分量 vz','m/s','fluid'],
  vorticity:['涡量 ω','1/s','fluid'],cp:['压力系数 Cp','1','fluid'],density:['流体密度 ρ','kg/m³','fluid'],temperature:['流体温度 T','K','fluid'],mach:['马赫数 Ma','1','fluid'],
  umag:['位移大小 |u|','m','all'],ux:['X 位移 Ux','m','all'],uy:['Y 位移 Uy','m','all'],uz:['Z 位移 Uz','m','all'],
  vm:['结构 von Mises 应力','Pa','solid'],sxx:['结构正应力 σxx','Pa','solid'],syy:['结构正应力 σyy','Pa','solid'],szz:['结构正应力 σzz','Pa','solid'],
  sxy:['结构剪应力 τxy','Pa','solid'],syz:['结构剪应力 τyz','Pa','solid'],sxz:['结构剪应力 τxz','Pa','solid']
};
const FSI_DEFAULT_FIELD=['vmag','pressure','vm','umag'];
const $fr=id=>document.getElementById(id);

function clearFsiResult(){
  stopFsiPlayback();fsiResult=null;fsiResultModel=null;fsiFrameCache.clear();fsiFrame=null;fsiFrameIndex=0;
  syncFsiResultControls();renderFsiResults();
}
async function setFsiResult(result,{model}){
  stopFsiPlayback();
  fsiResult=result;fsiResultModel=model;fsiFrameCache.clear();fsiFrame=null;
  fsiCamera={zoom:1,panX:0,panY:0};
  const field=$fr('fsiField');
  field.replaceChildren(...result.fields.filter(key=>FSI_FIELD_INFO[key]).map(key=>new Option(`${FSI_FIELD_INFO[key][0]} (${FSI_FIELD_INFO[key][1]})`,key)));
  field.value=FSI_DEFAULT_FIELD.find(key=>result.fields.includes(key))||result.fields[0];
  const slider=$fr('fsiFrame');slider.max=String(result.frames.length-1);slider.value=slider.max;
  syncFsiResultControls();
  await showFsiFrame(result.frames.length-1);
  autoFsiScale();
}
async function loadFsiFrame(index){
  if(fsiFrameCache.has(index))return fsiFrameCache.get(index);
  const response=await fetch(`./api/fsi-runs/${fsiResult.runId}/frames/${index}`,{cache:'no-store'});
  if(!response.ok)throw Error('流固耦合结果帧已清理，请重新计算。');
  const all=new Float32Array(await response.arrayBuffer()),n=fsiResult.nodeCount;
  const fields={};fsiResult.fields.forEach((key,k)=>{fields[key]=all.subarray(k*n,(k+1)*n);});
  const data={fields,index};
  fsiFrameCache.set(index,data);
  if(fsiFrameCache.size>6)fsiFrameCache.delete(fsiFrameCache.keys().next().value);
  return data;
}
async function showFsiFrame(index){
  const ticket=++fsiLoadTicket;
  const data=await loadFsiFrame(index);
  if(ticket!==fsiLoadTicket)return;
  fsiFrame=data;fsiFrameIndex=index;
  renderFsiResults();
}
function stopFsiPlayback(){if(fsiPlayback!==null)clearTimeout(fsiPlayback);fsiPlayback=null;const b=$fr('fsiPlay');if(b)b.textContent='播放过程';}
function playFsi(){
  if(fsiPlayback!==null){stopFsiPlayback();return;}
  const slider=$fr('fsiFrame');if(slider.value===slider.max)slider.value='0';
  $fr('fsiPlay').textContent='暂停';
  const step=async()=>{
    try{await showFsiFrame(Number(slider.value));}catch(error){$fr('fsiResultStatus').textContent=error.message;stopFsiPlayback();return;}
    if(fsiPlayback===null)return;
    if(slider.value===slider.max){stopFsiPlayback();return;}
    slider.stepUp();fsiPlayback=setTimeout(step,Math.max(40,400/Number($fr('fsiPlaybackSpeed').value)));
  };
  fsiPlayback=setTimeout(step,0);
}
function autoFsiScale(){
  if(!fsiResult||!fsiResultModel)return;
  const stats=fsiResult.frames.map(f=>f.stats.umag?.[1]||0),umax=Math.max(...stats);
  const xs=fsiResultModel.nodes.map(p=>p[0]),ys=fsiResultModel.nodes.map(p=>p[1]);
  const size=Math.hypot(Math.max(...xs)-Math.min(...xs),Math.max(...ys)-Math.min(...ys));
  const scale=umax>0?0.05*size/umax:1;
  const rounded=scale>=1?Number(scale.toPrecision(2)):scale;
  $fr('fsiScale').value=String(umax>0&&umax>0.05*size?1:rounded);
  renderFsiResults();
}
function syncFsiResultControls(){
  const has=Boolean(fsiResult);
  for(const id of ['fsiField','fsiScale','fsiAutoScale','fsiExport','fsiZoneFilter','fsiShowArrows','fsiShowMesh'])$fr(id).disabled=!has;
  $fr('fsiFrame').disabled=!has||fsiResult.frames.length<2;
  $fr('fsiPlay').disabled=!has||fsiResult.frames.length<2;
  $fr('fsiFrameRow').hidden=!has||fsiResult.frames.length<2;
  $fr('fsiRunInfo').textContent=has?fsiRunInfoText(fsiResult):'';
  renderFsiHistory();
}
function fsiRunInfoText(r){
  const m=r.meta||{},s=r.settings||{};
  const lines=[`${r.solver} · ${r.dimension === 3 ? '三维' : '二维'}${s.analysis==='transient'?`瞬态（Δt = ${s.timeStep} s，${s.steps} 步）`:'稳态'}`,
    `流体：${m.fluid?.name||''}（${m.compressible?'可压缩理想气体':'不可压缩'}）· 结构：${s.structure==='neohookean'?'Neo-Hookean 大变形':'线弹性小变形'}${r.dimension===2?` · ${s.plane==='stress'?'平面应力':'平面应变'}`:''}`,
    `流体单元 ${m.fluidCells?.toLocaleString()} · 结构单元 ${m.solidCells?.toLocaleString()} · 流固界面 ${m.interfaceFaces?.toLocaleString()} 段`,
    `材料：${(m.materials||[]).map(x=>`${x.name}（E ${(x.E/1e9).toPrecision(4)} GPa，ν ${x.nu}，ρ ${x.density} kg/m³）`).join('；')}`];
  if(r.mfem)lines.push(`MFEM 结构求解：PCG ${r.mfem.iterations} 次迭代 · 界面载荷合力 (${r.mfem.resultant.map(v=>v.toExponential(3)).join(', ')}) N${r.dimension===2?'/m':''}`);
  if(r.engine==='su2'&&s.analysis==='steady')lines.push(m.converged?'界面残差达到收敛判据。':'达到耦合迭代上限，界面残差未达到收敛判据，请查看收敛曲线并考虑增大迭代次数。');
  if(m.stoppedEarly)lines.push('SU2 提前停止，只保留已输出的时间帧。');
  lines.push(`计算用时 ${(r.elapsedMs/1000).toFixed(1)} s · 任务 ${r.runId}`);
  return lines.join('\n');
}
function fsiFieldRange(key){
  if($fr('fsiFixedColor').checked&&fsiResult.frames.length>1){
    let min=Infinity,max=-Infinity;
    for(const f of fsiResult.frames){const r=f.stats[key];if(r&&Number.isFinite(r[0])){min=Math.min(min,r[0]);max=Math.max(max,r[1]);}}
    return [min,max];
  }
  return fsiResult.frames[fsiFrameIndex]?.stats[key]||[0,0];
}
function fsiColor(v,min,max,diverging){
  if(!Number.isFinite(v))return null;
  if(diverging&&min<0&&max>0){
    const m=Math.max(-min,max)||1,t=Math.min(1,Math.abs(v)/m);
    const a=[244,246,244],b=v<0?[47,111,179]:[180,35,24];
    return `rgb(${a.map((c,i)=>Math.round(c+(b[i]-c)*t)).join(',')})`;
  }
  const t=Math.min(1,Math.max(0,max>min?(v-min)/(max-min):0));
  return `hsl(${Math.round(220*(1-t))},82%,${Math.round(46+6*Math.sin(Math.PI*t))}%)`;
}
function renderFsiResults(){
  const canvas=$fr('fsiCanvas');if(!canvas||currentPageKey()!=='fsi-results')return;
  const rect=canvas.getBoundingClientRect();if(!rect.width||!rect.height)return;
  const dpr=window.devicePixelRatio||1,w=rect.width,h=rect.height;
  canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);
  const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.fillStyle='#f6f9fb';ctx.fillRect(0,0,w,h);
  const status=$fr('fsiResultStatus');
  if(!fsiResult||!fsiFrame||!fsiResultModel){
    ctx.fillStyle='#718494';ctx.font='13px Microsoft YaHei';ctx.textAlign='center';ctx.fillText('请先在流固耦合设置页运行计算',w/2,h/2);
    status.textContent='请先运行计算。';$fr('fsiLegend').replaceChildren();return;
  }
  const model=fsiResultModel,key=$fr('fsiField').value,info=FSI_FIELD_INFO[key]||[key,'',''];
  const values=fsiFrame.fields[key],ux=fsiFrame.fields.ux,uy=fsiFrame.fields.uy;
  const scale=Math.max(0,Number($fr('fsiScale').value)||0),zone=$fr('fsiZoneFilter').value;
  const [min,max]=fsiFieldRange(key);
  const diverging=['pressure','vx','vy','vz','vorticity','cp','ux','uy','uz','sxx','syy','szz','sxy','syz','sxz'].includes(key);
  const pos=i=>[model.nodes[i][0]+scale*(Number.isFinite(ux?.[i])?ux[i]:0),model.nodes[i][1]+scale*(Number.isFinite(uy?.[i])?uy[i]:0)];
  let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
  for(const p of model.nodes){minX=Math.min(minX,p[0]);maxX=Math.max(maxX,p[0]);minY=Math.min(minY,p[1]);maxY=Math.max(maxY,p[1]);}
  const base=Math.min((w-60)/Math.max(maxX-minX,1e-12),(h-60)/Math.max(maxY-minY,1e-12))*fsiCamera.zoom;
  const cx=(minX+maxX)/2,cy=(minY+maxY)/2;
  const project=p=>[w/2+fsiCamera.panX+(p[0]-cx)*base,h/2+fsiCamera.panY-(p[1]-cy)*base];
  canvas._fsiInverse=(x,y)=>[(x-w/2-fsiCamera.panX)/base+cx,-(y-h/2-fsiCamera.panY)/base+cy];
  const showMesh=$fr('fsiShowMesh').checked;
  model.cells.forEach((cell,c)=>{
    const role=model.cellRoles[c];if(role!=='fluid'&&role!=='solid')return;
    const active=info[2]==='all'||info[2]===role;
    const filtered=zone!=='all'&&zone!==role;
    const pts=cell.map(i=>project(pos(i)));
    ctx.beginPath();ctx.moveTo(...pts[0]);ctx.lineTo(...pts[1]);ctx.lineTo(...pts[2]);ctx.closePath();
    if(filtered){ctx.fillStyle='rgba(225,231,235,.35)';ctx.fill();return;}
    if(active&&values){
      const avg=(values[cell[0]]+values[cell[1]]+values[cell[2]])/3;
      ctx.fillStyle=fsiColor(avg,min,max,diverging)||'#dfe6ea';
    }else ctx.fillStyle=role==='solid'?'#c9ced2':'rgba(214,233,243,.6)';
    ctx.fill();
    if(showMesh){ctx.strokeStyle='rgba(40,60,72,.25)';ctx.lineWidth=.5;ctx.stroke();}
    else{ctx.strokeStyle=ctx.fillStyle;ctx.lineWidth=.6;ctx.stroke();}
  });
  // Interface outline (solid boundary) on top.
  const edges=new Map();
  model.cells.forEach((cell,c)=>{if(model.cellRoles[c]!=='solid')return;for(let k=0;k<3;k++){const a=cell[k],b=cell[(k+1)%3],id=a<b?`${a},${b}`:`${b},${a}`;edges.set(id,(edges.get(id)||0)+1);}});
  ctx.strokeStyle='#263b47';ctx.lineWidth=1.4;ctx.beginPath();
  for(const [id,count] of edges)if(count===1){const [a,b]=id.split(',').map(Number);ctx.moveTo(...project(pos(a)));ctx.lineTo(...project(pos(b)));}
  ctx.stroke();
  if($fr('fsiShowArrows').checked&&fsiFrame.fields.vx)drawFsiArrows(ctx,model,project,pos,w,h);
  const time=fsiResult.frames[fsiFrameIndex]?.time;
  status.textContent=[fsiResult.frames.length>1?`帧 ${fsiFrameIndex+1} / ${fsiResult.frames.length}`:'',time!=null?`t = ${time.toPrecision(5)} s`:'',
    `${info[0]}：${Number.isFinite(min)?min.toExponential(4):'—'} 至 ${Number.isFinite(max)?max.toExponential(4):'—'} ${info[1]}`,
    `最大位移 ${(fsiResult.frames[fsiFrameIndex]?.stats.umag?.[1]||0).toExponential(4)} m`,scale!==1?`变形显示放大 ${Number(scale.toPrecision(4))} 倍`:''].filter(Boolean).join(' · ');
  renderFsiLegend(info,min,max,diverging);
  $fr('fsiZoomReadout').textContent=`${Math.round(fsiCamera.zoom*100)}%`;
}
function drawFsiArrows(ctx,model,project,pos,w,h){
  const vx=fsiFrame.fields.vx,vy=fsiFrame.fields.vy,vmax=fsiResult.frames[fsiFrameIndex]?.stats.vmag?.[1]||0;
  if(!(vmax>0))return;
  const step=26,seen=new Set();ctx.strokeStyle='rgba(20,32,40,.75)';ctx.fillStyle='rgba(20,32,40,.75)';ctx.lineWidth=1;
  model.nodes.forEach((_,i)=>{
    if(!Number.isFinite(vx[i]))return;
    const [x,y]=project(pos(i));if(x<0||y<0||x>w||y>h)return;
    const cell=`${Math.floor(x/step)},${Math.floor(y/step)}`;if(seen.has(cell))return;seen.add(cell);
    const m=Math.hypot(vx[i],vy[i]);if(!(m>vmax*0.02))return;
    const len=step*0.85*m/vmax,dx=vx[i]/m*len,dy=-vy[i]/m*len;
    ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x+dx,y+dy);ctx.stroke();
    const a=Math.atan2(dy,dx);ctx.beginPath();ctx.moveTo(x+dx,y+dy);ctx.lineTo(x+dx-4*Math.cos(a-0.45),y+dy-4*Math.sin(a-0.45));ctx.lineTo(x+dx-4*Math.cos(a+0.45),y+dy-4*Math.sin(a+0.45));ctx.closePath();ctx.fill();
  });
}
function renderFsiLegend(info,min,max,diverging){
  const host=$fr('fsiLegend');host.replaceChildren();
  const ramp=document.createElement('span');ramp.className='deformation-legend-ramp';
  ramp.style.background=diverging&&min<0&&max>0?'linear-gradient(90deg,#2f6fb3,#f4f6f4,#b42318)':'linear-gradient(90deg,hsl(220,82%,46%),hsl(165,82%,50%),hsl(110,82%,52%),hsl(55,82%,50%),hsl(0,82%,46%))';
  const lo=document.createElement('span'),hi=document.createElement('span'),title=document.createElement('strong');
  title.textContent=`${info[0]} (${info[1]})`;
  lo.textContent=Number.isFinite(min)?(diverging&&min<0&&max>0?(-Math.max(-min,max)).toExponential(3):min.toExponential(3)):'—';
  hi.textContent=Number.isFinite(max)?(diverging&&min<0&&max>0?Math.max(-min,max).toExponential(3):max.toExponential(3)):'—';
  host.append(title,lo,ramp,hi);
}
function renderFsiHistory(){
  const canvas=$fr('fsiHistoryCanvas');if(!canvas)return;
  const rect=canvas.getBoundingClientRect();if(!rect.width||!rect.height)return;
  const dpr=window.devicePixelRatio||1,w=rect.width,h=rect.height;
  canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);
  const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);ctx.fillStyle='#fff';ctx.fillRect(0,0,w,h);
  const history=fsiResult?.history||[];
  if(!history.length){ctx.fillStyle='#8193a0';ctx.font='12px Microsoft YaHei';ctx.textAlign='center';ctx.fillText('运行后显示收敛曲线',w/2,h/2);return;}
  const series=[['bgsFluid',fsiResult.engine==='oneway'?'流场残差 log₁₀':'界面残差（流体）log₁₀','#1b6fa8'],['bgsSolid','界面残差（结构）log₁₀','#c2410c']]
    .filter(([key])=>history.some(p=>Number.isFinite(p[key])));
  let lo=Infinity,hi=-Infinity;for(const [key] of series)for(const p of history)if(Number.isFinite(p[key])){lo=Math.min(lo,p[key]);hi=Math.max(hi,p[key]);}
  if(hi-lo<1){hi+=0.5;lo-=0.5;}
  const L=48,R=12,T=12,B=26,X=i=>L+(w-L-R)*i/Math.max(1,history.length-1),Y=v=>T+(h-T-B)*(hi-v)/(hi-lo);
  ctx.strokeStyle='#d7e1e7';ctx.lineWidth=1;ctx.fillStyle='#5f7482';ctx.font='11px Segoe UI';ctx.textAlign='right';
  for(let k=0;k<=4;k++){const v=lo+(hi-lo)*k/4,y=Y(v);ctx.beginPath();ctx.moveTo(L,y);ctx.lineTo(w-R,y);ctx.stroke();ctx.fillText(v.toFixed(1),L-6,y+4);}
  ctx.textAlign='center';ctx.fillText(fsiResult.engine==='oneway'?'流场迭代':fsiResult.settings.analysis==='transient'?'耦合迭代（全部时间步）':'耦合迭代',(L+w-R)/2,h-6);
  for(const [key,label,color] of series){
    ctx.strokeStyle=color;ctx.lineWidth=1.6;ctx.beginPath();let started=false;
    history.forEach((p,i)=>{if(!Number.isFinite(p[key]))return;const x=X(i),y=Y(p[key]);if(started)ctx.lineTo(x,y);else{ctx.moveTo(x,y);started=true;}});
    ctx.stroke();
  }
  const legend=$fr('fsiHistoryLegend');legend.replaceChildren();
  for(const [,label,color] of series){const s=document.createElement('span');const i=document.createElement('i');i.className='fsi-swatch';i.style.background=color;s.append(i,label);legend.append(s);}
}
async function exportFsiResult(){
  if(!fsiResult)throw Error('还没有流固耦合结果。');
  const handle=await window.chooseExportFile(window.uiText('TENSORA-流固耦合结果.json'),'application/json','.json');
  if(!handle)return;
  await window.writeExportFile(handle,async writer=>{
    await writer.write(`{"summary":${JSON.stringify(fsiResult)},"model":${JSON.stringify(fsiResultModel)},"frames":[`);
    for(let i=0;i<fsiResult.frames.length;i++){
      const data=await loadFsiFrame(i);
      const fields=Object.fromEntries(Object.entries(data.fields).map(([k,v])=>[k,Array.from(v,x=>Number.isFinite(x)?x:null)]));
      await writer.write((i?',':'')+JSON.stringify({time:fsiResult.frames[i].time,fields}));
    }
    await writer.write(']}');
  });
  $fr('fsiResultStatus').textContent='流固耦合结果已导出。';
}
function zoomFsi(factor,point){
  const rect=$fr('fsiCanvas').getBoundingClientRect(),p=point||{x:rect.width/2,y:rect.height/2},old=fsiCamera.zoom,next=Math.max(.1,Math.min(200,old*factor)),ratio=next/old;
  fsiCamera.panX=p.x-rect.width/2-ratio*(p.x-rect.width/2-fsiCamera.panX);
  fsiCamera.panY=p.y-rect.height/2-ratio*(p.y-rect.height/2-fsiCamera.panY);
  fsiCamera.zoom=next;renderFsiResults();
}
function initializeFsiResults(){
  const guard=fn=>async event=>{try{await fn(event);}catch(error){$fr('fsiResultStatus').textContent=error.message;}};
  for(const id of ['fsiField','fsiScale','fsiZoneFilter','fsiShowArrows','fsiShowMesh','fsiFixedColor'])$fr(id).addEventListener('change',renderFsiResults);
  $fr('fsiScale').addEventListener('input',renderFsiResults);
  $fr('fsiAutoScale').addEventListener('click',autoFsiScale);
  $fr('fsiFrame').addEventListener('input',guard(()=>{stopFsiPlayback();return showFsiFrame(Number($fr('fsiFrame').value));}));
  $fr('fsiPlay').addEventListener('click',playFsi);
  $fr('fsiExport').addEventListener('click',guard(exportFsiResult));
  $fr('fsiZoomIn').addEventListener('click',()=>zoomFsi(1.25));
  $fr('fsiZoomOut').addEventListener('click',()=>zoomFsi(0.8));
  $fr('fsiFit').addEventListener('click',()=>{fsiCamera={zoom:1,panX:0,panY:0};renderFsiResults();});
  const canvas=$fr('fsiCanvas');
  canvas.addEventListener('wheel',event=>{event.preventDefault();const r=canvas.getBoundingClientRect();zoomFsi(event.deltaY<0?1.15:1/1.15,{x:event.clientX-r.left,y:event.clientY-r.top});},{passive:false});
  canvas.addEventListener('pointerdown',event=>{fsiDrag={x:event.clientX,y:event.clientY,panX:fsiCamera.panX,panY:fsiCamera.panY};canvas.setPointerCapture(event.pointerId);canvas.classList.add('dragging');});
  canvas.addEventListener('pointermove',event=>{if(!fsiDrag)return;fsiCamera.panX=fsiDrag.panX+event.clientX-fsiDrag.x;fsiCamera.panY=fsiDrag.panY+event.clientY-fsiDrag.y;renderFsiResults();});
  const end=()=>{fsiDrag=null;canvas.classList.remove('dragging');};
  canvas.addEventListener('pointerup',end);canvas.addEventListener('pointercancel',end);
  canvas.addEventListener('dblclick',()=>{fsiCamera={zoom:1,panX:0,panY:0};renderFsiResults();});
  window.addEventListener('resize',()=>{if(currentPageKey()==='fsi-results'){renderFsiResults();renderFsiHistory();}});
  window.addEventListener('femlanguagechange',()=>{if(currentPageKey()==='fsi-results'){renderFsiResults();renderFsiHistory();}});
  syncFsiResultControls();
}
