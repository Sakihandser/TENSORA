// OpenCourant solid material cards shared by the 2D/3D blast workspaces and the
// damage & deformation workspace. The same schema runs in the browser
// (window.Blast3dCards) and in Node. Parameters are stored in SI units; `scale`
// converts from the displayed unit. `materialLines` only writes the upstream
// keyword cards: every constitutive update is computed by the unmodified
// OpenCourant Starter/Engine (RHT by the OpenCourant tools/rht_user_material
// user library loaded with -dylib).
(function(root){
  'use strict';
  const MODELS=[
    {id:'elastic',name:'线弹性 · /MAT/ELAST',law:'LAW1',damage:false,
      help:'各向同性线弹性，E、ν、ρ 取自关联的基础材料。可叠加拉伸应变失效以获得损伤与单元失效。'},
    {id:'jh2',name:'JH2 岩石 · /MAT/JOHN_HOLM（LAW79）',law:'LAW79',damage:true,
      help:'Johnson–Holmquist 2：压力相关强度、应变率效应、塑性累积损伤、破碎残余强度和多项式 EOS。'},
    {id:'rht',name:'RHT 混凝土/岩石 · /MAT/USER01（OpenCourant RHT 用户材料）',law:'USER01',damage:true,
      help:'Riedel–Hiermaier–Thoma 三曲面模型：压力与 Lode 角相关的失效面、弹性极限面与硬化帽、拉压分离的应变率增强、p-α 孔隙压实 EOS、峰后损伤与残余摩擦强度。由 OpenCourant 仓库 tools/rht_user_material 编译的用户材料库计算，E、ν 不参与（弹性由剪切模量 G 与 EOS A1/α0 决定），ρ 取自基础材料。'},
    {id:'hjc',name:'HJC 混凝土 · /MAT/JOHNSON_HOLMQUIST_CONCRETE（LAW126）',law:'LAW126',damage:true,
      help:'Holmquist–Johnson–Cook 混凝土：归一化强度面、压溃–压实 EOS 和累积损伤。'},
    {id:'cdpm2',name:'CDPM2 混凝土损伤塑性 · /MAT/CDPM2（LAW124）',law:'LAW124',damage:true,
      help:'Grassl 等的混凝土损伤塑性模型 CDPM2：塑性硬化与拉/压两个损伤变量，双线性拉伸软化按断裂能与单元长度正则化（裂带）。E、ν、ρ 取自关联的基础材料。'},
    {id:'dp',name:'Drucker–Prager · /MAT/DPRAG1（LAW10）',law:'LAW10',damage:false,
      help:'Drucker–Prager 弹塑性。由黏聚力与内摩擦角按与 Mohr–Coulomb 受压子午线外接的锥面换算为 √J2 = k + αp，并设拉伸截断压力。'},
    {id:'dpcap',name:'Drucker–Prager 帽盖 · /MAT/LAW81（DPRAG_CAP）',law:'LAW81',damage:false,
      help:'带压缩帽盖的 Drucker–Prager 模型，适用于岩土与多孔岩石：剪切锥由 Mohr–Coulomb 的 c、φ 按受压子午线换算到 q–p 平面，非关联流动由剪胀角 ψ 控制，帽盖压力 Pb 随塑性体积压缩线性硬化。E、ν、ρ 取自关联的基础材料。'},
    {id:'jc',name:'Johnson–Cook 金属 · /MAT/PLAS_JOHNS（LAW2）',law:'LAW2',damage:false,
      help:'Johnson–Cook 金属塑性：σy = (A + B·εpⁿ)(1 + C·ln ε̇*)(1 − T*ᵐ)，E、ν、ρ 取自关联的基础材料。塑性应变达到 εp,max 时删除单元；ρCp 为 0 时不计绝热温升（温度软化不起作用）。'}
  ];
  const FIELDS={
    jh2:[['G','剪切模量 G (GPa，0 由 E、ν 计算)',1e9],['A','完整强度系数 A',1],['N','完整强度指数 N',1],['B','破碎强度系数 B',1],['M','破碎强度指数 M',1],
      ['C','应变率系数 C',1],['rate0','参考应变率 (1/s)',1],['maxStrength','归一化破碎强度上限',1],
      ['T','静水拉伸强度 T (MPa)',1e6],['HEL','HEL 纵向应力 (GPa)',1e9],['pHEL','HEL 压力 (GPa)',1e9],
      ['D1','损伤系数 D1',1],['D2','损伤指数 D2',1],['K1','EOS K1 (GPa)',1e9],['K2','EOS K2 (GPa)',1e9],['K3','EOS K3 (GPa)',1e9],['beta','膨胀能量比例 β (0–1)',1]],
    rht:[['G','剪切模量 G (GPa)',1e9],['fc','单轴抗压强度 fc (MPa)',1e6],['fsRatio','剪切强度比 fs/fc',1],['ftRatio','拉伸强度比 ft/fc',1],
      ['A','失效面系数 A',1],['N','失效面指数 N (0–1]',1],['Q0','拉/压子午线比 Q0 (0.5–1]',1],['B','Lode 压力系数 B',1],
      ['Af','残余强度系数 Af',1],['Nf','残余强度指数 Nf',1],['gc','压缩弹性极限比 gc*',1],['gt','拉伸弹性极限比 gt*',1],['xi','硬化剪切模量比 ξ',1],
      ['D1','损伤系数 D1',1],['D2','损伤指数 D2',1],['epm','最小失效应变 εp,m',1],
      ['betaC','压缩应变率指数 βc (0–1/3)',1],['betaT','拉伸应变率指数 βt (0–1/3)',1],['e0c','压缩参考应变率 (1/s)',1],['e0t','拉伸参考应变率 (1/s)',1],
      ['ec','压缩转折应变率 (1/s)',1],['et','拉伸转折应变率 (1/s)',1],['ptf','拉伸塑性流动压力系数 PTF (0–1]',1],
      ['A1','EOS A1 (GPa)',1e9],['A2','EOS A2 (GPa)',1e9],['A3','EOS A3 (GPa)',1e9],['B0','EOS B0',1],['B1','EOS B1',1],
      ['T1','EOS T1 (GPa)',1e9],['T2','EOS T2 (GPa)',1e9],['gamma','Grüneisen γ（B0 = 0 时）',1],
      ['alpha0','初始孔隙度 α0 (≥1)',1],['pel','孔隙压溃起始压力 (MPa)',1e6],['pco','完全压实压力 (GPa)',1e9],['np','压实曲线指数 n (≥1)',1],
      ['epsf','侵蚀塑性应变（0 不删除单元）',1]],
    hjc:[['G','剪切模量 G (GPa，0 由 E、ν 计算)',1e9],['A','归一化黏聚强度 A',1],['B','归一化压力硬化系数 B',1],['N','压力硬化指数 N',1],
      ['fc','单轴抗压强度 fc (MPa)',1e6],['T','最大静水拉伸强度 T (MPa)',1e6],['C','应变率系数 C',1],['rate0','参考应变率 (1/s)',1],
      ['maxStrength','归一化强度上限 SFMAX',1],['efMin','最小断裂应变 EFMIN',1],
      ['pc','压溃压力 Pc (MPa)',1e6],['muc','压溃体积应变 μc',1],['pl','压实压力 Pl (GPa)',1e9],['mul','压实体积应变 μl',1],
      ['K1','EOS K1 (GPa)',1e9],['K2','EOS K2 (GPa)',1e9],['K3','EOS K3 (GPa)',1e9],['D1','损伤系数 D1',1],['D2','损伤指数 D2',1]],
    cdpm2:[['fc','单轴抗压强度 fc (MPa)',1e6],['ft','单轴抗拉强度 ft (MPa)',1e6],['gf','断裂能 Gf (J/m²)',1],
      ['hp','硬化模量 Hp',1],['qh0','初始硬化 qh0 (0–1)',1],['as','压缩损伤延性 As',1],['df','剪胀常数 Df',1],['efc','压缩损伤应变阈值 εfc',1],
      ['rate','应变率增强（1 开启 / 0 关闭）',1],['erode','完全损伤后删除单元（1 是 / 0 否）',1]],
    dp:[['cohesion','黏聚力 c (MPa)',1e6],['friction','内摩擦角 φ (°)',1],['tension','拉伸截断（静水拉应力，MPa）',1e6]],
    dpcap:[['cohesion','黏聚力 c (MPa，Mohr–Coulomb)',1e6],['friction','内摩擦角 φ (°)',1],['dilation','剪胀角 ψ (°)',1],
      ['capPressure','初始帽盖压力 Pb (MPa)',1e6],['capRatio','过渡压力比 Pa/Pb (0–1)',1],['capHardening','帽盖硬化模量 dPb/dεv (MPa，0 不硬化)',1e6]],
    jc:[['a','屈服强度 A (MPa)',1e6],['b','硬化系数 B (MPa)',1e6],['n','硬化指数 n (0–1]',1],['C','应变率系数 C',1],['rate0','参考应变率 (1/s)',1],
      ['m','温度软化指数 m',1],['tMelt','熔化温度 Tm (K)',1],['tRef','参考温度 Tr (K)',1],['rhoCp','体积比热 ρCp (MJ/(m³·K)，0 不计温升)',1e6],
      ['epsMax','失效塑性应变 εp,max（0 不删除单元）',1],['sigMax','流动应力上限 σmax (MPa，0 不限制)',1e6],['tension','静水拉伸截断（MPa，0 不截断）',1e6]],
    failure:[['strainStart','损伤起始主拉应变 ε₁',1],['strainEnd','完全失效主拉应变 ε₂',1]]
  };
  // Defaults: JH2 from the bundled granite card (thesis section 4.3); RHT is the
  // 35 MPa concrete demonstration set of OpenCourant tools/rht_user_material
  // (Borrvall & Riedel 2011); HJC from Holmquist, Johnson & Cook (1993) 48 MPa
  // concrete; CDPM2 uses fib MC2010 C30/37 strengths and fracture energy with the
  // Grassl et al. (2013) defaults; JC from Johnson & Cook (1983) OFHC copper
  // (ρCp = 8960 kg/m³ × 383 J/(kg·K)); DP, DP-cap and failure are generic starting
  // values that must be calibrated.
  const DEFAULTS={
    jh2:{G:21.9e9,A:0.76,N:0.62,B:0.25,M:0.62,C:0.005,rate0:1,maxStrength:0.25,T:54e6,HEL:4.5e9,pHEL:3.7e9,D1:0.005,D2:0.7,K1:25.7e9,K2:-4.5e12,K3:3e14,beta:0},
    rht:{G:16.7e9,fc:35e6,fsRatio:0.18,ftRatio:0.10,A:1.6,N:0.61,Q0:0.6805,B:0.0105,Af:1.6,Nf:0.61,gc:0.53,gt:0.70,xi:0.5,
      D1:0.04,D2:1,epm:0.01,betaC:0.032,betaT:0.036,e0c:3e-5,e0t:3e-6,ec:3e25,et:3e25,ptf:0.001,
      A1:35.27e9,A2:39.58e9,A3:9.04e9,B0:1.22,B1:1.22,T1:35.27e9,T2:0,gamma:0,alpha0:1.1884,pel:23.3e6,pco:6e9,np:3,epsf:2},
    hjc:{G:14.86e9,A:0.79,B:1.6,N:0.61,fc:48e6,T:4e6,C:0.007,rate0:1,maxStrength:7,efMin:0.01,pc:16e6,muc:0.001,pl:0.8e9,mul:0.1,K1:85e9,K2:-171e9,K3:208e9,D1:0.04,D2:1},
    cdpm2:{fc:38e6,ft:2.9e6,gf:141,hp:0.01,qh0:0.3,as:15,df:0.85,efc:1e-4,rate:1,erode:0},
    dp:{cohesion:20e6,friction:40,tension:5e6},
    dpcap:{cohesion:20e6,friction:40,dilation:10,capPressure:150e6,capRatio:0.5,capHardening:5000e6},
    jc:{a:90e6,b:292e6,n:0.31,C:0.025,rate0:1,m:1.09,tMelt:1356,tRef:293,rhoCp:3.43168e6,epsMax:0,sigMax:0,tension:0},
    failure:{strainStart:2e-4,strainEnd:1e-3}
  };
  const MODEL_IDS=MODELS.map(m=>m.id);
  // Field of the OpenCourant animation that carries the constitutive damage.
  const DAMAGE_SOURCE={jh2:'damg',hjc:'damg',cdpm2:'damg',rht:'usr3'};
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
  // RHT tensile-cutoff admissibility (rht_validate in rht_material_mod.F90).
  function rhtLode(costheta,q){
    const a=1-q*q,b=2*q-1,rad=Math.max(0,4*a*costheta**2+5*q*q-4*q);
    return (2*a*costheta+b*Math.sqrt(rad))/(4*a*costheta**2+b*b);
  }
  // Throws a readable error for parameters that the OpenCourant law cannot use.
  function validate(raw,label='材料卡'){
    const c=normalize(raw);
    const fail=message=>{throw new Error(`${label}：${message}`);};
    if(c.model==='jh2'){
      if(!(c.A>0&&c.N>0&&c.B>=0&&c.M>0&&c.C>=0&&c.rate0>0&&c.maxStrength>=0&&c.T>0&&c.HEL>c.pHEL&&c.pHEL>0&&c.D1>0&&c.D2>=0&&c.K1>0&&c.beta>=0&&c.beta<=1&&c.G>=0))fail('JH2 参数需满足 A、N、M、T、D1、K1 > 0，HEL > pHEL > 0，0 ≤ β ≤ 1。');
    }
    if(c.model==='rht'){
      if(!(c.G>0&&c.fc>0&&c.fsRatio>0&&c.ftRatio>0&&c.A>0&&c.N>0&&c.N<=1&&c.Q0>0.5&&c.Q0<=1&&c.B>=0))fail('RHT 需要 G、fc、fs/fc、ft/fc、A > 0，0 < N ≤ 1，0.5 < Q0 ≤ 1，B ≥ 0。');
      if(!(c.e0c>0&&c.e0t>0&&c.ec>=c.e0c&&c.et>=c.e0t&&c.betaC>=0&&c.betaT>=0&&c.betaC<=1/3&&c.betaT<=1/3&&c.ptf>0&&c.ptf<=1))fail('RHT 应变率参数需满足参考应变率 > 0、转折应变率不小于参考值、0 ≤ βc、βt ≤ 1/3，0 < PTF ≤ 1。');
      if(!(c.gc>0&&c.gt>0&&c.xi>0&&c.gc<=1&&c.gt<=1&&c.xi<=1&&c.D1>0&&c.D2>0&&c.epm>0&&c.Nf>0&&c.Af>=0&&c.epsf>=0))fail('RHT 需要 0 < gc*、gt*、ξ ≤ 1，D1、D2、εp,m、Nf > 0，Af 与侵蚀应变不得为负。');
      if(!(c.A1>0&&c.A2>=0&&c.A3>=0&&c.B0>=0&&c.B1>=0&&c.T1>0&&c.gamma>=0&&c.pel>=0&&c.pco>c.pel&&c.np>=1&&c.alpha0>=1))fail('RHT 状态方程需要 A1、T1 > 0，A2、A3、B0、B1、γ ≥ 0，完全压实压力大于压溃起始压力，n ≥ 1，α0 ≥ 1。');
      const q1=rhtLode(Math.sqrt(3)/2,c.Q0),qmin=c.B>0?0.5+Number.EPSILON:Math.max(0.5+Number.EPSILON,c.Q0);
      const shear=qmin*c.fsRatio,tensile=q1*c.ftRatio;
      if(!(shear-tensile>64*Number.EPSILON*Math.max(shear,tensile)))fail(`RHT 拉伸截断不成立：需要 Q_min·fs/fc（${shear.toPrecision(4)}）大于纯剪 Lode 因子 × ft/fc（${tensile.toPrecision(4)}）。请提高 fs/fc、降低 ft/fc，或取 B = 0。`);
    }
    if(c.model==='hjc'){
      if(!(c.A>0&&c.B>=0&&c.N>0&&c.fc>0&&c.T>0&&c.C>=0&&c.rate0>0&&c.maxStrength>0&&c.efMin>=0&&c.pc>0&&c.muc>0&&c.pl>c.pc&&c.mul>c.muc&&c.K1>0&&c.D1>0&&c.D2>=0&&c.G>=0))fail('HJC 参数需满足 A、N、fc、T、Pc、μc、K1、D1 > 0，Pl > Pc，μl > μc。');
    }
    if(c.model==='cdpm2'){
      if(!(c.fc>0&&c.ft>0&&c.ft<c.fc&&c.gf>0&&c.hp>=0&&c.qh0>0&&c.qh0<1&&c.as>0&&c.df>0&&c.df<=1&&c.efc>0&&[0,1].includes(c.rate)&&[0,1].includes(c.erode)))
        fail('CDPM2 需要 0 < ft < fc、Gf > 0、0 < qh0 < 1、As > 0、0 < Df ≤ 1、εfc > 0，Hp 不得为负；应变率与删除开关只能为 0 或 1。');
    }
    if(c.model==='dp'){
      if(!(c.cohesion>0&&c.friction>=0&&c.friction<89&&c.tension>0))fail('Drucker–Prager 需要 c > 0、0 ≤ φ < 89° 与正的拉伸截断。');
    }
    if(c.model==='dpcap'){
      if(!(c.cohesion>0&&c.friction>0&&c.friction<70&&c.dilation>=0&&c.dilation<=c.friction&&c.capPressure>0&&c.capRatio>0&&c.capRatio<1&&c.capHardening>=0))
        fail('Drucker–Prager 帽盖需要 c > 0、0 < φ < 70°、0 ≤ ψ ≤ φ、Pb > 0、0 < Pa/Pb < 1，帽盖硬化模量不得为负。');
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
  // LAW81 works in the von Mises q - pressure p plane: q = c_q + p tan(beta).
  // The same compression-meridian match gives tan(beta) = sqrt(3) alpha and
  // c_q = sqrt(3) k; the plastic flow angle uses the dilation angle likewise.
  function capCone(card){
    const meridian=deg=>{const s=Math.sin(deg*Math.PI/180);return 6*s/(3-s);};
    const tanBeta=meridian(card.friction),phi=card.friction*Math.PI/180;
    const cq=6*card.cohesion*Math.cos(phi)/(3-Math.sin(phi));
    return {cq,beta:Math.atan(tanBeta)*180/Math.PI,psi:Math.atan(meridian(card.dilation))*180/Math.PI,apexTension:cq/tanBeta};
  }
  // CDPM2 bilinear softening (DTYPE=2, FT1=0.3 ft, WF1=0.15 wf): Gf = 0.225 ft wf.
  const cdpm2CrackOpening=card=>card.gf/(0.225*card.ft);
  function describe(card){
    const c=normalize(card),model=MODELS.find(m=>m.id===c.model);
    return model.name.split(' · ')[0]+(c.failure.enabled?' + 拉伸应变失效':'');
  }
  // 2D blast cards (law 1 elastic, law 3 JH2) remain usable as a fallback.
  function fromBlastConstitutive(raw){
    if(raw?.law===3&&raw.jh2){const j=raw.jh2;return normalize({model:'jh2',...j});}
    return normalize({model:'elastic'});
  }

  // ------------------------------------------------------------- deck lines
  const f20=value=>{
    if(!Number.isFinite(value))throw Error('卡片数值无效');
    const text=value===0?'0':Math.abs(value)>=1e-3&&Math.abs(value)<1e9?String(Number(value.toPrecision(14))):value.toExponential(12);
    if(text.length>20)return value.toExponential(11).padStart(20);
    return text.padStart(20);
  };
  const i10=value=>{if(!Number.isSafeInteger(value))throw Error('卡片编号无效');return String(value).padStart(10);};
  const title=text=>String(text).replace(/[^\x20-\x7e]/g,'_').slice(0,100);
  // Material functions get ids far above the deck's own card counters.
  const FUNCTION_BASE=800000;
  // Lines of one OpenCourant material (and its failure model). `base` holds the
  // base material {id, name, rho, E, nu}. Returns the lines plus the moduli used
  // for wave speeds, initial-stress densities and result labels.
  function materialLines(raw,base,label='材料卡'){
    const card=validate(raw,label);
    const {id,rho,E,nu}=base,name=title(base.name||'material');
    if(!(rho>0)||!(E>0)||!(nu>-1&&nu<.5))throw Error(`${label}：需要正的密度、弹性模量与 -1 < ν < 0.5。`);
    const Gel=E/(2*(1+nu)),Kel=E/(3*(1-2*nu));
    const out={law:card.model,card,rho,E,nu,G:Gel,K:Kel,damage:DAMAGE_SOURCE[card.model]||null,userLibrary:null,erodes:false,functions:[]};
    if(card.model==='elastic'){
      out.lines=[`/MAT/ELAST/${id}`,name,'#              RHO_I',f20(rho),'#                  E                  nu',f20(E)+f20(nu)];
    }else if(card.model==='jh2'){
      const G=card.G>0?card.G:Gel;
      Object.assign(out,{G,K:card.K1,K1:card.K1,K2:card.K2,K3:card.K3});
      out.lines=[`/MAT/JOHN_HOLM/${id}`,name,
        '#              RHO_I',f20(rho),'#                  G',f20(G),
        '#                  a                   b                   m                   n',f20(card.A)+f20(card.B)+f20(card.M)+f20(card.N),
        '#                  c                EPS0          SIGMA_FMAX',f20(card.C)+f20(card.rate0)+f20(card.maxStrength),
        '#                  T                 HEL                PHEL',f20(card.T)+f20(card.HEL)+f20(card.pHEL),
        '#                 D1                  D2',f20(card.D1)+f20(card.D2),
        '#                 K1                  K2                  K3                BETA',f20(card.K1)+f20(card.K2)+f20(card.K3)+f20(card.beta)];
    }else if(card.model==='rht'){
      // /MAT/USER01 of tools/rht_user_material: native density, then 38 constants
      // read list-directed (constant 1 must equal the native density).
      const c=[rho,card.G,1e6,card.epsf,card.B0,card.B1,card.T1,card.A,card.N,card.fc,card.fsRatio,card.ftRatio,card.Q0,card.B,card.T2,
        card.e0c,card.e0t,card.ec,card.et,card.betaC,card.betaT,card.ptf,card.gc,card.gt,card.xi,card.D1,card.D2,card.epm,card.Af,card.Nf,
        card.gamma,card.A1,card.A2,card.A3,card.pel,card.pco,card.np,card.alpha0];
      const text=v=>String(Number(v.toPrecision(12)));
      const rows=[];for(let i=0;i<c.length;i+=5)rows.push(' '+c.slice(i,i+5).map(text).join(' '));
      // Initial bulk modulus of the porous EOS: K = A1 / alpha0 (lecmuser01).
      Object.assign(out,{G:card.G,K:card.A1/card.alpha0,userLibrary:'rht',erodes:card.epsf>0});
      out.lines=[`/MAT/USER01/${id}`,name,f20(rho),...rows];
    }else if(card.model==='hjc'){
      const G=card.G>0?card.G:Gel;
      Object.assign(out,{G,K:card.pc/card.muc,pc:card.pc,muc:card.muc});
      out.lines=[`/MAT/JOHNSON_HOLMQUIST_CONCRETE/${id}`,name,
        '#        Init. dens.',f20(rho),'#                  G',f20(G),
        '#                  A                   B                   N                  FC                   T',f20(card.A)+f20(card.B)+f20(card.N)+f20(card.fc)+f20(card.T),
        '#                  C                EPS0                FCUT               SFMAX               EFMIN',f20(card.C)+f20(card.rate0)+f20(0)+f20(card.maxStrength)+f20(card.efMin),
        '#                 PC                 MUC                  PL                 MUL',f20(card.pc)+f20(card.muc)+f20(card.pl)+f20(card.mul),
        '#                 K1                  K2                  K3',f20(card.K1)+f20(card.K2)+f20(card.K3),
        '#                 D1                  D2                IDEL             EPS_MAX             IFAILSO',f20(card.D1)+f20(card.D2)+' '.repeat(10)+i10(0)+f20(0)+' '.repeat(10)+i10(0),
        '#                 CT                POWT                  CC                POWC',f20(0)+f20(0)+f20(0)+f20(0)];
    }else if(card.model==='cdpm2'){
      // LAW124 (radioss2023 layout). Zero AH..DH, BS, ECC take the Starter defaults;
      // DFLAG 1 (tension + compression damage), DTYPE 2 (bilinear), IREG 2 (crack band).
      const wf=cdpm2CrackOpening(card);
      Object.assign(out,{erodes:card.erode===1,crackOpening:wf});
      out.lines=[`/MAT/CDPM2/${id}`,name,'#              RHO_I',f20(rho),
        '#                  E                  NU                IDEL               IRATE                FCUT',
        f20(E)+f20(nu)+' '.repeat(10)+i10(card.erode?2:1)+' '.repeat(10)+i10(card.rate?2:1)+f20(0),
        '#                ECC                 QH0                  FT                  FC                  HP',f20(0)+f20(card.qh0)+f20(card.ft)+f20(card.fc)+f20(card.hp),
        '#                 AH                  BH                  CH                  DH',f20(0)+f20(0)+f20(0)+f20(0),
        '#                 AS                  BS                  DF               DFLAG     DTYPE      IREG',f20(card.as)+f20(0)+f20(card.df)+' '.repeat(10)+i10(1)+i10(2)+i10(2),
        '#                 WF                 WF1                 FT1                 EFC',f20(wf)+f20(0.15*wf)+f20(0.3*card.ft)+f20(card.efc)];
    }else if(card.model==='dpcap'){
      // LAW81 (radioss2025 layout). Constant K, G, c; the cap pressure grows with the
      // compressive plastic volumetric strain through a linear function; Isoft = 1
      // keeps the cap from softening.
      const cone=capCone(card),fid=card.capHardening>0?FUNCTION_BASE+id:0;
      Object.assign(out,{cap:cone});
      // The radioss2026 keyword map only names this law LAW81 (not DPRAG_CAP).
      out.lines=[`/MAT/LAW81/${id}`,name,'#              RHO_I',f20(rho),
        '#                 K0                  G0                  C0                 PB0',f20(Kel)+f20(Gel)+f20(cone.cq)+f20(card.capPressure),
        '#                PHI                 PSI',f20(cone.beta)+f20(cone.psi),
        '#              ALPHA             EPS_MAX               EPS_0',f20(card.capRatio)+f20(0)+f20(0),
        '#  Fct_IDK   Fct_IDG   Fct_IDc  Fct_IDPb     Isoft',i10(0)+i10(0)+i10(0)+i10(fid)+i10(1),
        '#                 KW                  N0                  S0                  U0',f20(0)+f20(0)+f20(0)+f20(0),
        '#                TOL             ALPHA_V',f20(0)+f20(0)];
      if(fid){
        const slope=card.capHardening/card.capPressure;
        out.functions.push(fid);
        out.lines.push(`/FUNCT/${fid}`,title(`${base.name||'material'} cap hardening`),'#                  X                   Y',
          f20(-1)+f20(1),f20(0)+f20(1),f20(1)+f20(1+slope));
      }
    }else if(card.model==='jc'){
      // LAW2 Johnson-Cook (radioss2025 layout). Zero Pmin, EPS_p_max and SIG_max0 mean
      // "no cutoff" in the Starter; plastic strain above EPS_p_max deletes the element.
      out.erodes=card.epsMax>0;
      out.lines=[`/MAT/PLAS_JOHNS/${id}`,name,
        '#              RHO_I',f20(rho),
        '#                  E                  Nu     Iflag    flagVP                Pmin',f20(E)+f20(nu)+i10(0)+i10(0)+f20(card.tension>0?-card.tension:0),
        '#                  a                   b                   n           EPS_p_max            SIG_max0',f20(card.a)+f20(card.b)+f20(card.n)+f20(card.epsMax)+f20(card.sigMax),
        '#                  c           EPS_DOT_0       ICC   Fsmooth               F_cut               Chard',f20(card.C)+f20(card.rate0)+i10(0)+i10(0)+f20(0)+f20(0),
        '#                  m              T_melt              rhoC_p                 T_r               T_max',f20(card.m)+f20(card.tMelt)+f20(card.rhoCp)+f20(card.tRef)+f20(0)];
    }else{
      const dp=druckerPrager(card);
      out.drucker=dp;
      out.lines=[`/MAT/DPRAG1/${id}`,name,'#              RHO_I',f20(rho),
        '#                  E                  Nu',f20(E)+f20(nu),
        '#                 A0                  A1                  A2                Amax',f20(dp.A0)+f20(dp.A1)+f20(dp.A2)+f20(0),
        '#              P_min',f20(dp.pMin)];
    }
    if(card.failure.enabled){
      out.failure=true;out.erodes=true;
      out.lines.push(`/FAIL/TENSSTRAIN/${id}`,'#         EPSILON_T1          EPSILON_T2    FCT_ID          EPSILON_F1          EPSILON_F2     S_Flag',
        f20(card.failure.strainStart)+f20(card.failure.strainEnd)+i10(0)+f20(0)+f20(0)+i10(0),
        '#   FAILIP',i10(1));
    }
    return out;
  }
  // Engine animation requests for the damage variables of a set of materials.
  function damageAnimations(materials){
    const list=[];
    if(materials.some(m=>m.damage==='damg'))list.push('/ANIM/ELEM/DAMG');
    if(materials.some(m=>m.damage==='usr3'))list.push('/ANIM/ELEM/USER3');
    if(materials.some(m=>m.failure))list.push('/ANIM/BRICK/DAMA');
    return list;
  }
  const api={MODELS,FIELDS,DEFAULTS,DAMAGE_SOURCE,normalize,validate,normalizeLibraryCard,druckerPrager,capCone,cdpm2CrackOpening,describe,fromBlastConstitutive,
    materialLines,damageAnimations,f20,i10,title};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.Blast3dCards=api;
})(typeof window!=='undefined'?window:globalThis);
