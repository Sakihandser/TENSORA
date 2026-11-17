'use strict';
// Material snapshots for the classic models. Library entries are copied from
// materials/materials.json; demo-only materials use their own ids so the app
// does not overwrite them with library values when the model is opened.
const path = require('node:path');
const library = require(path.join(__dirname, '..', '..', 'materials', 'materials.json'));

function lib(id) {
  const m = library.materials.find(entry => entry.id === id);
  if (!m) throw Error('Missing library material ' + id);
  return JSON.parse(JSON.stringify(m));
}
function deformationCard(id) {
  const c = library.deformationMaterials.find(entry => entry.id === id);
  if (!c) throw Error('Missing deformation card ' + id);
  return JSON.parse(JSON.stringify(c.card));
}
function custom(id, name, props, notes = '') {
  return {id, name, strengthCriterion: props.yieldStrength ? 4 : 1, color: '#7c8a96', sourceUrl: '', sourceUrls: [], notes, blastConstitutive: null,
    yieldStrength: null, tensileStrength: null, compressiveStrength: null, fractureEnergy: null, ...props};
}
module.exports = {library, lib, deformationCard, custom};
