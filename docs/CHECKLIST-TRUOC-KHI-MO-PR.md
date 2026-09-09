# Checklist trước khi mở PR cho Khánh

Đúc từ toàn bộ lịch sử review thật của `khanhbq693` (khảo sát #1 → #70, 27 PR có review — 2026-09-04).
Không phải luật cố định: tick hết checklist **không** đảm bảo PR được duyệt — Khánh vẫn đọc code
thật và có thể đòi thêm điều chưa từng có ở đây. Đây chỉ là danh sách các lỗi **đã từng bị bắt lặp
lại**, dùng để tự soi trước, giảm số vòng sửa đi sửa lại. **Cập nhật thêm mỗi khi Khánh nêu yêu cầu
mới chưa có trong danh sách** — đừng để nó đứng yên rồi lại mất như bản trước.

Mỗi mục ghi: quy tắc — vì sao — PR đã từng dính. PR chỉ để tra lại ngữ cảnh, không cần đọc trước khi dùng.

---

## A. Đường dẫn file & upload

- [ ] **Không nhận `folder_path`/tên file tuỳ ý từ client rồi dùng thẳng.** Backend `Path(...)` /
  `iterdir()` / `write_bytes()` theo giá trị client gửi mà không `resolve()` + `is_relative_to(ROOT)`
  là đọc/ghi đè được bất kỳ file nào trên máy chủ. Quyết định cuối của dự án: **bỏ hẳn** chế độ
  "chọn thư mục máy chủ", chỉ còn upload từ máy người dùng. Nếu thấy code nhận đường dẫn thư mục
  server quay lại — đó gần chắc là tái phát, không phải tính năng mới hợp lệ; grep
  `Logs_update.md` xem đã có quyết định gỡ nó chưa (xem mục G8). — PR #3, #8, #19, #43, #63, #68, #70
- [ ] **Test path-traversal với cả `/` lẫn `\`.** Uvicorn giải mã `%2F` bị chặn nhưng `%5C` thì
  không; `pathlib` trên Windows coi `\` là dấu phân cách nên `Path('data/x') / '..\\..\\data'`
  thoát ra ngoài — bẫy này lặp lại 2 lần độc lập trên 2 module khác nhau. — PR #43, #63
- [ ] **Token/ID lấy từ URL dùng làm tên thư mục/file phải validate định dạng (VD UUID) trước.**
- [ ] **Filename từ client phải qua `safe_filename()`** (`backend/core/uploads.py`), không tự chế
  `os.path.basename()` — basename bỏ qua tên thiết bị Windows (`NUL`, `COM1`) và trả chuỗi rỗng khi
  input kết thúc bằng dấu phân cách (ghi đè chính thư mục). — PR #43, #54, #63, #68
- [ ] **Upload không được đọc hết vào RAM trước khi kiểm trần dung lượng.** `await f.read()` toàn
  bộ rồi mới so `total_size > MAX` là backend chết trước khi kịp từ chối file vài GB. Dùng
  `save_upload_to()` ghi theo khối (mẫu chuẩn: `backend/api/ach.py::start_job`). — PR #13, #43, #63,
  #68, #70
- [ ] **Trần dung lượng khai báo phải kẹp theo `MAX_REQUEST_BYTES`**, không phải hằng số tự đặt
  (800 MB, 1 GB) cao hơn `MAX_REQUEST_MB` mặc định (600) — `BodySizeLimitMiddleware` chặn trước ở
  600 nên thông báo lỗi in ra con số không bao giờ đạt tới được. Mẫu: `ach.py:41`. — PR #70

## B. Phân quyền (`FEATURES` / `FEATURE_GROUPS`)

- [ ] Mọi feature-code mới có trong **cả** dict `FEATURES` **và** cây phân cấp `FEATURE_GROUPS` —
  test `test_feature_codes_declared.py` quét được cả 2 lớp lẫn `require_feature(feature_code='x')`
  dạng keyword (từng có lỗ hổng bỏ sót cả hai, đã vá). — PR #68 vòng 3
- [ ] **Không đưa 1 mã vào `FEATURE_GROUPS` nếu nó không thật sự gate gì** — 1 menu gate theo
  `department_code` chứ không đọc `require_feature`/`has_feature` mà vẫn có ô tick trên màn Phân
  quyền là nói dối admin: tick vào không có tác dụng. — PR #67
- [ ] **Thêm `require_feature()` ép kiểm tra lần đầu cho 1 action vốn đã có mã nhưng chưa từng bị
  enforce → mọi nhóm hiện có mất quyền đó ngay sau deploy.** Cần migration `INSERT OR IGNORE` cấp
  bù cho nhóm đang có menu cha, **hoặc** ghi rõ vào `Logs_update.md` để vận hành cấp tay. — PR #54, #70
- [ ] **Luôn thử bằng tài khoản thường, không chỉ admin.** Admin đi qua `require_feature()` ngay
  dòng đầu nên luôn "chạy ngon" — lỗi thiếu mã quyền chỉ hiện với người không phải admin.

## C. Hiệu năng & event loop / threadpool dùng chung

- [ ] **`async def` endpoint không được gọi thẳng code đồng bộ nặng** (pandas/openpyxl/hashlib) —
  FastAPI chỉ tự đẩy sang thread khi endpoint khai `def` thường; `async def` chạy thẳng trên event
  loop duy nhất, treo cả backend cho **mọi** người dùng, không riêng người bấm nút. Cách rẻ nhất:
  đổi `async def` → `def` (tự threadpool hoá, an toàn vì `get_db()` tạo connection riêng mỗi
  request). — PR #12, #13
- [ ] Cùng lỗi áp dụng cho **frontend**: hàm băm/tính toán nặng trong `on_upload` hay handler khác
  chạy đồng bộ chặn UI của **mọi người dùng khác**, không riêng người vừa thao tác. — PR #14
- [ ] **Mọi lời gọi mạng trong code dùng chung nhiều trang** (sidebar/layout/helper) phải bọc
  `asyncio.to_thread` — không có ngoại lệ "chỉ gọi 1 lần lúc vẽ"; lúc backend khởi động lại
  (`deploy.bat`) timeout 10s treo cả frontend cho mọi người đang mở trang khác. — PR #22
- [ ] **`asyncio.gather()` cho thông tin phụ trợ/tham khảo phải `return_exceptions=True`** — API
  phụ lỗi không được phép làm chết cả trang chính (tab trắng vì 1 hàm gọi sai không tồn tại). — PR #35
- [ ] **Đo lại hiệu năng sau khi đổi cách ghi Excel**, kể cả thay đổi trông vô hại (style/format 2
  cột) — gán style object hàng vạn dòng có thể làm chậm gấp 3, chiếm slot dùng chung
  (`MAX_HEAVY_TASKS`) với các job khác. Chỉ gán đúng thuộc tính cần dùng. — PR #55
- [ ] **Không ghi SQLite (UPDATE/INSERT) mỗi request** nếu tránh được — SQLite chỉ cho 1 writer tại
  1 thời điểm cho toàn bộ file DB dùng chung; `busy_timeout=30000` khiến triệu chứng khi tắc là
  treo tới 30 giây rồi mới báo lỗi. VD: chỉ update `last_used_at` khi cách lần trước quá 1 ngưỡng
  (5 phút), không update mỗi lần. — PR #8, #11, #12

## D. Vòng lặp / polling / retry

- [ ] **Retry phải có backoff tăng dần và không retry lỗi xác định (403).** Vòng lặp thử lại vô hạn
  không delay từng tái phát 2 lần độc lập trên 2 module khi module sau **chép code** module trước
  mà thiếu đúng 2 hàng rào đã có (xem mục G3). — PR #12, #57
- [ ] **Vòng poll frontend phải có giới hạn số lần lỗi liên tiếp**, phân biệt *lỗi dứt khoát*
  (404/job mất hẳn → dừng ngay, ẩn nút Dừng) với *mất mạng tạm thời* (đếm 3 lần rồi mới dừng, giữ
  nút Dừng vì job có thể vẫn đang chạy) — và **không được nuốt `SessionExpiredError`** trong
  `except Exception`, vi phạm cả `docs/DESIGN.md` lẫn quy tắc "không nuốt lỗi không log" của
  `SKILL.md`. — PR #43, #63, #70 (PR#70 làm hơn yêu cầu, được khen)

## E. Số liệu tiền tệ / ngày tháng / dữ liệu Excel — sai âm thầm

- [ ] **Test parser số tiền phải phủ ca "để trống"/NaN**, không chỉ giá trị tường minh (`dr='0'`
  mặc định trong helper test có thể che mất bug dù 143 test vẫn xanh). Ô trống nên được chịu đựng
  tường minh, không raise làm sập cả lượt chấm — nhưng cũng không âm thầm gán 0 mà không log. Dùng
  `doc_so_tien_mem()` cho luồng "không được phép chết cả job". — PR #66, #69
- [ ] **Khi nhiều PR cùng sửa 1 file số tiền, thứ tự merge quyết định đúng/sai** — resolve conflict
  lấy nhầm bên sẽ xoá âm thầm fix vừa merge trước đó, và **test cũ vẫn xanh** vì test cũng bị lấy
  theo bản cũ. Đây là điểm bị nhắc nhiều nhất trong toàn bộ lịch sử review. — PR #66, #68, #69, #70
- [ ] **Đọc cột số tiền/mã tham chiếu từ Excel/CSV nguồn luôn ép `dtype=str`.** Không ép, pandas/
  calamine tự nâng kiểu `float64`: `'180.000'` → `180.0`, mất 3 số 0 — sai âm thầm, không lỗi
  không NaN. — PR #58, #69
- [ ] **Không `round()`/so sánh `==` trên `float`** cho số tiền — dùng `Decimal` chính xác tuyệt
  đối, tránh dư nhị phân làm "Chênh lệch" không hiện đúng 0 khi đã cân khớp. — PR #60, #61
- [ ] **Parse ngày qua helper chung có bọc lỗi**, không dùng `strptime()`/`xldate_as_tuple()` trần
  trên input tự do — ném lỗi nghiệp vụ có `filenames` để FE tô đúng file, không để lộ 500 trống
  rỗng. Validate định dạng ngay tại API trước khi ghi DB (tránh ghi được `'abc'` vào cột ngày, hỏng
  màn hình chung cho mọi người). — PR #35, #57, #67
- [ ] **Không sort theo chuỗi ngày dạng `"dd/mm/yyyy"`** (`ORDER BY` trên text) — sai thứ tự thời
  gian thực. — PR #57
- [ ] **Gán vào dict theo key trong vòng lặp group-by phải quyết định rõ: cộng dồn hay raise khi
  trùng** — không lặng lẽ ghi đè, dòng trùng biến mất không lỗi không log (kể cả ở module vốn
  "chống rất kỹ" ở chỗ khác). — PR #67

## F. Đồng bộ dữ liệu dẫn xuất (trigger, cache, nhiều nơi tính cùng 1 định nghĩa)

- [ ] **Trigger DB ghi dữ liệu dẫn xuất từ bảng có state machine nhiều bước phải xét đủ mọi đường
  thay đổi trạng thái** (insert/update/delete + mọi bước trung gian), không chỉ đường "tạo mới". Đã
  từng dính chuỗi 3-4 lỗi liên tiếp trên cùng 1 cơ chế vì chỉ xử lý 1 chiều. — PR #22
- [ ] **Khoá ngoại trỏ vào bảng bị trigger xoá cần `ON DELETE`**; cột tham chiếu phải được reset
  khi dòng bị ghi đè — thiếu là `IntegrityError` chặn thao tác hợp lệ hoặc dữ liệu kẹt vĩnh viễn. — PR #22
- [ ] **Khi sửa 1 công thức nghiệp vụ hiển thị ở nhiều màn hình, grep toàn bộ nơi định nghĩa lại
  cùng khái niệm.** Từng có 4 định nghĩa "số ngày đã nghỉ" khác nhau tồn tại song song. Nếu 2 vế
  đối chiếu dùng 2 luật parse số tiền khác nhau, dòng có số tiền ngăn-nghìn sẽ không bao giờ khớp
  `.isin()` — gắn nhãn sai dù đã thực cân khớp. — PR #3, #4, #69
- [ ] **Khi đổi code đọc 1 field từ payload dùng chung, kiểm schema thật của payload đó trước** —
  đọc field không tồn tại trong response luôn `False`/`None` âm thầm, tính năng "không bao giờ
  chạy" mà không ai biết. — PR #4

## G. Quy trình PR, merge, xác minh

- [ ] **Số liệu test trong PR/commit message phải là số chạy thật trên đúng commit head** — Khánh
  luôn tự `git fetch` + checkout + `pytest` thật, không tin số mô tả. Từng có PR chênh lệch số liệu
  tăng dần qua các lần cập nhật (thiếu 50 rồi 62 test) mà không ai phát hiện tới khi review. — PR #19,
  #63, #68
- [ ] **Trước khi đánh dấu "done" trong Implementation-notes.html, xác nhận code đã commit thật**
  (không chỉ ở working tree local) — ghi "done" mà code không tồn tại ở bất kỳ nhánh nào làm hỏng
  độ tin cậy của cả file notes cho người đọc sau. — PR #19, #68
- [ ] **Khi nhân bản 1 module làm khung cho module mới, đối chiếu với HEAD hiện tại của module
  gốc**, không phải bản tại thời điểm chép — nếu không sẽ tái lập nguyên xi các lỗi module gốc đã
  sửa rồi (từng dính 3/6 lỗi review theo đúng kiểu này). — PR #57
- [ ] **Nhánh cắt xa `develop` (100+ commit) phải rebase (không merge) lên develop mới nhất trước
  khi mở PR.** Xung đột `add/add` giữa nhánh cũ và develop: quy tắc là "lấy bản develop rồi mang
  tính năng của nhánh sang", không lấy nguyên 1 bên — lấy nhầm bên sẽ lặng lẽ revert fix bảo mật/
  nghiệp vụ vừa merge trước đó, và **test cũ vẫn xanh** vì cũng bị lấy theo bản cũ. — PR #43, #54,
  #66, #68, #69, #70
- [ ] **Không trộn thay đổi hiệu năng/refactor không liên quan vào PR tính năng đang khó review** —
  tách PR riêng, kể cả khi kết quả đo được thật và đáng kể. — PR #19, #70
- [ ] **Đổi output người dùng nhìn thấy (định dạng file, số liệu tổng, Excel→CSV...) phải có 1 dòng
  trong `Logs_update.md`**, không được nằm im trong commit không liên quan (VD gắn nhãn `perf`) —
  và cần BO xác nhận nếu đổi cả con số báo cáo. — PR #66, #70
- [ ] **Trước khi "port lại"/mang lại 1 cơ chế cũ, grep `Logs_update.md` xem có quyết định nào đã
  cố ý gỡ nó chưa** và vì lý do gì — đừng coi là chuyện kỹ thuật thuần tuý rồi tự quyết lại. — PR #43
- [ ] **Chạy `python frontend/main.py` một lần trước khi push** — bắt được `ImportError` (hàm được
  gọi nhưng chưa định nghĩa) làm chết cả frontend, kể cả trang đăng nhập, mà test qua `TestClient`
  gọi thẳng backend không phát hiện được. Kèm chạy `tests/test_frontend_api_client_calls.py` (bắt
  đúng lớp lỗi "gọi hàm client không tồn tại", VD `post_multipart` khi client chỉ có
  `post_upload`). — PR #43, #54, #63
- [ ] **Click-through UI thật trước khi báo "Ready for UX"** — test API xanh không đảm bảo nút bấm
  được trên giao diện thật.
- [ ] **Không import `backend.*` thẳng từ `frontend/*`** — kéo theo dependency nặng (pandas,
  pyzipper...) vào tiến trình frontend chỉ để dùng vài dòng logic, và tạo ra 2 bản logic không có
  gì canh đồng bộ khi 1 bên đổi luật. — PR #43

## H. Bảo mật khác (header, proxy)

- [ ] **Lọc header theo tên đã thường hoá trước khi gán, không dựa vào phép gán ghi đè dict** — HTTP
  header case-insensitive nhưng dict Python case-sensitive; `headers["X-Client-IP"] = ...` không
  xoá được `x-client-ip` client tự gửi trước đó → giả mạo được vào audit log. — PR #17
- [ ] **Route proxy/CORS chỉ mở đúng endpoint cần dùng**, không mở rộng kiểu `/api/{full_path:path}`
  — mất tác dụng lớp tường lửa production. — PR #17
- [ ] **Timeout cố định áp cho mọi endpoint qua 1 proxy dùng chung phải tính tới endpoint biết
  trước chạy lâu** (không đặt timeout thấp hơn thời gian chạy thật tối đa). — PR #17
- [ ] **Proxy không đệm toàn bộ request/response vào RAM** — chiếm RAM của tiến trình phục vụ tất
  cả người dùng, không riêng người gọi endpoint đó. — PR #17

## I. Phản biện trước khi mở PR — phần riêng cho module đối chiếu

Quy tắc chung (mọi PR, mọi module) nằm ở `docs/SKILL.md` mục "Trước khi mở PR — luôn chạy 1 lượt
phản biện" — đọc mục đó trước. Riêng 4 module đối chiếu (ACH, ILO1000, Chấm 459901, Đối chiếu Song
phương) có thêm:

- [ ] **Rủi ro cao cần nói rõ với người dùng, không tự quyết là "1 lượt Sonnet đủ rồi":** thay đổi
  động vào khoá khớp giao dịch (Map dc, Trace), thứ tự ưu tiên TT/Hủy, hoặc logic ngày-tháng/
  carryover — đúng nhóm lỗi đã dính thật (xem card 118/119 `Implementation-notes.html`: gom nhầm
  REFERENCE cheo chi nhánh, cửa sổ carryover hard-code cuối tuần).
- [ ] **Brief agent phản biện nhắc agent đọc kèm skill `bank-reconciliation`** (pitfalls đã đúc từ
  4 module này: parse số tiền, waterfall thứ tự, ambiguity, nhận diện file theo nội dung) — không
  chỉ đọc diff code, còn phải soi đúng nhóm lỗi nghiệp vụ đã lặp lại nhiều lần ở đây.

---

*Nguồn: agent khảo sát toàn bộ comment review của `khanhbq693` trên 27 PR (#1–#70) qua GraphQL,
2026-09-04. Bổ sung thêm mục A.6/B.2 từ tự đọc trực tiếp PR #68/#70/#71 (module Đối chiếu Song
phương) cùng ngày. Mục I bổ sung 2026-09-05 sau phiên sửa carryover ILO1000.*
