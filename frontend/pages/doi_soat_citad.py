"""Trang Đối soát lệnh CITAD (NHNN) ↔ IPCAS (Agribank) — Phòng Thanh toán.

Port từ `citad-fixed/DoiSoatCITAD.py` (tkinter, 1 màn hình không tab).
Bám sát pattern `frontend/pages/swift_recon.py`: upload nhiều file (CITAD,
IPCAS, Hub ngoại tệ) → gọi backend đối soát trong RAM → giữ kết quả trong
`state` của phiên làm việc → lọc/hiển thị bằng Python thuần, KHÔNG gọi lại
backend mỗi lần đổi bộ lọc — chỉ gọi backend khi: đối soát, và khi xuất Excel.

4 nhóm lọc (map từ radio button gốc `all/only_citad/only_ipcas/lech_trang_thai`)
+ ô tìm kiếm tự do trên mọi cột (giống thanh search gốc).
"""
import asyncio
import datetime
import hashlib

from nicegui import ui
import frontend.api_client as api
from frontend.shared import _sidebar, _content_area, _card, _require_auth, _handle_api_error
from backend.services.doi_soat_citad.exporters import STATUS_LBL


def _date_filter_input(label: str):
    """Ô lọc theo ngày — RỖNG mặc định ("không giới hạn"). Cùng pattern với
    `_date_filter_input` ở frontend/pages/doi_chieu_citad.py (không import
    chung vì đó là hàm nội bộ module, không phải tiện ích trong shared.py)."""
    with ui.input(label, value="").props("dense outlined clearable").classes("w-44") as date_input:
        with date_input.add_slot("append"):
            ui.icon("edit_calendar").on("click", lambda: menu.open()).classes("cursor-pointer")
        with ui.menu() as menu:
            ui.date(mask="DD/MM/YYYY", on_change=menu.close).bind_value(date_input)
    return date_input


def _navy_header(title: str, subtitle: str = ""):
    """Thanh tiêu đề nền xanh navy đậm, chữ trắng — theo mẫu banner người
    dùng gửi (ảnh Kanban Board), thay cho `_page_header()` dùng chung ở
    frontend/shared.py (chỉ đổi RIÊNG ở trang này, không đụng shared.py)."""
    with ui.column().classes("w-full bg-blue-950 rounded-2xl px-6 py-4 mb-4 gap-0.5"):
        ui.label(title).classes("text-xl font-bold text-white tracking-wide")
        if subtitle:
            ui.label(subtitle).classes("text-blue-200 text-sm")


def _date_picker_input(label: str, initial: str = None):
    """Ô nhập ngày dd/mm/yyyy kèm icon mở lịch chọn — QDate tự khoanh viền
    ngày hôm nay, không cần cấu hình thêm."""
    initial = initial or datetime.date.today().strftime('%d/%m/%Y')
    with ui.input(label, value=initial).props('dense outlined').classes('w-44') as date_input:
        with date_input.add_slot('append'):
            ui.icon('edit_calendar').on('click', lambda: menu.open()).classes('cursor-pointer')
        with ui.menu() as menu:
            ui.date(value=initial, mask='DD/MM/YYYY', on_change=menu.close).bind_value(date_input)
    return date_input

STATUS_COLOR = {
    "only_citad": "text-red-600", "only_ipcas": "text-blue-600",
    "only_hub": "text-blue-600", "lech_trang_thai": "text-orange-600", "both": "text-green-700",
    "dup_citad": "text-orange-600",
}

FILTERS = [
    ("Tất cả", None),
    ("Chỉ CITAD", ("only_citad", "dup_citad")),
    ("Chỉ Agribank (IPCAS/Hub)", ("only_ipcas", "only_hub")),
    ("Lệch trạng thái", ("lech_trang_thai",)),
]

# Đổi 09/09/2026 theo yêu cầu Phòng Thanh toán (đồng bộ với
# doi_soat_citad/exporters.py::HEADERS vừa sửa): bỏ "Dịch vụ" (suy được từ
# "Loại GD"), thêm "Số RefHub" — đặt SAU "Trạng thái" (cuối nhóm dữ liệu
# Agribank/IPCAS, đúng nguồn — refhub là dữ liệu gốc từ file IPCAS, không
# phải CITAD) thay vì đúng chỗ cũ của "Dịch vụ" (giữa nhóm CITAD). Bảng
# trên màn hình không có dải nhóm tiêu đề như Excel nên đổi vị trí ở đây
# an toàn tuyệt đối — cols dựng từ list này theo TÊN field, không theo
# chỉ số vị trí (xem `cols = [...]` bên dưới).
DISPLAY_COLS = [
    ("stt", "STT"), ("status_lbl", "Kết quả"), ("loai", "Loại GD"), ("chieu_lbl", "Chiều"),
    ("so_gd", "Số GD (CITAD)"), ("key_agri", "Số GD (Agribank)"),
    ("so_tien", "Số tiền"), ("loai_tien", "Loại tiền"), ("ngay", "Ngày GD"),
    ("nh_nhan", "Ngân hàng"), ("trang_thai", "Trạng thái"), ("refhub", "Số RefHub"),
    ("cong", "Ghi chú"),
]


@ui.page("/doi_soat_citad")
async def doi_soat_citad_page():
    if not _require_auth():
        return
    if not api.has_feature("menu.doi_soat_citad"):
        ui.navigate.to("/home")
        return

    state = {
        "citad_files": [],   # list[(filename, bytes)]
        "ipcas_files": [],
        "hub_files": [],
        "lech": None,        # list[dict] sau khi đối soát
        "n_khop": 0,
        "khop_rows": [],     # chi tiết từng dòng đã khớp — chỉ để "Xuất tất cả lệnh"
        "ngay_cham": "",
    }
    history_refresh = {"fn": None}

    with ui.row().classes("w-full"):
        await _sidebar("doi_soat_citad")
        with _content_area():
            _navy_header(
                "ĐỐI SOÁT CHÊNH LỆCH CITAD CUỐI NGÀY",
                "Đối soát lệnh chuyển tiền giữa CITAD (NHNN) và IPCAS (Agribank) theo ngày chấm",
            )

            with ui.tabs().classes("w-full") as tabs:
                tab_input = ui.tab("1. Tải file & Đối soát")
                tab_result = ui.tab("2. Kết quả")
                tab_hist = ui.tab("Lịch sử")

            with ui.tab_panels(tabs, value=tab_input).classes("w-full"):
                _build_input_panel(tab_input, state, tabs, tab_result, history_refresh)
                _build_result_panel(tab_result, state)
                _build_history_panel(tab_hist, history_refresh)


def _build_input_panel(tab, state, tabs, result_tab, history_refresh):
    with ui.tab_panel(tab):
        with _card("Ngày chấm"):
            with ui.row().classes("m-4 items-center gap-3"):
                ngay_input = _date_picker_input("Ngày chấm")

                def do_reset():
                    for clear_fn in upload_clears:
                        clear_fn()
                    ngay_input.value = datetime.date.today().strftime('%d/%m/%Y')
                    state["lech"] = None
                    state["n_khop"] = 0
                    state["khop_rows"] = []
                    state["ngay_cham"] = ""
                    msg_area.clear()
                    if "render" in state:
                        state["render"]()
                    ui.notify("Đã reset — sẵn sàng phiên chấm mới", type="info")

                def confirm_reset():
                    with ui.dialog() as dlg, ui.card():
                        ui.label("Xác nhận reset dữ liệu?").classes("text-lg font-bold text-red-600")
                        ui.label(
                            "Toàn bộ file đã chọn (CITAD/IPCAS/Hub) và kết quả đối soát hiện tại "
                            "sẽ bị xoá để bắt đầu phiên chấm mới. Hành động này không hoàn tác được."
                        ).classes("text-sm text-gray-700")
                        with ui.row().classes("mt-3 gap-2 justify-end w-full"):
                            ui.button("Huỷ", on_click=dlg.close).props("dense outline")

                            def _confirm():
                                dlg.close()
                                do_reset()

                            ui.button("Reset", on_click=_confirm).classes("bg-red-600 text-white").props("dense")
                    dlg.open()

                ui.button("Reset", icon="restart_alt", on_click=confirm_reset).props(
                    "dense outline"
                ).classes("text-red-600")

        with _card("Tải lên file"):
            with ui.grid(columns=3).classes("w-full gap-6 p-4"):
                upload_clears = [
                    _upload_column("File CITAD (.xls/.xlsx/.zip)", ".xls,.xlsx,.zip", state, "citad_files"),
                    _upload_column("File IPCAS (.csv/.txt/.zip)", ".csv,.txt,.zip", state, "ipcas_files"),
                    _upload_column("File Hub ngoại tệ (.xls/.xlsx, tuỳ chọn)", ".xls,.xlsx", state, "hub_files"),
                ]

        msg_area = ui.column().classes("px-4")
        btn = ui.button("Bắt đầu đối soát", icon="compare_arrows").classes("bg-red-800 text-white m-4")

        async def do_reconcile():
            if not state["citad_files"] or not state["ipcas_files"]:
                ui.notify("Cần ít nhất 1 file CITAD và 1 file IPCAS", type="warning")
                return
            if not ngay_input.value:
                ui.notify("Vui lòng nhập ngày chấm", type="warning")
                return
            btn.props("loading")
            msg_area.clear()
            try:
                files = []
                for fname, raw in state["citad_files"]:
                    files.append(("citad_files", (fname, raw, "application/octet-stream")))
                for fname, raw in state["ipcas_files"]:
                    files.append(("ipcas_files", (fname, raw, "application/octet-stream")))
                for fname, raw in state["hub_files"]:
                    files.append(("hub_files", (fname, raw, "application/octet-stream")))
                data = await asyncio.to_thread(
                    api.post_upload, "/api/doi-soat-citad/reconcile", files, {"ngay_cham": ngay_input.value}
                )
                state["lech"] = data["lech"]
                state["n_khop"] = data["n_khop"]
                state["khop_rows"] = data.get("khop_rows", [])
                state["ngay_cham"] = ngay_input.value
                with msg_area:
                    ui.label("Đối soát xong — xem kết quả ở tab tương ứng.").classes("text-green-700")
                    warnings = data.get("parse_warnings") or []
                    if warnings:
                        # 1 phần file lỗi nhưng vẫn còn file khác đọc được nên
                        # backend không chặn hẳn (422) — kết quả vẫn ra nhưng
                        # THIẾU dữ liệu từ (các) file lỗi, phải cảnh báo rõ,
                        # không để người dùng tưởng đối soát đầy đủ.
                        ui.label(
                            f"⚠ {len(warnings)} file bị lỗi khi đọc, kết quả có thể THIẾU dữ liệu:"
                        ).classes("text-orange-600 font-bold mt-1")
                        for w in warnings:
                            ui.label(f"• {w}").classes("text-orange-600 text-sm")
                if not data.get("history_saved", True):
                    ui.notify(
                        f"Đối soát xong nhưng LƯU LỊCH SỬ bị lỗi: {data.get('history_error')}",
                        type="warning", multi_line=True, timeout=0, close_button=True,
                    )
                elif history_refresh.get("fn"):
                    await history_refresh["fn"]()
                if "render" in state:
                    state["render"]()
                tabs.set_value(result_tab)
            except Exception as e:
                if _handle_api_error(e):
                    return
                with msg_area:
                    ui.label(f"Lỗi đối soát: {e}").classes("text-red-600")
            finally:
                btn.props(remove="loading")

        btn.on("click", do_reconcile)


def _upload_column(label, accept, state, key):
    with ui.column().classes("gap-1 border-2 border-red-800 rounded-2xl p-4"):
        ui.label(label).classes("text-sm font-medium")
        status = ui.label("Chưa chọn file nào").classes("text-gray-500 text-xs")
        file_rows_area = ui.column().classes("gap-0.5 mt-1")
        # Song song với state[key] (name, bytes) — chỉ để phát hiện + hiển thị
        # file trùng NỘI DUNG (hash SHA-256 của toàn bộ byte), KHÔNG dựa vào
        # tên file — người dùng có thể lỡ chọn cùng 1 file gốc 2 lần dưới 2
        # tên khác nhau (VD tải lại/đổi tên bản sao) mà không nhận ra.
        entries = []

        def render_rows():
            file_rows_area.clear()
            with file_rows_area:
                for ent in entries:
                    if ent["dup"]:
                        ui.label(f"⚠ {ent['name']} — TRÙNG NỘI DUNG với file khác trong nhóm này").classes(
                            "text-xs text-red-600 font-bold"
                        )
                    else:
                        ui.label(ent["name"]).classes("text-xs text-gray-500")

        async def on_upload(e):
            # Đọc file (I/O) + băm SHA-256 (CPU) đều là việc đồng bộ — chạy
            # thẳng trong handler sẽ chặn event loop của tiến trình frontend
            # DÙNG CHUNG cho mọi người dùng đang mở web, không riêng trang
            # này (đúng khuôn mẫu asyncio.to_thread đã quy định trong
            # DESIGN.md). File càng lớn/càng nhiều file liên tiếp thì càng
            # khựng rõ cho người khác.
            def _read_and_hash():
                data = e.content.read()
                return data, hashlib.sha256(data).hexdigest()
            content, file_hash = await asyncio.to_thread(_read_and_hash)
            dup_with = [ent["name"] for ent in entries if ent["hash"] == file_hash]

            state[key].append((e.name, content))
            entries.append({"name": e.name, "hash": file_hash, "dup": bool(dup_with)})

            if dup_with:
                # Đánh dấu ĐỎ cả file cũ lẫn file mới (không chỉ file vừa chọn) —
                # người dùng cần thấy rõ CẢ 2 bản đang trùng nhau để tự quyết định
                # xoá bớt, không tự động loại bỏ thay người dùng.
                for ent in entries:
                    if ent["hash"] == file_hash:
                        ent["dup"] = True
                with ui.dialog() as dlg, ui.card().classes("max-w-md"):
                    ui.label("⚠ Phát hiện file trùng nội dung").classes("text-lg font-bold text-red-600")
                    ui.label(
                        f'File "{e.name}" có NỘI DUNG GIỐNG Y HỆT (từng byte) với file đã chọn trước đó '
                        f'trong nhóm "{label}" — dù tên file khác nhau. Có thể bạn đã lỡ chọn trùng 1 file, '
                        f'khiến số liệu bị tính 2 lần khi đối soát. Các file đang trùng nhau:'
                    ).classes("text-sm text-gray-700")
                    for n in dup_with + [e.name]:
                        ui.label(f"• {n}").classes("text-sm text-red-600 font-mono")
                    ui.button("Đã hiểu", on_click=dlg.close).classes("bg-red-600 text-white mt-3")
                dlg.open()

            render_rows()
            status.text = f"Đã chọn {len(state[key])} file"
            status.classes(remove="text-gray-500", add="text-green-700")

        uploader = ui.upload(multiple=True, auto_upload=True, on_upload=on_upload).props(
            f'accept="{accept}" flat dense label="Chọn file"'
        ).classes("w-full")

        def clear():
            state[key] = []
            entries.clear()
            file_rows_area.clear()
            status.text = "Chưa chọn file nào"
            status.classes(remove="text-green-700", add="text-gray-500")
            # state[key] chỉ là danh sách phía Python — bản thân ui.upload (QUploader)
            # giữ RIÊNG 1 hàng đợi file phía client, không tự xoá theo. Không gọi
            # .reset() thì danh sách file (kèm dấu tick, % tải) vẫn hiện nguyên trên
            # UI dù state đã rỗng — đúng lỗi "ấn Xoá không xoá được" đã gặp.
            uploader.reset()

        ui.button("Xoá file đã chọn", on_click=clear).props("dense outline size=sm")

        return clear


def _build_result_panel(tab, state):
    with ui.tab_panel(tab):
        stats_area = ui.row().classes("w-full gap-3 flex-wrap mb-3")
        filter_row = ui.row().classes("w-full items-center gap-3 flex-wrap")
        table_area = ui.column().classes("w-full")
        export_row = ui.row().classes("gap-3 mt-3")

        current_view = {"rows": None}
        search_input = {"widget": None}
        active_filter = {"idx": 0}
        # Kết quả đối soát có thể lên tới hàng trăm nghìn dòng (đúng bản chất
        # nghiệp vụ — đối soát cả ngày giao dịch) — dồn hết vào 1 lần
        # ui.table(rows=...) từng làm TREO CỨNG cả trang (gửi + render toàn
        # bộ dòng cùng lúc qua websocket), kể cả không chuyển được tab khác.
        # Cắt trang phía Python trước khi đưa vào ui.table — mỗi lần chỉ gửi
        # đúng 1 trang.
        PAGE_SIZE = 200
        page_state = {"num": 1}

        def render():
            stats_area.clear()
            filter_row.clear()
            table_area.clear()
            export_row.clear()

            lech = state["lech"]
            with stats_area:
                if lech is None:
                    ui.label("Chưa có dữ liệu — vui lòng đối soát ở tab '1. Tải file & Đối soát' trước.").classes(
                        "text-gray-500"
                    )
                    return
                n_khop = state["n_khop"]
                n_only_citad = sum(1 for r in lech if r.get("status") in ("only_citad", "dup_citad"))
                n_only_agri = sum(1 for r in lech if r.get("status") in ("only_ipcas", "only_hub"))
                n_lech_tt = sum(1 for r in lech if r.get("status") == "lech_trang_thai")
                n_total = n_khop + len(lech)
                for lbl, val, bg, border, text in [
                    ("TỔNG LỆNH", n_total, "bg-slate-50", "border-slate-400", "text-slate-800"),
                    ("KHỚP", n_khop, "bg-emerald-50", "border-emerald-500", "text-emerald-700"),
                    ("CHỈ CITAD", n_only_citad, "bg-red-50", "border-red-500", "text-red-600"),
                    ("CHỈ AGRIBANK", n_only_agri, "bg-blue-50", "border-blue-500", "text-blue-600"),
                    ("LỆCH TRẠNG THÁI", n_lech_tt, "bg-amber-50", "border-amber-500", "text-orange-600"),
                ]:
                    with ui.card().classes(
                        f"px-4 py-2 min-w-[150px] rounded-xl shadow-sm border-l-4 {border} {bg}"
                    ):
                        ui.label(lbl).classes("text-xs font-medium text-gray-500")
                        ui.label(f"{val:,}").classes(f"text-xl font-bold {text}")

            if lech is None:
                return

            filter_buttons = []

            def _update_filter_buttons():
                for i, btn in enumerate(filter_buttons):
                    if i == active_filter["idx"]:
                        btn.props(remove="outline", add="unelevated")
                    else:
                        btn.props(remove="unelevated", add="outline")

            with filter_row:
                for i, (lbl, _statuses) in enumerate(FILTERS):
                    def _select(i=i):
                        active_filter["idx"] = i
                        page_state["num"] = 1  # đổi bộ lọc -> quay về trang 1, tránh trang trống
                        _update_filter_buttons()
                        render_table()
                    btn = ui.button(lbl, on_click=_select).props(
                        f"{'unelevated' if active_filter['idx'] == i else 'outline'} dense"
                    )
                    filter_buttons.append(btn)
                # debounce=300: kết quả có thể tới hàng trăm nghìn dòng — mỗi
                # lần lọc phải quét lại toàn bộ danh sách phía Python (đồng
                # bộ, chặn event loop dùng chung). Không debounce thì gõ mỗi
                # ký tự lại quét 1 lần, gõ nhanh dồn lại gây khựng cho cả
                # server. Quasar tự delay 300ms sau khi ngừng gõ mới bắn
                # update:model-value, không cần tự viết timer.
                search_input["widget"] = ui.input("Tìm kiếm...").props(
                    "dense outlined clearable debounce=300"
                ).classes("w-64")

                def _on_search(e):
                    page_state["num"] = 1
                    render_table()

                search_input["widget"].on("update:model-value", _on_search)

            def render_table():
                table_area.clear()
                _, statuses = FILTERS[active_filter["idx"]]
                view = lech if statuses is None else [r for r in lech if r.get("status") in statuses]
                q = (search_input["widget"].value or "").strip().lower() if search_input["widget"] else ""
                rows = []
                for i, r in enumerate(view, start=1):
                    row = {
                        "stt": i,
                        "status_lbl": STATUS_LBL.get(r.get("status"), r.get("status")),
                        "loai": (r.get("loai") or "").upper(),
                        "chieu_lbl": "Đi" if r.get("chieu") == "di" else "Đến",
                        "so_gd": r.get("so_gd") or "",
                        "key_agri": r.get("key_agri") or "",
                        "so_tien": r.get("so_tien") or 0,
                        "loai_tien": r.get("loai_tien") or "VNĐ",
                        "ngay": r.get("ngay") or "",
                        "nh_nhan": r.get("nh_nhan") or "",
                        "trang_thai": r.get("trang_thai") or "",
                        "refhub": r.get("refhub") or "",
                        # Ưu tiên ghi_chu tường minh (vd. phát hiện dup) nếu có,
                        # không thì mới rơi về "Cổng X" mặc định.
                        "cong": r.get("ghi_chu") or (f"Cổng {r['cong']}" if r.get("cong") else ""),
                    }
                    if q and q not in " ".join(str(v).lower() for v in row.values()):
                        continue
                    rows.append(row)

                # Kết quả có thể tới hàng trăm nghìn dòng — CẮT TRANG trước khi
                # đưa vào ui.table(), không đẩy nguyên cả danh sách vào 1 lần
                # (xem ghi chú PAGE_SIZE ở đầu hàm) — mỗi lần chỉ gửi/render
                # đúng PAGE_SIZE dòng, giữ trang luôn phản hồi được.
                total = len(rows)
                n_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
                if page_state["num"] > n_pages:
                    page_state["num"] = n_pages
                start = (page_state["num"] - 1) * PAGE_SIZE
                page_rows = rows[start:start + PAGE_SIZE]

                with table_area:
                    with ui.row().classes("w-full items-center justify-between mb-1"):
                        ui.label(
                            f"Hiển thị {len(page_rows)}/{total} dòng theo bộ lọc hiện tại "
                            f"— trang {page_state['num']}/{n_pages}."
                        ).classes("text-gray-500 text-sm")
                        with ui.row().classes("gap-1 items-center"):
                            def _prev_page():
                                if page_state["num"] > 1:
                                    page_state["num"] -= 1
                                    render_table()

                            def _next_page():
                                if page_state["num"] < n_pages:
                                    page_state["num"] += 1
                                    render_table()

                            ui.button(icon="chevron_left", on_click=_prev_page).props(
                                "dense flat size=sm" + ("" if page_state["num"] > 1 else " disable")
                            )
                            ui.button(icon="chevron_right", on_click=_next_page).props(
                                "dense flat size=sm" + ("" if page_state["num"] < n_pages else " disable")
                            )
                    cols = [
                        {
                            "name": k, "label": lbl, "field": k,
                            "align": "center", "sortable": True,
                            # field vẫn giữ SỐ THÔ (để sắp xếp đúng thứ tự số học) —
                            # :format là hàm JS Quasar dùng RIÊNG để hiển thị, có dấu
                            # phẩy ngăn cách hàng nghìn giống bảng Đối chiếu CITAD.
                            **({":format": "val => val ? val.toLocaleString('en-US') : val"} if k == "so_tien" else {}),
                        }
                        for k, lbl in DISPLAY_COLS
                    ]
                    with ui.table(columns=cols, rows=page_rows, row_key="stt").props(
                        'bordered separator="cell" table-header-class="bg-blue-900 text-white"'
                    ).classes("w-full"):
                        pass
                    current_view["rows"] = rows

            render_table()

            # Cả 2 nút đều khoá lại + quay vòng trong lúc chờ: sinh Excel phải
            # xếp hàng chờ suất run_heavy() dùng chung cả backend, người dùng
            # không thấy gì nhúc nhích sẽ bấm lại, mỗi lượt bấm lại chiếm thêm
            # một suất và tự làm chính mình chậm thêm.
            async def do_export():
                btn_export.props("loading")
                try:
                    payload = {"ngay_cham": state["ngay_cham"], "n_khop": state["n_khop"], "lech": state["lech"]}
                    content = await asyncio.to_thread(api.post_download, "/api/doi-soat-citad/export", payload)
                    ui.download(content, f"DoiSoat_CITAD_IPCAS_{state['ngay_cham'].replace('/', '-')}.xlsx")
                except Exception as e:
                    if _handle_api_error(e):
                        return
                    ui.notify(f"Lỗi: {e}", type="negative")
                finally:
                    btn_export.props(remove="loading")

            async def do_export_all():
                btn_export_all.props("loading")
                try:
                    payload = {
                        "ngay_cham": state["ngay_cham"],
                        "lech": state["lech"],
                        "khop_rows": state["khop_rows"],
                    }
                    # timeout 300s thay cho 60s mặc định: file "tất cả lệnh" có
                    # thể tới ~38.000 dòng (~5,8 giây sinh file) và còn phải chờ
                    # suất run_heavy() — 4 người bấm cùng lúc là nối đuôi nhau
                    # vì openpyxl giữ GIL, không chạy song song thật.
                    content = await asyncio.to_thread(
                        api.post_download, "/api/doi-soat-citad/export-all", payload, 300
                    )
                    ui.download(content, f"DoiSoat_CITAD_IPCAS_TatCa_{state['ngay_cham'].replace('/', '-')}.xlsx")
                except Exception as e:
                    if _handle_api_error(e):
                        return
                    ui.notify(f"Lỗi: {e}", type="negative")
                finally:
                    btn_export_all.props(remove="loading")

            with export_row:
                btn_export = ui.button(
                    "Xuất file Excel chênh lệch", icon="grid_on", on_click=do_export
                ).classes("bg-red-800 text-white")
                # Xuất ĐỦ mọi lệnh (khớp + lệch), không chỉ phần lệch như nút
                # trên — lệch đẩy lên đầu bảng, bôi vàng (xem
                # exporters.py::export_doiSoat_full).
                btn_export_all = ui.button(
                    "Xuất tất cả lệnh", icon="table_view", on_click=do_export_all
                ).classes("bg-slate-700 text-white")

        state["render"] = render
        render()


def _build_history_panel(tab, history_refresh):
    with ui.tab_panel(tab):
        with ui.row().classes("w-full items-end gap-3 flex-wrap mb-2"):
            tu_input = _date_filter_input("Từ ngày chấm")
            den_input = _date_filter_input("Đến ngày chấm")
            nguoi_input = ui.input("Tên người chấm", value="").props(
                "dense outlined clearable"
            ).classes("w-52")
            ui.button("Lọc", icon="filter_alt", on_click=lambda: load_history()).props("outline")

            async def clear_filter():
                tu_input.value = ""
                den_input.value = ""
                nguoi_input.value = ""
                await load_history()

            ui.button("Xoá lọc", icon="clear", on_click=clear_filter).props("outline color=grey dense")

        hist_area = ui.column().classes("w-full gap-2")

        async def load_history():
            hist_area.clear()
            try:
                params = {}
                if tu_input.value:
                    params["tu_ngay"] = tu_input.value
                if den_input.value:
                    params["den_ngay"] = den_input.value
                if nguoi_input.value:
                    params["nguoi_thuc_hien"] = nguoi_input.value
                rows = await asyncio.to_thread(api.get, "/api/doi-soat-citad/history", params)
            except Exception as e:
                if _handle_api_error(e):
                    return
                ui.notify(f"Lỗi: {e}", type="negative")
                return
            with hist_area:
                if not rows:
                    msg = (
                        "Không có lần đối soát nào khớp bộ lọc — thử bấm \"Xoá lọc\" để xem tất cả."
                        if (tu_input.value or den_input.value or nguoi_input.value)
                        else "Chưa có lịch sử đối soát nào"
                    )
                    ui.label(msg).classes("text-gray-400 p-4")
                    return
                with ui.row().classes(
                    "w-full items-center gap-3 px-3 py-2 bg-blue-900 rounded text-xs font-semibold text-white"
                ):
                    ui.label("Thời gian").classes("w-36")
                    ui.label("Ngày chấm").classes("w-24")
                    ui.label("Người thực hiện").classes("w-32")
                    ui.label("Khớp").classes("w-16 text-center")
                    ui.label("Lệch").classes("w-16 text-center")
                    ui.label("Thao tác").classes("flex-1")
                for r in rows:
                    _history_row(r)

        def _history_row(r: dict):
            history_id = r["id"]
            detail_area = ui.column().classes("w-full")
            expanded = {"open": False}
            # Lịch sử đối soát có thể lưu snapshot tới hàng trăm nghìn dòng
            # lệch (đúng bản chất — 1 ngày giao dịch thật) — đẩy cả khối đó
            # vào 1 ui.table() từng làm TREO CỨNG trình duyệt y hệt panel kết
            # quả chính trước khi được phân trang. Áp dụng lại đúng cách đó
            # ở đây: cắt trang phía Python, chỉ render 1 trang mỗi lần.
            HIST_PAGE_SIZE = 200
            hist_state = {"records": None, "page": 1}

            def render_hist_page():
                detail_area.clear()
                records = hist_state["records"]
                if not records:
                    with detail_area:
                        ui.label("Không có lệnh lệch nào (khớp 100%)").classes("text-gray-400 text-sm p-2")
                    return
                total = len(records)
                n_pages = max(1, (total + HIST_PAGE_SIZE - 1) // HIST_PAGE_SIZE)
                if hist_state["page"] > n_pages:
                    hist_state["page"] = n_pages
                start = (hist_state["page"] - 1) * HIST_PAGE_SIZE
                page_records = records[start:start + HIST_PAGE_SIZE]
                with detail_area:
                    with ui.row().classes("w-full items-center justify-between mb-1"):
                        ui.label(
                            f"Hiển thị {len(page_records)}/{total} dòng — trang {hist_state['page']}/{n_pages}."
                        ).classes("text-gray-500 text-xs")
                        with ui.row().classes("gap-1"):
                            def _prev():
                                if hist_state["page"] > 1:
                                    hist_state["page"] -= 1
                                    render_hist_page()

                            def _next():
                                if hist_state["page"] < n_pages:
                                    hist_state["page"] += 1
                                    render_hist_page()

                            ui.button(icon="chevron_left", on_click=_prev).props("dense flat size=sm")
                            ui.button(icon="chevron_right", on_click=_next).props("dense flat size=sm")
                    cols = [
                        {
                            "name": k, "label": lbl, "field": k,
                            "align": "center", "sortable": True,
                            **({":format": "val => val ? val.toLocaleString('en-US') : val"} if k == "so_tien" else {}),
                        }
                        for k, lbl in [("status", "Trạng thái"), ("so_gd", "Số GD"), ("key_agri", "Số GD (Agribank)"),
                                       ("so_tien", "Số tiền"), ("ngay", "Ngày"), ("nh_nhan", "Ngân hàng")]
                    ]
                    rows = [
                        {
                            "status": STATUS_LBL.get(rec.get("status"), rec.get("status")),
                            "so_gd": rec.get("so_gd"), "key_agri": rec.get("key_agri"),
                            "so_tien": rec.get("so_tien"), "ngay": rec.get("ngay"), "nh_nhan": rec.get("nh_nhan"),
                        }
                        for rec in page_records
                    ]
                    with ui.table(columns=cols, rows=rows, row_key="so_gd").props(
                        'bordered separator="cell" table-header-class="bg-blue-900 text-white"'
                    ).classes("w-full"):
                        pass

            async def xem_chi_tiet():
                if expanded["open"]:
                    detail_area.clear()
                    expanded["open"] = False
                    return
                try:
                    detail = await asyncio.to_thread(api.get, f"/api/doi-soat-citad/history/{history_id}")
                except Exception as e:
                    if _handle_api_error(e):
                        return
                    ui.notify(f"Lỗi: {e}", type="negative")
                    return
                expanded["open"] = True
                hist_state["records"] = detail["lech_records"]
                hist_state["page"] = 1
                render_hist_page()

            async def dl_excel():
                try:
                    content = await asyncio.to_thread(api.get_bytes, f"/api/doi-soat-citad/history/{history_id}/export")
                    ui.download(content, f"DoiSoat_CITAD_IPCAS_lichsu_{history_id}.xlsx")
                except Exception as e:
                    if _handle_api_error(e):
                        return
                    ui.notify(f"Lỗi: {e}", type="negative")

            with ui.column().classes("w-full border-b border-gray-100"):
                with ui.row().classes("w-full items-center gap-3 px-3 py-2 text-sm"):
                    ui.label(str(r["recon_date"])[:16]).classes("w-36")
                    ui.label(r["ngay_cham"]).classes("w-24")
                    ui.label(r.get("performed_by") or "").classes("w-32")
                    ui.label(str(r["n_khop"])).classes("w-16 text-center text-green-700")
                    ui.label(str(r["n_lech"])).classes("w-16 text-center text-red-600")
                    with ui.row().classes("flex-1 gap-2 flex-wrap"):
                        ui.button("Xem chi tiết", icon="visibility", on_click=xem_chi_tiet).props(
                            "dense outline size=sm"
                        ).classes("text-blue-700")
                        ui.button("Tải Excel", icon="grid_on", on_click=dl_excel).props("dense outline size=sm")

        history_refresh["fn"] = load_history
        ui.timer(0.1, load_history, once=True)
