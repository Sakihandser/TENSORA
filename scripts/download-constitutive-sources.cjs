// Download the exact pinned upstream bytes; never rewrite constitutive sources.
// Existing files are preserved unless their bytes already match the manifest.
const fs=require('node:fs'),path=require('node:path'),{createHash}=require('node:crypto');
const {execFileSync}=require('node:child_process');
const root=path.resolve(__dirname,'..');
const hash=b=>createHash('sha256').update(b).digest('hex');
async function main(){
 const records=[];
 for(const component of ['singularity-eos-runtime','openradioss-jh2','cbgeo-materials']){
  const dir=path.join(root,'third_party',component),m=JSON.parse(fs.readFileSync(path.join(dir,'manifest.json')));
  for(const f of m.files){
   const repo=f.repository||m.repository,commit=f.commit||m.commit;
   if(!/^https:\/\/github\.com\/[\w.-]+\/[\w.-]+$/.test(repo)||! /^[a-f0-9]{40}$/.test(commit))throw Error('Invalid pinned repository/commit');
   const target=path.resolve(dir,f.file);
   if(!target.startsWith(dir+path.sep))throw Error('Source path outside component');
   const url=repo.replace('https://github.com/','https://raw.githubusercontent.com/')+'/'+commit+'/'+f.origin;
   // curl uses the Windows network/certificate configuration in portable installs.
   const temporary=path.join(root,'tmp','constitutive-download',component+'-'+hash(Buffer.from(f.file))+'.part');
   fs.mkdirSync(path.dirname(temporary),{recursive:true});
   // File output is reset by curl on a retry; stdout retries can concatenate
   // partial responses. No source is installed until its hash matches.
   execFileSync('curl.exe',['-4','--fail','--silent','--show-error','--location','--connect-timeout','10','--max-time','60','--retry','2','--output',temporary,url],{windowsHide:true,maxBuffer:8*1024*1024});
   const bytes=fs.readFileSync(temporary);
   if(hash(bytes)!==f.sha256)throw Error('Downloaded source hash mismatch: '+url);
   if(fs.existsSync(target)&&hash(fs.readFileSync(target))!==f.sha256)throw Error('Preserving modified local source: '+target);
   fs.mkdirSync(path.dirname(target),{recursive:true});
   fs.writeFileSync(target,bytes);
   fs.unlinkSync(temporary);
   records.push({component,file:f.file,url,sha256:f.sha256,bytes:bytes.length});
  }
  console.log(component+': downloaded and verified '+m.files.length+' upstream files');
 }
 const report=path.join(root,'output','constitutive-source-download.json');
 fs.mkdirSync(path.dirname(report),{recursive:true});
 fs.writeFileSync(report,JSON.stringify({retrieved:new Date().toISOString(),files:records},null,2)+'\n');
 console.log(report);
}
main().catch(e=>{console.error(e);process.exitCode=1;});
