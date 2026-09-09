"""Đọc & tiền xử lý dữ liệu CORE — output `{ma_nh}_DEN.csv` của
`doi_chieu_song_phuong_service.process_zip()` (module phân loại IPCAS đã có sẵn, không sửa).
"""

from pathlib import Path

import pandas as pd

from backend.services.ach.so_tien import doc_so_tien

from .config import (
    CORE_REQUIRED_COLS, PREFIX_TRACE_CORE, QT_VON_REMARK_KEYWORD, QT_VON_TRBRCD,
    REFERENCE_QT_OSB,
)


_DUOI_EXCEL = {".xlsx", ".xls"}


def load_core_den_csv(path: str | Path) -> pd.DataFrame:
    """Đọc 1 file `{ma_nh}_DEN.csv`/`.xlsx` (đã phân loại sẵn, luôn CRAMOUNT ∈ ZERO_AMOUNTS) —
    tên hàm giữ chữ ".csv" vì dấu vết lịch sử (dùng chung cho cả 2 chiều, xem
    `doi_chieu_song_phuong_core_di/pipeline.py::_doc_core_di`), thật ra đọc được cả Excel
    (2026-09-09, yêu cầu Business Owner: người dùng có thể chỉ có sẵn bản Excel thay vì CSV).

    Excel dùng `engine="calamine"` — đúng quy ước đã kiểm chứng dữ liệu thật của module này
    (`doi_chieu_song_phuong_kenh/load_kenh.py`: `openpyxl` đọc sai/mất dữ liệu âm thầm với file có
    lỗi thẻ `<dimension>`, calamine đọc đúng + nhanh hơn). `dtype=str` giữ nguyên định dạng CỘT
    PANDAS — KHÔNG tự phục hồi được ID dài bị chính Excel làm tròn thành số/ký hiệu khoa học TRƯỚC
    khi python đọc tới (lỗi nằm ở lúc tạo file, không phải lúc đọc — đúng lớp lỗi đã dính thật ở
    khoá SPT nơi khác, PR #75). Chưa kiểm chứng bằng dữ liệu thật rằng schema CORE (TRBRCD 4 số,
    USERID/REFERENCE có tiền tố chữ) miễn nhiễm — chỉ là suy đoán hợp lý (các cột này không phải
    chuỗi số thuần dài như SPT) chưa có ca thật xác nhận. Nếu vẫn dính (VD chi nhánh mới có số 0
    đầu bị Excel bỏ), hậu quả là khoá sai → dòng đó hiện "chưa khớp" trong báo cáo (không phải
    khớp sai lặng lẽ) vì `CORE_REQUIRED_COLS` vẫn đủ, chỉ giá trị bên trong sai — không có lưới
    chặn nào phát hiện RA sớm hơn thế; cần Business Owner biết nếu thấy dòng "CORE THỪA" bất
    thường sau khi đổi sang nộp Excel.

    ⚠ 2026-09-09, phát hiện qua rà soát điểm mù kỹ thuật: đường nhanh của
    `_tim_file_core_hoac_csv_di` (đúng 1 file + offset 0) đưa thẳng file vào đây mà KHÔNG qua
    `_doc_trdate_1_file` (hàm duy nhất có try/except quanh việc đọc file) — 1 file `.xlsx` hỏng/
    giả (đổi đuôi từ file khác, hoặc corrupt) sẽ ném thẳng lỗi gốc của `calamine`/`pandas` (VD
    `CalamineError: Cannot detect file format`) lên tận `job["error"]`, không tên file, không
    tiếng Việt — khác hẳn quy ước mọi lỗi khác của module này. Bọc try/except NGAY TẠI ĐÂY (điểm
    hẹp nhất, mọi đường đọc core đều đi qua) thay vì rải lại ở từng nơi gọi."""
    path = Path(path)
    try:
        if path.suffix.lower() in _DUOI_EXCEL:
            df = pd.read_excel(path, dtype=str, engine="calamine")
        else:
            df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    except Exception as e:
        raise ValueError(f"Không đọc được file core '{path.name}' ({e}) — kiểm tra lại file có "
                          f"đúng định dạng .csv/.xlsx và không bị hỏng.") from e
    missing = CORE_REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"File core thiếu cột bắt buộc: {', '.join(sorted(missing))}")
    return df


def build_so_trace(df: pd.DataFrame) -> pd.Series:
    """Bước 1.2: bỏ tiền tố `1000API` khỏi REFERENCE, giữ phần còn lại, bỏ số 0 đầu (verify dữ
    liệu thật — xem `config.py`). Dòng REFERENCE không có tiền tố này → chuỗi rỗng (không tính
    được SO_TRACE, sẽ không khớp khoá nào — đúng ý, vì đó là loại giao dịch khác, VD `1000OSB`)."""
    ref = df["REFERENCE"].fillna("")
    mask = ref.str.startswith(PREFIX_TRACE_CORE)
    so_trace = pd.Series("", index=df.index)
    so_trace.loc[mask] = ref.loc[mask].str[len(PREFIX_TRACE_CORE):].str.lstrip("0")
    return so_trace


def build_key_den(df: pd.DataFrame, so_trace: pd.Series) -> pd.Series:
    """Bước 1.4: KEY = TRBRCD + SO_TRACE + DRAMOUNT."""
    dramount = doc_so_tien(df["DRAMOUNT"], nguon="core", ten_cot="DRAMOUNT")
    return df["TRBRCD"].astype(str).str.strip() + so_trace + dramount.astype(str)


def build_key_di(df: pd.DataFrame, so_trace: pd.Series) -> pd.Series:
    """Khoá CORE chiều ĐI (docx `Đối chiếu SP chiều đi.docx` Bước 1.3/2.6): KEY = TRBRCD +
    SO_TRACE + CRAMOUNT — khác `build_key_den()` ở chỗ dùng CRAMOUNT (ghi có) thay vì DRAMOUNT
    (ghi nợ). Xác nhận đúng bản chất nghiệp vụ bằng dữ liệu thật: DRAMOUNT của CSV `{ma_nh}_DI*.csv`
    LUÔN LÀ "0" (511.378/511.378 và 878.092/878.092 dòng khảo sát được), CRAMOUNT không bao giờ
    là "0" — đối lập hẳn với CSV `_DEN*.csv` (DRAMOUNT mang tiền, CRAMOUNT luôn 0)."""
    cramount = doc_so_tien(df["CRAMOUNT"], nguon="core_di", ten_cot="CRAMOUNT")
    return df["TRBRCD"].astype(str).str.strip() + so_trace + cramount.astype(str)


def mask_huy_cung_ngay(df: pd.DataFrame) -> pd.Series:
    """Bước 1.3: nhóm TRBRCD+REFERENCE trùng ≥2 dòng, tổng DRAMOUNT = 0 (tập DEN, CRAMOUNT luôn
    ∈ ZERO_AMOUNTS nên chỉ cần xét DRAMOUNT) → giao dịch huỷ cùng ngày. Trả boolean mask."""
    dramount = doc_so_tien(df["DRAMOUNT"], nguon="core", ten_cot="DRAMOUNT")
    khoa = df["TRBRCD"].astype(str).str.strip() + "\x00" + df["REFERENCE"].astype(str)
    tong = khoa.map(dramount.groupby(khoa).sum())
    dem = khoa.map(khoa.value_counts())
    return (dem >= 2) & (tong == 0)


def mask_qt_osb(df: pd.DataFrame) -> pd.Series:
    """Bước 1.8 — điện quyết toán OSB hàng ngày."""
    return df["REFERENCE"].fillna("") == REFERENCE_QT_OSB


def mask_qt_von(df: pd.DataFrame) -> pd.Series:
    """Bước 1.9 — quyết toán vốn."""
    trbrcd_ok = df["TRBRCD"].astype(str).str.strip() == QT_VON_TRBRCD
    remark_ok = df["REMARK"].fillna("").str.lower().str.contains(QT_VON_REMARK_KEYWORD, regex=False)
    return trbrcd_ok & remark_ok
