param([string]$BuildRoot = '')
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$solver = Join-Path $root 'third_party/code-aster'
$runtime = Join-Path $solver 'runtime-win-x64'
$lock = Join-Path $solver 'runtime-lock.txt'

function Get-VerifiedArchive([string]$Uri, [string]$Path, [string]$Digest) {
    if (-not (Test-Path -LiteralPath $Path)) {
        $partial = $Path + '.part'
        curl.exe --fail --location --silent --show-error --retry 2 $Uri --output $partial
        if ($LASTEXITCODE -ne 0) { throw "Download failed: $Uri" }
        if ((Get-FileHash -LiteralPath $partial -Algorithm SHA256).Hash -ine $Digest) { throw "SHA-256 mismatch: $Uri" }
        Move-Item -LiteralPath $partial -Destination $Path -Force
    }
    if ((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash -ine $Digest) { throw "SHA-256 mismatch: $Path" }
}

Get-VerifiedArchive 'https://gitlab.com/codeaster/src/-/archive/18.1.11/src-18.1.11.tar.gz' `
    (Join-Path $solver 'src-18.1.11.tar.gz') 'b231de9ba3ec8af7ae94d1b9d7a9d7e84efaf0eafb074d80fcd39e98a6b9a6b8'

if (-not (Test-Path -LiteralPath (Join-Path $runtime 'python.exe'))) {
    if (-not $BuildRoot) { $BuildRoot = Join-Path ([IO.Path]::GetTempPath()) 'tensora-code-aster-build' }
    $BuildRoot = [IO.Path]::GetFullPath($BuildRoot)
    if ($BuildRoot -cmatch '[^\x20-\x7e]') { throw 'Set -BuildRoot to a writable ASCII path for micromamba.' }
    New-Item -ItemType Directory -Path $BuildRoot -Force | Out-Null
    $archive = Join-Path $BuildRoot 'micromamba.tar.bz2'
    Get-VerifiedArchive 'https://conda.anaconda.org/conda-forge/win-64/micromamba-2.10.0-0.tar.bz2' `
        $archive '6283f25f8142606d86e81a43c7103b5d4f1d5c2027e3f9d7326eff23b33930d8'
    tar.exe -xf $archive -C $BuildRoot Library/bin/micromamba.exe
    if ($LASTEXITCODE -ne 0) { throw 'Could not extract micromamba.' }
    $mamba = Join-Path $BuildRoot 'Library/bin/micromamba.exe'
    $stage = Join-Path $BuildRoot ('runtime-' + [Guid]::NewGuid().ToString('N'))
    $cache = Join-Path $BuildRoot 'cache'
    $stageLock = Join-Path $BuildRoot 'runtime-lock.txt'
    Copy-Item -LiteralPath $lock -Destination $stageLock -Force
    & $mamba create --no-rc --root-prefix $cache --prefix $stage --file $stageLock --yes
    if ($LASTEXITCODE -ne 0) { throw 'Could not install the locked Code_Aster runtime.' }
    robocopy $stage $runtime /E /XJ /XD __pycache__ /XF '*.pyc' '*.pyo' /NFL /NDL /NJH /NJS /NP
    if ($LASTEXITCODE -ge 8) { throw 'Could not copy the locked Code_Aster runtime.' }
}

$packageMetadata = Join-Path $runtime 'conda-meta'
if (Test-Path -LiteralPath $packageMetadata) {
    $packages = @(Get-Content -LiteralPath $lock | Where-Object { $_ -like 'https://*' } | Sort-Object)
    $installed = @(Get-ChildItem -LiteralPath $packageMetadata -Filter '*.json' | ForEach-Object {
        $record = Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json
        "$($record.url)#$($record.sha256)"
    } | Sort-Object)
    if (Compare-Object -ReferenceObject $packages -DifferenceObject $installed) { throw 'The installed Code_Aster packages differ from the lock file.' }
}
foreach ($file in @('Library/bin/aster.dll', 'Library/lib/elem.1', 'Lib/site-packages/run_aster/run_aster_main.py')) {
    if (-not (Test-Path -LiteralPath (Join-Path $runtime $file))) { throw "Missing Code_Aster runtime file: $file" }
}
$config = Join-Path $runtime 'Lib/site-packages/code_aster/Utilities/aster_config.py'
$content = Get-Content -LiteralPath $config -Raw
if ($content -notmatch 'from sys import prefix') {
    $configPaths = @{
        ASTER_BINDIR = "'Library', 'bin'"
        ASTER_LIBDIR = "'Library', 'lib'"
        ASTER_DATADIR = "'Library', 'share', 'aster'"
        ASTER_SITEPACKAGESDIR = "'Lib', 'site-packages'"
        PYTHONDIR = "'Lib', 'site-packages'"
        PYTHONARCHDIR = "'Lib', 'site-packages'"
    }
    foreach ($key in $configPaths.Keys) {
        $content = $content -replace "(?m)^   $key=r`"[^`"]*`",", "   $key=join(prefix, $($configPaths[$key])),"
    }
    $content = $content.Replace('config = dict(', "from os.path import join`nfrom sys import prefix`n`nconfig = dict(")
    [IO.File]::WriteAllText($config, $content)
}
Write-Output 'Code_Aster 18.1.11 project runtime verified.'
