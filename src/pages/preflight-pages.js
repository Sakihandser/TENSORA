// Pre-run checks for the 2D pages and the material libraries. Each collector
// reads the current page inputs, asks CalcRules for findings and renders them in
// the page's "计算前检查" panel; run buttons go through Preflight.gate.
const preflightFinding=(level,code,zh)=>({level,code,zh,en:window.femI18n?.translateEnglish?.(zh)||zh});

// Restraints of the 2D drawing (geometry points and boundary curves).
function preflightRestraints2d(){
  const states=[];let curves=0,points=0;
  for(const node of scene.geometryNodes||[]){if(node.construction)continue;const c=mechanicalConstraints(node.mechanicalState);if(c.ux||c.uy){states.push(c);points++;}}
  for(const curve of scene.curves||[]){if(curve.construction)continue;const c=mechanicalConstraints(curve.mechanicalState);if(c.ux||c.uy){states.push(c);curves++;}}
  return {any:states.length>0,x:states.some(c=>c.ux),y:states.some(c=>c.uy),singlePoint:!curves&&points===1};
}
function preflightRegions2d(filter=()=>true){
  const regions=(scene.regions||[]).filter(r=>!isAirRegion(r)&&filter(r));
  const materials=new Map();let unassigned=0;
  for(const region of regions){
    const snapshot=materialSnapshotForRegion(region);
    if(!snapshot?.id){unassigned++;continue;}
    materials.set(snapshot.id,materialById(snapshot.id)||snapshot);
  }
  return {regions,materials:[...materials.values()],unassigned};
}
function preflightLoads2d(){return ['pointLoads','distributedLoads','bodyLoads'].reduce((n,key)=>n+(scene[key]||[]).length,0);}
function preflightMeshSizes2d(){
  let maxEdge=0,count=0;
  for(const element of scene.mesh?.elements||[]){count++;for(const l of element.edgeLengths||[])if(l>maxEdge)maxEdge=l;}
  const points=(scene.curves||[]).filter(c=>!c.construction).flatMap(c=>sampleCurve(c));
  const xs=points.map(p=>p.x),ys=points.map(p=>p.y);
  const w=points.length?Math.max(...xs)-Math.min(...xs):0,h=points.length?Math.max(...ys)-Math.min(...ys):0;
  return {maxEdge,count,width:w,height:h,diagonal:Math.hypot(w,h),shorter:Math.min(w,h)||Math.max(w,h)};
}

// ------------------------------------------------------------ static 2D
function collectStaticPreflight(){
  const {regions,materials,unassigned}=preflightRegions2d();
  const findings=CalcRules.checkStatic({dimension:2,structureRegions:regions.length,unassignedRegions:unassigned,
    restraints:preflightRestraints2d(),loads:preflightLoads2d(),materials,safety:true});
  if(!scene.mesh?.elements?.length)findings.push(preflightFinding('tip','static.mesh','尚未生成网格；开始计算时按“网格设置”的节点上限自动划分。'));
  if(document.getElementById('adaptiveMeshEnabled')?.checked&&Number(document.getElementById('adaptiveTolerance')?.value)<0.005)
    findings.push(preflightFinding('tip','static.adaptive','目标相对误差低于 0.5%，自适应加密可能达到节点上限或耗时保护后停止。'));
  return findings;
}

// ------------------------------------------------------------ deformation 2D
function collectDeformationPreflight(){
  const findings=[];
  let settings=null;
  try{settings=readDeformationControls();}catch(error){findings.push(preflightFinding('error','deformation.settings',error.message));}
  const {regions,materials,unassigned}=preflightRegions2d();
  findings.push(...CalcRules.checkStatic({dimension:2,structureRegions:regions.length,unassignedRegions:unassigned,restraints:preflightRestraints2d(),
    loads:preflightLoads2d(),materials,safety:false}));
  if(!settings)return findings;
  const sizes=preflightMeshSizes2d();
  const cards=[];
  for(const section of document.querySelectorAll('[data-deformation-material]')){
    const material=materialById(section.dataset.deformationMaterial)||materials.find(m=>m.id===section.dataset.deformationMaterial);
    try{cards.push({material,card:readDeformationCard(section)});}
    catch(error){findings.push({...preflightFinding('error','deformation.card',`${material?.name||''}：${error.message}`),target:{page:'deformation'}});}
  }
  const nonlinear=settings.finiteStrain||cards.some(({card})=>card.model!=='elastic');
  for(const {material,card} of cards){
    findings.push(...CalcRules.checkDeformationCard(material,card,{dimension:2,solver:settings.solver,planeMode:settings.planeMode,finiteStrain:settings.finiteStrain,
      meshSize:sizes.maxEdge,modelSize:sizes.diagonal}));
    if(settings.solver==='phast'&&card.model!=='phaseField')findings.push({...preflightFinding('error','deformation.phast.card',`${material?.name||''}：PhAST 路径要求所有材料选择“AT2 相场脆性断裂”。`),target:{page:'deformation',focus:'deformationSolver'}});
  }
  findings.push(...CalcRules.checkDeformationSettings(settings,{dimension:2,nonlinear}));
  if(settings.solver==='phast'&&scene.analysisNodes?.length>10000)findings.push({...preflightFinding('error','deformation.phast.nodes',`PhAST 路径最多支持 1 万节点（当前 ${scene.analysisNodes.length}），请减小网格节点上限。`),target:{page:'deformation',focus:'deformationMeshLimit'}});
  return findings;
}

// ------------------------------------------------------------ blast 2D
function collectBlastPreflight(){
  const findings=[];
  let settings;try{settings=blastCompatibilitySettings();}catch{settings={};}
  const laws={1:'elastic',3:'jh2',6:'mc'};
  for(const m of blastStrengthMaterials()){
    // Linked blast-library cards (shared with 3D) make every OpenCourant law available in 2D.
    const linked=typeof linkedBlastMaterialCard==='function'?linkedBlastMaterialCard(m.id):null;
    const card=blastRockDrafts.get(m.id)?.card||m.blastConstitutive;
    const law=linked?linked.card.model:laws[BlastMaterials.law({...m,blastConstitutive:card},settings)];
    findings.push(...CalcRules.checkBlastMaterial(materialById(m.id)||m,law));
  }
  if(!scene.mesh?.elements?.length)findings.push(preflightFinding('tip','blast.mesh','尚未生成网格；请在本页“网格准备”中生成。'));
  return findings;
}

// ------------------------------------------------------------ FSI 2D
function collectFsiPreflight(){
  const findings=[];
  const roles=new Map(fsiRegions().map(r=>[r,fsiRegionRole(r)]));
  const fluidRegions=[...roles].filter(([,role])=>role==='fluid').map(([r])=>r);
  const solid=preflightRegions2d(r=>fsiRegionRole(r)==='solid');
  if(!fluidRegions.length)findings.push({...preflightFinding('error','fsi.fluid.region','没有流体区域：请把至少一个区域设为“流体”。'),target:{page:'fsi',focus:'fsiRoles'}});
  if(!solid.regions.length)findings.push({...preflightFinding('error','fsi.solid.region','没有结构区域：请把至少一个区域设为“结构”。'),target:{page:'fsi',focus:'fsiRoles'}});
  if(solid.unassigned)findings.push({...preflightFinding('error','fsi.solid.material',`${solid.unassigned} 个结构区域尚未分配材料。`),target:{page:'home'}});
  let form={};try{form=fsiSolverSettings(readFsiForm());}catch{/* fields mid-edit */}
  for(const m of solid.materials)findings.push(...CalcRules.checkMaterial(m,{uses:['stiffness',...(form.analysis==='transient'?['density']:[])]}));
  const kinds={inlet:0,outlet:0,farfield:0},speeds=[];
  for(const {id} of fsiBoundaryCurves()){
    const b=fsiBoundarySetting(id);
    if(b.kind in kinds)kinds[b.kind]++;
    if(b.kind==='inlet'||b.kind==='farfield')speeds.push(Number(b.velocity??1));
  }
  const sizes=preflightMeshSizes2d();
  const fluidArea=fluidRegions.reduce((a,r)=>a+(Number(r.area)||0),0);
  const fluidElements=sizes.count?Math.max(1,Math.round(sizes.count*fluidArea/Math.max(fluidArea+solid.regions.reduce((a,r)=>a+(Number(r.area)||0),0),1e-30))):0;
  if(scene.mesh?.elements?.length&&fsiBoundaryCurves().some(({id})=>!fsiState().boundaries[id]))
    findings.push(preflightFinding('tip','fsi.walls.default','未指定类型的流体边界按无滑移壁面处理。'));
  findings.push(...CalcRules.checkFsi({dimension:2,engine:form.engine,analysis:form.analysis,turbulence:form.turbulence,fluid:fsiSelectedFluid(),
    speed:speeds.length?Math.max(...speeds):0,length:sizes.shorter,referencePressure:form.referencePressure,
    inlets:kinds.inlet,outlets:kinds.outlet,farfields:kinds.farfield,
    solidDensity:Math.min(...solid.materials.map(m=>Number(m.density)).filter(v=>v>0),Infinity),
    relaxation:form.relaxation,relaxationFactor:form.relaxationFactor,timeStep:form.timeStep,steps:form.steps,
    cellSize:fluidElements?Math.sqrt(fluidArea/fluidElements):0,hasRestraints:preflightRestraints2d().any}));
  if(!scene.mesh?.elements?.length)findings.push({...preflightFinding('error','fsi.mesh','尚未生成网格：请在右侧“网格准备”中生成。'),target:{page:'fsi',focus:'generateFsiMesh'}});
  return findings;
}

// ------------------------------------------------------------ libraries
function materialFormDraft(){
  const value=element=>element?.value===''||element?.value==null?null:Number(element.value);
  return {id:materialUi.id.value||null,name:materialUi.name.value.trim(),elasticModulus:value(materialUi.elasticModulus),poissonRatio:value(materialUi.poissonRatio),
    density:value(materialUi.density),yieldStrength:value(materialUi.yieldStrength),tensileStrength:value(materialUi.tensileStrength),
    compressiveStrength:value(materialUi.compressiveStrength),strengthCriterion:Number(materialUi.strengthCriterion?.value||4)};
}
function collectMaterialPreflight(){
  const draft=materialFormDraft();
  if(!draft.name&&draft.elasticModulus==null)return [];
  const strip=f=>{const {target,...rest}=f;return rest;};   // already on this form
  return [...CalcRules.checkMaterial(draft,{uses:['stiffness','density','safety'],criterion:draft.strengthCriterion}),...CalcRules.adviseMaterial(draft)].map(strip);
}
function collectFluidPreflight(){
  try{return CalcRules.checkFluid(readFsiLibraryDraft(true)).map(({target,...rest})=>rest);}
  catch(error){return [preflightFinding('error','fluid.form',error.message)];}
}

// ------------------------------------------------------------ wiring
const PREFLIGHT_PAGES={
  calculation:['staticPreflight',collectStaticPreflight],deformation:['deformationPreflight',collectDeformationPreflight],
  blast:['blastPreflight',collectBlastPreflight],fsi:['fsiPreflight',collectFsiPreflight],
  materials:['materialPreflight',collectMaterialPreflight],'fsi-library':['fluidPreflight',collectFluidPreflight]
};
function refreshPreflight(page=currentPageKey()){
  const entry=PREFLIGHT_PAGES[page];
  if(!entry||document.getElementById('enableSolid3dModule')?.checked&&['calculation','deformation','blast','fsi'].includes(page))return;
  let findings;
  try{findings=entry[1]();}catch(error){findings=[preflightFinding('warning','preflight.internal',`检查未完成：${error.message}`)];}
  Preflight.render(document.getElementById(entry[0]),findings);
}
// Runs `run` only when the page checks allow it.
async function runWithPreflight(page,run){
  const entry=PREFLIGHT_PAGES[page];
  if(entry){
    let findings=[];try{findings=entry[1]();}catch{/* fall through to the solver's own validation */}
    Preflight.render(document.getElementById(entry[0]),findings);
    if(!(await Preflight.gate(findings,page)))return;
  }
  return run();
}
function initializePreflightPages(){
  for(const [page,[id]] of Object.entries(PREFLIGHT_PAGES)){
    const host=document.getElementById(id);if(!host)continue;
    const root=host.closest('main')||host.parentElement;
    Preflight.watch(root,()=>{if(currentPageKey()===page)refreshPreflight(page);});
  }
  window.addEventListener('tensora-fsi-fluids-changed',()=>{if(currentPageKey()==='fsi')refreshPreflight('fsi');});
}
// Opens a base material in the material library form (used by "Locate").
window.openMaterialForEditing=function(id){
  const material=materialById(id);
  if(!material)return;
  setPage('materials');
  renderMaterialLibrary(id);writeMaterialForm(material);
  refreshPreflight('materials');
  materialUi.form?.scrollIntoView({block:'start',behavior:'smooth'});
};
