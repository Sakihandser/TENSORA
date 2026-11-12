const edges = [[0,1],[0,2],[0,3],[1,2],[1,3],[2,3]];
const dot = (a,b) => a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
const cross = (a,b) => [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]];

export const sectionNormals = { XY:[0,0,1], XZ:[0,1,0], YZ:[1,0,0] };

export function unitSectionNormal(normal) {
  const length = Math.hypot(...normal);
  return length > 0 && Number.isFinite(length) ? normal.map(value=>value/length) : null;
}

export function cutTetrahedra(mesh, point, normal, tolerance, hiddenVolumes) {
  const distances = Float64Array.from(mesh.nodes, node=>
    normal[0]*(node[0]-point[0])+normal[1]*(node[1]-point[1])+normal[2]*(node[2]-point[2]));
  for (let i=0; i<distances.length; i++) if (Math.abs(distances[i])<=tolerance) distances[i]=0;

  const basisU = unitSectionNormal(cross(normal, Math.abs(normal[0])<.8 ? [1,0,0] : [0,1,0]));
  const basisV = cross(normal,basisU);
  const positions=[], endpoints=[], fractions=[], elements=[];
  const coincidentFaces=new Map();
  for (let element=0; element<mesh.tets.length; element++) {
    const ids=mesh.tets[element];
    const a=distances[ids[0]], b=distances[ids[1]], c=distances[ids[2]], d=distances[ids[3]];
    if ((a>0&&b>0&&c>0&&d>0)||(a<0&&b<0&&c<0&&d<0)) continue;
    if (hiddenVolumes.has(String(mesh.tetVolumes?.[element]??'0'))) continue;

    const polygon=[], onPlane=[];
    for (const id of ids) if (distances[id]===0) onPlane.push(id);
    if (onPlane.length===4) continue;
    if (onPlane.length===3) {
      const key=onPlane.slice().sort((a,b)=>a-b).join(',');
      const positive=a+b+c+d>0;
      const previous=coincidentFaces.get(key);
      if (previous) {
        // For a shared face, use the visible cell on the side of the normal.
        if (positive&&!previous.positive) {
          elements[previous.index]=element;
          previous.positive=true;
        }
        continue;
      }
      coincidentFaces.set(key,{index:elements.length,positive});
    }
    for (const id of onPlane) polygon.push({position:mesh.nodes[id],i:id,j:id,t:0});
    for (const [from,to] of edges) {
      const i=ids[from],j=ids[to],di=distances[i],dj=distances[j];
      if (!((di<0&&dj>0)||(di>0&&dj<0))) continue;
      const t=di/(di-dj);
      const position=mesh.nodes[i].map((value,k)=>value+t*(mesh.nodes[j][k]-value));
      polygon.push({position,i,j,t});
    }
    if (polygon.length<3) continue;

    const center=[0,0,0];
    for (const {position} of polygon) for (let k=0;k<3;k++) center[k]+=position[k]/polygon.length;
    for (const vertex of polygon) {
      const offset=vertex.position.map((value,k)=>value-center[k]);
      vertex.angle=Math.atan2(dot(offset,basisV),dot(offset,basisU));
    }
    polygon.sort((a,b)=>a.angle-b.angle);
    for (let i=1; i<polygon.length-1; i++) {
      for (const {position,i:a,j:b,t} of [polygon[0],polygon[i],polygon[i+1]]) {
        positions.push(...position);
        endpoints.push(a,b);
        fractions.push(t);
      }
      elements.push(element);
    }
  }
  return {positions:new Float32Array(positions),endpoints:new Uint32Array(endpoints),
    fractions:new Float64Array(fractions),elements:new Uint32Array(elements)};
}

const stressFields=['sxx','syy','szz','sxy','syz','sxz'];
const strainFields=['exx','eyy','ezz','exy','eyz','exz'];

export function sectionValues(cut, result, field) {
  const values=new Float64Array(cut.fractions.length);
  const stressIndex=stressFields.indexOf(field), strainIndex=strainFields.indexOf(field);
  for (let i=0; i<values.length; i++) {
    const a=cut.endpoints[i*2], b=cut.endpoints[i*2+1], t=cut.fractions[i];
    const index=cut.elements[Math.floor(i/3)];
    const element=result.stress?.[index], data=result.elementData, base=index*14;
    if (!data&&!element&&result.nodeFields?.[field]) {
      const nodal=result.nodeFields[field];
      values[i]=nodal[a]+t*(nodal[b]-nodal[a]);
    }
    else if (stressIndex>=0) values[i]=data?data[base+stressIndex]:element.components[stressIndex];
    else if (strainIndex>=0) values[i]=data?data[base+7+strainIndex]:element.strain[strainIndex];
    else if (field==='safety') values[i]=data?result.elementSafety[index]:element.safetyCode;
    else if (field==='vm') values[i]=data?data[base+6]:element.vonMises;
    else if (field==='equivalentStrain') values[i]=data?data[base+13]:element.equivalentStrain;
    else {
      const nodal=result.nodeFields[field];
      values[i]=nodal[a]+t*(nodal[b]-nodal[a]);
    }
  }
  return values;
}
