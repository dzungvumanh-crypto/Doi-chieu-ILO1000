"""HTTP client kết nối tới FastAPI backend — token lưu per-user qua app.storage.user"""
import os
import httpx
from typing import Optional, Any, Dict
from nicegui import app
from dotenv import load_dotenv

load_dotenv(override=True)
# BACKEND_URL suy ra từ BACKEND_PORT nếu không set riêng — tránh quên đồng bộ
# khi đổi cổng (vd. hệ thống test dùng .env khác với BACKEND_PORT=9000)
# Dùng 127.0.0.1 chứ KHÔNG dùng localhost: trên Windows `localhost` phân giải ra
# ::1 (IPv6) trước, mà uvicorn --host 0.0.0.0 chỉ lắng nghe IPv4. Mỗi lần httpx
# mở kết nối MỚI (sau ~5s nhàn rỗi là pool hết hạn) sẽ chờ IPv6 thất bại ~2 giây
# rồi mới quay sang IPv4. Đo được: localhost 2062ms vs 127.0.0.1 18ms.
BACKEND_URL = os.getenv("BACKEND_URL", f"http://127.0.0.1:{os.getenv('BACKEND_PORT', '8000')}")


class ApiFileError(Exception):
    """Lỗi 400 có kèm danh sách tên file cụ thể gây lỗi (vd DtbbFileError.filenames) —
    backend trả detail dạng dict {"message":..., "filenames":[...]} thay vì chuỗi
    thường. FE dùng .filenames để tô đỏ đúng file trong danh sách đã chọn."""

    def __init__(self, message: str, filenames: list | None = None):
        super().__init__(message)
        self.filenames = filenames or []


class QuotaExceededBorrowError(Exception):
    """Lỗi 409 khi tạo/nộp lại/khai báo hộ đơn nghỉ phép vượt hạn mức năm nay —
    backend trả detail dạng dict {"code":"quota_exceeded_borrow", "year", "next_year",
    "remaining", "borrow_days"} (xem _check_quota_or_borrow ở backend/api/leaves.py).
    FE dùng để hỏi xác nhận "ứng phép năm sau" thay vì chặn cứng."""

    def __init__(self, detail: dict):
        super().__init__("Vượt quá số ngày phép còn lại")
        self.year = detail.get("year")
        self.next_year = detail.get("next_year")
        self.remaining = detail.get("remaining")
        self.borrow_days = detail.get("borrow_days")


class SessionExpiredError(Exception):
    """Raised khi backend trả 401 — session đã hết hạn hoặc đã logout."""
    pass


class DisplacedSessionError(Exception):
    """Raised khi phiên bị thay thế bởi đăng nhập mới từ thiết bị khác."""
    pass


class MustChangePasswordError(Exception):
    """Raised khi backend chặn vì tài khoản chưa đổi mật khẩu bắt buộc.

    Trước đây việc bắt đổi mật khẩu chỉ là một lần chuyển trang ở màn hình đăng
    nhập — gõ thẳng /home lên thanh địa chỉ là đi tiếp được. Nay backend chặn
    thật, nên frontend phải nhận ra và đưa người dùng về đúng chỗ."""
    pass


# Persistent client — tái dùng TCP connection, tránh overhead kết nối mỗi request
_client = httpx.Client(timeout=httpx.Timeout(10.0))
_download_client = httpx.Client(timeout=httpx.Timeout(60.0))


def set_token(token: str, user: dict):
    app.storage.user["token"] = token
    app.storage.user["user_data"] = user


def get_current_user() -> Optional[Dict]:
    return app.storage.user.get("user_data")


def clear_auth():
    app.storage.user.pop("token", None)
    app.storage.user.pop("user_data", None)
    app.storage.user.pop("features", None)


def load_my_features() -> None:
    """Gọi sau login. Lưu features vào app.storage.user['features'].
    features=None → admin (all-access). features=[] → không có nhóm nào.
    """
    try:
        result = get("/api/auth/my-features")
        app.storage.user["features"] = result.get("features")  # None hoặc list[str]
    except Exception:
        app.storage.user["features"] = []  # safe fallback


def has_feature(code: str) -> bool:
    """Kiểm tra user có feature code này không.
    Admin (features=None) → True cho mọi code.
    """
    user = get_current_user()
    if not user:
        return False
    if user.get("role") == "admin":
        return True
    features = app.storage.user.get("features")
    if features is None:
        # Chưa load hoặc admin — check role thêm lần nữa
        return user.get("role") == "admin"
    return code in features


def get_all_features() -> list:
    """GET /api/groups/features/all — danh sách feature definitions theo nhóm."""
    return get("/api/groups/features/all")


def login(username: str, password: str, client_ip: str = None, force: bool = False) -> Any:
    """Login without an existing token. Passes real browser IP via X-Client-IP."""
    headers = {"Content-Type": "application/json"}
    if client_ip:
        headers["X-Client-IP"] = client_ip
    try:
        r = _client.post(
            f"{BACKEND_URL}/api/auth/login",
            headers=headers,
            json={"username": username, "password": password, "force": force},
        )
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        raise Exception(_parse_error(e))
    except Exception as e:
        raise Exception(str(e))


def logout_session() -> None:
    """Notify backend to clear the session. Ignores errors (token may already be invalid)."""
    try:
        _client.post(
            f"{BACKEND_URL}/api/auth/logout",
            headers=_headers(),
            json={},
        )
    except Exception:
        pass


def _headers():
    h = {"Content-Type": "application/json"}
    token = app.storage.user.get("token")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def la_loi_mang(e: Exception) -> bool:
    """True khi máy chủ KHÔNG trả lời (hết giờ chờ, không nối được, đứt giữa chừng);
    False khi nó có trả lời nhưng là mã lỗi (404, 500...).

    Hai thứ này đòi hai cách xử lý ngược nhau ở phía gọi: im lặng thì phải thử lại
    và phải coi việc đang chạy là VẪN CÒN; còn trả lời 404 là câu trả lời dứt khoát,
    thử lại chỉ tổ mất thời gian và báo sai cho người dùng.

    `get()`/`post()` gói HTTPStatusError thành `Exception` thường (mất kiểu), còn
    lỗi mạng thì để nguyên kiểu httpx — nên chỉ cần hỏi "có phải httpx.HTTPError không".
    """
    return isinstance(e, httpx.HTTPError)


def _parse_error(e: "httpx.HTTPStatusError") -> str:
    try:
        body = e.response.json()
    except Exception:
        return str(e)
    detail = body.get("detail", "")
    # detail kiểu dict là quy ước sẵn có cho lỗi cần kèm dữ liệu (xem
    # post_upload_bytes): lấy 'message' ra, đừng in nguyên cái dict cho người dùng đọc.
    if isinstance(detail, dict):
        return str(detail.get("message") or detail)
    if isinstance(detail, list):
        parts = []
        for err in detail:
            loc = [str(x) for x in err.get("loc", []) if x not in ("body", "query")]
            msg = err.get("msg", "")
            parts.append(f"{'.'.join(loc)}: {msg}" if loc else msg)
        return "; ".join(parts) or str(e)
    return str(detail) or str(e)


def _raise_http_error(e: httpx.HTTPStatusError):
    if e.response.status_code == 401:
        clear_auth()
        try:
            detail = e.response.json().get("detail", "")
        except Exception:
            detail = ""
        if "__session_displaced__" in str(detail):
            raise DisplacedSessionError("Tài khoản này đang được đăng nhập từ thiết bị khác")
        raise SessionExpiredError("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.")
    if e.response.status_code == 403:
        try:
            detail = e.response.json().get("detail", "")
        except Exception:
            detail = ""
        if "__must_change_password__" in str(detail):
            # KHÔNG clear_auth(): token vẫn hợp lệ, người dùng cần nó để gọi
            # /api/auth/change-password. Xoá đi là đá họ về màn hình đăng nhập,
            # đăng nhập lại cũng vấp đúng chỗ này — vòng lặp không lối ra.
            raise MustChangePasswordError(
                "Bạn phải đổi mật khẩu trước khi sử dụng hệ thống"
            )
    # detail dạng dict có "filenames" — lỗi có cấu trúc (vd DtbbFileError), không phải
    # str/list detail thông thường. Chỉ endpoint nào chủ động trả dạng này mới vào
    # nhánh này — không đổi hành vi của các endpoint khác (luôn trả str/list detail).
    try:
        raw_detail = e.response.json().get("detail", "")
    except Exception:
        raw_detail = None
    if isinstance(raw_detail, dict) and "filenames" in raw_detail:
        raise ApiFileError(raw_detail.get("message") or str(raw_detail), raw_detail.get("filenames"))
    if (e.response.status_code == 409 and isinstance(raw_detail, dict)
            and raw_detail.get("code") == "quota_exceeded_borrow"):
        raise QuotaExceededBorrowError(raw_detail)
    raise Exception(_parse_error(e))


def get(path: str, params: dict = None, timeout: float = None) -> Any:
    # timeout: chỉ truyền cho endpoint chậm bất thường (vd. xem trước đơn nghỉ phép
    # phải chờ Word dựng PDF ~7s) — mặc định 10s của _client là đủ cho phần còn lại.
    try:
        kw = {} if timeout is None else {"timeout": timeout}
        r = _client.get(f"{BACKEND_URL}{path}", headers=_headers(), params=params, **kw)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        _raise_http_error(e)


def get_bytes(path: str, params: dict = None) -> bytes:
    """GET endpoint trả về raw bytes (Excel, ZIP...)."""
    try:
        r = _download_client.get(f"{BACKEND_URL}{path}", headers=_headers(), params=params)
        r.raise_for_status()
        return r.content
    except httpx.HTTPStatusError as e:
        _raise_http_error(e)
    except Exception as e:
        raise Exception(str(e))


def post(path: str, data: dict = None, timeout: float = None) -> Any:
    try:
        kw = {} if timeout is None else {"timeout": timeout}
        r = _client.post(f"{BACKEND_URL}{path}", headers=_headers(), json=data, **kw)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        _raise_http_error(e)
    except Exception as e:
        raise Exception(str(e))


def put(path: str, data: dict = None) -> Any:
    try:
        r = _client.put(f"{BACKEND_URL}{path}", headers=_headers(), json=data)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        _raise_http_error(e)
    except Exception as e:
        raise Exception(str(e))


def patch(path: str, data: dict = None, timeout: float = None) -> Any:
    # timeout: cho lời gọi chạy trong nhịp đồng hồ (vd. lưu tiến độ bài trắc
    # nghiệm mỗi mấy giây) — 10s mặc định của _client là quá dài ở đó, mạng
    # chập chờn sẽ làm đồng hồ đứng hình chờ một lần lưu.
    try:
        kw = {} if timeout is None else {"timeout": timeout}
        r = _client.patch(f"{BACKEND_URL}{path}", headers=_headers(), json=data, **kw)
        r.raise_for_status()
        try:
            return r.json()
        except Exception:
            return {}
    except httpx.HTTPStatusError as e:
        _raise_http_error(e)
    except Exception as e:
        raise Exception(str(e))


def delete(path: str) -> Any:
    try:
        r = _client.delete(f"{BACKEND_URL}{path}", headers=_headers())
        r.raise_for_status()
        try:
            return r.json()
        except Exception:
            return {}
    except httpx.HTTPStatusError as e:
        _raise_http_error(e)
    except Exception as e:
        raise Exception(str(e))


def post_upload_bytes(path: str, files: dict) -> bytes:
    """Multipart POST, nhận bytes response (ZIP, Excel…). Dùng cho generate-dept-zip."""
    try:
        h = {k: v for k, v in _headers().items() if k != "Content-Type"}
        r = _download_client.post(f"{BACKEND_URL}{path}", headers=h, files=files)
        r.raise_for_status()
        return r.content
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            clear_auth()
            raise SessionExpiredError("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.")
        try:
            body = e.response.json()
            detail = body.get("detail", "")
            if isinstance(detail, dict):
                raise Exception(detail.get("message", str(detail)))
            raise Exception(str(detail) or e.response.text)
        except SessionExpiredError:
            raise
        except Exception as inner:
            raise Exception(str(inner))
    except Exception as e:
        raise Exception(str(e))


def post_upload(path: str, files, data: dict = None, timeout: float = None) -> Any:
    """Gửi multipart/form-data (file upload). Hai dạng `files`:
      - dict: {'field': (name, bytes, mime)} — mỗi field một file
      - list: [('field', (name, bytes, mime)), ...] — BẮT BUỘC khi backend nhận
        `list[UploadFile]`, vì khi đó nhiều part dùng CHUNG một tên field (dict
        không thể có key trùng). Ví dụ: /api/ach/start.
    timeout=None giữ mặc định 60s của _download_client; truyền số lớn hơn cho
    endpoint upload nặng (ACH cho tới 500 MB, backend ghi hết ra đĩa mới trả lời).
    """
    try:
        h = {k: v for k, v in _headers().items() if k != "Content-Type"}
        kw = {"timeout": timeout} if timeout is not None else {}
        r = _download_client.post(f"{BACKEND_URL}{path}", headers=h, files=files,
                                  data=data or {}, **kw)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        _raise_http_error(e)
    except Exception as e:
        raise Exception(str(e))


def post_download(path: str, data: dict = None, timeout: float = None) -> bytes:
    """POST với JSON body, nhận bytes (Excel/Word).

    timeout=None giữ mặc định 60s của _download_client; truyền số lớn hơn cho
    endpoint sinh file rất lớn. Cùng khuôn mẫu với post_upload() phía trên —
    nút "Xuất tất cả lệnh" (doi_soat_citad) có thể xuất tới ~38.000 dòng và
    còn phải xếp hàng chờ suất run_heavy() dùng chung cả backend, nên 60s
    mặc định là quá sát.
    """
    try:
        kw = {"timeout": timeout} if timeout is not None else {}
        r = _download_client.post(f"{BACKEND_URL}{path}", headers=_headers(),
                                  json=data or {}, **kw)
        r.raise_for_status()
        return r.content
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            clear_auth()
            raise SessionExpiredError("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.")
        raise Exception(e.response.text)
    except Exception as e:
        raise Exception(str(e))


def download(path: str, params: dict = None, timeout: float = None) -> bytes:
    """Download file (docx, xlsx, etc.)

    timeout=None giữ mặc định 60s của _download_client — không đủ cho phiếu nghỉ
    phép PDF: backend cho phép Word khởi động nguội mất tới 150s
    (leave_pdf._CONVERT_TIMEOUT) trước khi coi là treo thật. Trước đây route này
    không có cách nào nâng timeout như post_upload()/post_download() ở trên nên
    ai bấm "Tải phiếu" đúng lúc Word chưa ấm sẽ bị rớt về bản .docx chưa ký dù
    server không hề lỗi, chỉ đang xử lý chậm — xem caller ở leaves.py.
    """
    try:
        kw = {"timeout": timeout} if timeout is not None else {}
        r = _download_client.get(f"{BACKEND_URL}{path}", headers=_headers(), params=params, **kw)
        r.raise_for_status()
        return r.content
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            clear_auth()
            raise SessionExpiredError("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.")
        raise Exception(e.response.text)
    except Exception as e:
        raise Exception(str(e))
