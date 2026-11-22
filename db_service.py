"""Lapisan layanan data untuk GoFood Kancil (Queue Kantin Online).

Saat ini menggunakan penyimpanan sementara (``st.session_state`` saat berjalan di
Streamlit, atau fallback dictionary saat dijalankan terpisah) agar MVP Role
Pembeli dapat langsung dijalankan dan diuji tanpa menunggu setup database selesai.

Setiap fungsi memiliki catatan struktur query Supabase yang setara supaya rekan
tim dapat mengganti isi fungsi ini dengan ``supabase.table(...)`` tanpa mengubah
kode tampilan UI.
"""

from __future__ import annotations

import base64
from datetime import datetime
import hashlib
import html
from typing import Any
import uuid

STATUS_PREPARING = "Sedang Menyiapkan Pesanan"
STATUS_READY = "Pesanan Sudah Bisa Diambil"
VALID_ORDER_STATUSES = (STATUS_PREPARING, STATUS_READY)

_FALLBACK_STORE: dict[str, Any] = {}


def _get_store() -> Any:
    """Mengembalikan ``st.session_state`` saat aktif di runtime Streamlit,
    atau fallback dictionary lokal saat modul diuji secara standalone.
    """
    try:
        import streamlit as st

        if getattr(st, "runtime", None) is not None and st.runtime.exists():
            return st.session_state
    except Exception:
        pass
    return _FALLBACK_STORE


def generate_qris_svg_data_uri(
    merchant_name: str, nmid: str, accent_color: str = "#E11D48"
) -> str:
    """Membuat gambar kartu QRIS berbasis SVG XML untuk masing-masing kios.

    Streamlit ``st.image()`` mendukung rendering string XML ``<svg ...>`` secara
    langsung tanpa library pembuat gambar tambahan.
    """
    safe_name = html.escape(merchant_name)
    safe_nmid = html.escape(nmid)
    safe_color = html.escape(accent_color)

    # Pola matriks QR deterministik dari nama merchant + NMID agar tiap kios unik
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
    # Tiga kotak penanda sudut khas QR Code
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
        "QRIS GOFOOD KANCIL</text>"
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


def encode_uploaded_file(uploaded_file: Any) -> tuple[bytes, str]:
    """Mengambil bytes dan nama file dari objek ``st.file_uploader``."""
    return uploaded_file.getvalue(), uploaded_file.name


def bytes_to_base64_data_uri(data: bytes, filename: str) -> str:
    """Mengonversi bytes gambar bukti bayar menjadi Data URI Base64.

    Siap disimpan langsung ke kolom bertipe ``TEXT`` (``payment_proof``) di
    tabel ``orders`` Supabase tanpa perlu konfigurasi Storage Bucket terpisah.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def init_db() -> None:
    """Mengisi data awal kios, menu, dan daftar pesanan ke store jika belum ada."""
    store = _get_store()

    if "db_tenants" not in store:
        store["db_tenants"] = [
            {
                "id": "t1",
                "name": "Kantin Ayam Geprek Mas Budi",
                "emoji": "🍗",
                "pin": "1234",
                "description": "Spesialis ayam geprek sambal bawang, tahu tempe, dan es segar.",
                "is_open": True,
                "queue_prefix": "A",
                "nmid": "ID102030400001",
                "qris_svg": generate_qris_svg_data_uri(
                    "Ayam Geprek Mas Budi", "ID102030400001", "#DC2626"
                ),
            },
            {
                "id": "t2",
                "name": "Soto & Bakso Bu Sari",
                "emoji": "🍲",
                "pin": "1234",
                "description": "Soto ayam bening, bakso urat, dan minuman hangat/dingin.",
                "is_open": True,
                "queue_prefix": "B",
                "nmid": "ID102030400002",
                "qris_svg": generate_qris_svg_data_uri(
                    "Soto & Bakso Bu Sari", "ID102030400002", "#059669"
                ),
            },
            {
                "id": "t3",
                "name": "Mie Ayam & Nasgor Pakde",
                "emoji": "🍜",
                "pin": "1234",
                "description": "Mie ayam jamur, nasi goreng kampung, dan kwetiau goreng.",
                "is_open": False,
                "queue_prefix": "C",
                "nmid": "ID102030400003",
                "qris_svg": generate_qris_svg_data_uri(
                    "Mie Ayam Pakde", "ID102030400003", "#D97706"
                ),
            },
        ]

    if "db_menus" not in store:
        store["db_menus"] = [
            # Kios t1
            {
                "id": "m1",
                "tenant_id": "t1",
                "name": "Paket Ayam Geprek + Nasi",
                "price": 15000,
                "emoji": "🍗",
                "description": "Ayam krispi geprek sambal bawang level 1-5 + nasi hangat.",
                "is_available": True,
            },
            {
                "id": "m2",
                "tenant_id": "t1",
                "name": "Ayam Geprek Keju Mozarella",
                "price": 18000,
                "emoji": "🧀",
                "description": "Ayam geprek dengan lelehan keju gurih di atasnya.",
                "is_available": True,
            },
            {
                "id": "m3",
                "tenant_id": "t1",
                "name": "Indomie Goreng Telur Geprek",
                "price": 13000,
                "emoji": "🍜",
                "description": "Indomie goreng double + telur dadar dan suwiran ayam.",
                "is_available": False,
            },
            {
                "id": "m4",
                "tenant_id": "t1",
                "name": "Es Teh Manis Jumbo",
                "price": 4000,
                "emoji": "🧋",
                "description": "Es teh manis dingin penyegar jam makan siang.",
                "is_available": True,
            },
            # Kios t2
            {
                "id": "m5",
                "tenant_id": "t2",
                "name": "Soto Ayam Lamongan + Nasi",
                "price": 14000,
                "emoji": "🍲",
                "description": "Kuah soto gurih lengkap dengan koya, telur, dan suwiran ayam.",
                "is_available": True,
            },
            {
                "id": "m6",
                "tenant_id": "t2",
                "name": "Bakso Urat Komplit",
                "price": 16000,
                "emoji": "🥣",
                "description": "Bakso urat besar, 3 bakso halus, mie kuning, dan bihun.",
                "is_available": True,
            },
            {
                "id": "m7",
                "tenant_id": "t2",
                "name": "Tahu Goreng Isi (3 pcs)",
                "price": 6000,
                "emoji": "🥟",
                "description": "Tahu isi sayur renyah cocok untuk teman makan soto.",
                "is_available": False,
            },
            {
                "id": "m8",
                "tenant_id": "t2",
                "name": "Es Jeruk Peras Asli",
                "price": 5000,
                "emoji": "🍊",
                "description": "Jeruk peras segar tanpa pemanis buatan.",
                "is_available": True,
            },
            # Kios t3
            {
                "id": "m9",
                "tenant_id": "t3",
                "name": "Mie Ayam Bakso Spesial",
                "price": 15000,
                "emoji": "🍝",
                "description": "Mie kenyal dengan topping ayam kecap dan 2 bakso sapi.",
                "is_available": True,
            },
            {
                "id": "m10",
                "tenant_id": "t3",
                "name": "Nasi Goreng Kampung Telur",
                "price": 16000,
                "emoji": "🍛",
                "description": "Nasi goreng bumbu terasi ringan dengan telur mata sapi.",
                "is_available": True,
            },
            {
                "id": "m11",
                "tenant_id": "t3",
                "name": "Kwetiau Goreng Sapi",
                "price": 17000,
                "emoji": "🥘",
                "description": "Kwetiau goreng gurih dengan irisan daging dan sawi.",
                "is_available": False,
            },
            {
                "id": "m12",
                "tenant_id": "t3",
                "name": "Air Mineral Dingin 600ml",
                "price": 4000,
                "emoji": "💧",
                "description": "Air mineral kemasan botol dingin.",
                "is_available": True,
            },
        ]

    if "db_orders" not in store:
        store["db_orders"] = []


def get_tenants() -> list[dict[str, Any]]:
    """Mengambil seluruh daftar kios kantin.

    Supabase equivalent: ``supabase.table("tenants").select("*").execute().data``
    """
    init_db()
    return list(_get_store()["db_tenants"])


def get_tenant_by_id(tenant_id: str) -> dict[str, Any] | None:
    """Mengambil detail 1 kios berdasarkan ``tenant_id``.

    Supabase equivalent:
    ``supabase.table("tenants").select("*").eq("id", tenant_id).single().execute().data``
    """
    for tenant in get_tenants():
        if tenant["id"] == tenant_id:
            return tenant
    return None


def get_menus_by_tenant(tenant_id: str) -> list[dict[str, Any]]:
    """Mengambil daftar menu milik satu kios.

    Supabase equivalent:
    ``supabase.table("menus").select("*").eq("tenant_id", tenant_id).execute().data``
    """
    init_db()
    return [
        menu for menu in _get_store()["db_menus"] if menu["tenant_id"] == tenant_id
    ]


def create_order(
    buyer_id: str,
    buyer_name: str,
    buyer_npm: str,
    tenant_id: str,
    items: list[dict[str, Any]],
    notes: str,
    payment_proof_bytes: bytes,
    payment_filename: str,
) -> dict[str, Any]:
    """Membuat pesanan baru setelah bukti pembayaran QRIS diunggah.

    Status default otomatis diset ke ``STATUS_PREPARING`` ("Sedang Menyiapkan Pesanan"),
    dan nomor antrean di-generate berurutan per kios (mis. ``A-001``, ``B-001``).

    Supabase equivalent:
    ``supabase.table("orders").insert(order_payload).execute()``
    """
    init_db()
    tenant = get_tenant_by_id(tenant_id)
    if tenant is None:
        raise ValueError(f"Kios dengan id '{tenant_id}' tidak ditemukan.")
    if not items:
        raise ValueError("Daftar item pesanan tidak boleh kosong.")
    if not payment_proof_bytes:
        raise ValueError("Bukti pembayaran QRIS wajib diunggah.")

    store = _get_store()
    existing_tenant_orders = [
        o for o in store["db_orders"] if o["tenant_id"] == tenant_id
    ]
    next_seq = len(existing_tenant_orders) + 1
    queue_number = f"{tenant['queue_prefix']}-{next_seq:03d}"

    total_price = sum(int(item["price"]) * int(item["qty"]) for item in items)
    order: dict[str, Any] = {
        "id": f"ord-{uuid.uuid4().hex[:8]}",
        "queue_number": queue_number,
        "buyer_id": buyer_id,
        "buyer_name": buyer_name,
        "buyer_npm": buyer_npm,
        "tenant_id": tenant_id,
        "tenant_name": tenant["name"],
        "items": [dict(item) for item in items],
        "notes": notes.strip(),
        "pickup_method": "Ambil langsung di konter kios",
        "total_price": total_price,
        "payment_proof_bytes": payment_proof_bytes,
        "payment_proof_b64": bytes_to_base64_data_uri(
            payment_proof_bytes, payment_filename
        ),
        "payment_filename": payment_filename,
        "status": STATUS_PREPARING,
        "created_at": datetime.now().strftime("%d %b %Y, %H:%M WIB"),
    }
    store["db_orders"].append(order)
    return order


def get_buyer_orders(buyer_id: str) -> list[dict[str, Any]]:
    """Mengambil riwayat & antrean pesanan milik pembeli (terbaru di paling atas).

    Supabase equivalent:
    ``supabase.table("orders").select("*").eq("buyer_id", buyer_id).order("created_at", desc=True).execute().data``
    """
    init_db()
    orders = [
        o for o in _get_store()["db_orders"] if o["buyer_id"] == buyer_id
    ]
    return list(reversed(orders))


def get_all_orders() -> list[dict[str, Any]]:
    """Mengambil seluruh pesanan lintas kios (dipakai oleh panel simulasi penjual).

    Supabase equivalent:
    ``supabase.table("orders").select("*").order("created_at", desc=True).execute().data``
    """
    init_db()
    return list(reversed(_get_store()["db_orders"]))


def update_order_status(order_id: str, new_status: str) -> bool:
    """Memperbarui status pesanan (``Sedang Menyiapkan Pesanan`` / ``Pesanan Sudah Bisa Diambil``).

    Supabase equivalent:
    ``supabase.table("orders").update({"status": new_status}).eq("id", order_id).execute()``
    """
    if new_status not in VALID_ORDER_STATUSES:
        raise ValueError(f"Status '{new_status}' tidak valid.")

    init_db()
    for order in _get_store()["db_orders"]:
        if order["id"] == order_id:
            order["status"] = new_status
            return True
    return False


def toggle_tenant_open(tenant_id: str, is_open: bool) -> bool:
    """Mengubah status buka/tutup kios kantin.

    Supabase equivalent:
    ``supabase.table("tenants").update({"is_open": is_open}).eq("id", tenant_id).execute()``
    """
    init_db()
    for tenant in _get_store()["db_tenants"]:
        if tenant["id"] == tenant_id:
            tenant["is_open"] = bool(is_open)
            return True
    return False


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
    emoji: str = "🍽️",
    is_available: bool = True,
) -> dict[str, Any]:
    """Menambahkan menu baru ke daftar menu milik suatu kios.

    Supabase equivalent:
    ``supabase.table("menus").insert(menu_payload).execute()``
    """
    init_db()
    if get_tenant_by_id(tenant_id) is None:
        raise ValueError(f"Kios dengan id '{tenant_id}' tidak ditemukan.")

    clean_name, parsed_price = _validate_menu_fields(name, price)
    clean_emoji = emoji.strip() or "🍽️"
    new_menu: dict[str, Any] = {
        "id": f"m-{uuid.uuid4().hex[:6]}",
        "tenant_id": tenant_id,
        "name": clean_name,
        "price": parsed_price,
        "emoji": clean_emoji,
        "description": description.strip(),
        "is_available": bool(is_available),
    }
    _get_store()["db_menus"].append(new_menu)
    return new_menu


def update_menu(
    menu_id: str,
    name: str,
    price: int,
    description: str,
    emoji: str,
    is_available: bool,
) -> bool:
    """Memperbarui detail menu yang sudah ada.

    Supabase equivalent:
    ``supabase.table("menus").update(payload).eq("id", menu_id).execute()``
    """
    clean_name, parsed_price = _validate_menu_fields(name, price)
    clean_emoji = emoji.strip() or "🍽️"

    init_db()
    for menu in _get_store()["db_menus"]:
        if menu["id"] == menu_id:
            menu["name"] = clean_name
            menu["price"] = parsed_price
            menu["description"] = description.strip()
            menu["emoji"] = clean_emoji
            menu["is_available"] = bool(is_available)
            return True
    return False


def toggle_menu_availability(menu_id: str, is_available: bool) -> bool:
    """Mengubah status ketersediaan stok menu (Tersedia / Habis).

    Supabase equivalent:
    ``supabase.table("menus").update({"is_available": is_available}).eq("id", menu_id).execute()``
    """
    init_db()
    for menu in _get_store()["db_menus"]:
        if menu["id"] == menu_id:
            menu["is_available"] = bool(is_available)
            return True
    return False


def delete_menu(menu_id: str) -> bool:
    """Menghapus menu dari kios berdasarkan ``menu_id``.

    Supabase equivalent:
    ``supabase.table("menus").delete().eq("id", menu_id).execute()``
    """
    init_db()
    menus = _get_store()["db_menus"]
    for idx, menu in enumerate(menus):
        if menu["id"] == menu_id:
            del menus[idx]
            return True
    return False


def get_tenant_orders(tenant_id: str) -> list[dict[str, Any]]:
    """Mengambil antrean pesanan milik satu kios secara berurutan (FIFO).

    Pesanan yang masuk lebih awal tampil di paling atas untuk diproses duluan.

    Supabase equivalent:
    ``supabase.table("orders").select("*").eq("tenant_id", tenant_id).order("created_at", desc=False).execute().data``
    """
    init_db()
    return [
        o for o in _get_store()["db_orders"] if o["tenant_id"] == tenant_id
    ]
