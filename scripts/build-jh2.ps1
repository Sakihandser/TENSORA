param([Parameter(Mandatory=$true)][string]$OutputDirectory, [string]$Compiler, [switch]$VerifyDriver)
$ErrorActionPreference='Stop'
$env:PSModulePath=$env:PSModulePath+[IO.Path]::PathSeparator+(Join-Path $PSHOME 'Modules')
function Get-TaskHash([string]$TaskPath){$taskSha=[Security.Cryptography.SHA256]::Create();try{return [BitConverter]::ToString($taskSha.ComputeHash([IO.File]::ReadAllBytes($TaskPath))).Replace('-','')}finally{$taskSha.Dispose()}}
$taskRoot=Split-Path -Parent $PSScriptRoot
$taskComponent=Join-Path $taskRoot 'third_party/openradioss-jh2'
$taskManifest=Get-Content -LiteralPath (Join-Path $taskComponent 'manifest.json') -Raw | ConvertFrom-Json
foreach($taskFile in $taskManifest.files){
  $taskActual=(Get-TaskHash (Join-Path $taskComponent $taskFile.file))
  if($taskActual -ne $taskFile.sha256){throw "Upstream JH2 source hash mismatch: $($taskFile.file)"}
}
if(!$Compiler){$Compiler=$env:TENSORA_GFORTRAN}
if(!$Compiler){$taskCommand=Get-Command gfortran -ErrorAction SilentlyContinue;if($taskCommand){$Compiler=$taskCommand.Source}}
if(!$Compiler){$Compiler=Join-Path $taskRoot '.tools/fortran/w64devkit/bin/gfortran.exe'}
if(!(Test-Path -LiteralPath $Compiler) -and (Test-Path -LiteralPath (Join-Path $taskRoot 'tmp/jh2-upstream/toolchain/w64devkit/bin/gfortran.exe'))){$Compiler=Join-Path $taskRoot 'tmp/jh2-upstream/toolchain/w64devkit/bin/gfortran.exe'}
if(!(Test-Path -LiteralPath $Compiler)){throw 'GNU Fortran is required: set TENSORA_GFORTRAN or run scripts/setup-jh2-toolchain.ps1.'}
$taskOutput=[IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Force -Path $taskOutput | Out-Null
# Build in an ASCII path: GNU Fortran module/include handling is not Unicode-safe.
$taskBuild=Join-Path ([IO.Path]::GetTempPath()) ('tensora-jh2-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $taskBuild | Out-Null
Copy-Item -LiteralPath (Join-Path $taskComponent 'upstream') -Destination (Join-Path $taskBuild 'upstream') -Recurse
Copy-Item -LiteralPath (Join-Path $taskComponent 'bridge.f90') -Destination $taskBuild
$taskFlags=@('-O2','-cpp','-DMYREAL8','-DCPP_mach=CPP_p4win64','-std=legacy','-ffixed-line-length-none','-frecursive','-fstack-arrays','-I','upstream')
Push-Location $taskBuild
try {
  foreach($taskUnit in @('constant_mod','sigeps79')){
    & $Compiler @taskFlags -c "upstream/$taskUnit.F" -o "$taskUnit.o"
    if($LASTEXITCODE -ne 0){throw "JH2 compilation failed: $taskUnit"}
  }
  & $Compiler -O2 -frecursive -c bridge.f90 -o bridge.o
  if($LASTEXITCODE -ne 0){throw 'JH2 C ABI compilation failed.'}
  & $Compiler -shared -static -static-libgcc -static-libgfortran constant_mod.o sigeps79.o bridge.o -o openradioss_jh2.dll
  if($LASTEXITCODE -ne 0){throw 'JH2 DLL link failed.'}
  Copy-Item -LiteralPath openradioss_jh2.dll -Destination $taskOutput -Force
  if($VerifyDriver){
    Copy-Item -LiteralPath (Join-Path $taskRoot 'tests/native/JH2UpstreamVerification.f90') -Destination driver.f90
    & $Compiler -O2 -frecursive -static -static-libgcc -static-libgfortran driver.f90 constant_mod.o sigeps79.o -o jh2-upstream-verification.exe
    if($LASTEXITCODE -ne 0){throw 'Direct upstream verification driver build failed.'}
    Copy-Item -LiteralPath jh2-upstream-verification.exe -Destination $taskOutput -Force
  }
} finally {Pop-Location}
$taskRecord=@{upstream=$taskManifest.repository;commit=$taskManifest.commit;abi=1;sourceHash=(Get-TaskHash (Join-Path $taskComponent 'upstream/sigeps79.F'));bridgeHash=(Get-TaskHash (Join-Path $taskComponent 'bridge.f90'));compiler=(& $Compiler --version | Select-Object -First 1);dllHash=(Get-TaskHash (Join-Path $taskOutput 'openradioss_jh2.dll'))}
$taskRecord | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskOutput 'openradioss_jh2.build.json') -Encoding utf8
$taskResolvedBuild=[IO.Path]::GetFullPath($taskBuild)
$taskResolvedTemp=[IO.Path]::GetFullPath([IO.Path]::GetTempPath())
if(!$taskResolvedBuild.StartsWith($taskResolvedTemp,[StringComparison]::OrdinalIgnoreCase) -or (Split-Path -Leaf $taskResolvedBuild) -notlike 'tensora-jh2-*'){throw 'Refusing to clean an unexpected JH2 build directory.'}
Remove-Item -LiteralPath $taskResolvedBuild -Recurse -Force
Write-Output "Built OpenRadioss SIGEPS79 $($taskManifest.commit) -> $taskOutput"
