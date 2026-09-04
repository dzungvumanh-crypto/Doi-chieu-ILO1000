"""Trang nghỉ phép → đăng ký, duyệt và lịch nghỉ."""

import asyncio

import datetime as _dt_mod

from nicegui import ui, app

import frontend.api_client as api

import frontend.ui_kit as ui_kit

from frontend.shared import _sidebar, _content_area, _page_header, _require_auth, _handle_api_error



# ─── LEAVES PAGE ─────────────────────────────────────────────────────────────

# Nhãn + màu chuyển về ui_kit.STATUS. Giữ tên _LEAVE_STATUS cho code cũ trong file.

_LEAVE_STATUS = {

    k: (ui_kit.status_label(k), ui_kit.STATUS[k]["chip"])

    for k in ("pending_ksv", "pending_tong_hop", "pending_gd", "approved", "rejected", "cancelled")

}

# Định nghĩa thật nằm ở ui_kit.LEAVE_TYPE — sidebar cũng đọc map này.
_LEAVE_TYPE = ui_kit.LEAVE_TYPE

# Nhóm hiển thị 3 trạng thái đơn giản trong cột Trạng thái của bảng

_STATUS_GROUP = {

    "pending_ksv":      ("Chờ KSV duyệt",    "bg-orange-100 text-orange-700"),

    "pending_tong_hop": ("Chờ Tổng hợp",      "bg-yellow-100 text-yellow-700"),

    "pending_gd":       ("Chờ Ban lãnh đạo duyệt", "bg-blue-100 text-blue-700"),

    "approved":         ("Hoàn thành",         "bg-green-100 text-green-700"),

    "rejected":         ("Từ chối",            "bg-red-100 text-red-700"),

    "cancelled":        ("Đã hủy",             "bg-gray-100 text-gray-500"),

}





# ─── Popup xem trước đơn + đặt chữ ký ────────────────────────────────────────
# Ảnh trang là bản in THẬT (Word đã dựng PDF, backend render ra PNG), nên chỗ thả
# chữ ký trong popup chính là chỗ nó nằm trên file PDF tải về — không phải bản mô
# phỏng bằng HTML.
_SIGN_PAGE_W_PX = 640          # bề ngang ảnh trang trong popup


def _sign_js(cid: str, ppm: float, ratio: float) -> str:
    """Kéo để di chuyển, kéo 4 góc để phóng to/thu nhỏ (khoá tỉ lệ ảnh).

    Nội dung q-dialog chỉ được gắn vào DOM khi popup mở, mà thứ tự tới nơi của
    lệnh mở và lệnh chạy JS không đảm bảo → dò lại vài nhịp cho tới khi thấy.
    """
    return f"""
(function attach(n) {{
  const wrap = document.getElementById('wrap_{cid}');
  const box  = document.getElementById('sig_{cid}');
  if (!wrap || !box) {{ if (n < 60) setTimeout(() => attach(n + 1), 50); return; }}
  const ppm = {ppm}, ratio = {ratio};
  let mode = null, corner = null, sx = 0, sy = 0, ox = 0, oy = 0, ow = 0, oh = 0;
  const lim = () => [wrap.clientWidth, wrap.clientHeight];
  function down(e, m, c) {{
    mode = m; corner = c; sx = e.clientX; sy = e.clientY;
    ox = box.offsetLeft; oy = box.offsetTop; ow = box.offsetWidth; oh = box.offsetHeight;
    e.preventDefault(); e.stopPropagation();
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
  }}
  function move(e) {{
    const [W, H] = lim(), dx = e.clientX - sx, dy = e.clientY - sy;
    if (mode === 'move') {{
      box.style.left = Math.max(0, Math.min(W - ow, ox + dx)) + 'px';
      box.style.top  = Math.max(0, Math.min(H - oh, oy + dy)) + 'px';
    }} else {{
      let nw = ow + (corner.indexOf('e') >= 0 ? dx : -dx);
      nw = Math.max(18, Math.min(W, nw));
      let nh = nw * ratio;
      if (nh > H) {{ nh = H; nw = nh / ratio; }}
      let nx = corner.indexOf('e') >= 0 ? ox : ox + ow - nw;
      let ny = corner.indexOf('s') >= 0 ? oy : oy + oh - nh;
      box.style.width  = nw + 'px'; box.style.height = nh + 'px';
      box.style.left = Math.max(0, Math.min(W - nw, nx)) + 'px';
      box.style.top  = Math.max(0, Math.min(H - nh, ny)) + 'px';
    }}
  }}
  function up() {{
    mode = null;
    window.removeEventListener('pointermove', move);
    window.removeEventListener('pointerup', up);
  }}
  // Ô ký nằm quá nửa trang A4 — cuộn sẵn tới đó, đừng bắt người dùng tự tìm.
  const sc = wrap.parentElement;
  if (sc) sc.scrollTop = Math.max(0, box.offsetTop - 120);
  box.addEventListener('pointerdown', e => down(e, 'move', null));
  box.querySelectorAll('[data-c]').forEach(h =>
      h.addEventListener('pointerdown', e => down(e, 'size', h.dataset.c)));
  window.__sigbox_{cid} = () => ({{
      x_mm: box.offsetLeft / ppm, y_mm: box.offsetTop / ppm,
      w_mm: box.offsetWidth / ppm, h_mm: box.offsetHeight / ppm }});
}})(0);
"""


def _sign_html(cid: str, pv: dict, ppm: float) -> str:
    def _px(v):
        return round(float(v) * ppm, 1)

    w_px = _px(pv["page_w_mm"])
    h_px = _px(pv["page_h_mm"])
    parts = [
        f'<div id="wrap_{cid}" style="position:relative;width:{w_px}px;height:{h_px}px;'
        f'background:#fff;box-shadow:0 1px 6px rgba(0,0,0,.25);user-select:none;">',
        f'<img src="{pv["page_png"]}" draggable="false" '
        f'style="width:100%;height:100%;display:block;pointer-events:none;">',
    ]
    # Chữ ký của người khác đã ký trước — chỉ để nhìn, không kéo được
    for p in pv.get("placed") or []:
        parts.append(
            f'<img src="{p["data_url"]}" draggable="false" title="{p["label"]}" '
            f'style="position:absolute;left:{_px(p["x_mm"])}px;top:{_px(p["y_mm"])}px;'
            f'width:{_px(p["w_mm"])}px;height:{_px(p["h_mm"])}px;pointer-events:none;">'
        )
    sig, box = pv.get("signature"), pv.get("suggest")
    if sig and box:
        hd = ("position:absolute;width:11px;height:11px;background:#fff;border:2px solid #dc2626;"
              "border-radius:2px;")
        parts.append(
            f'<div id="sig_{cid}" style="position:absolute;left:{_px(box["x_mm"])}px;'
            f'top:{_px(box["y_mm"])}px;width:{_px(box["w_mm"])}px;height:{_px(box["h_mm"])}px;'
            f'outline:1px dashed #dc2626;cursor:move;touch-action:none;">'
            f'<img src="{sig["data_url"]}" draggable="false" '
            f'style="width:100%;height:100%;pointer-events:none;">'
            f'<div data-c="nw" style="{hd}left:-6px;top:-6px;cursor:nwse-resize;"></div>'
            f'<div data-c="ne" style="{hd}right:-6px;top:-6px;cursor:nesw-resize;"></div>'
            f'<div data-c="sw" style="{hd}left:-6px;bottom:-6px;cursor:nesw-resize;"></div>'
            f'<div data-c="se" style="{hd}right:-6px;bottom:-6px;cursor:nwse-resize;"></div>'
            f'</div>'
        )
    parts.append("</div>")
    return "".join(parts)


async def _fetch_preview(call):
    """Gọi API xem trước kèm chỉ báo chờ — lần dựng đầu Word mất khoảng 5–7 giây.

    Trả về: payload nếu xong; None nếu phiên hết hạn (đã chuyển về đăng nhập);
    False nếu lỗi khác (gọi xong tự quyết định làm gì tiếp).
    """
    note = ui.notification("Đang dựng bản xem trước…", spinner=True, timeout=None)
    try:
        return await asyncio.to_thread(call)
    except Exception as e:
        if _handle_api_error(e):
            return None
        ui.notify(f"Không xem trước được đơn: {e}", type="warning", timeout=6000)
        return False
    finally:
        note.dismiss()


async def _open_sign_dialog(pv: dict, title: str, ok_label: str, ok_cls: str = "bg-green-600"):
    """Mở popup. Trả về None nếu huỷ, {} nếu xác nhận mà không ký,
    hoặc dict toạ độ {page,x_mm,y_mm,w_mm,h_mm} nếu có đặt chữ ký."""
    import uuid

    cid = uuid.uuid4().hex[:8]
    ppm = _SIGN_PAGE_W_PX / float(pv["page_w_mm"] or 210)
    box = pv.get("suggest") or {}
    has_sig = bool(pv.get("signature")) and bool(box)
    ratio = (float(box.get("h_mm") or 1) / float(box.get("w_mm") or 1)) if has_sig else 1.0

    # max-width inline + !important: Quasar đặt sẵn `.q-dialog__inner--minimized > div
    # { max-width: 560px }` với độ ưu tiên cao hơn class của Tailwind → không ghi đè
    # kiểu này thì ảnh trang A4 rộng 640px bị bóp lại.
    with ui.dialog() as dlg, ui.card().classes("p-4").style("width:auto;max-width:none !important"):
        with ui.row().classes("w-full items-center justify-between mb-1"):
            ui.label(title).classes("text-base font-bold text-gray-800")
            ui.button(icon="close", on_click=lambda: dlg.submit(None)).props("flat dense round")
        if has_sig:
            ui.label("Kéo chữ ký để đổi chỗ · kéo 4 góc để phóng to / thu nhỏ").classes(
                "text-xs text-gray-500 mb-2")
        else:
            ui.label("Chưa có ảnh chữ ký — vào Quản lý người dùng để tải lên. "
                     "Vẫn tiếp tục được nhưng phiếu sẽ không có chữ ký.").classes(
                "text-xs text-orange-600 mb-2")
        with ui.element("div").classes("overflow-auto").style("max-height:66vh"):
            ui.html(_sign_html(cid, pv, ppm))

        async def _ok():
            if not has_sig:
                dlg.submit({})
                return
            try:
                res = await ui.run_javascript(
                    f"window.__sigbox_{cid} ? window.__sigbox_{cid}() : null", timeout=5.0)
            except Exception:
                res = None
            if not res:
                ui.notify("Chưa đọc được vị trí chữ ký — thử lại sau giây lát", type="warning")
                return
            res["page"] = box.get("page", 0)
            dlg.submit(res)

        with ui.row().classes("w-full justify-end gap-2 mt-3"):
            ui.button("Hủy", on_click=lambda: dlg.submit(None)).classes("text-gray-500")
            ui.button(ok_label, icon="draw", on_click=_ok).classes(f"{ok_cls} text-white")

    ui.run_javascript(_sign_js(cid, ppm, ratio))
    try:
        return await dlg
    finally:
        dlg.delete()


def _leave_status_badge(status: str, label_override: str | None = None):

    label, cls = _LEAVE_STATUS.get(status, (status, "bg-gray-100 text-gray-500"))
    # Đơn NPBB gốc đã bị đơn điều chỉnh thay thế — nhãn riêng thay nhãn chung
    # chung, xem status_label ở backend (_leave_to_out).
    if label_override:
        label = label_override

    ui.label(label).classes(f"text-xs font-medium px-2 py-0.5 rounded border {cls}")





def _fmt_leave_dates(start_str: str, end_str: str, spread_dates=None) -> str:

    """1 ngày → DD/MM/YYYY; liên tiếp → DD/MM → DD/MM/YYYY; lẻ → DD/MM, DD/MM, DD/MM/YYYY"""

    if not start_str or not end_str:

        return "→"

    try:

        from datetime import date as _date

        s = _date.fromisoformat(start_str[:10])

        e = _date.fromisoformat(end_str[:10])

        if s == e:

            return s.strftime("%d/%m/%Y")

        if spread_dates and len(spread_dates) >= 2:

            parsed = sorted(_date.fromisoformat(d[:10]) for d in spread_dates)

            if len(parsed) <= 4:

                parts = [d.strftime("%d/%m") for d in parsed[:-1]]

                parts.append(parsed[-1].strftime("%d/%m/%Y"))

                return ", ".join(parts)

            else:

                first2 = ", ".join(d.strftime("%d/%m") for d in parsed[:2])

                return f"{first2} +{len(parsed) - 2} ngày"

        return f"{s.strftime('%d/%m')} → {e.strftime('%d/%m/%Y')}"

    except Exception:

        return start_str[:10]


def _fmt_ngay_vn(iso_str: str) -> str:

    """YYYY-MM-DD (hoặc có phần giờ) → DD/MM/YYYY, giữ nguyên chuỗi gốc nếu không parse được."""

    if not iso_str:

        return ""

    try:

        from datetime import date as _date

        return _date.fromisoformat(iso_str[:10]).strftime("%d/%m/%Y")

    except Exception:

        return iso_str




def _gd_display(leave: dict) -> str:

    """Thêm (TUQ) nếu PGĐ ký thay GĐ."""

    name = leave.get("gd_approver_name") or ""

    if name and leave.get("gd_is_pgd"):

        return f"{name} (TUQ)"

    return name





@ui.page("/leaves")

async def leaves_page():

    if not _require_auth():

        return

    if not api.has_feature("menu.leaves"):

        ui.navigate.to("/home")

        return

    await _sidebar("leaves")



    current_user = api.get_current_user()

    user_role    = current_user.get("role", "") if current_user else ""

    user_id      = current_user.get("id") if current_user else None  # key lưu là "id", không phải "staff_id"

    # ── Kiểm tra broadcast notification ủy quyền ─────────────────────────────
    _last_seen_key = f"_deleg_seen_{user_id}"
    _last_seen     = app.storage.user.get(_last_seen_key, "")
    _broadcast     = app.storage.general.get("_deleg_broadcast", {})
    _deleg_end     = _broadcast.get("end_date", "")
    _deleg_active  = not _deleg_end or _deleg_end >= __import__("datetime").date.today().isoformat()
    if _broadcast and _broadcast.get("ts", "") > _last_seen and _deleg_active:
        app.storage.user[_last_seen_key] = _broadcast["ts"]
        async def _show_deleg_popup(msg=_broadcast["msg"]):
            with ui.dialog(value=True) as _dp, ui.card().classes("p-6 max-w-lg"):
                ui.label("📋 Thông báo ủy quyền").classes("text-lg font-bold text-red-900 mb-3")
                ui.label(msg).classes("text-sm text-gray-700 leading-relaxed")
                ui.button("Đã hiểu", on_click=_dp.close).classes("bg-red-700 text-white mt-4 w-full")
        ui.timer(0.5, _show_deleg_popup, once=True)

    # ── Bật sẵn Word ở máy chủ ────────────────────────────────────────────────
    # Bản xem trước do Word dựng. Mở Word tốn ~1,5 giây, chuyển một đơn chỉ tốn
    # ~0,35 giây — nên đánh thức nó ngay lúc mở trang, trong khi người dùng còn
    # đang xem danh sách / điền đơn. Gọi xong quên luôn: hỏng cũng không ảnh hưởng
    # gì, đường xem trước thật vẫn tự bật Word khi cần.
    async def _warm_up_word():
        try:
            await asyncio.to_thread(api.post, "/api/leaves/preview/warmup", {})
        except Exception:
            pass        # dọn đường thôi, im lặng bỏ qua — không làm phiền người dùng
    ui.timer(0.2, _warm_up_word, once=True)

    # ── Popup thông báo carry-over hết hiệu lực sau Q1 (1 lần/năm/user) ──────
    async def _check_carryover_notice():
        try:
            res = await asyncio.to_thread(api.get, "/api/leaves/carryover-notice")
        except Exception:
            return
        if not isinstance(res, dict) or not res.get("show"):
            return
        with ui.dialog(value=True) as _cn_dp, ui.card().classes("p-6 max-w-lg"):
            ui.label("📌 Thông báo ngày phép chuyển kỳ").classes("text-lg font-bold text-red-900 mb-3")
            ui.label(
                "Ngày phép chuyển kỳ (carry-over) từ năm trước đã hết hiệu lực sau ngày 31/03. "
                "Các ngày chưa sử dụng đã bị thu hồi và không còn được cộng vào hạn mức phép năm nay."
            ).classes("text-sm text-gray-700 leading-relaxed")
            async def _ack():
                try:
                    await asyncio.to_thread(api.post, "/api/leaves/carryover-notice/ack", {})
                except Exception:
                    pass
                _cn_dp.close()
            ui.button("Đã hiểu", on_click=_ack).classes("bg-red-700 text-white mt-4 w-full")
    ui.timer(0.8, _check_carryover_notice, once=True)



    can_all        = (user_role in ("admin", "giam_doc", "pho_giam_doc")

                      or api.has_feature("leaves.forward_th"))  # Phòng TH xem toàn bộ

    # Bước Tổng hợp phân quyền theo FEATURE, không theo role: chuyên viên phòng TH
    # được cấp "leaves.forward_th" vẫn phải thao tác được. Backend (tong_hop_review)
    # chỉ kiểm tra _is_tong_hop_staff — các gate role cứng ở frontend chặn nhầm
    # khiến đơn hiện ra nhưng không có nút nào.
    can_forward_th = api.has_feature("leaves.forward_th")

    # Tab "Ủy quyền GĐ" giao được qua "Phân quyền theo nhóm" (admin luôn có).
    # Tab "Ngày lễ" vẫn admin-only — trước đây hai tab dùng CHUNG một biến, nới
    # quyền ủy quyền mà không tách thì mở nhầm luôn màn sửa ngày lễ toàn hệ thống.
    can_delegation = api.has_feature("leaves.delegation_admin")
    can_holiday    = user_role == "admin"

    show_approver  = user_role not in ("giam_doc", "pho_giam_doc", "admin", "truong_phong")



    # ── Drawer và dialog phải lý con trực tiếp của page ──────────────────────

    with ui.right_drawer(value=False).props("width=440 overlay behavior=mobile").classes(

        "bg-white shadow-2xl overflow-y-auto"

    ) as detail_drawer:

        drawer_container = ui.column().classes("w-full gap-0")



    with ui.dialog() as history_dialog, ui.card().classes("p-0 w-[560px] max-h-[80vh] overflow-y-auto"):

        history_container = ui.column().classes("w-full gap-0")



    # ── Dialog xác nhận chung ─────────────────────────────────────────────────

    _confirm_cb: list = [None]



    # _do_confirm_ref giúp button reference _do_confirm TRƯỚC khi nó được define

    _do_confirm_ref: list = [None]



    async def _cfm_on_click():

        """Wrapper async → NiceGUI gĐi trực tiếp nên có đồng client context."""

        if _do_confirm_ref[0]:

            await _do_confirm_ref[0]()



    with ui.dialog() as confirm_dialog, ui.card().classes("p-6 w-96"):

        _cfm_title = ui.label("").classes("text-lg font-bold text-red-900 mb-1")

        _cfm_msg   = ui.label("").classes("text-sm text-gray-600 mb-5")

        with ui.row().classes("gap-3 justify-end w-full"):

            ui.button("Hủy", on_click=confirm_dialog.close).props("flat").classes("text-gray-500")

            _cfm_ok = ui.button("Xác nhận", on_click=_cfm_on_click).classes("text-white")



    async def _do_confirm():

        confirm_dialog.close()

        if _confirm_cb[0]:

            await _confirm_cb[0]()



    _do_confirm_ref[0] = _do_confirm



    def _ask_confirm(title: str, msg: str, callback, ok_label: str = "Xác nhận", ok_cls: str = "bg-green-600"):

        _cfm_title.set_text(title)

        _cfm_msg.set_text(msg)

        _cfm_ok.set_text(ok_label)

        _cfm_ok.classes(replace=f"text-white {ok_cls}")

        _confirm_cb[0] = callback

        confirm_dialog.open()



    # ── Duyệt kèm ký ──────────────────────────────────────────────────────────

    async def _sign_then_approve(lid: int, slot: str, path: str, title: str, send):
        """Mở popup xem trước để người duyệt đặt chữ ký rồi mới gọi `send(payload)`.

        Không dựng được bản in thì vẫn cho duyệt (hỏi lại) — quy trình nghỉ phép
        không được đứng lại chỉ vì máy chủ chưa chuyển đổi được PDF.
        """
        pv = await _fetch_preview(lambda: api.get(path, {"slot": slot}, 120))
        if pv is None:
            return
        if pv is False:
            _ask_confirm(title,
                         "Không dựng được bản xem trước. Vẫn phê duyệt (phiếu sẽ không có chữ ký của bạn)?",
                         lambda: send({"action": "approve"}), "Phê duyệt", "bg-green-600")
            return
        box = await _open_sign_dialog(pv, title, "Ký và phê duyệt")
        if box is None:
            return
        payload = {"action": "approve"}
        if box:
            payload["signature"] = box
        await send(payload)



    # ── Cảnh báo đơn có ứng phép năm sau trước khi duyệt ────────────────────

    def _borrow_year_label(lv: dict) -> str:
        try:
            return f"năm {int((lv.get('start_date') or '')[:4]) + 1}"
        except Exception:
            return "năm sau"

    async def _borrow_confirm_or_run(lv: dict, run):
        """`borrow_next_year_days` > 0 nghĩa là đơn đã ăn vào hạn mức phép năm
        sau lúc tạo (xem _check_quota_or_borrow ở backend) — người duyệt phải
        được cảnh báo trước khi hoàn tất duyệt, không âm thầm duyệt qua.
        `run` là hàm async không tham số, thực hiện việc duyệt thật."""
        borrow = lv.get("borrow_next_year_days") or 0
        if not borrow:
            await run()
            return
        _ask_confirm(
            "Đơn có ứng phép năm sau",
            f"Đơn nghỉ phép của {lv.get('staff_name', '')} ({lv.get('department_name', '')}) "
            f"có sử dụng {borrow:.0f} ngày phép của {_borrow_year_label(lv)}. Tiếp tục duyệt?",
            run, "Tiếp tục duyệt", "bg-orange-600",
        )



    # ── Dialog từ chối (yêu cầu lý do) ──────────────────────────────────────

    _reject_cb: list = [None]

    with ui.dialog() as reject_dialog, ui.card().classes("p-6 w-80"):

        ui.label("Nhập lý do từ chối").classes("text-lg font-bold text-red-900 mb-4")

        reject_reason = ui.textarea("Lý do từ chối").classes("w-full").props("rows=3")



        async def _confirm_reject():

            if not reject_reason.value.strip():

                ui.notify("Vui lòng nhập lý do từ chối", type="warning")

                return

            cb = _reject_cb[0]

            reason = reject_reason.value.strip()

            reject_reason.value = ""

            reject_dialog.close()

            if cb:

                await cb(reason)



        def _reject_cancel():
            # Xoá lý do đang gõ dở — nếu không, mở dialog từ chối cho đơn KHÁC sau
            # đó vẫn còn giữ lý do của đơn trước, dễ gửi nhầm.
            reject_reason.value = ""
            reject_dialog.close()

        with ui.row().classes("w-full justify-end gap-2 mt-4"):

            ui.button("Hủy", on_click=_reject_cancel).classes("text-gray-500")

            ui.button("Xác nhận từ chối", on_click=_confirm_reject).classes("bg-red-700 text-white")



    with _content_area():

        # ── Banner thông báo ủy quyền đang hiệu lực ──────────────────────────
        try:
            _active_deleg = await asyncio.to_thread(api.get, "/api/delegations/active") or []
        except Exception:
            _active_deleg = []

        if _active_deleg:
            _deleg_texts = []
            for d in _active_deleg:
                _deleg_texts.append(
                    f"📋 {d.get('giam_doc_role_label','')} {d.get('giam_doc_name','GĐ')} ủy quyền cho "
                    f"{d.get('pho_giam_doc_role_label','')} {d.get('pho_giam_doc_name','PGĐ')} "
                    f"từ {_fmt_ngay_vn(d.get('start_date',''))} đến {_fmt_ngay_vn(d.get('end_date',''))}"
                )
            _banner_text = "   ·   ".join(_deleg_texts) + "   " * 5
            ui.html(f"""
                <div style="background:white; color:#8B0000;
                            border: 2px solid #8B0000; border-radius:8px;
                            padding:10px 16px; margin-bottom:10px;
                            overflow:hidden; font-size:15px; font-weight:600;">
                  <marquee behavior="scroll" direction="left" scrollamount="5"
                           style="white-space:nowrap; color:#8B0000;">
                    {_banner_text * 3}
                  </marquee>
                </div>
            """).classes("w-full")

        _page_header("Quản lý Nghỉ phép", "Đăng ký và phê duyệt nghỉ phép")



        # ── Load dữ liệu song song ────────────────────────────────────────────

        my_leaves, pending_leaves, all_leaves, dept_leaves, declared_leaves, delegations, balance_info, approver_list = \
            [], [], [], [], [], [], {}, []
        my_balance = {}



        can_dept     = user_role in ("truong_phong", "pho_phong")

        can_declared = api.has_feature("leaves.declare_direct")

        # Placeholder → chỉ có giá trị khi can_all=True (filter Dashboard)

        _f_from = _f_to = None



        async def _empty():

            return []



        try:

            results = await asyncio.gather(

                asyncio.to_thread(api.get, "/api/leaves/", {"scope": "mine"}),

                asyncio.to_thread(api.get, "/api/leaves/", {"scope": "pending"}),

                asyncio.to_thread(api.get, "/api/leaves/", {"scope": "all"}) if can_all else _empty(),

                asyncio.to_thread(api.get, "/api/leaves/", {"scope": "dept"}) if can_dept else _empty(),

                asyncio.to_thread(api.get, "/api/leaves/", {"scope": "declared"}) if can_declared else _empty(),

                asyncio.to_thread(api.get, "/api/delegations/") if can_delegation else _empty(),

                asyncio.to_thread(api.get, "/api/auth/me"),

                asyncio.to_thread(api.get, "/api/leaves/approvers") if show_approver else _empty(),

                asyncio.to_thread(api.get, "/api/leaves/my-balance"),

                return_exceptions=True,

            )

            my_leaves, pending_leaves, all_leaves, dept_leaves, declared_leaves, delegations, balance_info, approver_list, my_balance = results

            for r in results:

                if isinstance(r, api.SessionExpiredError):

                    ui.notify(str(r), type="warning")

                    ui.navigate.to("/login")

                    return

            # Lỗi khác (403/500/timeout...) bị return_exceptions=True nuốt thành giá
            # trị Exception — nếu không báo, all_leaves/dept_leaves... biến thành []
            # âm thầm và Dashboard/5 ô KPI/các bảng chỉ hiện toàn số 0 mà không ai
            # biết vì sao (vd cấp quyền leaves.forward_th cho người không thuộc
            # Phòng Tổng hợp → can_all=True ở frontend nhưng scope=all bị 403 ở
            # backend).
            _fetch_errors = [
                _name for _name, _val in (
                    ("Đơn của tôi", my_leaves), ("Chờ duyệt", pending_leaves),
                    ("Toàn trung tâm", all_leaves), ("Phòng tôi", dept_leaves),
                    ("Đã khai báo hộ", declared_leaves),
                )
                if isinstance(_val, Exception)
            ]

            if _fetch_errors:

                ui.notify(

                    f"Không tải được: {', '.join(_fetch_errors)} — số liệu có thể thiếu/sai, vui lòng tải lại trang.",

                    type="negative", timeout=8000)

            my_leaves      = my_leaves       if isinstance(my_leaves, list)      else []

            pending_leaves = pending_leaves  if isinstance(pending_leaves, list)  else []

            all_leaves     = all_leaves      if isinstance(all_leaves, list)      else []

            dept_leaves    = dept_leaves     if isinstance(dept_leaves, list)     else []

            declared_leaves = declared_leaves if isinstance(declared_leaves, list) else []

            delegations    = delegations     if isinstance(delegations, list)     else []

            balance_info   = balance_info    if isinstance(balance_info, dict)    else {}

            approver_list  = approver_list   if isinstance(approver_list, list)   else []

            my_balance     = my_balance      if isinstance(my_balance, dict)      else {}

        except Exception as e:

            if _handle_api_error(e):

                return



        pending_ids = {lv["id"] for lv in pending_leaves}



        # Badge sidebar do khối "Công việc chờ xử lý" trong shared.py tự nạp.



        if any(lv.get("status") == "rejected" for lv in my_leaves):

            ui.notify("Có đơn nghỉ phép bị từ chối. Xem tab 'Của tôi'.", type="negative", timeout=8000)



        # ── Balance card ──────────────────────────────────────────────────────
        # Lấy từ /api/leaves/my-balance (tôn trọng override hạn mức thủ công +
        # cộng carry-over) thay vì annual_leave_days ở /api/auth/me (chỉ tính
        # theo công thức tự động, không có carry-over) — khớp đúng tab Hạn mức phép.

        quota     = my_balance.get("quota_days", 12)

        carry     = my_balance.get("carry_over", 0)

        annual    = quota + carry

        remaining = my_balance.get("remaining", max(0, annual - my_balance.get("used_days", 0)))

        with ui.row().classes("gap-4 mb-4"):

            with ui.card().classes("bg-blue-50 border border-blue-200 p-4 rounded-xl min-w-40"):

                ui.label("Phép còn lại").classes("text-xs text-blue-600")

                ui.label(f"{remaining:g} / {annual:g} ngày").classes("text-xl font-bold text-blue-800")



        # ── Dialogs tạo đơn / nộp lại ────────────────────────────────────────

        approver_opts = {s["id"]: f"{s['full_name']} → {s['role_label']}" for s in approver_list}



        _today_slash = _dt_mod.date.today().isoformat().replace('-', '/')

        _today_iso   = _dt_mod.date.today().isoformat()

        # Quasar mặc định khoanh "hôm nay" bằng box-shadow 1px currentColor — quá
        # mờ để thấy được trên nền sáng. Ghi đè rõ ràng hơn cho mọi lịch chọn ngày
        # trong trang này.
        ui.add_css(".q-date__today { box-shadow: 0 0 0 2px #C62828 !important; border-radius: 50%; }")

        _VI_LOCALE = (
            ":locale=\"{ days: ['Chủ nhật','Thứ 2','Thứ 3','Thứ 4','Thứ 5','Thứ 6','Thứ 7'],"
            " daysShort: ['CN','T2','T3','T4','T5','T6','T7'],"
            " months: ['Tháng 1','Tháng 2','Tháng 3','Tháng 4','Tháng 5','Tháng 6',"
            "'Tháng 7','Tháng 8','Tháng 9','Tháng 10','Tháng 11','Tháng 12'],"
            " monthsShort: ['T01','T02','T03','T04','T05','T06','T07','T08','T09','T10','T11','T12'] }\""
        )

        _OPT_FUTURE  = f":options=\"d => d >= '{_today_slash}'\" {_VI_LOCALE}"

        _OPT_ALL     = f":options=\"() => true\" {_VI_LOCALE}"



        # Lấy danh sách GĐ/PGĐ để chọn khi tạo đơn

        gd_opts: dict = {}

        try:

            gd_list = await asyncio.to_thread(api.get, "/api/delegations/staff/giam-doc")

            pgd_list = await asyncio.to_thread(api.get, "/api/delegations/staff/pho-giam-doc")

            for s in (gd_list or []):

                gd_opts[s["id"]] = s["full_name"] + " (GĐ)"

            for s in (pgd_list or []):

                gd_opts[s["id"]] = s["full_name"] + " (PGĐ)"

        except Exception as e:

            if _handle_api_error(e):

                return

            # gd_opts rỗng → field "Ban lãnh đạo phê duyệt" sẽ ẩn khỏi form Tạo đơn

            # (xem điều kiện gd_opts and user_role != "giam_doc" bên dưới) — cảnh

            # báo rõ để người dùng biết đây là do lỗi tải dữ liệu, không phải thiết kế.

            ui.notify("Không tải được danh sách GĐ/PGĐ — vui lòng tải lại trang trước khi tạo đơn", type="negative")



        with ui.dialog() as create_dialog, ui.card().classes("p-6 w-[420px]"):

            ui.label("Tạo đơn nghỉ phép").classes("text-lg font-bold text-red-900 mb-4")

            import calendar as _cal_mod2
            from datetime import date as _dobj

            _c_today_ref = _dobj.today()
            _c_sel       = set()
            _c_cur       = [_c_today_ref.year, _c_today_ref.month]
            _c_min       = [_c_today_ref]   # list để mutate trong closure

            c_grid_area = ui.column().classes("w-full border border-gray-200 rounded p-2 bg-white")
            c_hint      = ui.label("Click chọn từng ngày · Click lại để bỏ chọn").classes("text-xs text-orange-500 mt-0.5")

            # ── Date picker cho thai sản / bảo hiểm ──────────────────────────────
            _rs_val = [""]   # YYYY-MM-DD ngày bắt đầu
            _re_val = [""]   # YYYY-MM-DD ngày kết thúc
            _rs_cur = [_c_today_ref.year, _c_today_ref.month]
            _re_cur = [_c_today_ref.year, _c_today_ref.month]

            c_range_area = ui.column().classes("w-full gap-2 mt-1")
            c_range_area.set_visibility(False)
            with c_range_area:
                ui.label("Chọn khoảng thời gian nghỉ").classes("text-xs text-blue-600 font-medium -mb-1")
                # Picker ngày bắt đầu
                with ui.column().classes("w-full gap-0"):
                    with ui.row().classes("w-full items-center gap-1"):
                        c_range_start = ui.input("Ngày bắt đầu", placeholder="DD/MM/YYYY").classes("flex-1")
                        _rs_cal_btn   = ui.button(icon="calendar_month").props("flat round dense size=sm color=grey-7")
                    _rs_cal = ui.column().classes("w-full border border-gray-200 rounded p-2 bg-white mt-1")
                    _rs_cal.set_visibility(False)
                # Picker ngày kết thúc
                with ui.column().classes("w-full gap-0 mt-1"):
                    with ui.row().classes("w-full items-center gap-1"):
                        c_range_end = ui.input("Ngày kết thúc", placeholder="DD/MM/YYYY").classes("flex-1")
                        _re_cal_btn  = ui.button(icon="calendar_month").props("flat round dense size=sm color=grey-7")
                    _re_cal = ui.column().classes("w-full border border-gray-200 rounded p-2 bg-white mt-1")
                    _re_cal.set_visibility(False)

            # ── Render calendar cho từng picker ───────────────────────────────────
            def _rs_render():
                _rs_cal.clear()
                y, m = _rs_cur
                with _rs_cal:
                    with ui.row().classes("w-full items-center justify-between mb-1"):
                        ui.button(icon="chevron_left",  on_click=_rs_prev).props("flat round dense size=sm")
                        ui.label(f"Tháng {m:02d}/{y}").classes("text-sm font-semibold text-gray-700")
                        ui.button(icon="chevron_right", on_click=_rs_next).props("flat round dense size=sm")
                    with ui.row().classes("w-full gap-0"):
                        for h in ["T2","T3","T4","T5","T6","T7","CN"]:
                            ui.label(h).classes("text-xs text-center text-gray-500 w-[14.28%] py-0.5")
                    first_wd = _dobj(y, m, 1).weekday()
                    last_day = _cal_mod2.monthrange(y, m)[1]
                    today_   = _dobj.today()
                    with ui.row().classes("w-full gap-0 flex-wrap"):
                        for _ in range(first_wd):
                            ui.label("").classes("w-[14.28%] h-7")
                        for day in range(1, last_day + 1):
                            ds = f"{y:04d}-{m:02d}-{day:02d}"; dobj = _dobj(y, m, day)
                            sel = (ds == _rs_val[0]); is_td = (dobj == today_); wknd = dobj.weekday() >= 5
                            def _pick_rs(ds=ds):
                                def _do():
                                    _rs_val[0] = ds
                                    c_range_start.value = f"{ds[8:10]}/{ds[5:7]}/{ds[0:4]}"
                                    _rs_cal.set_visibility(False); _rs_render()
                                return _do
                            with ui.element("div").classes("w-[14.28%] h-7 flex items-center justify-center"):
                                if sel:
                                    ui.label(str(day)).classes("w-6 h-6 rounded-full bg-red-700 text-white text-xs font-bold flex items-center justify-center cursor-pointer").on("click", _pick_rs())
                                elif is_td:
                                    ui.label(str(day)).classes("w-6 h-6 rounded-full ring-2 ring-red-500 text-red-600 text-xs font-bold flex items-center justify-center cursor-pointer hover:bg-red-50").on("click", _pick_rs())
                                elif wknd:
                                    ui.label(str(day)).classes("w-6 h-6 rounded flex items-center justify-center text-xs text-blue-300 hover:bg-blue-50 cursor-pointer").on("click", _pick_rs())
                                else:
                                    ui.label(str(day)).classes("w-6 h-6 rounded flex items-center justify-center text-xs text-gray-600 hover:bg-red-50 hover:text-red-700 cursor-pointer").on("click", _pick_rs())

            def _rs_prev():
                y, m = _rs_cur; _rs_cur[0], _rs_cur[1] = (y-1, 12) if m == 1 else (y, m-1); _rs_render()
            def _rs_next():
                y, m = _rs_cur; _rs_cur[0], _rs_cur[1] = (y+1, 1) if m == 12 else (y, m+1); _rs_render()
            def _rs_toggle():
                vis = not _rs_cal.visible; _rs_cal.set_visibility(vis)
                if vis: _rs_render()
            def _rs_parse():
                txt = c_range_start.value.strip()
                if not txt: _rs_val[0] = ""; return
                try:
                    parts = txt.replace("-", "/").split("/")
                    if len(parts) != 3 or len(parts[2]) != 4:
                        raise ValueError("Định dạng phải là dd/mm/yyyy")
                    d, mo, yr = int(parts[0]), int(parts[1]), int(parts[2])
                    _dobj(yr, mo, d); _rs_val[0] = f"{yr:04d}-{mo:02d}-{d:02d}"
                except Exception: _rs_val[0] = ""
            _rs_cal_btn.on("click", _rs_toggle)
            c_range_start.on("blur", _rs_parse)

            def _re_render():
                _re_cal.clear()
                y, m = _re_cur
                with _re_cal:
                    with ui.row().classes("w-full items-center justify-between mb-1"):
                        ui.button(icon="chevron_left",  on_click=_re_prev).props("flat round dense size=sm")
                        ui.label(f"Tháng {m:02d}/{y}").classes("text-sm font-semibold text-gray-700")
                        ui.button(icon="chevron_right", on_click=_re_next).props("flat round dense size=sm")
                    with ui.row().classes("w-full gap-0"):
                        for h in ["T2","T3","T4","T5","T6","T7","CN"]:
                            ui.label(h).classes("text-xs text-center text-gray-500 w-[14.28%] py-0.5")
                    first_wd = _dobj(y, m, 1).weekday()
                    last_day = _cal_mod2.monthrange(y, m)[1]
                    today_   = _dobj.today()
                    with ui.row().classes("w-full gap-0 flex-wrap"):
                        for _ in range(first_wd):
                            ui.label("").classes("w-[14.28%] h-7")
                        for day in range(1, last_day + 1):
                            ds = f"{y:04d}-{m:02d}-{day:02d}"; dobj = _dobj(y, m, day)
                            sel = (ds == _re_val[0]); is_td = (dobj == today_); wknd = dobj.weekday() >= 5
                            def _pick_re(ds=ds):
                                def _do():
                                    _re_val[0] = ds
                                    c_range_end.value = f"{ds[8:10]}/{ds[5:7]}/{ds[0:4]}"
                                    _re_cal.set_visibility(False); _re_render()
                                return _do
                            with ui.element("div").classes("w-[14.28%] h-7 flex items-center justify-center"):
                                if sel:
                                    ui.label(str(day)).classes("w-6 h-6 rounded-full bg-red-700 text-white text-xs font-bold flex items-center justify-center cursor-pointer").on("click", _pick_re())
                                elif is_td:
                                    ui.label(str(day)).classes("w-6 h-6 rounded-full ring-2 ring-red-500 text-red-600 text-xs font-bold flex items-center justify-center cursor-pointer hover:bg-red-50").on("click", _pick_re())
                                elif wknd:
                                    ui.label(str(day)).classes("w-6 h-6 rounded flex items-center justify-center text-xs text-blue-300 hover:bg-blue-50 cursor-pointer").on("click", _pick_re())
                                else:
                                    ui.label(str(day)).classes("w-6 h-6 rounded flex items-center justify-center text-xs text-gray-600 hover:bg-red-50 hover:text-red-700 cursor-pointer").on("click", _pick_re())

            def _re_prev():
                y, m = _re_cur; _re_cur[0], _re_cur[1] = (y-1, 12) if m == 1 else (y, m-1); _re_render()
            def _re_next():
                y, m = _re_cur; _re_cur[0], _re_cur[1] = (y+1, 1) if m == 12 else (y, m+1); _re_render()
            def _re_toggle():
                vis = not _re_cal.visible; _re_cal.set_visibility(vis)
                if vis: _re_render()
            def _re_parse():
                txt = c_range_end.value.strip()
                if not txt: _re_val[0] = ""; return
                try:
                    parts = txt.replace("-", "/").split("/")
                    if len(parts) != 3 or len(parts[2]) != 4:
                        raise ValueError("Định dạng phải là dd/mm/yyyy")
                    d, mo, yr = int(parts[0]), int(parts[1]), int(parts[2])
                    _dobj(yr, mo, d); _re_val[0] = f"{yr:04d}-{mo:02d}-{d:02d}"
                except Exception: _re_val[0] = ""
            _re_cal_btn.on("click", _re_toggle)
            c_range_end.on("blur", _re_parse)

            def _c_render():
                c_grid_area.clear()
                y, m = _c_cur
                min_d = _c_min[0]
                with c_grid_area:
                    with ui.row().classes("w-full items-center justify-between mb-1"):
                        ui.button(icon="chevron_left", on_click=_c_prev).props("flat round dense size=sm")
                        ui.label(f"Tháng {m:02d}/{y}").classes("text-sm font-semibold text-gray-700")
                        ui.button(icon="chevron_right", on_click=_c_next).props("flat round dense size=sm")
                    with ui.row().classes("w-full gap-0"):
                        for h in ["T2","T3","T4","T5","T6","T7","CN"]:
                            ui.label(h).classes("text-xs text-center text-gray-500 w-[14.28%] py-0.5")
                    first_wd  = _dobj(y, m, 1).weekday()
                    last_day  = _cal_mod2.monthrange(y, m)[1]
                    _c_today_ = _dobj.today()
                    with ui.row().classes("w-full gap-0 flex-wrap"):
                        for _ in range(first_wd):
                            ui.label("").classes("w-[14.28%] h-7")
                        for day in range(1, last_day + 1):
                            ds    = f"{y:04d}-{m:02d}-{day:02d}"
                            dobj  = _dobj(y, m, day)
                            sel   = ds in _c_sel
                            past  = dobj < min_d
                            wknd  = dobj.weekday() >= 5
                            is_td = (dobj == _c_today_)
                            def _mk(ds=ds):
                                def _toggle():
                                    _c_sel.discard(ds) if ds in _c_sel else _c_sel.add(ds)
                                    _c_render()
                                return _toggle
                            wrap_cls = "w-[14.28%] h-7 flex items-center justify-center"
                            with ui.element("div").classes(wrap_cls):
                                if sel:
                                    inner = "w-6 h-6 rounded-full bg-red-700 text-white text-xs font-bold flex items-center justify-center cursor-pointer"
                                    if is_td:
                                        inner += " ring-2 ring-offset-1 ring-red-400"
                                    ui.label(str(day)).classes(inner).on("click", _mk())
                                elif past:
                                    inner = "w-6 h-6 flex items-center justify-center text-xs text-gray-500 hover:bg-red-50 hover:text-red-700 cursor-pointer rounded"
                                    if is_td:
                                        inner += " rounded-full ring-2 ring-gray-300"
                                    ui.label(str(day)).classes(inner).on("click", _mk())
                                elif is_td:
                                    ui.label(str(day)).classes(
                                        "w-6 h-6 rounded-full ring-2 ring-red-500 text-red-600 text-xs font-bold flex items-center justify-center cursor-pointer hover:bg-red-50"
                                    ).on("click", _mk())
                                elif wknd:
                                    ui.label(str(day)).classes("w-6 h-6 rounded flex items-center justify-center text-xs text-blue-300 hover:bg-blue-50 cursor-pointer").on("click", _mk())
                                else:
                                    ui.label(str(day)).classes("w-6 h-6 rounded flex items-center justify-center text-xs text-gray-600 hover:bg-red-50 hover:text-red-700 cursor-pointer").on("click", _mk())

            def _c_prev():
                y, m = _c_cur
                _c_cur[0], _c_cur[1] = (y-1, 12) if m == 1 else (y, m-1)
                _c_render()

            def _c_next():
                y, m = _c_cur
                _c_cur[0], _c_cur[1] = (y+1, 1) if m == 12 else (y, m+1)
                _c_render()

            _c_render()

            c_type     = ui.select({k: v for k, v in _LEAVE_TYPE.items()}, label="Loại nghỉ phép", value="annual").classes("w-full mt-2")

            c_reason   = ui.textarea("Lý do (tuỳ chọn)").classes("w-full mt-2")

            c_approver = ui.select(approver_opts, label="Người phê duyệt (KSV)").classes("w-full mt-2") if show_approver else None

            # Luôn hiện field này cho non-GĐ kể cả khi gd_opts rỗng (do tải lỗi) — để
            # validation "if c_gd and not c_gd.value" bên dưới thật sự chặn được submit.
            # Trước đây gd_opts rỗng thì c_gd = None, validation bị bỏ qua hoàn toàn,
            # đơn tạo ra với gd_approver_id=NULL và kẹt vĩnh viễn ở bước Tổng hợp (TH
            # không có chỗ nào để chọn GĐ thay, xem tong_hop_review — chỉ dùng lại
            # gd_approver_id có sẵn trên đơn, không cho chọn mới).
            c_gd       = ui.select(gd_opts, label="Ban lãnh đạo phê duyệt (GĐ/PGĐ)").classes("w-full mt-2") if user_role != "giam_doc" else None



            def _c_on_type():

                lt = c_type.value
                is_range = lt in ("thai_san", "bao_hiem")

                c_grid_area.set_visibility(not is_range)
                c_hint.set_visibility(not is_range)
                c_range_area.set_visibility(is_range)

                c_reason.props(f'label="{"Lý do (bắt buộc)" if lt == "other" else "Lý do (tuỳ chọn)"}"')

                if not is_range:
                    if lt in ("annual", "bat_buoc"):
                        _c_min[0] = _dobj.today()
                        c_hint.set_text("Chỉ chọn ngày từ hôm nay trở đi" if lt == "annual" else "Tối thiểu 5 ngày làm việc")
                        c_hint.style("color:#f97316" if lt == "annual" else "color:#3b82f6")
                    else:
                        _c_min[0] = _dobj(2000, 1, 1)
                        c_hint.set_text("Nhập lý do bên dưới" if lt == "other" else "Click chọn từng ngày")
                        c_hint.style("color:#6b7280")
                    _c_sel.clear()
                    _c_render()



            c_type.on("update:model-value", _c_on_type)



            async def do_create():

                lt = c_type.value
                is_range = lt in ("thai_san", "bao_hiem")

                if is_range:
                    _rs_parse(); _re_parse()   # flush giá trị nhập tay nếu chưa blur
                    start_val = _rs_val[0]
                    end_val   = _re_val[0]
                    if not start_val or not end_val:
                        ui.notify("Vui lòng chọn hoặc nhập ngày bắt đầu và ngày kết thúc (DD/MM/YYYY)", type="warning"); return
                    if end_val < start_val:
                        ui.notify("Ngày kết thúc phải sau ngày bắt đầu", type="warning"); return
                    body = {"start_date": start_val, "end_date": end_val,
                            "leave_type": lt, "reason": c_reason.value or None}
                else:
                    dates = sorted(_c_sel)

                    if not dates:
                        ui.notify("Vui lòng chọn ít nhất 1 ngày", type="warning"); return

                    if lt == "other" and not (c_reason.value or "").strip():
                        ui.notify("Vui lòng nhập lý do khi chọn loại Khác", type="warning"); return

                    body = {"start_date": dates[0], "end_date": dates[-1],
                            "spread_dates": dates,
                            "leave_type": lt, "reason": c_reason.value or None}

                if show_approver and not c_approver.value:
                    ui.notify("Vui lòng chọn người phê duyệt (KSV)", type="warning"); return

                if c_gd and not c_gd.value:
                    ui.notify("Vui lòng chọn Ban lãnh đạo phê duyệt", type="warning"); return

                if show_approver:
                    body["ksv_approver_id"] = c_approver.value

                if c_gd and c_gd.value:
                    body["gd_approver_id"] = c_gd.value

                async def _send(_body=body):
                    try:
                        await asyncio.to_thread(api.post, "/api/leaves/", _body)

                        create_dialog.close()

                        if user_role == "giam_doc":
                            ui.notify("✅ Đơn nghỉ phép đã được ghi nhận và tự động duyệt.",
                                      type="positive", timeout=4000)
                        else:
                            ui.notify("✅ Gửi đơn nghỉ phép thành công! Đơn đang chờ phê duyệt.",
                                      type="positive", timeout=4000)

                        ui.timer(2.5, lambda: ui.navigate.to("/leaves"), once=True)

                    except api.QuotaExceededBorrowError as e:
                        # Vượt hạn mức năm nay nhưng năm sau còn đủ chỗ ứng — hỏi xác
                        # nhận thay vì chặn cứng, xem _check_quota_or_borrow ở backend.
                        async def _retry_with_borrow(_body2=_body):
                            _body2["confirm_borrow_next_year"] = True
                            await _send(_body2)
                        _ask_confirm(
                            "Vượt hạn mức phép",
                            f"Đơn nghỉ phép đã vượt quá hạn mức ngày nghỉ phép năm {e.year} "
                            f"(còn lại {e.remaining:.0f} ngày). Bạn có muốn tiếp tục ứng trước "
                            f"{e.borrow_days:.0f} ngày phép của năm {e.next_year} không?",
                            _retry_with_borrow, "Đồng ý ứng phép", "bg-orange-600",
                        )

                    except Exception as e:

                        if not _handle_api_error(e):

                            ui.notify(f"Gửi đơn thất bại: {e}", type="negative", timeout=5000)

                # Xem trước bản in thật rồi mới gửi — người làm đơn tự đặt chữ ký.
                pv = await _fetch_preview(lambda: api.post("/api/leaves/preview", body, 120))
                if pv is None:
                    return
                if pv is False:
                    # Không dựng được bản xem trước — hỏi rồi gửi đơn không chữ ký,
                    # chứ không chặn luôn việc nộp đơn.
                    _ask_confirm("Không xem trước được đơn",
                                 "Máy chủ chưa dựng được bản in. Vẫn gửi đơn (phiếu sẽ không có chữ ký)?",
                                 _send, "Vẫn gửi", "bg-red-700")
                    return

                box = await _open_sign_dialog(pv, "Xem trước đơn xin nghỉ phép",
                                              "Ký và gửi đơn", "bg-red-700")
                if box is None:
                    return
                if box:
                    body["signature"] = box
                await _send(body)



            def _c_open():
                _c_today_now = _dobj.today()
                _c_sel.clear()
                _c_min[0] = _c_today_now
                _c_cur[0], _c_cur[1] = _c_today_now.year, _c_today_now.month
                c_type.value = "annual"
                c_reason.value = ""
                if c_approver:
                    c_approver.value = None
                if c_gd:
                    c_gd.value = None
                _rs_val[0] = ""; _re_val[0] = ""
                _rs_cur[0], _rs_cur[1] = _c_today_now.year, _c_today_now.month
                _re_cur[0], _re_cur[1] = _c_today_now.year, _c_today_now.month
                c_range_start.value = ""
                c_range_end.value   = ""
                _rs_cal.set_visibility(False)
                _re_cal.set_visibility(False)
                c_grid_area.set_visibility(True)
                c_hint.set_visibility(True)
                c_range_area.set_visibility(False)
                _c_render()
                create_dialog.open()

            with ui.row().classes("w-full justify-end gap-2 mt-4"):

                ui.button("Hủy", on_click=create_dialog.close).classes("text-gray-500")

                ui.button("Gửi đơn", on_click=do_create).classes("bg-red-700 text-white")



        # ── Dialog nộp lại ────────────────────────────────────────────────────

        _rsub_id: list = [None]
        # "resubmit" (đơn bị từ chối, sửa & nộp lại — PUT /resubmit, ghi đè
        # đơn cũ) hoặc "npbb_adjust" (đơn bat_buoc đã duyệt, POST /npbb-adjust
        # tạo đơn MỚI liên kết qua adjusts_leave_id — xem _open_npbb_adjust).
        _rsub_mode: list = ["resubmit"]

        with ui.dialog() as resubmit_dialog, ui.card().classes("p-6 w-[420px]"):

            resubmit_title = ui.label("Chỉnh sửa & Nộp lại").classes("text-lg font-bold text-red-900 mb-4")

            r_dates    = ui.date(value=[]).props(f"multiple mask='YYYY-MM-DD' no-header first-day-of-week='1' {_OPT_FUTURE}").classes("w-full")

            r_hint     = ui.label("Click chọn từng ngày → Click lại để bỏ chọn").classes("text-xs text-orange-500 mt-0.5")

            r_type     = ui.select({k: v for k, v in _LEAVE_TYPE.items()}, label="Loại nghỉ phép", value="annual").classes("w-full mt-2")

            r_reason   = ui.textarea("Lý do (tuỳ chọn)").classes("w-full mt-2")

            r_approver = ui.select(approver_opts, label="Người phê duyệt (KSV)").classes("w-full mt-2") if show_approver else None

            r_gd_select = ui.select({}, label="Ban lãnh đạo phê duyệt (GĐ/PGĐ)").classes("w-full mt-2")

            def _r_on_type():

                lt = r_type.value

                if lt == "annual":

                    r_dates.props(_OPT_FUTURE)

                    r_hint.set_text("Chỉ chọn ngày từ hôm nay trở đi")

                    r_hint.style("color:#f97316")

                elif lt == "bat_buoc":

                    r_dates.props(_OPT_FUTURE)

                    r_hint.set_text("Tối thiểu 5 ngày làm việc liên tiếp")

                    r_hint.style("color:#3b82f6")

                else:

                    r_dates.props(_OPT_ALL)

                    r_hint.set_text("")

                    r_hint.style("color:#6b7280")



            r_type.on("update:model-value", _r_on_type)



            async def do_resubmit():

                lid = _rsub_id[0]

                raw = r_dates.value

                if not lid or not raw:

                    ui.notify("Vui lòng chọn ít nhất 1 ngày", type="warning"); return

                dates = sorted(set(raw if isinstance(raw, list) else [raw]))

                dates = [d[:10] for d in dates if d]

                if not dates:

                    ui.notify("Vui lòng chọn ít nhất 1 ngày", type="warning"); return

                if show_approver and not r_approver.value:

                    ui.notify("Vui lòng chọn người phê duyệt", type="warning"); return

                # Bắt buộc chọn GĐ/PGĐ giống dialog Tạo đơn — không được coi là tuỳ
                # chọn: nộp lại mà bỏ trống sẽ xoá mất GĐ đã chọn trước đó (backend chỉ
                # ghi đè khi có gd_approver_id gửi lên), và TH không có cách nào chọn
                # bù ở bước sau — đơn sẽ kẹt vĩnh viễn ở pending_tong_hop.
                if not r_gd_select.value:

                    ui.notify("Vui lòng chọn Ban lãnh đạo phê duyệt", type="warning"); return

                body = {"start_date": dates[0], "end_date": dates[-1],

                        "spread_dates": dates,

                        "leave_type": r_type.value, "reason": r_reason.value or None,

                        "gd_approver_id": r_gd_select.value}

                if show_approver:
                    body["ksv_approver_id"] = r_approver.value

                _is_npbb = _rsub_mode[0] == "npbb_adjust"
                try:
                    if _is_npbb:
                        await asyncio.to_thread(api.post, f"/api/leaves/{lid}/npbb-adjust", body)
                    else:
                        await asyncio.to_thread(api.put, f"/api/leaves/{lid}/resubmit", body)

                    resubmit_dialog.close()

                    detail_drawer.hide()

                    ui.notify("Đã tạo đơn điều chỉnh NPBB!" if _is_npbb else "Đã nộp lại đơn!",
                              type="positive")

                    ui.navigate.to("/leaves")

                except Exception as e:

                    _handle_api_error(e)



            with ui.row().classes("w-full justify-end gap-2 mt-4"):

                ui.button("Hủy", on_click=resubmit_dialog.close).classes("text-gray-500")

                resubmit_submit_btn = ui.button("Nộp lại", on_click=do_resubmit).classes("bg-orange-600 text-white")



        # ── Hôm mở drawer chi tiết ────────────────────────────────────────────

        async def open_detail(leave: dict):

            drawer_container.clear()

            with drawer_container:

                lid      = leave["id"]

                status   = leave["status"]

                is_owner = user_id is not None and leave.get("staff_id") == user_id

                in_pend  = lid in pending_ids

                _approver_roles = ("truong_phong", "pho_phong",
                                   "giam_doc", "pho_giam_doc", "admin")
                _can_act = user_role in _approver_roles

                ksv_act  = status == "pending_ksv" and in_pend and user_role in ("truong_phong", "pho_phong")

                th_act   = status == "pending_tong_hop" and in_pend and (_can_act or can_forward_th)

                gd_act   = status == "pending_gd" and in_pend and user_role in ("giam_doc", "pho_giam_doc")

                # Đơn của GĐ đã tự động approved — TH chỉ cần "xác nhận đã biết" (thông báo),
                # không phải điều kiện duyệt.
                th_ack_act = (status == "approved" and leave.get("staff_role") == "giam_doc"
                              and not leave.get("tong_hop_approver_id"))



                with ui.row().classes("w-full bg-red-800 text-white px-5 py-4 items-center gap-2"):

                    ui.icon("event_busy").classes("text-2xl")

                    with ui.column().classes("gap-0"):

                        ui.label("Chi tiết đơn nghỉ phép").classes("font-bold text-base")

                        ui.label(leave.get("staff_name", "")).classes("text-red-200 text-sm")



                with ui.column().classes("px-5 py-4 gap-3 w-full"):

                    with ui.row().classes("items-center gap-2"):

                        ui.label("Trạng thái:").classes("text-sm text-gray-600 font-medium")

                        _leave_status_badge(status, leave.get("status_label"))



                    def _info(lbl, val):

                        with ui.row().classes("w-full items-start gap-2"):

                            ui.label(lbl).classes("text-sm text-gray-500 w-28 shrink-0")

                            ui.label(str(val) if val else "→").classes("text-sm font-medium flex-1")



                    _info("Phòng:", leave.get("department_name") or "→")

                    _sd = leave.get("spread_dates")

                    _s  = (leave.get("start_date") or "")[:10]

                    _e  = (leave.get("end_date") or "")[:10]

                    if _sd and len(_sd) >= 2:

                        from datetime import date as _d

                        with ui.row().classes("w-full items-start gap-2"):

                            ui.label("Ngày nghỉ:").classes("text-sm text-gray-500 w-28 shrink-0")

                            with ui.column().classes("flex-1 gap-0.5"):

                                for _dstr in sorted(_sd):

                                    try:

                                        ui.label(_d.fromisoformat(_dstr[:10]).strftime("%d/%m/%Y")).classes("text-sm font-medium")

                                    except Exception:

                                        ui.label(_dstr[:10]).classes("text-sm font-medium")

                    else:

                        _info("Từ ngày:", _s)

                        _info("Đến ngày:", _e)

                    _info("Số ngày nghỉ:", f"{leave.get('leave_days', '')} ngày")

                    _info("Loại:", _LEAVE_TYPE.get(leave.get("leave_type", ""), leave.get("leave_type", "")))

                    _info("Lý do:", leave.get("reason") or "→")

                    # NPBB — đơn NÀY là đơn điều chỉnh: hiện lại ngày ĐÃ ĐĂNG KÝ của đơn
                    # gốc để đối chiếu (đơn gốc trỏ qua adjusts_leave, xem npbb_adjust_leave()
                    # ở backend).
                    _adjusts = leave.get("adjusts_leave")
                    if _adjusts:
                        with ui.column().classes("w-full gap-1 p-3 bg-orange-50 border border-orange-200 rounded"):
                            ui.label("Điều chỉnh từ đơn nghỉ phép bắt buộc đã đăng ký").classes(
                                "text-xs font-medium text-orange-700")
                            ui.label(
                                f"Ngày đã đăng ký: {_fmt_leave_dates(_adjusts.get('start_date') or '', _adjusts.get('end_date') or '', _adjusts.get('spread_dates'))}"
                            ).classes("text-sm text-gray-700")

                    # NPBB — đơn NÀY là đơn gốc: nếu đã có ai điều chỉnh, hiện trạng thái
                    # đơn điều chỉnh liên kết (approved thì đơn gốc đã tự "Đã hủy - Đã điều
                    # chỉnh", xem status_label ở backend).
                    _npbb_adj = leave.get("npbb_adjustment")
                    if _npbb_adj:
                        _adj_status_vn = {
                            "pending_ksv": "Chờ KSV duyệt", "pending_tong_hop": "Chờ Tổng hợp",
                            "pending_gd": "Chờ Ban lãnh đạo duyệt", "approved": "Đã duyệt",
                            "rejected": "Bị từ chối", "cancelled": "Đã hủy",
                        }.get(_npbb_adj.get("status"), _npbb_adj.get("status"))
                        with ui.column().classes("w-full gap-1 p-3 bg-orange-50 border border-orange-200 rounded"):
                            ui.label(f"Có đơn điều chỉnh ngày NPBB ({_adj_status_vn})").classes(
                                "text-xs font-medium text-orange-700")
                            ui.label(
                                f"Ngày đề nghị điều chỉnh: {_fmt_leave_dates(_npbb_adj.get('start_date') or '', _npbb_adj.get('end_date') or '', _npbb_adj.get('spread_dates'))}"
                            ).classes("text-sm text-gray-700")



                    if leave.get("is_direct"):

                        # Khai báo hộ → không qua quy trình duyệt

                        with ui.column().classes("w-full bg-purple-50 rounded-lg p-3 gap-1 border border-purple-100"):

                            ui.label("Khai báo hộ → Duyệt trực tiếp").classes("text-xs font-bold text-purple-700 uppercase")

                            _info("Người khai báo:", leave.get("declarer_name") or "→")

                            _info("Ghi chú:", "Đơn được khai báo và duyệt trực tiếp, không qua quy trình phê duyệt.")

                    else:

                        _is_admin = user_role == "admin"

                        # Bước 1: KSV
                        if leave.get("ksv_approver_id") or status == "pending_ksv":

                            with ui.column().classes("w-full bg-orange-50 rounded-lg p-3 gap-1 border border-orange-100"):

                                with ui.row().classes("w-full items-center justify-between"):
                                    ui.label("Bước 1 → KSV phê duyệt").classes("text-xs font-bold text-orange-700 uppercase")
                                    if _is_admin and status == "pending_ksv":
                                        with ui.row().classes("gap-1"):
                                            async def _admin_ksv_approve(lv=leave, l=lid):
                                                async def _do(payload, _l=l):
                                                    try:
                                                        await asyncio.to_thread(api.put, f"/api/leaves/{_l}/ksv-review", payload)
                                                        ui.notify("Đã duyệt bước KSV! Tiếp tục duyệt bước TH.", type="positive")
                                                        updated = await asyncio.to_thread(api.get, f"/api/leaves/{_l}")
                                                        if updated: await open_detail(updated)
                                                    except Exception as e:
                                                        _handle_api_error(e)
                                                async def _run(_l=l):
                                                    await _sign_then_approve(_l, "ksv", f"/api/leaves/{_l}/preview",
                                                                             "Duyệt bước KSV", _do)
                                                await _borrow_confirm_or_run(lv, _run)
                                            ui.button(icon="check", on_click=_admin_ksv_approve).props("round dense flat").classes("text-green-600 bg-green-50").tooltip("Phê duyệt KSV")
                                            async def _admin_ksv_reject(l=lid):
                                                async def _cb(reason, _l=l):
                                                    try:
                                                        await asyncio.to_thread(api.put, f"/api/leaves/{_l}/ksv-review", {"action": "reject", "comment": reason})
                                                        detail_drawer.hide(); ui.notify("Đã từ chối!", type="warning"); _nav_pending()
                                                    except Exception as e:
                                                        _handle_api_error(e)
                                                _reject_cb[0] = _cb; reject_dialog.open()
                                            ui.button(icon="close", on_click=_admin_ksv_reject).props("round dense flat").classes("text-red-600 bg-red-50").tooltip("Từ chối KSV")

                                _info("Người duyệt:", leave.get("ksv_approver_name") or "Chưa xác định")

                                if leave.get("ksv_approved_at"):
                                    _info("Ngày duyệt:", leave["ksv_approved_at"][:10])
                                    _info("Ý kiến:", leave.get("ksv_comment") or "→")
                                    ui.label("✓ Đã phê duyệt").classes("text-xs text-green-600 font-semibold mt-1")
                                elif status != "pending_ksv" and leave.get("ksv_approver_id"):
                                    ui.label("(Dữ liệu không ghi ngày duyệt)").classes("text-xs text-gray-500 italic")



                        # Bước 2: Tổng hợp

                        with ui.column().classes("w-full bg-yellow-50 rounded-lg p-3 gap-1 border border-yellow-100"):

                            with ui.row().classes("w-full items-center justify-between"):
                                ui.label("Bước 2 → Phòng Tổng hợp").classes("text-xs font-bold text-yellow-700 uppercase")
                                if _is_admin and status == "pending_tong_hop":
                                    with ui.row().classes("gap-1"):
                                        async def _admin_th_approve(lv=leave, l=lid):
                                            async def _do(_l=l, _lv=lv):
                                                try:
                                                    await asyncio.to_thread(api.post, f"/api/leaves/{_l}/tong-hop-review",
                                                        {"action": "forward", "gd_approver_id": _lv.get("gd_approver_id"), "comment": None})
                                                    ui.notify("Đã xác nhận TH! Tiếp tục duyệt bước GĐ.", type="positive")
                                                    updated = await asyncio.to_thread(api.get, f"/api/leaves/{_l}")
                                                    if updated: await open_detail(updated)
                                                except Exception as e:
                                                    _handle_api_error(e)
                                            _th_borrow = lv.get("borrow_next_year_days") or 0
                                            _th_msg = "Xác nhận & chuyển lên Ban lãnh đạo?"
                                            if _th_borrow:
                                                _th_msg += (f" ⚠ Đơn này có sử dụng {_th_borrow:.0f} ngày phép "
                                                            f"của {_borrow_year_label(lv)}.")
                                            _ask_confirm("Xác nhận TH", _th_msg, _do, "Xác nhận", "bg-green-600")
                                        ui.button(icon="check", on_click=_admin_th_approve).props("round dense flat").classes("text-green-600 bg-green-50").tooltip("Xác nhận TH")
                                        async def _admin_th_reject(l=lid):
                                            async def _cb(reason, _l=l):
                                                try:
                                                    await asyncio.to_thread(api.post, f"/api/leaves/{_l}/tong-hop-review", {"action": "reject", "comment": reason})
                                                    detail_drawer.hide(); ui.notify("Đã từ chối!", type="warning"); _nav_pending()
                                                except Exception as e:
                                                    _handle_api_error(e)
                                            _reject_cb[0] = _cb; reject_dialog.open()
                                        ui.button(icon="close", on_click=_admin_th_reject).props("round dense flat").classes("text-red-600 bg-red-50").tooltip("Từ chối TH")

                            _th_name = leave.get("tong_hop_approver_name")
                            _info("Người xử lý:", _th_name or "Chưa xử lý")

                            if leave.get("tong_hop_approved_at"):
                                _info("Ngày:", leave["tong_hop_approved_at"][:10])
                                _info("Ghi chú:", leave.get("tong_hop_comment") or "→")
                                ui.label("✓ Đã xác nhận").classes("text-xs text-green-600 font-semibold mt-1")
                            elif status not in ("pending_ksv", "pending_tong_hop") and _th_name:
                                ui.label("(Dữ liệu không ghi ngày xác nhận)").classes("text-xs text-gray-500 italic")

                            if th_ack_act and api.has_feature("leaves.forward_th"):
                                ui.label("Đơn của Giám đốc đã tự động duyệt — chỉ cần Tổng hợp xác nhận đã biết.").classes("text-xs text-gray-500 italic mt-1")
                                async def _th_ack(l=lid):
                                    try:
                                        await asyncio.to_thread(api.put, f"/api/leaves/{l}/tong-hop-ack", {})
                                        detail_drawer.hide()
                                        ui.notify("Đã xác nhận đã biết đơn của Giám đốc", type="positive")
                                        _nav_pending()
                                    except Exception as e:
                                        _handle_api_error(e)
                                ui.button("Xác nhận đã biết", icon="visibility", on_click=_th_ack).classes("bg-yellow-600 text-white text-xs mt-1")



                        # Bước 3: GĐ

                        with ui.column().classes("w-full bg-blue-50 rounded-lg p-3 gap-1 border border-blue-100"):

                            with ui.row().classes("w-full items-center justify-between"):
                                ui.label("Bước 3 → Giám đốc phê duyệt").classes("text-xs font-bold text-blue-700 uppercase")
                                if _is_admin and status == "pending_gd":
                                    with ui.row().classes("gap-1"):
                                        async def _admin_gd_approve(lv=leave, l=lid):
                                            async def _do(payload, _l=l):
                                                try:
                                                    await asyncio.to_thread(api.put, f"/api/leaves/{_l}/gd-review", payload)
                                                    detail_drawer.hide(); ui.notify("Đã duyệt GĐ!", type="positive"); _nav_pending()
                                                except Exception as e:
                                                    _handle_api_error(e)
                                            async def _run(_l=l):
                                                await _sign_then_approve(_l, "gd", f"/api/leaves/{_l}/preview",
                                                                         "Duyệt bước Giám đốc", _do)
                                            await _borrow_confirm_or_run(lv, _run)
                                        ui.button(icon="check", on_click=_admin_gd_approve).props("round dense flat").classes("text-green-600 bg-green-50").tooltip("Phê duyệt GĐ")
                                        async def _admin_gd_reject(l=lid):
                                            async def _cb(reason, _l=l):
                                                try:
                                                    await asyncio.to_thread(api.put, f"/api/leaves/{_l}/gd-review", {"action": "reject", "comment": reason})
                                                    detail_drawer.hide(); ui.notify("Đã từ chối!", type="warning"); _nav_pending()
                                                except Exception as e:
                                                    _handle_api_error(e)
                                            _reject_cb[0] = _cb; reject_dialog.open()
                                        ui.button(icon="close", on_click=_admin_gd_reject).props("round dense flat").classes("text-red-600 bg-red-50").tooltip("Từ chối GĐ")

                            _info("Người duyệt:", _gd_display(leave) or "Chưa xác định")

                            # Đơn đứng ở bước GĐ mà người được chỉ định là PGĐ hết ủy quyền:
                            # backend trả danh sách "chờ duyệt" RỖNG cho họ nên drawer không
                            # dựng nút nào — không nói ra thì màn hình trông y như bị lỗi.
                            if status == "pending_gd" and not leave.get("gd_can_review", True):
                                with ui.column().classes("w-full bg-amber-50 border-l-4 border-amber-500 rounded p-2 gap-0 mt-1"):
                                    ui.label("⚠ Ủy quyền của Phó Giám đốc đã hết hiệu lực").classes("text-xs font-bold text-amber-800")
                                    ui.label("Đơn đang đứng lại: người được chỉ định duyệt là Phó Giám đốc, "
                                             "nhưng giấy ủy quyền không còn hiệu lực cho ngày hôm nay nên hệ thống "
                                             "không cho bấm duyệt. Cần gia hạn ủy quyền ở tab \"Ủy quyền GĐ\", "
                                             "hoặc nhờ Quản trị viên duyệt thay.").classes("text-xs text-amber-900 leading-snug")

                            if leave.get("gd_approved_at"):
                                _info("Ngày duyệt:", leave["gd_approved_at"][:10])
                                _info("Ý kiến:", leave.get("gd_comment") or "→")
                                ui.label("✓ Đã phê duyệt").classes("text-xs text-green-600 font-semibold mt-1")
                            elif status == "approved":
                                ui.label("(Dữ liệu không ghi ngày duyệt)").classes("text-xs text-gray-500 italic")



                    ui.separator()



                    async def _download(l=lid):

                        try:

                            # timeout=160: backend cho Word cold-start tới 150s trước khi coi
                            # là treo thật (leave_pdf._CONVERT_TIMEOUT) — mặc định 60s của
                            # api.download() sẽ rớt về docx chưa ký oan dù server không lỗi.
                            content = await asyncio.to_thread(
                                api.download, f"/api/leaves/{l}/download", None, 160)

                            ui.download(content, f"phieu_nghi_phep_{l}.pdf")

                        except Exception as e:

                            if _handle_api_error(e):
                                return

                            # Máy chủ không chuyển được PDF (chưa cài Word / Word treo)
                            # → vẫn phải lấy được phiếu, tải bản Word không chữ ký.
                            ui.notify(f"Không tạo được PDF — đang tải bản Word. ({e})",
                                      type="warning", timeout=6000)
                            try:
                                content = await asyncio.to_thread(
                                    api.download, f"/api/leaves/{l}/download", {"fmt": "docx"})
                                ui.download(content, f"phieu_nghi_phep_{l}.docx")
                            except Exception as e2:
                                _handle_api_error(e2)



                    with ui.row().classes("gap-2 flex-nowrap mt-4 border-t border-gray-100 pt-4 w-full items-center").style("display:grid; grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));"):

                        ui.button("Tải phiếu", icon="download", on_click=_download).props("outline").classes("text-gray-700 font-bold w-full")




                        # KSV

                        if ksv_act and api.has_feature("leaves.approve_ksv"):

                            async def _ksv_approve(lv=leave, l=lid):

                                async def _do(payload, _l=l):

                                    try:

                                        await asyncio.to_thread(api.put, f"/api/leaves/{_l}/ksv-review", payload)

                                        detail_drawer.hide()

                                        ui.notify("Phê duyệt KSV thành công!", type="positive", timeout=3000)

                                        _nav_pending()

                                    except Exception as e:

                                        _handle_api_error(e)

                                async def _run(_l=l):
                                    await _sign_then_approve(_l, "ksv", f"/api/leaves/{_l}/preview",
                                                             "Xác nhận phê duyệt", _do)
                                await _borrow_confirm_or_run(lv, _run)



                            def _ksv_reject_open(l=lid):

                                async def _cb(reason, _l=l):

                                    try:

                                        await asyncio.to_thread(api.put, f"/api/leaves/{_l}/ksv-review",

                                            {"action": "reject", "comment": reason})

                                        detail_drawer.hide()

                                        ui.notify("Đã từ chối đơn.", type="warning", timeout=3000)

                                        _nav_pending()

                                    except Exception as e:

                                        _handle_api_error(e)

                                _reject_cb[0] = _cb

                                reject_dialog.open()



                            ui.button("Phê duyệt", icon="check_circle", on_click=_ksv_approve).classes("bg-green-600 text-white font-bold w-full")

                            ui.button("Từ chối", icon="cancel", on_click=_ksv_reject_open).classes("bg-red-600 text-white font-bold w-full")



                        # TH → ẩn khi đơn lý recall request (backend cũng block, nhưng ẩn cho UX)

                        if th_act and not leave.get("recall_reason") and api.has_feature("leaves.forward_th"):

                            def _th_forward_open(lv=leave, l=lid):
                                async def _do_forward(_l=l, _lv=lv):
                                    try:
                                        await asyncio.to_thread(api.post, f"/api/leaves/{_l}/tong-hop-review",
                                            {"action": "forward",
                                             "gd_approver_id": _lv.get("gd_approver_id"),
                                             "comment": None})
                                        detail_drawer.hide()
                                        ui.notify("Đã xác nhận & chuyển lên Ban lãnh đạo!", type="positive", timeout=3000)
                                        _nav_pending_th()
                                    except Exception as e:
                                        _handle_api_error(e)

                                # Chuyển cho PGĐ hết ủy quyền = đơn kẹt, chỉ Quản trị viên gỡ được.
                                # Không chặn (ủy quyền có thể được cấp sau) nhưng phải báo trước.
                                _warn = ("" if lv.get("gd_can_review", True) else
                                         " ⚠ Người duyệt là Phó Giám đốc nhưng giấy ủy quyền chưa/không còn "
                                         "hiệu lực hôm nay — chuyển lên bây giờ thì đơn sẽ đứng lại cho tới khi "
                                         "ủy quyền được gia hạn.")
                                _th_borrow = lv.get("borrow_next_year_days") or 0
                                if _th_borrow:
                                    _warn += (f" ⚠ Đơn này có sử dụng {_th_borrow:.0f} ngày phép "
                                              f"của {_borrow_year_label(lv)}.")
                                _ask_confirm(
                                    "Xác nhận phê duyệt",
                                    f"Xác nhận đơn của {lv.get('staff_name','')} và chuyển lên Ban lãnh đạo?{_warn}",
                                    _do_forward,
                                    ok_label="Xác nhận",
                                    ok_cls="bg-green-600"
                                )



                            def _th_reject_open(l=lid):

                                async def _cb(reason, _l=l):

                                    try:

                                        await asyncio.to_thread(api.post, f"/api/leaves/{_l}/tong-hop-review",

                                            {"action": "reject", "comment": reason})

                                        detail_drawer.hide()

                                        ui.notify("Đã từ chối đơn.", type="warning", timeout=3000)

                                        _nav_pending_th()

                                    except Exception as e:

                                        _handle_api_error(e)

                                _reject_cb[0] = _cb

                                reject_dialog.open()



                            ui.button("Phê duyệt", icon="check_circle",
                                      on_click=lambda lv=leave, l=lid: _th_forward_open(lv, l)).classes("bg-green-600 text-white font-bold w-full")

                            ui.button("Từ chối", icon="cancel", on_click=_th_reject_open).classes("bg-red-600 text-white font-bold w-full")



                        # GĐ

                        if gd_act and api.has_feature("leaves.approve_gd"):

                            async def _gd_approve(lv=leave, l=lid):

                                async def _do(payload, _l=l):

                                    try:

                                        await asyncio.to_thread(api.put, f"/api/leaves/{_l}/gd-review", payload)

                                        detail_drawer.hide()

                                        ui.notify("Phê duyệt Ban lãnh đạo thành công!", type="positive", timeout=3000)

                                        _nav_pending()

                                    except Exception as e:

                                        _handle_api_error(e)

                                async def _run(_l=l):
                                    await _sign_then_approve(_l, "gd", f"/api/leaves/{_l}/preview",
                                                             "Xác nhận phê duyệt", _do)
                                await _borrow_confirm_or_run(lv, _run)



                            def _gd_reject_open(l=lid):

                                async def _cb(reason, _l=l):

                                    try:

                                        await asyncio.to_thread(api.put, f"/api/leaves/{_l}/gd-review",

                                            {"action": "reject", "comment": reason})

                                        detail_drawer.hide()

                                        ui.notify("Đã từ chối đơn.", type="warning", timeout=3000)

                                        _nav_pending()

                                    except Exception as e:

                                        _handle_api_error(e)

                                _reject_cb[0] = _cb

                                reject_dialog.open()



                            ui.button("Phê duyệt", icon="check_circle", on_click=_gd_approve).classes("bg-green-600 text-white font-bold w-full")

                            ui.button("Từ chối", icon="cancel", on_click=_gd_reject_open).classes("bg-red-600 text-white font-bold w-full")



                        # Resubmit / Điều chỉnh NPBB — dùng chung 1 dialog, khác nhau ở
                        # tiêu đề, khả năng đổi loại nghỉ phép và endpoint gọi lúc submit
                        # (xem _rsub_mode, do_resubmit).
                        async def _load_resubmit_fields(lv, title="Chỉnh sửa & Nộp lại",
                                                        lock_type=False, mode="resubmit"):

                            resubmit_title.set_text(title)
                            _rsub_mode[0] = mode
                            resubmit_submit_btn.set_text("Tạo đơn điều chỉnh" if mode == "npbb_adjust" else "Nộp lại")

                            _spread = lv.get("spread_dates")

                            if _spread:
                                r_dates.value = _spread
                            else:
                                # Đơn cũ là khoảng liên tục (vd thai sản/bảo hiểm) — phải nạp
                                # ĐỦ mọi ngày từ start_date đến end_date vào picker "multiple",
                                # nếu không chỉ giữ lại ngày đầu, mất hết các ngày còn lại.
                                _s = (lv.get("start_date") or "")[:10]
                                _e = (lv.get("end_date") or "")[:10]
                                try:
                                    _sd = _dt_mod.date.fromisoformat(_s)
                                    _ed = _dt_mod.date.fromisoformat(_e) if _e else _sd
                                    _all_days, _d = [], _sd
                                    while _d <= _ed:
                                        _all_days.append(_d.isoformat())
                                        _d += _dt_mod.timedelta(days=1)
                                    r_dates.value = _all_days
                                except ValueError:
                                    r_dates.value = [_s] if _s else []

                            r_type.value   = lv.get("leave_type", "annual")
                            r_type.set_enabled(not lock_type)

                            r_reason.value = lv.get("reason") or ""

                            _rsub_id[0]    = lv["id"]

                            if r_approver:
                                r_approver.value = lv.get("ksv_approver_id")

                            # Load danh sách GĐ/PGĐ mỗi lần mở dialog
                            try:
                                lst = await asyncio.to_thread(api.get, "/api/leaves/gd-list")
                                r_gd_select.options = {
                                    s["id"]: f"{s['full_name']} ({s.get('role_label', '')})"
                                    for s in (lst or [])
                                }
                                r_gd_select.update()
                            except Exception:
                                pass

                            r_gd_select.value = lv.get("gd_approver_id")

                            resubmit_dialog.open()

                        if is_owner and status == "rejected" and api.has_feature("leaves.resubmit"):

                            async def _open_resubmit(lv=leave):
                                await _load_resubmit_fields(lv, "Chỉnh sửa & Nộp lại")

                            ui.button("Sửa & Nộp lại", icon="refresh", on_click=_open_resubmit).classes("bg-orange-500 text-white text-sm")

                        # Điều chỉnh ngày NPBB — chỉ đơn bat_buoc đã "Hoàn thành", tạo
                        # đơn MỚI liên kết qua adjusts_leave_id (POST /npbb-adjust), KHÔNG
                        # ghi đè đơn gốc — xem npbb_adjust_leave() ở backend. Ẩn nếu đã có
                        # đơn điều chỉnh đang xử lý (chưa bị từ chối/hủy).
                        _pending_adj = leave.get("npbb_adjustment")
                        _has_active_adj = bool(_pending_adj) and _pending_adj.get("status") not in ("rejected", "cancelled")
                        if (is_owner and status == "approved" and leave.get("leave_type") == "bat_buoc"
                                and not _has_active_adj and api.has_feature("leaves.create")):

                            async def _open_npbb_adjust(lv=leave):
                                await _load_resubmit_fields(lv, "Điều chỉnh ngày nghỉ phép bắt buộc",
                                                            lock_type=True, mode="npbb_adjust")

                            ui.button("Điều chỉnh ngày NPBB", icon="edit_calendar", on_click=_open_npbb_adjust).classes("bg-orange-500 text-white text-sm")

                        # Hủy đơn bị từ chối (không resubmit nữa)
                        if is_owner and status == "rejected":
                            async def _cancel_rejected(l=lid):
                                async def _do_cancel(_l=l):
                                    try:
                                        await asyncio.to_thread(api.patch, f"/api/leaves/{_l}/cancel", {})
                                        detail_drawer.hide()
                                        ui.notify("Đã hủy đơn thành công", type="positive")
                                        # Quay lại đúng tab đang đứng (không ép về "Chờ duyệt")
                                        app.storage.user["_leaves_goto_raw"] = leave_tabs.value
                                        ui.navigate.to("/leaves")
                                    except Exception as e:
                                        _handle_api_error(e)
                                _ask_confirm("Xác nhận hủy đơn",
                                             "Bạn có chắc muốn hủy đơn nghỉ này không?",
                                             _do_cancel,
                                             ok_label="Hủy đơn",
                                             ok_cls="bg-gray-600")
                            ui.button("Hủy đơn", icon="delete_forever", on_click=_cancel_rejected).classes("bg-gray-500 text-white text-sm")

                        # Hủy
                        # GĐ có toàn quyền huỷ đơn của chính mình bất cứ lúc nào — luôn hiện nút
                        # dù feature "leaves.cancel" chưa được cấp qua cấu hình phân quyền.
                        _can_cancel_now = (is_owner or user_role == "admin") and status not in ("cancelled", "rejected") \
                                and (api.has_feature("leaves.cancel") or (is_owner and user_role == "giam_doc"))
                        if _can_cancel_now:

                            def _cancel_open(l=lid, cur_status=status):
                                async def _do_cancel(_l=l, _st=cur_status):
                                    try:
                                        await asyncio.to_thread(api.patch, f"/api/leaves/{_l}/cancel", {})
                                        detail_drawer.hide()
                                        ui.notify("Đã hủy đơn thành công", type="warning")
                                        # Quay lại đúng tab đang đứng — không ép theo trạng thái đơn
                                        # (trước đây pending_tong_hop luôn nhảy sang "Chờ xác nhận TT"
                                        # dù đang xem từ Dashboard hay tab khác).
                                        app.storage.user["_leaves_goto_raw"] = leave_tabs.value
                                        ui.navigate.to("/leaves")
                                    except Exception as e:
                                        _handle_api_error(e)
                                _ask_confirm("Xác nhận hủy đơn",
                                             "Bạn có chắc muốn hủy đơn nghỉ này không?",
                                             _do_cancel, ok_label="Hủy đơn", ok_cls="bg-gray-600")

                            ui.button("Hủy đơn", icon="cancel", on_click=_cancel_open).classes("bg-gray-200 text-gray-700 text-sm")



                        # Rút đơn (recall) → chủ nhân yêu cầu rút đơn đã duyệt.
                        # Nếu đã có nút "Hủy đơn" (tự xử lý ngay) thì không cần thêm bước này nữa
                        # vì kết quả giống nhau (đơn chuyển sang cancelled).

                        has_recall = api.has_feature("leaves.recall")

                        if is_owner and status == "approved" and not leave.get("recall_reason") \
                                and has_recall and not _can_cancel_now:

                            def _open_recall(l=lid):

                                async def _cb(reason, _l=l):

                                    try:

                                        await asyncio.to_thread(api.post, f"/api/leaves/{_l}/recall", {"reason": reason})

                                        detail_drawer.hide()

                                        ui.notify("Đã gửi yêu cầu rút → chờ Phòng Tổng hợp xác nhận", type="info")

                                        ui.navigate.to("/leaves")

                                    except Exception as e:

                                        _handle_api_error(e)

                                _reject_cb[0] = _cb

                                reject_dialog.open()



                            ui.button("Rút đơn", icon="undo", on_click=_open_recall).classes("bg-orange-100 text-orange-800 text-sm")



                        # Xác nhận rút đơn → TH xác nhận khi đơn ở pending_tong_hop và recall

                        if th_act and leave.get("recall_reason") and has_recall:

                            async def _confirm_recall(l=lid):

                                try:

                                    await asyncio.to_thread(api.put, f"/api/leaves/{l}/recall-approve")

                                    detail_drawer.hide()

                                    ui.notify("Đã xác nhận rút đơn", type="positive")

                                    ui.navigate.to("/leaves")

                                except Exception as e:

                                    _handle_api_error(e)



                            ui.button("Xác nhận rút đơn", icon="undo", on_click=_confirm_recall).classes("bg-orange-700 text-white text-sm")



            detail_drawer.show()



        # ── Hôm mở dialog lịch sử ────────────────────────────────────────────

        async def open_history(leave: dict):

            history_container.clear()

            with history_container:

                with ui.row().classes("w-full bg-gray-800 text-white px-5 py-3 items-center gap-2"):

                    ui.icon("history").classes("text-xl")

                    with ui.column().classes("gap-0"):

                        ui.label("Lịch sử thao tác").classes("font-bold text-base")

                        ui.label(leave.get("staff_name", "")).classes("text-gray-300 text-sm")

                _load_error = False

                try:

                    logs = await asyncio.to_thread(api.get, f"/api/leaves/{leave['id']}/history")

                except Exception:

                    logs = []
                    _load_error = True

                if _load_error:

                    with ui.column().classes("p-6"):

                        ui.label("Không tải được lịch sử — vui lòng thử lại.").classes("text-red-500 text-sm")

                elif not logs:

                    with ui.column().classes("p-6"):

                        ui.label("Chưa có lịch sử thao tác.").classes("text-gray-500 text-sm")

                else:

                    _COLOR = {"green": "bg-green-100 text-green-700", "red": "bg-red-100 text-red-700",

                              "blue": "bg-blue-100 text-blue-700", "orange": "bg-orange-100 text-orange-700",

                              "grey": "bg-gray-100 text-gray-500"}

                    with ui.column().classes("px-5 py-4 gap-3 w-full"):

                        for log in logs:

                            cls = _COLOR.get(log.get("action_color", "grey"), "bg-gray-100 text-gray-500")

                            with ui.row().classes("w-full items-start gap-3 border-b border-gray-100 pb-3"):

                                with ui.column().classes("flex-1 gap-1"):

                                    with ui.row().classes("items-center gap-2"):

                                        ui.label(log.get("action_label", log.get("action", ""))).classes(

                                            f"text-xs font-medium px-2 py-0.5 rounded {cls}")

                                        ui.label(log.get("actor_name", "")).classes("text-sm font-medium")

                                    if log.get("comment"):

                                        ui.label(f"Lý do: {log['comment']}").classes("text-xs text-gray-500")

                                    ts = log.get("created_at", "")

                                    if ts:

                                        ui.label(ts[:16].replace("T", " ")).classes("text-xs text-gray-500")

            history_dialog.open()



        # ── Tracking selection ────────────────────────────────────────────────

        _sel: set = set()         # cho approve/reject

        _export_sel: set = set()  # cho xuất Excel leaves (dashboard / khai báo hộ)

        _quota_sel:  set = set()  # cho xuất Excel hạn mức phép

        # Mọi checkbox từng vẽ ra (gắn với _sel hoặc _export_sel, ở bất kỳ bảng
        # nào — Dashboard/Chờ duyệt/Phòng tôi/Của tôi/Khai báo hộ) — để
        # _on_leave_tab_change có thể bỏ tick TRỰC QUAN khi đổi tab. Từ khi bỏ
        # full-reload lúc đổi tab, các checkbox này không tự vẽ lại nữa nên vẫn
        # hiện đang tick dù _sel/_export_sel đã bị xoá — dễ hiểu lầm "đã chọn"
        # trong khi thực ra rỗng (hoặc ngược lại, Xuất Excel/Phê duyệt lặng lẽ
        # dùng nhầm phạm vi khác vì tưởng chưa chọn gì).
        _all_sel_checkboxes: list = []

        _approve_btn: list = []

        _reject_btn:  list = []



        def _upd_btns():

            en = bool(_sel)

            for b in _approve_btn:

                b.set_enabled(en)

            for b in _reject_btn:

                b.set_enabled(en)



        # ── Bulk actions ──────────────────────────────────────────────────────

        async def _bulk_approve():

            # Bảng ở tab Dashboard/Báo cáo chỉ tick vào _export_sel (dùng cho Xuất
            # Excel), không phải _sel (dùng cho Phê duyệt/Từ chối) — dự phòng bằng
            # _export_sel giống hệt cách Xuất Excel đã làm (xem _active_export_ids
            # bên dưới), tránh bấm Phê duyệt/Từ chối ở đó mà im lặng không làm gì.
            ids = list(_sel) if _sel else list(_export_sel)

            if not ids:

                ui.notify("Vui lòng tick chọn đơn cần phê duyệt", type="warning")

                return

            _bulk_lv_map = {lv["id"]: lv for lv in pending_leaves}



            async def _do_bulk(_ids=ids):

                lv_map   = {lv["id"]: lv for lv in pending_leaves}

                th_ids   = [i for i in _ids if lv_map.get(i, {}).get("status") == "pending_tong_hop"]

                other_ids = [i for i in _ids if i not in th_ids]

                ok_count = 0

                for i in other_ids:

                    st = lv_map.get(i, {}).get("status", "")

                    try:

                        if st == "pending_ksv":

                            await asyncio.to_thread(api.put, f"/api/leaves/{i}/ksv-review", {"action": "approve"})

                        elif st == "pending_gd":

                            await asyncio.to_thread(api.put, f"/api/leaves/{i}/gd-review", {"action": "approve"})

                        else:

                            continue

                        ok_count += 1

                    except Exception:

                        pass



                if th_ids:
                    # TH bulk: dùng gd_approver_id sẵn có trong từng đơn
                    for i in th_ids:
                        lv_data = lv_map.get(i, {})
                        try:
                            await asyncio.to_thread(api.post, f"/api/leaves/{i}/tong-hop-review",
                                {"action": "forward",
                                 "gd_approver_id": lv_data.get("gd_approver_id"),
                                 "comment": None})
                            ok_count += 1
                        except Exception:
                            pass

                _sel.clear()
                _export_sel.clear()
                fail_count = len(_ids) - ok_count
                if fail_count:
                    ui.notify(f"Phê duyệt {ok_count}/{len(_ids)} đơn — {fail_count} đơn lỗi (có thể đã bị xử lý trước đó), vui lòng kiểm tra lại.",
                               type="warning", timeout=5000)
                else:
                    ui.notify(f"Đã phê duyệt {ok_count} đơn thành công!", type="positive", timeout=3000)
                # _nav_pending()/_nav_pending_th() giờ đều "ở nguyên tab đang đứng"
                # (giống hệt nhau) — không còn cần phân nhánh theo th_ids nữa.
                _nav_pending()



            _borrow_ids = [i for i in ids if (_bulk_lv_map.get(i, {}).get("borrow_next_year_days") or 0) > 0]
            _bulk_msg = f"Bạn có chắc chắn muốn phê duyệt {len(ids)} đơn đã chọn?"
            if _borrow_ids:
                _lines = []
                for i in _borrow_ids:
                    _lv = _bulk_lv_map.get(i, {})
                    _lines.append(f"{_lv.get('staff_name', '')} ({_lv.get('department_name', '')}) — "
                                  f"{_borrow_year_label(_lv)}")
                _bulk_msg += (f" ⚠ Trong đó có {len(_borrow_ids)} đơn sử dụng ngày phép của năm sau: "
                              + "; ".join(_lines))

            _ask_confirm("Xác nhận phê duyệt",

                         _bulk_msg,

                         _do_bulk, "Phê duyệt", "bg-green-600")



        async def _bulk_reject_open():

            # Xem chú thích tương tự ở _bulk_approve — dự phòng bằng _export_sel.
            ids = list(_sel) if _sel else list(_export_sel)

            if not ids:

                ui.notify("Vui lòng tick chọn đơn cần từ chối", type="warning")

                return

            lv_map = {lv["id"]: lv for lv in pending_leaves}

            async def _cb(reason):

                ok_count = 0

                for i in ids:

                    st = lv_map.get(i, {}).get("status", "")

                    try:

                        if st == "pending_ksv":

                            await asyncio.to_thread(api.put, f"/api/leaves/{i}/ksv-review",

                                {"action": "reject", "comment": reason})

                        elif st == "pending_tong_hop":

                            await asyncio.to_thread(api.post, f"/api/leaves/{i}/tong-hop-review",

                                {"action": "reject", "comment": reason})

                        elif st == "pending_gd":

                            await asyncio.to_thread(api.put, f"/api/leaves/{i}/gd-review",

                                {"action": "reject", "comment": reason})

                        else:

                            continue

                        ok_count += 1

                    except Exception:

                        pass

                _sel.clear()

                _export_sel.clear()

                fail_count = len(ids) - ok_count

                if fail_count:

                    ui.notify(f"Từ chối {ok_count}/{len(ids)} đơn — {fail_count} đơn lỗi (có thể đã bị xử lý trước đó), vui lòng kiểm tra lại.",
                               type="warning", timeout=5000)

                else:

                    ui.notify(f"Đã từ chối {ok_count} đơn.", type="warning", timeout=3000)

                # _nav_pending()/_nav_pending_th() giờ đều "ở nguyên tab đang đứng"
                # (giống hệt nhau) — không còn cần phân nhánh theo trạng thái đơn nữa.
                _nav_pending()

            _reject_cb[0] = _cb

            reject_dialog.open()



        # ── Toolbar ───────────────────────────────────────────────────────────

        _has_any_approve = (
            (user_role not in ("chuyen_vien",) or can_forward_th)
            and any(api.has_feature(f) for f in (
                "leaves.approve_ksv", "leaves.forward_th", "leaves.approve_gd"
            ))
        )

        with ui.row().classes("gap-2 mb-4 items-center flex-wrap"):

            create_btn = ui.button("Tạo đơn", icon="add", on_click=_c_open).classes("bg-red-700 text-white text-base")

            # Không hardcode role — phân quyền hoàn toàn theo menu "Phân quyền theo nhóm".
            create_btn.set_visibility(api.has_feature("leaves.create"))

            ab = ui.button("Phê duyệt", icon="check_circle",

                           on_click=lambda: asyncio.ensure_future(_bulk_approve())).classes(

                "bg-green-600 text-white")

            ab.set_visibility(_has_any_approve)

            rb = ui.button("Từ chối", icon="cancel",

                           on_click=lambda: asyncio.ensure_future(_bulk_reject_open())).classes(

                "bg-red-600 text-white")

            rb.set_visibility(_has_any_approve)



            def _make_fname(base: str, from_val: str = "", to_val: str = "") -> str:

                """T→n file: base + khoảng lĐọc (nếu c→) + ngày xuất hôm nay."""

                import datetime as _dt_fname

                today = _dt_fname.date.today().strftime("%d%m%Y")

                f = (from_val or "").strip().replace("/", "")

                t = (to_val   or "").strip().replace("/", "")

                if f and t:

                    return f"{base}_{f}-{t}_xuat{today}.xlsx"

                elif f:

                    return f"{base}_tu{f}_xuat{today}.xlsx"

                elif t:

                    return f"{base}_den{t}_xuat{today}.xlsx"

                return f"{base}_xuat{today}.xlsx"



            def _tab_match(tab, cur):

                """So s→nh tab đang active với tab object.

                NiceGUI trả string (props['name']) từ leave_tabs.value."""

                if tab is None:

                    return False

                if cur is tab:

                    return True

                # NiceGUI lưu label/name trong _props

                props = getattr(tab, "_props", {})

                tab_name = props.get("name") or props.get("label") or getattr(tab, "text", None)

                return cur == tab_name



            async def _export_leaves():

                try:

                    cur = leave_tabs.value

                    import datetime as _dtt

                    today = _dtt.date.today().strftime("%d%m%Y")

                    # ── Hạn mức phép ──────────────────────────────────────────

                    if _tab_match(t_quota, cur):

                        yr  = q_year_sel.value

                        ids_str = ",".join(str(i) for i in sorted(_quota_sel)) if _quota_sel else ""

                        fname = (f"han_muc_phep_{yr}_da_chon_xuat{today}.xlsx"

                                 if ids_str else f"han_muc_phep_{yr}_xuat{today}.xlsx")

                        params = {"ids": ids_str} if ids_str else {}

                        content = await asyncio.to_thread(

                            api.download, f"/api/leaves/quotas/{yr}/export", params=params

                        )

                        ui.download(content, fname)

                        return

                    # ── C→c tab nghỉ phép ──────────────────────────────────────

                    # Tab Báo cáo tổng hợp → xuất tất cả đơn trong năm
                    if t_stats and _tab_match(t_stats, cur):
                        from datetime import date as _d_stats
                        _yr_stats = _d_stats.today().year
                        fname = f"bao_cao_tat_ca_don_nghi_phep_{_yr_stats}.xlsx"
                        content = await asyncio.to_thread(
                            api.download, "/api/leaves/export/annual",
                            params={"year": _yr_stats}
                        )
                        ui.download(content, fname)
                        return

                    # Dùng _export_sel (từ bảng export_sel) hoặc _sel (từ bảng phê duyệt) nếu có tick
                    # Không áp dụng _sel nếu đang ở tab không liên quan đến đơn phép
                    _active_export_ids = _export_sel if _export_sel else (_sel if _sel else set())

                    if _active_export_ids:

                        ids_str = ",".join(str(i) for i in sorted(_active_export_ids))

                        if _tab_match(t_direct, cur):

                            fv, tv = getattr(_df_from, "value", ""), getattr(_df_to, "value", "")

                            fname = _make_fname("don_khai_bao_ho_da_chon", fv, tv)

                        else:

                            fv, tv = ((_f_from.value or "") if _f_from else ""), ((_f_to.value or "") if _f_to else "")

                            fname = _make_fname("don_nghi_phep_da_chon", fv, tv)

                        content = await asyncio.to_thread(

                            api.download, "/api/leaves/export",

                            params={"scope": "all", "ids": ids_str},

                        )

                        ui.download(content, fname)

                        return

                    # Không có tick → xuất theo tab + khoảng ngày filter

                    def _dmy_to_iso(s):
                        """DD/MM/YYYY → YYYY-MM-DD (rỗng nếu không hợp lệ)."""
                        if not s or "/" not in s:
                            return ""
                        try:
                            d, m, y = s.split("/")
                            return f"{y}-{m}-{d}"
                        except Exception:
                            return ""

                    _dp: dict = {}

                    if t_pending_th and _tab_match(t_pending_th, cur):
                        # Tab "Chờ xác nhận TT": chỉ xuất pending_tong_hop
                        if not _pending_th_list:
                            ui.notify("Không có đơn nào để xuất", type="warning")
                            return
                        th_ids_str = ",".join(str(lv["id"]) for lv in _pending_th_list)
                        fname = _make_fname("don_cho_xac_nhan_tt")
                        content = await asyncio.to_thread(
                            api.download, "/api/leaves/export",
                            params={"scope": "all", "ids": th_ids_str},
                        )
                        ui.download(content, fname)
                        return

                    elif _tab_match(t_pending, cur):

                        if _is_dual_role:
                            # Dual role: tab "Chờ duyệt" chỉ hiện đơn KSV phòng mình
                            # (pending_tong_hop đã có tab "Chờ xác nhận TT" riêng) —
                            # export phải khớp đúng danh sách đang hiển thị, không
                            # dùng scope="pending" (backend gộp cả 2 loại cho dual role).
                            if not _pending_ksv_list:
                                ui.notify("Không có đơn nào để xuất", type="warning")
                                return
                            ksv_ids_str = ",".join(str(lv["id"]) for lv in _pending_ksv_list)
                            fname = _make_fname("don_cho_duyet")
                            content = await asyncio.to_thread(
                                api.download, "/api/leaves/export",
                                params={"scope": "all", "ids": ksv_ids_str},
                            )
                            ui.download(content, fname)
                            return

                        scp  = "pending"

                        fname = _make_fname("don_cho_duyet")

                    elif _tab_match(t_dept, cur):

                        scp  = "dept"

                        fname = _make_fname("don_phong_toi")

                    elif _tab_match(t_mine, cur):

                        scp  = "mine"

                        fname = _make_fname("don_cua_toi")

                    elif _tab_match(t_direct, cur):

                        scp  = "declared"

                        fv, tv = getattr(_df_from, "value", ""), getattr(_df_to, "value", "")

                        fname = _make_fname("don_khai_bao_ho", fv, tv)

                        _dp = {"date_from": _dmy_to_iso(fv), "date_to": _dmy_to_iso(tv)}

                    elif _tab_match(t_dashboard, cur):

                        scp  = "all" if can_all else "mine"

                        fv, tv = ((_f_from.value or "") if _f_from else ""), ((_f_to.value or "") if _f_to else "")

                        fname = _make_fname("tat_ca_don_nghi_phep", fv, tv)

                        _dp = {"date_from": _dmy_to_iso(fv), "date_to": _dmy_to_iso(tv)}

                    else:

                        scp  = "all" if can_all else "mine"

                        fname = _make_fname("danh_sach_nghi_phep")

                    content = await asyncio.to_thread(

                        api.download, "/api/leaves/export", params={"scope": scp, **_dp},

                    )

                    ui.download(content, fname)

                except Exception as e:

                    _handle_api_error(e)



            ui.button("Xuất Excel", icon="download",

                      on_click=_export_leaves).classes("bg-blue-700 text-white").tooltip("Xuất Excel theo tab đang xem")



        # ── H→m vẽ bảng ──────────────────────────────────────────────────────

        _PAGE_SIZE = 50

        def _draw_table_paged(leaves: list, show_name: bool = False, show_checkbox: bool = True,
                              export_sel: set = None):
            """Wrapper thêm pagination 50 dòng/trang cho _draw_table."""
            total = len(leaves)
            total_pages = max(1, (total + _PAGE_SIZE - 1) // _PAGE_SIZE)
            state = {"page": 1}
            body = ui.column().classes("w-full gap-0")

            def _render(p=None):
                if p is not None:
                    state["page"] = max(1, min(p, total_pages))
                pg = state["page"]
                body.clear()
                with body:
                    _draw_table(
                        leaves[(pg-1)*_PAGE_SIZE : pg*_PAGE_SIZE],
                        show_name=show_name, show_checkbox=show_checkbox, export_sel=export_sel,
                        _row_offset=(pg-1)*_PAGE_SIZE
                    )

            _render()

            if True:
                with ui.row().classes("w-full justify-center items-center gap-2 mt-3"):
                    _pg_lbl = ui.label(f"Trang {state['page']} / {total_pages}   ({total} đơn)").classes("text-xs text-gray-500 px-2")

                    def _goto(p):
                        _render(p)
                        _pg_lbl.set_text(f"Trang {state['page']} / {total_pages}   ({total} đơn)")

                    ui.button("«", on_click=lambda: _goto(1)).props("flat dense").classes("text-gray-600")
                    ui.button("‹", on_click=lambda: _goto(state["page"]-1)).props("flat dense").classes("text-gray-600")
                    ui.button("›", on_click=lambda: _goto(state["page"]+1)).props("flat dense").classes("text-gray-600")
                    ui.button("»", on_click=lambda: _goto(total_pages)).props("flat dense").classes("text-gray-600")
                    def _go_page(e):
                        try:
                            _goto(int(e.value))
                        except Exception:
                            pass
                    ui.input("Đến trang", on_change=_go_page).props("dense outlined").classes("w-20 text-xs")

        def _draw_table(leaves: list, show_name: bool = False, show_checkbox: bool = True,
                        export_sel: set = None, _row_offset: int = 0):

            # CSS border cho cột khi không có checkbox (dashboard view)

            _col_cls  = "text-xs shrink-0 border-r border-gray-400 pr-2 mr-1"

            _hdr_cls  = "font-semibold text-red-800 text-xs shrink-0 border-r border-red-400 pr-2 mr-1"

            with ui.column().classes("w-full gap-0 border-2 border-gray-400 rounded"):

                # Header

                with ui.row().classes("w-full bg-red-50 border-b-2 border-red-400 px-3 py-2 items-center gap-0"):

                    if show_checkbox or export_sel is not None:
                        _all_ids = [lv["id"] for lv in leaves]
                        _row_cks: list = []  # references tới từng checkbox hàng

                        def _select_all(e, _row_refs=_row_cks, _ids=_all_ids):
                            for ck in _row_refs:
                                ck.set_value(e.value)
                            if e.value:
                                _sel.update(_ids)
                            else:
                                for i in _ids: _sel.discard(i)
                            _upd_btns()

                        def _select_all_exp(e, _row_refs=_row_cks, _ids=_all_ids, _s=export_sel):
                            for ck in _row_refs:
                                ck.set_value(e.value)
                            if e.value:
                                _s.update(_ids)
                            else:
                                for i in _ids: _s.discard(i)

                        if show_checkbox:
                            _all_sel_checkboxes.append(
                                ui.checkbox(value=False, on_change=_select_all).props("dense").classes("w-6 shrink-0 mr-2").tooltip("Chọn / Bỏ chọn tất cả")
                            )
                        elif export_sel is not None:
                            _all_sel_checkboxes.append(
                                ui.checkbox(value=False, on_change=_select_all_exp).props("dense").classes("w-6 shrink-0 mr-2").tooltip("Chọn / Bỏ chọn tất cả")
                            )

                    ui.label("STT").classes(f"{_hdr_cls} w-8 text-center")

                    ui.label("Ngày tạo").classes(f"{_hdr_cls} w-20")

                    ui.label("Loại").classes(f"{_hdr_cls} w-28")

                    ui.label("Trạng thái").classes(f"{_hdr_cls} w-28")

                    ui.label("Loại đơn").classes(f"{_hdr_cls} w-24")

                    if show_name:

                        ui.label("Họ và tên").classes(f"{_hdr_cls} w-28")

                    ui.label("Phòng").classes(f"{_hdr_cls} w-32")

                    ui.label("Ngày nghỉ").classes(f"{_hdr_cls} w-36")

                    ui.label("KSV xác nhận").classes(f"{_hdr_cls} w-28")

                    ui.label("Phòng TH xác nhận").classes(f"{_hdr_cls} w-32")

                    ui.label("Ban lãnh đạo xác nhận").classes("font-semibold text-red-800 text-xs flex-1")

                    ui.label("").classes("w-16 shrink-0")

                if not leaves:
                    with ui.row().classes("w-full bg-white px-3 py-4 justify-center"):
                        ui.label("Không có đơn nghỉ phép nào.").classes("text-gray-400 text-sm italic")

                for _row_idx, lv in enumerate(leaves, _row_offset + 1):

                    sg_lbl, sg_cls = _STATUS_GROUP.get(lv["status"], (lv["status"], "bg-gray-100 text-gray-500"))
                    # Đơn NPBB gốc đã bị đơn điều chỉnh thay thế — nhãn riêng thay nhãn
                    # chung chung, xem status_label ở backend (_leave_to_out).
                    if lv.get("status_label"):
                        sg_lbl = lv["status_label"]

                    # Highlight đỏ nhạt nếu dòng này cần user hiện tại xử lý
                    _needs_action = (
                        (lv.get("status") == "rejected" and lv.get("staff_id") == user_id)
                        or (lv.get("status") == "pending_ksv"      and user_role in ("truong_phong", "pho_phong") and lv.get("ksv_approver_id") == user_id)
                        or (lv.get("status") == "pending_tong_hop" and (user_role not in ("chuyen_vien",) or can_forward_th) and lv.get("tong_hop_approver_id") == user_id)
                        or (lv.get("status") == "pending_tong_hop" and (user_role not in ("chuyen_vien",) or can_forward_th) and not lv.get("tong_hop_approver_id"))
                        or (lv.get("status") == "pending_gd"      and user_role in ("giam_doc", "pho_giam_doc") and lv.get("gd_approver_id") == user_id)
                    )
                    _row_bg = "bg-red-50 border-red-300" if _needs_action else "bg-white border-gray-300"

                    with ui.row().classes(f"w-full {_row_bg} border-b border-gray-300 px-3 py-1.5 items-center gap-0 hover:bg-red-100"):

                        if show_checkbox:

                            def _on_ck(e, l=lv["id"]):

                                _sel.add(l) if e.value else _sel.discard(l)

                                _upd_btns()

                            _ck = ui.checkbox(value=False, on_change=_on_ck).props("dense").classes("w-6 shrink-0 mr-2")
                            _row_cks.append(_ck)
                            _all_sel_checkboxes.append(_ck)

                        elif export_sel is not None:

                            def _on_exp_ck(e, l=lv["id"], _s=export_sel):

                                _s.add(l) if e.value else _s.discard(l)

                            _ck = ui.checkbox(value=False, on_change=_on_exp_ck).props("dense").classes("w-6 shrink-0 mr-2")
                            _row_cks.append(_ck)
                            _all_sel_checkboxes.append(_ck)



                        ui.label(str(_row_idx)).classes("text-xs w-8 shrink-0 text-center text-gray-500 border-r border-gray-400 pr-2 mr-1")

                        ui.label((lv.get("created_at") or "")[:10]).classes("text-xs w-20 shrink-0 border-r border-gray-400 pr-2 mr-1")

                        ui.label(_LEAVE_TYPE.get(lv.get("leave_type",""), lv.get("leave_type",""))).classes("text-xs w-28 shrink-0 truncate border-r border-gray-400 pr-2 mr-1")

                        with ui.column().classes("w-28 shrink-0 gap-0.5 border-r border-gray-400 pr-2 mr-1"):

                            ui.label(sg_lbl).classes(f"text-xs px-1.5 py-0.5 rounded {sg_cls} text-center")

                            if lv.get("rejected_step"):

                                _rs = lv["rejected_step"]

                                _rs_cls = {"KSV": "bg-orange-100 text-orange-700",

                                           "TH":  "bg-yellow-100 text-yellow-700",

                                           "GĐ":  "bg-blue-100 text-blue-700"}.get(_rs, "bg-gray-100 text-gray-600")

                                ui.label(f"Từ chối tại {_rs}").classes(f"text-[10px] px-1 py-0 rounded {_rs_cls} text-center")

                        # Cột Loại đơn
                        with ui.column().classes("w-24 shrink-0 gap-0.5 border-r border-gray-400 pr-2 mr-1 items-center justify-center"):

                            if lv.get("is_direct"):

                                ui.label("Khai báo hộ").classes("text-[10px] px-1.5 py-0.5 rounded bg-purple-100 text-purple-700 text-center font-semibold")

                            elif lv.get("is_resubmitted"):

                                ui.label("Gửi lại").classes("text-[10px] px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700 text-center font-semibold")

                            else:

                                ui.label("—").classes("text-xs text-gray-300 text-center")

                        if show_name:

                            ui.label(lv.get("staff_name", "")).classes("text-xs w-28 shrink-0 truncate border-r border-gray-400 pr-2 mr-1")

                        ui.label(lv.get("department_name") or "→").classes("text-xs w-32 shrink-0 truncate border-r border-gray-400 pr-2 mr-1")

                        ui.label(_fmt_leave_dates(lv.get("start_date",""), lv.get("end_date",""), lv.get("spread_dates"))).classes("text-xs w-36 shrink-0 border-r border-gray-400 pr-2 mr-1")

                        ui.label(lv.get("ksv_approver_name") or "→").classes("text-xs w-28 shrink-0 truncate border-r border-gray-400 pr-2 mr-1")

                        ui.label(lv.get("tong_hop_approver_name") or "→").classes("text-xs w-32 shrink-0 truncate border-r border-gray-400 pr-2 mr-1")

                        ui.label(_gd_display(lv) or "→").classes("text-xs flex-1 truncate")

                        with ui.row().classes("w-16 gap-0.5 justify-end shrink-0"):

                            ui.button(icon="info", on_click=lambda l=lv: asyncio.ensure_future(open_detail(l))).props(

                                "flat round dense size=sm").classes("text-blue-600").tooltip("Chi tiết")

                            ui.button(icon="history", on_click=lambda l=lv: asyncio.ensure_future(open_history(l))).props(

                                "flat round dense size=sm").classes("text-gray-500").tooltip("Lịch sử")



        # ── Tabs ──────────────────────────────────────────────────────────────

        with ui.tabs().classes("mb-4") as leave_tabs:

            _has_dash  = api.has_feature("leaves.dashboard")

            t_dashboard = ui.tab("Dashboard") if _has_dash else None

            # Nếu có Dashboard → gộp "Của tôi" và "Phòng tôi" vào Dashboard

            t_mine    = ui.tab("Của tôi") if not _has_dash else None

            # Hậu kiểm viên ngang chuyên viên ở quy trình nghỉ phép — không duyệt bước
            # nào, nên đừng dựng tab "Chờ duyệt" rỗng cho họ.
            _can_approve = user_role not in ("chuyen_vien", "hau_kiem_vien") or can_forward_th

            # Tách pending thành 2 danh sách: duyệt phòng (KSV) và xác nhận TT (TH)
            # Đơn của GĐ đã tự động approved cũng hiện ở đây để TH "xác nhận đã biết"
            # (thông báo, không phải điều kiện duyệt).
            _pending_ksv_list = [lv for lv in pending_leaves if lv.get("status") == "pending_ksv"]
            _pending_th_list  = [lv for lv in pending_leaves if lv.get("status") == "pending_tong_hop"
                                 or (lv.get("status") == "approved" and lv.get("staff_role") == "giam_doc"
                                     and not lv.get("tong_hop_approver_id"))]
            _is_dual_role     = api.has_feature("leaves.forward_th") and user_role in ("truong_phong", "pho_phong")

            # name= cố định tách khỏi label= động — leave_tabs.value chính là "name"
            # (Quasar QTabs v-model), nếu để label động làm luôn name thì mỗi lần số
            # lượng đơn đổi (sau khi duyệt/từ chối...) sẽ không so khớp lại được tab
            # đang đứng (_tab_match), khiến bị bật ngược về Dashboard.
            if _can_approve:
                if _is_dual_role:
                    # PP/TP Tổng hợp: 2 tab riêng
                    t_pending    = ui.tab(name="pending", label=f"Chờ duyệt ({len(_pending_ksv_list)})") if _pending_ksv_list or True else None
                    t_pending_th = ui.tab(name="pending_th", label=f"Chờ xác nhận TT ({len(_pending_th_list)})")
                else:
                    t_pending    = ui.tab(name="pending", label=f"Chờ duyệt ({len(pending_leaves)})")
                    t_pending_th = None
            else:
                t_pending    = None
                t_pending_th = None

            t_dept    = ui.tab(name="dept", label=f"Phòng tôi ({len(dept_leaves)})") if (can_dept and not _has_dash) else None

            t_declared = None  # gộp vào Dashboard

            # Lịch nghỉ phép gộp chung với quyền Tạo đơn — ai tạo được đơn thì xem được lịch,
            # không cần cấu hình phân quyền riêng.
            t_cal     = ui.tab("Lịch nghỉ phép")
            if not api.has_feature("leaves.create"):
                t_cal.set_visibility(False)

            t_deleg   = ui.tab("Ủy quyền GĐ") if can_delegation else None

            t_holiday = ui.tab("Ngày lễ") if can_holiday else None

            t_quota   = ui.tab("Hạn mức phép") if api.has_feature("leaves.quota_admin") else None

            t_stats   = ui.tab("Báo cáo tổng hợp") if api.has_feature("leaves.stats_export") else None

            t_direct  = ui.tab("Khai báo hộ") if api.has_feature("leaves.declare_direct") else None



        _goto     = app.storage.user.pop("_leaves_goto", None)
        _goto_raw = app.storage.user.pop("_leaves_goto_raw", None)

        if _goto == "khai_bao_ho" and t_direct:
            _default_tab = t_direct
        # Đổ chéo sang tab còn lại khi tab mong muốn không tồn tại với vai trò này:
        # sidebar chỉ biết trạng thái đơn, không biết người dùng có 2 tab hay 1.
        elif _goto == "pending" and (t_pending or t_pending_th):
            _default_tab = t_pending or t_pending_th
        elif _goto == "pending_th" and (t_pending_th or t_pending):
            _default_tab = t_pending_th or t_pending
        elif _goto_raw and any(
            _tab_match(_t, _goto_raw)
            for _t in (t_dashboard, t_mine, t_pending, t_pending_th, t_dept, t_direct, t_cal, t_quota, t_stats, t_deleg, t_holiday)
        ):
            _default_tab = next(
                _t for _t in (t_dashboard, t_mine, t_pending, t_pending_th, t_dept, t_direct, t_cal, t_quota, t_stats, t_deleg, t_holiday)
                if _tab_match(_t, _goto_raw)
            )
        else:
            _default_tab = t_dashboard if t_dashboard else (t_mine or t_pending or t_cal)

        # Nguyên tắc chung: mọi hành động (duyệt/từ chối/rút đơn/bulk...) xong đều ở
        # nguyên tab đang đứng, trừ khi người dùng tự bấm sang tab khác — không ép
        # về "Chờ duyệt"/"Chờ xác nhận TT" như trước nữa (kể cả khi thao tác từ
        # Dashboard hay bất kỳ tab nào khác).
        def _nav_pending():
            app.storage.user["_leaves_goto_raw"] = leave_tabs.value
            ui.navigate.to("/leaves")

        def _nav_pending_th():
            app.storage.user["_leaves_goto_raw"] = leave_tabs.value
            ui.navigate.to("/leaves")

        def _draw_pending_with_filter(src: list):
            """Bộ lọc inline cho tab Chờ duyệt / Chờ xác nhận TT."""
            from datetime import date as _d_cls
            _dept_opts = {"": "Tất cả phòng"}
            for lv in src:
                dn = lv.get("department_name") or lv.get("dept_name") or ""
                if dn and dn not in _dept_opts:
                    _dept_opts[dn] = dn

            with ui.card().classes("w-full p-3 mb-3 border border-gray-200 rounded-lg bg-gray-50"):
                with ui.row().classes("gap-3 flex-wrap items-end"):
                    _pf_name   = ui.input("Tìm theo tên").props("dense clearable outlined").classes("w-40")
                    _pf_dept   = ui.select(_dept_opts, value="", label="Phòng").props("dense outlined").classes("w-36") if len(_dept_opts) > 1 else None
                    with ui.input("Ngày nghỉ từ").props("dense clearable readonly outlined").classes("w-32") as _pf_from:
                        with _pf_from.add_slot("append"):
                            ui.icon("event").classes("cursor-pointer").on("click", lambda: _pf_cal_from.open())
                        with ui.menu() as _pf_cal_from:
                            ui.date(mask="DD/MM/YYYY").props(f'{_OPT_ALL} first-day-of-week="1"').bind_value(_pf_from)
                    with ui.input("đến ngày").props("dense clearable readonly outlined").classes("w-32") as _pf_to:
                        with _pf_to.add_slot("append"):
                            ui.icon("event").classes("cursor-pointer").on("click", lambda: _pf_cal_to.open())
                        with ui.menu() as _pf_cal_to:
                            ui.date(mask="DD/MM/YYYY").props(f'{_OPT_ALL} first-day-of-week="1"').bind_value(_pf_to)
                    # Buttons cùng hàng
                    _pf_search_btn = ui.button("Tìm kiếm", icon="search").classes("bg-red-700 text-white")
                    _pf_reset_btn  = ui.button("Xóa lọc", icon="clear").props("flat").classes("text-gray-500")

            _pf_body = ui.column().classes("w-full gap-0")

            def _pf_parse(s):
                if not s: return None
                try:
                    p = s.split("/")
                    return _d_cls(int(p[2]), int(p[1]), int(p[0])) if "/" in s else _d_cls.fromisoformat(s[:10])
                except Exception: return None

            def _pf_apply():
                nq = (_pf_name.value or "").strip().lower()
                dq = (_pf_dept.value or "") if _pf_dept else ""
                fd = _pf_parse(_pf_from.value)
                td = _pf_parse(_pf_to.value)
                filtered = []
                for lv in src:
                    if nq and nq not in (lv.get("staff_name") or "").lower(): continue
                    if dq and (lv.get("department_name") or lv.get("dept_name") or "") != dq: continue
                    if fd or td:
                        sd = lv.get("spread_dates")
                        dates = [d for d in (_pf_parse(x) for x in sd) if d] if sd else []
                        if dates:
                            if not any((not fd or d >= fd) and (not td or d <= td) for d in dates):
                                continue
                        else:
                            s = _pf_parse(lv.get("start_date", ""))
                            e = _pf_parse(lv.get("end_date", ""))
                            if s and e:
                                if fd and e < fd: continue
                                if td and s > td: continue
                    filtered.append(lv)
                # Bảng này show_checkbox=True mặc định (gắn với _sel, dùng cho Phê
                # duyệt/Từ chối) — lọc xong các dòng bị ẩn phải bỏ khỏi _sel, nếu
                # không Phê duyệt/Từ chối sau đó sẽ xử lý nhầm cả đơn không còn
                # hiển thị trên màn hình.
                _sel.clear()
                _pf_body.clear()
                with _pf_body:
                    _draw_table_paged(filtered, show_name=True)

            def _pf_reset():
                _sel.clear()
                _pf_name.value = ""
                if _pf_dept: _pf_dept.value = ""
                _pf_from.value = _pf_to.value = ""
                _pf_body.clear()
                with _pf_body:
                    _draw_table_paged(src, show_name=True)

            _pf_search_btn.on("click", lambda: _pf_apply())
            _pf_reset_btn.on("click", lambda: _pf_reset())
            _pf_name.on("keydown.enter", lambda _: _pf_apply())

            with _pf_body:
                _draw_table_paged(src, show_name=True)

        # Mọi panel đều đã được build + nạp dữ liệu (await) ngay trong lượt dựng
        # trang này (xem _load_dashboard/_reload_cal/_reload_holidays/_reload_quota
        # bên dưới), nên chuyển tab chỉ đơn thuần là Quasar ẩn/hiện panel đã có sẵn
        # ở client — KHÔNG cần (và trước đây gây trắng màn hình vì) reload lại cả
        # trang qua ui.navigate.to("/leaves"). Dữ liệu vẫn được làm mới bình thường
        # mỗi khi có hành động duyệt/từ chối/... (các chỗ đó tự gọi lại reload riêng).
        def _on_leave_tab_change():
            _sel.clear()
            # _export_sel dùng chung cho mọi bảng (Dashboard/Chờ duyệt/Của tôi/Khai báo
            # hộ...) và là nguồn dự phòng cho Phê duyệt/Từ chối khi _sel rỗng (xem
            # _bulk_approve) — nếu không xoá theo tab, tick chọn ở tab này rồi bấm
            # Phê duyệt/Từ chối ở tab khác (không tick gì) sẽ âm thầm tác động lên lựa
            # chọn cũ không còn hiển thị trên màn hình.
            _export_sel.clear()
            # Trước đây đổi tab = reload cả trang nên checkbox tự về trạng thái
            # chưa tick. Giờ trang không reload nữa — checkbox vẫn hiện đang tick
            # dù _sel/_export_sel đã bị xoá ở trên, dễ hiểu lầm "đã chọn" (hoặc
            # khiến Xuất Excel/Phê duyệt tưởng chưa chọn gì mà âm thầm dùng nhầm
            # phạm vi khác). Bỏ tick trực quan tất cả checkbox từng vẽ ra để khớp
            # với việc 2 set trên đã rỗng. Bọc try/except vì checkbox của 1 lần vẽ
            # trước có thể đã bị gỡ khỏi DOM (sau khi lọc/vẽ lại) — lỗi 1 cái không
            # được làm hỏng việc đổi tab.
            for _ck in _all_sel_checkboxes:
                try:
                    _ck.set_value(False)
                except Exception:
                    pass

        leave_tabs.on_value_change(_on_leave_tab_change)

        with ui.tab_panels(leave_tabs, value=_default_tab).classes("w-full"):

            if t_dashboard:

                with ui.tab_panel(t_dashboard):

                    # Thẻ tổng quan tách khỏi _db_area — để có thể tính lại riêng theo
                    # khoảng ngày ở Bộ lọc tìm kiếm mà không phải reload cả dashboard.
                    _kpi_area = ui.column().classes("w-full")

                    def _render_kpi_cards(counts: dict):
                        """Vẽ lại 5 ô tổng quan từ counts = {status: số lượng}."""
                        _kpi_area.clear()
                        with _kpi_area:
                            # Thẻ tổng quan — nền trắng, viền xám mảnh, vạch màu ở cạnh trên,
                            # chữ căn trái — giống kiểu ô thống kê bên trang đối chiếu. Cả cụm
                            # bọc trong 1 khung riêng viền đỏ/nền hồng để tách khỏi phần dưới.
                            with ui.element("div").classes(
                                "w-full p-3 rounded-lg border border-red-300 bg-red-50"
                            ):
                                with ui.row().classes("w-full gap-3 flex-nowrap"):
                                    _cards = [
                                        ("Chờ KSV", counts.get("pending_ksv", 0), "border-t-orange-400", "text-orange-600"),
                                        ("Chờ Tổng hợp", counts.get("pending_tong_hop", 0), "border-t-yellow-400", "text-yellow-600"),
                                        ("Chờ Ban lãnh đạo duyệt", counts.get("pending_gd", 0), "border-t-blue-400", "text-blue-600"),
                                        ("Hoàn thành", counts.get("approved", 0), "border-t-green-400", "text-green-600"),
                                        ("Khai báo hộ", counts.get("direct", 0), "border-t-purple-400", "text-purple-600"),
                                    ]
                                    for lbl, cnt, top_cls, num_cls in _cards:
                                        with ui.element("div").classes(
                                            f"flex-1 min-w-0 px-4 py-3 rounded-lg border border-gray-200 border-t-4 {top_cls} bg-white"
                                        ):
                                            ui.label(lbl).classes("text-xs font-semibold text-gray-500")
                                            ui.label(str(cnt)).classes(f"text-2xl font-bold mt-1 {num_cls}")

                    _db_area = ui.column().classes("w-full gap-4")



                    async def _load_dashboard():

                        _db_area.clear()

                        _yr = _dt_mod.date.today().year

                        try:

                            data = await asyncio.to_thread(

                                api.get, "/api/leaves/stats/leader-dashboard", {"year": _yr}

                            )

                        except Exception as e:

                            if _handle_api_error(e):

                                return

                            with _db_area:

                                ui.label("Không thể tải dashboard.").classes("text-red-500 text-sm")

                            return

                        data = data if isinstance(data, dict) else {}

                        by_status = data.get("by_status", {})

                        pending_d = data.get("pending", [])

                        top_d     = data.get("top_staff", [])



                        # Mặc định (chưa lọc theo ngày): số liệu theo phạm vi vai trò từ
                        # backend. Nếu có Bộ lọc tìm kiếm (can_all), khối filter bên dưới
                        # sẽ tự tính lại theo khoảng ngày ngay sau khi dựng xong — đè lên
                        # giá trị này (xem _apply_filter → _render_kpi_cards).
                        _render_kpi_cards(by_status)

                        with _db_area:

                            # Đơn đang ch??

                            pass  # bỏ Đơn đang chờ duyệt (đã có trong module Chờ duyệt)



                            # Top nghỉ nhiều

                            pass  # bỏ Top nghỉ nhiều



                    await _load_dashboard()



                    if can_all:

                        ui.separator().classes("my-4")



                        # ── Filter controls ───────────────────────────────────

                        _all_depts = sorted({lv.get("department_name") or "" for lv in all_leaves if lv.get("department_name")})

                        _status_opts = {"": "Tất cả trạng thái", **{k: v[0] for k, v in _LEAVE_STATUS.items()}}

                        _type_opts   = {"": "Tất cả loại", **_LEAVE_TYPE}

                        _dept_opts   = {"": "Tất cả phòng", **{d: d for d in _all_depts}}



                        with ui.card().classes("w-full p-4 mb-3 border-2 border-red-800 rounded-lg"):

                            ui.label("Bộ lọc tìm kiếm").classes("text-xs font-bold text-red-800 uppercase mb-2")

                            with ui.row().classes("gap-3 flex-wrap items-end"):

                                _f_name   = ui.input("Tìm theo tên").classes("w-40").props("dense clearable")

                                _f_status = ui.select(_status_opts, value="", label="Trạng thái").classes("w-40").props("dense")

                                _f_type   = ui.select(_type_opts, value="", label="Loại nghỉ").classes("w-36").props("dense")

                                _f_dept   = ui.select(_dept_opts, value="", label="Phòng").classes("w-40").props("dense")

                                _f_ltype  = ui.select({
                                    "": "Tất cả loại đơn",
                                    "direct": "Khai báo hộ",
                                    "resubmit": "Gửi lại",
                                    "normal": "Thường",
                                }, value="", label="Loại đơn").classes("w-36").props("dense")

                                with ui.input("Ngày nghỉ từ").classes("w-36").props("dense clearable readonly") as _f_from:

                                    with _f_from.add_slot("append"):

                                        ui.icon("event").classes("cursor-pointer").on("click", lambda: _cal_from.open())

                                    with ui.menu() as _cal_from:

                                        ui.date(mask="DD/MM/YYYY").props(f'{_OPT_ALL} first-day-of-week="1"').bind_value(_f_from)

                                with ui.input("đến ngày").classes("w-36").props("dense clearable readonly") as _f_to:

                                    with _f_to.add_slot("append"):

                                        ui.icon("event").classes("cursor-pointer").on("click", lambda: _cal_to.open())

                                    with ui.menu() as _cal_to:

                                        ui.date(mask="DD/MM/YYYY").props(f'{_OPT_ALL} first-day-of-week="1"').bind_value(_f_to)

                            with ui.row().classes("gap-3 mt-2 items-center flex-wrap"):

                                _f_count  = ui.label("").classes("text-sm font-medium text-red-800 flex-1")

                                _f_mine_state = {"active": False}

                                _f_mine_btn = ui.button("👤 Đơn của tôi", icon="person",

                                    on_click=lambda: _toggle_mine()).props("outline").classes("text-red-700 border-red-400")

                                ui.button("Tìm kiếm", icon="search",

                                          on_click=lambda: _apply_filter()).classes("bg-red-700 text-white")

                                ui.button("Xóa lọc", icon="clear",

                                          on_click=lambda: _reset_filter()).props("flat").classes("text-gray-500")



                        def _toggle_mine():

                            _f_mine_state["active"] = not _f_mine_state["active"]

                            if _f_mine_state["active"]:

                                _f_mine_btn.style("background:#8B0000; color:white; border-color:#8B0000")

                            else:

                                _f_mine_btn.style("background:transparent; color:#b91c1c; border-color:#fca5a5")

                            _apply_filter()



                        _all_container = ui.column().classes("w-full gap-0")



                        def _parse_date(s):

                            """dd/mm/yyyy hoặc yyyy-mm-dd → date object, None nếu lỗi."""

                            from datetime import date as _d

                            s = (s or "").strip()

                            if not s:

                                return None

                            try:

                                if "/" in s:

                                    parts = s.split("/")

                                    if len(parts) == 3:

                                        return _d(int(parts[2]), int(parts[1]), int(parts[0]))

                                return _d.fromisoformat(s[:10])

                            except Exception:

                                return None



                        def _matches_daterange(lv, from_d, to_d):
                            """True nếu đơn có ít nhất 1 ngày nghỉ rơi vào [from_d, to_d].
                            Không chọn ngày nào → luôn True. Tách ra từ _apply_filter để
                            dùng chung với _status_counts_by_date (5 ô tổng quan)."""
                            if not (from_d or to_d):
                                return True
                            sd = lv.get("spread_dates")
                            _dates = [d for d in (_parse_date(x) for x in sd) if d] if sd else []
                            if _dates:
                                return any((not from_d or d >= from_d) and (not to_d or d <= to_d) for d in _dates)
                            lv_start = _parse_date(lv.get("start_date", ""))
                            lv_end   = _parse_date(lv.get("end_date", ""))
                            if lv_start and lv_end:
                                if from_d and lv_end < from_d:
                                    return False
                                if to_d and lv_start > to_d:
                                    return False
                            return True

                        def _status_counts_by_date(from_d, to_d):
                            """Đếm đơn theo trạng thái trong khoảng ngày — nguồn cho 5 ô
                            tổng quan khi có Bộ lọc tìm kiếm (all_leaves = toàn trung tâm,
                            không giới hạn theo vai trò như by_status của backend)."""
                            counts = {"pending_ksv": 0, "pending_tong_hop": 0, "pending_gd": 0,
                                      "approved": 0, "direct": 0}
                            for lv in all_leaves:
                                if not _matches_daterange(lv, from_d, to_d):
                                    continue
                                st = lv.get("status")
                                if st in ("pending_ksv", "pending_tong_hop", "pending_gd"):
                                    counts[st] += 1
                                elif st == "approved":
                                    counts["approved"] += 1
                                    if lv.get("is_direct"):
                                        counts["direct"] += 1
                            return counts



                        def _apply_filter():

                            name_q  = (_f_name.value or "").strip().lower()

                            st_q    = _f_status.value or ""

                            ty_q    = _f_type.value or ""

                            dept_q  = _f_dept.value or ""

                            ltype_q = _f_ltype.value or ""

                            from_d  = _parse_date(_f_from.value)

                            to_d    = _parse_date(_f_to.value)

                            mine_only = _f_mine_state.get("active", False)

                            filtered = []

                            for lv in all_leaves:

                                if mine_only and lv.get("staff_id") != user_id:

                                    continue

                                if name_q and name_q not in (lv.get("staff_name") or "").lower():

                                    continue

                                if st_q and lv.get("status") != st_q:

                                    continue

                                if ty_q and lv.get("leave_type") != ty_q:

                                    continue

                                if dept_q and (lv.get("department_name") or "") != dept_q:

                                    continue

                                if ltype_q == "direct" and not lv.get("is_direct"):
                                    continue
                                if ltype_q == "resubmit" and not lv.get("is_resubmitted"):
                                    continue
                                if ltype_q == "normal" and (lv.get("is_direct") or lv.get("is_resubmitted")):
                                    continue

                                if not _matches_daterange(lv, from_d, to_d):

                                    continue

                                filtered.append(lv)

                            _f_count.set_text(f"{len(filtered)} / {len(all_leaves)} đơn")

                            _all_container.clear()

                            _export_sel.clear()

                            with _all_container:

                                _draw_table_paged(filtered, show_name=True, show_checkbox=False,

                                            export_sel=_export_sel)

                            # 5 ô tổng quan luôn theo đúng khoảng ngày đang lọc (không theo
                            # tên/trạng thái/phòng/loại đơn — chỉ riêng ngày) — không chọn
                            # ngày nào thì tính trên toàn bộ đơn (from_d=to_d=None).
                            _render_kpi_cards(_status_counts_by_date(from_d, to_d))



                        def _reset_filter():

                            _f_name.value   = ""

                            _f_status.value = ""

                            _f_type.value   = ""

                            _f_dept.value   = ""

                            _f_ltype.value  = ""

                            _f_from.value   = ""

                            _f_to.value     = ""

                            _f_mine_state["active"] = False

                            _f_mine_btn.style("background:transparent; color:#b91c1c; border-color:#fca5a5")

                            _apply_filter()



                        _f_name.on("keydown.enter", lambda _: _apply_filter())

                        _f_from.on("keydown.enter", lambda _: _apply_filter())

                        _f_to.on("keydown.enter",   lambda _: _apply_filter())



                        _apply_filter()  # render lần đầu

                    elif can_declared and declared_leaves:

                        ui.separator().classes("my-4")

                        ui.label(f"Đơn đã khai báo hộ ({len(declared_leaves)})").classes("font-bold text-gray-700 text-sm mb-2")

                        _draw_table(declared_leaves, show_name=True)



                    # Nếu không có "Của tôi" / "Phòng tôi" ri→ng → hiện trong Dashboard với filter

                    if _has_dash and not can_all:



                        def _make_section_filter(src_leaves: list, title_prefix: str, show_name_: bool):

                            """Tạo filter card + container cho một section."""

                            _sf_status_opts = {"": "Tất cả trạng thái", **{k: v[0] for k, v in _LEAVE_STATUS.items()}}

                            _sf_type_opts   = {"": "Tất cả loại", **_LEAVE_TYPE}

                            with ui.card().classes("w-full p-4 mb-3 border-2 border-red-800 rounded-lg"):

                                ui.label("Bộ lọc tìm kiếm").classes("text-xs font-bold text-red-800 uppercase mb-2")

                                with ui.row().classes("gap-3 flex-wrap items-end"):

                                    _sf_name   = ui.input("Tìm theo tên").classes("w-40").props("dense clearable")

                                    _sf_status = ui.select(_sf_status_opts, value="", label="Trạng thái").classes("w-40").props("dense")

                                    _sf_type   = ui.select(_sf_type_opts, value="", label="Loại nghỉ").classes("w-36").props("dense")

                                    # Phòng filter
                                    _sf_dept_opts = {"": "Tất cả phòng"}
                                    for lv in src_leaves:
                                        dn = lv.get("department_name") or lv.get("dept_name") or ""
                                        if dn and dn not in _sf_dept_opts.values():
                                            _sf_dept_opts[dn] = dn
                                    _sf_dept = ui.select(_sf_dept_opts, value="", label="Phòng").classes("w-40").props("dense") if len(_sf_dept_opts) > 2 else None

                                    with ui.input("Ngày nghỉ từ").classes("w-36").props("dense clearable readonly") as _sf_from:

                                        with _sf_from.add_slot("append"):

                                            ui.icon("event").classes("cursor-pointer").on("click", lambda: _sf_cal_from.open())

                                        with ui.menu() as _sf_cal_from:

                                            ui.date(mask="DD/MM/YYYY").props(f'{_OPT_ALL} first-day-of-week="1"').bind_value(_sf_from)

                                    with ui.input("đến ngày").classes("w-36").props("dense clearable readonly") as _sf_to:

                                        with _sf_to.add_slot("append"):

                                            ui.icon("event").classes("cursor-pointer").on("click", lambda: _sf_cal_to.open())

                                        with ui.menu() as _sf_cal_to:

                                            ui.date(mask="DD/MM/YYYY").props(f'{_OPT_ALL} first-day-of-week="1"').bind_value(_sf_to)

                                with ui.row().classes("gap-3 mt-2 items-center flex-wrap"):

                                    _sf_count = ui.label(f"{len(src_leaves)} / {len(src_leaves)} đơn").classes("text-sm font-medium text-red-800 flex-1")

                                    _sf_mine_state = {"active": False}

                                    _sf_mine_btn = ui.button("👤 Đơn của tôi",

                                        on_click=lambda: _sf_toggle_mine()

                                    ).props("flat").classes("border rounded px-3 text-red-700 border-red-400")

                                    ui.button("Tìm kiếm", icon="search",

                                              on_click=lambda: _sf_apply()).classes("bg-red-700 text-white")

                                    ui.button("Xóa lọc", icon="clear",

                                              on_click=lambda: _sf_reset()).props("flat").classes("text-gray-500")



                            def _sf_toggle_mine():

                                _sf_mine_state["active"] = not _sf_mine_state["active"]

                                if _sf_mine_state["active"]:

                                    _sf_mine_btn.style("background:#8B0000; color:white; border-color:#8B0000")

                                else:

                                    _sf_mine_btn.style("background:transparent; color:#b91c1c; border-color:#fca5a5")

                                _sf_apply()



                            _sf_container = ui.column().classes("w-full gap-0")



                            def _parse_sf_date(s):

                                from datetime import date as _dd

                                s = (s or "").strip()

                                if not s: return None

                                try:

                                    if "/" in s:

                                        p = s.split("/")

                                        return _dd(int(p[2]), int(p[1]), int(p[0]))

                                    return _dd.fromisoformat(s[:10])

                                except Exception:

                                    return None



                            def _sf_matches_daterange(lv, fd, td):
                                """Giống _matches_daterange ở khối can_all — nhưng dùng
                                _parse_sf_date riêng của section này (Phòng tôi/Của tôi)."""
                                if not (fd or td):
                                    return True
                                sd = lv.get("spread_dates")
                                _dates = [d for d in (_parse_sf_date(x) for x in sd) if d] if sd else []
                                if _dates:
                                    return any((not fd or d >= fd) and (not td or d <= td) for d in _dates)
                                s = _parse_sf_date(lv.get("start_date", ""))
                                e = _parse_sf_date(lv.get("end_date", ""))
                                if s and e:
                                    if fd and e < fd:
                                        return False
                                    if td and s > td:
                                        return False
                                return True

                            def _sf_status_counts(fd, td):
                                """Đếm theo trạng thái trong khoảng ngày — chỉ trong phạm vi
                                src_leaves (đơn phòng mình / đơn của mình), KHÔNG phải toàn
                                trung tâm — nguồn cho 5 ô tổng quan của KSV/chuyên viên."""
                                counts = {"pending_ksv": 0, "pending_tong_hop": 0, "pending_gd": 0,
                                          "approved": 0, "direct": 0}
                                for lv in src_leaves:
                                    if not _sf_matches_daterange(lv, fd, td):
                                        continue
                                    st = lv.get("status")
                                    if st in ("pending_ksv", "pending_tong_hop", "pending_gd"):
                                        counts[st] += 1
                                    elif st == "approved":
                                        counts["approved"] += 1
                                        if lv.get("is_direct"):
                                            counts["direct"] += 1
                                return counts

                            def _sf_apply():

                                nq = (_sf_name.value or "").strip().lower()

                                sq = _sf_status.value or ""

                                tq = _sf_type.value or ""

                                dq = (_sf_dept.value or "") if _sf_dept else ""

                                fd = _parse_sf_date(_sf_from.value)

                                td = _parse_sf_date(_sf_to.value)

                                mine_only = _sf_mine_state.get("active", False)

                                filtered = []

                                for lv in src_leaves:

                                    if mine_only and lv.get("staff_id") != user_id: continue

                                    if nq and nq not in (lv.get("staff_name") or "").lower(): continue

                                    if sq and lv.get("status") != sq: continue

                                    if tq and lv.get("leave_type") != tq: continue

                                    if dq and (lv.get("department_name") or lv.get("dept_name") or "") != dq: continue

                                    if not _sf_matches_daterange(lv, fd, td): continue

                                    filtered.append(lv)

                                _sf_count.set_text(f"{len(filtered)} / {len(src_leaves)} đơn")

                                _sf_container.clear()

                                _export_sel.clear()

                                with _sf_container:

                                    _draw_table_paged(filtered, show_name=show_name_, show_checkbox=False, export_sel=_export_sel)

                                # 5 ô tổng quan chỉ theo khoảng ngày (không theo tên/trạng
                                # thái/phòng/loại) — không chọn ngày nào thì tính trên toàn
                                # bộ đơn CỦA PHẠM VI NÀY (phòng mình / của mình), không phải
                                # toàn trung tâm.

                                _render_kpi_cards(_sf_status_counts(fd, td))



                            def _sf_reset():

                                _sf_name.value = _sf_status.value = _sf_type.value = ""

                                _sf_from.value = _sf_to.value = ""

                                if _sf_dept: _sf_dept.value = ""

                                _sf_mine_state["active"] = False

                                _sf_mine_btn.style("background:transparent; color:#b91c1c; border-color:#fca5a5")

                                _sf_count.set_text(f"{len(src_leaves)} / {len(src_leaves)} đơn")

                                _sf_container.clear()

                                _export_sel.clear()

                                with _sf_container:

                                    _draw_table_paged(src_leaves, show_name=show_name_, show_checkbox=False, export_sel=_export_sel)

                                _render_kpi_cards(_sf_status_counts(None, None))



                            _sf_name.on("keydown.enter", lambda _: _sf_apply())

                            with _sf_container:

                                _draw_table_paged(src_leaves, show_name=show_name_, show_checkbox=False, export_sel=_export_sel)

                            _render_kpi_cards(_sf_status_counts(None, None))  # render lần đầu, chưa lọc ngày



                        if can_dept and dept_leaves:

                            ui.separator().classes("my-4")

                            ui.label(f"Đơn phòng tôi ({len(dept_leaves)})").classes("font-bold text-gray-700 text-sm mb-2")

                            _make_section_filter(dept_leaves, "Phòng tôi", True)

                        else:

                            # Luôn hiện "Của tôi" kể cả khi chưa có đơn nào

                            ui.separator().classes("my-4")

                            ui.label(f"Đơn của tôi ({len(my_leaves)})").classes("font-bold text-gray-700 text-sm mb-2")

                            _make_section_filter(my_leaves, "Của tôi", False)



            if t_mine:

                with ui.tab_panel(t_mine):

                    _draw_table_paged(my_leaves)



            if t_pending:
                with ui.tab_panel(t_pending):
                    _show_pending = _pending_ksv_list if _is_dual_role else pending_leaves
                    _draw_pending_with_filter(_show_pending)

            if t_pending_th:
                with ui.tab_panel(t_pending_th):
                    with ui.column().classes("w-full gap-2"):
                        ui.label("Đơn chờ xác nhận của toàn Trung tâm").classes("text-sm text-gray-500 italic")
                        _draw_pending_with_filter(_pending_th_list)



            if can_dept and t_dept:

                with ui.tab_panel(t_dept):

                    _draw_table_paged(dept_leaves, show_name=True)



            with ui.tab_panel(t_cal):

                _today = _dt_mod.date.today()

                with ui.row().classes("gap-3 mb-4 items-center"):

                    cal_year  = ui.select({y: str(y) for y in range(2024, _today.year + 2)},

                                          label="Năm", value=_today.year).classes("w-28")

                    cal_month = ui.select({m: f"Tháng {m:02d}" for m in range(1, 13)},

                                          label="Tháng", value=_today.month).classes("w-36")



                _CAL_TYPE_COLOR = {

                    "annual":   "bg-blue-100 text-blue-800",

                    "bat_buoc": "bg-red-100 text-red-800",

                    "thai_san": "bg-orange-100 text-orange-800",

                    "bao_hiem": "bg-purple-100 text-purple-800",

                    "other":    "bg-gray-100 text-gray-600",

                }

                _CAL_TYPE_DOT = {

                    "annual":   "#1565C0",

                    "bat_buoc": "#C62828",

                    "thai_san": "#E65100",

                    "bao_hiem": "#6A1B9A",

                    "other":    "#546E7A",

                }

                _DOW_VN = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]



                cal_container = ui.column().classes("w-full gap-0")



                async def _reload_cal():

                    cal_container.clear()

                    try:

                        data = await asyncio.to_thread(

                            api.get, "/api/leaves/calendar",

                            {"year": cal_year.value, "month": cal_month.value},

                        )

                    except Exception:

                        data = {}

                    days_map = data.get("days", {}) if isinstance(data, dict) else {}

                    y, m = cal_year.value, cal_month.value



                    import calendar as _cal_mod

                    first_wd = _dt_mod.date(y, m, 1).weekday()  # 0=Thứ 2

                    last_day = _cal_mod.monthrange(y, m)[1]



                    with cal_container:

                        # Chú th→ch

                        with ui.row().classes("gap-4 mb-3 flex-wrap items-center"):

                            for _lt, _cls in _CAL_TYPE_COLOR.items():

                                with ui.row().classes("items-center gap-1"):

                                    ui.html(f'<span class="text-xs px-2 py-0.5 rounded {_cls}">{_LEAVE_TYPE.get(_lt, _lt)}</span>')

                        # Header ngày trong tuần

                        with ui.row().classes("w-full grid gap-1").style(

                                "display:grid;grid-template-columns:repeat(7,1fr)"):

                            for d in _DOW_VN:

                                ui.label(d).classes(

                                    "text-center text-xs font-bold text-gray-500 py-1"

                                    + (" text-red-600" if d == "CN" else "")

                                )

                        # Lưới ngày

                        with ui.element("div").style(

                                "display:grid;grid-template-columns:repeat(7,1fr);gap:4px"):

                            # → trống trước ngày 1

                            for _ in range(first_wd):

                                ui.element("div").classes("rounded bg-gray-50 min-h-[72px] p-1")

                            for day in range(1, last_day + 1):

                                d_str = f"{y}-{m:02d}-{day:02d}"

                                d_obj = _dt_mod.date(y, m, day)

                                people = days_map.get(d_str, [])

                                is_weekend = d_obj.weekday() >= 5

                                is_today   = d_obj == _today

                                bg = "bg-blue-50 border-blue-300" if is_today else (

                                     "bg-red-50" if is_weekend else "bg-white border-gray-100")

                                with ui.element("div").classes(

                                        f"rounded border {bg} min-h-[72px] p-1 overflow-hidden"

                                ):

                                    ui.label(str(day)).classes(

                                        "text-xs font-bold mb-1 " + (

                                            "text-blue-700" if is_today else

                                            "text-red-500" if is_weekend else "text-gray-700"

                                        )

                                    )

                                    for p in people[:3]:

                                        lt   = p.get("leave_type", "other")

                                        cls  = _CAL_TYPE_COLOR.get(lt, "bg-gray-100 text-gray-600")

                                        name = p.get("staff_name", "")

                                        # Rít g??n hờ tên → lấy tên cuối

                                        short = name.split()[-1] if name else ""

                                        ui.label(short).classes(

                                            f"text-[10px] leading-tight px-1 rounded truncate {cls} mb-0.5 w-full")

                                    if len(people) > 3:

                                        ui.label(f"+{len(people)-3}").classes(

                                            "text-[9px] text-gray-500 leading-tight")

                                    # Di chuột vào ô ngày → hiện đủ danh sách (không cắt bớt như
                                    # trên) — dữ liệu đã theo đúng phạm vi phòng ban BE trả về
                                    # (xem leave_calendar()), nên chỉ cần liệt kê nguyên `people`.
                                    if people:
                                        _n_dept = len({p.get("dept_name") for p in people if p.get("dept_name")})
                                        with ui.tooltip().classes(
                                                "bg-white text-gray-800 shadow-lg border border-gray-200 p-2"):
                                            with ui.column().classes("gap-0.5"):
                                                ui.label(f"Ngày {day:02d}/{m:02d} — {len(people)} người nghỉ").classes(
                                                    "text-xs font-bold text-gray-700 mb-1")
                                                for p in people:
                                                    _lt   = p.get("leave_type", "other")
                                                    _cls  = _CAL_TYPE_COLOR.get(_lt, "bg-gray-100 text-gray-600")
                                                    _name = p.get("staff_name", "")
                                                    _line = _name
                                                    if _n_dept > 1 and p.get("dept_name"):
                                                        _line += f" — {p['dept_name']}"
                                                    ui.label(_line).classes(
                                                        f"text-xs px-1.5 py-0.5 rounded {_cls} whitespace-nowrap")



                cal_year.on("update:model-value",  lambda: asyncio.ensure_future(_reload_cal()))

                cal_month.on("update:model-value", lambda: asyncio.ensure_future(_reload_cal()))

                await _reload_cal()



            if can_delegation and t_deleg:

                with ui.tab_panel(t_deleg):

                    # ── Dialog tạo ủy quyền ───────────────────────────────────

                    gd_staff_list, pgd_staff_list = [], []

                    _deleg_staff_results = await asyncio.gather(

                        asyncio.to_thread(api.get, "/api/delegations/staff/giam-doc"),

                        asyncio.to_thread(api.get, "/api/delegations/staff/pho-giam-doc"),

                        return_exceptions=True,

                    )

                    _deleg_staff_err = next((r for r in _deleg_staff_results if isinstance(r, Exception)), None)

                    if _deleg_staff_err is not None:

                        if isinstance(_deleg_staff_err, api.SessionExpiredError):

                            if _handle_api_error(_deleg_staff_err):

                                return

                        else:

                            ui.notify("Không tải được danh sách GĐ/PGĐ để tạo ủy quyền", type="negative")

                    else:

                        gd_staff_list, pgd_staff_list = _deleg_staff_results



                    gd_opts  = {s["id"]: s["full_name"] for s in (gd_staff_list  or [])}

                    pgd_opts = {s["id"]: s["full_name"] for s in (pgd_staff_list or [])}



                    with ui.dialog() as deleg_dialog, ui.card().classes("p-6 w-96"):

                        ui.label("Tạo ủy quyền Giám đốc").classes("text-lg font-bold text-red-900 mb-4")

                        d_gd   = ui.select(gd_opts,  label="Giám đốc ủy quyền").classes("w-full")

                        d_pgd  = ui.select(pgd_opts, label="PGĐ được ủy quyền").classes("w-full mt-2")

                        ui.label("Click chọn từng ngày → Click lại để bỏ chọn").classes("text-xs text-orange-500 mt-2")

                        _d_sel: list = []

                        def _on_d_change(e):
                            _d_sel.clear()
                            v = e.value
                            if isinstance(v, list):
                                _d_sel.extend(d for d in v if d and d != "undefined")
                            elif isinstance(v, dict):
                                _d_sel.extend(k for k, ok in v.items() if ok)
                            elif isinstance(v, str) and v:
                                _d_sel.append(v)

                        d_dates = ui.date(value=[], on_change=_on_d_change).props(
                            f"multiple mask='YYYY-MM-DD' no-header first-day-of-week='1' {_OPT_ALL}"
                        ).classes("w-full")

                        d_note = ui.input("Ghi chú (tuỳ chọn)").classes("w-full mt-2")



                        async def do_create_deleg():

                            if not d_gd.value or not d_pgd.value:
                                ui.notify("Vui lòng chọn Giám đốc và PGĐ", type="warning"); return

                            dates = sorted(set(_d_sel))
                            if not dates:
                                ui.notify("Vui lòng chọn ít nhất 1 ngày", type="warning"); return

                            start_date = dates[0]
                            end_date   = dates[-1]

                            try:

                                await asyncio.to_thread(api.post, "/api/delegations/", {

                                    "giam_doc_id": d_gd.value, "pho_giam_doc_id": d_pgd.value,

                                    "start_date": start_date, "end_date": end_date,

                                    "note": d_note.value or None,

                                })

                                deleg_dialog.close()

                                ui.notify("Đã tạo ủy quyền thành công!", type="positive")

                                # Broadcast thông báo đến tất cả user
                                from datetime import datetime as _dt_bc
                                gd_name  = gd_opts.get(d_gd.value, "Giám đốc")
                                pgd_name = pgd_opts.get(d_pgd.value, "Phó Giám đốc")
                                _msg = (f"📋 ỦY QUYỀN MỚI: Giám đốc {gd_name} ủy quyền cho "
                                        f"Phó Giám đốc {pgd_name} từ {_fmt_ngay_vn(start_date)} "
                                        f"đến {_fmt_ngay_vn(end_date)}")
                                if d_note.value:
                                    _msg += f" — {d_note.value}"
                                app.storage.general["_deleg_broadcast"] = {
                                    "msg": _msg, "ts": _dt_bc.now().isoformat(),
                                    "end_date": end_date,
                                }

                                ui.navigate.to("/leaves")

                            except Exception as e:

                                _handle_api_error(e)



                        with ui.row().classes("w-full justify-end gap-2 mt-4"):

                            ui.button("Hủy", on_click=deleg_dialog.close).classes("text-gray-500")

                            ui.button("Tạo ủy quyền", on_click=do_create_deleg).classes("bg-red-700 text-white")



                    def _deleg_open():
                        # Reset lại toàn bộ — nếu không, lần mở sau khi bấm "Hủy" dở
                        # dang vẫn còn giữ GĐ/PGĐ/ngày/ghi chú của lần trước.
                        d_gd.value = None
                        d_pgd.value = None
                        _d_sel.clear()
                        d_dates.value = []
                        d_note.value = ""
                        deleg_dialog.open()

                    ui.button("+ Tạo ủy quyền", on_click=_deleg_open).classes("bg-red-700 text-white mb-4")



                    if not delegations:

                        ui.label("Chưa có bản ghi ủy quyền nào.").classes("text-gray-500 text-sm")

                    else:

                        _dg_hdr = "font-semibold text-red-800 text-sm shrink-0 border-r border-red-200 pr-2 mr-2"
                        _dg_c   = "text-sm shrink-0 border-r border-gray-200 pr-2 mr-2"

                        with ui.column().classes("w-full gap-0 border border-gray-200 rounded overflow-hidden"):

                            with ui.row().classes("w-full bg-red-50 border-b border-red-100 px-4 py-2 gap-0 items-center"):

                                ui.label("STT").classes(f"{_dg_hdr} w-10 text-center")

                                ui.label("Giám đốc").classes(f"{_dg_hdr} w-32")

                                ui.label("PGĐ được ủy quyền").classes(f"{_dg_hdr} w-36")

                                ui.label("Từ ngày").classes(f"{_dg_hdr} w-24 text-center")

                                ui.label("Đến ngày").classes(f"{_dg_hdr} w-24 text-center")

                                ui.label("Ghi chú").classes(f"{_dg_hdr} flex-1")

                                ui.label("Trạng thái").classes(f"{_dg_hdr} w-32 text-center")

                                ui.label("").classes("w-16 shrink-0")

                            for _di, d in enumerate(delegations, 1):

                                today_str = __import__("datetime").date.today().isoformat()

                                is_eff = d["is_active"] and d["start_date"] <= today_str <= d["end_date"]

                                badge_cls = "bg-green-100 text-green-700" if is_eff else "bg-gray-100 text-gray-500"

                                badge_txt = "đang hiệu lực" if is_eff else "Không hiệu lực"

                                with ui.row().classes("w-full bg-white border-b border-gray-100 px-4 py-2 gap-0 items-center hover:bg-red-50"):

                                    ui.label(str(_di)).classes(f"{_dg_c} w-10 text-center")

                                    ui.label(d.get("giam_doc_name", "")).classes(f"{_dg_c} w-32 truncate")

                                    ui.label(d.get("pho_giam_doc_name", "")).classes(f"{_dg_c} w-36 truncate")

                                    ui.label(d.get("start_date", "")[:10]).classes(f"{_dg_c} w-24 text-center")

                                    ui.label(d.get("end_date", "")[:10]).classes(f"{_dg_c} w-24 text-center")

                                    ui.label(d.get("note") or "→").classes(f"{_dg_c} flex-1 text-gray-500")

                                    ui.label(badge_txt).classes(f"text-xs px-2 py-0.5 rounded {badge_cls} w-32 shrink-0 border-r border-gray-200 mr-2 text-center")

                                    if d["is_active"]:

                                        async def do_deactivate(did=d["id"]):

                                            try:

                                                await asyncio.to_thread(api.patch, f"/api/delegations/{did}/deactivate", {})

                                                ui.notify("Đã hủy ủy quyền", type="warning")

                                                ui.navigate.to("/leaves")

                                            except Exception as e:

                                                _handle_api_error(e)

                                        ui.button("Hủy", on_click=do_deactivate).classes("text-xs bg-gray-100 text-gray-600 w-16 shrink-0")

                                    else:

                                        ui.label("").classes("w-16 shrink-0")



            if can_holiday and t_holiday:

                with ui.tab_panel(t_holiday):

                    _cur_year = __import__("datetime").date.today().year

                    with ui.row().classes("gap-3 mb-4 items-center"):

                        h_year_sel = ui.select(

                            {y: str(y) for y in range(2024, _cur_year + 3)},

                            label="Năm", value=_cur_year,

                        ).classes("w-28")

                        ui.button("+ Thêm ngày lễ", icon="add",

                                  on_click=lambda: add_holiday_dialog.open()).classes("bg-red-700 text-white")



                    holiday_table_area = ui.column().classes("w-full gap-0")



                    with ui.dialog() as add_holiday_dialog, ui.card().classes("p-6 w-80"):

                        ui.label("Thêm ngày lễ").classes("text-lg font-bold text-red-900 mb-4")

                        h_date_in = ui.date(value="").props(f"label='Ngày lễ' mask='YYYY-MM-DD' first-day-of-week='1' {_VI_LOCALE}").classes("w-full")

                        h_name_in = ui.input("Tên ngày lễ").classes("w-full mt-2")



                        async def do_add_holiday():

                            if not h_date_in.value or not h_name_in.value.strip():

                                ui.notify("Vui lòng nhập đầy đủ thông tin", type="warning")

                                return

                            try:

                                await asyncio.to_thread(api.post, "/api/admin/holidays/", {

                                    "date": h_date_in.value,

                                    "name": h_name_in.value.strip(),

                                })

                                h_date_in.value = ""

                                h_name_in.value = ""

                                add_holiday_dialog.close()

                                ui.notify("Đã thêm ngày lễ!", type="positive")

                                await _reload_holidays()

                            except Exception as e:

                                _handle_api_error(e)



                        def _holiday_cancel():
                            h_date_in.value = ""
                            h_name_in.value = ""
                            add_holiday_dialog.close()

                        with ui.row().classes("w-full justify-end gap-2 mt-4"):

                            ui.button("Hủy", on_click=_holiday_cancel).classes("text-gray-500")

                            ui.button("Thêm", on_click=do_add_holiday).classes("bg-red-700 text-white")



                    async def _reload_holidays():

                        holiday_table_area.clear()

                        try:

                            holidays_data = await asyncio.to_thread(

                                api.get, "/api/admin/holidays/", {"year": h_year_sel.value}

                            )

                        except Exception:

                            holidays_data = []

                        holidays_data = holidays_data if isinstance(holidays_data, list) else []

                        with holiday_table_area:

                            if not holidays_data:

                                ui.label("Chưa có ngày lễ nào trong năm này.").classes("text-gray-500 text-sm mt-4")

                                return

                            with ui.column().classes("w-full gap-0"):

                                with ui.row().classes("w-full bg-red-50 border-b border-red-100 px-4 py-2 gap-3"):

                                    ui.label("Ngày").classes("font-semibold text-red-800 text-sm w-32 shrink-0")

                                    ui.label("Tên ngày lễ").classes("font-semibold text-red-800 text-sm flex-1")

                                    ui.label("").classes("w-12 shrink-0")

                                for h in holidays_data:

                                    with ui.row().classes("w-full bg-white border-b border-gray-100 px-4 py-2 gap-3 items-center"):

                                        ui.label(h.get("date", "")[:10]).classes("text-sm w-32 shrink-0 font-mono")

                                        ui.label(h.get("name", "")).classes("text-sm flex-1")

                                        async def do_del_holiday(hid=h["id"]):

                                            try:

                                                await asyncio.to_thread(api.delete, f"/api/admin/holidays/{hid}")

                                                ui.notify("Đã xóa ngày lễ", type="warning")

                                                await _reload_holidays()

                                            except Exception as ex:

                                                _handle_api_error(ex)

                                        ui.button(icon="delete", on_click=do_del_holiday).props(

                                            "flat round dense size=sm").classes("text-red-500 w-12 shrink-0")



                    h_year_sel.on("update:model-value", lambda: asyncio.ensure_future(_reload_holidays()))

                    await _reload_holidays()



            # ── Tab: Hạn mức phép ─────────────────────────────────────────────

            if t_quota:

                with ui.tab_panel(t_quota):

                    _today_year = _dt_mod.date.today().year

                    with ui.row().classes("gap-3 mb-4 items-end flex-nowrap"):

                        q_year_sel = ui.select(

                            {y: str(y) for y in range(_today_year - 2, _today_year + 2)},

                            label="Năm", value=_today_year,

                        ).classes("w-28 shrink-0")

                        if api.has_feature("leaves.quota_admin"):
                            ui.upload(
                                label="Nhập file hạn mức",
                                on_upload=lambda e: asyncio.create_task(_qi_on_upload(e)),
                                auto_upload=True,
                            ).props('accept=".xlsx" dense flat hide-upload-btn').classes(
                                "text-gray-700 w-56 shrink-0"
                            ).tooltip(
                                "File Excel có cột: STT, Họ và tên, Mã cán bộ, Phòng, Chức vụ, Hạn mức, Đã nghỉ"
                            )
                            ui.button("Lịch sử nhập", icon="history",
                                      on_click=lambda: asyncio.ensure_future(_qi_open_history())
                                      ).props("dense outline").classes("text-gray-700 shrink-0")

                    quota_area = ui.column().classes("w-full gap-0")

                    # ── Nhập file hạn mức: preview trước khi áp dụng ─────────────
                    _qi_state: dict = {"filename": "", "rows": []}
                    _qi_checks: dict = {}

                    with ui.dialog() as qi_preview_dialog, ui.card().classes("p-5 w-full max-w-4xl"):
                        ui.label("Xem trước dữ liệu nhập").classes("text-lg font-bold text-red-900 mb-1")
                        qi_summary_lbl = ui.label("").classes("text-sm text-gray-600 mb-2")
                        qi_rows_area = ui.column().classes("w-full gap-0 max-h-96 overflow-y-auto border border-gray-200 rounded")
                        with ui.row().classes("w-full justify-end gap-2 mt-4"):
                            ui.button("Từ chối", on_click=qi_preview_dialog.close).props("flat").classes("text-gray-500")
                            qi_apply_btn = ui.button("Đồng ý áp dụng", icon="check", on_click=lambda: asyncio.ensure_future(_qi_apply()))
                            qi_apply_btn.classes("bg-red-700 text-white")

                    def _qi_render_preview():
                        qi_rows_area.clear()
                        _qi_checks.clear()
                        rows = _qi_state["rows"]
                        matched = sum(1 for r in rows if r["matched"])
                        qi_summary_lbl.set_text(
                            f"File: {_qi_state['filename']} — Khớp {matched}/{len(rows)} dòng "
                            f"(theo Mã cán bộ, dự phòng theo Tên nếu không có/không khớp mã). "
                            f"Chỉ áp dụng cho các dòng đã tick và khớp được nhân viên."
                        )
                        with qi_rows_area:
                            with ui.row().classes("w-full px-2 py-1.5 bg-red-50 text-xs font-semibold text-red-800 border-b border-red-100 sticky top-0"):
                                ui.label("").classes("w-8")
                                ui.label("Họ tên (file)").classes("flex-1")
                                ui.label("Mã CB").classes("w-24")
                                ui.label("Khớp theo").classes("w-20")
                                ui.label("Khớp với (DB)").classes("flex-1")
                                ui.label("Hạn mức (cũ→mới)").classes("w-32 text-center")
                                ui.label("Đã nghỉ (cũ→mới)").classes("w-32 text-center")
                            _match_lbl = {"ma_can_bo": "Mã CB", "ten": "Tên"}
                            for _i, r in enumerate(rows):
                                with ui.row().classes("w-full px-2 py-1.5 border-b border-gray-100 items-center text-xs"
                                                       + ("" if r["matched"] else " bg-gray-50 text-gray-500")):
                                    cb = ui.checkbox(value=r["matched"]).classes("w-8")
                                    cb.set_enabled(r["matched"])
                                    if r["matched"]:
                                        _qi_checks[_i] = cb
                                    ui.label(r["ho_ten"]).classes("flex-1")
                                    ui.label(r["ma_can_bo"] or "→").classes("w-24")
                                    ui.label(_match_lbl.get(r.get("match_method"), "→")).classes(
                                        "w-20 " + ("text-green-700" if r["matched"] else "text-red-400"))
                                    _matched_name = r.get("matched_name")
                                    if r.get("row_error"):
                                        ui.label(r["row_error"]).classes("flex-1 text-red-500")
                                    elif _matched_name:
                                        _name_mismatch = _matched_name.strip().lower() != r["ho_ten"].strip().lower()
                                        ui.label(_matched_name).classes(
                                            "flex-1 " + ("text-orange-600 font-semibold" if _name_mismatch else "text-gray-600"))
                                    else:
                                        ui.label("Không khớp nhân viên nào").classes("flex-1 text-red-400")
                                    oq = r["old_quota_days"]
                                    ui.label(f"{oq:.0f} → {r['new_quota_days']:.0f}" if oq is not None else f"→ {r['new_quota_days']:.0f}").classes("w-32 text-center")
                                    ou = r["old_used_leave_days"]
                                    with ui.row().classes("w-32 items-center justify-center gap-1"):
                                        ui.label(f"{ou:.0f} → {r['new_used_leave_days']:.0f}" if ou is not None else f"→ {r['new_used_leave_days']:.0f}").classes("text-center")
                                        if r.get("rounded_warning"):
                                            ui.icon("warning", size="xs").classes("text-orange-500").tooltip(
                                                "Giá trị lẻ (nửa ngày) sẽ bị làm tròn lên nguyên ngày khi áp dụng"
                                            )

                    async def _qi_on_upload(e):
                        try:
                            yr = q_year_sel.value
                            result = await asyncio.to_thread(
                                api.post_upload,
                                f"/api/leaves/quotas/{yr}/import/preview",
                                {"file": (e.name, e.content.read(),
                                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                            )
                            _qi_state["filename"] = result.get("filename") or e.name
                            _qi_state["rows"] = result.get("rows") or []
                            if not _qi_state["rows"]:
                                ui.notify("Không đọc được dòng dữ liệu nào từ file.", type="warning")
                                return
                            _qi_render_preview()
                            qi_preview_dialog.open()
                        except Exception as ex:
                            _handle_api_error(ex)

                    async def _qi_apply():
                        rows = [r for _i, r in enumerate(_qi_state["rows"]) if _i in _qi_checks and _qi_checks[_i].value]
                        if not rows:
                            ui.notify("Chưa chọn dòng nào để áp dụng.", type="warning")
                            return
                        yr = q_year_sel.value
                        async def _do():
                            try:
                                res = await asyncio.to_thread(
                                    api.post, f"/api/leaves/quotas/{yr}/import/apply",
                                    {"filename": _qi_state["filename"], "rows": rows},
                                )
                                qi_preview_dialog.close()
                                _capped = res.get("capped_staff") or []
                                if _capped:
                                    ui.notify(
                                        f"Đã áp dụng {res.get('applied', 0)} nhân viên — nhưng {len(_capped)} người "
                                        f"({', '.join(_capped[:5])}{'…' if len(_capped) > 5 else ''}) đã có số ngày "
                                        f"đã dùng THẬT cao hơn số nhập, hệ thống giữ theo số thật, không giảm được.",
                                        type="warning", timeout=8000)
                                else:
                                    ui.notify(f"Đã áp dụng {res.get('applied', 0)} nhân viên. Có thể hoàn tác trong \"Lịch sử nhập\".",
                                              type="positive")
                                await _reload_quota()
                            except Exception as ex:
                                _handle_api_error(ex)
                        _ask_confirm("Xác nhận áp dụng",
                                     f"Áp dụng hạn mức + số ngày đã nghỉ cho {len(rows)} nhân viên từ file \"{_qi_state['filename']}\"? "
                                     f"Giá trị hiện tại sẽ bị ghi đè (có thể hoàn tác sau).",
                                     _do, "Đồng ý áp dụng", "bg-red-700")

                    with ui.dialog() as qi_history_dialog, ui.card().classes("p-5 w-full max-w-3xl"):
                        ui.label("Lịch sử nhập file hạn mức").classes("text-lg font-bold text-red-900 mb-3")
                        qi_history_area = ui.column().classes("w-full gap-0 max-h-96 overflow-y-auto")
                        with ui.row().classes("w-full justify-end mt-4"):
                            ui.button("Đóng", on_click=qi_history_dialog.close).props("flat").classes("text-gray-500")

                    async def _qi_open_history():
                        qi_history_area.clear()
                        try:
                            batches = await asyncio.to_thread(api.get, "/api/leaves/quotas/import/history")
                        except Exception as ex:
                            _handle_api_error(ex)
                            return
                        batches = batches if isinstance(batches, list) else []
                        with qi_history_area:
                            if not batches:
                                ui.label("Chưa có lần nhập nào.").classes("text-gray-500 text-sm")
                            for b in batches:
                                with ui.row().classes("w-full px-2 py-2 border-b border-gray-100 items-center text-xs gap-2"):
                                    with ui.column().classes("flex-1 gap-0"):
                                        ui.label(f"{b.get('filename') or '(không rõ tên file)'} — năm {b.get('year')}").classes("font-semibold text-sm")
                                        ui.label(
                                            f"{(b.get('imported_at') or '')[:16]} bởi {b.get('imported_by_name') or '→'} "
                                            f"— áp dụng {b.get('matched_count', 0)}/{b.get('row_count', 0)} dòng"
                                        ).classes("text-gray-500")
                                        if b.get("status") == "rolled_back":
                                            ui.label(
                                                f"↩ Đã hoàn tác {(b.get('rolled_back_at') or '')[:16]} bởi {b.get('rolled_back_by_name') or '→'}"
                                            ).classes("text-orange-600")
                                    if b.get("status") == "applied":
                                        async def _rb(bid=b["id"], fname=b.get("filename") or ""):
                                            async def _do(_bid=bid):
                                                try:
                                                    res = await asyncio.to_thread(
                                                        api.post, f"/api/leaves/quotas/import/{_bid}/rollback", {})
                                                    _skip = res.get("skipped_superseded", 0)
                                                    _msg = f"Đã hoàn tác {res.get('restored', 0)} nhân viên."
                                                    if _skip:
                                                        _msg += f" Bỏ qua {_skip} người đã có lần nhập mới hơn đè lên."
                                                    ui.notify(_msg, type="positive")
                                                    await _qi_open_history()
                                                    await _reload_quota()
                                                except Exception as ex:
                                                    _handle_api_error(ex)
                                            _ask_confirm("Xác nhận hoàn tác",
                                                         f"Hoàn tác lần nhập \"{fname}\"? Hạn mức + số ngày đã nghỉ của các nhân viên "
                                                         f"trong lần nhập này sẽ trở về giá trị trước đó.",
                                                         _do, "Hoàn tác", "bg-orange-600")
                                        ui.button("Hoàn tác", icon="undo", on_click=_rb).props("dense outline").classes("text-orange-700")
                                    else:
                                        ui.label("Đã hoàn tác").classes("text-gray-500 italic")
                        qi_history_dialog.open()



                    # Dialog sửa hạn mức + ngày vào ngânh

                    _quota_cb: list = [None]
                    _quota_carry: list = [0.0]  # carry-over hiệu lực của người đang sửa — dùng để tính "Còn lại" live

                    with ui.dialog() as quota_dialog, ui.card().classes("p-6 w-96"):

                        ui.label("Chỉnh sửa thông tin phép").classes("text-lg font-bold text-red-900 mb-1")

                        _q_staff_lbl = ui.label("").classes("text-sm text-gray-500 mb-3")

                        _q_calc_lbl  = ui.label("").classes("text-xs text-blue-600 mb-1")



                        def _update_q_remaining(e=None):
                            try:
                                q = float(q_days_input.value or 0)
                                u = float(q_used_input.value or 0)
                                c = float(_quota_carry[0] or 0)
                                rem = max(0.0, q + c - u)
                                _q_remaining_lbl.set_text(
                                    f"Còn lại: {rem:g} ngày  (Hạn mức {q:g} + Chuyển kỳ {c:g} − Đã dùng {u:g})")
                            except Exception:
                                _q_remaining_lbl.set_text("")

                        def _auto_calc_quota(e=None):

                            js = (q_join_input.value or "").strip()

                            # ??ủ định dạng DD-MM-YYYY

                            if len(js) == 10 and js[2] == "-" and js[5] == "-":

                                try:

                                    yr_join = int(js[6:10])

                                    yr_ref  = q_year_sel.value

                                    yrs     = max(0, yr_ref - yr_join)

                                    calc    = 12 + yrs // 4

                                    q_days_input.value = calc

                                    _q_calc_lbl.set_text(

                                        f"✓ {yrs} năm công tác → {calc} ngày phép tự động")

                                except Exception:

                                    _q_calc_lbl.set_text("")

                            else:

                                _q_calc_lbl.set_text("")

                            _update_q_remaining()



                        q_join_input = ui.input("Ngày vào ngânh (DD-MM-YYYY)",

                                                on_change=_auto_calc_quota).classes("w-full").props(

                            "dense mask='##-##-####' placeholder='DD-MM-YYYY'")

                        q_days_input = ui.number("Hạn mức ngày phép (tự động điền, có thể sửa thủ công)",

                                                 value=12, min=0, max=365,
                                                 on_change=_update_q_remaining).classes("w-full mt-2")

                        ui.label("Công thức: 12 ngày + 1 ngày mỗi 5 năm công tác").classes("text-xs text-gray-500 mt-1 mb-4")

                        q_used_input = ui.number("Đã dùng (có thể sửa thủ công)",
                                                  value=0, min=0, max=365,
                                                  on_change=_update_q_remaining).classes("w-full")

                        _q_remaining_lbl = ui.label("").classes("text-xs text-green-700 font-semibold mt-1 mb-4")



                        async def _confirm_quota():

                            cb = _quota_cb[0]

                            quota_dialog.close()

                            if cb:

                                await cb(q_days_input.value, q_join_input.value, q_used_input.value)



                        with ui.row().classes("w-full justify-end gap-2 mt-2"):

                            ui.button("Hủy", on_click=quota_dialog.close).props("flat").classes("text-gray-500")

                            ui.button("Lưu", icon="save", on_click=_confirm_quota).classes("bg-red-700 text-white")



                    async def _reload_quota():

                        quota_area.clear()

                        yr = q_year_sel.value

                        try:

                            data = await asyncio.to_thread(api.get, f"/api/leaves/quotas/{yr}")

                        except Exception:

                            data = []

                        data = data if isinstance(data, list) else []

                        _quota_sel.clear()

                        with quota_area:

                            if not data:

                                ui.label("Không có dữ liệu.").classes("text-gray-500 text-sm mt-4")

                                return

                            # Group theo phòng

                            from collections import defaultdict as _ddict

                            groups = _ddict(list)

                            for row in data:

                                groups[row.get("dept_name") or "→ Chưa có phòng →"].append(row)



                            _qh = "text-xs font-semibold text-red-800 shrink-0 border-r border-red-200 pr-3 mr-1"

                            _qc = "text-xs shrink-0 border-r border-gray-200 pr-3 mr-1"



                            def _render_quota_header(dept_rows, _row_cks):

                                with ui.row().classes("w-full bg-red-50 border-b border-red-200 px-3 py-1.5 items-center gap-0"):

                                    _dept_ids = [r["staff_id"] for r in dept_rows]

                                    def _select_all_q(e, _refs=_row_cks, _ids=_dept_ids):
                                        for ck in _refs:
                                            ck.set_value(e.value)
                                        if e.value:
                                            _quota_sel.update(_ids)
                                        else:
                                            for i in _ids:
                                                _quota_sel.discard(i)

                                    ui.checkbox(value=False, on_change=_select_all_q).props("dense").classes(
                                        "w-6 shrink-0 border-r border-gray-200 pr-2 mr-2"
                                    ).tooltip("Chọn / Bỏ chọn tất cả")

                                    ui.label("STT").classes(f"{_qh} w-8 text-center")

                                    ui.label("Họ và tên").classes(f"{_qh} w-36")

                                    ui.label("Mã cán bộ").classes(f"{_qh} w-24 text-center")

                                    ui.label("Ngày vào ngành").classes(f"{_qh} w-28 text-center")

                                    ui.label("Hạn mức").classes(f"{_qh} w-20 text-center")

                                    ui.label("Ngày phép chuyển kỳ").classes(f"{_qh} w-28 text-center")

                                    ui.label("Đã dùng").classes(f"{_qh} w-20 text-center")

                                    ui.label("Ngày phép của năm").classes(f"{_qh} flex-1 text-center")

                                    ui.label("").classes("w-8 shrink-0")



                            _DEPT_ORDER = {

                                "Ban Giám đốc": 0,

                                "Phòng Thanh toán": 1,

                                "Phòng Tổng hợp": 2,

                                "Phòng Swift": 3,

                                "Phòng Quản lý Tài khoản Nostro Vostro": 4,

                                "Phòng Kế toán": 5,

                                "Phòng KSNB&HTVH": 6,

                            }

                            with ui.column().classes("w-full gap-3"):

                                for dept_name, dept_rows in sorted(

                                    groups.items(),

                                    key=lambda x: (_DEPT_ORDER.get(x[0], 99), x[0])

                                ):

                                    with ui.column().classes("w-full gap-0 border border-gray-200 rounded overflow-hidden"):

                                        # Ti→u đờ phòng

                                        with ui.row().classes("w-full bg-red-900 px-3 py-1.5 items-center gap-2"):

                                            ui.label(dept_name).classes("text-white text-xs font-bold uppercase flex-1")

                                            ui.label(f"{len(dept_rows)} người").classes("text-red-200 text-xs")

                                        _row_cks: list = []  # references tới từng checkbox hàng trong phòng này

                                        _render_quota_header(dept_rows, _row_cks)

                                        for _qi, row in enumerate(dept_rows, 1):

                                            with ui.row().classes("w-full bg-white border-b border-gray-300 px-3 py-1.5 items-center gap-0 hover:bg-red-50"):

                                                def _on_qck(e, sid=row["staff_id"]):

                                                    _quota_sel.add(sid) if e.value else _quota_sel.discard(sid)

                                                _qck = ui.checkbox(value=False, on_change=_on_qck).props("dense").classes(
                                                    "w-6 shrink-0 border-r border-gray-200 pr-2 mr-2"
                                                )

                                                _row_cks.append(_qck)

                                                ui.label(str(_qi)).classes(f"{_qc} w-8 text-center")

                                                ui.label(row.get("staff_name", "")).classes(f"{_qc} w-36 truncate")

                                                ui.label(row.get("employee_code", "") or "→").classes(f"{_qc} w-24 text-center")

                                                jd = row.get("join_industry_date") or ""

                                                jd_fmt = f"{jd[8:10]}/{jd[5:7]}/{jd[:4]}" if len(jd) >= 10 else "→"

                                                ui.label(jd_fmt).classes(f"{_qc} w-28 text-center")

                                                ui.label(f"{row.get('quota_days', 0):.0f}").classes(f"{_qc} w-20 text-center font-mono")

                                                co = row.get("carry_over", 0)  # hết hiệu lực sau Q1 (31/3) — tự biến mất

                                                co_cls = "text-blue-700 font-semibold" if co > 0 else "text-gray-300"

                                                ui.label(f"{co:.1f}" if co > 0 else "0").classes(f"text-xs w-28 shrink-0 border-r border-gray-200 pr-3 mr-1 text-center font-mono {co_cls}")

                                                ui.label(f"{row.get('used_days', 0):.1f}").classes(f"{_qc} w-20 text-center font-mono")

                                                rem = row.get("remaining", 0)

                                                rem_cls = "text-green-700 font-semibold" if rem > 0 else "text-red-600 font-semibold"

                                                ui.label(f"{rem:.1f}").classes(f"text-xs flex-1 text-center font-mono {rem_cls}")



                                                def _open_quota_set2(sid=row["staff_id"], sname=row["staff_name"],

                                                                    cur_days=row["quota_days"],

                                                                    cur_join=row.get("join_industry_date",""),

                                                                    cur_used=row.get("used_days", 0),

                                                                    cur_carry=row.get("carry_over", 0)):

                                                    _q_staff_lbl.set_text(sname)

                                                    q_days_input.value = cur_days

                                                    q_used_input.value = cur_used

                                                    _quota_carry[0] = cur_carry

                                                    # Chuyển YYYY-MM-DD → DD-MM-YYYY để hiển thị

                                                    if cur_join and len(cur_join) >= 10:

                                                        q_join_input.value = f"{cur_join[8:10]}-{cur_join[5:7]}-{cur_join[:4]}"

                                                    else:

                                                        q_join_input.value = ""

                                                    _update_q_remaining()

                                                    async def _cb2(days, join_str, used_days, _sid=sid, _sname=sname, _yr=yr):

                                                        errs = []

                                                        _ud_capped = False

                                                        try:

                                                            await asyncio.to_thread(api.post, "/api/leaves/quotas",

                                                                {"staff_id": _sid, "year": _yr, "quota_days": float(days)})

                                                        except Exception as ex:

                                                            errs.append(str(ex))

                                                        try:

                                                            _ud_resp = await asyncio.to_thread(api.patch,

                                                                f"/api/leaves/quotas/staff/{_sid}/used-days",

                                                                {"year": _yr, "used_days": float(used_days)})

                                                            _ud_capped = isinstance(_ud_resp, dict) and _ud_resp.get("capped")

                                                        except Exception as ex:

                                                            errs.append(str(ex))

                                                        # Chuyển DD-MM-YYYY → YYYY-MM-DD trước khi lưu

                                                        js = (join_str or "").strip().replace("_", "")

                                                        if js and len(js) == 10 and js[2] == "-" and js[5] == "-":

                                                            iso = f"{js[6:10]}-{js[3:5]}-{js[:2]}"

                                                        else:

                                                            iso = js

                                                        if iso:

                                                            try:

                                                                await asyncio.to_thread(api.patch,

                                                                    f"/api/leaves/quotas/staff/{_sid}/join-date",

                                                                    {"join_industry_date": iso})

                                                            except Exception as ex:

                                                                errs.append(str(ex))

                                                        if errs:

                                                            ui.notify(f"Lỗi: {'; '.join(errs)}", type="negative", timeout=5000)

                                                        elif _ud_capped:

                                                            ui.notify(

                                                                f"Đã cập nhật {_sname} — nhưng số ngày đã dùng thật (từ đơn nghỉ phép thật) "

                                                                f"đã cao hơn giá trị bạn nhập, nên hệ thống giữ theo số thật, không giảm được.",

                                                                type="warning", timeout=6000)

                                                            await _reload_quota()

                                                        else:

                                                            ui.notify(f"Đã cập nhật {_sname}", type="positive", timeout=3000)

                                                            await _reload_quota()

                                                    _quota_cb[0] = _cb2

                                                    quota_dialog.open()

                                                ui.button(icon="edit", on_click=_open_quota_set2).props(

                                                    "flat round dense size=sm").classes("text-blue-600 shrink-0")





                    q_year_sel.on("update:model-value", lambda: asyncio.ensure_future(_reload_quota()))

                    await _reload_quota()



            # ── Tab: B→o cáo năm ─────────────────────────────────────────────

            if t_stats:

                with ui.tab_panel(t_stats):

                    _today_year = _dt_mod.date.today().year

                    with ui.row().classes("gap-3 mb-4 items-center"):

                        s_year_sel = ui.select(

                            {y: str(y) for y in range(_today_year - 2, _today_year + 2)},

                            label="Năm", value=_today_year,

                        ).classes("w-28")



                        async def _download_stats():

                            try:

                                content = await asyncio.to_thread(

                                    api.download, "/api/leaves/export/annual",
                                    params={"year": s_year_sel.value}

                                )

                                ui.download(content, f"bao_cao_tat_ca_don_nghi_phep_{s_year_sel.value}.xlsx")

                            except Exception as e:

                                _handle_api_error(e)



                        ui.button("Tải báo cáo Excel", icon="download", on_click=_download_stats).classes("bg-blue-700 text-white")

                        # Báo cáo NPBB — Phòng Tổng hợp chốt tổng gửi báo cáo (không phải
                        # từng cá nhân tự làm), quét dữ liệu đơn nghỉ phép bắt buộc trong
                        # năm đã chọn ở trên — xem export_npbb_batch() ở backend.
                        async def _download_npbb(mau: str):
                            try:
                                content = await asyncio.to_thread(
                                    api.download, "/api/leaves/export/npbb-batch",
                                    params={"year": s_year_sel.value, "mau": mau},
                                )
                                ui.download(content, f"bao_cao_npbb_mau{mau}_{s_year_sel.value}.docx")
                            except Exception as e:
                                _handle_api_error(e)

                        with ui.button("Báo cáo NPBB", icon="assignment").classes("bg-orange-700 text-white"):
                            with ui.menu():
                                ui.menu_item("Mẫu đăng ký (Mẫu 19 — gửi TCNS)", on_click=lambda: _download_npbb("19"))
                                ui.menu_item("Mẫu điều chỉnh (Mẫu 18 — nội bộ)", on_click=lambda: _download_npbb("18"))

                        # Mẫu đơn gốc (.docx) — Phòng Tổng hợp tải để in/phát cho ai cần
                        # điền tay, không qua bước điền dữ liệu (xem export_mau_don ở BE).
                        async def _download_mau_don(loai: str, fname: str):
                            try:
                                content = await asyncio.to_thread(
                                    api.download, "/api/leaves/export/mau-don",
                                    params={"loai": loai},
                                )
                                ui.download(content, fname)
                            except Exception as e:
                                _handle_api_error(e)

                        with ui.button("Mẫu đơn", icon="description").classes("bg-gray-600 text-white"):
                            with ui.menu():
                                ui.menu_item("Đơn xin nghỉ phép — Nhân viên",
                                             on_click=lambda: _download_mau_don("nv", "mau_don_nghi_phep_nhan_vien.docx"))
                                ui.menu_item("Đơn xin nghỉ phép — Trưởng/Phó phòng",
                                             on_click=lambda: _download_mau_don("tp", "mau_don_nghi_phep_truong_pho_phong.docx"))
                                ui.menu_item("Đơn xin nghỉ phép — Phó Giám đốc",
                                             on_click=lambda: _download_mau_don("pgd", "mau_don_nghi_phep_pho_giam_doc.docx"))
                                ui.menu_item("Đơn xin nghỉ phép — Giám đốc",
                                             on_click=lambda: _download_mau_don("gd", "mau_don_nghi_phep_giam_doc.docx"))
                                ui.separator()
                                ui.menu_item("Đăng ký nghỉ phép bắt buộc (NPBB)",
                                             on_click=lambda: _download_mau_don("npbb_dangky", "mau_don_dang_ky_npbb.docx"))
                                ui.menu_item("Điều chỉnh nghỉ phép bắt buộc (NPBB)",
                                             on_click=lambda: _download_mau_don("npbb_dieuchinh", "mau_don_dieu_chinh_npbb.docx"))



                    ui.label("Chọn năm và nhấn 'Tải báo cáo Excel' để xuất file tổng hợp phép. "
                             "Mục 'Mẫu đơn' tải file gốc dùng để dựng đơn thật, chỉ để tham khảo/in phát tay, "
                             "không tự điền dữ liệu.").classes("text-sm text-gray-500")



            # ── Tab: Khai báo hộ ─────────────────────────────────────────────

            if t_direct:

                with ui.tab_panel(t_direct):

                    # Load danh sách nhân viên

                    direct_staff_list = []

                    try:

                        direct_staff_list = await asyncio.to_thread(api.get, "/api/staff/")

                    except Exception:

                        direct_staff_list = []

                    direct_staff_list = direct_staff_list if isinstance(direct_staff_list, list) else []

                    direct_staff_opts  = {s["id"]: s["full_name"] for s in direct_staff_list}



                    _today_iso_d = _dt_mod.date.today().isoformat()
                    _drs_val = [""]   # ISO start date cho range thai_san/bao_hiem
                    _dre_val = [""]   # ISO end date cho range



                    ui.label("Khai báo nghỉ phép cho nhân viên khác (tạo đơn đã duyệt ngay).").classes("text-sm text-gray-500 mb-4")

                    ui.add_css(".q-date__header { display: none !important; }")



                    # ── Define helpers TRƯỚC để _submit có thể d→ng ──────────
                    # Nguồn lọc DUY NHẤT phải là declared_leaves gốc (bất biến trong
                    # vòng đời trang) — không dùng lại kết quả đã lọc lần trước làm
                    # nguồn cho lần lọc/"Xóa lọc" tiếp theo, tránh lọc chồng lọc.

                    # Placeholder containers → sẽ được assign sau khi render

                    _decl_refs = {"title": None, "container": None}



                    def _render_decl_table(leaves: list):

                        c = _decl_refs["container"]

                        t = _decl_refs["title"]

                        if c is None:

                            return

                        c.clear()

                        if t:

                            t.set_text(f"Đơn đã khai báo hộ ({len(leaves)})")

                        # Luôn xoá trước khi kiểm tra "không có đơn nào" — nếu không, lọc về
                        # 0 dòng sẽ return sớm và bỏ sót lần xoá này (xem _all_sel_checkboxes).
                        _export_sel.clear()

                        with c:

                            if not leaves:

                                ui.label("Chưa có đơn nào được khai báo.").classes("text-gray-500 text-sm")

                                return

                            _hc = "font-semibold text-red-800 text-xs shrink-0 border-r border-red-400 pr-2 mr-1"

                            _decl_row_cks: list = []

                            def _decl_select_all(e, _leaves=leaves):
                                for ck in _decl_row_cks:
                                    ck.set_value(e.value)
                                if e.value:
                                    _export_sel.update(dl["id"] for dl in _leaves)
                                else:
                                    for dl in _leaves: _export_sel.discard(dl["id"])

                            with ui.column().classes("w-full gap-0 border-2 border-gray-400 rounded"):

                                with ui.row().classes("w-full bg-red-50 border-b-2 border-red-400 px-3 py-2 items-center gap-0"):

                                    _all_sel_checkboxes.append(
                                        ui.checkbox(value=False, on_change=_decl_select_all).props("dense").classes("w-6 shrink-0 mr-2").tooltip("Chọn / Bỏ chọn tất cả")
                                    )

                                    ui.label("STT").classes(f"{_hc} w-8 text-center")

                                    ui.label("Ngày khai").classes(f"{_hc} w-20")

                                    ui.label("Nhân viên").classes(f"{_hc} w-32")

                                    ui.label("Phòng").classes(f"{_hc} w-32")

                                    ui.label("Người khai báo").classes(f"{_hc} w-32")

                                    ui.label("Loại").classes(f"{_hc} w-28")

                                    ui.label("Ngày nghỉ").classes("font-semibold text-red-800 text-xs flex-1")

                                    ui.label("").classes("w-8 shrink-0")

                                for _di, dl in enumerate(leaves, 1):

                                    with ui.row().classes("w-full bg-white border-b border-gray-100 px-3 py-1.5 items-center gap-0 hover:bg-purple-50"):

                                        def _on_decl_ck(e, l=dl["id"]):

                                            _export_sel.add(l) if e.value else _export_sel.discard(l)

                                        _dck = ui.checkbox(value=False, on_change=_on_decl_ck).props("dense").classes("w-6 shrink-0 mr-2")
                                        _decl_row_cks.append(_dck)
                                        _all_sel_checkboxes.append(_dck)

                                        ui.label(str(_di)).classes("text-xs w-8 shrink-0 text-center text-gray-500 border-r border-gray-400 pr-2 mr-1")

                                        ui.label((dl.get("created_at") or "")[:10]).classes("text-xs w-20 shrink-0 border-r border-gray-400 pr-2 mr-1 text-gray-500")

                                        ui.label(dl.get("staff_name") or "→").classes("text-xs w-32 shrink-0 truncate border-r border-gray-400 pr-2 mr-1")

                                        ui.label(dl.get("department_name") or "→").classes("text-xs w-32 shrink-0 truncate border-r border-gray-400 pr-2 mr-1")

                                        ui.label(dl.get("declarer_name") or "→").classes("text-xs w-32 shrink-0 truncate border-r border-gray-400 pr-2 mr-1")

                                        ui.label(_LEAVE_TYPE.get(dl.get("leave_type",""), dl.get("leave_type",""))).classes("text-xs w-28 shrink-0 truncate border-r border-gray-400 pr-2 mr-1")

                                        ui.label(_fmt_leave_dates(dl.get("start_date",""), dl.get("end_date",""), dl.get("spread_dates"))).classes("text-xs flex-1")

                                        def _del(did=dl["id"], sname=dl.get("staff_name","?")):

                                            with ui.dialog() as _ddlg, ui.card().classes("p-6 w-80"):

                                                ui.label("Xác nhận xóa").classes("text-lg font-bold text-red-900 mb-1")

                                                ui.label(f"Xóa đơn khai báo hộ của {sname}. Không thể hoàn tác.").classes("text-sm text-gray-600 mb-4")

                                                with ui.row().classes("gap-3 justify-end w-full"):

                                                    ui.button("Hủy", on_click=_ddlg.close).props("flat").classes("text-gray-500")

                                                    async def _do_del(_id=did, _dg=_ddlg):

                                                        try:

                                                            await asyncio.to_thread(api.delete, f"/api/leaves/{_id}")

                                                        except Exception as ex:

                                                            _dg.close()

                                                            ui.notify(f"Xóa thất bại: {ex}", type="negative", timeout=5000)

                                                            return

                                                        _dg.close()

                                                        ui.notify("✅ Đã xóa đơn khai báo hộ!", type="positive", timeout=3000)

                                                        app.storage.user["_leaves_goto"] = "khai_bao_ho"

                                                        ui.timer(1.5, lambda: ui.navigate.to("/leaves"), once=True)

                                                    ui.button("Xóa", icon="delete",

                                                              on_click=_do_del).classes("bg-red-600 text-white")

                                            _ddlg.open()

                                        ui.button(icon="delete", on_click=_del).props(

                                            "flat round dense size=sm").classes("text-red-500 shrink-0").tooltip("Xóa đơn")



                    # ── Form + bảng layout ────────────────────────────────────

                    with ui.row().classes("w-full gap-6 items-start flex-wrap"):

                      with ui.card().classes("p-6 w-96 shrink-0"):

                        d_staff  = ui.select(direct_staff_opts, label="Nhân viên").classes("w-full")

                        d_dates_wrap = ui.column().classes("w-full mt-2 gap-0")
                        with d_dates_wrap:
                            d_dates = ui.date(value=[]).props(f"multiple mask='YYYY-MM-DD' first-day-of-week='1' {_VI_LOCALE}").classes("w-full")
                            ui.label("Click chọn từng ngày → Click lại để bỏ chọn").classes("text-xs text-orange-500 mt-0.5")

                        import calendar as _cal_d
                        _d_today_ref = _dt_mod.date.today()
                        _d_rs_cur = [_d_today_ref.year, _d_today_ref.month]
                        _d_re_cur = [_d_today_ref.year, _d_today_ref.month]

                        d_range_wrap = ui.column().classes("w-full mt-2 gap-2")
                        d_range_wrap.set_visibility(False)
                        with d_range_wrap:
                            ui.label("Chọn khoảng thời gian nghỉ").classes("text-xs text-blue-600 font-medium -mb-1")
                            with ui.column().classes("w-full gap-0"):
                                with ui.row().classes("w-full items-center gap-1"):
                                    d_range_start = ui.input("Ngày bắt đầu", placeholder="DD/MM/YYYY").classes("flex-1")
                                    _d_rs_btn = ui.button(icon="calendar_month").props("flat round dense size=sm color=grey-7")
                                _d_rs_cal = ui.column().classes("w-full border border-gray-200 rounded p-2 bg-white mt-1")
                                _d_rs_cal.set_visibility(False)
                            with ui.column().classes("w-full gap-0 mt-1"):
                                with ui.row().classes("w-full items-center gap-1"):
                                    d_range_end = ui.input("Ngày kết thúc", placeholder="DD/MM/YYYY").classes("flex-1")
                                    _d_re_btn = ui.button(icon="calendar_month").props("flat round dense size=sm color=grey-7")
                                _d_re_cal = ui.column().classes("w-full border border-gray-200 rounded p-2 bg-white mt-1")
                                _d_re_cal.set_visibility(False)

                        def _d_rs_render():
                            _d_rs_cal.clear()
                            y, m = _d_rs_cur
                            with _d_rs_cal:
                                with ui.row().classes("w-full items-center justify-between mb-1"):
                                    ui.button(icon="chevron_left",  on_click=_d_rs_prev).props("flat round dense size=sm")
                                    ui.label(f"Tháng {m:02d}/{y}").classes("text-sm font-semibold text-gray-700")
                                    ui.button(icon="chevron_right", on_click=_d_rs_next).props("flat round dense size=sm")
                                with ui.row().classes("w-full gap-0"):
                                    for h in ["T2","T3","T4","T5","T6","T7","CN"]:
                                        ui.label(h).classes("text-xs text-center text-gray-500 w-[14.28%] py-0.5")
                                first_wd = _dt_mod.date(y, m, 1).weekday()
                                last_day = _cal_d.monthrange(y, m)[1]
                                today_d  = _dt_mod.date.today()
                                with ui.row().classes("w-full gap-0 flex-wrap"):
                                    for _ in range(first_wd):
                                        ui.label("").classes("w-[14.28%] h-7")
                                    for day in range(1, last_day + 1):
                                        ds = f"{y:04d}-{m:02d}-{day:02d}"; dobj = _dt_mod.date(y, m, day)
                                        sel = (ds == _drs_val[0]); is_td = (dobj == today_d); wknd = dobj.weekday() >= 5
                                        def _pick_d_rs(ds=ds):
                                            def _do():
                                                _drs_val[0] = ds
                                                d_range_start.value = f"{ds[8:10]}/{ds[5:7]}/{ds[0:4]}"
                                                _d_rs_cal.set_visibility(False); _d_rs_render()
                                            return _do
                                        with ui.element("div").classes("w-[14.28%] h-7 flex items-center justify-center"):
                                            if sel:
                                                ui.label(str(day)).classes("w-6 h-6 rounded-full bg-red-700 text-white text-xs font-bold flex items-center justify-center cursor-pointer").on("click", _pick_d_rs())
                                            elif is_td:
                                                ui.label(str(day)).classes("w-6 h-6 rounded-full ring-2 ring-red-500 text-red-600 text-xs font-bold flex items-center justify-center cursor-pointer hover:bg-red-50").on("click", _pick_d_rs())
                                            elif wknd:
                                                ui.label(str(day)).classes("w-6 h-6 rounded flex items-center justify-center text-xs text-blue-300 hover:bg-blue-50 cursor-pointer").on("click", _pick_d_rs())
                                            else:
                                                ui.label(str(day)).classes("w-6 h-6 rounded flex items-center justify-center text-xs text-gray-600 hover:bg-red-50 hover:text-red-700 cursor-pointer").on("click", _pick_d_rs())

                        def _d_rs_prev():
                            y, m = _d_rs_cur; _d_rs_cur[0], _d_rs_cur[1] = (y-1, 12) if m == 1 else (y, m-1); _d_rs_render()
                        def _d_rs_next():
                            y, m = _d_rs_cur; _d_rs_cur[0], _d_rs_cur[1] = (y+1, 1) if m == 12 else (y, m+1); _d_rs_render()
                        def _d_rs_toggle():
                            vis = not _d_rs_cal.visible; _d_rs_cal.set_visibility(vis)
                            if vis: _d_rs_render()
                        def _parse_drs():
                            txt = d_range_start.value.strip()
                            if not txt: _drs_val[0] = ""; return
                            try:
                                p = txt.replace("-", "/").split("/")
                                if len(p) != 3 or len(p[2]) != 4:
                                    raise ValueError("Định dạng phải là dd/mm/yyyy")
                                d_,mo,yr = int(p[0]),int(p[1]),int(p[2])
                                _dt_mod.date(yr, mo, d_)
                                _drs_val[0] = f"{yr:04d}-{mo:02d}-{d_:02d}"
                            except Exception: _drs_val[0] = ""
                        _d_rs_btn.on("click", _d_rs_toggle)
                        d_range_start.on("blur", _parse_drs)

                        def _d_re_render():
                            _d_re_cal.clear()
                            y, m = _d_re_cur
                            with _d_re_cal:
                                with ui.row().classes("w-full items-center justify-between mb-1"):
                                    ui.button(icon="chevron_left",  on_click=_d_re_prev).props("flat round dense size=sm")
                                    ui.label(f"Tháng {m:02d}/{y}").classes("text-sm font-semibold text-gray-700")
                                    ui.button(icon="chevron_right", on_click=_d_re_next).props("flat round dense size=sm")
                                with ui.row().classes("w-full gap-0"):
                                    for h in ["T2","T3","T4","T5","T6","T7","CN"]:
                                        ui.label(h).classes("text-xs text-center text-gray-500 w-[14.28%] py-0.5")
                                first_wd = _dt_mod.date(y, m, 1).weekday()
                                last_day = _cal_d.monthrange(y, m)[1]
                                today_d  = _dt_mod.date.today()
                                with ui.row().classes("w-full gap-0 flex-wrap"):
                                    for _ in range(first_wd):
                                        ui.label("").classes("w-[14.28%] h-7")
                                    for day in range(1, last_day + 1):
                                        ds = f"{y:04d}-{m:02d}-{day:02d}"; dobj = _dt_mod.date(y, m, day)
                                        sel = (ds == _dre_val[0]); is_td = (dobj == today_d); wknd = dobj.weekday() >= 5
                                        def _pick_d_re(ds=ds):
                                            def _do():
                                                _dre_val[0] = ds
                                                d_range_end.value = f"{ds[8:10]}/{ds[5:7]}/{ds[0:4]}"
                                                _d_re_cal.set_visibility(False); _d_re_render()
                                            return _do
                                        with ui.element("div").classes("w-[14.28%] h-7 flex items-center justify-center"):
                                            if sel:
                                                ui.label(str(day)).classes("w-6 h-6 rounded-full bg-red-700 text-white text-xs font-bold flex items-center justify-center cursor-pointer").on("click", _pick_d_re())
                                            elif is_td:
                                                ui.label(str(day)).classes("w-6 h-6 rounded-full ring-2 ring-red-500 text-red-600 text-xs font-bold flex items-center justify-center cursor-pointer hover:bg-red-50").on("click", _pick_d_re())
                                            elif wknd:
                                                ui.label(str(day)).classes("w-6 h-6 rounded flex items-center justify-center text-xs text-blue-300 hover:bg-blue-50 cursor-pointer").on("click", _pick_d_re())
                                            else:
                                                ui.label(str(day)).classes("w-6 h-6 rounded flex items-center justify-center text-xs text-gray-600 hover:bg-red-50 hover:text-red-700 cursor-pointer").on("click", _pick_d_re())

                        def _d_re_prev():
                            y, m = _d_re_cur; _d_re_cur[0], _d_re_cur[1] = (y-1, 12) if m == 1 else (y, m-1); _d_re_render()
                        def _d_re_next():
                            y, m = _d_re_cur; _d_re_cur[0], _d_re_cur[1] = (y+1, 1) if m == 12 else (y, m+1); _d_re_render()
                        def _d_re_toggle():
                            vis = not _d_re_cal.visible; _d_re_cal.set_visibility(vis)
                            if vis: _d_re_render()
                        def _parse_dre():
                            txt = d_range_end.value.strip()
                            if not txt: _dre_val[0] = ""; return
                            try:
                                p = txt.replace("-", "/").split("/")
                                if len(p) != 3 or len(p[2]) != 4:
                                    raise ValueError("Định dạng phải là dd/mm/yyyy")
                                d_,mo,yr = int(p[0]),int(p[1]),int(p[2])
                                _dt_mod.date(yr, mo, d_)
                                _dre_val[0] = f"{yr:04d}-{mo:02d}-{d_:02d}"
                            except Exception: _dre_val[0] = ""
                        _d_re_btn.on("click", _d_re_toggle)
                        d_range_end.on("blur", _parse_dre)

                        d_type   = ui.select({k: v for k, v in _LEAVE_TYPE.items()}, label="Loại nghỉ", value="annual").classes("w-full mt-2")

                        d_reason = ui.textarea("Lý do (tuỳ chọn)").classes("w-full mt-2").props("rows=2")
                        d_reason.set_visibility(False)

                        def _on_type_change(e):
                            lt = e.value
                            is_rng = lt in ("thai_san", "bao_hiem")
                            d_dates_wrap.set_visibility(not is_rng)
                            d_range_wrap.set_visibility(is_rng)
                            d_reason.set_visibility(lt == "other")

                        d_type.on_value_change(_on_type_change)



                        async def do_direct():

                            if not d_staff.value:
                                ui.notify("Vui lòng chọn nhân viên", type="warning"); return

                            lt = d_type.value
                            is_rng = lt in ("thai_san", "bao_hiem")
                            staff_name = direct_staff_opts.get(d_staff.value, "nhân viên")

                            if is_rng:
                                _parse_drs(); _parse_dre()
                                start_val, end_val = _drs_val[0], _dre_val[0]
                                if not start_val or not end_val:
                                    ui.notify("Vui lòng nhập ngày bắt đầu và ngày kết thúc (DD/MM/YYYY)", type="warning"); return
                                if end_val < start_val:
                                    ui.notify("Ngày kết thúc phải sau ngày bắt đầu", type="warning"); return
                                body = {"staff_id": d_staff.value, "start_date": start_val, "end_date": end_val,
                                        "leave_type": lt, "reason": d_reason.value or None}
                                confirm_lbl = f"Khai báo {_LEAVE_TYPE.get(lt, lt)} cho {staff_name} (từ {start_val} đến {end_val}). Đơn sẽ được duyệt ngay."
                            else:
                                raw = d_dates.value
                                if not raw:
                                    ui.notify("Vui lòng chọn ít nhất 1 ngày", type="warning"); return
                                dates = sorted(set(raw if isinstance(raw, list) else [raw]))
                                dates = [d[:10] for d in dates if d]
                                if not dates:
                                    ui.notify("Vui lòng chọn ít nhất 1 ngày", type="warning"); return
                                if lt == "other" and not (d_reason.value or "").strip():
                                    ui.notify("Vui lòng nhập lý do khi chọn loại Khác", type="warning"); return
                                body = {"staff_id": d_staff.value, "start_date": dates[0], "end_date": dates[-1],
                                        "spread_dates": dates, "leave_type": lt, "reason": d_reason.value or None}
                                confirm_lbl = f"Khai báo nghỉ cho {staff_name} ({len(dates)} ngày). Đơn sẽ được duyệt ngay."

                            # Inline dialog → không dùng shared _ask_confirm

                            with ui.dialog() as _dlg, ui.card().classes("p-6 w-96"):

                                ui.label("Xác nhận khai báo hộ").classes("text-lg font-bold text-red-900 mb-1")

                                ui.label(confirm_lbl).classes("text-sm text-gray-600 mb-4")

                                with ui.row().classes("gap-3 justify-end w-full"):

                                    ui.button("Hủy", on_click=_dlg.close).props("flat").classes("text-gray-500")

                                    def _on_direct_created(_rng=is_rng):
                                        # Đơn mới tạo phải phản ánh vào Dashboard/5 ô KPI/"Đơn của tôi"...
                                        # nhưng các dữ liệu đó chỉ fetch 1 lần lúc mở trang, không tự refetch
                                        # khi đổi tab nữa (xem _on_leave_tab_change) — phải reload thật qua
                                        # _nav_pending() giống hệt cơ chế duyệt/từ chối, quay lại đúng tab
                                        # Khai báo hộ sau khi reload xong.
                                        ui.notify("✅ Khai báo hộ thành công!", type="positive", timeout=4000)

                                        d_staff.value = None
                                        if _rng:
                                            _drs_val[0] = ""; _dre_val[0] = ""
                                            d_range_start.value = ""; d_range_end.value = ""
                                        else:
                                            d_dates.value = None

                                        d_type.value = "annual"
                                        d_dates_wrap.set_visibility(True)
                                        d_range_wrap.set_visibility(False)

                                        d_reason.value = ""

                                        d_reason.set_visibility(False)

                                        _nav_pending()

                                    async def _send_direct(_b):
                                        try:
                                            await asyncio.to_thread(api.post, "/api/leaves/direct", _b)
                                        except api.QuotaExceededBorrowError as e:
                                            # Vượt hạn mức năm nay nhưng năm sau còn đủ chỗ ứng — hỏi
                                            # xác nhận thay vì chặn cứng, xem _check_quota_or_borrow.
                                            async def _retry_with_borrow(_b2=_b):
                                                _b2["confirm_borrow_next_year"] = True
                                                await _send_direct(_b2)
                                            _ask_confirm(
                                                "Vượt hạn mức phép",
                                                f"Đơn khai báo hộ đã vượt quá hạn mức ngày nghỉ phép năm "
                                                f"{e.year} (còn lại {e.remaining:.0f} ngày). Bạn có muốn "
                                                f"tiếp tục ứng trước {e.borrow_days:.0f} ngày phép của năm "
                                                f"{e.next_year} không?",
                                                _retry_with_borrow, "Đồng ý ứng phép", "bg-orange-600",
                                            )
                                            return
                                        except Exception as e:
                                            if not _handle_api_error(e):
                                                ui.notify(f"Khai báo thất bại: {e}", type="negative", timeout=5000)
                                            return
                                        _on_direct_created()

                                    async def _on_confirm(_b=body, _d=_dlg):
                                        _d.close()
                                        await _send_direct(_b)

                                    ui.button("Khai báo", icon="check",

                                              on_click=_on_confirm).classes("bg-purple-700 text-white")

                            _dlg.open()



                        ui.button("Khai báo", icon="check",

                                  on_click=do_direct).classes("bg-purple-700 text-white mt-4")



                      # ── Cột phải: bảng đơn đã khai báo hộ ──────────────────

                      with ui.column().classes("flex-1 min-w-64"):

                        # Filter bảng khai báo hộ → giống style Dashboard

                        _df_type_opts = {"": "Tất cả loại", **_LEAVE_TYPE}

                        _df_depts     = sorted({s.get("department_name") or "" for s in direct_staff_list if s.get("department_name")})

                        _df_dept_opts = {"": "Tất cả phòng", **{d: d for d in _df_depts}}

                        with ui.card().classes("w-full p-4 mb-3 border-2 border-red-800 rounded-lg"):

                            ui.label("Bộ lọc tìm kiếm").classes("text-xs font-bold text-red-800 uppercase mb-2")

                            with ui.row().classes("gap-3 flex-wrap items-end"):

                                _df_name = ui.input("Tìm theo tên").classes("w-40").props("dense clearable")

                                _df_type = ui.select(_df_type_opts, value="", label="Loại nghỉ").classes("w-36").props("dense")

                                _df_dept = ui.select(_df_dept_opts, value="", label="Phòng").classes("w-40").props("dense")

                                with ui.input("Ngày nghỉ từ").classes("w-36").props("dense clearable readonly") as _df_from:

                                    with _df_from.add_slot("append"):

                                        ui.icon("event").classes("cursor-pointer").on("click", lambda: _dcal_from.open())

                                    with ui.menu() as _dcal_from:

                                        ui.date(mask="DD/MM/YYYY").props(f'{_OPT_ALL} first-day-of-week="1"').bind_value(_df_from)

                                with ui.input("đến ngày").classes("w-36").props("dense clearable readonly") as _df_to:

                                    with _df_to.add_slot("append"):

                                        ui.icon("event").classes("cursor-pointer").on("click", lambda: _dcal_to.open())

                                    with ui.menu() as _dcal_to:

                                        ui.date(mask="DD/MM/YYYY").props(f'{_OPT_ALL} first-day-of-week="1"').bind_value(_df_to)

                            with ui.row().classes("gap-3 mt-2 items-center"):

                                _df_count = ui.label("").classes("text-sm font-medium text-red-800 flex-1")

                                ui.button("Tìm kiếm", icon="search",

                                          on_click=lambda: _apply_decl_filter()).classes("bg-red-700 text-white")

                                ui.button("Xóa lọc", icon="clear",

                                          on_click=lambda: _reset_decl_filter()).props("flat").classes("text-gray-500")



                        _decl_refs["title"]     = ui.label("").classes("font-bold text-gray-700 text-sm mb-2")

                        _decl_refs["container"] = ui.column().classes("w-full gap-0")



                        def _parse_decl_date(s):

                            from datetime import date as _dd

                            s = (s or "").strip()

                            if not s: return None

                            try:

                                if "/" in s:

                                    p = s.split("/")

                                    return _dd(int(p[2]), int(p[1]), int(p[0]))

                                return _dd.fromisoformat(s[:10])

                            except Exception:

                                return None



                        def _apply_decl_filter():

                            name_q  = (_df_name.value or "").strip().lower()

                            type_q  = _df_type.value or ""

                            dept_q  = _df_dept.value or ""

                            from_d  = _parse_decl_date(_df_from.value)

                            to_d    = _parse_decl_date(_df_to.value)

                            src = declared_leaves

                            filtered_d = []

                            for dl in src:

                                if name_q and name_q not in (dl.get("staff_name") or "").lower():

                                    continue

                                if type_q and dl.get("leave_type") != type_q:

                                    continue

                                if dept_q and (dl.get("department_name") or "") != dept_q:

                                    continue

                                if from_d or to_d:

                                    # Đơn ngày lẻ (spread_dates) — so đúng các ngày thực tế
                                    # thay vì envelope start/end, khớp _pf_apply/_apply_filter.
                                    sd = dl.get("spread_dates")

                                    dates = [d for d in (_parse_decl_date(x) for x in sd) if d] if sd else []

                                    if dates:

                                        if not any((not from_d or d >= from_d) and (not to_d or d <= to_d) for d in dates):

                                            continue

                                    else:

                                        s = _parse_decl_date(dl.get("start_date", ""))

                                        e = _parse_decl_date(dl.get("end_date", ""))

                                        if s and e:

                                            if from_d and e < from_d:

                                                continue

                                            if to_d and s > to_d:

                                                continue

                                filtered_d.append(dl)

                            _df_count.set_text(f"{len(filtered_d)} / {len(src)} đơn")

                            _render_decl_table(filtered_d)



                        def _reset_decl_filter():

                            _df_name.value = ""

                            _df_type.value = ""

                            _df_dept.value = ""

                            _df_from.value = ""

                            _df_to.value   = ""

                            src = declared_leaves

                            _df_count.set_text(f"{len(src)} / {len(src)} đơn")

                            _render_decl_table(src)



                        _df_name.on("keydown.enter", lambda _: _apply_decl_filter())

                        _df_from.on("keydown.enter", lambda _: _apply_decl_filter())

                        _df_to.on("keydown.enter",   lambda _: _apply_decl_filter())



                        _render_decl_table(declared_leaves)

                        # Hiện count ngay từ đầu

                        _df_count.set_text(f"{len(declared_leaves)} / {len(declared_leaves)} đơn")

        # ── Bung sẵn chi tiết đơn được chỉ đích danh từ sidebar ───────────────
        # Đặt cuối hàm vì open_detail vẽ vào drawer_container, mà container đó
        # phải dựng xong trước. Không tìm thấy đơn (vừa bị người khác duyệt) thì
        # im lặng ở lại tab đã chọn — vẫn là màn hình thao tác đúng.
        _focus_id = app.storage.user.pop("_leaves_focus", None)
        if _focus_id:
            _focus_lv = next((lv for lv in pending_leaves if lv.get("id") == _focus_id), None)
            if _focus_lv:
                await open_detail(_focus_lv)



