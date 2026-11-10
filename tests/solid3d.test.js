'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs');
const {meshSolid,previewSolid,solveSolid,geometryScript,tetData,principalValues,safetyCode,assembleLoads}=require('../solid3d');

test('oblique sections interpolate the interior displacement and retain element stress',async()=>{
  const {cutTetrahedra,sectionValues,unitSectionNormal}=await import('../src/pages/solid3d-sections.js');
  const mesh={nodes:[[0,0,0],[1,0,0],[0,1,0],[0,0,1],[0,0,-1]],tets:[[0,1,2,3],[0,1,2,4]],tetVolumes:['A','B']};
  const result={nodeFields:{ux:mesh.nodes.map(([x,y,z])=>x+2*y+3*z)},
    stress:[{components:[10]},{components:[20]}]};
  const cut=cutTetrahedra(mesh,[.25,0,0],unitSectionNormal([1,1,0]),1e-10,new Set());
  assert.equal(cut.elements.length,4);
  const values=sectionValues(cut,result,'ux');
  values.forEach((value,i)=>{
    const [x,y,z]=cut.positions.subarray(i*3,i*3+3);
    assert.ok(Math.abs(x+y-.25)<1e-7);
    assert.ok(Math.abs(value-x-2*y-3*z)<1e-7);
  });
  assert.deepEqual([...new Set(sectionValues(cut,result,'sxx'))],[10,20]);
  const shared=cutTetrahedra(mesh,[0,0,0],[0,0,1],1e-10,new Set());
  assert.equal(shared.elements.length,1);
  const reversed=cutTetrahedra(mesh,[0,0,0],[0,0,-1],1e-10,new Set());
  assert.deepEqual([...sectionValues(reversed,result,'sxx')],[20,20,20]);
  const visible=cutTetrahedra(mesh,[0,0,0],[0,0,1],1e-10,new Set(['A']));
  assert.deepEqual([...sectionValues(visible,result,'sxx')],[20,20,20]);
});

test('CAD preview cuts only the chosen solid using plane, rotation and translation',async()=>{
  const preview=await previewSolid({shapes:[
    {type:'box',featureId:'front',dx:1,dy:.3,dz:.3},
    {type:'box',featureId:'rear',x:1.1,dx:1,dy:.3,dz:.3},
    {type:'cylinder',plane:'XZ',rz:90,y:.15,z:.15,radius:.1,height:2.2,operation:'cut',cutTarget:'front'}
  ]});
  assert.equal(preview.tets,undefined);
  assert.equal(preview.volumes.length,2);
  const frontFaces=preview.surfaces.filter(face=>face.triangles.every(tri=>tri.every(i=>preview.nodes[i][0]<1.05)));
  assert.equal(frontFaces.length,7);
  assert.equal(preview.surfaces.length-frontFaces.length,6);
  assert.ok(frontFaces.some(face=>face.triangles.every(tri=>tri.every(i=>{
    const [,y,z]=preview.nodes[i];
    return Math.abs(Math.hypot(y-.15,z-.15)-.1)<1e-8;
  }))));
});

test('TET4 gradient and 3-D cantilever force equilibrium',async()=>{
  const g=tetData([[0,0,0],[1,0,0],[0,1,0],[0,0,1]]);
  assert.equal(g.volume,1/6);assert.deepEqual(g.grads,[[-1,-1,-1],[1,0,0],[0,1,0],[0,0,1]]);
  const mesh=await meshSolid({shapes:[{type:'box',x:0,y:0,z:0,dx:1,dy:.2,dz:.2}],meshSize:.14});
  const faces=mesh.surfaces.map(s=>({id:s.id,x:s.triangles.flat().reduce((sum,id,_,a)=>sum+mesh.nodes[id][0]/a.length,0)}));
  const left=faces.reduce((a,b)=>a.x<b.x?a:b),right=faces.reduce((a,b)=>a.x>b.x?a:b);
  const out=solveSolid(mesh,{young:2e11,poisson:.3,conditions:[{surface:left.id,type:'fixed'},{surface:right.id,type:'force',fx:1000,fy:0,fz:0}]});
  assert.ok(out.maxDisplacement>0&&out.maxVonMises>0);
  assert.ok(Math.abs(out.maxDisplacement-1000/(2e11*.2*.2))/(1000/(2e11*.2*.2))<.1,'axial bar displacement should approach F L / E A');
  for(const field of ['ux','uy','uz','umag','sxx','syy','szz','sxy','syz','sxz','vm','exx','eyy','ezz','exy','eyz','exz','equivalentStrain'])assert.equal(out.nodeFields[field].length,mesh.nodes.length);
  assert.equal(out.surfaceSafety.length,mesh.surfaces.length);
  const net=(a,d)=>a.reduce((s,v,i)=>s+(i%3===d?v:0),0);
  assert.ok(Math.abs(net(out.nodalForces,0)-1000)<1e-8);
  assert.ok(Math.abs(net(out.reactions,0)+1000)<1e-4);
  assert.ok(Math.abs(net(out.reactions,1))<1e-4);
  assert.ok(Math.abs(net(out.reactions,2))<1e-4);
  assert.ok(out.residual<1e-5);
});
test('3-D principal stresses and shared material safety criteria',()=>{
  const p=principalValues([80e6,20e6,-10e6,0,0,0]);assert.deepEqual(p,[80e6,20e6,-10e6]);
  assert.equal(safetyCode([80e6,20e6,-10e6,0,0,0],80e6,{strengthCriterion:4,yieldStrength:70},.3),3);
  assert.equal(safetyCode([80e6,20e6,-10e6,0,0,0],80e6,{strengthCriterion:1,tensileStrength:70,compressiveStrength:100},.3),2);
  assert.equal(safetyCode([-10e6,-20e6,-110e6,0,0,0],100e6,{strengthCriterion:1,tensileStrength:70,compressiveStrength:100},.3),1);
  assert.equal(safetyCode([80e6,20e6,-10e6,0,0,0],80e6,{strengthCriterion:3,yieldStrength:100},.3),0);
  assert.equal(safetyCode([80e6,20e6,-10e6,0,0,0],80e6,{strengthCriterion:1,tensileStrength:70},.3),4);
});
test('bundled Gmsh imports STEP in metres',async()=>{
  const step=fs.readFileSync(require('node:path').join(__dirname,'fixtures/gmsh-as1-tu-203.stp'));
  const mesh=await meshSolid({stepBase64:step.toString('base64'),meshSize:.01});
  assert.ok(mesh.tets.length>100&&mesh.surfaces.length>10);
  assert.ok(Math.max(...mesh.nodes.flat())<1,'STEP millimetres should be converted to metres');
});
test('primitive CAD inputs reject nonphysical dimensions',()=>{
  assert.throws(()=>geometryScript([{type:'box',x:0,y:0,z:0,dx:-1,dy:1,dz:1}]),/大于零/);
});

test('touching CAD bodies retain conformal volumes and separate elastic materials',async()=>{
  const mesh=await meshSolid({shapes:[{type:'box',x:0,y:0,z:0,dx:.5,dy:.3,dz:.3},{type:'box',x:.5,y:0,z:0,dx:.5,dy:.3,dz:.3}],meshSize:.22});
  assert.equal(mesh.volumes.length,2);
  const byVolume=mesh.volumes.map(v=>new Set(mesh.tets.filter((_,i)=>mesh.tetVolumes[i]===v.id).flat()));
  assert.ok([...byVolume[0]].some(id=>byVolume[1].has(id)),'interface nodes must be shared');
  const end=s=>s.triangles.flat().reduce((sum,id,_,a)=>sum+mesh.nodes[id][0]/a.length,0);
  const left=mesh.surfaces.reduce((a,b)=>end(a)<end(b)?a:b),right=mesh.surfaces.reduce((a,b)=>end(a)>end(b)?a:b);
  const hard={id:'hard',elasticModulus:200,poissonRatio:.3,density:7850,yieldStrength:235,strengthCriterion:4},soft={...hard,id:'soft',elasticModulus:20};
  const conditions=[{type:'fixed',surface:left.id},{type:'force',surface:right.id,fx:1000,fy:0,fz:0}];
  const base={materials:[hard,soft],conditions};
  const uniform=solveSolid(mesh,{...base,volumeMaterials:Object.fromEntries(mesh.volumes.map(v=>[v.id,'hard']))});
  const mixed=solveSolid(mesh,{...base,volumeMaterials:{[mesh.volumes[0].id]:'hard',[mesh.volumes[1].id]:'soft'}});
  assert.ok(mixed.maxDisplacement>uniform.maxDisplacement*1.5);
  assert.deepEqual(new Set(mixed.stress.map(s=>s.volumeId)),new Set(mesh.volumes.map(v=>v.id)));
});

test('face, volume, gravity and node loads conserve their totals',async()=>{
  const mesh=await meshSolid({shapes:[{type:'box',x:0,y:0,z:0,dx:1,dy:1,dz:1}],meshSize:.5});
  const surface=mesh.surfaces[0],area=surface.triangles.reduce((sum,t)=>{const [a,b,c]=t.map(id=>mesh.nodes[id]),u=b.map((v,i)=>v-a[i]),v=c.map((w,i)=>w-a[i]);return sum+Math.hypot(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])/2;},0);
  const volume=mesh.tets.reduce((sum,t)=>sum+tetData(t.map(id=>mesh.nodes[id])).volume,0);
  const mat=()=>({material:{density:2000}}),fixed={type:'fixed',surface:surface.id};
  const total=(bc,d)=>{const {force}=assembleLoads(mesh,[fixed,bc],mat);return force.reduce((sum,v,i)=>sum+(i%3===d?v:0),0);};
  assert.ok(Math.abs(total({type:'force',surface:surface.id,fx:17,fy:0,fz:0},0)-17)<1e-8);
  assert.ok(Math.abs(total({type:'traction',surface:surface.id,fx:17,fy:0,fz:0},0)-17*area)<1e-8);
  assert.ok(Math.abs(total({type:'bodyForce',fx:0,fy:11,fz:0},1)-11*volume)<1e-8);
  assert.ok(Math.abs(total({type:'gravity',fx:0,fy:0,fz:-9.8},2)+9.8*2000*volume)<1e-8);
  assert.ok(Math.abs(total({type:'pointForce',node:0,fx:0,fy:0,fz:23},2)-23)<1e-8);
  const pressure=assembleLoads(mesh,[fixed,{type:'pressure',surface:surface.id,pressure:10}],mat).force;
  assert.ok(Math.abs(Math.hypot(...[0,1,2].map(d=>pressure.reduce((sum,v,i)=>sum+(i%3===d?v:0),0)))-10*area)<1e-8);
  const constrained=assembleLoads(mesh,[{type:'fixed',surface:surface.id,axes:[true,false,false]},{type:'pointForce',node:0,fx:1,fy:0,fz:0}],mat).fixed;
  assert.ok(constrained.some((v,i)=>i%3===0&&v===1)&&constrained.every((v,i)=>i%3===0||v===0));
});

test('extruded 2-D sketch cuts a hole from a CAD solid',async()=>{
  const mesh=await meshSolid({shapes:[{type:'box',x:0,y:0,z:0,dx:1,dy:1,dz:1},{type:'extrusion',polygon:[[.3,.3],[.7,.3],[.7,.7],[.3,.7]],z:0,height:1,operation:'cut'}],meshSize:.3});
  const volume=mesh.tets.reduce((sum,t)=>sum+tetData(t.map(id=>mesh.nodes[id])).volume,0);
  assert.ok(Math.abs(volume-.84)<.03,`cut volume ${volume}`);
});
