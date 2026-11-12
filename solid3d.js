'use strict';
// Standalone 3-D TET4 linear elasticity. Gmsh is used only for OCC CAD meshing.
const fs = require('node:fs/promises');
const fsSync = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn, spawnSync } = require('node:child_process');
const { Worker, parentPort, workerData } = require('node:worker_threads');
const { appendRestraintGeometry, bindRestraintGroups } = require('./solid3d-restraint-geometry');
const { isPressureLoad, isLinearSurfaceLoad, validateGeometryLoad, restraintGeometryKey,
  surfaceLoadValue, interpolateLoad, openEdgePath, segmentParameter } = require('./src/core/solid3d-restraint-data.js');
const GMSH = path.join(__dirname, 'third_party/gmsh/gmsh-4.15.0-Windows64/gmsh.exe');
const MAX_NODES = 350_000;
const MAX_TETS = 1_500_000;
const MESH_THREADS = Math.min(8,os.availableParallelism());
const PCG = path.join(__dirname,'TensoraCore/x64/Release/Solid3dPcg.exe');
// The RTX 4070 Laptop crossed over above the mid-size test. Leave headroom
// for the transfer and device startup costs before using GPU automatically.
const AUTO_GPU_TETS = 1_200_000;
const NATIVE_CPU_TETS = 80_000;
const finite = (v, name) => { const n=Number(v); if(!Number.isFinite(n)) throw Error(`${name} 必须为有限数值`); return n; };
const positive = (v, name) => { const n=finite(v,name); if(n<=0) throw Error(`${name} 必须大于零`); return n; };
const CAD_BOUNDARY_FAILURE = /Invalid boundary mesh|UnableToOrientTheShape|PLC Error|failed to recover constrained/i;

function geometryScript(shapes,{importStep=false}={}) {
  if(!Array.isArray(shapes)||(!shapes.length&&!importStep)||shapes.length>100) throw Error('需要至少一个实体，最多支持 100 个绘图特征');
  const lines=['SetFactory("OpenCASCADE");'],adds=[],cuts=[],targets=new Map();
  if(importStep){lines.push('Geometry.OCCTargetUnit = "M";','Merge "input.step";','imported[] = Volume{:};');adds.push('imported[]');}
  shapes.forEach((shape,i)=>{
    const p=[finite(shape.x??0,'X'),finite(shape.y??0,'Y'),finite(shape.z??0,'Z')],tag=`body${i}`;
    if(shape.type!=='extrusion') lines.push(`${tag} = newv;`);
    if(shape.type==='box') lines.push(`Box(${tag}) = {0,0,0,${positive(shape.dx,'长度')},${positive(shape.dy,'宽度')},${positive(shape.dz,'高度')}};`);
    else if(shape.type==='cylinder') lines.push(`Cylinder(${tag}) = {0,0,0,0,0,${positive(shape.height,'高度')},${positive(shape.radius,'半径')}};`);
    else if(shape.type==='sphere') lines.push(`Sphere(${tag}) = {0,0,0,${positive(shape.radius,'半径')}};`);
    else if(shape.type==='cone'){
      const top=finite(shape.topRadius??0,'顶面半径');
      if(top<0)throw Error('顶面半径不能小于零');
      lines.push(`Cone(${tag}) = {0,0,0,0,0,${positive(shape.height,'高度')},${positive(shape.radius,'底面半径')},${top}};`);
    }
    else if(shape.type==='extrusion'){
      const points=shape.polygon;if(!Array.isArray(points)||points.length<3||points.length>600)throw Error('二维截面须有 3–600 个点');
      const n=points.length;
      points.forEach((q,j)=>{const x=finite(Array.isArray(q)?q[0]:q.x,'草图 X'),y=finite(Array.isArray(q)?q[1]:q.y,'草图 Y');lines.push(`sp${i}_${j} = newp; Point(sp${i}_${j}) = {${x},${y},0,1};`);});
      points.forEach((_,j)=>lines.push(`sl${i}_${j} = newl; Line(sl${i}_${j}) = {sp${i}_${j},sp${i}_${(j+1)%n}};`));
      lines.push(`loop${i} = newll; Curve Loop(loop${i}) = {${points.map((_,j)=>`sl${i}_${j}`).join(',')}};`);
      lines.push(`surf${i} = news; Plane Surface(surf${i}) = {loop${i}};`);
      lines.push(`sketch${i}[] = Extrude {0,0,${positive(shape.height,'拉伸高度')}} { Surface{surf${i}}; };`);
      lines.push(`${tag} = sketch${i}[1];`);
    }else throw Error('不支持的 CAD 特征类型');
    const rotate=(axis,angle)=>lines.push(`Rotate {{${axis}}, {0,0,0}, ${angle}} { Volume{${tag}}; }`);
    const plane=shape.plane??'XY';
    if(plane==='XZ')rotate('1,0,0',Math.PI/2);
    else if(plane==='YZ')rotate('1,1,1',2*Math.PI/3);
    else if(plane!=='XY')throw Error('请选择 XY、XZ 或 YZ 基准面');
    ['rx','ry','rz'].forEach((key,k)=>{
      const angle=finite(shape[key]??0,key);
      if(angle)rotate(['1,0,0','0,1,0','0,0,1'][k],(angle%360)*Math.PI/180);
    });
    if(p.some(Boolean))lines.push(`Translate {${p.join(',')}} { Volume{${tag}}; }`);
    if(shape.operation==='cut'){
      cuts.push({tag,target:shape.cutTarget});
    }else{
      const body=`solid${i}[]`;
      lines.push(`${body} = {${tag}};`);
      adds.push(body);
      if(shape.featureId)targets.set(shape.featureId,body);
    }
  });
  if(!adds.length)throw Error('至少需要一个加实体');
  const globalCuts=[];
  for(const {tag,target} of cuts){
    if(!target){globalCuts.push(tag);continue;}
    const body=targets.get(target);
    if(!body)throw Error('切削目标已移除，请重新选择目标实体');
    lines.push(`${body} = BooleanDifference{ Volume{${body}}; Delete; }{ Volume{${tag}}; Delete; };`);
  }
  if(globalCuts.length)lines.push(`BooleanDifference{ Volume{${adds.join(',')}}; Delete; }{ Volume{${globalCuts.join(',')}}; Delete; }`);
  lines.push('Coherence;'); // OCC BooleanFragments: conformal multi-volume interfaces.
  return lines.join('\n')+'\n';
}
function run(exe,args,cwd,{timeout=90000,signal}={}){return new Promise((resolve,reject)=>{
  signal?.throwIfAborted();
  const child=spawn(exe,args,{cwd,windowsHide:true}); let out='',err='';
  let timedOut=false,spawnError;
  const abort=()=>child.kill();
  signal?.addEventListener('abort',abort,{once:true});
  const timer=setTimeout(()=>{timedOut=true;child.kill();},timeout);
  child.stdout.on('data',b=>{out+=b.toString();if(out.length>20000)out=out.slice(-20000);});
  child.stderr.on('data',b=>{err+=b.toString();if(err.length>20000)err=err.slice(-20000);});
  child.on('error',error=>{spawnError=error;});
  child.on('close',code=>{
    clearTimeout(timer);
    signal?.removeEventListener('abort',abort);
    if(signal?.aborted)return reject(signal.reason);
    if(timedOut)return reject(Error('三维网格生成超时'));
    if(spawnError)return reject(spawnError);
    if(code!==0||/No elements in volume\b/i.test(err)){
      return reject(Object.assign(Error(`Gmsh 失败 (${code}): ${err||out}`),{
        code:'GMSH_FAILED',boundaryFailure:CAD_BOUNDARY_FAILURE.test(err)||CAD_BOUNDARY_FAILURE.test(out)
      }));
    }
    resolve();
  });
});}
function faceKey(a,b,c){
  const min=Math.min(a,b,c),max=Math.max(a,b,c);
  return min+','+(a+b+c-min-max)+','+max;
}

// Index only triangles present on CAD faces, rather than every interior mesh face.
function surfaceTetOwners(tets,triangleGroups){
  const owners=new Map();
  let maxNode=0;
  for(const triangles of triangleGroups)for(const tri of triangles){
    owners.set(faceKey(...tri),{first:-1,second:-1,opposite:-1});
    maxNode=Math.max(maxNode,tri[0],tri[1],tri[2]);
  }
  const onSurface=new Uint8Array(maxNode+1);
  for(const key of owners.keys())for(const id of key.split(','))onSurface[Number(id)]=1;
  for(let i=0;i<tets.length;i++){
    const [a,b,c,d]=tets[i];
    if((onSurface[a]||0)+(onSurface[b]||0)+(onSurface[c]||0)+(onSurface[d]||0)<3)continue;
    for(let j=0;j<4;j++){
      const owner=owners.get(j===0?faceKey(b,c,d):j===1?faceKey(a,c,d):j===2?faceKey(a,b,d):faceKey(a,b,c));
      if(!owner)continue;
      if(owner.first<0){owner.first=i;owner.opposite=tets[i][j];}
      else owner.second=i;
    }
  }
  return owners;
}
function addEntityElement(entities,id,connect){
  if(!entities.has(id))entities.set(id,[]);
  entities.get(id).push(connect);
}
function parseMsh(text, cadOwners=null){
  const lines=text.split(/\r?\n/); const ni=lines.indexOf('$Nodes'),ei=lines.indexOf('$Elements');
  if(ni<0||ei<0)throw Error('Gmsh 未输出 MSH2 节点和单元');
  const count=Number(lines[ni+1]);if(!Number.isSafeInteger(count)||count<4||count>MAX_NODES)throw Error(`三维网格节点数须在 4–${MAX_NODES} 之间（当前 ${count}）`);
  const nodes=[],ids=new Map();
  for(let i=0;i<count;i++){const a=lines[ni+2+i].trim().split(/\s+/).map(Number);if(a.length!==4||!a.every(Number.isFinite))throw Error('网格节点数据无效');ids.set(a[0],i);nodes.push(a.slice(1));}
  const tets=[],tetVolumes=[],surfaces=new Map(),edges=new Map(),vertices=[],nElem=Number(lines[ei+1]);
  for(let i=0;i<nElem;i++){
    const a=lines[ei+2+i].trim().split(/\s+/).map(Number);const type=a[1],nt=a[2],connect=a.slice(3+nt).map(id=>ids.get(id));
    if(type!==1&&type!==2&&type!==4&&type!==15)continue;
    if(connect.some(v=>v===undefined))throw Error('网格单元引用不存在的节点');
    const entity=String(a[4]??a[3]??0);
    if(type===4){if(connect.length!==4)throw Error('目前仅支持一阶四面体');tets.push(connect);tetVolumes.push(entity);}
    else if(type===15)vertices.push({id:entity,node:connect[0]});
    else addEntityElement(type===1?edges:surfaces,entity,connect);
  }
  return finishMesh(nodes,tets,tetVolumes,surfaces,cadOwners,edges,vertices);
}
function parseBinaryMsh(buffer,cadOwners){
  let cursor=0;
  function line(){
    const end=buffer.indexOf(10,cursor);
    if(end<0)throw Error('Gmsh 二进制网格文件不完整');
    const text=buffer.toString('ascii',cursor,end).trim();
    cursor=end+1;
    return text;
  }
  function seek(marker){
    while(line()!==marker){}
  }
  if(line()!=='$MeshFormat'||line()!=='2.2 1 8'||buffer.readInt32LE(cursor)!==1){
    throw Error('Gmsh 二进制网格格式无效');
  }
  cursor+=4;
  seek('$Nodes');
  const count=Number(line());
  if(!Number.isSafeInteger(count)||count<4||count>MAX_NODES){
    throw Error(`三维网格节点数须在 4–${MAX_NODES} 之间（当前 ${count}）`);
  }
  const nodes=new Array(count),ids=new Map();
  for(let i=0;i<count;i++,cursor+=28){
    ids.set(buffer.readInt32LE(cursor),i);
    nodes[i]=[buffer.readDoubleLE(cursor+4),buffer.readDoubleLE(cursor+12),buffer.readDoubleLE(cursor+20)];
  }
  seek('$Elements');
  let remaining=Number(line());
  if(!Number.isSafeInteger(remaining)||remaining<1)throw Error('Gmsh 二进制网格格式无效');
  const tets=[],tetVolumes=[],surfaces=new Map(),edges=new Map(),vertices=[];
  const lengths={1:2,2:3,4:4,15:1};
  while(remaining>0){
    const type=buffer.readInt32LE(cursor), count=buffer.readInt32LE(cursor+4), tags=buffer.readInt32LE(cursor+8);
    cursor+=12;
    const length=lengths[type];
    if(!length||count<1||count>remaining||tags<0)throw Error('网格包含不支持的单元类型');
    const stride=4*(1+tags+length);
    if(cursor+stride*count>buffer.length)throw Error('Gmsh 二进制网格文件不完整');
    if(type===4&&tets.length+count>MAX_TETS)throw Error(`网格超过 ${MAX_TETS} 个四面体，请增大网格尺寸`);
    if(type===1||type===2||type===4||type===15){
      for(let i=0;i<count;i++,cursor+=stride){
        const entity=String(tags?buffer.readInt32LE(cursor+4*Math.min(tags,2)):0);
        const start=cursor+4*(1+tags);
        const connect=new Array(length);
        for(let j=0;j<length;j++){
          const index=ids.get(buffer.readInt32LE(start+4*j));
          if(index===undefined)throw Error('网格单元引用不存在的节点');
          connect[j]=index;
        }
        if(type===4){tets.push(connect);tetVolumes.push(entity);}
        else if(type===15)vertices.push({id:entity,node:connect[0]});
        else addEntityElement(type===1?edges:surfaces,entity,connect);
      }
    }else cursor+=count*stride;
    remaining-=count;
  }
  return finishMesh(nodes,tets,tetVolumes,surfaces,cadOwners,edges,vertices);
}
function edgeKey(a,b){return a<b?a+','+b:b+','+a;}
function boundaryEdges(curves,surfaces){
  const segmentsByKey=new Map();
  for(const segments of curves.values())for(const [a,b] of segments){
    segmentsByKey.set(edgeKey(a,b),new Set());
  }
  if(!segmentsByKey.size)return [];
  for(const face of surfaces)for(const [a,b,c] of face.triangles){
    segmentsByKey.get(edgeKey(a,b))?.add(face.id);
    segmentsByKey.get(edgeKey(b,c))?.add(face.id);
    segmentsByKey.get(edgeKey(c,a))?.add(face.id);
  }
  const edges=[];
  for(const [id,segments] of curves){
    const faceIds=new Set(),boundary=[];
    for(const segment of segments){
      const ids=segmentsByKey.get(edgeKey(...segment));
      if(!ids.size)continue;
      boundary.push(segment);
      for(const face of ids)faceIds.add(face);
    }
    if(boundary.length)edges.push({id,segments:boundary,surfaces:[...faceIds]});
  }
  return edges;
}
function finishMesh(nodes,tets,tetVolumes,surfaces,cadOwners,edges,vertices){
  if(cadOwners){
    const volumes=new Map(), faces=[];
    for(const [id,triangles] of surfaces){
      const owners=cadOwners.get(id);
      if(!owners?.length)continue;
      faces.push({id,triangles,volumeId:owners[0],neighborVolumeId:owners[1]??null});
      for(const owner of owners)volumes.set(owner,{id:owner});
    }
    if(!faces.length)throw Error('CAD 运算后没有可显示的实体');
    return {nodes,surfaces:faces,volumes:[...volumes.values()],edges:boundaryEdges(edges,faces)};
  }
  if(!tets.length||!surfaces.size)throw Error('网格缺少四面体或表面三角形');
  if(tets.length>MAX_TETS)throw Error(`网格超过 ${MAX_TETS} 个四面体，请增大网格尺寸`);
  const faceOwners=surfaceTetOwners(tets,surfaces.values());
  const exterior=[];
  for(const [id,triangles] of surfaces){
    const faces=[],triangleVolumes=[],triangleNeighborVolumes=[],trianglePressureSigns=[];
    for(const tri of triangles){
      const owner=faceOwners.get(faceKey(...tri));
      if(owner.first===-1)continue;
      const first=tetVolumes[owner.first],second=tetVolumes[owner.second];
      if(second===first)continue;
      faces.push(tri);triangleVolumes.push(first);triangleNeighborVolumes.push(second??null);
      const [a,b,c]=tri.map(id=>nodes[id]);
      const normal=cross(sub(b,a),sub(c,a));
      trianglePressureSigns.push(dot(normal,sub(nodes[owner.opposite],a))>0?1:-1);
    }
    if(faces.length)exterior.push({id,triangles:faces,triangleVolumes,triangleNeighborVolumes,trianglePressureSigns,volumeId:triangleVolumes[0]});
  }
  const byVolume=new Map();
  tets.forEach((tet,i)=>{
    const id=tetVolumes[i];
    if(!byVolume.has(id))byVolume.set(id,{id,elements:0,centroid:[0,0,0]});
    const volume=byVolume.get(id);
    volume.elements++;
    for(const n of tet)for(let k=0;k<3;k++)volume.centroid[k]+=nodes[n][k]/4;
  });
  const volumes=[...byVolume.values()];
  for(const v of volumes)v.centroid=v.centroid.map(sum=>sum/v.elements);
  return {nodes,tets,tetVolumes,volumes,surfaces:exterior,edges:boundaryEdges(edges,exterior),vertices};
}
async function buildSolid({shapes,stepBase64,meshSize,restraintGuides=[]},preview,{signal}={}){
  signal?.throwIfAborted();
  const size=preview?null:positive(meshSize,'网格尺寸');
  const dir=await fs.mkdtemp(path.join(os.tmpdir(),'tensora-3d-'));
  try{
    let input;
    if(stepBase64){const bytes=Buffer.from(String(stepBase64),'base64');if(!bytes.length||bytes.length>40_000_000)throw Error('STEP 文件须小于 40 MB');await fs.writeFile(path.join(dir,'input.step'),bytes);}
    let script=geometryScript(shapes||[],{importStep:!!stepBase64});
    if(!preview)script=appendRestraintGeometry(script,restraintGuides)+`
      meshVolumes[] = Volume{:};
      Printf("CAD volumes") > "mesh-volumes.txt";
      If (#meshVolumes[] > 0)
        For vi In {0:#meshVolumes[]-1}
          Printf("%.0f", meshVolumes[vi]) >> "mesh-volumes.txt";
        EndFor
      EndIf
    `;
    if(preview)script+=`
      Mesh.MeshSizeFromPoints = 0;
      Mesh.MeshSizeFromCurvature = 28;
      solids[] = Volume{:};
      Printf("CAD") > "cad-faces.txt";
      For vi In {0:#solids[]-1}
        faces[] = Boundary{ Volume{solids[vi]}; };
        For fi In {0:#faces[]-1}
          Printf("%g %g", Abs(faces[fi]), solids[vi]) >> "cad-faces.txt";
        EndFor
      EndFor
    `;
    input=path.join(dir,'input.geo');await fs.writeFile(input,script,'utf8');
    const output=path.join(dir,'mesh.msh');
    const args=[input,preview?'-2':'-3','-format','msh2','-bin','-o',output,'-nt',String(MESH_THREADS)];
    const started=performance.now();
    let algorithm=preview?'surface':'HXT';
    if(preview)await run(GMSH,args,dir,{signal});
    else{
      const options={timeout:240000,signal};
      const coarse=['-clmin',String(size),'-clmax',String(size)];
      try{await run(GMSH,[...args,...coarse,'-algo','hxt'],dir,options);}
      catch(error){
        if(error.code!=='GMSH_FAILED')throw error;
        algorithm='Delaunay';
        // Rebuild the surface triangulation too: both volume algorithms can
        // reject the same crossing facets on close or nearly tangent CAD faces.
        await fs.rm(output,{force:true});
        const sizing=error.boundaryFailure?['-clmin',String(size/8),'-clmax',String(size),
          '-setnumber','Mesh.Algorithm','1','-setnumber','Mesh.MeshSizeFromCurvature','64']:coarse;
        const retry=[...args,...sizing,'-algo','del3d'];
        try{await run(GMSH,retry,dir,options);}
        catch(retryError){
          if(retryError.boundaryFailure){
            throw Error('CAD 边界存在相交或重叠的三角面。请检查球体与相邻实体是否近相切、面是否重合，或切削后是否留下极薄区域。');
          }
          throw retryError;
        }
      }
    }
    const meshed=performance.now();
    const owners=preview?new Map():null;
    if(owners){
      const lines=(await fs.readFile(path.join(dir,'cad-faces.txt'),'utf8')).trim().split(/\r?\n/).slice(1);
      for(const line of lines){
        const [face,volume]=line.trim().split(/\s+/);
        if(!volume)continue;
        if(!owners.has(face))owners.set(face,[]);
        if(!owners.get(face).includes(volume))owners.get(face).push(volume);
      }
      if(!owners.size)throw Error('CAD 运算后没有可显示的实体');
    }
    const bytes=await fs.readFile(output,{signal});
    const mesh=parseBinaryMsh(bytes,owners);
    if(!preview){
      const expected=(await fs.readFile(path.join(dir,'mesh-volumes.txt'),{encoding:'utf8',signal})).trim().split(/\r?\n/).slice(1);
      const generated=new Set(mesh.volumes.map(volume=>volume.id));
      if(expected.some(id=>!generated.has(id.trim())))throw Error('部分 CAD 体域未生成四面体，请检查切削后是否存在极薄区域。');
    }
    if(!preview&&restraintGuides.length){
      const report=await fs.readFile(path.join(dir,'restraint-groups.txt'),'utf8');
      mesh.restraintGroups=bindRestraintGroups(mesh,restraintGuides,report);
    }
    if(!preview)mesh.meshTiming={algorithm,threads:MESH_THREADS,gmshMs:meshed-started,readMs:performance.now()-meshed};
    return mesh;
  }finally{await fs.rm(dir,{recursive:true,force:true});}
}
const meshSolid=(payload,options)=>buildSolid(payload,false,options);
const previewSolid=(payload,options)=>buildSolid(payload,true,options);
const sub=(a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]];
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
function tetData(points){
  const a=sub(points[1],points[0]),b=sub(points[2],points[0]),c=sub(points[3],points[0]);let det=dot(a,cross(b,c));
  if(Math.abs(det)<1e-24)throw Error('存在零体积四面体');
  const grads=[cross(b,c),cross(c,a),cross(a,b)].map(v=>v.map(x=>x/det));
  grads.unshift(grads[0].map((_,j)=>-grads[0][j]-grads[1][j]-grads[2][j]));
  return {volume:Math.abs(det)/6,grads,orientation:Math.sign(det)};
}
function principalValues(sigma){
  const [sx,sy,sz,txy,tyz,txz]=sigma,a=[[sx,txy,txz],[txy,sy,tyz],[txz,tyz,sz]];
  for(let iteration=0;iteration<24;iteration++){
    let p=0,q=1;for(const [i,j] of [[0,1],[0,2],[1,2]])if(Math.abs(a[i][j])>Math.abs(a[p][q])){p=i;q=j;}
    if(Math.abs(a[p][q])<1e-13*Math.max(1,Math.abs(sx),Math.abs(sy),Math.abs(sz)))break;
    const angle=.5*Math.atan2(2*a[p][q],a[q][q]-a[p][p]),c=Math.cos(angle),s=Math.sin(angle);
    const app=a[p][p],aqq=a[q][q],apq=a[p][q];a[p][p]=c*c*app-2*s*c*apq+s*s*aqq;a[q][q]=s*s*app+2*s*c*apq+c*c*aqq;a[p][q]=a[q][p]=0;
    for(let k=0;k<3;k++)if(k!==p&&k!==q){const kp=a[k][p],kq=a[k][q];a[k][p]=a[p][k]=c*kp-s*kq;a[k][q]=a[q][k]=s*kp+c*kq;}
  }
  return [a[0][0],a[1][1],a[2][2]].sort((a,b)=>b-a);
}
function safetyCode(sigma,vm,material,nu){
  if(!material)return 4;
  const fy=Number(material.yieldStrength)*1e6,ft=Number(material.tensileStrength)*1e6,fc=Number(material.compressiveStrength)*1e6;
  const criterion=Number(material.strengthCriterion)||(fy>0?4:1);
  if(criterion===4)return fy>0?(vm>=fy?3:0):4;
  if(criterion===3){
    if(!(fy>0))return 4;
    const principal=principalValues(sigma);
    return principal[0]-principal[2]>=fy?3:0;
  }
  if((criterion!==1&&criterion!==2)||!(ft>0&&fc>0))return 4;
  const principal=principalValues(sigma);
  const values=criterion===2?principal.map((v,i)=>v-nu*(principal.reduce((s,w,j)=>s+(j===i?0:w),0))):principal;
  const tension=Math.max(0,...values)/ft,compression=Math.max(0,...values.map(v=>-v))/fc;
  if(Math.max(tension,compression)<1)return 0;
  return compression>=tension?1:2;
}
function materialResolver(mesh,settings){
  const library=new Map((settings.materials||[]).map(m=>[String(m.id),m]));
  const cache=new Map();
  return index=>{
    const volume=mesh.tetVolumes?.[index]??'0';
    if(cache.has(volume))return cache.get(volume);
    const id=settings.volumeMaterials?.[volume];
    const chosen=library.size?library.get(String(id)):settings.material;
    if(!chosen&&library.size)throw Error(`体域 ${volume} 尚未指定材料`);
    const E=chosen?positive(Number(chosen.elasticModulus)*1e9,'弹性模量'):positive(settings.young,'弹性模量');
    const nu=chosen?finite(chosen.poissonRatio,'泊松比'):finite(settings.poisson,'泊松比');
    if(nu<=-1||nu>=.5)throw Error('泊松比须在 -1 与 0.5 之间');
    const entry={...lame(E,nu),E,nu,material:chosen||settings.material||null};
    cache.set(volume,entry);
    return entry;
  };
}
function surfaceLoad(triangles,nodes,load,owners,add){
  const data=triangles.map(triangle=>{
    const points=triangle.map(id=>nodes[id]);
    const normal=cross(sub(points[1],points[0]),sub(points[2],points[0]));
    return {triangle,points,normal,area:Math.hypot(...normal)/2};
  });
  const area=data.reduce((sum,item)=>sum+item.area,0);
  if(!(area>0))throw Error('载荷面面积为零');
  const pressure=isPressureLoad(load.type);
  for(const item of data){
    const {triangle,points,normal}=item;
    let direction;
    if(pressure){
      const info=owners.get(faceKey(...triangle));
      if(!info||info.opposite<0)throw Error('压力面找不到相邻四面体');
      const inward=sub(nodes[info.opposite],points[0]);
      const sign=dot(normal,inward)>0?1:-1;
      direction=normal.map(value=>sign*value/(2*item.area));
    }
    const values=points.map(point=>{
      const value=surfaceLoadValue(load,point);
      if(pressure)return direction.map(component=>component*value);
      if(load.type==='force')return load.start.map(value=>value/area);
      return value;
    });
    addConsistentLoad(triangle,values,item.area,add);
  }
}

// Integral of N_i q for affine q on a segment or triangle.
function addConsistentLoad(ids,values,measure,add){
  const sum=[0,0,0],scale=measure/(ids.length*(ids.length+1));
  for(const value of values)for(let i=0;i<3;i++)sum[i]+=value[i];
  for(let i=0;i<ids.length;i++)add(ids[i],sum.map((value,d)=>(value+values[i][d])*scale));
}
function lineLoad(segments,nodes,guide,add){
  const {load}=guide;
  const linear=load.type==='linearLineTraction';
  const onEdge=linear&&guide.kind==='edge';
  const path=onEdge?openEdgePath(segments,nodes):null;
  if(onEdge&&!path)throw Error('线性边载荷需要一条有两个端点的 CAD 边。');
  for(const segment of segments){
    const points=segment.map(id=>nodes[id]);
    const size=Math.hypot(...sub(points[1],points[0]));
    const values=points.map((point,index)=>{
      if(!linear)return load.start;
      const t=path?path.distances.get(segment[index])/path.length:segmentParameter(guide,point);
      return interpolateLoad(load,load.reverse?1-t:t);
    });
    addConsistentLoad(segment,values,size,add);
  }
}

function assembleLoads(mesh,conditions,materialForTet,faceOwners,{requireLoad=true,requireRestraint=true}={}){
  const {nodes,tets,surfaces}=mesh,n=nodes.length*3,force=new Float64Array(n),fixed=new Uint8Array(n);
  const surfaceMap=new Map(surfaces.map(s=>[String(s.id),s]));
  const edgeMap=new Map((mesh.edges||[]).map(edge=>[String(edge.id),edge]));
  const groups=new Map((mesh.restraintGroups||[]).map(group=>[group.id,group]));
  const hasPressure=(conditions||[]).some(bc=>isPressureLoad(bc.type)||isPressureLoad(bc.guide?.load?.type));
  const owners=faceOwners||(hasPressure?surfaceTetOwners(tets,surfaces.map(face=>face.triangles)):null);
  let fixedCount=0,loadedCount=0;
  const constrain=(id,axes)=>{if(!Number.isInteger(id)||id<0||id>=nodes.length)throw Error('约束节点不存在');for(let d=0;d<3;d++)if(axes[d]&&!fixed[id*3+d]){fixed[id*3+d]=1;fixedCount++;}};
  const add=(id,v)=>{
    if(!Number.isInteger(id)||id<0||id>=nodes.length)throw Error('载荷节点不存在');
    for(let d=0;d<3;d++){
      force[id*3+d]+=v[d];
      if(!Number.isFinite(force[id*3+d]))throw Error('载荷值必须为有限数值。');
    }
  };
  const vector=bc=>[finite(bc.fx,'Fx'),finite(bc.fy,'Fy'),finite(bc.fz,'Fz')];
  function bodyLoad(type,values,volumes){
    const targets=volumes===null?null:new Set(volumes.map(String));
    let matched=0;
    tets.forEach((tet,i)=>{
      if(targets&&!targets.has(String(mesh.tetVolumes?.[i])))return;
      matched++;
      const volume=tetData(tet.map(id=>nodes[id])).volume;
      const density=type==='gravity'?positive(materialForTet(i).material?.density,'密度'):1;
      const load=values.map(value=>value*volume*density/4);
      for(const id of tet)add(id,load);
    });
    if(!matched)throw Error('载荷作用体域不存在。');
  }
  function loadGroup(guide){
    validateGeometryLoad(guide?.kind,guide?.load);
    const group=groups.get(guide.id);
    if(!group||group.geometry!==restraintGeometryKey(guide)){
      throw Error('几何边界条件尚未绑定网格，请重新划分网格。');
    }
    const {kind,load}=guide;
    if(kind==='volume'){
      if(group.volumes!==null&&!group.volumes?.length)throw Error('载荷作用体域不存在。');
      bodyLoad(load.type,load.start,group.volumes);
      return;
    }
    if(kind==='point'){
      if(group.nodes?.length!==1)throw Error('载荷节点不存在');
      add(group.nodes[0],load.start);
      return;
    }
    const onLine=kind==='line'||kind==='edge';
    const source=onLine?edgeMap:surfaceMap;
    if(!group.entities?.length||group.entities.some(id=>!source.has(String(id)))){
      throw Error('几何边界条件尚未绑定网格，请重新划分网格。');
    }
    const elements=group.entities.flatMap(id=>{
      const entity=source.get(String(id));
      return onLine?entity.segments:entity.triangles;
    });
    if(onLine)lineLoad(elements,nodes,guide,add);
    else surfaceLoad(elements,nodes,load,owners,add);
  }
  for(const bc of conditions||[]){
    if(bc.type==='pointForce'){add(Number(bc.node),vector(bc));loadedCount++;continue;}
    if(bc.type==='fixedNode'){constrain(Number(bc.node),Array.isArray(bc.axes)?bc.axes:[true,true,true]);continue;}
    if(bc.type==='fixedGroup'){
      if(!Array.isArray(bc.axes)||bc.axes.length!==3||!bc.axes.every(axis=>typeof axis==='boolean')||!bc.axes.some(Boolean)){
        throw Error('至少选中一个位移方向。');
      }
      const group=groups.get(bc.group);
      if(!group?.nodes.length)throw Error('几何约束尚未绑定网格，请重新划分网格。');
      for(const id of group.nodes)constrain(id,bc.axes);
      continue;
    }
    if(bc.type==='loadGroup'){loadGroup(bc.guide);loadedCount++;continue;}
    if(bc.type==='bodyForce'||bc.type==='gravity'){
      bodyLoad(bc.type,vector(bc),bc.volume==null?null:[bc.volume]);loadedCount++;continue;
    }
    const surface=surfaceMap.get(String(bc.surface));if(!surface)throw Error('未找到 CAD 面 '+bc.surface);
    if(bc.type==='fixed'){const axes=Array.isArray(bc.axes)?bc.axes:[true,true,true];if(!axes.some(Boolean))throw Error('至少约束一个方向');for(const tri of surface.triangles)for(const id of tri)constrain(id,axes);continue;}
    const load=isLinearSurfaceLoad(bc.type)?bc:{type:bc.type,start:bc.type==='pressure'?finite(bc.pressure,'压力'):vector(bc)};
    validateGeometryLoad('face',load);
    surfaceLoad(surface.triangles,nodes,load,owners,add);
    loadedCount++;
  }
  if((requireRestraint&&fixedCount<3)||(requireLoad&&!loadedCount))throw Error('至少需要有效约束和载荷');
  return {force,fixed};
}

function deformationModelFromSolid(mesh,settings){
  if(!Array.isArray(mesh?.nodes)||!mesh.nodes.length||!Array.isArray(mesh.tets)||!mesh.tets.length||!Array.isArray(mesh.surfaces))throw Error('请先生成实体网格。');
  if(mesh.nodes.length>200000||mesh.tets.length>400000)throw Error('当前变形模块最多支持 20 万节点 / 40 万单元。');
  if(!Array.isArray(settings?.materials)||!settings.materials.length)throw Error('请先为实体区域分配材料。');
  const resolveMaterial=materialResolver(mesh,settings);
  const {force,fixed}=assembleLoads(mesh,settings.conditions,resolveMaterial);
  const materials=new Map();
  const elements=mesh.tets.map(([a,b,c,d],i)=>{
    const {E,nu,material}=resolveMaterial(i);
    const id=material.id;
    if(!materials.has(id))materials.set(id,{id,materialNo:materials.size+1});
    return {elementNo:i+1,node1:a+1,node2:b+1,node3:c+1,node4:d+1,
      elasticModulus:E,poissonRatio:nu,materialNo:materials.get(id).materialNo};
  });
  const nodes=mesh.nodes.map(([x,y,z],i)=>({nodeNo:i+1,x,y,z,forceX:force[i*3],forceY:force[i*3+1],forceZ:force[i*3+2],
    fixUx:Boolean(fixed[i*3]),fixUy:Boolean(fixed[i*3+1]),fixUz:Boolean(fixed[i*3+2])}));
  return {dimension:3,nodes,elements,materials:[...materials.values()]};
}

function lame(E,nu){
  return {lambda:E*nu/((1+nu)*(1-2*nu)),mu:E/(2*(1+nu))};
}

// Each pair of neighboring nodes contributes one dense 3 × 3 block.
// Pack the graph into typed arrays and reuse it for assembly and CG.
function stiffnessPattern(tets,nodeCount){
  const neighbors=Array.from({length:nodeCount},()=>new Set());
  for(const tet of tets)for(const a of tet)for(const b of tet)neighbors[a].add(b);
  const offsets=new Uint32Array(nodeCount+1);
  for(let i=0;i<nodeCount;i++)offsets[i+1]=offsets[i]+neighbors[i].size;
  const columns=new Uint32Array(offsets[nodeCount]);
  for(let i=0;i<nodeCount;i++)columns.set([...neighbors[i]].sort((a,b)=>a-b),offsets[i]);
  return {offsets,columns};
}
function assembleStiffness(nodes,tets,materialForTet){
  const {offsets,columns}=stiffnessPattern(tets,nodes.length);
  const blocks=new Float64Array(columns.length*9);
  const diagonal=new Float64Array(nodes.length*3).fill(1);
  for(let i=0;i<tets.length;i++){
    const tet=tets[i],{volume,grads}=tetData(tet.map(id=>nodes[id]));
    const {lambda,mu}=materialForTet(i);
    for(let a=0;a<4;a++)for(let b=0;b<4;b++){
      const node=tet[a],neighbor=tet[b],ga=grads[a],gb=grads[b];
      let lo=offsets[node],hi=offsets[node+1]-1;
      while(lo<hi){
        const mid=(lo+hi)>>>1;
        if(columns[mid]<neighbor)lo=mid+1;else hi=mid;
      }
      const block=lo*9,gradientDot=dot(ga,gb);
      for(let u=0;u<3;u++)for(let v=0;v<3;v++){
        const k=block+u*3+v;
        blocks[k]+=volume*(lambda*ga[u]*gb[v]+mu*(ga[v]*gb[u]+(u===v?gradientDot:0)));
        if(node===neighbor&&u===v)diagonal[node*3+u]=blocks[k];
      }
    }
  }
  return {offsets,columns,blocks,diagonal};
}
function multiplyStiffness({offsets,columns,blocks},vector,out){
  for(let row=0;row<offsets.length-1;row++){
    let x=0,y=0,z=0;
    for(let j=offsets[row];j<offsets[row+1];j++){
      const k=j*9,col=columns[j]*3;
      const a=vector[col],b=vector[col+1],c=vector[col+2];
      x+=blocks[k]*a+blocks[k+1]*b+blocks[k+2]*c;
      y+=blocks[k+3]*a+blocks[k+4]*b+blocks[k+5]*c;
      z+=blocks[k+6]*a+blocks[k+7]*b+blocks[k+8]*c;
    }
    out[row*3]=x;out[row*3+1]=y;out[row*3+2]=z;
  }
}
function nativePcg(matrix, inverse, force, tolerance, target){
  const dir=fsSync.mkdtempSync(path.join(os.tmpdir(),'tensora-pcg-'));
  const input=path.join(dir,'matrix.bin');
  let fd;
  try{
    fd=fsSync.openSync(input,'w');
    const header=Buffer.alloc(20);
    header.writeUInt32LE(0x31474350,0);
    header.writeUInt32LE(matrix.offsets.length-1,4);
    header.writeUInt32LE(matrix.columns.length,8);
    header.writeDoubleLE(tolerance,12);
    fsSync.writeFileSync(fd,header);
    for(const array of [matrix.offsets,matrix.columns,matrix.blocks,inverse,force]){
      fsSync.writeFileSync(fd,Buffer.from(array.buffer,array.byteOffset,array.byteLength));
    }
    fsSync.closeSync(fd);
    fd=fsSync.openSync(input,'r');
    const out=spawnSync(PCG,[target],{windowsHide:true,stdio:[fd,'pipe','pipe'],timeout:30*60_000,maxBuffer:force.byteLength+65536});
    if(out.error)throw out.error;
    if(out.status!==0||out.stdout.length!==force.byteLength+4){
      throw Error(out.stderr.toString().trim()||'Native PCG returned an invalid solution');
    }
    const x=new Float64Array(force.length);
    Buffer.from(x.buffer).set(out.stdout.subarray(4));
    return {x,iterations:out.stdout.readUInt32LE(0)};
  }finally{
    if(fd!==undefined)fsSync.closeSync(fd);
    fsSync.rmSync(dir,{recursive:true,force:true});
  }
}
function jsPcg(matrix,inverse,force,tolerance){
  const n=force.length,x=new Float64Array(n),r=Float64Array.from(force),z=new Float64Array(n),p=new Float64Array(n);
  const Ap=new Float64Array(n);
  let rz=0,norm=0,iterations=0;
  for(let i=0;i<n;i++){
    p[i]=r[i]*inverse[i];
    rz+=r[i]*p[i];norm+=r[i]*r[i];
  }
  for(;iterations<Math.min(8000,n*4)&&norm>tolerance*tolerance;iterations++){
    multiplyStiffness(matrix,p,Ap);
    let denom=0;
    for(let i=0;i<n;i++){
      if(!inverse[i])Ap[i]=0;
      denom+=p[i]*Ap[i];
    }
    if(!(denom>0))throw Error('刚度矩阵非正定，请检查约束和网格');
    const alpha=rz/denom;
    let next=0;
    norm=0;
    for(let i=0;i<n;i++){
      x[i]+=alpha*p[i];r[i]-=alpha*Ap[i];z[i]=r[i]*inverse[i];
      next+=r[i]*z[i];norm+=r[i]*r[i];
    }
    const beta=next/rz;
    for(let i=0;i<n;i++)p[i]=z[i]+beta*p[i];
    rz=next;
  }
  return {x,iterations};
}
function solvePcg(matrix,force,fixed,elementCount,preference){
  const inverse=matrix.diagonal.map((value,i)=>fixed[i]?0:1/value);
  const tolerance=Math.max(1e-12,Math.sqrt(dotArray(force,force))*1e-9);
  const product=new Float64Array(force.length);
  const tryGpu=preference==='gpu'||(preference!=='cpu'&&elementCount>=AUTO_GPU_TETS);
  let fallback=null;
  function verify(solution,backend){
    multiplyStiffness(matrix,solution.x,product);
    let norm=0;
    for(let i=0;i<force.length;i++){
      if(fixed[i]&&solution.x[i]!==0)throw Error('求解结果违反位移约束');
      if(!fixed[i])norm+=(force[i]-product[i])**2;
    }
    const residual=Math.sqrt(norm);
    if(!Number.isFinite(residual)||residual>tolerance*10)throw Error(`求解未收敛，残差 ${residual.toExponential(3)}`);
    return {...solution,backend,fallback,residual,product};
  }
  if(fsSync.existsSync(PCG)){
    if(tryGpu){
      try{return verify(nativePcg(matrix,inverse,force,tolerance,'gpu'),'GPU OpenCL FP64');}
      catch(error){fallback=error.message;}
    }
    if(tryGpu||elementCount>=NATIVE_CPU_TETS){
      try{return verify(nativePcg(matrix,inverse,force,tolerance,'cpu'),'CPU OpenMP FP64');}
      catch(error){fallback=fallback||error.message;}
    }
  }else if(tryGpu)fallback='Solid3dPcg.exe is unavailable';
  return verify(jsPcg(matrix,inverse,force,tolerance),'CPU JavaScript FP64');
}
function solveSolid(mesh,settings,{compact=false}={}){
  const {nodes,tets,surfaces}=mesh;if(!Array.isArray(nodes)||!Array.isArray(tets)||!Array.isArray(surfaces))throw Error('网格格式无效');
  if(nodes.length>MAX_NODES||tets.length>MAX_TETS)throw Error('网格过大');
  const started=performance.now();
  const owners=surfaceTetOwners(tets,surfaces.map(surface=>surface.triangles));
  const materialForTet=materialResolver(mesh,settings),{force,fixed}=assembleLoads(mesh,settings.conditions,materialForTet,owners);
  const n=nodes.length*3;
  const matrix=assembleStiffness(nodes,tets,materialForTet);
  const appliedForce=Float64Array.from(force);
  for(let i=0;i<n;i++)if(fixed[i])force[i]=0;
  const assembled=performance.now();
  const {x,iterations,residual,backend,fallback,product:reactions}=solvePcg(matrix,force,fixed,tets.length,settings.computeBackend);
  const solved=performance.now();
  const components=['sxx','syy','szz','sxy','syz','sxz','vm','exx','eyy','ezz','exy','eyz','exz','equivalentStrain'];
  const fields=Object.fromEntries(['ux','uy','uz','umag',...components].map(key=>[key,new Float64Array(nodes.length)]));
  const averaged=components.map(key=>fields[key]);
  const weights=new Float64Array(nodes.length),safetyCounts=[0,0,0,0,0];
  const elementSafety=new Uint8Array(tets.length);
  const elementData=compact?new Float64Array(tets.length*14):null;
  const stress=compact?null:new Array(tets.length);
  let maxDisplacement=0,maxVonMises=0;
  for(let i=0;i<nodes.length;i++){
    const ux=x[3*i],uy=x[3*i+1],uz=x[3*i+2];
    fields.ux[i]=ux;fields.uy[i]=uy;fields.uz[i]=uz;fields.umag[i]=Math.hypot(ux,uy,uz);
    maxDisplacement=Math.max(maxDisplacement,fields.umag[i]);
  }
  for(let i=0;i<tets.length;i++){
    const tet=tets[i],{volume,grads}=tetData(tet.map(id=>nodes[id]));
    const {lambda,mu,nu,material}=materialForTet(i);
    const strain=[0,0,0,0,0,0];
    for(let j=0;j<4;j++){
      const id=tet[j],ux=x[3*id],uy=x[3*id+1],uz=x[3*id+2];
      const [gx,gy,gz]=grads[j];
      strain[0]+=gx*ux;strain[1]+=gy*uy;strain[2]+=gz*uz;
      strain[3]+=(gy*ux+gx*uy)/2;
      strain[4]+=(gz*uy+gy*uz)/2;
      strain[5]+=(gz*ux+gx*uz)/2;
    }
    const trace=strain[0]+strain[1]+strain[2];
    const sigma=strain.map((v,j)=>2*mu*v+(j<3?lambda*trace:0));
    const [sx,sy,sz,txy,tyz,txz]=sigma,[ex,ey,ez,exy,eyz,exz]=strain;
    const vm=Math.sqrt(((sx-sy)**2+(sy-sz)**2+(sz-sx)**2)/2+3*(txy*txy+tyz*tyz+txz*txz));
    const equivalentStrain=Math.sqrt(((ex-ey)**2+(ey-ez)**2+(ez-ex)**2)/2+3*(exy*exy+eyz*eyz+exz*exz));
    const safety=safetyCode(sigma,vm,material,nu),values=[...sigma,vm,...strain,equivalentStrain];
    maxVonMises=Math.max(maxVonMises,vm);
    safetyCounts[safety]++;
    elementSafety[i]=safety;
    if(compact)elementData.set(values,i*14);
    else stress[i]={components:sigma,strain,volumeId:mesh.tetVolumes?.[i]??'0',vonMises:vm,equivalentStrain,safetyCode:safety};
    for(const id of tet){
      weights[id]+=volume;
      for(let j=0;j<averaged.length;j++)averaged[j][id]+=values[j]*volume;
    }
  }
  for(const field of averaged)for(let i=0;i<nodes.length;i++)field[i]/=weights[i]||1;
  const surfaceSafety=surfaces.map(surface=>({id:surface.id,codes:surface.triangles.map(tri=>elementSafety[owners.get(faceKey(...tri))?.first]??4)}));
  for(let i=0;i<n;i++)reactions[i]=fixed[i]?reactions[i]-appliedForce[i]:0;
  const summary={surfaceSafety,safetyCounts,maxDisplacement,maxVonMises,iterations,residual,backend,fallback,
    timing:{assemblyMs:assembled-started,iterationMs:solved-assembled,postprocessMs:performance.now()-solved}};
  if(compact)return {...summary,displacementVector:x,elementData,elementSafety,nodeFields:fields,nodalForces:appliedForce,reactions};
  const nodeFields=Object.fromEntries(Object.entries(fields).map(([key,field])=>[key,Array.from(field)]));
  const displacements=nodes.map((_,i)=>[x[3*i],x[3*i+1],x[3*i+2]]);
  return {...summary,displacements,stress,nodeFields,nodeVonMises:nodeFields.vm,nodalForces:Array.from(appliedForce),reactions:Array.from(reactions)};
}

function dotArray(a,b){let s=0;for(let i=0;i<a.length;i++)s+=a[i]*b[i];return s;}
let solveRunning=false;
async function solveSolidRequest(payload,{binary=false}={}){
  if(solveRunning)throw Error('已有三维计算在运行，请等待完成');
  solveRunning=true;
  try{
    return await new Promise((resolve,reject)=>{
      const worker=new Worker(__filename,{workerData:{solid3dRequest:payload,binary}});
      worker.once('message',message=>{
        if(message.error)reject(Error(message.error));else resolve(binary?message.parts:message.json);
      });
      worker.once('error',reject);
      worker.once('exit',code=>reject(Error(`三维求解进程已退出（${code}）`)));
    });
  }finally{
    solveRunning=false;
  }
}
if(parentPort&&workerData?.solid3dRequest){
  try{
    const {mesh,settings}=JSON.parse(workerData.solid3dRequest);
    if(workerData.binary){
      const {displacementVector,elementData,elementSafety,nodeFields,nodalForces,reactions,...summary}=solveSolid(mesh,settings,{compact:true});
      const arrays={displacementVector,elementData,nodalForces,reactions,...nodeFields,elementSafety};
      const metadata=Buffer.from(JSON.stringify({version:1,summary,arrays:Object.entries(arrays).map(([key,array])=>[key,array.length])}));
      const header=new Uint8Array(Math.ceil((4+metadata.length)/8)*8);
      new DataView(header.buffer).setUint32(0,metadata.length,true);
      header.set(metadata,4);
      const parts=[header,...Object.values(arrays).map(array=>new Uint8Array(array.buffer))];
      parentPort.postMessage({parts},parts.map(part=>part.buffer));
    }else parentPort.postMessage({json:JSON.stringify({ok:true,data:solveSolid(mesh,settings)})});
  }catch(error){
    parentPort.postMessage({error:error.message});
  }
}
module.exports={meshSolid,previewSolid,solveSolid,solveSolidRequest,parseMsh,geometryScript,tetData,principalValues,safetyCode,assembleLoads,deformationModelFromSolid};
