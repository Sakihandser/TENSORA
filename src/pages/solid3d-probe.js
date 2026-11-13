// Point probes for the 3D result stages (statics, deformation, blast). A probe is
// a point in the undeformed mesh with linear (barycentric) weights on a surface
// triangle or a tetrahedron; its values interpolate the nodal result fields.
import * as THREE from '../vendor/three/three.module.js';
import { deformationProbeSeries } from './solid3d-deformation.js';

const RESULT_STAGES=['results','deformation-results','blast-results'];
const tensorKeys=['sxx','syy','szz','sxy','syz','sxz'],strainKeys=['exx','eyy','ezz','exy','eyz','exz'];

// Interpolate nodal fields with probe weights; derived magnitudes are recomputed
// from interpolated components rather than interpolated themselves.
export function probeValues(fields,probe){
  const P=window.ResultProbe,values={};
  for(const [key,array] of Object.entries(fields||{}))if(array?.length)values[key]=P.interpolate(array,probe.nodes,probe.weights);
  if(['ux','uy','uz'].every(key=>key in values))values.umag=Math.hypot(values.ux,values.uy,values.uz);
  if(['vx','vy','vz'].every(key=>key in values))values.vmag=Math.hypot(values.vx,values.vy,values.vz);
  if(tensorKeys.every(key=>key in values)&&'vm' in values)values.vm=P.vonMises(...tensorKeys.map(key=>values[key]));
  if(strainKeys.every(key=>key in values)&&'equivalentStrain' in values)values.equivalentStrain=P.equivalentStrain(...strainKeys.map(key=>values[key]));
  return values;
}

export function createSolidProbes(ctx){
  const P=window.ResultProbe;
  const stores=Object.fromEntries(RESULT_STAGES.map(stage=>[stage,P.createStore()]));
  let stage='home',lastPlotted=null,down=null;
  const labelTextures=new Map();
  const activeStore=()=>stores[stage]||stores.results;
  const fields=()=>ctx.plotted()?.nodeFields||null;

  function quantities(){
    const available=fields();
    const keys=available?Object.keys(available):[];
    const order=['ux','uy','uz','umag','vx','vy','vz','vmag',...tensorKeys,'s1','vm','pressure',...strainKeys,'e1','equivalentStrain','peeq','plasticStrain','damageInitiation','damageEvolution','damage','failureDamage','eroded'];
    return [...order.filter(key=>keys.includes(key)),...keys.filter(key=>!order.includes(key))]
      .map(key=>({key,label:ctx.fieldLabel(key)||key,unit:ctx.fieldUnit(key)}));
  }
  function describe(ids,weights,prefix){
    const strongest=ids[weights.indexOf(Math.max(...weights))];
    return prefix?`${prefix} · 节点 ${strongest}`:`节点 ${strongest}`;
  }
  function finish(ids,weights,snap,prefix,message='',exact=null){
    if(snap){const k=weights.indexOf(Math.max(...weights));weights=weights.map((_,i)=>i===k?1:0);}
    const nodes=ctx.mesh().nodes;
    const point=exact&&!snap?[...exact]:[0,1,2].map(axis=>ids.reduce((sum,id,i)=>sum+weights[i]*nodes[id][axis],0));
    return {point,nodes:ids,weights,snapped:weights.some(w=>w===1),where:describe(ids,weights,prefix),message};
  }
  function locate(coords,{snap=false,hit=null}={}){
    const mesh=ctx.mesh();
    if(!mesh||!ctx.plotted())throw Error('当前没有可读取的结果。');
    if(hit)return finish(hit.ids,hit.weights,snap,'表面');
    const hidden=ctx.hiddenVolumes(),skip=hidden.size?i=>hidden.has(String(mesh.tetVolumes?.[i])):undefined;
    const found=P.locateTet(mesh.nodes,mesh.tets,coords,{skip});
    if(found)return finish(found.ids,found.weights,snap,`四面体 ${found.tet}`,'',coords);
    if(!snap)throw Error('该点不在网格内。勾选“吸附到最近节点”可读取最近节点。');
    const near=P.nearestNode3(mesh.nodes,coords);
    return finish([near.index],[1],false,'',`该点不在网格内，已吸附到最近节点 ${near.index}（距离 ${P.formatValue(near.distance)} m）。`);
  }
  function evaluate(probe){
    const available=fields();
    if(!available)return null;
    return {values:probeValues(available,probe)};
  }
  async function history(probes,{signal}){
    const ids=[...new Set(probes.flatMap(probe=>probe.nodes))],index=new Map(ids.map((id,k)=>[id,k]));
    const combine=(perNode,count)=>probes.map(probe=>{
      const out={},keys=new Set(probe.nodes.flatMap(id=>Object.keys(perNode[index.get(id)])));
      for(const key of keys){
        const series=new Array(count);
        for(let f=0;f<count;f++)series[f]=probe.nodes.reduce((sum,id,i)=>sum+probe.weights[i]*(Number(perNode[index.get(id)][key]?.[f])||0),0);
        out[key]=series;
      }
      for(let f=0;f<count;f++){
        const at=key=>out[key]?.[f];
        if(out.ux&&out.uy&&out.uz)(out.umag||=new Array(count))[f]=Math.hypot(at('ux'),at('uy'),at('uz'));
        if(out.vx&&out.vy&&out.vz)(out.vmag||=new Array(count))[f]=Math.hypot(at('vx'),at('vy'),at('vz'));
        if(tensorKeys.every(key=>out[key]))(out.vm||=new Array(count))[f]=P.vonMises(...tensorKeys.map(at));
        if(strainKeys.every(key=>out[key]))(out.equivalentStrain||=new Array(count))[f]=P.equivalentStrain(...strainKeys.map(at));
      }
      return out;
    });
    if(stage==='deformation-results'){
      const run=ctx.deformationRun();if(!run)throw Error('请在损伤变形面板运行计算。');
      const series=combine(deformationProbeSeries(run,ids,ctx.deformationThresholds()),run.frames.length);
      const loadFactor=Number(run.settings?.loadFactor??1);
      return {axes:[{key:'load',label:'载荷比例',unit:'',values:run.frames.map(frame=>frame.time*loadFactor)},
        {key:'increment',label:'增量序号',unit:'',values:run.frames.map((_,i)=>i+1)}],series};
    }
    const run=ctx.blastRun();if(!run)throw Error('暂无爆破结果。');
    const response=await fetch(`./api/blast3d-runs/${run.runId}/probe?nodes=${ids.join(',')}`,{cache:'no-store',signal});
    const body=await response.json().catch(()=>({}));
    if(!response.ok||!body.ok)throw Error(body.error||'测点时程读取失败。');
    const perNode=ids.map((_,k)=>Object.fromEntries(body.fields.map(key=>[key,body.values[key].map(frame=>frame[k])])));
    return {axes:[{key:'time',label:'时间',unit:'μs',values:body.times.map(time=>time*1e6)}],series:combine(perNode,body.times.length)};
  }

  const panel=P.createPanel({
    root:document.getElementById('solid3dProbePanel'),dimension:3,store:activeStore(),exportName:'三维测点结果',
    quantities,locate,evaluate,
    note:()=>'四面体（或表面三角形）内按节点结果线性插值；位移量、von Mises 应力和等效应变由插值后的分量计算。',
    historyAvailable:()=>stage==='deformation-results'?Boolean(ctx.deformationRun()):stage==='blast-results'&&Boolean(ctx.blastRun()),
    historyKey:()=>stage+':'+(stage==='deformation-results'?ctx.deformationRun()?.runId:ctx.blastRun()?.runId),
    history,historyTitle:'时程 / 增量曲线',
    currentIndex:()=>stage==='deformation-results'?Number(document.getElementById('solid3dDeformationFrame').value)
      :stage==='blast-results'?Number(document.getElementById('solid3dBlastFrame').value):-1,
    selectIndex:index=>ctx.selectFrame(stage,index),
    changed:()=>ctx.draw()
  });

  function labelTexture(text,color){
    const key=text+color;
    if(labelTextures.has(key))return labelTextures.get(key);
    const canvas=document.createElement('canvas');canvas.width=64;canvas.height=32;
    const c=canvas.getContext('2d');c.font='700 22px Segoe UI, Arial, sans-serif';c.textBaseline='middle';
    c.lineWidth=5;c.strokeStyle='#ffffff';c.strokeText(text,4,16);c.fillStyle=color;c.fillText(text,4,16);
    const texture=new THREE.CanvasTexture(canvas);labelTextures.set(key,texture);return texture;
  }

  return {
    panel,
    setStage(next){
      stage=next;lastPlotted=null;
      if(stores[next])panel.setStore(stores[next]);
    },
    meshChanged(){for(const store of Object.values(stores))store.items=[];panel.clear();},
    // Refresh the value table whenever the plotted frame changes.
    sync(){const plotted=ctx.plotted();if(plotted!==lastPlotted){lastPlotted=plotted;panel.refresh();}},
    pickEnabled:()=>RESULT_STAGES.includes(stage)&&panel.pickEnabled(),
    pointerDown(event){down={x:event.clientX,y:event.clientY};},
    wasDrag(event){return down&&Math.hypot(event.clientX-down.x,event.clientY-down.y)>4;},
    // hit: raycast result on a surface mesh drawn by draw(); ids are the triangle's mesh nodes.
    pick(hit,ids){
      const position=hit.object.geometry.getAttribute('position'),base=hit.faceIndex*3;
      const corners=[0,1,2].map(k=>new THREE.Vector3().fromBufferAttribute(position,base+k));
      const bary=new THREE.Triangle(...corners).getBarycoord(hit.point,new THREE.Vector3());
      if(!bary)return;
      const weights=[bary.x,bary.y,bary.z].map(w=>Math.max(0,w)),sum=weights.reduce((a,b)=>a+b,0)||1;
      panel.addAt(null,{hit:{ids,weights:weights.map(w=>w/sum)}});
    },
    // Markers follow the displayed (possibly deformed) surface.
    addMarkers(group,{scale=0}={}){
      if(!RESULT_STAGES.includes(stage))return;
      const items=activeStore().items,mesh=ctx.mesh();if(!items.length||!mesh)return;
      const available=fields();
      items.forEach((probe,i)=>{
        const values=available&&scale?probeValues({ux:available.ux,uy:available.uy,uz:available.uz},probe):null;
        const at=new THREE.Vector3(...probe.point).add(new THREE.Vector3(values?.ux||0,values?.uy||0,values?.uz||0).multiplyScalar(scale));
        const color=P.probeColor(i);
        const dot=new THREE.Points(new THREE.BufferGeometry().setAttribute('position',new THREE.Float32BufferAttribute(at.toArray(),3)),
          new THREE.PointsMaterial({color,size:11,sizeAttenuation:false,depthTest:false,depthWrite:false}));
        dot.renderOrder=5;group.add(dot);
        const sprite=new THREE.Sprite(new THREE.SpriteMaterial({map:labelTexture(probe.label,color),depthTest:false,depthWrite:false,sizeAttenuation:false}));
        sprite.center.set(-.12,-.2);sprite.scale.set(.08,.04,1);sprite.position.copy(at);sprite.renderOrder=6;group.add(sprite);
      });
    }
  };
}
