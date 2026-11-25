"""Modul autentikasi Pesan Kancil: Password Hashing (PBKDF2) & CAS 2.0 SSO UI.

Mendukung:
1. Hashing & verifikasi password aman menggunakan ``hashlib.pbkdf2_hmac`` (SHA-256)
   untuk akun Penjual Kios dan akun cadangan Pembeli.
2. Integrasi Single Sign-On Universitas Indonesia (``https://sso.ui.ac.id/cas2``)
   menggunakan protokol CAS 2.0 berbasis validasi XML ``serviceValidate``.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from typing import Any
import urllib.parse
import xml.etree.ElementTree as ET

import requests

SSO_UI_CAS_BASE = "https://sso.ui.ac.id/cas2"
DEFAULT_SERVICE_URL = "http://localhost:8501/"
PBKDF2_ITERATIONS = 100_000
SSO_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/xml, text/xml, */*",
}


def hash_password(password: str, salt: str | None = None) -> str:
    """Membuat hash password menggunakan PBKDF2-HMAC-SHA256 dengan salt acak."""
    active_salt = salt if salt is not None else secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        active_salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${active_salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Memverifikasi password terhadap string hash ``pbkdf2_sha256$salt$digest``."""
    if not stored_hash or "$" not in stored_hash:
        return False
    parts = stored_hash.split("$")
    if len(parts) != 3 or parts[0] != "pbkdf2_sha256":
        return False
    _, salt, _ = parts
    expected = hash_password(password, salt=salt)
    return hmac.compare_digest(expected, stored_hash)


def _normalize_service_url(url: str) -> str:
    """Menormalisasi URL callback aplikasi agar konsisten saat login & validasi CAS."""
    cleaned = url.strip()
    if not cleaned:
        return DEFAULT_SERVICE_URL
    parsed = urllib.parse.urlsplit(cleaned)
    path = parsed.path if parsed.path else "/"
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def get_app_service_url() -> str:
    """Mengambil URL layanan aplikasi untuk callback SSO UI.

    Urutan prioritas:
    1. Environment variable ``APP_SERVICE_URL``
    2. ``st.secrets["APP_SERVICE_URL"]`` (untuk deployment Streamlit Cloud)
    3. Default lokal ``http://localhost:8501/``
    """
    env_url = os.environ.get("APP_SERVICE_URL", "").strip()
    if env_url:
        return _normalize_service_url(env_url)

    try:
        import streamlit as st

        if getattr(st, "runtime", None) is not None and st.runtime.exists():
            secret_url = str(st.secrets.get("APP_SERVICE_URL", "")).strip()
            if secret_url:
                return _normalize_service_url(secret_url)
    except Exception:
        pass

    return DEFAULT_SERVICE_URL


def build_sso_login_url(service_url: str | None = None) -> str:
    """Membangun URL redirect halaman login CAS 2.0 SSO UI."""
    svc = _normalize_service_url(service_url or get_app_service_url())
    query = urllib.parse.urlencode({"service": svc})
    return f"{SSO_UI_CAS_BASE}/login?{query}"


def parse_cas_xml_response(xml_bytes: bytes) -> dict[str, Any]:
    """Mem-parsing payload XML balasan dari endpoint ``cas2/serviceValidate``."""
    ns = {"cas": "http://www.yale.edu/tp/cas"}
    root = ET.fromstring(xml_bytes)

    success_node = root.find(".//cas:authenticationSuccess", ns)
    if success_node is not None:
        user_node = success_node.find("cas:user", ns)
        username = (user_node.text or "").strip() if user_node is not None else ""

        attrs: dict[str, str] = {}
        attr_node = success_node.find("cas:attributes", ns)
        if attr_node is not None:
            for child in attr_node:
                tag_name = child.tag.split("}")[-1]
                attrs[tag_name] = (child.text or "").strip()

        full_name = attrs.get("ldap_cn") or attrs.get("nama") or username
        npm = attrs.get("npm") or username
        kd_org = attrs.get("kd_org", "")
        peran_user = attrs.get("peran_user", "mahasiswa")

        if not username:
            return {
                "authenticated": False,
                "error": "Respons SSO UI tidak memuat identitas pengguna.",
            }

        return {
            "authenticated": True,
            "username": username,
            "name": full_name,
            "npm": npm,
            "kd_org": kd_org,
            "peran_user": peran_user,
            "error": "",
        }

    failure_node = root.find(".//cas:authenticationFailure", ns)
    if failure_node is not None:
        code = failure_node.attrib.get("code", "AUTH_FAILED")
        detail = (failure_node.text or "").strip()
        msg = f"{code}: {detail}" if detail else code
        return {"authenticated": False, "error": msg}

    return {
        "authenticated": False,
        "error": "Format respons XML dari server SSO UI tidak dikenali.",
    }


def validate_sso_ticket(
    ticket: str, service_url: str | None = None, timeout: int = 8
) -> dict[str, Any]:
    """Memvalidasi tiket CAS (``ST-...``) langsung ke server ``sso.ui.ac.id/cas2``."""
    clean_ticket = ticket.strip()
    if not clean_ticket:
        return {"authenticated": False, "error": "Tiket SSO kosong."}

    svc = _normalize_service_url(service_url or get_app_service_url())
    validate_url = f"{SSO_UI_CAS_BASE}/serviceValidate"
    try:
        response = requests.get(
            validate_url,
            params={"service": svc, "ticket": clean_ticket},
            headers=SSO_REQUEST_HEADERS,
            timeout=timeout,
        )
        response.raise_for_status()
        return parse_cas_xml_response(response.content)
    except requests.RequestException as exc:
        return {
            "authenticated": False,
            "error": f"Gagal menghubungi server SSO UI: {exc}",
        }
    except ET.ParseError:
        return {
            "authenticated": False,
            "error": "Gagal membaca respons XML dari server SSO UI.",
        }
