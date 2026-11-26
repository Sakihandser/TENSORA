'use strict';
// 2D classic models. Units: m, N, Pa (material E in GPa and strengths in MPa
// follow the material library convention). Every model is plane per unit
// thickness (1 m), as in the TENSORA 2D workspaces.
const path = require('node:path');
const {Sketch} = require('./sketch.cjs');
const {lib, deformationCard, custom} = require('./materials.cjs');
const explosives = require(path.join(__dirname, '..', '..', 'explosives', 'library.json')).explosives;
const gases = require(path.join(__dirname, '..', '..', 'gases', 'library.json')).gases;
const fluids = require(path.join(__dirname, '..', '..', 'fluids', 'library.json')).fluids;

const mm = 1e-3;
const deg = Math.PI / 180;
const fluid = id => ({...fluids.find(f => f.id === id)});

// ---------------------------------------------------------------- helpers
function phast(materialId, {gc, l0, displacement, increments = 50}) {
  return {solver: 'phast', model: 'phaseField', planeMode: 1, finiteStrain: false, increments, maxIncrements: increments, loadFactor: 1,
    fractureLoading: 'displacement', fractureDisplacement: displacement,
    materials: {[materialId]: {model: 'phaseField', fractureEnergy: gc, fractureLength: l0}}};
}
function j2(materials, {planeMode, increments = 20, maxIncrements = 200, finiteStrain = false}) {
  return {solver: 'calculix', model: 'plastic', planeMode, finiteStrain, increments, maxIncrements, loadFactor: 1, fractureLoading: 'forces',
    materials: Object.fromEntries(materials.map(([id, card]) => [id, deformationCard(card)]))};
}
// 2D blast settings for the OpenCourant chain (plane-strain slab, ALE borehole):
// the TNT JWL card of the explosive library detonated at the borehole center, the
// library air as the ideal gap gas (sourceMode 1), JH2 rock and quiet outer edges.
// Only keys of blast-settings.js are written; the time step is chosen by OpenCourant.
function tntBlast(over) {
  const tnt = explosives.find(e => e.id === 'tnt-user-parameter-image').settings;
  const air = gases.find(g => g.id === 'air-user-parameter-image').settings;
  const {airEOS, ...gas} = air;
  return {sourceMode: 1, ...tnt, ...gas, airEOS: 0, planeMode: 1, loadMode: 0, confineX: 0, confineY: 0, boundary: 2, rockModel: 3,
    pressure: 1e9, pulse: 2e-5, damping: 0, timeLimitSeconds: 1800, frames: 51, ...over};
}
const granite = () => lib('thesis43-granite');
function rect(s, x0, y0, x1, y1) { return s.polyline([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], {closed: true}); }

// ---------------------------------------------------------------- fracture
// Miehe, Hofacker & Welschinger (2010) single-edge notched specimens, scaled
// from 1 mm to 100 mm (drawing features must be larger than about 0.1 mm).
function mieheSteel() {
  // Tensile strength = AT2 critical stress sqrt(27 E Gc / (256 l0)) for l0 = 5 mm.
  return custom('classic-miehe-steel', '脆性基准材料（Miehe 2010 单边缺口试样）', {elasticModulus: 210, poissonRatio: 0.3, density: 7850, tensileStrength: 109, color: '#5b6b7a'},
    'Miehe, Hofacker, Welschinger (2010) CMAME 199:2765 单边缺口试样的材料参数：E = 210 GPa，ν = 0.3，Gc = 2.7 kN/m。试样按 100 倍放大为 100 mm 见方，相场长度 l₀ = 5 mm，抗拉强度取 AT2 临界应力 √(27EGc/256l₀) ≈ 109 MPa。仅用于脆性相场断裂演示。');
}
function notchedSquare(name) {
  // 2 mm slot with a 90° V tip at the centre: a thinner square-ended slit
  // leaves sliver triangles that stall PhAST's Newton iterations.
  const s = new Sketch(name), L = 0.1, w = 1 * mm, c = 0.05;
  const ids = s.polyline([[0, 0], [L, 0], [L, L], [0, L], [0, c + w], [c - w, c + w], [c, c], [c - w, c - w], [0, c - w]], {closed: true});
  return {s, ids};
}

// ---------------------------------------------------------------- blasting
function blastPlate(name, {half = 0.15, hole = [0, 0, 5 * mm], emptyHoles = []} = {}) {
  const s = new Sketch(name);
  const outer = rect(s, -half, -half, half, half);
  s.region('花岗岩岩体', outer, {material: granite()});
  s.region('炮孔', s.circle(hole[0], hole[1], hole[2], 8), {kind: 'air'});
  emptyHoles.forEach(([x, y, r], i) => s.region(`空孔 ${i + 1}`, s.circle(x, y, r, 8), {kind: 'air'}));
  return {s, outer};
}

module.exports = {
  // ================================================================ fracture
  sent() {
    const {s, ids} = notchedSquare('单边缺口拉伸-I型相场断裂');
    s.setState(ids[0], 'static');
    s.traction(ids[2], 1e6, [0, 1], '位移控制方向');
    s.region('单边缺口钢板', ids, {material: mieheSteel()});
    return {scene: s.scene(), maxNodes: 7000, deformationSettings: phast('classic-miehe-steel', {gc: 2700, l0: 5 * mm, displacement: 5.4e-5, increments: 50})};
  },
  sens() {
    const {s, ids} = notchedSquare('单边缺口剪切-II型相场断裂');
    const [bottom, right, top, leftTop, , , , , leftBottom] = ids;
    s.setState(bottom, 'static');
    s.setState([right, top, leftTop, leftBottom], 'static-y');
    s.traction(top, 1e6, [1, 0], '位移控制方向');
    s.region('单边缺口钢板', ids, {material: mieheSteel()});
    return {scene: s.scene(), maxNodes: 7000, deformationSettings: phast('classic-miehe-steel', {gc: 2700, l0: 5 * mm, displacement: 7.0e-5, increments: 50})};
  },
  senb() {
    // Petersson (1981) notched concrete beam, 2.1 m x 0.2 m, span 2.0 m, notch 0.1 m.
    const s = new Sketch('三点弯曲缺口混凝土梁-相场断裂');
    // 20 mm notch with a 90° V tip at 0.1 m depth (about two elements wide).
    const ids = s.polyline([[0, 0], [0.04, 0], [0.06, 0], [1.04, 0], [1.04, 0.09], [1.05, 0.1], [1.06, 0.09], [1.06, 0], [2.04, 0], [2.06, 0], [2.1, 0],
      [2.1, 0.2], [1.07, 0.2], [1.03, 0.2], [0, 0.2]], {closed: true});
    s.setState(ids[1], 'static');
    s.setState(ids[8], 'static-y');
    s.traction(ids[12], 1e6, [0, -1], '跨中加载');
    const concrete = custom('classic-petersson-concrete', '混凝土（Petersson 梁）', {elasticModulus: 30, poissonRatio: 0.2, density: 2400, tensileStrength: 3.33, compressiveStrength: 40, fractureEnergy: 124, color: '#9a9a8f'},
      'Petersson (1981) 三点弯曲缺口梁：E = 30 GPa，ν = 0.2，ft = 3.33 MPa，Gf = 124 N/m；梁长 2.1 m（跨距 2.0 m）、高 0.2 m、缺口深 0.1 m。');
    s.region('缺口混凝土梁', ids, {material: concrete});
    // l0 = 27 E Gc / (256 ft²) ≈ 35 mm makes the AT2 critical stress equal ft.
    return {scene: s.scene(), maxNodes: 4200, deformationSettings: phast('classic-petersson-concrete', {gc: 124, l0: 0.035, displacement: 7.0e-4, increments: 40})};
  },
  lpanel() {
    // Winkler (2001) L-shaped concrete panel, 500 mm, load 30 mm from the arm end.
    const s = new Sketch('L形混凝土板-混合型相场断裂');
    const ids = s.polyline([[0, 0], [0.25, 0], [0.25, 0.25], [0.46, 0.25], [0.48, 0.25], [0.5, 0.25], [0.5, 0.5], [0, 0.5]], {closed: true});
    s.setState(ids[0], 'static');
    s.traction(ids[3], 1e6, [0, 1], '向上加载');
    const concrete = custom('classic-winkler-concrete', '混凝土（Winkler L 形板）', {elasticModulus: 25.85, poissonRatio: 0.18, density: 2400, tensileStrength: 2.7, compressiveStrength: 31, fractureEnergy: 95, color: '#a3a093'},
      'Winkler, Hofstetter, Niederwanger (2001) L 形板试验：E = 25.85 GPa，ν = 0.18，ft = 2.7 MPa，Gf = 95 N/m。');
    s.region('L形混凝土板', ids, {material: concrete});
    // l0 = 26 mm (σc ≈ 3.2 MPa, close to ft = 2.7 MPa; the physical value 35 mm is too coarse for the corner).
    return {scene: s.scene(), maxNodes: 4800, deformationSettings: phast('classic-winkler-concrete', {gc: 95, l0: 0.026, displacement: 1.0e-3, increments: 50})};
  },
  brazil() {
    // Flattened Brazilian disc, D = 50 mm, loading angle 2α = 20°.
    const s = new Sketch('巴西劈裂圆盘-岩石相场断裂');
    const R = 0.025, a = 10 * deg;
    const right = s.arcs(0, 0, R, -90 * deg + a, 90 * deg - a, 2);
    const top = s.line([R * Math.cos(90 * deg - a), R * Math.sin(90 * deg - a)], [R * Math.cos(90 * deg + a), R * Math.sin(90 * deg + a)]);
    const left = s.arcs(0, 0, R, 90 * deg + a, 270 * deg - a, 2);
    const bottom = s.line([R * Math.cos(270 * deg - a), R * Math.sin(270 * deg - a)], [R * Math.cos(-90 * deg + a), R * Math.sin(-90 * deg + a)]);
    s.setState(bottom, 'static');
    s.traction(top, 1e6, [0, -1], '压板加载');
    s.region('花岗岩圆盘', [...right, top, ...left, bottom], {material: lib('mat-blanco-mera')});
    return {scene: s.scene(), maxNodes: 2600, deformationSettings: phast('mat-blanco-mera', {gc: 20.9, l0: 3.94 * mm, displacement: 4e-5, increments: 40})};
  },
  // Linear elastic Mode I / II centre-crack plates for the 2D statics workspace.
  modeI() {
    const s = new Sketch('一型裂纹');
    const h = 0.6, a = 0.12, b = 8 * mm;
    const outer = rect(s, -h, -h, h, h);
    s.point(-h, -h, 'static'); s.point(h, -h, 'static-y');
    s.traction(outer[2], 50e6, [0, 1], 'σ');
    s.traction(outer[0], 50e6, [0, -1], 'σ');
    s.region('Q235 钢板', outer, {material: lib('mat-q235-steel')});
    s.region('中心裂纹', [s.ellipseQuarter([a, 0], [0, b], [a, b]), s.ellipseQuarter([0, b], [-a, 0], [-a, b]), s.ellipseQuarter([-a, 0], [0, -b], [-a, -b]), s.ellipseQuarter([0, -b], [a, 0], [a, -b])], {kind: 'air'});
    return {scene: s.scene(), maxNodes: 12000, staticPlaneMode: 0};
  },
  modeII() {
    const s = new Sketch('二型裂纹');
    const h = 0.6, a = 0.12, b = 8 * mm;
    const [bottom, right, top, left] = rect(s, -h, -h, h, h);
    s.point(-h, -h, 'static'); s.point(h, -h, 'static-y');
    s.traction(top, 30e6, [1, 0], 'τ'); s.traction(bottom, 30e6, [-1, 0], 'τ');
    s.traction(right, 30e6, [0, 1], 'τ'); s.traction(left, 30e6, [0, -1], 'τ');
    s.region('Q235 钢板', [bottom, right, top, left], {material: lib('mat-q235-steel')});
    s.region('中心裂纹', [s.ellipseQuarter([a, 0], [0, b], [a, b]), s.ellipseQuarter([0, b], [-a, 0], [-a, b]), s.ellipseQuarter([-a, 0], [0, -b], [-a, -b]), s.ellipseQuarter([0, -b], [a, 0], [a, -b])], {kind: 'air'});
    return {scene: s.scene(), maxNodes: 12000, staticPlaneMode: 0};
  },

  // ================================================================ plasticity
  holePlate() {
    // Quarter of a 200 mm x 360 mm 6061-T6 strip with a 50 mm hole, plane stress.
    const s = new Sketch('带孔板单向拉伸-J2弹塑性');
    const r = 0.025, W = 0.1, H = 0.18;
    const bottom = s.line([r, 0], [W, 0], 'static-y');
    const right = s.line([W, 0], [W, H]);
    const top = s.line([W, H], [0, H]);
    const left = s.line([0, H], [0, r], 'static-x');
    const hole = s.arc([0, r], [r * Math.SQRT1_2, r * Math.SQRT1_2], [r, 0]);
    s.traction(top, 200e6, [0, 1], 'σ = 200 MPa');
    s.region('6061-T6 铝板（1/4 对称）', [bottom, right, top, left, hole], {material: lib('mat-al-6061-t6')});
    return {scene: s.scene(), maxNodes: 3000, deformationSettings: j2([['mat-al-6061-t6', 'def-6061-t6']], {planeMode: 0})};
  },
  thickCylinder() {
    // Lamé thick-walled cylinder a = 100 mm, b = 200 mm, internal pressure 170 MPa.
    const s = new Sketch('厚壁圆筒内压-J2弹塑性');
    const a = 0.1, b = 0.2, n = 8, p = 170e6;
    const bottom = s.line([a, 0], [b, 0], 'static-y');
    const outer = s.arcs(0, 0, b, 0, Math.PI / 2, 2);
    const left = s.line([0, b], [0, a], 'static-x');
    const inner = s.arcs(0, 0, a, Math.PI / 2, 0, n);
    inner.forEach((id, i) => { const t = Math.PI / 2 - (i + 0.5) * Math.PI / 2 / n; s.traction(id, p, [Math.cos(t), Math.sin(t)], 'p'); });
    s.region('Q235 厚壁圆筒（1/4 对称）', [bottom, ...outer, left, ...inner], {material: lib('mat-q235-steel')});
    return {scene: s.scene(), maxNodes: 3000, deformationSettings: j2([['mat-q235-steel', 'def-q235']], {planeMode: 1})};
  },
  beamHinge() {
    // Simply supported Q235 beam, span 2.0 m, depth 0.2 m; collapse load 4Mp/L = 4.7 MN/m.
    const s = new Sketch('简支梁塑性铰-J2弹塑性');
    const ids = s.polyline([[0, 0], [0.04, 0], [0.06, 0], [2.04, 0], [2.06, 0], [2.1, 0], [2.1, 0.2], [1.07, 0.2], [1.03, 0.2], [0, 0.2]], {closed: true});
    s.setState(ids[1], 'static');
    s.setState(ids[3], 'static-y');
    s.traction(ids[7], 4.5e6 / 0.04, [0, -1], 'P = 4.5 MN/m');
    s.region('Q235 钢梁', ids, {material: lib('mat-q235-steel')});
    return {scene: s.scene(), maxNodes: 4000, deformationSettings: j2([['mat-q235-steel', 'def-q235']], {planeMode: 0, increments: 25, maxIncrements: 250})};
  },
  prandtlPunch() {
    // Flexible flat punch on a J2 half-space, limit pressure (2 + π)k ≈ 698 MPa for Q235.
    const s = new Sketch('普朗特冲头压入-J2弹塑性');
    const ids = s.polyline([[-0.2, -0.2], [0.2, -0.2], [0.2, 0], [0.02, 0], [-0.02, 0], [-0.2, 0]], {closed: true});
    s.setState(ids[0], 'static');
    s.setState([ids[1], ids[5]], 'static-x');
    s.traction(ids[3], 660e6 * 0.04 / 0.04, [0, -1], 'p = 660 MPa');
    s.region('Q235 半空间', ids, {material: lib('mat-q235-steel')});
    return {scene: s.scene(), maxNodes: 6000, deformationSettings: j2([['mat-q235-steel', 'def-q235']], {planeMode: 1, increments: 30, maxIncrements: 300})};
  },

  // ================================================================ blasting (2D OpenCourant + MFEM)
  blastSingle() {
    const {s} = blastPlate('单孔耦合装药爆破-花岗岩JH2');
    return {scene: s.scene(), maxNodes: 15000, blastExplosiveId: 'tnt-user-parameter-image', blastGasId: 'air-user-parameter-image',
      blastSettings: tntBlast({x: 0, y: 0, radius: 5 * mm, chargeRadius: 4.9 * mm, duration: 1e-4})};
  },
  blastDecoupled() {
    const {s} = blastPlate('不耦合装药爆破-空气间隙-花岗岩JH2', {hole: [0, 0, 8 * mm]});
    return {scene: s.scene(), maxNodes: 15000, blastExplosiveId: 'tnt-user-parameter-image', blastGasId: 'air-user-parameter-image',
      blastSettings: tntBlast({x: 0, y: 0, radius: 8 * mm, chargeRadius: 4 * mm, duration: 1e-4})};
  },
  blastGuideHoles() {
    const {s} = blastPlate('空孔导向爆破-花岗岩JH2', {emptyHoles: [[-0.06, 0, 6 * mm], [0.06, 0, 6 * mm]]});
    return {scene: s.scene(), maxNodes: 15000, blastExplosiveId: 'tnt-user-parameter-image', blastGasId: 'air-user-parameter-image',
      blastSettings: tntBlast({x: 0, y: 0, radius: 5 * mm, chargeRadius: 4.9 * mm, duration: 1.2e-4})};
  },
  blastConfined() {
    const {s} = blastPlate('深部围压爆破-各向异性地应力-花岗岩JH2');
    return {scene: s.scene(), maxNodes: 15000, blastExplosiveId: 'tnt-user-parameter-image', blastGasId: 'air-user-parameter-image',
      blastSettings: tntBlast({x: 0, y: 0, radius: 5 * mm, chargeRadius: 4.9 * mm, duration: 1e-4, confineX: 10e6, confineY: 30e6, loadMode: 0})};
  },
  blastCrater() {
    const s = new Sketch('单自由面爆破漏斗-花岗岩JH2');
    const outer = rect(s, -0.2, -0.25, 0.2, 0);
    s.region('花岗岩岩体', outer, {material: granite()});
    s.region('炮孔', s.circle(0, -0.06, 5 * mm, 8), {kind: 'air'});
    return {scene: s.scene(), maxNodes: 15000, blastExplosiveId: 'tnt-user-parameter-image', blastGasId: 'air-user-parameter-image',
      blastBoundaryModes: {[outer[2]]: 1},
      blastSettings: tntBlast({x: 0, y: -0.06, radius: 5 * mm, chargeRadius: 4.9 * mm, duration: 1.5e-4, frames: 61})};
  },

  // ================================================================ fluid–structure (SU2)
  cylinderWake() {
    // Re = 150 vortex street behind an aluminium cylinder (D = 20 mm) with a fixed bore.
    const s = new Sketch('圆柱绕流-二维瞬态流固耦合');
    const D = 0.02, cy = 0.002;
    const [bottom, right, top, left] = rect(s, -0.1, -0.08, 0.4, 0.08);
    s.region('空气流道', [bottom, right, top, left]);
    s.region('铝合金圆柱', s.circle(0, cy, D / 2, 4), {material: lib('mat-al-6061-t6')});
    s.region('固定轴孔', s.circle(0, cy, 4 * mm, 4, {state: 'static'}), {kind: 'air'});
    const air = fluid('fluid-air-20c-low-speed');
    return {scene: s.scene(), gmsh: {size: 0.008, fields: [
      {type: 'Ball', XCenter: 0, YCenter: cy, Radius: 0.013, Thickness: 0.03, VIn: 0.0008, VOut: 0.008},
      {type: 'Box', XMin: 0, XMax: 0.4, YMin: -0.03, YMax: 0.034, Thickness: 0.03, VIn: 0.0025, VOut: 0.008}]},
    fsiSettings: {roles: {R1: 'fluid', R2: 'solid'}, fluidId: air.id, fluid: air,
      boundaries: {[left]: {kind: 'inlet', velocity: 0.113}, [right]: {kind: 'outlet', pressure: 0}, [top]: {kind: 'slip'}, [bottom]: {kind: 'slip'}},
      form: {engine: 'su2', analysis: 'transient', structure: 'linear', plane: 'strain', turbulence: 'none', outerIterations: 2, fluidIterations: 10, solidIterations: 3,
        relaxation: 'aitken', relaxationFactor: 0.5, timeStep: 0.025, steps: 400, frames: 81, threads: 8, convergence: -6, referencePressure: 101325}}};
  },
  backwardStep() {
    // Expansion ratio 2, step S = 30 mm, Re_S = 450, 5S upstream and 30S downstream.
    const s = new Sketch('后台阶回流-二维流固耦合');
    const inlet = s.line([-0.15, 0.06], [-0.15, 0.03]);
    const upstreamWall = s.line([-0.15, 0.03], [0, 0.03]);
    const stepFace = s.line([0, 0.03], [0, 0]);
    const floor = s.line([0, 0], [0.9, 0]);
    const outlet = s.line([0.9, 0], [0.9, 0.06]);
    const ceiling = s.line([0.9, 0.06], [-0.15, 0.06]);
    s.region('台阶前后水流', [inlet, upstreamWall, stepFace, floor, outlet, ceiling]);
    const plateBottom = s.line([0, -0.009], [0.9, -0.009], 'static');
    s.region('下游铝合金底板', [floor, s.line([0.9, 0], [0.9, -0.009]), plateBottom, s.line([0, -0.009], [0, 0])], {material: lib('mat-al-6061-t6')});
    const water = fluid('fluid-water-20c');
    return {scene: s.scene(), gmsh: {size: 0.004, fields: [
      {type: 'Box', XMin: -0.02, XMax: 0.35, YMin: -0.01, YMax: 0.06, Thickness: 0.05, VIn: 0.002, VOut: 0.004}]},
    fsiSettings: {roles: {R1: 'fluid', R2: 'solid'}, fluidId: water.id, fluid: water,
      boundaries: {[inlet]: {kind: 'inlet', velocity: 0.015}, [outlet]: {kind: 'outlet', pressure: 0}},
      form: {engine: 'oneway', analysis: 'steady', structure: 'linear', plane: 'strain', turbulence: 'none', outerIterations: 1, fluidIterations: 2500,
        solidIterations: 3, relaxation: 'aitken', relaxationFactor: 0.5, timeStep: 0.01, steps: 100, frames: 21, threads: 8, convergence: -6, referencePressure: 101325}}};
  },
  venturi() {
    // Classical Venturi tube: D = 50 mm, throat d = 25 mm, 21° inlet cone, 7° diffuser.
    const s = new Sketch('文丘里管-伯努利原理-二维流固耦合');
    const xs = [0, 0.1, 0.1 + 0.0125 / Math.tan(21 * deg), 0.1 + 0.0125 / Math.tan(21 * deg) + 0.03];
    xs.push(xs[3] + 0.0125 / Math.tan(7 * deg), xs[3] + 0.0125 / Math.tan(7 * deg) + 0.15);
    const hy = [0.025, 0.025, 0.0125, 0.0125, 0.025, 0.025], wall = 0.035, end = xs[5];
    const inlet = s.line([0, 0.025], [0, -0.025]);
    const lower = xs.slice(0, 5).map((x, i) => s.line([x, -hy[i]], [xs[i + 1], -hy[i + 1]]));
    const outlet = s.line([end, -0.025], [end, 0.025]);
    const upper = xs.slice(0, 5).map((x, i) => s.line([xs[5 - i], hy[5 - i]], [xs[4 - i], hy[4 - i]]));
    s.region('液压油', [inlet, ...lower, outlet, ...upper]);
    const steel = lib('mat-q235-steel');
    s.region('上管壁', [...upper, s.line([0, 0.025], [0, wall]), s.line([0, wall], [end, wall], 'static'), s.line([end, wall], [end, 0.025])], {material: steel});
    s.region('下管壁', [...lower, s.line([end, -0.025], [end, -wall]), s.line([end, -wall], [0, -wall], 'static'), s.line([0, -wall], [0, -0.025])], {material: steel});
    const oil = fluid('fluid-hydraulic-oil-vg46');
    return {scene: s.scene(), gmsh: {size: 0.002, fields: [
      {type: 'Box', XMin: 0.09, XMax: 0.28, YMin: -0.04, YMax: 0.04, Thickness: 0.04, VIn: 0.0013, VOut: 0.002}]},
    fsiSettings: {roles: {R1: 'fluid', R2: 'solid', R3: 'solid'}, fluidId: oil.id, fluid: oil,
      boundaries: {[inlet]: {kind: 'inlet', velocity: 1.0}, [outlet]: {kind: 'outlet', pressure: 0}},
      form: {engine: 'oneway', analysis: 'steady', structure: 'linear', plane: 'strain', turbulence: 'none', outerIterations: 1, fluidIterations: 2000,
        solidIterations: 3, relaxation: 'aitken', relaxationFactor: 0.5, timeStep: 0.01, steps: 100, frames: 21, threads: 8, convergence: -6, referencePressure: 101325}}};
  },
  turekHron() {
    // Turek & Hron (2006) FSI2 benchmark: elastic flap behind a rigid cylinder, Re = 100.
    const s = new Sketch('Turek-Hron柔性尾板涡激振动-二维瞬态流固耦合');
    const [bottom, right, top, left] = rect(s, 0, 0, 2.5, 0.41);
    s.region('流道', [bottom, right, top, left]);
    const cx = 0.2, cy = 0.2, r = 0.05, x0 = cx + Math.sqrt(r * r - 0.01 * 0.01), t = Math.asin(0.01 / r);
    const attach = s.arc([x0, 0.19], [cx + r, cy], [x0, 0.21], 'static');
    const cyl = s.arcs(cx, cy, r, t, 2 * Math.PI - t, 2);
    s.region('刚性圆柱', [attach, ...cyl], {kind: 'air'});
    const flap = [attach, s.line([x0, 0.21], [0.6, 0.21]), s.line([0.6, 0.21], [0.6, 0.19]), s.line([0.6, 0.19], [x0, 0.19])];
    const rubber = custom('classic-turek-hron-fsi2', '弹性尾板（Turek–Hron FSI2）', {elasticModulus: 0.0014, poissonRatio: 0.4, density: 10000, color: '#e07a3f'},
      'Turek & Hron (2006) FSI2：ρs = 10000 kg/m³，μs = 0.5 MPa，νs = 0.4（E = 1.4 MPa）。');
    s.region('弹性尾板', flap, {material: rubber});
    const benchmarkFluid = {id: 'classic-turek-hron-fluid', name: 'Turek–Hron 基准流体', category: 'liquid', model: 'incompressible', density: 1000, viscosity: 1,
      color: '#7fb8d8', notes: 'Turek & Hron (2006) FSI2：ρf = 1000 kg/m³，νf = 1e-3 m²/s。', source: 'Turek, Hron (2006) Lecture Notes in Computational Science and Engineering 53'};
    return {scene: s.scene(), gmsh: {size: 0.02, fields: [
      {type: 'Ball', XCenter: cx, YCenter: cy, Radius: 0.065, Thickness: 0.08, VIn: 0.004, VOut: 0.02},
      {type: 'Box', XMin: 0.23, XMax: 0.62, YMin: 0.17, YMax: 0.23, Thickness: 0.06, VIn: 0.0035, VOut: 0.02},
      {type: 'Box', XMin: 0.2, XMax: 1.2, YMin: 0.06, YMax: 0.34, Thickness: 0.15, VIn: 0.009, VOut: 0.02}]},
    fsiSettings: {roles: {R1: 'fluid', R3: 'solid'}, fluidId: benchmarkFluid.id, fluid: benchmarkFluid,
      boundaries: {[left]: {kind: 'inlet', velocity: 1.0}, [right]: {kind: 'outlet', pressure: 0}},
      form: {engine: 'su2', analysis: 'transient', structure: 'neohookean', plane: 'strain', turbulence: 'none', outerIterations: 4, fluidIterations: 10, solidIterations: 8,
        relaxation: 'aitken', relaxationFactor: 0.5, timeStep: 0.005, steps: 1200, frames: 121, threads: 8, convergence: -6, referencePressure: 101325}}};
  },
  // ================================================================ structural dynamics (2D)
  // Euler–Bernoulli reference: f1 = (1.875²/2π)·√(EI/ρA)/L² = 81.5 Hz for Q235 (E = 200 GPa), L = 1 m, h = 0.1 m.
  cantileverModal() {
    const s = new Sketch('悬臂梁模态分析-二维-动力学-线弹性');
    const [bottom, right, top, left] = rect(s, 0, 0, 1, 0.1);
    s.setState(left, 'static');
    s.region('钢制悬臂梁', [bottom, right, top, left], {material: lib('mat-q235-steel')});
    return {scene: s.scene(), maxNodes: 900,
      dynamicsSettings: {analysis: 'modal', form: {planeMode: 0, elementOrder: 'quadratic', threads: 0, modes: 8}}};
  },
  cantileverHarmonic() {
    // Tip force 1 kN/m: static deflection FL³/3EI = 2.0e-5 m, resonance amplitude ≈ static / 2ζ.
    const s = new Sketch('悬臂梁端部激振谐响应-二维-动力学-线弹性');
    const [bottom, right, top, left] = rect(s, 0, 0, 1, 0.1);
    s.setState(left, 'static');
    s.region('钢制悬臂梁', [bottom, right, top, left], {material: lib('mat-q235-steel')});
    s.force([1, 0.1], 0, -1000, 'F₀ sin(2πft)');
    return {scene: s.scene(), maxNodes: 900,
      dynamicsSettings: {analysis: 'harmonic', form: {planeMode: 0, elementOrder: 'quadratic', threads: 0, freqMin: 5, freqMax: 1500, freqPoints: 20, dampingRatio: 0.02, harmonicModes: 10}}};
  },
  beamImpact() {
    // Simply supported steel beam, 2 m span, 50 kN/m half-sine pulse of 2 ms at mid-span (T1 ≈ 1/(π/2·√(EI/ρA)/L²) ≈ 0.025 s).
    const s = new Sketch('简支梁跨中冲击瞬态-二维-动力学-线弹性');
    const ids = s.polyline([[0, 0], [1, 0], [2, 0], [2, 0.1], [1, 0.1], [0, 0.1]], {closed: true});
    s.point(0, 0, 'static'); s.point(2, 0, 'static-y');
    s.region('钢梁', ids, {material: lib('mat-q235-steel')});
    s.force([1, 0.1], 0, -50000, 'P(t)');
    return {scene: s.scene(), maxNodes: 1400,
      dynamicsSettings: {analysis: 'transient', form: {planeMode: 0, elementOrder: 'quadratic', threads: 0, transientMethod: 'modal', transientModes: 30,
        endTime: 0.06, timeStep: 0.0001, frames: 61, rayleighAlpha: 0, rayleighBeta: 2e-5},
        load: {shape: 'halfsine', factor: 1, duration: 0.002}}};
  },
  diskCollision() {
    // Newton's cradle in plane strain: a steel cylinder at 10 m/s hits an identical one at rest.
    const s = new Sketch('圆盘对心碰撞-二维-动力学-线弹性');
    const r = 0.05;
    s.region('钢圆盘 A（运动）', s.circle(0, 0, r, 4), {material: lib('mat-q235-steel')});
    s.region('钢圆盘 B（静止）', s.circle(2 * r + 0.002, 0, r, 4), {material: lib('mat-q235-steel')});
    return {scene: s.scene(), maxNodes: 1600,
      dynamicsSettings: {analysis: 'explicit', form: {planeMode: 1, threads: 0, explicitEndTime: 0.0008, explicitFrames: 81, timeStepScale: 0.67, friction: 0, contact: true, selfContact: false, explicitLoads: false},
        cards: {'mat-q235-steel': {model: 'elastic'}}, partVelocityAt: [{point: [0, 0], velocity: [10, 0, 0]}]}};
  },
  ringCrush() {
    // Aluminium ring (outer radius 50 mm, wall 5 mm) driven at 30 m/s into a rigid wall: plastic hinges and crushing.
    const s = new Sketch('铝环撞刚性墙压溃-二维-动力学-双线性弹塑性');
    const outer = s.circle(0, 0, 0.05, 4), inner = s.circle(0, 0, 0.045, 4);
    s.region('6061-T6 铝环', outer, {material: lib('mat-al-6061-t6')});
    s.region('环内空腔', inner, {kind: 'air'});
    return {scene: s.scene(), maxNodes: 2600,
      // The thin ring needs sub-millimetre elements, so Δt is about 2e-8 s (no mass scaling: it would add >400 % mass here).
      dynamicsSettings: {analysis: 'explicit', form: {planeMode: 1, threads: 0, explicitEndTime: 0.002, explicitFrames: 41, timeStepScale: 0.67, minTimeStep: 0,
        friction: 0.1, contact: true, selfContact: true, explicitLoads: false},
        cards: {'mat-al-6061-t6': {model: 'plastic', yieldStress: 276e6, tangentModulus: 910e6, failureStrain: 0}},
        walls: [{point: [0.052, 0, 0], normal: [-1, 0, 0], friction: 0.1}], partVelocityAt: [{point: [0, 0.0475], velocity: [30, 0, 0]}]}};
  },
  supersonicWedge() {
    // Mach 2 inviscid flow over a 15° compression ramp: oblique shock at β ≈ 45.3°.
    const s = new Sketch('超声速楔形斜激波-二维流固耦合');
    const tip = 0.2, L = 1.0, H = 0.5, hEnd = (L - tip) * Math.tan(15 * deg);
    const floor = s.line([0, 0], [tip, 0]);
    const ramp = s.line([tip, 0], [L, hEnd]);
    const outlet = s.line([L, hEnd], [L, H]);
    const top = s.line([L, H], [0, H]);
    const inflow = s.line([0, H], [0, 0]);
    s.region('超声速空气', [floor, ramp, outlet, top, inflow]);
    s.region('钢制楔形体', [ramp, s.line([L, hEnd], [L, 0]), s.line([L, 0], [tip, 0], 'static')], {material: lib('mat-q235-steel')});
    const air = {id: 'classic-air-inviscid', name: '空气（无黏 Euler，20 °C）', category: 'gas', model: 'idealgas', density: 1.204, viscosity: 0, gamma: 1.4,
      gasConstant: 287.058, temperature: 293.15, color: '#d6ecf5', notes: '无黏理想气体，用于超声速 Euler 计算。', source: 'U.S. Standard Atmosphere 1976'};
    const v = 2 * Math.sqrt(1.4 * 287.058 * 293.15);
    return {scene: s.scene(), gmsh: {size: 0.008, fields: [
      {type: 'Box', XMin: 0.15, XMax: 1.0, YMin: 0, YMax: 0.5, Thickness: 0.05, VIn: 0.006, VOut: 0.008}]},
    fsiSettings: {roles: {R1: 'fluid', R2: 'solid'}, fluidId: air.id, fluid: air,
      boundaries: {[inflow]: {kind: 'farfield', velocity: +v.toFixed(2), angle: 0}, [top]: {kind: 'farfield', velocity: +v.toFixed(2), angle: 0},
        [outlet]: {kind: 'farfield', velocity: +v.toFixed(2), angle: 0}, [floor]: {kind: 'slip'}},
      form: {engine: 'oneway', analysis: 'steady', structure: 'linear', plane: 'strain', turbulence: 'none', outerIterations: 1, fluidIterations: 2000,
        solidIterations: 3, relaxation: 'aitken', relaxationFactor: 0.5, timeStep: 0.01, steps: 100, frames: 21, threads: 8, convergence: -7, referencePressure: 101325}}};
  },
};
