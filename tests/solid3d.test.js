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

test('CAD restraints mesh the support line and ligament of a half-beam before binding nodes',async()=>{
  const shapes=[{type:'box',dx:.09,dy:.04,dz:.02}];
  const cad=await previewSolid({shapes});
  const equal=(a,b)=>Math.abs(a-b)<1e-10;
  const at=(node,axis,value)=>equal(cad.nodes[node][axis],value);
  const surface=(axis,value)=>Number(cad.surfaces.find(face=>
    face.triangles.every(triangle=>triangle.every(node=>at(node,axis,value)))).id);
  const bottom=surface(1,0),center=surface(0,0);
  const bottomEdge=Number(cad.edges.find(edge=>
    edge.segments.every(segment=>segment.every(node=>at(node,1,0)&&at(node,2,0)))).id);
  const guides=[
    {id:'support',kind:'line',entity:bottom,start:[.08,0,0],end:[.08,0,.02],axes:[false,true,false]},
    {id:'ligament',kind:'patch',entity:center,min:[0,.02,0],max:[0,.04,.02],axis:0,axes:[true,false,false]},
    {id:'full-bottom',kind:'face',entity:bottom,axes:[false,true,false]},
    {id:'bottom-edge',kind:'edge',entity:bottomEdge,axes:[false,true,false]},
  ];
  for(const meshSize of [.008,.004]){
    const mesh=await meshSolid({shapes,meshSize,restraintGuides:guides});
    const nodesFor=id=>mesh.restraintGroups.find(group=>group.id===id).nodes;
    const support=nodesFor('support'),ligament=nodesFor('ligament');
    assert.ok(support.length>=3 && ligament.length>support.length);
    assert.ok(support.every(id=>equal(mesh.nodes[id][0],.08)&&equal(mesh.nodes[id][1],0)));
    assert.ok(support.some(id=>equal(mesh.nodes[id][2],0)));
    assert.ok(support.some(id=>equal(mesh.nodes[id][2],.02)));
    assert.ok(ligament.every(id=>equal(mesh.nodes[id][0],0)&&mesh.nodes[id][1]>=.02-1e-10));
    assert.ok(ligament.some(id=>equal(mesh.nodes[id][1],.02)));
    assert.ok(nodesFor('bottom-edge').some(id=>equal(mesh.nodes[id][0],.08)));
    assert.ok(nodesFor('full-bottom').some(id=>mesh.nodes[id][0]<.08-1e-10));
    assert.ok(nodesFor('full-bottom').some(id=>mesh.nodes[id][0]>.08+1e-10));
    const anchor=support.find(id=>equal(mesh.nodes[id][2],0));
    const top=mesh.nodes.findIndex(([x,y,z])=>equal(x,0)&&equal(y,.04)&&equal(z,0));
    const conditions=[
      ...guides.slice(0,2).map(guide=>({type:'fixedGroup',group:guide.id,axes:guide.axes})),
      {type:'fixedNode',node:anchor,axes:[false,false,true]},
      {type:'pointForce',node:top,fx:0,fy:-500,fz:0},
    ];
    const {fixed}=assembleLoads(mesh,conditions,()=>null);
    const crackMouth=mesh.nodes.findIndex(([x,y,z])=>equal(x,0)&&equal(y,0)&&equal(z,0));
    assert.equal(fixed[3*crackMouth],0);
    assert.ok(support.every(id=>fixed[3*id+1]===1));
    assert.ok(ligament.every(id=>fixed[3*id]===1));
    const result=solveSolid(mesh,{young:210e9,poisson:.3,conditions});
    const reactionY=result.reactions.reduce((sum,value,dof)=>sum+(dof%3===1?value:0),0);
    assert.ok(Math.abs(reactionY-500)<1e-4);
    assert.ok(result.displacements[crackMouth][0]>0);
  }
  const missed={...guides[0],start:[.08,.01,0],end:[.08,.01,.02]};
  await assert.rejects(meshSolid({shapes,meshSize:.008,restraintGuides:[missed]}),/几何边界条件无法绑定/);
});

test('CAD points and distributed loads bind before meshing and conserve force and moment',async()=>{
  const shapes=[{type:'box',dx:2,dy:1,dz:1}];
  const cad=await previewSolid({shapes});
  const face=(axis,value)=>Number(cad.surfaces.find(surface=>surface.triangles.every(triangle=>
    triangle.every(id=>Math.abs(cad.nodes[id][axis]-value)<1e-10))).id);
  const top=face(2,1);
  const clamp={id:'clamp',kind:'face',entity:face(0,0),axes:[true,true,true]};
  const point={id:'point',kind:'point',entity:top,at:[.73,.4,1],axes:[true,false,false]};
  const force={id:'force',kind:'point',entity:top,at:point.at,load:{type:'pointForce',start:[0,0,-5]}};
  const line={id:'line',kind:'line',entity:top,start:[.2,.4,1],end:[1.8,.4,1],
    load:{type:'linearLineTraction',start:[0,0,0],end:[0,0,-12]}};
  const patch={id:'patch',kind:'patch',entity:top,axis:2,min:[.3,.2,1],max:[1.7,.8,1],
    load:{type:'linearTraction',axis:0,from:.3,to:1.7,start:[0,0,-4],end:[0,0,-10]}};
  const volume={id:'volume',kind:'volume',entity:Number(cad.volumes[0].id),
    load:{type:'bodyForce',start:[0,0,-2]}};
  const uniform={...line,load:{type:'lineTraction',start:[0,0,-5]}};
  const pressure={...patch,load:{...patch.load,type:'linearPressure',start:4,end:10}};
  const affine={...patch,load:{type:'linearTraction',origin:[1,.5,1],start:[0,0,-7],
    gradient:[[0,0,2],[0,0,6],[0,0,0]]}};
  const affinePressure={...patch,load:{type:'linearPressure',origin:[1,.5,1],start:7,gradient:[-2,-6,0]}};
  const topEdge=cad.edges.find(edge=>edge.segments.every(segment=>
    segment.every(id=>cad.nodes[id][1]===0&&cad.nodes[id][2]===1)));
  const edge={id:'edge',kind:'edge',entity:Number(topEdge.id),
    load:{type:'linearLineTraction',start:[0,0,0],end:[0,0,-12]}};
  const near=(a,b)=>assert.ok(Math.abs(a-b)<1e-8, a+' != '+b);
  const fixed=[clamp,point].map(guide=>({type:'fixedGroup',group:guide.id,axes:guide.axes}));
  for(const meshSize of [.3,.17]){
    const mesh=await meshSolid({shapes,meshSize,restraintGuides:[clamp,point,force,line,patch,volume,edge]});
    const node=mesh.restraintGroups.find(g=>g.id===point.id).nodes[0];
    assert.deepEqual(mesh.nodes[node],point.at);
    assert.deepEqual(mesh.restraintGroups.find(g=>g.id===force.id).nodes,[node]);
    const cases=[
      [force,-5,.73,.4],
      [line,-9.6,.2+2*1.6/3,.4],
      [uniform,-8,1,.4],
      [patch,-5.88,1.1,.5],
      [pressure,-5.88,1.1,.5],
      [affine,-5.88,1-2*1.4**2/84,.5-6*.6**2/84],
      [affinePressure,-5.88,1-2*1.4**2/84,.5-6*.6**2/84],
      [edge,-12,4/3,0],
      [{...edge,load:{...edge.load,reverse:true}},-12,2/3,0],
      [volume,-4,1,.5],
    ];
    for(const [guide,total,x,y] of cases){
      const out=assembleLoads(mesh,[...fixed,{type:'loadGroup',guide}],()=>null);
      let sum=0,momentX=0,momentY=0;
      for(let i=0;i<mesh.nodes.length;i++){
        const fz=out.force[3*i+2];
        sum+=fz;
        momentX+=mesh.nodes[i][1]*fz;
        momentY-=mesh.nodes[i][0]*fz;
      }
      near(sum,total);
      near(momentX,y*total);
      near(momentY,-x*total);
      assert.deepEqual(Array.from(out.fixed.slice(3*node,3*node+3)),[1,0,0]);
    }
    const result=solveSolid(mesh,{young:210e9,poisson:.3,
      conditions:[...fixed,...[force,line,pressure].map(guide=>({type:'loadGroup',guide}))]});
    const reactionZ=result.reactions.reduce((sum,value,i)=>sum+(i%3===2?value:0),0);
    assert.ok(Math.abs(reactionZ-20.48)<1e-5);
  }
  await assert.rejects(meshSolid({shapes,meshSize:.3,restraintGuides:[{...point,at:[.73,.4,.9]}]}),
    /几何边界条件无法绑定/);
});

test('a picked point on the faceted preview is projected to the curved CAD face before meshing',async()=>{
  const shapes=[{type:'cylinder',radius:1,height:1}];
  const cad=await previewSolid({shapes});
  const side=cad.surfaces.find(face=>{
    const ids=new Set(face.triangles.flat());
    return [...ids].some(id=>cad.nodes[id][2]===0)&&[...ids].some(id=>cad.nodes[id][2]===1);
  });
  const point={id:'picked',kind:'point',entity:Number(side.id),at:[.94,.3,.45],
    projection:{normal:[1,0,0],radius:.1},axes:[true,false,false]};
  const mesh=await meshSolid({shapes,meshSize:.3,restraintGuides:[point]});
  const [node]=mesh.restraintGroups[0].nodes;
  const [x,y,z]=mesh.nodes[node];
  assert.ok(Math.abs(x-Math.sqrt(1-.3**2))<1e-9);
  assert.ok(Math.abs(y-.3)<1e-10&&Math.abs(z-.45)<1e-10);
  assert.equal(new Set(mesh.tets.flat()).size,mesh.nodes.length);
});

test('extruded 2-D sketch cuts a hole from a CAD solid',async()=>{
  const mesh=await meshSolid({shapes:[{type:'box',x:0,y:0,z:0,dx:1,dy:1,dz:1},{type:'extrusion',polygon:[[.3,.3],[.7,.3],[.7,.7],[.3,.7]],z:0,height:1,operation:'cut'}],meshSize:.3});
  const volume=mesh.tets.reduce((sum,t)=>sum+tetData(t.map(id=>mesh.nodes[id])).volume,0);
  assert.ok(Math.abs(volume-.84)<.03,`cut volume ${volume}`);
});
