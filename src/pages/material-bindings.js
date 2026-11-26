// Base material ↔ specialty material card bindings.
// Left: every base material (fixed). Right: the cards of the specialty library the
// user picks. A base material may be bound to several cards of one library (the
// same material under different constitutive laws); exactly one of them is
// active and used for calculation. Fluids and explosives have their own
// libraries and never appear here.
const MATERIAL_BINDING_LIBRARY_KEY='fem.material-bindings.library';
const MATERIAL_BINDING_LIBRARIES={
  deformation:{label:'损伤变形材料库',page:'deformation-library',module:'deformation',
    cards:()=>deformationMaterialLibrary,list:'deformationMaterialIds',active:'deformationMaterialId'},
  blast:{label:'爆破岩体材料卡',page:'blast-library',module:'blast',
    cards:()=>blastMaterialLibrary,list:'blastMaterialIds',active:'blastMaterialId'},
};
const DEFORMATION_MODEL_NAMES={
  plastic:'J2 塑性 · 各向同性硬化',elastic:'弹性 · 可启用几何非线性',neoHooke:'Neo-Hooke',mooneyRivlin:'Mooney–Rivlin',
  phaseField:'AT2 相场脆性断裂（PhAST）',crackBand:'裂带断裂（三维 OOFEM）',mazars:'Mazars 混凝土损伤（三维 Code_Aster）',
};
const materialBindingState={library:null,busy:false,selected:null,hover:null,drag:null};
const $mb=id=>document.getElementById(id);

function anyProfessionalModuleEnabled(){
  return Boolean((typeof blastModuleEnabled!=='undefined'&&blastModuleEnabled)||(typeof deformationEnabled!=='undefined'&&deformationEnabled)||(typeof fsiEnabled!=='undefined'&&fsiEnabled)
    ||(typeof dynamicsEnabled!=='undefined'&&dynamicsEnabled));
}
// Called whenever a specialty module is switched on or off.
function syncMaterialBindingsAvailability(){
  const visible=anyProfessionalModuleEnabled();
  document.querySelectorAll('[data-professional="any"]').forEach(element=>{element.hidden=!visible;});
  if(!visible&&currentPageKey()==='material-bindings')setPage('materials');
}

function materialBindingSpec(){return MATERIAL_BINDING_LIBRARIES[materialBindingState.library];}
function materialBindingIdsOf(material,spec=materialBindingSpec()){return material?.[spec.list]||[];}
function materialBindingCardLabel(key,entry){
  if(key==='blast')return Blast3dCards.describe(entry.card);
  if(entry.card?.model==='opencourant')return `OpenCourant · ${Blast3dCards.describe(entry.card.oc)}`;
  return DEFORMATION_MODEL_NAMES[entry.card?.model]||entry.card?.model||'';
}
function chooseMaterialBindingLibrary(){
  const select=$mb('materialBindingsLibrary');
  let key=materialBindingState.library;
  if(!key){try{key=localStorage.getItem(MATERIAL_BINDING_LIBRARY_KEY);}catch{/* storage unavailable */}}
  if(!MATERIAL_BINDING_LIBRARIES[key]){
    key=Object.keys(MATERIAL_BINDING_LIBRARIES).find(k=>isProfessionalCalculationEnabled(MATERIAL_BINDING_LIBRARIES[k].module))||'deformation';
  }
  materialBindingState.library=key;
  if(select.options.length!==Object.keys(MATERIAL_BINDING_LIBRARIES).length){
    select.replaceChildren(...Object.entries(MATERIAL_BINDING_LIBRARIES).map(([k,spec])=>new Option(spec.label,k)));
  }
  select.value=key;
}

// Which materials / cards are listed, honouring the name filter and "bound only".
function materialBindingVisibleSets(){
  const spec=materialBindingSpec(),cards=spec.cards();
  const query=$mb('materialBindingsFilter').value.trim().toLowerCase();
  const boundOnly=$mb('materialBindingsBoundOnly').checked;
  const matches=name=>!query||String(name).toLowerCase().includes(query);
  const cardById=new Map(cards.map(card=>[card.id,card]));
  const boundCardIds=new Set(materialLibrary.flatMap(material=>materialBindingIdsOf(material,spec)));
  const materials=materialLibrary.filter(material=>{
    const ids=materialBindingIdsOf(material,spec);
    if(boundOnly&&!ids.length)return false;
    return matches(material.name)||ids.some(id=>matches(cardById.get(id)?.name||''));
  });
  const shownMaterialIds=new Set(materials.map(material=>material.id));
  const visibleCards=cards.filter(card=>{
    if(boundOnly&&!boundCardIds.has(card.id))return false;
    if(matches(card.name))return true;
    return materialLibrary.some(material=>shownMaterialIds.has(material.id)&&matches(material.name)&&materialBindingIdsOf(material,spec).includes(card.id));
  });
  // Order cards beside the materials they belong to so the tree stays untangled.
  const rank=new Map(materials.map((material,index)=>[material.id,index]));
  const weight=card=>{
    const owners=materials.filter(material=>materialBindingIdsOf(material,spec).includes(card.id)).map(material=>rank.get(material.id));
    return owners.length?owners.reduce((a,b)=>a+b,0)/owners.length:Infinity;
  };
  const ordered=visibleCards.map((card,index)=>({card,index,weight:weight(card)}))
    .sort((a,b)=>a.weight-b.weight||(a.weight===Infinity?a.card.name.localeCompare(b.card.name):a.index-b.index)).map(entry=>entry.card);
  return {materials,cards:ordered,cardById};
}

function renderMaterialBindings(){
  if(!$mb('materialBindingsBoard'))return;
  chooseMaterialBindingLibrary();
  const spec=materialBindingSpec(),key=materialBindingState.library;
  const storage=$mb('materialBindingsStorage');
  storage.hidden=materialStorageConnected;storage.textContent=materialStorageConnected?'':materialWriteUnavailable;
  const moduleOff=!isProfessionalCalculationEnabled(spec.module);
  $mb('materialBindingsModuleOff').hidden=!moduleOff;
  const {materials,cards,cardById}=materialBindingVisibleSets();
  $mb('materialBindingsBaseCount').textContent=String(materials.length);
  $mb('materialBindingsCardCount').textContent=String(cards.length);
  const baseList=$mb('materialBindingsBaseList'),cardList=$mb('materialBindingsCardList');
  const openPicker=baseList.querySelector('details[open]')?.closest('[data-material-id]')?.dataset.materialId;
  // Keep keyboard focus on the same control across re-renders.
  const focused=document.activeElement?.closest?.('#materialBindingsBaseList [data-binding-action]');
  let focusKey=focused?[focused.closest('.mb-base-node')?.dataset.materialId,focused.dataset.cardId||focused.closest('.mb-branch')?.dataset.cardId,focused.dataset.bindingAction==='toggle'?'toggle':focused.className]:materialBindingState.pendingFocus;
  if(materialBindingState.busy){materialBindingState.pendingFocus=focusKey;focusKey=null;}
  else materialBindingState.pendingFocus=null;
  baseList.replaceChildren();cardList.replaceChildren();
  if(!materials.length)baseList.append(materialBindingEmpty('没有符合条件的基础材料。'));
  if(!cards.length)cardList.append(materialBindingEmpty(spec.cards().length?'没有符合条件的材料卡。':'该专业库中还没有材料卡。'));
  for(const material of materials)baseList.append(createMaterialBindingBaseNode(material,spec,key,cardById,openPicker===material.id));
  for(const card of cards)cardList.append(createMaterialBindingCardNode(card,spec,key));
  if(!materialBindingState.busy&&materialBindingState.selected&&!materialBindingLinkExists(materialBindingState.selected))materialBindingState.selected=null;
  for(const control of $mb('materialBindingsPage').querySelectorAll('[data-binding-action]'))control.disabled=materialBindingState.busy||!materialStorageConnected;
  if(focusKey){
    const [materialId,cardId,kind]=focusKey;
    const node=[...baseList.querySelectorAll('.mb-base-node')].find(entry=>entry.dataset.materialId===materialId);
    const target=kind==='toggle'?[...(node?.querySelectorAll('input[data-binding-action="toggle"]')||[])].find(box=>box.dataset.cardId===cardId)
      :[...(node?.querySelectorAll('.mb-branch')||[])].find(row=>row.dataset.cardId===cardId)?.querySelector(`.${kind.split(' ')[0]}`);
    target?.focus();
  }
  requestAnimationFrame(()=>drawMaterialBindingLinks(true));
}
function materialBindingEmpty(text){const p=document.createElement('p');p.className='mb-empty';p.textContent=text;return p;}
function materialBindingLinkExists({materialId,cardId}){
  return materialBindingIdsOf(materialById(materialId)).includes(cardId);
}

function createMaterialBindingBaseNode(material,spec,key,cardById,pickerOpen){
  const node=document.createElement('article');node.className='mb-node mb-base-node';node.dataset.materialId=material.id;
  const head=document.createElement('div');head.className='mb-node-head';head.dataset.dragSource='base';
  head.title='拖到右侧材料卡上即可绑定';
  const swatch=document.createElement('i');swatch.className='mb-swatch';swatch.style.background=material.color;
  const text=document.createElement('div');text.className='mb-node-text';
  const name=document.createElement('strong');name.textContent=material.name;
  const detail=document.createElement('small');detail.textContent=materialPropertyLine(material);
  text.append(name,detail);
  const port=document.createElement('span');port.className='mb-port';port.dataset.port='base';
  head.append(swatch,text,port);
  const ids=materialBindingIdsOf(material,spec),active=material[spec.active];
  const branches=document.createElement('ul');branches.className='mb-branches';
  for(const cardId of ids){
    const card=cardById.get(cardId);
    const row=document.createElement('li');row.className='mb-branch';row.dataset.cardId=cardId;
    row.classList.toggle('active',cardId===active);row.classList.toggle('missing',!card);
    const toggle=document.createElement('button');toggle.type='button';toggle.className='mb-activate';toggle.dataset.bindingAction=cardId===active?'deactivate':'activate';
    toggle.setAttribute('aria-pressed',String(cardId===active));
    toggle.title=cardId===active?'已激活（用于计算），点击取消激活':'设为激活（用于计算）';
    const label=document.createElement('span');label.className='mb-branch-text';
    const cardName=document.createElement('strong');cardName.textContent=card?.name||cardId;
    const cardModel=document.createElement('small');cardModel.textContent=card?materialBindingCardLabel(key,card):'材料卡已不存在';
    label.append(cardName,cardModel);
    const state=document.createElement('em');state.className='mb-state';state.textContent=cardId===active?'计算使用':'备用';
    const remove=document.createElement('button');remove.type='button';remove.className='mb-unbind';remove.dataset.bindingAction='unbind';
    remove.title='解除绑定';remove.setAttribute('aria-label','解除绑定');remove.textContent='×';
    const branchPort=document.createElement('span');branchPort.className='mb-branch-port';
    row.append(toggle,label,state,remove,branchPort);
    branches.append(row);
  }
  node.append(head);
  if(ids.length)node.append(branches);
  else{const none=document.createElement('p');none.className='mb-unbound';none.textContent='未绑定，计算时沿用默认本构';node.append(none);}
  if(ids.length&&!active){const warn=document.createElement('p');warn.className='mb-warning';warn.textContent='未激活任何材料卡，计算时沿用默认本构';node.append(warn);}
  node.append(createMaterialBindingPicker(material,spec,key,pickerOpen));
  return node;
}

// Dropdown with one checkbox per card: tick to bind, untick to unbind.
function createMaterialBindingPicker(material,spec,key,open){
  const details=document.createElement('details');details.className='mb-picker';details.open=open;
  const summary=document.createElement('summary');summary.textContent='绑定材料卡';
  const menu=document.createElement('div');menu.className='mb-picker-menu';
  const ids=materialBindingIdsOf(material,spec);
  const cards=spec.cards();
  if(!cards.length)menu.append(materialBindingEmpty('该专业库中还没有材料卡。'));
  for(const card of cards){
    const label=document.createElement('label');label.className='mb-picker-option';
    const box=document.createElement('input');box.type='checkbox';box.checked=ids.includes(card.id);box.dataset.cardId=card.id;box.dataset.bindingAction='toggle';
    const name=document.createElement('span');name.textContent=card.name;
    const model=document.createElement('small');model.textContent=materialBindingCardLabel(key,card);
    label.append(box,name,model);menu.append(label);
  }
  details.append(summary,menu);
  return details;
}

function createMaterialBindingCardNode(card,spec,key){
  const node=document.createElement('article');node.className='mb-node mb-card-node';node.dataset.cardId=card.id;node.dataset.dragSource='card';
  node.title='拖到左侧基础材料上即可绑定';
  const port=document.createElement('span');port.className='mb-port';port.dataset.port='card';
  const text=document.createElement('div');text.className='mb-node-text';
  const name=document.createElement('strong');name.textContent=card.name;
  const model=document.createElement('small');model.textContent=materialBindingCardLabel(key,card);
  text.append(name,model);
  const owners=materialLibrary.filter(material=>materialBindingIdsOf(material,spec).includes(card.id));
  const activeOwners=owners.filter(material=>material[spec.active]===card.id).length;
  const badge=document.createElement('span');badge.className='mb-badge';
  badge.textContent=`${activeOwners}/${owners.length}`;
  badge.title='激活 / 绑定的基础材料数';
  node.classList.toggle('unbound',!owners.length);
  node.append(port,text,badge);
  return node;
}

// ---------------------------------------------------------------- link drawing
function materialBindingPoint(element,side,board){
  const rect=element.getBoundingClientRect(),origin=board.getBoundingClientRect();
  return {x:(side==='right'?rect.right:rect.left)-origin.left+board.scrollLeft,y:rect.top+rect.height/2-origin.top+board.scrollTop};
}
function materialBindingCurve(a,b){
  const dx=Math.max(30,(b.x-a.x)/2);
  return `M${a.x},${a.y} C${a.x+dx},${a.y} ${b.x-dx},${b.y} ${b.x},${b.y}`;
}
// Push each card down to sit level with the first branch bound to it, so the
// links read as a tree instead of drifting diagonally. Cards keep their order.
function alignMaterialBindingCards(board){
  const cards=[...board.querySelectorAll('.mb-card-node')];
  for(const card of cards)card.style.marginTop='';
  const rows=new Map();
  for(const row of board.querySelectorAll('.mb-branch'))if(!rows.has(row.dataset.cardId))rows.set(row.dataset.cardId,row);
  for(const card of cards){
    const row=rows.get(card.dataset.cardId);
    if(!row)continue;
    const r=row.getBoundingClientRect(),c=card.getBoundingClientRect();
    const wanted=(r.top+r.height/2)-(c.top+c.height/2);
    if(wanted>1)card.style.marginTop=`${wanted}px`;
  }
}
function drawMaterialBindingLinks(align=false){
  const board=$mb('materialBindingsBoard'),svg=$mb('materialBindingsLinks');
  if(!board||board.offsetParent===null)return;
  if(align===true&&!materialBindingState.drag)alignMaterialBindingCards(board);
  const spec=materialBindingSpec();
  svg.setAttribute('width',board.scrollWidth);svg.setAttribute('height',board.scrollHeight);
  svg.replaceChildren();
  const cardNodes=new Map([...board.querySelectorAll('.mb-card-node')].map(node=>[node.dataset.cardId,node]));
  const {hover,selected}=materialBindingState;
  const links=[];
  for(const node of board.querySelectorAll('.mb-base-node')){
    const material=materialById(node.dataset.materialId);
    for(const row of node.querySelectorAll('.mb-branch')){
      const target=cardNodes.get(row.dataset.cardId);
      if(!target)continue;
      const link={materialId:node.dataset.materialId,cardId:row.dataset.cardId,active:material?.[spec.active]===row.dataset.cardId,
        from:materialBindingPoint(row,'right',board),to:materialBindingPoint(target,'left',board)};
      link.highlight=hover&&(hover.materialId===link.materialId||hover.cardId===link.cardId);
      link.selected=selected&&selected.materialId===link.materialId&&selected.cardId===link.cardId;
      links.push(link);
    }
  }
  // Inactive links first so the active ones sit on top.
  links.sort((a,b)=>Number(a.active)-Number(b.active)||Number(a.highlight||a.selected)-Number(b.highlight||b.selected));
  const ns='http://www.w3.org/2000/svg';
  for(const link of links){
    const d=materialBindingCurve(link.from,link.to);
    const group=document.createElementNS(ns,'g');
    group.setAttribute('class',['mb-link',link.active?'active':'bound',link.highlight?'hl':'',hover&&!link.highlight?'dim':'',link.selected?'selected':''].filter(Boolean).join(' '));
    group.dataset.materialId=link.materialId;group.dataset.cardId=link.cardId;
    const hit=document.createElementNS(ns,'path');hit.setAttribute('d',d);hit.setAttribute('class','mb-link-hit');
    const line=document.createElementNS(ns,'path');line.setAttribute('d',d);line.setAttribute('class','mb-link-line');
    const end=document.createElementNS(ns,'circle');end.setAttribute('cx',link.to.x);end.setAttribute('cy',link.to.y);end.setAttribute('r',3.5);end.setAttribute('class','mb-link-end');
    const title=document.createElementNS(ns,'title');title.textContent=link.active?'激活（用于计算）':'已绑定未激活';
    group.append(title,hit,line,end);
    svg.append(group);
  }
  if(materialBindingState.drag?.path)svg.append(materialBindingState.drag.path);
  for(const node of board.querySelectorAll('.mb-base-node,.mb-card-node')){
    const linked=hover&&(node.dataset.materialId?links.some(l=>l.highlight&&l.materialId===node.dataset.materialId):links.some(l=>l.highlight&&l.cardId===node.dataset.cardId));
    const own=hover&&(hover.materialId?node.dataset.materialId===hover.materialId:node.dataset.cardId===hover.cardId&&!node.dataset.materialId);
    node.classList.toggle('hl',Boolean(linked||own));
    node.classList.toggle('dim',Boolean(hover&&!linked&&!own));
  }
  positionMaterialBindingActions(links.find(link=>link.selected));
}
function positionMaterialBindingActions(link){
  const bar=$mb('materialBindingsLinkActions');
  bar.hidden=!link;
  if(!link)return;
  const material=materialById(link.materialId),card=materialBindingSpec().cards().find(entry=>entry.id===link.cardId);
  $mb('materialBindingsLinkName').textContent=`${material?.name||''} → ${card?.name||link.cardId}`;
  const activate=$mb('materialBindingsLinkActivate');
  activate.textContent=link.active?'取消激活':'设为激活';
  activate.dataset.bindingAction=link.active?'deactivate':'activate';
  bar.style.left=`${(link.from.x+link.to.x)/2}px`;bar.style.top=`${(link.from.y+link.to.y)/2}px`;
}

// ---------------------------------------------------------------- persistence
async function applyMaterialBindingOperation(operation){
  if(materialBindingState.busy)return;
  const status=$mb('materialBindingsStatus');
  if(!materialStorageConnected){status.textContent=materialWriteUnavailable;return;}
  materialBindingState.busy=true;renderMaterialBindings();
  try{
    const response=await fetch('./api/material-bindings',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({library:materialBindingState.library,...operation})});
    if(response.status===404||response.status===405)throw Error(legacyMaterialServiceMessage);
    const payload=await response.json();
    if(!response.ok)throw Error(payload.error||`HTTP ${response.status}`);
    applyProjectMaterials(payload);
    syncMaterialBindingConsumers();
    status.textContent={bind:'已绑定。',unbind:'已解除绑定。',activate:'已激活，计算将使用该材料卡。',deactivate:'已取消激活。'}[operation.action]||'';
  }catch(error){status.textContent=error.message;}
  finally{materialBindingState.busy=false;renderMaterialBindings();}
}
// Other pages read the active card ids; refresh whatever is already on screen.
function syncMaterialBindingConsumers(){
  if(materialBindingState.library==='blast')window.dispatchEvent(new Event('tensora-blast-materials-changed'));
  else window.dispatchEvent(new Event('tensora-deformation-materials-changed'));
  if(typeof renderDeformationMaterials==='function'&&currentPageKey()==='deformation')renderDeformationMaterials();
}

// ---------------------------------------------------------------- interaction
function materialBindingTargetAt(x,y,kind){
  const element=document.elementFromPoint(x,y);
  return element?.closest(kind==='base'?'.mb-card-node':'.mb-base-node')||null;
}
function startMaterialBindingDrag(event){
  const source=event.target.closest('[data-drag-source]');
  if(!source||event.button!==0||event.target.closest('button,input,summary,details,a'))return;
  const board=$mb('materialBindingsBoard');
  const kind=source.dataset.dragSource;
  const node=source.closest('.mb-node');
  const port=node.querySelector(':scope > .mb-node-head > .mb-port, :scope > .mb-port');
  materialBindingState.drag={kind,node,port,startX:event.clientX,startY:event.clientY,moved:false,path:null,target:null,pointerId:event.pointerId};
  board.setPointerCapture?.(event.pointerId);
}
function moveMaterialBindingDrag(event){
  const drag=materialBindingState.drag,board=$mb('materialBindingsBoard');
  if(!drag){
    const node=event.target.closest?.('.mb-node');
    const hover=node?(node.dataset.materialId?{materialId:node.dataset.materialId}:{cardId:node.dataset.cardId}):null;
    if(JSON.stringify(hover)!==JSON.stringify(materialBindingState.hover)){materialBindingState.hover=hover;drawMaterialBindingLinks();}
    return;
  }
  if(!drag.moved&&Math.hypot(event.clientX-drag.startX,event.clientY-drag.startY)<5)return;
  if(!drag.moved){
    drag.moved=true;board.classList.add('dragging');drag.node.classList.add('drag-source');
    drag.path=document.createElementNS('http://www.w3.org/2000/svg','path');drag.path.setAttribute('class','mb-drag-line');
    $mb('materialBindingsLinks').append(drag.path);
  }
  const origin=board.getBoundingClientRect();
  const pointer={x:event.clientX-origin.left+board.scrollLeft,y:event.clientY-origin.top+board.scrollTop};
  const anchor=materialBindingPoint(drag.port,drag.kind==='base'?'right':'left',board);
  drag.path.setAttribute('d',drag.kind==='base'?materialBindingCurve(anchor,pointer):materialBindingCurve(pointer,anchor));
  const target=materialBindingTargetAt(event.clientX,event.clientY,drag.kind);
  if(target!==drag.target){drag.target?.classList.remove('drop-target');target?.classList.add('drop-target');drag.target=target;}
}
function endMaterialBindingDrag(event){
  const drag=materialBindingState.drag;
  if(!drag)return;
  materialBindingState.drag=null;
  const board=$mb('materialBindingsBoard');
  board.classList.remove('dragging');drag.node.classList.remove('drag-source');drag.target?.classList.remove('drop-target');
  drag.path?.remove();
  if(board.hasPointerCapture?.(drag.pointerId))board.releasePointerCapture(drag.pointerId);
  // The click that follows a drag lands on the board (pointer capture); ignore it.
  if(drag.moved){materialBindingState.suppressClick=true;setTimeout(()=>{materialBindingState.suppressClick=false;},0);}
  if(!drag.moved||event.type==='pointercancel'||!drag.target)return;
  const materialId=drag.kind==='base'?drag.node.dataset.materialId:drag.target.dataset.materialId;
  const cardId=drag.kind==='base'?drag.target.dataset.cardId:drag.node.dataset.cardId;
  if(materialBindingIdsOf(materialById(materialId)).includes(cardId)){
    $mb('materialBindingsStatus').textContent='这两项已经绑定。';
    materialBindingState.selected={materialId,cardId};drawMaterialBindingLinks();
    return;
  }
  materialBindingState.selected={materialId,cardId};
  applyMaterialBindingOperation({action:'bind',materialId,cardId});
}

function initializeMaterialBindings(){
  const page=$mb('materialBindingsPage');
  if(!page)return;
  const board=$mb('materialBindingsBoard');
  $mb('materialBindingsLibrary').addEventListener('change',event=>{
    materialBindingState.library=event.target.value;materialBindingState.selected=null;
    try{localStorage.setItem(MATERIAL_BINDING_LIBRARY_KEY,materialBindingState.library);}catch{/* storage unavailable */}
    $mb('materialBindingsStatus').textContent='';
    renderMaterialBindings();
  });
  $mb('materialBindingsFilter').addEventListener('input',renderMaterialBindings);
  $mb('materialBindingsBoundOnly').addEventListener('change',renderMaterialBindings);
  $mb('materialBindingsOpenLibrary').addEventListener('click',()=>{
    const spec=materialBindingSpec();
    if(spec.page==='blast-library'){const kind=$mb('blastLibraryKind');if(kind){kind.value='material';kind.dispatchEvent(new Event('change'));}}
    setPage(spec.page);
  });
  board.addEventListener('pointerdown',startMaterialBindingDrag);
  board.addEventListener('pointermove',moveMaterialBindingDrag);
  board.addEventListener('pointerup',endMaterialBindingDrag);
  board.addEventListener('pointercancel',endMaterialBindingDrag);
  board.addEventListener('pointerleave',()=>{if(!materialBindingState.drag&&materialBindingState.hover){materialBindingState.hover=null;drawMaterialBindingLinks();}});
  board.addEventListener('click',event=>{
    if(materialBindingState.suppressClick){materialBindingState.suppressClick=false;return;}
    const link=event.target.closest('.mb-link');
    if(link){
      const next={materialId:link.dataset.materialId,cardId:link.dataset.cardId};
      const same=materialBindingState.selected?.materialId===next.materialId&&materialBindingState.selected?.cardId===next.cardId;
      materialBindingState.selected=same?null:next;drawMaterialBindingLinks();return;
    }
    const action=event.target.closest('button[data-binding-action]');
    if(action&&!action.closest('#materialBindingsLinkActions')){
      const row=action.closest('.mb-branch'),node=action.closest('.mb-base-node');
      if(row&&node)applyMaterialBindingOperation({action:action.dataset.bindingAction,materialId:node.dataset.materialId,cardId:row.dataset.cardId});
      return;
    }
    const branch=event.target.closest('.mb-branch');
    if(branch){
      materialBindingState.selected={materialId:branch.closest('.mb-base-node').dataset.materialId,cardId:branch.dataset.cardId};
      drawMaterialBindingLinks();return;
    }
    if(!event.target.closest('.mb-node,#materialBindingsLinkActions')&&materialBindingState.selected){materialBindingState.selected=null;drawMaterialBindingLinks();}
  });
  board.addEventListener('change',event=>{
    const box=event.target.closest('input[data-binding-action="toggle"]');
    if(!box)return;
    const materialId=box.closest('.mb-base-node').dataset.materialId;
    applyMaterialBindingOperation({action:box.checked?'bind':'unbind',materialId,cardId:box.dataset.cardId});
  });
  // Opening one dropdown closes the others; clicking elsewhere closes it.
  board.addEventListener('toggle',event=>{
    if(event.target.matches?.('details.mb-picker')&&event.target.open)for(const other of board.querySelectorAll('details.mb-picker[open]'))if(other!==event.target)other.open=false;
    requestAnimationFrame(drawMaterialBindingLinks);
  },true);
  document.addEventListener('pointerdown',event=>{
    if(event.target.closest?.('details.mb-picker'))return;
    for(const open of board.querySelectorAll('details.mb-picker[open]'))open.open=false;
  });
  const actions=$mb('materialBindingsLinkActions');
  actions.addEventListener('click',event=>{
    const button=event.target.closest('button[data-binding-action]'),selected=materialBindingState.selected;
    if(!button||!selected)return;
    if(button.dataset.bindingAction==='unbind')materialBindingState.selected=null;
    applyMaterialBindingOperation({action:button.dataset.bindingAction,...selected});
  });
  document.addEventListener('keydown',event=>{
    if(currentPageKey()!=='material-bindings'||!materialBindingState.selected)return;
    if(event.target.closest?.('input,select,textarea'))return;
    if(event.key==='Delete'||event.key==='Backspace'){
      event.preventDefault();
      const selected=materialBindingState.selected;materialBindingState.selected=null;
      applyMaterialBindingOperation({action:'unbind',...selected});
    }else if(event.key==='Escape'){materialBindingState.selected=null;drawMaterialBindingLinks();}
  });
  // Width changes reflow the text; realign. (Height changes come from the alignment itself.)
  let observedWidth=0;
  if(typeof ResizeObserver==='function')new ResizeObserver(([entry])=>{
    const width=Math.round(entry.contentRect.width);
    drawMaterialBindingLinks(width!==observedWidth);observedWidth=width;
  }).observe(board);
  syncMaterialBindingsAvailability();
}
