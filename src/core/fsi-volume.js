(function(root){
  'use strict';
  const edges=[[0,1],[0,2],[0,3],[1,2],[1,3],[2,3]];
  const minus=(a,b)=>a.map((x,i)=>x-b[i]);
  const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
  const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
  const mix=(a,b,t)=>a.map((x,i)=>x+(b[i]-x)*t);

  function middleEigenvalue(m){
    const offDiagonal=m[0][1]**2+m[0][2]**2+m[1][2]**2;
    if(!offDiagonal)return [m[0][0],m[1][1],m[2][2]].sort((a,b)=>a-b)[1];
    const mean=(m[0][0]+m[1][1]+m[2][2])/3;
    const d=[m[0][0]-mean,m[1][1]-mean,m[2][2]-mean];
    const p=Math.sqrt((dot(d,d)+2*offDiagonal)/6);
    if(!p)return mean;
    const scaled=m.map((row,i)=>row.map((x,j)=>(i===j?x-mean:x)/p));
    const r=dot(scaled[0],cross(scaled[1],scaled[2]))/2;
    const angle=Math.acos(Math.abs(r)>1-8*Number.EPSILON?Math.sign(r):r)/3;
    return mean+2*p*Math.cos(angle-2*Math.PI/3);
  }
  function vortexCriterion(gradient,criterion){
    if(criterion==='q'){
      // Match SU2's CFlowOutput::GetQCriterion: ||Ω||² − ||S||² = −tr(G²).
      let traceSquared=0;
      for(let i=0;i<3;i++)for(let j=0;j<3;j++)traceSquared+=gradient[i][j]*gradient[j][i];
      return -traceSquared;
    }
    const square=gradient.map((row,i)=>row.map((_,j)=>{
      let sum=0;
      for(let k=0;k<3;k++)sum+=(gradient[i][k]*gradient[k][j]+gradient[j][k]*gradient[k][i])/2;
      return sum;
    }));
    return middleEigenvalue(square);
  }
  function vortexField(nodes,cells,include,fields,criterion){
    const sums=new Float64Array(nodes.length),weights=new Float64Array(nodes.length);
    const velocity=['vx','vy','vz'].map(key=>fields[key]);
    if(velocity.some(axis=>!axis))return Float64Array.from(sums,()=>NaN);
    for(let i=0;i<cells.length;i++){
      if(!include(i))continue;
      const ids=cells[i],p=nodes[ids[0]],[a,b,c]=ids.slice(1).map(id=>minus(nodes[id],p));
      const rows=[cross(b,c),cross(c,a),cross(a,b)],volume=dot(a,rows[0]);
      if(!Number.isFinite(volume)||volume===0)continue;
      const grad=velocity.map(axis=>{
        const dvs=ids.slice(1).map(id=>axis[id]-axis[ids[0]]);
        return [0,1,2].map(d=>dvs.reduce((s,x,j)=>s+x*rows[j][d],0)/volume);
      });
      const value=vortexCriterion(grad,criterion);
      if(!Number.isFinite(value))continue;
      const weight=Math.abs(volume);
      for(const id of ids){sums[id]+=value*weight;weights[id]+=weight;}
    }
    return Float64Array.from(sums,(sum,i)=>weights[i]?sum/weights[i]:NaN);
  }

  // Marching tetrahedra, with optional independent coloring on each edge.
  function isosurface(tets,nodes,values,level,include=()=>true,colorValues=null){
    const positions=[],colors=[],seen=new Set();
    for(let i=0;i<tets.length;i++){
      if(!include(i))continue;
      const ids=tets[i],scalar=ids.map(id=>values[id]);
      if(!scalar.every(Number.isFinite)||Math.min(...scalar)>level||Math.max(...scalar)<=level)continue;
      const poly=[];
      for(const [a,b] of edges){
        const va=scalar[a],vb=scalar[b];
        if((va>level)===(vb>level))continue;
        const t=(level-va)/(vb-va),ia=ids[a],ib=ids[b];
        const key=t===0?String(ia):t===1?String(ib):`${Math.min(ia,ib)}:${Math.max(ia,ib)}`;
        if(poly.some(v=>v.key===key))continue;
        const color=colorValues?(t===0?colorValues[ia]:t===1?colorValues[ib]:colorValues[ia]*(1-t)+colorValues[ib]*t):level;
        poly.push({key,point:mix(nodes[ia],nodes[ib],t),color});
      }
      if(poly.length<3)continue;
      if(poly.every(v=>!v.key.includes(':'))){
        const key=poly.map(v=>v.key).sort().join(',');
        if(seen.has(key))continue;
        seen.add(key);
      }
      const origin=poly[0].point,u=minus(poly[1].point,origin),n=cross(u,minus(poly[2].point,origin));
      if(!Math.hypot(...n))continue;
      const out=minus(origin,nodes[ids[scalar.findIndex(x=>x>level)]]);
      const v=cross(dot(n,out)<0?n.map(x=>-x):n,u);
      const center=origin.map((_,d)=>poly.reduce((s,p)=>s+p.point[d]/poly.length,0));
      poly.sort((a,b)=>angle(a)-angle(b));
      function angle(item){
        const offset=minus(item.point,center);
        return Math.atan2(dot(offset,v)/Math.hypot(...v),dot(offset,u)/Math.hypot(...u));
      }
      for(let j=1;j<poly.length-1;j++)for(const item of [poly[0],poly[j],poly[j+1]]){
        positions.push(...item.point);colors.push(item.color);
      }
    }
    return {positions:new Float32Array(positions),colors:new Float32Array(colors)};
  }
  function particleSurface(positions,spacing,threshold=.45){
    const support=2*spacing;
    if(!(support>0))return {positions:new Float32Array(),colors:new Float32Array(),resolution:0};
    const lower=[Infinity,Infinity,Infinity],upper=[-Infinity,-Infinity,-Infinity];
    for(let i=0;i<positions.length;i+=3)if(Number.isFinite(positions[i]+positions[i+1]+positions[i+2])){
      for(let d=0;d<3;d++){lower[d]=Math.min(lower[d],positions[i+d]);upper[d]=Math.max(upper[d],positions[i+d]);}
    }
    if(!Number.isFinite(lower[0]))return {positions:new Float32Array(),colors:new Float32Array(),resolution:0};
    const min=lower.map(x=>x-support),size=upper.map((x,d)=>x+support-min[d]);
    const step=Math.max(spacing*.65,Math.max(...size)/140,Math.cbrt(size.reduce((a,b)=>a*b)/300000));
    const [nx,ny,nz]=size.map(x=>Math.ceil(x/step)+1),volume=new Float32Array(nx*ny*nz);
    const id=(x,y,z)=>(z*ny+y)*nx+x;
    const norm=315/(64*Math.PI)*(spacing/support)**3;
    // Compact poly6 particle kernel splatted into a regular scalar grid.
    for(let i=0;i<positions.length;i+=3){
      const p=[0,1,2].map(d=>(positions[i+d]-min[d])/step);
      if(!p.every(Number.isFinite))continue;
      const r=support/step,lo=p.map(x=>Math.max(0,Math.ceil(x-r))),hi=p.map((x,d)=>Math.min([nx,ny,nz][d]-1,Math.floor(x+r)));
      for(let z=lo[2];z<=hi[2];z++)for(let y=lo[1];y<=hi[1];y++)for(let x=lo[0];x<=hi[0];x++){
        const q=1-((x-p[0])**2+(y-p[1])**2+(z-p[2])**2)/(r*r);
        if(q>0)volume[id(x,y,z)]+=norm*q**3;
      }
    }
    const nodes=Array.from(volume,(_,i)=>[min[0]+(i%nx)*step,min[1]+(Math.floor(i/nx)%ny)*step,min[2]+Math.floor(i/(nx*ny))*step]);
    const tets=[];
    const pattern=[[0,1,3,7],[0,3,2,7],[0,2,6,7],[0,6,4,7],[0,4,5,7],[0,5,1,7]];
    for(let z=0;z<nz-1;z++)for(let y=0;y<ny-1;y++)for(let x=0;x<nx-1;x++){
      const corners=[id(x,y,z),id(x+1,y,z),id(x,y+1,z),id(x+1,y+1,z),
        id(x,y,z+1),id(x+1,y,z+1),id(x,y+1,z+1),id(x+1,y+1,z+1)];
      const scalar=corners.map(i=>volume[i]);
      if(Math.min(...scalar)>threshold||Math.max(...scalar)<=threshold)continue;
      for(const tet of pattern)tets.push(tet.map(i=>corners[i]));
    }
    return {...isosurface(tets,nodes,volume,threshold),resolution:step};
  }
  const api={isosurface,vortexCriterion,vortexField,particleSurface};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  else root.FsiVolume=api;
})(globalThis);
