'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
test('drawing animation has one pending frame through repeated rendering and input',()=>{
 const frames=new Map();let id=0,max=0;
 const ctx=vm.createContext({animation:{running:true,time:0,frame:null},ctx:{setTransform(){},clearRect(){}},dpr:1,view:{width:100,height:100},layers:{},
 currentPageKey:()=> 'home',requestAnimationFrame:cb=>{frames.set(++id,cb);max=Math.max(max,frames.size);return id;},cancelAnimationFrame:i=>frames.delete(i),animationIcon:{innerHTML:''}});
 for(const f of ['render-base','view-interactions'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/pages/drawing',f+'.js'),'utf8'),ctx);
 vm.runInContext('drawGrid=drawDraft=drawHover=drawShapePreview=()=>{};',ctx);
 for(let cycle=0;cycle<50;cycle++){
  for(let i=0;i<100;i++)ctx.render();
  assert.equal(frames.size,1);
  const [key,callback]=frames.entries().next().value;frames.delete(key);callback(cycle*16+1);
 }
 assert.equal(max,1);ctx.toggleAnimation();assert.equal(frames.size,0);
 ctx.toggleAnimation();assert.equal(frames.size,1);ctx.toggleAnimation();assert.equal(frames.size,0);
});

test('large mesh load editing stays within a 128 MiB JS heap',()=>{
 const {spawnSync}=require('node:child_process');const r=spawnSync(process.execPath,['--expose-gc','--max-old-space-size=128',path.join(__dirname,'../scripts/check-drawing-memory.cjs')],{encoding:'utf8',windowsHide:true,timeout:30000});assert.equal(r.status,0,r.stdout+r.stderr);const metrics=JSON.parse(r.stdout);assert.equal(metrics.edits,1000);assert.ok(metrics.historyBytes<1000000);assert.ok(metrics.heapGrowthBytes<8*1024*1024);
});
