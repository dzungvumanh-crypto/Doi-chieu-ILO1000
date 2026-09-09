"""Tính chứng từ nộp đúng hạn / quá hạn theo phòng.

Ngày nộp thực tế lấy từ `entry_change_logs` — timestamp sớm nhất của action
'handover' (chuyên viên nộp) hoặc 'edited_hkv' (HKV nhập trực tiếp), nhưng
**chỉ xét các lần nộp sau lần bị từ chối gần nhất**: lần nộp đã bị HKV trả về
(`rejected_handover`) không được tính là đã nộp.

Không dùng `handovers.handover_date`: khi nhập qua lưới, cột này được gán bằng
đúng `transaction_date`, nên khoảng cách giữa hai ngày luôn bằng 0 và mọi
chứng từ đều bị coi là đúng hạn.

Ngày làm việc để tính hạn nộp lấy từ `lich_lam_viec.tai_lich()` — bỏ T7/CN và
ngày lễ, nhưng T7/CN đã khai là **ngày làm bù** thì vẫn tính là ngày làm việc.
Ngày bù chỉ có ở màn **Phân lịch trực → Ngày đặc biệt**, không có nguồn nào khác.

Hai nhóm bị loại khỏi báo cáo:
- Không có log nộp nào (dữ liệu import cũ) → đếm riêng ở `no_submit_date`.
- Bị từ chối và chưa nộp lại → không còn lần nộp hợp lệ nào, không tính.
"""
import logging
import sqlite3
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import FrozenSet, Optional

from backend.services.lich_lam_viec import (
    LichLamViec, dem_ngay_lam_viec, la_ngay_lam_viec, tai_lich,
)

log = logging.getLogger(__name__)

# Hạn nộp: trong vòng 1 ngày làm việc kể từ ngày giao dịch
DEADLINE_WORKING_DAYS = 1

# Action đánh dấu chứng từ được nộp
SUBMIT_ACTIONS = ("handover", "edited_hkv")

# Action huỷ hiệu lực lần nộp trước đó (chỉ từ chối chứng từ mới;
# rejected_borrow / rejected_return thuộc luồng mượn - trả, không liên quan)
REJECT_ACTION = "rejected_handover"

# Nới ngày tra cứu lễ/phép ra trước kỳ báo cáo để phủ hết khoảng tx → nộp
_LOOKUP_PAD_DAYS = 35


def submitted_at_sql(alias: str = "de") -> str:
    """Subquery trả ngày nộp còn hiệu lực của một dòng document_entries.

    Dùng chung cho báo cáo, dashboard và lịch sử chứng từ — ba màn hình phải
    nói cùng một con số. Tham số đi kèm: SUBMITTED_AT_PARAMS.
    """
    placeholders = ",".join("?" * len(SUBMIT_ACTIONS))
    return f"""(SELECT MIN(sub.timestamp) FROM entry_change_logs sub
                 WHERE sub.entry_id = {alias}.id
                   AND sub.action IN ({placeholders})
                   AND sub.timestamp > COALESCE(
                         (SELECT MAX(rej.timestamp) FROM entry_change_logs rej
                           WHERE rej.entry_id = {alias}.id
                             AND rej.action = ?), ''))"""


SUBMITTED_AT_PARAMS = (*SUBMIT_ACTIONS, REJECT_ACTION)


def submitted_at_from_logs(logs) -> Optional[str]:
    """Bản Python của submitted_at_sql, dùng khi đã có sẵn danh sách log của chứng từ."""
    last_reject = max(
        (str(l["timestamp"]) for l in logs
         if (l["action"] or "") == REJECT_ACTION and l["timestamp"]),
        default="",
    )
    return min(
        (str(l["timestamp"]) for l in logs
         if (l["action"] or "") in SUBMIT_ACTIONS and l["timestamp"]
         and str(l["timestamp"]) > last_reject),
        default=None,
    )


def working_days_between(
    start_exclusive: date,
    end_inclusive: date,
    lich: LichLamViec,
    leave_dates: FrozenSet[date] = frozenset(),
) -> int:
    """Đếm ngày làm việc trong (start, end]. Bỏ T7/CN, ngày lễ, ngày nghỉ phép.

    T7/CN đã khai là ngày làm bù thì VẪN tính — hạn nộp ngắn lại đúng bằng số
    ngày phải đi làm thật. Xem `backend/services/lich_lam_viec.py`.
    """
    return dem_ngay_lam_viec(start_exclusive, end_inclusive, lich, leave_dates)


def _parse_submit_date(raw) -> Optional[date]:
    if not raw:
        return None
    s = str(raw)
    try:
        return datetime.fromisoformat(s).date()
    except ValueError:
        pass
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        log.warning("Không đọc được timestamp nộp chứng từ: %r", raw)
        return None


def _load_staff_leave(db: sqlite3.Connection, lo: date, hi: date, lich: LichLamViec) -> dict:
    """Ngày nghỉ phép đã duyệt của từng nhân viên (chỉ ngày làm việc).

    Ngày làm bù rơi vào T7/CN cũng là ngày làm việc, nên nghỉ phép trúng hôm đó
    vẫn được tính là vắng mặt — nếu không, ngày ấy vừa đòi người ta nộp chứng từ
    vừa không thừa nhận là họ đang nghỉ.

    Loại bản ghi nghỉ "tổng hợp" (từ Nhập file hạn mức / sửa tay "Đã dùng" ở
    module Nghỉ phép, xem update_used_days/import_quota_apply trong
    backend/api/leaves.py) — đây chỉ là cách hệ thống lưu số ngày phép đã
    dùng, không phải người thật sự vắng mặt những ngày đó. Bản ghi này luôn
    trải dài start_date→end_date liên tục từ 02/01 (không có spread_dates),
    nên nếu tính cả sẽ biến cả 1 khoảng ngày làm việc đầu năm của người đó
    thành "đang nghỉ phép" — chứng từ nộp trễ trong khoảng đó bị tính nhầm
    thành đúng hạn.
    """
    rows = db.execute(
        """SELECT staff_id, start_date, end_date FROM leave_records
           WHERE status = 'approved' AND end_date >= ? AND start_date <= ?
             AND (reason IS NULL OR NOT (reason LIKE '[Import]%' OR reason LIKE '[Điều chỉnh]%'))""",
        (lo.isoformat(), hi.isoformat()),
    ).fetchall()

    acc: dict = defaultdict(set)
    for r in rows:
        d = max(date.fromisoformat(r["start_date"]), lo)
        end = min(date.fromisoformat(r["end_date"]), hi)
        while d <= end:
            if la_ngay_lam_viec(d, lich):
                acc[r["staff_id"]].add(d)
            d += timedelta(days=1)
    return {sid: frozenset(days) for sid, days in acc.items()}


def _fetch_entries(db: sqlite3.Connection, period_start: date, period_end: date) -> list:
    """Chứng từ có ngày giao dịch trong kỳ, kèm ngày nộp còn hiệu lực (có thể NULL).

    Dòng có submitted_at NULL — chưa nộp lần nào, hoặc bị từ chối và chưa nộp lại —
    bị compute_period bỏ qua.
    """
    return db.execute(
        f"""SELECT de.id, de.transaction_date, de.sheet_count, de.staff_id,
                   h.received_by_id,
                   d.id AS dept_id, d.name AS dept_name, d.code AS dept_code,
                   {submitted_at_sql()} AS submitted_at,
                   u.full_name, u.ipcas_code, u.username, u.payment_username
            FROM document_entries de
            JOIN handovers h ON de.handover_id = h.id
            JOIN departments d ON h.department_id = d.id
            LEFT JOIN user_tttt u ON de.staff_id = u.id
            WHERE de.transaction_date >= ? AND de.transaction_date < ?
            ORDER BY d.name, de.transaction_date""",
        (*SUBMITTED_AT_PARAMS, period_start.isoformat(), period_end.isoformat()),
    ).fetchall()


def _count_without_submit_log(db: sqlite3.Connection, period_start: date, period_end: date) -> int:
    return db.execute(
        f"""SELECT COUNT(*) FROM document_entries de
            WHERE de.transaction_date >= ? AND de.transaction_date < ?
              AND NOT EXISTS (
                  SELECT 1 FROM entry_change_logs ecl
                  WHERE ecl.entry_id = de.id
                    AND ecl.action IN ({','.join('?' * len(SUBMIT_ACTIONS))})
              )""",
        (period_start.isoformat(), period_end.isoformat(), *SUBMIT_ACTIONS),
    ).fetchone()[0] or 0


def _staff_display_name(row) -> str:
    return row["full_name"] or row["payment_username"] or row["username"] or f"ID {row['staff_id']}"


def compute_period(db: sqlite3.Connection, year: int, month: int) -> dict:
    """Thống kê nộp đúng hạn / quá hạn của kỳ (theo ngày giao dịch)."""
    period_start = date(year, month, 1)
    period_end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

    rows = _fetch_entries(db, period_start, period_end)

    # ── Khoảng tra cứu lễ/phép: phủ từ trước kỳ đến ngày nộp muộn nhất ──
    submit_dates = [d for d in (_parse_submit_date(r["submitted_at"]) for r in rows) if d]
    lookup_lo = period_start - timedelta(days=_LOOKUP_PAD_DAYS)
    lookup_hi = max([period_end, *submit_dates]) if submit_dates else period_end

    lich = tai_lich(db, lookup_lo, lookup_hi)
    staff_leave = _load_staff_leave(db, lookup_lo, lookup_hi, lich)

    by_dept: dict = {}
    late_entries: list = []
    overall_total = 0
    overall_on_time = 0

    for r in rows:
        submitted = _parse_submit_date(r["submitted_at"])
        if not submitted:
            continue

        tx_date = date.fromisoformat(r["transaction_date"])
        recv_id = r["received_by_id"]
        receiver_leave = staff_leave.get(recv_id, frozenset()) if recv_id else frozenset()

        elapsed = working_days_between(tx_date, submitted, lich, receiver_leave)
        days_late = max(0, elapsed - DEADLINE_WORKING_DAYS)
        on_time = days_late == 0

        dept_name = r["dept_name"]
        bucket = by_dept.setdefault(
            dept_name, {"dept_id": r["dept_id"], "dept_code": r["dept_code"], "total": 0, "on_time": 0}
        )
        bucket["total"] += 1
        overall_total += 1
        if on_time:
            bucket["on_time"] += 1
            overall_on_time += 1
        else:
            late_entries.append({
                "entry_id":         r["id"],
                "dept_id":          r["dept_id"],
                "dept_name":        dept_name,
                "staff_id":         r["staff_id"],
                "staff_name":       _staff_display_name(r),
                "ipcas_code":       r["ipcas_code"] or "",
                "transaction_date": r["transaction_date"],
                "submitted_date":   submitted.isoformat(),
                "days_late":        days_late,
                "sheet_count":      r["sheet_count"],
            })

    late_entries.sort(key=lambda e: (e["dept_name"], -e["days_late"], e["transaction_date"]))

    by_dept_list = []
    for dept_name, data in sorted(by_dept.items()):
        t, ot = data["total"], data["on_time"]
        by_dept_list.append({
            "dept_id":   data["dept_id"],
            "dept_code": data["dept_code"],
            "dept_name": dept_name,
            "total":     t,
            "on_time":   ot,
            "late":      t - ot,
            "rate":      round(ot / t * 100, 1) if t else None,
        })

    return {
        "period": f"{year:04d}-{month:02d}",
        "overall": {
            "total":   overall_total,
            "on_time": overall_on_time,
            "late":    overall_total - overall_on_time,
            "rate":    round(overall_on_time / overall_total * 100, 1) if overall_total else None,
        },
        "by_dept":        by_dept_list,
        "late_entries":   late_entries,
        "no_submit_date": _count_without_submit_log(db, period_start, period_end),
    }
