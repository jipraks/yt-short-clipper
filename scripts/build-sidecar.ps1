param(
    [string]$TargetTriple = "x86_64-pc-windows-msvc"
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Spec = Join-Path $Root "build\spec\sidecar.spec"
$BinaryDir = Join-Path $Root "src-tauri\binaries"
$WorkDir = Join-Path $Root "build\sidecar"
$SpecDir = Join-Path $Root "build\spec"
$Name = "ytclip-sidecar-$TargetTriple"

New-Item -ItemType Directory -Path $BinaryDir -Force | Out-Null
New-Item -ItemType Directory -Path $WorkDir -Force | Out-Null
New-Item -ItemType Directory -Path $SpecDir -Force | Out-Null

py -m PyInstaller `
    --clean `
    --noconfirm `
    --distpath $BinaryDir `
    --workpath $WorkDir `
    $Spec

$Exe = Join-Path $BinaryDir "$Name.exe"
if (!(Test-Path -LiteralPath $Exe)) {
    throw "Sidecar binary was not created: $Exe"
}

Write-Output $Exe
