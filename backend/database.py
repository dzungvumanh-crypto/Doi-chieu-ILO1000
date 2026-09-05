"""SQLite connection factory — raw SQL, no ORM."""
import sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta
from backend.core.config import settings

DB_PATH = settings.DATABASE_URL.replace("sqlite:///", "")
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

_VN_TZ = timezone(timedelta(hours=7))


def _vn_now() -> datetime:
    return datetime.now(_VN_TZ).replace(tzinfo=None)


def write_audit(
    db: sqlite3.Connection,
    actor_id: int,
    action: str,
    target_type: str = None,
    target_id: int = None,
    detail: str = None,
    ip: str = None,
) -> None:
    # Không truyền ip → lấy IP thật đã lưu lúc đăng nhập (khớp Nhật ký đăng nhập)
    if ip is None and actor_id:
        try:
            from backend.core.sessions import get_session_ip
            ip = get_session_ip(db, actor_id)
        except Exception:
            pass
    db.execute(
        "INSERT INTO audit_logs (actor_id, action, target_type, target_id, detail, ip_address, created_at) VALUES (?,?,?,?,?,?,?)",
        (actor_id, action, target_type, target_id, detail, ip, _vn_now()),
    )


def compute_annual_leave(join_date_str, year: int = None) -> int:
    """Tính số ngày phép năm: 12 ngày + 1 ngày mỗi 5 năm vào ngành (đúng Điều 113
    Bộ luật Lao động — đối chiếu báo cáo thật 2026 khớp 67/72 người theo mốc 5
    năm, so với chỉ 12/72 nếu tính theo 4 năm).

    Ví dụ: vào ngành 2007, năm 2012 → 13 ngày; năm 2017 → 14 ngày.
    Trả về 12 nếu join_date_str là None hoặc không hợp lệ.
    """
    if not join_date_str:
        return 12
    from datetime import date
    try:
        join_date = join_date_str if isinstance(join_date_str, date) else date.fromisoformat(str(join_date_str))
        ref_year = year or _vn_now().date().year
        years = ref_year - join_date.year
        return 12 + max(0, years // 5)
    except Exception:
        return 12


def compute_carry_over(staff_id: int, year: int, db,
                       effective: bool = True, ref_date=None) -> float:
    """Số ngày phép năm (year-1) chưa dùng được mang sang Q1/year.

    effective=True : chỉ trả giá trị nếu ref_date (hoặc hôm nay) còn trong Q1.
    effective=False: luôn trả số ngày thực tế, dùng để hiển thị / in phiếu.
    ref_date       : ngày tham chiếu thay cho _vn_now().date() khi check Q1
                     (dùng khi tạo đơn nghỉ trong tương lai).
    """
    from datetime import date as _date, timedelta
    import json
    if effective:
        check_date = ref_date if ref_date else _vn_now().date()
        if check_date > _date(year, 3, 31):
            return 0.0
    prev_year = year - 1
    q = db.execute(
        "SELECT quota_days FROM leave_quotas WHERE staff_id=? AND year=?", (staff_id, prev_year)
    ).fetchone()
    staff = db.execute("SELECT join_industry_date FROM user_tttt WHERE id=?", (staff_id,)).fetchone()
    prev_quota = float(q["quota_days"]) if q else float(
        compute_annual_leave(staff["join_industry_date"] if staff else None, prev_year)
    )
    rows = db.execute(
        """SELECT start_date, end_date, spread_dates, borrow_next_year_days FROM leave_records
           WHERE staff_id=? AND status='approved'
             AND leave_type NOT IN ('thai_san','bao_hiem','khong_luong','hop_cong_tac')
             AND start_date <= ? AND end_date >= ?""",
        (staff_id, f"{prev_year}-12-31", f"{prev_year}-01-01"),
    ).fetchall()
    # Import muộn: lich_lam_viec không kéo theo gì từ database.py, nhưng đặt ở
    # đầu file thì mọi module import database.py đều phải nạp theo — giữ nguyên
    # kiểu import cục bộ mà hàm này đang dùng cho date/json.
    from backend.services.lich_lam_viec import la_ngay_lam_viec, tai_lich
    used = 0.0
    _lich = None
    for row in rows:
        # Phần đã "ứng" sang năm sau (borrow_next_year_days, xem
        # backend/api/leaves.py::_check_quota_or_borrow) không tính là đã dùng
        # của prev_year — nếu không carry-over sẽ bị tính hụt. CHỈ trừ borrow ở
        # đúng năm GỐC của đơn (năm chứa start_date) — đơn vắt ranh giới năm
        # (vd 29/12→02/01) có thể khớp overlap ở đây dù start_date KHÔNG phải
        # prev_year (vd đơn bắt đầu từ prev_year-1); trừ nhầm borrow của đơn đó
        # vào prev_year sẽ làm hụt used y hệt bug đã sửa ở _calc_used_days.
        borrow = row["borrow_next_year_days"] or 0.0
        row_start_year = _date.fromisoformat(row["start_date"]).year
        own_borrow = borrow if row_start_year == prev_year else 0.0
        if row["spread_dates"]:
            used += len([d for d in json.loads(row["spread_dates"]) if d.startswith(str(prev_year))]) - own_borrow
        else:
            if _lich is None:
                _lich = tai_lich(db, _date(prev_year, 1, 1), _date(prev_year, 12, 31))
            d = _date.fromisoformat(row["start_date"])
            end = _date.fromisoformat(row["end_date"])
            yr_count = 0
            while d <= end:
                if d.year == prev_year and la_ngay_lam_viec(d, _lich):
                    yr_count += 1
                d += timedelta(days=1)
            used += yr_count - own_borrow
    return max(0.0, prev_quota - used)


def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA synchronous=NORMAL")
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
