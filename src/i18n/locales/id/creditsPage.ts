import type { Messages } from "../../types";

/** Indonesian strings for the "creditsPage" namespace. */
export const creditsPage: Messages["creditsPage"] = {
  back: "Pengaturan",
  title: "Kredit open source",
  subtitle: "Cuplik dibangun di atas library dan tool open source ini. Terima kasih untuk semua yang membuatnya.",
  version: "Versi {{version}}. Dibuat dengan React 19, Tauri 2, dan Python 3.13.",
  listTitle: "Library dan tool",
  listBody: "Teks lisensi ditampilkan dalam bahasa Inggris, sesuai yang diterbitkan tiap proyek.",
  source: "Sumber",
  sourceLabel: "Buka kode sumber {{name}}",
  showLicense: "Lihat lisensi",
  hideLicense: "Sembunyikan lisensi",
  ffmpegNote: "FFmpeg berjalan sebagai program terpisah. Kode sumbernya ada di <src>ffmpeg.org</src>, dan build yang dibundel berasal dari <build>gyan.dev</build>.",
  libs: {
    ffmpeg: "Memproses, meng-encode, dan mengonversi audio dan video",
    ytdlp: "Mengunduh video dan subtitle YouTube",
    mediapipe: "Mendeteksi dan melacak wajah untuk klip potret",
    deno: "Runtime JavaScript untuk komponen remote yt-dlp",
    opencv: "Computer vision dan pengolahan gambar",
    pillow: "Menggambar teks hook di klip",
    tauri: "Framework aplikasi desktop",
    react: "Library antarmuka",
    radix: "Menu, popover, slider, dan pilihan yang aksesibel",
    i18next: "Terjemahan antarmuka bahasa Indonesia dan Inggris",
    jakarta: "Huruf yang dipakai di antarmuka",
    openai: "Klien AI untuk chat completion dan daftar model",
    antislop: "Aturan desain dan penulisan yang diikuti saat membangun antarmuka",
  },
};
