'use strict';
// Small 2D sketch helper that writes TENSORA drawing data (geometry nodes,
// curves, regions and loads). Coordinates are in metres.
class Sketch {
  constructor(name) {
    this.name = name;
    this.geometryNodes = [];
    this.curves = [];
    this.regions = [];
    this.pointLoads = [];
    this.distributedLoads = [];
    this.bodyLoads = [];
  }
  point(x, y, mechanicalState = 'free') {
    const tol = 1e-12;
    let node = this.geometryNodes.find(n => Math.abs(n.x - x) < tol && Math.abs(n.y - y) < tol);
    if (!node) {
      node = {id: `G${this.geometryNodes.length + 1}`, x, y, mechanicalState};
      this.geometryNodes.push(node);
    } else if (mechanicalState !== 'free') node.mechanicalState = mechanicalState;
    return node.id;
  }
  pt(id) { return this.geometryNodes.find(n => n.id === id); }
  curve(type, a, b, controls = [], mechanicalState = 'free') {
    const id = `C${this.curves.length + 1}`;
    this.curves.push({id, type, geometryNodeIds: [a, b], controls, mechanicalState});
    return id;
  }
  line(p, q, state = 'free') { return this.curve('line', this.point(...p), this.point(...q), [], state); }
  // Circular arc through start, mid and end.
  arc(p, mid, q, state = 'free') {
    return this.curve('arc', this.point(...p), this.point(...q), [{x: mid[0], y: mid[1]}], state);
  }
  // Axis-aligned elliptical quarter arc; control is the bounding-box corner.
  ellipseQuarter(p, q, corner, state = 'free') {
    return this.curve('ellipse', this.point(...p), this.point(...q), [{x: corner[0], y: corner[1]}], state);
  }
  // Polyline through the points; returns curve ids.
  polyline(points, {closed = false, state = 'free', states = null} = {}) {
    const ids = [];
    const n = closed ? points.length : points.length - 1;
    for (let i = 0; i < n; i++) ids.push(this.line(points[i], points[(i + 1) % points.length], states ? states[i] : state));
    return ids;
  }
  // Full circle as `segments` arcs; returns curve ids.
  circle(cx, cy, r, segments = 4, {start = 0, state = 'free'} = {}) {
    const ids = [];
    for (let i = 0; i < segments; i++) {
      const a0 = start + 2 * Math.PI * i / segments, a1 = start + 2 * Math.PI * (i + 1) / segments, am = (a0 + a1) / 2;
      const p = a => [cx + r * Math.cos(a), cy + r * Math.sin(a)];
      ids.push(this.arc(p(a0), p(am), p(i + 1 === segments ? start : a1), state));
    }
    return ids;
  }
  // Arc from angle a0 to a1 (radians) split into n arcs.
  arcs(cx, cy, r, a0, a1, n, state = 'free') {
    const ids = [], p = a => [cx + r * Math.cos(a), cy + r * Math.sin(a)];
    for (let i = 0; i < n; i++) {
      const s = a0 + (a1 - a0) * i / n, e = a0 + (a1 - a0) * (i + 1) / n;
      ids.push(this.arc(p(s), p((s + e) / 2), p(e), state));
    }
    return ids;
  }
  region(name, curveIds, {kind = 'structure', material = null} = {}) {
    const id = `R${this.regions.length + 1}`;
    this.regions.push({id, name, regionKind: kind, boundaryCurveIds: curveIds, material});
    return id;
  }
  setState(curveIds, state) { for (const id of [].concat(curveIds)) this.curves.find(c => c.id === id).mechanicalState = state; }
  // Uniform/linear traction along a curve: q in N/m, direction unit vector.
  traction(curveId, q, direction, label = 'q', qEnd = q) {
    const id = `Q${this.distributedLoads.length + 1}`;
    const l = Math.hypot(direction[0], direction[1]);
    this.distributedLoads.push({id, curveId, q, qStart: q, qEnd, direction: {x: direction[0] / l, y: direction[1] / l}, start: 0, end: 1, label});
    return id;
  }
  force(point, fx, fy, label = 'F') {
    const id = `F${this.pointLoads.length + 1}`;
    this.pointLoads.push({id, geometryNodeId: this.point(...point), fx, fy, label, anchor: {x: point[0], y: point[1]}});
    return id;
  }
  gravity(g = 9.81, label = 'g') {
    this.bodyLoads.push({id: `B${this.bodyLoads.length + 1}`, targetType: 'global', regionId: null, magnitude: g, direction: {x: 0, y: -1}, label});
  }
  scene() {
    return {version: 6, name: this.name, staticPlaneMode: 0, geometryNodes: this.geometryNodes, curves: this.curves, regions: this.regions,
      pointLoads: this.pointLoads, distributedLoads: this.distributedLoads, bodyLoads: this.bodyLoads};
  }
}
module.exports = {Sketch};
