"""Cấu hình module Đối chiếu Song phương — Hub ↔ Core (chiều ĐI).

Nguồn: tài liệu `Đối chiếu SP chiều đi.docx` (bản chi tiết nhất, Business Owner cung cấp
2026-09-03) + khảo sát dữ liệu thật NH 201/311 ngày 01-02/09/2026 (xem PLAN.md chiều đi).

Vì sao tách gói riêng thay vì thêm tham số `chieu` vào `doi_chieu_song_phuong_core/`:
thuật toán khác nhau ở gần như mọi bước — CORE dùng CRAMOUNT thay DRAMOUNT, phân loại theo
`USERID` thay `REFERENCE`, có thêm 6 nhãn "hủy chéo ngày" (đến chỉ có 1 nhãn hủy cùng ngày),
có nhánh "lệnh fx" ở CẢ 2 phía, và HUB không lọc `-`/RJCT mà lọc theo `TRANG_THAI_LENH == SCNL`.
Nhồi cả 2 luật vào 1 gói sẽ thành rừng `if chieu == ...`; gói "đến" đã duyệt PR#70, không đụng.

⚠️ Nhiều nhãn dưới đây CHƯA có ca thật nào để kiểm chứng — xem PLAN.md mục 6 và các comment
`# CHƯA verify bằng dữ liệu thật` tại đúng chỗ gán nhãn trong `match.py`.
"""

# ─── Cột CORE bắt buộc (output `{ma_nh}_DI*.csv` của doi_chieu_song_phuong_service) ────
# Khác `doi_chieu_song_phuong_core/config.py::CORE_REQUIRED_COLS`: thêm `USERID` — chiều đi
# phân loại "GD QT OSB" và "lệnh fx" theo USERID (Bước 2.4/2.5), chiều đến không dùng cột này.
CORE_REQUIRED_COLS_DI = {"TRBRCD", "USERID", "REFERENCE", "REMARK", "DRAMOUNT", "CRAMOUNT"}

# ─── Phạm vi HUB đưa vào Hub↔Core (Bước 1.1) ──────────────────────────────────
# Đúng nguyên văn docx: chỉ "SCNL". ERPO/CALD/TPAY đều bị loại, không vào waterfall.
#
# Lịch sử: bản trước (2026-09-04) từng thêm "TPAY" dựa trên verify chéo 4 ngày dữ liệu thật
# (28-31/8/2026, NH 311) — số dòng TPAY mỗi ngày khớp đúng số dòng người soát coi là khớp mà code
# báo "CORE THỪA". Tự nhận khi đó: "Docx không xác nhận trực tiếp — cần Business Owner xác nhận
# chính thức". Đã hỏi — **Business Owner KHẲNG ĐỊNH TPAY KHÔNG nằm trong phạm vi SCNL** (chốt
# 2026-09-06/07, xem `docs/Implementation-notes.html` card 120/121) — quyết định nghiệp vụ, đứng
# trên bằng chứng tương quan dữ liệu quan sát được trước đó. Đã bỏ "TPAY" theo đúng quyết định này.
TRANG_THAI_HUB_DOI_CHIEU = ("SCNL",)

# ─── 2 trạng thái tra ngược trên HUB GỐC CHƯA LỌC (Bước 2.17/2.18) ────────────
# Bản đã lọc SCNL không còn 2 trạng thái này — bắt buộc giữ thêm bản HUB gốc để tra.
TRANG_THAI_HUB_CHO_DUYET = "WTPA"
TRANG_THAI_HUB_LENH_LOI = "TPER"

# ─── Phân loại CORE theo USERID (Bước 2.4/2.5) ────────────────────────────────
# Chiều ĐẾN nhận diện điện quyết toán OSB qua `REFERENCE == "1000OSB"`; chiều ĐI docx nói rõ
# qua `USERID`. Dữ liệu thật khớp cả 2 cách (đúng 1 dòng, `REFERENCE` lẫn `USERID` đều "1000OSB")
# nhưng ở đây bám đúng câu chữ docx-đi.
USERID_QT_OSB = "1000OSB"
USERID_API_KEYWORD = "API"  # USERID KHÔNG chứa chuỗi này → "lệnh fx"

# ─── Bước 2.19 — quyết toán vốn ───────────────────────────────────────────────
# KHÔNG khai báo lại `QT_VON_TRBRCD`/`QT_VON_REMARK_KEYWORD` ở đây: luật giống HỆT chiều đến
# ("TRBRCD == 1000" + REMARK chứa "quyet toan von", không phân biệt hoa/thường), `match.py` gọi
# thẳng `doi_chieu_song_phuong_core/load_core.py::mask_qt_von`. Cùng một khái niệm nghiệp vụ →
# một chỗ định nghĩa, để BO đổi từ khoá là cả 2 chiều đổi theo, không lệch âm thầm.

# ─── Nhãn KETQUADOICHIEU ──────────────────────────────────────────────────────
NHAN_LENH_FX = "lệnh fx"
NHAN_QT_OSB = "GD QT OSB"
NHAN_QT_VON = "GD QT vốn"
NHAN_CORE_THUA = "CORE THỪA"
NHAN_HUB_THUA = "HUB THỪA"
NHAN_HUB_T_CORE_T = "hub T core T"
NHAN_CORE_HUY_CUNG_NGAY = "core T hủy T"
NHAN_HUB_CHO_DUYET = "core T hub Chờ duyệt chi trả"
NHAN_HUB_LENH_LOI = "core T hub TT lệnh lỗi"

# Core T khớp lùi HUB (Bước 2.6-2.9): core T so hub T, T-1, T-2, T-3 — offset theo HUB.
NHAN_CORE_KHOP_HUB = {
    0: NHAN_HUB_T_CORE_T,
    -1: "hub T-1 core T",
    -2: "hub T-2 core T",
    -3: "hub T-3 core T",
}
# HUB T khớp tới CORE (Bước 1.4-1.6): hub T so core T, T+1, T+2, T+3 — offset theo CORE.
NHAN_HUB_KHOP_CORE = {
    0: NHAN_HUB_T_CORE_T,
    1: "hub T core T+1",
    2: "hub T core T+2",
    3: "hub T core T+3",
}
# Hủy CHÉO NGÀY (Bước 2.11-2.16) — CHIỀU ĐẾN KHÔNG CÓ NHÓM NÀY.
# Nhãn đọc theo hướng "dòng nào hủy dòng nào": offset âm = dòng CORE ngày trước bị dòng ngày T
# hủy; offset dương = dòng CORE ngày T bị dòng ngày sau hủy. Nhãn luôn gán cho dòng của NGÀY T
# (file kết quả chỉ xuất CORE ngày T).
NHAN_CORE_HUY_CHEO_NGAY = {
    -1: "core T-1 hủy T",
    -2: "core T-2 hủy T",
    -3: "core T-3 hủy T",
    1: "core T hủy T+1",
    2: "core T hủy T+2",
    3: "core T hủy T+3",
}

# ─── Cửa sổ ngày ──────────────────────────────────────────────────────────────
# Giống chiều đến ở 2 hướng đầu; RIÊNG `OFFSET_CORE_HUY_CHEO_NGAY` là của chiều đi — kéo theo
# yêu cầu tải CORE ở CẢ T-3..T-1 (đến chỉ cần T..T+3), tổng 7 ngày CORE cho 1 lần chạy.
OFFSET_HUB_KHI_XU_LY_CORE = (0, -1, -2, -3)
OFFSET_CORE_KHI_XU_LY_HUB = (0, 1, 2, 3)
OFFSET_CORE_HUY_CHEO_NGAY = (-1, -2, -3, 1, 2, 3)
# Toàn bộ offset CORE cần đọc từ đĩa = hợp của 2 nhóm trên (T chỉ đọc 1 lần).
OFFSET_CORE_CAN_DOC = (-3, -2, -1, 0, 1, 2, 3)
