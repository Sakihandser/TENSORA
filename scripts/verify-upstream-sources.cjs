const fs=require('node:fs'),path=require('node:path'),{createHash}=require('node:crypto');
const file=path.resolve(process.argv[2]),m=JSON.parse(fs.readFileSync(file));
for(const f of m.files){const actual=createHash('sha256').update(fs.readFileSync(path.resolve(path.dirname(file),f.file))).digest('hex');if(actual!==f.sha256)throw Error('Upstream source hash mismatch: '+f.file);}
console.log('Verified '+m.files.length+' unmodified upstream files; '+m.commit);
