import sqlite3

import pytest

from backend.services import doi_chieu_citad_service as svc

_SCHEMA = """
CREATE TABLE doi_chieu_citad_sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ngay       TEXT    NOT NULL,
    data       TEXT    NOT NULL,
    updated_at DATETIME,
    updated_by INTEGER,
    status     TEXT    NOT NULL DEFAULT 'draft',
    created_by INTEGER,
    UNIQUE(ngay, created_by)
);
CREATE TABLE doi_chieu_citad_history (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ngay       TEXT,
    session_id INTEGER,
    staff_id   INTEGER,
    data       TEXT,
    created_at DATETIME,
    status     TEXT
);
CREATE TABLE doi_chieu_citad_history_edits (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    history_id  INTEGER,
    staff_id    INTEGER,
    created_at  DATETIME
);
CREATE TABLE user_tttt (
    id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT
);
"""


def _db():
    db = sqlite3.connect(":memory:", check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.executescript(_SCHEMA)
    return db


def test_hai_nguoi_khac_nhau_moi_nguoi_1_bang_rieng():
    """Bug đã báo: trước đây 1 ngày chỉ 1 người chấm được, người khác chấm
    cùng ngày (dù chỉ Napas) bị chặn cứng. Nay mỗi người phải tự lập được
    bảng RIÊNG của mình cho cùng 1 ngày, không đụng bảng người khác."""
    db = _db()
    ngay = "20/08/2026"

    svc.session_save(db, ngay, 1, {"napas_m": 10, "napas_t": 20, "lap_bang": "A"}, "draft")
    # Người 2 không truyền target_created_by — phải tự lập bảng RIÊNG, không
    # bị lỗi, không đè lên bảng người 1.
    svc.session_save(db, ngay, 2, {"napas_m": 99, "napas_t": 88, "lap_bang": "B"}, "draft")

    bang_1 = svc.session_get(db, ngay, created_by=1)
    bang_2 = svc.session_get(db, ngay, created_by=2)
    assert bang_1["lap_bang"] == "A" and bang_1["napas_m"] == 10
    assert bang_2["lap_bang"] == "B" and bang_2["napas_m"] == 99

    days = svc.get_reconciliation_days(db)
    assert len(days) == 2  # 2 dòng riêng cho cùng 1 ngày, không gộp lại
    assert {d["created_by"] for d in days} == {1, 2}

    db.close()


def test_gop_napas_vao_bang_nguoi_khac_qua_target_created_by():
    db = _db()
    ngay = "20/08/2026"
    svc.session_save(
        db, ngay, 1,
        {"lap_bang": "A", "gD": {"cong1": 1}, "napas_m": 10, "napas_t": 20,
         "pssmdp_m": 1, "pssmdp_t": 2},
        "draft",
    )

    # Người 2 góp Napas/PSS-MDP vào ĐÚNG bảng của người 1 (target_created_by=1).
    svc.session_save(
        db, ngay, 2,
        {"lap_bang": "sẽ bị bỏ qua", "gD": {"cong1": 999}, "napas_m": 555, "napas_t": 666,
         "pssmdp_m": 777, "pssmdp_t": 888},
        "draft",
        target_created_by=1,
    )

    bang = svc.session_get(db, ngay, created_by=1)
    assert bang["lap_bang"] == "A"  # field ngoài Napas/PSS-MDP giữ nguyên
    assert bang["gD"] == {"cong1": 1}
    assert bang["napas_m"] == 555 and bang["pssmdp_t"] == 888  # 4 field Napas/PSS-MDP đổi

    # Người 2 không được chốt bản cuối bảng của người khác.
    with pytest.raises(svc.SessionForbiddenError):
        svc.session_save(db, ngay, 2, {"napas_m": 1, "napas_t": 1}, "final", target_created_by=1)

    db.close()


def test_khong_the_gop_vao_bang_chua_ton_tai():
    db = _db()
    with pytest.raises(svc.SessionForbiddenError):
        svc.session_save(db, "20/08/2026", 2, {"napas_m": 1, "napas_t": 1}, "draft", target_created_by=1)
    db.close()


def test_bang_da_final_khong_luu_tiep_duoc_nhung_bang_khac_cung_ngay_khong_bi_anh_huong():
    db = _db()
    ngay = "20/08/2026"
    svc.session_save(db, ngay, 1, {"napas_m": 1, "napas_t": 1}, "final")
    svc.session_save(db, ngay, 2, {"napas_m": 2, "napas_t": 2}, "draft")

    with pytest.raises(svc.SessionLockedError):
        svc.session_save(db, ngay, 1, {"napas_m": 9, "napas_t": 9}, "draft")

    # Bảng của người 2 (khác created_by) vẫn lưu tiếp được bình thường.
    svc.session_save(db, ngay, 2, {"napas_m": 3, "napas_t": 3}, "draft")
    assert svc.session_get(db, ngay, created_by=2)["napas_m"] == 3

    db.close()


def test_lich_su_moi_bang_tach_rieng_khong_lan_nhau():
    db = _db()
    db.executescript(
        "INSERT INTO user_tttt (id, username, full_name) VALUES "
        "(1, 'a', 'Nguyen A'), (2, 'b', 'Nguyen B')"
    )
    ngay = "20/08/2026"
    svc.session_save(db, ngay, 1, {"napas_m": 1, "napas_t": 1}, "draft")
    svc.session_save(db, ngay, 2, {"napas_m": 2, "napas_t": 2}, "draft")
    svc.session_save(db, ngay, 1, {"napas_m": 10, "napas_t": 10}, "draft")  # gộp vào dòng lịch sử của người 1

    hist_1 = svc.get_reconciliation_history(db, ngay, created_by=1)
    hist_2 = svc.get_reconciliation_history(db, ngay, created_by=2)
    assert len(hist_1) == 1  # 2 lần lưu liên tiếp của người 1 gộp thành 1 dòng
    assert len(hist_2) == 1
    assert hist_1[0]["staff_id"] == 1 and hist_2[0]["staff_id"] == 2

    db.close()


def test_reconciliation_status_tinh_theo_bat_ky_bang_nao_final_va_khop():
    db = _db()
    ngay = "20/08/2026"
    FK = ['di_ih_m', 'di_ih_t', 'di_il_m', 'di_il_t', 'den_ih_m', 'den_ih_t', 'den_il_m', 'den_il_t']

    def sess(napas_t=0):
        gD = {}
        phD = {u: {f: 0.0 for f in FK} for u in ['VNĐ', 'USD', 'EUR']}
        return dict(gD=gD, phD=phD, napas_m=0, napas_t=napas_t, pssmdp_m=0, pssmdp_t=0)

    # Bảng của người 1: draft, không tính.
    svc.session_save(db, ngay, 1, sess(napas_t=999), "draft")
    # Bảng của người 2: final và khớp (PaymentHub toàn 0, CITAD cũng toàn 0/napas=0).
    svc.session_save(db, ngay, 2, sess(napas_t=0), "final")

    status = svc.get_reconciliation_status(db, ngay)
    assert status == {"exists": True, "matched": True}

    db.close()
