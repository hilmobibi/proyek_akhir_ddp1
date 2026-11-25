"""Tampilan UI Role Penjual (Kios Kantin) untuk Pesan Kancil — Tema Putih-Abu."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

import db_service
import ui_theme

SELLER_NAV_ORDERS = "Pesanan"
SELLER_NAV_MENUS = "Kelola Menu"
SELLER_NAV_PROFILE = "Profil Kios"


def _set_pending_action(order_id: str | None, action: str | None = None) -> None:
    """Menyimpan atau membersihkan status konfirmasi ganda aksi penjual."""
    if order_id is None or action is None:
        st.session_state["seller_pending_action"] = None
    else:
        st.session_state["seller_pending_action"] = {
            "order_id": order_id,
            "action": action,
        }


def _on_seller_nav_change() -> None:
    """Callback klik bottom navbar Penjual."""
    chosen = st.session_state.get("seller_bottom_nav_ctrl")
    if chosen:
        st.session_state["seller_nav"] = chosen
        st.session_state["seller_nav_synced"] = chosen


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
            st.caption("Konfirmasi bukti QRIS sudah valid & nominal sesuai?")
            if st.button(
                "Ya, Konfirmasi & Siapkan",
                key=f"confirm_yes_{order_id}",
                type="primary",
                use_container_width=True,
            ):
                db_service.update_order_status(order_id, db_service.STATUS_PREPARING)
                _set_pending_action(None)
                st.rerun()
            if st.button(
                "Batal",
                key=f"confirm_cancel_{order_id}",
                use_container_width=True,
            ):
                _set_pending_action(None)
                st.rerun()
        elif active_action == "reject_payment":
            st.caption("Yakin ingin menolak bukti pembayaran pesanan ini?")
            reject_reason = st.text_input(
                "Alasan Penolakan (Opsional)",
                placeholder="Contoh: Nominal tidak sesuai / bukti buram",
                key=f"reject_reason_{order_id}",
            )
            if st.button(
                "Ya, Tolak Pesanan",
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
                "Batal",
                key=f"reject_cancel_{order_id}",
                use_container_width=True,
            ):
                _set_pending_action(None)
                st.rerun()
        else:
            if st.button(
                "Konfirmasi Pembayaran",
                key=f"btn_confirm_pay_{order_id}",
                type="primary",
                use_container_width=True,
            ):
                _set_pending_action(order_id, "confirm_payment")
                st.rerun()
            if st.button(
                "Tolak Pembayaran",
                key=f"btn_reject_pay_{order_id}",
                type="secondary",
                use_container_width=True,
            ):
                _set_pending_action(order_id, "reject_payment")
                st.rerun()

    elif status == db_service.STATUS_PREPARING:
        if active_action == "mark_ready":
            st.caption("Pastikan pesanan sudah selesai & siap diambil di konter.")
            if st.button(
                "Ya, Sudah Bisa Diambil",
                key=f"ready_yes_{order_id}",
                type="primary",
                use_container_width=True,
            ):
                db_service.update_order_status(order_id, db_service.STATUS_READY)
                _set_pending_action(None)
                st.rerun()
            if st.button(
                "Batal",
                key=f"ready_cancel_{order_id}",
                use_container_width=True,
            ):
                _set_pending_action(None)
                st.rerun()
        else:
            if st.button(
                "Tandai Sudah Bisa Diambil",
                key=f"seller_ready_{order_id}",
                type="primary",
                use_container_width=True,
            ):
                _set_pending_action(order_id, "mark_ready")
                st.rerun()

    elif status == db_service.STATUS_READY:
        if st.button(
            "Kembalikan ke Disiapkan",
            key=f"seller_prep_{order_id}",
            use_container_width=True,
        ):
            db_service.update_order_status(order_id, db_service.STATUS_PREPARING)
            _set_pending_action(None)
            st.rerun()

    else:
        st.caption("Pesanan ini telah ditolak.")


def _render_orders_screen(tenant: dict[str, Any]) -> None:
    """Merender layar Dashboard Antrean Pesanan Masuk Penjual."""
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
            "Perlu Verifikasi", status_counts[db_service.STATUS_PENDING_PAYMENT]
        )
    with m2:
        st.metric("Disiapkan", status_counts[db_service.STATUS_PREPARING])
    with m3:
        st.metric("Siap Diambil", status_counts[db_service.STATUS_READY])
    with m4:
        st.metric("Pendapatan", ui_theme.format_rupiah(confirmed_revenue))
    with m5:
        st.write("")
        if st.button("Perbarui", use_container_width=True):
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
        wrap=False,
        format_func=lambda s: f"{nav_labels[s]} ({status_counts[s]})",
        label_visibility="collapsed",
        width="stretch",
        key=f"seller_order_nav_{tenant['id']}",
    )
    if selected_status is None:
        selected_status = db_service.STATUS_PENDING_PAYMENT

    filtered_orders = [o for o in orders if o["status"] == selected_status]
    if not filtered_orders:
        st.markdown(
            '<div class="gf-surface-note">Belum ada pesanan pada kategori status ini.</div>',
            unsafe_allow_html=True,
        )
        return

    for order in filtered_orders:
        with st.container(border=True):
            left_col, mid_col, right_col = st.columns([1.0, 2.5, 1.5])
            with left_col:
                st.caption("Nomor Antrean")
                st.markdown(
                    "<div style='font-size:28px;font-weight:700;letter-spacing:-0.03em;color:#18181B;'>"
                    f"#{html.escape(order['queue_number'])}</div>",
                    unsafe_allow_html=True,
                )
                st.caption(order["created_at"])

            with mid_col:
                st.markdown(
                    f"#### {order['buyer_name']} (`{order['buyer_npm']}`)"
                )
                for item in order["items"]:
                    st.markdown(
                        f"- **{item['name']}** × {item['qty']} "
                        f"({ui_theme.format_rupiah(int(item['price']) * int(item['qty']))})"
                    )
                st.caption(
                    f"Total: **{ui_theme.format_rupiah(int(order['total_price']))}** · {order['pickup_method']}"
                )
                if order["notes"]:
                    st.markdown(
                        f'<div class="gf-surface-note" style="margin-top:6px;">'
                        f"<b>Catatan Pembeli:</b> {html.escape(order['notes'])}</div>",
                        unsafe_allow_html=True,
                    )
                if (
                    order["status"] == db_service.STATUS_REJECTED
                    and order.get("rejection_reason")
                ):
                    st.markdown(
                        f'<div class="gf-surface-note" style="margin-top:6px;">'
                        f"<b>Alasan Penolakan:</b> {html.escape(order['rejection_reason'])}</div>",
                        unsafe_allow_html=True,
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
                    width=240,
                )


def _render_menus_screen(tenant: dict[str, Any]) -> None:
    """Merender layar Kelola Menu dengan foto makanan & upload foto oleh penjual."""
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
            new_photo = st.file_uploader(
                "Foto Menu (PNG / JPG - Opsional)",
                type=["png", "jpg", "jpeg"],
                key=f"add_menu_photo_{tenant['id']}",
            )
            new_avail = st.checkbox("Stok Tersedia", value=True)
            submitted = st.form_submit_button(
                "Simpan Menu Baru", type="primary", use_container_width=True
            )

            if submitted:
                if not new_name.strip():
                    st.error("Nama menu wajib diisi.")
                else:
                    image_data_uri = ""
                    if new_photo is not None:
                        img_bytes, img_name = db_service.encode_uploaded_file(
                            new_photo
                        )
                        image_data_uri = db_service.bytes_to_base64_data_uri(
                            img_bytes, img_name
                        )
                    db_service.add_menu(
                        tenant_id=tenant["id"],
                        name=new_name,
                        price=int(new_price),
                        description=new_desc,
                        emoji="",
                        is_available=new_avail,
                        image_url=image_data_uri,
                    )
                    st.rerun()

    menus = db_service.get_menus_by_tenant(tenant["id"])
    if not menus:
        st.markdown(
            '<div class="gf-surface-note">Kios ini belum memiliki menu. Tambahkan menu baru di atas.</div>',
            unsafe_allow_html=True,
        )
        return

    cols = st.columns(min(3, len(menus)))
    for idx, menu in enumerate(menus):
        in_stock = bool(menu["is_available"])
        with cols[idx % len(cols)]:
            with st.container(border=True):
                st.markdown(
                    ui_theme.render_media_html(
                        menu.get("image_url", ""),
                        menu["name"],
                        dimmed=not in_stock,
                        badge_text="TERSEDIA" if in_stock else "HABIS",
                        badge_open=in_stock,
                    ),
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<p class="gf-title">{html.escape(menu["name"])}</p>'
                    f'<p class="gf-desc">{html.escape(menu.get("description", ""))}</p>'
                    f'<p class="gf-price">{ui_theme.format_rupiah(int(menu["price"]))}</p>',
                    unsafe_allow_html=True,
                )

                btn_stock_col, btn_del_col = st.columns(2)
                with btn_stock_col:
                    if st.button(
                        "Set Habis" if in_stock else "Set Tersedia",
                        key=f"toggle_stock_{menu['id']}",
                        use_container_width=True,
                    ):
                        db_service.toggle_menu_availability(
                            menu["id"], not in_stock
                        )
                        st.rerun()

                with btn_del_col:
                    if st.button(
                        "Hapus",
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
                        edit_photo = st.file_uploader(
                            "Ganti Foto Menu (Opsional)",
                            type=["png", "jpg", "jpeg"],
                            key=f"edit_photo_{menu['id']}",
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
                                new_img_uri: str | None = None
                                if edit_photo is not None:
                                    img_b, img_n = db_service.encode_uploaded_file(
                                        edit_photo
                                    )
                                    new_img_uri = (
                                        db_service.bytes_to_base64_data_uri(
                                            img_b, img_n
                                        )
                                    )
                                db_service.update_menu(
                                    menu_id=menu["id"],
                                    name=edit_name,
                                    price=int(edit_price),
                                    description=edit_desc,
                                    emoji="",
                                    is_available=edit_avail,
                                    image_url=new_img_uri,
                                )
                                st.rerun()


def _render_profile_screen(tenant: dict[str, Any]) -> None:
    """Merender layar Profil Kios: unggah foto kios & lihat QRIS kios."""
    c_photo, c_qris = st.columns([1.3, 1])
    with c_photo:
        with st.container(border=True):
            st.markdown("#### Foto Kios Kantin")
            st.caption(
                "Foto ini tampil di halaman utama Etalase Kantin untuk pembeli."
            )
            st.markdown(
                ui_theme.render_media_html(
                    tenant.get("image_url", ""),
                    tenant["name"],
                    dimmed=not tenant["is_open"],
                ),
                unsafe_allow_html=True,
            )
            uploaded_kios_photo = st.file_uploader(
                "Unggah Foto Kios Baru (PNG / JPG)",
                type=["png", "jpg", "jpeg"],
                key=f"upload_kios_photo_{tenant['id']}",
            )
            if st.button(
                "Simpan Foto Kios",
                type="primary",
                disabled=uploaded_kios_photo is None,
                use_container_width=True,
            ):
                db_service.update_tenant_image(
                    tenant["id"],
                    uploaded_kios_photo.getvalue(),
                    uploaded_kios_photo.name,
                )
                st.rerun()

    with c_qris:
        with st.container(border=True):
            st.markdown("#### QRIS Pembayaran Kios")
            if tenant.get("qris_image_b64"):
                st.caption("QRIS asli kios sudah terpasang dan tampil di halaman checkout pembeli.")
            else:
                st.caption("Saat ini masih memakai QRIS contoh bawaan. Unggah QRIS aslimu di bawah.")
            st.image(db_service.get_tenant_qris_display(tenant), width=260)
            uploaded_qris = st.file_uploader(
                "Unggah Gambar QRIS Asli Kios (PNG / JPG)",
                type=["png", "jpg", "jpeg"],
                key=f"upload_kios_qris_{tenant['id']}",
            )
            if st.button(
                "Simpan QRIS Kios",
                key=f"save_kios_qris_{tenant['id']}",
                type="primary",
                disabled=uploaded_qris is None,
                use_container_width=True,
            ):
                db_service.update_tenant_qris(
                    tenant["id"],
                    uploaded_qris.getvalue(),
                    uploaded_qris.name,
                )
                st.rerun()


def render_seller_view(user: dict[str, Any]) -> None:
    """Merender seluruh halaman Role Penjual dengan floating bottom navbar 1 baris."""
    tenant_id = user.get("tenant_id")
    tenant = db_service.get_tenant_by_id(tenant_id) if tenant_id else None
    if tenant is None:
        st.error("Data kios untuk akun penjual ini tidak ditemukan.")
        return

    if "seller_nav" not in st.session_state:
        st.session_state["seller_nav"] = SELLER_NAV_ORDERS

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
            st.caption(tenant.get("description", ""))
        with h_right:
            if st.button(
                "Tutup Kios" if tenant["is_open"] else "Buka Kios",
                key=f"seller_toggle_open_{tenant['id']}",
                type="secondary" if tenant["is_open"] else "primary",
                use_container_width=True,
            ):
                db_service.toggle_tenant_open(tenant["id"], not tenant["is_open"])
                st.rerun()

    orders_count = len(db_service.get_tenant_orders(tenant["id"]))
    menus_count = len(db_service.get_menus_by_tenant(tenant["id"]))

    if st.session_state.get("seller_nav_synced") != st.session_state["seller_nav"]:
        st.session_state["seller_bottom_nav_ctrl"] = st.session_state["seller_nav"]
        st.session_state["seller_nav_synced"] = st.session_state["seller_nav"]

    nav_labels = {
        SELLER_NAV_ORDERS: f"Pesanan ({orders_count})" if orders_count else "Pesanan",
        SELLER_NAV_MENUS: f"Kelola Menu ({menus_count})",
        SELLER_NAV_PROFILE: "Profil Kios",
    }

    with st.container(key="bottom_nav"):
        st.segmented_control(
            "Navigasi Penjual",
            options=[SELLER_NAV_ORDERS, SELLER_NAV_MENUS, SELLER_NAV_PROFILE],
            format_func=lambda k: nav_labels[k],
            required=True,
            wrap=False,
            label_visibility="collapsed",
            width="stretch",
            key="seller_bottom_nav_ctrl",
            on_change=_on_seller_nav_change,
        )

    active = st.session_state["seller_nav"]
    if active == SELLER_NAV_ORDERS:
        _render_orders_screen(tenant)
    elif active == SELLER_NAV_MENUS:
        _render_menus_screen(tenant)
    else:
        _render_profile_screen(tenant)
