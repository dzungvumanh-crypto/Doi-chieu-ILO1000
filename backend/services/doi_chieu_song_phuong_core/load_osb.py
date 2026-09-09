"""Đọc file OSB (`osb {ma_nh}.xlsx`) — dữ liệu hạch toán chi tiết kênh OSB, dùng làm nguồn đối
chiếu cuối cùng cho các dòng HUB còn thừa sau khi so hết với CORE (Bước 2.6).

Cấu trúc thật (verify 21.8): 2 sheet — `Config` (bảng mã loại chi nhánh, không dùng) và
`Sheet 1` (dữ liệu thật, header nằm ở dòng thứ 3 → `header=2`).
"""

from pathlib import Path
from typing import BinaryIO

import pandas as pd

from backend.services.ach.so_tien import doc_so_tien
from backend.services.doi_chieu_song_phuong_kenh.load_hub import se_trace_hieu_dung

_REQUIRED_COLS = {"CN thực hiện", "Mã giao dịch", "Ngày hạch toán"}


def load_osb_file(source: str | Path | BinaryIO) -> pd.DataFrame:
    """Raise `ValueError` (KHÔNG tự đoán/tự sửa cấu trúc file) nếu file không đúng khuôn — quyết
    định của Business Owner (2026-09-06/07): file OSB sai định dạng phải CHẶN ĐỨNG quá trình đối
    chiếu và yêu cầu người cung cấp OSB xuất lại đúng khuôn, chương trình không được tự khắc phục
    (ví dụ tự dò lại dòng header) để tránh đọc nhầm mà không ai biết."""
    df = pd.read_excel(source, sheet_name="Sheet 1", dtype=str, header=2, engine="calamine")
    missing = _REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(
            f"File OSB sai định dạng, KHÔNG đối chiếu tiếp được — thiếu cột bắt buộc: "
            f"{', '.join(sorted(missing))}. Nguyên nhân thường gặp: file thiếu 2 dòng tiêu đề đầu "
            f"('DỮ LIỆU CHI TIẾT HẠCH TOÁN' + 1 dòng trống) nên dữ liệu bị lệch lên, khiến chương "
            f"trình đọc nhầm dòng tiêu đề thật. CẦN YÊU CẦU người cung cấp OSB xuất lại file đúng "
            f"khuôn chuẩn (tiêu đề ở dòng 1, dòng 2 để trống, tên cột ở dòng 3) rồi chạy lại — "
            f"KHÔNG tự đoán/tự sửa cấu trúc file này.")
    return df


def find_osb_by_ma_dich_vu(input_dir: str | Path, ma_nh: str) -> Path | None:
    """Dò file OSB không đúng tên chuẩn `osb {ma_nh}.xlsx`/`osb den {ma_nh} {ngày}.xlsx` — dữ
    liệu thật ngày 26/8 xuất thẳng từ IPCAS tên `DULIEUCHITIETHACHTOAN_*.xlsx` (không mang mã NH
    trong tên file, nhưng đúng sheet `Sheet 1`/header dòng 3/tiêu đề "DỮ LIỆU CHI TIẾT HẠCH TOÁN"
    — cùng 1 nguồn OSB, người chấm xác nhận 2026-08-28 chưa được map do đổi tên).

    Định tuyến đúng ngân hàng qua cột `Mã dịch vụ` = `BPO{ma_nh}` — verify 100% đồng nhất trong
    1 file (26/8: 8.493/8.493 dòng NH 202, 12.308/12.308 dòng NH 203, không trộn lẫn 2 NH/file).
    Trả `None` nếu không có file `DULIEUCHITIETHACHTOAN*.xlsx` nào, hoặc không file nào khớp mã
    dịch vụ của `ma_nh`."""
    ma_dich_vu = f"BPO{ma_nh}"
    for f in Path(input_dir).glob("DULIEUCHITIETHACHTOAN*.xlsx"):
        try:
            mau = pd.read_excel(
                f, sheet_name="Sheet 1", dtype=str, header=2,
                usecols=["Mã dịch vụ"], nrows=20, engine="calamine",
            )
        except (ValueError, KeyError):
            continue
        if set(mau["Mã dịch vụ"].dropna().unique()) == {ma_dich_vu}:
            return f
    return None


def build_key_osb(df: pd.DataFrame) -> pd.Series:
    """Khoá = 4 ký tự đầu `CN thực hiện` + `Mã giao dịch` — verify dữ liệu thật 21.8 (NH 202):
    khớp RAW 100% (8.117/8.117) với `CHI_NHANH+TRACE` hub, KHÔNG cần lstrip('0') (khác khoá
    core↔hub)."""
    cn4 = df["CN thực hiện"].fillna("").str[:4]
    ma_gd = df["Mã giao dịch"].fillna("")
    return cn4 + ma_gd


def build_key_hub_osb(hub_df: pd.DataFrame) -> pd.Series:
    """Khoá HUB dùng riêng để đối chiếu với OSB (Bước 2.6): `CHI_NHANH + TRACE` nguyên bản,
    KHÔNG lstrip('0'), KHÔNG kèm số tiền — khác hẳn `build_key_hub_core` (dùng cho khớp CORE,
    có lstrip('0') + kèm SO_TIEN). Verify dữ liệu thật: khớp raw 100% (8.117/8.117, NH 202 21.8)."""
    return hub_df["CHI_NHANH"].astype(str).str.strip() + hub_df["TRACE"].fillna("").str.strip()


def build_key_hub_osb_di(hub_df: pd.DataFrame) -> pd.Series:
    """Khoá HUB↔OSB chiều ĐI (Bước 1.7 `Đối chiếu SP chiều đi V2.docx`): `CHI_NHANH +
    SE_TRACE(hiệu dụng) + SO_TIEN`, KHÔNG lstrip('0').

    ⚠️ 2026-09-04 — V2 tài liệu THÊM `SO_TIEN` vào khoá (V1 chỉ có CHI_NHANH+SE_TRACE) — người
    chấm thủ công (Hương Ly) xác nhận trực tiếp qua trao đổi + văn bản viết lại. Lý do nghiệp vụ:
    OSB có cặp giao dịch gốc+đảo/huỷ cùng chi nhánh+mã giao dịch nhưng khác dấu số tiền (VD
    "159.000" ngày gốc, "-159.000" ngày đảo) — HUB.SO_TIEN LUÔN DƯƠNG (verify 100% dữ liệu thật,
    0 dòng âm ở cả NH 202/203) nên khi ghép SO_TIEN vào khoá, chỉ dòng OSB có "Số tiền" DƯƠNG mới
    khớp được — tự động chọn đúng dòng gốc mà không cần rule đặc biệt "ưu tiên số dương" (đúng ý
    Hương Ly trả lời trực tiếp: "lấy giao dịch có số tiền dương").

    Khác `build_key_hub_osb()` (chiều đến, KHÔNG đổi theo V2 — V2 chỉ sửa tài liệu "đi") ở 2 điểm:
    dùng `se_trace_hieu_dung()` thay TRACE trực tiếp (SE_TRACE nguồn HUB đi luôn rỗng, xem
    docstring cũ), và có thêm SO_TIEN trong khoá."""
    return (
        hub_df["CHI_NHANH"].astype(str).str.strip() + se_trace_hieu_dung(hub_df)
        + doc_so_tien(hub_df["SO_TIEN"], "hub_osb_di", "SO_TIEN").astype(str)
    )


def build_key_osb_di(df: pd.DataFrame) -> pd.Series:
    """Khoá OSB chiều ĐI (Bước 1.7 V2): 4 ký tự đầu `CN thực hiện` + `Mã giao dịch` + `Số tiền`
    (bỏ dấu `.`/`,` ngăn nghìn qua `doc_so_tien()`, GIỮ NGUYÊN dấu `-` nếu có — xem
    `build_key_hub_osb_di()` giải thích đầy đủ). KHÔNG dùng `build_key_osb()` (hàm dùng chung với
    chiều đến, đã verify đúng 2 phần cho đến — V2 chỉ đổi công thức của chiều đi, không đụng
    đến)."""
    cn4 = df["CN thực hiện"].fillna("").str[:4]
    ma_gd = df["Mã giao dịch"].fillna("")
    so_tien = doc_so_tien(df["Số tiền"], "osb_di", "Số tiền").astype(str)
    return cn4 + ma_gd + so_tien
