param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$environmentDir = Join-Path $projectRoot '.tools/fracture-python'
& $Python -m venv $environmentDir
if ($LASTEXITCODE -ne 0) { throw 'Cannot create the fracture Python environment. Specify -Python with a Python 3.12 executable.' }
$fracturePython = Join-Path $environmentDir 'Scripts/python.exe'
& $fracturePython -m pip install 'torch==2.15.0+cpu' --index-url https://download.pytorch.org/whl/cpu
if ($LASTEXITCODE -ne 0) { throw 'PyTorch installation failed.' }
& $fracturePython -m pip install -r (Join-Path $projectRoot 'third_party/phast/requirements-lock.txt')
if ($LASTEXITCODE -ne 0) { throw 'Fracture dependencies installation failed.' }
$previousPythonPath=$env:PYTHONPATH
try {
    $env:PYTHONPATH = Join-Path $projectRoot 'third_party/phast/upstream/src'
    & $fracturePython -c 'import phast,torch; print("PhAST import OK", torch.__version__)'
    if ($LASTEXITCODE -ne 0) { throw 'PhAST import verification failed.' }
} finally { $env:PYTHONPATH=$previousPythonPath }
