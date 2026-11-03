// Save only editable drawing data, with one timer and at most one request in flight.
let drawingRecoveryTimer = null;
let drawingRecoveryPending = null;
let drawingRecoverySaving = false;
let drawingRecoveryRevision = 0;
const DRAWING_RECOVERY_URL = './api/drawing-recovery';
let drawingRecoveryStorageKey = 'fem-drawing-recovery-v1:' + (window.location?.pathname || '/');
function drawingRecoveryStatus(text) {
  const element = document.getElementById('drawingRecoveryStatus');
  if (element) element.textContent = text;
}
function scheduleDrawingRecovery(snapshot) {
  drawingRecoveryRevision++;
  drawingRecoveryStatus("正在保存草稿…");
  drawingRecoveryPending = {version:1, savedAt:new Date().toISOString(), snapshot};
  if (drawingRecoveryTimer === null) drawingRecoveryTimer = setTimeout(() => {
    drawingRecoveryTimer = null;
    flushDrawingRecovery();
  }, 300);
}
function cacheDrawingRecovery(record) {
  try {
    // Keep synchronous storage small; the project file is the primary checkpoint.
    if (record.snapshot.length < 1000000) window.localStorage.setItem(drawingRecoveryStorageKey, JSON.stringify(record));
    else window.localStorage.removeItem(drawingRecoveryStorageKey);
  } catch { /* Disk autosave still works when browser storage is unavailable. */ }
}
function recoveryRequestBody(record) {
  return '{"savedAt":'+JSON.stringify(record.savedAt)+',"snapshot":'+record.snapshot+'}';
}
async function flushDrawingRecovery() {
  if (drawingRecoverySaving || !drawingRecoveryPending) return;
  const record = drawingRecoveryPending;
  drawingRecoveryPending = null;
  drawingRecoverySaving = true;
  cacheDrawingRecovery(record);
  try {
    const response = await fetch(DRAWING_RECOVERY_URL, {method:'POST',headers:{'Content-Type':'application/json'},body:recoveryRequestBody(record)});
    if (!response.ok) throw new Error('Autosave failed');
    if (!drawingRecoveryPending) drawingRecoveryStatus('草稿已自动保存');
  } catch {
    drawingRecoveryStatus('草稿保存失败，请手动保存 JSON');
  } finally {
    drawingRecoverySaving = false;
    if (drawingRecoveryPending) flushDrawingRecovery();
  }
}
async function initializeDrawingRecovery() {
  const revision = drawingRecoveryRevision;
  let record = null;
  let saved = null;
  try {
    const response = await fetch(DRAWING_RECOVERY_URL, {cache:'no-store'});
    if (response.ok) {
      saved = await response.json();
      if (saved.workspaceId) drawingRecoveryStorageKey = "fem-drawing-recovery-v1:" + saved.workspaceId;
    }
  } catch { /* A static/file page can still recover its browser checkpoint. */ }
  try { record = JSON.parse(window.localStorage.getItem(drawingRecoveryStorageKey) || 'null'); }
  catch { /* No browser checkpoint. */ }
  if (saved?.snapshot && (!record || saved.savedAt >= record.savedAt)) record = {...saved, snapshot:JSON.stringify(saved.snapshot)};
  // Never overwrite edits made while the initial read was pending.
  if (revision !== 0 || revision !== drawingRecoveryRevision || !record?.snapshot) return;
  try {
    const restored = JSON.parse(record.snapshot);
    if (!restored.scene || !Array.isArray(restored.scene.curves) || !Array.isArray(restored.scene.geometryNodes)) return;
    scene = normalizeScene(restored.scene);
    draft = restored.draft || null;
    activeTool = TOOL_LABELS[restored.activeTool] ? restored.activeTool : 'select';
    constructionMode = Boolean(restored.constructionMode);
    document.getElementById('constructionMode').checked = constructionMode;
    modelName.value = uiText(scene.name);
    toolButtons.forEach(button => button.classList.toggle('active',button.dataset.tool===activeTool));
    toolName.textContent = TOOL_LABELS[activeTool];
    canvas.classList.toggle('selecting',activeTool==='select');
    canvas.classList.toggle('erasing',activeTool==='eraser');
    rebuildDerivedRegions({markAnalysisNodePlacementStale:false,markAnalysisMeshStale:false});
    fitViewToScene();
    updatePanel();
    render();
    drawingRecoveryStatus('草稿已恢复');
  } catch {
    drawingRecoveryStatus('草稿读取失败，请导入已保存的 JSON');
  }
}
function checkpointDrawingBeforeExit() {
  if (!drawingRecoveryPending) return;
  cacheDrawingRecovery(drawingRecoveryPending);
  // keepalive is limited to 64 KiB. Larger drawings use the periodic project save.
  if (drawingRecoveryPending.snapshot.length < 20000) {
    fetch(DRAWING_RECOVERY_URL,{method:'POST',headers:{'Content-Type':'application/json'},body:recoveryRequestBody(drawingRecoveryPending),keepalive:true}).catch(()=>{});
  }
}
