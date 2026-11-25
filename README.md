# Tugas Akhir DDP1 — Pesan Kancil

Aplikasi pemesanan dan antrean kantin fakultas berbasis **Python (Streamlit)** dengan database **Firebase Cloud Firestore** dan autentikasi **SSO UI (CAS 2.0)**.

### Anggota Kelompok
- Azzam
- Hilmo
- Rasya

---

## Latar Belakang Masalah
Jam istirahat makan siang mahasiswa terbatas dan antrean kantin fakultas sering kali sangat padat. **Pesan Kancil** memungkinkan mahasiswa memesan makanan/minuman dari perangkat pribadi, membayar via QRIS masing-masing kios, dan memantau status antrean secara langsung sebelum mengambil pesanan di konter kios.

---

## Fitur Utama

### Pembeli (Mahasiswa)
- **Login SSO UI (`sso.ui.ac.id/cas2`):** Validasi tiket CAS 2.0 XML otomatis dan sinkronisasi profil mahasiswa ke Firestore.
- **Etalase Kantin 2 Tahap:** Pencarian & filter kios buka, Grid Kios berfoto, serta Grid Menu berfoto dengan *stepper* jumlah langsung di kartu menu.
- **Keranjang & Pembayaran QRIS per Kios:** 1 checkout per kios, tampilan QRIS asli masing-masing kios, catatan pesanan, dan unggah bukti pembayaran (otomatis dikompres ringan dengan `Pillow`).
- **Live Queue Deskriptif:** Pelacakan antrean dengan nomor antrean harian (`#A-001`, reset otomatis tiap ganti tanggal) dan status berwarna (`0%` Pembayaran sedang dikonfirmasi $\rightarrow$ `50%` Pesanan sedang disiapkan $\rightarrow$ `100%` Pesanan sudah bisa diambil, atau Pembayaran ditolak).

### Penjual (Pengelola Kios)
- **Daftar & Masuk Kios:** Registrasi kios baru atau masuk menggunakan **Nama Kios + Password** (terenkripsi PBKDF2-SHA256).
- **Dashboard Pesanan Masuk (FIFO):** Navigasi 4 status (`Menunggu Konfirmasi`, `Sedang Disiapkan`, `Sudah Bisa Diambil`, `Ditolak`), verifikasi bukti pembayaran QRIS, ringkasan pendapatan terkonfirmasi, dan **konfirmasi ganda (*double confirm*)** pada setiap perubahan status.
- **Kelola Menu & Profil Kios:** Tambah/edit/hapus menu beserta foto makanan, toggle cepat stok (`Tersedia` / `Habis`), buka/tutup kios, unggah **Foto Kios**, dan unggah **QRIS Asli Kios**.

---

## Struktur Proyek
```text
proyek_akhir_ddp1/
├── main.py                        # Entry point, routing login & layout utama
├── auth_service.py                # Autentikasi CAS 2.0 SSO UI & hashing password PBKDF2
├── db_service.py                  # Dual-mode Firebase Cloud Firestore + transaksi antrean harian
├── ui_theme.py                    # Sistem desain putih-abu minimalis & floating bottom navbar
├── buyer_view.py                  # Antarmuka Pembeli (Etalase, Keranjang QRIS, Antrean)
├── seller_view.py                 # Antarmuka Penjual (Pesanan, Kelola Menu, Profil Kios)
├── .streamlit/config.toml         # Konfigurasi tema terang putih-abu
├── assets/demo/                   # Foto contoh warung & menu Indonesia (+ CREDITS.md)
├── requirements.txt               # Dependensi Python
└── serviceAccountKey.example.json # Contoh struktur kunci Firebase (kunci asli di-gitignore)
```

---

## Cara Menjalankan di Lokal
```powershell
pip install -r requirements.txt
streamlit run main.py
```
*(Jika menggunakan `.venv` di proyek ini: `.\.venv\Scripts\streamlit run main.py`)*

---

## Konfigurasi Firebase & Deployment (Streamlit Community Cloud)

### Menjalankan Lokal dengan Firebase
1. Buat proyek di `https://console.firebase.google.com` dan aktifkan **Build $\rightarrow$ Firestore Database**.
2. Buka **Project settings $\rightarrow$ Service accounts $\rightarrow$ Generate new private key**.
3. Simpan file JSON tersebut di root proyek dengan nama **`serviceAccountKey.json`** *(sudah diabaikan oleh `.gitignore`)*.

### Deploy ke Streamlit Community Cloud
1. Buka `https://share.streamlit.io` dan klik **Create app $\rightarrow$ Deploy a public app from GitHub**.
2. Pilih repository `hilmobibi/proyek_akhir_ddp1`, branch `main`, dan main file path `main.py`.
3. Buka **Advanced settings $\rightarrow$ Secrets** (atau **App settings $\rightarrow$ Secrets** setelah deploy) lalu masukkan konfigurasi TOML berikut:
```toml
APP_SERVICE_URL = "https://nama-app-kamu.streamlit.app/"

[firebase]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

---

## Kredit Aset Foto Demo
Foto warung dan menu bawaan untuk demo berasal dari Wikimedia Commons (CC BY / CC BY-SA / CC0); rincian sumber dan lisensinya tercantum pada [assets/demo/CREDITS.md](assets/demo/CREDITS.md).
