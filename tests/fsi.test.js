'use strict';
// Fluid–structure interaction: input generation, the fluid library, and real
// SU2 / MFEM runs on a small channel over a flexible wall.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const test=require('node:test');
const {buildFsiInputs,splitMesh,fmt}=require('../fsi-deck');
const {prepare}=require('../fsi-model');
const FluidLibrary=require('../fluid-library');
const fsi=require('../fsi-runner');
const runsDirectory=fs.mkdtempSync(path.join(os.tmpdir(),'tensora-fsi-tests-'));
test.after(()=>fs.promises.rm(runsDirectory,{recursive:true,force:true,maxRetries:3}));
const runFsi=payload=>fsi.runFsi(payload,{runsDirectory});
const readFrame=(id,index)=>fsi.readFrame(id,index,{runsDirectory});

const WATER={id:'w',name:'water',model:'incompressible',density:1000,viscosity:1e-3};

// Fluid channel [0,L]x[0,H] above a solid wall strip [x0,x1]x[-t,0]; the wall is
// restrained on its bottom and side edges through nodal fixities.
function channel({L=1,H=0.2,t=0.02,x0=0.3,x1=0.7,nx=30,ny=8,ns=3,E=2e6}={}){
  const nodes=[],cells=[],cellRoles=[],cellMaterials=[],id=new Map();
  const add=(x,y)=>{const k=x.toFixed(9)+','+y.toFixed(9);if(!id.has(k)){id.set(k,nodes.length);nodes.push([x,y]);}return id.get(k);};
  const quad=(xa,xb,ya,yb,role)=>{const a=add(xa,ya),b=add(xb,ya),c=add(xb,yb),d=add(xa,yb);cells.push([a,b,c],[a,c,d]);cellRoles.push(role,role);cellMaterials.push(role==='solid'?'rubber':null,role==='solid'?'rubber':null);};
  const dx=L/nx,dy=H/ny;
  for(let i=0;i<nx;i++)for(let j=0;j<ny;j++)quad(i*dx,(i+1)*dx,j*dy,(j+1)*dy,'fluid');
  const i0=Math.round(x0/dx),i1=Math.round(x1/dx);
  for(let i=i0;i<i1;i++)for(let j=0;j<ns;j++)quad(i*dx,(i+1)*dx,-t+j*t/ns,-t+(j+1)*t/ns,'solid');
  const near=(a,b)=>Math.abs(a-b)<1e-9;
  const edges=pred=>{const out=[];for(const c of cells)for(const [a,b] of [[c[0],c[1]],[c[1],c[2]],[c[2],c[0]]])if(pred(nodes[a])&&pred(nodes[b]))out.push([a,b]);return out;};
  const restrained=p=>p[1]<=1e-9&&(near(p[1],-t)||near(p[0],x0)||near(p[0],x1));
  const fixed=nodes.flatMap(p=>restrained(p)?[1,1]:[0,0]);
  return {dimension:2,nodes,cells,cellRoles,cellMaterials,fixed,materials:{rubber:{name:'rubber',E,nu:0.45,density:1100}},
    boundaries:[{name:'C1',faces:edges(p=>near(p[0],0)&&p[1]>=0)},{name:'C2',faces:edges(p=>near(p[0],L)&&p[1]>=0)}]};
}
const BOUNDARIES={C1:{kind:'inlet',velocity:0.5},C2:{kind:'outlet',pressure:0}};

test('mesh split finds the interface, outward faces and restraint markers',()=>{
  const {model,settings}=prepare({model:channel(),settings:{boundaries:BOUNDARIES}});
  const split=splitMesh(model);
  assert.equal(split.interfaceFluid.length,12);
  assert.equal(split.interfaceSolid.length,12);
  assert.ok(split.fluidMarkers.has('C1')&&split.fluidMarkers.has('C2')&&split.fluidMarkers.has('wall_default'));
  assert.equal(settings.boundaries.fix_all.kind,'clamped');
  // Interface faces are oriented outward from each zone: opposite directions.
  const [a,b]=split.interfaceFluid[0],[c,d]=split.interfaceSolid.find(f=>new Set(f).has(a)&&new Set(f).has(b));
  assert.deepEqual([a,b],[d,c]);
});

test('SU2 inputs use multizone FSI options and reject incomplete models',()=>{
  const {model,settings}=prepare({model:channel(),settings:{boundaries:BOUNDARIES,turbulence:'sst'}});
  const {files,meta}=buildFsiInputs(model,settings,WATER);
  assert.match(files['config.cfg'],/SOLVER= MULTIPHYSICS/);
  assert.match(files['config_flow.cfg'],/SOLVER= INC_RANS/);
  assert.match(files['config_flow.cfg'],/KIND_TURB_MODEL= SST/);
  assert.match(files['config_flow.cfg'],/MARKER_INLET= \( C1, 288.15, 0.5, 1, 0, 0 \)/);
  assert.match(files['config_solid.cfg'],/MARKER_CLAMPED= \( fix_all \)/);
  assert.match(files['mesh_solid.su2'],/MARKER_TAG= fsi_solid/);
  assert.equal(meta.dynamicPressure,0.5*1000*0.25);
  const noOutlet=prepare({model:channel(),settings:{boundaries:{C1:{kind:'inlet',velocity:1}}}});
  assert.throws(()=>buildFsiInputs(noOutlet.model,noOutlet.settings,WATER),/压力出口/);
  const free=channel();free.fixed=free.fixed.map(()=>0);
  const unrestrained=prepare({model:free,settings:{boundaries:BOUNDARIES}});
  assert.throws(()=>buildFsiInputs(unrestrained.model,unrestrained.settings,WATER),/固定约束/);
  const air={name:'air',model:'idealgas',density:1.2,viscosity:1.8e-5,gamma:1.4,gasConstant:287,temperature:293};
  const fast=prepare({model:channel(),settings:{boundaries:{C1:{kind:'inlet',velocity:60},C2:{kind:'outlet',pressure:0}}}});
  const gas=buildFsiInputs(fast.model,fast.settings,air);
  assert.match(gas.files['config_flow.cfg'],/SOLVER= NAVIER_STOKES/);
  assert.match(gas.files['config_flow.cfg'],/FLUID_MODEL= IDEAL_GAS/);
  const stable=buildFsiInputs(fast.model,{...fast.settings,engine:'oneway',flowCfl:12,flowFirstOrder:true},air);
  assert.match(stable.files['config_flow.cfg'],/^CFL_NUMBER= 12$/m);
  assert.match(stable.files['config_flow.cfg'],/^CFL_ADAPT= NO$/m);
  assert.match(stable.files['config_flow.cfg'],/^MUSCL_FLOW= NO$/m);
  assert.throws(()=>buildFsiInputs(fast.model,{...fast.settings,flowCfl:0},air),/CFL/);
  // Free-stream pressure for the one-way loads matches FREESTREAM_PRESSURE.
  assert.equal(stable.meta.freestreamPressure,101325);
  const absolute=buildFsiInputs(fast.model,{...fast.settings,engine:'oneway',referencePressure:0},air);
  assert.match(absolute.files['config_flow.cfg'],new RegExp(`^FREESTREAM_PRESSURE= ${fmt(1.2*287*293)}$`,'m'));
  assert.equal(absolute.meta.freestreamPressure,1.2*287*293);
});

test('solver numbers keep every exponent digit',()=>{
  for(const v of [1.23456789012345e-20,-2.77555756156289e-20,1.11022302462516e-10,6.12323399573677e-17,1e-20,1.5e-30,7.2e30,
    1e14,123456789012345,100,0.1+0.2,101325,-0.5,0])
    assert.equal(Number(fmt(v)),Number(v.toPrecision(15)),`fmt(${v}) = ${fmt(v)}`);
  assert.equal(fmt(1.23456789012345e-20),'1.23456789012345e-20');
  assert.equal(fmt(1e14),'100000000000000');
  assert.equal(fmt(2.5e-7),'2.5e-7');
  // Round-off coordinates near zero must reach the SU2 mesh unchanged.
  const model=channel(),k=model.nodes.findIndex(p=>p[0]===0&&p[1]>0);
  model.nodes[k]=[1.23456789012345e-20,model.nodes[k][1]];
  const {model:prepared,settings}=prepare({model,settings:{boundaries:BOUNDARIES}});
  const {files,split}=buildFsiInputs(prepared,settings,WATER);
  const local=split.fluid.map.get(k),row=files['mesh_fluid.su2'].split('\n').find(line=>line.endsWith(` ${local}`)&&line.includes('e-'));
  assert.equal(Number(row.split(' ')[0]),1.23456789012345e-20);
});

test('fluid library validates records and ships the preset fluids',()=>{
  const library=FluidLibrary.normalize(JSON.parse(fs.readFileSync(path.join(__dirname,'..','fluids','library.json'),'utf8')));
  assert.ok(library.fluids.length>=10);
  for(const fluid of library.fluids){
    assert.ok(fluid.density>0&&fluid.viscosity>=0,fluid.name);
    if(fluid.model==='idealgas')assert.ok(fluid.gamma>1&&fluid.gasConstant>0&&fluid.temperature>0,fluid.name);
  }
  assert.throws(()=>FluidLibrary.entry({id:'x',name:'bad',model:'incompressible',density:-1,viscosity:1}),/density/);
  assert.throws(()=>FluidLibrary.entry({id:'x',name:'gas',model:'idealgas',density:1,viscosity:1e-5}),/gamma/);
  const saved={...library.fluids[0],viscosity:0};
  const selected=FluidLibrary.forModel(library.fluids,saved);
  assert.equal(selected.length,library.fluids.length);
  assert.equal(selected.find(fluid=>fluid.id===saved.id).viscosity,0);
  assert.notEqual(library.fluids[0].viscosity,0);
});

const solvers=fsi.available();
test('SU2 compressible one-way transfers wall pressure to MFEM',{skip:!solvers.su2||!solvers.mfem},async()=>{
  const air={name:'Air',model:'idealgas',density:1.225,viscosity:0,gamma:1.4,gasConstant:287.05,temperature:288.15};
  const settings={engine:'oneway',outerIterations:1,fluidIterations:60,
    boundaries:{C1:{kind:'inlet',velocity:40},C2:{kind:'outlet',pressure:200}}};
  const run=await runFsi({model:channel({nx:20,ny:5}),settings,fluid:air});
  assert.equal(run.meta.exitCode,0);
  assert.ok(run.frames[0].stats.pressure.every(Number.isFinite));
  assert.ok(run.frames[0].stats.vm[1]>0);
  assert.ok(run.mfem.resultant.every(Number.isFinite));
});

test('SU2 two-way and SU2 + MFEM one-way runs agree on a stiff wall',{skip:!solvers.su2||!solvers.mfem},async()=>{
  const settings={boundaries:BOUNDARIES,outerIterations:10,fluidIterations:60};
  const twoWay=await runFsi({model:channel(),settings,fluid:WATER});
  const oneWay=await runFsi({model:channel(),settings:{...settings,engine:'oneway'},fluid:WATER});
  assert.equal(twoWay.engine,'su2');assert.equal(oneWay.engine,'oneway');
  for(const run of [twoWay,oneWay]){
    assert.ok(run.fields.includes('pressure')&&run.fields.includes('vm')&&run.fields.includes('umag'));
    assert.ok(run.fields.includes('q'),'read the SU2 viscous Q_Criterion field');
    assert.ok(run.fields.includes('flowUx')&&run.fields.includes('flowUy'));
    const s=run.frames[0].stats;
    assert.ok(s.vmag[1]>0.5&&s.vmag[1]<1.5,`velocity ${s.vmag[1]}`);
    assert.ok(s.umag[1]>0&&s.vm[1]>0);
  }
  // The deformation is tiny, so two-way and one-way structural responses match.
  const u2=twoWay.frames[0].stats.umag[1],u1=oneWay.frames[0].stats.umag[1];
  assert.ok(Math.abs(u2-u1)/u1<0.02,`two-way ${u2} vs one-way ${u1}`);
  assert.ok(oneWay.mfem.iterations>0&&Math.abs(oneWay.mfem.resultant[1])>0);
  const frame=await readFrame(twoWay.runId,0);
  assert.equal(frame.length,twoWay.fields.length*twoWay.nodeCount*4);
  const oneWayFrame=await readFrame(oneWay.runId,0);
  const data=new Float32Array(oneWayFrame.buffer,oneWayFrame.byteOffset,oneWayFrame.byteLength/4);
  const at=(key,index)=>data[oneWay.fields.indexOf(key)*oneWay.nodeCount+index];
  const model=channel();
  const interfaceWithMotion=model.nodes.findIndex(([x,y],i)=>y===0&&x>.3&&x<.7&&Math.abs(at('uy',i))>1e-9);
  assert.ok(interfaceWithMotion>=0);
  assert.ok(Math.abs(at('flowUy',interfaceWithMotion))<1e-12);
});

// Tank [0,L]x[0,H]x[0,W] split into a water column (volume 1), an elastic plate
// clamped at its base (volume 2) and empty space (volume 3); gravity along -y.
function damBreak({L=0.4,H=0.2,W=0.04,h=0.01,E=0.005}={}){
  const nx=Math.round(L/h),ny=Math.round(H/h),nz=Math.round(W/h);
  const nodes=[],tets=[],tetVolumes=[];
  const id=(i,j,k)=>i*(ny+1)*(nz+1)+j*(nz+1)+k;
  for(let i=0;i<=nx;i++)for(let j=0;j<=ny;j++)for(let k=0;k<=nz;k++)nodes.push([L*i/nx,H*j/ny,W*k/nz]);
  for(let i=0;i<nx;i++)for(let j=0;j<ny;j++)for(let k=0;k<nz;k++){
    const x=(i+0.5)*L/nx,y=(j+0.5)*H/ny;
    const volume=x<0.1&&y<0.12?'1':x>0.25&&x<0.26&&y<0.08?'2':'3';
    const c=[id(i,j,k),id(i+1,j,k),id(i+1,j+1,k),id(i,j+1,k),id(i,j,k+1),id(i+1,j,k+1),id(i+1,j+1,k+1),id(i,j+1,k+1)];
    for(const t of [[0,1,2,6],[0,2,3,6],[0,3,7,6],[0,7,4,6],[0,4,5,6],[0,5,1,6]]){tets.push(t.map(q=>c[q]));tetVolumes.push(volume);}
  }
  const conditions=[];
  nodes.forEach((p,n)=>{if(p[1]<1e-9&&p[0]>0.25-1e-9&&p[0]<0.26+1e-9)conditions.push({type:'fixedNode',node:n,axes:[true,true,true]});});
  return {mesh:{nodes,tets,tetVolumes,volumes:[{id:'1'},{id:'2'},{id:'3'}],surfaces:[]},
    settings:{materials:[{id:'rubber',name:'rubber',elasticModulus:E,poissonRatio:0.45,density:1100}],volumeMaterials:{'2':'rubber'},conditions}};
}
const SPH_ROLES={'1':'fluid','2':'solid','3':'void'};
const WATER_K={...WATER,bulkModulus:2.2e9};

test('SPH decks place one particle per fluid tetrahedron and close the tank with walls',()=>{
  const {buildSphDecks}=require('../fsi-sph');
  const solid=damBreak();
  const fluidTets=solid.mesh.tetVolumes.filter(v=>v==='1').length;
  const decks=buildSphDecks(solid,{endTime:0.1,frames:3,gravity:[0,-9.81,0],volumeRoles:SPH_ROLES},WATER_K);
  assert.equal(decks.particles.length,fluidTets);
  const mass=decks.particles.reduce((sum,p)=>sum+p.mass,0);
  assert.ok(Math.abs(mass-1000*0.1*0.12*0.04)<1e-9,`fluid mass ${mass}`);
  assert.ok(decks.particles.every(p=>p.id>decks.particleBase));
  for(const card of ['/SPHCEL/','/PROP/SPH/2','/MAT/HYD_VISC/','/EOS/POLYNOMIAL/','/SH3N/','/INTER/TYPE7/','/GRAV/','/TETRA4/'])assert.ok(decks.starter.includes(card),card);
  // Soft rubber: the particles limit the step, so no mass scaling is needed.
  assert.equal(decks.meta.minTimeStep,0);
  assert.ok(decks.meta.soundSpeed>=20&&decks.meta.soundSpeed<1500);
  // Stiff steel plate: automatic mass scaling with gravity on the fluid only.
  const steel=damBreak({E:200});
  const scaled=buildSphDecks(steel,{endTime:0.1,frames:3,gravity:[0,-9.81,0],volumeRoles:SPH_ROLES},WATER_K);
  assert.ok(scaled.meta.minTimeStep>0&&scaled.meta.inertiaFactor>1);
  assert.equal(scaled.meta.structureGravity,false);
  assert.throws(()=>buildSphDecks(solid,{volumeRoles:SPH_ROLES},{name:'air',model:'idealgas',density:1.2,viscosity:1.8e-5,gamma:1.4,gasConstant:287,temperature:293}),/液体/);
  const free=damBreak();free.settings.conditions=[];
  assert.throws(()=>buildSphDecks(free,{volumeRoles:SPH_ROLES},WATER_K),/固定约束/);
});

test('OpenCourant SPH dam break runs and the water column collapses',{skip:!solvers.opencourant},async()=>{
  const run=await runFsi({solid:damBreak(),fluid:WATER_K,
    settings:{engine:'sph',endTime:0.06,frames:3,threads:4,gravity:[0,-9.81,0],volumeRoles:SPH_ROLES}});
  assert.equal(run.engine,'sph');
  assert.equal(run.frames.length,3);
  assert.ok(run.completed,run.termination?.message);
  const first=run.frames[0].particleStats,last=run.frames.at(-1).particleStats;
  // The column spreads along +x and its top drops under gravity.
  assert.ok(last.px[1]>first.px[1]+0.005,`front ${first.px[1]} -> ${last.px[1]}`);
  assert.ok(last.py[1]<first.py[1],`top ${first.py[1]} -> ${last.py[1]}`);
  assert.ok(last.pressure[1]>0&&last.vmag[1]>0.1&&last.vmag[1]<5);
  const frame=await readFrame(run.runId,2);
  assert.equal(frame.length,(run.fields.length*run.nodeCount+run.particleFields.length*run.particleCount)*4);
});

test('SU2 transient coupling saves time frames',{skip:!solvers.su2},async()=>{
  const run=await runFsi({model:channel({nx:20,ny:6}),fluid:WATER,
    settings:{boundaries:BOUNDARIES,analysis:'transient',structure:'neohookean',timeStep:0.005,steps:6,frames:4,outerIterations:4,fluidIterations:10,solidIterations:4}});
  assert.ok(run.frames.length>=3);
  assert.ok(run.frames.every((f,i)=>i===0||f.time>run.frames[i-1].time));
  assert.ok(Math.abs(run.frames.at(-1).time-0.03)<1e-12);
});
