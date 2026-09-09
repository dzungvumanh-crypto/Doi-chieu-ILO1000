"""
Test thuật toán module Đối chiếu Song phương — Kênh↔Hub chiều ĐẾN.

Test thuần trên DataFrame nhỏ dựng tay theo ĐÚNG định dạng đã xác nhận bằng dữ liệu
thật 3 ngày (21-23/08/2026): khoá SPRT 34 ký tự, khoá SPT 16 chữ số, TXID có `-` phải
loại trước khi đối chiếu (bản ghi huỷ/đảo WFPG/CGBR tham chiếu ngược WTSC/RTSC gốc),
`RJCT` là trạng thái một-phía đương nhiên duy nhất.

Chạy: .venv\\Scripts\\python.exe -m pytest tests/test_doi_chieu_song_phuong_kenh_algorithm.py -v
"""

import io
import zipfile

import pandas as pd
import pytest

from backend.services.doi_chieu_song_phuong_kenh import pipeline as pipeline_mod
from backend.services.doi_chieu_song_phuong_kenh.load_hub import (
    filter_before_reconcile, hub_filename, load_hub_zip,
)
from backend.services.doi_chieu_song_phuong_kenh.load_kenh import (
    find_kenh_path, kenh_filename, load_kenh_file,
)
from backend.services.doi_chieu_song_phuong_kenh.export import build_bang1_rows, export_bao_cao
from backend.services.doi_chieu_song_phuong_kenh.process import (
    check_unexpected_one_sided, classify_kenh_hub_den, classify_kenh_hub_di,
    dem_lech_tien_tren_khop, match_unit, summarize_unit, summarize_unit_di,
)

_HUB_COLS = ["NGAY_GIAO_DICH", "CHI_NHANH", "REFHUB", "MSGREF", "MSGSEQ", "TXID",
             "KENH_THANH_TOAN", "TRANG_THAI_LENH", "SO_TIEN", "TRACE", "SESSION",
             "LOAI_LENH_OSB", "NH_GUI", "NOI_DUNG"]


def _hub_row(msgref, txid, ktt="SP REALTIME", trang_thai="PYED", so_tien="100000",
             quote_prefix=False, trace="000353682"):
    q = "'" if quote_prefix else ""
    return {
        "NGAY_GIAO_DICH": "21/08/2026  ", "CHI_NHANH": "1000", "REFHUB": "'260821000000004744549727",
        "MSGREF": f"{q}{msgref}", "MSGSEQ": f"{q}{msgref}", "TXID": f"{q}{txid}",
        "KENH_THANH_TOAN": ktt, "TRANG_THAI_LENH": trang_thai, "SO_TIEN": so_tien,
        "TRACE": trace, "SESSION": "20260821", "LOAI_LENH_OSB": "0",
        "NH_GUI": "01202001", "NOI_DUNG": "TEST",
    }


def _hub_df(rows):
    return pd.DataFrame(rows, columns=_HUB_COLS)


def _kenh_row(mtid, so_tien="100000"):
    return {"STT": "1", "Ngày GD": "21/08/2026", "Giờ truyền nhận": "21/08/2026 00:00:06",
            "MtId/MsgId": mtid, "Số tiền": so_tien}


_KENH_COLS = ["STT", "Ngày GD", "Giờ truyền nhận", "MtId/MsgId", "Số tiền"]


def _kenh_df(rows):
    return pd.DataFrame(rows, columns=_KENH_COLS)


# ── Fixture riêng cho CHIỀU ĐI — schema HUB thật có 17 cột (khác 14 cột "đến"): thêm SE_TRACE,
# MA_GIAO_DICH, NGAY_KENH_TRA; NOI_DUNG KHÔNG phải cột cuối (NGAY_KENH_TRA nằm sau) — xem PLAN.md
# mục 1.1/3.5. Dùng riêng fixture này thay vì tái dùng _HUB_COLS (14 cột, đúng cho "đến" thôi).
_HUB_COLS_DI = ["NGAY_GIAO_DICH", "CHI_NHANH", "REFHUB", "MSGREF", "MSGSEQ", "TXID",
                "KENH_THANH_TOAN", "TRANG_THAI_LENH", "SO_TIEN", "TRACE", "SE_TRACE", "SESSION",
                "LOAI_LENH_OSB", "NH_NHAN", "MA_GIAO_DICH", "NOI_DUNG", "NGAY_KENH_TRA"]


def _hub_row_di(msgref, txid, ktt="SP REALTIME", trang_thai="SCNL", so_tien="100000",
                quote_prefix=False, trace="000353682", se_trace="", noi_dung="TEST"):
    q = "'" if quote_prefix else ""
    return {
        "NGAY_GIAO_DICH": "01/09/2026  ", "CHI_NHANH": "1000", "REFHUB": "'260901000000004744549727",
        "MSGREF": f"{q}{msgref}", "MSGSEQ": f"{q}{msgref}", "TXID": f"{q}{txid}",
        "KENH_THANH_TOAN": ktt, "TRANG_THAI_LENH": trang_thai, "SO_TIEN": so_tien,
        "TRACE": trace, "SE_TRACE": se_trace, "SESSION": "20260901", "LOAI_LENH_OSB": "  ",
        "NH_NHAN": "01202001", "MA_GIAO_DICH": "MAGD001", "NOI_DUNG": noi_dung,
        "NGAY_KENH_TRA": "01/09/2026",
    }


def _hub_df_di(rows):
    return pd.DataFrame(rows, columns=_HUB_COLS_DI)


# ── load_hub / load_kenh — filename helpers + zip parsing ─────────────────────

class TestFilenameHelpers:
    def test_hub_filename_theo_ma_nh(self):
        assert hub_filename("20260821", "202") == "doichieugd_20260821__05_DEN_9999_N.zip"
        assert hub_filename("20260821", "203") == "doichieugd_20260821__06_DEN_9999_N.zip"

    def test_hub_filename_ma_nh_khong_hop_le(self):
        with pytest.raises(ValueError):
            hub_filename("20260821", "999")

    def test_kenh_filename(self):
        assert kenh_filename("202", "SPRT") == "kênh đến SPRT 202.xlsx"
        assert kenh_filename("202", "SPT") == "kênh đến SPT 202.xlsx"

    def test_hub_filename_chieu_di(self):
        assert hub_filename("20260901", "201", chieu="DI") == "doichieugd_20260901__04_DI_9999_N.zip"

    def test_kenh_filename_chieu_di(self):
        assert kenh_filename("201", "SPRT", chieu="DI") == "kênh đi SPRT 201.xlsx"

    def test_find_kenh_path_khong_dau_chieu_di(self, tmp_path):
        (tmp_path / "kenh SPRT di 201 1.9.xlsx").write_bytes(b"x")
        p = find_kenh_path(tmp_path, "201", "SPRT", chieu="DI")
        assert p is not None and p.name == "kenh SPRT di 201 1.9.xlsx"

    def test_find_kenh_path_di_khong_khop_file_den(self, tmp_path):
        (tmp_path / "kênh đến SPRT 201.xlsx").write_bytes(b"x")
        assert find_kenh_path(tmp_path, "201", "SPRT", chieu="DI") is None

    def test_find_kenh_path_ca_2_chieu_cung_thu_muc_khong_lan(self, tmp_path):
        """Regression 2026-09-03: trước khi thêm từ khoá `chieu` vào `can_co`, 1 thư mục có cả
        file đi lẫn đến cùng mã NH+loại sẽ không phân biệt được — dễ chọn nhầm file."""
        (tmp_path / "kênh đến SPRT 201.xlsx").write_bytes(b"x")
        (tmp_path / "kenh SPRT di 201 1.9.xlsx").write_bytes(b"y")
        p_den = find_kenh_path(tmp_path, "201", "SPRT", chieu="DEN")
        p_di = find_kenh_path(tmp_path, "201", "SPRT", chieu="DI")
        assert p_den is not None and p_den.name == "kênh đến SPRT 201.xlsx"
        assert p_di is not None and p_di.name == "kenh SPRT di 201 1.9.xlsx"

    def test_find_kenh_path_ten_chuan(self, tmp_path):
        (tmp_path / "kênh đến SPRT 202.xlsx").write_bytes(b"x")
        p = find_kenh_path(tmp_path, "202", "SPRT")
        assert p is not None and p.name == "kênh đến SPRT 202.xlsx"

    def test_find_kenh_path_ten_dao_thu_tu(self, tmp_path):
        (tmp_path / "kênh đến 202 SPRT.xlsx").write_bytes(b"x")
        p = find_kenh_path(tmp_path, "202", "SPRT")
        assert p is not None and p.name == "kênh đến 202 SPRT.xlsx"

    def test_find_kenh_path_khong_thay(self, tmp_path):
        assert find_kenh_path(tmp_path, "202", "SPRT") is None

    def test_find_kenh_path_khong_dau_kem_ngay(self, tmp_path):
        """Dữ liệu NH 201/311 (thư mục TRANG/) đặt tên không dấu, kèm ngày: `kenh SPRT den 201
        24.8.xlsx`."""
        (tmp_path / "kenh SPRT den 201 24.8.xlsx").write_bytes(b"x")
        p = find_kenh_path(tmp_path, "201", "SPRT")
        assert p is not None and p.name == "kenh SPRT den 201 24.8.xlsx"

    def test_find_kenh_path_phan_biet_sprt_spt(self, tmp_path):
        (tmp_path / "kenh SPT den 201 24.8.xlsx").write_bytes(b"x")
        assert find_kenh_path(tmp_path, "201", "SPRT") is None
        assert find_kenh_path(tmp_path, "201", "SPT") is not None


class TestLoadHubZip:
    def _make_zip(self, df: pd.DataFrame) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("data.csv", df.to_csv(index=False).encode("utf-8-sig"))
        return buf.getvalue()

    def test_strip_nhay_don_dau_msgref_txid(self):
        df = _hub_df([_hub_row("MSG001", "TXID001", quote_prefix=True)])
        zip_bytes = self._make_zip(df)
        out = load_hub_zip(zip_bytes)
        assert out.loc[0, "MSGREF"] == "MSG001", "Phải strip dấu nháy đơn đầu"
        assert out.loc[0, "TXID"] == "TXID001"

    def test_doc_duoc_dong_noi_dung_co_ngoac_kep_chua_escape(self):
        """Dữ liệu thật (NH 311, 22.8.2026) có dòng NOI_DUNG chứa dấu " chưa escape đúng chuẩn
        CSV, khiến pd.read_csv raise ParserError — phải tự phục hồi, không mất dòng."""
        header = ",".join(_HUB_COLS)
        dong_binh_thuong = _hub_row("MSG001", "TXID001", so_tien="100000")
        dong_loi = _hub_row("MSG002", "TXID002", so_tien="468000000")
        dong_loi["NOI_DUNG"] = (
            '"Cong ty ABC thuc hien Du an "Kinh doanh vat lieu" tai xa X, tinh Y"'
        )
        csv_text = header + "\r\n"
        csv_text += ",".join(str(dong_binh_thuong[c]) for c in _HUB_COLS) + "\r\n"
        csv_text += ",".join(str(dong_loi[c]) for c in _HUB_COLS) + "\r\n"

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("data.csv", csv_text.encode("utf-8-sig"))

        logs = []
        out = load_hub_zip(buf.getvalue(), log=logs.append)
        assert len(out) == 2, "Không được mất dòng lỗi định dạng"
        assert out.loc[1, "TXID"] == "TXID002"
        assert out.loc[1, "SO_TIEN"] == "468000000"
        assert "Kinh doanh vat lieu" in out.loc[1, "NOI_DUNG"]
        assert any("CẢNH BÁO" in m for m in logs)

    def test_doc_duoc_dong_loi_khi_noi_dung_khong_phai_cot_cuoi(self):
        """Regression 2026-09-03: HUB chiều đi có 17 cột, NGAY_KENH_TRA nằm SAU NOI_DUNG (khác
        "đến" — NOI_DUNG là cột cuối). Bản `_doc_csv_hub_thu_cong()` cũ giả định NOI_DUNG luôn ở
        cuối sẽ nuốt mất NGAY_KENH_TRA vào NOI_DUNG khi rơi vào nhánh dự phòng. Bản mới định vị
        theo TÊN cột — phải giữ đúng NGAY_KENH_TRA nguyên vẹn."""
        header = ",".join(_HUB_COLS_DI)
        dong_binh_thuong = _hub_row_di("MSG001", "TXID001", so_tien="100000")
        dong_loi = _hub_row_di("MSG002", "TXID002", so_tien="468000000")
        dong_loi["NOI_DUNG"] = (
            '"Cong ty ABC thuc hien Du an "Kinh doanh vat lieu" tai xa X, tinh Y"'
        )
        dong_loi["NGAY_KENH_TRA"] = "02/09/2026"
        csv_text = header + "\r\n"
        csv_text += ",".join(str(dong_binh_thuong[c]) for c in _HUB_COLS_DI) + "\r\n"
        csv_text += ",".join(str(dong_loi[c]) for c in _HUB_COLS_DI) + "\r\n"

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("data.csv", csv_text.encode("utf-8-sig"))

        logs = []
        out = load_hub_zip(buf.getvalue(), log=logs.append)
        assert len(out) == 2, "Không được mất dòng lỗi định dạng"
        assert out.loc[1, "TXID"] == "TXID002"
        assert out.loc[1, "SO_TIEN"] == "468000000"
        assert "Kinh doanh vat lieu" in out.loc[1, "NOI_DUNG"]
        assert out.loc[1, "NGAY_KENH_TRA"] == "02/09/2026", (
            "NGAY_KENH_TRA (cột sau NOI_DUNG) không được bị nuốt vào NOI_DUNG"
        )
        assert any("CẢNH BÁO" in m for m in logs)

    def test_thieu_cot_bat_buoc_raise(self):
        df = pd.DataFrame([{"MSGREF": "'MSG001"}])
        with pytest.raises(ValueError, match="thiếu cột"):
            load_hub_zip(self._make_zip(df))

    def test_zip_nhieu_hon_1_file_raise(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("a.csv", "x")
            zf.writestr("b.csv", "y")
        with pytest.raises(ValueError, match="đúng 1 file"):
            load_hub_zip(buf.getvalue())


class TestFilterBeforeReconcile:
    def test_loai_dong_txid_co_dau_gach(self):
        df = load_hub_zip(TestLoadHubZip()._make_zip(_hub_df([
            _hub_row("MSG001", "TXID001", trang_thai="WTSC"),
            _hub_row("MSG001", "TXID001-260822000000004750633167", trang_thai="WFPG"),
        ])))
        logs = []
        out = filter_before_reconcile(df, log=logs.append)
        assert len(out) == 1
        assert out.iloc[0]["TRANG_THAI_LENH"] == "WTSC"
        assert any("Loại 1 dòng" in m for m in logs)

    def test_khong_co_dong_nao_bi_loai(self):
        df = load_hub_zip(TestLoadHubZip()._make_zip(_hub_df([_hub_row("MSG001", "TXID001")])))
        out = filter_before_reconcile(df)
        assert len(out) == 1

    def test_loai_cap_txid_trace_trung_nhau(self):
        df = load_hub_zip(TestLoadHubZip()._make_zip(_hub_df([
            _hub_row("MSG001", "TXID001", trang_thai="RFED", trace="4713461"),
            _hub_row("MSG002", "TXID001", trang_thai="RFED", trace="4713461"),
            _hub_row("MSG003", "TXID999", trang_thai="PYED", trace="9999999"),
        ])))
        logs = []
        out = filter_before_reconcile(df, log=logs.append)
        assert len(out) == 1
        assert out.iloc[0]["TXID"] == "TXID999"
        assert any("giao dịch huỷ" in m for m in logs)

    def test_nhom_hon_2_dong_trung_txid_trace_bi_canh_bao(self):
        df = load_hub_zip(TestLoadHubZip()._make_zip(_hub_df([
            _hub_row("MSG001", "TXID001", trace="4713461"),
            _hub_row("MSG002", "TXID001", trace="4713461"),
            _hub_row("MSG003", "TXID001", trace="4713461"),
        ])))
        logs = []
        out = filter_before_reconcile(df, log=logs.append)
        assert len(out) == 0
        assert any("CẢNH BÁO" in m and "hơn 2 dòng" in m for m in logs)

    def test_trace_rong_khong_bi_coi_la_trung(self):
        df = load_hub_zip(TestLoadHubZip()._make_zip(_hub_df([
            _hub_row("MSG001", "TXID001", trang_thai="RJCT", trace=""),
            _hub_row("MSG002", "TXID002", trang_thai="RJCT", trace=""),
            _hub_row("MSG003", "TXID003", trang_thai="RJCT", trace=""),
        ])))
        out = filter_before_reconcile(df)
        assert len(out) == 3


# ── process.match_unit — existence-check theo khoá ─────────────────────────────

class TestMatchUnitRealtime:
    def test_khop_theo_msgref(self):
        hub = _hub_df([_hub_row("020097048808210000062026pa5k802683", "TXID001")])
        kenh = _kenh_df([_kenh_row("020097048808210000062026pa5k802683")])
        mr = match_unit(hub, kenh, "SPRT")
        assert len(mr["matched_hub"]) == 1
        assert len(mr["only_hub"]) == 0
        assert len(mr["matched_kenh"]) == 1
        assert len(mr["only_kenh"]) == 0

    def test_khac_msgref_khong_khop(self):
        hub = _hub_df([_hub_row("MSG_A", "TXID001")])
        kenh = _kenh_df([_kenh_row("MSG_B")])
        mr = match_unit(hub, kenh, "SPRT")
        assert len(mr["matched_hub"]) == 0
        assert len(mr["only_hub"]) == 1
        assert len(mr["only_kenh"]) == 1

    def test_chi_lay_dong_kenh_thanh_toan_dung_loai(self):
        hub = _hub_df([
            _hub_row("MSG_RT", "TXID001", ktt="SP REALTIME"),
            _hub_row("MSG_TH", "TXID002", ktt="SP THUONG"),
        ])
        kenh = _kenh_df([_kenh_row("MSG_RT")])
        mr = match_unit(hub, kenh, "SPRT")
        assert len(mr["hub"]) == 1, "Chỉ lấy dòng SP REALTIME, bỏ SP THUONG"


class TestMatchUnitThuong:
    def test_khop_theo_txid_16_chu_so(self):
        hub = _hub_df([_hub_row("MSG001", "2620210308078343", ktt="SP THUONG")])
        kenh = _kenh_df([_kenh_row("2620210308078343")])
        mr = match_unit(hub, kenh, "SPT")
        assert len(mr["matched_hub"]) == 1


class TestBatBienSoHoc:
    def test_bao_toan_so_dong_ca_hub_va_kenh(self):
        hub = _hub_df([
            _hub_row("MSG_A", "TXID001"), _hub_row("MSG_B", "TXID002"),
            _hub_row("MSG_C", "TXID003"),
        ])
        kenh = _kenh_df([_kenh_row("MSG_A"), _kenh_row("MSG_X")])
        mr = match_unit(hub, kenh, "SPRT")
        assert len(mr["matched_hub"]) + len(mr["only_hub"]) == len(mr["hub"])
        assert len(mr["matched_kenh"]) + len(mr["only_kenh"]) == len(kenh)


# ── Guard cốt lõi: check_unexpected_one_sided ──────────────────────────────────

class TestGuardUnexpectedOneSided:
    def test_chi_hub_toan_rjct_khong_canh_bao(self):
        hub = _hub_df([_hub_row("MSG_A", "TXID001", trang_thai="RJCT")])
        kenh = _kenh_df([])
        mr = match_unit(hub, kenh, "SPRT")
        assert check_unexpected_one_sided(mr) == []

    def test_chi_hub_co_trang_thai_khac_rjct_canh_bao(self):
        """Đây là chốt kiểm soát cốt lõi (yêu cầu bổ sung Phase 9, mục E) — nếu 1
        dòng chỉ-hub mang trạng thái KHÁC RJCT (VD PYED bỗng không có đối ứng kênh),
        guard PHẢI phát hiện, không được im lặng bỏ qua."""
        hub = _hub_df([
            _hub_row("MSG_A", "TXID001", trang_thai="RJCT"),
            _hub_row("MSG_B", "TXID002", trang_thai="PYED"),
        ])
        kenh = _kenh_df([])
        mr = match_unit(hub, kenh, "SPRT")
        canh_bao = check_unexpected_one_sided(mr)
        assert canh_bao == ["PYED"], "Phải phát hiện đúng trạng thái lạ, bỏ qua RJCT đã dự kiến"

    def test_khong_co_dong_chi_hub_khong_canh_bao(self):
        hub = _hub_df([_hub_row("MSG_A", "TXID001", trang_thai="PYED")])
        kenh = _kenh_df([_kenh_row("MSG_A")])
        mr = match_unit(hub, kenh, "SPRT")
        assert check_unexpected_one_sided(mr) == []


# ── summarize_unit — Bảng 1, loại RJCT khỏi phía HUB ───────────────────────────

class TestSummarizeUnit:
    def test_rjct_bi_loai_khoi_bang_1(self):
        hub = _hub_df([
            _hub_row("MSG_A", "TXID001", trang_thai="PYED", so_tien="100000"),
            _hub_row("MSG_B", "TXID002", trang_thai="RJCT", so_tien="999999"),
        ])
        kenh = _kenh_df([_kenh_row("MSG_A", so_tien="100000")])
        mr = match_unit(hub, kenh, "SPRT")
        s = summarize_unit(mr, kenh, "202", "SPRT")
        assert s["so_mon_hub"] == 1, "RJCT (999999) phải bị loại khỏi đếm/tổng tiền Bảng 1"
        assert s["so_tien_hub"] == 100000
        assert s["chenh_so_mon"] == 0
        assert s["chenh_so_tien"] == 0


# ── dem_lech_tien_tren_khop ─────────────────────────────────────────────────────

class TestDemLechTien:
    def test_khong_lech(self):
        hub = _hub_df([_hub_row("MSG_A", "TXID001", so_tien="100000")])
        kenh = _kenh_df([_kenh_row("MSG_A", so_tien="100000")])
        mr = match_unit(hub, kenh, "SPRT")
        r = dem_lech_tien_tren_khop(mr, kenh, "SPRT")
        assert r["so_cap_lech"] == 0

    def test_phat_hien_lech(self):
        hub = _hub_df([_hub_row("MSG_A", "TXID001", so_tien="100000")])
        kenh = _kenh_df([_kenh_row("MSG_A", so_tien="999999")])
        mr = match_unit(hub, kenh, "SPRT")
        r = dem_lech_tien_tren_khop(mr, kenh, "SPRT")
        assert r["so_cap_lech"] == 1
        assert r["vi_du"][0]["so_tien_hub"] == 100000
        assert r["vi_du"][0]["so_tien_kenh"] == 999999


# ── export.build_bang1_rows — chỉ hiện đơn vị thật trong RECONCILE_UNITS ──────

_SUMMARY_MAU = {"so_mon_hub": 1, "so_tien_hub": 100000, "so_mon_kenh": 1,
                "so_tien_kenh": 100000, "chenh_so_mon": 0, "chenh_so_tien": 0}


class TestBuildBang1Rows:
    def test_khong_co_dong_spt_cho_nh_khong_co_nghiep_vu(self):
        """203 và 311 không có nghiệp vụ SPT — RECONCILE_UNITS không có entry cho 2 cặp này nên
        build_bang1_rows() không bao giờ tạo dòng cho chúng (không phải lỗi/thiếu dữ liệu, đơn
        giản là không nằm trong danh sách đơn vị cần chấm)."""
        day = {"ngay": "20260825", "don_vi": [
            {"ma_nh": ma_nh, "loai": loai, "trang_thai": "ok", "summary": _SUMMARY_MAU}
            for ma_nh, loai in [("201", "SPRT"), ("201", "SPT"), ("202", "SPRT"),
                                ("202", "SPT"), ("203", "SPRT"), ("311", "SPRT")]
        ]}
        df = build_bang1_rows([day])
        cap = set(zip(df["Ngân hàng"], df["Loại"]))
        assert cap == {("201", "SPRT"), ("201", "SPT"), ("202", "SPRT"),
                        ("202", "SPT"), ("203", "SPRT"), ("311", "SPRT")}
        assert ("203", "SPT") not in cap
        assert ("311", "SPT") not in cap
        assert ("311", "SPT") not in cap
        assert not df["Nguyên nhân"].str.contains("N/A", na=False).any()


# ── export.export_bao_cao — bọc khoá MtId/MsgId toàn chữ số khi ghi CSV chi tiết ──────────────

class TestExportBaoCaoBaoVeKhoaExcel:
    def test_mtid_spt_toan_chu_so_duoc_boc_trong_csv_that(self, tmp_path):
        """Bug báo bởi người dùng 2026-09-04: MtId/MsgId của SP THƯỜNG (16 chữ số thuần) sai khi
        mở file kenh_chi_tiet.csv bằng Excel — verify bằng file CSV thật ghi ra đĩa."""
        hub = _hub_df([_hub_row("2620210308078343", "TXID_SPT", ktt="SP THUONG", trang_thai="PYED")])
        kenh = _kenh_df([_kenh_row("2620210308078343")])
        ct = classify_kenh_hub_den(hub, kenh, "SPT")

        day = {"ngay": "20260904", "don_vi": [
            {"ma_nh": "202", "loai": "SPT", "trang_thai": "ok", "chi_tiet": ct, "summary": _SUMMARY_MAU},
        ]}
        paths = export_bao_cao([day], tmp_path)
        kenh_csv_path, hub_csv_path = paths[2], paths[1]

        # Đọc lại bằng pandas (đúng cách Excel sẽ hiểu field có dấu ngoặc kép), không so khớp
        # chuỗi thô — CSV tự nhân đôi dấu " khi ghi field chứa formula.
        kenh_out = pd.read_csv(kenh_csv_path, dtype=str, encoding="utf-8-sig")
        assert kenh_out.loc[0, "MtId/MsgId"] == '="2620210308078343"'

        hub_out = pd.read_csv(hub_csv_path, dtype=str, encoding="utf-8-sig")
        assert hub_out.loc[0, "TXID"] == "TXID_SPT"  # chữ+số giữ nguyên, không bọc


# ── classify_kenh_hub_den — Bước 1/2 chi tiết chiều ĐẾN (thay "Bảng 3", tài liệu v3) ────────

class TestClassifyKenhHubDen:
    def test_du_5_nhan_dung_thu_tu_waterfall(self):
        hub = _hub_df([
            # Bước 2.1: cặp (TXID, TRACE) trùng dòng khác -> "GD có trace hủy"
            _hub_row("MSG_TH1", "TXID_TH", trang_thai="RFED", trace="4713461"),
            _hub_row("MSG_TH2", "TXID_TH", trang_thai="RFED", trace="4713461"),
            # Bước 2.2: "-" trong TXID -> "GD chuyển tiếp"
            _hub_row("MSG_CT", "TXID_A-260822000000004750633167", trang_thai="WFPG"),
            # Bước 2.3: RJCT không khớp kênh -> "GD Đã từ chối-kênh không thành công"
            _hub_row("MSG_RJCT_KO", "TXID_RJCT", trang_thai="RJCT"),
            # Bước 2.4: khớp kênh -> "KÊNH THÀNH CÔNG"
            _hub_row("MSG_MATCHED", "TXID_OK", trang_thai="PYED"),
            # Bước 2.5: còn lại -> "HUB THỪA"
            _hub_row("MSG_HUBTHUA", "TXID_HT", trang_thai="PYED"),
            # Ngoài phạm vi loại (SP THUONG) — phải bị loại khỏi kết quả SPRT
            _hub_row("MSG_KHAC_LOAI", "TXID_KL", ktt="SP THUONG", trang_thai="PYED"),
        ])
        kenh = _kenh_df([
            _kenh_row("MSG_MATCHED"),
            _kenh_row("MSG_EXTRA"),  # chỉ có ở kênh -> "KÊNH THỪA"
        ])

        ct = classify_kenh_hub_den(hub, kenh, "SPRT")
        hub_out, kenh_out = ct["hub"], ct["kenh"]

        assert len(hub_out) == 6, "Dòng SP THUONG phải bị loại khỏi đơn vị SPRT"

        def _nhan(msgref):
            return hub_out.loc[hub_out["MSGREF"] == msgref, "TRẠNG THÁI KÊNH"].iloc[0]

        assert _nhan("MSG_TH1") == "GD có trace hủy"
        assert _nhan("MSG_TH2") == "GD có trace hủy"
        assert _nhan("MSG_CT") == "GD chuyển tiếp"
        assert _nhan("MSG_RJCT_KO") == "GD Đã từ chối-kênh không thành công"
        assert _nhan("MSG_MATCHED") == "KÊNH THÀNH CÔNG"
        assert _nhan("MSG_HUBTHUA") == "HUB THỪA"

        assert kenh_out.loc[kenh_out["MtId/MsgId"] == "MSG_MATCHED", "TRẠNG THÁI TẠI HUB"].iloc[0] == "PYED"
        assert kenh_out.loc[kenh_out["MtId/MsgId"] == "MSG_EXTRA", "TRẠNG THÁI TẠI HUB"].iloc[0] == "KÊNH THỪA"

    def test_trace_huy_uu_tien_hon_rjct(self):
        """Waterfall dừng ở bước đầu khớp — dòng vừa RJCT vừa có cặp trace trùng phải nhận nhãn
        "GD có trace hủy" (Bước 2.1), không rơi xuống Bước 2.3."""
        hub = _hub_df([
            _hub_row("MSG_A", "TXID_X", trang_thai="RJCT", trace="123"),
            _hub_row("MSG_B", "TXID_X", trang_thai="RJCT", trace="123"),
        ])
        kenh = _kenh_df([])
        ct = classify_kenh_hub_den(hub, kenh, "SPRT")
        assert (ct["hub"]["TRẠNG THÁI KÊNH"] == "GD có trace hủy").all()

    def test_khoa_theo_txid_cho_spt(self):
        hub = _hub_df([_hub_row("MSG_X", "2620210308078343", ktt="SP THUONG", trang_thai="PYED")])
        kenh = _kenh_df([_kenh_row("2620210308078343")])
        ct = classify_kenh_hub_den(hub, kenh, "SPT")
        assert ct["hub"]["TRẠNG THÁI KÊNH"].iloc[0] == "KÊNH THÀNH CÔNG"
        assert ct["kenh"]["TRẠNG THÁI TẠI HUB"].iloc[0] == "PYED"


class TestClassifyKenhHubDi:
    """Chiều đi — docx `Đối chiếu SP chiều đi.docx`: CHỈ 2 bước, KHÔNG lọc "-"/trace-huỷ trước khi
    khớp (khác hẳn đến — xem PLAN.md mục 2.1). Dùng `_hub_row_di`/`_hub_df_di` (schema 17 cột)."""

    def test_2_nhan_dung_waterfall_khong_loc_gi_truoc(self):
        hub = _hub_df_di([
            # Có "-" trong TXID và trạng thái không phải SCNL — đến sẽ lọc/gắn nhãn riêng,
            # đi thì KHÔNG lọc gì, chỉ xét có khớp kênh hay không.
            _hub_row_di("MSG_ERPO", "TXID_A-260901000000004750633167", trang_thai="ERPO"),
            _hub_row_di("MSG_MATCHED", "TXID_OK", trang_thai="SCNL"),
            _hub_row_di("MSG_HUBTHUA", "TXID_HT", trang_thai="SCNL"),
            _hub_row_di("MSG_KHAC_LOAI", "TXID_KL", ktt="SP THUONG", trang_thai="SCNL"),
        ])
        kenh = _kenh_df([
            _kenh_row("MSG_MATCHED"),
            _kenh_row("MSG_EXTRA"),  # chỉ có ở kênh -> "KÊNH THỪA"
        ])

        ct = classify_kenh_hub_di(hub, kenh, "SPRT")
        hub_out, kenh_out = ct["hub"], ct["kenh"]

        assert len(hub_out) == 3, "Dòng SP THUONG phải bị loại khỏi đơn vị SPRT"

        def _nhan(msgref):
            return hub_out.loc[hub_out["MSGREF"] == msgref, "TRẠNG THÁI KÊNH"].iloc[0]

        # Dòng có "-" trong TXID vẫn được xét khớp bình thường (không lọc trước như đến)
        assert _nhan("MSG_ERPO") == "HUB THỪA"
        assert _nhan("MSG_MATCHED") == "KÊNH THÀNH CÔNG"
        assert _nhan("MSG_HUBTHUA") == "HUB THỪA"

        # Bước 1: TRẠNG THÁI TẠI HUB = copy nguyên TRANG_THAI_LENH (kể cả ERPO/CALD, không lọc)
        assert kenh_out.loc[kenh_out["MtId/MsgId"] == "MSG_MATCHED", "TRẠNG THÁI TẠI HUB"].iloc[0] == "SCNL"
        assert kenh_out.loc[kenh_out["MtId/MsgId"] == "MSG_EXTRA", "TRẠNG THÁI TẠI HUB"].iloc[0] == "KÊNH THỪA"

    def test_khoa_theo_msgref_cho_spt_di(self):
        """Chiều ĐI dùng MSGREF cho SPT (KHÁC chiều đến, dùng TXID) — docx-đi ghi TXID (copy nhầm
        từ mẫu đến), nhưng dữ liệu thật NH 202 cho khớp 0/X mọi ngày với TXID, 93-99% với MSGREF;
        người chấm thủ công đã XÁC NHẬN dùng MSGREF (2026-09-04, đã chốt) — xem
        `config.py::LOAI_KHOA_HUB_DI`."""
        hub = _hub_df_di([_hub_row_di("2620410375583849", "TXID_KHAC", ktt="SP THUONG", trang_thai="SCNL")])
        kenh = _kenh_df([_kenh_row("2620410375583849")])
        ct = classify_kenh_hub_di(hub, kenh, "SPT")
        assert ct["hub"]["TRẠNG THÁI KÊNH"].iloc[0] == "KÊNH THÀNH CÔNG"
        assert ct["kenh"]["TRẠNG THÁI TẠI HUB"].iloc[0] == "SCNL"


class TestSummarizeUnitDi:
    """Bảng 1 chiều đi: cột (1)/(2) CHỈ đếm HUB trạng thái SCNL (không phải "loại 1 phía" như
    đến); cột (3)/(4) đếm toàn bộ kênh — không lọc."""

    def test_cot_1_2_chi_dem_scnl(self):
        hub = _hub_df_di([
            _hub_row_di("MSG_SCNL", "TXID_1", trang_thai="SCNL", so_tien="100000"),
            _hub_row_di("MSG_ERPO", "TXID_2", trang_thai="ERPO", so_tien="999999"),
            _hub_row_di("MSG_CALD", "TXID_3", trang_thai="CALD", so_tien="500000"),
        ])
        kenh = _kenh_df([_kenh_row("MSG_SCNL", so_tien="100000")])
        mr = match_unit(hub, kenh, "SPRT")
        summary = summarize_unit_di(mr, kenh, "201", "SPRT")
        assert summary["so_mon_hub"] == 1, "Chỉ đếm đúng 1 dòng SCNL, bỏ qua ERPO/CALD"
        assert summary["so_tien_hub"] == 100000
        assert summary["so_mon_kenh"] == 1
        assert summary["so_tien_kenh"] == 100000
        assert summary["chenh_so_mon"] == 0
        assert summary["chenh_so_tien"] == 0


# ── load_kenh_file — đọc thật bằng engine calamine ─────────────────────────────

class TestLoadKenhFile:
    def test_doc_dung_cot_va_gia_tri(self, tmp_path):
        df = pd.DataFrame([{
            "STT": "1", "Ngày GD": "21/08/2026", "Giờ truyền nhận": "21/08/2026 00:00:06",
            "MtId/MsgId": "020097048808210000062026pa5k802683", "Số tiền": 130000,
        }])
        path = tmp_path / "kenh_test.xlsx"
        df.to_excel(path, index=False, engine="openpyxl")

        out = load_kenh_file(str(path), "202", "SPRT")
        assert list(out.columns) == ["STT", "Ngày GD", "Giờ truyền nhận", "MtId/MsgId", "Số tiền"]
        assert out.loc[0, "MtId/MsgId"] == "020097048808210000062026pa5k802683"

    def test_thieu_cot_raise(self, tmp_path):
        df = pd.DataFrame([{"STT": "1", "MtId/MsgId": "X"}])
        path = tmp_path / "kenh_thieu_cot.xlsx"
        df.to_excel(path, index=False, engine="openpyxl")
        with pytest.raises(ValueError, match="thiếu cột"):
            load_kenh_file(str(path), "202", "SPRT")

    def test_sprt_sai_prefix_ngan_hang_raise(self, tmp_path):
        """Guard phương án A (lyxink.txt): file khai báo NH 202 nhưng MtId/MsgId
        mang prefix của NH khác — phải raise rõ ràng, không âm thầm chạy tiếp."""
        df = pd.DataFrame([{
            "STT": "1", "Ngày GD": "21/08/2026", "Giờ truyền nhận": "21/08/2026 00:00:06",
            "MtId/MsgId": "020097043608210000022026DVps338600", "Số tiền": 130000,
        }])  # prefix 0200970436 = NH 203, không phải 202
        path = tmp_path / "kenh_sai_nh.xlsx"
        df.to_excel(path, index=False, engine="openpyxl")
        with pytest.raises(ValueError, match="không đúng prefix"):
            load_kenh_file(str(path), "202", "SPRT")

    def test_spt_khong_ap_dung_guard_prefix(self, tmp_path):
        """SPT không có bằng chứng prefix theo NH — guard không được áp dụng, dù
        MtId/MsgId không khớp prefix của bất kỳ NH nào trong KENH_MTID_PREFIX."""
        df = pd.DataFrame([{
            "STT": "1", "Ngày GD": "21/08/2026", "Giờ truyền nhận": "21/08/2026 02:29:02",
            "MtId/MsgId": "2620210308078343", "Số tiền": 2000000,
        }])
        path = tmp_path / "kenh_spt.xlsx"
        df.to_excel(path, index=False, engine="openpyxl")
        out = load_kenh_file(str(path), "202", "SPT")
        assert len(out) == 1

    def test_chieu_di_khong_ap_dung_guard_prefix(self, tmp_path):
        """Regression 2026-09-03: verify dữ liệu thật `kenh SPRT di 201/311 1.9.xlsx` (TOÀN BỘ
        487.466 + 843.588 dòng) cho thấy 10 ký tự đầu MtId/MsgId CẢ 2 NGÂN HÀNG đều là
        "0200970405" — giống hệt nhau, không phải mã riêng theo NH như `KENH_MTID_PREFIX` giả
        định cho chiều đến. Guard phải bỏ qua hoàn toàn khi `chieu="DI"`, kể cả với NH có khai
        trong `KENH_MTID_PREFIX` (201) và prefix không khớp giá trị khai báo cho "đến"."""
        df = pd.DataFrame([{
            "STT": "1", "Ngày GD": "01/09/2026", "Giờ truyền nhận": "01/09/2026 00:00:08",
            "MtId/MsgId": "0200970405090100000820260200970405", "Số tiền": 100000,
        }])  # prefix thật "0200970405" -- KHÁC hẳn KENH_MTID_PREFIX["201"] ("0200970415")
        path = tmp_path / "kenh_di.xlsx"
        df.to_excel(path, index=False, engine="openpyxl")
        out = load_kenh_file(str(path), "201", "SPRT", chieu="DI")
        assert len(out) == 1

    def test_chieu_den_van_ap_dung_guard_prefix_mac_dinh(self, tmp_path):
        """`chieu` mặc định "DEN" — không truyền tham số này (mọi call site cũ) vẫn giữ nguyên
        hành vi guard đã có, không bị nới lỏng ngầm khi thêm tham số mới."""
        df = pd.DataFrame([{
            "STT": "1", "Ngày GD": "21/08/2026", "Giờ truyền nhận": "21/08/2026 00:00:06",
            "MtId/MsgId": "020097043608210000022026DVps338600", "Số tiền": 130000,
        }])
        path = tmp_path / "kenh_sai_nh_den.xlsx"
        df.to_excel(path, index=False, engine="openpyxl")
        with pytest.raises(ValueError, match="không đúng prefix"):
            load_kenh_file(str(path), "202", "SPRT")


class TestMainFromDirHubCache:
    """2026-08-31, tối ưu hiệu năng — NH 201 có 2 đơn vị (SPRT+SPT) dùng CHUNG 1 file HUB
    (`config.py::RECONCILE_UNITS`). Trước đây `main_from_dir` đọc+giải nén+lọc lại HUB bên trong
    vòng lặp từng đơn vị -> đọc 2 lần cùng 1 file cho NH 201/202. Test này khoá hành vi: đúng 1
    lần gọi `load_hub_zip()` cho cả 2 đơn vị."""

    def test_hub_doc_dung_1_lan_cho_2_don_vi_cung_nh(self, tmp_path, monkeypatch):
        ngay = "20260821"
        hub_bytes = TestLoadHubZip()._make_zip(_hub_df([
            _hub_row("0200970415MSGRT2010001", "TXID2010001SPRT", ktt="SP REALTIME"),
            _hub_row("MSGREF2010002", "TXID2010002SPT", ktt="SP THUONG"),
        ]))
        (tmp_path / hub_filename(ngay, "201")).write_bytes(hub_bytes)
        pd.DataFrame(_kenh_df([_kenh_row("0200970415MSGRT2010001")])).to_excel(
            tmp_path / kenh_filename("201", "SPRT"), index=False, engine="openpyxl")
        pd.DataFrame(_kenh_df([_kenh_row("TXID2010002SPT")])).to_excel(
            tmp_path / kenh_filename("201", "SPT"), index=False, engine="openpyxl")

        calls = []
        real_load_hub_zip = pipeline_mod.load_hub_zip

        def dem_va_goi(*args, **kwargs):
            calls.append(1)
            return real_load_hub_zip(*args, **kwargs)

        monkeypatch.setattr(pipeline_mod, "load_hub_zip", dem_va_goi)

        result = pipeline_mod.main_from_dir(tmp_path, ngay=ngay, ma_nh="201")

        assert result is not None
        trang_thai = {(d["ma_nh"], d["loai"]): d["trang_thai"] for d in result["don_vi"]}
        assert trang_thai[("201", "SPRT")] == "ok"
        assert trang_thai[("201", "SPT")] == "ok"
        assert len(calls) == 1, f"HUB bị đọc {len(calls)} lần cho 2 đơn vị cùng NH, kỳ vọng đúng 1 lần"
        assert set(result["hub_theo_nh"].keys()) == {"201"}


class TestMainFromDirChieuDi:
    """`main_from_dir(chieu="DI")` — dò đúng file `_DI_`, KHÔNG lọc `filter_before_reconcile`
    (khác đến), dùng đúng `classify_kenh_hub_di`/`summarize_unit_di`."""

    def test_dung_file_di_khong_loc_khong_canh_bao_one_sided(self, tmp_path):
        ngay = "20260901"
        # NH 201 SPRT bắt buộc khoá khớp prefix KENH_MTID_PREFIX["201"] = "0200970415"
        msg_matched = "0200970415MSGRT2010001"
        hub_bytes = TestLoadHubZip()._make_zip(_hub_df_di([
            # Có "-" trong TXID (đến sẽ lọc bỏ) và trạng thái ERPO (không phải SCNL) — đi giữ
            # nguyên, phải xuất hiện trong kết quả, không bị lọc trước.
            _hub_row_di("0200970415MSGRT_ERPO", "TXID_A-260901000000004750633167", trang_thai="ERPO"),
            _hub_row_di(msg_matched, "TXID_OK", trang_thai="SCNL", so_tien="100000"),
        ]))
        (tmp_path / hub_filename(ngay, "201", chieu="DI")).write_bytes(hub_bytes)
        pd.DataFrame(_kenh_df([_kenh_row(msg_matched, so_tien="100000")])).to_excel(
            tmp_path / kenh_filename("201", "SPRT", chieu="DI"), index=False, engine="openpyxl")
        # NH 201 có cả SPRT+SPT trong RECONCILE_UNITS — không cấp file kênh SPT thì unit đó
        # "thieu_file_kenh", không ảnh hưởng assertion cho SPRT bên dưới.

        result = pipeline_mod.main_from_dir(tmp_path, ngay=ngay, ma_nh="201", chieu="DI")

        assert result is not None
        sprt = next(d for d in result["don_vi"] if d["loai"] == "SPRT")
        assert sprt["trang_thai"] == "ok"
        # "-" trong TXID KHÔNG bị lọc trước (khác đến) -> cả 2 dòng hub đều xuất hiện trong chi tiết
        assert len(sprt["chi_tiet"]["hub"]) == 2
        assert sprt["canh_bao_trang_thai"] == [], (
            "Chiều đi không áp EXPECTED_ONE_SIDED_STATUSES của đến — không được sinh cảnh báo giả"
        )
        assert sprt["summary"]["so_mon_hub"] == 1, "Bảng 1 cột (1) chỉ đếm SCNL, bỏ qua ERPO"
