'use strict';
importScripts('./fsi-post.js');
let model,options,previous,paths,ids,placement;

function snapshot({fields,time}){
  const nodes=FsiPost.flowNodes(model.nodes,fields,options.engine);
  const locator=FsiPost.createLocator(nodes,model.cells,model.dimension,i=>model.fluid[i]);
  return {fields,time,locator,nodes};
}
function velocity(frame,point,hint){
  const hit=frame.locator.locate(point,hint);
  const values=['vx','vy','vz'].slice(0,point.length).map(key=>FsiPost.interpolate(frame.fields[key],hit));
  return values.every(Number.isFinite)?{hit,values}:null;
}
function advancePaths(next,maxSpeed){
  const dt=next.time-previous.time,span=previous.locator.span;
  const steps=Math.max(2,Math.min(192,Math.ceil(150*dt*maxSpeed/Math.max(span,1e-15))));
  const move=(p,v,h)=>p.map((x,d)=>x+h*v[d]);
  const sample=(point,fraction,from)=>{
    const a=velocity(previous,point,from?.a.hit.cell),b=velocity(next,point,from?.b.hit.cell);
    if(!a||!b)return null;
    if(from&&(!previous.locator.connected(from.point,point,from.a.hit,a.hit)
      ||!next.locator.connected(from.point,point,from.b.hit,b.hit)))return null;
    return {point,a,b,v:a.values.map((v,d)=>v+(b.values[d]-v)*fraction)};
  };
  for(const path of paths){
    if(!path.active)continue;
    let fraction=0,point=path.points.at(-1).point,lastRecorded=0;
    for(let i=0;i<steps*4&&fraction<1-1e-10;i++){
      const start=sample(point,fraction);
      let trial=null,increment=Math.min(1-fraction,1/steps);
      for(let subdivisions=0;start&&subdivisions<7;subdivisions++,increment*=.5){
        const mid=sample(move(point,start.v,dt*increment/2),fraction+increment/2,start);
        if(!mid)continue;
        trial=sample(move(point,mid.v,dt*increment),fraction+increment,start);
        if(trial)break;
      }
      if(!trial){path.active=false;break;}
      fraction+=increment;point=trial.point;
      if(fraction-lastRecorded>=1/16){
        path.points.push({point,time:previous.time+dt*fraction});
        lastRecorded=fraction;
      }
    }
    if(fraction>lastRecorded)path.points.push({point,time:previous.time+dt*fraction});
    if(fraction<1-1e-10)path.active=false;
  }
}
function particleFrame(data){
  const {positions,time}=data;
  if(!ids){
    const particles=positions.length/3,gap=Math.max(1,particles/options.density);
    ids=Array.from({length:Math.min(particles,options.density)},(_,i)=>Math.floor((i+.5)*gap)).filter(i=>i<particles);
    if(gap===1)ids=ids.map((_,i)=>i);
    paths=ids.map(()=>({points:[]}));
  }
  ids.forEach((id,i)=>{
    const point=Array.from(positions.subarray(id*3,id*3+3));
    paths[i].points.push({point:point.every(Number.isFinite)?point:null,time});
  });
}
self.onmessage=({data})=>{
  try{
    if(data.options){({model,options}=data);return;}
    if(options.engine==='sph')particleFrame(data);
    else{
      const current=snapshot(data);
      if(!previous){
        const facets=options.seedMode==='interface'
          ?FsiPost.interfaceFacets(model.cells,i=>model.fluid[i],i=>model.solid?.[i]):[];
        const {seeds,near,fallback}=FsiPost.flowSeeds(current.locator,current.nodes,facets,options);
        placement={near,fallback};
        paths=seeds.filter(point=>velocity(current,point)).map(point=>({active:true,points:[{point,time:data.time}]}));
      }else advancePaths(current,data.maxSpeed);
      previous=current;
    }
    self.postMessage(data.last?{paths:paths.map(path=>path.points).filter(points=>points.length>1),placement}:{next:true});
  }catch(error){self.postMessage({error:error.message});}
};
