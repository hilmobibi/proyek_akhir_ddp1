"""Entry point utama aplikasi GoFood Kancil (Queue Kantin Online) berbasis Streamlit."""

from __future__ import annotations

from typing import Any

import streamlit as st

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
    }


def _init_session_state() -> None:
    """Menginisialisasi state bawaan aplikasi dan mock database."""
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


def _set_buyer_session(buyer: dict[str, Any]) -> None:
    """Menyimpan sesi login Pembeli sekaligus mengingat profilnya untuk pindah role."""
    st.session_state["user"] = buyer
    st.session_state["last_buyer_user"] = buyer
    st.session_state["seller_pending_action"] = None


def _set_seller_session(tenant: dict[str, Any]) -> None:
    """Menyimpan sesi login Penjual berdasarkan kios yang dipilih."""
    st.session_state["user"] = {
        "id": f"seller-{tenant['id']}",
        "name": f"Pengelola {tenant['name']}",
        "tenant_id": tenant["id"],
        "role": "seller",
    }
    st.session_state["seller_pending_action"] = None


def _handle_sso_callback_hook() -> None:
    """Placeholder integrasi SSO UI (`?ticket=ST-...`) dari rekan tim.

    Saat teman yang menangani SSO UI + Supabase sudah selesai, ganti bagian
    simulasi di bawah ini dengan verifikasi tiket CAS SSO UI dan query user
    ke Supabase.
    """
    if "ticket" in st.query_params and st.session_state["user"] is None:
        ticket = st.query_params["ticket"]
        # TODO (Integrasi SSO UI + Supabase):
        # sso_profile = verify_sso_ticket(ticket)
        # db_user = upsert_supabase_user(sso_profile)
        _set_buyer_session(
            {
                "id": f"sso-{ticket[:8]}",
                "name": "Mahasiswa SSO UI",
                "npm": "2606000001",
                "role": "buyer",
            }
        )
        st.query_params.clear()


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
                st.subheader("Masuk sebagai Mahasiswa")
                st.caption(
                    "Masukkan Nama & NPM untuk mulai memesan. "
                    "(Nantinya akan terhubung ke Login SSO UI + Supabase)."
                )
                with st.form("student_login_form"):
                    name = st.text_input("Nama Mahasiswa", placeholder="Contoh: Hilmo")
                    npm = st.text_input("NPM", placeholder="Contoh: 2606123456")
                    submitted = st.form_submit_button(
                        "Masuk ke Kantin", type="primary", use_container_width=True
                    )

                if submitted:
                    clean_name = name.strip()
                    clean_npm = npm.strip()
                    if not clean_name or not clean_npm:
                        st.error("Nama dan NPM wajib diisi.")
                    else:
                        _set_buyer_session(
                            {
                                "id": f"npm-{clean_npm}",
                                "name": clean_name,
                                "npm": clean_npm,
                                "role": "buyer",
                            }
                        )
                        st.rerun()

                st.divider()
                if st.button(
                    "⚡ Login Cepat Pembeli (Demo)", use_container_width=True
                ):
                    _set_buyer_session(_default_demo_buyer())
                    st.rerun()

            with tab_seller_login:
                st.subheader("Masuk sebagai Pengelola Kios")
                st.caption(
                    "Pilih kios yang dikelola dan masukkan PIN kios "
                    "(PIN demo default: `1234`)."
                )
                if not tenants:
                    st.warning("Belum ada data kios.")
                else:
                    with st.form("seller_login_form"):
                        selected_tid = st.selectbox(
                            "Pilih Kios Kantin",
                            options=[t["id"] for t in tenants],
                            format_func=lambda tid: tenant_map[tid]["name"],
                        )
                        pin_input = st.text_input(
                            "PIN Kios", type="password", placeholder="Masukkan PIN (1234)"
                        )
                        seller_submit = st.form_submit_button(
                            "Masuk sebagai Penjual",
                            type="primary",
                            use_container_width=True,
                        )

                    if seller_submit:
                        chosen_tenant = tenant_map[selected_tid]
                        if pin_input.strip() != chosen_tenant.get("pin", "1234"):
                            st.error("PIN kios salah. Gunakan `1234` untuk demo.")
                        else:
                            _set_seller_session(chosen_tenant)
                            st.rerun()

                    st.divider()
                    quick_tid = st.selectbox(
                        "Kios untuk Login Cepat:",
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

    with col_right:
        with st.container(border=True):
            st.markdown("#### Alur GoFood Kancil")
            st.markdown(
                "**Untuk Mahasiswa (Pembeli):**\n"
                "1. Pilih kios & menu di **Etalase Kantin**.\n"
                "2. Checkout **1 kios** per pesanan & scan **QRIS khusus kios**.\n"
                "3. **Upload bukti pembayaran** (wajib) untuk masuk antrean (`0%`).\n"
                "4. Pantau **Live Queue** (`0% → 50% → 100%`) & ambil di konter kios.\n\n"
                "**Untuk Penjual Kios:**\n"
                "1. Kelola menu, harga, stok, & status **Buka/Tutup** kios.\n"
                "2. Cek bukti QRIS lalu **Konfirmasi / Tolak** pembayaran (dengan konfirmasi ganda).\n"
                "3. Tandai **Pesanan Sudah Bisa Diambil** setelah selesai disiapkan."
            )


def _render_sidebar(user: dict[str, Any]) -> None:
    """Merender sidebar profil, ringkasan, dan fitur pindah role cepat untuk demo."""
    tenants = db_service.get_tenants()
    tenant_map = {t["id"]: t for t in tenants}

    with st.sidebar:
        st.markdown("## GoFood Kancil")
        st.caption("Queue Kantin Online — Fakultas")
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
                buyer_profile = st.session_state.get("last_buyer_user") or _default_demo_buyer()
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
