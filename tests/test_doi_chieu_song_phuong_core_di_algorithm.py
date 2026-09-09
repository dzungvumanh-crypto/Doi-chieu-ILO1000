"""Test thuật toán module Đối chiếu Song phương — Hub ↔ Core (chiều ĐI).

Test thuần trên DataFrame nhỏ dựng tay, theo tài liệu `Đối chiếu SP chiều đi.docx` + khảo sát
dữ liệu thật NH 201/311 ngày 01-02/09/2026 (xem PLAN.md chiều đi).

⚠️ Các test có hậu tố `_CHUA_verify_du_lieu_that` phủ đúng 5 nhánh mà bộ dữ liệu thật KHÔNG có
ca nào để kiểm chứng (PLAN.md mục 6). Chúng chứng minh code chạy đúng theo CÂU CHỮ tài liệu,
KHÔNG chứng minh tài liệu mô tả đúng thực tế — đừng dùng chúng để nói "đã verify".

Chạy: .venv\\Scripts\\python.exe -m pytest tests/test_doi_chieu_song_phuong_core_di_algorithm.py -v
"""

import pandas as pd
import pytest

from backend.services import doi_chieu_song_phuong_common as common
from backend.services.doi_chieu_song_phuong_core import load_core, load_osb
from backend.services.doi_chieu_song_phuong_core_di import export, match, pipeline
from backend.services.doi_chieu_song_phuong_core_di.config import (
    NHAN_CORE_HUY_CHEO_NGAY, NHAN_CORE_HUY_CUNG_NGAY, NHAN_CORE_THUA, NHAN_HUB_CHO_DUYET,
    NHAN_HUB_LENH_LOI, NHAN_HUB_T_CORE_T, NHAN_HUB_THUA, NHAN_LENH_FX, NHAN_QT_OSB, NHAN_QT_VON,
)
from backend.services.doi_chieu_song_phuong_kenh.load_hub import (
    build_key_hub_core_di, mask_lenh_fx, se_trace_hieu_dung,
)

# ─── Dữ liệu dựng tay ─────────────────────────────────────────────────────────

_CORE_COLS = ["TRDATE", "TRBRCD", "USERID", "REFERENCE", "REMARK", "DRAMOUNT", "CRAMOUNT"]


def _core_row(trbrcd="1000", userid="1000API01", reference="1000API1002080",
              remark="giao dich test", dramount="0", cramount="500000"):
    """DRAMOUNT mặc định "0" — dữ liệu thật CSV `{ma_nh}_DI*.csv` luôn như vậy (100% dòng)."""
    return {"TRDATE": "20260901", "TRBRCD": trbrcd, "USERID": userid, "REFERENCE": reference,
            "REMARK": remark, "DRAMOUNT": dramount, "CRAMOUNT": cramount}


def _core_df(rows):
    return pd.DataFrame(rows, columns=_CORE_COLS)


def _core_da_gan_khoa(rows):
    df = _core_df(rows)
    so_trace = load_core.build_so_trace(df)
    df[match.KEY_COL] = load_core.build_key_di(df, so_trace)
    return df


# HUB chiều đi có 17 cột — thêm SE_TRACE, MA_GIAO_DICH, NGAY_KENH_TRA, và dùng NH_NHAN
# (chiều đến dùng NH_GUI). NGAY_KENH_TRA nằm SAU NOI_DUNG, không phải cột cuối như "đến".
_HUB_COLS = ["NGAY_GIAO_DICH", "CHI_NHANH", "REFHUB", "MSGREF", "MSGSEQ", "TXID",
             "KENH_THANH_TOAN", "TRANG_THAI_LENH", "SO_TIEN", "TRACE", "SE_TRACE", "SESSION",
             "LOAI_LENH_OSB", "NH_NHAN", "MA_GIAO_DICH", "NOI_DUNG", "NGAY_KENH_TRA"]


def _hub_row(chi_nhanh="1000", trace="1002080", se_trace="", so_tien="500000",
             trang_thai="SCNL", txid="TXID001", msgref="MSG001"):
    return {"NGAY_GIAO_DICH": "01/09/2026", "CHI_NHANH": chi_nhanh, "REFHUB": "REF001",
            "MSGREF": msgref, "MSGSEQ": msgref, "TXID": txid, "KENH_THANH_TOAN": "SP REALTIME",
            "TRANG_THAI_LENH": trang_thai, "SO_TIEN": so_tien, "TRACE": trace,
            "SE_TRACE": se_trace, "SESSION": "20260901", "LOAI_LENH_OSB": "  ",
            "NH_NHAN": "01202001", "MA_GIAO_DICH": "MGD001", "NOI_DUNG": "TEST",
            "NGAY_KENH_TRA": "01/09/2026"}


def _hub_df(rows):
    return pd.DataFrame(rows, columns=_HUB_COLS)


def _hub_da_gan_khoa(rows, log=None):
    """Bản HUB đã lọc SCNL + gắn `_KEY` — đúng thứ tự pipeline làm."""
    df = pipeline._loc_scnl(_hub_df(rows), log or (lambda m: None))
    df[match.KEY_COL] = build_key_hub_core_di(df)
    return df


def _osb_row(cn="5507 - Chi nhánh Sở Sao", ma_gd="000874279", ngay="01/09/2026", so_tien="1000000"):
    return {"CN thực hiện": cn, "Mã giao dịch": ma_gd, "Ngày hạch toán": ngay, "Số tiền": so_tien}


# ── load_hub: mask_lenh_fx / se_trace_hieu_dung / build_key_hub_core_di ───────

class TestMaskLenhFx:
    def test_thieu_ca_trace_lan_se_trace_la_lenh_fx(self):
        df = _hub_df([_hub_row(trace="", se_trace="")])
        assert mask_lenh_fx(df).tolist() == [True]

    def test_co_trace_thi_khong_phai_lenh_fx(self):
        df = _hub_df([_hub_row(trace="1002080", se_trace="")])
        assert mask_lenh_fx(df).tolist() == [False]

    def test_chi_co_se_trace_cung_khong_phai_lenh_fx(self):
        df = _hub_df([_hub_row(trace="", se_trace="9998888")])
        assert mask_lenh_fx(df).tolist() == [False]

    def test_khoang_trang_thuan_van_coi_la_rong(self):
        df = _hub_df([_hub_row(trace="   ", se_trace="  ")])
        assert mask_lenh_fx(df).tolist() == [True]


class TestSeTraceHieuDung:
    def test_se_trace_rong_thi_dung_trace_thay(self):
        """Dữ liệu thật: cột SE_TRACE nguồn RỖNG 100% (500.058/500.058 dòng, cả 201 lẫn 311) —
        đây là nhánh chạy trong thực tế, không phải nhánh dự phòng hiếm gặp."""
        df = _hub_df([_hub_row(trace="1002080", se_trace="")])
        assert se_trace_hieu_dung(df).tolist() == ["1002080"]

    def test_co_se_trace_thi_uu_tien_se_trace(self):
        df = _hub_df([_hub_row(trace="1002080", se_trace="9998888")])
        assert se_trace_hieu_dung(df).tolist() == ["9998888"]


class TestBuildKeyHubCoreDi:
    def test_ghep_chi_nhanh_se_trace_so_tien(self):
        df = _hub_df([_hub_row(chi_nhanh="1000", trace="1002080", so_tien="500000")])
        assert build_key_hub_core_di(df).iloc[0] == "10001002080500000"

    def test_lstrip_so_0_dau_se_trace(self):
        """Regression 2026-09-03: bản đầu KHÔNG lstrip('0') SE_TRACE — verify dữ liệu thật NH 201
        01/09/2026 cho thấy 0/972 dòng khớp (đáng lẽ 912/972) vì SO_TRACE phía CORE
        (`load_core.build_so_trace()`) đã lstrip('0') sẵn còn phía HUB thì không, lệch khoá."""
        df = _hub_df([_hub_row(chi_nhanh="1000", trace="0001002080", so_tien="500000")])
        assert build_key_hub_core_di(df).iloc[0] == "10001002080500000"

    def test_so_tien_ngan_nghin_cham_khong_bi_cat(self):
        """Regression chung của dự án: '180.000' phải ra 180000, không bị to_numeric() cắt còn
        180 (xem backend/services/ach/so_tien.py)."""
        df = _hub_df([_hub_row(trace="1002080", so_tien="180.000")])
        assert build_key_hub_core_di(df).iloc[0].endswith("180000")

    def test_so_tien_khong_hop_le_raise(self):
        df = _hub_df([_hub_row(trace="1002080", so_tien="1.5")])
        with pytest.raises(ValueError, match="không đúng định dạng"):
            build_key_hub_core_di(df)


# ── load_core.build_key_di (CRAMOUNT, không phải DRAMOUNT) ───────────────────

class TestBuildKeyDi:
    def test_dung_cramount_khong_dung_dramount(self):
        df = _core_df([_core_row(trbrcd="1000", reference="1000API1002080",
                                  dramount="0", cramount="500000")])
        so_trace = load_core.build_so_trace(df)
        assert load_core.build_key_di(df, so_trace).iloc[0] == "10001002080500000"

    def test_cramount_ngan_nghin_cham_khong_bi_cat(self):
        df = _core_df([_core_row(reference="1000API111", cramount="180.000")])
        so_trace = load_core.build_so_trace(df)
        assert load_core.build_key_di(df, so_trace).iloc[0].endswith("180000")

    def test_cramount_o_trong_coi_la_0(self):
        """Ô rỗng/NaN ở cột tiền — bắt buộc test dù dữ liệu mẫu không có (checklist dự án mục 8:
        lỗi này đã lặp ở PR#66/#69). `doc_so_tien()` coi ô trống là 0 + ghi log, KHÔNG raise."""
        df = _core_df([_core_row(reference="1000API111", cramount=""),
                       _core_row(reference="1000API222", cramount=None)])
        so_trace = load_core.build_so_trace(df)
        khoa = load_core.build_key_di(df, so_trace)
        assert khoa.tolist() == ["10001110", "10002220"]

    def test_dramount_rong_khong_anh_huong_khoa_di(self):
        """Chiều đi KHÔNG đọc DRAMOUNT ở bất kỳ bước nào — ô trống/NaN ở đó không được làm
        hỏng khoá lẫn phân loại."""
        df = _core_df([_core_row(reference="1000API111", dramount="", cramount="500000")])
        so_trace = load_core.build_so_trace(df)
        assert load_core.build_key_di(df, so_trace).iloc[0] == "1000111500000"
        assert match.classify_core_di(df, {}).iloc[0] == NHAN_CORE_THUA


# ── match: huỷ cùng ngày / OSB / lệnh fx phía core ───────────────────────────

class TestMaskHuyCungNgayDi:
    def test_cap_huy_tong_cramount_bang_0(self):
        df = _core_df([
            _core_row(reference="1000API111", cramount="500000"),
            _core_row(reference="1000API111", cramount="-500000"),
        ])
        assert match.mask_huy_cung_ngay_di(df).tolist() == [True, True]

    def test_trung_khoa_nhung_tong_khac_0_khong_phai_huy(self):
        df = _core_df([
            _core_row(reference="1000API111", cramount="500000"),
            _core_row(reference="1000API111", cramount="300000"),
        ])
        assert match.mask_huy_cung_ngay_di(df).tolist() == [False, False]

    def test_khong_trung_khoa_thi_khong_huy(self):
        df = _core_df([
            _core_row(reference="1000API111", cramount="500000"),
            _core_row(reference="1000API222", cramount="-500000"),
        ])
        assert match.mask_huy_cung_ngay_di(df).tolist() == [False, False]

    def test_dung_cramount_chu_khong_phai_dramount(self):
        """Bẫy chí mạng: DRAMOUNT của CSV `_DI*.csv` LUÔN = "0" — nếu xét DRAMOUNT thì mọi nhóm
        trùng khoá đều "tổng = 0", cả file bị gán nhãn huỷ mà không có lỗi nào báo ra."""
        df = _core_df([
            _core_row(reference="1000API111", dramount="0", cramount="500000"),
            _core_row(reference="1000API111", dramount="0", cramount="700000"),
        ])
        assert match.mask_huy_cung_ngay_di(df).tolist() == [False, False]

    def test_cramount_o_trong_coi_la_0(self):
        df = _core_df([
            _core_row(reference="1000API111", cramount=""),
            _core_row(reference="1000API111", cramount=""),
        ])
        assert match.mask_huy_cung_ngay_di(df).tolist() == [True, True]


class TestMaskUseridCore:
    def test_qt_osb_theo_userid(self):
        df = _core_df([_core_row(userid="1000OSB"), _core_row(userid="1000API01")])
        assert match.mask_qt_osb_di(df).tolist() == [True, False]

    def test_lenh_fx_khi_userid_khong_chua_api(self):
        df = _core_df([_core_row(userid="1000FX01"), _core_row(userid="1000API01"),
                       _core_row(userid="1000OSB")])
        assert match.mask_lenh_fx_core(df).tolist() == [True, False, True]


# ── CORE-side waterfall (Bước 2.2-2.19) ──────────────────────────────────────

class TestClassifyCoreDi:
    def test_buoc2_huy_cung_ngay_co_ca_that_dinh_chinh_plan(self):
        """ĐÍNH CHÍNH PLAN.md mục 6: nhánh này CÓ ca thật, không phải "chưa verify". PLAN suy ra
        sai từ "không dòng nào CRAMOUNT = 0" — điều kiện tài liệu là TỔNG của NHÓM = 0, một cặp
        +X/−X thì mỗi dòng đều khác 0. Chạy thật 01/09/2026: 24 cặp NH 201, 14 cặp NH 311.

        Test tự dựng vẫn giữ để chốt thứ tự: phải chặn TRƯỚC bước khớp HUB, kể cả khi khoá vẫn
        khớp được HUB."""
        core = _core_df([
            _core_row(reference="1000API111", cramount="500000"),
            _core_row(reference="1000API111", cramount="-500000"),
        ])
        hub_t = _hub_da_gan_khoa([_hub_row(chi_nhanh="1000", trace="111", so_tien="500000")])
        nhan = match.classify_core_di(core, {0: hub_t})
        assert nhan.tolist() == [NHAN_CORE_HUY_CUNG_NGAY, NHAN_CORE_HUY_CUNG_NGAY]

    def test_buoc3_gd_qt_osb(self):
        core = _core_df([_core_row(userid="1000OSB", reference="1000OSB",
                                    cramount="25000000000")])
        assert match.classify_core_di(core, {}).iloc[0] == NHAN_QT_OSB

    def test_buoc4_lenh_fx_phia_core_CHUA_verify_du_lieu_that(self):
        """PLAN.md mục 6 — 511.377/511.378 dòng thật đều có "API" trong USERID; dòng còn lại
        chính là dòng OSB (đã bị Bước 3 bắt trước). Không ca thật nào cho nhánh này."""
        core = _core_df([_core_row(userid="1000FX01", reference="1000API1002080")])
        assert match.classify_core_di(core, {}).iloc[0] == NHAN_LENH_FX

    def test_osb_uu_tien_truoc_lenh_fx(self):
        """Dòng OSB cũng KHÔNG chứa "API" trong USERID — nếu đảo thứ tự 2 bước, điện quyết toán
        OSB hàng ngày sẽ bị gán nhầm là "lệnh fx"."""
        core = _core_df([_core_row(userid="1000OSB", reference="1000OSB")])
        assert match.classify_core_di(core, {}).iloc[0] == NHAN_QT_OSB

    def test_buoc5_khop_hub_t(self):
        core = _core_df([_core_row(reference="1000API1002080", cramount="500000")])
        hub_t = _hub_da_gan_khoa([_hub_row(chi_nhanh="1000", trace="1002080", so_tien="500000")])
        assert match.classify_core_di(core, {0: hub_t}).iloc[0] == NHAN_HUB_T_CORE_T

    @pytest.mark.parametrize("off,nhan_mong_doi", [
        (-1, "hub T-1 core T"), (-2, "hub T-2 core T"), (-3, "hub T-3 core T"),
    ])
    def test_buoc6_8_khop_hub_lui_ngay(self, off, nhan_mong_doi):
        core = _core_df([_core_row(reference="1000API1002080", cramount="500000")])
        hub = _hub_da_gan_khoa([_hub_row(chi_nhanh="1000", trace="1002080", so_tien="500000")])
        assert match.classify_core_di(core, {off: hub}).iloc[0] == nhan_mong_doi

    def test_uu_tien_hub_t_truoc_hub_lui_ngay(self):
        core = _core_df([_core_row(reference="1000API1002080", cramount="500000")])
        hub = _hub_da_gan_khoa([_hub_row(chi_nhanh="1000", trace="1002080", so_tien="500000")])
        nhan = match.classify_core_di(core, {0: hub, -1: hub, -2: hub})
        assert nhan.iloc[0] == NHAN_HUB_T_CORE_T

    @pytest.mark.parametrize("off", [-1, -2, -3, 1, 2, 3])
    def test_buoc9_10_huy_cheo_ngay_CHUA_verify_du_lieu_that(self, off):
        """PLAN.md mục 6 — bộ dữ liệu mẫu chỉ có ĐÚNG 1 ngày, không có file CORE nào cho
        T-3..T-1/T+1..T+3, nên cả 6 nhãn huỷ chéo ngày chưa từng chạy qua dữ liệu thật.

        Điều kiện docx: cùng `TRBRCD & REFERENCE` (SAU KHI đã bỏ tiền tố ở CẢ 2 phía) và tổng
        CRAMOUNT hai dòng = 0."""
        core_t = _core_df([_core_row(reference="1000API111", cramount="500000")])
        core_khac = _core_df([_core_row(reference="1000API111", cramount="-500000")])
        nhan = match.classify_core_di(core_t, {}, {off: core_khac})
        assert nhan.iloc[0] == NHAN_CORE_HUY_CHEO_NGAY[off]

    def test_huy_cheo_ngay_doi_hoi_tong_bang_0_CHUA_verify_du_lieu_that(self):
        """Cùng TRBRCD&REFERENCE nhưng tổng ≠ 0 thì KHÔNG phải huỷ — phải rơi tiếp xuống dưới."""
        core_t = _core_df([_core_row(reference="1000API111", cramount="500000")])
        core_khac = _core_df([_core_row(reference="1000API111", cramount="300000")])
        assert match.classify_core_di(core_t, {}, {-1: core_khac}).iloc[0] == NHAN_CORE_THUA

    def test_huy_cheo_ngay_bo_tien_to_reference_ca_2_phia_CHUA_verify_du_lieu_that(self):
        """PLAN.md điểm mơ hồ 4: file CORE ngày khác cũng phải qua bước "bỏ tiền tố REFERENCE"
        trước khi so — nếu chỉ xử lý phía ngày T, khoá 2 bên lệch nhau và không bao giờ khớp."""
        core_t = _core_df([_core_row(reference="1000API0000111", cramount="500000")])
        core_khac = _core_df([_core_row(reference="1000API111", cramount="-500000")])
        assert match.classify_core_di(core_t, {}, {-1: core_khac}).iloc[0] == \
            NHAN_CORE_HUY_CHEO_NGAY[-1]

    def test_khop_hub_uu_tien_truoc_huy_cheo_ngay(self):
        core = _core_df([_core_row(reference="1000API111", cramount="500000")])
        hub_t = _hub_da_gan_khoa([_hub_row(chi_nhanh="1000", trace="111", so_tien="500000")])
        core_khac = _core_df([_core_row(reference="1000API111", cramount="-500000")])
        nhan = match.classify_core_di(core, {0: hub_t}, {-1: core_khac})
        assert nhan.iloc[0] == NHAN_HUB_T_CORE_T

    def test_buoc11_gd_qt_von_CHUA_verify_du_lieu_that(self):
        """PLAN.md mục 6 — 0 dòng REMARK thật nào chứa "quyet toan von" (không phân biệt
        hoa/thường). So khớp phải KHÔNG phân biệt hoa/thường theo đúng câu chữ tài liệu."""
        core = _core_df([
            _core_row(trbrcd="1000", reference="1000API999", remark="QUYET TOAN VON A-B"),
            _core_row(trbrcd="1000", reference="1000API998", remark="Quyet toan von TTDTSP"),
            _core_row(trbrcd="2000", reference="1000API997", remark="Quyet toan von"),
        ])
        nhan = match.classify_core_di(core, {})
        assert nhan.tolist() == [NHAN_QT_VON, NHAN_QT_VON, NHAN_CORE_THUA]

    def test_buoc12_con_lai_la_core_thua(self):
        core = _core_df([_core_row(reference="1000API999", cramount="500000")])
        assert match.classify_core_di(core, {}).iloc[0] == NHAN_CORE_THUA


# ── HUB-side waterfall (Bước 1.2-1.7 + 2.17/2.18) ────────────────────────────

class TestLocScnl:
    def test_giu_scnl_loai_erpo_cald_tpay(self):
        """Bước 1.1 — đúng nguyên văn docx: chỉ giữ SCNL. Từng thêm TPAY (2026-09-04) dựa trên
        verify chéo 4 ngày dữ liệu thật (28-31/8/2026, NH 311), nhưng Business Owner đã khẳng
        định TPAY KHÔNG nằm trong phạm vi SCNL (chốt 2026-09-06/07) — đảo lại đúng chữ docx.
        ERPO/CALD/TPAY đều bị loại như nhau, không có ngoại lệ."""
        logs = []
        df = pipeline._loc_scnl(_hub_df([
            _hub_row(trang_thai="SCNL", txid="T1"),
            _hub_row(trang_thai="ERPO", txid="T2"),
            _hub_row(trang_thai="CALD", txid="T3"),
            _hub_row(trang_thai="TPAY", txid="T4"),
        ]), logs.append)
        assert df["TXID"].tolist() == ["T1"]
        assert any("ERPO" in m for m in logs)
        assert any("TPAY" in m for m in logs)

    def test_khong_loai_gach_ngang_txid_nhu_chieu_den(self):
        """Chiều đến loại dòng có "-" trong TXID; docx-đi KHÔNG có bước lọc tương ứng — áp nhầm
        luật của đến sẽ vứt mất giao dịch thật."""
        df = pipeline._loc_scnl(
            _hub_df([_hub_row(trang_thai="SCNL", txid="TXID001-2602260000047506")]),
            lambda m: None)
        assert len(df) == 1


class TestClassifyHubDi:
    def test_buoc1_lenh_fx(self):
        hub = _hub_da_gan_khoa([_hub_row(trace="", se_trace="")])
        assert match.classify_hub_di(hub, {}, None).iloc[0] == NHAN_LENH_FX

    def test_buoc2_khop_core_t(self):
        hub = _hub_da_gan_khoa([_hub_row(chi_nhanh="1000", trace="1002080", so_tien="500000")])
        core_t = _core_da_gan_khoa([_core_row(reference="1000API1002080", cramount="500000")])
        assert match.classify_hub_di(hub, {0: core_t}, None).iloc[0] == NHAN_HUB_T_CORE_T

    @pytest.mark.parametrize("off,nhan_mong_doi", [
        (1, "hub T core T+1"), (2, "hub T core T+2"), (3, "hub T core T+3"),
    ])
    def test_buoc3_5_khop_core_ngay_sau(self, off, nhan_mong_doi):
        hub = _hub_da_gan_khoa([_hub_row(chi_nhanh="1000", trace="1002080", so_tien="500000")])
        core = _core_da_gan_khoa([_core_row(reference="1000API1002080", cramount="500000")])
        assert match.classify_hub_di(hub, {off: core}, None).iloc[0] == nhan_mong_doi

    def test_lenh_fx_chan_truoc_khop_core(self):
        """Dòng thiếu cả TRACE lẫn SE_TRACE dừng ngay ở Bước 1.2, không được đem đi khớp CORE
        (khoá của nó tụt còn CHI_NHANH+SO_TIEN, rất dễ khớp bừa)."""
        hub = _hub_da_gan_khoa([_hub_row(trace="", se_trace="", so_tien="500000")])
        core_t = _core_da_gan_khoa([_core_row(reference="1000API", cramount="500000")])
        assert match.classify_hub_di(hub, {0: core_t}, None).iloc[0] == NHAN_LENH_FX

    def test_buoc6_khop_osb_gan_nhan_ngay_hach_toan(self):
        hub = _hub_da_gan_khoa([_hub_row(chi_nhanh="5507", trace="000874279", so_tien="1000000")])
        osb = pd.DataFrame([_osb_row()])
        assert match.classify_hub_di(hub, {}, osb).iloc[0] == "OSB & 01/09/2026"

    def test_buoc6_cap_goc_dao_huy_tu_chon_dong_so_duong(self):
        """V2 tài liệu (2026-09-04) thêm SO_TIEN vào khoá OSB — cặp giao dịch gốc (+X) và đảo/huỷ
        (-X) cùng chi nhánh+mã giao dịch: HUB.SO_TIEN LUÔN DƯƠNG nên chỉ khớp được dòng OSB có
        Số tiền DƯƠNG (dòng gốc), tự động đúng ý người chấm thủ công ("lấy giao dịch số tiền
        dương") mà không cần rule riêng."""
        hub = _hub_da_gan_khoa([_hub_row(chi_nhanh="5507", trace="000874279", so_tien="159000")])
        osb = pd.DataFrame([
            _osb_row(ngay="27/08/2026", so_tien="159.000"),   # dòng gốc — phải được chọn
            _osb_row(ngay="28/08/2026", so_tien="-159.000"),  # dòng đảo/huỷ — phải bị loại
        ])
        assert match.classify_hub_di(hub, {}, osb).iloc[0] == "OSB & 27/08/2026"

    def test_khoa_osb_di_dung_se_trace_hieu_dung(self):
        """Khoá HUB↔OSB chiều đi = CHI_NHANH + SE_TRACE(hiệu dụng) + SO_TIEN (V2 tài liệu
        2026-09-04 thêm SO_TIEN — xem load_osb.py::build_key_hub_osb_di)."""
        hub = _hub_df([_hub_row(chi_nhanh="5507", trace="", se_trace="000874279", so_tien="1000000")])
        assert load_osb.build_key_hub_osb_di(hub).iloc[0] == "55070008742791000000"

    def test_khong_con_nhan_wtpa_tper_o_phia_hub(self):
        """Bước 2.17/2.18 thuộc waterfall CORE-side (xem `TestCoreTraHubGoc`) — HUB-side kết ở
        "HUB THỪA" (Bước 1.8). Bản đầu tiên đặt nhầm 2 nhãn này sang phía HUB; test khoá lại để
        không tái phát: dòng HUB không khớp CORE phải là "HUB THỪA" dù HUB gốc có dòng WTPA."""
        hub = _hub_da_gan_khoa([_hub_row(chi_nhanh="1000", trace="1002080", so_tien="500000")])
        nhan = match.classify_hub_di(hub, {}, None)
        assert nhan.iloc[0] == NHAN_HUB_THUA
        assert NHAN_HUB_CHO_DUYET not in set(nhan) and NHAN_HUB_LENH_LOI not in set(nhan)

    def test_buoc8_con_lai_la_hub_thua(self):
        hub = _hub_da_gan_khoa([_hub_row(chi_nhanh="1000", trace="999", so_tien="500000")])
        assert match.classify_hub_di(hub, {}, None).iloc[0] == NHAN_HUB_THUA


# ── Bước 2.17/2.18 — CORE-side tra HUB GỐC chưa lọc SCNL ─────────────────────

class TestCoreTraHubGoc:
    """2 bước ÁP CHÓT của waterfall CORE-side, ngay trước "CORE THỪA" (Bước 2.19).

    Ý nghĩa nghiệp vụ: dòng HUB tương ứng KHÔNG phải SCNL nên đã bị lọc khỏi bản chính, khiến
    dòng CORE không khớp được với ai. Tra bản HUB GỐC mới nói được vì sao — thay vì xếp im lặng
    vào "CORE THỪA"."""

    @staticmethod
    def _bo_du_lieu(trang_thai_hub_khac):
        """1 dòng CORE không khớp gì + HUB gốc gồm 1 dòng SCNL khác khoá và các dòng mang trạng
        thái `trang_thai_hub_khac` CÙNG khoá với dòng CORE đó."""
        core = _core_df([_core_row(reference="1000API1002080", cramount="500000")])
        rows = [_hub_row(chi_nhanh="1000", trace="999999", so_tien="111", trang_thai="SCNL",
                         txid="T0")]
        rows += [
            _hub_row(chi_nhanh="1000", trace="1002080", so_tien="500000",
                     trang_thai=tt, txid=f"T{i + 1}")
            for i, tt in enumerate(trang_thai_hub_khac)
        ]
        return core, _hub_df(rows), _hub_da_gan_khoa(rows)

    def test_buoc17_wtpa_CHUA_verify_du_lieu_that(self):
        """PLAN.md mục 6 — không mẫu HUB thật nào có trạng thái WTPA (thật quan sát được:
        SCNL/ERPO/CALD/TPAY). Test chứng minh hàm THỰC SỰ đọc bản HUB GỐC chưa lọc: dòng WTPA
        không tồn tại trong bản đã lọc SCNL, không truyền hub gốc thì phải ra "CORE THỪA"."""
        core, hub_goc, hub_scnl = self._bo_du_lieu(["WTPA"])
        assert len(hub_scnl) == 1  # dòng WTPA đã bị lọc khỏi bản chính
        assert match.classify_core_di(core, {0: hub_scnl}, hub_goc=hub_goc).iloc[0] == \
            NHAN_HUB_CHO_DUYET
        assert match.classify_core_di(core, {0: hub_scnl}).iloc[0] == NHAN_CORE_THUA

    def test_buoc18_tper_CHUA_verify_du_lieu_that(self):
        """PLAN.md mục 6 — như trên, cho trạng thái TPER."""
        core, hub_goc, hub_scnl = self._bo_du_lieu(["TPER"])
        assert match.classify_core_di(core, {0: hub_scnl}, hub_goc=hub_goc).iloc[0] == \
            NHAN_HUB_LENH_LOI

    def test_wtpa_uu_tien_truoc_tper_CHUA_verify_du_lieu_that(self):
        """Có cả 2 trạng thái cùng khoá → theo thứ tự docx, WTPA (2.17) xét trước TPER (2.18)."""
        core, hub_goc, hub_scnl = self._bo_du_lieu(["TPER", "WTPA"])
        assert match.classify_core_di(core, {0: hub_scnl}, hub_goc=hub_goc).iloc[0] == \
            NHAN_HUB_CHO_DUYET

    def test_khop_hub_scnl_uu_tien_truoc_tra_hub_goc_CHUA_verify_du_lieu_that(self):
        """Dòng CORE khớp được HUB SCNL thì dừng ở Bước 2.6, không rơi xuống 2.17/2.18."""
        rows = [
            _hub_row(chi_nhanh="1000", trace="1002080", so_tien="500000",
                     trang_thai="SCNL", txid="T1"),
            _hub_row(chi_nhanh="1000", trace="1002080", so_tien="500000",
                     trang_thai="WTPA", txid="T2"),
        ]
        core = _core_df([_core_row(reference="1000API1002080", cramount="500000")])
        nhan = match.classify_core_di(core, {0: _hub_da_gan_khoa(rows)}, hub_goc=_hub_df(rows))
        assert nhan.iloc[0] == NHAN_HUB_T_CORE_T

    def test_qt_von_uu_tien_truoc_tra_hub_goc_CHUA_verify_du_lieu_that(self):
        """Bước 2.10 (GD QT vốn) đứng TRƯỚC 2.17/2.18 trong waterfall."""
        core = _core_df([_core_row(trbrcd="1000", reference="1000API1002080",
                                    remark="Quyet toan von A-B", cramount="500000")])
        hub_goc = _hub_df([_hub_row(chi_nhanh="1000", trace="1002080", so_tien="500000",
                                     trang_thai="WTPA")])
        assert match.classify_core_di(core, {}, hub_goc=hub_goc).iloc[0] == NHAN_QT_VON

    def test_khac_khoa_thi_khong_gan_nhan_CHUA_verify_du_lieu_that(self):
        """Dòng WTPA khác khoá thì không được "nhận vơ" dòng CORE nào."""
        core = _core_df([_core_row(reference="1000API1002080", cramount="500000")])
        hub_goc = _hub_df([_hub_row(chi_nhanh="1000", trace="999999", so_tien="500000",
                                     trang_thai="WTPA")])
        assert match.classify_core_di(core, {}, hub_goc=hub_goc).iloc[0] == NHAN_CORE_THUA

    def test_mot_dong_wtpa_chi_giai_thich_dung_mot_dong_core_CHUA_verify_du_lieu_that(self):
        """Chống nhân bản nhãn: 2 dòng CORE cùng khoá nhưng chỉ 1 dòng WTPA ở HUB gốc → đúng 1
        dòng nhận nhãn, dòng còn lại là "CORE THỪA"."""
        core = _core_df([
            _core_row(reference="1000API1002080", cramount="500000"),
            _core_row(reference="1000API1002080", cramount="500000"),
        ])
        hub_goc = _hub_df([_hub_row(chi_nhanh="1000", trace="1002080", so_tien="500000",
                                     trang_thai="WTPA")])
        nhan = match.classify_core_di(core, {}, hub_goc=hub_goc)
        assert sorted(nhan.tolist()) == sorted([NHAN_HUB_CHO_DUYET, NHAN_CORE_THUA])


# ── OSB trùng `Mã giao dịch` — cảnh báo rõ, KHÔNG drop_duplicates âm thầm ─────

class TestOsbTrungMaGiaoDich:
    def test_trung_cung_ngay_hach_toan_chi_canh_bao(self):
        """Dữ liệu thật NH 201 có đúng 2 dòng trùng `Mã giao dịch`. Cùng ngày hạch toán → lookup
        ra kết quả như nhau dù lấy dòng nào, nhưng vẫn phải log để người soát biết."""
        hub = _hub_da_gan_khoa([_hub_row(chi_nhanh="5507", trace="000874279", so_tien="1000000")])
        osb = pd.DataFrame([_osb_row(ngay="01/09/2026"), _osb_row(ngay="01/09/2026")])
        logs = []
        nhan = match.classify_hub_di(hub, {}, osb, log=logs.append)
        assert nhan.iloc[0] == "OSB & 01/09/2026"
        assert any("CÙNG Ngày hạch toán" in m and "000874279" in m for m in logs)

    def test_trung_khac_ngay_hach_toan_canh_bao_ro_va_dung_dong_dau(self):
        """Ca nguy hiểm: kết quả phụ thuộc thứ tự dòng. Phải liệt kê đúng mã + CÁC giá trị ngày
        khác nhau và nói thẳng là đang lấy dòng ĐẦU TIÊN — không tự chọn rồi im lặng."""
        hub = _hub_da_gan_khoa([_hub_row(chi_nhanh="5507", trace="000874279", so_tien="1000000")])
        osb = pd.DataFrame([_osb_row(ngay="01/09/2026"), _osb_row(ngay="02/09/2026")])
        logs = []
        nhan = match.classify_hub_di(hub, {}, osb, log=logs.append)
        assert nhan.iloc[0] == "OSB & 01/09/2026"
        canh_bao = [m for m in logs if "KHÁC NHAU" in m]
        assert len(canh_bao) == 1
        assert "000874279" in canh_bao[0]
        assert "01/09/2026" in canh_bao[0] and "02/09/2026" in canh_bao[0]
        assert "DÒNG ĐẦU TIÊN" in canh_bao[0]

    def test_khong_trung_thi_khong_canh_bao(self):
        hub = _hub_da_gan_khoa([_hub_row(chi_nhanh="5507", trace="000874279", so_tien="1000000")])
        osb = pd.DataFrame([_osb_row(), _osb_row(ma_gd="000874280")])
        logs = []
        match.classify_hub_di(hub, {}, osb, log=logs.append)
        assert not [m for m in logs if "CẢNH BÁO" in m]

    def test_canh_bao_phat_ra_ca_khi_khong_dong_hub_nao_khop(self):
        """Dữ liệu OSB trùng là vấn đề của chính file nguồn — không được nấp trong nhánh "có
        dòng khớp" rồi biến mất vào những hôm không ai rơi tới bước OSB."""
        hub = _hub_da_gan_khoa([_hub_row(chi_nhanh="9999", trace="111", so_tien="500000")])
        osb = pd.DataFrame([_osb_row(ngay="01/09/2026"), _osb_row(ngay="02/09/2026")])
        logs = []
        nhan = match.classify_hub_di(hub, {}, osb, log=logs.append)
        assert nhan.iloc[0] == NHAN_HUB_THUA
        assert any("KHÁC NHAU" in m for m in logs)


# ── Chống khớp 1-nhiều khi trùng khoá (_khop_min_count) ──────────────────────

class TestKhopMinCount:
    def test_hub_trung_khoa_chi_khop_dung_so_dong_core_co(self):
        """2 dòng HUB cùng khoá, CORE chỉ có 1 dòng khoá đó → đúng 1 dòng HUB được khớp, dòng
        còn lại là HUB THỪA. Không được đánh dấu khớp cả 2 (merge 1-nhiều)."""
        hub = _hub_da_gan_khoa([
            _hub_row(chi_nhanh="1000", trace="1002080", so_tien="500000", txid="T1"),
            _hub_row(chi_nhanh="1000", trace="1002080", so_tien="500000", txid="T2"),
        ])
        core_t = _core_da_gan_khoa([_core_row(reference="1000API1002080", cramount="500000")])
        nhan = match.classify_hub_di(hub, {0: core_t}, None)
        assert sorted(nhan.tolist()) == sorted([NHAN_HUB_T_CORE_T, NHAN_HUB_THUA])

    def test_core_trung_khoa_chi_khop_dung_so_dong_hub_co(self):
        core = _core_df([
            _core_row(reference="1000API1002080", cramount="500000"),
            _core_row(reference="1000API1002080", cramount="500000"),
        ])
        hub_t = _hub_da_gan_khoa([_hub_row(chi_nhanh="1000", trace="1002080", so_tien="500000")])
        nhan = match.classify_core_di(core, {0: hub_t})
        assert sorted(nhan.tolist()) == sorted([NHAN_HUB_T_CORE_T, NHAN_CORE_THUA])

    def test_bat_bien_so_mon_khop_hub_t_core_t_bang_nhau(self):
        """Bất biến docx-đi Bước 2.6 ("đảm bảo số món và số tiền giống số liệu ở bước 1.3")."""
        core = _core_da_gan_khoa([
            _core_row(reference="1000API1002080", cramount="500000"),
            _core_row(reference="1000API1002080", cramount="500000"),
            _core_row(reference="1000API999", cramount="700000"),
        ])
        hub = _hub_da_gan_khoa([
            _hub_row(chi_nhanh="1000", trace="1002080", so_tien="500000", txid="T1"),
            _hub_row(chi_nhanh="1000", trace="1002080", so_tien="500000", txid="T2"),
            _hub_row(chi_nhanh="1000", trace="1002080", so_tien="500000", txid="T3"),
        ])
        n_core = int((match.classify_core_di(core, {0: hub}) == NHAN_HUB_T_CORE_T).sum())
        n_hub = int((match.classify_hub_di(hub, {0: core}, None) == NHAN_HUB_T_CORE_T).sum())
        assert n_core == n_hub == 2


# ── export.build_tong_hop_di ─────────────────────────────────────────────────

class TestBuildTongHopDi:
    def test_cong_tien_core_theo_cramount(self):
        """Cột "Số tiền CORE" phải cộng CRAMOUNT — DRAMOUNT của CSV `_DI*.csv` luôn = "0", lấy
        nhầm cột thì bảng tổng hợp ra 0 tuyệt đối mà không báo lỗi."""
        core = _core_df([_core_row(dramount="0", cramount="500000"),
                         _core_row(dramount="0", cramount="300000")])
        core["KETQUADOICHIEU"] = [NHAN_HUB_T_CORE_T, NHAN_CORE_THUA]
        hub = _hub_df([_hub_row(so_tien="500000")])
        hub["KETQUADOICHIEU"] = [NHAN_HUB_T_CORE_T]

        tong = export.build_tong_hop_di(core, hub)
        hang = tong[tong["Nhãn (KETQUADOICHIEU)"] == NHAN_HUB_T_CORE_T].iloc[0]
        assert hang["Số dòng CORE"] == 1 and hang["Số tiền CORE"] == 500000
        assert hang["Số dòng HUB"] == 1 and hang["Số tiền HUB"] == 500000

        hang_tong = tong[tong["Nhãn (KETQUADOICHIEU)"] == "Tổng cộng"].iloc[0]
        assert hang_tong["Số dòng CORE"] == 2 and hang_tong["Số tiền CORE"] == 800000

    def test_o_trong_cramount_coi_la_0_khong_raise(self):
        core = _core_df([_core_row(cramount=""), _core_row(cramount="300000")])
        core["KETQUADOICHIEU"] = [NHAN_CORE_THUA, NHAN_CORE_THUA]
        hub = _hub_df([_hub_row(so_tien="500000")])
        hub["KETQUADOICHIEU"] = [NHAN_HUB_THUA]
        tong = export.build_tong_hop_di(core, hub)
        hang = tong[tong["Nhãn (KETQUADOICHIEU)"] == NHAN_CORE_THUA].iloc[0]
        assert hang["Số dòng CORE"] == 2 and hang["Số tiền CORE"] == 300000

    def test_ghi_du_3_file(self, tmp_path):
        core = _core_df([_core_row()])
        core["KETQUADOICHIEU"] = [NHAN_CORE_THUA]
        core[match.KEY_COL] = ["x"]
        hub = _hub_df([_hub_row()])
        hub["KETQUADOICHIEU"] = [NHAN_HUB_THUA]
        hub[match.KEY_COL] = ["x"]
        paths = export.export_excel_di(
            {"core_df": core, "hub_df": hub}, tmp_path, "201_20260901_hubcore_di")
        assert [p.name for p in paths] == [
            "201_20260901_hubcore_di.xlsx",
            "201_20260901_hubcore_di_core_chi_tiet.csv",
            "201_20260901_hubcore_di_hub_chi_tiet.csv",
        ]
        assert all(p.exists() for p in paths)
        # Cột khoá nội bộ không được lọt ra file bàn giao
        assert match.KEY_COL not in pd.read_csv(paths[1], dtype=str).columns


class TestLoadCoreDenCsvFileHongDi:
    """Mirror `TestLoadCoreDenCsvFileHong` bên chiều đến (2026-09-09) — đường nhanh của
    `_tim_file_core_hoac_csv_di` cũng bỏ qua try/except của `_doc_trdate_1_file`, cần
    `load_core_den_csv()` tự bắt lỗi rõ ràng."""

    def test_xlsx_hong_bao_loi_ro_ten_file(self, tmp_path):
        p = tmp_path / "201_DI.xlsx"
        p.write_bytes(b"khong phai file excel that")
        with pytest.raises(ValueError, match="201_DI.xlsx"):
            load_core.load_core_den_csv(p)


# ── pipeline: dò file theo ngày ──────────────────────────────────────────────

class TestTimFileDi:
    def test_hub_di_khong_nhan_nham_file_den(self, tmp_path):
        (tmp_path / "1.9").mkdir()
        (tmp_path / "1.9" / "doichieugd_20260901__04_DEN_9999_N.zip").write_bytes(b"x")
        assert pipeline._tim_file_hub_di(tmp_path, "20260901", "201") is None
        (tmp_path / "1.9" / "doichieugd_20260901__04_DI_9999_N.zip").write_bytes(b"x")
        p = pipeline._tim_file_hub_di(tmp_path, "20260901", "201")
        assert p.name == "doichieugd_20260901__04_DI_9999_N.zip"

    def test_nhieu_hub_cung_khop_khong_tu_chon(self, tmp_path):
        (tmp_path / "doichieugd_20260901__04_DI_9999_N.zip").write_bytes(b"x")
        (tmp_path / "doichieugd_20260901__04_DI_9999_N_v2.zip").write_bytes(b"x")
        assert pipeline._tim_file_hub_di(tmp_path, "20260901", "201") is None

    def test_uu_tien_csv_da_phan_loai_hon_zip(self, tmp_path):
        (tmp_path / "GL02_20260901_1000.zip").write_bytes(b"x")
        (tmp_path / "201_DI.csv").write_bytes(b"x")
        loai, p = pipeline._tim_file_core_hoac_csv_di(tmp_path, "20260901", "201", 0)
        assert loai == "csv" and p.name == "201_DI.csv"

    def _viet_csv_trdate(self, path, *trdates):
        """Ghi 1 file CSV core hợp lệ, mỗi dòng 1 giá trị TRDATE trong `trdates` (nhiều giá trị →
        file có TRDATE lẫn nhiều ngày)."""
        _core_df([_core_row() | {"TRDATE": d} for d in trdates]).to_csv(path, index=False)

    def _viet_xlsx_trdate(self, path, *trdates):
        """Như `_viet_csv_trdate` nhưng ghi Excel (2026-09-09, hỗ trợ file core dạng .xlsx)."""
        _core_df([_core_row() | {"TRDATE": d} for d in trdates]).to_excel(
            path, index=False, engine="openpyxl")

    def test_1_file_1_offset_0_dung_duong_nhanh_khong_can_doc_noi_dung(self, tmp_path):
        """Đúng 1 file khớp + hỏi offset 0 (ngày T) → tin luôn, KHÔNG mở đọc nội dung (đường nhanh,
        giữ hiệu năng cho trường hợp phổ biến nhất) — file rỗng/hỏng vẫn được chấp nhận ở bước
        NÀY (nội dung sẽ được validate ở bước đọc CORE thật sự, không phải ở bước dò file)."""
        (tmp_path / "201_DI.csv").write_bytes(b"x")
        loai, p = pipeline._tim_file_core_hoac_csv_di(tmp_path, "20260901", "201", 0)
        assert loai == "csv" and p.name == "201_DI.csv"

    def test_1_file_offset_khac_0_tu_gan_dung_theo_trdate_that(self, tmp_path):
        """2026-09-08: 1 thư mục có CSV riêng cho ngày T VÀ ngày T+1 (2 đợt xuất trong 1 phiên,
        ca thật gặp trên dữ liệu 5-6/9/2026) — tên file không mang ngày nhưng TRDATE thật bên
        trong PHẢI được dùng để gán đúng offset, không còn bị luật cũ chặn cứng."""
        self._viet_csv_trdate(tmp_path / "201_DI_20260906_1615.csv", "20260901")
        self._viet_csv_trdate(tmp_path / "201_DI_20260907_1059.csv", "20260902")

        loai, p = pipeline._tim_file_core_hoac_csv_di(tmp_path, "20260901", "201", 0)
        assert loai == "csv" and p.name == "201_DI_20260906_1615.csv"

        loai, p = pipeline._tim_file_core_hoac_csv_di(tmp_path, "20260902", "201", 1)
        assert loai == "csv" and p.name == "201_DI_20260907_1059.csv"

        # Không file nào có TRDATE=20260831 (offset -1) → không tự nhận nhầm, trả None
        assert pipeline._tim_file_core_hoac_csv_di(tmp_path, "20260831", "201", -1) is None

    def test_1_file_xlsx_offset_0_dung_duong_nhanh(self, tmp_path):
        """2026-09-09: file core .xlsx đơn lẻ cũng đi được đường nhanh y hệt .csv."""
        self._viet_xlsx_trdate(tmp_path / "201_DI.xlsx", "20260901")
        loai, p = pipeline._tim_file_core_hoac_csv_di(tmp_path, "20260901", "201", 0)
        assert loai == "csv" and p.name == "201_DI.xlsx"

    def test_tron_csv_va_xlsx_khac_ngay_deu_dung_duoc(self, tmp_path):
        """Trộn lẫn 1 file .csv (ngày T) và 1 file .xlsx (ngày T+1) trong CÙNG thư mục — 2 định
        dạng bình đẳng, không định dạng nào được ưu tiên hơn."""
        self._viet_csv_trdate(tmp_path / "201_DI_csv.csv", "20260901")
        self._viet_xlsx_trdate(tmp_path / "201_DI_xlsx.xlsx", "20260902")

        loai, p = pipeline._tim_file_core_hoac_csv_di(tmp_path, "20260901", "201", 0)
        assert loai == "csv" and p.name == "201_DI_csv.csv"
        loai, p = pipeline._tim_file_core_hoac_csv_di(tmp_path, "20260902", "201", 1)
        assert loai == "csv" and p.name == "201_DI_xlsx.xlsx"

    def test_csv_va_xlsx_cung_ngay_khong_tu_chon(self, tmp_path):
        """1 file .csv và 1 file .xlsx CÙNG đại diện 1 ngày — vẫn phải chặn như "2 file trùng
        ngày", không tự chọn định dạng nào ưu tiên hơn."""
        self._viet_csv_trdate(tmp_path / "201_DI_csv.csv", "20260901")
        self._viet_xlsx_trdate(tmp_path / "201_DI_xlsx.xlsx", "20260901")
        logs = []
        assert pipeline._tim_file_core_hoac_csv_di(
            tmp_path, "20260901", "201", 1, logs.append) is None
        assert any("KHÔNG tự chọn" in m for m in logs)

    def test_offset_khac_0_van_nhan_zip_khi_khong_co_csv_dung_ngay(self, tmp_path):
        """CSV có sẵn nhưng TRDATE của nó không khớp offset đang hỏi → rơi về GL02 zip đúng ngày,
        không dùng liều CSV sai ngày."""
        self._viet_csv_trdate(tmp_path / "201_DI.csv", "20260901")
        (tmp_path / "GL02_20260902_1000.zip").write_bytes(b"x")
        loai, p = pipeline._tim_file_core_hoac_csv_di(tmp_path, "20260902", "201", 1)
        assert loai == "zip" and p.name == "GL02_20260902_1000.zip"

    def test_csv_2_file_gom_chung_1_thu_muc_dat_ten_theo_ngay_T(self, tmp_path):
        """Phát hiện qua rà soát 2026-09-08 (đã vá cho chiều đến qua phản biện 4 vòng, nay mirror
        cho chiều đi): người dùng thường gom MỌI CSV của cả phiên (nhiều ngày khác nhau) vào 1
        thư mục con đặt tên theo ngày T (VD `1.9/`) — không dò thêm theo `ngay_goc` thì offset≠0
        rơi về `goc_dir` (không đệ quy vào `1.9/`), mất file dù đã nằm sẵn trong thư mục T."""
        sub = tmp_path / "1.9"
        sub.mkdir()
        self._viet_csv_trdate(sub / "201_DI_20260906_0900.csv", "20260901")
        self._viet_csv_trdate(sub / "201_DI_20260907_0900.csv", "20260902")

        loai, p = pipeline._tim_file_core_hoac_csv_di(
            tmp_path, "20260901", "201", 0, ngay_goc="20260901")
        assert loai == "csv" and p.name == "201_DI_20260906_0900.csv"

        loai, p = pipeline._tim_file_core_hoac_csv_di(
            tmp_path, "20260902", "201", 1, ngay_goc="20260901")
        assert loai == "csv" and p.name == "201_DI_20260907_0900.csv"

    def test_csv_offset_am_cung_gom_chung_thu_muc_dat_ten_theo_ngay_T(self, tmp_path):
        """Chiều đi khác chiều đến ở chỗ cửa sổ CORE có CẢ offset ÂM (T-1, T-2, T-3 — nhánh huỷ
        chéo ngày, xem OFFSET_CORE_CAN_DOC trong core_di/config.py). Phản biện port `ngay_goc`
        (2026-09-08) xác nhận việc gộp `{ngay, ngay_goc}` đối xứng theo dấu offset, không chỉ tình
        cờ đúng cho offset dương như bản đến — test này khoá lại bằng offset -1 tường minh."""
        sub = tmp_path / "1.9"
        sub.mkdir()
        self._viet_csv_trdate(sub / "201_DI_hom_qua.csv", "20260831")
        self._viet_csv_trdate(sub / "201_DI_hom_nay.csv", "20260901")

        loai, p = pipeline._tim_file_core_hoac_csv_di(
            tmp_path, "20260831", "201", -1, ngay_goc="20260901")
        assert loai == "csv" and p.name == "201_DI_hom_qua.csv"

    def test_zip_gom_chung_1_thu_muc_dat_ten_theo_ngay_T(self, tmp_path):
        """Cùng lỗi tổ chức thư mục như CSV (test trên) nhưng cho nhánh GL02 ZIP fallback."""
        sub = tmp_path / "1.9"
        sub.mkdir()
        (sub / "GL02_20260901_1000.zip").write_bytes(b"x")
        (sub / "GL02_20260902_1000.zip").write_bytes(b"x")

        loai, p = pipeline._tim_file_core_hoac_csv_di(
            tmp_path, "20260902", "201", 1, ngay_goc="20260901")
        assert loai == "zip" and p.name == "GL02_20260902_1000.zip"

    def test_hub_di_gom_chung_1_thu_muc_dat_ten_theo_ngay_T(self, tmp_path):
        """Cùng lỗi tổ chức thư mục, cho `_tim_file_hub_di` — hậu quả nếu KHÔNG vá: HUB T-1 mất
        khiến CORE đáng lẽ khớp "hub T-1 core T" bị gắn nhầm "CORE THỪA" (sai số liệu âm thầm)."""
        sub = tmp_path / "1.9"
        sub.mkdir()
        (sub / "doichieugd_20260901__04_DI_9999_N.zip").write_bytes(b"x")
        (sub / "doichieugd_20260831__04_DI_9999_N.zip").write_bytes(b"x")

        p = pipeline._tim_file_hub_di(tmp_path, "20260831", "201", ngay_goc="20260901")
        assert p is not None and p.name == "doichieugd_20260831__04_DI_9999_N.zip"

    def test_nhieu_csv_cung_trdate_khong_tu_chon(self, tmp_path):
        """2 file CSV khác tên nhưng TRDATE thật BÊN TRONG lại trùng 1 ngày — vẫn phải chặn như
        luật cũ (không tự chọn), chỉ khác chỗ xét trên TRDATE thật thay vì xét trên việc "có nhiều
        file cùng khớp tên" như trước."""
        self._viet_csv_trdate(tmp_path / "201_DI_20260902_0900.csv", "20260901")
        self._viet_csv_trdate(tmp_path / "201_DI_20260902_1358.csv", "20260901")
        logs = []
        assert pipeline._tim_file_core_hoac_csv_di(
            tmp_path, "20260901", "201", 1, logs.append) is None
        assert any("KHÔNG tự chọn" in m for m in logs)

    def test_csv_trdate_lan_nhieu_ngay_trong_1_file_bi_loai_khong_crash(self, tmp_path):
        """1 file tự nó có TRDATE lẫn nhiều ngày (dữ liệu hỏng/gộp nhầm) — loại khỏi việc gán
        offset, log lỗi rõ, KHÔNG crash cả job và KHÔNG đoán dùng 1 trong các ngày đó."""
        self._viet_csv_trdate(tmp_path / "201_DI_lan_ngay.csv", "20260901", "20260902")
        logs = []
        assert pipeline._tim_file_core_hoac_csv_di(
            tmp_path, "20260901", "201", 1, logs.append) is None
        assert any("TRDATE lẫn" in m for m in logs)

    def test_file_hong_khong_doc_duoc_thi_bo_qua_khong_crash(self, tmp_path):
        """File rác (không đọc được cột TRDATE) gặp ở offset khác 0 — log lỗi rồi bỏ qua, không
        làm crash toàn bộ job (job vẫn tiếp tục với các offset/nhánh khác)."""
        (tmp_path / "201_DI_hong.csv").write_bytes(b"khong phai csv hop le")
        (tmp_path / "201_DI_that.csv").write_text(
            "TRDATE\n20260902\n", encoding="utf-8")
        logs = []
        loai, p = pipeline._tim_file_core_hoac_csv_di(
            tmp_path, "20260902", "201", 1, logs.append)
        assert loai == "csv" and p.name == "201_DI_that.csv"
        assert any("Không đọc được cột TRDATE" in m for m in logs)

    def test_osb_uu_tien_file_co_tu_khoa_di(self, tmp_path):
        """Thư mục làm việc thường có CẢ OSB đến lẫn đi của cùng NH — chọn nhầm là đọc sai
        nguồn mà không có dấu hiệu nào."""
        (tmp_path / "OSB den 201 1.9.xlsx").write_bytes(b"x")
        (tmp_path / "OSB di 201 1.9.xlsx").write_bytes(b"x")
        assert pipeline._tim_file_osb_di(tmp_path, "20260901", "201").name == "OSB di 201 1.9.xlsx"

    def test_osb_lui_ve_file_khong_ghi_chieu_va_canh_bao(self, tmp_path):
        (tmp_path / "osb 201.xlsx").write_bytes(b"x")
        logs = []
        p = pipeline._tim_file_osb_di(tmp_path, "20260901", "201", logs.append)
        assert p.name == "osb 201.xlsx"
        assert any("không thấy file nào có từ khoá 'di'" in m for m in logs)

    def test_osb_khong_co_file_thi_none(self, tmp_path):
        assert pipeline._tim_file_osb_di(tmp_path, "20260901", "201") is None


# ── tim_nhom_lenh_fx_trung_remark — quyết định người dùng 2026-09-05 ─────────

class TestTimNhomLenhFxTrungRemark:
    def _fx_row(self, trbrcd="6200", remark="Thanh toan tien ky quy", cramount="8877000"):
        row = _core_row(trbrcd=trbrcd, userid="BTAVPHUONG", remark=remark, cramount=cramount)
        return row

    def test_2_dong_cung_trbrcd_remark_duoc_gom_nhom(self):
        """Ca thật (2026-09-04): REFERENCE khác nhau nhưng REMARK giống hệt, CRAMOUNT +X/-X —
        docx không có rule ghép cặp theo REMARK (chỉ REFERENCE, Bước 2.3) nên cả 2 dòng đúng là
        "lệnh fx" theo code — vẫn phải xuất ra để người soát tự đối chiếu."""
        df = _core_df([self._fx_row(cramount="8877000"), self._fx_row(cramount="-8877000")])
        df["KETQUADOICHIEU"] = NHAN_LENH_FX
        nhom = match.tim_nhom_lenh_fx_trung_remark(df)
        assert len(nhom) == 2

    def test_remark_cong_thuc_lap_lai_nhieu_dong_van_xuat_du(self):
        """Nhóm REMARK "công thức" (chi lương NSNN...) lặp hàng trăm dòng — KHÔNG được code tự
        ghép cặp (rủi ro ghép nhầm giao dịch không liên quan), chỉ xuất nguyên vẹn cả nhóm."""
        rows = [self._fx_row(remark="Chi luong NSNN", cramount=str(1000 * i)) for i in range(1, 6)]
        df = _core_df(rows)
        df["KETQUADOICHIEU"] = NHAN_LENH_FX
        nhom = match.tim_nhom_lenh_fx_trung_remark(df)
        assert len(nhom) == 5

    def test_remark_don_le_khong_trung_thi_khong_xuat(self):
        df = _core_df([self._fx_row(remark="Giao dich rieng le, khong ai giong")])
        df["KETQUADOICHIEU"] = NHAN_LENH_FX
        nhom = match.tim_nhom_lenh_fx_trung_remark(df)
        assert nhom.empty

    def test_chi_xet_dong_da_gan_nhan_lenh_fx(self):
        """Dòng KHÔNG phải "lệnh fx" (VD "hub T core T") dù trùng TRBRCD+REMARK cũng không được
        tính — hàm này chỉ soi trong phạm vi Bước 2.5, không phải toàn bộ CORE."""
        df = _core_df([self._fx_row(remark="Trung remark"), self._fx_row(remark="Trung remark")])
        df["KETQUADOICHIEU"] = ["lệnh fx", "hub T core T"]
        nhom = match.tim_nhom_lenh_fx_trung_remark(df)
        assert len(nhom) == 0

    def test_khong_co_dong_lenh_fx_nao_thi_tra_rong(self):
        df = _core_df([_core_row()])
        df["KETQUADOICHIEU"] = "hub T core T"
        nhom = match.tim_nhom_lenh_fx_trung_remark(df)
        assert nhom.empty


class TestExportLenhFxTrungRemark:
    def test_export_ghi_them_file_khi_co_nhom_trung(self, tmp_path):
        core_df = _core_df([
            _core_row(trbrcd="6200", userid="BTAVPHUONG", remark="X", cramount="100"),
            _core_row(trbrcd="6200", userid="BTAVPHUONG", remark="X", cramount="-100"),
        ])
        core_df["KETQUADOICHIEU"] = NHAN_LENH_FX
        hub_df = pd.DataFrame(columns=["CHI_NHANH", "SO_TIEN", "KETQUADOICHIEU"])
        files = export.export_excel_di({"core_df": core_df, "hub_df": hub_df}, tmp_path, "test")
        ten_file = [p.name for p in files]
        assert "test_lenh_fx_trung_remark.csv" in ten_file
        noi_dung = pd.read_csv(tmp_path / "test_lenh_fx_trung_remark.csv", dtype=str)
        assert len(noi_dung) == 2

    def test_export_khong_ghi_file_khi_khong_co_nhom_trung(self, tmp_path):
        core_df = _core_df([_core_row()])
        core_df["KETQUADOICHIEU"] = "hub T core T"
        hub_df = pd.DataFrame(columns=["CHI_NHANH", "SO_TIEN", "KETQUADOICHIEU"])
        files = export.export_excel_di({"core_df": core_df, "hub_df": hub_df}, tmp_path, "test")
        assert "test_lenh_fx_trung_remark.csv" not in [p.name for p in files]


# ── export.export_excel_di — sheet "GhiChu" (2026-09-09, card 123) ────────────

class TestExportGhiChu:
    def _ket_qua(self):
        core_df = _core_df([_core_row()])
        core_df["KETQUADOICHIEU"] = "hub T core T"
        hub_df = _hub_df([_hub_row()])
        hub_df["KETQUADOICHIEU"] = "hub T core T"
        return core_df, hub_df

    def test_co_ghi_chu_thi_ghi_dung_noi_dung_vao_sheet(self, tmp_path):
        core_df, hub_df = self._ket_qua()
        ket_qua = {
            "core_df": core_df, "hub_df": hub_df,
            "ghi_chu": ["[HUB T-1] không tìm thấy file — BẮT BUỘC nhưng KHÔNG chặn: ..."],
        }
        paths = export.export_excel_di(ket_qua, tmp_path, "test")
        ghi_chu = pd.read_excel(paths[0], sheet_name="GhiChu")
        assert list(ghi_chu["Ghi chú"]) == ket_qua["ghi_chu"]

    def test_khong_thieu_file_thi_ghi_dong_mac_dinh(self, tmp_path):
        core_df, hub_df = self._ket_qua()
        ket_qua = {"core_df": core_df, "hub_df": hub_df, "ghi_chu": []}
        paths = export.export_excel_di(ket_qua, tmp_path, "test")
        ghi_chu = pd.read_excel(paths[0], sheet_name="GhiChu")
        assert len(ghi_chu) == 1
        assert "Không thiếu file" in ghi_chu["Ghi chú"].iloc[0]

    def test_thieu_key_ghi_chu_van_chay_duoc(self, tmp_path):
        """`ket_qua` dựng tay trong test cũ (trước 2026-09-09) không có key "ghi_chu" — sheet vẫn
        phải ghi được, không raise KeyError."""
        core_df, hub_df = self._ket_qua()
        paths = export.export_excel_di({"core_df": core_df, "hub_df": hub_df}, tmp_path, "test")
        ghi_chu = pd.read_excel(paths[0], sheet_name="GhiChu")
        assert len(ghi_chu) == 1


# ── pipeline.doi_chieu_hub_core_di — persist "ghi_chu" khi thiếu file T±k ─────

class TestPipelineGhiChuThieuFile:
    def test_thieu_hub_t_tru_1_duoc_ghi_vao_ghi_chu(self, tmp_path):
        """Ngày T bắt buộc phải có HUB/CORE; không nạp thêm HUB T-1 → pipeline vẫn chạy được
        (T-1 chỉ "bắt buộc nhưng không chặn"), nhưng phải để lại dấu vết trong `ghi_chu` — đúng
        yêu cầu Giai đoạn 2 (card 123): người soát đọc file kết quả một mình cũng biết vì sao
        thiếu nhãn "hub T-1 core T"."""
        ngay = "20260901"
        import zipfile

        hub_df = pd.DataFrame([{
            "NGAY_GIAO_DICH": "01/09/2026", "CHI_NHANH": "1000", "REFHUB": "R1",
            "MSGREF": "M1", "MSGSEQ": "M1", "TXID": "TX1", "KENH_THANH_TOAN": "SP REALTIME",
            "TRANG_THAI_LENH": "SCNL", "SO_TIEN": "100000", "TRACE": "000000001",
            "SE_TRACE": "", "SESSION": "20260901", "LOAI_LENH_OSB": "0",
            "NH_GUI": "01202001", "NOI_DUNG": "TEST",
        }])
        hub_zip = tmp_path / f"doichieugd_{ngay}__05_DI_9999_N.zip"
        with zipfile.ZipFile(hub_zip, "w") as zf:
            zf.writestr("data.csv", hub_df.to_csv(index=False).encode("utf-8-sig"))

        core_df = pd.DataFrame([{**_core_row(), "TRDATE": ngay}])
        (tmp_path / "202_DI.csv").write_text(
            core_df.to_csv(index=False), encoding="utf-8-sig")

        ket_qua = pipeline.doi_chieu_hub_core_di(tmp_path, ngay, "202")
        assert any(m.startswith("[HUB T-1] không tìm thấy file") for m in ket_qua["ghi_chu"])
        assert any("BẮT BUỘC nhưng KHÔNG chặn" in m for m in ket_qua["ghi_chu"])
