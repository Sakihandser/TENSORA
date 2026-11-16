# Build the MFEM one-way fluid–structure driver used by the FSI workspace.
# The bundled MFEM source and all intermediate outputs stay in this project.
# The executable is statically linked against MFEM and the MSVC runtime.
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$archive = Join-Path $root 'third_party\mfem\mfem-4.10-source.tar.gz'
$driverSrc = Join-Path $root 'TensoraCore\MfemFsi'
$OutputDirectory = Join-Path $root 'third_party\mfem\runtime-win-x64'
$cmake = (Get-Command cmake.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1).Source
if (-not $cmake) {
  $vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
  if (Test-Path -LiteralPath $vswhere) {
    $cmake = & $vswhere -latest -products '*' -version '[17.0,18.0)' -requires Microsoft.VisualStudio.Component.VC.CMake.Project -find 'Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe' | Select-Object -First 1
  }
}
if (-not $cmake) { throw 'CMake was not found. Install the Visual Studio 2022 C++ toolchain with CMake.' }
$sourceHash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
$BuildRoot = Join-Path $root ('.tools\build\mfem-fsi-portable-' + $sourceHash.Substring(0,12))
New-Item -ItemType Directory -Force $BuildRoot, $OutputDirectory | Out-Null
$MfemSource = Join-Path $BuildRoot 'mfem-4.10'
$sourceReady = Join-Path $BuildRoot 'source.sha256'
if (-not (Test-Path -LiteralPath $sourceReady)) {
  & (Join-Path $env:SystemRoot 'System32\tar.exe') -xzf $archive -C $BuildRoot
  if ($LASTEXITCODE) { throw 'MFEM source extraction failed' }
  Set-Content -LiteralPath $sourceReady -Value $sourceHash -Encoding ascii
}
$runtime = '-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded'
# Keep UTF-8 source and relative __FILE__ strings in MFEM's diagnostic messages.
$compilerConfig = Join-Path $BuildRoot 'compiler-flags.cmake'
$sourcePrefix = $root.Replace('\','/') + '/'
$flags = '/DWIN32 /D_WINDOWS /EHsc /utf-8 /MP2 /d1trimfile:"' + $sourcePrefix + '"'
Set-Content -LiteralPath $compilerConfig -Encoding utf8 -Value "set(CMAKE_CXX_FLAGS [=[$flags]=] CACHE STRING `"`" FORCE)"
$install = Join-Path $BuildRoot 'mfem-install'
if (-not (Test-Path (Join-Path $install 'lib\cmake\mfem'))) {
  & $cmake -S $MfemSource -B "$BuildRoot\mfem-build" -C $compilerConfig -G 'Visual Studio 17 2022' -A x64 $runtime `
    -DMFEM_USE_MPI=NO -DMFEM_USE_OPENMP=NO -DMFEM_ENABLE_EXAMPLES=NO -DMFEM_ENABLE_MINIAPPS=NO -DMFEM_ENABLE_TESTING=NO `
    -DBUILD_SHARED_LIBS=OFF "-DCMAKE_INSTALL_PREFIX=$install"
  if ($LASTEXITCODE) { throw 'MFEM configure failed' }
  & $cmake --build "$BuildRoot\mfem-build" --config Release --parallel 16 -- /v:minimal
  if ($LASTEXITCODE) { throw 'MFEM build failed' }
  & $cmake --install "$BuildRoot\mfem-build" --config Release
  if ($LASTEXITCODE) { throw 'MFEM install failed' }
}
& $cmake -S $driverSrc -B "$BuildRoot\fsi-build" -C $compilerConfig -G 'Visual Studio 17 2022' -A x64 $runtime "-Dmfem_DIR=$install\lib\cmake\mfem"
if ($LASTEXITCODE) { throw 'Driver configure failed' }
& $cmake --build "$BuildRoot\fsi-build" --config Release
if ($LASTEXITCODE) { throw 'Driver build failed' }
$exe = Join-Path $OutputDirectory 'mfem_fsi.exe'
Copy-Item "$BuildRoot\fsi-build\Release\mfem_fsi.exe" $exe -Force
Copy-Item (Join-Path $MfemSource 'LICENSE') (Join-Path $OutputDirectory 'MFEM-LICENSE') -Force
Copy-Item (Join-Path $MfemSource 'NOTICE') (Join-Path $OutputDirectory 'MFEM-NOTICE') -Force
$info = [ordered]@{
  component = 'mfem_fsi'; mfemVersion = '4.10'; mfemSource = 'mfem-4.10 (unmodified upstream release)'
  mfemSourceArchiveSha256 = $sourceHash
  driverSha256 = (Get-FileHash (Join-Path $PSScriptRoot '..\TensoraCore\MfemFsi\mfem_fsi.cpp') -Algorithm SHA256).Hash.ToLower()
  exeSha256 = (Get-FileHash $exe -Algorithm SHA256).Hash.ToLower(); builtAt = (Get-Date).ToString('s')
}
$info | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $OutputDirectory 'build-fsi.json')
Write-Output "Built $exe"
