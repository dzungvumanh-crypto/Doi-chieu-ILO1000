"""Quản lý nhân sự — đặc tả phân hệ, chuẩn hoá dữ liệu, thống kê & nhắc lịch.

Hồ sơ nhân sự khoá theo `user_tttt.id`: không có danh sách cán bộ riêng, mỗi
tài khoản là một hồ sơ. Họ tên / phòng / ngày vào ngành vẫn chỉ nằm ở
`user_tttt`, module này chỉ bổ sung phần hồ sơ.

Bảy phân hệ con (bằng cấp, bổ nhiệm, quá trình công tác, nghỉ gián đoạn, lương,
đào tạo, công cụ) có cùng một hình dạng: danh sách dòng gắn với một cán bộ.
Thay vì 7 bộ schema + 28 route giống hệt nhau, mô tả chúng bằng `SECTIONS` rồi
dùng chung một bộ CRUD — thêm cột chỉ là thêm một dòng ở đây, backend và form
nhập liệu ngoài giao diện tự có cột mới.
"""
import unicodedata
from datetime import date, timedelta

# ── Quản trị viên không có hồ sơ nhân sự ─────────────────────────────────────
# `admin` / `admin_l2` là tài khoản HỆ THỐNG, không phải cán bộ nghiệp vụ: không
# thuộc phòng nào (chọn vai trò quản trị ở màn Quản lý User là ô Phòng bị ẩn),
# không tham gia quy trình nghỉ phép, không có ngày tuyển dụng hay bậc lương của
# Trung tâm. Để họ lẫn trong danh sách hồ sơ thì mọi con số "tổng số cán bộ" đều
# lệch và người làm nhân sự phải nhớ tự trừ ra.
ROLES_KHONG_HO_SO = ("admin", "admin_l2")

# Mảnh WHERE dùng chung cho mọi truy vấn có bí danh bảng là `u` — sinh từ hằng ở
# trên, không gõ lại danh sách vai trò ở từng câu SQL.
SQL_CHI_CAN_BO = "u.role NOT IN ({})".format(
    ", ".join(f"'{r}'" for r in ROLES_KHONG_HO_SO))


# ── Nhãn giá trị chọn ────────────────────────────────────────────────────────
GIOI_TINH = {"nam": "Nam", "nu": "Nữ", "khac": "Khác"}

LOAI_BANG_CAP = {
    "trinh_do":  "Trình độ chuyên môn",
    "ngoai_ngu": "Chứng chỉ ngoại ngữ",
    "tin_hoc":   "Chứng chỉ tin học",
    "khac":      "Chứng chỉ khác",
}

LOAI_BO_NHIEM = {
    "quy_hoach":   "Quy hoạch",
    "bo_nhiem":    "Bổ nhiệm",
    "bo_nhiem_lai": "Bổ nhiệm lại",
    "dieu_dong":   "Điều động",
    "mien_nhiem":  "Miễn nhiệm",
}

HINH_THUC_DAO_TAO = {"online": "Online", "offline": "Offline"}

TRANG_THAI_CCDC = {
    "dang_dung":  "Đang sử dụng",
    "da_chuyen":  "Đã chuyển người khác",
    "da_tra":     "Đã trả văn phòng",
    "moi_cap":    "Mới được cấp — TSC chưa cập nhật",
}


def _f(kieu: str, nhan: str, bat_buoc: bool = False, chon: dict | None = None,
       mac_dinh=None) -> dict:
    """`mac_dinh` áp khi ô để trống — cả `chuan_hoa()` lẫn form ngoài giao diện
    cùng đọc, nên giá trị mặc định chỉ khai một chỗ."""
    return {"kieu": kieu, "nhan": nhan, "bat_buoc": bat_buoc, "chon": chon,
            "mac_dinh": mac_dinh}


# ── Đặc tả 7 phân hệ dạng danh sách ──────────────────────────────────────────
# order_by dùng nguyên trong câu SQL nên chỉ được viết ở đây, không nhận từ client.
SECTIONS: dict[str, dict] = {
    "degrees": {
        "table": "hr_degrees",
        "nhan": "Hồ sơ bằng cấp",
        "order_by": "IFNULL(issue_date, '') DESC, id DESC",
        "tu_sua": True,          # cán bộ tự khai bằng cấp của mình
        "fields": {
            "kind":        _f("enum", "Loại", True, LOAI_BANG_CAP),
            "name":        _f("text", "Tên bằng / chứng chỉ", True),
            "major":       _f("text", "Chuyên ngành"),
            "school":      _f("text", "Nơi đào tạo / cấp"),
            "issue_date":  _f("date", "Ngày cấp"),
            "expiry_date": _f("date", "Có giá trị đến"),
            "grade":       _f("text", "Xếp loại / kết quả"),
            "note":        _f("text", "Ghi chú"),
        },
    },
    "appointments": {
        "table": "hr_appointments",
        "nhan": "Quy hoạch, bổ nhiệm, điều động",
        "order_by": "IFNULL(effective_from, IFNULL(decision_date, '')) DESC, id DESC",
        "tu_sua": False,
        "fields": {
            "kind":           _f("enum", "Loại", True, LOAI_BO_NHIEM),
            "position":       _f("text", "Chức vụ", True),
            "unit":           _f("text", "Đơn vị"),
            "decision_no":    _f("text", "Số quyết định"),
            "decision_date":  _f("date", "Ngày quyết định"),
            "effective_from": _f("date", "Hiệu lực từ"),
            "effective_to":   _f("date", "Hiệu lực đến"),
            "note":           _f("text", "Ghi chú"),
        },
    },
    "work-history": {
        "table": "hr_work_history",
        "nhan": "Quá trình công tác",
        "order_by": "from_date DESC, id DESC",
        "tu_sua": False,
        "fields": {
            "from_date": _f("date", "Từ ngày", True),
            "to_date":   _f("date", "Đến ngày"),
            "position":  _f("text", "Chức vụ"),
            "unit":      _f("text", "Đơn vị", True),
            "at_branch": _f("bool", "Công tác tại chi nhánh"),
            "note":      _f("text", "Ghi chú"),
        },
    },
    "breaks": {
        "table": "hr_breaks",
        "nhan": "Quá trình nghỉ gián đoạn",
        "order_by": "from_date DESC, id DESC",
        "tu_sua": False,
        "fields": {
            "from_date":       _f("date", "Từ ngày", True),
            "to_date":         _f("date", "Đến ngày", True),
            "reason":          _f("text", "Lý do"),
            # Cả phân hệ này nói về nghỉ KHÔNG hưởng lương nên ô mặc định tích sẵn
            "unpaid":          _f("bool", "Không hưởng lương", mac_dinh=True),
            "count_seniority": _f("bool", "Vẫn tính thời gian công tác"),
            "note":            _f("text", "Ghi chú"),
        },
    },
    "salaries": {
        "table": "hr_salaries",
        "nhan": "Hồ sơ lương",
        "order_by": "decision_date DESC, id DESC",
        "tu_sua": False,
        # Lương tách quyền riêng: ai xem được hồ sơ chưa chắc được xem lương.
        "quyen_xem": "hr.salary_view",
        "quyen_sua": "hr.salary_edit",
        "fields": {
            "grade":              _f("text", "Bậc lương"),
            "coef_v1":            _f("num",  "Hệ số V1"),
            "coef_v2":            _f("num",  "Hệ số V2"),
            "position_allowance": _f("num",  "Phụ cấp chức vụ"),
            "decision_no":        _f("text", "Số quyết định"),
            "decision_date":      _f("date", "Ngày quyết định nâng lương", True),
            "effective_from":     _f("date", "Hưởng từ ngày"),
            "cycle_months":       _f("int",  "Chu kỳ nâng lương (tháng)"),
            "note":               _f("text", "Ghi chú"),
        },
    },
    "trainings": {
        "table": "hr_trainings",
        "nhan": "Đào tạo tại Agribank",
        "order_by": "IFNULL(from_date, '') DESC, id DESC",
        "tu_sua": True,
        "fields": {
            "course_name": _f("text", "Tên khóa học", True),
            "from_date":   _f("date", "Từ ngày"),
            "to_date":     _f("date", "Đến ngày"),
            "mode":        _f("enum", "Hình thức", False, HINH_THUC_DAO_TAO),
            "result":      _f("text", "Kết quả"),
            "organizer":   _f("text", "Đơn vị tổ chức"),
            "note":        _f("text", "Ghi chú"),
        },
    },
    "tools": {
        "table": "hr_tools",
        "nhan": "Công cụ, dụng cụ",
        "order_by": "IFNULL(issued_date, '') DESC, id DESC",
        # Chính cán bộ đứng tên mới biết công cụ đã chuyển cho ai / đã trả chưa
        # — đó là cột "trạng thái" trong yêu cầu nghiệp vụ.
        "tu_sua": True,
        "fields": {
            "tool_name":       _f("text", "Tên công cụ, dụng cụ", True),
            "tool_code":       _f("text", "Mã tài sản"),
            "quantity":        _f("int",  "Số lượng", mac_dinh=1),
            "issued_date":     _f("date", "Ngày được cấp"),
            # Cột NOT NULL: bỏ trống thì phải rơi về "đang sử dụng", không được
            # để API gửi NULL xuống rồi vỡ ở tầng SQLite.
            "status":          _f("enum", "Trạng thái", False, TRANG_THAI_CCDC,
                                   mac_dinh="dang_dung"),
            "next_issue_date": _f("date", "Dự kiến cấp mới"),
            "note":            _f("text", "Ghi chú"),
        },
    },
}

# Phân hệ được đính kèm file (quyết định, bản scan bằng cấp)
SECTIONS_CO_FILE = frozenset(("degrees", "appointments", "salaries", "trainings"))

# ── Hồ sơ cá nhân + thông tin công tác (bảng hr_profiles, 1 dòng / cán bộ) ────
# Tách hai nhóm vì quyền khác nhau: phần "tự khai" cán bộ sửa được hồ sơ của
# chính mình; phần "công tác" (ngày tuyển dụng, loại hợp đồng, chức vụ) là số
# liệu do người làm nhân sự nhập, không để người ta tự sửa của mình.
PROFILE_FIELDS_TU_KHAI: dict[str, dict] = {
    "gender":            _f("enum", "Giới tính", False, GIOI_TINH),
    "dob":               _f("date", "Ngày sinh"),
    "cccd":              _f("text", "Số CCCD"),
    "cccd_date":         _f("date", "Ngày cấp CCCD"),
    "cccd_place":        _f("text", "Nơi cấp CCCD"),
    "permanent_address": _f("text", "Địa chỉ thường trú"),
    "current_address":   _f("text", "Chỗ ở hiện tại"),
    "dependents":        _f("int",  "Số người phụ thuộc"),
    "contact_name":      _f("text", "Người liên lạc — họ tên"),
    "contact_relation":  _f("text", "Người liên lạc — quan hệ"),
    "contact_phone":     _f("text", "Người liên lạc — điện thoại"),
    "contact_address":   _f("text", "Người liên lạc — địa chỉ"),
    "note":              _f("text", "Ghi chú"),
}

PROFILE_FIELDS_CONG_TAC: dict[str, dict] = {
    "contract_type":  _f("text", "Loại hợp đồng"),
    "position_title": _f("text", "Chức vụ hiện tại"),
}

PROFILE_FIELDS = {**PROFILE_FIELDS_TU_KHAI, **PROFILE_FIELDS_CONG_TAC}

# ── Trường nằm ở `user_tttt`, hồ sơ chỉ mượn để hiện và sửa ──────────────────
# Không tạo bản thứ hai trong hr_profiles: hai bản sao của cùng một số điện
# thoại (hay cùng một ngày vào ngành) chắc chắn lệch nhau, mà cột ở user_tttt
# mới là cột cả hệ thống đang dùng.
PROFILE_FIELDS_TAI_KHOAN = {
    "phone": _f("text", "Điện thoại"),
    "email": _f("text", "Email"),
}

# `Ngày tuyển dụng` CHÍNH LÀ `Ngày vào ngành` (`user_tttt.join_industry_date`) —
# một mốc, một cột. Trước đây hr_profiles có thêm cột `recruit_date` riêng: hai ô
# cùng nghĩa nằm hai màn hình, nhập lệch nhau là không ai biết ô nào đúng.
#
# Tách khỏi nhóm "tự khai" dù cũng ghi vào user_tttt: cột này quyết định SỐ NGÀY
# PHÉP NĂM (`compute_annual_leave()` — 12 ngày + 1 ngày mỗi 5 năm). Để cán bộ tự
# sửa của mình là để họ tự cộng phép cho mình. Sửa được cần `hr.edit_all`, đúng
# như mọi số liệu công tác khác.
PROFILE_FIELDS_TAI_KHOAN_HR = {
    "join_industry_date": _f("date", "Ngày tuyển dụng (ngày vào ngành)"),
}


class LoiDuLieu(ValueError):
    """Dữ liệu người dùng gửi lên không hợp lệ — API đổi thành HTTP 400."""


# ── Chuẩn hoá & kiểm tra dữ liệu ─────────────────────────────────────────────
def _doc_ngay(gia_tri, nhan: str) -> str | None:
    """'2026-08-28' hoặc '28/08/2026' → '2026-08-28'. Rỗng → None."""
    if gia_tri is None:
        return None
    s = str(gia_tri).strip()
    if not s:
        return None
    if "/" in s:
        phan = s.split("/")
        if len(phan) == 3 and all(p.strip().isdigit() for p in phan):
            d, m, y = (int(p) for p in phan)
            s = f"{y:04d}-{m:02d}-{d:02d}"
    try:
        return date.fromisoformat(s).isoformat()
    except ValueError:
        raise LoiDuLieu(f"{nhan}: '{gia_tri}' không phải ngày hợp lệ (dd/mm/yyyy)")


def _doc_so(gia_tri, nhan: str, nguyen: bool):
    if gia_tri is None or str(gia_tri).strip() == "":
        return None
    try:
        so = float(str(gia_tri).replace(",", "."))
    except ValueError:
        raise LoiDuLieu(f"{nhan}: '{gia_tri}' không phải số")
    if nguyen:
        if so != int(so):
            raise LoiDuLieu(f"{nhan}: phải là số nguyên")
        return int(so)
    return so


def chuan_hoa(fields: dict[str, dict], body: dict, mot_phan: bool = False) -> dict:
    """Lọc & ép kiểu dữ liệu gửi lên theo đặc tả `fields`.

    Trường lạ bị từ chối chứ không bỏ qua im lặng: gõ nhầm tên cột mà vẫn nhận
    200 thì người dùng tưởng đã lưu, dữ liệu thì không có ở đâu cả.
    `mot_phan=True` (PATCH) chỉ xử lý những khoá thật sự được gửi lên.
    """
    if not isinstance(body, dict):
        raise LoiDuLieu("Dữ liệu gửi lên phải là một đối tượng JSON")
    la = sorted(set(body) - set(fields))
    if la:
        raise LoiDuLieu(f"Trường không thuộc phân hệ này: {', '.join(la)}")

    ra: dict = {}
    for ten, spec in fields.items():
        if mot_phan and ten not in body:
            continue
        gia_tri = body.get(ten)
        kieu, nhan = spec["kieu"], spec["nhan"]
        if kieu == "date":
            gia_tri = _doc_ngay(gia_tri, nhan)
        elif kieu == "int":
            gia_tri = _doc_so(gia_tri, nhan, nguyen=True)
        elif kieu == "num":
            gia_tri = _doc_so(gia_tri, nhan, nguyen=False)
        elif kieu == "bool":
            gia_tri = int(bool(gia_tri))
            if not gia_tri and ten not in body and spec["mac_dinh"]:
                gia_tri = 1
        elif kieu == "enum":
            gia_tri = (str(gia_tri).strip() or None) if gia_tri is not None else None
            if gia_tri is not None and gia_tri not in spec["chon"]:
                raise LoiDuLieu(f"{nhan}: giá trị '{gia_tri}' không hợp lệ")
        else:
            gia_tri = (str(gia_tri).strip() or None) if gia_tri is not None else None
        if gia_tri is None and spec["mac_dinh"] is not None:
            gia_tri = spec["mac_dinh"]
        if spec["bat_buoc"] and gia_tri in (None, ""):
            raise LoiDuLieu(f"Thiếu {nhan}")
        ra[ten] = gia_tri

    # Khoảng thời gian ngược đầu đuôi là lỗi nhập liệu, không phải dữ liệu hiếm
    for dau, cuoi in (("from_date", "to_date"), ("effective_from", "effective_to")):
        if ra.get(dau) and ra.get(cuoi) and ra[cuoi] < ra[dau]:
            raise LoiDuLieu(
                f"{fields[cuoi]['nhan']} không được trước {fields[dau]['nhan']}")
    return ra


# ── Trình độ: xếp hạng để thống kê "trình độ cao nhất" ───────────────────────
# Người nhập gõ tay ("Đại học", "ĐH Kinh tế quốc dân", "Thạc sỹ"...) nên phải dò
# theo từ khoá, không tra bảng mã. Không khớp từ khoá nào → nhóm "Khác", KHÔNG
# im lặng gán bừa một bậc.
_BAC_TRINH_DO = [
    (4, "Tiến sĩ",   ("tien si", "tien sy", "phd")),
    (3, "Thạc sĩ",   ("thac si", "thac sy", "cao hoc", "master")),
    (2, "Đại học",   ("dai hoc", "cu nhan", "ky su", "dh")),
    (1, "Cao đẳng",  ("cao dang", "cd")),
    (0, "Trung cấp", ("trung cap", "so cap")),
]


def bo_dau(s: str) -> str:
    """'Thạc sĩ' → 'thac si'. Dùng để dò từ khoá bất kể người nhập gõ có dấu hay không."""
    s = unicodedata.normalize("NFD", str(s or "").casefold())
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.replace("đ", "d")


def khoa_ten(ho_ten: str) -> tuple:
    """Khoá sắp xếp danh sách người, theo lối gọi tên tiếng Việt: **TÊN trước**
    (chữ cuối), rồi tới họ và đệm.

    Không dùng `ORDER BY full_name` của SQLite: nó so sánh theo MÃ BYTE, mà mọi
    chữ cái có dấu đều nằm sau 'z' trong bảng mã. Hậu quả đo được trên dữ liệu
    thật: cả Phòng Thanh toán 25 người thì "Đào Tiến Thành", "Đoàn Thị Huyền
    Trang", "Đặng Thị Hương Ly" bị dồn xuống 3 dòng cuối, sau "Vũ Văn Ngân";
    "Hà Phương Thu" đứng sau "Hoàng Thị Lan Anh"; "Tạ", "Tô", "Từ" đứng sau
    "Trần". Người tra danh sách theo vần không thấy tên ở chỗ đáng lẽ phải có
    nên báo "hệ thống lấy thiếu người" — không sai dữ liệu, chỉ sai chỗ đứng.

    Bỏ dấu trước khi so sánh nên Đ xếp cùng D, Ă/Â cùng A — đúng thứ tự bảng chữ
    cái tiếng Việt. Giữ thêm chuỗi gốc làm khoá cuối để thứ tự luôn ổn định.
    """
    phan = bo_dau(ho_ten).split()
    if not phan:
        return ("", "", ho_ten or "")
    return (phan[-1], " ".join(phan[:-1]), ho_ten or "")


# ── Thứ tự chức vụ khi đọc danh sách một phòng ───────────────────────────────
# Lãnh đạo trước, nhân viên sau — đúng cách một danh sách nhân sự được đọc.
#
# KHÔNG dùng `ROLE_RANK` trong backend/core/enums.py: bảng đó xếp theo QUYỀN
# (hậu kiểm viên đứng TRÊN trưởng phòng vì duyệt được nhiều việc hơn) và đang
# dùng để chặn leo thang quyền. Trộn hai thứ tự vào một bảng thì sửa thứ tự hiển
# thị là vô tình đổi luật phân quyền.
NHAN_CHUC_VU = {
    "giam_doc":      "Giám đốc",
    "pho_giam_doc":  "Phó Giám đốc",
    "truong_phong":  "Trưởng phòng",
    "pho_phong":     "Phó phòng",
    "hau_kiem_vien": "Hậu kiểm viên",
    "chuyen_vien":   "Chuyên viên",
}

THU_TU_CHUC_VU = {
    "giam_doc": 0,
    "pho_giam_doc": 1,
    "truong_phong": 2,
    "pho_phong": 3,
    # Hậu kiểm viên và chuyên viên cùng bậc "nhân viên" — xếp lẫn nhau theo tên,
    # không ai trên ai.
    "hau_kiem_vien": 4,
    "chuyen_vien": 4,
}
_CHUC_VU_CUOI = 9      # vai trò lạ (dữ liệu cũ) xuống cuối, không chen vào giữa


def khoa_phong_ten(phong: str | None, ho_ten: str, role: str | None = None) -> tuple:
    """Phòng → chức vụ → tên. Người chưa có phòng xuống cuối, không lên đầu."""
    return (bo_dau(phong) if phong else "zzzz",
            THU_TU_CHUC_VU.get(role, _CHUC_VU_CUOI),
            khoa_ten(ho_ten))


def xep_trinh_do(ten: str) -> tuple[int, str]:
    """Tên bằng cấp → (bậc, nhãn). Không nhận ra thì (-1, 'Khác')."""
    phang = f" {bo_dau(ten)} "
    for bac, nhan, khoa in _BAC_TRINH_DO:
        if any(f" {k} " in phang or phang.strip().startswith(k) for k in khoa):
            return bac, nhan
    return -1, "Khác"


def nhom_tuoi(dob: str | None, moc: date) -> str | None:
    if not dob:
        return None
    try:
        ngay_sinh = date.fromisoformat(str(dob)[:10])
    except ValueError:
        return None
    tuoi = moc.year - ngay_sinh.year - ((moc.month, moc.day) < (ngay_sinh.month, ngay_sinh.day))
    if tuoi < 30:
        return "Dưới 30"
    if tuoi < 40:
        return "30 – 39"
    if tuoi < 50:
        return "40 – 49"
    return "50 trở lên"


def cong_thang(ngay: date, so_thang: int) -> date:
    """Cộng tháng theo lịch, ngày 31 rơi vào tháng ngắn thì lùi về ngày cuối tháng."""
    thang = ngay.month - 1 + so_thang
    nam = ngay.year + thang // 12
    thang = thang % 12 + 1
    ngay_cuoi = [31, 29 if (nam % 4 == 0 and nam % 100 != 0) or nam % 400 == 0 else 28,
                 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][thang - 1]
    return date(nam, thang, min(ngay.day, ngay_cuoi))


# ── Nhắc lịch ────────────────────────────────────────────────────────────────
# Ba mốc nhắc theo yêu cầu nghiệp vụ. Nhắc gồm cả việc ĐÃ QUÁ HẠN: quá hạn mà
# biến mất khỏi danh sách thì người theo dõi không bao giờ thấy việc bị bỏ sót.
TRUOC_MOT_QUY = 92
TRUOC_MOT_NAM = 365
CHU_KY_NANG_LUONG_MAC_DINH = 36     # tháng — dùng khi dòng lương không ghi chu kỳ


def _dong(loai: str, r, ngay_moc: date, hom_nay: date, mo_ta: str) -> dict:
    return {
        "loai": loai,
        "staff_id": r["staff_id"],
        "employee_code": r["employee_code"],
        "full_name": r["full_name"],
        "department": r["department"],
        "ngay_moc": ngay_moc.isoformat(),
        "con_lai": (ngay_moc - hom_nay).days,
        "mo_ta": mo_ta,
    }


def tinh_nhac_lich(db, hom_nay: date | None = None) -> list[dict]:
    """Ba nhóm nhắc: nâng lương (trước 1 quý), bổ nhiệm lại (trước 1 năm),
    cấp công cụ/điện thoại mới (trước 1 quý). Sắp xếp theo ngày mốc gần nhất."""
    hom_nay = hom_nay or date.today()
    ra: list[dict] = []

    # ── Nâng lương: dòng lương mới nhất + chu kỳ ──
    rows = db.execute(
        """SELECT s.*, u.employee_code, u.full_name, d.name AS department
           FROM hr_salaries s
           JOIN user_tttt u ON u.id = s.staff_id AND u.is_active = 1
                              AND {chi_can_bo}
           LEFT JOIN departments d ON d.id = u.department_id
           WHERE s.id = (SELECT s2.id FROM hr_salaries s2 WHERE s2.staff_id = s.staff_id
                         ORDER BY s2.decision_date DESC, s2.id DESC LIMIT 1)""".format(chi_can_bo=SQL_CHI_CAN_BO)
    ).fetchall()
    han = hom_nay + timedelta(days=TRUOC_MOT_QUY)
    for r in rows:
        try:
            moc = cong_thang(date.fromisoformat(str(r["decision_date"])[:10]),
                             int(r["cycle_months"] or CHU_KY_NANG_LUONG_MAC_DINH))
        except (ValueError, TypeError):
            continue
        if moc <= han:
            ra.append(_dong("nang_luong", r, moc, hom_nay,
                            f"Bậc {r['grade'] or '—'} từ {r['decision_date']}"))

    # ── Bổ nhiệm lại: quyết định bổ nhiệm có ngày hết hiệu lực ──
    rows = db.execute(
        """SELECT a.*, u.employee_code, u.full_name, d.name AS department
           FROM hr_appointments a
           JOIN user_tttt u ON u.id = a.staff_id AND u.is_active = 1
                              AND {chi_can_bo}
           LEFT JOIN departments d ON d.id = u.department_id
           WHERE a.kind IN ('bo_nhiem', 'bo_nhiem_lai') AND a.effective_to IS NOT NULL
             AND a.effective_to <= ?""".format(chi_can_bo=SQL_CHI_CAN_BO),
        ((hom_nay + timedelta(days=TRUOC_MOT_NAM)).isoformat(),),
    ).fetchall()
    for r in rows:
        try:
            moc = date.fromisoformat(str(r["effective_to"])[:10])
        except ValueError:
            continue
        ra.append(_dong("bo_nhiem_lai", r, moc, hom_nay,
                        f"{r['position']} — QĐ {r['decision_no'] or '—'}"))

    # ── Cấp công cụ / điện thoại mới ──
    rows = db.execute(
        """SELECT t.*, u.employee_code, u.full_name, d.name AS department
           FROM hr_tools t
           JOIN user_tttt u ON u.id = t.staff_id AND u.is_active = 1
                              AND {chi_can_bo}
           LEFT JOIN departments d ON d.id = u.department_id
           WHERE t.next_issue_date IS NOT NULL AND t.next_issue_date <= ?
             AND t.status IN ('dang_dung', 'moi_cap')""".format(chi_can_bo=SQL_CHI_CAN_BO),
        (han.isoformat(),),
    ).fetchall()
    for r in rows:
        try:
            moc = date.fromisoformat(str(r["next_issue_date"])[:10])
        except ValueError:
            continue
        ra.append(_dong("cap_moi", r, moc, hom_nay,
                        f"{r['tool_name']} — cấp ngày {r['issued_date'] or '—'}"))

    ra.sort(key=lambda x: (x["ngay_moc"], x["full_name"]))
    return ra


# ── Thống kê ─────────────────────────────────────────────────────────────────
def _dem(cap: list[tuple[str, int]]) -> list[dict]:
    return [{"nhan": k, "so_luong": v} for k, v in cap]


def tinh_thong_ke(db, hom_nay: date | None = None) -> dict:
    """Thống kê nhân sự đang hoạt động: phòng ban, giới tính, trình độ, độ tuổi,
    đã từng công tác tại chi nhánh."""
    hom_nay = hom_nay or date.today()
    rows = db.execute(
        """SELECT u.id, u.full_name, d.name AS department, p.gender, p.dob
           FROM user_tttt u
           LEFT JOIN departments d ON d.id = u.department_id
           LEFT JOIN hr_profiles p ON p.staff_id = u.id
           WHERE u.is_active = 1 AND IFNULL(u.is_deleted, 0) = 0
             AND {chi_can_bo}""".format(chi_can_bo=SQL_CHI_CAN_BO)
    ).fetchall()

    # Trình độ cao nhất mỗi người — chấm điểm bằng Python vì tên bằng do người
    # nhập gõ tay, SQL không xếp hạng được (xem xep_trinh_do).
    bac_theo_nguoi: dict[int, tuple[int, str]] = {}
    for r in db.execute(
        "SELECT staff_id, name FROM hr_degrees WHERE kind = 'trinh_do'"
    ).fetchall():
        bac = xep_trinh_do(r["name"])
        cu = bac_theo_nguoi.get(r["staff_id"])
        if cu is None or bac[0] > cu[0]:
            bac_theo_nguoi[r["staff_id"]] = bac

    da_qua_cn = {r["staff_id"] for r in db.execute(
        "SELECT DISTINCT staff_id FROM hr_work_history WHERE at_branch = 1"
    ).fetchall()}

    phong: dict[str, int] = {}
    gioi: dict[str, int] = {}
    trinh_do: dict[str, int] = {}
    tuoi: dict[str, int] = {}
    n_qua_cn = 0
    for r in rows:
        phong[r["department"] or "Chưa có phòng"] = phong.get(r["department"] or "Chưa có phòng", 0) + 1
        nhan_gioi = GIOI_TINH.get(r["gender"], "Chưa khai")
        gioi[nhan_gioi] = gioi.get(nhan_gioi, 0) + 1
        nhan_td = bac_theo_nguoi.get(r["id"], (None, "Chưa khai"))[1]
        trinh_do[nhan_td] = trinh_do.get(nhan_td, 0) + 1
        nhan_tuoi = nhom_tuoi(r["dob"], hom_nay) or "Chưa khai"
        tuoi[nhan_tuoi] = tuoi.get(nhan_tuoi, 0) + 1
        if r["id"] in da_qua_cn:
            n_qua_cn += 1

    thu_tu_tuoi = ["Dưới 30", "30 – 39", "40 – 49", "50 trở lên", "Chưa khai"]
    return {
        "tong": len(rows),
        "theo_phong":    _dem(sorted(phong.items(), key=lambda x: -x[1])),
        "theo_gioi":     _dem(sorted(gioi.items(), key=lambda x: -x[1])),
        "theo_trinh_do": _dem(sorted(trinh_do.items(), key=lambda x: -x[1])),
        "theo_tuoi":     _dem([(k, tuoi[k]) for k in thu_tu_tuoi if k in tuoi]),
        "qua_chi_nhanh": [
            {"nhan": "Đã từng công tác tại chi nhánh", "so_luong": n_qua_cn},
            {"nhan": "Chưa qua chi nhánh", "so_luong": len(rows) - n_qua_cn},
        ],
    }


# ── Danh sách cán bộ tại một thời điểm ───────────────────────────────────────
NHOM_TRA_CUU = {
    "tat_ca":       "Toàn Trung tâm",
    "bgd":          "Ban Giám đốc",
    "truong_phong": "Trưởng phòng",
    "pho_phong":    "Phó phòng",
    "quy_hoach":    "Cán bộ trong quy hoạch",
}


def tra_cuu_danh_sach(db, nhom: str = "tat_ca", moc: date | None = None,
                      department_id: int | None = None) -> list[dict]:
    """Danh sách cán bộ theo nhóm, tại thời điểm `moc`.

    Phòng tại thời điểm lấy từ `staff_department_history` (bảng đã có sẵn từ
    tính năng đổi phòng), KHÔNG lấy `user_tttt.department_id` — cột đó chỉ nói
    phòng HIỆN TẠI nên tra ngày cũ sẽ ra kết quả của hôm nay.

    Chức vụ / quy hoạch tại thời điểm đọc từ `hr_appointments`: quyết định có
    hiệu lực bao trùm `moc` (chưa ghi ngày hết hiệu lực coi như còn hiệu lực).
    """
    moc = moc or date.today()
    m = moc.isoformat()
    rows = db.execute(
        """SELECT u.id AS staff_id, u.employee_code, u.full_name, u.role,
                  IFNULL(dh.name, d.name) AS department,
                  IFNULL(dh.id, d.id)     AS department_id,
                  p.position_title, p.gender, p.dob
           FROM user_tttt u
           LEFT JOIN departments d ON d.id = u.department_id
           LEFT JOIN hr_profiles p ON p.staff_id = u.id
           LEFT JOIN departments dh ON dh.id = (
                SELECT h.department_id FROM staff_department_history h
                WHERE h.staff_id = u.id AND h.effective_from <= ?
                ORDER BY h.effective_from DESC, h.id DESC LIMIT 1)
           WHERE u.is_active = 1 AND IFNULL(u.is_deleted, 0) = 0
             AND {chi_can_bo}
           ORDER BY IFNULL(dh.name, d.name)""".format(chi_can_bo=SQL_CHI_CAN_BO),
        (m,),
    ).fetchall()

    # Quyết định còn hiệu lực tại thời điểm tra cứu, gom theo cán bộ
    qd: dict[int, list] = {}
    for r in db.execute(
        """SELECT staff_id, kind, position, unit, decision_no, effective_from, effective_to
           FROM hr_appointments
           WHERE IFNULL(effective_from, IFNULL(decision_date, '0001-01-01')) <= ?
             AND (effective_to IS NULL OR effective_to >= ?)""",
        (m, m),
    ).fetchall():
        qd.setdefault(r["staff_id"], []).append(r)

    ra = []
    for r in rows:
        if department_id and r["department_id"] != department_id:
            continue
        cua_toi = qd.get(r["staff_id"], [])
        chuc_vu = next((q["position"] for q in cua_toi
                        if q["kind"] in ("bo_nhiem", "bo_nhiem_lai")), None)
        quy_hoach = [q["position"] for q in cua_toi if q["kind"] == "quy_hoach"]
        if nhom == "bgd" and r["role"] not in ("giam_doc", "pho_giam_doc"):
            continue
        if nhom == "truong_phong" and r["role"] != "truong_phong":
            continue
        if nhom == "pho_phong" and r["role"] != "pho_phong":
            continue
        if nhom == "quy_hoach" and not quy_hoach:
            continue
        ra.append({
            "staff_id":      r["staff_id"],
            "employee_code": r["employee_code"],
            "full_name":     r["full_name"],
            "department":    r["department"],
            "role":          r["role"],
            # Chức vụ ưu tiên quyết định bổ nhiệm còn hiệu lực; chưa nhập quyết
            # định thì dùng chức vụ khai trong hồ sơ.
            "chuc_vu":       chuc_vu or r["position_title"],
            "quy_hoach":     ", ".join(quy_hoach) or None,
            "gender":        GIOI_TINH.get(r["gender"]),
            "dob":           r["dob"],
        })
    # Sắp tên bằng Python, không bằng ORDER BY — xem khoa_ten()
    ra.sort(key=lambda x: khoa_phong_ten(x["department"], x["full_name"], x["role"]))
    return ra
