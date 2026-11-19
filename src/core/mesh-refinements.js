const MAX_MESH_REFINEMENTS = 50;
// Zones saved before transition controls existed keep their original linear
// grading (size + 0.6 * distance), i.e. a growth ratio of 1.6.
const MESH_REFINEMENT_LEGACY_GROWTH = 1.6;
const MESH_REFINEMENT_MIN_GROWTH = 1.05;
const MESH_REFINEMENT_MAX_GROWTH = 3;

// Transition: either `growth` (neighbouring element size ratio, linear size
// field with slope growth - 1) or `transitionWidth` (distance in m over which
// the size blends linearly from the zone size to the global size).
function normalizeMeshRefinementTransition(zone) {
  const hasGrowth = zone.growth !== undefined && zone.growth !== null;
  const hasWidth = zone.transitionWidth !== undefined && zone.transitionWidth !== null;
  if (hasGrowth && hasWidth) throw new Error("过渡方式只能选择增长率或过渡宽度之一。");
  if (hasWidth) {
    if (!Number.isFinite(zone.transitionWidth) || zone.transitionWidth <= 0) throw new Error("过渡宽度须为正数。");
    return { transitionWidth: zone.transitionWidth };
  }
  if (hasGrowth) {
    if (!Number.isFinite(zone.growth) || zone.growth < MESH_REFINEMENT_MIN_GROWTH || zone.growth > MESH_REFINEMENT_MAX_GROWTH) {
      throw new Error("过渡增长率须在 1.05 到 3 之间。");
    }
    return { growth: zone.growth };
  }
  return {};
}

function normalizeMeshRefinements(value = [], dimension) {
  if (!Array.isArray(value) || value.length > MAX_MESH_REFINEMENTS) {
    throw new Error("最多可设置 50 个局部加密区。");
  }
  const minimumSize = dimension === 2 ? 1e-4 : 1e-6;
  return value.map(zone => {
    if (!Array.isArray(zone?.center) || zone.center.length !== dimension || !zone.center.every(Number.isFinite) ||
        !Number.isFinite(zone.size) || zone.size < minimumSize) {
      throw new Error(dimension === 2
        ? "请输入有限的中心坐标，以及不小于 0.0001 m 的目标尺寸。"
        : "请输入有限的中心坐标，以及不小于 0.000001 m 的目标尺寸。");
    }
    const center = [...zone.center];
    if (zone.shape === 'box' || zone.shape === 'ellipsoid') {
      const lengths = zone.lengths;
      if (!Array.isArray(lengths) || lengths.length !== dimension || lengths.some((length, i) =>
        !Number.isFinite(length) || length / 2 <= 0 || !Number.isFinite(Math.abs(center[i]) + length / 2))) {
        throw new Error("请输入各轴方向的正长度。");
      }
      return { shape: zone.shape, center, lengths: [...lengths], size: zone.size, ...normalizeMeshRefinementTransition(zone) };
    }
    if (zone.shape !== undefined && zone.shape !== 'ball') throw new Error("不支持的局部加密区形状。");
    if (!Number.isFinite(zone.radius) || zone.radius <= 0 || center.some(coordinate => !Number.isFinite(Math.abs(coordinate) + zone.radius))) {
      throw new Error("请输入正半径。");
    }
    return { center, radius: zone.radius, size: zone.size, ...normalizeMeshRefinementTransition(zone) };
  });
}

const LOCAL_MESH_STALE_MESSAGE = "局部加密设置已更改，请重新生成网格。";

function meshRefinementGrowth(zone) {
  return zone.growth ?? MESH_REFINEMENT_LEGACY_GROWTH;
}

// Distance from the zone boundary at which the size reaches the global size.
function meshRefinementTransitionLength(zone, globalSize) {
  if (zone.transitionWidth) return zone.transitionWidth;
  if (!(globalSize > zone.size)) return 0;
  return (globalSize - zone.size) / (meshRefinementGrowth(zone) - 1);
}

// Target element size at a distance outside the zone; `globalSize` caps it.
function meshRefinementSizeAtDistance(zone, distanceFromZone, globalSize = Infinity) {
  const distance = Math.max(0, distanceFromZone);
  if (zone.transitionWidth) {
    if (!Number.isFinite(globalSize)) return distance > 0 ? Infinity : zone.size;
    if (distance >= zone.transitionWidth) return Math.max(globalSize, zone.size);
    return zone.size + (globalSize - zone.size) * distance / zone.transitionWidth;
  }
  return Math.min(globalSize, zone.size + (meshRefinementGrowth(zone) - 1) * distance);
}

function describeMeshRefinementTransition(zone) {
  return zone.transitionWidth ? `过渡宽度 ${zone.transitionWidth} m` : `增长率 ${meshRefinementGrowth(zone)}`;
}

function meshRefinementDistanceToSegment(center, a, b) {
  const [x, y] = center;
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const square = dx * dx + dy * dy;
  const t = square ? Math.max(0, Math.min(1, ((x - a.x) * dx + (y - a.y) * dy) / square)) : 0;
  return Math.hypot(x - a.x - t * dx, y - a.y - t * dy);
}

function meshRefinementDistanceFromSegment(zone, a, b) {
  if (!zone.shape) return Math.max(0, meshRefinementDistanceToSegment(zone.center, a, b) - zone.radius);
  const [x, y] = zone.center;
  const [u, v] = zone.lengths.map(length => length / 2);
  const first = { x: a.x - x, y: a.y - y }, last = { x: b.x - x, y: b.y - y };
  if (zone.shape === 'ellipsoid') {
    const radius = meshRefinementDistanceToSegment([0, 0], { x: first.x / u, y: first.y / v }, { x: last.x / u, y: last.y / v });
    return Math.max(0, radius - 1) * Math.min(u, v);
  }
  return meshRefinementBoxDistance(first, last, u, v);
}

function meshRefinementBoxDistance(a, b, u, v) {
  let enter = 0, exit = 1;
  for (const [start, end, limit] of [[a.x, b.x, u], [a.y, b.y, v]]) {
    const step = end - start;
    if (step === 0) {
      if (Math.abs(start) > limit) { enter = Infinity; break; }
      continue;
    }
    const first = (-limit - start) / step, last = (limit - start) / step;
    enter = Math.max(enter, Math.min(first, last));
    exit = Math.min(exit, Math.max(first, last));
  }
  if (enter <= exit) return 0;
  const pointDistance = point => Math.hypot(Math.max(0, Math.abs(point.x) - u), Math.max(0, Math.abs(point.y) - v));
  return Math.min(pointDistance(a), pointDistance(b), ...[[u, v], [u, -v], [-u, v], [-u, -v]]
    .map(corner => meshRefinementDistanceToSegment(corner, a, b)));
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { normalizeMeshRefinements, meshRefinementSizeAtDistance, meshRefinementTransitionLength, meshRefinementGrowth };
}
