'use strict';

// In 2D, an X restraint suppresses tx - y*rotation, and a Y restraint
// suppresses ty + x*rotation. With both translation axes restrained,
// rotation is suppressed if either set has a nonzero transverse span.
function validateStaticRestraints(nodes, elements) {
  const parents = new Map();
  function root(id) {
    while (parents.get(id) !== id) {
      parents.set(id, parents.get(parents.get(id)));
      id = parents.get(id);
    }
    return id;
  }
  for (const { node1, node2, node3 } of elements) {
    for (const id of [node1, node2, node3]) {
      if (!parents.has(id)) parents.set(id, id);
    }
    const group = root(node1);
    parents.set(root(node2), group);
    parents.set(root(node3), group);
  }
  const groups = new Map();
  for (const n of nodes) {
    if (!parents.has(n.nodeNo)) continue;
    const id = root(n.nodeNo);
    if (!groups.has(id)) groups.set(id, {
      nodeNo: n.nodeNo, minX: n.x, maxX: n.x, minY: n.y, maxY: n.y,
      minFixedX: Infinity, maxFixedX: -Infinity, minFixedY: Infinity, maxFixedY: -Infinity,
    });
    const g = groups.get(id);
    g.minX = Math.min(g.minX, n.x); g.maxX = Math.max(g.maxX, n.x);
    g.minY = Math.min(g.minY, n.y); g.maxY = Math.max(g.maxY, n.y);
    if (n.fixUx) {
      g.minFixedY = Math.min(g.minFixedY, n.y); g.maxFixedY = Math.max(g.maxFixedY, n.y);
    }
    if (n.fixUy) {
      g.minFixedX = Math.min(g.minFixedX, n.x); g.maxFixedX = Math.max(g.maxFixedX, n.x);
    }
  }
  for (const g of groups.values()) {
    const tolerance = 1e-10 * Math.max(g.maxX - g.minX, g.maxY - g.minY);
    const missing = [];
    if (g.minFixedY === Infinity) missing.push('X');
    if (g.minFixedX === Infinity) missing.push('Y');
    if (!missing.length && Math.max(g.maxFixedX - g.minFixedX, g.maxFixedY - g.minFixedY) <= tolerance) missing.push('Rz');
    if (missing.length) throw Error(`网格连通体（含计算节点 ${g.nodeNo}）缺少独立约束（${missing.join('、')}），请检查支撑并重新生成网格。`);
  }
}

module.exports = { validateStaticRestraints };
