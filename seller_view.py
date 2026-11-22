"""Tampilan UI Role Penjual (Kios Kantin) untuk GoFood Kancil (Queue Kantin Online)."""

from __future__ import annotations

from typing import Any

import streamlit as st

import buyer_view
import db_service


def _render_orders_tab(tenant: dict[str, Any]) -> None:
    """Merender Tab 1 Penjual: Dashboard antrean pesanan masuk secara berurutan (FIFO)."""
    orders = db_service.get_tenant_orders(tenant["id"])

    preparing_count = sum(
        1 for o in orders if o["status"] == db_service.STATUS_PREPARING
    )
    ready_count = sum(1 for o in orders if o["status"] == db_service.STATUS_READY)
    total_revenue = sum(int(o["total_price"]) for o in orders)

    m1, m2, m3, m4 = st.columns([1, 1, 1.3, 0.8])
    with m1:
        st.metric("🍳 Sedang Disiapkan", preparing_count)
    with m2:
        st.metric("🔔 Sudah Bisa Diambil", ready_count)
    with m3:
        st.metric("💰 Total Pendapatan", buyer_view.format_rupiah(total_revenue))
    with m4:
        st.write("")
        if st.button("🔄 Refresh Antrean", use_container_width=True):
            st.rerun()

    filter_choice = st.radio(
        "Filter Status Antrean:",
        options=["Semua", "Sedang Disiapkan", "Sudah Bisa Diambil"],
        horizontal=True,
        key=f"seller_order_filter_{tenant['id']}",
    )

    if filter_choice == "Sedang Disiapkan":
        filtered_orders = [
            o for o in orders if o["status"] == db_service.STATUS_PREPARING
        ]
    elif filter_choice == "Sudah Bisa Diambil":
        filtered_orders = [
            o for o in orders if o["status"] == db_service.STATUS_READY
        ]
    else:
        filtered_orders = orders

    if not filtered_orders:
        st.info("Belum ada pesanan pada kategori antrean ini.")
        return

    for order in filtered_orders:
        with st.container(border=True):
            left_col, mid_col, right_col = st.columns([1.1, 2.5, 1.4])
            with left_col:
                st.caption("Nomor Antrean")
                st.markdown(f"# `#{order['queue_number']}`")
                if order["status"] == db_service.STATUS_READY:
                    st.success("🔔 Sudah Bisa Diambil")
                else:
                    st.warning("🍳 Sedang Disiapkan")

            with mid_col:
                st.markdown(
                    f"#### {order['buyer_name']} (`{order['buyer_npm']}`)"
                )
                st.caption(
                    f"🕒 {order['created_at']} · 💰 **{buyer_view.format_rupiah(int(order['total_price']))}** · 📍 {order['pickup_method']}"
                )
                for item in order["items"]:
                    st.markdown(
                        f"- {item.get('emoji', '🍽️')} **{item['name']}** × {item['qty']} "
                        f"({buyer_view.format_rupiah(int(item['price']) * int(item['qty']))})"
                    )
                if order["notes"]:
                    st.info(f"📝 **Catatan Pembeli:** {order['notes']}")
                else:
                    st.caption("📝 Tidak ada catatan khusus dari pembeli.")

            with right_col:
                st.write("")
                if order["status"] == db_service.STATUS_PREPARING:
                    if st.button(
                        "🔔 Tandai Pesanan Sudah Bisa Diambil",
                        key=f"seller_ready_{order['id']}",
                        type="primary",
                        use_container_width=True,
                    ):
                        db_service.update_order_status(
                            order["id"], db_service.STATUS_READY
                        )
                        st.rerun()
                else:
                    if st.button(
                        "↩️ Kembalikan ke Sedang Menyiapkan",
                        key=f"seller_prep_{order['id']}",
                        use_container_width=True,
                    ):
                        db_service.update_order_status(
                            order["id"], db_service.STATUS_PREPARING
                        )
                        st.rerun()

            with st.expander("🧾 Verifikasi Bukti Pembayaran QRIS"):
                st.image(
                    order["payment_proof_bytes"],
                    caption=f"File: {order['payment_filename']}",
                    width=260,
                )


def _render_menus_tab(tenant: dict[str, Any]) -> None:
    """Merender Tab 2 Penjual: Tambah, edit, hapus, dan ubah stok menu."""
    with st.expander("➕ Tambah Menu Baru", expanded=False):
        with st.form(f"add_menu_form_{tenant['id']}", clear_on_submit=True):
            c1, c2, c3 = st.columns([2.2, 1.2, 0.8])
            with c1:
                new_name = st.text_input(
                    "Nama Menu", placeholder="Contoh: Ayam Bakar Madu + Nasi"
                )
            with c2:
                new_price = st.number_input(
                    "Harga (Rp)", min_value=1000, step=1000, value=15000
                )
            with c3:
                new_emoji = st.text_input("Emoji/Ikon", value="🍽️")

            new_desc = st.text_area(
                "Deskripsi Singkat",
                placeholder="Contoh: Ayam bakar bumbu madu + lalapan dan sambal.",
            )
            new_avail = st.checkbox("Stok Tersedia", value=True)
            submitted = st.form_submit_button(
                "💾 Simpan Menu Baru", type="primary", use_container_width=True
            )

            if submitted:
                if not new_name.strip():
                    st.error("Nama menu wajib diisi.")
                else:
                    db_service.add_menu(
                        tenant_id=tenant["id"],
                        name=new_name,
                        price=int(new_price),
                        description=new_desc,
                        emoji=new_emoji,
                        is_available=new_avail,
                    )
                    st.rerun()

    st.divider()
    menus = db_service.get_menus_by_tenant(tenant["id"])
    if not menus:
        st.info("Kios ini belum memiliki menu. Tambahkan menu baru di atas.")
        return

    cols = st.columns(2)
    for idx, menu in enumerate(menus):
        with cols[idx % 2]:
            with st.container(border=True):
                emoji = menu.get("emoji", "🍽️")
                in_stock = bool(menu["is_available"])
                stock_badge = "✅ Tersedia" if in_stock else "❌ Habis"

                st.markdown(f"#### {emoji} {menu['name']}")
                st.caption(menu.get("description", ""))
                st.markdown(
                    f"**{buyer_view.format_rupiah(int(menu['price']))}** · {stock_badge}"
                )

                btn_stock_col, btn_del_col = st.columns(2)
                with btn_stock_col:
                    toggle_label = "❌ Set Habis" if in_stock else "✅ Set Tersedia"
                    if st.button(
                        toggle_label,
                        key=f"toggle_stock_{menu['id']}",
                        use_container_width=True,
                    ):
                        db_service.toggle_menu_availability(
                            menu["id"], not in_stock
                        )
                        st.rerun()

                with btn_del_col:
                    if st.button(
                        "🗑️ Hapus",
                        key=f"delete_menu_{menu['id']}",
                        use_container_width=True,
                    ):
                        db_service.delete_menu(menu["id"])
                        st.rerun()

                with st.expander("✏️ Edit Menu"):
                    with st.form(f"edit_menu_{menu['id']}"):
                        edit_name = st.text_input("Nama Menu", value=menu["name"])
                        ec1, ec2 = st.columns([1.4, 0.8])
                        with ec1:
                            edit_price = st.number_input(
                                "Harga (Rp)",
                                min_value=1000,
                                step=1000,
                                value=max(1000, int(menu["price"])),
                            )
                        with ec2:
                            edit_emoji = st.text_input(
                                "Emoji", value=menu.get("emoji", "🍽️")
                            )
                        edit_desc = st.text_area(
                            "Deskripsi", value=menu.get("description", "")
                        )
                        edit_avail = st.checkbox(
                            "Stok Tersedia", value=bool(menu["is_available"])
                        )
                        save_edit = st.form_submit_button(
                            "Simpan Perubahan", use_container_width=True
                        )

                        if save_edit:
                            if not edit_name.strip():
                                st.error("Nama menu tidak boleh kosong.")
                            else:
                                db_service.update_menu(
                                    menu_id=menu["id"],
                                    name=edit_name,
                                    price=int(edit_price),
                                    description=edit_desc,
                                    emoji=edit_emoji,
                                    is_available=edit_avail,
                                )
                                st.rerun()


def render_seller_view(user: dict[str, Any]) -> None:
    """Merender seluruh halaman MVP Role Penjual (Kios Kantin)."""
    tenant_id = user.get("tenant_id")
    tenant = db_service.get_tenant_by_id(tenant_id) if tenant_id else None
    if tenant is None:
        st.error("Data kios untuk akun penjual ini tidak ditemukan.")
        return

    head_col, toggle_col = st.columns([3, 1.2])
    with head_col:
        emoji = tenant.get("emoji", "🏪")
        status_badge = (
            "🟢 **Kios Sedang Buka**"
            if tenant["is_open"]
            else "🔴 **Kios Sedang Tutup**"
        )
        st.markdown(f"### {emoji} {tenant['name']}  |  {status_badge}")
        st.caption(tenant["description"])
    with toggle_col:
        st.write("")
        toggle_btn_label = (
            "🔴 Tutup Kios" if tenant["is_open"] else "🟢 Buka Kios"
        )
        if st.button(
            toggle_btn_label,
            key=f"seller_toggle_open_{tenant['id']}",
            type="secondary" if tenant["is_open"] else "primary",
            use_container_width=True,
        ):
            db_service.toggle_tenant_open(tenant["id"], not tenant["is_open"])
            st.rerun()

    orders_count = len(db_service.get_tenant_orders(tenant["id"]))
    menus_count = len(db_service.get_menus_by_tenant(tenant["id"]))

    tab_orders, tab_menus = st.tabs(
        [
            f"📋 Dashboard Pesanan Masuk ({orders_count})",
            f"🍔 Kelola Menu ({menus_count})",
        ]
    )

    with tab_orders:
        _render_orders_tab(tenant)
    with tab_menus:
        _render_menus_tab(tenant)
