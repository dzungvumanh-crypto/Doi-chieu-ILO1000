"""Cấu hình module Đối chiếu Song phương — Hub ↔ Core (chiều ĐẾN).

Nguồn: tài liệu `đối chiếu Song phương.docx` mục "Đối chiếu kênh – core" (nội dung thực chất là
HUB ↔ CORE — tài liệu gọi tên mục hơi lệch, không có bước nào dùng file kênh) + verify dữ liệu
thật 21-25/08/2026 (xem plan `lập kế hoạch update code base` — file plan đã dùng khi code).

Khác 2 module đã có:
- `doi_chieu_song_phuong_service.py` — phân loại IPCAS/GL02 → 8 file `{ma_nh}_{DEN|DI}.csv`
  (module này TÁI DÙNG output, không tự giải mã GL02).
- `doi_chieu_song_phuong_kenh/` — đối chiếu HUB↔KÊNH (module này KHÔNG đụng, chỉ tái dùng
  `load_hub.load_hub_zip`/`filter_before_reconcile`/`hub_filename`).
"""

# ─── Cột CORE bắt buộc (output {ma_nh}_DEN.csv của doi_chieu_song_phuong_service) ─────
# ⚠️ `TRDATE` CỐ Ý không nằm trong tập này — không có gì bảo đảm mọi file đã phân loại sẵn có cột
# này (10 cột chuẩn của doi_chieu_song_phuong_service.py cũng không liệt kê nó). `pipeline.py`
# (`_doc_trdate_1_file`, `_tim_file_core_hoac_csv`) dùng TRDATE khi CÓ để tự xác minh/gán đúng
# ngày cho file offset≠0 và cảnh báo khi offset 0 lệch ngày — nhưng phải tự chịu trường hợp file
# không có cột này (coi là "không xác minh được", không phải lỗi/file hỏng), không được coi TRDATE
# là bắt buộc như 5 cột dưới đây (review PR#81, Khánh, 2026-09-09).
CORE_REQUIRED_COLS = {"TRBRCD", "REFERENCE", "REMARK", "DRAMOUNT", "CRAMOUNT"}

# ─── Trace hạch toán CORE (Bước 1.2) ───────────────────────────────────────────
# Tài liệu: "Cột REFERENCE bỏ các ký tự 1000API, giữ lại phần dữ liệu còn lại".
# ⚠️ Tài liệu KHÔNG nói rõ nhưng dữ liệu thật xác nhận bắt buộc lstrip('0') cả 2 bên (core lẫn
# hub TRACE) mới khớp được — verify 21.8: raw so khớp 0/18.952, sau lstrip('0') 18.029/18.952.
PREFIX_TRACE_CORE = "1000API"

# ─── Bước 1.8 — điện quyết toán OSB hàng ngày (đã xác nhận Business Owner 2026-08-26: mỗi ngày
# thường chỉ 1 điện) ─────────────────────────────────────────────────────────────
REFERENCE_QT_OSB = "1000OSB"

# ─── Bước 1.9 — quyết toán vốn (verify dữ liệu thật 21.8: 3 dòng, TRBRCD=1000, REMARK có cả
# hoa lẫn thường "QUYET TOAN VON"/"Quyet toan von") ─────────────────────────────
QT_VON_TRBRCD = "1000"
QT_VON_REMARK_KEYWORD = "quyet toan von"  # so khớp không phân biệt hoa/thường

# ─── Nhãn KETQUADOICHIEU ────────────────────────────────────────────────────────
NHAN_CORE_HUY = "core T hủy T"
NHAN_QT_OSB = "GD QT OSB"
NHAN_QT_VON = "GD QT vốn"
NHAN_CORE_THUA = "CORE THỪA"
NHAN_HUB_THUA = "HUB THỪA"
NHAN_HUB_T_CORE_T = "hub T core T"

# Core khớp lùi hub (Bước 1.4-1.7): core T so hub T, T-1, T-2, T-3 — offset theo hub.
NHAN_CORE_KHOP_HUB = {
    0: NHAN_HUB_T_CORE_T,
    -1: "hub T-1 core T",
    -2: "hub T-2 core T",
    -3: "hub T-3 core T",
}
# Hub khớp tới core (Bước 2.2-2.5): hub T so core T, T+1, T+2, T+3 — offset theo core.
NHAN_HUB_KHOP_CORE = {
    0: NHAN_HUB_T_CORE_T,
    1: "hub T core T+1",
    2: "hub T core T+2",
    3: "hub T core T+3",
}

# Số ngày tối đa nhìn lùi (hub, khi phân loại CORE) / nhìn tới (core, khi phân loại HUB).
# T-1/T+1 tài liệu không ghi "(nếu có)" — coi là bắt buộc cố xử lý (nhưng code vẫn phải chịu
# được thiếu file, không crash — "nếu có" áp dụng thống nhất cho toàn bộ offset).
OFFSET_HUB_KHI_XU_LY_CORE = (0, -1, -2, -3)
OFFSET_CORE_KHI_XU_LY_HUB = (0, 1, 2, 3)
