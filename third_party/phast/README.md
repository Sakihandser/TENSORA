# PhAST upstream integration

Source: https://github.com/CEMS-Lab/PhAST

Pinned commit: `086b899ffbba1a52bcbec139a2a567e3bf93da56`, version 0.16.2, retrieved 2026-11-05. MIT license retained at `upstream/LICENSE`.

`upstream/src` is an unmodified copy of the upstream package. `manifest.json` records SHA256 for each retained source and metadata file. Local integration lives in `scripts/phast-bridge.py` and `fracture-runner.js`; it supplies mesh/material data, boundary conditions, loading increments, and translates output. Equilibrium, staggered coupling, damage PDE solution, history irreversibility and stiffness degradation are upstream calls, not reimplemented here.

The installed environment is `.tools/fracture-python`, excluded from source control. Recreate with Python 3.12 and `scripts/setup-fracture.ps1 -Python <python.exe>`. Exact installed packages are retained in `requirements-lock.txt`; PyTorch CPU wheels use the official PyTorch wheel index. Portable distributions must package a Python environment separately or run setup. `TENSORA_FRACTURE_PYTHON` can point to another compatible interpreter.

Integrated route: CPU float64, T3 triangles, SI data through the direct Python API, small-strain plane strain, Amor split, AT2, projected damage bounds and upstream SciPy mechanics backend. Per-element E and Gc use upstream material-field APIs. Poisson ratio and phase-field length must match across materials. Residual stiffness is fixed at 1e-7. Force and displacement control are separate. No J2/fracture coupling, finite deformation or transient fracture is exposed by this adapter.

Run `node --test tests/fracture.test.js` to verify source hashes, material restrictions, irreversible notched-plate fracture, post-peak reaction drop and force/multi-material execution. Run `node tests/fracture-browser.cjs` to exercise the UI and actual HTTP solver path. The notch check is a coarse implementation regression, not a published quantitative benchmark reproduction or mesh convergence study.
