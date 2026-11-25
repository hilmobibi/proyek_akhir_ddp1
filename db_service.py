"""Lapisan layanan database dual-mode untuk Pesan Kancil.

Arsitektur:
- **1A (Dual-Mode):** Otomatis terhubung ke **Firebase Cloud Firestore** jika file
  ``serviceAccountKey.json`` atau ``st.secrets["firebase"]`` tersedia. Jika belum
  tersedia, otomatis berjalan pada mode memori lokal tanpa crash.
- **2 (Koleksi & Auth):** Mengelola 4 koleksi (``tenants``, ``menus``, ``orders``,
  ``users``) untuk mendukung SSO UI CAS 2.0, akun cadangan Pembeli, serta login
  Penjual berbasis Nama Kios + Password ter-hash.
- **3A (Kompresi Bukti QRIS):** Mengecilkan & mengompres gambar bukti bayar via
  ``Pillow`` (~30-60 KB JPEG) agar jauh di bawah batas dokumen 1 MB Firestore
  tanpa memerlukan Firebase Storage berbayar.
- **4A (Transaksi Nomor Antrean Harian):** Menggunakan ``@firestore.transactional``
  dengan reset otomatis setiap ganti tanggal (``A-001``, ``B-001``).
- **5A (Short Cache & Auto-Invalidate):** Meng-cache pembacaan Firestore singkat
  (``@st.cache_data``) dan otomatis menghapus cache setiap ada perubahan data.
"""

from __future__ import annotations

import base64
from collections.abc import Mapping
from datetime import datetime
import hashlib
import html
import io
import json
from pathlib import Path
from typing import Any
import uuid

import auth_service

STATUS_PENDING_PAYMENT = "Menunggu Konfirmasi Pembayaran"
STATUS_PREPARING = "Sedang Menyiapkan Pesanan"
STATUS_READY = "Pesanan Sudah Bisa Diambil"
STATUS_REJECTED = "Pembayaran Ditolak"
VALID_ORDER_STATUSES = (
    STATUS_PENDING_PAYMENT,
    STATUS_PREPARING,
    STATUS_READY,
    STATUS_REJECTED,
)

DEFAULT_SELLER_PASSWORD = "kancil123"
SERVICE_ACCOUNT_PATH = Path(__file__).resolve().parent / "serviceAccountKey.json"

_FALLBACK_STORE: dict[str, Any] = {}
_FIRESTORE_CLIENT_SINGLETON: Any = None
_FIRESTORE_CHECKED: bool = False
_FIRESTORE_SEEDED: bool = False


def _is_streamlit_active() -> bool:
    """Mengecek apakah kode sedang dieksekusi di dalam runtime aktif Streamlit."""
    try:
        import streamlit as st

        return getattr(st, "runtime", None) is not None and st.runtime.exists()
    except Exception:
        return False


def _get_store() -> Any:
    """Mengembalikan ``st.session_state`` atau fallback dictionary untuk mode lokal."""
    if _is_streamlit_active():
        import streamlit as st

        return st.session_state
    return _FALLBACK_STORE


def _load_firebase_credentials_dict() -> dict[str, Any] | None:
    """Membaca kredensial Service Account dari file lokal atau ``st.secrets``."""
    if SERVICE_ACCOUNT_PATH.is_file():
        try:
            raw = json.loads(SERVICE_ACCOUNT_PATH.read_text(encoding="utf-8"))
            private_key = str(raw.get("private_key", ""))
            if private_key and "YOUR_PRIVATE_KEY" not in private_key:
                return raw
        except Exception:
            pass

    if _is_streamlit_active():
        try:
            import streamlit as st

            if "firebase" in st.secrets:
                fb_sec = st.secrets["firebase"]
                if isinstance(fb_sec, Mapping):
                    cred_dict = dict(fb_sec)
                    if "private_key" in cred_dict:
                        cred_dict["private_key"] = str(
                            cred_dict["private_key"]
                        ).replace("\\n", "\n")
                    if "YOUR_PRIVATE_KEY" not in str(
                        cred_dict.get("private_key", "")
                    ):
                        return cred_dict
        except Exception:
            pass

    return None


def _create_firestore_client() -> Any | None:
    """Menginisialisasi objek client Firebase Cloud Firestore satu kali."""
    cred_dict = _load_firebase_credentials_dict()
    if cred_dict is None:
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception:
        return None


def get_firestore_client() -> Any | None:
    """Mengambil instance client Firestore (singleton), atau ``None`` jika mode lokal."""
    global _FIRESTORE_CLIENT_SINGLETON, _FIRESTORE_CHECKED

    if _is_streamlit_active():
        import streamlit as st

        @st.cache_resource(show_spinner=False)
        def _cached_client() -> Any | None:
            return _create_firestore_client()

        return _cached_client()

    if not _FIRESTORE_CHECKED:
        _FIRESTORE_CLIENT_SINGLETON = _create_firestore_client()
        _FIRESTORE_CHECKED = True
    return _FIRESTORE_CLIENT_SINGLETON


def get_db_backend_mode() -> str:
    """Mengembalikan ``'firebase'`` jika terhubung ke Firestore, atau ``'memory'``."""
    return "firebase" if get_firestore_client() is not None else "memory"


def clear_cache() -> None:
    """Membersihkan cache pembacaan data Streamlit agar query berikutnya segar."""
    if _is_streamlit_active():
        try:
            import streamlit as st

            st.cache_data.clear()
        except Exception:
            pass


def generate_qris_svg_data_uri(
    merchant_name: str, nmid: str, accent_color: str = "#18181B"
) -> str:
    """Membuat gambar kartu QRIS berbasis SVG XML untuk masing-masing kios."""
    safe_name = html.escape(merchant_name)
    safe_nmid = html.escape(nmid)
    safe_color = html.escape(accent_color)

    digest = hashlib.sha256(f"{merchant_name}:{nmid}".encode("utf-8")).digest()
    grid_size = 15
    cell = 9
    offset_x = 62
    offset_y = 74

    def _is_finder_area(row: int, col: int) -> bool:
        in_top_left = row < 4 and col < 4
        in_top_right = row < 4 and col >= grid_size - 4
        in_bottom_left = row >= grid_size - 4 and col < 4
        return in_top_left or in_top_right or in_bottom_left

    modules_svg: list[str] = []
    finder_origins = [
        (offset_x, offset_y),
        (offset_x + (grid_size - 3) * cell, offset_y),
        (offset_x, offset_y + (grid_size - 3) * cell),
    ]
    for fx, fy in finder_origins:
        size = cell * 3
        modules_svg.append(
            f'<rect x="{fx}" y="{fy}" width="{size}" height="{size}" '
            f'fill="none" stroke="#111827" stroke-width="4" rx="2"/>'
        )
        modules_svg.append(
            f'<rect x="{fx + 7}" y="{fy + 7}" width="{size - 14}" '
            f'height="{size - 14}" fill="#111827" rx="1"/>'
        )

    bit_idx = 0
    for r in range(grid_size):
        for c in range(grid_size):
            if _is_finder_area(r, c):
                continue
            byte_val = digest[(bit_idx // 8) % len(digest)]
            is_filled = (byte_val >> (bit_idx % 8)) & 1
            bit_idx += 1
            if is_filled:
                x = offset_x + c * cell
                y = offset_y + r * cell
                modules_svg.append(
                    f'<rect x="{x}" y="{y}" width="{cell - 1}" '
                    f'height="{cell - 1}" fill="#111827" rx="1"/>'
                )

    modules_joined = "\n    ".join(modules_svg)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="260" height="290" '
        'viewBox="0 0 260 290">'
        '<rect x="2" y="2" width="256" height="286" rx="16" fill="#FFFFFF" '
        'stroke="#E5E7EB" stroke-width="2"/>'
        f'<rect x="2" y="2" width="256" height="44" rx="14" fill="{safe_color}"/>'
        f'<rect x="2" y="32" width="256" height="14" fill="{safe_color}"/>'
        '<text x="130" y="29" text-anchor="middle" fill="#FFFFFF" '
        'font-family="Arial, sans-serif" font-size="16" font-weight="bold">'
        "QRIS PESAN KANCIL</text>"
        '<text x="130" y="61" text-anchor="middle" fill="#111827" '
        'font-family="Arial, sans-serif" font-size="12" font-weight="bold">'
        f"{safe_name}</text>"
        f"{modules_joined}"
        '<text x="130" y="232" text-anchor="middle" fill="#6B7280" '
        'font-family="monospace" font-size="10">'
        f"NMID: {safe_nmid}</text>"
        '<rect x="40" y="244" width="180" height="28" rx="6" fill="#F3F4F6"/>'
        '<text x="130" y="262" text-anchor="middle" fill="#374151" '
        'font-family="Arial, sans-serif" font-size="11" font-weight="bold">'
        "Scan &amp; Upload Bukti Bayar</text>"
        "</svg>"
    )


def compress_payment_image(
    data: bytes, filename: str, max_width: int = 600, quality: int = 72
) -> tuple[bytes, str]:
    """Mengecilkan & mengompres gambar bukti bayar ke JPEG ringan (< 100 KB).

    Memastikan ukuran dokumen pesanan selalu jauh di bawah batas 1 MB Firestore.
    Jika ``data`` bukan gambar valid (mis. bytes dummy saat unit test), data
    dikembalikan apa adanya tanpa melempar error.
    """
    try:
        from PIL import Image

        with Image.open(io.BytesIO(data)) as img:
            if img.mode in ("RGBA", "LA") or (
                img.mode == "P" and "transparency" in img.info
            ):
                rgba = img.convert("RGBA")
                background = Image.new("RGB", rgba.size, (255, 255, 255))
                background.paste(rgba, mask=rgba.split()[3])
                rgb_img = background
            else:
                rgb_img = img.convert("RGB")

            if rgb_img.width > max_width:
                ratio = max_width / float(rgb_img.width)
                new_height = max(1, int(rgb_img.height * ratio))
                rgb_img = rgb_img.resize(
                    (max_width, new_height), Image.Resampling.LANCZOS
                )

            out_buf = io.BytesIO()
            rgb_img.save(out_buf, format="JPEG", quality=quality, optimize=True)
            stem = filename.rsplit(".", 1)[0] if "." in filename else filename
            return out_buf.getvalue(), f"{stem}.jpg"
    except Exception:
        return data, filename


def encode_uploaded_file(uploaded_file: Any) -> tuple[bytes, str]:
    """Mengambil dan mengompres gambar dari objek ``st.file_uploader``."""
    return compress_payment_image(uploaded_file.getvalue(), uploaded_file.name)


def bytes_to_base64_data_uri(data: bytes, filename: str) -> str:
    """Mengonversi bytes gambar bukti bayar menjadi Data URI Base64."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    mime = "image/png" if ext == "png" else "image/jpeg"
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _decode_data_uri_to_bytes(data_uri_or_b64: str) -> bytes:
    """Mendekode string Data URI Base64 kembali menjadi raw ``bytes`` untuk ``st.image``."""
    if not data_uri_or_b64:
        return b""
    raw_b64 = (
        data_uri_or_b64.split(",", 1)[1]
        if "," in data_uri_or_b64
        else data_uri_or_b64
    )
    return base64.b64decode(raw_b64)


def _hydrate_order(doc_dict: dict[str, Any]) -> dict[str, Any]:
    """Memastikan field ``payment_proof_bytes`` selalu tersedia pada dict pesanan."""
    hydrated = dict(doc_dict)
    if not hydrated.get("payment_proof_bytes") and hydrated.get(
        "payment_proof_b64"
    ):
        hydrated["payment_proof_bytes"] = _decode_data_uri_to_bytes(
            hydrated["payment_proof_b64"]
        )
    hydrated.setdefault("rejection_reason", "")
    return hydrated


_DEFAULT_TENANT_META: dict[str, dict[str, str]] = {
    "t1": {
        "category": "Ayam & Sambal",
        "eta": "8-12 mnt",
        "image_url": "assets/demo/t1.jpg",
    },
    "t2": {
        "category": "Berkuah & Bakso",
        "eta": "5-10 mnt",
        "image_url": "assets/demo/t2.jpg",
    },
    "t3": {
        "category": "Mie & Nasi Goreng",
        "eta": "10-15 mnt",
        "image_url": "assets/demo/t3.jpg",
    },
}

_DEFAULT_MENU_IMAGES: dict[str, str] = {
    "m1": "assets/demo/m1.jpg",
    "m2": "assets/demo/m2.jpg",
    "m3": "assets/demo/m3.jpg",
    "m4": "assets/demo/m4.jpg",
    "m5": "assets/demo/m5.jpg",
    "m6": "assets/demo/m6.jpg",
    "m7": "assets/demo/m7.jpg",
    "m8": "assets/demo/m8.jpg",
    "m9": "assets/demo/m9.jpg",
    "m10": "assets/demo/m10.jpg",
    "m11": "assets/demo/m3.jpg",
    "m12": "assets/demo/m4.jpg",
}


def _hydrate_tenant(doc_dict: dict[str, Any]) -> dict[str, Any]:
    """Melengkapi field visual default kios bila dokumen Firestore lama belum memilikinya."""
    hydrated = dict(doc_dict)
    defaults = _DEFAULT_TENANT_META.get(hydrated.get("id", ""), {})
    if not hydrated.get("image_url"):
        hydrated["image_url"] = defaults.get("image_url", "")
    if not hydrated.get("category"):
        hydrated["category"] = defaults.get("category", "Kios Kantin")
    if not hydrated.get("eta"):
        hydrated["eta"] = defaults.get("eta", "5-10 mnt")
    # Pastikan QRIS selalu bertema monokrom bersih & hydrate QRIS asli jika sudah diunggah
    hydrated["qris_svg"] = generate_qris_svg_data_uri(
        hydrated.get("name", "Kios Kantin"),
        hydrated.get("nmid", "ID102030400000"),
        "#18181B",
    )
    qris_b64 = hydrated.get("qris_image_b64", "")
    hydrated["qris_image_b64"] = qris_b64
    hydrated["qris_image_bytes"] = (
        _decode_data_uri_to_bytes(qris_b64) if qris_b64 else b""
    )
    return hydrated


def get_tenant_qris_display(tenant: dict[str, Any]) -> bytes | str:
    """Mengembalikan gambar QRIS asli yang diunggah penjual, atau QRIS SVG bawaan."""
    if tenant.get("qris_image_bytes"):
        return tenant["qris_image_bytes"]
    if tenant.get("qris_image_b64"):
        return _decode_data_uri_to_bytes(tenant["qris_image_b64"])
    return tenant["qris_svg"]


def _hydrate_menu(doc_dict: dict[str, Any]) -> dict[str, Any]:
    """Melengkapi field foto default menu bila dokumen Firestore lama belum memilikinya."""
    hydrated = dict(doc_dict)
    if not hydrated.get("image_url"):
        hydrated["image_url"] = _DEFAULT_MENU_IMAGES.get(
            hydrated.get("id", ""), ""
        )
    return hydrated


def _build_seed_tenants() -> list[dict[str, Any]]:
    """Membangun data awal 3 kios kantin dengan password ter-hash."""
    default_pw_hash = auth_service.hash_password(
        DEFAULT_SELLER_PASSWORD, salt="pesankancil_seed"
    )
    return [
        {
            "id": "t1",
            "name": "Kantin Ayam Geprek Mas Budi",
            "category": "Ayam & Sambal",
            "eta": "8-12 mnt",
            "image_url": "assets/demo/t1.jpg",
            "emoji": "",
            "password_hash": default_pw_hash,
            "description": "Spesialis ayam geprek sambal bawang, tahu tempe, dan es segar.",
            "is_open": True,
            "queue_prefix": "A",
            "order_seq": 0,
            "order_seq_date": "",
            "nmid": "ID102030400001",
            "qris_svg": generate_qris_svg_data_uri(
                "Ayam Geprek Mas Budi", "ID102030400001", "#18181B"
            ),
        },
        {
            "id": "t2",
            "name": "Soto & Bakso Bu Sari",
            "category": "Berkuah & Bakso",
            "eta": "5-10 mnt",
            "image_url": "assets/demo/t2.jpg",
            "emoji": "",
            "password_hash": default_pw_hash,
            "description": "Soto ayam bening, bakso urat, dan minuman hangat/dingin.",
            "is_open": True,
            "queue_prefix": "B",
            "order_seq": 0,
            "order_seq_date": "",
            "nmid": "ID102030400002",
            "qris_svg": generate_qris_svg_data_uri(
                "Soto & Bakso Bu Sari", "ID102030400002", "#18181B"
            ),
        },
        {
            "id": "t3",
            "name": "Mie Ayam & Nasgor Pakde",
            "category": "Mie & Nasi Goreng",
            "eta": "10-15 mnt",
            "image_url": "assets/demo/t3.jpg",
            "emoji": "",
            "password_hash": default_pw_hash,
            "description": "Mie ayam jamur, nasi goreng kampung, dan kwetiau goreng.",
            "is_open": False,
            "queue_prefix": "C",
            "order_seq": 0,
            "order_seq_date": "",
            "nmid": "ID102030400003",
            "qris_svg": generate_qris_svg_data_uri(
                "Mie Ayam Pakde", "ID102030400003", "#18181B"
            ),
        },
    ]


def _build_seed_menus() -> list[dict[str, Any]]:
    """Membangun data awal 12 menu kantin."""
    return [
        {
            "id": "m1",
            "tenant_id": "t1",
            "name": "Paket Ayam Geprek + Nasi",
            "price": 15000,
            "emoji": "",
            "description": "Ayam krispi geprek sambal bawang level 1-5 + nasi hangat.",
            "is_available": True,
        },
        {
            "id": "m2",
            "tenant_id": "t1",
            "name": "Ayam Geprek Keju Mozarella",
            "price": 18000,
            "emoji": "",
            "description": "Ayam geprek dengan lelehan keju gurih di atasnya.",
            "is_available": True,
        },
        {
            "id": "m3",
            "tenant_id": "t1",
            "name": "Indomie Goreng Telur Geprek",
            "price": 13000,
            "emoji": "",
            "description": "Indomie goreng double + telur dadar dan suwiran ayam.",
            "is_available": False,
        },
        {
            "id": "m4",
            "tenant_id": "t1",
            "name": "Es Teh Manis Jumbo",
            "price": 4000,
            "emoji": "",
            "description": "Es teh manis dingin penyegar jam makan siang.",
            "is_available": True,
        },
        {
            "id": "m5",
            "tenant_id": "t2",
            "name": "Soto Ayam Lamongan + Nasi",
            "price": 14000,
            "emoji": "",
            "description": "Kuah soto gurih lengkap dengan koya, telur, dan suwiran ayam.",
            "is_available": True,
        },
        {
            "id": "m6",
            "tenant_id": "t2",
            "name": "Bakso Urat Komplit",
            "price": 16000,
            "emoji": "",
            "description": "Bakso urat besar, 3 bakso halus, mie kuning, dan bihun.",
            "is_available": True,
        },
        {
            "id": "m7",
            "tenant_id": "t2",
            "name": "Tahu Goreng Isi (3 pcs)",
            "price": 6000,
            "emoji": "",
            "description": "Tahu isi sayur renyah cocok untuk teman makan soto.",
            "is_available": False,
        },
        {
            "id": "m8",
            "tenant_id": "t2",
            "name": "Es Jeruk Peras Asli",
            "price": 5000,
            "emoji": "",
            "description": "Jeruk peras segar tanpa pemanis buatan.",
            "is_available": True,
        },
        {
            "id": "m9",
            "tenant_id": "t3",
            "name": "Mie Ayam Bakso Spesial",
            "price": 15000,
            "emoji": "",
            "description": "Mie kenyal dengan topping ayam kecap dan 2 bakso sapi.",
            "is_available": True,
        },
        {
            "id": "m10",
            "tenant_id": "t3",
            "name": "Nasi Goreng Kampung Telur",
            "price": 16000,
            "emoji": "",
            "description": "Nasi goreng bumbu terasi ringan dengan telur mata sapi.",
            "is_available": True,
        },
        {
            "id": "m11",
            "tenant_id": "t3",
            "name": "Kwetiau Goreng Sapi",
            "price": 17000,
            "emoji": "",
            "description": "Kwetiau goreng gurih dengan irisan daging dan sawi.",
            "is_available": False,
        },
        {
            "id": "m12",
            "tenant_id": "t3",
            "name": "Air Mineral Dingin 600ml",
            "price": 4000,
            "emoji": "",
            "description": "Air mineral kemasan botol dingin.",
            "is_available": True,
        },
    ]


def init_db() -> None:
    """Menginisialisasi koleksi awal di Firestore (auto-seed) atau di memori lokal."""
    global _FIRESTORE_SEEDED

    fs = get_firestore_client()
    if fs is not None:
        if not _FIRESTORE_SEEDED:
            existing = list(fs.collection("tenants").limit(1).stream())
            if not existing:
                batch = fs.batch()
                for tenant in _build_seed_tenants():
                    batch.set(
                        fs.collection("tenants").document(tenant["id"]), tenant
                    )
                for menu in _build_seed_menus():
                    batch.set(
                        fs.collection("menus").document(menu["id"]), menu
                    )
                batch.commit()
            _FIRESTORE_SEEDED = True
        return

    store = _get_store()
    if "db_tenants" not in store:
        store["db_tenants"] = _build_seed_tenants()
    if "db_menus" not in store:
        store["db_menus"] = _build_seed_menus()
    if "db_orders" not in store:
        store["db_orders"] = []
    if "db_users" not in store:
        store["db_users"] = {}


def _fetch_tenants_firestore() -> list[dict[str, Any]]:
    """Membaca seluruh dokumen koleksi ``tenants`` dari Firestore."""
    fs = get_firestore_client()
    if fs is None:
        return []
    docs = [_hydrate_tenant(doc.to_dict()) for doc in fs.collection("tenants").stream()]
    return sorted(docs, key=lambda d: str(d.get("id", "")))


def _fetch_menus_firestore(tenant_id: str) -> list[dict[str, Any]]:
    """Membaca menu milik satu kios dari koleksi ``menus`` Firestore."""
    fs = get_firestore_client()
    if fs is None:
        return []
    from google.cloud.firestore_v1.base_query import FieldFilter

    query = fs.collection("menus").where(
        filter=FieldFilter("tenant_id", "==", tenant_id)
    )
    docs = [_hydrate_menu(doc.to_dict()) for doc in query.stream()]
    return sorted(docs, key=lambda d: str(d.get("id", "")))


def get_tenants() -> list[dict[str, Any]]:
    """Mengambil seluruh daftar kios kantin (dengan short-cache di mode Firebase)."""
    init_db()
    if get_db_backend_mode() == "firebase":
        if _is_streamlit_active():
            import streamlit as st

            @st.cache_data(ttl=10, show_spinner=False)
            def _cached_tenants() -> list[dict[str, Any]]:
                return _fetch_tenants_firestore()

            return list(_cached_tenants())
        return _fetch_tenants_firestore()

    return [_hydrate_tenant(t) for t in _get_store()["db_tenants"]]


def get_tenant_by_id(tenant_id: str) -> dict[str, Any] | None:
    """Mengambil detail 1 kios berdasarkan ``tenant_id``."""
    for tenant in get_tenants():
        if tenant["id"] == tenant_id:
            return tenant
    return None


def get_menus_by_tenant(tenant_id: str) -> list[dict[str, Any]]:
    """Mengambil daftar menu milik satu kios (dengan short-cache di mode Firebase)."""
    init_db()
    if get_db_backend_mode() == "firebase":
        if _is_streamlit_active():
            import streamlit as st

            @st.cache_data(ttl=10, show_spinner=False)
            def _cached_menus(tid: str) -> list[dict[str, Any]]:
                return _fetch_menus_firestore(tid)

            return list(_cached_menus(tenant_id))
        return _fetch_menus_firestore(tenant_id)

    return [
        _hydrate_menu(menu)
        for menu in _get_store()["db_menus"]
        if menu["tenant_id"] == tenant_id
    ]


# ---------------------------------------------------------------------------
# Autentikasi User (Pembeli SSO UI / Akun Cadangan & Penjual Nama Kios + Password)
# ---------------------------------------------------------------------------


def upsert_sso_buyer(
    username: str, name: str, npm: str, kd_org: str = ""
) -> dict[str, Any]:
    """Menyimpan atau memperbarui profil mahasiswa hasil login SSO UI ke koleksi ``users``."""
    init_db()
    clean_npm = npm.strip() or username.strip()
    clean_name = name.strip() or username.strip()
    user_id = f"npm-{clean_npm}"
    now_iso = datetime.now().isoformat()

    payload = {
        "id": user_id,
        "username": username.strip(),
        "name": clean_name,
        "npm": clean_npm,
        "kd_org": kd_org.strip(),
        "role": "buyer",
        "auth_provider": "sso_ui",
        "updated_at": now_iso,
    }

    fs = get_firestore_client()
    if fs is not None:
        fs.collection("users").document(user_id).set(payload, merge=True)
        clear_cache()
    else:
        users_map = _get_store()["db_users"]
        existing = users_map.get(user_id, {})
        users_map[user_id] = {**existing, **payload}

    return {
        "id": user_id,
        "name": clean_name,
        "npm": clean_npm,
        "role": "buyer",
        "auth_provider": "sso_ui",
    }


def register_buyer(name: str, npm: str, password: str) -> dict[str, Any]:
    """Mendaftarkan akun mahasiswa baru (NPM + Password ter-hash) ke koleksi ``users``."""
    init_db()
    clean_name = name.strip()
    clean_npm = npm.strip()
    if not clean_name or not clean_npm:
        raise ValueError("Nama lengkap dan NPM wajib diisi.")
    if len(password) < 4:
        raise ValueError("Password minimal 4 karakter.")

    user_id = f"npm-{clean_npm}"
    pw_hash = auth_service.hash_password(password)
    now_iso = datetime.now().isoformat()

    fs = get_firestore_client()
    if fs is not None:
        doc_ref = fs.collection("users").document(user_id)
        snap = doc_ref.get()
        if snap.exists and (snap.to_dict() or {}).get("password_hash"):
            raise ValueError(
                "NPM ini sudah terdaftar. Silakan langsung masuk menggunakan passwordmu."
            )
        doc_ref.set(
            {
                "id": user_id,
                "name": clean_name,
                "npm": clean_npm,
                "password_hash": pw_hash,
                "role": "buyer",
                "auth_provider": "password",
                "updated_at": now_iso,
            },
            merge=True,
        )
        clear_cache()
    else:
        users_map = _get_store()["db_users"]
        if user_id in users_map and users_map[user_id].get("password_hash"):
            raise ValueError(
                "NPM ini sudah terdaftar. Silakan langsung masuk menggunakan passwordmu."
            )
        users_map[user_id] = {
            **users_map.get(user_id, {}),
            "id": user_id,
            "name": clean_name,
            "npm": clean_npm,
            "password_hash": pw_hash,
            "role": "buyer",
            "auth_provider": "password",
            "updated_at": now_iso,
        }

    return {
        "id": user_id,
        "name": clean_name,
        "npm": clean_npm,
        "role": "buyer",
        "auth_provider": "password",
    }


def authenticate_buyer(npm: str, password: str) -> dict[str, Any] | None:
    """Memverifikasi login akun mahasiswa berdasarkan NPM dan password."""
    init_db()
    clean_npm = npm.strip()
    if not clean_npm or not password:
        return None

    user_id = f"npm-{clean_npm}"
    fs = get_firestore_client()
    if fs is not None:
        snap = fs.collection("users").document(user_id).get()
        user_doc = snap.to_dict() if snap.exists else None
    else:
        user_doc = _get_store()["db_users"].get(user_id)

    if not user_doc or not user_doc.get("password_hash"):
        return None
    if not auth_service.verify_password(password, user_doc["password_hash"]):
        return None

    return {
        "id": user_doc["id"],
        "name": user_doc["name"],
        "npm": user_doc["npm"],
        "role": "buyer",
        "auth_provider": user_doc.get("auth_provider", "password"),
    }


def register_seller(
    name: str,
    password: str,
    category: str = "Kios Kantin",
    description: str = "",
    eta: str = "5-10 mnt",
    image_url: str = "",
    qris_image_b64: str = "",
) -> dict[str, Any]:
    """Mendaftarkan kios penjual baru beserta password ter-hash ke koleksi ``tenants``."""
    init_db()
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Nama kios wajib diisi.")
    if len(password) < 4:
        raise ValueError("Password minimal 4 karakter.")

    existing_names = {t["name"].strip().lower() for t in get_tenants()}
    if clean_name.lower() in existing_names:
        raise ValueError(
            "Nama kios ini sudah terdaftar. Silakan gunakan nama lain atau langsung masuk."
        )

    tenant_id = f"t-{uuid.uuid4().hex[:6]}"
    first_alnum = next((ch.upper() for ch in clean_name if ch.isalnum()), "K")
    nmid = f"ID1020{uuid.uuid4().int % 100_000_000:08d}"
    new_tenant: dict[str, Any] = {
        "id": tenant_id,
        "name": clean_name,
        "category": category.strip() or "Kios Kantin",
        "eta": eta.strip() or "5-10 mnt",
        "image_url": image_url.strip(),
        "emoji": "",
        "password_hash": auth_service.hash_password(password),
        "description": description.strip() or f"Kios {clean_name} di kantin fakultas.",
        "is_open": True,
        "queue_prefix": first_alnum,
        "order_seq": 0,
        "order_seq_date": "",
        "nmid": nmid,
        "qris_image_b64": qris_image_b64.strip(),
        "qris_svg": generate_qris_svg_data_uri(clean_name, nmid, "#18181B"),
    }

    fs = get_firestore_client()
    if fs is not None:
        fs.collection("tenants").document(tenant_id).set(new_tenant)
        clear_cache()
    else:
        _get_store()["db_tenants"].append(new_tenant)

    return _hydrate_tenant(new_tenant)


def authenticate_seller(tenant_name: str, password: str) -> dict[str, Any] | None:
    """Memverifikasi login Penjual berdasarkan Nama Kios (case-insensitive) & Password."""
    init_db()
    clean_query = tenant_name.strip().lower()
    if not clean_query or not password:
        return None

    for tenant in get_tenants():
        matches_name = tenant["name"].strip().lower() == clean_query
        matches_id = tenant["id"].strip().lower() == clean_query
        if matches_name or matches_id:
            pw_hash = tenant.get("password_hash", "")
            if pw_hash and auth_service.verify_password(password, pw_hash):
                return tenant
            return None
    return None


# ---------------------------------------------------------------------------
# Transaksi Pesanan & Live Queue
# ---------------------------------------------------------------------------


def create_order(
    buyer_id: str,
    buyer_name: str,
    buyer_npm: str,
    tenant_id: str,
    items: list[dict[str, Any]],
    notes: str,
    payment_proof_bytes: bytes,
    payment_filename: str,
    order_date_override: str | None = None,
) -> dict[str, Any]:
    """Membuat pesanan baru dengan kompresi gambar & transaksi nomor antrean harian.

    Status default otomatis diset ke ``STATUS_PENDING_PAYMENT`` (0%).
    Nomor antrean di-reset otomatis ke ``001`` setiap berganti tanggal.
    """
    init_db()
    if not items:
        raise ValueError("Daftar item pesanan tidak boleh kosong.")
    if not payment_proof_bytes:
        raise ValueError("Bukti pembayaran QRIS wajib diunggah.")

    compressed_bytes, compressed_name = compress_payment_image(
        payment_proof_bytes, payment_filename
    )
    proof_b64 = bytes_to_base64_data_uri(compressed_bytes, compressed_name)

    now = datetime.now()
    today_str = order_date_override or now.strftime("%Y-%m-%d")
    now_iso = now.isoformat()
    human_time = now.strftime("%d %b %Y, %H:%M WIB")
    order_id = f"ord-{uuid.uuid4().hex[:8]}"
    total_price = sum(int(item["price"]) * int(item["qty"]) for item in items)
    clean_items = [dict(item) for item in items]

    fs = get_firestore_client()
    if fs is not None:
        from firebase_admin import firestore

        tenant_ref = fs.collection("tenants").document(tenant_id)
        order_ref = fs.collection("orders").document(order_id)

        @firestore.transactional
        def _run_order_tx(transaction: Any) -> dict[str, Any]:
            snap = tenant_ref.get(transaction=transaction)
            if not snap.exists:
                raise ValueError(f"Kios dengan id '{tenant_id}' tidak ditemukan.")
            tdata = snap.to_dict() or {}
            if tdata.get("order_seq_date") == today_str:
                next_seq = int(tdata.get("order_seq", 0)) + 1
            else:
                next_seq = 1
            prefix = tdata.get("queue_prefix", "A")
            queue_number = f"{prefix}-{next_seq:03d}"

            doc_data: dict[str, Any] = {
                "id": order_id,
                "queue_number": queue_number,
                "order_date": today_str,
                "buyer_id": buyer_id,
                "buyer_name": buyer_name,
                "buyer_npm": buyer_npm,
                "tenant_id": tenant_id,
                "tenant_name": tdata["name"],
                "items": clean_items,
                "notes": notes.strip(),
                "pickup_method": "Ambil langsung di konter kios",
                "total_price": total_price,
                "payment_proof_b64": proof_b64,
                "payment_filename": compressed_name,
                "status": STATUS_PENDING_PAYMENT,
                "rejection_reason": "",
                "created_at": human_time,
                "created_at_iso": now_iso,
            }
            transaction.update(
                tenant_ref,
                {"order_seq": next_seq, "order_seq_date": today_str},
            )
            transaction.set(order_ref, doc_data)
            return doc_data

        created_doc = _run_order_tx(fs.transaction())
        clear_cache()
        return _hydrate_order(created_doc)

    store = _get_store()
    target_tenant = next(
        (t for t in store["db_tenants"] if t["id"] == tenant_id), None
    )
    if target_tenant is None:
        raise ValueError(f"Kios dengan id '{tenant_id}' tidak ditemukan.")

    if target_tenant.get("order_seq_date") == today_str:
        next_seq = int(target_tenant.get("order_seq", 0)) + 1
    else:
        next_seq = 1
    target_tenant["order_seq"] = next_seq
    target_tenant["order_seq_date"] = today_str
    queue_number = f"{target_tenant['queue_prefix']}-{next_seq:03d}"

    order: dict[str, Any] = {
        "id": order_id,
        "queue_number": queue_number,
        "order_date": today_str,
        "buyer_id": buyer_id,
        "buyer_name": buyer_name,
        "buyer_npm": buyer_npm,
        "tenant_id": tenant_id,
        "tenant_name": target_tenant["name"],
        "items": clean_items,
        "notes": notes.strip(),
        "pickup_method": "Ambil langsung di konter kios",
        "total_price": total_price,
        "payment_proof_bytes": compressed_bytes,
        "payment_proof_b64": proof_b64,
        "payment_filename": compressed_name,
        "status": STATUS_PENDING_PAYMENT,
        "rejection_reason": "",
        "created_at": human_time,
        "created_at_iso": now_iso,
    }
    store["db_orders"].append(order)
    return order


def get_buyer_orders(buyer_id: str) -> list[dict[str, Any]]:
    """Mengambil riwayat & antrean pesanan milik pembeli (terbaru di paling atas)."""
    init_db()
    fs = get_firestore_client()
    if fs is not None:
        from google.cloud.firestore_v1.base_query import FieldFilter

        query = fs.collection("orders").where(
            filter=FieldFilter("buyer_id", "==", buyer_id)
        )
        docs = [_hydrate_order(doc.to_dict()) for doc in query.stream()]
        return sorted(
            docs, key=lambda o: str(o.get("created_at_iso", "")), reverse=True
        )

    orders = [
        _hydrate_order(o)
        for o in _get_store()["db_orders"]
        if o["buyer_id"] == buyer_id
    ]
    return list(reversed(orders))


def get_tenant_orders(tenant_id: str) -> list[dict[str, Any]]:
    """Mengambil antrean pesanan milik satu kios secara berurutan (FIFO)."""
    init_db()
    fs = get_firestore_client()
    if fs is not None:
        from google.cloud.firestore_v1.base_query import FieldFilter

        query = fs.collection("orders").where(
            filter=FieldFilter("tenant_id", "==", tenant_id)
        )
        docs = [_hydrate_order(doc.to_dict()) for doc in query.stream()]
        return sorted(docs, key=lambda o: str(o.get("created_at_iso", "")))

    return [
        _hydrate_order(o)
        for o in _get_store()["db_orders"]
        if o["tenant_id"] == tenant_id
    ]


def get_all_orders() -> list[dict[str, Any]]:
    """Mengambil seluruh pesanan lintas kios (terbaru di paling atas)."""
    init_db()
    fs = get_firestore_client()
    if fs is not None:
        docs = [
            _hydrate_order(doc.to_dict())
            for doc in fs.collection("orders").stream()
        ]
        return sorted(
            docs, key=lambda o: str(o.get("created_at_iso", "")), reverse=True
        )

    return [
        _hydrate_order(o) for o in reversed(_get_store()["db_orders"])
    ]


def update_order_status(
    order_id: str, new_status: str, rejection_reason: str = ""
) -> bool:
    """Memperbarui status pesanan beserta alasan penolakan jika pembayaran ditolak."""
    if new_status not in VALID_ORDER_STATUSES:
        raise ValueError(f"Status '{new_status}' tidak valid.")

    clean_reason = (
        rejection_reason.strip() if new_status == STATUS_REJECTED else ""
    )

    init_db()
    fs = get_firestore_client()
    if fs is not None:
        doc_ref = fs.collection("orders").document(order_id)
        if not doc_ref.get().exists:
            return False
        doc_ref.update(
            {"status": new_status, "rejection_reason": clean_reason}
        )
        clear_cache()
        return True

    for order in _get_store()["db_orders"]:
        if order["id"] == order_id:
            order["status"] = new_status
            order["rejection_reason"] = clean_reason
            return True
    return False


# ---------------------------------------------------------------------------
# Pengelolaan Kios & CRUD Menu (Penjual)
# ---------------------------------------------------------------------------


def toggle_tenant_open(tenant_id: str, is_open: bool) -> bool:
    """Mengubah status buka/tutup kios kantin."""
    init_db()
    fs = get_firestore_client()
    if fs is not None:
        doc_ref = fs.collection("tenants").document(tenant_id)
        if not doc_ref.get().exists:
            return False
        doc_ref.update({"is_open": bool(is_open)})
        clear_cache()
        return True

    for tenant in _get_store()["db_tenants"]:
        if tenant["id"] == tenant_id:
            tenant["is_open"] = bool(is_open)
            return True
    return False


def update_tenant_image(
    tenant_id: str, image_bytes: bytes, filename: str
) -> str:
    """Mengompres dan menyimpan foto kios baru milik penjual ke database."""
    init_db()
    compressed_bytes, compressed_name = compress_payment_image(
        image_bytes, filename, max_width=640, quality=76
    )
    data_uri = bytes_to_base64_data_uri(compressed_bytes, compressed_name)

    fs = get_firestore_client()
    if fs is not None:
        doc_ref = fs.collection("tenants").document(tenant_id)
        if not doc_ref.get().exists:
            raise ValueError(f"Kios dengan id '{tenant_id}' tidak ditemukan.")
        doc_ref.update({"image_url": data_uri})
        clear_cache()
        return data_uri

    for tenant in _get_store()["db_tenants"]:
        if tenant["id"] == tenant_id:
            tenant["image_url"] = data_uri
            return data_uri
    raise ValueError(f"Kios dengan id '{tenant_id}' tidak ditemukan.")


def update_tenant_qris(
    tenant_id: str, qris_bytes: bytes, filename: str
) -> str:
    """Mengompres (ketajaman tinggi agar mudah discan) & menyimpan QRIS asli kios."""
    init_db()
    compressed_bytes, compressed_name = compress_payment_image(
        qris_bytes, filename, max_width=800, quality=88
    )
    data_uri = bytes_to_base64_data_uri(compressed_bytes, compressed_name)

    fs = get_firestore_client()
    if fs is not None:
        doc_ref = fs.collection("tenants").document(tenant_id)
        if not doc_ref.get().exists:
            raise ValueError(f"Kios dengan id '{tenant_id}' tidak ditemukan.")
        doc_ref.update({"qris_image_b64": data_uri})
        clear_cache()
        return data_uri

    for tenant in _get_store()["db_tenants"]:
        if tenant["id"] == tenant_id:
            tenant["qris_image_b64"] = data_uri
            return data_uri
    raise ValueError(f"Kios dengan id '{tenant_id}' tidak ditemukan.")


def _validate_menu_fields(name: str, price: int) -> tuple[str, int]:
    """Memvalidasi nama dan harga menu agar seragam saat tambah maupun edit."""
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Nama menu tidak boleh kosong.")
    parsed_price = int(price)
    if parsed_price <= 0:
        raise ValueError("Harga menu harus lebih dari 0.")
    return clean_name, parsed_price


def add_menu(
    tenant_id: str,
    name: str,
    price: int,
    description: str,
    emoji: str = "",
    is_available: bool = True,
    image_url: str = "",
) -> dict[str, Any]:
    """Menambahkan menu baru ke daftar menu milik suatu kios."""
    init_db()
    if get_tenant_by_id(tenant_id) is None:
        raise ValueError(f"Kios dengan id '{tenant_id}' tidak ditemukan.")

    clean_name, parsed_price = _validate_menu_fields(name, price)
    new_menu: dict[str, Any] = {
        "id": f"m-{uuid.uuid4().hex[:6]}",
        "tenant_id": tenant_id,
        "name": clean_name,
        "price": parsed_price,
        "emoji": emoji.strip(),
        "description": description.strip(),
        "is_available": bool(is_available),
        "image_url": image_url.strip(),
    }

    fs = get_firestore_client()
    if fs is not None:
        fs.collection("menus").document(new_menu["id"]).set(new_menu)
        clear_cache()
    else:
        _get_store()["db_menus"].append(new_menu)

    return new_menu


def update_menu(
    menu_id: str,
    name: str,
    price: int,
    description: str,
    emoji: str,
    is_available: bool,
    image_url: str | None = None,
) -> bool:
    """Memperbarui detail menu yang sudah ada (termasuk foto bila diunggah)."""
    clean_name, parsed_price = _validate_menu_fields(name, price)
    clean_emoji = emoji.strip()

    init_db()
    fs = get_firestore_client()
    if fs is not None:
        doc_ref = fs.collection("menus").document(menu_id)
        if not doc_ref.get().exists:
            return False
        updates: dict[str, Any] = {
            "name": clean_name,
            "price": parsed_price,
            "description": description.strip(),
            "emoji": clean_emoji,
            "is_available": bool(is_available),
        }
        if image_url is not None:
            updates["image_url"] = image_url.strip()
        doc_ref.update(updates)
        clear_cache()
        return True

    for menu in _get_store()["db_menus"]:
        if menu["id"] == menu_id:
            menu["name"] = clean_name
            menu["price"] = parsed_price
            menu["description"] = description.strip()
            menu["emoji"] = clean_emoji
            menu["is_available"] = bool(is_available)
            if image_url is not None:
                menu["image_url"] = image_url.strip()
            return True
    return False


def toggle_menu_availability(menu_id: str, is_available: bool) -> bool:
    """Mengubah status ketersediaan stok menu (Tersedia / Habis)."""
    init_db()
    fs = get_firestore_client()
    if fs is not None:
        doc_ref = fs.collection("menus").document(menu_id)
        if not doc_ref.get().exists:
            return False
        doc_ref.update({"is_available": bool(is_available)})
        clear_cache()
        return True

    for menu in _get_store()["db_menus"]:
        if menu["id"] == menu_id:
            menu["is_available"] = bool(is_available)
            return True
    return False


def delete_menu(menu_id: str) -> bool:
    """Menghapus menu dari kios berdasarkan ``menu_id``."""
    init_db()
    fs = get_firestore_client()
    if fs is not None:
        doc_ref = fs.collection("menus").document(menu_id)
        if not doc_ref.get().exists:
            return False
        doc_ref.delete()
        clear_cache()
        return True

    menus = _get_store()["db_menus"]
    for idx, menu in enumerate(menus):
        if menu["id"] == menu_id:
            del menus[idx]
            return True
    return False
