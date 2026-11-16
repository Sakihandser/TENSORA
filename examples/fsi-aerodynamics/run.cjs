'use strict';

const fs = require('node:fs');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {runFsi} = require('../../fsi-runner');

const root = path.resolve(__dirname, '..', '..');
const cases = {
  airfoil: {dimension: 2, speed: 40, angle: 5, iterations: 700, files: ['airfoil.geo']},
  sailplane: {dimension: 3, speed: 35, angle: 4, iterations: 900, files: ['sailplane.geo', 'airframe.stl', 'support.stl', 'outer.stl']},
};

function readModel(meshPath, dimension) {
  const lines = fs.readFileSync(meshPath, 'utf8').split(/\r?\n/);
  const nodeStart = lines.indexOf('$Nodes');
  const elementStart = lines.indexOf('$Elements');
  if (nodeStart < 0 || elementStart < 0) throw Error('Expected a Gmsh MSH2 ASCII mesh.');
  const nodeIds = new Map();
  const nodes = lines.slice(nodeStart + 2, lines.indexOf('$EndNodes')).map((row, i) => {
    const [id, ...coordinates] = row.trim().split(/\s+/).map(Number);
    nodeIds.set(id, i);
    return coordinates.slice(0, dimension);
  });
  const cells = [], cellRoles = [], cellMaterials = [], far = [];
  const restrained = new Set();
  const cellType = dimension === 2 ? 2 : 4;
  const faceType = dimension === 2 ? 1 : 2;
  for (const row of lines.slice(elementStart + 2, lines.indexOf('$EndElements'))) {
    const [, type, tagCount, physical, ...rest] = row.trim().split(/\s+/).map(Number);
    const points = rest.slice(tagCount - 1).map(id => nodeIds.get(id));
    if (type === cellType && (physical === 21 || physical === 22)) {
      cells.push(points);
      cellRoles.push(physical === 21 ? 'solid' : 'fluid');
      cellMaterials.push(physical === 21 ? 'aluminum' : null);
    }
    if (type === faceType && physical === 11) far.push(points);
    if (type === faceType && physical === 12) for (const id of points) restrained.add(id);
  }
  if (!cellRoles.includes('solid') || !cellRoles.includes('fluid') || !far.length || !restrained.size) {
    throw Error('The mesh must contain both domains and the far-field and support markers.');
  }
  const fixed = nodes.flatMap((_, i) => Array(dimension).fill(restrained.has(i) ? 1 : 0));
  const materials = {aluminum: {name: 'Equivalent aluminum solid', E: 70e9, nu: 0.33, density: 2700}};
  return {dimension, nodes, cells, cellRoles, cellMaterials, fixed, materials, boundaries: [{name: 'far', faces: far}]};
}

async function run(name) {
  const example = Object.hasOwn(cases, name) ? cases[name] : null;
  if (!example) throw Error('Choose airfoil or sailplane.');
  const {dimension, speed, angle, iterations, files} = example;
  const work = path.join(root, 'tmp', 'fsi-aerodynamics', name);
  fs.mkdirSync(work, {recursive: true});
  for (const file of files) fs.copyFileSync(path.join(__dirname, file), path.join(work, file));
  const gmsh = path.join(root, 'third_party', 'gmsh', 'gmsh-4.15.0-Windows64', 'gmsh.exe');
  const mesher = spawnSync(gmsh, [files[0], '-' + dimension, '-format', 'msh2', '-o', 'case.msh', '-nt', '4', '-log', 'mesh.log'],
    {cwd: work, windowsHide: true, stdio: 'ignore'});
  if (mesher.error) throw mesher.error;
  if (mesher.status !== 0) throw Error('Gmsh failed. See ' + path.join(work, 'mesh.log'));
  const model = readModel(path.join(work, 'case.msh'), dimension);
  const alpha = angle * Math.PI / 180;
  const fluid = {name: 'Air (inviscid)', model: 'idealgas', density: 1.225, viscosity: 0, gamma: 1.4, gasConstant: 287.05, temperature: 288.15};
  const settings = {engine: 'oneway', analysis: 'steady', plane: 'stress', outerIterations: 1,
    fluidIterations: iterations, threads: 4, convergence: -8, referencePressure: 101325,
    boundaries: {far: {kind: 'farfield', velocity: speed, direction: [Math.cos(alpha), Math.sin(alpha), 0]}}};
  if (name === 'sailplane') Object.assign(settings, {flowCfl: 12, flowFirstOrder: true});
  const result = await runFsi({model, fluid, settings}, {onProgress({phase, inner, residual}) {
    if (phase !== 'su2') console.log(phase);
    else if (inner % 100 === 0) console.log(`SU2 iteration ${inner}, log residual ${residual}`);
  }});
  console.log(path.join(root, 'calculation-data', 'fsi', result.runId, 'summary.json'));
  console.log(JSON.stringify({mesh: result.meta, lastIteration: result.history.at(-1), mfem: result.mfem, fields: result.frames[0].stats}, null, 2));
}

run(process.argv[2]).catch(error => { console.error(error.message); process.exitCode = 1; });
