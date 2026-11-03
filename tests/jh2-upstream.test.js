const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {spawnSync}=require('node:child_process'),{createHash}=require('node:crypto');
const root=path.resolve(__dirname,'..'),dir=path.join(root,'third_party/openradioss-jh2'),native=path.join(root,'tests/native/x64/Release');
test.before(()=>{
 const exe=path.join(native,'rock-verification.exe'),inputs=['tests/native/RockVerification.cpp','tests/native/RockVerification.vcxproj','TensoraCore/RockConstitutive.h','TensoraCore/OpenRadiossJH2.h'];
 if(fs.existsSync(exe)&&fs.existsSync(path.join(native,'openradioss_jh2.dll'))&&inputs.every(f=>fs.statSync(path.join(root,f)).mtimeMs<=fs.statSync(exe).mtimeMs))return;
 const r=spawnSync('C:/Program Files/Microsoft Visual Studio/2022/Community/MSBuild/Current/Bin/MSBuild.exe',['tests/native/RockVerification.vcxproj','/p:Configuration=Release','/p:Platform=x64','/v:minimal','/nologo'],{cwd:root,encoding:'utf8',windowsHide:true});assert.equal(r.status,0,r.stdout+r.stderr);
});
test('the compiled JH2 kernel is the pinned, unmodified upstream SIGEPS79 source',()=>{
 const m=JSON.parse(fs.readFileSync(path.join(dir,'manifest.json')));
 assert.equal(m.commit,'bad6688602d770e019b75773d2d5a48b4f9bd918');
 for(const f of m.files)assert.equal(createHash('sha256').update(fs.readFileSync(path.join(dir,f.file))).digest('hex'),f.sha256,f.file);
 const local=fs.readFileSync(path.join(root,'TensoraCore/RockConstitutive.h'),'utf8');
 assert.ok(local.includes('openradioss::Runtime().step('));
 assert.ok(!local.includes('oldDamage+dep/fail'));
});
test('C++ material integration matches direct Fortran upstream calls over 360 multiaxial steps',()=>{
 const build=spawnSync('powershell',['-NoProfile','-ExecutionPolicy','Bypass','-File','scripts/build-jh2.ps1','-OutputDirectory',native,'-VerifyDriver'],{cwd:root,encoding:'utf8',windowsHide:true});
 assert.equal(build.status,0,build.stdout+build.stderr);
 const app=spawnSync(path.join(native,'rock-verification.exe'),['upstream-path'],{encoding:'utf8',windowsHide:true,maxBuffer:16*1024*1024});assert.equal(app.status,0,app.stderr);
 const samples=JSON.parse(app.stdout);assert.equal(samples.length,360);
 assert.ok(samples.some(s=>s.input[32]<0),'must exercise tensile density states');
 const direct=spawnSync(path.join(native,'jh2-upstream-verification.exe'),[],{input:samples.map(s=>s.input.join(' ')).join('\n')+'\n',encoding:'utf8',windowsHide:true,maxBuffer:16*1024*1024});
 assert.equal(direct.status,0,direct.stderr);const rows=direct.stdout.trim().split(/\r?\n/).map(l=>l.trim().split(/\s+/).map(Number));assert.equal(rows.length,samples.length);
 samples.forEach((s,i)=>s.output.forEach((x,k)=>assert.ok(Math.abs(x-rows[i][k])<=1e-10*Math.max(1,Math.abs(rows[i][k])),`step ${i}, field ${k}: ${x} vs ${rows[i][k]}`)));
 assert.ok(samples.some(s=>s.output[6]>0));assert.ok(samples.some(s=>s.output[8]>0));
});
test('JH2 fails explicitly when its upstream runtime is missing',()=>{
 const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'tensora-jh2-missing-'));
 try{
  fs.copyFileSync(path.join(native,'rock-verification.exe'),path.join(temporary,'check.exe'));
  const r=spawnSync(path.join(temporary,'check.exe'),['tension'],{cwd:root,encoding:'utf8',windowsHide:true});
  assert.notEqual(r.status,0);assert.match(r.stderr,/OpenRadioss JH2 runtime is missing/);
 }finally{fs.rmSync(temporary,{recursive:true,force:true});}
});
