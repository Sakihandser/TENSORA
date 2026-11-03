#include "../../TensoraCore/RockConstitutive.h"
#include "../../TensoraCore/ShockViscosity.h"
#include <iostream>
#include <iomanip>
using namespace fem::rock;
Parameters Card(){Parameters p;p.law=3;p.E=51.166364e9;p.nu=.168181818;p.ft=8e6;p.fc=150e6;p.h=.0015;p.gf=100;p.A=.76;p.N=.62;p.B=.25;p.M=.62;p.C=.005;p.rate0=1;p.HEL=4.5e9;p.pHEL=3.7e9;p.T=54e6;p.D1=.005;p.D2=.7;p.maxStrength=.25;p.K1=25.7e9;p.K2=-4500e9;p.K3=300000e9;return p;}
void Print(const State& s){std::cout<<"{\"q\":"<<Q(s.stress)<<",\"pressure\":"<<-s.stress.trace()/3<<",\"damage\":"<<s.damage<<",\"plasticStrain\":"<<s.plasticStrain<<",\"plasticWork\":"<<s.plasticWork<<",\"szz\":"<<s.stress(2,2)<<"}";}
int main(int argc,char** argv){try{const std::string mode=argc>1?argv[1]:"strength";auto p=Card();std::cout<<std::setprecision(16);
  if(mode=="new-materials"){
    int samples=0;double plastic=0;
    for(int law:{1,6}){
      p.law=law;p.E=20e9;p.nu=.25;p.density=2500;p.friction=30;p.dilation=5;p.cohesion=5e6;p.tension=1e6;
      p.softening=1;p.residualFriction=25;p.residualDilation=2;p.residualCohesion=2e6;p.peakStrain=.001;p.residualStrain=.02;
      InitializeMaterial(p);State s;auto history=p.material->initialise_state_variables();Eigen::Matrix<double,6,1> stress=Eigen::Matrix<double,6,1>::Zero();
      for(int k=0;k<200;++k){
        Tensor de=Tensor::Zero();de(0,0)=-2e-5;de(1,1)=-1e-5;de(0,1)=de(1,0)=1e-4;de(0,2)=de(2,0)=3e-5;de(1,2)=de(2,1)=-2e-5;
        Eigen::Matrix<double,6,1> delta;delta<<de(0,0),de(1,1),de(2,2),2*de(0,1),2*de(1,2),2*de(0,2);
        stress=p.material->compute_stress(stress,delta,nullptr,&history);Step(p,s,de,1e-6,true);
        Eigen::Matrix<double,6,1> actual;actual<<s.stress(0,0),s.stress(1,1),s.stress(2,2),s.stress(0,1),s.stress(1,2),s.stress(0,2);
        if(!actual.allFinite()||(actual-stress).norm()>1e-10*std::max(1.,stress.norm()))throw std::runtime_error("Solid stress mapping mismatch");
        if(law==6&&std::abs(s.plasticStrain-history.at("pdstrain"))>1e-12)throw std::runtime_error("Plastic history mismatch");
        ++samples;
      }
      if(law==1&&std::abs(stress[3]-200*p.G()*2e-4)>1e-5)throw std::runtime_error("Engineering shear mapping mismatch");
      if(law==6)plastic=s.plasticStrain;
    }
    if(!(plastic>0))throw std::runtime_error("No plastic steps exercised");
    std::cout<<"{\"samples\":"<<samples<<",\"plastic\":"<<plastic<<"}";return 0;
  }
  if(mode=="failed-plane-flow"){
    // Isolate the material-point response from gas coupling and FE integration.
    // An already failed JH2 point can accommodate in-plane compression by
    // transverse plastic flow while sigma_zz remains zero.
    p.logarithmicVolume=true;p.normalizationStress=4.5e9;p.inputShearModulus=21.9e9;p.density=2660;p.beta=1;
    State x;x.damage=1;double input[40]={};
    for(int k=0;k<45000;++k){
      const State previous=x;Tensor de=Tensor::Zero();de(0,0)=-2e-4;
      x=PlaneStressIncrement(p,x,de,1e-9,true);
      if(k==44999){
        const auto parameters=JH2KernelParameters(p,true);std::copy(parameters.begin(),parameters.end(),input);
        const Tensor old=JH2PreviousDeviator(previous.effective),increment=x.strain-previous.strain;
        const double tail[20]={old(0,0),old(1,1),old(2,2),old(0,1),old(1,2),old(2,0),increment(0,0),increment(1,1),increment(2,2),2*increment(0,1),2*increment(1,2),2*increment(2,0),std::expm1(-x.strain.trace()),std::sqrt(2./3*Dev(increment).squaredNorm())/1e-9,p.density,previous.damage,previous.plasticStrain,previous.bulking,previous.jh2PreviousYield,previous.jh2Et};
        std::copy(tail,tail+20,input+20);
      }
    }
    std::cout<<"{\"planarJacobian\":"<<std::exp(x.strain(0,0)+x.strain(1,1))<<",\"thicknessStretch\":"<<std::exp(x.strain(2,2))<<",\"volumeJacobian\":"<<std::exp(x.strain.trace())<<",\"stress\":["<<x.stress(0,0)<<","<<x.stress(1,1)<<","<<x.stress(2,2)<<","<<x.stress(0,1)<<","<<x.stress(1,2)<<","<<x.stress(2,0)<<"],\"input\":[";
    for(int i=0;i<40;++i){if(i)std::cout<<",";std::cout<<input[i];}std::cout<<"]}";return 0;
  }
  if(mode=="plane-upstream-path"){
    p.normalizationStress=4.5e9;p.density=2660;
    std::cout<<"[";bool first=true;
    for(int logarithmic=0;logarithmic<2;++logarithmic)for(int scenario=0;scenario<3;++scenario){
      p.logarithmicVolume=logarithmic==1;p.beta=scenario==1?.7:0;State x;
      for(int k=0;k<160;++k){
        const double dt=1e-8;const State oldState=x;
        const Eigen::Vector3d inplane(x.strain(0,0)+(k<100 ? (scenario==0?4e-5:-4e-5) : 2e-5),x.strain(1,1)+(k<100?-1e-5:1e-5),2*x.strain(0,1)+(scenario==0?0:6e-5*std::cos(.07*k)));
        x=Advance(p,x,inplane,dt,false,true);
        const Tensor de=x.strain-oldState.strain,old=JH2PreviousDeviator(oldState.effective);
        const double mu=p.logarithmicVolume ? std::expm1(-x.strain.trace()) : std::expm1(-std::log1p(x.strain.trace()));
        const double input[40]={p.G(),2*p.G(),p.A,p.B,p.M,p.N,p.C,p.rate0,p.maxStrength,p.T/p.pHEL,
          p.pHEL,p.SigmaHEL(),p.D1,p.D2,p.K1,p.K2,p.K3,p.beta,0,1e30,
          old(0,0),old(1,1),old(2,2),old(0,1),old(1,2),old(2,0),de(0,0),de(1,1),de(2,2),2*de(0,1),2*de(1,2),2*de(2,0),
          mu,std::sqrt(2./3*Dev(de).squaredNorm())/dt,p.density,oldState.damage,oldState.plasticStrain,oldState.bulking,oldState.jh2PreviousYield,oldState.jh2Et};
        if(!first)std::cout<<",";first=false;
        std::cout<<"{\"logarithmic\":"<<logarithmic<<",\"scenario\":"<<scenario<<",\"ezz\":"<<x.strain(2,2)<<",\"input\":[";
        for(int i=0;i<40;++i){if(i)std::cout<<",";std::cout<<input[i];}
        std::cout<<"],\"output\":["<<x.stress(0,0)<<","<<x.stress(1,1)<<","<<x.stress(2,2)<<","<<x.stress(0,1)<<","<<x.stress(1,2)<<","<<x.stress(2,0)
          <<","<<x.damage<<","<<x.plasticStrain<<","<<x.bulking<<","<<x.jh2PreviousYield<<","<<x.jh2Et<<","<<x.jh2PreviousYield/p.SigmaHEL()<<","<<x.plasticStrain-oldState.plasticStrain<<","<<x.jh2SoundSpeed<<"]}";
      }
    }std::cout<<"]";return 0;
  }
  if(mode=="upstream-path"){
    p.logarithmicVolume=true;p.normalizationStress=4.5e9;
    std::cout<<"[";bool first=true;
    for(int scenario=0;scenario<3;++scenario){
      p.beta=scenario==1?.7:0;State x;
      for(int k=0;k<120;++k){
        const double dt=1e-8;Tensor de=Tensor::Zero();
        de(0,0)=k<50 ? -1.5e-4 : scenario==2 ? 2.0e-4 : 1.0e-4;de(1,1)=.2*de(0,0);de(2,2)=.1*de(0,0);
        de(0,1)=de(1,0)=scenario==2 ? 1e-9 : 1.3e-4*std::cos(.13*k);
        de(1,2)=de(2,1)=scenario==2 ? 0 : 8e-5*std::sin(.17*k);
        de(2,0)=de(0,2)=scenario==2 ? 0 : -5e-5;
        const Tensor old=JH2PreviousDeviator(x.effective);
        const double input[40]={p.G(),2*p.G(),p.A,p.B,p.M,p.N,p.C,p.rate0,p.maxStrength,p.T/p.pHEL,
          p.pHEL,p.SigmaHEL(),p.D1,p.D2,p.K1,p.K2,p.K3,p.beta,0,1e30,
          old(0,0),old(1,1),old(2,2),old(0,1),old(1,2),old(2,0),
          de(0,0),de(1,1),de(2,2),2*de(0,1),2*de(1,2),2*de(2,0),
          std::expm1(-(x.strain+de).trace()),std::sqrt(2./3*Dev(de).squaredNorm())/dt,2660,
          x.damage,x.plasticStrain,x.bulking,x.jh2PreviousYield,x.jh2Et};
        p.density=2660;Step(p,x,de,dt,true);
        if(!first)std::cout<<",";first=false;
        std::cout<<"{\"input\":[";for(int i=0;i<40;++i){if(i)std::cout<<",";std::cout<<input[i];}
        std::cout<<"],\"output\":["<<x.stress(0,0)<<","<<x.stress(1,1)<<","<<x.stress(2,2)<<","<<x.stress(0,1)<<","<<x.stress(1,2)<<","<<x.stress(2,0)
          <<","<<x.damage<<","<<x.plasticStrain<<","<<x.bulking<<","<<x.jh2PreviousYield<<","<<x.jh2Et
          <<","<<x.jh2PreviousYield/p.SigmaHEL()<<","<<x.plasticStrain-input[36]<<","<<x.jh2SoundSpeed<<"]}";
      }
    }std::cout<<"]";return 0;
  }
  if(mode=="shock-viscosity"){
    const auto compression=fem::CompressionViscosity(Eigen::Vector3d(-100,20,40),2600,.002,5000);
    const auto expansion=fem::CompressionViscosity(Eigen::Vector3d(100,200,0),2600,.002,5000);
    std::cout<<"{\"power\":"<<compression.power<<",\"trace\":"<<(compression.stress[0]+compression.stress[1])<<",\"expansion\":"<<expansion.stress.norm()<<"}";return 0;
  }
  if(mode=="strength"){std::cout<<"{\"sigmaHEL\":"<<p.SigmaHEL()<<",\"intact0\":"<<Intact(p,0,1)<<",\"intactConfined\":"<<Intact(p,100e6,1)<<",\"fast\":"<<Intact(p,100e6,1e5)<<",\"failed\":"<<Failed(p,100e6,1)<<",\"failureStrain\":"<<FailureStrain(p,100e6)<<"}";return 0;}
  if(mode=="shear-reference"){
    p.normalizationStress=4.5e9;State s;s.initialPressure=20e6;s.stress=s.effective=-20e6*Tensor::Identity();
    std::cout<<"{\"samples\":[";bool first=true;
    for(int i=0;i<600;++i){Tensor d=Tensor::Zero();if(i<400)d(0,1)=d(1,0)=.02/400/2;Step(p,s,d,1e-8,true);
      if(i==159 || i==160 || i==161 || i==180 || i==399 || i==599){if(!first)std::cout<<",";first=false;Print(s);}}
    std::cout<<"]}";return 0;
  }
  State s;int n=argc>2?std::stoi(argv[2]):400;const double dt=1e-5/n;
  if(mode=="bulking"){
    p.beta=.7;p.C=0;p.normalizationStress=4.5e9;p.logarithmicVolume=true;
    s.strain=-std::log1p(.01)/3*Tensor::Identity();
    const double pressure=EOS(p,s.strain.trace());s.stress=s.effective=-pressure*Tensor::Identity();
    Tensor de=Tensor::Zero();de(0,1)=de(1,0)=.01;
    Step(p,s,de,1e-7,true);
    const double before=-s.stress.trace()/3,bulking=s.bulking,energy=s.bulkingEnergy,damage=s.damage;
    Step(p,s,Tensor::Zero(),1e-7,false);
    std::cout<<"{\"pressureBefore\":"<<before<<",\"pressureAfter\":"<<-s.stress.trace()/3<<",\"bulking\":"<<bulking<<",\"energy\":"<<energy<<",\"damage\":"<<damage<<"}";return 0;
  }
  if(mode=="elastic"){p.law=1;Eigen::Vector3d e(.001,0,0);s=Advance(p,s,e,1e-5,false,false);std::cout<<"{\"sx\":"<<s.stress(0,0)<<",\"sy\":"<<s.stress(1,1)<<",\"szz\":"<<s.stress(2,2)<<"}";return 0;}
  if(mode=="yield-onset"){
    p.C=0;p.normalizationStress=4.5e9;const double pressure=20e6,threshold=Intact(p,pressure,0);
    s.initialPressure=pressure;s.stress=s.effective=-pressure*Tensor::Identity();
    Tensor delta=Tensor::Zero();delta(0,1)=delta(1,0)=threshold*(1+1e-8)/(std::sqrt(3.)*2*p.G());
    Step(p,s,delta,1e-7,true);const double firstDamage=s.damage,firstPlastic=s.plasticStrain;
    for(int i=0;i<100;i++)Step(p,s,Tensor::Zero(),1e-7,true);
    std::cout<<"{\"firstDamage\":"<<firstDamage<<",\"firstPlastic\":"<<firstPlastic<<",\"state\":";Print(s);std::cout<<"}";return 0;
  }
  if(mode=="plane-stress"){for(int i=1;i<=n;++i)s=Advance(p,s,Eigen::Vector3d(.003*i/n,0,0),dt,false,true);Print(s);return 0;}
  if(mode=="dp"){p.law=2;p.friction=35;p.dilation=0;}
  if(mode=="tension"){for(int i=0;i<n;++i)Step(p,s,Tensor::Identity()*(.01/n),dt,true);Print(s);return 0;}
  Tensor increment=Tensor::Zero();increment(0,0)=-.015/n;increment(1,1)=increment(2,2)=-.002/n;increment(0,1)=increment(1,0)=.01/n;
  for(int i=0;i<n;++i)Step(p,s,increment,dt,true);
  if(mode=="unload"){const double damage=s.damage,plastic=s.plasticStrain;for(int i=0;i<n;++i)Step(p,s,-increment*.1,dt,true);std::cout<<"{\"oldDamage\":"<<damage<<",\"oldPlastic\":"<<plastic<<",\"state\":";Print(s);std::cout<<"}";return 0;}
  Print(s);return 0;
}catch(const std::exception& ex){std::cerr<<ex.what();return 1;}}
