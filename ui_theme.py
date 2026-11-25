"""Sistem desain minimalis putih-abu bersama untuk GoFood Kancil."""

from __future__ import annotations

import base64
from functools import lru_cache
import html
from pathlib import Path

import streamlit as st

import db_service

PROJECT_DIR = Path(__file__).resolve().parent


def format_rupiah(amount: int) -> str:
    """Memformat angka integer menjadi string mata uang Rupiah (mis. Rp15.000)."""
    return f"Rp{amount:,}".replace(",", ".")


@lru_cache(maxsize=64)
def resolve_image_src(image_ref: str) -> str:
    """Mengubah path file lokal menjadi data URI; URL & data URI dikembalikan apa adanya."""
    if not image_ref or image_ref.startswith(("http://", "https://", "data:")):
        return image_ref
    file_path = PROJECT_DIR / image_ref
    if not file_path.is_file():
        return ""
    mime = "image/png" if file_path.suffix.lower() == ".png" else "image/jpeg"
    encoded = base64.b64encode(file_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def placeholder_svg_uri(label: str) -> str:
    """Fallback gambar monokrom bersih jika foto belum tersedia."""
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


def render_media_html(
    image_url: str,
    alt_label: str,
    dimmed: bool = False,
    badge_text: str | None = None,
    badge_open: bool = True,
    eta_text: str | None = None,
) -> str:
    """Membangun blok HTML gambar rasio 16:10 seragam dengan fallback monokrom."""
    fallback_uri = placeholder_svg_uri(alt_label)
    safe_url = html.escape(resolve_image_src(image_url) or fallback_uri)
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


def render_status_text_html(status: str, rejection_reason: str = "") -> str:
    """Merender status pesanan sebagai teks deskriptif besar tanpa persentase."""
    headline, sub = {
        db_service.STATUS_PENDING_PAYMENT: (
            "Pembayaran sedang dikonfirmasi",
            "Penjual sedang memeriksa bukti pembayaran yang kamu kirim.",
        ),
        db_service.STATUS_PREPARING: (
            "Pesanan sedang disiapkan",
            "Pembayaran sudah dikonfirmasi, kios sedang menyiapkan pesananmu.",
        ),
        db_service.STATUS_READY: (
            "Pesanan sudah bisa diambil",
            "Tunjukkan nomor antrean ini di konter kios.",
        ),
        db_service.STATUS_REJECTED: (
            "Pembayaran ditolak",
            rejection_reason.strip()
            or "Bukti pembayaran tidak sesuai. Silakan hubungi konter kios.",
        ),
    }.get(status, (status, ""))
    muted = " is-muted" if status == db_service.STATUS_REJECTED else ""
    return (
        f'<p class="gf-status-text{muted}">{html.escape(headline)}</p>'
        f'<p class="gf-status-sub">{html.escape(sub)}</p>'
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
            width: min(520px, calc(100vw - 24px));
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
            padding-left: 14px !important;
            padding-right: 14px !important;
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
        .stFormSubmitButton > button[kind="primary"],
        .stLinkButton > a[kind="primary"] {
            background-color: #18181B !important;
            color: #FFFFFF !important;
            border: 1px solid #18181B !important;
            border-radius: 10px !important;
            font-weight: 500 !important;
            height: 2.55rem !important;
            letter-spacing: -0.01em;
        }
        .stButton > button[kind="primary"]:hover,
        .stFormSubmitButton > button[kind="primary"]:hover,
        .stLinkButton > a[kind="primary"]:hover {
            background-color: #27272A !important;
            border-color: #27272A !important;
        }
        .stButton > button[kind="secondary"],
        .stFormSubmitButton > button[kind="secondary"],
        .stLinkButton > a[kind="secondary"] {
            background-color: #FFFFFF !important;
            color: #18181B !important;
            border: 1px solid #E4E4E7 !important;
            border-radius: 10px !important;
            font-weight: 500 !important;
            height: 2.55rem !important;
        }
        .stButton > button[kind="secondary"]:hover,
        .stFormSubmitButton > button[kind="secondary"]:hover,
        .stLinkButton > a[kind="secondary"]:hover {
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
