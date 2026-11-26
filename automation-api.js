'use strict';

const fs = require('node:fs/promises');
const path = require('node:path');
const {createHash} = require('node:crypto');
const {spawn} = require('node:child_process');
const {setTimeout:delay} = require('node:timers/promises');

// Match the Windows launcher's per-installation state directory.
const installationId = createHash('sha256').update(__dirname.toUpperCase()).digest('hex').slice(0,20).toUpperCase();
const browserPath = /^\/devtools\/browser\/[0-9a-f-]{36}$/i;
const targetId = /^[0-9a-f]+$/i;
const operations = [
  ['materials','GET','/api/materials'], ['saveMaterials','POST','/api/materials'],
  ['solidPreview','POST','/api/solid3d/preview'], ['solidMesh','POST','/api/solid3d/mesh'],
  ['static2d','POST','/api/calculation-runs'], ['static3d','POST','/api/solid3d/solve'],
  ['deformation','POST','/api/deformation-runs'], ['fsi','POST','/api/fsi-runs'],
  ['dynamics','POST','/api/dynamics-runs'], ['solverStatus','GET','/api/dynamics-status'],
  ['dynamicsSummary','GET','/api/dynamics-runs/{runId}'], ['dynamicsFrame','GET','/api/dynamics-runs/{runId}/frames/{index}'],
  ['dynamicsProbe','GET','/api/dynamics-runs/{runId}/probe?nodes={nodes}'],
  ['headlessSession','POST','/api/automation/session']
].map(([name,method,path])=>({name,method,path}));
let engine=null, starting=null;

async function localJson(url, method='GET') {
  const response = await fetch(url, {method,signal:AbortSignal.timeout(2500), redirect:'error'});
  const data = await response.json();
  if (!response.ok) throw Error(data.message || `HTTP ${response.status}`);
  return data;
}

async function discovery(request, response, pathname) {
  const servicePort = request.socket.localPort;
  const serviceUrl = `http://127.0.0.1:${servicePort}/`;
  const send = (status, data) => {
    response.writeHead(status, {'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});
    response.end(JSON.stringify(data));
  };
  const host = request.headers.host;
  // Session creation discloses a control handle. Only native loopback
  // clients can discover it, independently of CORS on the ordinary solver APIs.
  if (![ `127.0.0.1:${servicePort}`, `localhost:${servicePort}` ].includes(host) ||
      request.headers.origin !== undefined || request.headers['sec-fetch-site'] !== undefined) {
    send(403, {error:'local_client_required'}); return;
  }
  const session=pathname.endsWith('/session'), method=session?'POST':'GET';
  if (request.method !== method) {
    response.setHeader('Allow',method); send(405, {error:'method_not_allowed'}); return;
  }
  const profile=process.env.TENSORA_HEADLESS_PROFILE, binary=process.env.TENSORA_HEADLESS_BROWSER;
  const info = {application:'TENSORA', apiVersion:1, installationId, serviceUrl, headless:Boolean(profile)};
  if (!session) {
    send(200,{...info,ready:true,engineRunning:Boolean(engine),operations}); return;
  }
  if (!profile || !binary) {
    send(503,{...info,ready:false,error:'headless_engine_unavailable',message:'完整工作区会话需要后台启动器和 Chromium 运行时。'}); return;
  }
  try {
    starting ??= openSession(profile,binary,serviceUrl).finally(()=>{starting=null;});
    send(200,{...info,ready:true,protocol:'cdp',...await starting});
  } catch(error) {
    response.setHeader('Retry-After','1');
    send(503,{...info,ready:false,error:'headless_not_ready',message:error.message});
  }
}

async function openSession(profile,binary,serviceUrl) {
  const portFile=path.join(profile,'DevToolsActivePort');
  if (!engine) {
    await fs.mkdir(profile,{recursive:true});
    await fs.rm(portFile,{force:true});
    const child=spawn(binary,['--headless=new','--no-first-run','--no-default-browser-check',
      '--disable-background-networking','--window-size=1600,1000','--remote-debugging-address=127.0.0.1',
      '--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],
      {windowsHide:true,stdio:'ignore'});
    engine={child,target:null};
    const release=()=>{if(engine?.child===child)engine=null;};
    child.once('exit',release); child.once('error',release);
  }
  const deadline=Date.now()+15000;
  const owner=engine;
  while (engine===owner && Date.now()<deadline) {
    const result=await readSession(portFile,serviceUrl,owner);
    if(result)return result;
    await delay(150);
  }
  throw Error(engine?'无头工作区尚未就绪，请稍后重试。':'无头引擎启动失败或已退出。');
}

async function readSession(portFile,serviceUrl,owner) {
  try {
    const lines = (await fs.readFile(portFile,'utf8')).trim().split(/\r?\n/);
    const port = Number(lines[0]);
    if (!Number.isInteger(port) || port<1 || port>65535 || !browserPath.test(lines[1] || '')) throw Error();
    const address = `127.0.0.1:${port}`;
    const [version, targets] = await Promise.all([
      localJson(`http://${address}/json/version`), localJson(`http://${address}/json/list`)
    ]);
    // A previous process may have left its port file behind. Verify both the
    // browser instance and the page belonging to this installation's server.
    if (version.webSocketDebuggerUrl !== `ws://${address}${lines[1]}`) throw Error();
    const pages = targets.filter(t => t.type==='page' && t.title==='TENSORA' && t.url.split(/[?#]/,1)[0]===serviceUrl &&
      targetId.test(t.id) && t.webSocketDebuggerUrl===`ws://${address}/devtools/page/${t.id}`)
      .map(t=>({id:t.id, url:t.url, title:t.title, webSocketUrl:t.webSocketDebuggerUrl}));
    if (!pages.length) {
      // Create the application target after Chromium accepts connections. The
      // initial command-line URL on a cold profile may still be about:blank.
      const pending=targets.find(t=>t.id===owner.target);
      if (!pending || owner.loaded) {
        const target=await localJson(`http://${address}/json/new?${encodeURIComponent(serviceUrl)}`,'PUT');
        owner.target=target.id;
        owner.loaded=false;
      }
      return null;
    }
    owner.loaded=true;
    return {browserUrl:`http://${address}`, browserWebSocketUrl:version.webSocketDebuggerUrl, pages};
  } catch { return null; }
}

// Native clients can discover this installation without guessing the HTTP port.
async function detect() {
  const portFile = path.join(process.env.LOCALAPPDATA,'FemDesktop',installationId,'Headless','port.txt');
  const port = Number((await fs.readFile(portFile,'utf8')).trim());
  if (!Number.isInteger(port) || port<1 || port>65535) throw Error('桌面服务端口无效。');
  const info = await localJson(`http://127.0.0.1:${port}/api/automation`);
  if (info.application!=='TENSORA' || info.installationId!==installationId || !info.headless || info.ready!==true) throw Error('未找到此安装目录的后台服务。');
  return info;
}

if (require.main===module) detect().then(info=>console.log(JSON.stringify(info))).catch(error=>{
  console.error(JSON.stringify({ready:false,error:'discovery_failed',message:error.message}));
  process.exitCode=1;
});
module.exports = {discovery};
