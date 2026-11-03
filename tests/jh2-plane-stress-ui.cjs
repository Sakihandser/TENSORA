const {spawn}=require('node:child_process'),assert=require('node:assert/strict'),path=require('node:path');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'C:/Users/hongm/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..');
(async()=>{const server=spawn(process.execPath,['server.js'],{cwd:root,env:{...process.env,PORT:'5302',FEM_OPEN_BROWSER:'0'},windowsHide:true});let browser;
try{
 await new Promise((resolve,reject)=>{server.stdout.on('data',b=>{if(b.toString().includes('5302'))resolve();});server.once('error',reject);server.once('exit',code=>reject(Error(`server exited ${code}`)));});
 browser=await chromium.launch({channel:'msedge',headless:true});const page=await browser.newPage({viewport:{width:1500,height:1050}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:5302/');await page.waitForFunction(()=>window.femSketchApi&&typeof materialLibrary!=='undefined');
 const data=require('./helpers/cavity-scene').cavityScene();data.regions[0].material.blastConstitutive=require('./helpers/rock-card').rockCard();
 await page.evaluate(data=>{setBlastModuleEnabled(true,false);scene=normalizeScene(data);modelName.value=scene.name;rebuildDerivedRegions({markAnalysisNodePlacementStale:false,markAnalysisMeshStale:false});restoreBlastControls();setPage('blast');},data);
 await page.selectOption('#blastRockModel','3');await page.selectOption('#blastPlaneMode','0');await page.selectOption('#blastKinematics','1');
 assert.equal(await page.inputValue('#blastPlaneMode'),'0');assert.equal(await page.locator('#startBlast').isEnabled(),true);
 const r=await page.evaluate(()=>{scene.blastSettings=readBlastControls();return {settings:readBlastControls(),report:syncBlastCompatibility(),restored:normalizeScene(JSON.parse(JSON.stringify(scene))).blastSettings};});assert.deepEqual(r.report.errors,[]);assert.equal(r.settings.kinematics,1);assert.equal(r.restored.planeMode,0);assert.equal(r.restored.kinematics,1);
 await page.selectOption('#interfaceLanguage','en');assert.ok((await page.locator('#blastKinematics option:checked').innerText()).includes('Finite deformation'));assert.equal(await page.inputValue('#blastPlaneMode'),'0');
 await page.screenshot({path:path.join(root,'tmp/jh2-plane-stress-ui.png')});assert.deepEqual(errors,[]);console.log(JSON.stringify({ok:true,finitePlaneStress:true,persistence:true,english:true,pageErrors:errors}));
}finally{if(browser)await browser.close();server.kill();}})().catch(e=>{console.error(e);process.exitCode=1;});
