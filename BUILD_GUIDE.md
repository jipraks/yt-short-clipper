# Build Guide — YT Short Clipper v2

Panduan lengkap build aplikasi dari source sampai jadi 2 file zip yang diupload
ke GitHub Releases.

## TL;DR

Di mesin yang sudah pernah build (ffmpeg & deno sudah ada), cukup:

```powershell
# 1. Naikkan versi (lihat bagian "Naikkan Versi")
# 2. Build + bikin zip:
npm run release
```

Hasil: 2 zip di `src-tauri/target/release/bundle/`. Upload keduanya ke GitHub.

---

## Hasil Akhir

`npm run release` menghasilkan 2 zip:

| Zip | Isi | Untuk siapa | Ukuran |
|-----|-----|-------------|--------|
| `YTShortClipperV2_<versi>_x64_portable.zip` | App + sidecar + ffmpeg + deno + model + WebView2 + run.bat + PANDUAN | **User baru** (pertama kali pakai) | ~212 MB |
| `YTShortClipperV2_<versi>_x64_update.zip` | App + sidecar + run.bat + PANDUAN saja | **User lama** (sudah punya versi penuh) | ~97 MB |

**Kenapa dua zip?** Yang berubah antar versi cuma `yt-short-clipper-v2.exe`
(Rust + frontend) dan `ytclip-sidecar-*.exe` (Python). File besar ffmpeg (~195 MB),
deno (~97 MB), dan model bersifat statis. Jadi user lama cukup download
`update.zip` lalu **extract menimpa** folder lamanya — 2 exe tertimpa, sisanya
tetap. Hemat ~290 MB tiap update.

---

## Prasyarat (Sekali Saja)

| Tool | Keterangan |
|------|-----------|
| **Node.js** v18+ & npm | Build frontend + Tauri CLI |
| **Rust** + MSVC toolchain | `rustup`, target `x86_64-pc-windows-msvc` |
| **Python 3.13** | + dependency: `py -m pip install -r requirements.txt pyinstaller` |
| **Internet** | Untuk `npm run deps` (download ffmpeg/deno) & WebView2 bootstrapper |

Setelah clone repo:

```powershell
npm install        # dependency node + Tauri CLI
npm run deps       # download ffmpeg + deno ke src-tauri/binaries (sekali saja)
```

> `npm run deps` idempotent — kalau ffmpeg/deno sudah ada, di-skip. Pakai
> `npm run deps -- -Force` untuk download ulang.

---

## Naikkan Versi (Setiap Rilis Baru)

Ubah versi di **4 file** supaya konsisten:

| File | Field | Format | Contoh |
|------|-------|--------|--------|
| `src/config/version.ts` | `APP_VERSION` | pakai `-beta` | `2.0.1-beta` |
| `package.json` | `version` | pakai `-beta` | `2.0.1-beta` |
| `src-tauri/tauri.conf.json` | `version` | **numerik murni** | `2.0.1` |
| `src-tauri/Cargo.toml` | `version` | **numerik murni** | `2.0.1` |

> **Kenapa beda format?** Installer MSI (Windows) tidak menerima tag pre-release,
> jadi `tauri.conf.json` & `Cargo.toml` harus numerik (`2.0.1`). Label `-beta`
> yang dilihat user di footer & dipakai untuk cek-update berasal dari
> `src/config/version.ts`. Nama zip mengikuti `package.json` (`2.0.1-beta`).

---

## Cara 1 — Build Penuh (Direkomendasikan untuk Rilis)

```powershell
npm run release
```

Menjalankan 4 langkah berurutan:

| # | Langkah | Perintah internal | Output |
|---|---------|-------------------|--------|
| 1 | Compile Python core | `build:sidecar` (PyInstaller) | `src-tauri/binaries/ytclip-sidecar-*.exe` |
| 2 | Build frontend | `build` (tsc + vite) | `dist/` |
| 3 | Compile app | `tauri build` | `src-tauri/target/release/yt-short-clipper-v2.exe` + installer |
| 4 | Rakit zip | `package` | 2 zip di `src-tauri/target/release/bundle/` |

Durasi: beberapa menit (paling lama langkah 1 PyInstaller & langkah 3 compile Rust).

---

## Cara 2 — Build Manual (Hemat Waktu, Saat Sebagian Berubah)

Tidak semua langkah perlu diulang tiap kali. Jalankan **hanya yang berubah**,
lalu tutup dengan `npm run package`:

```powershell
# Kode Python berubah (yt_short_clipper_core/)
npm run build:sidecar

# Kode frontend berubah (src/)
npm run build

# Kode Rust berubah (src-tauri/)
npm run tauri build

# Selalu terakhir: rakit zip
npm run package
```

> ⚠️ **`npm run tauri build` TIDAK otomatis build frontend.** Kalau ada perubahan
> di `src/`, jalankan `npm run build` dulu — kalau tidak, exe akan memakai `dist/`
> yang lama (perubahan frontend tidak masuk).

### Opsi `npm run package`

```powershell
# Override label versi (default: dari package.json)
npm run package -- -Version 2.0.1-beta

# Paksa download ulang WebView2 bootstrapper
npm run package -- -Force
```

---

## Referensi Semua Perintah npm

| Perintah | Fungsi | Kapan dipakai |
|----------|--------|---------------|
| `npm install` | Install dependency node | Clone fresh / `node_modules` hilang |
| `npm run deps` | Download ffmpeg + deno | Sekali saja / saat deps hilang |
| `npm run build:sidecar` | Compile Python → exe | Kode `yt_short_clipper_core/` berubah |
| `npm run build` | Build frontend → `dist/` | Kode `src/` berubah |
| `npm run tauri build` | Compile Rust + bundle | Kode `src-tauri/` berubah |
| `npm run package` | Rakit folder portable + 2 zip | Tiap mau bikin zip rilis |
| `npm run release` | 4 langkah sekaligus (sidecar→build→tauri→package) | **Rilis resmi** |
| `npm run tauri dev` | Jalankan mode dev (hot-reload frontend) | Development |

---

## Catatan Teknis

- **Sidecar saat dev:** aplikasi selalu memakai binary
  `src-tauri/binaries/ytclip-sidecar-*.exe` kalau ada — termasuk saat
  `npm run tauri dev`. Jadi perubahan file `.py` baru terasa **setelah**
  `npm run build:sidecar` (restart `tauri dev` saja tidak cukup). Untuk iterasi
  cepat tanpa rebuild, hapus binary itu agar Rust fallback ke
  `py -m yt_short_clipper_core.sidecar` (butuh Python env lengkap terinstall).
- **WebView2:** zip menyertakan `MicrosoftEdgeWebview2Setup.exe` (~2 MB).
  `run.bat` otomatis meng-install runtime saat pertama dijalankan kalau belum ada.
- **Cache build:** WebView2 bootstrapper di-cache di
  `build/MicrosoftEdgeWebview2Setup.exe`; staging portable di
  `build/portable-stage/` (dibersihkan tiap `npm run package`).

---

## Checklist Rilis

- [ ] Naikkan versi di 4 file (lihat tabel "Naikkan Versi")
- [ ] `npm run release`
- [ ] Cek nama zip di `src-tauri/target/release/bundle/` sudah sesuai versi
- [ ] Tes `portable.zip` di folder/PC bersih: extract → `run.bat` → cek footer versi
- [ ] Tes `update.zip`: extract **menimpa** instalasi lama → `run.bat` → cek versi terupdate
- [ ] Upload **kedua** zip ke GitHub Release dengan tag (mis. `v2.0.1-beta`)
- [ ] Update endpoint cek-update (`api.ytclip.org/.../latest-version`) ke versi baru
      supaya user lama dapat notifikasi update di aplikasi
