'use strict';
// Damage & deformation on the bundled OpenCourant solver: explicit dynamics with a
// slow linear load ramp and adaptive dynamic relaxation (/ADYREL) for a
// quasi-static response. TENSORA only writes the Starter/Engine decks (materials
// from the shared OpenCourant card registry, blast3d-cards.js), launches the
// unmodified executables and maps the animation output to the deformation result
// format. 2D uses the plane-strain one-layer brick slab of the 2D blast workspace
// (each TRI3 -> 3 QUAD4 -> HEPH brick, all z displacements fixed); 3D uses /TETRA4.
const fs=require('node:fs/promises');
const path=require('node:path');
const B3=require('./blast3d-runner');
const B2=require('./blast2d-opencourant');
const Cards=require('./blast3d-cards');
const {normalize,materialFor}=require('./deformation-settings');
const {tetData}=require('./solid3d');
const {f20,i10,title}=Cards;

const RUNS=path.join(__dirname,'calculation-data','deformation');
const LIMITS={nodes:200000,elements:400000,frames:201};
const ENGINE_LINE=/NC=\s*(\d+)\s+T=\s*([-+0-9.Ee]+)\s+DT=\s*([-+0-9.Ee]+)/;

// Rate-dependent laws would see the artificial strain rate of the compressed load
// ramp; the quasi-static run switches their rate enhancement off.
function quasiStaticCard(card){
  const c={...card};
  if(['jh2','hjc','jc'].includes(c.model))c.C=0;
  if(c.model==='rht'){c.betaC=0;c.betaT=0;}
  if(c.model==='cdpm2')c.rate=0;
  return c;
}

function prepare(model,raw){
  const s=normalize(raw);
  if(s.solver!=='opencourant')throw Error('OpenCourant 准静态路径需要选择 OpenCourant 求解器。');
  const dimension=model?.dimension===3?3:2;
  if(dimension===2&&s.planeMode!==1)throw Error('OpenCourant 二维损伤变形按平面应变单层薄片计算，请选择平面应变。');
  if(!Array.isArray(model?.nodes)||!model.nodes.length||!Array.isArray(model.elements)||!model.elements.length)throw Error('请先生成网格。');
  if(model.nodes.length>LIMITS.nodes||model.elements.length>LIMITS.elements)throw Error('OpenCourant 损伤变形最多支持 20 万节点 / 40 万单元。');
  if(s.increments+1>LIMITS.frames)throw Error(`OpenCourant 准静态路径的结果帧数（加载增量数）须不超过 ${LIMITS.frames-1}。`);
  const materialsByNo=new Map((model.materials||[]).map(m=>[m.materialNo,m]));
  const cards=new Map(),bases=new Map(),warnings=[];
  for(const e of model.elements){
    if(cards.has(e.materialNo))continue;
    const material=materialsByNo.get(e.materialNo)||{};
    const card=materialFor(s,material.id??String(e.materialNo??'legacy'));
    if(card.model!=='opencourant')throw Error('OpenCourant 准静态路径要求所有实体材料选择 OpenCourant 本构卡，不与 CalculiX 本构混算。');
    const rho=Number(material.density),E=Number(e.elasticModulus),nu=Number(e.poissonRatio);
    const label=material.name||`材料 ${e.materialNo}`;
    if(!(rho>0))throw Error(`${label}：显式准静态计算需要基础材料的密度。`);
    if(!(E>0)||!(nu>-1&&nu<.5))throw Error(`${label}：弹性模量或泊松比无效。`);
    const oc=quasiStaticCard(card.oc);
    if(JSON.stringify(oc)!==JSON.stringify(card.oc))warnings.push(`${label}：准静态计算关闭了 ${Cards.describe(oc)} 的应变率增强，强度按参考应变率取值。`);
    cards.set(e.materialNo,{...card,oc});bases.set(e.materialNo,{rho,E,nu,name:label});
  }
  for(const e of model.elements){
    const b=bases.get(e.materialNo);
    if(Math.abs(Number(e.elasticModulus)-b.E)>1e-9*b.E||Math.abs(Number(e.poissonRatio)-b.nu)>1e-12)throw Error(`${b.name}：同一材料的单元弹性参数不一致。`);
  }
  return {s,dimension,cards,bases,warnings};
}

// Nodal targets of the displacement-controlled mode (same rule as PhAST/OOFEM):
// u_i = F_i / max|F| * amplitude, applied in the loaded directions only.
function loadVectors(model,s,dimension){
  const axes=dimension===3?['X','Y','Z']:['X','Y'];
  const displacement=s.fractureLoading==='displacement';
  let peak=0;
  for(const n of model.nodes)for(const a of axes)peak=Math.max(peak,Math.abs(Number(n['force'+a])||0));
  if(!peak)throw Error('模型没有非零载荷。');
  return model.nodes.map(n=>axes.map(a=>{
    const f=Number(n['force'+a])||0;
    if(displacement&&f&&n['fixU'+a.toLowerCase()])throw Error('位移加载方向与固定约束冲突，请调整载荷节点或约束。');
    return displacement?f/peak*s.fractureDisplacement:f;
  }));
}

function buildDecks(model,raw){
  const {s,dimension,cards,bases,warnings}=prepare(model,raw);
  const displacement=s.fractureLoading==='displacement';
  const index=new Map(model.nodes.map((n,i)=>[n.nodeNo,i]));
  const S=['#RADIOSS STARTER','# TENSORA damage & deformation deck for OpenCourant (explicit quasi-static)','/BEGIN','tensora_deformation','      2026         0',
    '                  kg                   m                   s','                  kg                   m                   s',
    '/TITLE','TENSORA quasi-static damage and deformation'];
  // Materials: one OpenCourant card per base material.
  const materials=new Map();let materialId=0;
  for(const [no,card] of cards){
    const b=bases.get(no),id=++materialId;
    materials.set(no,{id,materialNo:no,...Cards.materialLines(card.oc,{id,name:b.name,rho:b.rho,E:b.E,nu:b.nu},b.name)});
  }
  const vectors=loadVectors(model,s,dimension);
  let geometry,partOf;
  const coordinates=[];      // solver node coordinates
  const fixed=[];            // solver node fixed flags [x,y,z]
  const targets=[];          // solver node load / displacement vectors [x,y,z]
  let L=0,thickness=1,mesh=null,quadArea=null;
  if(dimension===3){
    model.nodes.forEach((n,i)=>{coordinates.push([n.x,n.y,n.z]);fixed.push([n.fixUx,n.fixUy,n.fixUz].map(Boolean));targets.push(vectors[i]);});
    // Solver element k+1 is model element k (the result reader relies on it).
    const elements=model.elements.map((e,k)=>{
      const ids=[e.node1,e.node2,e.node3,e.node4].map(no=>{const i=index.get(no);if(i===undefined)throw Error('单元引用不存在的节点。');return i;});
      if(tetData(ids.map(i=>coordinates[i])).orientation<0)[ids[1],ids[2]]=[ids[2],ids[1]];
      return {id:k+1,nodes:ids,materialNo:e.materialNo};
    });
    geometry={elements};
  }else{
    // Plane-strain slab: TRI3 -> 3 QUAD4 (edge midpoints + centroid), extruded by H.
    mesh=B2.buildMesh(model,{});
    const {PX,PY,N,quads,quadParent,edges,tris,centroid}=mesh;quadArea=mesh.quadArea;
    let H=Infinity;for(const a of quadArea)H=Math.min(H,Math.sqrt(Math.abs(a)));
    thickness=H;
    const M=PX.length;
    const nodeFix=new Array(M).fill(null).map(()=>[false,false]);
    const nodeTarget=new Array(M).fill(null).map(()=>[0,0]);
    model.nodes.forEach((n,i)=>{nodeFix[i]=[Boolean(n.fixUx),Boolean(n.fixUy)];nodeTarget[i]=vectors[i];});
    // Midpoints and centroids follow the linear TRI3 field: fixed (or prescribed)
    // only where every parent vertex is.
    const inherit=(child,parents)=>{for(let d=0;d<2;d++){
      nodeFix[child][d]=parents.every(p=>nodeFix[p][d]);
      if(displacement&&parents.every(p=>nodeTarget[p][d]!==0))nodeTarget[child][d]=parents.reduce((a,p)=>a+nodeTarget[p][d],0)/parents.length;
    }};
    for(const e of edges.values())inherit(e.mid,[e.a,e.b]);
    tris.forEach((t,ti)=>inherit(centroid[ti],t.v));
    for(let i=0;i<M;i++){coordinates.push([PX[i],PY[i],0]);fixed.push([...nodeFix[i],true]);}
    for(let i=0;i<M;i++){coordinates.push([PX[i],PY[i],H]);fixed.push([...nodeFix[i],true]);}
    // Forces are per unit thickness: the slab carries H times the load, half per face.
    const scale=displacement?1:H/2;
    for(let k=0;k<2;k++)for(let i=0;i<M;i++)targets.push([nodeTarget[i][0]*scale,nodeTarget[i][1]*scale,0]);
    const elements=quads.map((q,k)=>({id:k+1,nodes:[...q,...q.map(n=>n+M)],materialNo:tris[quadParent[k]].materialNo}));
    geometry={elements,M,N};
    if(model.nodes.length!==N)throw Error('二维网格节点编号无效。');
  }
  const lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];
  for(const p of coordinates)for(let d=0;d<3;d++){lo[d]=Math.min(lo[d],p[d]);hi[d]=Math.max(hi[d],p[d]);}
  L=Math.hypot(hi[0]-lo[0],hi[1]-lo[1],dimension===3?hi[2]-lo[2]:0);
  let wave=0;for(const m of materials.values())wave=Math.max(wave,Math.sqrt((m.K+4*m.G/3)/m.rho));
  if(!(L>0)||!(wave>0))throw Error('模型尺寸或材料波速无效。');
  // Load ramp duration: a multiple of the longitudinal wave transit time over the
  // model; adaptive dynamic relaxation removes the remaining inertia.
  const rampTime=s.quasiStaticFactor*L/wave;

  S.push('/NODE','#  node_ID                 Xc                  Yc                  Zc');
  coordinates.forEach(([x,y,z],i)=>S.push(i10(i+1)+f20(x)+f20(y)+f20(z)));
  for(const m of materials.values())for(const line of m.lines)S.push(line);
  S.push('/PROP/SOLID/1',dimension===3?'tet4 quasi-static':'plane-strain slab brick',
    '#   Isolid    Ismstr      Iale     Icpre  Itetra10     Inpts   Itetra4    Iframe                  Dn',
    i10(dimension===3?0:24)+i10(0)+i10(0)+i10(0)+i10(0)+i10(0)+i10(0)+i10(0)+f20(0),
    '#                 qa                  qb                   h              Lambda                  Mu',f20(0)+f20(0)+f20(0)+f20(0)+f20(0),
    '#         deltaT_min            vdef_min            vdef_max             ASP_max             COL_min',f20(0)+f20(0)+f20(0)+f20(0)+f20(0),
    '#     Ndir sphpartID  Icontrol',i10(0)+i10(0)+i10(0));
  partOf=new Map();
  for(const m of materials.values()){
    partOf.set(m.materialNo,m.id);
    S.push(`/PART/${m.id}`,title(`material ${m.materialNo}`),'#  prop_ID    mat_ID subset_ID',i10(1)+i10(m.id)+i10(0));
    S.push(dimension===3?`/TETRA4/${m.id}`:`/BRICK/${m.id}`);
    for(const e of geometry.elements)if(e.materialNo===m.materialNo)S.push(i10(e.id)+e.nodes.map(n=>i10(n+1)).join(''));
  }
  let groupId=0,cardId=100;
  const group=(name,ids)=>{const g=++groupId;S.push(`/GRNOD/NODE/${g}`,title(name));for(let i=0;i<ids.length;i+=10)S.push(ids.slice(i,i+10).map(i10).join(''));return g;};
  const patterns=new Map();
  fixed.forEach((f,i)=>{const code=f.map(v=>v?1:0).join('');if(code!=='000'){if(!patterns.has(code))patterns.set(code,[]);patterns.get(code).push(i+1);}});
  for(const [code,ids] of patterns)S.push(`/BCS/${++cardId}`,`fixed ${code}`,'#  Tra rot   skew_ID  grnod_ID',`   ${code} 000${i10(0)}${i10(group(`fixed ${code}`,ids))}`);
  // Linear ramp to the final load factor, then held.
  const ramp=++cardId;
  S.push(`/FUNCT/${ramp}`,'quasi-static load ramp','#                  X                   Y',f20(0)+f20(0),f20(rampTime)+f20(s.loadFactor),f20(rampTime*100)+f20(s.loadFactor));
  // Identical load vectors share one node group.
  const loads=new Map();let loadedNodes=0;
  targets.forEach((v,i)=>{
    if(!v.some(x=>x!==0))return;
    loadedNodes++;
    for(let d=0;d<3;d++){
      if(v[d]===0||fixed[i][d]&&!displacement)continue;
      const key=`${d}:${v[d]}`;
      if(!loads.has(key))loads.set(key,{d,value:v[d],ids:[]});
      loads.get(key).ids.push(i+1);
    }
  });
  for(const {d,value,ids} of loads.values()){
    const g=group(displacement?'prescribed displacement':'load',ids);
    if(displacement)S.push(`/IMPDISP/${++cardId}`,'prescribed displacement',
      '#funct_IDT       Dir   skew_ID sensor_ID  grnod_ID  frame_ID',i10(ramp)+'XYZ'[d].padStart(10)+i10(0)+i10(0)+i10(g)+i10(0),
      '#           Ascale_x            Fscale_y              Tstart               Tstop',f20(1)+f20(value)+f20(0)+f20(0));
    else S.push(`/CLOAD/${++cardId}`,'load','#funct_IDT       Dir   skew_ID sensor_ID  grnod_ID   Itypfun             Ascalex             Fscaley',
      i10(ramp)+'XYZ'[d].padStart(10)+i10(0)+i10(0)+i10(g)+i10(0)+f20(1)+f20(value));
  }
  S.push('/END');
  const animDt=rampTime/s.increments;
  const list=[...materials.values()];
  const E=['/RUN/tensora_deformation/1',f20(rampTime+animDt*0.5).trim(),
    '/ADYREL',`0 ${f20(rampTime*1.01).trim()}`,
    '/ANIM/DT',`0 ${animDt}`,
    '/ANIM/VECT/DISP','/ANIM/BRICK/TENS/STRESS','/ANIM/BRICK/TENS/STRAIN','/ANIM/ELEM/EPSP',...Cards.damageAnimations(list),
    '/DT/NODA/CST/0','0.67 0',
    '/TFILE/0',String(rampTime/200),'/PRINT/-1000','/PARITH/ON','/END'];
  return {starter:S.join('\n')+'\n',engine:E.join('\n')+'\n',settings:s,dimension,materials,list,cards,warnings,geometry,mesh,quadArea,thickness,
    rampTime,animDt,loadedNodes,waveSpeed:wave,modelSize:L,partOf};
}

function thColumns(text){
  const lines=text.split(/\r?\n/).filter(Boolean);if(lines.length<2)return null;
  const head=lines[0].split(',').map(h=>h.replace(/[^\x20-\x7e]/g,'').replace(/"/g,'').trim());
  const rows=lines.slice(1).map(l=>l.split(',').map(Number)).filter(r=>r.every(Number.isFinite));
  return {head,rows,col:name=>head.findIndex(h=>h===name)};
}

// 2D: average the three sub-quads of each triangle, then area-weighted nodal values.
function frame2d(vtk,d,model,time){
  const {mesh,quadArea,geometry}=d,{N,tris}=mesh,M=geometry.M;
  const pick=names=>{const keys=Object.keys(vtk.cellData),norm=k=>k.toLowerCase().replace(/^3delem_/,'');for(const name of names){const hit=keys.find(k=>norm(k)===name.toLowerCase());if(hit)return vtk.cellData[hit];}return null;};
  const ids=vtk.pointData.NODE_ID?.values,disp=Object.entries(vtk.pointData).find(([k])=>/displacement/i.test(k))?.[1];
  if(!ids||!disp)throw Error('anim_to_vtk 输出缺少节点位移。');
  const u=new Float64Array(2*M);
  for(let p=0;p<ids.length;p++){const i=ids[p]-1;if(i>=0&&i<M){u[2*i]=disp.values[3*p];u[2*i+1]=disp.values[3*p+1];}}
  const cellIds=pick(['ELEMENT_ID'])?.values,stress=pick(['Stress']),strain=pick(['Strain']),epsp=pick(['Plastic_Strain'])?.values;
  const damg=pick(['Damage'])?.values,usr3=pick(['User_Var_3'])?.values;
  if(!cellIds||!stress||stress.width!==9)throw Error('anim_to_vtk 输出缺少单元应力张量。');
  const at=new Int32Array(mesh.quads.length).fill(-1);for(let c=0;c<cellIds.length;c++){const q=cellIds[c]-1;if(q>=0&&q<at.length)at[q]=c;}
  const order=[0,4,8,1,5,2];
  const frame={time,displacement:{},stress:{},strain:{},plasticStrain:{},damage:{},elementFields:{}};
  const nodal=new Float64Array(N*14),weight=new Float64Array(N);
  tris.forEach((t,ti)=>{
    const m=d.materials.get(t.materialNo),dmg=m.damage==='usr3'?usr3:m.damage==='damg'?damg:null;
    const acc=new Float64Array(14);let w=0;
    for(let j=0;j<3;j++){
      const q=3*ti+j,c=at[q];if(c<0)continue;const A=Math.abs(quadArea[q]);w+=A;
      order.forEach((o,k)=>{acc[k]+=A*stress.values[9*c+o];if(strain&&strain.width===9)acc[6+k]+=A*strain.values[9*c+o];});
      if(epsp)acc[12]+=A*epsp[c];if(dmg)acc[13]+=A*dmg[c];
    }
    if(w>0)for(let k=0;k<14;k++)acc[k]/=w;
    acc[13]=Math.min(1,Math.max(0,acc[13]));
    const e=model.elements[ti];
    frame.elementFields[e.elementNo]={stress:[...acc.subarray(0,6)],strain:[...acc.subarray(6,12)],plasticStrain:acc[12],damage:acc[13]};
    for(const v of t.v){weight[v]+=t.area;for(let k=0;k<14;k++)nodal[v*14+k]+=t.area*acc[k];}
  });
  model.nodes.forEach((n,i)=>{
    const w=weight[i]||1,v=k=>nodal[i*14+k]/w;
    frame.displacement[n.nodeNo]=[u[2*i],u[2*i+1]];
    frame.stress[n.nodeNo]=[0,1,2,3,4,5].map(v);
    frame.strain[n.nodeNo]=[6,7,8,9,10,11].map(v);
    frame.plasticStrain[n.nodeNo]=[v(12)];
    frame.damage[n.nodeNo]=[v(13)];
  });
  return frame;
}
// 3D: the blast reader averages element values to nodes by volume.
function frame3d(vtk,d,model,time,reader){
  const {fields}=B3.frameFields(vtk,reader);
  const frame={time,displacement:{},stress:{},strain:{},plasticStrain:{},damage:{}};
  model.nodes.forEach((n,i)=>{
    frame.displacement[n.nodeNo]=[fields.ux[i],fields.uy[i],fields.uz[i]];
    frame.stress[n.nodeNo]=['sxx','syy','szz','sxy','syz','sxz'].map(k=>fields[k][i]);
    frame.strain[n.nodeNo]=['exx','eyy','ezz','exy','eyz','exz'].map(k=>fields[k][i]);
    frame.plasticStrain[n.nodeNo]=[fields.plasticStrain[i]];
    frame.damage[n.nodeNo]=[Math.min(1,Math.max(0,fields.damage[i]))];
  });
  return frame;
}

async function runOpenCourantDeformation(model,raw,{signal,onProgress,timeoutMs=60*60*1000}={}){
  if(!B3.available().opencourant)throw Error('项目内缺少 OpenCourant 运行时，请恢复 third_party/opencourant/runtime-win-x64。');
  signal?.throwIfAborted();
  const started=Date.now();
  const progress=(phase,fraction,extra={})=>onProgress?.({phase,fraction,elapsedMs:Date.now()-started,...extra});
  progress('preparing',0,{completedIncrements:0});
  const d=buildDecks(model,raw),s=d.settings;
  await fs.mkdir(RUNS,{recursive:true});
  const dir=await fs.mkdtemp(path.join(RUNS,'opencourant-'));
  const runId=path.basename(dir);
  const logFile=await fs.open(path.join(dir,'solver.log'),'w'),log=logFile.createWriteStream();
  const work=await B3.asciiWork('tensora-deform-'),runtime=path.join(work,'runtime');
  try{
    await fs.writeFile(path.join(dir,'request.json'),JSON.stringify({model,settings:s}));
    await Promise.all([fs.writeFile(path.join(work,'deform_0000.rad'),d.starter),fs.writeFile(path.join(work,'deform_0001.rad'),d.engine)]);
    await fs.symlink(B3.OPENCOURANT,runtime,'junction');
    // OpenMP start-up dominates on small meshes; scale the thread count with the element count.
    const threads=Math.max(1,Math.min(8,require('node:os').cpus().length,Math.round(d.geometry.elements.length/4000)));
    const env=B3.environment(runtime,threads),exec=name=>path.join(runtime,'exec',name);
    const dylib=await B3.userLibraryArgs(work,d.list);
    log.write('=== OpenCourant Starter ===\n');
    const starterCode=await B3.execute(exec('starter_win64.exe'),['-i','deform_0000.rad','-np','1','-nt',String(threads),...dylib],{cwd:work,env,signal,timeoutMs:20*60*1000,log});
    if(starterCode!==0||!(await fs.readdir(work)).some(name=>/^deform_0000_\d+\.rst$/i.test(name))){
      const out=await fs.readFile(path.join(work,'deform_0000.out'),'latin1').catch(()=>'');
      await fs.writeFile(path.join(dir,'deform_0000.out'),out);
      const errors=out.split(/\r?\n/).map((line,i,all)=>/ERROR ID/.test(line)?all.slice(i,i+4).join(' ').replace(/\s+/g,' ').trim():null).filter(Boolean).slice(0,4);
      throw Error(`OpenCourant Starter 未通过模型检查（退出码 ${starterCode}）。${errors.join('；')||'请查看任务日志 '+runId+'。'}`);
    }
    log.write('\n=== OpenCourant Engine ===\n');
    let lastTime=0;
    const {code:engineCode,termination:interruption}=await B3.execute(exec('engine_win64.exe'),['-i','deform_0001.rad','-nt',String(threads),...dylib],
      {cwd:work,env,signal,timeoutMs,log,captureStop:true,onLine:line=>{
        const m=line.match(ENGINE_LINE);if(!m)return;
        const t=Number(m[2]);if(!(Number.isFinite(t)&&t>=lastTime))return;lastTime=t;
        const fraction=Math.min(1,t/d.rampTime),elapsed=Date.now()-started;
        progress('solving',fraction,{completedIncrements:Math.floor(fraction*s.increments+1e-9),cycle:Number(m[1]),
          estimatedRemainingMs:fraction>0.02?elapsed*(1-fraction)/fraction:null});
      }});
    const engineOut=await fs.readFile(path.join(work,'deform_0001.out'),'latin1').catch(()=>'');
    await fs.writeFile(path.join(dir,'deform_0001.out'),engineOut);
    const normal=/NORMAL TERMINATION/i.test(engineOut);
    const userError=engineOut.match(/RHT USER01:[^\n]*/)?.[0];
    const animations=(await fs.readdir(work)).filter(name=>/^deformA\d{3,}$/.test(name)).sort();
    if(!animations.length)throw Error(interruption?.message||userError||`OpenCourant Engine 没有输出结果帧（退出码 ${engineCode}）。请查看任务日志 ${runId}。`);
    progress('processing',0);
    const reader=d.dimension===3?{nodeCount:model.nodes.length,tets:d.geometry.elements.map(e=>e.nodes),
      volumes:d.geometry.elements.map(e=>Math.abs(tetData(e.nodes.map(i=>[model.nodes[i].x,model.nodes[i].y,model.nodes[i].z])).volume)),
      failure:d.list.some(m=>m.failure),erosion:d.list.some(m=>m.erodes),materialDamage:d.list.some(m=>m.damage),
      damageByPart:new Map(d.list.map(m=>[m.id,m.damage||null]))}:null;
    const frames=[];let frameError=null;
    for(const name of animations){
      try{
        const vtkName=name+'.vtk',stream=(await fs.open(path.join(work,vtkName),'w')).createWriteStream();
        let code;try{code=await B3.execute(exec('anim_to_vtk_win64.exe'),[name],{cwd:work,env,timeoutMs:10*60*1000,log:stream});}
        finally{await new Promise(resolve=>stream.end(resolve));}
        if(code!==0)throw Error('anim_to_vtk 转换失败：'+name);
        const vtk=await B3.readVtk(path.join(work,vtkName));await fs.rm(path.join(work,vtkName),{force:true});
        const t=Number.isFinite(vtk.time)?vtk.time:frames.length*d.animDt;
        const fraction=Math.min(1,t/d.rampTime);
        if(frames.length&&fraction<=frames.at(-1).time+1e-9)continue;
        const frame=d.dimension===3?frame3d(vtk,d,model,fraction,reader):frame2d(vtk,d,model,fraction);
        const finite=Object.values(frame.displacement).every(v=>v.every(Number.isFinite))&&Object.values(frame.stress).every(v=>v.every(Number.isFinite));
        if(!finite)throw Error(`载荷比例 ${(fraction*s.loadFactor).toFixed(4)} 处结果出现非有限数值，计算发散。`);
        frames.push(frame);
        progress('processing',frames.length/animations.length);
      }catch(error){frameError=error;break;}
    }
    if(!frames.length)throw Error(frameError?.message||interruption?.message||'没有有效结果帧。');
    const reached=frames.at(-1).time>=1-0.25/s.increments;
    // Quasi-static check: kinetic energy at the end of the ramp relative to internal energy.
    const warnings=[...d.warnings];
    let energyRatio=null;
    try{
      await B3.execute(exec('th_to_csv_win64.exe'),['deformT01'],{cwd:work,env,timeoutMs:120000,log:{write(){}}});
      const th=thColumns(await fs.readFile(path.join(work,'deformT01.csv'),'latin1'));
      const ke=th?.col('KINETIC ENERGY'),ie=th?.col('INTERNAL ENERGY');
      if(th&&ke>=0&&ie>=0&&th.rows.length){
        const last=th.rows.filter(r=>r[0]<=d.rampTime*1.0001).at(-1)||th.rows.at(-1);
        if(last[ie]>0)energyRatio=last[ke]/last[ie];
        if(energyRatio>0.05)warnings.push(`加载结束时动能为内能的 ${(energyRatio*100).toFixed(1)}%，惯性影响明显；请增大“准静态加载时长系数”后重算。`);
      }
    }catch{/* The energy check is advisory; the run log keeps the histories. */}
    const completed=normal&&reached&&!interruption&&!frameError;
    const message=interruption?.message||frameError?.message||userError
      ||(!normal?'OpenCourant Engine 未正常结束，只保留已经输出的结果帧。'
      :!reached?`OpenCourant Engine 在载荷比例 ${(frames.at(-1).time*s.loadFactor).toFixed(4)} 处提前停止（单元严重畸变或材料积分失败），只保留此前结果帧。`:null);
    const termination=completed?null:{code:interruption?.code||'solver-stop',message,convergedFraction:frames.at(-1).time};
    const anyDamage=d.list.some(m=>m.damage);
    const result={ok:true,completed,termination,completedIncrements:Math.round(frames.at(-1).time*s.increments),runId,
      solver:'OpenCourant 20261011 · 显式准静态',model,settings:s,frames,
      materialSettings:Object.fromEntries([...d.cards].map(([no,card])=>[no,card])),
      damageEvolution:anyDamage,plasticity:true,warnings,
      meta:{dimension:d.dimension,rampTime:d.rampTime,waveSpeed:d.waveSpeed,modelSize:d.modelSize,slabThickness:d.dimension===2?d.thickness:null,
        energyRatio,loadedNodes:d.loadedNodes,materials:d.list.map(({lines,...m})=>({materialNo:m.materialNo,law:m.law,damage:m.damage,userLibrary:m.userLibrary}))}};
    await fs.writeFile(path.join(dir,'result.json'),JSON.stringify(result));
    await Promise.all(['deform_0000.rad','deform_0001.rad','deform_0000.out'].map(name=>fs.copyFile(path.join(work,name),path.join(dir,name)).catch(()=>{})));
    progress(completed?'complete':'partial',frames.at(-1).time,{completedIncrements:result.completedIncrements});
    return result;
  }finally{
    log.end();await logFile.close().catch(()=>{});
    await fs.unlink(runtime).catch(()=>{});
    if(!process.env.TENSORA_KEEP_DEFORM_WORK)await fs.rm(work,{recursive:true,force:true,maxRetries:3}).catch(()=>{});
  }
}

module.exports={buildDecks,prepare,quasiStaticCard,runOpenCourantDeformation};
