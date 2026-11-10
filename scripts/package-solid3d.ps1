param(
    [string]$BrowserSource = '',
    [string]$OutputRoot = '',
    [string]$LauncherSource = '',
    [string]$Version = ''
)
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$outputDefault = Join-Path (Split-Path $root -Parent) 'output'
if (-not $BrowserSource) { $BrowserSource = Join-Path $outputDefault 'browser-download/chromium-1234/chrome-win64' }
if (-not $OutputRoot) { $OutputRoot = $outputDefault }
if (-not $LauncherSource) { $LauncherSource = Join-Path $root 'TENSORA.exe' }
$browser = [IO.Path]::GetFullPath($BrowserSource)
if (-not (Test-Path -LiteralPath (Join-Path $browser 'chrome.exe'))) { throw 'Missing portable Chromium runtime.' }
if (-not (Test-Path -LiteralPath $LauncherSource)) { throw 'Build windows-launcher first.' }
$output = [IO.Path]::GetFullPath($OutputRoot)
New-Item -ItemType Directory -Force -Path $output | Out-Null
if ($Version -and $Version -notmatch '^v\d+\.\d+\.\d+$') { throw 'Use a version such as v1.2.1.' }
$name = if ($Version) { "TENSORA-$Version-windows-x64" } else { 'TENSORA-3D-portable-' + (Get-Date -Format 'yyyyMMdd-HHmmss') }
$dest = Join-Path $output $name
$zip = Join-Path $output ($name + '.zip')
if ((Test-Path -LiteralPath $dest) -or (Test-Path -LiteralPath $zip)) { throw "Release output already exists: $name" }
New-Item -ItemType Directory -Path $dest | Out-Null
function Copy-Tree([string]$source, [string]$relative) {
    $target = Join-Path $dest $relative
    New-Item -ItemType Directory -Force -Path (Split-Path $target -Parent) | Out-Null
    Copy-Item -LiteralPath (Join-Path $root $source) -Destination $target -Recurse -Force
}
Get-ChildItem -LiteralPath $root -File -Filter '*.js' | ForEach-Object { Copy-Tree $_.Name $_.Name }
foreach ($file in @('index.html','styles.css','README.md','LICENSE','CHANGELOG.md','start.bat')) { Copy-Tree $file $file }
foreach ($dir in @('assets','materials','explosives','gases','src','docs')) { Copy-Tree $dir $dir }
Copy-Tree 'calculation-data/README.md' 'calculation-data/README.md'
foreach ($script in @('phast-bridge.py','setup-fracture.ps1')) { Copy-Tree "scripts/$script" "scripts/$script" }
Copy-Tree 'TensoraCore/x64/Release' 'TensoraCore/x64/Release'
Copy-Tree 'third_party/calculix' 'third_party/calculix'
Copy-Tree 'third_party/phast' 'third_party/phast'
Copy-Tree 'third_party/cbgeo-materials' 'third_party/cbgeo-materials'
Copy-Tree 'third_party/clawpack-riemann' 'third_party/clawpack-riemann'
Copy-Tree 'third_party/openradioss-jh2' 'third_party/openradioss-jh2'
Copy-Tree 'third_party/singularity-eos-runtime' 'third_party/singularity-eos-runtime'
Copy-Tree 'third_party/SOURCES.json' 'third_party/SOURCES.json'
Copy-Tree 'third_party/gmsh/manifest.json' 'third_party/gmsh/manifest.json'
Copy-Tree 'third_party/gmsh/gmsh-4.15.0-source.tgz' 'third_party/gmsh/gmsh-4.15.0-source.tgz'
Copy-Tree 'third_party/chromium' 'third_party/chromium'
$gmshDir = Join-Path $dest 'third_party/gmsh/gmsh-4.15.0-Windows64'
New-Item -ItemType Directory -Force -Path $gmshDir | Out-Null
Get-ChildItem -LiteralPath (Join-Path $root 'third_party/gmsh/gmsh-4.15.0-Windows64') -File | Copy-Item -Destination $gmshDir
Copy-Tree 'node-v24.21.0-win-x64/node.exe' 'node-v24.21.0-win-x64/node.exe'
Copy-Tree 'node-v24.21.0-win-x64/LICENSE' 'node-v24.21.0-win-x64/LICENSE'
Copy-Item -LiteralPath $LauncherSource -Destination (Join-Path $dest 'TENSORA.exe')
New-Item -ItemType Directory -Force -Path (Join-Path $dest 'browser') | Out-Null
Copy-Item -LiteralPath $browser -Destination (Join-Path $dest 'browser/chrome-win64') -Recurse
Add-Type -AssemblyName System.IO.Compression.FileSystem
[IO.Compression.ZipFile]::CreateFromDirectory($dest,$zip,[IO.Compression.CompressionLevel]::Optimal,$true)
$hash = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath ($zip+'.sha256') -Value "$hash  $name.zip" -Encoding ascii
Write-Output "Portable directory: $dest"
Write-Output "Portable ZIP: $zip"
