const KINDS = new Set(['face','edge','line','patch','point','volume']);
const AXES = [0,1,2];

export const geometryLoadTypes = {
  point:['pointForce'],
  edge:['lineTraction','linearLineTraction'],
  line:['lineTraction','linearLineTraction'],
  face:['force','traction','pressure','linearTraction','linearPressure'],
  patch:['force','traction','pressure','linearTraction','linearPressure'],
  volume:['bodyForce','gravity']
};
export const isPressureLoad = type => type==='pressure'||type==='linearPressure';
export const isLinearSurfaceLoad = type => type==='linearTraction'||type==='linearPressure';
export const isLinearLoad = type => type==='linearLineTraction'||isLinearSurfaceLoad(type);

function point(value) {
  return Array.isArray(value) && value.length===3 && value.every(Number.isFinite);
}

function planarPatch(guide) {
  return point(guide.min) && point(guide.max) && AXES.includes(guide.axis) &&
    AXES.every(axis => axis===guide.axis ? guide.min[axis]===guide.max[axis] : guide.min[axis]<guide.max[axis]);
}

export function validateRestraintGuides(guides) {
  if (!Array.isArray(guides) || guides.length>100) throw Error('最多支持 100 项几何边界条件。');
  const ids = new Set();
  for (const guide of guides) {
    if (!guide || typeof guide.id!=='string' || !guide.id || ids.has(guide.id) ||
        !KINDS.has(guide.kind) || !Number.isSafeInteger(guide.entity) ||
        guide.entity<(guide.kind==='volume'?0:1)) {
      throw Error('几何边界条件数据无效。');
    }
    ids.add(guide.id);
    if (guide.load!==undefined) validateGeometryLoad(guide.kind,guide.load);
    else if (guide.kind==='volume'||!Array.isArray(guide.axes)||guide.axes.length!==3||
        !guide.axes.every(axis=>typeof axis==='boolean')||!guide.axes.some(Boolean)) {
      throw Error('几何约束数据无效。');
    }
    if (guide.kind==='point') {
      if(!point(guide.at))throw Error('请指定面上点的三维坐标。');
      if(guide.projection!==undefined){
        const {normal,radius}=guide.projection||{};
        if(!point(normal)||Math.abs(Math.hypot(...normal)-1)>1e-8||!Number.isFinite(radius)||radius<=0){
          throw Error('几何边界条件数据无效。');
        }
      }
    }
    if (guide.kind==='line' && (!point(guide.start) || !point(guide.end) ||
        !guide.start.some((value, axis) => value!==guide.end[axis]))) {
      throw Error('线段两端必须为不同的三维坐标。');
    }
    if (guide.kind==='patch' && !planarPatch(guide)) throw Error('局部面坐标范围无效。');
  }
}

export function validateGeometryLoad(kind,load) {
  if (!load||!geometryLoadTypes[kind]?.includes(load.type)) throw Error('载荷类型与几何对象不匹配。');
  const value=isPressureLoad(load.type)?Number.isFinite:point;
  const affine=isLinearSurfaceLoad(load.type)&&load.gradient!==undefined;
  if (!value(load.start)||isLinearLoad(load.type)&&!affine&&!value(load.end)) {
    throw Error('载荷值必须为有限数值。');
  }
  if(affine&&(!point(load.origin)||!Array.isArray(load.gradient)||load.gradient.length!==3||
      !load.gradient.every(value)))throw Error('多轴面载荷需要有效的参考点和三个坐标梯度。');
  if (isLinearSurfaceLoad(load.type)&&!affine&&(!AXES.includes(load.axis)||
      !Number.isFinite(load.from)||!Number.isFinite(load.to)||load.from===load.to)) {
    throw Error('面线性载荷需要两个不同的参考坐标。');
  }
  if(load.type==='linearLineTraction'&&load.reverse!==undefined&&typeof load.reverse!=='boolean'){
    throw Error('几何边界条件数据无效。');
  }
}

export function interpolateLoad(load,t){
  return Array.isArray(load.start)
    ?load.start.map((value,i)=>value+t*(load.end[i]-value))
    :load.start+t*(load.end-load.start);
}

export function surfaceLoadValue(load,position){
  if(!isLinearSurfaceLoad(load.type))return load.start;
  if(!load.gradient)return interpolateLoad(load,(position[load.axis]-load.from)/(load.to-load.from));
  const offset=position.map((value,i)=>value-load.origin[i]);
  const component=(base,component)=>load.gradient.reduce((value,derivative,axis)=>
    value+offset[axis]*(component===undefined?derivative:derivative[component]),base);
  return Array.isArray(load.start)?load.start.map(component):component(load.start);
}

// Geometric start is the lexicographically smaller endpoint. This order stays
// stable when CAD fragments and a different mesh add intermediate nodes.
export function openEdgePath(segments,nodes){
  const neighbors=new Map();
  for(const [a,b] of segments){
    if(!neighbors.has(a))neighbors.set(a,new Set());
    if(!neighbors.has(b))neighbors.set(b,new Set());
    neighbors.get(a).add(b);
    neighbors.get(b).add(a);
  }
  const ends=[...neighbors].filter(([,next])=>next.size===1).map(([id])=>id);
  if(ends.length!==2||[...neighbors.values()].some(next=>next.size>2))return null;
  ends.sort((a,b)=>nodes[a][0]-nodes[b][0]||nodes[a][1]-nodes[b][1]||nodes[a][2]-nodes[b][2]);
  const ids=[ends[0]],distances=new Map([[ends[0],0]]);
  let previous,current=ends[0],length=0;
  while(current!==ends[1]){
    const next=[...neighbors.get(current)].find(id=>id!==previous);
    if(next===undefined||distances.has(next))return null;
    length+=Math.hypot(...nodes[next].map((value,axis)=>value-nodes[current][axis]));
    distances.set(next,length);
    ids.push(next);
    previous=current;
    current=next;
  }
  return length>0&&ids.length===neighbors.size?{ids,distances,length}:null;
}

export function segmentParameter(guide,position){
  const direction=guide.end.map((value,i)=>value-guide.start[i]);
  const length=Math.hypot(...direction);
  return direction.reduce((sum,value,i)=>sum+(position[i]-guide.start[i])*(value/length),0)/length;
}

export function restraintGeometryKey(guide) {
  const key = [guide.kind,guide.entity];
  if (guide.kind==='point') {
    key.push(guide.at);
    if(guide.projection)key.push(guide.projection.normal,guide.projection.radius);
  }
  if (guide.kind==='line') key.push(guide.start,guide.end);
  if (guide.kind==='patch') key.push(guide.axis,guide.min,guide.max);
  return JSON.stringify(key);
}
