<#
.SYNOPSIS
  Assembles the portable distribution and produces two zips:
    - full   : first-time users (app + sidecar + ffmpeg + deno + model + WebView2)
    - update : existing users (app + sidecar only; no ffmpeg/deno/model)

  Run this AFTER building the artifacts:
    npm run deps           # ffmpeg + deno -> src-tauri/binaries   (only when deps change)
    npm run build:sidecar  # ytclip-sidecar-*.exe                  (when Python changes)
    npm run build          # vite -> dist                          (frontend)
    npm run tauri build    # yt-short-clipper-v2.exe               (Rust + bundle)

  Or just: npm run release  (chains sidecar + frontend + tauri + package)

.PARAMETER Version
  Override the version label used in zip names / PANDUAN.txt.
  Defaults to the "version" field in package.json (e.g. 2.0.1-beta).

.PARAMETER Force
  Re-download the WebView2 bootstrapper even if cached.
#>
param(
    [string]$Version,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")

# --- Resolve version (default: package.json) ---
if (-not $Version) {
    $pkg = Get-Content (Join-Path $Root "package.json") -Raw | ConvertFrom-Json
    $Version = $pkg.version
}
Write-Host "[package] Building portable distribution for version: $Version"

# --- Source artifact paths ---
$Bin         = Join-Path $Root "src-tauri\binaries"
$AppExe      = Join-Path $Root "src-tauri\target\release\yt-short-clipper-v2.exe"
$SidecarName = "ytclip-sidecar-x86_64-pc-windows-msvc.exe"
$Sidecar     = Join-Path $Bin "ytclip-sidecar-x86_64-pc-windows-msvc.exe"
$Ffmpeg      = Join-Path $Bin "ffmpeg\ffmpeg.exe"
$Deno        = Join-Path $Bin "bin\deno.exe"
$Model       = Join-Path $Bin "models\face_landmarker.task"

# --- Verify required artifacts exist ---
$required = [ordered]@{
    "app exe   (npm run build + npm run tauri build)" = $AppExe
    "sidecar   (npm run build:sidecar)"               = $Sidecar
    "ffmpeg    (npm run deps)"                         = $Ffmpeg
    "deno      (npm run deps)"                         = $Deno
    "model     (face_landmarker.task)"                = $Model
}
$missing = @()
foreach ($k in $required.Keys) {
    if (-not (Test-Path -LiteralPath $required[$k])) {
        $missing += ("  - {0}  ->  {1}" -f $k, $required[$k])
    }
}
if ($missing.Count -gt 0) {
    throw "Missing build artifacts:`n$($missing -join "`n")`n`nRun the build steps first (see PANDUAN-BUILD.md)."
}

# --- WebView2 evergreen bootstrapper (cached in build/) ---
$WebView2 = Join-Path $Root "build\MicrosoftEdgeWebview2Setup.exe"
if ((-not (Test-Path -LiteralPath $WebView2)) -or $Force) {
    Write-Host "[package] Downloading WebView2 bootstrapper..."
    New-Item -ItemType Directory -Path (Split-Path $WebView2) -Force | Out-Null
    Invoke-WebRequest -Uri "https://go.microsoft.com/fwlink/p/?LinkId=2124703" -OutFile $WebView2
}

# --- Staging dir (clean) ---
$Stage = Join-Path $Root "build\portable-stage"
if (Test-Path -LiteralPath $Stage) { Remove-Item -Recurse -Force $Stage }
New-Item -ItemType Directory -Path $Stage -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $Stage "ffmpeg") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $Stage "bin") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $Stage "models") -Force | Out-Null

# --- Copy the full payload ---
Copy-Item -LiteralPath $AppExe   -Destination (Join-Path $Stage "yt-short-clipper-v2.exe") -Force
Copy-Item -LiteralPath $Sidecar  -Destination (Join-Path $Stage $SidecarName) -Force
Copy-Item -LiteralPath $Ffmpeg   -Destination (Join-Path $Stage "ffmpeg\ffmpeg.exe") -Force
Copy-Item -LiteralPath $Deno     -Destination (Join-Path $Stage "bin\deno.exe") -Force
Copy-Item -LiteralPath $Model    -Destination (Join-Path $Stage "models\face_landmarker.task") -Force
Copy-Item -LiteralPath $WebView2 -Destination (Join-Path $Stage "MicrosoftEdgeWebview2Setup.exe") -Force

# --- run.bat (literal here-string; %errorlevel% must stay verbatim) ---
$runBat = @'
@echo off
reg query "HKLM\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-0C8375ABAB64}" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing WebView2 Runtime, please wait...
    start /wait MicrosoftEdgeWebview2Setup.exe /silent /install
)
start yt-short-clipper-v2.exe
'@
Set-Content -Path (Join-Path $Stage "run.bat") -Value $runBat -Encoding ASCII

# --- PANDUAN.txt (interpolates $Version) ---
$panduan = @"
PANDUAN SINGKAT YT SHORT CLIPPER V2
====================================

1. CARA MENJALANKAN
-------------------
Double-click file "run.bat".
Pada pertama kali menjalankan, Windows mungkin akan menginstall WebView2 Runtime
dan membutuhkan koneksi internet. Tunggu sampai selesai.

Jika muncul error "Could not find the webview2 runtime":
- Pastikan PC terhubung internet saat pertama kali menjalankan run.bat
- Atau install manual dengan double-click "MicrosoftEdgeWebview2Setup.exe",
  lalu jalankan "yt-short-clipper-v2.exe"


2. SETUP COOKIES YOUTUBE
------------------------
Aplikasi ini membutuhkan cookies YouTube untuk mengambil data video.

Cara mendapatkan cookies.txt:
1. Buka YouTube di browser (Chrome/Edge/Firefox) dan pastikan sudah login
2. Install extension "Get cookies.txt LOCALLY" di browser
3. Buka extension tersebut saat berada di youtube.com
4. Klik "Export" atau "Copy" cookies
5. Di aplikasi, klik "Upload YouTube cookies to continue"
6. Pilih file cookies.txt yang sudah dieksport

Tips:
- Jangan logout dari YouTube setelah mengekspor cookies
- Jika sering gagal download (error 403), export ulang cookies yang baru
- Pastikan cookies berisi SID, HSID, SSID, APISID, SAPISID, LOGIN_INFO


3. SETUP AI / OPENAI
--------------------
Aplikasi menggunakan AI untuk mendeteksi bagian menarik dari video.

1. Buka menu Settings -> AI Models
2. Pilih provider AI (OpenAI atau provider kompatibel OpenAI)
3. Masukkan API Key
4. Pilih model yang ingin digunakan (contoh: gpt-4o-mini, gpt-4o)
5. Klik Save

Untuk provider selain OpenAI:
- Masukkan Base URL API provider tersebut
- Pilih/model yang tersedia di provider tersebut


4. TROUBLESHOOTING
------------------
- Error "ffmpeg is not installed": pastikan folder ffmpeg tidak dihapus
dari hasil ekstrak zip.

- Error "cookies validation failed": export ulang cookies.txt dari YouTube.

- Aplikasi lambat saat processing: proses clip membutuhkan waktu tergantung
panjang video, kualitas, dan spesifikasi PC.


5. CATATAN
----------
Aplikasi ini adalah versi portable. Tidak perlu diinstall.
Cukup ekstrak zip dan jalankan run.bat.

Versi: $Version
"@
Set-Content -Path (Join-Path $Stage "PANDUAN.txt") -Value $panduan -Encoding UTF8

# --- Output dir ---
$OutDir = Join-Path $Root "src-tauri\target\release\bundle"
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

$FullZip   = Join-Path $OutDir ("YTShortClipperV2_{0}_x64_portable.zip" -f $Version)
$UpdateZip = Join-Path $OutDir ("YTShortClipperV2_{0}_x64_update.zip"   -f $Version)

# --- Full zip: entire staging folder (preserves ffmpeg/, bin/, models/) ---
if (Test-Path -LiteralPath $FullZip) { Remove-Item -Force $FullZip }
Write-Host "[package] Compressing FULL zip..."
Compress-Archive -Path (Join-Path $Stage "*") -DestinationPath $FullZip -CompressionLevel Optimal

# --- Update zip: only the artifacts that change between releases ---
$UpdateItems = @(
    (Join-Path $Stage "yt-short-clipper-v2.exe"),
    (Join-Path $Stage $SidecarName),
    (Join-Path $Stage "run.bat"),
    (Join-Path $Stage "PANDUAN.txt")
)
if (Test-Path -LiteralPath $UpdateZip) { Remove-Item -Force $UpdateZip }
Write-Host "[package] Compressing UPDATE zip..."
Compress-Archive -Path $UpdateItems -DestinationPath $UpdateZip -CompressionLevel Optimal

# --- Report ---
$fullMb = [math]::Round((Get-Item $FullZip).Length / 1MB, 1)
$updMb  = [math]::Round((Get-Item $UpdateZip).Length / 1MB, 1)
Write-Host ""
Write-Host "[package] Done."
Write-Host ("  FULL   : {0}  ({1} MB)  -> first-time users" -f $FullZip, $fullMb)
Write-Host ("  UPDATE : {0}  ({1} MB)  -> existing users (no ffmpeg/deno/model)" -f $UpdateZip, $updMb)
