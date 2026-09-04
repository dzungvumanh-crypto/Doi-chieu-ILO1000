"""Chữ ký trên đơn nghỉ phép — đặt vị trí, lưu bản sao ảnh, dán lên PDF.

Word không có trong môi trường test nên bước docx → pdf được thay bằng một trang
A4 trắng dựng sẵn; phần còn lại (toạ độ, dán ảnh, quyền, vòng đời chữ ký) chạy thật.
"""
import io
import sqlite3

import pytest
from fastapi.testclient import TestClient

from backend.core.deps import get_current_staff
from backend.database import get_db
from backend.main import app
from backend.services import leave_pdf

pdfium = pytest.importorskip("pypdfium2")
PIL = pytest.importorskip("PIL")
from PIL import Image, ImageDraw   # noqa: E402


def _png(w=400, h=150, color=(15, 30, 160, 255)) -> bytes:
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(img).rectangle([0, 0, w - 1, h - 1], fill=color)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _blank_a4() -> bytes:
    doc = pdfium.PdfDocument.new()
    doc.new_page(595.44, 842.04)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


SIG = _png()


# ── Dán ảnh lên PDF ──────────────────────────────────────────────────────────

def test_dan_dung_vi_tri_va_kich_thuoc():
    pdf = leave_pdf.stamp(_blank_a4(), [
        {"page": 0, "x_mm": 50, "y_mm": 100, "w_mm": 40, "h_mm": 15, "image": SIG},
    ])
    png, w_mm, h_mm, _ = leave_pdf.page_png(pdf, 0, dpi=100)
    im = Image.open(io.BytesIO(png)).convert("RGB")
    ppm = im.width / w_mm

    def px(x_mm, y_mm):
        return im.getpixel((int(x_mm * ppm), int(y_mm * ppm)))

    assert px(70, 107)[2] > 120 and px(70, 107)[0] < 90     # giữa khung → có mực xanh
    assert px(70, 90) == (255, 255, 255)                     # phía trên khung → trắng
    assert px(70, 125) == (255, 255, 255)                    # phía dưới khung → trắng
    assert px(30, 107) == (255, 255, 255)                    # bên trái khung → trắng


def test_khong_co_chu_ky_thi_tra_lai_nguyen_ban():
    goc = _blank_a4()
    assert leave_pdf.stamp(goc, []) is goc


def test_nhieu_chu_ky_tren_cung_mot_trang():
    """Mỗi ô ký một ảnh — cùng trang phải hiện đủ, không đè mất nhau."""
    pdf = leave_pdf.stamp(_blank_a4(), [
        {"page": 0, "x_mm": 30, "y_mm": 100, "w_mm": 30, "h_mm": 12, "image": SIG},
        {"page": 0, "x_mm": 120, "y_mm": 100, "w_mm": 30, "h_mm": 12, "image": SIG},
        {"page": 0, "x_mm": 120, "y_mm": 150, "w_mm": 30, "h_mm": 12, "image": SIG},
    ])
    png, w_mm, _, _ = leave_pdf.page_png(pdf, 0, dpi=100)
    im = Image.open(io.BytesIO(png)).convert("RGB")
    ppm = im.width / w_mm
    for x, y in ((45, 106), (135, 106), (135, 156)):
        assert im.getpixel((int(x * ppm), int(y * ppm)))[2] > 120, f"thiếu chữ ký ở ({x},{y})"


# ── API ───────────────────────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE user_tttt (id INTEGER PRIMARY KEY, full_name TEXT, username TEXT, role TEXT,
    employee_code TEXT, annual_leave_days REAL, used_leave_days REAL, join_industry_date TEXT,
    department_id INTEGER, is_active INTEGER DEFAULT 1);
CREATE TABLE departments (id INTEGER PRIMARY KEY, name TEXT, code TEXT, is_source INTEGER DEFAULT 1);
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
CREATE TABLE user_signatures (staff_id INTEGER PRIMARY KEY, filename TEXT, image BLOB, updated_at TEXT);
CREATE TABLE leave_signatures (id INTEGER PRIMARY KEY AUTOINCREMENT, leave_id INT, slot TEXT,
    staff_id INT, page INT, x_mm REAL, y_mm REAL, w_mm REAL, h_mm REAL, image BLOB, signed_at TEXT);
CREATE TABLE user_groups (id INTEGER PRIMARY KEY, name TEXT, is_active INTEGER DEFAULT 1);
CREATE TABLE group_members (group_id INT, staff_id INT);
CREATE TABLE group_features (group_id INT, feature_code TEXT);
CREATE TABLE audit_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, actor_id INT, action TEXT,
    target_type TEXT, target_id INT, detail TEXT, ip_address TEXT, created_at TEXT);
CREATE TABLE login_sessions (staff_id INTEGER PRIMARY KEY, ip_address TEXT, session_key TEXT, expires_at TEXT);
CREATE TABLE delegation_records (id INTEGER PRIMARY KEY AUTOINCREMENT, giam_doc_id INT,
    pho_giam_doc_id INT, start_date TEXT, end_date TEXT, is_active INT, note TEXT,
    created_by INT, created_at TEXT);
"""

NV, TP, GD = 1, 2, 3          # chuyên viên / trưởng phòng (KSV) / giám đốc


@pytest.fixture
def client(monkeypatch):
    leave_pdf.drop_cache()
    # Không gọi Word trong test — trả thẳng một trang A4 trắng.
    monkeypatch.setattr(leave_pdf, "docx_to_pdf", lambda _b: _blank_a4())

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    conn.execute("INSERT INTO departments (id,name,code) VALUES (1,'Phòng Thanh toán','TT')")
    conn.executemany(
        "INSERT INTO user_tttt (id,full_name,username,role,employee_code,annual_leave_days,"
        "used_leave_days,join_industry_date,department_id,is_active) VALUES (?,?,?,?,?,12,0,?,1,1)",
        [(NV, "Nguyễn Văn A", "a", "chuyen_vien", "NV001", "2015-01-01"),
         (TP, "Trần Thị B", "b", "truong_phong", "NV002", "2010-01-01"),
         (GD, "Lê Văn C", "c", "giam_doc", "NV003", "2005-01-01")],
    )
    conn.execute("INSERT INTO user_groups (id,name) VALUES (1,'Nhân viên')")
    conn.executemany("INSERT INTO group_members VALUES (1,?)", [(NV,), (TP,), (GD,)])
    conn.executemany("INSERT INTO group_features VALUES (1,?)",
                     [("leaves.create",), ("leaves.resubmit",),
                      ("leaves.approve_ksv",), ("leaves.approve_gd",)])
    conn.executemany("INSERT INTO user_signatures VALUES (?,?,?,?)",
                     [(NV, "a.png", SIG, "2026-08-14"), (TP, "b.png", SIG, "2026-08-14"),
                      (GD, "c.png", SIG, "2026-08-14")])
    conn.commit()

    who = {"id": NV}

    def _staff():
        r = conn.execute("SELECT * FROM user_tttt WHERE id=?", (who["id"],)).fetchone()
        return dict(r)

    def _db():
        yield conn

    app.dependency_overrides[get_current_staff] = _staff
    app.dependency_overrides[get_db] = _db
    c = TestClient(app)
    c.conn, c.who = conn, who
    yield c
    app.dependency_overrides.clear()
    conn.close()


_BOX = {"page": 0, "x_mm": 120.0, "y_mm": 180.0, "w_mm": 38.0, "h_mm": 14.0}


def _tao_don(client, **kw):
    body = {"start_date": "2026-12-01", "end_date": "2026-12-02", "leave_type": "annual",
            "reason": "Việc riêng", "ksv_approver_id": TP, "gd_approver_id": GD}
    body.update(kw)
    return client.post("/api/leaves/", json=body)


def test_xem_truoc_ban_nhap_co_anh_trang_va_khung_goi_y(client):
    r = client.post("/api/leaves/preview", json={
        "start_date": "2026-12-01", "end_date": "2026-12-02", "leave_type": "annual",
        "reason": "Việc riêng", "ksv_approver_id": TP, "gd_approver_id": GD})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["page_png"].startswith("data:image/png;base64,")
    assert 200 < body["page_w_mm"] < 215 and 290 < body["page_h_mm"] < 300
    assert body["slot"] == "nguoi_de_nghi"
    assert body["signature"]["data_url"].startswith("data:image/png;base64,")
    for k in ("x_mm", "y_mm", "w_mm", "h_mm"):
        assert body["suggest"][k] > 0


def test_tao_don_kem_chu_ky_luu_ban_sao_anh(client):
    assert _tao_don(client, signature=_BOX).status_code == 200
    row = client.conn.execute(
        "SELECT * FROM leave_signatures WHERE slot='nguoi_de_nghi'").fetchone()
    assert row["staff_id"] == NV and row["x_mm"] == 120.0 and row["w_mm"] == 38.0
    assert row["image"] == SIG          # ảnh được sao lại, không tham chiếu

    # Người dùng đổi ảnh chữ ký cá nhân → đơn đã ký KHÔNG đổi theo
    client.conn.execute("UPDATE user_signatures SET image=? WHERE staff_id=?", (_png(10, 10), NV))
    client.conn.commit()
    assert client.conn.execute(
        "SELECT image FROM leave_signatures WHERE slot='nguoi_de_nghi'").fetchone()["image"] == SIG


def test_chua_tai_anh_chu_ky_thi_bao_loi(client):
    client.conn.execute("DELETE FROM user_signatures WHERE staff_id=?", (NV,))
    client.conn.commit()
    r = _tao_don(client, signature=_BOX)
    assert r.status_code == 400 and "ảnh chữ ký" in r.json()["detail"]


def test_khong_ky_van_tao_duoc_don(client):
    assert _tao_don(client).status_code == 200
    assert client.conn.execute("SELECT COUNT(*) FROM leave_signatures").fetchone()[0] == 0


@pytest.mark.parametrize("xau", [
    {"page": 0, "x_mm": 120, "y_mm": 180, "w_mm": 400, "h_mm": 14},    # rộng quá khổ
    {"page": 0, "x_mm": 120, "y_mm": 180, "w_mm": 2, "h_mm": 14},      # bé đến vô nghĩa
    {"page": 0, "x_mm": 900, "y_mm": 180, "w_mm": 38, "h_mm": 14},     # ra ngoài trang
    {"page": 99, "x_mm": 120, "y_mm": 180, "w_mm": 38, "h_mm": 14},    # trang không có
])
def test_toa_do_vo_ly_bi_chan(client, xau):
    assert _tao_don(client, signature=xau).status_code == 400


def test_ksv_va_gd_ky_roi_tai_ve_pdf(client):
    assert _tao_don(client, signature=_BOX).status_code == 200
    lid = client.conn.execute("SELECT id FROM leave_records").fetchone()[0]

    client.who["id"] = TP
    r = client.put(f"/api/leaves/{lid}/ksv-review",
                   json={"action": "approve", "signature": dict(_BOX, x_mm=40.0)})
    assert r.status_code == 200, r.text

    client.conn.execute("UPDATE leave_records SET status='pending_gd' WHERE id=?", (lid,))
    client.conn.commit()
    client.who["id"] = GD
    r = client.put(f"/api/leaves/{lid}/gd-review",
                   json={"action": "approve", "signature": dict(_BOX, y_mm=220.0)})
    assert r.status_code == 200, r.text

    slots = {x[0] for x in client.conn.execute("SELECT slot FROM leave_signatures").fetchall()}
    assert slots == {"nguoi_de_nghi", "ksv", "gd"}

    r = client.get(f"/api/leaves/{lid}/download")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"

    # Ba chữ ký phải thật sự nằm trên trang in ra
    png, w_mm, _, _ = leave_pdf.page_png(r.content, 0, dpi=100)
    im = Image.open(io.BytesIO(png)).convert("RGB")
    ppm = im.width / w_mm
    for x, y in ((139, 187), (59, 187), (139, 227)):
        assert im.getpixel((int(x * ppm), int(y * ppm)))[2] > 120, f"thiếu chữ ký ở ({x},{y})"


def test_tu_choi_thi_khong_ky(client):
    assert _tao_don(client, signature=_BOX).status_code == 200
    lid = client.conn.execute("SELECT id FROM leave_records").fetchone()[0]
    client.who["id"] = TP
    r = client.put(f"/api/leaves/{lid}/ksv-review",
                   json={"action": "reject", "comment": "Không duyệt", "signature": _BOX})
    assert r.status_code == 200
    assert client.conn.execute(
        "SELECT COUNT(*) FROM leave_signatures WHERE slot='ksv'").fetchone()[0] == 0


def test_nop_lai_xoa_chu_ky_nguoi_duyet(client):
    assert _tao_don(client, signature=_BOX).status_code == 200
    lid = client.conn.execute("SELECT id FROM leave_records").fetchone()[0]
    for slot, sid in (("ksv", TP), ("gd", GD)):
        client.conn.execute(
            "INSERT INTO leave_signatures (leave_id,slot,staff_id,page,x_mm,y_mm,w_mm,h_mm,image,signed_at)"
            " VALUES (?,?,?,0,10,10,20,10,?,'2026-08-14')", (lid, slot, sid, SIG))
    client.conn.execute("UPDATE leave_records SET status='rejected' WHERE id=?", (lid,))
    client.conn.commit()

    r = client.put(f"/api/leaves/{lid}/resubmit", json={
        "start_date": "2026-12-08", "end_date": "2026-12-09", "leave_type": "annual",
        "reason": "Nộp lại", "ksv_approver_id": TP, "gd_approver_id": GD})
    assert r.status_code == 200, r.text
    slots = {x[0] for x in client.conn.execute("SELECT slot FROM leave_signatures").fetchall()}
    assert slots == {"nguoi_de_nghi"}      # chữ ký người duyệt cũ phải bị xoá


def test_o_ky_da_ky_thi_mo_lai_dung_cho_cu(client):
    assert _tao_don(client, signature=dict(_BOX, x_mm=77.0, y_mm=155.0)).status_code == 200
    lid = client.conn.execute("SELECT id FROM leave_records").fetchone()[0]
    body = client.get(f"/api/leaves/{lid}/preview", params={"slot": "nguoi_de_nghi"}).json()
    assert (body["suggest"]["x_mm"], body["suggest"]["y_mm"]) == (77.0, 155.0)


def test_nguoi_ngoai_cuoc_khong_xem_truoc_duoc(client):
    assert _tao_don(client, signature=_BOX).status_code == 200
    lid = client.conn.execute("SELECT id FROM leave_records").fetchone()[0]
    client.conn.execute(
        "INSERT INTO user_tttt (id,full_name,username,role,department_id,is_active)"
        " VALUES (9,'Người lạ','x','chuyen_vien',2,1)")
    client.conn.commit()
    client.who["id"] = 9
    assert client.get(f"/api/leaves/{lid}/preview").status_code == 403


def test_word_hong_thi_bao_loi_ro_rang(client, monkeypatch):
    def _no_word(_b):
        raise leave_pdf.PdfConvertError("Word chuyển đổi thất bại: thử")
    monkeypatch.setattr(leave_pdf, "docx_to_pdf", _no_word)
    leave_pdf.drop_cache()
    assert _tao_don(client).status_code == 200
    lid = client.conn.execute("SELECT id FROM leave_records").fetchone()[0]

    r = client.get(f"/api/leaves/{lid}/preview")
    assert r.status_code == 503 and "Word" in r.json()["detail"]

    # Đường lui: vẫn tải được bản Word không chữ ký
    r = client.get(f"/api/leaves/{lid}/download", params={"fmt": "docx"})
    assert r.status_code == 200 and r.content[:2] == b"PK"
