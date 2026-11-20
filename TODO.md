## Fitur utama:
### A. MVP — Role Pembeli (Mahasiswa)
1. Autentikasi Sederhana: Register & Login (bisa pakai Firebase Auth atau simpan user di Firestore dengan password ter-hash).
2. Etalase Kantin (Home): Daftar tenant/kios kantin (status: Buka / Tutup) dan daftar menu lengkap dengan harga, foto, & status stok (Tersedia / Habis).
3. Keranjang & Checkout: Tambah/kurangi item, catatan pesanan (misal: "tidak pedas"), pilih metode ambil (Ambil Sendiri / Diantar ke Meja), lalu klik Pesan.
4. Live Queue & Tracking Status: Halaman lacak pesanan dengan nomor antrean dan status bertahap: Menunggu Konfirmasi → Sedang Dimasak → Siap Diambil → Selesai.

### B. MVP — Role Penjual (Kios Kantin)
1. Kelola Menu: Tambah/edit/hapus menu dan tombol cepat untuk ubah status stok (Habis / Ada) serta status toko (Buka / Tutup).
2. Dashboard Pesanan Masuk: Melihat daftar antrean pesanan yang masuk secara berurutan, lengkap dengan catatan pembeli.
3. Update Status Pesanan: Tombol aksi (Terima → Masak → Siap Diambil → Selesai) yang langsung memperbarui halaman Pembeli.