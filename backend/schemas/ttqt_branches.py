"""Schemas cho Danh sách CN thực hiện TTQT."""
import unicodedata
from typing import Optional
from pydantic import BaseModel, field_validator


def _clean(v: Optional[str]) -> Optional[str]:
    """Chuỗi rỗng / toàn khoảng trắng → None để cột trống trong DB là NULL,
    không lẫn lộn '' với NULL khi lọc và xuất Excel.

    Kèm chuẩn hoá NFC để mọi bản ghi — dù nhập tay hay nhập từ Excel — cùng một
    dạng Unicode; nếu không, tìm theo tên sẽ trượt đúng những dòng lệch dạng."""
    if v is None:
        return None
    v = unicodedata.normalize("NFC", str(v)).strip()
    return v or None


class BranchBase(BaseModel):
    ma_cn: str
    ten_cn: str
    swift_bic: Optional[str] = None
    loai_cn: Optional[int] = None
    duoc_phep: Optional[str] = None
    cn_quan_ly: Optional[str] = None
    ghi_chu: Optional[str] = None
    sdt: Optional[str] = None
    dia_chi: Optional[str] = None
    dia_chi_en: Optional[str] = None
    is_closed: bool = False

    @field_validator("swift_bic")
    @classmethod
    def _upper_bic(cls, v):
        v = _clean(v)
        return v.upper() if v else None

    @field_validator("duoc_phep", "cn_quan_ly", "ghi_chu", "sdt", "dia_chi", "dia_chi_en")
    @classmethod
    def _strip_optional(cls, v):
        return _clean(v)

    @field_validator("ma_cn", "ten_cn")
    @classmethod
    def _require(cls, v):
        v = _clean(v)
        if not v:
            raise ValueError("Không được để trống")
        return v


class BranchCreate(BranchBase):
    pass


class BranchUpdate(BranchBase):
    pass


class BranchOut(BranchBase):
    id: int
    sort_order: Optional[int] = None
    updated_at: Optional[str] = None


class ImportResult(BaseModel):
    inserted: int
    updated: int
    deleted: int
    skipped: int
    errors: list[str] = []


class HistoryOut(BaseModel):
    """Một dòng lịch sử = một trường đã đổi (hoặc một lần thêm/xoá cả bản ghi)."""
    id: int
    created_at: Optional[str] = None
    actor_name: Optional[str] = None
    action: str
    action_label: str
    field: Optional[str] = None
    field_label: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
