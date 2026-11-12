param([string]$EnvironmentPath = '')
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (-not $EnvironmentPath) { $EnvironmentPath = Join-Path $root '.tools/fracture-python' }
$phast = Join-Path $root 'third_party/phast'
$target = Join-Path $phast 'runtime-win-x64'
$embedded = 'python-3.12.10-embed-amd64.zip'
$digest = '4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3'
$crtSource = Join-Path $root 'third_party/oofem/oofem_3.0_AMD64/bin'

function Copy-LocalCrt([string]$Directory) {
    # Keep the CPython archive's own VCRUNTIME files and add the C++ runtime used by its wheels.
    Get-ChildItem -LiteralPath $crtSource -Filter 'msvcp140*.dll' | Copy-Item -Destination $Directory
}

function Test-EmbeddedPython([string]$Directory) {
    $python = Join-Path $Directory 'python.exe'
    $source = Join-Path $phast 'upstream/src'
    $requirements = Join-Path $phast 'requirements-lock.txt'
    & $python -c @'
import importlib.metadata as metadata
from pathlib import Path
import sys
sys.path.insert(0, sys.argv[1])
for row in Path(sys.argv[2]).read_text(encoding="utf-8").splitlines():
    if row.strip():
        package, expected = row.strip().split("==", 1)
        actual = metadata.version(package)
        if actual != expected:
            raise RuntimeError(f"{package}: expected {expected}, got {actual}")
import gmsh, numpy, scipy, torch, phast
print(f"PhAST runtime verified with Python {sys.version.split()[0]} and torch {torch.__version__}")
'@ $source $requirements
    if ($LASTEXITCODE -ne 0) { throw 'Portable PhAST runtime did not pass its import and version checks.' }
}

if (Test-Path -LiteralPath $target) {
    Copy-LocalCrt $target
    Test-EmbeddedPython $target
    return
}
$lib = Join-Path $EnvironmentPath 'Lib'
if (-not (Test-Path -LiteralPath (Join-Path $lib 'site-packages'))) {
    throw 'Run scripts/setup-fracture.ps1 with Python 3.12 to stage the locked dependencies.'
}
$downloads = Join-Path $root '.tools/downloads'
New-Item -ItemType Directory -Path $downloads -Force | Out-Null
$archive = Join-Path $downloads $embedded
if (-not (Test-Path -LiteralPath $archive)) {
    curl.exe --fail --location --silent --show-error "https://www.python.org/ftp/python/3.12.10/$embedded" --output $archive
    if ($LASTEXITCODE -ne 0) { throw 'Failed to download the official CPython embedded archive.' }
}
if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $digest) {
    throw 'The embedded CPython archive SHA-256 does not match.'
}
$stage = Join-Path $phast ('runtime-stage-' + [Guid]::NewGuid().ToString('N'))
Expand-Archive -LiteralPath $archive -DestinationPath $stage
robocopy $lib (Join-Path $stage 'Lib') /E /XJ /XD __pycache__ /XF '*.pyc' '*.pyo' /NFL /NDL /NJH /NJS /NP
if ($LASTEXITCODE -ge 8) { throw 'Failed to copy the locked PhAST dependencies.' }
Set-Content -LiteralPath (Join-Path $stage 'python312._pth') -Encoding ascii -Value @('python312.zip', '.', 'Lib', 'Lib/site-packages', 'import site')
Copy-LocalCrt $stage
Test-EmbeddedPython $stage
Move-Item -LiteralPath $stage -Destination $target
