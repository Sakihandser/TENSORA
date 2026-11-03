const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),{spawnSync}=require('node:child_process');
const {blastRing}=require('./helpers/blast-ring'),{rockCard}=require('./helpers/rock-card');
const {runBlastCore}=require('../server'),{removeRun}=require('../blast-runner');
const root=path.resolve(__dirname,'..'),native=path.join(__dirname,'native/x64/Release');
function card(){const c=rockCard();c.jh2.G=0;c.jh2.K=0;return c;}
function model(){const m=blastRing({sectors:16,rings:3,outer:.3});m.materials[0].blastConstitutive=card();return m;}
test.before(()=>{
 const exe=path.join(native,'rock-verification.exe'),inputs=['tests/native/RockVerification.cpp','TensoraCore/RockConstitutive.h'];
 if(!fs.existsSync(exe)||inputs.some(f=>fs.statSync(path.join(root,f)).mtimeMs>fs.statSync(exe).mtimeMs)){
  const r=spawnSync('C:/Program Files/Microsoft Visual Studio/2022/Community/MSBuild/Current/Bin/MSBuild.exe',['tests/native/RockVerification.vcxproj','/p:Configuration=Release','/p:Platform=x64','/v:minimal','/nologo'],{cwd:root,encoding:'utf8',windowsHide:true});assert.equal(r.status,0,r.stdout+r.stderr);
 }
 if(!fs.existsSync(path.join(native,'jh2-upstream-verification.exe'))){
  const r=spawnSync('powershell',['-NoProfile','-ExecutionPolicy','Bypass','-File','scripts/build-jh2.ps1','-OutputDirectory',native,'-VerifyDriver'],{cwd:root,encoding:'utf8',windowsHide:true});assert.equal(r.status,0,r.stdout+r.stderr);
 }
});
test('accepted plane-stress updates replay exactly through unmodified SIGEPS79 in both kinematics',()=>{
 const app=spawnSync(path.join(native,'rock-verification.exe'),['plane-upstream-path'],{encoding:'utf8',windowsHide:true,maxBuffer:16e6});assert.equal(app.status,0,app.stderr);const samples=JSON.parse(app.stdout);assert.equal(samples.length,960);
 const direct=spawnSync(path.join(native,'jh2-upstream-verification.exe'),[],{input:samples.map(s=>s.input.join(' ')).join('\n')+'\n',encoding:'utf8',windowsHide:true,maxBuffer:16e6});assert.equal(direct.status,0,direct.stderr);
 const rows=direct.stdout.trim().split(/\r?\n/).map(l=>l.trim().split(/\s+/).map(Number));assert.equal(rows.length,960);
 for(const [i,s] of samples.entries()){
  const scale=Math.max(1e6,...s.output.slice(0,6).map(Math.abs));assert.ok(Math.abs(s.output[2])<=1e-8*scale,`sigma_zz ${i}`);
  s.output.forEach((x,k)=>assert.ok(Math.abs(x-rows[i][k])<=1e-9*Math.max(k<6?scale:1,Math.abs(rows[i][k])),`step ${i} field ${k}: ${x} != ${rows[i][k]}`));
 }
 for(const log of [0,1]){const subset=samples.filter(s=>s.logarithmic===log);assert.ok(subset.some(s=>s.output[6]>0));assert.ok(subset.some(s=>s.ezz>0));assert.ok(subset.some(s=>s.ezz<0));assert.ok(subset.some(s=>s.output[7]>0));}
});
test('extreme transverse flow of fully failed plane-stress JH2 is reproduced by the original kernel without FE or gas',()=>{
 const r=spawnSync(path.join(native,'rock-verification.exe'),['failed-plane-flow'],{encoding:'utf8',windowsHide:true,timeout:30000});assert.equal(r.status,0,r.stderr);const x=JSON.parse(r.stdout);
 assert.ok(x.planarJacobian<.00013);assert.ok(x.thicknessStretch>7000);assert.ok(x.volumeJacobian>.98&&x.volumeJacobian<1.01);
 assert.ok(Math.abs(x.stress[2])<1e-8*Math.hypot(...x.stress));
 const direct=spawnSync(path.join(native,'jh2-upstream-verification.exe'),[],{input:x.input.join(' ')+'\n',encoding:'utf8',windowsHide:true});assert.equal(direct.status,0,direct.stderr);
 const raw=direct.stdout.trim().split(/\s+/).map(Number);x.stress.forEach((v,i)=>assert.ok(Math.abs(v-raw[i])<1e-9*Math.max(1e6,Math.abs(v)),`extreme-state stress ${i}`));
});
for(const kinematics of [0,1])for(const pressure of [1e6,100e6])test(`JH2 plane stress blast: kinematics=${kinematics}, pressure=${pressure}`,async t=>{
 const h=await runBlastCore(model(),{rockModel:3,kinematics,planeMode:0,pressure,duration:2e-5,pulse:1e-5,frames:5,boundary:2,shockViscosity:0});t.after(()=>removeRun(h.id));
 assert.equal(h.kinematics,kinematics);assert.equal(h.planeMode,0);assert.equal(h.jh2BackendCommit,'bad6688602d770e019b75773d2d5a48b4f9bd918');
 for(const f of h.frames)for(const e of f.elements){assert.ok(e.every(Number.isFinite));assert.ok(Math.abs(e[7])<1e-7*Math.max(1e6,...e.slice(3,6).map(Math.abs)));}
 assert.ok(h.frames.at(-1).u.some(v=>Math.abs(v)>0));
});
for(const kinematics of [0,1])test(`JH2 plane stress confinement equilibrates without a startup wave: kinematics=${kinematics}`,async t=>{
 const h=await runBlastCore(model(),{rockModel:3,kinematics,planeMode:0,pressure:0,confineX:1e5,confineY:1e5,duration:1e-5,pulse:1e-5,frames:3,boundary:2,shockViscosity:0});t.after(()=>removeRun(h.id));
 assert.ok(h.preloadResidual<1e-6);assert.ok(h.frames.every(f=>f.kineticEnergy<1e-6));
});
for(const kinematics of [0,1])test(`gas and JH2 plane stress retain interface energy balance: kinematics=${kinematics}`,async t=>{
 const h=await runBlastCore(model(),{rockModel:3,kinematics,planeMode:0,sourceMode:1,productEOS:0,productDensity:1000,productEnergy:1e6,chargeRadius:.08,gasCells:32,duration:1e-5,frames:3,boundary:2,shockViscosity:0});t.after(()=>removeRun(h.id));
 for(const f of h.frames){assert.ok(f.elements.every(e=>e.every(Number.isFinite)));assert.ok(Math.abs((f.gasInternalEnergy+f.gasKineticEnergy+f.gasWallWork-h.initialGasEnergy)/h.initialGasEnergy)<1e-8);}
});
for(const kinematics of [0,1])test(`damaging plane-stress gas blast with default shock stabilization: kinematics=${kinematics}`,async t=>{
 const h=await runBlastCore(model(),{rockModel:3,kinematics,planeMode:0,sourceMode:1,productEOS:0,productDensity:1500,productEnergy:3e6,chargeRadius:.1,gasCells:32,duration:2e-4,frames:5,boundary:2,shockViscosity:1,gasFracture:1,crackDamage:.01});t.after(()=>removeRun(h.id));
 assert.ok(h.frames.some(f=>f.elements.some(e=>e[6]>0)));
 for(const f of h.frames){assert.ok(f.elements.every(e=>e.every(Number.isFinite)));assert.ok(Math.abs((f.gasInternalEnergy+f.gasKineticEnergy+f.gasWallWork-h.initialGasEnergy)/h.initialGasEnergy)<1e-8);for(const e of f.elements)assert.ok(Math.abs(e[7])<1e-7*Math.max(1e6,...e.slice(3,6).map(Math.abs)));}
});
test('finite plane-stress embedded weak layer has a bounded static residual and no startup wave',async t=>{
 const m=blastRing({sectors:48,rings:8,outer:.6});m.materials[0].blastConstitutive=card();m.materials[0].blastConstitutive.jh2.G=21.9e9;m.materials[0].blastConstitutive.jh2.K=25.7e9;
 const soft=structuredClone(m.materials[0]);soft.materialNo=2;soft.density=2340;soft.elasticModulus=18.71e9;soft.poissonRatio=.19;soft.blastConstitutive.jh2.G=9.98e9;soft.blastConstitutive.jh2.K=12.67e9;soft.blastConstitutive.jh2.T=44e6;m.materials.push(soft);
 for(const e of m.elements)if(Math.abs(e.centroidX+e.centroidY)<.06 && Math.hypot(e.centroidX,e.centroidY)<.25){e.materialNo=2;e.elasticModulus=soft.elasticModulus;e.poissonRatio=soft.poissonRatio;e.density=soft.density;}
 const h=await runBlastCore(m,{rockModel:3,kinematics:1,planeMode:0,pressure:0,confineX:20e6,confineY:20e6,duration:2e-5,pulse:1e-5,frames:3,boundary:2,shockViscosity:0});t.after(()=>removeRun(h.id));assert.ok(h.preloadResidual<1e-8);assert.ok(h.frames.every(f=>f.kineticEnergy<1e-8));
});
