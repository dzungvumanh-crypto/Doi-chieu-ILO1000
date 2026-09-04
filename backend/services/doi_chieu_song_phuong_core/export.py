"""Xuất kết quả đối chiếu HUB↔CORE — 1 file Excel tổng hợp (`TongHop`, theo nhãn KETQUADOICHIEU)
+ 2 file CSV chi tiết CORE/HUB (quyết định 2026-08-26: cần cả 2, không chỉ chi tiết; đổi 2026-08-31
sang CSV cho phần chi tiết — số đo thật cho thấy ghi Excel là nút thắt lớn nhất, xem
Implementation-notes.html card 98, module không dùng style/công thức Excel nào nên không mất gì).
"""

from pathlib import Path

import pandas as pd

from backend.services.ach.so_tien import doc_so_tien
from backend.services.doi_chieu_song_phuong_common import bao_ve_khoa_so_khoi_excel

from .match import KEY_COL

_COT_KHOA_HUB_CAN_BAO_VE = ("MSGREF", "TXID")

_TONG_HOP_COLS = ["Nhãn (KETQUADOICHIEU)", "Số dòng CORE", "Số tiền CORE", "Số dòng HUB", "Số tiền HUB"]


def build_tong_hop(core_df: pd.DataFrame, hub_df: pd.DataFrame) -> pd.DataFrame:
    core_amt = doc_so_tien(core_df["DRAMOUNT"], "core", "DRAMOUNT")
    hub_amt = doc_so_tien(hub_df["SO_TIEN"], "hub", "SO_TIEN")

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


def export_excel(ket_qua: dict, out_dir: str | Path, base_name: str) -> list[Path]:
    """`ket_qua` = dict trả về từ `pipeline.doi_chieu_hub_core()`. Ghi vào `out_dir`:
    `{base_name}.xlsx` (sheet `TongHop`) + `{base_name}_core_chi_tiet.csv` +
    `{base_name}_hub_chi_tiet.csv` (đổi 2026-08-31, trước là 3 sheet chung 1 file .xlsx). Trả
    `[tonghop_path, core_csv_path, hub_csv_path]` theo đúng thứ tự đó."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    core_df, hub_df = ket_qua["core_df"], ket_qua["hub_df"]
    tong_hop = build_tong_hop(core_df, hub_df)

    tonghop_path = out_dir / f"{base_name}.xlsx"
    with pd.ExcelWriter(tonghop_path, engine="xlsxwriter") as writer:
        tong_hop.to_excel(writer, sheet_name="TongHop", index=False)

    # CSV (không qua ExcelWriter) — Core_ChiTiet/Hub_ChiTiet có thể tới ~800k dòng, ghi CSV nhanh
    # hơn Excel nhiều lần (đo thật 2026-08-31, xem Implementation-notes.html card 98).
    # encoding="utf-8-sig" — đúng quy ước CSV khác của module.
    core_csv_path = out_dir / f"{base_name}_core_chi_tiet.csv"
    core_df.drop(columns=[KEY_COL], errors="ignore").to_csv(core_csv_path, index=False, encoding="utf-8-sig")

    hub_csv_path = out_dir / f"{base_name}_hub_chi_tiet.csv"
    hub_out = hub_df.drop(columns=[KEY_COL], errors="ignore").copy()
    for c in _COT_KHOA_HUB_CAN_BAO_VE:
        if c in hub_out.columns:
            hub_out[c] = bao_ve_khoa_so_khoi_excel(hub_out[c])
    hub_out.to_csv(hub_csv_path, index=False, encoding="utf-8-sig")

    return [tonghop_path, core_csv_path, hub_csv_path]
