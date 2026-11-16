import * as THREE from '../vendor/three/three.module.js';

export function createFsiLine(scene,draw){
  const $=name=>document.getElementById('solid3dFsi'+name);
  const panel=$('LineProfile'),status=$('LineStatus'),canvas=$('LineChart'),exportButton=$('ExportLine');
  const inputs=['A','B'].map(end=>['X','Y','Z'].map(d=>$('Line'+end+d)));
  const line=new THREE.LineSegments(new THREE.BufferGeometry(),new THREE.LineBasicMaterial({color:0x00717c,depthTest:false}));
  line.visible=false;line.renderOrder=8;scene.add(line);
  let mesh=null,runId=null,points=null,worker=null,request=null,shown=null,sequence=0;
  function clear(){
    worker?.terminate();worker=null;request=null;shown=null;line.visible=false;points=null;runId=null;mesh=null;
    line.geometry.dispose();line.geometry=new THREE.BufferGeometry();
    canvas.hidden=true;exportButton.disabled=true;status.textContent='';
  }
  panel.addEventListener('toggle',draw);
  $('ApplyLine').addEventListener('click',()=>{
    const coords=inputs.map(group=>group.map(input=>input.valueAsNumber));
    if(!coords.flat().every(Number.isFinite)||coords[0].every((x,d)=>x===coords[1][d])){
      status.textContent='请输入两个不同点的完整坐标。';return;
    }
    points=coords;draw();
  });
  exportButton.addEventListener('click',async()=>{
    try{
      const {frame,label,unit,samples}=shown;
      const rows=[['距离 (m)','X (m)','Y (m)','Z (m)',`${label} (${unit})`,'帧','时间 (s)'],
        ...samples.map(s=>[s.distance,...s.point,s.value,frame.index+1,frame.time])];
      const handle=await window.chooseExportFile('TENSORA-3D-FSI-profile.csv','text/csv','.csv');
      if(handle)await window.writeExportFile(handle,writer=>writer.write(ResultProbe.csvText(rows)));
    }catch(error){status.textContent=error.message;}
  });
  function update({mesh:view,run,frame,hidden,field,label,unit,role}){
    panel.hidden=!view||!frame;
    if(!view||!frame){if(mesh)clear();return;}
    if(view!==mesh||run.runId!==runId){clear();mesh=view;runId=run.runId;}
    if(!panel.open||!points){line.visible=false;return;}
    const values=frame.nodeFields[field];
    const roles=run.settings.volumeRoles;
    const visible=view.volumes.map(volume=>String(volume.id)).filter(id=>!hidden.has(id)&&roles[id]===role).sort();
    if(!values||!visible.length||(role==='fluid'&&frame.particles)){
      status.textContent='请选择具有体网格结果的可见结果场。';
      line.visible=false;canvas.hidden=true;exportButton.disabled=true;return;
    }
    const revision=[frame.index,role,...visible].join('/');
    const key=[revision,field,...points.flat()].join('/');
    if(request?.key!==key){
      if(!worker){
        worker=new Worker(new URL('../core/fsi-line-worker.js',import.meta.url));
        worker.postMessage({mesh:{nodes:mesh.nodes,tets:mesh.tets,tetVolumes:mesh.tetVolumes}});
        worker.onmessage=({data})=>{
          if(request?.id===data.id){request.result=data;draw();}
        };
        worker.onerror=()=>{
          worker.terminate();worker=null;
          if(request){request.result={error:'线剖面计算进程异常。'};draw();}
        };
      }
      const id=++sequence;
      request={key,id,result:null};
      const fields=FsiPost.packFields(frame,[field]);
      worker.postMessage({id,revision,role,visible,engine:run.engine,fields,field,points},Object.values(fields).map(values=>values.buffer));
    }
    if(!request.result?.samples){
      status.textContent=request.result?.error||'正在计算线剖面…';
      line.visible=false;canvas.hidden=true;exportButton.disabled=true;return;
    }
    const {samples}=request.result;
    const available=samples.filter(s=>Number.isFinite(s.value));
    if(!available.length){
      status.textContent='当前剖面与可见结果场没有有效交集。';
      line.visible=false;canvas.hidden=true;exportButton.disabled=true;return;
    }
    canvas.hidden=false;exportButton.disabled=false;
    if(shown?.samples!==samples){
      shown={samples,label,unit,frame};
      const coordinates=[];
      for(let i=1;i<samples.length;i++){
        if(Number.isFinite(samples[i-1].value)&&Number.isFinite(samples[i].value))coordinates.push(...samples[i-1].point,...samples[i].point);
      }
      line.geometry.dispose();line.geometry=new THREE.BufferGeometry();
      line.geometry.setAttribute('position',new THREE.Float32BufferAttribute(coordinates,3));
      const format=ResultProbe.formatValue,valid=available.map(s=>s.value);
      status.textContent=`长度 ${format(samples.at(-1).distance)} m · ${label} ${format(Math.min(...valid))} 至 ${format(Math.max(...valid))} ${unit}`;
    }
    line.visible=true;
    ResultProbe.drawChart(canvas,{x:samples.map(s=>s.distance),series:[{values:samples.map(s=>s.value),color:'#00717c'}],
      xLabel:'沿线距离 (m)',yLabel:`${label} (${unit})`});
  }
  return {update,clear,pending:()=>Boolean(panel.open&&request&&!request.result)};
}
