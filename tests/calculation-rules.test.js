'use strict';
// Pre-run check rules: material identification, unit mistakes, constitutive
// advice and module checks. Every finding must carry Chinese and English text.
const assert=require('node:assert/strict');
const test=require('node:test');
const R=require('../calculation-rules');

const steel={id:'s',name:'Q235钢',elasticModulus:200,poissonRatio:0.26,density:7850,yieldStrength:235,tensileStrength:370,strengthCriterion:4};
const concrete={id:'c',name:'C30混凝土',elasticModulus:30,poissonRatio:0.2,density:2400,tensileStrength:2.01,compressiveStrength:20.1,strengthCriterion:1};
const rubber={id:'r',name:'天然橡胶',elasticModulus:0.005,poissonRatio:0.495,density:1100};
const codes=list=>list.map(f=>f.code);
const levels=(list,code)=>list.filter(f=>f.code===code).map(f=>f.level);

test('materials are identified from their names or properties',()=>{
  assert.equal(R.classify(steel).kind,'metal');
  assert.equal(R.classify(concrete).kind,'concrete');
  assert.equal(R.classify({name:'花岗岩'}).kind,'rock');
  assert.equal(R.classify(rubber).kind,'rubber');
  assert.equal(R.classify({name:'X',elasticModulus:70,yieldStrength:200}).kind,'metal');
  assert.equal(R.classify({name:'X',elasticModulus:0.01}).kind,'rubber');
  assert.equal(R.classify({name:'X'}).kind,'unknown');
});

test('unit mistakes and impossible values are caught',()=>{
  const mpa=R.checkMaterial({...steel,elasticModulus:200000},{uses:['stiffness']});
  assert.deepEqual(levels(mpa,'material.E.units'),['error']);
  const gcc=R.checkMaterial({...steel,density:7.85},{uses:['density']});
  assert.deepEqual(levels(gcc,'material.rho.units'),['warning']);
  assert.deepEqual(levels(R.checkMaterial({...steel,poissonRatio:0.5}),'material.nu.invalid'),['error']);
  assert.deepEqual(levels(R.checkMaterial(rubber),'material.nu.incompressible'),['warning']);
  assert.ok(codes(R.checkMaterial({...steel,yieldStrength:400,tensileStrength:300},{uses:['strength']})).includes('material.fy.above.ft'));
  assert.ok(codes(R.checkMaterial({...concrete,tensileStrength:30,compressiveStrength:20},{uses:['strength']})).includes('material.ft.above.fc'));
  assert.deepEqual(R.checkMaterial(steel,{uses:['stiffness','density','safety']}),[]);
  assert.deepEqual(levels(R.checkMaterial({...concrete,elasticModulus:null}),'material.E.missing'),['error']);
});

test('safety checks follow the strength theory and the material class',()=>{
  assert.ok(codes(R.checkMaterial({...steel,yieldStrength:null},{uses:['safety']})).includes('material.safety.fy'));
  assert.ok(codes(R.checkMaterial({...concrete,strengthCriterion:4},{uses:['safety']})).includes('material.safety.brittle'));
  assert.ok(codes(R.checkMaterial({...concrete,compressiveStrength:null},{uses:['safety']})).includes('material.safety.ftfc'));
});

test('deformation advice points to models suited to the material',()=>{
  const j2Concrete=R.checkDeformationCard(concrete,{model:'plastic',yieldStress:30e6,hardening:1e9,criticalPlasticStrain:0.1},{dimension:2});
  const mismatch=j2Concrete.find(f=>f.code==='deformation.model.mismatch');
  assert.equal(mismatch.level,'warning');assert.match(mismatch.zh,/AT2/);
  assert.match(R.checkDeformationCard(concrete,{model:'plastic'},{dimension:3}).find(f=>f.code==='deformation.model.mismatch').zh,/Mazars/);
  assert.ok(!codes(R.checkDeformationCard(steel,{model:'plastic',yieldStress:235e6,hardening:1.43e9,criticalPlasticStrain:0.1},{dimension:2})).includes('deformation.model.mismatch'));
  // Hyperelastic cards need finite deformation; parameters are checked against E.
  const hyper=R.checkDeformationCard(rubber,{model:'neoHooke',c10:5e6,d1:1e-9},{dimension:2,finiteStrain:false});
  assert.ok(codes(hyper).includes('deformation.hyper.finite'));
  assert.ok(codes(hyper).includes('deformation.hyper.E'));
  // A 2D-unavailable model is an error without a duplicated mismatch warning.
  const mazars2d=R.checkDeformationCard(concrete,{model:'mazars',epsd0:1e-4},{dimension:2});
  assert.deepEqual(levels(mazars2d,'deformation.mazars.dim'),['error']);
  assert.ok(!codes(mazars2d).includes('deformation.model.mismatch'));
});

test('phase-field and crack-band cards are checked against the mesh',()=>{
  const coarse=R.checkDeformationCard(concrete,{model:'phaseField',fractureEnergy:100,fractureLength:0.002},{dimension:2,solver:'phast',meshSize:0.01,modelSize:0.1});
  assert.ok(codes(coarse).includes('deformation.phase.mesh'));
  assert.ok(codes(coarse).includes('deformation.phase.strength'));
  const fine=R.checkDeformationCard(concrete,{model:'phaseField',fractureEnergy:100,fractureLength:0.02},{dimension:2,solver:'phast',meshSize:0.005,modelSize:0.5});
  assert.ok(!codes(fine).includes('deformation.phase.mesh'));
  const band=R.checkDeformationCard(concrete,{model:'crackBand',tensileStrength:3e6,crackBandEnergy:100},{dimension:3,meshSize:2});
  assert.ok(codes(band).includes('deformation.crack.mesh'));
  const settings=R.checkDeformationSettings({solver:'phast',planeMode:0,finiteStrain:true,increments:10,maxIncrements:10,loadFactor:1},{dimension:2});
  assert.deepEqual(codes(settings),['deformation.phast.plane','deformation.phast.finite']);
});

test('blast advice respects the laws available in the workspace',()=>{
  assert.match(R.checkBlastMaterial(concrete,'elastic').find(f=>f.code==='blast.law.mismatch').zh,/HJC/);
  assert.ok(!codes(R.checkBlastMaterial({name:'花岗岩',elasticModulus:50,poissonRatio:0.25,density:2650},'jh2')).includes('blast.law.mismatch'));
  const metal2d=R.checkBlastMaterial(steel,'elastic',{available:['elastic','jh2','mc']});
  assert.ok(codes(metal2d).includes('blast.metal.2d'));
  assert.ok(!codes(metal2d).includes('blast.law.mismatch'));
});

test('FSI checks cover boundaries, Reynolds and Mach numbers, added mass and SPH inputs',()=>{
  const water={name:'水',category:'liquid',model:'incompressible',density:998,viscosity:1e-3};
  const air={name:'空气',category:'gas',model:'incompressible',density:1.2,viscosity:1.8e-5,soundSpeed:343};
  const base={dimension:2,engine:'su2',analysis:'steady',turbulence:'none',fluid:water,speed:0.5,length:0.4,inlets:1,outlets:1,farfields:0,hasRestraints:true};
  assert.deepEqual(levels(R.checkFsi(base),'fsi.reynolds'),['warning']);
  assert.ok(!codes(R.checkFsi({...base,turbulence:'sst'})).includes('fsi.reynolds'));
  assert.deepEqual(levels(R.checkFsi({...base,outlets:0}),'fsi.outlet'),['error']);
  assert.deepEqual(levels(R.checkFsi({...base,inlets:0}),'fsi.inlet'),['error']);
  assert.deepEqual(levels(R.checkFsi({...base,hasRestraints:false}),'fsi.restraint'),['error']);
  assert.deepEqual(levels(R.checkFsi({...base,fluid:air,speed:150,turbulence:'sst'}),'fsi.mach'),['warning']);
  assert.deepEqual(levels(R.checkFsi({...base,turbulence:'sst',solidDensity:1100,relaxation:'fixed',relaxationFactor:0.8}),'fsi.addedmass'),['warning']);
  assert.deepEqual(levels(R.checkFsi({...base,turbulence:'sst',analysis:'transient',timeStep:1,steps:10,cellSize:0.005}),'fsi.cfl'),['warning']);
  const sph={dimension:3,engine:'sph',fluid:water,inlets:0,hasRestraints:true,gravity:0,speed:0,hasVoid:false};
  assert.deepEqual(codes(R.checkFsi(sph)).filter(c=>c.startsWith('fsi.sph')),['fsi.sph.still','fsi.sph.void']);
  assert.deepEqual(levels(R.checkFsi({...sph,fluid:{...air,model:'idealgas',gamma:1.4,gasConstant:287,temperature:293}}),'fsi.sph.gas'),['error']);
});

test('static checks find missing materials, restraints and loads',()=>{
  const ok=R.checkStatic({dimension:2,structureRegions:1,unassignedRegions:0,restraints:{any:true,x:true,y:true},loads:1,materials:[steel],safety:true});
  assert.deepEqual(ok,[]);
  const bad=R.checkStatic({dimension:3,structureRegions:2,unassignedRegions:1,restraints:{any:true,x:true,y:true,z:false},loads:0,materials:[]});
  assert.deepEqual(codes(bad),['static.material','static.restraint.axis','static.loads']);
  assert.deepEqual(codes(R.checkStatic({dimension:2,structureRegions:1,restraints:{any:true,x:true,y:true,singlePoint:true},loads:1})),['static.restraint.rotation']);
});

test('every finding has both languages and a known level',()=>{
  const all=[
    ...R.checkMaterial({name:'X',elasticModulus:5000,poissonRatio:0.6,density:3},{uses:['stiffness','density','safety','strength']}),
    ...R.checkDeformationCard(concrete,{model:'plastic',yieldStress:1e9,hardening:1e12,criticalPlasticStrain:3},{dimension:2}),
    ...R.checkFsi({dimension:2,engine:'su2',analysis:'transient',fluid:null}),
    ...R.adviseMaterial(steel),...R.adviseMaterial({name:'X'})];
  assert.ok(all.length>5);
  for(const f of all){
    assert.ok(['error','warning','tip'].includes(f.level),f.code);
    assert.ok(f.zh&&/[㐀-鿿]/u.test(f.zh),f.code);
    // Only user material names may stay in Chinese inside the English text.
    const english=f.en.replaceAll('C30混凝土','').replaceAll('Q235钢','');
    assert.ok(english&&!/[㐀-鿿]/u.test(english),`${f.code}: ${f.en}`);
  }
});
