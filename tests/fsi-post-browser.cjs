'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {spawn}=require('node:child_process');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'C:/Users/hongm/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=process.env.TENSORA_TEST_ROOT||path.resolve(__dirname,'..');
fs.mkdirSync(path.join(root,'tmp'),{recursive:true});
const nodes2=[[0,0],[2,0],[2,1],[0,1],[0,-.1],[2,-.1]];
const model2={nodes:nodes2,cells:[[0,1,2],[0,2,3],[0,4,5],[0,5,1]],cellRoles:['fluid','fluid','solid','solid']};
const nodes3=[[0,0,0],[1,0,0],[0,1,0],[0,0,1],[0,0,-1]];
const tets=[[0,1,2,3],[0,1,2,4]];
const mesh={nodes:nodes3,tets,tetVolumes:['1','2'],volumes:[{id:'1',centroid:[.25,.25,.25]},{id:'2',centroid:[.25,.25,-.25]}],
  surfaces:[[1,2,3],[0,2,3],[0,1,3],[1,2,4],[0,2,4],[0,1,4],[0,1,2]].map((tri,i)=>({
    id:String(i+1),volumeId:i<3||i===6?'1':'2',triangles:[tri],...(i===6?{neighborVolumeId:'2'}:{})
  }))};
const summary=(dim,n)=>({ok:true,runId:'run-ui'+dim,dimension:dim,nodeCount:n,engine:'oneway',solver:'SU2 + MFEM',elapsedMs:1000,
  settings:{analysis:'transient',timeStep:.1,steps:2,volumeRoles:{1:'fluid',2:'solid'}},
  fields:['vx','vy',...(dim===3?['vz']:[]),'vmag','pressure','ux','uy','umag','flowUx','flowUy'],
  meta:{fluid:{name:'Water'},fluidCells:2,solidCells:1,interfaceFaces:1,materials:[]},history:[],
  frames:[1,2].map((speed,i)=>({time:i*.1,stats:{vmag:[speed,speed],pressure:[0,dim===2?2:1],umag:[0,.001]}}))});
const data=(run,nodes,speed)=>Buffer.from(Float32Array.from(run.fields.flatMap(key=>nodes.map(([x])=>
  (key==='vx'||key==='vmag')?speed:key==='pressure'?x:0))).buffer);
(async()=>{
  let browser;
  const server=spawn(process.env.TENSORA_TEST_NODE||process.execPath,['server.js'],{cwd:root,env:{...process.env,PORT:'0',FEM_OPEN_BROWSER:'0'},windowsHide:true});
  try{
    const url=await new Promise((resolve,reject)=>{
      server.stdout.on('data',b=>{const found=b.toString().match(/http:\/\/127\.0\.0\.1:\d+\//);if(found)resolve(found[0]);});
      server.once('exit',reject);
    });
    browser=await chromium.launch({executablePath:process.env.TENSORA_TEST_BROWSER||path.join(root,'browser/chrome-win64/chrome.exe'),headless:true,
      args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
    const page=await browser.newPage({viewport:{width:1500,height:950}}),errors=[];
    page.on('pageerror',error=>errors.push(error.stack));
    page.on('console',msg=>{if(msg.type()==='error'&&msg.text().includes('THREE.WebGLProgram'))errors.push(msg.text());});
    const run2=summary(2,nodes2.length),run3=summary(3,nodes3.length);
    for(const [run,nodes] of [[run2,nodes2],[run3,nodes3]]){
      await page.route('**/api/fsi-runs/'+run.runId+'/frames/*',route=>route.fulfill({
        contentType:'application/octet-stream',body:data(run,nodes,Number(route.request().url().at(-1))+1)
      }));
    }
    await page.route('**/api/fsi-runs',route=>route.fulfill({contentType:'application/x-ndjson',body:JSON.stringify({type:'result',result:run3})+'\n'}));
    await page.route('**/api/drawing-recovery',route=>route.fulfill({json:{}}));
    await page.route('**/api/fluids',route=>route.fulfill({json:{fluids:[{id:'water',name:'Water',model:'incompressible',density:1000,viscosity:.001}]}}));
    await page.goto(url);
    await page.locator('#professionalMenu summary').click();
    await page.check('#enableFsiModule');
    await page.locator('#professionalMenu summary').click();
    await page.evaluate(async({run,model})=>{await setFsiResult(run,{model});setPage('fsi-results');},{run:run2,model:model2});
    assert.equal(await page.locator('#fsiScale').inputValue(),'1');
    await page.locator('#fsiStreamlines').check();
    await page.waitForFunction(()=>document.getElementById('fsiStreamStatus').textContent.includes('32 条当前帧流线 · 结构附近'));
    await page.click('#fsiFocusSolid');
    await page.click('#fsiFit');
    await page.selectOption('#fsiSeedMode','plane');
    await page.waitForFunction(()=>document.getElementById('fsiStreamStatus').textContent.includes('16 条'));
    await page.selectOption('#fsiField','pressure');
    await page.click('#fsiPickProfile');
    const canvas=page.locator('#fsiCanvas');
    const rect=await canvas.boundingBox();
    await canvas.click({position:{x:rect.width*.35,y:rect.height*.45}});
    await canvas.click({position:{x:rect.width*.65,y:rect.height*.45}});
    assert.equal(await page.locator('#fsiProfileCanvas').isVisible(),true);
    assert.equal(await page.locator('#fsiExportProfile').isEnabled(),true);
    const csv=await page.evaluate(async()=>{
      window.chooseExportFile=async()=>({});
      window.writeExportFile=async(handle,write)=>{await write({write:chunk=>{window.profileCsv=chunk;}});};
      await exportFsiProfile();
      return window.profileCsv;
    });
    assert.match(csv,/流体压力 p \(Pa\)/);
    assert.equal(csv.trim().split('\r\n').length,202);
    await page.locator('#fsiPathlines').check();
    await page.waitForFunction(()=>document.getElementById('fsiPathStatus').textContent.includes('条路径线'));
    const video=await page.evaluate(async()=>{
      const chunks=[];
      window.writeExportFile=async(handle,write)=>{await write({write:chunk=>{chunks.push(chunk);}});};
      await exportFsiVideo();
      const blob=new Blob(chunks,{type:'video/webm'}),video=document.createElement('video');
      video.src=URL.createObjectURL(blob);
      await new Promise((resolve,reject)=>{video.onloadeddata=resolve;video.onerror=reject;});
      return {size:blob.size,width:video.videoWidth,duration:video.duration};
    });
    assert.ok(video.size>1000&&video.width>0&&Math.abs(video.duration-.2)<.005,JSON.stringify(video));
    await page.evaluate(()=>{
      window.vtkChunks=[];
      window.writeExportFile=async(handle,write)=>{await write({write:chunk=>{window.vtkChunks.push(chunk);}});};
    });
    await page.click('#fsiExportVtk');
    await page.waitForFunction(()=>document.getElementById('fsiResultStatus').textContent.includes('fsi.pvd'));
    const zip=await page.evaluate(async()=>new TextDecoder().decode(await new Blob(window.vtkChunks).arrayBuffer()));
    assert.ok(zip.startsWith('PK')&&zip.includes('fsi.pvd')&&zip.includes('frames/structure-0001.vtu'));
    await page.locator('#fsiFrame').press('Home');
    await page.waitForFunction(()=>document.getElementById('fsiStreamStatus').textContent.endsWith('1 m/s'));
    await page.screenshot({path:path.join(root,'tmp','fsi-post-2d.png'),fullPage:true});
    await page.selectOption('#fsiZoneFilter','solid');
    assert.equal(await page.locator('#fsiStreamlines').isDisabled(),true);
    console.log('2D layers, profile, CSV and frame updates passed');

    await page.locator('#professionalMenu summary').click();
    await page.check('#enableSolid3dModule');
    await page.locator('#professionalMenu summary').click();
    await page.evaluate(()=>setPage('home'));
    const project={kind:'tensora-solid3d',version:1,shapes:[],mesh,conditions:[{type:'fixed',surfaceId:'4'}],volumeMaterials:{2:'mat-q235-steel'},
      fsi3d:{roles:{1:'fluid',2:'solid'},faces:{1:{kind:'farfield',velocity:.0001,direction:[1,0,0]}}}};
    await page.locator('#solid3dLoadModel').setInputFiles({name:'channel.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(project))});
    await page.waitForFunction(()=>document.getElementById('solid3dStatus').textContent.includes('模型已导入'),null,{timeout:3500}).catch(async error=>{
      console.log(await page.locator('#solid3dStatus').textContent(),errors);throw error;
    });
    await page.evaluate(()=>setPage('fsi'));
    await page.waitForFunction(()=>document.getElementById('solid3dFsiFluid').options.length>0).catch(async error=>{
      console.log(await page.locator('#solid3dHeading').innerText(),errors);
      throw error;
    });
    // Dispatch into the normal FSI result response path with the controlled fixture.
    await page.evaluate(()=>{document.getElementById('solid3dFsiScale').value='14';});
    await page.locator('#solid3dRunFsi').click();
    if(await page.locator('.preflight-proceed').isVisible())await page.locator('.preflight-proceed').click();
    await page.locator('#solid3dFsiStreamlines').waitFor({state:'visible',timeout:4000}).catch(async error=>{
      console.log(await page.locator('#solid3dStatus').textContent(),await page.locator('#solid3dFsiPreflight').innerText(),errors);throw error;
    });
    await page.locator('#solid3dFsiStreamlines').check();
    assert.equal(await page.locator('#solid3dFsiScale').inputValue(),'1');
    await page.waitForFunction(()=>document.getElementById('solid3dFsiStreamStatus').textContent.includes('64 条当前帧流线 · 结构附近'));
    await page.click('#solid3dFsiFocusSolid');
    await page.locator('#solid3dFsiFrame').press('Home');
    await page.waitForFunction(()=>document.getElementById('solid3dFsiStreamStatus').textContent.endsWith('1 m/s'));
    await page.locator('#solid3dFsiPathlines').check();
    await page.waitForFunction(()=>document.getElementById('solid3dFsiPathStatus').textContent.includes('条路径线'));
    await page.selectOption('#solid3dFsiVolumeMode','iso');
    await page.selectOption('#solid3dFsiVolumeField','pressure');
    await page.waitForFunction(()=>document.getElementById('solid3dFsiVolumeStatus').textContent.includes('1 个三角面'));
    await page.selectOption('#solid3dFsiVolumeMode','volume');
    await page.waitForFunction(()=>document.getElementById('solid3dFsiVolumeStatus').textContent.includes('采样网格'));
    await page.screenshot({path:path.join(root,'tmp','fsi-post-volume.png'),fullPage:true});
    await page.selectOption('#solid3dFsiVolumeMode','none');
    await page.locator('#solid3dFsiLineProfile summary').click();
    const lineCoords={AX:.1,AY:.1,AZ:.1,BX:.7,BY:.1,BZ:.1};
    for(const [key,value] of Object.entries(lineCoords))await page.fill('#solid3dFsiLine'+key,String(value));
    await page.click('#solid3dFsiApplyLine');
    await page.waitForFunction(()=>document.getElementById('solid3dFsiLineStatus').textContent.includes('长度 0.6 m'));
    await page.locator('#solid3dAddSection').click();
    await page.selectOption('#solid3dSectionPlane','YZ');
    await page.fill('#solid3dSectionX','0.5');
    await page.locator('#solid3dSectionX').press('Tab');
    assert.match(await page.locator('#solid3dFsiSectionMetrics').innerText(),/0\.125 m²[\s\S]+0\.125 m³\/s/);
    const sectionCsv=await page.evaluate(async()=>{
      window.writeExportFile=async(handle,write)=>{await write({write:chunk=>{window.sectionCsv=chunk;}});};
      document.getElementById('solid3dFsiExportSections').click();
      await new Promise(resolve=>setTimeout(resolve,0));
      return window.sectionCsv;
    });
    assert.match(sectionCsv,/体积流量 \(m³\/s\)/);
    await page.screenshot({path:path.join(root,'tmp','fsi-post-3d.png'),fullPage:true});
    await page.evaluate(()=>{
      window.videoBytes=0;
      window.writeExportFile=async(handle,write)=>{await write({write:chunk=>{window.videoBytes+=chunk.byteLength;}});};
    });
    await page.click('#solid3dFsiExportVideo');
    await page.waitForFunction(()=>document.getElementById('solid3dStatus').textContent.includes('已导出 WebM'));
    assert.ok(await page.evaluate(()=>window.videoBytes>1000));
    await page.locator('#solid3dTree input').first().uncheck();
    await page.waitForFunction(()=>document.getElementById('solid3dFsiStreamStatus').textContent.includes('没有可见流体'));
    assert.equal(await page.locator('#solid3dFsiSectionMetrics').isVisible(),false);
    assert.deepEqual(errors,[]);
    console.log('3D workers, isosurface, volume rendering, line profile, section flow, filters and WebM passed');
  }finally{await browser?.close();server.kill();}
})().catch(error=>{console.error(error);process.exitCode=1;});
