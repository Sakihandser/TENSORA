# SU2 runtime (fluid–structure interaction)

`runtime-win-x64/SU2_CFD.exe` is the unmodified official Windows build of
[SU2](https://github.com/su2code/SU2) (LGPL-2.1, see `runtime-win-x64/SU2-LICENSE.md`).
TENSORA only writes SU2 meshes and configuration files, launches the program and
reads its ASCII restart, VTK and history output; the finite-volume flow solver,
the FEA structural solver, the mesh deformation, the interface interpolation and
the block Gauss–Seidel coupling are the upstream code.

| Item | Value |
| --- | --- |
| Release | `v8.6.0` "Harrier" |
| Asset | `SU2_v8.6.0_win64-omp.zip`, 29,350,764 bytes |
| Asset SHA-256 | `4bc28b656def415b4d22c8274af2473dd719aa5ebfa6bc1c95c08b1bac26508c` |
| Source | https://github.com/su2code/SU2/releases/tag/v8.6.0 |
| Used executable | `bin/SU2_CFD.exe` (OpenMP build, no MPI runtime required) |

TENSORA runs the bundled executable directly with relative mesh and configuration
paths. `manifest.json` records the executable hash.

## Options used by TENSORA

- `SOLVER= MULTIPHYSICS` with `CONFIG_LIST= (config_flow.cfg, config_solid.cfg)`,
  `MULTIZONE_MESH= NO`, `MARKER_ZONE_INTERFACE= (fsi_fluid, fsi_solid)`.
- Flow zone: `INC_NAVIER_STOKES` / `INC_RANS` (constant density, `INC_NONDIM= DIMENSIONAL`)
  or `NAVIER_STOKES` / `RANS` / `EULER` with `FLUID_MODEL= IDEAL_GAS`;
  `DEFORM_MESH= YES`, `MARKER_DEFORM_MESH= (fsi_fluid)`.
- Structural zone: `SOLVER= ELASTICITY`, `LINEAR_ELASTIC` or `NEO_HOOKEAN`,
  `MARKER_FLUID_LOAD= (fsi_solid)`, `MARKER_CLAMPED` / `MARKER_SYM`, and an
  element property file for several materials (`FEA_FILENAME`).
- Coupling: `BGS_RELAXATION= AITKEN_DYNAMIC` or `FIXED_PARAMETER`; transient runs
  use `TIME_MARCHING= DUAL_TIME_STEPPING-2ND_ORDER` and `NEWMARK_IMPLICIT`.
- Output: `OUTPUT_FILES= (RESTART_ASCII, PARAVIEW_ASCII[, SURFACE_CSV])`.

The one-way path runs the flow zone alone (rigid walls) and passes the wall
pressure and skin friction to the MFEM driver `third_party/mfem/runtime-win-x64/mfem_fsi.exe`.
