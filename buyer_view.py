"""Tampilan UI Role Pembeli (Mahasiswa) untuk GoFood Kancil (Queue Kantin Online)."""

from __future__ import annotations

from typing import Any

import streamlit as st

import db_service


def format_rupiah(amount: int) -> str:
    """Memformat angka integer menjadi string mata uang Rupiah (mis. Rp15.000)."""
    return f"Rp{amount:,}".replace(",", ".")


def _reset_cart() -> None:
    """Mengosongkan keranjang belanja aktif di session state."""
    st.session_state["cart"] = {"tenant_id": None, "items": {}}


def _add_to_cart(tenant_id: str, menu: dict[str, Any]) -> None:
    """Menambahkan 1 porsi menu ke keranjang belanja."""
    cart = st.session_state["cart"]
    if cart["tenant_id"] is None:
        cart["tenant_id"] = tenant_id

    menu_id = menu["id"]
    if menu_id in cart["items"]:
        cart["items"][menu_id]["qty"] += 1
    else:
        cart["items"][menu_id] = {
            "menu_id": menu_id,
            "name": menu["name"],
            "price": int(menu["price"]),
            "qty": 1,
        }


def _change_cart_qty(menu_id: str, delta: int) -> None:
    """Mengubah jumlah item di keranjang; menghapus item jika jumlah <= 0."""
    cart = st.session_state["cart"]
    items = cart["items"]
    if menu_id not in items:
        return

    new_qty = items[menu_id]["qty"] + delta
    if new_qty <= 0:
        del items[menu_id]
    else:
        items[menu_id]["qty"] = new_qty

    if not items:
        cart["tenant_id"] = None


def _render_tenant_grid(tenants: list[dict[str, Any]]) -> None:
    """Merender Tahap A: Grid pilihan kios kantin."""
    st.markdown("### Pilih Kios Kantin")
    st.caption("Klik salah satu kios untuk melihat daftar menu dan mulai memesan.")

    num_cols = min(3, len(tenants))
    cols = st.columns(num_cols)
    for idx, tenant in enumerate(tenants):
        menus = db_service.get_menus_by_tenant(tenant["id"])
        avail_count = sum(1 for m in menus if m["is_available"])
        total_count = len(menus)
        status_badge = "Buka" if tenant["is_open"] else "Tutup"

        with cols[idx % num_cols]:
            with st.container(border=True):
                st.markdown(f"#### {tenant['name']}")
                st.markdown(
                    f"**{status_badge}** · {avail_count}/{total_count} menu tersedia"
                )
                st.caption(tenant["description"])
                if st.button(
                    "🍽️ Lihat Menu",
                    key=f"open_tenant_{tenant['id']}",
                    type="primary" if tenant["is_open"] else "secondary",
                    use_container_width=True,
                ):
                    st.session_state["active_storefront_tenant_id"] = tenant["id"]
                    st.rerun()


def _render_menu_grid(tenants: list[dict[str, Any]], active_tenant_id: str) -> None:
    """Merender Tahap B: Grid pilihan menu milik kios yang dipilih."""
    tenant_map = {t["id"]: t for t in tenants}
    tenant = tenant_map.get(active_tenant_id)
    if tenant is None:
        st.session_state["active_storefront_tenant_id"] = None
        st.rerun()
        return

    if st.button("⬅️ Kembali ke Daftar Kios", key="back_to_tenant_grid"):
        st.session_state["active_storefront_tenant_id"] = None
        st.rerun()

    status_badge = (
        "**Kios Sedang Buka**" if tenant["is_open"] else "**Kios Sedang Tutup**"
    )
    st.markdown(f"### {tenant['name']}  |  {status_badge}")
    st.caption(tenant["description"])

    if not tenant["is_open"]:
        st.info(
            "Kios ini sedang tutup sementara. Kamu tetap bisa melihat menu, tetapi pemesanan dinonaktifkan."
        )

    cart = st.session_state["cart"]
    cart_locked_other_tenant = (
        cart["tenant_id"] is not None
        and cart["tenant_id"] != tenant["id"]
        and bool(cart["items"])
    )
    if cart_locked_other_tenant:
        active_tenant = tenant_map.get(cart["tenant_id"])
        active_name = active_tenant["name"] if active_tenant else "kios lain"
        st.warning(
            f"Keranjangmu sedang berisi menu dari **{active_name}**. "
            "Karena tiap kios memiliki QRIS pembayaran berbeda, checkout dilakukan per 1 kios."
        )
        if st.button(
            "🗑️ Kosongkan Keranjang & Pindah ke Kios Ini",
            key=f"switch_tenant_{tenant['id']}",
        ):
            _reset_cart()
            st.rerun()

    st.divider()
    menus = db_service.get_menus_by_tenant(tenant["id"])
    if not menus:
        st.info("Kios ini belum memiliki daftar menu.")
        return

    cols = st.columns(2)
    for idx, menu in enumerate(menus):
        with cols[idx % 2]:
            with st.container(border=True):
                in_stock = bool(menu["is_available"])
                stock_label = "Tersedia" if in_stock else "Habis"

                st.markdown(f"#### {menu['name']}")
                st.caption(menu.get("description", ""))
                st.markdown(f"**{format_rupiah(int(menu['price']))}** · {stock_label}")

                current_qty = cart["items"].get(menu["id"], {}).get("qty", 0)
                btn_label = (
                    f"➕ Tambah ke Keranjang ({current_qty} di keranjang)"
                    if current_qty > 0
                    else "➕ Tambah ke Keranjang"
                )
                disabled = (
                    (not tenant["is_open"])
                    or (not in_stock)
                    or cart_locked_other_tenant
                )
                if st.button(
                    btn_label,
                    key=f"add_{tenant['id']}_{menu['id']}",
                    disabled=disabled,
                    use_container_width=True,
                ):
                    _add_to_cart(tenant["id"], menu)
                    st.rerun()


def _render_storefront_tab(tenants: list[dict[str, Any]]) -> None:
    """Merender Tab 1: Etalase Kantin 2 tahap (Grid Kios -> Grid Menu)."""
    if not tenants:
        st.warning("Belum ada kios kantin yang terdaftar.")
        return

    active_tenant_id = st.session_state.get("active_storefront_tenant_id")
    if active_tenant_id is None:
        _render_tenant_grid(tenants)
    else:
        _render_menu_grid(tenants, active_tenant_id)


def _render_checkout_tab(user: dict[str, Any]) -> None:
    """Merender Tab 2: Keranjang, QRIS khusus kios, & upload bukti bayar wajib."""
    cart = st.session_state["cart"]
    items_dict: dict[str, dict[str, Any]] = cart["items"]

    if not items_dict or cart["tenant_id"] is None:
        st.info(
            "Keranjang belanjamu masih kosong. Silakan pilih menu di tab **Etalase Kantin**."
        )
        return

    tenant = db_service.get_tenant_by_id(cart["tenant_id"])
    if tenant is None:
        st.error("Data kios tidak ditemukan. Keranjang akan direset.")
        _reset_cart()
        return

    header_col, action_col = st.columns([3, 1])
    with header_col:
        st.markdown(f"### Pesanan dari: **{tenant['name']}**")
    with action_col:
        if st.button("🗑️ Kosongkan Keranjang", use_container_width=True):
            _reset_cart()
            st.rerun()

    st.info("**Metode Pengambilan:** Ambil langsung di konter kios")
    if not tenant["is_open"]:
        st.warning(
            "**Kios baru saja ditutup oleh penjual.** "
            "Pesanan tidak dapat dikirim sebelum kios buka kembali."
        )

    total_price = 0
    for menu_id, item in list(items_dict.items()):
        qty = int(item["qty"])
        subtotal = int(item["price"]) * qty
        total_price += subtotal

        with st.container(border=True):
            c_info, c_dec, c_qty, c_inc, c_del = st.columns([4, 1, 1, 1, 1])
            with c_info:
                st.markdown(f"**{item['name']}**")
                st.caption(
                    f"{format_rupiah(int(item['price']))} × {qty} = **{format_rupiah(subtotal)}**"
                )
            with c_dec:
                if st.button("➖", key=f"dec_{menu_id}", use_container_width=True):
                    _change_cart_qty(menu_id, -1)
                    st.rerun()
            with c_qty:
                st.markdown(
                    f"<div style='text-align:center; padding-top:6px; font-weight:bold;'>{qty}</div>",
                    unsafe_allow_html=True,
                )
            with c_inc:
                if st.button("➕", key=f"inc_{menu_id}", use_container_width=True):
                    _change_cart_qty(menu_id, 1)
                    st.rerun()
            with c_del:
                if st.button("🗑️", key=f"del_{menu_id}", use_container_width=True):
                    _change_cart_qty(menu_id, -qty)
                    st.rerun()

    notes = st.text_area(
        "Catatan Pesanan (Opsional)",
        placeholder="Contoh: Tidak pedas, sambal pisah, es sedikit...",
        key="checkout_notes",
    )

    st.divider()
    st.markdown(f"### Total Pembayaran: **{format_rupiah(total_price)}**")

    qris_col, upload_col = st.columns([1, 1.3])
    with qris_col:
        st.markdown("#### 1. Scan QRIS Kios")
        st.image(tenant["qris_svg"], width=260)
        st.caption(f"Merchant: **{tenant['name']}** | NMID: `{tenant['nmid']}`")
        st.caption(f"Pastikan nominal transfer tepat **{format_rupiah(total_price)}**.")

    with upload_col:
        st.markdown("#### 2. Upload Bukti Pembayaran (Wajib)")
        uploaded_file = st.file_uploader(
            "Upload Bukti Pembayaran QRIS (PNG/JPG - Wajib)",
            type=["png", "jpg", "jpeg"],
            key="payment_proof_uploader",
        )
        if uploaded_file is not None:
            with st.expander("Preview Bukti Pembayaran", expanded=True):
                st.image(uploaded_file, caption=uploaded_file.name, width=260)
        else:
            st.caption("Tombol pesan aktif setelah bukti pembayaran QRIS diunggah.")

        submit_disabled = (uploaded_file is None) or (not tenant["is_open"])
        if st.button(
            "🚀 Kirim Bukti & Buat Pesanan",
            type="primary",
            disabled=submit_disabled,
            use_container_width=True,
        ):
            proof_bytes, proof_filename = db_service.encode_uploaded_file(uploaded_file)
            order = db_service.create_order(
                buyer_id=user["id"],
                buyer_name=user["name"],
                buyer_npm=user["npm"],
                tenant_id=tenant["id"],
                items=list(items_dict.values()),
                notes=notes,
                payment_proof_bytes=proof_bytes,
                payment_filename=proof_filename,
            )
            _reset_cart()
            st.session_state["last_created_order"] = {
                "queue_number": order["queue_number"],
                "tenant_name": order["tenant_name"],
            }
            st.rerun()


def _render_live_queue_tab(user: dict[str, Any]) -> None:
    """Merender Tab 3: Pelacakan Live Queue & verifikasi pembayaran milik pembeli."""
    top_col, refresh_col = st.columns([4, 1])
    with top_col:
        st.markdown("### Status Antrean Pesananmu")
    with refresh_col:
        if st.button("🔄 Refresh Status", use_container_width=True):
            st.rerun()

    orders = db_service.get_buyer_orders(user["id"])
    if not orders:
        st.info(
            "Belum ada pesanan aktif. Pesananmu akan muncul di sini setelah kamu melakukan checkout dan upload bukti bayar."
        )
        return

    for order in orders:
        with st.container(border=True):
            head_left, head_right = st.columns([1.2, 2.8])
            with head_left:
                st.markdown("Nomor Antrean")
                st.markdown(f"# `#{order['queue_number']}`")
            with head_right:
                st.markdown(f"#### {order['tenant_name']}")
                st.caption(
                    f"{order['created_at']}  |  Total: **{format_rupiah(int(order['total_price']))}**  |  {order['pickup_method']}"
                )
                for item in order["items"]:
                    st.markdown(
                        f"- **{item['name']}** × {item['qty']} "
                        f"({format_rupiah(int(item['price']) * int(item['qty']))})"
                    )
                if order["notes"]:
                    st.caption(f"Catatan: *{order['notes']}*")

            status = order["status"]
            if status == db_service.STATUS_READY:
                st.progress(100)
                st.success(
                    f"**Status (100%): {db_service.STATUS_READY}!** — "
                    f"Silakan ambil pesananmu langsung di konter kios dengan menunjukkan nomor antrean **#{order['queue_number']}**."
                )
            elif status == db_service.STATUS_PREPARING:
                st.progress(50)
                st.info(
                    f"**Status (50%): {db_service.STATUS_PREPARING}** — "
                    "Pembayaran telah dikonfirmasi! Kios sedang menyiapkan makanan/minumanmu."
                )
            elif status == db_service.STATUS_REJECTED:
                st.progress(0)
                reason = order.get("rejection_reason", "").strip()
                reason_text = f" Alasan: *{reason}*" if reason else ""
                st.error(
                    f"**Status: {db_service.STATUS_REJECTED}** — "
                    f"Bukti pembayaran QRIS kamu ditolak oleh penjual.{reason_text}"
                )
            else:
                st.progress(0)
                st.warning(
                    f"**Status (0%): {db_service.STATUS_PENDING_PAYMENT}** — "
                    "Penjual sedang memeriksa bukti pembayaran QRIS yang kamu unggah."
                )

            with st.expander("Lihat Bukti Pembayaran QRIS"):
                st.image(
                    order["payment_proof_bytes"],
                    caption=f"File: {order['payment_filename']}",
                    width=260,
                )


def render_buyer_view(user: dict[str, Any]) -> None:
    """Merender seluruh halaman MVP Role Pembeli dengan 3 tab utama."""
    last_order = st.session_state.pop("last_created_order", None)
    if last_order:
        st.success(
            f"Pesanan **#{last_order['queue_number']}** di **{last_order['tenant_name']}** "
            "berhasil dikirim dan sedang **Menunggu Konfirmasi Pembayaran** oleh penjual. "
            "Pantau progresnya di tab **Live Queue & Tracking**."
        )

    cart_count = sum(
        int(item["qty"]) for item in st.session_state["cart"]["items"].values()
    )
    active_orders_count = len(db_service.get_buyer_orders(user["id"]))

    cart_label = (
        f"Keranjang & Checkout ({cart_count})"
        if cart_count
        else "Keranjang & Checkout"
    )
    queue_label = (
        f"Live Queue & Tracking ({active_orders_count})"
        if active_orders_count
        else "Live Queue & Tracking"
    )

    tab_store, tab_cart, tab_queue = st.tabs(
        ["Etalase Kantin", cart_label, queue_label]
    )

    tenants = db_service.get_tenants()
    with tab_store:
        _render_storefront_tab(tenants)
    with tab_cart:
        _render_checkout_tab(user)
    with tab_queue:
        _render_live_queue_tab(user)
