'use strict';

const assert = require('node:assert/strict');
const {spawn, execFileSync} = require('node:child_process');
const {once} = require('node:events');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const {setTimeout:delay} = require('node:timers/promises');
const test = require('node:test');
const root = path.resolve(__dirname,'..');

// Exercise the headless EXE with its own installation identity, model history,
// material library and browser profile. Only read-only runtimes are shared.
test('headless HTTP solver and on-demand workspaces work without desktop windows', {
  skip:process.platform!=='win32', timeout:200000
}, async () => {
  const {chromium} = require(process.env.PLAYWRIGHT_MODULE ||
    'C:/Users/hongm/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
  const dir = await fs.mkdtemp(path.join(os.tmpdir(),'tensora-control-'));
  const exe = path.join(dir,'TENSORA.exe');
  let app, closed, browser, state;
  try {
    const files = (await fs.readdir(root)).filter(name=>name.endsWith('.js'));
    for (const name of [...files,'index.html','styles.css','TENSORA.exe'])
      await fs.copyFile(path.join(root,name),path.join(dir,name));
    for (const name of ['materials','fluids','gases','explosives'])
      await fs.cp(path.join(root,name),path.join(dir,name),{recursive:true});
    for (const name of ['assets','src','browser','third_party','node-v24.21.0-win-x64'])
      await fs.symlink(path.join(root,name),path.join(dir,name),'junction');
    await fs.cp(path.join(root,'TensoraCore/x64/Release'),path.join(dir,'TensoraCore/x64/Release'),{recursive:true});

    const report = path.join(dir,'diagnose.json');
    execFileSync(exe,['--diagnose',report],{windowsHide:true,timeout:10000});
    const diagnosis = JSON.parse((await fs.readFile(report,'utf8')).replace(/^\uFEFF/,''));
    assert.equal(path.resolve(diagnosis.root),dir);
    state = diagnosis.state;
    app = spawn(exe,['--headless'],{cwd:dir,windowsHide:true,stdio:'ignore'});
    closed = once(app,'exit');
    let info;
    const deadline = Date.now()+90000;
    while (Date.now()<deadline && app.exitCode===null) {
      try {
        const port = Number(await fs.readFile(path.join(state,'Headless','port.txt'),'utf8'));
        const response = await fetch(`http://127.0.0.1:${port}/api/automation`,{signal:AbortSignal.timeout(3000)});
        if (response.ok) { info=await response.json(); break; }
      } catch { /* GUI and service start asynchronously. */ }
      await delay(200);
    }
    assert.ok(info?.ready,await fs.readFile(path.join(state,'Headless','launcher.log'),'utf8').catch(()=> 'No launcher log'));
    const cli = JSON.parse(execFileSync(process.execPath,[path.join(dir,'automation-api.js')],{encoding:'utf8',timeout:6000}));
    assert.equal(cli.serviceUrl,info.serviceUrl);
    assert.equal(cli.headless,true);
    assert.equal(cli.engineRunning,false);
    execFileSync(exe,['--headless'],{windowsHide:true,timeout:10000});
    const endpoint = new URL('/api/automation',info.serviceUrl);
    const blocked = await fetch(endpoint,{headers:{Origin:'https://other.invalid'}});
    assert.equal(blocked.status,403);
    assert.equal(blocked.headers.has('access-control-allow-origin'),false);
    assert.equal((await fetch(new URL('/api/materials',cli.serviceUrl),{headers:{Origin:'https://other.invalid'}})).status,403);
    assert.equal((await fetch(endpoint,{method:'POST'})).status,405);

    // Native clients can solve and fetch results before any browser exists.
    const routes=Object.fromEntries(cli.operations.map(op=>[op.name,op.path]));
    async function post(name,payload){
      const response=await fetch(new URL(routes[name],cli.serviceUrl),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
      const data=await response.json();
      assert.equal(response.status,200,data.error);
      return data;
    }
    const shape={shapes:[{type:'box',dx:1,dy:.2,dz:.2}],meshSize:.14};
    const cad=(await post('solidPreview',shape)).data;
    assert.equal(cad.surfaces.length,6);
    const grid=(await post('solidMesh',shape)).data;
    const faceAt=x=>grid.surfaces.find(s=>s.triangles.every(tri=>tri.every(i=>Math.abs(grid.nodes[i][0]-x)<1e-8))).id;
    const bar=(await post('static3d',{mesh:grid,settings:{young:2e11,poisson:.3,computeBackend:'cpu',
      conditions:[{type:'fixed',surface:faceAt(0)},{type:'force',surface:faceAt(1),fx:1000,fy:0,fz:0}]}})).data;
    assert.ok(Math.abs(bar.maxDisplacement/(1000/(2e11*.2*.2))-1)<.1);
    const model=require('./helpers/dynamics-models').planeModel([{n:[12,2],size:[1,.1]}],
      {id:'steel',name:'steel',E:210e9,nu:.3,rho:7850});
    for(const node of model.nodes)if(node.x===0)node.fixUx=node.fixUy=true;
    const result=await post('dynamics',{model,settings:{analysis:'modal',modes:2}});
    assert.equal(result.completed,true,result.error);
    assert.ok(Math.abs(result.modes[0].frequency-83.5)<3);
    const probe=await (await fetch(new URL(`/api/dynamics-runs/${result.runId}/probe?nodes=0`,cli.serviceUrl))).json();
    assert.equal(probe.values.ux.length,2);
    assert.equal((await (await fetch(endpoint)).json()).engineRunning,false);
    const sessionUrl=new URL(routes.headlessSession,cli.serviceUrl);
    const sessions=await Promise.all([1,2].map(async()=>await (await fetch(sessionUrl,{method:'POST'})).json()));
    const active=sessions[0];
    assert.ok(active.ready,JSON.stringify(active));
    assert.equal(active.browserWebSocketUrl,sessions[1].browserWebSocketUrl);
    browser = await chromium.connectOverCDP(active.browserWebSocketUrl);
    const browserSession=await browser.newBrowserCDPSession();
    const processes=await browserSession.send('SystemInfo.getProcessInfo');
    const pids=[app.pid,...processes.processInfo.map(p=>p.id)].filter(p=>Number.isInteger(p)&&p>0);
    const windows=execFileSync('powershell.exe',['-NoProfile','-Command',
      `@(Get-Process -Id ${pids.join(',')} -ErrorAction SilentlyContinue | Where-Object MainWindowHandle -ne 0).Count`],{windowsHide:true,encoding:'utf8'});
    assert.equal(Number(windows.trim()),0);
    const page = browser.contexts().flatMap(context=>context.pages()).find(p=>p.url()===active.pages[0].url);
    assert.ok(page);
    await page.setViewportSize({width:1600,height:1000});
    const session = await page.context().newCDPSession(page);
    assert.equal((await session.send('Target.getTargetInfo')).targetInfo.targetId,active.pages[0].id);
    const errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    await page.waitForFunction(()=>Boolean(window.femSketchApi && window.tensoraSolid3d));
    await page.locator('#professionalMenu summary').click();
    for (const id of ['enableDynamicsModule','enableDeformationModule','enableFsiModule','enableBlastModule'])
      await page.check('#'+id);
    await page.locator('#professionalMenu summary').click();
    const tabs = await page.locator('[data-page-tab]:visible').evaluateAll(elements=>elements.map(el=>el.dataset.pageTab));
    assert.equal(tabs.length,16);
    for (const tab of tabs) {
      await page.locator(`[data-page-tab="${tab}"]`).click();
      assert.equal(await page.evaluate(()=>currentPageKey()),tab);
    }
    await page.locator('[data-page-tab="home"]').click();
    const beam = require('../examples/classic-models/models-2d.cjs').cantileverHarmonic();
    await page.locator('#fileInput').setInputFiles({name:'control-test.json',mimeType:'application/json',
      buffer:Buffer.from(JSON.stringify(beam.scene))});
    await page.waitForFunction(name=>femSketchApi.getScene().name===name,beam.scene.name);
    await page.locator('[data-page-tab="calculation"]').click();
    await page.fill('#maxAnalysisNodes','100');
    await page.click('#calculationAutoMesh');
    await page.waitForFunction(()=>femSketchApi.getScene().mesh?.elements?.length>0);
    const staticMax = await page.evaluate(async()=>{
      const outcome=await femSketchApi.startCalculationWorkflow({adaptive:false,useGpuAcceleration:false});
      if (!outcome?.runResult?.ok) throw Error('Static solve failed');
      return calculationResultData.maxDisplacement;
    });
    assert.ok(staticMax>0);
    await page.locator('[data-page-tab="dynamics"]').click();
    await page.fill('#dynModes','3');
    await page.locator('#startDynamics').press('Enter');
    const proceed=page.locator('#preflightDialog[open] .preflight-proceed');
    if(await proceed.isVisible())await proceed.click();
    await page.locator('[data-page="dynamics-results"]:visible').waitFor();
    assert.equal(await page.locator('#dynModeTable tbody tr').count(),3);
    await page.locator('#dynModeTable tbody tr').nth(1).click();
    await page.waitForFunction(()=>document.querySelector('#dynFrame').value==='1');

    await page.locator('#professionalMenu summary').click();
    await page.check('#enableSolid3dModule');
    await page.locator('[data-page-tab="home"]').click();
    await page.click('#solid3dAddBox');
    await page.locator('[data-page-tab="calculation"]').click();
    await page.click('#solid3dMesh');
    await page.waitForFunction(()=>window.tensoraSolid3d.snapshot({compact:true}).mesh?.tets?.length>0);
    assert.deepEqual(errors,[]);
    execFileSync(exe,['--stop-headless'],{windowsHide:true,timeout:15000});
    await Promise.race([closed,delay(12000,undefined,{ref:false}).then(()=>{throw Error('Headless service stayed open');})]);
    assert.equal(app.exitCode,0);
    await assert.rejects(fetch(endpoint));
    await assert.rejects(fetch(active.browserUrl+'/json/version'));
  } finally {
    if(app && app.exitCode===null){app.kill();await closed;}
    await browser?.close().catch(()=>{});
    if(state)await fs.rm(state,{recursive:true,force:true,maxRetries:5});
    await fs.rm(dir,{recursive:true,force:true,maxRetries:5});
  }
});
