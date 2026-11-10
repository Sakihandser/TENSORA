$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$core = Join-Path $root 'TensoraCore'
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$vs = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (!$vs) { throw 'Visual Studio C++ build tools are required.' }
$vcvars = Join-Path $vs 'VC/Auxiliary/Build/vcvars64.bat'
$build = Join-Path ([IO.Path]::GetTempPath()) ('tensora-pcg-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $build | Out-Null
Copy-Item -LiteralPath (Join-Path $core 'Solid3dPcg.cpp'),(Join-Path $core 'OpenClApi.h') -Destination $build
Copy-Item -LiteralPath (Join-Path $core 'vendor') -Destination $build -Recurse
Push-Location $build
try {
    $compiler = 'call "'+$vcvars+'" && cl.exe /nologo /O2 /openmp /std:c++17 /EHsc /MT /Ivendor/opencl Solid3dPcg.cpp /Fe:Solid3dPcg.exe'
    & $env:ComSpec /d /c $compiler
    if ($LASTEXITCODE -ne 0) { throw 'Solid3dPcg compilation failed.' }
    Copy-Item -LiteralPath 'Solid3dPcg.exe' -Destination (Join-Path $core 'x64/Release/Solid3dPcg.exe') -Force
} finally {
    Pop-Location
    $temp = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
    $resolvedBuild = [IO.Path]::GetFullPath($build)
    if ($resolvedBuild.StartsWith($temp,[StringComparison]::OrdinalIgnoreCase) -and (Split-Path -Leaf $resolvedBuild) -like 'tensora-pcg-*') {
        Remove-Item -LiteralPath $resolvedBuild -Recurse -Force
    }
}
