'use strict';
const fs = require('node:fs/promises');
const path = require('node:path');
// One workspace-owned checkpoint, independent of the launcher's ephemeral HTTP port.
function createDrawingRecoveryStore(directory) {
  const target = path.join(directory, 'drawing-draft.json');
  let queue = Promise.resolve();
  function validate(snapshot) {
    if (!snapshot || typeof snapshot !== 'object' || !snapshot.scene ||
        !['geometryNodes','curves','pointLoads','distributedLoads','bodyLoads','regions'].every(k => Array.isArray(snapshot.scene[k]))) {
      throw new Error('Invalid drawing recovery snapshot.');
    }
    // Never persist solver arrays accidentally supplied by a caller.
    const {analysisNodes, mesh, analysisNodePlacement, ...scene} = snapshot.scene;
    return {scene, draft:snapshot.draft || null, activeTool:snapshot.activeTool || 'select', constructionMode:!!snapshot.constructionMode};
  }
  return {
    async read() {
      await queue;
      try { const record = JSON.parse(await fs.readFile(target, 'utf8')); validate(record.snapshot); return record; }
      catch (error) { if (error.code === 'ENOENT') return {snapshot:null}; throw error; }
    },
    save(raw) {
      const snapshot = validate(raw.snapshot || raw);
      const savedAt = raw.snapshot && Number.isFinite(Date.parse(raw.savedAt)) ? new Date(raw.savedAt).toISOString() : new Date().toISOString();
      const write = queue.then(async () => {
        let existing;
        try { existing = JSON.parse(await fs.readFile(target, 'utf8')); } catch { /* first checkpoint */ }
        if (existing?.savedAt > savedAt) return {ok:true, savedAt:existing.savedAt};
        const record = {version:1, savedAt, snapshot};
        await fs.mkdir(directory, {recursive:true});
        const temporary = target + '.tmp';
        await fs.writeFile(temporary, JSON.stringify(record), 'utf8');
        await fs.rename(temporary, target);
        return {ok:true, savedAt:record.savedAt};
      });
      queue = write.catch(() => {});
      return write;
    }
  };
}
module.exports = {createDrawingRecoveryStore};
