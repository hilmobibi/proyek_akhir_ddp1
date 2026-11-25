## Fitur Utama (Pesan Kancil):

### A. MVP — Role Pembeli (Mahasiswa)
- [x] **Autentikasi Hybrid (SSO UI CAS 2.0 + Akun NPM/Password):** Tombol login resmi `sso.ui.ac.id/cas2` (`serviceValidate` XML) + registrasi/login akun cadangan NPM & Password ter-hash (PBKDF2-SHA256) di koleksi `users`.
- [x] **Etalase Kantin (Home):** Tampilan 2 tahap berbasis Grid — **Grid Pilihan Kios** (`Buka` / `Tutup`) $\rightarrow$ **Grid Pilihan Menu** (harga, deskripsi, status stok `Tersedia` / `Habis`, serta tombol kembali ke daftar kios) dan penguncian keranjang per 1 kios.
- [x] **Keranjang, QRIS Per Toko, & Checkout:** Tambah/kurangi item, catatan pesanan, pengambilan default di konter kios, tampilan QRIS khusus per kios, dan wajib upload bukti pembayaran (otomatis dikompres ringan dengan `Pillow`) sebelum tombol pesan aktif.
- [x] **Live Queue & Tracking Status (3 Level Progress):** Halaman lacak pesanan dengan nomor antrean harian anti-bentrok (`#A-001`, dst.), preview bukti bayar, serta alur status:
  1. `0%` — `Menunggu Konfirmasi Pembayaran` (default setelah checkout; atau `Pembayaran Ditolak` beserta alasan jika ditolak)
  2. `50%` — `Sedang Menyiapkan Pesanan` (setelah bukti pembayaran dikonfirmasi penjual)
  3. `100%` — `Pesanan Sudah Bisa Diambil`
- [x] **Integrasi Database Dual-Mode (Firebase Cloud Firestore + Fallback Lokal):** Mendukung `serviceAccountKey.json` & `st.secrets["firebase"]`, auto-seeding data awal, transaksi Firestore nomor antrean harian, dan short-cache `@st.cache_data` dengan auto-invalidation.

### B. MVP — Role Penjual (Kios Kantin)
- [x] **Autentikasi Penjual:** Login menggunakan **Nama Kios + Password** ter-hash di koleksi `tenants`.
- [x] **Kelola Menu & Status Toko:** Tambah/edit/hapus menu, tombol cepat ubah status stok (`Tersedia` / `Habis`), serta toggle cepat status toko (`Buka` / `Tutup`).
- [x] **Dashboard Pesanan Masuk (Navigation Bar 4 Status):** Navigasi horizontal untuk `Menunggu Konfirmasi`, `Sedang Disiapkan`, `Sudah Bisa Diambil`, dan `Ditolak`, lengkap dengan verifikasi bukti QRIS.
- [x] **Update Status dengan Konfirmasi Ganda (Double Confirm):** Konfirmasi pembayaran (`0% → 50%`), penolakan pembayaran, dan penandaan pesanan siap diambil (`50% → 100%`) dilindungi konfirmasi ganda 2 langkah.
