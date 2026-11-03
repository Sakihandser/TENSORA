# CB-Geo material kernels

Source: https://github.com/cb-geo/mpm/tree/53fcb7609375fd44bf3481d24ee18bfdf0393adb

Models: `mpm::LinearElastic<3>` and `mpm::MohrCoulomb<3>`. Source files are unchanged. `manifest.json` records original paths and SHA-256 hashes, verified before compilation. `upstream/license.md` is the project's MIT license; the bundled JSON, sparsepp, robin-map, spdlog/fmt licenses remain in `upstream/external`.

`TensoraCore/CBGeoMaterials.h` supplies only a build boundary: the particle/mesh implementation is excluded by its existing header guards. These material kernels accept an incomplete `ParticleBase` pointer and never dereference it; the host passes `nullptr`. No replacement material base class, yield surface, return mapping or softening equation is supplied. The downloaded original `Material`, `LinearElastic`, `MohrCoulomb` and material utilities are compiled as written.

Host mapping: SI density kg/m³ and stress/modulus Pa; input angles in degrees (the library converts them to radians); strain is dimensionless; Voigt order xx, yy, zz, xy, yz, xz with engineering shear. State maps are copied with each host material state, so trial calls do not accumulate history. Each element owns a separate material instance. Plastic deviatoric strain is exported. Mohr–Coulomb does not define a scalar crack-damage variable, so the host does not invent one; crack-storage feedback is consequently inactive for that material. Its softening is controlled by its material-card flag. Plastic-work diagnostics are not yet evaluated for this model.

Build: import `CBGeoMaterials.props`, then build the main Release x64 project. The material kernels are compiled into the EXE; no separate CB-Geo DLL or complete MPM solver is needed. Run `node tests/new-constitutive-ui.cjs` for UI/persistence checks and `node --test tests/new-constitutive.test.js` for native/coupling checks. The latter requires the already-built main EXE.
