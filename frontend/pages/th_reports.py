"""Trang báo cáo dữ liệu thanh toán SWIFT — Phòng Tổng hợp."""
import asyncio
import json
from datetime import date
from urllib.parse import unquote

from nicegui import ui
import frontend.api_client as api
from frontend.shared import (
    _sidebar, _content_area, _page_header, _require_auth, _handle_api_error,
)


@ui.page("/th_reports")
async def th_reports_page():
    if not _require_auth():
        return
    if not api.has_feature("menu.th_reports"):
        ui.navigate.to("/home")
        return

    # ── State ────────────────────────────────────────────────────────────────
    state = {
        "in_file":   None, "in_name":  "",
        "out_file":  None, "out_name": "",
    }

    today = date.today()

    with ui.row().classes("w-full"):
        await _sidebar("th_reports")
        with _content_area():
            _page_header(
                "Báo cáo dữ liệu thanh toán",
                "Tổng hợp giao dịch chuyển tiền qua SWIFT theo quốc gia",
            )

            with ui.card().classes("w-full p-5 mb-5"):
                ui.label("Tải lên file dữ liệu").classes("text-base font-semibold text-red-800 mb-4")

                # ── Chọn kỳ báo cáo ───────────────────────────────────────────
                with ui.row().classes("items-end gap-4 mb-5"):
                    month_input = ui.number(
                        label="Tháng",
                        value=today.month,
                        min=1,
                        max=12,
                        format="%d",
                    ).classes("w-24")
                    year_input = ui.number(
                        label="Năm",
                        value=today.year,
                        min=2000,
                        max=2099,
                        format="%d",
                    ).classes("w-28")
                    ui.label("(Kỳ báo cáo)").classes("text-xs text-gray-500 pb-2")

                ui.separator().classes("my-3")

                # ── Upload hai file ───────────────────────────────────────────
                with ui.grid(columns=2).classes("w-full gap-6"):
                    with ui.column().classes("gap-1"):
                        ui.label("File Lệnh đến (IN)").classes("text-sm font-medium text-gray-700")
                        ui.label("Sheet: Result — cột CTHED, STTLM_AMT, TOTAL").classes("text-xs text-gray-500")
                        ui.upload(
                            on_upload=lambda e: state.update(
                                in_file=e.content.read(), in_name=e.name
                            ),
                            auto_upload=True,
                            max_file_size=20_000_000,
                        ).props('accept=".xlsx" flat dense label="Chọn file IN"').classes("w-full")

                    with ui.column().classes("gap-1"):
                        ui.label("File Lệnh đi (OUT)").classes("text-sm font-medium text-gray-700")
                        ui.label("Sheet: Result — cột CTHED, CUST_TYPE, TOTAL_AMT, TOTAL").classes("text-xs text-gray-500")
                        ui.upload(
                            on_upload=lambda e: state.update(
                                out_file=e.content.read(), out_name=e.name
                            ),
                            auto_upload=True,
                            max_file_size=20_000_000,
                        ).props('accept=".xlsx" flat dense label="Chọn file OUT"').classes("w-full")

                ui.separator().classes("my-4")

                gen_btn = ui.button(
                    "Tạo báo cáo",
                    icon="download",
                ).classes("bg-red-800 text-white")

            # ── Khu vực thông báo kết quả ─────────────────────────────────────
            result_area = ui.column().classes("w-full")

            # ── Cảnh báo quốc gia không có dòng trong mẫu ─────────────────────
            def _doc_bo_qua(resp_headers: dict) -> list[dict]:
                raw = resp_headers.get("x-skipped-countries") or resp_headers.get("X-Skipped-Countries")
                if not raw:
                    return []
                try:
                    return json.loads(unquote(raw))
                except Exception:
                    # Header hỏng không được phép chặn việc tải báo cáo về
                    return []

            def _ve_canh_bao(bo_qua: list[dict]):
                if not bo_qua:
                    return
                tong_den = sum(x["den"] for x in bo_qua)
                tong_di  = sum(x["di"]  for x in bo_qua)
                with ui.card().classes("w-full mt-3 p-4 bg-amber-50 border border-amber-300"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("warning", color="amber-8").classes("text-xl")
                        ui.label(
                            f"{len(bo_qua)} quốc gia / vùng lãnh thổ không có dòng trong "
                            f"mẫu D00054 — đã bỏ {tong_den} điện đến và {tong_di} điện đi "
                            f"khỏi báo cáo."
                        ).classes("text-amber-900 font-semibold text-sm")
                    ui.label(
                        "Số trên bảng vì thế NHỎ HƠN file nguồn. Kiểm lại trước khi nộp."
                    ).classes("text-amber-800 text-xs mb-2")
                    ui.table(
                        columns=[
                            {"name": "quoc_gia", "label": "Quốc gia / vùng lãnh thổ",
                             "field": "quoc_gia", "align": "left"},
                            {"name": "den",    "label": "GD đến",            "field": "den"},
                            {"name": "gt_den", "label": "Giá trị đến (nghìn)", "field": "gt_den"},
                            {"name": "di",     "label": "GD đi",             "field": "di"},
                            {"name": "gt_di",  "label": "Giá trị đi (nghìn)",  "field": "gt_di"},
                        ],
                        rows=bo_qua,
                        row_key="quoc_gia",
                    ).props("dense flat bordered").classes("w-full bg-white")

            # ── Handler ───────────────────────────────────────────────────────
            async def do_generate():
                if not state["in_file"]:
                    ui.notify("Vui lòng tải lên file Lệnh đến (IN)", type="warning")
                    return
                if not state["out_file"]:
                    ui.notify("Vui lòng tải lên file Lệnh đi (OUT)", type="warning")
                    return

                month = int(month_input.value or today.month)
                year  = int(year_input.value  or today.year)
                if not (1 <= month <= 12):
                    ui.notify("Tháng không hợp lệ (1–12)", type="warning")
                    return
                period = f"{year:04d}{month:02d}"

                gen_btn.props("loading")
                result_area.clear()
                try:
                    upload_files = {
                        "in_file":  (state["in_name"],  state["in_file"],  "application/octet-stream"),
                        "out_file": (state["out_name"], state["out_file"], "application/octet-stream"),
                    }
                    excel_bytes, resp_headers = await asyncio.to_thread(
                        api.post_upload_bytes_with_headers,
                        f"/api/th-reports/generate?period={period}",
                        upload_files,
                    )
                    filename = f"D00054-01204001-01204001-{period}-ST-M-01.xlsx"
                    ui.download(excel_bytes, filename)
                    with result_area:
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("check_circle", color="green").classes("text-xl")
                            ui.label(f"Đã tạo báo cáo kỳ {period}. File đang được tải về.").classes(
                                "text-green-700 font-medium text-sm"
                            )
                        _ve_canh_bao(_doc_bo_qua(resp_headers))
                except Exception as e:
                    if _handle_api_error(e):
                        return
                finally:
                    gen_btn.props(remove="loading")

            gen_btn.on("click", do_generate)
