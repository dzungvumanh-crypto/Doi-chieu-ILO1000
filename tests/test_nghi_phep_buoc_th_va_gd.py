"""Bước Tổng hợp và bước GĐ/PGĐ — hai kiểu "không có nút bấm" khác hẳn nhau.

1. Chuyên viên Phòng Tổng hợp được cấp `leaves.forward_th`: backend luôn cho
   thao tác (chỉ xét PHÒNG, không xét chức danh) — frontend từng chặn theo role
   nên ô tick phân quyền thành vô hiệu. Test khoá phía backend + khoá luôn việc
   frontend phải hỏi `has_feature`, không hardcode role.

2. Phó Giám đốc hết ủy quyền: backend chặn ĐÚNG, nhưng trước đây chặn im lặng —
   không danh sách, không nút, không lời giải thích. `gd_can_review` là cờ để
   màn hình nói ra được lý do.

Chạy: .venv/Scripts/python.exe -m pytest tests/test_nghi_phep_buoc_th_va_gd.py -v
"""

import re
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api.leaves import _leave_to_out
from backend.core.deps import get_current_staff
from backend.database import get_db
from backend.main import app

_SCHEMA = """
CREATE TABLE departments (id INTEGER PRIMARY KEY, code TEXT, name TEXT, is_source INTEGER DEFAULT 1);
CREATE TABLE user_tttt (id INTEGER PRIMARY KEY, full_name TEXT, username TEXT, role TEXT,
    employee_code TEXT, annual_leave_days REAL DEFAULT 12, used_leave_days REAL DEFAULT 0,
    department_id INTEGER, is_active INTEGER DEFAULT 1);
CREATE TABLE leave_records (id INTEGER PRIMARY KEY AUTOINCREMENT, staff_id INT, start_date TEXT,
    end_date TEXT, leave_type TEXT, reason TEXT, status TEXT, ksv_approver_id INT,
    ksv_approved_at TEXT, ksv_comment TEXT, tong_hop_approver_id INT, tong_hop_approved_at TEXT,
    tong_hop_comment TEXT, gd_approver_id INT, gd_approved_at TEXT, gd_comment TEXT,
    spread_dates TEXT, direct_by INT, is_direct INT, recall_reason TEXT,
    adjusts_leave_id INT, borrow_next_year_days REAL DEFAULT 0,
    created_at TEXT, updated_at TEXT);
CREATE TABLE leave_action_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, leave_id INT, actor_id INT,
    action TEXT, comment TEXT, from_status TEXT, to_status TEXT, created_at TEXT);
CREATE TABLE leave_quotas (staff_id INT, year INT, quota_days REAL);
CREATE TABLE public_holidays (date TEXT);
-- Lịch làm việc đọc cả bảng này (ngày lễ + ngày làm bù của Sổ trực),
-- xem backend/services/lich_lam_viec.py
CREATE TABLE duty_special_days (id INTEGER PRIMARY KEY AUTOINCREMENT, date DATE UNIQUE,
    day_type TEXT, label TEXT, is_confirmed INTEGER DEFAULT 0, created_at DATETIME);
CREATE TABLE delegation_records (id INTEGER PRIMARY KEY AUTOINCREMENT, giam_doc_id INT,
    pho_giam_doc_id INT, start_date TEXT, end_date TEXT, is_active INT DEFAULT 1, note TEXT,
    created_by_id INT, created_at TEXT);
CREATE TABLE user_groups (id INTEGER PRIMARY KEY, name TEXT, is_active INTEGER DEFAULT 1);
CREATE TABLE group_members (group_id INT, staff_id INT);
CREATE TABLE group_features (group_id INT, feature_code TEXT);
INSERT INTO departments (id, code, name, is_source) VALUES
    (5, 'KSNB', 'Phòng KSNB&HTVH', 1),
    (6, 'TH',   'Phòng Tổng hợp',  1),
    (7, 'BGD',  'Ban Giám đốc',    0);
INSERT INTO user_tttt (id, full_name, username, role, department_id) VALUES
    (1, 'Chuyên viên KSNB',   'cv',    'chuyen_vien',   5),
    (2, 'Trưởng phòng KSNB',  'tp',    'truong_phong',  5),
    (3, 'Chuyên viên TH',     'cvth',  'chuyen_vien',   6),
    (4, 'Giám đốc',           'gd',    'giam_doc',      7),
    (5, 'Phó Giám đốc',       'pgd',   'pho_giam_doc',  7);
-- Quyền đầy đủ cho mọi người: test này soi chốt chặn nghiệp vụ, không soi phân quyền nhóm.
INSERT INTO user_groups (id, name) VALUES (1, 'All');
INSERT INTO group_members (group_id, staff_id) VALUES (1,1),(1,2),(1,3),(1,4),(1,5);
INSERT INTO group_features (group_id, feature_code) VALUES
    (1, 'leaves.approve_gd'), (1, 'leaves.forward_th'), (1, 'leaves.create'), (1, 'menu.leaves');
"""

CV_KSNB, TP_KSNB, CV_TH, GD, PGD = 1, 2, 3, 4, 5

_STAFF = {
    CV_TH:  {"id": CV_TH,  "role": "chuyen_vien",   "department_id": 6, "username": "cvth"},
    CV_KSNB: {"id": CV_KSNB, "role": "chuyen_vien", "department_id": 5, "username": "cv"},
    GD:     {"id": GD,     "role": "giam_doc",      "department_id": 7, "username": "gd"},
    PGD:    {"id": PGD,    "role": "pho_giam_doc",  "department_id": 7, "username": "pgd"},
}


def _today() -> date:
    return date.today()


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    conn.commit()
    yield conn
    conn.close()


def _client(db, staff_id):
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: _STAFF[staff_id]
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear():
    yield
    app.dependency_overrides.clear()


def _don(db, status="pending_tong_hop", gd_id=GD):
    d = _today() + timedelta(days=3)
    cur = db.execute(
        "INSERT INTO leave_records (staff_id, start_date, end_date, leave_type, reason, status,"
        " ksv_approver_id, ksv_approved_at, gd_approver_id, created_at)"
        " VALUES (?,?,?,'annual','x',?,?,?,?,datetime('now'))",
        (CV_KSNB, d.isoformat(), d.isoformat(), status, TP_KSNB, str(_today()), gd_id),
    )
    db.commit()
    return cur.lastrowid


def _uy_quyen(db, tu: date, den: date, active=1):
    db.execute(
        "INSERT INTO delegation_records (giam_doc_id, pho_giam_doc_id, start_date, end_date,"
        " is_active, created_at) VALUES (?,?,?,?,?,datetime('now'))",
        (GD, PGD, tu.isoformat(), den.isoformat(), active),
    )
    db.commit()


# ── 1. Bước Tổng hợp phân quyền theo PHÒNG, không theo chức danh ─────────────

def test_chuyen_vien_phong_th_chuyen_duoc_don_len_ban_lanh_dao(db):
    lid = _don(db)
    r = _client(db, CV_TH).post(f"/api/leaves/{lid}/tong-hop-review",
                                json={"action": "forward", "gd_approver_id": GD})
    assert r.status_code == 200, r.text
    row = db.execute("SELECT status, tong_hop_approver_id FROM leave_records WHERE id=?", (lid,)).fetchone()
    assert row["status"] == "pending_gd"
    assert row["tong_hop_approver_id"] == CV_TH


def test_chuyen_vien_ngoai_phong_th_van_bi_chan(db):
    lid = _don(db)
    r = _client(db, CV_KSNB).post(f"/api/leaves/{lid}/tong-hop-review",
                                  json={"action": "forward", "gd_approver_id": GD})
    assert r.status_code == 403


def test_chuyen_vien_phong_th_thay_don_cho_buoc_tong_hop(db):
    _don(db)
    r = _client(db, CV_TH).get("/api/leaves/", params={"scope": "pending"})
    assert r.status_code == 200
    assert [x["status"] for x in r.json()] == ["pending_tong_hop"]


def test_frontend_khong_hardcode_role_o_cac_chot_buoc_tong_hop():
    """Bốn chốt frontend từng chặn theo role phải cùng hỏi feature `leaves.forward_th`.

    Chặn tái diễn kiểu "sửa một chỗ, ba chỗ còn lại vẫn khoá".
    """
    src = Path(__file__).resolve().parents[1] / "frontend" / "pages" / "leaves.py"
    code = src.read_text(encoding="utf-8")

    assert 'can_forward_th = api.has_feature("leaves.forward_th")' in code

    # Mọi lần loại trừ chuyên viên đều phải có đường thoát bằng feature.
    for m in re.finditer(r'user_role not in \("chuyen_vien",\)', code):
        doan = code[m.start(): m.start() + 120]
        assert "can_forward_th" in doan, f"còn chốt chặn theo role không hỏi feature: {doan!r}"

    assert 'th_act   = status == "pending_tong_hop" and in_pend and (_can_act or can_forward_th)' in code


# ── 2. Bước GĐ: PGĐ hết ủy quyền — chặn đúng nhưng phải nói ra lý do ─────────

def test_gd_can_review_false_khi_uy_quyen_het_han(db):
    lid = _don(db, status="pending_gd", gd_id=PGD)
    _uy_quyen(db, _today() - timedelta(days=10), _today() - timedelta(days=7))
    assert _leave_to_out(lid, db)["gd_can_review"] is False


def test_gd_can_review_false_khi_khong_co_uy_quyen_nao(db):
    lid = _don(db, status="pending_gd", gd_id=PGD)
    assert _leave_to_out(lid, db)["gd_can_review"] is False


def test_gd_can_review_false_khi_uy_quyen_bi_thu_hoi(db):
    lid = _don(db, status="pending_gd", gd_id=PGD)
    _uy_quyen(db, _today() - timedelta(days=1), _today() + timedelta(days=5), active=0)
    assert _leave_to_out(lid, db)["gd_can_review"] is False


def test_gd_can_review_true_khi_uy_quyen_con_hieu_luc(db):
    lid = _don(db, status="pending_gd", gd_id=PGD)
    _uy_quyen(db, _today(), _today())          # đúng 1 ngày, là hôm nay
    assert _leave_to_out(lid, db)["gd_can_review"] is True


def test_giam_doc_luon_can_review(db):
    """Giám đốc không cần ủy quyền — cờ phải True kể cả khi bảng ủy quyền rỗng."""
    lid = _don(db, status="pending_gd", gd_id=GD)
    assert _leave_to_out(lid, db)["gd_can_review"] is True


def test_pgd_het_uy_quyen_thi_bam_duyet_van_bi_tu_choi(db):
    """Cờ chỉ để giải thích — không được nới lỏng chốt chặn thật ở gd_review."""
    lid = _don(db, status="pending_gd", gd_id=PGD)
    r = _client(db, PGD).put(f"/api/leaves/{lid}/gd-review", json={"action": "approve"})
    assert r.status_code == 403


def test_frontend_hien_ly_do_khi_pgd_het_uy_quyen():
    src = Path(__file__).resolve().parents[1] / "frontend" / "pages" / "leaves.py"
    code = src.read_text(encoding="utf-8")
    assert 'status == "pending_gd" and not leave.get("gd_can_review", True)' in code
    assert 'lv.get("gd_can_review", True)' in code   # cảnh báo trước khi TH chuyển lên


# ── 3. Ủy quyền GĐ giao được qua "Phân quyền theo nhóm" ──────────────────────

def _cap_quyen(db, staff_id, code="leaves.delegation_admin"):
    db.execute("INSERT INTO user_groups (id, name) VALUES (9, 'Quản lý ủy quyền')")
    db.execute("INSERT INTO group_members (group_id, staff_id) VALUES (9, ?)", (staff_id,))
    db.execute("INSERT INTO group_features (group_id, feature_code) VALUES (9, ?)", (code,))
    db.commit()


def _body_uy_quyen():
    return {"giam_doc_id": GD, "pho_giam_doc_id": PGD,
            "start_date": _today().isoformat(),
            "end_date": (_today() + timedelta(days=30)).isoformat(),
            "note": "Ủy quyền thử"}


def test_feature_uy_quyen_co_trong_danh_muc_va_cay_phan_quyen():
    from backend.core.features import FEATURES, FEATURE_GROUPS
    assert "leaves.delegation_admin" in FEATURES
    # menu.leaves nay dung o cap 1 (kind="menu"), khong con nam trong "sections" —
    # duyet ca hai dang node de test khong gay khi cay menu doi hinh.
    def _menus(g):
        if g["kind"] == "menu":
            return [g]
        return [m for s in g["sections"] for m in s["menus"]]

    actions = [a for g in FEATURE_GROUPS for m in _menus(g)
               if m["code"] == "menu.leaves" for a in m["actions"]]
    assert "leaves.delegation_admin" in actions, "ô tick không hiện trên màn Phân quyền theo nhóm"


def test_khong_co_o_tick_thi_khong_tao_duoc_uy_quyen(db):
    r = _client(db, CV_TH).post("/api/delegations/", json=_body_uy_quyen())
    assert r.status_code == 403


def test_co_o_tick_thi_tao_duoc_uy_quyen(db):
    _cap_quyen(db, CV_TH)
    r = _client(db, CV_TH).post("/api/delegations/", json=_body_uy_quyen())
    assert r.status_code == 200, r.text
    assert db.execute("SELECT COUNT(*) c FROM delegation_records").fetchone()["c"] == 1


def test_uy_quyen_vua_cap_lam_pgd_duyet_duoc_ngay(db):
    """Vòng khép kín: cấp ô tick → tạo ủy quyền → cờ gd_can_review bật lên."""
    lid = _don(db, status="pending_gd", gd_id=PGD)
    assert _leave_to_out(lid, db)["gd_can_review"] is False
    _cap_quyen(db, CV_TH)
    assert _client(db, CV_TH).post("/api/delegations/", json=_body_uy_quyen()).status_code == 200
    assert _leave_to_out(lid, db)["gd_can_review"] is True
    assert _client(db, PGD).put(f"/api/leaves/{lid}/gd-review",
                                json={"action": "approve"}).status_code == 200


def test_o_tick_khong_mo_nham_tab_ngay_le():
    """can_delegation và can_holiday phải là HAI biến — trước đây dùng chung một."""
    src = Path(__file__).resolve().parents[1] / "frontend" / "pages" / "leaves.py"
    code = src.read_text(encoding="utf-8")
    assert 'can_delegation = api.has_feature("leaves.delegation_admin")' in code
    assert 'can_holiday    = user_role == "admin"' in code
    assert 'ui.tab("Ngày lễ") if can_holiday else None' in code
