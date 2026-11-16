// 2D fluid–structure interaction results: contours of the SU2 flow field and
// of the SU2/MFEM structural response on the shared mesh, deformed geometry,
// velocity arrows, frame playback for transient runs and interface
// convergence history. Values are read from the saved solver frames.
let fsiResult=null,fsiResultModel=null,fsiFrameCache=new Map(),fsiFrame=null,fsiFrameIndex=0,fsiPlayback=null,fsiLoadTicket=0;
let fsiCamera={zoom:1,panX:0,panY:0},fsiDrag=null;
let fsiPostFrame=null,fsiProfilePoints=[],fsiPickingProfile=false,fsiProfileSamples=[],fsiProbePanel=null;
let fsiRecording=false,fsiReferenceBounds=null,fsiInterfaces=null,fsiSolidNodes=[];
const FSI_FIELD_INFO={
  pressure:['流体压力 p','Pa','fluid'],vmag:['流速大小 |v|','m/s','fluid'],vx:['流速 X 分量 vx','m/s','fluid'],vy:['流速 Y 分量 vy','m/s','fluid'],vz:['流速 Z 分量 vz','m/s','fluid'],
  vorticity:['涡量 ω','1/s','fluid'],q:['Q 判据','1/s²','fluid'],cp:['压力系数 Cp','1','fluid'],density:['流体密度 ρ','kg/m³','fluid'],temperature:['流体温度 T','K','fluid'],mach:['马赫数 Ma','1','fluid'],
  umag:['位移大小 |u|','m','all'],ux:['X 位移 Ux','m','all'],uy:['Y 位移 Uy','m','all'],uz:['Z 位移 Uz','m','all'],
  vm:['结构 von Mises 应力','Pa','solid'],sxx:['结构正应力 σxx','Pa','solid'],syy:['结构正应力 σyy','Pa','solid'],szz:['结构正应力 σzz','Pa','solid'],
  sxy:['结构剪应力 τxy','Pa','solid'],syz:['结构剪应力 τyz','Pa','solid'],sxz:['结构剪应力 τxz','Pa','solid']
};
const FSI_DEFAULT_FIELD=['vmag','pressure','vm','umag'];
const $fr=id=>document.getElementById(id);
const fsiPathlines=FsiPaths.create(renderFsiResults);

function clearFsiResult(){
  stopFsiPlayback();++fsiLoadTicket;fsiResult=null;fsiResultModel=null;fsiFrameCache.clear();fsiFrame=null;fsiFrameIndex=0;
  resetFsiPost();
  syncFsiResultControls();renderFsiResults();
}
async function setFsiResult(result,{model}){
  stopFsiPlayback();
  fsiResult=result;fsiResultModel=model;fsiFrameCache.clear();fsiFrame=null;
  $fr('fsiScale').value='1';
  resetFsiPost();
  fsiSolidNodes=[...new Set(model.cells.flatMap((cell,i)=>model.cellRoles[i]==='solid'?cell:[]))];
  fsiReferenceBounds=[Infinity,Infinity,-Infinity,-Infinity];
  for(const [x,y] of model.nodes){
    fsiReferenceBounds[0]=Math.min(fsiReferenceBounds[0],x);
    fsiReferenceBounds[1]=Math.min(fsiReferenceBounds[1],y);
    fsiReferenceBounds[2]=Math.max(fsiReferenceBounds[2],x);
    fsiReferenceBounds[3]=Math.max(fsiReferenceBounds[3],y);
  }
  fsiCamera={zoom:1,panX:0,panY:0};
  const field=$fr('fsiField');
  field.replaceChildren(...result.fields.filter(key=>FSI_FIELD_INFO[key]).map(key=>new Option(`${FSI_FIELD_INFO[key][0]} (${FSI_FIELD_INFO[key][1]})`,key)));
  field.value=FSI_DEFAULT_FIELD.find(key=>result.fields.includes(key))||result.fields[0];
  const slider=$fr('fsiFrame');slider.max=String(result.frames.length-1);slider.value=slider.max;
  syncFsiResultControls();
  await showFsiFrame(result.frames.length-1);
}
async function loadFsiFrame(index,run=fsiResult){
  if(run===fsiResult&&fsiFrameCache.has(index))return fsiFrameCache.get(index);
  const response=await fetch(`./api/fsi-runs/${run.runId}/frames/${index}`,{cache:'no-store'});
  if(!response.ok)throw Error('流固耦合结果帧已清理，请重新计算。');
  const all=new Float32Array(await response.arrayBuffer()),n=run.nodeCount;
  if(all.length!==run.fields.length*n)throw Error('流固耦合结果帧数据不完整。');
  const fields={};run.fields.forEach((key,k)=>{fields[key]=all.subarray(k*n,(k+1)*n);});
  const data={fields,index};
  if(run===fsiResult){
    fsiFrameCache.set(index,data);
    if(fsiFrameCache.size>6)fsiFrameCache.delete(fsiFrameCache.keys().next().value);
  }
  return data;
}
async function showFsiFrame(index){
  const ticket=++fsiLoadTicket;
  const data=await loadFsiFrame(index);
  if(ticket!==fsiLoadTicket)return;
  fsiFrame=data;fsiFrameIndex=index;
  renderFsiResults();
  fsiProbePanel?.refresh();
}
function stopFsiPlayback(){if(fsiPlayback!==null)clearTimeout(fsiPlayback);fsiPlayback=null;const b=$fr('fsiPlay');if(b)b.textContent='播放过程';}
function playFsi(){
  if(fsiPlayback!==null){stopFsiPlayback();return;}
  const slider=$fr('fsiFrame');if(slider.value===slider.max)slider.value='0';
  $fr('fsiPlay').textContent='暂停';
  const step=async()=>{
    try{await showFsiFrame(Number(slider.value));}catch(error){$fr('fsiResultStatus').textContent=error.message;stopFsiPlayback();return;}
    if(fsiPlayback===null)return;
    if(slider.value===slider.max){
      if(!$fr('fsiLoop').checked){stopFsiPlayback();return;}
      slider.value='0';
    }else slider.stepUp();
    fsiPlayback=setTimeout(step,Math.max(40,400/Number($fr('fsiPlaybackSpeed').value)));
  };
  fsiPlayback=setTimeout(step,0);
}
function autoFsiScale(){
  if(!fsiResult||!fsiResultModel)return;
  const stats=fsiResult.frames.map(f=>f.stats.umag?.[1]||0),umax=Math.max(...stats);
  const [x0,y0,x1,y1]=fsiReferenceBounds;
  const size=Math.hypot(x1-x0,y1-y0);
  const scale=umax>0?0.05*size/umax:1;
  const rounded=scale>=1?Number(scale.toPrecision(2)):scale;
  $fr('fsiScale').value=String(umax>0&&umax>0.05*size?1:rounded);
  renderFsiResults();
}
function syncFsiResultControls(){
  const has=Boolean(fsiResult);
  for(const id of ['fsiField','fsiScale','fsiAutoScale','fsiExport','fsiZoneFilter','fsiShowArrows','fsiShowMesh','fsiShowIsolines'])$fr(id).disabled=!has;
  $fr('fsiExportVtk').disabled=!has;
  syncFsiFrameActions();
  $fr('fsiFrameRow').hidden=!has||fsiResult.frames.length<2;
  $fr('fsiRunInfo').textContent=has?fsiRunInfoText(fsiResult):'';
  syncFsiPostControls();
  renderFsiHistory();
}
function syncFsiFrameActions(){
  const transient=fsiResult?.frames.length>1,slider=$fr('fsiFrame');
  $fr('fsiFrameActions').hidden=!transient;
  $fr('fsiFrame').disabled=$fr('fsiPlay').disabled=!transient||fsiRecording;
  $fr('fsiPrevious').disabled=!transient||fsiRecording||slider.value==='0';
  $fr('fsiNext').disabled=!transient||fsiRecording||slider.value===slider.max;
  $fr('fsiExportVideo').disabled=!transient||fsiRecording||!FsiVideo.supported($fr('fsiCanvas'));
}
function resetFsiPost(){
  fsiPathlines.clear();
  fsiInterfaces=null;
  fsiProbePanel?.clear();
  fsiPostFrame=null;fsiProfilePoints=[];fsiProfileSamples=[];fsiPickingProfile=false;
}
function syncFsiPostControls(){
  const visibleFluid=$fr('fsiZoneFilter').value!=='solid';
  const enabled=Boolean(visibleFluid&&fsiFrame?.fields.vx?.length&&fsiFrame?.fields.vy?.length);
  const active=enabled&&$fr('fsiStreamlines').checked;
  const paths=enabled&&FsiPaths.available(fsiResult);
  $fr('fsiPathlines').disabled=!paths;
  $fr('fsiPathStatus').hidden=!paths||!$fr('fsiPathlines').checked;
  $fr('fsiStreamlines').disabled=!enabled;
  $fr('fsiStreamSettings').hidden=!active&&$fr('fsiPathStatus').hidden;
  $fr('fsiStreamStatus').hidden=!active;
  const plane=$fr('fsiSeedMode').value==='plane';
  for(const id of ['fsiSeedAxis','fsiSeedPosition','fsiSeedDensity'])$fr(id).parentElement.hidden=!plane;
  $fr('fsiNearSeedCount').parentElement.hidden=plane;
  $fr('fsiStreamDirection').parentElement.hidden=!active;
  $fr('fsiFocusSolid').disabled=!fsiFrame||!fsiSolidNodes.length;
  $fr('fsiPickProfile').disabled=!fsiFrame;
  $fr('fsiPickProfile').setAttribute('aria-pressed',String(fsiPickingProfile));
  $fr('fsiCanvas').classList.toggle('fsi-picking',fsiPickingProfile);
  $fr('fsiClearProfile').disabled=!fsiProfilePoints.length&&!fsiPickingProfile;
  $fr('fsiExportProfile').disabled=!fsiProfileSamples.some(s=>Number.isFinite(s.value));
  $fr('fsiProfileCanvas').hidden=fsiProfilePoints.length!==2;
  if(fsiProfilePoints.length!==2)$fr('fsiProfileFlow').hidden=true;
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
  syncFsiFrameActions();
  syncFsiPostControls();
  if(!fsiResult||!fsiFrame||!fsiResultModel){
    $fr('fsiProfileStatus').textContent='沿两点间直线采样当前结果场。';
    ctx.fillStyle='#718494';ctx.font='13px Microsoft YaHei';ctx.textAlign='center';ctx.fillText('请先在流固耦合设置页运行计算',w/2,h/2);
    status.textContent='请先运行计算。';$fr('fsiLegend').replaceChildren();return;
  }
  const model=fsiResultModel,key=$fr('fsiField').value,info=FSI_FIELD_INFO[key]||[key,'',''];
  const values=fsiFrame.fields[key];
  const scale=Math.max(0,Number($fr('fsiScale').value)||0),zone=$fr('fsiZoneFilter').value;
  const [min,max]=fsiFieldRange(key);
  const diverging=['pressure','vx','vy','vz','vorticity','q','cp','ux','uy','uz','sxx','syy','szz','sxy','syz','sxz'].includes(key);
  const post=fsiPostGeometry(scale);
  const pos=i=>post.display[i];
  const [minX,minY,maxX,maxY]=fsiReferenceBounds;
  const fit=fsiFitScale(w,h)*fsiCamera.zoom;
  const cx=(minX+maxX)/2,cy=(minY+maxY)/2;
  const project=p=>[w/2+fsiCamera.panX+(p[0]-cx)*fit,h/2+fsiCamera.panY-(p[1]-cy)*fit];
  canvas._fsiInverse=(x,y)=>[(x-w/2-fsiCamera.panX)/fit+cx,-(y-h/2-fsiCamera.panY)/fit+cy];
  const showMesh=$fr('fsiShowMesh').checked;
  const isolines=values&&$fr('fsiShowIsolines').checked&&max>min?[]:null;
  model.cells.forEach((cell,c)=>{
    const role=model.cellRoles[c];if(role!=='fluid'&&role!=='solid')return;
    const active=info[2]==='all'||info[2]===role;
    const filtered=zone!=='all'&&zone!==role;
    const pts=cell.map(i=>project(role==='fluid'?post.flowDisplay[i]:pos(i)));
    ctx.beginPath();ctx.moveTo(...pts[0]);ctx.lineTo(...pts[1]);ctx.lineTo(...pts[2]);ctx.closePath();
    if(filtered){ctx.fillStyle='rgba(225,231,235,.35)';ctx.fill();return;}
    if(active&&values){
      const avg=(values[cell[0]]+values[cell[1]]+values[cell[2]])/3;
      ctx.fillStyle=fsiColor(avg,min,max,diverging)||'#dfe6ea';
      if(isolines){
        const levels=diverging&&min<0&&max>0?[-Math.max(-min,max),Math.max(-min,max)]:[min,max];
        addFsiIsolines(isolines,pts,cell.map(i=>values[i]),...levels);
      }
    }else ctx.fillStyle=role==='solid'?'#c9ced2':'rgba(214,233,243,.6)';
    ctx.fill();
    if(showMesh){ctx.strokeStyle='rgba(40,60,72,.25)';ctx.lineWidth=.5;ctx.stroke();}
    else{ctx.strokeStyle=ctx.fillStyle;ctx.lineWidth=.6;ctx.stroke();}
  });
  if(isolines?.length){
    ctx.beginPath();
    for(const [a,b] of isolines){ctx.moveTo(...a);ctx.lineTo(...b);}
    ctx.strokeStyle='rgba(23,33,44,.70)';ctx.lineWidth=.9;ctx.stroke();
  }
  // Interface outline (solid boundary) on top.
  const edges=new Map();
  model.cells.forEach((cell,c)=>{if(model.cellRoles[c]!=='solid')return;for(let k=0;k<3;k++){const a=cell[k],b=cell[(k+1)%3],id=a<b?`${a},${b}`:`${b},${a}`;edges.set(id,(edges.get(id)||0)+1);}});
  ctx.strokeStyle='#263b47';ctx.lineWidth=1.4;ctx.beginPath();
  for(const [id,count] of edges)if(count===1){const [a,b]=id.split(',').map(Number);ctx.moveTo(...project(pos(a)));ctx.lineTo(...project(pos(b)));}
  ctx.stroke();
  if(zone!=='solid'&&$fr('fsiShowArrows').checked&&fsiFrame.fields.vx&&fsiFrame.fields.vy){
    drawFsiArrows(ctx,model,project,i=>post.flowDisplay[i],w,h);
  }
  if(!$fr('fsiStreamStatus').hidden)drawFsiStreamlines(ctx,project,post);
  drawFsiPathlines(ctx,project);
  renderFsiProfile(ctx,project,post,{key,info,zone});
  fsiProbePanel?.probes().forEach((probe,i)=>{
    if(zone!=='all'&&probe.role!==zone)return;
    const point=project(fsiMapHit(probe.hit,probe.role==='fluid'?post.flowDisplay:post.display));
    drawFsiProfilePoint(ctx,point);
    ctx.fillStyle=ResultProbe.probeColor(i);ctx.font='bold 12px Segoe UI';ctx.fillText(probe.label,point[0]+7,point[1]-7);
  });
  const time=fsiResult.frames[fsiFrameIndex]?.time;
  status.textContent=[fsiResult.frames.length>1?`帧 ${fsiFrameIndex+1} / ${fsiResult.frames.length}`:'',time!=null?`t = ${time.toPrecision(5)} s`:'',
    `${info[0]}：${Number.isFinite(min)?min.toExponential(4):'—'} 至 ${Number.isFinite(max)?max.toExponential(4):'—'} ${info[1]}`,
    `最大位移 ${(fsiResult.frames[fsiFrameIndex]?.stats.umag?.[1]||0).toExponential(4)} m`,scale!==1?`变形显示放大 ${Number(scale.toPrecision(4))} 倍`:''].filter(Boolean).join(' · ');
  renderFsiLegend(info,min,max,diverging);
  $fr('fsiZoomReadout').textContent=`${Math.round(fsiCamera.zoom*100)}%`;
}
function addFsiIsolines(segments,points,field,min,max){
  if(!field.every(Number.isFinite))return;
  const interval=(max-min)/12;
  const first=Math.max(1,Math.ceil((Math.min(...field)-min)/interval));
  const last=Math.min(11,Math.floor((Math.max(...field)-min)/interval));
  for(let index=first;index<=last;index++){
    const level=min+index*interval,cut=[];
    for(let a=0;a<3;a++){
      const b=(a+1)%3;
      if((field[a]>level)===(field[b]>level))continue;
      const t=(level-field[a])/(field[b]-field[a]);
      cut.push(points[a].map((x,d)=>x+(points[b][d]-x)*t));
    }
    if(cut.length===2)segments.push(cut);
  }
}
async function exportFsiVideo(){
  if(fsiRecording)return;
  const run=fsiResult,restore=Number($fr('fsiFrame').value);
  stopFsiPlayback();fsiRecording=true;syncFsiFrameActions();
  let saved=false;
  try{
    saved=await FsiVideo.save({canvas:$fr('fsiCanvas'),frameCount:run.frames.length,fps:Number($fr('fsiVideoFps').value),
      caption:index=>`${$fr('fsiField').selectedOptions[0]?.textContent||''} · t = ${ResultProbe.formatValue(run.frames[index].time)} s`,
      async renderFrame(index,capture){
        if(run!==fsiResult||currentPageKey()!=='fsi-results')throw Error('结果页面已切换，视频导出中止。');
        $fr('fsiFrame').value=String(index);
        await showFsiFrame(index);
        const start=performance.now();
        while(fsiPathlines.pending()){
          if(run!==fsiResult||currentPageKey()!=='fsi-results'||performance.now()-start>30000)throw Error('等待路径线超时或结果页面已切换。');
          await new Promise(resolve=>setTimeout(resolve,50));
        }
        if(run!==fsiResult||currentPageKey()!=='fsi-results')throw Error('结果页面已切换，视频导出中止。');
        capture();
      },
      progress:(index,count)=>{$fr('fsiResultStatus').textContent=`正在导出视频 ${index} / ${count}`;}
    });
  }finally{
    fsiRecording=false;
    if(run===fsiResult){
      $fr('fsiFrame').value=String(restore);await showFsiFrame(restore);
    }
    syncFsiFrameActions();
  }
  if(saved)$fr('fsiResultStatus').textContent='已导出 WebM 视频。';
}
function fsiPostGeometry(scale){
  if(fsiPostFrame?.frame!==fsiFrame){
    const physical=FsiPost.deformedNodes(fsiResultModel.nodes,fsiFrame.fields);
    const flow=FsiPost.flowNodes(fsiResultModel.nodes,fsiFrame.fields,fsiResult.engine);
    fsiPostFrame={frame:fsiFrame,physical,flow,locators:new Map()};
  }
  const post=fsiPostFrame;
  if(post.scale!==scale){
    post.scale=scale;
    post.display=scale===1?post.physical:FsiPost.deformedNodes(fsiResultModel.nodes,fsiFrame.fields,scale);
    post.flowDisplay=scale===1?post.flow:fsiResultModel.nodes.map((p,i)=>p.map((x,d)=>x+scale*(post.flow[i][d]-x)));
    post.pick=null;
  }
  return post;
}
function fsiLocator(nodes,role){
  const {cells,cellRoles}=fsiResultModel;
  return FsiPost.createLocator(nodes,cells,2,i=>role==='all'?['fluid','solid'].includes(cellRoles[i]):cellRoles[i]===role);
}
function fsiPhysicalLocator(post,role){
  if(!post.locators.has(role))post.locators.set(role,fsiLocator(role==='fluid'?post.flow:post.physical,role));
  return post.locators.get(role);
}
function fsiMapHit(hit,nodes){
  return [0,1].map(d=>hit.cell.ids.reduce((sum,id,i)=>sum+hit.weights[i]*nodes[id][d],0));
}
function fsiSeedOptions(){
  return {seedMode:$fr('fsiSeedMode').value,axis:Number($fr('fsiSeedAxis').value),percent:Number($fr('fsiSeedPosition').value),
    density:Number($fr('fsiSeedDensity').value),nearCount:Number($fr('fsiNearSeedCount').value)};
}
function drawFsiStreamlines(ctx,project,post){
  const settings=fsiSeedOptions(),direction=$fr('fsiStreamDirection').value;
  const signature=JSON.stringify({...settings,direction});
  const locator=fsiPhysicalLocator(post,'fluid');
  const maxSpeed=fsiResult.frames[fsiFrameIndex].stats.vmag?.[1]||0;
  if(post.stream?.signature!==signature){
    const roles=fsiResultModel.cellRoles;
    if(settings.seedMode==='interface')fsiInterfaces??=FsiPost.interfaceFacets(fsiResultModel.cells,i=>roles[i]==='fluid',i=>roles[i]==='solid');
    const {seeds,span,position,near,fallback}=FsiPost.flowSeeds(locator,post.flow,fsiInterfaces||[],settings);
    post.stream={signature,position,near,fallback,lines:FsiPost.traceStreamlines(locator,fsiFrame.fields,seeds,{direction,maxSpeed,localSpan:span})};
  }
  const {lines,position,near,fallback}=post.stream;
  ctx.save();ctx.lineJoin='round';
  for(const line of lines){
    const points=line.map(({hit})=>project(fsiMapHit(hit,post.flowDisplay)));
    ctx.beginPath();ctx.moveTo(...points[0]);
    for(const point of points.slice(1))ctx.lineTo(...point);
    ctx.lineWidth=3.5;ctx.strokeStyle='rgba(255,255,255,.85)';ctx.stroke();
    ctx.lineWidth=1.6;
    let spacing=14;
    for(let i=1;i<points.length;i++){
      const [x,y]=points[i], [px,py]=points[i-1];
      const rgb=FsiPost.speedColor((line[i].speed+line[i-1].speed)/2,maxSpeed);
      ctx.strokeStyle=`rgb(${rgb.map(v=>Math.round(v*255)).join(',')})`;
      ctx.beginPath();ctx.moveTo(px,py);ctx.lineTo(x,y);ctx.stroke();
      spacing+=Math.hypot(x-px,y-py);
      if(spacing<70)continue;
      spacing=0;
      const angle=Math.atan2(y-py,x-px);
      ctx.beginPath();ctx.moveTo(x-6*Math.cos(angle-.5),y-6*Math.sin(angle-.5));
      ctx.lineTo(x,y);ctx.lineTo(x-6*Math.cos(angle+.5),y-6*Math.sin(angle+.5));ctx.stroke();
    }
  }
  ctx.restore();
  const summary=$fr('fsiStreamStatus');
  const location=near?' · '+uiText('结构附近'):position===undefined?'':` · ${['X','Y'][settings.axis]} = ${ResultProbe.formatValue(position)} m`;
  const note=fallback?' · '+uiText('未找到共节点流固界面，已改用全域播种。'):'';
  summary.replaceChildren(`${lines.length?lines.length+' 条当前帧流线':'未生成有效流线。'}${location}${note}`);
  if(lines.length){
    const ramp=document.createElement('span');ramp.className='fsi-stream-ramp';
    summary.append(' · 流速 0 ',ramp,`${ResultProbe.formatValue(maxSpeed)} m/s`);
  }
}
function drawFsiPathlines(ctx,project){
  const status=$fr('fsiPathStatus');
  if(status.hidden){fsiPathlines.clear();return;}
  const settings=fsiSeedOptions();
  const {runId}=fsiResult,{nodes,cells,cellRoles}=fsiResultModel;
  const state=fsiPathlines.update(JSON.stringify([runId,settings]),()=>({
    model:{nodes,cells,dimension:2,fluid:cellRoles.map(role=>role==='fluid'),solid:cellRoles.map(role=>role==='solid')},
    run:fsiResult,loadFrame:loadFsiFrame,...settings
  }));
  status.textContent=state.message;
  if(!state.paths)return;
  ctx.save();ctx.strokeStyle='#087b69';ctx.lineWidth=2;ctx.setLineDash([5,3]);ctx.beginPath();
  FsiPaths.segments(state.paths,fsiResult.frames[fsiFrameIndex].time,(a,b)=>{
    ctx.moveTo(...project(a));ctx.lineTo(...project(b));
  });
  ctx.stroke();ctx.restore();
}
function renderFsiProfile(ctx,project,post,{key,info,zone}){
  const status=$fr('fsiProfileStatus'),canvas=$fr('fsiProfileCanvas'),stats=$fr('fsiProfileFlow');
  stats.hidden=true;
  if(fsiProfilePoints.length<2){
    status.textContent=fsiPickingProfile?(fsiProfilePoints.length?'请选择线剖面的终点。':'请选择线剖面的起点。'):'沿两点间直线采样当前结果场。';
    const point=fsiProfilePoints[0];
    const hit=point&&fsiPhysicalLocator(post,fsiProfileRole(info,zone)).locate(point);
    if(hit)drawFsiProfilePoint(ctx,project(fsiMapHit(hit,post.display)));
    return;
  }
  const role=fsiProfileRole(info,zone);
  const display=role==='fluid'?post.flowDisplay:post.display;
  const signature=[key,zone,...fsiProfilePoints.flat()].join('/');
  if(post.profile?.signature!==signature){
    const values=zone==='all'||info[2]==='all'||info[2]===zone?fsiFrame.fields[key]:null;
    const locator=fsiPhysicalLocator(post,role);
    const density=fsiResult.meta?.compressible?null:fsiResult.meta?.fluid?.density;
    const flow=role==='fluid'&&values?FsiPost.lineFlowMetrics(locator,...fsiProfilePoints,fsiFrame.fields,density):null;
    post.profile={signature,samples:FsiPost.lineProfile(locator,...fsiProfilePoints,values),flow};
  }
  fsiProfileSamples=post.profile.samples;
  const values=fsiProfileSamples.map(s=>s.value),valid=values.filter(Number.isFinite);
  status.textContent=valid.length
    ?`长度 ${ResultProbe.formatValue(fsiProfileSamples.at(-1).distance)} m · ${info[0]} ${ResultProbe.formatValue(Math.min(...valid))} 至 ${ResultProbe.formatValue(Math.max(...valid))} ${info[1]}`
    :'当前剖面与可见结果场没有有效交集。';
  const flow=post.profile.flow,format=ResultProbe.formatValue;
  if(flow?.coverage>0){
    stats.hidden=false;
    stats.textContent=[`流体截线长度 ${format(flow.coverage)} m · 正法向 (${flow.normal.map(format).join(', ')})`,
      Number.isFinite(flow.volume)?`体积流量 ${format(flow.volume)} m²/s`:'',
      Number.isFinite(flow.mass)?`质量流量 ${format(flow.mass)} kg/(m·s)`:'',
      flow.pressureLength?`压力合力 (${flow.force.map(format).join(', ')}) N/m`:''].filter(Boolean).join(' · ');
  }
  syncFsiPostControls();
  ResultProbe.drawChart(canvas,{x:fsiProfileSamples.map(s=>s.distance),series:[{values,color:'#007d89'}],
    xLabel:'沿线距离 (m)',yLabel:`${info[0]} (${info[1]})`});
  ctx.save();ctx.setLineDash([5,4]);ctx.lineWidth=2;ctx.strokeStyle='#00717c';ctx.beginPath();
  let open=false;
  for(const sample of fsiProfileSamples){
    if(!sample.hit||!Number.isFinite(sample.value)){open=false;continue;}
    const point=project(fsiMapHit(sample.hit,display));
    if(open)ctx.lineTo(...point);else ctx.moveTo(...point);
    open=true;
  }
  ctx.stroke();ctx.restore();
  const locator=fsiPhysicalLocator(post,role);
  for(const point of fsiProfilePoints){
    const hit=locator.locate(point);
    if(hit)drawFsiProfilePoint(ctx,project(fsiMapHit(hit,display)));
  }
}
function drawFsiProfilePoint(ctx,[x,y]){
  ctx.beginPath();ctx.arc(x,y,4,0,2*Math.PI);ctx.fillStyle='#00717c';ctx.fill();
  ctx.strokeStyle='#fff';ctx.lineWidth=1.5;ctx.stroke();
}
function fsiProfileRole(info,zone){
  return zone==='all'?info[2]:zone;
}
function pickFsiProfilePoint(event){
  const canvas=$fr('fsiCanvas'),rect=canvas.getBoundingClientRect(),post=fsiPostFrame,zone=$fr('fsiZoneFilter').value;
  if(!post||!canvas._fsiInverse)return;
  const role=fsiProfileRole(FSI_FIELD_INFO[$fr('fsiField').value],zone);
  if(post.pick?.role!==role){
    const display=role==='fluid'?post.flowDisplay:post.display;
    post.pick={role,locator:post.scale===1?fsiPhysicalLocator(post,role):fsiLocator(display,role)};
  }
  const hit=post.pick.locator.locate(canvas._fsiInverse(event.clientX-rect.left,event.clientY-rect.top));
  if(!hit){$fr('fsiProfileStatus').textContent='请选择可见网格内的点。';return;}
  const point=fsiMapHit(hit,role==='fluid'?post.flow:post.physical);
  if(fsiProfilePoints.length&&Math.hypot(...point.map((v,i)=>v-fsiProfilePoints[0][i]))<=post.pick.locator.span*1e-9){
    $fr('fsiProfileStatus').textContent='终点需与起点不同。';return;
  }
  fsiProfilePoints.push(point);
  if(fsiProfilePoints.length===2)fsiPickingProfile=false;
  renderFsiResults();
}
function fsiProbeValues(frame,probe){
  return Object.fromEntries(Object.entries(FSI_FIELD_INFO).filter(([key,info])=>frame.fields[key]&&(info[2]==='all'||info[2]===probe.role))
    .map(([key])=>[key,FsiPost.interpolate(frame.fields[key],probe.hit)]));
}
function locateFsiProbe(point,{fromClick,snap}){
  if(!fsiPostFrame)throw Error('当前没有可读取的结果。');
  const zone=$fr('fsiZoneFilter').value,info=FSI_FIELD_INFO[$fr('fsiField').value];
  const post=fsiPostFrame,role=fsiProfileRole(info,zone);
  const nodes=fromClick?(role==='fluid'?post.flowDisplay:post.display):(role==='fluid'?post.flow:post.physical);
  if(fromClick&&post.pick?.role!==role)post.pick={role,locator:fsiLocator(nodes,role)};
  let hit=(fromClick?post.pick.locator:fsiPhysicalLocator(post,role)).locate(point);
  // A query on an interface can be associated with either zone. Prefer the
  // zone of the plotted variable so shared nodes report its result.
  if(!hit)throw Error('该点不在当前可见结果网格内。');
  if(snap){
    const closest=hit.weights.indexOf(Math.max(...hit.weights));
    hit={...hit,weights:hit.weights.map((_,i)=>i===closest?1:0)};
  }
  const cellRole=fsiResultModel.cellRoles[hit.cell.index];
  return {role:cellRole,hit,point:fsiMapHit(hit,cellRole==='fluid'?post.flow:post.physical),where:`三角形 ${hit.cell.index+1}`};
}
async function exportFsiProfile(){
  const key=$fr('fsiField').value,[label,unit]=FSI_FIELD_INFO[key];
  const time=fsiResult.frames[fsiFrameIndex].time;
  const rows=[['距离 (m)','X (m)','Y (m)',`${label} (${unit})`,'帧','时间 (s)'],
    ...fsiProfileSamples.map(s=>[s.distance,...s.point,s.value,fsiFrameIndex+1,time])];
  const handle=await window.chooseExportFile(window.uiText('TENSORA-流固耦合线剖面.csv'),'text/csv','.csv');
  if(handle)await window.writeExportFile(handle,writer=>writer.write(ResultProbe.csvText(rows)));
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
function fsiFitScale(w,h){
  const [x0,y0,x1,y1]=fsiReferenceBounds;
  return Math.min(Math.max(1,w-60)/Math.max(x1-x0,1e-12),Math.max(1,h-60)/Math.max(y1-y0,1e-12));
}
function focusFsiSolid(){
  if(!fsiSolidNodes.length||!fsiPostFrame)return;
  let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
  for(const id of fsiSolidNodes){
    const [x,y]=fsiPostFrame.display[id];
    minX=Math.min(minX,x);minY=Math.min(minY,y);maxX=Math.max(maxX,x);maxY=Math.max(maxY,y);
  }
  const {width,height}=$fr('fsiCanvas').getBoundingClientRect();
  const base=fsiFitScale(width,height),span=Math.max(maxX-minX,maxY-minY,1e-12);
  const zoom=Math.min(200,Math.max(1,Math.min(width,height)/(1.55*span)/base));
  const [x0,y0,x1,y1]=fsiReferenceBounds,fit=base*zoom;
  fsiCamera={zoom,panX:((x0+x1)-(minX+maxX))*fit/2,panY:((minY+maxY)-(y0+y1))*fit/2};
  renderFsiResults();
}
function initializeFsiResults(){
  const guard=fn=>async event=>{try{await fn(event);}catch(error){$fr('fsiResultStatus').textContent=error.message;}};
  for(const id of ['fsiField','fsiScale','fsiZoneFilter','fsiShowArrows','fsiShowMesh','fsiShowIsolines','fsiFixedColor'])$fr(id).addEventListener('change',renderFsiResults);
  $fr('fsiScale').addEventListener('input',renderFsiResults);
  $fr('fsiAutoScale').addEventListener('click',autoFsiScale);
  $fr('fsiFrame').addEventListener('input',guard(()=>{stopFsiPlayback();return showFsiFrame(Number($fr('fsiFrame').value));}));
  $fr('fsiPlay').addEventListener('click',playFsi);
  for(const [id,step] of [['fsiPrevious',-1],['fsiNext',1]])$fr(id).addEventListener('click',guard(()=>{
    stopFsiPlayback();const slider=$fr('fsiFrame');slider.stepUp(step);return showFsiFrame(Number(slider.value));
  }));
  $fr('fsiExportVideo').addEventListener('click',guard(exportFsiVideo));
  $fr('fsiExport').addEventListener('click',guard(exportFsiResult));
  $fr('fsiExportVtk').addEventListener('click',guard(async()=>{
    const {nodes,cells,cellRoles}=fsiResultModel,run=fsiResult;
    if(await FsiExport.saveSeries({run,nodes,cells,role:i=>cellRoles[i],loadFrame:i=>loadFsiFrame(i,run)})){
      $fr('fsiResultStatus').textContent='已导出。解压后在 ParaView 中打开 fsi.pvd。';
    }
  }));
  for(const id of ['fsiStreamlines','fsiPathlines','fsiSeedMode','fsiNearSeedCount','fsiSeedAxis','fsiSeedPosition','fsiSeedDensity','fsiStreamDirection'])$fr(id).addEventListener('change',renderFsiResults);
  $fr('fsiPickProfile').addEventListener('click',()=>{
    fsiPickingProfile=!fsiPickingProfile;fsiProfilePoints=[];fsiProfileSamples=[];renderFsiResults();
  });
  $fr('fsiClearProfile').addEventListener('click',()=>{
    fsiProfilePoints=[];fsiProfileSamples=[];fsiPickingProfile=false;renderFsiResults();
  });
  $fr('fsiExportProfile').addEventListener('click',guard(exportFsiProfile));
  $fr('fsiZoomIn').addEventListener('click',()=>zoomFsi(1.25));
  $fr('fsiZoomOut').addEventListener('click',()=>zoomFsi(0.8));
  $fr('fsiFit').addEventListener('click',()=>{fsiCamera={zoom:1,panX:0,panY:0};renderFsiResults();});
  $fr('fsiFocusSolid').addEventListener('click',focusFsiSolid);
  const canvas=$fr('fsiCanvas');
  fsiProbePanel=ResultProbe.createPanel({
    root:$fr('fsiProbePanel'),dimension:2,pickByDefault:false,exportName:'二维流固耦合测点',
    quantities:()=>fsiResult?.fields.filter(key=>FSI_FIELD_INFO[key]).map(key=>({key,label:FSI_FIELD_INFO[key][0],unit:FSI_FIELD_INFO[key][1]}))||[],
    locate:locateFsiProbe,evaluate:probe=>fsiFrame?{values:fsiProbeValues(fsiFrame,probe)}:null,
    historyAvailable:()=>Boolean(fsiFrame&&FsiPaths.available(fsiResult)),historyKey:()=>fsiResult?.runId,
    history:(probes,{signal,progress})=>FsiSpectrum.probeHistory({run:fsiResult,loadFrame:loadFsiFrame,probes,signal,progress,evaluate:fsiProbeValues}),
    currentIndex:()=>fsiFrameIndex,
    selectIndex(index){if(!fsiRecording){stopFsiPlayback();$fr('fsiFrame').value=String(index);guard(()=>showFsiFrame(index))();}},
    spectrum:FsiSpectrum.spectrum,changed:renderFsiResults
  });
  canvas.addEventListener('wheel',event=>{event.preventDefault();const r=canvas.getBoundingClientRect();zoomFsi(event.deltaY<0?1.15:1/1.15,{x:event.clientX-r.left,y:event.clientY-r.top});},{passive:false});
  canvas.addEventListener('pointerdown',event=>{
    if(fsiPickingProfile){if(event.button===0)pickFsiProfilePoint(event);return;}
    fsiDrag={x:event.clientX,y:event.clientY,panX:fsiCamera.panX,panY:fsiCamera.panY};canvas.setPointerCapture(event.pointerId);canvas.classList.add('dragging');
  });
  canvas.addEventListener('pointermove',event=>{if(!fsiDrag)return;fsiCamera.panX=fsiDrag.panX+event.clientX-fsiDrag.x;fsiCamera.panY=fsiDrag.panY+event.clientY-fsiDrag.y;renderFsiResults();});
  const end=()=>{fsiDrag=null;canvas.classList.remove('dragging');};
  canvas.addEventListener('pointerup',event=>{
    if(fsiDrag&&event.button===0&&fsiProbePanel.pickEnabled()&&Math.hypot(event.clientX-fsiDrag.x,event.clientY-fsiDrag.y)<4){
      const rect=canvas.getBoundingClientRect();
      fsiProbePanel.addAt(canvas._fsiInverse(event.clientX-rect.left,event.clientY-rect.top),{fromClick:true});
    }
    end();
  });
  canvas.addEventListener('pointercancel',end);
  canvas.addEventListener('dblclick',()=>{fsiCamera={zoom:1,panX:0,panY:0};renderFsiResults();});
  window.addEventListener('resize',()=>{if(currentPageKey()==='fsi-results'){renderFsiResults();renderFsiHistory();}});
  window.addEventListener('femlanguagechange',()=>{if(currentPageKey()==='fsi-results'){renderFsiResults();renderFsiHistory();}});
  syncFsiResultControls();
}
