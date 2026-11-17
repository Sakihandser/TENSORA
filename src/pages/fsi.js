// 2D fluid–structure interaction workspace. Geometry, regions, materials,
// restraints and the TRI3 mesh are shared with the other workspaces; region
// roles, the fluid, boundary types, solver settings and results are owned here.
// The coupled solution is computed by SU2 (and MFEM for the one-way path) on
// the local server; this page only collects the inputs.
let fsiEnabled=false,fsiController=null,fsiFluids=[],fsiFluidRevision=0,fsiSelectedCurve=null,fsiProgressState=null;
const FSI_KIND_LABELS={wall:'无滑移壁面',slip:'滑移壁面 / 对称面',inlet:'速度入口',outlet:'压力出口',farfield:'远场'};
const FSI_ROLE_LABELS={solid:'结构',fluid:'流体',void:'不参与计算'};
const FSI_KIND_COLORS={wall:'#2f4858',slip:'#7a8f99',inlet:'#1b7f3b',outlet:'#c2410c',farfield:'#6d28d9',interface:'#d9480f'};
const FSI_FORM={engine:'fsiEngine',analysis:'fsiAnalysis',structure:'fsiStructure',plane:'fsiPlane',turbulence:'fsiTurbulence',
  outerIterations:'fsiOuterIterations',fluidIterations:'fsiFluidIterations',solidIterations:'fsiSolidIterations',
  relaxation:'fsiRelaxation',relaxationFactor:'fsiRelaxationFactor',timeStep:'fsiTimeStep',steps:'fsiSteps',frames:'fsiFrames',
  threads:'fsiThreads',convergence:'fsiConvergence',referencePressure:'fsiReferencePressure'};
const FSI_NUMERIC=new Set(['outerIterations','fluidIterations','solidIterations','relaxationFactor','timeStep','steps','frames','threads','convergence','referencePressure']);
const $fsi=id=>document.getElementById(id);

// ------------------------------------------------------------ scene state
function normalizeFsiSceneSettings(raw){
  const out={roles:{},boundaries:{},fluidId:null,form:{}};
  if(!raw||typeof raw!=='object')return out;
  for(const [id,role] of Object.entries(raw.roles||{}))if(FSI_ROLE_LABELS[role])out.roles[String(id)]=role;
  for(const [id,b] of Object.entries(raw.boundaries||{})){
    if(!b||!FSI_KIND_LABELS[b.kind])continue;
    const entry={kind:b.kind};
    for(const key of ['velocity','pressure','angle'])if(Number.isFinite(Number(b[key])))entry[key]=Number(b[key]);
    out.boundaries[String(id)]=entry;
  }
  if(typeof raw.fluidId==='string')out.fluidId=raw.fluidId;
  if(raw.fluid)out.fluid=FluidLibrary.entry(raw.fluid);
  for(const [key,value] of Object.entries(raw.form||{}))if(FSI_FORM[key]&&(typeof value==='string'||typeof value==='number'))out.form[key]=String(value);
  return out;
}
function fsiState(){
  if(!scene.fsiSettings)scene.fsiSettings=normalizeFsiSceneSettings(null);
  return scene.fsiSettings;
}
function fsiRegionRole(region){
  const saved=fsiState().roles[String(region.id)];
  if(saved)return saved;
  return materialSnapshotForRegion(region)?.id?'solid':'fluid';
}
function fsiRegions(){return (scene.regions||[]).filter(region=>!isAirRegion(region));}

// Boundary curves of the fluid domain. With a mesh, edges are classified by the
// neighbouring element roles; without one, by the region boundary curves.
function fsiBoundaryCurves(){
  const roleOfRegion=new Map(fsiRegions().map(r=>[String(r.id),fsiRegionRole(r)]));
  const elements=scene.mesh?.elements||[];
  const counts=new Map();
  if(elements.length){
    const owners=new Map();
    for(const element of elements){
      const role=roleOfRegion.get(String(element.structureRegionId||element.regionId))||'void';
      for(const edge of element.edges||[]){
        const key=(edge.nodeIds||[]).map(String).sort().join('|');
        if(!owners.has(key))owners.set(key,{roles:[],curveId:edge.curveId});
        const entry=owners.get(key);entry.roles.push(role);if(edge.curveId)entry.curveId=edge.curveId;
      }
    }
    for(const {roles,curveId} of owners.values()){
      if(!curveId||roles.length!==1||roles[0]!=='fluid')continue;
      counts.set(String(curveId),(counts.get(String(curveId))||0)+1);
    }
  }else{
    const solidCurves=new Set(),fluidCurves=new Set();
    for(const region of fsiRegions())for(const id of region.boundaryCurveIds||[])(fsiRegionRole(region)==='fluid'?fluidCurves:solidCurves).add(String(id));
    for(const id of fluidCurves)if(!solidCurves.has(id))counts.set(id,0);
  }
  return [...counts.entries()].map(([id,edges])=>({id,edges,curve:scene.curves.find(c=>String(c.id)===id)})).filter(entry=>entry.curve&&!entry.curve.construction);
}
function fsiBoundarySetting(id){return fsiState().boundaries[String(id)]||{kind:'wall'};}

// ------------------------------------------------------------ fluid library
async function loadFsiFluids(){
  try{
    const response=await fetch('/api/fluids',{cache:'no-store'});
    if(!response.ok)throw Error();
    const payload=await response.json();
    fsiFluids=payload.fluids||[];fsiFluidRevision=payload.revision;
  }catch{fsiFluids=[];}
  renderFsiFluidSelect();
  if(typeof renderFsiLibrary==='function'&&currentPageKey()==='fsi-library')renderFsiLibrary();
  window.dispatchEvent(new Event('tensora-fsi-fluids-changed'));
}
function fsiSelectedFluid(){
  const state=fsiState();
  const available=FluidLibrary.forModel(fsiFluids,state.fluid);
  return available.find(f=>f.id===state.fluidId)||available[0]||null;
}
function renderFsiFluidSelect(){
  const select=$fsi('fsiFluid');if(!select)return;
  const fluid=fsiSelectedFluid();
  select.replaceChildren(...FluidLibrary.forModel(fsiFluids,fsiState().fluid).map(f=>new Option(f.name,f.id)));
  if(fluid)select.value=fluid.id;
  $fsi('fsiFluidInfo').textContent=fluid?FluidLibrary.describe(fluid):'流体材料库为空，请先在“流体材料库”中添加流体。';
  $fsi('fsiReferencePressureRow').hidden=fluid?.model!=='idealgas';
}

// ------------------------------------------------------------ setup page
function readFsiForm(){
  const form={};
  for(const [key,id] of Object.entries(FSI_FORM))form[key]=$fsi(id).value;
  return form;
}
function restoreFsiForm(){
  const form=fsiState().form;
  for(const [key,id] of Object.entries(FSI_FORM))if(form[key]!=null)$fsi(id).value=form[key];
  syncFsiForm();
}
function syncFsiForm(){
  const oneway=$fsi('fsiEngine').value==='oneway';
  if(oneway)$fsi('fsiAnalysis').value='steady';
  $fsi('fsiAnalysis').disabled=oneway;
  const transient=$fsi('fsiAnalysis').value==='transient';
  for(const id of ['fsiTimeStepRow','fsiStepsRow','fsiFramesRow'])$fsi(id).hidden=!transient;
  for(const id of ['fsiOuterRow','fsiRelaxationRow','fsiRelaxationFactorRow','fsiSolidRow'])$fsi(id).hidden=oneway;
  $fsi('fsiStructure').disabled=oneway;
  if(oneway)$fsi('fsiStructure').value='linear';
  $fsi('fsiEngineNote').textContent=oneway
    ?'单向耦合：SU2 先在刚性壁面下求解稳态流场，再由 MFEM 以界面压力和壁面剪应力为载荷求解结构线弹性响应。结构变形不反馈流场，适合小变形风载、水压评估。'
    :'双向耦合：SU2 多区求解器在每个耦合迭代中依次求解流场、传递界面载荷、求解结构并按界面位移变形流体网格（分区块 Gauss–Seidel），直至界面收敛。';
}
function renderFsiRoles(){
  const host=$fsi('fsiRoles');host.replaceChildren();
  const regions=fsiRegions();
  if(!regions.length){const p=document.createElement('p');p.className='blast-note';p.textContent='请先在结构绘制页绘制闭合区域。';host.append(p);return;}
  for(const region of regions){
    const row=document.createElement('label');row.className='fsi-role-row';
    const material=materialSnapshotForRegion(region);
    const name=document.createElement('span');
    const swatch=document.createElement('i');swatch.className='fsi-swatch';swatch.style.background=region.materialColor||region.fillColor||'#dfe8ec';
    name.append(swatch,`${region.id}${material?.name?` · ${material.name}`:' · 未填充材料'}`);
    const select=document.createElement('select');
    for(const [value,text] of Object.entries(FSI_ROLE_LABELS))select.add(new Option(text,value));
    select.value=fsiRegionRole(region);
    select.addEventListener('change',()=>{fsiState().roles[String(region.id)]=select.value;renderFsiSetup();});
    row.append(name,select);host.append(row);
  }
  const solid=regions.filter(r=>fsiRegionRole(r)==='solid');
  const missing=solid.filter(r=>!materialSnapshotForRegion(r)?.id);
  $fsi('fsiRoleNote').textContent=missing.length?`结构区域 ${missing.map(r=>r.id).join('、')} 尚未分配材料，请在结构绘制页右键区域指定材料。`
    :'未填充材料的区域默认按流体处理；结构区域使用基础材料库中的 E、ν、ρ。“外部空气”孔洞在流场中视为刚性障碍物（无滑移壁面）。';
}
function renderFsiBoundaries(){
  const host=$fsi('fsiBoundaries');host.replaceChildren();
  const curves=fsiBoundaryCurves();
  if(!curves.length){const p=document.createElement('p');p.className='blast-note';p.textContent='设置流体区域后列出流体外边界；流固界面由网格自动识别。';host.append(p);return;}
  for(const {id,edges} of curves){
    const b=fsiBoundarySetting(id);
    const row=document.createElement('div');row.className='fsi-boundary-row';row.dataset.curve=id;
    row.classList.toggle('active',fsiSelectedCurve===id);
    const title=document.createElement('button');title.type='button';title.className='fsi-boundary-name';
    const dot=document.createElement('i');dot.className='fsi-swatch';dot.style.background=FSI_KIND_COLORS[b.kind];
    title.append(dot,`${id}${edges?` · ${edges} 段`:''}`);
    title.addEventListener('click',()=>{fsiSelectedCurve=fsiSelectedCurve===id?null:id;renderFsiSetup();});
    const kind=document.createElement('select');kind.setAttribute('aria-label','边界类型');
    for(const [value,text] of Object.entries(FSI_KIND_LABELS))kind.add(new Option(text,value));
    kind.value=b.kind;
    const value=document.createElement('label');value.className='fsi-boundary-value';
    const input=document.createElement('input');input.type='number';input.step='any';
    const angle=document.createElement('input');angle.type='number';angle.step='any';angle.setAttribute('aria-label','来流方向角 (°)');
    const angleLabel=document.createElement('label');angleLabel.className='fsi-boundary-value';
    const sync=()=>{
      const k=kind.value,current=fsiBoundarySetting(id);
      value.hidden=!['inlet','outlet','farfield'].includes(k);
      angleLabel.hidden=k!=='farfield';
      value.firstChild.textContent=k==='outlet'?'静压 (Pa，相对参考压力)':'流速 (m/s)';
      input.value=k==='outlet'?(current.pressure??0):(current.velocity??1);
      angle.value=current.angle??0;
      dot.style.background=FSI_KIND_COLORS[k];
    };
    value.append(document.createElement('span'),input);
    angleLabel.append(document.createElement('span'),angle);angleLabel.firstChild.textContent='来流方向角 (°，自 +X 逆时针)';
    const save=()=>{
      const k=kind.value,entry={kind:k};
      if(k==='inlet'||k==='farfield')entry.velocity=Number(input.value);
      if(k==='outlet')entry.pressure=Number(input.value);
      if(k==='farfield')entry.angle=Number(angle.value);
      fsiState().boundaries[id]=entry;
      renderFsiPreview();renderFsiReynolds();
    };
    kind.addEventListener('change',()=>{fsiState().boundaries[id]={kind:kind.value};sync();save();});
    input.addEventListener('change',save);angle.addEventListener('change',save);
    row.append(title,kind,value,angleLabel);host.append(row);sync();
  }
}
function renderFsiPreview(){
  const canvas=$fsi('fsiPreview');if(!canvas||currentPageKey()!=='fsi')return;
  const rect=canvas.getBoundingClientRect();if(!rect.width||!rect.height)return;
  const dpr=window.devicePixelRatio||1,w=rect.width,h=rect.height;
  canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);
  const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.fillStyle='#f2f7f9';ctx.fillRect(0,0,w,h);
  const curves=scene.curves.filter(c=>!c.construction).map(curve=>({curve,points:sampleCurve(curve)}));
  let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
  for(const {points} of curves)for(const p of points){minX=Math.min(minX,p.x);minY=Math.min(minY,p.y);maxX=Math.max(maxX,p.x);maxY=Math.max(maxY,p.y);}
  if(!Number.isFinite(minX)){ctx.fillStyle='#718494';ctx.font='13px Microsoft YaHei';ctx.textAlign='center';ctx.fillText('请先在结构绘制页创建或导入模型',w/2,h/2);canvas._fsiProject=null;return;}
  const scale=Math.min((w-40)/Math.max(maxX-minX,1e-9),(h-40)/Math.max(maxY-minY,1e-9));
  const project=p=>({x:w/2+(p.x-(minX+maxX)/2)*scale,y:h/2-(p.y-(minY+maxY)/2)*scale});
  canvas._fsiProject={project,curves};
  for(const region of [...scene.regions].sort((a,b)=>b.area-a.area)){
    if(!region.polygon?.length)continue;
    ctx.beginPath();region.polygon.forEach((p,i)=>{const q=project(p);if(i)ctx.lineTo(q.x,q.y);else ctx.moveTo(q.x,q.y);});ctx.closePath();
    const role=isAirRegion(region)?'air':fsiRegionRole(region);
    ctx.fillStyle=role==='fluid'?(fsiSelectedFluid()?.color||'#9fd0e6'):role==='solid'?(region.materialColor||'#c9b79c'):role==='air'?'#f2f7f9':'#e6eaec';
    ctx.globalAlpha=role==='fluid'?.55:1;ctx.fill();ctx.globalAlpha=1;
  }
  const boundary=new Map(fsiBoundaryCurves().map(b=>[b.id,fsiBoundarySetting(b.id).kind]));
  for(const {curve,points} of curves){
    const kind=boundary.get(String(curve.id));
    ctx.strokeStyle=kind?FSI_KIND_COLORS[kind]:'#8aa1ad';ctx.lineWidth=String(curve.id)===fsiSelectedCurve?4:kind?2.6:1.4;
    ctx.beginPath();points.forEach((p,i)=>{const q=project(p);if(i)ctx.lineTo(q.x,q.y);else ctx.moveTo(q.x,q.y);});ctx.stroke();
    if(kind){const m=project(points[Math.floor(points.length/2)]);ctx.fillStyle=FSI_KIND_COLORS[kind];ctx.font='11px Segoe UI';ctx.fillText(curve.id,m.x+4,m.y-4);}
  }
  const legend=$fsi('fsiPreviewLegend');legend.replaceChildren();
  for(const [kind,text] of Object.entries(FSI_KIND_LABELS)){const item=document.createElement('span');const dot=document.createElement('i');dot.className='fsi-swatch';dot.style.background=FSI_KIND_COLORS[kind];item.append(dot,text);legend.append(item);}
}
function pickFsiCurve(event){
  const canvas=$fsi('fsiPreview'),data=canvas._fsiProject;if(!data)return;
  const rect=canvas.getBoundingClientRect(),x=event.clientX-rect.left,y=event.clientY-rect.top;
  const candidates=new Set(fsiBoundaryCurves().map(b=>b.id));
  let best=null,bestDistance=10;
  for(const {curve,points} of data.curves){
    if(!candidates.has(String(curve.id)))continue;
    for(let i=1;i<points.length;i++){
      const a=data.project(points[i-1]),b=data.project(points[i]);
      const dx=b.x-a.x,dy=b.y-a.y,t=Math.max(0,Math.min(1,((x-a.x)*dx+(y-a.y)*dy)/((dx*dx+dy*dy)||1)));
      const d=Math.hypot(x-a.x-t*dx,y-a.y-t*dy);
      if(d<bestDistance){bestDistance=d;best=String(curve.id);}
    }
  }
  fsiSelectedCurve=best;renderFsiSetup();
  if(best)document.querySelector(`.fsi-boundary-row[data-curve="${CSS.escape(best)}"] select`)?.focus();
}
// Reynolds number estimate (fluid properties × largest inlet speed × shorter
// side of the model box) to guide the choice of a turbulence model.
function renderFsiReynolds(){
  const host=$fsi('fsiReynolds');if(!host)return;
  const fluid=fsiSelectedFluid();
  const speeds=Object.values(fsiState().boundaries).filter(b=>b.kind==='inlet'||b.kind==='farfield').map(b=>Number(b.velocity)||0);
  const points=scene.curves.filter(c=>!c.construction).flatMap(c=>sampleCurve(c));
  if(!fluid||!speeds.length||!points.length||!(fluid.viscosity>0)){host.textContent='设置速度入口或远场后显示雷诺数估算。';host.dataset.level='';return;}
  const xs=points.map(p=>p.x),ys=points.map(p=>p.y);
  const length=Math.min(Math.max(...xs)-Math.min(...xs),Math.max(...ys)-Math.min(...ys))||Math.max(Math.max(...xs)-Math.min(...xs),Math.max(...ys)-Math.min(...ys));
  const density=fluid.model==='idealgas'?Number($fsi('fsiReferencePressure').value)/(fluid.gasConstant*fluid.temperature):fluid.density;
  const re=density*Math.max(...speeds)*length/fluid.viscosity;
  // The recommendation itself is shown by the pre-run check panel.
  host.dataset.level='';
  host.textContent=`估算雷诺数 Re ≈ ${re.toExponential(2)}（特征长度取模型较短边 ${length.toPrecision(3)} m）。`;
}
function renderFsiSetup(){
  if(currentPageKey()!=='fsi')return;
  renderFsiRoles();renderFsiBoundaries();renderFsiFluidSelect();
  renderFsiReynolds();
  $fsi('fsiModelName').textContent=scene.name||'未命名模型';
  $fsi('fsiNodeCount').textContent=(scene.analysisNodes?.length||0).toLocaleString();
  $fsi('fsiElementCount').textContent=(scene.mesh?.elements?.length||0).toLocaleString();
  requestAnimationFrame(renderFsiPreview);
}

// ------------------------------------------------------------ model payload
function buildFsiModel2d(){
  if(!scene.mesh?.elements?.length)throw Error('请先生成网格（本页“网格”卡片或计算页）。');
  const payload=buildCalculationInputExport();
  const index=new Map(payload.nodes.map((n,i)=>[String(n.id),i]));
  const nodes=payload.nodes.map(n=>[n.x,n.y]);
  const fixed=payload.nodes.flatMap(n=>[n.constraints?.ux?1:0,n.constraints?.uy?1:0]);
  const roleOfRegion=new Map(fsiRegions().map(r=>[String(r.id),fsiRegionRole(r)]));
  const cells=[],cellRoles=[],cellMaterials=[],materials={};
  const curveFaces=new Map();
  for(const element of payload.elements){
    const role=roleOfRegion.get(String(element.region?.id))||'void';
    cells.push(element.nodeNumbers.map(n=>n-1));cellRoles.push(role);
    cellMaterials.push(role==='solid'?String(element.materialId||''):null);
    if(role==='solid'){
      const p=element.mechanicalProperties||{};
      if(!element.materialId)throw Error(`结构区域 ${element.region?.id||''} 尚未分配材料。`);
      materials[element.materialId]={name:element.materialName,E:p.elasticModulus,nu:p.poissonRatio,density:p.density};
    }
    for(const edge of element.edges||[]){
      if(!edge.curveId||edge.nodeIds?.length!==2)continue;
      const face=edge.nodeIds.map(id=>index.get(String(id)));
      if(face.some(v=>v===undefined))continue;
      const id=String(edge.curveId);
      if(!curveFaces.has(id))curveFaces.set(id,new Map());
      curveFaces.get(id).set([...face].sort((a,b)=>a-b).join(','),face);
    }
  }
  if(!cellRoles.includes('fluid'))throw Error('请至少把一个区域设为“流体”。');
  if(!cellRoles.includes('solid'))throw Error('请至少把一个区域设为“结构”。');
  // Curve ids may contain any character; SU2 marker names use C1, C2, ...
  const markerOf=new Map(),boundaries=[],kinds={};
  [...curveFaces.keys()].forEach((id,i)=>markerOf.set(id,`C${i+1}`));
  for(const [id,faces] of curveFaces){
    const name=markerOf.get(id);
    boundaries.push({name,faces:[...faces.values()]});
    const b=fsiBoundarySetting(id),entry={kind:b.kind};
    if(b.kind==='inlet'||b.kind==='farfield')entry.velocity=b.velocity??1;
    if(b.kind==='outlet')entry.pressure=b.pressure??0;
    if(b.kind==='farfield'){const a=(b.angle??0)*Math.PI/180;entry.direction=[Math.cos(a),Math.sin(a),0];}
    kinds[name]=entry;
  }
  return {model:{dimension:2,nodes,cells,cellRoles,cellMaterials,materials,boundaries,fixed},boundaries:kinds,markerOf:Object.fromEntries(markerOf)};
}
function fsiSolverSettings(form){
  const settings={};
  for(const [key,value] of Object.entries(form))settings[key]=FSI_NUMERIC.has(key)?Number(value):value;
  return settings;
}

// ------------------------------------------------------------ run + progress
const FSI_PHASES={preparing:'准备模型',su2:'SU2 求解',mfem:'MFEM 结构求解',processing:'读取结果',complete:'计算完成',partial:'计算提前停止，已保留部分结果',failed:'计算失败',cancelled:'计算已取消。'};
function renderFsiProgress(){
  const p=fsiProgressState,host=$fsi('fsiProgressPanel');
  if(!p){host.hidden=true;return;}
  host.hidden=false;host.dataset.state=p.phase;
  const weights={preparing:0,su2:.03,mfem:.85,processing:.9,partial:1,complete:1};
  const spans={su2:p.engine==='oneway'?.82:.87,mfem:.05,processing:.1};
  const value=p.phase==='complete'?1:Math.min(1,(weights[p.phase]??0)+(spans[p.phase]||0)*(p.fraction||0));
  $fsi('fsiProgress').value=value;
  $fsi('fsiProgressPercent').textContent=`${(value*100).toFixed(1)}%`;
  $fsi('fsiProgressPhase').textContent=FSI_PHASES[p.phase]||p.phase;
  const parts=[];
  if(p.timeIter!=null&&p.analysis==='transient')parts.push(`时间步 ${p.timeIter+1} / ${p.steps}`+(p.time!=null?` · t = ${p.time.toPrecision(4)} s`:''));
  if(p.outer!=null&&p.engine!=='oneway')parts.push(`耦合迭代 ${p.outer+1}`);
  if(p.inner!=null)parts.push(`流场迭代 ${p.inner+1}`);
  if(Number.isFinite(p.bgsFluid))parts.push(`界面残差 log₁₀ 流体 ${p.bgsFluid.toFixed(2)} / 结构 ${Number.isFinite(p.bgsSolid)?p.bgsSolid.toFixed(2):'—'}`);
  if(Number.isFinite(p.residual))parts.push(`流场残差 log₁₀ ${p.residual.toFixed(2)}`);
  parts.push(`已用 ${((p.elapsedMs||0)/1000).toFixed(1)} s`);
  $fsi('fsiProgressDetails').textContent=parts.join(' · ');
  $fsi('fsiProgressError').textContent=p.error||'';
}
async function readFsiStream(response,onProgress){
  if(!response.ok&&!response.headers.get('content-type')?.includes('ndjson')){const body=await response.json().catch(()=>({}));throw Error(body.error||'流固耦合计算失败');}
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
      if(message.type==='progress')onProgress(message);
      else if(message.type==='error')throw Error(message.error);
      else if(message.type==='result')result=message.result;
    }
  }
  if(!result)throw Error('计算进度连接中断，请重新计算。');
  return result;
}
async function runFsi2d(){
  if(fsiController)return;
  if(typeof runWithPreflight==='function'){let allowed=false;await runWithPreflight('fsi',()=>{allowed=true;});if(!allowed||fsiController)return;}
  const status=$fsi('fsiStatus');
  const controller=new AbortController();fsiController=controller;
  $fsi('startFsi').disabled=true;$fsi('cancelFsi').disabled=false;
  try{
    const form=readFsiForm();fsiState().form=form;
    const fluid=fsiSelectedFluid();
    if(!fluid)throw Error('请先在流体材料库中选择流体。');
    if(scene.analysisNodePlacement||scene.mesh?.metadata?.stale){
      await ensureCalculationMeshReadyForExport({adaptive:false,maxNodes:Math.min(400000,scene.analysisNodes.length||Number(maxAnalysisNodes.value))});
    }
    const built=buildFsiModel2d();
    const settings={...fsiSolverSettings(form),boundaries:built.boundaries};
    fsiProgressState={phase:'preparing',fraction:0,elapsedMs:0,engine:settings.engine,analysis:settings.analysis,steps:settings.steps};renderFsiProgress();
    status.textContent='正在提交流固耦合计算…';
    const response=await window.fetchSpecialtyRun(controller,'./api/fsi-runs',{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/x-ndjson'},
      body:JSON.stringify({model:built.model,settings,fluid})});
    const result=await readFsiStream(response,message=>{fsiProgressState={...fsiProgressState,...message};renderFsiProgress();});
    fsiProgressState={...fsiProgressState,phase:result.completed===false?'partial':'complete',fraction:1};renderFsiProgress();
    result.markerOf=built.markerOf;
    await setFsiResult(result,{model:built.model});
    status.textContent=result.termination?.message||fsiResultSummaryText(result);
    setPage('fsi-results');
  }catch(error){
    const cancelled=controller.signal.aborted||error.message==='计算已取消。';
    fsiProgressState={...(fsiProgressState||{}),phase:cancelled?'cancelled':'failed',error:cancelled?'':error.message};renderFsiProgress();
    status.textContent=cancelled?'流固耦合计算已取消。':error.message;
  }finally{fsiController=null;$fsi('startFsi').disabled=false;$fsi('cancelFsi').disabled=true;}
}
function fsiResultSummaryText(result){
  const meta=result.meta||{};
  const state=result.engine==='oneway'?'单向耦合计算完成':result.settings.analysis==='transient'?(meta.stoppedEarly?'瞬态耦合提前停止':'瞬态耦合计算完成'):(meta.converged?'稳态耦合已收敛':'稳态耦合达到迭代上限（未达到收敛判据）');
  return `${state}，用时 ${(result.elapsedMs/1000).toFixed(1)} s。`;
}

// ------------------------------------------------------------ module toggle
function setFsiEnabled(enabled){
  fsiEnabled=Boolean(enabled);
  $fsi('enableFsiModule').checked=fsiEnabled;
  document.querySelectorAll('[data-professional="fsi"]').forEach(el=>{el.hidden=!fsiEnabled;});
  updateProfessionalSummary();
  try{localStorage.setItem('fem.fsi.enabled',String(fsiEnabled));}catch{/* storage unavailable */}
  if(!fsiEnabled){
    fsiController?.abort();
    window.dispatchEvent(new Event('tensora-fsi-disabled'));
    if(['fsi','fsi-results','fsi-library'].includes(currentPageKey()))setPage('calculation');
  }
}
function updateProfessionalSummary(){
  document.getElementById('professionalSummary').textContent='基础'+(blastModuleEnabled?' + 爆破':'')+(deformationEnabled?' + 损伤变形':'')+(fsiEnabled?' + 流固耦合':'');
  if(typeof syncMaterialBindingsAvailability==='function')syncMaterialBindingsAvailability();
}
function clearFsiState(){
  fsiController?.abort();fsiProgressState=null;renderFsiProgress();fsiSelectedCurve=null;
  if(typeof clearFsiResult==='function')clearFsiResult();
  restoreFsiForm();
}
function initializeFsi(){
  let enabled=false;try{enabled=localStorage.getItem('fem.fsi.enabled')==='true';}catch{/* storage unavailable */}
  setFsiEnabled(enabled);
  $fsi('enableFsiModule').addEventListener('change',event=>setFsiEnabled(event.target.checked));
  for(const id of Object.values(FSI_FORM))$fsi(id).addEventListener('change',()=>{fsiState().form=readFsiForm();syncFsiForm();renderFsiReynolds();$fsi('fsiStatus').textContent='参数已更新，运行后生效。';});
  $fsi('fsiFluid').addEventListener('change',event=>{fsiState().fluidId=event.target.value;renderFsiFluidSelect();renderFsiPreview();renderFsiReynolds();});
  $fsi('startFsi').addEventListener('click',runFsi2d);
  $fsi('cancelFsi').addEventListener('click',e=>window.cancelSpecialtyRun(fsiController,e.currentTarget,message=>{$fsi('fsiStatus').textContent=message;}));
  $fsi('fsiPreview').addEventListener('click',pickFsiCurve);
  $fsi('fsiApplyWalls').addEventListener('click',()=>{
    for(const {id} of fsiBoundaryCurves())fsiState().boundaries[id]={kind:'wall'};
    renderFsiSetup();
  });
  $fsi('generateFsiMesh').addEventListener('click',async event=>{
    if(calculationWorkflowRunning)return;
    const status=$fsi('fsiMeshStatus'),count=Number($fsi('fsiMeshLimit').value);
    if(!Number.isSafeInteger(count)||count<3){status.textContent='节点上限须为不小于 3 的整数。';return;}
    calculationWorkflowRunning=true;event.target.disabled=true;status.textContent='正在生成网格…';
    try{maxAnalysisNodes.value=String(count);await autoGenerateAnalysisMesh({regenerateNodes:true,adaptive:false,maxNodes:count});status.textContent='网格已更新。';render();renderFsiSetup();}
    catch(error){status.textContent=error.message;}
    finally{calculationWorkflowRunning=false;event.target.disabled=false;}
  });
  window.addEventListener('resize',()=>{if(currentPageKey()==='fsi')renderFsiPreview();});
  restoreFsiForm();
  loadFsiFluids();
}
