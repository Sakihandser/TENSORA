// Blast constitutive registry. Stable legacy IDs are retained only to reject old selections.
(function(root){
 const availableIds=[1,3,6];
 const names=['已移除：裂带拉伸损伤','线弹性','已移除：DP','JH2','已移除：J2','已移除：Johnson-Cook','Mohr–Coulomb','已移除：Maxwell','已移除：Neo-Hookean','已移除：Cam-Clay','已移除：DP-Cap','已移除：Perzyna','已移除：正交弹性','已移除：Mooney-Rivlin','已移除：HJC'];
 const groups=Array(15).fill(null);groups[3]='jh2';groups[6]='mc';
 const fields={jh2:[['A','完整强度 A',1],['N','完整强度指数 N',1],['B','破碎强度 B',1],['M','破碎强度指数 M',1],
      ['C','应变率系数 C',1],['rate0','参考应变率 (1/s)',1],['HEL','HEL 纵向应力 (GPa)',1e9],['pHEL','HEL 压力 (GPa)',1e9],
      ['T','静水拉伸强度 T (MPa)',1e6],['D1','损伤系数 D1',1],['D2','损伤指数 D2',1],['maxStrength','归一化破碎强度上限',1],
      ['K1','EOS K1 (GPa)',1e9],['K2','EOS K2 (GPa)',1e9],['K3','EOS K3 (GPa)',1e9],['beta','膨胀能量比例 β (0–1)',1],
      ['referenceLength','损伤参考长度 (mm，当前仅支持0)',.001],['normalizationStress','归一化等效应力 σHEL (GPa，0 由 HEL 换算)',1e9],['G','剪切模量 G (GPa，0 使用 E/ν)',1e9],['K','输入体积模量 K (GPa，仅记录，0 使用 E/ν)',1e9]]};
 fields.mc=[['friction','摩擦角 (°)',1],['dilation','剪胀角 (°)',1],['cohesion','黏聚力 (MPa)',1e6],['tension','拉伸截断 (MPa)',1e6],['softening','应变软化 (0/1)',1],['residualFriction','残余摩擦角 (°)',1],['residualDilation','残余剪胀角 (°)',1],['residualCohesion','残余黏聚力 (MPa)',1e6],['peakStrain','软化起始塑性应变',1],['residualStrain','软化结束塑性应变',1]];
 const removed='所选本构已移除，请选择可用本构并填写参数。';
 const help=names.map((_,i)=>i===3?'JH2：压力相关强度、应变率、塑性损伤和破碎剩余强度。':i===1?'线弹性：各向同性弹性响应，不包含塑性和损伤。':i===6?'Mohr–Coulomb：压力相关剪切屈服、拉伸截断与可选应变软化；当前支持小变形平面应变。':removed);
 function normalize(raw){
  if(!raw||typeof raw!=='object'||Array.isArray(raw))return null;
  const out={law:raw.law??-1};if(!Number.isInteger(out.law)||out.law< -1||out.law>14)throw new Error('Invalid constitutive law.');
  if(raw.jh2){out.jh2={};for(const [key]of fields.jh2){const v=raw.jh2[key];if(v!==undefined&&v!==null&&v!==''){if(typeof v!=='number'||!Number.isFinite(v))throw new Error('Invalid JH2 parameter: '+key);out.jh2[key]=v;}}}
  if(raw.mc){out.mc={};for(const [key]of fields.mc){const v=raw.mc[key];if(v!==undefined&&v!==null&&v!==''){if(typeof v!=='number'||!Number.isFinite(v))throw new Error('Invalid Mohr-Coulomb parameter: '+key);out.mc[key]=v;}}}
  if(out.jh2){out.jh2.G??=0;out.jh2.K??=0;}return out;
 }
 function law(m,s){return m.blastConstitutive?.law>=0?m.blastConstitutive.law:s.rockModel??3;}
 function compatibility(material={},settings={}){const model=law(material,settings),errors=[],warnings=[];if(!availableIds.includes(model))errors.push(removed);if(settings.kinematics===1&&settings.planeMode===0&&model!==3)errors.push('有限变形平面应力当前仅支持 JH2。');if(model===6&&(settings.kinematics===1||settings.planeMode!==1))errors.push('Mohr–Coulomb 当前支持小变形平面应变。');return {model,errors,warnings};}
 function validate(material,settings){const card=normalize(material.blastConstitutive),model=law({...material,blastConstitutive:card},settings),prefix=material.name||'#'+material.materialNo;
  if(!availableIds.includes(model))throw new Error(prefix+': '+removed);
  if(model===1)return {model,card};
  if(model===6){const c=card?.mc;if(!c||fields.mc.some(([k])=>!Number.isFinite(c[k]))||!(c.friction>0&&c.friction<89&&c.dilation>=0&&c.dilation<=c.friction&&c.cohesion>0&&c.tension>0&&[0,1].includes(c.softening)&&c.residualFriction>0&&c.residualFriction<=c.friction&&c.residualDilation>=0&&c.residualDilation<=c.residualFriction&&c.residualCohesion>0&&c.residualCohesion<=c.cohesion&&c.peakStrain>=0&&c.residualStrain>c.peakStrain))throw new Error(prefix+': invalid or incomplete Mohr-Coulomb card.');const errors=compatibility(material,settings).errors;if(errors.length)throw new Error(errors.join('\n'));return {model,card};}
  const j=card?.jh2;if(!j||fields.jh2.some(([k])=>!Number.isFinite(j[k])))throw new Error(prefix+': complete the JH2 material card (SI units).');
  if(!(j.A>0&&j.B>=0&&j.N>0&&j.M>0&&j.C>=0&&j.rate0>0&&j.HEL>j.pHEL&&j.pHEL>0&&j.T>0&&j.D1>0&&j.D2>=0&&j.maxStrength>=0&&j.K1>0&&j.beta>=0&&j.beta<=1&&j.normalizationStress>=0&&j.G>=0&&j.K>=0))throw new Error(prefix+': invalid JH2 material card.');
  if(j.referenceLength!==0)throw new Error(prefix+': OpenRadioss local JH2 requires referenceLength=0; nonlocal regularization is not connected.');
  if(j.K3<0||(j.K3===0&&j.K2<0)||(j.K2<0&&j.K1-j.K2*j.K2/(3*j.K3)<=0))throw new Error(prefix+': JH2 EOS has a nonpositive compression tangent.');return {model,card};
 }
 function rows(model,settings){return (model.materials||[]).map(m=>{const {card,model:law}=validate(m,settings);if(law===1)return `${m.materialNo} 1`;if(law===6)return [m.materialNo,6,...fields.mc.map(([k])=>card.mc[k])].join(' ');const row=[m.materialNo,3,...fields.jh2.slice(0,18).map(([k])=>card.jh2[k]),0,0,'ELAS1',card.jh2.G,card.jh2.K];return row.join(' ');}).join('\n')+'\n';}
 const api={names,groups,help,fields,availableIds,normalize,law,compatibility,validate,rows};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.BlastMaterials=api;
})(typeof window!=='undefined'?window:globalThis);
