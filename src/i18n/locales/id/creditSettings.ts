import type { Messages } from "../../types";

/** Indonesian strings for the "creditSettings" namespace. */
export const creditSettings: Messages["creditSettings"] = {
  back: "Pengaturan",
  title: "Kredit sumber",
  subtitle: "Satu baris teks untuk menyebut channel aslinya, ditempel di setiap klip.",
  loading: "Memuat pengaturan kredit…",
  enable: {
    title: "Pasang kredit di setiap klip",
    body: "Ini setelan bawaan. Kamu tetap bisa mematikannya untuk satu render di dialog render.",
  },
  preview: {
    label: "Pratinjau",
    aria: "Pratinjau posisi kredit di klip 9:16",
    frame: "Klip 9:16",
    off: "Kredit sedang mati",
    hint: "Geser teksnya untuk memindahkan. Ukurannya sama dengan di klip jadi.",
  },
  text: {
    title: "Teks kredit",
    body: "Tulis persis seperti yang mau ditampilkan. Pakai {channel} supaya nama channel tiap video terisi sendiri.",
    label: "Teks",
    placeholder: "Sumber: YouTube/NamaChannel",
    placeholderWarning: "{channel} otomatis diganti dengan nama channel videonya saat klip dirender.",
  },
  position: {
    title: "Posisi",
    body: "Pilih sudutnya, lalu setel lebih halus pakai slider.",
    presetsAria: "Posisi cepat",
    presets: {
      topLeft: "Kiri atas",
      topCenter: "Tengah atas",
      topRight: "Kanan atas",
      bottomLeft: "Kiri bawah",
      bottomCenter: "Tengah bawah",
      bottomRight: "Kanan bawah",
    },
    x: "Kiri ke kanan",
    y: "Atas ke bawah",
    value: "{{pct}}%",
  },
  look: {
    title: "Tampilan",
    color: "Warna",
    colorPicker: "Pilih warna",
    colorHex: "Kode warna",
    colorInvalid: "Pakai kode warna hex, misalnya #FFFFFF.",
    fontSize: "Ukuran teks",
    fontSizeValue: "{{px}} px",
    opacity: "Opasitas",
  },
  errors: {
    needText: "Tulis teks kreditnya dulu, atau matikan kreditnya.",
    badColor: "Kode warnanya tidak valid. Pakai format seperti #FFFFFF.",
  },
  save: "Simpan",
  saving: "Menyimpan…",
  saved: "Pengaturan kredit disimpan.",
  saveFailed: "Pengaturan kredit gagal disimpan: {{reason}}",
};
