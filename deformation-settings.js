(function(root){
  'use strict';
  const defaults={solver:'calculix',fractureLoading:'forces',fractureDisplacement:.001,model:'plastic',planeMode:0,finiteStrain:true,increments:40,maxIncrements:400,loadFactor:1,yieldStress:250e6,hardening:1e9,criticalPlasticStrain:0.15};
  const hyperelasticDefaults={c10:500000,c01:100000,d1:2e-8};
  const mazarsDefaults={epsd0:.0001,ac:1.2,at:.9,bc:1500,bt:10000,k:.7};
  const crackBandDefaults={tensileStrength:3e6,crackBandEnergy:100};
  const hyperelasticKeywords={neoHooke:'NEO HOOKE',mooneyRivlin:'MOONEY-RIVLIN'};
  const isHyperelastic=model=>Object.hasOwn(hyperelasticKeywords,model);
  const isMaterialModel=model=>['plastic','elastic','phaseField','mazars','crackBand'].includes(model)||isHyperelastic(model);
  function normalize(raw={}){
    const s={...defaults,...raw};
    if(!['calculix','phast','aster','oofem'].includes(s.solver))throw Error('未知损伤变形求解器。');
    if(!['forces','displacement'].includes(s.fractureLoading)||!Number.isFinite(s.fractureDisplacement)||s.fractureDisplacement<=0)throw Error('断裂加载参数无效。');
    if(!isMaterialModel(s.model))throw Error('未知变形本构。');
    if(![0,1].includes(s.planeMode)||typeof s.finiteStrain!=='boolean')throw Error('二维假设或运动学设置无效。');
    for(const k of ['increments','maxIncrements'])if(!Number.isInteger(s[k])||s[k]<1||s[k]>10000)throw Error('增量数须为 1–10000 的整数。');
    if(s.solver==='calculix'&&s.maxIncrements<s.increments)throw Error('最大增量数不能小于初始增量数。');
    if(!s.materials&&isHyperelastic(s.model)&&!s.finiteStrain)throw Error('超弹性材料需要启用有限变形。');
    for(const k of ['loadFactor','yieldStress','criticalPlasticStrain'])if(!Number.isFinite(s[k])||s[k]<=0)throw Error('载荷系数、屈服应力和损伤起始阈值须为正数。');
    if(!Number.isFinite(s.hardening)||s.hardening<0)throw Error('塑性硬化模量不得为负。');
    const result=Object.fromEntries(Object.keys(defaults).map(k=>[k,s[k]]));
    if(isHyperelastic(s.model))Object.assign(result,normalizeHyperelastic(s));
    if(s.model==='mazars')Object.assign(result,normalizeMazars(s));
    if(s.model==='crackBand')Object.assign(result,normalizeCrackBand(s));
    if(s.model==='plastic'&&raw.hardeningCurve!==undefined)result.hardeningCurve=normalizeHardeningCurve(raw.hardeningCurve);
    if(raw.materials!==undefined){
      if(!raw.materials||typeof raw.materials!=='object'||Array.isArray(raw.materials))throw Error('材料参数映射无效。');
      result.materials=Object.fromEntries(Object.entries(raw.materials).map(([id,card])=>[id,normalizeMaterial(card)]));
    }
    return result;
  }
  function normalizeCrackBand(raw){
    const {tensileStrength,crackBandEnergy}={...crackBandDefaults,...raw};
    if(!Number.isFinite(tensileStrength)||tensileStrength<=0||!Number.isFinite(crackBandEnergy)||crackBandEnergy<=0){
      throw Error('裂带抗拉强度与断裂能须为正数。');
    }
    return {tensileStrength,crackBandEnergy};
  }
  function normalizeMazars(raw){
    const params=Object.fromEntries(Object.keys(mazarsDefaults).map(key=>[key,raw[key]??mazarsDefaults[key]]));
    if(Object.entries(params).some(([key,value])=>!Number.isFinite(value)||(key==='k'?value<0||value>1:value<=0))){
      throw Error('Mazars 参数须为正数，K 须在 0 到 1 之间。');
    }
    return params;
  }
  function normalizeHyperelastic(raw){
    const {c10,c01,d1}={...hyperelasticDefaults,...raw};
    if(!Number.isFinite(c10)||c10<=0||!Number.isFinite(d1)||d1<=0||
      (raw.model==='mooneyRivlin'&&(!Number.isFinite(c01)||c01<0)))throw Error('超弹性参数 C10、D1 须为正数，C01 不得为负。');
    return raw.model==='mooneyRivlin'?{c10,c01,d1}:{c10,d1};
  }
  function normalizeHardeningCurve(curve){
    const invalid=()=>Error('硬化曲线须含 2–1000 行，首行塑性应变为零，应变递增且真应力为正并不下降。');
    if(!Array.isArray(curve)||curve.length<2||curve.length>1000)throw invalid();
    let lastStress=0,lastStrain=-1;
    return curve.map((row,index)=>{
      if(!Array.isArray(row)||row.length!==2)throw invalid();
      const [stress,strain]=row;
      if(!Number.isFinite(stress)||stress<=0||stress<lastStress||!Number.isFinite(strain)||strain<=lastStrain||(!index&&strain!==0))throw invalid();
      lastStress=stress;lastStrain=strain;
      return [stress,strain];
    });
  }
  function normalizeMaterial(raw={}){
    if(!raw||typeof raw!=='object'||Array.isArray(raw))throw Error('材料参数卡无效。');
    const s={...defaults,...raw};
    if(!isMaterialModel(s.model))throw Error('未知变形本构。');
    if(!Number.isFinite(s.yieldStress)||s.yieldStress<=0||!Number.isFinite(s.criticalPlasticStrain)||s.criticalPlasticStrain<=0)throw Error('屈服应力和损伤起始阈值须为正数。');
    if(!Number.isFinite(s.hardening)||s.hardening<0)throw Error('塑性硬化模量不得为负。');
    const fractureEnergy=raw.fractureEnergy??2700,fractureLength=raw.fractureLength??.1;
    if(!Number.isFinite(fractureEnergy)||fractureEnergy<=0||!Number.isFinite(fractureLength)||fractureLength<=0)throw Error('断裂能和相场长度必须为正数。');
    return {model:s.model,yieldStress:s.yieldStress,hardening:s.hardening,criticalPlasticStrain:s.criticalPlasticStrain,fractureEnergy,fractureLength,
      ...(isHyperelastic(s.model)?normalizeHyperelastic(s):{}),
      ...(s.model==='mazars'?normalizeMazars(s):{}),
      ...(s.model==='crackBand'?normalizeCrackBand(raw):{}),
      ...(s.model==='plastic'&&s.hardeningCurve!==undefined?{hardeningCurve:normalizeHardeningCurve(s.hardeningCurve)}:{})};
  }
  function materialFor(settings,id){
    if(settings.materials){if(!Object.hasOwn(settings.materials,String(id)))throw Error('缺少材料的损伤变形参数。');return normalizeMaterial(settings.materials[String(id)]);}
    return normalizeMaterial(settings); // Migration of files saved before per-material cards.
  }
  function normalizeLibraryCard(raw){
    const id=String(raw?.id??'').trim(),name=String(raw?.name??'').trim();
    if(!/^[\w-]{1,100}$/.test(id)||!name)throw Error('请填写有效的损伤变形材料名称和编号。');
    const url=String(raw.sourceUrl??'').trim();
    return {id,name,card:normalizeMaterial(raw.card??null),sourceUrl:/^https?:\/\//i.test(url)?url:'',notes:String(raw.notes??'').trim()};
  }
  const api={defaults,hyperelasticDefaults,hyperelasticKeywords,isHyperelastic,mazarsDefaults,crackBandDefaults,normalize,normalizeMaterial,materialFor,normalizeLibraryCard}; if(typeof module==='object')module.exports=api;else root.DeformationSettings=api;
})(typeof globalThis==='object'?globalThis:this);
