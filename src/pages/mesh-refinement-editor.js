function createMeshRefinementEditor(form, { getZones, setZones, validate, onPicking }) {
  const coordinates = [...form.querySelectorAll('[data-refinement-coordinate]')];
  const lengths = [...form.querySelectorAll('[data-refinement-length]')];
  const shape = form.elements.shape;
  const shapeLabels = coordinates.length === 2
    ? { ball: '圆形', box: '矩形', ellipsoid: '椭圆' }
    : { ball: '球形', box: '长方体', ellipsoid: '椭球' };
  const radius = form.elements.radius;
  const size = form.elements.size;
  const pick = form.querySelector('[data-refinement-pick]');
  const save = form.querySelector('[type=submit]');
  const cancel = form.querySelector('[data-refinement-cancel]');
  const list = form.querySelector('[data-refinement-list]');
  const status = form.querySelector('[data-refinement-status]');
  let shownZones;
  let editing = -1;
  let picking = false;

  function syncShapeFields() {
    const round = shape.value === 'ball';
    radius.closest('label').hidden = !round;
    lengths.forEach(input => { input.closest('label').hidden = round; });
  }

  function setPicking(active) {
    picking = active;
    pick.setAttribute('aria-pressed', String(active));
    onPicking(active);
  }

  function reset() {
    editing = -1;
    form.reset();
    syncShapeFields();
    save.textContent = '添加加密区';
    cancel.hidden = true;
    status.textContent = '';
    setPicking(false);
  }

  function setCenter(center) {
    coordinates.forEach((input, index) => { input.value = String(Number(center[index].toPrecision(12))); });
    setPicking(false);
    status.textContent = '';
  }

  function sync() {
    const zones = getZones();
    if (shownZones === zones) return;
    shownZones = zones;
    reset();
    list.replaceChildren();
    zones.forEach((zone, index) => {
      const row = document.createElement('li');
      const position = document.createElement('span');
      const shapeLabel = document.createElement('strong');
      shapeLabel.textContent = shapeLabels[zone.shape || 'ball'];
      const extent = zone.lengths ? zone.lengths.join(' × ') : `r ${zone.radius}`;
      position.append(shapeLabel, ` · (${zone.center.map(value => Number(value.toPrecision(6))).join(', ')}) · ${extent} m · h ${zone.size} m`);
      position.title = `(${zone.center.join(', ')})`;
      const actions = document.createElement('div');
      const edit = document.createElement('button');
      edit.type = 'button';
      edit.textContent = '编辑';
      edit.addEventListener('click', () => {
        editing = index;
        coordinates.forEach((input, axis) => { input.value = String(zone.center[axis]); });
        shape.value = zone.shape || 'ball';
        radius.value = zone.radius ?? '';
        lengths.forEach((input, axis) => { input.value = zone.lengths?.[axis] ?? ''; });
        syncShapeFields();
        size.value = String(zone.size);
        save.textContent = '保存加密区';
        cancel.hidden = false;
        status.textContent = '';
        coordinates[0].focus();
      });
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.textContent = '删除';
      remove.addEventListener('click', () => {
        try { setZones(zones.filter((_, i) => i !== index)); sync(); }
        catch (error) { status.textContent = error.message; }
      });
      actions.append(edit, remove);
      row.append(position, actions);
      list.append(row);
    });
  }

  form.addEventListener('submit', event => {
    event.preventDefault();
    const zone = { shape: shape.value, center: coordinates.map(input => input.valueAsNumber), size: size.valueAsNumber };
    if (shape.value === 'ball') zone.radius = radius.valueAsNumber;
    else zone.lengths = lengths.map(input => input.valueAsNumber);
    try {
      const next = [...getZones()];
      next[editing < 0 ? next.length : editing] = zone;
      const normalized = normalizeMeshRefinements(next, coordinates.length);
      validate?.(zone);
      setZones(normalized);
      sync();
    } catch (error) {
      status.textContent = error.message;
    }
  });
  pick.addEventListener('click', () => {
    setPicking(!picking);
    status.textContent = picking ? '请在视窗中拾取加密中心。' : '';
  });
  shape.addEventListener('change', syncShapeFields);
  cancel.addEventListener('click', reset);
  form.addEventListener('keydown', event => { if (event.key === 'Escape') reset(); });
  const stopPicking = () => {
    if (picking) { setPicking(false); status.textContent = ''; }
  };
  const details = form.closest('details');
  details.addEventListener('toggle', () => { if (!details.open) stopPicking(); });

  return { sync, setCenter, isPicking: () => picking, stopPicking };
}
