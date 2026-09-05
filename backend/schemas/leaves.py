from datetime import date, datetime
from typing import Optional, Literal, List
from pydantic import BaseModel, ConfigDict


# ─── Leave ───────────────────────────────────────────────────────────────────
class SignaturePlacement(BaseModel):
    """Khung ảnh chữ ký trên trang đơn — mm, tính từ góc TRÊN-TRÁI trang."""
    page: int = 0
    x_mm: float
    y_mm: float
    w_mm: float
    h_mm: float

class LeaveCreate(BaseModel):
    start_date: date
    end_date: date
    leave_type: str = "annual"
    reason: Optional[str] = None
    ksv_approver_id: Optional[int] = None  # Bắt buộc với chuyen_vien/pho_phong/truong_phong
    gd_approver_id: Optional[int] = None   # Chọn trước Ban lãnh đạo phê duyệt
    spread_dates: Optional[List[str]] = None  # YYYY-MM-DD list khi nghỉ ngày lẻ không liên tục
    signature: Optional[SignaturePlacement] = None  # Chữ ký người đề nghị đặt ở popup xem trước

class LeaveReview(BaseModel):
    action: Literal["approve", "reject"]
    comment: Optional[str] = None
    signature: Optional[SignaturePlacement] = None  # Chữ ký người duyệt (chỉ khi approve)

class TongHopReview(BaseModel):
    action: Literal["forward", "reject"]
    gd_approver_id: Optional[int] = None  # Bắt buộc khi action="forward"
    comment: Optional[str] = None

class LeaveOut(BaseModel):
    id: int
    staff_id: int
    staff_name: str
    department_name: Optional[str] = None
    start_date: date
    end_date: date
    leave_days: int
    leave_type: str
    reason: Optional[str]
    status: str
    status_label: Optional[str] = None
    adjusts_leave_id: Optional[int] = None
    adjusts_leave: Optional[dict] = None
    npbb_adjustment: Optional[dict] = None
    ksv_approver_id: Optional[int] = None
    ksv_approver_name: Optional[str] = None
    ksv_approved_at: Optional[datetime] = None
    ksv_comment: Optional[str] = None
    tong_hop_approver_id: Optional[int] = None
    tong_hop_approver_name: Optional[str] = None
    tong_hop_approved_at: Optional[datetime] = None
    tong_hop_comment: Optional[str] = None
    gd_approver_id: Optional[int] = None
    gd_approver_name: Optional[str] = None
    gd_is_pgd: bool = False              # True nếu người ký là PGĐ → hiện (TUQ)
    gd_approved_at: Optional[datetime] = None
    gd_comment: Optional[str] = None
    is_direct: bool = False
    spread_dates: Optional[List[str]] = None
    recall_reason: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class LeaveActionLogOut(BaseModel):
    id: int
    actor_name: str
    action: str
    action_label: str
    comment: Optional[str]
    from_status: Optional[str]
    to_status: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ─── Quota & Direct ──────────────────────────────────────────────────────────
class LeaveQuotaUpsert(BaseModel):
    staff_id: int
    year: int
    quota_days: float

class LeaveQuotaOut(BaseModel):
    staff_id: int
    staff_name: str
    year: int
    quota_days: float
    carry_over: float = 0.0
    used_days: float = 0.0
    remaining: float = 0.0
    model_config = ConfigDict(from_attributes=True)

class DirectLeaveCreate(BaseModel):
    staff_id: int
    start_date: date
    end_date: date
    leave_type: str = "annual"
    reason: Optional[str] = None
    spread_dates: Optional[List[str]] = None

class RecallCreate(BaseModel):
    reason: str


class DelegationCreate(BaseModel):
    giam_doc_id: int
    pho_giam_doc_id: int
    start_date: date
    end_date: date
    note: Optional[str] = None

class DelegationOut(BaseModel):
    id: int
    giam_doc_id: int
    giam_doc_name: str
    pho_giam_doc_id: int
    pho_giam_doc_name: str
    start_date: date
    end_date: date
    note: Optional[str]
    is_active: bool
    created_by_name: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
