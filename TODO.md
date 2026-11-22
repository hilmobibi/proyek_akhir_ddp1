## Fitur Utama (GoFood Kancil — Queue Kantin Online):

### A. MVP — Role Pembeli (Mahasiswa)
- [x] **Autentikasi Sederhana & Hook SSO UI:** Form Login Mahasiswa (Nama & NPM + Demo Login) serta placeholder `st.query_params` (`?ticket=`) untuk integrasi SSO UI.
- [x] **Etalase Kantin (Home):** Tampilan 2 tahap berbasis Grid — **Grid Pilihan Kios** (`Buka` / `Tutup`) $\rightarrow$ **Grid Pilihan Menu** (harga, deskripsi, status stok `Tersedia` / `Habis`, serta tombol kembali ke daftar kios) dan penguncian keranjang per 1 kios.
- [x] **Keranjang, QRIS Per Toko, & Checkout:** Tambah/kurangi item, catatan pesanan, pengambilan default di konter kios, tampilan QRIS khusus per kios, dan wajib upload bukti pembayaran sebelum tombol pesan aktif.
- [x] **Live Queue & Tracking Status (2 Tahap):** Halaman lacak pesanan dengan nomor antrean (`#A-001`, dst.), preview bukti bayar, serta 2 status bertahap:
  1. `Sedang Menyiapkan Pesanan` (default)
  2. `Pesanan Sudah Bisa Diambil`
- [ ] **Integrasi Database & Auth Asli:** Sambungkan `db_service.py` dan hook SSO UI di `main.py` ke Supabase.

### B. MVP — Role Penjual (Kios Kantin)
- [x] **Kelola Menu & Status Toko:** Tambah/edit/hapus menu, tombol cepat ubah status stok (`Tersedia` / `Habis`), serta toggle cepat status toko (`Buka` / `Tutup`).
- [x] **Dashboard Pesanan Masuk:** Melihat daftar antrean pesanan masuk secara berurutan (FIFO) beserta catatan pembeli, ringkasan pendapatan, dan verifikasi bukti pembayaran QRIS.
- [x] **Update Status Pesanan:** Tombol aksi (`Sedang Menyiapkan Pesanan` → `Pesanan Sudah Bisa Diambil`) yang langsung memperbarui halaman Pembeli.
