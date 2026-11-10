import * as THREE from '../vendor/three/three.module.js';
import {cutTetrahedra, sectionNormals, sectionValues, unitSectionNormal} from './solid3d-sections.js';

export function createSectionView({host, camera, controls, scene, getState, draw, displayColor, fieldLabels, safetyColors, safetyLabels}) {
  const $=id=>document.getElementById('solid3d'+id);
  const mode=$('SectionMode'), list=$('SectionList'), planePicker=$('SectionPlane');
  const xyz=['X','Y','Z'].map(axis=>$('Section'+axis));
  const normals=['X','Y','Z'].map(axis=>$('SectionN'+axis));
  const handle=document.createElement('button');
  handle.type='button';
  handle.className='solid3d-section-handle';
  handle.textContent='拖动剖面';
  handle.hidden=true;
  host.append(handle);

  const group=new THREE.Group();
  scene.add(group);
  let planes=[], selected=null, nextNumber=1, drag=null, dragFrame=0;
  let cachedMesh=null, cachedBounds=null, cache=new WeakMap(), palette=null;
  const active=()=>{
    const {stage,mesh,result}=getState();
    return stage==='results'&&mesh&&result&&mode.value!=='surface';
  };
  function bounds(mesh) {
    if (cachedMesh!==mesh) {
      cachedMesh=mesh;
      cache=new WeakMap();
      const box=new THREE.Box3(), point=new THREE.Vector3();
      for (const node of mesh.nodes) box.expandByPoint(point.fromArray(node));
      const center=box.getCenter(new THREE.Vector3()), span=box.getSize(point).length();
      const tolerance=Math.max(span*1e-10,Number.EPSILON*Math.max(center.length(),span)*8);
      cachedBounds={center,span,tolerance};
    }
    return cachedBounds;
  }
  function refreshEditor() {
    list.replaceChildren();
    for (const plane of planes) {
      const row=document.createElement('div');
      row.className='solid3d-section-row';
      const visibility=document.createElement('input');
      visibility.type='checkbox';
      visibility.checked=plane.visible;
      visibility.setAttribute('aria-label','显示剖面 '+plane.number);
      visibility.addEventListener('change',()=>{plane.visible=visibility.checked;render();});
      const choose=document.createElement('button');
      choose.type='button';
      choose.textContent='剖面 '+plane.number;
      choose.setAttribute('aria-pressed',String(plane===selected));
      choose.addEventListener('click',()=>{selected=plane;refreshEditor();render();});
      row.append(visibility,choose);
      list.append(row);
    }
    $('SectionEditor').hidden=!selected;
    if (!selected) return;
    planePicker.value=selected.orientation;
    $('SectionNormal').hidden=selected.orientation!=='custom';
    xyz.forEach((input,i)=>input.value=selected.point[i]);
    normals.forEach((input,i)=>input.value=selected.normal[i]);
  }
  function clearGeometry() {
    for (const child of [...group.children]) {
      group.remove(child);
      child.geometry.dispose();
      child.material.dispose();
    }
    palette?.dispose();
    palette=null;
  }
  function cut(mesh, plane, hiddenVolumes, hiddenKey) {
    const normal=unitSectionNormal(plane.normal);
    if (!normal) return null;
    const {tolerance}=bounds(mesh);
    const key=[...plane.point,...normal,hiddenKey].join('|');
    const saved=cache.get(plane);
    if (saved?.key===key) return saved.cut;
    const geometry=cutTetrahedra(mesh,plane.point,normal,tolerance,hiddenVolumes);
    cache.set(plane,{key,cut:geometry});
    return geometry;
  }
  function colorScale(min,max) {
    const size=256, pixels=new Uint8Array(size*4), stops=[];
    for (let i=0; i<size; i++) {
      const color=displayColor(min+(max-min)*i/(size-1),min,max);
      pixels.set([color.r*255,color.g*255,color.b*255,255],i*4);
      if (i%17===0) stops.push(color.getStyle());
    }
    palette=new THREE.DataTexture(pixels,size,1);
    palette.minFilter=palette.magFilter=THREE.LinearFilter;
    palette.needsUpdate=true;
    return 'linear-gradient(to right,'+stops.join(',')+')';
  }
  function render() {
    const {mesh,result,field,hiddenVolumes}=getState();
    $('SectionPanel').disabled=!result||!mesh;
    clearGeometry();
    if (cachedMesh&&cachedMesh!==mesh) {cachedMesh=null;cachedBounds=null;cache=new WeakMap();}
    if (!active()) {$('SectionStatus').textContent='';return;}
    const legend=$('Legend');
    legend.replaceChildren();
    const displayed=planes.filter(plane=>plane.visible);
    const hiddenKey=[...hiddenVolumes].sort().join(',');
    const slices=[];
    let min=Infinity,max=-Infinity;
    const safety=field==='safety';
    for (const plane of displayed) {
      const geometry=cut(mesh,plane,hiddenVolumes,hiddenKey);
      if (!geometry?.elements.length) continue;
      const values=sectionValues(geometry,result,field);
      if (!safety) for (const value of values) {min=Math.min(min,value);max=Math.max(max,value);}
      slices.push({geometry,values});
    }
    $('SectionStatus').textContent=selected?.visible&&!unitSectionNormal(selected.normal)
      ?'剖面法向不能为零。':!displayed.length?'请新建或显示一个剖面。'
      :!slices.length?'剖面与可见体域无交集。'
      :slices.length<displayed.length?'部分剖面与可见体域无交集。':'';
    if (!slices.length) return;

    if (safety) {
      const present=new Set();
      for (const {values} of slices) for (const code of values) present.add(code);
      safetyLabels.forEach((label,i)=>{
        if (!present.has(i)) return;
        const line=document.createElement('div'), swatch=document.createElement('span');
        swatch.className='solid3d-swatch';
        swatch.style.background=safetyColors[i];
        line.append(swatch,label);
        legend.append(line);
      });
    } else {
      const bar=document.createElement('div');
      bar.className='solid3d-section-colorbar';
      bar.style.background=colorScale(min,max);
      const units=field.startsWith('s')||field==='vm'?'Pa':field.startsWith('u')?'m':'1';
      legend.append(`${fieldLabels[field]}：${min.toExponential(4)} 至 ${max.toExponential(4)} ${units}`,bar);
    }

    for (const {geometry,values} of slices) {
      const buffer=new THREE.BufferGeometry();
      buffer.setAttribute('position',new THREE.BufferAttribute(geometry.positions,3));
      let material;
      if (safety) {
        const colors=safetyColors.map(value=>new THREE.Color(value));
        const rgb=new Float32Array(values.length*3);
        values.forEach((value,i)=>(colors[value]||colors[4]).toArray(rgb,i*3));
        buffer.setAttribute('color',new THREE.BufferAttribute(rgb,3));
        material=new THREE.MeshBasicMaterial({side:THREE.DoubleSide,vertexColors:true});
      } else {
        const range=max-min;
        buffer.setAttribute('contourValue',new THREE.BufferAttribute(Float32Array.from(values,v=>range?(v-min)/range:0),1));
        material=new THREE.ShaderMaterial({
          side:THREE.DoubleSide,
          uniforms:{palette:{value:palette}},
          vertexShader:`
            attribute float contourValue;
            varying float contour;
            void main() {
              contour = contourValue;
              gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
            }`,
          fragmentShader:`
            uniform sampler2D palette;
            varying float contour;
            void main() {
              gl_FragColor = texture2D(palette, vec2((clamp(contour, 0.0, 1.0)*255.0+0.5)/256.0, 0.5));
              #include <colorspace_fragment>
            }`
        });
      }
      group.add(new THREE.Mesh(buffer,material));
    }
  }
  function anchor(plane, mesh, normal) {
    const {center}=bounds(mesh);
    const delta=new THREE.Vector3(...plane.point).sub(center).dot(normal);
    return center.clone().addScaledVector(normal,delta);
  }
  function handlePosition() {
    const normal=selected?.visible&&unitSectionNormal(selected.normal);
    handle.hidden=!active()||!normal;
    if (handle.hidden) return;
    const point=anchor(selected,getState().mesh,new THREE.Vector3(...normal)).project(camera);
    if (![point.x,point.y,point.z].every(Number.isFinite)) {handle.hidden=true;return;}
    const x=THREE.MathUtils.clamp((point.x+1)*host.clientWidth/2,58,host.clientWidth-58);
    const y=THREE.MathUtils.clamp((1-point.y)*host.clientHeight/2,22,host.clientHeight-22);
    handle.style.left=x+'px';
    handle.style.top=y+'px';
  }
  function finishDrag() {
    if (!drag) return;
    const {pointerId}=drag;
    drag=null;
    if (handle.hasPointerCapture(pointerId)) handle.releasePointerCapture(pointerId);
    controls.enabled=true;
  }
  handle.addEventListener('pointerdown',event=>{
    if (!active()||!selected?.visible||event.button!==0) return;
    const direction=unitSectionNormal(selected.normal);
    if (!direction) return;
    const normal=new THREE.Vector3(...direction), {mesh}=getState();
    const center=anchor(selected,mesh,normal);
    const step=bounds(mesh).span*.1;
    const p=center.clone().project(camera), q=center.clone().addScaledVector(normal,step).project(camera);
    const axis=new THREE.Vector2((q.x-p.x)*host.clientWidth/2,(p.y-q.y)*host.clientHeight/2);
    const viewDepth=Math.max(Math.abs(center.clone().applyMatrix4(camera.matrixWorldInverse).z),step);
    const worldPerPixel=2*viewDepth*Math.tan(THREE.MathUtils.degToRad(camera.fov/2))/host.clientHeight;
    const length=axis.length();
    const perPixel=length*worldPerPixel>step*.2?step/length:worldPerPixel;
    if (length*worldPerPixel<=step*.2) axis.set(0,-1);else axis.normalize();
    drag={plane:selected,point:selected.point.slice(),normal:direction,axis,perPixel,
      x:event.clientX,y:event.clientY,pointerId:event.pointerId};
    controls.enabled=false;
    handle.setPointerCapture(event.pointerId);
    event.preventDefault();
  });
  handle.addEventListener('pointermove',event=>{
    if (drag?.pointerId!==event.pointerId) return;
    const distance=((event.clientX-drag.x)*drag.axis.x+(event.clientY-drag.y)*drag.axis.y)*drag.perPixel;
    drag.plane.point=drag.point.map((value,i)=>value+distance*drag.normal[i]);
    xyz.forEach((input,i)=>input.value=Number(drag.plane.point[i].toPrecision(10)));
    if (!dragFrame) dragFrame=requestAnimationFrame(()=>{dragFrame=0;render();});
  });
  for (const event of ['pointerup','pointercancel','lostpointercapture']) handle.addEventListener(event,finishDrag);

  function ensureContourField(field) {
    if (!fieldLabels[field]&&field!=='safety') $('Display').value='umag';
  }
  mode.addEventListener('change',()=>{
    finishDrag();
    if (mode.value!=='surface') ensureContourField(getState().field);
    draw();
  });
  $('AddSection').addEventListener('click',()=>{
    const {mesh,result,field}=getState();
    if (!mesh||!result) return;
    const orientation=['XY','XZ','YZ'][(nextNumber-1)%3];
    selected={number:nextNumber++,orientation,point:bounds(mesh).center.toArray(),normal:[...sectionNormals[orientation]],visible:true};
    planes.push(selected);
    ensureContourField(field);
    if (mode.value==='surface') mode.value='sections';
    refreshEditor();draw();
  });
  $('RemoveSection').addEventListener('click',()=>{
    if (!selected) return;
    const index=planes.indexOf(selected);
    planes.splice(index,1);
    selected=planes[Math.min(index,planes.length-1)]||null;
    refreshEditor();render();
  });
  planePicker.addEventListener('change',()=>{
    selected.orientation=planePicker.value;
    if (selected.orientation!=='custom') selected.normal=[...sectionNormals[selected.orientation]];
    refreshEditor();render();
  });
  for (const [inputs,key] of [[xyz,'point'],[normals,'normal']]) inputs.forEach((input,i)=>{
    input.addEventListener('change',()=>{
      if (!selected) return;
      if (Number.isFinite(input.valueAsNumber)) selected[key][i]=input.valueAsNumber;
      else input.value=selected[key][i];
      render();
    });
  });
  return {
    mode:()=>active()?mode.value:'surface',
    selectSurfaceForModel(field) {
      if (!fieldLabels[field]&&field!=='safety') {finishDrag();mode.value='surface';}
    },
    render,
    frame:handlePosition,
    finishDrag,
    snapshot:()=>({mode:mode.value,planes}),
    load(saved) {
      finishDrag();
      const vector=value=>Array.isArray(value)&&value.length===3&&value.every(Number.isFinite);
      planes=(Array.isArray(saved?.planes)?saved.planes:[]).filter(p=>vector(p?.point)&&vector(p.normal))
        .map((p,i)=>({number:i+1,orientation:Object.hasOwn(sectionNormals,p.orientation)?p.orientation:'custom',
          point:p.point,normal:Object.hasOwn(sectionNormals,p.orientation)?[...sectionNormals[p.orientation]]:p.normal,visible:p.visible!==false}));
      selected=planes[0]||null;
      nextNumber=planes.length+1;
      mode.value=['sections','context'].includes(saved?.mode)?saved.mode:'surface';
      refreshEditor();
    }
  };
}
