import sqlite3

import pytest

from backend.services import doi_chieu_citad_service as svc

# KHÔNG còn UNIQUE(ngay, created_by) — bỏ từ migration rebuild lần 3
# (07/09/2026, xem backend/db/migrations.py): 1 người giờ có thể có NHIỀU
# bảng độc lập trong CÙNG 1 ngày, khoá bảng chỉ còn `id`.
_SCHEMA = """
CREATE TABLE doi_chieu_citad_sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ngay       TEXT    NOT NULL,
    data       TEXT    NOT NULL,
    updated_at DATETIME,
    updated_by INTEGER,
    status     TEXT    NOT NULL DEFAULT 'final',
    created_by INTEGER
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


# Bản có khai FK thật (ON DELETE SET NULL) — khớp đúng
# backend/db/migrations.py, dùng riêng cho test xoá bảng không mất lịch sử
# (review Người 1 PR#76: bug thật CASCADE xoá theo lịch sử). `_SCHEMA` ở
# trên không khai FK nên không bắt được lỗi loại này.
_SCHEMA_FK = _SCHEMA.replace(
    "session_id INTEGER,",
    "session_id INTEGER REFERENCES doi_chieu_citad_sessions(id) ON DELETE SET NULL,",
)


def _db_fk():
    db = sqlite3.connect(":memory:", check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(_SCHEMA_FK)
    return db


def test_hai_nguoi_khac_nhau_moi_nguoi_1_bang_rieng():
    """Bug đã báo: trước đây 1 ngày chỉ 1 người chấm được, người khác chấm
    cùng ngày (dù chỉ Napas) bị chặn cứng. Nay mỗi người phải tự lập được
    bảng RIÊNG của mình cho cùng 1 ngày, không đụng bảng người khác."""
    db = _db()
    ngay = "20/08/2026"

    id_1 = svc.session_save(db, ngay, 1, {"napas_m": 10, "napas_t": 20, "lap_bang": "A"}, "draft")
    # Người 2 không truyền session_id — phải tự lập bảng RIÊNG, không bị
    # lỗi, không đè lên bảng người 1.
    id_2 = svc.session_save(db, ngay, 2, {"napas_m": 99, "napas_t": 88, "lap_bang": "B"}, "draft")
    assert id_1 != id_2

    bang_1 = svc.session_get(db, id_1)
    bang_2 = svc.session_get(db, id_2)
    assert bang_1["lap_bang"] == "A" and bang_1["napas_m"] == 10
    assert bang_2["lap_bang"] == "B" and bang_2["napas_m"] == 99

    days = svc.get_reconciliation_days(db)
    assert len(days) == 2  # 2 dòng riêng cho cùng 1 ngày, không gộp lại
    assert {d["created_by"] for d in days} == {1, 2}

    db.close()


def test_khong_truyen_session_id_luon_tao_bang_moi_doc_lap():
    """Trọng tâm của thay đổi 07/09/2026: 1 người lưu bảng tạm ngày X, KHÔNG
    bấm "Tải" tiếp tục bảng cũ (nghĩa là KHÔNG truyền session_id) mà gõ lại
    từ đầu rồi lưu tiếp — phải ra 1 bảng MỚI hoàn toàn tách biệt, không đè
    lên bảng trước của chính họ. Truyền ĐÚNG session_id thì mới lưu tiếp
    (update in-place) vào đúng bảng đó — hành vi giữ nguyên như PR#76."""
    db = _db()
    ngay = "20/08/2026"

    id_1 = svc.session_save(db, ngay, 1, {"napas_m": 1, "napas_t": 1, "lap_bang": "Lần 1"}, "draft")
    # Không truyền session_id lần 2 — dù CÙNG 1 người, CÙNG 1 ngày.
    id_2 = svc.session_save(db, ngay, 1, {"napas_m": 2, "napas_t": 2, "lap_bang": "Lần 2"}, "draft")
    assert id_1 != id_2  # 2 bảng độc lập, không phải update đè

    bang_1 = svc.session_get(db, id_1)
    bang_2 = svc.session_get(db, id_2)
    assert bang_1["lap_bang"] == "Lần 1" and bang_1["napas_m"] == 1
    assert bang_2["lap_bang"] == "Lần 2" and bang_2["napas_m"] == 2

    days = svc.get_reconciliation_days(db)
    assert len(days) == 2  # cùng 1 người, cùng 1 ngày, vẫn 2 dòng bảng riêng
    assert {d["session_id"] for d in days} == {id_1, id_2}

    # Truyền ĐÚNG session_id lần 3 — lưu tiếp vào bảng 2, KHÔNG tạo bảng mới.
    id_3 = svc.session_save(db, ngay, 1, {"napas_m": 20, "napas_t": 20, "lap_bang": "Lần 2 sửa"}, "draft", session_id=id_2)
    assert id_3 == id_2
    assert svc.session_get(db, id_2)["lap_bang"] == "Lần 2 sửa"
    assert len(svc.get_reconciliation_days(db)) == 2  # vẫn 2 bảng, không đẻ thêm

    db.close()


def test_gop_napas_vao_bang_nguoi_khac_qua_session_id():
    db = _db()
    ngay = "20/08/2026"
    id_1 = svc.session_save(
        db, ngay, 1,
        {"lap_bang": "A", "gD": {"cong1": 1}, "napas_m": 10, "napas_t": 20,
         "pssmdp_m": 1, "pssmdp_t": 2},
        "draft",
    )

    # Người 2 góp Napas/PSS-MDP vào ĐÚNG bảng của người 1 (session_id=id_1).
    svc.session_save(
        db, ngay, 2,
        {"lap_bang": "sẽ bị bỏ qua", "gD": {"cong1": 999}, "napas_m": 555, "napas_t": 666,
         "pssmdp_m": 777, "pssmdp_t": 888},
        "draft",
        session_id=id_1,
    )

    bang = svc.session_get(db, id_1)
    assert bang["lap_bang"] == "A"  # field ngoài Napas/PSS-MDP giữ nguyên
    assert bang["gD"] == {"cong1": 1}
    assert bang["napas_m"] == 555 and bang["pssmdp_t"] == 888  # 4 field Napas/PSS-MDP đổi

    # Người 2 không được chốt bản cuối bảng của người khác.
    with pytest.raises(svc.SessionForbiddenError):
        svc.session_save(db, ngay, 2, {"napas_m": 1, "napas_t": 1}, "final", session_id=id_1)

    db.close()


def test_xem_1_dong_lich_su_hien_dung_nguoi_da_luu_dong_do():
    """Phản hồi thật (07/09/2026): bấm "Tải" vào dòng người 2 lưu (góp Napas
    vào bảng người 1) thì màn hình chỉ thấy tên người 1 (chủ bảng) khắp nơi,
    tưởng nhầm người 1 tự lưu hết. get_history_entry_data() phải trả kèm
    _meta_entry_staff_* — người THỰC SỰ lưu ĐÚNG dòng đó — tách biệt với
    _meta_created_by (chủ bảng, cố định, không đổi theo người lưu sau)."""
    db = _db()
    db.executescript(
        "INSERT INTO user_tttt (id, username, full_name) VALUES "
        "(1, 'trung', 'Nguyen Van Trung'), (2, 'lan', 'Tran Thi Lan')"
    )
    ngay = "20/08/2026"
    id_1 = svc.session_save(db, ngay, 1, {"lap_bang": "Trung", "napas_m": 1, "napas_t": 1}, "draft")
    svc.session_save(db, ngay, 2, {"napas_m": 555, "napas_t": 666}, "draft", session_id=id_1)

    hist = svc.get_reconciliation_history(db, id_1)
    assert len(hist) == 2  # 2 dòng — người 1 lưu 1 lần, người 2 lưu 1 lần, KHÔNG gộp

    entry_1 = svc.get_history_entry_data(db, hist[0]["id"])
    entry_2 = svc.get_history_entry_data(db, hist[1]["id"])

    # Cả 2 dòng đều thuộc bảng của người 1 (chủ bảng cố định) — cùng session_id.
    assert entry_1["_meta_session_id"] == id_1 and entry_2["_meta_session_id"] == id_1
    assert entry_1["_meta_created_by"] == 1 and entry_2["_meta_created_by"] == 1
    # Nhưng người THỰC SỰ lưu từng dòng phải đúng — dòng 1 là Trung, dòng 2 là Lan.
    assert entry_1["_meta_entry_staff_id"] == 1
    assert entry_1["_meta_entry_staff_name"] == "Nguyen Van Trung"
    assert entry_2["_meta_entry_staff_id"] == 2
    assert entry_2["_meta_entry_staff_name"] == "Tran Thi Lan"

    db.close()


def test_luu_vao_session_id_khong_ton_tai_bao_loi():
    db = _db()
    with pytest.raises(svc.SessionNotFoundError):
        svc.session_save(db, "20/08/2026", 2, {"napas_m": 1, "napas_t": 1}, "draft", session_id=999)
    db.close()


def test_bang_da_final_khong_luu_tiep_duoc_nhung_bang_khac_cung_ngay_khong_bi_anh_huong():
    db = _db()
    ngay = "20/08/2026"
    id_1 = svc.session_save(db, ngay, 1, {"napas_m": 1, "napas_t": 1}, "final")
    id_2 = svc.session_save(db, ngay, 2, {"napas_m": 2, "napas_t": 2}, "draft")

    with pytest.raises(svc.SessionLockedError):
        svc.session_save(db, ngay, 1, {"napas_m": 9, "napas_t": 9}, "draft", session_id=id_1)

    # Bảng của người 2 (bảng khác) vẫn lưu tiếp được bình thường.
    svc.session_save(db, ngay, 2, {"napas_m": 3, "napas_t": 3}, "draft", session_id=id_2)
    assert svc.session_get(db, id_2)["napas_m"] == 3

    db.close()


def test_lich_su_moi_bang_tach_rieng_khong_lan_nhau():
    db = _db()
    db.executescript(
        "INSERT INTO user_tttt (id, username, full_name) VALUES "
        "(1, 'a', 'Nguyen A'), (2, 'b', 'Nguyen B')"
    )
    ngay = "20/08/2026"
    id_1 = svc.session_save(db, ngay, 1, {"napas_m": 1, "napas_t": 1}, "draft")
    id_2 = svc.session_save(db, ngay, 2, {"napas_m": 2, "napas_t": 2}, "draft")
    # Lưu tiếp ĐÚNG bảng cũ của người 1 (truyền session_id) — gộp vào cùng 1
    # dòng lịch sử, KHÔNG tạo bảng/dòng lịch sử mới.
    svc.session_save(db, ngay, 1, {"napas_m": 10, "napas_t": 10}, "draft", session_id=id_1)

    hist_1 = svc.get_reconciliation_history(db, id_1)
    hist_2 = svc.get_reconciliation_history(db, id_2)
    assert len(hist_1) == 1  # 2 lần lưu liên tiếp CÙNG bảng gộp thành 1 dòng
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


def test_xoa_bang_tam_khong_lam_mat_lich_su():
    """Bug thật (review Người 1 PR#76, đo trực tiếp trên DB): session_id
    từng khai ON DELETE CASCADE — xoá 1 bảng TẠM (session_delete(), chỉ xoá
    được bảng chưa chốt) xoá theo LUÔN toàn bộ dòng lịch sử của bảng đó,
    mất dấu vết "ai đã chấm gì lúc nào" mà dialog Xoá không hề cảnh báo. Đã
    đổi sang ON DELETE SET NULL — lịch sử phải còn nguyên sau khi xoá."""
    db = _db_fk()
    db.executescript("INSERT INTO user_tttt (id, username, full_name) VALUES (1, 'a', 'Nguyen A')")
    ngay = "20/08/2026"
    id_1 = svc.session_save(db, ngay, 1, {"napas_m": 1, "napas_t": 1}, "draft")

    hist_before = svc.get_reconciliation_history(db, id_1)
    assert len(hist_before) == 1

    svc.session_delete(db, id_1, 1)

    row = db.execute(
        "SELECT ngay, staff_id, session_id FROM doi_chieu_citad_history WHERE id=?",
        (hist_before[0]["id"],),
    ).fetchone()
    assert row is not None  # dòng lịch sử KHÔNG bị xoá theo
    assert row["ngay"] == ngay and row["staff_id"] == 1
    assert row["session_id"] is None  # chỉ rời khỏi bảng đã xoá (SET NULL)

    db.close()


def test_xoa_bang_nguoi_khac_bao_loi_ro_rang():
    """07/09/2026: session_delete() giờ nhận thẳng `session_id` — thêm kiểm
    `created_by != staff_id` tường minh (SessionForbiddenError), khác bản cũ
    chỉ ngầm định đúng qua điều kiện WHERE ngay=?/created_by=? (không có
    thông báo lỗi riêng khi người khác cố xoá bảng không phải của mình)."""
    db = _db()
    ngay = "20/08/2026"
    id_1 = svc.session_save(db, ngay, 1, {"napas_m": 1, "napas_t": 1}, "draft")

    with pytest.raises(svc.SessionForbiddenError):
        svc.session_delete(db, id_1, 2)  # người 2 không phải chủ bảng

    assert svc.session_get(db, id_1) is not None  # bảng của người 1 vẫn còn nguyên

    with pytest.raises(svc.SessionNotFoundError):
        svc.session_delete(db, 999, 1)

    db.close()


def test_unlock_khong_ton_tai_bao_loi_ro_rang():
    """Bug thật (review Người 1 PR#76): UPDATE không khớp dòng nào (vd bảng
    đã bị xoá, hoặc id sai) từng lặng lẽ trả thành công — Admin thấy "Đã mở
    khoá" dù thực ra không có gì đổi. Nay phải báo lỗi rõ. 07/09/2026:
    session_admin_unlock() giờ chỉ nhận `session_id` — `id` đã đủ xác định
    đúng 1 bảng, không cần created_by nữa."""
    db = _db()
    ngay = "20/08/2026"
    id_1 = svc.session_save(db, ngay, 1, {"napas_m": 1, "napas_t": 1}, "final")

    with pytest.raises(svc.SessionNotFoundError):
        svc.session_admin_unlock(db, 999)

    # Bảng thật của người 1 vẫn nguyên trạng thái final, không bị đổi nhầm.
    assert svc.session_get(db, id_1)["_meta_status"] == "final"

    svc.session_admin_unlock(db, id_1)
    assert svc.session_get(db, id_1)["_meta_status"] == "draft"

    db.close()
