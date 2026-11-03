const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const Settings=require('../blast-settings'),Cards=require('../blast-materials'),GasEOS=require('../gas-eos');
function harness(input={},materials=[]){
  class Element{
    constructor(){this.value='';this.checked=false;this.textContent='';this.hidden=false;this.disabled=false;this.open=false;this.shows=0;this.dataset={};this.children=[];this.listeners={};this.classList={toggle(){}};}
    append(...x){this.children.push(...x);}replaceChildren(){this.children=[];}addEventListener(name,fn){(this.listeners[name]??=[]).push(fn);}showModal(){this.open=true;this.shows++;}close(){this.open=false;}
  }
  const elements=new Map(),element=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
  const c=vm.createContext({console,structuredClone,BlastSettings:Settings,BlastMaterials:Cards,GasEOS,calculationWorkflowRunning:false,
    scene:{blastSettings:Settings.normalize({}),regions:[],pointLoads:[],distributedLoads:[],bodyLoads:[]},blastStrengthMaterials:()=>materials,
    document:{getElementById:element,createElement:()=>new Element(),querySelectorAll:()=>[]},syncRegionMaterialSnapshots(){},setRegionMaterialData(){},syncBlastFractureControls(){}});
  for(const f of ['src/core/blast-dynamics.js','src/core/blast-rock-ui.js','src/core/blast-compatibility-ui.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'..',f),'utf8'),c);
  c.saved={...Settings.defaults,...input};vm.runInContext(`for(const [key,[id,scale]] of Object.entries(BLAST_FIELDS))document.getElementById(id).value=String(saved[key]/scale);document.getElementById('blastFracture').checked=saved.fracture;`,c);
  c.initializeBlastCompatibility();return {c,element};
}
test('removed solid models block Run without changing the selected settings',()=>{
 const h=harness({rockModel:8,planeMode:1,kinematics:1});const r=h.c.syncBlastCompatibility(true);assert.ok(r.errors.some(x=>x.includes('已移除')));assert.ok(h.element('startBlast').disabled);assert.equal(h.element('blastRockModel').value,'8');
 h.element('blastRockModel').value='3';assert.equal(h.c.syncBlastCompatibility().errors.length,0);assert.equal(h.element('startBlast').disabled,false);
});
test('unsupported gas EOS block Run until replaced by JWL',()=>{
 const h=harness({rockModel:3,sourceMode:1,productEOS:5,airEOS:0,jwlA:586e9,jwlB:21.6e9});assert.ok(h.c.syncBlastCompatibility().errors.some(x=>x.includes('状态方程')));
 h.element('blastProductEOS').value='1';assert.equal(h.c.syncBlastCompatibility().errors.length,0);
});
test('a valid configuration cannot re-enable Run during an active solve',()=>{
 const h=harness({rockModel:3});h.c.calculationWorkflowRunning=true;h.c.syncBlastCompatibility();assert.ok(h.element('startBlast').disabled);h.c.calculationWorkflowRunning=false;h.c.syncBlastCompatibility();assert.equal(h.element('startBlast').disabled,false);
});
test('JH2 accepts finite-deformation plane stress without changing either selection',()=>{
 const h=harness({rockModel:3,kinematics:1,planeMode:0});assert.equal(Settings.normalize({kinematics:1,planeMode:0}).planeMode,0);assert.equal(h.c.syncBlastCompatibility().errors.length,0);assert.equal(h.element('blastPlaneMode').value,'0');
});
