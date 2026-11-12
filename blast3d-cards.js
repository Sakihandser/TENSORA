// Rock material cards for the 3D blast workspace (OpenCourant material laws).
// The same schema runs in the browser (window.Blast3dCards) and in Node.
// Parameters are stored in SI units; `scale` converts from the displayed unit.
(function(root){
  'use strict';
  const MODELS=[
    {id:'elastic',name:'线弹性 · /MAT/ELAST',law:'LAW1',damage:false,
      help:'各向同性线弹性，E、ν、ρ 取自关联的基础材料。可叠加拉伸应变失效以获得损伤与单元失效。'},
    {id:'jh2',name:'JH2 岩石 · /MAT/JOHN_HOLM（LAW79）',law:'LAW79',damage:true,
      help:'Johnson–Holmquist 2：压力相关强度、应变率效应、塑性累积损伤、破碎残余强度和多项式 EOS。'},
    {id:'hjc',name:'HJC 混凝土 · /MAT/JOHNSON_HOLMQUIST_CONCRETE（LAW126）',law:'LAW126',damage:true,
      help:'Holmquist–Johnson–Cook 混凝土：归一化强度面、压溃–压实 EOS 和累积损伤。'},
    {id:'dp',name:'Drucker–Prager · /MAT/DPRAG1（LAW10）',law:'LAW10',damage:false,
      help:'Drucker–Prager 弹塑性。由黏聚力与内摩擦角按与 Mohr–Coulomb 受压子午线外接的锥面换算为 √J2 = k + αp，并设拉伸截断压力。'},
    {id:'jc',name:'Johnson–Cook 金属 · /MAT/PLAS_JOHNS（LAW2）',law:'LAW2',damage:false,
      help:'Johnson–Cook 金属塑性：σy = (A + B·εpⁿ)(1 + C·ln ε̇*)(1 − T*ᵐ)，E、ν、ρ 取自关联的基础材料。塑性应变达到 εp,max 时删除单元；ρCp 为 0 时不计绝热温升（温度软化不起作用）。'}
  ];
  const FIELDS={
    jh2:[['G','剪切模量 G (GPa，0 由 E、ν 计算)',1e9],['A','完整强度系数 A',1],['N','完整强度指数 N',1],['B','破碎强度系数 B',1],['M','破碎强度指数 M',1],
      ['C','应变率系数 C',1],['rate0','参考应变率 (1/s)',1],['maxStrength','归一化破碎强度上限',1],
      ['T','静水拉伸强度 T (MPa)',1e6],['HEL','HEL 纵向应力 (GPa)',1e9],['pHEL','HEL 压力 (GPa)',1e9],
      ['D1','损伤系数 D1',1],['D2','损伤指数 D2',1],['K1','EOS K1 (GPa)',1e9],['K2','EOS K2 (GPa)',1e9],['K3','EOS K3 (GPa)',1e9],['beta','膨胀能量比例 β (0–1)',1]],
    hjc:[['G','剪切模量 G (GPa，0 由 E、ν 计算)',1e9],['A','归一化黏聚强度 A',1],['B','归一化压力硬化系数 B',1],['N','压力硬化指数 N',1],
      ['fc','单轴抗压强度 fc (MPa)',1e6],['T','最大静水拉伸强度 T (MPa)',1e6],['C','应变率系数 C',1],['rate0','参考应变率 (1/s)',1],
      ['maxStrength','归一化强度上限 SFMAX',1],['efMin','最小断裂应变 EFMIN',1],
      ['pc','压溃压力 Pc (MPa)',1e6],['muc','压溃体积应变 μc',1],['pl','压实压力 Pl (GPa)',1e9],['mul','压实体积应变 μl',1],
      ['K1','EOS K1 (GPa)',1e9],['K2','EOS K2 (GPa)',1e9],['K3','EOS K3 (GPa)',1e9],['D1','损伤系数 D1',1],['D2','损伤指数 D2',1]],
    dp:[['cohesion','黏聚力 c (MPa)',1e6],['friction','内摩擦角 φ (°)',1],['tension','拉伸截断（静水拉应力，MPa）',1e6]],
    jc:[['a','屈服强度 A (MPa)',1e6],['b','硬化系数 B (MPa)',1e6],['n','硬化指数 n (0–1]',1],['C','应变率系数 C',1],['rate0','参考应变率 (1/s)',1],
      ['m','温度软化指数 m',1],['tMelt','熔化温度 Tm (K)',1],['tRef','参考温度 Tr (K)',1],['rhoCp','体积比热 ρCp (MJ/(m³·K)，0 不计温升)',1e6],
      ['epsMax','失效塑性应变 εp,max（0 不删除单元）',1],['sigMax','流动应力上限 σmax (MPa，0 不限制)',1e6],['tension','静水拉伸截断（MPa，0 不截断）',1e6]],
    failure:[['strainStart','损伤起始主拉应变 ε₁',1],['strainEnd','完全失效主拉应变 ε₂',1]]
  };
  // Defaults: JH2 from the bundled granite card (thesis section 4.3); HJC from
  // Holmquist, Johnson & Cook (1993) 48 MPa concrete; JC from Johnson & Cook (1983)
  // OFHC copper (ρCp = 8960 kg/m³ × 383 J/(kg·K)); DP and failure are generic
  // starting values that must be calibrated.
  const DEFAULTS={
    jh2:{G:21.9e9,A:0.76,N:0.62,B:0.25,M:0.62,C:0.005,rate0:1,maxStrength:0.25,T:54e6,HEL:4.5e9,pHEL:3.7e9,D1:0.005,D2:0.7,K1:25.7e9,K2:-4.5e12,K3:3e14,beta:0},
    hjc:{G:14.86e9,A:0.79,B:1.6,N:0.61,fc:48e6,T:4e6,C:0.007,rate0:1,maxStrength:7,efMin:0.01,pc:16e6,muc:0.001,pl:0.8e9,mul:0.1,K1:85e9,K2:-171e9,K3:208e9,D1:0.04,D2:1},
    dp:{cohesion:20e6,friction:40,tension:5e6},
    jc:{a:90e6,b:292e6,n:0.31,C:0.025,rate0:1,m:1.09,tMelt:1356,tRef:293,rhoCp:3.43168e6,epsMax:0,sigMax:0,tension:0},
    failure:{strainStart:2e-4,strainEnd:1e-3}
  };
  const MODEL_IDS=MODELS.map(m=>m.id);
  function number(raw,key,fallback){
    const value=raw?.[key];
    if(value===undefined||value===null||value==='')return fallback;
    const n=Number(value);
    if(!Number.isFinite(n))throw new Error(`材料卡参数无效：${key}`);
    return n;
  }
  function normalize(raw={}){
    const model=MODEL_IDS.includes(raw?.model)?raw.model:'elastic';
    const card={model};
    for(const [key] of FIELDS[model]||[])card[key]=number(raw,key,DEFAULTS[model][key]);
    const failure=raw?.failure&&typeof raw.failure==='object'?raw.failure:{};
    card.failure={enabled:failure.enabled===true};
    for(const [key] of FIELDS.failure)card.failure[key]=number(failure,key,DEFAULTS.failure[key]);
    return card;
  }
  // Throws a readable error for parameters that the OpenCourant law cannot use.
  function validate(raw,label='材料卡'){
    const c=normalize(raw);
    const fail=message=>{throw new Error(`${label}：${message}`);};
    if(c.model==='jh2'){
      if(!(c.A>0&&c.N>0&&c.B>=0&&c.M>0&&c.C>=0&&c.rate0>0&&c.maxStrength>=0&&c.T>0&&c.HEL>c.pHEL&&c.pHEL>0&&c.D1>0&&c.D2>=0&&c.K1>0&&c.beta>=0&&c.beta<=1&&c.G>=0))fail('JH2 参数需满足 A、N、M、T、D1、K1 > 0，HEL > pHEL > 0，0 ≤ β ≤ 1。');
    }
    if(c.model==='hjc'){
      if(!(c.A>0&&c.B>=0&&c.N>0&&c.fc>0&&c.T>0&&c.C>=0&&c.rate0>0&&c.maxStrength>0&&c.efMin>=0&&c.pc>0&&c.muc>0&&c.pl>c.pc&&c.mul>c.muc&&c.K1>0&&c.D1>0&&c.D2>=0&&c.G>=0))fail('HJC 参数需满足 A、N、fc、T、Pc、μc、K1、D1 > 0，Pl > Pc，μl > μc。');
    }
    if(c.model==='dp'){
      if(!(c.cohesion>0&&c.friction>=0&&c.friction<89&&c.tension>0))fail('Drucker–Prager 需要 c > 0、0 ≤ φ < 89° 与正的拉伸截断。');
    }
    if(c.model==='jc'){
      // OpenCourant LAW2 Starter rejects n > 1 and a zero reference strain rate.
      if(!(c.a>0&&c.b>=0&&c.n>0&&c.n<=1&&c.C>=0&&c.rate0>0&&c.m>0&&c.tRef>0&&c.tMelt>c.tRef&&c.rhoCp>=0&&c.epsMax>=0&&c.sigMax>=0&&c.tension>=0))
        fail('Johnson–Cook 需要 A > 0、0 < n ≤ 1、参考应变率 > 0、m > 0、Tm > Tr > 0，其余参数不得为负。');
    }
    if(c.failure.enabled&&!(c.failure.strainStart>0&&c.failure.strainEnd>c.failure.strainStart))fail('拉伸应变失效需满足 0 < ε₁ < ε₂。');
    return c;
  }
  function normalizeLibraryCard(raw={}){
    const id=String(raw.id||'').trim();
    if(!/^[A-Za-z0-9_-]{1,100}$/.test(id))throw new Error('材料卡编号无效。');
    const name=String(raw.name||'').trim();
    if(!name||name.length>160)throw new Error('请填写材料卡名称（不超过 160 字）。');
    return {id,name,sourceUrl:String(raw.sourceUrl||'').trim().slice(0,2000),notes:String(raw.notes||'').slice(0,12000),
      card:validate(raw.card,name),updatedAt:String(raw.updatedAt||new Date().toISOString())};
  }
  // Drucker-Prager cone outer to the Mohr-Coulomb compression meridian:
  // sqrt(J2) = k + alpha*p (p > 0 in compression) -> J2 = A0 + A1 p + A2 p^2.
  function druckerPrager(card){
    const phi=card.friction*Math.PI/180,s=Math.sin(phi),denominator=Math.sqrt(3)*(3-s);
    const alpha=6*s/denominator,k=6*card.cohesion*Math.cos(phi)/denominator;
    return {alpha,k,A0:k*k,A1:2*k*alpha,A2:alpha*alpha,pMin:-card.tension};
  }
  function describe(card){
    const c=normalize(card),model=MODELS.find(m=>m.id===c.model);
    return model.name.split(' · ')[0]+(c.failure.enabled?' + 拉伸应变失效':'');
  }
  // 2D blast cards (law 1 elastic, law 3 JH2) remain usable as a fallback.
  function fromBlastConstitutive(raw){
    if(raw?.law===3&&raw.jh2){const j=raw.jh2;return normalize({model:'jh2',...j});}
    return normalize({model:'elastic'});
  }
  const api={MODELS,FIELDS,DEFAULTS,normalize,validate,normalizeLibraryCard,druckerPrager,describe,fromBlastConstitutive};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.Blast3dCards=api;
})(typeof window!=='undefined'?window:globalThis);
