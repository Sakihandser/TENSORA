'use strict';
// Applies names.cjs to model files in a folder: writes <new name>.json with the
// stored model name updated, then removes the old file.
// Usage: node examples/classic-models/rename.cjs <folder>
const fs = require('node:fs');
const path = require('node:path');
const names = require('./names.cjs');
const dir = path.resolve(process.argv[2]);
for (const [from, to] of Object.entries(names)) {
  const source = path.join(dir, from + '.json'), target = path.join(dir, to + '.json');
  if (!fs.existsSync(source)) { console.log((fs.existsSync(target) ? 'done    ' : 'missing ') + from); continue; }
  const data = JSON.parse(fs.readFileSync(source, 'utf8'));
  data.name = to;
  fs.writeFileSync(target, JSON.stringify(data));
  JSON.parse(fs.readFileSync(target, 'utf8'));
  fs.unlinkSync(source);
  console.log('renamed ' + from + ' -> ' + to);
}
