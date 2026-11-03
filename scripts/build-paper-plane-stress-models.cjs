'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{spawn}=require('node:child_process'),{createHash}=require('node:crypto');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'C:/Users/hongm/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..'),dest=path.resolve(root,'..'),cache=path.join(root,'tmp/paper-plane-stress');fs.mkdirSync(cache,{recursive:true});
const Settings=require('../blast-settings');
const sha=b=>createHash('sha256').update(b).digest('hex');
function material(soft){return {id:soft?'paper-20261103-sandstone':'paper-20261103-granite',name:soft?'青砂岩（试验Ed/ν；论文JH2）':'花岗岩（试验Ed/ν；论文JH2）',elasticModulus:soft?18.71:64.33,poissonRatio:soft?.19:.25,density:soft?2340:2660,yieldStrength:null,tensileStrength:null,compressiveStrength:null,fractureEnergy:soft?82.51:519.7,strengthCriterion:1,color:soft?'#dfeacb':'#92c9ca',notes:'试验动态弹性参数：'+(soft?'表4.0.1 Ed=18.71 GPa, ν=0.19。':'表2.2.3 Ed=64.33 GPa, ν=0.25。')+'爆破JH2直接使用论文数值表的G、K1与显式σHEL，通用Ed/ν不覆盖JH2切线。T为静水拉伸强度，不充当单轴抗拉强度。未给单轴强度留空。',blastConstitutive:{law:3,jh2:{A:.76,N:.62,B:.25,M:.62,C:.005,rate0:1,HEL:6.7e9,pHEL:3.7e9,T:soft?44e6:54e6,D1:.005,D2:.7,maxStrength:.25,K1:25.7e9,K2:-4500e9,K3:300000e9,beta:1,referenceLength:0,normalizationStress:4.5e9,G:soft?9.98e9:21.9e9,K:soft?12.67e9:25.7e9}}};}
function make(kind){
 const s={version:6,name:`论文-${kind}-平面应力`,staticPlaneMode:0,geometryNodes:[],curves:[],regions:[],pointLoads:[],distributedLoads:[],bodyLoads:[],analysisNodes:[],mesh:{elements:[],metadata:null}};
 const node=(x,y)=>{const id='G'+(s.geometryNodes.length+1);s.geometryNodes.push({id,x,y,mechanicalState:'free'});return id;};
 const curve=(a,b,through)=>{const id='C'+(s.curves.length+1);s.curves.push({id,type:through?'arc':'line',geometryNodeIds:[a,b],controls:through?[through]:[],mechanicalState:'free'});return id;};
 const polygon=pts=>{const ids=pts.map(p=>node(...p));return ids.map((id,i)=>curve(id,ids[(i+1)%ids.length]));};
 s.regions.push({id:'R1',name:'花岗岩基体',regionKind:'structure',boundaryCurveIds:polygon([[-.3,-.3],[.3,-.3],[.3,.3],[-.3,.3]]),material:material(false)});
 if(kind==='W45'){
  const a=[Math.SQRT1_2,-Math.SQRT1_2],n=[Math.SQRT1_2,Math.SQRT1_2],r=.027,L=.15;
  const point=(u,v)=>({x:u*a[0]+v*n[0],y:u*a[1]+v*n[1]});
  const pts=[point(-L,r),point(L,r),point(L,-r),point(-L,-r)],ids=pts.map(p=>node(p.x,p.y));
  const curves=[curve(ids[0],ids[1]),curve(ids[1],ids[2],point(L+r,0)),curve(ids[2],ids[3]),curve(ids[3],ids[0],point(-L-r,0))];
  s.regions.push({id:'R2',name:'青砂岩弱夹层（W45）',regionKind:'structure',boundaryCurveIds:curves,material:material(true)});
 }
 const circle=[];for(let i=0;i<4;i++)circle.push(node(.008*Math.cos(i*Math.PI/2),.008*Math.sin(i*Math.PI/2)));
 s.regions.push({id:kind==='W45'?'R3':'R2',name:'炮孔（外部空气；装药由气体求解器设置）',regionKind:'air',boundaryCurveIds:circle.map((id,i)=>curve(id,circle[(i+1)%4],{x:.008*Math.cos((i+.5)*Math.PI/2),y:.008*Math.sin((i+.5)*Math.PI/2)}))});
 s.blastSettings=Settings.normalize({sourceMode:1,rockModel:3,kinematics:1,planeMode:0,radius:.008,chargeRadius:.005,x:0,y:0,productEOS:1,productDensity:1200,productEnergy:3.99e6,detonationVelocity:4300,jwlA:209.7e9,jwlB:3.5e9,jwlR1:5.8,jwlR2:1.3,jwlOmega:.39,airEOS:0,airDensity:1.225,airPressure:1e5,airGamma:1.4,specimenThickness:.05,ventEnds:0,boundary:2,loadMode:0,confineX:0,confineY:0,duration:.00012,frames:61,gasCells:192,dt:0,shockViscosity:0,gf:519.7,fracture:true,gasFracture:0,timeLimitSeconds:7200});
 return s;
}
async function main(){
 const server=spawn(process.execPath,['server.js'],{cwd:root,env:{...process.env,PORT:'5303',FEM_OPEN_BROWSER:'0'},windowsHide:true});let browser;
 try{
  await new Promise((resolve,reject)=>{server.stdout.on('data',b=>{if(b.toString().includes('5303'))resolve();});server.once('error',reject);server.once('exit',c=>reject(Error('server exit '+c)));});
  browser=await chromium.launch({channel:'msedge',headless:true});const page=await browser.newPage({viewport:{width:1600,height:1100}});page.on('pageerror',e=>console.error('PAGE',e.message));
  await page.goto('http://127.0.0.1:5303');await page.waitForFunction(()=>window.femSketchApi&&typeof materialLibrary!=='undefined');
  const records=[];
  for(const kind of ['均质板','W45']){
   const raw=make(kind);await page.evaluate(data=>{setBlastModuleEnabled(true,false);scene=normalizeScene(data);modelName.value=scene.name;rebuildDerivedRegions({markAnalysisNodePlacementStale:false,markAnalysisMeshStale:false});restoreBlastControls();setPage('calculation');},raw);
   console.log('MESH_START',kind);
   const meshed=await page.evaluate(async()=>{const m=await autoGenerateAnalysisMesh({adaptive:false,regenerateNodes:true,maxNodes:30000,spacing:.0044,minAngle:25,maxArea:9e-6});return {nodes:m.analysisNodes.length,elements:m.elements.length,regions:scene.regions.map(r=>({id:r.id,name:r.name,area:r.area,isAir:r.isAir,materialId:r.materialId})),warnings:m.warnings};});
   console.log('MESH_DONE',kind,JSON.stringify(meshed));assert.ok(meshed.elements>=30000&&meshed.elements<=60000);
   for(const stress of [0,20]){
    const name=`论文-${kind}-平面应力-${stress}-${stress}`;
    const bundle=JSON.parse(await page.evaluate(({stress,name})=>{scene.name=name;modelName.value=name;scene.blastSettings.confineX=scene.blastSettings.confineY=stress*1e6;restoreBlastControls();updatePanel();const payload=buildCalculationInputExport({adaptive:false});const direct=calculationInputPayloadToDirectModel(payload);for(const m of direct.materials)BlastMaterials.validate(m,scene.blastSettings);direct.blastBoundaryEdges=blastBoundaryEdges(payload,direct);const saved={...scene,analysisNodes:scene.analysisNodes.map(n=>({id:n.id,x:n.x,y:n.y,mechanicalState:n.mechanicalState,regionId:n.regionId,materialId:n.materialId,placement:n.placement,dof:n.dof})),mesh:{...scene.mesh,elements:scene.mesh.elements.map(e=>({id:e.id,type:e.type,analysisNodeIds:e.analysisNodeIds,area:e.area,signedArea:e.signedArea,centroid:e.centroid,regionId:e.regionId,structureRegionId:e.structureRegionId,materialId:e.materialId,edges:e.edges,boundaryCurveIds:e.boundaryCurveIds,quality:e.quality,generation:e.generation}))},viewport:{offsetX:800,offsetY:550,scale:1200},calculationViewport:{offsetX:680,offsetY:500,scale:1200}};return JSON.stringify({scene:saved,direct});},{stress,name}));
    assert.equal(bundle.direct.planeMode,0);assert.equal(bundle.scene.blastSettings.planeMode,0);
    bundle.scene.paperModelProvenance={createdAt:new Date().toISOString(),sourcePdf:'C:/Users/hongm/OneDrive/Desktop/pack260929/基于物质点法的高地应力环境非均质岩石爆破响应及破岩调控-终稿 .pdf',section:kind==='W45'?'4.3 / 4.1':'2.3.2',physicalThicknessM:.05,experimentalExplosive:'乳化炸药',explosiveParameterReference:'Emulsion #2, Xia et al. 2020 Table 2, DOI 10.1155/2020/8194801; actual experimental brand not reported',plasticTubeOuterDiameterM:.011,plasticTubeModeled:false,interfaceGroutModeled:false,notes:'乳化炸药牌号及EOS未报告，按用户追加要求采用文献整套2号乳化炸药JWL参数（非PETN）。管壁/过渡层缺少厚度和本构参数，按论文数值模型省略。轴向泄流无参数，采用二维数值模型无轴向流动假设；50mm为试验厚度及有效孔长。材料G/K直接传入JH2；通用E/ν取实测值。'};
    const file=path.join(dest,name+'.json'),bytes=Buffer.from(JSON.stringify(bundle.scene));assert.ok(!fs.existsSync(file),'Refuse overwrite '+file);fs.writeFileSync(file,bytes);
    fs.writeFileSync(path.join(cache,name+'-direct.json'),JSON.stringify(bundle.direct));fs.writeFileSync(path.join(cache,name+'-settings.json'),JSON.stringify(bundle.scene.blastSettings));
    records.push({name,file,sha256:sha(bytes),...meshed,settings:bundle.scene.blastSettings,materials:bundle.direct.materials});console.log('SAVED',name,bytes.length);
   }
   await page.evaluate(()=>{fitCalculationViewToScene();renderCalculationView();});await page.screenshot({path:path.join(cache,kind+'-mesh.png')});
   await page.evaluate(()=>{setPage('blast');renderBlastSetup();});await page.screenshot({path:path.join(cache,kind+'-blast.png'),fullPage:true});
  }
  fs.writeFileSync(path.join(cache,'build-audit.json'),JSON.stringify({records},null,2));
 }finally{if(browser)await browser.close();server.kill();}
}
main().catch(e=>{console.error(e);process.exitCode=1});
