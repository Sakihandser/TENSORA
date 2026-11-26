'use strict';
// 3D classic models (m, N, Pa). Each entry returns CAD features, a uniform
// Gmsh size and an assign(h) step that picks volumes and CAD faces on the
// generated mesh and returns the workspace snapshot pieces.
const path = require('node:path');
const fluids = require(path.join(__dirname, '..', '..', 'fluids', 'library.json')).fluids;
const fluid = id => ({...fluids.find(f => f.id === id)});
const S = value => String(value);
const box = (x, y, z, dx, dy, dz, extra = {}) => ({type: 'box', x, y, z, dx, dy, dz, ...extra});

const water = () => ({id: 'fsi-classic-water', name: '水（ρ = 1000 kg/m³）', category: 'liquid', model: 'incompressible', density: 1000, viscosity: 0.001,
  bulkModulus: 2.2e9, color: '#76c9e7'});
const rubber = (id, name, E) => ({id, name, elasticModulus: E, poissonRatio: 0.45, density: 1100, color: '#ed9b4c',
  notes: '演示用软橡胶，线弹性等效参数。', sourceUrl: '', sourceUrls: []});
const sphForm = over => ({solid3dFsiEngineSelect: 'sph', solid3dFsiSphVx: '0', solid3dFsiSphVy: '0', solid3dFsiSphVz: '0', solid3dFsiSphGx: '0', solid3dFsiSphGy: '-9.81',
  solid3dFsiSphGz: '0', solid3dFsiSphSound: '0', solid3dFsiSphDtScale: '0.6', solid3dFsiSphMassScaling: 'off', solid3dFsiSphMinDt: '0.00001', solid3dFsiThreads: '8', ...over});
const blastForm = over => ({solid3dBlastSource: 'jwl', solid3dBlastPeak: '200', solid3dBlastDuration: '100', solid3dBlastShape: 'sine', solid3dBlastRise: '10',
  solid3dBlastDetMode: 'custom', solid3dBlastDetTime: '0', solid3dBlastInitial: 'none', solid3dBlastLayer: '0', solid3dBlastDtScale: '0.6', solid3dBlastThreads: '8', ...over});
const fixedAll = surface => ({type: 'fixed', surface, axes: [true, true, true]});

module.exports = {
  // ================================================================ fluid (3D)
  damBreak() {
    // Dam break against a soft rubber plate (OpenCourant SPH), after the FSI.md regression case.
    const L = 0.4, H = 0.2, W = 0.04;
    return {name: '溃坝冲击挡板-三维SPH流固耦合', meshSize: 0.008,
      shapes: [box(0, 0, 0, L, H, W), box(0, 0, 0, 0.1, 0.12, W), box(0.244, 0, 0, 0.012, 0.08, W)],
      embeddedMaterials: [rubber('fsi-classic-rubber', '演示用软橡胶（E = 5 MPa）', 0.005)],
      assign(h) {
        const waterV = h.volumeAt(0.05, 0.06, 0.02), plate = h.volumeAt(0.25, 0.04, 0.02), cavity = h.mesh.volumes.map(v => S(v.id)).find(id => id !== waterV && id !== plate);
        const base = h.plane(1, 0, {volume: plate});
        return {volumeMaterials: {[plate]: 'fsi-classic-rubber'}, conditions: base.map(fixedAll),
          fsi3d: {roles: {[waterV]: 'fluid', [plate]: 'solid', [cavity]: 'void'}, faces: {}, fluidId: 'fsi-classic-water', fluid: water(),
            form: sphForm({solid3dFsiSphEnd: '0.35', solid3dFsiSphFrames: '36'})},
          report: `water ${waterV} plate ${plate} cavity ${cavity} base faces ${base}`};
      }};
  },
  sloshing() {
    // Liquid sloshing in a tank given an initial horizontal velocity, with an elastic bottom baffle.
    const L = 0.6, H = 0.3, W = 0.04, depth = 0.12, t = 0.015;
    return {name: '液舱晃荡与弹性挡板-三维SPH流固耦合', meshSize: 0.01,
      shapes: [box(0, 0, 0, L, H, W), box(0, 0, 0, L, depth, W), box(L / 2 - t / 2, 0, 0, t, 0.07, W)],
      embeddedMaterials: [rubber('classic-baffle-rubber', '挡板橡胶（E = 20 MPa）', 0.02)],
      assign(h) {
        const baffle = h.volumeAt(L / 2, 0.035, W / 2);
        const fluidVolumes = h.mesh.volumes.filter(v => S(v.id) !== baffle && v.centroid[1] < depth).map(v => S(v.id));
        const cavity = h.mesh.volumes.filter(v => S(v.id) !== baffle && v.centroid[1] >= depth).map(v => S(v.id));
        const roles = {[baffle]: 'solid'};
        for (const id of fluidVolumes) roles[id] = 'fluid';
        for (const id of cavity) roles[id] = 'void';
        return {volumeMaterials: {[baffle]: 'classic-baffle-rubber'}, conditions: h.plane(1, 0, {volume: baffle}).map(fixedAll),
          fsi3d: {roles, faces: {}, fluidId: 'fsi-classic-water', fluid: water(),
            form: sphForm({solid3dFsiSphEnd: '1.2', solid3dFsiSphFrames: '61', solid3dFsiSphVx: '0.6'})},
          report: `fluid ${fluidVolumes} cavity ${cavity} baffle ${baffle}`};
      }};
  },
  reynoldsPipe() {
    // Laminar pipe flow (Re = 400): D = 20 mm water pipe with a 3 mm aluminium wall, L = 20 D.
    const L = 0.4, r = 0.01, R = 0.013;
    return {name: '雷诺实验-三维圆管管流', meshSize: 0.0022,
      shapes: [{type: 'cylinder', radius: R, height: L, ry: 90}, {type: 'cylinder', radius: r, height: L, ry: 90}],
      assign(h) {
        // Both fragments are centred on the axis; the fluid core owns the small end disks.
        const fluidV = h.faces.find(f => f.planarAxis === 0 && f.max[1] < r + 1e-6).volumeId;
        const wall = h.mesh.volumes.map(v => S(v.id)).find(id => id !== fluidV);
        const inlet = h.plane(0, 0, {volume: fluidV}).filter(id => h.faces.find(f => f.id === id).max[1] < r + 1e-6);
        const outlet = h.plane(0, L, {volume: fluidV}).filter(id => h.faces.find(f => f.id === id).max[1] < r + 1e-6);
        const ends = [...h.plane(0, 0), ...h.plane(0, L)].filter(id => !inlet.includes(id) && !outlet.includes(id));
        const faces = {};
        for (const id of inlet) faces[id] = {kind: 'inlet', velocity: 0.02};
        for (const id of outlet) faces[id] = {kind: 'outlet', pressure: 0};
        return {volumeMaterials: {[wall]: 'mat-al-6061-t6'}, conditions: ends.map(fixedAll),
          sectionView: {mode: 'context', planes: [{orientation: 'XY', point: [L / 2, 0, 0], normal: [0, 0, 1], number: 1, visible: true}]},
          fsi3d: {roles: {[fluidV]: 'fluid', [wall]: 'solid'}, faces, fluidId: 'fluid-water-20c', fluid: fluid('fluid-water-20c'),
            form: {solid3dFsiEngineSelect: 'oneway', solid3dFsiAnalysis: 'steady', solid3dFsiStructure: 'linear', solid3dFsiTurbulence: 'none', solid3dFsiReference: '101325',
              solid3dFsiOuter: '1', solid3dFsiFluidIter: '1200', solid3dFsiThreads: '8', solid3dFsiConvergence: '-7', solid3dFsiFlowCfl: '', solid3dFsiFlowOrder: 'second'}},
          report: `fluid ${fluidV} wall ${wall} inlet ${inlet} outlet ${outlet} ends ${ends}`};
      }};
  },

  // ================================================================ blasting (3D OpenCourant)
  benchBlast() {
    // Granite bench, burden 80 mm, 30 mm hole with a JWL TNT column initiated at the bottom.
    const Z = 0.2, hx = 0.22, r = 0.015, bottom = 0.17;
    return {name: '台阶爆破-三维JWL装药-花岗岩JH2', meshSize: 0.01,
      shapes: [{type: 'extrusion', featureId: 'bench', polygon: [[0, 0], [0.5, 0], [0.5, 0.2], [0.3, 0.2], [0.3, 0.5], [0, 0.5]], plane: 'XY', z: 0, height: Z, materialId: 'thesis43-granite'},
        {type: 'cylinder', featureId: 'hole', operation: 'cut', cutTarget: 'bench', radius: r, height: 0.5 - bottom, rx: -90, x: hx, y: bottom, z: Z / 2},
        {type: 'cylinder', featureId: 'charge', radius: r, height: 0.25, rx: -90, x: hx, y: bottom, z: Z / 2}],
      assign(h) {
        const charge = h.volumeAt(hx, bottom + 0.125, Z / 2), rock = h.mesh.volumes.map(v => S(v.id)).find(id => id !== charge);
        const absorb = [...h.plane(1, 0, {volume: rock}), ...h.plane(0, 0, {volume: rock}), ...h.plane(2, 0, {volume: rock}), ...h.plane(2, Z, {volume: rock})];
        // The bench base rests on the rock foundation; the damping layer still absorbs waves there.
        return {volumeMaterials: {[rock]: 'thesis43-granite'}, conditions: h.plane(1, 0, {volume: rock}).map(fixedAll),
          blast3d: {form: blastForm({solid3dBlastDetX: S(hx), solid3dBlastDetY: S(bottom + 0.01), solid3dBlastDetZ: S(Z / 2), solid3dBlastEnd: '400', solid3dBlastFrames: '41'}),
            explosiveId: 'tnt-user-parameter-image', roles: {[rock]: 'rock', [charge]: 'charge'}, wallFaces: [], absorbFaces: absorb},
          report: `rock ${rock} charge ${charge} absorb ${absorb}`};
      }};
  },
  slabContact() {
    // Quarter of a 1 m x 1 m x 0.1 m C30 slab under a 100 x 100 x 40 mm contact TNT charge.
    return {name: '混凝土板接触爆炸-三维JWL-HJC', meshSize: 0.0125,
      shapes: [box(0, 0, 0, 0.5, 0.1, 0.5), box(0, 0.1, 0, 0.05, 0.04, 0.05)],
      assign(h) {
        const charge = h.volumeAt(0.025, 0.12, 0.025), slab = h.mesh.volumes.map(v => S(v.id)).find(id => id !== charge);
        const symX = h.plane(0, 0), symZ = h.plane(2, 0), clamp = [...h.plane(0, 0.5), ...h.plane(2, 0.5)];
        return {volumeMaterials: {[slab]: 'mat-c30-concrete'},
          conditions: [...symX.map(surface => ({type: 'fixed', surface, axes: [true, false, false]})), ...symZ.map(surface => ({type: 'fixed', surface, axes: [false, false, true]})), ...clamp.map(fixedAll)],
          blast3d: {form: blastForm({solid3dBlastDetX: '0', solid3dBlastDetY: '0.12', solid3dBlastDetZ: '0', solid3dBlastEnd: '300', solid3dBlastFrames: '31'}),
            explosiveId: 'tnt-user-parameter-image', roles: {[slab]: 'rock', [charge]: 'charge'}, wallFaces: [], absorbFaces: []},
          report: `slab ${slab} charge ${charge} symX ${symX} symZ ${symZ} clamp ${clamp}`};
      }};
  },
  steelPlate() {
    // Quarter of a clamped 400 x 400 x 8 mm Q235 plate with a 50 x 50 x 12 mm contact TNT charge (Johnson–Cook).
    return {name: '钢板接触爆炸鼓包-三维JWL-Johnson-Cook', meshSize: 0.004,
      shapes: [box(0, 0, 0, 0.2, 0.008, 0.2), box(0, 0.008, 0, 0.025, 0.012, 0.025)],
      assign(h) {
        const charge = h.volumeAt(0.0125, 0.014, 0.0125), plate = h.mesh.volumes.map(v => S(v.id)).find(id => id !== charge);
        const symX = h.plane(0, 0), symZ = h.plane(2, 0), clamp = [...h.plane(0, 0.2), ...h.plane(2, 0.2)];
        return {volumeMaterials: {[plate]: 'mat-q235-steel'},
          conditions: [...symX.map(surface => ({type: 'fixed', surface, axes: [true, false, false]})), ...symZ.map(surface => ({type: 'fixed', surface, axes: [false, false, true]})), ...clamp.map(fixedAll)],
          blast3d: {form: blastForm({solid3dBlastDetX: '0', solid3dBlastDetY: '0.02', solid3dBlastDetZ: '0', solid3dBlastEnd: '500', solid3dBlastFrames: '51'}),
            explosiveId: 'tnt-user-parameter-image', roles: {[plate]: 'rock', [charge]: 'charge'}, wallFaces: [], absorbFaces: []},
          report: `plate ${plate} charge ${charge} symX ${symX} symZ ${symZ} clamp ${clamp}`};
      }};
  },

  // ================================================================ plasticity / fracture (3D)
  holePlate3d() {
    // 360 x 200 x 10 mm 6061-T6 plate with a 50 mm hole, end traction 200 MPa (CalculiX C3D4, J2).
    return {name: '三维带孔板拉伸-J2弹塑性', meshSize: 0.006,
      shapes: [box(0, 0, 0, 0.36, 0.2, 0.01, {featureId: 'plate'}), {type: 'cylinder', featureId: 'hole', operation: 'cut', radius: 0.025, height: 0.01, x: 0.18, y: 0.1, z: 0}],
      assign(h) {
        const plate = S(h.mesh.volumes[0].id), fixedEnd = h.plane(0, 0), loaded = h.plane(0, 0.36);
        return {volumeMaterials: {[plate]: 'mat-al-6061-t6'},
          conditions: [...fixedEnd.map(fixedAll), ...loaded.map(surface => ({type: 'traction', surface, fx: 200e6, fy: 0, fz: 0}))],
          report: `fixed ${fixedEnd} loaded ${loaded}`};
      }};
  },
  brazil3d() {
    // ISRM-type flattened Brazilian disc, D = 50 mm, t = 25 mm, granite crack-band card (OOFEM).
    const R = 0.025, yf = R * Math.cos(10 * Math.PI / 180);
    return {name: '三维巴西劈裂-岩石裂带断裂', meshSize: 0.0025,
      shapes: [{type: 'cylinder', featureId: 'disc', radius: R, height: 0.025},
        box(-0.03, yf, -0.01, 0.06, 0.02, 0.045, {operation: 'cut'}), box(-0.03, -yf - 0.02, -0.01, 0.06, 0.02, 0.045, {operation: 'cut'})],
      assign(h) {
        const disc = S(h.mesh.volumes[0].id), top = h.plane(1, yf, {tol: 1e-5}), bottom = h.plane(1, -yf, {tol: 1e-5});
        return {volumeMaterials: {[disc]: 'mat-blanco-mera'},
          conditions: [...bottom.map(fixedAll), ...top.map(surface => ({type: 'force', surface, fx: 0, fy: -12000, fz: 0}))],
          report: `top ${top} bottom ${bottom}`};
      }};
  },
  fourPointBeam() {
    // C30 beam 600 x 100 x 100 mm, span 500 mm, loads at the third points (Mazars, Code_Aster).
    const pad = (x, y) => box(x - 0.01, y, 0, 0.02, 0.01, 0.1);
    return {name: '混凝土四点弯曲梁-三维Mazars损伤', meshSize: 0.0125,
      shapes: [box(0, 0, 0, 0.6, 0.1, 0.1), pad(0.05, -0.01), pad(0.55, -0.01), pad(0.05 + 0.5 / 3, 0.1), pad(0.55 - 0.5 / 3, 0.1)],
      assign(h) {
        const all = h.mesh.volumes.map(v => S(v.id)), materials = Object.fromEntries(all.map(id => [id, 'mat-c30-concrete']));
        const left = h.plane(1, -0.01, {within: [[0, -1, -1], [0.1, 1, 1]]}), right = h.plane(1, -0.01, {within: [[0.5, -1, -1], [0.6, 1, 1]]});
        const loads = h.plane(1, 0.11);
        return {volumeMaterials: materials,
          conditions: [...left.map(fixedAll), ...right.map(surface => ({type: 'fixed', surface, axes: [false, true, true]})),
            ...loads.map(surface => ({type: 'force', surface, fx: 0, fy: -3000, fz: 0}))],
          report: `volumes ${all} left ${left} right ${right} loads ${loads}`};
      }};
  },
  // ================================================================ structural dynamics (3D)
  ballCollision3d() {
    // Newton's cradle: a steel ball (r = 50 mm) at 10 m/s hits an identical ball at rest; Hertz contact lasts about 0.2 ms.
    const r = 0.05;
    return {name: '钢球对心碰撞-三维-动力学-线弹性', meshSize: 0.009,
      shapes: [{type: 'sphere', radius: r, x: 0, y: 0, z: 0}, {type: 'sphere', radius: r, x: 2 * r + 0.002, y: 0, z: 0}],
      assign(h) {
        const a = h.volumeAt(0, 0, 0), b = h.volumeAt(2 * r + 0.002, 0, 0);
        return {volumeMaterials: {[a]: 'mat-q235-steel', [b]: 'mat-q235-steel'},
          dynamics3d: dynamicsSnapshot(h, {solid3dDynAnalysis: 'explicit', solid3dDynExplicitEnd: '0.0008', solid3dDynExplicitFrames: '81', solid3dDynFriction: '0'},
            {velocityAt: [{point: [-r, 0, 0], velocity: [10, 0, 0]}], cards: {'mat-q235-steel': {model: 'elastic'}}}),
          report: `balls ${a} ${b}`};
      }};
  },
  carCrash3d() {
    // Simplified vehicle front at 15 m/s (54 km/h) into a rigid wall: a stiff body block carrying 180 kg,
    // a 6061-T6 crash box (60 × 60 mm square tube, 5 mm wall, 180 mm long) and a 10 mm bumper plate.
    // Kinetic energy ≈ 21 kJ against a tube squash load σy·A ≈ 300 kN: the crash box crushes by several centimetres.
    const body = {id: 'classic-car-body', name: '等效车身质量块（180 kg）', elasticModulus: 200, poissonRatio: 0.3, density: 6000, color: '#5b7c99',
      notes: '简化车身：钢的刚度，密度按 0.5 × 0.3 × 0.2 m 块体折算为 180 kg。用于吸能盒撞墙演示，不代表实车结构。', sourceUrl: '', sourceUrls: []};
    return {name: '汽车撞刚性墙-三维-动力学-双线性弹塑性', meshSize: 0.03,
      meshRefinements: [{shape: 'box', center: [0.095, 0, 0.1], lengths: [0.21, 0.26, 0.12], size: 0.0075}],
      embeddedMaterials: [body],
      shapes: [box(-0.5, -0.15, 0, 0.5, 0.3, 0.2, {featureId: 'cabin'}), box(0, -0.03, 0.07, 0.18, 0.06, 0.06, {featureId: 'crashbox'}),
        box(0, -0.025, 0.075, 0.18, 0.05, 0.05, {featureId: 'crashbox-hollow', operation: 'cut', cutTarget: 'crashbox'}),
        box(0.18, -0.12, 0.05, 0.01, 0.24, 0.1, {featureId: 'bumper'})],
      assign(h) {
        const cabin = h.volumeAt(-0.25, 0, 0.1);
        const front = h.mesh.volumes.map(v => S(v.id)).filter(id => id !== cabin);
        return {volumeMaterials: {[cabin]: body.id, ...Object.fromEntries(front.map(id => [id, 'mat-al-6061-t6']))},
          dynamics3d: dynamicsSnapshot(h, {solid3dDynAnalysis: 'explicit', solid3dDynExplicitEnd: '0.012', solid3dDynExplicitFrames: '49', solid3dDynFriction: '0.2', solid3dDynSelfContact: false},
            {velocityAt: [{point: [-0.25, 0, 0.1], velocity: [15, 0, 0]}],
              cards: {'mat-al-6061-t6': {model: 'plastic', yieldStress: 276e6, tangentModulus: 910e6, failureStrain: 0}, [body.id]: {model: 'elastic'}},
              walls: [{point: [0.195, 0, 0], normal: [-1, 0, 0], friction: 0.2}]}),
          report: `cabin ${cabin} front ${front}`};
      }};
  },
  plateModal3d() {
    // Steel cantilever plate 400 × 100 × 20 mm: Euler–Bernoulli f1 = 0.5596·√(E t²/12ρ)/L² = 102 Hz.
    return {name: '悬臂钢板模态-三维-动力学-线弹性', meshSize: 0.01,
      shapes: [box(0, 0, 0, 0.4, 0.1, 0.02)],
      assign(h) {
        const v = h.volumeAt(0.2, 0.05, 0.01), root = h.plane(0, 0);
        return {volumeMaterials: {[v]: 'mat-q235-steel'}, conditions: root.map(fixedAll),
          dynamics3d: dynamicsSnapshot(h, {solid3dDynAnalysis: 'modal', solid3dDynModes: '10', solid3dDynOrder: 'quadratic'}),
          report: `root ${root}`};
      }};
  },
  plateHarmonic3d() {
    // Same plate excited by 500 N (amplitude) on the free end face; static tip deflection FL³/3EI = 8.0e-4 m.
    return {name: '悬臂钢板端部激振谐响应-三维-动力学-线弹性', meshSize: 0.01,
      shapes: [box(0, 0, 0, 0.4, 0.1, 0.02)],
      assign(h) {
        const v = h.volumeAt(0.2, 0.05, 0.01), root = h.plane(0, 0), tip = h.plane(0, 0.4);
        return {volumeMaterials: {[v]: 'mat-q235-steel'},
          conditions: [...root.map(fixedAll), ...tip.map(surface => ({type: 'force', surface, fx: 0, fy: 0, fz: -500}))],
          dynamics3d: dynamicsSnapshot(h, {solid3dDynAnalysis: 'harmonic', solid3dDynFreqMin: '5', solid3dDynFreqMax: '1500', solid3dDynFreqPoints: '20',
            solid3dDynDamping: '0.02', solid3dDynHarmonicModes: '12', solid3dDynOrder: 'quadratic'}),
          report: `root ${root} tip ${tip}`};
      }};
  },
};

// 3D dynamics stage snapshot (as saved by the app). Part numbers follow the mesh, so
// velocities are given at a point inside each part and mapped to the part there.
function dynamicsSnapshot(h, form, {velocityAt = [], cards = {}, walls = []} = {}) {
  const parts = require(path.join(__dirname, '..', '..', 'dynamics-settings.js')).components(h.mesh.tets, h.mesh.nodes.length);
  const velocities = {};
  for (const {point, velocity} of velocityAt) {
    let best = -1, distance = Infinity;
    h.mesh.nodes.forEach((p, i) => { const e = Math.hypot(p[0] - point[0], p[1] - point[1], p[2] - point[2]); if (e < distance) { distance = e; best = i; } });
    velocities[S(parts.nodePart[best] + 1)] = velocity;
  }
  return {form: {solid3dDynThreads: '0', ...form}, velocities, cards, walls};
}
