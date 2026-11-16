(function(root){
  'use strict';
  function calculate({model,run,loadFrame,axis,percent,density,seedMode,nearCount,signal,progress}){
    return new Promise((resolve,reject)=>{
      const worker=new Worker('./src/core/fsi-path-worker.js');
      const finish=(fn,value)=>{
        worker.terminate();signal.removeEventListener('abort',abort);fn(value);
      };
      const abort=()=>finish(reject,signal.reason);
      signal.addEventListener('abort',abort,{once:true});
      if(signal.aborted){abort();return;}
      let index=0;
      async function send(){
        try{
          const frame=await loadFrame(index);
          signal.throwIfAborted();
          const {time,stats}=run.frames[index];
          const maxSpeed=Math.max(stats.vmag?.[1]||0,run.frames[index-1]?.stats.vmag?.[1]||0);
          const last=index===run.frames.length-1;
          if(frame.particles)worker.postMessage({time,last,positions:frame.particles.positions});
          else{
            const fields=FsiPost.packFields(frame,['vx','vy','vz']);
            worker.postMessage({time,last,maxSpeed,fields},Object.values(fields).map(values=>values.buffer));
          }
          progress?.(++index,run.frames.length);
        }catch(error){finish(reject,error);}
      }
      worker.onmessage=({data})=>{
        if(data.error)finish(reject,Error(data.error));
        else if(data.paths)finish(resolve,data);
        else send();
      };
      worker.onerror=event=>finish(reject,Error(event.message||'路径线计算进程异常。'));
      worker.postMessage({model,options:{axis,percent,density,seedMode,nearCount,engine:run.engine}});
      send();
    });
  }
  function segments(paths,time,add){
    for(const path of paths)for(let i=1;i<path.length;i++){
      const a=path[i-1],b=path[i];
      if(a.time>=time)break;
      if(!a.point||!b.point)continue;
      const t=Math.min(1,(time-a.time)/(b.time-a.time));
      const end=t===1?b.point:a.point.map((x,d)=>x+t*(b.point[d]-x));
      add(a.point,end);
    }
  }
  function create(refresh){
    let key=null,controller=null,state=null;
    function clear(){
      controller?.abort();key=null;controller=null;state=null;
    }
    function update(signature,getOptions){
      if(key===signature)return state;
      clear();key=signature;
      const request=controller=new AbortController();
      state={paths:null,pending:true,message:'正在计算路径线…'};
      calculate({...getOptions(),signal:request.signal,progress:(index,total)=>{
        if(controller===request)state.message=`正在读取路径线帧 ${index} / ${total}…`;
      }}).then(({paths,placement})=>{
        if(controller!==request)return;
        const origin=placement?.near?' · '+uiText('结构附近'):placement?.fallback?' · '+uiText('未找到共节点流固界面，已改用全域播种。'):'';
        state={paths,message:(paths.length?`${paths.length} 条路径线 · 从首帧释放`:'没有连续有效的路径线。')+origin};
        refresh();
      },error=>{
        if(controller!==request)return;
        state={paths:null,message:'路径线计算失败：'+error.message};
        refresh();
      });
      return state;
    }
    return {update,clear,pending:()=>Boolean(state?.pending)};
  }
  function available(run){
    return run?.frames.length>1&&run.frames.every(({time},i)=>Number.isFinite(time)&&(!i||time>run.frames[i-1].time));
  }
  root.FsiPaths={create,segments,available};
})(globalThis);
