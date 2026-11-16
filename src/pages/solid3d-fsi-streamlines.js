import * as THREE from '../vendor/three/three.module.js';
import {hasVelocity} from './solid3d-velocity-vectors.js';

export function createFsiStreamlines(scene,draw){
  const $=name=>document.getElementById('solid3dFsi'+name);
  const toggle=$('Streamlines'),summary=$('StreamStatus'),settings=$('StreamSettings');
  const line=new THREE.LineSegments(new THREE.BufferGeometry(),new THREE.LineBasicMaterial({vertexColors:true}));
  line.name='FSI streamlines';line.visible=false;scene.add(line);
  const pathToggle=$('Pathlines'),pathStatus=$('PathStatus');
  const pathLine=new THREE.LineSegments(new THREE.BufferGeometry(),new THREE.LineBasicMaterial({color:0x087b69}));
  pathLine.name='FSI pathlines';pathLine.visible=false;scene.add(pathLine);
  const paths=FsiPaths.create(draw);
  let pathGeometry=null;
  let worker=null,mesh=null,runId=null,busy=false,pending=null,current=null,sequence=0,rendered=null;

  for(const name of ['Streamlines','Pathlines','SeedMode','NearSeedCount','SeedAxis','SeedPosition','SeedDensity','ParticleSamples','StreamDirection','Transparent']){
    $(name).addEventListener('change',draw);
  }
  function clearSteady(){
    if(worker)worker.terminate();
    worker=null;mesh=null;runId=null;busy=false;pending=null;current=null;rendered=null;
    line.visible=false;
    line.geometry.dispose();line.geometry=new THREE.BufferGeometry();
  }
  function clearPaths(){
    paths.clear();
    pathLine.visible=false;
    if(pathGeometry){pathLine.geometry.dispose();pathLine.geometry=new THREE.BufferGeometry();pathGeometry=null;}
  }
  function process(){
    if(busy||!pending)return;
    if(!worker){
      worker=new Worker(new URL('../core/fsi-stream-worker.js',import.meta.url));
      worker.postMessage({mesh:{nodes:mesh.nodes,tets:mesh.tets,tetVolumes:mesh.tetVolumes}});
      worker.onmessage=({data})=>{
        busy=false;
        if(data.id===current?.id){current.result=data;draw();}
        process();
      };
      worker.onerror=()=>{
        worker.terminate();worker=null;busy=false;pending=null;
        if(current){current.result={error:'流线计算进程异常。'};draw();}
      };
    }
    const {frame,...options}=pending,fields=FsiPost.packFields(frame,['vx','vy','vz']);
    worker.postMessage({...options,frame:frame.index,fields},Object.values(fields).map(values=>values.buffer));
    pending=null;busy=true;
  }
  function updatePaths({view,run,frame,sph,loadFrame,visibleVolumes,solidVolumes,seeds}){
    pathStatus.hidden=pathToggle.disabled||!pathToggle.checked;
    if(pathStatus.hidden){clearPaths();return;}
    if(!visibleVolumes.length){
      clearPaths();pathStatus.textContent='当前没有可见流体体域。';return;
    }
    const signature=JSON.stringify([run.runId,seeds,visibleVolumes]);
    const visible=new Set(visibleVolumes),solid=new Set(solidVolumes);
    const state=paths.update(signature,()=>({
      model:sph?null:{nodes:view.nodes,cells:view.tets,dimension:3,
        fluid:view.tetVolumes.map(id=>visible.has(String(id))),solid:view.tetVolumes.map(id=>solid.has(String(id)))},
      run,loadFrame,...seeds
    }));
    pathStatus.textContent=state.message;
    if(!state.paths){pathLine.visible=false;return;}
    if(pathGeometry?.paths!==state.paths||pathGeometry?.time!==frame.time){
      const coords=[];
      FsiPaths.segments(state.paths,frame.time,(a,b)=>coords.push(...a,...b));
      pathLine.geometry.dispose();pathLine.geometry=new THREE.BufferGeometry();
      pathLine.geometry.setAttribute('position',new THREE.Float32BufferAttribute(coords,3));
      pathGeometry={paths:state.paths,time:frame.time};
    }
    pathLine.visible=true;
  }
  function update({mesh:view,run,frame,hidden,scale,loadFrame}){
    const sph=run?.engine==='sph';
    const enabled=Boolean(view&&frame&&!sph&&hasVelocity(frame.nodeFields));
    toggle.disabled=!enabled;$('StreamUnavailable').hidden=!sph;
    pathToggle.disabled=!(view&&frame&&FsiPaths.available(run)&&(sph||enabled));
    const active=enabled&&toggle.checked,showPaths=!pathToggle.disabled&&pathToggle.checked;
    settings.hidden=!(active||showPaths);
    const seedMode=$('SeedMode').value,plane=seedMode==='plane';
    for(const name of ['SeedAxis','SeedPosition','SeedDensity'])$(name).parentElement.hidden=Boolean(sph)||!plane;
    for(const name of ['SeedMode','Transparent'])$(name).parentElement.hidden=Boolean(sph);
    $('NearSeedCount').parentElement.hidden=Boolean(sph)||plane;
    $('StreamDirection').parentElement.hidden=!active;
    $('ParticleSamples').parentElement.hidden=!sph;
    const axis=Number($('SeedAxis').value),percent=Number($('SeedPosition').value);
    const density=Number($(sph?'ParticleSamples':'SeedDensity').value),direction=$('StreamDirection').value;
    const seeds=sph?{density}:{seedMode,nearCount:Number($('NearSeedCount').value),axis,percent,density};
    const roles=run?.settings.volumeRoles||{};
    const visibleVolumes=Object.keys(roles).filter(id=>roles[id]==='fluid'&&!hidden.has(id)).sort();
    const solidVolumes=Object.keys(roles).filter(id=>roles[id]==='solid').sort();
    if(showPaths)updatePaths({view,run,frame,sph,loadFrame,visibleVolumes,solidVolumes,seeds});
    else{pathStatus.hidden=true;clearPaths();}
    summary.hidden=!active;
    if(!active){
      if(mesh)clearSteady();
      return;
    }
    if(mesh!==view||runId!==run.runId){clearSteady();mesh=view;runId=run.runId;}
    if(!visibleVolumes.length){
      line.visible=false;pending=null;current=null;summary.textContent='当前没有可见流体体域。';
      return;
    }
    const signature=JSON.stringify([frame.index,seeds,direction,visibleVolumes]);
    if(current?.signature!==signature){
      const id=++sequence;
      current={signature,id,result:null};
      pending={id,frame,engine:run.engine,visibleVolumes,solidVolumes,...seeds,direction,maxSpeed:frame.maxVelocity};
      process();
    }
    const result=current.result;
    if(!result?.count){
      line.visible=false;
      summary.textContent=result?.error?'流线计算失败：'+result.error:result?'种子面未生成有效流线。':'正在计算当前帧流线…';
      return;
    }
    if(rendered?.result!==result||rendered?.scale!==scale){
      const {positions,reference,speeds}=result,max=frame.maxVelocity;
      const coordinates=Float32Array.from(positions,(v,i)=>reference[i]+scale*(v-reference[i]));
      const rgb=new Float32Array(speeds.length*3),color=new THREE.Color();
      speeds.forEach((speed,i)=>color.setRGB(...FsiPost.speedColor(speed,max),THREE.SRGBColorSpace).toArray(rgb,i*3));
      line.geometry.dispose();
      line.geometry=new THREE.BufferGeometry();
      line.geometry.setAttribute('position',new THREE.BufferAttribute(coordinates,3));
      line.geometry.setAttribute('color',new THREE.BufferAttribute(rgb,3));
      rendered={result,scale};
      const ramp=document.createElement('span');ramp.className='fsi-stream-ramp';
      const format=ResultProbe.formatValue;
      const location=result.near?uiText('结构附近'):`${['X','Y','Z'][axis]} = ${format(result.position)} m`;
      const note=result.fallback?' · '+uiText('未找到共节点流固界面，已改用全域播种。'):'';
      summary.replaceChildren(`${result.count} 条当前帧流线 · ${location}${note}`,
        document.createElement('br'),'流速 0 ',ramp,`${format(max)} m/s`);
    }
    line.visible=true;
  }

  return {update,clear:()=>{clearSteady();clearPaths();},
    pending:()=>Boolean(current&&!current.result)||paths.pending(),
    transparent:()=>!toggle.disabled&&(toggle.checked||!pathToggle.disabled&&pathToggle.checked)&&$('Transparent').checked};
}
