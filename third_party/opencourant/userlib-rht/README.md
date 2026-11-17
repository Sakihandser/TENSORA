# RHT user material library (OpenCourant `/MAT/USER01`)

`libraduser_win64.dll` is the Riedel–Hiermaier–Thoma (RHT) concrete/rock solid
material from the OpenCourant repository, `tools/rht_user_material`, compiled
unchanged against the official OpenCourant user library SDK. TENSORA writes the
`/MAT/USER01` card and passes `-dylib libraduser_win64.dll` to the bundled
OpenCourant 20261011 Starter and Engine; the stress update, EOS, damage and
erosion are computed by this library inside the Engine.

| Item | Value |
| --- | --- |
| Material source | OpenCourant `tools/rht_user_material` (snapshot in `source/`, AGPL-3.0, see `LICENSE.md`) |
| `rht_material_mod.F90` SHA-256 | `CA8406FA227E76C16E4E3AC38DED29A8D011FD1E7F57058E75A4DF3665681AD7` |
| `lecmuser01.F90` SHA-256 | `205E05CDA0C6815B15A3D03535DC7B00C606142FC947290CB29B6DBAB05AD722` |
| `luser01.F90` SHA-256 | `5E4546B6C92C7C1893812C49A20D6E8C58810B736E2BAC2B90ED51AA86469919` |
| SDK | [OpenCourant/Tools](https://github.com/OpenCourant/Tools) `userlib_sdk`, commit `4e52942e191d3b1ede4b320fb0f1780f4e41b59a` (the commit named in the material's README) |
| Compiler | GNU Fortran/GCC 16.2.0 (w64devkit 2.10.1), double precision, `-static` |
| Library SHA-256 | `14FE11DB62AF42930056FCCDAC9AE3D33F29E327B8E4B5647240F62FBD38AA2E` |

Rebuild with `powershell -File scripts/build-rht-userlib.ps1 -Verify`. GCC 14
and newer reject the SDK C wrapper's implicit declarations; the script only
adds `-Wno-error=…` options through `CMAKE_PROJECT_INCLUDE` and does not edit
the SDK or the material source.

## Verification on the bundled runtime (2026-11-17)

- `build_userlib.py --verify-adapter`: the SDK adapter test passed (Starter
  parameters, PARMAT, batched state, shear order, energy units, inactive element).
- `tests/run_solver.py` against `third_party/opencourant/runtime-win-x64`
  (OpenCourant 20261011): all ten one-brick cases (elastic, hydro, compression,
  tension, hydro_tension, fast, energy, gruneisen, unload, spall) ran through
  Starter and Engine with normal termination and passed every history check.
  The 20261011 `th_to_csv` appends non-printable bytes after the column titles,
  so the run used a copy of the script that reads the CSV as Latin-1 and takes
  the variable name after the element id; the material checks were unchanged.

Animation output: `/ANIM/ELEM/USER3` gives the RHT damage D (VTK
`3DELEM_User_Var_3`); plastic strain is the standard `/ANIM/ELEM/EPSP`.
See `source/README.md` for the equations, the 38 constants and the limits of
this implementation (no nonlocal regularization or mesh-size scaling).
