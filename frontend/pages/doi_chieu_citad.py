"""Trang Đối chiếu CITAD (NHNN) ↔ PaymentHub (Agribank) — Phòng Thanh toán.

Port từ `citad-fixed/DoiChieuCITAD.py` (tkinter). Giữ nguyên mô hình dữ liệu
và công thức tính chênh lệch gốc:
  - gD[cong][cur][fk]  — 5 cổng CITAD × 3 loại tiền × 8 trường
  - phD[cur][fk]       — PaymentHub × 3 loại tiền × 8 trường
  - napas[fk] / ebank[fk] / pssmdp[fk] — bổ sung Napas/Ebanking/PSS-MDP
  - Tổng CITAD = tổng 5 cổng + Napas IH Đến + PSS-MDP IH Đến (den_ih_m, den_ih_t)
    (PSS-MDP thêm sau theo yêu cầu Phòng Thanh toán — cùng nguyên lý Napas)
  - Tổng PaymentHub = tổng 3 loại tiền của PaymentHub
  - Chênh lệch = Tổng CITAD − Tổng PaymentHub  (đúng theo `_calc()` gốc)

Nút "Nạp CITAD"/"Nạp PaymentHub" đọc buffer do Extension Chrome gửi lên
(xem `extension_citad/`) — thay vì poll timer như bản tkinter, người dùng
bấm nút để nạp giống hệt hành vi gốc. Buffer được tách theo `owner`
(username TTTT cấu hình trong Extension) nên nhiều người dùng chung backend
không ghi đè/xoá dữ liệu của nhau (khác bản gốc — bản gốc chạy 1 server
cục bộ/máy nên vốn chỉ có 1 người dùng).

Napas/Ebanking chỉ có 2 field "IH Đến — Món/Tiền" thực sự được dùng trong
`_calc()`/session/export ở bản gốc (đã kiểm tra `_calc()`, `_get_session_data`,
`_export_excel` trong `citad-fixed/DoiChieuCITAD.py` gốc) — UI chỉ hiện đúng
2 ô này, không vẽ 8 field × 2 dòng như bản gốc (grid gốc có 12/16 ô không hề
được đọc ở đâu, chỉ gây hiểu nhầm).
"""
import asyncio
import datetime
import json
import logging
from decimal import Decimal

from nicegui import ui
from starlette.requests import Request as _StarletteRequest
import frontend.api_client as api
from frontend.shared import _sidebar, _content_area, _require_auth, _handle_api_error

_log = logging.getLogger(__name__)

# Card kiểu "modern SaaS" RIÊNG cho trang này (icon trong khung màu + tiêu đề,
# không dùng banner phủ màu như `_card()` dùng chung ở frontend/shared.py —
# đó là component DÙNG CHUNG CHO CẢ APP, không đổi ở đây để tránh ảnh hưởng
# các trang khác; trang này tự định nghĩa card riêng thay vì import `_card`).
# Mỗi tuple: (nền icon, màu chữ/icon, viền dòng tiêu đề, nền mờ phủ CẢ card —
# đủ 8 màu để mỗi bảng nhỏ (PaymentHub + 5 Cổng CITAD) có 1 màu riêng, dễ
# phân biệt khi cuộn qua nhiều bảng liên tiếp giống hệt nhau về cấu trúc).
_ACCENT = {
    "blue": ("bg-blue-50", "text-blue-600", "border-blue-100", "bg-blue-50/40"),
    "indigo": ("bg-indigo-50", "text-indigo-600", "border-indigo-100", "bg-indigo-50/40"),
    "emerald": ("bg-emerald-50", "text-emerald-600", "border-emerald-100", "bg-emerald-50/40"),
    "amber": ("bg-amber-50", "text-amber-600", "border-amber-100", "bg-amber-50/40"),
    "rose": ("bg-rose-50", "text-rose-600", "border-rose-100", "bg-rose-50/40"),
    "cyan": ("bg-cyan-50", "text-cyan-600", "border-cyan-100", "bg-cyan-50/40"),
    "purple": ("bg-purple-50", "text-purple-600", "border-purple-100", "bg-purple-50/40"),
    "teal": ("bg-teal-50", "text-teal-600", "border-teal-100", "bg-teal-50/40"),
}


def _navy_header(title: str, subtitle: str = ""):
    """Thanh tiêu đề nền xanh navy đậm, chữ trắng — theo mẫu banner người
    dùng gửi (ảnh Kanban Board), thay cho `_page_header()` dùng chung ở
    frontend/shared.py (chỉ đổi RIÊNG ở trang này, không đụng shared.py)."""
    with ui.column().classes(
        "w-full bg-blue-950 rounded-2xl px-6 py-4 mb-4 gap-0.5"
    ):
        ui.label(title).classes("text-xl font-bold text-white tracking-wide")
        if subtitle:
            ui.label(subtitle).classes("text-blue-200 text-sm")


def _section_card(title: str, icon: str = "table_chart", accent: str = "blue", outer_border: str = "border border-gray-200"):
    """`outer_border`: class viền KHUNG NGOÀI cả card (khác `border` bên
    dưới — đó là viền dưới thanh tiêu đề). Mặc định giữ NGUYÊN Y HỆT như
    trước ("border border-gray-200") cho mọi card khác trên trang; các
    bảng đối chiếu (PaymentHub/Cổng/Napas/Bảng chênh lệch) truyền riêng
    "border-2 border-red-800" theo đúng yêu cầu chỉ tô KHUNG NGOÀI đỏ đô,
    không đụng viền lưới bên trong từng ô (xem _grid_cell_cls, vẫn giữ
    nguyên màu xám cũ)."""
    bg, text, border, wash = _ACCENT.get(accent, _ACCENT["blue"])
    card = ui.card().classes(
        f"w-full rounded-2xl {outer_border} shadow-sm hover:shadow-md "
        f"transition-shadow duration-200 {wash} p-0 overflow-hidden"
    )
    with card:
        with ui.row().classes(f"w-full items-center gap-3 px-5 py-4 border-b {border} bg-gray-50/60"):
            with ui.row().classes(f"items-center justify-center w-9 h-9 rounded-xl {bg} shrink-0"):
                ui.icon(icon).classes(f"{text} text-lg")
            ui.label(title).classes("font-semibold text-gray-800 text-[15px]")
    return card

# ID cố định của extension_citad — suy ra tất định từ khoá "key" gắn cứng
# trong extension_citad/manifest.json (không phụ thuộc máy/thư mục cài đặt
# lúc "Load unpacked"). Dùng để gọi chrome.runtime.sendMessage từ trang này
# sang extension qua "externally_connectable" (xem extension_citad/background.js).
# Nếu thay khoá "key" trong manifest.json thì PHẢI cập nhật lại hằng số này.
_EXTENSION_ID = "dhollmjgbbjdcedijlmklmknndcachjh"


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


def _date_filter_input(label: str):
    """Ô lọc theo ngày — RỖNG mặc định (nghĩa là "không giới hạn"), khác
    `_date_picker_input` (luôn mặc định hôm nay). KHÔNG dùng cách tạo
    `_date_picker_input()` rồi gán `.value = ""` ngay sau đó — `ui.date`
    bên trong vẫn giữ giá trị khởi tạo "hôm nay" và đồng bộ ngược lại
    `date_input.value` qua `bind_value` theo chu kỳ, làm ô lọc âm thầm quay
    lại "hôm nay" sau vài trăm ms dù đã gán rỗng. Ở đây tạo `ui.date` không
    truyền `value=` ngay từ đầu nên cả 2 phía cùng rỗng, không có gì để
    đồng bộ ngược lại."""
    with ui.input(label, value="").props("dense outlined clearable").classes("w-44") as date_input:
        with date_input.add_slot("append"):
            ui.icon("edit_calendar").on("click", lambda: menu.open()).classes("cursor-pointer")
        with ui.menu() as menu:
            ui.date(mask="DD/MM/YYYY", on_change=menu.close).bind_value(date_input)
    return date_input

CONGS = [1, 9, 18, 17, 12]
# Mỗi cổng 1 màu riêng (xem `_ACCENT`) — chỉ để phân biệt trực quan giữa
# các bảng nhập liệu giống hệt nhau về cấu trúc, không mang ý nghĩa nghiệp vụ.
CONG_ACCENT = {1: "indigo", 9: "purple", 18: "rose", 17: "cyan", 12: "teal"}
CURS = ['VNĐ', 'USD', 'EUR']
FK = ['di_ih_m', 'di_ih_t', 'di_il_m', 'di_il_t', 'den_ih_m', 'den_ih_t', 'den_il_m', 'den_il_t']
FK_LBL = ['ĐI IH Món', 'ĐI IH Tiền', 'ĐI IL Món', 'ĐI IL Tiền',
          'ĐẾN IH Món', 'ĐẾN IH Tiền', 'ĐẾN IL Món', 'ĐẾN IL Tiền']
# ui.grid(columns=9) mặc định chia đều 9 cột (1fr mỗi cột) — cột "Tiền" VNĐ
# dài tới 21 ký tự (vd "43,462,772,025,396.47") bị cắt cụt vì chia bằng cột
# "Món" chỉ 5-6 ký tự (vd "22,888"). Dùng template tuỳ ý (ui.grid nhận string
# CSS grid-template-columns) thay vì số cột thường — cột Tiền rộng gấp ~2,4
# lần cột Món. Dùng chung ở CẢ 3 lưới (Bảng chênh lệch, build_grid,
# build_napas_pssmdp_grid) để cột vẫn thẳng hàng giữa các bảng như thiết kế.
_MONEY_GRID_TEMPLATE = '1fr 0.7fr 1.7fr 0.7fr 1.7fr 0.7fr 1.7fr 0.7fr 1.7fr'


def nv(v):
    try:
        return float(str(v).replace(',', '').replace(' ', '')) if v not in (None, '') else 0.0
    except Exception:
        return 0.0


def fmt(v):
    v = nv(v)
    if v == 0:
        return ''
    # QUAN TRỌNG: KHÔNG được cắt bằng int(v) — VNĐ luôn là số nguyên nên vô
    # hại, nhưng USD/EUR có phần xu (vd 2954592.79) sẽ bị cắt mất. Chữ hiển
    # thị ở đây sau đó bị đọc ngược lại thành dữ liệu gốc (nv(e.value) trong
    # on_change khi ô được set lại giá trị, kể cả set bằng code) — cắt ở đây
    # là mất vĩnh viễn phần xu, gây lệch số liệu thật khi cộng dồn nhiều
    # lệnh (đã xác nhận thực tế: lệch đúng 1 xu ở "Đối chiếu CITAD" ngày
    # 06/08/2026 vì 3 khoản USD đều bị cắt xu trước khi cộng).
    if v == int(v):
        return f'{int(v):,}'
    return f'{v:,.2f}'


def _dec(v) -> Decimal:
    """Chuyển sang Decimal CHÍNH XÁC TUYỆT ĐỐI, không qua số thực nhị phân.

    `Decimal(v)` trên 1 float sẽ mở ra đúng dạng nhị phân của nó (vd
    `Decimal(516.6)` ra `Decimal('516.59999999999999...')`) — phải đi qua
    `str(v)` trước: `str()` của float là chuỗi thập phân NGẮN NHẤT vẫn ra
    đúng float đó (thuật toán repr của Python), nên `Decimal(str(516.6))`
    ra đúng `Decimal('516.6')`. Dùng cho MỌI phép cộng dồn tiền (`_compute_totals_group()`,
    `cur_mismatch()`) — cộng nhiều số thực rồi so sánh trực tiếp có thể sinh
    dư nhị phân (bug thật 25/08/2026: 0,0078125 dù CITAD gốc cộng đúng khớp
    PaymentHub, khiến màn hình báo "+0,01" giả); cộng bằng Decimal thì không
    có dư nào — kết quả đúng tuyệt đối với số liệu gốc, khớp thật ra đúng 0,
    lệch thật dù nhỏ đến đâu vẫn hiện đúng, không đánh đổi độ chính xác lấy
    gọn màn hình."""
    try:
        return Decimal(str(v)) if v not in (None, '') else Decimal(0)
    except Exception:
        return Decimal(0)


def diff_exact(ci_val: Decimal, ph_val: Decimal) -> Decimal:
    """Chênh lệch CITAD-PaymentHub cho 1 cột — `ci_val`/`ph_val` phải là
    Decimal đã cộng dồn qua `_dec()` (xem `_compute_totals_group()`), nên phép
    trừ này chính xác tuyệt đối, không cần và không được làm tròn gì thêm."""
    return ci_val - ph_val


def cur_mismatch(ci_cur: dict, ph_cur: dict) -> bool:
    """Có lệch thật giữa CITAD/PaymentHub cho 1 loại tiền không — `ci_cur`/
    `ph_cur` phải là dict giá trị Decimal (cộng dồn qua `_dec()`), nên so
    `!=` ở đây chính xác tuyệt đối, không lẫn dư nhị phân nào."""
    return any(ci_cur[f] != ph_cur[f] for f in FK)


_CELL_DATA_BG = "bg-red-200"


def _apply_cell_bg(inp):
    """Tô nền hồng đỏ cho ô đã có dữ liệu — giúp nhìn lướt biết ngay ô nào
    đã nhập, ô nào còn trống, đặc biệt hữu ích khi bảng có nhiều cột. Trước
    dùng bg-red-50 (quá nhạt, dễ nhìn nhầm thành chưa tô) — đậm hơn hẳn để
    không còn nhầm được nữa."""
    if inp.value:
        inp.classes(add=_CELL_DATA_BG)
    else:
        inp.classes(remove=_CELL_DATA_BG)


def _set_input(inp, value):
    """Gán `.value` + đồng bộ luôn màu nền — dùng ở MỌI nơi gán giá trị ô
    bằng code (nạp session/buffer, xoá) thay vì gán `.value` trực tiếp, để
    không sót chỗ nào quên tô/xoá màu nền."""
    inp.value = value
    _apply_cell_bg(inp)


@ui.page("/doi_chieu_citad")
async def doi_chieu_citad_page(request: _StarletteRequest):
    if not _require_auth():
        return
    if not api.has_feature("menu.doi_chieu_citad"):
        ui.navigate.to("/home")
        return

    # Deep-link từ Sổ trực cuối ngày (/so_truc) — mở thẳng đúng ngày trong
    # tab "Lịch sử" thay vì phải tự gõ lại bộ lọc.
    deep_link_ngay = request.query_params.get("ngay")

    # Tham chiếu hàm nạp lại tab "Lịch sử" — gán bên trong _build_history_panel()
    # (khai báo hàm đó xong mới có), gọi lại ở _save_session_now() sau khi lưu
    # thành công để danh sách Lịch sử tự cập nhật ngay, không cần F5 cả trang.
    # Dùng dict (không phải biến thường) vì cả 2 hàm đều là closure lồng
    # trong doi_chieu_citad_page() — gán qua dict tránh phải khai `nonlocal`.
    history_refresh = {"fn": None}

    # "mode": 'edit' (sửa đủ mọi field — form mới hoặc đang xem bản tạm CỦA
    # CHÍNH MÌNH) | 'napas_only' (đang xem bản tạm của NGƯỜI KHÁC — chỉ 4 ô
    # Napas/PSS-MDP sửa được, phần còn lại khoá) | 'locked' (bản CUỐI đã
    # chốt — khoá hết, không ai sửa/lưu được nữa qua đây, kể cả người lập
    # bảng). Dict để mọi closure trong trang đọc/ghi được mà không cần
    # `nonlocal`. Xem _apply_view_mode().
    # "session_id": None nghĩa là form TRẮNG chưa "Tải" bảng nào — lưu sẽ LUÔN
    # tạo bảng MỚI (07/09/2026: 1 người có thể có nhiều bảng độc lập/ngày, xem
    # docstring đầu doi_chieu_citad_service.py). Có giá trị = đang sửa/lưu
    # tiếp ĐÚNG bảng đó (của chính mình hoặc napas_only vào bảng người khác).
    view_state = {
        "mode": "edit", "ngay_dang_xem": "", "session_id": None,
        "created_by": None, "created_by_name": "",
    }
    current_user = api.get_current_user() or {}

    # Dữ liệu số (float) — nguồn sự thật để tính chênh lệch, tách khỏi text hiển thị trên ô nhập
    data = {
        "gD": {c: {u: {f: 0.0 for f in FK} for u in CURS} for c in CONGS},
        "phD": {u: {f: 0.0 for f in FK} for u in CURS},
        "napas": {"den_ih_m": 0.0, "den_ih_t": 0.0},
        "ebank": {"den_ih_m": 0.0, "den_ih_t": 0.0},
        "pssmdp": {"den_ih_m": 0.0, "den_ih_t": 0.0},
    }
    inputs = {
        "gE": {c: {u: {} for u in CURS} for c in CONGS},
        "phE": {u: {} for u in CURS},
        "napasE": {},
        "pssmdpE": {},
    }
    # 3 bảng chênh lệch (04/09/2026): Gộp (cả 3 loại tiền, như trước giờ) +
    # 2 bảng tách riêng VNĐ (kèm Napas/PSS-MDP, kênh trong nước) / Ngoại tệ
    # (USD+EUR gộp chung 1 bảng, không tách tiếp theo từng loại ngoại tệ) —
    # xem đủ cả tổng lẫn chi tiết từng nhóm tiền cùng lúc.
    diff_labels = {"citad": {}, "phub": {}, "diff": {}}
    diff_labels_vnd = {"citad": {}, "phub": {}, "diff": {}}
    diff_labels_fx = {"citad": {}, "phub": {}, "diff": {}}
    lech_cur_label = None  # ui.label ghi chú "Lệch: <loại tiền>" cuối trang — gán khi dựng UI

    ngay_input = None
    lap_bang_input = None
    kiem_soat_input = None

    def _grid_cell_cls(row_idx: int, col_idx: int, n_rows: int, n_cols: int, extra: str = "") -> str:
        """Kẻ khung + chia dòng/cột cho `ui.grid`: border-r cho mọi cột trừ
        cột cuối, border-b cho mọi dòng trừ dòng cuối (đặt trên MỌI ô, kể cả
        ô chứa `ui.input`, để đồng bộ giao diện giữa các bảng nhập liệu và
        bảng chênh lệch — theo đúng yêu cầu). Dòng tiêu đề (row_idx=0) tô
        nền xanh dương — bỏ hẳn class màu chữ xám truyền vào qua `extra`
        (nếu có) rồi ép chữ trắng, thay vì nối thêm "text-white" phía sau
        (Tailwind không đảm bảo class nối sau luôn thắng class nối trước
        khi cùng set 1 thuộc tính — dễ ra chữ xám mờ trên nền xanh, khó đọc)."""
        if row_idx == 0:
            tokens = [t for t in extra.split() if not t.startswith("text-gray")]
            cls = " ".join(tokens) + " bg-blue-600 text-white py-2"
        else:
            cls = extra + " py-1.5"
        # Ranh giới giữa nhóm "Lệnh đi" (4 cột FK đầu) và "Lệnh đến" (4 cột
        # sau) — viền đậm + khoảng cách hở (mr/ml) để 2 khung tách bạch rõ
        # thành 2 khối riêng nhìn là biết ngay, không chỉ đọc dò tiêu đề từng
        # cột. col_idx=4 là cột cuối "Lệnh đi", col_idx=5 là cột đầu "Lệnh
        # đến" (0=cột "Loại tiền", 1-4=Lệnh đi, 5-8=Lệnh đến). Chặn border-r
        # thường bằng elif — 2 class border-r khác độ dày/màu cộng chung dễ
        # bị Tailwind chọn sai class thắng (đã có tiền lệ lỗi này trong file).
        if col_idx == 4:
            cls += " border-r-2 border-gray-400 pr-2 mr-2"
        elif col_idx < n_cols - 1:
            cls += " border-r border-gray-300 pr-2"
        if col_idx == 5:
            cls += " ml-2"
        if row_idx < n_rows - 1:
            cls += " border-b border-gray-300 pb-1"
        # Bo tròn 2 góc dưới của khung to (cả bảng) — đúng 2 ô cuối cùng của
        # dòng dữ liệu cuối. 2 góc trên do _group_header_row() tự lo (đứng
        # trên hàng row_idx=0 này nên _grid_cell_cls không với tới được).
        if row_idx == n_rows - 1:
            if col_idx == 0:
                cls += " rounded-bl-lg"
            elif col_idx == n_cols - 1:
                cls += " rounded-br-lg"
        return cls

    def _group_header_row():
        """Hàng gộp 2 nhóm cột 'LỆNH ĐI' / 'LỆNH ĐẾN', đặt TRÊN hàng tiêu đề
        chi tiết (Loại tiền + 8 nhãn cột) — mỗi nhãn nhóm chiếm đúng 4 cột
        FK (col-span-4) khớp ranh giới viền đậm + khoảng hở ở _grid_cell_cls().
        Không dùng chung _grid_cell_cls() vì hàng này chỉ có 3 ô logic (trống
        + 2 nhãn nhóm) trải trên 9 cột lưới — cách tính viền/nền viết tay
        riêng cho đơn giản, không gượng ép vào công thức row_idx/col_idx.
        Mỗi nhãn nhóm tự bo tròn 2 góc trên của CHÍNH NÓ (rounded-t-lg) —
        vừa là góc trên của "khung nhỏ" (LỆNH ĐI/LỆNH ĐẾN đứng tách biệt nhờ
        khoảng hở mr/ml) vừa đúng luôn là góc trên của "khung to" (cả bảng)
        vì đây là hàng trên cùng. Không bo góc dưới của 2 ô này — đáy dính
        liền hàng tiêu đề chi tiết bên dưới, bo sẽ hở ra tam giác nền trắng."""
        ui.label("").classes("bg-blue-800 border-b border-blue-900 rounded-tl-lg")
        ui.label("LỆNH ĐI").classes(
            "col-span-4 text-center text-xs font-bold text-white bg-blue-800 "
            "border-b border-r-2 border-blue-900 py-1 mr-2 rounded-t-lg"
        )
        ui.label("LỆNH ĐẾN").classes(
            "col-span-4 text-center text-xs font-bold text-white bg-blue-800 "
            "border-b border-blue-900 py-1 ml-2 rounded-t-lg"
        )

    def _compute_totals_group(curs: list) -> tuple:
        """Tổng CITAD (5 cổng + Napas/PSS-MDP IH Đến — CHỈ khi VNĐ nằm trong
        `curs`, kênh trong nước — KHÔNG cộng Ebanking) và tổng PaymentHub,
        CHỈ cộng các loại tiền trong `curs` — đúng công thức `_calc()` gốc,
        xem ghi chú chi tiết trong `doi_chieu_citad_service.py::build_xlsx`.
        Dùng cho CẢ 3 bảng chênh lệch trên màn hình (Gộp gọi với `curs=CURS`,
        VNĐ/Ngoại tệ gọi với tập con — xem recalc()/_fill_diff_table()) lẫn
        preview trước khi xuất Excel (`do_export()`, cũng gọi với `curs=CURS`)
        — luôn khớp nhau, tính 1 nơi duy nhất (trước đây có 2 hàm riêng cùng
        công thức — review Người 1 PR#76: 2 bản song song dễ lệch nhau khi
        sau này chỉ sửa 1 bản, gộp lại còn 1 nguồn duy nhất)."""
        # Cộng dồn bằng Decimal (qua _dec()) — KHÔNG cộng bằng float trực
        # tiếp. Cộng nhiều số thực (5 Cổng × 3 loại tiền + Napas + PSS-MDP)
        # có thể sinh dư nhị phân dù về bản chất đã khớp tuyệt đối (bug thật
        # 25/08/2026: 0,0078125 dù CITAD gốc cộng đúng khớp PaymentHub) —
        # Decimal cộng đúng tuyệt đối với số liệu gốc, không có dư nào phải
        # làm tròn/che đi, nên lệch thật dù chỉ 1 xu vẫn hiện đúng.
        ci = {f: Decimal(0) for f in FK}
        for c in CONGS:
            for u in curs:
                for f in FK:
                    ci[f] += _dec(data["gD"][c][u][f])
        if 'VNĐ' in curs:
            ci["den_ih_m"] += _dec(data["napas"]["den_ih_m"]) + _dec(data["pssmdp"]["den_ih_m"])
            ci["den_ih_t"] += _dec(data["napas"]["den_ih_t"]) + _dec(data["pssmdp"]["den_ih_t"])
        ph = {f: Decimal(0) for f in FK}
        for u in curs:
            for f in FK:
                ph[f] += _dec(data["phD"][u][f])
        return ci, ph

    def _fill_diff_table(labels: dict, curs: list):
        """Đổ số liệu vào 1 trong 2 bảng chênh lệch tách VNĐ/Ngoại tệ —
        cùng công thức hiển thị (—/✓ 0/±số) như bảng gộp cũ, chỉ khác nguồn
        (_compute_totals_group thay vì _compute_totals)."""
        ci, ph = _compute_totals_group(curs)
        for f in FK:
            ci_val, ph_val = ci[f], ph[f]
            df_val = diff_exact(ci_val, ph_val)
            labels["citad"][f].text = fmt(ci_val) if ci_val else '—'
            labels["phub"][f].text = fmt(ph_val) if ph_val else '—'
            if df_val == 0 and ci_val == 0 and ph_val == 0:
                labels["diff"][f].text = '—'
                labels["diff"][f].classes(remove='text-red-600 text-green-700')
            elif df_val == 0:
                labels["diff"][f].text = '✓ 0'
                labels["diff"][f].classes(remove='text-red-600', add='text-green-700')
            else:
                # Dùng fmt() (không phải int() cắt xu trực tiếp) — âm đã tự
                # có dấu "-" từ fmt(), chỉ cần tự thêm "+" cho dương. Trước
                # đây dòng này tự cắt riêng bằng int(df_val), lệch USD/EUR
                # kiểu 0.79 xu hiện thành "+0" dù vẫn bôi đỏ đúng — sai lệch
                # y hệt lỗi đã sửa ở fmt()/ô nhập, chỉ khác là sót ở đây.
                sign = '+' if df_val > 0 else ''
                labels["diff"][f].text = f'{sign}{fmt(df_val)}'
                labels["diff"][f].classes(remove='text-green-700', add='text-red-600')

    def recalc():
        # 3 bảng chênh lệch (04/09/2026): Gộp cả 3 loại tiền (như cũ, gọi
        # _compute_totals_group(CURS) — cùng 1 hàm duy nhất với 2 bảng tách,
        # không phải công thức riêng) + tách riêng VNĐ / Ngoại tệ (USD+EUR
        # gộp chung).
        _fill_diff_table(diff_labels, CURS)
        _fill_diff_table(diff_labels_vnd, ['VNĐ'])
        _fill_diff_table(diff_labels_fx, ['USD', 'EUR'])

        # Dòng ghi chú "Lệch: <loại tiền>" cuối trang — tính lại RIÊNG theo
        # TỪNG loại tiền (khác 2 bảng trên gộp USD+EUR chung) chỉ để phát
        # hiện có lệch hay không (không hiển thị số tiền lệch, chỉ nêu tên
        # loại tiền). Napas/PSS-MDP là kênh trong nước, chỉ cộng vào VNĐ.
        if lech_cur_label is not None:
            lech_curs = []
            for cur in CURS:
                ci_cur = {f: sum((_dec(data["gD"][c][cur][f]) for c in CONGS), Decimal(0)) for f in FK}
                if cur == 'VNĐ':
                    ci_cur["den_ih_m"] += _dec(data["napas"]["den_ih_m"]) + _dec(data["pssmdp"]["den_ih_m"])
                    ci_cur["den_ih_t"] += _dec(data["napas"]["den_ih_t"]) + _dec(data["pssmdp"]["den_ih_t"])
                ph_cur = {f: _dec(data["phD"][cur][f]) for f in FK}
                if cur_mismatch(ci_cur, ph_cur):
                    lech_curs.append(cur)
            if lech_curs:
                lech_cur_label.text = f"⚠ Lệch: {', '.join(lech_curs)}"
                lech_cur_label.classes(remove='text-emerald-700', add='text-red-600')
            else:
                lech_cur_label.text = "✓ Không lệch loại tiền nào"
                lech_cur_label.classes(remove='text-red-600', add='text-emerald-700')

    def build_grid(container, entry_store: dict, data_store: dict, row_keys: list):
        with container:
            n_cols = len(FK) + 1
            n_rows = len(row_keys) + 1
            with ui.grid(columns=_MONEY_GRID_TEMPLATE).classes("w-full gap-0 p-4"):
                _group_header_row()
                ui.label("Loại tiền").classes(
                    _grid_cell_cls(0, 0, n_rows, n_cols, "text-sm font-bold text-gray-500 text-center")
                )
                for col_idx, lbl in enumerate(FK_LBL, start=1):
                    ui.label(lbl).classes(
                        _grid_cell_cls(0, col_idx, n_rows, n_cols, "text-sm font-bold text-gray-500 text-center")
                    )
                for row_idx, cur in enumerate(row_keys, start=1):
                    # flex items-center justify-center (KHÔNG self-center text-center):
                    # ô nhãn cột "Loại tiền" cao tự nhiên THẤP hơn ô ui.input cùng hàng
                    # (Quasar q-field cao hơn 1 dòng chữ thường). self-center chỉ canh
                    # GIỮA cả ô (không cao hết hàng lưới) → viền dưới của ô nhãn nổi lơ
                    # lửng giữa hàng thay vì chạm đáy như viền ô input — nhìn lệch hàng
                    # rõ rệt khi đổi viền sang đỏ đậm. flex items-center giữ ô cao hết
                    # hàng (mặc định stretch của CSS grid) rồi mới canh chữ vào giữa
                    # BÊN TRONG ô đó — viền dưới lúc này chạm đáy đúng như ô input.
                    ui.label(cur).classes(
                        _grid_cell_cls(row_idx, 0, n_rows, n_cols, "text-sm font-bold flex items-center justify-center")
                    )
                    entry_store[cur] = {}
                    for col_idx, fk in enumerate(FK, start=1):
                        def _on_change(e, _c=cur, _f=fk, _dd=data_store):
                            _dd[_c][_f] = nv(e.value)
                            _apply_cell_bg(e.sender)
                            recalc()
                        # readonly cố định — bảng CITAD/PaymentHub CHỈ nạp qua
                        # Extension ("Nạp CITAD"/"Nạp PaymentHub"), không cho gõ
                        # tay để tránh sửa số liệu thủ công trên bản đang chấm.
                        # _set_input() (dùng trong load_citad_buffer/
                        # load_phub_buffer) gán .value bằng code, không bị
                        # readonly chặn — chỉ chặn gõ thật từ bàn phím.
                        inp = ui.input(value='', on_change=_on_change).props(
                            'dense outlined readonly input-class="text-right"'
                        ).classes(_grid_cell_cls(row_idx, col_idx, n_rows, n_cols, "w-full"))
                        inp.on('blur', lambda _, _i=inp: _set_input(_i, fmt(_i.value)))
                        entry_store[cur][fk] = inp

    def build_napas_pssmdp_grid(container):
        """Chỉ 2 field IH Đến (Món/Tiền) — DUY NHẤT được dùng trong recalc()/
        session/export (xem docstring đầu file). 6 field còn lại của mỗi
        dòng KHÔNG có ô nhập (tránh ô "chết" không có tác dụng gì), nhưng
        vẫn vẽ ĐỦ 8 cột giống hệt FK_LBL của các bảng CITAD/PaymentHub phía
        trên — để cột "ĐẾN IH Món/Tiền" ở đây thẳng hàng đúng vị trí với
        cột cùng tên ở các bảng khác, đọc xuống dễ đối chiếu hơn."""
        with container:
            n_cols = len(FK) + 1
            n_rows = 3
            with ui.grid(columns=_MONEY_GRID_TEMPLATE).classes("w-full gap-0 p-4"):
                _group_header_row()
                ui.label("Loại tiền").classes(
                    _grid_cell_cls(0, 0, n_rows, n_cols, "text-sm font-bold text-gray-500 text-center")
                )
                for col_idx, lbl in enumerate(FK_LBL, start=1):
                    ui.label(lbl).classes(
                        _grid_cell_cls(0, col_idx, n_rows, n_cols, "text-sm font-bold text-gray-500 text-center")
                    )
                # Ebanking KHÔNG còn ô nhập trên màn hình, và dòng "Ebanking"
                # cũng đã bỏ khỏi Excel xuất ra (20/08/2026 — kênh này không
                # còn dùng). data["ebank"] vẫn giữ trong code (không xoá hẳn)
                # chỉ để đọc lại không lỗi session CŨ đã lưu trước đây (xem
                # apply_session_data), không còn hiển thị hay xuất ra đâu nữa.
                for row_idx, (label, store, entry_store) in enumerate([
                    ("Napas", data["napas"], inputs["napasE"]),
                    ("PSS - MDP", data["pssmdp"], inputs["pssmdpE"]),
                ], start=1):
                    # Xem comment ở build_grid() — flex items-center justify-center
                    # thay self-center text-center để viền dưới chạm đáy hàng đúng
                    # như ô input bên cạnh, không nổi lơ lửng giữa hàng.
                    ui.label(label).classes(
                        _grid_cell_cls(row_idx, 0, n_rows, n_cols, "text-sm font-bold flex items-center justify-center")
                    )
                    for col_idx, fk in enumerate(FK, start=1):
                        cell_cls = _grid_cell_cls(row_idx, col_idx, n_rows, n_cols, "w-full")
                        if fk not in ("den_ih_m", "den_ih_t"):
                            # Cột không dùng — giữ ô trống để chiếm đúng bề rộng cột,
                            # không phải ô nhập (không có ý nghĩa nghiệp vụ ở đây).
                            # Tô nền xám nhạt để rõ ràng đây là ô "không dùng" có chủ
                            # đích, không phải lỗi giao diện làm mất ô.
                            ui.label("").classes(cell_cls + " bg-gray-50")
                            continue

                        def _on_change(e, _f=fk, _dd=store):
                            _dd[_f] = nv(e.value)
                            _apply_cell_bg(e.sender)
                            recalc()
                        # readonly cố định (04/09/2026) — như 5 Cổng CITAD/PaymentHub
                        # ở build_grid(): Napas/PSS-MDP CHỈ nạp qua Extension ("Nạp
                        # CITAD"/"Nạp PaymentHub"), không cho gõ tay nữa (trước đây
                        # gõ tay được ở mode 'edit'/'napas_only', chỉ khoá khi
                        # 'locked' — xem _apply_view_mode()). _set_input() gán .value
                        # bằng code, không bị readonly chặn — chỉ chặn gõ thật.
                        inp = ui.input(value='', on_change=_on_change).props(
                            'dense outlined readonly input-class="text-right"'
                        ).classes(cell_cls)
                        inp.on('blur', lambda _, _i=inp: _set_input(_i, fmt(_i.value)))
                        entry_store[fk] = inp

    def apply_session_data(sess: dict):
        if not sess:
            return
        if sess.get("ngay"):
            ngay_input.value = sess["ngay"]
        # ui.select(new_value_mode="add-unique") chỉ tự thêm giá trị lạ vào
        # options khi NGƯỜI DÙNG gõ — gán .value bằng code không kích hoạt
        # cơ chế đó (NiceGUI docstring: "ineffective when setting the value
        # property programmatically"). Tên không có sẵn trong options (đã
        # nghỉ/chuyển phòng, hoặc options chưa kịp tải) sẽ bị ChoiceElement
        # tự đổi thành None — mất tên khi mở lại bảng cũ, và nếu bấm Lưu sẽ
        # ghi đè None đè lên tên đã lưu trong DB (bug thật, ghi ở PR#53).
        # Tự bơm giá trị vào options trước khi gán để giữ nguyên tên cũ.
        #
        # PHẢI gọi .update() ngay sau khi đổi .options — đọc thẳng
        # docstring ui.select(): "After manipulating the options, call
        # update()". .options chỉ là thuộc tính thường, không tự kích hoạt
        # gì cả; ChoiceElement._values/._labels (dùng để đối chiếu khi đổi
        # .value) chỉ được tính lại bên trong update()/_update_options().
        # Thiếu bước này thì self._values vẫn CŨ, có thể khiến lần gán
        # .value tiếp theo tính sai index — hoặc lần .update() nào khác gọi
        # sau đó (không phải do mình) đọc lại self._values cũ, đúng bug
        # cần sửa lại xảy ra lần nữa.
        lap_bang = sess.get("lap_bang", "")
        if lap_bang and lap_bang not in (lap_bang_input.options or []):
            lap_bang_input.options = [*(lap_bang_input.options or []), lap_bang]
            lap_bang_input.update()
        lap_bang_input.value = lap_bang
        kiem_soat = sess.get("kiem_soat", "")
        if kiem_soat and kiem_soat not in (kiem_soat_input.options or []):
            kiem_soat_input.options = [*(kiem_soat_input.options or []), kiem_soat]
            kiem_soat_input.update()
        kiem_soat_input.value = kiem_soat
        gD = sess.get("gD", {})
        for c in CONGS:
            for u in CURS:
                for f in FK:
                    v = (gD.get(str(c), {}) or {}).get(u, {}).get(f, 0)
                    data["gD"][c][u][f] = nv(v)
                    _set_input(inputs["gE"][c][u][f], fmt(v))
        phD = sess.get("phD", {})
        for u in CURS:
            for f in FK:
                v = (phD.get(u, {}) or {}).get(f, 0)
                data["phD"][u][f] = nv(v)
                _set_input(inputs["phE"][u][f], fmt(v))
        # Napas/Ebanking chỉ có 2 field IH Đến trong session gốc (napas_m/napas_t)
        data["napas"]["den_ih_m"] = nv(sess.get("napas_m", 0))
        data["napas"]["den_ih_t"] = nv(sess.get("napas_t", 0))
        _set_input(inputs["napasE"]["den_ih_m"], fmt(data["napas"]["den_ih_m"]))
        _set_input(inputs["napasE"]["den_ih_t"], fmt(data["napas"]["den_ih_t"]))
        # Không còn ô nhập Ebanking trên UI, và dòng Ebanking cũng đã bỏ khỏi
        # Excel xuất ra — vẫn đọc lại giá trị CŨ đã lưu (nếu có) vào
        # data["ebank"] chỉ để không lỗi khi mở lại session cũ, không dùng gì
        # thêm.
        data["ebank"]["den_ih_m"] = nv(sess.get("ebank_m", 0))
        data["ebank"]["den_ih_t"] = nv(sess.get("ebank_t", 0))
        data["pssmdp"]["den_ih_m"] = nv(sess.get("pssmdp_m", 0))
        data["pssmdp"]["den_ih_t"] = nv(sess.get("pssmdp_t", 0))
        _set_input(inputs["pssmdpE"]["den_ih_m"], fmt(data["pssmdp"]["den_ih_m"]))
        _set_input(inputs["pssmdpE"]["den_ih_t"], fmt(data["pssmdp"]["den_ih_t"]))
        recalc()

    def _apply_view_mode(
        mode: str,
        session_id: int | None = None,
        created_by: int | None = None,
        created_by_name: str = "",
    ):
        """Khoá/mở form theo 3 chế độ — xem giải thích ở khai báo `view_state`
        đầu hàm doi_chieu_citad_page(). Khoá bằng prop `readonly` của Quasar
        trên TỪNG ô — chặn gõ thật ở phía trình duyệt, không chỉ ẩn nút (phòng
        còn sót đường sửa nào khác). KHÔNG đụng `inputs["gE"]`/`inputs["phE"]`
        (5 Cổng CITAD + PaymentHub) lẫn `inputs["napasE"]`/`inputs["pssmdpE"]`
        (Napas/PSS-MDP, cố định từ 04/09/2026) — cả 2 nhóm này readonly CỐ
        ĐỊNH ngay từ lúc dựng grid (chỉ nạp qua Extension, không phân biệt
        mode). Tham chiếu `btn_nap_citad`/`btn_nap_ph`/`btn_luu_tam`/
        `btn_luu_cuoi`/`btn_xoa`/`banner_area` — các biến này gán SAU trong
        cùng hàm doi_chieu_citad_page(), nhưng closure chỉ đọc lúc GỌI hàm
        này (sau khi trang đã dựng xong)."""
        view_state["mode"] = mode
        view_state["session_id"] = session_id
        view_state["created_by"] = created_by
        view_state["created_by_name"] = created_by_name

        other_inputs = [ngay_input, lap_bang_input, kiem_soat_input]
        other_lock = mode != "edit"
        for inp in other_inputs:
            inp.props("readonly") if other_lock else inp.props(remove="readonly")

        # "Nạp CITAD"/"Nạp PaymentHub" vẫn hiện ở napas_only cả hai — "Nạp
        # CITAD" là đường DUY NHẤT nạp được Napas/PSS-MDP thật (xem
        # load_citad_buffer()). "Nạp PaymentHub" từ 04/09/2026 không còn nạp
        # được gì ở napas_only nữa (Napas/PSS-MDP chỉ nhận từ CITAD, 5 Cổng/
        # PaymentHub thường thì đã khoá) — CỐ Ý không ẩn nút: bấm vào vẫn
        # phải thấy đúng thông báo "bắt buộc quét từ cổng Citad" (xem
        # load_phub_buffer()), ẩn hẳn nút thì người quét nhầm PaymentHub
        # không biết vì sao không nạp được, tưởng phần mềm lỗi.
        btn_nap_citad.set_visibility(mode in ("edit", "napas_only"))
        btn_nap_ph.set_visibility(mode in ("edit", "napas_only"))
        btn_xoa.set_visibility(mode == "edit")
        btn_luu_tam.set_visibility(mode in ("edit", "napas_only"))
        btn_luu_cuoi.set_visibility(mode == "edit")

        banner_area.clear()
        is_admin = current_user.get("role") == "admin"
        with banner_area:
            if mode == "napas_only":
                with ui.row().classes(
                    "w-full items-center gap-2 px-4 py-2.5 rounded-xl border border-blue-300 bg-blue-50 mb-2"
                ):
                    ui.icon("edit_note", color="blue-700").classes("text-lg")
                    ui.label(
                        f"Bảng TẠM của {created_by_name or 'người khác'} — bạn chỉ bổ sung được "
                        "Napas/PSS-MDP, các bảng khác đã khoá (chỉ người lập bảng sửa được)."
                    ).classes("text-sm text-blue-800 flex-1")
                    ui.button("Bỏ xem, làm bảng mới", icon="edit", on_click=_exit_readonly_view).props(
                        "dense flat color=blue-8"
                    )
            elif mode == "locked":
                with ui.row().classes(
                    "w-full items-center gap-2 px-4 py-2.5 rounded-xl border border-amber-300 bg-amber-50 mb-2"
                ):
                    ui.icon("lock", color="amber-700").classes("text-lg")
                    ui.label(
                        "Ngày này đã \"Lưu bảng cuối\" — CHỐT, không ai sửa được nữa."
                        + (f" Người lập bảng: {created_by_name}." if created_by_name else "")
                    ).classes("text-sm text-amber-800 flex-1")
                    ui.button("Bỏ xem, làm bảng mới", icon="edit", on_click=_exit_readonly_view).props(
                        "dense flat color=amber-8"
                    )
                    if is_admin:
                        ui.button("Mở khoá (Admin)", icon="lock_open", on_click=_admin_unlock).props(
                            "dense outline color=red"
                        )

    async def _admin_unlock():
        ngay = view_state["ngay_dang_xem"] or ngay_input.value
        # Bảng đang xem (mode='locked') — xác định trực tiếp qua `session_id`
        # (07/09/2026: 1 ngày có thể nhiều bảng đã chốt của nhiều người, id là
        # đủ, không cần suy qua ngay/created_by nữa) — xem session_admin_unlock().
        session_id = view_state["session_id"]
        with ui.dialog() as dialog, ui.card():
            ui.label(f"Mở khoá ngày {ngay}?").classes("text-base font-bold text-red-700")
            ui.label(
                "Ngày này sẽ về lại trạng thái BẢN TẠM — người lập bảng sửa/lưu tiếp được. "
                "Chỉ dùng khi thật sự cần sửa lỗi nhập liệu sau khi đã chốt."
            ).classes("text-sm text-gray-500")
            with ui.row().classes("w-full justify-end gap-2 mt-3"):
                ui.button("Huỷ", on_click=dialog.close).props("outline")

                async def _confirm():
                    dialog.close()
                    try:
                        await asyncio.to_thread(
                            api.post,
                            f"/api/doi-chieu-citad/session-by-id/{session_id}/unlock",
                            {},
                        )
                    except Exception as e:
                        if _handle_api_error(e):
                            return
                        ui.notify(f"Lỗi mở khoá: {e}", type="negative")
                        return
                    ui.notify(f"Đã mở khoá ngày {ngay}", type="positive")
                    await _load_session(session_id)
                    if history_refresh.get("fn"):
                        await history_refresh["fn"]()

                ui.button("Xác nhận mở khoá", icon="lock_open", on_click=_confirm).classes(
                    "bg-red-600 hover:bg-red-700 text-white rounded-lg"
                )
        dialog.open()

    def _exit_readonly_view():
        """Nút trên banner chỉ-xem/napas — xoá sạch form (giống nút "Xoá")
        rồi chuyển hẳn sang chế độ 'edit' cho hôm nay, KHÔNG động gì tới bản
        đang xem (bản tạm/bản cuối của người khác vẫn nguyên vẹn trong DB —
        đây chỉ là xoá màn hình, không phải sửa/lưu đè). do_reset() không
        đụng ngay_input/lap_bang_input/kiem_soat_input nên tự set lại 3 ô
        đó ở đây."""
        do_reset(notify=False)
        ngay_input.value = datetime.date.today().strftime('%d/%m/%Y')
        lap_bang_input.value = ""
        kiem_soat_input.value = ""
        _apply_view_mode("edit")
        ui.notify("Đã chuyển sang phiên chấm đối chiếu mới", type="info")

    def get_session_payload() -> dict:
        gD = {str(c): {u: {f: data["gD"][c][u][f] for f in FK} for u in CURS} for c in CONGS}
        phD = {u: {f: data["phD"][u][f] for f in FK} for u in CURS}
        return {
            "ngay": ngay_input.value,
            "lap_bang": lap_bang_input.value or "",
            "kiem_soat": kiem_soat_input.value or "",
            "gD": gD,
            "phD": phD,
            "napas_m": data["napas"]["den_ih_m"],
            "napas_t": data["napas"]["den_ih_t"],
            "ebank_m": data["ebank"]["den_ih_m"],
            "ebank_t": data["ebank"]["den_ih_t"],
            "pssmdp_m": data["pssmdp"]["den_ih_m"],
            "pssmdp_t": data["pssmdp"]["den_ih_t"],
            # None = form TRẮNG (chưa "Tải" bảng nào) → LUÔN tạo bảng MỚI, kể
            # cả khi đã có bảng khác cùng ngày (07/09/2026: 1 người có thể
            # nhiều bảng độc lập/ngày). Có giá trị = đang lưu tiếp ĐÚNG bảng đó
            # (của chính mình ở mode='edit', hoặc góp Napas/PSS-MDP vào bảng
            # người khác ở mode='napas_only') — xem session_save() trong service.
            "session_id": view_state["session_id"],
        }

    async def load_citad_buffer():
        try:
            items = await asyncio.to_thread(api.get, "/api/doi-chieu-citad/citad-buffer")
        except Exception as e:
            if _handle_api_error(e):
                return
            ui.notify(f"Lỗi: {e}", type="negative")
            return
        if not items:
            ui.notify("Chưa có dữ liệu CITAD. Dùng Extension trên trang CITAD!", type="warning")
            return
        # napas_only (đang bổ sung vào bản tạm của NGƯỜI KHÁC): CHỈ được áp
        # 2 item Napas/PSS-MDP — item 5 Cổng dù có trong buffer (vd người
        # này lỡ quét nhầm trang cổng khác) cũng bỏ qua, không ghi vào
        # data["gD"] (field đó bị khoá, có ghi cũng bị backend bỏ khi lưu —
        # nhưng ghi ra màn hình rồi lại không lưu được thì gây hiểu nhầm).
        # KHÔNG xoá buffer nếu còn item bị bỏ qua — người quét nhầm cổng vẫn
        # còn nguyên item đó trong buffer của họ để dùng đúng lúc (creator),
        # không mất trắng vì 1 lượt nạp Napas.
        napas_only = view_state["mode"] == "napas_only"
        count = 0
        skipped = 0
        for item in items:
            src = item.get("source", "")
            so_mon = item.get("soMon", 0)
            so_tien = item.get("soTien", 0)
            # Napas/PSS-MDP quét được từ trang CITAD "Kiểm soát yêu cầu quyết
            # toán lô đến" (Cổng 1, khác nguồn Napas/PSS-MDP từ PaymentHub —
            # xem load_phub_buffer) — cong/loai/chieu/tien của item này chỉ
            # điền cho đủ field bắt buộc ở CitadBufferIn, không mang ý nghĩa
            # thật, bỏ qua luôn không đọc.
            if src == "napas":
                data["napas"]["den_ih_m"] = nv(so_mon)
                data["napas"]["den_ih_t"] = nv(so_tien)
                _set_input(inputs["napasE"]["den_ih_m"], fmt(so_mon))
                _set_input(inputs["napasE"]["den_ih_t"], fmt(so_tien))
                count += 1
                continue
            if src == "pssmdp":
                data["pssmdp"]["den_ih_m"] = nv(so_mon)
                data["pssmdp"]["den_ih_t"] = nv(so_tien)
                _set_input(inputs["pssmdpE"]["den_ih_m"], fmt(so_mon))
                _set_input(inputs["pssmdpE"]["den_ih_t"], fmt(so_tien))
                count += 1
                continue
            if napas_only:
                skipped += 1
                continue
            cong = int(item.get("cong", 0) or 0)
            loai = item.get("loai", "")
            chieu = item.get("chieu", "")
            tien = item.get("tien", "VNĐ")
            if cong not in CONGS or tien not in CURS:
                continue
            fk_m, fk_t = f"{chieu}_{loai}_m", f"{chieu}_{loai}_t"
            if fk_m in FK:
                data["gD"][cong][tien][fk_m] = nv(so_mon)
                data["gD"][cong][tien][fk_t] = nv(so_tien)
                _set_input(inputs["gE"][cong][tien][fk_m], fmt(so_mon))
                _set_input(inputs["gE"][cong][tien][fk_t], fmt(so_tien))
                count += 1
        if skipped == 0:
            try:
                await asyncio.to_thread(api.delete, "/api/doi-chieu-citad/citad-buffer")
            except Exception:
                pass
        recalc()
        msg = f"Đã nạp {count} mục từ CITAD"
        if skipped:
            msg += f" — bỏ qua {skipped} mục 5 Cổng (chỉ nạp được Napas/PSS-MDP ở đây)"
        ui.notify(msg, type="positive" if count else "warning")

    async def load_phub_buffer():
        try:
            items = await asyncio.to_thread(api.get, "/api/doi-chieu-citad/paymenthub-buffer")
        except Exception as e:
            if _handle_api_error(e):
                return
            ui.notify(f"Lỗi: {e}", type="negative")
            return
        if not items:
            ui.notify("Chưa có dữ liệu PaymentHub. Dùng Extension!", type="warning")
            return
        # Xem ghi chú tương tự ở load_citad_buffer() — napas_only chỉ được
        # áp 2 item Napas/PSS-MDP, item PaymentHub thường (dù có trong
        # buffer) bỏ qua, không xoá buffer nếu còn item bị bỏ qua.
        napas_only = view_state["mode"] == "napas_only"
        count = 0
        skipped = 0
        skipped_napas = 0
        for item in items:
            loai, chieu = item.get("loai", ""), item.get("chieu", "")
            tien = item.get("tien", "VNĐ")
            so_mon, so_tien = item.get("soMon", 0), item.get("soTien", 0)
            src = item.get("source", "")
            # Napas/PSS-MDP CHỈ nhận từ CITAD từ 04/09/2026 (xem
            # load_citad_buffer) — cố ý KHÔNG sửa Extension (content_
            # paymenthub.js vẫn tự quét/gửi item này lên buffer như cũ, đỡ
            # phải ra bản Extension mới + cài lại từng máy trạm), web app chỉ
            # chủ động bỏ qua 2 nguồn này khi nạp từ PaymentHub — tránh 2
            # nguồn (CITAD/PaymentHub) đè số liệu lẫn nhau. Luôn bỏ (không
            # tính vào `skipped` chặn xoá buffer bên dưới) — khác `skipped`,
            # đây là dữ liệu KHÔNG BAO GIỜ còn dùng nữa, giữ lại trong buffer
            # cũng vô nghĩa.
            if src in ("napas", "pssmdp"):
                skipped_napas += 1
                continue
            if napas_only:
                skipped += 1
                continue
            if tien not in CURS:
                continue
            fk_m, fk_t = f"{chieu}_{loai}_m", f"{chieu}_{loai}_t"
            if fk_m in FK:
                data["phD"][tien][fk_m] = nv(so_mon)
                data["phD"][tien][fk_t] = nv(so_tien)
                _set_input(inputs["phE"][tien][fk_m], fmt(so_mon))
                _set_input(inputs["phE"][tien][fk_t], fmt(so_tien))
                count += 1
        if skipped == 0:
            try:
                await asyncio.to_thread(api.delete, "/api/doi-chieu-citad/paymenthub-buffer")
            except Exception:
                pass
        recalc()
        # Buffer CHỈ có mục Napas/PSS-MDP (trường hợp thường gặp nhất — người
        # dùng quét đúng trang PaymentHub, đúng ý cũ, nhưng giờ không còn nhận
        # nữa) — không mở đầu bằng "Đã nạp 0 mục" (đọc như báo lỗi/phần mềm
        # hỏng), nói thẳng luôn lý do để người dùng hiểu đây là CHỦ Ý, không
        # phải bug, và biết chính xác phải làm gì tiếp theo.
        if count == 0 and skipped_napas and not skipped:
            ui.notify(
                "Lệnh quyết toán lô bắt buộc phải quét dữ liệu từ cổng Citad — "
                "PaymentHub không dùng được cho Napas/PSS-MDP nữa.",
                type="warning",
            )
            return
        msg = f"Đã nạp {count} mục từ PaymentHub"
        if skipped:
            msg += f" — bỏ qua {skipped} mục (chỉ nạp được Napas/PSS-MDP ở đây)"
        if skipped_napas:
            msg += (f" — bỏ qua {skipped_napas} mục Napas/PSS-MDP. "
                    "Lệnh quyết toán lô bắt buộc phải quét dữ liệu từ cổng Citad")
        # skipped_napas ép cảnh báo dù count > 0 (có nạp được mục 5 Cổng khác) —
        # đây là điều người dùng CẦN chú ý (quét nhầm cổng), không để lẫn vào
        # thông báo "positive" chung chung của các mục nạp thành công khác.
        ui.notify(msg, type="warning" if skipped_napas else ("positive" if count else "warning"))

    def _mode_for_meta(sess: dict) -> tuple[str, int | None, int | None, str]:
        """Suy ra mode xem/sửa từ _meta_status/_meta_created_by(_username) —
        xem session_get()/get_history_entry_data() trong service. Trả
        (mode, session_id, created_by, created_by_name)."""
        status = sess.get("_meta_status")
        session_id = sess.get("_meta_session_id")
        created_by = sess.get("_meta_created_by")
        created_by_name = sess.get("_meta_created_by_username") or ""
        if status == "final":
            return "locked", session_id, created_by, created_by_name
        if created_by and created_by != current_user.get("id"):
            return "napas_only", session_id, created_by, created_by_name
        return "edit", session_id, created_by, created_by_name

    async def _load_session(session_id: int):
        """Tải bản HIỆN HÀNH của ĐÚNG 1 bảng theo `session_id` (session_get —
        khác _load_history_entry() luôn lấy đúng 1 dòng lịch sử cụ thể) vào
        form, áp đúng mode theo _meta_* — gọi sau khi Lưu (backend trả về
        đúng `session_id` vừa lưu, kể cả bảng MỚI vừa tạo) hoặc sau khi Admin
        mở khoá, để form phản ánh đúng trạng thái mới nhất, không cần F5."""
        try:
            sess = await asyncio.to_thread(
                api.get, f"/api/doi-chieu-citad/session-by-id/{session_id}"
            )
        except Exception as e:
            if _handle_api_error(e):
                return
            ui.notify(f"Lỗi tải: {e}", type="negative")
            return
        if not sess:
            _apply_view_mode("edit")
            return
        apply_session_data(sess)
        view_state["ngay_dang_xem"] = sess.get("ngay") or ngay_input.value
        mode, session_id, created_by, created_by_name = _mode_for_meta(sess)
        _apply_view_mode(mode, session_id, created_by, created_by_name)

    async def _save_session_now(status: str):
        payload = get_session_payload()
        payload["status"] = status
        try:
            resp = await asyncio.to_thread(api.post, "/api/doi-chieu-citad/session", payload)
        except Exception as e:
            if _handle_api_error(e):
                return
            ui.notify(f"Lỗi lưu: {e}", type="negative")
            return
        ui.notify(
            f"Đã lưu bản {'CUỐI' if status == 'final' else 'tạm'} ngày {ngay_input.value}", type="positive"
        )
        if history_refresh.get("fn"):
            await history_refresh["fn"]()
        # Tải lại ĐÚNG bảng vừa lưu — backend luôn trả về session_id thật sự
        # đã lưu (mới tạo hoặc lưu tiếp), không còn suy qua ngay/created_by
        # (07/09/2026: 1 ngày có thể nhiều bảng của nhiều người/của cùng 1
        # người, suy qua ngay sẽ mơ hồ không biết đúng bảng nào vừa lưu).
        await _load_session(resp["session_id"])

    def do_save_session(status: str):
        # Phòng vệ thêm — nút tương ứng đã ẩn theo mode (_apply_view_mode),
        # chặn lại ở đây phòng còn đường nào bấm được nút ẩn (vd bàn phím).
        if view_state["mode"] == "locked":
            ui.notify("Ngày này đã chốt bảng cuối — không lưu được nữa", type="warning")
            return
        if status == "final" and view_state["mode"] == "napas_only":
            ui.notify("Chỉ người lập bảng mới được \"Lưu bảng cuối\"", type="warning")
            return
        is_final = status == "final"
        with ui.dialog() as dialog, ui.card():
            if is_final:
                ui.label(f"CHỐT bảng cuối ngày {ngay_input.value}?").classes(
                    "text-base font-bold text-red-700"
                )
                ui.label(
                    "Sau khi chốt, KHÔNG AI sửa được nữa (kể cả bạn) — chỉ Admin mở khoá lại "
                    "được. Kiểm tra kỹ số liệu trước khi xác nhận."
                ).classes("text-sm text-gray-500")
            else:
                ui.label(f"Lưu bảng tạm ngày {ngay_input.value}?").classes("text-base font-bold")
                ui.label(
                    "Bảng tạm — người khác trong phòng vẫn vào được (qua tab \"Lịch sử\") để bổ "
                    "sung riêng Napas/PSS-MDP. Bấm \"Lưu bảng cuối\" khi đã chấm xong hẳn để chốt."
                ).classes("text-sm text-gray-500")
            with ui.row().classes("w-full justify-end gap-2 mt-3"):
                ui.button("Huỷ", on_click=dialog.close).props("outline")

                async def _confirm():
                    dialog.close()
                    await _save_session_now(status)

                ui.button(
                    "Xác nhận chốt bảng cuối" if is_final else "Xác nhận lưu bảng tạm",
                    icon="save",
                    on_click=_confirm,
                ).classes(
                    ("bg-red-600 hover:bg-red-700" if is_final else "bg-emerald-600 hover:bg-emerald-700")
                    + " text-white rounded-lg"
                )
        dialog.open()

    async def _load_history_entry(history_id: int, ngay_hien_thi: str):
        """Tải đúng số liệu của 1 lần lưu cụ thể (không phải bản hiện hành)
        vào form, áp đúng mode theo _meta_* của bản đó (xem _mode_for_meta):
        bản CUỐI luôn 'locked' (chỉ xem); bản TẠM thì 'edit' nếu đúng người
        lập bảng, 'napas_only' nếu người khác — không còn ép readonly toàn
        bộ như trước, để đúng yêu cầu cho phép người khác bổ sung Napas/
        PSS-MDP vào bản tạm qua Lịch sử."""
        try:
            sess = await asyncio.to_thread(api.get, f"/api/doi-chieu-citad/history-entry/{history_id}")
        except Exception as e:
            if _handle_api_error(e):
                return
            ui.notify(f"Lỗi tải bản lịch sử: {e}", type="negative")
            return
        apply_session_data(sess)
        view_state["ngay_dang_xem"] = ngay_hien_thi
        mode, session_id, created_by, created_by_name = _mode_for_meta(sess)
        _apply_view_mode(mode, session_id, created_by, created_by_name)
        tabs.set_value(tab_doi_chieu)
        # entry_staff_name = người THỰC SỰ lưu ĐÚNG dòng lịch sử vừa bấm "Tải"
        # (khác created_by_name — chủ bảng, cố định suốt vòng đời bảng). Thiếu
        # tên này thì bấm "Tải" vào dòng của B vẫn chỉ thấy tên A (chủ bảng)
        # khắp màn hình, tưởng nhầm A tự lưu hết — phản hồi thật 07/09/2026.
        entry_staff_name = sess.get("_meta_entry_staff_name") or ""
        msg = {
            "edit": "Đang xem bảng tạm của bạn — sửa/lưu tiếp được",
            "napas_only": f"Đang xem bảng tạm của {created_by_name} — chỉ bổ sung được Napas/PSS-MDP",
            "locked": "Đang xem bảng đã chốt (chỉ đọc)",
        }.get(mode, "Đang xem")
        if entry_staff_name and entry_staff_name != created_by_name:
            msg += f" (dòng này do {entry_staff_name} lưu)"
        ui.notify(f"{msg} — ngày {ngay_hien_thi}", type="positive")

    async def _show_edit_log(history_id: int):
        """Dialog liệt kê MỌI người đã lưu góp phần vào dòng lịch sử này, kèm
        thời gian — kể cả những lần lưu tạm bị gộp không có dòng lịch sử
        riêng (xem get_history_edits() ở service)."""
        try:
            edits = await asyncio.to_thread(
                api.get, f"/api/doi-chieu-citad/history-entry/{history_id}/edits"
            )
        except Exception as e:
            if _handle_api_error(e):
                return
            ui.notify(f"Lỗi tải nhật ký sửa: {e}", type="negative")
            return
        with ui.dialog() as dialog, ui.card().classes("w-full max-w-md"):
            ui.label("Nhật ký sửa bảng tạm").classes("text-lg font-bold text-red-900")
            if not edits:
                ui.label("Chưa có dữ liệu.").classes("text-sm text-gray-500 py-2")
            else:
                with ui.column().classes("w-full gap-0 border border-gray-200 rounded-lg overflow-hidden mt-2"):
                    for i, e in enumerate(edits, start=1):
                        with ui.row().classes(
                            "w-full items-center gap-2 px-3 py-2"
                            + ("" if i == len(edits) else " border-b border-gray-100")
                        ):
                            ui.label(str(i)).classes("text-xs text-gray-400 w-5")
                            with ui.column().classes("flex-grow gap-0"):
                                ui.label(e.get("full_name") or e["username"]).classes("text-sm font-medium")
                                ui.label(e["username"]).classes("text-xs text-gray-400")
                            ui.label(e["created_at"]).classes("text-xs text-gray-500")
            with ui.row().classes("w-full justify-end mt-3"):
                ui.button("Đóng", on_click=dialog.close).props("flat")
        dialog.open()

    def _render_history_entries(container, ngay: str, entries: list):
        """Danh sách từng lần lưu của 1 ngày — dùng chung cho tab Lịch sử
        (mở rộng tại chỗ khi bấm vào 1 ngày)."""
        with container:
            if not entries:
                ui.label("Chưa có ai lưu đối chiếu cho ngày này.").classes("text-sm text-gray-500 p-2")
                return
            with ui.column().classes("w-full border border-gray-200 rounded-xl gap-0 overflow-hidden"):
                for i, r in enumerate(entries, start=1):
                    is_last = i == len(entries)
                    with ui.row().classes(
                        "w-full items-center gap-0 px-2 py-1"
                        + ("" if is_last else " border-b border-gray-200")
                        + (" bg-emerald-50" if is_last else "")
                    ):
                        ui.label(str(i)).classes("text-xs text-gray-500 w-6 border-r border-gray-200 pr-2 mr-2")
                        ui.label(r["username"]).classes(
                            "text-sm font-bold flex-grow border-r border-gray-200 pr-2 mr-2"
                        )
                        ui.label(r["created_at"]).classes("text-xs text-gray-400 border-r border-gray-200 pr-2 mr-2")
                        if r.get("status") == "final":
                            ui.badge("Chính thức").props('color="positive"').classes("mr-2")
                        else:
                            ui.badge("Tạm").props('color="grey-7"').classes("mr-2")
                        if is_last:
                            ui.badge("Bản hiện hành").props('color="primary"').classes("mr-2")
                        ui.button(
                            icon="group",
                            on_click=lambda _, hid=r["id"]: _show_edit_log(hid),
                        ).props("flat dense round size=sm color=red-8").tooltip("Ai đã sửa bảng tạm này")
                        ui.button(
                            icon="download",
                            on_click=lambda _, hid=r["id"], ng=ngay: _load_history_entry(hid, ng),
                        ).props("outline dense round size=sm").tooltip("Tải bản này")

    def _build_history_panel(initial_ngay: str | None = None):
        """Tab "Lịch sử" — bảng TẤT CẢ các ngày đã có người chấm, lọc theo
        khoảng ngày, bấm 1 dòng để mở rộng tại chỗ xem chi tiết từng lần lưu
        của ngày đó (không dùng dialog — đúng pattern _build_history_panel
        của frontend/pages/swift_recon.py). `initial_ngay` (dd/mm/yyyy) đến
        từ deep-link ?ngay= của Sổ trực cuối ngày — set sẵn cả 2 ô lọc để
        chỉ hiện đúng ngày đó."""
        with ui.row().classes("w-full items-end gap-3 flex-wrap mb-2"):
            tu_input = _date_filter_input("Từ ngày")
            den_input = _date_filter_input("Đến ngày")
            if initial_ngay:
                tu_input.value = initial_ngay
                den_input.value = initial_ngay
            nguoi_input = ui.input("Tên người chấm", value="").props(
                "dense outlined clearable"
            ).classes("w-52")
            ui.button("Lọc", icon="filter_alt", on_click=lambda: load_days()).props("outline")

            async def clear_filter():
                tu_input.value = ""
                den_input.value = ""
                nguoi_input.value = ""
                await load_days()

            ui.button("Xoá lọc", icon="clear", on_click=clear_filter).props("outline color=grey dense")

        days_area = ui.column().classes("w-full gap-1")

        async def load_days():
            days_area.clear()
            try:
                params = {}
                if tu_input.value:
                    params["tu_ngay"] = tu_input.value
                if den_input.value:
                    params["den_ngay"] = den_input.value
                if nguoi_input.value:
                    params["nguoi_cham"] = nguoi_input.value
                rows = await asyncio.to_thread(api.get, "/api/doi-chieu-citad/reconciliation-days", params)
            except Exception as e:
                if _handle_api_error(e):
                    return
                ui.notify(f"Lỗi tải lịch sử: {e}", type="negative")
                return
            with days_area:
                if not rows:
                    msg = (
                        "Không có ngày nào khớp bộ lọc — thử bấm \"Xoá lọc\" để xem tất cả."
                        if (tu_input.value or den_input.value or nguoi_input.value)
                        else "Chưa có ngày nào được chấm."
                    )
                    ui.label(msg).classes("text-gray-400 p-4")
                    return
                with ui.column().classes("w-full border border-gray-200 rounded-xl gap-0 overflow-hidden"):
                    with ui.row().classes(
                        "w-full items-center gap-0 px-3 py-2 bg-blue-600 border-b border-gray-200 "
                        "text-xs font-semibold text-white"
                    ):
                        ui.label("Ngày").classes("w-28 border-r border-white/30 pr-2 mr-2")
                        ui.label("Người chấm").classes("w-44 border-r border-white/30 pr-2 mr-2")
                        ui.label("Số bảng").classes("w-24 text-center border-r border-white/30 pr-2 mr-2")
                        ui.label("Cập nhật gần nhất").classes("flex-1")
                    # TẦNG 1 = (ngày, created_by) — `rows` đã sắp (ngày, tên chủ
                    # bảng) LIỀN NHAU từ backend (xem get_reconciliation_days()),
                    # nên chỉ cần duyệt tuần tự gom các dòng liền kề cùng
                    # (ngay, created_by) thành 1 nhóm, không cần tự sort lại.
                    # 07/09/2026: đổi từ "1 dòng/bảng" sang "1 dòng/người" vì 1
                    # người giờ có thể có NHIỀU bảng độc lập/ngày (xem docstring
                    # đầu doi_chieu_citad_service.py) — mỗi bảng của người đó là
                    # 1 dòng TẦNG 2 lồng bên trong, không phải 1 dòng TẦNG 1 riêng.
                    groups = []
                    for r in rows:
                        if groups and groups[-1][0] == r["ngay"] and groups[-1][1] == r["created_by"]:
                            groups[-1][2].append(r)
                        else:
                            groups.append((r["ngay"], r["created_by"], [r]))
                    # Dòng ngăn cách xanh mỗi khi sang tháng khác — cùng kiểu
                    # đã dùng ở tab Lịch sử của Sổ trực (so_truc.py). `ngay`
                    # ở đây là dd/mm/yyyy (khác truc_date ISO của Sổ trực) nên
                    # lấy tháng/năm bằng cách tách chuỗi thay vì cắt 7 ký tự đầu.
                    current_month = None
                    for gi, (ngay, owner_id, bang_list) in enumerate(groups):
                        try:
                            _, m, y = ngay.split("/")
                            month_key = f"{y}-{m}"
                        except Exception:
                            month_key = None
                        if month_key is not None and month_key != current_month:
                            current_month = month_key
                            with ui.row().classes(
                                "w-full items-center px-3 py-1.5 bg-emerald-400"
                                + ("" if gi == 0 else " border-t border-gray-200")
                            ):
                                ui.label(f"{int(m)}/{y}").classes("text-xs font-bold text-emerald-950")
                        _person_row(ngay, bang_list, is_last=(gi == len(groups) - 1))

        def _session_row(ngay: str, r: dict, idx: int, is_last: bool):
            """TẦNG 2 — 1 bảng (`session_id`) ĐỘC LẬP của người ở dòng TẦNG 1
            cha (cùng ngày). Bảng chỉ có ĐÚNG 1 lần lưu thì GỘP LUÔN thành 1
            dòng duy nhất kèm sẵn nút Tải/Ai đã sửa — không bắt bấm thêm 1
            lần mở rộng chỉ để thấy lại đúng thông tin đã có ở dòng tóm tắt
            (phản hồi thực tế 07/09/2026: 2 dòng đó trùng lặp vô ích). Bảng
            có TỪ 2 lần lưu trở lên mới cần bấm để bung TẦNG 3 (danh sách
            thật sự có ý nghĩa để xem — tái dùng _render_history_entries).

            Dòng gộp dùng thẳng `r["last_history_id"]` (MAX(h.id) tính sẵn ở
            get_reconciliation_days(), review 07/09/2026) — KHÔNG gọi thêm
            GET .../history nữa: trước đây mỗi bảng 1-lần-lưu bắn 1 request
            RIÊNG khi bung Tầng 1, người có N bảng/ngày phải chờ N lượt
            đi-về tuần tự chỉ để lấy đúng 1 con số mỗi lần (N+1 request)."""
            session_id = r["session_id"]

            def _draw_expandable():
                # Dạng bấm-mở-rộng gốc (Tầng 2 tóm tắt -> bấm bung Tầng 3) —
                # dùng cho bảng có TỪ 2 lần lưu trở lên, VÀ dùng làm phương án
                # lùi về khi `last_history_id` thiếu bất thường (xem bên dưới)
                # để không mất hẳn chức năng Tải/Ai-đã-sửa, người dùng bấm lại
                # được để thử tải lần nữa thay vì thấy 1 dòng cụt không rõ lý do.
                expanded = {"open": False}
                with ui.column().classes("w-full" + ("" if is_last else " border-b border-gray-100")):
                    with ui.row().classes(
                        "w-full items-center gap-0 px-3 py-1.5 cursor-pointer hover:bg-gray-50"
                    ) as row:
                        ui.label(f"Bảng {idx}").classes(
                            "w-28 text-sm text-gray-600 border-r border-gray-200 pr-2 mr-2"
                        )
                        with ui.row().classes("w-44 items-center gap-1 border-r border-gray-200 pr-2 mr-2"):
                            if r.get("status") == "final":
                                ui.badge("Chính thức").props('color="positive"')
                            else:
                                ui.badge("Tạm").props('color="grey-7"')
                        ui.label(str(r["so_lan_luu"])).classes(
                            "w-24 text-center border-r border-gray-200 pr-2 mr-2"
                        )
                        ui.label(r["updated_at"] or "").classes("flex-1 text-xs text-gray-400")
                        ui.icon("expand_more").classes("text-gray-500")
                    detail_area = ui.column().classes("w-full pl-4")

                    async def toggle_detail():
                        if expanded["open"]:
                            detail_area.clear()
                            expanded["open"] = False
                            return
                        try:
                            entries = await asyncio.to_thread(
                                api.get, f"/api/doi-chieu-citad/session-by-id/{session_id}/history"
                            )
                        except Exception as e:
                            if _handle_api_error(e):
                                return
                            ui.notify(f"Lỗi: {e}", type="negative")
                            return
                        expanded["open"] = True
                        _render_history_entries(detail_area, ngay, entries)

                    row.on("click", toggle_detail)

            if r["so_lan_luu"] != 1:
                _draw_expandable()
                return

            hid = r.get("last_history_id")
            if hid is None:
                # so_lan_luu nói có 1 lần lưu nhưng last_history_id lại rỗng —
                # dữ liệu không khớp (không nên xảy ra, cả 2 field cùng lọc
                # theo session_id trong 1 câu SQL, nhưng nếu có thì KHÔNG
                # được che giấu bằng cách vẽ dòng thiếu nút im lặng) — lùi về
                # dạng bấm-mở-rộng để người dùng còn thấy bất thường và tự
                # kiểm tra được, thay vì tưởng bảng này không có nút nào.
                ui.notify(f"Bảng {idx}: dữ liệu lịch sử không khớp — bấm dòng để tải lại", type="warning")
                _draw_expandable()
                return

            with ui.row().classes(
                "w-full items-center gap-0 px-3 py-1.5"
                + ("" if is_last else " border-b border-gray-100")
            ):
                ui.label(f"Bảng {idx}").classes(
                    "w-28 text-sm text-gray-600 border-r border-gray-200 pr-2 mr-2"
                )
                with ui.row().classes("w-44 items-center gap-1 border-r border-gray-200 pr-2 mr-2"):
                    if r.get("status") == "final":
                        ui.badge("Chính thức").props('color="positive"')
                    else:
                        ui.badge("Tạm").props('color="grey-7"')
                # "1" cố định (so_lan_luu == 1 ở nhánh này) — giữ ĐÚNG 4 cột
                # như _draw_expandable() (w-28/w-44/w-24/flex-1), không thì 2
                # kiểu dòng Tầng 2 lệch cột "Cập nhật" khi đứng cạnh nhau
                # (thẩm mỹ, review 07/09/2026).
                ui.label("1").classes("w-24 text-center border-r border-gray-200 pr-2 mr-2")
                ui.label(r["updated_at"] or "").classes("flex-1 text-xs text-gray-400")
                ui.button(
                    icon="group", on_click=lambda _, h=hid: _show_edit_log(h)
                ).props("flat dense round size=sm color=red-8").tooltip("Ai đã sửa bảng tạm này")
                ui.button(
                    icon="download", on_click=lambda _, h=hid, ng=ngay: _load_history_entry(h, ng)
                ).props("outline dense round size=sm").tooltip("Tải bản này")

        def _person_row(ngay: str, bang_list: list, is_last: bool):
            """TẦNG 1 — 1 người lập bảng trong 1 ngày. Bung ra thấy TẦNG 2 =
            từng bảng ĐỘC LẬP người đó đã tạo cho ngày này — mỗi lần họ gõ
            lại đúng ngày rồi Lưu mà KHÔNG bấm "Tải" tiếp tục bảng cũ (kể cả
            sau khi 1 bảng cũ đã "Lưu bản cuối" rồi họ chấm lại) sinh ra 1
            bảng riêng ở đây, không gộp/đè lên bảng trước (xác nhận yêu cầu
            Phòng Thanh toán 07/09/2026)."""
            owner_name = bang_list[0]["created_by_name"] or bang_list[0]["created_by_username"] or "—"
            latest = max((b["updated_at"] or "" for b in bang_list), default="")
            expanded = {"open": False}
            with ui.column().classes("w-full" + ("" if is_last else " border-b border-gray-200")):
                with ui.row().classes(
                    "w-full items-center gap-0 px-3 py-2 cursor-pointer hover:bg-blue-50/50 bg-gray-50/70"
                ) as row:
                    ui.label(ngay).classes("w-28 font-bold border-r border-gray-200 pr-2 mr-2")
                    ui.label(owner_name).classes(
                        "w-44 text-sm font-semibold border-r border-gray-200 pr-2 mr-2"
                    )
                    ui.label(str(len(bang_list))).classes(
                        "w-24 text-center border-r border-gray-200 pr-2 mr-2"
                    )
                    ui.label(latest).classes("flex-1 text-xs text-gray-400")
                    ui.icon("expand_more").classes("text-gray-500")
                detail_area = ui.column().classes("w-full pl-4")

                def toggle_person_detail():
                    if expanded["open"]:
                        detail_area.clear()
                        expanded["open"] = False
                        return
                    expanded["open"] = True
                    with detail_area:
                        for bi, b in enumerate(bang_list, start=1):
                            _session_row(ngay, b, bi, is_last=(bi == len(bang_list)))

                row.on("click", toggle_person_detail)

        history_refresh["fn"] = load_days
        ui.timer(0.1, load_days, once=True)

    def do_reset(notify: bool = True):
        # Bấm "Xoá" chỉ hiện khi mode='edit' (xem _apply_view_mode) — nhưng
        # mode='edit' KHÔNG có nghĩa form đang trắng: bấm "Tải" bảng CỦA
        # CHÍNH MÌNH từ tab Lịch sử cũng vào mode='edit' kèm
        # view_state["session_id"] trỏ đúng bảng đó (để "Lưu tiếp" cập nhật
        # tại chỗ, không đẻ bảng mới — xem get_session_payload()). Trước đây
        # do_reset() chỉ xoá số liệu trên màn hình, KHÔNG đụng session_id —
        # bấm "Xoá" rồi gõ số liệu mới rồi "Lưu" sẽ ÂM THẦM GHI ĐÈ đúng bảng
        # vừa tải (mất trắng số liệu cũ), thay vì tạo bảng mới độc lập như
        # người dùng tưởng khi thấy màn hình đã sạch — rủi ro mất dữ liệu
        # thật (phát hiện khi rà soát lại 07/09/2026, chưa từng có ai báo vì
        # trước đây 1 người chỉ có ĐÚNG 1 bảng/ngày nên "xoá rồi lưu lại" và
        # "tạo bảng mới" là MỘT, không phân biệt được cho tới tính năng nhiều
        # bảng độc lập/ngày hôm nay). Xoá thì PHẢI tách khỏi bảng đang tải,
        # để lần lưu tiếp theo luôn tạo bảng mới, không đè lên bảng cũ.
        view_state["session_id"] = None
        for c in CONGS:
            for u in CURS:
                for f in FK:
                    data["gD"][c][u][f] = 0.0
                    _set_input(inputs["gE"][c][u][f], '')
        for u in CURS:
            for f in FK:
                data["phD"][u][f] = 0.0
                _set_input(inputs["phE"][u][f], '')
        for f in ("den_ih_m", "den_ih_t"):
            data["napas"][f] = 0.0
            data["ebank"][f] = 0.0
            data["pssmdp"][f] = 0.0
            _set_input(inputs["napasE"][f], '')
            _set_input(inputs["pssmdpE"][f], '')
        recalc()
        if notify:
            ui.notify("Đã xoá toàn bộ dữ liệu — lưu tiếp theo sẽ tạo bảng MỚI, không ghi đè bảng vừa tải", type="info")

    async def _do_download_export():
        gD = {str(c): {u: {f: data["gD"][c][u][f] for f in FK} for u in CURS} for c in CONGS}
        phD = {u: {f: data["phD"][u][f] for f in FK} for u in CURS}
        payload = {
            "day_str": ngay_input.value,
            "sheet_name": (ngay_input.value or "Sheet1").replace("/", "_"),
            "lb": lap_bang_input.value or "",
            "ks": kiem_soat_input.value or "",
            "gD": gD,
            "phD": phD,
            "nm": data["napas"]["den_ih_m"],
            "nt": data["napas"]["den_ih_t"],
            "em": data["ebank"]["den_ih_m"],
            "et": data["ebank"]["den_ih_t"],
            "sm": data["pssmdp"]["den_ih_m"],
            "st": data["pssmdp"]["den_ih_t"],
        }
        try:
            content = await asyncio.to_thread(api.post_download, "/api/doi-chieu-citad/export", payload)
            ui.download(content, f"Doi_chieu_CITAD_{payload['sheet_name']}.xlsx")
        except Exception as e:
            if _handle_api_error(e):
                return
            ui.notify(f"Lỗi xuất Excel: {e}", type="negative")

    def do_export():
        # Xem trước ĐẦY ĐỦ đúng các dòng sẽ có trong file Excel tải về (khớp
        # từng dòng với doi_chieu_citad_service.py::build_xlsx: Payment theo
        # từng loại tiền, CITAD tổng, từng Cổng × loại tiền, Napas, PSS - MDP,
        # Chênh lệch) — không chỉ 3 dòng tóm tắt như trước, để người dùng
        # soát được đúng số liệu chi tiết trước khi tải, giống hệt thứ tự
        # trong Excel (chỉ khác: header ở đây 1 tầng thay vì 3 tầng gộp ô
        # "LỆNH ĐI/LỆNH ĐẾN" như Excel — tên cột ĐI/ĐẾN IH/IL Món/Tiền đã
        # chứa đủ thông tin, và đồng bộ đúng kiểu header các bảng khác trên
        # trang này).
        ci, ph = _compute_totals_group(CURS)
        cols = [
            {"name": "label", "label": "", "field": "label", "align": "left"},
            {"name": "cur", "label": "Loại tiền", "field": "cur", "align": "center"},
        ] + [{"name": fk, "label": lbl, "field": fk, "align": "center"} for fk, lbl in zip(FK, FK_LBL)]

        rows = []

        def _add_row(label, cur, vals):
            row = {"id": len(rows), "label": label, "cur": cur}
            for fk, v in zip(FK, vals):
                row[fk] = fmt(v) or "—"
            rows.append(row)

        for cur in ["EUR", "USD", "VNĐ"]:  # đúng thứ tự Payment trong Excel
            _add_row(f"Payment {cur}", cur, [data["phD"][cur][f] for f in FK])
        _add_row("CITAD (tổng)", "", [ci[f] for f in FK])
        for cong in CONGS:
            for i, cur in enumerate(CURS):
                _add_row(f"Cổng {cong}" if i == 0 else "", cur, [data["gD"][cong][cur][f] for f in FK])
        _add_row("Napas", "", [0, 0, 0, 0, data["napas"]["den_ih_m"], data["napas"]["den_ih_t"], 0, 0])
        _add_row("PSS - MDP", "", [0, 0, 0, 0, data["pssmdp"]["den_ih_m"], data["pssmdp"]["den_ih_t"], 0, 0])
        diff_row = {"id": len(rows), "label": "CHÊNH LỆCH", "cur": ""}
        for fk in FK:
            diff_row[fk] = diff_labels["diff"][fk].text  # tái dùng text đã tính sẵn, luôn khớp trang
        rows.append(diff_row)

        with ui.dialog() as dialog, ui.card().classes("w-full max-w-6xl"):
            ui.label(f"Xem trước — Đối chiếu CITAD ngày {ngay_input.value or '—'}").classes(
                "text-lg font-bold text-gray-800"
            )
            ui.label(
                f"Lập bảng: {lap_bang_input.value or '—'}     Kiểm soát: {kiem_soat_input.value or '—'}"
            ).classes("text-sm text-gray-500 mb-2")
            with ui.element("div").classes("w-full overflow-x-auto"):
                with ui.table(columns=cols, rows=rows, row_key="id").props(
                    'bordered dense separator="cell" table-header-class="bg-blue-900 text-white"'
                ).classes("w-full"):
                    pass
            with ui.row().classes("w-full justify-end gap-2 mt-3"):
                ui.button("Đóng", on_click=dialog.close).props("outline")

                async def _confirm_download():
                    await _do_download_export()
                    dialog.close()

                ui.button("Tải xuống", icon="download", on_click=_confirm_download).classes(
                    "bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg"
                )
        dialog.open()

    # ── Danh sách tên Phòng Thanh toán cho ô "Lập bảng"/"Kiểm soát" ───────────
    # ui.select(with_input, new_value_mode="add-unique") — vẫn gõ tay tự do
    # được như ui.input cũ (giá trị gõ không có trong danh sách vẫn nhận),
    # thêm được bấm chọn từ danh sách có sẵn. Tra department theo CODE
    # "PAYMENT" thay vì hardcode id — tránh phụ thuộc thứ tự tạo phòng ban.
    async def _load_payment_staff_names():
        try:
            depts = await asyncio.to_thread(api.get, "/api/departments/")
            dept = next((d for d in depts if d.get("code") == "PAYMENT"), None)
            if not dept:
                _log.warning(
                    "Không tìm thấy phòng ban code='PAYMENT' — 2 ô Lập bảng/Kiểm soát không có gợi ý tên"
                )
                return
            staff = await asyncio.to_thread(
                api.get, "/api/staff/", {"department_id": dept["id"], "active_only": True}
            )
        except Exception as e:
            # Danh sách gợi ý — lỗi ở đây không được chặn cả trang, nhưng PHẢI
            # ghi log: options rỗng nhìn y hệt "phòng không có ai", không có log
            # thì không có đường nào biết vì sao tên biến mất.
            _log.warning("Không tải được danh sách nhân viên Phòng Thanh toán: %s", e)
            return
        names = {s["full_name"] for s in staff if s.get("full_name")}
        # GỘP vào options đang có, KHÔNG ghi đè. apply_session_data() tự bơm tên
        # người ký cũ (đã nghỉ/chuyển phòng) vào options để giữ được giá trị, và
        # new_value_mode="add-unique" cũng thêm tên người dùng vừa gõ tay vào đó.
        # Gán đè cả danh sách thì ChoiceElement._update_options() thấy .value
        # không còn trong options nữa và đổi ngay thành None — đúng lại lỗ hổng
        # vừa vá ở PR#53, chỉ khác đường đi.
        for sel in (lap_bang_input, kiem_soat_input):
            sel.options = sorted({*(sel.options or []), *names})
            sel.update()

    # ── Kết nối Extension (mã kết nối cá nhân — xem docstring api/doi_chieu_citad.py) ──
    ext_status_label = None

    async def refresh_extension_status():
        try:
            status = await asyncio.to_thread(api.get, "/api/doi-chieu-citad/extension-token/status")
        except Exception:
            return
        if status.get("connected"):
            last = status.get("last_used_at") or "chưa dùng lần nào"
            ext_status_label.text = f"● Đã kết nối — lần dùng gần nhất: {last}"
            ext_status_label.classes(remove="bg-gray-100 text-gray-500", add="bg-emerald-50 text-emerald-700")
        else:
            ext_status_label.text = "○ Chưa kết nối Extension"
            ext_status_label.classes(remove="bg-emerald-50 text-emerald-700", add="bg-gray-100 text-gray-500")

    async def _try_auto_connect_extension(token: str) -> bool:
        """Gửi trực tiếp {server, token} vào extension qua
        chrome.runtime.sendMessage (chỉ hoạt động nếu extension_citad đã
        được cài — Chrome tự chặn theo whitelist origin khai trong
        manifest.json::externally_connectable, xem background.js). Trả về
        False (không throw) cho MỌI lý do thất bại — chưa cài extension,
        trình duyệt không phải Chromium (Chrome/Edge/Cốc Cốc/...), hoặc bị
        chặn — để luôn còn đường lùi là dán tay."""
        # server LẤY ĐỘNG từ window.location.origin (chạy trong trình duyệt
        # người dùng) — đó chính là địa chỉ họ gõ để vào ứng dụng, đúng cổng
        # proxy phục vụ (api_proxy.py). KHÔNG dùng api.BACKEND_URL (địa chỉ
        # backend NỘI BỘ máy chủ, vd 127.0.0.1:8000) — trên máy trạm không
        # có gì lắng nghe ở đó, và nếu người dùng đã cấu hình tay đúng thì
        # bấm nút này sẽ GHI ĐÈ sang giá trị sai. Xem review PR #17.
        js = f"""
            return await new Promise((resolve) => {{
                if (!(window.chrome && chrome.runtime && chrome.runtime.sendMessage)) {{
                    resolve({{ok: false, error: 'no_chrome_runtime'}});
                    return;
                }}
                try {{
                    chrome.runtime.sendMessage({_EXTENSION_ID!r}, {{
                        type: 'SET_CONFIG',
                        server: window.location.origin,
                        token: {json.dumps(token)},
                    }}, (response) => {{
                        if (chrome.runtime.lastError) {{
                            resolve({{ok: false, error: chrome.runtime.lastError.message}});
                        }} else {{
                            resolve(response || {{ok: false, error: 'empty_response'}});
                        }}
                    }});
                }} catch (e) {{
                    resolve({{ok: false, error: String(e)}});
                }}
            }});
        """
        try:
            result = await ui.run_javascript(js, timeout=3.0)
        except Exception:
            return False
        return bool(isinstance(result, dict) and result.get("ok"))

    async def do_create_extension_token():
        try:
            result = await asyncio.to_thread(api.post, "/api/doi-chieu-citad/extension-token", {})
        except Exception as e:
            if _handle_api_error(e):
                return
            ui.notify(f"Lỗi: {e}", type="negative")
            return
        token = result["token"]
        auto_ok = await _try_auto_connect_extension(token)
        with ui.dialog() as dialog, ui.card().classes("w-full max-w-lg"):
            if auto_ok:
                ui.label("✓ Đã tự động kết nối vào Extension").classes("text-lg font-bold text-green-700")
                ui.label(
                    "Mã kết nối mới đã được gửi thẳng vào Extension đang cài trên trình duyệt "
                    "này — không cần dán tay. Có thể dùng ngay các nút \"Lấy dữ liệu\" trên "
                    "trang CITAD/PaymentHub."
                ).classes("text-sm text-gray-500")
                ui.button("Đóng", on_click=dialog.close).classes(
                    "bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg mt-2"
                )
            else:
                ui.label("Mã kết nối Extension mới").classes("text-lg font-bold")
                ui.label(
                    "Không tự động kết nối được (chưa cài Extension trên trình duyệt này, hoặc "
                    "trình duyệt không hỗ trợ) — chỉ hiện mã ĐÚNG 1 LẦN, sao chép ngay, rồi bấm "
                    "icon Extension trên thanh công cụ trình duyệt → \"Tuỳ chọn\" → dán vào ô Mã kết "
                    "nối. Tạo mã mới sẽ tự động huỷ mã cũ."
                ).classes("text-sm text-gray-500")
                token_input = ui.input(value=token).props("readonly outlined dense").classes("w-full font-mono")
                with ui.row().classes("w-full justify-end gap-2 mt-2"):
                    ui.button(
                        "Sao chép", icon="content_copy",
                        on_click=lambda: ui.run_javascript(
                            f"navigator.clipboard.writeText({token_input.value!r})"
                        ),
                    ).props("outline")
                    ui.button("Đóng", on_click=dialog.close).classes(
                        "bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg"
                    )
        dialog.open()
        await refresh_extension_status()

    async def do_revoke_extension_token():
        try:
            await asyncio.to_thread(api.delete, "/api/doi-chieu-citad/extension-token")
            ui.notify("Đã thu hồi mã kết nối", type="positive")
            await refresh_extension_status()
        except Exception as e:
            if _handle_api_error(e):
                return
            ui.notify(f"Lỗi: {e}", type="negative")

    async def do_download_extension():
        try:
            content = await asyncio.to_thread(api.get_bytes, "/api/doi-chieu-citad/extension-download")
            ui.download(content, "extension_citad.zip")
            ui.notify(
                "Đã tải xong — giải nén rồi vào chrome://extensions, bật Developer mode, "
                "bấm Load unpacked và chọn thư mục vừa giải nén.",
                type="positive", multi_line=True, timeout=8000,
            )
        except Exception as e:
            if _handle_api_error(e):
                return
            ui.notify(f"Lỗi: {e}", type="negative")

    _ACK_STORAGE_KEY = "citad_ext_update_ack"

    async def _get_installed_extension_version() -> str | None:
        """Hỏi Extension đang cài trên máy đang chạy version nào, qua
        chrome.runtime.sendMessage tới GET_VERSION (background.js) — cùng cơ
        chế externally_connectable với _try_auto_connect_extension. Trả về
        None cho MỌI lý do không lấy được (chưa cài, trình duyệt khác, bản
        quá cũ không hiểu message này) — không phân biệt được các trường hợp
        này với nhau nên không thể kết luận "đang dùng bản cũ" một cách chắc
        chắn, phải coi là "không biết" để tránh làm phiền người chưa cài
        Extension bao giờ."""
        js = f"""
            return await new Promise((resolve) => {{
                if (!(window.chrome && chrome.runtime && chrome.runtime.sendMessage)) {{
                    resolve(null);
                    return;
                }}
                try {{
                    chrome.runtime.sendMessage({_EXTENSION_ID!r}, {{type: 'GET_VERSION'}}, (response) => {{
                        if (chrome.runtime.lastError || !response || !response.ok) {{
                            resolve(null);
                        }} else {{
                            resolve(response.version || null);
                        }}
                    }});
                }} catch (e) {{
                    resolve(null);
                }}
            }});
        """
        try:
            return await ui.run_javascript(js, timeout=3.0)
        except Exception:
            return None

    async def _check_extension_update():
        installed = await _get_installed_extension_version()
        if not installed:
            return  # không cài/không rõ — im lặng bỏ qua, không đoán bừa
        try:
            latest = (await asyncio.to_thread(api.get, "/api/doi-chieu-citad/extension-version"))["version"]
        except Exception:
            return
        if installed == latest:
            return
        try:
            acked = await ui.run_javascript(f"return localStorage.getItem({_ACK_STORAGE_KEY!r})", timeout=2.0)
        except Exception:
            acked = None
        if acked == latest:
            return  # đã xác nhận đúng bản mới nhất này rồi — không hiện lại

        # persistent: chặn đóng bằng click ra ngoài/phím Esc — người dùng yêu
        # cầu rõ CHỈ bấm nút "Đã xác nhận" tường minh mới được phép ngừng
        # hiện popup, không có cách đóng thụ động nào khác.
        with ui.dialog().props("persistent") as dialog, ui.card().classes("w-full max-w-lg"):
            ui.label("⚠ Có bản cập nhật mới cho Extension").classes("text-lg font-bold text-orange-600")
            ui.label(
                f"Đang dùng: {installed}  —  Bản mới nhất: {latest}"
            ).classes("text-sm font-bold text-gray-700")
            ui.label(
                "Vào chrome://extensions, gỡ bản Extension cũ, rồi tải lại bản mới bên dưới và "
                "\"Load unpacked\" lại thư mục vừa giải nén."
            ).classes("text-sm text-gray-500")
            with ui.row().classes("w-full justify-end gap-2 mt-3"):
                ui.button(
                    "Tải Extension mới", icon="download", on_click=do_download_extension
                ).props("outline")

                async def _confirm_update():
                    await ui.run_javascript(
                        f"localStorage.setItem({_ACK_STORAGE_KEY!r}, {latest!r})"
                    )
                    dialog.close()

                ui.button("Đã xác nhận", icon="check", on_click=_confirm_update).classes(
                    "bg-orange-600 hover:bg-orange-700 text-white rounded-lg"
                )
        dialog.open()

    with ui.row().classes("w-full"):
        await _sidebar("doi_chieu_citad")
        with _content_area():
            _navy_header(
                "ĐỐI CHIẾU CITAD CUỐI NGÀY",
                "Đối chiếu số liệu CITAD (NHNN) với PaymentHub (Agribank) theo từng ngày",
            )

            with ui.tabs().props(
                "active-color=indigo-600 indicator-color=indigo-600 align=left"
            ).classes("w-full border-b border-gray-200 mb-1") as tabs:
                tab_doi_chieu = ui.tab("Đối chiếu")
                tab_lich_su = ui.tab("Lịch sử")

            with ui.tab_panels(tabs, value=tab_doi_chieu).classes("w-full"):
                with ui.tab_panel(tab_doi_chieu):
                    with _section_card("Kết nối Extension (nạp số liệu tự động từ CITAD/PaymentHub)", icon="extension", accent="indigo"):
                        with ui.row().classes("w-full items-center gap-3 p-2 flex-wrap"):
                            ext_status_label = ui.label("Đang kiểm tra...").classes(
                                "text-xs font-medium px-3 py-1.5 rounded-full bg-gray-100 text-gray-500"
                            )
                            ui.button(
                                "Tải Extension (.zip)", icon="download", on_click=do_download_extension
                            ).props("outline")
                            ui.button(
                                "Tạo mã kết nối mới", icon="vpn_key", on_click=do_create_extension_token
                            ).props("outline")
                            ui.button("Thu hồi", icon="link_off", on_click=do_revoke_extension_token).props(
                                "outline color=red dense"
                            )
                        ui.label(
                            "Lần đầu dùng: (1) Tải Extension → giải nén → chrome://extensions → Developer mode → "
                            "Load unpacked, chọn thư mục vừa giải nén — bước này vẫn phải tự làm 1 lần, Chrome không "
                            "cho web tự cài extension. (2) Bấm \"Tạo mã kết nối mới\" ở trên — nếu Extension đã cài "
                            "trên đúng trình duyệt này, mã sẽ tự động được gửi thẳng vào Extension, không cần dán tay. "
                            "Chỉ khi không tự kết nối được (trình duyệt khác, hoặc Extension chưa cài) mới cần sao "
                            "chép và dán thủ công vào trang Tuỳ chọn của Extension như hướng dẫn hiện ra. Mỗi người tự "
                            "tạo 1 mã riêng, không dùng chung với người khác. Chi tiết trong file README.md nằm sẵn "
                            "trong bản .zip vừa tải."
                        ).classes("text-xs text-gray-500 px-2 -mt-2")
                        ui.timer(0.1, refresh_extension_status, once=True)
                        ui.timer(0.1, _check_extension_update, once=True)

                    with ui.row().classes(
                        "w-full items-end gap-3 flex-wrap mb-2 bg-red-50 rounded-2xl "
                        "border-2 border-red-800 shadow-sm p-4"
                    ):
                        ngay_input = _date_picker_input("Ngày")

                        async def _on_ngay_changed(_e=None):
                            # Đổi ngày (gõ tay hoặc chọn lại lịch) khi đang
                            # tải/sửa 1 bảng (session_id != None) nghĩa là
                            # người dùng muốn chấm SANG NGÀY KHÁC — tách khỏi
                            # bảng cũ NGAY, để lần Lưu tiếp theo tự tạo bảng
                            # MỚI đúng ngày mới, thay vì ăn lỗi "Ngày không
                            # khớp với bảng đang lưu tiếp" mà không biết phải
                            # làm gì tiếp (hành động đổi ngày của họ hoàn
                            # toàn hợp lệ — bug phát hiện khi review 07/09/2026).
                            #
                            # AN TOÀN với apply_session_data() gán lại
                            # ngay_input.value khi "Tải" 1 bảng: NiceGUI gọi
                            # on_value_change ĐỒNG BỘ ngay khi gán .value dù
                            # gán từ code hay từ người dùng (xem
                            # ValueElement._handle_value_change) — nhưng cả
                            # _load_session() lẫn _load_history_entry() đều
                            # gọi _apply_view_mode(..., session_id, ...) NGAY
                            # SAU apply_session_data(), nên giá trị None ở
                            # đây bị ghi đè lại đúng session_id thật ngay sau
                            # đó — chỉ "thắng" khi KHÔNG có bước tải nào theo
                            # sau (đúng lúc người dùng tự đổi ngày).
                            if view_state["session_id"] is not None:
                                view_state["session_id"] = None
                                ui.notify(
                                    "Đã đổi sang ngày khác — lưu tiếp theo sẽ tạo bảng MỚI, "
                                    "không ghi đè bảng vừa tải",
                                    type="info",
                                )
                            await _check_ngay_da_co_bang()

                        ngay_input.on_value_change(_on_ngay_changed)
                        lap_bang_input = ui.select(
                            [], label="Lập bảng", with_input=True, new_value_mode="add-unique"
                        ).props("dense outlined").classes("w-48")
                        kiem_soat_input = ui.select(
                            [], label="Kiểm soát", with_input=True, new_value_mode="add-unique"
                        ).props("dense outlined").classes("w-48")
                        btn_nap_citad = ui.button("Nạp CITAD", icon="cloud_download", on_click=load_citad_buffer).props("outline").classes("rounded-lg")
                        btn_nap_ph = ui.button("Nạp PaymentHub", icon="cloud_download", on_click=load_phub_buffer).props("outline").classes("rounded-lg")
                        btn_luu_tam = ui.button(
                            "Lưu bảng tạm", icon="save", on_click=lambda: do_save_session("draft")
                        ).classes("bg-sky-600 hover:bg-sky-700 text-white rounded-lg")
                        # `.classes("bg-red-600 ...")` KHÔNG đủ — xác nhận thực tế bằng
                        # devtools: NiceGUI/Quasar tự thêm sẵn "bg-primary" cho MỌI
                        # ui.button() không khai color/flat/outline, mà `.bg-primary
                        # { background: var(--q-primary) !important; }` — !important
                        # luôn thắng class Tailwind thường bất kể thứ tự, nên trước đây
                        # nút này (và hoá ra CẢ những nút màu khác cùng kiểu trong
                        # trang, kể cả nút "Xuất Excel" có sẵn từ trước) đều hiện màu
                        # xanh mặc định của Quasar chứ không phải màu Tailwind đã khai.
                        # Dùng prop `color` CỦA QUASAR thay vì Tailwind class — đổi
                        # hẳn class Quasar tự thêm (bg-red thay vì bg-primary) nên
                        # không còn gì để !important đọ nữa.
                        btn_luu_cuoi = ui.button(
                            "Lưu bảng cuối", icon="lock", on_click=lambda: do_save_session("final")
                        ).props("color=red").classes("rounded-lg")
                        btn_xoa = ui.button("Xoá", icon="delete", on_click=do_reset).props("outline color=red").classes("rounded-lg")
                        ui.button("Xuất Excel", icon="grid_on", on_click=do_export).classes(
                            "bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg"
                        )
                    ui.timer(0.1, _load_payment_staff_names, once=True)

                    # Banner NHẮC (không chặn) — "bạn đã có bảng cho ngày
                    # này" khi gõ/chọn ngày mà CHÍNH MÌNH đã có ít nhất 1
                    # bảng (bất kể ai đang xem đúng bảng đó hay đang gõ bảng
                    # mới). Bổ sung sau khi review (07/09/2026): model mới
                    # "không Tải thì luôn tạo bảng mới" khiến F5 giữa chừng
                    # hoặc mở lại hôm sau rồi gõ đúng ngày cũ + nạp + Lưu sẽ
                    # ÂM THẦM đẻ bảng trùng — đường lưu tiếp bảng cũ nằm sâu
                    # 3 lớp trong tab Lịch sử, dễ quên. Chỉ NHẮC, không chặn:
                    # vẫn tạo được bảng mới độc lập nếu không bấm vào banner.
                    ngay_banner_area = ui.column().classes("w-full gap-0")

                    async def _check_ngay_da_co_bang():
                        ngay_banner_area.clear()
                        try:
                            ngay_dt = datetime.datetime.strptime((ngay_input.value or "").strip(), "%d/%m/%Y")
                        except Exception:
                            return  # ngày chưa gõ xong (vd đang gõ dở "08/0") — bỏ qua, không gọi API
                        ngay_str = ngay_dt.strftime("%d/%m/%Y")
                        try:
                            rows = await asyncio.to_thread(
                                api.get, "/api/doi-chieu-citad/reconciliation-days",
                                {"tu_ngay": ngay_str, "den_ngay": ngay_str},
                            )
                        except Exception:
                            return  # chỉ là gợi ý phụ — lỗi mạng thì bỏ qua lặng lẽ, không phải thao tác chính
                        # Lọc đúng CHÍNH MÌNH bằng created_by (id) — KHÔNG lọc qua
                        # `nguoi_cham` (so tên) vì 2 người trùng họ tên sẽ lẫn vào
                        # nhau (đúng lỗi A vừa sửa ở get_reconciliation_days()).
                        mine = [r for r in rows if r.get("created_by") == current_user.get("id")]
                        if not mine:
                            return
                        latest = max(mine, key=lambda r: r.get("updated_at") or "")
                        with ngay_banner_area:
                            with ui.row().classes(
                                "w-full items-center gap-2 px-4 py-2.5 rounded-xl border border-indigo-300 bg-indigo-50 mb-2"
                            ):
                                ui.icon("info", color="indigo-700").classes("text-lg")
                                ui.label(
                                    f"Bạn đã có {len(mine)} bảng cho ngày {ngay_str} — nếu muốn lưu "
                                    "tiếp bảng cũ (thay vì tạo bảng mới), bấm tải bảng gần nhất."
                                ).classes("text-sm text-indigo-800 flex-1")

                                async def _tai_gan_nhat(_e=None, sid=latest["session_id"]):
                                    await _load_session(sid)
                                    tabs.set_value(tab_doi_chieu)

                                ui.button(
                                    "Tải bảng gần nhất", icon="download", on_click=_tai_gan_nhat
                                ).props("dense outline color=indigo-8")

                    ui.timer(0.1, _check_ngay_da_co_bang, once=True)

                    # Banner trạng thái — nội dung dựng ĐỘNG theo mode trong
                    # _apply_view_mode() (rỗng/ẩn khi mode='edit' của chính
                    # mình), thay cho banner tĩnh cố định trước đây.
                    banner_area = ui.column().classes("w-full gap-0")

                    # 3 "Bảng chênh lệch" (Gộp / VNĐ / Ngoại tệ) đặt NGAY ĐẦU (trước
                    # PaymentHub/CITAD/Napas) theo yêu cầu — đây là bảng người dùng
                    # cần nhìn trước tiên khi mở lại 1 ngày đã chấm, không phải cuộn
                    # hết xuống dưới mới thấy. Thêm 2 bảng tách VNĐ/Ngoại tệ (USD+EUR
                    # gộp chung, không tách tiếp) từ 04/09/2026, GIỮ NGUYÊN bảng Gộp
                    # cả 3 loại tiền cũ — xem được cả tổng lẫn lệch nằm ở nhóm tiền
                    # nào cùng lúc, không cần đọc thêm dòng ghi chú "Lệch: <loại
                    # tiền>" bên dưới mới biết. Không ảnh hưởng logic: diff_labels/
                    # _vnd/_fx/lech_cur_label chỉ cần tồn tại TRƯỚC lúc recalc() chạy
                    # (ở cuối), không phụ thuộc thứ tự dựng UI so với các bảng nhập
                    # liệu khác.
                    def _build_diff_card(title: str, labels: dict):
                        with _section_card(title, icon="balance", accent="emerald",
                                           outer_border="border-2 border-red-800"):
                            n_cols = len(FK) + 1
                            n_rows = 4  # 1 dòng tiêu đề + CITAD/PaymentHub/CHÊNH LỆCH

                            with ui.grid(columns=_MONEY_GRID_TEMPLATE).classes("w-full gap-0 p-4"):
                                _group_header_row()
                                ui.label("").classes(
                                    _grid_cell_cls(0, 0, n_rows, n_cols, "text-sm font-bold text-gray-500 text-center")
                                )
                                for col_idx, lbl in enumerate(FK_LBL, start=1):
                                    ui.label(lbl).classes(
                                        _grid_cell_cls(0, col_idx, n_rows, n_cols, "text-sm font-bold text-gray-500 text-center")
                                    )
                                for row_idx, (key, label, color) in enumerate([
                                    ("citad", "CITAD", "text-sky-600"),
                                    ("phub", "PaymentHub", "text-purple-600"),
                                    ("diff", "CHÊNH LỆCH", "text-red-600"),
                                ], start=1):
                                    ui.label(label).classes(
                                        _grid_cell_cls(row_idx, 0, n_rows, n_cols, f"text-sm font-bold self-center {color}")
                                    )
                                    for col_idx, fk in enumerate(FK, start=1):
                                        lbl = ui.label("—").classes(
                                            _grid_cell_cls(row_idx, col_idx, n_rows, n_cols, "text-sm text-right self-center")
                                        )
                                        labels[key][fk] = lbl

                    _build_diff_card("Bảng chênh lệch (CITAD − PaymentHub)", diff_labels)
                    _build_diff_card("Bảng chênh lệch VNĐ (CITAD − PaymentHub)", diff_labels_vnd)
                    _build_diff_card("Bảng chênh lệch Ngoại tệ (CITAD − PaymentHub)", diff_labels_fx)
                    lech_cur_label = ui.label("").classes(
                        "text-sm font-semibold mt-1 mb-2 px-1"
                    )

                    with _section_card("PaymentHub – Agribank", icon="account_balance", accent="blue",
                                       outer_border="border-2 border-red-800"):
                        build_grid(ui.column().classes("w-full"), inputs["phE"], data["phD"], CURS)

                    for cong in CONGS:
                        with _section_card(
                            f"Cổng {cong} – CITAD (NHNN)", icon="swap_horiz", accent=CONG_ACCENT.get(cong, "blue"),
                            outer_border="border-2 border-red-800"
                        ):
                            build_grid(ui.column().classes("w-full"), inputs["gE"][cong], data["gD"][cong], CURS)

                    with _section_card("Napas / PSS - MDP (bổ sung)", icon="add_card", accent="amber",
                                       outer_border="border-2 border-red-800"):
                        build_napas_pssmdp_grid(ui.column().classes("w-full"))

                    recalc()

                with ui.tab_panel(tab_lich_su):
                    ui.label(
                        "1 bản đối chiếu CHUNG cho cả phòng mỗi ngày — ai lưu sau cùng là bản hiện hành. "
                        "Bấm vào 1 ngày để xem từng lần lưu, bấm \"Tải\" trên 1 lần lưu để xem/khôi phục "
                        "đúng số liệu của lần đó."
                    ).classes("text-xs text-gray-500 mb-2")
                    _build_history_panel(deep_link_ngay)

            if deep_link_ngay:
                tabs.set_value(tab_lich_su)
