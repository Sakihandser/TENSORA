'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),vm=require('node:vm');
const {spawnSync}=require('node:child_process');
const {encodeCalculationModelBinary,decodeCalculationResultBinary}=require('../calculation-ipc');
const root=path.resolve(__dirname,'..'),exe=path.join(root,'TensoraCore/x64/Release/TensoraCore.exe');
function model(c,sx=0,sy=0,tau=0,props={}){
 const mat={materialNo:1,elasticModulus:200e9,poissonRatio:.3,density:7850,yieldStrength:100e6,tensileStrength:100e6,compressiveStrength:200e6,strengthCriterion:c,...props};
 return {modelName:'strength',units:{length:'m',force:'N',elasticModulus:'Pa',density:'kg/m3',strength:'Pa'},materials:[mat],nodes:[
 {nodeNo:1,x:0,y:0,fixUx:true,fixUy:true,dofUx:1,dofUy:2},
 {nodeNo:2,x:1,y:0,fixUy:true,dofUx:3,dofUy:4,forceX:sx/2},
 {nodeNo:3,x:0,y:1,dofUx:5,dofUy:6,forceX:tau/2,forceY:sy/2}],
 elements:[{...mat,elementNo:1,node1:1,node2:2,node3:3,area:.5,centroidX:1/3,centroidY:1/3}],elementNodeLoads:[]};
}
function run(m,backend='cpu'){
 m.nodes=m.nodes.map(n=>({materialNo:1,regionNo:1,...n}));
 return spawnSync(exe,['--binary-ipc'],{cwd:root,input:encodeCalculationModelBinary(m),env:{...process.env,FEM_COMPUTE:backend},windowsHide:true,timeout:30000});
}
function solve(m,backend){const r=run(m,backend);assert.equal(r.status,0,r.stderr?.toString());return decodeCalculationResultBinary(r.stdout).elementResults[0];}
function check(c,sx,sy,tau,expected,props){const r=solve(model(c,sx,sy,tau,props));assert.equal(r.safetyCode,expected,JSON.stringify(r));return r;}
test('Rankine: asymmetric tensile/compressive limits and zero stress',()=>{
 check(1,0,0,0,0);check(1,90e6,0,0,0);check(1,101e6,0,0,2);check(1,0,-201e6,0,1);
 check(1,110e6,-240e6,0,1); // report the larger utilization
});
test('Saint-Venant: Poisson coupling and out-of-plane principal strain',()=>{
 check(1,90e6,-90e6,0,0);check(2,90e6,-90e6,0,2);
 check(2,-180e6,-180e6,0,2); // E epsilon_z=108 MPa
 check(2,80e6,80e6,0,0);
});
test('Tresca and von Mises distinguish pure shear, include sigma_z=0',()=>{
 check(3,0,0,55e6,3);check(4,0,0,55e6,0);
 check(3,0,0,60e6,3);check(4,0,0,60e6,3);
 check(3,110e6,110e6,0,3);check(4,110e6,110e6,0,3);
});
test('missing required data never reports safe; legacy auto selects criterion',()=>{
 for(const c of [1,2])check(c,0,0,0,4,{compressiveStrength:0});
 for(const c of [3,4])check(c,0,0,0,4,{yieldStrength:0});
 check(0,0,0,55e6,0);check(0,101e6,0,0,2,{yieldStrength:0});
 assert.notEqual(run(model(99)).status,0);
});
test('CPU/GPU result parity for all criteria',()=>{
 for(const c of [1,2,3,4]){const m=model(c,90e6,-90e6,10e6);const a=solve(m,'cpu'),b=solve(m,'gpu');assert.equal(a.safetyCode,b.safetyCode);}
});
test('mixed-material model applies each element criterion independently',()=>{
 const a=model(3,0,0,55e6),b=model(4,0,0,55e6);
 b.nodes.forEach(n=>{n.nodeNo+=3;n.x+=2;n.dofUx+=6;n.dofUy+=6;});
 const e=b.elements[0];e.elementNo=2;e.materialNo=2;e.node1+=3;e.node2+=3;e.node3+=3;e.centroidX+=2;b.materials[0].materialNo=2;
 a.nodes.push(...b.nodes);a.elements.push(e);a.materials.push(...b.materials);
 const r=run(a);assert.equal(r.status,0,r.stderr?.toString());assert.deepEqual(decodeCalculationResultBinary(r.stdout).elementResults.map(e=>e.safetyCode),[3,0]);
});
test('material card, snapshots and solver export preserve criterion and units',()=>{
 const ctx=vm.createContext({MATERIAL_SWATCHES:['#000000']});
 for(const f of ['src/core/numbers.js','src/core/scene-objects.js','src/core/material-utils.js','src/pages/materials/library.js','src/core/regions.js','src/core/calculation-export.js'])vm.runInContext(fs.readFileSync(path.join(root,f),'utf8'),ctx);
 for(const c of [1,2,3,4]){const m=ctx.normalizeMaterial({id:'M',name:'test',strengthCriterion:c,yieldStrength:100,tensileStrength:120,compressiveStrength:200});const s=ctx.createMaterialSnapshot(m),p=ctx.materialPropertiesForSolver(s);assert.equal(p.strengthCriterion,c);assert.equal(p.yieldStrength,100e6);assert.equal(ctx.materialMechanicalProperties(s).strengthCriterion,c);}
});
test('TXT input appended criterion is read; legacy missing column uses auto',()=>{
 const ctx=vm.createContext({});vm.runInContext(fs.readFileSync(path.join(root,'src/core/calculation-export.js'),'utf8'),ctx);
 const m=model(3,0,0,55e6);
 const payload={model:{name:'text-strength'},materials:[{id:'M',properties:m.materials[0]}],nodes:m.nodes.map(n=>({number:n.nodeNo,x:n.x,y:n.y,constraints:{ux:n.fixUx,uy:n.fixUy},dof:{ux:n.dofUx,uy:n.dofUy},loads:{fx:n.forceX||0,fy:n.forceY||0},materialId:'M'})),elements:[{number:1,nodeNumbers:[1,2,3],area:.5,centroid:{x:1/3,y:1/3},materialId:'M',mechanicalProperties:m.materials[0]}],counts:{nodes:3,elements:1,materials:1},units:m.units};
 // Export uses declared units from the normal frontend payload.
 payload.units={length:'m',force:'N',elasticModulus:'Pa',density:'kg/m3',strength:'Pa'};
 const text=ctx.calculationInputPayloadToText(payload);
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'fem-strength-'));fs.mkdirSync(path.join(dir,'calculation-data'));
 try{for(const legacy of [false,true]){const input=legacy?text.replace(/^(1 .*?) 3$/mg,'$1'):text;fs.writeFileSync(path.join(dir,'calculation-data/calculation-input.txt'),input);const r=spawnSync(exe,[],{cwd:dir,windowsHide:true,timeout:30000});assert.equal(r.status,0,r.stderr?.toString());const result=fs.readFileSync(path.join(dir,'calculation-data/calculation-result.txt'),'utf8');assert.match(result,legacy?/\b0 OK\b/:/\b3 YIELD_LIMIT\b/);}}
 finally{fs.rmSync(dir,{recursive:true,force:true});}
});
