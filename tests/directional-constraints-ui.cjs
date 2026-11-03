const {spawn}=require('node:child_process'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'C:/Users/hongm/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..');
(async()=>{const server=spawn(process.execPath,['server.js'],{cwd:root,env:{...process.env,PORT:'5297',FEM_OPEN_BROWSER:'0'},windowsHide:true});let browser;
try{
 await new Promise((resolve,reject)=>{server.stdout.on('data',b=>{if(b.toString().includes('5297'))resolve();});server.once('error',reject);server.once('exit',code=>reject(Error(`server exited ${code}`)));});
 browser=await chromium.launch({channel:'msedge',headless:true});const page=await browser.newPage({viewport:{width:1500,height:1050}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:5297/');await page.waitForFunction(()=>window.femSketchApi);
 await page.evaluate(()=>{scene=normalizeScene({geometryNodes:[{id:'G1',x:0,y:0},{id:'G2',x:2,y:0}],curves:[{id:'C1',type:'line',geometryNodeIds:['G1','G2']}]});selectObject('curve','C1');updatePanel();render();});
 for(const state of ['static','static-x','static-y','free']){
   await page.click(`[data-geometry-state="${state}"]`);
   assert.equal(await page.evaluate(()=>scene.curves[0].mechanicalState),state);
   assert.equal(await page.evaluate(()=>getGeometryStateAtPoint({x:1,y:0}).mechanicalState),state);
   assert.equal(await page.locator(`[data-geometry-state="${state}"]`).getAttribute('class').then(c=>c.includes('active')),true);
 }
 await page.click('[data-geometry-state="static-x"]');
 await page.evaluate(()=>{undoDrawing();selectObject('curve','C1');updatePanel();});
 assert.equal(await page.evaluate(()=>scene.curves[0].mechanicalState),'free');
 await page.click('[data-geometry-state="static-y"]');
 await page.evaluate(()=>{scene=normalizeScene(JSON.parse(JSON.stringify(scene)));selectObject('curve','C1');updatePanel();render();});
 assert.equal(await page.evaluate(()=>scene.curves[0].mechanicalState),'static-y');
 await page.screenshot({path:path.join(root,'tmp/directional-constraints-ui.png')});
 assert.deepEqual(errors,[]);console.log(JSON.stringify({ok:true,fourOptions:true,curveInheritance:true,undo:true,roundtrip:true,pageErrors:errors}));
}finally{if(browser)await browser.close();server.kill();}})().catch(e=>{console.error(e);process.exitCode=1;});
