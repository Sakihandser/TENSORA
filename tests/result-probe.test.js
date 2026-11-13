// Point probes: mesh location, interpolation, CSV output and server-side histories.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const P=require('../src/core/result-probe');
const close=(actual,expected,tolerance=1e-12)=>assert.ok(Math.abs(actual-expected)<=tolerance,`${actual} != ${expected}`);

test('triangle location returns barycentric weights and respects the displayed configuration',()=>{
  const n=[{nodeNo:1,x:0,y:0,ux:0,uy:0},{nodeNo:2,x:1,y:0,ux:.5,uy:0},{nodeNo:3,x:0,y:1,ux:0,uy:0},{nodeNo:4,x:1,y:1,ux:.5,uy:0}];
  const elements=[{elementNo:1,nodes:[n[0],n[1],n[2]]},{elementNo:2,nodes:[n[1],n[3],n[2]]}];
  const hit=P.locateTriangle(elements,{x:.25,y:.25});
  assert.equal(hit.element.elementNo,1);
  [.5,.25,.25].forEach((w,i)=>close(hit.weights[i],w));
  assert.equal(P.locateTriangle(elements,{x:.75,y:.75}).element.elementNo,2);
  assert.equal(P.locateTriangle(elements,{x:2,y:2}),null);
  // A point on the shared edge belongs to one of the two triangles with weights summing to one.
  const edge=P.locateTriangle(elements,{x:.5,y:.5});
  close(edge.weights.reduce((a,b)=>a+b,0),1);
  // In the deformed configuration (factor 1) x=1.4 lies inside the stretched mesh.
  const deformed=P.locateTriangle(elements,{x:1.4,y:.1},node=>({x:node.x+node.ux,y:node.y+node.uy}));
  assert.ok(deformed);
  const reference=deformed.element.nodes.reduce((sum,node,i)=>sum+deformed.weights[i]*node.x,0);
  assert.ok(reference<1&&reference>.8,String(reference));
  assert.equal(P.nearestNode(n,{x:.9,y:1.2}).node.nodeNo,4);
});

test('tetrahedron location interpolates linear fields exactly and skips hidden volumes',()=>{
  const nodes=[[0,0,0],[1,0,0],[0,1,0],[0,0,1],[1,1,1]];
  const tets=[[0,1,2,3],[1,2,3,4]];
  const point=[.2,.3,.1];
  const found=P.locateTet(nodes,tets,point);
  assert.equal(found.tet,0);
  const linear=nodes.map(([x,y,z])=>2*x-3*y+5*z+7);
  close(P.interpolate(linear,found.ids,found.weights),2*.2-3*.3+5*.1+7,1e-12);
  assert.equal(P.locateTet(nodes,tets,point,{skip:i=>i===0}),null);
  assert.equal(P.locateTet(nodes,tets,[3,3,3]),null);
  const second=P.locateTet(nodes,tets,[.6,.6,.6]);
  assert.equal(second.tet,1);
  close(second.weights.reduce((a,b)=>a+b,0),1);
  assert.deepEqual(P.nearestNode3(nodes,[.9,.9,1.2]).index,4);
});

test('derived quantities and CSV histories',()=>{
  const [s1,s2]=P.principal2d(10,-2,4);
  close(s1+s2,8);close(s1*s2,10*-2-16);
  close(P.vonMises(100,0,0,0,0,0),100);
  close(P.vonMises(0,0,0,10,0,0),Math.sqrt(300));
  close(P.equivalentStrain(.001,-.0005,-.0005,0,0,0),.001,1e-15);
  assert.equal(P.formatValue(0),'0');assert.equal(P.formatValue(12.3456789),'12.3457');assert.equal(P.formatValue(1.5e-7),'1.5000e-7');
  assert.equal(P.formatValue(undefined),'—');
  const history={axes:[{label:'时间',unit:'ms',values:[0,.5]}],series:[{ux:[0,1e-3]},{ux:[0,2e-3]}]};
  const rows=P.historyRows([{label:'P1'},{label:'P2'}],history,[{key:'ux',label:'X 位移 Ux',unit:'m'}]);
  assert.deepEqual(rows[0],['帧','时间 (ms)','P1 X 位移 Ux (m)','P2 X 位移 Ux (m)']);
  assert.deepEqual(rows[2],[1,.5,1e-3,2e-3]);
  const csv=P.csvText([['a,b','x"y'],[1,NaN]]);
  assert.equal(csv,'﻿"a,b","x""y"\r\n1,\r\n');
  const ticks=P.niceTicks(0,.93);
  assert.ok(ticks.ticks.length>=3&&ticks.min<=0&&ticks.max>=.93);
});

test('probe labels, notes and messages have English translations',()=>{
  const vm=require('node:vm'),source=fs.readFileSync(path.join(__dirname,'..','src','global','i18n.js'),'utf8');
  const context={console,Element:class{},HTMLInputElement:class{},CanvasRenderingContext2D:class{},MutationObserver:class{observe(){}disconnect(){}},
    CustomEvent:class{},Node:{TEXT_NODE:3},NodeFilter:{SHOW_ELEMENT:1,SHOW_TEXT:4},
    document:{documentElement:{},getElementById:()=>null,createTreeWalker:()=>({nextNode:()=>null})},
    window:{localStorage:{getItem:()=> 'en',setItem(){}},alert(){},confirm(){},addEventListener(){},dispatchEvent(){}}};
  context.window.window=context.window;vm.runInNewContext(source,context);
  const translate=context.window.femI18n.translateEnglish;
  const texts=[];
  // Export-name stems and the surface prefix are only shown as part of a composed text (checked below).
  const fragments=new Set(['测点结果','-时程.csv','二维测点结果','损伤变形测点结果','三维测点结果','表面']);
  for(const file of ['src/core/result-probe.js','src/pages/results/probe.js','src/pages/solid3d-probe.js']){
    const code=fs.readFileSync(path.join(__dirname,'..',file),'utf8');
    for(const match of code.matchAll(/(['"])((?:(?!\1).)*[㐀-鿿](?:(?!\1).)*)\1/gu))if(!match[2].includes('${')&&!fragments.has(match[2]))texts.push(match[2]);
  }
  for(const stem of ['测点结果','二维测点结果','损伤变形测点结果','三维测点结果'])texts.push(stem+'.csv',stem+'-时程.csv');
  texts.push('单元 12 · 节点 5','四面体 30 · 节点 7','表面 · 节点 9','删除测点 P3','P2 X 位移 Ux (m)','正应力 σxx (Pa)','时间 (ms)','正在读取测点时程… 40%',
    '该点不在网格内，已吸附到最近节点 18（距离 1.5000e-4 m）。','测点 Z (m)');
  const untranslated=[...new Set(texts)].filter(text=>/[㐀-鿿]/u.test(translate(text)));
  assert.deepEqual(untranslated,[]);
  assert.equal(context.window.femI18n.sourceMessage('Invalid probe indices.'),'测点编号无效。');
});

test('2D blast probe endpoint returns node and element histories that match saved frames',async t=>{
  const Codec=require('../blast-frame-codec'),{runBlastCore}=require('../server'),{serveBlastHistory,removeRun}=require('../blast-runner'),{blastRing}=require('./helpers/blast-ring');
  const model=blastRing({sectors:12,rings:2});
  const h=await runBlastCore(model,{fracture:false,frames:4,pulse:.00005,duration:.0001},{lazy:true});
  t.after(()=>removeRun(h.id));
  const server=http.createServer((request,response)=>serveBlastHistory(new URL(request.url,'http://localhost'),response));
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  t.after(()=>{server.closeAllConnections();return new Promise(resolve=>server.close(resolve));});
  const root=`http://127.0.0.1:${server.address().port}/api/blast-runs/${h.id}`;
  const response=await fetch(root+'/probe?nodes=0,5&elements=3');
  const body=await response.json();
  assert.equal(response.status,200);assert.equal(body.ok,true);
  assert.equal(body.times.length,4);assert.equal(body.nodes.length,2);assert.equal(body.elements[0].cells.length,4);
  const frame=Codec.decode(await (await fetch(root+'/frames/2')).arrayBuffer(),h);
  assert.deepEqual(body.nodes[1].u[2],[frame.u[10],frame.u[11]]);
  assert.deepEqual(body.nodes[1].v[2],[frame.v[10],frame.v[11]]);
  assert.deepEqual(body.elements[0].cells[2],Array.from(frame.elements[3]));
  assert.equal(body.times[2],frame.time);
  assert.equal((await fetch(root+'/probe?nodes=99999')).status,400);
  assert.equal((await fetch(root+'/probe?elements=-1')).status,400);
});

test('3D blast probe reader extracts per-frame nodal values of every saved field',async t=>{
  const blast3d=require('../blast3d-runner'),runId='run-probetest'+process.pid;
  const dir=path.join(blast3d.RUNS,runId);fs.mkdirSync(dir,{recursive:true});
  t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));
  const fields=['ux','vm'],n=3;
  fs.writeFileSync(path.join(dir,'summary.json'),JSON.stringify({fields,nodeCount:n,frames:[{time:0},{time:1e-5}]}));
  for(let k=0;k<2;k++){
    const values=new Float32Array(fields.length*n);for(let i=0;i<values.length;i++)values[i]=k*100+i;
    fs.writeFileSync(path.join(dir,`frame-${String(k).padStart(4,'0')}.bin`),Buffer.from(values.buffer));
  }
  const probe=await blast3d.readProbe(runId,'2,0');
  assert.deepEqual(probe.times,[0,1e-5]);
  assert.deepEqual(probe.values.ux,[[2,0],[102,100]]);
  assert.deepEqual(probe.values.vm,[[5,3],[105,103]]);
  await assert.rejects(blast3d.readProbe(runId,'3'),/测点节点编号无效/);
  await assert.rejects(blast3d.readProbe(runId,''),/测点节点编号无效/);
});
