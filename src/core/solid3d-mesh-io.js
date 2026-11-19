// Keep JSON requests and imports below the string limit of the desktop runtime.
export const SOLID_MODEL_BYTES_LIMIT = 400_000_000;

export function* jsonArray(count, get) {
  yield '[';
  const batch = 4096;
  for (let start = 0; start < count; start += batch) {
    const end = Math.min(start + batch, count);
    const values = [];
    for (let i = start; i < end; i++) values.push(JSON.stringify(get(i)) ?? 'null');
    if (start) yield ',';
    yield values.join(',');
  }
  yield ']';
}

export function* solidMeshJson(mesh) {
  if (!mesh) { yield 'null'; return; }
  const { nodes, tets, tetVolumes, ...metadata } = mesh;
  const header = JSON.stringify(metadata);
  yield header.slice(0, -1);
  let needsComma = header.length > 2;
  for (const [key, values] of Object.entries({ nodes, tets, tetVolumes })) {
    if (values === undefined) continue;
    if (needsComma) yield ',';
    yield JSON.stringify(key) + ':';
    if (Array.isArray(values)) yield* jsonArray(values.length, i => values[i]);
    else yield JSON.stringify(values);
    needsComma = true;
  }
  yield '}';
}

export function* solidModelJson(model) {
  const { mesh, ...metadata } = model;
  if (mesh === undefined) { yield JSON.stringify(model); return; }
  const header = JSON.stringify(metadata);
  yield header.slice(0, -1);
  if (header.length > 2) yield ',';
  yield '"mesh":';
  yield* solidMeshJson(mesh);
  yield '}';
}
