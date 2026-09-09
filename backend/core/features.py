"""Feature codes cho hệ thống phân quyền theo nhóm.

Mỗi code map tới 1 tính năng UI cụ thể. Backend RBAC (deps.py) không thay đổi.
Admin role luôn bypass toàn bộ feature check.
"""

# ── Feature codes ─────────────────────────────────────────────────────────────
# format: "category.action" — lowercase, dấu chấm phân cách

FEATURES: dict[str, str] = {
    # Sidebar menus
    "menu.handovers":          "Bàn giao chứng từ (menu)",
    "menu.bundles":            "Đóng chứng từ (menu)",
    "menu.storage":            "Lưu trữ (menu)",
    # Giữ nguyên code "menu.reports" — đổi code sẽ mất quyền đã gán trong group_features
    "menu.reports":            "Báo cáo hậu kiểm (menu)",
    "menu.handover_reports":   "Báo cáo bàn giao chứng từ (menu)",
    "menu.leaves":             "Nghỉ phép (menu)",
    # Hậu tố phòng đã bỏ: màn phân quyền có dải nhãn "Phòng Tổng hợp" ngay trên
    # mục này rồi, để lại sẽ đọc thành "Phòng Tổng hợp / … — Phòng TH".
    "menu.th_reports":         "Báo cáo dữ liệu thanh toán (menu)",
    "menu.staff":              "Quản lý User (menu)",
    "menu.logs":               "Nhật ký hệ thống (menu)",
    "menu.ttqt_branches":      "Danh sách CN TTQT (menu)",

    # Bàn giao chứng từ — thao tác
    "handovers.save_entry":    "Lưu số tờ chứng từ",
    "handovers.confirm_entry": "Xác nhận cho mượn / đã nhận",
    "handovers.reject_entry":  "Từ chối bàn giao",
    "handovers.borrow":        "Mượn lại chứng từ",
    "handovers.handback":      "Bàn giao lại chứng từ",
    # Giữ nguyên code "handovers.return_entry" — đổi code sẽ mất quyền đã gán trong group_features
    "handovers.return_entry":  "Chuyển trả chứng từ cho GDV",

    # Đóng chứng từ — thao tác
    "bundles.generate":        "Tạo bìa chứng từ",
    "bundles.download_cover":  "Tải xuống bìa",
    "bundles.mark_printed":    "Đánh dấu đã in",
    "bundles.delete":          "Xóa nhóm bìa",

    # Nghỉ phép — thao tác
    "leaves.create":           "Tạo đơn nghỉ phép",
    "leaves.cancel":           "Huỷ đơn nghỉ phép",
    "leaves.resubmit":         "Sửa & Nộp lại đơn",
    "leaves.approve_ksv":      "Duyệt / Từ chối (bước KSV)",
    "leaves.forward_th":       "Chuyển GĐ/PGĐ / Từ chối (bước Tổng hợp)",
    "leaves.approve_gd":       "Duyệt / Từ chối (bước Giám đốc)",
    "leaves.dashboard":        "Dashboard nghỉ phép (tổng quan + thống kê)",
    "leaves.quota_admin":      "Quản lý hạn mức phép theo năm",
    "leaves.delegation_admin": "Quản lý ủy quyền GĐ/PGĐ",
    "leaves.stats_export":     "Xuất báo cáo tổng hợp phép năm",
    "leaves.declare_direct":   "Khai báo hộ nghỉ phép",
    "leaves.recall":           "Rút đơn nhiều cấp",

    # Danh sách CN TTQT — thao tác
    "ttqt_branches.create":    "Thêm chi nhánh",
    "ttqt_branches.edit":      "Sửa chi nhánh",
    "ttqt_branches.delete":    "Xoá chi nhánh",
    "ttqt_branches.import":    "Nhập danh sách từ Excel",
    "ttqt_branches.export":    "Xuất danh sách ra Excel",
    "ttqt_branches.history":   "Xem lịch sử sửa đổi",

    # Quản lý User — thao tác
    "staff.create":            "Tạo tài khoản mới",
    "staff.edit":              "Chỉnh sửa nhân viên",
    "staff.delete":            "Xóa nhân viên",
    "staff.export":            "Xuất Excel / DB",
    "staff.import_db":         "Nhập DB",
    "staff.import_join_date":  "Nhập Ngày vào ngành từ Excel",

    # Phân lịch trực — Phòng Thanh toán
    "menu.duty_schedule":      "Phân lịch trực (menu)",   # dải nhãn "Phòng Thanh toán" đã nói phòng
    "duty.generate":           "Tạo lịch trực tự động",
    "duty.confirm":            "Xác nhận lịch trực",
    "duty.delete":             "Xóa lịch trực",
    "duty.export":             "Xuất Excel lịch trực",
    "duty.manage_staff":       "Quản lý nhân viên phân lịch (can_do_sp, is_on_project...)",
    "duty.manage_config":      "Cài đặt ca trực / ngày đặc biệt",

    # Chấm 459901 — Phòng Thanh toán
    "menu.cham_459901":    "Chấm 459901 — Phân loại bút toán TK 459901 (menu)",
    "cham_459901.process": "Xử lý file 459901 (ZIP hoặc Excel)",

    # Đối chiếu Song phương — Phòng Thanh toán
    "menu.doi_chieu_song_phuong":    "Đối chiếu Song phương — Định tuyến lệnh IPCAS (menu)",
    "doi_chieu_song_phuong.process": "Xử lý file ZIP Đối chiếu Song phương",
    # "Đối chiếu đến" (Kênh↔Hub + Hub↔Core, 2026-09-01) — tab riêng trong cùng menu
    # doi_chieu_song_phuong ở trên, tách quyền chạy khỏi quyền xem giống cham_ach.process.
    "doi_chieu_song_phuong_kenh_core.process": "Chạy \"Đối chiếu đến\" (Kênh↔Hub + Hub↔Core)",
    # "Đối chiếu đi" (Kênh↔Hub + Hub↔Core, 2026-09-03) — tab riêng thứ 2, mã HOÀN TOÀN MỚI,
    # chưa nhóm nào có sẵn — PHẢI cấp tay sau deploy (xem Logs_update.md), giống bài học PR#70.
    "doi_chieu_song_phuong_kenh_core_di.process": "Chạy \"Đối chiếu đi\" (Kênh↔Hub + Hub↔Core)",
    # Chấm ILO1000 — Phòng Thanh toán. Module đang xây dựng, chưa hoàn thiện (BO xác
    # nhận 2026-08-31: chưa từng có ai kể cả admin dùng được do thiếu đúng mã này —
    # không tách quyền xem/chạy riêng vì code hiện tại (5 endpoint + frontend) chỉ
    # dùng đúng 1 mã, chưa có chỗ nào cần phân biệt).
    "menu.cham_ilo1000": "Chấm ILO1000 — Đối chiếu 4 nguồn (menu)",
    # Chấm đối chiếu ACH — Phòng Thanh toán. Mã đổi từ `menu.doi_chieu_ach` khi
    # module `doi_chieu_ach` cũ được thay bằng `backend/services/ach/` — code ACH
    # (backend/api/ach.py, frontend/pages/cham_ach.py) đòi đúng mã `menu.cham_ach`.
    "menu.cham_ach":            "Chấm đối chiếu ACH (menu)",
    "cham_ach.process":         "Chạy đối chiếu ACH",
    # Đối chiếu CITAD ↔ PaymentHub — Phòng Thanh toán
    # Nhãn phải khớp tên menu ở frontend/shared.py, phần mô tả sau dấu — mới
    # nói rõ đối chiếu/đối soát với hệ thống nào.
    "menu.doi_chieu_citad":     "Đối chiếu CITAD cuối ngày — CITAD ↔ PaymentHub (menu)",
    # Đối chiếu CITAD ↔ PaymentHub — Phòng QLTK Nostro, Vostro. Module SONG
    # SONG với menu.doi_chieu_citad ở trên, không phải phân hệ con của nó —
    # nghiệp vụ/nguồn dữ liệu khác hẳn (xem doi_chieu_citad_nostro_service.py).
    "menu.doi_chieu_citad_nostro": "Đối chiếu CITAD - PaymentHub — Phòng QLTK Nostro, Vostro (menu)",
    # Đối soát CITAD ↔ IPCAS — Phòng Thanh toán
    "menu.doi_soat_citad":      "Đối soát chênh lệch CITAD cuối ngày — CITAD ↔ IPCAS (menu)",
    # Sổ trực cuối ngày — Phòng Thanh toán
    "menu.so_truc":             "Sổ trực cuối ngày (menu)",
    "so_truc.ksv_confirm":      "Xác nhận / Từ chối sổ trực (vai KSV)",
    # Đối chiếu điện SWIFT — hậu tố phòng bỏ vì đã có dải nhãn "Phòng Swift"
    "menu.swift_recon":        "Đối chiếu điện SWIFT (menu)",

    # Đối chiếu DTBB — Phòng Kế toán. "menu.dtbb" mở màn hình + mọi thao tác
    # tính/lưu/xoá/xuất (mọi người có quyền dùng như nhau). Bước XÁC NHẬN (vàng→xanh)
    # và bỏ xác nhận tách riêng "dtbb.confirm" vì đó là chốt số liệu của người kiểm
    # soát, không phải việc thường ngày. Cả hai đều check thật ở backend/api/dtbb.py.
    "menu.dtbb":     "Đối chiếu DTBB (menu)",
    "dtbb.confirm":  "Xác nhận / Bỏ xác nhận kỳ DTBB",

    # Chấm công — Phòng Kế toán. "menu.attendance" điều khiển việc hiện menu và mở
    # màn hình (sidebar + attendance.py). 2 action dưới là quyền cộng thêm trong màn:
    # xem bảng công cả phòng và xuất Excel — người chỉ có menu chỉ thấy "Công của tôi".
    "menu.attendance":       "Chấm công (menu)",
    "attendance.view_dept":  "Xem bảng công cả phòng + lịch sử các tháng",
    "attendance.export":     "Xuất Excel bảng công",

    # Ôn tập (Quizz) — bộ câu hỏi dùng chung cho cả cơ quan.
    # Xem/làm bài mở cho mọi người được cấp `menu.quiz`; tải bộ mới và xoá bộ
    # là hai quyền riêng vì chúng động tới dữ liệu dùng chung: xoá một bộ kéo
    # theo toàn bộ lượt làm bài và bảng xếp hạng của bộ đó.
    "menu.quiz":             "Ôn tập (menu)",
    "quiz.upload":           "Tải bộ câu hỏi lên / đổi tên bộ",
    "quiz.delete":           "Xoá bộ câu hỏi",

    # Chuẩn hoá văn bản — dùng chung cả cơ quan. Tách quyền sửa quy chuẩn ra
    # riêng: thông số trình bày là của cả đơn vị, một người đổi là mọi văn bản
    # người khác chạy sau đó đều theo số mới — không để chung với quyền dùng.
    "menu.vb_format":        "Chuẩn hoá văn bản (menu)",
    "vb_format.config":      "Sửa thông số quy chuẩn trình bày",

    # Quản lý nhân sự. `menu.hr_profiles` là quyền TỐI THIỂU: có nó là vào được
    # màn hình và tự khai hồ sơ của chính mình. Muốn thấy/sửa hồ sơ người khác
    # phải có thêm hr.view_all / hr.edit_all. Lương tách riêng hai mã vì đó là
    # số liệu chế độ, không đi kèm quyền xem hồ sơ thông thường.
    "menu.hr_profiles":      "Hồ sơ cán bộ (menu)",
    "hr.view_all":           "Xem hồ sơ của mọi cán bộ",
    "hr.edit_all":           "Sửa hồ sơ cán bộ khác + phần công tác, bổ nhiệm",
    "hr.salary_view":        "Xem hồ sơ lương của cán bộ khác",
    "hr.salary_edit":        "Sửa hồ sơ lương",
    "menu.hr_lookup":        "Tra cứu & Thống kê nhân sự (menu)",
    "hr.export":             "Xuất Excel danh sách cán bộ",
    "menu.hr_reminders":     "Nhắc lịch nhân sự (menu)",
}

# ── Cấu trúc màn hình phân quyền ──────────────────────────────────────────────
# Gom theo CHỨC NĂNG, soi gương cây menu sidebar (`MENU_TREE` trong
# frontend/shared.py) — admin nhìn màn phân quyền thấy đúng thứ user sẽ thấy.
#
# Hai loại phần tử cấp 1, phân biệt bằng khoá "kind":
#   kind="group" → thẻ có header. "sections" gom menu theo phòng;
#                  label=None nghĩa là không cần dải nhãn phòng.
#   kind="menu"  → thẻ không header, chính ô tick là tiêu đề thẻ. Dùng cho menu
#                  đứng một mình ở cấp 1 sidebar; nếu bọc header sẽ ra
#                  "Danh sách CN TTQT / Danh sách CN TTQT" — nhãn lặp hai lần.
#
# "actions": [] = menu chỉ có một ô tick, không có mục con.
FEATURE_GROUPS: list[dict] = [
    {
        "kind": "group",
        "dept": "Quản lý chứng từ",
        "icon": "folder_copy",
        "sections": [
            {
                "label": None,
                "menus": [
                    {
                        "code": "menu.handovers",
                        "actions": [
                            "handovers.save_entry",
                            "handovers.confirm_entry",
                            "handovers.reject_entry",
                            "handovers.borrow",
                            "handovers.handback",
                            "handovers.return_entry",
                        ],
                    },
                    {
                        "code": "menu.bundles",
                        "actions": [
                            "bundles.generate",
                            "bundles.download_cover",
                            "bundles.mark_printed",
                            "bundles.delete",
                        ],
                    },
                    {"code": "menu.storage", "actions": []},
                ],
            },
        ],
    },
    {
        "kind": "group",
        "dept": "Đối chiếu",
        "icon": "compare_arrows",
        "sections": [
            {
                "label": "Phòng Thanh toán",
                "menus": [
                    {"code": "menu.cham_459901", "actions": ["cham_459901.process"]},
                    {
                        "code": "menu.doi_chieu_song_phuong",
                        "actions": [
                            "doi_chieu_song_phuong.process",
                            "doi_chieu_song_phuong_kenh_core.process",
                            "doi_chieu_song_phuong_kenh_core_di.process",
                        ],
                    },
                    {"code": "menu.cham_ach", "actions": ["cham_ach.process"]},
                    {"code": "menu.cham_ilo1000", "actions": []},
                    {"code": "menu.doi_chieu_citad", "actions": []},
                    {"code": "menu.doi_soat_citad", "actions": []},
                ],
            },
            {
                "label": "Phòng Swift",
                "menus": [
                    {"code": "menu.swift_recon", "actions": []},
                ],
            },
            {
                "label": "Phòng QLTK Nostro, Vostro",
                "menus": [
                    {"code": "menu.doi_chieu_citad_nostro", "actions": []},
                ],
            },
            {
                "label": "Phòng Kế toán",
                "menus": [
                    {"code": "menu.dtbb", "actions": ["dtbb.confirm"]},
                ],
            },
        ],
    },
    {
        "kind": "group",
        "dept": "Báo cáo",
        "icon": "assessment",
        "sections": [
            {
                "label": "Phòng KSNB & HTVH",
                "menus": [
                    {"code": "menu.reports", "actions": []},
                    {"code": "menu.handover_reports", "actions": []},
                ],
            },
            {
                "label": "Phòng Tổng hợp",
                "menus": [
                    {"code": "menu.th_reports", "actions": []},
                ],
            },
        ],
    },
    {
        # Soi gương mục phẳng "leaves" ở cấp 1 của MENU_TREE.
        "kind": "menu",
        "code": "menu.leaves",
        "icon": "event_busy",
        "actions": [
            "leaves.create",
            "leaves.cancel",
            "leaves.resubmit",
            "leaves.approve_ksv",
            "leaves.forward_th",
            "leaves.approve_gd",
            "leaves.dashboard",
            "leaves.quota_admin",
            "leaves.delegation_admin",
            "leaves.stats_export",
            "leaves.declare_direct",
            "leaves.recall",
        ],
    },
    {
        # Soi gương nhóm "cong_truc" trong MENU_TREE. "menu.attendance" điều khiển
        # việc hiện menu + mở màn hình. 2 action con là quyền cộng thêm trong màn:
        # admin gán "xem bảng công cả phòng + xuất Excel" cho một GDV được giao theo
        # dõi chấm công, khỏi phải nâng role lên trưởng/phó phòng — attendance.py
        # check role trưởng/phó phòng/admin HOẶC 2 quyền này.
        "kind": "group",
        "dept": "Chấm công & Lịch trực",
        "icon": "date_range",
        "sections": [
            {
                "label": "Phòng Kế toán",
                "menus": [
                    {"code": "menu.attendance", "actions": ["attendance.view_dept", "attendance.export"]},
                ],
            },
            {
                "label": "Phòng Thanh toán",
                "menus": [
                    {
                        "code": "menu.duty_schedule",
                        "actions": [
                            "duty.generate",
                            "duty.confirm",
                            "duty.delete",
                            "duty.export",
                            "duty.manage_staff",
                            "duty.manage_config",
                        ],
                    },
                    {"code": "menu.so_truc", "actions": ["so_truc.ksv_confirm"]},
                ],
            },
        ],
    },
    {
        # Soi gương nhóm "Tính năng khác" ở cấp 1 của MENU_TREE — hai menu này
        # không thuộc phòng nào nên section không cần dải nhãn phòng.
        "kind": "group",
        "dept": "Tính năng khác",
        "icon": "apps",
        "sections": [
            {
                "label": None,
                "menus": [
                    {"code": "menu.quiz", "actions": ["quiz.upload", "quiz.delete"]},
                    {"code": "menu.vb_format", "actions": ["vb_format.config"]},
                ],
            },
        ],
    },
    {
        # Soi gương nhóm "nhansu" trong MENU_TREE.
        "kind": "group",
        "dept": "Quản lý nhân sự",
        "icon": "badge",
        "sections": [
            {
                "label": None,
                "menus": [
                    {
                        "code": "menu.hr_profiles",
                        "actions": [
                            "hr.view_all",
                            "hr.edit_all",
                            "hr.salary_view",
                            "hr.salary_edit",
                        ],
                    },
                    {"code": "menu.hr_lookup", "actions": ["hr.export"]},
                    {"code": "menu.hr_reminders", "actions": []},
                ],
            },
        ],
    },
    {
        "kind": "menu",
        "code": "menu.ttqt_branches",
        "icon": "account_tree",
        "actions": [
            "ttqt_branches.create",
            "ttqt_branches.edit",
            "ttqt_branches.delete",
            "ttqt_branches.import",
            "ttqt_branches.export",
            "ttqt_branches.history",
        ],
    },
    {
        "kind": "group",
        "dept": "Quản lý hệ thống",
        "icon": "admin_panel_settings",
        "sections": [
            {
                "label": None,
                "menus": [
                    {
                        "code": "menu.staff",
                        "actions": [
                            "staff.create",
                            "staff.edit",
                            "staff.delete",
                            "staff.export",
                            "staff.import_db",
                            "staff.import_join_date",
                        ],
                    },
                    {"code": "menu.logs", "actions": []},
                ],
            },
        ],
    },
]


# ── Chốt an toàn: FEATURE_GROUPS phải phủ kín FEATURES ────────────────────────
def _iter_group_codes():
    """Mọi mã quyền có mặt trong FEATURE_GROUPS, giữ nguyên phần trùng lặp."""
    for node in FEATURE_GROUPS:
        if node["kind"] == "menu":
            yield node["code"]
            yield from node["actions"]
            continue
        for section in node["sections"]:
            for menu in section["menus"]:
                yield menu["code"]
                yield from menu["actions"]


def _assert_feature_coverage() -> None:
    """Mã thiếu ở đây = mất quyền vĩnh viễn, nên chặn khởi động chứ không cảnh báo.

    PUT /api/groups/{id}/features xoá sạch quyền của nhóm rồi ghi lại đúng những
    ô tick đang hiển thị. Mã không được vẽ ra thì không nằm trong danh sách gửi
    lên → lần bấm Lưu đầu tiên xoá nó khỏi mọi nhóm, không log, không báo.
    """
    seen    = list(_iter_group_codes())
    dup     = sorted({c for c in seen if seen.count(c) > 1})
    missing = sorted(set(FEATURES) - set(seen))
    unknown = sorted(set(seen) - set(FEATURES))
    if dup or missing or unknown:
        raise RuntimeError(
            "FEATURE_GROUPS không khớp FEATURES — sửa backend/core/features.py.\n"
            f"  Thiếu (không hiện trên màn phân quyền, sẽ bị xoá khi lưu): {missing}\n"
            f"  Trùng lặp (một mã ở hai chỗ, ô tick sau đè ô trước): {dup}\n"
            f"  Không có trong FEATURES: {unknown}"
        )


_assert_feature_coverage()
