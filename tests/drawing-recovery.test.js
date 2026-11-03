'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs/promises'),os=require('node:os'),path=require('node:path');
const {createDrawingRecoveryStore}=require('../drawing-recovery-store');
const snapshot=name=>({scene:{version:6,name,geometryNodes:[{id:'G1',x:1,y:2}],curves:[],regions:[],pointLoads:[{id:'F1',fx:12,fy:34}],distributedLoads:[],bodyLoads:[],analysisNodes:[{id:'A1'}],mesh:{elements:[{id:'E1'}]}},activeTool:'line',constructionMode:true,draft:{kind:'line',points:[{x:1,y:2}]}});
test('disk checkpoint survives store restart, omits mesh, and invalid data cannot erase it',async t=>{
 const dir=await fs.mkdtemp(path.join(os.tmpdir(),'fem-drawing-recovery-'));t.after(()=>fs.rm(dir,{recursive:true,force:true}));
 const store=createDrawingRecoveryStore(dir);assert.equal((await store.read()).snapshot,null);
 await store.save(snapshot('restored'));const recovered=await createDrawingRecoveryStore(dir).read();
 assert.equal(recovered.snapshot.scene.name,'restored');assert.equal(recovered.snapshot.scene.pointLoads[0].fx,12);
 assert.equal(recovered.snapshot.scene.mesh,undefined);assert.equal(recovered.snapshot.scene.analysisNodes,undefined);
 assert.equal(recovered.snapshot.activeTool,'line');assert.equal(recovered.snapshot.draft.points[0].x,1);
 assert.throws(()=>store.save({scene:{}}),/Invalid/);assert.equal((await store.read()).snapshot.scene.name,'restored');
 const pending=[];for(let i=0;i<20;i++)pending.push(store.save(snapshot(String(i))));await Promise.all(pending);
 assert.equal((await store.read()).snapshot.scene.name,'19');assert.deepEqual(await fs.readdir(dir),['drawing-draft.json']);
});

test('late autosave delivery cannot overwrite a newer checkpoint',async t=>{
 const dir=await fs.mkdtemp(path.join(os.tmpdir(),'fem-recovery-order-'));t.after(()=>fs.rm(dir,{recursive:true,force:true}));const store=createDrawingRecoveryStore(dir);
 await store.save({snapshot:snapshot('new'),savedAt:'2026-10-29T10:00:01.000Z'});
 await store.save({snapshot:snapshot('old'),savedAt:'2026-10-29T10:00:00.000Z'});
 assert.equal((await store.read()).snapshot.scene.name,'new');
});
