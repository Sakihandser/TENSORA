'use strict';
function fracturePatch({nx=10,ny=10,notch=false}={}){
 const nodes=[],elements=[];const side=.01;
 for(let j=0;j<=ny;j++)for(let i=0;i<=nx;i++)nodes.push({nodeNo:j*(nx+1)+i+1,x:i*side/nx,y:j*side/ny,fixUx:j===0,fixUy:j===0,forceX:0,forceY:j===ny?1:0});
 for(let j=0;j<ny;j++)for(let i=0;i<nx;i++){
   if(notch&&j===Math.floor(ny/2)-1&&i<Math.floor(nx/2))continue;
   const a=j*(nx+1)+i+1,b=a+1,c=a+nx+1,d=c+1;
   for(const tri of [[a,b,d],[a,d,c]])elements.push({elementNo:elements.length+1,node1:tri[0],node2:tri[1],node3:tri[2],elasticModulus:210e9,poissonRatio:.3,materialNo:1});
 }
 const refs=new Set(elements.flatMap(e=>[e.node1,e.node2,e.node3]));
 return {modelName:notch?'SENT fracture verification':'Fracture patch',nodes:nodes.filter(n=>refs.has(n.nodeNo)),elements,materials:[{materialNo:1,id:'steel'}]};
}
function fractureSettings(extra={}){return {solver:'phast',planeMode:1,finiteStrain:false,increments:20,maxIncrements:200,fractureLoading:'displacement',fractureDisplacement:.00002,materials:{steel:{model:'phaseField',fractureEnergy:2700,fractureLength:.001}},...extra};}
module.exports={fracturePatch,fractureSettings};
