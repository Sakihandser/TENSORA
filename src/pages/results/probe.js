// Point probes for the 2D result workspace (static / deformation / blast channels)
// and for the deformation results page. Probes keep their reference (undeformed)
// coordinates; values follow the displayed frame, and histories cover all frames.
const resultProbeStores = { static: ResultProbe.createStore(), deformation: ResultProbe.createStore(), blast: ResultProbe.createStore() };
let resultProbePanel = null, deformationProbePanel = null;
let resultProbeChannel = null, resultProbeLastData = null, deformationProbeLastKey = "";
let deformationProbeProjection = null;
const resultProbeElementMaps = new WeakMap();

const RESULT_PROBE_QUANTITIES = [
  ["ux", "X 位移 Ux", "m"], ["uy", "Y 位移 Uy", "m"], ["umag", "位移量 |u|", "m"],
  ["vx", "X 速度 Vx", "m/s"], ["vy", "Y 速度 Vy", "m/s"], ["vmag", "速度量 |v|", "m/s"],
  ["sxx", "正应力 σxx", "Pa"], ["syy", "正应力 σyy", "Pa"], ["szz", "正应力 σzz", "Pa"], ["sxy", "剪应力 τxy", "Pa"],
  ["s1", "最大主应力 σ1", "Pa"], ["s2", "最小主应力 σ2", "Pa"], ["vm", "von Mises 应力", "Pa"], ["dynamicVm", "扰动等效应力", "Pa"],
  ["exx", "正应变 εxx", "1"], ["eyy", "正应变 εyy", "1"], ["ezz", "正应变 εzz", "1"], ["exy", "剪应变 εxy", "1"], ["equivalentStrain", "等效应变", "1"],
  ["plasticStrain", "等效塑性应变 PEEQ", "1"], ["damage", "损伤 d", "1"],
];

function resultProbeQuantities(channel) {
  const r = typeof deformationResult !== "undefined" ? deformationResult : null;
  const stressUnit = channel === "static" ? calculationResultData?.result?.units?.stress || "Pa" : "Pa";
  return RESULT_PROBE_QUANTITIES.map(([key, label, unit]) => {
    if (key === "damage" && channel === "deformation") label = r?.fracture ? "相场损伤 d" : "损伤起始指标";
    if (key === "plasticStrain" && channel === "blast") label = "等效塑性应变";
    return { key, label, unit: unit === "Pa" ? stressUnit : unit };
  });
}

function resultProbeElementMap(elements) {
  let map = resultProbeElementMaps.get(elements);
  if (!map) { map = new Map(elements.map((element) => [element.elementNo, element])); resultProbeElementMaps.set(elements, map); }
  return map;
}

// Locate a point on TRI3 result data. factor selects the displayed configuration
// (0 = undeformed); the probe always stores reference coordinates.
function locateResultProbe(data, coords, { snap = false, factor = 0 } = {}) {
  if (!data?.elements?.length) throw new Error("当前没有可读取的结果。");
  const position = factor ? (n) => ({ x: n.x + (n.ux || 0) * factor, y: n.y + (n.uy || 0) * factor }) : (n) => n;
  const point = { x: coords[0], y: coords[1] };
  let hit = ResultProbe.locateTriangle(data.elements, point, position), message = "";
  if (hit && snap) {
    let nearest = 0, best = Infinity;
    hit.element.nodes.forEach((node, i) => { const p = position(node), d = Math.hypot(p.x - point.x, p.y - point.y); if (d < best) { best = d; nearest = i; } });
    hit = { ...hit, weights: [0, 1, 2].map((i) => (i === nearest ? 1 : 0)) };
  }
  if (!hit) {
    if (!snap) throw new Error("该点不在网格内。勾选“吸附到最近节点”可读取最近节点。");
    const near = ResultProbe.nearestNode(data.nodes, point, position);
    const element = near && data.elements.find((e) => e.nodes.includes(near.node));
    if (!element) throw new Error("当前没有可读取的结果。");
    hit = { element, weights: element.nodes.map((n) => (n === near.node ? 1 : 0)) };
    message = `该点不在网格内，已吸附到最近节点 ${near.node.nodeNo}（距离 ${ResultProbe.formatValue(near.distance)} m）。`;
  }
  const nodes = hit.element.nodes, weights = hit.weights;
  const strongest = weights.indexOf(Math.max(...weights));
  const exact = !factor && !message && !snap;
  return {
    point: exact ? [coords[0], coords[1]] : [0, 1].map((axis) => nodes.reduce((sum, n, i) => sum + weights[i] * (axis ? n.y : n.x), 0)),
    elementNo: hit.element.elementNo, nodeNos: nodes.map((n) => n.nodeNo), weights,
    snapped: weights.some((w) => w === 1), where: `单元 ${hit.element.elementNo} · 节点 ${nodes[strongest].nodeNo}`, message,
  };
}

// Re-bind probes after a new run or a reloaded result (same reference coordinates).
function relocateResultProbes(store, topology, data) {
  if (store.topology === topology) return false;
  store.topology = topology;
  if (!store.items.length || !data) return true;
  store.items = store.items.flatMap((probe) => {
    try { return [{ ...locateResultProbe(data, probe.point, { snap: probe.snapped }), id: probe.id, label: probe.label }]; }
    catch { return []; }
  });
  return true;
}

function blastCellProbeValues(cells, baseline) {
  const [ex, ey, gxy, sx, sy, txy, damage] = cells, extended = cells.length > 7, sz = extended ? cells[7] : 0, base = baseline || cells;
  const dx = sx - base[3], dy = sy - base[4], dxy = txy - base[5], dz = sz - (base[7] ?? 0);
  const [s1, s2] = ResultProbe.principal2d(sx, sy, txy);
  return {
    sxx: sx, syy: sy, sxy: txy, ...(extended ? { szz: sz, plasticStrain: cells[8] ?? 0 } : {}), s1, s2,
    vm: Math.sqrt(Math.max(0, sx * sx + sy * sy + sz * sz - sx * sy - sy * sz - sz * sx + 3 * txy * txy)),
    dynamicVm: Math.sqrt(Math.max(0, dx * dx + dy * dy + dz * dz - dx * dy - dy * dz - dz * dx + 3 * dxy * dxy)),
    exx: ex, eyy: ey, exy: gxy / 2, equivalentStrain: Math.sqrt(Math.max(0, ex * ex - ex * ey + ey * ey + 0.75 * gxy * gxy)), damage,
  };
}

// Static and blast values come from the displayed result data.
function resultDataProbeValues(data, probe, channel) {
  if (!data) return null;
  const element = resultProbeElementMap(data.elements).get(probe.elementNo);
  const nodes = probe.nodeNos.map((no) => data.nodeByNo.get(no));
  if (!element || nodes.some((node) => !node)) return null;
  const sum = (read) => nodes.reduce((total, node, i) => total + probe.weights[i] * (Number(read(node)) || 0), 0);
  const ux = sum((n) => n.ux), uy = sum((n) => n.uy);
  const [s1, s2] = ResultProbe.principal2d(element.stressXx, element.stressYy, element.stressXy);
  const values = {
    ux, uy, umag: Math.hypot(ux, uy), sxx: element.stressXx, syy: element.stressYy, sxy: element.stressXy, s1, s2,
    vm: element.equivalentStress, exx: element.strainXx, eyy: element.strainYy, exy: element.strainXy, equivalentStrain: element.equivalentStrain,
  };
  if (element.stressZz !== undefined) values.szz = element.stressZz;
  if (channel === "blast") {
    values.dynamicVm = element.dynamicEquivalentStress;
    values.damage = element.damage;
    if (element.plasticStrain !== undefined) values.plasticStrain = element.plasticStrain;
    const frame = typeof tntCurrentFrame !== "undefined" ? tntCurrentFrame : null;
    const indices = blastHistory && resultProbeNodeIndex(blastHistory.model);
    if (frame?.v && indices) {
      const ids = probe.nodeNos.map((no) => indices.get(no));
      const vx = ids.reduce((t, id, i) => t + probe.weights[i] * frame.v[2 * id], 0), vy = ids.reduce((t, id, i) => t + probe.weights[i] * frame.v[2 * id + 1], 0);
      Object.assign(values, { vx, vy, vmag: Math.hypot(vx, vy) });
    }
  } else if (element.strainZz !== undefined) values.ezz = element.strainZz;
  const info = channel === "static" ? RESULT_SAFETY_LABELS?.[element.safetyCode] || element.safetyText || "" : "";
  return { values, info };
}

const resultProbeNodeIndexes = new WeakMap();
function resultProbeNodeIndex(model) {
  let map = resultProbeNodeIndexes.get(model);
  if (!map) { map = new Map(model.nodes.map((node, i) => [node.nodeNo, i])); resultProbeNodeIndexes.set(model, map); }
  return map;
}
const resultProbeModelElements = new WeakMap();
function resultProbeModelElementIndex(model) {
  let map = resultProbeModelElements.get(model);
  if (!map) { map = new Map(model.elements.map((element, i) => [element.elementNo, i])); resultProbeModelElements.set(model, map); }
  return map;
}

// Deformation values interpolate the nodal (extrapolated) solver output; PhAST
// element fields are used directly where the solver provides them.
function deformationProbeValues(r, index, probe) {
  const frame = r?.frames?.[index];
  if (!frame) return null;
  const elementIndex = resultProbeModelElementIndex(r.model).get(probe.elementNo);
  const element = r.model.elements[elementIndex];
  if (!element) return null;
  const card = deformationResultCard(r, element), elemental = frame.elementFields?.[probe.elementNo];
  const nodal = (field, j) => probe.nodeNos.reduce((sum, id, i) => sum + probe.weights[i] * (Number(frame[field]?.[id]?.[j]) || 0), 0);
  const [sx, sy, sz, sxy, syz, szx] = elemental?.stress || [0, 1, 2, 3, 4, 5].map((j) => nodal("stress", j));
  const [ex, ey, ez, exy, eyz, ezx] = elemental?.strain || [0, 1, 2, 3, 4, 5].map((j) => nodal("strain", j));
  const ux = nodal("displacement", 0), uy = nodal("displacement", 1), [s1, s2] = ResultProbe.principal2d(sx, sy, sxy);
  const values = {
    ux, uy, umag: Math.hypot(ux, uy), sxx: sx, syy: sy, szz: sz, sxy, s1, s2, vm: ResultProbe.vonMises(sx, sy, sz, sxy, syz, szx),
    exx: ex, eyy: ey, ezz: ez, exy, equivalentStrain: ResultProbe.equivalentStrain(ex, ey, ez, exy, eyz, ezx),
  };
  if (r.fracture) values.damage = elemental?.damage ?? nodal("damage", 0);
  else {
    const plastic = card.model === "plastic";
    values.plasticStrain = plastic ? nodal("plasticStrain", 0) : 0;
    values.damage = plastic ? values.plasticStrain / card.criticalPlasticStrain : 0;
  }
  return { values };
}

function deformationProbeHistory(probes) {
  const r = deformationResult;
  if (!r) throw new Error("请在损伤变形面板运行计算。");
  const series = probes.map((probe) => {
    const out = {};
    r.frames.forEach((_, i) => {
      const values = deformationProbeValues(r, i, probe)?.values || {};
      for (const [key, value] of Object.entries(values)) (out[key] ||= new Array(r.frames.length).fill(NaN))[i] = value;
    });
    return out;
  });
  return {
    axes: [
      { key: "load", label: "载荷比例", unit: "", values: r.frames.map((frame) => frame.time * r.settings.loadFactor) },
      { key: "increment", label: "增量序号", unit: "", values: r.frames.map((_, i) => i + 1) },
    ],
    series,
  };
}

async function blastProbeHistory(probes, { signal }) {
  const history = blastHistory;
  if (!history) throw new Error("暂无爆破结果。");
  const nodeIndex = resultProbeNodeIndex(history.model), elementIndex = resultProbeModelElementIndex(history.model);
  const nodes = [...new Set(probes.flatMap((probe) => probe.nodeNos.map((no) => nodeIndex.get(no))))];
  const elements = [...new Set(probes.map((probe) => elementIndex.get(probe.elementNo)))];
  if ([...nodes, ...elements].some((value) => value === undefined)) throw new Error("测点时程读取失败。");
  const url = `${history.frameBaseUrl.replace(/frames\/$/, "probe")}?nodes=${nodes.join(",")}&elements=${elements.join(",")}`;
  const response = await fetch(url, { cache: "no-store", signal });
  const body = await response.json().catch(() => ({}));
  if (!response.ok || !body.ok) throw new Error(body.error || "测点时程读取失败。");
  const nodeData = new Map(body.nodes.map((entry) => [entry.index, entry])), elementData = new Map(body.elements.map((entry) => [entry.index, entry]));
  const count = body.times.length;
  const series = probes.map((probe) => {
    const cells = elementData.get(elementIndex.get(probe.elementNo)).cells, ids = probe.nodeNos.map((no) => nodeData.get(nodeIndex.get(no)));
    const out = {};
    const put = (key, i, value) => { (out[key] ||= new Array(count).fill(NaN))[i] = value; };
    for (let i = 0; i < count; i++) {
      const sum = (field, axis) => ids.reduce((total, entry, k) => total + probe.weights[k] * entry[field][i][axis], 0);
      const ux = sum("u", 0), uy = sum("u", 1), vx = sum("v", 0), vy = sum("v", 1);
      put("ux", i, ux); put("uy", i, uy); put("umag", i, Math.hypot(ux, uy));
      put("vx", i, vx); put("vy", i, vy); put("vmag", i, Math.hypot(vx, vy));
      for (const [key, value] of Object.entries(blastCellProbeValues(cells[i], cells[0]))) put(key, i, value);
    }
    return out;
  });
  return { axes: [{ key: "time", label: "时间", unit: "ms", values: body.times.map((time) => time * 1000) }], series };
}

function resultProbeTopology(channel) {
  if (channel === "blast") return blastHistory?.model || null;
  if (channel === "deformation") return deformationResult?.model || null;
  return calculationResultData?.input || null;
}

function resultProbeDisplayFactor(panelIndex = -1) {
  const data = calculationResultData;
  if (!data) return 0;
  if (isResultTensorDashboard()) return panelIndex === 0 ? 1 : 0;
  if (activeResultView === "deformation") return resultDisplacementFactor(data);
  if (data.deformation && ["damage", "plasticStrain"].includes(activeResultView)) return resultDisplacementFactor(data);
  return 0;
}

function resultProbeDisplayedPoint(probe, data, factor) {
  if (!factor) return { x: probe.point[0], y: probe.point[1] };
  const nodes = probe.nodeNos.map((no) => data.nodeByNo.get(no));
  if (nodes.some((node) => !node)) return { x: probe.point[0], y: probe.point[1] };
  return {
    x: probe.point[0] + factor * nodes.reduce((sum, n, i) => sum + probe.weights[i] * (n.ux || 0), 0),
    y: probe.point[1] + factor * nodes.reduce((sum, n, i) => sum + probe.weights[i] * (n.uy || 0), 0),
  };
}

function drawResultProbeMarkers() {
  const data = calculationResultData, probes = resultProbeStores[activeResultChannel]?.items;
  if (!data || !probes?.length || !resultCtx) return;
  if (isResultTensorDashboard()) {
    resultDashboardPanels().forEach((panel, index) => {
      const bounds = index === 0 ? resultPanelBoundsCache.get(data) || data.baseBounds : data.baseBounds;
      const projector = resultPanelProjector(panel, bounds);
      drawResultPanelClipped(panel, () => ResultProbe.drawMarkers2d(resultCtx, probes, (probe) => projector(resultProbeDisplayedPoint(probe, data, index === 0 ? 1 : 0))));
    });
    return;
  }
  const factor = resultProbeDisplayFactor();
  ResultProbe.drawMarkers2d(resultCtx, probes, (probe) => resultWorldToScreen(resultProbeDisplayedPoint(probe, data, factor)));
}

// Called after each result render: switch stores with the channel, refresh values when the frame changes.
function syncResultProbePanel() {
  if (!resultProbePanel) return;
  const channel = activeResultChannel, store = resultProbeStores[channel];
  const data = channel === "deformation" ? resultChannels.deformation?.data || calculationResultData : calculationResultData;
  const relocated = relocateResultProbes(store, resultProbeTopology(channel), data);
  if (resultProbeChannel !== channel) {
    resultProbeChannel = channel; resultProbeLastData = calculationResultData;
    resultProbePanel.setStore(store);
    return;
  }
  if (relocated) { resultProbeLastData = calculationResultData; resultProbePanel.resetHistory(); return; }
  if (resultProbeLastData !== calculationResultData) { resultProbeLastData = calculationResultData; resultProbePanel.refresh(); }
}

function selectDeformationProbeFrame(index) {
  const slider = document.getElementById("deformationFrame");
  stopDeformationPlayback();
  slider.value = String(index);
  syncDeformationToBaseResults();
  renderDeformation();
}

function initializeResultProbes() {
  const resultRoot = document.getElementById("resultProbePanel");
  if (resultRoot) {
    resultProbePanel = ResultProbe.createPanel({
      root: resultRoot, dimension: 2, store: resultProbeStores[activeResultChannel], exportName: "二维测点结果", infoLabel: "安全校核",
      quantities: () => resultProbeQuantities(activeResultChannel),
      note: () => activeResultChannel === "blast" ? "TRI3 单元的应力、应变和损伤为单元常值，位移和速度按节点线性插值。"
        : activeResultChannel === "deformation" ? "位移、应力、应变和塑性应变按节点结果线性插值；求解器提供单元值时取单元值。"
          : "TRI3 单元的应力和应变为单元常值，位移按节点线性插值。",
      locate: (coords, options) => {
        const data = activeResultChannel === "deformation" ? resultChannels.deformation?.data || calculationResultData : calculationResultData;
        return locateResultProbe(data, coords, options);
      },
      evaluate: (probe) => activeResultChannel === "deformation"
        ? deformationProbeValues(deformationResult, Number(document.getElementById("deformationFrame").value) || 0, probe)
        : resultDataProbeValues(calculationResultData, probe, activeResultChannel),
      historyAvailable: () => (activeResultChannel === "blast" && Boolean(blastHistory)) || (activeResultChannel === "deformation" && Boolean(deformationResult)),
      historyKey: () => activeResultChannel + ":" + (activeResultChannel === "blast" ? blastHistory?.id : deformationResult?.runId),
      history: (probes, options) => activeResultChannel === "blast" ? blastProbeHistory(probes, options) : deformationProbeHistory(probes),
      historyTitle: "时程 / 增量曲线",
      currentIndex: () => activeResultChannel === "blast" ? Number(document.getElementById("blastFrame").value)
        : activeResultChannel === "deformation" ? Number(document.getElementById("deformationFrame").value) : -1,
      selectIndex: (index) => {
        if (activeResultChannel === "blast") { if (blastPlayback !== null) toggleBlastPlayback(); selectBlastFrame(index); }
        else if (activeResultChannel === "deformation") selectDeformationProbeFrame(index);
      },
      changed: () => { renderResultView(); if (activeResultChannel === "deformation") { deformationProbePanel?.refresh(); renderDeformation(); } },
    });
    resultProbeChannel = activeResultChannel;
  }

  const deformationRoot = document.getElementById("deformationProbePanel");
  if (deformationRoot) {
    deformationRoot.closest(".deformation-probe-card")?.classList.add("probe-wide");
    deformationProbePanel = ResultProbe.createPanel({
      root: deformationRoot, dimension: 2, store: resultProbeStores.deformation, exportName: "损伤变形测点结果",
      quantities: () => resultProbeQuantities("deformation"),
      note: () => "位移、应力、应变和塑性应变按节点结果线性插值；求解器提供单元值时取单元值。",
      locate: (coords, options) => {
        if (deformationResult && !resultChannels.deformation?.data) syncDeformationToBaseResults();
        return locateResultProbe(resultChannels.deformation?.data, coords, options);
      },
      evaluate: (probe) => deformationProbeValues(deformationResult, Number(document.getElementById("deformationFrame").value) || 0, probe),
      historyAvailable: () => Boolean(deformationResult),
      historyKey: () => "deformation:" + deformationResult?.runId,
      history: (probes) => deformationProbeHistory(probes),
      historyTitle: "增量曲线",
      currentIndex: () => Number(document.getElementById("deformationFrame").value),
      selectIndex: selectDeformationProbeFrame,
      changed: () => { renderDeformation(); if (activeResultChannel === "deformation") { resultProbePanel?.refresh(); renderResultView(); } },
    });
  }

  // A click (not a drag) on the result canvas adds a probe.
  bindProbeClicks(resultCanvas, (screen) => {
    if (!resultProbePanel?.pickEnabled() || !calculationResultData) return;
    const panelIndex = isResultTensorDashboard() ? resultDashboardPanels().indexOf(resultDashboardPanelAt(screen)) : -1;
    if (isResultTensorDashboard() && panelIndex < 0) return;
    const world = resultInteractionWorldPoint(screen);
    if (world) resultProbePanel.addAt([world.x, world.y], { factor: resultProbeDisplayFactor(panelIndex) });
  }, resultPointerPoint);
  const deformationCanvas = document.getElementById("deformationCanvas");
  bindProbeClicks(deformationCanvas, (screen) => {
    if (!deformationProbePanel?.pickEnabled() || !deformationResult || !deformationProbeProjection) return;
    const world = deformationProbeProjection.inverse(screen);
    deformationProbePanel.addAt([world.x, world.y], { factor: deformationProbeProjection.scale });
  }, (event) => { const box = deformationCanvas.getBoundingClientRect(); return { x: event.clientX - box.left, y: event.clientY - box.top }; });
}

// Distinguish a click from a pan drag; a double click (fit view) cancels the pending pick.
function bindProbeClicks(canvas, onPick, toScreen) {
  if (!canvas) return;
  let down = null, timer = null;
  canvas.addEventListener("pointerdown", (event) => {
    clearTimeout(timer); timer = null;
    down = event.button === 0 ? { x: event.clientX, y: event.clientY, id: event.pointerId } : null;
  });
  canvas.addEventListener("pointerup", (event) => {
    if (!down || down.id !== event.pointerId) return;
    const moved = Math.hypot(event.clientX - down.x, event.clientY - down.y);
    down = null;
    if (moved > 4) return;
    const screen = toScreen(event);
    timer = setTimeout(() => { timer = null; onPick(screen); }, 260);
  });
  canvas.addEventListener("dblclick", () => { clearTimeout(timer); timer = null; });
}

// Called at the end of renderDeformation with that page's projection.
function drawDeformationProbeMarkers(ctx, view) {
  deformationProbeProjection = view;
  const r = deformationResult, store = resultProbeStores.deformation;
  if (!r) return;
  const data = resultChannels.deformation?.data;
  if (relocateResultProbes(store, r.model, data)) { deformationProbePanel?.resetHistory(); resultProbePanel?.resetHistory(); }
  const index = Number(document.getElementById("deformationFrame").value) || 0, frame = r.frames[index] || r.frames.at(-1);
  if (store.items.length) {
    ResultProbe.drawMarkers2d(ctx, store.items, (probe) => {
      const shift = (axis) => probe.nodeNos.reduce((sum, id, i) => sum + probe.weights[i] * (Number(frame.displacement[id]?.[axis]) || 0), 0);
      const [x, y] = view.project({ x: probe.point[0] + shift(0) * view.scale, y: probe.point[1] + shift(1) * view.scale });
      return { x, y };
    });
  }
  const key = r.runId + ":" + index;
  if (key !== deformationProbeLastKey) { deformationProbeLastKey = key; deformationProbePanel?.refresh(); }
}

initializeResultProbes();
