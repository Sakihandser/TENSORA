# Build the MFEM pre-stress driver used by the 3D blast workspace.
# MFEM is compiled from the unmodified mfem-4.10 source tree (default: the
# sibling ..\mfem-4.10 folder). The executable is statically linked against
# MFEM and the MSVC runtime, so end users need no compiler or extra DLLs.
param(
  [string]$MfemSource = (Join-Path $PSScriptRoot '..\..\mfem-4.10'),
  [string]$BuildRoot = (Join-Path $env:TEMP 'tensora-build'),
  [string]$OutputDirectory = (Join-Path $PSScriptRoot '..\third_party\mfem\runtime-win-x64')
)
$ErrorActionPreference = 'Stop'
$cmake = (Resolve-Path 'C:\Program Files\Microsoft Visual Studio\2022\*\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe' | Select-Object -First 1).Path
if (-not $cmake) { throw 'Visual Studio 2022 CMake was not found.' }
$MfemSource = (Resolve-Path $MfemSource).Path
New-Item -ItemType Directory -Force $BuildRoot, $OutputDirectory | Out-Null
# MSVC/CMake are most reliable with ASCII paths; the project may live in a CJK folder.
$src = Join-Path $BuildRoot 'mfem-src'
if (-not (Test-Path $src)) { New-Item -ItemType Junction -Path $src -Target $MfemSource | Out-Null }
$driverSrc = Join-Path $BuildRoot 'prestress-src'
if (Test-Path $driverSrc) { Remove-Item $driverSrc -Recurse -Force }
Copy-Item (Join-Path $PSScriptRoot '..\TensoraCore\MfemPrestress') $driverSrc -Recurse
$runtime = '-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded'
# MFEM sources contain UTF-8 comments; on CJK Windows MSVC must not read them as the ANSI code page.
$flags = '-DCMAKE_CXX_FLAGS=/DWIN32 /D_WINDOWS /EHsc /utf-8'
& $cmake -S $src -B "$BuildRoot\mfem-build" -G 'Visual Studio 17 2022' -A x64 -DCMAKE_POLICY_DEFAULT_CMP0091=NEW $runtime $flags `
  -DMFEM_USE_MPI=NO -DMFEM_USE_OPENMP=NO -DMFEM_ENABLE_EXAMPLES=NO -DMFEM_ENABLE_MINIAPPS=NO -DMFEM_ENABLE_TESTING=NO `
  -DBUILD_SHARED_LIBS=OFF "-DCMAKE_INSTALL_PREFIX=$BuildRoot\mfem-install"
if ($LASTEXITCODE) { throw 'MFEM configure failed' }
& $cmake --build "$BuildRoot\mfem-build" --config Release --parallel 16 -- /v:minimal
if ($LASTEXITCODE) { throw 'MFEM build failed' }
& $cmake --install "$BuildRoot\mfem-build" --config Release
if ($LASTEXITCODE) { throw 'MFEM install failed' }
& $cmake -S $driverSrc -B "$BuildRoot\prestress-build" -G 'Visual Studio 17 2022' -A x64 -DCMAKE_POLICY_DEFAULT_CMP0091=NEW $runtime $flags "-Dmfem_DIR=$BuildRoot\mfem-install\lib\cmake\mfem"
if ($LASTEXITCODE) { throw 'Driver configure failed' }
& $cmake --build "$BuildRoot\prestress-build" --config Release
if ($LASTEXITCODE) { throw 'Driver build failed' }
$exe = Join-Path $OutputDirectory 'mfem_prestress.exe'
Copy-Item "$BuildRoot\prestress-build\Release\mfem_prestress.exe" $exe -Force
Copy-Item (Join-Path $MfemSource 'LICENSE') (Join-Path $OutputDirectory 'MFEM-LICENSE') -Force
Copy-Item (Join-Path $MfemSource 'NOTICE') (Join-Path $OutputDirectory 'MFEM-NOTICE') -Force
$info = [ordered]@{
  component = 'mfem_prestress'; mfemVersion = '4.10'; mfemSource = 'mfem-4.10 (unmodified upstream release)'
  driverSha256 = (Get-FileHash (Join-Path $PSScriptRoot '..\TensoraCore\MfemPrestress\mfem_prestress.cpp') -Algorithm SHA256).Hash.ToLower()
  exeSha256 = (Get-FileHash $exe -Algorithm SHA256).Hash.ToLower(); builtAt = (Get-Date).ToString('s')
}
$info | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $OutputDirectory 'build.json')
Write-Output "Built $exe"
