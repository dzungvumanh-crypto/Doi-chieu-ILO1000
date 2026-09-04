"""Helper dùng chung cho mọi pipeline Đối chiếu Song phương cần dò file theo NGÀY trong 1 thư
mục gốc chứa thư mục con theo ngày (`D.M` hoặc `D.M.YYYY`) và/hoặc file rời ở thư mục gốc.

Tách ra từ `doi_chieu_song_phuong_core/pipeline.py` (2026-08-28) khi thêm service điều phối
`doi_chieu_song_phuong_kenh_core_service.py` — cả 2 nơi cần cùng logic dò thư mục ngày, tránh
reach vào hàm `_private` của gói khác.
"""

import fnmatch
import re
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Iterator

import pandas as pd

_TOAN_CHU_SO = re.compile(r"[0-9]+")


def thu_muc_ngay_ung_vien(goc_dir: Path, ngay: str) -> list[Path]:
    """`ngay` dạng YYYYMMDD -> danh sách thư mục con khả dĩ, dạng `D.M` (VD `23.8`) — đúng quy
    ước dữ liệu 21-25/08. Dữ liệu bộ NH 201/311 (thư mục `TRANG/`) lại đặt tên `D.M.YYYY` (VD
    `24.8.2026`) — thử tên chuẩn trước, rồi glob mọi thư mục con bắt đầu đúng `D.M` để không phải
    thêm 1 hàm biến thể mỗi lần nguồn đổi cách đặt tên (giống cách đã làm cho tên file kênh)."""
    d = datetime.strptime(ngay, "%Y%m%d")
    prefix = f"{d.day}.{d.month}"
    ung_vien = [goc_dir / prefix]
    if goc_dir.exists():
        for sub in sorted(goc_dir.iterdir()):
            if sub.is_dir() and sub.name.startswith(prefix) and sub not in ung_vien:
                ung_vien.append(sub)
    return ung_vien


def cong_ngay(ngay: str, so_ngay: int) -> str:
    d = datetime.strptime(ngay, "%Y%m%d") + timedelta(days=so_ngay)
    return d.strftime("%Y%m%d")


def nhan_offset(off: int) -> str:
    return "T" if off == 0 else f"T{off:+d}"


def tim_file(goc_dir: Path, ngay: str, ten_file: str) -> Path | None:
    """Thử các thư mục ngày khả dĩ trước, rồi thư mục cha (file để rời không có thư mục riêng)."""
    for d in (*thu_muc_ngay_ung_vien(goc_dir, ngay), goc_dir):
        p = d / ten_file
        if p.exists():
            return p
    return None


@contextmanager
def do_thoi_gian(log: Callable[[str], None], nhan: str) -> Iterator[None]:
    """Đo thời gian 1 khối lệnh, ghi qua `log` sẵn có của job — dùng để tìm điểm nghẽn hiệu năng
    bằng số đo thật thay vì đoán (2026-08-30, yêu cầu Business Owner). Chỉ đo, KHÔNG đổi hành vi."""
    t0 = time.perf_counter()
    yield
    log(f"[TIMING] {nhan}: {time.perf_counter() - t0:.1f}s")


def tim_file_glob(goc_dir: Path, ngay: str, pattern: str) -> list[Path]:
    """Như `tim_file`, nhưng khớp `pattern` kiểu glob (VD `202_DEN*.csv`) thay vì tên chính xác —
    dữ liệu thật xuất thủ công thường kèm hậu tố ngày/giờ xuất (VD `202_DEN_20260827_1408.csv`),
    không đúng tên chuẩn module Phân loại dữ liệu xuất ra (`202_DEN.csv`). Dừng ở thư mục ĐẦU
    TIÊN có ít nhất 1 khớp (không gộp khớp từ nhiều thư mục ngày khác nhau); trả rỗng nếu không
    thấy đâu cả."""
    for d in (*thu_muc_ngay_ung_vien(goc_dir, ngay), goc_dir):
        if not d.exists():
            continue
        matches = sorted(d.glob(pattern))
        if matches:
            return matches
    return []


def bao_ve_khoa_so_khoi_excel(s: pd.Series) -> pd.Series:
    """Bọc `="..."` quanh các giá trị TOÀN CHỮ SỐ trước khi ghi CSV chi tiết — phát hiện từ bug
    báo cáo 2026-09-04: khoá SPT (`TXID` phía hub, `MtId/MsgId` phía kênh) là chuỗi 16 chữ số
    thuần, còn khoá SPRT (`MSGREF`, `MtId/MsgId` 34 ký tự) là chữ+số nên Excel tự nhận đúng là
    text. Excel mở CSV trực tiếp tự suy luận cột toàn chữ số là kiểu Số — vượt giới hạn 15 chữ số
    có nghĩa (giới hạn công bố chính thức của Excel) thì làm tròn chữ số cuối về 0, và số 0 đứng
    đầu bị rụng mất. `="..."` buộc Excel hiểu ô là công thức trả về chuỗi, hiển thị đúng nguyên
    văn — không đổi giá trị dòng lệnh mà tool khác (không phải Excel) đọc CSV này.

    Chỉ bọc giá trị KHỚP TOÀN BỘ chuỗi chữ số (`fullmatch`) — giá trị có `-` (VD "GD chuyển
    tiếp") hay bất kỳ ký tự nào khác giữ nguyên, nên không có `=`/`+`/`-`/`@`/dấu nháy kép nào từ
    dữ liệu lọt được vào trong công thức tự tạo — không phát sinh rủi ro command/formula injection
    dù `MtId/MsgId` đến từ file ngân hàng đối tác (nguồn ít tin cậy hơn dữ liệu nội bộ)."""
    la_so = s.str.fullmatch(_TOAN_CHU_SO) == True  # noqa: E712 — NaN == True là False, tránh warning downcast của .fillna
    return s.where(~la_so, '="' + s + '"')


def kiem_tra_du_lieu(ten_file_list: list[str], ngay: str, ma_nh: str) -> dict[str, str]:
    """Dò theo TÊN file (không đọc đĩa/byte) xem đã đủ dữ liệu chạy Tác vụ A (Kênh↔Hub) và
    Tác vụ B (Hub↔Core) chưa — cho banner cảnh báo TRƯỚC khi bấm Chạy (không chặn nút Chạy,
    hệ thống vẫn tự bỏ qua bước thiếu như hành vi hiện có).

    Tái dùng đúng luật dò tên đã áp dụng ở tầng pipeline (`hub_filename_glob`,
    `_tu_khoa_ten_file`, cùng pattern CSV/GL02 của `core/pipeline.py::_tim_file_core_hoac_csv`) —
    không phát minh luật mới, chỉ đổi input từ "thư mục trên đĩa" sang "danh sách tên file" để
    dùng được cả chế độ thư mục server lẫn chế độ tải file lên (chưa upload xong).

    Trả `{"kenh_hub": "du" | "thieu:<mô tả>", "hub_core": "du" | "thieu:<mô tả>"}`."""
    from backend.services.doi_chieu_song_phuong_kenh.load_hub import hub_filename_glob
    from backend.services.doi_chieu_song_phuong_kenh.load_kenh import _tu_khoa_ten_file

    ten_thuong = [t.lower() for t in ten_file_list]
    hub_pattern = hub_filename_glob(ngay, ma_nh).lower()
    co_hub = any(fnmatch.fnmatchcase(t, hub_pattern) for t in ten_thuong)
    co_kenh = any(
        {"kenh", ma_nh.lower()} <= _tu_khoa_ten_file(t) for t in ten_file_list
    )
    core_csv_pattern = f"{ma_nh}_den*.csv".lower()
    gl02_name = f"gl02_{ngay}_1000.zip".lower()
    co_core = any(fnmatch.fnmatchcase(t, core_csv_pattern) for t in ten_thuong) or (gl02_name in ten_thuong)

    if not co_hub:
        thieu_hub = "thieu:file HUB (doichieugd_*.zip)"
        return {"kenh_hub": thieu_hub, "hub_core": thieu_hub}

    ket_qua = {
        "kenh_hub": "du" if co_kenh else "thieu:file kênh (.xlsx do ngân hàng đối tác gửi)",
        "hub_core": "du" if co_core else "thieu:file CORE (CSV đã phân loại sẵn hoặc GL02_*.zip)",
    }
    return ket_qua
