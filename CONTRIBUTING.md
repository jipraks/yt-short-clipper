# Contributing to YT-Short-Clipper

Terima kasih sudah tertarik untuk berkontribusi! 🎉

Dokumen ini berisi panduan lengkap bagaimana cara berkontribusi ke project ini, baik untuk pemula maupun yang sudah berpengalaman.

## 📋 Daftar Isi

- [Cara Kerja Open Source](#cara-kerja-open-source)
- [Persiapan Awal](#persiapan-awal)
- [Workflow Kontribusi](#workflow-kontribusi)
- [Jenis Kontribusi](#jenis-kontribusi)
- [Code Style Guide](#code-style-guide)
- [Commit Message Convention](#commit-message-convention)
- [Pull Request Process](#pull-request-process)
- [Review Process](#review-process)

---

## 🌟 Cara Kerja Open Source

Sebelum mulai, pahami dulu konsep dasar open source di GitHub:

### Istilah Penting

| Istilah | Penjelasan |
|---------|------------|
| **Repository (Repo)** | Folder project yang disimpan di GitHub |
| **Fork** | Salinan repo ke akun GitHub kamu sendiri |
| **Clone** | Download repo ke komputer lokal |
| **Branch** | "Cabang" terpisah untuk mengerjakan fitur tanpa mengganggu kode utama |
| **Commit** | Menyimpan perubahan dengan pesan deskriptif |
| **Push** | Upload perubahan dari lokal ke GitHub |
| **Pull Request (PR)** | Permintaan untuk menggabungkan perubahan kamu ke repo utama |
| **Merge** | Menggabungkan perubahan dari PR ke kode utama |
| **Issue** | Laporan bug atau request fitur |

### Alur Kontribusi (Simplified)

```
1. Fork repo ──▶ 2. Clone ke lokal ──▶ 3. Buat branch baru
                                              │
                                              ▼
6. Buat Pull Request ◀── 5. Push ke GitHub ◀── 4. Edit & Commit
                                              
7. Review & Diskusi ──▶ 8. Merge! 🎉
```

---

## 🛠️ Persiapan Awal

### 1. Install Git

**Windows:**
```powershell
# Menggunakan winget
winget install Git.Git

# Atau download dari https://git-scm.com/download/win
```

**macOS:**
```bash
brew install git
```

**Linux:**
```bash
sudo apt install git
```

### 2. Konfigurasi Git

```bash
# Set nama dan email (akan muncul di commit)
git config --global user.name "Nama Kamu"
git config --global user.email "email@example.com"

# Verifikasi
git config --list
```

### 3. Buat Akun GitHub

1. Buka [github.com](https://github.com)
2. Klik "Sign up"
3. Ikuti proses registrasi

### 4. Setup SSH Key (Recommended)

SSH key memungkinkan push/pull tanpa input password berulang.

```bash
# Generate SSH key
ssh-keygen -t ed25519 -C "email@example.com"

# Tekan Enter untuk semua prompt (gunakan default)

# Copy SSH key
# Windows:
type %USERPROFILE%\.ssh\id_ed25519.pub | clip

# macOS:
pbcopy < ~/.ssh/id_ed25519.pub

# Linux:
cat ~/.ssh/id_ed25519.pub
```

Lalu tambahkan ke GitHub:
1. Buka GitHub → Settings → SSH and GPG keys
2. Klik "New SSH key"
3. Paste key dan save

---

## 🔄 Workflow Kontribusi

### Step 1: Fork Repository

1. Buka halaman repo: `https://github.com/OWNER/yt-short-clipper`
2. Klik tombol **"Fork"** di kanan atas
3. Pilih akun kamu sebagai destinasi
4. Tunggu proses fork selesai

Sekarang kamu punya salinan repo di `https://github.com/USERNAME-KAMU/yt-short-clipper`

### Step 2: Clone ke Komputer Lokal

```bash
# Clone repo fork kamu (bukan repo original!)
git clone https://github.com/USERNAME-KAMU/yt-short-clipper.git

# Masuk ke folder project
cd yt-short-clipper

# Tambahkan remote "upstream" (repo original)
git remote add upstream https://github.com/OWNER/yt-short-clipper.git

# Verifikasi remote
git remote -v
# Output:
# origin    https://github.com/USERNAME-KAMU/yt-short-clipper.git (fetch)
# origin    https://github.com/USERNAME-KAMU/yt-short-clipper.git (push)
# upstream  https://github.com/OWNER/yt-short-clipper.git (fetch)
# upstream  https://github.com/OWNER/yt-short-clipper.git (push)
```

### Step 3: Sync dengan Upstream (Penting!)

Sebelum mulai kerja, pastikan kode kamu up-to-date:

```bash
# Ambil update terbaru dari repo original
git fetch upstream

# Pindah ke branch main
git checkout main

# Merge update ke lokal
git merge upstream/main

# Push ke fork kamu
git push origin main
```

### Step 4: Buat Branch Baru

**JANGAN langsung edit di branch `main`!** Selalu buat branch baru.

```bash
# Format: tipe/deskripsi-singkat
git checkout -b feature/auto-translate-caption
# atau
git checkout -b fix/face-detection-error
# atau
git checkout -b docs/update-readme
```

### Step 5: Lakukan Perubahan

Edit file sesuai kebutuhan menggunakan editor favorit kamu.

```bash
# Cek status perubahan
git status

# Lihat detail perubahan
git diff
```

### Step 6: Commit Perubahan

```bash
# Tambahkan file yang diubah ke staging
git add nama_file.py
# atau tambahkan semua file
git add .

# Commit dengan pesan deskriptif
git commit -m "feat: add auto-translate for captions"
```

### Step 7: Push ke GitHub

```bash
# Push branch ke fork kamu
git push origin feature/auto-translate-caption
```

### Step 8: Buat Pull Request

1. Buka repo fork kamu di GitHub
2. Akan muncul banner "Compare & pull request" - klik itu
3. Atau klik tab "Pull requests" → "New pull request"
4. Pastikan:
   - **base repository**: repo original
   - **base**: main
   - **head repository**: fork kamu
   - **compare**: branch kamu
5. Isi judul dan deskripsi PR
6. Klik "Create pull request"

### Step 9: Respond to Review

Maintainer mungkin akan memberikan feedback. Untuk update PR:

```bash
# Lakukan perubahan sesuai feedback
git add .
git commit -m "fix: address review feedback"
git push origin feature/auto-translate-caption
```

PR akan otomatis terupdate.

---

## 📝 Jenis Kontribusi

### 🐛 Melaporkan Bug

1. Buka tab **Issues** di repo
2. Klik **"New issue"**
3. Pilih template "Bug Report"
4. Isi dengan detail:
   - Deskripsi bug
   - Langkah untuk reproduce
   - Expected vs actual behavior
   - Screenshot/log jika ada
   - Environment (OS, Python version, dll)

### 💡 Request Fitur

1. Buka tab **Issues**
2. Klik **"New issue"**
3. Pilih template "Feature Request"
4. Jelaskan:
   - Fitur yang diinginkan
   - Use case / alasan
   - Contoh implementasi (jika ada ide)

### 📖 Improve Documentation

- Fix typo
- Tambah contoh penggunaan
- Terjemahkan ke bahasa lain
- Tambah screenshot/diagram

### 🔧 Code Contribution

- Fix bug
- Implement fitur baru
- Improve performance
- Refactor code
- Add tests

---

## 🎨 Code Style Guide

### Python Style

Ikuti [PEP 8](https://pep8.org/) dengan beberapa tambahan:

```python
# ✅ Good
def process_video(input_path: str, output_path: str = None) -> bool:
    """
    Process video and return success status.
    
    Args:
        input_path: Path to input video file
        output_path: Path to output file (optional)
    
    Returns:
        True if successful, False otherwise
    """
    if output_path is None:
        output_path = generate_output_path(input_path)
    
    # Process video
    result = do_processing(input_path, output_path)
    
    return result.success


# ❌ Bad
def process_video(input_path,output_path=None):
    if output_path==None:
        output_path=generate_output_path(input_path)
    result=do_processing(input_path,output_path)
    return result.success
```

### Naming Convention

```python
# Variables & functions: snake_case
video_path = "path/to/video.mp4"
def process_video():
    pass

# Classes: PascalCase
class SpeakerTracker:
    pass

# Constants: UPPER_SNAKE_CASE
MAX_CLIP_DURATION = 120
DEFAULT_OUTPUT_DIR = "output"
```

### Import Order

```python
# 1. Standard library
import os
import sys
import json

# 2. Third-party packages
import cv2
import numpy as np
from openai import OpenAI

# 3. Local imports
from highlight_finder import find_highlights
from video_clipper import clip_video
```

---

## 📨 Commit Message Convention

Gunakan format [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <description>

[optional body]

[optional footer]
```

### Types

| Type | Penggunaan |
|------|------------|
| `feat` | Fitur baru |
| `fix` | Bug fix |
| `docs` | Perubahan dokumentasi |
| `style` | Formatting, tidak mengubah logic |
| `refactor` | Refactor code tanpa ubah behavior |
| `perf` | Performance improvement |
| `test` | Menambah/memperbaiki test |
| `chore` | Maintenance tasks |

### Contoh

```bash
# Fitur baru
git commit -m "feat: add support for English subtitles"

# Bug fix
git commit -m "fix: resolve face detection crash on low-res videos"

# Dokumentasi
git commit -m "docs: add installation guide for Ubuntu"

# Dengan body untuk penjelasan detail
git commit -m "feat: implement multi-speaker detection

- Add support for detecting up to 4 speakers
- Improve switching algorithm
- Add configuration options for sensitivity

Closes #42"
```

---

## 🔍 Pull Request Process

### PR Title Format

```
<type>: <short description>
```

Contoh:
- `feat: add auto-translate for captions`
- `fix: resolve memory leak in portrait converter`
- `docs: improve installation instructions`

### PR Description Template

```markdown
## Description
Jelaskan perubahan yang kamu buat.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring

## How Has This Been Tested?
Jelaskan bagaimana kamu test perubahan ini.

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated (if needed)
- [ ] No new warnings generated

## Screenshots (if applicable)
Tambahkan screenshot jika ada perubahan UI/output.

## Related Issues
Closes #(issue number)
```

---

## ✅ Review Process

Setelah PR dibuat:

1. **Automated Checks** - CI/CD akan run (jika ada)
2. **Maintainer Review** - Maintainer akan review code
3. **Feedback** - Mungkin ada request perubahan
4. **Approval** - Setelah approved, PR akan di-merge
5. **Celebration** - Kontribusi kamu sudah masuk! 🎉

### Tips untuk Review Cepat

- PR kecil lebih cepat di-review daripada PR besar
- Satu PR = satu fitur/fix
- Tulis deskripsi yang jelas
- Respond feedback dengan cepat

---

## ❓ Butuh Bantuan?

- Buka **Issue** dengan label `question`
- Diskusi di **Discussions** tab (jika enabled)
- Mention maintainer di PR/Issue

---

## 🙏 Code of Conduct

- Be respectful dan inclusive
- Constructive feedback only
- Help others learn
- No harassment atau discrimination

---

Terima kasih sudah berkontribusi! Setiap kontribusi, sekecil apapun, sangat berarti. 💪
