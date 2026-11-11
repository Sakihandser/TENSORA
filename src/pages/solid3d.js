import * as THREE from '../vendor/three/three.module.js';
import { OrbitControls } from '../vendor/three/OrbitControls.js';
import { createSectionView } from './solid3d-section-view.js';
import { decodeSolidResult, solidResultJson, solidResultSnapshot } from './solid3d-result-io.js';
import { createRestraintEditor, guideLabels, guideSegments, nearestCadEdge } from './solid3d-restraints.js';
import { drawLoadGlyphs } from './solid3d-load-view.js';
import { geometryLoadTypes, isLinearLoad, isLinearSurfaceLoad, isPressureLoad,
  restraintGeometryKey, validateGeometryLoad, validateRestraintGuides, openEdgePath } from '../core/solid3d-restraint-data.js';

const $=id=>document.getElementById(id), host=$('solid3dViewport');
const scene=new THREE.Scene();scene.background=new THREE.Color('#edf4f7');
const camera=new THREE.PerspectiveCamera(45,1,.001,1e8);camera.up.set(0,0,1);
const renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2));host.append(renderer.domElement);
const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;
scene.add(new THREE.HemisphereLight(0xffffff,0x7893a8,2.5));
const light=new THREE.DirectionalLight(0xffffff,2);light.position.set(3,4,8);scene.add(light);
const group=new THREE.Group();scene.add(group);
const axes=new THREE.Group();scene.add(axes);
const ray=new THREE.Raycaster(),pointer=new THREE.Vector2();
let shapes=[{type:'box',featureId:crypto.randomUUID(),x:0,y:0,z:0,dx:1,dy:.3,dz:.3,operation:'add'}],stepBase64=null,mesh=null,result=null,selected=null,selectedNode=null,selectedVolume=null,conditions=[];
let restraintGuides=[];
let materials=[];
const usableMaterial=m=>Number(m.elasticModulus)>0&&m.poissonRatio!=null&&Number.isFinite(Number(m.poissonRatio))&&Number(m.poissonRatio)>-1&&Number(m.poissonRatio)<.5;
let desiredMaterialId='';
let volumeMaterials={},hiddenVolumes=new Set(),stage='home';
let cad=null, revision=0, cadRevision=-1, previewTimer, previewRunning=false, previewQueued=false;
const status=msg=>{$('solid3dStatus').textContent=msg;$('solid3dInspectorStatus').textContent=msg;};
const cadSelection=()=>stage==='calculation'&&$('solid3dConstraintSource').value==='cad';
const displayedSolid=()=>stage==='home'||cadSelection()?cad||mesh:mesh||cad;
const pickMode=()=>$('solid3dPickMode').value;
const restraintEditor=createRestraintEditor({
  getState:()=>({cad:cadRevision===revision?cad:null,faceId:selected,mode:pickMode()}),
  update:()=>{restraintEditor.refresh(cadSelection());draw();},
  status
});
function boundGuides(){
  const groups=Array.isArray(mesh?.restraintGroups)?mesh.restraintGroups:[];
  return new Map(groups.filter(group=>group&&(group.nodes?.length||group.volumes===null||group.volumes?.length))
    .map(group=>[group.id,group]));
}
function guidesMatchMesh(){
  const groups=boundGuides();
  return groups.size===restraintGuides.length&&restraintGuides.every(guide=>
    groups.get(guide.id)?.geometry===restraintGeometryKey(guide));
}
const shapeNames={box:'盒体',cylinder:'圆柱体',sphere:'球体',cone:'圆锥 / 圆台',extrusion:'二维草图拉伸'};
const worldAxes=[new THREE.Vector3(1,0,0),new THREE.Vector3(0,1,0),new THREE.Vector3(0,0,1)];
function schedulePreview(){
  clearTimeout(previewTimer);
  previewTimer=setTimeout(rebuildCad,160);
}
async function rebuildCad(){
  if(previewRunning){previewQueued=true;return;}
  if(!shapes.length&&!stepBase64){cad=null;renderTree();updateInspector();draw();status('请添加 CAD 实体或导入 STEP。');return;}
  const requested=revision, fitAfter=!cad&&!mesh;
  previewRunning=true;
  if(stage==='home'||cadSelection())status('正在重建 CAD 几何…');
  try{
    const rebuilt=await post('preview',{shapes,stepBase64});
    if(requested!==revision)return;
    cad=rebuilt;
    cadRevision=revision;
    if(!mesh)hiddenVolumes=new Set(rebuilt.volumes.filter(volume=>hiddenVolumes.has(volume.id)).map(volume=>volume.id));
    refreshVolumeTargets();renderTree();updateInspector();restraintEditor.refresh(cadSelection());draw();
    if(fitAfter)fit();
    if(stage==='home'||cadSelection())status(`CAD 已重建 · ${cad.volumes.length} 个体域`);
  }catch(error){
    if(requested===revision&&(stage==='home'||cadSelection()))status(cad?`CAD 重建失败，显示上一次成功结果：${error.message}`:error.message);
  }finally{
    previewRunning=false;
    if(previewQueued){previewQueued=false;schedulePreview();}
  }
}
function geometryChanged({resetVisibility=false}={}){
  revision++;
  mesh=result=null;
  selected=selectedNode=selectedVolume=null;
  conditions=[];restraintGuides=[];volumeMaterials={};
  setConstraintSource('cad');
  if(resetVisibility)hiddenVolumes.clear();
  renderVolumes();showConditions();
  schedulePreview();
}
function clearGroup(){while(group.children.length){const child=group.children[0];group.remove(child);child.traverse(object=>{object.geometry?.dispose();if(Array.isArray(object.material))object.material.forEach(m=>m.dispose());else object.material?.dispose();});}}
function numeric(id){const v=Number($(id).value);if(!Number.isFinite(v))throw Error(`${id} 输入无效`);return v;}
function fit(){
  const box=new THREE.Box3();
  if(sectionView.mode()!=='surface'){
    const point=new THREE.Vector3();
    for(const node of mesh.nodes)box.expandByPoint(point.fromArray(node));
  }else box.setFromObject(group);
  if(box.isEmpty())return;
  const center=box.getCenter(new THREE.Vector3()),size=box.getSize(new THREE.Vector3()).length()||1;
  controls.target.copy(center);
  camera.position.copy(center).add(new THREE.Vector3(size*1.2,size*1.1,size*.9));
  camera.near=Math.max(size/10000,.000001);camera.far=Math.max(size*1000,10);
  camera.updateProjectionMatrix();controls.update();
}
function updateShapes(){
  const root=$('solid3dShapes');root.replaceChildren();
  if(stepBase64){const p=document.createElement('p');p.textContent='已载入 STEP；可继续添加实体或切削体。';root.append(p);}
  shapes.forEach((shape,i)=>{
    const card=document.createElement('div');card.className='solid3d-shape';
    const header=document.createElement('div');header.textContent=`${i+1}. ${shapeNames[shape.type]||shape.type}`;
    const actions=document.createElement('span');
    for(const [label,action] of [['复制',()=>shapes.push({...structuredClone(shape),featureId:crypto.randomUUID()})],['删除',()=>shapes.splice(i,1)]]){
      const button=document.createElement('button');button.type='button';button.textContent=label;
      button.addEventListener('click',()=>{action();updateShapes();geometryChanged({resetVisibility:true});});
      actions.append(button);
    }
    header.append(actions);card.append(header);
    const operation=document.createElement('select');for(const [value,label] of [['add','添加实体'],['cut','切削实体']]){const option=document.createElement('option');option.value=value;option.textContent=label;operation.append(option);}operation.value=shape.operation||'add';operation.addEventListener('change',()=>{shape.operation=operation.value;updateShapes();geometryChanged({resetVisibility:true});});const opLabel=document.createElement('label');opLabel.textContent='操作';opLabel.append(operation);card.append(opLabel);
    if(shape.operation==='cut'){
      const targetLabel=document.createElement('label');targetLabel.textContent='切削目标';
      const targetPicker=document.createElement('select');
      targetPicker.add(new Option('所有实体',''));
      shapes.forEach((body,j)=>{
        if(body.operation!=='cut')targetPicker.add(new Option(`${j+1}. ${shapeNames[body.type]}`,body.featureId));
      });
      if(shape.cutTarget&&![...targetPicker.options].some(option=>option.value===shape.cutTarget)){
        targetPicker.add(new Option('目标已移除',shape.cutTarget));
      }
      targetPicker.value=shape.cutTarget||'';
      targetPicker.addEventListener('change',()=>{shape.cutTarget=targetPicker.value;geometryChanged({resetVisibility:true});});
      targetLabel.append(targetPicker);card.append(targetLabel);
    }
    const planeLabel=document.createElement('label');planeLabel.textContent='基准面';
    const planePicker=$('solid3dBasePlane').cloneNode(true);planePicker.removeAttribute('id');planePicker.value=shape.plane||'XY';
    planePicker.addEventListener('change',()=>{shape.plane=planePicker.value;geometryChanged();});
    planeLabel.append(planePicker);card.append(planeLabel);
    const materialPicker=document.createElement('select');for(const material of materials.filter(usableMaterial)){const option=document.createElement('option');option.value=material.id;option.textContent=material.name;materialPicker.append(option);}materialPicker.value=shape.materialId||desiredMaterialId;materialPicker.addEventListener('change',()=>{shape.materialId=materialPicker.value;result=null;});const matLabel=document.createElement('label');matLabel.textContent='材料';matLabel.append(materialPicker);if(shape.operation!=='cut')card.append(matLabel);
    if(shape.type==='extrusion'){const count=document.createElement('p');count.textContent=`截面 ${shape.polygon.length} 个采样点`;card.append(count);}
    const dimensions={box:{dx:'长 U',dy:'宽 V',dz:'厚 N'},cylinder:{radius:'半径',height:'高度'},sphere:{radius:'半径'},cone:{radius:'底半径',topRadius:'顶半径',height:'高度'},extrusion:{height:'高度'}};
    for(const [key,name] of Object.entries({...dimensions[shape.type],x:'平移 X',y:'平移 Y',z:'平移 Z',rx:'旋转 X°',ry:'旋转 Y°',rz:'旋转 Z°'})){
      const label=document.createElement('label');label.textContent=name;
      const input=document.createElement('input');input.name=key;input.type='number';input.step='any';input.value=shape[key]??0;
      input.addEventListener('change',()=>{if(input.value!==''&&Number.isFinite(input.valueAsNumber)){shape[key]=input.valueAsNumber;geometryChanged();}else input.value=shape[key]??0;});
      label.append(input);card.append(label);
    }
    root.append(card);
  });
}
function insideShape(shape,p){
  const local=new THREE.Vector3(...p).sub(new THREE.Vector3(Number(shape.x||0),Number(shape.y||0),Number(shape.z||0)));
  for(let i=2;i>=0;i--)local.applyAxisAngle(worldAxes[i],-THREE.MathUtils.degToRad(Number(shape[['rx','ry','rz'][i]]||0)));
  const [x,y,z]=shape.plane==='XZ'?[local.x,local.z,-local.y]:shape.plane==='YZ'?[local.y,local.z,local.x]:local.toArray();
  if(shape.type==='sphere')return local.lengthSq()<=shape.radius**2+1e-8;
  if(z< -1e-8||z>Number(shape.type==='box'?shape.dz:shape.height)+1e-8)return false;
  if(shape.type==='box')return x>=-1e-8&&x<=shape.dx+1e-8&&y>=-1e-8&&y<=shape.dy+1e-8;
  if(shape.type==='cylinder'||shape.type==='cone'){
    const radius=shape.type==='cone'?Number(shape.radius)+(Number(shape.topRadius||0)-Number(shape.radius))*z/shape.height:shape.radius;
    return x*x+y*y<=radius**2+1e-8;
  }
  const polygon=shape.polygon||[];let inside=false;for(let i=0,j=polygon.length-1;i<polygon.length;j=i++){const a=polygon[i],b=polygon[j],ax=Array.isArray(a)?a[0]:a.x,ay=Array.isArray(a)?a[1]:a.y,bx=Array.isArray(b)?b[0]:b.x,by=Array.isArray(b)?b[1]:b.y;if((ay>y)!==(by>y)&&x<(bx-ax)*(y-ay)/(by-ay)+ax)inside=!inside;}return inside;
}
const FIELD_LABELS={ux:'X 位移 Ux',uy:'Y 位移 Uy',uz:'Z 位移 Uz',umag:'位移量 |u|',sxx:'正应力 σxx',syy:'正应力 σyy',szz:'正应力 σzz',sxy:'剪应力 τxy',syz:'剪应力 τyz',sxz:'剪应力 τxz',vm:'von Mises 应力',exx:'正应变 εxx',eyy:'正应变 εyy',ezz:'正应变 εzz',exy:'剪应变 εxy',eyz:'剪应变 εyz',exz:'剪应变 εxz',equivalentStrain:'等效应变'};
const SAFETY_COLORS=['#2f8f46','#f2c94c','#e76f51','#b42318','#64748b'];
const SAFETY_LABELS=['安全','抗压超限','抗拉超限','屈服超限','未完成校核'];
function displayColor(v,min,max){
  if(min<0&&max>0){const magnitude=Math.max(-min,max)||1,t=Math.min(1,Math.abs(v)/magnitude);return new THREE.Color('#f4f6f4').lerp(new THREE.Color(v<0?'#2f6fb3':'#b42318'),t);}
  const t=Math.min(1,Math.max(0,max>min?(v-min)/(max-min):0));return new THREE.Color().setHSL(.61*(1-t),.88,.48);
}
function drawGuideLines(segments,color,depthTest){
  if(!segments.length)return;
  const geometry=new THREE.BufferGeometry();
  geometry.setAttribute('position',new THREE.Float32BufferAttribute(segments.flat(2),3));
  const lines=new THREE.LineSegments(geometry,new THREE.LineBasicMaterial({color,depthTest,depthWrite:false}));
  lines.renderOrder=depthTest?1:2;
  group.add(lines);
}
function drawGuidePoints(positions,color,size){
  if(!positions.length)return;
  const geometry=new THREE.BufferGeometry();
  geometry.setAttribute('position',new THREE.Float32BufferAttribute(positions.flat(),3));
  const points=new THREE.Points(geometry,new THREE.PointsMaterial({
    color,size,sizeAttenuation:false,depthTest:false,depthWrite:false
  }));
  points.renderOrder=2;
  group.add(points);
}
function showLoadGlyphs(view,guide,binding,faces,scale){
  host.dataset.loadGlyphs=Number(host.dataset.loadGlyphs)+drawLoadGlyphs(group,view,guide,binding,faces,scale);
}
function drawCadRestraints(view,visibleFaces,scale){
  if(view!==cad||cadRevision!==revision)return;
  const visible=new Set(group.children.map(object=>object.userData.surface).filter(id=>id!=null));
  if(pickMode()==='edge'){
    const edges=(cad.edges||[]).filter(edge=>edge.surfaces.some(id=>visible.has(id)));
    drawGuideLines(edges.flatMap(edge=>edge.segments.map(segment=>segment.map(id=>cad.nodes[id]))),0x234c62,true);
  }
  const available=guide=>guide.kind==='edge'
    ?cad.edges?.find(edge=>Number(edge.id)===guide.entity)?.surfaces.some(id=>visible.has(id))
    :visible.has(String(guide.entity));
  const saved=restraintGuides.filter(available);
  for(const [load,color] of [[false,0x185ab5],[true,0xb75e06]]){
    const guides=saved.filter(guide=>Boolean(guide.load)===load);
    drawGuideLines(guides.flatMap(guide=>guideSegments(cad,guide)),color,false);
    drawGuidePoints(guides.filter(guide=>guide.kind==='point').map(guide=>guide.at),color,8);
    if(load&&$('solid3dShowLoads').checked){
      for(const guide of guides)showLoadGlyphs(cad,guide,null,visibleFaces,scale);
    }
  }
  if(pickMode()==='volume')return;
  try{
    const draft=restraintEditor.draft();
    if(available(draft)){
      drawGuideLines(guideSegments(cad,draft),0xd17000,false);
      if(draft.kind==='point')drawGuidePoints([draft.at],0xd17000,9);
    }
  }catch{/* An incomplete coordinate entry has no outline. */}
}
function drawBoundRestraints(visibleFaces,scale){
  if(!guidesMatchMesh()||!restraintGuides.length)return;
  const bindings=boundGuides();
  const fixed=new Set(),loaded=new Set();
  const visible=new Set(visibleFaces.map(({surface})=>String(surface.id)));
  for(const guide of restraintGuides){
    const target=guide.load?loaded:fixed;
    const binding=bindings.get(guide.id);
    for(const id of binding.nodes)target.add(id);
    if(!guide.load||guide.kind==='volume')continue;
    if(['line','edge'].includes(guide.kind)&&!mesh.edges?.some(edge=>
      binding.entities?.includes(String(edge.id))&&edge.surfaces.some(id=>visible.has(String(id)))))continue;
    if(guide.kind==='point'&&!visibleFaces.some(({surface,indices})=>
      indices.some(index=>surface.triangles[index].includes(binding.nodes[0]))))continue;
    showLoadGlyphs(mesh,guide,binding,visibleFaces,scale);
  }
  drawGuidePoints([...fixed].map(id=>mesh.nodes[id]).filter(Boolean),0x185ab5,5);
  drawGuidePoints([...loaded].map(id=>mesh.nodes[id]).filter(Boolean),0xb75e06,5);
}
function draw(){
  clearGroup();
  host.dataset.loadGlyphs='0';
  sectionView.render();
  const sectionMode=sectionView.mode();
  const showSurface=sectionMode==='surface';
  $('solid3dScale').disabled=!showSurface;
  $('solid3dShowDeformed').disabled=!showSurface;
  axes.visible=$('solid3dShowAxes').checked;
  for(const helper of [...axes.children]){axes.remove(helper);helper.geometry.dispose();helper.material.dispose();}
  const view=displayedSolid();
  const extent=new THREE.Box3();
  const point=new THREE.Vector3();
  for(const p of view?.nodes||[])extent.expandByPoint(point.fromArray(p));
  const axisSize=Math.max(.01,extent.isEmpty()?1:extent.getSize(point).length());
  axes.add(new THREE.AxesHelper(axisSize*.45));
  const grid=new THREE.GridHelper(axisSize*1.5,10,0x93adb9,0xcadce3);
  const plane=stage==='home'?$('solid3dBasePlane').value:'XY';
  if(plane==='XY')grid.rotation.x=Math.PI/2;
  if(plane==='YZ')grid.rotation.z=Math.PI/2;
  axes.add(grid);
  if(!view){$('solid3dMetrics').textContent='节点 0 · 四面体 0';return;}
  const analysisView=view===mesh;
  const mode=$('solid3dDisplay').value,scale=numeric('solid3dScale');
  const values=analysisView&&showSurface?result?.nodeFields?.[mode]||null:null,safety=analysisView&&showSurface&&mode==='safety'&&!!result;
  let min=0,max=0;
  if(values?.length){min=max=values[0];for(const value of values){min=Math.min(min,value);max=Math.max(max,value);}}
  const palette=['#6b9fb5','#b68c69','#8da676','#aa83a8','#6c9c91'];
  const showShell=sectionMode==='context'&&$('solid3dShowGeometry').checked;
  const visibleFaces=[];
  for(const surface of showSurface||showShell?view.surfaces:[]){
    const positions=[],colors=[],visibleTriangles=[];
    const safetyCodes=safety?result.surfaceSafety.find(s=>s.id===surface.id)?.codes:[];
    surface.triangles.forEach((tri,i)=>{const volumeId=String(surface.triangleVolumes?.[i]||surface.volumeId||'0'),neighbor=surface.triangleNeighborVolumes?.[i]??surface.neighborVolumeId;if(neighbor!=null?hiddenVolumes.has(volumeId)===hiddenVolumes.has(String(neighbor)):hiddenVolumes.has(volumeId))return;visibleTriangles.push(i);for(const id of tri){const p=view.nodes[id],u=analysisView?result?.displacements?.[id]||result?.displacementVector?.subarray(id*3,id*3+3)||[0,0,0]:[0,0,0];positions.push(...p.map((v,k)=>v+u[k]*((values||safety)&&$('solid3dShowDeformed').checked?scale:0)));if(values||safety){const c=safety?new THREE.Color(SAFETY_COLORS[safetyCodes?.[i]??4]):displayColor(values[id],min,max);colors.push(c.r,c.g,c.b);}}});
    if(!visibleTriangles.length)continue;
    visibleFaces.push({surface,indices:visibleTriangles});
    const geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));if(values||safety)geo.setAttribute('color',new THREE.Float32BufferAttribute(colors,3));geo.computeVertexNormals();
    const first=visibleTriangles[0];
    const owner=surface.triangleVolumes?.[first]||surface.volumeId;
    const visibleOwner=hiddenVolumes.has(owner)?surface.triangleNeighborVolumes?.[first]??surface.neighborVolumeId:owner;
    const materialIndex=Math.max(0,view.volumes.findIndex(v=>v.id===visibleOwner));
    const assigned=materials.find(m=>m.id===volumeMaterials[visibleOwner]);
    const highlighted=stage==='home'?visibleOwner===selectedVolume:surface.id===selected;
    const mat=showSurface
      ?new THREE.MeshStandardMaterial({color:(values||safety)?0xffffff:highlighted?0xffbd5a:assigned?.color||palette[materialIndex%palette.length],vertexColors:!!(values||safety),side:THREE.DoubleSide,flatShading:!(values||safety),roughness:.75,transparent:!$('solid3dShowGeometry').checked,opacity:$('solid3dShowGeometry').checked?1:.08,depthWrite:$('solid3dShowGeometry').checked})
      :new THREE.MeshBasicMaterial({color:0x7894a3,side:THREE.DoubleSide,transparent:true,opacity:.13,depthWrite:false});
    const obj=new THREE.Mesh(geo,mat);obj.userData.surface=surface.id;obj.userData.volume=visibleOwner;obj.userData.triangleIndices=visibleTriangles;group.add(obj);
    if(analysisView&&$('solid3dShowMesh').checked&&mode==='mesh'){const edges=new THREE.LineSegments(new THREE.WireframeGeometry(geo),new THREE.LineBasicMaterial({color:0x304f5d,transparent:true,opacity:.35}));group.add(edges);}
  }
  if(!analysisView){
    if(cadSelection())drawCadRestraints(view,visibleFaces,axisSize);
    $('solid3dMetrics').textContent='CAD 几何 · '+view.volumes.length+' 体域 · '+view.surfaces.length+' 面';
    return;
  }
  const pointSize=Math.max(axisSize*.012,.004);
  if(showSurface&&$('solid3dShowLoads').checked)drawBoundRestraints(visibleFaces,axisSize);
  if(showSurface&&$('solid3dShowLoads').checked)for(const bc of conditions){
    if(isLinearSurfaceLoad(bc.type))showLoadGlyphs(mesh,{kind:'face',load:bc},
      {entities:[String(bc.surface)]},visibleFaces,axisSize);
  }
  if(showSurface&&$('solid3dShowNodes').checked){const positions=mesh.nodes.flat(),geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));const points=new THREE.Points(geo,new THREE.PointsMaterial({color:0x225c6b,size:pointSize}));group.add(points);}
  if(showSurface&&$('solid3dShowLoads').checked)for(const bc of conditions){if(isLinearSurfaceLoad(bc.type))continue;const surface=mesh.surfaces.find(s=>String(s.id)===String(bc.surface));const nodes=bc.node!=null?[Number(bc.node)]:surface?[...new Set(surface.triangles.flat())]:bc.type==='bodyForce'||bc.type==='gravity'?[...new Set(mesh.tets.filter((_,i)=>!bc.volume||String(mesh.tetVolumes[i])===String(bc.volume)).flat())]:[];if(!nodes.length)continue;const center=new THREE.Vector3();nodes.forEach(id=>center.add(new THREE.Vector3(...mesh.nodes[id])));center.divideScalar(nodes.length);if(bc.type==='fixed'||bc.type==='fixedNode'){const marker=new THREE.Mesh(new THREE.SphereGeometry(pointSize*1.5,8,8),new THREE.MeshBasicMaterial({color:0x2454b8}));marker.position.copy(center);group.add(marker);continue;}const vector=new THREE.Vector3(Number(bc.fx)||0,Number(bc.fy)||0,Number(bc.fz)||0);if(bc.type==='pressure'){const tri=surface?.triangles[0];if(tri){const a=mesh.nodes[tri[0]],b=mesh.nodes[tri[1]],c=mesh.nodes[tri[2]];vector.copy(new THREE.Vector3(...b).sub(new THREE.Vector3(...a)).cross(new THREE.Vector3(...c).sub(new THREE.Vector3(...a))));}}if(vector.lengthSq()>0){vector.normalize();for(const id of nodes.filter((_,i)=>i%Math.max(1,Math.ceil(nodes.length/8))===0)){const arrow=new THREE.ArrowHelper(vector,new THREE.Vector3(...mesh.nodes[id]),axisSize*.12,0xd27813,axisSize*.035,axisSize*.015);group.add(arrow);}}}
  $('solid3dMetrics').textContent=`节点 ${mesh.nodes.length} · 四面体 ${mesh.tets.length}`+(result?` · 最大位移 ${result.maxDisplacement.toExponential(4)} m · 最大 von Mises ${result.maxVonMises.toExponential(4)} Pa · 迭代 ${result.iterations}`:'');
  $('solid3dResultSummary').textContent=result?`最大位移 ${result.maxDisplacement.toExponential(4)} m；最大 von Mises 应力 ${result.maxVonMises.toExponential(4)} Pa；求解迭代 ${result.iterations} 次。`:'尚无三维计算结果，请到“计算”页求解。';
  const timing=result?.timing;
  const seconds=ms=>(ms/1000).toFixed(2);
  $('solid3dPerformance').textContent=timing
    ?`${result.backend} · 组装 ${seconds(timing.assemblyMs)} s · 迭代 ${seconds(timing.iterationMs)} s · 后处理 ${seconds(timing.postprocessMs)} s`
    :'';
  $('solid3dPerformance').title=result?.fallback||'';
  if(!showSurface)return;
  const legend=$('solid3dLegend');legend.replaceChildren();
  if(safety){result.safetyCounts.forEach((count,i)=>{const line=document.createElement('div'),swatch=document.createElement('span');swatch.className='solid3d-swatch';swatch.style.background=SAFETY_COLORS[i];line.append(swatch,`${SAFETY_LABELS[i]}：${count} 个单元`);legend.append(line);});}
  else if(values){legend.textContent=`${FIELD_LABELS[mode]}：${min.toExponential(4)} 至 ${max.toExponential(4)} ${mode.startsWith('s')||mode==='vm'?'Pa':mode.startsWith('u')?'m':'1'}`;}
}
async function refreshMaterials(){
  let list;
  try{const response=await fetch('/api/materials',{cache:'no-store'});if(!response.ok)throw Error();list=(await response.json()).materials;}
  catch{list=window.PROJECT_MATERIAL_LIBRARY?.materials||[];}
  materials=Array.isArray(list)?list:[];
  const picker=$('solid3dMaterial'),previous=desiredMaterialId||picker.value;picker.replaceChildren();
  for(const material of materials.filter(usableMaterial)){const option=document.createElement('option');option.value=material.id;option.textContent=material.name;picker.append(option);}
  if(materials.some(m=>m.id===previous))picker.value=previous;
  desiredMaterialId=picker.value;
  showMaterial();
  updateShapes();renderVolumes();
}
function showMaterial(){const material=materials.find(m=>m.id===$('solid3dMaterial').value);$('solid3dMaterialInfo').textContent=material?`E = ${material.elasticModulus} GPa，ν = ${material.poissonRatio}；与二维材料库共用。`:'材料库中没有可用的线弹性材料。';}
function refreshVolumeTargets(){
  const target=$('solid3dVolumeTarget'),previous=target.value;
  const volumes=$('solid3dConstraintSource').value==='cad'?cad?.volumes:mesh?.volumes;
  const all=new Option('全部体域','');
  target.replaceChildren(all,...(volumes||[]).map(volume=>new Option('体域 '+volume.id,volume.id)));
  target.value=[...target.options].some(option=>option.value===previous)?previous:'';
}
function renderVolumes(){
  const root=$('solid3dVolumes');root.replaceChildren();
  for(const volume of mesh?.volumes||[]){
    if(!volumeMaterials[volume.id]){const shape=[...shapes].reverse().find(s=>s.operation!=='cut'&&s.materialId&&insideShape(s,volume.centroid));volumeMaterials[volume.id]=shape?.materialId||desiredMaterialId;}
    const card=document.createElement('div');card.className='solid3d-volume-card';const title=document.createElement('strong');title.textContent=`体域 ${volume.id} · ${volume.elements} 单元`;card.append(title);
    const p=document.createElement('p');p.textContent=`中心 (${volume.centroid.map(v=>v.toFixed(3)).join(', ')}) m`;card.append(p);
    const label=document.createElement('label');label.textContent='材料';const select=document.createElement('select');
    for(const material of materials.filter(usableMaterial)){const option=document.createElement('option');option.value=material.id;option.textContent=material.name;select.append(option);}select.value=volumeMaterials[volume.id];
    select.addEventListener('change',()=>{volumeMaterials[volume.id]=select.value;result=null;draw();renderTree();});label.append(select);card.append(label);root.append(card);
  }
  refreshVolumeTargets();renderTree();updateInspector();
}
function renderTree(){const root=$('solid3dTree');root.replaceChildren();
  const view=displayedSolid();
  if(!view){root.textContent='暂无 CAD 体域';return;}
  for(const volume of view.volumes||[]){const row=document.createElement('div');row.className='solid3d-tree-row';const check=document.createElement('input');check.type='checkbox';check.checked=!hiddenVolumes.has(volume.id);check.title='显示/隐藏体域';check.addEventListener('change',()=>{check.checked?hiddenVolumes.delete(volume.id):hiddenVolumes.add(volume.id);draw();});
    const name=document.createElement(stage==='home'?'button':'span');
    name.textContent=`体域 ${volume.id} · ${materials.find(m=>m.id===volumeMaterials[volume.id])?.name||'未指定'}`;
    if(stage==='home'){
      name.type='button';name.className='solid3d-tree-name';
      name.setAttribute('aria-pressed',String(volume.id===selectedVolume));
      name.addEventListener('click',()=>{selectedVolume=volume.id;renderTree();draw();});
    }
    const isolate=document.createElement('button');isolate.type='button';isolate.textContent='独显';isolate.addEventListener('click',()=>{hiddenVolumes=new Set(view.volumes.filter(v=>v.id!==volume.id).map(v=>v.id));selectedVolume=volume.id;renderTree();draw();});row.append(check,name,isolate);root.append(row);
  }
}
function setConstraintSource(source){
  $('solid3dConstraintSource').value=source;
  const picker=$('solid3dPickMode');
  if(source==='cad'&&picker.value==='node'||source==='mesh'&&!['face','node'].includes(picker.value))picker.value='face';
  selected=selectedNode=selectedVolume=null;
  restraintEditor.reset();
}
function updateConstraintControls(){
  const useCad=$('solid3dConstraintSource').value==='cad';
  $('solid3dConstraintSource').options[1].disabled=!mesh;
  for(const option of $('solid3dPickMode').options){
    option.hidden=option.disabled=useCad?option.value==='node':!['face','node'].includes(option.value);
  }
  $('solid3dLoadInputs').hidden=!useCad&&!mesh;
  $('solid3dClearFace').hidden=useCad&&['point','line','patch'].includes(pickMode());
  $('solid3dFixAxes').hidden=$('solid3dFixed').hidden=useCad&&pickMode()==='volume';
  refreshVolumeTargets();
  updateLoadInputs();
  restraintEditor.refresh(cadSelection());
}
function updateInspector(){
  const count=mesh?.nodes.length||0,element=mesh?.tets.length||0,volume=displayedSolid()?.volumes?.length||0;
  const meshSupports=conditions.filter(c=>c.type==='fixed'||c.type==='fixedNode').length;
  const cadLoads=restraintGuides.filter(guide=>guide.load).length;
  $('solid3dInspectorCounts').textContent=count+' 节点 · '+element+' 四面体 · '+volume+' 体域 · '+
    (meshSupports+restraintGuides.length-cadLoads)+' 约束 · '+(conditions.length-meshSupports+cadLoads)+' 载荷';
}
function showFaceInfo(){
  const view=displayedSolid();
  const surface=view?.surfaces.find(s=>s.id===selected);
  const info=$('solid3dFaceInfo');
  if(!surface){info.textContent='选择面后显示面心、面积与法向。';return;}
  const center=new THREE.Vector3(),normal=new THREE.Vector3();
  let area=0;
  for(const tri of surface.triangles){
    const [a,b,c]=tri.map(id=>new THREE.Vector3(...view.nodes[id]));
    const cross=b.clone().sub(a).cross(c.clone().sub(a)),triangleArea=cross.length()/2;
    center.add(a.add(b).add(c).multiplyScalar(triangleArea/3));
    normal.add(cross);
    area+=triangleArea;
  }
  center.divideScalar(area||1);
  const volume=view.volumes.find(v=>v.id===selectedVolume);
  if(volume?.centroid&&normal.dot(center.clone().sub(new THREE.Vector3(...volume.centroid)))<0)normal.negate();
  normal.normalize();
  const components=normal.toArray().map(Math.abs),axis=components.indexOf(Math.max(...components));
  const sign=normal.getComponent(axis)>=0?'+':'−';
  info.textContent='面心 ('+center.toArray().map(v=>v.toFixed(3)).join(', ')+') m · 面积 '+area.toExponential(3)+
    ' m² · 法向约 '+sign+'XYZ'[axis];
}
const directionLabel=axes=>axes.map((enabled,i)=>enabled?'XYZ'[i]:'').join('');
function describeLoad(load){
  if(load.gradient)return [load.start,'('+load.origin.join(', ')+') m',
    load.gradient.map((gradient,i)=>'∂/∂'+'XYZ'[i]+' '+gradient).join(' · ')+' Pa/m'].join(' · ');
  return [load.start,load.end].filter(value=>value!==undefined).join(' → ');
}
function conditionRow(label,remove){
  const row=document.createElement('div'), text=document.createElement('span'),button=document.createElement('button');
  row.className='solid3d-condition-row';
  text.textContent=label;
  button.textContent='删除';
  button.type='button';
  button.addEventListener('click',remove);
  row.append(text,button);
  return row;
}
function replaceGuides(guides){
  restraintGuides=guides;
  result=null;
  showConditions();
}
function replaceConditions(next){
  conditions=next;
  result=null;
  showConditions();
}
function showConditions(){
  updateConstraintControls();
  $('solid3dSelectedFace').textContent=selected??'—';
  $('solid3dSelectedNode').textContent=selectedNode??'—';
  $('solid3dSelectedVolume').textContent=selectedVolume??'—';
  showFaceInfo();
  const root=$('solid3dConditions');
  root.replaceChildren();
  const groups=guidesMatchMesh()?boundGuides():new Map();
  for(const guide of restraintGuides){
    const binding=groups.get(guide.id);
    const target=guide.kind==='volume'&&guide.entity===0?'全部体域':guideLabels[guide.kind]+' '+guide.entity;
    const label=[target,guide.load?LOAD_LABELS[guide.load.type]:directionLabel(guide.axes),
      !binding?'待划分网格':guide.kind==='volume'?'已绑定体域':binding.nodes.length+' 个已绑定节点'].join(' · ');
    const row=conditionRow(label,()=>replaceGuides(restraintGuides.filter(g=>g!==guide)));
    if(guide.kind==='point')row.title=(mesh?.nodes[binding?.nodes[0]]||guide.at).join(', ')+' m';
    if(guide.kind==='line')row.title=guide.start.join(', ')+' → '+guide.end.join(', ')+' m';
    if(guide.kind==='patch')row.title=guide.min.join(', ')+' → '+guide.max.join(', ')+' m';
    if(guide.load){
      const value=describeLoad(guide.load);
      row.title=[row.title,value].filter(Boolean).join(' · ');
    }
    root.append(row);
  }
  for(const bc of conditions){
    const target=bc.node!=null?'节点 '+bc.node:bc.surface!=null?'面 '+bc.surface:bc.volume?'体域 '+bc.volume:'全体';
    const name=bc.type==='fixed'||bc.type==='fixedNode'?'位移约束':LOAD_LABELS[bc.type]||bc.type;
    const data=bc.axes?directionLabel(bc.axes):isLinearSurfaceLoad(bc.type)
      ?describeLoad(bc):bc.pressure??[bc.fx,bc.fy,bc.fz].join(', ');
    root.append(conditionRow(target+' · '+name+' '+data,()=>replaceConditions(conditions.filter(c=>c!==bc))));
  }
  if(!conditions.length&&!restraintGuides.length)root.textContent='尚未设置边界条件';
  updateInspector();
  draw();
}
function putCondition(type){
  const mode=pickMode();
  if(cadSelection()){
    if(!cad||cadRevision!==revision)throw Error('请等待 CAD 几何重建。');
    const draft=mode==='volume'?{kind:mode,entity:Number($('solid3dVolumeTarget').value)}:restraintEditor.draft();
    if(type==='clear'){
      replaceGuides(restraintGuides.filter(g=>g.kind!==draft.kind||g.entity!==draft.entity));
      return;
    }
    const guide={...draft,id:crypto.randomUUID()};
    if(type==='load'){
      guide.load=readLoad();
      if(guide.kind==='edge'&&isLinearLoad(guide.load.type)){
        const edge=cad.edges.find(item=>Number(item.id)===guide.entity);
        if(!openEdgePath(edge.segments,cad.nodes))throw Error('线性边载荷需要一条有两个端点的 CAD 边。');
      }
    }
    else guide.axes=selectedAxes();
    const next=[...restraintGuides,guide];
    validateRestraintGuides(next);
    replaceGuides(next);
    status('几何边界条件已添加。生成网格后会完成绑定。');
    return;
  }
  if(!mesh)throw Error('请先生成网格。');
  if(type==='clear'){
    replaceConditions(conditions.filter(c=>mode==='node'?c.node!==selectedNode:c.surface!==selected));
    return;
  }
  if(type==='fixed'){
    if(mode==='node'&&selectedNode==null||mode==='face'&&!selected)throw Error('请先在模型上选择面或节点。');
    const axes=selectedAxes();
    const condition=mode==='node'?{type:'fixedNode',node:selectedNode,axes}:{type:'fixed',surface:selected,axes};
    replaceConditions([...conditions,condition]);
    return;
  }
  const load=readLoad(),loadType=load.type,bc={type:loadType};
  if(loadType==='pointForce'){
    if(selectedNode==null)throw Error('请先切换节点拾取并选中网格节点。');
    bc.node=selectedNode;
  }else if(loadType==='bodyForce'||loadType==='gravity'){
    bc.volume=$('solid3dVolumeTarget').value||null;
  }else{
    if(!selected)throw Error('请先在模型上选择 CAD 面。');
    bc.surface=selected;
  }
  if(isLinearSurfaceLoad(loadType))Object.assign(bc,load);
  else if(loadType==='pressure')bc.pressure=load.start;
  else [bc.fx,bc.fy,bc.fz]=load.start;
  replaceConditions([...conditions,bc]);
}
function selectedAxes(){
  const axes=['X','Y','Z'].map(axis=>$('solid3dFix'+axis).checked);
  if(!axes.some(Boolean))throw Error('至少选中一个位移方向。');
  return axes;
}

const LOAD_LABELS={force:'面总力',traction:'面力密度',pressure:'法向压力',bodyForce:'体力密度',
  gravity:'重力',pointForce:'节点力',lineTraction:'均匀线载荷',linearLineTraction:'线线性分布载荷',
  linearTraction:'面线性分布力',linearPressure:'面线性法向压力'};
function readLoad(){
  const type=$('solid3dLoadType').value;
  const value=id=>{
    const number=$(id).valueAsNumber;
    if(!Number.isFinite(number))throw Error('载荷值必须为有限数值。');
    return number;
  };
  const intensity=suffix=>isPressureLoad(type)?value('solid3dPressure'+suffix)
    :['x','y','z'].map(axis=>value('solid3dF'+axis+suffix));
  const load={type,start:intensity('')};
  const affine=isLinearSurfaceLoad(type)&&$('solid3dLoadProfileMode').value==='gradient';
  if(isLinearLoad(type)&&!affine)load.end=intensity('End');
  if(isLinearSurfaceLoad(type)){
    if(affine){
      const axes=['X','Y','Z'];
      load.origin=axes.map(axis=>value('solid3dLoadOrigin'+axis));
      load.gradient=axes.map(axis=>isPressureLoad(type)?value('solid3dGradient'+axis+'P')
        :axes.map(component=>value('solid3dGradient'+axis+component)));
    }else{
      load.axis='XYZ'.indexOf($('solid3dLoadAxis').value);
      load.from=value('solid3dLoadFrom');
      load.to=value('solid3dLoadTo');
    }
  }
  if(type==='linearLineTraction'&&pickMode()==='edge')load.reverse=$('solid3dEdgeReverse').checked;
  const kind=cadSelection()?pickMode():type==='pointForce'?'point'
    :geometryLoadTypes.volume.includes(type)?'volume':'face';
  validateGeometryLoad(kind,load);
  return load;
}
function updateLoadInputs(){
  const picker=$('solid3dLoadType');
  const allowed=$('solid3dConstraintSource').value==='cad'?geometryLoadTypes[pickMode()]
    :[...geometryLoadTypes.face,...geometryLoadTypes.volume,'pointForce'];
  if(!allowed)return;
  for(const option of picker.options)option.hidden=option.disabled=!allowed.includes(option.value);
  if(!allowed.includes(picker.value))picker.value=allowed[0];
  const type=picker.value,pressure=isPressureLoad(type),linear=isLinearLoad(type);
  const affine=isLinearSurfaceLoad(type)&&$('solid3dLoadProfileMode').value==='gradient';
  $('solid3dVolumeTargetRow').hidden=!geometryLoadTypes.volume.includes(type);
  $('solid3dLoadProfile').hidden=!isLinearSurfaceLoad(type);
  $('solid3dSingleAxisProfile').hidden=affine;
  $('solid3dGradientProfile').hidden=!affine;
  $('solid3dLoadStartLabel').hidden=!linear;
  $('solid3dLoadStartLabel').textContent=affine?'参考点强度':'起点强度';
  $('solid3dLoadEnd').hidden=!linear||affine;
  $('solid3dEdgeReverseRow').hidden=type!=='linearLineTraction'||pickMode()!=='edge';
  for(const field of document.querySelectorAll('[data-gradient-kind]')){
    field.hidden=field.dataset.gradientKind!==(pressure?'pressure':'vector');
  }
  $('solid3dPressureRow').hidden=$('solid3dPressureEndRow').hidden=!pressure;
  const unit=type==='traction'||isLinearSurfaceLoad(type)?'Pa'
    :geometryLoadTypes.line.includes(type)?'N/m':type==='bodyForce'?'N/m³':type==='gravity'?'m/s²':'N';
  for(const axis of ['x','y','z'])for(const suffix of ['','End']){
    $('solid3dF'+axis+suffix).parentElement.hidden=pressure;
    $('solid3dF'+axis+suffix+'Label').textContent=axis.toUpperCase()+' ('+unit+')';
  }
  $('solid3dForce').textContent='施加'+(type==='bodyForce'?'体力':LOAD_LABELS[type]);
}
function activateCadLoad(kind,type){
  if(!cadSelection())setConstraintSource('cad');
  $('solid3dPickMode').value=kind;
  $('solid3dLoadType').value=type;
  restraintEditor.stopPicking();
  if(cadRevision!==revision)schedulePreview();
  renderTree();showConditions();
  status(kind==='patch'?'请选择 CAD 面并指定局部范围。':'请选择 CAD 面并指定线段端点。');
}
async function post(route,payload){
  const headers={'Content-Type':'application/json'};
  if(route==='solve')headers.Accept='application/octet-stream';
  const response=await fetch('/api/solid3d/'+route,{
    method:'POST',headers,body:JSON.stringify(payload)
  });
  // A service started before the 3D API was updated can still serve newer UI files.
  if(response.status===404){
    throw Error('当前服务缺少三维接口。请先保存三维模型，再关闭软件窗口并重新启动。');
  }
  if(response.ok&&response.headers.get('Content-Type')==='application/octet-stream'){
    return decodeSolidResult(await response.arrayBuffer());
  }
  const data=await response.json().catch(()=>null);
  if(!data)throw Error(`三维服务返回了无效响应（HTTP ${response.status}）。`);
  if(!response.ok||!data.ok)throw Error(data.error||'三维计算失败');
  return data.data;
}
async function busy(button,work){button.disabled=true;try{await work();}catch(error){status(error.message);}finally{button.disabled=false;}}
function addShape(type,dimensions){
  shapes.push({type,...dimensions,featureId:crypto.randomUUID(),plane:$('solid3dBasePlane').value,x:0,y:0,z:0,operation:'add',materialId:desiredMaterialId});
  updateShapes();geometryChanged();
}
$('solid3dAddBox').addEventListener('click',()=>addShape('box',{dx:1,dy:.3,dz:.3}));
$('solid3dAddCylinder').addEventListener('click',()=>addShape('cylinder',{radius:.2,height:1}));
$('solid3dAddSphere').addEventListener('click',()=>addShape('sphere',{radius:.2}));
$('solid3dAddCone').addEventListener('click',()=>addShape('cone',{radius:.2,topRadius:0,height:.4}));
$('solid3dRebuild').addEventListener('click',schedulePreview);
$('solid3dBasePlane').addEventListener('change',draw);
$('solid3dStep').addEventListener('change',async event=>{const file=event.target.files?.[0];if(!file)return;if(!/\.(step|stp)$/i.test(file.name)||file.size>40_000_000){status('请选择小于 40 MB 的 STEP 文件。');return;}const bytes=new Uint8Array(await file.arrayBuffer());let binary='';for(let i=0;i<bytes.length;i+=32768)binary+=String.fromCharCode(...bytes.subarray(i,i+32768));stepBase64=btoa(binary);shapes=[];sectionView.load();cad=null;updateShapes();geometryChanged({resetVisibility:true});});
function simplifyLoop(polygon){const points=polygon.filter((p,i)=>i===0||Math.hypot(p[0]-polygon[i-1][0],p[1]-polygon[i-1][1])>1e-10);if(points.length>1&&Math.hypot(points[0][0]-points.at(-1)[0],points[0][1]-points.at(-1)[1])<1e-10)points.pop();let changed=true;while(changed&&points.length>3){changed=false;for(let i=0;i<points.length;i++){const a=points[(i+points.length-1)%points.length],b=points[i],c=points[(i+1)%points.length],cross=(b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0]);if(Math.abs(cross)<1e-8*Math.max(1,Math.hypot(c[0]-a[0],c[1]-a[1]))){points.splice(i,1);changed=true;break;}}}return points;}
function refreshSketchRegions(){const regions=window.tensora2dSketchSnapshot?.()||[],picker=$('solid3dSketchRegion'),previous=picker.value,hadRegions=picker.options.length>1;picker.replaceChildren();const all=document.createElement('option');all.value='';all.textContent=`全部区域 (${regions.length})`;picker.append(all);regions.forEach((region,i)=>{const option=document.createElement('option');option.value=String(region.id);option.textContent=`${i+1}. ${region.id} · ${region.regionKind==='air'?'空域':'结构'} · ${region.polygon.length} 点`;picker.append(option);});if(hadRegions&&[...picker.options].some(o=>o.value===previous))picker.value=previous;else if(regions.length)picker.value=String(regions.at(-1).id);}
function finishSketch(operation){
  const sketchStatus=$('solid3dSketchStatus');
  try{
    const regions=window.tensora2dSketchSnapshot?.()||[];
    if(!regions.length)throw Error('二维草图尚无闭合结构区域。');
    const normalOffset=numeric('solid3dSketchZ'),height=numeric('solid3dSketchHeight');
    if(!(height>0))throw Error('拉伸高度须大于零');
    const chosen=$('solid3dSketchRegion').value;
    const entries=regions.filter(region=>(!chosen||String(region.id)===chosen)&&(region.regionKind!=='air'||operation==='add'));
    if(!entries.length)throw Error('所选二维区域不可用于该操作，请刷新并选择结构区域。');
    const plane=$('solid3dSketchPlane').value;
    const offset=plane==='XZ'?{y:-normalOffset}:plane==='YZ'?{x:normalOffset}:{z:normalOffset};
    for(const region of entries){
      shapes.push({
        type:'extrusion',featureId:crypto.randomUUID(),polygon:simplifyLoop(region.polygon),plane,...offset,height,
        operation:operation==='add'&&region.regionKind==='air'?'cut':operation,materialId:region.materialId||desiredMaterialId
      });
    }
    sketchStatus.textContent='';
    geometryChanged({resetVisibility:operation==='cut'});
    window.tensoraSolid3dSketchMode=false;
    window.setPage('home');
    updateShapes();
  }catch(error){sketchStatus.textContent=error.message;}
}
$('solid3dEditSketch').addEventListener('click',()=>{$('solid3dSketchStatus').textContent='';$('solid3dSketchPlane').value=$('solid3dBasePlane').value;window.tensoraSolid3dSketchMode=true;window.setPage('home');refreshSketchRegions();});
$('solid3dSketchRefresh').addEventListener('click',refreshSketchRegions);
$('solid3dSketchAdd').addEventListener('click',()=>finishSketch('add'));
$('solid3dSketchCut').addEventListener('click',()=>finishSketch('cut'));
$('solid3dSketchCancel').addEventListener('click',()=>{window.tensoraSolid3dSketchMode=false;window.setPage('home');});
async function saveJson(name,payload){const handle=await window.chooseExportFile(window.uiText(name),'application/json','.json');if(!handle)return;await window.writeExportFile(handle,async writer=>writer.write(JSON.stringify(payload)));}
function modelSnapshot(){
  return {version:1,kind:'tensora-solid3d',shapes,stepBase64,meshSize:numeric('solid3dMeshSize'),
    mesh,conditions,restraintGuides,volumeMaterials,hiddenVolumes:[...hiddenVolumes],
    sectionView:sectionView.snapshot(),materialId:$('solid3dMaterial').value||desiredMaterialId};
}
$('solid3dSaveModel').addEventListener('click',async()=>{
  try{await saveJson('TENSORA-三维模型.json',modelSnapshot());status('三维模型已保存。');}
  catch(error){status(error.message);}
});
$('solid3dLoadModel').addEventListener('change',async event=>{
  try{
    const file=event.target.files?.[0];if(!file)return;
    if(file.size>200_000_000)throw Error('模型文件过大');
    const data=JSON.parse(await file.text());
    if(data.kind!=='tensora-solid3d'||data.version!==1||!Array.isArray(data.shapes)||!Array.isArray(data.conditions)){
      throw Error('不是有效的三维模型文件');
    }
    const guides=data.restraintGuides??[];
    validateRestraintGuides(guides);
    revision++;
    cad=null;
    shapes=data.shapes.map(shape=>({...shape,featureId:shape.featureId||crypto.randomUUID()}));
    stepBase64=typeof data.stepBase64==='string'?data.stepBase64:null;
    mesh=data.mesh&&Array.isArray(data.mesh.nodes)&&Array.isArray(data.mesh.tets)&&Array.isArray(data.mesh.surfaces)?data.mesh:null;
    conditions=data.conditions;restraintGuides=guides;
    volumeMaterials=data.volumeMaterials||{};hiddenVolumes=new Set(data.hiddenVolumes||[]);
    sectionView.load(data.sectionView);
    result=null;
    setConstraintSource(mesh&&guidesMatchMesh()?'mesh':'cad');
    desiredMaterialId=String(data.materialId||'');
    $('solid3dMeshSize').value=String(data.meshSize||.2);
    updateShapes();renderVolumes();showConditions();fit();status('三维模型已导入。');schedulePreview();
  }catch(error){status(error.message);}
  finally{event.target.value='';}
});
$('solid3dMesh').addEventListener('click',event=>busy(event.target,async()=>{
  const requested=revision,guides=restraintGuides;
  status('Gmsh 正在导入 CAD 并划分四面体…');
  const generated=await post('mesh',{shapes,stepBase64,meshSize:numeric('solid3dMeshSize'),restraintGuides:guides});
  if(requested!==revision||guides!==restraintGuides){
    status('几何或边界条件已更改，请重新生成网格。');
    return;
  }
  mesh=generated;
  result=null;
  conditions=[];
  volumeMaterials={};
  setConstraintSource('mesh');
  $('solid3dDisplay').value='mesh';
  renderVolumes();showConditions();fit();
  status('网格完成：'+mesh.nodes.length+' 节点，'+mesh.tets.length+' 四面体，'+mesh.volumes.length+' 体域，'+mesh.surfaces.length+' 个 CAD 面。');
}));
for(const [id,type] of [['solid3dFixed','fixed'],['solid3dClearFace','clear'],['solid3dForce','load']]){
  $(id).addEventListener('click',()=>{try{putCondition(type);}catch(error){status(error.message);}});
}
$('solid3dConstraintSource').addEventListener('change',()=>{
  setConstraintSource($('solid3dConstraintSource').value);
  if(cadSelection()&&cadRevision!==revision)schedulePreview();
  renderTree();showConditions();
});
$('solid3dPickMode').addEventListener('change',()=>{
  restraintEditor.stopPicking();
  restraintEditor.selectEdge(null);
  if(pickMode()==='point')restraintEditor.resetPoint();
  showConditions();
});
$('solid3dSolve').addEventListener('click',event=>busy(event.target,async()=>{
  if(!mesh)throw Error('请先生成网格。');
  if(!guidesMatchMesh())throw Error('几何边界条件已更改，请重新生成网格。');
  for(const volume of mesh.volumes)if(!volumeMaterials[volume.id])throw Error('体域 '+volume.id+' 尚未指定材料');
  const analyzedMesh=mesh, analyzedConditions=conditions, analyzedGuides=restraintGuides;
  const groupConditions=analyzedGuides.map(guide=>guide.load?{type:'loadGroup',guide}
    :{type:'fixedGroup',group:guide.id,axes:guide.axes});
  status('正在组装三维刚度矩阵并求解…');
  const solved=await post('solve',{mesh,settings:{materials,volumeMaterials,conditions:[...groupConditions,...conditions],computeBackend:$('solid3dComputeBackend').value}});
  if(mesh!==analyzedMesh||conditions!==analyzedConditions||restraintGuides!==analyzedGuides){
    status('网格或边界条件已更改，请重新求解。');
    return;
  }
  result=solved;
  $('solid3dDisplay').value='umag';
  draw();status('计算完成，残差 '+result.residual.toExponential(3)+'。');window.setPage('results');
}));

$('solid3dMaterial').addEventListener('change',()=>{desiredMaterialId=$('solid3dMaterial').value;result=null;showMaterial();draw();});
$('solid3dLoadType').addEventListener('change',updateLoadInputs);updateLoadInputs();
$('solid3dLoadProfileMode').addEventListener('change',updateLoadInputs);
$('solid3dPatchLoadShortcut').addEventListener('click',()=>activateCadLoad('patch','linearTraction'));
$('solid3dLineLoadShortcut').addEventListener('click',()=>activateCadLoad('line','linearLineTraction'));
for(const id of ['solid3dShowGeometry','solid3dShowMesh','solid3dShowLoads','solid3dShowNodes','solid3dShowAxes','solid3dShowDeformed'])$(id).addEventListener('change',draw);
$('solid3dShowAll').addEventListener('click',()=>{hiddenVolumes.clear();renderTree();draw();});
$('solid3dExport').addEventListener('click',async()=>{try{if(!result)throw Error('还没有三维计算结果');const handle=await window.chooseExportFile(window.uiText('TENSORA-三维结果.json'),'application/json','.json');if(!handle)return;await window.writeExportChunks(handle,solidResultJson(modelSnapshot(),result));status('三维结果已导出。');}catch(error){status(error.message);}});
$('solid3dDisplay').addEventListener('change',()=>{
  if(stage==='results')sectionView.selectSurfaceForModel($('solid3dDisplay').value);
  draw();
});
$('solid3dScale').addEventListener('change',draw);$('solid3dFit').addEventListener('click',fit);
const viewDirections={iso:[1,1,.8],top:[0,0,1],bottom:[0,0,-1],front:[0,-1,0],back:[0,1,0],left:[-1,0,0],right:[1,0,0]};
function setView(name){const direction=viewDirections[name];if(!direction)return;const distance=Math.max(camera.position.distanceTo(controls.target),1);camera.up.set(0,name==='top'?1:name==='bottom'?-1:0,name==='top'||name==='bottom'?0:1);camera.position.copy(controls.target).add(new THREE.Vector3(...direction).normalize().multiplyScalar(distance));camera.lookAt(controls.target);controls.update();}
for(const button of document.querySelectorAll('[data-solid3d-view]'))button.addEventListener('click',()=>setView(button.dataset.solid3dView));
const orientation=$('solid3dOrientation'),orientationContext=orientation.getContext('2d');
function drawOrientation(){const ctx=orientationContext,w=orientation.width,h=orientation.height;ctx.clearRect(0,0,w,h);ctx.fillStyle='rgba(255,255,255,.9)';ctx.beginPath();ctx.arc(w/2,h/2,61,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#b4c9d2';ctx.stroke();const inverse=camera.quaternion.clone().invert(),items=[];for(const [name,axis,color] of [['X',[1,0,0],'#c83c3c'],['Y',[0,1,0],'#2c994e'],['Z',[0,0,1],'#286cc9']])for(const sign of [-1,1]){const v=new THREE.Vector3(...axis).multiplyScalar(sign).applyQuaternion(inverse);items.push({name:sign>0?'+'+name:'−'+name,color:sign>0?color:'#81939b',v});}items.sort((a,b)=>a.v.z-b.v.z);for(const {name,color,v} of items){const x=w/2+v.x*42,y=h/2-v.y*42;ctx.strokeStyle=color;ctx.lineWidth=name.startsWith('+')?3:1.5;ctx.beginPath();ctx.moveTo(w/2,h/2);ctx.lineTo(x,y);ctx.stroke();ctx.fillStyle=color;ctx.beginPath();ctx.arc(x,y,10,0,Math.PI*2);ctx.fill();ctx.fillStyle='#fff';ctx.font='bold 10px Segoe UI';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(name,x,y);}}
renderer.domElement.addEventListener('click',event=>{
  const view=displayedSolid();
  if(!view||sectionView.mode()!=='surface')return;
  const rect=renderer.domElement.getBoundingClientRect();
  pointer.set((event.clientX-rect.left)/rect.width*2-1,-(event.clientY-rect.top)/rect.height*2+1);
  ray.setFromCamera(pointer,camera);
  const hit=ray.intersectObjects(group.children.filter(object=>object.isMesh&&object.userData.surface))[0];
  if(!hit)return;
  if(stage==='home'){
    selectedVolume=hit.object.userData.volume;
    renderTree();draw();
    return;
  }
  if(cadSelection()){
    if(view!==cad||cadRevision!==revision)return;
    const faceId=hit.object.userData.surface;
    const face=cad.surfaces.find(surface=>surface.id===faceId);
    const triangle=face.triangles[hit.object.userData.triangleIndices[hit.faceIndex]];
    const points=triangle.map(id=>new THREE.Vector3(...cad.nodes[id]));
    const location=ray.ray.intersectTriangle(...points,false,new THREE.Vector3())||hit.point;
    if(restraintEditor.pickEndpoint(faceId,location.toArray())){showConditions();return;}
    selected=faceId;
    selectedVolume=hit.object.userData.volume;
    if(pickMode()==='edge'){
      restraintEditor.selectEdge(nearestCadEdge(cad,selected,hit.point,camera,rect.width,rect.height));
    }
    if(pickMode()==='point'){
      const normal=points[1].clone().sub(points[0]).cross(points[2].clone().sub(points[0])).normalize();
      const radius=Math.max(points[0].distanceTo(points[1]),points[1].distanceTo(points[2]),points[2].distanceTo(points[0]));
      restraintEditor.selectPoint(location.toArray(),normal.lengthSq()&&radius?{normal:normal.toArray(),radius}:undefined);
    }
    if(pickMode()==='volume')$('solid3dVolumeTarget').value=selectedVolume;
    showConditions();
    return;
  }
  if(!mesh||view!==mesh)return;
  selected=hit.object.userData.surface;
  const surface=mesh.surfaces.find(face=>face.id===selected);
  const index=hit.object.userData.triangleIndices[hit.faceIndex]??0;
  selectedVolume=hit.object.userData.volume;
  if($('solid3dPickMode').value==='node'){
    const point=new THREE.Vector3();
    const distance=id=>hit.point.distanceToSquared(point.fromArray(mesh.nodes[id]));
    selectedNode=surface.triangles[index].reduce((best,id)=>distance(id)<distance(best)?id:best);
  }
  showConditions();
});
const resize=()=>{const w=host.clientWidth,h=host.clientHeight;if(!w||!h)return;camera.aspect=w/h;camera.updateProjectionMatrix();renderer.setSize(w,h,false);};new ResizeObserver(resize).observe(host);
window.addEventListener('tensora-solid3d-show',event=>{
  sectionView.finishDrag();
  stage=event.detail?.page||'home';
  for(const el of document.querySelectorAll('#solid3dPage [data-solid3d-stage]'))el.hidden=el.dataset.solid3dStage!==stage;
  $('solid3dHeading').textContent={home:'三维结构绘制',calculation:'三维计算',results:'三维计算结果'}[stage];
  if(stage!=='results')refreshMaterials();
  if(!cad&&(!mesh||cadSelection()))schedulePreview();
  if(stage==='results'&&result&&!FIELD_LABELS[$('solid3dDisplay').value]&&$('solid3dDisplay').value!=='safety')$('solid3dDisplay').value='umag';
  else if(stage==='calculation'&&mesh)$('solid3dDisplay').value='mesh';
  else if(stage==='home')$('solid3dDisplay').value='model';
  resize();renderTree();showConditions();
});
const sectionView=createSectionView({
  host,camera,controls,scene,draw,displayColor,fieldLabels:FIELD_LABELS,safetyColors:SAFETY_COLORS,safetyLabels:SAFETY_LABELS,
  getState:()=>({stage,mesh,result,field:$('solid3dDisplay').value,hiddenVolumes})
});
function animate(){
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene,camera);
  sectionView.frame();
  drawOrientation();
}
animate();updateShapes();renderVolumes();updateConstraintControls();
window.tensoraSolid3d={
  snapshot:({compact=false}={})=>{
    const model=modelSnapshot();
    return {...structuredClone({...model,cad}),result:compact||!result?.elementData?structuredClone(result):solidResultSnapshot(model,result)};
  },
  cameraDirection:()=>camera.position.clone().sub(controls.target).normalize().toArray(),setView
};
if(!$('solid3dPage').hidden)window.dispatchEvent(new CustomEvent('tensora-solid3d-show',{detail:{page:$('solid3dPage').dataset.page}}));
