"""Tampilan UI Role Penjual (Kios Kantin) untuk GoFood Kancil (Queue Kantin Online)."""

from __future__ import annotations

from typing import Any

import streamlit as st

import buyer_view
import db_service


def _set_pending_action(order_id: str | None, action: str | None = None) -> None:
    """Menyimpan atau membersihkan status konfirmasi ganda aksi penjual."""
    if order_id is None or action is None:
        st.session_state["seller_pending_action"] = None
    else:
        st.session_state["seller_pending_action"] = {
            "order_id": order_id,
            "action": action,
        }


def _render_order_status_badge(status: str) -> None:
    """Merender badge status pesanan pada kolom kiri kartu antrean penjual."""
    if status == db_service.STATUS_READY:
        st.success("100% · Sudah Bisa Diambil")
    elif status == db_service.STATUS_PREPARING:
        st.warning("50% · Sedang Disiapkan")
    elif status == db_service.STATUS_REJECTED:
        st.error("Pembayaran Ditolak")
    else:
        st.info("0% · Menunggu Konfirmasi")


def _render_order_actions(order: dict[str, Any]) -> None:
    """Merender tombol aksi penjual lengkap dengan konfirmasi ganda."""
    order_id = order["id"]
    status = order["status"]
    pending = st.session_state.get("seller_pending_action")
    active_action = (
        pending["action"]
        if pending and pending.get("order_id") == order_id
        else None
    )

    if status == db_service.STATUS_PENDING_PAYMENT:
        if active_action == "confirm_payment":
            st.warning("Konfirmasi bukti QRIS sudah valid & nominal sesuai?")
            if st.button(
                "✅ Ya, Konfirmasi & Siapkan",
                key=f"confirm_yes_{order_id}",
                type="primary",
                use_container_width=True,
            ):
                db_service.update_order_status(order_id, db_service.STATUS_PREPARING)
                _set_pending_action(None)
                st.rerun()
            if st.button(
                "❌ Batal",
                key=f"confirm_cancel_{order_id}",
                use_container_width=True,
            ):
                _set_pending_action(None)
                st.rerun()
        elif active_action == "reject_payment":
            st.error("Yakin ingin menolak bukti pembayaran pesanan ini?")
            reject_reason = st.text_input(
                "Alasan Penolakan (Opsional)",
                placeholder="Contoh: Nominal tidak sesuai / bukti buram",
                key=f"reject_reason_{order_id}",
            )
            if st.button(
                "🚫 Ya, Tolak Pesanan",
                key=f"reject_yes_{order_id}",
                type="primary",
                use_container_width=True,
            ):
                db_service.update_order_status(
                    order_id,
                    db_service.STATUS_REJECTED,
                    rejection_reason=reject_reason,
                )
                _set_pending_action(None)
                st.rerun()
            if st.button(
                "❌ Batal",
                key=f"reject_cancel_{order_id}",
                use_container_width=True,
            ):
                _set_pending_action(None)
                st.rerun()
        else:
            if st.button(
                "✅ Konfirmasi Pembayaran",
                key=f"btn_confirm_pay_{order_id}",
                type="primary",
                use_container_width=True,
            ):
                _set_pending_action(order_id, "confirm_payment")
                st.rerun()
            if st.button(
                "❌ Tolak Pembayaran",
                key=f"btn_reject_pay_{order_id}",
                type="secondary",
                use_container_width=True,
            ):
                _set_pending_action(order_id, "reject_payment")
                st.rerun()

    elif status == db_service.STATUS_PREPARING:
        if active_action == "mark_ready":
            st.warning("Pastikan pesanan sudah selesai & siap diambil di konter!")
            if st.button(
                "🔔 Ya, Sudah Bisa Diambil",
                key=f"ready_yes_{order_id}",
                type="primary",
                use_container_width=True,
            ):
                db_service.update_order_status(order_id, db_service.STATUS_READY)
                _set_pending_action(None)
                st.rerun()
            if st.button(
                "❌ Batal",
                key=f"ready_cancel_{order_id}",
                use_container_width=True,
            ):
                _set_pending_action(None)
                st.rerun()
        else:
            if st.button(
                "🔔 Tandai Pesanan Sudah Bisa Diambil",
                key=f"seller_ready_{order_id}",
                type="primary",
                use_container_width=True,
            ):
                _set_pending_action(order_id, "mark_ready")
                st.rerun()

    elif status == db_service.STATUS_READY:
        if st.button(
            "↩️ Kembalikan ke Sedang Menyiapkan",
            key=f"seller_prep_{order_id}",
            use_container_width=True,
        ):
            db_service.update_order_status(order_id, db_service.STATUS_PREPARING)
            _set_pending_action(None)
            st.rerun()

    else:
        st.caption("Pesanan ini telah ditolak.")


def _render_orders_tab(tenant: dict[str, Any]) -> None:
    """Merender Tab 1 Penjual: Dashboard antrean pesanan masuk secara berurutan (FIFO)."""
    orders = db_service.get_tenant_orders(tenant["id"])

    status_counts = {
        status: sum(1 for o in orders if o["status"] == status)
        for status in db_service.VALID_ORDER_STATUSES
    }
    confirmed_revenue = sum(
        int(o["total_price"])
        for o in orders
        if o["status"] in (db_service.STATUS_PREPARING, db_service.STATUS_READY)
    )

    m1, m2, m3, m4, m5 = st.columns([1.1, 1.1, 1.1, 1.4, 0.9])
    with m1:
        st.metric(
            "Menunggu Konfirmasi", status_counts[db_service.STATUS_PENDING_PAYMENT]
        )
    with m2:
        st.metric("Sedang Disiapkan", status_counts[db_service.STATUS_PREPARING])
    with m3:
        st.metric("Sudah Bisa Diambil", status_counts[db_service.STATUS_READY])
    with m4:
        st.metric(
            "Pendapatan Terkonfirmasi",
            buyer_view.format_rupiah(confirmed_revenue),
        )
    with m5:
        st.write("")
        if st.button("🔄 Refresh Antrean", use_container_width=True):
            db_service.clear_cache()
            st.rerun()

    nav_labels = {
        db_service.STATUS_PENDING_PAYMENT: "Menunggu Konfirmasi",
        db_service.STATUS_PREPARING: "Sedang Disiapkan",
        db_service.STATUS_READY: "Sudah Bisa Diambil",
        db_service.STATUS_REJECTED: "Ditolak",
    }
    selected_status = st.segmented_control(
        "Navigasi Status Antrean",
        options=list(nav_labels.keys()),
        default=db_service.STATUS_PENDING_PAYMENT,
        required=True,
        format_func=lambda status: f"{nav_labels[status]} ({status_counts[status]})",
        label_visibility="collapsed",
        width="stretch",
        key=f"seller_order_nav_{tenant['id']}",
    )
    if selected_status is None:
        selected_status = db_service.STATUS_PENDING_PAYMENT

    filtered_orders = [o for o in orders if o["status"] == selected_status]

    if not filtered_orders:
        st.info("Belum ada pesanan pada kategori antrean ini.")
        return

    for order in filtered_orders:
        with st.container(border=True):
            left_col, mid_col, right_col = st.columns([1.1, 2.4, 1.5])
            with left_col:
                st.caption("Nomor Antrean")
                st.markdown(f"# `#{order['queue_number']}`")
                _render_order_status_badge(order["status"])

            with mid_col:
                st.markdown(
                    f"#### {order['buyer_name']} (`{order['buyer_npm']}`)"
                )
                st.caption(
                    f"{order['created_at']} · **{buyer_view.format_rupiah(int(order['total_price']))}** · {order['pickup_method']}"
                )
                for item in order["items"]:
                    st.markdown(
                        f"- **{item['name']}** × {item['qty']} "
                        f"({buyer_view.format_rupiah(int(item['price']) * int(item['qty']))})"
                    )
                if order["notes"]:
                    st.info(f"**Catatan Pembeli:** {order['notes']}")
                else:
                    st.caption("Tidak ada catatan khusus dari pembeli.")
                if (
                    order["status"] == db_service.STATUS_REJECTED
                    and order.get("rejection_reason")
                ):
                    st.error(
                        f"**Alasan Penolakan:** {order['rejection_reason']}"
                    )

            with right_col:
                st.write("")
                _render_order_actions(order)

            auto_expand_proof = (
                order["status"] == db_service.STATUS_PENDING_PAYMENT
            )
            with st.expander(
                "Verifikasi Bukti Pembayaran QRIS", expanded=auto_expand_proof
            ):
                st.image(
                    order["payment_proof_bytes"],
                    caption=f"File: {order['payment_filename']}",
                    width=260,
                )


def _render_menus_tab(tenant: dict[str, Any]) -> None:
    """Merender Tab 2 Penjual: Tambah, edit, hapus, dan ubah stok menu."""
    with st.expander("Tambah Menu Baru", expanded=False):
        with st.form(f"add_menu_form_{tenant['id']}", clear_on_submit=True):
            c1, c2 = st.columns([2.2, 1.2])
            with c1:
                new_name = st.text_input(
                    "Nama Menu", placeholder="Contoh: Ayam Bakar Madu + Nasi"
                )
            with c2:
                new_price = st.number_input(
                    "Harga (Rp)", min_value=1000, step=1000, value=15000
                )

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
                        emoji="",
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
                in_stock = bool(menu["is_available"])
                stock_badge = "Tersedia" if in_stock else "Habis"

                st.markdown(f"#### {menu['name']}")
                st.caption(menu.get("description", ""))
                st.markdown(
                    f"**{buyer_view.format_rupiah(int(menu['price']))}** · {stock_badge}"
                )

                btn_stock_col, btn_del_col = st.columns(2)
                with btn_stock_col:
                    if st.button(
                        "❌ Set Habis" if in_stock else "✅ Set Tersedia",
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

                with st.expander("Edit Menu"):
                    with st.form(f"edit_menu_{menu['id']}"):
                        edit_name = st.text_input("Nama Menu", value=menu["name"])
                        edit_price = st.number_input(
                            "Harga (Rp)",
                            min_value=1000,
                            step=1000,
                            value=max(1000, int(menu["price"])),
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
                                    emoji=menu.get("emoji", ""),
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
        status_badge = (
            "**Kios Sedang Buka**"
            if tenant["is_open"]
            else "**Kios Sedang Tutup**"
        )
        st.markdown(f"### {tenant['name']}  |  {status_badge}")
        st.caption(tenant["description"])
    with toggle_col:
        st.write("")
        if st.button(
            "🔴 Tutup Kios" if tenant["is_open"] else "🟢 Buka Kios",
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
            f"Dashboard Pesanan Masuk ({orders_count})",
            f"Kelola Menu ({menus_count})",
        ]
    )

    with tab_orders:
        _render_orders_tab(tenant)
    with tab_menus:
        _render_menus_tab(tenant)
