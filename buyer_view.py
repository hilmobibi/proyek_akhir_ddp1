"""Tampilan UI Role Pembeli (Mahasiswa) untuk GoFood Kancil — Tema Putih-Abu."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

import db_service
import ui_theme

format_rupiah = ui_theme.format_rupiah

NAV_STOREFRONT = "Etalase"
NAV_CART = "Keranjang"
NAV_QUEUE = "Antrean"


def _reset_cart() -> None:
    """Mengosongkan keranjang belanja aktif di session state."""
    st.session_state["cart"] = {"tenant_id": None, "items": {}}


def _add_to_cart(tenant_id: str, menu: dict[str, Any]) -> None:
    """Menambahkan 1 porsi menu ke keranjang (otomatis 1 kios per checkout)."""
    cart = st.session_state["cart"]
    if cart["tenant_id"] != tenant_id:
        cart["tenant_id"] = tenant_id
        cart["items"] = {}

    menu_id = menu["id"]
    if menu_id in cart["items"]:
        cart["items"][menu_id]["qty"] += 1
    else:
        cart["items"][menu_id] = {
            "menu_id": menu_id,
            "name": menu["name"],
            "price": int(menu["price"]),
            "image_url": menu.get("image_url", ""),
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


def _on_buyer_nav_change() -> None:
    """Callback klik bottom navbar Pembeli."""
    chosen = st.session_state.get("buyer_bottom_nav_ctrl")
    if chosen:
        st.session_state["buyer_nav"] = chosen
        st.session_state["buyer_nav_synced"] = chosen


def _render_floating_cart_bar(tenants: list[dict[str, Any]]) -> None:
    """Bar ringkas ala GoFood ketika ada item aktif di dalam keranjang."""
    cart = st.session_state["cart"]
    if not cart["items"] or not cart["tenant_id"]:
        return

    qty_sum = sum(int(i["qty"]) for i in cart["items"].values())
    price_sum = sum(
        int(i["qty"]) * int(i["price"]) for i in cart["items"].values()
    )
    tenant_map = {t["id"]: t for t in tenants}
    t_name = tenant_map.get(cart["tenant_id"], {}).get("name", "Kios")

    with st.container(border=True):
        c_left, c_right = st.columns([3.2, 1.2])
        with c_left:
            st.markdown(
                f"**{qty_sum} item di keranjang** · **{format_rupiah(price_sum)}**  \n"
                f"<span style='font-size:12.5px;color:#71717A;'>Dari {html.escape(t_name)}</span>",
                unsafe_allow_html=True,
            )
        with c_right:
            if st.button(
                "Lanjut ke Keranjang",
                key="buyer_bar_goto_cart",
                type="primary",
                use_container_width=True,
            ):
                st.session_state["buyer_nav"] = NAV_CART
                st.rerun()


def _render_tenant_grid(tenants: list[dict[str, Any]]) -> None:
    """Merender Tahap A: Pencarian & Grid pilihan kios dengan foto kios."""
    search_col, filter_col = st.columns([2.6, 1.4])
    with search_col:
        query = st.text_input(
            "Cari kios atau makanan",
            placeholder="Cari ayam geprek, soto, mie...",
            label_visibility="collapsed",
            key="buyer_search_query",
        )
    with filter_col:
        only_open = st.segmented_control(
            "Filter Buka",
            options=["Semua Kios", "Sedang Buka"],
            default="Semua Kios",
            required=True,
            label_visibility="collapsed",
            width="stretch",
            key="buyer_open_filter",
        )

    st.markdown("#### Pilihan Kios Kantin")

    q_lower = query.strip().lower()
    visible_tenants: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    for t in tenants:
        if only_open == "Sedang Buka" and not t["is_open"]:
            continue
        t_menus = db_service.get_menus_by_tenant(t["id"])
        if q_lower:
            in_tenant = q_lower in t["name"].lower() or q_lower in t.get(
                "category", ""
            ).lower()
            in_menu = any(q_lower in m["name"].lower() for m in t_menus)
            if not (in_tenant or in_menu):
                continue
        visible_tenants.append((t, t_menus))

    if not visible_tenants:
        st.markdown(
            '<div class="gf-surface-note">Tidak ada kios yang cocok dengan pencarianmu.</div>',
            unsafe_allow_html=True,
        )
        return

    num_cols = min(3, len(visible_tenants))
    cols = st.columns(num_cols)
    for idx, (tenant, t_menus) in enumerate(visible_tenants):
        avail = sum(1 for m in t_menus if m["is_available"])
        is_open = bool(tenant["is_open"])

        with cols[idx % num_cols]:
            with st.container(border=True):
                st.markdown(
                    ui_theme.render_media_html(
                        tenant.get("image_url", ""),
                        tenant["name"],
                        dimmed=not is_open,
                        badge_text="BUKA" if is_open else "TUTUP",
                        badge_open=is_open,
                        eta_text=tenant.get("eta") if is_open else None,
                    ),
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<p class="gf-title">{html.escape(tenant["name"])}</p>'
                    f'<p class="gf-desc">{html.escape(tenant.get("description", ""))}</p>'
                    f'<div class="gf-meta-row">'
                    f'<span>{html.escape(tenant.get("category", "Kios Kantin"))}</span>'
                    f"<span>{avail}/{len(t_menus)} tersedia</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                if st.button(
                    "Lihat Menu",
                    key=f"open_tenant_{tenant['id']}",
                    type="primary" if is_open else "secondary",
                    use_container_width=True,
                ):
                    st.session_state["active_storefront_tenant_id"] = tenant["id"]
                    st.rerun()


def _render_menu_grid(tenants: list[dict[str, Any]], active_tenant_id: str) -> None:
    """Merender Tahap B: Header kios & Grid menu makanan dengan foto dan stepper."""
    tenant_map = {t["id"]: t for t in tenants}
    tenant = tenant_map.get(active_tenant_id)
    if tenant is None:
        st.session_state["active_storefront_tenant_id"] = None
        st.rerun()
        return

    if st.button("Kembali ke Semua Kios", key="back_to_tenant_grid"):
        st.session_state["active_storefront_tenant_id"] = None
        st.rerun()

    with st.container(border=True):
        h_img, h_info = st.columns([1.1, 2.9])
        with h_img:
            st.markdown(
                ui_theme.render_media_html(
                    tenant.get("image_url", ""),
                    tenant["name"],
                    dimmed=not tenant["is_open"],
                ),
                unsafe_allow_html=True,
            )
        with h_info:
            badge_cls = "gf-badge-open" if tenant["is_open"] else "gf-badge-closed"
            badge_lbl = "BUKA" if tenant["is_open"] else "TUTUP SEMENTARA"
            st.markdown(
                f'<span class="gf-badge {badge_cls}">{badge_lbl}</span>'
                f'<h3 style="margin:8px 0 4px 0;font-weight:700;letter-spacing:-0.02em;">'
                f'{html.escape(tenant["name"])}</h3>'
                f'<p style="color:#71717A;font-size:13.5px;margin:0 0 8px 0;">'
                f'{html.escape(tenant.get("description", ""))}</p>'
                f'<p style="color:#52525B;font-size:12.5px;margin:0;">'
                f'{html.escape(tenant.get("category", "Kios Kantin"))} &nbsp;·&nbsp; '
                f'Estimasi siap {html.escape(tenant.get("eta", "5-10 mnt"))} &nbsp;·&nbsp; '
                "Ambil di konter kios</p>",
                unsafe_allow_html=True,
            )

    cart = st.session_state["cart"]
    locked_other = (
        cart["tenant_id"] is not None
        and cart["tenant_id"] != tenant["id"]
        and bool(cart["items"])
    )
    if locked_other:
        other_name = tenant_map.get(cart["tenant_id"], {}).get("name", "kios lain")
        st.markdown(
            f'<div class="gf-surface-note">'
            f"Keranjangmu sedang berisi menu dari <b>{html.escape(other_name)}</b>. "
            "Menambahkan menu di bawah akan mengganti isi keranjang ke kios ini karena tiap kios memiliki QRIS berbeda."
            "</div>",
            unsafe_allow_html=True,
        )

    st.markdown("#### Daftar Menu")
    menus = db_service.get_menus_by_tenant(tenant["id"])
    if not menus:
        st.markdown(
            '<div class="gf-surface-note">Kios ini belum memiliki daftar menu.</div>',
            unsafe_allow_html=True,
        )
        return

    cols = st.columns(min(3, len(menus)))
    for idx, menu in enumerate(menus):
        in_stock = bool(menu["is_available"])
        can_order = bool(tenant["is_open"]) and in_stock
        qty_in_cart = (
            cart["items"].get(menu["id"], {}).get("qty", 0)
            if cart["tenant_id"] == tenant["id"]
            else 0
        )

        with cols[idx % len(cols)]:
            with st.container(border=True):
                st.markdown(
                    ui_theme.render_media_html(
                        menu.get("image_url", ""),
                        menu["name"],
                        dimmed=not in_stock,
                        badge_text=None if in_stock else "HABIS",
                        badge_open=False,
                    ),
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<p class="gf-title">{html.escape(menu["name"])}</p>'
                    f'<p class="gf-desc">{html.escape(menu.get("description", ""))}</p>'
                    f'<div class="gf-meta-row">'
                    f'<span class="gf-price">{format_rupiah(int(menu["price"]))}</span>'
                    f'<span>{"Tersedia" if in_stock else "Stok habis"}</span>'
                    f"</div>",
                    unsafe_allow_html=True,
                )

                if qty_in_cart > 0 and can_order:
                    s_dec, s_num, s_inc = st.columns([1, 1.2, 1])
                    with s_dec:
                        if st.button(
                            "-",
                            key=f"mdec_{tenant['id']}_{menu['id']}",
                            use_container_width=True,
                        ):
                            _change_cart_qty(menu["id"], -1)
                            st.rerun()
                    with s_num:
                        st.markdown(
                            f"<div style='text-align:center;padding-top:7px;font-weight:600;'>{qty_in_cart}</div>",
                            unsafe_allow_html=True,
                        )
                    with s_inc:
                        if st.button(
                            "+",
                            key=f"minc_{tenant['id']}_{menu['id']}",
                            type="primary",
                            use_container_width=True,
                        ):
                            _change_cart_qty(menu["id"], 1)
                            st.rerun()
                else:
                    btn_text = "Tambah" if in_stock else "Habis"
                    if st.button(
                        btn_text,
                        key=f"add_{tenant['id']}_{menu['id']}",
                        type="primary" if can_order else "secondary",
                        disabled=not can_order,
                        use_container_width=True,
                    ):
                        _add_to_cart(tenant["id"], menu)
                        st.rerun()


def _render_storefront_screen(tenants: list[dict[str, Any]]) -> None:
    """Merender layar Etalase (Grid Kios -> Grid Menu)."""
    if not tenants:
        st.markdown(
            '<div class="gf-surface-note">Belum ada kios kantin yang terdaftar.</div>',
            unsafe_allow_html=True,
        )
        return

    _render_floating_cart_bar(tenants)
    active_tenant_id = st.session_state.get("active_storefront_tenant_id")
    if active_tenant_id is None:
        _render_tenant_grid(tenants)
    else:
        _render_menu_grid(tenants, active_tenant_id)


def _render_checkout_screen(user: dict[str, Any]) -> None:
    """Merender layar Keranjang, QRIS khusus kios, & upload bukti bayar wajib."""
    cart = st.session_state["cart"]
    items_dict: dict[str, dict[str, Any]] = cart["items"]

    if not items_dict or cart["tenant_id"] is None:
        with st.container(border=True):
            st.markdown("#### Keranjang Belanja Kosong")
            st.caption("Belum ada makanan yang dipilih dari etalase kantin.")
            if st.button("Jelajahi Etalase Kantin", type="primary"):
                st.session_state["buyer_nav"] = NAV_STOREFRONT
                st.rerun()
        return

    tenant = db_service.get_tenant_by_id(cart["tenant_id"])
    if tenant is None:
        st.error("Data kios tidak ditemukan. Keranjang akan direset.")
        _reset_cart()
        return

    left_col, right_col = st.columns([1.45, 1.05])
    total_price = 0

    with left_col:
        with st.container(border=True):
            h1, h2 = st.columns([2.8, 1.2])
            with h1:
                st.markdown(f"#### {tenant['name']}")
                st.caption("Pengambilan langsung di konter kios")
            with h2:
                if st.button("Kosongkan", use_container_width=True):
                    _reset_cart()
                    st.rerun()

            if not tenant["is_open"]:
                st.markdown(
                    '<div class="gf-surface-note">'
                    "<b>Kios baru saja ditutup oleh penjual.</b> "
                    "Pesanan tidak dapat dikirim sebelum kios buka kembali."
                    "</div>",
                    unsafe_allow_html=True,
                )

            st.divider()
            for menu_id, item in list(items_dict.items()):
                qty = int(item["qty"])
                subtotal = int(item["price"]) * qty
                total_price += subtotal

                r_info, r_ctrl = st.columns([2.4, 1.5])
                with r_info:
                    st.markdown(f"**{item['name']}**")
                    st.caption(
                        f"{format_rupiah(int(item['price']))}  ·  Subtotal {format_rupiah(subtotal)}"
                    )
                with r_ctrl:
                    b1, b2, b3 = st.columns([1, 1, 1])
                    with b1:
                        if st.button("-", key=f"dec_{menu_id}", use_container_width=True):
                            _change_cart_qty(menu_id, -1)
                            st.rerun()
                    with b2:
                        st.markdown(
                            f"<div style='text-align:center;padding-top:7px;font-weight:600;'>{qty}</div>",
                            unsafe_allow_html=True,
                        )
                    with b3:
                        if st.button("+", key=f"inc_{menu_id}", use_container_width=True):
                            _change_cart_qty(menu_id, 1)
                            st.rerun()

            st.divider()
            notes = st.text_input(
                "Catatan untuk penjual (opsional)",
                placeholder="Contoh: Sambal dipisah, tidak pedas, es sedikit...",
                key="checkout_notes",
            )

    with right_col:
        with st.container(border=True):
            st.markdown("#### Pembayaran QRIS")
            st.markdown(
                '<div class="gf-meta-row" style="margin-top:4px;">'
                "<span>Total Tagihan</span>"
                f'<span style="font-size:18px;font-weight:700;color:#18181B;">{format_rupiah(total_price)}</span>'
                "</div>",
                unsafe_allow_html=True,
            )
            st.image(tenant["qris_svg"], width=240)
            st.caption(f"NMID: `{tenant['nmid']}`")

            uploaded_file = st.file_uploader(
                "Unggah bukti pembayaran QRIS (PNG / JPG)",
                type=["png", "jpg", "jpeg"],
                key="payment_proof_uploader",
            )
            if uploaded_file is not None:
                with st.expander("Preview Bukti Pembayaran", expanded=False):
                    st.image(uploaded_file, caption=uploaded_file.name, width=240)
            else:
                st.caption(
                    "Unggah tangkapan layar pembayaran QRIS untuk mengaktifkan tombol pesan."
                )

            submit_disabled = (uploaded_file is None) or (not tenant["is_open"])
            if st.button(
                "Kirim Bukti & Buat Pesanan",
                type="primary",
                disabled=submit_disabled,
                use_container_width=True,
            ):
                proof_bytes, proof_filename = db_service.encode_uploaded_file(
                    uploaded_file
                )
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
                st.session_state["buyer_nav"] = NAV_QUEUE
                st.rerun()


def _render_live_queue_screen(user: dict[str, Any]) -> None:
    """Merender layar Antrean dengan teks status deskriptif besar tanpa persentase."""
    top_col, refresh_col = st.columns([3.5, 1])
    with top_col:
        st.markdown("#### Antrean Aktif & Riwayat")
    with refresh_col:
        if st.button("Perbarui Status", use_container_width=True):
            db_service.clear_cache()
            st.rerun()

    orders = db_service.get_buyer_orders(user["id"])
    if not orders:
        st.markdown(
            '<div class="gf-surface-note">'
            "Belum ada pesanan aktif. Pesananmu akan muncul di sini setelah kamu checkout dan mengunggah bukti pembayaran."
            "</div>",
            unsafe_allow_html=True,
        )
        return

    for order in orders:
        with st.container(border=True):
            c_num, c_detail = st.columns([1.05, 2.95])
            with c_num:
                st.caption("Nomor Antrean")
                st.markdown(
                    "<div style='font-size:32px;font-weight:700;letter-spacing:-0.03em;color:#18181B;'>"
                    f"#{html.escape(order['queue_number'])}</div>",
                    unsafe_allow_html=True,
                )
                st.caption(order["created_at"])
            with c_detail:
                st.markdown(f"#### {order['tenant_name']}")
                items_summary = ", ".join(
                    f"{item['qty']}x {item['name']}" for item in order["items"]
                )
                st.markdown(
                    f"{items_summary}  ·  **{format_rupiah(int(order['total_price']))}**"
                )
                if order["notes"]:
                    st.caption(f"Catatan: {order['notes']}")

            st.markdown(
                ui_theme.render_status_text_html(
                    order["status"], order.get("rejection_reason", "")
                ),
                unsafe_allow_html=True,
            )

            with st.expander("Lihat Bukti Pembayaran QRIS"):
                st.image(
                    order["payment_proof_bytes"],
                    caption=f"File: {order['payment_filename']}",
                    width=240,
                )


def render_buyer_view(user: dict[str, Any]) -> None:
    """Merender seluruh halaman Role Pembeli dengan floating bottom navbar 1 baris."""
    if "buyer_nav" not in st.session_state:
        st.session_state["buyer_nav"] = NAV_STOREFRONT

    last_order = st.session_state.pop("last_created_order", None)
    if last_order:
        st.markdown(
            f'<div class="gf-surface-note">'
            f"Pesanan <b>#{html.escape(last_order['queue_number'])}</b> di "
            f"<b>{html.escape(last_order['tenant_name'])}</b> berhasil dikirim. "
            "Pembayaranmu sedang dikonfirmasi oleh penjual."
            "</div>",
            unsafe_allow_html=True,
        )

    cart_count = sum(
        int(item["qty"]) for item in st.session_state["cart"]["items"].values()
    )
    active_orders_count = len(db_service.get_buyer_orders(user["id"]))

    if st.session_state.get("buyer_nav_synced") != st.session_state["buyer_nav"]:
        st.session_state["buyer_bottom_nav_ctrl"] = st.session_state["buyer_nav"]
        st.session_state["buyer_nav_synced"] = st.session_state["buyer_nav"]

    nav_labels = {
        NAV_STOREFRONT: "Etalase",
        NAV_CART: f"Keranjang ({cart_count})" if cart_count else "Keranjang",
        NAV_QUEUE: f"Antrean ({active_orders_count})" if active_orders_count else "Antrean",
    }

    with st.container(key="bottom_nav"):
        st.segmented_control(
            "Navigasi Pembeli",
            options=[NAV_STOREFRONT, NAV_CART, NAV_QUEUE],
            format_func=lambda k: nav_labels[k],
            required=True,
            wrap=False,
            label_visibility="collapsed",
            width="stretch",
            key="buyer_bottom_nav_ctrl",
            on_change=_on_buyer_nav_change,
        )

    active = st.session_state["buyer_nav"]
    tenants = db_service.get_tenants()
    if active == NAV_STOREFRONT:
        _render_storefront_screen(tenants)
    elif active == NAV_CART:
        _render_checkout_screen(user)
    else:
        _render_live_queue_screen(user)
