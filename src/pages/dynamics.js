// 2D structural dynamics workspace. Geometry, regions, materials, restraints, loads
// and the TRI3 mesh are shared with the other workspaces; the analysis type, its
// parameters, part velocities, material cards, rigid walls and results are owned
// here. Modal / harmonic / implicit transient analyses run on CalculiX and explicit
// impact on OpenCourant through /api/dynamics-runs; this page only collects inputs.
let dynamicsEnabled=false,dynamicsController=null,dynamicsProgressState=null,dynamicsPartsCache=null;
const $dyn=id=>document.getElementById(id);
const DYN_FORM={planeMode:['dynPlane','number'],elementOrder:['dynOrder','text'],threads:['dynThreads','number'],modes:['dynModes','number'],
  freqMin:['dynFreqMin','number'],freqMax:['dynFreqMax','number'],freqPoints:['dynFreqPoints','number'],dampingRatio:['dynDamping','number'],
  harmonicModes:['dynHarmonicModes','number'],transientMethod:['dynTransientMethod','text'],transientModes:['dynTransientModes','number'],endTime:['dynEndTime','number'],timeStep:['dynTimeStep','number'],frames:['dynFrames','number'],
  rayleighAlpha:['dynAlpha','number'],rayleighBeta:['dynBeta','number'],explicitEndTime:['dynExplicitEnd','number'],explicitFrames:['dynExplicitFrames','number'],
  timeStepScale:['dynDtScale','number'],minTimeStep:['dynMinDt','number'],friction:['dynFriction','number'],contact:['dynContact','check'],selfContact:['dynSelfContact','check'],
  explicitLoads:['dynExplicitLoads','check']};
const DYN_LOAD={shape:['dynLoadShape','text'],factor:['dynLoadFactor','number'],frequency:['dynLoadFrequency','number'],duration:['dynLoadDuration','number'],rise:['dynLoadRise','number']};
const DYN_PART_COLORS=['#4f9fc9','#e07a3f','#6aa84f','#a678c9','#d4a017','#3aa6a0','#c95b7a','#7b8794'];

// ------------------------------------------------------------ scene state
function normalizeDynamicsSceneSettings(raw){
  const out={analysis:'modal',form:{},load:{},gravity:[0,0,0],partVelocities:{},cards:{},walls:[],loadTable:''};
  if(!raw||typeof raw!=='object')return out;
  if(DynamicsSettings.ANALYSIS_IDS.includes(raw.analysis))out.analysis=raw.analysis;
  for(const [key,value] of Object.entries(raw.form||{}))if(DYN_FORM[key]&&['string','number','boolean'].includes(typeof value))out.form[key]=value;
  for(const [key,value] of Object.entries(raw.load||{}))if(DYN_LOAD[key]&&['string','number'].includes(typeof value))out.load[key]=value;
  if(typeof raw.loadTable==='string')out.loadTable=raw.loadTable.slice(0,20000);
  if(Array.isArray(raw.gravity))out.gravity=[0,1,2].map(i=>Number(raw.gravity[i])||0);
  for(const [key,v] of Object.entries(raw.partVelocities||{}))if(Array.isArray(v))out.partVelocities[String(key)]=[0,1,2].map(i=>Number(v[i])||0);
  for(const [key,card] of Object.entries(raw.cards||{}))if(card&&typeof card==='object'&&['elastic','plastic','linked'].includes(card.model)){
    const entry={model:card.model};
    if(card.yieldStress!=null&&Number.isFinite(Number(card.yieldStress)))entry.yieldStress=Number(card.yieldStress);
    if(card.tangentModulus!=null&&Number.isFinite(Number(card.tangentModulus)))entry.tangentModulus=Number(card.tangentModulus);
    if(card.failureStrain!=null&&Number.isFinite(Number(card.failureStrain)))entry.failureStrain=Number(card.failureStrain);
    out.cards[String(key)]=entry;
  }
  if(Array.isArray(raw.walls))out.walls=raw.walls.slice(0,8).map(w=>({point:[0,1,2].map(i=>Number(w?.point?.[i])||0),normal:[0,1,2].map(i=>Number(w?.normal?.[i])||0),friction:Math.max(0,Number(w?.friction)||0)}));
  return out;
}
function dynamicsState(){
  if(!scene.dynamicsSettings)scene.dynamicsSettings=normalizeDynamicsSceneSettings(null);
  return scene.dynamicsSettings;
}
function selectedDynamicsAnalysis(){return document.querySelector('input[name="dynAnalysis"]:checked')?.value||'modal';}

function readDynamicsForm(){
  const state=dynamicsState();
  state.analysis=selectedDynamicsAnalysis();
  for(const [key,[id,kind]] of Object.entries(DYN_FORM))state.form[key]=kind==='check'?$dyn(id).checked:kind==='number'?Number($dyn(id).value):$dyn(id).value;
  for(const [key,[id,kind]] of Object.entries(DYN_LOAD))state.load[key]=kind==='number'?Number($dyn(id).value):$dyn(id).value;
  state.loadTable=$dyn('dynLoadTable').value;
  state.gravity=[Number($dyn('dynGx').value)||0,Number($dyn('dynGy').value)||0,0];
  return state;
}
function restoreDynamicsForm(){
  const state=dynamicsState(),defaults=DynamicsSettings.DEFAULTS;
  const radio=document.querySelector(`input[name="dynAnalysis"][value="${state.analysis}"]`);if(radio)radio.checked=true;
  for(const [key,[id,kind]] of Object.entries(DYN_FORM)){
    const value=state.form[key]??defaults[key];
    if(kind==='check')$dyn(id).checked=Boolean(value);else if(value!==undefined)$dyn(id).value=String(value);
  }
  for(const [key,[id]] of Object.entries(DYN_LOAD)){const value=state.load[key]??defaults.load[key];if(value!==undefined)$dyn(id).value=String(value);}
  $dyn('dynLoadTable').value=state.loadTable||$dyn('dynLoadTable').defaultValue;
  $dyn('dynGx').value=String(state.gravity[0]||0);$dyn('dynGy').value=String(state.gravity[1]||0);
  syncDynamicsForm();
}
function parseDynamicsTable(text){
  const rows=String(text||'').split(/\r?\n/).map(line=>line.trim()).filter(Boolean).map(line=>line.split(/[,，\s\t;]+/).map(Number));
  if(rows.some(r=>r.length<2||!r.slice(0,2).every(Number.isFinite)))throw Error('载荷时程表每行需要“时间, 系数”两个数值。');
  return rows.map(r=>[r[0],r[1]]);
}
function dynamicsLoad(state=dynamicsState()){
  const load={...DynamicsSettings.DEFAULTS.load,...state.load};
  if(load.shape==='table')load.table=parseDynamicsTable(state.loadTable||$dyn('dynLoadTable').value);
  return DynamicsSettings.normalizeLoad(load);
}

// ------------------------------------------------------------ mesh parts and materials
function dynamicsMesh(){
  const elements=scene.mesh?.elements||[];
  if(!elements.length)return null;
  if(dynamicsPartsCache?.mesh===scene.mesh&&dynamicsPartsCache.count===elements.length)return dynamicsPartsCache;
  const index=new Map((scene.analysisNodes||[]).map((n,i)=>[String(n.id),i]));
  const nodes=(scene.analysisNodes||[]).map(n=>[Number(n.x),Number(n.y),0]);
  const tris=[];
  for(const e of elements){const ids=(e.analysisNodeIds||e.nodeIds||[]).map(id=>index.get(String(id)));if(ids.length===3&&ids.every(i=>i!==undefined))tris.push(ids);}
  const parts=DynamicsUI.parts(tris,nodes);
  // Representative node (analysis node id) of each part maps it onto the exported model.
  const representative=parts.list.map(()=>null);
  parts.nodePart.forEach((k,i)=>{if(k>=0&&representative[k]===null)representative[k]=String(scene.analysisNodes[i].id);});
  dynamicsPartsCache={mesh:scene.mesh,count:elements.length,nodes,tris,parts,representative};
  return dynamicsPartsCache;
}
function dynamicsMaterials(){
  const ids=new Map();
  for(const region of scene.regions||[]){
    const snapshot=materialSnapshotForRegion(region);
    if(snapshot?.id&&!ids.has(snapshot.id))ids.set(snapshot.id,{...snapshot,...(typeof materialById==='function'?materialById(snapshot.id)||{}:{})});
  }
  return [...ids.values()];
}
function linkedBlastCard(material){
  const cards=typeof blastMaterialLibrary!=='undefined'?blastMaterialLibrary:(window.PROJECT_MATERIAL_LIBRARY?.blastMaterials||[]);
  return material?.blastMaterialId?cards.find(card=>card.id===material.blastMaterialId)||null:null;
}

// ------------------------------------------------------------ view
function syncDynamicsForm(){
  const analysis=selectedDynamicsAnalysis();
  document.querySelectorAll('.dynamics-page [data-dyn-analysis]').forEach(el=>{el.hidden=!el.dataset.dynAnalysis.split(' ').includes(analysis);});
  const shape=$dyn('dynLoadShape').value;
  document.querySelectorAll('.dynamics-page [data-dyn-load]').forEach(el=>{el.hidden=!el.dataset.dynLoad.split(' ').includes(shape);});
  document.querySelectorAll('.dynamics-page [data-dyn-method]').forEach(el=>{el.hidden=el.dataset.dynMethod!==$dyn('dynTransientMethod').value;});
  document.querySelectorAll('.dyn-analysis-card').forEach(card=>card.classList.toggle('active',card.querySelector('input').checked));
  const info=DynamicsSettings.ANALYSES.find(a=>a.id===analysis);
  $dyn('dynAnalysisHelp').textContent=info?.help||'';
  // Explicit 2D runs use the plane-strain slab.
  if(analysis==='explicit')$dyn('dynPlane').value='1';
  $dyn('dynPlane').disabled=analysis==='explicit';
  const loadsOff=analysis==='explicit'&&!$dyn('dynExplicitLoads').checked;
  for(const id of ['dynLoadShape','dynLoadFactor','dynLoadFrequency','dynLoadDuration','dynLoadRise','dynLoadTable'])$dyn(id).disabled=loadsOff;
  $dyn('startDynamics').textContent={modal:'运行模态分析',harmonic:'运行谐响应分析',transient:'运行瞬态动力学',explicit:'运行显式碰撞计算'}[analysis];
}
function renderDynamicsParts(){
  const host=$dyn('dynParts');host.replaceChildren();
  const mesh=dynamicsMesh(),state=dynamicsState();
  if(!mesh){const p=document.createElement('p');p.className='blast-note';p.textContent='请先在基础计算页划分网格。';host.append(p);return;}
  for(const part of mesh.parts.list){
    const row=document.createElement('div');row.className='dyn-part-row';
    const swatch=document.createElement('span');swatch.className='dyn-swatch';swatch.style.background=DYN_PART_COLORS[(part.part-1)%DYN_PART_COLORS.length];
    const title=document.createElement('strong');title.textContent=`部件 ${part.part}`;
    const info=document.createElement('small');info.textContent=`${part.nodes} 节点 · 中心 (${DynamicsUI.fmt(part.center[0],4)}, ${DynamicsUI.fmt(part.center[1],4)}) m`;
    const head=document.createElement('div');head.className='dyn-part-head';head.append(swatch,title,info);
    const velocity=state.partVelocities[String(part.part)]||[0,0,0];
    const inputs=document.createElement('div');inputs.className='dyn-vector-inputs';
    ['vx','vy'].forEach((name,d)=>{
      const label=document.createElement('label');label.textContent=`${name} (m/s)`;
      const input=document.createElement('input');input.type='number';input.step='any';input.value=String(velocity[d]||0);
      input.addEventListener('change',()=>{const v=[...(state.partVelocities[String(part.part)]||[0,0,0])];v[d]=Number(input.value)||0;state.partVelocities[String(part.part)]=v;renderDynamicsPreview();});
      label.append(input);inputs.append(label);
    });
    row.append(head,inputs);host.append(row);
  }
}
function renderDynamicsMaterials(){
  const host=$dyn('dynMaterials');host.replaceChildren();
  const state=dynamicsState(),materials=dynamicsMaterials();
  if(!materials.length){const p=document.createElement('p');p.className='blast-note';p.textContent='请先在结构绘制中为区域分配材料。';host.append(p);return;}
  for(const material of materials){
    const card=state.cards[material.id]||{model:'elastic'};
    const linked=linkedBlastCard(material);
    const box=document.createElement('div');box.className='deformation-material-card';
    const title=document.createElement('h3');title.textContent=`${material.name} · E ${DynamicsUI.fmt(Number(material.elasticModulus),4)} GPa · ρ ${material.density||'—'} kg/m³`;
    const select=document.createElement('select');
    select.add(new Option('线弹性','elastic'));select.add(new Option('双线性弹塑性（屈服 + 线性硬化）','plastic'));
    if(linked)select.add(new Option(`关联爆破材料卡：${linked.name}`,'linked'));
    select.value=card.model==='linked'&&!linked?'elastic':card.model;
    const model=document.createElement('label');model.className='blast-select-field';const span=document.createElement('span');span.textContent='本构';model.append(span,select);
    const grid=document.createElement('div');grid.className='blast-form-grid';grid.append(model);
    const fields=[['yieldStress','屈服应力 σy (MPa)',1e6,Number(material.yieldStrength)||235],['tangentModulus','切线模量 Et (MPa)',1e6,Math.max(1,Number(material.elasticModulus)*10)],['failureStrain','失效塑性应变（0 不删除单元）',1,0]];
    const inputs=fields.map(([key,label,scale,fallback])=>{
      const field=document.createElement('label');field.className='number-field';field.dataset.plastic='1';
      const text=document.createElement('span');text.textContent=label;
      const input=document.createElement('input');input.type='number';input.min='0';input.step='any';
      input.value=String(card[key]!=null&&Number.isFinite(card[key])&&(key==='yieldStress'?card[key]>0:card[key]>=0)?card[key]/scale:fallback);
      input.addEventListener('change',()=>save());
      field.append(text,input);grid.append(field);return {key,scale,input,field};
    });
    const save=()=>{
      const next={model:select.value};
      for(const {key,scale,input} of inputs)next[key]=(Number(input.value)||0)*scale;
      state.cards[material.id]=next;
      for(const {field} of inputs)field.hidden=select.value!=='plastic';
    };
    select.addEventListener('change',save);
    save();
    box.append(title,grid);host.append(box);
  }
}
function renderDynamicsWalls(){
  const host=$dyn('dynWalls');host.replaceChildren();
  const state=dynamicsState();
  if(!state.walls.length){const p=document.createElement('p');p.className='blast-note';p.textContent='未设置刚性墙。';host.append(p);}
  state.walls.forEach((wall,k)=>{
    const row=document.createElement('div');row.className='dyn-wall-row';
    const title=document.createElement('strong');title.textContent=`刚性墙 ${k+1}`;
    const grid=document.createElement('div');grid.className='dyn-vector-inputs';
    for(const [label,get,set] of [['墙上一点 x (m)',()=>wall.point[0],v=>{wall.point[0]=v;}],['墙上一点 y (m)',()=>wall.point[1],v=>{wall.point[1]=v;}],
      ['法向 nx',()=>wall.normal[0],v=>{wall.normal[0]=v;}],['法向 ny',()=>wall.normal[1],v=>{wall.normal[1]=v;}],['摩擦系数',()=>wall.friction,v=>{wall.friction=Math.max(0,v);}]]){
      const field=document.createElement('label');field.textContent=label;
      const input=document.createElement('input');input.type='number';input.step='any';input.value=String(get());
      input.addEventListener('change',()=>{set(Number(input.value)||0);renderDynamicsPreview();});
      field.append(input);grid.append(field);
    }
    const remove=document.createElement('button');remove.type='button';remove.textContent='删除';
    remove.addEventListener('click',()=>{state.walls.splice(k,1);renderDynamicsWalls();renderDynamicsPreview();});
    row.append(title,grid,remove);host.append(row);
  });
}
function dynamicsBounds(mesh){
  let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
  for(const p of mesh?.nodes||[]){minX=Math.min(minX,p[0]);minY=Math.min(minY,p[1]);maxX=Math.max(maxX,p[0]);maxY=Math.max(maxY,p[1]);}
  return {minX,minY,maxX,maxY};
}
function addDynamicsWall(){
  const mesh=dynamicsMesh(),state=dynamicsState();
  if(state.walls.length>=8){$dyn('dynStatus').textContent='刚性墙最多 8 个';return;}
  const b=mesh?dynamicsBounds(mesh):{minX:0,minY:0,maxX:1,maxY:1};
  const gap=0.02*Math.max(b.maxX-b.minX,b.maxY-b.minY,1e-6);
  // Default: a ground plane under the model for the first wall, then a wall on the right.
  state.walls.push(state.walls.length?{point:[b.maxX+gap,0,0],normal:[-1,0,0],friction:0}:{point:[0,b.minY-gap,0],normal:[0,1,0],friction:0.2});
  renderDynamicsWalls();renderDynamicsPreview();
}
function renderDynamicsPreview(){
  const canvas=$dyn('dynPreview'),box=canvas.getBoundingClientRect();
  if(!box.width||!box.height)return;
  const dpr=window.devicePixelRatio||1,w=box.width,h=box.height;
  canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);
  const g=canvas.getContext('2d');g.setTransform(dpr,0,0,dpr,0,0);g.fillStyle='#f2f7f9';g.fillRect(0,0,w,h);
  const mesh=dynamicsMesh();
  if(!mesh){g.fillStyle='#718494';g.font='13px Microsoft YaHei';g.textAlign='center';g.fillText('请先在基础计算页划分网格',w/2,h/2);return;}
  const state=dynamicsState(),analysis=selectedDynamicsAnalysis();
  const b=dynamicsBounds(mesh);
  const meshCenter=[(b.minX+b.maxX)/2,(b.minY+b.maxY)/2];
  const walls=analysis==='explicit'?state.walls:[];
  for(const wall of walls){b.minX=Math.min(b.minX,wall.point[0]);b.maxX=Math.max(b.maxX,wall.point[0]);b.minY=Math.min(b.minY,wall.point[1]);b.maxY=Math.max(b.maxY,wall.point[1]);}
  const size=Math.max(b.maxX-b.minX,b.maxY-b.minY,1e-9);
  const k=Math.min((w-50)/Math.max(b.maxX-b.minX,size*0.05),(h-50)/Math.max(b.maxY-b.minY,size*0.05));
  const P=p=>[w/2+(p[0]-(b.minX+b.maxX)/2)*k,h/2-(p[1]-(b.minY+b.maxY)/2)*k];
  mesh.tris.forEach((t,i)=>{
    const part=mesh.parts.elementPart[i];
    g.beginPath();t.forEach((n,j)=>{const q=P(mesh.nodes[n]);if(j)g.lineTo(...q);else g.moveTo(...q);});g.closePath();
    g.fillStyle=analysis==='explicit'?DYN_PART_COLORS[part%DYN_PART_COLORS.length]+'99':'#cfe3ea';g.fill();
    if(mesh.tris.length<6000){g.strokeStyle='#30556540';g.lineWidth=.5;g.stroke();}
  });
  // Restrained nodes.
  g.fillStyle='#185ab5';
  (scene.analysisNodes||[]).forEach((n,i)=>{if(n.mechanicalState&&n.mechanicalState!=='free'){const q=P(mesh.nodes[i]);g.fillRect(q[0]-2,q[1]-2,4,4);}});
  if(analysis==='explicit'){
    // Initial velocity arrows from each part centre.
    const speeds=mesh.parts.list.map(p=>Math.hypot(...(state.partVelocities[String(p.part)]||[0,0]).slice(0,2)));
    const maxSpeed=Math.max(...speeds,0);
    mesh.parts.list.forEach((p,i)=>{
      const v=state.partVelocities[String(p.part)]||[0,0,0];if(!speeds[i])return;
      const [x,y]=P(p.center),L=28+22*speeds[i]/maxSpeed,ux=v[0]/speeds[i],uy=-v[1]/speeds[i];
      g.strokeStyle='#b42318';g.fillStyle='#b42318';g.lineWidth=2.2;g.beginPath();g.moveTo(x,y);g.lineTo(x+ux*L,y+uy*L);g.stroke();
      g.beginPath();g.moveTo(x+ux*L,y+uy*L);g.lineTo(x+ux*(L-9)-uy*5,y+uy*(L-9)+ux*5);g.lineTo(x+ux*(L-9)+uy*5,y+uy*(L-9)-ux*5);g.closePath();g.fill();
      g.font='11px Segoe UI';g.fillText(`${DynamicsUI.fmt(speeds[i],3)} m/s`,x+ux*L+4,y+uy*L-4);
    });
    // Rigid walls: a thick line with hatching on the side away from the model.
    for(const wall of walls){
      const n=[wall.normal[0],wall.normal[1]],len=Math.hypot(...n);if(!(len>0))continue;
      const nx=n[0]/len,ny=n[1]/len,tx=-ny,ty=nx,c=P(wall.point),span=Math.max(w,h);
      g.strokeStyle='#2f4858';g.lineWidth=3;g.beginPath();g.moveTo(c[0]-tx*span,c[1]+ty*span);g.lineTo(c[0]+tx*span,c[1]-ty*span);g.stroke();
      const side=((meshCenter[0]-wall.point[0])*nx+(meshCenter[1]-wall.point[1])*ny)>=0?-1:1;
      g.lineWidth=1;for(let s=-span;s<span;s+=10){const ax=c[0]+tx*s,ay=c[1]-ty*s;g.beginPath();g.moveTo(ax,ay);g.lineTo(ax+(side*nx*8-tx*6),ay-(side*ny*8-ty*6));g.stroke();}
    }
    const gy=Number($dyn('dynGy').value)||0,gx=Number($dyn('dynGx').value)||0;
    if(gx||gy){const gl=Math.hypot(gx,gy);g.strokeStyle='#6d28d9';g.fillStyle='#6d28d9';g.lineWidth=2;g.beginPath();g.moveTo(w-24,24);g.lineTo(w-24+gx/gl*18,24-gy/gl*18);g.stroke();g.font='11px Segoe UI';g.fillText('g',w-40,20);}
  }
}
function renderDynamicsLoadPreview(){
  const canvas=$dyn('dynLoadPreview');
  if(!canvas.getBoundingClientRect().width)return;
  try{
    const load=dynamicsLoad(readDynamicsForm());
    const end=selectedDynamicsAnalysis()==='explicit'?Number($dyn('dynExplicitEnd').value):Number($dyn('dynEndTime').value);
    if(!(end>0))throw Error();
    const samples=DynamicsSettings.loadSamples(load,end);
    DynamicsUI.drawChart(canvas,[{label:'g(t)',x:samples.map(p=>p[0]),y:samples.map(p=>p[1])}],{xLabel:'时间 (s)',unit:'1'});
  }catch{const g=canvas.getContext('2d');g.clearRect(0,0,canvas.width,canvas.height);}
}
function renderDynamicsSetup(){
  if(currentPageKey()!=='dynamics')return;
  syncDynamicsForm();
  const mesh=dynamicsMesh();
  $dyn('dynModelName').textContent=scene.name||'未命名模型';
  $dyn('dynNodeCount').textContent=(scene.analysisNodes?.length||0).toLocaleString();
  $dyn('dynElementCount').textContent=(scene.mesh?.elements?.length||0).toLocaleString();
  $dyn('dynPartCount').textContent=String(mesh?.parts.list.length||0);
  renderDynamicsParts();renderDynamicsMaterials();renderDynamicsWalls();
  $dyn('dynModelInfo').textContent=mesh&&mesh.parts.list.length>1&&selectedDynamicsAnalysis()!=='explicit'
    ?`网格包含 ${mesh.parts.list.length} 个互不相连的部件；隐式分析中各部件独立振动，未约束的部件会出现刚体模态。`:'';
  if(typeof renderSpecialtyMeshStatus==='function')renderSpecialtyMeshStatus();
  requestAnimationFrame(()=>{renderDynamicsPreview();renderDynamicsLoadPreview();});
}

// ------------------------------------------------------------ run
function buildDynamicsRequest(){
  if(!scene.mesh?.elements?.length)throw Error('请先在基础计算页划分网格。');
  const state=readDynamicsForm();
  const payload=buildCalculationInputExport(),model=calculationInputPayloadToDirectModel(payload);
  model.materials.forEach((m,i)=>{m.id=payload.materials[i].id;});
  const settings={analysis:state.analysis,...state.form,load:state.analysis==='transient'||state.analysis==='explicit'?dynamicsLoad(state):undefined,
    gravity:state.gravity,walls:[],bodies:{},cards:{}};
  if(state.analysis==='explicit'){
    // Map the page's parts (analysis-node order) onto the exported model's parts.
    const mesh=dynamicsMesh();
    const exportIndex=new Map(payload.nodes.map((n,i)=>[String(n.id),i]));
    const triangles=model.elements.map(e=>[e.node1,e.node2,e.node3].map(no=>no-1));
    const exported=DynamicsSettings.components(triangles,model.nodes.length);
    mesh.parts.list.forEach((part,k)=>{
      const index=exportIndex.get(mesh.representative[k]);
      const target=index===undefined?-1:exported.nodePart[index];
      const velocity=state.partVelocities[String(part.part)]||[0,0,0];
      if(target>=0)settings.bodies[String(target+1)]={velocity:[velocity[0]||0,velocity[1]||0,0]};
    });
    for(const material of dynamicsMaterials()){
      const card=state.cards[material.id];if(!card)continue;
      if(card.model==='linked'){const linked=linkedBlastCard(material);if(linked)settings.cards[material.id]={model:'linked',card:linked.card,name:linked.name};}
      else settings.cards[material.id]=card;
    }
    settings.walls=state.walls.map(w=>({point:[w.point[0],w.point[1],0],normal:[w.normal[0],w.normal[1],0],friction:w.friction}));
  }
  return {model,settings:DynamicsSettings.normalize(settings)};
}
function renderDynamicsProgress(){
  const p=dynamicsProgressState,host=$dyn('dynProgressPanel');
  if(!p){host.hidden=true;return;}
  host.hidden=false;host.dataset.state=p.phase;
  const value=p.phase==='complete'?1:DynamicsUI.progressValue(p,p.analysis);
  $dyn('dynProgress').value=value;
  $dyn('dynProgressPercent').textContent=`${(value*100).toFixed(1)}%`;
  $dyn('dynProgressPhase').textContent=DynamicsUI.PHASES[p.phase]||p.phase;
  $dyn('dynProgressDetails').textContent=DynamicsUI.progressText(p,p.settings);
  $dyn('dynProgressError').textContent=p.error||'';
}
async function runDynamics2d(){
  if(dynamicsController)return;
  if(typeof runWithPreflight==='function'){let allowed=false;await runWithPreflight('dynamics',()=>{allowed=true;});if(!allowed||dynamicsController)return;}
  const status=$dyn('dynStatus'),controller=new AbortController();dynamicsController=controller;
  $dyn('startDynamics').disabled=true;$dyn('cancelDynamics').disabled=false;
  try{
    if(scene.analysisNodePlacement||scene.mesh?.metadata?.stale){await ensureCalculationMeshReadyForExport({adaptive:false});controller.signal.throwIfAborted();}
    const request=buildDynamicsRequest();
    dynamicsProgressState={phase:'preparing',fraction:0,elapsedMs:0,analysis:request.settings.analysis,settings:request.settings};renderDynamicsProgress();
    status.textContent='正在提交动力学计算…';
    const response=await window.fetchSpecialtyRun(controller,'./api/dynamics-runs',{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/x-ndjson'},body:JSON.stringify(request)});
    const result=await DynamicsUI.readStream(response,message=>{dynamicsProgressState={...dynamicsProgressState,...message};renderDynamicsProgress();});
    dynamicsProgressState={...dynamicsProgressState,phase:result.completed?'complete':'partial',fraction:1,error:result.termination?.message||''};renderDynamicsProgress();
    await setDynamicsResult(result);
    status.textContent=result.termination?.message||`${DynamicsUI.ANALYSIS_NAMES[result.analysis]}完成 · ${result.frames.length} 个结果帧 · 用时 ${(result.elapsedMs/1000).toFixed(1)} s`;
    setPage('dynamics-results');
  }catch(error){
    const cancelled=controller.signal.aborted||error.message==='计算已取消。';
    dynamicsProgressState={...(dynamicsProgressState||{}),phase:cancelled?'cancelled':'failed',error:cancelled?'':error.message};renderDynamicsProgress();
    status.textContent=cancelled?'动力学计算已取消。':error.message;
  }finally{dynamicsController=null;$dyn('startDynamics').disabled=false;$dyn('cancelDynamics').disabled=true;}
}

// ------------------------------------------------------------ module toggle
function setDynamicsEnabled(enabled){
  dynamicsEnabled=Boolean(enabled);
  $dyn('enableDynamicsModule').checked=dynamicsEnabled;
  document.querySelectorAll('[data-professional="dynamics"]').forEach(el=>{el.hidden=!dynamicsEnabled;});
  if(typeof updateProfessionalSummary==='function')updateProfessionalSummary();
  try{localStorage.setItem('fem.dynamics.enabled',String(dynamicsEnabled));}catch{/* storage unavailable */}
  if(!dynamicsEnabled){
    dynamicsController?.abort();
    window.dispatchEvent(new Event('tensora-dynamics-disabled'));
    if(['dynamics','dynamics-results'].includes(currentPageKey()))setPage('calculation');
  }
}
function clearDynamicsState(){
  dynamicsController?.abort();dynamicsProgressState=null;renderDynamicsProgress();dynamicsPartsCache=null;
  if(typeof clearDynamicsResult==='function')clearDynamicsResult();
  restoreDynamicsForm();
}
function initializeDynamics(){
  let enabled=false;try{enabled=localStorage.getItem('fem.dynamics.enabled')==='true';}catch{/* storage unavailable */}
  setDynamicsEnabled(enabled);
  $dyn('enableDynamicsModule').addEventListener('change',event=>setDynamicsEnabled(event.target.checked));
  const changed=()=>{readDynamicsForm();syncDynamicsForm();renderDynamicsPreview();renderDynamicsLoadPreview();$dyn('dynStatus').textContent='参数已更新，运行后生效。';};
  document.querySelectorAll('input[name="dynAnalysis"]').forEach(input=>input.addEventListener('change',()=>{changed();renderDynamicsSetup();}));
  for(const [id] of [...Object.values(DYN_FORM),...Object.values(DYN_LOAD)])$dyn(id).addEventListener('change',changed);
  for(const id of ['dynLoadTable','dynGx','dynGy'])$dyn(id).addEventListener('change',changed);
  $dyn('dynRayleighApply').addEventListener('click',()=>{
    try{
      const r=DynamicsSettings.rayleighFromRatio(Number($dyn('dynZeta').value),Number($dyn('dynZetaF1').value),Number($dyn('dynZetaF2').value));
      $dyn('dynAlpha').value=String(Number(r.alpha.toPrecision(6)));$dyn('dynBeta').value=String(Number(r.beta.toPrecision(6)));changed();
    }catch(error){$dyn('dynStatus').textContent=error.message;}
  });
  $dyn('dynAddWall').addEventListener('click',addDynamicsWall);
  $dyn('startDynamics').addEventListener('click',runDynamics2d);
  $dyn('cancelDynamics').addEventListener('click',e=>window.cancelSpecialtyRun(dynamicsController,e.currentTarget,message=>{$dyn('dynStatus').textContent=message;}));
  window.addEventListener('resize',()=>{if(currentPageKey()==='dynamics'){renderDynamicsPreview();renderDynamicsLoadPreview();}});
  restoreDynamicsForm();
}
