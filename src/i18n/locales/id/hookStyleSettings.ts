import type { Messages } from "../../types";

/** Indonesian strings for the "hookStyleSettings" namespace. */
export const hookStyleSettings: Messages["hookStyleSettings"] = {
  back: "Pengaturan",
  title: "Gaya hook",
  subtitle: "Tampilan teks hook di detik-detik awal setiap klip.",
  preview: {
    label: "Pratinjau hook di klip 9:16",
    sample: "Kalimat pembuka di detik awal",
    hint: "Geser kotak di pratinjau untuk memindahkannya.",
  },
  text: {
    title: "Teks",
    body: "Font, ukuran, dan warna kata-kata hook.",
    font: "Font",
    fontLoading: "Memuat font…",
    fontSearch: "Cari font",
    fontEmpty: "Tidak ada font yang cocok.",
    fontsFailed: "Daftar font gagal dimuat. Font yang tersimpan tetap dipakai.",
    size: "Ukuran",
    sizeValue: "{{value}}% lebar",
    color: "Warna teks",
  },
  box: {
    title: "Kotak",
    body: "Blok di belakang tiap baris hook.",
    background: "Warna kotak",
    radius: "Sudut membulat",
    radiusValue: "{{value}} px",
    radiusSharp: "Siku",
  },
  placement: {
    title: "Posisi",
    body: "Letak hook dan berapa lama tampil.",
    x: "Kiri ke kanan",
    y: "Atas ke bawah",
    percent: "{{value}}%",
    duration: "Durasi",
    durationValue_one: "{{value}} detik",
    durationValue_other: "{{value}} detik",
    durationBody: "Dihitung dari awal klip.",
  },
  color: {
    pick: "Pilih {{field}}",
    hex: "{{field}}, kode hex",
  },
  reset: "Kembalikan ke awal",
  save: "Simpan gaya hook",
  saving: "Menyimpan…",
  saved: "Gaya hook tersimpan.",
  saveFailed: "Gaya hook gagal disimpan. Coba lagi.",
};
