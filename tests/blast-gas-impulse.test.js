const test=require('node:test'),assert=require('node:assert/strict');
const {runBlastCore}=require('../server'),{removeRun}=require('../blast-runner');
const {blastRing}=require('./helpers/blast-ring');

test('one solid step receives the full gas pressure impulse, not a second average with the previous pressure',async t=>{
 const m=blastRing({sectors:24,rings:3,outer:.4}),dt=1e-7;
 const h=await runBlastCore(m,{sourceMode:1,chargeRadius:.1,gasCells:32,productEnergy:1e6,
  duration:dt,frames:2,fracture:false,shockViscosity:0,rockModel:1,planeMode:1});
 t.after(()=>removeRun(h.id));assert.equal(h.steps,1);
 const [a,b]=h.frames,N=m.nodes.length,mass=Array(N).fill(0),F=Array(2*N).fill(0);
 for(let k=0;k<24;k++){
  const j=(k+1)%24,dx=m.nodes[j].x-m.nodes[k].x,dy=m.nodes[j].y-m.nodes[k].y;
  for(const n of [k,j]){F[2*n]+=dy/2;F[2*n+1]-=dx/2;}
 }
 const internal=f=>{const result=Array(2*N).fill(0);
  m.elements.forEach((e,i)=>{const ids=e.nodeNumbers.map(n=>n-1),[p,q,r]=ids.map(n=>m.nodes[n]);
   const det=(q.x-p.x)*(r.y-p.y)-(r.x-p.x)*(q.y-p.y),gx=[q.y-r.y,r.y-p.y,p.y-q.y].map(x=>x/det),gy=[r.x-q.x,p.x-r.x,q.x-p.x].map(x=>x/det),s=f.elements[i];
   ids.forEach((n,j)=>{result[2*n]+=e.area*(gx[j]*s[3]+gy[j]*s[5]);result[2*n+1]+=e.area*(gy[j]*s[4]+gx[j]*s[5]);});
  });return result;};
 m.elements.forEach(e=>e.nodeNumbers.forEach(n=>mass[n-1]+=e.density*e.area/3));
 const dV=F.reduce((sum,x,i)=>sum+x*(b.u[i]-a.u[i]),0),meanP=(b.gasWallWork-a.gasWallWork)/dV;
 assert.ok(dV>0&&meanP>0);const fa=internal(a),fb=internal(b);
 let error=0,scale=0;
 for(let i=0;i<F.length;i++){const impulse=dt*(meanP*F[i]-.5*(fa[i]+fb[i]));const measured=mass[i>>1]*(b.v[i]-a.v[i]);error+=(impulse-measured)**2;scale+=impulse**2;}
 assert.ok(Math.sqrt(error/scale)<1e-9,`relative impulse error ${Math.sqrt(error/scale)}`);
});
