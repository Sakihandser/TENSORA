$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$taskDirectory=Join-Path $taskRoot 'tmp/jh2-upstream'
New-Item -ItemType Directory -Force -Path $taskDirectory | Out-Null
$taskArchive=Join-Path $taskDirectory 'w64devkit-x64-2.10.1.7z.exe'
if(!(Test-Path -LiteralPath $taskArchive)){Invoke-WebRequest -Uri 'https://github.com/skeeto/w64devkit/releases/download/v2.10.1/w64devkit-x64-2.10.1.7z.exe' -OutFile $taskArchive}
if((Get-FileHash -LiteralPath $taskArchive).Hash -ne 'ADD1EDF984CE4D473CFEB7C52E0AB38DB73A855BBA6C7F564D5E16648EB2896A'){throw 'Fortran toolchain archive SHA256 mismatch.'}
$taskDestination=Join-Path $taskRoot '.tools/fortran'
New-Item -ItemType Directory -Force -Path $taskDestination | Out-Null
Start-Process -FilePath $taskArchive -ArgumentList @('-y',('-o"'+$taskDestination+'"')) -WindowStyle Hidden -Wait
if(!(Test-Path -LiteralPath (Join-Path $taskDestination 'w64devkit/bin/gfortran.exe'))){throw 'Fortran toolchain extraction failed.'}
Write-Output 'Portable GNU Fortran installed inside .tools/fortran; no system PATH changes.'
