// 3D structural dynamics stages of the 3D workspace. The setup stage collects the
// analysis type and parameters, part velocities (connected pieces of the tetrahedral
// mesh), material cards and rigid walls, and posts them to /api/dynamics-runs where
// CalculiX (modal / harmonic / implicit transient) or OpenCourant (explicit impact)
// computes the response. The result stage shows saved frames in the shared viewer.
import * as THREE from '../vendor/three/three.module.js';

export const DYNAMICS_FIELD_LABELS={phx:'X 位移相位',phy:'Y 位移相位',phz:'Z 位移相位'};
const STORAGE_KEY='fem.dynamics3d.settings.v1';
const PART_COLORS=[0x4f9fc9,0xe07a3f,0x6aa84f,0xa678c9,0xd4a017,0x3aa6a0,0xc95b7a,0x7b8794];
const FORM={analysis:'solid3dDynAnalysis',elementOrder:'solid3dDynOrder',threads:'solid3dDynThreads',modes:'solid3dDynModes',
  freqMin:'solid3dDynFreqMin',freqMax:'solid3dDynFreqMax',freqPoints:'solid3dDynFreqPoints',dampingRatio:'solid3dDynDamping',harmonicModes:'solid3dDynHarmonicModes',
  transientMethod:'solid3dDynTransientMethod',transientModes:'solid3dDynTransientModes',endTime:'solid3dDynEndTime',timeStep:'solid3dDynTimeStep',frames:'solid3dDynFrames',rayleighAlpha:'solid3dDynAlpha',rayleighBeta:'solid3dDynBeta',
  explicitEndTime:'solid3dDynExplicitEnd',explicitFrames:'solid3dDynExplicitFrames',timeStepScale:'solid3dDynDtScale',minTimeStep:'solid3dDynMinDt',friction:'solid3dDynFriction'};
const CHECKS={contact:'solid3dDynContact',selfContact:'solid3dDynSelfContact',explicitLoads:'solid3dDynExplicitLoads'};
const LOAD={shape:'solid3dDynLoadShape',factor:'solid3dDynLoadFactor',frequency:'solid3dDynLoadFrequency',duration:'solid3dDynLoadDuration',rise:'solid3dDynLoadRise'};
const GRAVITY=['solid3dDynGx','solid3dDynGy','solid3dDynGz'];
const TEXT=new Set(['analysis','elementOrder','shape','transientMethod']);

export function createDynamicsPanel(ctx){
  const $=id=>document.getElementById(id);
  const UI=window.DynamicsUI,DS=window.DynamicsSettings;
  let velocities={},cards={},walls=[],run=null,frame=null,request=null,playback=null,phase=0,loadTicket=0,partsCache=null;
  const cache=new Map();
  let animatedVector=null;

  // ------------------------------------------------------------ model parts
  function parts(){
    const mesh=ctx.getMesh();
    if(!mesh)return null;
    if(partsCache?.mesh===mesh)return partsCache;
    const p=UI.parts(mesh.tets,mesh.nodes);
    const volumePart=new Map();
    mesh.tets.forEach((_,i)=>{const v=String(mesh.tetVolumes?.[i]??'0');if(!volumePart.has(v))volumePart.set(v,p.elementPart[i]);});
    partsCache={mesh,...p,volumePart};
    return partsCache;
  }
  function materials(){
    const mesh=ctx.getMesh(),ids=new Set();
    for(const volume of mesh?.volumes||[]){const id=ctx.volumeMaterial(String(volume.id));if(id)ids.add(String(id));}
    return [...ids].map(id=>ctx.material(id)).filter(Boolean);
  }
  function linkedCard(material){
    const list=typeof blastMaterialLibrary!=='undefined'?blastMaterialLibrary:(window.PROJECT_MATERIAL_LIBRARY?.blastMaterials||[]);
    return material?.blastMaterialId?list.find(card=>card.id===material.blastMaterialId)||null:null;
  }

  // ------------------------------------------------------------ settings
  function readSettings(){
    const s={};
    for(const [key,id] of Object.entries(FORM))s[key]=TEXT.has(key)?$(id).value:Number($(id).value);
    for(const [key,id] of Object.entries(CHECKS))s[key]=$(id).checked;
    s.gravity=GRAVITY.map(id=>Number($(id).value)||0);
    const load={};for(const [key,id] of Object.entries(LOAD))load[key]=TEXT.has(key)?$(id).value:Number($(id).value);
    if(load.shape==='table'&&['transient','explicit'].includes(s.analysis)){
      const rows=$('solid3dDynLoadTable').value.split(/\r?\n/).map(l=>l.trim()).filter(Boolean).map(l=>l.split(/[,，\s;]+/).map(Number));
      if(rows.some(r=>r.length<2||!r.slice(0,2).every(Number.isFinite)))throw Error('载荷时程表每行需要“时间, 系数”两个数值。');
      load.table=rows.map(r=>[r[0],r[1]]);
    }
    s.load=load;
    s.bodies={};
    const p=parts();
    if(p)p.list.forEach(part=>{const v=velocities[String(part.part)];if(v)s.bodies[String(part.part)]={velocity:v};});
    s.cards={};
    for(const material of materials()){
      const card=cards[material.id];if(!card)continue;
      if(card.model==='linked'){const linked=linkedCard(material);if(linked)s.cards[material.id]={model:'linked',card:linked.card,name:linked.name};}
      else s.cards[material.id]=card;
    }
    s.walls=walls.map(w=>({point:[...w.point],normal:[...w.normal],friction:w.friction}));
    return DS.normalize(s);
  }
  const FORM_IDS=[...Object.values(FORM),...Object.values(CHECKS),...Object.values(LOAD),...GRAVITY,'solid3dDynLoadTable'];
  function snapshot(){
    return {form:Object.fromEntries(FORM_IDS.map(id=>[id,$(id).type==='checkbox'?$(id).checked:$(id).value])),velocities,cards,walls};
  }
  function restore(data){
    if(!data||typeof data!=='object')return;
    for(const [id,value] of Object.entries(data.form||{})){
      if(!FORM_IDS.includes(id))continue;
      if($(id).type==='checkbox')$(id).checked=Boolean(value);else if(typeof value==='string')$(id).value=value;
    }
    velocities={};for(const [k,v] of Object.entries(data.velocities||{}))if(Array.isArray(v))velocities[k]=[0,1,2].map(i=>Number(v[i])||0);
    cards={};for(const [k,c] of Object.entries(data.cards||{}))if(c&&['elastic','plastic','linked'].includes(c.model))cards[k]={...c};
    walls=(Array.isArray(data.walls)?data.walls:[]).slice(0,8).map(w=>({point:[0,1,2].map(i=>Number(w?.point?.[i])||0),normal:[0,1,2].map(i=>Number(w?.normal?.[i])||0),friction:Math.max(0,Number(w?.friction)||0)}));
    syncForm();renderLists();
  }
  function persist(){try{localStorage.setItem(STORAGE_KEY,JSON.stringify({form:snapshot().form}));}catch{/* storage unavailable */}}

  // ------------------------------------------------------------ view
  function syncForm(){
    const analysis=$('solid3dDynAnalysis').value;
    for(const el of document.querySelectorAll('#solid3dPage [data-dyn3]'))el.hidden=!el.dataset.dyn3.split(' ').includes(analysis);
    const shape=$('solid3dDynLoadShape').value;
    for(const el of document.querySelectorAll('#solid3dPage [data-dyn3-load]'))el.hidden=!el.dataset.dyn3Load.split(' ').includes(shape);
    for(const el of document.querySelectorAll('#solid3dPage [data-dyn3-method]'))el.hidden=el.dataset.dyn3Method!==$('solid3dDynTransientMethod').value;
    $('solid3dDynHelp').textContent=DS.ANALYSES.find(a=>a.id===analysis)?.help||'';
    $('solid3dRunDynamics').textContent={modal:'运行三维模态分析',harmonic:'运行三维谐响应分析',transient:'运行三维瞬态动力学',explicit:'运行三维显式碰撞'}[analysis];
    const loadsOff=analysis==='explicit'&&!$('solid3dDynExplicitLoads').checked;
    for(const id of [...Object.values(LOAD),'solid3dDynLoadTable'])$(id).disabled=loadsOff;
  }
  const input=(value,onChange,step='any')=>{const el=document.createElement('input');el.type='number';el.step=step;el.value=String(value);el.addEventListener('change',()=>onChange(Number(el.value)||0));return el;};
  const field=(label,el)=>{const l=document.createElement('label');l.textContent=label;l.append(el);return l;};
  function renderLists(){
    const p=parts();
    const host=$('solid3dDynParts');host.replaceChildren();
    if(!p){const li=document.createElement('li');li.textContent='请先在“计算”页生成四面体网格。';host.append(li);}
    else for(const part of p.list){
      const li=document.createElement('li');
      const title=document.createElement('strong');title.textContent=`部件 ${part.part} · ${part.nodes} 节点 · 中心 (${part.center.map(v=>UI.fmt(v,4)).join(', ')}) m`;
      title.style.borderLeft=`6px solid #${PART_COLORS[(part.part-1)%PART_COLORS.length].toString(16).padStart(6,'0')}`;title.style.paddingLeft='6px';
      const row=document.createElement('div');row.className='solid3d-section-coordinates';
      const v=velocities[String(part.part)]||[0,0,0];
      ['vx','vy','vz'].forEach((name,d)=>row.append(field(`${name} (m/s)`,input(v[d],value=>{const next=[...(velocities[String(part.part)]||[0,0,0])];next[d]=value;velocities[String(part.part)]=next;ctx.draw();}))));
      li.append(title,row);host.append(li);
    }
    const mats=$('solid3dDynMaterials');mats.replaceChildren();
    const list=materials();
    if(!list.length){const li=document.createElement('li');li.textContent='生成网格并为体域分配材料后显示。';mats.append(li);}
    for(const material of list){
      const li=document.createElement('li');
      const title=document.createElement('strong');title.textContent=`${material.name} · E ${UI.fmt(Number(material.elasticModulus),4)} GPa · ρ ${material.density||'—'} kg/m³`;
      const select=document.createElement('select');
      select.add(new Option('线弹性','elastic'));select.add(new Option('双线性弹塑性（屈服 + 线性硬化）','plastic'));
      const linked=linkedCard(material);if(linked)select.add(new Option(`关联爆破材料卡：${linked.name}`,'linked'));
      const card=cards[material.id]||{model:'elastic'};
      select.value=card.model==='linked'&&!linked?'elastic':card.model;
      const values={yieldStress:card.yieldStress>0?card.yieldStress/1e6:Number(material.yieldStrength)||235,tangentModulus:card.tangentModulus>0?card.tangentModulus/1e6:Math.max(1,Number(material.elasticModulus)*10),failureStrain:card.failureStrain||0};
      const row=document.createElement('div');row.className='solid3d-section-coordinates';
      const save=()=>{cards[material.id]={model:select.value,yieldStress:values.yieldStress*1e6,tangentModulus:values.tangentModulus*1e6,failureStrain:values.failureStrain};row.hidden=select.value!=='plastic';};
      row.append(field('σy (MPa)',input(values.yieldStress,v=>{values.yieldStress=v;save();})),field('Et (MPa)',input(values.tangentModulus,v=>{values.tangentModulus=v;save();})),
        field('失效塑性应变',input(values.failureStrain,v=>{values.failureStrain=v;save();})));
      select.addEventListener('change',save);save();
      li.append(title,field('本构',select),row);mats.append(li);
    }
    const wallHost=$('solid3dDynWalls');wallHost.replaceChildren();
    if(!walls.length){const li=document.createElement('li');li.textContent='未设置刚性墙。';wallHost.append(li);}
    walls.forEach((wall,k)=>{
      const li=document.createElement('li');
      const title=document.createElement('strong');title.textContent=`刚性墙 ${k+1}`;
      const point=document.createElement('div');point.className='solid3d-section-coordinates';
      ['X','Y','Z'].forEach((axis,d)=>point.append(field(`点 ${axis} (m)`,input(wall.point[d],v=>{wall.point[d]=v;ctx.draw();}))));
      const normal=document.createElement('div');normal.className='solid3d-section-coordinates';
      ['nX','nY','nZ'].forEach((axis,d)=>normal.append(field(axis,input(wall.normal[d],v=>{wall.normal[d]=v;ctx.draw();}))));
      const remove=document.createElement('button');remove.type='button';remove.textContent='删除';
      remove.addEventListener('click',()=>{walls.splice(k,1);renderLists();ctx.draw();});
      li.append(title,point,normal,field('摩擦系数',input(wall.friction,v=>{wall.friction=Math.max(0,v);})),remove);wallHost.append(li);
    });
  }
  function addWall(fromFace){
    const mesh=ctx.getMesh();
    if(!mesh)throw Error('请先在“计算”页生成四面体网格。');
    const lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];
    for(const p of mesh.nodes)for(let d=0;d<3;d++){lo[d]=Math.min(lo[d],p[d]);hi[d]=Math.max(hi[d],p[d]);}
    const gap=0.02*Math.max(...hi.map((v,d)=>v-lo[d]),1e-6);
    if(fromFace){
      const face=mesh.surfaces.find(s=>s.id===ctx.selectedFace());
      if(!face)throw Error('请先在视窗中点选一个平面外表面。');
      // Area-weighted centre and normal of the CAD face; the wall sits just outside it.
      const c=[0,0,0],n=[0,0,0];let area=0;
      for(const tri of face.triangles){
        const [a,b,d]=tri.map(i=>mesh.nodes[i]);
        const u=[b[0]-a[0],b[1]-a[1],b[2]-a[2]],v=[d[0]-a[0],d[1]-a[1],d[2]-a[2]];
        const cr=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]],A=Math.hypot(...cr)/2;
        for(let k=0;k<3;k++){c[k]+=A*(a[k]+b[k]+d[k])/3;n[k]+=cr[k]/2;}area+=A;
      }
      const len=Math.hypot(...n);if(!(len>0))throw Error('所选面没有确定的法向。');
      const normal=n.map(v=>v/len),center=c.map(v=>v/area);
      const mid=[0,1,2].map(d=>(lo[d]+hi[d])/2),inward=(mid[0]-center[0])*normal[0]+(mid[1]-center[1])*normal[1]+(mid[2]-center[2])*normal[2]>0;
      const out=inward?normal.map(v=>-v):normal;
      walls.push({point:center.map((v,d)=>v+out[d]*gap*0.5),normal:out.map(v=>-v||0),friction:0});
    }else walls.push({point:[0,0,lo[2]-gap],normal:[0,0,1],friction:0.2});
    renderLists();ctx.draw();
  }
  async function refreshStatus(){
    try{
      const state=await (await fetch('/api/dynamics-status',{cache:'no-store'})).json();
      $('solid3dDynEngine').textContent=`CalculiX 2.22 隐式动力学${state.calculix?'':'（未找到求解器）'} · OpenCourant 显式碰撞${state.opencourant?'':'（未找到运行时）'}`;
    }catch{/* keep the static description */}
  }
  function show(){partsCache=null;refreshStatus();syncForm();renderLists();updateResultControls();}
  // Setup tint: parts in their colours for explicit runs.
  function volumeTint(volume){
    if($('solid3dDynAnalysis').value!=='explicit')return null;
    const part=parts()?.volumePart.get(String(volume));
    return part==null?null:PART_COLORS[part%PART_COLORS.length];
  }

  // Rigid walls as translucent squares and initial velocities as arrows.
  function decorate(group,size,{setup}){
    const shown=setup?($('solid3dDynAnalysis').value==='explicit'?walls:[]):(run?.analysis==='explicit'?run.meta?.walls||[]:[]);
    for(const wall of shown){
      const n=new THREE.Vector3(...wall.normal);if(n.lengthSq()===0)continue;n.normalize();
      const plane=new THREE.Mesh(new THREE.PlaneGeometry(size*1.2,size*1.2),new THREE.MeshBasicMaterial({color:0x2f4858,transparent:true,opacity:.22,side:THREE.DoubleSide,depthWrite:false}));
      plane.position.set(...wall.point);plane.quaternion.setFromUnitVectors(new THREE.Vector3(0,0,1),n);group.add(plane);
      const edges=new THREE.LineSegments(new THREE.EdgesGeometry(plane.geometry),new THREE.LineBasicMaterial({color:0x2f4858}));
      edges.position.copy(plane.position);edges.quaternion.copy(plane.quaternion);group.add(edges);
    }
    if(!setup||$('solid3dDynAnalysis').value!=='explicit')return;
    const p=parts();if(!p)return;
    const speeds=p.list.map(part=>Math.hypot(...(velocities[String(part.part)]||[0,0,0])));
    const max=Math.max(...speeds,0);
    p.list.forEach((part,i)=>{
      if(!speeds[i])return;
      const dir=new THREE.Vector3(...velocities[String(part.part)]).normalize();
      // Drawn on top of the solids: the arrow starts inside the part.
      const arrow=new THREE.ArrowHelper(dir,new THREE.Vector3(...part.center),size*(0.3+0.2*speeds[i]/max),0xb42318,size*.06,size*.03);
      arrow.traverse(object=>{if(object.material){object.material.depthTest=false;object.material.transparent=true;}object.renderOrder=3;});
      group.add(arrow);
    });
  }

  // ------------------------------------------------------------ run
  async function runDynamics(button){
    if(request)return;
    const solid=ctx.solidPayload();
    const settings=readSettings();
    persist();
    const controller=new AbortController(),progress=$('solid3dDynProgress'),text=$('solid3dDynProgressText');
    request=controller;button.disabled=true;$('solid3dCancelDynamics').disabled=false;
    progress.value=0;progress.hidden=false;text.textContent='';
    ctx.status('正在提交三维动力学计算…');
    try{
      const response=await window.fetchSpecialtyRun(controller,'./api/dynamics-runs',{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/x-ndjson'},
        body:JSON.stringify({solid,settings})});
      const result=await UI.readStream(response,message=>{progress.value=UI.progressValue(message,settings.analysis);text.textContent=UI.progressText(message,settings);});
      await setRun(result);
      ctx.status(result.termination?.message||`${UI.ANALYSIS_NAMES[result.analysis]}完成 · ${result.frames.length} 个结果帧 · 用时 ${(result.elapsedMs/1000).toFixed(1)} s`);
      ctx.setPage('dynamics-results');
    }catch(error){
      if(controller.signal.aborted||error.message==='计算已取消。')ctx.status('三维动力学计算已取消。');else throw error;
    }finally{request=null;button.disabled=false;$('solid3dCancelDynamics').disabled=true;progress.hidden=true;}
  }

  // ------------------------------------------------------------ results
  function autoScale(summary=run){
    if(!summary||summary.analysis==='explicit')return 1;
    const mesh=ctx.getMesh();if(!mesh)return 1;
    const lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];
    for(const p of mesh.nodes)for(let d=0;d<3;d++){lo[d]=Math.min(lo[d],p[d]);hi[d]=Math.max(hi[d],p[d]);}
    const size=Math.max(...hi.map((v,d)=>v-lo[d]));
    const peak=Math.max(...summary.frames.filter((_,i)=>!summary.modes?.[i]?.rigid||summary.analysis!=='modal').map(f=>f.stats.umag?.[1]||0),0);
    return peak>0?Number((0.1*size/peak).toPrecision(2)):1;
  }
  async function setRun(summary){
    stopPlayback();cache.clear();run=summary;frame=null;
    $('solid3dDynScale').value=String(autoScale(summary));
    const slider=$('solid3dDynFrame');slider.max=String(summary.frames.length-1);
    let start=summary.frames.length-1;
    if(summary.analysis==='modal')start=Math.max(0,(summary.modes||[]).findIndex(m=>!m.rigid));
    if(summary.analysis==='harmonic')start=summary.frames.reduce((best,f,i)=>(f.stats.umag?.[1]||0)>(summary.frames[best].stats.umag?.[1]||0)?i:best,0);
    slider.value=String(start);
    const curve=$('solid3dDynCurveSelect');curve.replaceChildren();
    for(const c of UI.curves(summary))curve.add(new Option(c.label,c.key));
    updateResultControls();
    await showFrame(start);
  }
  async function loadFrame(summary,index){
    const data=await UI.loadFrame(summary,index,cache);
    if(data.nodeFields)return data;
    const n=summary.nodeCount,displacementVector=new Float32Array(n*3);
    for(let i=0;i<n;i++){displacementVector[i*3]=data.fields.ux?.[i]||0;displacementVector[i*3+1]=data.fields.uy?.[i]||0;displacementVector[i*3+2]=data.fields.uz?.[i]||0;}
    const stats=summary.frames[index].stats;
    Object.assign(data,{nodeFields:data.fields,displacementVector,maxDisplacement:stats.umag?.[1]||0,maxVonMises:stats.vm?.[1]||0,time:summary.frames[index].value});
    return data;
  }
  async function showFrame(index){
    const ticket=++loadTicket;
    const data=await loadFrame(run,index);
    if(ticket!==loadTicket)return;
    frame=data;
    $('solid3dDynFrame').value=String(index);
    const f=run.frames[index];
    $('solid3dDynSummary').textContent=[UI.frameLabel(run,index),`最大位移 ${UI.fmt(f.stats.umag?.[1],4)} m`,f.stats.vm?`最大 von Mises ${UI.fmt(f.stats.vm[1],4)} Pa`:'',
      run.completed===false?run.termination?.message:''].filter(Boolean).join(' · ');
    for(const row of document.querySelectorAll('#solid3dDynModeTable tbody tr'))row.classList.toggle('active',run.analysis==='modal'&&Number(row.dataset.index)===index);
    updateFrameButtons();drawCurve();ctx.draw();
  }
  function drawCurve(){
    const canvas=$('solid3dDynCurve');
    if(!run||canvas.closest('[hidden]'))return;
    const curve=UI.curves(run).find(c=>c.key===$('solid3dDynCurveSelect').value);
    const index=Number($('solid3dDynFrame').value);
    if(!curve){UI.drawChart(canvas,[]);return;}
    UI.drawChart(canvas,curve.multi||[{label:curve.label,x:curve.x,y:curve.y}],{unit:curve.unit,xLabel:curve.bars?'模态阶数':UI.axisLabel(run),log:curve.log,bars:curve.bars,
      marker:run.analysis==='modal'?run.frames[index]?.mode:run.frames[index]?.value});
  }
  function renderModes(){
    const table=$('solid3dDynModeTable');table.replaceChildren();
    $('solid3dDynModesWrap').hidden=!run?.modes?.length;
    if(!run?.modes?.length)return;
    const head=document.createElement('tr');
    for(const text of ['阶次','频率 (Hz)','X 向累计','Y 向累计','Z 向累计']){const th=document.createElement('th');th.textContent=text;head.append(th);}
    const thead=document.createElement('thead');thead.append(head);
    const body=document.createElement('tbody');
    UI.modeRows(run).forEach((m,i)=>{
      const tr=document.createElement('tr');tr.dataset.index=String(i);if(m.rigid)tr.className='rigid';
      for(const text of [String(m.mode),m.rigid?'刚体模态':UI.fmt(m.frequency,6),...m.cumulative.map(v=>`${v.toFixed(1)}%`)]){const td=document.createElement('td');td.textContent=text;tr.append(td);}
      if(run.analysis==='modal')tr.addEventListener('click',()=>{stopPlayback();showFrame(i).catch(e=>ctx.status(e.message));});
      body.append(tr);
    });
    table.className='dyn-mode-table';table.append(thead,body);
  }
  function updateFrameButtons(){
    const slider=$('solid3dDynFrame'),many=Boolean(run)&&run.frames.length>1;
    slider.disabled=!many;
    $('solid3dDynPrevious').disabled=!many||slider.value==='0';
    $('solid3dDynNext').disabled=!many||slider.value===slider.max;
    $('solid3dPlayDynamics').disabled=!run||(!many&&run.analysis!=='modal');
    $('solid3dPlayDynamics').textContent=playback!==null?'暂停':run?.analysis==='modal'||run?.analysis==='harmonic'?'振型动画':'播放 / 暂停';
    $('solid3dDynFrameTitle').textContent=run?.analysis==='modal'?'模态阶数':run?.analysis==='harmonic'?'激励频率':'时间帧';
  }
  function updateResultControls(){
    const available=Boolean(run);
    $('solid3dExportDynamics').disabled=!available;
    if(!available)$('solid3dDynSummary').textContent='请在三维结构动力学设置页运行计算。';
    $('solid3dDynRunInfo').textContent=UI.runInfo(run);
    renderModes();updateFrameButtons();
  }
  function stopPlayback(){
    if(playback!==null){cancelAnimationFrame(playback);clearTimeout(playback);}
    playback=null;phase=0;animatedVector=null;updateFrameButtons();
  }
  function play(){
    if(!run)return;
    if(playback!==null){stopPlayback();ctx.draw();return;}
    if(run.analysis==='modal'||run.analysis==='harmonic'){
      let last=performance.now();
      const tick=now=>{phase+=(now-last)/1000*2*Math.PI/1.6;last=now;ctx.draw();playback=requestAnimationFrame(tick);};
      playback=requestAnimationFrame(tick);updateFrameButtons();return;
    }
    const slider=$('solid3dDynFrame');
    if(slider.value===slider.max)slider.value='0';
    const step=async()=>{
      try{await showFrame(Number(slider.value));}catch(error){ctx.status(error.message);stopPlayback();return;}
      if(playback===null)return;
      if(slider.value===slider.max){stopPlayback();return;}
      slider.stepUp();playback=setTimeout(step,150);
    };
    playback=setTimeout(step,0);updateFrameButtons();
  }
  // Deformation factor of the viewer: oscillates during mode-shape animation.
  function displayScale(){
    const scale=Number($('solid3dDynScale').value);
    if(!Number.isFinite(scale)||scale<0)return 0;
    return playback!==null&&run?.analysis==='modal'?scale*Math.sin(phase):scale;
  }
  function displayVector(){
    if(!frame||playback===null||run?.analysis!=='harmonic')return frame?.displacementVector;
    const amplitude=frame.displacementVector;
    if(animatedVector?.length!==amplitude.length)animatedVector=new Float32Array(amplitude.length);
    const phases=[frame.fields.phx,frame.fields.phy,frame.fields.phz];
    for(let axis=0;axis<3;axis++){
      for(let node=0;node<run.nodeCount;node++){
        const i=node*3+axis;
        animatedVector[i]=UI.harmonicDisplacement(amplitude[i],phases[axis]?.[node]??0,phase);
      }
    }
    return animatedVector;
  }
  async function exportRun(){
    const summary=run;
    if(!summary)throw Error('还没有三维动力学结果。');
    const handle=await window.chooseExportFile(window.uiText('TENSORA-三维动力学结果.json'),'application/json','.json');
    if(!handle)return;
    await window.writeExportFile(handle,async writer=>{
      await writer.write(`{"summary":${JSON.stringify(summary)},"frames":[`);
      for(let i=0;i<summary.frames.length;i++){
        const data=await UI.loadFrame(summary,i,null);
        const fields=Object.fromEntries(Object.entries(data.fields).map(([k,v])=>[k,Array.from(v,x=>Number.isFinite(x)?x:null)]));
        await writer.write((i?',':'')+JSON.stringify({value:summary.frames[i].value,label:UI.frameLabel(summary,i),fields}));
      }
      await writer.write(']}');
    });
    ctx.status('三维动力学结果已导出。');
  }

  // ------------------------------------------------------------ events
  const guard=fn=>async event=>{try{await fn(event);}catch(error){ctx.status(error.message);}};
  for(const id of FORM_IDS)$(id).addEventListener('change',()=>{syncForm();persist();if(id==='solid3dDynAnalysis'){renderLists();ctx.draw();}});
  $('solid3dDynRayleighApply').addEventListener('click',guard(()=>{
    const r=DS.rayleighFromRatio(Number($('solid3dDynZeta').value),Number($('solid3dDynZetaF1').value),Number($('solid3dDynZetaF2').value));
    $('solid3dDynAlpha').value=String(Number(r.alpha.toPrecision(6)));$('solid3dDynBeta').value=String(Number(r.beta.toPrecision(6)));persist();
  }));
  $('solid3dDynAddWall').addEventListener('click',guard(()=>addWall(false)));
  $('solid3dDynFaceWall').addEventListener('click',guard(()=>addWall(true)));
  $('solid3dRunDynamics').addEventListener('click',guard(event=>runDynamics(event.target)));
  $('solid3dCancelDynamics').addEventListener('click',e=>window.cancelSpecialtyRun(request,e.currentTarget,ctx.status));
  $('solid3dDynFrame').addEventListener('input',guard(()=>{stopPlayback();return showFrame(Number($('solid3dDynFrame').value));}));
  for(const [name,step] of [['Previous',-1],['Next',1]])$('solid3dDyn'+name).addEventListener('click',guard(()=>{
    stopPlayback();const slider=$('solid3dDynFrame');slider.stepUp(step);return showFrame(Number(slider.value));
  }));
  $('solid3dPlayDynamics').addEventListener('click',play);
  $('solid3dDynScale').addEventListener('change',()=>ctx.draw());
  $('solid3dDynAutoScale').addEventListener('click',()=>{$('solid3dDynScale').value=String(autoScale());ctx.draw();});
  $('solid3dDynCurveSelect').addEventListener('change',drawCurve);
  $('solid3dExportDynamics').addEventListener('click',guard(exportRun));
  try{const saved=JSON.parse(localStorage.getItem(STORAGE_KEY)||'null');if(saved)restore(saved);}catch{/* ignore */}
  syncForm();

  return {
    show,volumeTint,decorate,snapshot,restore,stopPlayback,displayScale,displayVector,drawCurve,readSettings,
    partCount:()=>parts()?.list.length||0,
    frame:()=>frame,hasRun:()=>Boolean(run),run:()=>run,fields:()=>run?.fields||[],
    currentIndex:()=>Number($('solid3dDynFrame').value),
    goToFrame(index){if(!run)return;stopPlayback();return showFrame(index).catch(error=>ctx.status(error.message));},
    meshChanged(){request?.abort();stopPlayback();++loadTicket;run=null;frame=null;cache.clear();partsCache=null;velocities={};
      const slider=$('solid3dDynFrame');slider.max=slider.value='0';renderLists();updateResultControls();},
    abort(){request?.abort();stopPlayback();}
  };
}
