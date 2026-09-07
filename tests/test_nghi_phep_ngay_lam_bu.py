"""Nghỉ phép rơi vào ngày làm bù VẪN bị trừ vào quỹ phép.

Trước đây `calculate_leave_days` chỉ biết `d.weekday() < 5` + `public_holidays`,
nên nghỉ đúng thứ Bảy phải đi làm bù thì không bị trừ ngày nào — người đó vắng
một ngày làm việc thật mà quỹ phép không đổi. Chính sách đã chốt 02/09/2026:
ngày làm bù là ngày làm việc, nghỉ hôm đó phải trừ.

Ngày làm bù chỉ khai được ở màn Phân lịch trực → Ngày đặc biệt (`duty_special_days`).
"""
import sqlite3
from datetime import date

import pytest

from backend.api.leaves import (
    _calc_used_days, _calc_used_days_bulk, _is_business_contiguous,
    _load_lich, calculate_leave_days,
)
from backend.database import compute_carry_over

# 2026: 02/01 thứ Sáu, 03/01 thứ Bảy, 04/01 Chủ nhật, 05/01 thứ Hai
T6 = date(2026, 1, 2)
T7 = date(2026, 1, 3)
CN = date(2026, 1, 4)
T2 = date(2026, 1, 5)

SCHEMA = """
CREATE TABLE public_holidays (id INTEGER PRIMARY KEY AUTOINCREMENT, date DATE UNIQUE, name TEXT);
CREATE TABLE duty_special_days (
    id INTEGER PRIMARY KEY AUTOINCREMENT, date DATE UNIQUE, day_type TEXT,
    label TEXT, is_confirmed INTEGER DEFAULT 0, created_at DATETIME);
CREATE TABLE leave_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT, staff_id INT, start_date TEXT, end_date TEXT,
    leave_type TEXT DEFAULT 'annual', status TEXT, spread_dates TEXT, reason TEXT,
    borrow_next_year_days REAL DEFAULT 0, adjusts_leave_id INT, other_deduct_quota INT DEFAULT 1);
CREATE TABLE leave_quotas (staff_id INT, year INT, quota_days REAL);
CREATE TABLE user_tttt (id INTEGER PRIMARY KEY, join_industry_date TEXT);
"""


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.execute("INSERT INTO user_tttt (id, join_industry_date) VALUES (7, '2015-01-01')")
    conn.commit()
    yield conn
    conn.close()


def _lam_bu(db, ngay=T7, xac_nhan=1):
    db.execute(
        "INSERT INTO duty_special_days (date, day_type, is_confirmed) VALUES (?,'makeup',?)",
        (ngay.isoformat(), xac_nhan),
    )
    db.commit()


def _don_nghi(db, start, end, year=None, status="approved"):
    db.execute(
        "INSERT INTO leave_records (staff_id, start_date, end_date, leave_type, status) "
        "VALUES (7, ?, ?, 'annual', ?)",
        (start.isoformat(), end.isoformat(), status),
    )
    db.commit()


def _lich(db, lo=T6, hi=T2):
    return _load_lich(db, lo, hi)


# ── calculate_leave_days ─────────────────────────────────────────────────────

def test_nghi_t6_den_t2_khong_co_ngay_bu(db):
    """T7/CN không tính → chỉ 2 ngày phép (thứ Sáu + thứ Hai)."""
    assert calculate_leave_days(T6, T2, _lich(db)) == 2


def test_ngay_lam_bu_bi_tru_them_mot_ngay(db):
    _lam_bu(db)
    assert calculate_leave_days(T6, T2, _lich(db)) == 3


def test_nghi_dung_mot_ngay_lam_bu_van_tru(db):
    """Nghỉ trọn thứ Bảy làm bù — trước đây rơi vào sàn `max(count, 1)` nên nhìn
    vẫn ra 1, nhưng là 1 giả. Nay là 1 thật, và Chủ nhật kề bên không cộng thêm."""
    _lam_bu(db)
    assert calculate_leave_days(T7, CN, _lich(db)) == 1


def test_ngay_bu_chua_xac_nhan_thi_khong_tru(db):
    _lam_bu(db, xac_nhan=0)
    assert calculate_leave_days(T6, T2, _lich(db)) == 2


def test_ngay_le_van_khong_tru(db):
    db.execute("INSERT INTO public_holidays (date, name) VALUES (?,?)", (T2.isoformat(), "Lễ"))
    db.commit()
    assert calculate_leave_days(T6, T2, _lich(db)) == 1


# ── Quỹ phép đã dùng ─────────────────────────────────────────────────────────

def test_calc_used_days_dem_ca_ngay_bu(db):
    _don_nghi(db, T6, T2)
    assert _calc_used_days(7, 2026, db) == 2
    _lam_bu(db)
    assert _calc_used_days(7, 2026, db) == 3


def test_calc_used_days_bulk_khop_ban_don_le(db):
    """Bản gộp truy vấn phải ra đúng cùng con số với bản đơn lẻ."""
    _don_nghi(db, T6, T2)
    _lam_bu(db)
    assert _calc_used_days_bulk([7], 2026, db)[7] == _calc_used_days(7, 2026, db) == 3


def test_carry_over_tru_ngay_bu_cua_nam_truoc(db):
    """27/12/2025 là thứ Bảy. Khai làm bù → năm 2025 dùng thêm 1 ngày, mang sang ít đi 1."""
    db.execute("INSERT INTO leave_quotas (staff_id, year, quota_days) VALUES (7, 2025, 12)")
    db.execute(
        "INSERT INTO leave_records (staff_id, start_date, end_date, leave_type, status) "
        "VALUES (7, '2025-12-26', '2025-12-29', 'annual', 'approved')"
    )
    db.commit()
    assert compute_carry_over(7, 2026, db, effective=False) == 10.0   # 26/12 T6 + 29/12 T2
    _lam_bu(db, date(2025, 12, 27))
    assert compute_carry_over(7, 2026, db, effective=False) == 9.0


# ── Câu chữ trên đơn in ──────────────────────────────────────────────────────

def test_khong_gop_khoang_khi_giua_co_ngay_lam_bu(db):
    """Nghỉ T6 và T2, ở giữa là T7 làm bù (có đi làm) → không được ghi gọn
    "từ ngày ... đến hết ngày ...", vì như thế là khai nghỉ cả thứ Bảy."""
    assert _is_business_contiguous([T6, T2], _lich(db)) is True
    _lam_bu(db)
    assert _is_business_contiguous([T6, T2], _lich(db)) is False
