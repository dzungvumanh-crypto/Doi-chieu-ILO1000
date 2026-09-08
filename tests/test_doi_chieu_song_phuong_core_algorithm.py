"""Test thuật toán module Đối chiếu Song phương — Hub ↔ Core (chiều ĐẾN).

Test thuần trên DataFrame nhỏ dựng tay, theo tài liệu `đối chiếu Song phương.docx` mục
"Đối chiếu kênh – core" (thực chất hub↔core) + verify dữ liệu thật 21-25/08/2026 (SO_TRACE cần
lstrip('0') dù tài liệu không nói rõ; khoá OSB↔HUB khớp raw không cần lstrip).

Chạy: .venv\\Scripts\\python.exe -m pytest tests/test_doi_chieu_song_phuong_core_algorithm.py -v
"""

import pandas as pd
import pytest

from backend.services import doi_chieu_song_phuong_common as common
from backend.services.doi_chieu_song_phuong_core import export, load_core, load_osb, match, pipeline
from backend.services.doi_chieu_song_phuong_core.config import (
    NHAN_CORE_HUY, NHAN_CORE_THUA, NHAN_HUB_THUA, NHAN_HUB_T_CORE_T, NHAN_QT_OSB, NHAN_QT_VON,
)
from backend.services.doi_chieu_song_phuong_kenh.load_hub import (
    build_key_hub_core, filter_before_reconcile_core,
)

_CORE_COLS = ["TRBRCD", "REFERENCE", "REMARK", "DRAMOUNT", "CRAMOUNT"]


def _core_row(trbrcd="1000", reference="1000API1002080", dramount="500000", cramount="0",
              remark="giao dich test"):
    return {"TRBRCD": trbrcd, "REFERENCE": reference, "REMARK": remark,
            "DRAMOUNT": dramount, "CRAMOUNT": cramount}


def _core_df(rows):
    return pd.DataFrame(rows, columns=_CORE_COLS)


_HUB_COLS = ["NGAY_GIAO_DICH", "CHI_NHANH", "REFHUB", "MSGREF", "MSGSEQ", "TXID",
             "KENH_THANH_TOAN", "TRANG_THAI_LENH", "SO_TIEN", "TRACE", "SESSION",
             "LOAI_LENH_OSB", "NH_GUI", "NOI_DUNG"]


def _hub_row(chi_nhanh="1000", trace="001002080", so_tien="500000", trang_thai="PYED",
             txid="TXID001", msgref="MSG001"):
    return {"NGAY_GIAO_DICH": "21/08/2026", "CHI_NHANH": chi_nhanh, "REFHUB": "REF001",
            "MSGREF": msgref, "MSGSEQ": msgref, "TXID": txid, "KENH_THANH_TOAN": "SP REALTIME",
            "TRANG_THAI_LENH": trang_thai, "SO_TIEN": so_tien, "TRACE": trace,
            "SESSION": "20260821", "LOAI_LENH_OSB": "0", "NH_GUI": "01202001", "NOI_DUNG": "TEST"}


def _hub_df(rows):
    return pd.DataFrame(rows, columns=_HUB_COLS)


def _hub_da_gan_khoa(rows):
    df = _hub_df(rows)
    df = filter_before_reconcile_core(df)
    df[match.KEY_COL] = build_key_hub_core(df)
    return df


def _core_da_gan_khoa(rows):
    df = _core_df(rows)
    so_trace = load_core.build_so_trace(df)
    df[match.KEY_COL] = load_core.build_key_den(df, so_trace)
    return df


# ── load_core: SO_TRACE, KEY, các nhóm không cần khớp hub ─────────────────────

class TestBuildSoTrace:
    def test_bo_prefix_1000api_va_lstrip_so_0(self):
        df = _core_df([_core_row(reference="1000API0001002080")])
        so_trace = load_core.build_so_trace(df)
        assert so_trace.iloc[0] == "1002080"

    def test_khong_co_prefix_thi_rong(self):
        df = _core_df([_core_row(reference="1000OSB")])
        so_trace = load_core.build_so_trace(df)
        assert so_trace.iloc[0] == ""


class TestBuildKeyDen:
    def test_dramount_ngan_nghin_cham_khong_bi_cat(self):
        """Regression: '180.000' phải ra 180000 khi build KEY, không bị to_numeric()
        trần cắt còn 180 (xem backend/services/ach/so_tien.py)."""
        df = _core_df([_core_row(trbrcd="1000", reference="1000API111", dramount="180.000")])
        so_trace = load_core.build_so_trace(df)
        key = load_core.build_key_den(df, so_trace)
        assert key.iloc[0].endswith("180000")

    def test_dramount_khong_hop_le_raise(self):
        df = _core_df([_core_row(trbrcd="1000", reference="1000API111", dramount="1.5")])
        so_trace = load_core.build_so_trace(df)
        with pytest.raises(ValueError, match="không đúng định dạng"):
            load_core.build_key_den(df, so_trace)


class TestMaskHuyCungNgay:
    def test_phat_hien_cap_huy(self):
        df = _core_df([
            _core_row(trbrcd="1000", reference="1000API111", dramount="500000"),
            _core_row(trbrcd="1000", reference="1000API111", dramount="-500000"),
        ])
        mask = load_core.mask_huy_cung_ngay(df)
        assert mask.tolist() == [True, True]

    def test_khong_trung_thi_khong_huy(self):
        df = _core_df([
            _core_row(trbrcd="1000", reference="1000API111", dramount="500000"),
            _core_row(trbrcd="1000", reference="1000API222", dramount="500000"),
        ])
        mask = load_core.mask_huy_cung_ngay(df)
        assert mask.tolist() == [False, False]

    def test_trung_nhung_tong_khac_0_khong_phai_huy(self):
        df = _core_df([
            _core_row(trbrcd="1000", reference="1000API111", dramount="500000"),
            _core_row(trbrcd="1000", reference="1000API111", dramount="300000"),
        ])
        mask = load_core.mask_huy_cung_ngay(df)
        assert mask.tolist() == [False, False]

    def test_dramount_ngan_nghin_phay_van_phat_hien_dung_cap_huy(self):
        """'180,000' (dấu phẩy) không được to_numeric() coerce về 0 làm sai tổng nhóm."""
        df = _core_df([
            _core_row(trbrcd="1000", reference="1000API111", dramount="180,000"),
            _core_row(trbrcd="1000", reference="1000API111", dramount="-180,000"),
        ])
        mask = load_core.mask_huy_cung_ngay(df)
        assert mask.tolist() == [True, True]


class TestMaskQtOsb:
    def test_dung_reference_1000osb(self):
        df = _core_df([_core_row(reference="1000OSB"), _core_row(reference="1000API111")])
        mask = load_core.mask_qt_osb(df)
        assert mask.tolist() == [True, False]


class TestMaskQtVon:
    def test_khong_phan_biet_hoa_thuong(self):
        df = _core_df([
            _core_row(trbrcd="1000", remark="QUYET TOAN VON TTDT SP GIUA A VA B"),
            _core_row(trbrcd="1000", remark="Quyet toan von trong TTDTSP"),
            _core_row(trbrcd="1000", remark="giao dich thuong"),
            _core_row(trbrcd="2000", remark="Quyet toan von"),
        ])
        mask = load_core.mask_qt_von(df)
        assert mask.tolist() == [True, True, False, False]


# ── load_osb: khoá 4 ký tự CN thực hiện + Mã giao dịch ─────────────────────────

class TestBuildKeyOsb:
    def test_lay_4_ky_tu_dau(self):
        df = pd.DataFrame([
            {"CN thực hiện": "5507 - Chi nhánh Sở Sao", "Mã giao dịch": "000874279",
             "Ngày hạch toán": "21/08/2026"},
        ])
        khoa = load_osb.build_key_osb(df)
        assert khoa.iloc[0] == "5507000874279"


# ── HUB cho nhánh core: filter_before_reconcile_core + build_key_hub_core ──────

class TestFilterBeforeReconcileCore:
    def test_loai_rjct(self):
        df = _hub_df([
            _hub_row(txid="TXID001", trang_thai="PYED"),
            _hub_row(txid="TXID002", trang_thai="RJCT"),
        ])
        logs = []
        out = filter_before_reconcile_core(df, log=logs.append)
        assert len(out) == 1
        assert out.iloc[0]["TRANG_THAI_LENH"] == "PYED"
        assert any("RJCT" in m for m in logs)

    def test_van_loai_gach_ngang_va_cap_txid_trace(self):
        df = _hub_df([
            _hub_row(txid="TXID001-260822000000004750633167", trang_thai="WFPG"),
            _hub_row(txid="TXID002", trace="9999999", trang_thai="RFED"),
            _hub_row(txid="TXID002", trace="9999999", trang_thai="RFED"),
        ])
        out = filter_before_reconcile_core(df)
        assert len(out) == 0


class TestBuildKeyHubCore:
    def test_lstrip_so_0_o_trace(self):
        df = _hub_df([_hub_row(chi_nhanh="1000", trace="001002080", so_tien="500000")])
        khoa = build_key_hub_core(df)
        assert khoa.iloc[0] == "10001002080500000"

    def test_so_tien_ngan_nghin_cham_khong_bi_cat(self):
        """Regression: '180.000' phải ra 180000 khi build KEY, không bị to_numeric()
        trần cắt còn 180 (xem backend/services/ach/so_tien.py)."""
        df = _hub_df([_hub_row(chi_nhanh="1000", trace="001002080", so_tien="180.000")])
        khoa = build_key_hub_core(df)
        assert khoa.iloc[0].endswith("180000")

    def test_so_tien_khong_hop_le_raise(self):
        df = _hub_df([_hub_row(chi_nhanh="1000", trace="001002080", so_tien="1.5")])
        with pytest.raises(ValueError, match="không đúng định dạng"):
            build_key_hub_core(df)


# ── match.classify_core ──────────────────────────────────────────────────────

class TestClassifyCore:
    def test_khop_hub_t(self):
        core = _core_df([_core_row(trbrcd="1000", reference="1000API1002080", dramount="500000")])
        hub_t = _hub_da_gan_khoa([_hub_row(chi_nhanh="1000", trace="001002080", so_tien="500000")])
        nhan = match.classify_core(core, {0: hub_t})
        assert nhan.iloc[0] == NHAN_HUB_T_CORE_T

    def test_khop_hub_t1_khi_khong_co_hub_t(self):
        core = _core_df([_core_row(trbrcd="1000", reference="1000API1002080", dramount="500000")])
        hub_t1 = _hub_da_gan_khoa([_hub_row(chi_nhanh="1000", trace="001002080", so_tien="500000")])
        nhan = match.classify_core(core, {-1: hub_t1})
        assert nhan.iloc[0] == "hub T-1 core T"

    def test_huy_cung_ngay_uu_tien_truoc_khop_hub(self):
        """Dòng thuộc cặp huỷ cùng ngày phải KHÔNG được đem đi khớp hub, kể cả khi trùng khoá."""
        core = _core_df([
            _core_row(trbrcd="1000", reference="1000API111", dramount="500000"),
            _core_row(trbrcd="1000", reference="1000API111", dramount="-500000"),
        ])
        hub_t = _hub_da_gan_khoa([_hub_row(chi_nhanh="1000", trace="111", so_tien="500000")])
        nhan = match.classify_core(core, {0: hub_t})
        assert nhan.tolist() == [NHAN_CORE_HUY, NHAN_CORE_HUY]

    def test_qt_osb(self):
        core = _core_df([_core_row(reference="1000OSB", dramount="25000000000")])
        nhan = match.classify_core(core, {})
        assert nhan.iloc[0] == NHAN_QT_OSB

    def test_qt_von(self):
        core = _core_df([_core_row(trbrcd="1000", reference="1000API999",
                                    remark="Quyet toan von giua A va B", dramount="90000000000")])
        nhan = match.classify_core(core, {})
        assert nhan.iloc[0] == NHAN_QT_VON

    def test_con_lai_la_core_thua(self):
        core = _core_df([_core_row(trbrcd="1000", reference="1000API999", dramount="500000")])
        nhan = match.classify_core(core, {})
        assert nhan.iloc[0] == NHAN_CORE_THUA


# ── match.classify_hub ───────────────────────────────────────────────────────

class TestClassifyHub:
    def test_khop_core_t(self):
        hub = _hub_da_gan_khoa([_hub_row(chi_nhanh="1000", trace="001002080", so_tien="500000")])
        core_t = _core_da_gan_khoa([_core_row(trbrcd="1000", reference="1000API1002080", dramount="500000")])
        nhan = match.classify_hub(hub, {0: core_t}, None)
        assert nhan.iloc[0] == NHAN_HUB_T_CORE_T

    def test_khop_core_t1_khi_khong_co_core_t(self):
        hub = _hub_da_gan_khoa([_hub_row(chi_nhanh="1000", trace="001002080", so_tien="500000")])
        core_t1 = _core_da_gan_khoa([_core_row(trbrcd="1000", reference="1000API1002080", dramount="500000")])
        nhan = match.classify_hub(hub, {1: core_t1}, None)
        assert nhan.iloc[0] == "hub T core T+1"

    def test_khop_osb_gan_nhan_ngay_hach_toan(self):
        hub = _hub_da_gan_khoa([_hub_row(chi_nhanh="5507", trace="000874279", so_tien="1000000")])
        osb = pd.DataFrame([
            {"CN thực hiện": "5507 - Chi nhánh Sở Sao", "Mã giao dịch": "000874279",
             "Ngày hạch toán": "21/08/2026"},
        ])
        nhan = match.classify_hub(hub, {}, osb)
        assert nhan.iloc[0] == "OSB & 21/08/2026"

    def test_con_lai_la_hub_thua(self):
        hub = _hub_da_gan_khoa([_hub_row(chi_nhanh="1000", trace="999", so_tien="500000")])
        nhan = match.classify_hub(hub, {}, None)
        assert nhan.iloc[0] == NHAN_HUB_THUA


# ── export.build_tong_hop ────────────────────────────────────────────────────

class TestBuildTongHop:
    def test_dem_va_cong_dung_theo_nhan(self):
        core = _core_df([
            _core_row(dramount="500000"), _core_row(dramount="300000"),
        ])
        core["KETQUADOICHIEU"] = [NHAN_HUB_T_CORE_T, NHAN_CORE_THUA]
        hub = _hub_df([_hub_row(so_tien="500000")])
        hub["KETQUADOICHIEU"] = [NHAN_HUB_T_CORE_T]

        tong = export.build_tong_hop(core, hub)
        hang_khop = tong[tong["Nhãn (KETQUADOICHIEU)"] == NHAN_HUB_T_CORE_T].iloc[0]
        assert hang_khop["Số dòng CORE"] == 1
        assert hang_khop["Số tiền CORE"] == 500000
        assert hang_khop["Số dòng HUB"] == 1
        assert hang_khop["Số tiền HUB"] == 500000

        hang_tong = tong[tong["Nhãn (KETQUADOICHIEU)"] == "Tổng cộng"].iloc[0]
        assert hang_tong["Số dòng CORE"] == 2
        assert hang_tong["Số tiền CORE"] == 800000


# ── pipeline: dò file theo ngày (T-3..T+3), kể cả file để rời ở thư mục cha ────

class TestTimFile:
    def test_cong_ngay(self):
        assert common.cong_ngay("20260823", -1) == "20260822"
        assert common.cong_ngay("20260823", 3) == "20260826"

    def test_thu_muc_ngay_ung_vien_khong_so_0_dau(self, tmp_path):
        assert common.thu_muc_ngay_ung_vien(tmp_path, "20260823")[0].name == "23.8"
        assert common.thu_muc_ngay_ung_vien(tmp_path, "20260905")[0].name == "5.9"

    def test_uu_tien_thu_muc_ngay_truoc(self, tmp_path):
        (tmp_path / "23.8").mkdir()
        (tmp_path / "23.8" / "GL02_20260823_1000.zip").write_bytes(b"x")
        loai, p = pipeline._tim_file_core_hoac_csv(tmp_path, "20260823", "202", 0)
        assert loai == "zip"
        assert p.parent.name == "23.8"

    def test_thu_muc_ngay_co_hau_to_nam(self, tmp_path):
        """Bộ dữ liệu NH 201/311 (thư mục TRANG/) đặt tên `D.M.YYYY` (VD `24.8.2026`) thay vì
        `D.M` — phải tự dò ra được, không cần đổi tên thư mục tay."""
        (tmp_path / "24.8.2026").mkdir()
        (tmp_path / "24.8.2026" / "GL02_20260824_1000.zip").write_bytes(b"x")
        loai, p = pipeline._tim_file_core_hoac_csv(tmp_path, "20260824", "201", 0)
        assert loai == "zip"
        assert p.parent.name == "24.8.2026"

    def test_roi_o_thu_muc_cha_van_tim_thay(self, tmp_path):
        """File 20.8 để rời ở gốc, không có thư mục 20.8/ riêng — quyết định 2026-08-26."""
        (tmp_path / "GL02_20260820_1000.zip").write_bytes(b"x")
        loai, p = pipeline._tim_file_core_hoac_csv(tmp_path, "20260820", "202", 0)
        assert loai == "zip"
        assert p.parent == tmp_path

    def test_khong_thay_thi_none(self, tmp_path):
        assert pipeline._tim_file_core_hoac_csv(tmp_path, "20260820", "202", 0) is None

    def test_uu_tien_csv_da_phan_loai_hon_zip(self, tmp_path):
        """Quyết định 2026-08-28: có sẵn `{ma_nh}_DEN.csv` thì dùng thẳng, không giải mã lại
        GL02 zip dù cả 2 cùng tồn tại — giảm số lần giải mã AES tốn RAM (card 91)."""
        (tmp_path / "23.8").mkdir()
        (tmp_path / "23.8" / "GL02_20260823_1000.zip").write_bytes(b"x")
        (tmp_path / "23.8" / "202_DEN.csv").write_bytes(b"x")
        loai, p = pipeline._tim_file_core_hoac_csv(tmp_path, "20260823", "202", 0)
        assert loai == "csv"
        assert p.name == "202_DEN.csv"

    def _viet_csv_trdate(self, path, *trdates):
        """Ghi 1 file CSV core hợp lệ, mỗi dòng 1 giá trị TRDATE trong `trdates` (nhiều giá trị →
        file có TRDATE lẫn nhiều ngày)."""
        rows = [{**_core_row(), "TRDATE": d} for d in trdates]
        pd.DataFrame(rows, columns=["TRDATE"] + _CORE_COLS).to_csv(path, index=False)

    def test_1_file_1_offset_0_dung_duong_nhanh_khong_can_doc_noi_dung(self, tmp_path):
        """Đúng 1 file khớp + hỏi offset 0 (ngày T) → tin luôn, KHÔNG mở đọc nội dung (đường nhanh,
        giữ hiệu năng cho trường hợp phổ biến nhất)."""
        (tmp_path / "202_DEN.csv").write_bytes(b"x")
        loai, p = pipeline._tim_file_core_hoac_csv(tmp_path, "20260823", "202", 0)
        assert loai == "csv" and p.name == "202_DEN.csv"

    def test_1_file_offset_khac_0_tu_gan_dung_theo_trdate_that(self, tmp_path):
        """2026-09-08: báo lỗi thật của người dùng — module "Đối chiếu đến" không chạy được khi
        upload CSV. Nguyên nhân: 1 thư mục có CSV riêng cho ngày T VÀ ngày T+1 (2 đợt xuất trong 1
        phiên) — luật cũ "CSV chỉ dùng offset 0" chặn cứng, không tự nhận được CSV của T+1 dù đã có
        sẵn. Nay đọc TRDATE thật bên trong để tự gán đúng offset, không còn bị chặn."""
        self._viet_csv_trdate(tmp_path / "202_DEN_20260823_0900.csv", "20260823")
        self._viet_csv_trdate(tmp_path / "202_DEN_20260824_0900.csv", "20260824")

        loai, p = pipeline._tim_file_core_hoac_csv(tmp_path, "20260823", "202", 0)
        assert loai == "csv" and p.name == "202_DEN_20260823_0900.csv"

        loai, p = pipeline._tim_file_core_hoac_csv(tmp_path, "20260824", "202", 1)
        assert loai == "csv" and p.name == "202_DEN_20260824_0900.csv"

        # Không file nào có TRDATE=20260825 (offset 2) → không tự nhận nhầm, trả None
        assert pipeline._tim_file_core_hoac_csv(tmp_path, "20260825", "202", 2) is None

    def test_offset_khac_0_van_nhan_zip_khi_khong_co_csv_dung_ngay(self, tmp_path):
        """CSV có sẵn nhưng TRDATE của nó không khớp offset đang hỏi → rơi về GL02 zip đúng ngày,
        không dùng liều CSV sai ngày (mặt còn lại của luật cũ vẫn phải giữ, thêm ở review
        2026-09-03: trước khi vá, CSV được xét TRƯỚC nên thắng cả ZIP đúng ngày nằm sẵn đó)."""
        self._viet_csv_trdate(tmp_path / "202_DEN.csv", "20260823")
        (tmp_path / "GL02_20260824_1000.zip").write_bytes(b"x")
        loai, p = pipeline._tim_file_core_hoac_csv(tmp_path, "20260824", "202", 1)
        assert loai == "zip" and p.name == "GL02_20260824_1000.zip"

    def test_nhieu_csv_cung_trdate_khong_tu_chon(self, tmp_path):
        """2 file CSV khác tên nhưng TRDATE thật BÊN TRONG lại trùng 1 ngày — vẫn phải chặn như
        luật cũ (không tự chọn), chỉ khác chỗ xét trên TRDATE thật thay vì xét trên việc "có nhiều
        file cùng khớp tên" như trước (quyết định 2026-08-30: nhiều người dùng có thể trỏ chung 1
        thư mục server cùng lúc, không tự đoán "mới nhất")."""
        (tmp_path / "23.8").mkdir()
        self._viet_csv_trdate(tmp_path / "23.8" / "202_DEN_20260823_0900.csv", "20260823")
        self._viet_csv_trdate(tmp_path / "23.8" / "202_DEN_20260823_1400.csv", "20260823")
        logs = []
        assert pipeline._tim_file_core_hoac_csv(
            tmp_path, "20260823", "202", 0, logs.append) is None
        assert any("KHÔNG tự chọn" in m for m in logs)

    def test_csv_trdate_lan_nhieu_ngay_trong_1_file_bi_loai_khong_crash(self, tmp_path):
        """1 file tự nó có TRDATE lẫn nhiều ngày (dữ liệu hỏng/gộp nhầm) — loại khỏi việc gán
        offset, log lỗi rõ, KHÔNG crash cả job và KHÔNG đoán dùng 1 trong các ngày đó."""
        self._viet_csv_trdate(tmp_path / "202_DEN_lan_ngay.csv", "20260823", "20260824")
        logs = []
        assert pipeline._tim_file_core_hoac_csv(
            tmp_path, "20260824", "202", 1, logs.append) is None
        assert any("TRDATE lẫn" in m for m in logs)

    def test_file_hong_khong_doc_duoc_thi_bo_qua_khong_crash(self, tmp_path):
        """File rác (không đọc được cột TRDATE) gặp ở offset khác 0 — log lỗi rồi bỏ qua, không
        làm crash toàn bộ job (job vẫn tiếp tục với các offset/nhánh khác)."""
        (tmp_path / "202_DEN_hong.csv").write_bytes(b"khong phai csv hop le")
        (tmp_path / "202_DEN_that.csv").write_text("TRDATE\n20260824\n", encoding="utf-8")
        logs = []
        loai, p = pipeline._tim_file_core_hoac_csv(
            tmp_path, "20260824", "202", 1, logs.append)
        assert loai == "csv" and p.name == "202_DEN_that.csv"
        assert any("Không đọc được cột TRDATE" in m for m in logs)

    def test_nhieu_hub_cung_khop_khong_tu_chon(self, tmp_path):
        """Như trên, áp dụng cho `_tim_file_hub` (dùng chung ở cả 2 bước Kênh↔Hub và Hub↔Core)."""
        (tmp_path / "23.8").mkdir()
        (tmp_path / "23.8" / "doichieugd_20260823__05_DEN_9999_N.zip").write_bytes(b"x")
        (tmp_path / "23.8" / "doichieugd_20260823__05_DEN_9999_N_v2.zip").write_bytes(b"x")
        assert pipeline._tim_file_hub(tmp_path, "20260823", "202") is None
