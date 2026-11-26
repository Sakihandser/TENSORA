"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const I18N_SOURCE = fs.readFileSync(path.join(__dirname, "..", "src", "global", "i18n.js"), "utf8");
const INDEX_SOURCE = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");

function createBrowserHarness(language = "en") {
  class ElementStub {
    constructor(tagName = "DIV") {
      this.tagName = tagName;
      this.attributes = new Map();
      this.value = "";
      this._listeners = new Map();
      this._walk = [];
    }
    hasAttribute(name) {
      return this.attributes.has(name);
    }
    getAttribute(name) {
      return this.attributes.get(name) ?? null;
    }
    setAttribute(name, value) {
      this.attributes.set(name, String(value));
    }
    addEventListener(name, listener) {
      this._listeners.set(name, listener);
    }
  }

  class InputStub extends ElementStub {}
  class CanvasStub {
    fillText(text) {
      this.lastFillText = text;
    }
    strokeText(text) {
      this.lastStrokeText = text;
    }
  }

  const pageText = { nodeType: 3, data: "结构绘制", parentElement: new ElementStub("BUTTON") };
  const titledButton = new ElementStub("BUTTON");
  titledButton.setAttribute("title", "自动划分网格");
  const selector = new ElementStub("SELECT");
  const documentElement = new ElementStub("HTML");
  documentElement._walk = [pageText, titledButton, selector];
  let observerCallback = null;
  const storage = new Map([["fem-interface-language", language]]);
  const alerts = [];
  const confirmations = [];

  class MutationObserverStub {
    constructor(callback) {
      observerCallback = callback;
    }
    observe() {}
    disconnect() {}
  }

  const context = {
    console,
    Element: ElementStub,
    HTMLInputElement: InputStub,
    CanvasRenderingContext2D: CanvasStub,
    MutationObserver: MutationObserverStub,
    CustomEvent: class CustomEventStub {
      constructor(type, options) {
        this.type = type;
        this.detail = options?.detail;
      }
    },
    Node: { TEXT_NODE: 3 },
    NodeFilter: { SHOW_ELEMENT: 1, SHOW_TEXT: 4 },
    document: {
      documentElement,
      getElementById(id) {
        return id === "interfaceLanguage" ? selector : null;
      },
      createTreeWalker(root) {
        const nodes = [...(root?._walk || [])];
        return { nextNode: () => nodes.shift() || null };
      },
    },
    window: {
      localStorage: {
        getItem: (key) => storage.get(key) ?? null,
        setItem: (key, value) => storage.set(key, String(value)),
      },
      alert: (message) => alerts.push(message),
      confirm: (message) => {
        confirmations.push(message);
        return true;
      },
      addEventListener() {},
      dispatchEvent() {},
    },
  };
  context.window.window = context.window;
  vm.runInNewContext(I18N_SOURCE, context, { filename: "i18n.js" });
  return { context, pageText, titledButton, selector, alerts, confirmations, CanvasStub, observer: () => observerCallback };
}

test("英文模式翻译静态文字、动态状态、弹窗和 Canvas 标签", () => {
  const harness = createBrowserHarness("en");
  const { window } = harness.context;
  assert.equal(harness.pageText.data, "Structure");
  assert.equal(harness.titledButton.getAttribute("title"), "Generate Mesh");
  assert.equal(window.femI18n.t("已布点 120 节点"), "120 nodes placed");
  assert.equal(window.femI18n.t("R2：外部空气"), "R2: Exterior Air");
  assert.equal(window.femI18n.t("R1 结构"), "R1 Structure");
  assert.equal(window.femI18n.t("state: 静态支撑"), "state: Fixed Support");
  assert.equal(window.femI18n.t("kind: 外部空气"), "kind: Exterior Air");
  assert.equal(window.femI18n.t("material: Q235钢"), "material: Q235 Steel");
  assert.equal(window.femI18n.t("Q235钢"), "Q235 Steel");

  window.alert("请输入材料名称。");
  window.confirm("删除材料“Steel”？");
  assert.deepEqual(harness.alerts, ["Enter a material name."]);
  assert.deepEqual(harness.confirmations, ["Delete material “Steel”?"]);

  const canvas = new harness.CanvasStub();
  canvas.fillText("应力云图", 0, 0);
  assert.equal(canvas.lastFillText, "Stress Contours");

  const dynamicText = { nodeType: 3, data: "待结果", parentElement: new harness.context.Element("SPAN") };
  harness.observer()([{ type: "characterData", target: dynamicText }]);
  assert.equal(dynamicText.data, "Awaiting Results");
});

test("语言切换可原位恢复中文并保存偏好", () => {
  const harness = createBrowserHarness("en");
  harness.context.window.femI18n.setLanguage("zh-CN", { refresh: false });
  assert.equal(harness.pageText.data, "结构绘制");
  assert.equal(harness.titledButton.getAttribute("title"), "自动划分网格");
  assert.equal(harness.context.document.documentElement.lang, "zh-CN");

  harness.context.window.femI18n.setLanguage("en", { refresh: false });
  assert.equal(harness.pageText.data, "Structure");
  assert.equal(harness.context.window.localStorage.getItem("fem-interface-language"), "en");
});

test('新版自适应节点保护与停止原因支持英文',()=>{
  const translate=createBrowserHarness('en').context.window.femI18n.translateEnglish;
  for(const value of ['自适应安全节点上限','自适应安全节点上限必须是 100–1000000 的整数。',
    '基础网格超过自适应安全节点上限，请提高该上限。',
    '自适应完成：达到奇点保护限制；ZZ 估计误差 12.53%',
    '自适应完成：误差下降停滞，已保留最后成功结果；ZZ 估计误差 10.00%',
    '自适应完成：达到自适应安全节点上限；ZZ 估计误差 5.10%']){
    assert.equal(/[\u3400-\u9fff]/u.test(translate(value)),false,value);
  }
});

test("index.html 中所有可见中文和辅助文本都有英文翻译", () => {
  const harness = createBrowserHarness("en");
  const translate = harness.context.window.femI18n.translateEnglish;
  const html = INDEX_SOURCE.replace(/<!--[\s\S]*?-->/g, "");
  const candidates = [];
  for (const match of html.matchAll(/>([^<>]+)</g)) {
    const text = match[1].trim();
    if (/[\u3400-\u9fff]/u.test(text)) candidates.push(text);
  }
  for (const match of html.matchAll(/(?:title|aria-label|placeholder|value)="([^"]*[\u3400-\u9fff][^"]*)"/gu)) {
    candidates.push(match[1]);
  }
  const untranslated = [...new Set(candidates)].filter((text) => translate(text) === text);
  assert.deepEqual(untranslated, []);
});

test("3D analysis output and backend diagnostics have English translations", () => {
  const translate = createBrowserHarness("en").context.window.femI18n.translateEnglish;
  for (const [source, english] of [
    ["网格完成：100 节点，240 四面体，1 体域，6 个 CAD 面。", "Mesh generated. Nodes 100, tetrahedra 240, volumes 1, CAD faces 6."],
    ["节点 100 · 四面体 240 · 最大位移 1.0000e-5 m · 最大 von Mises 3.0000e+6 Pa · 迭代 12",
      "Nodes 100 · Tetrahedra 240 · Max displacement 1.0000e-5 m · Max von Mises 3.0000e+6 Pa · Iterations 12"],
    ["三维网格节点数须在 4–25000 之间（当前 26000）", "A 3D mesh must have 4–25,000 nodes (received 26000)"],
    ["体域 1000 尚未指定材料", "Volume 1000 has no assigned material"],
    ["求解未收敛，残差 1.030e-3", "The solver did not converge. Residual 1.030e-3"],
    ["未找到 CAD 面 15", "CAD face 15 was not found"],
    ["未完成校核：3 个单元", "Not checked: 3 elements"],
  ]) assert.equal(translate(source), english);
});

 test("untranslated user text and attributes do not feed an observer loop when switching to Chinese",()=>{
  const h=createBrowserHarness("en"),parent=new h.context.Element("SPAN");
  let value="自定义模型XYZ",writes=0;
  const node={nodeType:3,parentElement:parent,get data(){return value;},set data(next){writes++;value=next;}};
  parent.setAttribute("title","自定义模型XYZ");let attributeWrites=0;
  const setAttribute=parent.setAttribute.bind(parent);parent.setAttribute=(name,text)=>{attributeWrites++;setAttribute(name,text);};
  h.context.document.documentElement._walk.push(node,parent);
  h.observer()([{type:"characterData",target:node},{type:"attributes",target:parent,attributeName:"title"}]);
  h.context.window.femI18n.setLanguage("zh-CN",{refresh:false});
  for(let i=0;i<10;i++)h.observer()([{type:"characterData",target:node},{type:"attributes",target:parent,attributeName:"title"}]);
  assert.equal(writes,0);assert.equal(attributeWrites,0);assert.equal(value,"自定义模型XYZ");
 });
 test("complete damage messages and backend errors use the selected language and restore their source",()=>{
  const h=createBrowserHarness("en"),i18n=h.context.window.femI18n;
  const source="损伤网格与断裂能不匹配：当前 Gf = 100 J/m²；青砂岩 / E940 要求 Gf > 235.92875 J/m²。请细化网格或检查已标定的强度、断裂能。";
  const node={nodeType:3,data:source,parentElement:new h.context.Element("OUTPUT")};
  h.context.document.documentElement._walk.push(node);h.observer()([{type:"characterData",target:node}]);
  assert.match(node.data,/Green sandstone \/ E940 requires Gf > 235.92875/);assert.doesNotMatch(node.data,/[\u3400-\u9fff]/u);
  const english=node.data;
  for(let i=0;i<10;i++){
    i18n.setLanguage("zh-CN",{refresh:false});assert.equal(node.data,source);
    i18n.setLanguage("en",{refresh:false});assert.equal(node.data,english);
  }
  assert.equal(i18n.t("完成 / 4995 步 / Δt = 0.04004 μs"),"Completed / 4995 steps / Δt = 0.04004 μs");
  assert.equal(i18n.t("花岗岩 — 单轴抗拉强度 (MPa)"),"Granite — Uniaxial tensile strength (MPa)");
  assert.equal(i18n.t("损伤网格细化：2 轮 / 70265 节点 / 139642 单元"),"Damage mesh refinement: 2 rounds / 70265 nodes / 139642 elements");
  assert.match(i18n.t("损伤网格已兼容：70265 节点 / 139642 单元；保留输入的强度与断裂能。"),/^Damage mesh compatible/);
  const error="Blast simulation failed: Requested blast dt exceeds stability or pressure-resolution limit; use dt=0.";
  i18n.setLanguage("zh-CN",{refresh:false});assert.match(i18n.t(error),/^爆破计算失败：时间步/);
  i18n.setLanguage("en",{refresh:false});assert.equal(i18n.t(error),error);
 });
 test("language changes redraw only the active page and source labels survive cloning in English",()=>{
  const h=createBrowserHarness("en"),calls=[];
  h.context.document.querySelector=()=>({dataset:{page:"blast"}});
  for(const name of ["render","renderCalculationView","renderResultView","renderMaterialLibrary","renderBlastSetup"])h.context.window[name]=()=>calls.push(name);
  h.context.window.femI18n.setLanguage("zh-CN");assert.deepEqual(calls,["renderBlastSetup"]);
  h.context.window.femI18n.setLanguage("en",{refresh:false});
  const span=new h.context.Element("SPAN");span.childNodes=[h.pageText];
  assert.equal(h.pageText.data,"Structure");assert.equal(h.context.window.femI18n.sourceText(span),"结构绘制");
 });

 test("blast backend diagnostics have Chinese text and English text",()=>{
  const h=createBrowserHarness("zh-CN"),i18n=h.context.window.femI18n,untranslated=[];
  for(const file of ["blast-runner.js","blast-frame-codec.js","explosive-library.js","gas-library.js","explosive-store.js"]){
    const code=fs.readFileSync(path.join(__dirname,"..",file),"utf8");
    for(const match of code.matchAll(/"([^"\n]+[.!])"/g)){
      const message=match[1];if(!/^[A-Z][A-Za-z0-9]/.test(message) || !message.includes(" "))continue;
      const source=i18n.sourceMessage(message);if(!/[\u3400-\u9fff]/u.test(source))untranslated.push(message);
      if(/[\u3400-\u9fff]/u.test(i18n.translateEnglish(source)))untranslated.push("English: "+source);
    }
  }
  assert.deepEqual([...new Set(untranslated)],[]);
 });
 test("all solid model names, help and parameter labels support English",()=>{
  const h=createBrowserHarness("en"),i18n=h.context.window.femI18n,cards=require('../blast-materials');
  for(const text of [...cards.names,...cards.help,...Object.values(cards.fields).flat().map(f=>f[1])])assert.doesNotMatch(i18n.translateEnglish(text),/[\u3400-\u9fff]/u,text);
 });
 test("OpenCourant card models, help, field labels and validation errors support English",()=>{
  const i18n=createBrowserHarness("en").context.window.femI18n,Cards=require('../blast3d-cards');
  const texts=[...Cards.MODELS.flatMap(m=>[m.name,m.help]),...Object.values(Cards.FIELDS).flat().map(f=>f[1]),...Cards.MODELS.map(m=>Cards.describe({model:m.id})+' · 未关联基础材料')];
  for(const raw of [{model:'rht',Q0:0.8,B:0.01,fsRatio:0.13,ftRatio:0.1},{model:'rht',N:2},{model:'rht',betaC:1},{model:'rht',gc:2},{model:'rht',pco:1},{model:'cdpm2',ft:50e6},{model:'dpcap',friction:80}]){
    try{Cards.validate(raw,'Rock A');assert.fail('expected rejection');}catch(error){texts.push(error.message);}
  }
  for(const text of texts)assert.doesNotMatch(i18n.translateEnglish(text),/[㐀-鿿]/u,text);
 });
 test("gas model names, requirements and configuration errors support English",()=>{
  const i18n=createBrowserHarness('en').context.window.femI18n,gas=require('../gas-eos'),cards=require('../blast-materials');
  for(const text of [...Object.values(gas.names),...Object.values(gas.help),...cards.compatibility({blastConstitutive:{law:8}},{planeMode:0,kinematics:0}).errors])assert.doesNotMatch(i18n.translateEnglish(text),/[\u3400-\u9fff]/u,text);
 });

test('structural dynamics labels, run information, progress and solver messages have English translations',()=>{
 const translate=createBrowserHarness('en').context.window.femI18n.translateEnglish;
 const DS=require('../dynamics-settings');
 const sandbox={window:{DynamicsSettings:DS}};sandbox.window.window=sandbox.window;
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'..','src','core','dynamics-common.js'),'utf8'),sandbox);
 const UI=sandbox.window.DynamicsUI,texts=[];
 texts.push(...DS.ANALYSES.map(a=>a.help),...Object.values(UI.FIELD_LABELS),...Object.values(UI.PHASES),...Object.values(UI.LOAD_SHAPES),...Object.values(UI.ANALYSIS_NAMES));
 const frames=[{index:0,value:83.02,mode:1,stats:{umag:[0,1],vm:[0,2]}},{index:1,value:0,mode:2,stats:{umag:[0,1],vm:[0,2]}}];
 const base={runId:'run-abc',nodeCount:10,cpuThreads:4,elapsedMs:1234,dimension:2,frames,fields:['ux','uy','umag','vm','phx'],
   meta:{nodes:10,elements:12,mass:785,elementType:'C3D15',quadratic:true,plane:'stress',sectionThickness:0.005,rigidModes:3,steps:100,parts:2,contacts:2,walls:[{id:1}],cycles:1234,
     timeStepEstimate:1e-6,minEdge:0.01,waveSpeed:5000,slabThickness:0.01,bodies:[{part:1,velocity:[5,0,0]}],
     materials:[{name:'Q235钢',label:'双线性弹塑性（σy 235.0 MPa，Et 1000 MPa）'},{name:'Q235钢',label:'线弹性'}],loadSamples:[[0,0],[1,1]],totalEffectiveMass:[700,700,700]},
   history:{kinetic:{label:'动能',x:[0,1],y:[10,5]},internal:{label:'内能（应变能 + 塑性功）',x:[0,1],y:[0,5]},wall1:{label:'刚性墙 1 法向力',unit:'N',x:[0,1],y:[0,1]}},
   modes:[{mode:1,frequency:83.02,period:0.012,rigid:false,effectiveMass:[0,481,0]},{mode:2,frequency:0,rigid:true,effectiveMass:[0,0,0]}],
   termination:{message:'CalculiX 提前停止，只保留到 t = 0.01 s 的结果。'}};
 for(const analysis of ['modal','harmonic','transient','explicit']){
   const summary={...base,analysis,solver:analysis==='explicit'?'OpenCourant 20261011 显式动力学':'CalculiX 2.22',settings:{...DS.DEFAULTS,analysis,load:{shape:'halfsine'}}};
   texts.push(...UI.runInfo(summary).split('\n'),UI.frameLabel(summary,0),UI.frameLabel(summary,1),UI.axisLabel(summary));
   for(const curve of UI.curves(summary))texts.push(curve.label,...(curve.multi||[]).map(s=>s.label));
   for(const key of summary.fields)texts.push(UI.fieldLabel(summary,key));
   texts.push(UI.progressText({phase:'engine',time:1e-4,dt:1e-7,cycle:1200,elapsedMs:2000},summary.settings),UI.progressText({phase:'solving',elapsedMs:500},summary.settings));
 }
 for(const raw of [{analysis:'harmonic',freqMin:10,freqMax:5},{analysis:'transient',timeStep:0},{analysis:'transient',frames:1},{analysis:'explicit',walls:[{normal:[0,0,0]}]},
   {analysis:'explicit',timeStepScale:2},{analysis:'transient',load:{shape:'table',table:[[0,0]]}},{analysis:'modal',modes:0},{analysis:'explicit',bodies:{1:{velocity:['x']}}}]){
   try{DS.normalize(raw);assert.fail('expected rejection');}catch(error){texts.push(error.message);}
 }
 texts.push('模态分析完成 · 10 个结果帧 · 用时 1.2 s','模态 1 · 83.02 Hz · 振型位移 |φ|（质量归一化） 1.390e-8 至 0.07124 m · 变形显示 1.4×','部件 1 · 238 节点 · 中心 (0, 0.1, 0) m',
   '12 节点 · 中心 (0.1, 0.2) m','Q235钢 · E 200 GPa · ρ 7850 kg/m³','关联爆破材料卡：Q235钢','节点 12 · (0.1, 0.2) m · 位移量 |u|','CalculiX 2.22 隐式动力学 · OpenCourant 显式碰撞（未找到运行时）',
   '网格包含 2 个互不相连的部件；隐式分析中各部件独立振动，未约束的部件会出现刚体模态。','steel：动力学计算需要材料密度。','刚性墙 1 穿过模型（3 个节点在墙后），请调整墙的位置。',
   '模型有 13 个独立部件，超过自动接触上限 12；请合并部件或关闭部件间接触。','t = 0.001 s 起结果发散（单元翻转或时间步过小）。','OpenCourant Engine 在 t = 0.001 s 提前停止（通常为单元严重畸变），只保留此前结果帧。',
   'X 向质量占比','Y 向累计','刚性墙 1 法向力–时间','vx (m/s)','点 X (m)','t = 3.000e-4 s · 最大位移 0.0015 m · 最大 von Mises 4.229e+6 Pa');
 const Rules=require('../calculation-rules');
 for(const f of Rules.checkDynamics({dimension:2,analysis:'explicit',settings:{gravity:[0,0,0],walls:[]},materials:[{name:'A',density:0,elasticModulus:0}],unassigned:1,restraints:false,loads:0,parts:20,velocities:[],mesh:false}))
   assert.doesNotMatch(f.en,/[㐀-鿿]/u,f.en);
 for(const text of texts)assert.doesNotMatch(translate(text),/[㐀-鿿]/u,text);
});

test('deformation controls, material validation and dynamic statuses have complete English translations',()=>{
 const translate=createBrowserHarness('en').context.window.femI18n.translateEnglish;
 const messages=['求解完成 · 40 个增量 · run-example','网格就绪：60 节点 / 100 单元','Model · CalculiX · 载荷比例 1.0000 · 节点峰值 1.0000e-2 m · 变形显示 1×','CalculiX 计算失败：solver stopped'];
 messages.push('已完成 12 个增量 · 已用 5 s · 预计剩余约 15 s','已完成 0 个增量 · 已用 1 s · 正在估算剩余时间…','已完成 40 个增量 · 已用 20 s','正在准备计算','正在求解','正在整理结果','计算完成','计算失败');
 const {diagnoseDeformationStop}=require('../deformation-runner');messages.push(diagnoseDeformationStop('*ERROR in nonlingeo: max. # of increments reached').message,diagnoseDeformationStop('*ERROR: increment size smaller than minimum').message,'未完成目标载荷（可查看已收敛过程）','暂停回放');
 for(const file of ['deformation-settings.js','deformation-runner.js','fracture-runner.js']){const source=fs.readFileSync(path.join(__dirname,'..',file),'utf8');for(const match of source.matchAll(/(?:Error|stop)\('([^']+)'\)/g))messages.push(match[1]);}
 for(const message of messages)assert.doesNotMatch(translate(message),/[\u3400-\u9fff]/,message);
});
