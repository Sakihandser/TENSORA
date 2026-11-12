'use strict';
// Builds OpenCourant (OpenRadioss continuation) Starter/Engine decks for the
// 3D blast workspace. This file only translates TENSORA's shared 3D model
// (Gmsh TET4 mesh, CAD faces, volume materials and loads) into upstream
// keyword cards. Explicit integration, material laws (/MAT/ELAST, /MAT/JOHN_HOLM,
// /MAT/JOHNSON_HOLMQUIST_CONCRETE, /MAT/DPRAG1, /MAT/PLAS_JOHNS, /MAT/JWL), failure (/FAIL/TENSSTRAIN),
// detonation (/DFS/DETPOINT), surface pressure (/PLOAD), damping layers (/DAMP) and initial stress (/INIBRI) are
// solved entirely by the unmodified OpenCourant executables.
const {assembleLoads,tetData}=require('./solid3d');
const BlastMaterials=require('./blast-materials');
const Blast3dCards=require('./blast3d-cards');

const LIMITS={nodes:300_000,tets:1_200_000,frames:201,endTime:1};
const finite=(value,name)=>{const n=Number(value);if(!Number.isFinite(n))throw Error(`${name} 必须为有限数值`);return n;};
const positive=(value,name)=>{const n=finite(value,name);if(!(n>0))throw Error(`${name} 必须大于零`);return n;};
const f20=value=>{
  if(!Number.isFinite(value))throw Error('卡片数值无效');
  const text=value===0?'0':Math.abs(value)>=1e-3&&Math.abs(value)<1e9?String(Number(value.toPrecision(14))):value.toExponential(12);
  if(text.length>20)return value.toExponential(11).padStart(20);
  return text.padStart(20);
};
const i10=value=>{if(!Number.isSafeInteger(value))throw Error('卡片编号无效');return String(value).padStart(10);};
const title=text=>String(text).replace(/[^\x20-\x7e]/g,'_').slice(0,100);

// Volume roles. A Lagrangian air gap is not offered: under detonation loading the
// gas elements invert within a few cycles. Decoupled charges use the wall-pressure mode.
const ROLES=['rock','charge','void'];
function normalizeSettings(raw={}){
  const s={...raw};
  s.sourceMode=s.sourceMode==='jwl'?'jwl':'pressure';
  s.endTime=positive(s.endTime??2e-3,'计算时长');
  if(s.endTime>LIMITS.endTime)throw Error('计算时长不能超过 1 s。');
  s.frames=Math.round(finite(s.frames??41,'保存帧数'));
  if(s.frames<2||s.frames>LIMITS.frames)throw Error(`保存帧数须在 2–${LIMITS.frames} 之间。`);
  s.initialState=['prestress','sudden','none'].includes(s.initialState)?s.initialState:'prestress';
  s.volumeRoles=s.volumeRoles&&typeof s.volumeRoles==='object'?s.volumeRoles:{};
  for(const role of Object.values(s.volumeRoles))if(!ROLES.includes(role))throw Error('体域角色无效。');
  s.rockCards=s.rockCards&&typeof s.rockCards==='object'?s.rockCards:{};
  s.absorbingSurfaces=[...new Set((s.absorbingSurfaces||[]).map(String))];
  s.absorbingThickness=finite(s.absorbingThickness??0,'吸收层厚度');
  if(s.absorbingThickness<0)throw Error('吸收层厚度不能为负。');
  s.threads=Math.max(1,Math.min(32,Math.round(finite(s.threads??4,'线程数'))));
  s.timeStepScale=finite(s.timeStepScale??0.67,'时间步安全系数');
  if(!(s.timeStepScale>0&&s.timeStepScale<=0.9))throw Error('时间步安全系数须在 0–0.9 之间。');
  if(s.sourceMode==='pressure'){
    s.wallSurfaces=[...new Set((s.wallSurfaces||[]).map(String))];
    if(!s.wallSurfaces.length)throw Error('请选择承受爆炸压力的孔壁 CAD 面。');
    s.peakPressure=positive(s.peakPressure,'孔壁峰值压力');
    s.pulseDuration=positive(s.pulseDuration,'压力脉冲时长');
    s.pulseShape=['sine','exponential'].includes(s.pulseShape)?s.pulseShape:'sine';
    if(s.pulseShape==='exponential'){s.riseTime=positive(s.riseTime,'压力上升时间');if(s.riseTime>=s.pulseDuration)throw Error('上升时间须小于脉冲时长。');}
  }else{
    const e=s.explosive?.settings;
    if(!e)throw Error('请选择炸药。');
    for(const key of ['productDensity','productEnergy','detonationVelocity','jwlA','jwlB','jwlR1','jwlR2','jwlOmega'])positive(e[key],`炸药参数 ${key}`);
    s.detonationPoint=(s.detonationPoint||[]).map((v,i)=>finite(v,'起爆点坐标 '+'XYZ'[i]));
    if(s.detonationPoint.length&&s.detonationPoint.length!==3)throw Error('起爆点需要三个坐标。');
    s.detonationTime=finite(s.detonationTime??0,'起爆时间');
    if(s.detonationTime<0||s.detonationTime>=s.endTime)throw Error('起爆时间须在 0 与计算时长之间。');
  }
  return s;
}

function faceKey(a,b,c){return [a,b,c].sort((x,y)=>x-y).join(',');}
function faceOwners(tets,active){
  const owners=new Map();
  tets.forEach((tet,t)=>{
    if(!active[t])return;
    for(let k=0;k<4;k++){
      const face=tet.filter((_,j)=>j!==k),key=faceKey(...face);
      const list=owners.get(key);
      if(list)list.push({tet:t,opposite:tet[k]});else owners.set(key,[{tet:t,opposite:tet[k]}]);
    }
  });
  return owners;
}
const sub=(a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]];
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];

// Rock material card -> OpenCourant /MAT (+ optional /FAIL/TENSSTRAIN) lines.
// `card` is a Blast3dCards card linked to the base material in the blast library;
// without a link, the base material's 2D blast card (elastic or JH2) is used.
function rockCard(material,id,linkedCard){
  const rho=positive(material.density,`${material.name} 密度`);
  const E=positive(Number(material.elasticModulus)*1e9,`${material.name} 弹性模量`);
  const nu=finite(material.poissonRatio,`${material.name} 泊松比`);
  if(nu<=-1||nu>=.5)throw Error(`${material.name} 泊松比须在 -1 与 0.5 之间。`);
  let card;
  if(linkedCard)card=Blast3dCards.validate(linkedCard,material.name);
  else if(BlastMaterials.law(material,{rockModel:1})===6)throw Error(`${material.name}：Mohr–Coulomb 仅用于二维平面应变；三维请在爆破库为该材料关联 Drucker–Prager 等材料卡。`);
  else card=Blast3dCards.validate(Blast3dCards.fromBlastConstitutive(material.blastConstitutive),material.name);
  const name=title(material.name||'rock'),Gel=E/(2*(1+nu)),Kel=E/(3*(1-2*nu));
  const base={rho,E,nu,card,source:linkedCard?'library':'material'};
  let result;
  if(card.model==='elastic'){
    result={...base,law:'elastic',G:Gel,K:Kel,lines:[`/MAT/ELAST/${id}`,name,'#              RHO_I',f20(rho),'#                  E                  nu',f20(E)+f20(nu)]};
  }else if(card.model==='jh2'){
    const G=card.G>0?card.G:Gel;
    result={...base,law:'jh2',G,K:card.K1,K1:card.K1,K2:card.K2,K3:card.K3,lines:[`/MAT/JOHN_HOLM/${id}`,name,
      '#              RHO_I',f20(rho),'#                  G',f20(G),
      '#                  a                   b                   m                   n',f20(card.A)+f20(card.B)+f20(card.M)+f20(card.N),
      '#                  c                EPS0          SIGMA_FMAX',f20(card.C)+f20(card.rate0)+f20(card.maxStrength),
      '#                  T                 HEL                PHEL',f20(card.T)+f20(card.HEL)+f20(card.pHEL),
      '#                 D1                  D2',f20(card.D1)+f20(card.D2),
      '#                 K1                  K2                  K3                BETA',f20(card.K1)+f20(card.K2)+f20(card.K3)+f20(card.beta)]};
  }else if(card.model==='hjc'){
    const G=card.G>0?card.G:Gel;
    result={...base,law:'hjc',G,K:card.pc/card.muc,pc:card.pc,muc:card.muc,lines:[`/MAT/JOHNSON_HOLMQUIST_CONCRETE/${id}`,name,
      '#        Init. dens.',f20(rho),'#                  G',f20(G),
      '#                  A                   B                   N                  FC                   T',f20(card.A)+f20(card.B)+f20(card.N)+f20(card.fc)+f20(card.T),
      '#                  C                EPS0                FCUT               SFMAX               EFMIN',f20(card.C)+f20(card.rate0)+f20(0)+f20(card.maxStrength)+f20(card.efMin),
      '#                 PC                 MUC                  PL                 MUL',f20(card.pc)+f20(card.muc)+f20(card.pl)+f20(card.mul),
      '#                 K1                  K2                  K3',f20(card.K1)+f20(card.K2)+f20(card.K3),
      '#                 D1                  D2                IDEL             EPS_MAX             IFAILSO',f20(card.D1)+f20(card.D2)+' '.repeat(10)+i10(0)+f20(0)+' '.repeat(10)+i10(0),
      '#                 CT                POWT                  CC                POWC',f20(0)+f20(0)+f20(0)+f20(0)]};
  }else if(card.model==='jc'){
    // LAW2 Johnson-Cook (radioss2025 layout). Zero Pmin, EPS_p_max and SIG_max0 mean
    // "no cutoff" in the Starter; plastic strain above EPS_p_max deletes the element.
    result={...base,law:'jc',G:Gel,K:Kel,erodes:card.epsMax>0,lines:[`/MAT/PLAS_JOHNS/${id}`,name,
      '#              RHO_I',f20(rho),
      '#                  E                  Nu     Iflag    flagVP                Pmin',f20(E)+f20(nu)+i10(0)+i10(0)+f20(card.tension>0?-card.tension:0),
      '#                  a                   b                   n           EPS_p_max            SIG_max0',f20(card.a)+f20(card.b)+f20(card.n)+f20(card.epsMax)+f20(card.sigMax),
      '#                  c           EPS_DOT_0       ICC   Fsmooth               F_cut               Chard',f20(card.C)+f20(card.rate0)+i10(0)+i10(0)+f20(0)+f20(0),
      '#                  m              T_melt              rhoC_p                 T_r               T_max',f20(card.m)+f20(card.tMelt)+f20(card.rhoCp)+f20(card.tRef)+f20(0)]};
  }else{
    const dp=Blast3dCards.druckerPrager(card);
    result={...base,law:'dp',G:Gel,K:Kel,drucker:dp,lines:[`/MAT/DPRAG1/${id}`,name,'#              RHO_I',f20(rho),
      '#                  E                  Nu',f20(E)+f20(nu),
      '#                 A0                  A1                  A2                Amax',f20(dp.A0)+f20(dp.A1)+f20(dp.A2)+f20(0),
      '#              P_min',f20(dp.pMin)]};
  }
  if(card.failure.enabled){
    result.failure=true;
    result.lines.push(`/FAIL/TENSSTRAIN/${id}`,'#         EPSILON_T1          EPSILON_T2    FCT_ID          EPSILON_F1          EPSILON_F2     S_Flag',
      f20(card.failure.strainStart)+f20(card.failure.strainEnd)+i10(0)+f20(0)+f20(0)+i10(0),
      '#   FAILIP',i10(1));
  }
  return result;
}
function explosiveCard(explosive,id){
  const e=explosive.settings,rho=e.productDensity,D=e.detonationVelocity;
  const pcj=Number(explosive.cjPressure)>0?Number(explosive.cjPressure):rho*D*D/(Number(e.productGamma)>0?e.productGamma+1:3.7);
  const E0=e.productEnergy*rho; // OpenCourant JWL E0 is volumetric (J/m3); the library stores J/kg.
  return {law:'jwl',rho,pcj,E0,lines:[`/MAT/JWL/${id}`,title(explosive.name||'explosive'),'#              RHO_I',f20(rho),
    '#                  A                   B                  R1                  R2               OMEGA',f20(e.jwlA)+f20(e.jwlB)+f20(e.jwlR1)+f20(e.jwlR2)+f20(e.jwlOmega),
    '#                  D                P_CJ                  E0                Eadd   I_BFRAC      Qopt',f20(D)+f20(pcj)+f20(E0)+f20(0)+i10(0)+i10(0),
    '#                 P0                 PSH          Bunreacted',f20(0)+f20(0)+f20(0),
    '#             TSTART               TSTOP',f20(0)+f20(0)]};
}

const decksUseDamage=materials=>materials.some(m=>m.law==='jh2'||m.law==='hjc');
const decksUseFailure=materials=>materials.some(m=>m.failure);

// Compression mu that gives EOS pressure p: LAW1 P = K*mu; LAW79 (JH2)
// P = K1 mu + K2 mu^2 + K3 mu^3 in compression and K1 mu in tension.
function volumetricStrain(material,p){
  if(material.law==='jh2'){
    if(p<=0)return p/material.K1;
    let mu=p/material.K1;
    for(let k=0;k<50;k++){
      const f=material.K1*mu+material.K2*mu*mu+material.K3*mu**3-p,df=material.K1+2*material.K2*mu+3*material.K3*mu*mu;
      if(!(df>0))break;
      const step=f/df;mu-=step;
      if(Math.abs(step)<1e-15)break;
    }
    return mu;
  }
  return p/material.K;
}

// Elastic wave speeds cp and cs of the adjacent solid.
function waveSpeeds(material){
  if(material.role!=='rock')throw Error('吸收边界只能设在岩体外表面。');
  const {G,K}=material;
  return {p:Math.sqrt((K+4*G/3)/material.rho),s:Math.sqrt(G/material.rho)};
}
// Caughey absorbing layer (CALM, Semblat et al. 2011): Rayleigh mass-proportional
// damping applied by OpenCourant /DAMP to node bands next to the selected outer
// faces. alpha grows quadratically toward the boundary so the impedance changes
// gradually; alpha_max = 3*ln(1/R)*c_p/L gives a round-trip amplitude ratio R.
const LAYER_BANDS=8,LAYER_REFLECTION=0.01;
function absorbingLayer(mesh,surfaceIds,surfaceMap,active,partOfVolume,materials,used,thickness){
  const owners=faceOwners(mesh.tets,active);
  const boundary=new Set();
  let maxImpedanceSpeed=0,edgeSum=0,edgeCount=0;
  for(const id of surfaceIds){
    const face=surfaceMap.get(id);
    if(!face)throw Error(`未找到吸收边界面 ${id}。`);
    for(const tri of face.triangles){
      const list=owners.get(faceKey(...tri));
      if(!list)continue; // Face of a volume that does not take part in the run.
      if(list.length!==1)throw Error(`CAD 面 ${id} 位于两个参与计算的体域之间，不能设为吸收边界。`);
      const part=partOfVolume.get(String(mesh.tetVolumes[list[0].tet]));
      maxImpedanceSpeed=Math.max(maxImpedanceSpeed,waveSpeeds(materials.find(m=>m.id===part.materialId)).p);
      for(const n of tri)boundary.add(n);
      const [a,b,c]=tri.map(n=>mesh.nodes[n]);
      edgeSum+=Math.hypot(...sub(b,a))+Math.hypot(...sub(c,b))+Math.hypot(...sub(a,c));edgeCount+=3;
    }
  }
  if(!boundary.size)throw Error('所选吸收边界面不属于参与计算的岩体。');
  // Model extent for the default thickness.
  const lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];
  mesh.nodes.forEach((p,i)=>{if(used[i])for(let d=0;d<3;d++){lo[d]=Math.min(lo[d],p[d]);hi[d]=Math.max(hi[d],p[d]);}});
  const minExtent=Math.min(...hi.map((v,d)=>v-lo[d]));
  const meanEdge=edgeSum/edgeCount;
  const L=thickness>0?thickness:Math.max(2*meanEdge,0.1*minExtent);
  // Distance of each node to the nearest boundary node (grid hash, error <= one element).
  const cell=Math.max(L/2,1e-9),grid=new Map();
  const key=(x,y,z)=>`${x},${y},${z}`;
  for(const n of boundary){const p=mesh.nodes[n],k=key(...p.map(v=>Math.floor(v/cell)));if(!grid.has(k))grid.set(k,[]);grid.get(k).push(p);}
  const reach=Math.ceil(L/cell);
  const bands=Array.from({length:LAYER_BANDS},()=>[]);
  for(let i=0;i<mesh.nodes.length;i++){
    if(!used[i])continue;
    const p=mesh.nodes[i],c=p.map(v=>Math.floor(v/cell));
    let best=Infinity;
    for(let dx=-reach;dx<=reach;dx++)for(let dy=-reach;dy<=reach;dy++)for(let dz=-reach;dz<=reach;dz++){
      const list=grid.get(key(c[0]+dx,c[1]+dy,c[2]+dz));
      if(list)for(const q of list){const d=(p[0]-q[0])**2+(p[1]-q[1])**2+(p[2]-q[2])**2;if(d<best)best=d;}
    }
    const distance=Math.sqrt(best);
    if(distance>=L)continue;
    bands[Math.min(LAYER_BANDS-1,Math.floor(distance/L*LAYER_BANDS))].push(i+1);
  }
  const alphaMax=3*Math.log(1/LAYER_REFLECTION)*maxImpedanceSpeed/L;
  const groups=bands.map((ids,k)=>{
    const middle=(k+0.5)/LAYER_BANDS;               // normalized depth from the boundary
    return {ids,alpha:alphaMax*(1-middle)**2};
  }).filter(g=>g.ids.length);
  return {groups,thickness:L,alphaMax,nodes:groups.reduce((s,g)=>s+g.ids.length,0),waveSpeed:maxImpedanceSpeed,meanEdge};
}
function pulseFunction(s){
  const points=[];
  const n=64,T=s.pulseDuration;
  for(let i=0;i<=n;i++){
    const t=T*i/n;
    let y;
    if(s.pulseShape==='sine')y=Math.sin(Math.PI*t/T);
    else{
      // Rise linearly, then exponential decay to zero at T (smooth, positive pulse).
      const tr=s.riseTime;
      y=t<=tr?t/tr:Math.exp(-4*(t-tr)/(T-tr))*(1-(t-tr)/(T-tr));
    }
    points.push([t,Math.max(0,y)]);
  }
  points.push([T*1.0001,0],[Math.max(s.endTime*2,T*2),0]);
  return points;
}
function pushFunction(lines,id,name,points){
  lines.push(`/FUNCT/${id}`,title(name),'#                  X                   Y');
  for(const [x,y] of points)lines.push(f20(x)+f20(y));
}
function pushGroup(lines,id,name,ids){
  lines.push(`/GRNOD/NODE/${id}`,title(name));
  for(let i=0;i<ids.length;i+=10)lines.push(ids.slice(i,i+10).map(i10).join(''));
}

// Returns the starter and engine decks plus the bookkeeping needed to read results.
function buildDecks(solid,raw,{prestress=null}={}){
  const mesh=solid?.mesh,solidSettings=solid?.settings||{};
  if(!Array.isArray(mesh?.nodes)||!mesh.nodes.length||!Array.isArray(mesh.tets)||!mesh.tets.length)throw Error('请先生成三维网格。');
  if(mesh.nodes.length>LIMITS.nodes||mesh.tets.length>LIMITS.tets)throw Error(`三维爆破最多支持 ${LIMITS.nodes.toLocaleString()} 节点 / ${LIMITS.tets.toLocaleString()} 四面体。`);
  const s=normalizeSettings(raw);
  const library=new Map((solidSettings.materials||[]).map(m=>[String(m.id),m]));
  const roleOf=volume=>s.volumeRoles[volume]||'rock';
  const volumes=mesh.volumes.map(v=>String(v.id));
  if(s.sourceMode==='jwl'&&!volumes.some(v=>roleOf(v)==='charge'))throw Error('JWL 装药模式需要把至少一个体域设为“装药”。');
  if(s.sourceMode==='pressure'&&volumes.some(v=>roleOf(v)==='charge'))throw Error('孔壁压力模式下装药体域不参与计算，请设为“岩体”或“不参与”。');
  if(!volumes.some(v=>roleOf(v)==='rock'))throw Error('至少需要一个岩体体域。');

  // Parts: one per (volume role, material) so results can be grouped by volume.
  const parts=[],partOfVolume=new Map(),materials=[];
  const materialIdFor=new Map();
  for(const volume of volumes){
    const role=roleOf(volume);
    if(role==='void')continue;
    let key,make;
    if(role==='rock'){
      const material=library.get(String(solidSettings.volumeMaterials?.[volume]));
      if(!material)throw Error(`体域 ${volume} 尚未指定材料。`);
      key='rock:'+material.id;make=id=>rockCard(material,id,s.rockCards[material.id]);
    }else if(role==='charge'){key='charge';make=id=>explosiveCard(s.explosive,id);}
    else throw Error('体域角色无效。');
    if(!materialIdFor.has(key)){const id=materials.length+1;materials.push({id,key,role,...make(id)});materialIdFor.set(key,id);}
    const part={id:parts.length+1,volume,role,materialId:materialIdFor.get(key)};
    parts.push(part);partOfVolume.set(volume,part);
  }
  const active=mesh.tets.map((_,i)=>partOfVolume.has(String(mesh.tetVolumes[i])));
  const used=new Uint8Array(mesh.nodes.length);
  mesh.tets.forEach((tet,i)=>{if(active[i])for(const n of tet)used[n]=1;});
  const rockTet=mesh.tets.map((_,i)=>active[i]&&partOfVolume.get(String(mesh.tetVolumes[i])).role==='rock');

  // Constant external loads and restraints reuse the 3D workspace's own assembly.
  const conditions=solidSettings.conditions||[];
  const library3d={materials:[...library.values()],volumeMaterials:solidSettings.volumeMaterials||{}};
  let force=new Float64Array(mesh.nodes.length*3),fixed=new Uint8Array(mesh.nodes.length*3);
  const hasLoads=conditions.some(bc=>!['fixed','fixedNode','fixedGroup'].includes(bc.type));
  const resolveMaterial=index=>{
    const material=library.get(String(library3d.volumeMaterials[mesh.tetVolumes[index]]));
    return {material:material||{density:0}};
  };
  if(conditions.length){
    const assembled=assembleLoads(mesh,conditions,resolveMaterial,null,{requireLoad:false,requireRestraint:false});
    force=assembled.force;fixed=assembled.fixed;
  }
  const applyLoads=s.initialState!=='none'&&hasLoads;
  if(!applyLoads)force.fill(0);
  for(let i=0;i<mesh.nodes.length;i++)if(!used[i])for(let d=0;d<3;d++){force[i*3+d]=0;fixed[i*3+d]=0;}

  const S=[],E=[];
  S.push('#RADIOSS STARTER','# TENSORA 3D blast deck for OpenCourant','/BEGIN','tensora_blast3d','      2026         0',
    '                  kg                   m                   s','                  kg                   m                   s',
    '/TITLE','TENSORA 3D blast simulation');
  S.push('/NODE','#  node_ID                 Xc                  Yc                  Zc');
  for(let i=0;i<mesh.nodes.length;i++)if(used[i]){const [x,y,z]=mesh.nodes[i];S.push(i10(i+1)+f20(x)+f20(y)+f20(z));}
  for(const m of materials)S.push(...m.lines);
  S.push('/PROP/SOLID/1','tet4 explicit',
    '#   Isolid    Ismstr      Iale     Icpre  Itetra10     Inpts   Itetra4    Iframe                  Dn',
    i10(0)+i10(0)+i10(0)+i10(0)+i10(0)+i10(0)+i10(0)+i10(0)+f20(0),
    '#                 qa                  qb                   h              Lambda                  Mu',
    f20(0)+f20(0)+f20(0)+f20(0)+f20(0),
    '#         deltaT_min            vdef_min            vdef_max             ASP_max             COL_min',
    f20(0)+f20(0)+f20(0)+f20(0)+f20(0),
    '#     Ndir sphpartID  Icontrol',i10(0)+i10(0)+i10(0));
  const tetsByPart=new Map(parts.map(p=>[p.id,[]]));
  let elementCount=0;
  mesh.tets.forEach((tet,i)=>{
    if(!active[i])return;
    const part=partOfVolume.get(String(mesh.tetVolumes[i]));
    const nodes=[...tet];
    if(tetData(nodes.map(n=>mesh.nodes[n])).orientation<0)[nodes[1],nodes[2]]=[nodes[2],nodes[1]];
    elementCount++;
    tetsByPart.get(part.id).push(i10(i+1)+nodes.map(n=>i10(n+1)).join(''));
  });
  for(const part of parts){
    S.push(`/PART/${part.id}`,title(`volume ${part.volume} ${part.role}`),'#  prop_ID    mat_ID subset_ID',i10(1)+i10(part.materialId)+i10(0));
    const rows=tetsByPart.get(part.id);
    if(rows.length){S.push(`/TETRA4/${part.id}`,...rows);}
  }

  let groupId=0,cardId=0;
  // Fixed restraints grouped by DOF pattern.
  const patterns=new Map();
  for(let i=0;i<mesh.nodes.length;i++){
    if(!used[i])continue;
    const code=`${fixed[i*3]}${fixed[i*3+1]}${fixed[i*3+2]}`;
    if(code==='000')continue;
    if(!patterns.has(code))patterns.set(code,[]);
    patterns.get(code).push(i+1);
  }
  for(const [code,ids] of patterns){
    const g=++groupId;pushGroup(S,g,`fixed ${code}`,ids);
    S.push(`/BCS/${++cardId}`,`fixed ${code}`,'#  Tra rot   skew_ID  grnod_ID',`   ${code} 000${i10(0)}${i10(g)}`);
  }
  // Absorbing boundary: graded Rayleigh-damping layer (/DAMP) next to the selected
  // outer faces. OpenCourant 20261011 /BCS/NRF mishandles triangular faces in the
  // Starter domain split (node_list(4)=0 in split_bcs_nrf), so tetrahedral meshes
  // cannot use it reliably; explicit dashpots would need boundary-scale spring mass.
  const surfaceMap=new Map((mesh.surfaces||[]).map(face=>[String(face.id),face]));
  let absorbingNodes=0,layer=null;
  if(s.absorbingSurfaces.length){
    layer=absorbingLayer(mesh,s.absorbingSurfaces,surfaceMap,active,partOfVolume,materials,used,s.absorbingThickness);
    absorbingNodes=layer.nodes;
    for(const band of layer.groups){
      const g=++groupId;pushGroup(S,g,'absorbing layer band',band.ids);
      S.push(`/DAMP/${++cardId}`,'absorbing layer band',
        '#              Alpha                Beta  grnod_id   skew_id              Tstart               Tstop',
        f20(band.alpha)+f20(0)+i10(g)+i10(0)+f20(0)+f20(s.endTime*10));
    }
  }
  // Constant external loads (confinement, gravity, point/line/surface loads).
  let loadedNodes=0;
  if(applyLoads){
    const constant=++cardId;
    pushFunction(S,constant,'constant external load',[[0,1],[s.endTime*10,1]]);
    for(let i=0;i<mesh.nodes.length;i++){
      const f=[force[i*3],force[i*3+1],force[i*3+2]];
      if(!f.some(v=>v!==0))continue;
      loadedNodes++;
      const g=++groupId;pushGroup(S,g,'load node',[i+1]);
      f.forEach((value,d)=>{
        if(value===0)return;
        S.push(`/CLOAD/${++cardId}`,'external load','#funct_IDT       Dir   skew_ID sensor_ID  grnod_ID   Itypfun             Ascalex             Fscaley',
          i10(constant)+'XYZ'[d].padStart(10)+i10(0)+i10(0)+i10(g)+i10(0)+f20(1)+f20(value));
      });
    }
  }
  // Blast source.
  let source;
  if(s.sourceMode==='pressure'){
    const owners=faceOwners(mesh.tets,rockTet);
    const segments=[];let area=0;
    for(const id of s.wallSurfaces){
      const face=surfaceMap.get(id);
      if(!face)throw Error(`未找到孔壁面 ${id}。`);
      for(const tri of face.triangles){
        const list=owners.get(faceKey(...tri));
        if(!list||list.length!==1)throw Error(`CAD 面 ${id} 不是岩体的外表面（例如位于两个岩体之间），不能作为孔壁加载面。`);
        const [a,b,c]=tri.map(n=>mesh.nodes[n]);
        const normal=cross(sub(b,a),sub(c,a));
        // A positive OpenCourant /PLOAD pushes along the segment normal (verified with
        // the borehole regression), so orient each segment normal into the rock.
        const seg=dot(normal,sub(mesh.nodes[list[0].opposite],a))>0?tri:[tri[0],tri[2],tri[1]];
        segments.push(seg);area+=Math.hypot(...normal)/2;
      }
    }
    const surf=++cardId,funct=++cardId;
    S.push(`/SURF/SEG/${surf}`,'blast hole wall');
    segments.forEach((seg,k)=>S.push(i10(k+1)+i10(seg[0]+1)+i10(seg[1]+1)+i10(seg[2]+1)+i10(seg[2]+1)));
    pushFunction(S,funct,'blast hole pressure history',pulseFunction(s));
    S.push(`/PLOAD/${++cardId}`,'blast hole pressure',
      '#  surf_ID  functIDT sensor_ID    Ipinch      Idel   Itypfun            Ascale_x            Fscale_y',
      i10(surf)+i10(funct)+i10(0)+i10(0)+i10(0)+i10(0)+f20(1)+f20(s.peakPressure));
    source={mode:'pressure',segments:segments.length,wallArea:area,peakPressure:s.peakPressure,pulseDuration:s.pulseDuration,pulseShape:s.pulseShape};
  }else{
    const chargeMaterial=materials.find(m=>m.role==='charge');
    let point=s.detonationPoint;
    if(!point.length){
      // Default: centroid of the charge volumes.
      let sum=[0,0,0],volume=0;
      mesh.tets.forEach((tet,i)=>{
        if(!active[i]||partOfVolume.get(String(mesh.tetVolumes[i])).role!=='charge')return;
        const pts=tet.map(n=>mesh.nodes[n]),v=Math.abs(tetData(pts).volume);
        for(let d=0;d<3;d++)sum[d]+=v*(pts[0][d]+pts[1][d]+pts[2][d]+pts[3][d])/4;
        volume+=v;
      });
      point=sum.map(v=>v/volume);
    }
    S.push(`/DFS/DETPOINT/${++cardId}`,'#               XDET                YDET                ZDET                TDET mat_IDDET',
      f20(point[0])+f20(point[1])+f20(point[2])+f20(s.detonationTime)+i10(chargeMaterial.id));
    source={mode:'jwl',detonationPoint:point,detonationTime:s.detonationTime,explosive:s.explosive.name,cjPressure:chargeMaterial.pcj,
      E0:chargeMaterial.E0};
  }
  // Initial stress from the MFEM equilibrium (rock elements only).
  if(prestress){
    S.push('/INIBRI/STRS_FGLO');
    mesh.tets.forEach((_,i)=>{
      if(!rockTet[i])return;
      const k=prestress.elementIndex[i];
      if(k<0)return;
      const [sxx,syy,szz,sxy,sxz,syz]=prestress.stress.subarray(k*6,k*6+6);
      const material=materials.find(m=>m.id===partOfVolume.get(String(mesh.tetVolumes[i])).materialId);
      // OpenCourant recomputes pressure from the EOS (mu = rho/rho0 - 1) every
      // cycle, so the hydrostatic part of the initial stress is carried by the
      // initial density; deviatoric stresses are updated incrementally.
      const rho=material.rho*(1+volumetricStrain(material,-(sxx+syy+szz)/3));
      S.push('# brick_ID Nb_integr   Isolnod    Isolid      nptr      npts      nptt      nlay grbric_ID',
        i10(i+1)+i10(1)+i10(4)+i10(0)+i10(0)+i10(0)+i10(0)+i10(0)+i10(0),
        f20(0)+f20(rho),f20(sxx)+f20(syy)+f20(szz),f20(sxy)+f20(syz)+f20(sxz),f20(0));
    });
  }
  S.push('/END');

  const animDt=s.endTime/(s.frames-1);
  const parith='/PARITH/ON';
  // Run slightly past the end so the animation at t=endTime is written.
  // Half an output interval exceeds any stable time step, and no further frame is due before it.
  E.push('/RUN/tensora_blast3d/1',f20(s.endTime+animDt*0.5).trim(),
    '/ANIM/DT',`0 ${animDt}`,
    '/ANIM/VECT/DISP','/ANIM/VECT/VEL',
    '/ANIM/BRICK/TENS/STRESS','/ANIM/BRICK/TENS/STRAIN','/ANIM/ELEM/VONM','/ANIM/ELEM/EPSP','/ANIM/ELEM/P',
    ...(decksUseDamage(materials)?['/ANIM/ELEM/DAMG']:[]),...(decksUseFailure(materials)?['/ANIM/BRICK/DAMA']:[]),
    '/DT/NODA/CST/0',`${s.timeStepScale} 0`,
    '/TFILE/0',String(Math.max(animDt/20,s.endTime/2000)),
    '/PRINT/-500',parith,'/END');
  return {
    starter:S.join('\n')+'\n',engine:E.join('\n')+'\n',settings:s,
    meta:{nodes:mesh.nodes.length,usedNodes:used.reduce((a,b)=>a+b,0),elements:elementCount,parts,materials:materials.map(({lines,...m})=>m),
      fixedDofs:fixed.reduce((a,b)=>a+b,0),absorbingNodes,loadedNodes,source,applyLoads,animDt,
      absorbingLayer:layer?{thickness:layer.thickness,alphaMax:layer.alphaMax,bands:layer.groups.length,waveSpeed:layer.waveSpeed}:null,
      volumeRoles:Object.fromEntries(volumes.map(v=>[v,roleOf(v)]))},
    force,fixed,used,rockTet,partOfVolume,materials
  };
}

module.exports={buildDecks,normalizeSettings,LIMITS,f20,faceOwners,pulseFunction};
