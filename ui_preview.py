"""Sandbox UI/UX mandiri untuk GoFood Kancil (Tema Putih-Abu Minimalis).

File ini sengaja dipisahkan sepenuhnya dari ``main.py``, ``db_service.py``, dan
``auth_service.py`` supaya eksplorasi dan revisi desain dapat dilakukan dengan
cepat menggunakan data contoh tanpa menyentuh database Firebase atau SSO UI.

Jalankan dengan:
    .\\.venv\\Scripts\\streamlit run ui_preview.py
"""

from __future__ import annotations

import base64
from functools import lru_cache
import html
from pathlib import Path
from typing import Any

import streamlit as st

PROJECT_DIR = Path(__file__).resolve().parent

SCREEN_STOREFRONT = "Etalase & Menu"
SCREEN_CART = "Keranjang & QRIS"
SCREEN_QUEUE = "Antrean Saya"
SCREEN_SELLER = "Dashboard Penjual"
SCREEN_LOGIN = "Halaman Masuk"

STATUS_PENDING = "Menunggu Konfirmasi Pembayaran"
STATUS_PREP = "Sedang Menyiapkan Pesanan"
STATUS_READY = "Pesanan Sudah Bisa Diambil"
STATUS_REJECT = "Pembayaran Ditolak"


def format_rp(amount: int) -> str:
    """Memformat integer menjadi nominal Rupiah (contoh: Rp15.000)."""
    return f"Rp{amount:,}".replace(",", ".")


@lru_cache(maxsize=64)
def _resolve_image_src(image_ref: str) -> str:
    """Mengubah path file lokal menjadi data URI agar bisa dipakai di tag <img>.

    Pada aplikasi final, nilai ini berasal dari foto yang diunggah penjual.
    URL http(s) dan data URI dikembalikan apa adanya.
    """
    if not image_ref or image_ref.startswith(("http://", "https://", "data:")):
        return image_ref
    file_path = PROJECT_DIR / image_ref
    if not file_path.is_file():
        return ""
    mime = "image/png" if file_path.suffix.lower() == ".png" else "image/jpeg"
    encoded = base64.b64encode(file_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _placeholder_svg_uri(label: str) -> str:
    """Fallback gambar monokrom bersih jika koneksi foto eksternal terputus."""
    safe = html.escape(label)
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="400" '
        'viewBox="0 0 640 400">'
        '<rect width="640" height="400" fill="#EBEBEF"/>'
        '<rect x="260" y="135" width="120" height="90" rx="14" '
        'fill="none" stroke="#A1A1AA" stroke-width="3"/>'
        '<circle cx="295" cy="168" r="10" fill="#A1A1AA"/>'
        '<path d="M272 212 L312 178 L340 202 L358 188 L368 212 Z" fill="#A1A1AA"/>'
        '<text x="320" y="262" text-anchor="middle" fill="#71717A" '
        'font-family="-apple-system, BlinkMacSystemFont, Inter, sans-serif" '
        f'font-size="16" font-weight="500">{safe}</text>'
        "</svg>"
    )
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def _monochrome_qris_svg(merchant_name: str, nmid: str) -> str:
    """Kartu QRIS monokrom putih-abu-hitam selaras dengan tema minimalis."""
    safe_name = html.escape(merchant_name)
    safe_nmid = html.escape(nmid)
    cells: list[str] = []
    origins = [(65, 76), (164, 76), (65, 175)]
    for ox, oy in origins:
        cells.append(
            f'<rect x="{ox}" y="{oy}" width="30" height="30" rx="4" '
            'fill="none" stroke="#18181B" stroke-width="4"/>'
        )
        cells.append(
            f'<rect x="{ox + 8}" y="{oy + 8}" width="14" height="14" rx="2" fill="#18181B"/>'
        )
    pattern = [
        (106, 78), (118, 78), (142, 78), (106, 90), (130, 90), (142, 90),
        (118, 102), (130, 102), (67, 118), (91, 118), (115, 118), (139, 118),
        (163, 118), (175, 118), (79, 130), (103, 130), (127, 130), (151, 130),
        (183, 130), (67, 142), (115, 142), (139, 142), (163, 142), (91, 154),
        (127, 154), (151, 154), (175, 154), (106, 178), (130, 178), (154, 178),
        (178, 178), (118, 190), (142, 190), (166, 190), (106, 198), (154, 198),
    ]
    for px, py in pattern:
        cells.append(
            f'<rect x="{px}" y="{py}" width="9" height="9" rx="1.5" fill="#18181B"/>'
        )
    joined = "".join(cells)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="260" height="284" viewBox="0 0 260 284">'
        '<rect x="1" y="1" width="258" height="282" rx="16" fill="#FFFFFF" stroke="#E4E4E7" stroke-width="1.5"/>'
        '<rect x="1" y="1" width="258" height="42" rx="15" fill="#18181B"/>'
        '<rect x="1" y="28" width="258" height="15" fill="#18181B"/>'
        '<text x="130" y="27" text-anchor="middle" fill="#FFFFFF" '
        'font-family="-apple-system, Inter, sans-serif" font-size="13" font-weight="600" letter-spacing="0.06em">'
        "QRIS PEMBAYARAN KIOS</text>"
        '<text x="130" y="61" text-anchor="middle" fill="#18181B" '
        'font-family="-apple-system, Inter, sans-serif" font-size="12" font-weight="600">'
        f"{safe_name}</text>"
        f"{joined}"
        '<text x="130" y="232" text-anchor="middle" fill="#71717A" '
        'font-family="monospace" font-size="10">'
        f"NMID: {safe_nmid}</text>"
        '<rect x="36" y="244" width="188" height="26" rx="8" fill="#F4F4F5"/>'
        '<text x="130" y="261" text-anchor="middle" fill="#3F3F46" '
        'font-family="-apple-system, Inter, sans-serif" font-size="10.5" font-weight="500">'
        "Scan QRIS &amp; unggah bukti bayar</text>"
        "</svg>"
    )


def inject_minimalist_css() -> None:
    """Menyuntikkan CSS minimalis bertema putih dan abu-abu ala GoFood clean."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif;
            color: #18181B;
        }

        /* Sembunyikan dekorasi pelangi atas & rapikan lebar halaman */
        [data-testid="stDecoration"] { display: none; }
        .block-container {
            max-width: 1060px !important;
            padding-top: 3.2rem !important;
            padding-bottom: 7rem !important;
        }

        /* Navigasi melayang menempel di bawah layar (selalu 1 baris) */
        .st-key-bottom_nav {
            position: fixed;
            bottom: 18px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 1000;
            width: min(640px, calc(100vw - 24px));
            background: rgba(255, 255, 255, 0.94);
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            border: 1px solid #E4E4E7;
            border-radius: 999px;
            padding: 6px 8px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
            overflow-x: auto;
        }
        .st-key-bottom_nav [data-testid="stVerticalBlockBorderWrapper"] {
            border: none !important;
            box-shadow: none !important;
        }
        .st-key-bottom_nav [data-baseweb="button-group"] {
            flex-wrap: nowrap !important;
        }
        .st-key-bottom_nav button {
            white-space: nowrap !important;
            font-size: 13px !important;
            padding-left: 12px !important;
            padding-right: 12px !important;
            box-shadow: none !important;
        }
        .st-key-bottom_nav button:focus,
        .st-key-bottom_nav button:focus-visible {
            outline: none !important;
            box-shadow: none !important;
        }

        /* Teks status antrean besar & deskriptif */
        .gf-status-text {
            font-size: 22px;
            font-weight: 650;
            letter-spacing: -0.02em;
            color: #18181B;
            line-height: 1.3;
            margin: 14px 0 2px 0;
        }
        .gf-status-sub {
            font-size: 14px;
            color: #71717A;
            margin: 0 0 4px 0;
        }
        .gf-status-text.is-muted { color: #52525B; }

        /* Kartu permukaan putih dengan border abu tipis & bayangan lembut */
        [data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #FFFFFF !important;
            border: 1px solid #E4E4E7 !important;
            border-radius: 16px !important;
            box-shadow: 0 1px 4px rgba(0, 0, 0, 0.03) !important;
            padding: 0.25rem !important;
            transition: border-color 0.15s ease, box-shadow 0.15s ease;
        }
        [data-testid="stVerticalBlockBorderWrapper"]:hover {
            border-color: #D4D4D8 !important;
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.05) !important;
        }

        /* Tombol utama hitam karbon & tombol sekunder putih-abu */
        .stButton > button[kind="primary"],
        .stFormSubmitButton > button[kind="primary"] {
            background-color: #18181B !important;
            color: #FFFFFF !important;
            border: 1px solid #18181B !important;
            border-radius: 10px !important;
            font-weight: 500 !important;
            height: 2.55rem !important;
            letter-spacing: -0.01em;
        }
        .stButton > button[kind="primary"]:hover,
        .stFormSubmitButton > button[kind="primary"]:hover {
            background-color: #27272A !important;
            border-color: #27272A !important;
        }
        .stButton > button[kind="secondary"],
        .stFormSubmitButton > button[kind="secondary"] {
            background-color: #FFFFFF !important;
            color: #18181B !important;
            border: 1px solid #E4E4E7 !important;
            border-radius: 10px !important;
            font-weight: 500 !important;
            height: 2.55rem !important;
        }
        .stButton > button[kind="secondary"]:hover,
        .stFormSubmitButton > button[kind="secondary"]:hover {
            background-color: #F4F4F5 !important;
            border-color: #D4D4D8 !important;
        }
        .stButton > button:disabled {
            background-color: #F4F4F5 !important;
            color: #A1A1AA !important;
            border-color: #E4E4E7 !important;
        }

        /* Komponen kartu gambar seragam ala GoFood */
        .gf-card-media {
            position: relative;
            width: 100%;
            aspect-ratio: 16 / 10;
            border-radius: 12px;
            overflow: hidden;
            background-color: #EBEBEF;
            margin-bottom: 0.65rem;
        }
        .gf-card-media img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }
        .gf-card-media.is-dimmed img {
            filter: grayscale(100%);
            opacity: 0.48;
        }
        .gf-badge {
            display: inline-block;
            padding: 3px 9px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.02em;
            line-height: 1.3;
        }
        .gf-badge-open {
            background-color: #18181B;
            color: #FFFFFF;
        }
        .gf-badge-closed {
            background-color: #F4F4F5;
            color: #71717A;
            border: 1px solid #E4E4E7;
        }
        .gf-badge-overlay {
            position: absolute;
            top: 10px;
            left: 10px;
            backdrop-filter: blur(8px);
        }
        .gf-eta-overlay {
            position: absolute;
            bottom: 10px;
            right: 10px;
            background: rgba(255, 255, 255, 0.92);
            color: #18181B;
            padding: 3px 9px;
            border-radius: 8px;
            font-size: 11px;
            font-weight: 600;
            border: 1px solid rgba(0,0,0,0.06);
        }
        .gf-title {
            font-size: 15.5px;
            font-weight: 600;
            color: #18181B;
            margin: 0 0 3px 0;
            letter-spacing: -0.015em;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .gf-desc {
            font-size: 13px;
            color: #71717A;
            margin: 0 0 10px 0;
            line-height: 1.42;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            min-height: 36px;
        }
        .gf-meta-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 12.5px;
            color: #52525B;
            margin-bottom: 10px;
        }
        .gf-price {
            font-size: 15px;
            font-weight: 700;
            color: #18181B;
            letter-spacing: -0.01em;
        }
        .gf-surface-note {
            background-color: #F4F4F5;
            border: 1px solid #E4E4E7;
            border-radius: 12px;
            padding: 12px 15px;
            font-size: 13px;
            color: #3F3F46;
            margin-bottom: 12px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _init_preview_data() -> None:
    """Menginisialisasi data dummy foto toko, foto menu, keranjang, dan pesanan."""
    if "pv_tenants" not in st.session_state:
        st.session_state["pv_tenants"] = [
            {
                "id": "t1",
                "name": "Ayam Geprek Mas Budi",
                "category": "Ayam & Sambal",
                "eta": "8-12 mnt",
                "price_range": "Mulai Rp4.000",
                "description": "Ayam krispi sambal bawang ulek dadakan, nasi hangat, dan minuman dingin.",
                "is_open": True,
                "nmid": "ID102030400001",
                "image_url": "assets/demo/t1.jpg",
            },
            {
                "id": "t2",
                "name": "Soto & Bakso Bu Sari",
                "category": "Berkuah & Bakso",
                "eta": "5-10 mnt",
                "price_range": "Mulai Rp5.000",
                "description": "Kuah kaldu ayam kampung hangat, bakso urat sapi asli, dan gorengan renyah.",
                "is_open": True,
                "nmid": "ID102030400002",
                "image_url": "assets/demo/t2.jpg",
            },
            {
                "id": "t3",
                "name": "Mie Ayam & Nasgor Pakde",
                "category": "Mie & Nasi Goreng",
                "eta": "10-15 mnt",
                "price_range": "Mulai Rp4.000",
                "description": "Mie ayam jamur racikan sendiri, nasi goreng kampung, dan kwetiau sapi.",
                "is_open": False,
                "nmid": "ID102030400003",
                "image_url": "assets/demo/t3.jpg",
            },
        ]

    if "pv_menus" not in st.session_state:
        st.session_state["pv_menus"] = [
            {
                "id": "m1",
                "tenant_id": "t1",
                "name": "Paket Ayam Geprek Sambal Bawang",
                "price": 15000,
                "description": "Ayam goreng tepung krispi digeprek sambal bawang segar plus nasi putih hangat.",
                "is_available": True,
                "image_url": "assets/demo/m1.jpg",
            },
            {
                "id": "m2",
                "tenant_id": "t1",
                "name": "Ayam Geprek Keju Leleh",
                "price": 18000,
                "description": "Ayam geprek pedas gurih dengan lapisan keju mozarella leleh di atasnya.",
                "is_available": True,
                "image_url": "assets/demo/m2.jpg",
            },
            {
                "id": "m3",
                "tenant_id": "t1",
                "name": "Mie Goreng Spesial Telur",
                "price": 13000,
                "description": "Mie goreng bumbu gurih disajikan dengan telur mata sapi setengah matang.",
                "is_available": False,
                "image_url": "assets/demo/m3.jpg",
            },
            {
                "id": "m4",
                "tenant_id": "t1",
                "name": "Es Teh Melati Dingin",
                "price": 4000,
                "description": "Teh melati seduh segar dengan es batu kristal ukuran gelas besar.",
                "is_available": True,
                "image_url": "assets/demo/m4.jpg",
            },
            {
                "id": "m5",
                "tenant_id": "t2",
                "name": "Soto Ayam Lamongan Koya",
                "price": 14000,
                "description": "Soto ayam bening tabur bubuk koya gurih, suwiran ayam, telur, dan nasi.",
                "is_available": True,
                "image_url": "assets/demo/m5.jpg",
            },
            {
                "id": "m6",
                "tenant_id": "t2",
                "name": "Bakso Urat Sapi Komplit",
                "price": 16000,
                "description": "Satu bakso urat besar, tiga bakso halus, bihun, mie kuning, dan sawi hijau.",
                "is_available": True,
                "image_url": "assets/demo/m6.jpg",
            },
            {
                "id": "m7",
                "tenant_id": "t2",
                "name": "Tahu Crispy Lada Garam",
                "price": 7000,
                "description": "Potongan tahu putih goreng tepung renyah dengan taburan bawang putih.",
                "is_available": False,
                "image_url": "assets/demo/m7.jpg",
            },
            {
                "id": "m8",
                "tenant_id": "t2",
                "name": "Es Jeruk Peras Murni",
                "price": 5000,
                "description": "Perasan jeruk manis segar dingin tanpa tambahan pemanis buatan.",
                "is_available": True,
                "image_url": "assets/demo/m8.jpg",
            },
            {
                "id": "m9",
                "tenant_id": "t3",
                "name": "Mie Ayam Jamur Spesial",
                "price": 15000,
                "description": "Mie telur kenyal dengan potongan ayam kecap jamur dan pangsit rebus.",
                "is_available": True,
                "image_url": "assets/demo/m9.jpg",
            },
            {
                "id": "m10",
                "tenant_id": "t3",
                "name": "Nasi Goreng Kampung",
                "price": 16000,
                "description": "Nasi goreng bumbu rempah tradisional dengan suwiran ayam dan kerupuk.",
                "is_available": True,
                "image_url": "assets/demo/m10.jpg",
            },
        ]

    if "pv_selected_tenant" not in st.session_state:
        st.session_state["pv_selected_tenant"] = None

    if "pv_cart" not in st.session_state:
        st.session_state["pv_cart"] = {
            "tenant_id": "t1",
            "items": {
                "m1": {
                    "menu_id": "m1",
                    "name": "Paket Ayam Geprek Sambal Bawang",
                    "price": 15000,
                    "qty": 1,
                    "image_url": "assets/demo/m1.jpg",
                },
                "m4": {
                    "menu_id": "m4",
                    "name": "Es Teh Melati Dingin",
                    "price": 4000,
                    "qty": 1,
                    "image_url": "assets/demo/m4.jpg",
                },
            },
        }

    if "pv_orders" not in st.session_state:
        st.session_state["pv_orders"] = [
            {
                "id": "ord-demo-1",
                "queue_number": "A-004",
                "tenant_id": "t1",
                "tenant_name": "Ayam Geprek Mas Budi",
                "buyer_name": "Hilmo",
                "buyer_npm": "2606123456",
                "created_at": "Hari ini, 12:05 WIB",
                "items": [
                    {"name": "Paket Ayam Geprek Sambal Bawang", "price": 15000, "qty": 1},
                    {"name": "Es Teh Melati Dingin", "price": 4000, "qty": 1},
                ],
                "notes": "Sambal dipisah, nasi sedikit saja.",
                "total_price": 19000,
                "status": STATUS_PREP,
                "rejection_reason": "",
            },
            {
                "id": "ord-demo-2",
                "queue_number": "A-005",
                "tenant_id": "t1",
                "tenant_name": "Ayam Geprek Mas Budi",
                "buyer_name": "Azzam",
                "buyer_npm": "2606654321",
                "created_at": "Hari ini, 12:08 WIB",
                "items": [
                    {"name": "Ayam Geprek Keju Leleh", "price": 18000, "qty": 1},
                ],
                "notes": "",
                "total_price": 18000,
                "status": STATUS_PENDING,
                "rejection_reason": "",
            },
        ]

    if "pv_screen" not in st.session_state:
        st.session_state["pv_screen"] = SCREEN_STOREFRONT

    if "pv_seller_pending" not in st.session_state:
        st.session_state["pv_seller_pending"] = None


def _render_media_html(
    image_url: str,
    alt_label: str,
    dimmed: bool = False,
    badge_text: str | None = None,
    badge_open: bool = True,
    eta_text: str | None = None,
) -> str:
    """Membangun blok HTML gambar rasio 16:10 seragam dengan fallback monokrom."""
    fallback_uri = _placeholder_svg_uri(alt_label)
    safe_url = html.escape(_resolve_image_src(image_url) or fallback_uri)
    safe_alt = html.escape(alt_label)
    dim_cls = " is-dimmed" if dimmed else ""

    overlay_parts: list[str] = []
    if badge_text:
        b_cls = "gf-badge-open" if badge_open else "gf-badge-closed"
        overlay_parts.append(
            f'<span class="gf-badge {b_cls} gf-badge-overlay">{html.escape(badge_text)}</span>'
        )
    if eta_text:
        overlay_parts.append(
            f'<span class="gf-eta-overlay">{html.escape(eta_text)}</span>'
        )

    overlays = "".join(overlay_parts)
    return (
        f'<div class="gf-card-media{dim_cls}">'
        f'<img src="{safe_url}" alt="{safe_alt}" '
        f"onerror=\"this.onerror=null;this.src='{fallback_uri}';\" />"
        f"{overlays}"
        "</div>"
    )


def _cart_add(tenant_id: str, menu: dict[str, Any]) -> None:
    cart = st.session_state["pv_cart"]
    if cart["tenant_id"] != tenant_id:
        cart["tenant_id"] = tenant_id
        cart["items"] = {}
    mid = menu["id"]
    if mid in cart["items"]:
        cart["items"][mid]["qty"] += 1
    else:
        cart["items"][mid] = {
            "menu_id": mid,
            "name": menu["name"],
            "price": int(menu["price"]),
            "qty": 1,
            "image_url": menu.get("image_url", ""),
        }


def _cart_delta(menu_id: str, delta: int) -> None:
    cart = st.session_state["pv_cart"]
    if menu_id not in cart["items"]:
        return
    new_q = cart["items"][menu_id]["qty"] + delta
    if new_q <= 0:
        del cart["items"][menu_id]
    else:
        cart["items"][menu_id]["qty"] = new_q
    if not cart["items"]:
        cart["tenant_id"] = None


# ---------------------------------------------------------------------------
# Layar 1: Etalase Kios & Menu Makanan (Gaya GoFood Putih-Abu)
# ---------------------------------------------------------------------------


def _render_Floating_cart_bar() -> None:
    """Bar ringkas ala GoFood ketika ada item aktif di dalam keranjang."""
    cart = st.session_state["pv_cart"]
    if not cart["items"] or not cart["tenant_id"]:
        return

    qty_sum = sum(i["qty"] for i in cart["items"].values())
    price_sum = sum(i["qty"] * i["price"] for i in cart["items"].values())
    tenants = {t["id"]: t for t in st.session_state["pv_tenants"]}
    t_name = tenants.get(cart["tenant_id"], {}).get("name", "Kios")

    with st.container(border=True):
        c_left, c_right = st.columns([3.2, 1.2])
        with c_left:
            st.markdown(
                f"**{qty_sum} item di keranjang** · **{format_rp(price_sum)}**  \n"
                f"<span style='font-size:12.5px;color:#71717A;'>Dari {html.escape(t_name)}</span>",
                unsafe_allow_html=True,
            )
        with c_right:
            if st.button(
                "Lanjut ke Keranjang",
                key="bar_goto_cart",
                type="primary",
                use_container_width=True,
            ):
                st.session_state["pv_screen"] = SCREEN_CART
                st.rerun()


def _render_storefront_screen() -> None:
    tenants = st.session_state["pv_tenants"]
    menus_all = st.session_state["pv_menus"]
    selected_tid = st.session_state["pv_selected_tenant"]

    _render_Floating_cart_bar()

    # Tahap A: Grid Pilihan Toko dengan Foto Toko
    if selected_tid is None:
        search_col, filter_col = st.columns([2.6, 1.4])
        with search_col:
            query = st.text_input(
                "Cari kios atau makanan",
                placeholder="Cari ayam geprek, soto, mie...",
                label_visibility="collapsed",
                key="pv_search_query",
            )
        with filter_col:
            only_open = st.segmented_control(
                "Filter Buka",
                options=["Semua Kios", "Sedang Buka"],
                default="Semua Kios",
                required=True,
                label_visibility="collapsed",
                width="stretch",
                key="pv_open_filter",
            )

        st.markdown("#### Pilihan Kios Kantin")

        q_lower = query.strip().lower()
        visible_tenants = []
        for t in tenants:
            if only_open == "Sedang Buka" and not t["is_open"]:
                continue
            t_menus = [m for m in menus_all if m["tenant_id"] == t["id"]]
            if q_lower:
                in_tenant = q_lower in t["name"].lower() or q_lower in t["category"].lower()
                in_menu = any(q_lower in m["name"].lower() for m in t_menus)
                if not (in_tenant or in_menu):
                    continue
            visible_tenants.append(t)

        if not visible_tenants:
            st.markdown(
                '<div class="gf-surface-note">Tidak ada kios yang cocok dengan pencarianmu.</div>',
                unsafe_allow_html=True,
            )
            return

        cols = st.columns(3)
        for idx, tenant in enumerate(visible_tenants):
            t_menus = [m for m in menus_all if m["tenant_id"] == tenant["id"]]
            avail = sum(1 for m in t_menus if m["is_available"])
            is_open = bool(tenant["is_open"])

            with cols[idx % 3]:
                with st.container(border=True):
                    st.markdown(
                        _render_media_html(
                            tenant["image_url"],
                            tenant["name"],
                            dimmed=not is_open,
                            badge_text="BUKA" if is_open else "TUTUP",
                            badge_open=is_open,
                            eta_text=tenant["eta"] if is_open else None,
                        ),
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f'<p class="gf-title">{html.escape(tenant["name"])}</p>'
                        f'<p class="gf-desc">{html.escape(tenant["description"])}</p>'
                        f'<div class="gf-meta-row">'
                        f'<span>{html.escape(tenant["category"])}</span>'
                        f'<span>{avail}/{len(t_menus)} tersedia</span>'
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "Lihat Menu",
                        key=f"pv_open_{tenant['id']}",
                        type="primary" if is_open else "secondary",
                        use_container_width=True,
                    ):
                        st.session_state["pv_selected_tenant"] = tenant["id"]
                        st.rerun()
        return

    # Tahap B: Halaman Kios & Grid Menu Makanan dengan Foto Makanan
    tenant_map = {t["id"]: t for t in tenants}
    tenant = tenant_map.get(selected_tid)
    if tenant is None:
        st.session_state["pv_selected_tenant"] = None
        st.rerun()
        return

    if st.button("Kembali ke Semua Kios", key="pv_back_tenants"):
        st.session_state["pv_selected_tenant"] = None
        st.rerun()

    # Header Kios bergaya GoFood Merchant Header
    with st.container(border=True):
        h_img, h_info = st.columns([1.1, 2.9])
        with h_img:
            st.markdown(
                _render_media_html(
                    tenant["image_url"],
                    tenant["name"],
                    dimmed=not tenant["is_open"],
                ),
                unsafe_allow_html=True,
            )
        with h_info:
            badge_cls = "gf-badge-open" if tenant["is_open"] else "gf-badge-closed"
            badge_lbl = "BUKA" if tenant["is_open"] else "TUTUP SEMENTARA"
            st.markdown(
                f'<span class="gf-badge {badge_cls}">{badge_lbl}</span>'
                f'<h3 style="margin:8px 0 4px 0;font-weight:700;letter-spacing:-0.02em;">'
                f'{html.escape(tenant["name"])}</h3>'
                f'<p style="color:#71717A;font-size:13.5px;margin:0 0 8px 0;">'
                f'{html.escape(tenant["description"])}</p>'
                f'<p style="color:#52525B;font-size:12.5px;margin:0;">'
                f'{html.escape(tenant["category"])} &nbsp;·&nbsp; '
                f'Estimasi siap {html.escape(tenant["eta"])} &nbsp;·&nbsp; '
                f"Ambil di konter kios</p>",
                unsafe_allow_html=True,
            )

    cart = st.session_state["pv_cart"]
    locked_other = (
        cart["tenant_id"] is not None
        and cart["tenant_id"] != tenant["id"]
        and bool(cart["items"])
    )
    if locked_other:
        other_name = tenant_map.get(cart["tenant_id"], {}).get("name", "kios lain")
        st.markdown(
            f'<div class="gf-surface-note">'
            f"Keranjangmu masih berisi menu dari <b>{html.escape(other_name)}</b>. "
            "Menambahkan menu di bawah akan mengganti isi keranjang ke kios ini."
            "</div>",
            unsafe_allow_html=True,
        )

    st.markdown("#### Daftar Menu")
    t_menus = [m for m in menus_all if m["tenant_id"] == tenant["id"]]
    m_cols = st.columns(3)
    for idx, menu in enumerate(t_menus):
        in_stock = bool(menu["is_available"])
        can_order = bool(tenant["is_open"]) and in_stock
        qty_in_cart = (
            cart["items"].get(menu["id"], {}).get("qty", 0)
            if cart["tenant_id"] == tenant["id"]
            else 0
        )

        with m_cols[idx % 3]:
            with st.container(border=True):
                st.markdown(
                    _render_media_html(
                        menu["image_url"],
                        menu["name"],
                        dimmed=not in_stock,
                        badge_text=None if in_stock else "HABIS",
                        badge_open=False,
                    ),
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<p class="gf-title">{html.escape(menu["name"])}</p>'
                    f'<p class="gf-desc">{html.escape(menu["description"])}</p>'
                    f'<div class="gf-meta-row">'
                    f'<span class="gf-price">{format_rp(int(menu["price"]))}</span>'
                    f'<span>{"Tersedia" if in_stock else "Stok habis"}</span>'
                    f"</div>",
                    unsafe_allow_html=True,
                )

                if qty_in_cart > 0 and can_order:
                    s_dec, s_num, s_inc = st.columns([1, 1.2, 1])
                    with s_dec:
                        if st.button(
                            "-",
                            key=f"pv_mdec_{menu['id']}",
                            use_container_width=True,
                        ):
                            _cart_delta(menu["id"], -1)
                            st.rerun()
                    with s_num:
                        st.markdown(
                            f"<div style='text-align:center;padding-top:7px;font-weight:600;'>{qty_in_cart}</div>",
                            unsafe_allow_html=True,
                        )
                    with s_inc:
                        if st.button(
                            "+",
                            key=f"pv_minc_{menu['id']}",
                            type="primary",
                            use_container_width=True,
                        ):
                            _cart_delta(menu["id"], 1)
                            st.rerun()
                else:
                    btn_text = "Tambah" if in_stock else "Habis"
                    if st.button(
                        btn_text,
                        key=f"pv_madd_{menu['id']}",
                        type="primary" if can_order else "secondary",
                        disabled=not can_order,
                        use_container_width=True,
                    ):
                        _cart_add(tenant["id"], menu)
                        st.rerun()


# ---------------------------------------------------------------------------
# Layar 2: Keranjang & Pembayaran QRIS
# ---------------------------------------------------------------------------


def _render_cart_screen() -> None:
    cart = st.session_state["pv_cart"]
    tenants = {t["id"]: t for t in st.session_state["pv_tenants"]}

    if not cart["items"] or not cart["tenant_id"]:
        with st.container(border=True):
            st.markdown("#### Keranjang Belanja Kosong")
            st.caption("Belum ada makanan yang dipilih dari etalase kantin.")
            if st.button("Jelajahi Etalase Kantin", type="primary"):
                st.session_state["pv_screen"] = SCREEN_STOREFRONT
                st.rerun()
        return

    tenant = tenants[cart["tenant_id"]]
    left_col, right_col = st.columns([1.45, 1.05])

    total_price = 0
    with left_col:
        with st.container(border=True):
            h1, h2 = st.columns([2.8, 1.2])
            with h1:
                st.markdown(f"#### {tenant['name']}")
                st.caption("Pengambilan langsung di konter kios")
            with h2:
                if st.button("Kosongkan", use_container_width=True):
                    st.session_state["pv_cart"] = {"tenant_id": None, "items": {}}
                    st.rerun()

            st.divider()
            for mid, item in list(cart["items"].items()):
                qty = int(item["qty"])
                sub = int(item["price"]) * qty
                total_price += sub

                r_info, r_ctrl = st.columns([2.4, 1.5])
                with r_info:
                    st.markdown(f"**{item['name']}**")
                    st.caption(f"{format_rp(int(item['price']))}  ·  Subtotal {format_rp(sub)}")
                with r_ctrl:
                    b1, b2, b3 = st.columns([1, 1, 1])
                    with b1:
                        if st.button("-", key=f"c_dec_{mid}", use_container_width=True):
                            _cart_delta(mid, -1)
                            st.rerun()
                    with b2:
                        st.markdown(
                            f"<div style='text-align:center;padding-top:7px;font-weight:600;'>{qty}</div>",
                            unsafe_allow_html=True,
                        )
                    with b3:
                        if st.button("+", key=f"c_inc_{mid}", use_container_width=True):
                            _cart_delta(mid, 1)
                            st.rerun()

            st.divider()
            notes = st.text_input(
                "Catatan untuk penjual (opsional)",
                placeholder="Contoh: Sambal dipisah, tidak pakai daun bawang...",
                key="pv_checkout_notes",
            )

    with right_col:
        with st.container(border=True):
            st.markdown("#### Pembayaran QRIS")
            st.markdown(
                f'<div class="gf-meta-row" style="margin-top:4px;">'
                f'<span>Total Tagihan</span>'
                f'<span style="font-size:18px;font-weight:700;color:#18181B;">{format_rp(total_price)}</span>'
                f"</div>",
                unsafe_allow_html=True,
            )
            st.image(
                _monochrome_qris_svg(tenant["name"], tenant["nmid"]),
                width=240,
            )
            uploaded = st.file_uploader(
                "Unggah bukti pembayaran (PNG / JPG)",
                type=["png", "jpg", "jpeg"],
                key="pv_proof_upload",
            )
            if st.button(
                "Kirim Bukti & Buat Pesanan",
                type="primary",
                disabled=uploaded is None,
                use_container_width=True,
            ):
                seq = len(st.session_state["pv_orders"]) + 4
                st.session_state["pv_orders"].insert(
                    0,
                    {
                        "id": f"ord-demo-{seq}",
                        "queue_number": f"A-{seq:03d}",
                        "tenant_id": tenant["id"],
                        "tenant_name": tenant["name"],
                        "buyer_name": "Hilmo",
                        "buyer_npm": "2606123456",
                        "created_at": "Baru saja",
                        "items": [
                            {"name": i["name"], "price": i["price"], "qty": i["qty"]}
                            for i in cart["items"].values()
                        ],
                        "notes": notes,
                        "total_price": total_price,
                        "status": STATUS_PENDING,
                        "rejection_reason": "",
                    },
                )
                st.session_state["pv_cart"] = {"tenant_id": None, "items": {}}
                st.session_state["pv_screen"] = SCREEN_QUEUE
                st.rerun()
            if uploaded is None:
                st.caption("Unggah tangkapan layar pembayaran QRIS untuk mengaktifkan tombol pesan.")


# ---------------------------------------------------------------------------
# Layar 3: Live Queue & Status Antrean Minimalis
# ---------------------------------------------------------------------------


def _render_status_text_html(status: str, reason: str = "") -> str:
    """Merender status pesanan sebagai teks deskriptif besar tanpa persentase."""
    headline, sub = {
        STATUS_PENDING: (
            "Pembayaran sedang dikonfirmasi",
            "Penjual sedang memeriksa bukti pembayaran yang kamu kirim.",
        ),
        STATUS_PREP: (
            "Pesanan sedang disiapkan",
            "Pembayaran sudah dikonfirmasi, kios sedang menyiapkan pesananmu.",
        ),
        STATUS_READY: (
            "Pesanan sudah bisa diambil",
            "Tunjukkan nomor antrean ini di konter kios.",
        ),
        STATUS_REJECT: (
            "Pembayaran ditolak",
            reason or "Bukti pembayaran tidak sesuai. Silakan hubungi konter kios.",
        ),
    }.get(status, (status, ""))
    muted = " is-muted" if status == STATUS_REJECT else ""
    return (
        f'<p class="gf-status-text{muted}">{html.escape(headline)}</p>'
        f'<p class="gf-status-sub">{html.escape(sub)}</p>'
    )


def _render_queue_screen() -> None:
    head_l, head_r = st.columns([3, 1])
    with head_l:
        st.markdown("#### Antrean Aktif & Riwayat")
    with head_r:
        if st.button("Perbarui Status", use_container_width=True):
            st.rerun()

    for order in st.session_state["pv_orders"]:
        with st.container(border=True):
            c_num, c_detail = st.columns([1.05, 2.95])
            with c_num:
                st.caption("Nomor Antrean")
                st.markdown(
                    f"<div style='font-size:32px;font-weight:700;letter-spacing:-0.03em;color:#18181B;'>"
                    f"#{html.escape(order['queue_number'])}</div>",
                    unsafe_allow_html=True,
                )
                st.caption(order["created_at"])
            with c_detail:
                st.markdown(f"#### {order['tenant_name']}")
                items_summary = ", ".join(
                    f"{i['qty']}x {i['name']}" for i in order["items"]
                )
                st.markdown(f"{items_summary}  ·  **{format_rp(int(order['total_price']))}**")
                if order["notes"]:
                    st.caption(f"Catatan: {order['notes']}")

            st.markdown(
                _render_status_text_html(
                    order["status"], order.get("rejection_reason", "")
                ),
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Layar 4: Dashboard Penjual Kios
# ---------------------------------------------------------------------------


def _render_seller_screen() -> None:
    tenant = st.session_state["pv_tenants"][0]
    orders = [
        o for o in st.session_state["pv_orders"] if o["tenant_id"] == tenant["id"]
    ]
    menus = [
        m for m in st.session_state["pv_menus"] if m["tenant_id"] == tenant["id"]
    ]

    with st.container(border=True):
        h_left, h_right = st.columns([3, 1.1])
        with h_left:
            state_lbl = "BUKA" if tenant["is_open"] else "TUTUP"
            b_cls = "gf-badge-open" if tenant["is_open"] else "gf-badge-closed"
            st.markdown(
                f'<span class="gf-badge {b_cls}">{state_lbl}</span> '
                f'<span style="font-size:18px;font-weight:700;margin-left:8px;">'
                f'{html.escape(tenant["name"])}</span>',
                unsafe_allow_html=True,
            )
            st.caption(tenant["description"])
        with h_right:
            if st.button(
                "Tutup Kios" if tenant["is_open"] else "Buka Kios",
                type="secondary" if tenant["is_open"] else "primary",
                use_container_width=True,
            ):
                tenant["is_open"] = not tenant["is_open"]
                st.rerun()

    tab_antrean, tab_menu = st.tabs(
        [f"Pesanan Masuk ({len(orders)})", f"Kelola Menu ({len(menus)})"]
    )

    with tab_antrean:
        counts = {
            s: sum(1 for o in orders if o["status"] == s)
            for s in (STATUS_PENDING, STATUS_PREP, STATUS_READY, STATUS_REJECT)
        }
        revenue = sum(
            int(o["total_price"])
            for o in orders
            if o["status"] in (STATUS_PREP, STATUS_READY)
        )

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Perlu Verifikasi", counts[STATUS_PENDING])
        k2.metric("Disiapkan", counts[STATUS_PREP])
        k3.metric("Siap Diambil", counts[STATUS_READY])
        k4.metric("Pendapatan", format_rp(revenue))

        nav_labels = {
            STATUS_PENDING: "Menunggu Konfirmasi",
            STATUS_PREP: "Sedang Disiapkan",
            STATUS_READY: "Sudah Bisa Diambil",
            STATUS_REJECT: "Ditolak",
        }
        active_nav = st.segmented_control(
            "Navigasi Status",
            options=list(nav_labels.keys()),
            default=STATUS_PENDING,
            required=True,
            format_func=lambda s: f"{nav_labels[s]} ({counts[s]})",
            label_visibility="collapsed",
            width="stretch",
            key="pv_seller_nav",
        )

        visible_orders = [o for o in orders if o["status"] == active_nav]
        if not visible_orders:
            st.markdown(
                '<div class="gf-surface-note">Tidak ada pesanan pada status ini.</div>',
                unsafe_allow_html=True,
            )
        for order in visible_orders:
            oid = order["id"]
            pending = st.session_state.get("pv_seller_pending")
            p_act = pending["action"] if pending and pending["id"] == oid else None

            with st.container(border=True):
                c1, c2, c3 = st.columns([0.9, 2.3, 1.4])
                with c1:
                    st.caption("Antrean")
                    st.markdown(f"### #{order['queue_number']}")
                with c2:
                    st.markdown(f"**{order['buyer_name']}** (`{order['buyer_npm']}`)")
                    for i in order["items"]:
                        st.caption(f"{i['qty']}x {i['name']} — {format_rp(i['price'] * i['qty'])}")
                    if order["notes"]:
                        st.caption(f"Catatan: {order['notes']}")
                with c3:
                    if order["status"] == STATUS_PENDING:
                        if p_act == "confirm":
                            st.caption("Konfirmasi pembayaran valid?")
                            if st.button("Ya, Konfirmasi", key=f"ok_{oid}", type="primary", use_container_width=True):
                                order["status"] = STATUS_PREP
                                st.session_state["pv_seller_pending"] = None
                                st.rerun()
                            if st.button("Batal", key=f"no_{oid}", use_container_width=True):
                                st.session_state["pv_seller_pending"] = None
                                st.rerun()
                        elif p_act == "reject":
                            st.caption("Yakin tolak pesanan ini?")
                            if st.button("Ya, Tolak", key=f"rok_{oid}", type="primary", use_container_width=True):
                                order["status"] = STATUS_REJECT
                                st.session_state["pv_seller_pending"] = None
                                st.rerun()
                            if st.button("Batal", key=f"rno_{oid}", use_container_width=True):
                                st.session_state["pv_seller_pending"] = None
                                st.rerun()
                        else:
                            if st.button("Konfirmasi Bayar", key=f"cf_{oid}", type="primary", use_container_width=True):
                                st.session_state["pv_seller_pending"] = {"id": oid, "action": "confirm"}
                                st.rerun()
                            if st.button("Tolak", key=f"rj_{oid}", use_container_width=True):
                                st.session_state["pv_seller_pending"] = {"id": oid, "action": "reject"}
                                st.rerun()
                    elif order["status"] == STATUS_PREP:
                        if p_act == "ready":
                            st.caption("Pesanan sudah siap di konter?")
                            if st.button("Ya, Siap Diambil", key=f"rdy_{oid}", type="primary", use_container_width=True):
                                order["status"] = STATUS_READY
                                st.session_state["pv_seller_pending"] = None
                                st.rerun()
                            if st.button("Batal", key=f"rdc_{oid}", use_container_width=True):
                                st.session_state["pv_seller_pending"] = None
                                st.rerun()
                        else:
                            if st.button("Tandai Siap Diambil", key=f"mk_{oid}", type="primary", use_container_width=True):
                                st.session_state["pv_seller_pending"] = {"id": oid, "action": "ready"}
                                st.rerun()

    with tab_menu:
        g_cols = st.columns(3)
        for idx, m in enumerate(menus):
            with g_cols[idx % 3]:
                with st.container(border=True):
                    st.markdown(
                        _render_media_html(
                            m["image_url"],
                            m["name"],
                            dimmed=not m["is_available"],
                            badge_text="TERSEDIA" if m["is_available"] else "HABIS",
                            badge_open=bool(m["is_available"]),
                        ),
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f'<p class="gf-title">{html.escape(m["name"])}</p>'
                        f'<p class="gf-price">{format_rp(int(m["price"]))}</p>',
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "Set Habis" if m["is_available"] else "Set Tersedia",
                        key=f"pv_stk_{m['id']}",
                        use_container_width=True,
                    ):
                        m["is_available"] = not m["is_available"]
                        st.rerun()


# ---------------------------------------------------------------------------
# Layar 5: Halaman Masuk Minimalis Terpusat
# ---------------------------------------------------------------------------


def _render_login_screen() -> None:
    _, center_col, _ = st.columns([1, 1.35, 1])
    with center_col:
        with st.container(border=True):
            st.markdown(
                "<h3 style='margin-bottom:2px;font-weight:700;letter-spacing:-0.02em;'>GoFood Kancil</h3>"
                "<p style='color:#71717A;font-size:13.5px;margin-bottom:16px;'>"
                "Pesan makanan kantin fakultas tanpa antre.</p>",
                unsafe_allow_html=True,
            )
            t_mhs, t_kios = st.tabs(["Mahasiswa", "Pengelola Kios"])
            with t_mhs:
                st.button(
                    "Masuk dengan SSO UI",
                    type="primary",
                    use_container_width=True,
                    key="pv_sso_btn",
                )
                st.divider()
                st.text_input("NPM", placeholder="2606123456", key="pv_login_npm")
                st.text_input(
                    "Password",
                    type="password",
                    placeholder="Masukkan password",
                    key="pv_login_pw",
                )
                st.button(
                    "Masuk ke Kantin",
                    use_container_width=True,
                    key="pv_login_submit",
                )
            with t_kios:
                st.text_input(
                    "Nama Kios",
                    placeholder="Ayam Geprek Mas Budi",
                    key="pv_kios_name",
                )
                st.text_input(
                    "Password Kios",
                    type="password",
                    placeholder="Masukkan password kios",
                    key="pv_kios_pw",
                )
                st.button(
                    "Masuk Dashboard Kios",
                    type="primary",
                    use_container_width=True,
                    key="pv_kios_submit",
                )


def _on_nav_change() -> None:
    """Callback klik navigasi bawah: simpan layar aktif yang dipilih pengguna."""
    chosen = st.session_state.get("pv_bottom_nav_control")
    if chosen:
        st.session_state["pv_screen"] = chosen
        st.session_state["pv_nav_synced"] = chosen


def main() -> None:
    st.set_page_config(
        page_title="UI Preview — GoFood Kancil",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_minimalist_css()
    _init_preview_data()

    st.markdown(
        "<div style='padding-bottom:6px;'>"
        "<span style='font-size:22px;font-weight:700;letter-spacing:-0.025em;'>GoFood Kancil</span>"
        "<span style='font-size:12px;color:#71717A;margin-left:8px;'>UI Preview</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    # Sinkronkan widget navigasi bila layar diganti lewat kode (mis. tombol
    # "Lanjut ke Keranjang"), lalu biarkan klik pengguna ditangani callback.
    if st.session_state.get("pv_nav_synced") != st.session_state["pv_screen"]:
        st.session_state["pv_bottom_nav_control"] = st.session_state["pv_screen"]
        st.session_state["pv_nav_synced"] = st.session_state["pv_screen"]

    # Navigasi preview antar-layar: melayang menempel di bawah layar (1 baris)
    nav_short_labels = {
        SCREEN_STOREFRONT: "Etalase",
        SCREEN_CART: "Keranjang",
        SCREEN_QUEUE: "Antrean",
        SCREEN_SELLER: "Penjual",
        SCREEN_LOGIN: "Masuk",
    }
    with st.container(key="bottom_nav"):
        st.segmented_control(
            "Layar Preview",
            options=list(nav_short_labels.keys()),
            format_func=lambda s: nav_short_labels[s],
            required=True,
            wrap=False,
            label_visibility="collapsed",
            width="stretch",
            key="pv_bottom_nav_control",
            on_change=_on_nav_change,
        )

    active = st.session_state["pv_screen"]
    if active == SCREEN_STOREFRONT:
        _render_storefront_screen()
    elif active == SCREEN_CART:
        _render_cart_screen()
    elif active == SCREEN_QUEUE:
        _render_queue_screen()
    elif active == SCREEN_SELLER:
        _render_seller_screen()
    else:
        _render_login_screen()


if __name__ == "__main__":
    main()
