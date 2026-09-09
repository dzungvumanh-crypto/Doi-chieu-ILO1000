"""Orchestrator: đối chiếu HUB↔CORE **chiều ĐI** cho 1 ngân hàng, 1 ngày T.

Khác orchestrator chiều đến (`doi_chieu_song_phuong_core/pipeline.py`) ở 3 điểm cấu trúc:

1. **Cửa sổ CORE rộng gấp đôi** — đến chỉ đọc CORE T..T+3; đi phải đọc thêm T-3..T-1 để chạy
   nhánh "huỷ chéo ngày" (Bước 2.11-2.16), tổng 7 ngày CORE cho mỗi lần chạy.
2. **Giữ CẢ 2 bản HUB ngày T** — `hub_scnl` (lọc `TRANG_THAI_LENH == "SCNL"`, dùng cho toàn bộ
   waterfall) và `hub_goc` (chưa lọc gì, CHỈ dùng ở Bước 2.17/2.18 tra WTPA/TPER — 2 bước áp
   chót của waterfall CORE-side). Đến không có nhu cầu này nên chỉ giữ 1 bản.
3. **Lọc HUB theo SCNL**, KHÔNG dùng `filter_before_reconcile_core()` của đến (loại `-` trong
   TXID + cặp TXID/TRACE trùng + RJCT) — docx-đi không có bước lọc nào tương ứng, áp nhầm sẽ
   vứt mất giao dịch thật.

Dò file dùng chung helper `doi_chieu_song_phuong_common` như chiều đến (thư mục ngày `D.M` /
`D.M.YYYY` rồi tới thư mục gốc).
"""

from pathlib import Path
from typing import Callable

import pandas as pd

from backend.services import doi_chieu_song_phuong_service as ipcas_svc
from backend.services.doi_chieu_song_phuong_common import (
    cong_ngay, do_thoi_gian, nhan_offset, thu_muc_ngay_ung_vien, tim_file, tim_file_glob,
)
from backend.services.doi_chieu_song_phuong_core import load_core, load_osb
from backend.services.doi_chieu_song_phuong_kenh.load_hub import (
    build_key_hub_core_di, hub_filename_glob, load_hub_zip,
)
from backend.services.doi_chieu_song_phuong_kenh.load_kenh import _tu_khoa_ten_file

from . import match
from .config import (
    CORE_REQUIRED_COLS_DI, NHAN_HUB_T_CORE_T, OFFSET_CORE_CAN_DOC, OFFSET_HUB_KHI_XU_LY_CORE,
    TRANG_THAI_HUB_DOI_CHIEU,
)

CHIEU = "DI"


# ─── Dò file ──────────────────────────────────────────────────────────────────

def _tim_file_hub_di(
    goc_dir: Path, ngay: str, ma_nh: str, log: Callable[[str], None] = lambda msg: None,
    ngay_goc: str | None = None,
) -> Path | None:
    """Khớp glob `doichieugd_{ngay}__{code}_DI_9999_N*.zip`. Nhiều file cùng khớp → KHÔNG tự
    đoán, trả `None` kèm log riêng (giữ đúng quyết định 2026-08-30 của chiều đến: nhiều người
    dùng có thể trỏ chung 1 thư mục, tự chọn "mới nhất" dễ đọc nhầm file người khác vừa thả).

    `ngay_goc`: ngày T gốc của cả lần chạy — dò THÊM thư mục ứng viên của ngày này khi không thấy
    theo ngày riêng của offset đang xét (2026-09-08, mirror đúng fix đã phản biện 4 vòng bên chiều
    đến — `doi_chieu_song_phuong_core/pipeline.py::_tim_file_hub`). Người dùng có thể gom HUB
    nhiều ngày (T, T-1, T-2, T-3) vào 1 thư mục đặt tên theo ngày T; không vá thì HUB T-1 bị mất →
    CORE đáng lẽ khớp "hub T-1 core T" bị gắn NHẦM "CORE THỪA" — sai số liệu âm thầm."""
    matches = tim_file_glob(goc_dir, ngay, hub_filename_glob(ngay, ma_nh, CHIEU))
    if not matches and ngay_goc is not None and ngay_goc != ngay:
        matches = tim_file_glob(goc_dir, ngay_goc, hub_filename_glob(ngay, ma_nh, CHIEU))
    if not matches:
        return None
    if len(matches) > 1:
        log(f"[LỖI] {len(matches)} file HUB khớp cùng lúc trong {matches[0].parent} — KHÔNG tự "
            f"chọn: {', '.join(p.name for p in matches)}. Cần dọn bớt file trùng hoặc dùng thư "
            f"mục riêng cho mỗi phiên.")
        return None
    return matches[0]


_DUOI_EXCEL_CORE = {".xlsx", ".xls"}


def _doc_trdate_1_file(path: Path, log: Callable[[str], None]) -> str | None:
    """Đọc TRDATE THẬT bên trong 1 file core đã phân loại (CSV hoặc Excel, 2026-09-09) — tên file
    (`{ma_nh}_DI*.csv`/`.xlsx`) KHÔNG mang ngày giao dịch, chỉ mở đọc nội dung mới biết đúng ngày
    nào. Trả `None` nếu không đọc được (file hỏng/thiếu cột) hoặc TRDATE lẫn nhiều ngày khác nhau
    trong cùng 1 file — không đoán, chỉ log lỗi rồi loại file đó khỏi việc gán offset (không chặn
    cả job)."""
    try:
        if path.suffix.lower() in _DUOI_EXCEL_CORE:
            col = pd.read_excel(path, dtype=str, engine="calamine",
                                 usecols=["TRDATE"])["TRDATE"].str.strip()
        else:
            col = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig",
                               usecols=["TRDATE"])["TRDATE"].str.strip()
    except Exception as e:
        log(f"[CORE] [LỖI] Không đọc được cột TRDATE của {path.name} ({e}) — bỏ qua file này khi "
            f"dò theo ngày.")
        return None
    uniq = col.unique()
    if len(uniq) != 1:
        log(f"[CORE] [LỖI] {path.name} có TRDATE lẫn {len(uniq)} ngày khác nhau trong cùng 1 "
            f"file — không tự gán được vào offset nào, bỏ qua file này.")
        return None
    return uniq[0]


def _theo_ngay_cac_file_csv_di(
    files: list[Path], cache: dict[tuple[Path, ...], dict[str, list[Path]]],
    log: Callable[[str], None],
) -> dict[str, list[Path]]:
    """Đọc TRDATE thật của MỌI file trong `files` (đã dò sẵn ở tầng gọi — KHÔNG tự glob lại 1 thư
    mục ở đây, vì `files` có thể đến từ NHIỀU thư mục ứng viên khác nhau gộp lại, xem
    `_tim_file_core_hoac_csv_di`), trả `{TRDATE: [file,...]}`. Dựng đúng 1 lần/tổ hợp file trong 1
    lần chạy rồi tái dùng cho mọi offset (`cache` truyền từ `doi_chieu_hub_core_di`, sống theo lần
    gọi — KHÔNG dùng biến module-level để tránh rò rỉ qua nhiều job của tiến trình server chạy
    dài)."""
    key = tuple(files)
    if key in cache:
        return cache[key]
    theo_ngay: dict[str, list[Path]] = {}
    for p in files:
        d = _doc_trdate_1_file(p, log)
        if d is not None:
            theo_ngay.setdefault(d, []).append(p)
    if len(files) > 1:
        log(f"[CORE] {len(files)} file CSV core đã phân loại — đã đọc TRDATE thật để tự gán đúng "
            f"ngày (KHÔNG dựa tên file/thư mục): "
            + ", ".join(f"{d}={[x.name for x in fs]}" for d, fs in sorted(theo_ngay.items())))
    cache[key] = theo_ngay
    return theo_ngay


def _tim_file_core_hoac_csv_di(
    goc_dir: Path, ngay: str, ma_nh: str, off: int, log: Callable[[str], None] = lambda msg: None,
    cache_ngay_csv: dict[tuple[Path, ...], dict[str, list[Path]]] | None = None,
    ngay_goc: str | None = None,
) -> tuple[str, Path] | None:
    """Ưu tiên `{ma_nh}_DI*.csv` (đã phân loại sẵn, đọc thẳng), nếu không có mới tới
    `GL02_{ngay}_1000.zip` (phải giải mã AES + phân loại).

    Tên file CSV KHÔNG mang ngày giao dịch. Đúng 1 file khớp VÀ đang hỏi offset 0 (ngày T) thì tin
    luôn — đường nhanh, giữ nguyên hiệu năng cho trường hợp phổ biến nhất (không mở file). Mọi
    trường hợp khác (nhiều file cùng khớp, hoặc đang hỏi offset khác 0) phải MỞ ĐỌC cột TRDATE thật
    bên trong từng file để biết nó đại diện đúng ngày nào rồi mới gán vào đúng offset — thay hẳn
    luật cũ "CSV chỉ dùng được cho offset 0" (chặn cứng vì sợ 1 file để rời khớp nhầm cả 7 offset,
    xem lịch sử lỗi ở chiều đến báo 2026-09-03). Thực tế vận hành 2026-09-08 cho thấy 1 thư mục có
    thể có SẴN CSV cho cả ngày T lẫn T+1 (2 đợt xuất trong cùng phiên) — luật cũ bỏ phí dữ liệu
    T+1 đã có, phải tự chạy tay ngoài chương trình mới dùng được.

    Vẫn giữ nguyên tắc KHÔNG tự đoán khi mơ hồ: TRDATE lẫn nhiều ngày trong 1 file, hoặc 2 file
    cùng đại diện 1 ngày, đều bị loại + log lỗi rõ ràng, không dùng liều — chỉ khác chỗ "mơ hồ" giờ
    xét trên NGÀY THẬT đọc được, không còn xét trên tên file/vị trí offset.

    `ngay_goc`: ngày T gốc của cả lần chạy — dò THÊM thư mục ứng viên của ngày này (cả cho CSV lẫn
    ZIP fallback) khi không thấy theo ngày riêng của offset đang xét (2026-09-08, mirror đúng fix
    đã phản biện 4 vòng bên chiều đến — `doi_chieu_song_phuong_core/pipeline.py::
    _tim_file_core_hoac_csv`). Người dùng thường gom mọi CSV/ZIP của cả phiên (nhiều ngày) vào 1
    thư mục đặt tên theo ngày T; `tim_file_glob()`/`tim_file()` chỉ dò theo ngày ĐANG HỎI nên
    không tự đệ quy vào thư mục con của ngày T khi đang hỏi offset khác — dò thêm cả 2 ngày mới
    chịu được cách tổ chức này.

    2026-09-09 (yêu cầu Business Owner): file đã phân loại sẵn giờ chấp nhận CẢ `.csv` lẫn
    `.xlsx` — cùng 1 cơ chế TRDATE thật, chỉ khác cách mở file (`load_core.load_core_den_csv()`
    tự dò đuôi). 2 định dạng bình đẳng, không định dạng nào được ưu tiên hơn."""
    patterns = [f"{ma_nh}_{CHIEU}*.csv", f"{ma_nh}_{CHIEU}*.xlsx"]
    cac_ngay_do = {ngay} if ngay_goc is None else {ngay, ngay_goc}
    matches: list[Path] = []
    da_thay: set[Path] = set()
    for nv in cac_ngay_do:
        for pattern in patterns:
            for p in tim_file_glob(goc_dir, nv, pattern):
                if p not in da_thay:
                    da_thay.add(p)
                    matches.append(p)
    matches.sort()
    if len(matches) == 1 and off == 0:
        return ("csv", matches[0])

    if matches:
        cache = cache_ngay_csv if cache_ngay_csv is not None else {}
        theo_ngay = _theo_ngay_cac_file_csv_di(matches, cache, log)
        cac_file = theo_ngay.get(ngay, [])
        if len(cac_file) == 1:
            return ("csv", cac_file[0])
        if len(cac_file) > 1:
            log(f"[CORE] [LỖI] {len(cac_file)} file cùng đại diện ngày {ngay} theo TRDATE thật "
                f"({', '.join(f.name for f in cac_file)}) — KHÔNG tự chọn, cần dọn bớt file trùng.")

    p = tim_file(goc_dir, ngay, f"GL02_{ngay}_1000.zip")
    if p is None and ngay_goc is not None and ngay_goc != ngay:
        p = tim_file(goc_dir, ngay_goc, f"GL02_{ngay}_1000.zip")
    if p is not None:
        return ("zip", p)
    return None


def _tim_file_osb_di(goc_dir: Path, ngay: str, ma_nh: str,
                     log: Callable[[str], None] = lambda msg: None) -> Path | None:
    """So khớp từ khoá (`osb` + mã NH) trong tên file, không phân biệt dấu/hoa-thường — dữ liệu
    thật chiều đi đặt tên `OSB di 201 1.9.xlsx`.

    ƯU TIÊN file có thêm từ khoá `di` trong tên: một thư mục làm việc thường có CẢ file OSB đến
    lẫn đi của cùng ngân hàng (`OSB den 201 ...` / `OSB di 201 ...`); chỉ so `{osb, ma_nh}` như
    chiều đến sẽ chọn phải file nào đứng trước trong thư mục — đọc nhầm nguồn mà không có dấu
    hiệu nào. Không thấy file nào có `di` thì mới lùi về file `osb + ma_nh` bất kỳ (dữ liệu xuất
    thẳng từ IPCAS không mang chiều trong tên), có log nói rõ đang dùng file nào."""
    du_phong: Path | None = None
    for d in (*thu_muc_ngay_ung_vien(goc_dir, ngay), goc_dir):
        if not d.exists():
            continue
        for f in sorted(d.glob("*.xlsx")):
            tu_khoa = _tu_khoa_ten_file(f.name)
            if not {"osb", ma_nh.lower()} <= tu_khoa:
                continue
            if "di" in tu_khoa:
                return f
            if du_phong is None:
                du_phong = f
        found = load_osb.find_osb_by_ma_dich_vu(d, ma_nh)
        if found is not None and du_phong is None:
            du_phong = found
    if du_phong is not None:
        log(f"[OSB] không thấy file nào có từ khoá 'di' trong tên — dùng {du_phong.name} "
            f"(kiểm lại đúng là dữ liệu OSB chiều ĐI trước khi tin kết quả).")
    return du_phong


# ─── Đọc dữ liệu ──────────────────────────────────────────────────────────────

def _loc_scnl(hub_goc: pd.DataFrame, log: Callable[[str], None]) -> pd.DataFrame:
    """Bước 1.1: chỉ giữ `TRANG_THAI_LENH` thuộc `TRANG_THAI_HUB_DOI_CHIEU` (đúng nguyên văn docx:
    chỉ SCNL — xem lịch sử "thêm rồi bỏ TPAY" tại comment `config.py`). ERPO/CALD/TPAY đều bị
    loại, không vào waterfall, không xuất hiện trong file kết quả Hub↔Core."""
    ttl = hub_goc["TRANG_THAI_LENH"].fillna("").astype(str).str.strip()
    giu = ttl.isin(TRANG_THAI_HUB_DOI_CHIEU)
    n_loai = int((~giu).sum())
    if n_loai:
        phan_bo = ttl[~giu].value_counts().to_dict()
        log(f"Loại {n_loai:,} dòng HUB không thuộc {TRANG_THAI_HUB_DOI_CHIEU} (không thuộc phạm "
            f"vi Hub↔Core chiều đi): {phan_bo}")
    return hub_goc[giu].reset_index(drop=True)


def _doc_hub_di(path: Path, log: Callable[[str], None]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Trả `(hub_goc, hub_scnl)` — `hub_goc` CHƯA lọc gì (cần cho Bước 2.17/2.18), `hub_scnl` đã
    lọc SCNL + gắn cột `_KEY`."""
    hub_goc = load_hub_zip(path.read_bytes(), log=log)
    hub_scnl = _loc_scnl(hub_goc, log)
    hub_scnl[match.KEY_COL] = build_key_hub_core_di(hub_scnl)
    return hub_goc, hub_scnl


def _doc_hub_di_tu_goc(hub_goc: pd.DataFrame, log: Callable[[str], None]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Như `_doc_hub_di` nhưng nhận thẳng HUB gốc đã đọc ở bước Kênh↔Hub (`kenh/pipeline.py::
    main_from_dir` trả `hub_theo_nh`, chiều đi KHÔNG lọc gì nên đó đúng là bản gốc) — tránh
    đọc + giải nén lại cùng 1 file HUB lần thứ hai trong cùng job."""
    hub_scnl = _loc_scnl(hub_goc, log)
    hub_scnl[match.KEY_COL] = build_key_hub_core_di(hub_scnl)
    return hub_goc, hub_scnl


def _doc_core_di(loai: str, path: Path, ma_nh: str, log: Callable[[str], None]) -> pd.DataFrame:
    """`loai="csv"`: đọc thẳng `{ma_nh}_DI*.csv` đã phân loại sẵn. `loai="zip"`: giải mã + phân
    loại GL02 (tái dùng `doi_chieu_song_phuong_service.process_zip`) rồi đọc `{ma_nh}_DI.csv`.

    Dùng `load_core.load_core_den_csv()` cho cả 2 chiều (tên hàm mang chữ "den" là dấu vết lịch
    sử — nội dung chỉ là đọc CSV + kiểm cột bắt buộc, không có gì riêng chiều đến), rồi kiểm
    thêm `USERID` — cột chiều đi bắt buộc phải có mà `CORE_REQUIRED_COLS` của đến không đòi."""
    if loai == "csv":
        log(f"đọc thẳng file đã phân loại sẵn {path.name} (bỏ qua giải mã GL02)...")
        csv_path = path
    else:
        log(f"đang giải mã + phân loại {path.name}...")
        result = ipcas_svc.process_zip(path, log_callback=log)
        csv_path = ipcas_svc.TEMP_DIR / result["token"] / f"{ma_nh}_{CHIEU}.csv"
    df = load_core.load_core_den_csv(csv_path)
    missing = CORE_REQUIRED_COLS_DI - set(df.columns)
    if missing:
        raise ValueError(f"File core chiều đi thiếu cột bắt buộc: {', '.join(sorted(missing))}")
    so_trace = load_core.build_so_trace(df)
    df[match.KEY_COL] = load_core.build_key_di(df, so_trace)
    return df


# ─── Orchestrator ─────────────────────────────────────────────────────────────

def doi_chieu_hub_core_di(
    goc_dir: str | Path, ngay: str, ma_nh: str,
    log_callback: Callable[[str], None] | None = None,
    hub_t_override: pd.DataFrame | None = None,
) -> dict:
    """Đối chiếu HUB↔CORE chiều ĐI, 1 ngân hàng, ngày `ngay` (YYYYMMDD).

    Trả `{"ma_nh", "ngay", "core_df", "hub_df"}` — 2 DataFrame đã gắn cột `KETQUADOICHIEU`
    (`hub_df` là bản đã lọc SCNL; bản HUB gốc không xuất ra, chỉ truyền vào `classify_core_di`
    cho Bước 2.17/2.18).

    `hub_t_override`: HUB GỐC ngày T đã đọc sẵn ở bước Kênh↔Hub (chiều đi không lọc gì trước khi
    khớp nên `hub_theo_nh` chính là bản gốc) — dùng thẳng thay vì đọc + giải nén lại.

    Raise `ValueError` nếu thiếu file bắt buộc (HUB T, CORE T)."""
    log = log_callback or (lambda msg: None)
    goc_dir = Path(goc_dir)

    # ── HUB: T, T-1, T-2, T-3 ──
    hub_theo_offset: dict[int, pd.DataFrame] = {}
    hub_goc_t: pd.DataFrame | None = None
    for off in OFFSET_HUB_KHI_XU_LY_CORE:
        nhan = nhan_offset(off)
        log_off = lambda m, nhan=nhan: log(f"[HUB {nhan}] {m}")
        if off == 0 and hub_t_override is not None:
            log(f"[HUB {nhan}] dùng lại HUB đã đọc từ bước Kênh↔Hub (bỏ qua đọc lại từ đĩa).")
            with do_thoi_gian(log, f"lọc SCNL + dựng khoá HUB {nhan} (tái dùng)"):
                hub_goc_t, hub_theo_offset[off] = _doc_hub_di_tu_goc(hub_t_override, log_off)
            continue
        p = _tim_file_hub_di(goc_dir, cong_ngay(ngay, off), ma_nh, log_off, ngay_goc=ngay)
        if p is None:
            if off == 0:
                nhac = " — BẮT BUỘC"
            elif off == -1:
                nhac = (" — BẮT BUỘC nhưng KHÔNG chặn: giao dịch CORE hôm nay đáng lẽ khớp HUB "
                        "hôm qua sẽ bị xếp NHẦM thành 'CORE THỪA' thay vì 'hub T-1 core T'. Cần "
                        "nạp thêm HUB zip ngày T-1.")
            else:
                nhac = " (bỏ qua)"
            log(f"[HUB {nhan}] không tìm thấy file" + nhac)
            continue
        log(f"[HUB {nhan}] đang đọc {p.name}...")
        with do_thoi_gian(log, f"đọc+parse HUB {nhan}"):
            hub_goc, hub_scnl = _doc_hub_di(p, log_off)
        hub_theo_offset[off] = hub_scnl
        if off == 0:
            hub_goc_t = hub_goc

    if 0 not in hub_theo_offset:
        raise ValueError(f"Không tìm thấy file HUB chiều đi ngày {ngay} cho NH {ma_nh} — không "
                         f"thể đối chiếu.")

    # ── CORE: T-3..T+3 (rộng gấp đôi chiều đến — nhánh huỷ chéo ngày cần cả 2 phía) ──
    core_theo_offset: dict[int, pd.DataFrame] = {}
    # Cache TRDATE→file (2026-09-08) dựng 1 lần, dùng lại cho cả 7 offset — tránh mở đọc lại cùng
    # tổ hợp file CSV 7 lần (xem `_theo_ngay_cac_file_csv_di`).
    cache_ngay_csv: dict[tuple[Path, ...], dict[str, list[Path]]] = {}
    for off in OFFSET_CORE_CAN_DOC:
        nhan = nhan_offset(off)
        log_off = lambda m, nhan=nhan: log(f"[CORE {nhan}] {m}")
        found = _tim_file_core_hoac_csv_di(
            goc_dir, cong_ngay(ngay, off), ma_nh, off, log_off,
            cache_ngay_csv=cache_ngay_csv, ngay_goc=ngay)
        if found is None:
            if off == 0:
                nhac = " — BẮT BUỘC"
            elif off == 1:
                nhac = (" — thiếu thì giao dịch HUB hôm nay mà CORE hạch toán sang ngày mai sẽ bị "
                        "xếp thành 'HUB THỪA'. Cần nạp thêm GL02 zip ngày T+1 (CSV đã phân loại "
                        "sẵn chỉ đại diện đúng ngày T).")
            else:
                nhac = " (bỏ qua — nhánh huỷ chéo ngày của offset này không chạy)"
            log(f"[CORE {nhan}] không tìm thấy file CSV/GL02" + nhac)
            continue
        loai, p = found
        with do_thoi_gian(log, f"đọc/giải mã CORE {nhan} ({loai})"):
            core_theo_offset[off] = _doc_core_di(loai, p, ma_nh, log_off)

    if 0 not in core_theo_offset:
        raise ValueError(f"Không tìm thấy file CSV/GL02 chiều đi ngày {ngay} — không thể đối chiếu.")

    # ── OSB ──
    osb_path = _tim_file_osb_di(goc_dir, ngay, ma_nh, log)
    osb_df = None
    if osb_path is not None:
        log(f"[OSB] đang đọc {osb_path.name}...")
        with do_thoi_gian(log, "đọc OSB"):
            osb_df = load_osb.load_osb_file(osb_path)
    else:
        log("[OSB] không tìm thấy file — bỏ qua Bước 1.7 (HUB thừa sẽ không đối chiếu OSB).")

    # ── Phân loại ──
    log("Đang phân loại CORE...")
    core_df = core_theo_offset[0].copy()
    core_khac_ngay = {off: df for off, df in core_theo_offset.items() if off != 0}
    with do_thoi_gian(log, "phân loại CORE (classify_core_di)"):
        core_df["KETQUADOICHIEU"] = match.classify_core_di(
            core_df, hub_theo_offset, core_khac_ngay, hub_goc=hub_goc_t)

    log("Đang phân loại HUB...")
    hub_df = hub_theo_offset[0].copy()
    with do_thoi_gian(log, "phân loại HUB (classify_hub_di)"):
        hub_df["KETQUADOICHIEU"] = match.classify_hub_di(hub_df, core_theo_offset, osb_df, log=log)

    # ── Bất biến docx-đi Bước 2.6: số món khớp "hub T core T" phải bằng nhau 2 phía ──
    n_core_khop = int((core_df["KETQUADOICHIEU"] == NHAN_HUB_T_CORE_T).sum())
    n_hub_khop = int((hub_df["KETQUADOICHIEU"] == NHAN_HUB_T_CORE_T).sum())
    if n_core_khop != n_hub_khop:
        log(f"[CẢNH BÁO] Bất biến vỡ: core khớp '{NHAN_HUB_T_CORE_T}' = {n_core_khop:,} dòng, "
            f"hub khớp '{NHAN_HUB_T_CORE_T}' = {n_hub_khop:,} dòng — không bằng nhau.")

    log(f"Hoàn thành NH {ma_nh} ngày {ngay} (chiều đi): core {len(core_df):,} dòng, hub "
        f"{len(hub_df):,} dòng, khớp '{NHAN_HUB_T_CORE_T}' = {n_core_khop:,} dòng.")

    return {"ma_nh": ma_nh, "ngay": ngay, "core_df": core_df, "hub_df": hub_df}
