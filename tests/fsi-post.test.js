'use strict';
const assert=require('node:assert/strict');
const test=require('node:test');
const {createLocator,flowNodes,lineProfile,lineFlowMetrics,seedPlane,interfaceFacets,flowSeeds,traceStreamlines}=require('../src/core/fsi-post');

test('structure seeds are placed inside interface-adjacent fluid triangles and tetrahedra',()=>{
  for(const {nodes,cells} of [
    {nodes:[[0,0],[1,0],[0,1],[0,-1],[0,40],[40,40],[40,0]],cells:[[0,1,2],[0,1,3],[4,5,6]]},
    {nodes:[[0,0,0],[1,0,0],[0,1,0],[0,0,1],[0,0,-1]],cells:[[0,1,2,3],[0,1,2,4]]}
  ]){
    const isFluid=i=>i!==1,isSolid=i=>i===1,dimension=nodes[0].length;
    const locator=createLocator(nodes,cells,dimension,isFluid);
    const facets=interfaceFacets(cells,isFluid,isSolid);
    assert.equal(facets.length,1);
    const options={seedMode:'interface',nearCount:32,axis:0,density:4,percent:25};
    const local=flowSeeds(locator,nodes,facets,options);
    assert.equal(local.near,true);
    assert.equal(local.seeds.length,32);
    assert.equal(local.seeds.every(p=>locator.locate(p)?.cell.index===0&&p.at(-1)>0&&p.at(-1)<.7),true);
    const fallback=flowSeeds(locator,nodes,[],options);
    assert.equal(fallback.fallback,true);
    assert.equal(fallback.seeds.length,4**(dimension-1));
    assert.deepEqual(interfaceFacets(cells,()=>false,isSolid),[]);
  }
});

test('near-structure offsets shorten across a thin gap instead of seeding disconnected fluid',()=>{
  const nodes=[[0,0],[1,0],[0,.03],[1,.03],[0,-1],[0,.031],[1,.031],[0,.25],[1,.25]];
  const cells=[[0,1,2],[1,3,2],[0,1,4],[5,6,7],[6,8,7]],isFluid=i=>i!==2;
  const locator=createLocator(nodes,cells,2,isFluid);
  const facets=interfaceFacets(cells,isFluid,i=>i===2);
  const {seeds}=flowSeeds(locator,nodes,facets,{seedMode:'interface',nearCount:25});
  assert.equal(seeds.length,25);
  assert.ok(seeds.every(p=>p[1]>0&&p[1]<=.03&&locator.locate(p)?.cell.index<2));
});

test('TRI3 streamlines follow the interpolated flow and stop at the channel walls',()=>{
  const nodes=[[0,0],[2,0],[2,1],[0,1]],cells=[[0,1,2],[0,2,3]];
  const locator=createLocator(nodes,cells,2);
  const fields={vx:[1,1,2,2],vy:[0,0,0,0]};
  const seeds=seedPlane(locator.bounds,0,.5,3);
  const lines=traceStreamlines(locator,fields,seeds,{maxSpeed:2});
  assert.equal(lines.length,3);
  lines.forEach((line,i)=>{
    assert.ok(line[0].point[0]<.001&&line.at(-1).point[0]>1.999);
    for(const {point,speed} of line){
      assert.ok(Math.abs(point[1]-seeds[i][1])<1e-12);
      assert.ok(Math.abs(speed-(1+point[1]))<1e-12);
    }
  });
  const [backward]=traceStreamlines(locator,fields,[seeds[0]],{direction:'backward'});
  assert.deepEqual(backward.at(-1).point,seeds[0]);
  assert.ok(backward.every(({point})=>point[0]<=1));
});

test('streamlines and line profiles cannot bridge a thin excluded zone',()=>{
  const nodes=[0,1,1.0001,2].flatMap(x=>[[x,0],[x,1]]);
  const cells=Array.from({length:3},(_,i)=>[[i*2,i*2+2,i*2+3],[i*2,i*2+3,i*2+1]]).flat();
  const locator=createLocator(nodes,cells,2,i=>i<2||i>=4);
  const values=nodes.map(([x,y])=>3*x-2*y);
  const [line]=traceStreamlines(locator,{vx:nodes.map(()=>1),vy:nodes.map(()=>0)},[[.97,.5]]);
  assert.ok(line.every(({point})=>point[0]<=1+1e-9));
  const profile=lineProfile(locator,[.1,.5],[1.9,.5],values,10);
  assert.equal(profile.filter(s=>!Number.isFinite(s.value)).length,1);
  for(const sample of profile.filter(s=>s.hit)){
    assert.ok(Math.abs(sample.value-(3*sample.point[0]-1))<1e-12);
  }
});

test('TET4 streamlines follow solver mesh motion independently of structure displacement',()=>{
  const reference=[[0,0,0],[1,0,0],[0,1,0],[0,0,1]];
  const fields={ux:[2,2,2,2],flowUx:[.1,.1,.1,.1],flowUy:[0,0,0,0],flowUz:[0,0,0,0],
    vx:[1,1,1,1],vy:[0,0,0,0],vz:[0,0,0,0]};
  assert.equal(flowNodes(reference,{ux:fields.ux},'oneway'),reference);
  const locator=createLocator(flowNodes(reference,fields,'su2'),[[0,1,2,3]],3);
  const [line]=traceStreamlines(locator,fields,[[.4,.2,.2]]);
  assert.ok(line[0].point[0]>=.1-1e-9&&line[0].point[0]<.101);
  assert.ok(line.at(-1).point[0]>.699&&line.at(-1).point[0]<=.7+1e-9);
  assert.ok(line.every(({point})=>point[1]===.2&&point[2]===.2));
});

test('2D cuts integrate flow and pressure once across contiguous or coincident TRI3 cells',()=>{
  const locator=createLocator([[0,0],[1,0],[1,1],[0,1]],[[0,1,2],[0,2,3]],2);
  const fields={vx:[1,1,3,3],vy:[0,0,0,0],pressure:[2,2,4,4]};
  const vertical=lineFlowMetrics(locator,[.5,-1],[.5,2],fields,1000);
  const close=(value,expected)=>assert.ok(Math.abs(value-expected)<1e-11,`${value} vs ${expected}`);
  close(vertical.coverage,1);
  close(vertical.volume,2);
  close(vertical.mass,2000);
  close(vertical.force[0],-3);
  const diagonal=lineFlowMetrics(locator,[0,0],[1,1],fields,1000);
  close(diagonal.coverage,Math.SQRT2);
  close(diagonal.volume,2);
});

test('section statistics integrate linear fields and signed flow across the physical cut',async()=>{
  const {cutTetrahedra,sectionValues,sectionFlowMetrics}=await import('../src/pages/solid3d-sections.js');
  const mesh={nodes:[[0,0,0],[1,0,0],[0,1,0],[0,0,1]],tets:[[0,1,2,3]],tetVolumes:['1']};
  const nodeFields={pressure:[0,0,3,6],vx:[2,2,2,2],vy:[0,0,0,0],vz:[0,0,0,0]};
  const point=[.5,0,0],normal=[1,0,0],cut=cutTetrahedra(mesh,point,normal,1e-12,new Set());
  const result={nodeFields},values=sectionValues(cut,result,'pressure');
  const stats=sectionFlowMetrics(mesh,cut,normal,result,values,1000);
  assert.equal(stats.area,.125);
  assert.equal(stats.mean,1.5);
  assert.equal(stats.flowRate,.25);
  assert.equal(stats.massRate,250);
  assert.equal(stats.pressureForce[0],-.1875);
  assert.equal(sectionFlowMetrics(mesh,cut,[-1,0,0],result,values).flowRate,-.25);
  nodeFields.vx[0]=NaN;
  const missing=sectionFlowMetrics(mesh,cut,normal,result,values);
  assert.equal(missing.velocityArea,0);
  assert.ok(Number.isNaN(missing.flowRate));
});

test('vortex criteria and isosurfaces follow the exact linear tetrahedral field',()=>{
  const {vortexField,isosurface,particleSurface}=require('../src/core/fsi-volume');
  const nodes=[[0,0,0],[1,0,0],[0,1,0],[0,0,1]],cells=[[0,1,2,3]];
  const velocity={vx:[0,0,-2,0],vy:[0,2,0,0],vz:[0,0,0,0]},all=()=>true;
  for(const value of vortexField(nodes,cells,all,velocity,'q'))assert.equal(value,8); // SU2 definition.
  for(const value of vortexField(nodes,cells,all,velocity,'lambda2'))assert.ok(Math.abs(value+4)<1e-12);
  const plane=isosurface(cells,nodes,[0,1,0,0],.5,all,[0,0,1,0]);
  assert.equal(plane.positions.length,9);
  assert.deepEqual(new Set([plane.positions[0],plane.positions[3],plane.positions[6]]),new Set([.5]));
  assert.deepEqual(new Set(plane.colors),new Set([0,.5]));
  const block=Float32Array.from([0,1,2,3].flatMap(x=>[0,1,2,3].flatMap(y=>[0,1,2,3].flatMap(z=>[x,y,z]))));
  const surface=particleSurface(block,1,.45);
  assert.ok(surface.positions.length>0&&surface.positions.every(Number.isFinite));
});

test('frequency spectrum recovers sinusoid amplitude and rejects irregular times',()=>{
  const {spectrum}=require('../src/core/fsi-spectrum');
  const times=Array.from({length:40},(_,i)=>i/40);
  const values=times.map(t=>5+3*Math.sin(2*Math.PI*7*t));
  const result=spectrum(times,values);
  assert.ok(Math.abs(result.frequency[result.peak]-7)<1e-12);
  assert.ok(Math.abs(result.amplitude[result.peak]-3)<1e-10);
  times[5]+=.002;
  assert.equal(spectrum(times,values),null);
});

test('ParaView series keeps time and zone separation with physical coordinates',async()=>{
  const post=require('../src/core/fsi-post'),{series}=require('../src/core/fsi-export');
  const model={nodes:[[0,0],[1,0],[0,1],[1,1]],cells:[[0,1,2],[1,2,3]]};
  const entries=[];
  for await(const entry of series({...model,role:i=>i?'solid':'fluid',
    run:{engine:'oneway',dimension:2,frames:[{time:.2}]},
    loadFrame:async()=>({fields:{pressure:[1,2,3,NaN],ux:[0,.2,0,.2],uy:[0,0,0,0]}})
  },post))entries.push(entry);
  assert.deepEqual(entries.map(e=>e.name),['frames/fluid-0000.vtu','frames/structure-0000.vtu','fsi.pvd']);
  assert.match(entries[2].text,/timestep="0.2".*part="0".*fluid-0000\.vtu/);
  assert.match(entries[2].text,/timestep="0.2".*part="1".*structure-0000\.vtu/);
  const coords=entry=>{
    const base64=/Name="Points"[^>]*>([^<]+)/.exec(entry.text)[1];
    const buffer=Buffer.from(base64,'base64');
    assert.equal(buffer.readUInt32LE(0),3*3*8);
    return Array.from({length:9},(_,i)=>buffer.readDoubleLE(4+i*8));
  };
  assert.deepEqual(coords(entries[0]),[0,0,0,1,0,0,0,1,0]);
  assert.deepEqual(coords(entries[1]),[1.2,0,0,0,1,0,1.2,1,0]);
});
