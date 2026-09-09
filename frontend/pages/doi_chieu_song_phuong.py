"""Trang Đối chiếu Song phương — 3 thẻ: Phân loại dữ liệu | Đối chiếu đến | Đối chiếu đi.

1 trang, 1 menu, 1 feature-code `menu.doi_chieu_song_phuong` cho quyền XEM cả 3 thẻ.

"Đối chiếu đến" (2026-08-28) và "Đối chiếu đi" (2026-09-03): KHÔNG phải 2 tính năng độc lập
(Kênh↔Hub + Hub↔Core) xếp cạnh nhau, mà là 1 chu trình khép kín mỗi chiều — người dùng đưa 1 thư
mục gốc + ngày + ngân hàng, hệ thống tự chạy Kênh↔Hub rồi Hub↔Core nối tiếp, 1 job/1 kết quả cuối
(đúng model ACH: nhiều pha bên trong, gộp báo cáo). "Đối chiếu đến" gọi
`/api/doi_chieu_song_phuong_kenh_core/*` (`doi_chieu_song_phuong_kenh_core_service.py`); "Đối
chiếu đi" gọi `/api/doi_chieu_song_phuong_kenh_core_di/*`
(`doi_chieu_song_phuong_kenh_core_di_service.py`) — 2 service/package TÁCH RIÊNG (không tham số
hoá `chieu` trong 1 module) vì thuật toán Hub↔Core khác nhau đủ nhiều giữa 2 chiều (khoá SE_TRACE/
CRAMOUNT, cửa sổ hủy chéo ngày, WTPA/TPER — xem PLAN.md khảo sát 2026-09-03).

Quyền BẤM CHẠY tách riêng theo chiều: `doi_chieu_song_phuong_kenh_core.process` (đến),
`doi_chieu_song_phuong_kenh_core_di.process` (đi) — tách khỏi `doi_chieu_song_phuong.process`
(thẻ Phân loại dữ liệu), giống cách `cham_ach.process` tách quyền chạy khỏi quyền xem. Quyền XEM
trang vẫn dùng chung `menu.doi_chieu_song_phuong` cho cả 3 thẻ.

Thẻ "Phân loại dữ liệu" CHỈ hỗ trợ 1 file/lượt (giữ đúng thiết kế hiện tại của
`doi_chieu_song_phuong_service.py` trên develop — xử lý ĐƯỜNG DẪN file đã nằm trên máy chủ, không
có job hàng loạt nhiều file/thư mục server như PR#68 từng thêm; việc đó là quyết định sản phẩm
riêng, chưa làm lại ở đây)."""

import asyncio
import time

from nicegui import ui
import frontend.api_client as api
import frontend.ui_kit as ui_kit
from frontend.shared import (
    _sidebar, _content_area, _page_header, _require_auth, _handle_api_error,
)
from frontend.job_runner import build_source_input

_POLL_INTERVAL = 1.5      # giây — dùng chung cho "Đối chiếu đến"
# Tiến độ "Phân loại dữ liệu" lưu trong bộ nhớ backend: backend restart là mất sạch, poll sẽ
# 404 mãi mãi. Hai mốc dừng dưới đây để nút không kẹt "đang xử lý" vĩnh viễn.
_MAX_POLL_SECONDS = 900   # 15 phút — dài hơn mọi file thực tế
_MAX_POLL_FAILS = 10      # số lần lỗi liên tiếp thì bỏ cuộc (thẻ 1 — vòng lặp while riêng, 1s/lần)
# Thẻ 2 "Đối chiếu đến" dùng `ui.timer` (khác cơ chế thẻ 1 ở trên) — hằng số RIÊNG, không dùng
# chung `_MAX_POLL_FAILS` dù cùng ý nghĩa, để đổi ngưỡng 1 thẻ không âm thầm đổi luôn thẻ kia.
_MAX_POLL_FAILS_DEN = 3   # số lần lỗi liên tiếp (mỗi lần cách nhau _POLL_INTERVAL) thì bỏ cuộc


# ─── Thẻ 1 — Phân loại dữ liệu (IPCAS/GL02), 1 file/lượt ───────────────────────
def _tab_phan_loai():
    state = {"file_bytes": None, "file_name": "", "result": None}

    with ui.card().classes("w-full p-5 mb-4"):
        ui.label("Tải lên file ZIP dữ liệu IPCAS").classes(
            "text-base font-semibold text-red-800 mb-3"
        )
        ui.label(
            "File ZIP mã hóa AES-256 — xuất từ IPCAS. "
            "Hệ thống định tuyến 4 ngân hàng đối chiếu: "
            "Vietinbank (201), BIDV (202), Vietcombank (203), MBBank (311)."
        ).classes("text-xs text-gray-500 mb-4")

        file_label = ui.label("Chưa chọn file").classes(
            "text-xs text-gray-500 italic mb-2"
        )

        def on_upload(e):
            state["file_bytes"] = e.content.read()
            state["file_name"]  = e.name
            file_label.set_text(f"Đã chọn: {e.name}")
            file_label.classes(remove="text-gray-500 italic", add="text-green-700 font-medium")

        uploader = ui.upload(
            on_upload=on_upload, auto_upload=True,
        ).props('accept=".zip" flat dense label="Chọn file ZIP..."').classes("w-full mb-3")

        progress_bar = ui.linear_progress(value=0).classes("w-full mb-1")
        progress_bar.set_visibility(False)
        progress_label = ui.label("").classes("text-xs text-gray-500 mb-3")
        progress_label.set_visibility(False)

        process_btn = ui.button("Xử lý", icon="play_arrow").classes(
            "bg-red-800 text-white"
        )
        if not api.has_feature("doi_chieu_song_phuong.process"):
            process_btn.props("disable")
            process_btn.tooltip("Bạn không có quyền thực hiện thao tác này")

    # ── Kết quả ───────────────────────────────────────────────────────
    result_area = ui.column().classes("w-full")

    # ── Handlers ──────────────────────────────────────────────────────
    async def do_process():
        if not state["file_bytes"]:
            ui.notify("Vui lòng chọn file ZIP trước", type="warning")
            return

        process_btn.props("loading disable")
        result_area.clear()
        progress_bar.set_value(0)
        progress_label.set_text("0% — Đang tải file lên...")
        progress_bar.set_visibility(True)
        progress_label.set_visibility(True)

        # ── Bước 1: upload, nhận task_token ──────────────────────────
        try:
            resp = await asyncio.to_thread(
                api.post_upload,
                "/api/doi_chieu_song_phuong/process",
                {"file": (state["file_name"], state["file_bytes"], "application/zip")},
            )
            task_token = resp["task_token"]
        except Exception as e:
            progress_bar.set_visibility(False)
            progress_label.set_visibility(False)
            process_btn.props(remove="loading disable")
            if not _handle_api_error(e):
                ui.notify(f"Lỗi tải file: {e}", type="negative")
            return

        # ── Bước 2: poll progress ────────────────────────────────────
        deadline = time.monotonic() + _MAX_POLL_SECONDS
        fails = 0
        while True:
            await asyncio.sleep(1.0)

            if time.monotonic() > deadline:
                progress_bar.set_visibility(False)
                progress_label.set_visibility(False)
                ui.notify(
                    "Quá thời gian chờ xử lý. File có thể quá lớn hoặc máy chủ đã "
                    "khởi động lại — hãy thử lại.",
                    type="negative", multi_line=True, close_button=True,
                )
                break

            try:
                prog = await asyncio.to_thread(
                    api.get, f"/api/doi_chieu_song_phuong/progress/{task_token}"
                )
                fails = 0
            except Exception as e:
                fails += 1
                if fails < _MAX_POLL_FAILS:
                    continue
                progress_bar.set_visibility(False)
                progress_label.set_visibility(False)
                if not _handle_api_error(e):
                    ui.notify(
                        f"Mất liên lạc với máy chủ khi theo dõi tiến độ: {e}",
                        type="negative", multi_line=True, close_button=True,
                    )
                break

            pct = prog.get("pct", 0)
            progress_bar.set_value(pct / 100)
            progress_label.set_text(f"{pct}% — {prog.get('msg', '')}")

            if prog.get("done"):
                progress_bar.set_visibility(False)
                progress_label.set_visibility(False)
                if prog.get("error"):
                    ui.notify(f"Lỗi xử lý: {prog['error']}", type="negative")
                else:
                    state["result"] = prog["result"]
                    _render_result(prog["result"])
                break

        process_btn.props(remove="loading disable")

    async def download_file(file_key: str):
        r = state.get("result")
        if not r:
            return
        token = r["token"]
        date  = r.get("process_date", "")
        try:
            data = await asyncio.to_thread(
                api.get_bytes,
                f"/api/doi_chieu_song_phuong/download/{token}/{file_key}",
            )
            ui.download(data, filename=f"{file_key}_{date}.csv")
        except Exception as e:
            if not _handle_api_error(e):
                ui.notify(f"Lỗi tải file: {e}", type="negative")

    def _render_result(r: dict):
        # index rows theo (ma_nh, chieu) để dựng nút tải
        rows_by_key = {f["file_key"]: f["rows"] for f in r.get("files", [])}

        with result_area:
            with ui.card().classes("w-full p-5"):
                with ui.row().classes("items-center gap-2 mb-4"):
                    ui.icon("check_circle", color="green").classes("text-xl")
                    ui.label(
                        f"Xử lý hoàn tất trong {r.get('elapsed_s', '?')}s "
                        f"— {r.get('total_rows', 0):,} dòng"
                    ).classes("font-semibold text-green-700")

                # ── Bảng thống kê ─────────────────────────────────────
                columns = [
                    {"name": "ma_nh",  "label": "Mã NH",     "field": "ma_nh",  "align": "left"},
                    {"name": "ten_nh", "label": "Ngân hàng", "field": "ten_nh", "align": "left"},
                    {"name": "den",    "label": "Lệnh ĐẾN",  "field": "so_lenh_den"},
                    {"name": "di",     "label": "Lệnh ĐI",   "field": "so_lenh_di"},
                    {"name": "tong",   "label": "Tổng",      "field": "tong"},
                ]
                ui.table(columns=columns, rows=r.get("stats", []),
                         row_key="ma_nh").classes("w-full mb-4")

                # ── Nút tải 8 file (mỗi NH 1 hàng: ĐẾN + ĐI) ─────────
                ui.label("Tải file CSV").classes("font-semibold text-red-800 mb-2")
                for s in r.get("stats", []):
                    ma = s["ma_nh"]
                    with ui.row().classes("w-full items-center gap-3 mb-2"):
                        ui.label(f'{ma} · {s["ten_nh"]}').classes(
                            "text-sm font-medium w-40 shrink-0"
                        )
                        for chieu, tag, cls in (
                            ("DEN", "ĐẾN", "text-blue-700"),
                            ("DI",  "ĐI",  "text-green-700"),
                        ):
                            key  = f"{ma}_{chieu}"
                            rows = rows_by_key.get(key, 0)
                            btn  = ui.button(
                                f"{tag} ({rows:,})", icon="download",
                            ).props("outline dense").classes(f"{cls} text-xs")

                            def _make_dl(k):
                                async def _handler():
                                    await download_file(k)
                                return _handler
                            btn.on("click", _make_dl(key))

    process_btn.on("click", do_process)

    # Click bất kỳ đâu trong vùng upload (trừ button) đều mở file picker
    return uploader


# ─── Thẻ 2 — Đối chiếu đến: Kênh↔Hub + Hub↔Core chạy tự động nối tiếp ──────────
def _tab_doi_chieu_den():
    """Chu trình khép kín (quyết định 2026-08-28): người dùng đưa 1 thư mục gốc + ngày +
    ngân hàng, hệ thống tự chạy Kênh↔Hub rồi Hub↔Core, chỉ 1 job/1 kết quả cuối — đúng model
    ACH (nhiều pha bên trong, gộp báo cáo). Kết quả vẫn nhiều file tải về, chỉ gộp chung 1 khu."""
    _STAGE_LABELS = ["Kênh↔Hub", "Hub↔Core", "Hoàn tất"]
    state = {"job_id": None, "log_pos": 0, "timer": None, "running": False,
              "poll_fails": 0, "files": {}}

    ui.label(
        "Chạy tự động nối tiếp Kênh↔Hub rồi Hub↔Core cho 1 ngân hàng — 1 lần bấm, 1 kết quả "
        "cuối (chỉ làm chiều ĐẾN)."
    ).classes("text-sm text-gray-500 mb-4")

    with ui.card().classes("w-full p-4 mb-4 bg-yellow-50 border border-yellow-400"):
        with ui.row().classes("items-start gap-2"):
            ui.icon("info", color="amber-700").classes("text-xl mt-0.5")
            ui.label(
                "Kênh↔Hub: đối chiếu HUB nội bộ với kênh song phương ngân hàng đối tác — 3 đơn "
                "vị (202,SPRT), (203,SPRT), (202,SPT), NH 203 chưa có SP THƯỜNG. "
                "Hub↔Core: đối chiếu HUB với hạch toán CORE/GL02 (cửa sổ T-3..T+3) — dùng "
                "file đã phân loại sẵn (\"{ma_nh}_DEN.csv\" hoặc .xlsx) nếu có, không thì tự giải "
                "mã GL02. Có thể chọn nhiều file đã phân loại khác ngày (T, T+1...) cùng lúc, "
                "trộn lẫn .csv/.xlsx cũng được — hệ thống tự đọc đúng ngày bên trong từng file. "
                "Mỗi lần chạy chỉ 1 ngân hàng (giới hạn RAM — mỗi NH phải giải mã lại GL02 từ "
                "đầu nếu chưa có CSV/Excel) — muốn đủ 4 NH thì bấm chạy 4 lần. Lỗi 1 bước không "
                "chặn bước còn lại."
            ).classes("text-sm text-amber-900")

    with ui.card().classes("w-full p-5 mb-4"):
        ui.label("Nguồn dữ liệu").classes("text-base font-semibold text-red-800 mb-3")

        build_source_input(
            state,
            accept=".zip,.xlsx,.csv",
            upload_label="Chọn file (có thể chọn nhiều)...",
            upload_hint=(
                "Chọn cùng lúc: 1-2 file HUB (.zip), 1-3 file kênh (.xlsx), file GL02 (.zip) hoặc "
                "file core đã phân loại (.csv hoặc .xlsx, có thể nhiều file khác ngày), OSB "
                "(.xlsx, nếu có) — giữ nguyên tên file gốc."
            ),
        )

        with ui.row().classes("gap-3 mt-3 items-end"):
            with ui.input(
                label="Ngày đối chiếu", placeholder="dd/mm/yyyy",
            ).props("outlined dense").classes("w-44") as ngay_input:
                with ui.menu().props("no-parent-event") as ngay_menu:
                    ui.date(mask="DD/MM/YYYY").props(
                        'first-day-of-week="1"'
                    ).bind_value(ngay_input)
                with ngay_input.add_slot("append"):
                    ui.icon("event").on("click", ngay_menu.open).classes(
                        "cursor-pointer text-gray-500"
                    )
            ma_nh_select = ui.select(
                {"201": "201 — Vietinbank", "202": "202 — BIDV",
                 "203": "203 — Vietcombank", "311": "311 — MBBank"},
                label="Ngân hàng", value="202",
            ).props("outlined dense").classes("w-52")

        readiness_box = ui.column().classes("w-full mt-3 gap-1")
        readiness_box.set_visibility(False)

        def _hide_readiness(_=None):
            """Banner Phần 2 dễ trở nên sai lệch khi người dùng đổi ngày/NH/thư mục sau khi đã
            kiểm tra — ẩn đi để tránh hiểu nhầm "đã đủ" với dữ liệu khác, không tự động kiểm tra
            lại (tránh gọi API dồn dập mỗi lần gõ phím)."""
            readiness_box.set_visibility(False)

        ngay_input.on_value_change(_hide_readiness)
        ma_nh_select.on_value_change(_hide_readiness)

        with ui.row().classes("gap-3 mt-4"):
            btn_check = ui.button("Kiểm tra dữ liệu", icon="fact_check",
                                  color="blue-7").props("outlined").classes("font-semibold")
            btn_run = ui.button("Chạy đối chiếu", icon="play_arrow",
                                color="red-8").classes("font-semibold")
            if not api.has_feature("doi_chieu_song_phuong_kenh_core.process"):
                btn_run.props("disable")
                btn_run.tooltip("Bạn không có quyền thực hiện thao tác này")
            btn_cancel = ui.button("Dừng", icon="stop_circle",
                                   color="grey-6").classes("font-semibold")
            btn_cancel.set_visibility(False)

        stepper_box = ui.column().classes("w-full mt-4")
        stepper_box.set_visibility(False)
        with stepper_box:
            ui_kit.stepper(_STAGE_LABELS, 0)

    with ui.card().classes("w-full p-0 mb-4"):
        with ui.row().classes("w-full bg-gray-800 px-4 py-2 rounded-t items-center gap-2"):
            ui.icon("terminal").classes("text-green-400 text-sm")
            ui.label("Log xử lý").classes("text-xs font-semibold text-green-300")
            spinner = ui.spinner("dots", size="xs", color="green")
            spinner.set_visibility(False)

        log_area = ui.column().classes(
            "w-full bg-gray-900 font-mono text-xs text-green-200 "
            "p-3 overflow-y-auto max-h-72 min-h-24 gap-0"
        )
        with log_area:
            ui.label('Sẵn sàng. Chọn nguồn dữ liệu + ngày + ngân hàng rồi bấm "Chạy đối chiếu".').classes(
                "text-gray-500"
            )

    result_card = ui.card().classes("w-full p-5")
    result_card.set_visibility(False)

    def _append_log(msg: str):
        with log_area:
            ui.label(msg).classes("leading-tight")

    def _clear_log():
        log_area.clear()

    def _update_stepper(stage: int):
        stepper_box.set_visibility(True)
        stepper_box.clear()
        with stepper_box:
            ui_kit.stepper(_STAGE_LABELS, stage)

    def _render_trang_thai_banner(trang_thai: dict | None):
        """Banner "Chưa đối chiếu được" cấp job (Phần 3, 2026-08-30) — tách khỏi bảng số liệu
        "Đã cân khớp/Chưa cân khớp" bên dưới (đó là chênh lệch THẬT, không đổi)."""
        if trang_thai and trang_thai.get("trang_thai") == "chua_doi_chieu":
            ly_do = trang_thai.get("ly_do") or "không rõ lý do"
            with ui.row().classes(
                "items-center gap-2 p-2 mb-2 bg-orange-50 border border-orange-300 rounded"
            ):
                ui.icon("warning", color="orange-8").classes("text-lg")
                ui.label(f"CHƯA ĐỐI CHIẾU ĐƯỢC — thiếu dữ liệu ({ly_do})").classes(
                    "text-sm font-semibold text-orange-800"
                )

    def _render_kenh_hub(kq: dict | None, trang_thai: dict | None = None):
        with ui.expansion("Kênh ↔ Hub", value=True).classes("w-full border rounded mb-2"):
            _render_trang_thai_banner(trang_thai)
            if kq is None:
                if not trang_thai:
                    ui.label("Không có kết quả — xem log.").classes("text-sm text-orange-700")
                return
            chenh_lech = kq.get("chenh_lech", {})
            if chenh_lech:
                columns = [
                    {"name": "dv", "label": "Đơn vị", "field": "dv", "align": "left"},
                    {"name": "trang_thai", "label": "Trạng thái", "field": "trang_thai"},
                    {"name": "chenh_mon", "label": "Chênh số món", "field": "chenh_mon"},
                    {"name": "chenh_tien", "label": "Chênh số tiền (đồng)", "field": "chenh_tien"},
                ]
                rows = []
                for k, v in chenh_lech.items():
                    cm, ct = v["chenh_so_mon"], v["chenh_so_tien"]
                    rows.append({
                        "dv": k,
                        "trang_thai": "Đã cân khớp" if cm == 0 and ct == 0 else "Chưa cân khớp",
                        "chenh_mon": f"{cm:+,}",
                        "chenh_tien": f"{ct:+,}",
                    })
                ui.table(columns=columns, rows=rows, row_key="dv").classes("w-full mb-2")
            canh_bao = kq.get("canh_bao", [])
            if canh_bao:
                with ui.card().classes("w-full p-3 bg-red-50 border border-red-400"):
                    ui.label("⚠ Cảnh báo trạng thái chỉ-hub ngoài dự kiến:").classes(
                        "text-sm font-semibold text-red-800"
                    )
                    for cb in canh_bao:
                        ui.label(f"{cb['don_vi']}: {cb['trang_thai']}").classes(
                            "text-xs text-red-700"
                        )

    def _render_hub_core(kq: dict | None, trang_thai: dict | None = None):
        with ui.expansion("Hub ↔ Core", value=True).classes("w-full border rounded mb-2"):
            _render_trang_thai_banner(trang_thai)
            if kq is None:
                if not trang_thai:
                    ui.label("Không có kết quả — xem log.").classes("text-sm text-orange-700")
                return
            ui.label(
                f"CORE: {kq.get('so_dong_core', 0):,} dòng — HUB: {kq.get('so_dong_hub', 0):,} dòng"
            ).classes("text-sm mb-2")
            columns = [
                {"name": "nhan", "label": "Nhãn KETQUADOICHIEU", "field": "nhan", "align": "left"},
                {"name": "core", "label": "Số dòng CORE", "field": "core"},
                {"name": "hub", "label": "Số dòng HUB", "field": "hub"},
            ]
            phan_bo_core = kq.get("phan_bo_core", {})
            phan_bo_hub = kq.get("phan_bo_hub", {})
            nhan_set = sorted(set(phan_bo_core) | set(phan_bo_hub))
            rows = [
                {"nhan": n, "core": phan_bo_core.get(n, 0), "hub": phan_bo_hub.get(n, 0)}
                for n in nhan_set
            ]
            ui.table(columns=columns, rows=rows, row_key="nhan").classes("w-full")

    def _show_results(res: dict):
        result_card.set_visibility(True)
        result_card.clear()
        with result_card:
            ui.label("Kết quả").classes("text-base font-semibold text-red-800 mb-3")
            with ui.row().classes("items-center gap-2 mb-3"):
                ui.icon("check_circle", color="green").classes("text-xl")
                ui.label(
                    f"Ngày đối chiếu: {res.get('ngay', '?')} — Ngân hàng: {res.get('ma_nh', '?')}"
                ).classes("font-semibold text-green-700")

            ket_qua = res.get("ket_qua", {})
            trang_thai = ket_qua.get("trang_thai") or {}
            _render_kenh_hub(ket_qua.get("kenh_hub"), trang_thai.get("kenh_hub"))
            _render_hub_core(ket_qua.get("hub_core"), trang_thai.get("hub_core"))

            ui.label("Tải file kết quả").classes("font-semibold text-red-800 mb-2 mt-2")
            with ui.row().classes("flex-wrap gap-3"):
                for fname in res.get("files", []):
                    url = f"/api/doi_chieu_song_phuong_kenh_core/download/{state['job_id']}/{fname}"

                    async def _tai_ket_qua(u=url, name=fname):
                        try:
                            content = await asyncio.to_thread(api.download, u)
                        except Exception as e:
                            if not _handle_api_error(e):
                                ui.notify(str(e), type="negative")
                            return
                        ui.download(content, name)

                    ui.button(fname, icon="table_chart", color="green-7").on(
                        "click", _tai_ket_qua
                    ).classes("text-xs")

    async def _poll():
        if not state["job_id"]:
            return
        try:
            res = await asyncio.to_thread(
                api.get,
                f"/api/doi_chieu_song_phuong_kenh_core/poll/{state['job_id']}",
                params={"since": state["log_pos"]},
            )
        except Exception as e:
            if _handle_api_error(e):
                return
            if not api.la_loi_mang(e):
                # Máy chủ CÓ trả lời, chỉ là trả lời lỗi (thường 404 "job đã hết hạn") — job
                # coi như đã mất hẳn, thử lại vô ích (khuôn mẫu cham_ach.py::_poll()).
                spinner.set_visibility(False)
                btn_cancel.set_visibility(False)
                btn_run.set_visibility(True)
                state["running"] = False
                if state["timer"]:
                    state["timer"].cancel()
                    state["timer"] = None
                ui.notify(f"Máy chủ từ chối theo dõi tiến độ: {e}", type="negative", timeout=0)
                return
            state["poll_fails"] += 1
            if state["poll_fails"] < _MAX_POLL_FAILS_DEN:
                return
            spinner.set_visibility(False)
            btn_run.set_visibility(True)
            state["running"] = False
            if state["timer"]:
                state["timer"].cancel()
                state["timer"] = None
            # KHÔNG ẩn btn_cancel — mất liên lạc do MẠNG, job có thể vẫn đang chạy.
            ui.notify(
                "Mất liên lạc với máy chủ khi theo dõi tiến độ — job có thể vẫn đang chạy "
                "trên máy chủ.", type="negative", timeout=0,
            )
            return

        state["poll_fails"] = 0
        new_logs = res.get("logs", [])
        for line in new_logs:
            _append_log(line)
        state["log_pos"] += len(new_logs)
        _update_stepper(res.get("stage", 0))

        status = res.get("status", "")
        if status in ("done", "error", "cancelled"):
            spinner.set_visibility(False)
            btn_cancel.set_visibility(False)
            btn_run.set_visibility(True)
            state["running"] = False
            if state["timer"]:
                state["timer"].cancel()
                state["timer"] = None

            if status == "done":
                _show_results(res)
                ui.notify("Hoàn thành! Tải file kết quả bên dưới.", type="positive")
            elif status == "error":
                ui.notify(f"Lỗi: {res.get('error', '')}", type="negative", timeout=0)
            elif status == "cancelled":
                ui.notify("Đã dừng theo yêu cầu.", type="warning")

    def _yyyymmdd_tu_dmy(s: str) -> str | None:
        parts = s.strip().split("/")
        if len(parts) != 3:
            return None
        d, m, y = parts
        if not (d.isdigit() and m.isdigit() and y.isdigit()):
            return None
        return f"{y}{m.zfill(2)}{d.zfill(2)}"

    def _render_readiness_line(nhan: str, trang_thai: str):
        if trang_thai == "du":
            ui.label(f"✅ Đủ dữ liệu {nhan}").classes("text-sm text-green-700")
        else:
            ly_do = trang_thai.split(":", 1)[1] if ":" in trang_thai else trang_thai
            ui.label(f"⚠️ {nhan}: thiếu {ly_do}").classes("text-sm text-orange-700")

    async def _check_readiness():
        """Dò TÊN file TRƯỚC khi bấm "Chạy" — chỉ để biết trước đủ/thiếu, KHÔNG chặn nút Chạy
        (2026-08-30, banner cảnh báo, hành vi chạy-rồi-tự-bỏ-qua-bước-thiếu giữ nguyên)."""
        ngay = _yyyymmdd_tu_dmy(ngay_input.value or "")
        ma_nh = ma_nh_select.value
        if not ngay:
            ui.notify("Ngày đối chiếu chưa hợp lệ — bấm icon lịch để chọn.", type="warning")
            return
        if not ma_nh:
            ui.notify("Chưa chọn ngân hàng.", type="warning")
            return
        if not state["files"]:
            ui.notify("Chưa chọn file nào.", type="warning")
            return
        body: dict = {"ngay": ngay, "ma_nh": ma_nh, "file_names": list(state["files"].keys())}

        try:
            res = await asyncio.to_thread(
                api.post, "/api/doi_chieu_song_phuong_kenh_core/check_readiness", body,
            )
        except Exception as e:
            if not _handle_api_error(e):
                ui.notify(str(e), type="negative")
            return

        readiness_box.set_visibility(True)
        readiness_box.clear()
        with readiness_box:
            _render_readiness_line("Kênh↔Hub", res.get("kenh_hub", ""))
            _render_readiness_line("Hub↔Core", res.get("hub_core", ""))

    async def on_run():
        if state["running"]:
            return
        ngay = _yyyymmdd_tu_dmy(ngay_input.value or "")
        ma_nh = ma_nh_select.value
        if not ngay:
            ui.notify("Ngày đối chiếu chưa hợp lệ — bấm icon lịch để chọn.", type="warning")
            return
        if not ma_nh:
            ui.notify("Chưa chọn ngân hàng.", type="warning")
            return
        if not state["files"]:
            ui.notify("Chưa chọn file nào.", type="warning")
            return

        _clear_log()
        result_card.set_visibility(False)
        readiness_box.set_visibility(False)
        btn_run.set_visibility(False)
        btn_cancel.set_visibility(True)
        spinner.set_visibility(True)
        state["running"] = True
        state["log_pos"] = 0
        state["poll_fails"] = 0
        _update_stepper(0)

        try:
            _append_log(f"Đang tải {len(state['files'])} file lên — Ngày: {ngay} — NH: {ma_nh}")
            res = await asyncio.to_thread(
                api.post_upload,
                "/api/doi_chieu_song_phuong_kenh_core/start_upload",
                files=[("files", (name, data, "application/octet-stream"))
                       for name, data in state["files"].items()],
                data={"ngay": ngay, "ma_nh": ma_nh},
                timeout=600.0,
            )
        except Exception as e:
            spinner.set_visibility(False)
            btn_cancel.set_visibility(False)
            btn_run.set_visibility(True)
            state["running"] = False
            if not _handle_api_error(e):
                ui.notify(str(e), type="negative")
            return

        state["job_id"] = res.get("job_id")
        _append_log(f"Job ID: {state['job_id']}")
        state["timer"] = ui.timer(_POLL_INTERVAL, _poll)

    async def on_cancel():
        if not state["job_id"]:
            return
        try:
            await asyncio.to_thread(
                api.post, f"/api/doi_chieu_song_phuong_kenh_core/cancel/{state['job_id']}"
            )
            _append_log("[Yêu cầu dừng đã gửi — chờ xử lý xong bước hiện tại...]")
        except Exception as e:
            ui.notify(str(e), type="negative")

    btn_check.on("click", _check_readiness)
    btn_run.on("click", on_run)
    btn_cancel.on("click", on_cancel)


# ─── Thẻ 3 — Đối chiếu đi: Kênh↔Hub + Hub↔Core chạy tự động nối tiếp ───────────
def _tab_doi_chieu_di():
    """Mirror `_tab_doi_chieu_den()` — cùng kiến trúc 1 job/1 kết quả cuối, đổi endpoint sang
    `/api/doi_chieu_song_phuong_kenh_core_di/*` và khoá kết quả `kenh_hub_di`/`hub_core_di`
    (xem `doi_chieu_song_phuong_kenh_core_di_service.py`). Thuật toán Hub↔Core khác hẳn "đến"
    (SE_TRACE, CRAMOUNT, cửa sổ hủy chéo ngày, WTPA/TPER — xem PLAN.md) nhưng UI dùng chung được
    100% vì `_render_hub_core()`/`_render_kenh_hub()` chỉ đọc dict shape chung
    (`phan_bo_core`/`phan_bo_hub`/`chenh_lech`), không hardcode nhãn KETQUADOICHIEU nào."""
    _STAGE_LABELS = ["Kênh↔Hub", "Hub↔Core", "Hoàn tất"]
    state = {"job_id": None, "log_pos": 0, "timer": None, "running": False,
              "poll_fails": 0, "files": {}}

    ui.label(
        "Chạy tự động nối tiếp Kênh↔Hub rồi Hub↔Core cho 1 ngân hàng — 1 lần bấm, 1 kết quả "
        "cuối (chỉ làm chiều ĐI)."
    ).classes("text-sm text-gray-500 mb-4")

    with ui.card().classes("w-full p-4 mb-4 bg-yellow-50 border border-yellow-400"):
        with ui.row().classes("items-start gap-2"):
            ui.icon("info", color="amber-700").classes("text-xl mt-0.5")
            ui.label(
                "Kênh↔Hub: đối chiếu HUB nội bộ với kênh song phương ngân hàng đối tác — không "
                "lọc gì trước khi khớp (khác chiều đến), Bảng 1 chỉ đếm HUB trạng thái SCNL. "
                "Hub↔Core: đối chiếu HUB (chỉ dòng SCNL) với hạch toán CORE/GL02 (cửa sổ "
                "T-3..T+3, kể cả hủy chéo ngày) — dùng file đã phân loại sẵn (\"{ma_nh}_DI.csv\" "
                "hoặc .xlsx) nếu có, không thì tự giải mã GL02. Có thể chọn nhiều file đã phân "
                "loại khác ngày (T, T-1, T+1...) cùng lúc, trộn lẫn .csv/.xlsx cũng được — hệ "
                "thống tự đọc đúng ngày bên trong từng file. Mỗi lần chạy chỉ 1 ngân hàng — muốn "
                "đủ 4 NH thì bấm chạy 4 lần. Lỗi 1 bước không chặn bước còn lại."
            ).classes("text-sm text-amber-900")

    with ui.card().classes("w-full p-5 mb-4"):
        ui.label("Nguồn dữ liệu").classes("text-base font-semibold text-red-800 mb-3")

        build_source_input(
            state,
            accept=".zip,.xlsx,.csv",
            upload_label="Chọn file (có thể chọn nhiều)...",
            upload_hint=(
                "Chọn cùng lúc: 1-2 file HUB (.zip), 1-3 file kênh (.xlsx), file GL02 (.zip) hoặc "
                "file core đã phân loại (.csv hoặc .xlsx, có thể nhiều file khác ngày), OSB "
                "(.xlsx, nếu có) — giữ nguyên tên file gốc."
            ),
        )

        with ui.row().classes("gap-3 mt-3 items-end"):
            with ui.input(
                label="Ngày đối chiếu", placeholder="dd/mm/yyyy",
            ).props("outlined dense").classes("w-44") as ngay_input:
                with ui.menu().props("no-parent-event") as ngay_menu:
                    ui.date(mask="DD/MM/YYYY").props(
                        'first-day-of-week="1"'
                    ).bind_value(ngay_input)
                with ngay_input.add_slot("append"):
                    ui.icon("event").on("click", ngay_menu.open).classes(
                        "cursor-pointer text-gray-500"
                    )
            ma_nh_select = ui.select(
                {"201": "201 — Vietinbank", "202": "202 — BIDV",
                 "203": "203 — Vietcombank", "311": "311 — MBBank"},
                label="Ngân hàng", value="201",
            ).props("outlined dense").classes("w-52")

        readiness_box = ui.column().classes("w-full mt-3 gap-1")
        readiness_box.set_visibility(False)

        def _hide_readiness(_=None):
            readiness_box.set_visibility(False)

        ngay_input.on_value_change(_hide_readiness)
        ma_nh_select.on_value_change(_hide_readiness)

        with ui.row().classes("gap-3 mt-4"):
            btn_check = ui.button("Kiểm tra dữ liệu", icon="fact_check",
                                  color="blue-7").props("outlined").classes("font-semibold")
            btn_run = ui.button("Chạy đối chiếu", icon="play_arrow",
                                color="red-8").classes("font-semibold")
            if not api.has_feature("doi_chieu_song_phuong_kenh_core_di.process"):
                btn_run.props("disable")
                btn_run.tooltip("Bạn không có quyền thực hiện thao tác này")
            btn_cancel = ui.button("Dừng", icon="stop_circle",
                                   color="grey-6").classes("font-semibold")
            btn_cancel.set_visibility(False)

        stepper_box = ui.column().classes("w-full mt-4")
        stepper_box.set_visibility(False)
        with stepper_box:
            ui_kit.stepper(_STAGE_LABELS, 0)

    with ui.card().classes("w-full p-0 mb-4"):
        with ui.row().classes("w-full bg-gray-800 px-4 py-2 rounded-t items-center gap-2"):
            ui.icon("terminal").classes("text-green-400 text-sm")
            ui.label("Log xử lý").classes("text-xs font-semibold text-green-300")
            spinner = ui.spinner("dots", size="xs", color="green")
            spinner.set_visibility(False)

        log_area = ui.column().classes(
            "w-full bg-gray-900 font-mono text-xs text-green-200 "
            "p-3 overflow-y-auto max-h-72 min-h-24 gap-0"
        )
        with log_area:
            ui.label('Sẵn sàng. Chọn nguồn dữ liệu + ngày + ngân hàng rồi bấm "Chạy đối chiếu".').classes(
                "text-gray-500"
            )

    result_card = ui.card().classes("w-full p-5")
    result_card.set_visibility(False)

    def _append_log(msg: str):
        with log_area:
            ui.label(msg).classes("leading-tight")

    def _clear_log():
        log_area.clear()

    def _update_stepper(stage: int):
        stepper_box.set_visibility(True)
        stepper_box.clear()
        with stepper_box:
            ui_kit.stepper(_STAGE_LABELS, stage)

    def _render_trang_thai_banner(trang_thai: dict | None):
        if trang_thai and trang_thai.get("trang_thai") == "chua_doi_chieu":
            ly_do = trang_thai.get("ly_do") or "không rõ lý do"
            with ui.row().classes(
                "items-center gap-2 p-2 mb-2 bg-orange-50 border border-orange-300 rounded"
            ):
                ui.icon("warning", color="orange-8").classes("text-lg")
                ui.label(f"CHƯA ĐỐI CHIẾU ĐƯỢC — thiếu dữ liệu ({ly_do})").classes(
                    "text-sm font-semibold text-orange-800"
                )

    def _render_kenh_hub(kq: dict | None, trang_thai: dict | None = None):
        with ui.expansion("Kênh ↔ Hub", value=True).classes("w-full border rounded mb-2"):
            _render_trang_thai_banner(trang_thai)
            if kq is None:
                if not trang_thai:
                    ui.label("Không có kết quả — xem log.").classes("text-sm text-orange-700")
                return
            chenh_lech = kq.get("chenh_lech", {})
            if chenh_lech:
                columns = [
                    {"name": "dv", "label": "Đơn vị", "field": "dv", "align": "left"},
                    {"name": "trang_thai", "label": "Trạng thái", "field": "trang_thai"},
                    {"name": "chenh_mon", "label": "Chênh số món", "field": "chenh_mon"},
                    {"name": "chenh_tien", "label": "Chênh số tiền (đồng)", "field": "chenh_tien"},
                ]
                rows = []
                for k, v in chenh_lech.items():
                    cm, ct = v["chenh_so_mon"], v["chenh_so_tien"]
                    rows.append({
                        "dv": k,
                        "trang_thai": "Đã cân khớp" if cm == 0 and ct == 0 else "Chưa cân khớp",
                        "chenh_mon": f"{cm:+,}",
                        "chenh_tien": f"{ct:+,}",
                    })
                ui.table(columns=columns, rows=rows, row_key="dv").classes("w-full mb-2")
            canh_bao = kq.get("canh_bao", [])
            if canh_bao:
                with ui.card().classes("w-full p-3 bg-red-50 border border-red-400"):
                    ui.label("⚠ Cảnh báo trạng thái chỉ-hub ngoài dự kiến:").classes(
                        "text-sm font-semibold text-red-800"
                    )
                    for cb in canh_bao:
                        ui.label(f"{cb['don_vi']}: {cb['trang_thai']}").classes(
                            "text-xs text-red-700"
                        )

    def _render_hub_core(kq: dict | None, trang_thai: dict | None = None):
        with ui.expansion("Hub ↔ Core", value=True).classes("w-full border rounded mb-2"):
            _render_trang_thai_banner(trang_thai)
            if kq is None:
                if not trang_thai:
                    ui.label("Không có kết quả — xem log.").classes("text-sm text-orange-700")
                return
            ui.label(
                f"CORE: {kq.get('so_dong_core', 0):,} dòng — HUB: {kq.get('so_dong_hub', 0):,} dòng"
            ).classes("text-sm mb-2")
            columns = [
                {"name": "nhan", "label": "Nhãn KETQUADOICHIEU", "field": "nhan", "align": "left"},
                {"name": "core", "label": "Số dòng CORE", "field": "core"},
                {"name": "hub", "label": "Số dòng HUB", "field": "hub"},
            ]
            phan_bo_core = kq.get("phan_bo_core", {})
            phan_bo_hub = kq.get("phan_bo_hub", {})
            nhan_set = sorted(set(phan_bo_core) | set(phan_bo_hub))
            rows = [
                {"nhan": n, "core": phan_bo_core.get(n, 0), "hub": phan_bo_hub.get(n, 0)}
                for n in nhan_set
            ]
            ui.table(columns=columns, rows=rows, row_key="nhan").classes("w-full")

    def _show_results(res: dict):
        result_card.set_visibility(True)
        result_card.clear()
        with result_card:
            ui.label("Kết quả").classes("text-base font-semibold text-red-800 mb-3")
            with ui.row().classes("items-center gap-2 mb-3"):
                ui.icon("check_circle", color="green").classes("text-xl")
                ui.label(
                    f"Ngày đối chiếu: {res.get('ngay', '?')} — Ngân hàng: {res.get('ma_nh', '?')}"
                ).classes("font-semibold text-green-700")

            ket_qua = res.get("ket_qua", {})
            trang_thai = ket_qua.get("trang_thai") or {}
            _render_kenh_hub(ket_qua.get("kenh_hub_di"), trang_thai.get("kenh_hub_di"))
            _render_hub_core(ket_qua.get("hub_core_di"), trang_thai.get("hub_core_di"))

            ui.label("Tải file kết quả").classes("font-semibold text-red-800 mb-2 mt-2")
            with ui.row().classes("flex-wrap gap-3"):
                for fname in res.get("files", []):
                    url = f"/api/doi_chieu_song_phuong_kenh_core_di/download/{state['job_id']}/{fname}"

                    async def _tai_ket_qua(u=url, name=fname):
                        try:
                            content = await asyncio.to_thread(api.download, u)
                        except Exception as e:
                            if not _handle_api_error(e):
                                ui.notify(str(e), type="negative")
                            return
                        ui.download(content, name)

                    ui.button(fname, icon="table_chart", color="green-7").on(
                        "click", _tai_ket_qua
                    ).classes("text-xs")

    async def _poll():
        if not state["job_id"]:
            return
        try:
            res = await asyncio.to_thread(
                api.get,
                f"/api/doi_chieu_song_phuong_kenh_core_di/poll/{state['job_id']}",
                params={"since": state["log_pos"]},
            )
        except Exception as e:
            if _handle_api_error(e):
                return
            if not api.la_loi_mang(e):
                spinner.set_visibility(False)
                btn_cancel.set_visibility(False)
                btn_run.set_visibility(True)
                state["running"] = False
                if state["timer"]:
                    state["timer"].cancel()
                    state["timer"] = None
                ui.notify(f"Máy chủ từ chối theo dõi tiến độ: {e}", type="negative", timeout=0)
                return
            state["poll_fails"] += 1
            if state["poll_fails"] < _MAX_POLL_FAILS_DEN:
                return
            spinner.set_visibility(False)
            btn_run.set_visibility(True)
            state["running"] = False
            if state["timer"]:
                state["timer"].cancel()
                state["timer"] = None
            ui.notify(
                "Mất liên lạc với máy chủ khi theo dõi tiến độ — job có thể vẫn đang chạy "
                "trên máy chủ.", type="negative", timeout=0,
            )
            return

        state["poll_fails"] = 0
        new_logs = res.get("logs", [])
        for line in new_logs:
            _append_log(line)
        state["log_pos"] += len(new_logs)
        _update_stepper(res.get("stage", 0))

        status = res.get("status", "")
        if status in ("done", "error", "cancelled"):
            spinner.set_visibility(False)
            btn_cancel.set_visibility(False)
            btn_run.set_visibility(True)
            state["running"] = False
            if state["timer"]:
                state["timer"].cancel()
                state["timer"] = None

            if status == "done":
                _show_results(res)
                ui.notify("Hoàn thành! Tải file kết quả bên dưới.", type="positive")
            elif status == "error":
                ui.notify(f"Lỗi: {res.get('error', '')}", type="negative", timeout=0)
            elif status == "cancelled":
                ui.notify("Đã dừng theo yêu cầu.", type="warning")

    def _yyyymmdd_tu_dmy(s: str) -> str | None:
        parts = s.strip().split("/")
        if len(parts) != 3:
            return None
        d, m, y = parts
        if not (d.isdigit() and m.isdigit() and y.isdigit()):
            return None
        return f"{y}{m.zfill(2)}{d.zfill(2)}"

    def _render_readiness_line(nhan: str, trang_thai: str):
        if trang_thai == "du":
            ui.label(f"✅ Đủ dữ liệu {nhan}").classes("text-sm text-green-700")
        else:
            ly_do = trang_thai.split(":", 1)[1] if ":" in trang_thai else trang_thai
            ui.label(f"⚠️ {nhan}: thiếu {ly_do}").classes("text-sm text-orange-700")

    async def _check_readiness():
        ngay = _yyyymmdd_tu_dmy(ngay_input.value or "")
        ma_nh = ma_nh_select.value
        if not ngay:
            ui.notify("Ngày đối chiếu chưa hợp lệ — bấm icon lịch để chọn.", type="warning")
            return
        if not ma_nh:
            ui.notify("Chưa chọn ngân hàng.", type="warning")
            return
        if not state["files"]:
            ui.notify("Chưa chọn file nào.", type="warning")
            return
        body: dict = {"ngay": ngay, "ma_nh": ma_nh, "file_names": list(state["files"].keys())}

        try:
            res = await asyncio.to_thread(
                api.post, "/api/doi_chieu_song_phuong_kenh_core_di/check_readiness", body,
            )
        except Exception as e:
            if not _handle_api_error(e):
                ui.notify(str(e), type="negative")
            return

        readiness_box.set_visibility(True)
        readiness_box.clear()
        with readiness_box:
            _render_readiness_line("Kênh↔Hub", res.get("kenh_hub", ""))
            _render_readiness_line("Hub↔Core", res.get("hub_core", ""))

    async def on_run():
        if state["running"]:
            return
        ngay = _yyyymmdd_tu_dmy(ngay_input.value or "")
        ma_nh = ma_nh_select.value
        if not ngay:
            ui.notify("Ngày đối chiếu chưa hợp lệ — bấm icon lịch để chọn.", type="warning")
            return
        if not ma_nh:
            ui.notify("Chưa chọn ngân hàng.", type="warning")
            return
        if not state["files"]:
            ui.notify("Chưa chọn file nào.", type="warning")
            return

        _clear_log()
        result_card.set_visibility(False)
        readiness_box.set_visibility(False)
        btn_run.set_visibility(False)
        btn_cancel.set_visibility(True)
        spinner.set_visibility(True)
        state["running"] = True
        state["log_pos"] = 0
        state["poll_fails"] = 0
        _update_stepper(0)

        try:
            _append_log(f"Đang tải {len(state['files'])} file lên — Ngày: {ngay} — NH: {ma_nh}")
            res = await asyncio.to_thread(
                api.post_upload,
                "/api/doi_chieu_song_phuong_kenh_core_di/start_upload",
                files=[("files", (name, data, "application/octet-stream"))
                       for name, data in state["files"].items()],
                data={"ngay": ngay, "ma_nh": ma_nh},
                timeout=600.0,
            )
        except Exception as e:
            spinner.set_visibility(False)
            btn_cancel.set_visibility(False)
            btn_run.set_visibility(True)
            state["running"] = False
            if not _handle_api_error(e):
                ui.notify(str(e), type="negative")
            return

        state["job_id"] = res.get("job_id")
        _append_log(f"Job ID: {state['job_id']}")
        state["timer"] = ui.timer(_POLL_INTERVAL, _poll)

    async def on_cancel():
        if not state["job_id"]:
            return
        try:
            await asyncio.to_thread(
                api.post, f"/api/doi_chieu_song_phuong_kenh_core_di/cancel/{state['job_id']}"
            )
            _append_log("[Yêu cầu dừng đã gửi — chờ xử lý xong bước hiện tại...]")
        except Exception as e:
            ui.notify(str(e), type="negative")

    btn_check.on("click", _check_readiness)
    btn_run.on("click", on_run)
    btn_cancel.on("click", on_cancel)


# ─── Trang chính — page shell 3 thẻ ─────────────────────────────────────────────
@ui.page("/doi_chieu_song_phuong")
async def doi_chieu_song_phuong_page():
    if not _require_auth():
        return
    if not api.has_feature("menu.doi_chieu_song_phuong"):
        ui.navigate.to("/home")
        return

    with ui.row().classes("w-full"):
        await _sidebar("doi_chieu_song_phuong")
        with _content_area():
            _page_header(
                "Đối chiếu Song phương",
                "Phân loại IPCAS · Đối chiếu Kênh-Hub-Core chiều đến/đi",
            )

            with ui.tabs().props(
                "active-color=indigo-600 indicator-color=indigo-600 align=left"
            ).classes("w-full border-b border-gray-200 mb-4") as tabs:
                tab_phan_loai = ui.tab("Phân loại dữ liệu")
                tab_den = ui.tab("Đối chiếu đến")
                tab_di = ui.tab("Đối chiếu đi")

            with ui.tab_panels(tabs, value=tab_phan_loai).classes("w-full"):
                with ui.tab_panel(tab_phan_loai):
                    uploader = _tab_phan_loai()
                with ui.tab_panel(tab_den):
                    _tab_doi_chieu_den()
                with ui.tab_panel(tab_di):
                    _tab_doi_chieu_di()

    # Click bất kỳ đâu trong vùng upload (trừ button) đều mở file picker (thẻ Phân loại dữ liệu)
    await ui.context.client.connected()
    await ui.run_javascript(f'''
        setTimeout(function() {{
            var el = document.getElementById("c{uploader.id}");
            if (!el) return;
            var inp = el.querySelector('input[type="file"]');
            if (!inp) return;
            el.style.cursor = 'pointer';
            el.addEventListener('click', function(e) {{
                if (!e.target.closest('button')) inp.click();
            }});
        }}, 200);
    ''')
