import type { Messages } from "../../types";

/** Indonesian strings for the "replizSettings" namespace. */
export const replizSettings: Messages["replizSettings"] = {
  title: "Repliz",
  subtitle: "Posting klip yang sudah jadi ke YouTube, TikTok, Instagram, dan Facebook langsung dari Cuplik.",
  status: {
    loading: "Membaca key yang tersimpan…",
    checking: "Mengecek koneksi ke Repliz…",
    connected_one: "Tersambung. {{count}} akun sosmed siap dipakai.",
    connected_other: "Tersambung. {{count}} akun sosmed siap dipakai.",
    notConnected: "Belum tersambung. Tempel Access Key dan Secret Key kamu di bawah.",
    rejected: "Repliz menolak key yang tersimpan: {{reason}}",
    rejectedHint: "Salin key baru dari dashboard Repliz, lalu sambungkan lagi.",
    accountOff: "belum terhubung",
  },
  pitch: {
    title: "Kenapa Repliz",
  },
  keys: {
    title: "Key Repliz kamu",
    stored: "Cuplik menyimpan key di penyimpanan kredensial sistem, bukan di file biasa.",
  },
  connected: "Repliz tersambung.",
  dashboard: "Buka dashboard Repliz",
  disconnect: {
    action: "Putuskan Repliz",
    title: "Putuskan Repliz?",
    body: "Cuplik akan menghapus key-nya. Akun dan jadwal posting di Repliz tetap aman. Kalau mau sambung lagi, tempel ulang key-nya.",
    confirm: "Putuskan",
    cancel: "Batal",
    close: "Tutup",
    working: "Memutuskan…",
    done: "Repliz sudah diputus.",
    failed: "Repliz gagal diputus. Coba lagi.",
  },
};
