"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const {spawn} = require("node:child_process");
const fs = require("node:fs/promises");
const path = require("node:path");
const os = require("node:os");
const http = require("node:http");
const net = require("node:net");
const {once} = require("node:events");

// Isolated copies avoid rewriting the user's material-library script at startup.
async function fixture(t) {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "fem-desktop-server-"));
  t.after(() => fs.rm(directory, {recursive:true, force:true}));
  const root = path.join(__dirname, "..");
  for (const file of await fs.readdir(root)) if (file.endsWith(".js")) await fs.copyFile(path.join(root,file), path.join(directory,file));
  const core = path.join("src", "core");
  await fs.mkdir(path.join(directory, core), {recursive:true});
  for (const file of ["solid3d-restraint-data.js", "mesh-refinements.js", "solid3d-mesh-io.js"]) {
    await fs.copyFile(path.join(root, core, file), path.join(directory, core, file));
  }
  await fs.writeFile(path.join(directory,"index.html"), "<title>Desktop server test</title>");
  return directory;
}
function launch(t, directory, port, {args=[], env={}}={}) {
  const child = spawn(process.execPath, [path.join(directory,"server.js"), ...args], {
    cwd:directory, windowsHide:true, stdio:["pipe","pipe","pipe"],
    env:{...process.env, FEM_OPEN_BROWSER:"0", FEM_DESKTOP:"1", PORT:String(port), ...env},
  });
  let output = "", errors = "";
  child.stderr.on("data", data => { errors += data; });
  t.after(() => { if (child.exitCode === null) child.kill(); });
  const closed = once(child,"exit");
  const ready = new Promise((resolve,reject) => {
    const timeout = setTimeout(() => reject(new Error("Readiness timeout: " + output + errors)), 10000);
    child.once("error", error => {clearTimeout(timeout); reject(error);});
    child.once("exit", () => {clearTimeout(timeout); reject(new Error("Exited before ready: " + output + errors));});
    child.stdout.on("data", data => {
      output += data;
      const match = output.match(/^FEM_DESKTOP_READY (.+)\r?$/m);
      if (match) { clearTimeout(timeout); resolve(JSON.parse(match[1])); }
    });
  });
  return {child, ready, closed, errors:() => errors};
}
function get(url) {
  return new Promise((resolve,reject) => {
    http.get(url, response => {
      let body=""; response.on("data",data=>{body+=data;});
      response.on("end",()=>resolve({status:response.statusCode,body}));
    }).on("error",reject);
  });
}
async function within(promise, ms=5000) {
  let timer;
  try {return await Promise.race([promise,new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error("Shutdown timeout")),ms);})]);}
  finally {clearTimeout(timer);}
}

test("desktop service reports the actual ephemeral port and exits when owner pipe closes", async t => {
  const directory = await fixture(t);
  const app = launch(t,directory,0);
  const ready = await app.ready;
  assert.equal(ready.pid,app.child.pid);
  assert.ok(ready.port>0);
  assert.equal(ready.url,`http://127.0.0.1:${ready.port}/`);
  const response=await get(ready.url);
  assert.equal(response.status,200);
  assert.match(response.body,/Desktop server test/);
  app.child.stdin.end();
  const [code]=await within(app.closed);
  assert.equal(code,0,app.errors());
  await assert.rejects(get(ready.url),{code:"ECONNREFUSED"});
});

test("desktop service skips an occupied port without attaching to or stopping its owner", async t => {
  const directory=await fixture(t);
  const occupied=net.createServer(socket=>socket.end());
  await new Promise(resolve=>occupied.listen(0,"127.0.0.1",resolve));
  t.after(()=>occupied.close());
  const firstPort=occupied.address().port;
  const app=launch(t,directory,firstPort);
  const ready=await app.ready;
  assert.notEqual(ready.port,firstPort);
  assert.ok(ready.port>firstPort && ready.port<=firstPort+20);
  assert.equal((await get(ready.url)).status,200);
  app.child.stdin.write("shutdown\n");
  assert.equal((await within(app.closed))[0],0,app.errors());
  assert.equal(occupied.listening,true);
  assert.doesNotMatch(app.errors(),/MaxListenersExceededWarning|ERR_SERVER_NOT_RUNNING/);
});

test("desktop shutdown also closes active HTTP connections", async t => {
  const directory=await fixture(t);
  const app=launch(t,directory,0);
  const ready=await app.ready;
  const socket=net.connect(ready.port,"127.0.0.1");
  socket.on("error",()=>{});
  t.after(()=>socket.destroy());
  await once(socket,"connect");
  // An incomplete POST would otherwise hold server.close() open indefinitely.
  socket.write("POST /api/materials HTTP/1.1\r\nHost: localhost\r\nContent-Length: 200\r\n\r\n{");
  app.child.stdin.end();
  assert.equal((await within(app.closed))[0],0);
});

test('drawing recovery API survives a desktop restart on a different port',async t=>{
 const directory=await fixture(t),first=launch(t,directory,0),ready=await first.ready;
 const snapshot={scene:{name:'Recovered plate',geometryNodes:[{id:'G1',x:1,y:2}],curves:[],regions:[],pointLoads:[{id:'F1',fx:125,fy:-300}],distributedLoads:[],bodyLoads:[]},draft:null,activeTool:'select',constructionMode:false};
 const saved=await fetch(ready.url+'api/drawing-recovery',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(snapshot)});assert.equal(saved.status,200);
 first.child.stdin.end();assert.equal((await within(first.closed))[0],0);
 const second=launch(t,directory,0),next=await second.ready;
 const record=await (await fetch(next.url+'api/drawing-recovery')).json();assert.equal(record.snapshot.scene.name,'Recovered plate');assert.equal(record.snapshot.scene.pointLoads[0].fx,125);
 second.child.stdin.end();assert.equal((await within(second.closed))[0],0);
});

test('strict-port rejects occupied port, CLI --port overrides PORT env, and health/server-info/automation-api report bound port', async t => {
  const {parseServerCliArgs} = require('../server');
  const parsed = parseServerCliArgs(['--port=5210', '--strict-port', '--no-open'], {PORT:'5173', FEM_OPEN_BROWSER:'1'});
  assert.equal(parsed.port, 5210);
  assert.equal(parsed.strictPort, true);
  assert.equal(parsed.maxPortAttempts, 0);
  assert.equal(parsed.openBrowser, false);
  assert.throws(() => parseServerCliArgs(['--port', '70000'], {}), /端口无效/);
  assert.throws(() => parseServerCliArgs(['--port-range', '-1'], {}), /端口尝试范围无效/);

  const directory = await fixture(t);
  const occupied = net.createServer(socket => socket.end());
  await new Promise(resolve => occupied.listen(0, '127.0.0.1', resolve));
  t.after(() => occupied.close());
  const busyPort = occupied.address().port;

  // Strict mode exits non-zero rather than hopping to busyPort + 1.
  const strictApp = launch(t, directory, busyPort, {args: ['--strict-port']});
  strictApp.ready.catch(() => {});
  const [strictCode] = await within(strictApp.closed);
  assert.notEqual(strictCode, 0);
  assert.match(strictApp.errors(), /严格端口模式|已被占用/);

  // CLI --port 0 overrides occupied PORT env and reports live health/server-info.
  const app = launch(t, directory, busyPort, {args: ['--port', '0', '--port-range', '5'], env: {TENSORA_INSTANCE: 'demo'}});
  const ready = await app.ready;
  assert.notEqual(ready.port, busyPort);
  const health = await (await fetch(ready.url + 'api/health')).json();
  assert.equal(health.ok, true);
  assert.equal(health.port, ready.port);
  const info = await (await fetch(ready.url + 'api/server-info')).json();
  assert.equal(info.ok, true);
  assert.equal(info.port, ready.port);
  assert.equal(info.instance, 'demo');
  assert.equal(info.serviceUrl, ready.url);

  // automation-api.js --port discovers the service directly and exposes expanded operations.
  const auto = await (await fetch(ready.url + 'api/automation')).json();
  assert.equal(auto.port, ready.port);
  assert.equal(auto.instance, 'demo');
  const opNames = new Set(auto.operations.map(o => o.name));
  for (const name of ['health','serverInfo','blast2d','blast3d','fsiStatus','dynamics','specialtyCancel','closeHeadlessSession']) {
    assert.ok(opNames.has(name), 'missing operation ' + name);
  }
  const {execFileSync} = require('node:child_process');
  const urlOnly = execFileSync(process.execPath, [path.join(directory, 'automation-api.js'), '--port', String(ready.port), '--url-only'], {encoding: 'utf8', timeout: 5000}).trim();
  assert.equal(urlOnly, ready.url);
  const portOnly = execFileSync(process.execPath, [path.join(directory, 'automation-api.js'), '--port', String(ready.port), '--port-only'], {encoding: 'utf8', timeout: 5000}).trim();
  assert.equal(portOnly, String(ready.port));

  app.child.stdin.end();
  assert.equal((await within(app.closed))[0], 0, app.errors());
});
