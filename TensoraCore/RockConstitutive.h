#pragma once
// JH2 stress/damage updates call the unmodified OpenRadioss SIGEPS79 runtime.
// Other blast solid laws were removed; only initialization/energy diagnostics remain.
// References and parameter conventions: docs/ROCK_CONSTITUTIVE.md.
#include <Eigen/Dense>
#include <algorithm>
#include <array>
#include <cmath>
#include <stdexcept>
#include <vector>
#include <memory>
#include "OpenRadiossJH2.h"
#include "CBGeoMaterials.h"

namespace fem { namespace rock {
using Tensor=Eigen::Matrix3d;
inline Tensor Dev(const Tensor& t){return t-Tensor::Identity()*(t.trace()/3.);}
inline double Q(const Tensor& s){return std::sqrt(1.5*Dev(s).squaredNorm());}
struct Parameters {
  int law=3;
  bool logarithmicVolume=false;
  bool hasFractureEnergy=false;
  double E=0,nu=0,ft=0,fc=0,gf=100,h=1,density=1;
  double A=0,N=0,B=0,M=0,C=0,rate0=1,HEL=0,pHEL=0,T=0,D1=0,D2=0,maxStrength=0,K1=0,K2=0,K3=0,beta=0,referenceLength=0;
  double friction=0,dilation=0;
  double normalizationStress=0,inputShearModulus=0,inputBulkModulus=0;
  double cohesion=0,tension=0,softening=0,residualFriction=0,residualDilation=0,residualCohesion=0,peakStrain=0,residualStrain=0;
  std::shared_ptr<mpm::Material<3>> material;
  double G()const{return law==3 && inputShearModulus>0 ? inputShearModulus : E/(2*(1+nu));}
  double K()const{return law==3 ? K1 : E/(3*(1-2*nu));}
  double SigmaHEL()const{return normalizationStress>0 ? normalizationStress : 1.5*(HEL-pHEL);}
};
struct State {
  Tensor stress=Tensor::Zero(),effective=Tensor::Zero(),strain=Tensor::Zero();
  double damage=0,history=0,plasticStrain=0,plasticWork=0,bulking=0,bulkingEnergy=0,initialPressure=0,initialVolumeStrain=0,tensileOpening=0;
  double temperature=0,pc=0,plasticVolume=0,maxCompression=0,solidEnergy=0,hardeningEnergy=0;
  double jh2PreviousYield=0,jh2Et=1,jh2ReferenceMu=0,jh2ReferencePressure=0,jh2SoundSpeed=0;
  bool jh2ReferenceReady=false;
  mpm::dense_map materialState;
  std::vector<Tensor> memory;
};
inline double EOS(const Parameters& p,double volumeStrain){
  // mu = rho/rho0 - 1, with small-strain volume J=1+tr(epsilon).
  if(!p.logarithmicVolume && volumeStrain<=-0.8)throw std::runtime_error("Rock volume collapsed; refine mesh/time step or use a particle solver.");
  const double mu=p.logarithmicVolume ? std::expm1(-volumeStrain) : -volumeStrain/(1+volumeStrain);
  return mu>0 ? ((p.K3*mu+p.K2)*mu+p.K1)*mu : p.K1*mu;
}
inline double Rate(const Parameters& p,double rate){return 1+p.C*std::log(std::max(1.,rate/p.rate0));}
inline double CompressionMu(const Parameters& p,double volumeStrain){
  return p.logarithmicVolume ? std::expm1(-volumeStrain) : -volumeStrain/(1+volumeStrain);
}
inline double Intact(const Parameters& p,double pressure,double rate){return p.SigmaHEL()*p.A*std::pow(std::max(0.,(pressure+p.T)/p.pHEL),p.N)*Rate(p,rate);}
inline double Failed(const Parameters& p,double pressure,double rate){return p.SigmaHEL()*std::min(p.maxStrength,p.B*std::pow(std::max(0.,pressure/p.pHEL),p.M)*Rate(p,rate));}
inline double Strength(const Parameters& p,double pressure,double rate,double damage){return (1-damage)*Intact(p,pressure,rate)+damage*Failed(p,pressure,rate);}
inline double FailureStrain(const Parameters& p,double pressure){
  const double scale=p.referenceLength>0 ? p.referenceLength/p.h : 1.;
  return std::max(1e-8,p.D1*std::pow(std::max(0.,(pressure+p.T)/p.pHEL),p.D2)*scale);
}
// Map the prescribed prestress to the reference density expected by SIGEPS79.
// This is initialization/kinematics, not a replacement constitutive integration.
inline double JH2InitialMu(const Parameters& p,double pressure){
  if(pressure<=0)return pressure/p.K1;
  double lo=0,hi=.01;
  auto value=[&](double mu){return ((p.K3*mu+p.K2)*mu+p.K1)*mu;};
  while(value(hi)<pressure){hi*=2;if(hi>1e6)throw std::runtime_error("Cannot initialize OpenRadioss JH2 reference density.");}
  for(int k=0;k<64;++k){const double mid=.5*(lo+hi);if(value(mid)<pressure)lo=mid;else hi=mid;}
  return .5*(lo+hi);
}
// SIGEPS79 reconstructs pressure from density; only the previous deviator enters
// its stress trial. Pack that invariant directly. Pairwise differences avoid
// manufacturing deviatoric stress by subtracting nearly equal hydrostatic terms.
inline Tensor JH2PreviousDeviator(const Tensor& stress){
  Tensor result=stress;
  result(0,0)=((stress(0,0)-stress(1,1))+(stress(0,0)-stress(2,2)))/3;
  result(1,1)=((stress(1,1)-stress(0,0))+(stress(1,1)-stress(2,2)))/3;
  result(2,2)=-(result(0,0)+result(1,1));return result;
}
inline std::array<double,20> JH2KernelParameters(const Parameters& p,bool damageEnabled){
  return {p.G(),2*p.G(),p.A,p.B,p.M,p.N,p.C,p.rate0,p.maxStrength,p.T/p.pHEL,
    p.pHEL,p.SigmaHEL(),p.D1,p.D2,p.K1,p.K2,p.K3,damageEnabled?p.beta:0.,0.,1e30};
}
inline void JH2Step(const Parameters& p,State& s,const Tensor& increment,double dt,bool damageEnabled){
  if(!(dt>0) || !increment.allFinite())throw std::runtime_error("Invalid OpenRadioss JH2 strain/time increment.");
  if(p.referenceLength!=0)throw std::runtime_error("OpenRadioss local JH2 requires referenceLength=0; nonlocal regularization is not connected.");
  if(!s.jh2ReferenceReady || s.jh2ReferencePressure!=s.initialPressure){
    s.jh2ReferenceMu=JH2InitialMu(p,s.initialPressure);
    s.jh2ReferencePressure=s.initialPressure;s.jh2ReferenceReady=true;
  }
  s.strain+=increment;
  const double trace=s.strain.trace();
  const double mu=p.logarithmicVolume ? std::expm1(std::log1p(s.jh2ReferenceMu)-(trace-s.initialVolumeStrain))
    : std::expm1(std::log1p(s.jh2ReferenceMu)+std::log1p(s.initialVolumeStrain)-std::log1p(trace));
  if(!(mu>-1) || !std::isfinite(mu))throw std::runtime_error("Invalid OpenRadioss JH2 density/volume.");
  const auto parameters=JH2KernelParameters(p,damageEnabled);
  const Tensor old=JH2PreviousDeviator(s.effective);
  double oldStress[6]={old(0,0),old(1,1),old(2,2),old(0,1),old(1,2),old(2,0)};
  double delta[6]={increment(0,0),increment(1,1),increment(2,2),2*increment(0,1),2*increment(1,2),2*increment(2,0)};
  double state[5]={s.damage,s.plasticStrain,s.bulking,s.jh2PreviousYield,s.jh2Et},stress[6],results[3];
  const double rate=std::sqrt(2./3*Dev(increment).squaredNorm())/dt,oldBulking=s.bulking;
  openradioss::Runtime().step(parameters.data(),oldStress,delta,mu,rate,p.density,state,stress,results);
  if(damageEnabled)s.damage=state[0];
  s.plasticStrain=state[1];s.bulking=state[2];s.jh2PreviousYield=state[3];s.jh2Et=state[4];s.jh2SoundSpeed=results[2];
  s.effective<<stress[0],stress[3],stress[5],stress[3],stress[1],stress[4],stress[5],stress[4],stress[2];
  s.stress=s.effective;
  // Diagnostics only: the returned stress and damage are never projected locally.
  const double trial=Q(Dev(old)+2*p.G()*Dev(increment));
  const double bulkingWork=(s.bulking-oldBulking)*(2*p.K1*mu+s.bulking+oldBulking)/(2*p.K1);
  s.bulkingEnergy+=std::max(0.,bulkingWork);
  s.plasticWork+=std::max(0.,.5*(trial+Q(s.stress))*results[1]-std::max(0.,bulkingWork));
  if(!s.stress.allFinite() || !std::isfinite(s.damage) || !std::isfinite(s.plasticStrain) || !std::isfinite(s.bulking) || !std::isfinite(s.jh2SoundSpeed))throw std::runtime_error("Non-finite OpenRadioss JH2 material response.");
}
inline void Step(const Parameters& p,State& s,const Tensor& increment,double dt,bool damageEnabled){
  if(p.law==1||p.law==6){
    if(!p.material||!(dt>0)||!increment.allFinite())throw std::runtime_error("Invalid solid material state or increment.");
    if(s.materialState.empty())s.materialState=p.material->initialise_state_variables();
    Eigen::Matrix<double,6,1> old,delta;
    // CB-Geo Voigt order: xx, yy, zz, xy, yz, xz; engineering shear.
    old<<s.stress(0,0),s.stress(1,1),s.stress(2,2),s.stress(0,1),s.stress(1,2),s.stress(0,2);
    delta<<increment(0,0),increment(1,1),increment(2,2),2*increment(0,1),2*increment(1,2),2*increment(0,2);
    const auto result=p.material->compute_stress(old,delta,nullptr,&s.materialState);
    if(!result.allFinite())throw std::runtime_error("Non-finite solid material response.");
    s.strain+=increment;s.stress<<result[0],result[3],result[5],result[3],result[1],result[4],result[5],result[4],result[2];s.effective=s.stress;
    if(p.law==6)s.plasticStrain=s.materialState.at("pdstrain");
    return;
  }
  if(p.law!=3)throw std::runtime_error("This local solid constitutive model was removed; select upstream JH2.");
  JH2Step(p,s,increment,dt,damageEnabled);
}
inline void InitializeMaterial(Parameters& p){
  if(p.law!=1&&p.law!=6)return;
  Json props={{"density",p.density},{"youngs_modulus",p.E},{"poisson_ratio",p.nu}};
  if(p.law==1)p.material=std::make_shared<mpm::LinearElastic<3>>(0,props);
  else {
    props.update(Json{{"softening",p.softening==1},{"friction",p.friction},{"dilation",p.dilation},{"cohesion",p.cohesion},{"tension_cutoff",p.tension},{"residual_friction",p.residualFriction},{"residual_dilation",p.residualDilation},{"residual_cohesion",p.residualCohesion},{"peak_pdstrain",p.peakStrain},{"residual_pdstrain",p.residualStrain}});
    p.material=std::make_shared<mpm::MohrCoulomb<3>>(0,props);
  }
}
// Plane stress is a kinematic constraint around the unmodified 3D material
// call. Every trial starts from the SAME saved history; only a converged state
// is committed. Enforce sigma_zz=0 at EACH accepted subincrement.
inline State PlaneStressIncrement(const Parameters& p,const State& old,const Tensor& inplaneDelta,double dt,bool damageEnabled){
  auto evaluate=[&](double dz){
    State trial=old;Tensor delta=inplaneDelta;delta(2,2)=dz;
    Step(p,trial,delta,dt,damageEnabled);
    if(p.logarithmicVolume)trial.plasticWork=old.plasticWork+std::exp(trial.strain.trace()-trial.initialVolumeStrain)*(trial.plasticWork-old.plasticWork);
    return trial;
  };
  auto converged=[&](const State& s){return std::abs(s.stress(2,2))<=(damageEnabled ? 1e-8 : 1e-10)*std::max(1e6,s.stress.norm());};
  // JH2's bulk tangent comes from its EOS; p.nu is only an initial guess.
  const double guess=-p.nu/(1-p.nu)*inplaneDelta.trace();
  const double lower=p.logarithmicVolume ? -2. : -.95*(1+old.strain.trace()+inplaneDelta.trace());
  const double upper=2.;
  if(!(lower<upper))throw std::runtime_error("Invalid plane-stress trial volume.");
  auto admissible=[&](double z){return std::clamp(z,lower,upper);};
  double z=admissible(guess);State result=evaluate(z);
  for(int k=0;k<20;++k){
    if(converged(result))return result;
    const double h=std::max(1e-9,1e-4*std::max(inplaneDelta.norm(),std::abs(z)));
    const double a=admissible(z-h),b=admissible(z+h);
    const double derivative=(evaluate(b).stress(2,2)-evaluate(a).stress(2,2))/(b-a);
    if(!std::isfinite(derivative)||std::abs(derivative)<1e-10*p.E)break;
    const double correction=std::clamp(result.stress(2,2)/derivative,-.05,.05);
    bool improved=false;
    for(int line=0;line<10;++line){
      const double candidate=admissible(z-std::ldexp(correction,-line));State trial=evaluate(candidate);
      if(converged(trial)||std::abs(trial.stress(2,2))<std::abs(result.stress(2,2))){z=candidate;result=trial;improved=true;break;}
    }
    if(!improved)break;
  }
  // Damage/softening may destroy the Newton tangent. Search near the elastic
  // guess, then bisect a sign-changing admissible interval without projecting stress.
  double width=std::max(1e-8,.25*inplaneDelta.norm());
  double lo=z,hi=z;State left=result,right=result;
  for(int k=0;k<28;++k){
    lo=admissible(guess-width);hi=admissible(guess+width);left=evaluate(lo);right=evaluate(hi);
    if(converged(left))return left;if(converged(right))return right;
    if(std::signbit(left.stress(2,2))!=std::signbit(right.stress(2,2)))break;
    if(lo==lower&&hi==upper)break;width*=2;
  }
  if(std::signbit(left.stress(2,2))!=std::signbit(right.stress(2,2)))for(int k=0;k<80;++k){
    z=.5*(lo+hi);result=evaluate(z);if(converged(result))return result;
    if(std::signbit(left.stress(2,2))!=std::signbit(result.stress(2,2))){hi=z;right=result;}else{lo=z;left=result;}
  }
  throw std::runtime_error("Rock plane-stress return did not converge; reduce time step or use plane strain.");
}
inline State Advance(const Parameters& p,const State& old,const Eigen::Vector3d& inplane,double dt,bool planeStrain,bool damageEnabled){
  Tensor target=Tensor::Zero();target(0,0)=inplane[0];target(1,1)=inplane[1];target(0,1)=target(1,0)=inplane[2]/2;
  Tensor delta=target-old.strain;
  if(!planeStrain)delta(2,2)=0;
  const double measure=delta.norm()+(planeStrain ? 0 : std::abs(p.nu/(1-p.nu)*(delta(0,0)+delta(1,1))));
  if(!std::isfinite(measure)||!(dt>0)||measure>1024*2e-4)throw std::runtime_error("Rock strain increment too large; reduce time step.");
  const int n=std::max(1,static_cast<int>(std::ceil(measure/2e-4)));
  State s=old;
  for(int i=0;i<n;++i){
    if(!planeStrain)s=PlaneStressIncrement(p,s,delta/n,dt/n,damageEnabled);
    else {const double previousWork=s.plasticWork;Step(p,s,delta/n,dt/n,damageEnabled);
      if(p.logarithmicVolume)s.plasticWork=previousWork+std::exp(s.strain.trace()-s.initialVolumeStrain)*(s.plasticWork-previousWork);
    }
  }
  return s;
}
inline void Initialize(const Parameters& p,State& s,const Eigen::Vector3d& strain,const Eigen::Vector3d& stress,bool planeStrain){
  s.strain(0,0)=strain[0];s.strain(1,1)=strain[1];s.strain(0,1)=s.strain(1,0)=strain[2]/2;
  s.strain(2,2)=planeStrain ? 0 : -p.nu/(1-p.nu)*(strain[0]+strain[1]);
  s.stress(0,0)=stress[0];s.stress(1,1)=stress[1];s.stress(0,1)=s.stress(1,0)=stress[2];
  s.stress(2,2)=planeStrain ? p.nu*(stress[0]+stress[1]) : 0;s.effective=s.stress;
  s.initialPressure=-s.stress.trace()/3;s.initialVolumeStrain=s.strain.trace();
}
// Diagnostic EOS work per reference volume: integral P(mu)/(1+mu)^2 dmu.
// The closed forms cancel to zero at small elastic strains. Integrate the
// convergent series there, so a quiet state does not lose its volumetric energy.
inline double JH2CompressionEnergy(const Parameters& p,double mu){
  if(std::abs(mu)<.01){
    double integrals[3]={0,0,0};
    for(int n=1;n<=3;++n){double power=std::pow(mu,n+1);for(int k=0;k<16;++k){integrals[n-1]+=(k%2 ? -1. : 1.)*(k+1)*power/(n+k+1);power*=mu;}}
    return p.K1*integrals[0]+p.K2*integrals[1]+p.K3*integrals[2];
  }
  const double log=std::log1p(mu),inverse=1/(1+mu);
  return p.K1*(log+inverse-1)+p.K2*(mu-2*log-inverse+1)+p.K3*(.5*mu*mu-2*mu+3*log+inverse-1);
}
inline double StoredEnergy(const Parameters& p,const State& s){
  const double pressure=-s.stress.trace()/3;
  double bulk=pressure*pressure/(2*p.K());
  if(p.law==3 && pressure>0){
    const double volume=p.logarithmicVolume?std::exp(s.strain.trace()):1+s.strain.trace();
    if(volume>0 && volume<1)bulk=JH2CompressionEnergy(p,1/volume-1);
  }
  return std::max(0.,bulk)+Dev(s.stress).squaredNorm()/(4*p.G())+s.bulkingEnergy;
}
} }
