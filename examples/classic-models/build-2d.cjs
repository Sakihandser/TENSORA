'use strict';
// Builds the 2D classic models through the TENSORA web app itself: the scene is
// loaded with normalizeScene(), regions are rebuilt, the app's Triangle mesher
// (or, for fluid–structure models, a graded Gmsh mesh in the compact format of
// the NACA 0012 example) creates the TRI3 mesh, workspace settings are checked
// with the app's own normalizers and the file is written like "保存模型".
// Usage: node examples/classic-models/build-2d.cjs [outDir] [modelKey ...]
const {spawn} = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const root = path.resolve(__dirname, '..', '..');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'C:/Users/hongm/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const models = require('./models-2d.cjs');
const {meshScene} = require('./gmsh-2d.cjs');
const names = require('./names.cjs');

const outDir = path.resolve(process.argv[2] || path.join(root, '..'));
const only = new Set(process.argv.slice(3));
const PORT = String(5297 + Math.floor(Math.random() * 50));

function prepareInPage(spec) {
  scene = normalizeScene(spec.scene);
  modelName.value = scene.name;
  rebuildDerivedRegions({markAnalysisNodePlacementStale: false, markAnalysisMeshStale: false});
  const missing = spec.scene.regions.filter(r => !scene.regions.some(s => s.id === r.id && s.name === r.name));
  if (missing.length || scene.regions.length !== spec.scene.regions.length) {
    throw Error('Regions not recognised: ' + missing.map(r => r.id).join(',') + ' detected ' + scene.regions.map(r => `${r.id}/${r.name}/${r.boundaryCurveIds.join('+')}`).join('; '));
  }
  return {geometryNodes: scene.geometryNodes, curves: scene.curves, regions: scene.regions.map(r => ({id: r.id, regionKind: r.regionKind, boundaryCurveIds: r.boundaryCurveIds}))};
}

async function finishInPage({spec, mesh}) {
  if (mesh) {
    scene.analysisNodes = mesh.analysisNodes.map(n => ({...n}));
    scene.analysisNodePlacement = null;
    scene.mesh = {elements: mesh.elements, metadata: mesh.metadata};
    scene = normalizeScene(JSON.parse(JSON.stringify(scene)));
    rebuildDerivedRegions({markAnalysisNodePlacementStale: false, markAnalysisMeshStale: false});
  } else if (spec.maxNodes) {
    maxAnalysisNodes.value = String(spec.maxNodes);
    await autoGenerateAnalysisMesh({regenerateNodes: true, adaptive: false, maxNodes: spec.maxNodes});
  }
  if (spec.deformationSettings) scene.deformationSettings = DeformationSettings.normalize(spec.deformationSettings);
  if (spec.blastSettings) scene.blastSettings = BlastSettings.normalize(spec.blastSettings);
  if (spec.blastBoundaryModes) scene.blastBoundaryModes = spec.blastBoundaryModes;
  if (spec.blastExplosiveId) scene.blastExplosiveId = spec.blastExplosiveId;
  if (spec.blastGasId) scene.blastGasId = spec.blastGasId;
  if (spec.fsiSettings) scene.fsiSettings = normalizeFsiSceneSettings(spec.fsiSettings);
  if (spec.dynamicsSettings) {
    // Part numbers follow the mesh, so initial velocities are given at a point inside each part.
    const d = {...spec.dynamicsSettings, partVelocities: {...(spec.dynamicsSettings.partVelocities || {})}};
    dynamicsPartsCache = null;
    const parts = dynamicsMesh();
    for (const {point, velocity} of d.partVelocityAt || []) {
      let best = -1, distance = Infinity;
      parts.nodes.forEach((p, i) => { const e = Math.hypot(p[0] - point[0], p[1] - point[1]); if (e < distance) { distance = e; best = i; } });
      d.partVelocities[String(parts.parts.nodePart[best] + 1)] = velocity;
    }
    scene.dynamicsSettings = normalizeDynamicsSceneSettings(d);
  }
  if (spec.staticPlaneMode !== undefined) scene.staticPlaneMode = spec.staticPlaneMode;
  syncRegionMaterialSnapshots();
  classifyAnalysisElements();
  setPage('home');
  fitViewToScene();
  fitCalculationViewToScene();
  const elements = scene.mesh?.elements || [];
  const byId = new Map(scene.analysisNodes.map(n => [n.id, n]));
  let hMax = 0, hMin = Infinity;
  for (const e of elements) for (let i = 0; i < 3; i++) {
    const a = byId.get(e.analysisNodeIds[i]), b = byId.get(e.analysisNodeIds[(i + 1) % 3]), l = Math.hypot(a.x - b.x, a.y - b.y);
    hMax = Math.max(hMax, l); hMin = Math.min(hMin, l);
  }
  const fixed = scene.analysisNodes.filter(n => n.mechanicalState !== 'free').length;
  const info = {nodes: scene.analysisNodes.length, elements: elements.length, fixedNodes: fixed, hMax: +hMax.toPrecision(3), hMin: +hMin.toPrecision(3),
    regions: scene.regions.map(r => `${r.id}:${r.regionKind}:${r.materialName || '-'}`).join(' ')};
  const payload = {...scene, viewport: {offsetX: view.offsetX, offsetY: view.offsetY, scale: view.scale}, calculationViewport: getCalculationViewState()};
  // Region/material classification of nodes and elements is recomputed by
  // importScene() -> rebuildDerivedRegions(); leave it out of the file.
  const derived = ['isStatic', 'isFree', 'geometrySourceType', 'geometrySourceId', 'geometrySourceDistance', 'structureName', 'regionKind',
    'isAir', 'isStructure', 'materialId', 'materialName', 'materialColor', 'materialProperties'];
  const json = JSON.stringify(payload, function (key, value) {
    if (derived.includes(key) && this && (this.analysisNodeIds || (this.placement !== undefined && 'ux' in this))) return undefined;
    if (key === 'sources' && this && this.sourceType !== undefined) return undefined;
    return value;
  });
  return {json, info};
}

(async () => {
  const server = spawn(path.join(root, 'node-v24.21.0-win-x64', 'node.exe'), ['server.js'], {cwd: root, env: {...process.env, PORT, FEM_OPEN_BROWSER: '0'}, windowsHide: true});
  let browser;
  try {
    await new Promise((resolve, reject) => { server.stdout.on('data', b => { if (b.toString().includes(PORT)) resolve(); }); server.once('error', reject); setTimeout(() => reject(Error('server start timeout')), 30000); });
    browser = await chromium.launch({executablePath: path.join(root, 'browser', 'chrome-win64', 'chrome.exe'), headless: true});
    const page = await browser.newPage({viewport: {width: 1600, height: 1000}});
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('dialog', d => { errors.push('dialog: ' + d.message()); d.dismiss(); });
    await page.goto(`http://127.0.0.1:${PORT}`);
    await page.waitForFunction(() => window.femSketchApi && typeof normalizeFsiSceneSettings === 'function');
    for (const [key, make] of Object.entries(models)) {
      if (only.size && !only.has(key)) continue;
      const spec = make();
      spec.scene.name = names[spec.scene.name] || spec.scene.name;
      const started = Date.now();
      try {
        const geometry = await page.evaluate(prepareInPage, spec);
        const mesh = spec.gmsh ? meshScene(geometry, {...spec.gmsh, workDir: fs.mkdtempSync(path.join(os.tmpdir(), 'tensora-gmsh2d-'))}) : null;
        const {json, info} = await page.evaluate(finishInPage, {spec, mesh});
        const file = path.join(outDir, spec.scene.name + '.json');
        fs.writeFileSync(file, json);
        console.log(`OK ${key} -> ${path.basename(file)} ${(json.length / 1e6).toFixed(2)} MB ${JSON.stringify(info)} ${((Date.now() - started) / 1000).toFixed(1)} s`);
      } catch (error) {
        console.log(`FAIL ${key}: ${error.message.split('\n').slice(0, 3).join(' / ')}`);
      }
      if (errors.length) { console.log('  page errors: ' + errors.join(' | ')); errors.length = 0; }
    }
  } finally {
    await browser?.close();
    server.kill();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
