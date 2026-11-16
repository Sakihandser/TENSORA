// Pre-run checks shared by every calculation workspace. The rules inspect user
// input (materials, constitutive choices, solver settings and model setup) and
// return findings; they never change the input or compute a solution.
//
// Finding: {level:'error'|'warning'|'tip', code, zh, en, target?}
//   error   - the run cannot start (missing or impossible input);
//   warning - the run can start after confirmation (likely wrong or misleading);
//   tip     - guidance on model choice or parameters.
// target: {page?, focus?, material?} tells the panel where the input lives.
(function(root,factory){
  if(typeof module==='object'&&module.exports)module.exports=factory();
  else root.CalcRules=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const item=(level,code,zh,en,target)=>({level,code,zh,en,...(target?{target}:{})});
  const num=v=>v===null||v===undefined||v===''?NaN:Number(v);
  const has=v=>Number.isFinite(num(v));
  const fmt=v=>{const n=Number(v);if(!Number.isFinite(n))return '—';const a=Math.abs(n);return a!==0&&(a<1e-3||a>=1e5)?n.toExponential(2):String(Number(n.toPrecision(4)));};
  const name=m=>String(m?.name||m?.id||'材料');

  // ---------------------------------------------------------------- materials
  const CLASS_LABELS={metal:['金属','metal'],concrete:['混凝土 / 砂浆','concrete / mortar'],rock:['岩石','rock'],
    brittle:['玻璃 / 陶瓷','glass / ceramic'],rubber:['橡胶 / 弹性体','rubber / elastomer'],polymer:['聚合物 / 塑料','polymer / plastic'],unknown:['未识别','unidentified']};
  // Typical ranges: E in GPa, density in kg/m³ (engineering handbooks).
  const RANGES={metal:{E:[40,420],rho:[1700,19500]},concrete:{E:[8,60],rho:[1500,2700]},rock:{E:[0.5,130],rho:[1300,3400]},
    brittle:{E:[40,450],rho:[2000,6500]},rubber:{E:[0.0003,0.1],rho:[850,1700]},polymer:{E:[0.05,15],rho:[700,2300]}};
  const KEYWORDS=[
    ['concrete',/混凝土|砂浆|水泥|concrete|mortar|cement/i],
    ['rubber',/橡胶|硅胶|弹性体|rubber|elastomer|silicone/i],
    ['polymer',/塑料|树脂|尼龙|聚[乙丙苯氯酰碳]|PVC|HDPE|LDPE|\bPE\b|\bPP\b|ABS|PMMA|epoxy|nylon|polymer|plastic|polyeth|polyprop/i],
    ['brittle',/玻璃|陶瓷|glass|ceramic|alumina|氧化铝/i],
    ['metal',/钢|铁|铝|铜|钛|镁|锌|镍|锡|铅|合金|金属|steel|iron|alumin|copper|brass|bronze|titan|magnes|nickel|alloy|metal|\d{4}-T\d/i],
    ['rock',/岩|石|granite|sandstone|marble|limestone|basalt|rock|gypsum|shale|coal|煤/i]
  ];
  function classify(m){
    const label=`${m?.name||''}`;
    for(const [kind,pattern] of KEYWORDS)if(pattern.test(label))return {kind,by:'name'};
    const E=num(m?.elasticModulus),fy=num(m?.yieldStrength),ft=num(m?.tensileStrength),fc=num(m?.compressiveStrength);
    if(has(E)){
      if(E<0.1)return {kind:'rubber',by:'properties'};
      if(E<15&&num(m?.density)<2300)return {kind:'polymer',by:'properties'};
      if(fy>0&&E>=40)return {kind:'metal',by:'properties'};
      if(fc>0&&ft>0&&ft<fc/4)return {kind:E<=60?'concrete':'rock',by:'properties'};
    }
    return {kind:'unknown',by:'none'};
  }
  const classLabel=kind=>CLASS_LABELS[kind]||CLASS_LABELS.unknown;

  // uses: Set of 'stiffness' | 'density' | 'safety' | 'strength'
  function checkMaterial(m,{uses=['stiffness'],criterion}={}){
    const out=[],n=name(m),target={material:m?.id};
    const need=new Set(uses);
    const E=num(m?.elasticModulus),nu=num(m?.poissonRatio),rho=num(m?.density);
    const fy=num(m?.yieldStrength),ft=num(m?.tensileStrength),fc=num(m?.compressiveStrength);
    const {kind}=classify(m),range=RANGES[kind],[zhKind,enKind]=classLabel(kind);
    if(need.has('stiffness')){
      if(!has(E)||E<=0)out.push(item('error','material.E.missing',`${n}：缺少弹性模量 E。`,`${n}: Young's modulus E is missing.`,target));
      else{
        if(E>1500)out.push(item('error','material.E.units',`${n}：弹性模量 ${fmt(E)} GPa 超过所有已知材料（金刚石约 1200 GPa）。材料库的 E 以 GPa 为单位，是否按 MPa 填写了？`,
          `${n}: E = ${fmt(E)} GPa exceeds every known material (diamond ≈ 1200 GPa). The library stores E in GPa; was it entered in MPa?`,target));
        else if(range&&(E<range.E[0]/5||E>range.E[1]*5))out.push(item('warning','material.E.range',`${n}：E = ${fmt(E)} GPa 与${zhKind}的常见范围 ${range.E[0]}–${range.E[1]} GPa 相差较大，请核对单位（GPa）和数值。`,
          `${n}: E = ${fmt(E)} GPa is far from the usual ${enKind} range ${range.E[0]}–${range.E[1]} GPa. Check the value and unit (GPa).`,target));
        else if(E<1e-5)out.push(item('warning','material.E.tiny',`${n}：E = ${fmt(E)} GPa 极小，请核对单位（GPa）。`,`${n}: E = ${fmt(E)} GPa is extremely small; check the unit (GPa).`,target));
      }
      if(!has(nu))out.push(item('error','material.nu.missing',`${n}：缺少泊松比 ν。`,`${n}: Poisson's ratio ν is missing.`,target));
      else if(nu>=0.5||nu<=-1)out.push(item('error','material.nu.invalid',`${n}：泊松比 ν = ${fmt(nu)} 不在 (−1, 0.5) 内。`,`${n}: Poisson's ratio ν = ${fmt(nu)} is outside (−1, 0.5).`,target));
      else if(nu>0.49)out.push(item('warning','material.nu.incompressible',`${n}：ν = ${fmt(nu)} 接近不可压缩，线性三角形 / 四面体单元会出现体积锁死，位移偏小、应力振荡。橡胶类材料建议在损伤变形中使用超弹性本构。`,
        `${n}: ν = ${fmt(nu)} is nearly incompressible; linear triangles and tetrahedra lock, giving too-small displacements and oscillating stress. Use a hyperelastic model in Deformation for rubber-like materials.`,target));
      else if(nu<0)out.push(item('warning','material.nu.negative',`${n}：负泊松比（ν = ${fmt(nu)}）只出现在特殊拉胀材料中，请确认。`,`${n}: a negative Poisson's ratio (ν = ${fmt(nu)}) only occurs in special auxetic materials; please confirm.`,target));
    }
    if(need.has('density')){
      if(!has(rho)||rho<=0)out.push(item('error','material.rho.missing',`${n}：缺少密度（动力计算需要质量）。`,`${n}: density is missing (dynamic analysis needs mass).`,target));
      else if(rho<50)out.push(item('warning','material.rho.units',`${n}：密度 ${fmt(rho)} kg/m³ 过小，是否按 g/cm³ 或 t/m³ 填写了？例如钢应为 7850 kg/m³。`,
        `${n}: density ${fmt(rho)} kg/m³ is too small; was it entered in g/cm³ or t/m³? Steel, for example, is 7850 kg/m³.`,target));
      else if(range&&(rho<range.rho[0]*0.5||rho>range.rho[1]*1.5))out.push(item('warning','material.rho.range',`${n}：密度 ${fmt(rho)} kg/m³ 与${zhKind}的常见范围 ${range.rho[0]}–${range.rho[1]} kg/m³ 相差较大。`,
        `${n}: density ${fmt(rho)} kg/m³ is far from the usual ${enKind} range ${range.rho[0]}–${range.rho[1]} kg/m³.`,target));
    }
    if(need.has('safety')||need.has('strength')){
      if(fy>0&&ft>0&&fy>ft*1.02)out.push(item('warning','material.fy.above.ft',`${n}：屈服强度 ${fmt(fy)} MPa 高于抗拉强度 ${fmt(ft)} MPa，两者可能填反。`,
        `${n}: yield strength ${fmt(fy)} MPa exceeds tensile strength ${fmt(ft)} MPa; the two may be swapped.`,target));
      if(fy>0&&E>0&&fy/(E*1000)>0.05)out.push(item('warning','material.fy.units',`${n}：屈服应变 σy/E = ${fmt(fy/(E*1000))} 过大，请核对屈服强度（MPa）和 E（GPa）的单位。`,
        `${n}: yield strain σy/E = ${fmt(fy/(E*1000))} is implausibly large; check the units of yield strength (MPa) and E (GPa).`,target));
      if(ft>0&&fc>0&&['rock','concrete','brittle'].includes(kind)&&ft>fc)out.push(item('warning','material.ft.above.fc',`${n}：抗拉强度 ${fmt(ft)} MPa 高于抗压强度 ${fmt(fc)} MPa，${zhKind}通常相反，两者可能填反。`,
        `${n}: tensile strength ${fmt(ft)} MPa exceeds compressive strength ${fmt(fc)} MPa; for ${enKind} it is usually the reverse, so the values may be swapped.`,target));
    }
    if(need.has('safety')){
      const c=num(criterion??m?.strengthCriterion);
      if((c===1||c===2)&&!(ft>0&&fc>0))out.push(item('warning','material.safety.ftfc',`${n}：第${c===1?'一':'二'}强度理论需要抗拉和抗压强度，缺少时该材料的安全校核显示为“未完成校核”。`,
        `${n}: the ${c===1?'first':'second'} strength theory needs tensile and compressive strength; without them the safety check of this material is incomplete.`,target));
      if((c===3||c===4)&&!(fy>0))out.push(item('warning','material.safety.fy',`${n}：第${c===3?'三':'四'}强度理论需要屈服强度，缺少时该材料的安全校核显示为“未完成校核”。`,
        `${n}: the ${c===3?'third':'fourth'} strength theory needs a yield strength; without it the safety check of this material is incomplete.`,target));
      if((c===3||c===4)&&['rock','concrete','brittle'].includes(kind))out.push(item('tip','material.safety.brittle',`${n}：${zhKind}属于脆性材料，第三 / 第四强度理论针对塑性屈服，建议改用第一强度理论（最大拉应力）。`,
        `${n}: ${enKind} is brittle; the third / fourth theories describe plastic yielding, so the first (maximum tensile stress) theory is more suitable.`,target));
      if((c===1||c===2)&&kind==='metal')out.push(item('tip','material.safety.metal',`${n}：金属一般按第四强度理论（von Mises）校核屈服。`,`${n}: metals are usually checked against yielding with the fourth (von Mises) theory.`,target));
    }
    return out;
  }

  // ---------------------------------------------------------------- deformation
  const DEFORMATION_MODELS={plastic:['J2 塑性','J2 plasticity'],elastic:['弹性','elastic'],neoHooke:['Neo-Hooke','Neo-Hooke'],mooneyRivlin:['Mooney–Rivlin','Mooney–Rivlin'],
    phaseField:['AT2 相场断裂','AT2 phase-field fracture'],crackBand:['裂带断裂','crack-band fracture'],mazars:['Mazars 混凝土损伤','Mazars concrete damage']};
  function recommendDeformation(kind,dimension){
    if(kind==='metal')return ['plastic'];
    if(kind==='rubber')return ['neoHooke','mooneyRivlin'];
    if(kind==='concrete')return dimension===3?['mazars','crackBand']:['phaseField'];
    if(kind==='rock'||kind==='brittle')return dimension===3?['crackBand']:['phaseField'];
    if(kind==='polymer')return ['plastic','elastic'];
    return [];
  }
  // card: deformation material card (SI units); ctx: {dimension, solver, planeMode, finiteStrain, meshSize, modelSize}
  function checkDeformationCard(m,card,ctx={}){
    const out=[],n=name(m),target={material:m?.id,page:'deformation'};
    const {kind}=classify(m),[zhKind,enKind]=classLabel(kind);
    const model=card?.model||'plastic',[zhModel,enModel]=DEFORMATION_MODELS[model]||[model,model];
    const E=num(m?.elasticModulus)*1e9,nu=num(m?.poissonRatio);
    const rec=recommendDeformation(kind,ctx.dimension);
    // Models not offered in this dimension are reported as errors below instead.
    const unavailable=(ctx.dimension===2&&['mazars','crackBand'].includes(model))||(ctx.dimension===3&&model==='phaseField');
    if(kind!=='unknown'&&rec.length&&!rec.includes(model)&&!unavailable){
      const zhRec=rec.map(k=>DEFORMATION_MODELS[k][0]).join(' / '),enRec=rec.map(k=>DEFORMATION_MODELS[k][1]).join(' / ');
      const why={plastic:['J2 屈服与静水压力无关，不能描述岩石、混凝土的拉压不对称和软化开裂。','J2 yielding ignores hydrostatic pressure and cannot capture the tension–compression asymmetry and softening of rock or concrete.'],
        phaseField:['相场 / 裂带模型描述脆性开裂，金属的延性屈服应使用塑性模型。','phase-field and crack-band models describe brittle cracking; ductile metals need a plasticity model.'],
        crackBand:['相场 / 裂带模型描述脆性开裂，金属的延性屈服应使用塑性模型。','phase-field and crack-band models describe brittle cracking; ductile metals need a plasticity model.'],
        mazars:['Mazars 模型是为混凝土标定的损伤模型。','the Mazars model is calibrated for concrete.'],
        elastic:['弹性模型不包含屈服、损伤或开裂。','the elastic model has no yielding, damage or cracking.'],
        neoHooke:['超弹性模型适用于橡胶类大变形材料。','hyperelastic models are meant for rubber-like large-strain materials.'],
        mooneyRivlin:['超弹性模型适用于橡胶类大变形材料。','hyperelastic models are meant for rubber-like large-strain materials.']}[model]||['',''];
      out.push(item('warning','deformation.model.mismatch',`${n}（识别为${zhKind}）选用了“${zhModel}”。${why[0]}建议：${zhRec}。`,
        `${n} (identified as ${enKind}) uses “${enModel}”. ${why[1]} Recommended: ${enRec}.`,target));
    }
    if(['neoHooke','mooneyRivlin'].includes(model)){
      if(ctx.finiteStrain===false)out.push(item('error','deformation.hyper.finite',`${n}：超弹性本构需要启用“有限变形 / 几何非线性”。`,`${n}: hyperelastic models require finite deformation (geometric nonlinearity).`,{page:'deformation',focus:'deformationFinite'}));
      const c10=num(card.c10),c01=model==='mooneyRivlin'?num(card.c01)||0:0,d1=num(card.d1);
      if(c10>0&&d1>0&&E>0){
        const mu=2*(c10+c01),K=2/d1,Eeq=9*K*mu/(3*K+mu),nuEq=(3*K-2*mu)/(2*(3*K+mu));
        if(Eeq/E<0.5||Eeq/E>2)out.push(item('warning','deformation.hyper.E',`${n}：超弹性参数对应的小应变模量 E ≈ ${fmt(Eeq/1e6)} MPa，与基础材料 E = ${fmt(E/1e6)} MPa 相差超过一倍。超弹性计算使用 C10、C01、D1，请核对单位（C 为 MPa，D1 为 MPa⁻¹）。`,
          `${n}: the hyperelastic parameters give a small-strain modulus E ≈ ${fmt(Eeq/1e6)} MPa, more than a factor of two from the base E = ${fmt(E/1e6)} MPa. The analysis uses C10, C01 and D1; check their units (C in MPa, D1 in MPa⁻¹).`,target));
        if(nuEq<0.45)out.push(item('tip','deformation.hyper.compressible',`${n}：D1 对应的等效泊松比约 ${fmt(nuEq)}，比一般橡胶（0.49 以上）可压缩性明显。`,`${n}: D1 implies an equivalent Poisson's ratio of about ${fmt(nuEq)}, noticeably more compressible than typical rubber (above 0.49).`,target));
      }
    }
    if(model==='plastic'){
      const sy=num(card.yieldStress),H=num(card.hardening),ec=num(card.criticalPlasticStrain);
      if(sy>0&&E>0){
        const ey=sy/E;
        if(ey>0.05)out.push(item('warning','deformation.plastic.units',`${n}：屈服应变 σy/E = ${fmt(ey)} 过大，请核对屈服应力（MPa）和基础材料 E（GPa）。`,`${n}: yield strain σy/E = ${fmt(ey)} is too large; check the yield stress (MPa) and the base E (GPa).`,target));
        if(ey<2e-5)out.push(item('warning','deformation.plastic.low',`${n}：屈服应变 σy/E = ${fmt(ey)} 极小，材料几乎一加载就屈服，请核对单位。`,`${n}: yield strain σy/E = ${fmt(ey)} is tiny, so the material yields almost immediately; check the units.`,target));
        const fy=num(m?.yieldStrength)*1e6;
        if(fy>0&&Math.abs(sy-fy)/fy>0.5)out.push(item('tip','deformation.plastic.base',`${n}：材料卡屈服应力 ${fmt(sy/1e6)} MPa 与基础材料屈服强度 ${fmt(fy/1e6)} MPa 相差较大。`,`${n}: the card's yield stress ${fmt(sy/1e6)} MPa differs markedly from the base yield strength ${fmt(fy/1e6)} MPa.`,target));
      }
      if(H>0&&E>0&&H>=E)out.push(item('warning','deformation.plastic.hardening',`${n}：硬化模量 H = ${fmt(H/1e6)} MPa 不小于弹性模量，这是 dσ/dεp 而不是总应变切线模量，请核对。`,
        `${n}: hardening modulus H = ${fmt(H/1e6)} MPa is not below E; it is dσ/dεp, not the total-strain tangent modulus.`,target));
      if(ec>1.5)out.push(item('tip','deformation.plastic.peeq',`${n}：损伤起始阈值 ${fmt(ec)} 超过 1.5，金属一般在 0.05–0.5 之间。`,`${n}: the damage-initiation threshold ${fmt(ec)} is above 1.5; metals typically range 0.05–0.5.`,target));
    }
    if(model==='phaseField'){
      if(ctx.solver&&ctx.solver!=='phast')out.push(item('error','deformation.phase.solver',`${n}：AT2 相场断裂需要在“求解路径”中选择 PhAST。`,`${n}: AT2 phase-field fracture needs the PhAST solution path.`,{page:'deformation',focus:'deformationSolver'}));
      const Gc=num(card.fractureEnergy),l0=num(card.fractureLength),ft=num(m?.tensileStrength)*1e6;
      if(Gc>0&&l0>0&&E>0){
        const sc=Math.sqrt(27*E*Gc/(256*l0));
        if(ft>0&&(sc/ft<0.5||sc/ft>2)){
          const l=27*E*Gc/(256*ft*ft);
          out.push(item('tip','deformation.phase.strength',`${n}：按 AT2 换算的临界应力 σc = √(27EGc/256l₀) ≈ ${fmt(sc/1e6)} MPa，与材料抗拉强度 ${fmt(ft/1e6)} MPa 不一致；若希望两者一致，可取 l₀ ≈ ${fmt(l)} m。`,
            `${n}: the AT2 critical stress σc = √(27EGc/256l₀) ≈ ${fmt(sc/1e6)} MPa differs from the tensile strength ${fmt(ft/1e6)} MPa; to match them use l₀ ≈ ${fmt(l)} m.`,target));
        }
        if(ctx.meshSize>0&&ctx.meshSize>l0/2)out.push(item('warning','deformation.phase.mesh',`${n}：网格最大边长 ${fmt(ctx.meshSize)} m 大于 l₀/2 = ${fmt(l0/2)} m，损伤带无法分辨，裂纹路径和峰值载荷依赖网格。请加密网格。`,
          `${n}: the largest element edge ${fmt(ctx.meshSize)} m exceeds l₀/2 = ${fmt(l0/2)} m; the damage band is not resolved, so crack path and peak load depend on the mesh. Refine the mesh.`,target));
        if(ctx.modelSize>0&&l0>ctx.modelSize/5)out.push(item('warning','deformation.phase.length',`${n}：相场长度 l₀ = ${fmt(l0)} m 超过模型尺寸的 1/5，损伤会弥散到大范围。`,`${n}: phase-field length l₀ = ${fmt(l0)} m exceeds a fifth of the model size, so damage spreads over a wide zone.`,target));
      }
      if(Gc>0&&(Gc<1||Gc>1e5))out.push(item('warning','deformation.phase.Gc',`${n}：断裂能 Gc = ${fmt(Gc)} J/m² 不在常见范围（玻璃约 10，混凝土约 100，岩石 10–500），请核对单位（J/m²）。`,
        `${n}: fracture energy Gc = ${fmt(Gc)} J/m² is outside the usual range (glass ≈ 10, concrete ≈ 100, rock 10–500); check the unit (J/m²).`,target));
    }
    if(model==='crackBand'){
      const ft=num(card.tensileStrength),Gf=num(card.crackBandEnergy),fBase=num(m?.tensileStrength)*1e6;
      if(ft>0&&fBase>0&&Math.abs(ft-fBase)/fBase>0.5)out.push(item('tip','deformation.crack.ft',`${n}：裂带抗拉强度 ${fmt(ft/1e6)} MPa 与基础材料 ${fmt(fBase/1e6)} MPa 相差较大。`,`${n}: crack-band tensile strength ${fmt(ft/1e6)} MPa differs markedly from the base value ${fmt(fBase/1e6)} MPa.`,target));
      if(ft>0&&Gf>0&&E>0&&ctx.meshSize>0){
        const hmax=2*E*Gf/(ft*ft);
        if(ctx.meshSize>hmax)out.push(item('warning','deformation.crack.mesh',`${n}：单元尺寸 ${fmt(ctx.meshSize)} m 超过裂带模型允许的 2EGf/ft² ≈ ${fmt(hmax)} m，软化段会出现突跳（snap-back）。请加密网格。`,
          `${n}: element size ${fmt(ctx.meshSize)} m exceeds the crack-band limit 2EGf/ft² ≈ ${fmt(hmax)} m, so softening snaps back. Refine the mesh.`,target));
      }
    }
    if(model==='mazars'){
      const e0=num(card.epsd0),ft=num(m?.tensileStrength)*1e6;
      if(e0>0&&ft>0&&E>0&&(e0/(ft/E)<0.5||e0/(ft/E)>2))out.push(item('tip','deformation.mazars.epsd0',`${n}：EPSD0 = ${fmt(e0)} 与 ft/E ≈ ${fmt(ft/E)} 不一致，通常两者接近。`,`${n}: EPSD0 = ${fmt(e0)} differs from ft/E ≈ ${fmt(ft/E)}; they are usually close.`,target));
      if(ctx.dimension===2)out.push(item('error','deformation.mazars.dim',`${n}：Mazars 损伤只能用于三维损伤变形（Code_Aster）。`,`${n}: Mazars damage is available only in 3D deformation (Code_Aster).`,target));
    }
    if(model==='crackBand'&&ctx.dimension===2)out.push(item('error','deformation.crack.dim',`${n}：裂带断裂只能用于三维损伤变形（OOFEM）。`,`${n}: crack-band fracture is available only in 3D deformation (OOFEM).`,target));
    if(E>0&&has(nu)&&nu>0.49&&['plastic','elastic'].includes(model))out.push(item('tip','deformation.locking',`${n}：ν 接近 0.5 时一阶单元会体积锁死，橡胶类材料请用超弹性本构。`,`${n}: with ν near 0.5 first-order elements lock; use a hyperelastic model for rubber-like materials.`,target));
    return out;
  }
  function checkDeformationSettings(s,ctx={}){
    const out=[],target={page:'deformation'};
    if(s.solver==='phast'){
      if(ctx.dimension===3)out.push(item('error','deformation.phast.3d','PhAST 相场断裂只用于二维平面应变，三维请使用 Code_Aster（Mazars）或 OOFEM（裂带）。','PhAST phase-field fracture is 2D plane strain only; in 3D use Code_Aster (Mazars) or OOFEM (crack band).',target));
      if(s.planeMode!==1)out.push(item('error','deformation.phast.plane','PhAST 相场断裂需要“平面应变”假设。','PhAST phase-field fracture needs the plane-strain assumption.',{page:'deformation',focus:'deformationPlane'}));
      if(s.finiteStrain)out.push(item('error','deformation.phast.finite','PhAST 相场断裂为小变形，请关闭“有限变形”。','PhAST phase-field fracture is small-strain; turn finite deformation off.',{page:'deformation',focus:'deformationFinite'}));
    }
    if(s.solver==='calculix'&&s.maxIncrements<s.increments)out.push(item('error','deformation.increments','最大增量数不能小于初始增量数。','The maximum number of increments cannot be below the initial number.',{page:'deformation',focus:'deformationMaxIncrements'}));
    if(s.solver==='calculix'&&s.increments<5&&ctx.nonlinear)out.push(item('tip','deformation.increments.few',`初始增量数 ${s.increments} 较少，非线性问题容易在第一步不收敛，建议 20–40。`,`Only ${s.increments} initial increments; nonlinear problems often fail to converge in the first step. Use 20–40.`,{page:'deformation',focus:'deformationIncrements'}));
    if(s.loadFactor>5)out.push(item('tip','deformation.loadfactor',`最终载荷系数 ${fmt(s.loadFactor)} 较大，结构可能在达到目标前失稳或不收敛。`,`The final load factor ${fmt(s.loadFactor)} is large; the structure may become unstable or stop converging before reaching it.`,{page:'deformation',focus:'deformationLoadFactor'}));
    return out;
  }

  // ---------------------------------------------------------------- blast
  // law: 'elastic' | 'jh2' | 'hjc' | 'dp' | 'jc' | 'mc'
  const BLAST_LAWS={elastic:['线弹性','linear elastic'],jh2:['JH2 岩石','JH2 rock'],hjc:['HJC 混凝土','HJC concrete'],dp:['Drucker–Prager','Drucker–Prager'],jc:['Johnson–Cook 金属','Johnson–Cook metal'],mc:['Mohr–Coulomb','Mohr–Coulomb']};
  // available: laws offered by the workspace (2D blast: elastic, JH2, Mohr–Coulomb).
  function checkBlastMaterial(m,law,{available}={}){
    const out=[],n=name(m),target={material:m?.id};
    const {kind}=classify(m),[zhKind,enKind]=classLabel(kind);
    let rec={metal:['jc'],concrete:['hjc','jh2'],rock:['jh2','hjc','dp','mc'],brittle:['jh2']}[kind];
    if(rec&&available){
      rec=rec.filter(k=>available.includes(k));
      if(!rec.length&&kind==='metal'&&law==='elastic'){
        out.push(item('tip','blast.metal.2d',`${n}：二维爆破没有金属塑性本构，按线弹性计算；需要塑性与失效时请使用三维爆破的 Johnson–Cook 材料卡。`,
          `${n}: 2D blast has no metal plasticity, so it is treated as linear elastic; use a Johnson–Cook card in 3D blast for plasticity and failure.`,target));
        rec=null;
      }
    }
    if(rec&&rec.length&&law&&!rec.includes(law)){
      const [zhLaw,enLaw]=BLAST_LAWS[law]||[law,law];
      out.push(item(law==='elastic'?'tip':'warning','blast.law.mismatch',`${n}（识别为${zhKind}）使用“${zhLaw}”。建议：${rec.map(k=>BLAST_LAWS[k][0]).join(' / ')}。${law==='elastic'?'线弹性不产生损伤或破坏，结果只反映应力波。':''}`,
        `${n} (identified as ${enKind}) uses “${enLaw}”. Recommended: ${rec.map(k=>BLAST_LAWS[k][1]).join(' / ')}.${law==='elastic'?' Linear elasticity produces no damage or failure; results show stress waves only.':''}`,target));
    }
    out.push(...checkMaterial(m,{uses:['stiffness','density']}).filter(f=>f.level!=='tip'));
    return out;
  }

  // ---------------------------------------------------------------- fluids & FSI
  function checkFluid(f){
    const out=[],target={page:'fsi-library'};
    if(!f){out.push(item('error','fluid.missing','请在流体材料库中选择流体。','Choose a fluid from the fluid library.',target));return out;}
    const rho=num(f.density),mu=num(f.viscosity);
    if(f.category==='liquid'&&(rho<500||rho>20000))out.push(item('warning','fluid.rho',`${f.name}：液体密度 ${fmt(rho)} kg/m³ 不常见（水约 1000），请核对单位。`,`${f.name}: liquid density ${fmt(rho)} kg/m³ is unusual (water ≈ 1000); check the unit.`,target));
    if(f.category==='gas'&&(rho<0.01||rho>300))out.push(item('warning','fluid.rho.gas',`${f.name}：气体密度 ${fmt(rho)} kg/m³ 不常见（空气约 1.2），请核对单位。`,`${f.name}: gas density ${fmt(rho)} kg/m³ is unusual (air ≈ 1.2); check the unit.`,target));
    if(mu>10)out.push(item('warning','fluid.mu',`${f.name}：动力黏度 ${fmt(mu)} Pa·s 极大（甘油约 1.4），是否按 mPa·s 或 cP 填写了？`,`${f.name}: dynamic viscosity ${fmt(mu)} Pa·s is very large (glycerol ≈ 1.4); was it entered in mPa·s or cP?`,target));
    if(f.model==='idealgas'){
      const T=num(f.temperature),R=num(f.gasConstant);
      if(R>0&&T>0&&rho>0){const p=rho*R*T;if(p<1e3||p>1e8)out.push(item('warning','fluid.state',`${f.name}：ρRT = ${fmt(p)} Pa 偏离常见压力，请核对密度、R 和 T。`,`${f.name}: ρRT = ${fmt(p)} Pa is far from usual pressures; check density, R and T.`,target));}
    }
    return out;
  }
  // ctx: {engine, analysis, turbulence, fluid, speed, length, referencePressure, inlets, outlets, farfields,
  //       solidDensity, relaxation, relaxationFactor, timeStep, steps, cellSize, hasRestraints, dimension}
  function checkFsi(c){
    const out=[],page='fsi',f=c.fluid;
    out.push(...checkFluid(f));
    if(!f)return out;
    if(c.engine==='sph'){
      if(f.model!=='incompressible')out.push(item('error','fsi.sph.gas','SPH 显式路径只支持液体，请选择不可压缩液体，气体请改用 SU2 路径。','The SPH path supports liquids only; choose an incompressible liquid or use the SU2 path for gases.',{page:'fsi-library'}));
      if(c.inlets>0)out.push(item('error','fsi.sph.inlet','SPH 显式路径不支持速度入口；请用“流体初速度”给流体赋速度。','The SPH path has no velocity inlet; give the fluid an initial velocity instead.',{page}));
      if(!(c.gravity>0)&&!(c.speed>0))out.push(item('warning','fsi.sph.still','流体初速度和重力都为零，流体保持静止，结构不受动态载荷。','Initial velocity and gravity are both zero, so the fluid stays at rest and the structure is not loaded dynamically.',{page}));
      if(!c.hasVoid)out.push(item('tip','fsi.sph.void','没有“不参与计算”的空腔体域，流体只能在初始形状内运动；溃坝、冲击等问题请留出流体可进入的空间。','There is no cavity volume, so the fluid can only move within its initial shape; leave space for it to flow into for dam breaks or impacts.',{page}));
      if(c.soundSpeed>0&&c.characteristic>0&&c.soundSpeed<10*c.characteristic)out.push(item('warning','fsi.sph.sound',`数值声速 ${fmt(c.soundSpeed)} m/s 低于特征流速 ${fmt(c.characteristic)} m/s 的 10 倍，流体会明显压缩，压力偏离不可压缩解。`,
        `The numerical sound speed ${fmt(c.soundSpeed)} m/s is below ten times the characteristic speed ${fmt(c.characteristic)} m/s; the fluid compresses noticeably and pressures depart from the incompressible solution.`,{page}));
      if(c.stiffStructure)out.push(item('tip','fsi.sph.stiff','结构刚度高（金属），显式时间步远小于流体粒子；“自动”质量缩放会加快计算，但结构惯性被放大，结果只适合准静态评估。','The structure is stiff (metal), so its explicit step is far below the particle step. Automatic mass scaling speeds up the run but inflates structural inertia; results then suit quasi-static assessment only.',{page}));
    }else{
      if(!c.inlets&&!c.farfields)out.push(item('error','fsi.inlet','流体区至少需要一个速度入口或远场边界。','The fluid needs at least one velocity inlet or far-field boundary.',{page}));
      if(c.inlets&&!c.outlets&&!c.farfields)out.push(item('error','fsi.outlet','有速度入口时还需要压力出口或远场边界，否则流体无处流出。','A velocity inlet also needs a pressure outlet or far field, otherwise the fluid has nowhere to go.',{page}));
      if(c.speed>0&&c.length>0&&f.viscosity>0){
        const rho=f.model==='idealgas'&&c.referencePressure>0?c.referencePressure/(f.gasConstant*f.temperature):f.density;
        const re=rho*c.speed*c.length/f.viscosity;
        if(re>2300&&c.turbulence==='none'&&c.analysis==='steady')out.push(item('warning','fsi.reynolds',`估算雷诺数 Re ≈ ${fmt(re)}，层流稳态在该雷诺数下一般不收敛（流动非定常或已是湍流）。建议选用 SST / SA 湍流模型，或改为瞬态分析。`,
          `Estimated Reynolds number Re ≈ ${fmt(re)}; a steady laminar solution usually does not converge here (the flow is unsteady or turbulent). Use the SST / SA turbulence model or a transient analysis.`,{page,focus:'fsiTurbulence'}));
        else if(re>2300&&c.turbulence==='none')out.push(item('tip','fsi.reynolds.transient',`估算雷诺数 Re ≈ ${fmt(re)}，流动可能为湍流，建议选用湍流模型。`,`Estimated Reynolds number Re ≈ ${fmt(re)}; the flow is likely turbulent, so a turbulence model is advisable.`,{page,focus:'fsiTurbulence'}));
        else if(re<100&&c.turbulence!=='none')out.push(item('tip','fsi.reynolds.low',`估算雷诺数 Re ≈ ${fmt(re)}，流动为层流，湍流模型不必要。`,`Estimated Reynolds number Re ≈ ${fmt(re)}; the flow is laminar, so no turbulence model is needed.`,{page,focus:'fsiTurbulence'}));
      }
      if(f.category==='gas'&&f.model==='incompressible'&&c.speed>0){
        const a=f.soundSpeed>0?f.soundSpeed:343,mach=c.speed/a;
        if(mach>0.3)out.push(item('warning','fsi.mach',`马赫数约 ${fmt(mach)} 超过 0.3，不可压缩假设误差明显，建议改用该气体的理想气体（可压缩）卡。`,`The Mach number ≈ ${fmt(mach)} exceeds 0.3; the incompressible assumption is inaccurate, so use an ideal-gas (compressible) card.`,{page:'fsi-library'}));
      }
      if(f.model==='idealgas'&&c.speed>0){
        const a=Math.sqrt(f.gamma*f.gasConstant*f.temperature),mach=c.speed/a;
        if(mach>=5)out.push(item('error','fsi.mach.high',`马赫数约 ${fmt(mach)}，超出本模块范围（< 5）。`,`The Mach number ≈ ${fmt(mach)} is outside this module's range (< 5).`,{page}));
        else if(mach<0.1)out.push(item('tip','fsi.mach.low',`马赫数约 ${fmt(mach)}，可压缩求解在低速下收敛慢，可改用低速不可压缩卡。`,`The Mach number ≈ ${fmt(mach)}; compressible solvers converge slowly at low speed, so a low-speed incompressible card is preferable.`,{page:'fsi-library'}));
      }
      if(c.engine==='su2'&&c.solidDensity>0){
        const ratio=f.density/c.solidDensity;
        if(ratio>0.3&&(c.relaxation==='fixed'&&c.relaxationFactor>0.5))out.push(item('warning','fsi.addedmass',`流体与结构密度比 ${fmt(ratio)} 较大，附加质量效应强，固定松弛因子 ${fmt(c.relaxationFactor)} 容易使耦合迭代发散。建议改用 Aitken 动态松弛或把松弛因子降到 0.3 以下。`,
          `The fluid-to-structure density ratio ${fmt(ratio)} is high (strong added-mass effect); a fixed relaxation factor of ${fmt(c.relaxationFactor)} easily makes the coupling diverge. Use Aitken relaxation or a factor below 0.3.`,{page,focus:'fsiRelaxation'}));
        else if(ratio>0.3&&c.analysis==='transient')out.push(item('tip','fsi.addedmass.tip',`流体与结构密度比 ${fmt(ratio)} 较大，瞬态耦合可能需要更多耦合迭代次数。`,`The fluid-to-structure density ratio ${fmt(ratio)} is high; transient coupling may need more coupling iterations.`,{page}));
      }
      if(c.analysis==='transient'&&c.timeStep>0&&c.speed>0&&c.cellSize>0){
        const cfl=c.speed*c.timeStep/c.cellSize;
        if(cfl>50)out.push(item('warning','fsi.cfl',`时间步内流体移动约 ${fmt(cfl)} 个单元，涡脱落等非定常现象会被抹平。建议把时间步减小到约 ${fmt(5*c.cellSize/c.speed)} s。`,
          `The fluid travels about ${fmt(cfl)} cells per time step, which smears unsteady features such as vortex shedding. Reduce the time step to about ${fmt(5*c.cellSize/c.speed)} s.`,{page,focus:'fsiTimeStep'}));
        if(c.steps>0&&c.length>0&&c.timeStep*c.steps<c.length/c.speed)out.push(item('tip','fsi.duration',`总时长 ${fmt(c.timeStep*c.steps)} s 小于流体流过模型一次的时间 ${fmt(c.length/c.speed)} s，流场可能尚未发展。`,
          `The total time ${fmt(c.timeStep*c.steps)} s is shorter than one flow-through time ${fmt(c.length/c.speed)} s; the flow may not have developed yet.`,{page,focus:'fsiSteps'}));
      }
      if(c.engine==='oneway')out.push(item('tip','fsi.oneway','单向耦合假设结构变形不影响流场，变形明显时（位移超过流道尺寸的约 1%）请改用双向耦合。','One-way coupling assumes the deformation does not affect the flow; switch to two-way coupling when displacements exceed about 1% of the flow passage.',{page}));
    }
    if(c.hasRestraints===false)out.push(item('error','fsi.restraint','结构没有约束，会发生刚体运动。请在结构绘制页（或三维计算页）给结构边界添加固定支撑。','The structure has no restraints and would move as a rigid body. Add supports to its boundary on the Structure page (or in 3D Analysis).',{page:c.dimension===3?'calculation':'home'}));
    return out;
  }

  // ---------------------------------------------------------------- static
  // ctx: {materials:[...], structureRegions, unassignedRegions, restraints:{x,y,z}, loads, dimension, safety}
  function checkStatic(c){
    const out=[];
    if(!c.structureRegions)out.push(item('error','static.regions',c.dimension===3?'还没有实体，请先建立或导入三维模型。':'还没有结构区域，请先在结构绘制页绘制闭合区域。',c.dimension===3?'There is no solid yet; build or import a 3D model first.':'There is no structural region yet; draw closed regions on the Structure page first.',{page:'home'}));
    if(c.unassignedRegions>0)out.push(item('error','static.material',`${c.unassignedRegions} 个${c.dimension===3?'体域':'结构区域'}尚未分配材料。`,`${c.unassignedRegions} ${c.dimension===3?'volumes have':'structural regions have'} no material assigned.`,{page:c.dimension===3?'calculation':'home'}));
    const r=c.restraints||{};
    if(!r.any)out.push(item('error','static.restraint','模型没有任何约束，静力问题无解（刚体位移）。请添加固定支撑。','The model has no restraints, so the static problem has no solution (rigid-body motion). Add supports.',{page:c.dimension===3?'calculation':'home'}));
    else{
      const missing=['x','y',...(c.dimension===3?['z']:[])].filter(a=>!r[a]);
      if(missing.length)out.push(item('error','static.restraint.axis',`没有任何节点约束 ${missing.map(a=>a.toUpperCase()).join('、')} 方向位移，模型会沿该方向刚体移动。`,`No node restrains the ${missing.map(a=>a.toUpperCase()).join(', ')} displacement, so the model moves freely in that direction.`,{page:c.dimension===3?'calculation':'home'}));
      else if(r.singlePoint)out.push(item('warning','static.restraint.rotation','所有约束集中在一个点上，模型可能绕该点转动（刚体转动）。请在另一位置再加一个约束。','All restraints sit at one point, so the model may rotate about it. Add a restraint at a second location.',{page:c.dimension===3?'calculation':'home'}));
    }
    if(!c.loads)out.push(item('warning','static.loads','模型没有载荷，计算结果将全部为零。','The model has no loads, so every result will be zero.',{page:c.dimension===3?'calculation':'home'}));
    for(const m of c.materials||[])out.push(...checkMaterial(m,{uses:['stiffness',...(c.safety?['safety']:[])],criterion:m.strengthCriterion}));
    return out;
  }

  // Identified class and the models suited to it in each workspace (material library).
  function adviseMaterial(m){
    const {kind,by}=classify(m),[zhKind,enKind]=classLabel(kind);
    if(kind==='unknown')return [item('tip','material.class.unknown',`${name(m)}：无法从名称或参数识别材料类别，请按实际材料选择本构。`,`${name(m)}: the material class cannot be identified from its name or properties; choose models for the actual material.`)];
    const advice={
      metal:['静力安全校核用第四强度理论；损伤变形用 J2 塑性（CalculiX）；三维爆破用 Johnson–Cook 材料卡。','static safety: fourth (von Mises) theory; deformation: J2 plasticity (CalculiX); 3D blast: Johnson–Cook card.'],
      concrete:['静力安全校核用第一强度理论；损伤变形二维用 AT2 相场（PhAST），三维用 Mazars（Code_Aster）或裂带（OOFEM）；爆破用 HJC 材料卡。','static safety: first theory; deformation: AT2 phase field (PhAST) in 2D, Mazars (Code_Aster) or crack band (OOFEM) in 3D; blast: HJC card.'],
      rock:['静力安全校核用第一强度理论；损伤变形二维用 AT2 相场，三维用裂带（OOFEM）；爆破用 JH2（或 Drucker–Prager）材料卡。','static safety: first theory; deformation: AT2 phase field in 2D, crack band (OOFEM) in 3D; blast: JH2 (or Drucker–Prager) card.'],
      brittle:['静力安全校核用第一强度理论；损伤变形用 AT2 相场或裂带断裂。','static safety: first theory; deformation: AT2 phase field or crack band.'],
      rubber:['损伤变形用 Neo-Hooke 或 Mooney–Rivlin 超弹性并启用有限变形；线弹性计算在 ν 接近 0.5 时会锁死。','deformation: Neo-Hooke or Mooney–Rivlin hyperelasticity with finite deformation; linear elastic analysis locks as ν approaches 0.5.'],
      polymer:['小应变下可用线弹性；屈服后用 J2 塑性作近似（不含黏弹性和率效应）。','linear elasticity at small strain; J2 plasticity as an approximation after yield (no viscoelastic or rate effects).']
    }[kind];
    return [item('tip','material.class',`${name(m)} 识别为${zhKind}（依据${by==='name'?'名称':'参数'}）。推荐：${advice[0]}`,`${name(m)} is identified as ${enKind} (from its ${by==='name'?'name':'properties'}). Recommended: ${advice[1]}`)];
  }

  function summarize(findings){
    const count={error:0,warning:0,tip:0};
    for(const f of findings)count[f.level]=(count[f.level]||0)+1;
    return count;
  }
  // Remove duplicates (same code and text), keeping order.
  function unique(findings){
    const seen=new Set();
    return findings.filter(f=>{const k=f.level+'|'+f.zh;if(seen.has(k))return false;seen.add(k);return true;});
  }

  return {classify,classLabel,adviseMaterial,checkMaterial,checkDeformationCard,checkDeformationSettings,recommendDeformation,checkBlastMaterial,
    checkFluid,checkFsi,checkStatic,summarize,unique,DEFORMATION_MODELS,BLAST_LAWS,RANGES};
});
