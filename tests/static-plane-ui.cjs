const {spawn}=require('node:child_process'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'C:/Users/hongm/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..');
(async()=>{const server=spawn(process.execPath,['server.js'],{cwd:root,env:{...process.env,PORT:'0',FEM_OPEN_BROWSER:'0'},windowsHide:true});let browser;
try{
 const url=await new Promise((resolve,reject)=>{let output='';server.stdout.on('data',b=>{output+=b.toString();const url=output.match(/http:\/\/127\.0\.0\.1:\d+\//);if(url)resolve(url[0]);});server.once('error',reject);server.once('exit',code=>reject(Error(`server exited ${code}`)));});
 browser=await chromium.launch({channel:'msedge',headless:true});const page=await browser.newPage({viewport:{width:1500,height:1050}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(url);await page.waitForFunction(()=>window.femSketchApi);
 await page.evaluate(()=>setPage('calculation'));assert.equal(await page.inputValue('#staticPlaneMode'),'0');
 await page.selectOption('#staticPlaneMode','1');assert.equal(await page.evaluate(()=>scene.staticPlaneMode),1);
 const roundtrip=await page.evaluate(()=>({saved:JSON.parse(JSON.stringify(scene)).staticPlaneMode,restored:normalizeScene(JSON.parse(JSON.stringify(scene))).staticPlaneMode,legacy:normalizeScene({}).staticPlaneMode}));assert.deepEqual(roundtrip,{saved:1,restored:1,legacy:0});
 await page.evaluate(()=>undoDrawing());assert.equal(await page.inputValue('#staticPlaneMode'),'0');
 await page.selectOption('#staticPlaneMode','1');await page.evaluate(()=>clearScene());assert.equal(await page.inputValue('#staticPlaneMode'),'0');
 await page.evaluate(()=>{scene=normalizeScene({...scene,staticPlaneMode:1});updatePanel();});assert.equal(await page.inputValue('#staticPlaneMode'),'1');
 await page.screenshot({path:path.join(root,'tmp/static-plane-ui.png')});assert.deepEqual(errors,[]);console.log(JSON.stringify({ok:true,selection:true,roundtrip:true,legacy:true,undo:true,clear:true,restore:true,pageErrors:errors}));
}finally{if(browser)await browser.close();server.kill();}})().catch(e=>{console.error(e);process.exitCode=1;});
