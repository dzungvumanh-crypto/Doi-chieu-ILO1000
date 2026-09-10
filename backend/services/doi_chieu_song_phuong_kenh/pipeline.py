"""Orchestrator: đối chiếu 1 ngày cho toàn bộ `RECONCILE_UNITS`.

Ngày được tự nhận diện từ tên file HUB (`doichieugd_YYYYMMDD__NN_{DEN|DI}_9999_N.zip`)
có trong thư mục đầu vào — không dựa vào tên thư mục (không đáng tin, VD `21.8`).

Tham số `chieu` (2026-09-03, thêm hỗ trợ "đi"): thuật toán Kênh↔Hub chiều đi ĐƠN GIẢN HƠN đến —
không lọc "-"/TXID+TRACE trùng trước khi khớp, Bảng 1 chỉ đếm HUB trạng thái SCNL (không phải
"loại trạng thái một-phía" như đến) — xem `process.classify_kenh_hub_di`/`summarize_unit_di` và
`Đối chiếu SP chiều đi.docx`.
"""

import re
import threading
from pathlib import Path
from typing import Callable

from backend.services.doi_chieu_song_phuong_common import do_thoi_gian

from .config import RECONCILE_UNITS
from .load_hub import filter_before_reconcile, hub_filename, load_hub_zip
from .load_kenh import find_kenh_path, kenh_filename, load_kenh_file
from .process import (
    check_unexpected_one_sided, classify_kenh_hub_den, classify_kenh_hub_di,
    dem_lech_tien_tren_khop, match_unit, summarize_unit, summarize_unit_di,
)

_HUB_NAME_RE = {
    "DEN": re.compile(r"doichieugd_(\d{8})__\d{2}_DEN_9999_N\.zip"),
    "DI": re.compile(r"doichieugd_(\d{8})__\d{2}_DI_9999_N\.zip"),
}


def detect_ngay(input_dir: str | Path, chieu: str = "DEN") -> str | None:
    """Tìm ngày (YYYYMMDD) từ tên file HUB đầu tiên khớp mẫu trong thư mục (đúng `chieu`)."""
    pattern = _HUB_NAME_RE[chieu]
    for p in Path(input_dir).iterdir():
        m = pattern.match(p.name)
        if m:
            return m.group(1)
    return None


def main_from_dir(
    input_dir: str | Path,
    ngay: str | None = None,
    ma_nh: str | None = None,
    log_callback: Callable[[str], None] | None = None,
    cancel_event: threading.Event | None = None,
    hub_path_override: Path | None = None,
    chieu: str = "DEN",
) -> dict | None:
    """Đối chiếu 1 ngày, các đơn vị trong `RECONCILE_UNITS`.

    `ma_nh`: lọc chỉ chạy đơn vị của 1 ngân hàng (VD dùng bởi service điều phối
    Kênh↔Hub + Hub↔Core hợp nhất, quyết định 2026-08-28 — mỗi lần chạy 1 NH). Mặc định
    `None` giữ nguyên hành vi cũ — chạy toàn bộ `RECONCILE_UNITS`.

    `hub_path_override`: dùng thẳng đường dẫn HUB đã resolve sẵn ở tầng gọi (glob-tolerant, xem
    `doi_chieu_song_phuong_kenh_core_service.py`) thay vì tự dò lại bằng tên chính xác — tránh 2
    lần resolve HUB lệch nhau khi file HUB không đúng tên chuẩn (đã dính lỗi CSV CORE/OSB cùng
    dạng). Chỉ có ý nghĩa khi `ma_nh` đã lọc còn 1 giá trị (mọi đơn vị của NH đó dùng chung 1 file
    HUB); mặc định `None` giữ nguyên hành vi tự dò cũ cho caller độc lập/test hiện có.

    Trả `{"ngay": ..., "don_vi": [...], "hub_theo_nh": {ma_nh: hub_df_da_loc}}` — `hub_theo_nh`
    (2026-08-31) là HUB đã qua `filter_before_reconcile`, cache theo NH để bước Hub↔Core
    (`kenh_core_service.py`) tái dùng thay vì tự đọc lại cùng file (xem `doi_chieu_hub_core`
    tham số `hub_t_override`). Mỗi phần tử `don_vi` có `trang_thai`
    ("ok" | "thieu_file_hub" | "thieu_file_kenh"). Khi "ok", kèm `match_result`
    (dict DataFrame từ `process.match_unit`), `kenh_df`, `summary` (có `chenh_so_mon`/
    `chenh_so_tien` — số tuyệt đối, KHÔNG dùng %, xem `SKILL.md`/quy tắc dự án: 1 lệnh
    chiếm tỉ lệ % rất nhỏ vẫn có thể mang giá trị hàng nghìn tỷ), `lech_tien`,
    `canh_bao_trang_thai`, `chi_tiet` (dict `{"hub":..., "kenh":...}` từ
    `process.classify_kenh_hub_den` — file gốc gắn cột trạng thái từng dòng, theo v3).

    Trả None nếu bị huỷ giữa chừng hoặc không xác định được ngày.
    """
    log = log_callback or (lambda msg: None)
    cancel = cancel_event or threading.Event()
    input_dir = Path(input_dir)

    ngay = ngay or detect_ngay(input_dir, chieu)
    if not ngay:
        log(f"[LỖI] Không tìm thấy file HUB (doichieugd_*_{chieu}_9999_N.zip) trong thư mục — "
            "không xác định được ngày đối chiếu.")
        return None
    log(f"Ngày đối chiếu: {ngay}")

    units = [u for u in RECONCILE_UNITS if ma_nh is None or u["ma_nh"] == ma_nh]
    don_vi_results = []
    # Cache HUB theo NH (2026-08-31, tối ưu hiệu năng) — NH 201/202 có 2 đơn vị (SPRT+SPT) DÙNG
    # CHUNG 1 file HUB (chỉ phụ thuộc `ma_nh`, không phụ thuộc `loai` — xem `config.py`). Trước
    # đây mỗi unit tự đọc+giải nén+lọc lại từ đầu dù kết quả giống hệt nhau. `None` = đã thử NH đó,
    # không có file (tránh dò lại + log lặp cho unit thứ 2 cùng NH).
    hub_cache: dict[str, tuple | None] = {}
    hub_theo_nh: dict[str, object] = {}  # trả ra ngoài cho caller (A2) tái dùng ở bước Hub↔Core

    for unit in units:
        if cancel.is_set():
            return None
        ma_nh, loai = unit["ma_nh"], unit["loai"]
        nhan = f"[{ma_nh}-{loai}]"

        if ma_nh not in hub_cache:
            hub_path = hub_path_override or (input_dir / hub_filename(ngay, ma_nh, chieu))
            if not hub_path.exists():
                log(f"[{ma_nh}] BỎ QUA — thiếu file HUB: {hub_path.name}")
                hub_cache[ma_nh] = None
            else:
                log(f"[{ma_nh}] Đang đọc HUB ({hub_path.name})...")
                with do_thoi_gian(log, f"[{ma_nh}] đọc+parse HUB"):
                    hub_raw = load_hub_zip(hub_path.read_bytes(), log=lambda msg, m=ma_nh: log(f"[{m}] {msg}"))
                    if chieu == "DI":
                        # Docx-đi không có bước lọc "-"/TXID+TRACE trùng trước khi khớp Kênh↔Hub
                        # (khác hẳn "đến") — dùng thẳng hub_raw, xem PLAN.md mục 2.1.
                        hub = hub_raw
                    else:
                        hub = filter_before_reconcile(hub_raw, log=lambda msg, m=ma_nh: log(f"[{m}] {msg}"))
                hub_cache[ma_nh] = (hub_raw, hub)
                hub_theo_nh[ma_nh] = hub
        elif hub_cache[ma_nh] is not None:
            log(f"{nhan} Dùng lại HUB đã đọc cho NH {ma_nh} (đơn vị khác cùng ngân hàng).")

        if hub_cache[ma_nh] is None:
            don_vi_results.append({"ma_nh": ma_nh, "loai": loai, "ngay": ngay, "trang_thai": "thieu_file_hub"})
            continue
        hub_raw, hub = hub_cache[ma_nh]
        if cancel.is_set():
            return None

        kenh_path = find_kenh_path(input_dir, ma_nh, loai, chieu)
        if kenh_path is None:
            # Review Khánh PR#86 B2 (2026-09-10): từ 03/09/2026 tên file kênh BẮT BUỘC có từ khoá
            # chiều ("đến"/"đi", không dấu cũng được — "den"/"di") mới nhận diện được, không chỉ
            # cần đủ "kênh"+mã NH+loại như trước. Log cũ không nói rõ điều này, dễ khiến người đọc
            # tưởng file đang nằm ngay đó mà chương trình không thấy là lỗi chương trình.
            log(f"{nhan} BỎ QUA — thiếu file kênh: {kenh_filename(ma_nh, loai, chieu)} "
                f"(đã thử cả tên đảo thứ tự {ma_nh}/{loai}; tên file BẮT BUỘC có đủ 4 từ khoá "
                f"không phân biệt dấu/hoa-thường/thứ tự: \"kênh\", \"{ma_nh}\", \"{loai}\", và "
                f"từ chỉ chiều \"{chieu.lower()}\" — VD \"đến\"/\"den\" hoặc \"đi\"/\"di\")")
            don_vi_results.append({"ma_nh": ma_nh, "loai": loai, "ngay": ngay, "trang_thai": "thieu_file_kenh"})
            continue

        log(f"{nhan} Đang đọc kênh ({kenh_path.name})...")
        with do_thoi_gian(log, f"{nhan} đọc file kênh"):
            kenh_df = load_kenh_file(str(kenh_path), ma_nh, loai, chieu)
        if cancel.is_set():
            return None

        log(f"{nhan} Đang so khớp...")
        mr = match_unit(hub, kenh_df, loai, chieu=chieu)

        # ── Bất biến bắt buộc ──
        assert len(mr["matched_hub"]) + len(mr["only_hub"]) == len(mr["hub"]), \
            f"{nhan} Bất biến HUB vỡ (matched+only != tổng)"
        assert len(mr["matched_kenh"]) + len(mr["only_kenh"]) == len(kenh_df), \
            f"{nhan} Bất biến KÊNH vỡ (matched+only != tổng)"

        if chieu == "DI":
            # `EXPECTED_ONE_SIDED_STATUSES` (chỉ {"RJCT"}) là khái niệm riêng của "đến" — hub đi
            # thật có ERPO/CALD/TPAY xuất hiện một-phía HOÀN TOÀN BÌNH THƯỜNG (không có counterpart
            # bên kênh), docx-đi không định nghĩa danh sách "một-phía dự kiến" nào. Áp nguyên hàm
            # `check_unexpected_one_sided` (viết riêng cho luật "đến") sẽ báo cảnh báo giả liên
            # tục — bỏ qua bước này cho "đi" thay vì suy diễn 1 danh sách chưa có căn cứ.
            canh_bao = []
        else:
            canh_bao = check_unexpected_one_sided(mr)
            if canh_bao:
                log(f"{nhan} [CẢNH BÁO] Trạng thái chỉ-hub ngoài dự kiến (khác RJCT): {canh_bao}")

        summary = (summarize_unit_di if chieu == "DI" else summarize_unit)(mr, kenh_df, ma_nh, loai)
        lech = dem_lech_tien_tren_khop(mr, kenh_df, loai, chieu=chieu)
        if lech["so_cap_lech"]:
            log(f"{nhan} [CẢNH BÁO] {lech['so_cap_lech']} cặp khớp khoá nhưng LỆCH tiền!")

        log(f"{nhan} Khớp {len(mr['matched_hub']):,}/{len(mr['hub']):,} dòng — "
            f"chỉ-hub {len(mr['only_hub']):,}, chỉ-kênh {len(mr['only_kenh']):,} — "
            f"chênh số món {summary['chenh_so_mon']:+,}, chênh số tiền {summary['chenh_so_tien']:+,} đồng")

        log(f"{nhan} Đang dựng file chi tiết (gắn cột trạng thái từng dòng)...")
        chi_tiet = (classify_kenh_hub_di if chieu == "DI" else classify_kenh_hub_den)(hub_raw, kenh_df, loai)

        don_vi_results.append({
            "ma_nh": ma_nh, "loai": loai, "ngay": ngay, "trang_thai": "ok",
            "match_result": mr, "kenh_df": kenh_df,
            "summary": summary, "lech_tien": lech,
            "canh_bao_trang_thai": canh_bao,
            "chi_tiet": chi_tiet,
        })

    log(f"Hoàn thành đối chiếu ngày {ngay}.")
    return {"ngay": ngay, "don_vi": don_vi_results, "hub_theo_nh": hub_theo_nh}
