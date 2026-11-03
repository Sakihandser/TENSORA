(function(root){
  'use strict';
  const defaults={model:'plastic',planeMode:0,finiteStrain:true,increments:40,maxIncrements:400,loadFactor:1,yieldStress:250e6,hardening:1e9,criticalPlasticStrain:0.15};
  function normalize(raw={}){
    const s={...defaults,...raw};
    if(!['plastic','elastic'].includes(s.model))throw Error('未知变形本构。');
    if(![0,1].includes(s.planeMode)||typeof s.finiteStrain!=='boolean')throw Error('二维假设或运动学设置无效。');
    for(const k of ['increments','maxIncrements'])if(!Number.isInteger(s[k])||s[k]<1||s[k]>10000)throw Error('增量数须为 1–10000 的整数。');
    if(s.maxIncrements<s.increments)throw Error('最大增量数不能小于初始增量数。');
    for(const k of ['loadFactor','yieldStress','criticalPlasticStrain'])if(!Number.isFinite(s[k])||s[k]<=0)throw Error('载荷系数、屈服应力和损伤起始阈值须为正数。');
    if(!Number.isFinite(s.hardening)||s.hardening<0)throw Error('塑性硬化模量不得为负。');
    const result=Object.fromEntries(Object.keys(defaults).map(k=>[k,s[k]]));
    if(raw.materials!==undefined){
      if(!raw.materials||typeof raw.materials!=='object'||Array.isArray(raw.materials))throw Error('材料参数映射无效。');
      result.materials=Object.fromEntries(Object.entries(raw.materials).map(([id,card])=>[id,normalizeMaterial(card)]));
    }
    return result;
  }
  function normalizeMaterial(raw={}){
    if(!raw||typeof raw!=='object'||Array.isArray(raw))throw Error('材料参数卡无效。');
    const s={...defaults,...raw};
    if(!['plastic','elastic'].includes(s.model))throw Error('未知变形本构。');
    if(!Number.isFinite(s.yieldStress)||s.yieldStress<=0||!Number.isFinite(s.criticalPlasticStrain)||s.criticalPlasticStrain<=0)throw Error('屈服应力和损伤起始阈值须为正数。');
    if(!Number.isFinite(s.hardening)||s.hardening<0)throw Error('塑性硬化模量不得为负。');
    return {model:s.model,yieldStress:s.yieldStress,hardening:s.hardening,criticalPlasticStrain:s.criticalPlasticStrain};
  }
  function materialFor(settings,id){
    if(settings.materials){if(!Object.hasOwn(settings.materials,String(id)))throw Error('缺少材料的损伤变形参数。');return normalizeMaterial(settings.materials[String(id)]);}
    return normalizeMaterial(settings); // Migration of files saved before per-material cards.
  }
  const api={defaults,normalize,normalizeMaterial,materialFor}; if(typeof module==='object')module.exports=api;else root.DeformationSettings=api;
})(typeof globalThis==='object'?globalThis:this);
