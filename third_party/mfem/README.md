# MFEM initial-equilibrium driver (3D blast)

`runtime-win-x64/mfem_prestress.exe` solves the static equilibrium that precedes
a 3D blast run when "Static equilibrium first (MFEM)" is selected. It is built
by `scripts/build-mfem-prestress.ps1` from:

- the unmodified MFEM 4.10 release source (`../mfem-4.10` next to this project,
  BSD-3-Clause, see `runtime-win-x64/MFEM-LICENSE` and `MFEM-NOTICE`);
- `TensoraCore/MfemPrestress/mfem_prestress.cpp`, a thin driver that only calls
  MFEM: `Mesh` (MFEM v1.0 TET4 file), `H1_FECollection`, `ElasticityIntegrator`
  with `PWConstCoefficient` Lamé parameters per material, `FormLinearSystem`,
  `CGSolver` + `GSSmoother`, `RecoverFEMSolution` and
  `ElasticityIntegrator::ComputeElementFlux` for element stresses.

The consistent nodal loads come from the existing 3D load assembly
(`solid3d.js:assembleLoads`), the same vector that OpenCourant later holds with
`/CLOAD`. Element stresses are passed to OpenCourant with `/INIBRI/STRS_FGLO`;
the hydrostatic part is also encoded in the initial density because OpenCourant
recomputes pressure from the EOS (`mu = rho/rho0 - 1`) every cycle.

MSVC options: static runtime (`/MT`), no OpenMP, `/utf-8` (MFEM sources contain
UTF-8 comments that MSVC misreads on CJK Windows code pages). `build.json`
records the driver and executable hashes.
