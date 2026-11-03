'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../src/core/drawing-recovery.js'),'utf8');
const snap=name=>JSON.stringify({scene:{name,geometryNodes:[{id:'G1',x:1,y:2}],curves:[],regions:[],pointLoads:[{id:'F1',fx:3000,fy:0}],distributedLoads:[],bodyLoads:[]},activeTool:'select',draft:null,constructionMode:false});
function harness(fetch){
 const storage=new Map(),timers=new Map(),status={textContent:''};let tid=0;
 const ctx=vm.createContext({fetch,setTimeout:fn=>{timers.set(++tid,fn);return tid;},window:{location:{pathname:'/'},localStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)}},
 document:{getElementById:()=>status},scene:{name:'untouched'},TOOL_LABELS:{select:'Select'},toolButtons:[],toolName:{},modelName:{},uiText:s=>s,canvas:{classList:{toggle(){}}},normalizeScene:s=>({...s,analysisNodes:[],mesh:{elements:[],metadata:null}}),rebuildDerivedRegions(){},fitViewToScene(){},updatePanel(){},render(){}});
 vm.runInContext(source,ctx);return {ctx,timers,storage,status};
}
test('autosave coalesces input and has only one in-flight request while retaining latest changes',async()=>{
 const requests=[];const h=harness((url,options)=>new Promise(resolve=>requests.push({body:JSON.parse(options.body),resolve})));
 for(let i=0;i<50;i++)h.ctx.scheduleDrawingRecovery(snap('input '+i));assert.equal(h.timers.size,1);
 const saving=h.ctx.flushDrawingRecovery();assert.equal(requests.length,1);assert.equal(requests[0].body.snapshot.scene.name,'input 49');
 h.ctx.scheduleDrawingRecovery(snap('latest'));await h.ctx.flushDrawingRecovery();assert.equal(requests.length,1);
 requests[0].resolve({ok:true});await saving;assert.equal(requests.length,2);assert.equal(requests[1].body.snapshot.scene.name,'latest');
 requests[1].resolve({ok:true});await new Promise(resolve=>setImmediate(resolve));assert.equal(h.status.textContent,'草稿已自动保存');
});
test('startup restores saved geometry and loads using workspace-scoped storage',async()=>{
 const h=harness(async()=>({ok:true,json:async()=>({workspaceId:'workspace1',savedAt:'2026-10-29T00:00:00.000Z',snapshot:JSON.parse(snap('Restored'))})}));
 await h.ctx.initializeDrawingRecovery();assert.equal(h.ctx.scene.name,'Restored');assert.equal(h.ctx.scene.pointLoads[0].fx,3000);assert.equal(h.ctx.scene.analysisNodes.length,0);assert.equal(h.status.textContent,'草稿已恢复');
 h.ctx.scheduleDrawingRecovery(snap('edited'));h.ctx.checkpointDrawingBeforeExit();assert.ok(h.storage.has('fem-drawing-recovery-v1:workspace1'));
});
test('slow recovery reads never replace a drawing that the user has already started editing',async()=>{
 let finish;const h=harness(()=>new Promise(resolve=>{finish=resolve;}));const init=h.ctx.initializeDrawingRecovery();
 h.ctx.scene.name='New user drawing';h.ctx.scheduleDrawingRecovery(snap('New user drawing'));
 finish({ok:true,json:async()=>({snapshot:JSON.parse(snap('Old draft')),savedAt:'2026-10-29T00:00:00.000Z'})});await init;assert.equal(h.ctx.scene.name,'New user drawing');
});
test('failed autosave keeps browser recovery and reports failure without throwing',async()=>{
 const h=harness(async()=>{throw new Error('disk unavailable');});h.ctx.scheduleDrawingRecovery(snap('Retained'));await h.ctx.flushDrawingRecovery();assert.match(h.status.textContent,/保存失败/);assert.equal(h.storage.size,1);
});

test('edits made before material loading finishes also prevent startup recovery from replacing them',async()=>{
 const h=harness(async()=>({ok:true,json:async()=>({snapshot:JSON.parse(snap('Old draft')),savedAt:'2026-10-29T00:00:00.000Z'})}));
 h.ctx.scene.name='Already editing';h.ctx.scheduleDrawingRecovery(snap('Already editing'));await h.ctx.initializeDrawingRecovery();assert.equal(h.ctx.scene.name,'Already editing');
});
