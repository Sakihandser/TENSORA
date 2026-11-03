'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { sceneWorkflowHarness } = require('./helpers/scene-workflow');
const { encodeCalculationModelBinary, decodeCalculationResultBinary } = require('../calculation-ipc');

function triangle() {
  const material = { id: 'M1', name: 'Elastic', elasticModulus: 200, poissonRatio: .25, density: 2500 };
  return sceneWorkflowHarness({ geometryNodes: [
    { id: 'G1', x: 0, y: 0, mechanicalState: 'static' },
    { id: 'G2', x: 1, y: 0, mechanicalState: 'static-y' },
    { id: 'G3', x: 0, y: 1, mechanicalState: 'static-x' },
  ], curves: [
    { id: 'C1', type: 'line', geometryNodeIds: ['G1', 'G2'] },
    { id: 'C2', type: 'line', geometryNodeIds: ['G2', 'G3'] },
    { id: 'C3', type: 'line', geometryNodeIds: ['G3', 'G1'] },
  ], regions: [{ id: 'R1', boundaryCurveIds: ['C1', 'C2', 'C3'], material }],
  analysisNodes: [{ id: 'A1', x: 0, y: 0 }, { id: 'A2', x: 1, y: 0 }, { id: 'A3', x: 0, y: 1 }],
  mesh: { elements: [{ id: 'E1', nodeIds: ['A1', 'A2', 'A3'], regionId: 'R1' }] },
  pointLoads: [{ id: 'F1', geometryNodeId: 'G2', fx: 500000, fy: 0 }] });
}

test('directional states and legacy supports survive scene save and reload', () => {
  const { context: c, scene } = triangle();
  const restored = c.normalizeScene(JSON.parse(JSON.stringify(scene)));
  assert.deepEqual(Array.from(restored.geometryNodes, n => n.mechanicalState), ['static', 'static-y', 'static-x']);
  for (const legacy of [true, 'fixed', 'ground', '静态']) {
    assert.equal(c.normalizeMechanicalState(legacy), 'static');
    assert.equal(JSON.stringify(c.mechanicalConstraints(legacy)), '{"ux":true,"uy":true}');
  }
});

test('curve intersection constraints combine per axis and release without stale endpoint constraints', () => {
  const { context: c, scene } = triangle();
  scene.geometryNodes.forEach(n => { n.mechanicalState = 'free'; });
  scene.curves[0].mechanicalState = 'static-x';
  scene.curves[2].mechanicalState = 'static-y';
  c.syncIntersectionGeometryNodes();
  assert.equal(c.getGeometryStateAtPoint({ x: 0, y: 0 }).mechanicalState, 'static');
  assert.equal(c.getGeometryStateAtPoint({ x: .5, y: 0 }).mechanicalState, 'static-x');
  scene.curves[0].mechanicalState = 'free';
  c.syncIntersectionGeometryNodes();
  assert.equal(c.getGeometryStateAtPoint({ x: 0, y: 0 }).mechanicalState, 'static-y');
  scene.curves[2].mechanicalState = 'free';
  c.syncIntersectionGeometryNodes();
  assert.equal(c.getGeometryStateAtPoint({ x: 0, y: 0 }).mechanicalState, 'free');
  scene.curves[0].construction = true;
  scene.curves[0].mechanicalState = 'static';
  assert.equal(c.getGeometryStateAtPoint({ x: .5, y: 0 }).mechanicalState, 'free');
});

test('adaptive boundary provenance retains its single constrained axis', () => {
  const { context: c, scene } = triangle();
  scene.curves[0].mechanicalState = 'static-x';
  const node = { x: .5, y: -.1, placement: { sourceType: 'adaptiveBoundary', curveId: 'C1' } };
  c.classifyAnalysisNode(node);
  assert.equal(node.mechanicalState, 'static-x');
  assert.equal(node.isStatic, true);
  scene.curves[0].mechanicalState = 'static-y';
  c.classifyAnalysisNode(node);
  assert.equal(node.mechanicalState, 'static-y');
});

test('frontend exports single-axis flags consistently in JSON, text and direct solver input', () => {
  const { context: c } = triangle();
  const p = c.buildCalculationInputExport(), m = c.calculationInputPayloadToDirectModel(p);
  assert.deepEqual(Array.from(m.nodes, n => [n.fixUx, n.fixUy]), [[true, true], [false, true], [true, false]]);
  assert.deepEqual(Array.from(p.boundaryConditions, b => Array.from(b.fixed)), [['ux', 'uy'], ['uy'], ['ux']]);
  assert.equal(p.boundaryConditions[1].ux, null);
  const text = c.calculationInputPayloadToText(p).split(/\r?\n/);
  const start = text.indexOf('NODES') + 2;
  assert.deepEqual(text.slice(start, start + 3).map(line => line.trim().split(/\s+/).slice(3, 5)), [['1', '1'], ['0', '1'], ['1', '0']]);
});

test('actual C++ solve from frontend directional settings leaves free axes movable and constrained axes zero', () => {
  const { context: c } = triangle();
  const model = c.calculationInputPayloadToDirectModel(c.buildCalculationInputExport());
  const run = spawnSync(path.join(__dirname, '../TensoraCore/x64/Release/TensoraCore.exe'), ['--binary-ipc'],
    { input: encodeCalculationModelBinary(model), windowsHide: true, timeout: 30000 });
  assert.equal(run.status, 0, run.stderr.toString());
  const result = decodeCalculationResultBinary(run.stdout), d = result.nodeDisplacements;
  assert.equal(d[0].ux, 0); assert.equal(d[0].uy, 0);
  assert.equal(d[1].uy, 0); assert.equal(d[2].ux, 0);
  assert.ok(Math.abs(d[1].ux - 5e-6) < 1e-14);
  assert.ok(Math.abs(d[2].uy + 1.25e-6) < 1e-14);
});

test('deformation input fixes only the selected displacement components', () => {
  const { context: c } = triangle();
  const model = c.calculationInputPayloadToDirectModel(c.buildCalculationInputExport());
  const { input } = require('../deformation-runner').deck(model, {});
  const boundary = input.split('*BOUNDARY\n')[1].split('*STEP')[0].trim().split('\n');
  assert.deepEqual(boundary, ['1,1,1', '1,2,2', '2,2,2', '3,1,1']);
});

test('blast dynamics honors each single-axis constraint and retains motion on the other axis', async () => {
  const { context: c } = triangle();
  const { blastRing } = require('./helpers/blast-ring');
  const { runBlastCore } = require('../server');
  for (const state of ['static-x', 'static-y']) {
    const model = blastRing({ sectors: 16, rings: 3 });
    const constraints = c.mechanicalConstraints(state);
    for (const n of model.nodes) { n.fixUx = constraints.ux; n.fixUy = constraints.uy; }
    const result = await runBlastCore(model, { rockModel: 1, fracture: false, boundary: 0,
      pressure: 1e6, pulse: 1e-5, duration: 3e-5, frames: 3 });
    const fixedAxis = state === 'static-x' ? 0 : 1;
    for (const frame of result.frames) {
      assert.ok(frame.u.every((v, i) => i % 2 !== fixedAxis || v === 0));
    }
    assert.ok(result.frames.at(-1).u.some((v, i) => i % 2 !== fixedAxis && Math.abs(v) > 1e-12));
  }
});
