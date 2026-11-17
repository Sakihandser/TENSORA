'use strict';
// 2D blast workflow on bundled open-source solvers:
//   (optional) MFEM 4.10 plane-strain static equilibrium -> OpenCourant Starter/Engine
//   (one-layer plane-strain slab of BRICK cells, ALE LAW51 explosive products and air)
//   -> OpenCourant anim_to_vtk / th_to_csv -> FEMBLT02 frames on the TRI3 mesh.
// TENSORA only converts the shared TRI3 model into keyword cards, launches the
// unmodified executables and maps their output back. Explicit integration,
// constitutive laws (/MAT/ELAST, /MAT/JOHN_HOLM, /MAT/DPRAG1), multi-material ALE
// gas dynamics (/MAT/LAW51 + /MAT/JWL + /EOS/POLYNOMIAL), detonation
// (/DFS/DETPOINT), wall pressure (/PLOAD), quiet boundaries (/BCS/NRF), damping
// (/DAMP) and initial stress (/INIBRI) are all computed by OpenCourant.
const fs=require('node:fs/promises');
const path=require('node:path');
const os=require('node:os');
const {existsSync}=require('node:fs');
const Settings=require('./blast-settings');
const RockMaterials=require('./blast-materials');
const Blast3dCards=require('./blast3d-cards');
const {f20}=require('./blast3d-deck');
const B3=require('./blast3d-runner');

const MFEM=path.join(__dirname,'third_party','mfem','runtime-win-x64','mfem_prestress.exe');
const GMSH=path.join(__dirname,'third_party','gmsh','gmsh-4.15.0-Windows64','gmsh.exe');
const SOLVER='OpenCourant 20261011 (OpenRadioss continuation), 2D plane strain';
const i10=value=>{if(!Number.isSafeInteger(value))throw Error('卡片编号无效');return String(value).padStart(10);};
const title=text=>String(text).replace(/[^\x20-\x7e]/g,'_').slice(0,100)||'item';
const LIMITS={elements:400_000};

function available(){
  const state=B3.available();
  return {opencourant:state.opencourant,mfem:existsSync(MFEM),gmsh:existsSync(GMSH)};
}

// ------------------------------------------------------------------ settings
function normalizeSettings(input){
  const s=Settings.normalize(input);
  if(s.chargeRadius>s.radius*(1+1e-8))throw Error("Charge radius exceeds the cavity radius.");
  const errors=[];
  // Requests carrying options of the removed legacy core are rejected, not silently dropped.
  if(input.ventEnds>0)errors.push('轴向开口泄流已随旧二维核心移除，OpenCourant 平面应变 ALE 中炮孔两端封闭。');
  if(input.gasFracture===1)errors.push('“连通裂隙均压储气”已随旧二维核心移除，OpenCourant 计算中气体只作用于炮孔内。');
  if(errors.length)throw Error(errors.join('\n'));
  return s;
}

// ---------------------------------------------------------- mesh conversion
// Each TRI3 becomes three QUAD4 cells (vertex, edge midpoint, centroid, edge
// midpoint). The quads are non-degenerate and are extruded into one layer of
// one-point HEPH bricks (Isolid=24) with z fixed, so no collapsed element
// biases the lumped mass or the hourglass control.
function buildMesh(model,s){
  if(!model||!Array.isArray(model.nodes)||!Array.isArray(model.elements)||model.nodes.length<3||!model.elements.length)throw Error('二维爆破需要节点与三角形单元。');
  if(model.elements.length>LIMITS.elements)throw Error(`OpenCourant 二维爆破最多支持 ${LIMITS.elements.toLocaleString()} 个三角形单元。`);
  const N=model.nodes.length,index=new Map();
  model.nodes.forEach((n,i)=>{if(!Number.isFinite(n.x)||!Number.isFinite(n.y))throw Error('节点坐标无效。');if(index.has(n.nodeNo))throw Error('节点编号重复。');index.set(n.nodeNo,i);});
  const X=[],Y=[];model.nodes.forEach(n=>{X.push(n.x);Y.push(n.y);});
  const tris=[],edges=new Map(),key=(a,b)=>a<b?a*N+b:b*N+a;
  model.elements.forEach((e,t)=>{
    let v=[e.node1,e.node2,e.node3].map(no=>{const i=index.get(no);if(i===undefined)throw Error(`单元 ${e.elementNo} 引用不存在的节点。`);return i;});
    const det=(X[v[1]]-X[v[0]])*(Y[v[2]]-Y[v[0]])-(X[v[2]]-X[v[0]])*(Y[v[1]]-Y[v[0]]);
    if(!(Math.abs(det)>0)||!Number.isFinite(det))throw Error(`单元 ${e.elementNo} 面积为零。`);
    if(det<0)v=[v[0],v[2],v[1]];
    tris.push({v,area:Math.abs(det)/2,materialNo:e.materialNo});
    for(let k=0;k<3;k++){
      const a=v[k],b=v[(k+1)%3],id=key(a,b);
      let edge=edges.get(id);
      if(!edge){edge={a:Math.min(a,b),b:Math.max(a,b),count:0,tri:t,third:v[(k+2)%3],mid:-1};edges.set(id,edge);}
      if(++edge.count>2)throw Error('网格存在非流形边。');
    }
  });
  // Node numbering: original vertices, edge midpoints, triangle centroids.
  const PX=[...X],PY=[...Y];
  for(const edge of edges.values()){edge.mid=PX.length;PX.push((X[edge.a]+X[edge.b])/2);PY.push((Y[edge.a]+Y[edge.b])/2);}
  const centroid=tris.map(t=>{const id=PX.length;PX.push((X[t.v[0]]+X[t.v[1]]+X[t.v[2]])/3);PY.push((Y[t.v[0]]+Y[t.v[1]]+Y[t.v[2]])/3);return id;});
  const quads=[],quadParent=[],quadArea=[];
  tris.forEach((t,ti)=>{
    const m=k=>edges.get(key(t.v[k],t.v[(k+1)%3])).mid;
    for(let k=0;k<3;k++){
      const q=[t.v[k],m(k),centroid[ti],m((k+2)%3)];
      quads.push(q);quadParent.push(ti);quadArea.push(polygonArea(q.map(n=>[PX[n],PY[n]])));
    }
  });
  return {N,X,Y,PX,PY,tris,edges,key,centroid,quads,quadParent,quadArea,index};
}
function polygonArea(points){let a=0;for(let i=0;i<points.length;i++){const p=points[i],q=points[(i+1)%points.length];a+=p[0]*q[1]-p[1]*q[0];}return a/2;}

// Boundary loops, the blast cavity and per-edge boundary modes (same rules as the
// documented 2D workflow: 3% radius tolerance, closed loop, at least 6 edges).
function classifyBoundary(mesh,model,s){
  const {N,X,Y,edges,tris,key}=mesh;
  const parent=Array.from({length:N},(_,i)=>i),find=i=>{while(parent[i]!==i){parent[i]=parent[parent[i]];i=parent[i];}return i;};
  const boundary=[...edges.values()].filter(e=>e.count===1);
  for(const e of boundary){const a=find(e.a),b=find(e.b);if(a!==b)parent[b]=a;}
  const loopArea=new Map();
  for(const e of boundary){
    const cross=(X[e.b]-X[e.a])*(Y[e.third]-Y[e.a])-(Y[e.b]-Y[e.a])*(X[e.third]-X[e.a]);
    const r=find(e.a);loopArea.set(r,(loopArea.get(r)||0)+(cross>0?1:-1)*(X[e.a]*Y[e.b]-Y[e.a]*X[e.b]));
  }
  // The blast centre must lie in a hole, not inside a solid triangle.
  for(const t of tris){
    const [p,q,r]=t.v,det=(X[q]-X[p])*(Y[r]-Y[p])-(X[r]-X[p])*(Y[q]-Y[p]);
    const s1=((X[q]-X[p])*(s.y-Y[p])-(Y[q]-Y[p])*(s.x-X[p]))/det,s2=((s.x-X[p])*(Y[r]-Y[p])-(s.y-Y[p])*(X[r]-X[p]))/det;
    if(s1>=-1e-10&&s2>=-1e-10&&s1+s2<=1+1e-10)throw Error('爆源中心必须位于网格中显式建出的圆形炮孔内。');
  }
  const tol=Math.max(s.radius*.03,1e-10),overrides=new Map();
  for(const edge of model.blastBoundaryEdges||[]){
    const a=mesh.index.get(edge.node1),b=mesh.index.get(edge.node2);
    if(a===undefined||b===undefined||![0,1,2,3].includes(edge.mode))throw Error('边界覆盖设置无效。');
    const e=edges.get(key(a,b));if(!e||e.count!==1)throw Error('边界覆盖必须引用真实的外边界网格边。');
    if(overrides.has(key(a,b)))throw Error('边界覆盖重复。');overrides.set(key(a,b),edge.mode);
  }
  const wall=[],outer=[],other=[];
  for(const e of boundary){
    const area=loopArea.get(find(e.a));
    const onCircle=n=>Math.abs(Math.hypot(X[n]-s.x,Y[n]-s.y)-s.radius)<=tol;
    if(area<0&&onCircle(e.a)&&onCircle(e.b)){
      // Inward (solid) side must face away from the centre.
      const mx=(X[e.a]+X[e.b])/2,my=(Y[e.a]+Y[e.b])/2,toSolid=[X[e.third]-mx,Y[e.third]-my];
      if(toSolid[0]*(mx-s.x)+toSolid[1]*(my-s.y)<=0)throw Error('识别到的加载边界不是炮孔壁。');
      wall.push(e);
    }else (area>0?outer:other).push(e);
  }
  if(wall.length<6)throw Error('没有与爆源中心/半径匹配、且至少含 6 条网格边的闭合圆形炮孔。');
  const degree=new Map();for(const e of wall)for(const n of [e.a,e.b])degree.set(n,(degree.get(n)||0)+1);
  for(const d of degree.values())if(d!==2)throw Error('炮孔壁必须是完整闭合的边界环。');
  const modeOf=new Map();
  for(const e of outer)modeOf.set(e,overrides.get(key(e.a,e.b))??s.boundary);
  for(const e of other)modeOf.set(e,overrides.get(key(e.a,e.b))??0);
  return {wall,outer,other,modeOf};
}

// Ordered wall loop on the quad mesh (vertex, midpoint, vertex, ...), CCW about the centre.
function wallLoop(mesh,wall,s){
  const {X,Y,PX,PY}=mesh,next=new Map();
  for(const e of wall){(next.get(e.a)||next.set(e.a,[]).get(e.a)).push(e);(next.get(e.b)||next.set(e.b,[]).get(e.b)).push(e);}
  const loop=[],start=wall[0].a;let node=start,prev=null;
  for(let guard=0;guard<=wall.length;guard++){
    const e=next.get(node).find(item=>item!==prev);
    loop.push(node,e.mid);prev=e;node=e.a===node?e.b:e.a;
    if(node===start)break;
  }
  if(loop.length!==2*wall.length)throw Error('炮孔壁不是单一闭合环。');
  if(polygonArea(loop.map(n=>[PX[n]-s.x,PY[n]-s.y]))<0)loop.reverse();
  return loop;
}

// ------------------------------------------------------------- materials
function solidMaterial(material,id,s,warnings){
  const label=material.name||`材料 ${material.materialNo}`;
  const name=title(material.name||`material ${material.materialNo}`);
  const rho=Number(material.density),E=Number(material.elasticModulus),nu=Number(material.poissonRatio);
  if(!(rho>0)||!(E>0)||!(nu>-1&&nu<.5))throw Error(`${material.name||material.materialNo}：需要正的密度、弹性模量与 -1<ν<0.5。`);
  // A blast-library card linked to the base material (shared with the 3D workspace)
  // takes precedence over the legacy 2D card; the slab uses the same OpenCourant laws.
  if(material.blastCard){
    const m=Blast3dCards.materialLines(material.blastCard,{id,name:material.name||`material ${material.materialNo}`,rho,E,nu},label);
    if(m.failure)warnings.push(`${label}：拉伸应变失效会删除薄片单元，二维结果中被删除的三角形保持最后的应力。`);
    return {id,...m,source:'library'};
  }
  const {model:law,card}=RockMaterials.validate(material,s);
  const Gel=E/(2*(1+nu)),Kel=E/(3*(1-2*nu));
  if(law===1)return {id,law:'elastic',rho,E,nu,G:Gel,K:Kel,lines:[`/MAT/ELAST/${id}`,name,'#              RHO_I',f20(rho),'#                  E                  nu',f20(E)+f20(nu)]};
  if(law===3){
    const j=card.jh2,G=j.G>0?j.G:Gel;
    const derived=1.5*(j.HEL-j.pHEL);
    if(j.normalizationStress>0&&Math.abs(j.normalizationStress-derived)>1e-6*derived)warnings.push(`${label}：OpenCourant LAW79 用 σHEL = 1.5(HEL−PHEL) = ${(derived/1e9).toPrecision(4)} GPa 归一化，忽略输入的归一化应力 ${(j.normalizationStress/1e9).toPrecision(4)} GPa。`);
    return {id,law:'jh2',rho,E,nu,G,K:j.K1,K1:j.K1,K2:j.K2,K3:j.K3,lines:[`/MAT/JOHN_HOLM/${id}`,name,
      '#              RHO_I',f20(rho),'#                  G',f20(G),
      '#                  a                   b                   m                   n',f20(j.A)+f20(j.B)+f20(j.M)+f20(j.N),
      '#                  c                EPS0          SIGMA_FMAX',f20(j.C)+f20(j.rate0)+f20(j.maxStrength),
      '#                  T                 HEL                PHEL',f20(j.T)+f20(j.HEL)+f20(j.pHEL),
      '#                 D1                  D2',f20(j.D1)+f20(j.D2),
      '#                 K1                  K2                  K3                BETA',f20(j.K1)+f20(j.K2)+f20(j.K3)+f20(j.beta)]};
  }
  // Mohr-Coulomb -> Drucker-Prager cone matched to MC in plane strain
  // (Drucker & Prager 1952): sqrt(J2) = k + alpha p with
  // alpha = 3 tan(phi)/sqrt(9+12 tan^2 phi), k = 3c/sqrt(9+12 tan^2 phi).
  // OpenCourant LAW10 uses J2 = A0 + A1 p + A2 p^2 and the tension cutoff Pmin.
  const c=card.mc,tanPhi=Math.tan(c.friction*Math.PI/180),root=Math.sqrt(9+12*tanPhi*tanPhi);
  const alpha=3*tanPhi/root,k=3*c.cohesion/root;
  warnings.push(`${label}：Mohr–Coulomb 以平面应变匹配的 Drucker–Prager 锥（OpenCourant LAW10）计算；剪胀角、应变软化与残余强度参数在该卡中没有对应项，未参与计算。`);
  return {id,law:'dp',rho,E,nu,G:Gel,K:Kel,lines:[`/MAT/DPRAG1/${id}`,name,'#              RHO_I',f20(rho),
    '#                  E                  Nu',f20(E)+f20(nu),
    '#                 A0                  A1                  A2                Amax',f20(k*k)+f20(2*k*alpha)+f20(alpha*alpha)+f20(0),
    '#              P_min',f20(-c.tension)]};
}
// Compression mu that gives EOS pressure p (LAW1/LAW10 linear, LAW79 cubic in compression).
function volumetricStrain(m,p){
  if(m.law!=='jh2'||p<=0)return p/m.K;
  let mu=p/m.K1;
  for(let k=0;k<60;k++){const f=m.K1*mu+m.K2*mu*mu+m.K3*mu**3-p,df=m.K1+2*m.K2*mu+3*m.K3*mu*mu;if(!(df>0))break;const step=f/df;mu-=step;if(Math.abs(step)<1e-16)break;}
  return mu;
}

// ----------------------------------------------------------- cavity (ALE)
async function meshCavity(work,mesh,loop,s,options){
  const {PX,PY}=mesh,n=loop.length,lines=['General.Terminal = 1;','Mesh.MshFileVersion = 2.2;','Mesh.RecombineAll = 1;','Mesh.Algorithm = 8;',
    'Mesh.RecombinationAlgorithm = 1;','Mesh.Smoothing = 10;','Mesh.CharacteristicLengthExtendFromBoundary = 1;','Mesh.CharacteristicLengthFromPoints = 1;'];
  for(let i=0;i<n;i++){
    const a=loop[(i+n-1)%n],b=loop[i],c=loop[(i+1)%n];
    const lc=(Math.hypot(PX[b]-PX[a],PY[b]-PY[a])+Math.hypot(PX[c]-PX[b],PY[c]-PY[b]))/2;
    lines.push(`Point(${i+1}) = {${PX[b].toPrecision(17)}, ${PY[b].toPrecision(17)}, 0, ${lc.toPrecision(12)}};`);
  }
  for(let i=0;i<n;i++)lines.push(`Line(${i+1}) = {${i+1}, ${(i+1)%n+1}};`);
  lines.push(`Transfinite Curve{1:${n}} = 2;`,`Curve Loop(1) = {1:${n}};`,'Plane Surface(1) = {1};','Recombine Surface{1};');
  await fs.writeFile(path.join(work,'cavity.geo'),lines.join('\n')+'\n');
  const log={write(){}},code=await B3.execute(GMSH,['cavity.geo','-2','-format','msh2','-o','cavity.msh','-nt','1'],{cwd:work,env:process.env,signal:options.signal,timeoutMs:5*60*1000,log});
  if(code!==0)throw Error(`Gmsh 炮孔网格划分失败（退出码 ${code}）。`);
  const text=await fs.readFile(path.join(work,'cavity.msh'),'latin1'),rows=text.split(/\r?\n/);
  const ni=rows.indexOf('$Nodes'),ei=rows.indexOf('$Elements');
  if(ni<0||ei<0)throw Error('Gmsh 未输出 MSH2 节点和单元。');
  const nodeCount=Number(rows[ni+1]),gmshNode=new Map(),size=Math.max(s.radius,1e-12);
  const wallKey=new Map(loop.map(id=>[`${Math.round(PX[id]/size*1e9)},${Math.round(PY[id]/size*1e9)}`,id]));
  const newNodes=[];
  for(let k=0;k<nodeCount;k++){
    const [tag,x,y]=rows[ni+2+k].trim().split(/\s+/).map(Number);
    const hit=wallKey.get(`${Math.round(x/size*1e9)},${Math.round(y/size*1e9)}`);
    if(hit!==undefined)gmshNode.set(tag,hit);
    else{const id=PX.length+newNodes.length;newNodes.push([x,y]);gmshNode.set(tag,id);}
  }
  const elementCount=Number(rows[ei+1]),cells=[];let triangles=0;
  for(let k=0;k<elementCount;k++){
    const parts=rows[ei+2+k].trim().split(/\s+/).map(Number),type=parts[1],tags=parts[2],ids=parts.slice(3+tags).map(t=>gmshNode.get(t));
    if(type===3)cells.push(ids);
    else if(type===2){cells.push([ids[0],ids[1],ids[2],ids[2]]);triangles++;}
  }
  if(!cells.length)throw Error('Gmsh 未生成炮孔网格。');
  const matched=new Set([...gmshNode.values()].filter(id=>id<PX.length));
  if(matched.size!==loop.length)throw Error('Gmsh 炮孔网格的边界节点与孔壁节点不一致。');
  for(const [x,y] of newNodes){PX.push(x);PY.push(y);}
  for(const cell of cells){
    const a=polygonArea(cell.map(id=>[PX[id],PY[id]]));
    if(a<0)cell.reverse();
    if(!(Math.abs(a)>0))throw Error('炮孔网格存在零面积单元。');
  }
  return {cells,triangles,newNodes:newNodes.length};
}
// Area fraction of a quad inside the charge circle (bilinear map, Gauss sampling).
function chargeFraction(points,s){
  const r=s.chargeRadius,d=points.map(([x,y])=>Math.hypot(x-s.x,y-s.y));
  const radius=Math.max(...points.map(([x,y])=>Math.hypot(x-points[0][0],y-points[0][1])));
  if(Math.max(...d)<=r)return 1;
  if(Math.min(...d)>=r+radius)return 0;
  const g=16;let inside=0,total=0;
  for(let i=0;i<g;i++)for(let j=0;j<g;j++){
    const xi=-1+(2*i+1)/g,eta=-1+(2*j+1)/g,N=[(1-xi)*(1-eta),(1+xi)*(1-eta),(1+xi)*(1+eta),(1-xi)*(1+eta)].map(v=>v/4);
    const dN=[[-(1-eta),-(1-xi)],[1-eta,-(1+xi)],[1+eta,1+xi],[-(1+eta),1-xi]].map(v=>v.map(w=>w/4));
    let x=0,y=0,J=[[0,0],[0,0]];
    for(let k=0;k<4;k++){x+=N[k]*points[k][0];y+=N[k]*points[k][1];J[0][0]+=dN[k][0]*points[k][0];J[0][1]+=dN[k][1]*points[k][0];J[1][0]+=dN[k][0]*points[k][1];J[1][1]+=dN[k][1]*points[k][1];}
    const w=Math.abs(J[0][0]*J[1][1]-J[0][1]*J[1][0]);total+=w;if(Math.hypot(x-s.x,y-s.y)<=r)inside+=w;
  }
  return inside/total;
}

// --------------------------------------------------------------- the deck
async function buildDecks(model,rawSettings,work,options={}){
  const s=normalizeSettings(rawSettings),warnings=[];
  const mesh=buildMesh(model,s),bnd=classifyBoundary(mesh,model,s);
  const loop=wallLoop(mesh,bnd.wall,s);
  const {N,PX,PY,quads,quadParent,quadArea,tris,edges}=mesh;
  // Materials.
  const materials=new Map();let nextId=0;
  for(const m of model.materials||[])materials.set(m.materialNo,solidMaterial(m,++nextId,s,warnings));
  for(const t of tris)if(!materials.has(t.materialNo))throw Error('每个实体材料都需要有效的爆破本构卡。');
  // Constraints: model restraints, then per-edge boundary modes on vertices; midpoint
  // and centroid DOFs are fixed where the linear TRI3 field is fixed.
  const nodeCount=()=>PX.length;
  const fixed=new Uint8Array(PX.length*2);
  model.nodes.forEach((n,i)=>{fixed[2*i]=n.fixUx?1:0;fixed[2*i+1]=n.fixUy?1:0;});
  const nodeMode=new Int8Array(N),absorbingEdges=[];let fixedEdges=0;
  for(const [e,mode] of bnd.modeOf){if(mode>0){for(const n of [e.a,e.b])nodeMode[n]=Math.max(nodeMode[n],mode);}if(mode===2)absorbingEdges.push(e);if(mode===3)fixedEdges++;}
  for(let i=0;i<N;i++)if(nodeMode[i]>0)fixed[2*i]=fixed[2*i+1]=nodeMode[i]===3?1:0;
  for(const e of edges.values())for(let d=0;d<2;d++)fixed[2*e.mid+d]=fixed[2*e.a+d]&&fixed[2*e.b+d];
  tris.forEach((t,ti)=>{for(let d=0;d<2;d++)fixed[2*mesh.centroid[ti]+d]=fixed[2*t.v[0]+d]&&fixed[2*t.v[1]+d]&&fixed[2*t.v[2]+d];});
  // Constant external load: assembled nodal loads of the model plus the confining
  // traction t = -diag(px,py) n on the outer boundary (consistent on sub-edges).
  const force=new Float64Array(PX.length*2);
  model.nodes.forEach((n,i)=>{force[2*i]+=Number(n.forceX)||0;force[2*i+1]+=Number(n.forceY)||0;});
  const inward=e=>{const dx=PX[e.b]-PX[e.a],dy=PY[e.b]-PY[e.a],L=Math.hypot(dx,dy);let n=[-dy/L,dx/L];
    if(n[0]*(PX[e.third]-(PX[e.a]+PX[e.b])/2)+n[1]*(PY[e.third]-(PY[e.a]+PY[e.b])/2)<0)n=[-n[0],-n[1]];return {n,L};};
  const confined=s.confineX>0||s.confineY>0;
  if(confined)for(const e of bnd.outer){
    const {n,L}=inward(e),t=[s.confineX*n[0],s.confineY*n[1]];
    for(const [node,w] of [[e.a,L/4],[e.mid,L/2],[e.b,L/4]]){force[2*node]+=w*t[0];force[2*node+1]+=w*t[1];}
  }
  const hasLoads=force.some(v=>v!==0);
  // Ambient pressure of the borehole gas acts on the wall before detonation.
  const airPreload=new Float64Array(PX.length*2);
  if(s.sourceMode===1)for(const e of bnd.wall){const {n,L}=inward(e);for(const [node,w] of [[e.a,L/4],[e.mid,L/2],[e.b,L/4]]){airPreload[2*node]+=w*s.airPressure*n[0];airPreload[2*node+1]+=w*s.airPressure*n[1];}}

  // Cavity: ALE products + air.
  let cavity=null;
  if(s.sourceMode===1)cavity=await meshCavity(work,mesh,loop,s,options);
  // ALE cavity nodes are appended after the rock nodes; they carry no restraint or load.
  const totalNodes=nodeCount();
  const fixedAll=new Uint8Array(totalNodes*2);fixedAll.set(fixed);
  const forceAll=new Float64Array(totalNodes*2);forceAll.set(force);
  const airAll=new Float64Array(totalNodes*2);airAll.set(airPreload);

  // Plane strain as a one-layer slab: every 2D node has a twin at z = H, all z
  // displacements are fixed, and the slab is symmetric about its mid-plane, so the
  // in-plane fields are identical on both faces and eps_zz = gamma_xz = gamma_yz = 0.
  // OpenCourant's 2D QUAD elements were not used because they do not output the JH2
  // (LAW79) damage variable; the one-point BRICK path outputs damage, full stress and
  // strain tensors and accepts /INIBRI initial stress (as in the 3D blast workspace).
  // H is the smallest in-plane cell size, so the slab does not reduce the time step.
  const allCells=cavity?quads.concat(cavity.cells):quads;
  let H=Infinity;for(const c of allCells)H=Math.min(H,Math.sqrt(Math.abs(polygonArea(c.map(n=>[PX[n],PY[n]])))));
  if(!(H>0))throw Error('网格存在零面积单元。');
  const M=totalNodes,top=i=>i+M;
  const S=['#RADIOSS STARTER','# TENSORA 2D (plane-strain slab) blast deck for OpenCourant','/BEGIN','tensora_blast2d','      2026         0',
    '                  kg                   m                   s','                  kg                   m                   s',
    '/TITLE','TENSORA 2D plane-strain blast simulation',
    '/NODE','#  node_ID                 Xc                  Yc                  Zc'];
  for(let i=0;i<M;i++)S.push(i10(i+1)+f20(PX[i])+f20(PY[i])+f20(0));
  for(let i=0;i<M;i++)S.push(i10(top(i)+1)+f20(PX[i])+f20(PY[i])+f20(H));
  for(const m of materials.values())for(const line of m.lines)S.push(line);
  const prop=(id,name,ale)=>S.push(`/PROP/SOLID/${id}`,name,
    '#   Isolid    Ismstr      Iale     Icpre  Itetra10     Inpts   Itetra4    Iframe                  Dn',
    i10(ale?0:24)+i10(0)+i10(ale?1:0)+i10(0)+i10(0)+i10(0)+i10(0)+i10(0)+f20(0),
    '#                 qa                  qb                   h              Lambda                  Mu',f20(0)+f20(0)+f20(0)+f20(0)+f20(0),
    '#         deltaT_min            vdef_min            vdef_max             ASP_max             COL_min',f20(0)+f20(0)+f20(0)+f20(0)+f20(0),
    '#     Ndir sphpartID  Icontrol',i10(0)+i10(0)+i10(0));
  // Rock: one-point HEPH brick (Isolid=24, physical stabilization) on each quad prism.
  prop(1,'rock brick (plane-strain slab)',false);
  const brick=(id,q)=>i10(id)+q.map(n=>i10(n+1)).join('')+q.map(n=>i10(top(n)+1)).join('');
  const parts=[];
  const quadsByMaterial=new Map();
  quads.forEach((q,k)=>{const no=tris[quadParent[k]].materialNo;(quadsByMaterial.get(no)||quadsByMaterial.set(no,[]).get(no)).push(k);});
  for(const [no,list] of quadsByMaterial){
    const m=materials.get(no),part=parts.length+1;parts.push({id:part,role:'rock',materialNo:no,materialId:m.id});
    S.push(`/PART/${part}`,title(`rock material ${no}`),'#  prop_ID    mat_ID subset_ID',i10(1)+i10(m.id)+i10(0),`/BRICK/${part}`);
    for(const k of list)S.push(brick(k+1,quads[k]));
  }
  let groupId=0,cardId=0;
  const group=(name,ids)=>{const g=++groupId;S.push(`/GRNOD/NODE/${g}`,title(name));for(let i=0;i<ids.length;i+=10)S.push(ids.slice(i,i+10).map(id=>i10(id+1)).join(''));return g;};
  const both=ids=>ids.flatMap(i=>[i,top(i)]);
  // Restraints: z on every node (plane strain), plus the in-plane restraints.
  for(const code of ['00','10','01','11']){
    const ids=[];for(let i=0;i<M;i++)if(`${fixedAll[2*i]}${fixedAll[2*i+1]}`===code)ids.push(i);
    if(!ids.length)continue;
    const g=group(`fixed ${code}1`,both(ids));
    S.push(`/BCS/${++cardId}`,`fixed ${code}1`,'#  Tra rot   skew_ID  grnod_ID',`   ${code}1 000${i10(0)}${i10(g)}`);
  }
  // Quiet (Lysmer) boundaries: OpenCourant /BCS/NRF on brick faces whose four nodes are in the set.
  if(absorbingEdges.length){
    const set=new Set();for(const e of absorbingEdges)for(const n of [e.a,e.mid,e.b])set.add(n);
    const g=group('quiet boundary nodes',both([...set].sort((a,b)=>a-b)));
    S.push(`/BCS/NRF/${++cardId}`,'quiet boundary','#   set_ID',i10(g));
  }
  // Mass-proportional damping of the rock.
  if(s.damping>0){
    const rockNodes=new Set();for(const q of quads)for(const n of q)rockNodes.add(n);
    const g=group('rock nodes (mass damping)',both([...rockNodes].sort((a,b)=>a-b)));
    S.push(`/DAMP/${++cardId}`,'mass proportional damping','#              Alpha                Beta  grnod_id   skew_id              Tstart               Tstop',
      f20(s.damping)+f20(0)+i10(g)+i10(0)+f20(0)+f20(s.duration*10));
  }
  // Loads are per unit thickness; each face node carries half of the slab load.
  const applyLoads=hasLoads;
  let loadedNodes=0;
  if(applyLoads){
    const constant=++cardId;S.push(`/FUNCT/${constant}`,'constant external load','#                  X                   Y',f20(0)+f20(1),f20(s.duration*10)+f20(1));
    for(let i=0;i<M;i++){
      if(forceAll[2*i]===0&&forceAll[2*i+1]===0)continue;
      loadedNodes++;const g=group('load node',[i,top(i)]);
      for(let d=0;d<2;d++)if(forceAll[2*i+d]!==0)S.push(`/CLOAD/${++cardId}`,'external load','#funct_IDT       Dir   skew_ID sensor_ID  grnod_ID   Itypfun             Ascalex             Fscaley',
        i10(constant)+'XY'[d].padStart(10)+i10(0)+i10(0)+i10(g)+i10(0)+f20(1)+f20(forceAll[2*i+d]*H/2));
    }
  }
  // Blast source.
  const source={mode:s.sourceMode===1?'gas':'pressure',wallEdges:bnd.wall.length,wallNodes:loop.length};
  const gasParts=[];let aleCells=[],aleMaterials=[];
  if(s.sourceMode===0){
    const surf=++cardId,funct=++cardId;
    S.push(`/SURF/SEG/${surf}`,'blast hole wall');let k=0;
    for(const e of bnd.wall){
      const c=mesh.centroid[e.tri];
      for(const [a,b] of [[e.a,e.mid],[e.mid,e.b]]){
        // A positive /PLOAD acts along the segment normal (verified in the 3D blast
        // regression); segment (p,q,q',p') has the normal (dy,-dx,0) of p->q, which
        // must point into the rock (checked by the outward wall-motion regression).
        const into=(PY[b]-PY[a])*(PX[c]-PX[a])-(PX[b]-PX[a])*(PY[c]-PY[a]);
        const [p,q]=into>0?[a,b]:[b,a];S.push(i10(++k)+i10(p+1)+i10(q+1)+i10(top(q)+1)+i10(top(p)+1));
      }
    }
    S.push(`/FUNCT/${funct}`,'half-sine wall pressure','#                  X                   Y');
    const n=64;for(let i=0;i<=n;i++)S.push(f20(s.pulse*i/n)+f20(Math.sin(Math.PI*i/n)));
    S.push(f20(s.pulse*1.000001)+f20(0),f20(Math.max(s.duration,s.pulse)*10)+f20(0));
    S.push(`/PLOAD/${++cardId}`,'blast hole pressure','#  surf_ID  functIDT sensor_ID    Ipinch      Idel   Itypfun            Ascale_x            Fscale_y',
      i10(surf)+i10(funct)+i10(0)+i10(0)+i10(0)+i10(0)+f20(1)+f20(s.pressure));
    Object.assign(source,{peakPressure:s.pressure,pulse:s.pulse});
  }else{
    // Submaterials: air (ideal gas) and products (JWL or ideal gas).
    const airId=++nextId,prodId=++nextId;
    const gamma=s.airGamma;
    S.push(`/MAT/HYD_VISC/${airId}`,'borehole air','#              RHO_I',f20(s.airDensity),'#                 Nu                Pmin',f20(0)+f20(0));
    S.push(`/EOS/POLYNOMIAL/${airId}`,'ideal gas p=(gamma-1)(1+mu)E','#                 C0                  C1                  C2                  C3',
      f20(0)+f20(0)+f20(0)+f20(0),
      '#                 C4                  C5                  E0                 Psh               RHO_0',f20(gamma-1)+f20(gamma-1)+f20(s.airPressure/(gamma-1))+f20(0)+f20(0));
    let prodLabel;
    if(s.productEOS===1){
      const rho=s.productDensity,D=s.detonationVelocity,pcj=rho*D*D/((s.productGamma>1?s.productGamma:1+s.jwlOmega)+1);
      // LAW51 needs the bulk modulus of the unreacted explosive ahead of the detonation
      // front. Estimate rho0 c0^2 with the bulk sound speed c0 ~ D/3 (TNT: 2.3 km/s).
      const unreactedBulk=rho*(D/3)**2;
      S.push(`/MAT/JWL/${prodId}`,'explosive (JWL)','#              RHO_I',f20(rho),
        '#                  A                   B                  R1                  R2               OMEGA',f20(s.jwlA)+f20(s.jwlB)+f20(s.jwlR1)+f20(s.jwlR2)+f20(s.jwlOmega),
        '#                  D                P_CJ                  E0                Eadd   I_BFRAC      Qopt',f20(D)+f20(pcj)+f20(s.productEnergy*rho)+f20(0)+i10(0)+i10(0),
        '#                 P0                 PSH          Bunreacted',f20(0)+f20(0)+f20(unreactedBulk),
        '#             TSTART               TSTOP',f20(0)+f20(0));
      prodLabel='JWL';Object.assign(source,{cjPressure:pcj,detonationVelocity:D,unreactedBulkModulus:unreactedBulk,unreactedBulkNote:'rho0 (D/3)^2'});
    }else{
      const g=s.productGamma;
      S.push(`/MAT/HYD_VISC/${prodId}`,'reacted products (ideal gas)','#              RHO_I',f20(s.productDensity),'#                 Nu                Pmin',f20(0)+f20(0));
      S.push(`/EOS/POLYNOMIAL/${prodId}`,'ideal-gas products','#                 C0                  C1                  C2                  C3',f20(0)+f20(0)+f20(0)+f20(0),
        '#                 C4                  C5                  E0                 Psh               RHO_0',f20(g-1)+f20(g-1)+f20(s.productDensity*s.productEnergy)+f20(0)+f20(0));
      prodLabel='ideal products';
    }
    // Volume fractions from the charge circle, quantized to 1/50.
    aleCells=cavity.cells;
    const fractionGroups=new Map();let chargeArea=0,cavityArea=0;
    aleCells.forEach((cell,k)=>{
      const pts=cell.map(id=>[PX[id],PY[id]]),a=Math.abs(polygonArea(pts)),f=Math.round(chargeFraction(pts,s)*50)/50;
      chargeArea+=f*a;cavityArea+=a;(fractionGroups.get(f)||fractionGroups.set(f,[]).get(f)).push(k);
    });
    const exact=Math.PI*s.chargeRadius**2,ratio=chargeArea/exact;
    if(Math.abs(ratio-1)>.05)warnings.push(`炮孔网格对装药面积的离散误差为 ${((ratio-1)*100).toFixed(1)}%，建议加密孔壁网格。`);
    prop(2,'borehole gas (ALE multi-material)',true);
    const ids=[...fractionGroups.keys()].sort((a,b)=>a-b);
    for(const f of ids){
      const matId=++nextId,part=parts.length+1;
      S.push(`/MAT/LAW51/${matId}`,title(`borehole gas, charge fraction ${f}`),'','#    Iform',i10(12),
        '#                                     NU              Nu_Vol',' '.repeat(20)+f20(0)+f20(0),
        '#    MatID           ALPHA_MAT',i10(airId)+f20(1-f),i10(prodId)+f20(f));
      parts.push({id:part,role:'gas',fraction:f,materialId:matId});gasParts.push(part);
      aleMaterials.push({id:matId,fraction:f,cells:fractionGroups.get(f).length});
      S.push(`/PART/${part}`,title(`borehole gas ${f}`),'#  prop_ID    mat_ID subset_ID',i10(2)+i10(matId)+i10(0),`/BRICK/${part}`);
      for(const k of fractionGroups.get(f))S.push(brick(quads.length+k+1,aleCells[k]));
    }
    // Laplacian grid smoothing (OpenCourant NWALE=5, lambda=1, one iteration) keeps
    // the ALE cells regular while the Lagrangian wall nodes move with the rock.
    S.push('/ALE/GRID/LAPLACIAN','#             LAMBDA     Niter',f20(1)+i10(1));
    // /BCS fixes the material z velocity only; the grid z velocity of the ALE nodes is
    // fixed separately so the slab keeps its thickness (plane strain for the gas too).
    const aleNodes=new Set();for(const cell of aleCells)for(const n of cell)if(n>=N+mesh.edges.size+tris.length)aleNodes.add(n);
    if(aleNodes.size){const g=group('ALE grid z fixed',both([...aleNodes].sort((a,b)=>a-b)));
      S.push(`/ALE/BCS/${++cardId}`,'ALE grid plane strain','#   trarot   Skew_id   Gnod_id',`   001 000${i10(0)}${i10(g)}`);}
    // A detonation line along the borehole axis (z), i.e. a point in the section.
    if(s.productEOS===1)S.push(`/DFS/DETPOINT/${++cardId}`,'#               XDET                YDET                ZDET                TDET mat_IDDET',f20(s.x)+f20(s.y)+f20(H/2)+f20(0)+i10(0));
    Object.assign(source,{products:prodLabel,chargeArea,exactChargeArea:exact,chargeAreaRatio:ratio,cavityArea,aleElements:aleCells.length,
      aleTriangles:cavity.triangles,aleMaterials,airPressure:s.airPressure});
    S.push(`/TH/PART/${++cardId}`,'borehole gas','#     var1      var2      var3      var4      var5      var6      var7      var8      var9     var10','DEF',
      '#     Obj1      Obj2      Obj3      Obj4      Obj5      Obj6      Obj7      Obj8      Obj9     Obj10');
    for(let i=0;i<gasParts.length;i+=10)S.push(gasParts.slice(i,i+10).map(i10).join(''));
  }
  // Fastest signal speed: rock P waves, detonation or product sound speed.
  let waveSpeed=0;for(const m of materials.values())waveSpeed=Math.max(waveSpeed,Math.sqrt((m.K+4*m.G/3)/m.rho));
  if(s.sourceMode===1)waveSpeed=Math.max(waveSpeed,s.productEOS===1?s.detonationVelocity:Math.sqrt(s.productGamma*(s.productGamma-1)*s.productEnergy));
  return {S,s,mesh,bnd,loop,materials,parts,gasParts,aleCells,fixed:fixedAll,force:forceAll,airPreload:airAll,applyLoads,loadedNodes,absorbingEdges:absorbingEdges.length,fixedEdges,warnings,source,totalNodes,thickness:H,waveSpeed};
}

// ------------------------------------------------- MFEM initial equilibrium
// Plane-strain static equilibrium of the rock under the constant loads (and the
// ambient borehole pressure in gas mode) on the same QUAD mesh. Without physical
// supports, three gauge DOFs per connected body remove rigid modes; the loads
// must then be self-equilibrated (checked below), so the gauges carry no reaction.
async function prestress(work,d,options){
  const {mesh,materials}=d,{PX,PY,quads,quadParent,tris}=mesh;
  const rockNodes=new Int32Array(PX.length).fill(-1),order=[];
  for(const q of quads)for(const n of q)if(rockNodes[n]<0){rockNodes[n]=order.length;order.push(n);}
  const total=new Float64Array(PX.length*2);for(let i=0;i<total.length;i++)total[i]=d.force[i]+d.airPreload[i];
  const slots=[],slotOf=new Map(),rows=[];
  quads.forEach((q,k)=>{
    const m=materials.get(tris[quadParent[k]].materialNo);
    if(!slotOf.has(m.id)){slotOf.set(m.id,slots.length+1);const lambda=m.K-2*m.G/3;slots.push({lambda,mu:m.G});}
    rows.push(`${slotOf.get(m.id)} 3 ${q.map(n=>rockNodes[n]).join(' ')}`);
  });
  // Connected bodies and gauge DOFs.
  const parent=order.map((_,i)=>i),find=i=>{while(parent[i]!==i){parent[i]=parent[parent[i]];i=parent[i];}return i;};
  for(const q of quads)for(let k=1;k<4;k++){const a=find(rockNodes[q[0]]),b=find(rockNodes[q[k]]);if(a!==b)parent[b]=a;}
  const ess=new Set(),bodies=new Map();
  order.forEach((n,i)=>{const r=find(i);(bodies.get(r)||bodies.set(r,[]).get(r)).push(n);});
  for(let i=0;i<order.length;i++)for(let k=0;k<2;k++)if(d.fixed[2*order[i]+k])ess.add(2*i+k);
  let gauges=0;
  for(const ids of bodies.values()){
    const basis=[],x0=PX[ids[0]],y0=PY[ids[0]];let scale=1e-12;for(const n of ids)scale=Math.max(scale,Math.hypot(PX[n]-x0,PY[n]-y0));
    const add=(n,axis)=>{let row=axis===0?[1,0,-(PY[n]-y0)/scale]:[0,1,(PX[n]-x0)/scale];
      for(const b of basis){const t=b[0]*row[0]+b[1]*row[1]+b[2]*row[2];row=row.map((v,j)=>v-t*b[j]);}
      const norm=Math.hypot(...row);if(norm<1e-9)return false;basis.push(row.map(v=>v/norm));return true;};
    for(const n of ids)for(let a=0;a<2;a++)if(d.fixed[2*n+a])add(n,a);
    if(basis.length>=3)continue;
    // Self-equilibrium of the loads on an unsupported body (net force and moment).
    let fx=0,fy=0,mz=0,mag=0;for(const n of ids){const a=total[2*n],b=total[2*n+1];fx+=a;fy+=b;mz+=(PX[n]-x0)*b-(PY[n]-y0)*a;mag+=Math.hypot(a,b);}
    if(mag>0&&(Math.hypot(fx,fy)>1e-8*mag||Math.abs(mz)>1e-8*mag*scale))throw Error('外载荷在没有支座的情况下不能自平衡。请添加真实支承、平衡外载荷，或选择“起爆时突然施加外载荷”。');
    for(const n of ids){if(basis.length>=3)break;for(let a=0;a<2&&basis.length<3;a++)if(!ess.has(2*rockNodes[n]+a)&&add(n,a)){ess.add(2*rockNodes[n]+a);gauges++;}}
  }
  const forces=[];for(const n of order)forces.push(total[2*n],total[2*n+1]);
  // Large meshes: concatenate arrays instead of spreading >100k rows as arguments.
  const meshText=['MFEM mesh v1.0','','dimension','2','','elements',String(rows.length)].concat(rows,['','boundary','0','','vertices',String(order.length),'2'],
    order.map(n=>`${PX[n].toPrecision(17)} ${PY[n].toPrecision(17)}`),['']).join('\n');
  const data=[String(slots.length),...slots.map(v=>`${v.lambda} ${v.mu}`),String(ess.size),[...ess].sort((a,b)=>a-b).join(' '),'1e-12 200000',forces.join(' ')].join('\n');
  await Promise.all([fs.writeFile(path.join(work,'prestress.mesh'),meshText),fs.writeFile(path.join(work,'prestress.dat'),data)]);
  const code=await B3.execute(MFEM,[work],{cwd:work,env:process.env,signal:options.signal,timeoutMs:30*60*1000,log:options.log});
  const lines=(await fs.readFile(path.join(work,'prestress.out'),'utf8').catch(()=>'')).trim().split(/\r?\n/);
  const [converged,iterations,finalNorm,relNorm]=(lines[0]||'').split(/\s+/).map(Number);
  if(code!==0||converged!==1)throw Error(`MFEM 二维初始平衡求解失败（退出码 ${code}，迭代 ${iterations??'-'} 次）。`);
  const stress=new Float64Array(quads.length*4);
  for(let k=0;k<quads.length;k++){const v=lines[k+1].split(/\s+/).map(Number);stress.set([v[0],v[1],v[2],v[3]],k*4);}
  if(!stress.every(Number.isFinite))throw Error('MFEM 初始应力含非有限数值。');
  // Stored elastic energy 1/2 sigma : C^-1 sigma (plane strain, isotropic), per unit thickness.
  let energy=0;
  quads.forEach((q,k)=>{const m=materials.get(tris[quadParent[k]].materialNo),[a,b,c,t]=stress.subarray(k*4,k*4+4);
    energy+=mesh.quadArea[k]*((a*a+b*b+c*c)-2*m.nu*(a*b+b*c+c*a)+2*(1+m.nu)*t*t)/(2*m.E);});
  return {stress,iterations,finalNorm,relativeNorm:relNorm,gauges,energy};
}
function initialStateLines(d,pre){
  const {mesh,materials}=d,{quads,quadParent,tris}=mesh,L=['/INIBRI/STRS_FGLO'];
  for(let k=0;k<quads.length;k++){
    const [a,b,c,t]=pre.stress.subarray(k*4,k*4+4),m=materials.get(tris[quadParent[k]].materialNo);
    // OpenCourant recomputes pressure from the EOS (mu = rho/rho0 - 1) every cycle,
    // so the hydrostatic part is carried by the initial density (as in the 3D path).
    const rho=m.rho*(1+volumetricStrain(m,-(a+b+c)/3));
    L.push('# brick_ID Nb_integr   Isolnod    Isolid      nptr      npts      nptt      nlay grbric_ID',
      i10(k+1)+i10(1)+i10(8)+i10(24)+i10(0)+i10(0)+i10(0)+i10(0)+i10(0),
      f20(0)+f20(rho),f20(a)+f20(b)+f20(c),f20(t)+f20(0)+f20(0),f20(0));
  }
  return L;
}

// --------------------------------------------------------------- results
function readThCsv(text){
  const rows=text.trim().split(/\r?\n/),head=rows[0].split(',').map(v=>v.replace(/"/g,'').trim());
  const data=rows.slice(1).map(r=>r.split(',').map(Number)).filter(r=>Number.isFinite(r[0]));
  const col=name=>head.findIndex(h=>h.toUpperCase()===name);
  return {head,data,col};
}
function interpolate(th,column,time){
  if(!th||column<0||!th.data.length)return 0;
  const rows=th.data;if(time<=rows[0][0])return rows[0][column];
  for(let i=1;i<rows.length;i++)if(rows[i][0]>=time){const a=rows[i-1],b=rows[i],w=(time-a[0])/Math.max(b[0]-a[0],1e-300);return a[column]+w*(b[column]-a[column]);}
  return rows.at(-1)[column];
}
// Average displacement gradient over each triangle, exact for the piecewise-
// bilinear quad field: integral of u (x) n over the triangle boundary (vertex,
// midpoint, vertex on each edge), divided by the area.
function triangleStrain(mesh,ux,uy,t,ti){
  const {PX,PY,edges,key}=mesh;let gxx=0,gxy=0,gyx=0,gyy=0;
  for(let k=0;k<3;k++){
    const a=t.v[k],b=t.v[(k+1)%3],m=edges.get(key(a,b)).mid,nx=PY[b]-PY[a],ny=-(PX[b]-PX[a]);
    const mx=(ux[a]+2*ux[m]+ux[b])/4,my=(uy[a]+2*uy[m]+uy[b])/4;
    gxx+=mx*nx;gxy+=mx*ny;gyx+=my*nx;gyy+=my*ny;
  }
  return [gxx/t.area,gyy/t.area,(gxy+gyx)/t.area];
}

async function runBlast2d(model,rawSettings,options={}){
  const state=available();
  if(!state.opencourant)throw Error('项目内缺少 OpenCourant 运行时，请恢复 third_party/opencourant/runtime-win-x64。');
  const started=Date.now();
  const progress=(phase,fraction,extra={})=>options.onProgress?.({phase,fraction,elapsedSeconds:(Date.now()-started)/1000,...extra});
  progress('preparing',0);
  const work=await B3.asciiWork('tensora-blast2d-'),runtime=path.join(work,'runtime');
  const logParts=[];const log={write:chunk=>{logParts.push(chunk);if(logParts.length>4000)logParts.splice(0,1000);}};
  try{
    if(rawSettings?.sourceMode===1&&!state.gmsh)throw Error('项目内缺少 Gmsh，无法划分炮孔气体网格。');
    const d=await buildDecks(model,rawSettings,work,{signal:options.signal});
    const s=d.s,S=d.S;
    let pre=null;
    if(s.loadMode===0&&(d.applyLoads||s.sourceMode===1)){
      if(!state.mfem)throw Error('项目内缺少 MFEM 初始平衡程序 third_party/mfem/runtime-win-x64/mfem_prestress.exe。');
      progress('prestress',0);
      pre=await prestress(work,d,{signal:options.signal,log});
      for(const line of initialStateLines(d,pre))S.push(line);
    }
    S.push('/END');
    const frames=s.frames,animDt=s.duration/(frames-1);
    const solidList=[...d.materials.values()];
    const damageCards=Blast3dCards.damageAnimations(solidList.map(m=>({damage:m.damage??(m.law==='jh2'?'damg':null),failure:m.failure})));
    const engine=['/RUN/tensora_blast2d/1',f20(s.duration+animDt*.5).trim(),'/ANIM/DT',`0 ${animDt}`,
      '/ANIM/VECT/DISP','/ANIM/VECT/VEL','/ANIM/BRICK/TENS/STRESS',
      '/ANIM/ELEM/VONM','/ANIM/ELEM/EPSP','/ANIM/ELEM/P',...damageCards,
      // Stop (keeping the frames already written) instead of crawling when a
      // distorted cell drives the element time step three decades below its start.
      '/DT/BRICK/STOP',`0.9 ${(1e-3*d.thickness/d.waveSpeed).toExponential(6)}`,
      '/TFILE/0',String(Math.max(animDt/20,s.duration/4000)),'/PRINT/-500','/PARITH/ON','/END'];
    await fs.writeFile(path.join(work,'blast2d_0000.rad'),S.join('\n')+'\n');
    await fs.writeFile(path.join(work,'blast2d_0001.rad'),engine.join('\n')+'\n');
    await fs.symlink(B3.OPENCOURANT,runtime,'junction');
    const threads=Math.max(1,Math.min(8,os.cpus().length));
    const env=B3.environment(runtime,threads),exec=name=>path.join(runtime,'exec',name);
    const dylib=await B3.userLibraryArgs(work,solidList);
    const deadline=started+s.timeLimitSeconds*1000,remaining=()=>Math.max(1000,deadline-Date.now());
    progress('starter',0);
    const starterCode=await B3.execute(exec('starter_win64.exe'),['-i','blast2d_0000.rad','-np','1','-nt',String(threads),...dylib],{cwd:work,env,signal:options.signal,timeoutMs:remaining(),log});
    const restart=(await fs.readdir(work)).some(name=>/^blast2d_0000_\d+\.rst$/i.test(name));
    if(starterCode!==0||!restart){
      const out=await fs.readFile(path.join(work,'blast2d_0000.out'),'latin1').catch(()=>'');
      const errors=out.split(/\r?\n/).map((line,i,all)=>/ERROR ID/.test(line)?all.slice(i,i+4).join(' ').replace(/\s+/g,' ').trim():null).filter(Boolean).slice(0,4);
      throw Error(`OpenCourant Starter 未通过模型检查（退出码 ${starterCode}）。${errors.join('；')||'请检查材料参数与网格。'}`);
    }
    progress('solving',0);
    const ENGINE_LINE=/NC=\s*(\d+)\s+T=\s*([-+0-9.Ee]+)\s+DT=\s*([-+0-9.Ee]+)/;
    let lastTime=0,cycles=0;
    // The Engine listing is block-buffered; written animation frames give a reliable
    // progress estimate in between.
    const poll=setInterval(()=>{fs.readdir(work).then(names=>{
      const written=names.filter(name=>/^blast2dA\d{3,}$/.test(name)).length,t=Math.max(0,written-1)*animDt;
      if(t>lastTime){lastTime=t;progress('solving',.9*Math.min(1,t/s.duration),{time:t});}
    }).catch(()=>{});},2000);
    const {code:engineCode,termination:interruption}=await B3.execute(exec('engine_win64.exe'),['-i','blast2d_0001.rad','-nt',String(threads),...dylib],{cwd:work,env,signal:options.signal,timeoutMs:remaining(),log:{write(){}},captureStop:true,onLine:line=>{
      const m=line.match(ENGINE_LINE);
      if(m){const t=Number(m[2]);cycles=Number(m[1]);if(Number.isFinite(t)&&t>=lastTime){lastTime=t;progress('solving',.9*Math.min(1,t/s.duration),{time:t,completedSteps:cycles});}}
    }}).finally(()=>clearInterval(poll));
    if(interruption?.code==='timeout')interruption.message=`二维爆破计算超过 ${s.timeLimitSeconds} 秒。`;
    const engineOut=await fs.readFile(path.join(work,'blast2d_0001.out'),'latin1').catch(()=>'');
    const normal=/NORMAL TERMINATION/i.test(engineOut);
    // Cycle count from the Engine listing (the last cycle/time/time-step row).
    for(const m of engineOut.matchAll(/^\s+(\d+)\s+[-+0-9.E]+\s+[-+0-9.E]+\s+[A-Z]+\s+\d+/gm))cycles=Math.max(cycles,Number(m[1]));
    // Rows are printed only every 500 cycles; the final summary carries the exact count.
    const total=engineOut.match(/TOTAL NUMBER OF CYCLES\s*:\s*(\d+)/);if(total)cycles=Math.max(cycles,Number(total[1]));
    const animations=(await fs.readdir(work)).filter(name=>/^blast2dA\d{3,}$/.test(name)).sort();
    if(!animations.length)throw Error(interruption?.message||`OpenCourant Engine 没有输出动画帧（退出码 ${engineCode}）。${(engineOut.match(/ERROR[^\n]*/g)||[]).slice(0,2).join('；')}`);
    // Time histories: global energies and the borehole-gas part energies.
    const thText=async name=>{await B3.execute(exec('th_to_csv_win64.exe'),[name],{cwd:work,env,timeoutMs:120000,log:{write(){}}});return fs.readFile(path.join(work,name+'.csv'),'latin1').catch(()=>null);};
    const globalText=await thText('blast2dT01').catch(()=>null);
    const th=globalText?readThCsv(globalText):null;
    // Part histories (T01 also carries /TH/PART columns; th_to_csv names them by part).
    const result=await convertFrames(work,exec,env,d,pre,th,animations,options,progress);
    const lastTimeSaved=result.times.at(-1)??0,reached=result.frames.length>0&&lastTimeSaved>=s.duration-.5*animDt;
    const completed=normal&&reached&&!result.diverged&&!interruption&&!result.frameError;
    if(!result.frames.length)throw Error(interruption?.message||result.frameError?.message||'OpenCourant 计算从第一帧起发散，请检查材料参数、网格质量和载荷。');
    const dtColumn=th?th.col('TIME STEP'):-1,dtValues=dtColumn>=0?th.data.map(r=>r[dtColumn]).filter(v=>v>0):[];
    const termination=completed?null:interruption||{code:engineCode,message:result.frameError?.message||(result.diverged?`第 ${result.frames.length+1} 帧起数值发散，只保留此前 ${result.frames.length} 帧。`
      :!normal?'OpenCourant Engine 未正常结束，只保留已经输出的帧。'
      :`OpenCourant Engine 在 ${(lastTimeSaved*1e6).toFixed(2)} μs 提前停止（通常为单元严重畸变或翻转），未达到设定时长。`)};
    const metadata={solver:SOLVER,solverBackend:'OpenCourant',prestressSolver:pre?'MFEM 4.10':null,meshMapping:'TRI3 -> 3 x QUAD4 (centroid + edge midpoints)',
      nodeCount:d.mesh.N,elementCount:d.mesh.tris.length,quadElements:d.mesh.quads.length,aleElements:d.aleCells.length,solverNodes:d.totalNodes,
      frameCount:result.frames.length,requestedFrames:frames,cellScalarCount:10,frameScalarCount:s.sourceMode===1?12:8,
      dt:dtValues.length?[...dtValues].sort((a,b)=>a-b)[dtValues.length>>1]:0,dtMin:dtValues.reduce((a,b)=>Math.min(a,b),Infinity),dtMax:dtValues.reduce((a,b)=>Math.max(a,b),0),steps:cycles,stepCountIsEstimate:false,planeMode:1,sourceMode:s.sourceMode,
      productEOS:s.productEOS,airEOS:s.airEOS,effectiveProductGamma:s.productEOS===1?1+s.jwlOmega:s.productGamma,
      initialGasEnergy:result.initialGasEnergy,preloadEnergy:pre?pre.energy:0,preloadIterations:pre?.iterations??0,preloadGauges:pre?.gauges??0,
      loadedEdges:d.bnd.wall.length,absorbingEdges:d.absorbingEdges,fixedBoundaryEdges:d.fixedEdges,loadedNodes:d.loadedNodes,
      materials:[...d.materials.entries()].map(([no,m])=>({materialNo:no,law:m.law,card:m.lines[0],source:m.source||'material'})),source:d.source,warnings:d.warnings,
      completed,termination,elapsedSeconds:(Date.now()-started)/1000,solverInputUnits:'m-kg-s-Pa-J'};
    progress(completed?'complete':'partial',1);
    return {metadata,frames:result.frames};
  }catch(error){
    if(process.env.TENSORA_KEEP_BLAST2D_WORK)error.message+=`（作业目录 ${work}）`;
    throw error;
  }finally{
    await fs.unlink(runtime).catch(()=>{});
    if(!process.env.TENSORA_KEEP_BLAST2D_WORK)await fs.rm(work,{recursive:true,force:true,maxRetries:3}).catch(()=>{});
  }
}

const pick=(data,names)=>{const keys=Object.keys(data),norm=k=>k.toLowerCase().replace(/^[23]delem_/,'').replace(/_+$/,'');
  for(const name of names){const hit=keys.find(k=>norm(k)===name.toLowerCase());if(hit)return data[hit];}return null;};

async function convertFrames(work,exec,env,d,pre,th,animations,options,progress){
  const {mesh,s}=d,{N,tris,quads,quadParent,quadArea,PX,PY}=mesh,E=tris.length,nq=quads.length;
  const gas=s.sourceMode===1;
  const frames=[],times=[];let diverged=false,baseline=null,initialGasEnergy=0,frameError=null;
  const col=name=>th?th.col(name):-1;
  // Gas part energies: th_to_csv lists part blocks after the global block.
  const gasIe=th?th.head.map((h,i)=>/^borehole gas .*\sIE$/.test(h)?i:-1).filter(i=>i>=0):[];
  const gasKe=th?th.head.map((h,i)=>/^borehole gas .*\sKE$/.test(h)?i:-1).filter(i=>i>=0):[];
  const gasEnergy=(cols,t)=>cols.reduce((sum,c)=>sum+interpolate(th,c,t),0);
  const damageSource=tris.map(tri=>{const m=d.materials.get(tri.materialNo);return m.damage??(m.law==='jh2'?'damg':null);});
  const quadMass=new Float64Array(PX.length);
  quads.forEach((q,k)=>{const m=d.materials.get(tris[quadParent[k]].materialNo);for(const n of q)quadMass[n]+=m.rho*quadArea[k]/4;});
  // anim_to_vtk conversions run a few frames ahead of the (sequential) parsing.
  const convert=async name=>{
    const vtkName=name+'.vtk',stream=(await fs.open(path.join(work,vtkName),'w')).createWriteStream();
    let code;try{code=await B3.execute(exec('anim_to_vtk_win64.exe'),[name],{cwd:work,env,timeoutMs:10*60*1000,log:stream});}
    finally{await new Promise(resolve=>stream.end(resolve));}
    if(code!==0)throw Error('anim_to_vtk 转换失败：'+name);
    return vtkName;
  };
  const pendingVtk=new Map(),AHEAD=4;
  const schedule=k=>{if(k<animations.length&&!pendingVtk.has(k)){const job=convert(animations[k]);job.catch(()=>{});pendingVtk.set(k,job);}};
  for(let k=0;k<animations.length;k++){
    try{
      for(let j=k;j<=k+AHEAD;j++)schedule(j);
      const vtkName=await pendingVtk.get(k);pendingVtk.delete(k);
      const vtk=await B3.readVtk(path.join(work,vtkName));await fs.rm(path.join(work,vtkName),{force:true});
      const ids=vtk.pointData.NODE_ID?.values,disp=pick(vtk.pointData,['Displacement']),vel=pick(vtk.pointData,['Velocity']);
      if(!ids||!disp||!vel)throw Error('anim_to_vtk 输出缺少节点位移或速度。');
      const ux=new Float64Array(PX.length),uy=new Float64Array(PX.length),vx=new Float64Array(PX.length),vy=new Float64Array(PX.length);
      for(let p=0;p<ids.length;p++){const i=ids[p]-1;if(i<0||i>=PX.length)continue;ux[i]=disp.values[3*p];uy[i]=disp.values[3*p+1];vx[i]=vel.values[3*p];vy[i]=vel.values[3*p+1];}
      const cellIds=pick(vtk.cellData,['ELEMENT_ID'])?.values;if(!cellIds)throw Error('anim_to_vtk 输出缺少单元编号。');
      const field=name=>pick(vtk.cellData,[name])?.values;
      // Bricks: symmetric 3x3 stress tensor, row-major (xx xy xz / yx yy yz / zx zy zz).
      const tensor=pick(vtk.cellData,['Stress']),dmgField=field('Damage'),usr3=field('User_Var_3'),epsp=field('Plastic_Strain'),pr=field('Pressure');
      if(!tensor||tensor.width!==9)throw Error('anim_to_vtk 输出缺少单元应力张量。');
      const T=tensor.values;
      const at=new Int32Array(nq+d.aleCells.length).fill(-1);for(let c=0;c<cellIds.length;c++){const q=cellIds[c]-1;if(q>=0&&q<at.length)at[q]=c;}
      const time=Number.isFinite(vtk.time)?vtk.time:k*s.duration/(s.frames-1);
      // /RUN ends half an output interval after the requested time; drop the closing dump.
      if(time>s.duration+.25*s.duration/(s.frames-1))continue;
      // Triangle averages of the three sub-quads.
      const cells=new Float64Array(E*10);let maxStress=0,maxDynamic=0;
      const triStress=new Float64Array(E*4);
      for(let t=0;t<E;t++){
        let w=0,a=0,b=0,c=0,sh=0,dm=0,ep=0;
        const dmg=damageSource[t]==='usr3'?usr3:damageSource[t]==='damg'?dmgField:null;
        for(let j=0;j<3;j++){const q=3*t+j,cc=at[q];if(cc<0)continue;const A=quadArea[q];w+=A;a+=A*T[9*cc];b+=A*T[9*cc+4];c+=A*T[9*cc+8];sh+=A*T[9*cc+1];if(dmg)dm+=A*dmg[cc];if(epsp)ep+=A*epsp[cc];}
        if(w>0){a/=w;b/=w;c/=w;sh/=w;dm/=w;ep/=w;}
        const strain=triangleStrain(mesh,ux,uy,tris[t],t);
        cells.set([strain[0],strain[1],strain[2],a,b,sh,Math.min(1,Math.max(0,dm)),c,ep,0],10*t);triStress.set([a,b,c,sh],4*t);
        const eq=(x,y,z,q)=>Math.sqrt(Math.max(0,((x-y)**2+(y-z)**2+(z-x)**2)/2+3*q*q));
        maxStress=Math.max(maxStress,eq(a,b,c,sh));
        if(baseline)maxDynamic=Math.max(maxDynamic,eq(a-baseline[4*t],b-baseline[4*t+1],c-baseline[4*t+2],sh-baseline[4*t+3]));
      }
      if(!baseline)baseline=triStress;
      let kinetic=0;for(let i=0;i<PX.length;i++)if(quadMass[i])kinetic+=.5*quadMass[i]*(vx[i]**2+vy[i]**2);
      // Wall pressure: area-weighted gas pressure of the ALE cells touching the wall (gas mode),
      // or the prescribed wall pressure history.
      let wallPressure=s.sourceMode===0?(time<s.pulse?s.pressure*Math.sin(Math.PI*time/s.pulse):0):0;
      if(gas&&pr){let w=0,p=0;const wall=new Set(d.loop);d.aleCells.forEach((cell,j)=>{if(!cell.some(n=>wall.has(n)))return;const cc=at[nq+j];if(cc<0)return;const A=Math.abs(polygonArea(cell.map(n=>[PX[n],PY[n]])));w+=A;p+=A*pr[cc];});if(w>0)wallPressure=p/w;}
      const u=new Float64Array(2*N),v=new Float64Array(2*N);
      for(let i=0;i<N;i++){u[2*i]=ux[i];u[2*i+1]=uy[i];v[2*i]=vx[i];v[2*i+1]=vy[i];}
      const finite=Number.isFinite(maxStress)&&u.every(Number.isFinite)&&v.every(Number.isFinite)&&cells.every(Number.isFinite);
      let largest=0;for(let i=0;i<u.length;i++)largest=Math.max(largest,Math.abs(u[i]));
      if(!finite||largest>1e3){diverged=true;break;}
      // Slab energies -> per unit thickness.
      const H=d.thickness,internal=interpolate(th,col('INTERNAL ENERGY'),time)/H,external=interpolate(th,col('EXTERNAL WORK'),time)/H,hourglass=interpolate(th,col('HOURGLASS ENERGY'),time)/H;
      const gasIE=gasEnergy(gasIe,time)/H,gasKE=gasEnergy(gasKe,time)/H;
      if(k===0)initialGasEnergy=gasIE+gasKE;
      const scalars=[time,wallPressure,kinetic,internal-gasIE+(pre?pre.energy:0),external,hourglass,maxStress,maxDynamic];
      if(gas){
        const area=Math.abs(polygonArea(d.loop.map(n=>[PX[n]+ux[n],mesh.PY[n]+uy[n]])));
        scalars.push(gasIE,gasKE,initialGasEnergy-gasIE-gasKE,Math.sqrt(area/Math.PI));
      }
      const raw=Buffer.alloc((scalars.length+4*N+10*E)*8);let o=0;
      for(const x of scalars){raw.writeDoubleLE(Number.isFinite(x)?x:0,o);o+=8;}
      Buffer.from(u.buffer).copy(raw,o);o+=u.byteLength;Buffer.from(v.buffer).copy(raw,o);o+=v.byteLength;Buffer.from(cells.buffer).copy(raw,o);
      frames.push(raw);times.push(time);
      progress('saving',.9+.1*(k+1)/animations.length,{savedFrames:k+1,totalFrames:animations.length});
      await options.onFrame?.(raw,k);
    }catch(error){frameError=error;break;}
  }
  await Promise.allSettled(pendingVtk.values());
  return {frames,times,diverged,initialGasEnergy,frameError};
}

module.exports={runBlast2d,buildDecks,buildMesh,classifyBoundary,normalizeSettings,available,volumetricStrain,chargeFraction,triangleStrain,SOLVER};
