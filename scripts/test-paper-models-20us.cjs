const fs=require('fs'),path=require('path'),{runBlastCore}=require('../server'),{removeRun}=require('../blast-runner');
const c=path.resolve('tmp/paper-plane-stress'),out=path.join(c,'revision-20us');fs.mkdirSync(out,{recursive:true});
const names=['论文-W45-平面应力-0-0','论文-均质板-平面应力-0-0','论文-W45-平面应力-20-20','论文-均质板-平面应力-20-20'];
async function run(name){const s=JSON.parse(fs.readFileSync(path.resolve('..',name+'.json'))),m=JSON.parse(fs.readFileSync(path.join(c,name+'-direct.json'))),frames=[];let h,metadata;const start=Date.now();
 try{console.log('START_20US',name);h=await runBlastCore(m,{...s.blastSettings,duration:20e-6,frames:41,timeLimitSeconds:60},{lazy:true,onFrame:(f,meta)=>{metadata=meta;frames.push(f);}});const record={name,ok:true,requestedDuration:20e-6,seconds:(Date.now()-start)/1000,metadata,frames,settings:s.blastSettings};fs.writeFileSync(path.join(out,name+'.json'),JSON.stringify(record,null,2));console.log('PASS_20US',name);}
 catch(e){const record={name,ok:false,requestedDuration:20e-6,lastSavedTime:frames.at(-1)?.time??0,seconds:(Date.now()-start)/1000,error:e.message,metadata,frames,settings:s.blastSettings};fs.writeFileSync(path.join(out,name+'.json'),JSON.stringify(record,null,2));console.log('FAIL_20US',name,record.lastSavedTime,e.message);}
 finally{if(h)await removeRun(h.id);}}
(async()=>{let i=0;await Promise.all([0,1].map(async()=>{while(i<names.length)await run(names[i++]);}));})().catch(e=>{console.error(e);process.exitCode=1});
