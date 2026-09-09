"""Orchestrator: đối chiếu HUB↔CORE cho 1 ngân hàng, 1 ngày T.

Dò file HUB (T, T-1, T-2, T-3) và CORE/GL02 (T, T+1, T+2, T+3) trong cả thư mục ngày lẫn thư
mục cha `dữ liệu/` — quyết định 2026-08-26: một số ngày dữ liệu được cung cấp rời (VD
`GL02_20260820_1000.zip` không có thư mục `20.8/`), không di chuyển file, code tự dò cả 2 nơi.

CORE đọc từ CSV đã phân loại sẵn nếu có (`{ma_nh}_DEN.csv`, đúng file thẻ Phân loại dữ liệu xuất
ra), chỉ giải mã lại GL02 zip khi không thấy CSV — quyết định 2026-08-28, giảm số lần phải giải
mã AES ~150-160MB (nguyên nhân MemoryError thật khi chạy nhiều NH liên tiếp, xem Implementation-
notes.html card 91).

HUB offset T: `doi_chieu_hub_core()` chấp nhận `hub_t_override` (2026-08-31, tối ưu hiệu năng) —
tránh đọc+giải nén lại file HUB mà bước Kênh↔Hub (`kenh/pipeline.py::main_from_dir`) đã đọc trước
đó trong cùng job (`doi_chieu_song_phuong_kenh_core_service.py` truyền vào).
"""

from pathlib import Path
from typing import Callable

import pandas as pd

from backend.services import doi_chieu_song_phuong_service as ipcas_svc
from backend.services.doi_chieu_song_phuong_common import (
    cong_ngay, do_thoi_gian, nhan_offset, thu_muc_ngay_ung_vien, tim_file, tim_file_glob,
)
from backend.services.doi_chieu_song_phuong_kenh.load_hub import (
    build_key_hub_core, filter_before_reconcile_core, hub_filename_glob, loai_rjct_hub_core,
    load_hub_zip,
)
from backend.services.doi_chieu_song_phuong_kenh.load_kenh import _tu_khoa_ten_file

from . import load_core, load_osb, match
from .config import NHAN_HUB_T_CORE_T


def _tim_file_hub(
    goc_dir: Path, ngay: str, ma_nh: str, log: Callable[[str], None] = lambda msg: None,
    ngay_goc: str | None = None,
) -> Path | None:
    """Khớp glob `doichieugd_{ngay}__{code}_DEN_9999_N*.zip` — KHÔNG đòi tên chính xác, cùng lý
    do CSV CORE/OSB đã vá (dữ liệu export thủ công có thể kèm hậu tố).

    Nhiều file khớp → KHÔNG tự đoán (đổi 2026-08-30, khác hành vi cũ "lấy file mtime mới nhất") —
    coi như chưa xác định được, trả None kèm log riêng biệt với "không tìm thấy". Lý do: nhiều
    người dùng có thể trỏ chung 1 thư mục server (mode 2) cùng lúc — tự đoán "mới nhất" dễ đọc
    nhầm file người khác vừa thả vào, ra kết quả sai mà không ai biết (chỉ có 1 dòng cảnh báo dễ
    bỏ qua).

    `ngay_goc`: ngày T gốc của cả lần chạy — dò THÊM thư mục ứng viên của ngày này nếu không thấy
    theo `ngay` riêng của offset đang xét (2026-09-08, phát hiện qua phản biện vòng 3 trước PR:
    cùng cơ chế lỗi đã vá cho CSV/ZIP core — người dùng gom file HUB nhiều ngày (T, T-1, T-2, T-3)
    vào 1 thư mục đặt tên theo ngày T thay vì mỗi ngày 1 thư mục riêng. Hậu quả nếu KHÔNG vá: thiếu
    HUB T-1 không chỉ "thiếu dữ liệu" mà làm CORE đáng lẽ khớp "hub T-1 core T" bị rơi xuống gắn
    nhầm nhãn "CORE THỪA" — sai nhãn âm thầm, job vẫn báo "Hoàn thành" bình thường, xem
    `match.py::classify_core` bước khớp `OFFSET_HUB_KHI_XU_LY_CORE`. Tên file HUB tự mang đúng
    ngày giao dịch nên không cần đọc nội dung để xác minh như CSV core — chỉ cần mở rộng thư mục
    tìm kiếm."""
    matches = tim_file_glob(goc_dir, ngay, hub_filename_glob(ngay, ma_nh))
    if not matches and ngay_goc is not None and ngay_goc != ngay:
        matches = tim_file_glob(goc_dir, ngay_goc, hub_filename_glob(ngay, ma_nh))
    if not matches:
        return None
    if len(matches) > 1:
        log(f"[LỖI] {len(matches)} file HUB khớp cùng lúc trong {matches[0].parent} — KHÔNG tự "
            f"chọn (tránh đọc nhầm khi nhiều người dùng chung thư mục): "
            f"{', '.join(p.name for p in matches)}. Cần dọn bớt file trùng hoặc dùng thư mục "
            f"riêng cho mỗi phiên.")
        return None
    return matches[0]


_DUOI_EXCEL_CORE = {".xlsx", ".xls"}


def _doc_trdate_1_file(path: Path, log: Callable[[str], None]) -> str | None:
    """Đọc TRDATE THẬT bên trong 1 file core đã phân loại (CSV hoặc Excel, 2026-09-09) — tên file
    (`{ma_nh}_DEN*.csv`/`.xlsx`) KHÔNG mang ngày giao dịch, chỉ mở đọc nội dung mới biết đúng ngày
    nào. Trả `None` nếu không đọc được (file hỏng/thiếu cột) hoặc TRDATE lẫn nhiều ngày khác nhau
    trong cùng 1 file — không đoán, chỉ log lỗi rồi loại file đó khỏi việc gán offset (không chặn
    cả job). Mirror `doi_chieu_song_phuong_core_di/pipeline.py::_doc_trdate_1_file` — 2 chiều dùng
    chung nguồn GL02 nên cùng 1 luật, không viết lại logic khác nhau."""
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


def _theo_ngay_cac_file_csv(
    files: list[Path], cache: dict[tuple[Path, ...], dict[str, list[Path]]],
    log: Callable[[str], None],
) -> dict[str, list[Path]]:
    """Đọc TRDATE thật của MỌI file trong `files` (đã dò sẵn ở tầng gọi — KHÔNG tự glob lại 1 thư
    mục ở đây, vì `files` có thể đến từ NHIỀU thư mục ứng viên khác nhau gộp lại, xem
    `_tim_file_core_hoac_csv`), trả `{TRDATE: [file,...]}`. Dựng đúng 1 lần/tổ hợp file trong 1
    lần chạy rồi tái dùng cho mọi offset (`cache` truyền từ `doi_chieu_hub_core`, sống theo lần
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


def _tim_file_core_hoac_csv(
    goc_dir: Path, ngay: str, ma_nh: str, off: int, log: Callable[[str], None] = lambda msg: None,
    cache_ngay_csv: dict[tuple[Path, ...], dict[str, list[Path]]] | None = None,
    ngay_goc: str | None = None,
) -> tuple[str, Path] | None:
    """Ưu tiên `{ma_nh}_DEN*.csv` (đã phân loại sẵn, đọc thẳng — không giải mã) — khớp glob,
    KHÔNG đòi tên chính xác `{ma_nh}_DEN.csv`: dữ liệu thật xuất thủ công (ngoài module Phân
    loại dữ liệu) luôn kèm hậu tố ngày/giờ xuất (VD `202_DEN_20260827_1408.csv`, người chấm xác
    nhận 2026-08-28 đây đúng là dữ liệu CORE của ngày trong tên thư mục, không phải ngày trong
    tên file).

    Tên file CSV KHÔNG mang ngày giao dịch. Đúng 1 file khớp VÀ đang hỏi offset 0 (ngày T) thì tin
    luôn — đường nhanh, giữ nguyên hiệu năng cho trường hợp phổ biến nhất (không mở file). Mọi
    trường hợp khác (nhiều file cùng khớp, hoặc đang hỏi offset khác 0) phải MỞ ĐỌC cột TRDATE thật
    bên trong từng file để biết nó đại diện đúng ngày nào rồi mới gán vào đúng offset (2026-09-08) —
    thay hẳn luật cũ "CHỈ dùng CSV cho offset 0" (2026-09-03, chặn cứng vì sợ 1 file để rời khớp
    nhầm cả 4 offset). Luật cũ chặn luôn cả trường hợp hợp lệ: người dùng có sẵn CSV đã phân loại
    cho CẢ ngày T lẫn T+1 (2 đợt xuất trong 1 phiên) — báo lỗi thật của người dùng 2026-09-08, mirror
    đúng lỗi đã sửa ở chiều đi (`doi_chieu_song_phuong_core_di/pipeline.py::_tim_file_core_hoac_csv_di`).

    Vẫn giữ nguyên tắc KHÔNG tự đoán khi mơ hồ: TRDATE lẫn nhiều ngày trong 1 file, hoặc 2 file
    cùng đại diện 1 ngày, đều bị loại + log lỗi rõ ràng, không dùng liều — chỉ khác chỗ "mơ hồ" giờ
    xét trên NGÀY THẬT đọc được, không còn xét trên tên file/vị trí offset.

    CSV đã phân loại sẵn chỉ đại diện cho ĐÚNG 1 ngày/file — muốn có CORE cho offset khác phải có
    ZIP đúng ngày đó, hoặc 1 CSV khác đại diện đúng ngày đó (đọc được qua TRDATE thật). Không thấy
    CSV nào khớp ngày đang hỏi thì mới tới `GL02_{ngay}_1000.zip` (cần giải mã AES + phân loại).
    Trả `(loai, path)`, `loai` là `"csv"`/`"zip"`, hoặc `None` nếu không thấy/không xác định được
    cái nào.

    `ngay_goc`: ngày T gốc của cả lần chạy (bằng `ngay` khi `off == 0`, khác khi `off != 0`) —
    dùng để dò thư mục làm việc chứa CSV, THÊM VÀO chỗ dò theo `ngay` của offset đang xét, KHÔNG
    thay thế. Lý do (phát hiện qua phản biện trước PR, 2026-09-08): `tim_file_glob()` chọn thư mục
    ứng viên theo NGÀY ĐANG HỎI qua `thu_muc_ngay_ung_vien()`; người dùng thường gom mọi CSV của cả
    phiên (nhiều ngày khác nhau) vào 1 thư mục ĐẶT TÊN THEO NGÀY T — nếu chỉ dò theo ngày riêng của
    offset≠0, thư mục `D.M` của ngày đó không tồn tại, `tim_file_glob` rơi thẳng về `goc_dir`
    (KHÔNG đệ quy vào thư mục con `D.M` của ngày T) → không thấy file dù nó đang nằm ngay đó. Dò cả
    2 ngày (gộp, khử trùng) vừa chịu được cách tổ chức "gom vào thư mục ngày T" vừa chịu được cách
    tổ chức "mỗi ngày 1 thư mục riêng" (bên nào tồn tại thì dùng).

    2026-09-09 (yêu cầu Business Owner): file đã phân loại sẵn giờ chấp nhận CẢ `.csv` lẫn
    `.xlsx` — cùng 1 cơ chế TRDATE thật, chỉ khác cách mở file (`load_core.load_core_den_csv()`
    tự dò đuôi). Không có ưu tiên .csv hơn .xlsx hay ngược lại — 2 định dạng bình đẳng, nếu cả 2
    cùng đại diện 1 ngày thì vẫn là "2 file cùng đại diện 1 ngày", chặn như nhau."""
    patterns = [f"{ma_nh}_DEN*.csv", f"{ma_nh}_DEN*.xlsx"]
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
        theo_ngay = _theo_ngay_cac_file_csv(matches, cache, log)
        cac_file = theo_ngay.get(ngay, [])
        if len(cac_file) == 1:
            return ("csv", cac_file[0])
        if len(cac_file) > 1:
            log(f"[LỖI] {len(cac_file)} file cùng đại diện ngày {ngay} theo TRDATE thật "
                f"({', '.join(f.name for f in cac_file)}) — KHÔNG tự chọn, cần dọn bớt file trùng.")

    p = tim_file(goc_dir, ngay, f"GL02_{ngay}_1000.zip")
    if p is None and ngay_goc is not None and ngay_goc != ngay:
        # Cùng lý do CSV ở trên (2026-09-08): GL02 zip của offset≠0 có thể bị gom vào thư mục đặt
        # tên theo ngày T thay vì thư mục riêng đúng ngày của nó — thử thêm thư mục ứng viên của
        # `ngay_goc`, tên file vẫn phải đúng `GL02_{ngay}_1000.zip` (tên tự mang ngày, không đổi).
        p = tim_file(goc_dir, ngay_goc, f"GL02_{ngay}_1000.zip")
    if p is not None:
        return ("zip", p)
    return None


def _tim_file_osb(goc_dir: Path, ngay: str, ma_nh: str) -> Path | None:
    """So khớp từ khoá (`osb` + mã ngân hàng) trong tên file, không phân biệt dấu/hoa-thường —
    dữ liệu thật đã thấy cả `osb {ma_nh}.xlsx` và `osb den {ma_nh} {ngày}.xlsx`/`OSB den ...`.
    Không thấy theo tên thì thử `find_osb_by_ma_dich_vu` (dữ liệu xuất thẳng từ IPCAS tên
    `DULIEUCHITIETHACHTOAN_*.xlsx`, không mang mã NH trong tên file — người chấm báo thiếu
    2026-08-28, xem docstring hàm đó)."""
    can_co = {"osb", ma_nh.lower()}
    for d in (*thu_muc_ngay_ung_vien(goc_dir, ngay), goc_dir):
        if not d.exists():
            continue
        for f in d.glob("*.xlsx"):
            if can_co <= _tu_khoa_ten_file(f.name):
                return f
        found = load_osb.find_osb_by_ma_dich_vu(d, ma_nh)
        if found is not None:
            return found
    return None


def _doc_hub(path: Path, log: Callable[[str], None]) -> pd.DataFrame:
    df = load_hub_zip(path.read_bytes(), log=log)
    df = filter_before_reconcile_core(df, log)
    df[match.KEY_COL] = build_key_hub_core(df)
    return df


def _doc_hub_tu_da_loc(hub_da_loc_base: pd.DataFrame, log: Callable[[str], None]) -> pd.DataFrame:
    """Như `_doc_hub`, nhưng nhận thẳng HUB đã qua `filter_before_reconcile()` từ bước Kênh↔Hub
    (2026-08-31, tối ưu hiệu năng) — chỉ áp thêm lọc RJCT riêng của nhánh core + build khoá, KHÔNG
    đọc lại/giải nén lại file HUB đã đọc trước đó trong cùng job."""
    df = loai_rjct_hub_core(hub_da_loc_base, log)
    df[match.KEY_COL] = build_key_hub_core(df)
    return df


def _doc_core(loai: str, path: Path, ma_nh: str, log: Callable[[str], None]) -> pd.DataFrame:
    """`loai="csv"`: đọc thẳng `{ma_nh}_DEN.csv`/`.xlsx` đã phân loại sẵn — không giải mã (tên
    `loai` giữ "csv" làm nhãn chung cho "đã phân loại sẵn", `load_core_den_csv()` tự dò đuôi thật,
    xem `_tim_file_core_hoac_csv`). `loai="zip"`: giải mã + phân loại GL02 (tái dùng
    `doi_chieu_song_phuong_service.process_zip`, không sửa module phân loại) rồi đọc đúng file
    `{ma_nh}_DEN.csv` vừa sinh ra."""
    if loai == "csv":
        log(f"đọc thẳng file đã phân loại sẵn {path.name} (bỏ qua giải mã GL02)...")
        csv_path = path
    else:
        log(f"đang giải mã + phân loại {path.name}...")
        # 2026-09-01: process_zip() trên develop nhận ĐƯỜNG DẪN file (đọc từ đĩa, không tải cả
        # ZIP GL02 ~150-160MB vào RAM trước) — khác bản trước đây nhận thẳng bytes.
        result = ipcas_svc.process_zip(path, log_callback=log)
        csv_path = ipcas_svc.TEMP_DIR / result["token"] / f"{ma_nh}_DEN.csv"
    df = load_core.load_core_den_csv(csv_path)
    so_trace = load_core.build_so_trace(df)
    df[match.KEY_COL] = load_core.build_key_den(df, so_trace)
    return df


def doi_chieu_hub_core(
    goc_dir: str | Path, ngay: str, ma_nh: str,
    log_callback: Callable[[str], None] | None = None,
    hub_t_override: pd.DataFrame | None = None,
) -> dict:
    """Đối chiếu HUB↔CORE 1 ngân hàng, ngày `ngay` (YYYYMMDD). Trả
    `{"ma_nh", "ngay", "core_df", "hub_df"}` — 2 DataFrame đã gắn cột `KETQUADOICHIEU`.

    `hub_t_override` (2026-08-31, tối ưu hiệu năng): HUB offset T đã đọc+lọc sẵn (qua
    `filter_before_reconcile()`) từ bước Kênh↔Hub (`kenh/pipeline.py::main_from_dir`, khoá
    `hub_theo_nh`) — dùng thẳng thay vì đọc+giải nén lại cùng file HUB lần thứ 2-3 trong job. `None`
    giữ nguyên hành vi cũ (tự dò + đọc file), dùng cho caller độc lập/test hiện có.

    Raise `ValueError` nếu thiếu file bắt buộc (HUB T, CORE T)."""
    log = log_callback or (lambda msg: None)
    goc_dir = Path(goc_dir)

    hub_theo_offset: dict[int, pd.DataFrame] = {}
    for off in (0, -1, -2, -3):
        nhan = nhan_offset(off)
        if off == 0 and hub_t_override is not None:
            log(f"[HUB {nhan}] dùng lại HUB đã đọc từ bước Kênh↔Hub (bỏ qua đọc lại từ đĩa).")
            with do_thoi_gian(log, f"đọc+parse HUB {nhan} (tái dùng, chỉ lọc RJCT)"):
                hub_theo_offset[off] = _doc_hub_tu_da_loc(hub_t_override, lambda m, nhan=nhan: log(f"[HUB {nhan}] {m}"))
            continue
        p = _tim_file_hub(
            goc_dir, cong_ngay(ngay, off), ma_nh, lambda m, nhan=nhan: log(f"[HUB {nhan}] {m}"),
            ngay_goc=ngay,
        )
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
            hub_theo_offset[off] = _doc_hub(p, log)

    if 0 not in hub_theo_offset:
        raise ValueError(f"Không tìm thấy file HUB ngày {ngay} cho NH {ma_nh} — không thể đối chiếu.")

    core_theo_offset: dict[int, pd.DataFrame] = {}
    # Cache TRDATE→file (2026-09-08) khoá theo TỔ HỢP file gộp được ở mỗi offset (xem
    # `_theo_ngay_cac_file_csv`) — tiết kiệm khi nhiều offset cùng gộp ra ĐÚNG 1 tổ hợp giống nhau
    # (ca phổ biến: mọi file nằm chung 1 thư mục phẳng). KHÔNG đảm bảo tuyệt đối "mỗi file chỉ đọc
    # 1 lần" — nếu `ngay`/`ngay_goc` trỏ tới các thư mục ứng viên KHÁC NHAU theo từng offset, tổ
    # hợp gộp được có thể lớn dần qua từng offset, khiến cache-key đổi và một vài file bị đọc lại
    # (đã xác nhận qua phản biện 2026-09-09: kịch bản 2 file ở 2 thư mục ngày riêng biệt đọc lại 1
    # file, thay vì tối ưu tuyệt đối). Không sai kết quả, chỉ chưa tối ưu hết mức lời chú thích cũ
    # từng ngụ ý — sửa lại nếu sau này cần tối ưu triệt để hơn (khoá cache theo từng file riêng lẻ).
    cache_ngay_csv: dict[tuple[Path, ...], dict[str, list[Path]]] = {}
    for off in (0, 1, 2, 3):
        nhan = nhan_offset(off)
        found = _tim_file_core_hoac_csv(
            goc_dir, cong_ngay(ngay, off), ma_nh, off,
            lambda m, nhan=nhan: log(f"[CORE {nhan}] {m}"),
            cache_ngay_csv=cache_ngay_csv, ngay_goc=ngay,
        )
        if found is None:
            # 2026-09-03: T+1 gắn nhãn BẮT BUỘC (config.py — tài liệu không ghi "nếu có") nhưng
            # chỉ T mới raise. Nói thẳng hệ quả thay vì để 1 chữ BẮT BUỘC trần rồi job vẫn báo
            # hoàn thành — người chấm không đọc ra được là kết quả đã thiếu hay đủ.
            if off == 0:
                nhac = " — BẮT BUỘC"
            elif off == 1:
                nhac = (" — BẮT BUỘC nhưng KHÔNG chặn: giao dịch HUB hôm nay mà CORE hạch toán "
                        "sang ngày mai sẽ bị xếp thành 'HUB THỪA'. Cần nạp thêm GL02 zip ngày "
                        "T+1 (CSV đã phân loại sẵn chỉ đại diện đúng ngày T).")
            else:
                nhac = " (bỏ qua)"
            log(f"[CORE {nhan}] không tìm thấy file CSV/GL02" + nhac)
            continue
        loai, p = found
        with do_thoi_gian(log, f"đọc/giải mã CORE {nhan} ({loai})"):
            core_theo_offset[off] = _doc_core(loai, p, ma_nh, lambda m, nhan=nhan: log(f"[CORE {nhan}] {m}"))

    if 0 not in core_theo_offset:
        raise ValueError(f"Không tìm thấy file CSV/GL02 ngày {ngay} — không thể đối chiếu.")

    osb_path = _tim_file_osb(goc_dir, ngay, ma_nh)
    osb_df = None
    if osb_path is not None:
        log(f"[OSB] đang đọc {osb_path.name}...")
        with do_thoi_gian(log, "đọc OSB"):
            osb_df = load_osb.load_osb_file(osb_path)
    else:
        log("[OSB] không tìm thấy file — bỏ qua Bước 2.6 (HUB thừa sẽ không đối chiếu OSB).")

    log("Đang phân loại CORE...")
    core_df = core_theo_offset[0].copy()
    with do_thoi_gian(log, "phân loại CORE (classify_core)"):
        core_df["KETQUADOICHIEU"] = match.classify_core(core_df, hub_theo_offset)

    log("Đang phân loại HUB...")
    hub_df = hub_theo_offset[0].copy()
    with do_thoi_gian(log, "phân loại HUB (classify_hub)"):
        hub_df["KETQUADOICHIEU"] = match.classify_hub(hub_df, core_theo_offset, osb_df)

    n_core_khop = int((core_df["KETQUADOICHIEU"] == NHAN_HUB_T_CORE_T).sum())
    n_hub_khop = int((hub_df["KETQUADOICHIEU"] == NHAN_HUB_T_CORE_T).sum())
    if n_core_khop != n_hub_khop:
        log(f"[CẢNH BÁO] Bất biến vỡ: core khớp '{NHAN_HUB_T_CORE_T}' = {n_core_khop:,} dòng, "
            f"hub khớp '{NHAN_HUB_T_CORE_T}' = {n_hub_khop:,} dòng — không bằng nhau.")

    log(f"Hoàn thành NH {ma_nh} ngày {ngay}: core {len(core_df):,} dòng, hub {len(hub_df):,} dòng, "
        f"khớp '{NHAN_HUB_T_CORE_T}' = {n_core_khop:,} dòng.")

    return {"ma_nh": ma_nh, "ngay": ngay, "core_df": core_df, "hub_df": hub_df}
