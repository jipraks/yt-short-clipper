<#
.SYNOPSIS
  Builds the Microsoft Store package (MSIX) for Cuplik.

  The Store signs MSIX packages itself, so this produces an unsigned .msix to
  upload in Partner Center. Pass -TestCert to also sign a copy with a local
  self-signed certificate, for installing on this machine before uploading.

  Steps:
    1. Frontend with VITE_STORE_BUILD=1 (no self-update prompt; the Store updates it)
    2. Rust release exe (tauri build --no-bundle)
    3. Stage the same layout as the portable zip: exe, sidecar, ffmpeg, deno, model
    4. Fill AppxManifest.xml from store/msix/identity.json and package.json
    5. makeappx pack

  Run `npm run build:sidecar` first whenever the Python code changed.

.PARAMETER Version
  Four-part package version. Defaults to package.json's version with any
  pre-release tag dropped and .0 added (2.0.8-beta -> 2.0.8.0). The Store
  requires the last part to be 0.

.PARAMETER SkipBuild
  Reuse the existing dist/ and release exe; only restage and pack.

.PARAMETER TestCert
  Also produce a copy signed with a self-signed certificate whose subject is
  the manifest Publisher, so it can be installed locally.
#>
param(
    [string]$Version,
    [switch]$SkipBuild,
    [switch]$TestCert
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Store = Join-Path $Root "store\msix"

# --- Identity from Partner Center ---
$identity = Get-Content (Join-Path $Store "identity.json") -Raw | ConvertFrom-Json
if ($identity.identityName -like "FILL_ME*" -or $identity.publisher -like "*FILL-ME*") {
    throw "Fill store/msix/identity.json from Partner Center (Product identity) first."
}

# --- Version ---
if (-not $Version) {
    $pkg = Get-Content (Join-Path $Root "package.json") -Raw | ConvertFrom-Json
    $core = ($pkg.version -split "-")[0]
    $parts = @($core -split "\.")
    while ($parts.Count -lt 3) { $parts += "0" }
    $Version = "{0}.{1}.{2}.0" -f $parts[0], $parts[1], $parts[2]
}
if ($Version -notmatch '^\d+\.\d+\.\d+\.0$') { throw "Version must look like 2.0.8.0 (last part 0), got $Version" }
Write-Host "[msix] Version $Version"

# --- makeappx / signtool from the newest Windows SDK ---
$kits = "${env:ProgramFiles(x86)}\Windows Kits\10\bin"
$sdk = Get-ChildItem $kits -Directory | Where-Object { $_.Name -match '^10\.' } | Sort-Object Name -Descending | Select-Object -First 1
if (-not $sdk) { throw "Windows 10/11 SDK not found under $kits" }
$MakeAppx = Join-Path $sdk.FullName "x64\makeappx.exe"
$SignTool = Join-Path $sdk.FullName "x64\signtool.exe"

# --- Build ---
if (-not $SkipBuild) {
    Push-Location $Root
    try {
        $env:VITE_STORE_BUILD = "1"
        npm run build
        if ($LASTEXITCODE -ne 0) { throw "Frontend build failed" }
        npx tauri build --no-bundle
        if ($LASTEXITCODE -ne 0) { throw "Tauri build failed" }
    } finally {
        Remove-Item Env:\VITE_STORE_BUILD -ErrorAction SilentlyContinue
        Pop-Location
    }
}

# --- Artifacts ---
$Bin = Join-Path $Root "src-tauri\binaries"
$artifacts = [ordered]@{
    "Cuplik.exe"                                 = Join-Path $Root "src-tauri\target\release\yt-short-clipper-v2.exe"
    "ytclip-sidecar-x86_64-pc-windows-msvc.exe" = Join-Path $Bin "ytclip-sidecar-x86_64-pc-windows-msvc.exe"
    "ffmpeg\ffmpeg.exe"                          = Join-Path $Bin "ffmpeg\ffmpeg.exe"
    "bin\deno.exe"                               = Join-Path $Bin "bin\deno.exe"
    "models\face_landmarker.task"                = Join-Path $Bin "models\face_landmarker.task"
}
$missing = $artifacts.GetEnumerator() | Where-Object { -not (Test-Path -LiteralPath $_.Value) }
if ($missing) { throw "Missing build artifacts:`n" + (($missing | ForEach-Object { "  $($_.Value)" }) -join "`n") }

# --- Stage ---
$Stage = Join-Path $Root "build\msix-stage"
if (Test-Path -LiteralPath $Stage) { Remove-Item -Recurse -Force $Stage }
New-Item -ItemType Directory -Path $Stage | Out-Null
foreach ($entry in $artifacts.GetEnumerator()) {
    $dest = Join-Path $Stage $entry.Key
    New-Item -ItemType Directory -Path (Split-Path $dest) -Force | Out-Null
    Copy-Item -LiteralPath $entry.Value -Destination $dest
}
Copy-Item -Recurse (Join-Path $Store "Assets") (Join-Path $Stage "Assets")

# --- Manifest ---
function Escape-Xml([string]$s) { [System.Security.SecurityElement]::Escape($s) }
$manifest = Get-Content (Join-Path $Store "AppxManifest.template.xml") -Raw
$manifest = $manifest.Replace("{{IDENTITY_NAME}}", (Escape-Xml $identity.identityName)).
    Replace("{{PUBLISHER}}", (Escape-Xml $identity.publisher)).
    Replace("{{PUBLISHER_DISPLAY_NAME}}", (Escape-Xml $identity.publisherDisplayName)).
    Replace("{{DISPLAY_NAME}}", (Escape-Xml $identity.displayName)).
    Replace("{{DESCRIPTION}}", (Escape-Xml $identity.description)).
    Replace("{{VERSION}}", $Version)
Set-Content -Path (Join-Path $Stage "AppxManifest.xml") -Value $manifest -Encoding UTF8

# --- Pack ---
$OutDir = Join-Path $Root "build\msix"
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
$Msix = Join-Path $OutDir ("Cuplik_{0}_x64.msix" -f $Version)
if (Test-Path -LiteralPath $Msix) { Remove-Item -Force $Msix }
& $MakeAppx pack /d $Stage /p $Msix /o
if ($LASTEXITCODE -ne 0) { throw "makeappx failed" }
Write-Host "[msix] Store upload: $Msix"

# --- Optional local test copy ---
if ($TestCert) {
    $subject = $identity.publisher
    $cert = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Subject -eq $subject -and $_.HasPrivateKey } | Select-Object -First 1
    if (-not $cert) {
        $cert = New-SelfSignedCertificate -Type Custom -Subject $subject -KeyUsage DigitalSignature `
            -FriendlyName "Cuplik MSIX test" -CertStoreLocation "Cert:\CurrentUser\My" `
            -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}")
    }
    $Test = Join-Path $OutDir ("Cuplik_{0}_x64.test-signed.msix" -f $Version)
    Copy-Item -Force $Msix $Test
    & $SignTool sign /fd SHA256 /sha1 $cert.Thumbprint $Test
    if ($LASTEXITCODE -ne 0) { throw "signtool failed" }
    Write-Host "[msix] Test copy: $Test"
    Write-Host "[msix] To install it, trust the certificate once (admin): put it in Local Machine > Trusted People."
}
