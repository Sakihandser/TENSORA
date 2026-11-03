'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{createHash}=require('node:crypto');
const root=path.resolve(__dirname,'..'),dest=path.resolve(root,'..'),cache=path.join(root,'tmp/paper-plane-stress');
const {runBlastCore}=require('../server'),{readBlastFrame,removeRun}=require('../blast-runner'),Cards=require('../blast-materials'),Settings=require('../blast-settings');
const hash=b=>createHash('sha256').update(b).digest('hex');
async function main(){const audit={createdAt:new Date().toISOString(),records:[]};
 for(const kind of ['均质板','W45'])for(const pressure of [0,20]){
  const name=`论文-${kind}-平面应力-${pressure}-${pressure}`,file=path.join(dest,name+'.json'),raw=fs.readFileSync(file),s=JSON.parse(raw),d=JSON.parse(fs.readFileSync(path.join(cache,name+'-direct.json'))),settings=Settings.normalize(s.blastSettings);
  assert.equal(s.staticPlaneMode,0);assert.equal(settings.planeMode,0);assert.equal(settings.kinematics,1);assert.equal(settings.specimenThickness,.05);assert.equal(settings.confineX,pressure*1e6);assert.equal(settings.confineY,pressure*1e6);assert.equal(settings.boundary,2);assert.equal(settings.loadMode,0);assert.equal(settings.ventEnds,0);assert.equal(settings.shockViscosity,0);assert.equal(settings.gf,519.7);assert.equal(settings.radius,.008);assert.equal(settings.chargeRadius,.005);
  for(const [k,v]of Object.entries({productEOS:1,productDensity:1200,productEnergy:3.99e6,detonationVelocity:4300,jwlA:209.7e9,jwlB:3.5e9,jwlR1:5.8,jwlR2:1.3,jwlOmega:.39,airDensity:1.225,airPressure:1e5,airGamma:1.4}))assert.equal(settings[k],v,k);
  assert.ok(d.elements.length>=30000&&d.elements.length<=60000);assert.equal(s.mesh.elements.length,d.elements.length);assert.equal(d.materials.length,kind==='W45'?2:1);
  for(const m of d.materials){Cards.validate(m,settings);const j=m.blastConstitutive.jh2,soft=m.density===2340;assert.equal(m.fractureEnergy,soft?82.51:519.7);assert.ok(soft||m.density===2660);for(const[k,v]of Object.entries({A:.76,N:.62,B:.25,M:.62,C:.005,rate0:1,HEL:6.7e9,pHEL:3.7e9,T:soft?44e6:54e6,D1:.005,D2:.7,maxStrength:.25,K1:25.7e9,K2:-4500e9,K3:300000e9,beta:1,referenceLength:0,normalizationStress:4.5e9,G:soft?9.98e9:21.9e9,K:soft?12.67e9:25.7e9}))assert.equal(j[k],v,k);assert.equal(m.elasticModulus,(soft?18.71:64.33)*1e9);assert.equal(m.poissonRatio,soft?.19:.25);}
  const nodeByNo=new Map(d.nodes.map(n=>[n.nodeNo,n])),edges=new Map(),areas={};let totalArea=0,minArea=Infinity,orientation=0,materialErrors=0;const seen=new Set();
  for(const e of d.elements){const refs=[e.node1,e.node2,e.node3],nodes=refs.map(id=>nodeByNo.get(id));assert.ok(nodes.every(Boolean));const [a,b,c]=nodes,area=((b.x-a.x)*(c.y-a.y)-(c.x-a.x)*(b.y-a.y))/2;assert.ok(area>0);assert.ok(Math.abs(area-e.area)<1e-12);totalArea+=area;minArea=Math.min(minArea,area);const key=[...refs].sort((a,b)=>a-b).join(',');assert.ok(!seen.has(key));seen.add(key);for(let k=0;k<3;k++){const key=[refs[k],refs[(k+1)%3]].sort((a,b)=>a-b).join(',');edges.set(key,(edges.get(key)||0)+1);}
   const x=(a.x+b.x+c.x)/3,y=(a.y+b.y+c.y)/3,u=(x-y)/Math.SQRT2,v=(x+y)/Math.SQRT2,inside=Math.hypot(Math.max(0,Math.abs(u)-.15),v)<.027;
   const m=d.materials.find(m=>m.materialNo===e.materialNo);if(kind==='W45'&&inside!==(m.density===2340))materialErrors++;areas[m.name]=(areas[m.name]||0)+area;
  }
  assert.equal(materialErrors,0);assert.ok([...edges.values()].every(v=>v===1||v===2));assert.ok(Math.abs(totalArea-(.36-Math.PI*.008**2))<1e-5);
  const cavityEdges=[...edges].filter(([key,count])=>count===1&&key.split(',').every(id=>Math.abs(Math.hypot(nodeByNo.get(+id).x,nodeByNo.get(+id).y)-.008)<1e-6));assert.ok(cavityEdges.length>=12);
  console.log('SMOKE_START',name,d.nodes.length,d.elements.length);let h;const start=Date.now();
  try{h=await runBlastCore(d,{...settings,duration:2e-6,frames:2,gasCells:settings.gasCells},{lazy:true});const first=await readBlastFrame(h.id,0),last=await readBlastFrame(h.id,1);assert.equal(h.planeMode,0);assert.equal(h.kinematics,1);assert.ok(h.preloadResidual<1e-6);assert.ok(last.elements.every(e=>e.every(Number.isFinite)));assert.ok(last.u.every(Number.isFinite));for(const e of last.elements)assert.ok(Math.abs(e[7])<1e-6*Math.max(1e6,...e.slice(3,6).map(Math.abs)));
   const record={name,file,sha256:hash(raw),nodes:d.nodes.length,elements:d.elements.length,mesh:{totalArea,minArea,cavityEdges:cavityEdges.length,materialAreas:areas,nonManifoldEdges:0,duplicateElements:0,materialErrors},parametersVerified:true,smoke:{duration:2e-6,gasCells:settings.gasCells,deliveredGasCells:settings.gasCells,configuredDuration:settings.duration,seconds:(Date.now()-start)/1000,preloadResidual:h.preloadResidual,initialKineticEnergy:first.kineticEnergy,allFinite:true,planeStress:true,jh2BackendCommit:h.jh2BackendCommit,gasBackendCommit:h.gasBackendCommit}};audit.records.push(record);console.log('SMOKE_DONE',name,JSON.stringify(record.smoke));fs.writeFileSync(path.join(cache,'verification-audit.json'),JSON.stringify(audit,null,2));
  }finally{if(h)await removeRun(h.id);}
 }
}
main().catch(e=>{console.error(e);process.exitCode=1});
