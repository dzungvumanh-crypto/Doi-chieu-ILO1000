"""Quản lý nghỉ phép — đăng ký, phê duyệt, tải phiếu"""
import base64
import io
import json
import os
import re
import sqlite3
import threading
import unicodedata
from datetime import date, timedelta
from typing import FrozenSet, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse

from backend.core.concurrency import run_heavy
from backend.core.uploads import read_limited_sync
from backend.core.deps import TONG_HOP_CODES, get_current_staff, require_feature
from backend.core.enums import LeaveStatus
from backend.core.paths import template_path
from backend.services.lich_lam_viec import (
    LICH_RONG, LichLamViec, la_ngay_lam_viec, tai_lich,
)
from backend.database import get_db, write_audit, _vn_now, compute_annual_leave, compute_carry_over
from backend.schemas.leaves import (
    LeaveCreate, LeaveReview, TongHopReview,
    DirectLeaveCreate, RecallCreate, LeaveQuotaUpsert,
)
from backend.services import leave_pdf

router = APIRouter()

LEAVE_TYPE_LABELS = {
    "bat_buoc":    "Nghỉ phép bắt buộc",
    "annual":      "Nghỉ phép năm",
    "thai_san":    "Nghỉ thai sản",
    "bao_hiem":    "Nghỉ bảo hiểm",
    "khong_luong": "Nghỉ không lương",
    "hop_cong_tac": "Họp/Công tác",
    "other":       "Khác",
    # Legacy types (giữ để tương thích với data cũ)
    "sick":      "Nghỉ ốm",
    "personal":  "Nghỉ việc riêng",
    "dot_xuat":  "Nghỉ đột xuất",
}

_VALID_LEAVE_TYPES = frozenset(LEAVE_TYPE_LABELS.keys())
# Các loại nghỉ không tính vào/trừ hạn mức phép năm — nghỉ không lương cũng
# không dùng tới hạn mức phép năm (nghỉ hẳn không lương, không phải trừ phép).
_NO_QUOTA_TYPES = frozenset({"thai_san", "bao_hiem", "khong_luong", "hop_cong_tac"})

# leave_type="other" (Khác) không cố định miễn/trừ quota như các loại trên —
# người tạo đơn tự chọn qua cột other_deduct_quota (mặc định 1 = có trừ,
# giống "annual", khớp hành vi cũ trước khi có lựa chọn này). Chọn "Không" thì
# ghi nhận y hệt các loại trong _NO_QUOTA_TYPES — không tính toán gì thêm.
# Dùng ở nơi đã có sẵn 2 giá trị Python (leave_type, other_deduct_quota); các
# câu SQL tự thêm điều kiện tương đương "AND NOT (leave_type='other' AND
# other_deduct_quota=0)" cạnh mọi chỗ có "leave_type NOT IN (...)" ở trên.
def _is_no_quota_row(leave_type: str, other_deduct_quota) -> bool:
    if leave_type in _NO_QUOTA_TYPES:
        return True
    if leave_type == "other":
        return not bool(other_deduct_quota if other_deduct_quota is not None else True)
    return False


_OTHER_NO_QUOTA_SQL = "AND NOT (leave_type='other' AND other_deduct_quota=0)"

ACTION_LABELS = {
    "create":         ("Nộp đơn",            "blue"),
    "ksv_approve":    ("KSV phê duyệt",      "green"),
    "ksv_reject":     ("KSV từ chối",        "red"),
    "th_forward":     ("TH chuyển GĐ",       "blue"),
    "th_reject":      ("TH từ chối",         "red"),
    "gd_approve":     ("GĐ phê duyệt",       "green"),
    "gd_reject":      ("GĐ từ chối",         "red"),
    "resubmit":       ("Nộp lại",            "orange"),
    "npbb_adjust":    ("Điều chỉnh ngày NPBB", "orange"),
    "npbb_adjusted_cancel": ("Đơn gốc bị thay bởi đơn điều chỉnh", "grey"),
    "npbb_adjustment_recalled": ("Đơn gốc được khôi phục do đơn điều chỉnh bị rút/hủy", "grey"),
    "cancel":         ("Hủy đơn",            "grey"),
    "direct_create":  ("Khai báo hộ",        "purple"),
    "recall_request": ("Yêu cầu rút đơn",    "orange"),
    "recall_approve": ("Xác nhận rút đơn",   "grey"),
    "th_ack_gd":      ("TH xác nhận đã biết", "green"),
}

_LEAVE_STATUS_VN = {
    LeaveStatus.PENDING_KSV:      "Chờ KSV duyệt",
    LeaveStatus.PENDING_TONG_HOP: "Chờ Tổng hợp",
    LeaveStatus.PENDING_GD:       "Chờ Ban lãnh đạo duyệt",
    LeaveStatus.APPROVED:         "Hoàn thành",
    LeaveStatus.REJECTED:         "Bị từ chối",
    LeaveStatus.CANCELLED:        "Đã hủy",
}

# Các role cấp cao — bỏ qua bước KSV, vào thẳng pending_tong_hop
_HIGH_ROLES = frozenset(("giam_doc", "pho_giam_doc", "admin", "truong_phong"))


# ─── Helpers ────────────────────────────────────────────────────────────────

_NO_ACTIVE_ADJ_SQL = (
    "AND NOT EXISTS (SELECT 1 FROM leave_records adj "
    "WHERE adj.adjusts_leave_id = leave_records.id "
    "AND adj.status NOT IN ('rejected','cancelled'))"
)


def _calc_used_days(staff_id: int, year: int, db: sqlite3.Connection,
                    exclude_id: int | None = None,
                    include_pending: bool = False) -> float:
    """Số ngày đã dùng trong năm — nguồn sự thật duy nhất.

    Đếm tất cả loại TRỪ thai_san/bao_hiem.
    include_pending=True: cộng thêm đơn đang chờ duyệt (dùng khi kiểm tra quota lúc nộp lại).
    exclude_id: bỏ qua đơn đang xem (dùng khi in phiếu).

    Có tính "ứng phép năm sau" (borrow_next_year_days, xem
    _check_quota_or_borrow): phần đã ứng bị trừ khỏi năm gốc của đơn, cộng
    sang năm sau — nên đơn tạo năm N-1 có ứng vẫn cộng đúng vào năm N dù ngày
    nghỉ thực tế không nằm trong năm N.

    Đơn NPBB gốc (bat_buoc) đang có đơn điều chỉnh CÒN HIỆU LỰC (chưa bị từ
    chối/hủy, kể cả khi đơn điều chỉnh còn đang chờ duyệt) bị loại khỏi tổng —
    nếu không, cả đơn gốc (vẫn 'approved' cho tới khi đơn điều chỉnh duyệt xong
    hẳn, xem _cancel_adjusted_original) LẪN đơn điều chỉnh (include_pending=True
    cộng luôn cả pending) cùng cộng vào, ra hạn mức "đã dùng" gấp đôi ảo trong
    lúc đơn điều chỉnh còn đang xử lý.
    """
    if include_pending:
        statuses = ("'approved','pending_ksv','pending_tong_hop','pending_gd'")
    else:
        statuses = "'approved'"
    excl = "AND id != ?" if exclude_id is not None else ""
    params: list = [staff_id]
    if exclude_id is not None:
        params.append(exclude_id)
    # Lấy theo overlap với năm (không chỉ start_date cùng năm) — đơn vắt qua
    # ranh giới năm (vd 29/12 → 02/01) vẫn phải được xét để đếm đúng phần ngày
    # rơi vào năm đang tính, xem thêm vòng lặp clip theo d.year bên dưới.
    params += [f"{year}-12-31", f"{year}-01-01"]
    rows = db.execute(
        f"""SELECT spread_dates, start_date, end_date, borrow_next_year_days FROM leave_records
            WHERE staff_id=? {excl} AND status IN ({statuses})
              AND leave_type NOT IN ('thai_san','bao_hiem','khong_luong','hop_cong_tac')
              {_OTHER_NO_QUOTA_SQL}
              AND start_date <= ? AND end_date >= ?
              {_NO_ACTIVE_ADJ_SQL}""",
        params,
    ).fetchall()
    total = 0.0
    _lich: LichLamViec | None = None  # lazy load khi cần
    for row in rows:
        borrow = row["borrow_next_year_days"] or 0.0
        # borrow_next_year_days là số ngày VƯỢT hạn mức năm GỐC (năm chứa
        # start_date, xem _check_quota_or_borrow) bị chuyển sang tính vào năm
        # sau — không phải "số ngày rơi vào năm sau" theo lịch. Đơn vắt qua
        # ranh giới năm (vd 29/12→02/01) đồng thời khớp CẢ 2 câu SELECT ở đây
        # (năm gốc lẫn năm sau, vì cùng chồng lấn khoảng ngày) — nếu trừ borrow
        # ở MỌI năm đơn này chồng lấn tới (thay vì chỉ năm gốc) thì phần ngày
        # đã "ứng" bị trừ 2 lần, tổng dùng cả 2 năm cộng lại hụt mất đúng bằng
        # borrow (bug thật, xem audit — 5 ngày thực tế chỉ còn ra tổng 3).
        row_start_year = date.fromisoformat(row["start_date"]).year
        own_borrow = borrow if row_start_year == year else 0.0
        if row["spread_dates"]:
            yr_count = len([d for d in json.loads(row["spread_dates"]) if d.startswith(str(year))])
        else:
            if _lich is None:
                _lich = _load_lich(db, date(year, 1, 1), date(year, 12, 31))
            d = date.fromisoformat(row["start_date"])
            e = date.fromisoformat(row["end_date"])
            yr_count = 0
            while d <= e:
                if d.year == year and la_ngay_lam_viec(d, _lich):
                    yr_count += 1
                d += timedelta(days=1)
        total += yr_count - own_borrow
    # Phần ứng TỪ năm trước SANG năm đang tính — đơn gốc nằm hẳn ở year-1
    # nhưng phần vượt hạn mức đã được tính vào year, cộng riêng ở đây vì câu
    # SELECT trên chỉ lấy đơn có ngày nghỉ chồng lên year.
    borrowed_params: list = [staff_id]
    if exclude_id is not None:
        borrowed_params.append(exclude_id)
    borrowed_params.append(str(year - 1))
    for row in db.execute(
        f"""SELECT borrow_next_year_days FROM leave_records
            WHERE staff_id=? {excl} AND status IN ({statuses})
              AND strftime('%Y', start_date) = ?
              {_NO_ACTIVE_ADJ_SQL}""",
        borrowed_params,
    ).fetchall():
        total += row["borrow_next_year_days"] or 0.0
    return total


def _calc_used_days_bulk(staff_ids: list, year: int, db: sqlite3.Connection,
                         include_pending: bool = False) -> dict:
    """Bản gộp truy vấn của _calc_used_days cho NHIỀU nhân viên cùng lúc (1 query
    thay vì N) — dùng cho các màn hình liệt kê toàn bộ nhân viên (get_quotas,
    export_quotas, stats_annual) để tránh N+1. Phải giữ đúng logic tính giống hệt
    _calc_used_days (đơn lẻ)."""
    if not staff_ids:
        return {}
    statuses = ("'approved','pending_ksv','pending_tong_hop','pending_gd'"
                if include_pending else "'approved'")
    placeholders = ",".join("?" * len(staff_ids))
    rows = db.execute(
        f"""SELECT staff_id, spread_dates, start_date, end_date, borrow_next_year_days FROM leave_records
            WHERE staff_id IN ({placeholders}) AND status IN ({statuses})
              AND leave_type NOT IN ('thai_san','bao_hiem','khong_luong','hop_cong_tac')
              {_OTHER_NO_QUOTA_SQL}
              AND start_date <= ? AND end_date >= ?
              {_NO_ACTIVE_ADJ_SQL}""",
        list(staff_ids) + [f"{year}-12-31", f"{year}-01-01"],
    ).fetchall()
    result = {sid: 0.0 for sid in staff_ids}
    _lich: LichLamViec | None = None
    for row in rows:
        borrow = row["borrow_next_year_days"] or 0.0
        # Chỉ trừ borrow ở đúng năm GỐC (năm chứa start_date) — xem chú thích
        # đầy đủ trong _calc_used_days, cùng 1 bug/1 cách sửa.
        row_start_year = date.fromisoformat(row["start_date"]).year
        own_borrow = borrow if row_start_year == year else 0.0
        if row["spread_dates"]:
            yr_count = len([d for d in json.loads(row["spread_dates"]) if d.startswith(str(year))])
        else:
            if _lich is None:
                _lich = _load_lich(db, date(year, 1, 1), date(year, 12, 31))
            d = date.fromisoformat(row["start_date"])
            e = date.fromisoformat(row["end_date"])
            yr_count = 0
            while d <= e:
                if d.year == year and la_ngay_lam_viec(d, _lich):
                    yr_count += 1
                d += timedelta(days=1)
        result[row["staff_id"]] += yr_count - own_borrow
    # Phần ứng TỪ năm trước SANG năm đang tính — xem chú thích trong _calc_used_days.
    for row in db.execute(
        f"""SELECT staff_id, borrow_next_year_days FROM leave_records
            WHERE staff_id IN ({placeholders}) AND status IN ({statuses})
              AND strftime('%Y', start_date) = ?
              {_NO_ACTIVE_ADJ_SQL}""",
        list(staff_ids) + [str(year - 1)],
    ).fetchall():
        result[row["staff_id"]] += row["borrow_next_year_days"] or 0.0
    return result


def _carry_over_bulk(staff_ids: list, year: int, db: sqlite3.Connection,
                     effective: bool = True, ref_date=None) -> dict:
    """Bản gộp truy vấn của compute_carry_over (backend/database.py) cho NHIỀU
    nhân viên cùng lúc — tránh N+1. Phải giữ đúng logic tính giống hệt bản đơn lẻ."""
    if not staff_ids:
        return {}
    if effective:
        check_date = ref_date if ref_date else date.today()
        if check_date > date(year, 3, 31):
            return {sid: 0.0 for sid in staff_ids}
    prev_year = year - 1
    placeholders = ",".join("?" * len(staff_ids))
    quota_by_staff = {
        r["staff_id"]: float(r["quota_days"])
        for r in db.execute(
            f"SELECT staff_id, quota_days FROM leave_quotas WHERE year=? AND staff_id IN ({placeholders})",
            [prev_year] + list(staff_ids),
        ).fetchall()
    }
    join_by_staff = {
        r["id"]: r["join_industry_date"]
        for r in db.execute(
            f"SELECT id, join_industry_date FROM user_tttt WHERE id IN ({placeholders})",
            list(staff_ids),
        ).fetchall()
    }
    used_by_staff: dict = {}
    _lich: LichLamViec | None = None
    for r in db.execute(
        f"""SELECT staff_id, start_date, end_date, spread_dates, borrow_next_year_days FROM leave_records
           WHERE staff_id IN ({placeholders}) AND status='approved'
             AND leave_type NOT IN ('thai_san','bao_hiem','khong_luong','hop_cong_tac')
             {_OTHER_NO_QUOTA_SQL}
             AND start_date <= ? AND end_date >= ?""",
        list(staff_ids) + [f"{prev_year}-12-31", f"{prev_year}-01-01"],
    ).fetchall():
        sid = r["staff_id"]
        # Phần đã "ứng" sang year (= prev_year + 1) không tính là đã dùng của
        # prev_year — nếu không carry-over sẽ bị tính hụt (coi như dùng hết cả
        # phần đã chuyển sang năm sau), xem _check_quota_or_borrow. Chỉ trừ ở
        # đúng năm gốc của đơn — xem chú thích đầy đủ trong compute_carry_over
        # (backend/database.py) và _calc_used_days, cùng 1 bug/1 cách sửa.
        borrow = r["borrow_next_year_days"] or 0.0
        row_start_year = date.fromisoformat(r["start_date"]).year
        own_borrow = borrow if row_start_year == prev_year else 0.0
        if r["spread_dates"]:
            used_by_staff[sid] = used_by_staff.get(sid, 0.0) + len(
                [d for d in json.loads(r["spread_dates"]) if d.startswith(str(prev_year))]
            ) - own_borrow
        else:
            if _lich is None:
                _lich = _load_lich(db, date(prev_year, 1, 1), date(prev_year, 12, 31))
            d = date.fromisoformat(r["start_date"])
            e = date.fromisoformat(r["end_date"])
            yr_count = 0
            while d <= e:
                if d.year == prev_year and la_ngay_lam_viec(d, _lich):
                    yr_count += 1
                d += timedelta(days=1)
            used_by_staff[sid] = used_by_staff.get(sid, 0.0) + yr_count - own_borrow
    result = {}
    for sid in staff_ids:
        prev_quota = quota_by_staff.get(sid)
        if prev_quota is None:
            prev_quota = float(compute_annual_leave(join_by_staff.get(sid), prev_year))
        result[sid] = max(0.0, prev_quota - used_by_staff.get(sid, 0.0))
    return result


def _check_quota_or_borrow(staff_id: int, join_industry_date: Optional[str], leave_type: str,
                           leave_days: float, ref_year: int, confirm_borrow: bool,
                           db: sqlite3.Connection, eff_start: Optional[date] = None,
                           other_deduct_quota: bool = True) -> float:
    """Kiểm tra hạn mức phép năm — thay cho khối kiểm tra copy-paste ở
    create_leave/resubmit_leave/create_direct_leave.

    Trả về số ngày cần "ứng" trước vào hạn mức năm sau (0.0 nếu không vượt
    hạn mức năm nay). bat_buoc/thai_san/bao_hiem không áp dụng — trả về 0.0
    ngay, không đọc gì thêm (khớp _NO_QUOTA_TYPES + "!= bat_buoc" cũ).
    leave_type="other" kèm other_deduct_quota=False cũng miễn hệt vậy — người
    tạo đơn tự chọn "Khác" không tính vào hạn mức phép năm (xem _is_no_quota_row).

    confirm_borrow=False mà vượt hạn mức: 409 kèm code "quota_exceeded_borrow"
    để FE hiện popup hỏi "ứng phép năm sau" — KHÔNG phải lỗi cứng 400, người
    dùng có thể xác nhận rồi gọi lại với confirm_borrow=True.
    confirm_borrow=True mà năm sau CŨNG không đủ chỗ ứng: 400 cứng, không cho
    tạo đơn dù đã đồng ý ứng (không ứng được "khống").
    """
    if leave_type == "bat_buoc" or _is_no_quota_row(leave_type, other_deduct_quota):
        return 0.0

    # ref_date=eff_start (ngày BẮT ĐẦU NGHỈ, không phải ngày bấm nộp đơn) — quy
    # định "chuyển kỳ hết hạn sau 31/03" nói về ngày NGHỈ THẬT phải rơi trước
    # mốc đó, không phải ngày nộp đơn (_build_form_ctx in phiếu cũng đã dùng
    # ref_date=start từ trước — dùng "hôm nay" ở đây sẽ ra 2 con số khác nhau
    # cho cùng 1 đơn vắt qua mốc 31/03, vd nộp 25/03 xin nghỉ 15/06). Trước đó
    # nữa hard-code ref_date=date(ref_year, 1, 1) (luôn là 01/01) nên check
    # "> 31/03" không bao giờ đúng — carry-over hết hạn không bao giờ được áp
    # dụng, đơn nghỉ tạo tháng 6, tháng 10 vẫn cộng thêm ngày chuyển năm.
    carry_eff = compute_carry_over(staff_id, ref_year, db, effective=True, ref_date=eff_start)
    _q_row = db.execute(
        "SELECT quota_days FROM leave_quotas WHERE staff_id=? AND year=?",
        (staff_id, ref_year),
    ).fetchone()
    quota = (float(_q_row["quota_days"]) if _q_row
             else float(compute_annual_leave(join_industry_date, ref_year)))
    used_total = _calc_used_days(staff_id, ref_year, db, include_pending=True)
    remaining = quota + carry_eff - used_total
    if leave_days <= remaining:
        return 0.0

    overflow = leave_days - max(0.0, remaining)
    if not confirm_borrow:
        raise HTTPException(409, detail={
            "code": "quota_exceeded_borrow",
            "year": ref_year, "next_year": ref_year + 1,
            "remaining": remaining, "borrow_days": overflow,
        })

    next_year = ref_year + 1
    _q_next = db.execute(
        "SELECT quota_days FROM leave_quotas WHERE staff_id=? AND year=?",
        (staff_id, next_year),
    ).fetchone()
    next_quota = (float(_q_next["quota_days"]) if _q_next
                  else float(compute_annual_leave(join_industry_date, next_year)))
    next_used = _calc_used_days(staff_id, next_year, db, include_pending=True)
    next_remaining = next_quota - next_used
    if overflow > next_remaining:
        raise HTTPException(400, f"Đã vượt quá hạn mức ngày nghỉ phép của năm {ref_year} và {next_year}")
    return overflow


def _load_lich(db: sqlite3.Connection, start: date, end: date) -> LichLamViec:
    """Lịch làm việc trong khoảng — ngày lễ + ngày làm bù.

    Ngày làm bù rơi vào T7/CN là ngày làm việc, nên nghỉ phép hôm đó VẪN bị trừ
    vào quỹ phép. Xem `backend/services/lich_lam_viec.py`."""
    return tai_lich(db, start, end)


def calculate_leave_days(
    start: date, end: date,
    lich: LichLamViec = LICH_RONG,
) -> int:
    """Đếm ngày làm việc thực (trừ T7, CN và ngày lễ). Tối thiểu 1 ngày.

    T7/CN đã khai là ngày làm bù VẪN tính — nghỉ đúng hôm đó là nghỉ một ngày
    làm việc thật nên phải trừ vào quỹ phép."""
    count = 0
    d = start
    while d <= end:
        if la_ngay_lam_viec(d, lich):
            count += 1
        d += timedelta(days=1)
    return max(count, 1)


def _period_days(
    start: date, end: date,
    lich: LichLamViec = LICH_RONG,
    leave_type: Optional[str] = None,
) -> int:
    """Số ngày của khoảng nghỉ liên tục (khi không dùng spread_dates).

    thai_san/bao_hiem/khong_luong/hop/cong_tac: tính theo ngày lịch liên tục (kể cả T7, CN, lễ).
    Các loại khác: chỉ tính ngày làm việc (calculate_leave_days).
    """
    if leave_type in _NO_QUOTA_TYPES:
        return (end - start).days + 1
    return calculate_leave_days(start, end, lich)


def _norm_vn(s) -> str:
    """Chuẩn hoá text tiếng Việt để so khớp: bỏ dấu, chữ thường, gọn khoảng trắng.

    Đ/đ không tự tách dấu qua NFD (không giống ă/â/ê...) nên phải thay tay.
    """
    if not s:
        return ""
    s = str(s).replace("Đ", "D").replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s).strip().lower()


def _is_tong_hop_staff(staff: dict, db: sqlite3.Connection) -> bool:
    dept_id = staff.get("department_id")
    if not dept_id:
        return False
    r = db.execute("SELECT code FROM departments WHERE id = ?", (dept_id,)).fetchone()
    return bool(r and r["code"].upper() in TONG_HOP_CODES)


def _can_gd_review(current: dict, db: sqlite3.Connection) -> bool:
    if current["role"] == "giam_doc":
        return True
    if current["role"] == "pho_giam_doc":
        today = _vn_now().date().isoformat()
        return db.execute(
            "SELECT id FROM delegation_records WHERE pho_giam_doc_id = ? AND is_active = 1 AND start_date <= ? AND end_date >= ?",
            (current["id"], today, today),
        ).fetchone() is not None
    return False


def _apply_status_transition(
    leave_id: int, old_status: str, new_status: str,
    start: date, end: date, staff_id: int,
    lich: LichLamViec,
    db: sqlite3.Connection,
    days: Optional[int] = None,
    is_new: bool = False,
    actor_id: Optional[int] = None,
):
    """Cập nhật status và điều chỉnh used_leave_days (idempotent).

    is_new=True: dùng khi tạo đơn đã approved ngay (GĐ tự duyệt) — old_status
    truyền vào phải là status THẬT sự đang có trong DB (để khoá lạc quan khớp),
    còn is_new mới là cờ báo "coi như mới approved" để cộng used_leave_days dù
    old_status == new_status.

    actor_id: người thực hiện thao tác gây ra chuyển trạng thái này — chỉ cần
    khi transition approved→cancelled có thể là đơn điều chỉnh NPBB (để ghi
    đúng actor cho log khôi phục đơn gốc, xem _restore_adjusted_original).
    Mặc định lấy staff_id (chủ đơn) nếu người gọi không truyền — đủ dùng cho
    các luồng tự huỷ, chỉ cancel_leave (admin/GĐ huỷ hộ) cần truyền rõ.
    """
    if days is None:
        rec = db.execute("SELECT spread_dates, leave_type, other_deduct_quota, adjusts_leave_id FROM leave_records WHERE id=?", (leave_id,)).fetchone()
        if rec and rec["spread_dates"]:
            days = len(json.loads(rec["spread_dates"]))
        else:
            days = calculate_leave_days(start, end, lich)
        leave_type = rec["leave_type"] if rec else None
        other_deduct_quota = rec["other_deduct_quota"] if rec else True
        adjusts_leave_id = rec["adjusts_leave_id"] if rec else None
    else:
        rec2 = db.execute("SELECT leave_type, other_deduct_quota, adjusts_leave_id FROM leave_records WHERE id=?", (leave_id,)).fetchone()
        leave_type = rec2["leave_type"] if rec2 else None
        other_deduct_quota = rec2["other_deduct_quota"] if rec2 else True
        adjusts_leave_id = rec2["adjusts_leave_id"] if rec2 else None

    # Khoá lạc quan: chỉ chuyển trạng thái nếu status hiện tại trong DB đúng
    # bằng old_status — chặn 2 request duyệt trùng cùng lúc (double-click, 2
    # tab) cộng/trừ used_leave_days 2 lần cho cùng 1 đơn.
    cur = db.execute(
        "UPDATE leave_records SET status = ?, updated_at = ? WHERE id = ? AND status = ?",
        (new_status, str(_vn_now()), leave_id, old_status),
    )
    if cur.rowcount == 0:
        raise HTTPException(409, "Đơn đã được xử lý bởi một yêu cầu khác, vui lòng tải lại trang")

    # Đơn điều chỉnh NPBB đã duyệt bị huỷ thẳng (vd admin/GĐ dùng cancel_leave
    # thay vì luồng Rút đơn) — đơn gốc từng bị _cancel_adjusted_original
    # chuyển "Đã hủy" lúc đơn điều chỉnh này duyệt xong phải được khôi phục
    # lại, nếu không sẽ kẹt vĩnh viễn không điều chỉnh lại được nữa.
    if old_status == LeaveStatus.APPROVED and new_status == LeaveStatus.CANCELLED and adjusts_leave_id:
        _restore_adjusted_original(adjusts_leave_id, actor_id or staff_id, db)

    # Chỉ điều chỉnh used_leave_days khi leave_type xác định và không miễn quota
    if leave_type is not None and not _is_no_quota_row(leave_type, other_deduct_quota):
        if (is_new or old_status != LeaveStatus.APPROVED) and new_status == LeaveStatus.APPROVED:
            db.execute(
                "UPDATE user_tttt SET used_leave_days = COALESCE(used_leave_days, 0) + ? WHERE id = ?",
                (days, staff_id),
            )
        elif old_status == LeaveStatus.APPROVED and new_status in (LeaveStatus.CANCELLED, LeaveStatus.REJECTED):
            db.execute(
                "UPDATE user_tttt SET used_leave_days = MAX(0, COALESCE(used_leave_days, 0) - ?) WHERE id = ?",
                (days, staff_id),
            )


def _log_action(
    db: sqlite3.Connection, leave_id: int, actor_id: int, action: str,
    comment: Optional[str], from_status: str, to_status: str,
):
    db.execute(
        "INSERT INTO leave_action_logs (leave_id, actor_id, action, comment, from_status, to_status, created_at) VALUES (?,?,?,?,?,?,?)",
        (leave_id, actor_id, action, comment, from_status, to_status, str(_vn_now())),
    )


def _cancel_adjusted_original(orig_leave_id: int, actor_id: int, db: sqlite3.Connection) -> None:
    """Chuyển đơn NPBB gốc sang "Đã hủy" khi đơn điều chỉnh của nó vừa được
    duyệt xong (approved) — gọi từ _create_leave_core (GĐ tự tạo đơn điều
    chỉnh, tự duyệt luôn) và gd_review (đơn điều chỉnh duyệt xong bước cuối).

    Không hoàn lại hạn mức của đơn gốc: bat_buoc vốn không tính vào bước CHẶN
    hạn mức (_NO_QUOTA_TYPES/"!= bat_buoc" ở _create_leave_core), nên đơn gốc
    approved chưa từng bị trừ hạn mức riêng để phải hoàn — used_leave_days chỉ
    dùng để hiển thị, đơn điều chỉnh mới sẽ cộng đúng phần của nó khi duyệt."""
    orig = db.execute("SELECT status FROM leave_records WHERE id=?", (orig_leave_id,)).fetchone()
    if not orig or orig["status"] != LeaveStatus.APPROVED:
        return
    db.execute(
        "UPDATE leave_records SET status=?, updated_at=? WHERE id=?",
        (LeaveStatus.CANCELLED, str(_vn_now()), orig_leave_id),
    )
    _log_action(db, orig_leave_id, actor_id, "npbb_adjusted_cancel", None,
                LeaveStatus.APPROVED, LeaveStatus.CANCELLED)


def _restore_adjusted_original(orig_leave_id: int, actor_id: int, db: sqlite3.Connection) -> None:
    """Đối xứng với _cancel_adjusted_original — khôi phục đơn NPBB gốc về lại
    "Hoàn thành" khi đơn điều chỉnh (đã duyệt) của nó bị rút/hủy sau đó
    (approve_recall, hoặc hủy thẳng qua cancel_leave/_apply_status_transition).

    Không có bước này, đơn gốc kẹt "Đã hủy" vĩnh viễn — npbb_adjust_leave chỉ
    nhận điều chỉnh đơn đang "Hoàn thành" nên sẽ không bao giờ điều chỉnh lại
    được nữa dù đơn điều chỉnh đã bị rút. Chỉ khôi phục khi đơn gốc ĐANG đúng
    "Đã hủy" (khoá điều kiện, tránh khôi phục nhầm nếu đơn gốc đã bị xử lý
    khác đi vì lý do gì đó không phải do đơn điều chỉnh này)."""
    orig = db.execute("SELECT status FROM leave_records WHERE id=?", (orig_leave_id,)).fetchone()
    if not orig or orig["status"] != LeaveStatus.CANCELLED:
        return
    db.execute(
        "UPDATE leave_records SET status=?, updated_at=? WHERE id=?",
        (LeaveStatus.APPROVED, str(_vn_now()), orig_leave_id),
    )
    _log_action(db, orig_leave_id, actor_id, "npbb_adjustment_recalled", None,
                LeaveStatus.CANCELLED, LeaveStatus.APPROVED)


def _validate_ksv(ksv_id: Optional[int], current: dict, db: sqlite3.Connection) -> dict:
    if not ksv_id:
        raise HTTPException(400, "Vui lòng chọn người phê duyệt bước KSV")
    ksv = db.execute("SELECT * FROM user_tttt WHERE id = ? AND is_active = 1", (ksv_id,)).fetchone()
    if not ksv:
        raise HTTPException(400, "Người phê duyệt không tồn tại hoặc đã bị vô hiệu")
    if ksv["role"] not in ("truong_phong", "pho_phong", "admin"):
        raise HTTPException(400, "Người phê duyệt phải là Trưởng phòng hoặc Phó phòng")
    if ksv_id == current["id"]:
        raise HTTPException(400, "Không thể tự phê duyệt")
    # KSV phải cùng phòng — khớp đúng get_approvers() (đã sửa: Hậu kiểm viên
    # cũng lọc theo phòng, không còn cross-department nữa).
    if ksv["role"] != "admin":
        staff_dept = current.get("department_id")
        ksv_dept   = ksv["department_id"]
        if staff_dept and ksv_dept and staff_dept != ksv_dept:
            raise HTTPException(400, "Người phê duyệt phải thuộc cùng phòng ban với người nộp đơn")
    return dict(ksv)


def _is_alt_ksv(current: dict, staff_id: int, db: sqlite3.Connection) -> bool:
    """Trưởng/Phó phòng CÙNG PHÒNG với người nộp đơn — được duyệt THAY bước
    KSV dù không phải người được chỉ định ban đầu.

    Trước đây chỉ đúng người được chỉ định (ksv_approver_id) hoặc Admin mới
    duyệt được — nếu người đó đang nghỉ phép/vắng mặt, đơn đứng yên ở
    pending_ksv vô thời hạn, chỉ Admin "duyệt nhanh" gỡ được. Điều kiện dưới
    đây khớp đúng tập ứng viên hợp lệ lúc CHỌN KSV khi tạo đơn (_validate_ksv):
    cùng phòng ban, không tự duyệt đơn của chính mình.
    """
    if current["role"] not in ("truong_phong", "pho_phong"):
        return False
    if current["id"] == staff_id:
        return False
    row = db.execute("SELECT department_id FROM user_tttt WHERE id = ?", (staff_id,)).fetchone()
    return bool(row and row["department_id"] and row["department_id"] == current.get("department_id"))


# Câu SELECT đủ mọi cột/JOIN mà 1 dòng "LeaveOut" cần — dùng chung cho cả
# _leave_to_out (1 đơn) lẫn list_leaves (nhiều đơn, xem _LEAVE_JOIN_SQL bên
# dưới bọc thêm "WHERE lr.id IN (...)" thay vì "WHERE lr.id = ?").
_LEAVE_JOIN_SQL = """SELECT lr.*,
              s.full_name AS staff_name, s.department_id AS s_dept_id, s.role AS staff_role,
              kv.full_name AS ksv_name,
              th.full_name AS th_name,
              gd.full_name AS gd_approver_name, gd.role AS gd_role,
              d.name AS dept_name,
              db_user.full_name AS declarer_name,
              -- PGĐ chỉ duyệt được khi còn ủy quyền hiệu lực HÔM NAY. Tính sẵn ở
              -- đây (không phải chỉ trong gd_review) để màn hình nói được lý do
              -- vì sao người duyệt không có nút, thay vì im lặng.
              CASE WHEN gd.role = 'pho_giam_doc' THEN
                   (SELECT COUNT(*) FROM delegation_records dr
                     WHERE dr.pho_giam_doc_id = gd.id AND dr.is_active = 1
                       AND dr.start_date <= ? AND dr.end_date >= ?)
                   ELSE 1 END AS gd_can_review
       FROM leave_records lr
       LEFT JOIN user_tttt s       ON lr.staff_id             = s.id
       LEFT JOIN user_tttt kv      ON lr.ksv_approver_id      = kv.id
       LEFT JOIN user_tttt th      ON lr.tong_hop_approver_id = th.id
       LEFT JOIN user_tttt gd      ON lr.gd_approver_id       = gd.id
       LEFT JOIN departments d     ON s.department_id          = d.id
       LEFT JOIN user_tttt db_user ON lr.direct_by             = db_user.id"""


def _npbb_brief_row(o) -> dict:
    """Tóm tắt 1 đơn NPBB liên quan (đơn gốc hoặc đơn điều chỉnh) — hình dạng
    dùng chung cho cả adjusts_leave lẫn npbb_adjustment trong LeaveOut."""
    return {
        "id": o["id"], "status": o["status"],
        "start_date": o["start_date"], "end_date": o["end_date"],
        "spread_dates": json.loads(o["spread_dates"]) if o["spread_dates"] else None,
    }


def _leave_row_to_dict(r, lich: LichLamViec, is_resubmitted: bool,
                       adjusts_leave: Optional[dict], npbb_adjustment: Optional[dict]) -> dict:
    """Dựng dict LeaveOut từ 1 dòng đã SELECT bằng _LEAVE_JOIN_SQL, cộng phần
    phải tra riêng theo lô (lịch làm việc, is_resubmitted, NPBB 2 chiều) —
    tách khỏi _leave_to_out để list_leaves tra 1 lần cho cả danh sách thay vì
    lặp lại N lần (mỗi lần thêm vài câu SQL riêng, xem list_leaves)."""
    start = date.fromisoformat(r["start_date"])
    end   = date.fromisoformat(r["end_date"])
    _days = len(json.loads(r["spread_dates"])) if r["spread_dates"] else _period_days(start, end, lich, r["leave_type"])

    _status_label = _LEAVE_STATUS_VN.get(r["status"], r["status"])
    if r["status"] == LeaveStatus.CANCELLED and npbb_adjustment and npbb_adjustment["status"] == LeaveStatus.APPROVED:
        _status_label = "Đã hủy - Đã điều chỉnh"

    return {
        "id":                     r["id"],
        "staff_id":               r["staff_id"],
        "staff_name":             r["staff_name"] or "",
        "staff_role":             r["staff_role"],
        "department_name":        r["dept_name"],
        "start_date":             r["start_date"],
        "end_date":               r["end_date"],
        "leave_days":             _days,
        "leave_type":             r["leave_type"],
        "reason":                 r["reason"],
        "status":                 r["status"],
        "status_label":           _status_label,
        "adjusts_leave_id":       r["adjusts_leave_id"],
        "adjusts_leave":          adjusts_leave,
        "npbb_adjustment":        npbb_adjustment,
        "ksv_approver_id":        r["ksv_approver_id"],
        "ksv_approver_name":      r["ksv_name"],
        "ksv_approved_at":        r["ksv_approved_at"],
        "ksv_comment":            r["ksv_comment"],
        "tong_hop_approver_id":   r["tong_hop_approver_id"],
        "tong_hop_approver_name": r["th_name"],
        "tong_hop_approved_at":   r["tong_hop_approved_at"],
        "tong_hop_comment":       r["tong_hop_comment"],
        "gd_approver_id":         r["gd_approver_id"],
        "gd_approver_name":       r["gd_approver_name"],
        "gd_is_pgd":              (r["gd_role"] == "pho_giam_doc") if r["gd_role"] else False,
        "gd_can_review":          bool(r["gd_can_review"]),
        "gd_approved_at":         r["gd_approved_at"],
        "gd_comment":             r["gd_comment"],
        "is_direct":              bool(r["is_direct"]) if r["is_direct"] is not None else False,
        "declarer_name":          r["declarer_name"] or "",
        "spread_dates":           json.loads(r["spread_dates"]) if r["spread_dates"] else None,
        "recall_reason":          r["recall_reason"],
        "borrow_next_year_days":  r["borrow_next_year_days"] or 0.0,
        "other_deduct_quota":     bool(r["other_deduct_quota"]) if r["other_deduct_quota"] is not None else True,
        "created_at":             r["created_at"],
        "rejected_step":          (
            "GĐ"  if r["status"] == "rejected" and r["gd_approved_at"]
            else "TH"  if r["status"] == "rejected" and r["tong_hop_approved_at"]
            else "KSV" if r["status"] == "rejected"
            else None
        ),
        "is_resubmitted": is_resubmitted,
    }


def _leave_to_out(leave_id: int, db: sqlite3.Connection) -> dict:
    today = _vn_now().date().isoformat()
    r = db.execute(f"{_LEAVE_JOIN_SQL}\n           WHERE lr.id = ?", (today, today, leave_id)).fetchone()
    if not r:
        return {}

    start = date.fromisoformat(r["start_date"])
    end   = date.fromisoformat(r["end_date"])
    lich = _load_lich(db, start, end)

    # NPBB — đơn gốc mà đơn NÀY điều chỉnh (nếu có), và đơn điều chỉnh trỏ VỀ
    # đơn này (nếu đơn này là bat_buoc và có ai đó điều chỉnh nó).
    def _npbb_ref(other_id):
        o = db.execute(
            "SELECT id, status, start_date, end_date, spread_dates FROM leave_records WHERE id=?",
            (other_id,),
        ).fetchone()
        return _npbb_brief_row(o) if o else None

    adjusts_leave = _npbb_ref(r["adjusts_leave_id"]) if r["adjusts_leave_id"] else None
    npbb_adjustment = None
    if r["leave_type"] == "bat_buoc":
        _adj_row = db.execute(
            "SELECT id FROM leave_records WHERE adjusts_leave_id=? "
            "AND status NOT IN ('rejected') ORDER BY created_at DESC LIMIT 1",
            (leave_id,),
        ).fetchone()
        if _adj_row:
            npbb_adjustment = _npbb_ref(_adj_row["id"])

    is_resubmitted = bool(db.execute(
        "SELECT 1 FROM leave_action_logs WHERE leave_id=? AND action='resubmit' LIMIT 1",
        (leave_id,)
    ).fetchone())

    return _leave_row_to_dict(r, lich, is_resubmitted, adjusts_leave, npbb_adjustment)


# ─── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/approvers")
def get_approvers(
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(get_current_staff),
):
    _ROLE_LABEL = {
        "truong_phong":  "Trưởng phòng",
        "pho_phong":     "Phó phòng",
        "admin":         "Quản trị viên cấp 1",
    }
    dept_id = current.get("department_id")
    if dept_id:
        # Chỉ lấy KSV cùng phòng (Trưởng/Phó phòng) với người tạo đơn. Hậu kiểm viên
        # KHÔNG duyệt nghỉ phép — ngang chuyên viên ở quy trình này.
        rows = db.execute(
            """SELECT id, full_name, role FROM user_tttt
               WHERE is_active = 1 AND id != ?
                 AND role IN ('truong_phong','pho_phong')
                 AND department_id = ?
               ORDER BY full_name""",
            (current["id"], dept_id),
        ).fetchall()
    else:
        rows = db.execute(
            """SELECT id, full_name, role FROM user_tttt
               WHERE is_active = 1 AND role IN ('truong_phong','pho_phong','admin')
                 AND id != ? ORDER BY full_name""",
            (current["id"],),
        ).fetchall()
    return [{"id": r["id"], "full_name": r["full_name"], "role_label": _ROLE_LABEL.get(r["role"], r["role"])} for r in rows]


@router.get("/gd-list")
def get_gd_list(
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(get_current_staff),
):
    rows = db.execute(
        "SELECT id, full_name, role FROM user_tttt WHERE is_active = 1 AND role IN ('giam_doc','pho_giam_doc')"
    ).fetchall()
    _ROLE_LABEL = {"giam_doc": "Giám đốc", "pho_giam_doc": "Phó Giám đốc"}
    return [{"id": r["id"], "full_name": r["full_name"], "role_label": _ROLE_LABEL.get(r["role"], r["role"])} for r in rows]


def _create_leave_core(body: LeaveCreate, current: dict, db: sqlite3.Connection,
                        adjusts_leave_id: Optional[int] = None, action: str = "create") -> int:
    """Lõi tạo 1 đơn nghỉ phép — dùng chung cho create_leave (đơn mới bình
    thường) và npbb_adjust_leave (đơn điều chỉnh NPBB, adjusts_leave_id trỏ về
    đơn gốc). Không commit — người gọi tự commit sau khi làm xong việc riêng
    (vd npbb_adjust_leave còn phải kiểm tra đơn gốc trước khi gọi hàm này)."""
    if body.leave_type not in _VALID_LEAVE_TYPES:
        raise HTTPException(400, f"Loại nghỉ phép không hợp lệ: {body.leave_type}")

    # ── Xử lý spread_dates (nghỉ ngày lẻ không liên tục) ──
    if body.spread_dates:
        spread = sorted(set(body.spread_dates))
        if len(spread) < 1:
            raise HTTPException(400, "spread_dates phải có ít nhất 1 ngày")
        try:
            eff_start = date.fromisoformat(spread[0])
            eff_end   = date.fromisoformat(spread[-1])
        except ValueError:
            raise HTTPException(400, "Định dạng ngày không hợp lệ (yêu cầu YYYY-MM-DD)")
        leave_days = len(spread)
        spread_json = json.dumps(spread)
        _lich = _load_lich(db, eff_start, eff_end)
    else:
        if body.end_date < body.start_date:
            raise HTTPException(400, "Ngày kết thúc phải sau ngày bắt đầu")
        eff_start   = body.start_date
        eff_end     = body.end_date
        _lich = _load_lich(db, eff_start, eff_end)
        leave_days = _period_days(eff_start, eff_end, _lich, body.leave_type)
        spread_json = None

    if body.leave_type == "annual":
        if eff_start < _vn_now().date():
            raise HTTPException(400, "Nghỉ phép năm phải từ hôm nay trở đi")

    # Kiểm tra hạn mức — trả về số ngày cần ứng trước năm sau nếu vượt hạn mức
    # năm nay và người tạo đơn đã đồng ý (confirm_borrow_next_year), 0.0 nếu
    # không vượt hoặc loại nghỉ không áp dụng (bat_buoc/thai_san/bao_hiem).
    borrow_days = _check_quota_or_borrow(
        current["id"], current.get("join_industry_date"), body.leave_type,
        leave_days, eff_start.year, body.confirm_borrow_next_year, db,
        eff_start=eff_start, other_deduct_quota=body.other_deduct_quota,
    )

    if body.leave_type == "bat_buoc" and leave_days < 5:
        raise HTTPException(400, "Nghỉ phép bắt buộc phải từ 5 ngày làm việc trở lên")

    # Kiểm tra trùng ngày theo spread_dates thực tế (không dùng envelope khi có spread)
    # Đơn điều chỉnh NPBB (adjusts_leave_id) được phép trùng với chính đơn gốc
    # — đơn gốc sẽ tự chuyển "Đã hủy" khi đơn điều chỉnh này duyệt xong, xem
    # _cancel_adjusted_original.
    _excl_sql = " AND id != ?" if adjusts_leave_id else ""
    _excl_params = [adjusts_leave_id] if adjusts_leave_id else []
    if body.spread_dates:
        _existing = db.execute(
            f"""SELECT start_date, end_date, spread_dates FROM leave_records
               WHERE staff_id=? {_excl_sql} AND status NOT IN ('rejected','cancelled')
                 AND (reason IS NULL OR NOT (reason LIKE '[Import]%' OR reason LIKE '[Điều chỉnh]%'))""",
            [current["id"]] + _excl_params
        ).fetchall()
        _new_days = set(spread)
        for _el in _existing:
            if _el["spread_dates"]:
                if _new_days & set(json.loads(_el["spread_dates"])):
                    raise HTTPException(409, "Khoảng ngày nghỉ bị trùng với đơn hiện có")
            elif any(_el["start_date"] <= d <= _el["end_date"] for d in spread):
                raise HTTPException(409, "Khoảng ngày nghỉ bị trùng với đơn hiện có")
    else:
        # Đơn mới là khoảng liên tục — với đơn hiện có CÓ spread_dates, phải so
        # với các ngày thực tế (không phải envelope start/end) để tránh báo
        # trùng oan khi khoảng mới chỉ chồng lên envelope chứ không chạm ngày
        # thực nào.
        _existing2 = db.execute(
            f"""SELECT start_date, end_date, spread_dates FROM leave_records
               WHERE staff_id=? {_excl_sql} AND status NOT IN ('rejected','cancelled')
                 AND (reason IS NULL OR NOT (reason LIKE '[Import]%' OR reason LIKE '[Điều chỉnh]%'))
                 AND start_date<=? AND end_date>=?""",
            [current["id"]] + _excl_params + [eff_end.isoformat(), eff_start.isoformat()]
        ).fetchall()
        if _existing2:
            _new_range_days = None
            for _el in _existing2:
                if _el["spread_dates"]:
                    if _new_range_days is None:
                        _new_range_days, _d = set(), eff_start
                        while _d <= eff_end:
                            _new_range_days.add(_d.isoformat())
                            _d += timedelta(days=1)
                    if set(json.loads(_el["spread_dates"])) & _new_range_days:
                        raise HTTPException(409, "Khoảng ngày nghỉ bị trùng với đơn hiện có")
                else:
                    raise HTTPException(409, "Khoảng ngày nghỉ bị trùng với đơn hiện có")

    if current["role"] == "giam_doc":
        # GĐ là cấp cao nhất — tự duyệt ngay, không qua quy trình
        initial_status  = LeaveStatus.APPROVED
        ksv_approver_id = None
    elif current["role"] in _HIGH_ROLES:
        initial_status  = LeaveStatus.PENDING_TONG_HOP
        ksv_approver_id = None
    else:
        ksv = _validate_ksv(body.ksv_approver_id, current, db)
        initial_status  = LeaveStatus.PENDING_KSV
        ksv_approver_id = ksv["id"]

    # Nếu user chọn trước Ban lãnh đạo, validate
    gd_approver_id = None
    gd_approved_at = None
    if current["role"] == "giam_doc":
        # GĐ tự duyệt đơn của chính mình — ghi nhận GĐ là người duyệt
        gd_approver_id = current["id"]
        gd_approved_at = str(_vn_now())
    elif body.gd_approver_id:
        gd_staff = db.execute(
            "SELECT id, role FROM user_tttt WHERE id=? AND is_active=1", (body.gd_approver_id,)
        ).fetchone()
        if gd_staff and gd_staff["role"] in ("giam_doc", "pho_giam_doc"):
            gd_approver_id = gd_staff["id"]

    cur = db.execute(
        """INSERT INTO leave_records
               (staff_id, start_date, end_date, leave_type, reason, status,
                ksv_approver_id, gd_approver_id, gd_approved_at, spread_dates,
                adjusts_leave_id, borrow_next_year_days, other_deduct_quota, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (current["id"], eff_start.isoformat(), eff_end.isoformat(),
         body.leave_type, body.reason, initial_status, ksv_approver_id,
         gd_approver_id, gd_approved_at, spread_json, adjusts_leave_id,
         borrow_days, int(body.other_deduct_quota), str(_vn_now()), str(_vn_now())),
    )
    leave_id = cur.lastrowid
    if body.signature:
        _save_signature(db, leave_id, "nguoi_de_nghi", current["id"], body.signature)
    _log_action(db, leave_id, current["id"], action, None, "", initial_status)
    if initial_status == LeaveStatus.APPROVED:
        _apply_status_transition(leave_id, LeaveStatus.APPROVED, LeaveStatus.APPROVED,
                                 eff_start, eff_end, current["id"], _lich, db, is_new=True)
        if adjusts_leave_id:
            _cancel_adjusted_original(adjusts_leave_id, current["id"], db)
    return leave_id


@router.post("/")
def create_leave(
    body: LeaveCreate,
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(require_feature("leaves.create")),
):
    if current.get("role") == "admin":
        raise HTTPException(403, "Admin không tham gia quy trình nghỉ phép")
    leave_id = _create_leave_core(body, current, db)
    db.commit()
    return _leave_to_out(leave_id, db)


@router.post("/{leave_id}/npbb-adjust")
def npbb_adjust_leave(
    leave_id: int,
    body: LeaveCreate,
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(require_feature("leaves.create")),
):
    """Điều chỉnh ngày nghỉ phép bắt buộc SAU KHI đơn gốc đã "Hoàn thành" —
    tạo 1 ĐƠN MỚI riêng (adjusts_leave_id trỏ về đơn gốc), đi qua đủ 3 bước
    duyệt như đơn bình thường. Đơn gốc tự chuyển "Đã hủy" khi đơn này duyệt
    xong (xem _cancel_adjusted_original, gọi từ _create_leave_core khi GĐ tự
    tạo & tự duyệt, hoặc từ gd_review khi duyệt qua đủ 3 bước)."""
    orig = db.execute("SELECT * FROM leave_records WHERE id=?", (leave_id,)).fetchone()
    if not orig:
        raise HTTPException(404, "Không tìm thấy đơn nghỉ phép")
    if orig["staff_id"] != current["id"]:
        raise HTTPException(403, "Chỉ chủ nhân đơn mới được điều chỉnh")
    if orig["leave_type"] != "bat_buoc":
        raise HTTPException(400, "Chỉ đơn nghỉ phép bắt buộc mới điều chỉnh được theo cách này")
    # Không cho điều chỉnh CHỒNG lên 1 đơn điều chỉnh khác — mọi lần điều
    # chỉnh luôn trỏ thẳng về đúng 1 đơn NPBB GỐC duy nhất (adjusts_leave_id
    # IS NULL), không xếp chuỗi nhiều cấp. Muốn điều chỉnh tiếp thì phải rút/
    # huỷ đơn điều chỉnh hiện tại trước — lúc đó đơn gốc tự khôi phục lại
    # "Hoàn thành" (xem _restore_adjusted_original) và điều chỉnh lại được
    # bình thường. Lý do: báo cáo NPBB (export_npbb_batch) chỉ dò đúng 1 cấp
    # cha-con để tìm "đơn điều chỉnh mới nhất còn hiệu lực" — xếp chuỗi nhiều
    # cấp sẽ khiến nhân sự biến mất khỏi báo cáo khi cấp giữa bị thay thế.
    if orig["adjusts_leave_id"] is not None:
        raise HTTPException(
            400,
            "Đây là đơn điều chỉnh — không thể điều chỉnh tiếp lên đơn điều chỉnh. "
            "Vui lòng rút/hủy đơn điều chỉnh này trước, đơn gốc sẽ tự khôi phục "
            "\"Hoàn thành\" để điều chỉnh lại.",
        )
    if orig["status"] != LeaveStatus.APPROVED:
        raise HTTPException(400, "Chỉ điều chỉnh được đơn đã hoàn thành")
    _active = db.execute(
        """SELECT id FROM leave_records WHERE adjusts_leave_id=?
           AND status NOT IN ('rejected','cancelled') LIMIT 1""",
        (leave_id,),
    ).fetchone()
    if _active:
        raise HTTPException(409, "Đơn này đã có đơn điều chỉnh đang xử lý")
    if body.leave_type != "bat_buoc":
        raise HTTPException(400, "Đơn điều chỉnh phải cùng loại nghỉ phép bắt buộc")
    new_leave_id = _create_leave_core(body, current, db, adjusts_leave_id=leave_id, action="npbb_adjust")
    db.commit()
    return _leave_to_out(new_leave_id, db)


@router.get("/")
def list_leaves(
    scope: str = "mine",
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(get_current_staff),
):
    role = current["role"]
    # Bản ghi tổng hợp giả (nhập Excel / sửa tay hạn mức, xem update_used_days và
    # import_quota_apply) chỉ phục vụ tính _calc_used_days — không phải đơn nghỉ
    # phép thật, không có người nộp/KSV/TH/GĐ nào cả. Ẩn khỏi mọi danh sách đơn để
    # khỏi hiện như 1 đơn thật trong "Đơn của tôi"/"Chờ duyệt"/lịch/toàn trung tâm.
    clauses: list = ["(reason IS NULL OR NOT (reason LIKE '[Import]%' OR reason LIKE '[Điều chỉnh]%'))"]
    params: list  = []

    if scope == "mine":
        clauses.append("staff_id = ?")
        params.append(current["id"])

    elif scope == "pending":
        # Đơn của GĐ đã tự động approved nhưng Tổng hợp chưa "biết" — chỉ mang tính
        # thông báo (xem tong-hop-ack), không phải điều kiện duyệt.
        _gd_unack = (
            "(status = 'approved' AND tong_hop_approver_id IS NULL "
            "AND staff_id IN (SELECT id FROM user_tttt WHERE role = 'giam_doc'))"
        )
        if role == "admin":
            clauses.append(f"(status IN ('pending_ksv','pending_tong_hop','pending_gd') OR {_gd_unack})")
        elif role in ("giam_doc", "pho_giam_doc"):
            if not _can_gd_review(current, db):
                return []
            clauses.append("gd_approver_id = ? AND status = 'pending_gd'")
            params.append(current["id"])
        elif _is_tong_hop_staff(current, db):
            if role in ("truong_phong", "pho_phong"):
                # PP/TP Tổng hợp: duyệt bước TH cho toàn trung tâm
                # VÀ duyệt bước KSV cho nhân viên phòng mình (kể cả KSV thay
                # thế — cùng phòng, không phải người được chỉ định ban đầu,
                # xem _is_alt_ksv).
                clauses.append(
                    f"(status = 'pending_tong_hop' OR "
                    f"((ksv_approver_id = ? OR staff_id IN "
                    f"(SELECT id FROM user_tttt WHERE department_id = ? AND id != ?)) "
                    f"AND status = 'pending_ksv') OR {_gd_unack})"
                )
                params += [current["id"], current.get("department_id"), current["id"]]
            else:
                clauses.append(f"(status = 'pending_tong_hop' OR {_gd_unack})")
        elif role in ("truong_phong", "pho_phong"):
            # Kể cả KSV thay thế cùng phòng — xem _is_alt_ksv.
            clauses.append(
                "((ksv_approver_id = ? OR staff_id IN "
                "(SELECT id FROM user_tttt WHERE department_id = ? AND id != ?)) "
                "AND status = 'pending_ksv')"
            )
            params += [current["id"], current.get("department_id"), current["id"]]
        else:
            return []

    elif scope == "declared":
        # Người khai báo hộ xem các đơn mình đã khai báo
        clauses.append("direct_by = ?")
        params.append(current["id"])

    elif scope == "dept":
        # Phó phòng / Trưởng phòng xem tất cả đơn của nhân viên trong phòng mình
        if role not in ("truong_phong", "pho_phong", "admin"):
            raise HTTPException(403, "Không có quyền xem đơn phòng")
        dept_id = current.get("department_id")
        if not dept_id:
            return []
        clauses.append("staff_id IN (SELECT id FROM user_tttt WHERE department_id = ? AND is_active = 1)")
        params.append(dept_id)

    elif scope == "all":
        if role not in ("admin", "giam_doc", "pho_giam_doc"):
            if not _is_tong_hop_staff(current, db):
                raise HTTPException(403, "Không có quyền xem tất cả đơn")

    else:
        raise HTTPException(400, "scope phải là mine | pending | declared | dept | all")

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    # 1 câu duy nhất cho cả danh sách (không phải 1 câu id + N câu _leave_to_out
    # riêng từng dòng) — mệnh đề where ở trên chỉ tham chiếu cột của leave_records
    # (không alias) nên bọc nguyên vào 1 subquery lọc id là an toàn, không đụng
    # gì tới cách dựng clauses/params phía trên.
    today = _vn_now().date().isoformat()
    id_where_sql = f"SELECT id FROM leave_records {where}"
    rows = db.execute(
        f"{_LEAVE_JOIN_SQL}\n           WHERE lr.id IN ({id_where_sql})\n           ORDER BY lr.created_at DESC",
        [today, today] + params,
    ).fetchall()
    if not rows:
        return []

    # Lịch làm việc: 1 lần cho cả danh sách (khoảng rộng nhất bao hết mọi đơn)
    # thay vì mỗi đơn 1 lần — LichLamViec là tập ngày lễ/bù trong khoảng nạp,
    # nạp rộng hơn chỉ là tập cha, la_ngay_lam_viec() vẫn ra đúng kết quả từng
    # ngày. Bỏ qua hẳn nếu MỌI đơn đều có spread_dates (khi đó _period_days
    # không bao giờ được gọi tới, lịch nạp về sẽ không dùng vào đâu).
    if any(not r["spread_dates"] for r in rows):
        lich = _load_lich(
            db,
            min(date.fromisoformat(r["start_date"]) for r in rows),
            max(date.fromisoformat(r["end_date"]) for r in rows),
        )
    else:
        lich = LICH_RONG

    leave_ids = [r["id"] for r in rows]
    ph = ",".join("?" for _ in leave_ids)
    resubmitted_ids = {rr["leave_id"] for rr in db.execute(
        f"SELECT DISTINCT leave_id FROM leave_action_logs WHERE action='resubmit' AND leave_id IN ({ph})",
        leave_ids,
    ).fetchall()}

    # NPBB, chiều "đơn gốc mà 1 dòng trong danh sách điều chỉnh" — chỉ những
    # đơn có adjusts_leave_id mới cần tra.
    adj_target_ids = {r["adjusts_leave_id"] for r in rows if r["adjusts_leave_id"]}
    adjusts_leave_by_id: dict = {}
    if adj_target_ids:
        ph2 = ",".join("?" for _ in adj_target_ids)
        for rr in db.execute(
            f"SELECT id, status, start_date, end_date, spread_dates FROM leave_records WHERE id IN ({ph2})",
            list(adj_target_ids),
        ).fetchall():
            adjusts_leave_by_id[rr["id"]] = _npbb_brief_row(rr)

    # NPBB, chiều "đơn điều chỉnh trỏ VỀ 1 đơn bat_buoc trong danh sách" — chỉ
    # đơn bat_buoc mới có thể bị điều chỉnh, y hệt điều kiện trong _leave_to_out.
    bat_buoc_ids = [r["id"] for r in rows if r["leave_type"] == "bat_buoc"]
    npbb_adjustment_by_original: dict = {}
    if bat_buoc_ids:
        ph3 = ",".join("?" for _ in bat_buoc_ids)
        for rr in db.execute(
            f"""SELECT id, adjusts_leave_id, status, start_date, end_date, spread_dates
               FROM leave_records WHERE adjusts_leave_id IN ({ph3})
                 AND status NOT IN ('rejected') ORDER BY created_at DESC""",
            bat_buoc_ids,
        ).fetchall():
            # Giữ dòng ĐẦU TIÊN mỗi đơn gốc (đã ORDER BY created_at DESC) — khớp
            # đúng "ORDER BY created_at DESC LIMIT 1" của _leave_to_out.
            npbb_adjustment_by_original.setdefault(rr["adjusts_leave_id"], _npbb_brief_row(rr))

    return [
        _leave_row_to_dict(
            r, lich,
            r["id"] in resubmitted_ids,
            adjusts_leave_by_id.get(r["adjusts_leave_id"]) if r["adjusts_leave_id"] else None,
            npbb_adjustment_by_original.get(r["id"]),
        )
        for r in rows
    ]


@router.get("/today")
def leaves_today(
    db: sqlite3.Connection = Depends(get_db),
    _: dict = Depends(get_current_staff),
):
    """Thống kê nghỉ phép hôm nay: tổng + phân theo phòng."""
    # Chỉ đếm đơn ĐÃ DUYỆT — cố ý khác /calendar (lịch tháng hiện cả đơn chờ,
    # nhưng có nhãn trạng thái đi kèm). Endpoint này chỉ phục vụ card "Nghỉ phép
    # hôm nay" ở Trang chủ — con số trần, không nhãn — nên gộp đơn chưa duyệt vào
    # sẽ báo người vẫn đang đi làm là đã nghỉ. Đừng "đồng bộ" hai chỗ này.
    today = _vn_now().date().isoformat()
    rows = db.execute(
        """SELECT lr.id, lr.spread_dates, lr.start_date, lr.end_date,
                  u.full_name, d.name AS dept_name
           FROM leave_records lr
           JOIN user_tttt u ON lr.staff_id = u.id
           LEFT JOIN departments d ON u.department_id = d.id
           WHERE lr.status = 'approved'
             AND (lr.reason IS NULL OR NOT (lr.reason LIKE '[Import]%' OR lr.reason LIKE '[Điều chỉnh]%'))
             AND lr.start_date <= ? AND lr.end_date >= ?""",
        (today, today),
    ).fetchall()

    result = []
    for r in rows:
        if r["spread_dates"]:
            if today not in json.loads(r["spread_dates"]):
                continue
        result.append({
            "staff_name": r["full_name"] or "",
            "dept_name":  r["dept_name"] or "—",
        })

    by_dept: dict = {}
    for item in result:
        d = item["dept_name"]
        by_dept[d] = by_dept.get(d, 0) + 1

    return {
        "total":   len(result),
        "by_dept": [{"dept_name": d, "count": c}
                    for d, c in sorted(by_dept.items(), key=lambda x: -x[1])],
    }


@router.get("/calendar")
def leave_calendar(
    year: int,
    month: int,
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(get_current_staff),
):
    import calendar as _cal
    if not (1 <= month <= 12):
        raise HTTPException(400, "month phải từ 1 đến 12")
    # date(year, ...) bên dưới ném ValueError nếu năm ngoài 1..9999 → HTTP 500
    if not (2000 <= year <= 2100):
        raise HTTPException(400, "year phải từ 2000 đến 2100")
    last_day = _cal.monthrange(year, month)[1]
    start = date(year, month, 1)
    end   = date(year, month, last_day)

    # Xem toàn trung tâm: Admin/Ban Giám đốc/Phòng Tổng hợp — đúng tiêu chí của
    # scope="all" trong list_leaves() phía trên, để không tạo ra 2 định nghĩa
    # "ai xem được toàn trung tâm" khác nhau trong cùng module.
    # Hậu kiểm viên KHÔNG nằm trong danh sách: họ ngang chuyên viên ở quy trình
    # nghỉ phép, scope="all" và scope="dept" đều trả 403 cho họ
    # (tests/test_nghi_phep_hau_kiem_vien.py). Cho họ xem cả lịch là mở lại đúng
    # đường vừa bịt, chỉ khác cửa.
    # Phòng khác chỉ thấy người CÙNG PHÒNG nghỉ ngày nào — theo yêu cầu nghiệp vụ.
    sees_all = (current["role"] in ("admin", "giam_doc", "pho_giam_doc")
                or _is_tong_hop_staff(current, db))

    clauses = ["lr.status NOT IN ('rejected','cancelled')",
               "(lr.reason IS NULL OR NOT (lr.reason LIKE '[Import]%' OR lr.reason LIKE '[Điều chỉnh]%'))",
               "lr.start_date <= ?", "lr.end_date >= ?"]
    params: list = [end.isoformat(), start.isoformat()]
    if not sees_all:
        dept_id = current.get("department_id")
        if dept_id:
            clauses.append("ks.department_id = ?")
            params.append(dept_id)
        else:
            # Không thuộc phòng nào (hiếm gặp) — chỉ thấy đơn của chính mình,
            # không trả lỗi/để trống cả lịch.
            clauses.append("lr.staff_id = ?")
            params.append(current["id"])

    leaves = db.execute(
        f"""SELECT lr.id, lr.start_date, lr.end_date, lr.leave_type, lr.status,
                   ks.full_name, d.name AS dept_name
            FROM leave_records lr
            LEFT JOIN user_tttt ks ON lr.staff_id = ks.id
            LEFT JOIN departments d ON ks.department_id = d.id
            WHERE {' AND '.join(clauses)}""",
        params,
    ).fetchall()

    day_map: dict = {}
    cur = start
    while cur <= end:
        day_map[cur.isoformat()] = []
        cur += timedelta(days=1)

    for lv in leaves:
        cur = max(date.fromisoformat(lv["start_date"]), start)
        lv_end = min(date.fromisoformat(lv["end_date"]), end)
        while cur <= lv_end:
            day_map[cur.isoformat()].append({
                "staff_name": lv["full_name"] or "",
                "dept_name":  lv["dept_name"] or "",
                "leave_type": lv["leave_type"],
                "status":     lv["status"],
                "leave_id":   lv["id"],
            })
            cur += timedelta(days=1)

    return {"year": year, "month": month, "days": day_map}


@router.get("/export")
def export_leaves(
    scope: str = "all",
    ids: str = "",        # danh sách id cách nhau bởi dấu phẩy, ưu tiên hơn scope
    date_from: str = "",  # ISO yyyy-mm-dd, lọc thêm theo khoảng ngày nghỉ (tuỳ chọn)
    date_to: str = "",
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(get_current_staff),
):
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill

    role = current["role"]
    # Bản ghi tổng hợp giả (nhập Excel / sửa tay hạn mức) không phải đơn nghỉ phép
    # thật — ẩn khỏi file xuất, xem chú thích tương tự ở list_leaves().
    clauses: list = ["(lr.reason IS NULL OR NOT (lr.reason LIKE '[Import]%' OR lr.reason LIKE '[Điều chỉnh]%'))"]
    params: list  = []

    # Nếu có danh sách ID cụ thể → xuất đúng những dòng đó
    if ids:
        id_list = [int(i.strip()) for i in ids.split(",") if i.strip().isdigit()]
        if not id_list:
            raise HTTPException(400, "ids không hợp lệ")
        placeholders = ",".join("?" * len(id_list))
        clauses.append(f"lr.id IN ({placeholders})")
        params.extend(id_list)
    elif scope == "mine":
        clauses.append("lr.staff_id = ?")
        params.append(current["id"])
    elif scope == "all":
        if role not in ("admin", "giam_doc", "pho_giam_doc"):
            if not _is_tong_hop_staff(current, db):
                raise HTTPException(403, "Không có quyền xuất tất cả đơn")
    elif scope == "pending":
        if _is_tong_hop_staff(current, db) and role in ("truong_phong", "pho_phong"):
            clauses.append(
                "(lr.status = 'pending_tong_hop' OR "
                "(lr.ksv_approver_id = ? AND lr.status = 'pending_ksv'))"
            )
            params.append(current["id"])
        elif role in ("truong_phong", "pho_phong"):
            clauses.append("lr.ksv_approver_id = ? AND lr.status = 'pending_ksv'")
            params.append(current["id"])
        elif _is_tong_hop_staff(current, db):
            clauses.append("lr.status = 'pending_tong_hop'")
        elif role in ("giam_doc", "pho_giam_doc", "admin"):
            clauses.append("lr.status = 'pending_gd'")
        else:
            clauses.append("1=0")
    elif scope in ("dept", "declared"):
        clauses.append("1=1")  # allow all, scope already handled by client
    else:
        raise HTTPException(400, "scope phải là mine | pending | all | dept | declared")

    # Lọc thêm theo khoảng ngày nghỉ nếu có — trước đây frontend tính fv/tv chỉ để
    # đặt TÊN FILE (vd "..._01012026-31012026...") nhưng không gửi lên đây, khiến nội
    # dung file luôn là toàn bộ scope bất kể tên file ghi gì — dễ hiểu lầm báo cáo sai kỳ.
    if date_from:
        clauses.append("lr.end_date >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("lr.start_date <= ?")
        params.append(date_to)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    leaves = db.execute(
        f"""SELECT lr.*, s.full_name AS staff_name, s.department_id AS s_dept_id,
                   kv.full_name AS ksv_name, th.full_name AS th_name,
                   gd.full_name AS gd_name, gd.role AS gd_role,
                   d.name AS dept_name
            FROM leave_records lr
            LEFT JOIN user_tttt s  ON lr.staff_id             = s.id
            LEFT JOIN user_tttt kv ON lr.ksv_approver_id      = kv.id
            LEFT JOIN user_tttt th ON lr.tong_hop_approver_id = th.id
            LEFT JOIN user_tttt gd ON lr.gd_approver_id       = gd.id
            LEFT JOIN departments d ON s.department_id          = d.id
            {where}
            ORDER BY lr.created_at DESC""",
        params,
    ).fetchall()

    # Tải tất cả ngày lễ 1 lần cho toàn bộ khoảng
    all_lich: LichLamViec = LICH_RONG
    if leaves:
        min_d = min(date.fromisoformat(lv["start_date"]) for lv in leaves)
        max_d = max(date.fromisoformat(lv["end_date"])   for lv in leaves)
        all_lich = _load_lich(db, min_d, max_d)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Nghỉ phép"

    hdr_fill = PatternFill("solid", fgColor="C62828")
    hdr_font = Font(bold=True, color="FFFFFF")
    headers  = ["STT", "Họ và tên", "Phòng", "Loại nghỉ",
                "Ngày nghỉ", "Số ngày", "Trạng thái",
                "KSV duyệt", "Phòng Tổng hợp", "GĐ/PGĐ", "Ngày tạo"]
    widths   = [6, 25, 20, 18, 40, 9, 18, 22, 22, 22, 14]
    ws.append(headers)
    for cell, w in zip(ws[1], widths):
        cell.fill = hdr_fill
        cell.font = hdr_font
        cell.alignment = Alignment(horizontal="center")
        ws.column_dimensions[cell.column_letter].width = w

    for idx, lv in enumerate(leaves, 1):
        s_date = date.fromisoformat(lv["start_date"])
        e_date = date.fromisoformat(lv["end_date"])
        days   = _period_days(s_date, e_date, all_lich, lv["leave_type"])
        gd_name = ""
        if lv["gd_name"]:
            gd_name = lv["gd_name"]
            if lv["gd_role"] == "pho_giam_doc":
                gd_name += " (TUQ)"
        created = lv["created_at"] or ""
        try:
            from datetime import datetime as _dt
            created = _dt.fromisoformat(str(created)).strftime("%d/%m/%Y")
        except Exception:
            pass
        # Ngày nghỉ: liệt kê từng ngày nếu không liên nhau
        import json as _j
        if lv["spread_dates"]:
            try:
                spread = _j.loads(lv["spread_dates"])
                dates_str = ", ".join(date.fromisoformat(d).strftime("%d/%m/%Y") for d in sorted(spread))
            except Exception:
                dates_str = s_date.strftime("%d/%m/%Y")
        else:
            dates_str = f"{s_date.strftime('%d/%m/%Y')} → {e_date.strftime('%d/%m/%Y')}"

        row_data = [
            idx,
            lv["staff_name"] or "",
            lv["dept_name"] or "",
            LEAVE_TYPE_LABELS.get(lv["leave_type"] or "", ""),
            dates_str,
            days,
            _LEAVE_STATUS_VN.get(lv["status"] or "", lv["status"] or ""),
            lv["ksv_name"] or "",
            lv["th_name"]  or "",
            gd_name,
            created,
        ]
        ws.append(row_data)
        # Wrap text cho cột Ngày nghỉ (cột E = index 5)
        ws.cell(ws.max_row, 5).alignment = Alignment(wrap_text=True, horizontal="left")

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename*=UTF-8''danh_sach_nghi_phep.xlsx"},
    )


# ─── Thông báo carry-over hết hiệu lực sau Q1 ──────────────────────────────────
# Phải khai báo TRƯỚC "/{leave_id}" bên dưới — nếu không, FastAPI/Starlette sẽ
# khớp "/carryover-notice" vào route "/{leave_id}" trước (cùng 1 segment, cùng
# method GET) rồi báo lỗi 422 khi ép kiểu int, route đúng bên dưới không bao
# giờ được gọi tới.

_CARRYOVER_NOTICE_CUTOFF = (3, 31)  # hết Q1 (31/3)


@router.get("/carryover-notice")
def get_carryover_notice(
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(get_current_staff),
):
    """Có cần hiện popup thông báo carry-over hết hiệu lực không — 1 lần/năm/user,
    hiện cho mọi user (không phân biệt có carry-over hay không) kể từ sau 31/3."""
    today = _vn_now().date()
    year  = today.year
    cutoff = date(year, *_CARRYOVER_NOTICE_CUTOFF)
    if today <= cutoff:
        return {"show": False}
    row = db.execute(
        "SELECT carryover_notice_year FROM user_tttt WHERE id=?", (current["id"],)
    ).fetchone()
    already_seen = bool(row and row["carryover_notice_year"] == year)
    return {"show": not already_seen, "year": year}


@router.post("/carryover-notice/ack")
def ack_carryover_notice(
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(get_current_staff),
):
    """Đánh dấu user đã xem thông báo carry-over hết hiệu lực trong năm nay."""
    year = _vn_now().date().year
    db.execute(
        "UPDATE user_tttt SET carryover_notice_year=? WHERE id=?", (year, current["id"]),
    )
    db.commit()
    return {"ok": True}


_OVERDUE_PENDING_LEVEL_VN = {
    "pending_ksv": "KSV", "pending_tong_hop": "Phòng Tổng hợp", "pending_gd": "Ban lãnh đạo",
}


@router.get("/overdue-pending-notice")
def get_overdue_pending_notice(
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(get_current_staff),
):
    """Đơn nghỉ phép CỦA CHÍNH user này đã tới/qua ngày nghỉ mà vẫn còn ở trạng
    thái chờ duyệt (KSV/Tổng hợp/Ban lãnh đạo) — nhắc họ theo dõi/thúc duyệt.
    Hiện lại mỗi lần mở trang trong khi vẫn còn đơn thoả điều kiện (không phải
    thông báo 1 lần/năm như carryover-notice — vấn đề còn tồn tại là còn nhắc)."""
    today = _vn_now().date()
    rows = db.execute(
        """SELECT id, start_date, end_date, spread_dates, status FROM leave_records
           WHERE staff_id=? AND status IN ('pending_ksv','pending_tong_hop','pending_gd')
             AND start_date <= ?""",
        (current["id"], today.isoformat()),
    ).fetchall()
    items = []
    for r in rows:
        if r["spread_dates"]:
            overdue = sorted(d for d in json.loads(r["spread_dates"]) if date.fromisoformat(d) <= today)
            if not overdue:
                continue
            date_label = ", ".join(date.fromisoformat(d).strftime("%d/%m/%Y") for d in overdue)
        else:
            date_label = date.fromisoformat(r["start_date"]).strftime("%d/%m/%Y")
        items.append({
            "id": r["id"],
            "date_label": date_label,
            "level": _OVERDUE_PENDING_LEVEL_VN.get(r["status"], r["status"]),
        })
    return {"show": bool(items), "items": items}


@router.get("/my-balance")
def get_my_balance(
    year: int = None,
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(get_current_staff),
):
    """Hạn mức phép của CHÍNH người đang đăng nhập — dùng cho banner "Phép còn lại"
    ở đầu trang. Khác với get_quotas (yêu cầu quyền leaves.quota_admin, xem toàn bộ
    nhân viên), endpoint này ai đăng nhập cũng gọi được nhưng chỉ trả về đúng 1
    người (current["id"]) — tái dùng cùng công thức (override trong leave_quotas
    + carry-over + used) để không lệch với tab Hạn mức phép.

    Đặt TRƯỚC /{leave_id} — nếu không, FastAPI khớp "/my-balance" vào path param
    leave_id (giống lý do staff.py đặt /export trước /{staff_id})."""
    from datetime import date as _today_d
    yr = year or _today_d.today().year
    staff_id = current["id"]

    q = db.execute(
        "SELECT quota_days FROM leave_quotas WHERE year=? AND staff_id=?", (yr, staff_id)
    ).fetchone()
    quota = float(q["quota_days"]) if q else float(compute_annual_leave(current.get("join_industry_date"), yr))
    carry = _carry_over_bulk([staff_id], yr, db, effective=True).get(staff_id, 0.0)
    used  = _calc_used_days_bulk([staff_id], yr, db, include_pending=True).get(staff_id, 0.0)

    return {
        "year":        yr,
        "quota_days":  quota,
        "carry_over":  carry,
        "used_days":   used,
        "remaining":   max(0.0, quota + carry - used),
    }


@router.get("/{leave_id}")
def get_leave(
    leave_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(get_current_staff),
):
    r = db.execute("SELECT * FROM leave_records WHERE id = ?", (leave_id,)).fetchone()
    if not r:
        raise HTTPException(404, "Không tìm thấy đơn nghỉ phép")
    is_th = _is_tong_hop_staff(current, db)
    if (r["staff_id"] != current["id"]
            and r["ksv_approver_id"] != current["id"]
            and r["tong_hop_approver_id"] != current["id"]
            and r["gd_approver_id"] != current["id"]
            and r["direct_by"] != current["id"]
            and not is_th
            and current["role"] not in ("admin", "giam_doc", "pho_giam_doc")):
        raise HTTPException(403, "Không có quyền xem đơn này")
    return _leave_to_out(leave_id, db)


@router.delete("/{leave_id}")
def delete_leave(
    leave_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(get_current_staff),
):
    """Xóa đơn khai báo hộ — chỉ người khai báo hoặc admin mới được xóa."""
    leave = db.execute("SELECT * FROM leave_records WHERE id = ?", (leave_id,)).fetchone()
    if not leave:
        raise HTTPException(404, "Không tìm thấy đơn")
    if not leave["is_direct"]:
        raise HTTPException(403, "Chỉ có thể xóa đơn khai báo hộ")
    if leave["direct_by"] != current["id"] and current["role"] != "admin":
        raise HTTPException(403, "Không có quyền xóa đơn này")
    # Hoàn trả used_leave_days nếu đơn đã approved và không phải loại miễn quota
    if leave["status"] == "approved" and not _is_no_quota_row(leave["leave_type"], leave["other_deduct_quota"]):
        if leave["spread_dates"]:
            days = len(json.loads(leave["spread_dates"]))
        else:
            from datetime import date as _d
            s = _d.fromisoformat(leave["start_date"])
            e = _d.fromisoformat(leave["end_date"])
            _lich = _load_lich(db, s, e)
            days = calculate_leave_days(s, e, _lich)
        db.execute(
            "UPDATE user_tttt SET used_leave_days = MAX(0, COALESCE(used_leave_days,0) - ?) WHERE id = ?",
            (days, leave["staff_id"]),
        )
    db.execute("DELETE FROM leave_action_logs WHERE leave_id = ?", (leave_id,))
    db.execute("DELETE FROM leave_records WHERE id = ?", (leave_id,))
    db.commit()
    return {"message": "Đã xóa đơn khai báo hộ"}


@router.put("/{leave_id}/ksv-review")
def ksv_review(
    leave_id: int,
    body: LeaveReview,
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(require_feature("leaves.approve_ksv")),
):
    leave = db.execute("SELECT * FROM leave_records WHERE id = ?", (leave_id,)).fetchone()
    if not leave:
        raise HTTPException(404, "Không tìm thấy đơn nghỉ phép")
    if leave["status"] != LeaveStatus.PENDING_KSV:
        raise HTTPException(400, f"Đơn đang ở trạng thái '{leave['status']}'")
    if (leave["ksv_approver_id"] != current["id"] and current["role"] != "admin"
            and not _is_alt_ksv(current, leave["staff_id"], db)):
        raise HTTPException(403, "Bạn không phải người được chỉ định duyệt bước này")
    if body.action == "reject" and not body.comment:
        raise HTTPException(400, "Vui lòng nhập lý do từ chối")

    old = leave["status"]
    new_status = LeaveStatus.PENDING_TONG_HOP if body.action == "approve" else LeaveStatus.REJECTED
    # Nếu admin hoặc KSV thay thế cùng phòng thực hiện: ghi lại đúng người vừa
    # duyệt (không phải người được chỉ định ban đầu), xem _is_alt_ksv.
    if leave["ksv_approver_id"] != current["id"]:
        db.execute("UPDATE leave_records SET ksv_approver_id=? WHERE id=?", (current["id"], leave_id))
    db.execute(
        "UPDATE leave_records SET ksv_approved_at=?, ksv_comment=? WHERE id=?",
        (str(_vn_now()), body.comment, leave_id),
    )
    if body.action == "approve" and body.signature:
        _save_signature(db, leave_id, "ksv", current["id"], body.signature)
    start = date.fromisoformat(leave["start_date"])
    end   = date.fromisoformat(leave["end_date"])
    _lich = _load_lich(db, start, end)
    _apply_status_transition(leave_id, old, new_status, start, end, leave["staff_id"], _lich, db)
    _log_action(db, leave_id, current["id"],
                "ksv_approve" if body.action == "approve" else "ksv_reject",
                body.comment, old, new_status)
    db.commit()
    return _leave_to_out(leave_id, db)


@router.post("/{leave_id}/tong-hop-review")
def tong_hop_review(
    leave_id: int,
    body: TongHopReview,
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(get_current_staff),
):
    if not _is_tong_hop_staff(current, db) and current["role"] != "admin":
        raise HTTPException(403, "Chỉ nhân viên Phòng Tổng hợp hoặc Admin mới thực hiện được")
    leave = db.execute("SELECT * FROM leave_records WHERE id = ?", (leave_id,)).fetchone()
    if not leave:
        raise HTTPException(404, "Không tìm thấy đơn nghỉ phép")
    # [TẠM TẮT theo yêu cầu 2026-07-18 — bật lại khi được báo] Chặn tự xử lý đơn
    # của chính mình ở bước Tổng hợp — hiện cho phép Phòng Tổng hợp duyệt tất cả
    # đơn kể cả đơn của họ để test luồng duyệt trung tâm.
    # if leave["staff_id"] == current["id"] and current["role"] != "admin":
    #     raise HTTPException(403, "Không thể tự xử lý đơn nghỉ phép của chính mình")
    if leave["status"] != LeaveStatus.PENDING_TONG_HOP:
        raise HTTPException(400, f"Đơn đang ở trạng thái '{leave['status']}'")
    if leave["recall_reason"]:
        raise HTTPException(400, "Đây là yêu cầu rút đơn — dùng /recall-approve để xử lý")
    if body.action == "reject" and not body.comment:
        raise HTTPException(400, "Vui lòng nhập lý do từ chối")

    old = leave["status"]
    db.execute(
        "UPDATE leave_records SET tong_hop_approver_id=?, tong_hop_approved_at=?, tong_hop_comment=? WHERE id=?",
        (current["id"], str(_vn_now()), body.comment, leave_id),
    )

    if body.action == "forward":
        if not body.gd_approver_id:
            raise HTTPException(400, "Vui lòng chọn GĐ/PGĐ phê duyệt")
        gd = db.execute("SELECT * FROM user_tttt WHERE id = ? AND is_active = 1", (body.gd_approver_id,)).fetchone()
        if not gd or gd["role"] not in ("giam_doc", "pho_giam_doc"):
            raise HTTPException(400, "Người được chọn không phải GĐ hoặc PGĐ")
        db.execute("UPDATE leave_records SET gd_approver_id=? WHERE id=?", (body.gd_approver_id, leave_id))
        new_status = LeaveStatus.PENDING_GD
        action_key = "th_forward"
    else:
        new_status = LeaveStatus.REJECTED
        action_key = "th_reject"

    start = date.fromisoformat(leave["start_date"])
    end   = date.fromisoformat(leave["end_date"])
    _lich = _load_lich(db, start, end)
    _apply_status_transition(leave_id, old, new_status, start, end, leave["staff_id"], _lich, db)
    _log_action(db, leave_id, current["id"], action_key, body.comment, old, new_status)
    db.commit()
    return _leave_to_out(leave_id, db)


@router.put("/{leave_id}/tong-hop-ack")
def tong_hop_ack_gd_leave(
    leave_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(get_current_staff),
):
    """Tổng hợp xác nhận ĐÃ BIẾT đơn của Giám đốc — chỉ mang tính thông báo/ghi nhận,
    không phải điều kiện duyệt (đơn GĐ đã tự động approved ngay khi tạo)."""
    if not _is_tong_hop_staff(current, db) and current["role"] != "admin":
        raise HTTPException(403, "Chỉ Phòng Tổng hợp hoặc Admin mới xác nhận được")
    leave = db.execute("SELECT * FROM leave_records WHERE id=?", (leave_id,)).fetchone()
    if not leave:
        raise HTTPException(404, "Không tìm thấy đơn")
    staff = db.execute("SELECT role FROM user_tttt WHERE id=?", (leave["staff_id"],)).fetchone()
    if not staff or staff["role"] != "giam_doc":
        raise HTTPException(400, "Chỉ áp dụng cho đơn nghỉ phép của Giám đốc")
    if leave["tong_hop_approver_id"]:
        raise HTTPException(400, "Đơn đã được Tổng hợp xác nhận trước đó")

    db.execute(
        "UPDATE leave_records SET tong_hop_approver_id=?, tong_hop_approved_at=? WHERE id=?",
        (current["id"], str(_vn_now()), leave_id),
    )
    _log_action(db, leave_id, current["id"], "th_ack_gd", None, leave["status"], leave["status"])
    db.commit()
    return _leave_to_out(leave_id, db)


@router.put("/{leave_id}/gd-review")
def gd_review(
    leave_id: int,
    body: LeaveReview,
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(require_feature("leaves.approve_gd")),
):
    leave = db.execute("SELECT * FROM leave_records WHERE id = ?", (leave_id,)).fetchone()
    if not leave:
        raise HTTPException(404, "Không tìm thấy đơn nghỉ phép")
    if leave["status"] != LeaveStatus.PENDING_GD:
        raise HTTPException(400, f"Đơn đang ở trạng thái '{leave['status']}'")
    if leave["staff_id"] == current["id"] and current["role"] != "admin":
        raise HTTPException(403, "Không thể tự duyệt đơn nghỉ phép của chính mình")
    if current["role"] != "admin":
        if not _can_gd_review(current, db):
            raise HTTPException(403, "Phó Giám đốc chưa được ủy quyền phê duyệt")
        if leave["gd_approver_id"] != current["id"]:
            raise HTTPException(403, "Bạn không phải người được chỉ định duyệt bước này")
    if body.action == "reject" and not body.comment:
        raise HTTPException(400, "Vui lòng nhập lý do từ chối")

    old = leave["status"]
    new_status = LeaveStatus.APPROVED if body.action == "approve" else LeaveStatus.REJECTED
    db.execute(
        "UPDATE leave_records SET gd_approved_at=?, gd_comment=?, gd_approver_id=? WHERE id=?",
        (str(_vn_now()), body.comment, current["id"], leave_id),
    )
    if body.action == "approve" and body.signature:
        _save_signature(db, leave_id, "gd", current["id"], body.signature)
    start = date.fromisoformat(leave["start_date"])
    end   = date.fromisoformat(leave["end_date"])
    _lich = _load_lich(db, start, end)
    _apply_status_transition(leave_id, old, new_status, start, end, leave["staff_id"], _lich, db)
    _log_action(db, leave_id, current["id"],
                "gd_approve" if body.action == "approve" else "gd_reject",
                body.comment, old, new_status)
    if new_status == LeaveStatus.APPROVED and leave["adjusts_leave_id"]:
        _cancel_adjusted_original(leave["adjusts_leave_id"], current["id"], db)
    db.commit()
    return _leave_to_out(leave_id, db)


@router.put("/{leave_id}/resubmit")
def resubmit_leave(
    leave_id: int,
    body: LeaveCreate,
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(require_feature("leaves.resubmit")),
):
    leave = db.execute("SELECT * FROM leave_records WHERE id = ?", (leave_id,)).fetchone()
    if not leave:
        raise HTTPException(404, "Không tìm thấy đơn nghỉ phép")
    if leave["staff_id"] != current["id"]:
        raise HTTPException(403, "Chỉ chủ nhân đơn mới được nộp lại")
    if leave["status"] != LeaveStatus.REJECTED:
        raise HTTPException(400, "Chỉ có thể nộp lại đơn đã bị từ chối")

    if body.spread_dates:
        spread = sorted(set(body.spread_dates))
        if len(spread) < 1:
            raise HTTPException(400, "spread_dates phải có ít nhất 1 ngày")
        try:
            eff_start  = date.fromisoformat(spread[0])
            eff_end    = date.fromisoformat(spread[-1])
        except ValueError:
            raise HTTPException(400, "Định dạng ngày không hợp lệ (yêu cầu YYYY-MM-DD)")
        leave_days = len(spread)
        spread_json = json.dumps(spread)
        _lich = _load_lich(db, eff_start, eff_end)
    else:
        if body.end_date < body.start_date:
            raise HTTPException(400, "Ngày kết thúc phải sau ngày bắt đầu")
        eff_start   = body.start_date
        eff_end     = body.end_date
        _lich = _load_lich(db, eff_start, eff_end)
        leave_days = _period_days(eff_start, eff_end, _lich, body.leave_type)
        spread_json = None

    # leave["status"] lúc vào hàm luôn là REJECTED (chặn ở trên) nên không cần
    # exclude_id — _calc_used_days trong _check_quota_or_borrow không đếm đơn
    # rejected.
    borrow_days = _check_quota_or_borrow(
        current["id"], current.get("join_industry_date"), body.leave_type,
        leave_days, eff_start.year, body.confirm_borrow_next_year, db,
        eff_start=eff_start, other_deduct_quota=body.other_deduct_quota,
    )

    # Kiểm tra trùng ngày theo spread_dates thực tế
    if body.spread_dates:
        _existing = db.execute(
            """SELECT start_date, end_date, spread_dates FROM leave_records
               WHERE staff_id=? AND id!=? AND status NOT IN ('rejected','cancelled')
                 AND (reason IS NULL OR NOT (reason LIKE '[Import]%' OR reason LIKE '[Điều chỉnh]%'))""",
            (current["id"], leave_id)
        ).fetchall()
        _new_days = set(spread)
        for _el in _existing:
            if _el["spread_dates"]:
                if _new_days & set(json.loads(_el["spread_dates"])):
                    raise HTTPException(409, "Khoảng ngày nghỉ bị trùng với đơn hiện có")
            elif any(_el["start_date"] <= d <= _el["end_date"] for d in spread):
                raise HTTPException(409, "Khoảng ngày nghỉ bị trùng với đơn hiện có")
    else:
        _existing2 = db.execute(
            """SELECT start_date, end_date, spread_dates FROM leave_records
               WHERE staff_id=? AND id!=? AND status NOT IN ('rejected','cancelled')
                 AND (reason IS NULL OR NOT (reason LIKE '[Import]%' OR reason LIKE '[Điều chỉnh]%'))
                 AND start_date<=? AND end_date>=?""",
            (current["id"], leave_id, eff_end.isoformat(), eff_start.isoformat())
        ).fetchall()
        if _existing2:
            _new_range_days = None
            for _el in _existing2:
                if _el["spread_dates"]:
                    if _new_range_days is None:
                        _new_range_days, _d = set(), eff_start
                        while _d <= eff_end:
                            _new_range_days.add(_d.isoformat())
                            _d += timedelta(days=1)
                    if set(json.loads(_el["spread_dates"])) & _new_range_days:
                        raise HTTPException(409, "Khoảng ngày nghỉ bị trùng với đơn hiện có")
                else:
                    raise HTTPException(409, "Khoảng ngày nghỉ bị trùng với đơn hiện có")

    if current["role"] == "giam_doc":
        # GĐ là cấp cao nhất — tự duyệt ngay, không qua quy trình (nhất quán với create_leave)
        new_status      = LeaveStatus.APPROVED
        ksv_approver_id = None
    elif current["role"] in _HIGH_ROLES:
        new_status      = LeaveStatus.PENDING_TONG_HOP
        ksv_approver_id = None
    else:
        ksv = _validate_ksv(body.ksv_approver_id, current, db)
        new_status      = LeaveStatus.PENDING_KSV
        ksv_approver_id = ksv["id"]

    # Validate và lưu GĐ/PGĐ approver nếu người dùng chọn
    new_gd_approver_id = None
    new_gd_approved_at = None
    if current["role"] == "giam_doc":
        new_gd_approver_id = current["id"]
        new_gd_approved_at = str(_vn_now())
    elif body.gd_approver_id:
        gd_row = db.execute(
            "SELECT id FROM user_tttt WHERE id=? AND role IN ('giam_doc','pho_giam_doc') AND is_active=1",
            (body.gd_approver_id,)
        ).fetchone()
        if gd_row:
            new_gd_approver_id = gd_row["id"]

    old = leave["status"]
    _log_action(db, leave_id, current["id"], "resubmit", None, old, new_status)

    db.execute(
        """UPDATE leave_records SET
               ksv_approver_id=?, ksv_approved_at=NULL, ksv_comment=NULL,
               tong_hop_approver_id=NULL, tong_hop_approved_at=NULL, tong_hop_comment=NULL,
               gd_approver_id=?, gd_approved_at=?, gd_comment=NULL,
               leave_type=?, start_date=?, end_date=?, reason=?, spread_dates=?,
               borrow_next_year_days=?, other_deduct_quota=?
           WHERE id=?""",
        (ksv_approver_id, new_gd_approver_id, new_gd_approved_at, body.leave_type, eff_start.isoformat(),
         eff_end.isoformat(), body.reason, spread_json, borrow_days, int(body.other_deduct_quota), leave_id),
    )
    # Đơn quay lại từ đầu → chữ ký của người duyệt cũ không còn giá trị. Ngày tháng
    # và số ngày phép trên phiếu đã đổi, giữ lại là để chữ ký thật nằm trên tờ đơn khác.
    db.execute("DELETE FROM leave_signatures WHERE leave_id=? AND slot IN ('ksv','gd')", (leave_id,))
    if body.signature:
        _save_signature(db, leave_id, "nguoi_de_nghi", current["id"], body.signature)
    _apply_status_transition(leave_id, old, new_status, eff_start, eff_end, leave["staff_id"], _lich, db)
    db.commit()
    return _leave_to_out(leave_id, db)


@router.patch("/{leave_id}/cancel")
def cancel_leave(
    leave_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(get_current_staff),
):
    leave = db.execute("SELECT * FROM leave_records WHERE id = ?", (leave_id,)).fetchone()
    if not leave:
        raise HTTPException(404, "Không tìm thấy đơn nghỉ phép")
    if leave["staff_id"] != current["id"] and current["role"] != "admin":
        raise HTTPException(403, "Chỉ chủ nhân đơn hoặc Admin mới được hủy")
    if leave["status"] == LeaveStatus.CANCELLED:
        raise HTTPException(400, "Đơn đã được hủy trước đó")
    if leave["recall_reason"] and current["role"] != "admin":
        raise HTTPException(
            400,
            "Đơn đang chờ Phòng Tổng hợp xác nhận rút — dùng chức năng xác nhận rút đơn để xử lý",
        )
    # Hủy thẳng đơn đã approved (bỏ qua luồng Rút đơn/Recall) chỉ dành cho:
    # GĐ tự hủy đơn của chính mình (toàn quyền), hoặc người có quyền
    # "leaves.cancel" được cấp riêng — khớp đúng điều kiện hiện nút ở frontend
    # (_can_cancel_now). Người khác phải dùng /recall cho đơn đã duyệt.
    if leave["status"] == LeaveStatus.APPROVED and current["role"] != "admin":
        _is_gd_self = current["role"] == "giam_doc" and leave["staff_id"] == current["id"]
        _has_cancel_feature = db.execute(
            """SELECT 1 FROM group_features gf
               JOIN group_members gm ON gm.group_id = gf.group_id
               JOIN user_groups g ON g.id = gm.group_id AND g.is_active = 1
               WHERE gm.staff_id = ? AND gf.feature_code = 'leaves.cancel'
               LIMIT 1""",
            (current["id"],),
        ).fetchone() is not None
        if not (_is_gd_self or _has_cancel_feature):
            raise HTTPException(
                403,
                "Đơn đã duyệt — vui lòng dùng chức năng Rút đơn (cần Phòng Tổng hợp xác nhận)",
            )

    old   = leave["status"]
    start = date.fromisoformat(leave["start_date"])
    end   = date.fromisoformat(leave["end_date"])
    _lich = _load_lich(db, start, end)
    _apply_status_transition(leave_id, old, LeaveStatus.CANCELLED, start, end, leave["staff_id"], _lich, db,
                             actor_id=current["id"])
    _log_action(db, leave_id, current["id"], "cancel", None, old, LeaveStatus.CANCELLED)
    db.commit()
    return _leave_to_out(leave_id, db)


@router.get("/{leave_id}/history")
def get_leave_history(
    leave_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(get_current_staff),
):
    leave = db.execute("SELECT * FROM leave_records WHERE id = ?", (leave_id,)).fetchone()
    if not leave:
        raise HTTPException(404, "Không tìm thấy đơn nghỉ phép")
    is_th = _is_tong_hop_staff(current, db)
    if (leave["staff_id"] != current["id"]
            and leave["ksv_approver_id"] != current["id"]
            and leave["gd_approver_id"] != current["id"]
            and leave["direct_by"] != current["id"]
            and not is_th
            and current["role"] not in ("admin", "giam_doc", "pho_giam_doc")):
        raise HTTPException(403)

    logs = db.execute(
        """SELECT lal.*, ks.full_name AS actor_name
           FROM leave_action_logs lal
           LEFT JOIN user_tttt ks ON lal.actor_id = ks.id
           WHERE lal.leave_id = ? ORDER BY lal.created_at""",
        (leave_id,),
    ).fetchall()

    return [
        {
            "id":           log["id"],
            "actor_name":   log["actor_name"] or "",
            "action":       log["action"],
            "action_label": ACTION_LABELS.get(log["action"], (log["action"], "grey"))[0],
            "action_color": ACTION_LABELS.get(log["action"], (log["action"], "grey"))[1],
            "comment":      log["comment"],
            "from_status":  log["from_status"],
            "to_status":    log["to_status"],
            "created_at":   log["created_at"],
        }
        for log in logs
    ]


# ─── Word template download ──────────────────────────────────────────────────

_ROLE_VN = {
    "chuyen_vien":   "Chuyên viên",
    "pho_phong":     "Phó phòng",
    "truong_phong":  "Trưởng phòng",
    "hau_kiem_vien": "Hậu kiểm viên",
    "giam_doc":      "Giám đốc",
    "pho_giam_doc":  "Phó Giám đốc",
    "admin":         "Quản trị viên cấp 1",
    "admin_l2":      "Quản trị viên cấp 2",
}

# template_path() chứ không phải os.path.join(): tên thư mục có dấu trên đĩa đang
# ở dạng NFD, ghép chuỗi NFC từ mã nguồn sẽ không khớp — xem backend/core/paths.py
_TPL_DIR = template_path("Phòng Tổng hợp", "Nghỉ phép")
_TPL_PATH = template_path("don_xin_nghi_phep_tpl.docx")
# Mẫu 1 TCNS — "ĐƠN ĐĂNG KÝ ĐIỀU CHỈNH THỜI GIAN NGHỈ PHÉP BẮT BUỘC", dùng
# riêng cho đơn có adjusts_leave_id (xem _build_form_ctx, npbb_adjust_leave).
_NPBB_ADJUST_TPL_PATH = template_path("don_dieu_chinh_npbb_tpl.docx")
# Mẫu 1 TCNS — "ĐƠN ĐĂNG KÝ THỜI GIAN NGHỈ PHÉP BẮT BUỘC", dùng cho đơn nghỉ
# phép bắt buộc MỚI (chưa từng điều chỉnh) — leave_type == "bat_buoc" và
# adjusts_leave_id rỗng, xem _build_form_ctx.
_NPBB_REGISTER_TPL_PATH = template_path("don_dang_ky_npbb_tpl.docx")

def _pick_template(staff_role: str) -> str:
    """Chọn file docx theo role. Fallback về template gốc nếu chưa có."""
    _map = {
        "chuyen_vien":   "don_xin_nghi_phep_nv.docx",
        "pho_phong":     "don_xin_nghi_phep_tp.docx",
        "truong_phong":  "don_xin_nghi_phep_tp.docx",
        "giam_doc":      "don_xin_nghi_phep_gd.docx",
        "pho_giam_doc":  "don_xin_nghi_phep_pgd.docx",
        "hau_kiem_vien": "don_xin_nghi_phep_nv.docx",
        "admin":         "don_xin_nghi_phep_tp.docx",
    }
    fname = _map.get(staff_role or "", "don_xin_nghi_phep_tp.docx")
    path  = os.path.join(_TPL_DIR, fname)
    return path if os.path.exists(path) else _TPL_PATH


def _is_business_contiguous(sorted_dates: list, lich: LichLamViec = LICH_RONG) -> bool:
    """True nếu các ngày liền nhau, hoặc khoảng cách giữa 2 ngày kế tiếp chỉ
    toàn ngày nghỉ (nghỉ hết tuần rồi nghỉ tiếp tuần sau) — coi như 1 khoảng
    liên tục để ghi gọn "Từ ngày...đến hết ngày..." thay vì liệt kê từng ngày.

    Thứ Bảy đi làm bù nằm trong khoảng trống thì KHÔNG gộp: hôm đó người ta đi
    làm, ghi "từ ngày ... đến hết ngày ..." trên đơn in là khai họ nghỉ cả một
    ngày làm việc mà thực tế họ có mặt."""
    for prev, cur in zip(sorted_dates, sorted_dates[1:]):
        gap = (cur - prev).days
        if gap == 1:
            continue
        if gap > 1 and all(
            not la_ngay_lam_viec(prev + timedelta(days=i), lich)
            for i in range(1, gap)
        ):
            continue
        return False
    return True


def _fmt_leave_period(start: date, end: date, days: int, spread_dates: list = None,
                      lich: LichLamViec = LICH_RONG) -> str:
    if spread_dates and len(spread_dates) > 1:
        parsed = sorted(date.fromisoformat(d) for d in spread_dates)
        if _is_business_contiguous(parsed, lich):
            # Liền nhau (hoặc chỉ cách bởi T7/CN) — ghi gọn thành 1 khoảng.
            return (
                f"{days:02d} ngày "
                f"(Từ ngày {parsed[0].strftime('%d/%m/%Y')} đến hết ngày {parsed[-1].strftime('%d/%m/%Y')})"
            )
        # Ngày lẻ không liên tục — liệt kê đủ từng ngày, không ghi "Từ...đến..."
        # (dễ hiểu lầm là nghỉ liên tục cả khoảng min→max).
        dates_str = ", ".join(d.strftime("%d/%m/%Y") for d in parsed)
        return f"{days:02d} ngày (các ngày: {dates_str})"
    if days == 1:
        return f"{days:02d} ngày (ngày {start.day:02d} tháng {start.month:02d} năm {start.year})"
    return (
        f"{days:02d} ngày "
        f"(Từ ngày {start.strftime('%d/%m/%Y')} đến ngày {end.strftime('%d/%m/%Y')})"
    )


_FORM_ROW_SQL = """SELECT lr.*,
          s.full_name AS staff_name, s.role AS staff_role,
          s.employee_code, s.annual_leave_days, s.used_leave_days,
          s.join_industry_date,
          d.name AS dept_name,
          kv.full_name AS ksv_name,
          gd.full_name AS gd_approver_name, gd.role AS gd_role
   FROM leave_records lr
   LEFT JOIN user_tttt s  ON lr.staff_id             = s.id
   LEFT JOIN departments d ON s.department_id          = d.id
   LEFT JOIN user_tttt kv ON lr.ksv_approver_id      = kv.id
   LEFT JOIN user_tttt gd ON lr.gd_approver_id       = gd.id
   WHERE lr.id = ?"""


def _load_form_row(leave_id: int, db: sqlite3.Connection):
    r = db.execute(_FORM_ROW_SQL, (leave_id,)).fetchone()
    if not r:
        raise HTTPException(404, "Không tìm thấy đơn nghỉ phép")
    return r


def _can_view_form(r, current: dict, db: sqlite3.Connection) -> bool:
    return (r["staff_id"] == current["id"]
            or r["ksv_approver_id"] == current["id"]
            or r["gd_approver_id"] == current["id"]
            or r["direct_by"] == current["id"]
            or _is_tong_hop_staff(current, db)
            or current["role"] in ("admin", "giam_doc", "pho_giam_doc")
            # Trưởng/Phó phòng cùng phòng — được xem/duyệt THAY bước KSV nếu
            # người được chỉ định vắng mặt, xem _is_alt_ksv.
            or (r["status"] == LeaveStatus.PENDING_KSV and _is_alt_ksv(current, r["staff_id"], db)))


def _draft_form_row(body: LeaveCreate, current: dict, db: sqlite3.Connection) -> dict:
    """Dòng dữ liệu giả lập cho đơn CHƯA tạo — để xem trước trước khi gửi.

    Giữ đúng bộ khoá mà _build_form_ctx đọc; đơn thật thì các khoá này do câu
    SELECT ở _FORM_ROW_SQL cấp.
    """
    s = db.execute(
        """SELECT s.*, d.name AS dept_name
           FROM user_tttt s LEFT JOIN departments d ON s.department_id = d.id
           WHERE s.id = ?""",
        (current["id"],),
    ).fetchone()
    if not s:
        raise HTTPException(404, "Không tìm thấy hồ sơ nhân sự của bạn")

    def _name_role(sid):
        if not sid:
            return None, None
        row = db.execute("SELECT full_name, role FROM user_tttt WHERE id=?", (sid,)).fetchone()
        return (row["full_name"], row["role"]) if row else (None, None)

    ksv_name, _ = _name_role(body.ksv_approver_id)
    gd_name, gd_role = _name_role(body.gd_approver_id)
    if body.spread_dates:
        spread = sorted(set(body.spread_dates))
        eff_start, eff_end = spread[0], spread[-1]
        spread_json = json.dumps(spread)
    else:
        eff_start, eff_end = body.start_date.isoformat(), body.end_date.isoformat()
        spread_json = None
    return {
        "staff_id": current["id"], "staff_name": s["full_name"], "staff_role": s["role"],
        "employee_code": s["employee_code"], "annual_leave_days": s["annual_leave_days"],
        "used_leave_days": s["used_leave_days"], "join_industry_date": s["join_industry_date"],
        "dept_name": s["dept_name"], "direct_by": None,
        "start_date": eff_start, "end_date": eff_end, "spread_dates": spread_json,
        "leave_type": body.leave_type, "reason": body.reason,
        "ksv_approver_id": body.ksv_approver_id, "ksv_name": ksv_name,
        "gd_approver_id": body.gd_approver_id, "gd_approver_name": gd_name, "gd_role": gd_role,
        # Luồng xem trước (POST /preview) chỉ dùng cho tạo đơn thường — điều
        # chỉnh NPBB (npbb_adjust_leave) không đi qua bước xem trước này nên
        # dòng giả lập không bao giờ là đơn điều chỉnh, xem _build_form_ctx.
        "adjusts_leave_id": None,
        # Đơn chưa tạo — chưa thể biết có phải ứng phép năm sau không (chỉ xác
        # định lúc gửi thật, xem _check_quota_or_borrow), luôn coi như 0 ở đây.
        "borrow_next_year_days": 0,
        "other_deduct_quota": body.other_deduct_quota,
    }


def _npbb_ksv_block(r, db: sqlite3.Connection) -> tuple:
    """(ksv_sign, ksv_label) cho khối chữ ký "Trưởng phòng" trong 2 mẫu NPBB —
    ẩn hẳn khi người làm đơn không có KSV cấp trên (Trưởng phòng/GĐ/PGĐ tự làm
    đơn), y hệt điều kiện ksv_sign của đơn nghỉ phép thường ở _build_form_ctx.
    Nhãn TUQ. khi người duyệt hộ là Phó phòng — cùng logic ksv_dept_label ở
    đó, giữ 1 dòng cho khớp phong cách đã chốt của mẫu NPBB (khác mẫu đơn
    thường tách 2 dòng)."""
    dept_raw = r["dept_name"] or ""
    dept_short = dept_raw[6:] if dept_raw.upper().startswith("PHÒNG ") else dept_raw
    ksv_sign = r["staff_role"] not in ("truong_phong", "giam_doc", "pho_giam_doc")
    _ksv_role = None
    if r["ksv_approver_id"]:
        _ksv_r = db.execute("SELECT role FROM user_tttt WHERE id=?", (r["ksv_approver_id"],)).fetchone()
        _ksv_role = _ksv_r["role"] if _ksv_r else None
    ksv_label = f"TUQ. Trưởng phòng {dept_short}" if _ksv_role == "pho_phong" else f"Trưởng phòng {dept_short}"
    return ksv_sign, ksv_label


def _build_npbb_adjust_form_ctx(r, db: sqlite3.Connection) -> dict:
    """Ctx cho Mẫu 1 TCNS ("ĐƠN ĐĂNG KÝ ĐIỀU CHỈNH THỜI GIAN NGHỈ PHÉP BẮT
    BUỘC") — khác hẳn phiếu nghỉ phép thường, không có hạn mức/carry-over,
    chỉ so sánh ngày ĐÃ ĐĂNG KÝ (đơn gốc, tra qua adjusts_leave_id) với ngày
    ĐIỀU CHỈNH (chính đơn r, tạo bởi npbb_adjust_leave)."""
    start = date.fromisoformat(r["start_date"])
    end   = date.fromisoformat(r["end_date"])
    _lich = _load_lich(db, start, end)
    so_ngay_moi = len(json.loads(r["spread_dates"])) if r["spread_dates"] else _period_days(start, end, _lich, r["leave_type"])

    orig = db.execute(_FORM_ROW_SQL, (r["adjusts_leave_id"],)).fetchone()
    if orig:
        o_start = date.fromisoformat(orig["start_date"])
        o_end   = date.fromisoformat(orig["end_date"])
        o_lich  = _load_lich(db, o_start, o_end)
        so_ngay_goc  = len(json.loads(orig["spread_dates"])) if orig["spread_dates"] else _period_days(o_start, o_end, o_lich, orig["leave_type"])
        tu_ngay_goc  = o_start.strftime("%d/%m/%Y")
        den_ngay_goc = o_end.strftime("%d/%m/%Y")
    else:
        so_ngay_goc, tu_ngay_goc, den_ngay_goc = 0, "", ""

    dept_raw = r["dept_name"] or ""
    now = _vn_now()
    ksv_sign, ksv_label = _npbb_ksv_block(r, db)
    return {
        "ho_ten":             r["staff_name"] or "",
        "chuc_vu":            _ROLE_VN.get(r["staff_role"] or "", r["staff_role"] or ""),
        "don_vi_cong_tac":    f"{dept_raw} – Trung tâm Thanh toán" if dept_raw else "Trung tâm Thanh toán",
        # GĐ/PGĐ không thể "kính đề nghị" chính Giám đốc TTTT — đơn của diện
        # HĐTV kính gửi thẳng Ban Tổ chức Nhân sự (đối chiếu hồ sơ NPBB thật
        # "DIỆN HĐTV"); các cấp còn lại giữ nguyên đối tượng cũ.
        "doi_tuong":          "Ban Tổ chức Nhân sự" if r["staff_role"] in ("giam_doc", "pho_giam_doc") else "Giám đốc Trung tâm Thanh toán",
        "nam":                start.year,
        "so_ngay_goc":        f"{int(so_ngay_goc):02d}",
        "tu_ngay_goc":        tu_ngay_goc,
        "den_ngay_goc":       den_ngay_goc,
        "so_ngay_moi":        f"{int(so_ngay_moi):02d}",
        "tu_ngay_moi":        start.strftime("%d/%m/%Y"),
        "den_ngay_moi":       end.strftime("%d/%m/%Y"),
        "ngay_ky":            now.day, "thang_ky": now.month, "nam_ky": now.year,
        "ksv_sign":           ksv_sign,
        "ksv_label":          ksv_label,
        "truong_phong_name":  r["ksv_name"] or "",
        "nguoi_de_nghi_name": r["staff_name"] or "",
        "gd_name":            r["gd_approver_name"] or "",
    }


def _build_npbb_register_form_ctx(r, leave_id: Optional[int], db: sqlite3.Connection) -> dict:
    """Ctx cho Mẫu 1 TCNS ("ĐƠN ĐĂNG KÝ THỜI GIAN NGHỈ PHÉP BẮT BUỘC") — đơn
    nghỉ phép bắt buộc MỚI, chưa từng điều chỉnh: chỉ 1 khoảng ngày, không so
    sánh gốc/điều chỉnh như _build_npbb_adjust_form_ctx.

    bat_buoc KHÔNG bị miễn khỏi hạn mức phép năm — nó vẫn cộng vào
    used_leave_days/_calc_used_days (chỉ miễn bước CHẶN khi hết hạn mức, xem
    create_leave/_create_leave_core) — nên mẫu giấy vẫn phải hiện đúng tổng
    hạn mức và số đã nghỉ, khớp với mẫu thật (Tổng số ngày được hưởng / Đã
    nghỉ / Đăng ký)."""
    start = date.fromisoformat(r["start_date"])
    end   = date.fromisoformat(r["end_date"])
    _lich = _load_lich(db, start, end)
    so_ngay = len(json.loads(r["spread_dates"])) if r["spread_dates"] else _period_days(start, end, _lich, r["leave_type"])

    _q_row = db.execute(
        "SELECT quota_days FROM leave_quotas WHERE staff_id=? AND year=?",
        (r["staff_id"], start.year),
    ).fetchone()
    tong_ngay_phep = (
        float(_q_row["quota_days"]) if _q_row
        else (compute_annual_leave(r["join_industry_date"], start.year) if r["join_industry_date"] else (r["annual_leave_days"] or 12))
    )
    so_ngay_da_nghi = _calc_used_days(r["staff_id"], start.year, db, exclude_id=leave_id)

    dept_raw = r["dept_name"] or ""
    now = _vn_now()
    ksv_sign, ksv_label = _npbb_ksv_block(r, db)
    return {
        "ho_ten":             r["staff_name"] or "",
        "chuc_vu":            _ROLE_VN.get(r["staff_role"] or "", r["staff_role"] or ""),
        "don_vi_cong_tac":    f"{dept_raw} – Trung tâm Thanh toán" if dept_raw else "Trung tâm Thanh toán",
        # Xem chú thích trong _build_npbb_adjust_form_ctx.
        "doi_tuong":          "Ban Tổ chức Nhân sự" if r["staff_role"] in ("giam_doc", "pho_giam_doc") else "Giám đốc Trung tâm Thanh toán",
        "nam":                start.year,
        "tong_ngay_phep":     f"{tong_ngay_phep:.0f}",
        "so_ngay_da_nghi":    f"{so_ngay_da_nghi:.0f}",
        "so_ngay":            f"{int(so_ngay):02d}",
        "tu_ngay":            start.strftime("%d/%m/%Y"),
        "den_ngay":           end.strftime("%d/%m/%Y"),
        "ngay_ky":            now.day, "thang_ky": now.month, "nam_ky": now.year,
        "ksv_sign":           ksv_sign,
        "ksv_label":          ksv_label,
        "truong_phong_name":  r["ksv_name"] or "",
        "nguoi_de_nghi_name": r["staff_name"] or "",
        "gd_name":            r["gd_approver_name"] or "",
    }


def _build_form_ctx(r, leave_id: Optional[int], db: sqlite3.Connection) -> tuple:
    """(ctx cho docxtpl, đường dẫn template). `r` là dòng thật hoặc dòng giả lập."""
    if r["adjusts_leave_id"]:
        return _build_npbb_adjust_form_ctx(r, db), _NPBB_ADJUST_TPL_PATH
    if r["leave_type"] == "bat_buoc":
        return _build_npbb_register_form_ctx(r, leave_id, db), _NPBB_REGISTER_TPL_PATH

    tpl_path = _pick_template(r["staff_role"])
    if not os.path.exists(tpl_path):
        raise HTTPException(500, "Chưa có template đơn nghỉ phép")

    start = date.fromisoformat(r["start_date"])
    end   = date.fromisoformat(r["end_date"])
    now   = _vn_now()
    _lich = _load_lich(db, start, end)

    leave_days = len(json.loads(r["spread_dates"])) if r["spread_dates"] else _period_days(start, end, _lich, r["leave_type"])
    # Ưu tiên hạn mức nhập tay (leave_quotas) — khớp đúng quy tắc get_quotas/export_quotas/
    # stats_annual; chỉ tính theo ngày vào ngành khi năm đó chưa có ai nhập tay.
    _q_row = db.execute(
        "SELECT quota_days FROM leave_quotas WHERE staff_id=? AND year=?",
        (r["staff_id"], start.year),
    ).fetchone()
    tong_phep = (
        float(_q_row["quota_days"]) if _q_row
        else (compute_annual_leave(r["join_industry_date"], start.year) if r["join_industry_date"] else (r["annual_leave_days"] or 12))
    )
    carry_original = compute_carry_over(r["staff_id"], start.year, db, effective=False)
    # Carryover hiệu lực theo ngày bắt đầu của đơn (Q1 → có carryover, sau Q1 → 0)
    carry_eff_doc  = compute_carry_over(r["staff_id"], start.year, db, effective=True, ref_date=start)
    # Số ngày đã nghỉ TRONG CÙNG NĂM (trừ đơn hiện tại)
    da_nghi = _calc_used_days(r["staff_id"], start.year, db, exclude_id=leave_id)
    con_lai = max(0.0, tong_phep + carry_eff_doc - da_nghi - leave_days)

    # ── Biến 2-năm cho trường hợp có ngày dư ──
    has_carryover   = carry_eff_doc > 0
    carryover_used  = min(float(carry_eff_doc), float(leave_days))
    new_year_days   = leave_days - carryover_used
    if has_carryover:
        _prev_year = start.year - 1
        _q_prev = db.execute(
            "SELECT quota_days FROM leave_quotas WHERE staff_id=? AND year=?",
            (r["staff_id"], _prev_year),
        ).fetchone()
        tong_so_phep_prev = float(_q_prev["quota_days"]) if _q_prev else float(
            compute_annual_leave(r["join_industry_date"], _prev_year) if r["join_industry_date"] else 12
        )
        da_nghi_prev = _calc_used_days(r["staff_id"], _prev_year, db)
        con_lai_prev = max(0.0, tong_so_phep_prev - da_nghi_prev - carryover_used)
        con_lai_cur  = max(0.0, tong_phep - da_nghi - new_year_days)
    else:
        _prev_year = start.year - 1
        tong_so_phep_prev = 0.0
        da_nghi_prev = 0.0
        con_lai_prev = 0.0
        con_lai_cur  = con_lai

    # Tên GĐ/PGĐ
    gd_name = r["gd_approver_name"] or ""

    # Tên phòng ngắn (bỏ tiền tố "Phòng ")
    dept_raw  = r["dept_name"] or ""
    dept_short = dept_raw.upper()
    if dept_short.startswith("PHÒNG "):
        dept_short = dept_short[6:]
    # Tên phòng ngắn, giữ nguyên hoa/thường — dùng trong câu văn thường (mẫu
    # đơn theo cấp bậc don_xin_nghi_phep_nv.docx), khác dept_short (viết hoa,
    # dùng cho nhãn TRƯỞNG PHÒNG/TUQ. ở trên).
    phong_ten = dept_raw[6:] if dept_raw.upper().startswith("PHÒNG ") else dept_raw

    # GĐ không thể "kính đề nghị" chính mình — đơn của GĐ kính gửi thẳng Tổng
    # Giám đốc Agribank (đối chiếu mẫu "GIẤY NGHỈ PHÉP GIÁM ĐỐC" thật); PGĐ vẫn
    # kính đề nghị Tổng Giám đốc trong thân đơn (mẫu riêng don_xin_nghi_phep_pgd.docx
    # tự ghi cứng khối "Kính gửi" 3 dòng — không dùng doi_tuong_full ở đó). Các
    # cấp còn lại giữ nguyên đối tượng cũ.
    if r["staff_role"] in ("giam_doc", "pho_giam_doc"):
        doi_tuong, doi_tuong_full = "Tổng Giám đốc", "Tổng Giám đốc Agribank"
    else:
        doi_tuong, doi_tuong_full = "Giám đốc Trung tâm Thanh toán", "Giám đốc Trung tâm Thanh toán Agribank"

    # Nhãn KSV — luôn hiện với role thường, kể cả khai báo hộ (ksv_approver_id=NULL)
    ksv_sign = r["staff_role"] not in ("truong_phong", "giam_doc", "pho_giam_doc")
    ksv_role = ""
    if r["ksv_approver_id"]:
        ksv_r = db.execute("SELECT role FROM user_tttt WHERE id=?", (r["ksv_approver_id"],)).fetchone()
        if ksv_r:
            ksv_role = ksv_r["role"]

    if ksv_role == "pho_phong":
        ksv_dept_label      = f"TUQ. TRƯỞNG PHÒNG {dept_short}"
        ksv_dept_label_line2 = "PHÓ TRƯỞNG PHÒNG"
    else:  # truong_phong hoặc không xác định (khai báo hộ)
        ksv_dept_label      = f"TRƯỞNG PHÒNG {dept_short}"
        ksv_dept_label_line2 = ""

    # Nhãn ký tên cho Ban lãnh đạo
    gd_role = r["gd_role"] or ""
    if gd_role == "pho_giam_doc":
        gd_title_line1 = "TUQ. GIÁM ĐỐC TTTT"
        gd_title_line2 = "PHÓ GIÁM ĐỐC"
    elif gd_role == "giam_doc":
        gd_title_line1 = "GIÁM ĐỐC TTTT"
        gd_title_line2 = ""
    else:
        gd_title_line1 = "GIÁM ĐỐC TTTT"
        gd_title_line2 = ""

    # annual/bat_buoc → ngày làm đơn; dot_xuat và các loại khác → ngày bắt đầu nghỉ
    _doc_date = now.date() if r["leave_type"] in ("annual", "bat_buoc") else start
    ctx = {
        "ngay_thang_nam":   f"{_doc_date.day:02d} tháng {_doc_date.month:02d} năm {_doc_date.year}",
        "doi_tuong":        doi_tuong,
        "doi_tuong_full":   doi_tuong_full,
        "ho_va_ten":        r["staff_name"] or "",
        "chuc_vu":          ("Giám đốc - Trung tâm Thanh toán Agribank"
                            if r["staff_role"] == "giam_doc"
                            else "Phó Giám đốc - Trung tâm Thanh toán Agribank"
                            if r["staff_role"] == "pho_giam_doc"
                            else _ROLE_VN.get(r["staff_role"] or "", r["staff_role"] or "")),
        "don_vi":           r["dept_name"] or "",
        "phong_ten":        phong_ten,
        "nam_phep":         str(start.year),
        "tong_so_phep":      str(tong_phep),
        "so_ngay_da_nghi":   f"{da_nghi:g}",
        "so_ngay_xin_nghi":  _fmt_leave_period(
            start, end, leave_days,
            json.loads(r["spread_dates"]) if r["spread_dates"] else None,
            _lich,
        ),
        "so_ngay_con_lai":   f"{con_lai_cur:g}",
        # 2-năm (carryover)
        "has_carryover":     has_carryover,
        "prev_year":         str(_prev_year),
        "tong_so_phep_prev": f"{int(tong_so_phep_prev)}",
        "da_nghi_prev":      f"{da_nghi_prev:g}",
        "da_nghi_cur":       f"{da_nghi:g}",
        "con_lai_prev":      f"{con_lai_prev:g}",
        "con_lai_cur":       f"{con_lai_cur:g}",
        "ly_do":            r["reason"] or "",
        "ksv_name":         (r["ksv_name"] or "") if ksv_sign else "",
        "gd_name":          gd_name,
        "gd_title_line1":        gd_title_line1,
        "gd_title_line2":        gd_title_line2,
    }

    ctx["ksv_dept_label"] = ksv_dept_label if ksv_sign else ""
    ctx["ksv_dept_label_line2"] = ksv_dept_label_line2 if ksv_sign else ""

    # Override chuc_vu để thêm phòng + tên ngân hàng cho các role cấp trung
    if r["staff_role"] in ("truong_phong", "pho_phong"):
        role_prefix = _ROLE_VN.get(r["staff_role"], "")
        dept_suffix = (r["dept_name"] or "").replace("Phòng ", "")
        if dept_suffix:
            ctx["chuc_vu"] = f"{role_prefix} {dept_suffix} - Trung tâm Thanh toán Agribank"
        else:
            ctx["chuc_vu"] = f"{role_prefix} - Trung tâm Thanh toán Agribank"

    _LEAVE_TYPE_VN = {
        "thai_san": "thai sản theo chế độ", "bao_hiem": "bảo hiểm theo chế độ",
        "annual": "phép năm", "bat_buoc": "phép bắt buộc",
        "khong_luong": "không lương", "hop_cong_tac": "họp/công tác",
        "other": "phép khác",
    }
    is_no_quota = _is_no_quota_row(r["leave_type"], r["other_deduct_quota"])
    ctx["is_no_quota"]    = is_no_quota
    ctx["leave_type_vn"]  = _LEAVE_TYPE_VN.get(r["leave_type"], r["leave_type"] or "")
    # thai_san / bao_hiem không tính hạn mức — để trống các ô quota trên phiếu
    if is_no_quota:
        ctx.update({
            "tong_so_phep":      "",
            "so_ngay_da_nghi":   "",
            "so_ngay_con_lai":   "",
            "has_carryover":     False,
            "tong_so_phep_prev": "",
            "da_nghi_prev":      "",
            "da_nghi_cur":       "",
            "con_lai_prev":      "",
            "con_lai_cur":       "",
        })
    return ctx, tpl_path


def _render_form_docx(ctx: dict, tpl_path: str) -> bytes:
    from docxtpl import DocxTemplate
    tpl = DocxTemplate(tpl_path)
    tpl.render(ctx)
    buf = io.BytesIO()
    tpl.save(buf)
    return buf.getvalue()


# ─── Bản PDF + chữ ký ────────────────────────────────────────────────────────
# Nhãn để dò vị trí gợi ý cho từng ô ký. Dò PHÂN BIỆT HOA-THƯỜNG: chữ thường
# "Trưởng phòng" còn nằm ở dòng "Chức vụ:" phía trên, khớp trúng dòng đó thì chữ
# ký nhảy lên giữa trang.
_SIG_SLOTS = {
    "nguoi_de_nghi": "NGƯỜI ĐỀ NGHỊ",
    "ksv":           "TRƯỞNG PHÒNG",
    "gd":            "GIÁM ĐỐC TTTT",
}
_SIG_SLOT_VN = {"nguoi_de_nghi": "Người đề nghị", "ksv": "Trưởng phòng", "gd": "Ban lãnh đạo"}
_SIG_W_MM = 38.0          # bề ngang mặc định của khung chữ ký
_SIG_RATIO = 0.38         # cao/rộng khi không đọc được kích thước ảnh


def _form_pdf(r, leave_id: Optional[int], db: sqlite3.Connection) -> bytes:
    """PDF gốc (chưa có chữ ký). Word chỉ chạy khi cache trượt — khoá cache là
    nội dung đơn nên sửa người duyệt / số ngày là tự dựng lại."""
    ctx, tpl_path = _build_form_ctx(r, leave_id, db)
    try:
        mtime = os.path.getmtime(tpl_path)
    except OSError:
        mtime = 0
    key = leave_pdf.cache_key(tpl_path, mtime, json.dumps(ctx, sort_keys=True, default=str))
    return leave_pdf.base_pdf(key, lambda: _render_form_docx(ctx, tpl_path))


def _sig_image(staff_id: Optional[int], db: sqlite3.Connection) -> Optional[bytes]:
    if not staff_id:
        return None
    row = db.execute("SELECT image FROM user_signatures WHERE staff_id=?", (staff_id,)).fetchone()
    return row["image"] if row else None


def _suggest_sig_box(pdf: bytes, slot: str, image: Optional[bytes]) -> dict:
    """Khung gợi ý: ngay dưới nhãn ô ký, giữa theo chiều ngang của nhãn."""
    ratio = _SIG_RATIO
    if image:
        w_px, h_px = leave_pdf.png_size(image)
        if w_px and h_px:
            ratio = h_px / w_px
    w = _SIG_W_MM
    h = max(6.0, min(45.0, w * ratio))
    anchor = None
    needle = _SIG_SLOTS.get(slot)
    if needle:
        anchor = leave_pdf.find_text_box(pdf, needle, match_case=True)
    if anchor:
        x = anchor["x_mm"] + anchor["w_mm"] / 2 - w / 2
        y = anchor["y_mm"] + anchor["h_mm"] + 1.5
        page = anchor["page"]
    else:
        # Không dò được nhãn (mẫu đơn đổi chữ) — thả xuống giữa nửa dưới trang,
        # người ký tự kéo. Thà lệch còn hơn không hiện chữ ký nào.
        x, y, page = 85.0, 200.0, 0
    return {"page": page, "x_mm": round(x, 2), "y_mm": round(y, 2),
            "w_mm": round(w, 2), "h_mm": round(h, 2)}


def _placed_signatures(leave_id: Optional[int], db: sqlite3.Connection) -> list:
    if not leave_id:
        return []
    rows = db.execute(
        """SELECT slot, page, x_mm, y_mm, w_mm, h_mm, image, signed_at
           FROM leave_signatures WHERE leave_id=? ORDER BY id""",
        (leave_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def _validate_placement(pl) -> dict:
    """Chặn toạ độ vô lý trước khi ghi DB (khung ngoài trang, bé/to bất thường)."""
    if pl is None:
        return None
    box = {"page": int(pl.page or 0), "x_mm": float(pl.x_mm), "y_mm": float(pl.y_mm),
           "w_mm": float(pl.w_mm), "h_mm": float(pl.h_mm)}
    if box["page"] < 0 or box["page"] > 20:
        raise HTTPException(400, "Số trang đặt chữ ký không hợp lệ")
    if not (5.0 <= box["w_mm"] <= 150.0 and 3.0 <= box["h_mm"] <= 150.0):
        raise HTTPException(400, "Kích thước chữ ký không hợp lệ (rộng 5–150mm, cao 3–150mm)")
    if not (-5.0 <= box["x_mm"] <= 420.0 and -5.0 <= box["y_mm"] <= 594.0):
        raise HTTPException(400, "Vị trí chữ ký nằm ngoài trang")
    return box


def _save_signature(db: sqlite3.Connection, leave_id: int, slot: str,
                    staff_id: int, pl) -> None:
    """Ghi chữ ký vào đơn. Ảnh được SAO LẠI vào leave_signatures ngay lúc ký —
    sau này người ký đổi hoặc xoá ảnh cá nhân thì đơn cũ không đổi theo."""
    box = _validate_placement(pl)
    if box is None:
        return
    image = _sig_image(staff_id, db)
    if not image:
        raise HTTPException(400, "Chưa có ảnh chữ ký — vào Quản lý người dùng để tải lên")
    db.execute("DELETE FROM leave_signatures WHERE leave_id=? AND slot=?", (leave_id, slot))
    db.execute(
        """INSERT INTO leave_signatures
               (leave_id, slot, staff_id, page, x_mm, y_mm, w_mm, h_mm, image, signed_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (leave_id, slot, staff_id, box["page"], box["x_mm"], box["y_mm"],
         box["w_mm"], box["h_mm"], image, str(_vn_now())),
    )


def _data_url(image: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(image).decode()


def _preview_payload(r, leave_id: Optional[int], slot: str,
                     signer_id: Optional[int], db: sqlite3.Connection) -> dict:
    """Ảnh trang đơn + chữ ký đã có + khung gợi ý cho ô ký sắp tới."""
    try:
        pdf = _form_pdf(r, leave_id, db)
    except leave_pdf.PdfConvertError as e:
        raise HTTPException(503, f"Không dựng được bản xem trước: {e}")

    all_sigs = _placed_signatures(leave_id, db)
    placed = [p for p in all_sigs if p["slot"] != slot]
    my_image = _sig_image(signer_id, db) if slot else None
    # Ô này đã ký rồi (duyệt lại, xem lại) → mở đúng chỗ cũ, đừng kéo về chỗ gợi ý
    earlier = next((p for p in all_sigs if p["slot"] == slot), None)
    if not slot:
        suggest = None
    elif earlier:
        suggest = {k: earlier[k] for k in ("page", "x_mm", "y_mm", "w_mm", "h_mm")}
    else:
        suggest = _suggest_sig_box(pdf, slot, my_image)
    page_no = suggest["page"] if suggest else (placed[0]["page"] if placed else 0)
    png, w_mm, h_mm, n_pages = leave_pdf.page_png(pdf, page_no)
    return {
        "page": page_no,
        "pages": n_pages,
        "page_png": _data_url(png),
        "page_w_mm": round(w_mm, 2),
        "page_h_mm": round(h_mm, 2),
        "slot": slot or None,
        "slot_label": _SIG_SLOT_VN.get(slot, ""),
        "signature": ({"data_url": _data_url(my_image)} if my_image else None),
        "suggest": suggest,
        "placed": [
            {"slot": p["slot"], "label": _SIG_SLOT_VN.get(p["slot"], p["slot"]),
             "x_mm": p["x_mm"], "y_mm": p["y_mm"], "w_mm": p["w_mm"], "h_mm": p["h_mm"],
             "data_url": _data_url(p["image"])}
            for p in placed if p["page"] == page_no
        ],
    }


def _sig_slot_for(r, current: dict, db: sqlite3.Connection) -> str:
    """Ô ký mà người đang đăng nhập được quyền ký trên đơn này."""
    if r["staff_id"] == current["id"]:
        return "nguoi_de_nghi"
    if r["status"] == LeaveStatus.PENDING_KSV and (
            r["ksv_approver_id"] == current["id"] or current["role"] == "admin"
            or _is_alt_ksv(current, r["staff_id"], db)):
        return "ksv"
    if r["status"] == LeaveStatus.PENDING_GD and (
            r["gd_approver_id"] == current["id"] or current["role"] == "admin"):
        return "gd"
    return ""


# ── Ba endpoint dưới đây gọi Word qua PowerShell (5–7 giây khi cache lạnh, tối
# đa 150 giây nếu Word treo) và tuần tự hoá trên `leave_pdf._word_lock`.
#
# Chúng PHẢI là `async def` + `await run_heavy(...)`. Để `def` thì FastAPI đẩy
# vào threadpool CHUNG 40 token của anyio: mấy người cùng bấm "Xem trước" là
# xếp hàng ở `_word_lock` mà vẫn mỗi người giữ một token, Word treo một lần là
# bể cạn — và lúc đó MỌI endpoint khác của hệ thống (chấm công, bàn giao, sổ
# trực... đều là `def`) cùng đứng chờ theo. Đo được trên hệ thống thật: 40 việc
# nặng đồng thời làm `/api/auth/me` kẹt 38 giây.
#
# `run_heavy()` giới hạn ở MAX_HEAVY=4, phần token còn lại luôn dành cho request
# nhẹ. Xem backend/core/concurrency.py.
#
# Kết nối SQLite dùng lại được trong luồng phụ vì `get_db()` mở với
# `check_same_thread=False`, và ở đây chỉ có một luồng đụng vào tại một thời điểm.


@router.post("/preview/warmup")
def warm_up_preview(current: dict = Depends(get_current_staff)):
    """Bật sẵn Word ở nền — gọi ngay khi mở màn nghỉ phép.

    Mở Word tốn ~1,5 giây, chuyển một file chỉ tốn ~0,35 giây. Bật trước lúc người
    dùng còn đang điền đơn thì đến khi bấm "Xem trước" gần như không phải chờ.

    Trả lời ngay, không đợi Word lên: đây là việc dọn đường, hỏng cũng không sao
    (đường xem trước thật vẫn tự bật Word khi cần).
    """
    threading.Thread(target=leave_pdf.warm_up, name="word-warmup", daemon=True).start()
    return {"ok": True}


@router.post("/preview")
async def preview_draft_form(
    body: LeaveCreate,
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(require_feature("leaves.create")),
):
    """Xem trước đơn CHƯA gửi — để người làm đơn đặt chữ ký rồi mới bấm gửi."""
    if body.leave_type not in _VALID_LEAVE_TYPES:
        raise HTTPException(400, f"Loại nghỉ phép không hợp lệ: {body.leave_type}")

    def _work():
        r = _draft_form_row(body, current, db)
        return _preview_payload(r, None, "nguoi_de_nghi", current["id"], db)

    return await run_heavy(_work)


@router.get("/{leave_id}/preview")
async def preview_leave_form(
    leave_id: int,
    slot: str = "",
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(get_current_staff),
):
    """Xem trước đơn đã có. `slot` để trống → tự chọn ô ký hợp lệ của người gọi."""
    if slot and slot not in _SIG_SLOTS:
        raise HTTPException(400, "Ô ký không hợp lệ")

    def _work():
        r = _load_form_row(leave_id, db)
        if not _can_view_form(r, current, db):
            raise HTTPException(403, "Không có quyền xem đơn này")
        o = slot or _sig_slot_for(r, current, db)
        return _preview_payload(r, leave_id, o, current["id"] if o else None, db)

    return await run_heavy(_work)


@router.get("/{leave_id}/download")
async def download_leave_form(
    leave_id: int,
    fmt: str = "pdf",
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(get_current_staff),
):
    def _work():
        r = _load_form_row(leave_id, db)
        if not _can_view_form(r, current, db):
            raise HTTPException(403, "Không có quyền tải đơn này")

        ec = r["employee_code"] or "staff"
        if fmt == "docx":
            # Đường lui khi máy chủ không chuyển được PDF (chưa cài Word / Word treo).
            ctx, tpl_path = _build_form_ctx(r, leave_id, db)
            return (_render_form_docx(ctx, tpl_path),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    f"don_nghi_phep_{ec}_{r['start_date']}.docx")

        try:
            pdf = _form_pdf(r, leave_id, db)
            pdf = leave_pdf.stamp(pdf, _placed_signatures(leave_id, db))
        except leave_pdf.PdfConvertError as e:
            raise HTTPException(503, f"Không tạo được PDF: {e}")
        return pdf, "application/pdf", f"don_nghi_phep_{ec}_{r['start_date']}.pdf"

    noi_dung, kieu, ten_file = await run_heavy(_work)
    return StreamingResponse(
        io.BytesIO(noi_dung),
        media_type=kieu,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{ten_file}"},
    )


# ─── Hạn mức phép (quota) ──────────────────────────────────────────────────────

@router.get("/quotas/{year}")
def get_quotas(
    year: int,
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(require_feature("leaves.quota_admin")),
):
    """Trả danh sách hạn mức phép của tất cả nhân viên trong năm."""
    staffs = db.execute(
        """SELECT u.id, u.full_name, u.employee_code, u.join_industry_date, d.name AS dept_name
           FROM user_tttt u
           LEFT JOIN departments d ON u.department_id = d.id
           WHERE u.is_active=1 AND (u.is_deleted=0 OR u.is_deleted IS NULL)
           ORDER BY d.name, u.full_name"""
    ).fetchall()
    staff_ids = [s["id"] for s in staffs]
    from datetime import date as _today_d
    is_current_year = (year == _today_d.today().year)
    # Gộp truy vấn hạn mức/carry-over/đã dùng cho TOÀN BỘ nhân viên thành vài query
    # thay vì mỗi nhân viên ~9-10 query (N+1) — quan trọng vì endpoint này load mỗi
    # lần mở trang Hạn mức phép.
    quota_by_staff = {
        r["staff_id"]: float(r["quota_days"])
        for r in db.execute(
            f"SELECT staff_id, quota_days FROM leave_quotas WHERE year=? AND staff_id IN "
            f"({','.join('?' * len(staff_ids))})", [year] + staff_ids
        ).fetchall()
    } if staff_ids else {}
    carry_by_staff      = _carry_over_bulk(staff_ids, year, db, effective=True)
    carry_orig_by_staff = _carry_over_bulk(staff_ids, year, db, effective=False) if is_current_year else {}
    # include_pending=True: khớp đúng enforcement thật lúc tạo đơn (create_leave
    # dùng include_pending=True), tránh hiện "còn lại" cao hơn thực tế cho phép.
    used_by_staff        = _calc_used_days_bulk(staff_ids, year, db, include_pending=True)
    result = []
    for s in staffs:
        quota = quota_by_staff.get(s["id"], float(compute_annual_leave(s["join_industry_date"], year)))
        carry          = carry_by_staff.get(s["id"], 0.0)    # hiển thị Chuyển kỳ
        # Chỉ dùng carry_original để bù khi đang xem năm hiện tại (sau Q1).
        # Năm cũ → Q1 đã qua lâu rồi, carry-over không còn liên quan nữa.
        carry_original = carry_orig_by_staff.get(s["id"], 0.0) if is_current_year else 0.0
        used = used_by_staff.get(s["id"], 0.0)
        result.append({
            "staff_id":         s["id"],
            "staff_name":       s["full_name"],
            "employee_code":    s["employee_code"] or "",
            "dept_name":        s["dept_name"] or "",
            "join_industry_date": str(s["join_industry_date"])[:10] if s["join_industry_date"] else "",
            "year":             year,
            "quota_days":       quota,
            "carry_over":       carry,
            "carry_original":   carry_original,
            "used_days":        used,
            # "remaining" phải khớp số ngày enforcement thực sự cho phép đặt tiếp
            # (create_leave dùng carry hiệu lực theo Q1, không phải carry_original thô).
            "remaining":        max(0.0, quota + carry - used),
        })
    return result


@router.post("/quotas")
def upsert_quota(
    body: LeaveQuotaUpsert,
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(require_feature("leaves.quota_admin")),
):
    """Ghi đè hạn mức phép cho nhân viên trong năm cụ thể."""
    if body.quota_days < 0:
        raise HTTPException(400, "quota_days không được âm")
    staff = db.execute("SELECT id FROM user_tttt WHERE id=? AND is_active=1", (body.staff_id,)).fetchone()
    if not staff:
        raise HTTPException(404, "Nhân viên không tồn tại")
    db.execute(
        "INSERT INTO leave_quotas (staff_id, year, quota_days) VALUES (?,?,?) ON CONFLICT(staff_id, year) DO UPDATE SET quota_days=excluded.quota_days",
        (body.staff_id, body.year, body.quota_days),
    )
    db.commit()
    return {"ok": True, "staff_id": body.staff_id, "year": body.year, "quota_days": body.quota_days}


@router.patch("/quotas/staff/{staff_id}/join-date")
def update_join_date(
    staff_id: int,
    body: dict,
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(require_feature("leaves.quota_admin")),
):
    """Cập nhật ngày vào ngành — chỉ dành cho quota admin.

    Đây là đường ghi thứ ba vào `user_tttt.join_industry_date` (hai đường kia ở
    `backend/api/staff.py`: sửa cán bộ và nhập Excel hàng loạt). Cột này là hồ
    sơ nhân sự chứ không phải số liệu phép, nên phải giữ hai thứ ngang bằng hai
    đường kia:

      - **Validate ISO.** Trước đây nhận thẳng chuỗi client gửi và ghi nguyên
        vào cột DATE. Gõ "01/07/2020" hay "hôm qua" đều vào được, rồi
        `compute_annual_leave()` và mọi chỗ `date.fromisoformat()` đọc cột này
        sẽ vỡ — ở nơi khác, muộn hơn, không ai lần ra nguyên nhân.
      - **Ghi nhật ký kèm giá trị cũ.** AuditMiddleware có ghi, nhưng chỉ ghi
        được `PATCH <đường dẫn>` — không biết ai đổi từ ngày nào sang ngày nào.
        Số ngày phép năm tính từ cột này, nên đổi nó là đổi hạn mức phép.
    """
    join_date = (body.get("join_industry_date") or "").strip()
    if not join_date:
        raise HTTPException(400, "join_industry_date không được để trống")
    try:
        join_date = date.fromisoformat(join_date).isoformat()
    except ValueError:
        raise HTTPException(400, "Ngày vào ngành phải theo định dạng YYYY-MM-DD")
    if date.fromisoformat(join_date) > _vn_now().date():
        raise HTTPException(400, "Ngày vào ngành không được ở tương lai")

    staff = db.execute(
        "SELECT id, full_name, join_industry_date FROM user_tttt WHERE id=? AND is_active=1",
        (staff_id,),
    ).fetchone()
    if not staff:
        raise HTTPException(404, "Không tìm thấy nhân viên")

    db.execute("UPDATE user_tttt SET join_industry_date=? WHERE id=?", (join_date, staff_id))
    write_audit(
        db, current["id"], "staff_join_date_update", "staff", staff_id,
        f"{staff['full_name']}: ngày vào ngành {staff['join_industry_date'] or '(trống)'} → {join_date}",
    )
    db.commit()
    return {"ok": True, "staff_id": staff_id, "join_industry_date": join_date}


@router.patch("/quotas/staff/{staff_id}/used-days")
def update_used_days(
    staff_id: int,
    body: dict,
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(require_feature("leaves.quota_admin")),
):
    """Sửa tay số ngày đã dùng cho 1 nhân viên/năm.

    _calc_used_days (nguồn sự thật duy nhất) không đọc user_tttt.used_leave_days —
    nó đếm từ leave_records — nên sửa tay cũng phải ghi qua 1 bản ghi nghỉ bat_buoc
    approved tổng hợp, giống hệt cơ chế "Nhập file hạn mức" (import_quota_apply).
    Xoá bản ghi tổng hợp cũ (dù tạo bởi import hay sửa tay trước đó) trước khi tạo
    mới — 2 cách nhập luôn thay thế lẫn nhau, không cộng dồn.
    """
    try:
        year = int(body.get("year"))
        used_days = float(body.get("used_days"))
    except (TypeError, ValueError):
        raise HTTPException(400, "year/used_days không hợp lệ")
    if used_days < 0:
        raise HTTPException(400, "Số ngày đã dùng không được âm")
    staff = db.execute("SELECT id FROM user_tttt WHERE id=? AND is_active=1", (staff_id,)).fetchone()
    if not staff:
        raise HTTPException(404, "Không tìm thấy nhân viên")

    db.execute(
        "DELETE FROM leave_records WHERE staff_id=? AND leave_type='bat_buoc' "
        "AND strftime('%Y', start_date)=? AND (reason LIKE '[Import]%' OR reason LIKE '[Điều chỉnh]%')",
        (staff_id, str(year)),
    )
    # used_days là TỔNG mong muốn (khớp giá trị đang hiển thị/tiền điền trên dialog —
    # vốn đã gồm cả đơn nghỉ THẬT), không phải số ngày cộng thêm. Sau khi xoá bản ghi
    # tổng hợp cũ ở trên, phần còn lại trong leave_records là đơn THẬT — phải trừ đi
    # phần này rồi mới chèn đúng phần chênh lệch. Thiếu bước trừ này thì mỗi lần lưu
    # (kể cả không đổi gì, vì dialog tự điền sẵn tổng hiện tại) sẽ cộng dồn thêm đúng
    # bằng tổng cũ — tăng vô hạn qua từng lần bấm Lưu.
    real_used = _calc_used_days(staff_id, year, db, include_pending=True)
    delta = used_days - real_used
    n_days = int(delta + 0.5) if delta > 0 else 0  # round-half-up, không âm
    if n_days >= 1:
        sd = _import_spread_dates(n_days, year)
        if sd:
            now = _vn_now()
            db.execute(
                """INSERT INTO leave_records
                       (staff_id, leave_type, start_date, end_date, spread_dates,
                        status, reason, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (staff_id, "bat_buoc", sd[0], sd[-1], json.dumps(sd), "approved",
                 f"[Điều chỉnh] Đặt số ngày đã dùng = {n_days} (năm {year})",
                 now, now),
            )
    final_used = real_used + n_days
    db.execute("UPDATE user_tttt SET used_leave_days=? WHERE id=?", (final_used, staff_id))
    db.commit()
    return {
        "ok": True, "staff_id": staff_id, "year": year,
        "used_days": final_used,
        # requested < real_used (vd đơn thật đã nhiều hơn số muốn đặt) → không thể trừ
        # bớt đơn thật bằng bản ghi tổng hợp, kết quả bị chặn ở real_used — báo cho
        # frontend biết để thông báo thay vì im lặng lệch số.
        "capped": used_days < real_used,
    }


# ─── Nhập file hạn mức (Excel) ─────────────────────────────────────────────────
# File có thể khác cấu trúc/thứ tự cột giữa các lần — dò cột theo TIÊU ĐỀ (dòng
# header) thay vì cố định vị trí, chỉ cần đủ các trường: STT, Họ và tên,
# Mã cán bộ, Hạn mức, Đã nghỉ. Khớp nhân viên theo Mã cán bộ trước (duy nhất
# theo từng người) — nếu không khớp thì thử theo tên (chuẩn hoá bỏ dấu, chỉ
# nhận khi tên đó chỉ khớp đúng 1 nhân viên). Chỉ nhập "Hạn mức" + "Đã nghỉ"
# (ghi đè used_leave_days) — không nhập "Chuyển năm" vì hệ thống tính động
# từ hạn mức + số ngày đã dùng của năm trước.

def _qi_detect_columns(ws) -> Optional[dict]:
    """Dò dòng tiêu đề trong 6 dòng đầu, trả về map field -> chỉ số cột."""
    for row in ws.iter_rows(min_row=1, max_row=6, values_only=True):
        col_map: dict = {}
        for idx, cell in enumerate(row or ()):
            n = _norm_vn(cell)
            if not n:
                continue
            if "stt" not in col_map and n == "stt":
                col_map["stt"] = idx
            elif "ma_can_bo" not in col_map and ("ma can bo" in n or "ma cb" in n or "ma nv" in n or "ma nhan vien" in n):
                col_map["ma_can_bo"] = idx
            elif "ho_ten" not in col_map and ("ho ten" in n or "ho va ten" in n or n == "ten"):
                col_map["ho_ten"] = idx
            elif "phong" not in col_map and "phong" in n:
                col_map["phong"] = idx
            elif "han_muc" not in col_map and "han muc" in n:
                col_map["han_muc"] = idx
            elif "da_nghi" not in col_map and "da nghi" in n:
                col_map["da_nghi"] = idx
        if {"stt", "ho_ten", "han_muc"} <= col_map.keys():
            return col_map
    return None


@router.post("/quotas/{year}/import/preview")
def import_quota_preview(
    year: int,
    file: UploadFile = File(...),
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(require_feature("leaves.quota_admin")),
):
    """Đọc file Excel hạn mức, khớp nhân viên theo Mã cán bộ / tên — KHÔNG ghi DB."""
    import openpyxl
    content = read_limited_sync(file, ten="File Excel hạn mức")
    try:
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception:
        raise HTTPException(400, "File không hợp lệ — vui lòng chọn đúng file Excel (.xlsx)")
    ws = wb.active

    try:
        col_map = _qi_detect_columns(ws)
        if not col_map:
            raise HTTPException(
                400,
                "Không tìm thấy dòng tiêu đề hợp lệ trong file — cần có tối thiểu các cột "
                "STT, Họ và tên, Hạn mức (còn Mã cán bộ, Phòng, Đã nghỉ nếu có).",
            )

        staffs_by_code: dict = {}
        staffs_by_name: dict = {}
        staff_names: dict = {}
        for r in db.execute("SELECT id, employee_code, full_name FROM user_tttt WHERE is_active=1").fetchall():
            code = (r["employee_code"] or "").strip()
            if code:
                staffs_by_code[code] = r["id"]
            staff_names[r["id"]] = r["full_name"] or ""
            nm = _norm_vn(r["full_name"])
            if nm:
                staffs_by_name.setdefault(nm, []).append(r["id"])

        # Gộp truy vấn hạn mức/đã dùng hiện tại thành 1 lần thay vì mỗi dòng 1 query.
        old_quota_by_staff = {
            r["staff_id"]: float(r["quota_days"])
            for r in db.execute("SELECT staff_id, quota_days FROM leave_quotas WHERE year=?", (year,)).fetchall()
        }
        old_used_by_staff = {
            r["id"]: float(r["used_leave_days"]) if r["used_leave_days"] is not None else 0.0
            for r in db.execute("SELECT id, used_leave_days FROM user_tttt WHERE is_active=1").fetchall()
        }

        def _cell(row, key):
            idx = col_map.get(key)
            return row[idx] if idx is not None and idx < len(row) else None

        def _to_stt(v):
            """Chấp nhận STT dạng int, float nguyên (1.0), hoặc text số ("1")."""
            if isinstance(v, bool):
                return None
            if isinstance(v, int):
                return v
            if isinstance(v, float) and v.is_integer():
                return int(v)
            if isinstance(v, str) and v.strip().isdigit():
                return int(v.strip())
            return None

        rows_out = []
        for row in ws.iter_rows(values_only=True):
            stt = _to_stt(_cell(row, "stt"))
            if stt is None:
                continue
            ho_ten  = _cell(row, "ho_ten")
            ma_cb   = _cell(row, "ma_can_bo")
            phong   = _cell(row, "phong")
            han_muc = _cell(row, "han_muc")
            da_nghi = _cell(row, "da_nghi")
            if not (ho_ten and str(ho_ten).strip()) or han_muc is None:
                continue

            try:
                new_quota = float(str(han_muc).strip().replace(",", "."))
                new_used  = float(str(da_nghi).strip().replace(",", ".")) if da_nghi not in (None, "") else 0.0
            except (ValueError, TypeError):
                # Ô số liệu không hợp lệ — vẫn hiện dòng này để người dùng biết, nhưng
                # đánh dấu lỗi và không cho tick áp dụng (matched=False).
                rows_out.append({
                    "stt": stt, "ho_ten": str(ho_ten).strip(),
                    "ma_can_bo": str(ma_cb).strip() if ma_cb else "",
                    "phong": str(phong).strip() if phong else "",
                    "matched": False, "match_method": None, "staff_id": None,
                    "new_quota_days": 0, "new_used_leave_days": 0,
                    "old_quota_days": None, "old_used_leave_days": None,
                    "row_error": "Hạn mức / Đã nghỉ không phải số hợp lệ",
                    "rounded_warning": False,
                })
                continue

            ma_cb_s = str(ma_cb).strip() if ma_cb else ""
            staff_id = None
            match_method = None
            if ma_cb_s and ma_cb_s in staffs_by_code:
                staff_id = staffs_by_code[ma_cb_s]
                match_method = "ma_can_bo"
            else:
                cands = staffs_by_name.get(_norm_vn(ho_ten)) or []
                if len(cands) == 1:
                    staff_id = cands[0]
                    match_method = "ten"

            item = {
                "stt":                 stt,
                "ho_ten":              str(ho_ten).strip(),
                "ma_can_bo":           ma_cb_s,
                "phong":               str(phong).strip() if phong else "",
                "matched":             staff_id is not None,
                "match_method":        match_method,
                "matched_name":        staff_names.get(staff_id) if staff_id else None,
                "staff_id":            staff_id,
                "new_quota_days":      new_quota,
                "new_used_leave_days": new_used,
                "old_quota_days":      old_quota_by_staff.get(staff_id) if staff_id else None,
                "old_used_leave_days": old_used_by_staff.get(staff_id) if staff_id else None,
                # Hệ thống không có khái niệm "nửa ngày phép" — khi áp dụng, "Đã nghỉ"
                # có phần thập phân sẽ bị làm tròn lên nguyên ngày (xem import_quota_apply).
                # Cảnh báo trước để người nhập biết, tránh lệch 0.5 ngày âm thầm.
                "rounded_warning":     new_used != int(new_used),
            }
            rows_out.append(item)
    finally:
        wb.close()

    matched_count = sum(1 for r in rows_out if r["matched"])
    return {"filename": file.filename, "rows": rows_out, "total": len(rows_out), "matched": matched_count}


def _import_spread_dates(n_days: int, year: int) -> list:
    """Sinh n_days ngày làm việc (T2–T6) từ 02/01/year — dùng cho bản ghi nghỉ tổng hợp khi import.

    CỐ Ý không xét ngày lễ / ngày làm bù. Đây là bản ghi giả lập để lưu SỐ ngày
    phép đã dùng khi nhập file hạn mức, không phải người thật sự vắng mặt những
    ngày đó (xem `_load_staff_leave` trong handover_report_service). Chỉ độ dài
    danh sách có nghĩa, từng ngày cụ thể thì không — kéo lịch làm việc vào đây
    chỉ đổi ngày nào được chọn chứ không đổi con số, mà lại tốn một truy vấn DB."""
    out = []
    d = date(year, 1, 2)
    while len(out) < n_days and d.year == year:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


@router.post("/quotas/{year}/import/apply")
def import_quota_apply(
    year: int,
    body: dict,
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(require_feature("leaves.quota_admin")),
):
    """Áp dụng dữ liệu hạn mức đã xem trước.

    - quota_days → ghi vào leave_quotas.
    - "Đã nghỉ" → tạo bản ghi nghỉ bat_buoc approved tổng hợp (nguồn sự thật cho
      _calc_used_days), thay vì chỉ ghi used_leave_days (trường này không được đọc
      khi tính hạn mức). Import lại sẽ thay bản ghi tổng hợp cũ (idempotent).
    - Giá trị cũ + id bản ghi tạo ra lưu vào quota_import_items để hoàn tác."""
    rows = body.get("rows") or []
    filename = body.get("filename") or ""
    rows = [r for r in rows if r.get("staff_id")]
    if not rows:
        raise HTTPException(400, "Không có dòng nào khớp nhân viên để áp dụng")

    for r in rows:
        try:
            qd, ud = float(r.get("new_quota_days") or 0), float(r.get("new_used_leave_days") or 0)
        except (ValueError, TypeError):
            raise HTTPException(400, "Dữ liệu hạn mức/đã nghỉ không hợp lệ")
        if qd < 0 or ud < 0:
            raise HTTPException(400, "Hạn mức và số ngày đã nghỉ không được âm")

    staff_ids = [r["staff_id"] for r in rows]
    placeholders = ",".join("?" * len(staff_ids))
    active_staff_ids = {
        r["id"] for r in db.execute(
            f"SELECT id FROM user_tttt WHERE id IN ({placeholders}) AND is_active=1", staff_ids
        ).fetchall()
    }
    old_quota_by_staff = {
        r["staff_id"]: float(r["quota_days"])
        for r in db.execute(
            f"SELECT staff_id, quota_days FROM leave_quotas WHERE year=? AND staff_id IN ({placeholders})",
            [year] + staff_ids,
        ).fetchall()
    }
    old_used_by_staff = {
        r["id"]: float(r["used_leave_days"]) if r["used_leave_days"] is not None else 0.0
        for r in db.execute(
            f"SELECT id, used_leave_days FROM user_tttt WHERE id IN ({placeholders})", staff_ids
        ).fetchall()
    }

    now = _vn_now()
    cur = db.execute(
        "INSERT INTO quota_import_batches (year, filename, imported_by, imported_at, row_count) VALUES (?,?,?,?,?)",
        (year, filename, current["id"], now, len(rows)),
    )
    batch_id = cur.lastrowid

    # Xoá TRƯỚC toàn bộ bản ghi tổng hợp cũ (import HOẶC sửa tay trước đó) của
    # từng nhân viên trong đợt này, rồi mới tính _calc_used_days_bulk — để
    # real_used_by_staff phản ánh đúng phần đơn THẬT còn lại, không lẫn số của
    # lần import/sửa tay trước. Phải tách thành 2 lượt (xoá rồi mới tính hàng
    # loạt) thay vì tính trong cùng vòng lặp per-row như update_used_days, vì ở
    # đây xử lý nhiều nhân viên cùng lúc — tính bulk 1 lần rẻ hơn N lần gọi
    # _calc_used_days đơn lẻ.
    for staff_id in staff_ids:
        if staff_id not in active_staff_ids:
            continue
        db.execute(
            "DELETE FROM leave_records WHERE staff_id=? AND leave_type='bat_buoc' "
            "AND strftime('%Y', start_date)=? AND (reason LIKE '[Import]%' OR reason LIKE '[Điều chỉnh]%')",
            (staff_id, str(year)),
        )
    real_used_by_staff = _calc_used_days_bulk(staff_ids, year, db, include_pending=True)

    applied = 0
    capped_staff: list = []
    for r in rows:
        staff_id = r["staff_id"]
        if staff_id not in active_staff_ids:
            continue
        new_quota = float(r.get("new_quota_days") or 0)
        new_used  = float(r.get("new_used_leave_days") or 0)
        old_quota = old_quota_by_staff.get(staff_id)
        old_used  = old_used_by_staff.get(staff_id, 0.0)

        # ── Hạn mức ──
        db.execute(
            "INSERT INTO leave_quotas (staff_id, year, quota_days) VALUES (?,?,?) "
            "ON CONFLICT(staff_id, year) DO UPDATE SET quota_days=excluded.quota_days",
            (staff_id, year, new_quota),
        )

        # ── "Đã nghỉ" → bản ghi nghỉ tổng hợp (để _calc_used_days đếm được) ──
        # new_used là TỔNG mong muốn (số trong file Excel), không phải số ngày
        # cộng thêm — trừ đi phần đơn THẬT (real_used, đã tính ở trên sau khi
        # xoá bản ghi tổng hợp cũ) rồi mới chèn đúng phần chênh lệch. Thiếu bước
        # trừ này thì nhân viên đã có đơn thật trong năm sẽ bị cộng dồn sai
        # ngay từ lần import đầu tiên (giống lỗi đã sửa ở update_used_days).
        real_used = real_used_by_staff.get(staff_id, 0.0)
        delta = new_used - real_used
        # int(round()) dùng banker's rounding (4.5→4, 5.5→6) — không nhất quán.
        # delta có thể âm nên chặn >=0 trước khi +0.5 làm tròn half-up.
        n_days = int(delta + 0.5) if delta > 0 else 0
        if delta < 0:
            capped_staff.append(r.get("matched_name") or r.get("ho_ten") or f"#{staff_id}")
        created_leave_id = None
        if n_days >= 1:
            _sd = _import_spread_dates(n_days, year)
            if _sd:
                _c = db.execute(
                    """INSERT INTO leave_records
                           (staff_id, leave_type, start_date, end_date, spread_dates,
                            status, reason, created_at, updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (staff_id, "bat_buoc", _sd[0], _sd[-1], json.dumps(_sd), "approved",
                     f"[Import] Tổng hợp {n_days} ngày đã nghỉ năm {year} (batch #{batch_id})",
                     now, now),
                )
                created_leave_id = _c.lastrowid

        final_used = real_used + n_days

        # ── Lưu item để hoàn tác (kèm id bản ghi vừa tạo) ──
        db.execute(
            """INSERT INTO quota_import_items
                   (batch_id, staff_id, old_quota_days, old_used_leave_days,
                    new_quota_days, new_used_leave_days, created_leave_id)
               VALUES (?,?,?,?,?,?,?)""",
            (batch_id, staff_id, old_quota, old_used, new_quota, final_used, created_leave_id),
        )
        # Trường cache — hiển thị hạn mức không đọc, giữ đồng bộ cho tương thích.
        db.execute("UPDATE user_tttt SET used_leave_days=? WHERE id=?", (final_used, staff_id))
        applied += 1

    db.execute("UPDATE quota_import_batches SET matched_count=? WHERE id=?", (applied, batch_id))
    db.commit()
    return {
        "batch_id": batch_id, "applied": applied,
        # Nhân viên có "Đã nghỉ" trong file thấp hơn số ngày đơn thật đã ghi
        # nhận — không thể trừ bớt đơn thật bằng bản ghi tổng hợp, kết quả bị
        # giữ ở mức thật, báo cho frontend biết thay vì im lặng lệch số.
        "capped_staff": capped_staff,
    }


@router.get("/quotas/import/history")
def import_quota_history(
    year: Optional[int] = None,
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(require_feature("leaves.quota_admin")),
):
    """Lịch sử các lần nhập file hạn mức — dùng để hoàn tác."""
    clause = "WHERE b.year=?" if year else ""
    params = (year,) if year else ()
    rows = db.execute(
        f"""SELECT b.*, u.full_name AS imported_by_name, rb.full_name AS rolled_back_by_name
            FROM quota_import_batches b
            LEFT JOIN user_tttt u  ON b.imported_by     = u.id
            LEFT JOIN user_tttt rb ON b.rolled_back_by  = rb.id
            {clause}
            ORDER BY b.imported_at DESC""",
        params,
    ).fetchall()
    return [dict(r) for r in rows]


@router.post("/quotas/import/{batch_id}/rollback")
def import_quota_rollback(
    batch_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(require_feature("leaves.quota_admin")),
):
    """Hoàn tác 1 lần nhập file — khôi phục quota_days, xoá bản ghi nghỉ tổng hợp đã
    tạo, và khôi phục used_leave_days về giá trị trước khi nhập. Nếu có lần nhập sau
    đó cũng đổi cùng nhân viên, giá trị sẽ bị ghi đè theo lần hoàn tác này (không tự
    động dồn nhiều lần hoàn tác)."""
    batch = db.execute("SELECT * FROM quota_import_batches WHERE id=?", (batch_id,)).fetchone()
    if not batch:
        raise HTTPException(404, "Không tìm thấy lần nhập")
    if batch["status"] == "rolled_back":
        raise HTTPException(400, "Lần nhập này đã được hoàn tác trước đó")

    items = db.execute("SELECT * FROM quota_import_items WHERE batch_id=?", (batch_id,)).fetchall()
    skipped_superseded = 0
    for it in items:
        # Nếu nhân viên này đã có lần nhập KHÁC (chưa hoàn tác) mới hơn cùng năm
        # đè lên sau batch này, thì hoàn tác batch cũ sẽ ghi sai giá trị (batch
        # mới mới là đúng) — bỏ qua nhân viên này, chỉ hoàn tác cho ai chưa bị
        # đè bởi lần nhập nào mới hơn.
        _newer = db.execute(
            """SELECT 1 FROM quota_import_items qi
               JOIN quota_import_batches b2 ON b2.id = qi.batch_id
               WHERE qi.staff_id = ? AND b2.year = ? AND b2.id != ?
                 AND b2.status != 'rolled_back'
                 AND (b2.imported_at > ? OR (b2.imported_at = ? AND b2.id > ?))
               LIMIT 1""",
            (it["staff_id"], batch["year"], batch_id,
             batch["imported_at"], batch["imported_at"], batch_id),
        ).fetchone()
        if _newer:
            skipped_superseded += 1
            continue
        if it["old_quota_days"] is not None:
            db.execute(
                "INSERT INTO leave_quotas (staff_id, year, quota_days) VALUES (?,?,?) "
                "ON CONFLICT(staff_id, year) DO UPDATE SET quota_days=excluded.quota_days",
                (it["staff_id"], batch["year"], it["old_quota_days"]),
            )
        else:
            db.execute(
                "DELETE FROM leave_quotas WHERE staff_id=? AND year=?", (it["staff_id"], batch["year"])
            )
        # Xoá bản ghi nghỉ tổng hợp mà lần nhập này đã tạo (nếu có)
        _clid = it["created_leave_id"] if "created_leave_id" in it.keys() else None
        if _clid:
            db.execute("DELETE FROM leave_records WHERE id=?", (_clid,))
        if it["old_used_leave_days"] is not None:
            db.execute(
                "UPDATE user_tttt SET used_leave_days=? WHERE id=?",
                (it["old_used_leave_days"], it["staff_id"]),
            )

    db.execute(
        "UPDATE quota_import_batches SET status='rolled_back', rolled_back_by=?, rolled_back_at=? WHERE id=?",
        (current["id"], str(_vn_now()), batch_id),
    )
    db.commit()
    return {
        "ok": True, "batch_id": batch_id,
        "restored": len(items) - skipped_superseded,
        "skipped_superseded": skipped_superseded,
    }


@router.get("/quotas/{year}/export")
def export_quotas(
    year: int,
    ids: str = "",   # staff_id cách nhau bởi dấu phẩy
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(require_feature("leaves.quota_admin")),
):
    """Xuất bảng hạn mức phép năm ra Excel."""
    import openpyxl, io
    from openpyxl.styles import Alignment, Font, PatternFill
    from fastapi.responses import Response

    id_filter = {int(i.strip()) for i in ids.split(",") if i.strip().isdigit()} if ids else None

    staffs = db.execute(
        """SELECT u.id, u.full_name, u.employee_code, u.join_industry_date, d.name AS dept_name
           FROM user_tttt u
           LEFT JOIN departments d ON u.department_id = d.id
           WHERE u.is_active=1 AND (u.is_deleted=0 OR u.is_deleted IS NULL)
           ORDER BY d.name, u.full_name"""
    ).fetchall()

    staffs = [s for s in staffs if not id_filter or s["id"] in id_filter]
    staff_ids = [s["id"] for s in staffs]
    # Gộp truy vấn thay vì N+1 (mỗi nhân viên trước đây ~4-9 query riêng).
    quota_by_staff = {
        r["staff_id"]: float(r["quota_days"])
        for r in db.execute(
            f"SELECT staff_id, quota_days FROM leave_quotas WHERE year=? AND staff_id IN "
            f"({','.join('?' * len(staff_ids))})", [year] + staff_ids
        ).fetchall()
    } if staff_ids else {}
    carry_by_staff = _carry_over_bulk(staff_ids, year, db, effective=True)
    # include_pending=True: khớp đúng enforcement thật lúc tạo đơn.
    used_by_staff  = _calc_used_days_bulk(staff_ids, year, db, include_pending=True)

    data = []
    for s in staffs:
        quota  = quota_by_staff.get(s["id"], float(compute_annual_leave(s["join_industry_date"], year)))
        # carry-over hết hiệu lực sau Q1 (31/3) — cả cột hiển thị lẫn "remaining" đều dùng
        # cùng một giá trị "còn hiệu lực" để nhất quán với enforcement lúc tạo đơn.
        carry  = carry_by_staff.get(s["id"], 0.0)
        used   = used_by_staff.get(s["id"], 0.0)
        join_date = s["join_industry_date"] or ""
        data.append({"name": s["full_name"], "dept": s["dept_name"] or "",
                     "join_date": join_date,
                     "quota": quota, "carry": carry, "used": used,
                     "remaining": max(0.0, quota + carry - used)})

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Han muc phep {year}"

    # Dòng tiêu đề năm
    ws.merge_cells("A1:H1")
    title_cell = ws.cell(row=1, column=1, value=f"BẢNG HẠN MỨC NGHỈ PHÉP NĂM {year}")
    title_cell.font      = Font(bold=True, size=13)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 24

    header_fill = PatternFill("solid", fgColor="8B0000")
    hdr_font    = Font(color="FFFFFF", bold=True)
    headers     = ["STT", "Họ và tên", "Phòng ban", "Ngày vào ngành", "Hạn mức", "Chuyển kỳ", "Đã dùng", "Ngày phép của năm"]
    col_widths  = [6, 30, 30, 18, 12, 12, 12, 12]
    for ci, (h, w) in enumerate(zip(headers, col_widths), 1):
        cell = ws.cell(row=2, column=ci, value=h)
        cell.font, cell.fill = hdr_font, header_fill
        cell.alignment = Alignment(horizontal="center")
        ws.column_dimensions[cell.column_letter].width = w
    for ri, r in enumerate(data, 3):
        ws.cell(ri, 1, ri - 2).alignment = Alignment(horizontal="center")
        ws.cell(ri, 2, r["name"]).alignment = Alignment(horizontal="left")
        ws.cell(ri, 3, r["dept"]).alignment = Alignment(horizontal="left")
        ws.cell(ri, 4, r["join_date"]).alignment = Alignment(horizontal="center")
        for ci, val in enumerate([r["quota"], r["carry"], r["used"]], 5):
            ws.cell(ri, ci, round(val, 1)).alignment = Alignment(horizontal="center")
        cell_rem = ws.cell(ri, 8, round(r["remaining"], 1))
        cell_rem.font = Font(color="157A3A" if r["remaining"] > 0 else "CC0000", bold=True)
        cell_rem.alignment = Alignment(horizontal="center")
    buf = io.BytesIO()
    wb.save(buf)
    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="han_muc_phep_{year}.xlsx"'},
    )


def _calc_occurred_days(staff_id: int, year: int, db: sqlite3.Connection, today: date) -> float:
    """Số ngày ĐÃ THỰC SỰ NGHỈ tính đến `today` trong năm — chỉ đếm ngày đã
    xảy ra (<= today), KHÁC _calc_used_days (đếm cả phần đơn đã duyệt nhưng
    ngày nghỉ còn ở tương lai, dùng để kiểm tra hạn mức lúc tạo đơn). Loại trừ
    y hệt _NO_QUOTA_TYPES — bat_buoc vẫn tính (mang tính bắt buộc nhưng vẫn
    trừ vào quỹ phép năm khi báo cáo, xem export_all_leaves_annual)."""
    rows = db.execute(
        f"""SELECT spread_dates, start_date, end_date FROM leave_records
            WHERE staff_id=? AND status='approved'
              AND leave_type NOT IN ('thai_san','bao_hiem','khong_luong','hop_cong_tac')
              {_OTHER_NO_QUOTA_SQL}
              AND start_date <= ? AND end_date >= ?""",
        (staff_id, f"{year}-12-31", f"{year}-01-01"),
    ).fetchall()
    total = 0.0
    lich: LichLamViec | None = None
    for row in rows:
        if row["spread_dates"]:
            for ds in json.loads(row["spread_dates"]):
                if ds.startswith(str(year)) and date.fromisoformat(ds) <= today:
                    total += 1
        else:
            if lich is None:
                lich = _load_lich(db, date(year, 1, 1), date(year, 12, 31))
            d = date.fromisoformat(row["start_date"])
            e = min(date.fromisoformat(row["end_date"]), today)
            while d <= e:
                if d.year == year and la_ngay_lam_viec(d, lich):
                    total += 1
                d += timedelta(days=1)
    return total


@router.get("/export/annual")
def export_all_leaves_annual(
    year: int,
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(require_feature("leaves.stats_export")),
):
    """Báo cáo tổng hợp phép năm theo phòng ban — đúng mẫu Phòng Tổng hợp
    đang dùng: STT/Họ và tên/Phòng/Chức vụ/Hạn mức/Chuyển năm/Tổng phép/
    "Đã nghỉ tính đến [ngày xuất file]"/Còn lại, có dòng tổng theo từng phòng
    (đứng TRƯỚC danh sách nhân sự phòng đó, đúng thứ tự mẫu giấy thật).
    """
    import openpyxl, io
    from openpyxl.styles import Alignment, Font
    from openpyxl.worksheet.page import PageMargins
    from fastapi.responses import Response

    today = _vn_now().date()

    # feature leaves.stats_export chỉ gate theo group_features, không tự ràng buộc
    # phòng ban — nếu admin lỡ gán quyền này cho nhóm không phải Tổng hợp/lãnh đạo,
    # phải tự lọc ở đây để không lộ dữ liệu toàn trung tâm (khớp leader_dashboard).
    _scope_required = (current["role"] not in ("admin", "giam_doc", "pho_giam_doc")
                       and not _is_tong_hop_staff(current, db))
    _dept_sql    = " AND u.department_id = ?" if _scope_required else ""
    _dept_params = [current.get("department_id")] if _scope_required else []

    staffs = db.execute(
        f"""SELECT u.id, u.full_name, u.role, u.join_industry_date, d.name AS dept_name
           FROM user_tttt u
           LEFT JOIN departments d ON u.department_id = d.id
           WHERE u.is_active=1 AND (u.is_deleted=0 OR u.is_deleted IS NULL)
             AND u.department_id IS NOT NULL{_dept_sql}
           ORDER BY d.name, u.full_name""",
        _dept_params
    ).fetchall()

    # Tính trước từng người — cần xong hết mới biết tổng theo phòng để ghi
    # dòng tổng TRƯỚC danh sách nhân sự (đúng thứ tự mẫu giấy thật).
    person_rows = []
    for s in staffs:
        quota_row = db.execute(
            "SELECT quota_days FROM leave_quotas WHERE staff_id=? AND year=?",
            (s["id"], year),
        ).fetchone()
        han_muc = float(quota_row["quota_days"]) if quota_row else float(compute_annual_leave(s["join_industry_date"], year))
        chuyen_nam = compute_carry_over(s["id"], year, db, effective=True, ref_date=today)
        tong_phep = han_muc + chuyen_nam
        da_nghi = _calc_occurred_days(s["id"], year, db, today)
        # max(0.0, ...) — khớp đúng cách get_quotas/stats_annual đang làm. Xuất
        # báo cáo SAU 31/03: chuyen_nam về 0 (hết hiệu lực) nhưng da_nghi vẫn
        # đếm đủ những ngày quý I đã dùng đúng bằng số chuyển kỳ đó (đơn đã
        # duyệt, không tự xoá theo) — trừ (số hạn mức thật đã bị coi là 0) ra
        # khỏi (số ngày thật đã nghỉ) có thể ra âm, in ra tờ giấy đưa lãnh đạo
        # là con số vô lý. Kẹp về 0 thay vì hiện số âm.
        con_lai = max(0.0, tong_phep - da_nghi)
        person_rows.append({
            "name": s["full_name"] or "", "dept": s["dept_name"] or "(Chưa gán phòng)",
            "chuc_vu": _ROLE_VN.get(s["role"] or "", s["role"] or ""),
            "han_muc": han_muc, "chuyen_nam": chuyen_nam, "tong_phep": tong_phep,
            "da_nghi": da_nghi, "con_lai": con_lai,
        })

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Báo cáo {year}"[:31]

    FONT_NAME = "Times New Roman"
    FONT_SIZE = 14
    headers = ["STT", "Họ và tên", "Phòng", "Chức vụ", "Hạn mức (ngày)", "Chuyển năm",
               "Tổng phép", f"Đã nghỉ (ngày) tính đến {today.strftime('%d/%m/%Y')}", "Còn lại"]
    widths  = [6, 28, 34, 22, 9, 10, 8, 20, 10]
    hdr_font = Font(name=FONT_NAME, size=FONT_SIZE, bold=True)
    for ci, (h, w) in enumerate(zip(headers, widths), 1):
        cell = ws.cell(2, ci, h)
        cell.font = hdr_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.column_dimensions[cell.column_letter].width = w
    # Cột "Đã nghỉ tính đến..." tô đỏ — mốc ngày động, dễ thấy ngay là số liệu
    # chỉ đúng tính đến lúc xuất, không phải trọn năm.
    ws.cell(2, 8).font = Font(name=FONT_NAME, size=FONT_SIZE, bold=True, color="FFFF0000")
    ws.row_dimensions[2].height = 40

    dept_font = Font(name=FONT_NAME, size=FONT_SIZE, bold=True)
    data_font = Font(name=FONT_NAME, size=FONT_SIZE)

    ri = 3
    stt = 0
    idx = 0
    while idx < len(person_rows):
        dept = person_rows[idx]["dept"]
        group = []
        while idx < len(person_rows) and person_rows[idx]["dept"] == dept:
            group.append(person_rows[idx])
            idx += 1

        dept_row = ri
        ws.cell(dept_row, 2, dept).font = dept_font
        for col, key in ((5, "han_muc"), (7, "tong_phep"), (8, "da_nghi"), (9, "con_lai")):
            cell = ws.cell(dept_row, col, round(sum(p[key] for p in group), 1))
            cell.font = dept_font
            cell.alignment = Alignment(horizontal="center")
        ri += 1

        for p in group:
            stt += 1
            ws.cell(ri, 1, stt).font = data_font
            ws.cell(ri, 1).alignment = Alignment(horizontal="center")
            ws.cell(ri, 2, p["name"]).font = data_font
            ws.cell(ri, 3, p["dept"]).font = data_font
            ws.cell(ri, 4, p["chuc_vu"]).font = data_font
            for col, key in ((5, "han_muc"), (6, "chuyen_nam"), (7, "tong_phep"), (8, "da_nghi"), (9, "con_lai")):
                cell = ws.cell(ri, col, round(p[key], 1))
                cell.font = data_font
                cell.alignment = Alignment(horizontal="center")
            ri += 1

    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_margins = PageMargins(left=0.3, right=0.3, top=0.4, bottom=0.4, header=0.2, footer=0.2)
    ws.print_area = f"A1:I{ri - 1}"

    buf = io.BytesIO(); wb.save(buf)
    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="bao_cao_nghi_phep_{year}.xlsx"'},
    )


# ─── Báo cáo NPBB (Mẫu 18 nội bộ / Mẫu 19 gửi TCNS) ─────────────────────────
_NPBB_MAU_TPL = {
    "18": template_path("npbb_mau18_dieu_chinh_tpl.docx"),
    "19": template_path("npbb_mau19_dangky_tpl.docx"),
}


def _npbb_set_cell_text(cell, text: str):
    """Ghi đè text 1 ô bảng, giữ format đoạn đầu — dùng khi nhân bản dòng mẫu
    (deepcopy) rồi điền dữ liệu thật, xem export_npbb_batch. Dữ liệu mẫu gốc
    có ô nhiều đoạn nên XOÁ HẲN các đoạn thừa (không chỉ xoá text) — nếu
    không, đoạn trống để lại 1 dòng trắng thừa trong ô khi in ra."""
    paragraphs = cell.paragraphs
    first = paragraphs[0]
    if first.runs:
        first.runs[0].text = text
        for run in first.runs[1:]:
            run.text = ""
    else:
        first.add_run(text)
    for p in paragraphs[1:]:
        p._element.getparent().remove(p._element)


@router.get("/export/npbb-batch")
def export_npbb_batch(
    year: int,
    mau: str = Query(..., pattern="^(18|19)$", description="18 = tờ trình nội bộ, 19 = gửi TCNS"),
    month: int = Query(None, ge=1, le=12, description="Bỏ trống = xuất cả năm, đúng theo yêu cầu 'báo cáo hàng tháng'"),
    preview: bool = Query(False, description="True = trả PDF xem trước (chuyển tạm qua Word), False = tải file .docx gốc theo mẫu TCNS"),
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(require_feature("leaves.stats_export")),
):
    """Danh sách nhân sự có đơn nghỉ phép bắt buộc trong năm/tháng — "Thời gian
    đã đăng ký" lấy đúng đơn GỐC (adjusts_leave_id IS NULL), "Thời gian điều
    chỉnh" lấy đơn điều chỉnh ĐÃ DUYỆT nếu có (xem npbb_adjust_leave). Đơn
    gốc bị hủy do KHÔNG PHẢI điều chỉnh (rút/hủy thường) không xuất hiện.

    Lọc theo THỜI GIAN ĐÃ ĐĂNG KÝ (start_date của đơn gốc) — cùng field với
    chế độ theo năm cũ, chỉ thu hẹp thêm xuống đúng 1 tháng khi có truyền
    `month`, không đổi field lọc sang created_at.

    `preview=true` chuyển bản .docx vừa dựng sang PDF qua Word (leave_pdf.
    docx_to_pdf, cùng cơ chế với xem trước phiếu nghỉ phép) chỉ để hiển thị —
    bản tải về thật vẫn phải gọi lại không kèm preview để lấy đúng .docx gốc.
    """
    import docx
    from copy import deepcopy
    from fastapi.responses import Response

    tpl_path = _NPBB_MAU_TPL[mau]
    if not os.path.exists(tpl_path):
        raise HTTPException(500, "Chưa có template báo cáo NPBB")

    # feature leaves.stats_export chỉ gate theo group_features, không tự ràng buộc
    # phòng ban — nếu admin lỡ gán quyền này cho nhóm không phải Tổng hợp/lãnh đạo,
    # phải tự lọc ở đây để không lộ dữ liệu toàn trung tâm (khớp export_all_leaves_annual).
    _scope_required = (current["role"] not in ("admin", "giam_doc", "pho_giam_doc")
                       and not _is_tong_hop_staff(current, db))
    _dept_sql    = " AND s.department_id = ?" if _scope_required else ""
    _dept_params = [current.get("department_id")] if _scope_required else []

    if month:
        _period_sql = "strftime('%Y-%m', lr.start_date) = ?"
        _period_param = f"{year:04d}-{month:02d}"
    else:
        _period_sql = "strftime('%Y', lr.start_date) = ?"
        _period_param = str(year)

    roots = db.execute(
        f"""SELECT lr.*, s.full_name AS staff_name, s.role AS staff_role,
                  s.join_industry_date, d.name AS dept_name
           FROM leave_records lr
           LEFT JOIN user_tttt s   ON lr.staff_id = s.id
           LEFT JOIN departments d ON s.department_id = d.id
           WHERE lr.leave_type='bat_buoc' AND lr.adjusts_leave_id IS NULL
             AND {_period_sql}{_dept_sql}
             AND (lr.status='approved' OR EXISTS(
                    SELECT 1 FROM leave_records adj
                    WHERE adj.adjusts_leave_id = lr.id AND adj.status='approved'))
           ORDER BY d.name, s.full_name""",
        [_period_param] + _dept_params,
    ).fetchall()

    def _fmt_range(s: str, e: str) -> str:
        return (f"Từ {date.fromisoformat(s).strftime('%d/%m/%Y')} "
                f"đến hết ngày {date.fromisoformat(e).strftime('%d/%m/%Y')}")

    rows_data = []
    for r in roots:
        adj = db.execute(
            """SELECT start_date, end_date FROM leave_records
               WHERE adjusts_leave_id=? AND status='approved'
               ORDER BY created_at DESC LIMIT 1""",
            (r["id"],),
        ).fetchone()
        quota_row = db.execute(
            "SELECT quota_days FROM leave_quotas WHERE staff_id=? AND year=?",
            (r["staff_id"], year),
        ).fetchone()
        tong_phep = (float(quota_row["quota_days"]) if quota_row
                     else float(compute_annual_leave(r["join_industry_date"], year)))
        da_nghi = _calc_used_days(r["staff_id"], year, db)
        rows_data.append({
            "name":       r["staff_name"] or "",
            "chuc_vu":    _ROLE_VN.get(r["staff_role"] or "", r["staff_role"] or ""),
            "tong_phep":  tong_phep,
            "da_nghi":    da_nghi,
            "da_dang_ky": _fmt_range(r["start_date"], r["end_date"]),
            "dieu_chinh": _fmt_range(adj["start_date"], adj["end_date"]) if adj else "",
        })

    doc = docx.Document(tpl_path)
    table = doc.tables[1]
    tbl = table._tbl
    # Dòng dữ liệu mẫu (row index 2, sau 2 dòng tiêu đề) — nhân bản XML của nó
    # cho mỗi nhân sự thật, xoá hết các dòng mẫu gốc trước khi chèn lại.
    template_tr = deepcopy(table.rows[2]._tr)
    for row in table.rows[2:]:
        tbl.remove(row._tr)
    for idx, item in enumerate(rows_data, 1):
        tbl.append(deepcopy(template_tr))
        cells = table.rows[-1].cells
        _npbb_set_cell_text(cells[0], str(idx))
        _npbb_set_cell_text(cells[1], item["name"])
        _npbb_set_cell_text(cells[2], "")
        _npbb_set_cell_text(cells[3], "")
        _npbb_set_cell_text(cells[4], item["chuc_vu"])
        _npbb_set_cell_text(cells[5], "TTTT")
        _npbb_set_cell_text(cells[6], f"{item['tong_phep']:g}")
        _npbb_set_cell_text(cells[7], f"{item['da_nghi']:g}")
        _npbb_set_cell_text(cells[8], item["da_dang_ky"])
        _npbb_set_cell_text(cells[9], item["dieu_chinh"])
    if not rows_data:
        tbl.append(deepcopy(template_tr))
        cells = table.rows[-1].cells
        _npbb_set_cell_text(cells[1], f"Không có nhân sự nghỉ phép bắt buộc năm {year}")
        for ci in (0, 2, 3, 4, 5, 6, 7, 8, 9):
            _npbb_set_cell_text(cells[ci], "")

    buf = io.BytesIO()
    doc.save(buf)
    docx_bytes = buf.getvalue()

    if preview:
        try:
            pdf_bytes = leave_pdf.docx_to_pdf(docx_bytes)
        except leave_pdf.PdfConvertError as e:
            raise HTTPException(503, f"Không tạo được bản xem trước: {e}")
        return Response(content=pdf_bytes, media_type="application/pdf")

    fname = f"bao_cao_npbb_mau{mau}_{year}.docx"
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


# ─── Báo cáo năm ────────────────────────────────────────────────────────────

@router.get("/stats/annual/{year}")
def stats_annual(
    year: int,
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(require_feature("leaves.stats_export")),
):
    """Tổng hợp phép năm — số ngày quota, carry-over, đã dùng, còn lại theo từng nhân viên."""
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill

    # Cùng lý do như export_all_leaves_annual: feature leaves.stats_export không tự
    # ràng buộc phòng ban — lọc thủ công để tránh lộ dữ liệu toàn trung tâm.
    _scope_required = (current["role"] not in ("admin", "giam_doc", "pho_giam_doc")
                       and not _is_tong_hop_staff(current, db))
    _dept_sql    = " AND u.department_id = ?" if _scope_required else ""
    _dept_params = [current.get("department_id")] if _scope_required else []

    staffs = db.execute(
        f"""SELECT u.id, u.full_name, u.employee_code, u.join_industry_date, d.name AS dept_name
           FROM user_tttt u
           LEFT JOIN departments d ON u.department_id = d.id
           WHERE u.is_active=1 AND (u.is_deleted=0 OR u.is_deleted IS NULL){_dept_sql}
           ORDER BY d.name, u.full_name""",
        _dept_params
    ).fetchall()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Tổng hợp phép {year}"

    # Dòng tiêu đề năm
    ws.merge_cells("A1:H1")
    title_cell = ws.cell(row=1, column=1, value=f"BÁO CÁO TỔNG HỢP NGHỈ PHÉP NĂM {year}")
    title_cell.font      = Font(bold=True, size=13)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 24

    hdr_fill = PatternFill("solid", fgColor="8B0000")
    hdr_font = Font(bold=True, color="FFFFFF")
    headers = ["STT", "Họ và tên", "Phòng ban", "Ngày vào ngành", "Hạn mức", "Chuyển kỳ", "Đã dùng", "Ngày phép của năm"]
    widths  = [6, 28, 28, 18, 12, 12, 12, 12]
    for ci, (h, w) in enumerate(zip(headers, widths), 1):
        cell = ws.cell(row=2, column=ci, value=h)
        cell.fill = hdr_fill
        cell.font = hdr_font
        cell.alignment = Alignment(horizontal="center")
        ws.column_dimensions[cell.column_letter].width = w

    staff_ids = [s["id"] for s in staffs]
    # Gộp truy vấn thay vì N+1.
    quota_by_staff = {
        r["staff_id"]: float(r["quota_days"])
        for r in db.execute(
            f"SELECT staff_id, quota_days FROM leave_quotas WHERE year=? AND staff_id IN "
            f"({','.join('?' * len(staff_ids))})", [year] + staff_ids
        ).fetchall()
    } if staff_ids else {}
    carry_by_staff = _carry_over_bulk(staff_ids, year, db, effective=True)
    # include_pending=True: khớp đúng enforcement thật lúc tạo đơn.
    used_by_staff  = _calc_used_days_bulk(staff_ids, year, db, include_pending=True)

    for idx, s in enumerate(staffs, 1):
        quota = quota_by_staff.get(s["id"], float(compute_annual_leave(s["join_industry_date"], year)))
        # carry-over hết hiệu lực sau Q1 (31/3) — cả cột hiển thị lẫn "remaining" đều dùng
        # cùng một giá trị "còn hiệu lực" để nhất quán với enforcement lúc tạo đơn.
        carry     = carry_by_staff.get(s["id"], 0.0)
        used      = used_by_staff.get(s["id"], 0.0)
        remaining = max(0.0, quota + carry - used)
        ri = idx + 2
        ws.cell(ri, 1, idx).alignment = Alignment(horizontal="center")
        ws.cell(ri, 2, s["full_name"]).alignment = Alignment(horizontal="left")
        ws.cell(ri, 3, s["dept_name"] or "").alignment = Alignment(horizontal="left")
        ws.cell(ri, 4, s["join_industry_date"] or "").alignment = Alignment(horizontal="center")
        for ci, val in enumerate([quota, carry, used], 5):
            ws.cell(ri, ci, round(val, 1)).alignment = Alignment(horizontal="center")
        cell_rem = ws.cell(ri, 8, round(remaining, 1))
        cell_rem.font = Font(color="157A3A" if remaining > 0 else "CC0000", bold=True)
        cell_rem.alignment = Alignment(horizontal="center")

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''bao_cao_phep_{year}.xlsx"},
    )


# ─── Báo cáo chấm công tháng (suy ra từ đơn nghỉ phép đã duyệt) ────────────
def _build_attendance_month_sheet(ws, db: sqlite3.Connection, year: int, month: int, staffs):
    """Dựng 1 sheet chấm công cho đúng 1 tháng vào worksheet `ws` đã tạo sẵn —
    theo mẫu giấy "TONG HOP CHAM CONG TTTT" của Phòng Tổng hợp: nhóm theo
    phòng ban, mỗi người 1 dòng, X = đi làm, P = nghỉ phép (suy ra từ
    leave_records đã duyệt), để trống = T7/CN/lễ.

    CHỈ tự động được phần suy ra từ đơn nghỉ phép đã duyệt — cột xếp loại thi
    đua không có nguồn dữ liệu nào trong phần mềm nên không tự điền được;
    Phòng Tổng hợp bổ sung thủ công sau khi tải về, đúng như mẫu giấy vẫn dùng.

    Ngày sau thời điểm xuất file (kể cả các ngày còn lại của tháng hiện tại)
    để trống — chưa xảy ra thì chưa có gì để tính, không suy đoán "X".
    """
    import calendar
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.page import PageMargins

    today = _vn_now().date()
    ws.title = f"Thang {month:02d}-{year}"

    days_in_month = calendar.monthrange(year, month)[1]
    start = date(year, month, 1)
    end = date(year, month, days_in_month)
    lich = _load_lich(db, start, end)

    # Ký hiệu theo loại nghỉ (theo yêu cầu Phòng Tổng hợp) — loại nào không có
    # ký hiệu riêng thì dùng chung "P". "hop_cong_tac" giờ là leave_type thật
    # (đi qua đúng luồng đơn nghỉ phép bình thường) nên tự điền được từ dữ liệu
    # thật, không còn phải để trống như trước khi loại này chưa tồn tại.
    # "CT" (không phải "H") — bảng attendance_symbols có sẵn "H" = "Đi học"
    # (dùng bởi hệ chấm công thật của Phòng Kế toán, backend/db/migrations.py
    # ::trg_leave_*_sync_attendance) — dùng lại "H" ở đây cho "họp/công tác"
    # sẽ đụng ký hiệu, hiểu sai bản chất khi đọc báo cáo. "CT" = "Công tác" đã
    # có sẵn trong attendance_symbols (review PR #77, Người 1, 2026-09-06).
    _ATTENDANCE_SYMBOL = {"bat_buoc": "BB", "hop_cong_tac": "CT"}

    staff_ids = [s["id"] for s in staffs]
    leave_symbol_by_staff: dict[int, dict] = {sid: {} for sid in staff_ids}
    if staff_ids:
        placeholders = ",".join("?" for _ in staff_ids)
        rows = db.execute(
            f"""SELECT staff_id, start_date, end_date, spread_dates, leave_type FROM leave_records
               WHERE status='approved' AND staff_id IN ({placeholders})
                 AND start_date <= ? AND end_date >= ?""",
            (*staff_ids, end.isoformat(), start.isoformat()),
        ).fetchall()
        for r in rows:
            symbol = _ATTENDANCE_SYMBOL.get(r["leave_type"], "P")
            if r["spread_dates"]:
                for ds in json.loads(r["spread_dates"]):
                    d = date.fromisoformat(ds)
                    if start <= d <= end:
                        leave_symbol_by_staff[r["staff_id"]][d] = symbol
            else:
                d = max(date.fromisoformat(r["start_date"]), start)
                e = min(date.fromisoformat(r["end_date"]), end)
                while d <= e:
                    leave_symbol_by_staff[r["staff_id"]][d] = symbol
                    d += timedelta(days=1)

    # Font/cỡ chữ lấy đúng nguyên file mẫu thật "TONG HOP CHAM CONG TTTT-2026.xlsx"
    # (sheet T12026/T22026 — bản 2026 hiện hành, không phải bản 2023 cũ đã đổi mẫu).
    FONT_NAME = "Times New Roman"
    total_cols = 3 + days_in_month + 3  # STT, Họ và tên, Mã cán bộ, các ngày, X, N.L, Ăn ca
    last_col = get_column_letter(total_cols)
    left_end = total_cols // 2

    ws.merge_cells(f"A1:{get_column_letter(left_end)}1")
    a1 = ws.cell(1, 1, "NGÂN HÀNG NÔNG NGHIỆP")
    a1.font = Font(name=FONT_NAME, size=12, bold=False)
    a1.alignment = Alignment(horizontal="center")
    ws.merge_cells(f"{get_column_letter(left_end + 1)}1:{last_col}1")
    c = ws.cell(1, left_end + 1, "CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM")
    c.font = Font(name=FONT_NAME, size=12, bold=True)
    c.alignment = Alignment(horizontal="center")

    ws.merge_cells(f"A2:{get_column_letter(left_end)}2")
    a2 = ws.cell(2, 1, "VÀ PHÁT TRIỂN NÔNG THÔN VIỆT NAM")
    a2.font = Font(name=FONT_NAME, size=12, bold=False)
    a2.alignment = Alignment(horizontal="center")
    ws.merge_cells(f"{get_column_letter(left_end + 1)}2:{last_col}2")
    c = ws.cell(2, left_end + 1, "Độc lập - Tự do - Hạnh phúc")
    c.font = Font(name=FONT_NAME, size=12, bold=True)
    c.alignment = Alignment(horizontal="center")

    ws.merge_cells(f"A3:{get_column_letter(left_end)}3")
    a3 = ws.cell(3, 1, "TRUNG TÂM THANH TOÁN")
    a3.font = Font(name=FONT_NAME, size=12, bold=True)
    a3.alignment = Alignment(horizontal="center")

    ws.merge_cells(f"A5:{last_col}5")
    tc = ws.cell(5, 1, "BẢNG CHẤM CÔNG LAO ĐỘNG")
    tc.font = Font(name=FONT_NAME, size=14, bold=True)
    tc.alignment = Alignment(horizontal="center")
    ws.row_dimensions[5].height = 18.75

    ws.merge_cells(f"A6:{last_col}6")
    tc = ws.cell(6, 1, f"Tháng {month:02d} năm {year}")
    tc.font = Font(name=FONT_NAME, size=14, bold=True)
    tc.alignment = Alignment(horizontal="center")
    ws.row_dimensions[6].height = 18.75

    HEADER_ROW = 8
    # Mẫu thật dùng cỡ chữ KHÁC NHAU theo từng cột ở dòng tiêu đề, không đồng
    # nhất 1 cỡ: STT/Mã cán bộ 10, Họ và tên 12, các cột ngày 10, X/N.L/Ăn ca 9.
    hdr_font_stt  = Font(name=FONT_NAME, size=10, bold=True)
    hdr_font_name = Font(name=FONT_NAME, size=12, bold=True)
    hdr_font_day  = Font(name=FONT_NAME, size=10, bold=True)
    hdr_font_sum  = Font(name=FONT_NAME, size=9, bold=True)
    weekend_fill = PatternFill("solid", fgColor="FFFFFF00")
    holiday_fill = PatternFill("solid", fgColor="C8E6C9")
    thin = Side(style="thin", color="000000")
    cell_border = Border(left=thin, right=thin, top=thin, bottom=thin)
    wrap_center = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws.row_dimensions[HEADER_ROW].height = 27
    ws.cell(HEADER_ROW, 1, "STT").font = hdr_font_stt
    ws.cell(HEADER_ROW, 2, "Họ và tên").font = hdr_font_name
    ws.cell(HEADER_ROW, 3, "Mã cán bộ").font = hdr_font_stt
    ws.column_dimensions["A"].width = 4
    ws.column_dimensions["B"].width = 24
    ws.column_dimensions["C"].width = 10
    day_col0 = 4
    for dnum in range(1, days_in_month + 1):
        col = day_col0 + dnum - 1
        cell = ws.cell(HEADER_ROW, col, dnum)
        cell.font = hdr_font_day
        cell.border = cell_border
        ws.column_dimensions[get_column_letter(col)].width = 3.5
        d = date(year, month, dnum)
        if not la_ngay_lam_viec(d, lich):
            cell.fill = holiday_fill if d in lich.ngay_le else weekend_fill
    sum_col0 = day_col0 + days_in_month
    for i, label in enumerate(("X", "N.L", "Ăn ca")):
        col = sum_col0 + i
        cell = ws.cell(HEADER_ROW, col, label)
        cell.font = hdr_font_sum
        ws.column_dimensions[get_column_letter(col)].width = 4.3
    for ci in range(1, total_cols + 1):
        cell = ws.cell(HEADER_ROW, ci)
        cell.border = cell_border
        cell.alignment = wrap_center

    # Font/cỡ chữ dòng dữ liệu (khác dòng tiêu đề): STT 11, Họ tên/Mã cán bộ 12,
    # ô ngày + cột tổng 10 — không bold, màu chữ mặc định (đen). Mẫu thật có vài
    # dòng tô chữ đỏ nhưng KHÔNG theo quy luật cố định nào (chỉ 1 số cán bộ ở 1
    # số tháng) nên không có cách suy ra tự động — để mặc định đen cho mọi dòng.
    data_font_stt  = Font(name=FONT_NAME, size=11)
    data_font_name = Font(name=FONT_NAME, size=12)
    data_font_code = Font(name=FONT_NAME, size=10)
    data_font_day  = Font(name=FONT_NAME, size=10)
    data_font_sum  = Font(name=FONT_NAME, size=10)
    dept_font      = Font(name=FONT_NAME, size=10, bold=True)

    ri = HEADER_ROW + 1
    cur_dept = None
    dept_stt = 0
    for s in staffs:
        if s["dept_name"] != cur_dept:
            if cur_dept is not None:
                ws.cell(ri, 2, dept_stt).font = dept_font
                ri += 1
            cur_dept = s["dept_name"]
            dept_stt = 0
            dc = ws.cell(ri, 2, cur_dept or "(Chưa gán phòng)")
            dc.font = dept_font
            dc.alignment = wrap_center
            ri += 1
        ws.row_dimensions[ri].height = 22.5
        dept_stt += 1
        c1 = ws.cell(ri, 1, dept_stt); c1.font = data_font_stt; c1.alignment = Alignment(horizontal="center")
        ws.cell(ri, 2, s["full_name"] or "").font = data_font_name
        c3 = ws.cell(ri, 3, s["employee_code"] or ""); c3.font = data_font_code; c3.alignment = Alignment(horizontal="center")
        x_count = 0
        for dnum in range(1, days_in_month + 1):
            d = date(year, month, dnum)
            col = day_col0 + dnum - 1
            cell = ws.cell(ri, col)
            cell.font = data_font_day
            cell.alignment = Alignment(horizontal="center")
            cell.border = cell_border
            if not la_ngay_lam_viec(d, lich):
                cell.fill = holiday_fill if d in lich.ngay_le else weekend_fill
                continue
            # Ngày chưa tới (sau thời điểm xuất file) — chưa có dữ liệu thật, để
            # trống, không suy đoán "X" cho ngày chưa xảy ra.
            if d > today:
                continue
            _sym = leave_symbol_by_staff.get(s["id"], {}).get(d)
            if _sym:
                cell.value = _sym
            else:
                cell.value = "X"
                x_count += 1
        total_work_days = sum(
            1 for dnum in range(1, days_in_month + 1)
            if la_ngay_lam_viec(date(year, month, dnum), lich) and date(year, month, dnum) <= today
        )
        for i, val in enumerate((x_count, total_work_days, x_count)):
            cell = ws.cell(ri, sum_col0 + i, val)
            cell.font = data_font_sum
            cell.alignment = Alignment(horizontal="center")
        for ci in range(1, total_cols + 1):
            ws.cell(ri, ci).border = cell_border
        ri += 1
    if cur_dept is not None:
        ws.cell(ri, 2, dept_stt).font = dept_font
        ri += 1

    ri += 1
    note = ws.cell(ri, 1,
        "Ghi chú: X = đi làm, P = nghỉ phép, BB = nghỉ phép bắt buộc, H = họp/công tác "
        "(tất cả tự động lấy từ đơn nghỉ phép đã duyệt trong hệ thống). Ô để trống tô màu = Thứ Bảy/Chủ "
        "nhật/ngày lễ, ô để trống không tô màu = ngày chưa tới "
        f"(tính đến {today.strftime('%d/%m/%Y')}, thời điểm xuất file). Cột xếp loại thi đua KHÔNG có dữ "
        "liệu nên chưa tự điền.")
    note.font = Font(name=FONT_NAME, size=9, italic=True, color="666666")
    ws.merge_cells(f"A{ri}:{last_col}{ri}")

    ri += 2
    footer_font = Font(name=FONT_NAME, size=12, bold=True)
    third = total_cols // 3
    # Merge 1 khoảng nhỏ quanh mỗi nhãn — chữ căn giữa (center) trong Excel
    # KHÔNG tự tràn sang ô trống bên cạnh như chữ căn trái, cột A lại rất hẹp
    # (width=4) nên nếu chỉ ghi vào đúng 1 ô, "LẬP BẢNG" sẽ bị cắt chữ khi mở
    # bằng Excel thật (chỉ hiện được "BẢNG"). Excel/LibreOffice không kiểm
    # tra chồng lấn merge khi ghi bằng openpyxl nên vẫn phải tự canh đủ hẹp.
    for col, label in ((1, "LẬP BẢNG"), (third + 1, "KIỂM SOÁT"), (2 * third + 1, "GIÁM ĐỐC")):
        end_col = min(col + 3, total_cols)
        ws.merge_cells(start_row=ri, start_column=col, end_row=ri, end_column=end_col)
        cell = ws.cell(ri, col, label)
        cell.font = footer_font
        cell.alignment = Alignment(horizontal="center")

    # Canh in vừa 1 trang ngang — bảng rộng tới hơn 30 cột (mỗi ngày 1 cột)
    # nên khổ dọc mặc định của Excel sẽ luôn bị tràn sang trang 2 nếu không
    # ép khổ ngang + fit-to-width. fitToPage PHẢI bật thì fitToWidth mới có
    # tác dụng — thiếu dòng đó Excel bỏ qua toàn bộ cấu hình fit, in theo
    # scale 100% mặc định.
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_margins = PageMargins(left=0.2, right=0.2, top=0.4, bottom=0.4, header=0.2, footer=0.2)
    ws.print_area = f"A1:{last_col}{ri}"


@router.get("/export/attendance-monthly")
def export_attendance_monthly(
    year: int,
    month: int = Query(None, ge=1, le=12, description="Bỏ trống = xuất cả năm, mỗi tháng 1 sheet"),
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(require_feature("leaves.stats_export")),
):
    """Xuất báo cáo chấm công — 1 tháng (1 sheet) hoặc cả năm (12 sheet, mỗi
    tháng 1 sheet, đúng cấu trúc file mẫu "TONG HOP CHAM CONG TTTT")."""
    import openpyxl

    _scope_required = (current["role"] not in ("admin", "giam_doc", "pho_giam_doc")
                       and not _is_tong_hop_staff(current, db))
    _dept_sql    = " AND u.department_id = ?" if _scope_required else ""
    _dept_params = [current.get("department_id")] if _scope_required else []

    staffs = db.execute(
        f"""SELECT u.id, u.full_name, u.employee_code, d.name AS dept_name
           FROM user_tttt u
           LEFT JOIN departments d ON u.department_id = d.id
           WHERE u.is_active=1 AND (u.is_deleted=0 OR u.is_deleted IS NULL)
             AND u.department_id IS NOT NULL{_dept_sql}
           ORDER BY d.name, u.full_name""",
        _dept_params
    ).fetchall()

    wb = openpyxl.Workbook()
    if month is None:
        # Cả năm: chỉ xuất tới tháng hiện tại — tháng chưa tới thì chưa có
        # ngày nào xảy ra, không có gì để tính, xuất sheet trống vô nghĩa.
        today = _vn_now().date()
        months_so_far = [m for m in range(1, 13) if date(year, m, 1) <= today]
        if not months_so_far:
            raise HTTPException(400, f"Năm {year} chưa tới, chưa có tháng nào để xuất báo cáo")
        wb.remove(wb.active)
        for m in months_so_far:
            ws = wb.create_sheet()
            _build_attendance_month_sheet(ws, db, year, m, staffs)
        fname = f"bao_cao_cham_cong_ca_nam_{year}.xlsx"
    else:
        ws = wb.active
        _build_attendance_month_sheet(ws, db, year, month, staffs)
        fname = f"bao_cao_cham_cong_{month:02d}_{year}.xlsx"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{fname}"},
    )


# ─── Dashboard lãnh đạo ─────────────────────────────────────────────────────

@router.get("/stats/leader-dashboard")
def leader_dashboard(
    year: int = None,
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(require_feature("leaves.dashboard")),
):
    """Thống kê tổng quan: số đơn theo trạng thái, top nghỉ nhiều, chờ duyệt."""
    from datetime import date as _date
    yr = year or _date.today().year

    # Đơn chờ duyệt — filter theo role, giống list_leaves(scope="pending")
    role = current["role"]
    p_where = ""
    p_params: list = []
    # Đơn của GĐ đã tự động approved nhưng Tổng hợp chưa "biết" — giống hệt
    # _gd_unack trong list_leaves(scope="pending"), thiếu nhánh này khiến widget
    # "Chờ KSV/Chờ Tổng hợp" trên dashboard không khớp số với tab Chờ xác nhận TT.
    _gd_unack = (
        "(lr.status = 'approved' AND lr.tong_hop_approver_id IS NULL "
        "AND lr.staff_id IN (SELECT id FROM user_tttt WHERE role = 'giam_doc'))"
    )
    if role == "admin":
        p_where = f"(lr.status IN ('pending_ksv','pending_tong_hop','pending_gd') OR {_gd_unack})"
    elif role in ("giam_doc", "pho_giam_doc"):
        if _can_gd_review(current, db):
            p_where = "lr.gd_approver_id = ? AND lr.status = 'pending_gd'"
            p_params.append(current["id"])
    elif _is_tong_hop_staff(current, db) and role in ("truong_phong", "pho_phong"):
        # PP/TP Tổng hợp: xem cả KSV phòng mình + TH/GĐ toàn trung tâm — khớp đúng
        # phạm vi "toàn trung tâm" đã áp dụng cho approved/top_staff bên dưới
        # (_scope_required). Thiếu pending_gd ở đây khiến ô "Chờ GĐ" luôn hiện 0
        # dù đơn đang thật sự chờ GĐ (nhìn thấy trong bảng danh sách bên dưới).
        p_where = (f"(lr.status IN ('pending_tong_hop', 'pending_gd') "
                   f"OR (lr.ksv_approver_id = ? AND lr.status = 'pending_ksv') OR {_gd_unack})")
        p_params.append(current["id"])
    elif _is_tong_hop_staff(current, db):
        p_where = f"(lr.status IN ('pending_tong_hop', 'pending_gd') OR {_gd_unack})"
    elif role in ("truong_phong", "pho_phong"):
        p_where = "lr.ksv_approver_id = ? AND lr.status = 'pending_ksv'"
        p_params.append(current["id"])

    if p_where:
        pending_rows = db.execute(
            f"""SELECT lr.id, s.full_name, lr.status, lr.start_date, lr.end_date, lr.leave_type
               FROM leave_records lr
               JOIN user_tttt s ON lr.staff_id = s.id
               WHERE {p_where}
               ORDER BY lr.created_at""",
            p_params,
        ).fetchall()
    else:
        pending_rows = []

    # Số liệu tổng quan (đã duyệt, khai báo hộ, top nghỉ nhiều) chỉ tính người
    # cùng phòng, TRỪ admin / Giám đốc / PGĐ / Phòng Tổng hợp — những vai trò
    # này thấy toàn trung tâm. Áp dụng cho mọi role còn lại (kể cả chuyên viên).
    # Dùng cờ riêng để biết CÓ cần scope hay không — không được suy ra từ giá trị
    # department_id, vì nếu user chưa gán phòng (department_id NULL) thì falsy
    # sẽ vô tình tắt luôn bộ lọc và lộ số liệu toàn trung tâm cho họ.
    _scope_required = (role not in ("admin", "giam_doc", "pho_giam_doc")
                       and not _is_tong_hop_staff(current, db))
    if _scope_required:
        _dept_sql    = " AND s.department_id = ?"
        # department_id NULL → "= NULL" không khớp dòng nào (đúng ý: ẩn hết thay
        # vì lộ toàn trung tâm) — an toàn hơn là bỏ lọc.
        _dept_params = [current.get("department_id")]
    else:
        _dept_sql    = ""
        _dept_params = []

    # by_status: đếm từ danh sách pending đã filter + approved trong năm
    by_status: dict = {}
    for r in pending_rows:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    # Bản ghi tổng hợp giả (nhập Excel/sửa tay hạn mức) không phải đơn nghỉ phép
    # thật — loại khỏi "Hoàn thành"/"Khai báo hộ" để khớp với list_leaves() (đã ẩn
    # tương tự) và không đếm 1 thao tác đối soát hạn mức như 1 đơn đã hoàn thành.
    _not_synthetic = "AND (lr.reason IS NULL OR NOT (lr.reason LIKE '[Import]%' OR lr.reason LIKE '[Điều chỉnh]%'))"
    approved_cnt = db.execute(
        f"""SELECT COUNT(*) FROM leave_records lr JOIN user_tttt s ON lr.staff_id = s.id
           WHERE lr.status='approved' AND strftime('%Y', lr.start_date)=?{_dept_sql} {_not_synthetic}""",
        [str(yr)] + _dept_params,
    ).fetchone()[0]
    by_status["approved"] = approved_cnt
    by_status["direct"] = db.execute(
        f"""SELECT COUNT(*) FROM leave_records lr JOIN user_tttt s ON lr.staff_id = s.id
           WHERE lr.is_direct=1 AND lr.status='approved' AND strftime('%Y', lr.start_date)=?{_dept_sql} {_not_synthetic}""",
        [str(yr)] + _dept_params,
    ).fetchone()[0]
    pending = [
        {
            "id": r["id"], "staff_name": r["full_name"],
            "status": r["status"], "status_label": _LEAVE_STATUS_VN.get(r["status"], r["status"]),
            "start_date": r["start_date"], "end_date": r["end_date"],
            "leave_type": LEAVE_TYPE_LABELS.get(r["leave_type"], r["leave_type"]),
        }
        for r in pending_rows
    ]

    # Top 10 nhân viên nghỉ nhiều nhất trong năm (approved) — tính "Số ngày" bằng
    # _period_days (ngày làm việc, trừ T7/CN/lễ) giống mọi nơi khác trong hệ
    # thống, không đếm ngày lịch thô (julianday) như trước.
    top_raw = db.execute(
        f"""SELECT lr.staff_id, s.full_name, lr.leave_type, lr.spread_dates,
                  lr.start_date, lr.end_date
           FROM leave_records lr
           JOIN user_tttt s ON lr.staff_id = s.id
           WHERE lr.status='approved' AND strftime('%Y', lr.start_date)=?{_dept_sql} {_not_synthetic}""",
        [str(yr)] + _dept_params,
    ).fetchall()
    _lich_nam = _load_lich(db, date(yr, 1, 1), date(yr, 12, 31))
    _top_totals: dict = {}
    _top_names: dict = {}
    for r in top_raw:
        if r["spread_dates"]:
            nd = len(json.loads(r["spread_dates"]))
        else:
            nd = _period_days(
                date.fromisoformat(r["start_date"]), date.fromisoformat(r["end_date"]),
                _lich_nam, r["leave_type"],
            )
        _top_totals[r["staff_id"]] = _top_totals.get(r["staff_id"], 0) + nd
        _top_names[r["staff_id"]] = r["full_name"]
    top_staff = [
        {"staff_name": _top_names[sid], "total_days": total}
        for sid, total in sorted(_top_totals.items(), key=lambda kv: kv[1], reverse=True)[:10]
    ]

    return {
        "year": yr,
        "by_status": by_status,
        "pending": pending,
        "top_staff": top_staff,
    }


# ─── Khai báo hộ (direct leave) ──────────────────────────────────────────────

@router.post("/direct")
def create_direct_leave(
    body: DirectLeaveCreate,
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(require_feature("leaves.declare_direct")),
):
    """Khai báo hộ — tạo đơn approved ngay, cộng used_leave_days thủ công."""
    staff = db.execute(
        "SELECT * FROM user_tttt WHERE id=? AND is_active=1", (body.staff_id,)
    ).fetchone()
    if not staff:
        raise HTTPException(404, "Nhân viên không tồn tại")

    if body.leave_type not in _VALID_LEAVE_TYPES:
        raise HTTPException(400, f"Loại nghỉ phép không hợp lệ: {body.leave_type}")

    if body.spread_dates:
        spread = sorted(set(body.spread_dates))
        if len(spread) < 1:
            raise HTTPException(400, "spread_dates phải có ít nhất 1 ngày")
        try:
            eff_start  = date.fromisoformat(spread[0])
            eff_end    = date.fromisoformat(spread[-1])
        except ValueError:
            raise HTTPException(400, "Định dạng ngày không hợp lệ (yêu cầu YYYY-MM-DD)")
        leave_days = len(spread)
        spread_json = json.dumps(spread)
    else:
        if body.end_date < body.start_date:
            raise HTTPException(400, "Ngày kết thúc phải sau ngày bắt đầu")
        eff_start   = body.start_date
        eff_end     = body.end_date
        _lich = _load_lich(db, eff_start, eff_end)
        leave_days = _period_days(eff_start, eff_end, _lich, body.leave_type)
        spread_json = None

    # Kiểm tra trùng ngày với đơn đã tồn tại (kể cả khai báo hộ và đơn thường)
    all_dates = json.loads(spread_json) if spread_json else [
        (eff_start + __import__('datetime').timedelta(days=i)).isoformat()
        for i in range((eff_end - eff_start).days + 1)
    ]
    existing = db.execute(
        """SELECT lr.id, lr.start_date, lr.end_date, lr.spread_dates
           FROM leave_records lr
           WHERE lr.staff_id=? AND lr.status NOT IN ('cancelled','rejected')
             AND (lr.reason IS NULL OR NOT (lr.reason LIKE '[Import]%' OR lr.reason LIKE '[Điều chỉnh]%'))""",
        (body.staff_id,)
    ).fetchall()
    conflict_dates = []
    for ex in existing:
        ex_dates = json.loads(ex["spread_dates"]) if ex["spread_dates"] else [
            (date.fromisoformat(ex["start_date"]) + __import__('datetime').timedelta(days=i)).isoformat()
            for i in range((date.fromisoformat(ex["end_date"]) - date.fromisoformat(ex["start_date"])).days + 1)
        ]
        overlap = set(all_dates) & set(ex_dates)
        if overlap:
            conflict_dates.extend(sorted(overlap))
    if conflict_dates:
        conflict_str = ", ".join(sorted(set(conflict_dates))[:5])
        raise HTTPException(409, f"Nhân viên đã có đơn nghỉ vào ngày: {conflict_str}. Vui lòng kiểm tra lại.")

    # Kiểm tra hạn mức — dùng chung _check_quota_or_borrow (trước đây khối này
    # tự viết riêng, thiếu điều kiện miễn bat_buoc nên "khai báo hộ" nghỉ bắt
    # buộc bị từ chối sai khi hết hạn mức, khác với create_leave/resubmit_leave).
    borrow_days = _check_quota_or_borrow(
        body.staff_id, staff["join_industry_date"], body.leave_type,
        leave_days, eff_start.year, body.confirm_borrow_next_year, db,
        eff_start=eff_start, other_deduct_quota=body.other_deduct_quota,
    )

    cur = db.execute(
        """INSERT INTO leave_records
               (staff_id, start_date, end_date, leave_type, reason, status,
                is_direct, direct_by, spread_dates, borrow_next_year_days, other_deduct_quota, created_at, updated_at)
           VALUES (?,?,?,?,?,'approved',1,?,?,?,?,?,?)""",
        (body.staff_id, eff_start.isoformat(), eff_end.isoformat(),
         body.leave_type, body.reason,
         current["id"], spread_json, borrow_days, int(body.other_deduct_quota), str(_vn_now()), str(_vn_now())),
    )
    leave_id = cur.lastrowid
    if not _is_no_quota_row(body.leave_type, body.other_deduct_quota):
        db.execute(
            "UPDATE user_tttt SET used_leave_days = COALESCE(used_leave_days,0) + ? WHERE id=?",
            (leave_days, body.staff_id),
        )
    _log_action(db, leave_id, current["id"], "direct_create", None, "", LeaveStatus.APPROVED)
    db.commit()
    return _leave_to_out(leave_id, db)


# ─── Recall (rút đơn đã duyệt) ───────────────────────────────────────────────

@router.post("/{leave_id}/recall")
def request_recall(
    leave_id: int,
    body: RecallCreate,
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(require_feature("leaves.recall")),
):
    """Yêu cầu rút đơn đã duyệt — ghi recall_reason, chuyển sang pending_tong_hop để xác nhận."""
    leave = db.execute("SELECT * FROM leave_records WHERE id=?", (leave_id,)).fetchone()
    if not leave:
        raise HTTPException(404, "Không tìm thấy đơn")
    if leave["status"] != LeaveStatus.APPROVED:
        raise HTTPException(400, "Chỉ rút được đơn đã duyệt")
    if leave["staff_id"] != current["id"] and current["role"] != "admin":
        raise HTTPException(403, "Chỉ chủ nhân đơn hoặc Admin mới được yêu cầu rút")
    if not body.reason:
        raise HTTPException(400, "Vui lòng nhập lý do rút đơn")

    old = leave["status"]
    db.execute(
        "UPDATE leave_records SET recall_reason=?, status=?, updated_at=? WHERE id=?",
        (body.reason, LeaveStatus.PENDING_TONG_HOP, str(_vn_now()), leave_id),
    )
    _log_action(db, leave_id, current["id"], "recall_request", body.reason, old, LeaveStatus.PENDING_TONG_HOP)
    db.commit()
    return _leave_to_out(leave_id, db)


@router.put("/{leave_id}/recall-approve")
def approve_recall(
    leave_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current: dict = Depends(require_feature("leaves.recall")),
):
    """Phòng Tổng hợp xác nhận rút đơn — chuyển sang cancelled."""
    if not _is_tong_hop_staff(current, db) and current["role"] != "admin":
        raise HTTPException(403, "Chỉ Phòng Tổng hợp hoặc Admin mới xác nhận rút đơn")
    leave = db.execute("SELECT * FROM leave_records WHERE id=?", (leave_id,)).fetchone()
    if not leave:
        raise HTTPException(404, "Không tìm thấy đơn")

    # Đơn của Giám đốc: GĐ có toàn quyền với đơn của mình, Tổng hợp có thể xác nhận
    # rút/hủy bất cứ lúc nào sau khi tạo — không cần GĐ gọi request_recall trước
    # và không bắt buộc đơn phải đang ở pending_tong_hop.
    staff_row  = db.execute("SELECT role FROM user_tttt WHERE id=?", (leave["staff_id"],)).fetchone()
    is_gd_leave = bool(staff_row and staff_row["role"] == "giam_doc")

    if not is_gd_leave and leave["staff_id"] == current["id"] and current["role"] != "admin":
        raise HTTPException(403, "Không thể tự xác nhận rút đơn của chính mình")

    if is_gd_leave:
        if leave["status"] in (LeaveStatus.CANCELLED, LeaveStatus.REJECTED):
            raise HTTPException(400, "Đơn đã ở trạng thái kết thúc, không thể xác nhận rút")
    else:
        if leave["status"] != LeaveStatus.PENDING_TONG_HOP or not leave["recall_reason"]:
            raise HTTPException(400, "Đơn này không trong trạng thái chờ xác nhận rút")
    old = leave["status"]
    # Khoá lạc quan (giống _apply_status_transition): chỉ chuyển trạng thái nếu
    # status hiện tại trong DB đúng bằng old — chặn 2 request xác nhận rút trùng
    # cùng lúc (double-click, 2 tab Phòng Tổng hợp) trừ used_leave_days 2 lần
    # cho cùng 1 đơn. Đổi trạng thái TRƯỚC rồi mới trừ hạn mức — request thua
    # cuộc dừng lại ở đây (409), không chạm tới bước trừ hạn mức nữa.
    cur = db.execute(
        "UPDATE leave_records SET status=?, updated_at=? WHERE id=? AND status=?",
        (LeaveStatus.CANCELLED, str(_vn_now()), leave_id, old),
    )
    if cur.rowcount == 0:
        raise HTTPException(409, "Đơn đã được xử lý bởi một yêu cầu khác, vui lòng tải lại trang")
    # Đơn điều chỉnh NPBB bị rút — đơn gốc từng bị _cancel_adjusted_original
    # chuyển "Đã hủy" lúc đơn điều chỉnh này duyệt xong phải được khôi phục
    # lại "Hoàn thành", nếu không sẽ kẹt vĩnh viễn không điều chỉnh lại được
    # nữa (npbb_adjust_leave chỉ nhận điều chỉnh đơn đang "Hoàn thành"). Kiểm
    # tra thẳng adjusts_leave_id — không cần so `old` vì luồng 2 bước của
    # nhân viên thường có old='pending_tong_hop' (đã đổi từ request_recall)
    # chứ không phải 'approved' lúc tới ĐÂY, dù bản chất vẫn là rút 1 đơn đã
    # từng "Hoàn thành".
    if leave["adjusts_leave_id"]:
        _restore_adjusted_original(leave["adjusts_leave_id"], current["id"], db)
    # Trừ used_leave_days khi xác nhận rút (approved → cancelled) — trừ thai_san/bao_hiem
    # vì loại này chưa từng được cộng vào used_leave_days lúc duyệt.
    if not _is_no_quota_row(leave["leave_type"], leave["other_deduct_quota"]):
        start = date.fromisoformat(leave["start_date"])
        end   = date.fromisoformat(leave["end_date"])
        _lich = _load_lich(db, start, end)
        days  = len(json.loads(leave["spread_dates"])) if leave["spread_dates"] else _period_days(start, end, _lich, leave["leave_type"])
        db.execute(
            "UPDATE user_tttt SET used_leave_days = MAX(0, COALESCE(used_leave_days,0) - ?) WHERE id=?",
            (days, leave["staff_id"]),
        )
    _log_action(db, leave_id, current["id"], "recall_approve", None, old, LeaveStatus.CANCELLED)
    db.commit()
    return _leave_to_out(leave_id, db)
