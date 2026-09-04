"""Xuất kết quả đối chiếu Kênh↔Hub — 1 file Excel tổng hợp + 2 file CSV chi tiết (đổi 2026-08-31,
số đo thật cho thấy ghi Excel chiếm 60% tổng thời gian job — xem Implementation-notes.html card
98 — module này không dùng style/freeze pane/công thức Excel nào nên đổi sang CSV cho phần chi
tiết không mất gì ngoài tốc độ). Trước đó (2026-08-28) đã gộp cả 3 vào 1 file Excel 3 sheet:
`Bang1_TongHop` (tổng hợp, GIỮ Excel — nhỏ, không đáng đổi), `Hub_ChiTiet` (toàn bộ dòng HUB đã
gắn cột "TRẠNG THÁI KÊNH", ĐỔI CSV), `Kenh_ChiTiet` (toàn bộ dòng KÊNH đã gắn cột "TRẠNG THÁI TẠI
HUB", ĐỔI CSV) — 2 file chi tiết gộp MỌI đơn vị (SPRT+SPT) trong `day_results`, phân biệt bằng cột
"Ngày"/"Ngân hàng"/"Loại" chèn ở đầu.

Bảng 1 theo đúng mẫu Table 0 trong `đối chiếu kênh hub Song phương.docx` — tài liệu còn định
nghĩa "Bảng 1" cho CHIỀU ĐI, module này chỉ làm chiều ĐẾN (quyết định chủ dự án 2026-08-25) nên
không dựng cột chiều đi: không có dữ liệu thật để dựng, dựng bảng rỗng/giả sẽ gây hiểu nhầm.

Nội dung chi tiết lấy nguyên từ `don_vi["chi_tiet"]` (`process.classify_kenh_hub_den`, theo Bước
1/2 tài liệu v3 27/08/2026) — không đổi logic phân loại, chỉ đổi cách gộp file xuất ra.

⚠️ Gộp 1 sheet/1 file chỉ an toàn vì `doi_chieu_song_phuong_kenh_core_service.py` giới hạn mỗi
job 1 ngân hàng (tối đa 2 đơn vị SPRT+SPT/lần) — tổng vẫn dưới giới hạn ~1.048.576 dòng/sheet của
Excel (NH nhiều giao dịch nhất quan sát được, 311, ~800k dòng HUB thô/ngày) dù CSV không có giới
hạn này. KHÔNG gọi hàm này với `day_results` gộp nhiều ngân hàng cùng lúc.
"""

from pathlib import Path

import pandas as pd

from backend.services.doi_chieu_song_phuong_common import bao_ve_khoa_so_khoi_excel

from .config import KENH_KEY_COL, RECONCILE_UNITS

_COT_KHOA_HUB_CAN_BAO_VE = ("MSGREF", "TXID")

_BANG1_COLS = [
    "Ngày", "Ngân hàng", "Loại", "Số món HUB (1)", "Số tiền HUB (2)",
    "Số món kênh (3)", "Số tiền kênh (4)", "Chênh số món (5)=(3)-(1)",
    "Chênh tiền (6)=(4)-(2)", "Nguyên nhân",
]


def build_bang1_rows(day_results: list[dict]) -> pd.DataFrame:
    """Bảng 1: 1 dòng/ngày/đơn vị THẬT trong `RECONCILE_UNITS` (đơn vị không có nghiệp vụ,
    VD SPT của NH 203/311, không xuất hiện — quyết định 2026-08-26, xem `config.py`) + dòng
    TỔNG khi có nhiều hơn 1 ngày."""
    rows = []
    totals: dict[tuple, dict] = {}

    for day in day_results:
        ngay = day["ngay"]
        by_unit = {(d["ma_nh"], d["loai"]): d for d in day["don_vi"]}

        for unit in RECONCILE_UNITS:
            ma_nh, loai = unit["ma_nh"], unit["loai"]
            d = by_unit.get((ma_nh, loai))
            if d is None or d["trang_thai"] != "ok":
                trang_thai = d["trang_thai"] if d else "khong_tim_thay"
                rows.append({
                    "Ngày": ngay, "Ngân hàng": ma_nh, "Loại": loai,
                    "Số món HUB (1)": "", "Số tiền HUB (2)": "",
                    "Số món kênh (3)": "", "Số tiền kênh (4)": "",
                    "Chênh số món (5)=(3)-(1)": "", "Chênh tiền (6)=(4)-(2)": "",
                    "Nguyên nhân": f"Lỗi/thiếu dữ liệu: {trang_thai}",
                })
                continue

            s = d["summary"]
            rows.append({
                "Ngày": ngay, "Ngân hàng": ma_nh, "Loại": loai,
                "Số món HUB (1)": s["so_mon_hub"], "Số tiền HUB (2)": s["so_tien_hub"],
                "Số món kênh (3)": s["so_mon_kenh"], "Số tiền kênh (4)": s["so_tien_kenh"],
                "Chênh số món (5)=(3)-(1)": s["chenh_so_mon"], "Chênh tiền (6)=(4)-(2)": s["chenh_so_tien"],
                "Nguyên nhân": "",
            })
            key = (ma_nh, loai)
            t = totals.setdefault(key, {"so_mon_hub": 0, "so_tien_hub": 0, "so_mon_kenh": 0, "so_tien_kenh": 0})
            t["so_mon_hub"] += s["so_mon_hub"]
            t["so_tien_hub"] += s["so_tien_hub"]
            t["so_mon_kenh"] += s["so_mon_kenh"]
            t["so_tien_kenh"] += s["so_tien_kenh"]

    if len(day_results) > 1:
        for (ma_nh, loai), t in totals.items():
            rows.append({
                "Ngày": f"TỔNG {len(day_results)} NGÀY", "Ngân hàng": ma_nh, "Loại": loai,
                "Số món HUB (1)": t["so_mon_hub"], "Số tiền HUB (2)": t["so_tien_hub"],
                "Số món kênh (3)": t["so_mon_kenh"], "Số tiền kênh (4)": t["so_tien_kenh"],
                "Chênh số món (5)=(3)-(1)": t["so_mon_kenh"] - t["so_mon_hub"],
                "Chênh tiền (6)=(4)-(2)": t["so_tien_kenh"] - t["so_tien_hub"],
                "Nguyên nhân": "",
            })

    return pd.DataFrame(rows, columns=_BANG1_COLS)


def _gop_chi_tiet(day_results: list[dict], key: str) -> pd.DataFrame:
    """Gộp `don_vi["chi_tiet"][key]` (`key` = "hub"/"kenh") của mọi đơn vị `ok` trong
    `day_results` thành 1 DataFrame, chèn cột "Ngày"/"Ngân hàng"/"Loại" ở đầu để phân biệt."""
    frames = []
    for day in day_results:
        ngay = day["ngay"]
        for d in day["don_vi"]:
            if d["trang_thai"] != "ok":
                continue
            df = d["chi_tiet"][key].copy()
            df.insert(0, "Loại", d["loai"])
            df.insert(0, "Ngân hàng", d["ma_nh"])
            df.insert(0, "Ngày", ngay)
            frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def export_bao_cao(day_results: list[dict], out_dir: str | Path) -> list[Path]:
    """Xuất báo cáo Kênh↔Hub vào `out_dir` — 1 file Excel tổng hợp (`Bang1_TongHop`) + 2 file CSV
    chi tiết (`Hub_ChiTiet`/`Kenh_ChiTiet`, xem docstring module — đổi 2026-08-31, trước là 3
    sheet chung 1 file). `day_results` = danh sách kết quả `pipeline.main_from_dir()`, 1 phần
    tử/ngày (>=1 ngày). Trả `[tonghop_path, hub_csv_path, kenh_csv_path]` theo đúng thứ tự đó."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tonghop_path = out_dir / "doi_chieu_song_phuong_kenh_tonghop.xlsx"
    with pd.ExcelWriter(tonghop_path, engine="xlsxwriter") as writer:
        build_bang1_rows(day_results).to_excel(writer, sheet_name="Bang1_TongHop", index=False)

    # CSV (không qua ExcelWriter) — 2 file chi tiết có thể tới ~800k dòng, ghi CSV nhanh hơn Excel
    # nhiều lần (đo thật 2026-08-31: ghi Excel 2 sheet 700-800k dòng ~184-224s/lượt, xem
    # Implementation-notes.html card 98) vì không phải mã hoá container XML/zip của xlsx.
    # encoding="utf-8-sig" — đúng quy ước CSV khác của module (GL02/HUB), tránh lỗi hiển thị
    # tiếng Việt khi mở bằng Excel.
    hub_csv_path = out_dir / "doi_chieu_song_phuong_kenh_hub_chi_tiet.csv"
    hub_out = _gop_chi_tiet(day_results, "hub")
    for c in _COT_KHOA_HUB_CAN_BAO_VE:
        if c in hub_out.columns:
            hub_out[c] = bao_ve_khoa_so_khoi_excel(hub_out[c])
    hub_out.to_csv(hub_csv_path, index=False, encoding="utf-8-sig")

    kenh_csv_path = out_dir / "doi_chieu_song_phuong_kenh_kenh_chi_tiet.csv"
    kenh_out = _gop_chi_tiet(day_results, "kenh")
    if KENH_KEY_COL in kenh_out.columns:
        kenh_out[KENH_KEY_COL] = bao_ve_khoa_so_khoi_excel(kenh_out[KENH_KEY_COL])
    kenh_out.to_csv(kenh_csv_path, index=False, encoding="utf-8-sig")

    return [tonghop_path, hub_csv_path, kenh_csv_path]
