// ABI/units boundary only. EOS equations execute in the unmodified LANL headers.
#include <singularity-eos/eos/eos_jwl.hpp>
#include <singularity-eos/eos/eos_ideal.hpp>
#include <singularity-eos/eos/eos_noble_abel.hpp>
#include <singularity-eos/eos/eos_stiff.hpp>
#include <cmath>
#include <exception>

// Check before upstream constructors (which may abort on invalid parameters).
static bool valid_parameters(int model,const double* p){
  if(model==3||model==4){
    for(int i=0;i<4;++i)if(!std::isfinite(p[i]))return false;
    return p[0]>1&&p[1]>=0&&p[2]>=0&&p[3]>=0;
  }
  if(model==0)return std::isfinite(p[0])&&p[0]>1;
  if(model!=1)return false;
  for(int i=1;i<7;++i)if(!std::isfinite(p[i]))return false;
  return p[1]>0&&p[2]>=0&&p[3]>=0&&p[4]>0&&p[5]>0&&p[6]>0;
}
template<class EOS> static int evaluate_extra(const EOS& eos,double rho,double energy,double shift,double* out){
  if(!(energy>shift))return 1;
  out[0]=eos.PressureFromDensityInternalEnergy(rho,energy);
  out[1]=eos.BulkModulusFromDensityInternalEnergy(rho,energy);
  // A clamped pressure is outside this positive-pressure fluid solver's domain.
  return out[0]>singularity::robust::SMALL()&&out[1]>singularity::robust::SMALL()&&std::isfinite(out[0]+out[1])?0:3;
}
// These models have no rho-p inverse in this revision. Invert their existing
// pressure API numerically; no duplicate EOS equation is implemented here.
template<class EOS> static int invert_extra(const EOS& eos,double rho,double pressure,double shift,double* out){
  double lo=shift,hi=shift+1;
  for(int i=0;i<100&&eos.PressureFromDensityInternalEnergy(rho,hi)<pressure;++i)hi=shift+2*(hi-shift);
  if(!std::isfinite(hi)||eos.PressureFromDensityInternalEnergy(rho,hi)<pressure)return 3;
  for(int i=0;i<100;++i){double mid=lo+(hi-lo)/2;if(eos.PressureFromDensityInternalEnergy(rho,mid)<pressure)lo=mid;else hi=mid;}
  *out=lo+(hi-lo)/2;return std::isfinite(*out)&&*out>shift?0:3;
}

extern "C" __declspec(dllexport) const char* tensora_eos_source(){return "b4f71a7748770dfa6ce4d678754c463c09262fb7";}
extern "C" __declspec(dllexport) int tensora_eos_abi(){return 1;}
// SI: params={gamma,rho0,A,B,R1,R2,omega}; rho kg/m3, e J/kg, p Pa, bulk Pa.
// Cv=1 is a constructor-only placeholder: no temperature/entropy API is called;
// all rho-e pressure, bulk and rho-p energy methods below are independent of Cv.
extern "C" __declspec(dllexport) int tensora_eos_evaluate(int model,const double* params,double rho,double energy,double* result){
  if(!params||!result||!(rho>0&&energy>0)||!std::isfinite(rho+energy))return 1;
  if(model!=0&&model!=1&&model!=3&&model!=4)return 2;
  if(!valid_parameters(model,params))return 1;
  try{
    if(model==3){if(params[1]*rho>=1)return 1;return evaluate_extra(singularity::NobleAbel(params[0]-1,1.,params[1],params[3]),rho,energy,params[3],result);}
    if(model==4){if(rho*(energy-params[3])<=params[2])return 1;return evaluate_extra(singularity::StiffGas(params[0]-1,1.,params[2],params[3]),rho,energy,params[3],result);}
    if(model==1){
      const singularity::JWL eos(params[2],params[3],params[4],params[5],params[6],params[1],1.);
      result[0]=eos.PressureFromDensityInternalEnergy(rho,energy);
      result[1]=eos.BulkModulusFromDensityInternalEnergy(rho,energy);
    }else if(model==0){
      const singularity::IdealGas eos(params[0]-1,1.);
      result[0]=eos.PressureFromDensityInternalEnergy(rho,energy);
      result[1]=eos.BulkModulusFromDensityInternalEnergy(rho,energy);
    }else return 2;
    return result[0]>0&&result[1]>0&&std::isfinite(result[0]+result[1])?0:3;
  }catch(const std::exception&){return 4;}
}
extern "C" __declspec(dllexport) int tensora_eos_energy(int model,const double* params,double rho,double pressure,double* result){
  if(!params||!result||!(rho>0&&pressure>0)||!std::isfinite(rho+pressure))return 1;
  if(model!=0&&model!=1&&model!=3&&model!=4)return 2;
  if(!valid_parameters(model,params))return 1;
  try{
    if(model==3){if(params[1]*rho>=1)return 1;return invert_extra(singularity::NobleAbel(params[0]-1,1.,params[1],params[3]),rho,pressure,params[3],result);}
    if(model==4)return invert_extra(singularity::StiffGas(params[0]-1,1.,params[2],params[3]),rho,pressure,params[3],result);
    if(model==0){
      const singularity::IdealGas eos(params[0]-1,1.);
      eos.InternalEnergyFromDensityPressure(rho,pressure,*result);
    }else if(model==1){
      const singularity::JWL eos(params[2],params[3],params[4],params[5],params[6],params[1],1.);
      eos.InternalEnergyFromDensityPressure(rho,pressure,*result);
    }else return 2;
    return *result>0&&std::isfinite(*result)?0:3;
  }catch(const std::exception&){return 4;}
}
