'use strict';
// Graded TRI3 meshes for 2D fluid–structure models. The drawing geometry is
// written as an OpenCASCADE .geo, fragmented so all regions share nodes, and
// meshed by the bundled Gmsh with MathEval size fields. Triangles are assigned
// to the innermost drawing region containing their centroid (air regions are
// dropped) and boundary edges are mapped back to drawing curve ids. The result
// uses the same compact format as the NACA 0012 example: analysis nodes with
// coordinates and elements with region ids and boundary edges.
const fs = require('node:fs');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const root = path.resolve(__dirname, '..', '..');
const GMSH = path.join(root, 'third_party', 'gmsh', 'gmsh-4.15.0-Windows64', 'gmsh.exe');

function circleCenter(a, b, c) {
  const d = 2 * (a.x * (b.y - c.y) + b.x * (c.y - a.y) + c.x * (a.y - b.y));
  const a2 = a.x * a.x + a.y * a.y, b2 = b.x * b.x + b.y * b.y, c2 = c.x * c.x + c.y * c.y;
  return {x: (a2 * (b.y - c.y) + b2 * (c.y - a.y) + c2 * (a.y - b.y)) / d, y: (a2 * (c.x - b.x) + b2 * (a.x - c.x) + c2 * (b.x - a.x)) / d};
}
// Polyline samples of a drawing curve (lines and three-point arcs).
function sampleCurve(curve, nodes, n = 64) {
  const [a, b] = curve.geometryNodeIds.map(id => nodes.get(id));
  if (curve.type === 'line') return [a, b];
  if (curve.type !== 'arc') throw Error('gmsh-2d supports line and arc curves only');
  const m = curve.controls[0], c = circleCenter(a, m, b), r = Math.hypot(a.x - c.x, a.y - c.y);
  const ang = p => Math.atan2(p.y - c.y, p.x - c.x);
  let t0 = ang(a), tm = ang(m), t1 = ang(b);
  const norm = t => (t - t0 + 4 * Math.PI) % (2 * Math.PI);
  let sweep = norm(t1); if (sweep === 0) sweep = 2 * Math.PI;
  if (norm(tm) > sweep) sweep -= 2 * Math.PI; // clockwise arc
  return Array.from({length: n + 1}, (_, i) => ({x: c.x + r * Math.cos(t0 + sweep * i / n), y: c.y + r * Math.sin(t0 + sweep * i / n)}));
}
function segDistance(p, a, b) {
  const dx = b.x - a.x, dy = b.y - a.y, l2 = dx * dx + dy * dy;
  const t = l2 ? Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / l2)) : 0;
  return Math.hypot(p.x - a.x - t * dx, p.y - a.y - t * dy);
}
function polyDistance(p, poly) { let d = Infinity; for (let i = 1; i < poly.length; i++) d = Math.min(d, segDistance(p, poly[i - 1], poly[i])); return d; }
function inside(p, poly) {
  let c = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const a = poly[i], b = poly[j];
    if ((a.y > p.y) !== (b.y > p.y) && p.x < (b.x - a.x) * (p.y - a.y) / (b.y - a.y) + a.x) c = !c;
  }
  return c;
}
function area(poly) { let s = 0; for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) s += (poly[j].x + poly[i].x) * (poly[j].y - poly[i].y); return Math.abs(s / 2); }

// Order the curves of a region into a closed chain of oriented curve ids.
function loopOf(region, curves) {
  const list = region.boundaryCurveIds.map(id => curves.get(id));
  const first = list.shift();
  const chain = [{c: first, rev: false}];
  let end = first.geometryNodeIds[1];
  while (list.length) {
    const i = list.findIndex(c => c.geometryNodeIds.includes(end));
    if (i < 0) throw Error('Region ' + region.id + ' boundary is not a single closed loop');
    const [c] = list.splice(i, 1), rev = c.geometryNodeIds[1] === end;
    chain.push({c, rev});
    end = rev ? c.geometryNodeIds[0] : c.geometryNodeIds[1];
  }
  return chain;
}

function meshScene(scene, {size, fields = [], workDir}) {
  const nodes = new Map(scene.geometryNodes.map(n => [n.id, n]));
  const curves = new Map(scene.curves.filter(c => !c.construction).map(c => [c.id, c]));
  const lines = ['SetFactory("OpenCASCADE");', 'Mesh.MeshSizeFromPoints = 0;', 'Mesh.MeshSizeFromCurvature = 0;', 'Mesh.MeshSizeExtendFromBoundary = 0;',
    'Mesh.Algorithm = 6;', 'Geometry.Tolerance = 1e-9;'];
  const pointTag = new Map(); let p = 0;
  for (const n of nodes.values()) { pointTag.set(n.id, ++p); lines.push(`Point(${p}) = {${n.x}, ${n.y}, 0};`); }
  const curveTag = new Map(); let k = 0;
  for (const c of curves.values()) {
    const [a, b] = c.geometryNodeIds.map(id => pointTag.get(id));
    if (c.type === 'line') lines.push(`Line(${++k}) = {${a}, ${b}};`);
    else {
      const ctr = circleCenter(nodes.get(c.geometryNodeIds[0]), c.controls[0], nodes.get(c.geometryNodeIds[1]));
      lines.push(`Point(${++p}) = {${ctr.x}, ${ctr.y}, 0};`);
      // OCC circle arcs are drawn the short way; split arcs to keep them < 180°.
      lines.push(`Point(${++p}) = {${c.controls[0].x}, ${c.controls[0].y}, 0};`);
      lines.push(`Circle(${++k}) = {${a}, ${p - 1}, ${p}};`);
      const first = k;
      lines.push(`Circle(${++k}) = {${p}, ${p - 1}, ${b}};`);
      curveTag.set(c.id, [first, k]);
      continue;
    }
    curveTag.set(c.id, [k]);
  }
  const regions = scene.regions.map(r => ({...r, poly: loopOf(r, curves).flatMap(({c, rev}) => { const s = sampleCurve(c, nodes); return rev ? s.reverse() : s; })}));
  let loop = 0; const surfaces = [];
  for (const r of regions) {
    const chain = loopOf(r, curves).flatMap(({c, rev}) => { const t = curveTag.get(c.id); return rev ? [...t].reverse().map(x => -x) : t; });
    lines.push(`Curve Loop(${++loop}) = {${chain.join(', ')}};`, `Plane Surface(${loop}) = {${loop}};`);
    surfaces.push(loop);
  }
  lines.push(`BooleanFragments{ Surface{${surfaces.join(', ')}}; Delete; }{}`);
  // Size field: min of the base size and each Box/Ball field ({type, ...params}).
  const ids = [];
  fields.forEach(({type, ...params}, i) => {
    const id = i + 1; ids.push(id);
    lines.push(`Field[${id}] = ${type};`);
    const defaults = type === 'Box' ? {ZMin: -1, ZMax: 1} : type === 'Ball' ? {ZCenter: 0} : {};
    for (const [key, value] of Object.entries({...defaults, ...params})) lines.push(`Field[${id}].${key} = ${value};`);
  });
  ids.push(fields.length + 1);
  lines.push(`Field[${fields.length + 1}] = MathEval;`, `Field[${fields.length + 1}].F = "${size}";`);
  lines.push(`Field[${fields.length + 2}] = Min;`, `Field[${fields.length + 2}].FieldsList = {${ids.join(', ')}};`, `Background Field = ${fields.length + 2};`);
  fs.mkdirSync(workDir, {recursive: true});
  fs.writeFileSync(path.join(workDir, 'model.geo'), lines.join('\n') + '\n');
  const run = spawnSync(GMSH, ['model.geo', '-2', '-format', 'msh2', '-o', 'model.msh', '-nt', '4'], {cwd: workDir, windowsHide: true, encoding: 'utf8'});
  if (run.status !== 0) throw Error('Gmsh failed: ' + (run.stderr || run.stdout).slice(-2000));
  return readMesh(fs.readFileSync(path.join(workDir, 'model.msh'), 'utf8'), scene, regions, curves, nodes);
}

function readMesh(text, scene, regions, curves, geometryNodes) {
  const rows = text.split(/\r?\n/);
  const ni = rows.indexOf('$Nodes'), ei = rows.indexOf('$Elements');
  const count = Number(rows[ni + 1]), ids = new Map(), pts = [];
  for (let i = 0; i < count; i++) { const [id, x, y] = rows[ni + 2 + i].trim().split(/\s+/).map(Number); ids.set(id, pts.length); pts.push({x, y}); }
  const triangles = [], segments = [];
  for (let i = 0, n = Number(rows[ei + 1]); i < n; i++) {
    const a = rows[ei + 2 + i].trim().split(/\s+/).map(Number), type = a[1], tags = a[2], conn = a.slice(3 + tags).map(id => ids.get(id));
    if (type === 2) triangles.push(conn); else if (type === 1) segments.push(conn);
  }
  const byArea = [...regions].sort((a, b) => area(a.poly) - area(b.poly));
  const curveSamples = [...curves.values()].map(c => ({c, s: sampleCurve(c, geometryNodes, 256)}));
  const span = Math.max(...pts.map(q => q.x)) - Math.min(...pts.map(q => q.x));
  const tol = 1e-6 * span + 1e-9;
  const curveOf = (a, b) => {
    const m = {x: (pts[a].x + pts[b].x) / 2, y: (pts[a].y + pts[b].y) / 2};
    let best = null, d = Infinity;
    for (const {c, s} of curveSamples) { const e = polyDistance(m, s); if (e < d) { d = e; best = c; } }
    const chord = Math.hypot(pts[a].x - pts[b].x, pts[a].y - pts[b].y);
    return d < Math.max(tol, 0.02 * chord) ? best.id : null;
  };
  const segCurve = new Map();
  for (const [a, b] of segments) { const id = curveOf(a, b); if (id) segCurve.set(a < b ? a + ',' + b : b + ',' + a, id); }
  const used = new Map(), out = [];
  for (const tri of triangles) {
    const c = {x: (pts[tri[0]].x + pts[tri[1]].x + pts[tri[2]].x) / 3, y: (pts[tri[0]].y + pts[tri[1]].y + pts[tri[2]].y) / 3};
    const region = byArea.find(r => inside(c, r.poly));
    if (!region || region.regionKind === 'air') continue;
    const [a, b, d] = tri, cross = (pts[b].x - pts[a].x) * (pts[d].y - pts[a].y) - (pts[d].x - pts[a].x) * (pts[b].y - pts[a].y);
    const t = cross < 0 ? [a, d, b] : [a, b, d];
    for (const id of t) if (!used.has(id)) used.set(id, used.size + 1);
    out.push({t, region: region.id});
  }
  const staticCurves = [...curves.values()].filter(c => c.mechanicalState !== 'free').map(c => ({c, s: sampleCurve(c, geometryNodes, 256)}));
  const analysisNodes = [...used.entries()].map(([i, n]) => {
    const q = pts[i];
    const states = staticCurves.filter(({s}) => polyDistance(q, s) < tol).map(({c}) => c.mechanicalState);
    const state = states.includes('static') || (states.includes('static-x') && states.includes('static-y')) ? 'static' : states[0] || 'free';
    return {id: 'A' + n, x: q.x, y: q.y, mechanicalState: state};
  });
  const elements = out.map(({t, region}, i) => {
    const edges = [];
    for (let j = 0; j < 3; j++) {
      const a = t[j], b = t[(j + 1) % 3], id = segCurve.get(a < b ? a + ',' + b : b + ',' + a);
      if (id) edges.push({nodeIds: ['A' + used.get(a), 'A' + used.get(b)], curveId: id});
    }
    return {id: 'E' + (i + 1), type: 'TRI3', analysisNodeIds: t.map(n => 'A' + used.get(n)), regionId: region, structureRegionId: region, edges};
  });
  return {analysisNodes, elements, metadata: {algorithm: 'gmsh', stale: false}};
}

module.exports = {meshScene};
