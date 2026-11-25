"""Entry point utama aplikasi Pesan Kancil berbasis Streamlit."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

import auth_service
import buyer_view
import db_service
import seller_view
import ui_theme


def _init_session_state() -> None:
    """Menginisialisasi state bawaan aplikasi dan database."""
    db_service.init_db()
    if "user" not in st.session_state:
        st.session_state["user"] = None
    if "cart" not in st.session_state:
        st.session_state["cart"] = {"tenant_id": None, "items": {}}
    if "active_storefront_tenant_id" not in st.session_state:
        st.session_state["active_storefront_tenant_id"] = None
    if "seller_pending_action" not in st.session_state:
        st.session_state["seller_pending_action"] = None
    if "sso_auth_error" not in st.session_state:
        st.session_state["sso_auth_error"] = ""


def _set_buyer_session(buyer: dict[str, Any]) -> None:
    """Menyimpan sesi login Pembeli hasil autentikasi SSO UI."""
    st.session_state["user"] = buyer
    st.session_state["seller_pending_action"] = None
    st.session_state["sso_auth_error"] = ""


def _set_seller_session(tenant: dict[str, Any]) -> None:
    """Menyimpan sesi login Penjual berdasarkan kios yang terautentikasi."""
    st.session_state["user"] = {
        "id": f"seller-{tenant['id']}",
        "name": f"Pengelola {tenant['name']}",
        "tenant_id": tenant["id"],
        "role": "seller",
    }
    st.session_state["seller_pending_action"] = None
    st.session_state["sso_auth_error"] = ""


def _logout_user() -> None:
    """Membersihkan sesi login saat pengguna keluar."""
    st.session_state["user"] = None
    st.session_state["cart"] = {"tenant_id": None, "items": {}}
    st.session_state["active_storefront_tenant_id"] = None
    st.session_state["seller_pending_action"] = None
    st.session_state["buyer_nav"] = buyer_view.NAV_STOREFRONT
    st.session_state["seller_nav"] = seller_view.SELLER_NAV_ORDERS


def _handle_sso_callback_hook() -> None:
    """Memvalidasi callback tiket CAS 2.0 dari SSO UI (`?ticket=ST-...`)."""
    if "ticket" in st.query_params and st.session_state["user"] is None:
        ticket = str(st.query_params["ticket"])
        st.query_params.clear()

        result = auth_service.validate_sso_ticket(ticket)
        if result.get("authenticated"):
            buyer = db_service.upsert_sso_buyer(
                username=result["username"],
                name=result["name"],
                npm=result["npm"],
                kd_org=result.get("kd_org", ""),
            )
            _set_buyer_session(buyer)
            st.rerun()
        else:
            st.session_state["sso_auth_error"] = result.get(
                "error", "Validasi tiket SSO UI gagal."
            )


def _render_buyer_login_tab() -> None:
    """Merender halaman masuk Pembeli khusus menggunakan SSO UI."""
    sso_err = st.session_state.get("sso_auth_error", "")
    if sso_err:
        st.error(f"Login SSO UI gagal ({sso_err}). Silakan coba kembali.")

    st.caption(
        "Gunakan akun resmi mahasiswa Universitas Indonesia untuk mulai memesan makanan di kantin fakultas."
    )
    with st.container(key="sso_ui_btn"):
        st.link_button(
            "Masuk dengan SSO UI",
            auth_service.build_sso_login_url(),
            type="primary",
            use_container_width=True,
        )
    st.caption("Autentikasi melalui sso.ui.ac.id/cas2.")


def _render_seller_login_tab() -> None:
    """Merender halaman Masuk & Daftar akun baru bagi Pengelola Kios."""
    seller_mode = st.segmented_control(
        "Mode Akun Penjual",
        options=["Masuk Kios", "Daftar Kios Baru"],
        default="Masuk Kios",
        required=True,
        wrap=False,
        label_visibility="collapsed",
        width="stretch",
        key="seller_auth_mode",
    )

    if seller_mode == "Daftar Kios Baru":
        with st.form("seller_register_form"):
            reg_kios_name = st.text_input(
                "Nama Kios",
                placeholder="Contoh: Warung Nasi Goreng Pak Joko",
            )
            reg_category = st.text_input(
                "Kategori Makanan",
                placeholder="Contoh: Nasi & Mie, Ayam & Sambal, Minuman",
            )
            reg_desc = st.text_area(
                "Deskripsi Singkat Kios",
                placeholder="Jelaskan menu andalan kiosmu secara singkat...",
            )
            reg_photo = st.file_uploader(
                "Foto Kios (PNG / JPG - Opsional)",
                type=["png", "jpg", "jpeg"],
                key="seller_register_photo",
            )
            reg_qris = st.file_uploader(
                "Gambar QRIS Asli Kios (PNG / JPG - Opsional, bisa diubah di Profil Kios)",
                type=["png", "jpg", "jpeg"],
                key="seller_register_qris",
            )
            reg_pw = st.text_input(
                "Password",
                type="password",
                placeholder="Minimal 4 karakter",
            )
            reg_pw_confirm = st.text_input(
                "Konfirmasi Password",
                type="password",
                placeholder="Ulangi password",
            )
            reg_submit = st.form_submit_button(
                "Daftar & Masuk Dashboard Kios",
                type="primary",
                use_container_width=True,
            )

        if reg_submit:
            if reg_pw != reg_pw_confirm:
                st.error("Konfirmasi password tidak cocok.")
            else:
                try:
                    image_data_uri = ""
                    if reg_photo is not None:
                        img_bytes, img_name = db_service.encode_uploaded_file(
                            reg_photo
                        )
                        image_data_uri = db_service.bytes_to_base64_data_uri(
                            img_bytes, img_name
                        )
                    qris_data_uri = ""
                    if reg_qris is not None:
                        q_bytes, q_name = db_service.compress_payment_image(
                            reg_qris.getvalue(),
                            reg_qris.name,
                            max_width=800,
                            quality=88,
                        )
                        qris_data_uri = db_service.bytes_to_base64_data_uri(
                            q_bytes, q_name
                        )
                    new_tenant = db_service.register_seller(
                        name=reg_kios_name,
                        password=reg_pw,
                        category=reg_category,
                        description=reg_desc,
                        image_url=image_data_uri,
                        qris_image_b64=qris_data_uri,
                    )
                    _set_seller_session(new_tenant)
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
    else:
        with st.form("seller_login_form"):
            kios_name_input = st.text_input(
                "Nama Kios",
                placeholder="Masukkan nama kios terdaftar",
            )
            password_input = st.text_input(
                "Password",
                type="password",
                placeholder="Masukkan password kios",
            )
            seller_submit = st.form_submit_button(
                "Masuk Dashboard Kios",
                type="primary",
                use_container_width=True,
            )

        if seller_submit:
            matched_tenant = db_service.authenticate_seller(
                kios_name_input, password_input
            )
            if matched_tenant is None:
                st.error("Nama kios atau password salah.")
            else:
                _set_seller_session(matched_tenant)
                st.rerun()


def _render_login_page() -> None:
    """Merender halaman masuk terpusat minimalis bergaya putih-abu."""
    _, center_col, _ = st.columns([1, 1.45, 1])
    with center_col:
        with st.container(border=True):
            st.markdown(
                "<h3 style='margin-bottom:2px;font-weight:700;letter-spacing:-0.02em;'>Pesan Kancil</h3>"
                "<p style='color:#71717A;font-size:13.5px;margin-bottom:14px;'>"
                "Pesan makanan kantin fakultas tanpa antre.</p>",
                unsafe_allow_html=True,
            )
            tab_buyer_login, tab_seller_login = st.tabs(
                ["Mahasiswa", "Pengelola Kios"]
            )
            with tab_buyer_login:
                _render_buyer_login_tab()
            with tab_seller_login:
                _render_seller_login_tab()


def _render_top_header(user: dict[str, Any]) -> None:
    """Merender header minimalis di atas halaman."""
    tenants = {t["id"]: t for t in db_service.get_tenants()}
    if user["role"] == "seller":
        t_name = tenants.get(user.get("tenant_id", ""), {}).get(
            "name", "Dashboard Penjual"
        )
        subtitle = f"Penjual · {t_name}"
    else:
        subtitle = f"{user['name']} · {user['npm']}"

    st.markdown(
        "<div style='padding-bottom:6px;'>"
        "<span style='font-size:22px;font-weight:700;letter-spacing:-0.025em;'>Pesan Kancil</span>"
        f"<span style='font-size:13px;color:#71717A;margin-left:10px;'>{html.escape(subtitle)}</span>"
        "</div>",
        unsafe_allow_html=True,
    )


def _render_sidebar(user: dict[str, Any]) -> None:
    """Merender sidebar profil pengguna dan tombol keluar."""
    tenants = {t["id"]: t for t in db_service.get_tenants()}
    db_mode = db_service.get_db_backend_mode()
    db_label = (
        "Firebase Cloud Firestore"
        if db_mode == "firebase"
        else "Memori Lokal"
    )

    with st.sidebar:
        st.markdown("## Pesan Kancil")
        st.caption(f"Database: **{db_label}**")
        st.divider()

        if user["role"] == "buyer":
            st.markdown("### Profil Pembeli")
            st.markdown(f"**Nama:** {user['name']}")
            st.markdown(f"**NPM:** `{user['npm']}`")
            if st.button(
                "Keluar", key="sidebar_logout_btn", use_container_width=True
            ):
                _logout_user()
                st.rerun()
        else:
            current_tenant = tenants.get(user.get("tenant_id", ""))
            st.markdown("### Profil Penjual")
            if current_tenant:
                status_text = "Buka" if current_tenant["is_open"] else "Tutup"
                st.markdown(f"**Kios:** {current_tenant['name']}")
                st.markdown(f"**Status:** {status_text}")
            if st.button(
                "Keluar",
                key="sidebar_seller_logout_btn",
                use_container_width=True,
            ):
                _logout_user()
                st.rerun()


def main() -> None:
    """Menjalankan aplikasi utama Pesan Kancil."""
    st.set_page_config(
        page_title="Pesan Kancil",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    ui_theme.inject_minimalist_css()
    _init_session_state()
    _handle_sso_callback_hook()

    user = st.session_state["user"]
    if user is None:
        _render_login_page()
        return

    _render_sidebar(user)
    _render_top_header(user)
    if user["role"] == "seller":
        seller_view.render_seller_view(user)
    else:
        buyer_view.render_buyer_view(user)


if __name__ == "__main__":
    main()
