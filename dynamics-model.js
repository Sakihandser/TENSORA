'use strict';
// Converts the shared 2D (TRI3 direct model) or 3D (Gmsh TET4 mesh + CAD conditions)
// model into one neutral form for the dynamics adapters. Loads and restraints reuse
// the existing assemblies (2D: calculation export; 3D: solid3d.assembleLoads).
const {assembleLoads,tetData}=require('./solid3d');
const DynamicsSettings=require('./dynamics-settings');

const {LIMITS}=DynamicsSettings;
const finite=v=>Number.isFinite(Number(v));

function checkMaterial(m){
  if(!(m.E>0))throw Error(`${m.name}：弹性模量必须大于零。`);
  if(!(m.nu>-1&&m.nu<.5))throw Error(`${m.name}：泊松比须在 -1 与 0.5 之间。`);
}

function from3d(solid){
  const mesh=solid?.mesh,settings=solid?.settings||{};
  if(!Array.isArray(mesh?.nodes)||!mesh.nodes.length||!Array.isArray(mesh.tets)||!mesh.tets.length)throw Error('请先在“计算”页生成四面体网格。');
  if(mesh.nodes.length>LIMITS.nodes||mesh.tets.length>LIMITS.elements)throw Error(`动力学模块最多支持 ${LIMITS.nodes.toLocaleString()} 节点 / ${LIMITS.elements.toLocaleString()} 单元。`);
  const library=new Map((settings.materials||[]).map(m=>[String(m.id),m]));
  const materials=[],indexOf=new Map();
  const elementMaterial=new Int32Array(mesh.tets.length);
  const materialFor=new Map();
  const resolve=i=>{
    const volume=String(mesh.tetVolumes?.[i]??'0');
    if(materialFor.has(volume))return materialFor.get(volume);
    const raw=library.get(String(settings.volumeMaterials?.[volume]));
    if(!raw)throw Error(`体域 ${volume} 尚未指定材料。`);
    const id=String(raw.id);
    if(!indexOf.has(id)){
      const m={id,name:raw.name||id,E:Number(raw.elasticModulus)*1e9,nu:Number(raw.poissonRatio),rho:Number(raw.density)||0,
        yieldStrength:Number(raw.yieldStrength)>0?Number(raw.yieldStrength)*1e6:0,color:raw.color||null};
      checkMaterial(m);indexOf.set(id,materials.length);materials.push(m);
    }
    const entry={index:indexOf.get(id),material:raw};
    materialFor.set(volume,entry);
    return entry;
  };
  mesh.tets.forEach((_,i)=>{elementMaterial[i]=resolve(i).index;});
  const {force,fixed}=assembleLoads(mesh,settings.conditions||[],i=>({material:resolve(i).material}),null,{requireLoad:false,requireRestraint:false});
  const elements=mesh.tets.map(tet=>{
    const e=[...tet];
    if(tetData(e.map(n=>mesh.nodes[n])).orientation<0)[e[1],e[2]]=[e[2],e[1]];
    return e;
  });
  return {dimension:3,coords:mesh.nodes.map(p=>[p[0],p[1],p[2]]),elements,elementMaterial,materials,force,fixed,
    volumes:mesh.tets.map((_,i)=>String(mesh.tetVolumes?.[i]??'0'))};
}

function from2d(model){
  const nodes=model?.nodes,elements=model?.elements;
  if(!Array.isArray(nodes)||!nodes.length||!Array.isArray(elements)||!elements.length)throw Error('请先在基础计算页划分网格。');
  if(nodes.length>LIMITS.nodes||elements.length>LIMITS.elements)throw Error(`动力学模块最多支持 ${LIMITS.nodes.toLocaleString()} 节点 / ${LIMITS.elements.toLocaleString()} 单元。`);
  const index=new Map();
  const coords=nodes.map((n,i)=>{
    if(!Number.isSafeInteger(n.nodeNo)||index.has(n.nodeNo)||!finite(n.x)||!finite(n.y))throw Error('节点编号或坐标无效。');
    index.set(n.nodeNo,i);return [Number(n.x),Number(n.y),0];
  });
  const force=new Float64Array(nodes.length*3),fixed=new Uint8Array(nodes.length*3);
  nodes.forEach((n,i)=>{
    force[i*3]=Number(n.forceX)||0;force[i*3+1]=Number(n.forceY)||0;
    fixed[i*3]=n.fixUx?1:0;fixed[i*3+1]=n.fixUy?1:0;
  });
  const byNo=new Map((model.materials||[]).map(m=>[m.materialNo,m]));
  const materials=[],indexOf=new Map();
  const elementMaterial=new Int32Array(elements.length);
  const list=elements.map((e,k)=>{
    const ids=[e.node1,e.node2,e.node3].map(no=>{const i=index.get(no);if(i===undefined)throw Error('单元引用不存在的节点。');return i;});
    if(new Set(ids).size!==3)throw Error('存在退化三角形。');
    const [a,b,c]=ids.map(i=>coords[i]);
    const area=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);
    if(Math.abs(area)<1e-20)throw Error('存在退化三角形。');
    if(area<0)[ids[1],ids[2]]=[ids[2],ids[1]];
    const base=byNo.get(e.materialNo)||{};
    const id=String(base.id??e.materialNo??'legacy');
    if(!indexOf.has(id)){
      const m={id,name:base.name||`材料 ${e.materialNo}`,E:Number(e.elasticModulus),nu:Number(e.poissonRatio),
        rho:Number(base.density??e.density)||0,yieldStrength:Number(base.yieldStrength??e.yieldStrength)||0,materialNo:e.materialNo};
      checkMaterial(m);indexOf.set(id,materials.length);materials.push(m);
    }
    const m=materials[indexOf.get(id)];
    if(Math.abs(Number(e.elasticModulus)-m.E)>1e-9*m.E||Math.abs(Number(e.poissonRatio)-m.nu)>1e-12)throw Error(`${m.name}：同一材料的单元弹性参数不一致。`);
    elementMaterial[k]=indexOf.get(id);
    return ids;
  });
  return {dimension:2,coords,elements:list,elementMaterial,materials,force,fixed,nodeNo:nodes.map(n=>n.nodeNo),
    elementNo:elements.map(e=>e.elementNo),source:model};
}

function fromPayload(payload){
  return payload?.solid?from3d(payload.solid):from2d(payload?.model);
}

// Bounding box diagonal and lumped total mass (for reports and checks).
function modelStats(m,thickness=1){
  const lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];
  for(const p of m.coords)for(let d=0;d<3;d++){lo[d]=Math.min(lo[d],p[d]);hi[d]=Math.max(hi[d],p[d]);}
  let mass=0,minEdge=Infinity;
  m.elements.forEach((e,k)=>{
    const p=e.map(i=>m.coords[i]);
    const size=m.dimension===3?Math.abs(tetData(p).volume)
      :Math.abs((p[1][0]-p[0][0])*(p[2][1]-p[0][1])-(p[1][1]-p[0][1])*(p[2][0]-p[0][0]))/2*thickness;
    mass+=size*m.materials[m.elementMaterial[k]].rho;
    for(let a=0;a<e.length;a++)for(let b=a+1;b<e.length;b++)minEdge=Math.min(minEdge,Math.hypot(p[a][0]-p[b][0],p[a][1]-p[b][1],p[a][2]-p[b][2]));
  });
  return {lo,hi,diagonal:Math.hypot(hi[0]-lo[0],hi[1]-lo[1],hi[2]-lo[2]),mass,minEdge};
}

module.exports={fromPayload,from2d,from3d,modelStats};
