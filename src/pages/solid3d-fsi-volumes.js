import * as THREE from '../vendor/three/three.module.js';
import {FSI_FIELD_LABELS,fsiFieldUnit} from './solid3d-fsi.js';

const quantities={...FSI_FIELD_LABELS,q:'Q 判据',lambda2:'λ₂ 判据'};
const unit=key=>fsiFieldUnit(key)||'1/s²';

function raycast(data,opacity){
  const {texture,dims,lower,upper}=data;
  const volume=new THREE.Data3DTexture(texture,...dims);
  volume.format=THREE.RGFormat;
  volume.minFilter=volume.magFilter=THREE.LinearFilter;
  volume.unpackAlignment=1;
  volume.needsUpdate=true;
  const uniforms={volume:{value:volume},eye:{value:new THREE.Vector3()},opacity:{value:opacity}};
  const mesh=new THREE.Mesh(new THREE.BoxGeometry(),new THREE.ShaderMaterial({
    glslVersion:THREE.GLSL3,uniforms,transparent:true,depthWrite:false,side:THREE.BackSide,
    vertexShader:`
      out vec3 point;
      void main(){
        point=position+vec3(0.5);
        gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);
      }`,
    fragmentShader:`
      precision highp sampler3D;
      uniform sampler3D volume;
      uniform vec3 eye;
      uniform float opacity;
      in vec3 point;
      out vec4 imageColor;
      void main(){
        vec3 dir=normalize(point-eye);
        vec3 inverseDir=1.0/(sign(dir+vec3(1e-8))*max(abs(dir),vec3(1e-8)));
        vec3 a=-eye*inverseDir, b=(1.0-eye)*inverseDir;
        vec3 near=min(a,b);
        float entry=max(0.0,max(near.x,max(near.y,near.z)));
        float exitDistance=length(point-eye);
        if(exitDistance<=entry) discard;
        float spacing=(exitDistance-entry)/128.0;
        vec4 accum=vec4(0.0);
        for(int i=0;i<128;i++){
          vec2 sampleValue=texture(volume,eye+dir*(entry+(float(i)+0.5)*spacing)).rg;
          float coverage=sampleValue.g;
          if(coverage<0.4) continue;
          float value=clamp(sampleValue.r/coverage,0.0,1.0);
          vec3 color=mix(vec3(0.10,0.34,0.82),vec3(0.97,0.25,0.06),smoothstep(0.0,1.0,value));
          float alpha=1.0-exp(-opacity*spacing*coverage*(0.12+2.7*value));
          accum.rgb+=(1.0-accum.a)*alpha*color;
          accum.a+=(1.0-accum.a)*alpha;
          if(accum.a>0.98) break;
        }
        if(accum.a<0.002) discard;
        imageColor=vec4(accum.rgb/accum.a,accum.a);
      }`
  }));
  mesh.position.set(...lower.map((v,i)=>(v+upper[i])/2));
  mesh.scale.set(...upper.map((v,i)=>v-lower[i]));
  mesh.onBeforeRender=(_renderer,_scene,camera)=>{
    uniforms.eye.value.copy(camera.position);
    mesh.worldToLocal(uniforms.eye.value);
    uniforms.eye.value.addScalar(.5);
  };
  return mesh;
}

export function createFsiVolumes(scene,draw,colorFor){
  const $=name=>document.getElementById('solid3dFsi'+name);
  const group=new THREE.Group();scene.add(group);
  const mode=$('VolumeMode'),field=$('VolumeField'),level=$('IsoLevel'),opacity=$('VolumeOpacity'),summary=$('VolumeStatus');
  const options=Object.entries(quantities).map(([key,label])=>new Option(`${label} (${unit(key)})`,key));
  field.replaceChildren(...options);field.value='vmag';
  let worker=null,mesh=null,runId=null,sequence=0,current=null,pending=null,busy=false,resultShown=null;

  function clearDisplay(){
    for(const object of [...group.children]){
      group.remove(object);
      object.geometry.dispose();
      object.material.uniforms?.volume?.value.dispose();
      object.material.dispose();
    }
    resultShown=null;
  }
  function clear(){
    worker?.terminate();worker=null;current=null;pending=null;busy=false;mesh=null;runId=null;
    clearDisplay();
  }
  function process(){
    if(busy||!pending)return;
    if(!worker){
      worker=new Worker(new URL('../core/fsi-volume-worker.js',import.meta.url));
      worker.postMessage({mesh:{nodes:mesh.nodes,tets:mesh.tets,tetVolumes:mesh.tetVolumes}});
      worker.onmessage=({data})=>{
        busy=false;
        if(current?.id===data.id){current.result=data;draw();}
        process();
      };
      worker.onerror=()=>{
        worker.terminate();worker=null;pending=null;busy=false;
        if(current){current.result={error:'三维场计算进程异常。'};draw();}
      };
    }
    const {frame,...options}=pending;
    const fields=frame.particles?{}:FsiPost.packFields(frame,[options.field,'vx','vy','vz','vmag']);
    busy=true;
    worker.postMessage({...options,frame:frame.index,fields},Object.values(fields).map(values=>values.buffer));
    pending=null;
  }
  for(const input of [mode,field,level,opacity,$('SphLevel')])input.addEventListener('change',()=>{
    if(input===field||input===mode)level.value='';
    draw();
  });
  function update({mesh:view,run,frame,hidden}){
    const sph=Boolean(frame?.particles);
    mode.disabled=!frame;
    for(const option of mode.options)option.hidden=option.value==='particles'?!sph:option.value!=='none'&&sph;
    if(frame&&mode.selectedOptions[0]?.hidden)mode.value='none';
    const active=frame&&view&&mode.value!=='none'&&(mode.value==='particles')===sph;
    $('VolumeSettings').hidden=!active;
    $('VolumeFieldRow').hidden=sph;$('IsoLevelRow').hidden=mode.value!=='iso';
    $('SphLevelRow').hidden=!sph;$('VolumeOpacityRow').hidden=mode.value!=='volume';
    if(!active){if(mesh)clear();return;}
    if(view!==mesh||run.runId!==runId){clear();mesh=view;runId=run.runId;}
    const velocity=['vx','vy','vz'].every(key=>frame.nodeFields[key]);
    for(const option of options)option.disabled=!(frame.nodeFields[option.value]||velocity&&['q','lambda2'].includes(option.value));
    if(field.selectedOptions[0]?.disabled)field.value=options.find(option=>!option.disabled)?.value||'';
    const visible=Object.keys(run.settings.volumeRoles||{}).filter(id=>run.settings.volumeRoles[id]==='fluid'&&!hidden.has(id)).sort();
    if(!visible.length||!sph&&!field.value){clearDisplay();current=null;pending=null;summary.textContent='当前没有可用的可见流体结果。';return;}
    const isovalue=sph?Number($('SphLevel').value):level.valueAsNumber;
    const signature=[frame.index,mode.value,field.value,isovalue,...visible].join('/');
    if(current?.signature!==signature){
      clearDisplay();
      const id=++sequence;
      current={signature,id,result:null};
      pending={id,frame,mode:mode.value,field:field.value,level:isovalue,visible,engine:run.engine,
        particlePositions:frame.particles?.positions,spacing:run.meta?.spacing};
      process();
    }
    const data=current.result;
    if(!data||data.error){summary.textContent=data?.error||'正在生成当前帧的三维图层…';return;}
    if(data===resultShown){
      if(data.mode==='volume')group.children[0].material.uniforms.opacity.value=Number(opacity.value);
      return;
    }
    resultShown=data;
    const format=ResultProbe.formatValue;
    if(data.mode==='volume'){
      group.add(raycast(data,Number(opacity.value)));
      const ramp=document.createElement('span');ramp.className='fsi-stream-ramp fsi-volume-ramp';
      summary.replaceChildren(`采样网格 ${data.dims.join(' × ')}`,document.createElement('br'),
        format(data.min),ramp,`${format(data.max)} ${unit(field.value)}`);
      return;
    }
    const count=data.positions.length/9;
    summary.textContent=data.mode==='particles'
      ?`水面 ${count.toLocaleString()} 个三角面 · 网格间距 ${format(data.resolution)} m`
      :`等值 ${format(data.level)} ${unit(field.value)} · ${count.toLocaleString()} 个三角面 · 场范围 ${format(data.min)} 至 ${format(data.max)}`;
    if(!count)return;
    const geo=new THREE.BufferGeometry();
    geo.setAttribute('position',new THREE.BufferAttribute(data.positions,3));
    geo.computeVertexNormals();
    const useColors=data.colors?.length&&frame.maxVelocity>0;
    if(useColors){
      const colors=new Float32Array(data.colors.length*3);
      data.colors.forEach((value,i)=>colorFor(value,0,frame.maxVelocity).toArray(colors,i*3));
      geo.setAttribute('color',new THREE.BufferAttribute(colors,3));
      summary.textContent+=' · 按流速着色';
    }
    group.add(new THREE.Mesh(geo,new THREE.MeshStandardMaterial({color:useColors?0xffffff:0x279abd,
      vertexColors:Boolean(useColors),side:THREE.DoubleSide,roughness:.55,transparent:sph,opacity:sph ? .75 : 1,depthWrite:!sph})));
  }
  return {update,clear,transparent:()=>Boolean(current)&&mode.value!=='particles',
    hasWaterSurface:()=>mode.value==='particles'&&group.children.length>0,pending:()=>Boolean(current&&!current.result)};
}
