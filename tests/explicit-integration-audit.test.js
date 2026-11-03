const test=require('node:test'),assert=require('node:assert/strict');
const {blastRing}=require('./helpers/blast-ring'),{rockCard}=require('./helpers/rock-card');
const {runBlastCore}=require('../server'),{removeRun}=require('../blast-runner');

// Leave exactly ONE physical degree of freedom. Independently assemble its
// scalar mass/stiffness and compare with the analytic step-loaded oscillator.
// This checks displacement, velocity, signs, SI scaling and convergence of the
// production integrator, rather than replaying its own constitutive inputs.
const cases=[1,3].flatMap(law=>[0,1].flatMap(planeMode=>(law===3?[0,1]:[0]).map(kinematics=>({law,planeMode,kinematics}))));
for(const {law,planeMode,kinematics} of cases)test(`analytic oscillator: law ${law}, planeMode ${planeMode}, kinematics ${kinematics}`,async t=>{
 const m=blastRing({sectors:12,rings:2,outer:.4}),F=100,E=20e9,nu=.2,rho=2500;
 const G=E/(2*(1+nu)),K=E/(3*(1-2*nu)),lambda=K-2*G/3;
 let mass=0,stiffness=0;
 for(const [i,n] of m.nodes.entries()){n.fixUx=i!==0;n.fixUy=true;n.forceX=i===0?F:0;}
 for(const e of m.elements){
  const ids=e.nodeNumbers.map(n=>n-1),j=ids.indexOf(0);if(j<0)continue;
  const [a,b,c]=ids.map(i=>m.nodes[i]),det=(b.x-a.x)*(c.y-a.y)-(c.x-a.x)*(b.y-a.y);
  const gx=[b.y-c.y,c.y-a.y,a.y-b.y][j]/det,gy=[c.x-b.x,a.x-c.x,b.x-a.x][j]/det;
  mass+=rho*Math.abs(det)/6;stiffness+=Math.abs(det)/2*((planeMode===1?lambda+2*G:E/(1-nu*nu))*gx*gx+G*gy*gy);
 }
 if(law===3){const card=rockCard();Object.assign(card.jh2,{G,K,K1:K,K2:0,K3:0,beta:0,A:1e6,T:1e12});m.materials[0].blastConstitutive=card;}
 const omega=Math.sqrt(stiffness/mass),duration=2.3*Math.PI/omega;
 const settings={rockModel:law,planeMode,kinematics,loadMode:1,boundary:0,pressure:0,shockViscosity:0,fracture:false,duration,pulse:duration,frames:2};
 const runs=[];t.after(()=>Promise.all(runs.map(h=>removeRun(h.id))));
 const baseline=await runBlastCore(m,settings);runs.push(baseline);
 const errors=[];
 for(const factor of [.5,.25]){
  const h=await runBlastCore(m,{...settings,dt:baseline.dt*factor});runs.push(h);
  const f=h.frames.at(-1),u=F/stiffness*(1-Math.cos(omega*duration)),v=F/(mass*omega)*Math.sin(omega*duration);
  errors.push(Math.hypot((f.u[0]-u)/(F/stiffness),(f.v[0]-v)/(F/(mass*omega))));
  assert.ok(Math.abs(f.externalWork-F*f.u[0])<1e-10*Math.max(1,Math.abs(f.externalWork)));
  assert.ok(Math.abs(f.kineticEnergy-.5*mass*f.v[0]**2)<1e-10);
  assert.ok(Math.abs(f.strainEnergy-.5*stiffness*f.u[0]**2)<1e-7*Math.max(1e-6,f.strainEnergy),`stored energy ${f.strainEnergy}, analytic ${.5*stiffness*f.u[0]**2}`);
 }
 assert.ok(errors[1]<errors[0]*.35,`halved time step must converge at second order: ${errors}`);
 assert.ok(errors[1]<.015,`analytic displacement/velocity error ${errors[1]}`);
});
