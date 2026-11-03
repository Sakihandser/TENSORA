const test=require('node:test'),assert=require('node:assert/strict'),path=require('node:path'),fs=require('node:fs'),os=require('node:os'),{spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..'),native=path.join(__dirname,'native/x64/Release'),exe=path.join(native,'gas-verification.exe');
test.before(()=>{
 const build=spawnSync('C:/Program Files/Microsoft Visual Studio/2022/Community/MSBuild/Current/Bin/MSBuild.exe',['tests/native/GasVerification.vcxproj','/p:Configuration=Release','/p:Platform=x64','/v:minimal','/nologo'],{cwd:root,encoding:'utf8',windowsHide:true});
 assert.equal(build.status,0,build.stdout+build.stderr);
});
test('DLL EOS agrees with direct upstream headers, SI/CGS scaling and inverse energy for 100 states',()=>{
 const r=spawnSync(exe,['upstream-eos'],{encoding:'utf8',windowsHide:true});assert.equal(r.status,0,r.stderr);
 assert.deepEqual(JSON.parse(r.stdout),{samples:100,rejected:14});
});
test('EOS fails explicitly without the upstream DLL',()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'tensora-eos-missing-'));
 try{
  const copy=path.join(dir,'check.exe');fs.copyFileSync(exe,copy);
  const r=spawnSync(copy,['upstream-eos'],{encoding:'utf8',windowsHide:true});
  assert.notEqual(r.status,0);assert.match(r.stderr,/Singularity-EOS runtime is missing/);
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
