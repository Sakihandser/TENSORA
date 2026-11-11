import * as THREE from '../vendor/three/three.module.js';
import { interpolateLoad, isPressureLoad, openEdgePath, segmentParameter, surfaceLoadValue }
  from '../core/solid3d-restraint-data.js';

const mix=(a,b,t)=>a.map((value,i)=>value+(b[i]-value)*t);

function clipPolygon(polygon,axis,limit,sign){
  const clipped=[];
  for(let i=0;i<polygon.length;i++){
    const a=polygon[i], b=polygon[(i+1)%polygon.length];
    const da=(a[axis]-limit)*sign, db=(b[axis]-limit)*sign;
    if(da>=0)clipped.push(a);
    if((da<0&&db>0)||(da>0&&db<0))clipped.push(mix(a,b,da/(da-db)));
  }
  return clipped;
}

function surfaceSamples(view,faces,patch){
  const pieces=[];
  let totalArea=0;
  for(const face of faces){
    const stride=patch?1:Math.max(1,Math.ceil(face.indices.length/1200));
    for(let sample=0;sample<face.indices.length;sample+=stride){
      const index=face.indices[sample];
      const original=face.surface.triangles[index].map(id=>view.nodes[id]);
      const [a,b,c]=original.map(point=>new THREE.Vector3(...point));
      const normal=b.sub(a).cross(c.sub(a)).normalize();
      normal.multiplyScalar(face.surface.trianglePressureSigns?.[index]??-1);
      let polygon=original;
      if(patch)for(let axis=0;axis<3;axis++){
        if(axis===patch.axis)continue;
        polygon=clipPolygon(clipPolygon(polygon,axis,patch.min[axis],1),axis,patch.max[axis],-1);
      }
      for(let i=1;i+1<polygon.length;i++){
        const [p,q,r]=[polygon[0],polygon[i],polygon[i+1]];
        const area=new THREE.Vector3(...q).sub(new THREE.Vector3(...p))
          .cross(new THREE.Vector3(...r).sub(new THREE.Vector3(...p))).length()/2;
        if(area>0){totalArea+=area;pieces.push({points:[p,q,r],normal:normal.toArray(),limit:totalArea});}
      }
    }
  }
  const samples=[];
  let j=0;
  for(let i=0;i<15&&pieces.length;i++){
    const target=totalArea*(i+.5)/15;
    while(pieces[j].limit<target&&j+1<pieces.length)j++;
    const {points,normal}=pieces[j];
    const u=Math.sqrt((i*.61803398875+.29)%1),v=(i*.41421356237+.31)%1;
    const point=points[0].map((value,d)=>(1-u)*value+u*((1-v)*points[1][d]+v*points[2][d]));
    samples.push({point,normal});
  }
  return samples;
}

function segmentSamples(segments,parameters){
  let total=0;
  const pieces=segments.map(([a,b],i)=>{
    const length=Math.hypot(...b.map((value,d)=>value-a[d]));
    total+=length;
    return {a,b,length,limit:total,parameters:parameters?.[i]};
  }).filter(piece=>piece.length>0);
  if(!pieces.length)return [];
  let j=0;
  return Array.from({length:9},(_,i)=>{
    const distance=i*total/8;
    while(pieces[j].limit<distance&&j+1<pieces.length)j++;
    const piece=pieces[j],t=Math.min(1,Math.max(0,1+(distance-piece.limit)/piece.length));
    const [from,to]=piece.parameters||[0,0];
    return {point:mix(piece.a,piece.b,t),t:from+t*(to-from)};
  });
}

function lineSamples(view,guide,entities,faces,scale){
  if(!entities&&guide.kind==='line'){
    // Draft line samples are clipped to the selected CAD face, including holes.
    const point=new THREE.Vector3(),nearest=new THREE.Vector3();
    const triangles=faces.flatMap(({surface,indices})=>indices.map(index=>new THREE.Triangle(
      ...surface.triangles[index].map(id=>new THREE.Vector3(...view.nodes[id])))));
    return segmentSamples([[guide.start,guide.end]],[[0,1]]).filter(sample=>{
      point.fromArray(sample.point);
      return triangles.some(triangle=>triangle.closestPointToPoint(point,nearest)
        .distanceToSquared(point)<=(scale*1e-7)**2);
    });
  }
  const edges=(view.edges||[]).filter(edge=>entities?entities.includes(String(edge.id)):Number(edge.id)===guide.entity);
  let ids=edges.flatMap(edge=>edge.segments);
  let parameters;
  if(guide.load.type==='linearLineTraction'&&guide.kind==='edge'){
    const path=openEdgePath(ids,view.nodes);
    if(!path)return [];
    ids=path.ids.slice(1).map((id,i)=>[path.ids[i],id]);
    parameters=ids.map(segment=>segment.map(id=>path.distances.get(id)/path.length));
  }else if(guide.load.type==='linearLineTraction'){
    parameters=ids.map(segment=>segment.map(id=>segmentParameter(guide,view.nodes[id])));
  }
  return segmentSamples(ids.map(segment=>segment.map(id=>view.nodes[id])),parameters);
}

export function drawLoadGlyphs(group,view,guide,binding,visibleFaces,scale){
  const {load,kind}=guide;
  const entities=binding?.entities;
  const faces=visibleFaces.filter(({surface})=>entities?entities.includes(String(surface.id)):Number(surface.id)===guide.entity);
  let samples;
  if(kind==='point'){
    const point=binding?view.nodes[binding.nodes[0]]:guide.at;
    samples=point?[{point}]:[];
  }else if(kind==='line'||kind==='edge'){
    samples=lineSamples(view,guide,entities,faces,scale);
  }else{
    samples=surfaceSamples(view,faces,!entities&&kind==='patch'?guide:null);
  }
  const vectors=samples.map(({point,normal,t})=>{
    if(load.type==='linearLineTraction')return interpolateLoad(load,load.reverse?1-t:t);
    const value=surfaceLoadValue(load,point);
    return isPressureLoad(load.type)?normal.map(component=>component*value):value;
  });
  const maximum=Math.max(0,...vectors.map(vector=>Math.hypot(...vector)));
  let count=0;
  samples.forEach(({point},i)=>{
    const vector=new THREE.Vector3(...vectors[i]),magnitude=vector.length();
    if(!(magnitude>0&&maximum>0))return;
    const direction=vector.divideScalar(magnitude);
    const length=.15*scale*magnitude/maximum;
    const origin=new THREE.Vector3(...point).addScaledVector(direction,-length);
    const arrow=new THREE.ArrowHelper(direction,origin,length,0xb84608,length*.27,length*.14);
    for(const child of arrow.children){child.material.depthTest=false;child.material.depthWrite=false;child.renderOrder=4;}
    group.add(arrow);
    count++;
  });
  return count;
}
