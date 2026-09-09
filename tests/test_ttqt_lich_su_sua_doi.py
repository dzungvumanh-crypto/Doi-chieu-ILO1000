"""Danh sách CN TTQT — lịch sử sửa đổi từng chi nhánh.

Canh ba điều dễ hỏng lặng lẽ: ghi đúng trường nào đã đổi (không đẻ dòng "đã sửa"
khi thật ra không đổi gì), nhập lại đúng file cũ không sinh lịch sử rác, và lịch
sử không biến mất khi chi nhánh bị xoá rồi nhập lại dưới id mới.
"""
import io as _io
import sqlite3

import openpyxl
import pytest
from fastapi.testclient import TestClient

from backend.core.deps import get_current_staff
from backend.database import get_db
from backend.db.migrations import _create_tables
from backend.main import app


@pytest.fixture
def db(tmp_path):
    duong = tmp_path / "ttqt.db"
    _create_tables(str(duong))
    conn = sqlite3.connect(duong, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "INSERT INTO user_tttt (id, employee_code, full_name, role, username, pwd_hash, is_active)"
        " VALUES (7, 'NS007', 'Phạm Thị Duyên', 'chuyen_vien', 'duyen', 'x', 1)"
    )
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_current_staff] = lambda: dict(
        db.execute("SELECT * FROM user_tttt WHERE id = 7").fetchone()
    )
    app.dependency_overrides[get_db] = lambda: db
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()


def _cap_quyen(db, *codes):
    gid = db.execute("INSERT INTO user_groups (name, is_active) VALUES ('T', 1)").lastrowid
    db.execute("INSERT INTO group_members (group_id, staff_id) VALUES (?, 7)", (gid,))
    for c in codes:
        db.execute("INSERT INTO group_features (group_id, feature_code) VALUES (?, ?)", (gid, c))
    db.commit()


_MOI = {"ma_cn": "9999", "ten_cn": "CN Thử Nghiệm", "swift_bic": "VBAAVNVX999",
        "loai_cn": 1, "sdt": "0243 111 2222"}


def _file_excel(rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["MÃ CN", "TÊN CN", "SWIFT BIC", "LOẠI CN", "SĐT"])
    for r in rows:
        ws.append(r)
    buf = _io.BytesIO()
    wb.save(buf)
    return {"file": ("ds.xlsx", buf.getvalue(),
                     "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}


# ── Thêm mới ─────────────────────────────────────────────────────────────────
def test_them_moi_ghi_mot_dong_lich_su(client, db):
    _cap_quyen(db, "ttqt_branches.create", "ttqt_branches.history")
    bid = client.post("/api/ttqt-branches/", json=_MOI).json()["id"]

    h = client.get(f"/api/ttqt-branches/{bid}/history").json()
    assert len(h) == 1
    assert h[0]["action_label"] == "Thêm mới"
    assert h[0]["actor_name"] == "Phạm Thị Duyên"
    assert h[0]["created_at"]
    assert "9999" in h[0]["new_value"]


# ── Sửa ──────────────────────────────────────────────────────────────────────
def test_sua_ghi_dung_truong_da_doi(client, db):
    _cap_quyen(db, "ttqt_branches.create", "ttqt_branches.edit", "ttqt_branches.history")
    bid = client.post("/api/ttqt-branches/", json=_MOI).json()["id"]

    client.patch(f"/api/ttqt-branches/{bid}",
                 json={**_MOI, "ten_cn": "CN Đã Đổi Tên", "is_closed": True})
    h = client.get(f"/api/ttqt-branches/{bid}/history").json()

    sua = {x["field"]: x for x in h if x["action"] == "update"}
    assert set(sua) == {"ten_cn", "is_closed"}          # sdt / bic không đổi → không ghi
    assert sua["ten_cn"]["old_value"] == "CN Thử Nghiệm"
    assert sua["ten_cn"]["new_value"] == "CN Đã Đổi Tên"
    assert sua["ten_cn"]["field_label"] == "TÊN CN"
    assert sua["is_closed"]["old_value"] == "Đang hoạt động"
    assert sua["is_closed"]["new_value"] == "Đã đóng BIC"


def test_luu_lai_y_nguyen_khong_sinh_lich_su(client, db):
    """Bấm Lưu mà không sửa gì → không được đẻ dòng lịch sử giả."""
    _cap_quyen(db, "ttqt_branches.create", "ttqt_branches.edit", "ttqt_branches.history")
    bid = client.post("/api/ttqt-branches/", json=_MOI).json()["id"]
    client.patch(f"/api/ttqt-branches/{bid}", json=_MOI)

    h = client.get(f"/api/ttqt-branches/{bid}/history").json()
    assert [x["action"] for x in h] == ["create"]


def test_o_trong_gui_len_chuoi_rong_khong_tinh_la_doi(client, db):
    """Form web gửi chuỗi rỗng cho ô trống, DB lưu NULL — hai thứ đó là MỘT."""
    _cap_quyen(db, "ttqt_branches.create", "ttqt_branches.edit", "ttqt_branches.history")
    bid = client.post("/api/ttqt-branches/", json=_MOI).json()["id"]
    client.patch(f"/api/ttqt-branches/{bid}", json={**_MOI, "ghi_chu": "", "dia_chi": "   "})

    h = client.get(f"/api/ttqt-branches/{bid}/history").json()
    assert [x["action"] for x in h] == ["create"]


# ── Phân quyền ───────────────────────────────────────────────────────────────
def test_khong_co_quyen_thi_403(client, db):
    _cap_quyen(db, "ttqt_branches.create")
    bid = client.post("/api/ttqt-branches/", json=_MOI).json()["id"]
    assert client.get(f"/api/ttqt-branches/{bid}/history").status_code == 403


def test_chi_nhanh_khong_ton_tai_thi_404(client, db):
    _cap_quyen(db, "ttqt_branches.history")
    assert client.get("/api/ttqt-branches/98765/history").status_code == 404


# ── Nhập Excel ───────────────────────────────────────────────────────────────
def test_nhap_excel_ghi_lich_su_theo_tung_truong(client, db):
    _cap_quyen(db, "ttqt_branches.import", "ttqt_branches.history")
    client.post("/api/ttqt-branches/import",
                files=_file_excel([["9999", "CN Thử Nghiệm", "VBAAVNVX999", 1, "0243 111 2222"]]))
    bid = db.execute("SELECT id FROM ttqt_branches WHERE ma_cn = '9999'").fetchone()["id"]

    # Nhập lại y hệt → không thêm dòng lịch sử nào
    client.post("/api/ttqt-branches/import",
                files=_file_excel([["9999", "CN Thử Nghiệm", "VBAAVNVX999", 1, "0243 111 2222"]]))
    h = client.get(f"/api/ttqt-branches/{bid}/history").json()
    assert [x["action"] for x in h] == ["import"]

    # Nhập bản có SĐT mới → đúng một dòng "sdt"
    client.post("/api/ttqt-branches/import",
                files=_file_excel([["9999", "CN Thử Nghiệm", "VBAAVNVX999", 1, "0243 999 8888"]]))
    h = client.get(f"/api/ttqt-branches/{bid}/history").json()
    assert h[0]["field"] == "sdt"
    assert h[0]["action_label"] == "Nhập Excel"
    assert h[0]["old_value"] == "0243 111 2222"
    assert h[0]["new_value"] == "0243 999 8888"


def test_xoa_roi_nhap_lai_van_thay_lich_su_cu(client, db):
    """Nhập có tích "Xoá CN thiếu" rồi nhập lại sinh id MỚI cho cùng mã CN —
    lịch sử cũ phải theo được sang bản ghi mới, nếu không mọi dấu vết biến mất."""
    _cap_quyen(db, "ttqt_branches.import", "ttqt_branches.history")
    client.post("/api/ttqt-branches/import",
                files=_file_excel([["9999", "CN Thử Nghiệm", "VBAAVNVX999", 1, "0243 111 2222"]]))
    client.post("/api/ttqt-branches/import?delete_missing=true",
                files=_file_excel([["8888", "CN Khác", "VBAAVNVX888", 2, ""]]))
    client.post("/api/ttqt-branches/import",
                files=_file_excel([["8888", "CN Khác", "VBAAVNVX888", 2, ""],
                                   ["9999", "CN Thử Nghiệm", "VBAAVNVX999", 1, "0243 111 2222"]]))

    bid_moi = db.execute("SELECT id FROM ttqt_branches WHERE ma_cn = '9999'").fetchone()["id"]
    h = client.get(f"/api/ttqt-branches/{bid_moi}/history").json()
    assert [x["action"] for x in h] == ["import", "delete", "import"]   # mới nhất đứng trước


def test_khong_keo_nham_lich_su_cua_chi_nhanh_con_song(client, db):
    """Hai chi nhánh khác nhau: lịch sử của bên này không được lọt sang bên kia."""
    _cap_quyen(db, "ttqt_branches.create", "ttqt_branches.history")
    a = client.post("/api/ttqt-branches/", json=_MOI).json()["id"]
    b = client.post("/api/ttqt-branches/",
                    json={**_MOI, "ma_cn": "8888", "ten_cn": "CN Khác"}).json()["id"]

    assert len(client.get(f"/api/ttqt-branches/{a}/history").json()) == 1
    assert len(client.get(f"/api/ttqt-branches/{b}/history").json()) == 1
