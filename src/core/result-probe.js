// Point probes for result viewers: locate a point in a TRI3 / TET4 mesh, read
// interpolated values, and show current values and time / increment histories.
// The geometry helpers have no DOM dependency so that Node tests can load them.
(function(root){
  'use strict';
  const EPS=1e-9;

  // ------------------------------------------------------------ geometry
  // Barycentric weights of p in triangle (a,b,c); points are {x,y}.
  function triangleWeights(p,a,b,c){
    const det=(b.y-c.y)*(a.x-c.x)+(c.x-b.x)*(a.y-c.y);
    if(!Number.isFinite(det)||Math.abs(det)<1e-300)return null;
    const w0=((b.y-c.y)*(p.x-c.x)+(c.x-b.x)*(p.y-c.y))/det;
    const w1=((c.y-a.y)*(p.x-c.x)+(a.x-c.x)*(p.y-c.y))/det;
    return [w0,w1,1-w0-w1];
  }
  const inside=(weights,tolerance)=>weights&&weights.every(w=>w>=-tolerance);
  const clampWeights=weights=>{
    const clipped=weights.map(w=>Math.max(0,w)),sum=clipped.reduce((a,b)=>a+b,0)||1;
    return clipped.map(w=>w/sum);
  };
  // elements: [{nodes:[n0,n1,n2]}]; position(node) gives the configuration used for the search.
  function locateTriangle(elements,point,position=node=>node,tolerance=1e-7){
    let best=null;
    for(let i=0;i<elements.length;i++){
      const nodes=elements[i].nodes;if(!nodes||nodes.length!==3)continue;
      const a=position(nodes[0]),b=position(nodes[1]),c=position(nodes[2]);
      if(point.x<Math.min(a.x,b.x,c.x)-EPS||point.x>Math.max(a.x,b.x,c.x)+EPS||point.y<Math.min(a.y,b.y,c.y)-EPS||point.y>Math.max(a.y,b.y,c.y)+EPS)continue;
      const weights=triangleWeights(point,a,b,c);
      if(!weights)continue;
      const worst=Math.min(...weights);
      if(worst>=0)return {element:elements[i],index:i,weights};
      if(worst>=-tolerance&&(!best||worst>best.worst))best={element:elements[i],index:i,weights,worst};
    }
    return best?{element:best.element,index:best.index,weights:clampWeights(best.weights)}:null;
  }
  function nearestNode(nodes,point,position=node=>node){
    let best=null;
    for(let i=0;i<nodes.length;i++){
      const p=position(nodes[i]),d=Math.hypot(p.x-point.x,p.y-point.y);
      if(!best||d<best.distance)best={node:nodes[i],index:i,distance:d};
    }
    return best;
  }
  // Barycentric weights of p in tetrahedron (a,b,c,d); points are [x,y,z].
  function tetWeights(p,a,b,c,d){
    const m=[b[0]-a[0],c[0]-a[0],d[0]-a[0],b[1]-a[1],c[1]-a[1],d[1]-a[1],b[2]-a[2],c[2]-a[2],d[2]-a[2]];
    const det=m[0]*(m[4]*m[8]-m[5]*m[7])-m[1]*(m[3]*m[8]-m[5]*m[6])+m[2]*(m[3]*m[7]-m[4]*m[6]);
    if(!Number.isFinite(det)||Math.abs(det)<1e-300)return null;
    const r=[p[0]-a[0],p[1]-a[1],p[2]-a[2]];
    const w1=(r[0]*(m[4]*m[8]-m[5]*m[7])-m[1]*(r[1]*m[8]-m[5]*r[2])+m[2]*(r[1]*m[7]-m[4]*r[2]))/det;
    const w2=(m[0]*(r[1]*m[8]-m[5]*r[2])-r[0]*(m[3]*m[8]-m[5]*m[6])+m[2]*(m[3]*r[2]-r[1]*m[6]))/det;
    const w3=(m[0]*(m[4]*r[2]-r[1]*m[7])-m[1]*(m[3]*r[2]-r[1]*m[6])+r[0]*(m[3]*m[7]-m[4]*m[6]))/det;
    return [1-w1-w2-w3,w1,w2,w3];
  }
  // nodes: [[x,y,z]], tets: [[a,b,c,d]]; skip(index) excludes hidden volumes.
  function locateTet(nodes,tets,point,{skip,tolerance=1e-7}={}){
    let best=null;
    for(let i=0;i<tets.length;i++){
      if(skip?.(i))continue;
      const t=tets[i],a=nodes[t[0]],b=nodes[t[1]],c=nodes[t[2]],d=nodes[t[3]];
      let out=false;
      for(let k=0;k<3&&!out;k++){
        const lo=Math.min(a[k],b[k],c[k],d[k]),hi=Math.max(a[k],b[k],c[k],d[k]);
        out=point[k]<lo-EPS*(1+Math.abs(lo))||point[k]>hi+EPS*(1+Math.abs(hi));
      }
      if(out)continue;
      const weights=tetWeights(point,a,b,c,d);if(!weights)continue;
      const worst=Math.min(...weights);
      if(worst>=0)return {tet:i,ids:[...t],weights};
      if(worst>=-tolerance&&(!best||worst>best.worst))best={tet:i,ids:[...t],weights,worst};
    }
    return best?{tet:best.tet,ids:best.ids,weights:clampWeights(best.weights)}:null;
  }
  function nearestNode3(nodes,point,allowed){
    let best=null;
    const visit=i=>{const p=nodes[i],d=Math.hypot(p[0]-point[0],p[1]-point[1],p[2]-point[2]);if(!best||d<best.distance)best={index:i,distance:d};};
    if(allowed)for(const i of allowed)visit(i);else for(let i=0;i<nodes.length;i++)visit(i);
    return best;
  }
  const interpolate=(values,ids,weights)=>{let sum=0;for(let i=0;i<ids.length;i++)sum+=weights[i]*(Number(values[ids[i]])||0);return sum;};

  // ------------------------------------------------------------ mechanics
  function principal2d(sx,sy,txy){
    const center=(sx+sy)/2,radius=Math.hypot((sx-sy)/2,txy);
    return [center+radius,center-radius];
  }
  const vonMises=(sx,sy,sz,sxy,syz,szx)=>Math.sqrt(Math.max(0,((sx-sy)**2+(sy-sz)**2+(sz-sx)**2)/2+3*(sxy*sxy+syz*syz+szx*szx)));
  const equivalentStrain=(ex,ey,ez,exy,eyz,ezx)=>Math.sqrt(Math.max(0,2*((ex-ey)**2+(ey-ez)**2+(ez-ex)**2)/9+4*(exy*exy+eyz*eyz+ezx*ezx)/3));

  // ------------------------------------------------------------ formatting
  function formatValue(value){
    if(value==null||value==='')return '—';
    if(typeof value==='string')return value;
    if(!Number.isFinite(value))return String(value);
    if(value===0)return '0';
    const magnitude=Math.abs(value);
    if(magnitude>=1e-3&&magnitude<1e5)return String(Number(value.toPrecision(6)));
    return value.toExponential(4);
  }
  // Compact axis labels: 6e+6, 2.5e-5, 0.125.
  function formatTick(value){
    if(value===0)return '0';
    const magnitude=Math.abs(value);
    if(magnitude>=1e-3&&magnitude<1e4)return String(Number(value.toPrecision(4)));
    const [mantissa,exponent]=value.toExponential(2).split('e');
    return `${Number(mantissa)}e${Number(exponent)}`;
  }
  const csvCell=value=>{
    const text=typeof value==='number'?(Number.isFinite(value)?String(value):''):String(value??'');
    return /[",\n\r]/.test(text)?'"'+text.replace(/"/g,'""')+'"':text;
  };
  const csvText=rows=>'﻿'+rows.map(row=>row.map(csvCell).join(',')).join('\r\n')+'\r\n';
  const quantityHeader=q=>q.unit&&q.unit!=='1'?`${q.label} (${q.unit})`:q.label;
  function historyRows(probes,history,quantities){
    const header=['帧',...history.axes.map(axis=>axis.unit?`${axis.label} (${axis.unit})`:axis.label)];
    for(const probe of probes)for(const q of quantities)header.push(`${probe.label} ${quantityHeader(q)}`);
    const rows=[header];
    for(let i=0;i<history.axes[0].values.length;i++){
      const row=[i,...history.axes.map(axis=>axis.values[i])];
      probes.forEach((probe,p)=>{for(const q of quantities)row.push(history.series[p]?.[q.key]?.[i]);});
      rows.push(row);
    }
    return rows;
  }

  // ------------------------------------------------------------ chart
  const COLORS=['#d9480f','#1c7ed6','#2b8a3e','#ae3ec9','#f08c00','#0c8599','#c2255c','#5c940d'];
  const probeColor=index=>COLORS[index%COLORS.length];
  function niceTicks(min,max,count=5){
    if(!(max>min)){const pad=Math.abs(min)*.1||1;min-=pad;max+=pad;}
    const raw=(max-min)/count,power=10**Math.floor(Math.log10(raw)),step=[1,2,2.5,5,10].map(f=>f*power).find(s=>s>=raw)||raw;
    const ticks=[];for(let v=Math.ceil(min/step)*step;v<=max+step*1e-9;v+=step)ticks.push(Math.abs(v)<step*1e-9?0:v);
    return {min:Math.min(min,ticks[0]??min),max:Math.max(max,ticks.at(-1)??max),ticks};
  }
  function chartLayout(canvas,x,series){
    const width=canvas.clientWidth||canvas.width,height=canvas.clientHeight||canvas.height;
    const area={left:60,right:width-10,top:10,bottom:height-30};
    let xmin=Infinity,xmax=-Infinity,ymin=Infinity,ymax=-Infinity;
    for(const v of x)if(Number.isFinite(v)){xmin=Math.min(xmin,v);xmax=Math.max(xmax,v);}
    for(const s of series)for(const v of s.values)if(Number.isFinite(v)){ymin=Math.min(ymin,v);ymax=Math.max(ymax,v);}
    if(xmin===Infinity){xmin=0;xmax=1;}if(ymin===Infinity){ymin=0;ymax=1;}
    if(xmax===xmin)xmax=xmin+1;
    const yt=niceTicks(ymin,ymax),xt=niceTicks(xmin,xmax);
    const sx=v=>area.left+(v-xmin)/(xmax-xmin)*(area.right-area.left),sy=v=>area.bottom-(v-yt.min)/(yt.max-yt.min)*(area.bottom-area.top);
    return {width,height,area,xmin,xmax,yt,xt,sx,sy};
  }
  function drawChart(canvas,{x=[],series=[],xLabel='',yLabel='',current=-1,hover=-1}={}){
    const dpr=root.devicePixelRatio||1,layout=chartLayout(canvas,x,series),{width,height,area,sx,sy,yt,xt}=layout;
    if(!width||!height)return layout;
    canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);
    const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);
    ctx.clearRect(0,0,width,height);ctx.fillStyle='#ffffff';ctx.fillRect(0,0,width,height);
    ctx.font='10px Segoe UI, Arial, sans-serif';ctx.strokeStyle='#e3e9ee';ctx.fillStyle='#5b6b78';ctx.lineWidth=1;
    ctx.textAlign='right';ctx.textBaseline='middle';
    for(const v of yt.ticks){const y=sy(v);ctx.beginPath();ctx.moveTo(area.left,y);ctx.lineTo(area.right,y);ctx.stroke();ctx.fillText(formatTick(v),area.left-4,y);}
    ctx.textAlign='center';ctx.textBaseline='top';
    for(const v of xt.ticks){if(v<layout.xmin-1e-12||v>layout.xmax+1e-12)continue;const px=sx(v);ctx.beginPath();ctx.moveTo(px,area.top);ctx.lineTo(px,area.bottom);ctx.stroke();ctx.fillText(formatTick(v),px,area.bottom+3);}
    ctx.strokeStyle='#8a9aa6';ctx.strokeRect(area.left,area.top,area.right-area.left,area.bottom-area.top);
    if(xLabel){ctx.fillStyle='#34495e';ctx.textBaseline='bottom';ctx.fillText(xLabel,(area.left+area.right)/2,height-1);}
    if(yLabel){ctx.save();ctx.translate(8,(area.top+area.bottom)/2);ctx.rotate(-Math.PI/2);ctx.textBaseline='middle';ctx.fillStyle='#34495e';ctx.fillText(yLabel,0,0);ctx.restore();}
    ctx.save();ctx.beginPath();ctx.rect(area.left,area.top,area.right-area.left,area.bottom-area.top);ctx.clip();
    if(current>=0&&Number.isFinite(x[current])){ctx.strokeStyle='#495057';ctx.setLineDash([4,3]);ctx.beginPath();ctx.moveTo(sx(x[current]),area.top);ctx.lineTo(sx(x[current]),area.bottom);ctx.stroke();ctx.setLineDash([]);}
    for(const s of series){
      ctx.strokeStyle=s.color;ctx.lineWidth=1.7;ctx.beginPath();let open=false;
      s.values.forEach((v,i)=>{if(!Number.isFinite(v)||!Number.isFinite(x[i])){open=false;return;}const px=sx(x[i]),py=sy(v);if(open)ctx.lineTo(px,py);else{ctx.moveTo(px,py);open=true;}});
      ctx.stroke();
      if(s.values.length<=80){ctx.fillStyle=s.color;s.values.forEach((v,i)=>{if(Number.isFinite(v)&&Number.isFinite(x[i])){ctx.beginPath();ctx.arc(sx(x[i]),sy(v),1.8,0,Math.PI*2);ctx.fill();}});}
      const marker=hover>=0?hover:current;
      if(marker>=0&&Number.isFinite(s.values[marker])&&Number.isFinite(x[marker])){ctx.fillStyle='#fff';ctx.strokeStyle=s.color;ctx.lineWidth=2;ctx.beginPath();ctx.arc(sx(x[marker]),sy(s.values[marker]),3.5,0,Math.PI*2);ctx.fill();ctx.stroke();}
    }
    if(hover>=0&&Number.isFinite(x[hover])){ctx.strokeStyle='rgba(73,80,87,.45)';ctx.beginPath();ctx.moveTo(sx(x[hover]),area.top);ctx.lineTo(sx(x[hover]),area.bottom);ctx.stroke();}
    ctx.restore();
    return layout;
  }
  function nearestIndex(layout,x,pixelX){
    let best=-1,distance=Infinity;
    x.forEach((v,i)=>{if(!Number.isFinite(v))return;const d=Math.abs(layout.sx(v)-pixelX);if(d<distance){distance=d;best=i;}});
    return best;
  }

  // ------------------------------------------------------------ panel UI
  function element(tag,props={},children=[]){
    const node=document.createElement(tag);
    for(const [key,value] of Object.entries(props)){
      if(key==='class')node.className=value;else if(key==='text')node.textContent=value;
      else if(key in node&&!key.includes('-'))node[key]=value;else node.setAttribute(key,value);
    }
    for(const child of [].concat(children))if(child!=null)node.append(child);
    return node;
  }
  const t=text=>typeof root.uiText==='function'?root.uiText(text):text;
  function createStore(){return {items:[],next:1};}

  // options: root, dimension, store, quantities(), locate(coords,{snap,fromClick}), evaluate(probe),
  // history(probes,{signal}) -> {axes:[{key,label,unit,values}],series:[{key:[...]}]}, historyKey(),
  // currentIndex(), selectIndex(i), changed(), exportName
  function createPanel(options){
    const dim=options.dimension===3?3:2,axes=dim===3?['X','Y','Z']:['X','Y'];
    let store=options.store||createStore();
    let history=null,historyKey='',historyController=null,hover=-1,lastLayout=null,historyQuantity='',historyAxis=0;
    const coordinateInputs=axes.map(axis=>element('input',{type:'number',step:'any','aria-label':`测点 ${axis} (m)`}));
    const pick=element('input',{type:'checkbox',checked:true});
    const snap=element('input',{type:'checkbox'});
    const addButton=element('button',{type:'button',text:'添加测点'});
    const clearButton=element('button',{type:'button',text:'清除全部测点'});
    const exportButton=element('button',{type:'button',text:'导出当前值 CSV'});
    const message=element('p',{class:'probe-message',role:'status'});
    const table=element('div',{class:'probe-table-wrap'});
    const note=element('p',{class:'probe-note'});
    const quantitySelect=element('select',{'aria-label':'曲线物理量'});
    const axisSelect=element('select',{'aria-label':'曲线横轴'});
    const canvas=element('canvas',{class:'probe-chart','aria-label':'测点时程曲线'});
    const historyStatus=element('p',{class:'probe-message',role:'status'});
    const historyTable=element('div',{class:'probe-table-wrap probe-history-table'});
    const historyExport=element('button',{type:'button',text:'导出时程 CSV'});
    const readout=element('p',{class:'probe-readout'});
    const historyDetails=element('details',{class:'probe-history-values'},[element('summary',{text:'逐帧数值'}),historyTable]);
    const historySection=element('div',{class:'probe-history'},[
      element('h3',{text:options.historyTitle||'时程曲线'}),
      element('div',{class:'probe-history-controls'},[element('label',{},[element('span',{text:'物理量'}),quantitySelect]),element('label',{},[element('span',{text:'横轴'}),axisSelect])]),
      canvas,readout,historyStatus,historyDetails,element('div',{class:'probe-actions'},[historyExport])
    ]);
    historySection.hidden=true;
    const body=element('div',{class:'result-probe'},[
      element('p',{class:'probe-hint',text:dim===3?'单击模型表面或输入坐标，读取该点的插值结果。':'单击云图或输入坐标，读取该点的结果数值。'}),
      element('div',{class:`probe-coordinates probe-coordinates-${dim}`},[...coordinateInputs.map((input,i)=>element('label',{},[element('span',{text:`${axes[i]} (m)`}),input])),addButton]),
      element('label',{class:'probe-check'},[pick,element('span',{text:'单击视窗拾取测点'})]),
      element('label',{class:'probe-check'},[snap,element('span',{text:'吸附到最近节点'})]),
      message,table,note,
      element('div',{class:'probe-actions'},[clearButton,exportButton]),
      historySection
    ]);
    options.root.replaceChildren(body);

    const setMessage=(text,error=false)=>{message.textContent=text||'';message.classList.toggle('error',Boolean(error));};
    const quantities=()=>(options.quantities?.()||[]);
    function evaluateAll(){return store.items.map(probe=>{try{return options.evaluate(probe)||null;}catch{return null;}});}
    function renderTable(){
      table.replaceChildren();
      note.textContent=store.items.length?options.note?.()||'':'';
      exportButton.disabled=clearButton.disabled=!store.items.length;
      if(!store.items.length){table.append(element('p',{class:'probe-empty',text:'尚未添加测点。'}));return;}
      const results=evaluateAll(),list=quantities();
      const head=element('tr',{},[element('th',{text:'物理量'})]);
      store.items.forEach((probe,i)=>{
        const remove=element('button',{type:'button',class:'probe-remove',text:'×',title:'删除测点','aria-label':`删除测点 ${probe.label}`});
        remove.addEventListener('click',()=>removeProbe(probe.id));
        head.append(element('th',{},[element('span',{class:'probe-swatch',style:`background:${probeColor(i)}`}),probe.label,remove]));
      });
      const rows=[head];
      const infoRow=(label,read)=>{const row=element('tr',{class:'probe-info'},[element('th',{text:label})]);store.items.forEach((probe,i)=>row.append(element('td',{text:read(probe,results[i])})));return row;};
      rows.push(infoRow('坐标 (m)',probe=>probe.point.map(v=>formatValue(v)).join(', ')));
      if(store.items.some(probe=>probe.where))rows.push(infoRow('位置',probe=>probe.where||'—'));
      if(results.some(result=>result?.info))rows.push(infoRow(options.infoLabel||'说明',(probe,result)=>result?.info||'—'));
      for(const q of list){
        if(!results.some(result=>result?.values&&result.values[q.key]!=null))continue;
        const row=element('tr',{},[element('th',{text:q.label,title:q.unit&&q.unit!=='1'?q.unit:''},q.unit&&q.unit!=='1'?[element('small',{text:` ${q.unit}`})]:[])]);
        results.forEach(result=>row.append(element('td',{text:formatValue(result?.values?.[q.key])})));
        rows.push(row);
      }
      if(!results.some(Boolean))rows.push(element('tr',{},[element('td',{colspan:String(store.items.length+1),text:'当前没有可读取的结果。'})]));
      table.append(element('table',{class:'probe-table'},rows));
    }
    function markersChanged(){options.changed?.();}
    function removeProbe(id){store.items=store.items.filter(probe=>probe.id!==id);invalidateHistory();renderAll();markersChanged();}
    function addProbe(probe){
      if(store.items.length>=8){setMessage('最多保留 8 个测点，请先删除不需要的测点。',true);return false;}
      const item={...probe,id:store.next,label:'P'+store.next};store.next++;
      store.items.push(item);invalidateHistory();renderAll();markersChanged();
      setMessage(probe.message||'');
      return item;
    }
    function addAt(coords,context={}){
      try{
        const located=options.locate(coords,{snap:snap.checked,...context});
        if(!located)return null;
        coordinateInputs.forEach((input,i)=>{input.value=String(Number(located.point[i].toPrecision(10)));});
        return addProbe(located);
      }catch(error){setMessage(t(error.message),true);return null;}
    }
    function invalidateHistory(){historyController?.abort();historyController=null;history=null;historyKey='';}
    function updateHistoryControls(list){
      const previous=quantitySelect.value||historyQuantity;
      quantitySelect.replaceChildren(...list.map(q=>new Option(quantityHeader(q),q.key)));
      if(list.some(q=>q.key===previous))quantitySelect.value=previous;
      historyQuantity=quantitySelect.value;
      const previousAxis=axisSelect.value;
      axisSelect.replaceChildren(...(history?.axes||[]).map((axis,i)=>new Option(axis.unit?`${axis.label} (${axis.unit})`:axis.label,String(i))));
      if([...axisSelect.options].some(option=>option.value===previousAxis))axisSelect.value=previousAxis;
      historyAxis=Number(axisSelect.value)||0;
      axisSelect.parentElement.hidden=(history?.axes||[]).length<2;
    }
    function historyQuantities(){
      if(!history)return [];
      return quantities().filter(q=>history.series.some(series=>series?.[q.key]?.some(Number.isFinite)));
    }
    function renderChart(){
      if(historySection.hidden||!history){canvas.hidden=true;readout.textContent='';return;}
      canvas.hidden=false;
      const q=quantities().find(item=>item.key===quantitySelect.value),axis=history.axes[historyAxis]||history.axes[0];
      const x=axis.values,series=store.items.map((probe,i)=>({label:probe.label,color:probeColor(i),values:history.series[i]?.[q?.key]||[]}));
      const current=options.currentIndex?.()??-1;
      lastLayout=drawChart(canvas,{x,series,xLabel:t(axis.unit?`${axis.label} (${axis.unit})`:axis.label),yLabel:q?t(quantityHeader(q)):'',current,hover});
      const index=hover>=0?hover:current;
      readout.textContent=index>=0&&q?`${t(axis.label)} = ${formatValue(x[index])}${axis.unit?' '+axis.unit:''} · `+series.map(s=>`${s.label} = ${formatValue(s.values[index])}`).join(' · '):'';
    }
    function renderHistoryTable(){
      historyTable.replaceChildren();
      if(!history||!historyDetails.open)return;
      const q=quantities().find(item=>item.key===quantitySelect.value);if(!q)return;
      const current=options.currentIndex?.()??-1;
      const head=element('tr',{},[element('th',{text:'帧'}),...history.axes.map(axis=>element('th',{text:axis.unit?`${axis.label} (${axis.unit})`:axis.label})),...store.items.map(probe=>element('th',{text:probe.label}))]);
      const rows=[head];
      for(let i=0;i<history.axes[0].values.length;i++){
        const row=element('tr',{class:i===current?'current':''},[element('td',{text:String(i+1)}),...history.axes.map(axis=>element('td',{text:formatValue(axis.values[i])})),...store.items.map((_,p)=>element('td',{text:formatValue(history.series[p]?.[q.key]?.[i])}))]);
        row.addEventListener('click',()=>options.selectIndex?.(i));
        rows.push(row);
      }
      historyTable.append(element('table',{class:'probe-table'},rows));
    }
    async function loadHistory(){
      const supported=Boolean(options.history)&&(options.historyAvailable?.()??true);
      historySection.hidden=!supported||!store.items.length;
      historyExport.disabled=true;
      if(historySection.hidden){invalidateHistory();return;}
      const key=store.items.map(probe=>probe.id).join(',')+'|'+(options.historyKey?.()||'');
      if(key===historyKey&&(history||historyController))return;
      invalidateHistory();historyKey=key;
      const controller=new AbortController();historyController=controller;
      historyStatus.textContent=t('正在读取测点时程…');canvas.hidden=true;
      try{
        const result=await options.history(store.items.slice(),{signal:controller.signal,progress:fraction=>{if(historyController===controller)historyStatus.textContent=t('正在读取测点时程…')+` ${Math.round(fraction*100)}%`;}});
        if(historyController!==controller)return;
        history=result;historyController=null;historyStatus.textContent='';
        updateHistoryControls(historyQuantities());historyExport.disabled=!history;
        renderChart();renderHistoryTable();
      }catch(error){
        if(controller.signal.aborted||historyController!==controller)return;
        historyController=null;history=null;historyStatus.textContent=t(error.message||'测点时程读取失败。');
      }
    }
    function renderAll(){renderTable();loadHistory();if(history){updateHistoryControls(historyQuantities());renderChart();renderHistoryTable();}}
    async function save(name,rows){
      try{
        if(typeof root.chooseExportFile!=='function')throw Error('当前环境不支持选择保存位置，请使用启动器打开程序。');
        const handle=await root.chooseExportFile(t(name),'text/csv','.csv');if(!handle)return;
        await root.writeExportFile(handle,writer=>writer.write(csvText(rows.map(row=>row.map(cell=>typeof cell==='string'?t(cell):cell)))));
        setMessage(t('已导出 CSV。'));
      }catch(error){setMessage(t(error.message),true);}
    }
    addButton.addEventListener('click',()=>{
      const coords=coordinateInputs.map(input=>input.value.trim()===''?NaN:Number(input.value));
      if(coords.some(v=>!Number.isFinite(v))){setMessage(t('请输入完整的测点坐标。'),true);return;}
      addAt(coords);
    });
    for(const input of coordinateInputs)input.addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();addButton.click();}});
    clearButton.addEventListener('click',()=>{store.items=[];invalidateHistory();renderAll();markersChanged();setMessage('');});
    exportButton.addEventListener('click',()=>{
      const results=evaluateAll(),list=quantities().filter(q=>results.some(r=>r?.values?.[q.key]!=null));
      const rows=[['测点',...axes.map(axis=>`${axis} (m)`),'位置',...list.map(quantityHeader)]];
      store.items.forEach((probe,i)=>rows.push([probe.label,...probe.point,probe.where||'',...list.map(q=>results[i]?.values?.[q.key])]));
      save((options.exportName||'测点结果')+'.csv',rows);
    });
    historyExport.addEventListener('click',()=>{if(history)save((options.exportName||'测点结果')+'-时程.csv',historyRows(store.items,history,historyQuantities()));});
    quantitySelect.addEventListener('change',()=>{historyQuantity=quantitySelect.value;renderChart();renderHistoryTable();});
    axisSelect.addEventListener('change',()=>{historyAxis=Number(axisSelect.value)||0;renderChart();});
    historyDetails.addEventListener('toggle',renderHistoryTable);
    canvas.addEventListener('pointermove',event=>{
      if(!history||!lastLayout)return;const box=canvas.getBoundingClientRect();
      const axis=history.axes[historyAxis]||history.axes[0],next=nearestIndex(lastLayout,axis.values,event.clientX-box.left);
      if(next!==hover){hover=next;renderChart();}
    });
    canvas.addEventListener('pointerleave',()=>{hover=-1;renderChart();});
    canvas.addEventListener('click',event=>{
      if(!history||!lastLayout)return;const box=canvas.getBoundingClientRect();
      const axis=history.axes[historyAxis]||history.axes[0],index=nearestIndex(lastLayout,axis.values,event.clientX-box.left);
      if(index>=0)options.selectIndex?.(index);
    });
    if(typeof ResizeObserver==='function')new ResizeObserver(()=>renderChart()).observe(canvas);
    root.addEventListener?.('femlanguagechange',()=>{renderTable();if(history){updateHistoryControls(historyQuantities());renderChart();renderHistoryTable();}});
    renderAll();
    return {
      // Re-read current values (frame change, field change).
      refresh(){renderTable();loadHistory();renderChart();if(historyDetails.open)renderHistoryTable();},
      resetHistory(){invalidateHistory();renderAll();},
      clear(){store.items=[];invalidateHistory();renderAll();setMessage('');},
      setStore(next){if(next===store)return;store=next;invalidateHistory();renderAll();setMessage('');},
      store:()=>store,
      probes:()=>store.items,
      pickEnabled:()=>pick.checked,
      addAt,
      setMessage(text,error){setMessage(t(text),error);},
      color:index=>probeColor(index)
    };
  }

  // Draw numbered probe markers on a 2D canvas; project(probe) returns screen {x,y} or null.
  function drawMarkers2d(ctx,probes,project){
    ctx.save();ctx.font='700 11px Segoe UI, Arial, sans-serif';ctx.textBaseline='bottom';ctx.textAlign='left';
    probes.forEach((probe,i)=>{
      const p=project(probe);if(!p||!Number.isFinite(p.x)||!Number.isFinite(p.y))return;
      const color=probeColor(i);
      ctx.lineWidth=3;ctx.strokeStyle='#ffffff';ctx.beginPath();ctx.arc(p.x,p.y,5,0,Math.PI*2);ctx.stroke();
      ctx.lineWidth=1.8;ctx.strokeStyle=color;ctx.beginPath();ctx.arc(p.x,p.y,5,0,Math.PI*2);ctx.moveTo(p.x-9,p.y);ctx.lineTo(p.x+9,p.y);ctx.moveTo(p.x,p.y-9);ctx.lineTo(p.x,p.y+9);ctx.stroke();
      ctx.lineWidth=3;ctx.strokeStyle='#ffffff';ctx.strokeText(probe.label,p.x+7,p.y-5);ctx.fillStyle=color;ctx.fillText(probe.label,p.x+7,p.y-5);
    });
    ctx.restore();
  }

  const api={triangleWeights,locateTriangle,nearestNode,tetWeights,locateTet,nearestNode3,interpolate,principal2d,vonMises,equivalentStrain,
    formatValue,formatTick,csvText,historyRows,niceTicks,probeColor,createStore,createPanel,drawChart,drawMarkers2d};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.ResultProbe=api;
})(typeof window!=='undefined'?window:globalThis);
