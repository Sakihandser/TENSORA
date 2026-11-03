'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),path=require('node:path'),fs=require('node:fs'),vm=require('node:vm'),os=require('node:os');
const {spawnSync}=require('node:child_process');
const {encodeCalculationModelBinary:encode,decodeCalculationResultBinary:decode}=require('../calculation-ipc');
const {estimateZZError}=require('../src/core/adaptive-mesh');
const root=path.resolve(__dirname,'..'),exe=path.join(root,'TensoraCore/x64/Release/TensoraCore.exe');
function model(planeMode=0,sx=80e6,sy=0,tau=0,criterion=4,nu=.3){
 const m={materialNo:1,elasticModulus:200e9,poissonRatio:nu,density:7850,yieldStrength:100e6,tensileStrength:100e6,compressiveStrength:200e6,strengthCriterion:criterion};
 return {planeMode,modelName:'plane verification',materials:[m],nodes:[
 {nodeNo:1,x:0,y:0,fixUx:true,fixUy:true,dofUx:1,dofUy:2},
 {nodeNo:2,x:1,y:0,fixUy:true,dofUx:3,dofUy:4,forceX:sx/2},
 {nodeNo:3,x:0,y:1,dofUx:5,dofUy:6,forceX:tau/2,forceY:sy/2}].map(n=>({materialNo:1,regionNo:1,...n})),elements:[{...m,elementNo:1,node1:1,node2:2,node3:3,area:.5,centroidX:1/3,centroidY:1/3}],elementNodeLoads:[]};
}
function run(m,backend='cpu',input=encode(m)){const r=spawnSync(exe,['--binary-ipc'],{cwd:root,input,env:{...process.env,FEM_COMPUTE:backend},windowsHide:true,timeout:30000});assert.equal(r.status,0,r.stderr.toString());return decode(r.stdout);}
function close(a,b){assert.ok(Math.abs(a-b)<1e-8*Math.max(1,Math.abs(b)),`${a} != ${b}`);}
test('analytic TRI3 patch: both modes, shear and clockwise connectivity',()=>{
 for(const mode of [0,1])for(const reverse of [false,true]){
  const m=model(mode,80e6,-20e6,15e6);if(reverse)[m.elements[0].node2,m.elements[0].node3]=[m.elements[0].node3,m.elements[0].node2];
  const r=run(m),e=r.elementResults[0],sz=mode?.3*60e6:0;
  assert.equal(r.planeMode,mode);close(e.stressXx,80e6);close(e.stressYy,-20e6);close(e.stressXy,15e6);close(e.stressZz,sz);
  close(e.strainXx,(80e6-.3*(-20e6+sz))/200e9);close(e.strainYy,(-20e6-.3*(80e6+sz))/200e9);close(e.strainXy,15e6*1.3/200e9);
  close(e.strainZz,mode?0:-.3*60e6/200e9);
  close(e.equivalentStress,Math.sqrt(80e6**2+20e6**2+sz**2+80e6*20e6-60e6*sz+3*15e6**2));
 }
});
test('all strength criteria use the out-of-plane state',()=>{
 for(const criterion of [3,4]){assert.equal(run(model(0,110e6,110e6,0,criterion)).elementResults[0].safetyCode,3);assert.equal(run(model(1,110e6,110e6,0,criterion)).elementResults[0].safetyCode,0);}
 assert.equal(run(model(0,-180e6,-180e6,0,2)).elementResults[0].safetyCode,2);assert.equal(run(model(1,-180e6,-180e6,0,2)).elementResults[0].safetyCode,0);
 assert.equal(run(model(0,-80e6,-80e6,0,1,-.8)).elementResults[0].safetyCode,0);assert.equal(run(model(1,-80e6,-80e6,0,1,-.8)).elementResults[0].safetyCode,2);
});
test('CPU/GPU parity for both assumptions and all criteria',()=>{
 for(const mode of [0,1])for(const c of [1,2,3,4]){const m=model(mode,110e6,110e6,20e6,c),a=run(m).elementResults[0],b=run(m,'gpu').elementResults[0];for(const k of ['strainXx','strainYy','strainXy','stressXx','stressYy','stressXy','stressZz','equivalentStress'])close(a[k],b[k]);assert.equal(a.safetyCode,b.safetyCode);}
});
test('legacy v2 input defaults to plane stress; invalid plane mode rejected at both boundaries',()=>{
 const m=model(),b=encode(m),old=Buffer.concat([b.subarray(0,12),b.subarray(16)]);old.writeUInt32LE(2,8);close(run(m,'cpu',old).elementResults[0].stressZz,0);
 assert.throws(()=>encode({...m,planeMode:2}));b.writeInt32LE(2,12);const r=spawnSync(exe,['--binary-ipc'],{cwd:root,input:b,windowsHide:true});assert.notEqual(r.status,0);assert.match(r.stderr.toString(),/plane mode/);
});
test('TXT and binary exports preserve mode and out-of-plane tensors',()=>{
 const ctx=vm.createContext({});for(const f of ['src/core/calculation-export.js','src/pages/results/render.js'])vm.runInContext(fs.readFileSync(path.join(root,f),'utf8'),ctx);
 const m=model(1,110e6,110e6),mat=m.materials[0];
 const p={model:{name:'plane-text',planeMode:1},materials:[{id:'M',properties:mat}],nodes:m.nodes.map(n=>({number:n.nodeNo,x:n.x,y:n.y,constraints:{ux:n.fixUx,uy:n.fixUy},dof:{ux:n.dofUx,uy:n.dofUy},loads:{fx:n.forceX||0,fy:n.forceY||0},materialId:'M'})),elements:[{number:1,nodeNumbers:[1,2,3],area:.5,centroid:{x:1/3,y:1/3},materialId:'M',mechanicalProperties:mat}],counts:{nodes:3,elements:1,materials:1}};
 const text=ctx.calculationInputPayloadToText(p);assert.match(text,/PLANE_MODE 1/);assert.equal(ctx.calculationInputPayloadToDirectModel(p).planeMode,1);
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'fem-plane-'));fs.mkdirSync(path.join(dir,'calculation-data'));
 try{fs.writeFileSync(path.join(dir,'calculation-data/calculation-input.txt'),text);const r=spawnSync(exe,[],{cwd:dir,windowsHide:true,timeout:30000});assert.equal(r.status,0,r.stderr.toString());const parsed=ctx.parseCalculationResultText(fs.readFileSync(path.join(dir,'calculation-data/calculation-result.txt'),'utf8'));assert.equal(parsed.planeMode,1);close(parsed.elementResults[0].stressZz,66e6);close(parsed.elementResults[0].equivalentStress,44e6);assert.equal(parsed.elementResults[0].safetyCode,0);}
 finally{fs.rmSync(dir,{recursive:true,force:true});}
});
test('ZZ energy uses plane-strain compliance and preserves constant stress patches',()=>{
 const base={materials:[],nodes:[],elements:[{number:1,id:'E1',nodeNumbers:[1,2,3],nodeIds:['A1','A2','A3'],area:.5,mechanicalProperties:{elasticModulus:200e9,poissonRatio:.3}}]};
 const r={elementResults:[{elementNo:1,stressXx:80e6,stressYy:20e6,stressXy:10e6}]};
 for(const mode of [0,1]){const e=estimateZZError({...base,model:{planeMode:mode}},r);assert.equal(e.totalError,0);assert.equal(e.relativeError,0);}
});
test('ZZ plane-strain error energy matches the analytic two-triangle integral',()=>{
 const mat={elasticModulus:200e9,poissonRatio:.3};
 const p={elements:[{number:1,id:'E1',nodeIds:['A','B','C'],area:.5,mechanicalProperties:mat},{number:2,id:'E2',nodeIds:['A','C','D'],area:.5,mechanicalProperties:mat}]};
 const r={elementResults:[{elementNo:1,stressXx:80e6,stressYy:20e6,stressXy:10e6},{elementNo:2,stressXx:0,stressYy:0,stressXy:0}]};
 for(const mode of [0,1]){const energy=((mode?.91:1)*(80e6**2+20e6**2)-2*(mode?.39:.3)*80e6*20e6+2.6*10e6**2)/400e9;close(estimateZZError({...p,model:{planeMode:mode}},r).totalError,Math.sqrt(energy/8));}
});
test('plane-strain mixed materials recover sigma_zz using each local Poisson ratio',()=>{
 const a=model(1,60e6,40e6,0,4,.2),b=model(1,60e6,40e6,0,4,.4);b.materials[0].materialNo=2;
 for(const n of b.nodes){n.nodeNo+=3;n.dofUx+=6;n.dofUy+=6;n.x+=2;n.materialNo=2;}
 const e=b.elements[0];e.elementNo=2;e.materialNo=2;e.node1+=3;e.node2+=3;e.node3+=3;e.centroidX+=2;
 a.nodes.push(...b.nodes);a.materials.push(...b.materials);a.elements.push(e);
 for(const backend of ['cpu','gpu']){const r=run(a,backend);close(r.elementResults[0].stressZz,20e6);close(r.elementResults[1].stressZz,40e6);}
});
test('legacy v1 results remain readable after adding out-of-plane output',()=>{
 const r=spawnSync(exe,['--binary-ipc'],{cwd:root,input:encode(model()),windowsHide:true});assert.equal(r.status,0,r.stderr.toString());
 const old=Buffer.concat([r.stdout.subarray(0,12),r.stdout.subarray(16,-16)]);old.writeUInt32LE(1,8);const result=decode(old);assert.equal(result.planeMode,0);close(result.elementResults[0].stressXx,80e6);assert.equal(result.elementResults[0].stressZz,0);
});
