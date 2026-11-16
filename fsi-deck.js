'use strict';
// Fluid–structure interaction inputs. TENSORA only splits the shared mesh into
// a fluid zone and a solid zone, names the boundary markers and writes the
// options of the upstream solvers:
//   * SU2 8.6 multizone driver (SOLVER= MULTIPHYSICS): finite-volume flow,
//     FEA structure, mesh deformation and the block Gauss–Seidel coupling;
//   * MFEM 4.10 one-way driver: elasticity under the SU2 wall pressure and
//     friction (see TensoraCore/MfemFsi/mfem_fsi.cpp).
// No flow, structural or coupling equations are evaluated here.

const BOUNDARY_KINDS=['inlet','outlet','wall','slip','farfield'];
const SOLID_KINDS=['clamped','roller'];
const LIMITS={nodes:400000,cells:1500000,steps:20000,outer:200,frames:201};

const finite=(value,name,{min=-Infinity,max=Infinity,positive=false}={})=>{
  const v=Number(value);
  if(!Number.isFinite(v)||v<min||v>max||(positive&&!(v>0)))throw Error(`${name} 输入无效。`);
  return v;
};
const integer=(value,name,min,max)=>{
  const v=Number(value);
  if(!Number.isSafeInteger(v)||v<min||v>max)throw Error(`${name}须为 ${min}–${max} 的整数。`);
  return v;
};
const pick=(value,allowed,fallback)=>allowed.includes(value)?value:fallback;
const key=nodes=>[...nodes].sort((a,b)=>a-b).join(',');
const fmt=v=>Number(v).toPrecision(15).replace(/\.?0+(e|$)/,'$1');

// ------------------------------------------------------------------ fluids
function normalizeFluid(raw){
  if(!raw||typeof raw!=='object')throw Error('请选择流体材料。');
  const model=pick(raw.model,['incompressible','idealgas'],'incompressible');
  const fluid={id:String(raw.id||''),name:String(raw.name||'流体').slice(0,160),model,
    density:finite(raw.density,'流体密度',{positive:true}),
    viscosity:finite(raw.viscosity,'动力黏度',{min:0})};
  if(model==='idealgas'){
    fluid.gamma=finite(raw.gamma??1.4,'比热比 γ',{min:1.0001,max:3});
    fluid.gasConstant=finite(raw.gasConstant??287.058,'气体常数 R',{positive:true});
    fluid.temperature=finite(raw.temperature??288.15,'参考温度',{positive:true});
  }
  if(raw.bulkModulus!=null&&raw.bulkModulus!=='')fluid.bulkModulus=finite(raw.bulkModulus,'体积模量',{positive:true});
  return fluid;
}

// ------------------------------------------------------------- settings
const DEFAULTS={engine:'su2',analysis:'steady',structure:'linear',plane:'strain',turbulence:'none',
  outerIterations:40,fluidIterations:40,solidIterations:10,relaxation:'aitken',relaxationFactor:0.5,
  timeStep:1e-3,steps:100,frames:41,threads:4,convergence:-6,referencePressure:101325,interpolation:'nearest'};

function normalizeSettings(raw={},dimension){
  const s={...DEFAULTS,...raw};
  const out={
    engine:pick(s.engine,['su2','oneway'],'su2'),
    analysis:pick(s.analysis,['steady','transient'],'steady'),
    structure:pick(s.structure,['linear','neohookean'],'linear'),
    plane:pick(s.plane,['strain','stress'],'strain'),
    turbulence:pick(s.turbulence,['none','sa','sst'],'none'),
    relaxation:pick(s.relaxation,['aitken','fixed'],'aitken'),
    relaxationFactor:finite(s.relaxationFactor,'松弛因子',{min:0.01,max:1}),
    outerIterations:integer(s.outerIterations,'耦合迭代次数',1,LIMITS.outer),
    fluidIterations:integer(s.fluidIterations,'流体内迭代次数',1,100000),
    solidIterations:integer(s.solidIterations,'结构内迭代次数',1,1000),
    timeStep:finite(s.timeStep,'时间步长',{positive:true}),
    steps:integer(s.steps,'时间步数',1,LIMITS.steps),
    frames:integer(s.frames,'保存帧数',2,LIMITS.frames),
    threads:integer(s.threads,'CPU 线程数',1,64),
    convergence:finite(s.convergence,'收敛判据',{min:-16,max:0}),
    referencePressure:finite(s.referencePressure,'参考压力',{min:0}),
    dimension
  };
  if(out.engine==='oneway')out.analysis='steady';
  if(out.analysis==='steady'){
    if(s.flowCfl!=null)out.flowCfl=finite(s.flowCfl,'流体 CFL',{positive:true});
    if(s.flowFirstOrder===true)out.flowFirstOrder=true;
  }
  out.boundaries={};
  for(const [name,value] of Object.entries(s.boundaries||{})){
    if(!/^[A-Za-z0-9_-]{1,40}$/.test(name))throw Error('边界名称无效：'+name);
    const kind=pick(value?.kind,[...BOUNDARY_KINDS,...SOLID_KINDS],null);
    if(!kind)throw Error(`边界 ${name} 的类型无效。`);
    const b={kind};
    if(kind==='inlet'||kind==='farfield'){
      b.velocity=finite(value.velocity,`边界 ${name} 的流速`,{min:0});
      if(kind==='farfield'||Array.isArray(value.direction)){
        const dir=(value.direction||[1,0,0]).slice(0,3).map((v,i)=>finite(v??0,`边界 ${name} 的方向分量 ${i+1}`));
        const length=Math.hypot(...dir);
        if(!(length>0))throw Error(`边界 ${name} 的流动方向不能为零向量。`);
        b.direction=dir.map(v=>v/length);
      }
    }
    if(kind==='outlet')b.pressure=finite(value.pressure??0,`边界 ${name} 的出口压力`);
    out.boundaries[name]=b;
  }
  return out;
}

// --------------------------------------------------------------- mesh split
function cellFaces(cell,dimension){
  if(dimension===2){const [a,b,c]=cell;return [[a,b,c],[b,c,a],[c,a,b]];}   // [face..., opposite]
  const [a,b,c,d]=cell;return [[a,b,c,d],[a,b,d,c],[a,c,d,b],[b,c,d,a]];
}

// model: {dimension,nodes,cells,cellRoles('fluid'|'solid'),cellMaterials,boundaries:[{name,faces}]}
function splitMesh(model){
  const dimension=Number(model?.dimension);
  if(dimension!==2&&dimension!==3)throw Error('流固耦合模型维度须为 2 或 3。');
  const per=dimension===2?3:4,nodes=model.nodes,cells=model.cells,roles=model.cellRoles;
  if(!Array.isArray(nodes)||!nodes.length||nodes.length>LIMITS.nodes)throw Error(`节点数须在 1–${LIMITS.nodes} 之间。`);
  if(!Array.isArray(cells)||!cells.length||cells.length>LIMITS.cells)throw Error(`单元数须在 1–${LIMITS.cells} 之间。`);
  if(!Array.isArray(roles)||roles.length!==cells.length)throw Error('单元角色数量与单元数不一致。');
  for(const p of nodes)if(!Array.isArray(p)||p.length<dimension||p.slice(0,dimension).some(v=>!Number.isFinite(v)))throw Error('节点坐标无效。');
  for(const c of cells)if(!Array.isArray(c)||c.length!==per||c.some(n=>!Number.isSafeInteger(n)||n<0||n>=nodes.length)||new Set(c).size!==per)throw Error('单元节点编号无效。');
  const fluidCells=[],solidCells=[];
  roles.forEach((role,i)=>{if(role==='fluid')fluidCells.push(i);else if(role==='solid')solidCells.push(i);});
  if(!fluidCells.length)throw Error('模型中没有流体区域。请在流固耦合设置中把至少一个区域设为“流体”。');
  if(!solidCells.length)throw Error('模型中没有结构区域。请把至少一个区域设为“结构”。');
  // Faces with their owning cells.
  const faces=new Map();
  cells.forEach((cell,i)=>{
    if(roles[i]!=='fluid'&&roles[i]!=='solid')return;
    for(const f of cellFaces(cell,dimension)){
      const face=f.slice(0,dimension),k=key(face);
      let entry=faces.get(k);
      if(!entry){entry={nodes:face,owners:[],opposite:f[dimension]};faces.set(k,entry);}
      entry.owners.push(i);
    }
  });
  const named=new Map();
  for(const b of model.boundaries||[]){
    if(!/^[A-Za-z0-9_-]{1,40}$/.test(String(b?.name)))throw Error('边界名称无效。');
    for(const f of b.faces||[])if(Array.isArray(f)&&f.length===dimension)named.set(key(f),String(b.name));
  }
  const fluidMarkers=new Map(),solidMarkers=new Map(),interfaceFluid=[],interfaceSolid=[];
  const push=(map,name,face)=>{if(!map.has(name))map.set(name,[]);map.get(name).push(face);};
  // Boundary faces are oriented outward from the owning cell (SU2 convention).
  const orient=(entry,owner)=>{
    const face=[...entry.nodes];
    const cell=cells[owner],opp=cell.find(n=>!face.includes(n));
    if(dimension===2){
      const [a,b]=face.map(n=>nodes[n]),o=nodes[opp];
      const cross=(b[0]-a[0])*(o[1]-a[1])-(b[1]-a[1])*(o[0]-a[0]);
      if(cross<0)face.reverse();     // keep the cell on the left: outward normal points right
      return face;
    }
    const [a,b,c]=face.map(n=>nodes[n]),o=nodes[opp];
    const u=[b[0]-a[0],b[1]-a[1],b[2]-a[2]],v=[c[0]-a[0],c[1]-a[1],c[2]-a[2]];
    const n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];
    if(n[0]*(o[0]-a[0])+n[1]*(o[1]-a[1])+n[2]*(o[2]-a[2])>0)[face[1],face[2]]=[face[2],face[1]];
    return face;
  };
  let unassigned=0;
  for(const [k,entry] of faces){
    const fluidOwners=entry.owners.filter(i=>roles[i]==='fluid'),solidOwners=entry.owners.filter(i=>roles[i]==='solid');
    if(entry.owners.length>2)throw Error('网格存在非流形面，请重新生成网格。');
    if(fluidOwners.length===1&&solidOwners.length===1){
      const solidFace=orient(entry,solidOwners[0]);
      interfaceFluid.push(orient(entry,fluidOwners[0]));interfaceSolid.push(solidFace);
      // A restrained interface face is also a structural support marker.
      if(named.has(k))push(solidMarkers,named.get(k),solidFace);
      continue;
    }
    if(fluidOwners.length===1&&entry.owners.length===1){
      const name=named.get(k);
      if(!name)unassigned++;
      push(fluidMarkers,name||'wall_default',orient(entry,fluidOwners[0]));continue;
    }
    if(solidOwners.length===1&&entry.owners.length===1){
      const name=named.get(k);
      push(solidMarkers,name||'free_default',orient(entry,solidOwners[0]));
    }
  }
  if(!interfaceFluid.length)throw Error('流体区与结构区没有共享边界（流固界面）。请确认两者相邻且网格在界面处共节点。');
  const zone=list=>{
    const map=new Map(),local=[];
    for(const i of list)for(const n of cells[i])if(!map.has(n)){map.set(n,local.length);local.push(n);}
    return {map,nodes:local};
  };
  return {dimension,fluidCells,solidCells,fluid:zone(fluidCells),solid:zone(solidCells),fluidMarkers,solidMarkers,
    interfaceFluid,interfaceSolid,unassignedFluidFaces:unassigned,faceCount:faces.size};
}

// ---------------------------------------------------------- SU2 mesh files
function su2Mesh(model,split,zoneName,settings){
  const {dimension}=split,zone=split[zoneName],cellList=zoneName==='fluid'?split.fluidCells:split.solidCells;
  const markers=new Map(zoneName==='fluid'?split.fluidMarkers:split.solidMarkers);
  markers.set(zoneName==='fluid'?'fsi_fluid':'fsi_solid',zoneName==='fluid'?split.interfaceFluid:split.interfaceSolid);
  // Traction-free solid faces need no marker; SU2 rejects markers missing from the config.
  if(zoneName==='solid')for(const name of [...markers.keys()])if(name!=='fsi_solid'&&!SOLID_KINDS.includes(settings?.boundaries?.[name]?.kind))markers.delete(name);
  const cellType=dimension===2?5:10,faceType=dimension===2?3:5;
  const out=[`NDIME= ${dimension}`,`NELEM= ${cellList.length}`];
  cellList.forEach((c,i)=>{
    let nodes=model.cells[c].map(n=>zone.map.get(n));
    if(dimension===2){
      // SU2 expects counter-clockwise triangles.
      const [a,b,c2]=model.cells[c].map(n=>model.nodes[n]);
      if((b[0]-a[0])*(c2[1]-a[1])-(b[1]-a[1])*(c2[0]-a[0])<0)nodes=[nodes[0],nodes[2],nodes[1]];
    }
    out.push(`${cellType} ${nodes.join(' ')} ${i}`);
  });
  out.push(`NPOIN= ${zone.nodes.length}`);
  zone.nodes.forEach((n,i)=>out.push(`${model.nodes[n].slice(0,dimension).map(fmt).join(' ')} ${i}`));
  out.push(`NMARK= ${markers.size}`);
  for(const [name,faces] of markers){
    out.push(`MARKER_TAG= ${name}`,`MARKER_ELEMS= ${faces.length}`);
    for(const f of faces)out.push(`${faceType} ${f.map(n=>zone.map.get(n)).join(' ')}`);
  }
  return out.join('\n')+'\n';
}

// Element-based property file for multi-material structures (FEA_FILENAME).
function elementProperties(model,split){
  const ids=[],index=new Map();
  const rows=split.solidCells.map((c,i)=>{
    const id=String(model.cellMaterials?.[c]??'');
    if(!index.has(id)){index.set(id,ids.length);ids.push(id);}
    return `${i} ${index.get(id)}`;
  });
  return {ids,text:['index material',...rows].join('\n')+'\n'};
}

function solidMaterials(model,ids){
  return ids.map(id=>{
    const m=model.materials?.[id];
    if(!m)throw Error('结构区域缺少材料，请在结构绘制中为结构区域分配材料。');
    return {id,name:String(m.name||id),E:finite(m.E,`材料 ${m.name||id} 的弹性模量`,{positive:true}),
      nu:finite(m.nu,`材料 ${m.name||id} 的泊松比`,{min:0,max:0.4999}),density:finite(m.density,`材料 ${m.name||id} 的密度`,{positive:true})};
  });
}

// ------------------------------------------------------------- SU2 config
function averageNormal(model,faces,dimension){
  // Outward normal of the boundary faces (used to point inlet flow inward).
  const sum=[0,0,0];
  for(const f of faces){
    const p=f.map(n=>model.nodes[n]);
    if(dimension===2){sum[0]+=p[1][1]-p[0][1];sum[1]+=-(p[1][0]-p[0][0]);}
    else{
      const u=[0,1,2].map(k=>p[1][k]-p[0][k]),v=[0,1,2].map(k=>p[2][k]-p[0][k]);
      sum[0]+=u[1]*v[2]-u[2]*v[1];sum[1]+=u[2]*v[0]-u[0]*v[2];sum[2]+=u[0]*v[1]-u[1]*v[0];
    }
  }
  const l=Math.hypot(...sum)||1;return sum.map(v=>v/l);
}

function lines(object){return Object.entries(object).filter(([,v])=>v!==undefined&&v!==null).map(([k,v])=>`${k}= ${v}`).join('\n')+'\n';}
const tuple=values=>`( ${values.join(', ')} )`;

function flowConfig(model,split,s,fluid,{multizone=true}={}){
  const dim=split.dimension,cfg={},markers=split.fluidMarkers;
  const kinds=name=>name==='wall_default'?{kind:'wall'}:s.boundaries[name]||{kind:'wall'};
  const walls=['fsi_fluid'],slip=[],inlets=[],outlets=[],far=[];
  let reference=null;
  for(const [name,faces] of markers){
    const b=kinds(name);
    if(b.kind==='wall')walls.push(name);
    else if(b.kind==='slip')slip.push(name);
    else if(b.kind==='outlet')outlets.push([name,b.pressure]);
    else if(b.kind==='farfield'){far.push(name);reference??={velocity:b.velocity,direction:b.direction};}
    else if(b.kind==='inlet'){
      const dir=b.direction||averageNormal(model,faces,dim).map(v=>-v);
      inlets.push([name,b.velocity,dir]);
      reference??={velocity:b.velocity,direction:dir};
    }
  }
  if(!inlets.length&&!far.length)throw Error('流体区至少需要一个“速度入口”或“远场”边界。');
  if(inlets.length&&!outlets.length&&!far.length)throw Error('设置了速度入口时还需要“压力出口”或“远场”边界。');
  const speed=reference.velocity,dir=[...reference.direction,0,0].slice(0,3);
  const viscous=fluid.viscosity>0;
  const turb={none:'NONE',sa:'SA',sst:'SST'}[s.turbulence];
  if(fluid.model==='incompressible'){
    Object.assign(cfg,{SOLVER:viscous?(turb!=='NONE'?'INC_RANS':'INC_NAVIER_STOKES'):'INC_EULER',KIND_TURB_MODEL:viscous&&turb!=='NONE'?turb:undefined,
      INC_NONDIM:'DIMENSIONAL',INC_DENSITY_MODEL:'CONSTANT',INC_DENSITY_INIT:fmt(fluid.density),
      INC_VELOCITY_INIT:tuple(dir.map(v=>fmt(v*speed))),INC_ENERGY_EQUATION:'NO',
      VISCOSITY_MODEL:viscous?'CONSTANT_VISCOSITY':undefined,MU_CONSTANT:viscous?fmt(fluid.viscosity):undefined});
    if(inlets.length){
      cfg.INC_INLET_TYPE=inlets.map(()=> 'VELOCITY_INLET').join(', ');
      cfg.MARKER_INLET=tuple(inlets.flatMap(([n,v,d])=>[n,'288.15',fmt(v),...[...d,0,0].slice(0,3).map(fmt)]));
    }
    if(outlets.length){
      cfg.INC_OUTLET_TYPE=outlets.map(()=> 'PRESSURE_OUTLET').join(', ');
      cfg.MARKER_OUTLET=tuple(outlets.flatMap(([n,p])=>[n,fmt(p)]));
    }
    if(viscous&&turb==='SST'){cfg.FREESTREAM_TURBULENCEINTENSITY='0.05';cfg.FREESTREAM_TURB2LAMVISCRATIO='10';}
    if(viscous&&turb==='SA')cfg.FREESTREAM_NU_FACTOR='3';
  }else{
    const T=fluid.temperature,R=fluid.gasConstant,g=fluid.gamma,a=Math.sqrt(g*R*T),mach=speed/a;
    if(mach>=5)throw Error(`来流马赫数 ${mach.toFixed(2)} 超出本模块范围（< 5）。`);
    const p=s.referencePressure>0?s.referencePressure:fluid.density*R*T;
    // Inlet total conditions from the isentropic relations (SU2 input convention).
    const factor=1+(g-1)/2*mach*mach;
    Object.assign(cfg,{SOLVER:viscous?(turb!=='NONE'?'RANS':'NAVIER_STOKES'):'EULER',KIND_TURB_MODEL:viscous&&turb!=='NONE'?turb:undefined,
      FLUID_MODEL:'IDEAL_GAS',GAMMA_VALUE:fmt(g),GAS_CONSTANT:fmt(R),REF_DIMENSIONALIZATION:'DIMENSIONAL',
      FREESTREAM_OPTION:'TEMPERATURE_FS',FREESTREAM_PRESSURE:fmt(p),FREESTREAM_TEMPERATURE:fmt(T),INIT_OPTION:'TD_CONDITIONS',
      MACH_NUMBER:fmt(Math.max(mach,1e-6)),AOA:fmt(Math.atan2(dir[1],dir[0])*180/Math.PI),SIDESLIP_ANGLE:fmt(dim===3?Math.asin(Math.max(-1,Math.min(1,dir[2])))*180/Math.PI:0),
      VISCOSITY_MODEL:viscous?'CONSTANT_VISCOSITY':undefined,MU_CONSTANT:viscous?fmt(fluid.viscosity):undefined,
      CONDUCTIVITY_MODEL:viscous?'CONSTANT_PRANDTL':undefined,PRANDTL_LAM:viscous?'0.72':undefined,
      REYNOLDS_NUMBER:viscous?fmt(Math.max(1,fluid.density*speed/Math.max(fluid.viscosity,1e-30))):undefined,REYNOLDS_LENGTH:'1.0',
      CONV_NUM_METHOD_FLOW:'ROE',MUSCL_FLOW:'YES',SLOPE_LIMITER_FLOW:'VENKATAKRISHNAN',VENKAT_LIMITER_COEFF:'0.05'});
    if(inlets.length)cfg.MARKER_INLET=tuple(inlets.flatMap(([n,v,d])=>{
      const m=v/a,f=1+(g-1)/2*m*m;
      return [n,fmt(T*f),fmt(p*Math.pow(f,g/(g-1))),...[...d,0,0].slice(0,3).map(fmt)];
    }));
    if(outlets.length)cfg.MARKER_OUTLET=tuple(outlets.flatMap(([n,pr])=>[n,fmt(p+pr)]));
    void factor;
  }
  if(viscous)cfg.MARKER_HEATFLUX=tuple(walls.flatMap(n=>[n,'0.0']));
  else cfg.MARKER_EULER=tuple(walls);
  if(slip.length)cfg.MARKER_SYM=tuple(slip);
  if(far.length)cfg.MARKER_FAR=tuple(far);
  Object.assign(cfg,{
    MARKER_PLOTTING:tuple(['fsi_fluid']),MARKER_MONITORING:tuple(['fsi_fluid']),
    NUM_METHOD_GRAD:'WEIGHTED_LEAST_SQUARES',
    CONV_NUM_METHOD_FLOW:cfg.CONV_NUM_METHOD_FLOW||'FDS',MUSCL_FLOW:s.flowFirstOrder?'NO':'YES',SLOPE_LIMITER_FLOW:cfg.SLOPE_LIMITER_FLOW||'NONE',
    CONV_NUM_METHOD_TURB:turb!=='NONE'&&viscous?'SCALAR_UPWIND':undefined,MUSCL_TURB:turb!=='NONE'&&viscous?'NO':undefined,
    TIME_DISCRE_FLOW:'EULER_IMPLICIT',TIME_DISCRE_TURB:turb!=='NONE'&&viscous?'EULER_IMPLICIT':undefined,
    CFL_NUMBER:s.flowCfl!=null?fmt(s.flowCfl):s.analysis==='transient'?'1000':'50',
    CFL_ADAPT:s.analysis==='transient'||s.flowCfl!=null?'NO':'YES',
    CFL_ADAPT_PARAM:s.analysis==='transient'||s.flowCfl!=null?undefined:'( 0.5, 1.5, 10.0, 1e4 )',
    LINEAR_SOLVER:'FGMRES',LINEAR_SOLVER_PREC:'ILU',LINEAR_SOLVER_ERROR:'1E-4',LINEAR_SOLVER_ITER:'20',
    INNER_ITER:String(s.fluidIterations),CONV_FIELD:fluid.model==='incompressible'?'RMS_PRESSURE':'RMS_DENSITY',
    CONV_RESIDUAL_MINVAL:fmt(s.convergence),CONV_STARTITER:'0',
    MESH_FILENAME:'mesh_fluid.su2',MESH_FORMAT:'SU2',
    SCREEN_OUTPUT:'( INNER_ITER, RMS_RES )',SCREEN_WRT_FREQ_INNER:'1',
    HISTORY_OUTPUT:'( ITER, RMS_RES, AERO_COEFF )',
    VOLUME_OUTPUT:'( COORDINATES, SOLUTION, PRIMITIVE, VORTEX_IDENTIFICATION )',
    OUTPUT_FILES:'( RESTART_ASCII, PARAVIEW_ASCII, SURFACE_CSV )',TABULAR_FORMAT:'CSV',
    RESTART_FILENAME:'restart_flow',SOLUTION_FILENAME:'solution_flow',VOLUME_FILENAME:'flow',SURFACE_FILENAME:'surface_flow',CONV_FILENAME:'history_flow'
  });
  if(multizone){
    Object.assign(cfg,{DEFORM_MESH:'YES',MARKER_DEFORM_MESH:tuple(['fsi_fluid']),MARKER_ZONE_INTERFACE:tuple(['fsi_fluid','fsi_solid']),
      DEFORM_STIFFNESS_TYPE:'INVERSE_VOLUME',DEFORM_LINEAR_SOLVER:'CONJUGATE_GRADIENT',DEFORM_LINEAR_SOLVER_PREC:'ILU',
      DEFORM_LINEAR_SOLVER_ITER:'1000',DEFORM_LINEAR_SOLVER_ERROR:'1E-9',DEFORM_NONLINEAR_ITER:'1',DEFORM_CONSOLE_OUTPUT:'NO'});
    if(slip.length)cfg.MARKER_DEFORM_MESH_SYM_PLANE=tuple(slip);
  }
  if(s.analysis==='transient')Object.assign(cfg,{TIME_MARCHING:'DUAL_TIME_STEPPING-2ND_ORDER'});
  return cfg;
}

function solidConfig(model,split,s,materials){
  const cfg={SOLVER:'ELASTICITY',MATH_PROBLEM:'DIRECT',
    GEOMETRIC_CONDITIONS:s.structure==='neohookean'?'LARGE_DEFORMATIONS':'SMALL_DEFORMATIONS',
    MATERIAL_MODEL:s.structure==='neohookean'?'NEO_HOOKEAN':'LINEAR_ELASTIC',MATERIAL_COMPRESSIBILITY:'COMPRESSIBLE',
    FORMULATION_ELASTICITY_2D:s.plane==='stress'?'PLANE_STRESS':'PLANE_STRAIN',
    ELASTICITY_MODULUS:tuple(materials.map(m=>fmt(m.E))),POISSON_RATIO:tuple(materials.map(m=>fmt(m.nu))),
    MATERIAL_DENSITY:tuple(materials.map(m=>fmt(m.density))),
    FEA_FILENAME:materials.length>1?'element_properties.dat':'none_element_properties.dat',
    MARKER_FLUID_LOAD:tuple(['fsi_solid']),MARKER_ZONE_INTERFACE:tuple(['fsi_fluid','fsi_solid']),
    LINEAR_SOLVER:'CONJUGATE_GRADIENT',LINEAR_SOLVER_PREC:'ILU',LINEAR_SOLVER_ERROR:'1E-8',LINEAR_SOLVER_ITER:'5000',
    INNER_ITER:String(s.structure==='neohookean'?s.solidIterations:Math.max(1,Math.min(s.solidIterations,3))),
    CONV_FIELD:'RMS_UTOL',CONV_RESIDUAL_MINVAL:'-8',
    BGS_RELAXATION:s.relaxation==='aitken'?'AITKEN_DYNAMIC':'FIXED_PARAMETER',
    STAT_RELAX_PARAMETER:fmt(s.relaxationFactor),AITKEN_DYN_MAX_INITIAL:fmt(s.relaxationFactor),AITKEN_DYN_MIN_INITIAL:fmt(Math.min(s.relaxationFactor,0.5)),
    MESH_FILENAME:'mesh_solid.su2',MESH_FORMAT:'SU2',
    SCREEN_OUTPUT:'( INNER_ITER, RMS_RES, VMS )',HISTORY_OUTPUT:'( ITER, RMS_RES, STRUCT_COEFF )',
    VOLUME_OUTPUT:'( COORDINATES, SOLUTION, STRESS )',
    OUTPUT_FILES:'( RESTART_ASCII, PARAVIEW_ASCII )',TABULAR_FORMAT:'CSV',
    RESTART_FILENAME:'restart_solid',SOLUTION_FILENAME:'solution_solid',VOLUME_FILENAME:'solid',CONV_FILENAME:'history_solid'};
  const clamped=[],roller=[];
  for(const [name] of split.solidMarkers){
    const kind=s.boundaries[name]?.kind;
    if(kind==='clamped')clamped.push(name);else if(kind==='roller')roller.push(name);
  }
  if(!clamped.length&&!roller.length)throw Error('结构区需要固定约束：请在结构绘制中给结构边界添加固定支撑（或在三维计算页设置约束）。');
  if(clamped.length)cfg.MARKER_CLAMPED=tuple(clamped);
  if(roller.length)cfg.MARKER_SYM=tuple(roller);
  if(s.analysis==='transient')Object.assign(cfg,{TIME_DISCRE_FEA:'NEWMARK_IMPLICIT',NEWMARK_BETA:'0.2601',NEWMARK_GAMMA:'0.52'});
  return cfg;
}

function masterConfig(s){
  const cfg={SOLVER:'MULTIPHYSICS',CONFIG_LIST:'( config_flow.cfg, config_solid.cfg )',MULTIZONE_MESH:'NO',
    MULTIZONE_SOLVER:'BLOCK_GAUSS_SEIDEL',MARKER_ZONE_INTERFACE:tuple(['fsi_fluid','fsi_solid']),
    OUTER_ITER:String(s.outerIterations),CONV_RESIDUAL_MINVAL:'-8',
    TIME_DOMAIN:s.analysis==='transient'?'YES':'NO',WRT_ZONE_HIST:'YES',WRT_ZONE_CONV:'NO',
    SCREEN_OUTPUT:'( TIME_ITER, OUTER_ITER, AVG_BGS_RES[0], AVG_BGS_RES[1], DEFORM_MIN_VOLUME[0] )',
    OUTPUT_FILES:'( RESTART_ASCII, PARAVIEW_ASCII )',
    OUTPUT_WRT_FREQ:s.analysis==='transient'?String(Math.max(1,Math.floor(s.steps/(s.frames-1)))):String(s.outerIterations),
    MULTIZONE_ADAPT_FILENAME:undefined};
  if(s.analysis==='transient')Object.assign(cfg,{TIME_STEP:fmt(s.timeStep),TIME_ITER:String(s.steps),MAX_TIME:fmt(s.timeStep*s.steps*1.0001),RESTART_SOL:'NO'});
  return cfg;
}

// One-way path: SU2 runs the flow alone with rigid interface walls.
function onewayFlowConfig(model,split,s,fluid){
  const cfg=flowConfig(model,split,{...s,analysis:'steady'},fluid,{multizone:false});
  cfg.INNER_ITER=String(Math.max(s.fluidIterations,s.outerIterations*s.fluidIterations));
  return cfg;
}

function buildFsiInputs(model,rawSettings,rawFluid){
  const split=splitMesh(model);
  const settings=normalizeSettings(rawSettings,split.dimension);
  const fluid=normalizeFluid(rawFluid);
  for(const [name] of split.fluidMarkers)if(name!=='wall_default'&&settings.boundaries[name]&&!BOUNDARY_KINDS.includes(settings.boundaries[name].kind))
    throw Error(`边界 ${name} 位于流体区，只能设为入口、出口、壁面、滑移或远场。`);
  const props=elementProperties(model,split);
  const materials=solidMaterials(model,props.ids);
  const files={'mesh_fluid.su2':su2Mesh(model,split,'fluid',settings),'mesh_solid.su2':su2Mesh(model,split,'solid',settings)};
  if(materials.length>1)files['element_properties.dat']=props.text;
  if(settings.engine==='su2'){
    files['config_flow.cfg']=lines(flowConfig(model,split,settings,fluid));
    files['config_solid.cfg']=lines(solidConfig(model,split,settings,materials));
    files['config.cfg']=lines(masterConfig(settings));
  }else{
    files['config_flow.cfg']=lines(onewayFlowConfig(model,split,settings,fluid));
    solidConfig(model,split,settings,materials);   // validates the structural restraints
  }
  const meta={dimension:split.dimension,fluidCells:split.fluidCells.length,solidCells:split.solidCells.length,
    fluidNodes:split.fluid.nodes.length,solidNodes:split.solid.nodes.length,interfaceFaces:split.interfaceFluid.length,
    fluidMarkers:Object.fromEntries([...split.fluidMarkers].map(([n,f])=>[n,{faces:f.length,kind:n==='wall_default'?'wall':settings.boundaries[n]?.kind||'wall'}])),
    solidMarkers:Object.fromEntries([...split.solidMarkers].filter(([n])=>n!=='free_default').map(([n,f])=>[n,{faces:f.length,kind:settings.boundaries[n]?.kind||'free'}])),
    unassignedFluidFaces:split.unassignedFluidFaces,materials,fluid,
    compressible:fluid.model==='idealgas'};
  // Reference dynamic pressure SU2 uses for its force and skin-friction coefficients.
  let speed=0;
  for(const [name] of split.fluidMarkers){const b=settings.boundaries[name];if(b&&(b.kind==='inlet'||b.kind==='farfield')){speed=b.velocity;break;}}
  const rho=fluid.model==='idealgas'?(settings.referencePressure>0?settings.referencePressure/(fluid.gasConstant*fluid.temperature):fluid.density):fluid.density;
  meta.referenceSpeed=speed;meta.dynamicPressure=0.5*rho*speed*speed;
  return {files,split,settings,fluid,materials,meta};
}

// Solid zone for the one-way MFEM path. Boundary attributes: 1 wetted
// interface, 2 clamped, 3/4/5 roller fixing the x/y/z component (the axis
// closest to the face normal). surfaceLoads: Map(globalNode -> [p, tau...]).
function mfemInput(model,split,materials,surfaceLoads,settings){
  const {dimension}=split,zone=split.solid;
  const geom=dimension===2?2:4,bgeom=dimension===2?1:2;   // MFEM TRIANGLE/TETRAHEDRON, SEGMENT/TRIANGLE
  const index=new Map(materials.map((m,i)=>[m.id,i+1]));
  const point=n=>model.nodes[n];
  const elements=split.solidCells.map(c=>{
    let nodes=[...model.cells[c]];
    if(dimension===2){
      const [a,b,d]=nodes.map(point);
      if((b[0]-a[0])*(d[1]-a[1])-(b[1]-a[1])*(d[0]-a[0])<0)[nodes[1],nodes[2]]=[nodes[2],nodes[1]];
    }else{
      const [a,b,d,e]=nodes.map(point),u=[0,1,2].map(k=>b[k]-a[k]),v=[0,1,2].map(k=>d[k]-a[k]),w=[0,1,2].map(k=>e[k]-a[k]);
      const det=u[0]*(v[1]*w[2]-v[2]*w[1])-u[1]*(v[0]*w[2]-v[2]*w[0])+u[2]*(v[0]*w[1]-v[1]*w[0]);
      if(det<0)[nodes[1],nodes[2]]=[nodes[2],nodes[1]];
    }
    return `${index.get(String(model.cellMaterials?.[c]??''))} ${geom} ${nodes.map(n=>zone.map.get(n)).join(' ')}`;
  });
  const boundary=[],obliqueRollers=[];
  for(const f of split.interfaceSolid)boundary.push(`1 ${bgeom} ${f.map(n=>zone.map.get(n)).join(' ')}`);
  for(const [name,faces] of split.solidMarkers){
    const kind=settings.boundaries[name]?.kind;
    if(kind==='clamped')for(const f of faces)boundary.push(`2 ${bgeom} ${f.map(n=>zone.map.get(n)).join(' ')}`);
    if(kind==='roller'){
      const normal=averageNormal(model,faces,dimension).map(Math.abs);
      const axis=normal.indexOf(Math.max(...normal));
      if(normal[axis]<0.99)obliqueRollers.push(name);
      for(const f of faces)boundary.push(`${3+axis} ${bgeom} ${f.map(n=>zone.map.get(n)).join(' ')}`);
    }
  }
  const mesh=['MFEM mesh v1.0','','dimension',String(dimension),'','elements',String(elements.length),...elements,'',
    'boundary',String(boundary.length),...boundary,'','vertices',String(zone.nodes.length),String(dimension),
    ...zone.nodes.map(n=>point(n).slice(0,dimension).map(v=>Number(v).toPrecision(17)).join(' ')),''].join('\n');
  const width=dimension+1,traction=new Float64Array(zone.nodes.length*width),has=new Uint8Array(zone.nodes.length);
  for(const [global,values] of surfaceLoads){
    const local=zone.map.get(global);
    if(local===undefined)continue;
    has[local]=1;
    for(let k=0;k<width;k++)traction[local*width+k]=Number(values[k])||0;
  }
  // Lame parameters; plane stress uses the standard reduced lambda.
  const lame=m=>{
    const mu=m.E/(2*(1+m.nu)),lambda=m.E*m.nu/((1+m.nu)*(1-2*m.nu));
    return dimension===2&&settings.plane==='stress'?[2*lambda*mu/(lambda+2*mu),mu]:[lambda,mu];
  };
  const data=[String(materials.length),...materials.map(m=>lame(m).map(v=>v.toPrecision(17)).join(' ')),'1e-12 100000',String(zone.nodes.length),
    ...Array.from({length:zone.nodes.length},(_,i)=>`${has[i]} ${Array.from(traction.subarray(i*width,(i+1)*width)).map(v=>v.toPrecision(12)).join(' ')}`)].join('\n')+'\n';
  return {mesh,data,obliqueRollers};
}

module.exports={buildFsiInputs,splitMesh,normalizeSettings,normalizeFluid,mfemInput,elementProperties,su2Mesh,LIMITS,BOUNDARY_KINDS,SOLID_KINDS};
