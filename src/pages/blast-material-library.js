// Rock material cards for the 3D blast workspace (blast library, "material" kind).
// Cards are stored in materials/materials.json (blastMaterials) and linked to
// base materials through material.blastMaterialId, like deformation cards.
let blastMaterialCardId=null;
const blastMaterialElement=id=>document.getElementById(id);
function blastMaterialStatus(text){blastMaterialElement('blastMaterialStatus').textContent=text;}
function blastMaterialLinkedNames(cardId){
  return materialLibrary.filter(material=>material.blastMaterialId===cardId).map(material=>material.name);
}
function renderBlastMaterialList(){
  const list=blastMaterialElement('blastLibraryList');
  list.replaceChildren();
  blastMaterialElement('blastLibraryCount').textContent=String(blastMaterialLibrary.length);
  if(!blastMaterialLibrary.length){
    const empty=document.createElement('p');empty.className='blast-note';empty.textContent='暂无已保存的岩体材料卡。';list.append(empty);
  }
  for(const entry of blastMaterialLibrary){
    const button=document.createElement('button');button.type='button';button.className='blast-library-item';
    button.classList.toggle('active',entry.id===blastMaterialCardId);
    const name=document.createElement('strong');name.textContent=entry.name;
    const detail=document.createElement('small');
    const names=blastMaterialLinkedNames(entry.id);
    detail.textContent=`${Blast3dCards.describe(entry.card)} · ${names.length?names.join('、'):'未关联基础材料'}`;
    button.append(name,document.createElement('br'),detail);
    button.addEventListener('click',()=>openBlastMaterialCard(entry));
    list.append(button);
  }
}
function blastMaterialNumberField(host,key,label,scale,value,prefix){
  const field=document.createElement('label');field.className='material-field';
  const text=document.createElement('span');text.textContent=label;
  const input=document.createElement('input');input.type='number';input.step='any';input.id=`${prefix}-${key}`;
  input.dataset.key=key;input.dataset.scale=String(scale);
  input.value=Number.isFinite(value)?String(Number((value/scale).toPrecision(12))):'';
  field.append(text,input);host.append(field);
}
function renderBlastMaterialFields(card){
  const host=blastMaterialElement('blastMaterialFields');host.replaceChildren();
  const model=blastMaterialElement('blastMaterialModel').value;
  const defaults=Blast3dCards.DEFAULTS[model]||{},values=card?.model===model?card:defaults;
  for(const [key,label,scale] of Blast3dCards.FIELDS[model]||[])blastMaterialNumberField(host,key,label,scale,Number.isFinite(values[key])?values[key]:defaults[key],'blast-card');
  blastMaterialElement('blastMaterialHelp').textContent=Blast3dCards.MODELS.find(m=>m.id===model)?.help||'';
  if(model==='dp'){
    const note=document.createElement('p');note.className='blast-note';note.id='blastMaterialDpNote';host.append(note);
    const update=()=>{
      try{
        const dp=Blast3dCards.druckerPrager(readBlastMaterialCard());
        note.textContent=`换算：√J2 = ${(dp.k/1e6).toPrecision(4)} MPa + ${dp.alpha.toPrecision(4)}·p；A0 = ${dp.A0.toExponential(3)} Pa²，A1 = ${dp.A1.toExponential(3)} Pa，A2 = ${dp.A2.toPrecision(4)}，P_min = ${(dp.pMin/1e6).toPrecision(4)} MPa。`;
      }catch{note.textContent='';}
    };
    host.addEventListener('input',update);update();
  }
}
function openBlastMaterialCard(record){
  blastMaterialCardId=record?.id||null;
  const card=Blast3dCards.normalize(record?.card||{model:'jh2'});
  blastMaterialElement('blastMaterialTitle').textContent=record?record.name:'新建材料卡';
  blastMaterialElement('blastMaterialName').value=record?.name||'';
  blastMaterialElement('blastMaterialSource').value=record?.sourceUrl||'';
  blastMaterialElement('blastMaterialNotes').value=record?.notes||'';
  blastMaterialElement('blastMaterialModel').value=card.model;
  renderBlastMaterialFields(card);
  blastMaterialElement('blastMaterialFailure').checked=card.failure.enabled;
  const failure=blastMaterialElement('blastMaterialFailureFields');failure.replaceChildren();
  for(const [key,label,scale] of Blast3dCards.FIELDS.failure)blastMaterialNumberField(failure,key,label,scale,card.failure[key],'blast-failure');
  syncBlastMaterialFailure();
  blastMaterialElement('blastMaterialDelete').disabled=!record;
  blastMaterialStatus('');
  renderBlastMaterialList();renderBlastMaterialLinks();
}
function syncBlastMaterialFailure(){
  const enabled=blastMaterialElement('blastMaterialFailure').checked;
  for(const input of blastMaterialElement('blastMaterialFailureFields').querySelectorAll('input'))input.disabled=!enabled;
}
function readBlastMaterialCard(){
  const read=host=>Object.fromEntries([...host.querySelectorAll('input[data-key]')].map(input=>[input.dataset.key,
    input.value.trim()===''?NaN:Number(input.value)*Number(input.dataset.scale)]));
  return {model:blastMaterialElement('blastMaterialModel').value,...read(blastMaterialElement('blastMaterialFields')),
    failure:{enabled:blastMaterialElement('blastMaterialFailure').checked,...read(blastMaterialElement('blastMaterialFailureFields'))}};
}
async function postBlastMaterial(endpoint,data){
  if(!materialStorageConnected)throw Error(materialWriteUnavailable);
  const response=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  if(response.status===404||response.status===405)throw Error(legacyMaterialServiceMessage);
  const payload=await response.json();
  if(!response.ok)throw Error(payload.error||`HTTP ${response.status}`);
  applyProjectMaterials(payload);
  renderBlastMaterialLink(materialById(materialUi.id.value)?.blastMaterialId);
  window.dispatchEvent(new Event('tensora-blast-materials-changed'));
}
async function saveBlastMaterialCard(copy){
  try{
    const record=Blast3dCards.normalizeLibraryCard({
      id:!copy&&blastMaterialCardId?blastMaterialCardId:'blastmat-'+crypto.randomUUID(),
      name:blastMaterialElement('blastMaterialName').value,sourceUrl:blastMaterialElement('blastMaterialSource').value,
      notes:blastMaterialElement('blastMaterialNotes').value,card:readBlastMaterialCard()});
    await postBlastMaterial('./api/blast-materials',record);
    openBlastMaterialCard(blastMaterialLibrary.find(entry=>entry.id===record.id));
    blastMaterialStatus('材料卡已保存。');
  }catch(error){blastMaterialStatus(error.message);}
}
async function deleteBlastMaterialCard(){
  if(!blastMaterialCardId)return;
  const names=blastMaterialLinkedNames(blastMaterialCardId);
  if(!window.confirm(names.length?`删除所选材料卡？以下基础材料的关联将被解除：${names.join('、')}`:'删除所选材料卡？'))return;
  try{
    await postBlastMaterial('./api/blast-materials',{remove:blastMaterialCardId});
    openBlastMaterialCard(blastMaterialLibrary[0]||null);
    blastMaterialStatus('已删除所选材料卡。');
  }catch(error){blastMaterialStatus(error.message);}
}
function renderBlastMaterialLinks(){
  const base=blastMaterialElement('blastMaterialLinkBase'),card=blastMaterialElement('blastMaterialLinkCard');
  const previous=base.value;
  base.replaceChildren(...materialLibrary.map(entry=>new Option(entry.name,entry.id)));
  if(materialLibrary.some(entry=>entry.id===previous))base.value=previous;
  const linked=materialById(base.value)?.blastMaterialId;
  card.replaceChildren(new Option('不关联（沿用二维爆破本构）',''),...blastMaterialLibrary.map(entry=>new Option(entry.name,entry.id)));
  if(linked&&!blastMaterialLibrary.some(entry=>entry.id===linked))card.add(new Option(linked,linked));
  card.value=linked||'';
  blastMaterialElement('blastMaterialLinkSave').disabled=!materialStorageConnected||!base.value;
  const list=blastMaterialElement('blastMaterialLinks');list.replaceChildren();
  for(const material of materialLibrary.filter(entry=>entry.blastMaterialId)){
    const item=document.createElement('li');
    const cardName=blastMaterialLibrary.find(entry=>entry.id===material.blastMaterialId)?.name||material.blastMaterialId;
    item.textContent=`${material.name} → ${cardName}`;list.append(item);
  }
}
function renderBlastMaterialLibrary(){
  if(!blastMaterialLibrary.some(entry=>entry.id===blastMaterialCardId))blastMaterialCardId=null;
  openBlastMaterialCard(blastMaterialLibrary.find(entry=>entry.id===blastMaterialCardId)||blastMaterialLibrary[0]||null);
}
function initializeBlastMaterialLibrary(){
  const model=blastMaterialElement('blastMaterialModel');
  model.replaceChildren(...Blast3dCards.MODELS.map(entry=>new Option(entry.name,entry.id)));
  model.addEventListener('change',()=>renderBlastMaterialFields(null));
  blastMaterialElement('blastMaterialFailure').addEventListener('change',syncBlastMaterialFailure);
  blastMaterialElement('blastMaterialForm').addEventListener('submit',event=>{event.preventDefault();saveBlastMaterialCard(false);});
  blastMaterialElement('blastMaterialCopy').addEventListener('click',()=>saveBlastMaterialCard(true));
  blastMaterialElement('blastMaterialDelete').addEventListener('click',deleteBlastMaterialCard);
  blastMaterialElement('blastMaterialLinkBase').addEventListener('change',()=>{blastMaterialElement('blastMaterialLinkStatus').textContent='';renderBlastMaterialLinks();});
  blastMaterialElement('blastMaterialLinkForm').addEventListener('submit',async event=>{
    event.preventDefault();
    const status=blastMaterialElement('blastMaterialLinkStatus');
    try{
      await postBlastMaterial('./api/blast-material-links',{materialId:blastMaterialElement('blastMaterialLinkBase').value,cardId:blastMaterialElement('blastMaterialLinkCard').value||null});
      renderBlastMaterialList();renderBlastMaterialLinks();
      status.textContent='材料关联已保存。';
    }catch(error){status.textContent=error.message;}
  });
}
