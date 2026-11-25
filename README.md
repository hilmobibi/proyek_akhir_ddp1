# Tugas Akhir DDP1 GoFood Kancil (Queue Kantin Online)

### Anggota Kelompok:
- Azzam
- Hilmo
- Rasya

## Ide
Karena jam makan siang terbatas dan hectic banget, alangkah baiknya kalau bisa memesan makanan kantin dari perangkat pribadi. Itulah solusi yang sedang kami usahakan.

---

## Cara Menjalankan Aplikasi (Lokal)
```powershell
.\.venv\Scripts\streamlit run main.py
```

---

## Cara Menghubungkan ke Firebase Cloud Firestore (2 Menit)
Aplikasi menggunakan sistem **Dual-Mode**: jika kunci Firebase ditemukan, otomatis memakai **Firebase Cloud Firestore**; jika belum ditaruh, otomatis memakai memori lokal agar tidak crash.

1. Buka `https://console.firebase.google.com` dan klik **Add project** (misal: `gofood-kancil`).
2. Di menu kiri klik **Build -> Firestore Database -> Create database** (pilih lokasi `asia-southeast2` Jakarta atau `asia-southeast1` Singapore).
3. Klik ikon **Gerigi (Project settings) -> tab Service accounts -> Generate new private key**.
4. Simpan file JSON yang terunduh ke folder utama proyek ini dengan nama **`serviceAccountKey.json`** (sudah otomatis diabaikan oleh `.gitignore` agar aman).
5. Saat aplikasi dijalankan pertama kali, koleksi awal `tenants` dan `menus` akan **otomatis dibuat (auto-seed)** di Firestore.

### Deployment ke Streamlit Community Cloud
Di menu **App Settings -> Secrets**, tempelkan isi `serviceAccountKey.json` dalam format TOML:
```toml
APP_SERVICE_URL = "https://nama-aplikasi-kamu.streamlit.app/"

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

## Akun Login
- **Mahasiswa (Pembeli):** Login via **SSO UI (`sso.ui.ac.id/cas2`)**, atau daftar/masuk menggunakan **NPM + Password** (tersedia juga tombol Login Cepat Demo).
- **Penjual (Kios Kantin):** Masuk menggunakan **Nama Kios + Password** (password demo awal untuk ketiga kios: `kancil123`).
