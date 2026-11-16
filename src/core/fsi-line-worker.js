'use strict';
importScripts('./fsi-post.js');
let mesh,cached;
self.onmessage=({data})=>{
  if(data.mesh){mesh=data.mesh;cached=null;return;}
  const {id,revision,visible,role,engine,fields,field,points}=data;
  try{
    if(cached?.revision!==revision){
      const nodes=role==='fluid'?FsiPost.flowNodes(mesh.nodes,fields,engine):FsiPost.deformedNodes(mesh.nodes,fields);
      const volumeIds=new Set(visible);
      cached={revision,locator:FsiPost.createLocator(nodes,mesh.tets,3,i=>volumeIds.has(String(mesh.tetVolumes[i])))};
    }
    const samples=FsiPost.lineProfile(cached.locator,...points,fields[field]);
    self.postMessage({id,samples:samples.map(({point,distance,value})=>({point,distance,value}))});
  }catch(error){self.postMessage({id,error:error.message});}
};
