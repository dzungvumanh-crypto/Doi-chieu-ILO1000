"""Schema migrations — _create_tables + _ensure_indexes.

Thêm migration mới: append câu SQL vào cuối list `schema_migrations` trong _ensure_indexes().
Format comment: # Người X — YYYY-MM-DD: mô tả ngắn
Tạo PR riêng, Người 1 approve.
"""
import logging
import sqlite3
from datetime import datetime

from backend.database import DB_PATH


# ── Tạo tables (fresh install) ────────────────────────────────────────────────
def _create_tables(db_path: str):
    """Tạo tất cả bảng nếu chưa có — idempotent."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = OFF")
    statements = [
        """CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code VARCHAR(20) NOT NULL UNIQUE,
            name VARCHAR(200) NOT NULL,
            is_source BOOLEAN DEFAULT 1,
            is_active BOOLEAN DEFAULT 1
        )""",
        """CREATE TABLE IF NOT EXISTS user_tttt (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_code VARCHAR(20) NOT NULL UNIQUE,
            full_name VARCHAR(100) NOT NULL,
            role TEXT NOT NULL DEFAULT 'chuyen_vien',
            department_id INTEGER REFERENCES departments(id),
            username VARCHAR(50) NOT NULL UNIQUE,
            pwd_hash VARCHAR(200) NOT NULL,
            phone VARCHAR(20),
            email VARCHAR(100),
            start_date DATE,
            annual_leave_days INTEGER DEFAULT 12,
            used_leave_days INTEGER DEFAULT 0,
            must_change_password BOOLEAN DEFAULT 0,
            ipcas_code VARCHAR(20),
            payment_username VARCHAR(50),
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME
        )""",
        """CREATE TABLE IF NOT EXISTS source_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_code TEXT,
            full_name TEXT,
            department_id INTEGER REFERENCES departments(id),
            is_active INTEGER DEFAULT 1
        )""",
        """CREATE TABLE IF NOT EXISTS handovers (
            id INTEGER NOT NULL PRIMARY KEY,
            department_id INTEGER NOT NULL REFERENCES departments(id),
            handover_date DATE NOT NULL,
            received_by_id INTEGER REFERENCES user_tttt(id),
            delivered_by VARCHAR(100),
            notes TEXT,
            status VARCHAR(20) DEFAULT 'draft',
            created_at DATETIME,
            UNIQUE(department_id, handover_date)
        )""",
        """CREATE TABLE IF NOT EXISTS document_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            handover_id INTEGER NOT NULL REFERENCES handovers(id),
            source_user_id INTEGER,
            transaction_date DATE NOT NULL,
            sheet_count INTEGER NOT NULL,
            notes TEXT,
            entry_status TEXT DEFAULT 'confirmed',
            entered_by_id INTEGER REFERENCES user_tttt(id),
            confirmed_by_id INTEGER REFERENCES user_tttt(id),
            confirmed_at DATETIME,
            borrowed_at DATETIME,
            borrow_reason TEXT,
            staff_id INTEGER REFERENCES user_tttt(id)
        )""",
        """CREATE TABLE IF NOT EXISTS bundle_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            department_id INTEGER NOT NULL REFERENCES departments(id),
            total_bundles INTEGER DEFAULT 1,
            created_by_id INTEGER NOT NULL REFERENCES user_tttt(id),
            created_at DATETIME,
            notes TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS bundles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL REFERENCES bundle_groups(id),
            sequence INTEGER NOT NULL,
            total_sheets INTEGER DEFAULT 0,
            custodian_id INTEGER REFERENCES user_tttt(id),
            storage_box VARCHAR(50),
            storage_location VARCHAR(200),
            cover_printed_at DATETIME,
            status VARCHAR(20) DEFAULT 'pending',
            cover_units TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS bundle_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bundle_id INTEGER NOT NULL REFERENCES bundles(id),
            entry_id INTEGER NOT NULL REFERENCES document_entries(id)
        )""",
        """CREATE TABLE IF NOT EXISTS entry_change_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL REFERENCES document_entries(id),
            action TEXT NOT NULL,
            performed_by_id INTEGER NOT NULL REFERENCES user_tttt(id),
            timestamp DATETIME,
            old_sheet_count INTEGER,
            new_sheet_count INTEGER,
            notes TEXT
        )""",
        # Lịch sử đổi phòng cán bộ — dùng để định tuyến chứng từ về đúng phòng theo ngày giao dịch
        """CREATE TABLE IF NOT EXISTS staff_department_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id INTEGER NOT NULL REFERENCES user_tttt(id),
            department_id INTEGER NOT NULL REFERENCES departments(id),
            effective_from DATE NOT NULL,
            created_at DATETIME
        )""",
        """CREATE TABLE IF NOT EXISTS leave_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id INTEGER NOT NULL REFERENCES user_tttt(id),
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            leave_type TEXT DEFAULT 'annual',
            reason TEXT,
            status TEXT DEFAULT 'pending_ksv',
            ksv_approver_id INTEGER REFERENCES user_tttt(id),
            ksv_approved_at DATETIME,
            ksv_comment TEXT,
            tong_hop_approver_id INTEGER REFERENCES user_tttt(id),
            tong_hop_approved_at DATETIME,
            tong_hop_comment TEXT,
            gd_approver_id INTEGER REFERENCES user_tttt(id),
            gd_approved_at DATETIME,
            gd_comment TEXT,
            created_at DATETIME,
            updated_at DATETIME
        )""",
        # Session và rate-limit được persist vào DB
        """CREATE TABLE IF NOT EXISTS login_sessions (
            staff_id INTEGER PRIMARY KEY REFERENCES user_tttt(id),
            ip_address TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS login_rate_limit (
            username TEXT PRIMARY KEY,
            attempt_count INTEGER DEFAULT 0,
            window_start TEXT,
            locked_until TEXT
        )""",
        # Audit log cho thao tác admin nhạy cảm
        """CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_id INTEGER REFERENCES user_tttt(id),
            action TEXT NOT NULL,
            target_type TEXT,
            target_id INTEGER,
            detail TEXT,
            ip_address TEXT,
            created_at DATETIME
        )""",
        # Phân quyền theo nhóm
        """CREATE TABLE IF NOT EXISTS user_groups (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        VARCHAR(100) UNIQUE NOT NULL,
            description TEXT,
            is_active   BOOLEAN DEFAULT 1,
            created_at  DATETIME
        )""",
        """CREATE TABLE IF NOT EXISTS group_members (
            group_id INTEGER NOT NULL REFERENCES user_groups(id) ON DELETE CASCADE,
            staff_id INTEGER NOT NULL REFERENCES user_tttt(id)   ON DELETE CASCADE,
            PRIMARY KEY (group_id, staff_id)
        )""",
        """CREATE TABLE IF NOT EXISTS group_features (
            group_id     INTEGER      NOT NULL REFERENCES user_groups(id) ON DELETE CASCADE,
            feature_code VARCHAR(100) NOT NULL,
            PRIMARY KEY (group_id, feature_code)
        )""",
        """CREATE TABLE IF NOT EXISTS swift_recon_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recon_type VARCHAR(10) NOT NULL,
            recon_date DATETIME NOT NULL,
            performed_by_id INTEGER REFERENCES user_tttt(id),
            file_saa_name VARCHAR(255),
            file_ql_name VARCHAR(255),
            total_saa INTEGER,
            total_ql INTEGER,
            total_matched INTEGER,
            total_diff INTEGER,
            merged_json TEXT,
            raw_a_json TEXT,
            raw_b_json TEXT,
            summary_json TEXT,
            diff_a_only_json TEXT,
            diff_b_only_json TEXT,
            di_not_ack_json TEXT,
            created_at DATETIME
        )""",
        # Đối chiếu CITAD 1 ngày = 1 báo cáo CHUNG của cả phòng (không tách
        # theo staff_id nữa — ai lưu sau cùng là bản hiện hành, xem lịch sử
        # từng lần lưu ở bảng doi_chieu_citad_history bên dưới).
        """CREATE TABLE IF NOT EXISTS doi_chieu_citad_sessions (
            ngay        TEXT    PRIMARY KEY,
            data        TEXT    NOT NULL,
            updated_at  DATETIME,
            updated_by  INTEGER REFERENCES user_tttt(id) ON DELETE SET NULL
        )""",
        # Lịch sử từng lần lưu đối chiếu CITAD — 1 dòng/lần bấm Lưu, kèm
        # NGUYÊN VẸN số liệu của phiên chấm đó (không chỉ ai/lúc nào) — để
        # ngày nào nhiều người cùng chấm thì xem/tải lại đúng bản của từng
        # lần lưu, không chỉ biết mỗi tên người lưu.
        """CREATE TABLE IF NOT EXISTS doi_chieu_citad_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ngay        TEXT    NOT NULL,
            staff_id    INTEGER NOT NULL REFERENCES user_tttt(id) ON DELETE CASCADE,
            data        TEXT    NOT NULL,
            created_at  DATETIME NOT NULL
        )""",
        # Mã kết nối Extension cá nhân (thay khoá tĩnh dùng chung sau review
        # bảo mật) — 1 token/staff, chỉ lưu hash, tạo mã mới tự thu hồi mã cũ.
        """CREATE TABLE IF NOT EXISTS doi_chieu_citad_extension_tokens (
            staff_id     INTEGER PRIMARY KEY REFERENCES user_tttt(id) ON DELETE CASCADE,
            token_hash   TEXT NOT NULL UNIQUE,
            created_at   DATETIME,
            last_used_at DATETIME
        )""",
        # Đối chiếu CITAD ↔ PaymentHub — Phòng QLTK Nostro, Vostro. Song song
        # với doi_chieu_citad_sessions/_history (Phòng Thanh toán), khoá theo
        # `ky` (kỳ đối chiếu "dd/mm/yyyy-dd/mm/yyyy", có thể gộp nhiều ngày)
        # thay vì `ngay` đơn — xem doi_chieu_citad_nostro_service.py. Dùng
        # CHUNG bảng doi_chieu_citad_extension_tokens ở trên (mã kết nối
        # Extension trung lập, không tạo bảng token riêng cho module này).
        # `created_by` = người LẬP BẢNG (người đầu tiên lưu kỳ đó), cố định
        # suốt vòng đời bản ghi; `updated_by` = người lưu SAU CÙNG. Tab "Lịch
        # sử" hiển thị created_by — bản chung của cả phòng, nếu hiển thị
        # updated_by thì ai lưu đè sau cũng chiếm mất tên người lập bảng
        # (đúng lỗi đã sửa ở module Phòng Thanh toán, xem ALTER tương ứng
        # trong _ensure_indexes()).
        """CREATE TABLE IF NOT EXISTS doi_chieu_citad_nostro_sessions (
            ky          TEXT    PRIMARY KEY,
            data        TEXT    NOT NULL,
            updated_at  DATETIME,
            updated_by  INTEGER REFERENCES user_tttt(id) ON DELETE SET NULL,
            created_by  INTEGER REFERENCES user_tttt(id) ON DELETE SET NULL
        )""",
        """CREATE TABLE IF NOT EXISTS doi_chieu_citad_nostro_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ky          TEXT    NOT NULL,
            staff_id    INTEGER NOT NULL REFERENCES user_tttt(id) ON DELETE CASCADE,
            data        TEXT    NOT NULL,
            created_at  DATETIME NOT NULL
        )""",
        # Mã kết nối Extension RIÊNG của Phòng QLTK Nostro, Vostro — TÁCH HẲN
        # khỏi doi_chieu_citad_extension_tokens (Phòng Thanh toán). Lý do: 2
        # bảng ban đầu dùng CHUNG 1 bảng token theo staff_id — tạo mã mới ở
        # module này (INSERT ... ON CONFLICT(staff_id) DO UPDATE) vô tình
        # THU HỒI LUÔN mã của module kia cho cùng 1 người, gây lỗi 403 âm
        # thầm khi 1 người dùng cả 2 Extension song song (phát hiện thực tế
        # khi test). Từ nay 2 phòng dùng 2 mã hoàn toàn độc lập, tạo/thu hồi
        # ở phòng nào chỉ ảnh hưởng đúng phòng đó.
        """CREATE TABLE IF NOT EXISTS doi_chieu_citad_nostro_extension_tokens (
            staff_id     INTEGER PRIMARY KEY REFERENCES user_tttt(id) ON DELETE CASCADE,
            token_hash   TEXT NOT NULL UNIQUE,
            created_at   DATETIME,
            last_used_at DATETIME
        )""",
        """CREATE TABLE IF NOT EXISTS doi_soat_citad_history (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            ngay_cham           VARCHAR(10) NOT NULL,
            recon_date          DATETIME NOT NULL,
            performed_by_id     INTEGER REFERENCES user_tttt(id),
            citad_file_names    TEXT,
            ipcas_file_names    TEXT,
            hub_file_names      TEXT,
            total_citad         INTEGER,
            total_ipcas         INTEGER,
            total_hub           INTEGER,
            n_khop              INTEGER,
            n_lech              INTEGER,
            lech_json           TEXT,
            created_at          DATETIME
        )""",
        # Sổ trực cuối ngày Phòng Thanh toán — KHÔNG tách bảng lịch sử riêng
        # như doi_chieu_citad, bảng này tự thân là lịch sử. `truc_date` KHÔNG
        # unique (khác bản đầu): KSV "từ chối" (để sửa HAY để huỷ, cả 2 đều
        # chỉ ĐỀ NGHỊ) ghi đè lên cùng 1 dòng như cũ (quay về draft), nhưng
        # GDV tự bấm "Huỷ phiên trực" (draft_cancel, status='cancelled') mới
        # là NGÕ CỤT thật — dòng đó đóng vĩnh viễn, phải tạo dòng MỚI (phiên
        # trực khác) cho đúng ngày đó nên 1 ngày có thể có NHIỀU dòng.
        # get_active_by_date() trong service luôn lấy dòng chưa 'cancelled'
        # MỚI NHẤT làm phiên đang làm việc.
        # `ksv_decision` ('reject_fix' | 'reject_cancel' | 'self_edit' | NULL):
        # phân biệt KSV vừa từ chối để SỬA hay để HUỶ, hay đang TỰ chỉnh sửa
        # lại 1 phiên đã "Hoàn thành" (request_edit(), nhánh KSV) —
        # status='draft' giống hệt các trường hợp nên không suy ra được từ
        # status. GDV cần biết để: (1) banner hiện đúng chữ "để sửa"/"để huỷ"/
        # "tự chỉnh sửa", (2) nếu 'reject_cancel' thì KHOÁ hẳn form sửa, chỉ
        # còn nút "Huỷ phiên trực". Reset về NULL khi forward_to_ksv()/
        # ksv_finalize_edit() thành công. `gdv_decided_by`/`gdv_decided_at`
        # dùng lại cho CẢ 2 việc: ai đã tự huỷ phiên (draft_cancel) VÀ GDV nào
        # vừa "Yêu cầu chỉnh sửa" 1 phiên đã Hoàn thành (request_edit(), nhánh
        # GDV) — phân biệt bằng status (cancelled vs draft).
        # Luồng: draft -> pending_ksv -> approved -> draft (GDV/KSV yêu cầu
        # chỉnh sửa lại) | draft (KSV từ chối — sửa hoặc huỷ) | cancelled
        # (CHỈ GDV tự huỷ, ngõ cụt).
        """CREATE TABLE IF NOT EXISTS so_truc_records (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            truc_date         TEXT    NOT NULL,
            gdv1_name         TEXT    DEFAULT '',
            gdv2_name         TEXT    DEFAULT '',
            gdv1_id           INTEGER REFERENCES user_tttt(id) ON DELETE SET NULL,
            gdv2_id           INTEGER REFERENCES user_tttt(id) ON DELETE SET NULL,
            ghi_chu           TEXT    DEFAULT '',
            status            TEXT    NOT NULL DEFAULT 'draft',
            initiated_by      INTEGER REFERENCES user_tttt(id) ON DELETE SET NULL,
            initiated_at      DATETIME,
            ksv_id            INTEGER REFERENCES user_tttt(id) ON DELETE SET NULL,
            confirmed_by      INTEGER REFERENCES user_tttt(id) ON DELETE SET NULL,
            confirmed_at      DATETIME,
            ksv_decided_by    INTEGER REFERENCES user_tttt(id) ON DELETE SET NULL,
            ksv_decided_at    DATETIME,
            reject_reason     TEXT,
            ksv_decision      TEXT,
            gdv_decided_by    INTEGER REFERENCES user_tttt(id) ON DELETE SET NULL,
            gdv_decided_at    DATETIME,
            truc_phu_ids      TEXT    DEFAULT '[]',
            created_at        DATETIME NOT NULL,
            updated_at        DATETIME NOT NULL
        )""",
        # Danh mục chi nhánh thực hiện TTQT — nguồn gốc là file Excel do Phòng
        # KSNB phát hành, nhập vào đây để tra cứu / sửa trực tiếp trên hệ thống.
        # sort_order giữ đúng thứ tự dòng trong file gốc (mã CN không tăng dần).
        """CREATE TABLE IF NOT EXISTS ttqt_branches (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            ma_cn        VARCHAR(20) NOT NULL UNIQUE,
            ten_cn       VARCHAR(200) NOT NULL,
            swift_bic    VARCHAR(20),
            loai_cn      INTEGER,
            duoc_phep    VARCHAR(100),
            cn_quan_ly   VARCHAR(200),
            ghi_chu      TEXT,
            sdt          VARCHAR(100),
            dia_chi      TEXT,
            dia_chi_en   TEXT,
            is_closed    INTEGER NOT NULL DEFAULT 0,
            sort_order   INTEGER,
            updated_at   DATETIME
        )""",
        # ── Ôn tập trắc nghiệm (Quizz) ────────────────────────────────────
        # Bộ câu hỏi nhập MỘT LẦN từ Excel rồi dùng chung cho cả cơ quan —
        # `content_hash` để nhận ra ai đó tải lại đúng file cũ dưới tên khác.
        """CREATE TABLE IF NOT EXISTS quiz_sets (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            name           VARCHAR(200) NOT NULL UNIQUE,
            description    TEXT,
            source_file    TEXT,
            content_hash   VARCHAR(64),
            question_count INTEGER NOT NULL DEFAULT 0,
            created_by     INTEGER REFERENCES user_tttt(id) ON DELETE SET NULL,
            created_at     DATETIME NOT NULL,
            is_active      INTEGER NOT NULL DEFAULT 1
        )""",
        # opt4 để trống được: file mẫu có cả câu 3 lựa chọn.
        """CREATE TABLE IF NOT EXISTS quiz_questions (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            set_id     INTEGER NOT NULL REFERENCES quiz_sets(id) ON DELETE CASCADE,
            order_no   INTEGER NOT NULL,
            content    TEXT NOT NULL,
            opt1       TEXT,
            opt2       TEXT,
            opt3       TEXT,
            opt4       TEXT,
            correct_no INTEGER NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS quiz_attempts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            set_id          INTEGER NOT NULL REFERENCES quiz_sets(id) ON DELETE CASCADE,
            staff_id        INTEGER NOT NULL REFERENCES user_tttt(id) ON DELETE CASCADE,
            mode            TEXT NOT NULL DEFAULT 'practice',
            settings        TEXT,
            total_questions INTEGER NOT NULL DEFAULT 0,
            correct_count   INTEGER,
            score           REAL,
            duration_ms     INTEGER,
            status          TEXT NOT NULL DEFAULT 'in_progress',
            elapsed_ms      INTEGER NOT NULL DEFAULT 0,
            current_idx     INTEGER NOT NULL DEFAULT 0,
            saved_at        DATETIME,
            started_at      DATETIME NOT NULL,
            finished_at     DATETIME
        )""",
        # Sinh sẵn đủ N dòng lúc tạo lượt: thứ tự câu và thứ tự đáp án đã trộn
        # phải lưu lại, nếu không màn "Xem lại bài" sẽ dựng ra một đề khác hẳn
        # với đề người dùng vừa làm.
        """CREATE TABLE IF NOT EXISTS quiz_attempt_items (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            attempt_id   INTEGER NOT NULL REFERENCES quiz_attempts(id) ON DELETE CASCADE,
            question_id  INTEGER NOT NULL REFERENCES quiz_questions(id) ON DELETE CASCADE,
            order_no     INTEGER NOT NULL,
            option_order TEXT NOT NULL,
            chosen_no    INTEGER,
            is_correct   INTEGER,
            time_ms      INTEGER
        )""",
        # ── Quản lý nhân sự — 2026-08-28 ──────────────────────────────────────
        # `recruit_date` cố ý KHÔNG có ở đây: "Ngày tuyển dụng" chính là "Ngày vào
        # ngành" đã nằm ở `user_tttt.join_industry_date` — một mốc thì một cột.
        # Mọi bảng khoá theo `staff_id` = user_tttt.id: hồ sơ nhân sự KHÔNG có
        # danh sách cán bộ riêng, cán bộ nào có tài khoản thì có hồ sơ. Nhờ vậy
        # họ tên / phòng / ngày vào ngành chỉ nằm một chỗ, không phải đồng bộ
        # hai bảng (xem docs/Implementation-notes.html).
        """CREATE TABLE IF NOT EXISTS hr_profiles (
            staff_id          INTEGER PRIMARY KEY REFERENCES user_tttt(id) ON DELETE CASCADE,
            gender            TEXT,
            dob               DATE,
            cccd              VARCHAR(20),
            cccd_date         DATE,
            cccd_place        VARCHAR(200),
            permanent_address TEXT,
            current_address   TEXT,
            dependents        INTEGER DEFAULT 0,
            contact_name      VARCHAR(100),
            contact_relation  VARCHAR(50),
            contact_phone     VARCHAR(30),
            contact_address   TEXT,
            contract_type     VARCHAR(100),
            position_title    VARCHAR(100),
            photo             BLOB,
            photo_mime        VARCHAR(50),
            note              TEXT,
            updated_at        DATETIME,
            updated_by        INTEGER REFERENCES user_tttt(id) ON DELETE SET NULL
        )""",
        """CREATE TABLE IF NOT EXISTS hr_degrees (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id    INTEGER NOT NULL REFERENCES user_tttt(id) ON DELETE CASCADE,
            kind        TEXT NOT NULL,
            name        VARCHAR(200) NOT NULL,
            major       VARCHAR(200),
            school      VARCHAR(200),
            issue_date  DATE,
            expiry_date DATE,
            grade       VARCHAR(100),
            note        TEXT,
            created_at  DATETIME,
            updated_at  DATETIME,
            updated_by  INTEGER REFERENCES user_tttt(id) ON DELETE SET NULL
        )""",
        """CREATE TABLE IF NOT EXISTS hr_appointments (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id       INTEGER NOT NULL REFERENCES user_tttt(id) ON DELETE CASCADE,
            kind           TEXT NOT NULL,
            position       VARCHAR(200) NOT NULL,
            unit           VARCHAR(200),
            decision_no    VARCHAR(100),
            decision_date  DATE,
            effective_from DATE,
            effective_to   DATE,
            note           TEXT,
            created_at     DATETIME,
            updated_at     DATETIME,
            updated_by     INTEGER REFERENCES user_tttt(id) ON DELETE SET NULL
        )""",
        """CREATE TABLE IF NOT EXISTS hr_work_history (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id   INTEGER NOT NULL REFERENCES user_tttt(id) ON DELETE CASCADE,
            from_date  DATE NOT NULL,
            to_date    DATE,
            position   VARCHAR(200),
            unit       VARCHAR(200) NOT NULL,
            at_branch  INTEGER NOT NULL DEFAULT 0,
            note       TEXT,
            created_at DATETIME,
            updated_at DATETIME,
            updated_by INTEGER REFERENCES user_tttt(id) ON DELETE SET NULL
        )""",
        # Nghỉ gián đoạn: `count_seniority = 0` nghĩa là khoảng này KHÔNG tính
        # vào thời gian công tác (nghỉ không hưởng lương) — đây là số liệu để
        # người làm chế độ đối chiếu, phần mềm không tự trừ vào phép năm.
        """CREATE TABLE IF NOT EXISTS hr_breaks (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id        INTEGER NOT NULL REFERENCES user_tttt(id) ON DELETE CASCADE,
            from_date       DATE NOT NULL,
            to_date         DATE NOT NULL,
            reason          VARCHAR(200),
            unpaid          INTEGER NOT NULL DEFAULT 1,
            count_seniority INTEGER NOT NULL DEFAULT 0,
            note            TEXT,
            created_at      DATETIME,
            updated_at      DATETIME,
            updated_by      INTEGER REFERENCES user_tttt(id) ON DELETE SET NULL
        )""",
        """CREATE TABLE IF NOT EXISTS hr_salaries (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id           INTEGER NOT NULL REFERENCES user_tttt(id) ON DELETE CASCADE,
            grade              VARCHAR(50),
            coef_v1            REAL,
            coef_v2            REAL,
            position_allowance REAL,
            decision_no        VARCHAR(100),
            decision_date      DATE NOT NULL,
            effective_from     DATE,
            cycle_months       INTEGER,
            note               TEXT,
            created_at         DATETIME,
            updated_at         DATETIME,
            updated_by         INTEGER REFERENCES user_tttt(id) ON DELETE SET NULL
        )""",
        """CREATE TABLE IF NOT EXISTS hr_trainings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id    INTEGER NOT NULL REFERENCES user_tttt(id) ON DELETE CASCADE,
            course_name VARCHAR(300) NOT NULL,
            from_date   DATE,
            to_date     DATE,
            mode        TEXT,
            result      VARCHAR(200),
            organizer   VARCHAR(200),
            note        TEXT,
            created_at  DATETIME,
            updated_at  DATETIME,
            updated_by  INTEGER REFERENCES user_tttt(id) ON DELETE SET NULL
        )""",
        # `next_issue_date` = ngày dự kiến được cấp mới. Nhắc lịch "cấp điện
        # thoại mới trước 1 quý" đọc đúng cột này, không đoán theo tên công cụ.
        """CREATE TABLE IF NOT EXISTS hr_tools (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id        INTEGER NOT NULL REFERENCES user_tttt(id) ON DELETE CASCADE,
            tool_name       VARCHAR(200) NOT NULL,
            tool_code       VARCHAR(100),
            quantity        INTEGER DEFAULT 1,
            issued_date     DATE,
            status          TEXT NOT NULL DEFAULT 'dang_dung',
            next_issue_date DATE,
            note            TEXT,
            created_at      DATETIME,
            updated_at      DATETIME,
            updated_by      INTEGER REFERENCES user_tttt(id) ON DELETE SET NULL
        )""",
        # File đính kèm dùng chung cho mọi phân hệ (quyết định bổ nhiệm, bằng
        # cấp, chứng chỉ...). `section` + `item_id` là khoá ngoại ĐA HÌNH nên
        # SQLite không ràng buộc hộ được: xoá dòng nào thì code phải tự xoá file
        # của dòng đó (xem `_xoa_dinh_kem()` trong backend/api/hr.py).
        """CREATE TABLE IF NOT EXISTS hr_attachments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            section     TEXT NOT NULL,
            item_id     INTEGER NOT NULL,
            filename    VARCHAR(255) NOT NULL,
            mime        VARCHAR(100),
            size_bytes  INTEGER,
            content     BLOB NOT NULL,
            uploaded_by INTEGER REFERENCES user_tttt(id) ON DELETE SET NULL,
            uploaded_at DATETIME
        )""",
    ]
    for s in statements:
        cur.execute(s)
    cur.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()


# ── Migrate schema (idempotent) ───────────────────────────────────────────────
def _ensure_indexes():
    """Tạo index và migrate schema trên DB hiện tại (idempotent)."""
    schema_migrations = [
        # Schema migration – thêm cột mới nếu chưa có (SQLite không hỗ trợ IF NOT EXISTS cho ADD COLUMN)
        # Bọc trong try/except ở Python để bỏ qua lỗi "duplicate column"
        "ALTER TABLE bundles ADD COLUMN cover_units TEXT",
        # Cột mới cho KSNBStaff (chuyên viên)
        "ALTER TABLE user_tttt ADD COLUMN department_id INTEGER REFERENCES departments(id)",
        # Cột mới cho DocumentEntry
        "ALTER TABLE document_entries ADD COLUMN entry_status TEXT DEFAULT 'confirmed'",
        "ALTER TABLE document_entries ADD COLUMN entered_by_id INTEGER REFERENCES user_tttt(id)",
        "ALTER TABLE document_entries ADD COLUMN confirmed_by_id INTEGER REFERENCES user_tttt(id)",
        "ALTER TABLE document_entries ADD COLUMN confirmed_at DATETIME",
        "ALTER TABLE document_entries ADD COLUMN borrowed_at DATETIME",
        "ALTER TABLE document_entries ADD COLUMN borrow_reason TEXT",
        # Gán phòng KSNB cho staff cũ không có department_id (idempotent)
        # KHÔNG gán cho 'admin': quản trị viên không thuộc phòng nào (xem migration cuối file).
        "UPDATE user_tttt SET department_id = (SELECT id FROM departments WHERE code = 'KSNB' LIMIT 1) WHERE department_id IS NULL AND role IN ('hau_kiem_vien', 'controller', 'viewer')",
        # Quyền mới — migrate controller → pho_phong
        "ALTER TABLE user_tttt ADD COLUMN annual_leave_days INTEGER DEFAULT 12",
        "ALTER TABLE user_tttt ADD COLUMN used_leave_days INTEGER DEFAULT 0",
        "UPDATE user_tttt SET role = 'pho_phong' WHERE role = 'controller'",
        "UPDATE user_tttt SET role = 'chuyen_vien' WHERE role = 'viewer'",
        "INSERT OR IGNORE INTO departments (code, name, is_source, is_active) VALUES ('TH', 'Phòng Tổng hợp', 0, 1)",
        "INSERT OR IGNORE INTO departments (code, name, is_source, is_active) VALUES ('BGD', 'Ban Giám đốc', 0, 1)",
        # Gán GĐ/PGĐ vào Ban Giám đốc (idempotent — chạy lại không hại)
        "UPDATE user_tttt SET department_id = (SELECT id FROM departments WHERE code = 'BGD' LIMIT 1) WHERE role IN ('giam_doc', 'pho_giam_doc')",
        # Mở rộng LeaveRecord cho workflow 2 bước
        "ALTER TABLE leave_records ADD COLUMN ksv_approver_id INTEGER REFERENCES user_tttt(id)",
        "ALTER TABLE leave_records ADD COLUMN ksv_approved_at DATETIME",
        "ALTER TABLE leave_records ADD COLUMN ksv_comment TEXT",
        "ALTER TABLE leave_records ADD COLUMN gd_approver_id INTEGER REFERENCES user_tttt(id)",
        "ALTER TABLE leave_records ADD COLUMN gd_approved_at DATETIME",
        "ALTER TABLE leave_records ADD COLUMN gd_comment TEXT",
        "ALTER TABLE leave_records ADD COLUMN updated_at DATETIME",
        "UPDATE leave_records SET status = 'pending_ksv' WHERE status = 'pending'",
        # Bảng ủy quyền GĐ
        """CREATE TABLE IF NOT EXISTS delegation_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            giam_doc_id INTEGER NOT NULL REFERENCES user_tttt(id),
            pho_giam_doc_id INTEGER NOT NULL REFERENCES user_tttt(id),
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            note TEXT,
            created_by_id INTEGER NOT NULL REFERENCES user_tttt(id),
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME
        )""",
        # Workflow nghỉ phép 3 bước — Phòng Tổng hợp
        "ALTER TABLE leave_records ADD COLUMN tong_hop_approver_id INTEGER REFERENCES user_tttt(id)",
        "ALTER TABLE leave_records ADD COLUMN tong_hop_approved_at DATETIME",
        "ALTER TABLE leave_records ADD COLUMN tong_hop_comment TEXT",
        # Bảng ngày lễ
        """CREATE TABLE IF NOT EXISTS public_holidays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL UNIQUE,
            name TEXT NOT NULL
        )""",
        # Bảng nhật ký đăng nhập
        """CREATE TABLE IF NOT EXISTS login_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            staff_id INTEGER REFERENCES user_tttt(id),
            ip_address TEXT,
            success INTEGER NOT NULL,
            detail TEXT,
            created_at DATETIME
        )""",
        # Bảng lịch sử thao tác nghỉ phép
        """CREATE TABLE IF NOT EXISTS leave_action_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            leave_id INTEGER NOT NULL REFERENCES leave_records(id),
            actor_id INTEGER NOT NULL REFERENCES user_tttt(id),
            action TEXT NOT NULL,
            comment TEXT,
            from_status TEXT,
            to_status TEXT,
            created_at DATETIME
        )""",
        # 1.3 — bắt buộc đổi mật khẩu lần đầu
        "ALTER TABLE user_tttt ADD COLUMN must_change_password BOOLEAN DEFAULT 0",
        # 1.4 — mã IPCAS và username Payment cho KSNB staff (HKV)
        "ALTER TABLE user_tttt ADD COLUMN ipcas_code VARCHAR(20)",
        "ALTER TABLE user_tttt ADD COLUMN payment_username VARCHAR(50)",
        # 1.5 — gộp SourceUser vào KSNBStaff: thêm staff_id vào document_entries
        "ALTER TABLE document_entries ADD COLUMN staff_id INTEGER REFERENCES user_tttt(id)",
        # Backfill staff_id: match source_users.user_code == user_tttt.ipcas_code
        """UPDATE document_entries
           SET staff_id = (
               SELECT ks.id FROM user_tttt ks
               JOIN source_users su ON trim(ks.ipcas_code) = trim(su.user_code)
               WHERE su.id = document_entries.source_user_id
               LIMIT 1
           )
           WHERE staff_id IS NULL AND source_user_id IS NOT NULL""",
        # 1.6 — unique index mới dùng staff_id (constraint cũ trên source_user_id bị vô hiệu do NULL)
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_entry_staff_date ON document_entries(handover_id, staff_id, transaction_date)",
        # 2.0 — CHECK constraints cho dữ liệu nghiệp vụ (SQLite cho phép thêm qua trigger thay vì ALTER)
        # Dùng trigger để chặn sheet_count <= 0 khi INSERT/UPDATE
        """CREATE TRIGGER IF NOT EXISTS chk_sheet_count_insert
           BEFORE INSERT ON document_entries
           WHEN NEW.sheet_count <= 0
           BEGIN SELECT RAISE(ABORT, 'sheet_count phải lớn hơn 0'); END""",
        """CREATE TRIGGER IF NOT EXISTS chk_sheet_count_update
           BEFORE UPDATE ON document_entries
           WHEN NEW.sheet_count <= 0
           BEGIN SELECT RAISE(ABORT, 'sheet_count phải lớn hơn 0'); END""",
        # (trigger chk_used_leave_days định nghĩa ở dưới, sau khi bảng đã đổi tên)
        # Persist session và rate-limit — tồn tại qua restart
        """CREATE TABLE IF NOT EXISTS login_sessions (
            staff_id INTEGER PRIMARY KEY REFERENCES user_tttt(id),
            ip_address TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS login_rate_limit (
            username TEXT PRIMARY KEY,
            attempt_count INTEGER DEFAULT 0,
            window_start TEXT,
            locked_until TEXT
        )""",
        # (audit_logs đã tạo ở trên — bỏ định nghĩa trùng)
        # Xóa mềm — ẩn khỏi danh sách nhưng giữ lịch sử
        "ALTER TABLE user_tttt ADD COLUMN is_deleted BOOLEAN DEFAULT 0",
        # Trigger dùng tên bảng mới (idempotent — IF NOT EXISTS)
        """CREATE TRIGGER IF NOT EXISTS chk_used_leave_days
           BEFORE UPDATE ON user_tttt
           WHEN NEW.used_leave_days < 0
           BEGIN SELECT RAISE(ABORT, 'used_leave_days không được âm'); END""",

        # Ngày vào ngành — dùng để tính số ngày phép năm (12 + floor(năm / 4))
        "ALTER TABLE user_tttt ADD COLUMN join_industry_date DATE",

        # ── Thêm migration mới DƯỚI ĐÂY ─────────────────────────────────────────
        # Format: # Người X — YYYY-MM-DD: mô tả ngắn
        # "ALTER TABLE <bảng> ADD COLUMN <cột> <kiểu>",

        # Phân quyền theo nhóm — 2026-06-08
        """CREATE TABLE IF NOT EXISTS user_groups (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        VARCHAR(100) UNIQUE NOT NULL,
            description TEXT,
            is_active   BOOLEAN DEFAULT 1,
            created_at  DATETIME
        )""",
        """CREATE TABLE IF NOT EXISTS group_members (
            group_id INTEGER NOT NULL REFERENCES user_groups(id) ON DELETE CASCADE,
            staff_id INTEGER NOT NULL REFERENCES user_tttt(id)   ON DELETE CASCADE,
            PRIMARY KEY (group_id, staff_id)
        )""",
        """CREATE TABLE IF NOT EXISTS group_features (
            group_id     INTEGER      NOT NULL REFERENCES user_groups(id) ON DELETE CASCADE,
            feature_code VARCHAR(100) NOT NULL,
            PRIMARY KEY (group_id, feature_code)
        )""",
        # KSNB System — 2026-06-09: session_key để enforce single-session per user
        "ALTER TABLE login_sessions ADD COLUMN session_key TEXT",

        # ── Phân lịch trực Phòng Thanh toán — 2026-06-09 ────────────────────────
        """CREATE TABLE IF NOT EXISTS duty_staff_meta (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL UNIQUE REFERENCES user_tttt(id),
            can_do_sp    BOOLEAN DEFAULT 0,
            is_sp_backup BOOLEAN DEFAULT 0,
            is_on_project BOOLEAN DEFAULT 0,
            display_order INTEGER DEFAULT 999,
            created_at   DATETIME
        )""",
        """CREATE TABLE IF NOT EXISTS duty_absences (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id     INTEGER NOT NULL REFERENCES user_tttt(id),
            absence_date DATE    NOT NULL,
            created_at   DATETIME,
            UNIQUE(staff_id, absence_date)
        )""",
        """CREATE TABLE IF NOT EXISTS duty_requests (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id     INTEGER NOT NULL REFERENCES user_tttt(id),
            request_type VARCHAR(10) NOT NULL CHECK(request_type IN ('once','weekly')),
            specific_date DATE,
            day_of_week  INTEGER,
            year         INTEGER,
            is_active    BOOLEAN DEFAULT 1,
            created_at   DATETIME
        )""",
        """CREATE TABLE IF NOT EXISTS duty_special_days (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            date         DATE    UNIQUE NOT NULL,
            day_type     VARCHAR(20) NOT NULL CHECK(day_type IN ('holiday','cutoff','settlement','makeup')),
            label        VARCHAR(100),
            is_confirmed BOOLEAN DEFAULT 0,
            created_at   DATETIME
        )""",
        """CREATE TABLE IF NOT EXISTS duty_rotation_state (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            year        INTEGER NOT NULL,
            role        VARCHAR(20) NOT NULL,
            staff_id    INTEGER NOT NULL REFERENCES user_tttt(id),
            shift_count INTEGER DEFAULT 0,
            last_used   DATE,
            position    INTEGER DEFAULT 0,
            UNIQUE(year, role, staff_id)
        )""",
        """CREATE TABLE IF NOT EXISTS duty_shifts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            shift_date  DATE NOT NULL,
            shift_type  VARCHAR(20) NOT NULL CHECK(shift_type IN ('normal','friday','cutoff','settlement_main','settlement_sub')),
            leader_id   INTEGER REFERENCES user_tttt(id),
            sp_id       INTEGER REFERENCES user_tttt(id),
            sp_warning  VARCHAR(20),
            nv_ids      TEXT DEFAULT '[]',
            nv_count    INTEGER DEFAULT 0,
            is_auto     BOOLEAN DEFAULT 1,
            status      VARCHAR(10) DEFAULT 'draft' CHECK(status IN ('draft','confirmed')),
            created_at  DATETIME,
            UNIQUE(shift_date, shift_type)
        )""",
        """CREATE TABLE IF NOT EXISTS duty_shift_config (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            year        INTEGER UNIQUE NOT NULL,
            nv_count    INTEGER DEFAULT 2,
            signer_name VARCHAR(100)
        )""",
        f"INSERT OR IGNORE INTO duty_shift_config (year, nv_count) VALUES ({datetime.now().year}, 2)",
        "CREATE INDEX IF NOT EXISTS ix_duty_staff_meta_user   ON duty_staff_meta(user_id)",
        "CREATE INDEX IF NOT EXISTS ix_duty_absences_staff    ON duty_absences(staff_id)",
        "CREATE INDEX IF NOT EXISTS ix_duty_absences_date     ON duty_absences(absence_date)",
        "CREATE INDEX IF NOT EXISTS ix_duty_requests_staff    ON duty_requests(staff_id)",
        "CREATE INDEX IF NOT EXISTS ix_duty_rotation_year     ON duty_rotation_state(year, role)",
        "CREATE INDEX IF NOT EXISTS ix_duty_shifts_date       ON duty_shifts(shift_date)",
        # 2026-08-07: thống nhất 1 cờ song phương duy nhất. Lãnh đạo từng được đánh dấu
        # "Backup SP" nay chuyển thành can_do_sp để không mất khả năng trực song phương.
        # Cột is_sp_backup giữ lại (không drop) nhưng engine/UI không còn đọc.
        #
        # Hai câu này là một cặp: cả list chạy lại MỖI lần khởi động, nên nếu không
        # xoá cờ nguồn thì admin bỏ tick "biết song phương" xong restart là cờ tự bật
        # lại — im lặng, và UI đã gỡ is_sp_backup nên không có cách nào gỡ bằng tay.
        "UPDATE duty_staff_meta SET can_do_sp = 1 WHERE is_sp_backup = 1 AND can_do_sp = 0",
        "UPDATE duty_staff_meta SET is_sp_backup = 0 WHERE is_sp_backup = 1",

        # ── 2026-08-08: khai báo số người trực + ca quyết toán chính/phụ ────────
        # Số người mỗi ca trước đây cứng trong code. Nay phòng tự khai, và số đã
        # khai là bắt buộc — thiếu thì không hình thành ca trực.
        "ALTER TABLE duty_shift_config ADD COLUMN ld_count INTEGER DEFAULT 1",
        "ALTER TABLE duty_shift_config ADD COLUMN qt_ld_count INTEGER DEFAULT 1",
        "ALTER TABLE duty_shift_config ADD COLUMN qt_nv_chinh_count INTEGER DEFAULT 3",
        "ALTER TABLE duty_shift_config ADD COLUMN qt_nv_phu_count INTEGER DEFAULT 2",

        # ── 2026-08-13: chức danh người ký trên file lịch trực ─────────────────
        # Chữ "GIÁM ĐỐC" trước đây nằm cứng trong hàm dựng file, đổi sang Phó Giám
        # đốc là phải sửa code. Bản ghi cũ để NULL và rơi về mặc định lúc xuất.
        "ALTER TABLE duty_shift_config ADD COLUMN signer_title VARCHAR(100)",

        # Một ca có thể có nhiều Lãnh đạo (nhất là ngày quyết toán) → leader_id đơn
        # lẻ không đủ. Cột leader_id giữ lại nhưng engine/API ngừng đọc.
        "ALTER TABLE duty_shifts ADD COLUMN leader_ids TEXT DEFAULT '[]'",
        # Ca quyết toán: nhân viên chia 2 nhóm, nhóm phụ về sớm hơn
        "ALTER TABLE duty_shifts ADD COLUMN nv_phu_ids TEXT DEFAULT '[]'",
        "ALTER TABLE duty_shifts ADD COLUMN nv_phu_count INTEGER DEFAULT 0",
        "UPDATE duty_shifts SET leader_ids = '[' || leader_id || ']' "
        "WHERE leader_id IS NOT NULL AND COALESCE(leader_ids, '[]') = '[]'",

        # Ca quyết toán từng lưu thành 2 dòng (settlement_main + settlement_sub);
        # nay gộp thành 1 ca có nhóm trực phụ. Đổ người của ca phụ vào nv_phu_ids
        # của ca chính cùng ngày rồi xoá dòng phụ.
        """UPDATE duty_shifts SET
               nv_phu_ids = (SELECT s.nv_ids FROM duty_shifts s
                             WHERE s.shift_date = duty_shifts.shift_date
                               AND s.shift_type = 'settlement_sub'),
               nv_phu_count = (SELECT s.nv_count FROM duty_shifts s
                               WHERE s.shift_date = duty_shifts.shift_date
                                 AND s.shift_type = 'settlement_sub')
           WHERE shift_type = 'settlement_main'
             AND COALESCE(nv_phu_ids, '[]') = '[]'
             AND EXISTS (SELECT 1 FROM duty_shifts s
                         WHERE s.shift_date = duty_shifts.shift_date
                           AND s.shift_type = 'settlement_sub')""",
        "DELETE FROM duty_shifts WHERE shift_type = 'settlement_sub'",
        # Popup thông báo carry-over hết hiệu lực sau Q1 — mỗi user chỉ xem 1 lần/năm
        "ALTER TABLE user_tttt ADD COLUMN carryover_notice_year INTEGER",
        # Nhập file hạn mức phép (Excel) — lưu lịch sử để có thể hoàn tác
        """CREATE TABLE IF NOT EXISTS quota_import_batches (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            year           INTEGER NOT NULL,
            filename       TEXT,
            imported_by    INTEGER REFERENCES user_tttt(id),
            imported_at    DATETIME,
            row_count      INTEGER DEFAULT 0,
            matched_count  INTEGER DEFAULT 0,
            status         TEXT DEFAULT 'applied' CHECK(status IN ('applied','rolled_back')),
            rolled_back_by INTEGER REFERENCES user_tttt(id),
            rolled_back_at DATETIME
        )""",
        """CREATE TABLE IF NOT EXISTS quota_import_items (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id             INTEGER NOT NULL REFERENCES quota_import_batches(id),
            staff_id             INTEGER NOT NULL REFERENCES user_tttt(id),
            old_quota_days       REAL,
            old_used_leave_days  REAL,
            new_quota_days       REAL,
            new_used_leave_days  REAL,
            created_leave_id     INTEGER
        )""",
        # DB đã tạo bảng trước khi có cột này → thêm bù (lỗi duplicate bị nuốt)
        "ALTER TABLE quota_import_items ADD COLUMN created_leave_id INTEGER",
        "CREATE INDEX IF NOT EXISTS ix_quota_import_items_batch ON quota_import_items(batch_id)",
        # Người 3 — 2026-07-15: bù migration còn thiếu cho leave_records/leave_quotas.
        # Các cột/bảng này đã được thêm out-of-band trên DB dùng để phát triển
        # (không qua migrations.py) nên fresh-install trước đây bị lỗi "no such
        # column"/"no such table" ở /api/leaves/today, khai báo hộ, hạn mức, dashboard.
        "ALTER TABLE leave_records ADD COLUMN spread_dates TEXT",
        "ALTER TABLE leave_records ADD COLUMN is_direct BOOLEAN DEFAULT 0",
        "ALTER TABLE leave_records ADD COLUMN direct_by INTEGER REFERENCES user_tttt(id)",
        "ALTER TABLE leave_records ADD COLUMN recall_reason TEXT",
        """CREATE TABLE IF NOT EXISTS leave_quotas (
            staff_id  INTEGER NOT NULL REFERENCES user_tttt(id),
            year      INTEGER NOT NULL,
            quota_days REAL   NOT NULL DEFAULT 12,
            PRIMARY KEY (staff_id, year)
        )""",
        # year là cột thứ 2 trong PRIMARY KEY (staff_id, year) nên không tận dụng
        # được index khi lọc riêng theo year (get_quotas/export_quotas/stats_annual,
        # _carry_over_bulk) — thêm index riêng cho year.
        "CREATE INDEX IF NOT EXISTS ix_leave_quotas_year ON leave_quotas(year)",

        # ── Lịch sử đổi phòng cán bộ — 2026-07-20 ──────────────────────────────
        # Bảng: mỗi dòng = "từ ngày effective_from, cán bộ thuộc phòng department_id"
        """CREATE TABLE IF NOT EXISTS staff_department_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id INTEGER NOT NULL REFERENCES user_tttt(id),
            department_id INTEGER NOT NULL REFERENCES departments(id),
            effective_from DATE NOT NULL,
            created_at DATETIME
        )""",
        # Backfill baseline: user chưa có lịch sử → 1 dòng (phòng hiện tại, hiệu lực từ 2000-01-01)
        """INSERT INTO staff_department_history (staff_id, department_id, effective_from, created_at)
           SELECT u.id, u.department_id, '2000-01-01', datetime('now')
           FROM user_tttt u
           WHERE u.department_id IS NOT NULL
             AND NOT EXISTS (SELECT 1 FROM staff_department_history h WHERE h.staff_id = u.id)""",

        # ── Danh sách CN thực hiện TTQT — 2026-08-04 ──────────────────────────
        # Lặp lại DDL của _create_tables() để DB đang chạy cũng có bảng này.
        """CREATE TABLE IF NOT EXISTS ttqt_branches (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            ma_cn        VARCHAR(20) NOT NULL UNIQUE,
            ten_cn       VARCHAR(200) NOT NULL,
            swift_bic    VARCHAR(20),
            loai_cn      INTEGER,
            duoc_phep    VARCHAR(100),
            cn_quan_ly   VARCHAR(200),
            ghi_chu      TEXT,
            sdt          VARCHAR(100),
            dia_chi      TEXT,
            dia_chi_en   TEXT,
            is_closed    INTEGER NOT NULL DEFAULT 0,
            sort_order   INTEGER,
            updated_at   DATETIME
        )""",

        # ── Quản trị viên không thuộc phòng nào — 2026-08-05 ──────────────────
        # Migration cũ (dòng ~292) từng gán KSNB cho role='admin'. Nghiệp vụ sau
        # đó đổi: staff.py ép department_id = NULL cho admin/admin_l2. Hai bên
        # đá nhau → sửa+lưu thì mất phòng, khởi động lại thì phòng hiện về.
        # Dọn cả bảng lịch sử, nếu không admin vẫn bị tính là thành viên KSNB
        # trong báo cáo bàn giao (truy vấn hist ở handovers.py).
        "UPDATE user_tttt SET department_id = NULL WHERE role IN ('admin', 'admin_l2')",
        "DELETE FROM staff_department_history WHERE staff_id IN (SELECT id FROM user_tttt WHERE role IN ('admin', 'admin_l2'))",

        # ── Đối chiếu số liệu DTBB — Phòng Kế toán — 2026-08-07 ─────────────────
        # 1 dòng/kỳ/chi nhánh (report_date = ngày cuối kỳ suy từ tên file upload, vd
        # 2026-07-31; branch_code = mã chi nhánh suy từ tên file, '9999' = toàn hệ
        # thống/TSC khi tên file không mang mã chi nhánh — xem
        # reader.py::extract_report_date_and_branch()). UNIQUE(report_date,
        # branch_code) đặt ở khối constraint bảng, không inline theo cột, để 1 ngày
        # có nhiều chi nhánh cùng lưu được.
        # created_by/updated_by để phân biệt lần lưu đầu vs lần ghi đè (FE hỏi xác
        # nhận ghi đè trước khi gọi lại /save — xem dtbb_report_details bên dưới).
        # status: 'pending' (vàng, mới lưu/ghi đè) → 'confirmed' (xanh, đã được
        # Trưởng/Phó phòng Kế toán xác nhận — không phải chính created_by/updated_by).
        # Kỳ đã 'confirmed' bị chặn ghi đè ở API cho tới khi bị 'unconfirm' về pending.
        """CREATE TABLE IF NOT EXISTS dtbb_reports (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            report_date     DATE NOT NULL,
            branch_code     VARCHAR(10) NOT NULL DEFAULT '9999',
            vnd_duoi12      REAL NOT NULL DEFAULT 0,
            vnd_tu12        REAL NOT NULL DEFAULT 0,
            usd_duoi12      REAL NOT NULL DEFAULT 0,
            usd_tu12        REAL NOT NULL DEFAULT 0,
            tk413_usd       REAL NOT NULL DEFAULT 0,
            rate_usd_to_vnd REAL NOT NULL DEFAULT 0,
            file_count      INTEGER NOT NULL DEFAULT 0,
            status          VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','confirmed')),
            confirmed_by    INTEGER REFERENCES user_tttt(id),
            confirmed_at    DATETIME,
            created_by      INTEGER NOT NULL REFERENCES user_tttt(id),
            created_at      DATETIME NOT NULL,
            updated_by      INTEGER REFERENCES user_tttt(id),
            updated_at      DATETIME,
            UNIQUE(report_date, branch_code)
        )""",
        # 1 dòng/loại tiền/kỳ — lưu số dư nguyên tệ (chưa quy đổi) + tỷ giá đã dùng,
        # phục vụ truy vết/kiểm toán lại từng mã tiền thay vì chỉ có tổng cuối cùng.
        """CREATE TABLE IF NOT EXISTS dtbb_report_details (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id       INTEGER NOT NULL REFERENCES dtbb_reports(id) ON DELETE CASCADE,
            ccy             TEXT NOT NULL,
            rate_to_vnd     REAL,
            group1_native   REAL NOT NULL DEFAULT 0,
            group2_native   REAL NOT NULL DEFAULT 0,
            tk413_native    REAL NOT NULL DEFAULT 0,
            UNIQUE(report_id, ccy)
        )""",

        # ── Đồng bộ is_active NULL — 2026-08-11 ───────────────────────────────
        # is_active không NOT NULL và không có DEFAULT nên NULL lọt vào được.
        # Mọi truy vấn đọc đều so `is_active = 1` → NULL vốn đã là "không hoạt
        # động"; ghi hẳn 0 để danh sách user không còn dòng làm hỏng response.
        "UPDATE user_tttt SET is_active = 0 WHERE is_active IS NULL",

        # ── Ảnh chữ ký cá nhân — 2026-08-14 ───────────────────────────────────
        # Bảng riêng, KHÔNG thêm cột BLOB vào user_tttt: get_current_staff()
        # dùng `SELECT *` nên mỗi request sẽ đọc cả ảnh vào bộ nhớ.
        """CREATE TABLE IF NOT EXISTS user_signatures (
            staff_id   INTEGER PRIMARY KEY REFERENCES user_tttt(id) ON DELETE CASCADE,
            filename   TEXT,
            image      BLOB NOT NULL,
            updated_at DATETIME
        )""",

        # ── Chữ ký đã đặt trên đơn nghỉ phép — 2026-08-14 ─────────────────────
        # Toạ độ tính bằng mm từ góc TRÊN-TRÁI trang (hệ của trình duyệt), lật trục
        # y khi dán vào PDF. `image` là BẢN SAO ảnh chữ ký lúc ký, không phải khoá
        # ngoại sang user_signatures: người ký đổi/xoá ảnh cá nhân về sau thì đơn
        # đã ký vẫn phải giữ nguyên đúng thứ họ đã ký.
        """CREATE TABLE IF NOT EXISTS leave_signatures (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            leave_id   INTEGER NOT NULL REFERENCES leave_records(id) ON DELETE CASCADE,
            slot       TEXT    NOT NULL,
            staff_id   INTEGER,
            page       INTEGER NOT NULL DEFAULT 0,
            x_mm       REAL    NOT NULL,
            y_mm       REAL    NOT NULL,
            w_mm       REAL    NOT NULL,
            h_mm       REAL    NOT NULL,
            image      BLOB    NOT NULL,
            signed_at  DATETIME
        )""",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_leave_sig_slot ON leave_signatures(leave_id, slot)",

        # ── Chấm công — Phòng Kế toán — 2026-07-23 ──────────────────────────────
        """CREATE TABLE IF NOT EXISTS attendance_symbols (
            symbol      TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            work_value  REAL NOT NULL DEFAULT 0,
            color       TEXT DEFAULT '#E5E7EB',
            is_active   BOOLEAN DEFAULT 1
        )""",
        """INSERT OR IGNORE INTO attendance_symbols (symbol, description, work_value, color, is_active) VALUES
            ('x',   'Công cả ngày', 1.0, '#DCFCE7', 1),
            ('P',   'Nghỉ phép',    0.0, '#FEE2E2', 1),
            ('0.5', 'Nửa công',     0.5, '#FEF9C3', 1)""",
        """CREATE TABLE IF NOT EXISTS attendances (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id     INTEGER NOT NULL REFERENCES user_tttt(id),
            date         DATE    NOT NULL,
            symbol       TEXT    NOT NULL REFERENCES attendance_symbols(symbol),
            work_value   REAL    NOT NULL DEFAULT 0,
            status       TEXT    NOT NULL DEFAULT 'auto' CHECK(status IN ('auto','adjusted','confirmed')),
            note         TEXT,
            confirmed_by INTEGER REFERENCES user_tttt(id),
            confirmed_at DATETIME,
            created_at   DATETIME,
            updated_at   DATETIME,
            source_leave_id INTEGER REFERENCES leave_records(id),
            UNIQUE(staff_id, date)
        )""",
        # Rà soát vòng 2 PR #22 — 2026-08-10: trước đây trigger revert (huỷ/xoá đơn
        # nghỉ) xác định dòng attendances cần xoá bằng cách khớp lại "ký hiệu suy ra
        # từ leave_type" — nếu 2 đơn nghỉ chồng ngày cùng ra 1 ký hiệu (leaves.py chặn
        # trùng lịch bằng SELECT-rồi-INSERT, không atomic), huỷ đơn cũ có thể xoá nhầm
        # dòng do đơn mới tạo. Thêm cột này để trigger revert khớp đúng theo ID đơn
        # nghỉ đã tạo ra dòng đó, không đoán qua ký hiệu nữa.
        #
        # Sửa theo review vòng 2 PR #22 (Người 1, 2026-08-12): câu ALTER này trước đây
        # nằm ở dòng ~590 (TRƯỚC khối CREATE TABLE attendances) — cài mới trên DB trắng
        # sẽ ALTER một bảng chưa tồn tại → "no such table: attendances", lỗi này KHÔNG
        # nằm trong danh sách nuốt lỗi (cố ý, xem phần xử lý lỗi bên dưới) nên sẽ raise
        # và chặn khởi động app. DB thật đang chạy không lộ vì bảng attendances đã có
        # sẵn từ migration 2026-07-23. Chuyển câu ALTER xuống đây — ngay sau khi bảng
        # chắc chắn đã tồn tại (từ CREATE TABLE IF NOT EXISTS ở trên, dù DB mới hay cũ).
        "ALTER TABLE attendances ADD COLUMN source_leave_id INTEGER REFERENCES leave_records(id)",
        # Rà soát review PR #22 (Người 1, 17/08): trigger revert xoá 'attendances'
        # khi huỷ/xoá đơn nghỉ (trg_leave_unapprove_revert_attendance /
        # trg_leave_delete_revert_attendance), nhưng attendance_adjustments.attendance_id
        # trỏ vào đúng dòng đó mà KHÔNG có ON DELETE — nếu dòng công còn một yêu cầu
        # điều chỉnh (đang chờ hoặc đã bị từ chối) tham chiếu tới, DELETE dính
        # FOREIGN KEY constraint, đơn nghỉ kẹt lại không huỷ được. ON DELETE CASCADE:
        # xoá dòng công thì dọn theo luôn yêu cầu điều chỉnh của chính nó — hợp lý vì
        # yêu cầu điều chỉnh không còn ý nghĩa gì khi dòng công gốc không còn tồn tại.
        # DB đã cài từ trước (bảng đã tạo, thiếu CASCADE) được vá bằng khối tạo lại
        # bảng ngay dưới khối rename ksnb_staff — SQLite không cho ALTER constraint.
        """CREATE TABLE IF NOT EXISTS attendance_adjustments (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            attendance_id   INTEGER NOT NULL REFERENCES attendances(id) ON DELETE CASCADE,
            requested_by    INTEGER NOT NULL REFERENCES user_tttt(id),
            old_symbol      TEXT,
            new_symbol      TEXT NOT NULL,
            old_work_value  REAL,
            new_work_value  REAL NOT NULL,
            reason          TEXT NOT NULL,
            status          TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected')),
            reviewer_id     INTEGER REFERENCES user_tttt(id),
            reviewed_at     DATETIME,
            reject_reason   TEXT,
            created_at      DATETIME
        )""",
        # Trigger: đơn nghỉ phép chuyển sang 'approved' → tự ghi ký hiệu tương ứng vào
        # attendances. Không sửa backend/api/leaves.py (module khác phụ trách) — dùng
        # trigger SQL thuần, tự kích hoạt trên câu UPDATE status thật của leaves.py,
        # không gọi code Python nào từ đó. spread_dates (nghỉ ngày lẻ không liên tục,
        # cột JSON có sẵn trên leave_records): nếu có giá trị thì chỉ đánh dấu đúng các
        # ngày trong JSON đó; nếu NULL thì đánh dấu toàn bộ ngày làm việc trong
        # [start_date,end_date] (bỏ T7/CN + public_holidays — áp dụng cho MỌI leave_type,
        # kể cả thai_san/bao_hiem: quyết định nghiệp vụ 2026-08-10 là lưới chấm công chỉ
        # đánh ngày thường, số ngày phép tính đủ lịch vẫn đúng riêng ở leaves.py, không
        # liên quan lưới này). Chỉ ghi đè dòng đang status='auto' — không đụng dòng đã
        # 'adjusted'/'confirmed' (kế toán đã tự xử lý ngày đó). datetime('now','+7 hours')
        # xấp xỉ _vn_now() vì trigger SQL thuần không gọi được hàm Python — trade-off này
        # được ghi trong Implementation-notes.html.
        #
        # Sửa theo review PR #22 (Người 1, 2026-08-10):
        #  - 'bat_buoc' là leave_type CỦA BẢN GHI GIẢ (import hạn mức phép/đặt số ngày đã
        #    dùng ở leaves.py::import_quota_apply, update_used_days — KHÔNG phải đơn nghỉ
        #    thật) → loại hẳn khỏi trigger, không được đánh bất kỳ ký hiệu nào.
        #  - Chỉ áp dụng cho nhân viên Phòng Kế toán (ACCT) — trước đây chạy cho toàn hệ
        #    thống, phình bảng attendances vô ích cho các phòng không dùng tính năng này.
        #  - Ký hiệu theo leave_type thay vì hardcode 'P': thai_san/bao_hiem→'T', sick→'O',
        #    còn lại (annual/other/personal/dot_xuat...)→'P'.
        # Rà soát vòng 2 PR #22: thêm is_active=1 vào EXISTS (đồng bộ đúng với
        # _acct_staff_rows() ở attendance.py — nhân viên ACCT đã nghỉ việc không còn
        # kích hoạt trigger); ghi thêm source_leave_id để trigger revert bên dưới khớp
        # đúng đơn nghỉ, không đoán qua ký hiệu. DROP trước để đảm bảo DB đã chạy
        # migration cũ (trigger cùng tên) cũng được thay bằng logic mới — CREATE
        # TRIGGER IF NOT EXISTS sẽ bỏ qua nếu trigger cùng tên đã tồn tại.
        #
        # Sửa theo review vòng 2 PR #22 (Người 1, 2026-08-12) — lỗi mới phát sinh từ
        # fix trước: 'bat_buoc' KHÔNG CHỈ là leave_type của bản ghi giả (import hạn
        # mức/đặt số ngày đã dùng) — nó còn là loại nghỉ THẬT nhân viên nộp được
        # (leaves.py validate riêng: phải ≥5 ngày làm việc). Loại hẳn theo leave_type
        # khiến đơn "nghỉ phép bắt buộc" thật của ACCT không được chấm công nghỉ, lưới
        # rơi về mặc định 'x' = đủ công — sai ngược chiều so với lỗi gốc. Dấu hiệu
        # đúng để nhận biết bản ghi giả là REASON (2 nơi tạo bản ghi giả ở leaves.py
        # đều gắn tiền tố cố định "[Import]"/"[Điều chỉnh]"), không phải leave_type.
        # CẢNH BÁO: cách này dựa vào chuỗi text — nếu sau này ai đổi câu chữ reason ở
        # leaves.py (import_quota_apply/update_used_days) mà không cập nhật CASE này
        # thì sẽ hỏng ngầm (bản ghi giả lại bị chấm công, hoặc đơn thật lại bị bỏ qua).
        #
        # Rà soát tiếp theo: leave_records.reason NULLABLE (LeaveCreate.reason cũng
        # optional) — đơn "bat_buoc" THẬT không nhập lý do sẽ có reason=NULL. SQLite:
        # "NULL LIKE '...'" → NULL, không phải FALSE → cả biểu thức NOT (...) thành
        # NULL → WHEN coi NULL là false → trigger KHÔNG chạy, đúng lỗi vừa sửa lại tái
        # phát qua đường NULL. Thêm "reason IS NOT NULL AND" để khi NULL, vế
        # "bat_buoc AND ..." chắc chắn là FALSE (không phải NULL) → NOT FALSE = TRUE
        # → trigger chạy bình thường cho đơn thật.
        "DROP TRIGGER IF EXISTS trg_leave_approved_sync_attendance",
        """CREATE TRIGGER IF NOT EXISTS trg_leave_approved_sync_attendance
            AFTER UPDATE OF status ON leave_records
            WHEN NEW.status = 'approved' AND OLD.status != 'approved'
                 AND NOT (NEW.leave_type = 'bat_buoc' AND NEW.reason IS NOT NULL
                          AND (NEW.reason LIKE '[Import]%' OR NEW.reason LIKE '[Điều chỉnh]%'))
                 AND EXISTS (SELECT 1 FROM user_tttt u JOIN departments d ON d.id = u.department_id
                             WHERE u.id = NEW.staff_id AND d.code = 'ACCT' AND u.is_active = 1)
            BEGIN
                INSERT INTO attendances (staff_id, date, symbol, work_value, status, source_leave_id, created_at, updated_at)
                WITH RECURSIVE d(day) AS (
                    SELECT NEW.start_date
                    UNION ALL
                    SELECT date(day, '+1 day') FROM d WHERE day < NEW.end_date
                )
                SELECT NEW.staff_id, day,
                       CASE NEW.leave_type WHEN 'thai_san' THEN 'T' WHEN 'bao_hiem' THEN 'T'
                            WHEN 'sick' THEN 'O' ELSE 'P' END,
                       (SELECT work_value FROM attendance_symbols WHERE symbol =
                           CASE NEW.leave_type WHEN 'thai_san' THEN 'T' WHEN 'bao_hiem' THEN 'T'
                                WHEN 'sick' THEN 'O' ELSE 'P' END),
                       'auto', NEW.id, datetime('now','+7 hours'), datetime('now','+7 hours')
                FROM d
                WHERE (
                    (NEW.spread_dates IS NOT NULL AND day IN (SELECT value FROM json_each(NEW.spread_dates)))
                    OR
                    (NEW.spread_dates IS NULL AND strftime('%w', day) NOT IN ('0','6')
                         AND day NOT IN (SELECT date FROM public_holidays))
                )
                ON CONFLICT(staff_id, date) DO UPDATE SET
                    symbol = excluded.symbol,
                    work_value = excluded.work_value,
                    status = 'auto',
                    source_leave_id = excluded.source_leave_id,
                    updated_at = datetime('now','+7 hours')
                WHERE attendances.status = 'auto';
            END""",
        # Trigger bổ sung: backend/api/leaves.py::create_direct_leave ("khai báo hộ") INSERT
        # thẳng leave_records với status='approved' ngay từ đầu (không qua UPDATE) — trigger
        # AFTER UPDATE ở trên sẽ không kích hoạt cho trường hợp này. Thêm trigger AFTER INSERT
        # cùng logic để phủ đúng path này (phát hiện khi test thực tế qua API /api/leaves/direct).
        # Cùng các fix bat_buoc/ACCT-only/ký hiệu theo leave_type như trigger UPDATE ở
        # trên, kể cả fix vòng 2 (nhận biết bản ghi giả qua reason, xem comment ở trigger
        # trg_leave_approved_sync_attendance phía trên — không lặp lại toàn bộ ở đây).
        "DROP TRIGGER IF EXISTS trg_leave_direct_insert_sync_attendance",
        """CREATE TRIGGER IF NOT EXISTS trg_leave_direct_insert_sync_attendance
            AFTER INSERT ON leave_records
            WHEN NEW.status = 'approved'
                 AND NOT (NEW.leave_type = 'bat_buoc' AND NEW.reason IS NOT NULL
                          AND (NEW.reason LIKE '[Import]%' OR NEW.reason LIKE '[Điều chỉnh]%'))
                 AND EXISTS (SELECT 1 FROM user_tttt u JOIN departments d ON d.id = u.department_id
                             WHERE u.id = NEW.staff_id AND d.code = 'ACCT' AND u.is_active = 1)
            BEGIN
                INSERT INTO attendances (staff_id, date, symbol, work_value, status, source_leave_id, created_at, updated_at)
                WITH RECURSIVE d(day) AS (
                    SELECT NEW.start_date
                    UNION ALL
                    SELECT date(day, '+1 day') FROM d WHERE day < NEW.end_date
                )
                SELECT NEW.staff_id, day,
                       CASE NEW.leave_type WHEN 'thai_san' THEN 'T' WHEN 'bao_hiem' THEN 'T'
                            WHEN 'sick' THEN 'O' ELSE 'P' END,
                       (SELECT work_value FROM attendance_symbols WHERE symbol =
                           CASE NEW.leave_type WHEN 'thai_san' THEN 'T' WHEN 'bao_hiem' THEN 'T'
                                WHEN 'sick' THEN 'O' ELSE 'P' END),
                       'auto', NEW.id, datetime('now','+7 hours'), datetime('now','+7 hours')
                FROM d
                WHERE (
                    (NEW.spread_dates IS NOT NULL AND day IN (SELECT value FROM json_each(NEW.spread_dates)))
                    OR
                    (NEW.spread_dates IS NULL AND strftime('%w', day) NOT IN ('0','6')
                         AND day NOT IN (SELECT date FROM public_holidays))
                )
                ON CONFLICT(staff_id, date) DO UPDATE SET
                    symbol = excluded.symbol,
                    work_value = excluded.work_value,
                    status = 'auto',
                    source_leave_id = excluded.source_leave_id,
                    updated_at = datetime('now','+7 hours')
                WHERE attendances.status = 'auto';
            END""",
        # Trigger ngược: đơn đã 'approved' bị huỷ/từ chối lại → xoá ký hiệu tự động tương
        # ứng (chỉ xoá nếu vẫn còn status='auto' — nếu đã bị chỉnh tay/duyệt điều chỉnh
        # thành 'adjusted'/'confirmed' thì giữ nguyên, không đụng).
        # Sửa theo review PR #22: trước đây xoá theo cả khoảng BETWEEN start_date/end_date
        # bất kể spread_dates — đơn nghỉ ngày lẻ (vd 2 ngày rời nhau) khi huỷ sẽ xoá lây
        # sang "P"/"T"/"O" của ĐƠN KHÁC nằm lọt trong khoảng đó (đã test thực tế, xem PR).
        # Giờ tôn trọng spread_dates + đúng ký hiệu theo leave_type y hệt trigger ghi, chỉ
        # xoá đúng những ngày/ký hiệu mà trigger ghi từng thực sự tạo ra.
        # Rà soát vòng 2 PR #22: trước đây xoá bằng cách khớp lại ký hiệu suy ra từ
        # leave_type + khoảng ngày — nếu 2 đơn nghỉ chồng ngày cùng ra 1 ký hiệu (có
        # thể xảy ra do leaves.py chặn trùng lịch không atomic), huỷ đơn cũ sẽ xoá
        # nhầm dòng do đơn khác tạo ra. Giờ khớp thẳng theo source_leave_id — chỉ xoá
        # đúng dòng do chính đơn nghỉ này tạo, không cần đoán qua ký hiệu/khoảng ngày nữa.
        # Sửa theo review PR #22 (Người 1, 17/08): luồng "thu hồi đơn đã duyệt"
        # (leaves.py::request_recall/approve_recall) đi 2 bước — approved →
        # pending_tong_hop (request_recall), rồi pending_tong_hop → cancelled
        # (approve_recall). Ở bước UPDATE cuối cùng OLD.status đã là
        # 'pending_tong_hop', không còn 'approved' → trigger cũ không chạy, "P" mồ
        # côi ở lại vĩnh viễn. Thêm 'pending_tong_hop' vào WHEN để bắt cả 2 luồng.
        # An toàn cho các đường pending_tong_hop khác (bị Tổng hợp từ chối trước khi
        # từng được duyệt): DELETE chỉ xoá đúng dòng status='auto' khớp
        # source_leave_id — đơn chưa từng approved thì chưa từng được trigger ghi
        # sync tạo dòng nào, DELETE không khớp gì, vô hại.
        "DROP TRIGGER IF EXISTS trg_leave_unapprove_revert_attendance",
        """CREATE TRIGGER IF NOT EXISTS trg_leave_unapprove_revert_attendance
            AFTER UPDATE OF status ON leave_records
            WHEN OLD.status IN ('approved','pending_tong_hop') AND NEW.status IN ('cancelled','rejected')
            BEGIN
                DELETE FROM attendances
                WHERE staff_id = NEW.staff_id
                  AND status = 'auto'
                  AND source_leave_id = NEW.id;
            END""",
        # Trigger mới theo review PR #22: 3 chỗ trong leaves.py xoá thẳng bản ghi
        # leave_records (xoá đơn khai báo hộ, rollback batch import) không có trigger dọn
        # attendances tương ứng — để lại ký hiệu "mồ côi" vĩnh viễn. Logic xoá giống hệt
        # trigger unapprove ở trên, chỉ khác sự kiện kích hoạt (DELETE thay vì UPDATE).
        # Cùng fix vòng 2 nhận biết bản ghi giả qua reason (không phải leave_type) —
        # xem comment đầy đủ ở trg_leave_approved_sync_attendance. Bắt buộc phải sửa
        # trigger này theo cùng điều kiện: nếu chỉ trigger ghi cho phép đơn 'bat_buoc'
        # thật đi qua mà trigger xoá này vẫn chặn theo leave_type cũ, huỷ/xoá đơn
        # 'bat_buoc' thật sẽ không dọn được dòng attendances đã ghi — để lại mồ côi.
        "DROP TRIGGER IF EXISTS trg_leave_delete_revert_attendance",
        """CREATE TRIGGER IF NOT EXISTS trg_leave_delete_revert_attendance
            AFTER DELETE ON leave_records
            WHEN OLD.status = 'approved'
                 AND NOT (OLD.leave_type = 'bat_buoc' AND OLD.reason IS NOT NULL
                          AND (OLD.reason LIKE '[Import]%' OR OLD.reason LIKE '[Điều chỉnh]%'))
            BEGIN
                DELETE FROM attendances
                WHERE staff_id = OLD.staff_id
                  AND status = 'auto'
                  AND source_leave_id = OLD.id;
            END""",

        # ── Gỡ bỏ Check-in/out tự động — 2026-07-29 (người dùng đổi ý, không dùng
        # nữa) — DROP thay vì để nguyên CREATE, vì DB đang chạy sống đã lỡ tạo
        # bảng/trigger này ở migration trước đó (2026-07-24), cần dọn sạch. Không
        # xoá/sửa lịch sử migration cũ, chỉ nối thêm bước dọn dẹp phía sau.
        "DROP TRIGGER IF EXISTS trg_login_sync_checkin",
        "DROP TABLE IF EXISTS attendance_checkin_logs",

        # ── Bổ sung ký hiệu chấm công theo đúng mẫu giấy thật của Phòng Kế toán
        # (file 5_BANG_CHAM_CONG_PHONG_KE_TOAN_2026.xlsx) — 2026-08-05. CT/H/HT vẫn
        # tính đủ 1 công (công tác/đi học/hội thao vẫn là đi làm, không phải nghỉ);
        # T/ND/O/S/C không tính công, giống 'P' — theo xác nhận của người dùng.
        """INSERT OR IGNORE INTO attendance_symbols (symbol, description, work_value, color, is_active) VALUES
            ('T',  'Nghỉ thai sản',    0.0, '#FDE68A', 1),
            ('ND', 'Nghỉ dưỡng',       0.0, '#FBCFE8', 1),
            ('CT', 'Công tác',         1.0, '#BFDBFE', 1),
            ('O',  'Nghỉ ốm',          0.0, '#E5E7EB', 1),
            ('H',  'Đi học',           1.0, '#C7D2FE', 1),
            ('S',  'Nghỉ ốm dài ngày', 0.0, '#D1D5DB', 1),
            ('C',  'Cưới',             0.0, '#FBCFE8', 1),
            ('HT', 'Hội Thao',         1.0, '#A7F3D0', 1)""",
        # Backfill theo review PR #22 (Người 1, 18/08): fix trước đó (put_day /
        # review_adjustment reset source_leave_id=NULL khi ghi đè) chỉ áp dụng cho
        # LƯỢT GHI MỚI kể từ lúc code chạy — dòng attendances đã ở trạng thái
        # 'confirmed'/'adjusted' TỪ TRƯỚC bản vá vẫn còn source_leave_id trỏ về đơn
        # nghỉ cũ, xoá đúng đơn đó vẫn dính FOREIGN KEY constraint y hệt lỗi gốc.
        # Tự nhiên idempotent: sau lần chạy đầu dọn sạch, các lần sau WHERE không
        # còn dòng nào khớp nên vô hại — không cần dò sqlite_master như khối vá bảng.
        """UPDATE attendances SET source_leave_id = NULL
           WHERE status IN ('confirmed','adjusted') AND source_leave_id IS NOT NULL""",

        # ── Đối chiếu CITAD — Lưu bản tạm / Lưu bản cuối — 2026-08-20 ─────────
        # `status`: 'draft' (bản tạm — người KHÁC người lập bảng vẫn vào được để
        # nạp riêng Napas/PSS-MDP qua Extension) | 'final' (bản cuối — CHỐT,
        # không ai sửa được nữa kể cả người lập bảng, chỉ Admin mở khoá qua
        # endpoint riêng). Default 'final' để dữ liệu CŨ (lưu trước khi có tính
        # năng này, qua nút "Lưu" duy nhất) coi như đã chốt sẵn — không tự
        # nhiên biến thành bản tạm ai cũng sửa Napas được.
        # `created_by`: người lập bảng — người ĐẦU TIÊN lưu ngày đó, cố định
        # suốt vòng đời bản ghi (không đổi theo `updated_by`, vốn là người lưu
        # SAU CÙNG — 2 khái niệm khác nhau, cần tách riêng để biết ai được sửa
        # đủ mọi trường, ai chỉ được nạp Napas/PSS-MDP). Backfill từ
        # `updated_by` cho dữ liệu cũ — không có thông tin ai lập bảng thật sự
        # trước đây, đây là ước lượng hợp lý nhất có thể.
        "ALTER TABLE doi_chieu_citad_sessions ADD COLUMN status TEXT NOT NULL DEFAULT 'final'",
        "ALTER TABLE doi_chieu_citad_sessions ADD COLUMN created_by INTEGER REFERENCES user_tttt(id) ON DELETE SET NULL",
        "UPDATE doi_chieu_citad_sessions SET created_by = updated_by WHERE created_by IS NULL",
        "ALTER TABLE doi_chieu_citad_history ADD COLUMN status TEXT NOT NULL DEFAULT 'final'",

        # ── Đối chiếu CITAD - PaymentHub (Nostro, Vostro) — người lập bảng ──
        # Bảng đã có `created_by` ngay trong _create_tables(); ALTER này chỉ
        # vá DB đã tạo bảng ở bản nhánh trước đó (lỗi "duplicate column" được
        # nuốt có chủ đích). Backfill từ `updated_by` vì bản ghi cũ không có
        # thông tin ai lập bảng thật sự.
        "ALTER TABLE doi_chieu_citad_nostro_sessions ADD COLUMN created_by INTEGER REFERENCES user_tttt(id) ON DELETE SET NULL",
        "UPDATE doi_chieu_citad_nostro_sessions SET created_by = updated_by WHERE created_by IS NULL",

        # ── Đối chiếu CITAD — nhật ký từng lượt sửa bảng tạm — 2026-08-21 ─────
        # Các lần "Lưu bảng tạm" LIÊN TIẾP gộp vào CHUNG 1 dòng
        # doi_chieu_citad_history (UPDATE tại chỗ, tránh phình Lịch sử — xem
        # docstring session_save()), nên dòng lịch sử đó không còn giữ dấu vết
        # từng người đã góp phần sửa. Bảng riêng này ghi lại MỌI lần lưu,
        # không gộp, gắn theo history_id của dòng đang đại diện cho bản ghi đó
        # — phục vụ icon "Ai đã sửa bảng tạm này" trên tab Lịch sử.
        """CREATE TABLE IF NOT EXISTS doi_chieu_citad_history_edits (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            history_id  INTEGER NOT NULL REFERENCES doi_chieu_citad_history(id) ON DELETE CASCADE,
            staff_id    INTEGER NOT NULL REFERENCES user_tttt(id) ON DELETE CASCADE,
            created_at  DATETIME NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS ix_doi_chieu_citad_history_edits_history_id ON doi_chieu_citad_history_edits(history_id)",

        # ── ACH — cấp phát cham_ach.process khi bắt đầu enforce — 2026-08-31 ──
        # cham_ach.process đã khai trong FEATURES từ trước nhưng CHƯA từng được
        # require_feature() kiểm tra thật (mọi endpoint /start /continue /cancel
        # trước PR#54 chỉ đòi menu.cham_ach). Nhóm nào trong DB thật đang có
        # menu.cham_ach nhiều khả năng KHÔNG có cham_ach.process — bắt đầu
        # enforce mà không cấp bù thì mọi user không phải admin mất nút "Chạy"
        # ngay khi deploy (review PR#54, khanhbq693). Cấp bù = giữ nguyên hành
        # vi trước merge; QTV vẫn thu hồi tay được sau nếu muốn tách quyền thật.
        """INSERT OR IGNORE INTO group_features (group_id, feature_code)
           SELECT group_id, 'cham_ach.process' FROM group_features
           WHERE feature_code = 'menu.cham_ach'""",
        # ── Ôn tập trắc nghiệm (Quizz) — 2026-08-26 ───────────────────────
        # Bản sao của khối trong _create_tables(): DB đã cài từ trước không
        # chạy lại _create_tables cho bảng mới thêm sau này.
        # ── Ôn tập trắc nghiệm (Quizz) ────────────────────────────────────
        # Bộ câu hỏi nhập MỘT LẦN từ Excel rồi dùng chung cho cả cơ quan —
        # `content_hash` để nhận ra ai đó tải lại đúng file cũ dưới tên khác.
        """CREATE TABLE IF NOT EXISTS quiz_sets (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            name           VARCHAR(200) NOT NULL UNIQUE,
            description    TEXT,
            source_file    TEXT,
            content_hash   VARCHAR(64),
            question_count INTEGER NOT NULL DEFAULT 0,
            created_by     INTEGER REFERENCES user_tttt(id) ON DELETE SET NULL,
            created_at     DATETIME NOT NULL,
            is_active      INTEGER NOT NULL DEFAULT 1
        )""",
        # opt4 để trống được: file mẫu có cả câu 3 lựa chọn.
        """CREATE TABLE IF NOT EXISTS quiz_questions (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            set_id     INTEGER NOT NULL REFERENCES quiz_sets(id) ON DELETE CASCADE,
            order_no   INTEGER NOT NULL,
            content    TEXT NOT NULL,
            opt1       TEXT,
            opt2       TEXT,
            opt3       TEXT,
            opt4       TEXT,
            correct_no INTEGER NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS quiz_attempts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            set_id          INTEGER NOT NULL REFERENCES quiz_sets(id) ON DELETE CASCADE,
            staff_id        INTEGER NOT NULL REFERENCES user_tttt(id) ON DELETE CASCADE,
            mode            TEXT NOT NULL DEFAULT 'practice',
            settings        TEXT,
            total_questions INTEGER NOT NULL DEFAULT 0,
            correct_count   INTEGER,
            score           REAL,
            duration_ms     INTEGER,
            status          TEXT NOT NULL DEFAULT 'in_progress',
            elapsed_ms      INTEGER NOT NULL DEFAULT 0,
            current_idx     INTEGER NOT NULL DEFAULT 0,
            saved_at        DATETIME,
            started_at      DATETIME NOT NULL,
            finished_at     DATETIME
        )""",
        # Sinh sẵn đủ N dòng lúc tạo lượt: thứ tự câu và thứ tự đáp án đã trộn
        # phải lưu lại, nếu không màn "Xem lại bài" sẽ dựng ra một đề khác hẳn
        # với đề người dùng vừa làm.
        """CREATE TABLE IF NOT EXISTS quiz_attempt_items (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            attempt_id   INTEGER NOT NULL REFERENCES quiz_attempts(id) ON DELETE CASCADE,
            question_id  INTEGER NOT NULL REFERENCES quiz_questions(id) ON DELETE CASCADE,
            order_no     INTEGER NOT NULL,
            option_order TEXT NOT NULL,
            chosen_no    INTEGER,
            is_correct   INTEGER,
            time_ms      INTEGER
        )""",
        "CREATE INDEX IF NOT EXISTS ix_quiz_questions_set      ON quiz_questions(set_id, order_no)",
        "CREATE INDEX IF NOT EXISTS ix_quiz_attempts_staff     ON quiz_attempts(staff_id, started_at)",
        "CREATE INDEX IF NOT EXISTS ix_quiz_attempts_set       ON quiz_attempts(set_id, status)",
        "CREATE INDEX IF NOT EXISTS ix_quiz_attempt_items_att  ON quiz_attempt_items(attempt_id, order_no)",
        # ── Quizz: tạm dừng & làm tiếp — 2026-08-27 ───────────────────────
        # Ba cột giữ chỗ người làm đang đứng, để lần vào sau nối tiếp đúng chỗ.
        # NOT NULL kèm DEFAULT hằng số nên ALTER TABLE của SQLite chấp nhận được.
        "ALTER TABLE quiz_attempts ADD COLUMN elapsed_ms INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE quiz_attempts ADD COLUMN current_idx INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE quiz_attempts ADD COLUMN saved_at DATETIME",
        # ── Chuẩn hoá văn bản theo QĐ 979 — 2026-08-27 ─────────────────
        # Đúng MỘT dòng: quy chuẩn trình bày là của cả cơ quan, không phải của
        # từng người. CHECK(id = 1) chặn thẳng ở tầng DB — code có ghi nhầm
        # dòng thứ hai thì báo lỗi ngay, thay vì âm thầm sinh ra hai bản cấu hình
        # rồi mỗi lần đọc lại trúng một bản khác nhau.
        """CREATE TABLE IF NOT EXISTS vb_format_config (
            id          INTEGER PRIMARY KEY CHECK (id = 1),
            config_json TEXT NOT NULL DEFAULT '{}',
            updated_at  DATETIME,
            updated_by  INTEGER REFERENCES user_tttt(id) ON DELETE SET NULL
        )""",
        "INSERT OR IGNORE INTO vb_format_config (id, config_json) VALUES (1, '{}')",

        # ── dtbb_reports.rate_usd_to_vnd — 2026-08-27 ─────────────────────────
        # Lưu lại tỷ giá VND/USD (ttbuyrt/taxrt fallback) đã dùng lúc tính, để FE
        # tính "USD quy đổi" theo từng mã tiền khi xem lại kỳ đã lưu — mỗi mã tiền
        # chỉ lưu tỷ giá riêng của nó (rate_to_vnd), không lưu tỷ giá USD dùng làm
        # mẫu số nên không tái tạo được nếu thiếu cột này. Kỳ lưu trước bản vá có
        # giá trị mặc định 0 — FE nhận biết 0 để ẩn hẳn cột thay vì hiện số sai.
        "ALTER TABLE dtbb_reports ADD COLUMN rate_usd_to_vnd REAL NOT NULL DEFAULT 0",

        # ── Người 3 — Nghỉ phép bắt buộc: điều chỉnh ngày sau khi đã duyệt —
        # 2026-09-03 ────────────────────────────────────────────────────────
        # Nút "Điều chỉnh ngày NPBB" (chỉ đơn bat_buoc đã approved) tạo 1 ĐƠN
        # MỚI riêng (không ghi đè đơn gốc) — cột này trỏ ngược về đơn gốc. Đơn
        # gốc vẫn "Hoàn thành" cho tới khi đơn điều chỉnh duyệt xong đủ 3 bước
        # thì mới tự chuyển "Đã hủy" (xem npbb_adjust_leave, gd_review trong
        # backend/api/leaves.py). Báo cáo NPBB (mẫu 18/19 TCNS) so sánh ngày
        # "đã đăng ký" (đơn gốc) vs "điều chỉnh" (đơn này) qua liên kết đó.
        "ALTER TABLE leave_records ADD COLUMN adjusts_leave_id INTEGER REFERENCES leave_records(id)",

        # ── Người 3 — Ứng trước ngày phép của năm sau khi hết hạn mức năm nay —
        # 2026-09-04 ────────────────────────────────────────────────────────
        # Lưu ĐÚNG phần ngày vượt hạn mức năm nay mà người tạo đơn đã đồng ý
        # "ứng" trước vào quỹ phép năm sau (KHÔNG phải phần đơn tự nhiên vắt
        # qua ranh giới năm — phần đó tính lại từ ngày thật của đơn, xem
        # _calc_used_days). Xem _check_quota_or_borrow trong backend/api/leaves.py.
        "ALTER TABLE leave_records ADD COLUMN borrow_next_year_days REAL DEFAULT 0",
    ]
    _mig_log = logging.getLogger(__name__)

    # ── Rename ksnb_staff → user_tttt (one-time, idempotent) ─────────────────
    # PHẢI chạy TRƯỚC schema_migrations: mọi câu SQL trong list dùng tên mới `user_tttt`.
    # Nếu để sau, DB cũ (còn tên `ksnb_staff`) sẽ trượt toàn bộ migration bên dưới.
    _rc = sqlite3.connect(DB_PATH, timeout=30)
    try:
        _existing = {r[0] for r in _rc.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "ksnb_staff" in _existing:
            if "user_tttt" in _existing:
                # _create_tables() đã tạo user_tttt rỗng trước — xóa đi để rename.
                # Chỉ xóa khi thật sự rỗng: bảng có dữ liệu nghĩa là tình huống ngoài dự kiến,
                # thà dừng lại còn hơn mất dữ liệu nhân sự.
                _n = _rc.execute("SELECT COUNT(*) FROM user_tttt").fetchone()[0]
                if _n:
                    raise RuntimeError(
                        f"Tồn tại song song 2 bảng: ksnb_staff và user_tttt (user_tttt có {_n} dòng). "
                        "Không tự động gộp — cần xử lý thủ công trước khi khởi động."
                    )
                _rc.execute("DROP TABLE user_tttt")
            _rc.execute("ALTER TABLE ksnb_staff RENAME TO user_tttt")
            _rc.commit()
            _mig_log.info("Đã đổi tên bảng ksnb_staff → user_tttt")
    finally:
        _rc.close()

    # ── Vá attendance_adjustments.attendance_id thiếu ON DELETE CASCADE (one-time,
    # idempotent) — 2026-08-18, theo review PR #22 (Người 1). SQLite không cho ALTER
    # TABLE sửa ràng buộc FK, nên tạo bảng mới đúng schema, copy dữ liệu, xoá bảng
    # cũ, đổi tên. Bảng cài mới đã có CASCADE sẵn từ CREATE TABLE IF NOT EXISTS ở
    # trên nên khối này bỏ qua (điều kiện "ON DELETE CASCADE" not in sql không khớp).
    _ac = sqlite3.connect(DB_PATH, timeout=30)
    try:
        _adj_row = _ac.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='attendance_adjustments'"
        ).fetchone()
        if _adj_row and _adj_row[0] and "ON DELETE CASCADE" not in _adj_row[0]:
            _ac.execute("PRAGMA foreign_keys = OFF")
            _ac.execute("""CREATE TABLE attendance_adjustments_new (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                attendance_id   INTEGER NOT NULL REFERENCES attendances(id) ON DELETE CASCADE,
                requested_by    INTEGER NOT NULL REFERENCES user_tttt(id),
                old_symbol      TEXT,
                new_symbol      TEXT NOT NULL,
                old_work_value  REAL,
                new_work_value  REAL NOT NULL,
                reason          TEXT NOT NULL,
                status          TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected')),
                reviewer_id     INTEGER REFERENCES user_tttt(id),
                reviewed_at     DATETIME,
                reject_reason   TEXT,
                created_at      DATETIME
            )""")
            _ac.execute("INSERT INTO attendance_adjustments_new SELECT * FROM attendance_adjustments")
            _ac.execute("DROP TABLE attendance_adjustments")
            _ac.execute("ALTER TABLE attendance_adjustments_new RENAME TO attendance_adjustments")
            _ac.commit()
            _mig_log.info("Đã thêm ON DELETE CASCADE cho attendance_adjustments.attendance_id")
    finally:
        _ac.close()

    # ── Vá dtbb_reports: thêm branch_code + status xác nhận, đổi UNIQUE từ
    # report_date đơn sang (report_date, branch_code) — one-time, idempotent.
    # 2026-08-27. SQLite không cho ALTER TABLE sửa ràng buộc UNIQUE nên phải tạo
    # bảng mới đúng schema, copy dữ liệu cũ (branch_code mặc định '9999', status
    # mặc định 'pending' — kỳ đã lưu trước bản vá này coi như chưa được xác nhận),
    # xoá bảng cũ, đổi tên. Bảng cài mới đã đúng schema từ CREATE TABLE IF NOT
    # EXISTS ở trên nên khối này bỏ qua (điều kiện "branch_code" not in sql không khớp).
    _db = sqlite3.connect(DB_PATH, timeout=30)
    try:
        _dtbb_row = _db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='dtbb_reports'"
        ).fetchone()
        if _dtbb_row and _dtbb_row[0] and "branch_code" not in _dtbb_row[0]:
            _db.execute("PRAGMA foreign_keys = OFF")
            _db.execute("""CREATE TABLE dtbb_reports_new (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                report_date     DATE NOT NULL,
                branch_code     VARCHAR(10) NOT NULL DEFAULT '9999',
                vnd_duoi12      REAL NOT NULL DEFAULT 0,
                vnd_tu12        REAL NOT NULL DEFAULT 0,
                usd_duoi12      REAL NOT NULL DEFAULT 0,
                usd_tu12        REAL NOT NULL DEFAULT 0,
                tk413_usd       REAL NOT NULL DEFAULT 0,
                rate_usd_to_vnd REAL NOT NULL DEFAULT 0,
                file_count      INTEGER NOT NULL DEFAULT 0,
                status          VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','confirmed')),
                confirmed_by    INTEGER REFERENCES user_tttt(id),
                confirmed_at    DATETIME,
                created_by      INTEGER NOT NULL REFERENCES user_tttt(id),
                created_at      DATETIME NOT NULL,
                updated_by      INTEGER REFERENCES user_tttt(id),
                updated_at      DATETIME,
                UNIQUE(report_date, branch_code)
            )""")
            _db.execute("""INSERT INTO dtbb_reports_new
                (id, report_date, vnd_duoi12, vnd_tu12, usd_duoi12, usd_tu12, tk413_usd,
                 file_count, created_by, created_at, updated_by, updated_at)
                SELECT id, report_date, vnd_duoi12, vnd_tu12, usd_duoi12, usd_tu12, tk413_usd,
                       file_count, created_by, created_at, updated_by, updated_at
                FROM dtbb_reports""")
            _db.execute("DROP TABLE dtbb_reports")
            _db.execute("ALTER TABLE dtbb_reports_new RENAME TO dtbb_reports")
            _db.commit()
            _mig_log.info("Đã thêm branch_code/status cho dtbb_reports (UNIQUE report_date,branch_code)")
    finally:
        _db.close()

    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        for s in schema_migrations:
            try:
                conn.execute(s)
                conn.commit()
            except Exception as exc:
                conn.rollback()
                msg = str(exc).lower()
                # Nuốt có chủ đích: migration đã chạy ở lần khởi động trước.
                # KHÔNG thêm "no such table" vào đây — sai tên bảng phải báo lỗi,
                # nếu không migration hỏng sẽ trôi qua im lặng (cột không được thêm).
                if "duplicate column" not in msg and "already exists" not in msg and "already another table" not in msg:
                    if "database is locked" in msg or "locked" in msg:
                        _mig_log.warning("Migration skipped (DB locked, sẽ thử lại lần sau): %.80s", s)
                    else:
                        _mig_log.error("Migration failed: %s — %s", s, exc)
                        raise
    finally:
        conn.close()

    # ── Rebuild handovers: received_by_id NOT NULL → nullable, thêm UNIQUE(dept,date) ──
    _raw = sqlite3.connect(DB_PATH)
    _raw.isolation_level = None  # autocommit để PRAGMA foreign_keys hoạt động
    try:
        _cur = _raw.cursor()
        _cur.execute("PRAGMA table_info(handovers)")
        _h_cols = {r[1]: r[3] for r in _cur.fetchall()}  # {col_name: notnull_flag}
        _cur.execute("PRAGMA index_list(handovers)")
        # origin='u' → UNIQUE constraint (phân biệt với 'c' = CREATE INDEX thường)
        _uniq_ok = any(r[2] and r[3] == 'u' for r in _cur.fetchall())
        _needs_rebuild = bool(_h_cols.get('received_by_id', 0)) or not _uniq_ok
        if _needs_rebuild:
            _mig_log = logging.getLogger(__name__)
            _mig_log.info("Rebuilding handovers table (received_by_id → nullable, UNIQUE added)...")
            _cur.execute("PRAGMA foreign_keys = OFF")
            _cur.execute("PRAGMA legacy_alter_table = ON")
            _cur.execute("BEGIN EXCLUSIVE")
            try:
                _cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='handovers'")
                _tbl_ok = bool(_cur.fetchone())
                _cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='_handovers_bak'")
                _bak_ok = bool(_cur.fetchone())
                if _tbl_ok:
                    if _bak_ok:
                        _cur.execute("DROP TABLE _handovers_bak")
                    _cur.execute("ALTER TABLE handovers RENAME TO _handovers_bak")
                elif not _bak_ok:
                    raise RuntimeError("Không tìm thấy dữ liệu handovers để migrate")
                _cur.execute("""
                    CREATE TABLE handovers (
                        id INTEGER NOT NULL PRIMARY KEY,
                        department_id INTEGER NOT NULL,
                        handover_date DATE NOT NULL,
                        received_by_id INTEGER,
                        delivered_by VARCHAR(100),
                        notes TEXT,
                        status VARCHAR(20),
                        created_at DATETIME,
                        UNIQUE(department_id, handover_date)
                    )
                """)
                _cur.execute("""
                    INSERT INTO handovers
                    SELECT id, department_id, handover_date, received_by_id,
                           delivered_by, notes, status, created_at
                    FROM _handovers_bak
                """)
                _cur.execute("DROP TABLE _handovers_bak")
                _cur.execute("COMMIT")
                logging.getLogger(__name__).info("handovers rebuild hoàn tất")
            except Exception as _me:
                _cur.execute("ROLLBACK")
                logging.getLogger(__name__).error("handovers rebuild thất bại: %s", _me)
                raise
            finally:
                _cur.execute("PRAGMA legacy_alter_table = OFF")
                _cur.execute("PRAGMA foreign_keys = ON")
    finally:
        _raw.close()

    # ── Rebuild document_entries: source_user_id NOT NULL → nullable ────────────
    _raw_de = sqlite3.connect(DB_PATH)
    _raw_de.isolation_level = None
    try:
        _cur_de = _raw_de.cursor()
        _cur_de.execute("PRAGMA table_info(document_entries)")
        _de_notnull = {r[1]: r[3] for r in _cur_de.fetchall()}
        if _de_notnull.get("source_user_id", 0):  # notnull=1 → cần fix
            _mig_log2 = logging.getLogger(__name__)
            _mig_log2.info("Rebuilding document_entries (source_user_id NOT NULL → nullable)...")
            _cur_de.execute("PRAGMA foreign_keys = OFF")
            _cur_de.execute("PRAGMA legacy_alter_table = ON")
            _cur_de.execute("BEGIN EXCLUSIVE")
            try:
                _cur_de.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='_de_bak'")
                if _cur_de.fetchone():
                    _cur_de.execute("DROP TABLE _de_bak")
                _cur_de.execute("ALTER TABLE document_entries RENAME TO _de_bak")
                _cur_de.execute("""
                    CREATE TABLE document_entries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        handover_id INTEGER NOT NULL REFERENCES handovers(id),
                        source_user_id INTEGER,
                        transaction_date DATE NOT NULL,
                        sheet_count INTEGER NOT NULL,
                        notes TEXT,
                        entry_status TEXT DEFAULT 'confirmed',
                        entered_by_id INTEGER REFERENCES user_tttt(id),
                        confirmed_by_id INTEGER REFERENCES user_tttt(id),
                        confirmed_at DATETIME,
                        borrowed_at DATETIME,
                        borrow_reason TEXT,
                        staff_id INTEGER REFERENCES user_tttt(id)
                    )
                """)
                _cur_de.execute("INSERT INTO document_entries SELECT * FROM _de_bak")
                _cur_de.execute("DROP TABLE _de_bak")
                _cur_de.execute("COMMIT")
                _mig_log2.info("document_entries rebuild hoàn tất")
            except Exception as _de_err:
                _cur_de.execute("ROLLBACK")
                logging.getLogger(__name__).error("document_entries rebuild thất bại: %s", _de_err)
                raise
            finally:
                _cur_de.execute("PRAGMA legacy_alter_table = OFF")
                _cur_de.execute("PRAGMA foreign_keys = ON")
    finally:
        _raw_de.close()

    # ── Rebuild doi_chieu_citad_sessions: khoá (ngay, staff_id) → khoá ngay riêng ──
    # CREATE TABLE IF NOT EXISTS ở _create_tables() không làm gì trên DB đã có
    # bảng này với schema CŨ (từ trước khi đổi sang "1 bản ghi CHUNG/ngày") —
    # session_save() mới dùng INSERT ... ON CONFLICT(ngay) sẽ lỗi trên bảng cũ
    # (thiếu cột updated_by, khoá chính không khớp ON CONFLICT(ngay), cột
    # staff_id NOT NULL không được cấp giá trị). SQLite không đổi khoá chính
    # tại chỗ nên phải dựng bảng mới, chép dữ liệu, xoá bảng cũ, đổi tên.
    _raw_dc = sqlite3.connect(DB_PATH)
    _raw_dc.isolation_level = None
    try:
        _cur_dc = _raw_dc.cursor()
        _cur_dc.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='doi_chieu_citad_sessions'")
        if _cur_dc.fetchone():
            _cur_dc.execute("PRAGMA table_info(doi_chieu_citad_sessions)")
            _dc_cols = {r[1] for r in _cur_dc.fetchall()}
            if "staff_id" in _dc_cols:  # dấu hiệu bảng vẫn còn schema cũ
                _mig_log3 = logging.getLogger(__name__)
                _mig_log3.info("Rebuilding doi_chieu_citad_sessions (khoá (ngay, staff_id) → khoá ngay riêng)...")
                _cur_dc.execute("PRAGMA foreign_keys = OFF")
                _cur_dc.execute("PRAGMA legacy_alter_table = ON")
                _cur_dc.execute("BEGIN EXCLUSIVE")
                try:
                    _cur_dc.execute(
                        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='_doi_chieu_citad_sessions_bak'"
                    )
                    if _cur_dc.fetchone():
                        _cur_dc.execute("DROP TABLE _doi_chieu_citad_sessions_bak")
                    _cur_dc.execute("ALTER TABLE doi_chieu_citad_sessions RENAME TO _doi_chieu_citad_sessions_bak")
                    _cur_dc.execute("""
                        CREATE TABLE doi_chieu_citad_sessions (
                            ngay        TEXT    PRIMARY KEY,
                            data        TEXT    NOT NULL,
                            updated_at  DATETIME,
                            updated_by  INTEGER REFERENCES user_tttt(id) ON DELETE SET NULL
                        )
                    """)
                    # Bảng cũ có thể nhiều dòng/ngày (1 dòng/staff_id) — mỗi ngày chỉ
                    # giữ lại ĐÚNG 1 dòng: người lưu SAU CÙNG (updated_at lớn nhất,
                    # lệch giờ thì lấy staff_id lớn hơn để có kết quả tất định).
                    _cur_dc.execute("""
                        INSERT INTO doi_chieu_citad_sessions (ngay, data, updated_at, updated_by)
                        SELECT ngay, data, updated_at, staff_id
                        FROM (
                            SELECT ngay, data, updated_at, staff_id,
                                   ROW_NUMBER() OVER (
                                       PARTITION BY ngay ORDER BY updated_at DESC, staff_id DESC
                                   ) AS rn
                            FROM _doi_chieu_citad_sessions_bak
                        )
                        WHERE rn = 1
                    """)
                    _cur_dc.execute("DROP TABLE _doi_chieu_citad_sessions_bak")
                    _cur_dc.execute("COMMIT")
                    _mig_log3.info("doi_chieu_citad_sessions rebuild hoàn tất")
                except Exception as _dc_err:
                    _cur_dc.execute("ROLLBACK")
                    logging.getLogger(__name__).error("doi_chieu_citad_sessions rebuild thất bại: %s", _dc_err)
                    raise
                finally:
                    _cur_dc.execute("PRAGMA legacy_alter_table = OFF")
                    _cur_dc.execute("PRAGMA foreign_keys = ON")
    finally:
        _raw_dc.close()

    index_stmts = [
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_entry_staff_date ON document_entries(handover_id, staff_id, transaction_date)",
        "CREATE INDEX IF NOT EXISTS ix_source_users_dept      ON source_users(department_id)",
        "CREATE INDEX IF NOT EXISTS ix_doc_entries_user        ON document_entries(source_user_id)",
        "CREATE INDEX IF NOT EXISTS ix_doc_entries_staff       ON document_entries(staff_id)",
        "CREATE INDEX IF NOT EXISTS ix_doc_entries_handover    ON document_entries(handover_id)",
        "CREATE INDEX IF NOT EXISTS ix_doc_entries_date        ON document_entries(transaction_date)",
        "CREATE INDEX IF NOT EXISTS ix_handovers_dept          ON handovers(department_id)",
        "CREATE INDEX IF NOT EXISTS ix_handovers_recv          ON handovers(received_by_id)",
        "CREATE INDEX IF NOT EXISTS ix_bundle_groups_dept      ON bundle_groups(department_id)",
        "CREATE INDEX IF NOT EXISTS ix_bundle_groups_creator   ON bundle_groups(created_by_id)",
        "CREATE INDEX IF NOT EXISTS ix_bundles_group           ON bundles(group_id)",
        "CREATE INDEX IF NOT EXISTS ix_bundles_custodian       ON bundles(custodian_id)",
        "CREATE INDEX IF NOT EXISTS ix_bundle_items_bundle     ON bundle_items(bundle_id)",
        "CREATE INDEX IF NOT EXISTS ix_bundle_items_entry      ON bundle_items(entry_id)",
        "CREATE INDEX IF NOT EXISTS ix_leave_records_staff     ON leave_records(staff_id)",
        "CREATE INDEX IF NOT EXISTS ix_doc_entries_status      ON document_entries(entry_status)",
        "CREATE INDEX IF NOT EXISTS ix_entry_change_logs_entry ON entry_change_logs(entry_id)",
        "CREATE INDEX IF NOT EXISTS ix_entry_change_logs_actor ON entry_change_logs(performed_by_id)",
        "CREATE INDEX IF NOT EXISTS ix_leave_records_ksv    ON leave_records(ksv_approver_id)",
        "CREATE INDEX IF NOT EXISTS ix_leave_records_gd     ON leave_records(gd_approver_id)",
        "CREATE INDEX IF NOT EXISTS ix_doi_soat_citad_history_date ON doi_soat_citad_history(recon_date)",
        "CREATE INDEX IF NOT EXISTS ix_doi_chieu_citad_history_ngay ON doi_chieu_citad_history(ngay)",
        "CREATE INDEX IF NOT EXISTS ix_delegation_gd        ON delegation_records(giam_doc_id)",
        "CREATE INDEX IF NOT EXISTS ix_delegation_pgd       ON delegation_records(pho_giam_doc_id)",
        "CREATE INDEX IF NOT EXISTS ix_leave_records_th     ON leave_records(tong_hop_approver_id)",
        "CREATE INDEX IF NOT EXISTS ix_leave_action_logs    ON leave_action_logs(leave_id)",
        "CREATE INDEX IF NOT EXISTS ix_public_holidays_date ON public_holidays(date)",
        "CREATE INDEX IF NOT EXISTS ix_login_logs_username  ON login_logs(username)",
        "CREATE INDEX IF NOT EXISTS ix_login_logs_created    ON login_logs(created_at)",
        "CREATE INDEX IF NOT EXISTS ix_login_sessions_exp    ON login_sessions(expires_at)",
        "CREATE INDEX IF NOT EXISTS ix_audit_logs_actor      ON audit_logs(actor_id)",
        "CREATE INDEX IF NOT EXISTS ix_audit_logs_created    ON audit_logs(created_at)",
        "CREATE INDEX IF NOT EXISTS ix_user_tttt_dept        ON user_tttt(department_id)",
        "CREATE INDEX IF NOT EXISTS ix_staff_dept_hist       ON staff_department_history(staff_id, effective_from)",
        "CREATE INDEX IF NOT EXISTS ix_ttqt_branches_bic      ON ttqt_branches(swift_bic)",
        "CREATE INDEX IF NOT EXISTS ix_ttqt_branches_sort     ON ttqt_branches(is_closed, sort_order)",
        "CREATE INDEX IF NOT EXISTS ix_dtbb_reports_date       ON dtbb_reports(report_date)",
        "CREATE INDEX IF NOT EXISTS ix_dtbb_reports_status     ON dtbb_reports(status)",
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_dtbb_reports_date_branch ON dtbb_reports(report_date, branch_code)",
        "CREATE INDEX IF NOT EXISTS ix_dtbb_report_details_rpt ON dtbb_report_details(report_id)",
        "CREATE INDEX IF NOT EXISTS ix_so_truc_records_date ON so_truc_records(truc_date)",
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_so_truc_active_date ON so_truc_records(truc_date) WHERE status != 'cancelled'",
        # Rác còn lại sau lần đổi tên bảng ksnb_staff → user_tttt: index cũ vẫn
        # nằm nguyên trên bảng mới. `ix_ksnb_staff_dept` trùng y hệt
        # `ix_user_tttt_dept`, còn `ix_ksnb_staff_id` phủ lên chính khoá chính
        # (rowid) nên không câu truy vấn nào dùng tới. Không sai kết quả, chỉ
        # bắt SQLite ghi thừa mỗi lần thêm/sửa cán bộ.
        "DROP INDEX IF EXISTS ix_ksnb_staff_dept",
        "DROP INDEX IF EXISTS ix_ksnb_staff_id",
        "CREATE INDEX IF NOT EXISTS ix_attendances_date           ON attendances(date)",
        "CREATE INDEX IF NOT EXISTS ix_attendance_adj_attendance  ON attendance_adjustments(attendance_id)",
        "CREATE INDEX IF NOT EXISTS ix_attendance_adj_status      ON attendance_adjustments(status)",
        "CREATE INDEX IF NOT EXISTS ix_attendance_adj_requested_by ON attendance_adjustments(requested_by)",
        "CREATE INDEX IF NOT EXISTS ix_quiz_questions_set      ON quiz_questions(set_id, order_no)",
        "CREATE INDEX IF NOT EXISTS ix_quiz_attempts_staff     ON quiz_attempts(staff_id, started_at)",
        "CREATE INDEX IF NOT EXISTS ix_quiz_attempts_set       ON quiz_attempts(set_id, status)",
        "CREATE INDEX IF NOT EXISTS ix_quiz_attempt_items_att  ON quiz_attempt_items(attempt_id, order_no)",
        # ── Quản lý nhân sự — 2026-08-28 ──────────────────────────────────────
        # Mọi màn hình hồ sơ đều lọc theo staff_id trước tiên.
        "CREATE INDEX IF NOT EXISTS ix_hr_degrees_staff      ON hr_degrees(staff_id)",
        "CREATE INDEX IF NOT EXISTS ix_hr_appointments_staff ON hr_appointments(staff_id)",
        "CREATE INDEX IF NOT EXISTS ix_hr_work_history_staff ON hr_work_history(staff_id)",
        "CREATE INDEX IF NOT EXISTS ix_hr_breaks_staff       ON hr_breaks(staff_id)",
        "CREATE INDEX IF NOT EXISTS ix_hr_salaries_staff     ON hr_salaries(staff_id, decision_date)",
        "CREATE INDEX IF NOT EXISTS ix_hr_trainings_staff    ON hr_trainings(staff_id)",
        "CREATE INDEX IF NOT EXISTS ix_hr_tools_staff        ON hr_tools(staff_id)",
        "CREATE INDEX IF NOT EXISTS ix_hr_attachments_owner  ON hr_attachments(section, item_id)",
        # ── Nghỉ phép bắt buộc — 2026-09-05 ────────────────────────────────────
        # _leave_to_out tra adjusts_leave_id cho mỗi đơn bat_buoc (tìm đơn điều
        # chỉnh) — list_leaves gọi hàm này cho TỪNG dòng nên thiếu index này
        # khiến mỗi đơn bat_buoc quét lại toàn bộ leave_records, chi phí tăng
        # theo bình phương số dòng thay vì tuyến tính.
        "CREATE INDEX IF NOT EXISTS ix_leave_records_adj ON leave_records(adjusts_leave_id)",
    ]
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        for s in index_stmts:
            try:
                conn.execute(s)
            except Exception as _idx_exc:
                if "already exists" not in str(_idx_exc).lower() and "no such table" not in str(_idx_exc).lower():
                    raise
        conn.commit()
    finally:
        conn.close()
