// Structural dynamics settings shared by the browser (window.DynamicsSettings) and
// Node. Only input normalization, defaults and model bookkeeping live here; every
// dynamic solution is computed by the bundled CalculiX (modal, harmonic, implicit
// transient) or OpenCourant (explicit impact) executables.
(function(root){
  'use strict';
  const ANALYSES=[
    {id:'modal',solver:'calculix',name:'模态分析 · CalculiX *FREQUENCY',
      help:'求解结构固有频率、振型、参与因子与有效质量（Lanczos / ARPACK）。不需要外载荷；约束不足（自由–自由）时自动多求刚体模态并单独标注。'},
    {id:'harmonic',solver:'calculix',name:'谐响应（机械振动）· CalculiX *STEADY STATE DYNAMICS',
      help:'在模态基础上做稳态简谐响应：模型中的载荷作为简谐力幅值，按频率扫描给出位移幅值、相位和应力幅值，以及频响曲线。'},
    {id:'transient',solver:'calculix',name:'瞬态动力学（隐式）· CalculiX *MODAL DYNAMIC / *DYNAMIC',
      help:'模态叠加法（快速，线性结构）或直接积分（α 法，无条件稳定）。模型载荷按选定时程变化，可设瑞利阻尼，适合冲击载荷、启停与强迫振动的时域响应。'},
    {id:'explicit',solver:'opencourant',name:'显式动力学（碰撞冲击）· OpenCourant',
      help:'中心差分显式积分。各部件可设初速度，部件之间自动接触，可加刚性墙与重力，材料可为线弹性、双线性弹塑性或关联的 OpenCourant 本构卡。适合小球对撞、汽车撞墙、跌落等高速冲击。'}
  ];
  const ANALYSIS_IDS=ANALYSES.map(a=>a.id);
  const LOAD_SHAPES=['step','ramp','sine','halfsine','pulse','table'];
  const DEFAULTS={
    analysis:'modal',planeMode:0,elementOrder:'quadratic',threads:0,
    // modal
    modes:10,
    // harmonic
    freqMin:1,freqMax:500,freqPoints:20,dampingRatio:0.02,harmonicModes:20,
    // transient (implicit): mode superposition (fast, linear) or direct integration
    transientMethod:'modal',transientModes:30,endTime:0.1,timeStep:0.0005,frames:41,rayleighAlpha:0,rayleighBeta:0,
    load:{shape:'step',factor:1,frequency:50,duration:0.01,rise:0.001,table:[[0,0],[0.01,1],[0.02,0]]},
    // explicit
    explicitEndTime:0.005,explicitFrames:51,timeStepScale:0.67,minTimeStep:0,gravity:[0,0,0],
    explicitLoads:false,contact:true,selfContact:false,friction:0.1,
    bodies:{},cards:{},walls:[]
  };
  const LIMITS={nodes:200000,elements:400000,modes:200,freqPoints:200,frames:401,explicitFrames:201,steps:200000};
  const finite=(value,name)=>{const n=Number(value);if(!Number.isFinite(n))throw new Error(`${name} 必须为有限数值`);return n;};
  const positive=(value,name)=>{const n=finite(value,name);if(!(n>0))throw new Error(`${name} 必须大于零`);return n;};
  const integer=(value,name,min,max)=>{const n=Math.round(finite(value,name));if(n<min||n>max)throw new Error(`${name} 须在 ${min}–${max} 之间`);return n;};
  const vector=(value,name,fallback=[0,0,0])=>{
    const v=Array.isArray(value)?value:fallback;
    return [0,1,2].map(i=>finite(v[i]??0,`${name} ${'XYZ'[i]}`));
  };
  function normalizeLoad(raw={}){
    const d=DEFAULTS.load;
    const shape=LOAD_SHAPES.includes(raw.shape)?raw.shape:d.shape;
    const load={shape,factor:finite(raw.factor??d.factor,'载荷系数'),
      frequency:finite(raw.frequency??d.frequency,'激励频率'),duration:finite(raw.duration??d.duration,'持续时间'),rise:finite(raw.rise??d.rise,'上升时间')};
    if(shape==='sine'&&!(load.frequency>0))throw new Error('正弦载荷的激励频率必须大于零');
    if(['halfsine','pulse','ramp'].includes(shape)&&!(load.duration>0))throw new Error('载荷持续时间必须大于零');
    if(shape==='pulse'&&!(load.rise>0&&load.rise<load.duration))throw new Error('矩形脉冲的上升时间须大于零并小于持续时间');
    if(shape==='table'){
      const rows=(Array.isArray(raw.table)?raw.table:d.table).map(r=>[finite(r?.[0],'时程表时间'),finite(r?.[1],'时程表系数')]);
      if(rows.length<2)throw new Error('载荷时程表至少需要两行');
      for(let i=1;i<rows.length;i++)if(!(rows[i][0]>rows[i-1][0]))throw new Error('载荷时程表的时间须严格递增');
      load.table=rows;
    }
    return load;
  }
  // Multiplier of the model loads at time t (same rule as the cards written for the solvers).
  function loadValue(load,t){
    const f=load.factor;
    switch(load.shape){
      case 'step':return t>=0?f:0;
      case 'ramp':return f*Math.min(1,Math.max(0,t/load.duration));
      case 'sine':return f*Math.sin(2*Math.PI*load.frequency*t);
      case 'halfsine':return t<=load.duration?f*Math.sin(Math.PI*t/load.duration):0;
      case 'pulse':{
        const r=load.rise,D=load.duration;
        if(t<r)return f*t/r;
        if(t<=D-r)return f;
        if(t<D)return f*(D-t)/r;
        return 0;
      }
      case 'table':{
        const rows=load.table;
        if(t<=rows[0][0])return f*rows[0][1];
        for(let i=1;i<rows.length;i++)if(t<=rows[i][0]){
          const [t0,v0]=rows[i-1],[t1,v1]=rows[i];
          return f*(v0+(v1-v0)*(t-t0)/(t1-t0));
        }
        return f*rows.at(-1)[1];
      }
      default:return 0;
    }
  }
  // Piecewise-linear samples of the load history over [0, end] (for *AMPLITUDE and /FUNCT).
  function loadSamples(load,end){
    const points=new Set([0,end]);
    if(load.shape==='step')points.add(0);
    if(load.shape==='ramp')points.add(Math.min(end,load.duration));
    if(load.shape==='table')for(const [t] of load.table)if(t>=0&&t<=end)points.add(t);
    if(load.shape==='pulse')for(const t of [load.rise,load.duration-load.rise,load.duration])if(t<=end)points.add(t);
    if(load.shape==='sine'){
      const n=Math.min(20000,Math.ceil(end*load.frequency*32)+1);
      for(let i=0;i<=n;i++)points.add(end*i/n);
    }
    if(load.shape==='halfsine'){
      const T=Math.min(end,load.duration);
      for(let i=0;i<=32;i++)points.add(T*i/32);
      if(load.duration<end)points.add(Math.min(end,load.duration*1.000001));
    }
    return [...points].sort((a,b)=>a-b).map(t=>[t,loadValue(load,t)]);
  }
  function normalizeBody(raw={}){
    return {velocity:vector(raw.velocity,'初速度')};
  }
  // Constitutive card of a base material for explicit runs.
  function normalizeCard(raw={}){
    const model=['elastic','plastic','linked'].includes(raw.model)?raw.model:'elastic';
    const card={model};
    if(model==='plastic'){
      card.yieldStress=positive(raw.yieldStress??235e6,'屈服应力');
      card.tangentModulus=finite(raw.tangentModulus??1e9,'切线模量');
      if(card.tangentModulus<0)throw new Error('切线模量不能为负');
      card.failureStrain=finite(raw.failureStrain??0,'失效塑性应变');
      if(card.failureStrain<0)throw new Error('失效塑性应变不能为负');
    }
    // A linked card is an OpenCourant card of the shared registry (blast3d-cards.js),
    // resolved in the browser from the material binding and validated when written.
    if(model==='linked'){
      if(!raw.card||typeof raw.card!=='object')throw new Error('关联的 OpenCourant 材料卡缺失');
      card.card=raw.card;card.name=String(raw.name||'');
    }
    return card;
  }
  function normalizeWall(raw={}){
    const point=vector(raw.point,'刚性墙位置');
    const normal=vector(raw.normal,'刚性墙法向',[1,0,0]);
    const length=Math.hypot(...normal);
    if(!(length>0))throw new Error('刚性墙法向不能为零向量');
    const friction=finite(raw.friction??0,'刚性墙摩擦系数');
    if(friction<0)throw new Error('刚性墙摩擦系数不能为负');
    return {point,normal:normal.map(v=>v/length),friction};
  }
  function normalize(raw={}){
    const s={...DEFAULTS,...(raw&&typeof raw==='object'?raw:{})};
    s.analysis=ANALYSIS_IDS.includes(s.analysis)?s.analysis:'modal';
    s.planeMode=Number(s.planeMode)===1?1:0;
    s.elementOrder=s.elementOrder==='linear'?'linear':'quadratic';
    s.threads=integer(s.threads??0,'CPU 线程数',0,64);
    if(s.analysis==='modal')s.modes=integer(s.modes,'模态阶数',1,LIMITS.modes);
    if(s.analysis==='harmonic'){
      s.freqMin=positive(s.freqMin,'扫频起点');
      s.freqMax=positive(s.freqMax,'扫频终点');
      if(s.freqMax<=s.freqMin)throw new Error('扫频终点须大于起点');
      s.freqPoints=integer(s.freqPoints,'每段频率点数',2,LIMITS.freqPoints);
      s.dampingRatio=finite(s.dampingRatio,'阻尼比');
      if(s.dampingRatio<0||s.dampingRatio>=1)throw new Error('阻尼比须在 0–1 之间');
      s.harmonicModes=integer(s.harmonicModes,'参与叠加的模态数',1,LIMITS.modes);
    }
    if(s.analysis==='transient'){
      s.transientMethod=s.transientMethod==='direct'?'direct':'modal';
      s.transientModes=integer(s.transientModes??30,'参与叠加的模态数',1,LIMITS.modes);
      s.endTime=positive(s.endTime,'计算时长');
      s.timeStep=positive(s.timeStep,'时间步长');
      if(s.endTime/s.timeStep>LIMITS.steps)throw new Error(`时间步数超过 ${LIMITS.steps.toLocaleString()}，请增大时间步长`);
      if(s.timeStep>s.endTime)throw new Error('时间步长不能大于计算时长');
      s.frames=integer(s.frames,'保存帧数',2,LIMITS.frames);
      s.rayleighAlpha=finite(s.rayleighAlpha,'瑞利阻尼 α');
      s.rayleighBeta=finite(s.rayleighBeta,'瑞利阻尼 β');
      if(s.rayleighAlpha<0||s.rayleighBeta<0)throw new Error('瑞利阻尼系数不能为负');
      s.load=normalizeLoad(s.load);
    }
    if(s.analysis==='explicit'){
      s.explicitEndTime=positive(s.explicitEndTime,'计算时长');
      if(s.explicitEndTime>10)throw new Error('显式计算时长不能超过 10 s');
      s.explicitFrames=integer(s.explicitFrames,'保存帧数',2,LIMITS.explicitFrames);
      s.timeStepScale=finite(s.timeStepScale,'时间步安全系数');
      if(!(s.timeStepScale>0&&s.timeStepScale<=0.9))throw new Error('时间步安全系数须在 0–0.9 之间');
      // Nodal mass scaling: 0 keeps the true mass; otherwise mass is added where the stable step is below this value.
      s.minTimeStep=finite(s.minTimeStep??0,'最小时间步');
      if(s.minTimeStep<0)throw new Error('最小时间步不能为负');
      if(s.minTimeStep>=s.explicitEndTime)throw new Error('最小时间步须小于计算时长');
      s.gravity=vector(s.gravity,'重力加速度');
      s.explicitLoads=s.explicitLoads===true;
      s.contact=s.contact!==false;
      s.selfContact=s.selfContact===true;
      s.friction=finite(s.friction,'接触摩擦系数');
      if(s.friction<0)throw new Error('接触摩擦系数不能为负');
      s.load=normalizeLoad(s.load);
      const bodies={};for(const [key,value] of Object.entries(s.bodies&&typeof s.bodies==='object'?s.bodies:{}))bodies[String(key)]=normalizeBody(value);
      s.bodies=bodies;
      const cards={};for(const [key,value] of Object.entries(s.cards&&typeof s.cards==='object'?s.cards:{}))cards[String(key)]=normalizeCard(value);
      s.cards=cards;
      s.walls=(Array.isArray(s.walls)?s.walls:[]).map(normalizeWall);
      if(s.walls.length>8)throw new Error('刚性墙最多 8 个');
    }
    return s;
  }
  // Rayleigh coefficients giving damping ratio zeta at two frequencies (Hz).
  function rayleighFromRatio(zeta,f1,f2){
    const w1=2*Math.PI*f1,w2=2*Math.PI*f2;
    if(!(zeta>=0)||!(w1>0)||!(w2>w1))throw new Error('需要阻尼比 ≥ 0 和两个递增的正频率');
    return {alpha:2*zeta*w1*w2/(w1+w2),beta:2*zeta/(w1+w2)};
  }
  // Connected components of an element list ("parts" of an impact model). Elements are
  // node index arrays (0-based). Parts are numbered by their smallest node index so the
  // browser and the server agree on the order.
  function components(elements,nodeCount){
    const parent=new Int32Array(nodeCount);for(let i=0;i<nodeCount;i++)parent[i]=i;
    const find=i=>{while(parent[i]!==i){parent[i]=parent[parent[i]];i=parent[i];}return i;};
    for(const e of elements)for(let k=1;k<e.length;k++){const a=find(e[0]),b=find(e[k]);if(a!==b)parent[Math.max(a,b)]=Math.min(a,b);}
    const label=new Map(),nodePart=new Int32Array(nodeCount).fill(-1);
    const roots=[];
    for(const e of elements)for(const n of e){const r=find(n);if(!label.has(r)){label.set(r,-1);roots.push(r);}}
    roots.sort((a,b)=>a-b).forEach((r,i)=>label.set(r,i));
    for(const e of elements)for(const n of e)nodePart[n]=label.get(find(n));
    const elementPart=elements.map(e=>label.get(find(e[0])));
    return {count:roots.length,elementPart,nodePart};
  }
  const api={ANALYSES,ANALYSIS_IDS,LOAD_SHAPES,DEFAULTS,LIMITS,normalize,normalizeLoad,normalizeBody,normalizeCard,normalizeWall,
    loadValue,loadSamples,rayleighFromRatio,components};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.DynamicsSettings=api;
})(typeof window!=='undefined'?window:globalThis);
