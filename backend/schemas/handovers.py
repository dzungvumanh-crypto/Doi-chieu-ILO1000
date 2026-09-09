from datetime import date
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field

from .staff import StaffOut


# ─── Document Entry ──────────────────────────────────────────────────────────
# Dùng bởi backend/schemas/bundles.py (BundleItemOut.entry)
class DocumentEntryOut(BaseModel):
    id: int
    staff_id: Optional[int] = None
    transaction_date: date
    sheet_count: int
    notes: Optional[str]
    staff: Optional[StaffOut] = None
    model_config = ConfigDict(from_attributes=True)


# ─── Grid ────────────────────────────────────────────────────────────────────
class GridEntryOut(BaseModel):
    staff_id: int
    day: int
    sheet_count: int
    entry_id: Optional[int] = None
    entry_status: str = "confirmed"         # pending_confirm | confirmed | borrowed
    entered_by_name: Optional[str] = None   # Tên người nhập

class GridResponse(BaseModel):
    users: List[StaffOut]
    entries: List[GridEntryOut]
    days_in_month: int
    # Ngày trong tháng là ngày nghỉ lễ (1..days_in_month) — lưới tô vàng như T7/CN
    holidays: List[int] = []

class EntryUpsertRequest(BaseModel):
    staff_id: int
    date: date
    sheet_count: int = Field(ge=0)
    # Chỉ bắt buộc khi xoá ô đã chốt (sheet_count=0 trên ô confirmed/borrowed)
    reason: Optional[str] = None

class BorrowRequest(BaseModel):
    reason: str

class HandbackRequest(BaseModel):
    sheet_count: int = Field(gt=0)

class RejectRequest(BaseModel):
    reason: str

class ReturnToStaffRequest(BaseModel):
    reason: str


# ─── Entry History ────────────────────────────────────────────────────────────
class EntryHistoryItem(BaseModel):
    id: int
    action: str                         # key enum
    action_label: str                   # mô tả tiếng Việt
    action_color: str                   # blue | green | orange | purple
    performed_by: str                   # full_name
    performed_by_role: str              # vai trò + phòng
    timestamp: str                      # "HH:MM:SS DD/MM/YYYY"
    old_sheet_count: Optional[int] = None
    new_sheet_count: Optional[int] = None

class EntryHistoryOut(BaseModel):
    entry_id: int
    source_user_name: str
    transaction_date: str               # "DD/MM/YYYY"
    submit_date: Optional[str] = None   # "DD/MM/YYYY" — ngày nộp thật, None nếu không có log
    sheet_count: int
    current_status: str
    current_status_label: str
    borrow_reason: Optional[str] = None
    logs: List[EntryHistoryItem]


# ─── Archive ─────────────────────────────────────────────────────────────────
class ArchiveRecord(BaseModel):
    ngay_mo: str
    ngay_kt: str
    tieu_de: str

class HandoverArchiveResponse(BaseModel):
    records: List[ArchiveRecord]
    total: int
