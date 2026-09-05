"""Phân loại KETQUADOICHIEU cho đối chiếu HUB↔CORE **chiều ĐI** — đúng trình tự các bước tài
liệu `Đối chiếu SP chiều đi.docx`, top-down, dừng ở bước đầu tiên khớp được.

⚠️ ĐÍNH CHÍNH PLAN.md mục 6 (đo lại trên dữ liệu thật 2026-09-04, sau khi code xong): nhãn
`"core T hủy T"` **CÓ ca thật**, không thuộc diện "chưa verify" như PLAN xếp. PLAN suy ra sai từ
"không dòng CORE nào có CRAMOUNT = 0" — điều kiện của tài liệu là TỔNG CRAMOUNT của NHÓM = 0, mà
một cặp +X/−X thì mỗi dòng đều khác 0. Chạy thật: NH 201 = 24 cặp (48 dòng), NH 311 = 14 cặp
(28 dòng) — đúng bằng số cặp `TRBRCD & REFERENCE` trùng mà chính PLAN mục 1.4 đã đếm được.

⚠️ NHÃN CHƯA CÓ CA THẬT ĐỂ KIỂM CHỨNG (xem PLAN.md mục 6 — chỉ có test tự dựng, KHÔNG được nói
là "đã verify bằng dữ liệu thật" khi mô tả PR):
- `"lệnh fx"` phía CORE — 511.377/511.378 dòng đều có "API" trong USERID, dòng còn lại là OSB
  (đã bị bước trước bắt).
- `"GD QT vốn"` — 0 dòng REMARK chứa "quyet toan von".
- Cả 6 nhãn hủy chéo ngày — bộ dữ liệu mẫu chỉ có ĐÚNG 1 ngày, không có file T±1/±2/±3 nào.
- `"core T hub Chờ duyệt chi trả"` / `"core T hub TT lệnh lỗi"` — không mẫu HUB thật nào có
  trạng thái WTPA/TPER (thật quan sát được: SCNL/ERPO/CALD/TPAY).

Cả 5 nhóm trên đều nằm ở waterfall **CORE-side** (`classify_core_di`). Waterfall HUB-side
(`classify_hub_di`) không có nhãn nào thuộc diện chưa verify.

⚠️ CẬP NHẬT 2026-09-04 (verify 4 ngày dữ liệu thật 28-31/8, NH 311, đối chiếu chéo với file
"chấm" tay của người soát): HUB `TRANG_THAI_LENH="TPAY"` được người soát coi là khớp bình thường
với CORE, KHÔNG bị loại như ERPO/CALD. `config.py::TRANG_THAI_HUB_DOI_CHIEU` đã đổi thành
`("SCNL", "TPAY")` — mọi chỗ dưới đây ghi "đã lọc SCNL" nay là "đã lọc SCNL+TPAY". Docx không xác
nhận trực tiếp điều này; cần Business Owner xác nhận chính thức.

⚠️ Vị trí WTPA/TPER: Bước 2.17/2.18 = 2 bước ÁP CHÓT của CORE-side, ngay trước "CORE THỪA"
(Bước 2.19) — KHÔNG phải HUB-side. Bản đầu tiên đặt nhầm sang HUB-side, đã tra nguyên văn docx
và chuyển đúng chỗ 2026-09-04.

Tái dùng nguyên `_khop_min_count`/`_phan_loai_chuoi_khoa` của gói chiều đến (khớp theo
`min(count mỗi khoá)`, KHÔNG merge 1-1 ngẫu nhiên) — cùng một cơ chế chống trùng khoá, không
viết lại để 2 chiều khỏi trôi lệch nhau.
"""

from typing import Callable

import pandas as pd

from backend.services.ach.so_tien import doc_so_tien
from backend.services.doi_chieu_song_phuong_core import load_core, load_osb
from backend.services.doi_chieu_song_phuong_core.match import (
    KEY_COL, _khop_min_count, _phan_loai_chuoi_khoa,
)
from backend.services.doi_chieu_song_phuong_kenh.load_hub import (
    build_key_hub_core_di, mask_lenh_fx,
)

from .config import (
    NHAN_CORE_HUY_CHEO_NGAY, NHAN_CORE_HUY_CUNG_NGAY, NHAN_CORE_KHOP_HUB, NHAN_CORE_THUA,
    NHAN_HUB_CHO_DUYET, NHAN_HUB_KHOP_CORE, NHAN_HUB_LENH_LOI, NHAN_HUB_THUA, NHAN_LENH_FX,
    NHAN_QT_OSB, NHAN_QT_VON, OFFSET_CORE_HUY_CHEO_NGAY, OFFSET_CORE_KHI_XU_LY_HUB,
    OFFSET_HUB_KHI_XU_LY_CORE, TRANG_THAI_HUB_CHO_DUYET, TRANG_THAI_HUB_LENH_LOI,
    USERID_API_KEYWORD, USERID_QT_OSB,
)

__all__ = [
    "KEY_COL", "classify_core_di", "classify_hub_di", "build_khoa_huy_cheo_ngay",
    "tim_nhom_lenh_fx_trung_remark",
]

_KHONG_LOG: Callable[[str], None] = lambda msg: None


# ─── Helper riêng chiều đi ────────────────────────────────────────────────────

def _cramount(df: pd.DataFrame) -> pd.Series:
    return doc_so_tien(df["CRAMOUNT"], nguon="core_di", ten_cot="CRAMOUNT")


def mask_huy_cung_ngay_di(df: pd.DataFrame) -> pd.Series:
    """Bước 2.3: nhóm `TRBRCD + REFERENCE` trùng ≥2 dòng VÀ tổng `CRAMOUNT` của nhóm = 0 → cặp
    giao dịch huỷ trong CÙNG ngày. Trả boolean mask.

    Khác `load_core.mask_huy_cung_ngay()` (chiều đến) đúng ở cột tiền: đi dùng CRAMOUNT (ghi có),
    đến dùng DRAMOUNT — dữ liệu thật xác nhận CSV `_DI*.csv` có DRAMOUNT LUÔN = "0" nên xét
    DRAMOUNT ở đây thì nhóm nào cũng "tổng = 0", gán nhãn huỷ cho toàn bộ file."""
    cramount = _cramount(df)
    khoa = df["TRBRCD"].astype(str).str.strip() + "\x00" + df["REFERENCE"].astype(str)
    tong = khoa.map(cramount.groupby(khoa).sum())
    dem = khoa.map(khoa.value_counts())
    return (dem >= 2) & (tong == 0)


def mask_qt_osb_di(df: pd.DataFrame) -> pd.Series:
    """Bước 2.4: `USERID == "1000OSB"`. Chiều đến nhận diện qua REFERENCE, đi qua USERID — bám
    đúng câu chữ docx-đi (dữ liệu thật khớp cả 2 cách, đúng 1 dòng/ngày)."""
    return df["USERID"].fillna("").astype(str).str.strip() == USERID_QT_OSB


def mask_lenh_fx_core(df: pd.DataFrame) -> pd.Series:
    """Bước 2.5: `USERID` KHÔNG chứa chuỗi "API" → lệnh fx. Phải chạy SAU Bước 2.4 (dòng OSB
    cũng không chứa "API" nhưng đã bị bắt trước, xem `classify_core_di`)."""
    return ~df["USERID"].fillna("").astype(str).str.contains(USERID_API_KEYWORD, regex=False)


def tim_nhom_lenh_fx_trung_remark(core_df: pd.DataFrame) -> pd.DataFrame:
    """Lọc các dòng "lệnh fx" (Bước 2.5) có `TRBRCD & REMARK` trùng với ≥1 dòng lệnh fx khác —
    xuất riêng để người soát tự đối chiếu trên hệ thống, KHÔNG để chương trình tự ghép cặp.

    Bối cảnh (quyết định người dùng 2026-09-05): docx chỉ định nghĩa "hủy cùng ngày" theo
    `TRBRCD&REFERENCE` (Bước 2.3) — không có rule ghép cặp theo REMARK. Verify dữ liệu thật tìm
    được 1 ca có thật (2 dòng REFERENCE khác nhau, REMARK giống hệt nhau, CRAMOUNT +X/-X) mà người
    chấm tay coi là 1 cặp huỷ — nhưng cũng tìm được 7 nhóm REMARK "công thức" (chi lương NSNN, trợ
    cấp xã hội...) lặp lại hàng trăm dòng/ngày với nhiều mức tiền trùng cả 2 dấu — nếu để code tự
    ghép cặp theo REMARK+tổng=0 sẽ ghép NHẦM giao dịch không liên quan. Giải pháp: không tự ghép,
    chỉ xuất NGUYÊN VẸN mọi dòng lệnh fx có REMARK trùng lặp để Ly/Trang tự đối chiếu tay.

    Trả DataFrame rỗng (0 dòng, giữ nguyên cột) nếu không có nhóm nào trùng."""
    fx = core_df[core_df["KETQUADOICHIEU"] == NHAN_LENH_FX].copy()
    if fx.empty:
        return fx
    dem = fx.groupby(["TRBRCD", "REMARK"])["TRBRCD"].transform("size")
    trung = fx[dem >= 2].sort_values(["TRBRCD", "REMARK"])
    return trung


def build_khoa_huy_cheo_ngay(df: pd.DataFrame, so_trace: pd.Series) -> pd.Series:
    """Khoá ĐÍCH cho so khớp huỷ chéo ngày (Bước 2.11-2.16): `TRBRCD + SO_TRACE + (−CRAMOUNT)`.

    Mẹo dùng dấu âm thay vì kiểm tổng sau khi ghép cặp: điều kiện docx là "cùng TRBRCD&REFERENCE
    (sau khi đã xử lý file core) VÀ tổng CRAMOUNT hai dòng = 0". Dòng nguồn ngày T mang khoá
    `TRBRCD + SO_TRACE + CRAMOUNT` (chính là `load_core.build_key_di`); dòng đích ngày khác chỉ
    khớp được khi `CRAMOUNT_đích = −CRAMOUNT_nguồn`, tức đúng "tổng = 0". Nhờ vậy dùng lại được
    nguyên `_khop_min_count` (chống trùng khoá, không ghép 1-nhiều) thay vì tự viết vòng lặp
    ghép cặp mới."""
    cramount = _cramount(df)
    return df["TRBRCD"].astype(str).str.strip() + so_trace + (-cramount).astype(str)


def _tra_hub_goc_theo_trang_thai(
    khoa: pd.Series, con_lai: pd.Series, nhan: pd.Series,
    hub_goc: pd.DataFrame | None, trang_thai: str, ten_nhan: str,
) -> None:
    """Bước 2.17/2.18 — 2 bước ÁP CHÓT của waterfall **CORE-side**, ngay trước "CORE THỪA": với
    dòng CORE còn lại chưa phân loại, tra HUB GỐC CHƯA LỌC (bản người dùng tải lên, còn đủ mọi
    `TRANG_THAI_LENH`) xem có dòng HUB cùng khoá mang trạng thái `trang_thai` không.

    Đây chính là lý do phải giữ bản HUB gốc: dòng WTPA/TPER KHÔNG có trong bản đã lọc SCNL, nên
    không có nó thì các dòng CORE này chỉ biết xếp vào "CORE THỪA" mà không nói được vì sao.

    Khoá 2 phía cùng công thức nên so được trực tiếp: CORE dùng `TRBRCD + SO_TRACE + CRAMOUNT`
    (`load_core.build_key_di`), HUB dùng `CHI_NHANH + SE_TRACE(hiệu dụng) + SO_TIEN`
    (`build_key_hub_core_di`) — đúng cặp khoá vẫn dùng ở mọi bước khớp HUB↔CORE khác.

    Dùng `_khop_min_count` chứ không phải `isin()`: 1 dòng WTPA chỉ giải thích được cho ĐÚNG 1
    dòng CORE cùng khoá, không "nhân bản" nhãn ra cả nhóm trùng khoá."""
    if hub_goc is None or not con_lai.any():
        return
    ttl = hub_goc["TRANG_THAI_LENH"].fillna("").astype(str).str.strip()
    con = hub_goc[ttl == trang_thai]
    if not len(con):
        return
    khoa_goc = build_key_hub_core_di(con)
    idx = con_lai[con_lai].index
    mask_khop = _khop_min_count(khoa.loc[idx], khoa_goc)
    idx_khop = mask_khop[mask_khop].index
    # CHƯA verify bằng dữ liệu thật — xem PLAN.md mục 6, chỉ có test tự dựng
    nhan.loc[idx_khop] = ten_nhan
    con_lai.loc[idx_khop] = False


# ─── CORE-side waterfall ──────────────────────────────────────────────────────

def classify_core_di(
    core_df: pd.DataFrame,
    hub_theo_offset: dict[int, pd.DataFrame],
    core_theo_offset: dict[int, pd.DataFrame] | None = None,
    hub_goc: pd.DataFrame | None = None,
) -> pd.Series:
    """Nhãn KETQUADOICHIEU cùng index `core_df` — CORE ngày T, chiều ĐI (Bước 2.2-2.19).

    `hub_theo_offset`: `{offset: hub_df}` — HUB đã lọc `TRANG_THAI_LENH == "SCNL"` và có cột
    `_KEY` (`build_key_hub_core_di`); offset thiếu file thì vắng mặt trong dict.
    `core_theo_offset`: `{offset: core_df}` các ngày KHÁC T (T-3..T-1, T+1..T+3) dùng riêng cho
    nhánh huỷ chéo ngày; mỗi DataFrame chỉ cần các cột CORE gốc (khoá được dựng tại chỗ). Offset
    0 nếu có sẽ bị BỎ QUA (đã xử lý ở Bước 2.3 huỷ cùng ngày).
    `hub_goc`: HUB GỐC ngày T CHƯA lọc SCNL (bản người dùng tải lên) — chỉ dùng cho Bước
    2.17/2.18 (WTPA/TPER). `None` thì 2 bước đó bị bỏ qua, dòng còn lại rơi thẳng vào "CORE THỪA".

    Nhãn chưa verify bằng dữ liệu thật: `"lệnh fx"`, `"GD QT vốn"`, 6 nhãn huỷ chéo ngày,
    `"core T hub Chờ duyệt chi trả"`, `"core T hub TT lệnh lỗi"` — xem docstring module +
    PLAN.md mục 6. (`"core T hủy T"` ĐÃ có ca thật, đính chính PLAN.)
    """
    core_theo_offset = core_theo_offset or {}
    so_trace = load_core.build_so_trace(core_df)
    khoa = load_core.build_key_di(core_df, so_trace)
    nhan = pd.Series("", index=core_df.index)
    con_lai = pd.Series(True, index=core_df.index)

    # ── Bước 2.3 — huỷ cùng ngày ──
    mask_huy = mask_huy_cung_ngay_di(core_df)
    # ĐÃ verify bằng dữ liệu thật 01/09/2026: 48 dòng (24 cặp) NH 201, 28 dòng (14 cặp) NH 311 —
    # đính chính PLAN.md mục 6, xem docstring module.
    nhan.loc[mask_huy] = NHAN_CORE_HUY_CUNG_NGAY
    con_lai.loc[mask_huy] = False

    # ── Bước 2.4 — điện quyết toán OSB ──
    mask_osb = con_lai & mask_qt_osb_di(core_df)
    nhan.loc[mask_osb] = NHAN_QT_OSB
    con_lai.loc[mask_osb] = False

    # ── Bước 2.5 — lệnh fx (USERID không chứa "API") ──
    mask_fx = con_lai & mask_lenh_fx_core(core_df)
    nhan.loc[mask_fx] = NHAN_LENH_FX  # CHƯA verify bằng dữ liệu thật — xem PLAN.md mục 6, chỉ có test tự dựng
    con_lai.loc[mask_fx] = False

    # ── Bước 2.6-2.9 — khớp HUB ngày T, T-1, T-2, T-3 ──
    cac_buoc = []
    for off in OFFSET_HUB_KHI_XU_LY_CORE:
        hub_df = hub_theo_offset.get(off)
        cac_buoc.append((NHAN_CORE_KHOP_HUB[off], hub_df[KEY_COL] if hub_df is not None else None))
    _phan_loai_chuoi_khoa(khoa, con_lai, cac_buoc, nhan)

    # ── Bước 2.11-2.16 — huỷ CHÉO NGÀY (chiều đến không có nhóm này) ──
    cac_buoc_huy = []
    for off in OFFSET_CORE_HUY_CHEO_NGAY:
        core_khac = core_theo_offset.get(off)
        if core_khac is None:
            cac_buoc_huy.append((NHAN_CORE_HUY_CHEO_NGAY[off], None))
            continue
        # "(sau khi đã xử lý file core)" — file ngày khác cũng phải bỏ tiền tố REFERENCE trước
        # khi so, không dùng REFERENCE thô (PLAN.md điểm mơ hồ 4).
        so_trace_khac = load_core.build_so_trace(core_khac)
        cac_buoc_huy.append(
            (NHAN_CORE_HUY_CHEO_NGAY[off], build_khoa_huy_cheo_ngay(core_khac, so_trace_khac))
        )
    # CHƯA verify bằng dữ liệu thật — xem PLAN.md mục 6, chỉ có test tự dựng (6 nhãn huỷ chéo ngày)
    _phan_loai_chuoi_khoa(khoa, con_lai, cac_buoc_huy, nhan)

    # ── Bước 2.10 — quyết toán vốn ──
    mask_von = con_lai & load_core.mask_qt_von(core_df)
    nhan.loc[mask_von] = NHAN_QT_VON  # CHƯA verify bằng dữ liệu thật — xem PLAN.md mục 6, chỉ có test tự dựng
    con_lai.loc[mask_von] = False

    # ── Bước 2.17/2.18 — 2 bước áp chót: tra HUB GỐC chưa lọc, ngay trước "CORE THỪA" ──
    _tra_hub_goc_theo_trang_thai(
        khoa, con_lai, nhan, hub_goc, TRANG_THAI_HUB_CHO_DUYET, NHAN_HUB_CHO_DUYET)
    _tra_hub_goc_theo_trang_thai(
        khoa, con_lai, nhan, hub_goc, TRANG_THAI_HUB_LENH_LOI, NHAN_HUB_LENH_LOI)

    # ── Bước 2.19 ──
    nhan.loc[con_lai] = NHAN_CORE_THUA
    return nhan


# ─── HUB-side waterfall ───────────────────────────────────────────────────────

def _canh_bao_osb_trung_ma_gd(osb_df: pd.DataFrame, log: Callable[[str], None]) -> None:
    """Phát hiện khoá OSB trùng (`build_key_osb_di()` — 4 ký tự đầu `CN thực hiện` + `Mã giao
    dịch` + `Số tiền`, ĐÚNG khoá thật dùng để khớp ở Bước 1.7 V2) và BÁO RÕ, không bao giờ
    `drop_duplicates()` âm thầm (quyết định 2026-09-03 — dữ liệu thật NH 201 có đúng 2 dòng
    trùng).

    ⚠️ Lịch sử 2 lần sửa (2026-09-04):
    1. Bản đầu so trùng trên `Mã giao dịch` ĐƠN LẺ — mã này đánh số theo CHI NHÁNH, không phải
       toàn hệ thống, nên hàng trăm "trùng" chỉ là 2 chi nhánh khác nhau tình cờ cùng số thứ tự
       (verify NH 203, 27/8: 739 mã trùng → còn 35 khi so khoá composite 2 phần).
    2. Đổi sang khoá 2 phần (`build_key_osb()`, không kèm số tiền), còn lại 35 (203)/22 (202) khoá
       trùng — hoá ra đây là các cặp giao dịch gốc+đảo/huỷ (cùng chi nhánh+mã GD, số tiền +X/-X).
       V2 tài liệu thêm `Số tiền` vào khoá (`build_key_osb_di()`) → còn 0 khoá trùng, vì HUB.SO_TIEN
       luôn dương nên chỉ khớp được dòng OSB dương (đúng dòng gốc, đúng ý người chấm thủ công).

    - Trùng nhưng CÙNG `Ngày hạch toán` → lookup ra kết quả như nhau, chỉ log cảnh báo để người
      soát biết OSB có dữ liệu trùng thật.
    - Trùng mà KHÁC `Ngày hạch toán` → nhãn `"OSB & <ngày>"` phụ thuộc thứ tự dòng: liệt kê đúng
      khoá + các giá trị ngày khác nhau, nói thẳng là đang lấy dòng ĐẦU TIÊN, để người soát tự
      quyết định. Không tự chọn rồi im lặng."""
    khoa = load_osb.build_key_osb_di(osb_df)
    ngay = osb_df["Ngày hạch toán"].fillna("").astype(str)
    so_dong = khoa.value_counts()
    trung = so_dong[so_dong >= 2].index
    if not len(trung):
        return

    so_ngay = ngay.groupby(khoa).nunique()
    khac_ngay = [k for k in trung if so_ngay.get(k, 0) > 1]
    cung_ngay = [k for k in trung if so_ngay.get(k, 0) <= 1]

    if cung_ngay:
        log(f"[CẢNH BÁO] OSB có {len(cung_ngay)} khoá (chi nhánh+mã giao dịch) trùng nhưng CÙNG "
            f"Ngày hạch toán (không đổi kết quả đối chiếu): {', '.join(map(str, cung_ngay[:10]))}"
            + (" ..." if len(cung_ngay) > 10 else ""))
    if khac_ngay:
        chi_tiet = "; ".join(
            f"{k} → {sorted(set(ngay[khoa == k]))}" for k in khac_ngay[:10]
        )
        log(f"[CẢNH BÁO] OSB có {len(khac_ngay)} khoá (chi nhánh+mã giao dịch) trùng với Ngày "
            f"hạch toán KHÁC NHAU — nhãn 'OSB & <ngày>' sẽ lấy theo DÒNG ĐẦU TIÊN, kết quả KHÔNG "
            f"chắc chắn, cần người soát kiểm lại: {chi_tiet}" + (" ..." if len(khac_ngay) > 10 else ""))


def _ngay_hach_toan_theo_khoa(osb_df: pd.DataFrame, khoa_osb: pd.Series) -> pd.Series:
    """Lookup `khoá OSB → Ngày hạch toán`, giữ dòng ĐẦU TIÊN. Cảnh báo trùng lặp do
    `_canh_bao_osb_trung_ma_gd()` phát ra trước đó (tách ra để cảnh báo luôn được ghi kể cả khi
    không dòng HUB nào khớp OSB)."""
    return (
        osb_df.assign(**{KEY_COL: khoa_osb})
        .drop_duplicates(KEY_COL)
        .set_index(KEY_COL)["Ngày hạch toán"]
    )


def classify_hub_di(
    hub_df: pd.DataFrame,
    core_theo_offset: dict[int, pd.DataFrame],
    osb_df: pd.DataFrame | None,
    log: Callable[[str], None] = _KHONG_LOG,
) -> pd.Series:
    """Nhãn KETQUADOICHIEU cùng index `hub_df` — HUB ngày T, chiều ĐI (Bước 1.2-1.8).

    `hub_df`: HUB đã lọc `TRANG_THAI_LENH == "SCNL"`, có cột `_KEY` (`build_key_hub_core_di`).
    `core_theo_offset`: `{offset: core_df}` — CORE đã có cột `_KEY` (`load_core.build_key_di`).
    `osb_df`: DataFrame gốc từ `load_osb.load_osb_file` (chưa build khoá), hoặc `None`.

    KHÔNG có bước tra HUB gốc WTPA/TPER ở đây: docx-đi đặt 2 bước đó ở Bước 2.17/2.18 — tức
    waterfall **CORE-side** (`classify_core_di`), ngay trước "CORE THỪA". Waterfall HUB-side kết
    thúc ở "HUB THỪA" (Bước 1.8). Bản đầu tiên viết nhầm sang phía này (2026-09-04), đã tra lại
    nguyên văn tài liệu và chuyển về đúng chỗ — đừng đưa lại vào đây.

    Mọi nhãn HUB-side đều đã có ca thật trên dữ liệu 01/09/2026 (`lệnh fx` phía HUB không có ca
    vì mọi dòng SCNL thật đều có TRACE — dòng thiếu TRACE đúng bằng nhóm ERPO/CALD đã bị lọc)."""
    khoa = hub_df[KEY_COL]
    nhan = pd.Series("", index=hub_df.index)
    con_lai = pd.Series(True, index=hub_df.index)

    # ── Bước 1.2 — lệnh fx (thiếu CẢ TRACE lẫn SE_TRACE) ──
    mask_fx = mask_lenh_fx(hub_df)
    nhan.loc[mask_fx] = NHAN_LENH_FX
    con_lai.loc[mask_fx] = False

    # ── Bước 1.4-1.6 — khớp CORE ngày T, T+1, T+2, T+3 ──
    cac_buoc = []
    for off in OFFSET_CORE_KHI_XU_LY_HUB:
        core_df = core_theo_offset.get(off)
        cac_buoc.append((NHAN_HUB_KHOP_CORE[off], core_df[KEY_COL] if core_df is not None else None))
    _phan_loai_chuoi_khoa(khoa, con_lai, cac_buoc, nhan)

    # ── Bước 1.7 — khớp OSB, nhãn kèm Ngày hạch toán ──
    # Khoá 3 phần (CHI_NHANH/CN4+SE_TRACE/Mã_GD+SO_TIEN, V2 tài liệu 2026-09-04) — xem
    # build_key_hub_osb_di()/build_key_osb_di() giải thích vì sao ghép SO_TIEN tự loại được cặp
    # đảo/huỷ mà không cần rule "ưu tiên số dương" riêng.
    if osb_df is not None:
        # Cảnh báo trùng khoá phát ra NGAY khi đọc được OSB, không nấp trong nhánh "có dòng khớp"
        # — dữ liệu OSB trùng là vấn đề của chính file nguồn, người soát cần biết kể cả hôm nào
        # không dòng HUB nào rơi tới bước này.
        _canh_bao_osb_trung_ma_gd(osb_df, log)
    if osb_df is not None and con_lai.any():
        khoa_osb = load_osb.build_key_osb_di(osb_df)
        khoa_hub_osb = load_osb.build_key_hub_osb_di(hub_df)
        idx = con_lai[con_lai].index
        mask_khop = _khop_min_count(khoa_hub_osb.loc[idx], khoa_osb)
        idx_khop = mask_khop[mask_khop].index
        if len(idx_khop):
            ngay_theo_khoa = _ngay_hach_toan_theo_khoa(osb_df, khoa_osb)
            ngay = khoa_hub_osb.loc[idx_khop].map(ngay_theo_khoa).fillna("")
            nhan.loc[idx_khop] = "OSB & " + ngay
            con_lai.loc[idx_khop] = False

    # ── Bước 1.8 ──
    nhan.loc[con_lai] = NHAN_HUB_THUA
    return nhan
