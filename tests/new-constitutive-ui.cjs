// Browser regression: material writes are intercepted, preserving the user's library.
const {spawn}=require('node:child_process'),assert=require('node:assert/strict'),path=require('node:path'),fs=require('node:fs');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'C:/Users/hongm/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..');
(async()=>{
 const server=spawn(process.execPath,['server.js'],{cwd:root,env:{...process.env,PORT:'5301',FEM_OPEN_BROWSER:'0'},windowsHide:true});let browser;
 try{
  await new Promise((resolve,reject)=>{server.stdout.on('data',b=>{if(b.toString().includes('5301'))resolve();});server.once('error',reject);server.once('exit',code=>reject(Error('Server exit '+code)));});
  browser=await chromium.launch({channel:'msedge',headless:true});const page=await browser.newPage({viewport:{width:1600,height:1100}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  let saved;await page.route('**/api/materials',async route=>{if(route.request().method()!=='POST')return route.continue();saved=route.request().postDataJSON();return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(saved)});});
  await page.goto('http://127.0.0.1:5301/');await page.waitForFunction(()=>window.femSketchApi&&typeof materialLibrary!=='undefined');
  const data=require('./helpers/cavity-scene').cavityScene();
  await page.evaluate(data=>{setBlastModuleEnabled(true,false);scene=normalizeScene(data);modelName.value=scene.name;rebuildDerivedRegions({markAnalysisNodePlacementStale:false,markAnalysisMeshStale:false});restoreBlastControls();setPage('blast');},data);
  const options=await page.evaluate(()=>Object.fromEntries(['blastProductEOS','blastAirEOS','blastRockModel'].map(id=>[id,Array.from(document.getElementById(id).options,o=>[o.value,o.textContent])])));
  assert.deepEqual(options.blastProductEOS.map(o=>o[0]),['1','0','3','4']);assert.deepEqual(options.blastAirEOS.map(o=>o[0]),['0','3','4']);assert.deepEqual(options.blastRockModel.map(o=>o[0]),['1','3','6']);
  for(const values of Object.values(options))for(const [,label]of values)assert.doesNotMatch(label,/上游|直接调用/);
  async function select(id,value){await page.selectOption(id,value);if(await page.locator('#blastCompatibilityDialog').evaluate(d=>d.open))await page.click('#blastCompatibilityClose');}
  await select('#blastSourceMode','1');await select('#blastPlaneMode','1');await select('#blastProductEOS','3');await select('#blastAirEOS','4');
  assert.ok(await page.locator('[data-gas-extra="product.Covolume"]').isVisible());assert.equal(await page.locator('[data-gas-extra="product.PressureOffset"]').isVisible(),false);assert.ok(await page.locator('[data-gas-extra="air.PressureOffset"]').isVisible());
  await page.fill('#blastProductCovolume','0.0001');await page.fill('#blastProductEnergyShift','0.01');await page.fill('#blastAirPressureOffset','0.02');await page.fill('#blastAirEnergyShift','0.001');
  await select('#blastRockModel','6');await select('[data-rock-law][data-rock-material="test-rock"]','6');
  const card={friction:30,dilation:5,cohesion:5,tension:1,softening:1,residualFriction:25,residualDilation:2,residualCohesion:2,peakStrain:.001,residualStrain:.02};
  for(const [key,v]of Object.entries(card))await page.locator(`[data-rock-field="mc.${key}"]`).fill(String(v));
  await page.click('#saveBlastRockCards');await page.waitForFunction(()=>document.getElementById('blastRockStatus').textContent==='本构参数已保存。');
  const material=saved.materials.find(m=>m.id==='test-rock');assert.equal(material.blastConstitutive.law,6);assert.equal(material.blastConstitutive.mc.cohesion,5e6);assert.equal(material.blastConstitutive.mc.residualCohesion,2e6);
  const restored=await page.evaluate(()=>{const first=readBlastControls();scene.blastSettings=first;restoreBlastControls();return {first,next:readBlastControls(),card:normalizeScene(structuredClone(scene)).regions.find(r=>r.material)?.material.blastConstitutive};});
  assert.deepEqual(restored.first,restored.next);assert.equal(restored.first.airPressureOffset,20000);assert.equal(restored.first.productEnergyShift,10000);assert.equal(restored.first.airEnergyShift,1000);assert.equal(restored.card.law,6);
  assert.doesNotMatch(await page.locator('#blastProductEOSHelp,#blastAirEOSHelp,#blastRockHelp').allTextContents().then(x=>x.join(' ')),/上游|直接调用/);
  assert.deepEqual(errors,[]);
  fs.mkdirSync(path.join(root,'output'),{recursive:true});await page.locator('.blast-rock-card').screenshot({path:path.join(root,'output/new-constitutive-ui.png')});
  console.log(JSON.stringify({ok:true,options,materialCardSaved:true,SIUnits:true,modelRoundTrip:true,pageErrors:errors}));
 }finally{await browser?.close();server.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
