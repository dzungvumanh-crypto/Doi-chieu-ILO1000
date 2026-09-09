"""API endpoints báo cáo dữ liệu thanh toán SWIFT — Phòng Tổng hợp."""
import json
import logging
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import Response

from backend.core.concurrency import run_heavy
from backend.core.deps import require_feature
from backend.services.th_report_service import (
    parse_incoming, parse_outgoing, fill_template,
)

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/th-reports", tags=["th-reports"])


def _dl_headers(filename: str) -> dict:
    fallback = "".join(ch if ord(ch) < 128 and ch not in '\\"' else "_" for ch in filename)
    return {
        "Content-Disposition": (
            f'attachment; filename="{fallback}"; '
            f"filename*=UTF-8''{quote(filename, safe='')}"
        )
    }


@router.post("/generate")
async def generate_payment_report(
    in_file: UploadFile = File(...),
    out_file: UploadFile = File(...),
    period: str = Query(..., description="Kỳ báo cáo định dạng YYYYMM, ví dụ: 202605"),
    current: dict = Depends(require_feature("menu.th_reports")),
):
    """Nhận file Lệnh đến + Lệnh đi, điền vào mẫu D00054 và trả về file Excel."""
    # ── Validate period format ────────────────────────────────────────────────
    period = period.strip()
    if len(period) != 6 or not period.isdigit():
        raise HTTPException(status_code=400, detail="period phải có định dạng YYYYMM (6 chữ số)")

    # ── Đọc file bytes ────────────────────────────────────────────────────────
    try:
        in_bytes = await in_file.read()
        out_bytes = await out_file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Không thể đọc file: {e}")

    # ── Parse ─────────────────────────────────────────────────────────────────
    try:
        incoming = await run_heavy(parse_incoming, in_bytes)
    except Exception as e:
        log.exception("Lỗi parse file Lệnh đến")
        raise HTTPException(status_code=400, detail=f"File Lệnh đến không hợp lệ: {e}")

    try:
        outgoing = await run_heavy(parse_outgoing, out_bytes)
    except Exception as e:
        log.exception("Lỗi parse file Lệnh đi")
        raise HTTPException(status_code=400, detail=f"File Lệnh đi không hợp lệ: {e}")

    # ── Fill template ─────────────────────────────────────────────────────────
    try:
        excel_bytes, bo_qua = await run_heavy(fill_template, incoming, outgoing, period)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Template báo cáo không tìm thấy trên server")
    except Exception as e:
        log.exception("Lỗi fill template")
        raise HTTPException(status_code=500, detail=f"Lỗi tạo báo cáo: {e}")

    filename = f"D00054-01204001-01204001-{period}-ST-M-01.xlsx"
    headers = _dl_headers(filename)
    # Cảnh báo đi kèm THÂN FILE nên phải nhét vào header: đổi response sang JSON
    # bọc file base64 thì phình 33% và hỏng đường tải xuống hiện có.
    # URL-encode vì header HTTP chỉ chở được latin-1.
    headers["X-Skipped-Countries"] = quote(json.dumps(bo_qua, ensure_ascii=True))
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )
