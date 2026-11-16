'use strict';
importScripts('./fsi-post.js');

let mesh,geometry=null,interfaces=null;
self.onmessage=({data})=>{
  if(data.mesh){
    mesh=data.mesh;
    geometry=null;
    interfaces=null;
    return;
  }
  const {id,frame,fields,engine,visibleVolumes,solidVolumes,seedMode,direction,maxSpeed}=data;
  try{
    const key=frame+'/'+visibleVolumes.join(',');
    if(geometry?.key!==key){
      const visible=new Set(visibleVolumes);
      const nodes=FsiPost.flowNodes(mesh.nodes,fields,engine);
      const locator=FsiPost.createLocator(nodes,mesh.tets,3,i=>visible.has(String(mesh.tetVolumes[i])));
      geometry={key,locator,nodes};
    }
    const {locator,nodes}=geometry;
    const interfaceKey=visibleVolumes.join(',')+'/'+solidVolumes.join(',');
    if(seedMode==='interface'&&interfaces?.key!==interfaceKey){
      const fluid=new Set(visibleVolumes),solid=new Set(solidVolumes);
      interfaces={key:interfaceKey,facets:FsiPost.interfaceFacets(mesh.tets,
        i=>fluid.has(String(mesh.tetVolumes[i])),i=>solid.has(String(mesh.tetVolumes[i])))};
    }
    const {seeds,span,position,near,fallback}=FsiPost.flowSeeds(locator,nodes,interfaces?.facets||[],data);
    const lines=FsiPost.traceStreamlines(locator,fields,seeds,{direction,maxSpeed,localSpan:span});
    const size=lines.reduce((sum,line)=>sum+2*(line.length-1),0);
    const positions=new Float64Array(size*3),reference=new Float64Array(size*3),speeds=new Float32Array(size);
    let offset=0;
    function add({point,hit,speed}){
      positions.set(point,offset*3);
      for(let d=0;d<3;d++)reference[offset*3+d]=hit.cell.ids.reduce((sum,n,i)=>sum+hit.weights[i]*mesh.nodes[n][d],0);
      speeds[offset++]=speed;
    }
    for(const line of lines)for(let i=1;i<line.length;i++){add(line[i-1]);add(line[i]);}
    self.postMessage({id,positions,reference,speeds,position,near,fallback,count:lines.length},
      [positions.buffer,reference.buffer,speeds.buffer]);
  }catch(error){
    self.postMessage({id,error:error.message});
  }
};
