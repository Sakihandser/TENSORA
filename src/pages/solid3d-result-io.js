export function decodeSolidResult(buffer) {
  const headerLength=new DataView(buffer).getUint32(0,true);
  const header=JSON.parse(new TextDecoder().decode(new Uint8Array(buffer,4,headerLength)));
  if(header.version!==1)throw Error('Unsupported 3D result format');
  let offset=Math.ceil((4+headerLength)/8)*8;
  const result={...header.summary,nodeFields:{}};
  const direct=['displacementVector','elementData','elementSafety','nodalForces','reactions'];
  for(const [name,count] of header.arrays) {
    const Type=name==='elementSafety'?Uint8Array:Float64Array;
    const array=new Type(buffer,offset,count);
    offset+=array.byteLength;
    if(direct.includes(name))result[name]=array;
    else result.nodeFields[name]=array;
  }
  if(offset!==buffer.byteLength)throw Error('Incomplete 3D result data');
  return result;
}

function elementRecord(model,elementData,elementSafety,i) {
  const base=i*14;
  return {components:Array.from(elementData.subarray(base,base+6)),
    strain:Array.from(elementData.subarray(base+7,base+13)),volumeId:model.mesh?.tetVolumes?.[i]??'0',
    vonMises:elementData[base+6],equivalentStrain:elementData[base+13],safetyCode:elementSafety[i]};
}

export function solidResultSnapshot(model,result) {
  if(!result?.elementData)return result;
  const {displacementVector,elementData,elementSafety,nodeFields,nodalForces,reactions,...summary}=result;
  const fields=Object.fromEntries(Object.entries(nodeFields).map(([key,field])=>[key,Array.from(field)]));
  return {...summary, nodeFields:fields, nodeVonMises:fields.vm,
    displacements:Array.from({length:displacementVector.length/3},(_,i)=>Array.from(displacementVector.subarray(3*i,3*i+3))),
    stress:Array.from(elementSafety,(_,i)=>elementRecord(model,elementData,elementSafety,i)),
    nodalForces:Array.from(nodalForces),reactions:Array.from(reactions)};
}

// Preserve the existing JSON schema without building a single huge string.
function* jsonArray(count,get) {
  yield '[';
  const batch=4096;
  for(let start=0;start<count;start+=batch){
    const end=Math.min(start+batch,count), values=[];
    for(let i=start;i<end;i++)values.push(JSON.stringify(get(i)));
    if(start)yield ',';
    yield values.join(',');
  }
  yield ']';
}

export function* solidResultJson(model,result) {
  if(!result.elementData){yield JSON.stringify({model,result});return;}
  const {displacementVector,elementData,elementSafety,nodeFields,nodalForces,reactions,...summary}=result;
  yield '{"model":';
  yield JSON.stringify(model);
  yield ',"result":';
  yield JSON.stringify(summary).slice(0,-1);
  yield ',"displacements":';
  yield* jsonArray(displacementVector.length/3,i=>Array.from(displacementVector.subarray(3*i,3*i+3)));
  yield ',"stress":';
  yield* jsonArray(elementSafety.length,i=>elementRecord(model,elementData,elementSafety,i));
  yield ',"nodeFields":{';
  for(const [i,[key,field]] of Object.entries(nodeFields).entries()){
    if(i)yield ',';
    yield JSON.stringify(key)+':';
    yield* jsonArray(field.length,j=>field[j]);
  }
  yield '},"nodeVonMises":';
  yield* jsonArray(nodeFields.vm.length,i=>nodeFields.vm[i]);
  yield ',"nodalForces":';
  yield* jsonArray(nodalForces.length,i=>nodalForces[i]);
  yield ',"reactions":';
  yield* jsonArray(reactions.length,i=>reactions[i]);
  yield '}}';
}
