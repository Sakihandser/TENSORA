(function(root){
  'use strict';
  function spectrum(times,values){
    const n=times.length;
    if(n<8||values.length!==n||!values.every(Number.isFinite))return null;
    const dt=(times[n-1]-times[0])/(n-1);
    if(!(dt>0)||times.some((time,i)=>!Number.isFinite(time)||Math.abs(time-times[0]-i*dt)>dt*1e-5))return null;
    const mean=values.reduce((sum,v)=>sum+v/n,0);
    const window=times.map((_,i)=>(1-Math.cos(2*Math.PI*i/n))/2);
    const gain=window.reduce((a,b)=>a+b,0);
    const signal=values.map((v,i)=>(v-mean)*window[i]);
    const bins=Math.floor(n/2);
    const frequency=Array.from({length:bins},(_,i)=>(i+1)/(n*dt));
    const amplitude=frequency.map((_,i)=>{
      let real=0,imaginary=0;
      for(let j=0;j<n;j++){
        const phase=2*Math.PI*(i+1)*j/n;
        real+=signal[j]*Math.cos(phase);
        imaginary+=signal[j]*Math.sin(phase);
      }
      return Math.hypot(real,imaginary)*(2*(i+1)===n?1:2)/gain;
    });
    const peak=amplitude.indexOf(Math.max(...amplitude));
    return {frequency,amplitude,peak};
  }
  async function probeHistory({run,loadFrame,probes,evaluate,signal,progress}){
    const series=probes.map(()=>({}));
    for(let index=0;index<run.frames.length;index++){
      const frame=await loadFrame(index);
      signal.throwIfAborted();
      probes.forEach((probe,i)=>{
        for(const [key,value] of Object.entries(evaluate(frame,probe))){
          (series[i][key]??=[]).push(value);
        }
      });
      progress?.((index+1)/run.frames.length);
    }
    return {axes:[{key:'time',label:'时间',unit:'s',values:run.frames.map(({time})=>time)}],series};
  }
  if(typeof module!=='undefined'&&module.exports)module.exports={spectrum};
  else root.FsiSpectrum={spectrum,probeHistory};
})(globalThis);
