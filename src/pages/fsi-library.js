// Fluid material library page. Records live in fluids/library.json and are
// shared by the 2D and 3D fluid–structure interaction workspaces.
let fsiLibraryId=null,fsiLibraryBusy=false;
const FSI_LIBRARY_FIELDS=[
  ['density','密度 ρ (kg/m³)','all'],['viscosity','动力黏度 μ (Pa·s)','all'],
  ['gamma','比热比 γ','idealgas'],['gasConstant','气体常数 R (J/(kg·K))','idealgas'],['temperature','参考温度 T (K)','idealgas'],
  ['bulkModulus','体积模量 K (Pa，可留空)','optional'],['soundSpeed','声速 c (m/s，可留空)','optional']
];
const $fl=id=>document.getElementById(id);
function fsiLibraryMessage(text){$fl('fsiLibraryStatus').textContent=text;}
function renderFsiLibraryList(){
  const list=$fl('fsiLibraryList');if(!list)return;
  list.replaceChildren();
  $fl('fsiLibraryCount').textContent=String(fsiFluids.length);
  const filter=$fl('fsiLibraryCategory').value;
  for(const fluid of fsiFluids){
    if(filter!=='all'&&fluid.category!==filter)continue;
    const button=document.createElement('button');button.type='button';button.className='blast-library-item fsi-library-item';
    button.classList.toggle('active',fluid.id===fsiLibraryId);button.disabled=fsiLibraryBusy;
    const swatch=document.createElement('i');swatch.className='fsi-swatch';swatch.style.background=fluid.color;
    const name=document.createElement('strong');name.textContent=fluid.name;
    const detail=document.createElement('small');detail.textContent=`${fluid.model==='idealgas'?'理想气体':'不可压缩'} · ρ ${fluid.density} kg/m³ · μ ${Number(fluid.viscosity).toExponential(2)} Pa·s`;
    button.append(swatch,name,detail);
    button.addEventListener('click',()=>openFsiLibraryRecord(fluid));
    list.append(button);
  }
}
function syncFsiLibraryModel(){
  const gas=$fl('fsiLibraryModel').value==='idealgas';
  for(const [key,,scope] of FSI_LIBRARY_FIELDS)$fl(`fsiLibrary-${key}`).closest('label').hidden=scope==='idealgas'&&!gas;
  $fl('fsiLibraryModelHelp').textContent=gas
    ?'理想气体：SU2 按可压缩 Navier–Stokes（无黏时为 Euler）方程求解，状态方程 p = ρRT；参考压力在流固耦合设置中给定，密度由参考压力和温度确定。'
    :'不可压缩：SU2 按常密度不可压缩 Navier–Stokes 方程求解，压力为相对出口（参考）压力的表压。体积模量与声速仅作记录。';
}
function openFsiLibraryRecord(record){
  fsiLibraryId=record?.id||null;
  const r=record||{name:'',category:'liquid',model:'incompressible',density:1000,viscosity:0.001,color:'#7fb8d8',notes:'',source:'用户输入'};
  $fl('fsiLibraryTitle').textContent=record?record.name:'新建流体';
  $fl('fsiLibraryName').value=r.name;
  $fl('fsiLibraryCategoryField').value=r.category;
  $fl('fsiLibraryModel').value=r.model;
  for(const [key] of FSI_LIBRARY_FIELDS)$fl(`fsiLibrary-${key}`).value=r[key]??(key==='gamma'?1.4:key==='gasConstant'?287.058:key==='temperature'?293.15:'');
  $fl('fsiLibraryColor').value=r.color||'#7fb8d8';
  $fl('fsiLibrarySource').value=r.source||'';
  $fl('fsiLibraryNotes').value=r.notes||'';
  $fl('fsiLibraryDelete').disabled=!record;
  fsiLibraryMessage('');syncFsiLibraryModel();renderFsiLibraryList();
  if(typeof refreshPreflight==='function')refreshPreflight('fsi-library');
}
function readFsiLibraryDraft(copy){
  const raw={id:!copy&&fsiLibraryId?fsiLibraryId:`fluid-${crypto.randomUUID()}`,name:$fl('fsiLibraryName').value,
    category:$fl('fsiLibraryCategoryField').value,model:$fl('fsiLibraryModel').value,color:$fl('fsiLibraryColor').value,
    source:$fl('fsiLibrarySource').value,notes:$fl('fsiLibraryNotes').value};
  for(const [key,,scope] of FSI_LIBRARY_FIELDS){
    const input=$fl(`fsiLibrary-${key}`),value=input.value.trim();
    if(scope==='idealgas'&&raw.model!=='idealgas')continue;
    raw[key]=value===''?null:Number(value);
  }
  try{return FluidLibrary.entry(raw);}
  catch(error){
    const field=String(error.message).match(/parameter: (\w+)/)?.[1];
    const label=FSI_LIBRARY_FIELDS.find(([key])=>key===field)?.[1];
    throw Error(label?`“${label}”输入无效。`:'请填写流体名称和有效参数。');
  }
}
async function persistFsiLibrary(fluids){
  const response=await fetch('/api/fluids',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({version:1,revision:fsiFluidRevision,fluids})});
  const body=await response.json().catch(()=>({}));
  if(!response.ok)throw Error(response.status===409?'流体材料库已在其他窗口修改，请重新读取后再保存。':(body.error||'保存流体材料库失败。'));
  fsiFluids=body.fluids;fsiFluidRevision=body.revision;
  renderFsiFluidSelect();window.dispatchEvent(new Event('tensora-fsi-fluids-changed'));
}
async function withFsiLibraryBusy(action){
  fsiLibraryBusy=true;
  const controls=[...$fl('fsiLibraryPage').querySelectorAll('input,select,textarea,button')];
  const previous=controls.map(control=>control.disabled);controls.forEach(control=>{control.disabled=true;});
  try{return await action();}finally{fsiLibraryBusy=false;controls.forEach((control,i)=>{control.disabled=previous[i];});renderFsiLibraryList();}
}
async function saveFsiLibraryDraft(copy){
  if(fsiLibraryBusy)return;
  try{
    const record=readFsiLibraryDraft(copy);
    await withFsiLibraryBusy(()=>persistFsiLibrary([...fsiFluids.filter(f=>f.id!==record.id),record]));
    openFsiLibraryRecord(fsiFluids.find(f=>f.id===record.id));fsiLibraryMessage('流体已保存到流体材料库。');
  }catch(error){fsiLibraryMessage(error.message);}
}
async function deleteFsiLibraryDraft(){
  if(!fsiLibraryId||fsiLibraryBusy)return;
  if(!window.confirm('删除所选流体？已保存的计算结果不受影响。'))return;
  try{
    const id=fsiLibraryId;
    await withFsiLibraryBusy(()=>persistFsiLibrary(fsiFluids.filter(f=>f.id!==id)));
    if(fsiState().fluidId===id)fsiState().fluidId=null;
    openFsiLibraryRecord(fsiFluids[0]||null);fsiLibraryMessage('已删除所选流体。');
  }catch(error){fsiLibraryMessage(error.message);}
}
function renderFsiLibrary(){
  if(!fsiLibraryId||!fsiFluids.some(f=>f.id===fsiLibraryId))openFsiLibraryRecord(fsiFluids.find(f=>f.id===fsiState().fluidId)||fsiFluids[0]||null);
  else renderFsiLibraryList();
}
function initializeFsiLibrary(){
  $fl('fsiLibraryNew').addEventListener('click',()=>openFsiLibraryRecord(null));
  $fl('fsiLibraryReload').addEventListener('click',async()=>{await loadFsiFluids();renderFsiLibrary();fsiLibraryMessage('流体材料库已重新读取。');});
  $fl('fsiLibraryCategory').addEventListener('change',renderFsiLibraryList);
  $fl('fsiLibraryModel').addEventListener('change',()=>{
    syncFsiLibraryModel();
    $fl('fsiLibraryCategoryField').value=$fl('fsiLibraryModel').value==='idealgas'?'gas':$fl('fsiLibraryCategoryField').value;
  });
  $fl('fsiLibraryForm').addEventListener('submit',event=>{event.preventDefault();saveFsiLibraryDraft(false);});
  $fl('fsiLibraryCopy').addEventListener('click',()=>saveFsiLibraryDraft(true));
  $fl('fsiLibraryDelete').addEventListener('click',deleteFsiLibraryDraft);
  $fl('fsiLibraryApply').addEventListener('click',()=>{
    if(!fsiLibraryId){fsiLibraryMessage('请先保存流体，再应用到流固耦合设置。');return;}
    fsiState().fluidId=fsiLibraryId;
    window.dispatchEvent(new CustomEvent('tensora-fsi-fluid-selected',{detail:{id:fsiLibraryId}}));
    renderFsiFluidSelect();setPage('fsi');
  });
}
