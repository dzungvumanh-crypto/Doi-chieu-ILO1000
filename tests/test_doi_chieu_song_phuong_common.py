"""Test đơn vị cho helper dùng chung — `kiem_tra_du_lieu()` (Phần 2, 2026-08-30): dò TÊN file
(không đọc đĩa) xem đủ dữ liệu chạy Kênh↔Hub / Hub↔Core chưa, dùng cho banner cảnh báo TRƯỚC khi
bấm "Chạy" (không chặn nút Chạy). `bao_ve_khoa_so_khoi_excel()` (2026-09-04): bọc khoá toàn chữ
số (SPT) trước khi ghi CSV chi tiết, tránh Excel tự làm tròn/rụng số 0 đứng đầu khi mở trực tiếp.

Chạy: .venv\\Scripts\\python.exe -m pytest tests/test_doi_chieu_song_phuong_common.py -v
"""

import pandas as pd

from backend.services.doi_chieu_song_phuong_common import bao_ve_khoa_so_khoi_excel, kiem_tra_du_lieu

_NGAY = "20260825"
_MA_NH = "202"
_HUB_NAME = "doichieugd_20260825__05_DEN_9999_N.zip"
_KENH_NAME = "kênh đến SPRT 202.xlsx"
_CORE_CSV_NAME = "202_DEN_20260827_1408.csv"
_GL02_NAME = "GL02_20260825_1000.zip"


class TestKiemTraDuLieu:
    def test_du_ca_hai_khi_co_hub_kenh_va_core_csv(self):
        ket_qua = kiem_tra_du_lieu([_HUB_NAME, _KENH_NAME, _CORE_CSV_NAME], _NGAY, _MA_NH)
        assert ket_qua == {"kenh_hub": "du", "hub_core": "du"}

    def test_du_ca_hai_khi_core_la_gl02_zip_thay_vi_csv(self):
        ket_qua = kiem_tra_du_lieu([_HUB_NAME, _KENH_NAME, _GL02_NAME], _NGAY, _MA_NH)
        assert ket_qua == {"kenh_hub": "du", "hub_core": "du"}

    def test_thieu_ca_hai_khi_khong_co_file_hub(self):
        ket_qua = kiem_tra_du_lieu([_KENH_NAME, _CORE_CSV_NAME], _NGAY, _MA_NH)
        assert ket_qua["kenh_hub"].startswith("thieu:")
        assert ket_qua["hub_core"].startswith("thieu:")

    def test_chi_du_kenh_hub_khi_thieu_core(self):
        ket_qua = kiem_tra_du_lieu([_HUB_NAME, _KENH_NAME], _NGAY, _MA_NH)
        assert ket_qua["kenh_hub"] == "du"
        assert ket_qua["hub_core"].startswith("thieu:")

    def test_chi_du_hub_core_khi_thieu_kenh(self):
        ket_qua = kiem_tra_du_lieu([_HUB_NAME, _CORE_CSV_NAME], _NGAY, _MA_NH)
        assert ket_qua["kenh_hub"].startswith("thieu:")
        assert ket_qua["hub_core"] == "du"

    def test_khong_phan_biet_hoa_thuong_va_dau_khong_can_thiet(self):
        ket_qua = kiem_tra_du_lieu(
            [_HUB_NAME.upper(), "KENH DEN SPRT 202.XLSX", _CORE_CSV_NAME.upper()], _NGAY, _MA_NH,
        )
        assert ket_qua == {"kenh_hub": "du", "hub_core": "du"}

    def test_file_khong_lien_quan_khong_lam_du_gia(self):
        ket_qua = kiem_tra_du_lieu(["readme.txt", "osb 202.xlsx"], _NGAY, _MA_NH)
        assert ket_qua["kenh_hub"].startswith("thieu:")
        assert ket_qua["hub_core"].startswith("thieu:")


class TestBaoVeKhoaSoKhoiExcel:
    def test_boc_chuoi_toan_chu_so_16_ky_tu_khoa_spt(self):
        s = pd.Series(["2620210308078343"])
        out = bao_ve_khoa_so_khoi_excel(s)
        assert out.iloc[0] == '="2620210308078343"'

    def test_khong_boc_chuoi_chu_va_so_khoa_sprt(self):
        s = pd.Series(["020097048808210000062026pa5k802683"])
        out = bao_ve_khoa_so_khoi_excel(s)
        assert out.iloc[0] == "020097048808210000062026pa5k802683"

    def test_khong_boc_txid_co_dau_gach_ngang(self):
        """TXID dạng ghép "GD chuyển tiếp" (VD TXID001-260822000000004750633167) không phải
        toàn chữ số — giữ nguyên, không được bọc."""
        s = pd.Series(["TXID001-260822000000004750633167"])
        out = bao_ve_khoa_so_khoi_excel(s)
        assert out.iloc[0] == "TXID001-260822000000004750633167"

    def test_giu_nguyen_chuoi_rong_va_nan(self):
        s = pd.Series(["", None])
        out = bao_ve_khoa_so_khoi_excel(s)
        assert out.iloc[0] == ""
        assert pd.isna(out.iloc[1])

    def test_giu_so_0_dung_dau_khi_boc(self):
        """Số 0 đứng đầu là đúng lý do cần bọc — Excel coi là Số sẽ rụng mất số 0 này."""
        s = pd.Series(["0200970415123456"])
        out = bao_ve_khoa_so_khoi_excel(s)
        assert out.iloc[0] == '="0200970415123456"'
