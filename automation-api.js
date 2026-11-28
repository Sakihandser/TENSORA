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
const instanceNamePattern = /^[A-Za-z0-9_-]{1,32}$/;
const operations = [
  ['health','GET','/api/health'], ['serverInfo','GET','/api/server-info'],
  ['materials','GET','/api/materials'], ['saveMaterials','POST','/api/materials'],
  ['explosives','GET','/api/explosives'], ['saveExplosives','POST','/api/explosives'],
  ['gases','GET','/api/gases'], ['saveGases','POST','/api/gases'],
  ['fluids','GET','/api/fluids'], ['saveFluids','POST','/api/fluids'],
  ['blastMaterials','POST','/api/blast-materials'], ['deformationMaterials','POST','/api/deformation-materials'],
  ['materialBindings','POST','/api/material-bindings'],
  ['solidPreview','POST','/api/solid3d/preview'], ['solidMesh','POST','/api/solid3d/mesh'],
  ['static2d','POST','/api/calculation-runs'], ['static3d','POST','/api/solid3d/solve'],
  ['deformation','POST','/api/deformation-runs'],
  ['blast2d','POST','/api/blast-runs'], ['blast3dStatus','GET','/api/blast3d-status'],
  ['blast3d','POST','/api/blast3d-runs'], ['blast3dSummary','GET','/api/blast3d-runs/{runId}'],
  ['blast3dFrame','GET','/api/blast3d-runs/{runId}/frames/{index}'], ['blast3dProbe','GET','/api/blast3d-runs/{runId}/probe?nodes={nodes}'],
  ['fsiStatus','GET','/api/fsi-status'], ['fsi','POST','/api/fsi-runs'],
  ['fsiSummary','GET','/api/fsi-runs/{runId}'], ['fsiFrame','GET','/api/fsi-runs/{runId}/frames/{index}'],
  ['dynamics','POST','/api/dynamics-runs'], ['solverStatus','GET','/api/dynamics-status'],
  ['dynamicsSummary','GET','/api/dynamics-runs/{runId}'], ['dynamicsFrame','GET','/api/dynamics-runs/{runId}/frames/{index}'],
  ['dynamicsProbe','GET','/api/dynamics-runs/{runId}/probe?nodes={nodes}'],
  ['specialtyCancel','POST','/api/specialty-runs/{runId}/cancel'],
  ['headlessSession','POST','/api/automation/session'], ['closeHeadlessSession','DELETE','/api/automation/session']
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
  const session=pathname.endsWith('/session');
  if (!session && request.method !== 'GET') {
    response.setHeader('Allow','GET'); send(405, {error:'method_not_allowed'}); return;
  }
  if (session && !['POST','DELETE'].includes(request.method)) {
    response.setHeader('Allow','POST, DELETE'); send(405, {error:'method_not_allowed'}); return;
  }
  const profile=process.env.TENSORA_HEADLESS_PROFILE, binary=process.env.TENSORA_HEADLESS_BROWSER;
  const instance=process.env.TENSORA_INSTANCE || (profile ? 'default' : 'desktop');
  const info = {application:'TENSORA', apiVersion:1, installationId, serviceUrl, port:servicePort, pid:process.pid,
    instance, strictPort:process.env.TENSORA_STRICT_PORT==='1', headless:Boolean(profile)};
  if (!session) {
    send(200,{...info,ready:true,engineRunning:Boolean(engine),operations}); return;
  }
  if (request.method === 'DELETE') {
    const hadEngine = Boolean(engine);
    if (engine?.child) {
      const child = engine.child;
      engine = null;
      try { child.kill(); } catch { /* already exited */ }
    }
    send(200,{...info,ready:true,closed:hadEngine,engineRunning:false}); return;
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
function stateRoot() {
  return path.join(process.env.LOCALAPPDATA || '', 'FemDesktop', installationId);
}

async function queryPort(port, {requireHeadless=true, verifyInstallation=true}={}) {
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw Error('桌面服务端口无效。');
  const info = await localJson(`http://127.0.0.1:${port}/api/automation`);
  if (info.application !== 'TENSORA' || info.ready !== true) throw Error('目标端口不是有效的 TENSORA 服务。');
  if (verifyInstallation && info.installationId !== installationId) throw Error('未找到此安装目录的后台服务。');
  if (requireHeadless && !info.headless) throw Error('目标端口运行的不是后台模式服务。');
  return info;
}

async function detect(options={}) {
  if (options.url) {
    const parsed = new URL(options.url);
    if (!['127.0.0.1','localhost'].includes(parsed.hostname)) throw Error('仅允许连接本机环回地址（127.0.0.1 / localhost）。');
    const port = Number(parsed.port || 80);
    return queryPort(port, {requireHeadless:false, verifyInstallation:false});
  }
  if (options.port != null) {
    return queryPort(options.port, {requireHeadless:false, verifyInstallation:false});
  }
  if (options.all) {
    const root = stateRoot();
    const candidates = [{label:'desktop', file:path.join(root,'port.txt'), requireHeadless:false}];
    const entries = await fs.readdir(root, {withFileTypes:true}).catch(()=>[]);
    for (const entry of entries) {
      if (!entry.isDirectory()) continue;
      if (entry.name === 'Headless' || entry.name.startsWith('Headless-'))
        candidates.push({label:entry.name, file:path.join(root,entry.name,'port.txt'), requireHeadless:true});
      else if (entry.name.startsWith('Desktop-'))
        candidates.push({label:entry.name, file:path.join(root,entry.name,'port.txt'), requireHeadless:false});
    }
    const instances = [];
    for (const item of candidates) {
      try {
        const port = Number((await fs.readFile(item.file,'utf8')).trim());
        const info = await queryPort(port, {requireHeadless:item.requireHeadless, verifyInstallation:true});
        instances.push({stateFolder:item.label, ...info});
      } catch { /* stopped or stale port.txt */ }
    }
    return {application:'TENSORA', installationId, count:instances.length, instances};
  }
  let portFile;
  const requireHeadless = !options.desktop;
  if (options.desktop) {
    portFile = options.instance ? path.join(stateRoot(), `Desktop-${options.instance}`, 'port.txt') : path.join(stateRoot(), 'port.txt');
  } else if (options.instance) {
    portFile = path.join(stateRoot(), `Headless-${options.instance}`, 'port.txt');
  } else {
    portFile = path.join(stateRoot(), 'Headless', 'port.txt');
  }
  const port = Number((await fs.readFile(portFile,'utf8')).trim());
  return queryPort(port, {requireHeadless, verifyInstallation:true});
}

function parseCliArgs(argv) {
  const options = {};
  for (let i = 0; i < argv.length; i++) {
    let arg = argv[i], inline = null;
    const eq = arg.indexOf('=');
    if (arg.startsWith('--') && eq > 2) { inline = arg.slice(eq + 1); arg = arg.slice(0, eq); }
    const next = flag => { if (inline !== null) return inline; if (i + 1 >= argv.length) throw Error(`参数 ${flag} 缺少取值。`); return argv[++i]; };
    if (arg === '--help' || arg === '-h') options.help = true;
    else if (arg === '--all') options.all = true;
    else if (arg === '--desktop') options.desktop = true;
    else if (arg === '--url-only') options.urlOnly = true;
    else if (arg === '--port-only') options.portOnly = true;
    else if (arg === '--instance') {
      const name = next('--instance');
      if (!instanceNamePattern.test(name)) throw Error(`实例名无效：${name}`);
      options.instance = name;
    } else if (arg === '--port' || arg === '-p') {
      const p = Number(next(arg));
      if (!Number.isInteger(p) || p < 1 || p > 65535) throw Error(`端口无效：${p}`);
      options.port = p;
    } else if (arg === '--url') {
      options.url = next('--url');
    } else throw Error(`未知参数：${argv[i]}`);
  }
  return options;
}

if (require.main === module) {
  (async () => {
    const options = parseCliArgs(process.argv.slice(2));
    if (options.help) {
      console.log([
        '用法: node automation-api.js [选项]',
        '  （无参数）             发现本安装目录默认后台实例（Headless/port.txt）并输出 JSON',
        '  --instance <名称>      发现指定命名实例（配合 TENSORA.exe --instance <名称>）',
        '  --desktop              发现桌面窗口模式实例',
        '  --port <N> / -p <N>    直接探测本机指定端口上的 TENSORA 服务',
        '  --url <URL>            直接探测指定本机服务 URL',
        '  --all                  扫描并列出本安装目录所有在线的桌面与后台实例',
        '  --url-only             仅输出服务根地址（便于脚本赋值）',
        '  --port-only            仅输出端口号'
      ].join('\n'));
      return;
    }
    const info = await detect(options);
    if (options.urlOnly && info.serviceUrl) console.log(info.serviceUrl);
    else if (options.portOnly && info.port) console.log(String(info.port));
    else console.log(JSON.stringify(info));
  })().catch(error => {
    console.error(JSON.stringify({ready:false,error:'discovery_failed',message:error.message}));
    process.exitCode = 1;
  });
}
module.exports = {discovery, detect, parseCliArgs, operations};
