// Map CalculiX nodal FRD fields to the shared 3D viewer.
const stressKeys=['sxx','syy','szz','sxy','syz','sxz'];
const strainKeys=['exx','eyy','ezz','exy','eyz','exz'];
const displacementKeys=['ux','uy','uz'];

export function initiationThresholds(run){
  const thresholds=new Float64Array(run.model.nodes.length).fill(Infinity);
  for(const element of run.model.elements){
    const card=run.materialSettings[element.materialNo];
    if(card.model!=='plastic')continue;
    for(const id of [element.node1,element.node2,element.node3,element.node4]){
      thresholds[id-1]=Math.min(thresholds[id-1],card.criticalPlasticStrain);
    }
  }
  return thresholds;
}

export function deformationFrame3d(run,index,thresholds){
  const frame=run.frames[index],count=run.model.nodes.length;
  const plastic=Object.values(run.materialSettings).some(card=>card.model==='plastic');
  const keys=[...displacementKeys,'umag',...stressKeys,'vm',...strainKeys,'equivalentStrain'];
  if(plastic)keys.push('peeq','damageInitiation');
  if(run.damageEvolution)keys.push('damageEvolution');
  const nodeFields=Object.fromEntries(keys.map(key=>[key,new Float64Array(count)]));
  const displacementVector=new Float64Array(count*3);
  let maxDisplacement=0,maxVonMises=0;
  for(let i=0;i<count;i++){
    const id=run.model.nodes[i].nodeNo,u=frame.displacement[id],stress=frame.stress[id],strain=frame.strain[id];
    displacementVector.set(u,i*3);
    displacementKeys.forEach((key,j)=>{nodeFields[key][i]=u[j];});
    stressKeys.forEach((key,j)=>{nodeFields[key][i]=stress[j];});
    strainKeys.forEach((key,j)=>{nodeFields[key][i]=strain[j];});
    nodeFields.umag[i]=Math.hypot(...u);
    const [sx,sy,sz,sxy,syz,sxz]=stress,[ex,ey,ez,exy,eyz,exz]=strain;
    nodeFields.vm[i]=Math.sqrt(((sx-sy)**2+(sy-sz)**2+(sz-sx)**2)/2+3*(sxy**2+syz**2+sxz**2));
    nodeFields.equivalentStrain[i]=Math.sqrt(2*((ex-ey)**2+(ey-ez)**2+(ez-ex)**2)/9+4*(exy**2+eyz**2+exz**2)/3);
    if(plastic){
      nodeFields.peeq[i]=frame.plasticStrain[id][0];
      nodeFields.damageInitiation[i]=nodeFields.peeq[i]/thresholds[i];
    }
    if(run.damageEvolution)nodeFields.damageEvolution[i]=frame.damage[id][0];
    maxDisplacement=Math.max(maxDisplacement,nodeFields.umag[i]);
    maxVonMises=Math.max(maxVonMises,nodeFields.vm[i]);
  }
  return {nodeFields,displacementVector,maxDisplacement,maxVonMises};
}

// Nodal values of selected nodes (0-based mesh indices) at every frame:
// result[k][key][frame] for node ids[k]. Used by point probes.
export function deformationProbeSeries(run,ids,thresholds){
  const plastic=Object.values(run.materialSettings).some(card=>card.model==='plastic');
  const count=run.frames.length;
  return ids.map(i=>{
    const id=run.model.nodes[i].nodeNo,out={};
    const put=(key,f,value)=>{(out[key]||=new Float64Array(count))[f]=value;};
    run.frames.forEach((frame,f)=>{
      const u=frame.displacement[id]||[0,0,0],stress=frame.stress[id]||[0,0,0,0,0,0],strain=frame.strain[id]||[0,0,0,0,0,0];
      displacementKeys.forEach((key,j)=>put(key,f,u[j]||0));
      stressKeys.forEach((key,j)=>put(key,f,stress[j]||0));
      strainKeys.forEach((key,j)=>put(key,f,strain[j]||0));
      if(plastic){const peeq=frame.plasticStrain?.[id]?.[0]||0;put('peeq',f,peeq);put('damageInitiation',f,peeq/thresholds[i]);}
      if(run.damageEvolution)put('damageEvolution',f,frame.damage?.[id]?.[0]||0);
    });
    return out;
  });
}
