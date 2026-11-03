#include "../../TensoraCore/GasDynamics.h"
#include <cmath>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <limits>
#include <singularity-eos/eos/eos_jwl.hpp>
#include <singularity-eos/eos/eos_ideal.hpp>
#include <singularity-eos/eos/eos_noble_abel.hpp>
#include <singularity-eos/eos/eos_stiff.hpp>

static void close(double a,double b){
  if(!std::isfinite(a)||!std::isfinite(b)||std::abs(a-b)>2e-12*std::max(1.,std::abs(b)))throw std::runtime_error("EOS upstream/units mismatch");
}
template<class EOS,class CGS> static void checkEOS(const EOS& direct,const CGS& cgs,int model,const double* params,double rho,double e){
  const auto actual=fem::EvaluateUpstreamEOS(model,params,rho,e);
  const double pressure=direct.PressureFromDensityInternalEnergy(rho,e);
  close(actual.pressure,pressure);
  close(actual.soundSpeedSquared,direct.BulkModulusFromDensityInternalEnergy(rho,e)/rho);
  double restored=0;
  if(fem::upstream_eos::Runtime().energy(model,params,rho,pressure,&restored))throw std::runtime_error("EOS inverse rejected");
  close(restored,e);
  // kg/m3 -> g/cm3, J/kg -> erg/g, dyn/cm2 -> Pa.
  close(actual.pressure,cgs.PressureFromDensityInternalEnergy(rho*.001,e*1e4)*.1);
  close(actual.soundSpeedSquared,cgs.BulkModulusFromDensityInternalEnergy(rho*.001,e*1e4)*.1/rho);
}
static void verifyUpstreamEOS(){
  int samples=0,rejected=0;
  for(double gamma:{1.2,1.4,1.67})for(double rho:{.125,1.25,10.,1320.,2000.})for(double e:{1e5,1e6,5e6,1e7}){
    double params[7]={gamma,0,0,0,0,0,0};
    const singularity::IdealGas direct(gamma-1,1.);
    checkEOS(direct,direct,0,params,rho,e);++samples;
  }
  for(int card=0;card<2;++card){
    const double rho0=card?1620.:1320.,A=card?373.77e9:586e9,B=card?3.7471e9:21.6e9,R1=card?4.15:5.81,R2=card?.9:1.77,w=card?.35:.282;
    double params[7]={1+w,rho0,A,B,R1,R2,w};
    const singularity::JWL direct(A,B,R1,R2,w,rho0,1.),cgs(A*10,B*10,R1,R2,w,rho0*.001,1.);
    for(double ratio:{.1,.5,1.,1.5,2.})for(double e:{1e6,5e6,1e7,2e7}){
      checkEOS(direct,cgs,1,params,rho0*ratio,e);++samples;
    }
  }
  for(int model:{0,1})for(int slot=0;slot<7;++slot){
    if((model==0&&slot!=0)||(model==1&&slot==0))continue;
    for(double bad:{std::numeric_limits<double>::infinity(),std::numeric_limits<double>::quiet_NaN()}){
      double params[7]={1.4,1320,586e9,21.6e9,5.81,1.77,.282},out[2];params[slot]=bad;
      if(fem::upstream_eos::Runtime().evaluate(model,params,1320,5e6,out)!=1||fem::upstream_eos::Runtime().energy(model,params,1320,1e9,out)!=1)throw std::runtime_error("Nonfinite EOS parameter accepted");
      ++rejected;
    }
  }
  std::cout<<"{\"samples\":"<<samples<<",\"rejected\":"<<rejected<<"}";
}
int main(int argc,char* argv[]) {
  try {
    const std::string mode=argc>1 ? argv[1] : "sod";
    if(mode=="upstream-eos"){verifyUpstreamEOS();return 0;}
    if(mode=="new-eos"){
      int samples=0;
      for(int model:{3,4})for(double rho:{1.2,30.,1000.,3000.})for(double e:{5e6,1e7,2e7,3e7}){
        const double b=2e-4,pinf=1e6,q=2e4;double params[7]={1.4,b,pinf,q,0,0,0};
        if(model==3)checkEOS(singularity::NobleAbel(.4,1.,b,q),singularity::NobleAbel(.4,1.,b*1000,q*1e4),model,params,rho,e);
        else checkEOS(singularity::StiffGas(.4,1.,pinf,q),singularity::StiffGas(.4,1.,pinf*10,q*1e4),model,params,rho,e);
        ++samples;
      }
      double params[7]={1.4,.001,0,0,0,0,0},out[2];
      if(fem::upstream_eos::Runtime().evaluate(3,params,1000,1e6,out)!=1)throw std::runtime_error("Covolume singularity accepted");
      params[2]=2e9;if(fem::upstream_eos::Runtime().evaluate(4,params,1000,1e6,out)!=1)throw std::runtime_error("Negative temperature accepted");
      params[2]=4e8;if(fem::upstream_eos::Runtime().evaluate(4,params,1000,1e6,out)!=3)throw std::runtime_error("Clamped pressure accepted");
      std::cout<<"{\"samples\":"<<samples<<"}";return 0;
    }
    fem::GasParameters p;p.geometry=mode=="radial" || mode=="moving" ? 2 : 1;
    p.cells=argc>2 ? std::stoi(argv[2]) : 200;p.radius=1;p.chargeRadius=.5;
    p.productDensity=1;p.productEnergy=2.5;p.omega=.4;p.airDensity=.125;p.airPressure=.1;p.airGamma=1.4;
    double duration=argc>3 ? std::stod(argv[3]) : .2;
    if(mode=="expansion" || mode=="vacuum"){
      const double u=mode=="vacuum"?4:2;const auto c=fem::GasDynamics::SolveContact(1,-u,.4,std::sqrt(.56),1,u,.4,std::sqrt(.56));
      std::cout<<std::setprecision(16)<<"{\"pressure\":"<<c.pressure<<",\"velocity\":"<<c.velocity<<",\"fallback\":"<<(c.rarefaction?"true":"false")<<"}";return 0;
    }
    if(mode=="eos") {
      p.productLaw.model=1;p.A=20;p.B=3;p.R1=4.5;p.R2=1.1;p.omega=.3;
      const double rho=.7,e=100,delta=1e-6;
      const auto eos=fem::GasDynamics::ProductsEOS(p,rho,e);
      const auto plus=fem::GasDynamics::ProductsEOS(p,rho+delta,e+delta*eos.pressure/(rho*rho));
      const auto minus=fem::GasDynamics::ProductsEOS(p,rho-delta,e-delta*eos.pressure/(rho*rho));
      std::cout<<std::setprecision(16)<<"{\"pressure\":"<<eos.pressure<<",\"c2\":"<<eos.soundSpeedSquared<<",\"finiteDifference\":"<<(plus.pressure-minus.pressure)/(2*delta)<<"}";return 0;
    }
    if(mode=="contact" || mode=="moving")p.airPressure=1;
    if(mode=="axial"){p.geometry=2;p.chargeRadius=p.radius;p.productDensity=10;p.productEnergy=2.5e6;p.airPressure=1e5;p.ventEnds=2;p.specimenThickness=.05;}
    if(mode=="vented-gap" || mode=="vented-moving"){
      p=fem::GasParameters{};p.cells=argc>2 ? std::stoi(argv[2]) : 192;
      p.radius=.016;p.chargeRadius=.01;p.productDensity=1320;p.productEnergy=7380000000./1320;
      p.productLaw.model=1;p.A=586e9;p.B=21.6e9;p.R1=5.81;p.R2=1.77;p.omega=.282;
      p.airDensity=1.25;p.airPressure=1e5;p.airGamma=1.4;p.ventEnds=2;p.specimenThickness=.05;
    }
    if(mode=="radial"){p.chargeRadius=.25;p.productEnergy=25;}
    if(mode=="blast" || mode=="blast-moving" || mode=="blast-jwl") {
      p=fem::GasParameters{};p.cells=argc>2 ? std::stoi(argv[2]) : 192;
      if(mode=="blast-jwl"){p.productLaw.model=1;p.A=1e8;p.B=1e7;}
    }
    fem::GasDynamics gas(p);
    const double averagePressure=gas.Advance(duration,mode=="moving" ? .98 : mode=="blast-moving" ? .102 : mode=="vented-moving" ? p.radius*1.1 : p.radius);
    const auto s=gas.Snapshot();const auto pressure=gas.Pressures(),density=gas.Densities();
    std::cout<<std::setprecision(16)<<"{\"initialEnergy\":"<<gas.InitialEnergy()<<",\"internalEnergy\":"<<s.internalEnergy
      <<",\"kineticEnergy\":"<<s.kineticEnergy<<",\"wallWork\":"<<s.wallWork<<",\"wallPressure\":"<<s.wallPressure<<",\"substeps\":"<<s.substeps
      <<",\"rezones\":"<<s.rezones<<",\"airFilmTransitions\":"<<s.airFilmTransitions<<",\"productMass\":"<<s.productMass<<",\"airMass\":"<<s.airMass
      <<",\"ventedMass\":"<<s.ventedMass<<",\"ventedEnergy\":"<<s.ventedEnergy
      <<",\"averagePressure\":"<<averagePressure<<",\"cells\":[";
    for(std::size_t i=0;i<density.size();++i){if(i)std::cout<<",";std::cout<<"["<<.5*(gas.Positions()[i]+gas.Positions()[i+1])<<","<<density[i]<<","<<pressure[i]<<","<<gas.Velocities()[i]<<","<<gas.Positions()[i+1]-gas.Positions()[i]<<"]";}
    std::cout<<"]}";return 0;
  }catch(const std::exception& error){std::cerr<<error.what();return 1;}
}
