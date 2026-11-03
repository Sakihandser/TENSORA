// Dynamics/Newmark adapted from MFEM 4.10 ex10, ex23 and linalg/ode.cpp.
// Copyright (c) 2010-2026 Lawrence Livermore National Security, LLC.
// BSD-3-Clause: ../mfem-4.10/LICENSE. TRI3 damage, preload, quiet boundaries
// and streamed history are application additions; see ../docs/BLAST_DYNAMICS.md.
#include "BlastDynamics.h"
#include "GasDynamics.h"
#include "RockConstitutive.h"
#include "ShockViscosity.h"
#include <Eigen/Dense>
#include <Eigen/Sparse>
#include <Eigen/SparseCholesky>
#include <algorithm>
#include <array>
#include <cmath>
#include <chrono>
#include <iostream>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <limits>
#include <map>
#include <memory>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <tuple>
#include <unordered_map>
#include <vector>

namespace fem {
namespace {
using V6=Eigen::Matrix<double,6,1>;
using B36=Eigen::Matrix<double,3,6>;
struct Cell {
  std::array<std::size_t,3> nodes;
  B36 B;
  Eigen::Matrix2d previousF=Eigen::Matrix2d::Identity();
  double initialJacobian=1,currentJacobian=1,planarJacobian=1,localTimeLimit=1,initialZz=0;
  Eigen::Matrix3d D;
  double area,E,rho,nu,damage=0,viscousPower=0,altitude=0;
  Eigen::Vector3d strain=Eigen::Vector3d::Zero(),stress=Eigen::Vector3d::Zero(),initialStress=Eigen::Vector3d::Zero();
  rock::Parameters rockParameters;
  rock::State rockState;
  std::vector<std::size_t> neighbours;
  bool cavityCell=false;
};
struct Edge {std::size_t a=0,b=0,third=0,cell=0;int count=0;};
struct Groups {
  std::vector<std::size_t> p;
  explicit Groups(std::size_t n):p(n){std::iota(p.begin(),p.end(),0);}
  std::size_t Find(std::size_t i){while(p[i]!=i){p[i]=p[p[i]];i=p[i];}return i;}
  void Join(std::size_t a,std::size_t b){a=Find(a);b=Find(b);if(a!=b)p[b]=a;}
};
std::string TextArg(int argc,char* argv[],const std::string& key,const std::string& fallback="") {
  for(int i=1;i<argc;++i)if(argv[i]==key){if(++i>=argc)throw std::runtime_error("Missing blast setting: "+key);return argv[i];}
  return fallback;
}
double Arg(int argc,char* argv[],const std::string& key,double fallback) {
  const auto text=TextArg(argc,argv,key);if(text.empty())return fallback;
  std::size_t used=0;const double x=std::stod(text,&used);
  if(used!=text.size() || !std::isfinite(x))throw std::runtime_error("Invalid blast setting: "+key);
  return x;
}
void Require(bool ok,const char* msg){if(!ok)throw std::runtime_error(msg);}
double Equivalent(const Eigen::Vector3d& s,double zz=0){return std::sqrt(std::max(0.,s[0]*s[0]+s[1]*s[1]+zz*zz-s[0]*s[1]-s[1]*zz-zz*s[0]+3*s[2]*s[2]));}
template<typename T>void Raw(std::ostream& out,const T& x){out.write(reinterpret_cast<const char*>(&x),sizeof(x));}
}

int RunBlastDynamics(const CalculationModel& model,int argc,char* argv[],std::ostream& out) {
  const double cx=Arg(argc,argv,"--blast-x",0),cy=Arg(argc,argv,"--blast-y",0),radius=Arg(argc,argv,"--blast-radius",.1);
  const double peak=Arg(argc,argv,"--blast-pressure",1e7),pulse=Arg(argc,argv,"--blast-pulse",1e-4),duration=Arg(argc,argv,"--blast-duration",1e-3);
  const double requestedDt=Arg(argc,argv,"--blast-dt",0),damping=Arg(argc,argv,"--blast-damping",0),gf=Arg(argc,argv,"--blast-gf",100);
  const double frameSetting=Arg(argc,argv,"--blast-frames",61),fracture=Arg(argc,argv,"--blast-fracture",1);
  const double boundarySetting=Arg(argc,argv,"--blast-boundary",0),loadMode=Arg(argc,argv,"--blast-loadMode",0);
  const double confineX=Arg(argc,argv,"--blast-confineX",0),confineY=Arg(argc,argv,"--blast-confineY",0);
  const double planeMode=Arg(argc,argv,"--blast-planeMode",0);
  const double rockModel=Arg(argc,argv,"--blast-rockModel",3),gasFracture=Arg(argc,argv,"--blast-gasFracture",0),crackDamage=Arg(argc,argv,"--blast-crackDamage",.95);
  const double kinematics=Arg(argc,argv,"--blast-kinematics",0);
  const double shockSetting=Arg(argc,argv,"--blast-shockViscosity",1);Require(shockSetting==0 || shockSetting==1,"Invalid shock stabilization setting.");
  Require(kinematics==0 || kinematics==1,"Invalid blast kinematics.");
  Require((rockModel==1||rockModel==3||rockModel==6) && (gasFracture==0 || gasFracture==1) && crackDamage>0 && crackDamage<=1,"Invalid rock or fracture-storage selection.");
  std::map<int,rock::Parameters> rockCards;
  std::map<int,std::array<double,4>> jh2ElasticResponse;
  const auto rockFile=TextArg(argc,argv,"--blast-rock-file");
  if(!rockFile.empty()){
    std::ifstream file(std::filesystem::u8path(rockFile));Require(file.good(),"Cannot read rock material cards.");
    std::string line;while(std::getline(file,line)){if(line.empty())continue;std::istringstream row(line);int id;rock::Parameters p;
      Require(bool(row>>id>>p.law),"Malformed rock material card.");
      Require(id>0 && (p.law==1||p.law==3||p.law==6) && !rockCards.count(id),"Invalid/duplicate rock material card.");
      if(p.law==3)Require(bool(row>>p.A>>p.N>>p.B>>p.M>>p.C>>p.rate0>>p.HEL>>p.pHEL>>p.T>>p.D1>>p.D2>>p.maxStrength>>p.K1>>p.K2>>p.K3>>p.beta>>p.referenceLength>>p.normalizationStress>>p.friction>>p.dilation),"Malformed JH2 material card.");
      if(p.law==6)Require(bool(row>>p.friction>>p.dilation>>p.cohesion>>p.tension>>p.softening>>p.residualFriction>>p.residualDilation>>p.residualCohesion>>p.peakStrain>>p.residualStrain),"Malformed Mohr-Coulomb card.");
      std::string extra;
      while(row>>extra){
        if(extra=="ELAS1"){Require(bool(row>>p.inputShearModulus>>p.inputBulkModulus) && std::isfinite(p.inputShearModulus+p.inputBulkModulus) && p.inputShearModulus>=0 && p.inputBulkModulus>=0,"Malformed JH2 elastic moduli.");}
        else if(extra=="GF1"){Require(!p.hasFractureEnergy && bool(row>>p.gf) && std::isfinite(p.gf) && p.gf>0,"Malformed material fracture energy.");p.hasFractureEnergy=true;}
        else Require(false,"Malformed rock material card.");
      }
      rockCards[id]=p;
    }
  }
  const double sourceMode=Arg(argc,argv,"--blast-sourceMode",0),productEOS=Arg(argc,argv,"--blast-productEOS",0);
  Require((sourceMode==0 || sourceMode==1) && (productEOS==0 || productEOS==1||productEOS==3||productEOS==4),"Invalid gas source or product EOS mode.");
  const bool gasMode=sourceMode==1;
  Require(radius>0 && peak>=0 && pulse>0 && duration>0 && (gasMode || duration>=pulse),"Blast radius/times must be positive, pressure nonnegative, pulse <= duration.");
  GasParameters gasParameters;gasParameters.radius=radius;
  gasParameters.chargeRadius=Arg(argc,argv,"--blast-chargeRadius",radius);
  gasParameters.productDensity=Arg(argc,argv,"--blast-productDensity",1000);
  gasParameters.productEnergy=Arg(argc,argv,"--blast-productEnergy",1e6);
  gasParameters.A=productEOS==1 ? Arg(argc,argv,"--blast-jwlA",0) : 0;
  gasParameters.B=productEOS==1 ? Arg(argc,argv,"--blast-jwlB",0) : 0;
  gasParameters.R1=productEOS==1 ? Arg(argc,argv,"--blast-jwlR1",4.5) : 4.5;
  gasParameters.R2=productEOS==1 ? Arg(argc,argv,"--blast-jwlR2",1.1) : 1.1;
  gasParameters.omega=productEOS==1 ? Arg(argc,argv,"--blast-jwlOmega",.3) : Arg(argc,argv,"--blast-productGamma",1.3)-1;

  gasParameters.airDensity=Arg(argc,argv,"--blast-airDensity",1.2);gasParameters.airPressure=Arg(argc,argv,"--blast-airPressure",101325);
  gasParameters.airGamma=Arg(argc,argv,"--blast-airGamma",1.4);
  const double airEOS=Arg(argc,argv,"--blast-airEOS",0);
  Require(airEOS==0||airEOS==3||airEOS==4,"Invalid gas source or product EOS mode.");
  gasParameters.productLaw.model=static_cast<int>(productEOS);gasParameters.productLaw.gamma=gasParameters.omega+1;
  gasParameters.airLaw.model=static_cast<int>(airEOS);gasParameters.airLaw.gamma=gasParameters.airGamma;
  gasParameters.productLaw.covolume=Arg(argc,argv,"--blast-productCovolume",0);gasParameters.productLaw.pressureOffset=Arg(argc,argv,"--blast-productPressureOffset",0);gasParameters.productLaw.energyShift=Arg(argc,argv,"--blast-productEnergyShift",0);
  gasParameters.airLaw.covolume=Arg(argc,argv,"--blast-airCovolume",0);gasParameters.airLaw.pressureOffset=Arg(argc,argv,"--blast-airPressureOffset",0);gasParameters.airLaw.energyShift=Arg(argc,argv,"--blast-airEnergyShift",0);
  const double ventEnds=Arg(argc,argv,"--blast-ventEnds",0);Require(ventEnds>=0 && ventEnds<=2 && std::floor(ventEnds)==ventEnds,"Invalid axial vent geometry or opening time.");
  gasParameters.ventEnds=static_cast<int>(ventEnds);gasParameters.specimenThickness=Arg(argc,argv,"--blast-specimenThickness",.05);gasParameters.ventOpeningTime=Arg(argc,argv,"--blast-ventOpeningTime",0);
  const double gasCellSetting=Arg(argc,argv,"--blast-gasCells",192);
  Require(gasCellSetting>=16 && gasCellSetting<=2048 && std::floor(gasCellSetting)==gasCellSetting,"Gas cells must be an integer from 16 to 2048.");
  gasParameters.cells=static_cast<int>(gasCellSetting);
  std::unique_ptr<GasDynamics> gas;
  if(gasMode){
    Require(productEOS!=1 || gasParameters.A>0 || gasParameters.B>0,"JWL requires user-supplied expansion coefficients; use ideal products for verification.");
    gas=std::make_unique<GasDynamics>(gasParameters);
  }
  Require(requestedDt>=0 && damping>=0 && gf>0 && frameSetting>=2 && frameSetting<=201 && std::floor(frameSetting)==frameSetting &&
    (fracture==0 || fracture==1) && boundarySetting>=0 && boundarySetting<=3 && std::floor(boundarySetting)==boundarySetting &&
    (loadMode==0 || loadMode==1) && (planeMode==0 || planeMode==1) && confineX>=0 && confineY>=0,"Invalid blast integration/boundary/load settings.");
  Require(!model.elements.empty() && model.nodes.size()>=3,"Blast requires a triangular mesh.");
  const std::size_t nn=model.nodes.size(),nd=nn*2;
  Require(nd<std::numeric_limits<int>::max() && (4.*nn+7.*model.elements.size()+(gasMode ? 12 : 8))*8<=256.*1024*1024,"A single blast frame exceeds 256 MiB; partition the model.");
  int frames=static_cast<int>(frameSetting);
  std::unordered_map<int,std::size_t> nodeIndex;
  for(std::size_t i=0;i<nn;++i)Require(nodeIndex.emplace(model.nodes[i].nodeNo,i).second,"Duplicate blast node number.");
  Eigen::VectorXd mass=Eigen::VectorXd::Zero(nd),bound=mass,u=mass,v=mass,a=mass,pressureForce=mass,external=mass;
  std::vector<bool> fixed(nd);
  for(std::size_t i=0;i<nn;++i){const auto& n=model.nodes[i];fixed[2*i]=n.fixUx;fixed[2*i+1]=n.fixUy;external[2*i]=n.forceX;external[2*i+1]=n.forceY;}
  // Node force is the canonical assembled load, as in the static solver.
  // elementNodeLoads are redundant export records and must NOT be added twice.
  std::map<std::pair<std::size_t,std::size_t>,Edge> edges;
  std::vector<Cell> cells;cells.reserve(model.elements.size());
  bool advanced=rockModel!=0 || gasFracture!=0 || kinematics!=0 || ventEnds>0 || planeMode==1;
  Groups solidGroups(nn),boundaryGroups(nn);
  for(const auto& e:model.elements){
    Cell c;c.nodes={nodeIndex.at(e.node1),nodeIndex.at(e.node2),nodeIndex.at(e.node3)};
    const auto& p=model.nodes[c.nodes[0]];const auto& q=model.nodes[c.nodes[1]];const auto& r=model.nodes[c.nodes[2]];
    const double det=(q.x-p.x)*(r.y-p.y)-(r.x-p.x)*(q.y-p.y);
    c.area=.5*std::abs(det);c.E=e.elasticModulus;c.rho=e.density;c.nu=e.poissonRatio;
    c.altitude=2*c.area/std::max({std::hypot(q.x-p.x,q.y-p.y),std::hypot(r.x-q.x,r.y-q.y),std::hypot(p.x-r.x,p.y-r.y)});
    if(rockCards.count(e.materialNo))c.rockParameters=rockCards.at(e.materialNo);
    else Require(false,"Every solid material requires a valid constitutive card.");
    auto& rp=c.rockParameters;rp.E=c.E;rp.nu=c.nu;rp.ft=e.tensileStrength;rp.fc=e.compressiveStrength;if(!rp.hasFractureEnergy)rp.gf=gf;rp.h=std::sqrt(2*c.area);
    rp.logarithmicVolume=kinematics==1;rp.density=c.rho;
    Require(kinematics!=1 || planeMode!=0 || rp.law==3,"Finite-deformation plane stress currently supports JH2 only.");
    if(rp.law==6){
      Require(kinematics==0&&planeMode==1,"Mohr-Coulomb requires small-strain plane strain.");
      Require(std::isfinite(rp.friction+rp.dilation+rp.cohesion+rp.tension+rp.softening+rp.residualFriction+rp.residualDilation+rp.residualCohesion+rp.peakStrain+rp.residualStrain),"Invalid Mohr-Coulomb parameters.");
      Require(rp.friction>0&&rp.friction<89&&rp.dilation>=0&&rp.dilation<=rp.friction&&rp.cohesion>0&&rp.tension>0&&(rp.softening==0||rp.softening==1)&&rp.residualFriction>0&&rp.residualFriction<=rp.friction&&rp.residualDilation>=0&&rp.residualDilation<=rp.residualFriction&&rp.residualCohesion>0&&rp.residualCohesion<=rp.cohesion&&rp.peakStrain>=0&&rp.residualStrain>rp.peakStrain,"Invalid Mohr-Coulomb parameters.");
    }
    if(rp.law==3){
      Require(rp.A>0 && rp.N>0 && rp.B>=0 && rp.M>0 && rp.C>=0 && rp.rate0>0 && rp.HEL>rp.pHEL && rp.pHEL>0 && rp.T>0 && rp.D1>0 && rp.D2>=0 && rp.maxStrength>=0 && rp.K1>0 && rp.K3>=0 && rp.beta>=0 && rp.beta<=1 && rp.referenceLength>=0 && rp.normalizationStress>=0,"Invalid JH2 parameters.");
      Require((rp.K3>0 || rp.K2>=0) && (rp.K2>=0 || rp.K1-rp.K2*rp.K2/(3*rp.K3)>0),"JH2 compression EOS is not hyperbolic.");
      // JH2's EOS controls initial bulk stiffness; G still comes from E/nu.
      const double G=rp.G(),K=rp.K1;rp.E=c.E=9*K*G/(3*K+G);rp.nu=c.nu=(3*K-2*G)/(2*(3*K+G));
      jh2ElasticResponse[e.materialNo]={rp.inputBulkModulus>0 ? rp.inputBulkModulus : e.elasticModulus/(3*(1-2*e.poissonRatio)),K,G,std::sqrt((K+4*G/3)/c.rho)};
    }
    Require(c.area>1e-18 && std::isfinite(c.area) && c.rho>0 && std::isfinite(c.rho) && c.E>0 && std::isfinite(c.E) && c.nu>-1 && c.nu<.5,
      "Blast elements require positive area, density, E and -1 < nu < 0.5.");
    rock::InitializeMaterial(rp);
    const double s1=((q.x-p.x)*(cy-p.y)-(q.y-p.y)*(cx-p.x))/det,s2=((cx-p.x)*(r.y-p.y)-(cy-p.y)*(r.x-p.x))/det;
    Require(!(s1>=-1e-10 && s2>=-1e-10 && s1+s2<=1+1e-10),"Blast center must lie in an explicitly meshed circular cavity.");
    const double gx[3]={(q.y-r.y)/det,(r.y-p.y)/det,(p.y-q.y)/det},gy[3]={(r.x-q.x)/det,(p.x-r.x)/det,(q.x-p.x)/det};
    c.B.setZero();for(int j=0;j<3;++j){c.B(0,2*j)=gx[j];c.B(1,2*j+1)=gy[j];c.B(2,2*j)=gy[j];c.B(2,2*j+1)=gx[j];}
    c.D<<1,c.nu,0,c.nu,1,0,0,0,(1-c.nu)/2;c.D*=c.E/(1-c.nu*c.nu);
    if(planeMode==1){c.D<<1-c.nu,c.nu,0,c.nu,1-c.nu,0,0,0,(1-2*c.nu)/2;c.D*=c.E/((1+c.nu)*(1-2*c.nu));}
    const Eigen::Matrix<double,6,6> k=c.area*c.B.transpose()*c.D*c.B;
    const double stiffnessBound=1.;
    for(int j=0;j<6;++j){const auto d=2*c.nodes[j/2]+j%2;mass[d]+=c.rho*c.area/3;bound[d]+=stiffnessBound*k.row(j).cwiseAbs().sum();}
    for(int j=0;j<3;++j){
      const auto aa=c.nodes[j],bb=c.nodes[(j+1)%3];solidGroups.Join(aa,bb);
      auto& edge=edges[std::minmax(aa,bb)];edge.a=aa;edge.b=bb;edge.third=c.nodes[(j+2)%3];edge.cell=cells.size();++edge.count;
      Require(edge.count<=2,"Blast mesh contains a nonmanifold edge.");
    }
    cells.push_back(c);
  }
  for(const auto& item:edges)if(item.second.count==1)boundaryGroups.Join(item.second.a,item.second.b);
  const bool shock=shockSetting==1 && (gasMode || std::any_of(cells.begin(),cells.end(),[](const Cell& c){return c.rockParameters.law==3;}));
  const bool adaptiveTime=shock || kinematics==1 || std::any_of(cells.begin(),cells.end(),[](const Cell& c){return c.rockParameters.law==3;});
  const int cellScalars=10;
  Require((24.+4.*nn+cellScalars*cells.size())*8<=256.*1024*1024,"A single blast frame exceeds 256 MiB; partition the model.");
  // Shared edges supply the crack connectivity graph, including material interfaces.
  std::map<std::pair<std::size_t,std::size_t>,std::size_t> edgeOwner;
  for(std::size_t k=0;k<cells.size();++k)for(int j=0;j<3;++j){auto key=std::minmax(cells[k].nodes[j],cells[k].nodes[(j+1)%3]);auto found=edgeOwner.find(key);
    if(found==edgeOwner.end())edgeOwner[key]=k;else {cells[k].neighbours.push_back(found->second);cells[found->second].neighbours.push_back(k);}}
  std::map<std::size_t,double> boundaryAreas;
  for(const auto& item:edges)if(item.second.count==1){
    const auto& e=item.second;const auto& p=model.nodes[e.a];const auto& q=model.nodes[e.b];const auto& r=model.nodes[e.third];
    const double cross=(q.x-p.x)*(r.y-p.y)-(q.y-p.y)*(r.x-p.x);
    boundaryAreas[boundaryGroups.Find(e.a)]+=(cross>0 ? 1 : -1)*(p.x*q.y-p.y*q.x);
  }
  std::map<std::pair<std::size_t,std::size_t>,int> overrides;
  const auto boundaryFile=TextArg(argc,argv,"--blast-boundary-file");
  if(!boundaryFile.empty()){
    std::ifstream input(std::filesystem::u8path(boundaryFile));Require(input.good(),"Cannot read blast boundary overrides.");
    int na,nb,mode;
    while(input>>na>>nb>>mode){
      Require(mode>=0 && mode<=3 && nodeIndex.count(na) && nodeIndex.count(nb),"Invalid blast boundary override.");
      auto key=std::minmax(nodeIndex.at(na),nodeIndex.at(nb));
      Require(edges.count(key) && edges.at(key).count==1,"Boundary override must reference a true exterior mesh edge.");
      Require(overrides.emplace(key,mode).second,"Duplicate blast boundary override.");
    }
    Require(input.eof(),"Malformed blast boundary override file.");
  }
  std::vector<Eigen::Matrix2d> dashpot(nn,Eigen::Matrix2d::Zero());
  std::vector<int> nodeMode(nn,0);
  std::map<std::size_t,int> loadedDegree;
  int loadedEdges=0,absorbingEdges=0,fixedBoundaryEdges=0;
  auto thickness=[&](const Cell& c){return kinematics==1 && planeMode==0 ? std::exp(c.rockState.strain(2,2)) : 1.;};
  std::vector<std::tuple<std::size_t,std::size_t,double,std::size_t>> cavitySegments;
  std::vector<std::tuple<std::size_t,std::size_t,double,std::size_t>> confinementSegments;
  for(const auto& item:edges){
    const auto& e=item.second;if(e.count!=1)continue;
    const auto& p=model.nodes[e.a];const auto& q=model.nodes[e.b];const auto& r=model.nodes[e.third];
    const double dx=q.x-p.x,dy=q.y-p.y,length=std::hypot(dx,dy);
    Eigen::Vector2d inward(-dy/length,dx/length);
    if(inward.dot(Eigen::Vector2d(r.x-(p.x+q.x)/2,r.y-(p.y+q.y)/2))<0)inward=-inward;
    const double tol=std::max(radius*.03,1e-10);
    const bool cavity=boundaryAreas[boundaryGroups.Find(e.a)]<0 && std::abs(std::hypot(p.x-cx,p.y-cy)-radius)<=tol && std::abs(std::hypot(q.x-cx,q.y-cy)-radius)<=tol;
    if(cavity){
      cells[e.cell].cavityCell=true;
      cavitySegments.emplace_back(e.a,e.b,inward.dot(Eigen::Vector2d(-dy/length,dx/length)),e.cell);
      Require(inward.dot(Eigen::Vector2d((p.x+q.x)/2-cx,(p.y+q.y)/2-cy))>0,"Selected pressure boundary is not a cavity wall.");
      for(auto i:{e.a,e.b}){pressureForce.segment<2>(2*i)+=.5*length*inward;++loadedDegree[i];}++loadedEdges;continue;
    }
    const bool outer=boundaryAreas[boundaryGroups.Find(e.a)]>0;
    if(outer)confinementSegments.emplace_back(e.a,e.b,inward.dot(Eigen::Vector2d(-dy/length,dx/length)),e.cell);
    const auto overrideMode=overrides.find(item.first);
    const int mode=overrideMode!=overrides.end() ? overrideMode->second : outer ? static_cast<int>(boundarySetting) : 0;
    if(outer)for(auto i:{e.a,e.b}){external[2*i]+=.5*length*confineX*inward[0];external[2*i+1]+=.5*length*confineY*inward[1];}
    if(mode==3)++fixedBoundaryEdges;
    for(auto i:{e.a,e.b})nodeMode[i]=std::max(nodeMode[i],mode);
    if(mode==2){
      const auto& c=cells[e.cell];const double cp=std::sqrt(c.D(0,0)/c.rho),cs=std::sqrt(c.E/(2*c.rho*(1+c.nu)));
      Eigen::Matrix2d C=.5*length*c.rho*(cs*Eigen::Matrix2d::Identity()+(cp-cs)*inward*inward.transpose());

      for(auto i:{e.a,e.b})dashpot[i]+=C;++absorbingEdges;
    }
  }
  Require(loadedEdges>=6,"No closed circular cavity with at least 6 boundary edges matches blast center/radius.");
  for(const auto& item:loadedDegree)Require(item.second==2,"Blast cavity boundary must be a complete closed loop.");
  for(std::size_t i=0;i<nn;++i)if(nodeMode[i])fixed[2*i]=fixed[2*i+1]=nodeMode[i]==3;
  double lambdaBound=0;
  for(std::size_t i=0;i<nd;++i){Require(mass[i]>0 && std::isfinite(mass[i]) && std::isfinite(bound[i]),"Unconnected node or invalid blast mass/stiffness.");if(!fixed[i])lambdaBound=std::max(lambdaBound,bound[i]/mass[i]);}
  Require(lambdaBound>0 && std::isfinite(lambdaBound),"Blast model has no movable degrees of freedom.");
  const double stableDt=1.4/std::sqrt(lambdaBound);
  double sourceDt=pulse/20;
  if(gasMode){
    const auto products=GasDynamics::ProductsEOS(gasParameters,gasParameters.productDensity,gasParameters.productEnergy);
    const auto air=GasDynamics::AirEOS(gasParameters,gasParameters.airDensity,GasDynamics::AirEnergy(gasParameters,gasParameters.airDensity,gasParameters.airPressure));
    const double sound=std::max(std::sqrt(products.soundSpeedSquared),std::sqrt(air.soundSpeedSquared));
    const double gap=radius-gasParameters.chargeRadius;
    sourceDt=std::min(gasParameters.chargeRadius,gap>radius*1e-8 ? gap : radius)/(20*sound);
    external+=gasParameters.airPressure*pressureForce;
  }
  // Prescribed far-field Cauchy stress acts on the CURRENT boundary. Keeping
  // the original nodal forces instead changes traction and produces a spurious
  // torque on an obliquely layered body as it deforms.
  auto followerForce=[&](const Eigen::VectorXd& displacement,bool includeAir=false){
    Eigen::VectorXd f=Eigen::VectorXd::Zero(nd);
    auto add=[&](const auto& segments,double sx,double sy){for(const auto& edge:segments){
      const auto aa=std::get<0>(edge),bb=std::get<1>(edge);const double sign=std::get<2>(edge);
      const double dx=model.nodes[bb].x+displacement[2*bb]-model.nodes[aa].x-displacement[2*aa];
      const double dy=model.nodes[bb].y+displacement[2*bb+1]-model.nodes[aa].y-displacement[2*aa+1];
      const Eigen::Vector2d traction=.5*sign*thickness(cells[std::get<3>(edge)])*Eigen::Vector2d(-sx*dy,sy*dx);
      f.segment<2>(2*aa)+=traction;f.segment<2>(2*bb)+=traction;
    }};
    add(confinementSegments,confineX,confineY);
    if(includeAir && gasMode)add(cavitySegments,gasParameters.airPressure,gasParameters.airPressure);
    return f;
  };
  const Eigen::VectorXd originalConfinement=followerForce(u);
  const Eigen::VectorXd deadExternal=external-originalConfinement;
  auto externalAt=[&](const Eigen::VectorXd& displacement)->Eigen::VectorXd{
    return kinematics==1 ? (deadExternal+followerForce(displacement)).eval() : external;
  };
  const double dtLimit=std::min(stableDt,sourceDt);
  Require(requestedDt==0 || requestedDt<=dtLimit*(1+1e-12),"Requested blast dt exceeds stability or pressure-resolution limit; use dt=0.");
  const double stepsNeeded=std::ceil(duration/(requestedDt>0 ? requestedDt : dtLimit));
  Require(std::isfinite(stepsNeeded) && stepsNeeded<=20000000,"Blast needs over 20 million steps; check tiny elements or simulation duration.");
  const int steps=static_cast<int>(stepsNeeded);frames=std::min(frames,steps+1);double dt=duration/steps;const double baseDt=dt;
  const int workers=cells.size()>=4096 ? static_cast<int>(std::min(8u,std::max(1u,std::thread::hardware_concurrency()))) : 1;
  std::vector<V6> localForce(cells.size());
  std::vector<std::vector<std::pair<std::size_t,int>>> incident(nn);
  for(std::size_t k=0;k<cells.size();++k)for(int j=0;j<3;++j)incident[cells[k].nodes[j]].push_back({k,j});
  auto shockForce=[&](Cell& c,const B36& B){
    c.viscousPower=0;V6 force=V6::Zero();if(!shock)return force;
    V6 velocity;for(int j=0;j<6;++j)velocity[j]=v[2*c.nodes[j/2]+j%2];const Eigen::Vector3d rate=B*velocity;
    const double rho=c.rho/c.currentJacobian,h=c.rockParameters.h*std::sqrt(c.planarJacobian);
    double bulk=c.rockParameters.K();
    if(c.rockParameters.law==3){const double mu=std::max(0.,rock::CompressionMu(c.rockParameters,c.rockState.strain.trace()));bulk=(c.rockParameters.K1+2*c.rockParameters.K2*mu+3*c.rockParameters.K3*mu*mu)*(1+mu);}
    const double sound=std::sqrt((planeMode==1 ? bulk+4*c.rockParameters.G()/3 : c.D(0,0))/rho);
    const auto visc=CompressionViscosity(rate,rho,h,sound);c.viscousPower=c.area*c.currentJacobian*visc.power;
    force=c.area*c.currentJacobian*B.transpose()*visc.stress;
    const double altitude=c.altitude*std::sqrt(c.planarJacobian);
    c.localTimeLimit=std::min(c.localTimeLimit,.45/(sound/altitude+2.5*visc.coefficient/(rho*altitude*altitude)));
    return force;
  };
  bool initializing=false;double materialEvaluationTime=0;
  auto internal=[&,workers](bool evolve){
    std::string rockError;
    #pragma omp parallel for num_threads(workers) if(workers>1)
    for(int k=0;k<static_cast<int>(cells.size());++k){
      auto& c=cells[k];V6 ue;for(int j=0;j<6;++j)ue[j]=u[2*c.nodes[j/2]+j%2];c.strain=c.B*ue;
      if(evolve){
        try {
          B36 spatialB=c.B;
          if(kinematics==1){
            Eigen::Matrix2d F=Eigen::Matrix2d::Identity();
            for(int j=0;j<3;++j){F(0,0)+=ue[2*j]*c.B(0,2*j);F(0,1)+=ue[2*j]*c.B(1,2*j+1);F(1,0)+=ue[2*j+1]*c.B(0,2*j);F(1,1)+=ue[2*j+1]*c.B(1,2*j+1);}
            const double J=F.determinant();
            if(!(J>1e-4 && F.allFinite())){
              std::ostringstream diagnostic;diagnostic<<std::setprecision(17)
                <<"Finite-deformation mesh inverted/collapsed: element="<<model.elements[k].elementNo
                <<", Jxy="<<J<<", previousJxy="<<c.previousF.determinant()
                <<", thicknessStretch="<<thickness(c)<<", damage="<<c.rockState.damage
                <<", time="<<materialEvaluationTime<<", dt="<<dt<<", previousStress=["<<c.rockState.stress(0,0)<<","<<c.rockState.stress(1,1)<<","<<c.rockState.stress(0,1)<<"]"
                <<", Fxy=["<<F(0,0)<<","<<F(0,1)<<","<<F(1,0)<<","<<F(1,1)<<"]";
              throw std::runtime_error(diagnostic.str());
            }
            const Eigen::Matrix2d relative=F*c.previousF.inverse();
            // Closed-form 2D polar decomposition avoids an eigensolver in every
            // element at every explicit step, including the unperturbed bulk.
            const double cosine=relative(0,0)+relative(1,1),sine=relative(1,0)-relative(0,1),norm=std::hypot(cosine,sine);
            Require(norm>0,"Invalid finite-deformation stretch.");Eigen::Matrix2d R;R<<cosine/norm,-sine/norm,sine/norm,cosine/norm;
            const Eigen::Matrix2d stretch=R.transpose()*relative;const double mean=.5*stretch.trace(),radius=std::hypot(.5*(stretch(0,0)-stretch(1,1)),stretch(0,1));
            const double plus=mean+radius,minus=relative.determinant()/plus;Require(minus>0 && plus>0,"Invalid finite-deformation stretch.");
            const double logPlus=std::log(plus),logMinus=std::log(minus),factor=radius>1e-12 ? (logPlus-logMinus)/(2*radius) : 1/mean;
            const Eigen::Matrix2d logU=.5*(logPlus+logMinus)*Eigen::Matrix2d::Identity()+factor*(stretch-mean*Eigen::Matrix2d::Identity());
            rock::Tensor rotation=rock::Tensor::Identity();rotation.block<2,2>(0,0)=R;
            c.rockState.stress=(rotation*c.rockState.stress*rotation.transpose()).eval();c.rockState.effective=(rotation*c.rockState.effective*rotation.transpose()).eval();c.rockState.strain=(rotation*c.rockState.strain*rotation.transpose()).eval();
            const Eigen::Matrix2d delta=R*logU*R.transpose();c.strain<<c.rockState.strain(0,0)+delta(0,0),c.rockState.strain(1,1)+delta(1,1),2*(c.rockState.strain(0,1)+delta(0,1));
            const Eigen::Matrix2d inverse=F.inverse().transpose();spatialB.setZero();
            for(int j=0;j<3;++j){const Eigen::Vector2d gradient=inverse*Eigen::Vector2d(c.B(0,2*j),c.B(1,2*j+1));spatialB(0,2*j)=gradient[0];spatialB(1,2*j+1)=gradient[1];spatialB(2,2*j)=gradient[1];spatialB(2,2*j+1)=gradient[0];}
            c.previousF=F;c.planarJacobian=J;c.currentJacobian=J;
            double maxEdge=0;for(int j=0;j<3;++j){const auto a=c.nodes[j],b=c.nodes[(j+1)%3];maxEdge=std::max(maxEdge,std::hypot(model.nodes[a].x+u[2*a]-model.nodes[b].x-u[2*b],model.nodes[a].y+u[2*a+1]-model.nodes[b].y-u[2*b+1]));}
            // The material call below determines the transverse logarithmic
            // strain. Density and internal-force volume then use det(F_3D).
            c.localTimeLimit=2*c.area*J/maxEdge;
          }
          c.rockState=rock::Advance(c.rockParameters,c.rockState,c.strain,dt,planeMode==1,fracture!=0 && !initializing);
          if(kinematics==1){
            c.currentJacobian=c.planarJacobian*thickness(c);
            Require(c.currentJacobian>1e-6 && std::isfinite(c.currentJacobian),"Plane-stress thickness/volume collapsed; reduce loading or use remeshing.");
            const auto& rp=c.rockParameters;const double mu=std::max(0.,rock::CompressionMu(rp,c.rockState.strain.trace()));
            const double bulk=rp.law==3 ? (1+mu)*(rp.K1+2*rp.K2*mu+3*rp.K3*mu*mu) : rp.K();
            c.localTimeLimit*=.45/std::sqrt((bulk+4*rp.G()/3)/(c.rho/c.currentJacobian));
          }
          if(kinematics==0 && c.rockParameters.law==3){
            const auto& rp=c.rockParameters;const double mu=std::max(0.,rock::CompressionMu(rp,c.rockState.strain.trace()));
            const double bulk=(1+mu)*(rp.K1+2*rp.K2*mu+3*rp.K3*mu*mu);
            c.localTimeLimit=.45*c.altitude/std::sqrt((bulk+4*rp.G()/3)/c.rho);
          }

          c.damage=c.rockState.damage;c.stress<<c.rockState.stress(0,0),c.rockState.stress(1,1),c.rockState.stress(0,1);localForce[k]=c.area*c.currentJacobian*spatialB.transpose()*c.stress+shockForce(c,spatialB);
        }catch(const std::exception& ex){
          #pragma omp critical
          {if(rockError.empty())rockError=ex.what();}
        }
        continue;
      }
      // Linear tangent is used only as the static preload preconditioner.
      c.stress=c.D*c.strain;
      c.rockState.stress(2,2)=planeMode==1 ? c.nu*(c.stress[0]+c.stress[1]) : 0;
      localForce[k]=c.area*c.B.transpose()*c.stress;

    }
    if(!rockError.empty())throw std::runtime_error(rockError);
    Eigen::VectorXd f=Eigen::VectorXd::Zero(nd);
    #pragma omp parallel for num_threads(workers) if(workers>1)
    for(int i=0;i<static_cast<int>(nn);++i)for(const auto& source:incident[i])f.segment<2>(2*i)+=localForce[source.first].segment<2>(2*source.second);
    return f;
  };
  double preloadResidual=0;
  std::vector<int> preloadFreeIndex;
  std::unique_ptr<Eigen::SimplicialLDLT<Eigen::SparseMatrix<double>>> preloadSolver;
  if(loadMode==0 && external.squaredNorm()>0){
    // Static-only gauge constraints remove missing rigid modes. Their reactions
    // must vanish: unbalanced loads are never held by hidden physical supports.
    std::vector<bool> staticFixed=fixed;
    std::map<std::size_t,std::vector<std::size_t>> components;
    for(std::size_t i=0;i<nn;++i)components[solidGroups.Find(i)].push_back(i);
    for(const auto& component:components){
      const auto& ids=component.second;const auto& origin=model.nodes[ids.front()];double scale=1e-12;
      for(auto i:ids)scale=std::max(scale,std::hypot(model.nodes[i].x-origin.x,model.nodes[i].y-origin.y));
      std::vector<Eigen::Vector3d> basis;
      auto independent=[&](std::size_t i,int axis){
        Eigen::Vector3d row=axis==0 ? Eigen::Vector3d(1,0,-(model.nodes[i].y-origin.y)/scale) : Eigen::Vector3d(0,1,(model.nodes[i].x-origin.x)/scale);
        for(const auto& b:basis)row-=b.dot(row)*b;
        if(row.norm()<1e-9)return false;basis.push_back(row.normalized());return true;
      };
      for(auto i:ids)for(int axis=0;axis<2;++axis)if(fixed[2*i+axis])independent(i,axis);
      for(auto i:ids)for(int axis=0;axis<2 && basis.size()<3;++axis)if(!staticFixed[2*i+axis] && independent(i,axis))staticFixed[2*i+axis]=true;
    }
    std::vector<int> freeIndex(nd,-1);int nf=0;for(std::size_t i=0;i<nd;++i)if(!staticFixed[i])freeIndex[i]=nf++;
    if(nf){
      std::vector<Eigen::Triplet<double>> triplets;triplets.reserve(cells.size()*36);
      for(const auto& c:cells){const Eigen::Matrix<double,6,6> k=c.area*c.B.transpose()*c.D*c.B;
        for(int i=0;i<6;++i){const int row=freeIndex[2*c.nodes[i/2]+i%2];if(row<0)continue;
          for(int j=0;j<6;++j){const int col=freeIndex[2*c.nodes[j/2]+j%2];if(col>=0)triplets.emplace_back(row,col,k(i,j));}}
      }
      Eigen::SparseMatrix<double> K(nf,nf);K.setFromTriplets(triplets.begin(),triplets.end());triplets.clear();triplets.shrink_to_fit();
      Eigen::VectorXd rhs(nf);for(std::size_t i=0;i<nd;++i)if(freeIndex[i]>=0)rhs[freeIndex[i]]=external[i];
      preloadSolver=std::make_unique<Eigen::SimplicialLDLT<Eigen::SparseMatrix<double>>>();auto& solver=*preloadSolver;solver.compute(K);
      Require(solver.info()==Eigen::Success && solver.vectorD().minCoeff()>0,"Initial stress equilibrium stiffness is singular; check constraints and disconnected mesh.");
      const Eigen::VectorXd solution=solver.solve(rhs);Require(solver.info()==Eigen::Success && solution.allFinite(),"Initial stress equilibrium solve failed.");
      for(std::size_t i=0;i<nd;++i)if(freeIndex[i]>=0)u[i]=solution[freeIndex[i]];
      preloadFreeIndex=freeIndex;
    }
    const Eigen::VectorXd initialInternal=internal(false);
    Eigen::VectorXd residual=initialInternal-external;for(std::size_t i=0;i<nd;++i)if(fixed[i])residual[i]=0;
    preloadResidual=residual.norm()/std::max(external.norm(),1e-30);
    Require(preloadResidual<1e-7,"External loads cannot equilibrate without rigid-body reactions. Add physical supports, balance forces/moments, or select sudden loading.");

  }else internal(false);
  double preloadEnergy=0;for(auto& c:cells){c.initialStress=c.stress;c.initialZz=c.rockState.stress(2,2);preloadEnergy+=.5*c.area*c.strain.dot(c.stress);}
  for(auto& c:cells)if(c.rockParameters.law!=0 || kinematics==1){
    rock::Initialize(c.rockParameters,c.rockState,c.strain,c.stress,planeMode==1);
    c.initialZz=c.rockState.stress(2,2);
    if(kinematics==1){for(int j=0;j<3;++j){const auto n=c.nodes[j];c.previousF(0,0)+=u[2*n]*c.B(0,2*j);c.previousF(0,1)+=u[2*n]*c.B(1,2*j+1);c.previousF(1,0)+=u[2*n+1]*c.B(0,2*j);c.previousF(1,1)+=u[2*n+1]*c.B(1,2*j+1);}c.initialJacobian=c.planarJacobian=c.previousF.determinant();c.currentJacobian=c.planarJacobian*thickness(c);c.localTimeLimit=baseDt*.25;}
    if(c.rockParameters.law==3)Require(rock::Q(c.rockState.stress)<=rock::Strength(c.rockParameters,c.rockState.initialPressure,0,0)*(1+1e-7) && c.rockState.initialPressure>=-c.rockParameters.T,"Initial equilibrium exceeds JH2 strength; nonlinear static initialization is required.");

  }
  // Re-equilibrate with the SAME spatial gradients and objective constitutive
  // update used in dynamics. The reference elastic stiffness is a modified-
  // Newton preconditioner; convergence is checked on all physical free DOFs,
  // including the static gauge reactions. No fictitious balancing force is added.
  Eigen::VectorXd initialInternalForce;
  int finitePreloadIterations=0;
  if(kinematics==1){
    for(auto& c:cells){
      const double correction=.5*(std::log(c.currentJacobian)-c.rockState.strain.trace());
      c.rockState.strain(0,0)+=correction;c.rockState.strain(1,1)+=correction;
      c.rockState.initialVolumeStrain=c.rockState.strain.trace();
    }
    initializing=true;
    double forceRoundoffSquared=0;
    for(const auto& c:cells)forceRoundoffSquared+=std::pow(c.E*c.area*c.B.norm(),2);
    // Computing log(F) near I incurs O(epsilon*E) stress roundoff. A relative
    // residual alone is unattainable for a fine, stiff mesh under only 0.1 MPa
    // atmospheric preload. Scale the absolute floor by assembled force units.
    const double forceRoundoff=8*std::numeric_limits<double>::epsilon()*std::sqrt(forceRoundoffSquared);
    const int preloadIterationLimit=planeMode==0 ? 120 : 40;
    // Static displacement corrections are trial configurations, not physical
    // time steps. Re-evaluate plane-stress preload from the same reference
    // history instead of accumulating roundoff/history over Newton iterations.
    std::vector<rock::State> preloadStates;std::vector<Eigen::Matrix2d> preloadF;
    if(planeMode==0){preloadStates.reserve(cells.size());preloadF.reserve(cells.size());for(const auto& c:cells){preloadStates.push_back(c.rockState);preloadF.push_back(c.previousF);}}
    for(int iteration=0;iteration<preloadIterationLimit;++iteration){
      if(planeMode==0)for(std::size_t k=0;k<cells.size();++k){cells[k].rockState=preloadStates[k];cells[k].previousF=preloadF[k];}
      initialInternalForce=internal(true);
      if(loadMode!=0 || !preloadSolver)break;
      const Eigen::VectorXd preloadExternal=deadExternal+followerForce(u,true)-(gasMode ? (gasParameters.airPressure*pressureForce).eval() : Eigen::VectorXd::Zero(nd).eval());
      Eigen::VectorXd residual=preloadExternal-initialInternalForce;
      for(std::size_t i=0;i<nd;++i)if(fixed[i])residual[i]=0;
      preloadResidual=residual.norm()/std::max(preloadExternal.norm(),1e-30);
      // Nested plane-stress constraints and the finite-strain follower load
      // produce a small roundoff floor on heterogeneous meshes. Use an explicit
      // relative force tolerance (still below 0.2 Pa at a 20 MPa preload).
      const double preloadRelativeTolerance=planeMode==0 ? 1e-8 : 1e-9;
      if(preloadResidual<preloadRelativeTolerance || residual.norm()<forceRoundoff)break;
      if(iteration==preloadIterationLimit-1){std::ostringstream message;message<<std::setprecision(16)<<"Finite-deformation initial equilibrium did not converge: "<<preloadResidual;throw std::runtime_error(message.str());}
      Eigen::VectorXd rhs=Eigen::VectorXd::Zero(preloadSolver->vectorD().size());
      for(std::size_t i=0;i<nd;++i)if(preloadFreeIndex[i]>=0)rhs[preloadFreeIndex[i]]=residual[i];
      const Eigen::VectorXd correction=preloadSolver->solve(rhs);
      Require(correction.allFinite(),"Finite-deformation preload correction failed.");
      for(std::size_t i=0;i<nd;++i)if(preloadFreeIndex[i]>=0)u[i]+=correction[preloadFreeIndex[i]];
      ++finitePreloadIterations;
    }
    initializing=false;
    for(auto& c:cells){
      Require(c.rockState.plasticStrain<1e-14 && c.damage==0,"Finite-deformation preload exceeds elastic strength; nonlinear inelastic initialization is required.");
      c.initialStress=c.stress;c.initialZz=c.rockState.stress(2,2);c.initialJacobian=c.planarJacobian;
      c.rockState.initialPressure=-c.rockState.stress.trace()/3;c.rockState.initialVolumeStrain=c.rockState.strain.trace();
      if(c.rockParameters.law==3)Require(rock::Q(c.rockState.stress)<=rock::Intact(c.rockParameters,c.rockState.initialPressure,0)*(1+1e-7) && c.rockState.initialPressure>=-c.rockParameters.T,"Finite-deformation preload exceeds static JH2 strength.");
    }
    preloadEnergy=0;for(const auto& c:cells)preloadEnergy+=c.area*rock::StoredEnergy(c.rockParameters,c.rockState);
  }else initialInternalForce=internal(false);
  preloadSolver.reset();
  std::vector<Eigen::Matrix2d> inverseMass(nn);
  for(std::size_t i=0;i<nn;++i){
    dashpot[i]+=damping*mass[2*i]*Eigen::Matrix2d::Identity();
    Eigen::Matrix2d lhs=mass[2*i]*Eigen::Matrix2d::Identity()+.5*dt*dashpot[i];
    for(int axis=0;axis<2;++axis)if(fixed[2*i+axis]){lhs.row(axis).setZero();lhs.col(axis).setZero();lhs(axis,axis)=1;}
    inverseMass[i]=lhs.inverse();
  }
  if(loadMode==1)for(std::size_t i=0;i<nd;++i)if(!fixed[i])a[i]=external[i]/mass[i];
  double currentGasPressure=gasMode ? gas->Snapshot().wallPressure : 0.;
  const Eigen::VectorXd referenceU=u;
  auto cavityGeometry=[&](const Eigen::VectorXd& displacement){
    Eigen::VectorXd gradient=Eigen::VectorXd::Zero(nd);
    for(const auto& edge:cavitySegments){const auto aa=std::get<0>(edge),bb=std::get<1>(edge);const double sign=std::get<2>(edge);
      const double dx=model.nodes[bb].x+displacement[2*bb]-model.nodes[aa].x-displacement[2*aa],dy=model.nodes[bb].y+displacement[2*bb+1]-model.nodes[aa].y-displacement[2*aa+1];
      const Eigen::Vector2d force=.5*sign*thickness(cells[std::get<3>(edge)])*Eigen::Vector2d(-dy,dx);gradient.segment<2>(2*aa)+=force;gradient.segment<2>(2*bb)+=force;
    }
    double area=0;for(std::size_t i=0;i<nn;++i)area+=.5*gradient.segment<2>(2*i).dot(Eigen::Vector2d(model.nodes[i].x+displacement[2*i],model.nodes[i].y+displacement[2*i+1]));
    return std::make_pair(gradient,area);
  };
  const double initialCavityArea=kinematics==1 ? cavityGeometry(referenceU).second : 0;
  double sweptCavityVolume=0;
  if(gasMode){
    const Eigen::VectorXd initialPressureForce=kinematics==1 ? cavityGeometry(u).first : pressureForce;
    const Eigen::VectorXd initialForce=externalAt(u)+currentGasPressure*initialPressureForce-gasParameters.airPressure*pressureForce-initialInternalForce;
    for(std::size_t i=0;i<nd;++i)if(!fixed[i])a[i]=initialForce[i]/mass[i];
  }
  auto pressure=[&](double t){return gasMode ? currentGasPressure : t>=0 && t<pulse ? peak*std::sin(3.14159265358979323846*t/pulse) : 0.;};
  if(!jh2ElasticResponse.empty())openradioss::Runtime();
  std::ostringstream metadata;metadata<<std::setprecision(16)<<"{\"jh2IntegrationVersion\":4,\"jh2ParameterVersion\":2,\"jh2Backend\":\"OpenRadioss SIGEPS79\",\"jh2BackendCommit\":\""<<openradioss::Commit<<"\",\"jh2BackendABI\":1,\"gasIntegrationVersion\":2,\"materialFractureVersion\":1,\"shockViscosityVersion\":1,\"shockViscosity\":"<<(shock?1:0)<<",\"nodeCount\":"<<nn<<",\"elementCount\":"<<cells.size()<<",\"frameCount\":"<<frames
    <<",\"dt\":"<<dt<<",\"stableDt\":"<<stableDt<<",\"steps\":"<<steps<<",\"loadedEdges\":"<<loadedEdges<<",\"absorbingEdges\":"<<absorbingEdges
    <<",\"fixedBoundaryEdges\":"<<fixedBoundaryEdges<<",\"preloadResidual\":"<<preloadResidual<<",\"preloadEnergy\":"<<preloadEnergy<<",\"workers\":"<<workers
    <<",\"dynamicsIntegrationVersion\":2,\"jh2BulkingVersion\":1,\"finitePreloadIterations\":"<<finitePreloadIterations
    <<",\"planeMode\":"<<planeMode<<",\"jh2PlaneStressVersion\":1,\"constitutiveVersion\":2,\"solidConstitutiveVersion\":2,\"supportedSolidLaws\":[1,3,6],\"rockModel\":"<<rockModel<<",\"gasFracture\":"<<gasFracture<<",\"kinematics\":"<<kinematics<<",\"gasVentEnds\":"<<ventEnds<<",\"stepCountIsEstimate\":"<<(adaptiveTime?"true":"false")<<",\"cellScalarCount\":"<<cellScalars
    <<",\"gasConstitutiveVersion\":2,\"gasBackend\":\"LANL Singularity-EOS\",\"gasBackendCommit\":\"b4f71a7748770dfa6ce4d678754c463c09262fb7\",\"gasBackendABI\":1,\"airEOS\":"<<airEOS<<",\"effectiveProductGamma\":"<<(gasParameters.omega+1)<<",\"productEOS\":"<<productEOS<<",\"sourceMode\":"<<sourceMode<<",\"geometryDiagnosticsVersion\":1,\"frameScalarCount\":"<<(ventEnds>0 ? 28 : advanced ? 24 : gasMode ? 12 : 8)<<",\"initialGasEnergy\":"<<(gasMode ? gas->InitialEnergy() : 0)<<"}";
  std::string json=metadata.str();json.pop_back();std::ostringstream response;response<<std::setprecision(16)<<",\"jh2ElasticResponse\":[";bool firstMaterial=true;
  for(const auto& entry:jh2ElasticResponse){if(!firstMaterial)response<<",";firstMaterial=false;const auto& x=entry.second;
    response<<"{\"materialNo\":"<<entry.first<<",\"inputBulkModulus\":"<<x[0]<<",\"eosBulkModulus\":"<<x[1]<<",\"shearModulus\":"<<x[2]<<",\"initialPWaveSpeed\":"<<x[3]<<"}";
  }response<<"],\"solverInputUnits\":\"m-kg-s-Pa-J/kg\",\"jh2KernelInputs\":[";
  firstMaterial=true;std::map<int,bool> recordedMaterials;
  for(std::size_t k=0;k<cells.size();++k){const auto& c=cells[k];const int id=model.elements[k].materialNo;
    if(c.rockParameters.law!=3 || recordedMaterials[id])continue;recordedMaterials[id]=true;
    if(!firstMaterial)response<<",";firstMaterial=false;
    response<<"{\"materialNo\":"<<id<<",\"density\":"<<c.rho<<",\"parameters\":[";
    const auto values=rock::JH2KernelParameters(c.rockParameters,fracture!=0);
    for(std::size_t i=0;i<values.size();++i){if(i)response<<",";response<<values[i];}response<<"]}";
  }
  response<<"],\"gasKernelInputs\":{\"productEOS\":"<<productEOS<<",\"airEOS\":"<<airEOS
    <<",\"referenceDensity\":"<<gasParameters.productDensity<<",\"specificEnergy\":"<<gasParameters.productEnergy
    <<",\"A\":"<<gasParameters.A<<",\"B\":"<<gasParameters.B<<",\"R1\":"<<gasParameters.R1<<",\"R2\":"<<gasParameters.R2
    <<",\"omega\":"<<gasParameters.omega<<",\"airDensity\":"<<gasParameters.airDensity<<",\"airPressure\":"<<gasParameters.airPressure<<",\"airGamma\":"<<gasParameters.airGamma<<"}}";
  json+=response.str();out.write("FEMBLT02",8);Raw(out,static_cast<std::uint32_t>(json.size()));out.write(json.data(),json.size());
  int saved=0;double externalWork=0,dissipated=0;
  std::vector<double> cellOutput(cells.size()*cellScalars);
  double crackVolume=0,gasStorageWork=0;
  std::vector<double> crackWeights(cells.size(),0);
  Eigen::VectorXd gasForce=kinematics==1 ? cavityGeometry(u).first : pressureForce;
  auto progressAt=std::chrono::steady_clock::now();
  double simulationTime=0;
  for(int step=0;adaptiveTime ? simulationTime<=duration : step<=steps;++step){
    Require(step<20000000,"Finite-deformation step limit reached; severely distorted mesh requires remeshing.");
    const auto now=std::chrono::steady_clock::now();
    if(step==0 || step==steps || now-progressAt>=std::chrono::milliseconds(250)){
      std::cerr<<"BLAST_PROGRESS "<<(adaptiveTime ? std::min(steps,static_cast<int>(simulationTime/duration*steps)) : step)<<" "<<steps<<"\n";progressAt=now;
    }
    const double time=adaptiveTime ? simulationTime : step*dt;
    if(adaptiveTime ? (step==0 || time>=duration*saved/(frames-1)-1e-14) : (step==0 || step==static_cast<int>(std::llround(static_cast<double>(saved)*steps/(frames-1))) || step==steps)){
      double elastic=0,maxStress=0,maxDynamic=0,plasticWork=0,maxStrain=0;
      for(std::size_t i=0;i<cells.size();++i){const auto& c=cells[i];elastic+=c.rockParameters.law!=0 || kinematics==1 ? c.area*rock::StoredEnergy(c.rockParameters,c.rockState) : .5*c.area*c.strain.dot(c.stress);
        if(c.rockParameters.law!=0 || kinematics==1){auto delta=c.rockState.stress;delta(0,0)-=c.initialStress[0];delta(1,1)-=c.initialStress[1];delta(0,1)-=c.initialStress[2];delta(1,0)-=c.initialStress[2];delta(2,2)-=c.initialZz;
          maxStress=std::max(maxStress,rock::Q(c.rockState.stress));maxDynamic=std::max(maxDynamic,rock::Q(delta));
        }else {maxStress=std::max(maxStress,Equivalent(c.stress,c.rockState.stress(2,2)));maxDynamic=std::max(maxDynamic,Equivalent(c.stress-c.initialStress,c.rockState.stress(2,2)-c.initialZz));}
        plasticWork+=c.area*c.rockState.plasticWork;maxStrain=std::max(maxStrain,std::sqrt(std::max(0.,c.strain[0]*c.strain[0]-c.strain[0]*c.strain[1]+c.strain[1]*c.strain[1]+.75*c.strain[2]*c.strain[2])));
        const double values[14]={c.strain[0],c.strain[1],c.strain[2],c.stress[0],c.stress[1],c.stress[2],c.damage,c.rockState.stress(2,2),c.rockState.plasticStrain,c.rockState.plasticWork,0,0,0,0};
        std::copy(values,values+cellScalars,cellOutput.begin()+i*cellScalars);}
      const double frameTime=adaptiveTime ? duration*saved/(frames-1) : time;
      const std::array<double,8> info={frameTime,pressure(time),.5*(mass.array()*v.array().square()).sum(),elastic,externalWork,dissipated,maxStress,maxDynamic};
      out.write(reinterpret_cast<const char*>(info.data()),sizeof(info));
      if(gasMode || advanced){const auto state=gasMode ? gas->Snapshot() : GasSnapshot{};const std::array<double,4> extra={state.internalEnergy,state.kineticEnergy,state.wallWork,state.radius};out.write(reinterpret_cast<const char*>(extra.data()),sizeof(extra));}
      if(advanced){const std::array<double,4> extra={plasticWork,crackVolume,gasStorageWork,maxStrain};out.write(reinterpret_cast<const char*>(extra.data()),sizeof(extra));
        double minJ=1,maxCfl=0;for(const auto& c:cells){minJ=std::min(minJ,c.currentJacobian);if(adaptiveTime)maxCfl=std::max(maxCfl,dt/c.localTimeLimit);}
        const std::array<double,4> diagnostics={static_cast<double>(step),minJ,gasMode ? static_cast<double>(gas->Snapshot().rarefactionFallbacks) : 0,maxCfl};out.write(reinterpret_cast<const char*>(diagnostics.data()),sizeof(diagnostics));
        double minPlanar=std::numeric_limits<double>::infinity(),minThickness=minPlanar,maxThickness=0,maxResidual=0;
        for(const auto& c:cells){minPlanar=std::min(minPlanar,c.planarJacobian);minThickness=std::min(minThickness,thickness(c));maxThickness=std::max(maxThickness,thickness(c));if(planeMode==0)maxResidual=std::max(maxResidual,std::abs(c.rockState.stress(2,2))/std::max(1e6,c.rockState.stress.norm()));}
        const std::array<double,4> geometry={minPlanar,minThickness,maxThickness,maxResidual};out.write(reinterpret_cast<const char*>(geometry.data()),sizeof(geometry));
      }
      if(ventEnds>0){const auto state=gasMode?gas->Snapshot():GasSnapshot{};const std::array<double,4> extra={state.ventedMass,state.ventedEnergy,state.productMass,state.airMass};out.write(reinterpret_cast<const char*>(extra.data()),sizeof(extra));}
      out.write(reinterpret_cast<const char*>(u.data()),nd*sizeof(double));out.write(reinterpret_cast<const char*>(v.data()),nd*sizeof(double));
      out.write(reinterpret_cast<const char*>(cellOutput.data()),cellOutput.size()*sizeof(double));
      out.flush();Require(out.good(),"Failed writing streamed blast frame.");++saved;
    }
    if(adaptiveTime ? time>=duration-1e-15 : step==steps)break;
    if(adaptiveTime){dt=baseDt;for(const auto& c:cells)dt=std::min(dt,c.localTimeLimit);dt=std::min(dt,duration*saved/(frames-1)-time);Require(dt>1e-14,"Finite-deformation CFL step collapsed; use remeshing or a particle solver.");}
    const Eigen::VectorXd oldU=u,oldV=v;
    const Eigen::VectorXd previousExternal=externalAt(oldU);
    const Eigen::VectorXd previousPressureForce=kinematics==1 && planeMode==0 ? cavityGeometry(oldU).first : pressureForce;
    // a stores the instantaneous endpoint acceleration. The gas solver returns
    // an interval mean pressure, whose impulse must not be averaged again
    // with the previous interval's pressure by the two Verlet half kicks.
    Eigen::VectorXd oldGasApplied;
    if(gasMode)oldGasApplied=currentGasPressure*gasForce-gasParameters.airPressure*pressureForce;
    u+=dt*v+(.5*dt*dt)*a;v+=(.5*dt)*a;
    double gasAverage=0;
    Eigen::VectorXd intervalCavityForce;
    if(gasMode){
      // Small-strain area change is integral(u.n ds). Mapping it to pi R^2
      // makes the radial fluid's wall-volume work match the solid interface work.
      gasForce=pressureForce;double topologyVolume=0;const double previousCrackVolume=crackVolume;crackVolume=0;
      if(kinematics==1)gasForce=cavityGeometry((.5*(u+oldU)).eval()).first;
      intervalCavityForce=gasForce;
      if(kinematics==1 && planeMode==0)sweptCavityVolume+=gasForce.dot(u-oldU);
      if(gasFracture==1){
        std::vector<bool> connected(cells.size(),false);std::vector<std::size_t> queue;
        for(std::size_t k=0;k<cells.size();++k)if(cells[k].cavityCell && cells[k].damage>=crackDamage){connected[k]=true;queue.push_back(k);}
        for(std::size_t j=0;j<queue.size();++j)for(auto k:cells[queue[j]].neighbours)if(!connected[k] && cells[k].damage>=crackDamage){connected[k]=true;queue.push_back(k);}
        for(std::size_t k=0;k<cells.size();++k){const auto& c=cells[k];if(!connected[k])continue;
          V6 next,previous;for(int j=0;j<6;++j){const auto d=2*c.nodes[j/2]+j%2;next[j]=u[d]-referenceU[d];previous[j]=oldU[d]-referenceU[d];}
          Eigen::Matrix<double,1,6> gradient=c.B.row(0)+c.B.row(1);double opening=gradient.dot(next),oldOpening=gradient.dot(previous);const double weight=c.damage;
          if(kinematics==1){
            Eigen::Matrix2d Fn=Eigen::Matrix2d::Identity(),Fo=Fn;
            for(int j=0;j<3;++j){const auto n=c.nodes[j];const Eigen::RowVector2d g(c.B(0,2*j),c.B(1,2*j+1));Fn+=u.segment<2>(2*n)*g;Fo+=oldU.segment<2>(2*n)*g;}
            opening=Fn.determinant()-c.initialJacobian;oldOpening=Fo.determinant()-c.initialJacobian;
            const Eigen::Matrix2d Fmid=.5*(Fn+Fo),cofactor=Fmid.determinant()*Fmid.inverse().transpose();
            for(int j=0;j<3;++j){const Eigen::Vector2d g=cofactor*Eigen::Vector2d(c.B(0,2*j),c.B(1,2*j+1));gradient[2*j]=g[0];gradient[2*j+1]=g[1];}
          }
          if(kinematics==1 && planeMode==0){const double t=thickness(c);opening*=t;oldOpening*=t;gradient*=t;}
          crackVolume+=c.area*weight*std::max(0.,opening);
          topologyVolume+=c.area*(weight-crackWeights[k])*std::max(0.,oldOpening);
          // Secant derivative makes force work equal the change in unilateral
          // storage volume for fixed damage, even when a crack closes.
          const double ratio=std::abs(opening-oldOpening)>1e-16 ? (std::max(0.,opening)-std::max(0.,oldOpening))/(opening-oldOpening) : opening>0 ? 1 : 0;
          for(int j=0;j<6;++j)gasForce[2*c.nodes[j/2]+j%2]+=c.area*weight*ratio*gradient[j];
          crackWeights[k]=weight;
        }
      }
      if(kinematics==1 && planeMode==0)topologyVolume=crackVolume-previousCrackVolume-(gasForce-intervalCavityForce).dot(u-oldU);
      const double wallArea=3.14159265358979323846*radius*radius+(kinematics==1 ? (planeMode==0 ? sweptCavityVolume : cavityGeometry(u).second-initialCavityArea) : pressureForce.dot(u-referenceU))+crackVolume;
      Require(wallArea>0,"Mean cavity area collapsed in gas coupling.");
      gasAverage=gas->Advance(time+dt,std::sqrt(wallArea/3.14159265358979323846));
      gasStorageWork+=gasAverage*topologyVolume;
      currentGasPressure=gas->WallPressure();
    }
    const double forcingPressure=gasMode ? gasAverage-gasParameters.airPressure : pressure(time+dt);
    materialEvaluationTime=time+dt;
    const Eigen::VectorXd internalForce=internal(true);
    Eigen::VectorXd applied=forcingPressure*(kinematics==1 && planeMode==0 ? cavityGeometry(u).first : pressureForce);
    if(gasMode)applied=gasAverage*gasForce-gasParameters.airPressure*pressureForce;
    const Eigen::VectorXd currentExternal=externalAt(u);
    Eigen::VectorXd force=currentExternal+applied-internalForce;
    if(gasMode)force+=applied-oldGasApplied;
    if(shock)for(const auto& c:cells)dissipated+=dt*c.viscousPower;
    #pragma omp parallel for num_threads(workers) if(workers>1)
    for(int i=0;i<static_cast<int>(nn);++i){
      if(adaptiveTime){Eigen::Matrix2d lhs=mass[2*i]*Eigen::Matrix2d::Identity()+.5*dt*dashpot[i];for(int axis=0;axis<2;++axis)if(fixed[2*i+axis]){lhs.row(axis).setZero();lhs.col(axis).setZero();lhs(axis,axis)=1;}inverseMass[i]=lhs.inverse();}
      Eigen::Vector2d rhs=force.segment<2>(2*i)-dashpot[i]*v.segment<2>(2*i);
      for(int axis=0;axis<2;++axis)if(fixed[2*i+axis])rhs[axis]=0;
      a.segment<2>(2*i)=inverseMass[i]*rhs;v.segment<2>(2*i)+=.5*dt*a.segment<2>(2*i);
    }
    if(gasMode){
      // Restore endpoint force for the next displacement predictor. Crack
      // storage uses the same secant volume gradient as the interval work.
      Eigen::VectorXd endpointGasForce=gasForce;
      if(kinematics==1)endpointGasForce+=cavityGeometry(u).first-(planeMode==0 ? intervalCavityForce : cavityGeometry((.5*(u+oldU)).eval()).first);
      const Eigen::VectorXd endpoint=currentExternal+currentGasPressure*endpointGasForce-gasParameters.airPressure*pressureForce-internalForce;
      for(std::size_t i=0;i<nn;++i){
        a.segment<2>(2*i)=(endpoint.segment<2>(2*i)-dashpot[i]*v.segment<2>(2*i))/mass[2*i];
        for(int axis=0;axis<2;++axis)if(fixed[2*i+axis])a[2*i+axis]=0;
      }
      gasForce=endpointGasForce;
    }
    Require(u.allFinite() && v.allFinite() && a.allFinite(),"Blast solution diverged; check mesh/material/time step.");
    const double workPressure=gasMode ? gasAverage-gasParameters.airPressure : .5*(pressure(time)+pressure(time+dt));
    Eigen::VectorXd workForce=workPressure*(kinematics==1 && planeMode==0 ? (.5*(previousPressureForce+cavityGeometry(u).first)).eval() : pressureForce);if(gasMode)workForce=applied;
    externalWork+=(.5*(previousExternal+currentExternal)+workForce).dot(u-oldU);
    for(std::size_t i=0;i<nn;++i)dissipated+=.5*dt*(oldV.segment<2>(2*i).dot(dashpot[i]*oldV.segment<2>(2*i))+v.segment<2>(2*i).dot(dashpot[i]*v.segment<2>(2*i)));
    simulationTime=time+dt;
  }
  if(gasMode){const auto state=gas->Snapshot();std::cerr<<"BLAST_GAS_STATS "<<state.substeps<<" "<<state.rezones<<" "<<state.airFilmTransitions<<"\n";}
  out.flush();return 0;
}
}
