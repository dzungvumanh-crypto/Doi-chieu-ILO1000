"""Xuất kết quả đối chiếu HUB↔CORE **chiều ĐI** — 1 file Excel tổng hợp (`TongHop`, phân bố theo
nhãn KETQUADOICHIEU) + 2 file CSV chi tiết CORE/HUB + (nếu có) 1 file CSV riêng cho nhóm "lệnh fx"
trùng REMARK (xem `match.py::tim_nhom_lenh_fx_trung_remark` — không tự ghép cặp huỷ bằng code,
xuất nguyên vẹn để người soát tự đối chiếu tay trên hệ thống).

Giữ nguyên khuôn của chiều đến (`doi_chieu_song_phuong_core/export.py`): chi tiết ghi CSV, chỉ
bảng tổng hợp ghi Excel — số đo thật 2026-08-31 cho thấy ghi Excel chiếm ~60% thời gian job với
dữ liệu vài trăm nghìn dòng, mà module không dùng style/công thức Excel nào.

KHÁC chiều đến đúng MỘT chỗ (ngoài file lệnh-fx-trùng-remark mới): cột "Số tiền CORE" cộng
`CRAMOUNT` thay vì `DRAMOUNT` — CSV `{ma_nh}_DI*.csv` có DRAMOUNT LUÔN = "0" (511.378/511.378 và
878.092/878.092 dòng đã khảo sát), lấy DRAMOUNT thì cột tiền CORE ra 0 tuyệt đối, bảng tổng hợp
mất hết ý nghĩa mà không báo lỗi.
"""

from pathlib import Path

import pandas as pd

from backend.services.ach.so_tien import doc_so_tien

from .match import KEY_COL, tim_nhom_lenh_fx_trung_remark

_TONG_HOP_COLS = ["Nhãn (KETQUADOICHIEU)", "Số dòng CORE", "Số tiền CORE", "Số dòng HUB", "Số tiền HUB"]

_GHI_CHU_KHONG_THIEU_FILE = (
    "Không thiếu file HUB/CORE nào trong cửa sổ ngày cần đọc cho lần chạy này (HUB T..T-3, "
    "CORE T-3..T+3) — mọi nhãn T±k trong bảng TongHop đều có đủ dữ liệu để tính."
)


def build_tong_hop_di(core_df: pd.DataFrame, hub_df: pd.DataFrame) -> pd.DataFrame:
    core_amt = doc_so_tien(core_df["CRAMOUNT"], "core_di", "CRAMOUNT")
    hub_amt = doc_so_tien(hub_df["SO_TIEN"], "hub_di", "SO_TIEN")

    core_grp = (
        core_df.assign(_amt=core_amt)
        .groupby("KETQUADOICHIEU")
        .agg(so_dong_core=("KETQUADOICHIEU", "size"), so_tien_core=("_amt", "sum"))
    )
    hub_grp = (
        hub_df.assign(_amt=hub_amt)
        .groupby("KETQUADOICHIEU")
        .agg(so_dong_hub=("KETQUADOICHIEU", "size"), so_tien_hub=("_amt", "sum"))
    )

    tong = core_grp.join(hub_grp, how="outer").fillna(0)
    for c in ("so_dong_core", "so_tien_core", "so_dong_hub", "so_tien_hub"):
        tong[c] = tong[c].astype("int64")
    tong = tong.reset_index().rename(columns=dict(zip(
        ["KETQUADOICHIEU", "so_dong_core", "so_tien_core", "so_dong_hub", "so_tien_hub"],
        _TONG_HOP_COLS,
    ))).sort_values(_TONG_HOP_COLS[0]).reset_index(drop=True)

    tong_dong = {
        _TONG_HOP_COLS[0]: "Tổng cộng",
        _TONG_HOP_COLS[1]: int(tong[_TONG_HOP_COLS[1]].sum()),
        _TONG_HOP_COLS[2]: int(tong[_TONG_HOP_COLS[2]].sum()),
        _TONG_HOP_COLS[3]: int(tong[_TONG_HOP_COLS[3]].sum()),
        _TONG_HOP_COLS[4]: int(tong[_TONG_HOP_COLS[4]].sum()),
    }
    return pd.concat([tong, pd.DataFrame([tong_dong])], ignore_index=True)


def export_excel_di(ket_qua: dict, out_dir: str | Path, base_name: str) -> list[Path]:
    """`ket_qua` = dict trả về từ `pipeline.doi_chieu_hub_core_di()`. Ghi vào `out_dir`:
    `{base_name}.xlsx` (sheet `TongHop` + `GhiChu`) + `{base_name}_core_chi_tiet.csv` +
    `{base_name}_hub_chi_tiet.csv` + (nếu có) `{base_name}_lenh_fx_trung_remark.csv`. Trả danh
    sách đường dẫn theo đúng thứ tự ghi (file cuối chỉ xuất hiện khi có dòng để báo) — sheet
    `GhiChu` KHÔNG tính vào danh sách trả về vì nằm chung file `{base_name}.xlsx`."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    core_df, hub_df = ket_qua["core_df"], ket_qua["hub_df"]
    tong_hop = build_tong_hop_di(core_df, hub_df)

    tonghop_path = out_dir / f"{base_name}.xlsx"
    with pd.ExcelWriter(tonghop_path, engine="xlsxwriter") as writer:
        tong_hop.to_excel(writer, sheet_name="TongHop", index=False)
        # Sheet "GhiChu" (2026-09-09) — persist ghi chú thiếu file HUB/CORE của chính lần chạy
        # này, để người soát mở file kết quả một mình cũng biết vì sao thiếu nhãn T±k nào đó,
        # không phải tra lại log job (card 123 Implementation-notes.html).
        ghi_chu = ket_qua.get("ghi_chu") or [_GHI_CHU_KHONG_THIEU_FILE]
        pd.DataFrame({"Ghi chú": ghi_chu}).to_excel(writer, sheet_name="GhiChu", index=False)

    # encoding="utf-8-sig" — đúng quy ước CSV của cả module Đối chiếu Song phương.
    core_csv_path = out_dir / f"{base_name}_core_chi_tiet.csv"
    core_df.drop(columns=[KEY_COL], errors="ignore").to_csv(
        core_csv_path, index=False, encoding="utf-8-sig")

    hub_csv_path = out_dir / f"{base_name}_hub_chi_tiet.csv"
    hub_df.drop(columns=[KEY_COL], errors="ignore").to_csv(
        hub_csv_path, index=False, encoding="utf-8-sig")

    ket_qua_files = [tonghop_path, core_csv_path, hub_csv_path]

    # Nhóm "lệnh fx" trùng REMARK — quyết định người dùng 2026-09-05 (xem
    # match.py::tim_nhom_lenh_fx_trung_remark): không tự ghép cặp huỷ bằng code, chỉ xuất nguyên
    # vẹn để Ly/Trang tự đối chiếu tay trên hệ thống. Chỉ ghi file khi thực sự có nhóm trùng.
    nhom_fx_trung = tim_nhom_lenh_fx_trung_remark(core_df)
    if not nhom_fx_trung.empty:
        fx_trung_path = out_dir / f"{base_name}_lenh_fx_trung_remark.csv"
        nhom_fx_trung.drop(columns=[KEY_COL], errors="ignore").to_csv(
            fx_trung_path, index=False, encoding="utf-8-sig")
        ket_qua_files.append(fx_trung_path)

    return ket_qua_files
