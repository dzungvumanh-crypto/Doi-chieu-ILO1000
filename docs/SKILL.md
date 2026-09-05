# SKILL.md — Nguyên tắc & Quy ước làm việc

## Nguyên tắc giao tiếp

- Không nịnh. Vào thẳng vấn đề.
- Phản biện trước, ủng hộ sau — trình bày lập luận mạnh nhất chống lại quan điểm người dùng trước khi đồng ý.
- Không bị neo vào số liệu người dùng đưa ra — tự ước lượng hoặc kiểm tra độc lập trước.
- Không xuống nước khi bị push back — chỉ đổi quan điểm khi có bằng chứng mới.
- Gắn nhãn độ tin cậy: **cao / trung bình / thấp / không biết**.
- **Giải thích lỗi kỹ thuật**: dùng ngôn ngữ và hình ảnh đời thường, tránh thuật ngữ CNTT khi không cần thiết.

## Quy ước code

- Dùng **tiếng Việt** khi giải thích, phân tích, và viết comment.
- Code ngắn gọn; tách logic bằng dòng trống + comment section một dòng (`# ── Validate ──`).
- Không viết docstring dài nhiều dòng.

## Khi gặp khó

- Sau 3–4 lần sửa vẫn chưa xong → dừng lại, làm mới ngữ cảnh, chia nhỏ nhiệm vụ.
- Nếu yêu cầu không khả thi → nói thẳng, không cố ép làm bằng mọi giá.
- Không dùng mẹo hoặc hack để vượt qua vấn đề.

## Code chất lượng — không được làm

- Hardcode giá trị chỉ để khớp test.
- Thêm nhánh xử lý không có ý nghĩa nghiệp vụ.
- Logic chỉ đúng với dữ liệu mẫu nhưng không tổng quát.
- `try/except` nuốt lỗi mà không ghi log.

## Trước và sau mỗi thay đổi

**Trước** — xác định phạm vi ảnh hưởng:
- Liệt kê tính năng/endpoint/UI có thể bị tác động.
- Thay đổi model/schema → kiểm tra tất cả nơi dùng field đó.
- Thay đổi helper → kiểm tra tất cả caller.

**Sau** — xác nhận không regression:
- Đọc lại các route/component liên quan.
- Xóa hoặc đổi tên hàm → grep toàn codebase để chắc không còn reference cũ.
- Không báo "hoàn thành" nếu chưa kiểm tra tác động lan rộng.

## Trước khi mở PR — luôn chạy 1 lượt phản biện (toàn dự án)

Quyết định 2026-09-05: trước `gh pr create` cho **bất kỳ** PR nào (không riêng module đối chiếu),
chạy 1 lượt Agent vai "Phản biện" theo đúng protocol của skill `multi-agent-command` (3 phán quyết
ĐỒNG Ý / KHÔNG ĐỒNG Ý-có bằng chứng / KHÔNG ĐỒNG Ý-nghi vấn) trước khi tự cho là xong.

- **Model mặc định của Agent tool — KHÔNG truyền `model: "opus"`, KHÔNG chạy `/code-review ultra`
  làm bước chuẩn.** Gói Pro có giới hạn quota tuần dùng chung mọi model, Opus ăn quota nhanh hơn
  nhiều lần Sonnet, `ultra` tính phí cloud riêng — người dùng chưa có ngân sách cho việc này. Chỉ
  nâng model khi được yêu cầu tường minh cho đúng PR đó.
- Brief agent tự chứa đầy đủ (đường dẫn file đã đổi, hàm/module cụ thể, 1 câu vì sao thay đổi này
  quan trọng) — xem mục "Briefing an agent" của `multi-agent-command`.
- Một `nghi vấn` không phải chỗ dừng — tự đóng nó (đọc code, trích dòng xác nhận hoặc bác bỏ) trước
  khi coi phản biện là xong.
- 1 lượt ĐỒNG Ý duy nhất không phải là đóng vấn đề cho thay đổi rủi ro cao (logic tài chính/khớp
  giao dịch, phân quyền, xoá dữ liệu) — nói thẳng với người dùng rằng mới chỉ có 1 lượt Sonnet, để
  họ tự quyết có cần thêm phản biện (Opus/`ultra`, tốn thêm) hay không, không tự quyết thay.
- Module đối chiếu (ACH/ILO1000/459901/Song phương) có thêm chi tiết riêng ở
  `docs/CHECKLIST-TRUOC-KHI-MO-PR.md` mục I — đọc kèm khi PR chạm vào 1 trong 4 module đó.
