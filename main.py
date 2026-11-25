"""Entry point utama aplikasi GoFood Kancil (Queue Kantin Online) berbasis Streamlit."""

from __future__ import annotations

from typing import Any

import streamlit as st

import auth_service
import buyer_view
import db_service
import seller_view


def _default_demo_buyer() -> dict[str, Any]:
    """Mengembalikan data akun demo default untuk Role Pembeli."""
    return {
        "id": "npm-2606123456",
        "name": "Hilmo (Demo)",
        "npm": "2606123456",
        "role": "buyer",
        "auth_provider": "demo",
    }


def _init_session_state() -> None:
    """Menginisialisasi state bawaan aplikasi dan database."""
    db_service.init_db()
    if "user" not in st.session_state:
        st.session_state["user"] = None
    if "last_buyer_user" not in st.session_state:
        st.session_state["last_buyer_user"] = _default_demo_buyer()
    if "cart" not in st.session_state:
        st.session_state["cart"] = {"tenant_id": None, "items": {}}
    if "active_storefront_tenant_id" not in st.session_state:
        st.session_state["active_storefront_tenant_id"] = None
    if "seller_pending_action" not in st.session_state:
        st.session_state["seller_pending_action"] = None
    if "sso_auth_error" not in st.session_state:
        st.session_state["sso_auth_error"] = ""


def _set_buyer_session(buyer: dict[str, Any]) -> None:
    """Menyimpan sesi login Pembeli sekaligus mengingat profilnya untuk pindah role."""
    st.session_state["user"] = buyer
    st.session_state["last_buyer_user"] = buyer
    st.session_state["seller_pending_action"] = None
    st.session_state["sso_auth_error"] = ""


def _set_seller_session(tenant: dict[str, Any]) -> None:
    """Menyimpan sesi login Penjual berdasarkan kios yang dipilih."""
    st.session_state["user"] = {
        "id": f"seller-{tenant['id']}",
        "name": f"Pengelola {tenant['name']}",
        "tenant_id": tenant["id"],
        "role": "seller",
    }
    st.session_state["seller_pending_action"] = None
    st.session_state["sso_auth_error"] = ""


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
    """Merender form login Pembeli: SSO UI CAS 2.0 + Akun Cadangan NPM & Password."""
    st.subheader("Masuk sebagai Mahasiswa")
    sso_err = st.session_state.get("sso_auth_error", "")
    if sso_err:
        st.error(f"Login SSO UI gagal ({sso_err}). Gunakan akun NPM & Password di bawah jika domain belum di-whitelist.")

    st.link_button(
        "🎓 Masuk dengan SSO UI",
        auth_service.build_sso_login_url(),
        type="primary",
        use_container_width=True,
    )
    st.caption(
        "Autentikasi resmi mahasiswa via protokol CAS 2.0 (sso.ui.ac.id/cas2)."
    )

    st.divider()
    st.caption("Atau masuk / daftar menggunakan akun GoFood Kancil:")

    buyer_mode = st.segmented_control(
        "Mode Akun Mahasiswa",
        options=["Masuk Akun", "Daftar Akun"],
        default="Masuk Akun",
        required=True,
        label_visibility="collapsed",
        width="stretch",
        key="buyer_auth_mode",
    )

    if buyer_mode == "Daftar Akun":
        with st.form("student_register_form"):
            reg_name = st.text_input("Nama Lengkap", placeholder="Contoh: Hilmo")
            reg_npm = st.text_input("NPM", placeholder="Contoh: 2606123456")
            reg_pw = st.text_input(
                "Password",
                type="password",
                placeholder="Minimal 4 karakter",
            )
            reg_submitted = st.form_submit_button(
                "📝 Daftar & Masuk", type="primary", use_container_width=True
            )

        if reg_submitted:
            try:
                buyer = db_service.register_buyer(reg_name, reg_npm, reg_pw)
                _set_buyer_session(buyer)
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    else:
        with st.form("student_login_form"):
            login_npm = st.text_input("NPM", placeholder="Contoh: 2606123456")
            login_pw = st.text_input(
                "Password",
                type="password",
                placeholder="Masukkan password akunmu",
            )
            login_submitted = st.form_submit_button(
                "🔑 Masuk ke Kantin", type="primary", use_container_width=True
            )

        if login_submitted:
            buyer = db_service.authenticate_buyer(login_npm, login_pw)
            if buyer is None:
                st.error(
                    "NPM atau password tidak ditemukan. Silakan pilih Daftar Akun terlebih dahulu."
                )
            else:
                _set_buyer_session(buyer)
                st.rerun()

    st.divider()
    if st.button("⚡ Login Cepat Pembeli (Demo)", use_container_width=True):
        _set_buyer_session(_default_demo_buyer())
        st.rerun()


def _render_seller_login_tab(
    tenants: list[dict[str, Any]], tenant_map: dict[str, dict[str, Any]]
) -> None:
    """Merender form login Penjual berbasis Nama Kios + Password."""
    st.subheader("Masuk sebagai Pengelola Kios")
    if not tenants:
        st.warning("Belum ada data kios.")
        return

    tenant_names = ", ".join(t["name"] for t in tenants)
    st.caption(
        f"Masukkan Nama Kios dan Password. Kios terdaftar: {tenant_names} "
        f"(Password demo awal: `{db_service.DEFAULT_SELLER_PASSWORD}`)."
    )
    with st.form("seller_login_form"):
        kios_name_input = st.text_input(
            "Nama Kios",
            placeholder="Contoh: Kantin Ayam Geprek Mas Budi",
        )
        password_input = st.text_input(
            "Password",
            type="password",
            placeholder="Masukkan password kios",
        )
        seller_submit = st.form_submit_button(
            "🔑 Masuk sebagai Penjual",
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

    st.divider()
    quick_tid = st.selectbox(
        "Kios untuk Login Cepat (Demo):",
        options=[t["id"] for t in tenants],
        format_func=lambda tid: tenant_map[tid]["name"],
        key="quick_seller_tenant_select",
    )
    if st.button(
        "⚡ Login Cepat Penjual (Kios Terpilih)",
        use_container_width=True,
    ):
        _set_seller_session(tenant_map[quick_tid])
        st.rerun()


def _render_login_page() -> None:
    """Merender halaman login 2 role (Pembeli Mahasiswa & Penjual Kios Kantin)."""
    st.title("GoFood Kancil — Queue Kantin Online")
    st.caption("Pesan makanan & minuman kantin satu fakultas tanpa antre lama.")

    tenants = db_service.get_tenants()
    tenant_map = {t["id"]: t for t in tenants}

    col_left, col_right = st.columns([1.35, 1])
    with col_left:
        with st.container(border=True):
            tab_buyer_login, tab_seller_login = st.tabs(
                ["Pembeli (Mahasiswa)", "Penjual (Kios Kantin)"]
            )
            with tab_buyer_login:
                _render_buyer_login_tab()
            with tab_seller_login:
                _render_seller_login_tab(tenants, tenant_map)

    with col_right:
        with st.container(border=True):
            st.markdown("#### Alur GoFood Kancil")
            st.markdown(
                "**Untuk Mahasiswa (Pembeli):**\n"
                "1. Masuk via **SSO UI** atau akun NPM & Password.\n"
                "2. Pilih kios & menu di **Etalase Kantin**.\n"
                "3. Scan **QRIS khusus kios** & upload bukti pembayaran (`0%`).\n"
                "4. Pantau **Live Queue** (`0% → 50% → 100%`) & ambil di konter kios.\n\n"
                "**Untuk Penjual Kios:**\n"
                "1. Masuk menggunakan **Nama Kios + Password**.\n"
                "2. Kelola menu, harga, stok, & status **Buka/Tutup** kios.\n"
                "3. Cek bukti QRIS lalu **Konfirmasi / Tolak** pembayaran (konfirmasi ganda).\n"
                "4. Tandai **Pesanan Sudah Bisa Diambil** setelah selesai disiapkan."
            )
            db_mode = db_service.get_db_backend_mode()
            db_text = (
                "Firebase Cloud Firestore (Aktif)"
                if db_mode == "firebase"
                else "Memori Lokal (Fallback — taruh serviceAccountKey.json untuk Cloud)"
            )
            st.caption(f"Status Database: **{db_text}**")


def _render_sidebar(user: dict[str, Any]) -> None:
    """Merender sidebar profil, status database, ringkasan, dan pindah role demo."""
    tenants = db_service.get_tenants()
    tenant_map = {t["id"]: t for t in tenants}
    db_mode = db_service.get_db_backend_mode()
    db_label = (
        "Firebase Cloud Firestore"
        if db_mode == "firebase"
        else "Memori Lokal (Fallback)"
    )

    with st.sidebar:
        st.markdown("## GoFood Kancil")
        st.caption("Queue Kantin Online — Fakultas")
        st.caption(f"Database: **{db_label}**")
        st.divider()

        if user["role"] == "buyer":
            st.markdown("### Profil Pembeli")
            st.markdown(f"**Nama:** {user['name']}")
            st.markdown(f"**NPM:** `{user['npm']}`")
            if st.button("🚪 Keluar (Logout)", use_container_width=True):
                st.session_state["user"] = None
                st.session_state["cart"] = {"tenant_id": None, "items": {}}
                st.session_state["active_storefront_tenant_id"] = None
                st.session_state["seller_pending_action"] = None
                st.rerun()

            st.divider()
            cart = st.session_state["cart"]
            cart_qty = sum(int(item["qty"]) for item in cart["items"].values())
            cart_total = sum(
                int(item["price"]) * int(item["qty"])
                for item in cart["items"].values()
            )
            st.markdown("### Ringkasan Keranjang")
            if cart_qty > 0 and cart["tenant_id"]:
                active_tenant = tenant_map.get(cart["tenant_id"])
                tenant_name = active_tenant["name"] if active_tenant else "-"
                st.caption(f"Kios: **{tenant_name}**")
                st.write(
                    f"{cart_qty} item · **{buyer_view.format_rupiah(cart_total)}**"
                )
            else:
                st.caption("Keranjang masih kosong.")

            st.divider()
            st.markdown("### Pindah Role (Demo)")
            st.caption(
                "Beralih ke tampilan Penjual untuk memproses pesanan yang baru kamu buat."
            )
            if tenants:
                target_tid = st.selectbox(
                    "Pilih Dashboard Kios:",
                    options=[t["id"] for t in tenants],
                    format_func=lambda tid: tenant_map[tid]["name"],
                    key="sidebar_switch_seller_tid",
                )
                if st.button(
                    "🍳 Masuk ke Mode Penjual",
                    key="switch_to_seller_btn",
                    use_container_width=True,
                ):
                    _set_seller_session(tenant_map[target_tid])
                    st.rerun()

        else:
            current_tenant = tenant_map.get(user.get("tenant_id", ""))
            st.markdown("### Profil Penjual")
            if current_tenant:
                status_text = "Buka" if current_tenant["is_open"] else "Tutup"
                st.markdown(f"**Kios:** {current_tenant['name']}")
                st.markdown(f"**Status:** {status_text}")
            if st.button("🚪 Keluar (Logout)", use_container_width=True):
                st.session_state["user"] = None
                st.session_state["seller_pending_action"] = None
                st.rerun()

            st.divider()
            st.markdown("### Ganti Kios (Demo)")
            if tenants:
                current_idx = next(
                    (
                        i
                        for i, t in enumerate(tenants)
                        if t["id"] == user.get("tenant_id")
                    ),
                    0,
                )
                switch_tid = st.selectbox(
                    "Kelola Kios Lain:",
                    options=[t["id"] for t in tenants],
                    index=current_idx,
                    format_func=lambda tid: tenant_map[tid]["name"],
                    key="sidebar_seller_tenant_switch",
                )
                if st.button(
                    "🔁 Buka Dashboard Kios Ini",
                    key="switch_seller_tenant_btn",
                    use_container_width=True,
                ):
                    _set_seller_session(tenant_map[switch_tid])
                    st.rerun()

            st.divider()
            st.markdown("### Pindah Role (Demo)")
            if st.button(
                "🎓 Kembali ke Mode Pembeli (Demo)",
                key="switch_to_buyer_btn",
                use_container_width=True,
            ):
                buyer_profile = (
                    st.session_state.get("last_buyer_user")
                    or _default_demo_buyer()
                )
                _set_buyer_session(buyer_profile)
                st.rerun()


def main() -> None:
    """Menjalankan aplikasi utama GoFood Kancil."""
    st.set_page_config(
        page_title="GoFood Kancil - Queue Kantin Online",
        layout="wide",
    )
    _init_session_state()
    _handle_sso_callback_hook()

    user = st.session_state["user"]
    if user is None:
        _render_login_page()
        return

    _render_sidebar(user)
    if user["role"] == "seller":
        st.title("GoFood Kancil — Dashboard Penjual")
        seller_view.render_seller_view(user)
    else:
        st.title("GoFood Kancil — Kantin Fakultas")
        buyer_view.render_buyer_view(user)


if __name__ == "__main__":
    main()
