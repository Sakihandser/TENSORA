import * as THREE from '../vendor/three/three.module.js';

const $ = id => document.getElementById('solid3d'+id);
const AXES = ['X','Y','Z'];
export const guideLabels = {face:'CAD 面', edge:'CAD 边', line:'面上线段', patch:'局部面',
  point:'CAD 面上点',volume:'CAD 体域'};

function faceBounds(cad, face) {
  const min = [Infinity,Infinity,Infinity], max = [-Infinity,-Infinity,-Infinity];
  for (const triangle of face.triangles) for (const id of triangle) {
    cad.nodes[id].forEach((value, axis) => {
      min[axis] = Math.min(min[axis], value);
      max[axis] = Math.max(max[axis], value);
    });
  }
  const span = max.map((value, axis) => value-min[axis]);
  const axis = span.findIndex(value => value <= Math.max(...span)*1e-9 + 1e-12);
  return {min, max, axis};
}

export function guideSegments(cad, guide) {
  if (guide.kind==='point'||guide.kind==='volume') return [];
  if (guide.kind === 'line') return [[guide.start,guide.end]];
  if (guide.kind === 'patch') {
    const [u,v] = [0,1,2].filter(axis => axis !== guide.axis);
    const corners = [[0,0],[1,0],[1,1],[0,1]].map(([i,j]) => {
      const p = [...guide.min];
      if (i) p[u] = guide.max[u];
      if (j) p[v] = guide.max[v];
      return p;
    });
    return corners.map((p, i) => [p,corners[(i+1)%4]]);
  }
  const edges = (cad.edges||[]).filter(edge => guide.kind === 'edge'
    ? Number(edge.id) === guide.entity : edge.surfaces.includes(String(guide.entity)));
  return edges.flatMap(edge => edge.segments.map(segment => segment.map(id => cad.nodes[id])));
}

export function nearestCadEdge(cad, faceId, hitPoint, camera, width, height) {
  const p = new THREE.Vector2(), a = new THREE.Vector2(), b = new THREE.Vector2();
  const projected = new THREE.Vector3();
  const screen = (point, out) => {
    projected.fromArray(point).project(camera);
    return out.set(projected.x*width/2, projected.y*height/2);
  };
  screen(hitPoint.toArray(),p);
  let best = null, distance = 14**2;
  for (const edge of cad.edges||[]) {
    if (!edge.surfaces.includes(String(faceId))) continue;
    for (const [i,j] of edge.segments) {
      screen(cad.nodes[i],a);
      screen(cad.nodes[j],b);
      const dx=b.x-a.x, dy=b.y-a.y, length=dx*dx+dy*dy;
      const t=length ? Math.max(0,Math.min(1,((p.x-a.x)*dx+(p.y-a.y)*dy)/length)) : 0;
      const d=(p.x-a.x-t*dx)**2+(p.y-a.y-t*dy)**2;
      if (d < distance) {best=edge.id;distance=d;}
    }
  }
  return best;
}

export function createRestraintEditor({getState, update, status}) {
  const inputs = prefix => AXES.map(axis => $(prefix+axis));
  const start = inputs('LineStart'), end = inputs('LineEnd'), at=inputs('Point');
  const lower = inputs('PatchMin'), upper = inputs('PatchMax');
  const lineButtons = [$('LineStart'),$('LineEnd')];
  let endpoint = null, edge = null, projection;

  function stopPicking() {
    endpoint = null;
    for (const button of lineButtons) button.setAttribute('aria-pressed','false');
  }

  function reset() {
    stopPicking();
    edge = null;
    resetPoint();
    for (const input of [...start,...end,...lower,...upper]) input.value = '';
  }
  function resetPoint(){
    projection=undefined;
    for(const input of at)input.value='';
  }

  function read(field) {
    if (field.validity.badInput) throw Error('请输入有效的坐标。');
    if (field.value === '') return null;
    if (!Number.isFinite(field.valueAsNumber)) throw Error('请输入有效的坐标。');
    return field.valueAsNumber;
  }

  function draft() {
    const {cad,faceId,mode} = getState();
    if (!cad) throw Error('请等待 CAD 几何重建。');
    if (mode === 'edge') {
      if (edge === null) throw Error('请在模型上点击 CAD 边。');
      return {kind:mode,entity:Number(edge)};
    }
    const face = cad.surfaces.find(surface => surface.id === faceId);
    if (!face) throw Error('请先在模型上选择 CAD 面。');
    const entity = Number(face.id);
    if (mode === 'face') return {kind:mode,entity};
    if (mode==='point') {
      const coordinates=at.map(read);
      if(!coordinates.every(Number.isFinite))throw Error('请指定面上点的三维坐标。');
      return {kind:mode,entity,at:coordinates,projection};
    }
    if (mode === 'line') {
      const from = start.map(read), to = end.map(read);
      if (!from.every(Number.isFinite) || !to.every(Number.isFinite)) throw Error('请指定线段的起点和终点。');
      if (from.every((value, i) => value === to[i])) throw Error('线段两端必须为不同的三维坐标。');
      return {kind:mode,entity,start:from,end:to};
    }
    const bounds = faceBounds(cad,face);
    if (bounds.axis < 0) throw Error('局部面须选在平行于 XY、XZ 或 YZ 的 CAD 平面上。');
    const min = lower.map((input, i) => i===bounds.axis ? bounds.min[i] : Math.max(bounds.min[i],read(input)??bounds.min[i]));
    const max = upper.map((input, i) => i===bounds.axis ? bounds.min[i] : Math.min(bounds.max[i],read(input)??bounds.max[i]));
    if (min.some((value, i) => i !== bounds.axis && value >= max[i])) throw Error('局部面坐标范围无效。');
    return {kind:mode,entity,min,max,axis:bounds.axis};
  }

  function refresh(isCad) {
    const {cad,faceId,mode} = getState();
    const showRegion = isCad && ['point','line','patch'].includes(mode);
    $('Region').hidden = !showRegion;
    $('LineInputs').hidden = mode !== 'line';
    $('PointInputs').hidden = mode !== 'point';
    $('PatchInputs').hidden = mode !== 'patch';
    const edgeInfo = $('EdgeInfo');
    edgeInfo.hidden = !isCad || mode !== 'edge';
    edgeInfo.textContent = edge === null ? '请在模型上点击 CAD 边。' : '选中 CAD 边 '+edge;
    const preview = $('RestraintPreview');
    preview.hidden = !showRegion;
    if (!showRegion) return;
    const face = cad?.surfaces.find(surface => surface.id===faceId);
    lineButtons.forEach(button => button.disabled=!face);
    const bounds = mode==='patch' && face ? faceBounds(cad,face) : null;
    for (let axis=0; axis<3; axis++) {
      const disabled = !bounds || bounds.axis===axis;
      lower[axis].disabled = upper[axis].disabled = disabled;
      lower[axis].placeholder = bounds ? Number(bounds.min[axis].toPrecision(7)) : '';
      upper[axis].placeholder = bounds ? Number(bounds.max[axis].toPrecision(7)) : '';
    }
    $('RegionHint').textContent = {
      point:'在 CAD 面上点击定位，也可以修改下方坐标。',
      line:'先选面，再输入两端坐标，或在该面上拾取端点。',
      patch:'在选中平面上输入局部范围。留空时取面的坐标边界。'
    }[mode];
    try {
      draft();
      preview.textContent = '橙色轮廓为待划分的约束范围。';
    } catch (error) {
      preview.textContent = error.message;
    }
  }

  function pickEndpoint(faceId,point) {
    if (endpoint === null) return false;
    if (faceId !== getState().faceId) {
      status('请在同一个 CAD 面上拾取端点。');
      return true;
    }
    const fields = endpoint===0 ? start : end;
    fillPoint(fields,point);
    stopPicking();
    return true;
  }
  function fillPoint(fields,point){
    point.forEach((value,axis)=>fields[axis].value=Number(value.toPrecision(15)));
  }
  function selectPoint(point,pickedProjection){
    fillPoint(at,point);
    projection=pickedProjection;
  }

  lineButtons.forEach((button,i) => button.addEventListener('click',() => {
    const previous=endpoint;
    stopPicking();
    if (previous===i) return;
    endpoint=i;
    button.setAttribute('aria-pressed','true');
    status('请在选中的 CAD 面上点击端点。');
  }));
  for (const input of [...at,...start,...end,...lower,...upper]) input.addEventListener('change',update);
  for(const input of at)input.addEventListener('input',()=>{projection=undefined;});
  return {draft,refresh,reset,resetPoint,stopPicking,pickEndpoint,selectPoint,selectEdge:id=>{edge=id;}};
}
