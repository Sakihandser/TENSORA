# Direct LANL Singularity-EOS runtime

2026-11-01: NobleAbel (model 3) and StiffGas (model 4) are also compiled from unmodified headers at the same commit. For these two models the seven-slot ABI array is `{gamma, covolume, pressureOffset, energyShift, 0, 0, 0}`: covolume in m³/kg, pressureOffset in Pa, energyShift in J/kg. The original seven slots for models 0/1 are unchanged. Since this upstream revision lacks a rho-p inverse for models 3/4, the bridge brackets and bisects their original pressure API. It rejects the covolume singularity, nonpositive thermal domain and clamped nonpositive pressure states. See [model parameters and validation](../../docs/CONSTITUTIVE_MODELS.md).

The blast core calls the unmodified C++ `singularity::JWL` and `singularity::IdealGas` implementations through `singularity_eos.dll`. `bridge.cpp` only validates and maps inputs; no EOS equation or local fallback is implemented there.

Source: [LANL Singularity-EOS](https://github.com/lanl/singularity-eos/tree/b4f71a7748770dfa6ce4d678754c463c09262fb7), commit `b4f71a7748770dfa6ce4d678754c463c09262fb7`; Ports-of-call commit `b24342966968ee768de1bd825f4582aba61b2fde`. `manifest.json` lists every compiled transitive header with repository, original path and SHA-256. Hashes are checked before every build. The upstream licenses are included alongside the source.

The bridge calls `PressureFromDensityInternalEnergy`, `BulkModulusFromDensityInternalEnergy` and `InternalEnergyFromDensityPressure`. Parameters are `{gamma,rho0,A,B,R1,R2,omega}` in kg/m³, Pa and J/kg; gamma, R1, R2 and omega are dimensionless. Sound speed squared is bulk modulus divided by current density. Reference density rho0 always remains the initial product density.

Cv=1 is a constructor placeholder, not a thesis heat capacity. None of the called density-energy pressure/bulk or density-pressure energy methods depends on Cv. Temperature and entropy are not exposed. Thermal features would require physical caloric parameters.

Build Release x64 with Visual Studio 2022 MSVC v143 using `SingularityEOS.vcxproj`, or the parent `TensoraCore.vcxproj`. `SingularityEOS.targets` builds, verifies source hashes and deploys the DLL next to the core. The core loads that absolute adjacent path and checks ABI=1 and the pinned commit. Missing or mismatched libraries fail explicitly.

This replaces material EOS only. Radial finite-volume, interface, work-transfer and axial-vent algorithms remain application code. No blast simulation was rerun during this audit on 2026-10-28.
