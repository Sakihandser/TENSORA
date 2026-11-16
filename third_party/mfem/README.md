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

# MFEM one-way fluid–structure driver

`runtime-win-x64/mfem_fsi.exe` is built by `scripts/build-mfem-fsi.ps1` from
`mfem-4.10-source.tar.gz` in this directory and `TensoraCore/MfemFsi/mfem_fsi.cpp`.
The archive SHA-256 is `40784df5b9be3a1963fea2cc6cdb54030eb75785e8b1c271cc1b46d6c448c032`.
The optional rebuild uses the Visual Studio 2022 C++ toolchain and CMake. It
extracts and builds the source under the project's `.tools/build` directory.
MFEM diagnostics report source paths relative to the project.
The driver solves the structure of the one-way FSI path under the wall loads of the SU2 flow:
the SU2 vertex pressure and wall shear (skin friction × reference dynamic
pressure) become order-1 H1 `GridFunction`s; `VectorBoundaryFluxLFIntegrator`
(−p n) and `VectorBoundaryLFIntegrator` (τ) integrate them on the wetted boundary;
`ElasticityIntegrator`, `FormLinearSystem`, `CGSolver` + `GSSmoother` and
`ComputeElementFlux` give displacements and element stresses on TRI3 or TET4
meshes. Boundary attributes: 1 wetted interface, 2 clamped, 3/4/5 roller in x/y/z.
Plane stress uses the reduced Lamé parameter 2λμ/(λ+2μ). `build-fsi.json`
records the driver and executable hashes.
