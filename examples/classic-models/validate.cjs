'use strict';
// Opens each model file through the app's own import inputs, records the
// "计算前检查" findings, presses the workspace's run button and intercepts the
// request, then builds the solver input decks from that request with the
// server's own adapters (CalculiX / PhAST / OOFEM / SU2 / OpenCourant). No
// solver is started.
// Usage: node examples/classic-models/validate.cjs file.json [...]
const {spawn} = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..', '..');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'C:/Users/hongm/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const solid3d = require(path.join(root, 'solid3d.js'));
const {deck} = require(path.join(root, 'deformation-runner.js'));
const {prepareFracture} = require(path.join(root, 'fracture-runner.js'));
const {prepareCrackBand} = require(path.join(root, 'oofem-fracture-runner.js'));
const {prepare} = require(path.join(root, 'fsi-model.js'));
const {buildFsiInputs} = require(path.join(root, 'fsi-deck.js'));
const {buildSphDecks} = require(path.join(root, 'fsi-sph.js'));
const {buildDecks} = require(path.join(root, 'blast3d-deck.js'));
const {buildDecks: buildBlast2dDecks} = require(path.join(root, 'blast2d-opencourant.js'));
const DeformationSettings = require(path.join(root, 'deformation-settings.js'));

const files = process.argv.slice(2);
const PORT = String(5350 + Math.floor(Math.random() * 40));

async function checkRequest(route, payload) {
  if (route === 'deformation-runs') {
    const s = payload.settings;
    if (payload.solid) {
      const model = solid3d.deformationModelFromSolid(payload.solid.mesh, payload.solid.settings);
      if (s.solver === 'oofem') prepareCrackBand(model, s);
      else if (s.solver === 'aster') DeformationSettings.normalize(s);
      else deck(model, s);
      return `${s.solver} 3D: ${model.nodes.length} nodes, ${model.elements.length} elements`;
    }
    if (s.solver === 'phast') { const r = prepareFracture(payload.model, s); return `PhAST: ${payload.model.nodes.length} nodes${r.warnings.length ? ' · ' + r.warnings.join(' ') : ''}`; }
    deck(payload.model, s);
    return `CalculiX 2D: ${payload.model.nodes.length} nodes, ${payload.model.elements.length} elements, plane ${s.planeMode}`;
  }
  if (route === 'fsi-runs') {
    if (payload.settings.engine === 'sph') {
      const d = buildSphDecks(payload.solid, payload.settings, payload.fluid);
      return `SPH: ${d.particles?.length ?? d.meta?.particles ?? '?'} particles · ${JSON.stringify(d.meta || {}).slice(0, 220)}`;
    }
    const {model, settings} = prepare(payload);
    const inputs = buildFsiInputs(model, settings, payload.fluid);
    return `SU2 ${inputs.settings.engine}/${inputs.settings.analysis}: fluid ${inputs.split.fluid.nodes.length} / solid ${inputs.split.solid.nodes.length} nodes`;
  }
  if (route === 'blast3d-runs') {
    const d = buildDecks(payload.solid, payload.settings);
    return `OpenCourant: ${payload.solid.mesh.tets.length} tets, roles ${JSON.stringify(payload.settings.volumeRoles)}, starter ${Math.round(d.starter.length / 1024)} KB`;
  }
  if (route === 'blast-runs') {
    // Build the OpenCourant slab + ALE borehole decks (Gmsh meshes the borehole); no solver run.
    const work = fs.mkdtempSync(path.join(require('node:os').tmpdir(), 'tensora-validate-blast2d-'));
    try {
      const d = await buildBlast2dDecks(payload.model, payload.settings, work);
      return `2D blast (OpenCourant): ${payload.model.nodes.length} nodes, ${payload.model.elements.length} TRI3 -> ${d.mesh.quads.length} quads, ${d.aleCells.length} ALE cells, ` +
        `wall ${d.bnd.wall.length} edges, hole r ${d.s.radius} charge ${d.s.chargeRadius}, source ${d.s.sourceMode}, H ${d.thickness.toPrecision(3)} m` +
        (d.source?.chargeAreaRatio ? `, charge area ratio ${d.source.chargeAreaRatio.toFixed(4)}` : '') + (d.warnings.length ? ' · ' + d.warnings.join(' ') : '');
    } finally { fs.rmSync(work, {recursive: true, force: true}); }
  }
  return 'unknown route';
}

(async () => {
  const server = spawn(path.join(root, 'node-v24.21.0-win-x64', 'node.exe'), ['server.js'], {cwd: root, env: {...process.env, PORT, FEM_OPEN_BROWSER: '0'}, windowsHide: true});
  let browser;
  try {
    await new Promise((resolve, reject) => { server.stdout.on('data', b => { if (b.toString().includes(PORT)) resolve(); }); setTimeout(() => reject(Error('server timeout')), 30000); });
    browser = await chromium.launch({executablePath: path.join(root, 'browser', 'chrome-win64', 'chrome.exe'), headless: true});
    for (const file of files) {
      const text = fs.readFileSync(file, 'utf8'), data = JSON.parse(text), is3d = data.kind === 'tensora-solid3d';
      const context = await browser.newContext({viewport: {width: 1600, height: 1000}});
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', e => errors.push(e.message));
      page.on('dialog', d => { errors.push('dialog: ' + d.message().slice(0, 200)); d.dismiss(); });
      let captured = null;
      await page.route(/\/api\/(deformation-runs|fsi-runs|blast3d-runs|blast-runs)$/, async route => {
        captured = {route: route.request().url().split('/api/')[1], body: route.request().postData()};
        await route.fulfill({status: 400, contentType: 'application/json', body: JSON.stringify({ok: false, error: 'captured by validation'})});
      });
      await page.goto(`http://127.0.0.1:${PORT}`);
      await page.waitForFunction(() => window.femSketchApi && window.Preflight);
      const workspace = is3d ? (data.blast3d ? 'blast' : data.fsi3d ? 'fsi' : 'deformation')
        : data.fsiSettings ? 'fsi' : data.blastSettings && data.blastExplosiveId ? 'blast' : data.deformationSettings ? 'deformation' : 'calculation';
      const toggles = {blast: '#enableBlastModule', fsi: '#enableFsiModule', deformation: '#enableDeformationModule'};
      const result = {file: path.basename(file), workspace};
      try {
        if (is3d) await page.evaluate(() => { const e = document.getElementById('enableSolid3dModule'); if (!e.checked) e.click(); });
        if (toggles[workspace]) await page.evaluate(sel => { const e = document.querySelector(sel); if (!e.checked) e.click(); }, toggles[workspace]);
        if (is3d) {
          await page.evaluate(() => window.setPage('calculation'));
          await page.setInputFiles('#solid3dLoadModel', file);
          await page.waitForFunction(() => /已导入|imported/i.test(document.getElementById('solid3dStatus').textContent), null, {timeout: 60000});
        } else {
          await page.setInputFiles('#fileInput', file);
          await page.waitForFunction(name => typeof scene !== 'undefined' && scene.name === name, data.name, {timeout: 120000});
          result.mesh = await page.evaluate(() => ({nodes: scene.analysisNodes.length, elements: scene.mesh.elements.length, stale: Boolean(scene.mesh.metadata?.stale)}));
        }
        await page.evaluate(w => window.setPage(w), workspace);
        await page.waitForTimeout(is3d ? 2500 : 600);
        if (!is3d && typeof refreshPreflight === 'function') await page.evaluate(w => refreshPreflight(w), workspace);
        const host = is3d ? {calculation: '#solid3dPreflight', deformation: '#solid3dDeformationPreflight', blast: '#solid3dBlastPreflight', fsi: '#solid3dFsiPreflight'}[workspace]
          : {calculation: '#staticPreflight', deformation: '#deformationPreflight', blast: '#blastPreflight', fsi: '#fsiPreflight'}[workspace];
        if (is3d) await page.click(`#solid3dPage .solid3d-panel`, {position: {x: 5, y: 5}}).catch(() => {});
        await page.waitForTimeout(500);
        result.preflight = (await page.locator(host).innerText().catch(() => '')).replace(/\s+/g, ' ').trim().slice(0, 600);
        if (workspace !== 'calculation') {
          const button = is3d ? {deformation: '#solid3dRunDeformation', blast: '#solid3dRunBlast', fsi: '#solid3dRunFsi'}[workspace]
            : {deformation: '#startDeformation', blast: '#startBlast', fsi: '#startFsi'}[workspace];
          await page.click(button);
          for (let i = 0; i < 600 && !captured; i++) {
            const dialog = page.locator('dialog[open]');
            if (await dialog.count()) {
              result.gate = (await dialog.innerText()).replace(/\s+/g, ' ').slice(0, 400);
              const proceed = dialog.locator('.preflight-proceed');
              if (await proceed.count()) await proceed.click(); else break;
            }
            await page.waitForTimeout(250);
          }
          if (captured) {
            result.request = `${captured.route} ${(captured.body.length / 1e6).toFixed(1)} MB`;
            if (process.env.SAVE_REQUESTS) fs.writeFileSync(path.join(process.env.SAVE_REQUESTS, path.basename(file, '.json') + '.request.json'), captured.body);
            result.deck = await checkRequest(captured.route, JSON.parse(captured.body));
          } else {
            result.request = 'NOT SENT';
            result.status = (await page.locator(is3d ? '#solid3dStatus' : `[data-page="${workspace}"] [id$="Status"]`).first().innerText().catch(() => '')).slice(0, 300);
          }
          if (!is3d) result.meshAfter = await page.evaluate(() => ({nodes: scene.analysisNodes.length, elements: scene.mesh.elements.length}));
        } else {
          result.model = await page.evaluate(() => { const m = prepareCalculationModelData(); return {counts: m.counts, warnings: m.warnings}; });
        }
      } catch (error) {
        result.error = error.message.split('\n')[0];
      }
      if (errors.length) result.pageErrors = errors.slice(0, 5);
      console.log(JSON.stringify(result));
      await context.close();
    }
  } finally {
    await browser?.close();
    server.kill();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
