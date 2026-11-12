# OpenCourant runtime (3D blast)

`runtime-win-x64/` holds the unmodified official Windows SMP package of
[OpenCourant](https://github.com/OpenCourant/OpenCourant), the community
continuation of OpenRadioss (AGPL-3.0). TENSORA only writes Starter/Engine input
decks, launches the executables and reads their animation output; the explicit
solver, material laws and output converters are the upstream programs.

| Item | Value |
| --- | --- |
| Release | `latest-20261011` (stable build 20261011, commit cb760c2) |
| Asset | `OpenCourant_win64.zip`, 350,476,183 bytes |
| SHA-256 | `6d0ea8b43b68aa12f0a2787b339384a554978cbb65a5d3dbaf1e40598f02e7e6` |
| Used executables | `exec/starter_win64.exe`, `exec/engine_win64.exe`, `exec/anim_to_vtk_win64.exe`, `exec/th_to_csv_win64.exe` |
| Support files | `hm_cfg_files/`, `extlib/hm_reader/win64`, `extlib/h3d/lib/win64`, `extlib/intelOneAPI_runtime/win64` (OpenMP/MKL runtime) |
| Licenses | `runtime-win-x64/licenses/` and the Intel runtime notices under `extlib/intelOneAPI_runtime/license/` |

The MPI engines, single-precision builds, the Intel MPI runtime and the
`openradioss_gui` folder of the package are not shipped because the 3D blast
workspace runs the SMP double-precision engine only. The matching source tree is
the `OpenCourant-main` folder next to this project (and the upstream repository).

## Upstream issues found while integrating

- `/BCS/NRF` on tetrahedral meshes: for triangular faces `node_list(4)` stays 0,
  but `starter/source/restart/ddsplit/split_bcs_nrf.F90` compares it with
  `node_list(3)` and then indexes node 0, which crashes the Starter depending on
  the mesh. The engine `/PARITH/ON` branch of `bcs_nrf.F90` also crashed with
  this package. TENSORA therefore builds absorbing boundaries from `/DAMP`
  (Caughey absorbing layer) instead of `/BCS/NRF`.
- `/ANIM/ELEM/DAMA` is not an engine keyword; material damage of LAW79 (JH2) is
  written with `/ANIM/ELEM/DAMG` and appears in VTK as `3DELEM_Damage`.

To refresh the runtime, download the release asset again, verify the SHA-256 and
copy the folders listed above.
