# Rebuilds third_party/opencourant/userlib-rht/libraduser_win64.dll from the
# OpenCourant repository's tools/rht_user_material sources and the official
# OpenCourant userlib SDK (OpenCourant/Tools, pinned commit). No TENSORA code is
# compiled into the library. Requires the portable GNU Fortran toolchain in
# .tools/fortran/w64devkit (or TENSORA_GFORTRAN_BIN), Visual Studio's bundled
# CMake/Ninja, Git and Python 3.
param(
  [string]$OpenCourantSource = (Join-Path $PSScriptRoot '..\..\OpenCourant-main'),
  [string]$Work = (Join-Path $env:TEMP 'tensora-build\rht'),
  [switch]$Verify
)
$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '..')
$sdkCommit = '4e52942e191d3b1ede4b320fb0f1780f4e41b59a'
$gfortranBin = if ($env:TENSORA_GFORTRAN_BIN) { $env:TENSORA_GFORTRAN_BIN } else { Join-Path $root '.tools\fortran\w64devkit\bin' }
$vs = 'C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft'
$git = Join-Path $vs 'TeamFoundation\Team Explorer\Git\cmd\git.exe'
$env:Path = "$gfortranBin;$vs\CMake\CMake\bin;$vs\CMake\Ninja;" + $env:Path
$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (Test-Path (Join-Path $root '.tools\fracture-python\Scripts\python.exe')) { $python = Join-Path $root '.tools\fracture-python\Scripts\python.exe' }
$tool = Join-Path (Resolve-Path $OpenCourantSource) 'tools\rht_user_material'
if (-not (Test-Path (Join-Path $tool 'rht_material_mod.F90'))) { throw "RHT sources not found in $tool" }

New-Item -ItemType Directory -Force $Work | Out-Null
Push-Location $Work
try {
  if (-not (Test-Path 'Tools')) { & $git clone --quiet https://github.com/OpenCourant/Tools.git Tools }
  & $git -C Tools checkout --quiet $sdkCommit
  # The SDK's C wrapper relies on implicit declarations, which GCC 14+ rejects by
  # default, and its CMakeLists resets CMAKE_C_FLAGS; inject the options instead.
  Set-Content -Path inc.cmake -Encoding ascii -Value 'add_compile_options($<$<COMPILE_LANGUAGE:C>:-Wno-error=implicit-function-declaration> $<$<COMPILE_LANGUAGE:C>:-Wno-error=int-conversion> $<$<COMPILE_LANGUAGE:C>:-Wno-error=incompatible-pointer-types> $<$<COMPILE_LANGUAGE:Fortran>:-fallow-argument-mismatch>)'
  if (Test-Path sdk) { Remove-Item -Recurse -Force sdk }
  cmake -S Tools/userlib_sdk/source -B sdk -G Ninja -Darch=win64 -Dcompiler=gfortran -Dprecision=dp "-DCMAKE_PROJECT_INCLUDE=$Work/inc.cmake"
  if ($LASTEXITCODE) { throw 'SDK configure failed' }
  cmake --build sdk
  if ($LASTEXITCODE) { throw 'SDK build failed' }
  & $python -I (Join-Path $tool 'build_userlib.py') --sdk-build "$Work\sdk" --build-dir "$Work\library" --verify-adapter
  if ($LASTEXITCODE) { throw 'User library build failed' }
  if ($Verify) {
    # Upstream one-brick Starter/Engine checks on the bundled OpenCourant runtime.
    $env:PYTHONUTF8 = '1'
    & $python -I (Join-Path $tool 'tests\run_solver.py') --radioss-root (Join-Path $root 'third_party\opencourant\runtime-win-x64') --library "$Work\library\libraduser_win64.dll" --output "$Work\solver_runs"
    if ($LASTEXITCODE) { Write-Warning 'run_solver.py reported failures; the 20261011 th_to_csv may append non-printable bytes to column titles.' }
  }
  $target = Join-Path $root 'third_party\opencourant\userlib-rht'
  New-Item -ItemType Directory -Force (Join-Path $target 'source') | Out-Null
  Copy-Item "$Work\library\libraduser_win64.dll" $target -Force
  Copy-Item (Join-Path $tool '*.F90'),(Join-Path $tool 'build_userlib.py'),(Join-Path $tool 'README.md'),(Join-Path $tool 'VALIDATION.md') (Join-Path $target 'source') -Force
  Get-FileHash (Join-Path $target 'libraduser_win64.dll')
} finally { Pop-Location }
