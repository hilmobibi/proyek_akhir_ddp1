"""Entry point utama aplikasi Quentin (Queue Kantin Online) berbasis Streamlit."""

from __future__ import annotations

import streamlit as st

import buyer_view
import db_service


def _init_session_state() -> None:
    """Menginisialisasi state bawaan aplikasi dan mock database."""
    db_service.init_db()
    if "user" not in st.session_state:
        st.session_state["user"] = None
    if "cart" not in st.session_state:
        st.session_state["cart"] = {"tenant_id": None, "items": {}}


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
        st.session_state["user"] = {
            "id": f"sso-{ticket[:8]}",
            "name": "Mahasiswa SSO UI",
            "npm": "2606000001",
            "role": "buyer",
        }
        st.query_params.clear()


def _render_login_page() -> None:
    """Merender halaman login sederhana bagi mahasiswa sebelum masuk ke etalase."""
    st.title("🍽️ Quentin — Queue Kantin Online")
    st.caption("Pesan makanan & minuman kantin satu fakultas tanpa antre lama.")

    col_left, col_right = st.columns([1.3, 1])
    with col_left:
        with st.container(border=True):
            st.subheader("🎓 Masuk sebagai Mahasiswa (Pembeli)")
            st.caption(
                "Masukkan Nama & NPM untuk mulai memesan. "
                "(Nantinya halaman ini akan terhubung ke Login SSO UI + Supabase)."
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
                    st.session_state["user"] = {
                        "id": f"npm-{clean_npm}",
                        "name": clean_name,
                        "npm": clean_npm,
                        "role": "buyer",
                    }
                    st.rerun()

            st.divider()
            if st.button("⚡ Login Cepat (Akun Demo)", use_container_width=True):
                st.session_state["user"] = {
                    "id": "npm-2606123456",
                    "name": "Hilmo (Demo)",
                    "npm": "2606123456",
                    "role": "buyer",
                }
                st.rerun()

    with col_right:
        with st.container(border=True):
            st.markdown("#### ✨ Alur Pemesanan Quentin")
            st.markdown(
                "1. Pilih kios & menu di **Etalase Kantin**.\n"
                "2. Checkout **1 kios** per pesanan & scan **QRIS khusus kios**.\n"
                "3. **Upload bukti pembayaran** (wajib) untuk masuk antrean.\n"
                "4. Pantau **Live Queue (2 Tahap)** dan ambil langsung di konter kios."
            )


def _render_sidebar(user: dict) -> None:
    """Merender sidebar profil mahasiswa, ringkasan keranjang, dan simulator penjual."""
    with st.sidebar:
        st.markdown("## 🍽️ Quentin")
        st.caption("Queue Kantin Online — Fakultas")
        st.divider()

        st.markdown("### 🎓 Profil Pembeli")
        st.markdown(f"**Nama:** {user['name']}")
        st.markdown(f"**NPM:** `{user['npm']}`")
        if st.button("🚪 Keluar (Logout)", use_container_width=True):
            st.session_state["user"] = None
            st.session_state["cart"] = {"tenant_id": None, "items": {}}
            st.rerun()

        st.divider()
        cart = st.session_state["cart"]
        cart_qty = sum(int(item["qty"]) for item in cart["items"].values())
        cart_total = sum(
            int(item["price"]) * int(item["qty"]) for item in cart["items"].values()
        )
        st.markdown("### 🛒 Ringkasan Keranjang")
        if cart_qty > 0 and cart["tenant_id"]:
            tenant = db_service.get_tenant_by_id(cart["tenant_id"])
            tenant_name = tenant["name"] if tenant else "-"
            st.caption(f"Kios: **{tenant_name}**")
            st.write(
                f"{cart_qty} item · **{buyer_view.format_rupiah(cart_total)}**"
            )
        else:
            st.caption("Keranjang masih kosong.")

        st.divider()
        with st.expander("🛠️ Simulasi Penjual (Testing Live Queue)", expanded=False):
            st.caption(
                "Panel sementara untuk mengetes perubahan status Live Queue dari sisi kios."
            )
            all_orders = db_service.get_all_orders()
            if not all_orders:
                st.info("Belum ada pesanan masuk.")
            else:
                for order in all_orders:
                    with st.container(border=True):
                        st.markdown(
                            f"**#{order['queue_number']}** · {order['tenant_name']}"
                        )
                        st.caption(
                            f"Pembeli: {order['buyer_name']} ({order['buyer_npm']}) | "
                            f"{buyer_view.format_rupiah(int(order['total_price']))}"
                        )
                        st.caption(f"Status saat ini: **{order['status']}**")
                        st.image(
                            order["payment_proof_bytes"],
                            caption=f"Bukti: {order['payment_filename']}",
                            width=180,
                        )
                        if order["status"] == db_service.STATUS_PREPARING:
                            if st.button(
                                "🔔 Tandai Sudah Bisa Diambil",
                                key=f"sim_ready_{order['id']}",
                                use_container_width=True,
                            ):
                                db_service.update_order_status(
                                    order["id"], db_service.STATUS_READY
                                )
                                st.rerun()
                        else:
                            if st.button(
                                "↩️ Kembalikan ke Menyiapkan",
                                key=f"sim_prep_{order['id']}",
                                use_container_width=True,
                            ):
                                db_service.update_order_status(
                                    order["id"], db_service.STATUS_PREPARING
                                )
                                st.rerun()


def main() -> None:
    """Menjalankan aplikasi utama Quentin."""
    st.set_page_config(
        page_title="Quentin - Queue Kantin Online",
        page_icon="🍽️",
        layout="wide",
    )
    _init_session_state()
    _handle_sso_callback_hook()

    user = st.session_state["user"]
    if user is None:
        _render_login_page()
        return

    _render_sidebar(user)
    st.title("🍽️ Quentin — Kantin Fakultas")
    buyer_view.render_buyer_view(user)


if __name__ == "__main__":
    main()
