#pragma once
// Compression viscosity following Laghos' rho(2 h^2 |mu| + h c/2)
// scale. Project onto compressive strain-rate modes so numerical stabilization
// never introduces a tensile traction into the fracture constitutive law.
#include <Eigen/Dense>
#include <cmath>
namespace fem {
struct ShockStress {Eigen::Vector3d stress=Eigen::Vector3d::Zero();double coefficient=0,power=0;};
inline ShockStress CompressionViscosity(const Eigen::Vector3d& rate,double rho,double h,double sound){
  ShockStress result;const double mean=.5*(rate[0]+rate[1]),rad=std::hypot(.5*(rate[0]-rate[1]),.5*rate[2]);
  const double low=mean-rad;if(low>=0)return result;
  const double high=std::min(0.,mean+rad),factor=rad>0 ? (high-low)/(2*rad) : 0;
  Eigen::Vector3d negative;negative<<.5*(high+low)+factor*.5*(rate[0]-rate[1]),.5*(high+low)-factor*.5*(rate[0]-rate[1]),factor*.5*rate[2];
  result.coefficient=rho*(2*h*h*(-low)+.5*h*sound);result.stress=result.coefficient*negative;
  result.power=result.stress.dot(rate);return result;
}
}
