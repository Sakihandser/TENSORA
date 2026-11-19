// 切换当前工具，同时取消未完成的草图和拖动状态。
function setTool(tool) {
  if (typeof shapeDialog !== "undefined" && shapeDialog.open) closeShapeEditor();
  activeTool = tool;
  draft = null;
  interaction = null;
  toolButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.tool === tool);
  });
  toolName.textContent = TOOL_LABELS[tool];
  canvas.classList.toggle("selecting", tool === "select");
  canvas.classList.toggle("erasing", tool === "eraser");
  render();
}

// 切换载荷方向输入方式：手绘拖拽或角度预输入。
function setLoadDirectionMode(mode) {
  loadDirectionMode = mode === "input" ? "input" : "drag";
  loadDirectionButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.loadMode === loadDirectionMode);
  });
}

// 切换体力作用范围：点击区域或全局统一施加。
function setBodyForceScope(scope) {
  bodyForceScope = scope === "global" ? "global" : "region";
  bodyForceScopeButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.bodyForceScope === bodyForceScope);
  });
}

// 计算页工具点击入口；计算输入准备完成后会写入项目中转目录。
function handleCalculationToolClick(tool) {
  if (calculationWorkflowRunning) return;
  setCalculationTool(tool);
  if (tool === "analysis-nodes") {
    try { autoPlaceAnalysisNodes(); }
    catch (error) { handleCalculationExportError(error); }
  }
  if (tool === "auto-mesh") {
    autoGenerateAnalysisMesh().catch(handleCalculationExportError);
  }
  // Both runs pass the pre-run check first (errors stop, warnings ask once).
  const guarded = (run) => typeof runWithPreflight === "function" ? runWithPreflight("calculation", run) : run();
  if (tool === "start-calculation" && typeof startCalculationWorkflow === "function") {
    guarded(() => startCalculationWorkflow()).catch(handleCalculationExportError);
  }
  if (tool === "refine-once") {
    guarded(() => startCalculationWorkflow({ adaptive: true, refineOnce: true, maxIterations: 1 })).catch(handleCalculationExportError);
  }
}

// 计算页工具状态切换；实际计算流程由 handleCalculationToolClick 分发。
function setCalculationTool(tool) {
  activeCalculationTool = tool || "";
  calculationToolButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.calculationTool === activeCalculationTool);
  });
  if (calculationModeName) {
    calculationModeName.textContent = CALCULATION_TOOL_LABELS[activeCalculationTool] || "计算";
  }
}
