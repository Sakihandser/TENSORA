function createMeshRefinementEditor(form, { getZones, setZones, validate, onPicking, getGlobalSize }) {
  const coordinates = [...form.querySelectorAll('[data-refinement-coordinate]')];
  const lengths = [...form.querySelectorAll('[data-refinement-length]')];
  const shape = form.elements.shape;
  const shapeLabels = coordinates.length === 2
    ? { ball: '圆形', box: '矩形', ellipsoid: '椭圆' }
    : { ball: '球形', box: '长方体', ellipsoid: '椭球' };
  const radius = form.elements.radius;
  const size = form.elements.size;
  const transition = form.elements.transition;
  const growth = form.elements.growth;
  const transitionWidth = form.elements.transitionWidth;
  const transitionNote = form.querySelector('[data-refinement-transition-note]');
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

  const formatLength = value => String(Number(value.toPrecision(3)));

  // Explain the transition the user is setting, using the current global size when known.
  function syncTransitionFields() {
    const byWidth = transition.value === 'width';
    growth.closest('label').hidden = byWidth;
    transitionWidth.closest('label').hidden = !byWidth;
    const global = Number(getGlobalSize?.());
    const target = size.valueAsNumber;
    const lines = [byWidth
      ? '加密区外该距离内，单元尺寸由目标尺寸线性增大到全局尺寸。'
      : '相邻单元尺寸之比：1.1–1.3 过渡平缓，1.5 以上过渡较快。'];
    if (global > 0 && target > 0 && target < global) {
      if (byWidth && transitionWidth.valueAsNumber > 0) {
        lines.push(`全局尺寸 ${formatLength(global)} m，等效增长率约 ${formatLength(1 + (global - target) / transitionWidth.valueAsNumber)}。`);
      } else if (!byWidth && growth.valueAsNumber > 1) {
        const rate = growth.valueAsNumber;
        const layers = Math.ceil(Math.log(global / target) / Math.log(rate));
        lines.push(`全局尺寸 ${formatLength(global)} m，过渡区约 ${formatLength((global - target) / (rate - 1))} m（约 ${layers} 层单元）。`);
      }
    } else if (global > 0 && target >= global) {
      lines.push('目标尺寸不小于全局尺寸时，该加密区不起作用。');
    }
    const key = lines.join('\n');
    if (transitionNote.dataset.source === key) return;
    transitionNote.dataset.source = key;
    transitionNote.replaceChildren(...lines.map(line => {
      const span = document.createElement('span');
      span.textContent = line;
      return span;
    }));
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
    syncTransitionFields();
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
      const transitionLabel = document.createElement('span');
      transitionLabel.textContent = describeMeshRefinementTransition(zone);
      position.append(shapeLabel, ` · (${zone.center.map(value => Number(value.toPrecision(6))).join(', ')}) · ${extent} m · h ${zone.size} m · `, transitionLabel);
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
        transition.value = zone.transitionWidth ? 'width' : 'growth';
        growth.value = String(meshRefinementGrowth(zone));
        transitionWidth.value = zone.transitionWidth ?? '';
        syncTransitionFields();
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
    if (transition.value === 'width') zone.transitionWidth = transitionWidth.valueAsNumber;
    else zone.growth = growth.valueAsNumber;
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
  transition.addEventListener('change', syncTransitionFields);
  for (const input of [size, growth, transitionWidth]) input.addEventListener('input', syncTransitionFields);
  cancel.addEventListener('click', reset);
  form.addEventListener('keydown', event => { if (event.key === 'Escape') reset(); });
  const stopPicking = () => {
    if (picking) { setPicking(false); status.textContent = ''; }
  };
  const details = form.closest('details');
  details.addEventListener('toggle', () => { if (!details.open) stopPicking(); });

  return { sync, setCenter, isPicking: () => picking, stopPicking, refreshTransitionNote: syncTransitionFields };
}
