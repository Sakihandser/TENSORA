import * as THREE from '../vendor/three/three.module.js';
import {sectionValues} from './solid3d-sections.js';

const components=['vx','vy','vz'];
export const hasVelocity=fields=>components.every(key=>fields?.[key]?.length);

export function addTriangleVelocity(samples,positions,offset,fields,ids){
  const velocity=components.map(key=>(fields[key][ids[0]]+fields[key][ids[1]]+fields[key][ids[2]])/3);
  if(!velocity.every(Number.isFinite))return;
  const [x,y,z]=[0,1,2].map(k=>(positions[offset+k]+positions[offset+k+3]+positions[offset+k+6])/3);
  samples.push(x,y,z,...velocity);
}

export function sectionVelocitySamples(mesh,cuts,frame,volumeRoles){
  const samples=[];
  for(const cut of cuts){
    const fields=Object.fromEntries(components.map(key=>[key,sectionValues(cut,frame,key)]));
    cut.elements.forEach((tet,i)=>{
      const role=volumeRoles?.[mesh.tetVolumes?.[tet]];
      if(!role||role==='fluid')addTriangleVelocity(samples,cut.positions,i*9,fields,[i*3,i*3+1,i*3+2]);
    });
  }
  return samples;
}

export function particleVelocitySamples({positions,values,count}){
  const samples=[];
  const {vx,vy,vz}=values;
  const stride=Math.max(1,Math.ceil(count/16000));
  for(let i=0;i<count;i+=stride){
    if(![vx[i],vy[i],vz[i]].every(Number.isFinite))continue;
    samples.push(positions[i*3],positions[i*3+1],positions[i*3+2],vx[i],vy[i],vz[i]);
  }
  return samples;
}

export function createVelocityVectors(scene,camera,controls,host){
  const line=new THREE.LineSegments(new THREE.BufferGeometry(),new THREE.LineBasicMaterial({
    color:0x152c37,transparent:true,opacity:.92,depthWrite:false
  }));
  line.name='FSI velocity vectors';
  line.frustumCulled=false;
  line.renderOrder=10;
  line.visible=false;
  scene.add(line);
  let samples=[],maximum=0,dirty=false;
  const invalidate=()=>{dirty=true;};
  controls.addEventListener('change',invalidate);

  function setSamples(next,maxSpeed){
    samples=next;
    maximum=maxSpeed;
    if(samples.length&&(!Number.isFinite(maximum)||maximum<=0)){
      maximum=0;
      for(let i=0;i<samples.length;i+=6)maximum=Math.max(maximum,Math.hypot(samples[i+3],samples[i+4],samples[i+5]));
    }
    if(!samples.length)line.visible=false;
    invalidate();
  }

  function render(){
    if(!dirty)return;
    dirty=false;
    const width=host.clientWidth,height=host.clientHeight;
    if(!samples.length||!(maximum>0)||!width||!height)return;
    camera.updateMatrixWorld();
    const point=new THREE.Vector3(),viewPoint=new THREE.Vector3(),start=new THREE.Vector3(),end=new THREE.Vector3();
    const selected=new Map(),spacing=36;
    const forward=camera.getWorldDirection(new THREE.Vector3());
    // Sample in screen space so zooming exposes more vectors without crowding the view.
    for(let i=0;i<samples.length;i+=6){
      point.set(samples[i],samples[i+1],samples[i+2]);
      start.copy(point).project(camera);
      if(Math.abs(start.x)>1||Math.abs(start.y)>1||Math.abs(start.z)>1)continue;
      viewPoint.copy(point).applyMatrix4(camera.matrixWorldInverse);
      const worldPerPixel=-2*viewPoint.z/(camera.projectionMatrix.elements[5]*height);
      if(!(worldPerPixel>0))continue;
      const scale=worldPerPixel*25/maximum;
      end.set(samples[i+3],samples[i+4],samples[i+5]).multiplyScalar(scale).add(point).project(camera);
      const x=(start.x+1)*width/2,y=(start.y+1)*height/2;
      const dx=(end.x-start.x)*width/2,dy=(end.y-start.y)*height/2;
      const length=Math.hypot(dx,dy);
      if(!(length>=2))continue;
      const key=`${Math.floor(x/spacing)},${Math.floor(y/spacing)}`;
      if(selected.has(key)&&selected.get(key).z<=start.z)continue;
      // Keep the arrow just in front of its contour or surface to avoid depth flicker.
      const depth=end.copy(point).addScaledVector(forward,-2*worldPerPixel).project(camera).z;
      const shorten=Math.min(1,25/length);
      selected.set(key,{x,y,z:start.z,depth,dx:dx*shorten,dy:dy*shorten});
    }
    const positions=[],vertex=new THREE.Vector3();
    const add=(x,y,z)=>{vertex.set(2*x/width-1,2*y/height-1,z).unproject(camera);positions.push(vertex.x,vertex.y,vertex.z);};
    for(const {x,y,depth,dx,dy} of selected.values()){
      const tipX=x+dx,tipY=y+dy;
      add(x,y,depth);add(tipX,tipY,depth);
      for(const side of [-1,1]){
        add(tipX,tipY,depth);
        add(tipX-.32*dx+side*.16*dy,tipY-.32*dy-side*.16*dx,depth);
      }
    }
    line.geometry.dispose();
    line.geometry=new THREE.BufferGeometry();
    line.geometry.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));
    line.visible=positions.length>0;
  }

  return {setSamples,invalidate,render};
}
