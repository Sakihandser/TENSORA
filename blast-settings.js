// Shared browser/server settings for the 2D OpenCourant blast chain; all solver inputs use SI units.
// Only quantities that the OpenCourant/MFEM decks consume are kept. Keys stored by
// older models (time step, gas cells, vents, plane stress, ...) are dropped here.
(function(root) {
  const Gas=typeof module!=='undefined'&&module.exports?require('./gas-eos'):root.GasEOS;
  const defaults = Object.freeze({x:0,y:0,radius:.1,chargeRadius:.1,pressure:10e6,pulse:1e-4,duration:1e-3,
    damping:0,frames:61,boundary:0,loadMode:0,confineX:0,confineY:0,timeLimitSeconds:1800,planeMode:1,
    sourceMode:0,productEOS:0,productDensity:1000,productEnergy:1e6,productGamma:1.3,detonationVelocity:2000,
    jwlA:0,jwlB:0,jwlR1:4.5,jwlR2:1.1,jwlOmega:.3,
    airDensity:1.2,airPressure:101325,airGamma:1.4,airEOS:0,rockModel:3});
  function normalize(input={}) {
    const settings={...defaults,...input};
    if(input.chargeRadius===undefined)settings.chargeRadius=input.radius ?? defaults.radius;
    for(const key of Object.keys(defaults)) {
      if(typeof settings[key]!=="number" || !Number.isFinite(settings[key])) throw new Error(`Invalid blast setting: ${key}`);
    }
    if(settings.radius<=0 || settings.chargeRadius<=0 || settings.pressure<0 || settings.pulse<=0 ||
      settings.duration<=0 || (settings.sourceMode===0 && settings.pulse>settings.duration) || settings.damping<0 ||
      !Number.isInteger(settings.frames) || settings.frames<2 || settings.frames>201) throw new Error("Invalid blast radius, pressure, times, damping or frame count.");
    if(![0,1,2,3].includes(settings.boundary) || ![0,1].includes(settings.loadMode) || settings.confineX<0 || settings.confineY<0 ||
      settings.timeLimitSeconds<1 || settings.timeLimitSeconds>7200) throw new Error("Invalid blast boundary, confinement or time limit.");
    if(settings.planeMode!==1)throw new Error('二维爆破只按平面应变计算，不支持平面应力。');
    if(![0,1].includes(settings.sourceMode) || ![0,1].includes(settings.productEOS) || settings.airEOS!==0)throw new Error("Invalid gas source or EOS mode.");
    if(!Number.isInteger(settings.rockModel) || settings.rockModel<0 || settings.rockModel>14)throw new Error("Invalid rock constitutive setting.");
    if(settings.sourceMode===1 && (!(settings.productDensity>0) || !(settings.productEnergy>0) ||
      (settings.productEOS===0 && !(settings.productGamma>1 && settings.productGamma<=10)) ||
      (settings.productEOS===1 && (settings.jwlA<0 || settings.jwlB<0 || !(settings.jwlR1>0) || !(settings.jwlR2>0) ||
        !(settings.jwlOmega>0 && settings.jwlOmega<=9) || (settings.jwlA===0 && settings.jwlB===0) || !(settings.detonationVelocity>0))) ||
      !(settings.airDensity>0) || !(settings.airPressure>0) || !(settings.airGamma>1 && settings.airGamma<=2)))throw new Error("Invalid gas/products parameters; JWL requires calibrated expansion coefficients and a detonation velocity.");
    const constraints=Gas.constraints(settings);if(constraints.errors.length)throw new Error(constraints.errors.map(e=>`${e.scope}：${e.message}`).join('\n'));
    return Object.fromEntries(Object.keys(defaults).map(key=>[key,settings[key]]));
  }
  // Settings saved by models of the removed legacy core may hold plane stress or EOS
  // without an OpenCourant card. Loading maps them to the only supported choices
  // (plane strain, ideal gap gas, ideal-gas products); new requests are still validated strictly.
  function migrate(stored={}){
    const {planeMode,airEOS,productEOS,...rest}=stored||{};
    return normalize({...rest,...([0,1].includes(productEOS)?{productEOS}:{})});
  }
  const api={defaults,normalize,migrate};
  if(typeof module!=="undefined" && module.exports) module.exports=api;
  else root.BlastSettings=api;
})(typeof window!=="undefined" ? window : globalThis);
