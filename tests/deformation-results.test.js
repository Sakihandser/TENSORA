'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const settings=require('../deformation-settings'),exportsApi=require('../result-export');
test('nonlinear standard-view snapshot preserves nodal displacements, tensors and per-material initiation without static writeback',async()=>{
 const context=vm.createContext({DeformationSettings:settings,isFinitePoint:p=>Number.isFinite(p.x)&&Number.isFinite(p.y)});
 for(const file of ['src/pages/results/render.js','src/pages/deformation-results.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'..',file),'utf8'),context);
 const r={runId:'test-run',settings:{planeMode:1,loadFactor:2},materialSettings:{1:{model:'plastic',criticalPlasticStrain:.1},2:{model:'elastic',criticalPlasticStrain:.2}},model:{modelName:'Nonlinear fixture',nodes:[{nodeNo:1,x:0,y:0},{nodeNo:2,x:1,y:0},{nodeNo:3,x:1,y:1},{nodeNo:4,x:0,y:1}],elements:[{elementNo:1,node1:1,node2:2,node3:3,materialNo:1},{elementNo:2,node1:1,node2:3,node3:4,materialNo:2}]},frames:[{time:.5,displacement:{},stress:{},strain:{},plasticStrain:{}}]};
 for(let i=1;i<=4;i++){r.frames[0].displacement[i]=[.003,.004,0];r.frames[0].stress[i]=[100e6,20e6,30e6,5e6,0,0];r.frames[0].strain[i]=[.01,-.002,0,.001,0,0];r.frames[0].plasticStrain[i]=[.05];}
 const before=JSON.stringify(r),data=context.buildDeformationResultSnapshot(r,0);
 assert.equal(JSON.stringify(r),before);assert.equal(data.nodes[0].displacementMagnitude,.005);assert.equal(data.planeMode,1);assert.equal(data.elements[0].stressZz,30e6);assert.equal(data.elements[0].strainXy,.001);assert.ok(Math.abs(data.elements[0].plasticStrain-.05)<1e-15);assert.ok(Math.abs(data.elements[0].damage-.5)<1e-15);assert.equal(data.elements[1].damage,0);assert.equal(data.elements[1].plasticStrain,0);assert.equal(data.elements[0].safetyCode,4);assert.equal(data.loadFactor,1);assert.equal(data.runInfo.deformationFrame,true);
 const fields=exportsApi.fields(data);assert.ok(fields.some(f=>f.key==='plasticStrain'));assert.ok(fields.some(f=>f.key==='damage'&&f.title.includes('initiation')));assert.ok(!fields.some(f=>f.key==='safetyCode'));
 const entries=[];for await(const item of exportsApi.documents(data))entries.push(item);
 const source=JSON.parse(entries.find(e=>e.name==='source.json').text);assert.equal(source.runId,'test-run');assert.equal(source.materialSettings[1].criticalPlasticStrain,.1);assert.equal(source.loadFactor,1);
 assert.match(entries.find(e=>e.name==='index.html').text,/CalculiX 非线性结果/);
 r.completed=false;r.termination={code:'increment-limit',convergedFraction:.5};const partial=context.buildDeformationResultSnapshot(r,0),partialEntries=[];for await(const item of exportsApi.documents(partial))partialEntries.push(item);
 assert.equal(partial.completed,false);assert.equal(partial.result.completed,false);assert.equal(JSON.parse(partialEntries.find(e=>e.name==='source.json').text).completed,false);assert.match(partialEntries.find(e=>e.name==='index.html').text,/未完成目标载荷/);
});
