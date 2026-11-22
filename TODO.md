## Fitur Utama (GoFood Kancil — Queue Kantin Online):

### A. MVP — Role Pembeli (Mahasiswa)
- [x] **Autentikasi Sederhana & Hook SSO UI:** Form Login Mahasiswa (Nama & NPM + Demo Login) serta placeholder `st.query_params` (`?ticket=`) untuk integrasi SSO UI.
- [x] **Etalase Kantin (Home):** Tampilan 2 tahap berbasis Grid — **Grid Pilihan Kios** (`Buka` / `Tutup`) $\rightarrow$ **Grid Pilihan Menu** (harga, deskripsi, status stok `Tersedia` / `Habis`, serta tombol kembali ke daftar kios) dan penguncian keranjang per 1 kios.
- [x] **Keranjang, QRIS Per Toko, & Checkout:** Tambah/kurangi item, catatan pesanan, pengambilan default di konter kios, tampilan QRIS khusus per kios, dan wajib upload bukti pembayaran sebelum tombol pesan aktif.
- [x] **Live Queue & Tracking Status (3 Level Progress):** Halaman lacak pesanan dengan nomor antrean (`#A-001`, dst.), preview bukti bayar, serta alur status:
  1. `0%` — `Menunggu Konfirmasi Pembayaran` (default setelah checkout; atau `Pembayaran Ditolak` beserta alasan jika ditolak)
  2. `50%` — `Sedang Menyiapkan Pesanan` (setelah bukti pembayaran dikonfirmasi penjual)
  3. `100%` — `Pesanan Sudah Bisa Diambil`
- [ ] **Integrasi Database & Auth Asli:** Sambungkan `db_service.py` dan hook SSO UI di `main.py` ke Supabase.

### B. MVP — Role Penjual (Kios Kantin)
- [x] **Kelola Menu & Status Toko:** Tambah/edit/hapus menu, tombol cepat ubah status stok (`Tersedia` / `Habis`), serta toggle cepat status toko (`Buka` / `Tutup`).
- [x] **Dashboard Pesanan Masuk & Verifikasi Pembayaran:** Melihat antrean pesanan masuk secara berurutan (FIFO) beserta catatan pembeli, ringkasan pendapatan terkonfirmasi, dan verifikasi bukti pembayaran QRIS (Konfirmasi / Tolak).
- [x] **Update Status dengan Konfirmasi Ganda (Double Confirm):** Konfirmasi pembayaran (`0% → 50%`), penolakan pembayaran, dan penandaan pesanan siap diambil (`50% → 100%`) dilindungi konfirmasi ganda 2 langkah.
