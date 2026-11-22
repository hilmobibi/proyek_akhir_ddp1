## Fitur Utama (Quentin — Queue Kantin Online):

### A. MVP — Role Pembeli (Mahasiswa)
- [x] **Autentikasi Sederhana & Hook SSO UI:** Form Login Mahasiswa (Nama & NPM + Demo Login) serta placeholder `st.query_params` (`?ticket=`) untuk integrasi SSO UI.
- [x] **Etalase Kantin (Home):** Daftar kios kantin (`Buka` / `Tutup`), daftar menu dengan harga, deskripsi, dan status stok (`Tersedia` / `Habis`), serta penguncian keranjang per 1 kios.
- [x] **Keranjang, QRIS Per Toko, & Checkout:** Tambah/kurangi item, catatan pesanan, pengambilan default di konter kios, tampilan QRIS khusus per kios, dan wajib upload bukti pembayaran sebelum tombol pesan aktif.
- [x] **Live Queue & Tracking Status (2 Tahap):** Halaman lacak pesanan dengan nomor antrean (`#A-001`, dst.), preview bukti bayar, serta 2 status bertahap:
  1. `Sedang Menyiapkan Pesanan` (default)
  2. `Pesanan Sudah Bisa Diambil`
- [x] **Panel Simulasi Penjual (Sidebar):** Untuk mengetes perubahan status Live Queue dan mengecek bukti bayar QRIS dari sisi kios.
- [ ] **Integrasi Database & Auth Asli:** Sambungkan `db_service.py` dan hook SSO UI di `main.py` ke Supabase.

### B. MVP — Role Penjual (Kios Kantin)
- [ ] **Kelola Menu:** Tambah/edit/hapus menu dan tombol cepat untuk ubah status stok (`Tersedia` / `Habis`) serta status toko (`Buka` / `Tutup`).
- [ ] **Dashboard Pesanan Masuk:** Melihat daftar antrean pesanan yang masuk secara berurutan beserta catatan pembeli dan verifikasi bukti pembayaran QRIS.
- [ ] **Update Status Pesanan:** Tombol aksi (`Sedang Menyiapkan Pesanan` → `Pesanan Sudah Bisa Diambil`) yang langsung memperbarui halaman Pembeli.
