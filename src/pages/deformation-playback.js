// Playback follows saved converged load fractions, not physical dynamic time.
let deformationPlayback={playing:false,position:0,lastTick:0,request:null};
const deformationPlaybackRanges=new WeakMap();
function updateDeformationPlaybackControls(){
  const disabled=!deformationResult||deformationResult.frames.length<2;
  for(const id of ['deformationPlay','baseDeformationPlay']){const button=document.getElementById(id);button.disabled=disabled;button.textContent=deformationPlayback.playing?'暂停回放':'播放加载过程';button.setAttribute('aria-pressed',String(deformationPlayback.playing));}
  document.getElementById('deformationRestart').disabled=disabled;
}
function stopDeformationPlayback(){
  if(deformationPlayback.request!==null)cancelAnimationFrame(deformationPlayback.request);
  deformationPlayback.playing=false;deformationPlayback.request=null;updateDeformationPlaybackControls();
}
function showDeformationPlaybackFrame(index){
  document.getElementById('deformationFrame').value=index;syncDeformationToBaseResults();renderDeformation();
}
function toggleDeformationPlayback(restart=false){
  if(deformationPlayback.playing&&!restart){stopDeformationPlayback();return;}
  if(!deformationResult||deformationResult.frames.length<2)return;
  stopDeformationPlayback();
  const frames=deformationResult.frames,current=Number(document.getElementById('deformationFrame').value)||0;
  const index=restart||current>=frames.length-1?0:current;
  showDeformationPlaybackFrame(index);
  deformationPlayback={playing:true,position:frames[index].time,lastTick:performance.now(),request:null};updateDeformationPlaybackControls();
  const result=deformationResult;
  function tick(now){
    if(!deformationPlayback.playing||deformationResult!==result)return;
    if(now-deformationPlayback.lastTick<80){deformationPlayback.request=requestAnimationFrame(tick);return;}
    const speed=Number(document.getElementById('deformationPlaybackSpeed').value)||1;
    deformationPlayback.position=Math.min(frames.at(-1).time,deformationPlayback.position+(now-deformationPlayback.lastTick)*speed/8000);
    deformationPlayback.lastTick=now;
    let index=0;while(index+1<frames.length&&frames[index+1].time<=deformationPlayback.position+1e-12)index++;
    if(index!==Number(document.getElementById('deformationFrame').value))showDeformationPlaybackFrame(index);
    if(deformationPlayback.position>=frames.at(-1).time){showDeformationPlaybackFrame(frames.length-1);stopDeformationPlayback();return;}
    deformationPlayback.request=requestAnimationFrame(tick);
  }
  deformationPlayback.request=requestAnimationFrame(tick);
}
function initializeDeformationPlayback(){
  for(const id of ['deformationPlay','baseDeformationPlay'])document.getElementById(id).addEventListener('click',()=>toggleDeformationPlayback());
  document.getElementById('deformationRestart').addEventListener('click',()=>toggleDeformationPlayback(true));
  for(const id of ['deformationShowLoads','deformationFixedColor'])document.getElementById(id).addEventListener('change',renderDeformation);
  document.addEventListener('visibilitychange',()=>{if(document.hidden)stopDeformationPlayback();});
  updateDeformationPlaybackControls();
}
function deformationPlaybackColorPeak(result,field){
  if(result.fracture&&field==='damage')return 1;
  let cache=deformationPlaybackRanges.get(result);if(!cache){cache=new Map();deformationPlaybackRanges.set(result,cache);}
  const key=field+JSON.stringify(result.materialSettings||result.settings.materials||{});if(cache.has(key))return cache.get(key);
  const cards=new Map();
  if(['damage','plasticStrain'].includes(field))for(const e of result.model.elements){const card=deformationResultCard(result,e);if(card.model!=='plastic')continue;for(const id of [e.node1,e.node2,e.node3]){if(!cards.has(id)||card.criticalPlasticStrain<cards.get(id).criticalPlasticStrain)cards.set(id,card);}}
  let peak=0;
  for(const f of result.frames)for(const n of result.model.nodes)peak=Math.max(peak,deformationValue(f,n.nodeNo,field,cards.get(n.nodeNo)||{model:'elastic'}));
  cache.set(key,peak);return peak;
}
function drawDeformationPlaybackLoads(context,result,frame,coords,project){
  if(result.fracture&&result.settings.fractureLoading==='displacement')return; // These are prescribed motions, not applied forces.
  const nodes=result.model.nodes.filter(n=>Math.hypot(n.forceX||0,n.forceY||0)>0);let max=0;
  for(const n of nodes)max=Math.max(max,Math.hypot(n.forceX||0,n.forceY||0));if(!max)return;
  context.save();context.strokeStyle='#b22632';context.fillStyle='#b22632';context.lineWidth=2;
  const stride=Math.max(1,Math.ceil(nodes.length/300));
  for(let i=0;i<nodes.length;i+=stride){const n=nodes[i],fx=n.forceX||0,fy=n.forceY||0,magnitude=Math.hypot(fx,fy),length=64*frame.time*magnitude/max;if(length<2)continue;
    const [x,y]=project(coords.get(n.nodeNo)),dx=fx/magnitude,dy=-fy/magnitude;
    context.beginPath();context.moveTo(x-dx*length,y-dy*length);context.lineTo(x,y);context.stroke();
    context.beginPath();context.moveTo(x,y);context.lineTo(x-dx*7-dy*3,y-dy*7+dx*3);context.lineTo(x-dx*7+dy*3,y-dy*7-dx*3);context.closePath();context.fill();
  }context.restore();
}
