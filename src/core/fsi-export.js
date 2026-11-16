(function(root){
  'use strict';
  const flowKeys=new Set(['vx','vy','vz','vmag','pressure','cp','vorticity','q','density','temperature','mach']);
  const ownKeys=(fields,predicate)=>Object.keys(fields).filter(key=>!key.startsWith('flowU')&&predicate(key));
  function dataArray(name,data,components=1,type='Float32'){
    const buffer=new Uint8Array(data.byteLength+4);
    new DataView(buffer.buffer).setUint32(0,data.byteLength,true);
    buffer.set(new Uint8Array(data.buffer,data.byteOffset,data.byteLength),4);
    const binary=buffer.toBase64?.()??base64(buffer);
    return `<DataArray type="${type}" Name="${name}" NumberOfComponents="${components}" format="binary">${binary}</DataArray>`;
  }
  function base64(bytes){
    const parts=[];
    for(let i=0;i<bytes.length;i+=0x6000)parts.push(btoa(String.fromCharCode(...bytes.subarray(i,i+0x6000))));
    return parts.join('');
  }
  const vtk=(kind,content)=>`<?xml version="1.0"?>\n<VTKFile type="${kind}" version="0.1" byte_order="LittleEndian" header_type="UInt32">\n${content}\n</VTKFile>\n`;
  function extract(cells,predicate){
    const ids=[],local=new Map(),connectivity=[];
    cells.forEach((cell,i)=>{
      if(!predicate(i))return;
      for(const id of cell){
        if(!local.has(id)){local.set(id,ids.length);ids.push(id);}
        connectivity.push(local.get(id));
      }
    });
    return {ids,connectivity:Int32Array.from(connectivity)};
  }
  function points(ids,coordinates){
    const xyz=new Float64Array(ids.length*3);
    ids.forEach((id,i)=>xyz.set(coordinates[id],i*3));
    return dataArray('Points',xyz,3,'Float64');
  }
  function pointData(ids,fields,keys,idName){
    const arrays=keys.map(key=>dataArray(key,Float32Array.from(ids,id=>fields[key][id])));
    for(const [name,components] of [['Velocity',['vx','vy','vz']],['Displacement',['ux','uy','uz']]]){
      if(!components.slice(0,2).every(k=>keys.includes(k)))continue;
      const vector=new Float32Array(ids.length*3);
      ids.forEach((id,i)=>components.forEach((key,d)=>vector[i*3+d]=fields[key]?.[id]??0));
      arrays.push(dataArray(name,vector,3));
    }
    arrays.push(dataArray(idName,Int32Array.from(ids),1,'Int32'));
    return arrays.join('\n');
  }
  function unstructured(zone,dimension,nodes,fields,isFlow,sph){
    const {ids,connectivity}=zone,width=dimension+1,count=connectivity.length/width;
    const offsets=Int32Array.from({length:count},(_,i)=>(i+1)*width);
    const types=new Uint8Array(count).fill(dimension===2?5:10);
    const keys=ownKeys(fields,key=>isFlow?flowKeys.has(key):sph||!flowKeys.has(key));
    return vtk('UnstructuredGrid',`<UnstructuredGrid><Piece NumberOfPoints="${ids.length}" NumberOfCells="${count}">
<PointData>${pointData(ids,fields,keys,'GlobalNodeId')}</PointData><Points>${points(ids,nodes)}</Points>
<Cells>${dataArray('connectivity',connectivity,1,'Int32')}${dataArray('offsets',offsets,1,'Int32')}${dataArray('types',types,1,'UInt8')}</Cells>
</Piece></UnstructuredGrid>`);
  }
  function particleCloud(particles){
    const {count,positions,values}=particles,ids=[];
    for(let i=0;i<count;i++)if(positions.subarray(i*3,i*3+3).every(Number.isFinite))ids.push(i);
    const xyz=new Float32Array(ids.length*3);
    ids.forEach((id,i)=>xyz.set(positions.subarray(id*3,id*3+3),i*3));
    return vtk('PolyData',`<PolyData><Piece NumberOfPoints="${ids.length}" NumberOfVerts="${ids.length}" NumberOfLines="0" NumberOfStrips="0" NumberOfPolys="0">
<PointData>${pointData(ids,values,ownKeys(values,key=>flowKeys.has(key)),'ParticleId')}</PointData><Points>${dataArray('Points',xyz,3)}</Points>
<Verts>${dataArray('connectivity',Int32Array.from(ids,(_,i)=>i),1,'Int32')}${dataArray('offsets',Int32Array.from(ids,(_,i)=>i+1),1,'Int32')}</Verts>
</Piece></PolyData>`);
  }
  async function* series({run,nodes,cells,role,loadFrame},post=root.FsiPost){
    const flow=run.engine==='sph'?null:extract(cells,i=>role(i)==='fluid'),solid=extract(cells,i=>role(i)==='solid');
    const files=[];
    for(let i=0;i<run.frames.length;i++){
      const frame=await loadFrame(i),fields=frame.fields||{...frame.nodeFields,...frame.flowGeometry};
      for(const [part,label,zone] of [[0,'fluid',flow],[1,'structure',solid]]){
        if(!zone?.ids.length)continue;
        const coordinates=part===0?post.flowNodes(nodes,fields,run.engine):post.deformedNodes(nodes,fields);
        const name='frames/'+label+'-'+String(i).padStart(4,'0')+'.vtu';
        files.push({time:run.frames[i].time??i,part,name});
        yield {name,text:unstructured(zone,run.dimension,coordinates,fields,part===0,run.engine==='sph')};
      }
      if(frame.particles){
        const name='frames/particles-'+String(i).padStart(4,'0')+'.vtp';
        files.push({time:run.frames[i].time??i,part:2,name});
        yield {name,text:particleCloud(frame.particles)};
      }
    }
    yield {name:'fsi.pvd',text:vtk('Collection','<Collection>\n'+files.map(({time,part,name})=>
      `<DataSet timestep="${time}" group="" part="${part}" file="${name}"/>`).join('\n')+'\n</Collection>')};
  }
  async function saveSeries(options){
    const handle=await root.chooseExportFile('TENSORA-FSI-ParaView.zip','application/zip','.zip');
    if(!handle)return false;
    let compress;
    try{
      new CompressionStream('deflate-raw');
      compress=async bytes=>new Uint8Array(await new Response(new Blob([bytes]).stream().pipeThrough(new CompressionStream('deflate-raw'))).arrayBuffer());
    }catch{/* Standard stored ZIP is available in browsers without raw deflate. */}
    await root.writeExportChunks(handle,root.ResultExport.archive(series(options),compress));
    return true;
  }
  const api={series,saveSeries};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  else root.FsiExport=api;
})(globalThis);
