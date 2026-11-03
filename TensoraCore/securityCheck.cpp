#include "ElementCalculations.h"
#include <algorithm>
#include <cmath>

namespace fem {
int CheckElementSecurity(double yield, double tensile, double compressive,
    const Eigen::Matrix2d& stress, int criterion, double nu, double sz) {
  // All criteria use the 3D principal state: sigma_z is supplied from the selected plane assumption.
  if (!stress.allFinite() || !std::isfinite(sz)) return 4;
  const double sx=stress(0,0), sy=stress(1,1);
  const double tau=0.5*(stress(0,1)+stress(1,0));
  const double mean=0.5*(sx+sy), radius=std::hypot(0.5*(sx-sy),tau);
  const double a=mean+radius, b=mean-radius;
  auto positive=[](double x){return std::isfinite(x) && x>0;};
  if (criterion==0) criterion=positive(yield)?4:1;
  if (criterion==3 || criterion==4) {
    if (!positive(yield)) return 4;
    const double equivalent=criterion==3 ? std::max({a,b,sz})-std::min({a,b,sz})
      : std::sqrt(std::max(0.0,sx*sx+sy*sy+sz*sz-sx*sy-sy*sz-sz*sx+3*tau*tau));
    return equivalent>=yield ? 3 : 0;
  }
  if ((criterion!=1 && criterion!=2) || !positive(tensile) || !positive(compressive)) return 4;
  double maximum=std::max(a,sz), minimum=std::min(b,sz);
  if (criterion==2) {
    if (!std::isfinite(nu) || nu<=-1 || nu>=0.5) return 4;
    // E*epsilon_i = sigma_i - nu*(sigma_j+sigma_k), including epsilon_z.
    maximum=std::max({a-nu*(b+sz),b-nu*(a+sz),sz-nu*(a+b)});
    minimum=std::min({a-nu*(b+sz),b-nu*(a+sz),sz-nu*(a+b)});
  }
  const double tensionIndex=std::max(0.0,maximum)/tensile;
  const double compressionIndex=std::max(0.0,-minimum)/compressive;
  if (std::max(tensionIndex,compressionIndex)<1.0) return 0;
  return compressionIndex>=tensionIndex ? 1 : 2;
}
} // namespace fem
