'use strict';
importScripts('./fsi-post.js','./fsi-volume.js');
let mesh=null,cache=null;

self.onmessage=({data})=>{
  if(data.mesh){mesh=data.mesh;cache=null;return;}
  const {id,frame,mode,field,fields,engine,visible,level,particlePositions,spacing}=data;
  try{
    if(mode==='particles'){
      const {positions,resolution}=FsiVolume.particleSurface(particlePositions,spacing,level);
      self.postMessage({id,mode,positions,resolution},[positions.buffer]);
      return;
    }
    const key=frame+'/'+visible.join(',');
    if(cache?.key!==key){
      const active=new Set(visible),include=i=>active.has(String(mesh.tetVolumes[i]));
      cache={key,include,nodes:FsiPost.flowNodes(mesh.nodes,fields,engine),vortices:{}};
    }
    const {nodes,include}=cache;
    const values=fields[field]||(cache.vortices[field]??=FsiVolume.vortexField(nodes,mesh.tets,include,fields,field));
    let min=Infinity,max=-Infinity;
    for(let i=0;i<mesh.tets.length;i++)if(include(i))for(const n of mesh.tets[i]){
      const value=values[n];
      if(Number.isFinite(value)){min=Math.min(min,value);max=Math.max(max,value);}
    }
    if(!Number.isFinite(min)){self.postMessage({id,mode,error:'可见流体域没有有效数据。'});return;}
    if(mode==='iso'){
      if(!Number.isFinite(level)&&(field==='q'&&max<=0||field==='lambda2'&&min>=0)){
        self.postMessage({id,mode,error:field==='q'?'可见区域没有正值 Q。':'可见区域没有负值 λ₂。'});return;
      }
      const isovalue=Number.isFinite(level)?level:field==='q'&&max>0?max*.15:field==='lambda2'&&min<0?min*.15:(min+max)/2;
      const {positions,colors}=FsiVolume.isosurface(mesh.tets,nodes,values,isovalue,include,fields.vmag);
      self.postMessage({id,mode,positions,colors,min,max,level:isovalue},[positions.buffer,colors.buffer]);
      return;
    }
    const locator=cache.locator??=FsiPost.createLocator(nodes,mesh.tets,3,include);
    const {min:lower,max:upper}=locator.bounds;
    const sizes=upper.map((value,i)=>value-lower[i]),longest=Math.max(...sizes);
    const [nx,ny,nz]=sizes.map(s=>Math.max(2,Math.ceil(56*s/longest)));
    const texture=new Uint8Array(nx*ny*nz*2);
    for(let z=0;z<nz;z++)for(let y=0;y<ny;y++){
      let last=null;
      for(let x=0;x<nx;x++){
        const point=[(x+.5)/nx,(y+.5)/ny,(z+.5)/nz].map((f,i)=>lower[i]+sizes[i]*f);
        const hit=locator.locate(point,last),value=FsiPost.interpolate(values,hit);
        last=hit?.cell;
        if(!Number.isFinite(value))continue;
        const index=2*((z*ny+y)*nx+x);
        texture[index]=Math.round(255*(max>min?(value-min)/(max-min):.5));
        texture[index+1]=255;
      }
    }
    self.postMessage({id,mode,texture,dims:[nx,ny,nz],lower,upper,min,max},[texture.buffer]);
  }catch(error){
    self.postMessage({id,mode,error:error.message});
  }
};
