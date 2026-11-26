'use strict';
const assert=require('node:assert/strict');
const {spawn,execFileSync}=require('node:child_process');
const fs=require('node:fs/promises');
const os=require('node:os');
const path=require('node:path');
const test=require('node:test');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'C:/Users/hongm/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..');

test('2D and 3D cantilevers through import, preflight, result tables, probes and animation', {timeout:150000},async t=>{
  const work=await fs.mkdtemp(path.join(os.tmpdir(),'tensora-dynamics-browser-'));
  t.after(()=>fs.rm(work,{recursive:true,force:true,maxRetries:3}));
  execFileSync(process.execPath,['examples/classic-models/build-3d.cjs',work,'plateModal3d','plateHarmonic3d'],{cwd:root,windowsHide:true});
  const files=await fs.readdir(work);
  const server=spawn(process.execPath,['server.js'],{cwd:root,windowsHide:true,
    env:{...process.env,PORT:'0',FEM_OPEN_BROWSER:'0',TENSORA_DYNAMICS_RUNS_DIR:path.join(work,'runs')}});
  const closed=new Promise(resolve=>server.once('close',resolve));
  let browser;
  try{
    const url=await new Promise((resolve,reject)=>{
      let log='';
      server.stdout.on('data',chunk=>{log+=chunk;const match=log.match(/http:\/\/127\.0\.0\.1:\d+\//);if(match)resolve(match[0]);});
      server.once('error',reject);server.once('exit',code=>reject(Error('server exit '+code)));
    });
    browser=await chromium.launch({...(process.env.TENSORA_TEST_BROWSER?{executablePath:process.env.TENSORA_TEST_BROWSER}:{channel:'msedge'}),
      headless:true,args:['--use-gl=angle','--use-angle=swiftshader']});
    const page=await browser.newPage({viewport:{width:1500,height:1000}});
    const errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto(url);
    await page.locator('#professionalMenu summary').click();
    await page.check('#enableDynamicsModule');
    await page.click('[data-page-tab="home"]');
    const beam=require('../examples/classic-models/models-2d.cjs').cantileverModal();
    await page.locator('#fileInput').setInputFiles({name:'beam.json',mimeType:'application/json',
      buffer:Buffer.from(JSON.stringify({...beam.scene,dynamicsSettings:beam.dynamicsSettings}))});
    await page.waitForFunction(name=>window.femSketchApi.getScene().name===name,beam.scene.name);
    await page.click('[data-page-tab="calculation"]');
    await page.click('#calculationAutoMesh');
    await page.waitForFunction(()=>scene.mesh?.elements?.length>0);
    await page.click('[data-page-tab="dynamics"]');
    await page.fill('#dynModes','3');
    await page.click('#startDynamics');
    const preflight=page.locator('#preflightDialog[open]');
    if(await preflight.isVisible())await preflight.locator('.preflight-proceed').click();
    await page.locator('[data-page="dynamics-results"]:visible').waitFor();
    assert.equal(await page.locator('#dynModeTable tbody tr').count(),3);
    await page.selectOption('#dynField','sxx');
    const point=await page.evaluate(()=>{const p=dynamicsCamera.project(dynamicsCamera.coords[0]);return {x:p[0],y:p[1]};});
    await page.locator('#dynCanvas').click({position:point});
    await page.locator('#dynProbeCanvas:visible').waitFor();
    await page.evaluate(()=>{window.showSaveFilePicker=async()=>({createWritable:async()=>({
      write(text){window.probeCsv=text;},close(){},abort(){}
    })});});
    await page.click('#dynExportCurve');
    await page.waitForFunction(()=>Boolean(window.probeCsv));
    const probeCsv=(await page.evaluate(()=>window.probeCsv)).split('# ').at(-1);
    assert.match(probeCsv,/\(Pa\)\n1,/);
    assert.match(probeCsv,/\n2,.*\n3,/);
    if(!await page.locator('#professionalMenu').evaluate(el=>el.open))await page.locator('#professionalMenu summary').click();
    await page.check('#enableSolid3dModule');
    for(const analysis of ['modal','harmonic']){
      await page.click('[data-page-tab="home"]');
      const name=files.find(file=>file.includes(analysis==='modal'?'模态':'谐响应'));
      await page.locator('#solid3dLoadModel').setInputFiles(path.join(work,name));
      await page.waitForFunction(expected=>window.tensoraSolid3d?.snapshot({compact:true}).dynamics3d.form.solid3dDynAnalysis===expected&&
        document.querySelector('#solid3dStatus').textContent.includes('已导入'),analysis);
      await page.click('[data-page-tab="dynamics"]');
      if(analysis==='modal')await page.fill('#solid3dDynModes','3');
      await page.click('#solid3dRunDynamics');
      const dialog=page.locator('#preflightDialog[open]');
      if(await dialog.isVisible())await dialog.locator('.preflight-proceed').click();
      await page.locator('[data-solid3d-stage="dynamics-results"]:visible').first().waitFor({timeout:45000});
      const rows=page.locator('#solid3dDynModeTable tbody tr');
      assert.ok(await rows.count()>0);
      if(analysis==='modal'){
        assert.equal(await rows.count(),3);
        const first=Number(await rows.first().locator('td').nth(1).innerText());
        assert.ok(first>99&&first<106,'first plate frequency '+first);
        await rows.nth(1).click();
        await page.waitForFunction(()=>document.querySelector('#solid3dDynFrame').value==='1');
        assert.equal(await rows.nth(1).getAttribute('class'),'active');
      }else{
        await page.selectOption('#solid3dDisplay','phz');
        await page.evaluate(()=>{
          const apply=DynamicsUI.harmonicDisplacement;
          DynamicsUI.harmonicDisplacement=(amplitude,degrees,angle)=>{
            if(amplitude>0&&Math.abs(degrees)>1)window.animatedWithPhase=true;
            return apply(amplitude,degrees,angle);
          };
        });
        await page.click('#solid3dPlayDynamics');
        await page.waitForFunction(()=>document.querySelector('#solid3dPlayDynamics').textContent==='暂停');
        await page.waitForFunction(()=>window.animatedWithPhase);
        await page.click('#solid3dPlayDynamics');
        assert.equal(await page.locator('#solid3dPlayDynamics').innerText(),'振型动画');
      }
    }
    assert.deepEqual(errors,[]);
  }finally{
    await browser?.close();
    server.kill();await closed;
  }
});
