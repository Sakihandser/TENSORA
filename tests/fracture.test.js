'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {prepareFracture,runFracture}=require('../fracture-runner'),{fracturePatch,fractureSettings}=require('./helpers/fracture-patch');
test('downloaded PhAST sources match pinned GitHub commit and hashes',()=>{
 const root=path.resolve(__dirname,'../third_party/phast'),manifest=JSON.parse(fs.readFileSync(path.join(root,'manifest.json')));assert.equal(manifest.commit,'086b899ffbba1a52bcbec139a2a567e3bf93da56');
 for(const f of manifest.files)assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,f.file))).digest('hex'),f.sha256,f.file);
});
test('fracture adapter rejects unsupported physics and preserves per-material cards',()=>{
 const m=fracturePatch({nx:2,ny:2}),s=fractureSettings();assert.throws(()=>prepareFracture(m,{...s,finiteStrain:true}),/小变形平面应变/);assert.throws(()=>prepareFracture(m,{...s,planeMode:0}),/小变形平面应变/);
 assert.throws(()=>prepareFracture(m,{...s,materials:{steel:{model:'plastic'}}}),/所有实体材料/);
 const multi=structuredClone(m);multi.materials.push({materialNo:2,id:'other'});multi.elements[1].materialNo=2;multi.elements[1].elasticModulus=100e9;
 s.materials.other={model:'phaseField',fractureEnergy:5400,fractureLength:.001};const req=prepareFracture(multi,s);assert.equal(req.materialSettings[2].fractureEnergy,5400);assert.ok(req.warnings.length);
 multi.elements[1].poissonRatio=.2;assert.throws(()=>prepareFracture(multi,s),/相同泊松比/);
});
test('upstream AT2 notch propagates a localized irreversible damage band with load drop',async()=>{
 const updates=[],result=await runFracture(fracturePatch({nx:20,ny:20,notch:true}),fractureSettings({fractureDisplacement:.000028,increments:25}),{onProgress:p=>updates.push(p)});
 assert.equal(result.completed,true);assert.equal(result.fracture,true);assert.equal(result.frames.length,26);assert.equal(result.frames[0].time,0);assert.equal(result.frames.at(-1).time,1);
 assert.ok(updates.some(p=>p.phase==='solving'&&p.fraction>0&&p.fraction<1));
 for(let i=0;i<result.frames.length;i++)for(const [id,[d]]of Object.entries(result.frames[i].damage)){assert.ok(d>=0&&d<=1);if(i)assert.ok(d>=result.frames[i-1].damage[id][0]-1e-10);}
 const f=result.frames.at(-1),peak=Math.max(...result.frames.map(f=>f.reactionForce));assert.ok(Math.max(...Object.values(f.damage).map(d=>d[0]))>.95);assert.ok(f.reactionForce<peak*.1,'no post-peak load drop');
 const broken=result.model.nodes.filter(n=>f.damage[n.nodeNo][0]>.9);assert.ok(broken.some(n=>n.x>.009));assert.ok(broken.every(n=>n.y>.003&&n.y<.007),'damage should remain near the notch ligament');
 fs.mkdirSync(path.resolve(__dirname,'../tmp'),{recursive:true});fs.writeFileSync(path.resolve(__dirname,'../tmp/fracture-verified-result.json'),JSON.stringify(result));
});
test('force loading and heterogeneous E/Gc use original nodal loads once',async()=>{
 const m=fracturePatch({nx:2,ny:2}),s=fractureSettings({fractureLoading:'forces',increments:3});m.materials.push({materialNo:2,id:'other'});m.elements[0].materialNo=2;m.elements[0].elasticModulus=100e9;s.materials.other={model:'phaseField',fractureEnergy:4000,fractureLength:.001};
 m.elementNodeLoads=[{elementNo:1,forceY1:1e50}];[m.elements[0].node2,m.elements[0].node3]=[m.elements[0].node3,m.elements[0].node2];const r=await runFracture(m,s);assert.equal(r.completed,true);assert.ok(Math.max(...Object.values(r.frames.at(-1).damage).map(d=>d[0]))<1e-5);assert.equal(r.materialSettings[2].fractureEnergy,4000);
 const c=new AbortController();c.abort();await assert.rejects(runFracture(m,s,{signal:c.signal}),/取消/);
});
