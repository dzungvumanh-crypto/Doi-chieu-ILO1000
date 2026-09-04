"""API Đối chiếu CITAD ↔ PaymentHub — Phòng Thanh toán.

Port từ tool desktop độc lập (server.py + DoiChieuCITAD.py — xem
`extension_citad/README.md` để biết bối cảnh gốc). Logic buffer/session/xuất
Excel lấy từ `doi_chieu_citad_service.py` — xem docstring ở đó.

Đây là router MỚI, tự quản lý. 2 việc cần Người 1 duyệt riêng:
  1. Đăng ký router này vào backend/api/registry.py
  2. Thêm bảng doi_chieu_citad_sessions + doi_chieu_citad_extension_tokens +
     doi_chieu_citad_history vào backend/db/migrations.py

## Xác thực buffer — thiết kế lại sau review bảo mật

Bản đầu dùng 1 khoá tĩnh dùng chung (`CITAD_EXTENSION_KEY`) cho toàn Phòng
Thanh toán + field `owner` do CHÍNH Extension tự khai trong payload. Review
chỉ ra: ai có khoá cũng ghi được buffer dưới BẤT KỲ tên nào — kể cả cố tình
chèn số liệu giả để dòng chênh lệch ra đúng 0 rồi người lập bảng ký duyệt mà
không biết. Đây là lỗ hổng nặng nhất trong toàn bộ PR.

Thiết kế mới — **mã kết nối (extension token) cá nhân**:
- Người dùng đăng nhập web TTTT thật (JWT) → vào `/doi_chieu_citad` → bấm
  "Tạo mã kết nối" → nhận 1 token ngẫu nhiên (chỉ hiện ĐÚNG 1 lần) → dán vào
  Extension (`extension_citad/content.js`, hằng số `EXTENSION_TOKEN`).
- Backend chỉ lưu SHA-256 hash của token (`doi_chieu_citad_extension_tokens`,
  1 dòng/staff — tạo mã mới tự thu hồi mã cũ).
- `POST /citad-buffer`, `POST /paymenthub-buffer`: xác thực bằng header
  `X-Extension-Token`, backend TRA CỨU `owner` từ token hợp lệ trong DB —
  KHÔNG còn nhận `owner` do client tự khai trong payload nữa.
- `GET`/`DELETE` buffer, mọi endpoint session/export/token: người dùng đã
  đăng nhập gọi qua `frontend/api_client.py` (JWT) — `require_feature` +
  `current["username"]` như mọi router khác.

Token bị lộ chỉ ảnh hưởng đúng 1 người (không phải cả phòng), thu hồi được
riêng lẻ, không cần đổi khoá chung. Vẫn còn 1 rủi ro CHƯA giải quyết bằng
code: token truyền qua HTTP thường (không TLS) vẫn đọc được nếu bắt gói tin
trên mạng nội bộ — bắt buộc backend production phải chạy sau HTTPS, xem
cảnh báo tự động trong `extension_citad/content.js`.
"""
from __future__ import annotations

import io
import re

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import Response, StreamingResponse

from backend.database import get_db
from backend.core import audit_queue
from backend.core.net import header_ip_dang_tin
from backend.core.concurrency import run_heavy
from backend.core.deps import require_admin, require_feature
from backend.schemas.doi_chieu_citad import (
    CitadBufferIn,
    ExportIn,
    ExtensionTokenOut,
    ExtensionTokenStatus,
    PaymentHubBufferIn,
    SessionIn,
)
from backend.services import doi_chieu_citad_service as svc


def _safe_filename(name: str) -> str:
    """Lọc ký tự có thể phá cấu trúc header Content-Disposition (dấu ngoặc
    kép, xuống dòng, backslash) — `sheet_name` đến từ input người dùng."""
    return re.sub(r'[\r\n"\\]', '_', name)

router = APIRouter(prefix="/api/doi-chieu-citad", tags=["doi-chieu-citad"])


def _resolve_extension_owner(
    request: Request, x_extension_token: str = Header(default=""), db=Depends(get_db)
) -> str:
    """Dependency cho 2 endpoint POST buffer — trả về username chủ token
    hợp lệ, KHÔNG bao giờ tin owner do client tự khai.

    Tự ghi audit ở ĐÂY (actor_id đúng người) thay vì để AuditMiddleware chung
    ghi — middleware đó chỉ đọc JWT qua header Authorization, không biết
    X-Extension-Token là ai nên mọi dòng audit từ Extension trước đây đều có
    actor_id=NULL dù backend tra được chính xác. Do middleware chung vẫn sẽ
    ghi thêm 1 dòng NỮA cho cùng request nếu không chặn, đã thêm
    '/api/doi-chieu-citad/citad-buffer' và '/paymenthub-buffer' vào
    _SKIP_PREFIXES trong backend/core/audit_middleware.py (đúng mục đích
    _SKIP_PREFIXES ghi sẵn: "tự ghi audit riêng ... middleware bỏ qua") —
    PHẢI sửa cùng lúc, không thì sẽ có double audit.

    Ghi qua `audit_queue.enqueue()` chứ KHÔNG dùng `write_audit()` đồng bộ:
    đây là 2 endpoint tần suất cao nhất hệ thống (Extension tự gửi mỗi lần
    có số liệu mới), mà ghi audit đồng bộ trên request từng làm mỗi POST
    chậm thêm 5,5 giây khi có lệnh ghi khác đang giữ khoá DB — đúng lý do
    commit "perf: gỡ nghẽn backend" đẩy toàn bộ audit sang hàng đợi nền.
    Hàng đợi cũng không bao giờ raise và ghi bằng kết nối riêng, nên không
    còn phải commit trước khi raise như bản đồng bộ trước đây."""
    resolved = svc.resolve_extension_token(db, x_extension_token)
    client_ip = request.client.host if request.client else None
    # Header chỉ đáng tin khi bên gọi là proxy frontend chạy cùng máy — xem
    # backend/core/net.py. Extension đi qua đúng đường đó (frontend/api_proxy.py).
    ip_hdr = header_ip_dang_tin(client_ip, request.headers.get("X-Client-IP"))
    if not resolved:
        # Ghi audit CẢ khi token không hợp lệ/đã bị thu hồi — đây là tín hiệu
        # cần theo dõi (máy quên cập nhật token mới, hoặc có người đang dò
        # token), đặc biệt vì cơ chế thử lại phía Extension có backoff tới 5
        # phút nên 1 máy cấu hình sai sẽ âm thầm gửi mãi. _SKIP_PREFIXES đã
        # chặn AuditMiddleware chung ghi thay cho 2 đường dẫn này, nên nếu
        # không tự ghi ở đây thì request thất bại sẽ KHÔNG ĐỂ LẠI VẾT GÌ.
        audit_queue.enqueue(
            request.method, request.url.path, 403, "", ip_hdr, client_ip,
            actor_id=None,
            detail="THẤT BẠI: mã kết nối Extension không hợp lệ hoặc đã bị thu hồi",
        )
        raise HTTPException(
            status_code=403,
            detail="Mã kết nối Extension không hợp lệ hoặc đã bị thu hồi — "
            "vào /doi_chieu_citad, mục 'Kết nối Extension' để tạo mã mới.",
        )
    staff_id, owner = resolved
    # KHÔNG ghi audit cho lượt gửi THÀNH CÔNG — đây là 2 endpoint tần suất cao
    # nhất hệ thống (Extension tự gửi mỗi lần có số liệu mới), ghi mỗi lần chỉ
    # tạo hàng nghìn dòng audit vô nghĩa (đều là cùng 1 hành vi lặp lại) làm
    # trôi mất các dòng audit có ý nghĩa khác trong màn Nhật ký hệ thống. Lượt
    # THẤT BẠI (token sai/thu hồi) vẫn ghi ở trên — đó mới là tín hiệu cần biết.
    return owner


# ── CITAD buffer ─────────────────────────────────────────────────────────
# POST: Extension gọi (xác thực bằng token cá nhân, không JWT). GET/DELETE:
# người dùng web gọi (JWT, tự động chỉ thấy/xoá buffer của chính mình).
@router.post("/citad-buffer")
def save_citad_buffer(data: CitadBufferIn, owner: str = Depends(_resolve_extension_owner)):
    svc.buffer_save_citad(owner, data.model_dump())
    return {"ok": True}


@router.get("/citad-buffer")
def get_citad_buffer(current: dict = Depends(require_feature("menu.doi_chieu_citad"))):
    return svc.buffer_get_citad(current["username"])


@router.delete("/citad-buffer")
def clear_citad_buffer(current: dict = Depends(require_feature("menu.doi_chieu_citad"))):
    svc.buffer_clear_citad(current["username"])
    return {"ok": True}


# ── PaymentHub buffer ────────────────────────────────────────────────────
@router.post("/paymenthub-buffer")
def save_ph_buffer(data: PaymentHubBufferIn, owner: str = Depends(_resolve_extension_owner)):
    svc.buffer_save_ph(owner, data.items)
    return {"ok": True}


@router.get("/paymenthub-buffer")
def get_ph_buffer(current: dict = Depends(require_feature("menu.doi_chieu_citad"))):
    return svc.buffer_get_ph(current["username"])


@router.delete("/paymenthub-buffer")
def clear_ph_buffer(current: dict = Depends(require_feature("menu.doi_chieu_citad"))):
    svc.buffer_clear_ph(current["username"])
    return {"ok": True}


# ── Mã kết nối Extension (thay CITAD_EXTENSION_KEY dùng chung) ───────────
@router.get("/extension-token/status", response_model=ExtensionTokenStatus)
def extension_token_status(db=Depends(get_db), current: dict = Depends(require_feature("menu.doi_chieu_citad"))):
    return svc.get_extension_token_status(db, current["id"])


@router.post("/extension-token", response_model=ExtensionTokenOut)
def create_extension_token(db=Depends(get_db), current: dict = Depends(require_feature("menu.doi_chieu_citad"))):
    """Tạo mã mới — TỰ ĐỘNG thu hồi mã cũ (1 token/người). Trả plaintext
    ĐÚNG 1 LẦN, backend chỉ lưu hash, không xem lại được."""
    token = svc.generate_extension_token(db, current["id"])
    return {"token": token}


@router.delete("/extension-token")
def delete_extension_token(db=Depends(get_db), current: dict = Depends(require_feature("menu.doi_chieu_citad"))):
    svc.revoke_extension_token(db, current["id"])
    return {"ok": True}


@router.get("/extension-download")
def download_extension(current: dict = Depends(require_feature("menu.doi_chieu_citad"))):
    """Tải extension_citad/ dạng .zip để người dùng tự giải nén + Load
    unpacked — Chrome không cho web tự cài extension, đây chỉ là bước tải
    file cho tiện, không thay thế được thao tác cài thủ công."""
    try:
        content = svc.build_extension_zip()
    except FileNotFoundError as e:
        raise HTTPException(500, str(e))
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="extension_citad.zip"'},
    )


@router.get("/extension-version")
def extension_version(current: dict = Depends(require_feature("menu.doi_chieu_citad"))):
    """Version mới nhất backend đang phát hành (đọc từ manifest.json) —
    frontend so với version Extension đang cài trên máy để báo popup nhắc
    cập nhật nếu khác nhau."""
    return {"version": svc.get_extension_latest_version()}


# ── Session theo (ngay, created_by) — mỗi người 1 bảng riêng/ngày, xem
# docstring session_save trong service ────────────────────────────────────
# QUAN TRỌNG: {ngay:path} là path converter "tham lam" (khớp cả dấu "/"
# trong ngay=dd/mm/yyyy) — Starlette khớp route theo ĐÚNG THỨ TỰ ĐĂNG KÝ,
# nên MỌI route có tiền tố "/session/{ngay:path}" phải đăng ký các route cụ
# thể hơn ("/history", ...) TRƯỚC route trần "/session/{ngay:path}". Nếu
# đăng ký sai thứ tự, "/session/{ngay:path}" (rộng hơn) sẽ nuốt mất request
# đáng lẽ khớp route cụ thể hơn (đã từng gây lỗi: gọi .../history luôn rơi
# vào get_session(), coi "<ngay>/history" là 1 chuỗi ngay, trả về rỗng).
@router.get("/sessions")
def list_sessions(db=Depends(get_db), current: dict = Depends(require_feature("menu.doi_chieu_citad"))):
    return svc.session_list(db)


@router.get("/reconciliation-days")
def get_reconciliation_days(
    tu_ngay: str | None = None,
    den_ngay: str | None = None,
    nguoi_cham: str | None = None,
    db=Depends(get_db),
    current: dict = Depends(require_feature("menu.doi_chieu_citad")),
):
    """1 dòng/bảng đã có ai chấm (1 ngày có thể nhiều dòng nếu nhiều người
    đều tự lập bảng riêng) — phục vụ tab "Lịch sử" (bảng nhiều ngày, lọc
    theo khoảng ngày + tên người chấm). tu_ngay/den_ngay dạng dd/mm/yyyy,
    để trống = không giới hạn đầu/cuối. nguoi_cham khớp gần đúng (không
    phân biệt hoa/thường), theo cả tên đầy đủ lẫn username."""
    return svc.get_reconciliation_days(db, tu_ngay, den_ngay, nguoi_cham)


@router.get("/session/{ngay:path}/history")
def get_reconciliation_history(
    ngay: str,
    created_by: int,
    db=Depends(get_db),
    current: dict = Depends(require_feature("menu.doi_chieu_citad")),
):
    """Lịch sử từng lần lưu của ĐÚNG 1 bảng (`created_by` — id người lập
    bảng đó, lấy từ dòng tương ứng ở get_reconciliation_days) — mỗi dòng
    gắn username người đã chấm dòng đó."""
    return svc.get_reconciliation_history(db, ngay, created_by)


@router.get("/session/{ngay:path}")
def get_session(
    ngay: str,
    created_by: int | None = None,
    db=Depends(get_db),
    current: dict = Depends(require_feature("menu.doi_chieu_citad")),
):
    """Mặc định (`created_by` bỏ trống) trả về bảng CỦA CHÍNH người gọi cho
    ngày này. Truyền `created_by` để xem bảng của người khác (vd sau khi
    Admin mở khoá bảng của người khác, cần tải lại đúng bảng đó)."""
    owner = created_by if created_by is not None else current["id"]
    return svc.session_get(db, ngay, owner) or {}


@router.post("/session")
def save_session(
    data: SessionIn, db=Depends(get_db), current: dict = Depends(require_feature("menu.doi_chieu_citad"))
):
    """"Lưu bản tạm" (status='draft') hay "Lưu bản cuối" (status='final') —
    xem session_save() trong service cho quy tắc ai được sửa gì.
    `target_created_by` bỏ trống = bảng của chính người gọi; có giá trị =
    đang góp Napas/PSS-MDP vào bảng người khác đã lập. 403 khi bảng đã chốt
    (SessionLockedError) hoặc người gọi không phải người lập bảng nhưng cố
    sửa ngoài Napas/PSS-MDP hay cố chốt bản cuối (SessionForbiddenError)."""
    payload = data.model_dump()
    status = payload.pop("status")
    target_created_by = payload.pop("target_created_by")
    try:
        svc.session_save(db, data.ngay, current["id"], payload, status, target_created_by)
    except (svc.SessionLockedError, svc.SessionForbiddenError) as e:
        raise HTTPException(403, str(e))
    return {"ok": True}


@router.delete("/session/{ngay:path}")
def delete_session(
    ngay: str, db=Depends(get_db), current: dict = Depends(require_feature("menu.doi_chieu_citad"))
):
    """Xoá bảng CỦA CHÍNH người gọi cho ngày này — không đụng bảng người
    khác cùng ngày (nếu có)."""
    try:
        svc.session_delete(db, ngay, current["id"])
    except (svc.SessionLockedError, svc.SessionForbiddenError) as e:
        raise HTTPException(403, str(e))
    return {"ok": True}


@router.post("/session/{ngay:path}/unlock")
def unlock_session(
    ngay: str,
    created_by: int,
    db=Depends(get_db),
    current: dict = Depends(require_admin),
):
    """Chỉ Admin — mở khoá ĐÚNG 1 bảng (`created_by` — id người lập bảng đó)
    đã "Lưu bản cuối" về lại bản tạm để người lập bảng sửa tiếp.
    `created_by` bắt buộc: 1 ngày có thể có nhiều bảng đã chốt của nhiều
    người khác nhau. Không phải xoá số liệu, chỉ đổi status."""
    svc.session_admin_unlock(db, ngay, created_by)
    return {"ok": True}


@router.get("/history-entry/{history_id}")
def get_history_entry(
    history_id: int, db=Depends(get_db), current: dict = Depends(require_feature("menu.doi_chieu_citad"))
):
    """Số liệu nguyên vẹn của đúng 1 dòng trong lịch sử — phục vụ nút "Tải"
    trên từng dòng ở dialog "Lịch sử đối chiếu"."""
    data = svc.get_history_entry_data(db, history_id)
    if data is None:
        raise HTTPException(404, "Không tìm thấy bản ghi lịch sử này")
    return data


@router.get("/history-entry/{history_id}/edits")
def get_history_entry_edits(
    history_id: int, db=Depends(get_db), current: dict = Depends(require_feature("menu.doi_chieu_citad"))
):
    """Danh sách người đã lưu góp phần vào dòng lịch sử này, kèm thời gian —
    phục vụ icon "Ai đã sửa" trên mỗi dòng ở tab Lịch sử."""
    return svc.get_history_edits(db, history_id)


# ── Xuất Excel ────────────────────────────────────────────────────────────
@router.post("/export")
async def export_excel(data: ExportIn, current: dict = Depends(require_feature("menu.doi_chieu_citad"))):
    # build_xlsx() dựng workbook openpyxl — việc nặng, phải qua run_heavy()
    # để nằm trong giới hạn dùng chung (backend/core/concurrency.py). Khai
    # `def` thường thì rơi vào bể 40 token chung của anyio, ngoài giới hạn đó.
    buf = await run_heavy(svc.build_xlsx, data)
    fname = _safe_filename(f"Doi_chieu_CITAD_{data.sheet_name}.xlsx")
    return StreamingResponse(
        io.BytesIO(buf),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
