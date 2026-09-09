# Hệ thống của TTTT - Agribank

---

## Cài đặt

### 1. Yêu cầu
- Python 3.10+
- Windows / Linux / macOS
- **Microsoft Word** trên máy chạy backend — chỉ cần cho việc xuất **đơn nghỉ phép bản PDF**
  (Word chuyển `.docx` → `.pdf`). Không có Word thì hệ thống vẫn chạy đủ, riêng phần ký đơn
  lui về tải bản `.docx` không chữ ký.
  Backend **giữ sẵn một bản Word chạy ngầm** để không phải mở/đóng Word cho từng tờ đơn
  (~0,3 giây thay vì ~5 giây mỗi lần xem trước). Bản này chiếm ~130 MB RAM và tự tắt sau
  15 phút không ai dùng. Chỉnh bằng `WORD_SERVER`, `WORD_IDLE_SECONDS`, `WORD_MAX_JOBS`
  trong `.env` — xem `.env.example`.
  **Máy người dùng không cần Word** — họ chỉ dùng trình duyệt.
  > ⚠️ **Word đòi một phiên có người đăng nhập trên máy chủ** — xem
  > [mục riêng bên dưới](#word-đòi-phiên-đăng-nhập-trên-máy-chủ)

### 2. Tạo môi trường ảo và cài thư viện

```bash
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt

# Máy phát triển (muốn chạy pytest) dùng file này thay cho dòng trên —
# nó đã bao gồm toàn bộ requirements.txt, chỉ thêm pytest
pip install -r requirements-dev.txt
```

### 3. Khởi tạo database

```bash
python init_db.py
```

Kết quả:
```
✓ Database đã khởi tạo thành công!
Tài khoản đăng nhập:
  Admin : admin / Admin@2024!
```
> ⚠️ Đổi mật khẩu ngay sau lần đăng nhập đầu tiên.

### 4. Cấu hình `.env` (bắt buộc)

Copy `.env.example` thành `.env` rồi điền hai khoá bí mật — **thiếu là hệ thống không khởi động**:

```bash
python -c "import secrets; print(secrets.token_hex(32))"   # chạy 2 lần, lấy 2 giá trị khác nhau
```

```ini
SECRET_KEY=<giá trị 1>       # khoá ký JWT (backend)
STORAGE_SECRET=<giá trị 2>   # khoá ký cookie phiên (frontend)
```

> Trên Windows, `start.bat` **tự sinh cả hai** nếu `.env` chưa có hoặc còn thiếu — không cần làm tay.
> Đổi `STORAGE_SECRET` sẽ đăng xuất toàn bộ người dùng đang đăng nhập một lần.

Chạy thật trên mạng nội bộ thì đặt thêm (xem mục [Truy cập LAN](#truy-cập-lan-nhiều-người-dùng)):

```ini
ENV=production                                  # tắt /docs, /redoc, /openapi.json
```

> `ALLOWED_ORIGINS` **chỉ cần khi có máy khác gọi thẳng cổng 8000 từ trình duyệt.** Với
> `BACKEND_HOST=127.0.0.1` (mặc định `start.bat` sinh ra) thì không cần đặt: trình duyệt
> chỉ nói chuyện với frontend cổng 8080, CORS không tham gia vào đường đi nào cả.

Hai mật khẩu nghiệp vụ — không bắt buộc để khởi động, nhưng thiếu là mất tính năng hoặc mất lớp bảo vệ:

```ini
DOI_CHIEU_ZIP_PASSWORD=<mật khẩu file ZIP do đơn vị cấp file đặt>
BACKUP_PASSWORD=<mật khẩu nén bản sao lưu>
```

| Biến | Thiếu thì sao |
|---|---|
| `DOI_CHIEU_ZIP_PASSWORD` | Đối chiếu ACH / Chấm 459901 / Đối chiếu Song phương báo lỗi rõ khi giải nén; phần còn lại chạy bình thường. Trước 20/08/2026 mật khẩu này nằm cứng trong mã nguồn nên **đã đi vào lịch sử git** — nếu chưa đổi thì coi như đã lộ. |
| `CHAM459901_FOLDER_ROOTS` | Chấm 459901 **khoá** chế độ *Chọn thư mục server* (bấm vào báo lỗi nói rõ phải thêm gì); chế độ tải file lên không ảnh hưởng. Đây là danh sách thư mục được phép quét, ngăn nhau bằng dấu `;` — đường dẫn người dùng gõ phải nằm trong đó. |
| `BACKUP_PASSWORD` | Bản sao lưu ghi ra `.db` **không mã hoá** (chứa mã băm mật khẩu toàn bộ tài khoản), kèm cảnh báo trong log mỗi lần backup. Xem mục [Backup tự động](#backup-tự-động). |

> `start.bat` **tự sinh `BACKUP_PASSWORD`** nếu `.env` chưa có, và in ra màn hình đúng một lần —
> chép ngay vào két mật khẩu của đơn vị. `DOI_CHIEU_ZIP_PASSWORD` phải điền tay vì đó là mật khẩu
> của bên cấp file, không phải của phần mềm này — không có cách nào tự sinh hộ.

> **Nâng cấp máy đang chạy:** `deploy.bat` không chép đè `.env` của máy đích, nên biến mới thêm vào
> giữa vòng đời hệ thống **không tự sang**. Từ 22/08/2026 `deploy.bat` in cảnh báo (bước 1/8, nhắc lại
> ở khung tổng kết cuối) khi `.env` máy đích còn thiếu biến thuộc loại phải gõ tay — hiện là
> `DOI_CHIEU_ZIP_PASSWORD` và `CHAM459901_FOLDER_ROOTS`. Biến mới cùng loại thì thêm vào bảng `CHI_CANH_BAO` trong
> `scripts/deploy_env_check.py`; chỉ đưa vào đó thứ mà **thiếu là gãy tính năng**, không thì bảng
> thành danh sách dài ai cũng bỏ qua.

Hai biến tuỳ chọn liên quan đến hiệu năng và mức độ kín của backend:

```ini
BACKEND_URL=http://127.0.0.1:8000   # frontend gọi backend — KHÔNG dùng localhost
BACKEND_HOST=127.0.0.1              # địa chỉ backend lắng nghe
```

> **Đừng dùng `localhost` cho `BACKEND_URL`.** Trên Windows nó phân giải ra `::1` (IPv6)
> trước, mà uvicorn chỉ lắng nghe IPv4 → mỗi kết nối mới tốn thêm ~2 giây chờ IPv6
> thất bại. Đo được: `localhost` 2062 ms so với `127.0.0.1` 18 ms. Không đặt dòng này
> cũng được — mặc định trong code đã là `127.0.0.1`.

> `BACKEND_HOST=127.0.0.1` kín hơn: trình duyệt người dùng chỉ nói chuyện với frontend
> cổng 8080, không bao giờ chạm cổng 8000. Extension CITAD cũng đi qua proxy cổng 8080.
> Chỉ đổi sang `0.0.0.0` khi chắc chắn **có máy khác gọi thẳng API** — và khi đó phải đặt
> luôn `ALLOWED_ORIGINS`.
>
> `start.bat` sinh `.env` mới với `127.0.0.1`, và `deploy.bat` kiểm tra rồi hỏi sửa khi
> máy đích đang để `0.0.0.0`. Mặc định trong code (khi `.env` không có dòng này) vẫn là
> `0.0.0.0` — nên cứ ghi rõ ra `.env` thay vì dựa vào mặc định.

### 5. Chạy hệ thống

```bash
python run.py
```

Truy cập:
- **Giao diện web**: http://localhost:8080
- **API docs**: http://localhost:8000/docs — chỉ khi `ENV=development`. Ở `production`
  cả `/docs`, `/redoc` và `/openapi.json` đều trả 404; cần xem để gỡ lỗi thì đặt
  `ENABLE_API_DOCS=1`, **không** hạ `ENV` xuống `development`
- **Từ máy khác trong LAN**: http://[IP-máy-chủ]:8080

> **Windows — dùng `start.bat`.** Script tự kiểm tra `.venv` và **vá tại chỗ** (~2 giây) khi thư mục dự án
> được mang sang máy khác (chạy từ USB), thay vì xoá và cài lại toàn bộ thư viện. Máy mới cần **Python 3.10.x**;
> bản 3.11/3.12 sẽ buộc cài lại thư viện và **cần internet**.
>
> Sửa file `.bat` / `.ps1` phải giữ xuống dòng **CRLF** — `.gitattributes` đã ép sẵn khi clone/checkout,
> nhưng công cụ ghi file thường mặc định LF và `cmd.exe` chạy sai file .bat dạng LF mà không báo lỗi rõ.

---

## Cấu trúc hệ thống

```
├── backend/
│   ├── main.py              # FastAPI app + schema migration khi khởi động
│   ├── database.py          # SQLite engine (WAL mode, FK via PRAGMA)
│   ├── core/
│   │   ├── config.py        # Cấu hình (SECRET_KEY, DATABASE_URL, NTP...)
│   │   ├── security.py      # JWT + bcrypt
│   │   ├── deps.py          # FastAPI dependencies (RBAC)
│   │   ├── sessions.py      # Session lưu DB (bảng login_sessions) — không mất khi restart
│   │   ├── audit_middleware.py # Ghi nhật ký thao tác tập trung → audit_logs
│   │   ├── audit_queue.py   # Hàng đợi + 1 luồng ghi audit, không chặn response
│   │   ├── concurrency.py   # Giới hạn số việc nặng chạy đồng thời (sinh Word/Excel)
│   │   ├── paths.py         # Đường dẫn template có dấu — chống lệch chuẩn hoá Unicode NFC/NFD
│   │   ├── net.py           # IP thật của người dùng — chỉ tin X-Client-IP từ máy đáng tin
│   │   ├── uploads.py       # Trần kích thước upload + làm sạch tên file (chống ghi ra ngoài thư mục)
│   │   └── rate_limit.py    # Chặn dò mật khẩu — đếm theo tên đăng nhập VÀ theo địa chỉ máy
│   ├── api/
│   │   ├── auth.py          # Đăng nhập / đăng xuất / đổi mật khẩu
│   │   ├── staff.py         # Quản lý cán bộ
│   │   ├── departments.py   # Phòng ban
│   │   ├── groups.py        # Nhóm cán bộ
│   │   ├── handovers.py     # Phiếu bàn giao chứng từ
│   │   ├── bundles.py       # Gom tập + in bìa
│   │   ├── leaves.py        # Nghỉ phép (workflow 3 bước)
│   │   ├── delegations.py   # Ủy quyền Giám đốc
│   │   ├── dashboard.py     # Tổng quan thống kê
│   │   ├── reports.py       # Báo cáo hậu kiểm
│   │   ├── handover_reports.py # Báo cáo bàn giao chứng từ (đúng hạn/quá hạn)
│   │   ├── th_reports.py    # Báo cáo tổng hợp (phòng TH)
│   │   ├── swift_recon.py   # Đối chiếu điện SWIFT (phòng Swift)
│   │   ├── duty_schedule.py # Lịch trực
│   │   ├── duty_staff.py    # Cán bộ trực
│   │   ├── duty_constraints.py # Ràng buộc lịch trực
│   │   ├── duty_stats.py    # Thống kê lịch trực
│   │   ├── duty_export.py   # Xuất lịch trực
│   │   ├── cham459901.py    # Phân loại bút toán TK 459901
│   │   ├── doi_chieu_song_phuong.py # Đối chiếu song phương (định tuyến lệnh IPCAS)
│   │   ├── ttqt_branches.py # Danh mục CN thực hiện TTQT (CRUD + import/export Excel)
│   │   ├── logs.py          # Nhật ký hệ thống (admin)
│   │   └── holidays.py      # Quản lý ngày lễ (admin)
│   └── services/
│       ├── bundle_service.py       # Thuật toán gom tập (max 350 tờ)
│       ├── cover_service.py        # Tạo bìa tập chứng từ (docxtpl)
│       ├── archive_cover_service.py# Bìa hồ sơ lưu trữ M01/LHS (đọc Excel tra cứu → điền XML)
│       ├── report_service.py       # Xuất báo cáo Excel
│       ├── handover_report_service.py # Tính chứng từ nộp đúng hạn / quá hạn
│       ├── th_report_service.py    # Xuất báo cáo tổng hợp (phòng TH)
│       ├── backup_service.py       # Backup SQLite tự động
│       ├── log_cleanup_service.py  # Dọn login_logs / audit_logs quá hạn theo lịch
│       ├── time_sync.py            # Cảnh báo lệch giờ máy chủ so NTP (không tự sửa, có cache)
│       ├── cham459901_service.py   # Xử lý ZIP/Excel + phân loại bút toán 459901
│       ├── doi_chieu_song_phuong_service.py # Định tuyến lệnh IPCAS theo NH + chiều → 8 CSV
│       ├── swift_recon/            # Đối chiếu điện SWIFT (parse, so khớp, export Excel)
│       └── duty_*                  # Xếp lịch trực, ràng buộc, thống kê, xuất file (6 module)
├── frontend/
│   ├── main.py              # NiceGUI entry point
│   ├── shared.py            # Layout chung (sidebar, header, helpers)
│   ├── ui_kit.py            # Nguồn sự thật: màu, trạng thái, khung chờ, font
│   ├── le_29.py             # Trang trí chủ đề Quốc khánh 2-9 (tự bật 25/8–3/9)
│   ├── api_client.py        # httpx wrapper → backend
│   └── pages/
│       ├── login.py         # Đăng nhập
│       ├── dashboard.py     # Tổng quan
│       ├── pending_work.py  # Màn hình theo dõi việc chờ xử lý (/pending/<loại>)
│       ├── staff.py         # Quản lý cán bộ
│       ├── groups.py        # Quản lý nhóm
│       ├── group_features.py # Phân quyền theo nhóm
│       ├── handovers.py     # Bàn giao chứng từ
│       ├── bundles.py       # Gom tập + in bìa
│       ├── storage.py       # Lưu trữ tập (số hộp, vị trí kệ) + In bìa hồ sơ M01/LHS
│       ├── ttqt_branches.py # Danh sách CN thực hiện TTQT
│       ├── leaves.py        # Nghỉ phép
│       ├── duty_schedule.py # Lịch trực
│       ├── cham_459901.py   # Phân loại bút toán TK 459901
│       ├── doi_chieu_song_phuong.py # Đối chiếu song phương (định tuyến lệnh IPCAS)
│       ├── reports.py       # Báo cáo hậu kiểm
│       ├── handover_reports.py # Báo cáo bàn giao chứng từ (đúng hạn/quá hạn)
│       ├── th_reports.py    # Báo cáo tổng hợp
│       ├── swift_recon.py   # Đối chiếu điện SWIFT (phòng Swift)
│       ├── user_management.py # Quản lý tài khoản (admin)
│       ├── login_logs.py    # Nhật ký đăng nhập (admin)
│       ├── audit_logs.py    # Nhật ký thao tác — lịch sử ghi dữ liệu (admin)
│       ├── logs.py          # Nhật ký lỗi & cảnh báo (admin)
│       └── change_password.py # Đổi mật khẩu
├── templates/                       # ⚠ Tên thư mục có dấu — xem ghi chú bên dưới
│   ├── bia_mau_goc.docx             # Mẫu bìa tập chứng từ
│   ├── don_xin_nghi_phep_tpl.docx  # Template phiếu nghỉ phép (mẫu chung, dùng khi thiếu mẫu riêng)
│   ├── Phòng Tổng hợp/
│   │   └── Nghỉ phép/               # Mẫu đơn riêng theo chức danh (_nv/_tp/_gd/_pgd.docx)
│   └── Phòng KSNB&HTVH/
│       └── Bàn giao cho lưu trữ/
│           ├── Bia_ho_so.doc        # Mẫu gốc do bên lưu trữ cấp (giữ để đối chiếu)
│           └── Bia_ho_so.docx       # Bản dùng lúc chạy (chuyển từ .doc, render giống hệt)
├── data/
│   ├── ksnb.db             # SQLite database (tự tạo khi chạy lần đầu)
│   ├── backups/            # Backup tự động — xem mục "Backup tự động"
│   └── temp_*/             # File tải lên + kết quả tạm của ACH / Chấm 459901 /
│                           #   Đối chiếu song phương / Đối soát CITAD. Sống hết ngày làm
│                           #   việc, temp_cleanup_service xoá sạch lúc 23h (không chờ ai
│                           #   mở menu). Backend bật giữa ngày chỉ dọn rác của hôm trước
├── logs/
│   ├── app.log             # Log xoay vòng (5 MB × 3 file) — nguồn của màn hình Nhật ký hệ thống
│   ├── backend.log         # stdout/stderr tiến trình backend (run.py ghi) — xoay khi >20 MB, giữ 3 đời
│   ├── frontend.log        # stdout/stderr tiến trình frontend (run.py ghi) — xoay khi >20 MB, giữ 3 đời
│   └── *.truoc-utf8.log    # Phần log ghi trước bản vá UTF-8, run.py tự tách ra một lần
├── init_db.py               # Khởi tạo DB + seed data
├── run.py                   # Launcher (chạy backend + frontend song song; ép UTF-8 cho tiến trình con)
├── .github/workflows/       # CI — chạy pytest mỗi lần push / mở PR
├── docs/                    # Tài liệu dự án (README.md, CLAUDE.md, Logs_update.md ở gốc)
│   ├── DESIGN.md                # Patterns & business logic
│   ├── SKILL.md                 # Nguyên tắc & quy ước làm việc
│   ├── CONTRIBUTING.md          # Quy tắc đóng góp
│   ├── Implementation-notes.html # Ghi chú kỹ thuật, quyết định thiết kế (bản đang dùng)
│   └── Implementation-notes.md   # Bản cũ, giữ làm lịch sử
├── scripts/                 # Script phụ trợ chạy tay hoặc do deploy.bat gọi
│   ├── deploy_env_check.py      # Kiểm/sửa .env máy đích khi deploy
│   ├── deploy_don_file_thua.py  # Dò file .py cũ còn sót trên máy đích
│   ├── import_users_csv.py      # Nạp data/user_tttt.csv vào bảng user_tttt
│   ├── tach_mau_vb.py           # Tách 18 mẫu Phụ lục V ra templates/vb_mau/
│   └── sua_moc_thoi_gian_o_chung_tu.py  # Sửa tay mốc thời gian một ô chứng từ (ca lẻ 03/09/2026)
└── requirements.txt
```

> ⚠️ **Thư mục template có dấu tiếng Việt: luôn dùng `template_path()` trong `backend/core/paths.py`, không dùng `os.path.join`.**
> Tên thư mục trên đĩa (và trong git) ở dạng Unicode **NFD**, còn chuỗi gõ trong mã nguồn là **NFC** — hai chuỗi khác nhau về byte, Windows không tự chuẩn hoá, nên `os.path.exists()` trả về `False` dù thư mục vẫn ở đó. Thư mục con (`Nghỉ phép`, `Bàn giao cho lưu trữ`) cũng NFD, nên phải đưa **toàn bộ** các đoạn vào `template_path()`, đừng resolve nửa chừng rồi `join` tiếp.
>
> Thêm file mẫu mới thì **copy/paste vào thư mục đang có sẵn**, **đừng gõ tay tên thư mục** để tạo mới — bộ gõ sinh NFC và sẽ đẻ ra thư mục thứ hai trùng tên (đã từng xảy ra với `Phòng Tổng hợp`, hậu quả là mẫu đơn riêng theo chức danh không bao giờ được dùng mà không báo lỗi gì). `tests/test_paths.py` canh việc này.

---

## Chức năng

### Module Nhân sự & Tài khoản
- Quản lý cán bộ theo phòng ban, vai trò (8 vai trò — xem bảng RBAC)
- Quản lý nhóm cán bộ và phân quyền tính năng theo nhóm
- Dashboard tổng quan: KPI người dùng & phòng nghiệp vụ, bảng nghỉ phép hôm nay theo phòng, biểu đồ cột tỷ lệ nộp chứng từ đúng hạn/muộn theo 4 phòng (chọn tháng/năm để xem). **Mọi vai trò đều vào Trang chủ sau khi đăng nhập**
- **Chủ đề kỷ niệm 2-9**: từ 25/8 đến hết 3/9 hằng năm, Trang chủ và trang Đăng nhập tự đổi nền + hiện khẩu hiệu chào mừng Cách mạng Tháng Tám và Quốc khánh; hết khoảng ngày tự trở lại giao diện thường. Khoảng ngày và nội dung nằm trong `frontend/le_29.py`
- **Công việc chờ xử lý**: khối ở đầu sidebar, hiện trên mọi trang — số chứng từ chờ xác nhận và đơn nghỉ phép chờ duyệt của **chính người đang đăng nhập**; bấm vào mở màn hình theo dõi `/pending/<loại>` có đủ chi tiết và link nhảy thẳng tới ô cần xử lý
- **Nhật ký thao tác** (audit log): middleware ghi tập trung mọi request thay đổi dữ liệu (POST/PUT/PATCH/DELETE) vào bảng `audit_logs` — ai, làm gì, kết quả HTTP, IP, thời gian; tự dọn sau 365 ngày
  - **Kèm tóm tắt dữ liệu gửi lên** (`backend/core/audit_body.py`): query string + body JSON, để cột *Chi tiết* nói được **đã sửa cái gì** chứ không chỉ "HTTP 200". Ba giới hạn cố ý — chỉ đọc body JSON ≤ 8 KB (bỏ qua multipart/file), **che khoá nhạy cảm** (mật khẩu, token, ảnh chữ ký — nhật ký xuất Excel được nên coi như đã công khai), và cắt còn tối đa 800 ký tự
  - **Bấm một dòng** để mở hộp thoại xem đầy đủ, kể cả nguyên văn bản ghi
  - **Lọc** theo phương thức, từ khoá, **khoảng ngày, người thao tác, module** (`GET /api/admin/logs/audit/filters` đổ dữ liệu vào hai ô chọn — chỉ liệt kê người đã thực sự có dòng trong nhật ký)
- Nhật ký đăng nhập và nhật ký lỗi/cảnh báo hệ thống (admin xem, lọc theo user/thời gian)
- **Ảnh chữ ký cá nhân** (menu *Quản lý người dùng*, mọi vai trò kể cả chuyên viên): tải lên ảnh
  **PNG nền trong suốt**, tối đa 2 MB, mỗi người một ảnh. Ảnh lưu trong DB (bảng `user_signatures`)
  nên đi cùng bản sao lưu `.db`; chỉ xem/sửa/xoá được ảnh **của chính mình**. Dùng để ký đơn nghỉ phép
- **Trạng thái tài khoản** — cột `user_tttt.is_active` cho phép NULL (dữ liệu cũ, đường *Nhập DB*). **NULL = tạm khoá**, thống nhất với `WHERE is_active = 1` ở đăng nhập và danh sách cán bộ; migration lúc khởi động ghi hẳn về `0`, `StaffOut` cũng ép NULL → `False` để một dòng bỏ trống không làm hỏng cả response `/api/staff/`
- **Nhập Ngày vào ngành hàng loạt từ Excel** (nút *Nhập Ngày vào ngành*, feature `staff.import_join_date`)
  — `POST /api/staff/import-join-dates`, khớp theo **Mã cán bộ**, chỉ ghi cột `join_industry_date`.
  Dòng tiêu đề cột được dò trong 15 dòng đầu (file thật có dòng trống ở trên); dòng nào ô Mã cán bộ
  rỗng thì bỏ qua (tiêu đề nhóm phòng). Nhận ngày dạng `dd/mm/yyyy`, `yyyy-mm-dd`, ô định dạng Date,
  và serial Excel; **loại mọi năm ngoài 1950 → năm hiện tại**. Mặc định `overwrite=false` — chỉ điền
  vào ô đang trống, ai đã có ngày khác thì được liệt kê chứ không bị đè. Giao diện luôn chạy
  `dry_run=true` trước để xem số dòng sẽ đổi / mã không khớp / ô ngày hỏng, chỉ mở nút ghi khi thật sự
  có thay đổi. Người đã xoá (`is_deleted = 1`) không được khớp; endpoint **không tạo tài khoản mới**

- **Xuất / Nhập file DB người dùng** (`staff.export` · `staff.import_db`) — dùng để di trú toàn bộ
  tài khoản sang hệ thống khác **mà không phải đặt lại mật khẩu**, nên file mang theo nguyên
  `pwd_hash` và `role`. Vì thế **cả hai đường đều chỉ Quản trị viên (cấp 1/2) gọi được**, xét theo
  vai trò thật chứ không chỉ theo feature. Đường nhập còn bỏ qua — và báo lại danh sách bỏ qua —
  các dòng có `role` sai chính tả, `department_id` không tồn tại, hoặc thiếu Mã cán bộ; khớp theo
  **Mã cán bộ**. ⚠️ **Số liệu phép (`used_leave_days`, `annual_leave_days`, `carryover_notice_year`)
  của tài khoản đã có thì KHÔNG bị đè** — đó là dữ liệu của module Nghỉ phép, nơi có batch nhập +
  hoàn tác riêng; tài khoản mới thì vẫn lấy theo file. `tests/test_import_db_an_toan.py` canh việc này

### Module Nghỉ phép
- Cán bộ tạo đơn xin nghỉ (phép năm, ốm, việc riêng, khác)
- Workflow duyệt 3 bước: **KSV → Tổng hợp → Giám đốc**
- Ủy quyền Giám đốc: GĐ có thể ủy quyền cho PGĐ trong khoảng thời gian xác định
- Tải phiếu nghỉ phép dạng **`.pdf`** đúng mẫu (Word chuyển từ `.docx`; máy không có Word → lui về `.docx`)
- **Ký đơn trên bản in**: lúc gửi đơn và lúc phê duyệt (KSV, Ban lãnh đạo) hiện popup xem trước
  **chính bản in thật**, kéo/thu phóng ảnh chữ ký cá nhân vào đúng ô ký rồi mới gửi/duyệt.
  Mở màn Nghỉ phép là backend tự đánh thức Word ở nền, nên đến lúc bấm nút gần như không phải chờ.
  Chữ ký được **sao lại vào đơn** tại thời điểm ký — sau này đổi hoặc xoá ảnh chữ ký cá nhân
  thì đơn đã ký không đổi theo. Nộp lại đơn bị từ chối sẽ xoá chữ ký của người duyệt.
  Chưa có ảnh chữ ký (Quản lý người dùng → Ảnh chữ ký) thì vẫn gửi/duyệt được, chỉ là phiếu trống ô ký.
  *Duyệt hàng loạt và bước Tổng hợp không ký.*
- **Lịch nghỉ tháng chỉ hiện người cùng phòng.** Xem được toàn trung tâm: admin, GĐ/PGĐ, nhân viên
  phòng Tổng hợp — đúng tiêu chí `scope="all"` của `list_leaves()`. Hậu kiểm viên **không** nằm trong
  danh sách này (họ ngang chuyên viên ở quy trình nghỉ phép). Rê chuột vào ô ngày để xem đủ danh sách
- Theo dõi quota phép năm (hạn ngạch / đã dùng); chuyển tiếp ngày phép chưa dùng năm trước sang Q1
- Banner "Phép còn lại" tính đủ hạn mức nhập tay + ngày chuyển kỳ, khớp đúng tab Hạn mức phép
- Đơn nghỉ vắt qua ranh giới năm (vd 29/12 → 02/01) được chia đúng cho từng năm khi tính hạn mức
- Nghỉ thai sản / bảo hiểm (không trừ vào hạn mức phép năm), chọn khoảng ngày bằng lịch cuộn
- **Nghỉ không lương** và **Họp/Công tác** — đi đủ 3 bước duyệt như đơn thường nhưng **không trừ hạn
  mức phép năm**. *Nghỉ không lương* chọn khoảng ngày liên tục; *Họp/Công tác* chọn lẻ từng ngày như
  phép năm. Ở bảng công phòng Kế toán, Họp/Công tác vào ký hiệu **`CT` = đủ 1 công** (đang đi làm, chỉ
  không có mặt tại trụ sở), nghỉ không lương vào `P` = 0 công
- **Nghỉ "Khác"**: người tạo đơn tự chọn nút gạt *Trừ vào hạn mức phép năm* — bật thì tính y hệt đơn
  nghỉ phép năm (trừ hạn mức, cộng vào số ngày đã nghỉ, có thể phải ứng phép năm sau); tắt thì chỉ ghi
  nhận ngày nghỉ, không đụng tới hạn mức — giống thai sản / bảo hiểm / không lương / họp-công tác.
  Cột `leave_records.other_deduct_quota`; đơn "Khác" tạo **trước 06/09/2026** mặc định là **có trừ**,
  đúng bằng hành vi cũ
- Nhập hạn mức phép hàng loạt từ file Excel (xem trước / áp dụng / hoàn tác); sửa tay số ngày "Đã dùng" của từng người — cả hai cách đều thay thế lẫn nhau, không cộng dồn
- Bản ghi hạn mức nhập từ Excel / sửa tay không phải đơn nghỉ thật: bị ẩn khỏi danh sách đơn, lịch, kiểm tra trùng ngày, số liệu Dashboard, Trang chủ và Báo cáo bàn giao
- Khai báo hộ; ngày nghỉ lẻ không liên tục (`spread_dates`)
- Bảng nghỉ phép hôm nay trên Trang chủ theo từng phòng — **chỉ đếm đơn đã duyệt** (lịch tháng trong menu thì hiện cả đơn đang chờ, kèm nhãn trạng thái)
- Chống duyệt trùng: hai người (hoặc hai tab) bấm duyệt cùng lúc thì chỉ lần đầu có hiệu lực, lần sau báo đơn đã được xử lý
- Resubmit đơn bị từ chối; huỷ đơn đang chờ hoặc đã duyệt
- **Nghỉ phép bắt buộc (NPBB)**: đơn đã "Hoàn thành" có nút *Điều chỉnh ngày NPBB* — tạo **đơn mới**
  liên kết qua `leave_records.adjusts_leave_id`, đi lại đủ 3 bước duyệt; đơn gốc chỉ chuyển
  *"Đã hủy - Đã điều chỉnh"* khi đơn mới duyệt xong. Màn chi tiết hiện cả hai chiều liên kết.
  **Không điều chỉnh chồng lên một đơn điều chỉnh** — mọi đơn điều chỉnh luôn trỏ về đúng một đơn gốc
  duy nhất, vì báo cáo Mẫu 18/19 chỉ dò một cấp cha-con (xếp chuỗi hai cấp làm nhân sự biến mất khỏi
  báo cáo). Muốn điều chỉnh lại: rút/hủy đơn điều chỉnh hiện tại, **đơn gốc tự trở lại "Hoàn thành"**
  rồi lập đơn điều chỉnh mới — không giới hạn số lần. Dialog điều chỉnh **để trống lịch chọn ngày**
  (ngày đơn gốc ghi ở dòng chữ riêng phía trên để đối chiếu), tránh tưởng nhầm đã chọn xong
- Mẫu đơn xin nghỉ phép năm **riêng theo chức danh** (nhân viên / trưởng - phó phòng / GĐ / PGĐ).
  Đơn của GĐ kính gửi **Tổng Giám đốc Agribank**, không phải Giám đốc TTTT; mẫu NPBB của diện HĐTV
  gửi **Ban Tổ chức Nhân sự**
- Mẫu đơn cá nhân NPBB (đăng ký / điều chỉnh — "Mẫu 1 TCNS") và báo cáo tổng hợp
  **Mẫu 18** (nội bộ) / **Mẫu 19** (gửi TCNS):
  `GET /api/leaves/export/npbb-batch?year=&mau=18|19[&month=][&preview=true]`.
  Bỏ trống `month` = cả năm. Bấm vào mẫu sẽ **mở xem trước** (PDF do Word chuyển tạm) rồi mới tải;
  máy chủ không chuyển được PDF thì **tự tải thẳng bản `.docx` gốc** — báo cáo này không phụ thuộc Word

- **Ứng phép năm sau khi vượt hạn mức**: vượt quỹ năm nay mà năm sau còn chỗ thì API trả **409**
  `{"code":"quota_exceeded_borrow", ...}` thay vì chặn cứng 400; frontend hỏi xác nhận rồi gọi lại với
  `confirm_borrow_next_year=true`. Phần vượt lưu ở `leave_records.borrow_next_year_days` và **trừ thật**
  vào quỹ năm sau. Vượt cả năm sau thì chặn hẳn. Cả 3 bước duyệt + duyệt lô đều cảnh báo trước khi duyệt
  đơn có ứng phép
- **KSV thay thế**: Trưởng/Phó phòng **cùng phòng** với người nộp đơn duyệt được bước KSV dù không phải
  `ksv_approver_id` (`_is_alt_ksv`) — đơn không còn kẹt khi người được chỉ định vắng mặt. Đây là *bước
  duyệt của hồ sơ*, không phải quyền truy cập; xem mục **Phân quyền** trong `docs/DESIGN.md`
- Tab **Báo cáo tổng hợp** (tên cũ: Báo cáo năm) — **Báo cáo chấm công**
  `GET /api/leaves/export/attendance-monthly?year=[&month=]`: bỏ trống `month` = cả năm, mỗi tháng một
  sheet (chỉ tới tháng hiện tại). Nhóm theo phòng; `X` = đi làm, `P` = nghỉ phép, `BB` = phép bắt buộc,
  `CT` = họp/công tác — tất cả suy từ đơn đã duyệt. Ô tô màu để trống = T7/CN/lễ, ô **không tô màu** để
  trống = ngày chưa tới. Riêng cột xếp loại thi đua không có nguồn dữ liệu, phòng Tổng hợp điền tay
- **Báo cáo nghỉ phép năm** `GET /api/leaves/export/annual?year=`: theo đúng mẫu giấy phòng Tổng hợp
  đang dùng — nhóm theo phòng (dòng tổng đứng trước danh sách nhân sự), cột *Đã nghỉ* tính đến **đúng
  ngày bấm xuất file**. Sau 31/03 phép chuyển kỳ hết hiệu lực nên cột *Tổng phép* tụt về hạn mức gốc
  trong khi *Đã nghỉ* vẫn đếm cả ngày quý I đã tiêu bằng phép chuyển kỳ — *Còn lại* kẹp về 0 (khớp tab
  Hạn mức phép), nên dòng đó có thể hiện *Đã nghỉ* lớn hơn *Tổng phép*
  > ⚠️ **Số ngày phép năm đổi mốc thâm niên 4 → 5 năm** (`compute_annual_leave()`, đúng Điều 114 BLLĐ:
  > khớp 67/72 người trên báo cáo thật 2026, mốc 4 năm cũ khớp 12/72). Người vào ngành đủ 4/8/12… năm
  > **giảm 1 ngày**; chưa có bước rà ai đã nghỉ quá hạn mức mới — xem card **NP2** trong
  > [`docs/Implementation-notes.html`](docs/Implementation-notes.html)
  > Mốc hết hạn phép chuyển kỳ **31/03** so theo **ngày bắt đầu nghỉ** của đơn, không phải ngày bấm
  > nộp đơn (`_check_quota_or_borrow(eff_start=...)`) — nộp 25/03 xin nghỉ 15/06 thì không còn được
  > cộng phép chuyển kỳ. Cùng mốc với chỗ in phiếu (`_build_form_ctx`)

### Module Chứng từ Hậu kiểm
- **Bàn giao**: GDV nhập số tờ theo ngày, HKV/KSV xác nhận từng ô
  - *Phạm vi xem*: `admin` / GĐ / PGĐ và người có quyền hậu kiểm (`handovers.confirm_entry`) xem được **mọi phòng nguồn**; các vai trò còn lại — kể cả trưởng/phó phòng — chỉ xem **phòng của chính mình**, dropdown chọn phòng cũng chỉ liệt kê phòng đó. Backend chặn ở `grid`, `history` và `export` (xuất Excel tự ép về phòng người gọi)
  - *Phạm vi ghi*: `admin`, `giam_doc`, `pho_giam_doc` **chỉ đọc — bị cấm hoàn toàn** mọi thao tác ghi (`_NO_WRITE_ROLES`, chặn ở dependency `require_handover_write` nên `admin` không bypass được như với `require_feature`). Các vai trò còn lại ghi được **trong phòng mình** nếu nhóm được cấp feature tương ứng; riêng người có `handovers.confirm_entry` ghi được trên mọi phòng
  - Vào được menu vẫn cần feature `menu.handovers` — vai trò không tự mở menu
  - *Vòng đời một ô*: `chờ xác nhận → đã xác nhận`; mượn - trả có hai đường vào trạng thái **đang mượn**:
    GDV bấm **Mượn lại** (xin → HKV duyệt), hoặc HKV/KSV bấm **Chuyển trả GDV** ở panel lịch sử để đẩy thẳng
    `đã xác nhận → đang mượn` (bắt buộc nhập lý do, feature `handovers.return_entry`, chặn cứng `chuyen_vien`).
    Cả hai đường đều kết thúc bằng GDV **Bàn giao lại** → HKV xác nhận
  - *Cột ngày nghỉ*: T7/CN **và ngày nghỉ lễ** tô vàng ở dòng tiêu đề lẫn ô trống. Ngày lễ do backend trả về (`holidays` trong `GET /api/handovers/grid`, lấy qua `tai_lich()` — hợp `public_holidays` với `duty_special_days`), không tính lại ở frontend. Ô **đã có số** vẫn giữ màu theo trạng thái, vì chứng từ phát sinh đúng ngày lễ là chuyện có thật
  - *Cán bộ chuyển phòng*: chứng từ hiển thị theo phòng tại **ngày giao dịch** — trước ngày chuyển ở phòng cũ, từ ngày chuyển ở phòng mới (lịch sử đổi phòng lưu ở bảng `staff_department_history`). Nhập bù chứng từ tháng cũ cho cán bộ đã chuyển vẫn vào đúng phòng cũ; do giới hạn phạm vi phòng ở trên, việc nhập bù này do người hậu kiểm thực hiện
- **Gom tập tự động**:
  - Max 350 tờ/tập
  - (user, ngày) không bị tách sang tập khác
  - Nếu 1 ngày > 350 tờ → chia 2 tập cân bằng
- **In bìa**: Tạo file `.docx` đúng format mẫu (2-column layout)
  - Danh sách bìa (`GET /api/bundles/groups`) **chỉ trả dòng tiêu đề** — tên phòng, kỳ, ngày tạo,
    người tạo, số bìa — **không kèm tập và mục bên trong**. Ba ô lọc mặc định "tất cả" nên lần mở
    trang đầu tiên kéo về toàn bộ kho; kèm cả tập/mục thì mỗi tập là thêm một câu SQL (283 câu,
    315 KB cho kho 1 năm; đo trên dữ liệu nhân theo năm, 5 năm là 513 ms / 5,1 MB và còn tăng
    tiếp) trong khi giao diện không đọc tới. Chi tiết tập lấy ở `GET /api/bundles/groups/{id}` —
    mọi đường in bìa / tải bìa đều đi qua đó, không đổi
- **Lưu trữ**: Ghi số hộp, vị trí kệ; tra cứu theo phòng/thời gian; bảng tổng hợp cả năm (số tờ/số tập theo phòng × 12 tháng); sửa **ngày** và **số chứng từ** ngay trên bảng — nhập vào ô trống để thêm tập, sửa về 0 để xoá tập, số tập/tổng tự cập nhật. Sửa ngày chỉ ghi lại `cover_units` của tập, **không đụng** số liệu bàn giao gốc của phòng nguồn (`document_entries`); mỗi dòng phải còn ít nhất một ngày, xoá hết ngày thì báo lỗi và giữ nguyên số đang nhập
  - *Tab "In bìa hồ sơ"*: Nạp file Excel tra cứu hồ sơ (`LT_HS_TRACUU_*.xls`) xuất từ chương trình lưu trữ → điền vào mẫu bìa **M01/LHS** (`templates/Phòng KSNB&HTVH/Bàn giao cho lưu trữ/Bia_ho_so.docx`), giữ nguyên toàn bộ định dạng của mẫu. Lấy cột **I** *Mã vạch* (ký hiệu thông tin + chuỗi barcode), cột **C** *Tên hồ sơ* (dòng tiêu đề + **Ngày mở** = ngày **đầu tiên** xuất hiện trong tên), cột **F** *Ngày CVKT*, cột **G** *Số tờ*. Chọn hồ sơ cần in trên bảng rồi tải về **1 file Word nhiều trang** (mỗi hồ sơ 1 trang) hoặc **ZIP mỗi hồ sơ 1 file**. Máy in phải cài font **"3 of 9 Barcode"**, nếu không dòng mã vạch in ra thành chữ thường và máy quét không đọc được
- **Báo cáo** (menu con):
  - *Báo cáo hậu kiểm*: Xuất Excel tổng hợp theo phòng
  - *Báo cáo bàn giao chứng từ*: Số chứng từ nộp đúng hạn / quá hạn theo phòng; chi tiết cán bộ nào nộp chậm chứng từ ngày nào, chậm bao nhiêu ngày làm việc. **Xuất Word A4 ngang** đúng kỳ đang xem (bảng tổng hợp theo phòng + chi tiết quá hạn, phần chi tiết chỉ ghi họ tên, không ghi User IPCAS)
- **Báo cáo tổng hợp**: Báo cáo riêng cho phòng Tổng hợp
- **Lịch sử thay đổi**: Ghi log mọi thao tác xác nhận, mượn, trả chứng từ

### Module Danh sách CN TTQT
- Danh mục chi nhánh thực hiện thanh toán quốc tế trực tiếp (mã CN, tên CN, SWIFT BIC, loại I/II,
  CN loại I quản lý, SĐT, địa chỉ, ghi chú)
- Menu: **Danh sách CN TTQT** (menu phẳng, cấp 1)
- Tra cứu theo mã CN / tên CN / SWIFT BIC; lọc theo loại CN và trạng thái
  (**Đang hoạt động** / **Đã đóng BIC** / Tất cả) — CN đã đóng BIC tô xám khi xem chung
- Thêm / sửa / xoá từng CN ngay trên giao diện, mọi thao tác ghi audit log
- **Nhập từ Excel**: đọc đúng file gốc do phòng KSNB phát hành — dòng đánh dấu `Đóng BICCODE` phân
  tách nhóm CN còn hoạt động với nhóm đã đóng BIC. Mặc định chỉ **thêm mới + cập nhật**; tích ô
  *"Xoá CN không có trong file"* nếu muốn đồng bộ hoàn toàn theo file
- **Xuất Excel** theo đúng bộ lọc đang xem; file xuất ra nhập lại được (cùng định dạng file gốc)
- **Lịch sử sửa đổi** (nút 🕘 ở cuối mỗi dòng): ngày giờ — người sửa — sửa mục nào — giá trị cũ →
  giá trị mới. Ghi cho cả sửa tay lẫn nhập Excel, **mỗi trường một dòng**; nhập lại đúng file cũ
  không sinh dòng nào vì không có gì đổi. Lịch sử giữ lại cả khi chi nhánh bị xoá, và theo được
  sang bản ghi mới nếu chi nhánh đó được nhập lại cùng mã CN
- Phân quyền riêng theo nhóm (`menu.ttqt_branches` +
  `ttqt_branches.create/edit/delete/import/export/history`)

  > Mã `ttqt_branches.history` là mã mới — **chưa nhóm nào được tick sẵn**. Vào
  > **Phân quyền theo nhóm → Danh sách CN TTQT** bật lên thì nút Lịch sử mới hiện.

### Module Lịch trực
- Xếp lịch trực tự động cho phòng Thanh toán
- **Số người mỗi ca do phòng tự khai** ở tab Cài đặt (ca thường và ca quyết toán khai riêng);
  một ca có thể có **nhiều hơn một Lãnh đạo**. Thiếu người so với số đã khai thì
  **không hình thành ca trực**, có cảnh báo nêu rõ lý do
- **Ca quyết toán** chia nhóm trực chính / trực phụ (nhóm phụ về sớm hơn), lưu thành **một** bản ghi
- Cần **ít nhất 1 người xử lý song phương** trong Lãnh đạo + nhóm trực chính — thiếu hoặc dư
  đều vẫn lập ca, chỉ cảnh báo. Người ở nhóm trực phụ không tính (về sớm)
- Ngày thường bốc **ngẫu nhiên trong nhóm ít ca nhất**; thứ 6 luân phiên **tất định**.
  Có tiêu chí phụ tránh hình thành ê-kíp trực cố định
- **Ba luật công bằng (mềm)**, áp dụng như nhau cho Lãnh đạo lẫn nhân viên: không quá
  **2 ca/tuần**, không quá **2 thứ 6/tháng**, không trực thứ 6 ở **2 tuần liên tiếp**.
  Thuật toán ưu tiên tránh; pool cạn thì **vẫn lập ca** kèm cảnh báo nêu đích danh người bị
  phá luật — đủ người quan trọng hơn giữ đúng luật mềm. Đường **sửa tay** cũng cảnh báo,
  nhưng hiện chỉ soi các ca **trước** ngày đang sửa (xem card 91 trong Implementation-notes)
- **Sửa tay** thành phần ca: vai song phương hệ thống tự suy từ cờ "biết song phương",
  số ca trong vòng xoay đi theo người được đổi. Sửa xong ca quay về bản thảo, phải xác nhận lại
- **Xoá hoặc tạo lại lịch trả số ca về vòng xoay** — mọi đường ghi/xoá ca đều tra cùng
  `KENH_VONG_XOAY` trong `duty_scheduler_engine.py`, không đường nào tự hiểu khác
- **Thứ 7 / chủ nhật đi làm**: khai loại **"Ngày bù"** ở tab Ngày đặc biệt rồi xác nhận thì
  hôm đó sinh ca thường, vào lịch tuần/tháng, lên file Excel, đăng ký nguyện vọng được,
  và được tính khi dò 2 ngày cut-off cuối tháng
- **Ngày lễ lấy từ hai nguồn**: danh mục ngày lễ chung `public_holidays` (nhập ở màn hình *Nghỉ phép*
  — giao diện nhập ngày lễ duy nhất của phần mềm) hợp với khai báo riêng ở tab *Ngày đặc biệt*.
  **Khai báo riêng thắng**: ngày đã có dòng trong `duty_special_days` thì lấy nguyên `day_type` của
  nó, nhờ vậy ngày làm bù rơi trúng ngày lễ (nhà nước hoán đổi) vẫn đúng là ngày làm
- **Đơn nghỉ phép đã duyệt tự loại người khỏi lịch** — không phải khai vắng mặt lần thứ hai.
  Đọc thẳng `leave_records` lúc xếp lịch chứ không sao chép sang `duty_absences`: đơn còn bị huỷ,
  thu hồi, sửa ngày. Chỉ đơn `approved` mới tính; đơn đang chờ duyệt vẫn xếp trực bình thường
- Quản lý cán bộ trực, ràng buộc lịch trực (ngày không trực, giới hạn ca)
- Thống kê số ca trực theo cán bộ, theo tháng — **trực chính và trực phụ đếm 2 cột riêng**, không quy đổi
- **Xuất lịch trực ra Excel** bám mẫu giấy của phòng: 5 cột A–E, trắng đen, cỡ chữ 24/18/16,
  mỗi ngày đúng một hàng; ngày quyết toán để trực chính IN HOA đậm và trực phụ nghiêng nhỏ
  trong cùng ô. **Chức danh người ký khai được** ở tab Cài đặt (`signer_title`), mặc định "GIÁM ĐỐC"
- **Phân quyền enforce ở backend**, không chỉ ẩn nút: cả 35 endpoint đều gắn `require_feature`
  (`menu.duty_schedule` để đọc · `duty.generate` tạo & sửa lịch · `duty.confirm` · `duty.delete`
  · `duty.export` · `duty.manage_staff` cờ nhân sự & vắng mặt · `duty.manage_config` cài đặt &
  ngày đặc biệt & reset vòng xoay)

### Module Đối chiếu điện SWIFT (phòng Swift)
- Đối chiếu điện SAA ↔ Màn hình quản lý điện, 2 chiều: **Điện đến** / **Điện đi**
- Mỗi bên nhận **nhiều file** (SAA có thể xuất nhiều đợt trong ngày) — tự gộp
  trước khi đối chiếu; giới hạn 10 file hoặc 100 MB mỗi ô
- Xuất Excel 5 loại mỗi chiều: Tổng hợp, Chi tiết lệch, Bản ghi đang lọc,
  **Tổng hợp theo biểu mẫu** và **Chi tiết lệch theo biểu mẫu** (Mẫu 04/05,
  khung nền lấy từ `backend/services/swift_recon/templates/`)
- Cột "Chênh lệch" đếm số bản ghi **không khớp khoá**, không phải hiệu số lượng
- Tab **Lịch sử đối chiếu** — lưu vào bảng `swift_recon_history` trong DB chung
- Phân quyền riêng theo nhóm (`menu.swift_recon`)

### Module Chấm 459901
- Phân loại bút toán tài khoản trung gian 459901 dành cho phòng Thanh toán
- Menu: **Đối chiếu → Phòng Thanh toán → Chấm 459901**
- Upload **một hoặc nhiều** file chứa dữ liệu giao dịch; xử lý bất đồng bộ (~65s)
- Nhận **ZIP** (bản xuất gốc GL02, mã hoá AES-256; bên trong là `.csv` hoặc Excel) và **Excel
  rời** (`.xlsx/.xlsm/.xlsb/.xls`) — trộn hai loại trong một lượt cũng được. Đuôi khác bị chặn
  ngay ở bước tải lên (400). Với Excel: đọc **mọi sheet**, tự dò hàng tiêu đề trong 10 dòng đầu
  (bản người dùng lưu lại hay có dòng tiêu đề báo cáo ở trên cùng), sheet nào thiếu cột bắt buộc
  thì báo lỗi kèm tên sheet chứ không lặng lẽ bỏ qua
- Nhiều file được **gộp** rồi mới phân loại — cặp Cancel/Normal của một lệnh hủy có thể nằm ở
  hai file khác ngày, chạy tách từng file thì cả hai vế rơi nhầm vào *Khác*. Chọn trùng tên
  file trong cùng một lượt bị chặn (400) vì dữ liệu nhân đôi không sinh lỗi nào
- Phân loại thác nước thành **7 nhóm**, xuất 7 file Excel: **Lệnh Hủy**, **Lệnh Đi**,
  **1000 Hoàn trả**, **Chuyển chi nhánh**, **Điện KO offline**, **Cân CN**, **GD khác**.
  Dòng chỉ khớp được một chân (chưa đủ cặp Nợ/Có) không bị đoán bừa — rơi về *GD khác*
  kèm ghi chú "nghi ngờ, cần chấm tay"
- Nhóm nào quá **1.048.573 dòng** thì **tự tách sang sheet thứ hai trong cùng file** (`Lệnh Đi
  (1/2)`, `Lệnh Đi (2/2)`…) — vẫn đúng 7 file như cũ, chỉ nhiều sheet hơn. Một file GL02 một
  ngày đã cho ~617.000 dòng *Lệnh Đi*, nên gộp 2 ngày là vượt trần 1.048.576 dòng của định dạng
  Excel; trước đây phần mềm cứ ghi tiếp qua trần, báo "Hoàn thành!" rồi Excel **từ chối mở file**
  mà không có lỗi nào ở cả hai đầu. Dòng **TỔNG CỘNG** cuối mỗi sheet là tổng **của sheet đó**
  (nhãn ghi rõ `TỔNG CỘNG PHẦN 2/2`), tổng cả nhóm nằm ở dòng tiêu đề trên cùng. Lượt chạy chỉ
  có một sheet — tức gần như mọi lượt — hiển thị y hệt trước, không đổi gì
- Nhận thêm **3 file phụ trợ tuỳ chọn**, tự nhận diện theo tên: HUB đi (`Quay_...`),
  HUB đến (`Danh sach...den`) để chấm nhóm *1000 Hoàn trả*, và file tồn tháng trước
  (`459_TON_T<n>.xlsx`) ghép nối tiếp vào dữ liệu tháng này. Thiếu **cả 2** file HUB thì
  bỏ qua nhóm 1000 Hoàn trả; chỉ có 1/2 thì bỏ cả hai và báo rõ trên màn hình
- Hai cách nạp dữ liệu hiển thị đồng thời: **tải file lên**, hoặc **chọn thư mục trên máy
  chủ** (dữ liệu đã nằm sẵn ở đó, khỏi upload). Chế độ thứ hai chỉ quét trong các thư mục
  khai ở `CHAM459901_FOLDER_ROOTS`; đường dẫn ngoài phạm vi bị từ chối **trước khi** kiểm
  tra tồn tại, để endpoint không thành máy dò cây thư mục của máy chủ
- Chế độ chọn thư mục **gõ/dán đường dẫn**, không có nút *Duyệt...*. Hộp thoại duyệt cây thư
  mục đã bị gỡ cùng endpoint `/api/fs/browse` vì nó cho **mọi người đăng nhập liệt kê sạch ổ
  đĩa máy chủ**
- File tải lên được ghi **thẳng từng khối** xuống `data/temp_cham459901/upload_<token>/`
  (`save_upload_to`), `process_files()` nhận **đường dẫn** chứ không nhận bytes. CSV bên trong
  ZIP đọc qua `zf.open()` — luồng giải nén, không có lúc nào cả file nằm trong RAM (đo: CSV
  114 MB → đỉnh 0,1 MB thay vì 256 MB). Workbook Excel trong ZIP vẫn phải qua RAM: calamine
  đọc nhảy vị trí nên không nhận luồng tuần tự
- Phân quyền riêng theo nhóm (`menu.cham_459901`, `cham_459901.process`)

### Module Đối chiếu Song phương
- Định tuyến lệnh IPCAS phục vụ đối chiếu song phương tại phòng Thanh toán
- Menu: **Đối chiếu → Phòng Thanh toán → Đối chiếu Song phương** — 2 thẻ đang dùng: **Phân loại
  dữ liệu** và **Đối chiếu đến** (thẻ **Đối chiếu đi** còn đang xây, chưa có backend)
- **Thẻ Phân loại dữ liệu**: upload file ZIP chứa dữ liệu IPCAS (GL02); xử lý bất đồng bộ, theo
  dõi tiến độ real-time. File tải lên được ghi **thẳng từng khối** xuống
  `data/temp_doi_chieu_song_phuong/upload_<token>/`; `process_zip()` nhận **đường dẫn**, kiểm
  magic bytes bằng 4 byte đầu đọc từ file, và duyệt CSV bên trong ZIP theo luồng (`zf.open()`) —
  `_route_file()` đi tuần tự từng dòng nên không bao giờ cần nhìn lại dòng đã qua
- Phân loại mỗi dòng theo **4 ngân hàng** (Vietinbank 201, BIDV 202, Vietcombank 203, MBBank 311) × **2 chiều**: **ĐẾN** (`CRAMOUNT=0`) / **ĐI** (`DRAMOUNT=0`) → xuất **8 file CSV**
- ⚠️ ZIP dùng mật khẩu chung (`DOI_CHIEU_ZIP_PASSWORD`) nhưng entry GL02 thật là **PKWARE
  ZipCrypto cổ điển**, không phải AES-256 (tên lớp `pyzipper.AESZipFile` gây hiểu nhầm — mỗi entry
  tự chọn thuật toán riêng). ZipCrypto chỉ giải mã được bằng vòng lặp Python thuần, chậm với file
  hàng triệu dòng; đường tắt `numba.njit` (tùy chọn, tự lui về `pyzipper` gốc nếu máy thiếu numba)
  giải mã nhanh hơn **~35 lần** cho đúng trường hợp này — chi tiết & cách phân biệt an toàn với
  AES thật (`wz_aes_version is None`) xem `docs/Implementation-notes.html` card 112
- **Thẻ Đối chiếu đến** (`/api/doi_chieu_song_phuong_kenh_core`): chạy **Kênh↔Hub rồi Hub↔Core**
  tự động nối tiếp trong 1 job cho 1 ngân hàng + 1 ngày mỗi lượt — không phải 2 tính năng rời
  nhau, lỗi 1 bước không chặn bước còn lại, chỉ khi cả 2 đều lỗi mới đánh dấu job lỗi. Từ
  02/09/2026 chỉ nhận **tải file lên** (HUB zip, kênh xlsx, GL02 zip / CORE csv-xlsx, OSB xlsx cùng lúc) —
  đã bỏ hẳn chế độ "chọn thư mục server" cùng nút "Duyệt..." — 2 endpoint cũ nhận `folder_path`
  tuỳ ý không qua allowlist nào, tiền lệ giống lỗ hổng `/api/fs/browse` đã gỡ ở ACH trước đó (xem
  `docs/Implementation-notes.html` card 113). Backend ghi **thẳng từng khối** xuống đĩa job
  (`save_upload_to`), không gom vào RAM trước — cùng khuôn mẫu upload của module ACH
- **File CORE đã phân loại sẵn: nhận cả `.csv` lẫn `.xlsx`, và ngày lấy từ NỘI DUNG file**
  (từ 09/09/2026, PR #81). Bước Hub↔Core nhìn tới CORE của T+1..T+3, nhưng tên `{mã NH}_DEN*.csv`
  không mang ngày. Luật cũ 03/09 vá bằng cách chỉ nhận CSV cho ngày T — chặn luôn cả trường hợp
  hợp lệ là người dùng đã có sẵn file của T+1. Nay hệ thống **mở file đọc cột `TRDATE`** để gán
  đúng offset, nộp nhiều file khác ngày một lượt và trộn `.csv` với `.xlsx` đều được
  (`docs/Implementation-notes.html` card 129)
  - `TRDATE` **không** nằm trong `CORE_REQUIRED_COLS` — file không có cột này vẫn được nhận cho
    **ngày T** (tương thích ngược), nhưng không dùng được cho offset khác
  - File mà `TRDATE` bên trong **lẫn nhiều ngày** (phân loại gộp nhiều đợt zip một lượt) bị **từ
    chối cả file** — đổi so với trước, khi nó được nhận cho ngày T kèm luôn dòng của ngày khác.
    Cách xử lý: phân loại lại từng ngày rồi nộp riêng. Module ILO1000 gặp cùng dạng file này thì
    **lọc theo `TRDATE`** (`ilo1000/pipeline.py::_filter_core_by_date`); chiều ĐẾN chưa làm vậy
  - Cùng một ngày mà có 2 file (kể cả 1 `.csv` + 1 `.xlsx` cùng nội dung) thì **không tự chọn**,
    báo lỗi yêu cầu bỏ bớt — cùng nguyên tắc "không đoán khi mơ hồ" của `_tim_file_hub()`
  - ⚠️ Bảng **"đủ/thiếu" hiện trước khi bấm Chạy** (`common.kiem_tra_du_lieu()`) vẫn chỉ dò theo
    **TÊN** file, không mở file ra xem — nên có thể báo "đủ" rồi lúc chạy mới dừng vì ngày bên
    trong không khớp. Docstring hàm đó nói "tái dùng đúng luật dò tên của pipeline" đã **không
    còn đúng** kể từ PR #81
  - ⚠️ Tham số `ngay_goc` (dò thêm thư mục ngày T) chỉ có tác dụng khi thư mục nguồn có thư mục
    con dạng `D.M`. `/start_upload` ghi phẳng qua `safe_filename()` nên **hiện là no-op** — nó
    chuẩn bị cho chế độ thư mục máy chủ đã bị gỡ ở PR #70
- **3 file CSV chi tiết bọc `="..."` quanh cột khoá toàn chữ số** (từ 09/09/2026) —
  `MSGREF`/`TXID` ở hai file `..._hub_chi_tiet.csv`, `MtId/MsgId` ở `..._kenh_chi_tiet.csv`.
  Khoá SP THƯỜNG là chuỗi **16 chữ số thuần**, vượt trần **15 chữ số có nghĩa** của Excel: mở CSV
  bằng double-click thì Excel tự coi cột đó là kiểu Số — rụng số 0 đứng đầu và làm tròn chữ số
  cuối về 0. SP REALTIME không dính vì khoá có chữ cái nên Excel tự nhận là văn bản. Mở bằng
  double-click nay ra đúng nguyên văn, nhưng **Power Query hoặc công cụ khác đọc CSV thô sẽ thấy
  `="..."` bao quanh giá trị** — không phải lỗi. Cột `TRACE`/`CHI_NHANH` cùng dạng dữ liệu
  **chưa** bọc (`docs/Implementation-notes.html` card 128)
- Phân quyền riêng theo nhóm: `menu.doi_chieu_song_phuong` (xem trang/kiểm tra dữ liệu),
  `doi_chieu_song_phuong.process` (chạy Phân loại dữ liệu),
  `doi_chieu_song_phuong_kenh_core.process` (chạy Đối chiếu đến)

### Module Đối chiếu ACH
- Đối chiếu GL02 (IPCAS/NPO) với MIS PaymentHub theo phiên ACH, cả hai chiều ĐI và ĐẾN
- Menu: **Đối chiếu → Phòng Thanh toán → Chấm đối chiếu ACH**
- Chọn bộ file 1 ngày **từ máy người dùng**: `GL02*.zip`, file GW `.xlsx`, 2 file `*_DI_*.zip`,
  2 file `*_DEN_*.zip`, PDF sao kê ACH (lấy số session + suy ngày đối chiếu). Mở thư mục chứa
  bộ file rồi Ctrl+A để chọn cả loạt. Mỗi file gửi lên frontend ngay khi chọn (`auto_upload`) và
  **nằm trong RAM** của tiến trình frontend cho tới lúc bấm Chạy; backend thì ghi **thẳng từng
  khối** xuống `data/temp_ach/<job>/input/` (`save_upload_to`), không gom vào RAM trước — đo với
  file 200 MB: đỉnh bộ nhớ 400 MB (cách cũ `read_limited` rồi mới ghi) → **2 MB**. Tên file được
  `safe_filename()` cắt sạch phần đường dẫn trước khi ghi — tên client gửi lên là chuỗi tuỳ ý,
  ghép thẳng vào `Path` thì đoạn tuyệt đối nuốt trọn thư mục đích. Trần 500 MB (`_MAX_UPLOAD`), bộ
  file thật 150–250 MB → cần dư RAM tương ứng ở **cả hai** tiến trình. Timeout lần gửi này để
  riêng 600s (`post_upload(..., timeout=600.0)`), các màn hình khác giữ mặc định 60s
- Ngày đối chiếu suy từ tên file PDF (`ACH_YYYYMMDD_..._NRT_<session>_...` → ngày T-1), nhập tay được;
  không suy được thì **báo lỗi**, không lặng lẽ dùng ngày khác
- Khớp theo số lượng cặp khoá: chiều ĐI `TRBRCD+SO_TRACE+CRAMOUNT` ↔ `CHI_NHANH+SO_TRACE+SO_TIEN`,
  chiều ĐẾN `SO_TRACE+DRAMOUNT` ↔ `TRACE+SO_TIEN`. Lệnh TPAY vượt số slot GW được tách ra sheet
  **TIMEOUT_KHONG_KENH** (đánh dấu `CO_TRONG_GW` nếu MSGREF vẫn có trong GW → cần kiểm tra tay)
- Kết quả: 1 file Excel 11 sheet (TONG_KET, PHAN_TICH có cảnh báo tự động, các sheet khớp/thừa,
  CAP_CN_TIEN, RAW_GW); sheet trên **15.000 dòng** tự tách ra CSV riêng, tải lẻ hoặc tải gộp ZIP
- Chạy nền trên **1 luồng riêng** (`max_workers=1`) — job thứ hai xếp hàng; theo dõi tiến độ + nhật ký
  bằng poll, có nút Dừng (dừng ở mốc kiểm tra giữa các pha, không tức thì)
- Kết quả nằm trong `data/temp_ach/` **hết ngày làm việc**, 23h xoá sạch; không lưu lịch sử vào DB.
  Cần giữ lâu hơn thì tải về máy trong ngày
- Phân quyền riêng theo nhóm: `menu.cham_ach` = xem trang / kiểm tra file / tải kết quả,
  `cham_ach.process` = được bấm Chạy, Chạy tiếp sau Checkpoint và Dừng

### Module Đối chiếu CITAD ↔ PaymentHub
- Đối chiếu số liệu tổng CITAD (NHNN) với PaymentHub (Agribank) theo từng ngày
- Menu: **Đối chiếu → Phòng Thanh toán → Đối chiếu CITAD**
- Nhập tay 5 cổng CITAD × 3 loại tiền × 8 trường; chênh lệch tính lại ngay khi gõ
- Ngoài 5 cổng còn 2 kênh cộng vào tổng CITAD: **Napas** và **PSS - MDP** (chỉ 2 ô *IH Đến —
  Món/Tiền*). Kênh **Ebanking** đã ngừng: bỏ khỏi màn hình 14/08/2026, bỏ nốt khỏi file Excel
  20/08/2026 — số liệu các ngày đã chấm vẫn nằm nguyên trong DB, chỉ không hiện/in ra nữa
- Mỗi bảng khoá theo `id` riêng (`doi_chieu_citad_sessions`, từ 07/09/2026) — **1 người có thể
  có nhiều bảng độc lập trong cùng 1 ngày**: bấm "Tải" một bảng đã lưu để sửa/lưu tiếp tại chỗ,
  còn gõ ngày rồi Lưu mà KHÔNG bấm "Tải" thì luôn sinh **1 bảng mới hoàn toàn tách biệt** (kể cả
  sau khi 1 bảng cũ đã "Lưu bảng cuối" rồi chấm lại). "Lưu bảng tạm" cho phép người khác vào góp
  riêng Napas/PSS-MDP; mỗi lần Lưu ghi thêm 1 dòng vào `doi_chieu_citad_history` để xem/tải lại
  từng bản cũ. Đổi ô ngày sau khi đã "Tải" 1 bảng sẽ tự tách khỏi bảng đó (không ghi đè nhầm)
- Vào bảng **tạm** của người khác (qua tab *Lịch sử*) vẫn chỉ bổ sung được Napas/PSS-MDP như cũ,
  không sửa được ô nào khác và không chốt bản cuối hộ được
- **Sổ trực cuối ngày** coi một ngày là *đã đối chiếu, đã khớp* nếu **bất kỳ** bảng nào của ngày
  đó đã "Lưu bảng cuối" và khớp. ⚠️ Nghĩa là nếu người A chốt bảng khớp còn người B chốt bảng
  lệch cho cùng ngày, Sổ trực **không** cảnh báo — cảnh báo này chỉ là nhắc phụ trợ, không chặn
- Hai ô **Napas** / **PSS - MDP** **không gõ tay được nữa** (từ 05/09/2026), chỉ nạp qua nút
  *"Nạp CITAD"*. Extension quét ở trang PaymentHub vẫn gửi hai mục này lên nhưng phần mềm chủ
  động bỏ qua và báo *"Lệnh quyết toán lô bắt buộc phải quét dữ liệu từ cổng Citad"* —
  **không phải lỗi**, và **không cần cài lại Extension** (Extension không đổi gì)
- **Ba bảng chênh lệch** thay vì một (từ 05/09/2026): bảng *Gộp* cả 3 loại tiền như cũ, thêm
  bảng **VNĐ** riêng và bảng **Ngoại tệ** (USD + EUR gộp chung) — nhìn ra ngay lệch nằm ở nhóm
  tiền nào, không phải đọc dòng ghi chú cuối trang. Công thức và file Excel xuất ra không đổi
- Xuất Excel theo mẫu *"Báo cáo đối chiếu giao dịch hệ thống thanh toán điện tử liên ngân hàng"*
  đã duyệt (`build_xlsx` — không đổi format/công thức khi sửa)
- Kèm **Extension trình duyệt** (`extension_citad/`) tự lấy số liệu từ trang CITAD/PaymentHub:
  tải `.zip` ngay trên màn hình, ghép nối bằng *mã kết nối* cá nhân
  (`doi_chieu_citad_extension_tokens`, chỉ lưu hash SHA-256, tạo mã mới tự thu hồi mã cũ).
  Chỉ chạy trên Chromium (Chrome/Edge/Cốc Cốc), phải cài tay từng máy
- Hai ô **Lập bảng** / **Kiểm soát** vừa gõ tay tự do, vừa bấm chọn từ danh sách nhân viên
  **Phòng Thanh toán** (tra theo `code='PAYMENT'`, không phụ thuộc id phòng).
  Tên không nằm trong danh sách (người đã nghỉ / chuyển phòng / gõ tay kiểu khác) vẫn được giữ
  nguyên khi mở lại bảng cũ — hai lỗi mất tên và **Xuất Excel 422** của 23/08/2026 đã vá
  25/08/2026, xem `docs/Implementation-notes.html` mục Z8
- Tab **Lịch sử** (từ 07/09/2026, chia 3 tầng): **người lập bảng** (nhóm theo ngày + người) →
  **từng bảng độc lập** của người đó → **từng lần lưu** trong bảng đó (mỗi người bấm *Lưu* là
  một dòng riêng mang đúng tên, không gộp nhiều người vào một dòng mang tên người lập bảng). Có
  dòng ngăn cách khi sang tháng khác. ⚠️ Ô lọc **Tên người chấm** vẫn chỉ tìm theo **người lập
  bảng** — tìm tên người chỉ bổ sung Napas/PSS-MDP sẽ không ra ngày nào, phải bung bảng ra mới thấy
- Phân quyền riêng theo nhóm (`menu.doi_chieu_citad`)

### Module Đối chiếu CITAD - PaymentHub (Phòng QLTK Nostro, Vostro)
- Module **song song, độc lập hoàn toàn** với "Đối chiếu CITAD ↔ PaymentHub" của Phòng Thanh toán ở
  trên — bảng riêng, buffer riêng, route riêng, Extension riêng, **mã kết nối riêng**
  (`doi_chieu_citad_nostro_extension_tokens`). Không dùng chung gì cả
- ⚠️ **Mã kết nối phải tạo riêng cho từng Extension** (27/08/2026, PR#64). Trước đó 2 module dùng
  chung bảng `doi_chieu_citad_extension_tokens` khoá theo `staff_id`, nên ai tạo mã ở module này
  là **âm thầm thu hồi mã module kia của chính mình** → 1 trong 2 Extension bị 403. Nay tách hẳn 2
  bảng, tạo/thu hồi ở phòng nào chỉ ảnh hưởng đúng phòng đó
- Menu: **Đối chiếu → Phòng QLTK Nostro, Vostro → Đối chiếu CITAD - PaymentHub**
- Nguồn số liệu khác hẳn: CITAD lấy ở trang **"Tra cứu dữ liệu"** (không phải "Bảng kê giao dịch"),
  chỉ chiều **Đi**, chỉ **giao dịch thành công**, chỉ VNĐ, đủ 5 cổng; PaymentHub lấy dòng
  **Tổng cộng** ở trang "Lập bảng kê phí chia sẻ CITAD"
- Công thức: Tổng CITAD (GTT/GTC) = cộng 5 cổng; Tổng HUB (GTC) = Trước 15h30 + Từ 15h30;
  Chênh lệch = Tổng CITAD − Tổng HUB
- **Kỳ đối chiếu linh hoạt** (Từ ngày – Đến ngày, gộp được nhiều ngày) thay vì 1 dòng/ngày cố định.
  Trước khi lưu có **cảnh báo (không chặn)** nếu kỳ mới chồng ngày với kỳ đã lưu, hoặc bỏ hở ngày so
  với kỳ liền trước
- Mỗi kỳ là **một bản ghi chung cả phòng** (`doi_chieu_citad_nostro_sessions`, khoá theo `ky`) — ai
  lưu sau cùng là bản hiện hành, nhưng cột **người chấm** ở tab Lịch sử luôn hiển thị **người lập
  bảng** (người lưu đầu tiên), không đổi theo người lưu sau. Mỗi lần bấm Lưu ghi thêm 1 dòng vào
  `doi_chieu_citad_nostro_history` để xem/tải lại từng bản cũ
- Kèm **Extension trình duyệt riêng** (`extension_citad_nv/`) — **không** dùng chung
  `extension_citad/` của Phòng Thanh toán, 2 gói có 2 ID khác nhau, cài song song được. Một mã kết
  nối dùng được cho cả 2 gói nếu một người làm cả 2 module
- Phân quyền riêng theo nhóm (`menu.doi_chieu_citad_nostro`) — user Nostro **không** có
  `menu.doi_chieu_citad` nên không vào được màn hình của Phòng Thanh toán và ngược lại

### Module Đối soát CITAD ↔ IPCAS
- Đối soát từng lệnh chuyển tiền giữa CITAD (NHNN) và IPCAS (Agribank) theo ngày chấm
- Menu: **Đối chiếu → Phòng Thanh toán → Đối soát CITAD ↔ IPCAS**
- Upload file CITAD (`.xls`/`.xlsx`/`.zip`), IPCAS (`.csv`/`.zip`) và Hub ngoại tệ (`.xls`/`.xlsx`);
  khớp trong RAM theo `msgref` (Đi) / `txid` (Đến), phân loại lệch thành 4 nhóm:
  **Chỉ CITAD / Chỉ IPCAS / Chỉ Hub / Lệch trạng thái**
- **Phát hiện IPCAS/Hub hạch toán trùng**: cùng 1 lệnh ghi nhiều lần sẽ hiện thành từng dòng
  **Chỉ Agribank** riêng (đúng số lần dư), kèm ghi chú "N lần" trên dòng đã khớp — không gộp lại
  thành 1 dòng như trước
- **Cặp "hạch toán nhầm rồi huỷ"** (GDV hạch toán tay sai chi nhánh rồi huỷ, hạch toán lại) được
  nhận ra qua `REFHUB` và **loại khỏi đối soát** — không tính khớp, không tính lệch
- ⚠️ **Lệnh Đến trạng thái PYED/PYEK nay VẪN hiện nếu không khớp CITAD.** Trước 24/08/2026 hai
  trạng thái này được bỏ qua khi tính dư. Hệ quả: **báo cáo có thể nhiều dòng lệch hơn trước** một
  cách hợp lệ — số liệu trước/sau mốc này không so sánh trực tiếp được
- ⚠️ **Lệnh Đi trạng thái `SCNL` nhưng cột `NGAY_KENH_TRA` để trống nay KHÔNG còn được coi là
  khớp** (từ 28/08/2026, yêu cầu Phòng Thanh toán). `SCNL` nghĩa là "đã sang kênh thành công",
  nhưng kênh chưa ghi ngày trả thì chưa phải xác nhận thật — lệnh CITAD tương ứng rơi vào nhóm
  **Chỉ CITAD** để người dùng tự xác minh. Hệ quả: **số dòng lệch có thể tăng**, số liệu
  trước/sau mốc này không so sánh trực tiếp được
- 🔴 **Điểm mù đã biết của quy tắc trên** (từ 09/09/2026 vá được một nửa): dòng IPCAS nói trên nay
  **vẫn được giữ lại** khi đọc file, nên nếu CITAD **có** lệnh tương ứng thì dòng "Chỉ CITAD" nay
  kèm luôn **Số RefHub** để tra cứu bên Agribank, và `total_ipcas` trong tab Lịch sử **hết đếm
  thiếu**. Nửa còn lại chưa vá: nếu CITAD **không hề có** lệnh đó thì dòng vẫn biến mất khỏi báo
  cáo, không hiện ở nhóm **Chỉ Agribank** — đây đúng là ca đáng ngờ nhất (IPCAS ghi đã đi kênh mà
  CITAD chưa từng thấy), đang chờ Phòng Thanh toán chốt vì cho hiện sẽ làm số dòng lệch tăng thêm.
  Xem `docs/Implementation-notes.html` (card 109, 127)
- ⚠️ **`total_ipcas` từ 09/09/2026 không so sánh trực tiếp được với các lượt chấm cũ** — cùng một
  file IPCAS nay cho con số lớn hơn trước, vì hết đếm thiếu nhóm dòng nói trên (không phải do dữ
  liệu thay đổi)
- **Cột "Dịch vụ" đã bỏ, thay bằng cột "Số RefHub"** (09/09/2026, yêu cầu Phòng Thanh toán) — trên
  cả Excel xuất ra lẫn bảng "Kết quả" trên màn hình. Nội dung cột "Dịch vụ" cũ suy thẳng được từ
  cột **Loại GD** (IH = giá trị cao, IL = giá trị thấp) ngay bên cạnh. "Số RefHub" đặt **cuối nhóm
  AGRIBANK (IPCAS)** vì đó là dữ liệu gốc của file IPCAS, phía CITAD không có
- 🔴 **Dòng nhóm "Lệch trạng thái" hiện vẫn để trống cột Số RefHub** dù IPCAS có sẵn giá trị đó —
  đúng nhóm cần tra cứu nhất. Đang chờ vá; xem `docs/Implementation-notes.html` (card 127)
- Cảnh báo khi chọn **trùng nội dung file** (băm SHA-256 toàn bộ byte, không dựa vào tên file).
  ⚠️ Chỉ là cảnh báo, bấm qua được — nhưng chọn nhầm trùng file nay khiến **mỗi dòng đẻ 1 dòng
  lệch giả**, không còn bị lọc âm thầm như trước
- Xuất Excel 4 sheet; tab **Lịch sử** lưu `doi_soat_citad_history` kèm snapshot nguyên vẹn danh sách
  lệch — xem lại/tải lại đúng số liệu của lần đối soát cũ, không tính lại từ file gốc
- Nút **"Xuất tất cả lệnh"** xuất đủ cả khớp lẫn lệch trong 1 sheet (lệch đẩy lên đầu, bôi vàng);
  ~38.000 dòng mất ~6 giây nhờ đặt style ở cấp cột thay vì từng ô, riêng 2 cột số (STT, Số tiền)
  phải gán căn lề từng ô vì Excel **không** áp style cột cho ô đã ghi giá trị — xem
  `docs/Implementation-notes.html` (card 105). Danh sách khớp **không** lưu vào lịch sử, chỉ giữ
  trong phiên
- 🔴 **KHÔNG mở file CSV IPCAS bằng Excel rồi lưu lại** — kể cả chỉ mở ra xem rồi bấm Ctrl+S.
  Excel tự đổi mọi số tiền đủ lớn (từ ~100 tỷ, đúng nhóm giá trị **cao**/IH) sang ký hiệu khoa
  học (`5.53722E+11`) và **chỉ giữ ~6 chữ số có nghĩa** — 6 chữ số cuối bị làm tròn thành 0
  **vĩnh viễn trong file**, không cách nào lấy lại. Từ 25/08/2026 chương trình đọc đúng độ lớn
  của dạng khoa học (trước đó cho ra `55372211`, sai hẳn), nhưng **phần chính xác đã mất thì
  không cứu được** — gặp file nghi bị Excel lưu đè thì tải lại bản gốc từ IPCAS
- ⚠️ Chương trình **chưa cảnh báo** khi gặp file đã bị Excel làm hỏng kiểu trên — vẫn chấm bình
  thường và ra vài chục dòng lệch không giải thích được. Đang chờ vá; xem
  `docs/Implementation-notes.html` (card 107)
- Phân quyền riêng theo nhóm (`menu.doi_soat_citad`)

### Module Sổ trực cuối ngày (Phòng Thanh toán)
- Ghi nhận ca trực cuối ngày: **2 GDV chính** (+ trực phụ chỉ liệt kê, không tham gia duyệt)
  nhập ghi chú, chọn **1 KSV** xác nhận. Menu cấp 1: **Sổ trực cuối ngày**
- Luồng: `draft` → `pending_ksv` → `approved`. Một GDV đủ để chuyển KSV; GDV còn lại bấm
  *Xác nhận phiên trực* chỉ để ghi nhận đã xem (`gdv_ack`, không chặn luồng)
- KSV có hai lựa chọn từ chối, **cả hai đều chỉ là đề nghị và đều quay về `draft`** —
  phân biệt bằng `ksv_decision`: `reject_fix` (yêu cầu sửa) và `reject_cancel` (đề nghị huỷ,
  khoá form, GDV chỉ còn nút *Huỷ phiên trực*). **Chỉ GDV mới đóng được phiên thật**
  (`draft_cancel` → `cancelled`, ngõ cụt — làm lại phải mở phiên mới cho cùng ngày)
- Phiên đã **Hoàn thành** vẫn mở lại sửa được (`request_edit`): GDV mở lại thì phải đẩy KSV
  duyệt lại từ đầu; KSV tự mở lại (`self_edit`) thì tự sửa rồi tự chốt (`ksv_finalize_edit`)
- **Khoá theo đúng người, không theo vai**: một khi `gdv1_id`/`gdv2_id` đã chọn, chỉ đúng 2 tài
  khoản đó sửa được; `ksv_id` khoá cứng từ lần chọn đầu, đẩy lại sau khi bị từ chối vẫn phải
  đúng người đó. Sai người → `NotAllowedError` → HTTP 403
- Một ngày có thể có **nhiều phiên** (đã huỷ rồi mở lại). Unique index một phần
  `ux_so_truc_active_date (truc_date) WHERE status != 'cancelled'` bảo đảm mỗi ngày chỉ một
  phiên đang hoạt động, đồng thời chặn tranh chấp khi hai GDV cùng mở một ngày
- Cảnh báo (không chặn) khi **Đối chiếu CITAD cùng ngày chưa khớp**; link sang thẳng tab
  Lịch sử của `/doi_chieu_citad?ngay=`. Từ 23/08/2026 **chỉ bản đã "Lưu bảng cuối"
  (`status='final'`) mới tính là đã đối chiếu** — bảng tạm coi như chưa có, vì Napas/PSS-MDP
  thường do người khác bổ sung sau nên bản tạm "khớp" chỉ khớp trên phần đã nhập
- Badge **Sổ trực chờ xử lý** trên sidebar; trang chủ nhắc khi sau 16h (giờ máy chủ) chưa ai
  mở sổ. Tab **Lịch sử** không lọc thì hiện **toàn bộ** phiên trực (trước 23/08/2026 chỉ hiện
  1 phiên gần nhất), có dòng ngăn cách khi sang tháng khác; xuất Excel vẫn bắt buộc chọn khoảng ngày
- Phân quyền: `menu.so_truc` (vào module, xem lịch sử) + `so_truc.ksv_confirm`
  (được xuất hiện trong danh sách chọn KSV)

### Module Ôn tập (Quizz)
- Nhóm **Tính năng khác** → **Ôn tập** (`/quiz`). Dùng chung cho cả cơ quan, không thuộc phòng nào
- **Bộ câu hỏi chỉ tải lên một lần** — người sau chọn bộ có sẵn để ôn, không phải nhập lại.
  File Excel, cột theo thứ tự: `Câu hỏi | Đáp án 1 | Đáp án 2 | Đáp án 3 | Đáp án 4 | Đáp án đúng`
  (đáp án đúng ghi **số 1-4**). Bỏ trống *Đáp án 4* nếu câu chỉ có 3 lựa chọn. Nút *Tải file mẫu*
  xuất đúng khuôn này. Dòng 1 được nhận là tiêu đề nếu ô A chứa chữ "câu hỏi"
- Dòng sai (đáp án đúng không phải số, trỏ vào ô trống, dưới 2 lựa chọn) **bị bỏ qua kèm số dòng**
  để người nhập mở Excel sửa; cả file không có dòng nào hợp lệ thì bị từ chối. Không bao giờ đoán
  đáp án — đoán sai là người học nhớ sai
- Chặn tải lên trùng: **trùng tên** (`UNIQUE`) và **trùng nội dung câu hỏi**, báo rõ bộ cũ tên gì.
  Vân tay lấy từ **nội dung đã đọc**, không phải từ byte của file — mở file ra xem rồi bấm lưu là
  Excel đổi dấu thời gian bên trong, băm theo file sẽ không nhận ra bản sao
- **Cài đặt trước khi làm bài**: chế độ (*Ôn tập* — hiện đáp án ngay sau mỗi câu / *Thi thử* — chỉ chấm
  khi nộp), số câu (10/20/30/50/100 hoặc tất cả), **trộn thứ tự câu hỏi**, **trộn thứ tự đáp án**,
  **thời gian mỗi câu** (10-90 giây hoặc không giới hạn), **tổng thời gian làm bài** (5-90 phút hoặc
  không giới hạn). Hết giờ câu thì tự sang câu kế; hết tổng giờ thì hệ thống tự nộp bài
- Màn làm bài `/quiz/play` chiếm **toàn màn hình** (không sidebar): 4 ô đáp án màu + hình khối xếp
  lưới 2×2 bằng nhau, thanh tiến trình, hai đồng hồ. Nộp xong hiện điểm, số câu
  **đúng / sai / bỏ trống**, thời gian làm và phần **Xem lại bài** từng câu (đáp án đúng gắn nhãn
  *ĐÁP ÁN ĐÚNG* + viền trắng, ô chọn sai gắn nhãn *BẠN CHỌN*, các ô còn lại xám hẳn)
- **Tạm dừng & làm tiếp**: tiến độ được **lưu lên máy chủ sau mỗi câu trả lời**, không đợi nộp bài.
  Mất kết nối, máy ngủ, tắt máy hay đóng nhầm tab đều không mất bài — vào lại bộ câu hỏi đó, thẻ hiện
  **Làm tiếp** và nối đúng câu đang đứng, kèm đáp án đã chọn và thời gian đã tiêu. Nút **Tạm dừng**
  trên thanh trên lưu rồi thoát; chỉ báo nhỏ cạnh đồng hồ cho biết đã lưu hay còn câu chưa gửi được
- **Đồng hồ đếm thời gian làm bài, không phải thời gian thực** — tạm dừng thì đồng hồ dừng theo. Máy
  chủ chỉ cho thời gian **tăng**, gửi lại gói cũ không kéo dài thêm được
- **Mỗi người mỗi bộ nhiều nhất một bài dở.** Bấm *Bắt đầu bài mới* trên bộ đang có bài dở sẽ bỏ bài
  đó (có cảnh báo trước); menu ⋮ còn có *Bỏ bài đang làm dở*
- **Lịch sử của tôi** (30 lượt gần nhất, bấm để xem lại bài) và **Bảng xếp hạng** theo từng bộ — mỗi
  người lấy lượt tốt nhất, cùng điểm thì ai nhanh hơn đứng trên. Bảng xếp hạng **chỉ tính bài Thi thử**;
  chế độ Ôn tập hiện sẵn đáp án nên điểm không có ý nghĩa so sánh
- Chấm điểm **luôn ở backend**, đọc đáp án đúng từ DB — client chỉ gửi "tôi chọn ô số mấy"
- Đề được cố định ngay lúc bắt đầu (thứ tự câu + thứ tự đáp án lưu vào `quiz_attempt_items`): F5 giữa
  bài không sinh đề mới, và màn xem lại hiển thị đúng đề đã làm
- ⚠️ **Xoá một bộ là xoá luôn** toàn bộ câu hỏi, mọi lượt làm bài của mọi người và bảng xếp hạng của bộ
  đó (`ON DELETE CASCADE`) — không hoàn tác được
- Bảng DB: `quiz_sets`, `quiz_questions`, `quiz_attempts`, `quiz_attempt_items`
- Phân quyền riêng theo nhóm: `menu.quiz` (vào module, ôn tập, xem xếp hạng) +
  `quiz.upload` (tải bộ mới / đổi tên) + `quiz.delete` (xoá bộ)

---

### Module Chuẩn hoá văn bản (QĐ 979/QyĐ-NHNo-PC)
- Nhóm **Tính năng khác** → **Chuẩn hoá văn bản** (`/vb_format`). Dùng chung cho cả cơ quan, không thuộc phòng nào
- Tải một file **`.docx`** lên → hệ thống sửa về đúng thể thức và kỹ thuật trình bày theo
  *Quy định 979/QyĐ-NHNo-PC* (Điều 4–17, Phụ lục III, Phụ lục IV) → hiện **nhật ký từng đoạn đã sửa**
  → bấm *Tải văn bản đã chuẩn hoá*. File `.doc` đời cũ bị từ chối kèm hướng dẫn (python-docx không đọc
  được định dạng nhị phân cũ)
- **Đường kẻ ngang dưới Tiêu ngữ / tên đơn vị / trích yếu** (Điều 7.2, 8.2, 11.2) vẽ bằng đối tượng
  `<v:line>` — **không phải gạch chân**: quy định đòi đường dài **1/3–1/2** dòng chữ ở tên đơn vị và
  trích yếu, mà `w:u` luôn dài đúng bằng chữ còn `w:pBdr` luôn dài hết bề ngang đoạn. Mẫu 979 cũng
  dùng `<v:line>` (đếm được 7 thẻ, không có gạch chân nào). Vẽ lại nhiều lần không chồng vạch
- **Đo bề rộng chữ thật rồi nén ký tự cho dòng thể thức vừa một dòng** (`do_chu.py`): đo bằng chính
  phông sẽ in qua Pillow. "NGÂN HÀNG NÔNG NGHIỆP VÀ PHÁT TRIỂN NÔNG THÔN VIỆT NAM" cỡ 12 đậm đo được
  238,0 pt / ô 241,2 pt. Tràn thì nén `w:spacing` tối đa **−24 twip** (đúng mức Phụ lục V dùng),
  **không hạ cỡ chữ**; hết trần vẫn tràn thì dừng và ghi cảnh báo
- **Ba cách kẻ vạch sẵn, ba cách xử lý**: hình vẽ (`<v:line>`, Straight Connector) thì **giữ
  nguyên**; gạch chân (`w:u`) và viền dưới của đoạn (`w:pBdr/w:bottom`) thì **gỡ rồi vẽ lại** — hai
  cách sau không cắt ngắn được (gạch chân dài đúng bằng chữ, viền đoạn dài hết bề ngang đoạn) nên
  không làm được yêu cầu "1/3 đến 1/2 dòng chữ". Chỉ nhấc riêng `w:bottom`, giữ viền trên/trái/phải
- **Không vẽ chồng lên đường kẻ có sẵn**: Word neo hình vẽ tay vào *chính đoạn có chữ*
  (`positionV relativeFrom="paragraph"`), không đặt ở đoạn riêng. Chỉ soi đoạn kế tiếp là vẽ thêm
  vạch thứ hai. Ở chính đoạn chỉ nhận đúng hình đường thẳng (`<v:line>`, `prstGeom prst="line"`,
  `straightConnector1`) — nhận mọi `<w:drawing>` thì đoạn tên đơn vị có logo sẽ không bao giờ được kẻ
- **Số trang đếm lại từ 1**: `<w:pgNumType w:start="N"/>` theo chân văn bản khi người soạn cắt một
  phần ra khỏi tài liệu dài. Chèn số trang đúng chỗ mà đếm từ 23 thì nhìn vẫn là sai — nay ép về 1
  và ghi số cũ vào nhật ký
- **Bỏ ngắt trang thủ công** (bật sẵn, tắt được ở tab Cấu hình): dấu ngắt tay đặt theo bố cục *cũ*;
  chuẩn hoá làm chữ cao lên nên nó rơi vào giữa chừng và đẻ ra một trang gần như trống. Đoạn chỉ
  chứa dấu ngắt thì bỏ cả đoạn, đoạn có chữ thì chỉ nhấc thẻ `<w:br>` — không mất chữ. Tắt khi văn
  bản thật sự cần sang trang mới (Phụ lục ban hành kèm theo Quyết định)
- **Mục con của gạch đầu dòng** — QĐ 979 chỉ đánh số tới cấp *điểm* (a, b, c), dưới đó không có
  cấp nào được quy định nên đây là **thói quen trình bày, không phải điều khoản**:
  - **Giữ thụt lề tác giả đã tự đặt**: gạch đầu dòng thụt sâu hơn mức chung là cách duy nhất trong
    `.docx` để nói "đây là mục con"; ép `left_indent` về 0 là xoá phẳng phân cấp đó. Lời văn thường
    thụt vô cớ thì vẫn dọn về 0 như cũ
  - **Tự nhận mục con** (bật sẵn): dòng gạch đầu dòng kết thúc bằng `:` mở một danh sách con; mục
    con dùng ký tự `+` và thụt thêm 1 cm. Danh sách con **đóng** ở dòng kết thúc bằng `.` — nhưng
    chỉ khi các dòng trên đã dùng `;` (quy ước Điều 15.4), vì người soạn chấm câu mọi dòng bằng `.`
    thì dấu chấm không nói lên điều gì — hoặc ở dòng đầu tiên không phải gạch đầu dòng
  - Không áp cho danh sách **Nơi nhận** và **Kính gửi**: cũng dùng `-` nhưng là danh sách phẳng, cỡ chữ riêng
- **Số của danh sách tự động ăn theo cỡ chữ của đoạn**: số thứ tự / dấu chấm tròn do Word sinh lúc
  hiển thị, lấy định dạng từ `w:pPr/w:rPr` (dấu đoạn) chứ không từ `<w:r>` nào — sửa cỡ chữ từng run
  không chạm tới nó, nên số "4." "I." in ra bằng nửa con chữ. Chỉ đồng bộ ở đoạn CÓ `numPr`
- **Không đánh thêm số trang khi văn bản đã có**: soi đủ sáu chỗ (header/footer × mặc định/trang
  đầu/trang chẵn). Trước đây chỉ soi header mặc định nên văn bản đánh số ở chân trang bị đè thêm
- **"Kính trình:"** được nhận như "Kính gửi" — Mẫu 16 Phụ lục V (Phiếu trình chuyển) dùng đúng chữ này
- **Bảng dựng để canh chỗ vẫn được áp thể thức**: khối "Kính gửi / Kính trình" hay được dựng bằng
  bảng (một ô nhãn, một ô tên người nhận). Mọi ô **cùng một bảng** với dòng đó ăn theo thể thức của
  khối — Điều 4.2 chỉ dành cho bảng số liệu. Ranh giới là **cái bảng** (`ap_dung.nhom_bang()`), không
  phải "ô liền kề": lan theo ô liền kề thì một bảng số liệu dán sát ngay sau bị kéo theo trọn vẹn
- **Danh sách chấm tròn tự động được đổi thành gạch đầu dòng TRƯỚC khi nhận diện thể thức.** Dấu
  chấm tròn do Word vẽ lúc hiển thị, không nằm trong `p.text` — mà luật nhận khối **Nơi nhận** lại
  đi tìm đúng dấu gạch đầu dòng đó. Khối Nơi nhận dựng bằng nút bullet của Word vì thế trượt hết
  mọi luật, mang mã `bang` và giữ nguyên cỡ chữ gốc. `ap_dung.go_bullet_tu_dong()` chạy trước
  `phan_loai()` (cùng chỗ với `bo_ngat_trang_thu_cong()`). Tắt ô *"Chuyển danh sách chấm tròn tự
  động…"* thì lỗi này quay lại — cố ý không vá bằng cách dạy bộ nhận diện đọc `numPr`, nó chỉ đọc
  con chữ và phải giữ đúng một nguồn dữ liệu
- **Quyền hạn người ký chiếm được hai dòng** (Điều 13.2): "TL. TỔNG GIÁM ĐỐC" rồi "GIÁM ĐỐC TRUNG
  TÂM THANH TOÁN". Dòng thứ hai lọt qua phép thử họ tên (5 từ, từ nào cũng mở đầu chữ hoa) nên từng
  bị nhận là **họ tên**, và họ tên thật nằm dưới khoảng chừa chữ ký thì không còn ai nhận. Nay xét
  **chức danh trước, họ tên sau**, đi tối đa 2 dòng
- **Từ khoá chức danh dùng "TRƯỞNG" để trần**, không liệt kê từng chức danh ghép: đã có TRƯỞNG
  PHÒNG / BAN / ĐƠN VỊ / BỘ PHẬN mà "TRƯỞNG NHÓM" vẫn lọt, khiến cả khối chữ ký của một Báo cáo
  không được áp thể thức
- **Tiêu ngữ được sửa cả hoa/thường**, không chỉ dấu nối và dấu cách: Điều 7.2 nói thẳng "chữ cái
  đầu của các cụm từ được viết hoa" nên "Hạnh **P**húc" là sai. Kiểu bỏ dấu ("Hoà" / "Hòa") vẫn
  **không** bị đụng — quy định không nói gì, đó là thói quen từng đơn vị. Không sửa khi chuỗi tách
  ra khác 3 cụm
- **Bỏ tab / dấu cách thụt đầu dòng gõ tay** ở thành phần mà quy chuẩn tự đặt `thut_cm`: để lại thì
  dòng đó thụt gấp đôi (tab + 1 cm). Tab **giữa** dòng không bị đụng — đó là canh cột
- **Trích yếu công văn xuống dòng cũng được nối dài**: luật nối dài vốn chỉ chạy từ mốc *tên loại
  văn bản*, mà công văn thì không có tên loại — trích yếu của nó là dòng `V/v …` ngay dưới số ký
  hiệu. Dòng thứ hai vì thế rơi vào lời văn và bị áp cỡ 14 / căn đều hai bên / thụt 1 cm, trong khi
  dòng trên là cỡ 12 canh giữa. Dùng lại chính hàm cũ nên thừa hưởng nguyên các hàng rào của nó
- **Thêm dấu cách sau tiền tố đề ký**: "TL.TỔNG GIÁM ĐỐC" → "TL. TỔNG GIÁM ĐỐC" (TM. / KT. / TL. /
  TUQ. / Q., chỉ nhận tiền tố viết hoa đứng đầu dòng)
- **Khối tên đơn vị chia vai theo chữ đậm tác giả đã đặt** (Điều 8.2 — ban hành thì đậm + có đường
  kẻ, chủ quản thì không). Đây là dấu hiệu do người viết đặt, dùng trước mọi phép đoán trên con chữ;
  bắt được cả trường hợp tên đơn vị ban hành dài trải hai dòng mà dòng sau mở đầu bằng danh từ
  ("BAN TRIỂN KHAI … / TỔ TRIỂN KHAI …"). Bỏ qua khi cả khối cùng đậm (tác giả không phân biệt) hoặc
  khi các dòng đậm không liền nhau ở cuối khối
- **Tên đơn vị dài trình bày nhiều dòng** (Điều 8.2): khối in hoa đầu văn bản được gom thành từng
  **cụm** trước khi lấy cụm cuối làm đơn vị ban hành. "NGÂN HÀNG NÔNG NGHIỆP / VÀ PHÁT TRIỂN NÔNG
  THÔN VIỆT NAM" là MỘT tên xuống dòng — đọc mỗi dòng là một cấp đơn vị thì nửa trên bị bỏ in đậm.
  Dấu hiệu nhận cụm cố ý để hẹp: chỉ dòng mở đầu bằng liên từ hoặc gạch nối (`VÀ`, `-`, `–`, `—`),
  vì không tên cơ quan nào bắt đầu như vậy. Khối hai cấp thật ("… VIỆT NAM" / "CHI NHÁNH HÀ NỘI")
  không đổi
- **Trích yếu xuống dòng**: dòng nối tiếp cũng được nhận là trích yếu (tối đa 3 dòng, dừng khi gặp
  `Căn cứ` / `Điều` / `Kính gửi`…), nếu không thì dòng thứ hai bị căn đều hai bên và không in đậm
  trong khi dòng trên căn giữa
- **Tab "Mẫu trình bày sẵn"** — bản trắng của **18 mẫu Phụ lục V** (Nghị quyết, Quyết định,
  Công văn, Tờ trình, Giấy mời, Biên bản, Đơn xin nghỉ phép…). Bấm *Tải mẫu* là có file `.docx`
  đúng thể thức để điền nội dung vào, khỏi phải copy-paste từ file Phụ lục. Lề trang đã đặt về
  đúng quy chuẩn 20/20/30/20 mm (bản trong Phụ lục để 15 mm cho vừa trang giấy) và đã gỡ header
  mang số trang của Phụ lục
  - **Phần "Ghi chú" của Phụ lục được giữ nguyên** (đoạn ghi chú ở Mẫu 07 và các chú thích chân
    trang ở Mẫu 04, Mẫu 17) — người soạn **tự xoá trước khi phát hành**
  - 18 file nằm ở `templates/vb_mau/`, sinh bằng `python scripts/tach_mau_vb.py`. Chỉ chạy lại khi
    Phụ lục V có bản mới; máy chính không chạy script này
- **Ba việc được làm tự động:**

  | Nhóm | Nội dung |
  |---|---|
  | Thể thức trình bày | Khổ giấy A4, lề 30/20/20/20 mm, đánh số trang canh giữa lề trên (bỏ trang 1), phông Times New Roman (đặt cho cả nhánh `w:cs` để chữ có dấu không lệch phông), màu chữ đen, **giãn dòng 1,2** và cách đoạn 6 pt cho lời văn, thụt dòng đầu 1 cm, chuẩn hoá Tiêu ngữ về “Độc lập - Tự do - Hạnh phúc” (gạch NỐI, mỗi bên một dấu cách — Điều 7.2), và **cỡ chữ / kiểu chữ / căn lề / giãn dòng riêng cho 28 thành phần thể thức** theo Phụ lục III |
  | Viết hoa (Phụ lục IV) | Chữ đầu câu và đầu dòng (có danh sách viết tắt chặn: `TP.`, `v.v.`, `TM.`…); viện dẫn (Phần/Chương/Mục/Tiểu mục/**Điều** viết hoa, *khoản* và *điểm* viết thường — mục V.7); và **từ điển cụm từ** do người dùng tự khai |
  | Đánh số, gạch đầu dòng | Mọi ký tự gạch đầu dòng (`•`, `–`, `*`, `+`…) → `- `; khoản `1)` `1/` → `1.`; điểm `a.` `a/` → `a)`; mục La Mã `I)` `I/` → `I.`; danh sách **chấm tròn** tự động của Word → gạch đầu dòng gõ tay |

- **Giãn dòng và cách đoạn khác nhau theo từng khối.** Điều 12.6 cho một *dải* (tối thiểu
  dòng đơn, tối đa 1,5) nên phải đo lại từ chính văn bản QĐ 979 mới biết lấy số nào:

  | Khối | Giãn dòng | Cách đoạn | Căn cứ |
  |---|---|---|---|
  | Lời văn (căn cứ, Chương, Điều, khoản, điểm) | **1,2** | 6 pt | Đo từ `Phần VB_Hướng dẫn thể thức văn bản.docx` |
  | Khối thể thức đầu trang (Quốc hiệu, Tiêu ngữ, tên đơn vị, số ký hiệu, ngày tháng, tên loại, trích yếu) | **dòng đơn** | **0** | Điều 7.3 và 8.2: "trình bày cách nhau dòng đơn" |
  | Khối cuối (Nơi nhận, chức vụ và họ tên người ký) | **dòng đơn** | **0** | cùng lý do |

  Lấy 1,5 là lấy đúng cận TRÊN của dải — hợp lệ nhưng thưa hơn hẳn mẫu. Áp luôn cho khối
  đầu trang thì Tiêu ngữ bị đẩy xa Quốc hiệu, khối đầu cao gấp đôi mẫu Phụ lục V. Hai
  cột cuối của bảng thành phần thể thức trong tab Cấu hình cho phép để trống = theo giá
  trị chung, hoặc điền số = ép chính xác cho riêng thành phần đó
- **Cỡ chữ khối đầu lấy theo con số đếm được trên 18 mẫu Phụ lục V**, không lấy cận trên
  của dải: Quốc hiệu **12** (17/18 mẫu), tên đơn vị **12**, trích yếu công văn **12**,
  Tiêu ngữ và số ký hiệu **13**. Chênh một điểm làm dòng "NGÂN HÀNG NÔNG NGHIỆP VÀ
  PHÁT TRIỂN NÔNG THÔN VIỆT NAM" tràn cột và đẩy chữ "NAM" xuống dòng riêng — "Việt Nam"
  nằm trong danh sách cụm từ liền dòng để chặn hẳn
- **"Kính gửi" có hai cách trình bày** (Điều 15.4.a): gửi **một** nơi thì cả cụm nằm trên một
  dòng và **canh giữa** (mẫu 06, 09); gửi **nhiều** nơi thì chỉ có chữ "Kính gửi:" đứng
  riêng rồi liệt kê xuống dòng, để **sát trái** (mẫu 08). Hai tình huống có hai mục cấu hình riêng
- **Khoảng trống trước đoạn (Spacing Before) luôn được đưa về 0.** Khoảng cách thật giữa
  hai đoạn là *After của đoạn trên + Before của đoạn dưới*, nên 7pt/7pt cho ra **14pt** mà
  hộp Paragraph chỉ hiện hai số 7. Đưa Before về 0 để chỉ còn một nguồn quyết định.
  Khối đầu trang, Kính gửi và khối cuối về **0/0**; lời văn giữ After sẵn có nếu đã ≥ 6pt
  (Điều 12.6 chỉ nêu mức tối thiểu). Ô bảng trong khối đầu cũng về 0/0 — khối đó hay được
  dựng bằng bảng hai cột; bảng số liệu giữa văn bản không bị ảnh hưởng
- **Xuống dòng để trình bày thì KHÔNG viết hoa chữ đầu.** Phụ lục IV mục I nói "đầu một *câu
  hoàn chỉnh*". Phải đủ hai điều kiện mới viết hoa: đoạn đó là **lời văn thật** (không phải
  trích yếu, tên đơn vị, Kính gửi, Nơi nhận, chức danh — những thứ đó là *cụm từ*, không
  phải câu) **và** đoạn liền trước đã kết thúc bằng `.` `!` `?` `;` `:`. Ví dụ ô trích yếu
  "V/v Thông báo thay đổi tên/địa chỉ đăng ký" xuống dòng thành "trên hệ thống SWIFT" cho cân
  ô — giữ nguyên chữ thường. Luật viết hoa **sau dấu chấm giữa đoạn** không đổi
- **Tên loại văn bản ngoài danh sách Điều 3 vẫn được nhận** (ĐỀ CƯƠNG, KẾ HOẠCH KIỂM
  TRA…) — Điều 3.2.ađ cho phép "các loại văn bản… khác phù hợp với thực tiễn" nên danh
  sách không bao giờ đủ. Nhận theo hình thức: dòng in hoa ngắn đứng riêng **ngay dưới số
  ký hiệu hoặc địa danh - ngày tháng**. Không có mốc đó thì không đoán — một dòng in hoa
  giữa văn bản có thể là tiêu đề bảng, tên phụ lục, bất cứ thứ gì
- **Dòng ngày tháng ĐỂ TRỐNG vẫn được nhận** ("Hà Nội, ngày   tháng   năm 2026") — dự
  thảo trình ký và mọi mẫu trong Phụ lục V đều viết như vậy
- **Cụm từ không được tách dòng**: ví dụ *Tổng Giám đốc* sẽ không bị Word ngắt thành "Tổng" ở cuối dòng
  và "Giám đốc" ở dòng dưới — dấu cách bên trong cụm được đổi thành dấu cách không ngắt (U+00A0).
  Danh sách cụm từ khai trong tab Cấu hình; **chỉ nên khai cụm ngắn**, cụm dài bị ghim liền dòng sẽ đẩy
  nguyên khối xuống dòng dưới và để lại khoảng trống dài ở dòng trên
- **Đánh dấu vùng đã sửa bằng highlight**, ba màu cho ba loại việc khác nhau:
  **vàng** = sửa định dạng riêng của đoạn (cỡ chữ, đậm/nghiêng, căn lề) · **xanh lá** = sửa con chữ
  (viết hoa, đánh số, gạch đầu dòng) · **xanh ngọc** = cụm từ được ghép liền dòng.
  Những sửa đổi áp **đồng loạt cả văn bản** (giãn dòng, cách đoạn, phông chữ, thụt dòng đầu) chỉ vào
  mục *Sửa chung* của nhật ký, **không bôi màu** — bôi hết thì cả trang vàng khè, không còn chỗ để soi
- ⚠️ **Danh sách ĐÁNH SỐ tự động của Word được giữ nguyên** kèm cảnh báo. Số "1." "2." không nằm trong
  file — Word tính lúc hiển thị — nên đổi thành số gõ tay đồng nghĩa với tự đếm lại toàn bộ, lệch một
  chỗ là sai số cả văn bản mà không có gì báo. Có công tắc bật trong tab Cấu hình cho ai chấp nhận rủi ro
- ⚠️ Phụ lục IV phần lớn **đòi hiểu ngữ cảnh** (tên người, tên địa lý, tên sự kiện) — máy không đoán,
  chỉ sửa những cụm khai trong từ điển. Cụm đang viết **HOA TOÀN BỘ** được bỏ qua để không phá dòng tên
  đơn vị trên đầu văn bản
- Ô **bảng số liệu** giữa văn bản chỉ được sửa phông chữ, không đụng cỡ chữ và căn lề (Điều 4.2 cho phép
  bảng biểu trình bày riêng). Nhưng đoạn trong bảng vẫn được nhận diện, vì khối Quốc hiệu / tên đơn vị
  đầu trang thường được dựng bằng bảng hai cột
- **Tab *Cấu hình quy chuẩn***: lề trang, phông chữ, giãn dòng, cách đoạn; cỡ chữ / đậm / nghiêng /
  hoa-thường / căn lề / thụt dòng cho từng thành phần thể thức; hai danh sách cụm từ; các công tắc
  đánh số; màu highlight. Nhập cỡ chữ ra ngoài dải quy định thì **cảnh báo, không chặn**. Nút
  *Khôi phục mặc định theo QĐ 979*. Chỉ **phần khác mặc định** được lưu vào DB — quy định đổi thì các
  mục chưa từng đụng tới tự đi theo mặc định mới
- File kết quả nằm trong `data/temp_vb_format/`, **sống hết ngày làm việc và bị dọn lúc 23h** cùng các
  tính năng có file tạm khác
- Bảng DB: `vb_format_config` (đúng một dòng, `CHECK (id = 1)`)
- Phân quyền riêng theo nhóm: `menu.vb_format` (tải file lên, chuẩn hoá, tải kết quả) +
  `vb_format.config` (sửa thông số quy chuẩn). Tách hai quyền vì quy chuẩn là của cả đơn vị — một
  người đổi là mọi văn bản người khác chạy sau đó đều theo số mới.
  **Chỉ có `menu.vb_format` thì tab Cấu hình vẫn mở được để XEM, nhưng mọi ô nhập đều bị khoá**
  (không chỉ hai nút Lưu / Khôi phục) — khoá mỗi nút thì người dùng vẫn gõ được vào gần 200 ô,
  tưởng đã sửa xong rồi mới phát hiện không lưu được. Backend chặn độc lập ở cả hai đường ghi
  (`PUT /cau-hinh` và `POST /cau-hinh/mac-dinh` đều trả 403)

---

### Module Quản lý nhân sự
- Nhóm **Quản lý nhân sự** → **Hồ sơ cán bộ** (`/hr_profiles`) · **Tra cứu & Thống kê**
  (`/hr_lookup`) · **Nhắc lịch** (`/hr_reminders`). Dùng chung cả cơ quan, không thuộc phòng nào
- **Quản trị viên không có hồ sơ nhân sự.** Tài khoản `admin` / `admin_l2` là tài khoản hệ thống,
  không thuộc phòng nào, không có ngày tuyển dụng hay bậc lương — nên bị loại khỏi danh sách hồ sơ,
  thống kê, tra cứu và nhắc lịch (`hr_service.ROLES_KHONG_HO_SO`). Mở hồ sơ của tài khoản quản trị trả
  **404 kèm lý do**, không phải màn hình trống. Quản trị viên vẫn vào màn hình bình thường để nhập hộ
  hồ sơ cho cán bộ
- **Hồ sơ khoá theo tài khoản** (`user_tttt.id`) — không có danh sách cán bộ riêng. Họ tên, mã cán bộ,
  phòng đọc thẳng từ `user_tttt`; điện thoại, email và **ngày tuyển dụng** sửa trong hồ sơ **ghi ngược
  lại** `user_tttt` chứ không tạo bản sao. Hệ quả: cán bộ chưa có tài khoản thì chưa có hồ sơ
- **"Ngày tuyển dụng" chính là "Ngày vào ngành"** (`user_tttt.join_industry_date`) — một mốc, một cột,
  sửa ở màn Hồ sơ cán bộ hay màn Quản lý User đều là sửa cùng một chỗ. ⚠️ Cột này quyết định **số ngày
  phép năm** (`compute_annual_leave()`: 12 ngày + 1 ngày mỗi 4 năm) nên **sửa được cần `hr.edit_all`**,
  không nằm trong phần cán bộ tự khai — tự khai được là tự cộng phép cho mình
- **Tám phân hệ:**

  | Phân hệ | Nội dung chính | Cán bộ tự khai? | File đính kèm |
  |---|---|---|---|
  | Hồ sơ cá nhân | Giới tính, ngày sinh, CCCD, địa chỉ, điện thoại, email, ảnh thẻ, số người phụ thuộc, người liên lạc | ✔ | ảnh thẻ |
  | Hồ sơ bằng cấp | Trình độ, chuyên ngành, chứng chỉ ngoại ngữ / tin học / khác | ✔ | ✔ |
  | Quy hoạch, bổ nhiệm, điều động | Loại, chức vụ, đơn vị, số & ngày quyết định, hiệu lực từ–đến | ✘ | ✔ |
  | Thông tin công tác | Phòng (từ tài khoản), chức vụ, **ngày tuyển dụng = ngày vào ngành**, loại hợp đồng | ✘ | — |
  | Quá trình công tác | Từ ngày – đến ngày – chức vụ – đơn vị, cờ *đã qua chi nhánh* | ✘ | — |
  | Nghỉ gián đoạn | Từ ngày – đến ngày, lý do, không hưởng lương, có tính thời gian công tác không | ✘ | — |
  | Hồ sơ lương | Bậc, hệ số V1/V2, phụ cấp chức vụ, ngày QĐ nâng lương, chu kỳ nâng lương | ✘ | ✔ |
  | Đào tạo tại Agribank | Tên khoá – thời gian – Online/Offline – kết quả | ✔ | ✔ |
  | Công cụ, dụng cụ | Tên, mã tài sản, ngày cấp, **trạng thái** (đang dùng / đã chuyển người khác / đã trả văn phòng / mới cấp mà TSC chưa cập nhật), dự kiến cấp mới | ✔ | — |

- **Thứ tự danh sách: phòng → chức vụ → tên.** Trong mỗi phòng, **Trưởng phòng đứng trước, rồi Phó
  phòng, rồi nhân viên** (hậu kiểm viên và chuyên viên cùng bậc, xếp lẫn nhau theo tên); Ban Giám đốc
  thì Giám đốc trước Phó Giám đốc. Bảng thứ tự ở `hr_service.THU_TU_CHUC_VU` — **không** dùng chung
  `ROLE_RANK` của `backend/core/enums.py`: bảng đó xếp theo *quyền* (hậu kiểm viên đứng trên trưởng
  phòng) và đang dùng để chặn leo thang quyền, trộn vào nhau thì sửa thứ tự hiển thị là vô tình đổi
  luật phân quyền
- **Tên sắp đúng bảng chữ cái tiếng Việt** — không dùng `ORDER BY` của SQLite (so sánh theo mã byte
  nên mọi chữ có dấu nằm sau `z`). Sắp bằng Python qua `hr_service.khoa_ten()`: bỏ dấu để so sánh
  (Đ xếp cùng D, Ă/Â cùng A) và lấy **chữ cuối làm khoá chính** theo lối gọi tên tiếng Việt —
  *Đào Tiến Thành* nằm ở vần **Th**, cạnh *Thảo*, *Thu*, *Thủy*
- **Tra cứu tại từng thời điểm**: chọn ngày rồi lọc theo *Toàn Trung tâm / Ban Giám đốc / Trưởng phòng /
  Phó phòng / Cán bộ trong quy hoạch*. Phòng tại ngày đó lấy từ `staff_department_history` (**không**
  lấy phòng hiện tại), chức vụ và quy hoạch lấy từ quyết định còn hiệu lực tại ngày đó. Xuất Excel được
- **Thống kê**: theo phòng ban / giới tính / trình độ / độ tuổi / đã qua chi nhánh hay chưa. Trình độ
  dò theo **từ khoá** trên tên bằng người nhập gõ tay và lấy bằng cao nhất; không nhận ra thì xếp
  *"Khác"* chứ không đoán bừa một bậc
- **Nhắc lịch**: nâng lương (**trước 1 quý**, tính từ ngày QĐ + chu kỳ, mặc định 36 tháng), bổ nhiệm lại
  (**trước 1 năm**, tính từ ngày hết hiệu lực của QĐ bổ nhiệm), cấp công cụ/điện thoại mới (**trước 1
  quý**, theo cột *Dự kiến cấp mới*). Việc **đã quá hạn vẫn hiện** và được tô đỏ
- **Tệp đính kèm chọn được ngay ở bước Thêm dòng** — không phải lưu rồi mở lại. Tệp chọn lúc đó hiện
  trong danh sách với nhãn *chờ lưu* (bỏ ra được), và chỉ thực sự tải lên sau khi dòng hồ sơ đã tạo
  (API đính kèm cần `item_id`, mà id chỉ có sau khi lưu). Tệp lỗi **không** làm mất dòng vừa tạo — báo
  đích danh tệp nào hỏng để tải lại
- **Định dạng và dung lượng** — khai một chỗ trong `backend/api/hr.py` rồi trả qua `GET /api/hr/meta`
  để ô chọn file ngoài giao diện lọc đúng thứ backend nhận:

  | | Đuôi file | Trần dung lượng |
  |---|---|---|
  | Ảnh cá nhân (ảnh thẻ) | `.jpg` `.jpeg` `.png` `.webp` | 5 MB |
  | Tệp đính kèm (bằng cấp, quyết định) | `.pdf` + `.jpg` `.jpeg` `.png` `.webp` | 15 MB |

  Kiểm theo **phần mở rộng**, và kiểu MIME lưu lại cũng **suy từ đuôi file**, không lấy `content_type`
  do trình duyệt khai: đó là chuỗi client tự đặt, lưu lại rồi phát ngược ra thì người tải lên chọn được
  luôn kiểu nội dung máy chủ sẽ trả cho người khác — ảnh thẻ được trả **inline** nên đó là đường đưa
  nội dung lạ chạy trên chính tên miền của hệ thống
- **Ảnh thẻ và file quyết định lưu trong DB** (BLOB, giống ảnh chữ ký). Để ngoài đĩa thì sao lưu DB
  xong vẫn mất file
- Bảng DB: `hr_profiles`, `hr_degrees`, `hr_appointments`, `hr_work_history`, `hr_breaks`,
  `hr_salaries`, `hr_trainings`, `hr_tools`, `hr_attachments`
- **Phân quyền theo nhóm** — `menu.hr_profiles` là mức tối thiểu (vào màn hình + tự khai hồ sơ của
  chính mình), mọi thứ khác cộng thêm:

  | Việc | Hồ sơ của mình | Hồ sơ người khác |
  |---|---|---|
  | Xem | `menu.hr_profiles` | + `hr.view_all` |
  | Sửa phần tự khai | `menu.hr_profiles` | + `hr.edit_all` |
  | Sửa phần công tác, bổ nhiệm, quá trình công tác, nghỉ gián đoạn | `hr.edit_all` | `hr.edit_all` |
  | Xem hồ sơ lương | `menu.hr_profiles` | + `hr.salary_view` |
  | Sửa hồ sơ lương | `hr.salary_edit` | `hr.salary_edit` |

  Thêm `menu.hr_lookup` (tra cứu & thống kê), `hr.export` (xuất Excel), `menu.hr_reminders` (nhắc lịch).
  **Sửa lương luôn cần quyền riêng, kể cả hồ sơ của chính mình** — bậc lương là số liệu do người làm chế
  độ nhập theo quyết định. Hồ sơ lương của người khác bị **ẩn hẳn** khỏi phản hồi, không trả mảng rỗng
  (mảng rỗng đọc thành "chưa có dữ liệu lương", sai hoàn toàn)
- **Cột của 7 phân hệ dạng danh sách khai đúng một chỗ** — `hr_service.SECTIONS`. Backend dùng chung một
  bộ CRUD, còn form nhập liệu ngoài giao diện dựng từ `GET /api/hr/meta`, nên thêm một cột chỉ phải sửa
  một dòng. Đánh đổi: thân request là `dict` (kiểm bằng `chuan_hoa()`, báo lỗi tiếng Việt theo đúng nhãn
  cột) nên `/docs` không mô tả được thân request của nhóm route này

---

## Phân quyền (RBAC)

| Vai trò | Mô tả |
|---|---|
| `admin` | **Quản trị viên cấp 1** — toàn quyền hệ thống, quản lý tài khoản & phân quyền nhóm. **Ngoại lệ: chỉ đọc ở Bàn giao chứng từ** |
| `admin_l2` | **Quản trị viên cấp 2** — quyền theo nhóm chức năng được gán; không thuộc phòng nào; không được tạo/sửa/xóa tài khoản cấp 1; **dùng được màn Phân quyền chức năng, trừ nhóm chứa chính mình** |
| `hau_kiem_vien` | Quyền hậu kiểm (xác nhận, gom tập, in bìa) |
| `giam_doc` | Duyệt nghỉ phép bước cuối; xem toàn bộ màn hình. **Chỉ đọc ở Bàn giao chứng từ** (xem mọi phòng) |
| `pho_giam_doc` | Duyệt thay GĐ khi có ủy quyền còn hiệu lực. **Chỉ đọc ở Bàn giao chứng từ** (xem mọi phòng) |
| `truong_phong` | Duyệt nghỉ phép bước KSV; xem + nhập bàn giao **phòng mình** nếu nhóm được cấp feature (trừ khi có quyền hậu kiểm) |
| `pho_phong` | Duyệt nghỉ phép bước KSV; xem + nhập bàn giao **phòng mình** nếu nhóm được cấp feature (trừ khi có quyền hậu kiểm) |
| `chuyen_vien` | Nhập bàn giao, xem dữ liệu phòng mình |

**Phân cấp**: `admin > admin_l2 > hau_kiem_vien > giam_doc / pho_giam_doc > truong_phong > pho_phong > chuyen_vien`

> `admin_l2` (Quản trị viên cấp 2) hiển thị chung nhóm "Quản trị viên" như cấp 1, nhưng quyền hạn được cấu hình qua **Phân quyền theo nhóm** thay vì all-access.

**Cấp 2 và màn Phân quyền chức năng** — cấp 2 thấy menu *Phân quyền chức năng* và thao tác như cấp 1
(tạo/sửa/xoá nhóm, thêm bớt thành viên, tick ma trận quyền), trừ hai đường có thể dùng để tự nâng mình
lên gần bằng cấp 1:

| Thao tác | Cấp 1 | Cấp 2 |
|---|---|---|
| Nhóm **không** chứa mình | ✔ | ✔ |
| Nhóm **có** chứa mình (sửa tên, xoá, thành viên, quyền) | ✔ | ✘ 403 — chỉ xem |
| Tự thêm mình vào một nhóm bất kỳ | ✔ | ✘ 403 |

Chặn ở backend (`groups.py::_chan_l2_tu_cap_quyen`), frontend chỉ khoá nút cho khỏi bấm rồi nhận 403.
Hai luật phải đi cùng nhau: nếu chỉ cấm sửa nhóm chứa mình thì cấp 2 lập nhóm mới full quyền rồi tự
thêm mình vào — lúc thêm, nhóm chưa chứa mình. Vẫn còn một đường **không** chặn: hai cấp 2 cấp quyền
chéo cho nhau; đó là chuyện chọn người, không phải chuyện mã.

### Menu sidebar
Menu nhóm theo **chức năng**, không theo phòng ban. Hover để mở flyout bên phải.

```
Quản lý chứng từ ─ Bàn giao chứng từ / Đóng chứng từ / Lưu trữ
Đối chiếu ──────── Phòng Thanh toán ─ Chấm 459901 / Song phương / ILO1000 / ACH / CITAD / Đối soát CITAD
                   Phòng Swift ────── Đối chiếu điện SWIFT
                   Phòng QLTK Nostro, Vostro ─ Đối chiếu CITAD - PaymentHub
                   Phòng Kế toán ──── Đối chiếu DTBB
Báo cáo ────────── Phòng KSNB & HTVH ─ Báo cáo hậu kiểm / Báo cáo bàn giao chứng từ
                   Phòng Tổng hợp ──── Báo cáo dữ liệu thanh toán
Nghỉ phép ──────── menu phẳng, không có nhóm cha
Chấm công & Lịch trực ─ Phòng Kế toán ───── Chấm công
                   Phòng Thanh toán ── Phân lịch trực / Sổ trực cuối ngày
Quản lý nhân sự ── Hồ sơ cán bộ / Tra cứu & Thống kê / Nhắc lịch
Danh sách CN TTQT ─ menu phẳng, không có nhóm cha
Tính năng khác ─── Ôn tập / Chuẩn hoá văn bản
```

Tầng "phòng" **chỉ còn ở cấp 2** của Đối chiếu, Báo cáo và Chấm công & Lịch trực, và chỉ liệt kê phòng đang thực sự có tính năng. Trước đây menu chia theo phòng ở cấp 1; cách đó buộc người dùng phải biết chức năng mình cần thuộc phòng nào mới tìm ra.

**Nghỉ phép** đứng riêng ở cấp 1 (22/08/2026), ngang hàng với *Chấm công & Lịch trực*: cả cơ quan dùng hằng ngày nên không bắt người dùng hover qua một nhóm mới tới. Nhóm *Chấm công & Lịch trực* giờ thuần các mục của riêng một phòng.

Một nhóm **chỉ hiện khi user có ít nhất 1 chức năng** bên trong (`menu.<key>`); nhóm con không còn mục nào hiển thị được cũng bị bỏ qua — không dựng mục menu hover ra rỗng. Menu phẳng cấp 1 kiểm feature giống hệt: không có `menu.ttqt_branches` thì không thấy "Danh sách CN TTQT".

**Không còn ngoại lệ nào** (03/09/2026). *Chấm công* và *Đối chiếu DTBB* trước đây gate theo **phòng** (`ACCT`) chứ không theo feature-flag, và `_dept_group()` có tham số `overrides` riêng để đè kết quả cho đúng hai khoá đó. Cả cơ chế `overrides` lẫn hàm tra mã phòng `_user_dept_code()` đã **xoá hẳn** — để lại là lời mời dựng lại đúng thứ vừa gỡ. Mọi mục ẩn/hiện theo `menu.<key>`, không có nhánh đặc biệt nào trong vòng lặp dựng menu.

> **Đổi lại: sau khi deploy phải cấp quyền tay.** Trước đây mọi nhân viên phòng Kế toán tự động có hai menu này; nay admin phải xếp họ vào nhóm có `menu.attendance` / `menu.dtbb` (và `dtbb.confirm` cho trưởng/phó phòng). Không cấp là cả phòng mất menu. Đây là đánh đổi cố ý: nhận thêm một bước lúc deploy để lấy khả năng giao việc cho người phòng khác mà không phải sửa mã. Xem mục *Phân quyền* trong `docs/DESIGN.md`.

Cây menu nằm ở `shared.MENU_TREE`. Phần tử cấp 1 là **tuple** `(key, label, icon)` cho menu phẳng, hoặc **dict** `{"id", "label", "icon", "items"}` cho nhóm. Sâu tối đa 3 tầng — `_dept_group()` không dựng được tầng thứ tư.

Trên cùng là khối **Công việc chờ xử lý**, tự ẩn khi không có việc nào. Dưới nó là **Trang chủ** — hiện với mọi vai trò và mọi vai trò đều vào được.

> **Phân quyền màn hình đi theo nhóm quyền, không theo vai trò.** Các trang Báo cáo, Lưu trữ, Báo cáo bàn giao, Nhân sự, Đóng tập chỉ kiểm `menu.<key>` — giống hệt luật mà backend (`require_feature`) và sidebar đang dùng. Trước đây các trang này còn một lớp chặn cứng theo vai trò chạy **trước** lớp nhóm quyền, khiến quyền admin cấp cho `chuyen_vien` qua nhóm không có tác dụng mà không báo gì. Lớp đó đã gỡ; chỉ `/user-management` còn giữ vì là trang duy nhất không gắn mã feature nào.

### Màn hình Phân quyền theo nhóm
Bố cục **soi gương cây menu sidebar** — admin tick quyền theo đúng thứ user sẽ nhìn thấy. Cấu trúc ở `backend/core/features.py::FEATURE_GROUPS`, hai loại thẻ phân biệt bằng khoá `kind`:

| `kind` | Hình dạng | Dùng cho |
|---|---|---|
| `group` | Thẻ có header đỏ; `sections` gom menu theo phòng (`label=None` = không cần dải nhãn) | Quản lý chứng từ, Đối chiếu, Báo cáo, Chấm công & Lịch trực, Quản lý nhân sự, Tính năng khác, Quản lý hệ thống |
| `menu` | Thẻ **không header**, chính ô tick là tiêu đề thẻ | Nghỉ phép, Danh sách CN TTQT |

Dải nhãn phòng **không phải ô tick** — luật *"mỗi ô tick là đúng một mã quyền"* được giữ nguyên, để không có hai loại ô nhìn giống nhau mà ý nghĩa khác nhau. Cạnh dải nhãn có nút **Chọn tất cả / Bỏ chọn**, chỉ tác động lên MENU chứ không tự cấp ACTION — tránh một cú bấm cấp luôn quyền chạy xử lý dữ liệu.

> ⚠️ **`FEATURE_GROUPS` phải phủ kín `FEATURES`** — `_assert_feature_coverage()` kiểm lúc import và **chặn khởi động** nếu thiếu / trùng / thừa mã. Lý do: `PUT /api/groups/{id}/features` xoá sạch quyền của nhóm rồi ghi lại đúng các ô tick đang hiển thị. Mã không được vẽ ra sẽ không nằm trong danh sách gửi lên → lần bấm **Lưu** đầu tiên xoá nó khỏi mọi nhóm, không log, không báo. Vì vậy `_render_features()` và `save_features()` trong `frontend/pages/group_features.py` **phải sửa cùng lượt** — sửa một mà quên cái kia thì quyền mất im lặng.

**Thu gọn / mở rộng**: chỉ bằng nút ở góc trên cùng bên trái. Click vào mục menu chỉ điều hướng, không đổi trạng thái sidebar. Icon nút phản ánh trạng thái hiện tại (`menu_open` khi đang mở, `menu` khi đang thu gọn). Lựa chọn được lưu trong `localStorage` và giữ nguyên khi chuyển trang.

Máy có màn hình rộng **≤ 1440px** (máy trạm 1366×768) mặc định vào đã thu gọn sẵn, nhường thêm ~184px cho vùng nội dung. Chỉ áp dụng khi user chưa từng bấm nút — đã bấm một lần thì lựa chọn đó được tôn trọng ở mọi màn hình.

### Vùng nội dung
Giao diện thiết kế cho **máy trạm desktop**, không có breakpoint mobile. Vùng nội dung rộng `calc(100% - 16rem)` (hoặc `- 4.5rem` khi sidebar thu gọn) và cho **cuộn ngang** khi bảng vượt khung — không cắt bớt nội dung.

Đầu mỗi trang hiển thị **đường dẫn menu** dẫn tới trang đó, ví dụ *Báo cáo / Phòng KSNB & HTVH / **Báo cáo hậu kiểm***. Phần cha in nhỏ màu xám, tên trang giữ cỡ tiêu đề. Đường dẫn **suy ra từ route** rồi tra bảng dựng sẵn từ chính cây menu (`shared.BREADCRUMBS`) — đổi tên một mục trong `MENU_TREE` thì breadcrumb tự đổi theo, không có chỗ thứ hai phải sửa. Trang không nằm trong menu (`/home`, `/user-management`) không hiện phần cha. Menu phẳng cấp 1 (Danh sách CN TTQT) chỉ có 1 đoạn nên cũng không hiện phần cha — nếu hiện sẽ là chính tên trang lặp lại.

> Điều kiện: route của trang phải trùng khoá menu (`@ui.page("/reports")` ↔ khoá `reports`) — ràng buộc này vốn đã có sẵn vì sidebar điều hướng bằng `ui.navigate.to(f"/{key}")`.

**Ô chọn file**: bấm vào **cả dải màu** của ô là mở hộp thoại chọn file, không cần nhắm đúng dấu `+`. Mặc định Quasar chỉ gắn `<input type="file">` vào riêng nút `+`; `ui_kit.install()` nạp một listener ở cấp `document` chuyển tiếp click từ `.q-uploader__header` sang input đó. Áp dụng cho **mọi** `ui.upload` trong dự án, kể cả ô tạo động — không phải sửa gì ở từng trang. Click rơi trúng nút thật (`.q-btn, button, label, input, a`) vẫn giữ hành vi cũ.

### Màn hình đăng nhập
Hai bên ô đăng nhập là **các cụm đường dẫn nhanh** tới hệ thống nghiệp vụ (Thanh toán trong nước / Thanh toán quốc tế / Nội bộ), click mở tab mới. Danh sách để cứng trong `frontend/pages/login.py` chứ không nằm trong DB — cố ý, để trang login **không phụ thuộc backend**: backend chết thì người dùng vẫn mở được CITAD, mail, iOffice.

Bố cục khoá bằng biến CSS (`--pc-row`, `--pc-head`, `--pc-pad`, `--pc-bd`) để các hàng trái/phải luôn ngang nhau. Khoảng cách giữa hai cụm bên phải **tính bằng Python** từ số link mỗi cụm (`_split_gap_css()`) — thêm hoặc bớt link ở cụm nào cũng tự khớp lại.

---

## Quy trình duyệt nghỉ phép

```
[Cán bộ tạo đơn]
       ↓
pending_ksv  →  (Trưởng/Phó phòng duyệt)
       ↓
pending_tong_hop  →  (Phòng TH chọn GĐ/PGĐ và chuyển lên)
       ↓
pending_gd  →  (GĐ hoặc PGĐ nếu có ủy quyền còn hiệu lực)
       ↓
approved / rejected / cancelled
```

---

## Tập số (số La Mã)

| Trường hợp | Ký hiệu |
|---|---|
| 1 tập duy nhất | I/I |
| Chia 2 tập | I/II, II/II |
| Chia 3 tập | I/III, II/III, III/III |

---

## Backup tự động

Database SQLite được backup vào `data/backups/` **mỗi lần app khởi động** và sau đó mỗi 24h.
Cấu hình trong `backend/services/backup_service.py`.

**Tiêu chí giữ lại** (hợp của hai tập, giữ cả hai):

| Giữ | Vì sao |
|---|---|
| Bản mới nhất của **mỗi ngày**, trong `_GIU_NGAY = 7` ngày gần nhất | Chiều sâu lịch sử — hỏng DB thường phát hiện muộn |
| `_GIU_GAN_NHAT = 5` bản mới nhất, bất kể ngày | Một ngày khởi động lại nhiều lần thì bản vừa chụp không bị dọn ngay |

> ⚠️ **Chỉ file đúng mẫu `ksnb_YYYYMMDD_HHMM.db` (hoặc `.zip`) mới bị xoá tự động.** Bản đặt tay
> (`ksnb_truoc_nhomA_20260728.db`…) **không bao giờ** bị đụng tới — muốn bỏ thì xoá tay.
> Trước đây luật dọn glob `ksnb_*.db` và sắp **theo tên**: `'2' < 'b' < 't'` nên bản đặt tay
> luôn bị coi là "mới nhất", vừa chiếm chỗ vĩnh viễn vừa làm màn hình Admin báo sai ngày
> backup gần nhất. `tests/test_backup_rotation.py` canh việc này.

**Thư mục backup phụ** (`BACKUP_EXTRA_DIR` trong `.env`, nên đặt ở ổ/máy khác): mỗi bản backup được
chép sang đó rồi **áp cùng luật dọn**. Tức là phần mềm chủ động xoá file trên ổ/máy ngoài — vẫn chỉ
đụng đúng mẫu tên `ksnb_YYYYMMDD_HHMM.db` / `.zip`.

> ⚠️ **Mỗi máy chủ một thư mục riêng.** Hai máy cùng trỏ vào một thư mục thì tên file không phân
> biệt được nguồn, máy này sẽ xoá bản của máy kia mà cả hai đều tưởng mình còn đủ lịch sử.

### Mã hoá bản sao lưu (`BACKUP_PASSWORD`)

Đặt `BACKUP_PASSWORD` trong `.env` thì mỗi bản sao lưu được nén thành `.zip` **mã hoá AES-256**
(mở được bằng 7-Zip/WinRAR sẵn có, không cần công cụ riêng của phần mềm), bản `.db` trần bị xoá
ngay sau đó.

Vì sao cần: file `.db` chứa **nguyên cột `pwd_hash` của toàn bộ tài khoản**. Ai đọc được thư mục
`data/backups` — hoặc share mạng `BACKUP_EXTRA_DIR` — là mang mã băm về dò ngoại tuyến, không cần
quyền gì trong phần mềm.

> ⚠️ **Mất mật khẩu này = không mở được bản sao lưu.** Cất vào két mật khẩu của đơn vị, đừng chỉ để
> trong `.env` trên đúng cái máy mà bản sao lưu dùng để cứu.

Để trống thì **vẫn backup** nhưng ra `.db` không mã hoá, kèm một dòng cảnh báo trong log mỗi lần
chạy — mất bản sao lưu nặng hơn hẳn việc bản sao lưu chưa được mã hoá, nên thiếu cấu hình không
làm dừng việc backup. `tests/test_backup_ma_hoa.py` canh cả hai nhánh.

---

## Word đòi phiên đăng nhập trên máy chủ

**Máy chủ phải có một tài khoản đang đăng nhập** (console hoặc RDP) thì việc xuất đơn nghỉ
phép bản PDF mới chạy. Chạy `start.bat` bằng tay trong phiên đó là đúng cách.

**Không** đưa hệ thống vào Windows Service, cũng không dùng Task Scheduler với tuỳ chọn
*"Run whether user is logged on or not"*. Cả hai đều chạy ở **phiên 0** — phiên không có
màn hình — và Word không làm việc được ở đó.

Đã đo trên chính máy này (chạy dưới `NT AUTHORITY\SYSTEM`, phiên 0):

| Bước | Kết quả ở phiên 0 |
|---|---|
| `New-Object -ComObject Word.Application` | ✅ tạo được, mất 0,59 s |
| `Documents.Open(...)` | ❌ trả về `null` — **không ném lỗi, chỉ trả rỗng** |
| Chuyển sang PDF | ❌ không thực hiện được |

Chỗ khó chịu là bước 1 **thành công**, nên nhìn qua tưởng Word chạy tốt. Chỉ tới lúc mở tài
liệu mới hỏng, mà lại hỏng kiểu trả `null` chứ không báo lỗi.

**Hỏng thì hệ thống không đứng lại**: API trả 503, giao diện tự lui về tải bản `.docx` và vẫn
duyệt đơn được, chỉ là không có chữ ký trên bản in. Trong log sẽ thấy nguyên văn:

> Word mo len duoc nhung KHONG mo duoc tai lieu. Thuong gap khi backend chay o phien khong co
> nguoi dang nhap...

> 💡 Máy chủ hay bị khoá màn hình hoặc mất phiên RDP: khoá màn hình **vẫn giữ phiên**, không
> sao. Nhưng *đăng xuất* (Sign out) thì mất phiên — sau khi khởi động lại máy, phải đăng nhập
> rồi chạy lại `start.bat`.

## Truy cập LAN (nhiều người dùng)

Mở firewall port 8080:

```bash
# Windows
netsh advfirewall firewall add rule name="TTTT" dir=in action=allow protocol=TCP localport=8080
```

> Chỉ cần mở 8080. Trình duyệt người dùng **không bao giờ gọi thẳng cổng 8000** — frontend
> gọi backend qua loopback trong cùng máy chủ. Mở thêm 8000 chỉ để lộ API ra mạng mà không
> được lợi ích gì; nếu không có hệ thống nào khác cần, đặt luôn `BACKEND_HOST=127.0.0.1`.

Người dùng khác truy cập: `http://[IP-máy-chủ]:8080`

Đặt trong `.env` — quên là trang liệt kê toàn bộ endpoint bị mở công khai ra mạng:

```ini
BACKEND_HOST=127.0.0.1                       # cổng backend chỉ nghe trong máy chủ
ENV=production                               # tắt /docs, /redoc, /openapi.json
```

Chỉ thêm `ALLOWED_ORIGINS=http://192.168.1.100:8080` khi thật sự phải để `BACKEND_HOST=0.0.0.0`
cho một hệ thống khác gọi thẳng API — nhiều giá trị cách nhau dấu phẩy.

Hai biến nữa có mặc định an toàn, chỉ đặt khi cần đổi:

```ini
MAX_UPLOAD_MB=200          # trần MỘT file tải lên; MAX_REQUEST_MB=600 cho cả thân request
TRUSTED_PROXY_IPS=         # máy được phép khai IP hộ qua X-Client-IP (loopback đã có sẵn)
```

> Chỉ điền `TRUSTED_PROXY_IPS` khi đặt nginx/IIS **trước cổng backend**. Máy không nằm trong danh
> sách mà gửi `X-Client-IP` thì backend bỏ qua và ghi IP thật của kết nối — nếu không, nhật ký
> truy vết có thể do chính người bị truy vết viết ra.

Backend tự **cảnh báo trong log khi khởi động** nếu đang lắng nghe trên mạng mà hai biến này chưa đặt đúng.
`deploy.bat` cũng kiểm `.env` của máy đích ở bước 1/8 và hỏi trước khi sửa, nên không phải nhớ thủ công.

---

## Lệnh thường dùng

```bash
# Cài thư viện (đúng những gì máy chính cần)
pip install -r requirements.txt

# Máy phát triển: thêm pytest (đã gồm sẵn requirements.txt)
pip install -r requirements-dev.txt

# Chạy test
python -m pytest -q

# Khởi tạo DB lần đầu
python init_db.py

# Chạy toàn bộ hệ thống
python run.py

# Chạy backend riêng (development)
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Chạy frontend riêng
python frontend/main.py
```
