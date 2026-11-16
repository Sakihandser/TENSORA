'use strict';
// Explicit transient fluid–structure interaction with OpenCourant (OpenRadioss
// continuation): the fluid is discretized by SPH particles (/SPHCEL, /PROP/SPH,
// /MAT/HYD_VISC + /EOS/POLYNOMIAL), the structure by Lagrangian TET4 elements
// (/MAT/ELAST), coupled by node-to-surface contact (/INTER/TYPE7); container walls
// are fixed shell segments. TENSORA only places the particles (one per fluid
// tetrahedron, mass rho*V), writes the keyword decks, launches the unmodified
// Starter / Engine / anim_to_vtk executables and reads their output.
const fs=require('node:fs/promises');
const {existsSync}=require('node:fs');
const path=require('node:path');
const {f20}=require('./blast3d-deck');
const {assembleLoads,tetData}=require('./solid3d');
const {readVtk,environment,execute,OPENCOURANT}=require('./blast3d-runner');

function openCourantAvailable(){
  return ['exec/starter_win64.exe','exec/engine_win64.exe','exec/anim_to_vtk_win64.exe','exec/vcruntime140.dll',
    'hm_cfg_files/config/CFG','hm_cfg_files/messages',
    'extlib/hm_reader/win64/hm_reader_win64.dll',
    'extlib/intelOneAPI_runtime/win64/libiomp5md.dll',
    'extlib/intelOneAPI_runtime/win64/mkl_intel_thread.2.dll',
    'extlib/intelOneAPI_runtime/win64/mkl_core.2.dll']
    .every(file=>existsSync(path.join(OPENCOURANT,file)));
}

async function mapProjectDrive(log){
  if(!process.env.SystemRoot)return null;
  const subst=path.join(process.env.SystemRoot,'System32','subst.exe');
  if(!existsSync(subst))return null;
  for(const letter of 'ZYXWVUTSRQPONMLKJIHGFED'){
    const drive=letter+':';
    const root=drive+'\\';
    if(existsSync(root))continue;
    const options={cwd:__dirname,timeoutMs:5000,log};
    if(await execute(subst,[drive,__dirname],options)===0){
      return {root,release:()=>execute(subst,[drive,'/D'],options)};
    }
  }
  return null;
}

const LIMITS={particles:250000,tets:600000,frames:201,endTime:10};
const i10=value=>{if(!Number.isSafeInteger(value))throw Error('卡片编号无效');return String(value).padStart(10);};
const title=text=>String(text).replace(/[^\x20-\x7e]/g,'_').slice(0,100);
const finite=(v,name,{min=-Infinity,max=Infinity,positive=false}={})=>{
  const n=Number(v);
  if(!Number.isFinite(n)||n<min||n>max||(positive&&!(n>0)))throw Error(`${name} 输入无效。`);
  return n;
};
const vector=(v,name)=>{
  if(!Array.isArray(v)||v.length!==3)throw Error(`${name} 需要三个分量。`);
  return v.map((x,i)=>finite(x,`${name} ${'XYZ'[i]}`));
};
const faceKey=f=>[...f].sort((a,b)=>a-b).join(',');
const sub=(a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]];
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
const PARTICLE_FIELDS=['px','py','pz','vx','vy','vz','vmag','pressure','density'];
const MESH_FIELDS=['ux','uy','uz','umag','vx','vy','vz','vmag','sxx','syy','szz','sxy','syz','sxz','vm'];

function normalizeSettings(raw={},fluid){
  if(fluid?.model!=='incompressible')throw Error('SPH 显式流固耦合只支持液体（不可压缩流体卡）。气体请使用 SU2 路径。');
  const s={
    endTime:finite(raw.endTime??0.5,'计算时长',{positive:true,max:LIMITS.endTime}),
    frames:Math.round(finite(raw.frames??41,'保存帧数',{min:2,max:LIMITS.frames})),
    timeStepScale:finite(raw.timeStepScale??0.6,'时间步安全系数',{positive:true,max:0.9}),
    threads:Math.round(finite(raw.threads??4,'CPU 线程数',{min:1,max:64})),
    initialVelocity:vector(raw.initialVelocity??[0,0,0],'流体初速度'),
    gravity:vector(raw.gravity??[0,0,-9.81],'重力加速度'),
    soundSpeed:finite(raw.soundSpeed??0,'数值声速',{min:0}),
    // Structural mass scaling: 'auto' matches the particle time step, 'off', or a given minimum Δt.
    massScaling:['auto','off','custom'].includes(raw.massScaling)?raw.massScaling:'auto',
    minTimeStep:finite(raw.minTimeStep??0,'最小时间步',{min:0}),
    volumeRoles:raw.volumeRoles&&typeof raw.volumeRoles==='object'?raw.volumeRoles:{},
    boundaries:raw.boundaries&&typeof raw.boundaries==='object'?raw.boundaries:{}
  };
  for(const role of Object.values(s.volumeRoles))if(!['fluid','solid','void'].includes(role))throw Error('体域角色无效。');
  return s;
}

// Builds Starter / Engine decks from the shared 3D mesh.
function buildSphDecks(solid,rawSettings,fluid){
  const mesh=solid?.mesh,solidSettings=solid?.settings||{};
  if(!Array.isArray(mesh?.nodes)||!Array.isArray(mesh?.tets)||!mesh.tets.length||!Array.isArray(mesh.surfaces))throw Error('请先在三维“计算”页生成四面体网格。');
  if(mesh.tets.length>LIMITS.tets)throw Error(`SPH 显式流固耦合最多支持 ${LIMITS.tets.toLocaleString()} 个四面体。`);
  const s=normalizeSettings(rawSettings,fluid);
  const roleOf=volume=>s.volumeRoles[String(volume)]||'solid';
  const library=new Map((solidSettings.materials||[]).map(m=>[String(m.id),m]));
  const tetRole=mesh.tets.map((_,i)=>roleOf(mesh.tetVolumes[i]));
  if(!tetRole.includes('fluid'))throw Error('请至少把一个体域设为“流体”。');
  if(!tetRole.includes('solid'))throw Error('请至少把一个体域设为“结构”。');
  const nNodes=mesh.nodes.length;
  // SPH cells use their node IDs as element IDs: keep them above every TET4 / SH3N ID.
  const particleBase=nNodes+4*mesh.tets.length;
  // ---- particles: one per fluid tetrahedron at its centroid, mass rho*V
  const rho=fluid.density;
  const particles=[];let fluidVolume=0,maxHeight=-Infinity,minHeight=Infinity;
  const g=s.gravity,gLen=Math.hypot(...g);
  mesh.tets.forEach((tet,i)=>{
    if(tetRole[i]!=='fluid')return;
    const pts=tet.map(n=>mesh.nodes[n]),v=Math.abs(tetData(pts).volume);
    const c=[0,1,2].map(d=>(pts[0][d]+pts[1][d]+pts[2][d]+pts[3][d])/4);
    particles.push({id:particleBase+particles.length+1,position:c,mass:rho*v});
    fluidVolume+=v;
    if(gLen>0){const h=-dot(c,g)/gLen;maxHeight=Math.max(maxHeight,h);minHeight=Math.min(minHeight,h);}
  });
  if(particles.length>LIMITS.particles)throw Error(`流体粒子数 ${particles.length.toLocaleString()} 超过上限 ${LIMITS.particles.toLocaleString()}，请增大网格尺寸。`);
  const spacing=Math.cbrt(fluidVolume/particles.length);
  // Weakly compressible fluid: K = rho c^2 with a numerical sound speed at least
  // ten times the characteristic speed (initial speed, free fall over the fluid height).
  const height=gLen>0?Math.max(0,maxHeight-minHeight):0;
  const characteristic=Math.max(Math.hypot(...s.initialVelocity),Math.sqrt(2*gLen*height),0.1);
  const physical=fluid.bulkModulus?Math.sqrt(fluid.bulkModulus/rho):fluid.soundSpeed||1480;
  const sound=s.soundSpeed>0?s.soundSpeed:Math.min(physical,Math.max(10*characteristic,20));
  const bulk=rho*sound*sound;
  // ---- structure
  const solidTets=[];mesh.tets.forEach((_,i)=>{if(tetRole[i]==='solid')solidTets.push(i);});
  const solidNode=new Uint8Array(nNodes);for(const i of solidTets)for(const n of mesh.tets[i])solidNode[n]=1;
  const materials=new Map();
  for(const i of solidTets){
    const id=String(solidSettings.volumeMaterials?.[mesh.tetVolumes[i]]??'');
    if(materials.has(id))continue;
    const m=library.get(id);
    if(!m)throw Error('结构体域尚未指定材料，请在三维计算页为结构体域分配材料。');
    materials.set(id,{id,name:m.name,E:finite(Number(m.elasticModulus)*1e9,`${m.name} 弹性模量`,{positive:true}),
      nu:finite(m.poissonRatio,`${m.name} 泊松比`,{min:-0.99,max:0.4999}),density:finite(m.density,`${m.name} 密度`,{positive:true}),matId:materials.size+1});
  }
  // Estimated explicit step of the structure: tetrahedron height over the dilatational
  // wave speed (the Engine computes its own; this only chooses the mass-scaling target).
  let structureStep=Infinity;
  for(const i of solidTets){
    const pts=mesh.tets[i].map(n=>mesh.nodes[n]),volume=Math.abs(tetData(pts).volume);
    let maxArea=0;
    for(let k=0;k<4;k++){const f=pts.filter((_,j)=>j!==k);maxArea=Math.max(maxArea,Math.hypot(...cross(sub(f[1],f[0]),sub(f[2],f[0])))/2);}
    const m=materials.get(String(solidSettings.volumeMaterials?.[mesh.tetVolumes[i]]??''));
    const wave=Math.sqrt(m.E*(1-m.nu)/(m.density*(1+m.nu)*(1-2*m.nu)));
    structureStep=Math.min(structureStep,s.timeStepScale*(3*volume/maxArea)/wave);
  }
  // Nodal mass scaling (OpenCourant /DT/NODA/CST dtmin). Automatic scaling is used only
  // when the structure step is below 1/20 of the particle step (stiff metals); softer
  // structures keep their true inertia. Gravity then acts on the fluid only, so the added
  // mass carries no fictitious weight; the result reports the inertia factor.
  const particleStep=s.timeStepScale*spacing/sound;
  const minTimeStep=s.massScaling==='off'?0:s.massScaling==='custom'?s.minTimeStep
    :structureStep<0.05*particleStep?0.5*particleStep:0;
  if(s.massScaling==='custom'&&!(minTimeStep>0))throw Error('请填写大于零的最小时间步。');
  const inertiaFactor=minTimeStep>structureStep?(minTimeStep/structureStep)**2:1;
  const conditions=(solidSettings.conditions||[]).filter(bc=>/^fixed/.test(bc.type));
  const {fixed}=assembleLoads(mesh,conditions,()=>({material:null}),null,{requireLoad:false,requireRestraint:false});
  let restrained=0;for(let n=0;n<nNodes;n++)if(solidNode[n]&&(fixed[n*3]||fixed[n*3+1]||fixed[n*3+2]))restrained++;
  if(!restrained)throw Error('结构需要固定约束：请在三维计算页为结构设置约束。');
  // ---- faces: structure contact surface and rigid container walls
  const owners=new Map();
  mesh.tets.forEach((tet,i)=>{for(let k=0;k<4;k++){const f=tet.filter((_,j)=>j!==k),key=faceKey(f);
    const e=owners.get(key);if(e)e.push({i,opp:tet[k]});else owners.set(key,[{i,opp:tet[k],f}]);}});
  const openFaces=new Set();
  for(const surface of mesh.surfaces){
    const kind=s.boundaries[`S${surface.id}`]?.kind;
    if(kind==='inlet')throw Error('SPH 显式路径不支持速度入口；请用“流体初速度”给流体赋初速，或改用 SU2 路径。');
    if(kind==='outlet'||kind==='farfield')for(const tri of surface.triangles)openFaces.add(faceKey(tri));
  }
  const structureSegments=[],wallTriangles=[];
  for(const list of owners.values()){
    const {f,i,opp}=list[0];
    const roles=list.map(e=>tetRole[e.i]);
    const outward=(face,o)=>{const [a,b,c]=face.map(n=>mesh.nodes[n]);return dot(cross(sub(b,a),sub(c,a)),sub(mesh.nodes[o],a))>0?[face[0],face[2],face[1]]:[...face];};
    if(roles.includes('solid')&&!(roles.length===2&&roles[0]==='solid'&&roles[1]==='solid')){
      const k=roles.indexOf('solid');
      structureSegments.push(outward(list[k].f||f,list[k].opp));
    }else if(list.length===1&&roles[0]!=='solid'&&!openFaces.has(faceKey(f))){
      wallTriangles.push(outward(f,opp).reverse());  // normal into the domain
    }
  }
  if(!structureSegments.length)throw Error('没有找到结构表面。');
  // ---- Starter deck
  const S=['#RADIOSS STARTER','# TENSORA SPH fluid-structure deck for OpenCourant','/BEGIN','tensora_fsi_sph','      2026         0',
    '                  kg                   m                   s','                  kg                   m                   s',
    '/TITLE','TENSORA SPH fluid-structure interaction'];
  const wallNodeId=new Map();
  for(const tri of wallTriangles)for(const n of tri)if(!wallNodeId.has(n))wallNodeId.set(n,particleBase+particles.length+wallNodeId.size+1);
  S.push('/NODE','#  node_ID                 Xc                  Yc                  Zc');
  for(let n=0;n<nNodes;n++)if(solidNode[n]){const [x,y,z]=mesh.nodes[n];S.push(i10(n+1)+f20(x)+f20(y)+f20(z));}
  for(const p of particles)S.push(i10(p.id)+f20(p.position[0])+f20(p.position[1])+f20(p.position[2]));
  for(const [n,id] of wallNodeId){const [x,y,z]=mesh.nodes[n];S.push(i10(id)+f20(x)+f20(y)+f20(z));}
  for(const m of materials.values())S.push(`/MAT/ELAST/${m.matId}`,title(m.name),'#              RHO_I',f20(m.density),'#                  E                  nu',f20(m.E)+f20(m.nu));
  const fluidMat=materials.size+1,wallMat=materials.size+2;
  S.push(`/MAT/HYD_VISC/${fluidMat}`,title(fluid.name),'#              RHO_I',f20(rho),'#                 Nu                Pmin',f20(fluid.viscosity/rho)+f20(-0.01*bulk));
  S.push(`/EOS/POLYNOMIAL/${fluidMat}`,'weakly compressible liquid','#                 C0                  C1                  C2                  C3',f20(0)+f20(bulk)+f20(0)+f20(0),
    '#                 C4                  C5                  E0                 Psh               RHO_0',f20(0)+f20(0)+f20(0)+f20(0)+f20(0));
  S.push(`/MAT/ELAST/${wallMat}`,'rigid container wall (fixed nodes)','#              RHO_I',f20(1000),'#                  E                  nu',f20(1e6)+f20(0.3));
  S.push('/PROP/SOLID/1','tet4 structure','#   Isolid    Ismstr      Iale     Icpre  Itetra10     Inpts   Itetra4    Iframe                  Dn',
    i10(0)+i10(0)+i10(0)+i10(0)+i10(0)+i10(0)+i10(0)+i10(0)+f20(0),'#                 qa                  qb                   h              Lambda                  Mu',f20(0)+f20(0)+f20(0)+f20(0)+f20(0),
    '#         deltaT_min            vdef_min            vdef_max             ASP_max             COL_min',f20(0)+f20(0)+f20(0)+f20(0)+f20(0),'#     Ndir sphpartID  Icontrol',i10(0)+i10(0)+i10(0));
  S.push('/PROP/SPH/2','fluid particles','#                 mp                beta               alpha            alpha_cs   skew_ID      h_1D',
    f20(rho*fluidVolume/particles.length)+f20(0)+f20(0)+f20(0)+i10(0)+i10(0),
    '#    Order                   h             Xi_Stab                          hmin                hmax',i10(0)+f20(1.2*spacing)+f20(0)+' '.repeat(10)+f20(0)+f20(0),
    '#               hcst',f20(0));
  S.push('/PROP/SHELL/3','container wall','#   Ishell    Ismstr     Ish3n    Idrill    Ipinch                  P_Thick_Fail',i10(0)+i10(0)+i10(0)+i10(0)+i10(0)+' '.repeat(10)+f20(0),
    '#                 Hm                  Hf                  Hr                  Dm                  Dn',f20(0)+f20(0)+f20(0)+f20(0)+f20(0),
    '#        N                         Thick              Ashear              Ithick     Iplas      Ipos',i10(1)+' '.repeat(10)+f20(spacing)+f20(0)+' '.repeat(10)+i10(0)+i10(0)+i10(0));
  // Parts: one per structural material, the particles, the walls.
  const partOfMaterial=new Map();let partId=0;
  for(const m of materials.values()){
    const id=++partId;partOfMaterial.set(m.id,id);
    S.push(`/PART/${id}`,title(`structure ${m.name}`),'#  prop_ID    mat_ID subset_ID',i10(1)+i10(m.matId)+i10(0),`/TETRA4/${id}`);
    for(const i of solidTets){
      if(String(solidSettings.volumeMaterials?.[mesh.tetVolumes[i]]??'')!==m.id)continue;
      const nodes=[...mesh.tets[i]];
      if(tetData(nodes.map(n=>mesh.nodes[n])).orientation<0)[nodes[1],nodes[2]]=[nodes[2],nodes[1]];
      S.push(i10(i+1)+nodes.map(n=>i10(n+1)).join(''));
    }
  }
  const fluidPart=++partId;
  S.push(`/PART/${fluidPart}`,title(`fluid ${fluid.name}`),'#  prop_ID    mat_ID subset_ID',i10(2)+i10(fluidMat)+i10(0),`/SPHCEL/${fluidPart}`,'#  node_ID      Flag                MASS');
  for(const p of particles)S.push(i10(p.id)+i10(0)+f20(p.mass));
  const wallPart=wallTriangles.length?++partId:0;
  if(wallPart){
    S.push(`/PART/${wallPart}`,'container walls','#  prop_ID    mat_ID subset_ID',i10(3)+i10(wallMat)+i10(0),`/SH3N/${wallPart}`);
    wallTriangles.forEach((t,k)=>S.push(i10(mesh.tets.length+k+1)+t.map(n=>i10(wallNodeId.get(n))).join('')));
  }
  let group=0,card=0;
  const pushGroup=(name,ids)=>{const id=++group;S.push(`/GRNOD/NODE/${id}`,title(name));for(let k=0;k<ids.length;k+=10)S.push(ids.slice(k,k+10).map(i10).join(''));return id;};
  const patterns=new Map();
  for(let n=0;n<nNodes;n++){
    if(!solidNode[n])continue;
    const code=`${fixed[n*3]}${fixed[n*3+1]}${fixed[n*3+2]}`;
    if(code==='000')continue;
    if(!patterns.has(code))patterns.set(code,[]);
    patterns.get(code).push(n+1);
  }
  for(const [code,ids] of patterns){const gid=pushGroup(`fixed ${code}`,ids);S.push(`/BCS/${++card}`,`fixed ${code}`,'#  Tra rot   skew_ID  grnod_ID',`   ${code} 000${i10(0)}${i10(gid)}`);}
  if(wallPart){const gid=pushGroup('container wall nodes',[...wallNodeId.values()]);S.push(`/BCS/${++card}`,'container walls','#  Tra rot   skew_ID  grnod_ID',`   111 111${i10(0)}${i10(gid)}`);}
  const particleGroup=pushGroup('fluid particles',particles.map(p=>p.id));
  if(s.initialVelocity.some(v=>v!==0))S.push(`/INIVEL/TRA/${++card}`,'fluid initial velocity','#                 Vx                  Vy                  Vz   Gnod_id   Skew_id',
    f20(s.initialVelocity[0])+f20(s.initialVelocity[1])+f20(s.initialVelocity[2])+i10(particleGroup)+i10(0),'#             tstart   sens_ID',f20(0)+i10(0));
  if(gLen>0){
    const moving=minTimeStep>0?particleGroup
      :pushGroup('gravity nodes',[...[...solidNode.keys()].filter(n=>solidNode[n]).map(n=>n+1),...particles.map(p=>p.id)]);
    const funct=++card;
    S.push(`/FUNCT/${funct}`,'constant gravity','#                  X                   Y',f20(0)+f20(1),f20(s.endTime*10)+f20(1));
    g.forEach((value,d)=>{if(value!==0)S.push(`/GRAV/${++card}`,`gravity ${'XYZ'[d]}`,
      '#funct_IDT       DIR   skew_ID sensor_ID  grnod_ID                      Ascale_x            Fscale_Y',
      i10(funct)+'XYZ'[d].padStart(10)+i10(0)+i10(0)+i10(moving)+' '.repeat(10)+f20(1)+f20(value));});
  }
  // Node-to-surface contact with constant penalty stiffness matching the fluid
  // compressibility (K h); the gap is a quarter of the particle spacing.
  const stiffness=bulk*spacing,gap=0.25*spacing;
  const contact=(id,name,surfaceId)=>S.push(`/INTER/TYPE7/${id}`,title(name),
    '# grnod_id   surf_id      Istf      Ithe      Igap                Ibag      Idel     Icurv      Iadm',
    i10(particleGroup)+i10(surfaceId)+i10(1)+i10(0)+i10(0)+' '.repeat(10)+i10(0)+i10(0)+i10(0)+i10(0),
    '#          Fscalegap             Gap_max             Fpenmax                         Itied      Ists',f20(0)+f20(0)+f20(0)+' '.repeat(20)+i10(0)+i10(0),
    '#              Stmin               Stmax   Percent_mesh_size               dtmin  Irem_gap   Irem_i2',f20(0)+f20(0)+f20(0)+f20(0)+i10(0)+i10(0),
    '#              Stfac                Fric              GAPmin              Tstart               Tstop',f20(stiffness)+f20(0)+f20(gap)+f20(0)+f20(0),
    '#      IBC                        Inacti               VIS_S               VIS_F              Bumult',' '.repeat(30)+i10(5)+f20(0)+f20(0)+f20(0),
    '#    Ifric    Ifiltr               Xfreq     Iform   sens_ID   fct_IDF             AscaleF   fric_ID',i10(0)+i10(0)+f20(0)+i10(0)+i10(0)+i10(0)+f20(0)+i10(0));
  const structureSurface=++card;
  S.push(`/SURF/SEG/${structureSurface}`,'structure surface');
  structureSegments.forEach((seg,k)=>S.push(i10(k+1)+i10(seg[0]+1)+i10(seg[1]+1)+i10(seg[2]+1)+i10(seg[2]+1)));
  contact(++card,'fluid particles to structure',structureSurface);
  if(wallPart){
    const wallSurface=++card;
    S.push(`/SURF/SEG/${wallSurface}`,'container walls');
    wallTriangles.forEach((t,k)=>S.push(i10(k+1)+t.map(n=>i10(wallNodeId.get(n))).join('')+i10(wallNodeId.get(t[2]))));
    contact(++card,'fluid particles to container',wallSurface);
  }
  S.push('/END');
  // ---- Engine deck
  const animDt=s.endTime/(s.frames-1);
  // Nodal mass scaling (OpenCourant /DT/NODA/CST dtmin): stiff structures would otherwise
  // force a time step far below the particle step. Added mass is reported with the results.
  const E=['/RUN/tensora_fsi_sph/1',f20(s.endTime+animDt*0.5).trim(),'/ANIM/DT',`0 ${animDt}`,
    '/ANIM/VECT/DISP','/ANIM/VECT/VEL','/ANIM/BRICK/TENS/STRESS','/ANIM/ELEM/VONM','/ANIM/ELEM/P','/ANIM/ELEM/DENS',
    '/DT/NODA/CST/0',`${s.timeStepScale} ${minTimeStep}`,'/TFILE/0',String(Math.max(animDt/20,s.endTime/2000)),'/PRINT/-500','/PARITH/ON','/END'];
  const meta={particles:particles.length,spacing,smoothingLength:1.2*spacing,fluidVolume,fluidMass:rho*fluidVolume,soundSpeed:sound,physicalSoundSpeed:physical,
    bulkModulus:bulk,characteristicSpeed:characteristic,contactStiffness:stiffness,gap,structureTets:solidTets.length,structureNodes:solidNode.reduce((a,b)=>a+b,0),
    structureSegments:structureSegments.length,wallTriangles:wallTriangles.length,restrainedNodes:restrained,animDt,
    particleTimeStep:particleStep,structureTimeStep:structureStep,minTimeStep,massScaling:s.massScaling,inertiaFactor,
    structureGravity:gLen>0&&!(minTimeStep>0),
    structureMass:[...materials.values()].reduce((sum,m)=>sum+m.density*solidTets.filter(i=>String(solidSettings.volumeMaterials?.[mesh.tetVolumes[i]]??'')===m.id)
      .reduce((v,i)=>v+Math.abs(tetData(mesh.tets[i].map(n=>mesh.nodes[n])).volume),0),0),
    materials:[...materials.values()].map(({matId,...m})=>m),fluid,initialVelocity:s.initialVelocity,gravity:s.gravity};
  return {starter:S.join('\n')+'\n',engine:E.join('\n')+'\n',settings:s,meta,particles,particleBase,solidNode,solidTets};
}

// One animation frame -> structural nodal fields + particle arrays.
function sphFrame(vtk,decks,mesh){
  const n=mesh.nodes.length,P=decks.particles.length;
  const mesh_=Object.fromEntries(MESH_FIELDS.map(k=>[k,new Float32Array(n).fill(NaN)]));
  const part=Object.fromEntries(PARTICLE_FIELDS.map(k=>[k,new Float32Array(P).fill(NaN)]));
  const ids=vtk.pointData.NODE_ID?.values;
  if(!ids)throw Error('anim_to_vtk 输出缺少 NODE_ID。');
  const disp=vtk.pointData.Displacement?.values,vel=vtk.pointData.Velocity?.values,pts=vtk.points;
  for(let p=0;p<ids.length;p++){
    const id=ids[p];
    if(id>=1&&id<=n){
      const i=id-1;
      if(disp){mesh_.ux[i]=disp[p*3];mesh_.uy[i]=disp[p*3+1];mesh_.uz[i]=disp[p*3+2];mesh_.umag[i]=Math.hypot(disp[p*3],disp[p*3+1],disp[p*3+2]);}
      if(vel){mesh_.vx[i]=vel[p*3];mesh_.vy[i]=vel[p*3+1];mesh_.vz[i]=vel[p*3+2];mesh_.vmag[i]=Math.hypot(vel[p*3],vel[p*3+1],vel[p*3+2]);}
    }else if(id>decks.particleBase&&id<=decks.particleBase+P){
      const k=id-decks.particleBase-1;
      part.px[k]=pts[p*3];part.py[k]=pts[p*3+1];part.pz[k]=pts[p*3+2];
      if(vel){part.vx[k]=vel[p*3];part.vy[k]=vel[p*3+1];part.vz[k]=vel[p*3+2];part.vmag[k]=Math.hypot(vel[p*3],vel[p*3+1],vel[p*3+2]);}
    }
  }
  // Cells: TET4 stresses (volume-weighted nodal averages) and SPH vertex cells.
  const cells=vtk.cells;
  const stress=vtk.cellData['3DELEM_Stress'],sphP=vtk.cellData.SPHELEM_Pressure,sphRho=vtk.cellData.SPHELEM_Density;
  const order=[0,4,8,1,5,2],keys=['sxx','syy','szz','sxy','syz','sxz'];
  const sums=Object.fromEntries(keys.map(k=>[k,new Float64Array(n)])),weight=new Float64Array(n);
  let c=0,offset=0;
  while(cells&&offset<cells.length){
    const count=cells[offset];
    if(count===4&&stress){
      const nodes=[...cells.subarray(offset+1,offset+5)].map(q=>ids[q]-1);
      if(nodes.every(i=>i>=0&&i<n)){
        const w=Math.abs(tetData(nodes.map(i=>mesh.nodes[i])).volume);
        for(const i of nodes){weight[i]+=w;keys.forEach((k,j)=>{sums[k][i]+=w*stress.values[c*9+order[j]];});}
      }
    }else if(count===1){
      const k=ids[cells[offset+1]]-decks.particleBase-1;
      if(k>=0&&k<P){if(sphP)part.pressure[k]=sphP.values[c];if(sphRho)part.density[k]=sphRho.values[c];}
    }
    offset+=count+1;c++;
  }
  for(let i=0;i<n;i++){
    if(!(weight[i]>0))continue;
    for(const k of keys)mesh_[k][i]=sums[k][i]/weight[i];
    const [a,b,d,xy,yz,xz]=keys.map(k=>mesh_[k][i]);
    mesh_.vm[i]=Math.sqrt(((a-b)**2+(b-d)**2+(d-a)**2)/2+3*(xy*xy+yz*yz+xz*xz));
  }
  return {mesh:mesh_,particles:part};
}

const ENGINE_LINE=/NC=\s*(\d+)\s+T=\s*([-+0-9.Ee]+)\s+DT=\s*([-+0-9.Ee]+)/;

// Runs the SPH chain and writes frames in the FSI run folder `dir`.
async function runSph(payload,{dir,runId,log,signal,progress,timeoutMs}){
  const decks=buildSphDecks(payload.solid,payload.settings,payload.fluid);
  const s=decks.settings,mesh=payload.solid.mesh;
  const work=path.join(dir,'work');
  let driveAlias;
  try{
    await fs.mkdir(work);
    await Promise.all([fs.writeFile(path.join(work,'model_0000.rad'),decks.starter),fs.writeFile(path.join(work,'model_0001.rad'),decks.engine)]);
    let cwd=work,runtime=OPENCOURANT;
    const solverEnv=()=>({...environment(runtime,s.threads,cwd),TMP:cwd,TEMP:cwd,TMPDIR:cwd});
    let env=solverEnv();
    const exec=name=>path.join(runtime,'exec',name);
    progress('starter',0);
    log.write('=== OpenCourant Starter ===\n');
    const start=()=>execute(exec('starter_win64.exe'),['-i','model_0000.rad','-np','1','-nt',String(s.threads)],{cwd,env,signal,timeoutMs:20*60*1000,log});
    let starterCode=await start();
    // Older Intel Fortran scratch I/O requires paths representable in the system code page.
    if(starterCode===43){
      driveAlias=await mapProjectDrive(log);
      if(driveAlias){
        cwd=path.join(driveAlias.root,path.relative(__dirname,work));
        runtime=path.join(driveAlias.root,path.relative(__dirname,OPENCOURANT));
        env=solverEnv();
        log.write('Retrying OpenCourant Starter with a local Windows project drive alias.\n');
        starterCode=await start();
      }
    }
    if(starterCode!==0||!(await fs.readdir(work)).some(name=>/^model_0000_\d+\.rst$/i.test(name))){
      const out=await fs.readFile(path.join(work,'model_0000.out'),'latin1').catch(()=>'');
      await fs.writeFile(path.join(dir,'model_0000.out'),out);
      const errors=out.split(/\r?\n/).map((line,i,all)=>/ERROR ID/.test(line)?all.slice(i,i+4).join(' ').replace(/\s+/g,' ').trim():null).filter(Boolean).slice(0,3);
      throw Error(`OpenCourant Starter 未通过模型检查（退出码 ${starterCode}）。${errors.join('；')||'请查看任务日志 '+runId+'。'}`);
    }
    progress('engine',0);
    log.write('\n=== OpenCourant Engine ===\n');
    let last=0;
    const engineCode=await execute(exec('engine_win64.exe'),['-i','model_0001.rad','-nt',String(s.threads)],{cwd,env,signal,timeoutMs,log,onLine:line=>{
      const m=line.match(ENGINE_LINE);
      if(m){const t=Number(m[2]);if(Number.isFinite(t)&&t>=last){last=t;progress('engine',Math.min(1,t/s.endTime),{time:t,cycle:Number(m[1]),dt:Number(m[3])});}}
    }});
    const engineOut=await fs.readFile(path.join(work,'model_0001.out'),'latin1').catch(()=>'');
    await fs.writeFile(path.join(dir,'model_0001.out'),engineOut);
    const animations=(await fs.readdir(work)).filter(name=>/^modelA\d{3,}$/.test(name)).sort();
    if(!animations.length)throw Error(`OpenCourant Engine 没有输出动画帧（退出码 ${engineCode}）。请查看任务日志 ${runId}。`);
    progress('processing',0);
    const frames=[];
    for(let k=0;k<animations.length;k++){
      signal?.throwIfAborted();
      const vtkFile=path.join(work,animations[k]+'.vtk');
      const stream=(await fs.open(vtkFile,'w')).createWriteStream();
      let code;
      try{code=await execute(exec('anim_to_vtk_win64.exe'),[animations[k]],{cwd,env,signal,timeoutMs:10*60*1000,log:stream});}
      finally{await new Promise(resolve=>stream.end(resolve));}
      if(code!==0)throw Error('anim_to_vtk 转换失败：'+animations[k]);
      const vtk=await readVtk(vtkFile);
      await fs.rm(vtkFile,{force:true});
      // The run ends half an output interval past the end time; the Engine's final
      // animation written there is not one of the requested frames.
      if(Number.isFinite(vtk.time)&&vtk.time>s.endTime+0.25*decks.meta.animDt)continue;
      const {mesh:fields,particles}=sphFrame(vtk,decks,mesh);
      const stats={};
      const range=(key,values)=>{let lo=Infinity,hi=-Infinity;for(const v of values)if(Number.isFinite(v)){if(v<lo)lo=v;if(v>hi)hi=v;}return [lo,hi];};
      for(const key of MESH_FIELDS)stats[key]=range(key,fields[key]);
      const particleStats={};
      for(const key of PARTICLE_FIELDS)particleStats[key]=range(key,particles[key]);
      // Fluid quantities live on particles; the combined range drives the shared color scale.
      for(const key of ['vx','vy','vz','vmag']){const a=stats[key],b=particleStats[key];stats[key]=[Math.min(a[0],b[0]),Math.max(a[1],b[1])];}
      for(const key of ['pressure','density'])stats[key]=particleStats[key];
      const buffer=Buffer.concat([...MESH_FIELDS.map(key=>Buffer.from(fields[key].buffer)),...PARTICLE_FIELDS.map(key=>Buffer.from(particles[key].buffer))]);
      const index=frames.length;
      await fs.writeFile(path.join(dir,`frame-${String(index).padStart(4,'0')}.bin`),buffer);
      frames.push({index,time:Number.isFinite(vtk.time)?vtk.time:k*decks.meta.animDt,stats,particleStats});
      progress('processing',(k+1)/animations.length);
    }
    const normal=/NORMAL TERMINATION/i.test(engineOut);
    // Last cycle row: CYCLE TIME DT type id ERROR I-E K-E K-E-R EXT-WORK MAS.ERR TOTAL-MASS MASS-ADDED.
    const rows=engineOut.split(/\r?\n/).filter(line=>/^\s+\d+\s+[-+0-9.E]+\s+[-+0-9.E]+\s+\S+\s+\d+\s+-?[\d.]+%/.test(line));
    const lastRow=rows.at(-1)?.trim().split(/\s+/);
    const engineStats=lastRow?{cycles:Number(lastRow[0]),energyError:lastRow[5],totalMass:Number(lastRow[11]),addedMass:Number(lastRow[12])}:null;
    const reached=frames.at(-1).time>=s.endTime-0.5*decks.meta.animDt;
    const diverged=frames.findIndex(f=>['umag','vmag'].some(key=>!Number.isFinite(f.stats[key][1])||f.stats[key][1]>1e4));
    if(diverged===0)throw Error('OpenCourant 计算从第一帧起发散，请检查材料参数、网格质量和数值声速。');
    if(diverged>0)frames.splice(diverged);
    const completed=normal&&reached&&diverged<0;
    await Promise.all(['model_0000.rad','model_0001.rad','model_0000.out'].map(name=>fs.copyFile(path.join(work,name),path.join(dir,name)).catch(()=>{})));
    return {frames,completed,
      termination:completed?null:{code:engineCode,message:diverged>0?`第 ${diverged+1} 帧起数值发散，只保留此前 ${diverged} 帧。`
        :!normal?'OpenCourant Engine 未正常结束，只保留已经输出的帧。':`OpenCourant Engine 在 t = ${frames.at(-1).time.toPrecision(4)} s 提前停止，未达到设定时长。`},
      meta:{...decks.meta,engine:engineStats},settings:s,meshFields:MESH_FIELDS,particleFields:PARTICLE_FIELDS,particleCount:decks.particles.length};
  }finally{
    if(driveAlias)await driveAlias.release().catch(()=>{});
    if(!process.env.TENSORA_KEEP_FSI_WORK)await fs.rm(work,{recursive:true,force:true,maxRetries:3}).catch(()=>{});
  }
}

module.exports={buildSphDecks,runSph,openCourantAvailable,sphFrame,normalizeSettings,MESH_FIELDS,PARTICLE_FIELDS,LIMITS};
