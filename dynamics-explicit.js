'use strict';
// OpenCourant 20261011 adapter of the dynamics workspace: explicit impact dynamics.
// Parts are the connected pieces of the mesh. TENSORA writes the Starter/Engine
// decks (initial velocities /INIVEL, node-to-surface contact /INTER/TYPE7 between
// parts, planar rigid walls /RWALL/PLANE, gravity /GRAV, loads /CLOAD with a time
// function, materials from the shared card registry blast3d-cards.js), launches the
// unmodified executables (OpenMP threads) and reads the animation and time-history
// output. 2D uses the plane-strain one-layer brick slab of the 2D blast workspace.
const fs=require('node:fs/promises');
const path=require('node:path');
const {availableParallelism}=require('node:os');
const B3=require('./blast3d-runner');
const B2=require('./blast2d-opencourant');
const Cards=require('./blast3d-cards');
const DS=require('./dynamics-settings');
const {meshCpuThreads}=require('./cpu-threads');
const {tetData}=require('./solid3d');
const {f20,i10,title}=Cards;
const ENGINE_LINE=/NC=\s*(\d+)\s+T=\s*([-+0-9.Ee]+)\s+DT=\s*([-+0-9.Ee]+)/;
const MAX_CONTACT_PARTS=12;

// Material card of one base material: elastic, bilinear plasticity (Johnson–Cook LAW2
// with n = 1 and no rate or temperature terms) or a linked OpenCourant card.
function materialCard(material,card={model:'elastic'}){
  if(card.model==='plastic')return {card:Cards.normalize({model:'jc',a:card.yieldStress,b:card.tangentModulus,n:1,C:0,rate0:1,m:1,tMelt:1800,tRef:293,rhoCp:0,
    epsMax:card.failureStrain,sigMax:0,tension:0}),label:`双线性弹塑性（σy ${(card.yieldStress/1e6).toPrecision(4)} MPa，Et ${(card.tangentModulus/1e6).toPrecision(4)} MPa${card.failureStrain>0?`，εp,f ${card.failureStrain}`:''}）`};
  if(card.model==='linked')return {card:Cards.normalize(card.card),label:`${card.name||'OpenCourant 材料卡'}（${Cards.describe(Cards.normalize(card.card))}）`};
  return {card:Cards.normalize({model:'elastic'}),label:'线弹性'};
}

function faceKey(a,b,c){return [a,b,c].sort((x,y)=>x-y).join(',');}
const sub=(a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]];
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];

// Solver geometry: nodes, solid elements, part of each element, fixed DOFs, nodal
// loads, outward contact segments per part and the map back to model nodes.
function geometry(m){
  const parts=DS.components(m.elements,m.coords.length);
  if(m.dimension===3){
    const coordinates=m.coords,fixed=[],loads=[];
    for(let i=0;i<coordinates.length;i++){fixed.push([0,1,2].map(d=>Boolean(m.fixed[i*3+d])));loads.push([0,1,2].map(d=>m.force[i*3+d]));}
    const owners=new Map();
    m.elements.forEach((tet,t)=>{for(let k=0;k<4;k++){const face=tet.filter((_,j)=>j!==k),key=faceKey(...face);
      const list=owners.get(key);if(list)list.push({t,face,opposite:tet[k]});else owners.set(key,[{t,face,opposite:tet[k]}]);}});
    const segments=[];
    for(const list of owners.values()){
      if(list.length!==1)continue;
      const {t,face,opposite}=list[0],[a,b,c]=face.map(n=>coordinates[n]);
      const outward=dot(cross(sub(b,a),sub(c,a)),sub(coordinates[opposite],a))<0;
      segments.push({part:parts.elementPart[t],nodes:outward?[face[0],face[1],face[2],face[2]]:[face[0],face[2],face[1],face[1]]});
    }
    const elements=m.elements.map((e,k)=>({id:k+1,nodes:e,material:m.elementMaterial[k],part:parts.elementPart[k]}));
    const weights=m.elements.map(e=>Math.abs(tetData(e.map(n=>coordinates[n])).volume));
    return {coordinates,elements,fixed,loads,segments,weights,partCount:parts.count,thickness:1,modelCount:coordinates.length,kind:'tetra'};
  }
  // Plane-strain slab: TRI3 -> 3 QUAD4 -> one layer of bricks of thickness H.
  const mesh=B2.buildMesh(m.source,{});
  const {PX,PY,N,quads,quadParent,edges,tris,centroid,quadArea}=mesh;
  if(N!==m.coords.length)throw Error('二维网格节点编号无效。');
  // Every node is fixed out of plane, so the thickness only scales mass and stiffness.
  // A slab thinner than the in-plane elements would make the thickness govern the
  // explicit step of every brick; the largest element size keeps the step in-plane.
  let H=0;for(const a of quadArea)H=Math.max(H,Math.sqrt(Math.abs(a)));
  const M=PX.length;
  const nodeFix=Array.from({length:M},()=>[false,false]);
  for(let i=0;i<N;i++)nodeFix[i]=[Boolean(m.fixed[i*3]),Boolean(m.fixed[i*3+1])];
  const inherit=(child,parents)=>{for(let d=0;d<2;d++)nodeFix[child][d]=parents.every(p=>nodeFix[p][d]);};
  for(const e of edges.values())inherit(e.mid,[e.a,e.b]);
  tris.forEach((t,ti)=>inherit(centroid[ti],t.v));
  const coordinates=[],fixed=[],loads=[];
  for(let layer=0;layer<2;layer++)for(let i=0;i<M;i++){
    coordinates.push([PX[i],PY[i],layer*H]);fixed.push([...nodeFix[i],true]);
    // Loads are per unit thickness: the slab carries H times the load, half per face.
    loads.push(i<N?[m.force[i*3]*H/2,m.force[i*3+1]*H/2,0]:[0,0,0]);
  }
  // Tri element order of the neutral model equals the direct-model order used by buildMesh.
  const triPart=parts.elementPart;
  const elements=quads.map((q,k)=>({id:k+1,nodes:[...q,...q.map(n=>n+M)],material:m.elementMaterial[quadParent[k]],part:triPart[quadParent[k]]}));
  // Boundary half-edges of the quad mesh (CCW quads: outward normal on the right).
  const count=new Map();
  quads.forEach((q,k)=>{for(let j=0;j<4;j++){const a=q[j],b=q[(j+1)%4],key=a<b?`${a},${b}`:`${b},${a}`;const v=count.get(key);if(v)v.n++;else count.set(key,{n:1,a,b,k});}});
  const segments=[];
  for(const {n,a,b,k} of count.values())if(n===1)segments.push({part:triPart[quadParent[k]],nodes:[a,b,b+M,a+M]});
  return {coordinates,elements,fixed,loads,segments,weights:quadArea.map(Math.abs),partCount:parts.count,thickness:H,M,mesh,modelCount:N,kind:'slab'};
}

function buildDecks(m,s){
  const g=geometry(m);
  const S=['#RADIOSS STARTER','# TENSORA structural dynamics deck for OpenCourant (explicit impact)','/BEGIN','tensora_dynamics','      2026         0',
    '                  kg                   m                   s','                  kg                   m                   s',
    '/TITLE','TENSORA explicit impact dynamics'];
  // Materials: one card per base material in use.
  const used=[...new Set(g.elements.map(e=>e.material))].sort((a,b)=>a-b);
  const materials=new Map();
  for(const index of used){
    const base=m.materials[index];
    if(!(base.rho>0))throw Error(`${base.name}：显式动力学需要材料密度。`);
    const requested=s.cards[base.id]||{model:'elastic'};
    if(requested.model==='plastic'&&!(requested.yieldStress>0))throw Error(`${base.name}：双线性弹塑性需要屈服应力。`);
    const {card,label}=materialCard(base,requested);
    const id=materials.size+1;
    materials.set(index,{id,index,label,name:base.name,...Cards.materialLines(card,{id,name:base.name,rho:base.rho,E:base.E,nu:base.nu},base.name)});
  }
  const list=[...materials.values()];
  S.push('/NODE','#  node_ID                 Xc                  Yc                  Zc');
  g.coordinates.forEach(([x,y,z],i)=>S.push(i10(i+1)+f20(x)+f20(y)+f20(z)));
  for(const mat of list)for(const line of mat.lines)S.push(line);
  S.push('/PROP/SOLID/1',g.kind==='tetra'?'tet4 explicit':'plane-strain slab brick',
    '#   Isolid    Ismstr      Iale     Icpre  Itetra10     Inpts   Itetra4    Iframe                  Dn',
    i10(g.kind==='tetra'?0:24)+i10(0)+i10(0)+i10(0)+i10(0)+i10(0)+i10(0)+i10(0)+f20(0),
    '#                 qa                  qb                   h              Lambda                  Mu',f20(0)+f20(0)+f20(0)+f20(0)+f20(0),
    '#         deltaT_min            vdef_min            vdef_max             ASP_max             COL_min',f20(0)+f20(0)+f20(0)+f20(0)+f20(0),
    '#     Ndir sphpartID  Icontrol',i10(0)+i10(0)+i10(0));
  // OpenCourant parts: one per (mesh part, material) so energies stay per body.
  const opParts=new Map();
  for(const e of g.elements){const key=`${e.part}:${e.material}`;if(!opParts.has(key))opParts.set(key,{id:opParts.size+1,part:e.part,material:e.material,rows:[]});
    opParts.get(key).rows.push(i10(e.id)+e.nodes.map(n=>i10(n+1)).join(''));}
  for(const p of opParts.values()){
    S.push(`/PART/${p.id}`,title(`part ${p.part+1} ${m.materials[p.material].name}`),'#  prop_ID    mat_ID subset_ID',i10(1)+i10(materials.get(p.material).id)+i10(0));
    S.push(g.kind==='tetra'?`/TETRA4/${p.id}`:`/BRICK/${p.id}`);
    for(const row of p.rows)S.push(row);
  }
  let groupId=0,cardId=100;
  const group=(name,ids)=>{const id=++groupId;S.push(`/GRNOD/NODE/${id}`,title(name));for(let i=0;i<ids.length;i+=10)S.push(ids.slice(i,i+10).map(i10).join(''));return id;};
  // Restraints grouped by DOF pattern.
  const patterns=new Map();
  g.fixed.forEach((f,i)=>{const code=f.map(v=>v?1:0).join('');if(code!=='000'){if(!patterns.has(code))patterns.set(code,[]);patterns.get(code).push(i+1);}});
  for(const [code,ids] of patterns)S.push(`/BCS/${++cardId}`,`fixed ${code}`,'#  Tra rot   skew_ID  grnod_ID',`   ${code} 000${i10(0)}${i10(group(`fixed ${code}`,ids))}`);
  // Nodes of each part.
  const partNodes=Array.from({length:g.partCount},()=>new Set());
  for(const e of g.elements)for(const n of e.nodes)partNodes[e.part].add(n+1);
  const partGroups=partNodes.map((set,k)=>set.size?group(`part ${k+1} nodes`,[...set].sort((a,b)=>a-b)):0);
  // Initial velocities per part (2D: in-plane components only).
  const bodies=[];
  for(let k=0;k<g.partCount;k++){
    const v=(s.bodies[String(k+1)]?.velocity||[0,0,0]).map((x,d)=>m.dimension===2&&d===2?0:x);
    bodies.push({part:k+1,nodes:partNodes[k].size,velocity:v});
    if(v.some(x=>x!==0))S.push(`/INIVEL/TRA/${++cardId}`,`part ${k+1} initial velocity`,'#                 Vx                  Vy                  Vz   Gnod_id   Skew_id',
      f20(v[0])+f20(v[1])+f20(v[2])+i10(partGroups[k])+i10(0),'#             tstart   sens_ID',f20(0)+i10(0));
  }
  const allNodes=group('all nodes',g.coordinates.map((_,i)=>i+1));
  const constant=++cardId;
  S.push(`/FUNCT/${constant}`,'constant','#                  X                   Y',f20(0)+f20(1),f20(s.explicitEndTime*10)+f20(1));
  const gravity=m.dimension===2?[s.gravity[0],s.gravity[1],0]:s.gravity;
  gravity.forEach((value,d)=>{if(value!==0)S.push(`/GRAV/${++cardId}`,`gravity ${'XYZ'[d]}`,
    '#funct_IDT       DIR   skew_ID sensor_ID  grnod_ID                      Ascale_x            Fscale_Y',
    i10(constant)+'XYZ'[d].padStart(10)+i10(0)+i10(0)+i10(allNodes)+' '.repeat(10)+f20(1)+f20(value));});
  // External loads of the model with the chosen time history.
  let loadedNodes=0;
  if(s.explicitLoads){
    const funct=++cardId;
    S.push(`/FUNCT/${funct}`,'load history','#                  X                   Y');
    const samples=DS.loadSamples(s.load,s.explicitEndTime);
    for(const [t,v] of samples)S.push(f20(t)+f20(v));
    S.push(f20(s.explicitEndTime*10)+f20(samples.at(-1)[1]));
    const byValue=new Map();
    g.loads.forEach((v,i)=>{
      if(!v.some(x=>x!==0))return;loadedNodes++;
      v.forEach((value,d)=>{if(!value||g.fixed[i][d])return;const key=`${d}:${value}`;if(!byValue.has(key))byValue.set(key,{d,value,ids:[]});byValue.get(key).ids.push(i+1);});
    });
    if(!byValue.size)throw Error('已选择施加外载荷，但模型中没有可施加的载荷。');
    for(const {d,value,ids} of byValue.values())S.push(`/CLOAD/${++cardId}`,'external load','#funct_IDT       Dir   skew_ID sensor_ID  grnod_ID   Itypfun             Ascalex             Fscaley',
      i10(funct)+'XYZ'[d].padStart(10)+i10(0)+i10(0)+i10(group('load',ids))+i10(0)+f20(1)+f20(value));
  }
  // Characteristic element size (contact gap) and wave speed (time step estimate).
  let minEdge=Infinity;
  for(const e of g.elements){
    const p=e.nodes.map(n=>g.coordinates[n]),pairs=g.kind==='tetra'?[[0,1],[0,2],[0,3],[1,2],[1,3],[2,3]]:[[0,1],[1,2],[2,3],[3,0]];
    for(const [a,b] of pairs)minEdge=Math.min(minEdge,Math.hypot(...sub(p[a],p[b])));
  }
  const wave=Math.max(...list.map(mat=>Math.sqrt((mat.K+4*mat.G/3)/mat.rho)));
  const erosion=list.some(mat=>mat.erodes);
  // Contact between parts: each ordered pair (secondary nodes of i, main surface of j).
  const segmentsByPart=Array.from({length:g.partCount},()=>[]);
  for(const seg of g.segments)segmentsByPart[seg.part].push(seg.nodes);
  const surfaceNodes=segmentsByPart.map(list=>[...new Set(list.flat())].map(n=>n+1).sort((a,b)=>a-b));
  const gap=0.1*minEdge;
  const contacts=[];
  const surface=(name,segs)=>{const id=++cardId;S.push(`/SURF/SEG/${id}`,title(name));segs.forEach((seg,k)=>S.push(i10(k+1)+seg.map(n=>i10(n+1)).join('')));return id;};
  const contact=(name,nodeGroup,surfaceId,igap)=>S.push(`/INTER/TYPE7/${++cardId}`,title(name),
    '# grnod_id   surf_id      Istf      Ithe      Igap   Multimp      Ibag      Idel     Icurv      Iadm',
    i10(nodeGroup)+i10(surfaceId)+i10(4)+i10(0)+i10(igap)+' '.repeat(10)+i10(0)+i10(erosion?2:0)+i10(0)+i10(0),
    '#          Fscalegap             Gap_max             Fpenmax                         Itied      Ists',f20(0)+f20(0)+f20(0)+' '.repeat(20)+i10(0)+i10(0),
    '#              Stmin               Stmax   Percent_mesh_size               dtmin  Irem_gap   Irem_i2',f20(0)+f20(0)+f20(0)+f20(0)+i10(0)+i10(0),
    '#              Stfac                Fric              GAPmin              Tstart               Tstop',f20(1)+f20(s.friction)+f20(gap)+f20(0)+f20(0),
    '#      IBC                        Inacti               VIS_S               VIS_F              Bumult',' '.repeat(30)+i10(6)+f20(0)+f20(0)+f20(0),
    '#    Ifric    Ifiltr               Xfreq     Iform   sens_ID   fct_IDF             AscaleF   fric_ID',i10(0)+i10(0)+f20(0)+i10(0)+i10(0)+i10(0)+f20(0)+i10(0));
  if(s.contact&&g.partCount>1){
    if(g.partCount>MAX_CONTACT_PARTS)throw Error(`模型有 ${g.partCount} 个独立部件，超过自动接触上限 ${MAX_CONTACT_PARTS}；请合并部件或关闭部件间接触。`);
    const surfaces=segmentsByPart.map((segs,k)=>segs.length?surface(`part ${k+1} surface`,segs):0);
    const nodeGroups=surfaceNodes.map((ids,k)=>ids.length?group(`part ${k+1} surface nodes`,ids):0);
    for(let i=0;i<g.partCount;i++)for(let j=0;j<g.partCount;j++){
      if(i===j||!nodeGroups[i]||!surfaces[j])continue;
      contact(`part ${i+1} nodes on part ${j+1}`,nodeGroups[i],surfaces[j],0);contacts.push([i+1,j+1]);
    }
  }
  if(s.selfContact)segmentsByPart.forEach((segs,k)=>{
    if(!segs.length)return;
    contact(`part ${k+1} self contact`,group(`part ${k+1} self contact nodes`,surfaceNodes[k]),surface(`part ${k+1} self surface`,segs),3);contacts.push([k+1,k+1]);
  });
  // Planar rigid walls, normal oriented toward the model.
  const center=[0,1,2].map(d=>g.coordinates.reduce((a,p)=>a+p[d],0)/g.coordinates.length);
  const walls=[];
  s.walls.forEach((wall,k)=>{
    let normal=m.dimension===2?[wall.normal[0],wall.normal[1],0]:wall.normal;
    const length=Math.hypot(...normal);
    if(!(length>0))throw Error(`刚性墙 ${k+1} 的法向在平面内为零。`);
    normal=normal.map(v=>v/length);
    const point=m.dimension===2?[wall.point[0],wall.point[1],0]:wall.point;
    if(dot(sub(center,point),normal)<0)normal=normal.map(v=>-v||0);
    const behind=g.coordinates.filter(p=>dot(sub(p,point),normal)<-1e-9*Math.max(1,Math.hypot(...p))).length;
    if(behind)throw Error(`刚性墙 ${k+1} 穿过模型（${behind} 个节点在墙后），请调整墙的位置。`);
    const slide=wall.friction>0?2:0,id=++cardId;
    S.push(`/RWALL/PLANE/${id}`,title(`rigid wall ${k+1}`),'#  node_ID     Slide  grnd_ID1  grnd_ID2     Iform',i10(0)+i10(slide)+i10(allNodes)+i10(0)+i10(0));
    if(slide===2)S.push('#                  d                fric            Diameter                           ifq',f20(0)+f20(wall.friction)+f20(0)+' '.repeat(20)+i10(0));
    else S.push('#                  d                fric                 ifq',f20(0)+' '.repeat(20)+f20(0));
    S.push('#                 XM                  YM                  ZM',f20(point[0])+f20(point[1])+f20(point[2]),
      '#                XM1                 YM1                 ZM1',f20(point[0]+normal[0])+f20(point[1]+normal[1])+f20(point[2]+normal[2]));
    walls.push({id,point,normal,friction:wall.friction});
  });
  if(walls.length)S.push('/TH/RWALL/1','rigid wall forces','#      var       var       var       var       var       var       var       var       var       var','DEF',
    '#      Obj       Obj       Obj       Obj       Obj       Obj       Obj       Obj       Obj       Obj',walls.map(w=>i10(w.id)).join(''));
  S.push('/TH/PART/2','part energies','#      var       var       var       var       var       var       var       var       var       var','DEF',
    '#      Obj       Obj       Obj       Obj       Obj       Obj       Obj       Obj       Obj       Obj');
  const partIds=[...opParts.values()].map(p=>p.id);
  for(let i=0;i<partIds.length;i+=10)S.push(partIds.slice(i,i+10).map(i10).join(''));
  S.push('/END');
  const animDt=s.explicitEndTime/(s.explicitFrames-1);
  const E=['/RUN/tensora_dynamics/1',f20(s.explicitEndTime+animDt*0.5).trim(),
    '/ANIM/DT',`0 ${animDt}`,
    '/ANIM/VECT/DISP','/ANIM/VECT/VEL','/ANIM/BRICK/TENS/STRESS','/ANIM/BRICK/TENS/STRAIN','/ANIM/ELEM/VONM','/ANIM/ELEM/EPSP','/ANIM/ELEM/P',
    ...Cards.damageAnimations(list),
    // Nodal time step; a positive minimum step adds nodal mass where needed (mass scaling).
    '/DT/NODA/CST/0',`${s.timeStepScale} ${s.minTimeStep}`,
    '/TFILE/0',String(Math.max(animDt/10,s.explicitEndTime/4000)),'/PRINT/-500','/PARITH/ON','/END'];
  const timeStep=Math.max(s.timeStepScale*minEdge/wave,s.minTimeStep);
  return {starter:S.join('\n')+'\n',engine:E.join('\n')+'\n',g,list,materials,animDt,
    meta:{parts:g.partCount,minTimeStep:s.minTimeStep,bodies,contacts:contacts.length,contactGap:gap,walls,gravity,loadedNodes,minEdge,waveSpeed:wave,timeStepEstimate:timeStep,
      cycleEstimate:Math.ceil(s.explicitEndTime/timeStep),slabThickness:g.kind==='slab'?g.thickness:null,erosion,
      materials:list.map(mat=>({name:mat.name,label:mat.label,law:mat.law,E:mat.E,nu:mat.nu,rho:mat.rho}))}};
}

function thTable(text){
  const lines=text.split(/\r?\n/).filter(Boolean);if(lines.length<2)return null;
  const head=lines[0].split(',').map(h=>h.replace(/[^\x20-\x7e]/g,'').replace(/"/g,'').replace(/\s+/g,' ').trim());
  while(head.length&&!head.at(-1))head.pop();
  const rows=lines.slice(1).map(l=>l.split(',').slice(0,head.length).map(v=>Number(v))).filter(r=>r.length===head.length&&r.every(Number.isFinite));
  return {head,rows};
}

// Nodal fields on model nodes from one animation frame.
function frameFields(vtk,d,m){
  const N=d.g.modelCount;
  const pick=names=>{const keys=Object.keys(vtk.cellData),norm=k=>k.toLowerCase().replace(/^3delem_/,'');for(const name of names){const hit=keys.find(k=>norm(k)===name.toLowerCase());if(hit)return vtk.cellData[hit];}return null;};
  const ids=vtk.pointData.NODE_ID?.values;
  const disp=Object.entries(vtk.pointData).find(([k])=>/displacement/i.test(k))?.[1];
  const vel=Object.entries(vtk.pointData).find(([k])=>/velocity/i.test(k))?.[1];
  if(!ids||!disp)throw Error('anim_to_vtk 输出缺少节点位移。');
  const keys=['ux','uy','uz','umag','vx','vy','vz','vmag','sxx','syy','szz','sxy','syz','sxz','vm','pressure','peeq','damage'];
  const f=Object.fromEntries(keys.map(k=>[k,new Float32Array(N)]));
  for(let p=0;p<ids.length;p++){
    const i=ids[p]-1;if(i<0||i>=N)continue;   // 2D: the bottom-layer vertices are the model nodes
    for(let k=0;k<3;k++){f[['ux','uy','uz'][k]][i]=disp.values[3*p+k];if(vel)f[['vx','vy','vz'][k]][i]=vel.values[3*p+k];}
  }
  const cellIds=pick(['ELEMENT_ID'])?.values,stress=pick(['Stress']),epsp=pick(['Plastic_Strain'])?.values,pres=pick(['Pressure'])?.values;
  const damg=pick(['Damage'])?.values,usr3=pick(['User_Var_3'])?.values,alive=pick(['EROSION_STATUS'])?.values;
  if(!cellIds||!stress||stress.width!==9)throw Error('anim_to_vtk 输出缺少单元应力张量。');
  const at=new Int32Array(d.g.elements.length).fill(-1);
  for(let c=0;c<cellIds.length;c++){const e=cellIds[c]-1;if(e>=0&&e<at.length)at[e]=c;}
  const order=[0,4,8,1,5,2];
  const width=9,sums=new Float64Array(N*width),weight=new Float64Array(N);
  const values=new Float64Array(width);
  const read=(e,c)=>{
    order.forEach((o,k)=>{values[k]=stress.values[9*c+o];});
    values[6]=pres?pres[c]:-(values[0]+values[1]+values[2])/3;
    values[7]=epsp?epsp[c]:0;
    const mat=d.materials.get(e.material);
    values[8]=mat?.damage==='usr3'?usr3?.[c]??0:mat?.damage==='damg'?damg?.[c]??0:0;
  };
  if(d.g.kind==='tetra'){
    // Element values -> volume-weighted nodal averages (eroded elements excluded).
    for(const e of d.g.elements){
      const c=at[e.id-1];if(c<0||(alive&&alive[c]===0))continue;
      read(e,c);const w=d.g.weights[e.id-1];
      for(const n of e.nodes){weight[n]+=w;for(let k=0;k<width;k++)sums[n*width+k]+=w*values[k];}
    }
  }else{
    // 2D slab: the three quads of a triangle are averaged, then area-weighted to its vertices.
    const {quadParent,tris}=d.g.mesh;
    const triSums=new Float64Array(tris.length*width),triArea=new Float64Array(tris.length);
    for(const e of d.g.elements){
      const c=at[e.id-1];if(c<0||(alive&&alive[c]===0))continue;
      read(e,c);const t=quadParent[e.id-1],w=d.g.weights[e.id-1];
      triArea[t]+=w;for(let k=0;k<width;k++)triSums[t*width+k]+=w*values[k];
    }
    tris.forEach((t,ti)=>{if(!triArea[ti])return;for(const v of t.v){weight[v]+=t.area;for(let k=0;k<width;k++)sums[v*width+k]+=t.area*triSums[ti*width+k]/triArea[ti];}});
  }
  const sk=['sxx','syy','szz','sxy','syz','sxz','pressure','peeq','damage'];
  for(let i=0;i<N;i++){
    f.umag[i]=Math.hypot(f.ux[i],f.uy[i],f.uz[i]);f.vmag[i]=Math.hypot(f.vx[i],f.vy[i],f.vz[i]);
    if(!(weight[i]>0)){for(const k of [...sk,'vm'])f[k][i]=NaN;continue;}
    sk.forEach((k,j)=>{f[k][i]=sums[i*width+j]/weight[i];});
    f.vm[i]=Math.sqrt(((f.sxx[i]-f.syy[i])**2+(f.syy[i]-f.szz[i])**2+(f.szz[i]-f.sxx[i])**2)/2+3*(f.sxy[i]**2+f.syz[i]**2+f.sxz[i]**2));
  }
  if(!d.list.some(mat=>mat.damage))delete f.damage;
  if(!d.list.some(mat=>['jc','jh2','hjc','rht','cdpm2','dp','dpcap'].includes(mat.law)))delete f.peeq;
  return f;
}

async function run(m,s,{dir,signal,timeoutMs,progress,writeFrame}){
  if(!B3.available().opencourant)throw Error('项目内缺少 OpenCourant 运行时，请恢复 third_party/opencourant/runtime-win-x64。');
  const d=buildDecks(m,s);
  const work=await B3.asciiWork('tensora-dyn-'),runtime=path.join(work,'runtime');
  const log=(await fs.open(path.join(dir,'solver.log'),'w')).createWriteStream();
  try{
    await Promise.all([fs.writeFile(path.join(work,'dyn_0000.rad'),d.starter),fs.writeFile(path.join(work,'dyn_0001.rad'),d.engine)]);
    await fs.symlink(B3.OPENCOURANT,runtime,'junction');
    // OpenMP start-up dominates on small meshes; scale the thread count with the element count.
    const threads=meshCpuThreads(s.threads,d.g.elements.length,4000);
    const env=B3.environment(runtime,threads),exec=name=>path.join(runtime,'exec',name);
    env.OMP_DYNAMIC='FALSE';
    const dylib=await B3.userLibraryArgs(work,d.list);
    progress('starter',0);
    log.write('=== OpenCourant Starter ===\n');
    const starterCode=await B3.execute(exec('starter_win64.exe'),['-i','dyn_0000.rad','-np','1','-nt',String(threads),...dylib],{cwd:work,env,signal,timeoutMs:20*60*1000,log});
    if(starterCode!==0||!(await fs.readdir(work)).some(name=>/^dyn_0000_\d+\.rst$/i.test(name))){
      const out=await fs.readFile(path.join(work,'dyn_0000.out'),'latin1').catch(()=>'');
      await fs.writeFile(path.join(dir,'dyn_0000.out'),out);
      const errors=out.split(/\r?\n/).map((line,i,all)=>/ERROR ID/.test(line)?all.slice(i,i+4).join(' ').replace(/\s+/g,' ').trim():null).filter(Boolean).slice(0,4);
      throw Error(`OpenCourant Starter 未通过模型检查（退出码 ${starterCode}）。${errors.join('；')||'请查看任务日志。'}`);
    }
    progress('engine',0);
    log.write('\n=== OpenCourant Engine ===\n');
    let lastTime=0;
    const {code:engineCode,termination:interruption}=await B3.execute(exec('engine_win64.exe'),['-i','dyn_0001.rad','-nt',String(threads),...dylib],
      {cwd:work,env,signal,timeoutMs,log,captureStop:true,onLine:line=>{
        const hit=line.match(ENGINE_LINE);if(!hit)return;
        const t=Number(hit[2]);if(!(Number.isFinite(t)&&t>=lastTime))return;lastTime=t;
        progress('engine',Math.min(1,t/s.explicitEndTime),{time:t,cycle:Number(hit[1]),dt:Number(hit[3])});
      }});
    if(interruption?.code==='cancelled')throw Error(interruption.message);
    const engineOut=await fs.readFile(path.join(work,'dyn_0001.out'),'latin1').catch(()=>'');
    await fs.writeFile(path.join(dir,'dyn_0001.out'),engineOut);
    const normal=/NORMAL TERMINATION/i.test(engineOut);
    const animations=(await fs.readdir(work)).filter(name=>/^dynA\d{3,}$/.test(name)).sort();
    if(!animations.length)throw Error(interruption?.message||`OpenCourant Engine 没有输出结果帧（退出码 ${engineCode}）。`);
    progress('processing',0);
    // anim_to_vtk converts one frame per process: several conversions run in parallel
    // while the frames are read and stored in order.
    const convert=async name=>{
      const vtkName=name+'.vtk',stream=(await fs.open(path.join(work,vtkName),'w')).createWriteStream();
      let code;try{code=await B3.execute(exec('anim_to_vtk_win64.exe'),[name],{cwd:work,env,signal,timeoutMs:10*60*1000,log:stream});}
      finally{await new Promise(resolve=>stream.end(resolve));}
      if(code!==0)throw Error('anim_to_vtk 转换失败：'+name);
      return path.join(work,vtkName);
    };
    const pool=Math.max(1,Math.min(6,availableParallelism()-1)),pending=new Map();let next=0;
    const launch=()=>{while(next<animations.length&&pending.size<pool){const name=animations[next++],job=convert(name);job.catch(()=>{});pending.set(name,job);}};
    const frames=[];let frameError=null;
    for(const name of animations){
      try{
        launch();
        const file=await pending.get(name);pending.delete(name);
        const vtk=await B3.readVtk(file);await fs.rm(file,{force:true});
        const t=Number.isFinite(vtk.time)?vtk.time:frames.length*d.animDt;
        if(frames.length&&t<=frames.at(-1)+1e-15)continue;
        const fields=frameFields(vtk,d,m);
        if(!fields.umag.every(Number.isFinite)||fields.umag.some(v=>v>1e3))throw Error(`t = ${t.toPrecision(4)} s 起结果发散（单元翻转或时间步过小）。`);
        await writeFrame(fields,t,{});
        frames.push(t);
        progress('processing',frames.length/animations.length);
      }catch(error){frameError=error;break;}
    }
    await Promise.allSettled(pending.values());
    if(signal?.aborted)throw Error('计算已取消。');
    if(!frames.length)throw Error(frameError?.message||interruption?.message||'没有有效结果帧。');
    // Global and part energies, rigid wall forces (time histories).
    const history={};
    try{
      await B3.execute(exec('th_to_csv_win64.exe'),['dynT01'],{cwd:work,env,timeoutMs:120000,log:{write(){}}});
      const th=thTable(await fs.readFile(path.join(work,'dynT01.csv'),'latin1'));
      if(th){
        const column=pattern=>th.head.findIndex(h=>pattern.test(h));
        const time=th.rows.map(r=>r[0]);
        const series=(key,label,unit,index,scale=1)=>{if(index>=0)history[key]={label,unit,x:time,y:th.rows.map(r=>r[index]*scale)};};
        // 2D slab: energies and forces per unit thickness (divide by the slab thickness).
        const unit=m.dimension===2?1/d.g.thickness:1;
        series('kinetic','动能','J',column(/^KINETIC ENERGY$/i),unit);
        series('internal','内能（应变能 + 塑性功）','J',column(/^INTERNAL ENERGY$/i),unit);
        series('plastic','塑性功','J',column(/^PLASTIC WORK$/i),unit);
        series('contact','接触能','J',column(/^CONTACT ENERGY$/i),unit);
        series('external','外力功','J',column(/^EXTERNAL WORK$/i),unit);
        series('hourglass','沙漏能','J',column(/^HOURGLASS ENERGY$/i),unit);
        const added=column(/^PERCENTAGE ADDED MASS$/i);
        if(added>=0&&s.minTimeStep>0)d.meta.addedMassPercent=Math.max(0,...th.rows.map(r=>r[added]));
        // /TH/RWALL DEF writes six unnamed columns per wall: the accumulated normal impulse
        // X, Y, Z and tangential impulse X, Y, Z (N·s). The force is its time derivative,
        // taken as a central difference of the saved samples.
        const derivative=values=>values.map((_,i)=>{const a=Math.max(0,i-1),b=Math.min(values.length-1,i+1);return time[b]>time[a]?(values[b]-values[a])/(time[b]-time[a]):0;});
        d.meta.walls.forEach((wall,k)=>{
          const columns=th.head.map((h,i)=>h.startsWith(`rigid wall forces ${wall.id} `)?i:-1).filter(i=>i>=0);
          if(columns.length<3)return;
          const normal=th.rows.map(r=>Math.hypot(r[columns[0]],r[columns[1]],r[columns[2]])*unit);
          history[`wall${k+1}`]={label:`刚性墙 ${k+1} 法向力`,unit:'N',x:time,y:derivative(normal)};
          history[`wallImpulse${k+1}`]={label:`刚性墙 ${k+1} 法向冲量`,unit:'N·s',x:time,y:normal};
          if(columns.length>=6&&wall.friction>0)history[`wallFriction${k+1}`]={label:`刚性墙 ${k+1} 摩擦力`,unit:'N',x:time,
            y:derivative(th.rows.map(r=>Math.hypot(r[columns[3]],r[columns[4]],r[columns[5]])*unit))};
        });
        d.meta.historyColumns=th.head.slice(0,80);
      }
    }catch{/* Time histories are optional; the frames remain valid. */}
    const reached=frames.at(-1)>=s.explicitEndTime-0.5*d.animDt;
    const completed=normal&&reached&&!interruption&&!frameError;
    const message=interruption?.message||frameError?.message||(!normal?'OpenCourant Engine 未正常结束，只保留已经输出的结果帧。'
      :!reached?`OpenCourant Engine 在 t = ${frames.at(-1).toPrecision(4)} s 提前停止（通常为单元严重畸变），只保留此前结果帧。`:null);
    const engine=engineOut.match(/TOTAL NUMBER OF CYCLES\s*:\s*(\d+)/i);
    d.meta.cycles=engine?Number(engine[1]):null;
    const error=engineOut.match(/ENERGY ERROR\s*:?\s*([-+0-9.Ee]+)\s*%/i)?.[1];
    d.meta.energyError=error!=null?Number(error):null;
    await Promise.all(['dyn_0000.rad','dyn_0001.rad','dyn_0000.out'].map(name=>fs.copyFile(path.join(work,name),path.join(dir,name)).catch(()=>{})));
    return {solver:'OpenCourant 20261011 显式动力学',cpuThreads:threads,meta:d.meta,history,
      termination:completed?null:{code:interruption?.code||'solver-stop',message}};
  }finally{
    log.end();
    await fs.unlink(runtime).catch(()=>{});
    if(!process.env.TENSORA_KEEP_DYNAMICS_WORK)await fs.rm(work,{recursive:true,force:true,maxRetries:3}).catch(()=>{});
  }
}

module.exports={buildDecks,run,geometry,materialCard};
