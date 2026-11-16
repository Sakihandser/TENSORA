'use strict';
// Builds the neutral FSI model {dimension,nodes,cells,cellRoles,cellMaterials,
// materials,boundaries,fixed} from the 2D drawing payload or the 3D CAD mesh,
// and turns the existing displacement restraints into solid boundary markers.
const solid3d=require('./solid3d');

const key=nodes=>[...nodes].sort((a,b)=>a-b).join(',');

// Solid boundary faces whose nodes are all fully restrained become "clamped";
// faces restrained in one common direction become "roller" (symmetry) faces.
function restraintBoundaries(model){
  const {dimension,cells,cellRoles,fixed}=model;
  if(!fixed)return [];
  const isFixed=(n,d)=>fixed[n*dimension+d]===1||fixed[n*dimension+d]===true;
  const counts=new Map();
  cells.forEach((cell,i)=>{
    if(cellRoles[i]!=='solid'&&cellRoles[i]!=='fluid')return;
    const faces=dimension===2?[[cell[0],cell[1]],[cell[1],cell[2]],[cell[2],cell[0]]]
      :[[cell[0],cell[1],cell[2]],[cell[0],cell[1],cell[3]],[cell[0],cell[2],cell[3]],[cell[1],cell[2],cell[3]]];
    for(const f of faces){const k=key(f);const e=counts.get(k)||{face:f,roles:[]};e.roles.push(cellRoles[i]);counts.set(k,e);}
  });
  const groups={fix_all:[],fix_x:[],fix_y:[],fix_z:[]};
  for(const {face,roles} of counts.values()){
    // Exterior solid faces and fluid–solid interface faces (a clamped root on
    // the wetted surface); faces between two solid cells are interior.
    if(!roles.includes('solid')||roles.length!==1&&roles.every(r=>r==='solid'))continue;
    const axes=[...Array(dimension).keys()].filter(d=>face.every(n=>isFixed(n,d)));
    if(axes.length===dimension)groups.fix_all.push(face);
    else if(axes.length===1)groups[['fix_x','fix_y','fix_z'][axes[0]]].push(face);
  }
  return Object.entries(groups).filter(([,faces])=>faces.length).map(([name,faces])=>({name,faces,kind:name==='fix_all'?'clamped':'roller'}));
}

// 3D: the shared tetrahedral mesh, volume materials and restraints of the 3D workspace.
function fromSolid(solid,settings){
  const mesh=solid?.mesh;
  if(!Array.isArray(mesh?.nodes)||!Array.isArray(mesh?.tets)||!mesh.tets.length||!Array.isArray(mesh.surfaces))throw Error('请先在三维“计算”页生成四面体网格。');
  const roles=settings?.volumeRoles||{};
  const library=new Map((solid.settings?.materials||[]).map(m=>[String(m.id),m]));
  const cellRoles=mesh.tets.map((_,i)=>{const r=roles[String(mesh.tetVolumes[i])]||'solid';return r==='fluid'||r==='solid'?r:'void';});
  const cellMaterials=mesh.tets.map((_,i)=>cellRoles[i]==='solid'?String(solid.settings?.volumeMaterials?.[mesh.tetVolumes[i]]??''):null);
  const materials={};
  for(const id of new Set(cellMaterials.filter(Boolean))){
    const m=library.get(id);
    if(!m)throw Error('结构体域尚未指定材料，请在三维计算页为结构体域分配材料。');
    materials[id]={name:m.name,E:Number(m.elasticModulus)*1e9,nu:Number(m.poissonRatio),density:Number(m.density)};
  }
  // Restraints are resolved by the 3D workspace's own condition assembly.
  const conditions=(solid.settings?.conditions||[]).filter(bc=>/^fixed/.test(bc.type));
  const {fixed}=solid3d.assembleLoads(mesh,conditions,()=>({material:null}),null,{requireLoad:false,requireRestraint:false});
  const boundaries=mesh.surfaces.map(surface=>({name:`S${surface.id}`,faces:surface.triangles}));
  return {dimension:3,nodes:mesh.nodes,cells:mesh.tets,cellRoles,cellMaterials,materials,boundaries,fixed};
}

// Final model + settings with restraint markers merged in.
function prepare(payload){
  const settings={...(payload?.settings||{})};
  const model=payload?.solid?fromSolid(payload.solid,settings):payload?.model;
  if(!model)throw Error('缺少流固耦合模型。');
  const restraints=restraintBoundaries(model);
  // Restraint faces take precedence over user boundary names on the same face.
  const taken=new Set(restraints.flatMap(r=>r.faces.map(key)));
  model.boundaries=[...(model.boundaries||[]).map(b=>({...b,faces:(b.faces||[]).filter(f=>!taken.has(key(f)))})),...restraints.map(({name,faces})=>({name,faces}))];
  settings.boundaries={...(settings.boundaries||{})};
  for(const r of restraints)settings.boundaries[r.name]={kind:r.kind};
  return {model,settings};
}

module.exports={prepare,fromSolid,restraintBoundaries};
