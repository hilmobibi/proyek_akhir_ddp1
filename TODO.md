## Fitur Utama (Pesan Kancil):

### A. Role Pembeli (Mahasiswa)
- [x] **Login SSO UI (CAS 2.0):** Autentikasi resmi `sso.ui.ac.id/cas2` (`serviceValidate` XML) dengan sinkronisasi otomatis profil mahasiswa ke koleksi `users`.
- [x] **Etalase Kantin (Home):** Tampilan 2 tahap berbasis Grid — **Grid Pilihan Kios berfoto** (`BUKA` / `TUTUP`, pencarian & filter) $\rightarrow$ **Grid Pilihan Menu berfoto** dengan *stepper* jumlah langsung di kartu menu.
- [x] **Keranjang, QRIS Asli Per Toko, & Checkout:** 1 kios per checkout, catatan pesanan, pengambilan di konter kios, tampilan QRIS asli milik kios, dan wajib unggah bukti pembayaran (terkompresi otomatis via `Pillow`).
- [x] **Live Queue & Tracking Status:** Nomor antrean harian anti-bentrok (`#A-001`) dengan teks status deskriptif berwarna dan persentase:
  1. `0% · Pembayaran sedang dikonfirmasi` (Amber) atau `Pembayaran ditolak` (Merah)
  2. `50% · Pesanan sedang disiapkan` (Biru)
  3. `100% · Pesanan sudah bisa diambil` (Hijau)
- [x] **Database Firebase Cloud Firestore (Dual-Mode):** Mendukung `serviceAccountKey.json` & `st.secrets["firebase"]`, *auto-seeding*, transaksi antrean harian, dan *short-cache*.

### B. Role Penjual (Kios Kantin)
- [x] **Daftar & Masuk Kios:** Registrasi kios baru (beserta foto kios & QRIS asli opsional) dan login **Nama Kios + Password** ter-hash (PBKDF2-SHA256).
- [x] **Kelola Menu, Foto Kios, & QRIS Asli:** Tambah/edit/hapus menu berfoto, ubah stok cepat (`Tersedia` / `Habis`), buka/tutup kios, serta unggah Foto Kios dan QRIS Asli di tab `Profil Kios`.
- [x] **Dashboard Pesanan Masuk (FIFO):** Navigasi 4 status (`Menunggu Konfirmasi`, `Sedang Disiapkan`, `Sudah Bisa Diambil`, `Ditolak`), verifikasi bukti pembayaran QRIS, dan konfirmasi ganda (*double confirm*).
