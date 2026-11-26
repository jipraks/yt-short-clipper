import type { Messages } from "../types";

export const id: Messages = {
  common: {
    appName: "Cuplik",
    language: {
      id: "Bahasa Indonesia",
      en: "English",
    },
  },
  languagePicker: {
    optionHint: "Menu dan panduan pakai Bahasa Indonesia.",
    confirm: "Pakai Bahasa Indonesia",
    saving: "Menyimpan…",
    saveFailed: "Bahasa belum tersimpan. Coba lagi.",
  },
  onboardingCookies: {
    title: "Sambungkan YouTube ke Cuplik",
    lead: "Cuplik mengunduh video YouTube pakai akunmu sendiri, lewat file cookies dari Chrome. Cukup dilakukan sekali.",
    privacy: "File ini berisi sesi login YouTube-mu. Cuplik menyimpannya di komputer ini saja dan hanya memakainya untuk mengakses YouTube.",
    stepLabel: "Langkah {{n}}",
    steps: {
      install: {
        title: "Pasang ekstensi Get cookies.txt LOCALLY",
        body: "Buka halamannya di Chrome Web Store, lalu klik Add to Chrome.",
        action: "Buka Chrome Web Store",
        alt: "Halaman Get cookies.txt LOCALLY di Chrome Web Store dengan tombol Add to Chrome",
      },
      allow: {
        title: "Izinkan ekstensinya",
        body: "Chrome akan meminta izin. Klik Add extension.",
        alt: "Dialog Chrome untuk menambahkan Get cookies.txt LOCALLY, dengan tombol Add extension",
      },
      login: {
        title: "Buka YouTube dan pastikan sudah login",
        body: "Buka youtube.com di Chrome. Kalau di kanan atas masih ada tombol Sign in, login dulu.",
        action: "Buka YouTube",
      },
      export: {
        title: "Ekspor cookies",
        body: "Di tab YouTube, klik ikon ekstensi di kanan atas Chrome. Kalau tidak kelihatan, klik ikon puzzle dulu. Pastikan judulnya menyebut youtube.com, lalu klik Export.",
        alt: "Ekstensi terbuka di youtube.com, dengan tombol Export",
      },
      upload: {
        title: "Upload cookies.txt di sini",
        body: "Chrome menyimpan file bernama cookies.txt, biasanya di folder Downloads.",
        alt: "Notifikasi download Chrome yang menampilkan cookies.txt",
      },
    },
    choose: "Pilih cookies.txt",
    chooseAgain: "Pilih file lain",
    checking: "Mengecek file…",
    valid: "YouTube sudah tersambung. Cuplik sekarang bisa mengunduh video.",
    alreadyValid: "YouTube sudah tersambung. Upload file baru hanya kalau download mulai gagal.",
    errors: {
      wrongFormat: "File ini berformat JSON. Di ekstensi, ubah Export Format ke Netscape, lalu ekspor lagi.",
      notYoutube: "File ini tidak berisi cookies YouTube. Ekspor dari tab youtube.com.",
      notSignedIn: "File ini berisi cookies YouTube tapi tanpa sesi login. Login ke YouTube di Chrome, lalu ekspor lagi.",
      readFailed: "File tidak bisa dibaca. Coba pilih lagi.",
      saveFailed: "Cookies tidak bisa disimpan: {{reason}}",
    },
    finish: "Mulai pakai Cuplik",
    finishing: "Menyimpan…",
    finishFailed: "Progres belum tersimpan. Coba lagi.",
    later: "Nanti saja",
    laterHint: "Cuplik belum bisa mengunduh video sebelum YouTube tersambung. Kamu bisa melakukannya nanti dari halaman Create.",
  },
};
