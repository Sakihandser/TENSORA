'use strict';
// Small structured meshes for the dynamics regression tests.

// Box [x0,x0+L]x[y0,y0+B]x[z0,z0+H] split into 5 tets per hexahedron.
function boxTets(nx,ny,nz,L,B,H,origin=[0,0,0],offset=0){
  const id=(i,j,k)=>offset+i*(ny+1)*(nz+1)+j*(nz+1)+k;
  const nodes=[];
  for(let i=0;i<=nx;i++)for(let j=0;j<=ny;j++)for(let k=0;k<=nz;k++)nodes.push([origin[0]+i*L/nx,origin[1]+j*B/ny,origin[2]+k*H/nz]);
  const tets=[];
  for(let i=0;i<nx;i++)for(let j=0;j<ny;j++)for(let k=0;k<nz;k++){
    const c=[id(i,j,k),id(i+1,j,k),id(i+1,j+1,k),id(i,j+1,k),id(i,j,k+1),id(i+1,j,k+1),id(i+1,j+1,k+1),id(i,j+1,k+1)];
    const even=(i+j+k)%2===0;
    const pattern=even?[[0,1,3,4],[1,2,3,6],[1,3,4,6],[3,4,6,7],[1,4,5,6]]:[[0,1,2,5],[0,2,3,7],[0,5,7,4],[2,5,6,7],[0,2,5,7]];
    for(const t of pattern)tets.push(t.map(q=>c[q]));
  }
  return {nodes,tets};
}

// 3D solid payload: boxes become volumes "1", "2", ... with one material.
function solidPayload(boxes,material,conditions=[]){
  const nodes=[],tets=[],tetVolumes=[];
  boxes.forEach((b,v)=>{
    const part=boxTets(...b.n,...b.size,b.origin||[0,0,0],nodes.length);
    nodes.push(...part.nodes);
    for(const t of part.tets){tets.push(t);tetVolumes.push(String(v+1));}
  });
  const volumeMaterials=Object.fromEntries(boxes.map((_,v)=>[String(v+1),material.id]));
  return {mesh:{nodes,tets,tetVolumes,surfaces:[],volumes:boxes.map((_,v)=>({id:String(v+1)}))},
    settings:{materials:[material],volumeMaterials,conditions}};
}

// 2D direct model (TRI3) of rectangles; materials in Pa as in the calculation export.
function planeModel(rects,material){
  const nodes=[],elements=[];
  rects.forEach(r=>{
    const [nx,ny]=r.n,[L,H]=r.size,[x0,y0]=r.origin||[0,0];
    const base=nodes.length;
    for(let i=0;i<=nx;i++)for(let j=0;j<=ny;j++)nodes.push({nodeNo:nodes.length+1,x:x0+i*L/nx,y:y0+j*H/ny,forceX:0,forceY:0,fixUx:false,fixUy:false});
    const id=(i,j)=>base+i*(ny+1)+j+1;
    for(let i=0;i<nx;i++)for(let j=0;j<ny;j++){
      const a=id(i,j),b=id(i+1,j),c=id(i+1,j+1),d=id(i,j+1);
      for(const t of [[a,b,c],[a,c,d]])elements.push({elementNo:elements.length+1,node1:t[0],node2:t[1],node3:t[2],materialNo:1,
        elasticModulus:material.E,poissonRatio:material.nu,density:material.rho});
    }
  });
  return {nodes,elements,materials:[{materialNo:1,id:material.id,name:material.name,density:material.rho,yieldStrength:material.yieldStrength||0}]};
}

module.exports={boxTets,solidPayload,planeModel};
