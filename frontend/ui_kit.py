"""Bộ giao diện dùng chung — nguồn sự thật duy nhất cho màu, trạng thái, khung chờ.

Nguyên tắc: mỗi hàm ở đây phải NGẮN HƠN cách viết tay, nếu không sẽ không ai dùng
(xem `_card()` trong shared.py — dựng xong nhưng chỉ 1 trang dùng).
"""
from nicegui import ui

# ── Bảng màu ──────────────────────────────────────────────────────────────────
# shared.COLORS trỏ về đây. Đổi tông Agribank thì sửa duy nhất chỗ này.
COLORS = {
    "primary": "#8B0000",
    "accent":  "#C00000",
    "bg":      "#F5F7FA",
    "card":    "#FFFFFF",
    "text":    "#1A1A2E",
    "muted":   "#6B7280",   # đạt WCAG AA trên nền trắng (4.83:1)
    "border":  "#E5E7EB",
    "success": "#16A34A",
    "warning": "#D97706",
    "danger":  "#DC2626",
}

# Cỡ chữ nền tảng. B5 sẽ nâng "base" 12px → 14px cùng lúc với làm lại bảng —
# đổi riêng ở đây sẽ vỡ bố cục các bảng đang vừa khít.
FONT_SIZES = {"xs": "12px", "base": "12px", "md": "14px", "lg": "16px", "xl": "20px"}

RADIUS = {"sm": "4px", "md": "8px", "lg": "12px"}


def _css_vars() -> str:
    parts = [f"--c-{k}: {v};" for k, v in COLORS.items()]
    parts += [f"--fs-{k}: {v};" for k, v in FONT_SIZES.items()]
    parts += [f"--r-{k}: {v};" for k, v in RADIUS.items()]
    return ":root { " + " ".join(parts) + " }"


# ── Trạng thái nghiệp vụ ──────────────────────────────────────────────────────
# Khoá phẳng, không chia theo màn hình → gọi chỉ cần 1 tham số.
# Va chạm duy nhất khi gộp: "rejected" trước đây là "Bị từ chối" (bàn giao) và
# "Từ chối" (nghỉ phép). Đã thống nhất thành "Từ chối".
_CHIP = "text-xs font-medium px-2 py-0.5 rounded border whitespace-nowrap"

# chip = class Tailwind cho <label>; dot = hex cho chấm tròn; cell = (nền, viền) hex
# cho ô lưới dựng bằng HTML thô. Trạng thái nào không tô ô thì bỏ khoá "cell".
STATUS = {
    # ── Bàn giao chứng từ (document_entries.entry_status) ──
    "pending_confirm":  {"label": "Chờ xác nhận", "chip": "bg-orange-100 text-orange-700 border-orange-300",
                         "dot": "#D97706", "cell": ("#FEF3C7", "#F59E0B")},
    "confirmed":        {"label": "Đã xác nhận",  "chip": "bg-green-100 text-green-700 border-green-300",
                         "dot": "#16A34A", "cell": ("#DCFCE7", "#16A34A")},
    "borrowed":         {"label": "Đang mượn",    "chip": "bg-purple-100 text-purple-700 border-purple-300",
                         "dot": "#7C3AED", "cell": ("#EDE9FE", "#7C3AED")},
    # ── Nghỉ phép (leave_records.status) ──
    "pending_ksv":      {"label": "Chờ KSV duyệt", "chip": "bg-orange-100 text-orange-700 border-orange-300",
                         "dot": "#D97706"},
    "pending_tong_hop": {"label": "Chờ Tổng hợp",  "chip": "bg-yellow-100 text-yellow-700 border-yellow-300",
                         "dot": "#CA8A04"},
    "pending_gd":       {"label": "Chờ Ban lãnh đạo duyệt", "chip": "bg-blue-100 text-blue-700 border-blue-300",
                         "dot": "#2563EB"},
    "approved":         {"label": "Hoàn thành",    "chip": "bg-green-100 text-green-700 border-green-300",
                         "dot": "#16A34A"},
    "rejected":         {"label": "Từ chối",       "chip": "bg-red-100 text-red-700 border-red-300",
                         "dot": "#DC2626", "cell": ("#FEE2E2", "#DC2626")},
    "cancelled":        {"label": "Đã hủy",        "chip": "bg-gray-100 text-gray-500 border-gray-300",
                         "dot": "#6B7280"},
    # ── Lịch trực + bàn giao ở trạng thái nháp (duty_shifts / handovers.status) ──
    "draft":            {"label": "Bản thảo",      "chip": "bg-gray-100 text-gray-600 border-gray-300",
                         "dot": "#6B7280"},
}

_UNKNOWN = {"label": "", "chip": "bg-gray-100 text-gray-500 border-gray-300", "dot": COLORS["muted"]}

# Loại nghỉ phép — đặt ở đây thay vì trong leaves.py vì sidebar cũng cần đọc,
# mà shared.py không import được leaves.py (leaves.py đã import shared.py).
LEAVE_TYPE = {
    "bat_buoc":    "Nghỉ phép bắt buộc",
    "annual":      "Nghỉ phép năm",
    "thai_san":    "Nghỉ thai sản",
    "bao_hiem":    "Nghỉ bảo hiểm",
    "khong_luong":  "Nghỉ không lương",
    "hop_cong_tac": "Họp/Công tác",
    "other":        "Khác",
}


def _spec(code: str) -> dict:
    return STATUS.get(code, _UNKNOWN)


def status_label(code: str) -> str:
    """Nhãn tiếng Việt. Mã lạ → trả về nguyên mã để lộ ra, không nuốt."""
    return STATUS.get(code, {}).get("label") or code


def status_dot(code: str) -> str:
    """Mã hex cho chấm tròn / chữ màu trong HTML thô."""
    return _spec(code).get("dot", COLORS["muted"])


def status_cell(code: str) -> tuple[str, str] | None:
    """(nền, viền) hex cho ô lưới. None nếu trạng thái này không tô ô."""
    return _spec(code).get("cell")


def status_chip(code: str):
    return ui.label(status_label(code)).classes(f"{_CHIP} {_spec(code)['chip']}")


# ── Trạng thái rỗng ───────────────────────────────────────────────────────────
def empty_state(message: str, icon: str = "inbox", hint: str = ""):
    """Dùng thay chuỗi 'Chưa có...' viết tay. Không thêm dấu chấm cuối câu."""
    with ui.column().classes("w-full items-center justify-center py-10 gap-2") as box:
        ui.icon(icon).classes("text-4xl text-gray-400")
        ui.label(message.rstrip(".")).classes("text-gray-500 text-sm")
        if hint:
            ui.label(hint).classes("text-gray-500 text-xs")
    return box


# ── Khung chờ ─────────────────────────────────────────────────────────────────
def skeleton_rows(count: int = 5, height: str = "2.25rem"):
    """Khung xương cho bảng đang tải. Thay cho việc để màn hình trắng."""
    with ui.column().classes("w-full gap-2") as box:
        for _ in range(count):
            ui.skeleton().props(f'height={height} animation=wave').classes("w-full")
    return box


def skeleton_cards(count: int = 3, height: str = "6rem"):
    with ui.row().classes("w-full gap-4 flex-wrap") as box:
        for _ in range(count):
            ui.skeleton().props(f'height={height} animation=wave').classes("flex-1 min-w-[12rem]")
    return box


# ── Card ──────────────────────────────────────────────────────────────────────
def card(title: str = "", padding: str = "p-4"):
    """Card có padding ĐẶT TƯỜNG MINH.

    NiceGUI 2.0 bỏ CSS padding tự động của Quasar cho ui.card. Không dựa vào giá
    trị mặc định thì card giữ nguyên hình dạng ở cả 1.4.x lẫn 2.x — bớt một hạng
    mục phải soi mắt khi nâng cấp (spike B1).
    """
    outer = ui.card().classes(f"w-full shadow-sm rounded-xl bg-white p-0 overflow-hidden border border-gray-200")
    with outer:
        if title:
            with ui.row().classes("w-full bg-red-50 px-4 py-3 border-b border-red-100 items-center"):
                ui.label(title).classes("font-semibold text-red-800")
        body = ui.column().classes(f"w-full {padding} gap-3")
    return outer, body


# ── Stepper ngang ─────────────────────────────────────────────────────────────
def stepper(labels: list[str], current: int):
    """Thanh bước ngang cho tiến trình nhiều giai đoạn (VD chạy job nền).

    `current` = index (0-based) của bước đang chạy; các bước < current coi là đã
    xong (tick xanh); == current tô đỏ Agribank (đang chạy); > current xám nhạt.
    Gọi lại (rebuild) mỗi khi `current` đổi — không tự bind, do NiceGUI không có
    binding 2 chiều tiện cho layout dạng này.
    """
    with ui.row().classes("w-full items-start gap-0") as box:
        for i, label in enumerate(labels):
            done   = i < current
            active = i == current
            with ui.column().classes("items-center flex-1 gap-1"):
                with ui.row().classes("w-full items-center gap-0"):
                    if i > 0:
                        ui.element("div").classes(
                            "flex-1 h-0.5 " + ("bg-green-500" if i <= current else "bg-gray-200")
                        )
                    circle_cls = (
                        "bg-green-500 text-white" if done else
                        "bg-red-700 text-white" if active else
                        "bg-gray-200 text-gray-500"
                    )
                    with ui.element("div").classes(
                        f"w-7 h-7 rounded-full flex items-center justify-center "
                        f"text-xs font-bold shrink-0 {circle_cls}"
                    ):
                        if done:
                            ui.icon("check").classes("text-sm")
                        else:
                            ui.label(str(i + 1))
                    if i < len(labels) - 1:
                        ui.element("div").classes(
                            "flex-1 h-0.5 " + ("bg-green-500" if i < current else "bg-gray-200")
                        )
                ui.label(label).classes(
                    "text-xs text-center " + (
                        "text-green-700 font-medium" if done else
                        "text-red-800 font-semibold" if active else
                        "text-gray-400"
                    )
                )
    return box


# ── Nạp một lần cho mỗi trang ─────────────────────────────────────────────────
_FONT_HREF = ("https://fonts.googleapis.com/css2?"
              "family=Inter:wght@400;500;600;700&display=swap")

# Bấm vào cả dải màu (header) của ô chọn file là mở hộp thoại chọn file, không
# bắt người dùng nhắm đúng dấu "+". Quasar chỉ gắn <input type=file> vào riêng
# nút "+", nên phải bắt click ở cấp document rồi chuyển tiếp sang input đó.
# Dùng bắt sự kiện nổi bọt (không capture) + loại trừ nút thật để các nút khác
# trên header (tải lên, xoá hàng đợi) vẫn hoạt động như cũ.
# Gọi input.click() an toàn: handler của chính Quasar trên input chỉ gọi
# stopPropagation (không preventDefault) nên hộp thoại vẫn mở, và cú click tổng
# hợp cũng không nổi ngược lên listener này.
_UPLOADER_CLICK_JS = """<script>
if (!window.__uploaderHeaderClickInstalled) {
  window.__uploaderHeaderClickInstalled = true;
  document.addEventListener('click', function (ev) {
    const header = ev.target.closest && ev.target.closest('.q-uploader__header');
    if (!header) return;
    if (ev.target.closest('.q-btn, button, label, input, a')) return;
    const box = header.closest('.q-uploader') || header.parentElement;
    if (!box || box.classList.contains('disabled')) return;
    const input = box.querySelector('input[type="file"]');
    if (input && !input.disabled) input.click();
  });
}
</script>"""

_UPLOADER_CSS = """
.q-uploader__header { cursor: pointer; }
.q-uploader__header .q-btn, .q-uploader__header button, .q-uploader__header label { cursor: pointer; }
"""


def install():
    """Gọi một lần đầu mỗi trang — nạp token + font.

    Gọi trùng không hại (trình duyệt gộp <link> cùng URL), nhưng cố ý KHÔNG dùng
    cờ chống trùng qua `context.get_client()`: API đó bị gỡ ở NiceGUI 2.0.
    """
    ui.add_head_html(f'<link href="{_FONT_HREF}" rel="stylesheet">')
    ui.add_head_html(
        f"<style>{_css_vars()}\n"
        "body, .q-app { font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif; }"
        f"{_UPLOADER_CSS}"
        "</style>"
    )
    ui.add_head_html(_UPLOADER_CLICK_JS)
