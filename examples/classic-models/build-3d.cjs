'use strict';
// Builds the 3D classic models: CAD features are meshed by the app's own Gmsh
// path (solid3d.meshSolid, exactly what "生成网格" calls), volumes and CAD faces
// are identified geometrically, and the 3D workspace snapshot (conditions,
// volume materials, blast / FSI settings) is written like "保存三维模型".
// Usage: node examples/classic-models/build-3d.cjs [outDir] [modelKey ...]
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..', '..');
const solid3d = require(path.join(root, 'solid3d.js'));
const models = require('./models-3d.cjs');
const names = require('./names.cjs');

const outDir = path.resolve(process.argv[2] || path.join(root, '..'));
const only = new Set(process.argv.slice(3));

function describeFaces(mesh) {
  const nodes = mesh.nodes;
  return mesh.surfaces.map(face => {
    const min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity], c = [0, 0, 0], nrm = [0, 0, 0];
    let area = 0;
    for (const tri of face.triangles) {
      const [a, b, d] = tri.map(i => nodes[i]);
      const u = [b[0] - a[0], b[1] - a[1], b[2] - a[2]], v = [d[0] - a[0], d[1] - a[1], d[2] - a[2]];
      const n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]], A = Math.hypot(...n) / 2;
      area += A;
      for (let k = 0; k < 3; k++) { c[k] += A * (a[k] + b[k] + d[k]) / 3; nrm[k] += n[k] / 2; }
      for (const p of [a, b, d]) for (let k = 0; k < 3; k++) { min[k] = Math.min(min[k], p[k]); max[k] = Math.max(max[k], p[k]); }
    }
    return {id: String(face.id), volumeId: String(face.volumeId), neighbor: face.triangleNeighborVolumes?.find(v => v != null) ?? null,
      centroid: c.map(x => x / area), area, min, max, planarAxis: [0, 1, 2].find(k => max[k] - min[k] < 1e-9) ?? -1};
  });
}

// Small query API handed to each model's assign() step.
function helpers(mesh) {
  const faces = describeFaces(mesh);
  const volumeAt = (x, y, z) => {
    let best = null, d = Infinity;
    for (const v of mesh.volumes) { const e = Math.hypot(v.centroid[0] - x, v.centroid[1] - y, v.centroid[2] - z); if (e < d) { d = e; best = v; } }
    return String(best.id);
  };
  // Planar faces on the plane axis = value (axis 0/1/2), optionally of a volume and inside a box.
  const plane = (axis, value, {volume = null, within = null, tol = 1e-6} = {}) => faces.filter(f => f.planarAxis === axis && Math.abs(f.min[axis] - value) < tol &&
    (!volume || f.volumeId === volume || String(f.neighbor) === volume) &&
    (!within || [0, 1, 2].every(k => f.centroid[k] >= within[0][k] - tol && f.centroid[k] <= within[1][k] + tol))).map(f => f.id);
  const where = predicate => faces.filter(predicate).map(f => f.id);
  return {mesh, faces, volumeAt, plane, where};
}

(async () => {
  for (const [key, make] of Object.entries(models)) {
    if (only.size && !only.has(key)) continue;
    const spec = make();
    spec.name = names[spec.name] || spec.name;
    const started = Date.now();
    try {
      const shapes = spec.shapes.map((shape, i) => ({featureId: shape.featureId || `feature-${i + 1}`, operation: 'add', ...shape}));
      const mesh = await solid3d.meshSolid({shapes, stepBase64: null, meshSize: spec.meshSize, restraintGuides: []});
      const h = helpers(mesh);
      const assigned = spec.assign(h);
      for (const condition of assigned.conditions || []) if (condition.surface && !mesh.surfaces.some(s => String(s.id) === String(condition.surface))) throw Error('missing face ' + condition.surface);
      const used = new Set(Object.values(assigned.volumeMaterials || {}));
      const model = {version: 1, kind: 'tensora-solid3d', name: spec.name, shapes, stepBase64: null, meshSize: spec.meshSize, mesh,
        conditions: assigned.conditions || [], restraintGuides: [], volumeMaterials: assigned.volumeMaterials || {}, hiddenVolumes: assigned.hiddenVolumes || [],
        ...(spec.embeddedMaterials?.length ? {embeddedMaterials: spec.embeddedMaterials.filter(m => used.has(m.id))} : {}),
        sectionView: assigned.sectionView || {mode: 'surface', planes: []}, materialId: [...used][0] || '',
        ...(assigned.blast3d ? {blast3d: assigned.blast3d} : {}), ...(assigned.fsi3d ? {fsi3d: assigned.fsi3d} : {})};
      delete model.mesh.meshTiming;
      const json = JSON.stringify(model);
      fs.writeFileSync(path.join(outDir, spec.name + '.json'), json);
      const volumes = mesh.volumes.map(v => `${v.id}:${v.elements}`).join(' ');
      console.log(`OK ${key} -> ${spec.name}.json ${(json.length / 1e6).toFixed(2)} MB nodes ${mesh.nodes.length} tets ${mesh.tets.length} volumes [${volumes}] faces ${mesh.surfaces.length} ${((Date.now() - started) / 1000).toFixed(1)} s`);
      if (assigned.report) console.log('   ' + assigned.report);
    } catch (error) {
      console.log(`FAIL ${key}: ${error.stack.split('\n').slice(0, 3).join(' / ')}`);
    }
  }
})();
