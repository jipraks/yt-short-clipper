# Cuplik: Microsoft Store listing

Everything Partner Center asks for, ready to paste. Product type: **MSIX or PWA app**
(same as FreeKasir; the Store signs the package). Keep the platform name out of every field.

## Product setup

| Field | Value |
| --- | --- |
| Product name | **Cuplik**, reserved 2026-11-26; submit before 2027-02-26 or the name is released |
| Store ID | 9PHPBBFP7PPH (https://apps.microsoft.com/detail/9PHPBBFP7PPH) |
| Package identity | `PTJipraksDigitalIndonesia.Cuplik`, publisher `CN=71723326-F1AB-4B54-A8DB-6874AED77B43` (in `store/msix/identity.json`) |
| Category | Photo & video |
| Pricing | Free |
| Markets | Indonesia first; add others later if wanted |
| Privacy policy URL | https://cuplik.jipraks.id/privacy-policy |
| Website | https://cuplik.jipraks.id |
| Support contact | (your support email or https://cuplik.jipraks.id) |
| Additional license terms | https://cuplik.jipraks.id/terms-condition |
| Copyright | © 2026 PT Jipraks Digital Indonesia |
| System requirements (minimum) | Windows 10 version 1809 or later, 64-bit, 8 GB RAM, internet connection |
| Package | `build/msix/Cuplik_<version>_x64.msix` from `npm run build:msix` |

### Age rating questionnaire (IARC), suggested answers
- Category: **Productivity / utility style app (not a game)**.
- Violence, sexual content, gambling, drugs: **No**.
- Users can interact or share content: **Yes** (users can post their own clips to their
  social accounts through Repliz). Users cannot chat with each other inside the app.
- Shares user location: **No**.
- Digital purchases: **Yes** (users can top up an AI usage balance through QRIS; this is
  the app's own payment flow, allowed for non-game apps).
- Uncontrolled internet access / web browser: **No**.
- Contains AI-generated content: **Yes** (AI picks highlights and writes titles and hooks).

---

## Bahasa Indonesia (id-ID)

### Deskripsi
Cuplik mengubah video panjang jadi klip pendek vertikal yang siap diposting. Tempel link
video, pilih berapa klip yang kamu mau, dan AI membaca seluruh transkrip untuk menemukan
momen yang paling layak jadi klip. Kamu tinggal cek, rapikan, lalu render.

Cocok untuk clipper, kreator, dan tim konten yang memotong podcast, wawancara, kajian,
atau siaran panjang jadi Shorts, Reels, dan video TikTok setiap hari.

Cara kerjanya
1. Tempel link video dan pilih bahasa subtitle.
2. AI mencari highlight dan memberi skor setiap momen.
3. Atur awal dan akhir klip di editor timeline, lengkap dengan transkripnya.
4. Render jadi video 9:16: wajah pembicara diikuti otomatis, caption kata per kata,
   teks hook di detik awal, logo, dan kredit sumber.
5. Jadwalkan posting ke banyak akun sekaligus lewat Repliz, tanpa keluar dari Cuplik.

Kenapa Cuplik
- Hemat waktu: dari video satu jam ke beberapa klip siap posting dalam hitungan menit.
- Editor yang jelas: setiap highlight bisa ditarik, dipotong, dan dicek transkripnya
  sebelum dirender.
- Klip rapi: framing 9:16 yang mengikuti wajah, atau tetap 16:9 kalau mau diedit sendiri.
- Bahasa Indonesia dan Inggris.
- Saldo AI bawaan dengan top up QRIS, atau pakai API key AI milikmu sendiri.

Catatan
Cuplik butuh koneksi internet. Pastikan kamu punya hak atas video yang kamu potong dan
posting.

### Yang baru di versi ini
- Tampilan baru yang lebih rapi, sepenuhnya dalam Bahasa Indonesia dan Inggris.
- Halaman Klip: semua video jadi dalam satu tempat, terhubung ke proyek asalnya.
- Dialog render dengan contoh hasil, dan halaman render yang menunjukkan progres per klip.
- Jadwal posting Repliz kini menampilkan detail akun dan waktu tayang.

### Fitur produk (maks. 20, masing-masing maks. 200 karakter)
1. AI menemukan momen terbaik dari video panjang dan memberi skor tiap highlight
2. Editor timeline untuk mengatur awal dan akhir klip, lengkap dengan transkrip
3. Framing 9:16 otomatis yang mengikuti wajah pembicara
4. Caption kata per kata yang pas dengan suara
5. Teks hook buatan AI di detik-detik awal klip
6. Logo dan kredit sumber di setiap klip, bisa diatur posisinya
7. Jadwalkan posting ke banyak akun sosmed sekaligus lewat Repliz
8. Judul dan deskripsi posting ditulis AI, tinggal salin
9. Halaman Klip dan Proyek untuk mengatur semua hasil
10. Saldo AI bawaan dengan top up QRIS, atau pakai API key sendiri
11. Render lebih cepat dengan kartu grafis yang didukung
12. Tersedia dalam Bahasa Indonesia dan Inggris

### Deskripsi singkat
Ubah video panjang jadi klip pendek vertikal dengan AI: cari highlight, rapikan di
timeline, render dengan caption dan hook, lalu jadwalkan posting.

### Kata kunci pencarian (maks. 7)
klip video, video pendek, reels, shorts, editor video, ai clipper, podcast clip

---

## English (en-US)

### Description
Cuplik turns long videos into short vertical clips that are ready to post. Paste a video
link, choose how many clips you want, and the AI reads the whole transcript to find the
moments most worth clipping. You review, trim, and render.

Built for clippers, creators, and content teams who cut podcasts, interviews, talks, and
long streams into Shorts, Reels, and TikTok videos every day.

How it works
1. Paste a video link and pick the subtitle language.
2. The AI finds the highlights and scores every moment.
3. Adjust each clip's start and end on a timeline editor, with the transcript beside it.
4. Render to 9:16 video: the speaker's face is followed automatically, with word-by-word
   captions, a hook line in the first seconds, your logo, and a source credit.
5. Schedule posts to many accounts at once through Repliz, without leaving Cuplik.

Why Cuplik
- Saves time: from an hour-long video to several ready-to-post clips in minutes.
- A clear editor: drag, trim, and check the transcript of every highlight before rendering.
- Clean framing: 9:16 that follows faces, or keep 16:9 to edit it yourself.
- Indonesian and English.
- Built-in AI balance topped up with QRIS, or use your own AI API key.

Note
Cuplik needs an internet connection. Make sure you have the rights to the videos you clip
and post.

### What's new in this version
- A cleaner redesign, fully in Indonesian and English.
- A Clips page: every finished video in one place, linked to its project.
- A render dialog with an example of the result, and per-clip render progress.
- Repliz scheduling now shows each account and the posting time.

### Product features (max 20, each max 200 characters)
1. AI finds the best moments in long videos and scores every highlight
2. Timeline editor to set each clip's start and end, with the transcript
3. Automatic 9:16 framing that follows the speaker's face
4. Word-by-word captions timed to the speech
5. AI-written hook text in the first seconds of a clip
6. Your logo and a source credit on every clip, placed where you want
7. Schedule posts to many social accounts at once through Repliz
8. AI-written post titles and descriptions, ready to copy
9. Clips and Projects pages to keep every result organised
10. Built-in AI balance with QRIS top up, or your own API key
11. Faster rendering on supported graphics cards
12. Available in Indonesian and English

### Short description
Turn long videos into short vertical clips with AI: find highlights, trim them on a
timeline, render with captions and hooks, then schedule your posts.

### Search terms (max 7)
video clips, short video, reels, shorts, video editor, ai clipper, podcast clips

---

## Store images

Ready in `store/screenshots/` (kept out of git; they are large). Upload in this order.

| Asset | Size | Files |
| --- | --- | --- |
| Screenshots (Desktop), Indonesian | 3840×2160 PNG | `store/screenshots/id/01-editor.png` … `08-ai.png` |
| Screenshots (Desktop), English | 3840×2160 PNG | `store/screenshots/en/01-editor.png` … `08-ai.png` |
| 1:1 box art | 2160×2160 PNG | `store/screenshots/art/box-1x1.png` |
| 2:3 poster art | 1440×2160 PNG | `store/screenshots/art/poster-2x3.png` |
| 16:9 super hero art | 3840×2160 PNG | `store/screenshots/art/hero-16x9.png` |

Captions on each screenshot (Partner Center has a caption field per image):

| # | Bahasa Indonesia | English |
| --- | --- | --- |
| 1 | AI menemukan momen terbaik | AI finds the best moments |
| 2 | Atur bentuk dan tampilan klip | Choose the shape and the look |
| 3 | Semua klip siap posting | Every clip, ready to post |
| 4 | Jadwalkan ke banyak akun sekaligus | Schedule to many accounts at once |
| 5 | Tahu persis kapan klip tayang | Know exactly when it goes live |
| 6 | Render jalan sendiri, klip demi klip | Rendering runs on its own |
| 7 | Proyek tersusun rapi | Projects stay organised |
| 8 | Saldo AI dengan top up QRIS | An AI balance with QRIS top up |

The footage in the screenshots, the hero art, and the render-dialog samples in `public/`
is Mixkit stock video (Mixkit free license): clips 52190, 44048, 2948 and 52181. The
project titles, channels, transcripts and accounts shown are invented for the demo.
