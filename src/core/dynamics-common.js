// Helpers shared by the 2D dynamics pages and the 3D dynamics stages: field labels,
// result frame streaming, progress text, mode tables and a small line chart.
(function(root){
  'use strict';
  const FIELD_LABELS={umag:'位移量 |u|',ux:'X 位移 Ux',uy:'Y 位移 Uy',uz:'Z 位移 Uz',vmag:'速度量 |v|',vx:'X 速度 Vx',vy:'Y 速度 Vy',vz:'Z 速度 Vz',
    vm:'von Mises 应力',sxx:'正应力 σxx',syy:'正应力 σyy',szz:'正应力 σzz',sxy:'剪应力 τxy',syz:'剪应力 τyz',sxz:'剪应力 τxz',
    pressure:'压力 p（压为正）',peeq:'等效塑性应变 PEEQ',damage:'本构损伤 D',phx:'X 位移相位',phy:'Y 位移相位',phz:'Z 位移相位'};
  const HARMONIC_LABELS={umag:'位移幅值 |u|',ux:'X 位移幅值',uy:'Y 位移幅值',uz:'Z 位移幅值',vm:'von Mises 应力幅值（周期内峰值）',
    sxx:'σxx 幅值',syy:'σyy 幅值',szz:'σzz 幅值',sxy:'τxy 幅值',syz:'τyz 幅值',sxz:'τxz 幅值'};
  const MODAL_LABELS={umag:'振型位移 |φ|（质量归一化）',ux:'振型 X 分量',uy:'振型 Y 分量',uz:'振型 Z 分量',vm:'振型 von Mises 应力（相对值）'};
  const UNITS={umag:'m',ux:'m',uy:'m',uz:'m',vmag:'m/s',vx:'m/s',vy:'m/s',vz:'m/s',vm:'Pa',sxx:'Pa',syy:'Pa',szz:'Pa',sxy:'Pa',syz:'Pa',sxz:'Pa',
    pressure:'Pa',peeq:'1',damage:'1',phx:'°',phy:'°',phz:'°'};
  const ANALYSIS_NAMES={modal:'模态分析',harmonic:'谐响应',transient:'瞬态动力学',explicit:'显式碰撞冲击'};
  const PHASES={preparing:'准备模型',solving:'CalculiX 求解',starter:'OpenCourant Starter 检查模型',engine:'OpenCourant Engine 显式求解',
    processing:'读取结果',complete:'计算完成',partial:'计算提前停止，已保留部分结果',failed:'计算失败',cancelled:'计算已取消。'};
  const LOAD_SHAPES={step:'阶跃（突加恒载）',ramp:'线性斜坡后保持',sine:'正弦简谐',halfsine:'半正弦脉冲',pulse:'梯形脉冲',table:'表格（时间, 系数）'};
  const fmt=(v,digits=4)=>Number.isFinite(v)?(Math.abs(v)>=1e-3&&Math.abs(v)<1e5||v===0?String(Number(v.toPrecision(digits))):v.toExponential(digits-1)):'—';

  function fieldLabel(summary,key){
    if(summary?.analysis==='harmonic'&&HARMONIC_LABELS[key])return HARMONIC_LABELS[key];
    if(summary?.analysis==='modal'&&MODAL_LABELS[key])return MODAL_LABELS[key];
    return FIELD_LABELS[key]||key;
  }
  function harmonicDisplacement(amplitude,phaseDegrees,cycleAngle){
    return amplitude*Math.sin(cycleAngle+phaseDegrees*Math.PI/180);
  }
  function frameLabel(summary,index){
    const f=summary?.frames?.[index];if(!f)return '';
    if(summary.analysis==='modal'){
      const mode=summary.modes?.[index];
      return mode?.rigid?`模态 ${f.mode} · 刚体模态`:`模态 ${f.mode} · ${fmt(f.value,5)} Hz`;
    }
    if(summary.analysis==='harmonic')return `f = ${fmt(f.value,5)} Hz`;
    return `t = ${fmt(f.value,4)} s`;
  }
  function axisLabel(summary){return summary?.analysis==='harmonic'?'频率 (Hz)':summary?.analysis==='modal'?'模态阶数':'时间 (s)';}

  async function readStream(response,onProgress){
    if(!response.ok&&!response.headers.get('content-type')?.includes('ndjson')){const body=await response.json().catch(()=>({}));throw Error(body.error||'动力学计算失败');}
    const reader=response.body.getReader(),decoder=new TextDecoder();
    let buffer='',result=null;
    for(;;){
      const {value,done}=await reader.read();
      if(done)break;
      buffer+=decoder.decode(value,{stream:true});
      const lines=buffer.split('\n');buffer=lines.pop();
      for(const line of lines){
        if(!line.trim())continue;
        const message=JSON.parse(line);
        if(message.type==='progress')onProgress?.(message);
        else if(message.type==='error')throw Error(message.error);
        else if(message.type==='result')result=message.result;
      }
    }
    if(!result)throw Error('计算进度连接中断，请重新计算。');
    return result;
  }
  // Overall progress fraction from a progress message.
  function progressValue(message,analysis){
    const explicit=analysis==='explicit';
    const weight=explicit?{preparing:0,starter:.02,engine:.1,processing:.85,partial:1,complete:1}:{preparing:0,solving:.03,processing:.8,partial:1,complete:1};
    const span=explicit?{engine:.75,processing:.15}:{solving:analysis==='transient'?.77:.05,processing:.2};
    return Math.min(1,(weight[message.phase]??0)+(span[message.phase]||0)*(message.fraction||0));
  }
  function progressText(message,settings){
    const parts=[PHASES[message.phase]||message.phase];
    if(message.time!=null){
      const end=settings?.analysis==='explicit'?settings.explicitEndTime:settings?.endTime;
      parts.push(`t = ${fmt(message.time,4)} s${end?` / ${end} s`:''}`);
    }
    if(message.dt)parts.push(`Δt = ${message.dt.toExponential(2)} s`);
    if(message.cycle)parts.push(`循环 ${message.cycle.toLocaleString()}`);
    parts.push(`已用 ${((message.elapsedMs||0)/1000).toFixed(1)} s`);
    return parts.join(' · ');
  }

  async function loadFrame(summary,index,cache){
    const key=`${summary.runId}:${index}`;
    if(cache?.has(key))return cache.get(key);
    const response=await fetch(`./api/dynamics-runs/${summary.runId}/frames/${index}`,{cache:'no-store'});
    if(!response.ok)throw Error('动力学结果帧已清理，请重新计算。');
    const all=new Float32Array(await response.arrayBuffer()),n=summary.nodeCount;
    if(all.length!==summary.fields.length*n)throw Error('动力学结果帧数据不完整。');
    const fields={};
    summary.fields.forEach((name,k)=>{fields[name]=all.subarray(k*n,(k+1)*n);});
    const data={index,fields};
    if(cache){cache.set(key,data);if(cache.size>12)cache.delete(cache.keys().next().value);}
    return data;
  }
  async function loadProbe(summary,nodes){
    const response=await fetch(`./api/dynamics-runs/${summary.runId}/probe?nodes=${nodes.join(',')}`,{cache:'no-store'});
    const body=await response.json();
    if(!response.ok||!body.ok)throw Error(body.error||'测点数据读取失败。');
    return body;
  }

  // Curves offered by a run: built-in histories plus per-frame maxima.
  function curves(summary){
    if(!summary)return [];
    const x=summary.frames.map(f=>f.value),out=[];
    if(summary.analysis==='harmonic'){
      out.push({key:'frf',label:'最大位移幅值–频率（频响曲线）',unit:'m',x,y:summary.frames.map(f=>f.stats.umag?.[1]??NaN),log:true});
      if(summary.fields.includes('vm'))out.push({key:'frfStress',label:'最大 von Mises 应力幅值–频率',unit:'Pa',x,y:summary.frames.map(f=>f.stats.vm?.[1]??NaN),log:true});
    }
    if(summary.analysis==='transient'||summary.analysis==='explicit'){
      out.push({key:'umax',label:'最大位移 |u|–时间',unit:'m',x,y:summary.frames.map(f=>f.stats.umag?.[1]??NaN)});
      if(summary.fields.includes('vm'))out.push({key:'vmmax',label:'最大 von Mises 应力–时间',unit:'Pa',x,y:summary.frames.map(f=>f.stats.vm?.[1]??NaN)});
    }
    if(summary.analysis==='transient'&&summary.meta?.loadSamples)out.push({key:'load',label:'载荷系数–时间',unit:'1',x:summary.meta.loadSamples.map(p=>p[0]),y:summary.meta.loadSamples.map(p=>p[1])});
    if(summary.analysis==='explicit'){
      const energies=['kinetic','internal','plastic','contact','external','hourglass'].filter(k=>summary.history?.[k]);
      if(energies.length)out.push({key:'energy',label:'能量–时间',unit:'J',multi:energies.map(k=>({label:summary.history[k].label,x:summary.history[k].x,y:summary.history[k].y}))});
      for(const [key,h] of Object.entries(summary.history||{}))if(key.startsWith('wall'))out.push({key,label:`${h.label}–时间`,unit:h.unit,x:h.x,y:h.y});
    }
    if(summary.analysis==='modal'&&summary.modes?.some(m=>m.effectiveMass))out.push({key:'mass',label:'有效质量占比–模态',unit:'%',bars:true,
      multi:['X','Y','Z'].slice(0,summary.dimension===2?2:3).map((axis,d)=>{
        const total=summary.meta?.totalEffectiveMass?.[d]||summary.meta?.mass||1;
        return {label:`${axis} 向`,x:summary.modes.map(m=>m.mode),y:summary.modes.map(m=>(m.effectiveMass?.[d]||0)/total*100)};
      })});
    return out;
  }

  const PALETTE=['#007c89','#c2410c','#6d28d9','#1b7f3b','#b42318','#2f4858','#a16207'];
  // Line (or grouped bar) chart. series: [{label,x,y}], options {unit,xLabel,log,bars,marker}.
  function drawChart(canvas,series,{unit='',xLabel='',log=false,bars=false,marker=null}={}){
    const box=canvas.getBoundingClientRect();if(!box.width||!box.height)return;
    const dpr=window.devicePixelRatio||1;canvas.width=Math.round(box.width*dpr);canvas.height=Math.round(box.height*dpr);
    const g=canvas.getContext('2d');g.setTransform(dpr,0,0,dpr,0,0);
    const w=box.width,h=box.height;g.fillStyle='#fff';g.fillRect(0,0,w,h);
    g.font='11px Segoe UI, Microsoft YaHei';
    // Legend entries wrap into rows above the plot.
    const legend=[];
    if(series.length>1){
      let x=66,y=10;
      for(const s of series){
        const width=22+g.measureText(root.femI18n?.t?.(s.label)??s.label).width+12;
        if(x+width>w-8&&x>66){x=66;y+=16;}
        legend.push({x,y});x+=width;
      }
    }
    const pad={l:66,r:14,t:legend.length?legend.at(-1).y+14:12,b:34};
    let xs=[],ys=[];
    for(const s of series){s.x.forEach((v,i)=>{const y=s.y[i];if(Number.isFinite(v)&&Number.isFinite(y)&&(!log||y>0)){xs.push(v);ys.push(log?Math.log10(y):y);}});}
    g.font='11px Segoe UI, Microsoft YaHei';g.fillStyle='#7a8996';
    if(!xs.length){g.textAlign='center';g.fillText('暂无曲线数据',w/2,h/2);return;}
    let x0=Math.min(...xs),x1=Math.max(...xs),y0=Math.min(...ys),y1=Math.max(...ys);
    if(bars){x0-=0.5;x1+=0.5;y0=Math.min(0,y0);}
    if(x1===x0){x0-=1;x1+=1;}
    if(y1===y0){const d=Math.abs(y0)||1;y0-=0.1*d;y1+=0.1*d;}
    const yr=y1-y0;y0-=0.05*yr;y1+=0.05*yr;
    const X=v=>pad.l+(v-x0)/(x1-x0)*(w-pad.l-pad.r),Y=v=>h-pad.b-(v-y0)/(y1-y0)*(h-pad.t-pad.b);
    g.strokeStyle='#e5edf2';g.lineWidth=1;g.textAlign='right';g.textBaseline='middle';
    for(let k=0;k<=4;k++){
      const v=y0+(y1-y0)*k/4,py=Y(v);
      g.beginPath();g.moveTo(pad.l,py);g.lineTo(w-pad.r,py);g.stroke();
      g.fillText(log?(10**v).toExponential(1):fmt(v,3),pad.l-6,py);
    }
    g.textAlign='center';g.textBaseline='top';
    for(let k=0;k<=5;k++){const v=x0+(x1-x0)*k/5;g.fillText(bars?String(Math.round(v)):fmt(v,3),X(v),h-pad.b+6);}
    g.fillText(xLabel,(pad.l+w-pad.r)/2,h-14);
    g.save();g.translate(12,(pad.t+h-pad.b)/2);g.rotate(-Math.PI/2);g.fillText(unit?`(${unit})`:'',0,0);g.restore();
    g.strokeStyle='#9fb3bf';g.beginPath();g.moveTo(pad.l,pad.t);g.lineTo(pad.l,h-pad.b);g.lineTo(w-pad.r,h-pad.b);g.stroke();
    series.forEach((s,k)=>{
      const color=s.color||PALETTE[k%PALETTE.length];g.strokeStyle=color;g.fillStyle=color;g.lineWidth=1.6;
      if(bars){
        const width=Math.max(2,(X(1)-X(0))*0.8/series.length);
        s.x.forEach((v,i)=>{const y=s.y[i];if(!Number.isFinite(y))return;const left=X(v)-width*series.length/2+k*width;g.fillRect(left,Y(Math.max(0,y)),width-1,Math.abs(Y(y)-Y(0)));});
      }else{
        g.beginPath();let started=false;
        s.x.forEach((v,i)=>{let y=s.y[i];if(!Number.isFinite(v)||!Number.isFinite(y)||(log&&!(y>0))){started=false;return;}if(log)y=Math.log10(y);
          if(started)g.lineTo(X(v),Y(y));else{g.moveTo(X(v),Y(y));started=true;}});
        g.stroke();
      }
      if(legend[k]){g.textAlign='left';g.textBaseline='middle';const {x:lx,y:ly}=legend[k];g.fillRect(lx,ly-1,14,3);g.fillStyle='#476071';g.fillText(s.label,lx+18,ly);}
    });
    if(marker!=null&&Number.isFinite(marker)&&marker>=x0&&marker<=x1){g.strokeStyle='#d9480f';g.setLineDash([4,3]);g.beginPath();g.moveTo(X(marker),pad.t);g.lineTo(X(marker),h-pad.b);g.stroke();g.setLineDash([]);}
  }

  function modeRows(summary){
    if(!summary?.modes)return [];
    const dims=summary.dimension===2?2:3;
    const totals=[0,1,2].map(d=>summary.meta?.totalEffectiveMass?.[d]||summary.meta?.mass||0);
    const cumulative=[0,0,0];
    return summary.modes.map(m=>{
      const ratio=[0,1,2].map(d=>totals[d]>0&&m.effectiveMass?m.effectiveMass[d]/totals[d]*100:NaN);
      ratio.forEach((r,d)=>{if(Number.isFinite(r))cumulative[d]+=r;});
      return {mode:m.mode,rigid:m.rigid,frequency:m.frequency,period:m.period,ratio:ratio.slice(0,dims),cumulative:cumulative.slice(0,dims)};
    });
  }

  function runInfo(summary){
    if(!summary)return '';
    const s=summary.settings,m=summary.meta||{};
    const lines=[`${ANALYSIS_NAMES[summary.analysis]} · ${summary.solver} · ${summary.frames.length} 帧 · CPU 线程 ${summary.cpuThreads??'—'}`,
      `模型：${(m.nodes??summary.nodeCount).toLocaleString()} 节点 · ${(m.elements??0).toLocaleString()} 单元 · 质量 ${fmt(m.mass,4)} kg${summary.dimension===2?'/m':''}`];
    if(m.elementType)lines.push(`求解单元：${m.elementType}${m.quadratic?'（二次单元）':''}${summary.dimension===2?` · ${m.plane==='strain'?'平面应变':'平面应力'}，单层楔形单元 t = ${fmt(m.sectionThickness,3)} m`:''}`);
    if(summary.analysis==='modal'){
      const elastic=(summary.modes||[]).filter(x=>!x.rigid);
      lines.push(`弹性模态 ${elastic.length} 阶${m.rigidModes?` · 约束不足，另含刚体模态 ${(summary.modes||[]).length-elastic.length} 阶`:''}${elastic[0]?` · 基频 ${fmt(elastic[0].frequency,5)} Hz`:''}`);
    }
    if(summary.analysis==='harmonic')lines.push(`扫频 ${s.freqMin}–${s.freqMax} Hz · 模态阻尼比 ζ = ${s.dampingRatio} · 叠加 ${(summary.modes||[]).length} 阶模态`);
    if(summary.analysis==='transient')lines.push(`${s.transientMethod==='direct'?'直接积分':`模态叠加（${(summary.modes||[]).length||s.transientModes} 阶）`} · 时长 ${s.endTime} s · Δt = ${fmt(m.timeStep??s.timeStep,6)} s（${m.steps} 步） · 载荷：${LOAD_SHAPES[s.load?.shape]||''} · 瑞利阻尼 α = ${s.rayleighAlpha}，β = ${s.rayleighBeta}`);
    if(summary.analysis==='explicit'){
      lines.push(`时长 ${s.explicitEndTime} s · 部件 ${m.parts} 个 · 接触对 ${m.contacts} · 刚性墙 ${(m.walls||[]).length} 个${m.cycles?` · ${m.cycles.toLocaleString()} 个循环`:''}`);
      lines.push(`时间步估计 ${fmt(m.timeStepEstimate,3)} s · 最小单元边长 ${fmt(m.minEdge,3)} m · 纵波速 ${fmt(m.waveSpeed,4)} m/s${m.slabThickness?` · 平面应变薄片厚 ${fmt(m.slabThickness,3)} m`:''}`);
      if(m.minTimeStep>0)lines.push(`质量缩放：最小时间步 ${fmt(m.minTimeStep,3)} s${Number.isFinite(m.addedMassPercent)?`，附加质量 ${m.addedMassPercent.toFixed(2)}%`:''}`);
      if(m.addedMassPercent>5)lines.push('注意：附加质量超过 5%，惯性被明显放大，冲击响应失真；请减小最小时间步或加粗网格。');
      for(const b of m.bodies||[])if(b.velocity.some(v=>v!==0))lines.push(`部件 ${b.part}：初速度 (${b.velocity.map(v=>fmt(v,4)).join(', ')}) m/s`);
      for(const mat of m.materials||[])lines.push(`材料 ${mat.name}：${mat.label}`);
      if(summary.history?.kinetic){
        const ke=summary.history.kinetic.y,ie=summary.history.internal?.y||[];
        lines.push(`动能 ${fmt(ke[0],4)} → ${fmt(ke.at(-1),4)} J · 内能 ${fmt(ie.at(-1),4)} J${summary.dimension===2?'（单位厚度）':''}`);
      }
    }
    if(summary.termination)lines.push(summary.termination.message);
    lines.push(`计算用时 ${(summary.elapsedMs/1000).toFixed(1)} s · 任务 ${summary.runId}`);
    return lines.filter(Boolean).join('\n');
  }

  // Parts of a mesh (connected pieces) with their node count and centroid.
  function parts(elements,nodes){
    const c=root.DynamicsSettings.components(elements,nodes.length);
    const list=Array.from({length:c.count},(_,k)=>({part:k+1,nodes:0,center:[0,0,0]}));
    nodes.forEach((p,i)=>{const k=c.nodePart[i];if(k<0)return;const e=list[k];e.nodes++;for(let d=0;d<3;d++)e.center[d]+=p[d]||0;});
    for(const e of list)e.center=e.center.map(v=>v/Math.max(1,e.nodes));
    return {list,nodePart:c.nodePart,elementPart:c.elementPart};
  }

  root.DynamicsUI={FIELD_LABELS,UNITS,ANALYSIS_NAMES,PHASES,LOAD_SHAPES,fmt,fieldLabel,frameLabel,axisLabel,readStream,progressValue,progressText,
    loadFrame,loadProbe,curves,drawChart,modeRows,runInfo,parts,harmonicDisplacement,PALETTE};
})(typeof window!=='undefined'?window:globalThis);
