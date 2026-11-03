#pragma once
// Executed EOS dependency: unmodified LANL Singularity-EOS, no local equations.
#include "SingularityEOS.h"
#include <cmath>
#include <stdexcept>
namespace fem {
struct GasLaw {int model=0;double gamma=1.4,covolume=0,pressureOffset=0,energyShift=0;};
struct GasThermodynamics {double pressure=0,soundSpeedSquared=0;};
inline void GasLawCheck(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
inline GasLaw ActiveGasLaw(GasLaw c){GasLawCheck(c.model==0||c.model==3||c.model==4,"Unsupported gas model.");return c;}
inline void ValidateGasLaw(const GasLaw& c){GasLawCheck((c.model==0||c.model==3||c.model==4)&&c.gamma>1&&c.gamma<=10&&std::isfinite(c.gamma+c.covolume+c.pressureOffset+c.energyShift)&&c.covolume>=0&&c.pressureOffset>=0&&c.energyShift>=0,"Invalid gas model or parameters.");}
inline GasThermodynamics EvaluateUpstreamEOS(int model,const double* parameters,double rho,double energy){
 double result[2];const int status=upstream_eos::Runtime().evaluate(model,parameters,rho,energy,result);
 GasLawCheck(status==0,"Upstream gas EOS rejected density, energy, pressure or bulk modulus.");
 return {result[0],result[1]/rho};
}
inline GasThermodynamics EvaluateGasLaw(const GasLaw& c,double rho,double energy){
 ValidateGasLaw(c);const double parameters[7]={c.gamma,c.covolume,c.pressureOffset,c.energyShift,0,0,0};return EvaluateUpstreamEOS(c.model,parameters,rho,energy);
}
inline double GasEnergyFromPressure(const GasLaw& c,double rho,double pressure){
 ValidateGasLaw(c);const double parameters[7]={c.gamma,c.covolume,c.pressureOffset,c.energyShift,0,0,0};double energy;
 GasLawCheck(upstream_eos::Runtime().energy(c.model,parameters,rho,pressure,&energy)==0,"Gas EOS rejected pressure-to-energy conversion.");return energy;
}
}
