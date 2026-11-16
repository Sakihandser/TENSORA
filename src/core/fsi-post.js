(function(root){
  'use strict';
  const weightTolerance=1e-9;
  const displacement=['ux','uy','uz'], velocity=['vx','vy','vz'];
  const subtract=(a,b)=>a.map((x,i)=>x-b[i]);
  const dot=(a,b)=>a.reduce((sum,x,i)=>sum+x*b[i],0);
  const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
  const between=(a,b,t)=>a.map((x,i)=>x+t*(b[i]-x));
  const advance=(p,v,h)=>p.map((x,i)=>x+h*v[i]);
  const finiteOrZero=v=>Number.isFinite(v)?v:0;

  function deformedNodes(nodes,fields,scale=1){
    return nodes.map((p,i)=>p.map((x,d)=>x+scale*finiteOrZero(fields[displacement[d]]?.[i])));
  }
  function flowNodes(nodes,fields,engine){
    if(fields.flowUx&&fields.flowUy){
      return deformedNodes(nodes,{ux:fields.flowUx,uy:fields.flowUy,uz:fields.flowUz});
    }
    return engine==='oneway'?nodes:deformedNodes(nodes,fields);
  }

  // Index only the cells eligible for interpolation. The tree and cell
  // transforms belong to one geometry snapshot and can be reused across plots.
  function createLocator(nodes,cells,dimension,include=()=>true){
    const entries=[];
    cells.forEach((ids,index)=>{
      if(!include(index))return;
      const points=ids.map(i=>nodes[i]),origin=points[0];
      const min=origin.map((_,d)=>Math.min(...points.map(p=>p[d])));
      const max=origin.map((_,d)=>Math.max(...points.map(p=>p[d])));
      entries.push({ids,index,origin,inverse:undefined,min,max});
    });
    function build(items){
      if(!items.length)return null;
      const min=Array(dimension).fill(Infinity),max=Array(dimension).fill(-Infinity);
      for(const item of items)for(let d=0;d<dimension;d++){
        min[d]=Math.min(min[d],item.min[d]);
        max[d]=Math.max(max[d],item.max[d]);
      }
      if(items.length<=12)return {min,max,items};
      const span=subtract(max,min),axis=span.indexOf(Math.max(...span));
      const middle=(min[axis]+max[axis])/2,left=[],right=[];
      for(const item of items)((item.min[axis]+item.max[axis])/2<middle?left:right).push(item);
      if(!left.length||!right.length){
        const half=Math.floor(items.length/2);
        return {min,max,children:[build(items.slice(0,half)),build(items.slice(half))]};
      }
      return {min,max,children:[build(left),build(right)]};
    }
    const tree=build(entries),span=tree?Math.hypot(...subtract(tree.max,tree.min)):0;
    const epsilon=tree?Math.max(span*weightTolerance,8*Number.EPSILON*Math.max(...tree.min.map(Math.abs),...tree.max.map(Math.abs))):0;
    function visit(box,lo,hi,accept){
      if(!box||lo.some((x,d)=>x>box.max[d]+epsilon||hi[d]<box.min[d]-epsilon))return null;
      if(box.items){
        for(const cell of box.items){
          if(lo.some((x,d)=>x>cell.max[d]+epsilon||hi[d]<cell.min[d]-epsilon))continue;
          const hit=accept(cell);
          if(hit)return hit;
        }
        return null;
      }
      for(const child of box.children){
        const hit=visit(child,lo,hi,accept);
        if(hit)return hit;
      }
      return null;
    }
    function weights(cell,p){
      if(cell.inverse===undefined){
        const [a,b,c]=cell.ids.slice(1).map(id=>subtract(nodes[id],cell.origin));
        const rows=dimension===2?[[b[1],-b[0]],[-a[1],a[0]]]:[cross(b,c),cross(c,a),cross(a,b)];
        const determinant=dot(a,rows[0]);
        cell.inverse=determinant&&Number.isFinite(determinant)?rows.map(row=>row.map(x=>x/determinant)):null;
      }
      if(!cell.inverse)return null;
      const relative=subtract(p,cell.origin),rest=cell.inverse.map(row=>dot(row,relative));
      return [1-rest.reduce((a,b)=>a+b,0),...rest];
    }
    const inside=w=>w.every(v=>v>=-weightTolerance);
    function locate(p,hint){
      const test=cell=>{
        const w=weights(cell,p);
        return w&&inside(w)?{cell,weights:w}:null;
      };
      return (hint&&test(hint))||visit(tree,p,p,test);
    }
    // Clip the segment to each intersected simplex. Reject any uncovered
    // interval, even when both endpoints happen to lie in valid fluid cells.
    function segmentSpans(a,b){
      const lo=a.map((x,i)=>Math.min(x,b[i])),hi=a.map((x,i)=>Math.max(x,b[i])),intervals=[];
      visit(tree,lo,hi,cell=>{
        const from=weights(cell,a),to=weights(cell,b);
        if(!from||!to)return null;
        let first=0,last=1;
        for(let i=0;i<from.length;i++){
          if(from[i]<-weightTolerance&&to[i]<-weightTolerance)return null;
          if(from[i]<-weightTolerance)first=Math.max(first,-from[i]/(to[i]-from[i]));
          if(to[i]<-weightTolerance)last=Math.min(last,-from[i]/(to[i]-from[i]));
        }
        if(last>first)intervals.push({first,last,cell});
        return null;
      });
      return intervals.sort((a,b)=>a.first-b.first||b.last-a.last);
    }
    function connected(a,b,start,end){
      if(start.cell===end.cell)return true;
      let reach=0;
      for(const {first,last} of segmentSpans(a,b)){
        if(first>reach+weightTolerance)return false;
        reach=Math.max(reach,last);
      }
      return reach>=1-weightTolerance;
    }
    return {bounds:tree&&{min:tree.min,max:tree.max},span,locate,connected,segmentSpans,weights};
  }

  function interpolate(values,hit){
    if(!values||!hit)return NaN;
    let value=0;
    for(let i=0;i<hit.weights.length;i++){
      const weight=hit.weights[i];
      if(weight<=weightTolerance)continue;
      const v=values[hit.cell.ids[i]];
      if(!Number.isFinite(v))return NaN;
      value+=weight*v;
    }
    return value;
  }

  function seedPlane({min,max},axis,fraction,density){
    let seeds=[min.map((x,i)=>x+(max[i]-x)*fraction)];
    for(let d=0;d<min.length;d++)if(d!==axis){
      const dir=d;
      seeds=seeds.flatMap(seed=>Array.from({length:density},(_,i)=>{
        const point=seed.slice();
        point[dir]=min[dir]+(max[dir]-min[dir])*(i+.5)/density;
        return point;
      }));
    }
    return seeds;
  }

  // A shared facet supplies both a point on the structure and a direction
  // into the adjacent fluid simplex, independent of face winding.
  function interfaceFacets(cells,isFluid,isSolid){
    const solidFacets=new Map();
    const key=face=>face.slice().sort((a,b)=>a-b).join(',');
    cells.forEach((cell,i)=>{
      if(!isSolid(i))return;
      cell.forEach((_,opposite)=>{
        const face=cell.filter((_,j)=>j!==opposite),name=key(face);
        solidFacets.set(name,(solidFacets.get(name)||0)+1);
      });
    });
    if(!solidFacets.size)return [];
    const facets=[];
    cells.forEach((cell,i)=>{
      if(!isFluid(i))return;
      cell.forEach((inside,j)=>{
        const face=cell.filter((_,k)=>k!==j);
        if(solidFacets.get(key(face))===1)facets.push({face,inside});
      });
    });
    return facets;
  }
  function seedInterface(locator,nodes,facets,count){
    const min=nodes[0].map(()=>Infinity),max=nodes[0].map(()=>-Infinity);
    let total=0;
    const measured=[];
    for(const {face,inside} of facets){
      const points=face.map(id=>nodes[id]),[a,b,c]=points;
      const edge=subtract(b,a),normal=c?cross(edge,subtract(c,a)):[-edge[1],edge[0]];
      const magnitude=Math.hypot(...normal),measure=c?magnitude/2:magnitude;
      if(!(measure>0))continue;
      const sign=dot(normal,subtract(nodes[inside],a))<0?-1:1;
      for(const p of points)p.forEach((x,d)=>{min[d]=Math.min(min[d],x);max[d]=Math.max(max[d],x);});
      measured.push({points,inside,measure,start:total,inward:normal.map(x=>sign*x/magnitude)});
      total+=measure;
    }
    if(!total)return {seeds:[],span:0};
    const span=Math.hypot(...subtract(max,min)),layers=[0,.012,.032,.064,.105];
    let j=0;
    const seeds=Array.from({length:count},(_,i)=>{
      const s=total*(i+.5)/count;
      while(j<measured.length-1&&s>=measured[j].start+measured[j].measure)j++;
      const {points,inside,measure,start,inward}=measured[j];
      const f=Math.min(.99,Math.max(.01,(s-start)/measure));
      let p=between(points[0],points[1],f);
      if(points.length===3)p=between(points[0],between(points[1],points[2],((i+.5)*.61803398875)%1),Math.sqrt(f));
      const base=between(p,nodes[inside],.16),hit=locator.locate(base);
      if(!hit)return null;
      // Extend the band beyond a single near-wall element on refined meshes.
      // Shorten the normal offset if a neighboring wall limits the clearance.
      let distance=span*layers[i%layers.length];
      for(let attempt=0;distance>0&&attempt<6;attempt++,distance*=.5){
        const target=advance(base,inward,distance),end=locator.locate(target,hit.cell);
        if(end&&locator.connected(base,target,hit,end))return target;
      }
      return base;
    }).filter(Boolean);
    return {seeds,span};
  }
  function flowSeeds(locator,nodes,facets,{seedMode,axis,percent,density,nearCount}){
    if(!locator.bounds)return {seeds:[]};
    if(seedMode==='interface'&&facets.length){
      const local=seedInterface(locator,nodes,facets,nearCount);
      if(local.seeds.length)return {...local,near:true};
    }
    const seeds=seedPlane(locator.bounds,axis,percent/100,density);
    return {seeds,position:seeds[0]?.[axis],fallback:seedMode==='interface'};
  }

  function traceStreamlines(locator,fields,seeds,{direction='both',maxSpeed=0,localSpan=0}={}){
    if(!locator.span)return [];
    const domainStep=locator.span/160;
    const step=localSpan?Math.min(domainStep,localSpan/100):domainStep;
    const stagnation=maxSpeed*1e-8;
    function sample(point,hint){
      const hit=locator.locate(point,hint);
      if(!hit)return null;
      const v=point.map((_,i)=>interpolate(fields[velocity[i]],hit));
      const speed=Math.hypot(...v);
      return speed>stagnation&&Number.isFinite(speed)?{point,hit,speed,unit:v.map(x=>x/speed)}:null;
    }
    function march(seed,sign){
      const path=[];
      let current=seed;
      for(let i=0;i<640;i++){
        let next=null;
        // Midpoint Runge–Kutta in arc length. Reduce step at sharp turns
        // and boundaries, using the current cell as the first search hint.
        for(let h=step;h>=step/64;h*=.5){
          const mid=sample(advance(current.point,current.unit,sign*h/2),current.hit.cell);
          if(!mid||dot(current.unit,mid.unit)<.92||!locator.connected(current.point,mid.point,current.hit,mid.hit))continue;
          const trial=sample(advance(current.point,mid.unit,sign*h),mid.hit.cell);
          if(!trial||dot(mid.unit,trial.unit)<.92||!locator.connected(current.point,trial.point,current.hit,trial.hit))continue;
          next=trial;
          break;
        }
        if(!next||Math.hypot(...subtract(next.point,current.point))<step/128)break;
        path.push(next);
        current=next;
        if(i>8&&Math.hypot(...subtract(current.point,seed.point))<step*.7)break;
      }
      return path;
    }
    const lines=[];
    for(const point of seeds){
      const seed=sample(point);
      if(!seed)continue;
      const line=direction==='forward'?[]:march(seed,-1).reverse();
      line.push(seed);
      if(direction!=='backward')line.push(...march(seed,1));
      if(line.length>1)lines.push(line);
    }
    return lines;
  }

  function lineProfile(locator,from,to,values,count=201){
    const length=Math.hypot(...subtract(to,from)),samples=[];
    let previous=null;
    for(let i=0;i<count;i++){
      const t=i/(count-1),point=between(from,to,t),hit=locator.locate(point,previous?.hit?.cell);
      if(previous?.hit&&hit&&!locator.connected(previous.point,point,previous.hit,hit)){
        const middle=(i-.5)/(count-1);
        samples.push({point:between(from,to,middle),distance:middle*length,value:NaN});
      }
      previous={point,distance:t*length,value:interpolate(values,hit),hit};
      samples.push(previous);
    }
    return samples;
  }

  function lineFlowMetrics(locator,from,to,fields,constantDensity){
    const [dx,dy]=subtract(to,from),length=Math.hypot(dx,dy),normal=[dy/length,-dx/length];
    let reach=0,coverage=0,velocityLength=0,massLength=0,pressureLength=0,volume=0,mass=0,pressure=0;
    for(const {first,last,cell} of locator.segmentSpans(from,to)){
      const start=Math.max(reach,first);
      if(last<=start)continue;
      reach=last;
      const side=(last-start)*length;
      const hits=[start,last].map(t=>({cell,weights:locator.weights(cell,between(from,to,t))}));
      const at=values=>hits.map(hit=>interpolate(values,hit));
      const p=at(fields.pressure),rho=fields.density?at(fields.density):[constantDensity,constantDensity];
      const vx=at(fields.vx),vy=at(fields.vy),vn=vx.map((x,i)=>x*normal[0]+vy[i]*normal[1]);
      coverage+=side;
      if(p.every(Number.isFinite)){pressureLength+=side;pressure+=side*(p[0]+p[1])/2;}
      if(!vn.every(Number.isFinite))continue;
      velocityLength+=side;volume+=side*(vn[0]+vn[1])/2;
      if(rho.every(x=>Number.isFinite(x)&&x>0)){
        massLength+=side;
        mass+=side*(2*dot(rho,vn)+rho[0]*vn[1]+rho[1]*vn[0])/6;
      }
    }
    return {coverage,normal,velocityLength,massLength,pressureLength,volume:velocityLength?volume:NaN,
      mass:massLength?mass:NaN,force:normal.map(n=>pressureLength?-n*pressure:NaN)};
  }

  // Dark blue to magenta: remains legible over the bright contour palette.
  const speedColor=(speed,max)=>[.10+.70*Math.min(1,speed/(max||1)),.10,.32+.20*Math.min(1,speed/(max||1))];
  function packFields(frame,keys){
    const fields=frame.fields||{...frame.nodeFields,...frame.flowGeometry};
    const needed=new Set([...keys,...displacement,'flowUx','flowUy','flowUz']);
    return Object.fromEntries([...needed].filter(key=>fields[key]).map(key=>[key,fields[key].slice()]));
  }
  const api={createLocator,deformedNodes,flowNodes,interpolate,seedPlane,interfaceFacets,flowSeeds,traceStreamlines,
    lineProfile,lineFlowMetrics,speedColor,packFields};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  else root.FsiPost=api;
})(globalThis);
