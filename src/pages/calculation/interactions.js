let analysisRefinementEditor;

function initializeAnalysisRefinementEditor() {
  analysisRefinementEditor = createMeshRefinementEditor(document.getElementById("analysisMeshRefinements"), {
    getZones: () => scene.meshRefinements,
    setZones: zones => {
      if (calculationWorkflowRunning) throw new Error("计算正在进行，请结束后修改局部加密设置。");
      withDrawingHistory(() => {
        scene.meshRefinements = zones;
        markAnalysisNodePlacementStale("localRefinementsChanged");
        markAnalysisMeshStale("localRefinementsChanged");
      });
      renderCalculationView();
    },
    validate: zone => {
      const global = analysisMeshMode() === "size" ? currentAnalysisGlobalMeshSize() : null;
      if (global && zone.size >= global) throw new Error("局部目标尺寸须小于全局网格尺寸。");
    },
    onPicking: active => calculationCanvas.classList.toggle("refinement-picking", active),
    getGlobalSize: currentAnalysisGlobalMeshSize,
  });
  analysisRefinementEditor.sync();
  initializeAnalysisMeshSettings();
}

// "Mesh size" / "node limit" switch on the base calculation page.
function initializeAnalysisMeshSettings() {
  const modes = [...document.querySelectorAll('input[name="analysisMeshMode"]')];
  const sizeInput = document.getElementById("analysisMeshSize");
  if (!modes.length || !sizeInput) return;
  const sizingChanged = () => {
    markAnalysisNodePlacementStale("meshSizingChanged");
    markAnalysisMeshStale("meshSizingChanged");
    syncAnalysisMeshSettings();
    updatePanel();
    renderCalculationView();
  };
  for (const radio of modes) {
    radio.addEventListener("change", () => {
      if (calculationWorkflowRunning) {
        modes.find(item => item.value !== radio.value).checked = true;
        return;
      }
      if (radio.value === "size" && !(Number(sizeInput.value) > 0)) {
        const suggested = suggestedAnalysisMeshSize();
        if (suggested) sizeInput.value = String(suggested);
      }
      sizingChanged();
    });
  }
  sizeInput.addEventListener("change", sizingChanged);
  sizeInput.addEventListener("input", syncAnalysisMeshSettings);
  maxAnalysisNodes?.addEventListener("change", sizingChanged);
  syncAnalysisMeshSettings();
}

// Start the size input from the current mesh (or the node limit's equivalent size).
function suggestedAnalysisMeshSize() {
  let spacing = Number(scene.analysisNodePlacement?.spacing);
  if (!(spacing > 0)) {
    try {
      rebuildDerivedRegions({ markAnalysisNodePlacementStale: false, markAnalysisMeshStale: false });
      spacing = estimateAnalysisNodeSpacing(collectAnalysisPlacementTopology(), readAnalysisNodeLimit());
    } catch {
      return null;
    }
  }
  return spacing > 0 ? Number(Math.max(spacing, ANALYSIS_MESH_MIN_SIZE).toPrecision(2)) : null;
}

function syncAnalysisMeshSettings() {
  const mode = analysisMeshMode();
  const adaptive = Boolean(document.getElementById("adaptiveMeshEnabled")?.checked);
  document.querySelectorAll("[data-mesh-mode]").forEach(row => { row.hidden = row.dataset.meshMode !== mode; });
  document.querySelectorAll('input[name="analysisMeshMode"], #analysisMeshSize').forEach(input => { input.disabled = adaptive; });
  const note = document.getElementById("analysisMeshSizingNote");
  if (note) {
    const spacing = Number(scene.analysisNodePlacement?.spacing);
    const text = adaptive
      ? "自适应网格启用时，初始网格由自适应设置决定。"
      : mode === "size"
        ? "按目标单元边长布置节点并剖分；安全上限 1,000,000 节点。"
        : spacing > 0 && !scene.analysisNodePlacement?.stale
          ? `按节点上限自动估算尺寸；当前网格尺寸约 ${Number(spacing.toPrecision(3))} m。`
          : "按节点上限自动估算单元尺寸。";
    // Rendering calls this often; only touch the DOM when the source text changes.
    if (note.dataset.source !== text) {
      note.dataset.source = text;
      note.textContent = text;
    }
  }
  analysisRefinementEditor?.refreshTransitionNote();
}

// 计算页滚轮缩放，缩放中心固定在鼠标所在世界坐标。
function onCalculationWheel(event) {
  event.preventDefault();
  const screen = calculationPointerPoint(event);
  const before = calculationScreenToWorld(screen);
  const factor = Math.exp(-event.deltaY * 0.0012);
  calculationView.scale = clamp(calculationView.scale * factor, 1e-4, 1e7);
  calculationView.offsetX = screen.x - before.x * calculationView.scale;
  calculationView.offsetY = screen.y + before.y * calculationView.scale;
  gpuMeshRenderer.requestFrame("calculation-interaction", renderCalculationView);
}

// 开始计算页平移，未来计算节点布置工具可在这里分支接入。
function startCalculationPan(screen) {
  calculationInteraction = {
    mode: "pan",
    lastScreen: screen,
  };
  calculationCanvas.classList.add("panning");
}

// 计算页右键或中键保持平移，拾取模式下左键设置加密中心。
function onCalculationPointerDown(event) {
  if (!calculationCanvas) return;
  const screen = calculationPointerPoint(event);
  if (event.button === 0 && analysisRefinementEditor?.isPicking()) {
    const { x, y } = calculationScreenToWorld(screen);
    analysisRefinementEditor.setCenter([x, y]);
    event.preventDefault();
    return;
  }
  calculationCanvas.setPointerCapture(event.pointerId);
  if (event.button === 0 || event.button === 1 || event.button === 2) {
    startCalculationPan(screen);
    event.preventDefault();
  }
}

// 计算页鼠标移动：更新坐标读数，并在平移时移动独立视窗。
function onCalculationPointerMove(event) {
  const screen = calculationPointerPoint(event);
  const world = calculationScreenToWorld(screen);
  if (calculationCoordReadout) {
    calculationCoordReadout.textContent = `x ${formatNumber(world.x)}, y ${formatNumber(world.y)}`;
  }
  if (calculationInteraction?.mode !== "pan") return;
  const dx = screen.x - calculationInteraction.lastScreen.x;
  const dy = screen.y - calculationInteraction.lastScreen.y;
  calculationView.offsetX += dx;
  calculationView.offsetY += dy;
  calculationInteraction.lastScreen = screen;
  gpuMeshRenderer.requestFrame("calculation-interaction", renderCalculationView);
}

// 计算页鼠标抬起，结束平移状态。
function onCalculationPointerUp() {
  if (calculationInteraction?.mode === "pan") {
    calculationCanvas.classList.remove("panning");
  }
  calculationInteraction = null;
}

// 计算页不弹出浏览器右键菜单，右键拖动会和绘图页一样用于平移。
function onCalculationContextMenu(event) {
  event.preventDefault();
}

// 开关计算页动画层；没有位移数据时仍保留按钮状态，后续结果进入后会直接播放。
function toggleCalculationAnimation() {
  calculationAnimation.running = !calculationAnimation.running;
  if (calculationAnimationIcon) {
    calculationAnimationIcon.innerHTML = `<use href="${calculationAnimation.running ? "#icon-pause" : "#icon-play"}"></use>`;
  }
  if (calculationAnimation.running) {
    renderCalculationView();
  } else {
    cancelCalculationAnimationFrame();
    renderCalculationView();
  }
}
