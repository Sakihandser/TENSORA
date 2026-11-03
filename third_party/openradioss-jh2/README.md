# OpenRadioss JH2 runtime

This directory is an **executed dependency**, not a reference snapshot. The JH2
branch calls the original Fortran `SIGEPS79` from the OpenRadioss LAW79 material
through the C ABI in `bridge.f90`. The original files in `upstream/` are unmodified.
`manifest.json` pins the repository, commit, original paths, and SHA-256 hashes.

Source: [OpenRadioss mirror, commit bad6688602d770e019b75773d2d5a48b4f9bd918](https://github.com/gabrielrussell/OpenRadioss/tree/bad6688602d770e019b75773d2d5a48b4f9bd918).
This is the archived mirror identified by that exact commit; it is not represented
as a new release of the full solver. Only its LAW79 material kernel and required
constants/includes are built. The TRI3 dynamics and gas solver remain TENSORA's.

## Build and deployment

On x64 Windows, use GNU Fortran (set `TENSORA_GFORTRAN`) or bootstrap the pinned
portable compiler with `powershell -File scripts/setup-jh2-toolchain.ps1`.
The local compiler is kept in `.tools/fortran`, separate from disposable `tmp/`.
Then build the Visual Studio project normally. The imported MSBuild target builds
`openradioss_jh2.dll` into the executable's output directory. For a direct build:

```powershell
powershell -File scripts/build-jh2.ps1 -OutputDirectory TensoraCore/x64/Release
```

GNU Fortran runtime libraries are linked statically into this DLL. Users running
the program do not need a compiler. Distribute the DLL **next to** the native EXE;
it is loaded by absolute path. Missing/mismatched DLLs produce errors; there is no
local JH2 fallback. `openradioss_jh2.build.json` records the actual compiler,
bridge/source hashes and binary hash. The source files are checked before builds.
Static runtime notices are preserved in `runtime-notices/` (MinGW-w64, GPLv3,
and the GCC Runtime Library Exception).

## Interface boundary

- The bridge packs/unpacks arrays only. `SIGEPS79` performs EOS pressure,
  tensile cutoff, strength, radial return, damage and bulking updates.
- Parameters use SI units. `G2=2G`, `TSTAR=T/pHEL`, `SHEL=sigmaHEL` and engineering
  shear increments are passed as expected by the upstream routine. No paper
  material constants are adjusted. The rate is the equivalent deviatoric strain
  rate supplied by the host dynamics, as it is in OpenRadioss.
- Upstream history `DMG`, `DEFP`, `UVAR(1:2)`, and `ET` is preserved between calls.
- Pressure is reconstructed from density by upstream. The previous **deviator**
  is passed separately from the volume state; this is algebraically equivalent to
  its internal pressure subtraction and avoids hydrostatic cancellation noise.
  Pure hydrostatic stress is packed as an exactly zero deviator. No damage or
  returned stress is corrected after the upstream call.
- Prescribed initial stress sets the reference density by an EOS root solve.
  Subsequent volume ratios come from the host strain/kinematics. This replaces
  the former additive pressure offset; it is not a new material parameter.
- Local damage (`INLOC=0`) and no element deletion (`IDEL=0`) are selected. A
  nonzero legacy `referenceLength` is rejected: upstream nonlocal fields and
  element deletion/contact have not been connected to this continuous TRI3 mesh.
- With damage disabled, the host retains the previous damage and disables the
  bulking-energy transfer. Plastic stress return still uses the upstream kernel.
  Local energy diagnostics do not feed back into its stress or damage.

`tests/jh2-upstream.test.js` compares the C++ material path against a separately
compiled Fortran host that directly calls `SIGEPS79`, without `bridge.f90`.
It also checks the source hashes and explicit failure without the runtime.
These checks verify material integration, not reproduction of a full blast model.

## License

The upstream files and the compiled OpenRadioss component are
**AGPL-3.0-or-later**, with their complete original license in `upstream/LICENSE.md`.
The bridge is distributed under the same license. TENSORA's existing MIT notice
does not replace this component's license. Distributing a linked combined program
must honor the AGPL, including providing its corresponding source and build
instructions. The complete component source and instructions are included here;
no release or publication is performed by the integration itself.
