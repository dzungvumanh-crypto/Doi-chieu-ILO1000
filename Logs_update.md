# Logs cập nhật hệ thống

Ghi lại từng đợt push lên GitHub / deploy sang máy chính (qua `deploy.bat`). Entry mới nhất ở trên cùng.

---

- 09/09/2026 Đối chiếu Song phương — chiều ĐI - **Nhận nhiều file GL02/CSV/Excel cùng lúc, tự đọc ngày thật bên trong file; bỏ TPAY khỏi diện tính khớp; báo cáo có thêm ghi chú tự giải thích**
    + ✅ **File core đã phân loại sẵn nay nộp được cả `.xlsx`**, không chỉ `.csv`, và **nộp cùng lúc
      nhiều file của nhiều ngày khác nhau (T-1, T, T+1…) đã chạy được** — hệ thống tự mở file đọc
      cột ngày (TRDATE) để biết file nào của ngày nào, không cần đặt tên file đúng quy ước. Cùng
      cải tiến như chiều ĐẾN (PR #81, mục 09/09/2026 phía trên), áp dụng riêng cho chiều đi
    + ✅ **Trạng thái HUB "TPAY" không còn được tính là khớp với CORE nữa** — quay lại đúng văn bản
      gốc (chỉ tính "SCNL"), theo đúng xác nhận trực tiếp của Phòng nghiệp vụ. Trước đó có một đợt
      thử nghiệm tạm tính TPAY là khớp dựa trên so sánh dữ liệu thật, nay đã bỏ theo đúng chốt này
    + ✅ **File kết quả (bảng tổng hợp Hub↔Core và báo cáo tổng kết) nay có thêm sheet "GhiChu"**
      tự giải thích 2 điều hay bị hiểu nhầm là lỗi số liệu: (1) vì sao bảng tổng hợp Kênh↔Hub và
      file chi tiết CSV có số dòng khác nhau (cố ý khác phạm vi, không phải bỏ sót), và (2) ngày
      nào bị thiếu file HUB/CORE khiến thiếu nhãn đối chiếu ở ngày đó — trước đây chỉ giải thích
      được qua trao đổi trực tiếp, không có trong chính file kết quả
    + ⚠️ **Module còn 1 điểm chưa giải thích được, đã ghi nhận, chưa chặn dùng**: một số dòng CORE
      thuộc kênh Mobile Banking (giá trị nhỏ so với tổng khối lượng) chưa xác định được quy tắc
      khớp HUB tương ứng — đang chờ Phòng nghiệp vụ xác nhận thêm, xem `docs/Implementation-notes.html`
    + ✅ Cấp quyền `Chạy "Đối chiếu đi" (Kênh↔Hub + Hub↔Core)` (đã ghi ở mục 03/09/2026 bên dưới)
      không đổi gì thêm — đợt này không có quyền mới

---

- 09/09/2026 Báo cáo bàn giao chứng từ - **File Word xuất ra đã in và ký được ngay, không phải sửa tay trong Word nữa**
    + ✅ **Bảng dài tràn sang trang sau nay vẫn còn dòng tiêu đề cột** (STT, Họ và tên, Ngày giao
      dịch, Ngày nộp, Số ngày chậm, Số tờ). Trước đây sang trang là mất, người đọc phải lật ngược
      lại trang trước mới biết cột nào là cột nào
    + ✅ **Có số trang, đặt ở đầu trang, trang đầu bỏ trống** — đúng lối trình bày văn bản quen dùng
    + ✅ **Cuối báo cáo có sẵn ô ký "LẬP BẢNG" và "KIỂM SOÁT"**, chừa khoảng trống để ký tay.
      **Cố ý không in sẵn tên người ký**: người lập và người kiểm soát đổi theo kỳ, in sẵn thì tháng
      nào cũng phải sửa lại trong Word, mà sửa xong lần sau xuất ra nó lại quay về như cũ
    + ✅ **Chữ trên file gọn lại theo mẫu Phòng đã chốt**: cột thứ 5 bảng tổng hợp ghi **"Nộp chậm"**
      (trước ghi "Nộp quá hạn"); tiêu đề từng phòng chỉ còn **"1. Phòng Kế toán"** (trước kèm đuôi
      "— 7 chứng từ quá hạn")
    + ⚠️ **Chữ trên màn hình vẫn giữ như cũ** ("Nộp quá hạn", "Phòng X — N chứng từ quá hạn").
      Lần này chỉ sửa file Word xuất ra. Nên màn hình và file in ra dùng chữ khác nhau — cố ý, không
      phải sót
    + ℹ️ **Cột "Họ và tên" gộp ô theo cán bộ.** Nếu một người có nhiều chứng từ và cụm đó bị cắt
      ngang trang, các dòng nằm ở đầu trang sau sẽ **để trống tên**. Word không có cách lặp lại nội
      dung ô đã gộp sang trang mới; muốn hết hẳn thì phải bỏ gộp ô, in lại tên ở từng dòng — chờ
      Phòng quyết

- 09/09/2026 Đối chiếu Song phương — chiều ĐẾN (PR #81) - **Nhận file core Excel, và tự đọc ngày thật bên trong file thay vì đoán theo thứ tự**
    + ✅ **File core đã phân loại sẵn nay nộp được cả `.xlsx`**, không chỉ `.csv` như trước
      (yêu cầu Phòng nghiệp vụ 09/09). Cách dùng không đổi gì, chỉ là chọn thêm được loại file
    + ✅ **Nộp cùng lúc nhiều file core của nhiều ngày khác nhau (T, T+1…) đã chạy được.** Trước
      đây hệ thống buộc "file CSV chỉ dùng cho ngày T", có sẵn file của T+1 cũng không nhận —
      đó là lỗi người dùng báo ngày 08/09. Nay hệ thống **mở file ra đọc cột ngày (TRDATE)** để
      biết file nào của ngày nào, trộn lẫn `.csv` với `.xlsx` cũng được
    + ✅ **Nạp nhầm file của ngày khác nay bị chặn.** Trước đây nếu chỉ có file core của ngày
      T+1 mà bấm chạy cho ngày T, hệ thống vẫn nhận và chạy tới cùng, báo "Hoàn thành", **số
      liệu sai ngày mà không có một dòng nào báo**. Nay có dòng đỏ nói rõ file đó là ngày nào
    + ⚠️ **Có một trường hợp trước chạy được, nay sẽ dừng lại:** file core mà **bên trong chứa
      nhiều ngày** (do lúc phân loại gộp nhiều đợt zip làm một lượt). Trước đây hệ thống nhận
      file đó cho ngày T — kèm luôn cả dòng của ngày khác vào số liệu. Nay hệ thống **không
      đoán nữa**: báo lỗi và dừng bước Hub↔Core. **Cách xử lý: phân loại lại từng ngày một rồi
      nộp riêng.** Bước Kênh↔Hub vẫn chạy bình thường, không bị ảnh hưởng
    + ⚠️ **Cùng một ngày đừng nộp cả bản `.csv` lẫn `.xlsx`** — hệ thống cố ý không tự chọn hộ
      (tránh đọc nhầm bản cũ), sẽ báo lỗi yêu cầu bỏ bớt một file
    + ℹ️ **Bảng "đủ/thiếu" hiện trước khi bấm Chạy chỉ nhìn TÊN file**, chưa mở file ra xem.
      Nên vẫn có thể báo "đủ" rồi lúc chạy mới dừng vì ngày bên trong không khớp — đọc dòng log
      để biết lý do

- 09/09/2026 Báo cáo dữ liệu thanh toán (Phòng TH) - **Báo cáo lâu nay ra thiếu vài chục điện mỗi kỳ mà không ai được báo; nay hiện rõ thiếu ở đâu**
    + 🔴 **Đây là lỗi đã tồn tại từ trước, không phải lỗi mới.** Mẫu D00054 của NHNN chỉ có **195
      dòng quốc gia**, trong khi hệ thống SWIFT báo theo mã quốc tế nên còn kèm cả **vùng lãnh thổ**
      (Bermuda, quần đảo Cayman, Guam, đảo Réunion…). Nơi nào không có dòng trong mẫu thì bị bỏ khỏi
      báo cáo — **lặng lẽ**, không báo, không ghi chú. Người làm báo cáo tải file về, thấy đủ số, nộp
      đi mà không có cách nào biết
    + **Đo trên chính dữ liệu của phòng**: kỳ 202606 hụt **59 điện**, kỳ 202608 hụt **43 điện**.
      Nghĩa là mọi kỳ đã nộp từ trước tới nay đều thiếu tương tự
    + ✅ **Nay sau khi bấm "Tạo báo cáo", màn hình hiện một thẻ vàng** ghi rõ bao nhiêu nơi bị bỏ, kèm
      **bảng liệt kê từng nơi: tên, số điện đến, giá trị đến, số điện đi, giá trị đi**. Không có gì bị
      bỏ thì không hiện thẻ nào
    + ⚠️ **Thấy thẻ vàng thì kiểm lại trước khi nộp.** Con số trên báo cáo lúc đó **nhỏ hơn** file
      nguồn đúng bằng phần ghi trong bảng
    + **Số liệu trên báo cáo KHÔNG thay đổi** so với trước. Đợt này chỉ *nói ra* phần đang bị giấu,
      chưa cộng thêm gì vào báo cáo
    + **Sửa thêm một chỗ chực hỏng**: dòng tổng ở cuối file dữ liệu (dòng có ô tên nước để trống) nay
      bị loại một cách chắc chắn. Trước đây nó rơi ra do trùng hợp; file xuất tháng 6 không có dòng
      này còn tháng 8 lại có, nên nếu công cụ xuất file đổi cách ghi thì **số liệu chiều đi có thể bị
      tính gấp đôi** mà cũng không báo lỗi. Nay không còn khả năng đó
    + 🔴 **Hai việc còn chờ chốt, chưa làm**: (1) có gộp vùng lãnh thổ về nước mẹ hay không — quần đảo
      Cayman và Virgin thuộc Anh, Guam và American Samoa thuộc Mỹ, Réunion thuộc Pháp… Gộp xong thì
      tổng khớp 100%, nhưng đây là **thay đổi số nộp lên NHNN** nên phải có người quyết;
      (2) **Nam Sudan** — quốc gia độc lập từ 2011, mẫu D00054 soạn khoảng 2010 nên không có dòng,
      không gộp vào đâu được, phải hỏi NHNN
    + ✅ **Không phải làm gì sau khi cập nhật, không đổi dữ liệu, không cấp thêm quyền**

- 09/09/2026 Đối soát CITAD - **Bỏ cột "Dịch vụ", thêm cột "Số RefHub"; lệnh đã khớp nay cũng hiện RefHub**
    + **Cột "Dịch vụ" đã bỏ khỏi báo cáo** — cả file Excel xuất ra lẫn bảng "Kết quả" trên màn hình.
      Nội dung cột đó đọc thẳng được từ cột **Loại GD** ngay bên cạnh: IH là chuyển giá trị cao, IL
      là chuyển giá trị thấp. Số liệu bên trong **không bị xoá**, chỉ thôi hiện ra
    + **Thêm cột "Số RefHub"** — mã tham chiếu vốn đã nằm sẵn trong file IPCAS nhưng từ trước tới nay
      chưa bao giờ được đưa ra báo cáo. Cột này nằm **cuối nhóm AGRIBANK (IPCAS)**, không nằm chỗ cũ
      của "Dịch vụ", vì đó là số liệu của Agribank chứ không phải của CITAD
    + **Trước đây chỉ dòng chưa khớp mới có RefHub, lệnh đã khớp thì trống trơn.** Nay mọi lệnh có
      RefHub đều hiện đủ
    + **Lệnh Đi mà IPCAS báo "đã sang kênh" nhưng chưa ghi ngày kênh trả**: vẫn rơi vào nhóm
      **Chỉ CITAD** như quy tắc 28/08/2026, nhưng nay **kèm theo số RefHub** để tra cứu bên Agribank.
      Trước đây dòng này bị bỏ ngay từ lúc đọc file nên mất luôn số RefHub, người chấm không có gì
      trong tay để tra
    + ⚠️ **Con số "tổng dòng IPCAS" trong tab Lịch sử nay lớn hơn trước với cùng một file** — vì
      trước đây nó đếm thiếu đúng nhóm dòng nói trên. Đây là sửa đúng, không phải dữ liệu thay đổi.
      Hệ quả: **không so sánh trực tiếp con số này với các lượt chấm trước ngày 09/09/2026**
    + 🔴 **Còn một chỗ chưa xong**: dòng thuộc nhóm **Lệch trạng thái** vẫn để trống cột Số RefHub,
      dù bên IPCAS có sẵn giá trị đó — trong khi đây đúng là nhóm cần tra cứu nhất. Sẽ vá riêng
    + 🔴 **Vẫn giữ điểm mù cũ**: lệnh IPCAS báo đã đi kênh mà CITAD **không hề có** thì dòng vẫn
      không hiện ra báo cáo. Đang chờ Phòng Thanh toán chốt, vì cho hiện sẽ làm số dòng lệch tăng
    + ✅ **Không phải làm gì sau khi cập nhật, không đổi dữ liệu, không cấp thêm quyền**

- 08/09/2026 Chuẩn hoá văn bản - **Rà soát lại trên hai văn bản thật — sửa 8 chỗ, khối chữ ký và Nơi nhận**
    + **Khối "Nơi nhận" gõ bằng nút chấm tròn của Word thì không được sửa gì cả.** Dấu chấm tròn đó
      do Word **tự vẽ**, nó không nằm trong chữ nên phần mềm đọc dòng "Như trên;" mà không thấy dấu
      gạch đầu dòng nào — và luật nhận khối Nơi nhận lại đi tìm đúng dấu gạch ấy. Cả khối bị bỏ qua:
      không về cỡ 11, không căn trái, không giãn dòng đơn. Nay phần mềm đổi chấm tròn thành gạch
      đầu dòng **trước** khi đọc, nên khối được nhận như văn bản gõ tay
    + ⚠️ **Nếu bỏ tick ô "Chuyển danh sách chấm tròn tự động…"** trong tab Cấu hình thì lỗi trên
      quay lại. Nên để nguyên ô đó
    + **Tên người ký bị bỏ sót khi ký thay.** Khối chữ ký kiểu "TL. TỔNG GIÁM ĐỐC" rồi
      "GIÁM ĐỐC TRUNG TÂM THANH TOÁN": phần mềm tưởng dòng thứ hai là **tên người**, nên tên thật ở
      dưới khoảng chừa chữ ký không còn ai nhận — giữ nguyên cỡ chữ, không in đậm, không canh giữa.
      Nay hai dòng chức vụ được hiểu đúng là chức vụ, tên người lấy ở dòng dưới
    + **"TRƯỞNG NHÓM" nay được nhận là chức vụ.** Trước đây danh sách chỉ có Trưởng phòng, Trưởng
      ban, Trưởng đơn vị, Trưởng bộ phận — thiếu "Trưởng nhóm" nên cả khối chữ ký của một Báo cáo
      không được áp thể thức. Nay mọi chức danh có chữ "Trưởng" đều được nhận
    + **Tiêu ngữ "Độc lập - Tự do - Hạnh Phúc"** (chữ P hoa) nay được sửa về "Hạnh phúc". Cách bỏ
      dấu ("Hoà" hay "Hòa") vẫn **không** bị đụng tới — đó là thói quen của từng đơn vị
    + **Dòng gõ phím Tab để thụt đầu dòng nay bị thụt gấp đôi.** Phần mềm đã tự đặt thụt 1 cm mà
      dấu Tab vẫn nằm đó. Nay Tab ở **đầu dòng** được bỏ; Tab **giữa dòng** (dùng canh cột, kiểu
      "- Swift Code &nbsp;&nbsp;: VBAAVNVX330") vẫn giữ nguyên
    + **"TL.TỔNG GIÁM ĐỐC" gõ dính** nay được thêm dấu cách thành "TL. TỔNG GIÁM ĐỐC". Áp cho cả
      TM. / KT. / TL. / TUQ. / Q.
    + **Dòng "V/v ..." của công văn dài quá phải xuống dòng thì nửa dưới bị trình bày như câu văn
      thường** — nửa trên cỡ 12 canh giữa, nửa dưới cỡ 14 căn đều hai bên. Nay cả hai dòng cùng
      được hiểu là trích yếu
    + **Thêm ô "Lề trái đoạn" vào tab Cấu hình quy chuẩn.** Thông số này vốn vẫn được áp lên văn bản
      (nó kéo lời văn về sát lề) nhưng **không có ô nào trên màn hình** — người dùng không nhìn thấy
      và không tắt được. Ô "Thụt dòng đầu" nay cũng xoá trống được: để trống = không đụng tới
    + ✅ **Không phải làm gì sau khi cập nhật, không đổi dữ liệu, không cấp thêm quyền**

- 08/09/2026 Chuẩn hoá văn bản - **Số tự động không còn bị teo, số trang không còn bị đánh đè**
    + **Số thứ tự "4." "5." "I." "II." in ra bé bằng nửa chữ.** Nguyên nhân: những số đó do Word
      **tự sinh** khi hiển thị, cỡ chữ của chúng nằm ở một chỗ khác hẳn cỡ chữ của câu văn nên
      phần mềm sửa câu văn mà không chạm tới số. Nay số ăn theo đúng cỡ chữ của đoạn
    + **Số trang bị đánh đè thành hai con số.** Trước đây phần mềm chỉ nhìn ở **đầu trang** xem đã
      có số chưa; văn bản nào đánh số ở **chân trang** (hoặc chỉ ở trang đầu) thì bị đánh thêm một
      lần nữa. Nay soi đủ **sáu chỗ** đầu/chân trang trước khi quyết định
    + **Dòng "Kính trình:" của Tờ trình** trước đây không được nhận ra (phần mềm chỉ biết "Kính
      gửi"), nên bị áp thể thức của câu văn thường. Nay nhận như "Kính gửi" — Mẫu 16 Phụ lục V
      (Phiếu trình chuyển) dùng đúng chữ này
    + **Khối "Kính trình" dựng bằng bảng nay vẫn được áp thể thức.** Nhiều người đặt "Kính trình:"
      và tên người nhận vào hai ô của một bảng cho dễ canh. Trước đây ô thứ hai bị coi là ô bảng
      số liệu nên giữ nguyên cỡ chữ gốc — nửa dòng cỡ 14, nửa dòng cỡ 11. Nay mọi ô **cùng bảng đó**
      đều theo thể thức của khối
    + ⚠️ **Bảng số liệu thật vẫn không bị đụng tới** — kể cả khi nằm ngay sát bên dưới khối Kính
      trình, vì phần mềm phân biệt theo **từng cái bảng** chứ không theo ô đứng cạnh nhau
    + ✅ **Không phải làm gì sau khi cập nhật**

- 07/09/2026 Chuẩn hoá văn bản - **Tên đơn vị ban hành dài 2 dòng không còn bị bỏ đậm nửa trên**
    + Khối đầu văn bản kiểu **"BAN TRIỂN KHAI GP QLRR HOẠT ĐỘNG"** rồi **"TỔ TRIỂN KHAI NGHIỆP VỤ"**
      — cả hai dòng cùng thuộc tên đơn vị ban hành nên phải in đậm cả hai. Trước đây phần mềm chỉ
      để đậm dòng cuối, dòng trên bị bỏ đậm
    + Nay phần mềm **đọc chính chữ đậm người soạn đã đặt** để biết dòng nào thuộc tên đơn vị ban
      hành, dòng nào là đơn vị cấp trên — thay vì đoán theo con chữ. Người soạn bôi đậm đúng chỗ
      thì phần mềm giữ đúng chỗ đó
    + Không đụng tới khối mà **cả khối cùng đậm** hoặc **cả khối cùng không đậm** — khi đó người
      soạn không phân biệt hai vai, phần mềm quay về cách cũ
    + ✅ **Không phải làm gì sau khi cập nhật**

- 07/09/2026 Chuẩn hoá văn bản - **Mục con của gạch đầu dòng nay trình bày khác mục cha**
    + **Việc đã sai:** dòng gạch đầu dòng nào người soạn **tự thụt vào cho sâu hơn** để thể hiện
      mục con thì phần mềm lại kéo thẳng về lề cũ — mục con nằm ngang hàng với chính mục cha của
      nó, đọc ra thành các mục ngang cấp. Nay giữ nguyên mức thụt người soạn đã đặt (đoạn lời văn
      thường bị thụt vô cớ thì vẫn dọn về lề như cũ)
    + **Việc mới làm:** phần mềm **tự nhận ra mục con** cả khi người soạn không thụt lề gì cả.
      Dòng gạch đầu dòng kết thúc bằng dấu **hai chấm ":"** thì các dòng gạch đầu dòng ngay dưới là
      mục con của nó — được đổi dấu thành **"+"** và thụt vào thêm 1 cm
    + Danh sách con **kết thúc** ở dòng có dấu **chấm** cuối câu (theo đúng quy ước "cuối mỗi dòng
      dấu chấm phẩy, dòng cuối cùng dấu chấm"), hoặc ở dòng đầu tiên không phải gạch đầu dòng
    + ⚠️ **Đây là thói quen trình bày, không phải quy định.** QĐ 979 chỉ đánh số tới cấp *điểm*
      (a, b, c), dưới đó không nói gì. Nếu văn bản của phòng có quy ước khác thì vào tab **Cấu hình
      quy chuẩn** đổi ký tự mục con, đổi mức thụt, hoặc bỏ tick ô *"Tự nhận mục con"*
    + ⚠️ **Chỗ phần mềm có thể nhận nhầm:** một mục **ngang cấp** đứng ngay sau danh sách con mà
      không có dòng nào chen giữa và danh sách con không dùng dấu chấm phẩy — nó sẽ bị tụt xuống
      làm mục con. Mọi dòng bị đổi đều **bôi màu trong nhật ký**, xem lại rồi tải mới chắc
    + **Danh sách Nơi nhận và Kính gửi không bị đụng tới** — hai khối đó cũng dùng "-" nhưng là
      danh sách phẳng
    + ✅ **Không phải cấp quyền gì thêm, không đổi dữ liệu**

- 08/09/2026 Đối chiếu CITAD (Phòng Thanh toán) - **Cho phép 1 người có nhiều bảng đối chiếu độc lập trong cùng 1 ngày**
    + Trước đây mỗi người chỉ được **đúng 1 bảng/ngày**. Nay bấm "Tải" một bảng đã lưu để sửa/lưu
      tiếp tại chỗ như cũ, còn **gõ ngày rồi Lưu mà KHÔNG bấm "Tải"** thì luôn sinh ra **1 bảng
      mới hoàn toàn tách biệt** — kể cả sau khi một bảng cũ đã "Lưu bảng cuối" rồi chấm lại
    + Tab **Lịch sử** dựng lại thành **3 tầng**: người lập bảng → từng bảng độc lập của người đó
      → từng lần lưu trong bảng đó. Bảng chỉ có 1 lần lưu hiện gộp thẳng 1 dòng, có nút Tải/Ai đã
      sửa ngay, không phải bấm mở rộng thêm 1 lần chỉ để thấy lại đúng thông tin đã có
    + Có dòng ngăn cách khi danh sách Lịch sử sang tháng khác
    + ⚠️ **Đổi ô ngày sau khi đã "Tải" một bảng** sẽ tự tách khỏi bảng đó — báo rõ "lưu tiếp theo
      sẽ tạo bảng MỚI", để không lưu nhầm đè lên bảng vừa tải. Nếu đang xem bảng của người khác
      (chỉ góp Napas/PSS-MDP) mà quên bấm Tải bảng của họ trước khi Lưu thì hệ thống cũng chặn
      đúng cách tương tự, không ghi đè nhầm số liệu người khác
    + 🔎 Gõ đúng 1 ngày đã có sẵn bảng của mình (kể cả mở lại hôm sau, hoặc F5 giữa chừng) sẽ hiện
      banner nhắc **"Bạn đã có N bảng cho ngày này"** kèm nút tải nhanh bảng gần nhất — chỉ nhắc,
      không chặn tạo bảng mới nếu không bấm vào
    + ✅ **Không phải làm gì sau khi cập nhật** — không đổi công thức tính chênh lệch, không đổi
      cách xuất Excel, không đổi quyền. Dữ liệu cũ giữ nguyên khi hệ thống tự cập nhật cấu trúc

- 06/09/2026 Nghỉ phép - **Rà soát toàn bộ đợt sửa "Khác"/điều chỉnh NPBB — sửa 2 lỗi hiện chữ hướng dẫn sai loại nghỉ**
    + Giao agent rà soát riêng toàn bộ code mới của 2 đợt trước (loại "Khác" tự chọn tính hạn mức,
      chặn điều chỉnh NPBB xếp chuỗi) — xác nhận toàn bộ 5 câu SQL + các điểm chặn/khôi phục đơn gốc
      đều đúng, không sót chỗ nào cần sửa
    + ✅ **Phát hiện + sửa**: dòng chữ hướng dẫn (vd "Tối thiểu 5 ngày làm việc") ở dialog "Tạo đơn"
      và "Sửa & Nộp lại/Điều chỉnh NPBB" bị kẹt hiện theo loại nghỉ đã chọn ở LẦN MỞ DIALOG TRƯỚC —
      do gán `.value` bằng code không tự kích hoạt sự kiện đổi loại nghỉ (chỉ kích hoạt khi người
      dùng tự tay bấm dropdown). Gọi tường minh lại hàm cập nhật hướng dẫn mỗi lần mở dialog — cùng
      cách đã áp dụng đúng cho nút gạt "Trừ vào hạn mức phép năm" ở đợt trước
    + Verify: chạy lại 135 test liên quan nghỉ phép/hạn mức/chấm công/bàn giao — pass đủ; bấm thử
      qua Playwright cả 2 dialog sau khi sửa — hiện đúng hướng dẫn theo loại nghỉ mỗi lần mở

- 06/09/2026 Nghỉ phép - **Điều chỉnh NPBB: chặn xếp chuỗi nhiều cấp, đơn gốc tự khôi phục khi rút đơn điều chỉnh**
    + Phát hiện qua rà soát thực tế (tạo đơn điều chỉnh cấp 2 thật rồi kiểm tra báo cáo): điều chỉnh
      1 đơn *vốn đã là đơn điều chỉnh* (chuỗi gốc → điều chỉnh 1 → điều chỉnh 2) khiến nhân sự đó
      **biến mất hoàn toàn khỏi báo cáo NPBB** ở Báo cáo tổng hợp — báo cáo chỉ dò đúng 1 cấp cha-con
      để tìm đơn điều chỉnh còn hiệu lực, không theo được chuỗi 2 cấp trở lên
    + ✅ **Chặn hẳn điều chỉnh chồng lên điều chỉnh** — mọi đơn điều chỉnh giờ luôn trỏ thẳng về đúng
      1 đơn NPBB GỐC duy nhất, không xếp chuỗi. Nút "Điều chỉnh ngày NPBB" ẩn trên chính đơn điều
      chỉnh; ô tìm-chọn đơn ở dialog "Tạo đơn" cũng lọc bỏ, chỉ liệt kê đúng đơn gốc
    + ✅ **Đơn gốc tự khôi phục "Hoàn thành"** khi đơn điều chỉnh (đã duyệt) bị rút/hủy — trước đây
      đơn gốc kẹt "Đã hủy" vĩnh viễn, không thể điều chỉnh lại được nữa dù đơn điều chỉnh đã bị rút.
      Áp dụng cho cả 2 đường rút đơn: "Hủy đơn" trực tiếp lẫn "Rút đơn" cần Phòng Tổng hợp xác nhận
    + Từ nay: muốn điều chỉnh lại 1 đơn NPBB đã có đơn điều chỉnh, phải rút/hủy đơn điều chỉnh hiện
      tại trước — đơn gốc tự về "Hoàn thành", làm điều chỉnh mới lại từ đơn gốc đó. Số lần điều chỉnh
      không giới hạn, miễn tuần tự từng lần một
    + Verify thật qua API (tạo đơn điều chỉnh cấp 2, rút đơn qua cả 2 đường, dọn sạch sau khi xong):
      chặn đúng lúc điều chỉnh chồng lên điều chỉnh; đơn gốc khôi phục đúng sau khi rút; điều chỉnh
      lại thành công sau khi khôi phục. 135 test liên quan pass đủ

- 06/09/2026 Nghỉ phép - **Loại nghỉ "Khác": tự chọn có tính vào hạn mức phép năm hay không**
    + Trước đây `leave_type="other"` (Khác) LUÔN trừ vào hạn mức phép năm giống hệt "Nghỉ phép năm"
      — không đúng cho mọi lý do "Khác" (hộp lý do tự do, có thể là loại nghỉ theo luật lao động
      không tính vào phép năm). Thêm 1 nút gạt "Trừ vào hạn mức phép năm" (kèm dòng giải thích rõ 2
      chiều) — chỉ hiện khi chọn loại "Khác", ở cả 3 nơi tạo đơn: Tạo đơn, Sửa & Nộp lại, Khai báo hộ
    + **Bật (mặc định, giữ nguyên hành vi cũ)**: tính đúng như đơn Nghỉ phép năm — trừ hạn mức còn
      lại, cộng vào số ngày đã nghỉ, có thể phải ứng phép năm sau nếu vượt hạn mức
    + **Tắt**: chỉ ghi nhận ngày nghỉ để theo dõi, không tính toán gì vào hạn mức phép năm — giống
      hệt các loại đã miễn hạn mức sẵn có (thai sản/bảo hiểm/không lương/họp-công tác)
    + Verify thật qua API (tạo/xoá/nộp lại đơn thật, dọn sạch sau khi xong): "Khác" tắt trừ hạn mức
      tạo được dù vượt xa hạn mức (30 ngày trên hạn mức 12), không đổi `used_leave_days`/báo cáo năm;
      "Khác" bật trừ hạn mức tính đúng y hệt phép năm (used_days/remaining/báo cáo năm); nộp lại đơn
      đổi từ bật sang tắt cập nhật đúng trong DB; xoá đơn khai báo hộ loại "Khác tắt" không hoàn
      nhầm hạn mức (vì bản thân nó chưa từng bị trừ)

- 06/09/2026 Nghỉ phép - **Sửa 5 lỗi từ review thật của Người 1 trên PR #77**
    + ✅ **"Họp/Công tác" chấm công tự động thành 0 công thay vì đủ công** — 2 trigger đồng bộ
      `attendances` (tạo từ PR #22, trước khi loại nghỉ `hop_cong_tac` ra đời) rơi đúng loại này vào
      `ELSE 'P'` (0 công) thay vì dùng ký hiệu `CT` = "Công tác" (1 công) đã có sẵn trong
      `attendance_symbols` nhưng chưa trigger nào dùng. Thêm migration cho cả 2 trigger. Xem
      [Implementation Notes #122](docs/Implementation-notes.html)
    + ✅ **Ký hiệu `H` đụng độ giữa báo cáo chấm công mới và hệ chấm công thật** — đổi
      `hop_cong_tac` sang dùng chung `CT` với hệ chấm công thật thay vì tự đặt `H` (đã có nghĩa khác
      là "Đi học"). Xem #122
    + ✅ **Báo cáo NPBB mất hẳn đường tải nếu bản xem trước PDF lỗi** (Word chưa cài/treo trên máy
      chủ) — trước đây dừng luôn ở bước báo lỗi; giờ tự động tải thẳng file .docx gốc (không phụ
      thuộc Word) làm phương án dự phòng, khớp đúng cách phiếu nghỉ phép đã xử lý PDF hỏng. Xem #122
    + ✅ **Cột "Còn lại" trong báo cáo tổng hợp năm ra số âm sau 31/03** — phép chuyển kỳ hết hạn bị
      trừ về 0 nhưng số ngày đã nghỉ (gồm cả phần từng dùng phép chuyển kỳ) không trừ theo, có thể ra
      âm. Kẹp về 0, khớp đúng cách 2 màn hình khác đang làm. Xem #122
    + ✅ **Mốc hết hạn 31/03 tính theo ngày bấm nộp đơn thay vì ngày nghỉ thật** — fix đợt trước
      (#121) bỏ hard-code nhưng lại mặc định dùng "hôm nay" (ngày nộp đơn); quy định thật nói về
      ngày NGHỈ phải rơi trước 31/03, không phải ngày nộp. Đổi sang truyền đúng ngày bắt đầu nghỉ.
      Xem #122
    + *Toàn bộ 5 lỗi verify bằng dữ liệu thật (không đoán từ đọc code) trước/sau cho từng lỗi, dọn
      sạch dữ liệu test sau khi xong — xem #122*

- 06/09/2026 Bàn giao chứng từ - **Cột ngày nghỉ lễ tô vàng như hai ngày cuối tuần**
    + Trước đây bảng nhập chứng từ chỉ tô vàng **thứ Bảy và Chủ nhật**. Ngày nghỉ lễ giữa tuần
      trông y hệt ngày đi làm, không có gì nhắc người nhập rằng hôm đó lẽ ra không có chứng từ
    + Nay ngày lễ tô vàng **giống hệt cuối tuần** — cả ô số ngày trên đầu bảng lẫn ô trống bên dưới
    + Danh sách ngày lễ lấy từ **cùng một chỗ** với màn Nghỉ phép và Sổ trực (ngày lễ khai ở
      *Nghỉ phép → Ngày lễ* và *Phân lịch trực → Ngày đặc biệt*) — khai một lần, cả ba màn hình
      hiểu giống nhau. Không phải khai riêng cho màn chứng từ
    + Ô **đã có số** vẫn giữ màu theo trạng thái (xanh = đã chốt, cam = chờ xác nhận, tím = đang
      mượn). Chứng từ phát sinh đúng ngày lễ là chuyện có thật, trạng thái quan trọng hơn màu ngày nghỉ
    + ⚠️ **Thứ Bảy đi làm bù vẫn tô vàng** — chưa đổi ở màn này. Bảng chấm công thì đã bỏ vàng cho
      ngày làm bù, vì ở đó cột Tổng có cộng công của hôm ấy nên để vàng là mâu thuẫn nhìn thấy được

- 05/09/2026 Nghỉ phép - **Sửa hết 5 cảnh báo còn treo của 2 đợt trước + thêm loạt báo cáo/phiếu in + rà soát tìm thêm 2 lỗi quyền/khoá**
    + ✅ **Đã sửa "Báo cáo NPBB liệt kê nhầm gần như toàn bộ nhân sự"** (cảnh báo ở mục dưới) — nguyên
      nhân là 1 lỗi SQL rộng hơn nhiều so với tưởng ban đầu: mọi danh sách/báo cáo đơn nghỉ phép đều
      **âm thầm bỏ sót đơn thật không nhập lý do** (không riêng gì báo cáo NPBB). Xem chi tiết ở
      [Implementation Notes #119](docs/Implementation-notes.html)
    + ✅ **Đã sửa "Số Đã nghỉ hiển thị lớn hơn thực tế"** (cảnh báo ở mục dưới) — tab Hạn mức phép/số
      "Phép còn lại"/xuất Excel hạn mức trước đây đếm trùng đơn gốc **và** đơn điều chỉnh NPBB cùng
      lúc trong thời gian đơn điều chỉnh còn chờ duyệt. Xem #119
    + ✅ **Đã sửa "Đơn nghỉ vắt qua Tết dương lịch có ứng phép bị đếm thiếu ngày"** (cảnh báo ở đợt
      "Ứng phép năm sau" bên dưới) — trừ nhầm số ngày đã ứng ở cả 2 năm thay vì đúng 1 năm gốc. Xem #119
    + ✅ **Đã sửa "Ngày phép chuyển kỳ chưa hết hạn 31/03 như quy định"** (cảnh báo ở đợt "Ứng phép
      năm sau" bên dưới) — mốc so sánh hạn 31/03 bị hard-code cứng thành 01/01 nên phép chuyển kỳ
      **không bao giờ hết hạn thật sự**; đơn nghỉ tạo tháng 6, tháng 10 vẫn cộng thêm ngày chuyển
      năm. Xem #121
    + ✅ **Đã sửa "Nộp lại đơn bị từ chối mà vượt hạn mức thì chưa hỏi ứng phép"** (cảnh báo ở đợt
      "Ứng phép năm sau" bên dưới) — backend vốn đã hỗ trợ sẵn, chỉ riêng màn "Sửa & Nộp lại" chưa
      bắt tín hiệu để hỏi, nên vượt hạn mức là báo lỗi rồi dừng luôn. Xem #121
    + **Rà soát thêm phát hiện 2 lỗi quyền/khoá không liên quan tới hạn mức**: nút "Hủy đơn" bị ẩn
      nhầm cho đơn đang chờ duyệt ở tài khoản chưa được cấp quyền riêng; nút Phê duyệt/Từ chối của
      Phó Giám đốc vẫn hiện dù giấy uỷ quyền đã hết hạn. Toàn bộ 7 lỗi (5 ở trên + 2 lỗi này) đã
      sửa, verify bằng dữ liệu thật trước/sau cho từng lỗi — xem #119, #120, #121
    + **Thêm 2 loại nghỉ mới**: *Nghỉ không lương* và *Họp/Công tác* — đi qua đúng quy trình duyệt
      (KSV → Tổng hợp → Giám đốc) như đơn thường, nhưng **không trừ vào hạn mức phép năm** (vẫn hiện
      trong chấm công/báo cáo để theo dõi). Họp/Công tác cho chọn lẻ từng ngày (giống phép năm) thay
      vì chọn khoảng liên tục
    + **Điều chỉnh nghỉ phép bắt buộc giờ có thêm lối tạo trực tiếp** từ nút "Tạo đơn" (trước đây chỉ
      tạo được từ nút "Điều chỉnh ngày NPBB" trong chi tiết 1 đơn cụ thể) — chọn loại "Điều chỉnh
      nghỉ phép bắt buộc", tìm và chọn đơn gốc cần đổi ngày, sau đó vào đúng màn nhập ngày mới +
      chọn KSV/Ban lãnh đạo phê duyệt như luồng cũ. Chi tiết đơn (cả gốc lẫn điều chỉnh) có link bấm
      mở tab mới sang đơn liên quan
    + **Báo cáo chấm công tháng** (theo đúng mẫu TCNS): chọn 1 tháng hoặc "Chọn cả năm" (dừng đúng ở
      tháng hiện tại nếu đang xem năm nay, không sinh sheet tương lai); ký hiệu P/BB/H theo đúng loại
      nghỉ; dữ liệu quét lại thật mỗi lần xuất, không cache
    + **Báo cáo nghỉ phép năm viết lại theo đúng mẫu giấy thật**: nhóm theo phòng ban (dòng tổng
      trước, chi tiết từng người sau), cột "Đã nghỉ" tính đến đúng thời điểm bấm xuất file
    + **Tải phiếu nghỉ phép**: cho chọn PDF (có chữ ký, mặc định) hoặc Word (không có chữ ký — ghi rõ
      trên nút để không nhầm là bản tương đương); PDF mở xem trước toàn màn hình trước khi tải, có
      nút "Tải xuống"/"Đóng" riêng thay vì tải thẳng
    + **Bảng danh sách đơn nghỉ phép**: sắp lại thứ tự cột (Họ và tên/Phòng lên ngay sau Ngày tạo),
      kéo dãn được từng cột bằng chuột, khung viền đậm rõ hơn; thêm bộ lọc theo "Ngày tạo" (chọn 1
      ngày) và ô "Tìm theo tên" giờ gõ ra danh sách nhân sự thật để bấm chọn (tự cập nhật theo danh
      sách nhân sự hiện tại, không phải gõ mù)
    + **Popup nhắc đơn quá hạn chưa duyệt**: đơn của chính mình đã tới/qua ngày nghỉ mà vẫn còn
      "chờ duyệt" sẽ tự nhắc khi mở trang, ghi rõ đang kẹt ở cấp nào
    + *Lưu ý vận hành*: nhóm quyền "QA-all" (tài khoản test nội bộ) thiếu sẵn quyền "Hủy đơn nghỉ
      phép"/"Rút đơn nhiều cấp" — đã cấp bổ sung; nếu nhóm quyền khác của đơn vị cũng thiếu 2 quyền
      này thì cấp thêm tương tự qua màn Quản lý nhóm quyền

- 05/09/2026 Đối chiếu CITAD - **Nhiều người cùng chấm một ngày, khoá nguồn Napas/PSS-MDP, tách bảng chênh lệch VNĐ / Ngoại tệ**
    + **Hết cảnh "một ngày chỉ một người chấm được".** Trước đây một ngày chỉ có đúng một bảng
      dùng chung cả phòng: người thứ hai vào chấm cùng ngày thì bị chặn, hoặc phải sửa đè lên
      bảng người thứ nhất đã lập. Nay **mỗi người tự lập bảng riêng của mình** cho cùng một ngày,
      không ai đụng vào bảng ai
    + Tab **Lịch sử** vì thế có thể hiện **nhiều dòng cho cùng một ngày** — mỗi dòng là bảng của
      một người, kèm nhãn **Chính thức** (đã Lưu bảng cuối) hay **Tạm**
    + **Vào bảng tạm của người khác vẫn chỉ bổ sung được Napas/PSS-MDP** như trước, không sửa
      được ô nào khác và không chốt bản cuối hộ được
    + **Hai ô Napas / PSS - MDP không gõ tay được nữa** — chỉ nạp bằng nút *"Nạp CITAD"*, giống
      hệt 5 cổng CITAD và PaymentHub. Nếu quét ở trang PaymentHub, phần mềm sẽ **bỏ qua** hai mục
      này và báo *"Lệnh quyết toán lô bắt buộc phải quét dữ liệu từ cổng Citad"* — **đây không
      phải lỗi phần mềm**, chỉ là quét nhầm trang. **Không cần cài lại Extension**, Extension
      không thay đổi gì
    + **Ba bảng chênh lệch thay vì một:** bảng *Gộp* cả 3 loại tiền như cũ, thêm bảng **VNĐ**
      riêng và bảng **Ngoại tệ** (USD + EUR chung một bảng). Nhìn là biết ngay lệch nằm ở nhóm
      tiền nào, không phải đọc dòng ghi chú nhỏ cuối trang. **File Excel xuất ra không đổi**
    + ⚠️ **Sổ trực cuối ngày đọc "đã khớp" theo bất kỳ bảng nào của ngày đó.** Một ngày giờ có
      nhiều bảng, nên nếu người A chốt bảng khớp mà người B chốt bảng còn lệch thì Sổ trực
      **vẫn báo đã khớp**, không cảnh báo gì. Cảnh báo này xưa nay chỉ là nhắc phụ trợ và không
      chặn ai bấm xác nhận — nhưng cần biết để đừng tin nó thay cho việc tự kiểm
    + Sửa lỗi phát hiện lúc soát: bấm **Xoá** một bảng tạm từng xoá theo luôn toàn bộ lịch sử của
      bảng đó (mất dấu vết ai đã chấm gì lúc nào); và người đang bổ sung Napas vào bảng người
      khác, sau khi bấm Lưu thì màn hình lặng lẽ chuyển sang chế độ "làm bảng mới" trong khi số
      liệu của người kia vẫn còn trên màn hình — bấm Lưu lần nữa sẽ đẻ ra một bảng thừa

- 05/09/2026 Nghỉ phép - **Ứng phép năm sau khi hết hạn mức, trưởng/phó phòng duyệt thay nhau, báo cáo chấm công tháng**
    + **Hết ngày phép vẫn xin nghỉ được — bằng cách ứng trước của năm sau.** Trước đây xin quá số
      ngày còn lại là bị chặn thẳng, không còn đường nào khác. Nay phần mềm hỏi lại *"Đơn đã vượt
      hạn mức năm nay, có ứng trước N ngày của năm sau không?"*. Đồng ý thì đơn được tạo, và số
      ngày ứng đó **bị trừ thật vào quỹ phép năm sau** — không phải lời nhắc suông. Ứng vượt cả
      quỹ năm sau thì vẫn bị chặn
    + **Người duyệt thấy rõ đơn nào có ứng phép.** Cả ba bước duyệt (KSV, Tổng hợp, Ban lãnh đạo)
      và cả nút duyệt hàng loạt đều hiện cảnh báo nêu tên người xin nghỉ và năm bị ứng trước khi
      duyệt thật
    + **Trưởng / phó phòng cùng phòng nay duyệt thay nhau được ở bước KSV.** Trước đây chỉ đúng
      người được chọn lúc nộp đơn mới bấm được — người đó đi công tác hay nghỉ phép thì đơn nằm
      đó vô thời hạn, chỉ quản trị viên gỡ được. Nay bất kỳ trưởng / phó phòng nào **cùng phòng
      với người xin nghỉ** đều duyệt được (vẫn không ai tự duyệt đơn của mình)
    + **Tab "Báo cáo năm" đổi tên thành "Báo cáo tổng hợp"**, thêm mục *Báo cáo hàng tháng* chọn
      riêng năm / tháng
    + **Báo cáo chấm công tháng (file Excel)** dựng theo mẫu giấy "Tổng hợp chấm công TTTT" —
      nhóm theo phòng, **X** = đi làm, **P** = nghỉ phép, ô để trống tô màu = T7/CN/ngày lễ.
      ⚠️ **Chỉ điền được hai cột đó.** Các buổi họp / tập huấn / công tác và cột xếp loại thi đua
      **không có trong phần mềm** nên để trống, phòng Tổng hợp điền tay sau khi tải về — đã ghi
      chú ngay cuối bảng trong file
    + **Rê chuột trên bảng đơn nghỉ phép nay sáng cả dòng lẫn cột** như Excel, đỡ dóng nhầm hàng
    + **Nút "Tải phiếu" hết bị rớt về bản chưa ký.** Lần in đầu tiên sau khi máy chủ khởi động,
      Word cần tới hơn một phút để sẵn sàng; phần mềm chỉ chờ 60 giây rồi bỏ cuộc và đưa bản
      `.docx` chưa có chữ ký. Nay chờ đủ 160 giây
    + ⚠️ **QUAN TRỌNG — số ngày phép năm của một số người sẽ thay đổi sau lần cập nhật này.**
      Công thức thâm niên trước đây cộng thêm 1 ngày **mỗi 4 năm** vào ngành; đúng luật phải là
      **mỗi 5 năm**. Đối chiếu báo cáo thật năm 2026: mốc 5 năm khớp **67/72** người, mốc 4 năm cũ
      chỉ khớp **12/72**. Ai vào ngành đủ 4, 8, 12… năm sẽ **giảm 1 ngày** so với con số phần mềm
      hiển thị trước đây. Người nào đã nghỉ hết số cũ thì lần xin nghỉ tới sẽ báo hết phép —
      **báo lại cho phòng Tổng hợp chỉnh tay ở tab Hạn mức phép**, đừng tự đoán
    + ⚠️→✅ **~~Ngày phép chuyển từ năm trước hiện chưa hết hạn 31/03 như quy định~~ — đã sửa, xem
      entry mới nhất ở trên cùng.** Trước đây đơn nghỉ vào tháng 6, tháng 10 vẫn được cộng thêm
      số ngày chuyển năm
    + ⚠️→✅ **~~Nộp lại đơn bị từ chối mà vượt hạn mức thì chưa hỏi ứng phép~~ — đã sửa, xem entry
      mới nhất ở trên cùng.** Trước đây vẫn báo lỗi và dừng (tạo đơn mới và khai báo hộ thì đã có)
    + ⚠️→✅ **~~Đơn nghỉ vắt qua Tết dương lịch mà có ứng phép sẽ bị đếm thiếu ngày~~ — đã sửa,
      xem entry mới nhất ở trên cùng.** Trước đây chỉ ảnh hưởng đơn bắt đầu năm này kết thúc năm
      sau và đồng thời vượt hạn mức
- 05/09/2026 Nghỉ phép - **Nghỉ phép bắt buộc: đăng ký, điều chỉnh ngày, và mẫu đơn riêng theo chức danh**
    + **Điều chỉnh ngày nghỉ phép bắt buộc sau khi đơn đã duyệt xong.** Đơn đã "Hoàn thành" nay có
      nút *"Điều chỉnh ngày NPBB"*. Bấm vào sẽ tạo **một đơn mới**, đi lại đủ ba bước duyệt như đơn
      thường. **Đơn cũ không bị xoá và không bị sửa** — nó vẫn nằm nguyên đó cho tới khi đơn mới
      duyệt xong mới chuyển thành *"Đã hủy - Đã điều chỉnh"*. Mở đơn nào cũng thấy đường dẫn sang
      đơn kia, nên lúc nào cũng đối chiếu được ngày đã đăng ký với ngày xin đổi
    + **Mẫu đơn xin nghỉ phép năm nay in đúng theo chức danh.** Trước đây nhân viên, trưởng/phó
      phòng, Giám đốc, Phó Giám đốc **in ra cùng một tờ giấy** — phần mềm có sẵn danh sách 4 mẫu
      riêng nhưng 4 file mẫu đó **chưa từng được đặt vào máy**, nên nó lặng lẽ quay về dùng mẫu
      chung. Không báo lỗi, không ai biết. Nay đã có đủ 4 mẫu thật
    + **Đơn của Giám đốc trước đây "kính gửi Giám đốc Trung tâm Thanh toán"** — tức là gửi cho
      chính mình. Đối chiếu mẫu giấy thật, nay sửa thành **Tổng Giám đốc Agribank**
    + **Thêm 2 mẫu đơn cá nhân** (đăng ký / điều chỉnh nghỉ phép bắt buộc, "Mẫu 1 TCNS") và
      **báo cáo tổng hợp Mẫu 18 (nội bộ) / Mẫu 19 (gửi TCNS)** cho phòng Tổng hợp
    + ⚠️→✅ **~~CHƯA DÙNG ĐƯỢC "Báo cáo NPBB" (Mẫu 18/19)~~ — đã sửa, xem entry mới nhất ở trên.**
      Báo cáo này từng **liệt kê nhầm gần như toàn bộ nhân sự** kèm khoảng ngày không có thật.
      Nguyên nhân thật rộng hơn tưởng ban đầu: không phải riêng báo cáo NPBB bỏ sót lọc dòng tổng
      hợp, mà là lỗi SQL khiến MỌI danh sách/báo cáo đơn nghỉ phép âm thầm bỏ sót đơn thật không
      nhập lý do — xem chi tiết ở entry mới nhất
    + ⚠️→✅ **~~Số "Đã nghỉ" hiển thị có thể lớn hơn thực tế~~ — đã sửa, xem entry mới nhất ở trên.**
      Ghi chú lúc đó "*tab Hạn mức phép vẫn đúng*" **hoá ra chưa chính xác** — chính tab đó cũng bị
      đếm trùng đơn gốc/đơn điều chỉnh trong lúc đơn điều chỉnh còn chờ duyệt, chỉ là bug khác với
      bug ban đầu nghi ngờ. Đã sửa cả 2
    + ✅ **Màn hình danh sách đơn nghỉ phép nhanh hơn** — trước đây mỗi đơn hiện ra tốn 4 lượt hỏi
      cơ sở dữ liệu riêng, danh sách 1.000 đơn là hơn 4.000 lượt. Nay gộp lại còn 6 lượt cho cả
      danh sách, bất kể bao nhiêu đơn (đo được: 118 ms → 33 ms cho 991 đơn)
    + ✅ **Không phải làm gì sau khi cập nhật** — không đổi quyền, không đổi thao tác cũ

- 05/09/2026 Chấm ILO1000 - **Sửa lỗi giao dịch bình thường bị gán nhầm "Đã hủy"**
    + Người chấm phản ánh ngay trên file kết quả ngày **26/08**: nhiều món **sheet Hub ghi "Hoàn
      thành"** nhưng hệ thống chấm lại ghi **"Đã hủy"** — 24 dòng, đều thuộc các đợt chi trả
      **trợ cấp xã hội (BTXH)**
    + Nguyên nhân: các đợt chi trả này **dùng chung một số hiệu đợt** cho nhiều chi nhánh cùng
      tham gia — giống nhiều nhà chung một số nhà. Hệ thống tưởng đó là một giao dịch duy nhất,
      nên khi **một** chi nhánh có lệnh hủy thật thì nó gán **"Đã hủy" cho cả các chi nhánh còn
      lại**, dù những chi nhánh đó không liên quan gì
    + Cách chữa: khi xét hủy, hệ thống nay ghép **số hiệu đợt + mã chi nhánh** làm một cặp, không
      nhìn số hiệu đợt một mình nữa. Lệnh hủy của chi nhánh nào chỉ ảnh hưởng đúng chi nhánh đó
    + ⚠️ **Kết quả đã chấm trước đây có thể sai — nên chấm lại.** Món nào hệ thống ghi "Đã hủy"
      mà sheet Hub ghi "Hoàn thành" thì chạy lại file ngày đó để lấy kết quả đúng. **Lệnh hủy
      thật vẫn được nhận ra đầy đủ như cũ**, không mất món nào
    + ✅ **Không phải làm gì sau khi cập nhật** — không đổi giao diện, không đổi quyền, không đổi
      thao tác

- 04/09/2026 Danh sách CN TTQT - **Thêm nút xem lịch sử sửa đổi của từng chi nhánh**
    + Cuối mỗi dòng trong bảng có thêm nút hình **đồng hồ quay ngược** 🕘. Bấm vào mở bảng:
      **ngày giờ — người sửa — sửa mục nào — giá trị cũ → giá trị mới**
    + Ghi cho **cả hai đường**: sửa tay trên giao diện và nhập file Excel. Mỗi trường thay đổi là
      **một dòng riêng**, không gộp — nhìn ra ngay ai đổi số điện thoại, ai đổi mã SWIFT
    + Nhập lại **đúng file Excel cũ** thì không sinh dòng nào, vì không có gì đổi thật. Bấm Lưu mà
      không sửa gì cũng vậy. Lịch sử chỉ chứa thay đổi thật, không có dòng rác
    + Chi nhánh **bị xoá vẫn giữ lịch sử**; nếu sau đó nhập lại cùng mã CN thì lịch sử cũ hiện
      tiếp trong bản ghi mới — không mất dấu vết
    + ⚠️ **Lịch sử tính từ hôm nay trở đi.** Các lần sửa trước đây không dựng lại được: sổ nhật ký
      cũ chỉ ghi "đã sửa trường nào", không ghi sửa thành gì. Lúc chưa có dữ liệu, bảng hiện dòng
      *"Chưa có thay đổi nào được ghi lại"*
    + ⚠️ **Phải bật quyền thì nút mới hiện.** Vào **Phân quyền theo nhóm → Danh sách CN TTQT**,
      tick ô *"Xem lịch sử sửa đổi"* cho các nhóm cần dùng

- 04/09/2026 Đối chiếu Song phương - **Sửa lỗi khoá SPT bị Excel làm sai khi mở trực tiếp file CSV chi tiết**
    + Việc thật: người dùng báo cột **MtId/MsgId** (file `..._kenh_chi_tiet.csv`) và **TXID** (file
      `..._hub_chi_tiet.csv`) của SP THƯỜNG bị sai sau khi xuất kết quả — SP REALTIME thì không sao
    + Nguyên nhân: khoá SPT là chuỗi **16 chữ số thuần**. Excel mở CSV trực tiếp tự suy luận cột
      toàn chữ số là kiểu Số: **số 0 đứng đầu bị rụng**, và số vượt quá 15 chữ số có nghĩa (giới hạn
      của Excel) bị **làm tròn chữ số cuối về 0** — 16 chữ số của SPT vượt giới hạn này ở mọi giá trị
    + Fix: các cột khoá này giờ được bọc `="..."` trước khi ghi CSV, ép Excel hiểu là công thức trả
      về chuỗi và hiển thị đúng nguyên văn
    + ⚠️ **File CSV trên đĩa đổi định dạng ở đúng các cột này.** Mở bằng Excel bằng cách
      double-click vẫn ra đúng số như trước giờ, nhưng mở bằng trình soạn thảo văn bản, bằng
      Power Query, hoặc công cụ khác đọc CSV thô sẽ thấy `="..."` bao quanh giá trị — không phải lỗi,
      chỉ cần biết trước để khỏi bất ngờ
    + ✅ Không đổi quyền, không cần thao tác gì thêm ngoài lưu ý trên

- 04/09/2026 Chuẩn hoá văn bản - **Sửa 4 lỗi phát hiện trên văn bản thật (TB Swift code Quảng Ninh)**
    + **Số trang in ra sai — trang 2 ghi "24", trang 3 ghi "25".** Nguyên nhân: file gốc được cắt
      ra từ một tài liệu dài nên vẫn mang lệnh *"đánh số bắt đầu từ trang 23"* ẩn bên trong. Người
      soạn không nhìn thấy lệnh này ở đâu trên màn hình Word. Nay phần mềm đặt lại **đếm từ 1** và
      ghi số cũ vào nhật ký sửa đổi
    + **Tiêu ngữ đã có đường kẻ ngang rồi lại bị kẻ thêm vạch thứ hai.** Nguyên nhân: người soạn vẽ
      vạch bằng công cụ Line của Word, vạch đó **dính vào chính dòng chữ** chứ không nằm ở dòng
      riêng, nên phần mềm không thấy và vẽ đè thêm. Nay nhận ra được cả hai cách đặt vạch
    + **Trang 2 chỉ có đúng một đoạn văn** (bản gốc 2 trang, chuẩn hoá xong thành 3). Nguyên nhân:
      chuẩn hoá làm chữ cao lên (giãn dòng 1,2 theo quy định) nên đoạn cuối tràn sang trang sau,
      rồi **dấu ngắt trang do người soạn đặt tay** lại đẩy phần tiếp theo sang trang thứ ba
    + ⚠️ **Phần mềm nay tự bỏ ngắt trang thủ công.** Dấu ngắt tay được đặt theo bố cục **cũ** của
      văn bản, giữ lại thì hay đẻ ra trang trống. Việc bỏ **hiện rõ trong nhật ký sửa đổi** cùng
      một dòng lưu ý
    + ⚠️ **Văn bản thật sự cần sang trang mới thì phải tắt ô này** — ví dụ Phụ lục ban hành kèm
      theo Quyết định. Vào tab **Cấu hình quy chuẩn**, bỏ tick ô *"Bỏ ngắt trang thủ công"* rồi
      chạy lại. Bản gốc không bao giờ bị sửa nên chạy lại bao nhiêu lần cũng được
    + **Tên ngân hàng bị bỏ in đậm mất nửa trên.** Tên *"NGÂN HÀNG NÔNG NGHIỆP VÀ PHÁT TRIỂN
      NÔNG THÔN VIỆT NAM"* dài nên viết thành 2 dòng. Phần mềm tưởng đó là **hai cấp đơn vị**
      (dòng trên là đơn vị cấp trên, dòng dưới là đơn vị ban hành) nên bỏ in đậm dòng trên. Nay
      nhận ra dòng bắt đầu bằng chữ *"VÀ"* là **phần nối tiếp của dòng trên**, không phải một tên
      mới — cả hai dòng cùng in đậm, và vẫn chỉ có một đường kẻ dưới dòng cuối
    + Khối **hai cấp thật** (ví dụ *"NGÂN HÀNG … VIỆT NAM"* rồi *"CHI NHÁNH HÀ NỘI"*) **không đổi
      gì** — vẫn là đơn vị cấp trên không in đậm, đơn vị ban hành in đậm
    + **Tab Cấu hình có thêm 5 ô tick** trước nay chưa hiện ra: nén chữ cho dòng thể thức vừa một
      dòng, mức nén tối đa, bỏ gạch chân ở dòng thể thức, vẽ đường kẻ ngang, bỏ ngắt trang thủ công
    + ✅ **Không phải làm gì sau khi cập nhật** — không đổi dữ liệu, không đổi quyền

- 04/09/2026 Chứng từ - **Trả lại ngày giờ nộp thật cho ô chứng từ bị điền nhầm người (chạy tay trên máy chủ)**
    + Việc thật: GDV nộp chứng từ **ngày 27/08** nhưng điền vào **ô của người khác**, HKV đã xác
      nhận. Người vận hành xoá ô nhầm rồi nhập lại vào ô đúng — ô mới mang **ngày nhập lại (03/09)**
      thay vì ngày nộp thật (28/08)
    + Lý do: **xoá ô là xoá vĩnh viễn**, kéo theo cả lịch sử của ô đó. "Ngày giờ nộp" không được
      lưu riêng ở đâu cả — nó chính là dòng lịch sử vừa bị xoá. Nhập lại thì hệ thống chỉ biết
      ngày hôm nay
    + Cách chữa: thêm `scripts/sua_moc_thoi_gian_o_chung_tu.py`, **chạy tay trên máy chủ**, đụng
      đúng một ô. Mặc định **chỉ xem, không ghi**; muốn ghi thật phải thêm cờ `--ghi` và script
      **tự sao lưu DB trước**. Chạy hai lần không hỏng thêm
    + ⚠️ Script **tự dừng** nếu ô nhầm vẫn còn hoặc số tờ trên máy chủ khác số tờ gốc — không tự
      quyết thay người vận hành
    + 🔎 Dấu vết can thiệp **không bị giấu**: script ghi một dòng vào **Nhật ký hệ thống** nói rõ
      đã sửa gì, vì sao
    + ⚠️ **Gốc rễ vẫn còn**: xoá một ô đã xác nhận là mất luôn cả số liệu lẫn lịch sử, không có
      thùng rác. **Trước khi xoá ô, hãy chắc chắn.** Đường sửa đúng (đánh dấu xoá thay vì xoá hẳn,
      hoặc thao tác "đổi chủ ô" giữ nguyên mốc thời gian) chưa làm trong đợt này vì đụng vào
      đường đọc số liệu bàn giao dùng chung cho báo cáo khối lượng và đóng tập
    + ✅ **Không phải làm gì sau khi cập nhật** — không đổi giao diện, không đổi quyền. Script chỉ
      chạy khi người vận hành gõ lệnh

- 03/09/2026 Đối chiếu Song phương - **⚠️ THÊM TAB "ĐỐI CHIẾU ĐI" — PHẢI CẤP QUYỀN SAU KHI DEPLOY**
    + Tab "Đối chiếu đi" (Kênh↔Hub + Hub↔Core) trước đây chỉ có khung "chưa triển khai" — nay chạy
      đầy đủ, cùng cách dùng như tab "Đối chiếu đến" đã có (chọn file, ngày, ngân hàng, bấm Chạy)
    + **Việc phải làm ngay sau khi deploy:** vào **Phân quyền chức năng**, cấp mục
      `Chạy "Đối chiếu đi" (Kênh↔Hub + Hub↔Core)` cho các nhóm cần dùng — thiếu mục này thì vẫn
      **vào xem được** tab mới nhưng bấm nút **Chạy** sẽ báo "Không có quyền truy cập tính năng này"
    + Vì sao phải làm tay: đây là quyền **mới hoàn toàn**, chưa từng tồn tại nên không nhóm nào có
      sẵn. Tài khoản Quản trị viên dùng được ngay — **thử bằng tài khoản quản trị sẽ tưởng đã xong**,
      phải thử bằng tài khoản thường mới biết đã cấp đủ hay chưa (đúng bài học đợt 02/09)
    + Cách tính chiều đi khác chiều đến ở vài điểm nghiệp vụ (không lọc bớt dữ liệu trước khi đối
      chiếu Kênh↔Hub, cách nhận diện giao dịch quyết toán/lệnh FX...) — người chấm đã xác nhận quy
      tắc trước khi triển khai, không cần thao tác gì thêm ngoài việc cấp quyền ở trên
    + ✅ Không đổi dữ liệu/quyền của tab "Đối chiếu đến" đang dùng
    + ⚠️ **Bổ sung 10/09/2026 (review Khánh PR#86):** tên file kênh (Excel do ngân hàng đối tác
      gửi) từ nay BẮT BUỘC phải có chữ "đến" hoặc "đi" trong tên (không dấu cũng được: "den"/"di")
      — trước đó chỉ cần đủ "kênh" + mã ngân hàng + loại (SPRT/SPT). Đổi để phân biệt 1 thư mục có
      cả file kênh chiều đến lẫn chiều đi cùng mã NH. **Ảnh hưởng cả tab "Đối chiếu đến" đang
      dùng** — file kênh cũ đặt tên không có từ khoá chiều giờ không được nhận diện nữa, hệ thống
      ghi "thiếu file kênh" dù file vẫn nằm đúng chỗ. Cách xử lý: đổi tên file kênh thêm chữ
      "đến"/"đi" cho khớp chiều thật của file.

- 03/09/2026 Chuẩn hoá văn bản - **Kẻ đúng đường kẻ ngang, không để tên ngân hàng bị cắt đôi, trích yếu 2 dòng không còn lệch**
    + **Đường kẻ ngang dưới Tiêu ngữ, tên đơn vị và trích yếu nay được vẽ đúng.** Quy định đòi
      *đường kẻ ngang nét liền*, dài bằng dòng chữ ở Tiêu ngữ và bằng **1/3–1/2** dòng chữ ở hai
      chỗ kia. Trước đây phần mềm không vẽ được thứ ngắn hơn dòng chữ. Chạy chuẩn hoá lại nhiều
      lần cũng không bị chồng thêm vạch
    + **Tên ngân hàng không còn bị cắt đôi.** Dòng *"NGÂN HÀNG NÔNG NGHIỆP VÀ PHÁT TRIỂN NÔNG THÔN
      VIỆT NAM"* ở cỡ chữ 13 dài hơn ô chứa nên Word đẩy chữ **"NAM" xuống một dòng riêng**. Nay
      phần mềm **đo bề rộng chữ thật** rồi **nén ký tự lại** cho vừa — đúng cách mẫu 979 làm, và
      **không hạ cỡ chữ** (cỡ chữ là do quy định, hạ xuống là làm sai một thứ đang đúng)
    + ⚠️ Nén tới mức tối đa mà vẫn tràn thì phần mềm **dừng lại và ghi cảnh báo** trong nhật ký sửa
      đổi, không nén tiếp — nén quá tay thì chữ dính vào nhau, đọc còn khó hơn để nó xuống dòng.
      Thấy cảnh báo này thì rút ngắn tên đơn vị hoặc nới ô chứa trong file gốc
    + **Trích yếu dài 2–3 dòng không còn lệch nhau.** Trước đây chỉ dòng đầu được canh giữa và in
      đậm, dòng thứ hai bị căn đều hai bên và chữ thường — nhìn ra ngay là hai khối lệch. Nay các
      dòng nối tiếp cũng được nhận là trích yếu (tối đa 3 dòng, và dừng ngay khi gặp *Căn cứ*,
      *Điều*, *Kính gửi*…)
    + Bốn mục mới trong tab **Cấu hình quy chuẩn** để bật/tắt: nén chữ cho vừa dòng, mức nén tối
      đa, gỡ gạch chân ở dòng thể thức, vẽ đường kẻ ngang
    + ✅ **Không phải làm gì sau khi cập nhật** — không đổi dữ liệu, không đổi quyền

- 03/09/2026 Nhật ký hệ thống - **Cột "Chi tiết" nay nói rõ đã sửa cái gì; thêm bộ lọc và xem chi tiết từng dòng**
    + **Trước đây cột "Chi tiết" trống ở phần lớn số dòng** — đo trên máy thật: 2.292/2.885 dòng
      (79%) không có gì. Người tra soát biết *ai đã sửa tập chứng từ lúc mấy giờ* nhưng không biết
      **sửa gì**, muốn biết phải đi mò lại trong chính màn hình nghiệp vụ
    + Nay mỗi dòng kèm **tóm tắt dữ liệu đã gửi lên** (các trường và giá trị). Ví dụ thay vì chỉ
      thấy *"HTTP 200"*, giờ đọc được *"trang_thai=approved, ghi_chu=Đồng ý"*
    + **Bấm vào một dòng bất kỳ** để mở bảng xem đầy đủ: thời gian, người thao tác, chi tiết,
      đường dẫn kỹ thuật, nguyên văn bản ghi, địa chỉ IP, mã bản ghi. Bảng chính vẫn hiện bản rút
      gọn cho dễ quét mắt
    + **Thêm bộ lọc**: khoảng ngày (Từ ngày / Đến ngày), **người thao tác**, và **module**
      (chứng từ, nghỉ phép, chấm công, DTBB, ôn tập, chuẩn hoá văn bản…). Ô chọn người thao tác
      chỉ liệt kê những người **đã thực sự có dòng** trong nhật ký, kèm số dòng của từng người
    + 🔒 **Mật khẩu, mã đăng nhập và ảnh chữ ký KHÔNG bao giờ được ghi vào nhật ký** — bị che
      thành `***`. Việc này quan trọng vì nhật ký **xuất được ra Excel và tải về**, tức là coi như
      đã công khai. File tải lên (Excel, ZIP, ảnh) cũng không bị đọc vào nhật ký
    + ✅ **Không phải cấp quyền gì thêm** — ai đang vào được menu **Nhật ký hệ thống** thì dùng
      được ngay. Dòng nhật ký cũ vẫn xem bình thường, chỉ là không có phần tóm tắt (lúc ghi chưa
      có tính năng này)

- 03/09/2026 Chuẩn hoá văn bản - **Thêm tab "Mẫu trình bày sẵn": tải về bản trắng của 18 mẫu Phụ lục V**
    + Vào **Tính năng khác → Chuẩn hoá văn bản**, có thêm tab **"Mẫu trình bày sẵn"** bên cạnh tab
      cũ. Trong đó là 18 mẫu của Phụ lục V — Nghị quyết, Quyết định, Văn bản hợp nhất, Thư công
      tác, Tờ trình, Công văn, Giấy mời, Giấy giới thiệu, Biên bản, Giấy biên nhận, Giấy đi đường,
      Đơn xin nghỉ phép, Phiếu trình chuyển, Bản sao văn bản, Phụ lục văn bản…
    + Bấm **"Tải mẫu"** ở dòng nào là tải về file Word trắng của mẫu đó, mở ra điền nội dung vào
      là xong — không phải mở file Phụ lục 20 trang rồi copy-paste từng khối nữa
    + **Lề trang đã đặt sẵn đúng quy định** (trên/dưới 20 mm, trái 30 mm, phải 20 mm). Bản nằm
      trong file Phụ lục để lề trên/dưới 15 mm cho mỗi mẫu vừa gọn một trang giấy — ai copy thẳng
      từ đó ra là văn bản sai lề ngay từ đầu mà không biết
    + ⚠️ **Phần "Ghi chú" của Phụ lục được giữ nguyên trong mẫu** — theo yêu cầu. Cụ thể là dòng
      *"Ghi chú: Mẫu này áp dụng chung đối với..."* ở cuối **Mẫu 07**, và mấy dòng chú thích nhỏ ở
      chân trang của **Mẫu 04** và **Mẫu 17**. Đây là hướng dẫn của Phụ lục, **phải tự xoá trước
      khi phát hành văn bản** — phần mềm không tự xoá
    + ✅ **Không phải cấp quyền gì thêm** — ai đang vào được menu **Chuẩn hoá văn bản** thì tải mẫu
      được luôn, không có ô tick mới trong Phân quyền chức năng
    + ✅ **Không đổi gì ở tab chuẩn hoá cũ** — tải file lên để phần mềm sửa thể thức vẫn chạy y như trước

- 03/09/2026 Đối chiếu Song phương - **Sửa lỗi: chọn CSV đã phân loại sẵn cho GL02 thì không chạy đúng**
    + Ở thẻ **"Đối chiếu đến"**, phần nạp dữ liệu CORE/GL02 có 2 cách: tải file ZIP GL02 gốc (hệ
      thống tự giải mã + phân loại), hoặc tải thẳng file CSV đã phân loại sẵn (tải từ thẻ "Phân
      loại dữ liệu" ở trước, chọn đúng file `{mã NH}_DEN.csv` của ngân hàng cần chấm)
    + **Trước đây cách CSV bị lỗi:** khi đối chiếu cửa sổ nhiều ngày (T-3 đến T+3), 1 file CSV của
      đúng 1 ngày lại bị dùng nhầm làm dữ liệu cho **cả 4 ngày trong cửa sổ**, làm sai kết quả đối
      chiếu Hub↔Core. Cách dùng file ZIP gốc không bị lỗi này (tên file ZIP tự mang đúng ngày)
    + Nay đã sửa: file CSV chỉ được dùng cho đúng 1 ngày nó đại diện; các ngày còn lại trong cửa
      sổ không có CSV riêng thì phải có file ZIP đúng ngày đó, không tự lấy tạm CSV ngày khác nữa
    + ⚠️ **Lưu ý khi dùng cách CSV:** 1 file CSV chỉ có dữ liệu của đúng ngày đối chiếu. Giao dịch
      hôm nay mà CORE hạch toán sang **ngày hôm sau** sẽ bị xếp vào "HUB THỪA". Muốn chấm đủ thì
      nạp thêm file **GL02 zip của ngày hôm sau**. Bản ghi log giờ nói rõ điều này khi thiếu, thay
      vì chỉ ghi cụt lủn "BẮT BUỘC" rồi vẫn báo hoàn thành
    + ✅ **Không phải làm gì sau khi cập nhật** — không đổi dữ liệu đã có, không đổi quyền của ai

- 03/09/2026 Chấm công + Đối chiếu DTBB - **⚠️ HAI MENU NÀY GIỜ THEO PHÂN QUYỀN — PHẢI CẤP QUYỀN SAU KHI DEPLOY, KHÔNG LÀM LÀ PHÒNG KẾ TOÁN MẤT MENU**
    + Trước đây phần mềm tự nhận ra ai thuộc **Phòng Kế toán** rồi cho hiện hai menu **"Chấm công"**
      và **"Đối chiếu DTBB"**. Ai không thuộc phòng đó thì không có cách nào cấp được, dù cần —
      phải sửa phần mềm. Nay hai menu này chuyển sang **Phân quyền chức năng** giống mọi menu khác
    + **⚠️ Việc phải làm NGAY sau khi deploy** — vào **Phân quyền chức năng**, cấp cho nhóm của
      Phòng Kế toán:
        - `Chấm công (menu)` — thiếu là **cả phòng không thấy menu Chấm công**, kể cả để xem công
          của chính mình
        - `Đối chiếu DTBB (menu)` — thiếu là **cả phòng không thấy menu Đối chiếu DTBB**
        - `Xác nhận / Bỏ xác nhận kỳ DTBB` — cấp cho **Trưởng phòng và Phó phòng Kế toán**. Thiếu
          là vào xem được nhưng bấm nút xác nhận (vàng → xanh) sẽ báo *"Không có quyền truy cập
          tính năng này"*
    + Vì sao phải làm tay: hai mã `Đối chiếu DTBB (menu)` và `Xác nhận / Bỏ xác nhận kỳ DTBB` là
      **quyền mới hoàn toàn**, chưa nhóm nào có. Riêng `Chấm công (menu)` thì mã đã có sẵn từ lâu
      nhưng **trước đây không điều khiển gì cả** — nhóm nào đang tick sẵn thì dùng được ngay, nhóm
      chưa tick phải tick vào
    + Tài khoản **Quản trị viên vẫn dùng được ngay** không cần cấp gì — nên **thử bằng tài khoản
      quản trị sẽ tưởng mọi thứ đã xong**. Bắt buộc thử bằng một tài khoản nhân viên Phòng Kế toán
      thường mới biết đã cấp đủ chưa
    + **Đổi lại được gì:** giờ giao cho một người phòng khác làm hộ chấm công hoặc DTBB chỉ cần
      tick một ô, không phải sửa phần mềm và chờ deploy. Bảng công vẫn **chỉ liệt kê nhân viên
      Phòng Kế toán** như cũ — cấp quyền là cho phép người ta **mở màn hình**, không đổi nội dung
      bảng
    + Không có màn hình mới, không đổi số liệu, không phải nhập lại gì

- 03/09/2026 Menu - **"Đối chiếu DTBB" chuyển vào nhóm Đối chiếu**
    + Trước đây **"Đối chiếu DTBB"** đứng riêng một dòng ngoài cùng danh sách menu bên trái. Nay
      nằm trong nhóm **Đối chiếu → Phòng Kế toán**, cùng chỗ với các màn đối chiếu khác
    + Chỉ đổi vị trí trên menu. Màn hình, số liệu, cách làm không đổi gì

- 02/09/2026 Nghỉ phép + Chấm công - **Ngày làm bù nay tính là ngày đi làm**
    + Cùng đợt với mục Báo cáo nộp chứng từ ở trên, nay áp dụng nốt cho **Nghỉ phép** và
      **Chấm công**. Cả phần mềm dùng chung một cách hiểu "thế nào là ngày làm việc"
    + **Nghỉ phép:** nghỉ đúng ngày làm bù (thứ Bảy cả cơ quan đi làm) thì **vẫn bị trừ vào quỹ
      phép**. Trước đây không trừ — máy tưởng đó là thứ Bảy nghỉ bình thường. Số ngày trên đơn,
      ô "đã dùng", ô "còn lại" và số ngày mang sang quý I năm sau đều tính lại theo cách mới
    + **Đơn in ra cũng đổi câu chữ:** nghỉ thứ Sáu và thứ Hai mà thứ Bảy ở giữa là ngày làm bù thì
      đơn **không** còn ghi gộp "Từ ngày ... đến hết ngày ..." nữa mà liệt kê từng ngày — vì ghi
      gộp là khai nghỉ cả thứ Bảy, ngày người ta thực tế có mặt
    + **Chấm công:** ngày làm bù nay **có tính công** (mặc định ký hiệu "x" như ngày thường), **xin
      điều chỉnh được**, và trên lưới **không còn tô màu vàng cuối tuần** nữa. Bảng công xuất ra
      Excel cũng vậy. Trước đây ngày đó bị chấm 0 công và bấm xin điều chỉnh thì báo *"Không thể
      xin điều chỉnh cho ngày nghỉ cuối tuần"*
    + **Vẫn chỉ khai một chỗ duy nhất:** Phân lịch trực → tab "Ngày đặc biệt" → loại "Ngày bù", và
      phải bấm **Xác nhận**. Không có màn hình mới
    + Tính năng Nghỉ phép chưa dùng chính thức nên **không có đơn thật nào bị ảnh hưởng**. Bảng
      chấm công thì có: tháng nào có ngày làm bù đã khai, tổng số công của tháng đó sẽ tăng lên
      đúng bằng số ngày bù

- 02/09/2026 Báo cáo nộp chứng từ - **⚠️ TỈ LỆ ĐÚNG HẠN CÓ THỂ ĐỔI — phải khai ngày làm bù**
    + Quy định là nộp chứng từ trong **1 ngày làm việc**, không tính thứ Bảy, Chủ nhật và ngày lễ.
      Nhưng trước đây phần mềm **không biết ngày đi làm bù**: thứ Bảy cả cơ quan đi làm mà máy vẫn
      coi là ngày nghỉ, nên chứng từ nộp trễ thật vẫn được chấm là đúng hạn
    + Nay đã sửa. Phần mềm lấy ngày làm bù từ chỗ **đã có sẵn**: menu **Phân lịch trực → tab
      "Ngày đặc biệt"** — chọn loại **"Ngày bù"**. Không có màn hình mới nào phải học
    + **Việc phải làm:** ngày làm bù nào chưa khai thì vào đó khai, và nhớ bấm **"Xác nhận"**.
      Khai xong mà quên bấm Xác nhận thì phần mềm vẫn coi hôm đó là ngày nghỉ như cũ — giống hệt
      cách Sổ trực đang làm, không phải quy tắc mới
    + Ngày lễ khai ở **màn Nghỉ phép** vẫn dùng bình thường như trước, không phải nhập lại. Ngày lễ
      khai ở tab Ngày đặc biệt cũng được tính. Nếu **một ngày được khai ở cả hai chỗ mà khác nhau**
      (ví dụ danh mục lễ ghi là nghỉ, Phân lịch trực ghi là ngày bù) thì **lấy theo Phân lịch trực**
    + **⚠️ Số cũ sẽ đổi:** in lại báo cáo của tháng đã qua sau đợt này có thể ra tỉ lệ khác trước —
      vài chứng từ đang "đúng hạn" chuyển sang "quá hạn". Đó là kết quả **đúng** theo quy định, không
      phải phần mềm hỏng. Ai đã in bản cũ để lưu thì nên biết trước điều này
    + Hai loại **"Cut-off"** và **"Quyết toán"** ở tab Ngày đặc biệt **không** phải ngày nghỉ, không
      ảnh hưởng gì tới hạn nộp — cứ khai như trước
    + **Nghỉ phép và Chấm công cũng đổi theo** (xem mục ngay dưới)

- 02/09/2026 Đối chiếu Song phương + Chấm ILO1000 - **⚠️ HAI MÀN HÌNH MỚI — PHẢI CẤP QUYỀN SAU KHI DEPLOY**
    + Đợt này thêm **2 thứ mới**: tab **"Đối chiếu đến"** (Kênh↔Hub + Hub↔Core) nằm trong màn
      Đối chiếu Song phương đã có, và màn hình **"Chấm ILO1000"** (đối chiếu 4 nguồn) hoàn toàn mới
    + **Việc phải làm ngay sau khi deploy:** vào **Phân quyền chức năng**, cấp 2 mục mới cho các
      nhóm cần dùng:
        - `Chấm ILO1000 — Đối chiếu 4 nguồn (menu)` — thiếu mục này thì **không ai nhìn thấy màn
          hình mới** trong danh sách bên trái (trừ tài khoản Quản trị viên)
        - `Chạy "Đối chiếu đến" (Kênh↔Hub + Hub↔Core)` — thiếu mục này thì vẫn **vào xem được**
          tab mới nhưng bấm nút **Chạy** sẽ báo *"Không có quyền truy cập tính năng này"*
    + Vì sao phải làm tay: đây là quyền **mới hoàn toàn**, chưa từng tồn tại trong máy nên không
      nhóm nào đang có sẵn. Khác đợt ACH 31/08 — lần đó quyền đã khai từ trước nên cấp bù tự động
      được; lần này không có gì để cấp bù từ đó
    + Tài khoản Quản trị viên dùng được ngay, không cần cấp gì — nên **nếu chỉ thử bằng tài khoản
      quản trị thì sẽ tưởng mọi thứ đã xong**. Phải thử bằng một tài khoản thường mới biết đã cấp
      đủ hay chưa
    + Lần deploy này **cài thêm thư viện** (`numba`, `numpy`) nên bước "đang cài thư viện" của
      `deploy.bat` sẽ lâu hơn thường lệ (tải khoảng 100 MB). Cứ để chạy, không phải làm gì. Máy
      không cài được cũng **không sao** — phần mềm tự chạy theo cách cũ, chỉ chậm hơn ở bước giải
      nén file GL02

- 02/09/2026 Đối chiếu Song phương + Chấm ILO1000 - **Bỏ nút "Chọn thư mục server", chỉ còn "Tải file lên"**
    + Trước đây 2 màn hình này có 2 cách nạp dữ liệu: tải file lên qua trình duyệt, hoặc gõ đường
      dẫn một thư mục trên máy chủ rồi bấm **"Duyệt..."** để chọn. Nay bỏ hẳn cách thứ hai —
      **chỉ còn tải file lên**
    + Lý do: hộp thoại "Duyệt..." cho xem cả cây thư mục của máy chủ, và rà lại lần này phát hiện
      vẫn còn vài chỗ chưa được chặn đúng phạm vi cho phép. Bỏ hẳn đường này để chắc chắn **không
      ai còn xem/dò được thư mục máy chủ qua nút Duyệt** nữa, thay vì vá từng chỗ dễ bị sót thêm
      về sau
    + Cách nạp file lên không đổi: vẫn chọn file như trước (giữ Ctrl hoặc Shift để chọn nhiều file
      một lúc), phần mềm tự lưu và chạy y như cũ
    + ✅ **Không phải làm gì sau khi cập nhật** — không đổi dữ liệu đã có, không đổi quyền của ai,
      không cần thao tác gì thêm

- 01/09/2026 Chấm 459901 - **Sửa 3 lỗi: đếm thiếu dòng, thanh tiến trình chạy mãi, nút Dừng im lặng**
    + **Ô "Tổng số dòng" đếm thiếu đúng bằng số dòng của file tồn tháng trước.** Cộng 7 nhóm
      kết quả lại thì ra một con số, mà ô tổng ở trên lại ghi con số nhỏ hơn — ai đối chiếu hai
      chỗ đều tưởng phần mềm làm mất dòng. Thật ra 7 nhóm mới đúng, chỉ ô tổng chốt sổ quá sớm,
      trước lúc ghép file tồn vào. **Không có dòng nào bị mất, chỉ hiển thị sai**
    + **Thanh tiến trình chạy mãi không dừng nếu máy chủ khởi động lại giữa chừng.** Trước đây
      mất liên lạc thì phần mềm cứ hỏi lại vô hạn, không báo gì — người dùng ngồi chờ một việc
      đã chết. Nay thử lại 4 giây, vẫn không được thì **báo rõ "mất kết nối, không rõ đã xong
      hay chưa"** và mở khoá nút để chạy lại. Phiên đăng nhập hết hạn thì tự về trang đăng nhập
      thay vì đứng im
    + **Nút "Dừng" và "Xóa kết quả" bấm vào không phản hồi trong một số trường hợp.** Khi có lỗi,
      thông báo lỗi bị nuốt mất — màn hình không đổi gì, cũng không báo gì. Nay báo đúng
    + ✅ **Không phải làm gì sau khi cập nhật**

- 31/08/2026 Chấm đối chiếu ACH - **⚠️ VIỆC PHẢI LÀM SAU KHI DEPLOY ĐỢT NÀY (PR#54)**
    + **Kiểm tra quyền `cham_ach.process` ngay sau khi deploy.** Đợt này bắt đầu ép kiểm tra
      thật quyền chạy (`cham_ach.process`) cho nút "Chạy đối chiếu"/"Tiếp tục"/"Dừng" — trước
      đây mã này đã khai nhưng CHƯA từng được kiểm, các nhóm trong DB thật có thể chỉ được cấp
      `menu.cham_ach` (xem trang) mà chưa có `cham_ach.process` (chạy). Đã có migration tự cấp
      bù `cham_ach.process` cho mọi nhóm đang có `menu.cham_ach` (giữ nguyên quyền như trước
      deploy), nhưng **vẫn nên chạy câu SQL sau trên DB thật để xác nhận không còn nhóm nào bị
      sót** (migration chỉ chạy 1 lần lúc khởi động backend):
      ```sql
      SELECT g.name FROM user_groups g
      JOIN group_features gf ON gf.group_id = g.id AND gf.feature_code = 'menu.cham_ach'
      WHERE NOT EXISTS (
          SELECT 1 FROM group_features x
          WHERE x.group_id = g.id AND x.feature_code = 'cham_ach.process'
      );
      ```
      Ra dòng nào là nhóm đó vẫn thiếu quyền chạy — cấp tay qua màn Phân quyền chức năng.
    + **Xoá tay thư mục `data/temp_ach` cũ (đường dẫn tương đối, nằm cạnh thư mục chạy
      backend)** nếu có. `TEMP_DIR` đổi sang đường dẫn tuyệt đối (`BASE_DIR/data/temp_ach`) —
      thư mục cũ ở vị trí tương đối sẽ không còn được vòng dọn tự động quét tới, thành mồ côi
      vĩnh viễn nếu không xoá tay một lần.
- 30/08/2026 Chấm 459901 - **Sửa lỗi file Excel kết quả không mở được khi dữ liệu quá lớn**
    + **Gộp từ 2 file GL02 trở lên thì file *Lệnh Đi* trước đây Excel không mở được.** Một file GL02 một ngày đã cho khoảng **617.000 dòng** nhóm *Lệnh Đi*, mà một trang tính Excel chỉ chứa được tối đa **1.048.576 dòng**. Phần mềm cứ ghi tiếp qua giới hạn đó rồi báo *"Hoàn thành!"* như bình thường — người dùng chờ hơn một phút, tải về file hơn 100 MB, mở ra thì Excel **từ chối** hoặc đòi *"repair"* và ăn mất dữ liệu. **Không có thông báo lỗi nào ở cả hai đầu**
    + **Nay nhóm nào quá lớn sẽ tự tách sang trang tính thứ hai trong cùng file** — tên trang ghi rõ *Lệnh Đi (1/2)*, *Lệnh Đi (2/2)*. **Vẫn đúng 7 file kết quả như cũ**, chỉ là mở ra thấy nhiều trang tính hơn; cách tải về không đổi
    + **Dòng TỔNG CỘNG ở cuối mỗi trang tính là tổng của riêng trang đó**, nhãn ghi rõ *TỔNG CỘNG PHẦN 2/2* để không nhầm. Tổng của cả nhóm nằm ở dòng tiêu đề trên cùng, kèm khoảng dòng đang xem
    + ✅ **Lượt chạy bình thường (chỉ một trang tính) hiển thị y hệt trước, không đổi gì** — tên trang không có đuôi, nhãn vẫn là *TỔNG CỘNG*. Không phải làm gì sau khi cập nhật

- 30/08/2026 Đóng chứng từ - **Trang danh sách bìa mở nhanh hơn, và không chậm dần theo năm tháng**
    + **Mỗi lần mở trang, phần mềm tải về toàn bộ bìa chứng từ từ trước đến nay** kèm chi tiết từng tập và từng chứng từ bên trong — trong khi bảng danh sách chỉ hiện 5 cột: tên phòng, kỳ, ngày tạo, người tạo, số bìa
    + Đo trên dữ liệu thật rồi nhân lên theo năm: kho **1 năm** mất 39 mili giây và 315 KB; kho **5 năm** mất **513 mili giây và 5,1 MB** — càng dùng lâu càng chậm, không có điểm dừng
    + **Nay chỉ lấy đúng 5 cột đang hiện**: kho 5 năm còn **32 mili giây**, dung lượng còn **8,3 KB**. Bấm vào từng bìa để in hoặc tải xuống thì vẫn lấy đầy đủ chi tiết như trước, **không mất gì**
    + **Sửa thêm lỗi nút "Lọc" im lặng**: nếu phiên đăng nhập đã hết hạn, bấm *Lọc* thì màn hình đứng im — không báo gì, cũng không tự chuyển về trang đăng nhập. Nay báo đúng và chuyển trang

- 30/08/2026 Rà soát toàn hệ - **Sửa lỗi cả giao diện không lên được, và nhật ký bị bơm lỗi giả**
    + **Toàn bộ giao diện không khởi động được** vì trang *Chấm 459901* còn gọi một hàm đã bị gỡ ở đợt trước (gỡ cùng lúc với nút *Duyệt...*). Cách nạp trang hiện tại **không bọc chống lỗi**, nên một trang hỏng là cả phần mềm không lên — không riêng trang đó
    + Nút **"Duyệt..."** ở chế độ *chọn thư mục server* đã bỏ hẳn: hộp thoại đó cho **mọi người đăng nhập liệt kê sạch ổ đĩa máy chủ**. Vẫn dán được đường dẫn như thường, phạm vi thư mục vẫn bị chặn như cũ
    + **Nhật ký vận hành không còn bị bơm lỗi giả khi chạy kiểm thử.** Trước đây mỗi lượt chạy test lại ghi thêm hàng loạt dòng báo lỗi *"không tìm thấy bảng"* vào nhật ký thật — người vận hành mở ra thấy lỗi không hề tồn tại rồi đi tìm sự cố không có

- 28/08/2026 Menu mới - **Quản lý nhân sự** (hồ sơ cán bộ, tra cứu & thống kê, nhắc lịch)
    + Nhóm menu mới **Quản lý nhân sự** với 3 mục: **Hồ sơ cán bộ**, **Tra cứu & Thống kê**, **Nhắc lịch**
    + **Hồ sơ cán bộ** gồm 8 phần: hồ sơ cá nhân (kèm **ảnh thẻ**, CCCD, địa chỉ, số người phụ thuộc, người liên lạc) · bằng cấp và chứng chỉ · quy hoạch – bổ nhiệm – điều động (**đính kèm được file PDF quyết định**) · thông tin và quá trình công tác · quá trình nghỉ gián đoạn · hồ sơ lương · đào tạo tại Agribank · công cụ dụng cụ đang đứng tên
    + **Hồ sơ gắn thẳng vào tài khoản đang có** — không phải nhập lại họ tên, mã cán bộ, phòng. Sửa điện thoại/email trong hồ sơ là sửa luôn thông tin tài khoản, không có hai nơi lệch nhau
    + **"Ngày tuyển dụng" và "Ngày vào ngành" là MỘT** — chỉ có một ô, sửa ở màn *Hồ sơ cán bộ* hay màn *Quản lý User* đều là sửa cùng một chỗ, không còn cảnh hai ô cùng nghĩa ghi lệch nhau. ⚠️ Ô này quyết định **số ngày phép năm**, nên **cán bộ không tự sửa được** — chỉ người được cấp quyền *"Sửa hồ sơ cán bộ khác"* mới sửa
    + **Ai cũng tự khai được hồ sơ của chính mình** (thông tin cá nhân, bằng cấp, khoá đào tạo, trạng thái công cụ đang giữ). Muốn xem hoặc sửa hồ sơ người khác thì phải được cấp thêm quyền trong màn hình *Phân quyền theo nhóm*
    + **Hồ sơ lương có quyền riêng.** Không được cấp thì phần lương của người khác **không hiện ra**; và **sửa lương luôn cần quyền riêng, kể cả hồ sơ của chính mình**
    + **Tra cứu theo từng thời điểm**: chọn một ngày trong quá khứ để xem danh sách cán bộ *toàn Trung tâm / Ban Giám đốc / Trưởng phòng / Phó phòng / trong quy hoạch* **đúng như tại ngày đó** — phòng lấy theo lịch sử chuyển phòng, chức vụ lấy theo quyết định còn hiệu lực. Xuất được ra Excel
    + **Mỗi phòng xếp Trưởng phòng lên đầu**, rồi Phó phòng, rồi nhân viên (hậu kiểm viên và chuyên viên cùng bậc, xếp lẫn theo tên); Ban Giám đốc thì Giám đốc trước Phó Giám đốc. Chức vụ hiện ngay dưới tên trong danh sách để nhìn ra thứ tự
    + **Danh sách cán bộ sắp theo TÊN, đúng thứ tự bảng chữ cái tiếng Việt.** Trước đó máy xếp theo mã ký tự nên mọi tên bắt đầu bằng chữ có dấu (Đ, Ạ, Ô, Ư…) bị dồn xuống cuối danh sách — *Đào Tiến Thành* nằm sau *Vũ Văn Ngân*, ai tra theo vần đều tưởng hệ thống **lấy thiếu người** (dữ liệu vẫn đủ, chỉ sai chỗ đứng). Nay *Đào Tiến Thành* nằm đúng vần **Th**, cạnh *Thảo*, *Thu*, *Thủy*
    + **Thống kê** theo phòng ban, giới tính, trình độ, độ tuổi, đã qua chi nhánh hay chưa
    + **Nhắc lịch tự động**: nâng lương (báo trước 1 quý), bổ nhiệm lại (báo trước 1 năm), cấp điện thoại/công cụ mới (báo trước 1 quý). Việc **đã quá hạn vẫn nằm trong danh sách** và được tô đỏ, không biến mất
    + **Tài khoản quản trị viên không có hồ sơ nhân sự** — không nằm trong danh sách cán bộ, không được tính vào thống kê, tra cứu hay nhắc lịch. Quản trị viên vẫn vào màn hình bình thường để nhập hộ hồ sơ cho cán bộ khác
    + ⚠️ **Việc cần làm sau khi cập nhật**: quản trị viên vào *Phân quyền theo nhóm* → thẻ **Quản lý nhân sự** để cấp quyền. Chưa cấp thì chưa ai thấy menu này
    + **Đính kèm tệp ngay khi thêm dòng hồ sơ** — chọn file rồi bấm *Lưu* một lần, không phải lưu trước rồi mở lại. Tệp đang chờ hiện nhãn *chờ lưu* và bỏ ra được nếu chọn nhầm; chọn được nhiều tệp một lượt
    + **Định dạng nhận vào**: ảnh cá nhân là **JPG, PNG, WEBP** (tối đa 5 MB); tệp đính kèm là **PDF, JPG, PNG, WEBP** (tối đa 15 MB). Hộp thoại chọn file chỉ hiện đúng những đuôi này nên không còn cảnh chọn xong mới bị báo lỗi
    + Ảnh thẻ và file quyết định **nằm trong cơ sở dữ liệu** nên được sao lưu cùng bản backup hằng ngày
    + Thêm 9 bảng mới trong cơ sở dữ liệu (tự tạo lúc khởi động), **không sửa hay xoá bảng nào đang có**. Không đụng tới nghỉ phép, chấm công hay bất kỳ chức năng nào đang chạy

- 28/08/2026 Menu bên trái - **Gộp "Ôn tập" và "Chuẩn hoá văn bản" vào nhóm "Tính năng khác"**
    + Hai mục *Ôn tập trắc nghiệm* và *Chuẩn hoá văn bản* trước đây nằm rời ở ngoài cùng, nay **nằm chung trong mục "Tính năng khác"** — đưa chuột vào là hiện ra cả hai bên phải
    + *Ôn tập trắc nghiệm* **đổi tên ngắn lại thành "Ôn tập"** (tên trong màn hình Phân quyền theo nhóm cũng đổi theo)
    + **Không phải cấp lại quyền.** Ai đang thấy hai mục này thì sau khi cập nhật vẫn thấy đúng như vậy, chỉ khác chỗ đứng trên menu
    + Không đổi cơ sở dữ liệu, không đổi cách chạy của hai chức năng

- 28/08/2026 Chấm 459901 - **Chia 7 nhóm thay vì 3, thêm đối chiếu HUB và ghép tồn tháng trước**
    + **Kết quả nay tách thành 7 nhóm** thay vì 3: *Lệnh Hủy*, *Lệnh Đi*, *1000 Hoàn trả*, *Chuyển chi nhánh*, *Điện KO offline*, *Cân CN*, *GD khác*. Mỗi nhóm một file Excel riêng, phần phải chấm tay vì thế nhỏ đi rất nhiều
    + **Chấm được nhóm 1000 Hoàn trả** nếu tải kèm 2 file HUB (*Quay\_...* của lệnh đi và *Danh sach... den* của lệnh đến). Hai file này **không bắt buộc** — thiếu cả hai thì phần mềm bỏ qua nhóm này, các bút toán đó rơi về *GD khác* để chấm tay như trước. Chỉ tải lên **một trong hai** thì bỏ cả hai, và màn hình báo rõ để biết mà tải nốt
    + **Ghép được file tồn tháng trước** (`459_TON_T<số tháng>.xlsx`): những bút toán tháng trước chưa chấm xong được đưa vào cùng dữ liệu tháng này rồi phân loại lại từ đầu. Ghi chú chấm tay cũ trong file đó không được giữ lại — cố ý, để không mang theo kết luận cũ có thể đã sai
    + **Không cần đặt tên file dữ liệu theo mẫu nào.** Cứ kéo thả tất cả vào cùng lúc, phần mềm tự nhận ra đâu là file dữ liệu, đâu là 2 file HUB, đâu là file tồn. File lạ trong danh sách bị bỏ qua và báo tên ra, không chặn cả lượt
    + **Dòng chỉ khớp được một nửa thì không bị đoán bừa.** Bút toán tìm thấy một vế nhưng thiếu vế đối ứng sẽ nằm ở *GD khác* kèm ghi chú "nghi ngờ, cần chấm tay" — thà để người chấm nhìn còn hơn xếp nhầm nhóm rồi không ai kiểm lại
    + **Thêm cách nạp dữ liệu: chỉ thẳng thư mục trên máy chủ**, khỏi tải file lên. Dùng khi dữ liệu đã nằm sẵn trên máy chủ. Hai cách hiện cùng lúc trên màn hình, chọn cách nào cũng được
    + ⚠️ **Việc cần làm sau khi cập nhật (chỉ nếu muốn dùng cách chỉ thẳng thư mục)**: mở file `.env` trên máy chủ, thêm một dòng `CHAM459901_FOLDER_ROOTS=` rồi ghi thư mục chứa dữ liệu vào sau dấu bằng (nhiều thư mục thì ngăn nhau bằng dấu chấm phẩy), sau đó khởi động lại. **Chưa thêm dòng này thì bấm vào sẽ báo lỗi nhắc đúng việc phải làm** — cách tải file lên vẫn dùng bình thường, không phải làm gì. Sở dĩ phải khai trước là để phần mềm chỉ đọc đúng những thư mục đã cho phép, không đọc lung tung chỗ khác trên máy chủ
    + **Bấm Dừng giữa chừng nay dừng thật**, và có thể xoá bộ kết quả vừa chạy để làm lại từ đầu
    + Không đụng cơ sở dữ liệu, không đổi quyền
- 28/08/2026 Đối chiếu CITAD - PaymentHub (Phòng QLTK Nostro, Vostro) - **Dùng song song 2 tiện ích không còn đá nhau**
    + **Lỗi gặp phải**: ai dùng cả tiện ích của *Phòng Thanh toán* lẫn tiện ích của *Phòng QLTK Nostro, Vostro* thì **chỉ một bên chạy được**, bên còn lại báo lỗi không có quyền. Tạo lại mã bên này thì bên kia hỏng, và ngược lại — quay vòng mãi không thoát
    + **Nguyên nhân**: hai tiện ích tuy là hai gói riêng nhưng lại **dùng chung một ô đựng mã kết nối** theo từng người. Mã mới tạo ra ghi đè lên mã cũ, nên bấm *Tạo mã kết nối mới* ở màn hình này là **tự thu hồi mã của màn hình kia** — không có thông báo nào báo cho biết
    + **Nay mỗi phòng có ô đựng mã riêng.** Tạo hay thu hồi mã ở phòng nào chỉ ảnh hưởng đúng phòng đó. Dùng song song cả 2 tiện ích hoàn toàn bình thường
    + ⚠️ **Việc cần làm sau khi cập nhật**: ai đang dùng tiện ích *CITAD - PaymentHub N&V* phải vào màn hình đó, tab **Kết nối Extension**, bấm **Tạo mã kết nối mới** một lần nữa. Mã cũ không tự chuyển sang được — tab sẽ hiện "Chưa kết nối" cho dễ nhận ra. Mã của Phòng Thanh toán **không phải làm gì**, vẫn dùng như cũ
    + Có thêm một bảng mới trong cơ sở dữ liệu (tự tạo lúc khởi động), không sửa hay xoá bảng nào đang có. Không đổi quyền, không đổi cách đối chiếu

- 28/08/2026 Đối soát CITAD - **Lệnh đi báo thành công nhưng kênh chưa xác nhận ngày trả thì không tự khớp nữa** (PR #65)
    + Lệnh chiều Đi bên IPCAS ghi trạng thái `SCNL` (đã sang kênh thành công) nhưng ô **NGAY_KENH_TRA để trống** thì kênh thanh toán **chưa thực sự xác nhận** — trước đây chương trình vẫn tự đóng dấu "khớp" cho những lệnh này. Nay lệnh CITAD tương ứng được đưa xuống nhóm **Chỉ CITAD** để anh chị tự xác minh
    + File IPCAS **không có** cột `NGAY_KENH_TRA` (định dạng cũ) thì không bị ảnh hưởng gì
    + ⚠️ **Báo cáo có thể ra nhiều dòng lệch hơn trước** — đây là đúng, không phải lỗi. Số liệu trước và sau mốc này không so sánh trực tiếp với nhau được
    + 🔴 **Điểm cần biết**: nếu bên CITAD **hoàn toàn không có** lệnh đó, thì dòng IPCAS nói trên **biến mất khỏi báo cáo** thay vì hiện ở nhóm *Chỉ Agribank* như trước. Đây lại là ca đáng ngờ nhất (sổ mình ghi đã đi kênh mà NHNN chưa từng thấy lệnh). Ô tổng số dòng IPCAS cũng đếm thiếu tương ứng. Đã ghi nhận để vá ở đợt sau
    + Không đổi cơ sở dữ liệu, không đổi quyền

- 27/08/2026 Menu mới - **Chuẩn hoá văn bản theo Quy định 979 của Tổng Giám đốc**
    + Menu mới **Chuẩn hoá văn bản** ở ngoài cùng sidebar. Tải một file Word lên, hệ thống sửa lại cho đúng *Quy định 979/QyĐ-NHNo-PC về thể thức và kỹ thuật trình bày văn bản*, rồi cho tải bản đã sửa về
    + **Chỉ nhận file `.docx`.** File `.doc` đời cũ thì mở bằng Word, chọn *Lưu thành* `.docx` rồi tải lên — hệ thống báo rõ điều này chứ không để lỗi khó hiểu
    + **Những gì được sửa tự động**: khổ giấy A4 và lề trang (trái 30mm, ba cạnh còn lại 20mm); đánh số trang giữa lề trên và bỏ trang đầu; phông Times New Roman, chữ đen; **giãn dòng 1,2** và cách đoạn 6pt cho phần lời văn, còn khối đầu trang (Quốc hiệu, Tiêu ngữ, tên đơn vị, số ký hiệu, ngày tháng, tên loại, trích yếu) và khối cuối (Nơi nhận, người ký) thì **dòng đơn, không cách đoạn** đúng như mẫu 979; thụt đầu dòng 1cm; **Tiêu ngữ được đưa về đúng dạng "Độc lập - Tự do - Hạnh phúc"** (gạch nối ngắn, mỗi bên đúng một dấu cách — không còn cảnh kéo giãn bằng dấu cách cho bằng dòng Quốc hiệu); **cỡ chữ và kiểu chữ đúng cho từng phần của văn bản** — Quốc hiệu, Tiêu ngữ, tên đơn vị, số ký hiệu, ngày tháng, tên loại, trích yếu, căn cứ, Chương, Mục, Điều, khoản, điểm, Kính gửi, Nơi nhận, chức vụ và họ tên người ký (28 mục, theo Phụ lục III)
    + **Sửa cả cách viết hoa** (Phụ lục IV): viết hoa chữ đầu câu và đầu dòng; khi viện dẫn thì Phần / Chương / Mục / Điều viết hoa còn *khoản*, *điểm* viết thường; và sửa theo **danh sách cụm từ do mình khai** (Nhà nước, Ngân hàng Nhà nước Việt Nam, Ban Kiểm soát, Tổng Giám đốc...)
    + **Sửa cả gạch đầu dòng và đánh số**: mọi ký tự đầu dòng lạ (`•` `–` `*` `+`) đưa về `- `; khoản gõ `1)` hay `1/` đưa về `1.`; điểm gõ `a.` hay `a/` đưa về `a)`; mục La Mã `I)` đưa về `I.`; danh sách chấm tròn tự động của Word đổi thành gạch đầu dòng gõ tay
    + **Cỡ chữ khối đầu văn bản lấy đúng theo mẫu 979**: Quốc hiệu và tên đơn vị cỡ 12, Tiêu ngữ và số ký hiệu cỡ 13, trích yếu công văn cỡ 12. **Nhờ vậy dòng "NGÂN HÀNG NÔNG NGHIỆP VÀ PHÁT TRIỂN NÔNG THÔN VIỆT NAM" không còn bị tràn cột làm chữ "NAM" rớt xuống một dòng riêng**; riêng chữ "Việt Nam" cũng đã được ghim không cho tách đôi
    + **Dòng "Kính gửi" gửi cho MỘT nơi được căn giữa** đúng như mẫu công văn; gửi nhiều nơi (chỉ có chữ "Kính gửi:" rồi liệt kê xuống dòng) thì vẫn để sát trái
    + **Khoảng cách trên/dưới đoạn ở khối đầu văn bản được đưa về 0 và 0** (trước đây file để 7pt/7pt thì khoảng cách thật giữa hai dòng là 14pt, mà hộp Paragraph của Word chỉ hiện hai số 7). Ô bảng ở khối đầu cũng được dọn theo — khối đó hay được dựng bằng bảng hai cột. Bảng số liệu giữa văn bản không bị đụng
    + **Xuống dòng cho đẹp thì không bị viết hoa chữ đầu nữa.** Ví dụ ô "V/v Thông báo thay đổi tên/địa chỉ đăng ký / trên hệ thống SWIFT" — chữ "trên" giữ nguyên chữ thường vì đó là chỗ ngắt dòng cho cân ô, không phải câu mới. Quy tắc: chỉ viết hoa khi đoạn đó là lời văn thật **và** dòng ngay trước đã kết thúc bằng dấu chấm, chấm phẩy hoặc hai chấm
    + **Tên loại văn bản lạ vẫn được căn giữa đúng chỗ**: ĐỀ CƯƠNG, KẾ HOẠCH KIỂM TRA... không nằm trong danh sách tên loại của QĐ 979 nhưng hệ thống vẫn nhận ra qua vị trí (dòng in hoa ngắn nằm ngay dưới số ký hiệu hoặc dòng địa danh - ngày tháng)
    + **Dòng ngày tháng chưa điền vẫn nhận đúng** — "Hà Nội, ngày      tháng      năm 2026" của dự thảo trình ký được căn giữa và in nghiêng như quy định
    + **Cụm từ không bị tách làm hai dòng**: ví dụ chữ *Tổng Giám đốc* sẽ luôn nằm gọn trên một dòng, không còn cảnh "Tổng" ở cuối dòng trên và "Giám đốc" rơi xuống dòng dưới. Danh sách cụm từ tự khai thêm được
    + **Chỗ nào đã sửa đều được bôi màu** để dễ soát lại: **vàng** là sửa định dạng của riêng đoạn đó (cỡ chữ, in đậm, căn lề), **xanh lá** là sửa vào chữ (viết hoa, đánh số, gạch đầu dòng), **xanh ngọc** là cụm từ được ghép cho khỏi tách dòng. Những thứ sửa đồng loạt cả văn bản (giãn dòng, cách đoạn, phông chữ) **không bôi màu** — bôi hết thì cả trang vàng khè, không còn nhìn ra chỗ nào đáng chú ý; chúng được liệt kê riêng trong bảng kết quả
    + **Xem trước rồi mới tải về**: sau khi chạy, màn hình liệt kê từng đoạn đã sửa (số thứ tự đoạn, đoạn đó là phần nào của văn bản, trích nội dung, đã sửa những gì). Đọc thấy đúng ý thì bấm *Tải văn bản đã chuẩn hoá*
    + ⚠️ **Danh sách đánh số tự động của Word được giữ nguyên, có ghi chú nhắc.** Số 1. 2. 3. của loại danh sách này do Word tự tính lúc hiển thị chứ không nằm trong file, hệ thống đọc ra không được nên không dám sửa — sửa mò là lệch số cả văn bản mà không ai biết. Muốn đúng quy định thì gõ số thẳng vào dòng rồi tắt đánh số tự động trong Word
    + ⚠️ **Quy tắc viết hoa tên người, tên địa danh, tên sự kiện thì hệ thống không tự sửa** — những cái đó phải hiểu nội dung câu mới quyết được, máy đoán là sửa hỏng câu chữ của người soạn. Chỉ sửa các cụm từ đã khai sẵn trong danh sách
    + ⚠️ **Bảng số liệu trong văn bản chỉ được đổi phông chữ**, không đụng cỡ chữ và căn lề — quy định cho phép bảng biểu trình bày riêng
    + **Tab *Cấu hình quy chuẩn*** để chỉnh thông số: lề trang, phông chữ, giãn dòng, cách đoạn; cỡ chữ / in đậm / in nghiêng / in hoa / căn lề / thụt dòng cho từng phần văn bản; hai danh sách cụm từ; các công tắc đánh số; màu bôi. Nhập cỡ chữ ngoài dải quy định thì hiện dấu nhắc chứ không chặn. Có nút **Khôi phục mặc định theo QĐ 979**
    + **Phân quyền**: *Chuẩn hoá văn bản (menu)* cho người dùng hằng ngày, và *Sửa thông số quy chuẩn trình bày* cấp riêng — thông số là của cả đơn vị, một người đổi là mọi văn bản người khác chạy sau đó đều theo số mới
    + **Ai không được cấp quyền sửa thông số thì mọi ô trong tab Cấu hình đều bị khoá**, chỉ xem được chứ không gõ vào được. Trước đó chỉ hai nút *Lưu* và *Khôi phục mặc định* bị mờ, còn các ô vẫn gõ được nên dễ tưởng là sửa được — **số liệu thật không hề bị đổi**, vì máy chủ luôn từ chối ghi khi không đủ quyền
    + **File kết quả để trên máy chủ hết ngày làm việc, 23h tự xoá** như các tính năng khác. Cần giữ lâu hơn thì tải về máy mình trong ngày

- 27/08/2026 Chấm 459901 - **Tải lên được cả file Excel, không chỉ file ZIP**
    + **Nhận thêm Excel** (`.xlsx`, `.xlsm`, `.xlsb`, `.xls`) bên cạnh file ZIP xuất từ GL02. Ai đã mở ZIP ra, cắt bớt hay lọc lại rồi lưu thành Excel thì tải thẳng file đó lên, khỏi nén lại
    + **Trộn ZIP với Excel trong cùng một lượt cũng được** — tất cả vẫn được gộp lại rồi mới phân loại, nên cặp lệnh hủy nằm ở hai file khác nhau vẫn bắt được như trước
    + **File Excel có dòng tiêu đề báo cáo ở trên cùng vẫn đọc được**: hệ thống tự tìm dòng tên cột trong 10 dòng đầu, không bắt phải xoá cho sạch mới tải lên
    + **Workbook nhiều sheet thì đọc hết mọi sheet.** Sheet nào thiếu cột bắt buộc sẽ **báo lỗi kèm tên sheet** chứ không âm thầm bỏ qua — thà bị từ chối còn hơn tính thiếu bút toán mà không ai biết. Sheet trống hoàn toàn thì bỏ qua, không kêu
    + **Chọn nhầm file kiểu khác** (PDF, Word, ảnh...) bị chặn **ngay khi bấm chọn**, báo rõ chỉ nhận những đuôi nào — không phải chờ tải lên xong mới biết
    + **Lưu ý khi lưu Excel**: mở file CSV bằng Excel rồi lưu lại thì Excel đổi các ô mã số thành kiểu số. Hệ thống đã xử lý đúng trường hợp này, số tài khoản 459901 không bị đọc thành "459901.0" nữa
    + Cách phân loại Hủy / Đi / Khác **không đổi**, kết quả xuất ra vẫn 3 file Excel như cũ
    + Không đụng cơ sở dữ liệu, không đổi quyền

- 27/08/2026 File tải lên - **File để trên máy chủ hết ngày làm việc, 23h tự xoá sạch**
    + **Trước đây file biến mất giữa giờ làm**: kết quả *Chấm đối chiếu ACH* chỉ sống **4 giờ**, *Chấm 459901* và *Đối chiếu song phương* chỉ **2 giờ**. Chạy buổi sáng, chiều quay lại tải báo cáo thì không còn gì — không thông báo, không dấu vết, người dùng tưởng hệ thống lỗi
    + **Nay giữ hết ngày**: mọi file tải lên và kết quả sinh ra nằm trên máy chủ tới **23h hằng ngày** rồi mới bị xoá sạch. Trong ngày tải lại bao nhiêu lần cũng được. **Cần giữ lâu hơn thì tải về máy mình trong ngày** — hệ thống không lưu lịch sử các lượt chạy này
    + **Máy chủ khởi động lại giữa ngày không làm mất file của ngày hôm đó** — lúc bật lên nó chỉ dọn rác còn sót của những ngày trước
    + **Máy chủ tắt qua đêm cũng không bỏ sót**: lần bật đầu tiên sau đó dọn bù ngay, không đợi tới 23h hôm sau
    + **Nhận file nhẹ hơn hẳn cho máy chủ**: trước đây máy chủ phải ôm trọn bộ file trong bộ nhớ rồi mới ghi xuống ổ đĩa — bộ file 200 MB chiếm tới **400 MB bộ nhớ**. Nay ghi thẳng xuống ổ đĩa từng phần, cùng bộ file đó chỉ còn **2 MB**. Đây chính là nguyên nhân gốc của những lần *"[WinError 10054]"* khi tải bộ file nặng
    + **Đã chặn được cảnh hai người cùng upload đè nhau ở ACH**: máy chủ nay coi là "đang bận" ngay từ giây đầu tiên nhận file, không phải đợi tới lúc bắt đầu chạy. Trước đó suốt vài phút upload là khoảng trống, hai bộ file vài trăm MB cùng lọt vào
    + **Chấm 459901 và Đối chiếu song phương cũng đã chuyển sang cách này** — file tải lên nằm trong `data/temp_cham459901/upload_.../` và `data/temp_doi_chieu_song_phuong/upload_.../` rồi mới được xử lý. Thêm một khoản tiết kiệm nữa: dữ liệu bên trong file ZIP trước đây được **bung hết ra bộ nhớ** rồi mới đọc — một file CSV nén nhỏ nhưng bung ra 114 MB thì chiếm tới **256 MB bộ nhớ**; nay đọc lần lượt từng dòng, chỉ còn **0,1 MB**
    + **Đối soát CITAD**: file tải lên nay nằm trong `data/temp_citad/` của phần mềm thay vì thư mục tạm của Windows — tra lại được khi cần đối chiếu; vẫn xoá ngay sau khi đối soát xong như trước
    + **Đổi lại**: ổ đĩa máy chủ giữ nhiều file hơn trước trong ngày (mỗi lượt ACH khoảng 150–250 MB). Nếu ổ đĩa chật, báo người phát triển để hạ giờ dọn xuống sớm hơn
    + Không đụng cơ sở dữ liệu, không đổi quyền, không đổi cách chạy đối chiếu

- 26/08/2026 Chấm đối chiếu ACH - **Hết lỗi khó hiểu "[WinError 10054]" khi bấm Chạy đối chiếu**
    + **Chuyện gì đã xảy ra**: bộ file ACH chọn lên quá nặng, máy chủ từ chối nhận và **cắt kết nối ngay lúc file đang gửi dở**. Vì bị cắt giữa chừng nên lời từ chối ("file vượt quá dung lượng cho phép") không bao giờ tới được màn hình — trình duyệt chỉ kịp báo một mã lỗi mạng của Windows. Log máy chủ thì vẫn ghi đúng là *vượt dung lượng*, nhưng người dùng không thấy được
    + **Nay chặn ngay trên máy mình, trước khi gửi**: nếu bộ file vượt trần thì hiện thẳng *tổng bao nhiêu MB, trần bao nhiêu MB, và 3 file nặng nhất là file nào* — chưa gửi đi byte nào, không phải ngồi chờ
    + **Dòng "Đã chọn (... file)" nay có thêm tổng dung lượng**, ví dụ *Đã chọn (7 file, 512 MB)* — nhìn là biết mình đang ở đâu so với trần
    + **Trần hiện tại là 500 MB cho cả một lượt.** Bộ file thật vượt mức này thì báo người phát triển — nâng được bằng cấu hình, nhưng cần cân nhắc vì máy chủ phải giữ toàn bộ bộ file trong bộ nhớ khi chạy
    + **Không cho chạy chồng hai phiên nữa** — đây mới là nguyên nhân hay gặp nhất: phiên cũ chưa chạy xong (kể cả đang **chờ xác nhận MIS_đi**) mà upload bộ file phiên mới thì máy chủ phải ôm hai bộ dữ liệu cùng lúc, hết bộ nhớ và **chết ngay giữa lúc đang nhận file**
    + Nay bấm *Chạy đối chiếu* lúc máy chủ còn bận sẽ hiện: **đang chạy phiên nào, mã phiên, bận bao lâu rồi, và phải làm gì** — chưa gửi file đi. Muốn chạy đè thì bấm **Dừng** cho phiên cũ trước
    + **Chốt này nằm ở máy chủ**, không phải ở trình duyệt — nên **F5 hay mở tab mới cũng không lách được**, và người khác đang chạy dở thì mình cũng bị chặn (trước đây trình duyệt chỉ nhớ phiên của chính tab đang mở)
    + **Nút "Dừng" nay dừng cho ra dừng**: bấm xong màn hình báo *đang dừng*, chờ bước đang chạy kết thúc, rồi mới báo **"Đã dừng hẳn. Bộ nhớ đã được giải phóng — chạy phiên mới được rồi"**. Trước đây nó chỉ báo *đã gửi yêu cầu dừng* rồi im, không ai biết dừng thật chưa
    + **Vì sao phải chờ**: lệnh dừng chỉ có hiệu lực ở **ranh giới giữa các bước**. Đang giải nén file MIS thì phải xong chỗ đó mới dừng được — chạy phiên mới lúc đang chờ là máy chủ vẫn ôm hai bộ dữ liệu, đúng cảnh vừa sửa. Hệ thống chờ tối đa **5 phút**; quá đó nó **nói thẳng là chưa dừng được** và khuyên đừng chạy tiếp
    + Máy chủ **thu hồi bộ nhớ ngay** khi phiên kết thúc (dù dừng giữa chừng hay chạy xong), không đợi hệ thống tự dọn
    + **Không tự động ngắt phiên cũ** khi bấm Chạy — phiên đang *chờ xác nhận MIS_đi* thường là có người đang mở file ra điền dở, ngắt ngang là mất công họ
    + Lỡ đóng trình duyệt giữa chừng thì phiên cũ **tự hết hiệu lực sau 4 giờ**, không khoá máy vĩnh viễn
    + Nếu kết nối vẫn đứt vì lý do khác (máy chủ vừa khởi động lại), thông báo cũng được viết lại bằng tiếng Việt thay vì để nguyên mã lỗi
    + Không đụng cơ sở dữ liệu, không đổi quyền, không đổi cách chạy đối chiếu

- 26/08/2026 Menu MỚI - **Ôn tập trắc nghiệm (Quizz)** — ôn thi nghiệp vụ ngay trên hệ thống
    + **Vào bằng**: menu **Ôn tập trắc nghiệm** ở thanh bên trái (nằm dưới *Danh sách CN TTQT*). **Phải được cấp quyền mới thấy menu** — báo quản trị viên thêm vào nhóm quyền tương ứng
    + **Bộ câu hỏi chỉ cần tải lên MỘT lần cho cả cơ quan.** Người vào sau chỉ việc chọn bộ có sẵn rồi bấm *Bắt đầu*, không phải tải lại file lần nào nữa
    + **File Excel để tải lên** phải đúng thứ tự cột: *Câu hỏi | Đáp án 1 | Đáp án 2 | Đáp án 3 | Đáp án 4 | Đáp án đúng*. Ô *Đáp án đúng* ghi **số 1, 2, 3 hoặc 4** (không ghi A/B/C/D). Câu chỉ có 3 lựa chọn thì **bỏ trống ô Đáp án 4**. Có sẵn nút **Tải file mẫu** để lấy đúng khuôn
    + **Dòng nào sai thì bỏ dòng đó và báo rõ số dòng** để mở Excel sửa, phần còn lại vẫn nhập bình thường. Hệ thống **không tự đoán đáp án** — thà thiếu một câu còn hơn để người ôn nhớ sai
    + **Không tải lên trùng được**: trùng tên bộ, hoặc trùng **nội dung câu hỏi** với bộ đã có, đều bị chặn và báo tên bộ cũ để đi tìm. Đổi tên file, hay mở file ra xem rồi bấm lưu, đều không lách được — hệ thống so nội dung chứ không so file
    + **Cài đặt trước mỗi lần làm bài**:
        - **Chế độ** — *Ôn tập* (hiện đáp án đúng ngay sau khi chọn, để học) hoặc *Thi thử* (chỉ chấm khi nộp bài)
        - **Số câu** — 10 / 20 / 30 / 50 / 100 hoặc lấy hết bộ
        - **Trộn thứ tự câu hỏi** và **trộn thứ tự đáp án** — bật/tắt riêng
        - **Thời gian mỗi câu** — 10 đến 90 giây, hoặc không giới hạn. Hết giờ tự sang câu kế
        - **Tổng thời gian làm bài** — 5 đến 90 phút, hoặc không giới hạn. Hết giờ hệ thống **tự nộp bài**
    + **Màn làm bài chiếm cả màn hình** (không có thanh menu bên trái): câu hỏi ở giữa, 4 ô đáp án màu to bên dưới, thanh tiến trình và hai đồng hồ ở trên. Có nút *Bỏ qua câu này* và nút thoát (hỏi lại trước khi thoát)
    + **Nộp bài xong hiện ngay**: điểm phần trăm, số câu **đúng / sai / bỏ trống** (bỏ trống tách riêng khỏi sai, để biết mình *không kịp* hay *không biết*), thời gian làm bài, và phần **Xem lại bài** từng câu — tô xanh đáp án đúng, tô đỏ ô mình đã chọn sai
    + **Lịch sử của tôi**: 30 lượt gần nhất, bấm vào xem lại nguyên bài đã làm
    + **Bảng xếp hạng** theo từng bộ (biểu tượng cúp trên thẻ bộ câu hỏi): mỗi người lấy lượt tốt nhất, cùng điểm thì ai làm nhanh hơn đứng trên. **Chỉ tính bài Thi thử** — chế độ Ôn tập hiện sẵn đáp án nên ai cũng 100%, đưa vào bảng thì bảng mất ý nghĩa
    + ⚠️ **Xoá một bộ câu hỏi là xoá luôn toàn bộ lượt làm bài của mọi người và bảng xếp hạng của bộ đó**, không lấy lại được. Vì vậy quyền *Xoá bộ câu hỏi* tách riêng, không đi kèm quyền tải lên
    + **Tạm dừng và làm tiếp** — *bổ sung 27/08*:
        - **Bài làm được lưu tự động sau mỗi câu trả lời**, không đợi tới lúc bấm *Nộp bài*. Mất mạng, máy ngủ, tắt máy giữa chừng hay lỡ đóng tab đều **không mất bài**
        - Vào lại menu *Ôn tập trắc nghiệm*, thẻ của bộ đó hiện nút **Làm tiếp** kèm dòng *"Đang dở — đã trả lời X/Y câu"*. Bấm vào là quay lại **đúng câu đang làm**, giữ nguyên các đáp án đã chọn và thời gian đã dùng
        - Nút **Tạm dừng** ở góc trên bên phải màn làm bài: lưu lại rồi về danh sách. Cạnh đồng hồ có chỉ báo nhỏ *✓ đã lưu* / *⚠ chưa lưu* để biết bài mình có đang được giữ hay không
        - **Đồng hồ dừng khi tạm dừng** — nó đếm thời gian *làm bài*, không phải thời gian trôi ngoài đời. Nghỉ trưa hai tiếng rồi vào làm tiếp không bị mất giờ
        - **Mỗi người mỗi bộ chỉ giữ một bài dở.** Muốn làm lại từ đầu thì vào menu ⋮ trên thẻ, chọn *Bắt đầu bài mới* — hệ thống báo trước là bài dở cũ sẽ bị bỏ. Cũng ở menu đó có *Bỏ bài đang làm dở*
        - ⚠️ Bài bỏ dở **không tính điểm và không lên bảng xếp hạng** cho tới khi bấm *Nộp bài*
    + **Cơ sở dữ liệu thêm 3 cột** vào bảng lượt làm bài, tự thêm lúc khởi động — không phải làm gì thêm, dữ liệu cũ giữ nguyên
    + **Không làm chậm hệ thống, không làm ngập Nhật ký thao tác** — đã đo trên bản sao cơ sở dữ liệu thật:
        - 20 người ôn tập cùng lúc: các màn hình khác vẫn chạy như cũ (truy vấn báo cáo 0,2 ms trước và sau, không đổi)
        - Dung lượng: một bộ 550 câu tốn 280 KB (nhập một lần); mỗi lượt làm bài cỡ 20 câu tốn dưới 1 KB
        - **Việc lưu tiến độ KHÔNG ghi vào Nhật ký thao tác.** Nếu ghi thì một bài 550 câu để lại 550 dòng và nhật ký của các phần khác bị đẩy trôi. Những việc cần tra sau này — ai tải bộ câu hỏi lên, ai đổi tên, ai xoá bộ, ai nộp bài — thì **vẫn ghi đầy đủ**
    + **Ba quyền cần khai báo cho nhóm**: *Ôn tập trắc nghiệm (menu)* — vào module và làm bài; *Tải bộ câu hỏi lên / đổi tên bộ*; *Xoá bộ câu hỏi*
    + **Cơ sở dữ liệu có thêm 4 bảng mới**, tự tạo lúc khởi động — không phải làm gì thêm. Không đụng tới dữ liệu sẵn có
    + Thêm 31 test tự động cho phần này. Toàn bộ **804 test** chạy đạt. Đã thử nhập đúng file *1. Kiến thức chung Đợt II.2026.xlsx*: **550/550 câu vào sạch, không dòng nào lỗi**

- 25/08/2026 Giao diện - **Trang Đăng nhập và Trang chủ đổi sang chủ đề kỷ niệm 2-9**
    + **Tự bật từ 25/8, tự tắt sau ngày 3/9** — không ai phải làm gì để gỡ sau lễ, và sang năm tự bật lại. Ngoài khoảng ngày này hai trang y hệt như cũ
    + **Trang Đăng nhập**: nền đỏ cờ bừng sáng quanh ô đăng nhập rồi sẫm dần ra rìa, dải cờ đỏ - vàng trên đỉnh trang, ngôi sao vàng lớn mờ làm hoạ tiết, khẩu hiệu chào mừng đặt phía trên ô đăng nhập
    + **Trang chủ**: nền ấm dần lên phía trên (đáy vẫn giữ màu cũ để bảng số và biểu đồ dễ đọc), thêm dải khẩu hiệu hai dòng ngay dưới tiêu đề
    + **Khẩu hiệu**: *NHIỆT LIỆT CHÀO MỪNG 81 NĂM CÁCH MẠNG THÁNG TÁM THÀNH CÔNG (19/8/1945 - 19/8/2026) VÀ QUỐC KHÁNH NƯỚC CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM (2/9/1945 - 2/9/2026)!* — số năm tự tính, sang năm không phải sửa
    + **Chỉ đổi hai trang này.** Các màn hình khác và thanh menu bên trái giữ nguyên màu — trong dịp lễ, rời Trang chủ sang màn khác sẽ thấy nền trở lại như thường
    + **Không đụng cơ sở dữ liệu, không đổi quyền, không đổi thao tác nào.** Máy không vào được internet vẫn hiển thị đủ: mọi hoạ tiết đều vẽ tại chỗ, không tải ảnh từ ngoài

- 25/08/2026 Bàn giao chứng từ - **Xoá ô chứng từ đã xác nhận: bắt nhập lý do và ghi lại vào Nhật ký thao tác**
    + **Trước đây xoá một ô đã xác nhận không để lại dấu vết ở đâu cả**: người có quyền xác nhận chỉ cần xoá trắng ô rồi bấm Lưu — số liệu và cả lịch sử sửa đổi riêng của ô đó biến mất cùng lúc. Nhật ký thao tác vẫn có một dòng, nhưng nội dung y hệt một lần sửa số tờ bình thường, không phân biệt được
    + **Nay bắt buộc nhập lý do** khi xoá ô đang ở trạng thái *Đã xác nhận* hoặc *Đang mượn*. Ô chưa xác nhận (hoặc bị trả lại) vẫn xoá bình thường như cũ, không hỏi gì
    + **Nhật ký thao tác ghi lại đủ**: ai xoá, xoá ô của giao dịch viên nào, ngày nào, bao nhiêu tờ, phòng nào, trạng thái trước khi xoá, và lý do — đọc một dòng là hiểu chuyện gì đã xảy ra
    + **Màn Nhật ký thao tác có thêm cột "Chi tiết"**: hiện nội dung của những thao tác có ghi chi tiết. Các dòng máy tự ghi (chỉ có mã kết quả HTTP) để trống cột này cho khỏi rối mắt
    + Không đụng cơ sở dữ liệu, không phải khai báo quyền lại
- 25/08/2026 Đối chiếu CITAD - **Đã vá 2 lỗi ở ô *Lập bảng* / *Kiểm soát* cảnh báo hôm 23/08 (PR#56)**:
    + ✅ **Mở lại bảng cũ không còn mất tên người ký nữa.** Tên của người đã nghỉ, đã chuyển phòng, hay
      gõ tay kiểu khác đều hiện đúng như lúc lưu. **Bấm *Lưu* lúc này đã an toàn** — cảnh báo "thấy ô
      trống bất thường thì đừng bấm Lưu" ở mục 23/08 bên dưới **không còn hiệu lực**
    + ✅ **Xuất Excel không còn báo lỗi khi để trống cả hai ô.** Không phải gõ dấu gạch để lách nữa
    + **Tab *Lịch sử* nay hiện đúng người đã bấm Lưu ở từng dòng.** Trước đây mọi dòng của một ngày đều
      mang tên người lập bảng, ai vào bổ sung Napas / PSS - MDP cũng không thấy tên mình. Nay **mỗi
      người bấm Lưu là một dòng riêng**, nên **số dòng và cột *Số lần lưu* sẽ nhiều hơn trước** — không
      phải hệ thống đếm nhầm
    + ⚠️ **Ngày đã chốt bản cuối vẫn có thể còn vài dòng ghi "Tạm" nằm phía trên dòng "Chính thức".**
      Đó là các lần lưu tạm của từng người, được giữ lại làm dấu vết — dòng cuối cùng mới là bản đang
      dùng, có nhãn *Bản hiện hành*
    + ⚠️ **Ô lọc *Tên người chấm* vẫn chỉ tìm theo người lập bảng.** Gõ tên người chỉ bổ sung Napas /
      PSS - MDP sẽ **không ra ngày nào** — phải bấm vào ngày để bung danh sách ra mới thấy tên họ.
      Chưa sửa vì đổi cách tìm là đổi nghiệp vụ, cần Phòng Thanh toán chốt trước
    + Không đổi cơ sở dữ liệu, không phải khai báo quyền lại

- 25/08/2026 Đối soát CITAD ↔ IPCAS - **Sửa lỗi đọc SAI số tiền khi file IPCAS đã bị Excel lưu đè (đã merge PR#58)**
    + 🔴 **Nguyên nhân — Phòng Thanh toán tự phát hiện**: mở file CSV của IPCAS bằng Excel (chỉ để xoá thử 1 dòng) rồi lưu lại. Excel **tự động** đổi mọi số tiền đủ lớn — từ khoảng 100 tỷ trở lên, đúng nhóm giá trị **cao** (IH) — sang kiểu viết tắt `5.53722E+11`. Số nhỏ (nhóm **thấp**/IL) không đủ lớn nên không bị đổi, đúng khớp hiện tượng quan sát được *"chỉ nhóm cao mới lệch, nhóm thấp thì không"*
    + **Chương trình đọc sai hoàn toàn**: cách đọc cũ gom hết chữ số lại, `5.53722E+11` thành **55.372.211 đồng** thay vì **553.722.000.000 đồng** — cái đuôi `11` chính là phần `E+11` bị dính vào. Nay đọc đúng
    + **Đo trên dữ liệu thật**: file gốc ngày 19/08 (chưa ai mở bằng Excel) **không đổi gì** — vẫn 38.129 khớp / 14 lệch, đúng như cũ. File ngày 24/08 đã bị Excel lưu đè: **42.549 khớp / 120 lệch → 42.563 khớp / 92 lệch**
    + 🔴 **92 dòng lệch còn lại KHÔNG phải lỗi chương trình và không sửa được**: lúc Excel đổi sang kiểu viết tắt, nó **chỉ giữ khoảng 6 chữ số đầu**, các chữ số sau bị làm tròn thành 0 **ngay trong file** — đã xác nhận bằng cách đọc thẳng nội dung file. Số tiền thật đã mất, chương trình đọc kiểu gì cũng không lấy lại được
    + ⚠️ **Việc cần làm từ nay — quan trọng hơn cả bản vá**: **không mở file CSV của IPCAS bằng Excel rồi bấm lưu**, kể cả chỉ mở ra xem. Cần xem thì mở bằng Notepad, hoặc mở bằng Excel nhưng **thoát ra không lưu**. Lỡ lưu rồi thì **tải lại file gốc từ IPCAS**, đừng chấm bằng file đó
    + ⚠️ **Chương trình chưa biết tự cảnh báo** khi gặp file đã bị hỏng kiểu này — nó vẫn chấm bình thường và cho ra vài chục dòng lệch không giải thích được. Gặp tình huống "tự nhiên nhiều dòng lệch ở nhóm giá trị cao" thì nghĩ ngay tới nguyên nhân này trước. Đã ghi lại để người phát triển vá đợt sau
    + **Không đụng cơ sở dữ liệu, không phải khai báo quyền lại.** Lưu ý: các lần chấm **đã lưu trong tab Lịch sử trước hôm nay vẫn giữ nguyên số cũ (sai)** — lịch sử là ảnh chụp tại thời điểm chấm, không tính lại. Cần số đúng thì chấm lại bằng file gốc
    + Thêm 4 test tự động. Toàn bộ **725 test** chạy đạt sau khi merge (đo lại trên đúng bản đã merge, không có test nào lỗi)
    + 🟡 **5 điểm review CHƯA sửa, để người phát triển xử lý sau** (chi tiết + cách sửa đã đo ở `docs/Implementation-notes.html` card 107): ô Excel kiểu số cho ra số **sai gấp 10 lần**; số tiền lẫn đơn vị (`5.53722E+11 VND`) rơi lại về lỗi cũ; số âm dạng viết tắt nay đi lọt; codebase đang có **3 luật đọc số tiền khác nhau** ở 3 module; và thiếu cảnh báo file hỏng nói trên

- 25/08/2026 Đối chiếu CITAD - PaymentHub - **Màn hình MỚI cho Phòng QLTK Nostro, Vostro (đã merge PR#57)**
    + **Vào bằng**: Đối chiếu → Phòng QLTK Nostro, Vostro → Đối chiếu CITAD - PaymentHub. **Phải được cấp quyền mới thấy menu** — báo quản trị viên thêm vào nhóm quyền tương ứng
    + **Đây là màn hình riêng, không liên quan gì tới màn "Đối chiếu CITAD" của Phòng Thanh toán**: số liệu lấy từ trang khác (CITAD lấy ở **"Tra cứu dữ liệu"**, chỉ chiều **Đi**, chỉ **giao dịch thành công**; PaymentHub lấy dòng **Tổng cộng** ở trang "Lập bảng kê phí chia sẻ CITAD"). Hai phòng không nhìn thấy và không ghi đè số liệu của nhau
    + **Chấm gộp được nhiều ngày**: chọn Từ ngày – Đến ngày thay vì mỗi ngày một bản. Khi bấm Lưu, máy **cảnh báo** nếu kỳ vừa chọn trùng ngày với kỳ đã chấm trước đó, hoặc bỏ sót ngày ở giữa — **chỉ cảnh báo, vẫn cho lưu**, quyết định là ở người chấm
    + **Tiện ích lấy số liệu tự động (Extension) là bản RIÊNG**, tải ngay trên màn hình ở tab "Kết nối Extension". ⚠️ **Không dùng chung với Extension của Phòng Thanh toán** — ai đang dùng bản kia thì cài thêm bản này, hai bản chạy song song được, không phải gỡ bản cũ
    + **Cột "người chấm" trong tab Lịch sử là người LẬP BẢNG** (người lưu đầu tiên của kỳ đó), không đổi khi người khác lưu đè sau — để biết ai phụ trách kỳ đó, không phải ai bấm Lưu gần nhất
    + Thêm 2 bảng mới trong cơ sở dữ liệu, **không sửa/xoá bảng cũ nào** — các màn hình đang dùng không bị ảnh hưởng
    + ⚠️ **Chưa thử được trên máy trong mạng nội bộ Agribank**: phần tự động lấy số liệu từ trang CITAD/PaymentHub thật chưa chạy thử lần nào (môi trường phát triển không vào được mạng nội bộ). **Lần đầu dùng nên đối chiếu lại vài số với bản chấm tay** trước khi tin hoàn toàn. Nếu số không lên, vẫn **gõ tay bình thường** được — mọi ô đều nhập tay được
    + **6 lỗi đã tìm ra và vá trước khi merge** (chi tiết kỹ thuật ở `docs/Implementation-notes.html` mục Z9), trong đó đáng chú ý với người dùng:
        * **Tab Lịch sử bị sập** (trang trắng) nếu gõ ngày sai kiểu vào ô lọc — ví dụ gõ dở `01/08` rồi bấm Tìm. Nay gõ sai chỉ là không lọc, không sập
        * **Tiện ích lấy số liệu gửi hỏng mà không báo gì**: mã kết nối hết hạn / mất mạng thì im lặng hoàn toàn, người dùng tưởng đã lưu xong. Nay **luôn hiện thông báo** — đỏ nghĩa là mã kết nối hỏng phải tạo lại, vàng nghĩa là mạng lỗi và máy sẽ tự thử lại
        * **Lưu được kỳ trống** (xoá trắng ô ngày rồi bấm Lưu) tạo ra bản ghi không hiện ra ở đâu mà cũng không xoá được. Nay bắt buộc nhập đủ Từ ngày – Đến ngày
        * **File Excel xuất ra gọi tên cổng khác với màn hình** (Excel ghi "Cổng 1", màn hình ghi "Cổng 001"). Nay hai nơi gọi giống nhau
    + Thêm **19 test tự động** cho module này (PR gửi lên ban đầu không có test nào). Toàn bộ **732 test** chạy đạt sau khi merge

- 24/08/2026 Đối soát CITAD ↔ IPCAS - **Đã merge PR#55 vào develop (các mục 23/08 bên dưới nay đã lên bản chính)**
    + **Gộp chung 6 đợt sửa ghi ở dưới**: bắt được IPCAS/Hub hạch toán trùng, loại cặp hạch toán nhầm-huỷ theo REFHUB, lệnh chuyển chi nhánh chỉ tính dòng gốc, sửa cột Ngày GD / STT / Số tiền trong file "Tất cả lệnh", thêm 41 test tự động cho phần đối soát (trước đây không có test nào)
    + ⚠️ **Từ hôm nay báo cáo có thể NHIỀU dòng lệch hơn trước, và đó là đúng.** Lệnh Đến trạng thái **PYED/PYEK** trước đây được bỏ qua khi tính dư, nay không khớp CITAD là **vẫn hiện**. Vì vậy **số liệu trước và sau mốc 24/08/2026 không so sánh trực tiếp được** — không phải hệ thống hỏng
    + ⚠️ **Chọn nhầm trùng file nay hậu quả nặng hơn nhiều.** Hộp cảnh báo "trùng nội dung file" vẫn chỉ là cảnh báo, bấm qua được — nhưng nếu bấm qua, **mỗi dòng trong file sẽ đẻ 1 dòng lệch giả** (trước đây bị lọc âm thầm). Thấy hộp cảnh báo đỏ thì nên xoá bớt file rồi chọn lại từ đầu
    + 🔴 **Hai lỗi đã biết khi merge, CHƯA vá — đọc kỹ trước khi tin dòng lệch**:
        * **Có thể hiện dòng "Chỉ IPCAS" GIẢ ở lệnh ĐI**, khi hai lệnh Đi khác nhau tình cờ trùng mã TXID và trùng cả số tiền / ngân hàng nhận / trạng thái / ngày. Dấu hiệu nhận ra: dòng lệch ghi *"1 trong 2 lần IPCAS ghi nhận lệnh này"* nhưng tra lại IPCAS chỉ thấy đúng 1 bút toán
        * **Có thể hiện dòng "Chỉ Hub" GIẢ** nếu file Hub ngoại tệ không có cột *Trạng thái* (hoặc cột đó đổi tên) — lúc đó lệnh chuyển chi nhánh bị hiểu nhầm thành ghi trùng
        * Cả hai chờ người phát triển vá ở đợt sau. Trong lúc chờ: **gặp dòng "Chỉ IPCAS"/"Chỉ Hub" kèm ghi chú "N lần" thì tra lại IPCAS/Hub trước khi báo lệch cho đối tác**. Chi tiết kỹ thuật + cách sửa đã đo ở `docs/Implementation-notes.html` card 106
    + Không đổi cơ sở dữ liệu, không phải khai báo quyền lại. Toàn bộ **702 test** chạy đạt sau khi merge

- 23/08/2026 Đối soát CITAD↔IPCAS - **Sửa lại theo review PR#55 (Người 1): fix căn lề STT/Số tiền hôm qua làm xuất "Tất cả lệnh" chậm gấp 3 lần**:
    + ⚠️ **Người 1 đo lại bằng cProfile trên PR**: cách sửa căn lề 2 cột STT/Số tiền (đợt trước) làm xuất "Tất cả lệnh" chậm từ 6,19 giây lên **18,94 giây (gấp 3,1 lần)** — comment lúc đó viết "không đánh đổi tốc độ xuất" nhưng chưa đo lại thật
    + **Nguyên nhân**: cách sửa cũ gán CẢ font+nền+viền+căn lề (4 thuộc tính) cho 2 ô đó, trong khi chỉ cần đúng căn lề + dấu phẩy — mỗi lượt gán thêm là 1 lượt máy phải so khớp kiểu dáng với bảng kiểu dùng chung của cả file, tốn thời gian
    + **Vì sao đáng lo**: hàm xuất này chỉ có 4 "chỗ" xử lý việc nặng dùng chung cho CẢ hệ thống (nghỉ phép, in bìa, ACH, SWIFT...) — chậm gấp 3 lần nghĩa là giữ mất 1 trong 4 chỗ đó lâu gấp 3 lần, 2 người xuất cùng lúc sẽ chiếm gần hết, người khác đang thao tác việc nặng khác sẽ thấy đơ mà không hiểu vì sao
    + **Đã sửa**: chỉ gán đúng căn lề + dấu phẩy cho 2 ô này, bỏ hẳn font/nền/viền không cần thiết. Đo lại trên dữ liệu thật 19/08/2026: **5,22 giây** — còn nhanh hơn cả trước khi có đợt sửa nào, không còn ảnh hưởng gì
    + Không đổi giao diện file xuất, không cần sửa test — toàn bộ 41 test vẫn pass

- 23/08/2026 Đối soát CITAD↔IPCAS - **Sửa 2 lỗi hiển thị thật trong file xuất "Tất cả lệnh": cột Ngày GD trống ở dòng gốc CITAD, cột Số tiền căn lề/định dạng khác nhau giữa dòng khớp và dòng lệch**:
    + ⚠️ **Phòng Thanh toán phát hiện qua ảnh chụp file Excel thật**: cột "Số tiền" ở phần dòng đã khớp căn PHẢI và không có dấu phẩy ngăn cách hàng nghìn, trong khi phần dòng lệch căn TRÁI và có dấu phẩy — nhìn không thống nhất giữa 2 phần
    + **Nguyên nhân xác nhận bằng cách mổ trực tiếp file XML xuất ra**: để xuất nhanh cho ~38.000 dòng khớp, code ghi giá trị thô không style riêng từng ô, định dạng đặt ở CẤP CỘT — nhưng Excel KHÔNG áp dụng định dạng cấp cột cho ô đã có giá trị ghi vào (chỉ áp cho ô thật sự trống), nên các ô này rơi về định dạng mặc định của Excel (số thì căn phải, không dấu phẩy)
    + **Cùng lúc phát hiện thêm**: cột "Ngày GD" luôn TRỐNG ở mọi dòng có gốc CITAD (dòng khớp, dòng Chỉ CITAD) — vì file CITAD không có cột ngày riêng cho từng dòng (chỉ ghi 1 lần ở đầu file, áp dụng chung), khác dòng Chỉ IPCAS có ngày riêng nên hiện bình thường — tạo cảm giác 2 phần "lệch cột" khi xem
    + **Đã sửa**: cột Ngày GD nay hiện đúng ngày đang chấm khi CITAD không có ngày riêng (mọi dòng trong 1 lần chấm luôn cùng 1 ngày, không mơ hồ); cột Số tiền ở dòng khớp được style riêng (căn trái + dấu phẩy) giống hệt dòng lệch — chỉ đúng 1 cột này, KHÔNG style lại cả 13 cột để giữ tốc độ xuất (đổi tốc độ ~10 lần chỉ để đồng bộ toàn bộ cột là không đáng, theo lựa chọn của Phòng Thanh toán)
    + **Phát hiện tiếp cùng gốc lỗi**: cột "STT" ở dòng khớp cũng bị y hệt vấn đề trên (là số nguyên nên Excel tự căn PHẢI thay vì GIỮA như ý định) — sửa cùng cách, style riêng đúng ô STT cho dòng khớp
    + Thêm 4 test mới (file test riêng cho `exporters.py`, ghi file Excel thật rồi đọc lại kiểm tra, không mock) — toàn bộ **41 test** pass

- 23/08/2026 Đối soát CITAD↔IPCAS - **Rà soát lại toàn bộ sau các sửa hôm nay: sửa 1 câu ghi chú viết cứng sai khi CITAD tự trùng khoá thật, chưa từng ảnh hưởng dữ liệu đã chấm**:
    + ⚠️ **Phát hiện qua tự rà soát** (theo yêu cầu kiểm tra lại toàn bộ đối soát): câu ghi chú trên dòng ĐÃ khớp khi báo "nguồn đối ứng ghi nhận trùng" luôn viết cứng "chỉ tính khớp 1 lần" — đúng với lệnh Đi nhưng SAI với lệnh Đến/ngoại tệ khi CITAD cũng tự trùng khoá thật (đã xác nhận có thật, xem mục sửa lỗi tính dòng thừa phía dưới): ví dụ CITAD trùng 2 dòng thật + IPCAS trùng 3 dòng sẽ hiện sai "chỉ tính khớp 1 lần — xem thêm 2 dòng" thay vì đúng "khớp 2 lần — xem thêm 1 dòng"
    + **Không ảnh hưởng số liệu tổng** (khớp/lệch vẫn đúng, chỉ câu chữ giải thích sai) — kiểm dữ liệu thật 19/08/2026: không có trường hợp nào rơi đúng vào tình huống này nên báo cáo hôm nay không sai
    + **Đã sửa**: câu ghi chú giờ dùng đúng số dòng CITAD thật khớp được, không còn viết cứng là 1
    + Thêm 1 test khoá lại — toàn bộ **32 test** pass, số liệu thật không đổi (38.129 khớp / 14 lệch)

- 23/08/2026 Đối soát CITAD↔IPCAS - **Tìm ra và loại đúng nguyên nhân của phần lớn dòng "Chỉ IPCAS" đang bị báo hôm nay: GDV hạch toán thủ công nhầm chi nhánh, phải huỷ rồi hạch toán lại**:
    + ⚠️ **Phòng Thanh toán tự tìm ra nguyên nhân** khi soi lại 1 trong các nhóm bị báo lệch bằng Excel: lệnh Đến được GDV hạch toán thủ công NHẦM chi nhánh, phải HUỶ bút toán đó rồi hạch toán lại thủ công đúng nơi — bút toán HUỶ dùng LẠI đúng số phiếu ghi sổ (trace) của bút toán bị huỷ (2 dòng cùng chi nhánh, cùng trace), còn bút toán hạch toán lại ĐÚNG luôn có số trace MỚI (có thể ở chi nhánh khác). Đây chính là nguyên nhân thật của hiện tượng "trùng trace" đã phát hiện hôm qua — không phải IPCAS ngẫu nhiên cấp trace khác nhau, mà là 1 quy trình sửa sai có chủ đích của GDV
    + **Kiểm lại cả 5 nhóm đang bị báo "Chỉ IPCAS" hôm nay**: cả 5/5 đều đúng mẫu này (2 dòng trùng chi nhánh+trace, 1 dòng trace riêng) — nghĩa là cả 5 nhóm không phải chênh lệch thật, chỉ là dấu vết của việc sửa sai thao tác, không cần Phòng Thanh toán kiểm tra lại nữa
    + **Đã thêm**: đọc thêm cột "REFHUB" (mã tham chiếu điện đến gốc, duy nhất cho mỗi lệnh thật, không bị trùng lặp giữa các lệnh khác nhau như TXID) để xác định chắc chắn nhiều dòng có phải cùng 1 lệnh gốc hay không, trước khi áp dụng quy tắc loại cặp trùng chi nhánh+trace
    + **An toàn**: nếu 1 lệnh có TẤT CẢ các dòng đều trùng chi nhánh+trace (không tìm được dòng nào là bút toán đúng cuối cùng) thì KHÔNG loại gì cả, vẫn báo lệch như trước — theo xác nhận của Phòng Thanh toán, trường hợp này không xảy ra trong thực tế, chỉ là chốt an toàn
    + **Kết quả trên dữ liệu thật 19/08/2026**: số lệch giảm từ 24 xuống còn **14** (13 Chỉ IPCAS + 1 Chỉ CITAD), số khớp giữ nguyên 38.129 — đúng 10 dòng vừa loại là 5 nhóm × 2 dòng thừa mỗi nhóm
    + Thêm 3 test khoá lại (kể cả ca dòng đúng ở chi nhánh khác, và ca an toàn không có dòng nào đúng) — toàn bộ **32 test** pass

- 23/08/2026 Đối soát CITAD↔IPCAS - **Sửa lỗi tính SAI số dòng "IPCAS/Hub ghi nhận trùng" khi CITAD cũng tự trùng khoá thật (chưa từng xảy ra trên dữ liệu đã chấm, nhưng có thể xảy ra)**:
    + ⚠️ **Phát hiện qua câu hỏi trực tiếp của Phòng Thanh toán**: "lệnh lệch có chắc CITAD không có không, nếu các lệnh giống hệt nhau nhưng có đủ ở cả CITAD và IPCAS thì không phải lệch". Kiểm tra lại code phát hiện: khi tính số dòng "Chỉ IPCAS"/"Chỉ Hub" do nguồn đối ứng ghi nhận trùng, phần mềm LUÔN giả định CITAD chỉ có đúng 1 lệnh cho mỗi mã giao dịch — đúng với lệnh Đi (VNĐ) nhưng KHÔNG đúng với lệnh Đến (VNĐ) và ngoại tệ (Hub), 2 loại này CITAD được phép tự trùng mã thật (đã xác nhận 1.154 nhóm trùng thật riêng ngày 19/08/2026)
    + **Ví dụ cụ thể lỗi cũ**: CITAD trùng 2 dòng thật + IPCAS trùng 3 dòng cho cùng 1 lệnh → phần mềm cũ báo dư SAI 2 dòng (3-1, coi CITAD chỉ có 1) thay vì ĐÚNG 1 dòng (3-2), kèm ghi chú sai "CITAD chỉ có 1 lệnh" dù CITAD thật có 2
    + **Đã kiểm lại toàn bộ dữ liệu 19/08/2026**: không có ca nào rơi vào đúng tình huống lỗi (24 dòng lệch hôm nay đều ứng với CITAD có 0 hoặc 1 dòng, không có dòng nào CITAD có ≥2) — số liệu báo cáo hôm nay KHÔNG đổi (38.129 khớp / 24 lệch), nhưng lỗi có thật và cần sửa trước khi gặp phải trong dữ liệu ngày khác
    + **Đã sửa**: đếm đúng số dòng CITAD thật theo từng mã giao dịch thay vì giả định luôn là 1, áp dụng cho cả VNĐ Đến lẫn ngoại tệ (Hub)
    + Thêm 1 test khoá lại đúng ca lỗi (CITAD trùng 2, IPCAS trùng 3 → dư đúng 1) — toàn bộ 29 test pass

- 23/08/2026 Đối soát CITAD↔IPCAS - **Rà soát cuối ngày: sửa 1 lỗi có sẵn từ trước (không phải do các sửa hôm nay), không ảnh hưởng ngày nào đã chấm bằng VNĐ thuần tuý**:
    + ⚠️ **Lỗi tìm được**: khi 1 ngày chấm có CẢ lệnh VNĐ lẫn lệnh ngoại tệ (USD/EUR), nếu 1 mã số giao dịch VNĐ trùng ngẫu nhiên với 1 mã số giao dịch ngoại tệ (2 hệ đánh số hoàn toàn độc lập với nhau, trùng số là chuyện ngẫu nhiên có thể xảy ra), lệnh IPCAS thật của bên VNĐ có thể **biến mất hoàn toàn khỏi báo cáo** — không khớp, không "Chỉ IPCAS". Lỗi này có sẵn trong phần mềm từ trước, không phải do các lần sửa trong ngày hôm nay gây ra — chỉ tình cờ chưa gặp phải vì dữ liệu dùng để kiểm tra suốt hôm nay chỉ có lệnh VNĐ, không có lệnh ngoại tệ
    + **Đã sửa**: tách riêng việc theo dõi "lệnh nào đã khớp" cho VNĐ và ngoại tệ, không dùng chung nữa
    + **Đồng thời sửa cho nhất quán**: dòng "lệch trạng thái" (khớp được số hiệu nhưng IPCAS chưa xác nhận thành công) giờ cũng ghi rõ khi IPCAS có dữ liệu trùng, giống như dòng đã khớp hoàn toàn — trước đây chỉ dòng khớp hoàn toàn mới có ghi chú này
    + Thêm 2 test khoá lại — toàn bộ 28 test pass. Đã kiểm lại dữ liệu thật 19/08/2026: số liệu không đổi (38.129 khớp / 24 lệch), đúng như dự kiến vì ngày này chỉ có lệnh VNĐ

- 23/08/2026 Đối soát CITAD↔IPCAS - **Sửa tiếp: các lệnh "IPCAS hạch toán trùng" phát hiện hôm nay thực ra bị đếm THIẾU (trùng 3 lần, báo có 2)**:
    + ⚠️ **Phát hiện qua tự kiểm thử của Phòng Thanh toán**: xoá thử 1 dòng trong 1 nhóm trùng IPCAS để kiểm tra lại, phát hiện nhóm đó thực ra có 3 dòng, không phải 2. Kiểm lại toàn bộ: **cả 5 nhóm đã báo trùng hôm nay đều bị thiếu đúng 1 dòng** — dòng thứ 3 giống hệt mọi thông tin (chi nhánh, ngân hàng, trạng thái, ngày, số tiền) nhưng có 1 số phiếu ghi sổ (trace) khác, nên bị máy hiểu nhầm là "khác nhau" và **biến mất hoàn toàn** khỏi báo cáo — không khớp, không "Chỉ IPCAS", không hiện ở đâu cả
    + **Đã sửa**: số phiếu ghi sổ không còn được dùng để phân biệt "trùng hay không trùng" nữa — chỉ cần giống hệt các thông tin định danh khác (chi nhánh, ngân hàng, trạng thái, ngày, số tiền) là tính là trùng, bất kể số phiếu ghi sổ khác nhau
    + **Đã kiểm chứng thêm bằng cách xoá NGẪU NHIÊN 20 lệnh IPCAS bất kỳ** (không liên quan gì tới các nhóm trùng) — cả 20/20 đều hiện đúng "Chỉ CITAD" ngay, xác nhận việc phát hiện "lệnh CITAD không có gì đối ứng" hoạt động đúng cho mọi trường hợp, không riêng ca cụ thể vừa test
    + Thêm 1 test khoá lại — toàn bộ 26 test pass

- 23/08/2026 Đối soát CITAD↔IPCAS - **"Chuyển chi nhánh — chỉ tính dòng gốc" nay áp dụng cho cả ngoại tệ (USD/EUR qua Hub), không riêng VNĐ**:
    + Xác nhận nghiệp vụ Phòng Thanh toán: ngoại tệ cũng có lệnh chuyển chi nhánh giống VNĐ (IPCAS) — 1 lệnh sinh nhiều dòng cùng "Số thành công" nhưng khác chi nhánh; dòng gốc là dòng mang trạng thái **"Đã trả KH"**
- 23/08/2026 Đối soát CITAD↔IPCAS - **"Chuyển chi nhánh — chỉ tính dòng gốc" nay áp dụng cho cả ngoại tệ (USD/EUR qua Hub), không riêng VNĐ**:
    + Xác nhận nghiệp vụ Phòng Thanh toán: ngoại tệ cũng có lệnh chuyển chi nhánh giống VNĐ (IPCAS) — 1 lệnh sinh nhiều dòng cùng "Số thành công" nhưng khác chi nhánh; dòng gốc là dòng mang trạng thái **"Đã trả KH"**
    + **Trước bản sửa này, phần mềm hoàn toàn chưa đọc cột "Trạng thái" của file Hub ngoại tệ** — và khi trùng "Số thành công", dòng nào thắng phụ thuộc thứ tự dòng trong file (không cố định, có thể đổi kết quả giữa các lần chấm cùng 1 file). Nay dòng "Đã trả KH" luôn thắng, đúng dòng gốc
    + **Không đổi cách làm hằng ngày.** File Hub không có cột Trạng thái thì mọi thứ giữ nguyên như trước (không có gì để ưu tiên)
    + Thêm 1 test khoá lại hành vi này — toàn bộ 25 test pass

- 23/08/2026 Đối soát CITAD↔IPCAS - **Bắt được thêm ca "IPCAS/Hub hạch toán trùng lệnh" — trước đây bị bỏ qua âm thầm, ra thành dòng "Chỉ Agribank"/"Chỉ Hub" riêng**:
    + ⚠️ **Phát hiện qua tự kiểm thử của Phòng Thanh toán**: dán thêm 1 dòng y hệt vào file IPCAS để mô phỏng việc IPCAS ghi nhận trùng 1 lệnh Đến, chạy đối soát thì máy không báo gì — vì bước đọc file IPCAS có sẵn 1 khâu âm thầm bỏ dòng trùng y hệt trước khi đối soát kịp thấy
    + **Đây là chiều ngược lại của tính năng đã có** (CITAD gửi trùng 1 lệnh Đi, IPCAS chỉ ghi 1 lần — phát hiện từ 20/08): nay thêm chiều IPCAS/Hub ghi trùng 1 lệnh, trong khi CITAD chỉ có đúng 1 lệnh — áp dụng cho **cả VND (IPCAS) lẫn ngoại tệ (Hub)**
    + **Dòng trùng dư ra nay hiện thành dòng "Chỉ IPCAS"/"Chỉ Hub" RIÊNG** (không chỉ 1 câu ghi chú trên dòng đã khớp) — đúng bản chất CITAD chỉ xác nhận đúng 1 lệnh, phần dư ra là số liệu không có gì đối chứng. Dòng khớp và các dòng dư đều ghi rõ số lần trùng và đúng cổng CITAD của lệnh đó để tra thẳng ra
    + 🔧 **Đính chính trong ngày — bản sửa đầu tiên tự phát hiện sai trước khi báo xong, đã sửa lại ngay**: lần đầu đếm "trùng" theo đúng mã giao dịch IPCAS dùng để khớp lệnh — tưởng hợp lý nhưng kiểm lại bằng dữ liệu thật thì số Lệch nhảy vọt từ 12 lên 1.556, vì IPCAS có thể dùng CHUNG 1 mã cho nhiều lệnh THẬT khác nhau (khác ngân hàng nhận) — bị hiểu nhầm hàng loạt thành "hạch toán trùng". Đã sửa: chỉ tính là trùng thật khi khớp đủ MỌI thông tin nhận dạng (thêm mã chi nhánh, số trace), không chỉ mã giao dịch. Đã kiểm lại đúng dữ liệu thật: về đúng **12 lệch gốc + 6 lệnh trùng thật đã xác nhận = 18**, không còn sai lệch lớn
    + **Không đổi số Khớp của bất kỳ ngày nào đã chấm trước đây** — chỉ thêm dòng "Chỉ IPCAS"/"Chỉ Hub" mới cho đúng số lượng dư ra thật, không đổi lệnh nào đã khớp thành lệch
    + Bộ test tự động của module tăng lên 21 bài, trong đó có bài canh riêng ca "trùng ngẫu nhiên mã giao dịch nhưng không phải trùng thật" để không tái diễn lỗi vừa đính chính

- 23/08/2026 Đối soát CITAD↔IPCAS - **Lệnh Đến bất thường mang trạng thái PYED/PYEK không còn biến mất khỏi báo cáo**:
    + ⚠️ **Phát hiện qua tự kiểm thử của Phòng Thanh toán**: thêm 1 lệnh KHÔNG CÓ THẬT (không khớp CITAD nào) mang trạng thái PYED vào file IPCAS Đến, chạy đối soát thì máy không báo gì — vì có sẵn 1 luật từ 20/08 bỏ qua mọi lệnh Đến trạng thái PYED/PYEK khi tính "Chỉ IPCAS" (lý do ban đầu: PYED/PYEK là đang xử lý, CITAD chưa kịp có). Luật đó không phân biệt được "PYED thật đang chờ CITAD" với "PYED giả sẽ không bao giờ khớp" — cả hai đều bị bỏ qua như nhau, im lặng
    + **Nguyên tắc đúng đã xác nhận**: chênh lệch SỐ LƯỢNG lệnh áp dụng cho MỌI trạng thái, không riêng gì trạng thái nào. Từ nay lệnh Đến không khớp CITAD nào luôn hiện "Chỉ IPCAS", bất kể mang trạng thái gì
    + **Không gây bùng nổ số liệu** dù PYED là trạng thái khá phổ biến — kiểm bằng dữ liệu thật: số Lệch chỉ tăng đúng 1 (đúng bằng lệnh giả vừa thêm để test), nghĩa là tuyệt đại đa số lệnh PYED thật vốn đã khớp sẵn với CITAD, chỉ đúng lệnh bất thường mới lộ ra
    + Sửa lại 2 test đã khoá hành vi cũ, giờ khoá đúng hành vi mới — toàn bộ 24 test pass

- 23/08/2026 Đối soát CITAD↔IPCAS - **Cài đặt đúng việc còn dang dở từ tài liệu bàn giao gốc: "Lệnh chuyển chi nhánh Đến — chỉ tính dòng gốc"**:
    + ⚠️ **Phát hiện qua trao đổi với Phòng Thanh toán**: một số lệnh IPCAS Đến có mã dạng "số gốc-dãy số dài" — đây là lệnh CHUYỂN CHI NHÁNH (IPCAS chuyển 1 lệnh sang chi nhánh khác xử lý), không phải chênh lệch thật. Việc này đã được ghi chú từ trước trong tài liệu bàn giao gốc của dự án nhưng đánh dấu "chưa cài đặt"
    + **Phát hiện thêm, quan trọng hơn**: dòng gốc (luôn ở 1 chi nhánh cố định, trạng thái CGBR) và dòng con (chuyển sang chi nhánh khác) đang dùng CHUNG 1 khoá để khớp lệnh — nên từ trước tới nay khi 2 dòng này trùng nhau, hệ thống **tự chọn NHẦM dòng con** để hiện kết quả đối soát (vì bảng độ ưu tiên trạng thái thiếu đúng mã của dòng gốc). Hậu quả: ngân hàng nhận và trạng thái hiển thị cho những lệnh này trước nay là của dòng con, không phải dòng gốc
    + **Từ nay dòng gốc luôn được chọn đúng** khi có va chạm — dòng con (chỉ là thao tác nội bộ IPCAS) bị loại hẳn, không còn hiện sai thông tin ngân hàng nhận/trạng thái nữa. Đúng nguyên tắc Phòng Thanh toán xác nhận: "1 lệnh CITAD cân với 1 lệnh gốc IPCAS là được"
    + **Không đổi số Khớp/Lệch của bất kỳ ngày nào** — đã kiểm chứng bằng đúng dữ liệu thật, chỉ đổi đúng thông tin hiển thị (ngân hàng nhận/trạng thái) cho các lệnh từng bị chọn nhầm
    + Thêm 1 test khoá lại đúng hành vi này — toàn bộ 24 test pass

- 23/08/2026 Đối soát CITAD↔IPCAS - **Dòng "Chỉ IPCAS"/"Chỉ Hub" thôi hiện nhầm số ở cột "Số GD (CITAD)"**:
    + ⚠️ **Phát hiện qua câu hỏi trực tiếp của người dùng khi xem bảng kết quả**: dòng báo "Chỉ IPCAS" (nghĩa là CITAD không hề có lệnh này) nhưng cột "Số GD (CITAD)" vẫn hiện 1 số — gây hiểu lầm là CITAD cũng có lệnh đó. Đây là lỗi hiển thị **có sẵn từ trước**, không phải do các thay đổi trong ngày, chỉ là được để ý ra khi đang xem kỹ các dòng liên quan tới mục ở trên
    + **Từ nay dòng "Chỉ IPCAS"/"Chỉ Hub" để trống đúng cột "Số GD (CITAD)"** — giống hệt cách dòng "Chỉ CITAD" từ trước tới nay vẫn để trống đúng cột "Số GD (Agribank)". Áp dụng cho cả màn hình xem lẫn file Excel xuất ra
    + **Không đổi số Khớp/Lệch của bất kỳ ngày nào** — chỉ đổi cách hiển thị 1 cột, không đổi lệnh nào từ khớp thành lệch hay ngược lại
    + Thêm 2 test khoá lại đúng hành vi này (cột CITAD để trống ở cả dòng "Chỉ IPCAS" và "Chỉ Hub") — toàn bộ 23 test pass

- 22/08/2026 Đối soát CITAD↔IPCAS - **Thử mở rộng chốt chặn "CITAD gửi trùng" sang lệnh Đến/ngoại tệ — RÚT LẠI trong ngày vì làm sai số liệu thật**:
    + 🚫 **Đã thử rồi bỏ, không phải tính năng mới.** Có ý định mở rộng chốt chặn "CITAD gửi trùng" (sửa 20/08, khi đó chỉ áp cho lệnh Đi VND) sang cả lệnh Đến VND và ngoại tệ. Khi kiểm lại bằng đúng dữ liệu CITAD/IPCAS thật ngày 19/08/2026 thì phát hiện **số Khớp tụt từ 38.130 xuống còn 36.715** — mất hơn 1.400 lệnh khớp THẬT một cách oan uổng
    + **Nguyên nhân**: CITAD đánh số "Số GD" **riêng theo từng cổng** (cổng 1, 9, 12, 17, 18) — một mã số hoàn toàn có thể trùng giữa 2 cổng khác nhau mà KHÔNG phải là gửi trùng, chỉ là trùng số ngẫu nhiên vì 2 cổng đếm độc lập. Máy không phân biệt được việc này với CITAD gửi trùng thật, nên gạt nhầm hàng loạt lệnh Đến khớp đúng thành "Trùng CITAD"
    + ✅ **Đã trả lại đúng như cũ — chỉ VND Đi mới có chốt chặn "gửi trùng", như từ 20/08 tới nay.** Đã kiểm lại bằng đúng dữ liệu 19/08/2026: số Khớp/Lệch về đúng 38.130/12 như trước. **Không ai cần làm gì, màn hình và số liệu không đổi so với trước ngày hôm nay**
    + Thêm bộ test tự động đầu tiên cho module Đối soát CITAD (15 test, trước đây module này không có test nào) — trong đó có 2 bài khoá lại đúng phát hiện ở trên, để lần sau có ai định mở rộng chốt chặn này thì phải tự chứng minh bằng dữ liệu thật trước, không suy luận suông


- 23/08/2026 Sổ trực + Đối chiếu CITAD - **5 sửa nhỏ theo phản hồi dùng thật (PR#53)**
    + **Sổ trực nay chỉ coi là "đã đối chiếu CITAD" khi ngày đó đã bấm *Lưu bảng cuối***. Bảng mới *Lưu tạm* vẫn bị tính là **chưa có**, nên lời nhắc trước khi chuyển KSV / xác nhận vẫn hiện. Cố ý làm vậy: số Napas và PSS - MDP thường do người khác điền sau, một bảng tạm "khớp" chỉ khớp trên phần đã nhập
    + ⚠️ **Sẽ thấy lời nhắc thường xuyên hơn trước.** Ngày nào chuyển KSV trước khi có người chốt bảng cuối là có hộp thoại nhắc. Vẫn **không chặn** — bấm *Vẫn xác nhận* là đi tiếp
    + ⚠️ **Câu chữ trong hộp thoại đó chưa chỉnh theo**: nó vẫn viết *"Chưa có bản đối chiếu CITAD nào được lưu"* trong khi thực tế có thể **đang có bảng tạm**. Bảng tạm không mất đi đâu cả — mở màn Đối chiếu CITAD vẫn còn nguyên. Sẽ sửa lại câu chữ ở đợt sau
    + **Tab *Lịch sử* của Sổ trực: không chọn ngày thì hiện TOÀN BỘ phiên trực**, trước đây chỉ hiện đúng 1 phiên gần nhất. Danh sách dài nhiều tháng có **dòng ngăn cách màu xanh mint ghi tháng/năm** để dễ dò. Muốn thu hẹp thì chọn khoảng ngày rồi bấm *Lọc*
    + **Ô *Lập bảng* / *Kiểm soát* ở Đối chiếu CITAD nay bấm chọn được tên** từ danh sách nhân viên Phòng Thanh toán, vẫn gõ tay tự do như cũ
    + 🔴 **Hai lỗi đã biết ở hai ô này, chưa vá — xin đọc kỹ**:
        * **Xuất Excel sẽ báo lỗi nếu để trống cả hai ô.** Cách tránh: điền tên (hoặc gõ một dấu gạch) trước khi bấm *Xuất Excel*
        * **Mở lại bảng cũ mà tên người ký không có trong danh sách Phòng Thanh toán** (người đã nghỉ, đã chuyển phòng, hoặc tên gõ tay kiểu khác) thì **ô đó hiện trống**. Nguy hiểm hơn: lúc đó bấm *Lưu* sẽ **ghi đè mất tên cũ trong máy**. Trong lúc chờ vá: nếu mở bảng của ngày cũ mà thấy hai ô này trống bất thường thì **đừng bấm Lưu**, báo lại để khôi phục
    + **Bấm *Bỏ xem, làm bảng mới* nay chỉ hiện 1 thông báo** (*"Đã chuyển sang phiên chấm đối chiếu mới"*) thay vì 2 thông báo chồng nhau. Nút *Xoá* riêng vẫn báo như cũ
    + **Đối soát CITAD ↔ IPCAS: 3 khung tải file** (CITAD / IPCAS / Hub ngoại tệ) nay **có viền đỏ đô bo góc riêng** cho dễ phân biệt
    + Không đổi cơ sở dữ liệu, không phải khai báo quyền lại. Toàn bộ **666 test** chạy đạt

- 22/08/2026 Bàn giao cho lưu trữ - **Cột TIEUDE_HS đổi sang mẫu "Nhật ký chứng từ ngày ... của Phòng ..."**
    + **Đổi gì**: tiêu đề hồ sơ nộp lưu trữ trước đây in ra là *"Hồ sơ ngày 27/02/2025 Phòng Kế toán tháng 02/2025 tập 1/2"*, nay là **"Nhật ký chứng từ ngày 27/02/2025 của Phòng Kế toán tập 1/2"**
    + **Bỏ hẳn đuôi "tháng 02/2025"**: ngày ghi ngay phía trước đã có đủ tháng và năm rồi, nhắc lại chỉ làm ô dài thêm
    + Ba dạng đều đúng: một ngày (*... ngày 26/02/2025 của Phòng NosVos*), nhiều ngày gộp một tập (*... ngày 03/03/2025, 04/03/2025 của ...*), một ngày chia nhiều tập (*... tập 1/2*, *... tập 2/2*)
    + ⚠️ **Máy in đúng tên phòng đang lưu trong hệ thống, không tự viết tắt.** Phòng QLTK Nostro Vostro sẽ in ra đủ chữ *"của Phòng Quản lý Tài khoản Nostro Vostro"*. Muốn in gọn hơn thì phải sửa tên phòng ở màn Quản lý phòng ban
    + Áp dụng cho **cả bảng xem trước lẫn file Excel tải về** — không phải làm gì thêm, mở lại màn *Bàn giao cho lưu trữ* là thấy

- 22/08/2026 Tra cứu lưu trữ - **Bảng thôi tự dài thêm 5 dòng trống sau mỗi lần lưu**
    + **Đổi gì**: trước đây cứ lưu một lần là bảng mọc thêm 5 dòng trống ở cuối, lưu vài lần thì phải cuộn qua cả chục dòng rỗng mới tới nút bấm. Nay **tháng chưa có dữ liệu mới có sẵn 5 dòng trống**; tháng đã có dữ liệu thì bảng đúng bằng số dòng thật
    + **Cần nhập thêm ngày mới thì bấm nút *Thêm dòng*** — tốn một cú bấm, đổi lại bảng luôn sạch
    + Dòng trống không in ra giấy, như cũ

- 22/08/2026 Trang chủ - **Ô "Người dùng" thôi đếm nhầm Quản trị viên cấp 2**
    + **Đổi gì**: ô *Người dùng* ở Trang chủ vốn đã bỏ qua tài khoản quản trị, nhưng chỉ bỏ qua cấp 1. Thêm một **Quản trị viên cấp 2** là con số nhảy lên một, dù đó không phải người dùng nghiệp vụ
    + Nay **cả hai cấp quản trị đều không được đếm**. Con số có thể giảm 1–2 so với hôm qua — đó là số đúng, không phải mất người

- 22/08/2026 Chấm 459901 - **Chọn được nhiều file ZIP trong một lần, không phải chọn từng cái**
    + **Đổi gì**: bấm *Chọn file ZIP* nay giữ **Ctrl** (chọn từng file rời) hoặc **Shift** (chọn cả dải) để lấy nhiều file một lượt, hoặc kéo-thả cả nhóm file vào ô. Tên các file đã chọn hiện ngay bên dưới kèm số lượng
    + **Quan trọng — nhiều file được GỘP thành một lần chấm, không phải chấm riêng từng file rồi cộng lại.** Cố ý làm vậy: một lệnh hủy gồm hai vế (bút toán gốc và bút toán hủy), hai vế đó có thể nằm ở hai file khác ngày. Chấm riêng từng file thì không vế nào tìm được vế kia, cả hai bị xếp nhầm sang *Lệnh Khác* — **không có lỗi nào báo, chỉ là số liệu sai**
    + **Vẫn chọn một file như cũ thì không có gì đổi** — kết quả y hệt trước đây
    + ⚠️ **Lỡ chọn trùng một file hai lần thì máy báo lỗi và không chạy.** Cố ý chặn: dữ liệu bị nhân đôi vẫn khớp cặp hủy như thường, không sinh lỗi nào, chỉ là **mọi con số gấp đôi** mà không ai nhận ra. Máy so theo tên file — nếu bạn đổi tên bản sao thành tên khác thì máy **không** phát hiện được, xin tự kiểm trước khi bấm *Xử lý*
    + **Bấm nhầm thì có nút *Xóa danh sách file*** để chọn lại từ đầu
    + **Nếu một file trong nhóm bị hỏng hoặc sai định dạng**, thông báo lỗi nay **nói rõ tên file nào** — trước đây chỉ báo chung chung, chọn cả chục file thì không biết bỏ cái nào ra
    + **Giới hạn**: mỗi file tối đa 200 MB, tổng cả lượt tối đa 600 MB. Vượt thì chia làm nhiều lượt
    + Không đổi cơ sở dữ liệu, không phải khai báo quyền lại. Toàn bộ **666 test** chạy đạt (thêm 7 test mới, trong đó có bài canh đúng việc cặp lệnh hủy nằm ở hai file khác nhau)

- 22/08/2026 Giao diện - **Menu "Nghỉ phép" ra ngoài, không còn nằm trong "Chấm công & Lịch trực"**
    + **Đổi gì**: trước đây muốn vào *Nghỉ phép* phải rê chuột vào *Chấm công & Lịch trực* rồi mới thấy. Nay **Nghỉ phép nằm thẳng ngoài menu bên trái**, bấm một lần là vào, ngang hàng với *Chấm công & Lịch trực*
    + **Vì sao**: cả cơ quan dùng nghỉ phép hằng ngày, còn chấm công và lịch trực là việc của riêng hai phòng — bắt mọi người đi qua một nhóm mang tên hai phòng đó là ngược
    + **Màn *Phân quyền theo nhóm* cũng đổi theo**: ô tick *Nghỉ phép* nay là **một thẻ riêng**, không còn nằm trong thẻ *Chấm công & Lịch trực*. Các ô tick con (tạo đơn, duyệt, uỷ quyền, hạn mức...) **giữ nguyên không thiếu ô nào**
    + **Không phải làm gì thêm**: ai đang được cấp quyền nghỉ phép thì vẫn thấy menu, chỉ đổi chỗ. Không đổi cơ sở dữ liệu, không đổi đường dẫn trang, không cần khai báo lại quyền
    + Toàn bộ **659 test** chạy đạt

- 22/08/2026 Lịch trực - **Phân lịch nay tự giãn ca: tối đa 2 ca/tuần, 2 thứ 6/tháng, không thứ 6 hai tuần liền**
    + **Vì sao có mục này**: máy xếp lịch trước đây chỉ biết *"tuần này đã trực chưa"* — trả lời xong là hết. Một người trực thứ Hai rồi thì thứ Ba vẫn có thể bị gọi tiếp, và người trực thứ 6 tuần này tuần sau lại thứ 6, vì với máy thì "đã trực 1 lần" hay "đã trực 3 lần" đều chỉ là *đã trực*
    + **Từ nay máy tránh ba việc**: xếp một người **quá 2 ca trong một tuần**; xếp một người **trực thứ 6 quá 2 lần trong tháng**; xếp một người **trực thứ 6 hai tuần liên tiếp**. Ba luật áp dụng **như nhau cho Lãnh đạo và nhân viên**
    + ⚠️ **Đây là luật mềm, không phải luật cấm.** Hôm nào nghỉ phép nhiều, không còn ai khác để gọi thì máy **vẫn lập đủ ca** — nhưng ghi rõ *"ông A phải trực quá 2 ca/tuần vì không đủ người khác"* ngay dòng cảnh báo sau khi sinh lịch. Cố ý làm vậy: thà có ca trực kèm lời nhắc còn hơn để trống một ngày
    + **Với quân số hiện nay của phòng (7 Lãnh đạo, 18 nhân viên) thì rất dư** — 5 ca/tuần chia cho 7 Lãnh đạo, 4 thứ 6/tháng chia cho 7 người. Bình thường sẽ không thấy cảnh báo nào; thấy là dấu hiệu hôm đó vắng nhiều thật
    + ⚠️ **Lịch sinh ra sẽ khác lịch cũ.** Thứ tự chọn người đã đổi, nên bấm *tạo lại lịch* cho một tuần đã sinh trước hôm nay sẽ ra kết quả khác. Lịch **đã xác nhận** thì không bị đụng
    + ⚠️ **Khi sửa tay ca trực, lời nhắc chưa đầy đủ**: hiện phần mềm chỉ soi các ca **trước** ngày đang sửa. Sửa ca thứ Hai mà người đó đã có ca thứ Tư, thứ Năm, thứ Sáu thì **không có lời nhắc nào**. Chỗ này đã ghi nhận, sẽ sửa ở đợt sau — trong lúc chờ, khi sửa tay xin nhìn cả tuần trên màn hình thay vì tin vào lời nhắc
    + Không đổi cơ sở dữ liệu, không phải khai báo gì thêm. Toàn bộ **553 test** chạy đạt (thêm 9 test mới, trong đó có bài mô phỏng phân lịch **3 tháng liên tục** để chắc ba luật giữ được đồng thời)

- 22/08/2026 Vận hành - **`deploy.bat` nay cảnh báo khi `.env` máy chính thiếu mật khẩu phải gõ tay**
    + **Vì sao có mục này**: chiều 21/08, máy chính chạy *Đối chiếu ACH* — chờ hơn một phút rồi dừng, báo *"Chưa đặt DOI_CHIEU_ZIP_PASSWORD trong file .env"*. Không ai xoá dòng đó cả: nó **chưa bao giờ** có trên máy chính. `deploy.bat` **cố ý không chép đè `.env`** của máy chính (chép đè là mất `SECRET_KEY`, đăng xuất toàn bộ), nên mọi dòng cấu hình mới đều phải có người gõ vào
    + Hai lần trước (`STORAGE_SECRET` 07/2026, `BACKUP_PASSWORD` 08/2026) `start.bat` **tự sinh hộ** nên không ai để ý khoảng trống này. Nó tự sinh được vì đó là mật khẩu **của phần mềm**; còn mật khẩu file ZIP là **của đơn vị cấp file**, không đoán được, buộc phải gõ
    + **Từ nay khi chạy `deploy.bat`**: nếu `.env` máy đích thiếu dòng nào thuộc loại phải gõ tay, deploy in cảnh báo ở **bước 1/8** và **nhắc lại lần nữa** trong khung tổng kết cuối cùng (chỗ thực sự có người đọc). Cảnh báo bắt cả trường hợp *có dòng nhưng để trống*
    + **Deploy không tự điền giá trị** — không đoán bừa mật khẩu của bên ngoài. Việc phải làm vẫn là mở `.env` trên máy đó, thêm dòng, rồi **tắt hẳn và chạy lại `start.bat`**
    + **Không đổi gì trong phần mềm** — chỉ đổi công cụ cập nhật của người vận hành. Hệ thống test cũng được nhắc như vậy
    + ⚠️ Đã **đính chính** mục *20/08/2026 Rà soát bảo mật đợt 2* phía dưới: câu *"bạn không phải làm gì, giá trị cũ đã được điền sẵn"* là **sai** — đó là trạng thái của máy phát triển, không phải máy chính

- 21/08/2026 Lưu trữ - **Tháng chưa có dữ liệu nay vẫn nhập được số liệu vào bảng Tra cứu lưu trữ**
    + **Việc đã sửa**: các tháng đầu năm chưa triển khai chương trình nên trong máy không có tập nào. Trước đây chọn những tháng đó, bảng chỉ hiện dòng chữ *"Không có dữ liệu"* — **không có ô nào để gõ**, muốn đưa số cũ vào phải nhập lại từ màn bàn giao rồi gom tập từ đầu
    + **Từ nay**: chọn tháng nào cũng có bảng, cuối bảng luôn sẵn **5 dòng trống** (nền xám nhạt) để gõ **Ngày** và **Số chứng từ**. Gõ xong bấm **Lưu thay đổi** như bình thường
    + **Cần nhập nhiều hơn 5 ngày một lượt**: bấm nút **Thêm dòng** (cạnh nút Lưu) để có thêm dòng trống — số đang gõ dở không bị mất
    + **Bản in không có các dòng trống này** — bấm *In danh sách* vẫn ra đúng bảng như trước
    + ⚠️ **Gõ ngày mà quên số chứng từ thì phần mềm báo lỗi và không lưu gì cả** (cả lần lưu đó). Cố ý làm vậy: thà báo rõ còn hơn hiện chữ "Đã lưu" trong khi thực tế không ghi được gì
    + ⚠️ **Số nhập tay không vào báo cáo khối lượng theo giao dịch viên** — báo cáo đó đếm chứng từ do từng người bàn giao, còn nhập tay thì không biết ai nộp. Bảng *Tra cứu lưu trữ*, *Tổng hợp cả năm* và file *Bàn giao cho lưu trữ* thì có đủ
    + ⚠️ **In bìa cho tập nhập tay sẽ trống phần người nộp**, vì phần mềm không biết ai nộp
    + 🚫 **Đừng bấm gom tập lại cho tháng đã nhập tay.** Nút gom tập dựng lại toàn bộ tập của tháng đó từ dữ liệu bàn giao, phần nhập tay sẽ mất và không lấy lại được. Tháng thuần nhập tay (không có bàn giao nào) thì an toàn — gom tập sẽ báo "không có chứng từ" và dừng lại, không xoá gì
    + **Cột Ngày nay có sẵn 10 ô** (trước là 2) — một hồ sơ nhập bù thường gộp cả tuần
    + 🔧 **Đã sửa lỗi tách dòng**: gõ Ngày *1 2* với Số chứng từ *12 34* trên **một** dòng, lưu xong lại thành **hai** dòng giống hệt nhau, mỗi dòng Số tập = 1. Nguyên nhân là lỗi có sẵn từ trước: phần mềm chỉ biết gộp các tập **cùng một ngày**, còn tập **gộp nhiều ngày** thì mỗi tập bị tách một dòng. Nay gộp đúng: một dòng = một hồ sơ, Số tập đếm đủ
    + ⚠️ **Kèm theo, bìa tập nhiều ngày nay được đánh số**: hai tập của cùng hồ sơ *"ngày 01, 02"* trước in **1/1 cả hai** (hai bìa giống hệt nhau), nay in **1/2** và **2/2**. File *Bàn giao cho lưu trữ* cũng ghi thêm *"tập 1/2"*. Tổng số tập và tổng số tờ **không đổi** — chỉ đổi cách gộp và cách đánh số. Ai đã in bìa trước đó thì in lại cho khớp
    + Toàn bộ **654 test** chạy đạt (thêm 20 test mới: nhập cho tháng trống, gộp dòng nhiều ngày, đánh số bìa)

- 21/08/2026 Nghỉ phép - **Lịch nghỉ chỉ còn hiện người CÙNG PHÒNG; banner uỷ quyền ghi đủ chức danh**
    + ⚠️ **Đây là thay đổi ai-thấy-gì, đọc kỹ**: trước đây mở màn *Nghỉ phép*, **bất kỳ ai** cũng thấy tên toàn bộ người nghỉ của **cả trung tâm** trên lịch tháng. Nay mỗi người **chỉ thấy người cùng phòng mình**
    + **Vẫn xem được toàn trung tâm**: Quản trị viên, Giám đốc / Phó Giám đốc, và nhân viên **phòng Tổng hợp** — đúng những vai vốn đã được xem toàn bộ danh sách đơn
    + ⚠️ **Hậu kiểm viên nay cũng chỉ thấy phòng mình.** Cùng đợt này Hậu kiểm viên đã ra khỏi quy trình duyệt nghỉ phép, nên để họ đọc tên cả trung tâm trên lịch là hở đúng cái cửa vừa đóng. Đã thêm bài kiểm tự động canh việc này
    + **Rê chuột vào một ô ngày** trên lịch nay hiện **đủ danh sách** người nghỉ hôm đó (ô ngày chỉ đủ chỗ hiện 3 tên đầu rồi "+N"). Ai đang xem nhiều phòng thì có kèm tên phòng
    + **Banner uỷ quyền ghi đủ chức danh và ngày kiểu Việt Nam**: trước là *"Nguyễn Văn A ủy quyền cho Trần Thị B từ 2026-08-01 đến 2026-08-05"*, nay là *"**Giám đốc** Nguyễn Văn A ủy quyền cho **Phó Giám đốc** Trần Thị B từ **01/08/2026** đến **05/08/2026**"*
    + **Không đổi gì về quy trình duyệt, hạn mức phép hay số liệu báo cáo** — chỉ đổi ai nhìn thấy gì trên lịch
    + Toàn bộ **636 test** chạy đạt

- 21/08/2026 Nghỉ phép - **Bản xem trước đơn hiện gần như tức thì (từ ~5 giây xuống ~0,3 giây)**
    + **Chỗ chậm nằm ở đâu**: mỗi lần bấm *Xem trước* / *Gửi đơn* / *Phê duyệt*, phần mềm **mở Word lên rồi đóng ngay** chỉ để chuyển một tờ đơn sang PDF. Bấm 10 lần là mở Word 10 lần. Đo trên máy thật: mở + đóng Word mất **3,6 giây**, còn việc chuyển tờ đơn chỉ mất **0,25 giây** — tức là gần hết thời gian ngồi chờ là dựng Word lên rồi phá đi
    + **Từ nay**: phần mềm **giữ sẵn một bản Word chạy ngầm** và dùng lại cho mọi người, y như để sẵn cái máy in đã bật thay vì bật/tắt cho từng tờ

    | Thao tác | Trước | Sau |
    |---|---|---|
    | Bấm *Xem trước* một đơn mới | 4–6,5 giây | **~0,3 giây** |
    | Lượt đầu sau khi Word đã ngủ | 4–6,5 giây | ~1,1 giây |
    | Xem lại đơn vừa xem | tức thì | tức thì |

    + **Mở màn Nghỉ phép là phần mềm tự đánh thức Word** ở nền, trong lúc anh/chị còn đang xem danh sách hoặc điền đơn — nên đến khi bấm nút thì gần như không phải chờ
    + **Ảnh tờ đơn gửi về nhẹ đi hơn hai lần** (107 KB → 43 KB): tờ đơn in đen trắng nên không cần gửi kèm thông tin màu. Mẫu đơn nào có logo hoặc dấu đỏ thì phần mềm tự nhận ra và giữ nguyên màu
    + ⚠️ **Chỉ máy chủ mới có Word chạy ngầm — máy người dùng không có gì cả.** Người dùng vào bằng trình duyệt, máy họ không cài, không chạy, không cần Word
    + ⚠️ **Trên máy chủ, trong Task Manager sẽ thấy một tiến trình WINWORD chạy ngầm** — đó là bản Word của phần mềm, **không phải Word ai đó quên tắt**. Nó ăn khoảng **130 MB RAM**, gần như không tốn CPU lúc rảnh, và **tự tắt sau 15 phút** không ai dùng
    + ⚠️ **Nếu máy chủ cũng là máy có người ngồi làm việc** — điều này quan trọng: khi bản Word ngầm đang chạy mà anh/chị **mở một file Word trên chính máy đó**, Windows có thể đưa tài liệu vào đúng bản ngầm ấy (Word vốn chỉ chạy một bản). Phần mềm đã được vá để **nhận ra và tuyệt đối không đóng** bản Word đang có tài liệu mở: nó thà để Word chạy tiếp còn hơn đóng mất bài anh/chị đang gõ. Đã thử nghiệm và xác nhận: tài liệu **còn nguyên** sau khi phần mềm tắt Word ngầm
    + 💡 **Khuyến nghị**: nếu được, đừng dùng chính máy chủ để soạn thảo Word. Không phải vì phần mềm sẽ làm hỏng — hàng rào đã dựng và đã thử — mà vì máy chủ nên làm mỗi việc chạy máy chủ
    + 🚫 **Máy chủ PHẢI có một tài khoản đang đăng nhập** (màn hình console hoặc RDP) thì mới xuất được PDF. **Đừng** đưa hệ thống vào Windows Service, cũng **đừng** đặt Task Scheduler kiểu *"chạy cả khi không ai đăng nhập"* — Word không làm việc được ở đó. Khoá màn hình thì không sao (vẫn giữ phiên); **đăng xuất** hoặc khởi động lại máy thì phải đăng nhập rồi chạy lại `start.bat`
    + Đã đo thật: ở phiên không người đăng nhập, Word **mở lên được** (nên nhìn qua tưởng chạy tốt) nhưng **không mở được tài liệu**. Nếu lỡ rơi vào tình huống này thì hệ thống **không đứng lại** — tự lui về tải bản `.docx` và vẫn duyệt đơn bình thường, đồng thời ghi log nói rõ nguyên nhân thay vì một câu lỗi kỹ thuật khó hiểu
    + **Máy chủ chưa cài Word thì không đổi gì** — vẫn báo lỗi rõ và vẫn cho tải bản `.docx` như trước, quy trình duyệt đơn không đứng lại
    + **Vẫn còn đường lui**: nếu bản Word chạy ngầm gặp trục trặc, phần mềm **tự động quay về cách cũ** (mở/đóng từng lần, chậm hơn nhưng chạy được) — không ai bị kẹt
    + Ba nút chỉnh trong `.env` nếu cần: `WORD_SERVER=0` (tắt hẳn cách mới), `WORD_IDLE_SECONDS` (bao lâu không dùng thì tắt Word), `WORD_MAX_JOBS` (bao nhiêu lượt thì thay Word mới)
    + Toàn bộ **630 test** chạy đạt (thêm 13 test mới canh các đường hỏng: Word trục trặc, Word báo lỗi, không đóng nhầm Word của người vận hành, không diệt nhầm tiến trình khác)

- 21/08/2026 Phân quyền - **Quản trị viên cấp 2 nay thấy và dùng được menu *Phân quyền chức năng***
    + **Việc đã sửa**: trước đây Quản trị viên **cấp 2** đăng nhập **không thấy** nhóm menu *Phân quyền chức năng* (hai mục *Nhóm user* và *Phân quyền theo nhóm*). Không phải lỗi hiển thị — phần mềm chỉ mở menu này cho cấp 1
    + **Từ nay cấp 2 làm được như cấp 1**: tạo / sửa / xoá nhóm, thêm bớt thành viên, tick quyền cho nhóm
    + ⚠️ **Trừ đúng hai việc, để cấp 2 không tự nâng quyền cho mình**:
        - **Không sửa được nhóm mà chính mình đang ở trong** — mở ra vẫn xem được đầy đủ, nhưng các nút bị khoá và có dòng chữ giải thích ngay trên màn hình
        - **Không tự thêm mình vào bất kỳ nhóm nào** — tên mình không xuất hiện trong ô *Thêm nhân viên*
        - Lý do: nếu không chặn, chỉ cần mở nhóm của mình rồi tick hết ô là cấp 2 có gần đủ quyền của cấp 1, vòng qua toàn bộ hàng rào đã dựng ở màn *Quản lý User*
    + **Cần một Quản trị viên cấp 1 đổi quyền cho nhóm của chính cấp 2** — cấp 2 không tự làm được, đó là chủ đích
    + ⚠️ **Việc biết mà không chặn**: hai Quản trị viên cấp 2 vẫn có thể **cấp quyền chéo cho nhau** (người này sửa nhóm của người kia). Chặn nốt thì cấp 2 gần như không dùng được, vì hầu hết nhóm quản trị đều có cấp 2 trong đó. Đây là chuyện **chọn người giao vai**, hãy cân nhắc khi bổ nhiệm cấp 2
    + **Cấp 1 và mọi vai trò khác không đổi gì.** Người không phải quản trị viên vẫn không thấy menu này
    + Toàn bộ **612 test** chạy đạt (thêm 11 test mới khoá lại đúng các đường tự nâng quyền)

- 21/08/2026 Toàn hệ thống - **Gọn lại menu bên trái: gộp Chấm công, Nghỉ phép, Phân lịch trực, Sổ trực vào một menu**
    + **Không thêm, không bớt tính năng nào.** Chỉ đổi chỗ đứng của 4 menu cũ — mọi màn hình và quyền hạn giữ nguyên
    + ***Phòng Kế toán* không còn là menu ngoài cùng** — nó lùi vào thành một mục bên trong menu mới
    + **Bốn menu cũ nay nằm chung dưới menu *Chấm công & Lịch trực***:
        - *Nghỉ phép* nằm ngay bên trong, vì cả cơ quan đều dùng
        - *Chấm công* nằm trong mục **Phòng Kế toán**
        - *Phân lịch trực* và *Sổ trực cuối ngày* nằm trong mục **Phòng Thanh toán**
    + ⚠️ **Thao tác dài hơn trước một nhịp**: *Nghỉ phép* nay phải rê chuột một lần mới thấy (trước bấm thẳng ở ngoài); *Chấm công*, *Phân lịch trực*, *Sổ trực* phải rê qua tên phòng rồi mới tới
    + **Ai thấy gì thì vẫn y như cũ**: *Chấm công* vẫn chỉ hiện với nhân viên Phòng Kế toán và Quản trị viên; ba mục kia vẫn theo quyền được cấp ở *Phân quyền theo nhóm*. Không có ai bỗng dưng thấy thêm hay mất đi menu nào
    + **Màn hình *Phân quyền theo nhóm* đổi theo cho khớp** — bốn ô tick cũ nằm rải rác nay gom vào chung một thẻ *Chấm công & Lịch trực*. **Quyền đã cấp không đổi**, chỉ đổi chỗ hiển thị
    + Dòng đường dẫn ở đầu mỗi trang tự đổi theo (ví dụ *Chấm công & Lịch trực / Phòng Thanh toán / **Sổ trực cuối ngày***)
    + Toàn bộ **583 test** chạy đạt

- 20/08/2026 Toàn hệ thống - **Rà soát bảo mật đợt 2 — vá 6 điểm hở, không đổi cách làm việc hằng ngày**
    + **Đợt này không thêm menu nào.** Nhưng có **hai việc người vận hành phải làm ngay**, đọc hai gạch đầu dòng có ⚠️ đầu tiên
    + ⚠️ **Mật khẩu file ZIP nguồn (ACH / Chấm 459901 / Đối chiếu Song phương) coi như đã lộ — cần đề nghị đơn vị cấp file đổi.** Mật khẩu này trước đây nằm **ngay trong mã nguồn** phần mềm, tức là ai từng có bản sao mã nguồn đều đọc được, và **xoá đi bây giờ cũng không xoá được khỏi lịch sử**. Nay nó nằm trong file cấu hình `.env` như các khoá bí mật khác
        - 🔧 **Đính chính 21/08/2026** — dòng này trước đây ghi *"bạn không phải làm gì, giá trị cũ đã được điền sẵn"*. **Sai.** `deploy.bat` cố ý **không bao giờ** chép đè `.env` của máy chính (để khỏi mất `SECRET_KEY`), nên dòng mật khẩu mới **không tự có mặt** ở đó. Ngày 21/08 máy chính chạy Đối chiếu ACH thì dừng ở bước giải nén, báo *"Chưa đặt DOI_CHIEU_ZIP_PASSWORD trong file .env"*
        - **Việc phải làm trên máy chính**: mở file `.env`, thêm vào cuối một dòng `DOI_CHIEU_ZIP_PASSWORD=<mật khẩu do đơn vị cấp file đặt>`, lưu lại rồi **tắt hẳn và chạy lại `start.bat`** (file `.env` chỉ được đọc lúc khởi động). Không có dòng này thì ba chức năng Đối chiếu ACH / Chấm 459901 / Đối chiếu Song phương báo lỗi ở bước giải nén; phần còn lại của phần mềm vẫn chạy bình thường
        - Chạy được rồi thì việc tiếp theo là đề nghị bên cấp file **đổi mật khẩu**, sau đó sửa lại đúng dòng đó trong `.env`
    + ⚠️ **Bản sao lưu tự động nay được mã hoá — hãy cất mật khẩu vào két.** File sao lưu `.db` chứa **mã băm mật khẩu của toàn bộ tài khoản**: ai chép được thư mục `data\backups` (hoặc thư mục backup phụ trên máy khác) là mang về dò mật khẩu ngoài tầm kiểm soát, không cần quyền gì trong phần mềm. Nay mỗi bản sao lưu ra file **`.zip` có mật khẩu (AES-256)**, mở được bằng **7-Zip / WinRAR** sẵn có, không cần công cụ riêng
        - Mật khẩu do `start.bat` **tự sinh và in ra màn hình đúng một lần** khi chạy lần đầu sau bản cập nhật này. **Chép ngay vào két mật khẩu của đơn vị.** Nó cũng nằm ở dòng `BACKUP_PASSWORD` trong file `.env`
        - **Mất mật khẩu này là không mở được bản sao lưu.** Đừng chỉ để nó trong `.env` trên đúng cái máy mà bản sao lưu dùng để cứu
        - Bản sao lưu **cũ** (đuôi `.db`) vẫn dùng được bình thường và vẫn được dọn theo đúng luật cũ
    + **Người bị bắt đổi mật khẩu nay không đi vòng được nữa.** Trước đây màn hình *Đổi mật khẩu* chỉ hiện lên rồi thôi — gõ thẳng địa chỉ trang khác lên thanh địa chỉ là dùng tiếp bình thường, **không bao giờ phải đổi**. Nay phần mềm chặn thật: người có mật khẩu mặc định `1`, hoặc vừa được Quản trị viên đặt lại mật khẩu, **chỉ vào được đúng màn hình đổi mật khẩu** cho tới khi đổi xong
    + **Xem hồ sơ cán bộ nay đúng phạm vi như xem danh sách.** Danh sách nhân sự vốn chỉ cho xem người **cùng phòng**, nhưng đường xem **từng người** lại không kiểm — nghĩa là số điện thoại, email, mã IPCAS, tên đăng nhập Payment của **toàn cơ quan** vẫn lấy ra được. Nay hai đường dùng chung một luật. Quản trị viên, Hậu kiểm viên, Giám đốc / Phó Giám đốc và nhân viên phòng Tổng hợp **không đổi gì**
    + **Trang web nay chống được kiểu lừa bấm nút.** Không có lớp bảo vệ này, kẻ xấu dựng một trang mồi và đặt trang thật của hệ thống **trong một khung trong suốt** đè lên; bạn tưởng mình bấm nút trên trang mồi nhưng thực ra đang bấm nút *Xoá* hoặc *Duyệt* trong phiên đăng nhập thật của chính mình. Không ảnh hưởng gì tới thao tác bình thường
    + **Nhật ký đăng nhập nay giữ 12 tháng thay vì 30 ngày.** Một vụ dò mật khẩu bị phát hiện muộn hơn một tháng thì dấu vết đã bị chính hệ thống xoá mất — không còn gì để truy. Nhãn trên màn hình đã sửa theo
    + **Chưa sửa trong đợt này — việc lớn nhất còn lại: hệ thống vẫn chạy HTTP, chưa có HTTPS.** Nghĩa là mật khẩu đăng nhập và dữ liệu đi qua mạng nội bộ ở dạng **đọc được** với ai có khả năng nghe trộm đường truyền. Sửa việc này **không nằm trong phần mềm** — cần dựng máy chủ web (IIS/nginx) đứng trước và xin chứng thư số nội bộ. Đây là việc nên đưa vào kế hoạch gần
    + Chưa sửa (mức nhẹ, đã ghi lại): nâng cấp một số thư viện cũ; mã kết nối Extension CITAD chưa có hạn dùng; mật khẩu dài quá 72 ký tự bị cắt âm thầm
    + Toàn bộ **583 test** chạy đạt (thêm 16 test mới khoá lại đúng các lỗ hổng vừa vá)

- 20/08/2026 Đối soát CITAD↔IPCAS - **Sửa 2 lỗi làm mất/nhầm lệnh Napas-PSS_MDP khi đối soát, thêm nút "Xuất tất cả lệnh"**:
    + ⚠️ **Lỗi thật, gây sai số liệu**: file Hub (PaymentHub) chứa lệnh Napas/PSS-MDP bị **đọc ra 0 dòng hoàn toàn, không báo lỗi gì** — dòng "Tổng số giao dịch:N" đầu file bị nhận nhầm thành dòng tiêu đề cột, khiến cả sheet bị bỏ qua. Đã xác nhận thực tế bằng dữ liệu ngày 19/08/2026: 12 lệnh Napas/PSS-MDP đúng ra phải báo "chênh lệch" (vì cố tình không nạp vào CITAD) thì bị mất trắng, không hiện ở đâu cả trong báo cáo
    + ⚠️ **Lỗi thứ 2 liên quan**: khi sửa xong lỗi trên, phát hiện thêm — mã "Số thành công" (txid) bên IPCAS **dùng chung cho nhiều lệnh khác nhau** trong cùng 1 phiên (lệnh giá trị cao Napas trùng túi với hàng loạt lệnh giá trị thấp không liên quan). Trước đây chỉ so khớp theo txid nên lệnh giá trị thấp "đè mất" lệnh Napas thật khi trùng mã — đã sửa: so khớp thêm theo loại kênh (IH/IL) **và** số tiền, chỉ khi khớp đủ cả 3 mới coi là cùng 1 lệnh. Số lệnh khớp không đổi, chỉ những lệnh THẬT SỰ lệch mới hiện đúng, đủ
    + **Xuất Excel giờ có thêm nút "Xuất tất cả lệnh"** — trước đây chỉ xuất được các lệnh lệch, nay xuất được ĐỦ cả lệnh khớp lẫn lệch trong 1 file, map đúng từng cặp CITAD ↔ Agribank theo hàng, lệch đẩy lên đầu bảng và bôi vàng để dễ nhìn. File có thể tới ~38.000 dòng nhưng xuất chỉ mất khoảng 6 giây (đã tối ưu riêng, không ảnh hưởng gì tới nút "Xuất Excel" chênh lệch cũ)
    + **Chống treo khi xuất file lớn**: nút xuất nay **khoá lại và quay vòng** trong lúc chờ, không còn cảnh bấm xong không thấy gì nhúc nhích rồi bấm lại nhiều lần (mỗi lượt bấm lại chiếm thêm một suất xử lý nặng của máy chủ, tự làm chính mình chậm thêm). Thời gian chờ tối đa cho nút "Xuất tất cả lệnh" nâng từ 1 phút lên 5 phút để phòng lúc nhiều người cùng xuất. Riêng phần sinh file đã rút từ **21 giây xuống ~6 giây**, nên cũng đỡ chiếm chỗ của các việc nặng khác đang chạy cùng lúc (in bìa, sinh đơn nghỉ phép...)
    + Đổi tên cột "Key Agribank" thành **"Số GD (Agribank)"** cho rõ nghĩa — cả màn hình chấm, tab Lịch sử, lẫn file Excel xuất ra
    + **5 lỗi nhỏ khác phát hiện khi rà soát cùng đợt, đã sửa**: file CITAD đuôi lạ nay báo lỗi rõ thay vì bỏ qua im lặng; cột ngày IPCAS đọc sai khi tên ngân hàng có dấu phẩy; khoá so khớp file Hub-CITAD không khớp được nếu mã có lẫn chữ cái; lỗi đọc ô Excel nay có ghi log thay vì nuốt hoàn toàn; nhãn trạng thái ở màn hình và file Excel dùng chung 1 nguồn thay vì 2 bản chép tay dễ lệch nhau
    + Toàn bộ thay đổi đã kiểm chứng lại bằng đúng bộ dữ liệu thật (CITAD + IPCAS + Hub ngày 19/08/2026) — số liệu khớp/lệch không đổi so với trước khi sửa các lỗi nhỏ, chỉ có 2 lỗi lớn ở trên là thay đổi số liệu (theo hướng ĐÚNG hơn — hiện ra chênh lệch thật trước đây bị giấu mất)

- 20/08/2026 Đối chiếu CITAD - **Bỏ nốt dòng "Ebanking" khỏi file Excel xuất ra**:
    + Đợt 14/08 đã bỏ ô nhập Ebanking khỏi màn hình (kênh này không còn dùng) nhưng **sót**: dòng "Ebanking" vẫn được in ra trong file Excel tải về và trong bảng xem trước khi xuất — nay bỏ luôn cả hai chỗ, đồng bộ với màn hình
    + Không đổi số liệu Chênh lệch — dòng Ebanking từ trước tới nay vốn **không được cộng** vào tổng CITAD (chỉ in ra tham khảo), nên bỏ dòng không ảnh hưởng con số báo cáo
    + Số liệu Ebanking của các ngày đã chấm trước đây vẫn nằm nguyên trong dữ liệu đã lưu, chỉ không còn hiện/in ra đâu nữa

- 19/08/2026 Chấm đối chiếu ACH - **Sự cố "Mất kết nối tới máy chủ"**
    + ⚠️ **Chạy lại khi lượt trước chưa dừng hẳn nay bị chặn.** Đây chính là lý do lần 2 không phản hồi: màn hình bỏ cuộc **không có nghĩa là máy chủ đã dừng** — lượt 1 vẫn chạy tiếp, bấm chạy lượt 2 là **hai lượt đối chiếu cùng lúc** trên một máy đã đuối. Nay phần mềm hỏi lại máy chủ trước, còn lượt cũ thì báo rõ và yêu cầu bấm **Dừng** trước
    + **Nút *Dừng* nay ở lại trên màn hình khi mất liên lạc** (trước đây tự ẩn đi). Ẩn nút đó là cắt mất đường duy nhất để dừng lượt chạy cũ đang chiếm máy
    + **Bước giải nén nay có báo cáo tiến độ**: đang giải nén file nào, bằng công cụ gì, mất bao lâu, đọc được bao nhiêu dòng. Trước đây từ lúc bắt đầu B4 tới lúc xong là một khoảng **lặng hoàn toàn** — không phân biệt được "đang chạy nặng" với "đã chết"
    + ⚠️ **Cảnh báo mới: nếu máy chủ không cài 7-Zip (hoặc giải nén thất bại), phần mềm phải dùng cách dự phòng ngốn bộ nhớ gấp khoảng 7 lần kích thước file** — hai file cùng lúc có thể lên tới vài GB và làm máy chủ chậm hẳn. Trước đây việc rẽ sang cách này **không hiện ở đâu cả**, chỉ nằm trong file nhật ký kỹ thuật. Nay hiện ngay trên màn hình. **Nếu thấy cảnh báo này, hãy cài 7-Zip lên máy chủ**
    + Cùng lúc áp cho cả bước đọc GL02 và MIS_đến, không riêng MIS_đi — ba bước dùng chung một cách giải nén
    + **Chưa sửa trong đợt này**: cách dự phòng vẫn nạp trọn file vào bộ nhớ (chữa gốc cần bộ dữ liệu thật để đối chứng); và lúc nhận file tải lên, máy chủ vẫn ghi cả bộ file xuống đĩa theo cách làm mọi menu khác phải chờ. Xem *Implementation-notes* mục Z1
    + **Nguyên nhân gốc chưa chốt.** Cần file `logs/backend.log` trên máy chính quanh 13:38 ngày 19/08 để biết chắc. Đợt này bảo đảm: lần sau tái diễn thì bằng chứng nằm ngay trên màn hình
    + Toàn bộ **546 test** chạy đạt (thêm 19 test mới)

- 18/08/2026 Toàn hệ thống - **Rà soát MENU và các tính năng**
    + **Đợt này không thêm menu nào.** Nhưng có **một thay đổi làm lịch trực sinh ra khác trước** — đọc mục *Phân lịch trực* dưới đây trước khi tạo lịch tháng mới
    + ⚠️ **Nút *Nhập DB* (màn hình Quản lý User) trước đây ghi đè cả số ngày phép đã dùng của mọi người.** File .db nhập vào mang theo **toàn bộ** cột, kể cả *số ngày phép đã dùng*, *vai trò* và *mật khẩu*. Nhập lại một file cũ là **xoá sổ số ngày phép đã dùng của cả cơ quan**, mà không có cách nào hoàn tác — trong khi màn hình *Quỹ phép* có sẵn cơ chế nhập theo đợt và **hoàn tác được**. Nay: người đã có trong hệ thống thì **giữ nguyên số ngày phép**, chỉ tài khoản **mới** mới lấy theo file
    + ⚠️ **Cũng nút đó: nay chỉ Quản trị viên bấm được** (như nút *Xuất DB*). Trước đây ai được cấp quyền *Nhập DB* đều bấm được, mà file .db đặt được **mật khẩu và vai trò cho bất kỳ ai** — tức là người đó **tự nâng mình lên Quản trị viên** bằng một file sửa tay. Không cần biết kỹ thuật, chỉ cần sửa file
    + **Nhập DB nay bỏ qua dòng hỏng thay vì nuốt lặng**: dòng ghi sai tên vai trò, dòng trỏ vào phòng ban không có trên hệ thống này, dòng thiếu Mã cán bộ — đều bị bỏ và **hiện ra danh sách** để bạn biết đã sót ai. Trước đây chúng vẫn được ghi vào, tạo ra tài khoản hỏng mà không ai biết
    + ⚠️ **Phân lịch trực — ngày lễ khai ở màn hình *Nghỉ phép* nay lịch trực mới thấy.** Trước đây hai chỗ dùng hai danh sách ngày lễ **riêng biệt không biết nhau**: khai ngày lễ ở *Nghỉ phép* xong, lịch trực **vẫn xếp người trực ngày đó** và vẫn tính cut-off cuối tháng như ngày làm việc, trừ khi có người nhớ bấm *Seed ngày lễ* bên tab Ngày đặc biệt. Nay tự động lấy cả hai. **Ngày đã khai riêng ở tab Ngày đặc biệt vẫn ưu tiên**, nên ngày lễ được hoán đổi thành ngày đi làm bù không bị hiểu nhầm
    + ⚠️ **Phân lịch trực — người có đơn nghỉ phép đã duyệt nay không bị xếp trực nữa.** Trước đây muốn tránh thì phải vào Sổ trực khai vắng mặt **lần thứ hai**, đúng người, đúng từng ngày — không ai nhớ và cũng không có gì nhắc. Chỉ **đơn đã duyệt xong** mới tính; đơn đang chờ duyệt vẫn xếp trực bình thường. **Hệ quả cần biết: lịch tạo lại từ giờ sẽ khác lịch cũ** ở những ngày có người nghỉ phép hoặc có ngày lễ
    + **Sửa *Ngày vào ngành* ở màn hình Quỹ phép nay bị kiểm tra định dạng**: trước đây gõ `01/07/2020` hay bất kỳ chữ gì cũng lưu được, rồi **số ngày phép năm tính ra sai** ở nơi khác, lúc khác — rất khó lần ra. Nay chỉ nhận ngày hợp lệ, không nhận ngày ở tương lai, và **ghi vào Nhật ký thao tác kèm giá trị cũ** (đổi ngày này là đổi hạn mức phép của người ta)
    + **Nhật ký đăng nhập nay chỉ còn việc đăng nhập**: trước đây mỗi lần tải file backup lại chèn thêm một dòng vào đó, làm thống kê số lượt đăng nhập đếm dôi và đẩy nhật ký thật ra khỏi trang đầu. Nay ghi vào **Nhật ký thao tác** cho đúng chỗ
    + **Sửa rò rỉ file tạm ở *Đối chiếu điện SWIFT***: mỗi lần xuất Excel bị lỗi là để lại một file rác trên máy chủ **vĩnh viễn**, không ai dọn. 8 chỗ cùng một lỗi, nay gộp về một chỗ nên không thể sót lại
    + **Thư mục kết quả tạm nay được dọn đều đặn 6 tiếng một lần.** Trước đây chỉ dọn *khi có người mở đúng menu đó* — nghỉ dùng một tháng thì kết quả của tháng trước nằm nguyên trên ổ đĩa. Kèm theo: sửa lỗi *Đối chiếu ACH* để lại thư mục mồ côi sau mỗi lần khởi động lại (kiểm tra trên máy này thấy 2 thư mục còn sót từ 13/08)
    + **Hai file nhật ký `logs/backend.log` và `logs/frontend.log` nay có xoay vòng** (quá 20 MB thì tách, giữ 3 đời). Trước đây **không có gì dọn chúng cả** — máy chạy liên tục vài tháng là file vài GB. Lưu ý: chỉ xoay được **lúc khởi động lại**, vì đang chạy thì Windows không cho đổi tên file đang mở
    + ⚠️ **Nếu có cấu hình thư mục backup phụ (`BACKUP_EXTRA_DIR`): mỗi máy chủ phải dùng một thư mục riêng.** Phần mềm tự xoá bản backup quá hạn ở đó; hai máy cùng trỏ vào một thư mục thì máy này xoá bản của máy kia mà cả hai đều tưởng mình còn đủ lịch sử. Đã ghi cảnh báo ngay trong `.env.example`
    + **Chưa sửa (để lại có chủ đích)**: sửa *số tờ* của chứng từ đã đóng tập ở menu *Bàn giao chứng từ* vẫn làm lệch với bảng *Tra cứu lưu trữ* — hai màn hình đọc hai nguồn khác nhau. Người dùng quyết định để lại đợt sau
    + Toàn bộ **527 test** chạy đạt (thêm 27 test mới cho riêng đợt này)

- 18/08/2026 Toàn hệ thống - **Rà soát và vá lỗi bảo mật, gỡ nghẽn khi nhiều người dùng cùng lúc**:
    + **Đợt này không thêm menu nào, không đổi cách làm việc hằng ngày của ai.** Chỉ sửa những chỗ hở bên trong. Đọc phần in đậm dưới đây là đủ biết cái gì có thể khác đi
    + ⚠️ **Vá lỗ hổng nặng ở *Chấm đối chiếu ACH***: tên file người dùng tải lên được dùng thẳng làm tên file lưu trên máy chủ. Ai cố tình đặt tên file kiểu đường dẫn (`..\..\` hoặc `C:\...`) là **ghi đè được file bất kỳ trên ổ đĩa máy chủ**, kể cả file của chính phần mềm. Nay tên file bị cắt sạch phần đường dẫn trước khi lưu. **Người dùng bình thường không thấy khác gì**, trừ một điểm: chọn nhầm **hai file trùng tên** trong cùng một lượt thì nay báo lỗi rõ ràng thay vì âm thầm bỏ mất một file
    + **Xem trước / tải đơn nghỉ phép không còn làm cả hệ thống đứng**: ba thao tác này phải nhờ Word dựng file PDF, mất 5–7 giây mỗi lần. Trước đây vài người cùng bấm là **mọi menu khác** (chấm công, bàn giao, sổ trực) cũng đứng chờ theo, mà nhìn bề ngoài chỉ thấy "máy chậm". Nay việc nặng chạy trong khu riêng, tối đa 4 việc cùng lúc; người xem đơn vẫn phải chờ đến lượt nhưng **không kéo theo ai**. Chấm 459901 và Đối chiếu song phương cũng sửa cùng kiểu
    + **Mọi ô tải file nay có giới hạn dung lượng** (mặc định 200 MB một file, riêng ACH giữ nguyên 500 MB cho cả lượt). Trước đây không có giới hạn nào — một file quá lớn là máy chủ hết bộ nhớ và **cả phần mềm dừng**, mọi người bị đá ra. Nay file quá cỡ bị từ chối kèm thông báo tiếng Việt, không ảnh hưởng ai khác. Con số này chỉnh được trong `.env` nếu có nghiệp vụ cần file lớn hơn
    + ⚠️ **Nút *Xuất file DB người dùng* (màn hình Quản lý User) nay chỉ Quản trị viên bấm được.** File đó chứa mật khẩu đã mã hoá của **toàn bộ** tài khoản. Trước đây ai được cấp quyền *Xuất Excel danh sách* là bấm được luôn, mà việc bấm **không để lại dấu vết ở đâu cả**. Nay ngoài Quản trị viên thì báo lỗi, và cả hai nút xuất (Excel lẫn DB) đều ghi vào **Nhật ký hệ thống**
    + **Không ai tự nâng quyền cho mình được nữa**: trước đây người được cấp quyền *Sửa tài khoản* có thể mở tài khoản của chính mình và đổi vai trò thành *Quản trị viên cấp 1*. Nay chỉ sửa được tài khoản có vai trò **thấp hơn mình**, và không đổi được vai trò của chính mình. Quản trị viên cấp 1 và cấp 2 **làm việc y như cũ, không đổi gì**
    + **Nhập sai tên vai trò thì bị chặn ngay**: trước đây gõ thừa một dấu cách là tài khoản đó **mất sạch quyền** mà không báo lỗi gì — người dùng đăng nhập được nhưng bấm gì cũng bị từ chối, rất khó đoán nguyên nhân
    + **Nhật ký ghi đúng địa chỉ máy thật**: trước đây máy nào cũng có thể tự khai địa chỉ khác khi gọi thẳng vào máy chủ, tức là **nhật ký truy vết có thể do chính người bị truy vết viết ra**. Nay chỉ tin địa chỉ do phần mềm của mình chuyển tiếp
    + **Chặn dò mật khẩu theo máy**: trước đây chỉ đếm số lần sai theo *tên đăng nhập*, nên thử lần lượt mỗi tài khoản 4 lần là dò mãi không bị chặn. Nay đếm thêm theo máy gọi tới (20 lần sai trong 5 phút thì khoá 15 phút). **Người gõ nhầm mật khẩu vài lần vẫn không bị ảnh hưởng**
    + ⚠️ **Sửa cách dọn file backup cũ — trước đây khởi động lại nhiều lần trong ngày là mất sạch lịch sử một tuần.** Hệ thống tự backup **mỗi lần khởi động**, mà khi gặp sự cố thì nó tự khởi động lại tới 5 lần liên tiếp. Luật cũ giữ 7 file mới nhất ⇒ 5 bản chụp cách nhau vài giây đẩy hết bản của cả tuần đi. Cơ sở dữ liệu này **đã từng hỏng thật**, mà hỏng thì thường phát hiện muộn — cái cứu được là **bản của mấy ngày trước**, không phải bản của 3 phút trước
    + **Nay giữ: bản mới nhất của mỗi ngày trong 7 ngày gần nhất, cộng 5 bản mới nhất bất kể ngày.** Nhiều nhất khoảng 12 file (~14 MB), đổi lấy việc không bao giờ mất lịch sử vì khởi động lại
    + ⚠️ **Bản backup tự đặt tên (như `ksnb_truoc_nhomA_20260728.db`) nay KHÔNG BAO GIỜ bị xoá tự động.** Trước đây chúng nằm chung một rổ với backup tự động. Đây là bản người ta cố ý tạo trước khi làm việc nguy hiểm — thứ cần nhất khi có sự cố, và là thứ duy nhất không tự tạo lại được. **Muốn xoá thì tự vào thư mục `data/backups` xoá tay**
    + **Sửa dòng "Backup gần nhất" ở màn hình Nhật ký hệ thống — nó đang báo sai ngày.** Máy chính hôm nay hiện *28/07/2026* trong khi bản backup mới nhất là **hôm nay**, lệch ba tuần. Nguyên nhân: hệ thống sắp file theo thứ tự chữ cái nên tưởng file đặt tay là file mới nhất. Nay hiện đúng, và tách rõ *"5 bản + 2 bản đặt tay"*
    + Dọn 2 chỉ mục thừa còn sót lại từ lần đổi tên bảng nhân sự, và cập nhật thư viện Pydantic sang cách viết mới (105 → 0 cảnh báo của phần mềm mình; phần còn lại là của thư viện ngoài)
    + Toàn bộ **500 test** chạy đạt (thêm 39 test mới, mỗi test khoá đúng một lỗ hổng vừa vá — đã kiểm chứng là **đỏ khi gỡ bản vá ra**)
    + ⚠️ **Việc cần làm bằng tay, phần mềm không tự làm thay được**: rất nhiều tài khoản đang để mật khẩu quá đơn giản. Đây là việc vận hành, xem mục riêng khi triển khai

- 17/08/2026 Phòng Thanh toán - **Menu mới: Sổ trực cuối ngày**:
    + **Việc này để làm gì**: mỗi ngày hai giao dịch viên trực cuối ngày ghi lại tình hình ca trực, một kiểm soát viên xem và xác nhận. Trước nay ghi ra sổ giấy, không tra lại được và không ai biết hôm nào chưa ai ghi
    + **Vào bằng menu *Sổ trực cuối ngày*** ở cột trái (nằm dưới *Phân lịch trực*)
    + **Cách làm hằng ngày**:
        1. Một trong hai người trực mở menu, chọn ngày, chọn tên **GDV 1** và **GDV 2**, gõ ghi chú ca trực, chọn **KSV** sẽ xác nhận
        2. Bấm **Chuyển KSV xác nhận**. Người trực còn lại vào bấm **Xác nhận phiên trực** cho biết đã xem — bước này *không chặn gì*, KSV vẫn duyệt được ngay
        3. KSV mở lên, xem, bấm **Xác nhận** là xong
    + **KSV thấy chưa ổn thì có 2 nút**: *Yêu cầu sửa lại* (trả về cho 2 GDV sửa rồi đẩy lại) và *Đề nghị huỷ* (khoá luôn ô nhập, GDV chỉ còn nút *Huỷ phiên trực*). ⚠️ **Cả hai đều chỉ là đề nghị** — KSV không tự đóng được phiên, **chỉ GDV mới bấm huỷ thật**. Huỷ rồi thì mở phiên mới cho đúng ngày đó, sổ cũ vẫn lưu trong Lịch sử
    + **Ghi sai đã duyệt xong vẫn sửa được** — bấm *Yêu cầu chỉnh sửa*. GDV bấm thì phải qua KSV duyệt lại; KSV tự bấm thì tự sửa tự chốt luôn
    + ⚠️ **Khoá theo đúng người, không theo chức danh.** Đã chọn ai làm GDV 1 / GDV 2 thì **chỉ đúng hai người đó** sửa được, người thứ ba mở lên chỉ xem. KSV cũng vậy: chọn ai từ đầu thì đẩy lại sau khi bị từ chối vẫn phải đúng người đó, không đổi sang người khác được. Lý do: sổ trực là chứng từ nội bộ, phải biết chính xác ai ghi và ai duyệt
    + **Không ai phải nhớ**: có việc chờ mình thì hiện ở khối *Công việc chờ xử lý* cột trái, gồm cả khi KSV vừa từ chối. Sau 16h mà chưa ai mở sổ hôm nay thì Trang chủ hiện dòng nhắc
    + **Nhắc nhẹ nếu Đối chiếu CITAD ngày đó chưa khớp** — chỉ cảnh báo, vẫn bấm xác nhận được; có sẵn nút mở thẳng sang lịch sử chấm CITAD của đúng ngày
    + Tab **Lịch sử** xem lại mọi ngày, **xuất Excel** theo khoảng ngày
    + Cấp quyền ở *Phân quyền theo nhóm*: **Sổ trực cuối ngày** (vào được menu) và **Xác nhận / Từ chối sổ trực** (được chọn làm KSV)
    + Không đụng tới menu nào khác — riêng nút ở màn *Công việc chờ xử lý* đổi chữ từ *Tới nơi xử lý* thành **Chuyển đến trang** cho cả 3 loại việc. Toàn bộ **461 test** chạy đạt (thêm 20 test mới)

- 17/08/2026 Quản lý User - **Nạp Ngày vào ngành cho cả cơ quan bằng một file Excel**:
    + **Vì sao cần**: ô *Ngày vào ngành* đã có sẵn trong màn hình Thêm/Sửa tài khoản từ lâu, nhưng trên máy chính **cả 80 người đều đang để trống**. Số ngày phép năm được tính từ ngày này — trống thì ai cũng bị coi là 12 ngày, kể cả người đã công tác 25 năm. Gõ tay 72 người thì vừa lâu vừa không cách nào biết đã sót ai
    + **Nay có nút *Nhập Ngày vào ngành*** ở màn hình *Quản lý User*, cạnh nút *Xuất Excel*
    + **Cách làm trên máy chính** (chỉ Quản trị viên):
        1. Vào **Quản lý User** → bấm **Nhập Ngày vào ngành**
        2. Bấm **Chọn file Excel** → chọn file `MA CB.xlsx`
        3. Hệ thống **xem trước ngay, chưa ghi gì cả**: hiện sẽ cập nhật bao nhiêu người, ai không khớp mã, ai bỏ trống ô ngày
        4. Xem xong thấy đúng thì bấm **Ghi vào hệ thống**. Thấy sai thì đóng lại, sửa file rồi chọn lại — chưa có gì bị đổi
    + **File cần có 2 cột: *Mã cán bộ* và *Ngày vào ngành*** (dạng `dd/mm/yyyy`). Các cột khác (STT, Họ và tên, Phòng, Chức vụ) có cũng được, không có cũng được. Dòng tiêu đề nhóm phòng xen giữa danh sách được tự bỏ qua
    + ⚠️ **Ghép người theo *Mã cán bộ*, không theo họ tên** — tên trùng nhau quá nhiều nên không tin được. Mã nào không có trong hệ thống thì phần xem trước liệt kê ra để kiểm, **hệ thống không tự tạo tài khoản mới**
    + ⚠️ **Mặc định KHÔNG đè lên người đã có ngày.** Ai đã điền sẵn (hoặc bạn vừa sửa tay) thì được giữ nguyên và liệt kê ở mục *"Đã có ngày khác — giữ nguyên"* để bạn tự đối chiếu. Chỉ khi chắc chắn file mới đúng hơn thì mới tick ô **Ghi đè**. Lý do: vài tháng sau nhập lại đúng file cũ là mọi chỉnh tay bị xoá sạch mà không một dòng thông báo
    + **Nhập lại nhiều lần vô hại** — lần thứ hai báo *"đã đúng, bỏ qua"* chứ không nhân đôi hay đổi gì
    + ⚠️ **Riêng file `MA CB.xlsx` hiện tại: 2 người bỏ trống ô ngày ngay trong file** — *Nguyễn Thị Hà Dương* và *Nguyễn Thanh Minh*. Hai người này phải vào Sửa tài khoản điền tay, hoặc điền vào file rồi nhập lại
    + Ngày nhập xong hiện luôn ở cột **Ngày vào ngành** trên bảng danh sách — cột này nằm ngay **bên phải cột Mã cán bộ**, chỉ hiện ngày (`01/04/1999`), không kèm số ngày phép nữa
    + **Sửa lỗi bảng danh sách bị chữ đè lên nhau**: các cột trước đây tự co lại khi bảng rộng hơn khung màn hình, chữ tràn sang ô bên cạnh. Nay mỗi cột giữ đúng bề rộng, chữ dài bị cắt bằng dấu `…`, và màn hình hẹp thì **cuộn ngang** thay vì bóp méo
    + Không đụng tới menu nào khác. Toàn bộ **441 test** của hệ thống chạy đạt (thêm 12 test mới cho riêng phần này)

- 17/08/2026 Phân lịch trực - **Sửa lỗi đếm số ca, cho thứ 7/CN đi làm, file Excel bám mẫu của phòng**:
    + ⚠️ **Sửa lỗi nặng: tạo lại lịch làm số ca phình lên.** Trước đây bấm *Tạo lịch* xem thử rồi tạo lại lần nữa thì hệ thống vẫn nhớ cả hai lần — tạo lại 3 lần cho một tuần là nó tưởng mọi người đã trực 45 ca trong khi thật ra chỉ 15. Xoá lịch cũng không trả lại. Vì **chia đều số ca là tiêu chí chính** nên ai bị cộng oan sẽ bị đẩy xuống cuối hàng ở mọi tuần sau, mà lịch vẫn *trông hợp lệ* nên không ai nhìn ra. **Nay xoá hoặc tạo lại đều trả số ca về đúng.** Số ca đang lệch sẵn từ trước thì dùng nút *Reset vòng xoay* ở tab Cài đặt để đưa về mốc sạch
    + **Sửa cảnh báo báo nhầm**: ngày quyết toán nào có người **trực phụ** biết song phương cũng bị báo *"dư người song phương"*, dù nhóm trực chính vẫn đúng một người. Người trực phụ về sớm nên không giữ vai này — nay không tính nữa
    + **Thứ 7 / chủ nhật đi làm thì khai "Ngày bù"**: tab *Ngày đặc biệt* → chọn ngày → loại **Ngày bù** → nhớ bấm **Xác nhận** (khai xong mà chưa xác nhận thì không sinh ca). Hôm đó sẽ có ca như ngày thường, hiện thêm hàng T7/CN trên bảng tuần, lên file Excel, đăng ký nguyện vọng được, và được tính khi dò 2 ngày cut-off cuối tháng
    + **Ba ô nhập ngày đổi thành ô chọn lịch** (Từ ngày / Đến ngày ở khai vắng mặt, và ô thêm ngày đặc biệt) — không phải gõ tay `YYYY-MM-DD` nữa, bấm biểu tượng lịch mà chọn, hiện theo dd/mm/yyyy
    + **File Excel làm lại theo đúng tờ giấy phòng đang dùng**: 5 cột thay vì 8, bỏ hết màu nền (in đen trắng cho rõ), cỡ chữ 24/18/16, mỗi ngày đúng một hàng, bảng căn giữa tờ giấy. Ngày quyết toán để **trực chính IN HOA đậm**, trực phụ chữ nghiêng nhỏ hơn ngay bên dưới trong cùng ô. Ngày nghỉ lễ ghi rõ *"(Nghỉ lễ: ...)"*
    + **Chức danh người ký khai được** ở tab Cài đặt (ô *Chức danh người ký*, cạnh ô tên) — đổi sang Phó Giám đốc không phải sửa phần mềm nữa. Để trống thì vẫn in "GIÁM ĐỐC"
    + **Màn hình hết nuốt cảnh báo**: trước đây tạo lịch xong chỉ báo *"Tạo N ca"*, ngày nào không lập được ca vì thiếu người trông y hệt ngày nghỉ lễ — đều là hàng trống. Nay hiện rõ thiếu ai, và hàng nghỉ lễ ghi lý do thay cho dấu "—"
    + ⚠️ **Ba chỗ còn hở, chưa sửa trong đợt này** (đều nằm trong menu Phân lịch trực, không lan sang tính năng khác):
        + **Cut-off / quyết toán rơi đúng vào thứ 7 làm bù thì ngày đó không sinh ca** — nhãn "Ngày bù" bị nhãn "Cut-off" ghi đè lên, hệ thống mất dấu là hôm đó có đi làm. Gặp trường hợp này thì xếp tay ca cho ngày đó
        + **Tuần vắt qua giao thừa (28/12 → 03/01)**: xoá lịch không trả hết số ca cho những ngày thuộc năm mới
        + Ngày vừa có ca đã xác nhận vừa có ca bản thảo, tạo lại lịch thì ca bị bỏ qua vẫn bị cộng số ca
    + Không đụng tới bất kỳ menu nào khác. Toàn bộ 429 test của hệ thống chạy đạt

- 14/08/2026 Nghỉ phép - **Ký đơn ngay trên bản in, phiếu tải về đổi sang PDF**:
    + **Tải lên ảnh chữ ký của mình trước đã**: vào tên mình ở góc trái → *Quản lý người dùng* → khung **Ảnh chữ ký**. Ảnh phải là **PNG nền trong suốt** (nền trắng sẽ che mất chữ trên đơn), tối đa 2 MB. Mỗi người tự tải ảnh của mình, không ai xem hay đặt hộ được
    + **Lúc gửi đơn**: bấm *Gửi đơn* → hiện ra **tờ đơn thật, đúng như lúc in** (không phải bản mô phỏng) với chữ ký của bạn đặt sẵn dưới ô *NGƯỜI ĐỀ NGHỊ*. **Kéo để đổi chỗ, kéo 4 góc để phóng to/thu nhỏ**, ưng rồi bấm *Ký và gửi đơn*
    + **Lúc phê duyệt** (Trưởng/Phó phòng và Ban lãnh đạo): y hệt như vậy — thấy cả chữ ký người trước đã ký, đặt chữ ký của mình vào ô của mình rồi bấm *Ký và phê duyệt*
    + ⚠️ **Lần mở popup đầu tiên của mỗi đơn chờ khoảng 5–7 giây** — đó là lúc Word dựng bản in. Các lần sau của cùng đơn đó gần như tức thì. Sửa người duyệt hay số ngày nghỉ thì dựng lại từ đầu
    + **Nút *Tải phiếu* nay ra file PDF** thay vì Word, chữ ký đã nằm sẵn trên đó. Máy chủ trục trặc không tạo được PDF thì hệ thống **tự tải bản Word không chữ ký** kèm thông báo, không để ai kẹt lại
    + **Chưa tải ảnh chữ ký vẫn dùng bình thường** — popup báo chưa có ảnh, gửi/duyệt vẫn xong, chỉ là ô ký để trống như trước nay vẫn thế
    + **Đổi hoặc xoá ảnh chữ ký cá nhân KHÔNG làm đổi các đơn đã ký** — mỗi đơn giữ bản sao ảnh tại đúng thời điểm ký. Nộp lại đơn bị từ chối thì chữ ký của người duyệt cũ bị xoá (tờ đơn đã khác ngày, khác số ngày phép)
    + ⚠️ **Chưa ký được ở hai chỗ**: *duyệt hàng loạt* (chọn nhiều đơn duyệt một lượt — không thể đặt chữ ký cho từng tờ) và *bước Tổng hợp* (ô "XÁC NHẬN CỦA P. TỔNG HỢP" trên mẫu không có dòng tên người ký). Cần ký thì mở từng đơn ra duyệt
    + ⚠️ **Máy chính phải có Microsoft Word** và phải chạy lại `deploy.bat`/`start.bat` để cài 2 thư viện mới. Chưa cài thì popup báo lỗi và lui về bản Word
    + ⚠️ **Phần kéo–thả bằng chuột chưa được thử trên máy thật** — phần dựng file và đặt chữ ký đã chạy đúng đầu-cuối, nhưng thao tác kéo trên màn hình cần người dùng xác nhận giúp. Có gì lệch báo lại ngay

- 14/08/2026 Tra cứu lưu trữ - **Sửa được cả cột Ngày ngay trên bảng**:
    + Trước đây chỉ sửa được cột *Số chứng từ*; ngày ghi sai thì phải sửa từ khâu bàn giao. Nay **gõ thẳng vào ô Ngày** trên bảng rồi bấm *Lưu thay đổi*
    + **Sửa ngày ở đây KHÔNG đụng tới số liệu bàn giao gốc của phòng nguồn** — chỉ đổi ngày ghi trên bìa tập. Báo cáo khối lượng bàn giao giữ nguyên
    + ⚠️ **Mỗi dòng phải còn ít nhất một ngày.** Xoá sạch ngày của một dòng thì hệ thống báo lỗi và **giữ nguyên số đang nhập** để sửa lại — nếu cho lưu, tập đó sẽ biến mất khỏi bảng trong khi vẫn nằm trong dữ liệu
    + Hai nút *Lưu thay đổi* / *In danh sách* chuyển sang **bên trái** bảng, kèm dòng nhắc cách sửa

- 14/08/2026 Cài đặt - **Sửa lỗi cài thư viện báo nhầm thành "lỗi mạng"**:
    + **Triệu chứng**: chạy `start.bat`/`deploy.bat` báo *"kiem tra ket noi internet"* trong khi mạng hoàn toàn bình thường
    + **Nguyên nhân**: một dòng ghi chú **có dấu tiếng Việt** trong `requirements.txt`. Công cụ cài thư viện đọc file này theo bảng mã Windows, gặp chữ có dấu là chết ngay **trước khi** kịp gọi ra mạng — nên thông báo lỗi chỉ đoán mò
    + Nay hai file `.bat` **nói đúng nguyên nhân**, và có **chốt chặn tự động** không cho lọt chữ có dấu vào `requirements.txt` nữa

- 14/08/2026 Đối chiếu CITAD - **Khoá nhập tay 5 Cổng và PaymentHub**, thêm nguồn quét Napas/PSS-MDP:
    + ⚠️ **5 bảng Cổng CITAD và bảng PaymentHub từ nay KHÔNG gõ tay được nữa** — chỉ nạp bằng nút *Nạp CITAD* / *Nạp PaymentHub* qua Extension. Mục đích: không để sửa tay số liệu trên bản đang chấm
    + ⚠️ **Hệ quả cần biết trước: không còn cách nhập dự phòng cho hai bảng này.** Hôm nào Extension đọc sai hoặc không chạy thì phải xử lý ở Extension chứ không gõ đè lên được. Gặp trường hợp đó, báo ngay để xử lý trong ngày thay vì cố chấm tiếp
    + **Bảng Napas / PSS-MDP vẫn sửa tay bình thường** — không nằm trong diện khoá
    + **Tab *Lịch sử* chuyển thành chỉ xem** — mở một bản đã chấm ra xem thì không sửa hay lưu đè được. Bấm *Quay lại chỉnh sửa* để thoát chế độ xem và nhập mới cho hôm nay
    + **Thêm cách lấy Napas/PSS-MDP thứ hai**: quét thẳng từ trang CITAD *Kiểm soát yêu cầu quyết toán lô đến* (Cổng 1), song song cách cũ qua PaymentHub. Dùng nguồn nào cũng được, không xung đột
    + **Ô nhập Ebanking đã bỏ khỏi màn hình** — số liệu Ebanking của các ngày đã lưu trước đây **vẫn giữ nguyên**, vẫn xuất ra Excel đầy đủ, chỉ là không nhập mới được nữa. ⚠️ **Phần "vẫn xuất ra Excel" nay không còn đúng**: dòng Ebanking đã bỏ nốt khỏi file Excel ngày 20/08/2026 — xem entry đầu file
    + Giao diện: bảng chênh lệch đưa lên đầu trang, tách riêng hai khung *LỆNH ĐI* / *LỆNH ĐẾN*, ô đã có số liệu đậm nền hồng cho dễ nhìn, và một số chỉnh về viền/khoảng cách
    + ⚠️ **Phải tải lại `.zip` và cài lại Extension (bản 2.17)** — vào `/doi_chieu_citad` → **Tải Extension**, giải nén, *Load unpacked* lại. Không cài lại thì nút *Nạp CITAD* không lấy được Napas/PSS-MDP từ nguồn mới

- 14/08/2026 Đối chiếu ACH - **Sửa nút "Chạy đối chiếu" bấm vào là báo lỗi đỏ, không chạy được**:
    + **Triệu chứng**: chọn đủ bộ file, phần kiểm tra file báo xanh hết, nhưng bấm *Chạy đối chiếu* thì hiện thông báo đỏ và không có gì xảy ra. Giống gọi vào một số điện thoại in sẵn trên tờ rơi mà tổng đài chưa bao giờ đấu nối — mọi khâu trước đó vẫn bình thường vì chúng chạy xong **trước** cú gọi
    + **Nguyên nhân**: phần giao diện gọi tới một chức năng gửi file mà bên trong hệ thống **chưa bao giờ được viết ra**. Đây không phải lỗi mới phát sinh: tính năng chọn file từ máy rồi bấm Chạy **chưa từng chạy được** kể từ khi module ACH được viết lại
    + **Vì sao không ai phát hiện sớm hơn**: toàn bộ bài kiểm tra tự động của module ACH đều gọi thẳng vào phần lõi, **không đi qua đúng khâu bị hỏng**. Càng nhiều bài kiểm tra xanh càng dễ tưởng là an toàn
    + Nay đã nối đúng khâu đó, và **nới thời gian chờ lên 10 phút** riêng cho lần gửi này vì bộ file ACH một ngày có thể tới hàng trăm MB — các màn hình khác giữ nguyên 1 phút như cũ, không đổi gì
    + Thêm **chốt chặn tự động** quét toàn bộ giao diện, bắt buộc mọi lời gọi tới phần lõi phải trỏ đúng chức năng có thật. Cùng loại lỗi này ở **bất kỳ màn hình nào** sẽ bị chặn ngay lúc lập trình, không đợi tới lúc người dùng bấm nút. Đã chạy lại toàn bộ **359 test**
    + Sửa luôn một câu **sai trong README**: tài liệu ghi bộ file được "ghi thẳng ra đĩa, không giữ trong RAM", thực tế **cả frontend lẫn backend đều giữ trọn bộ trong RAM** rồi mới ghi ra đĩa. Không đổi code, chỉ ghi lại cho đúng để người vận hành liệu RAM máy chính
    + ⚠️ **Còn tồn**: các bước SAU khi bấm Chạy (theo dõi tiến độ → dừng chờ xác nhận MIS_đi → tải file xác nhận → nộp lại → tải kết quả) **chưa một lần được chạy thật từ giao diện**, vì trước đây không ai tới được đó. Cần chạy thử trọn một phiên trước khi dùng chính thức

- 13/08/2026 Đối chiếu CITAD - Extension **bản 2.15**: nhiều tab tự nhận mã mới, bớt rác Nhật ký:
    + **Mở sẵn nhiều tab CITAD rồi mới tạo mã kết nối — nay chạy được.** Trước đây tab nào mở TRƯỚC lúc bấm *Tạo mã kết nối mới* sẽ kẹt với mã cũ, phải tự F5 từng tab. Nay mọi tab đang mở tự nhận mã mới ngay, không phải làm gì
    + ⚠️ **Dùng tab ẩn danh thì phải bật quyền trước — Chrome mặc định TẮT.** Vào `chrome://extensions` → Chi tiết → bật **"Cho phép ở chế độ ẩn danh"**. Chưa bật thì Extension **không chạy chút nào** trong tab ẩn danh: không lưu được, cũng không báo lỗi gì, nhìn y như Extension hỏng
    + Thông báo lỗi khi lưu thất bại nay **nói đúng lý do** (chưa cấu hình / mã bị thu hồi / lỗi mạng) thay vì luôn hiện *"Không kết nối server ()"* chung chung
    + **Nhật ký hệ thống bớt rác**: mỗi lần Extension gửi số liệu thành công không còn ghi một dòng nhật ký nữa — thao tác này lặp hàng trăm lần mỗi ca, làm trôi mất các dòng nhật ký có ý nghĩa của những phần khác. Việc **lưu bản đối chiếu vẫn được ghi đầy đủ** như cũ, và lần gửi **thất bại** (mã sai/bị thu hồi) vẫn ghi — đó mới là thứ cần theo dõi
    + ⚠️ **Phải tải lại `.zip` và cài lại Extension** — vào `/doi_chieu_citad` → **Tải Extension**, giải nén, *Load unpacked* lại

- 13/08/2026 Giao diện - Ô chọn file: **bấm vào cả dải màu là mở được**, hết cảnh phải nhắm đúng dấu `+`:
    + **Trước đây**: ô chọn file có một dải màu rộng, nhưng chỉ đúng **dấu `+` bé xíu ở góc phải** là bấm được. Bấm vào phần còn lại — chiếm hơn 90% diện tích và trông y hệt một cái nút — thì không có gì xảy ra. Giống cánh cửa kính lớn mà chỉ có mỗi ô nhỏ ở mép là đẩy được
    + **Nay**: bấm chỗ nào trên dải màu cũng mở hộp thoại chọn file. Con trỏ chuột cũng đổi thành hình bàn tay khi rê qua, để nhìn là biết bấm được
    + Áp dụng **một lần cho toàn bộ hệ thống** — tất cả ô chọn file ở 11 màn hình (ACH, CITAD, Song phương, 459901, SWIFT, Lưu trữ, Báo cáo, Nhân sự, Nghỉ phép, Chi nhánh TTQT…) đều được, kể cả màn hình thêm mới sau này
    + Các nút sẵn có trên dải màu (dấu `+`, nút tải lên, nút xoá danh sách) **giữ nguyên** cách dùng cũ. Không đổi quyền, không đụng dữ liệu. Đã chạy lại toàn bộ **361 test**
    + ⚠️ Lần đầu vào sau khi cập nhật, nếu vẫn thấy như cũ thì bấm **Ctrl+F5** — trình duyệt đang giữ bản giao diện cũ trong bộ nhớ đệm

- 13/08/2026 Nhật ký hệ thống - Đổi tên nút cho dễ hiểu, hết cảnh **bấm nút tưởng làm mới hoá ra lại lọc mất log**:
    + **Người dùng thật báo**: "ấn *Cập nhật* thì tự ẩn một số log". Thực ra **không log nào bị ẩn hay bị xoá** — nút *Cập nhật* là **nút lọc**, nghĩa là "chỉ cho tôi xem những thao tác sửa dữ liệu". Bấm vào thì mọi dòng thêm mới / xoá đều tạm ẩn đi, nhìn như danh sách bị mất bớt. Bấm *Tất cả* là hiện lại đủ
    + Nguyên nhân là cách đặt tên: nút làm mới trang lúc đó **chỉ có ký hiệu mũi tên tròn `↻`, không có chữ**, trong khi nút lọc lại mang đúng cái tên người ta quen hiểu là "tải lại"
    + Nay đổi lại cho khỏi nhầm: **`Cập nhật` → `Sửa`**, **`Ghi/Thêm` → `Thêm mới`**, **`↻` → `Làm mới`** (có chữ, giống hệt màn *Lịch sử lỗi & cảnh báo* — trước đây hai màn cùng chức năng lại ghi hai kiểu). Thêm chữ **"Lọc:"** đứng trước nhóm nút lọc và chú thích hiện ra khi rê chuột vào từng nút
    + **Chỉ đổi chữ trên nút.** Không đổi quyền, không đụng dữ liệu, không đổi file Excel xuất ra. Đã chạy lại toàn bộ **357 test**
    + ⚠️ **Còn tồn**: bộ lọc *Sửa* hiện vẫn bỏ sót một nhóm thao tác sửa — **huỷ đơn nghỉ phép, sửa ngày vào làm, sửa số ngày phép đã dùng, ngừng uỷ quyền, sửa chi nhánh TTQT, sửa lượt xem kho**. Sáu việc này **chỉ hiện khi chọn *Tất cả***, lọc kiểu nào cũng không thấy. Đợt này chỉ đổi tên nút nên chưa động vào; sẽ xử lý riêng

- 13/08/2026 Rà soát kỹ thuật - Sửa lệch múi giờ khi dọn nhật ký, gọn lại danh sách thư viện:
    + **Nhật ký cũ bị giữ lâu hơn hạn đúng 7 tiếng**: hệ thống ghi thời điểm vào nhật ký theo **giờ Việt Nam**, nhưng lúc dọn nhật ký quá hạn lại đem so với **giờ quốc tế** (chậm hơn 7 tiếng) — như hai cái đồng hồ lệch nhau. Không mất dữ liệu, không sai số liệu, chỉ là nhật ký đăng nhập (hạn 30 ngày) và nhật ký thao tác (hạn 365 ngày) sống dai hơn hạn 7 tiếng rồi mới bị xoá. Nay cả hai dùng chung một đồng hồ
    + Đã soi và **cố ý giữ nguyên** phần phiên đăng nhập với phần khoá tài khoản khi nhập sai mật khẩu: hai chỗ đó tuy cũng chạy theo giờ quốc tế nhưng ghi và so **cùng một loại giờ** nên không lệch. Sửa ẩu cho "đồng bộ" sẽ khiến mọi phiên đang đăng nhập được gia hạn thêm 7 tiếng và mọi tài khoản đang bị khoá được mở sớm 7 tiếng
    + **Gỡ thư viện `sqlalchemy`** khỏi danh sách cài đặt — không một dòng code nào dùng tới (dự án dùng SQL thuần), nhưng máy chính vẫn phải tải nó về mỗi lần danh sách thư viện thay đổi
    + **Thêm `requirements-dev.txt`** cho máy lập trình: máy chính giữ nguyên, chỉ cài đúng thứ cần để chạy; bộ chạy test (`pytest`) tách sang file riêng. Trước đây `pytest` không nằm trong danh sách nào cả, nên người mới cài theo đúng hướng dẫn rồi chạy test sẽ báo thiếu thư viện
    + Không đổi gì ở giao diện hay nghiệp vụ. Đã chạy lại toàn bộ **357 test**

- 13/08/2026 Kiểm thử tự động - Thêm CI chạy pytest trên GitHub + chốt chặn rò thư mục máy chủ:
    + **Từ nay mỗi lần push hoặc mở PR, GitHub tự chạy toàn bộ 357 test** trên máy Windows sạch. Trước đây chỉ chạy tay trên máy người sửa — quên chạy là lỗi lọt qua mà không ai biết
    + Thêm **chốt chặn** cho `/api/fs/browse` (API liệt kê cây thư mục máy chủ, đã gỡ ở bản này): nhánh `Cham_ILO1000` chưa gộp vẫn còn API đó và **không kiểm quyền**, ai đăng nhập cũng duyệt được ổ đĩa máy chủ. Khi gộp nhánh đó vào, hai file liên quan hoà nhau **không báo xung đột** — không ai có cơ hội thấy nó quay lại. Test này là dấu hiệu duy nhất
    + Đã thử ngược: dựng lại đúng kịch bản lỗ hổng quay lại → test **đỏ** kèm thông báo giải thích tại chỗ. Gỡ ra → **xanh** lại

- 13/08/2026 Deploy - Tự dò và dọn file code cũ còn sót trên máy đích:
    + **Vấn đề âm thầm từ trước tới nay**: `deploy.bat` chép bằng `robocopy /E` — chỉ thêm và ghi đè, **không bao giờ xoá**. File nào bị xoá khỏi dự án vẫn nằm lại vĩnh viễn trên máy chính
    + Nguy hiểm nhất là **trang giao diện**: chương trình nạp trang bằng cách quét thư mục `frontend/pages`, file nào còn trong đó là còn thành một trang. Một trang đã xoá vẫn mở được bằng địa chỉ cũ (bookmark, lịch sử trình duyệt) rồi vỡ vì API phía sau đã bị gỡ. Admin bị nặng nhất vì luôn qua mọi kiểm tra quyền
    + Nay `deploy.bat` thêm **bước 6/8**: tự so danh sách file giữa máy nguồn và máy đích, liệt kê thứ chỉ có ở máy đích, **hỏi trước khi xoá**. Trả lời `n` là giữ nguyên
    + **Chỉ tự xoá file `.py` cũ trong `backend/` và `frontend/`**. File loại khác — kể cả mẫu Word trong `templates/` — chỉ liệt kê ra để xem bằng mắt, không đụng tới, phòng trường hợp người dùng tự thêm mẫu trên máy chính
    + Đã áp dụng cho cả `deploy-test.bat` (hệ thống test cổng 9000) vì `deploy.bat` gọi tiếp file này
    + Áp dụng ngay khi deploy PR #31: 12 file của module ACH cũ sẽ được dọn tự động
    + Gom 3 file script phụ trợ ở thư mục gốc (`deploy_env_check.py`, `deploy_don_file_thua.py`, `import_users_csv.py`) vào thư mục **`scripts/`** cho gốc dự án gọn lại. `run.py` và `init_db.py` **giữ nguyên ở gốc** — lệnh `python run.py` / `python init_db.py` không đổi
    + Sửa kèm 1 lỗi có sẵn: `import_users_csv.py` trỏ database vào `ksnb.db` cạnh file thay vì `data/ksnb.db`, nên chạy là dừng ngay ở "Không tìm thấy database"
    + Gom tiếp tài liệu vào thư mục **`docs/`** (`DESIGN.md`, `SKILL.md`, `CONTRIBUTING.md`, `Implementation-notes.html/.md`, spec SWIFT). Ba file ở lại gốc: `README.md` (GitHub đọc từ gốc), `CLAUDE.md` (công cụ đọc từ gốc), **`Logs_update.md`** (deploy.bat chép sang máy chính để đọc ngay)

- 13/08/2026 Chấm đối chiếu ACH - Tách quyền "được chạy" khỏi quyền "được xem", bỏ chế độ chọn thư mục trên máy chủ:
    + **Lỗi phân quyền có thật**: ô tick **"Chạy đối chiếu ACH"** ở màn phân quyền nhóm trước đây **không có tác dụng gì** — tick hay bỏ tick, ai vào được menu ACH là chạy được. Nay tick vào mới được bấm Chạy / Chạy tiếp / Dừng; người không tick vẫn xem tiến độ và tải kết quả bình thường
    + **Bỏ nút "Chọn thư mục"**: nút này duyệt thư mục trên **máy chủ** chứ không phải máy người dùng — người ngồi máy khác không thể trỏ vào ổ đĩa của mình, và nó để lộ cây thư mục máy chủ cho mọi tài khoản đã đăng nhập. Nay chỉ còn một cách nạp dữ liệu: **mở thư mục trên máy mình, Ctrl+A (hoặc giữ Shift) chọn cả bộ file rồi kéo-thả / bấm Mở**
    + ⚠️ **Thay đổi thói quen làm việc**: trước đây kết quả tự được ghi vào thư mục con `Output` ngay cạnh dữ liệu gốc. Nay **không còn** — phải bấm tải từng file kết quả từ trang về. Đổi lại bộ file (150–250 MB) được gửi lên qua mạng mỗi lần chạy, nếu đường truyền chậm sẽ thấy lâu hơn ở bước upload
    + Đã chạy lại toàn bộ 356 test tự động, khởi động thật cả backend lẫn giao diện để xác nhận trang ACH không vỡ

- 13/08/2026 Nghỉ phép - Sửa **màn hình trắng khi chưa có đơn nghỉ phép nào** (PR #32):
    + **Người dùng thật báo**: tài khoản Chuyên viên chưa tạo đơn nào, vào tab *Của tôi* chỉ thấy trơ một dòng chữ "Không có đơn nghỉ phép nào." — không khung bảng, không tiêu đề cột. Nhiều người tưởng phần mềm lỗi hoặc chưa tải xong nên bấm F5 nhiều lần
    + Nay **khung bảng và tiêu đề cột luôn hiện** (STT, Ngày tạo, Loại, Trạng thái…), dòng "Không có đơn nghỉ phép nào." nằm gọn bên trong khung — nhìn ra ngay là "chưa có đơn", không phải "hỏng". Áp dụng cho mọi bảng đơn phép: *Của tôi*, *Chờ duyệt*, *Phòng tôi*, và cả kết quả lọc/tìm kiếm ở Dashboard trả về 0 dòng
    + ⚠️ **Còn tồn**: tab *Khai báo hộ* vẫn giữ kiểu cũ (chỉ hiện dòng chữ trần "Chưa có đơn nào được khai báo.") — sẽ xử lý ở đợt sau
    + Không đổi quyền, không đụng dữ liệu, không cần thao tác gì sau khi cập nhật

- 12/08/2026 Danh sách CN TTQT - Sửa lỗi **gõ tên chi nhánh vào ô tìm kiếm không ra kết quả nào**:
    + **Lỗi thật, đã ảnh hưởng 43/218 chi nhánh**: tên bắt đầu bằng chữ hoa có dấu — *Đống Đa, Mỹ Đình, Đà Nẵng, Nam Định…* — gõ vào ô tìm kiếm thì danh sách **trả về rỗng**, không một dòng cảnh báo nào, trông y như chi nhánh đó không có trong hệ thống. Các chi nhánh tên bắt đầu bằng chữ thường/không dấu vẫn tìm ra bình thường nên lỗi lọt lâu
    + Nguyên nhân: phần so khớp cũ chỉ biết hạ chữ hoa **A–Z**, gặp *Đ, Ô, Ê…* thì để nguyên — máy đem "Điện Biên" so với "điện biên" và coi là hai tên khác nhau
    + Nay so khớp đúng chữ tiếng Việt, **không phân biệt hoa thường**. Thêm luôn **tìm không dấu**: gõ `dien bien` hoặc `dong da` cũng ra kết quả
    + Lúc **nhập Excel** và **thêm / sửa tay** hệ thống tự chuẩn hoá cách lưu chữ có dấu, để không còn cảnh cùng một tên mà máy lưu hai kiểu khác nhau
    + **Không cần nhập lại dữ liệu, không cần thao tác gì** — 218 chi nhánh đang có tìm được ngay sau khi cập nhật. Chỉ đổi cách tìm, không đụng tới dữ liệu, giao diện hay quyền

- 12/08/2026 Toàn hệ thống - **Sắp xếp lại menu theo chức năng thay vì theo phòng**:
    + **Trước đây menu cấp 1 là tên phòng.** Muốn mở *Đối chiếu ACH* phải biết trước nó thuộc Phòng Thanh toán; người mới hoặc người kiêm nhiệm nhiều mảng phải mò từng phòng
    + Nay menu cấp 1 là **việc cần làm**:
        - **Quản lý chứng từ** → Bàn giao chứng từ / Đóng chứng từ / Lưu trữ
        - **Đối chiếu** → *Phòng Thanh toán* (Chấm 459901, Song phương, ACH, Đối chiếu CITAD cuối ngày, Đối soát chênh lệch CITAD cuối ngày) và *Phòng Swift* (Đối chiếu điện SWIFT)
        - **Báo cáo** → *Phòng KSNB & HTVH* (Báo cáo hậu kiểm, Báo cáo bàn giao chứng từ) và *Phòng Tổng hợp* (Báo cáo dữ liệu thanh toán)
        - **Nghỉ phép**, **Phân lịch trực**, **Danh sách CN TTQT** đứng riêng ngoài cùng, không còn nằm trong phòng nào
    + Tên phòng **chỉ còn ở tầng giữa** của hai menu Đối chiếu và Báo cáo — nơi cùng một loại việc nhưng mỗi phòng làm một kiểu. Chỉ hiện phòng đang thực sự có tính năng
    + **Quyền của mọi nhóm giữ nguyên 100%** — chỉ đổi cách sắp xếp, không đổi tên chức năng nào. Không ai bị mất hay được thêm quyền sau lần cập nhật này
    + ⚠️ **Màn *Phân quyền theo nhóm* đổi bố cục theo menu mới.** Đường đi cũ trong các log bên dưới không còn đúng — ví dụ quyền *Chuyển trả chứng từ cho GDV* trước ở *Phòng KSNB & HTVH → Bàn giao chứng từ*, **nay ở *Quản lý chứng từ* → Bàn giao chứng từ**. Quyền vẫn còn nguyên, chỉ nằm ở thẻ khác
    + Màn phân quyền có thêm nút **"Chọn tất cả" / "Bỏ chọn"** cạnh mỗi tên phòng. Nút này **chỉ tích các màn hình**, không tự tích các thao tác bên trong (tạo / xoá / xử lý file…) — muốn cấp thao tác vẫn phải tự tích, tránh lỡ tay cấp quyền chạy dữ liệu

- 12/08/2026 Lưu trữ - Thêm tab **"In bìa hồ sơ"** để in bìa hồ sơ lưu trữ (mẫu M01/LHS) hàng loạt từ file Excel tra cứu:
    + **Trước đây phải vào chương trình lưu trữ bấm in từng hồ sơ một.** 140 hồ sơ là 140 lần bấm, mỗi lần ra một file Word riêng
    + Nay vào *Quản lý chứng từ → Lưu trữ → tab **In bìa hồ sơ***, nạp file Excel tra cứu (`LT_HS_TRACUU_*.xls`) xuất thẳng từ chương trình lưu trữ. Phần mềm đọc file, hiện bảng để soát lại, tích chọn hồ sơ cần in rồi tải về **một file Word — mỗi hồ sơ một trang**, in một lượt. Ai muốn từng file riêng thì bấm nút **Tải ZIP (mỗi hồ sơ 1 file)**
    + Dữ liệu lấy từ đâu: **Mã vạch** = cột I (điền vào dòng *Ký hiệu thông tin* và dòng mã vạch); **dòng tiêu đề** = cột C; **Ngày mở** = ngày **đầu tiên** xuất hiện trong cột C (ví dụ *"Nhật ký chứng từ ngày 04/02/2025, 05/02/2025, 06/02/2025"* → ngày mở là **04/02/2025**); **Ngày công việc kết thúc** = cột F; **Số tờ** = cột G
    + **Bìa in ra giống hệt bìa của chương trình lưu trữ.** Đã đối chiếu với 2 file bìa gốc do chương trình lưu trữ tự sinh (kèm trong file zip người dùng gửi) — chữ trên bìa trùng khít từng ký tự, kể cả hồ sơ gộp nhiều ngày. Mẫu Word không bị đụng tới định dạng, căn lề, cỡ chữ hay font nào
    + ⚠️ **Máy in phải cài font "3 of 9 Barcode".** Không có font thì dòng mã vạch in ra thành chữ thường `*1000.P026.178074.1*` và **máy quét không đọc được**. Đây là yêu cầu sẵn có của mẫu bìa, không phải phát sinh mới — nhưng giờ in hàng loạt nên lỡ thiếu font là hỏng cả tập
    + Dòng nào trong Excel mà tên hồ sơ **không có ngày** thì ô *Ngày mở* để trống, và phần mềm **báo cảnh báo vàng kèm số thứ tự dòng** ngay trên bảng để soát lại trước khi in
    + Quyền: dùng chung quyền màn hình *Lưu trữ* (`menu.storage`), **không cần cấp thêm gì**

- 12/08/2026 Nghỉ phép / Kỹ thuật - Sửa lỗi **hai thư mục "Phòng Tổng hợp" trùng tên** trong `templates/` làm mẫu đơn theo chức danh không được dùng:
    + **Trong `templates/` đang có hai thư mục tên y hệt nhau là "Phòng Tổng hợp"** — nhìn trong Explorer thấy hai dòng giống hệt. Nguyên nhân: chữ có dấu tiếng Việt có hai cách lưu khác nhau bên trong máy (dạng dựng sẵn và dạng ghép dấu rời), Windows coi là hai tên khác nhau nên tạo ra hai thư mục
    + **Hậu quả**: chương trình tìm mẫu đơn nghỉ phép trong thư mục **rỗng**, nên các **mẫu đơn riêng theo chức danh** (nhân viên / trưởng phòng / giám đốc / phó giám đốc) nếu đặt vào thư mục thật sẽ **không bao giờ được dùng** — hệ thống lặng lẽ quay về mẫu chung, không báo lỗi gì. Hiện thư mục đó đang rỗng nên chưa ai gặp, nhưng cứ bỏ mẫu riêng vào là dính ngay
    + ⚠️ **Đính chính**: lần báo trước có ghi *"máy chỉ checkout từ git sẽ hỏng phiếu nghỉ phép"* — **không đúng**. In đơn nghỉ phép vẫn chạy bình thường vì có sẵn mẫu chung ở thư mục gốc để dùng thay. Lỗi thật chỉ ảnh hưởng mẫu riêng theo chức danh
    + **Đã xử lý**: xoá thư mục thừa (bản rỗng, không có file nào, không nằm trong git), **giữ thư mục đang chứa dữ liệu** (`Báo cáo giao dịch chuyển tiền qua Swift`). Đồng thời sửa cách chương trình dò đường dẫn để khớp được cả hai cách lưu, không phụ thuộc thư mục được tạo kiểu nào
    + ⚠️ **Khi thêm file mẫu mới**: **copy/paste vào thư mục đang có sẵn**, **đừng gõ tay tên thư mục** để tạo thư mục mới — gõ tay sẽ đẻ lại đúng thư mục trùng vừa xoá và lỗi quay lại y như cũ
    + Không đổi giao diện, không đổi quyền, không cần thao tác gì sau khi cập nhật

- 12/08/2026 Đối chiếu CITAD - Sửa lỗi lệch số liệu ngoại tệ do cắt xu USD/EUR:
    + **Lỗi thật, gây sai số liệu**: ô nhập số liệu (5 cổng, Payment, Napas, PSS-MDP, Ebanking) hiển thị số theo kiểu số nguyên — USD/EUR có phần xu (vd 2.954.592,79) bị **cắt mất phần xu khi hiển thị**, và chữ đã cắt này sau đó bị đọc ngược lại thành số liệu gốc, mất vĩnh viễn phần xu. Xác nhận thực tế: ngày 06/08/2026 lệch đúng 1 xu vì 3 khoản USD đều bị cắt trước khi cộng
    + Sửa để giữ nguyên phần xu khi hiển thị — áp dụng cho cả VNĐ (không đổi, luôn số nguyên) lẫn USD/EUR (giờ hiện đủ 2 chữ số thập phân nếu có)
    + Sửa luôn 1 chỗ sót: dòng **"CHÊNH LỆCH"** trên màn hình (và bảng xem trước khi xuất Excel) vẫn còn 1 công thức riêng cắt xu độc lập, chưa được sửa cùng lần trước — lệch thật kiểu +0,79 từng hiện nhầm thành "+0" (vẫn bôi đỏ đúng nhưng số hiện sai). Đã test lại bằng số liệu thật, hiện đúng
    + File Excel tải về không bị ảnh hưởng (backend luôn tính lại bằng số thực đầy đủ, độc lập với màn hình)

- 12/08/2026 Đối chiếu / Đối soát CITAD - Thêm bộ lọc Lịch sử theo ngày + tên người chấm, tự động refresh:
    + **Đối chiếu CITAD**: tab Lịch sử thêm ô lọc **"Tên người chấm"** (trước chỉ lọc được theo ngày). Cột "Người lưu sau cùng" đổi sang hiện tên đầy đủ thay vì tên đăng nhập
    + **Đối soát CITAD ↔ IPCAS**: tab Lịch sử trước đây **không có bộ lọc nào** (chỉ hiện 100 lần gần nhất) — nay thêm đủ 3 ô lọc **"Từ ngày chấm"/"Đến ngày chấm"/"Tên người chấm"**
    + **Tự động cập nhật Lịch sử**: trước đây phải bấm F5 tải lại cả trang thì tab Lịch sử mới thấy bản vừa lưu/đối soát. Nay ở **Đối chiếu CITAD**, ngay sau khi lưu thành công, Lịch sử tự nạp lại dữ liệu mới ở phía sau — **không tự chuyển tab**, đang ở tab nào vẫn ở nguyên tab đó. Bên **Đối soát CITAD ↔ IPCAS** cơ chế này vốn đã có sẵn từ trước, đã kiểm tra lại xác nhận vẫn hoạt động đúng
    + Đã sửa kèm 1 lỗi hiệu năng tự phát sinh khi thêm bộ lọc: câu truy vấn lịch sử đối soát bị mất giới hạn số dòng, tải hết cả bảng mỗi lần gọi kể cả khi không lọc gì — đã thêm lại giới hạn cho trường hợp không lọc (phổ biến nhất)

- 11/08/2026 Đối chiếu CITAD - Extension lên **bản 2.14**, sửa dứt điểm lỗi chọn nhầm bảng rỗng:
    + ℹ️ Đây là **bản chốt** của chuỗi 2.11 → 2.14: ba bản trước chẩn đoán chưa đúng vì không có dữ liệu thật từ trang Agribank. Bản này sửa theo đúng nguyên nhân đã xác nhận qua lệnh kiểm tra chạy trực tiếp trên trang — không phải lại một lần đoán nữa
    + Xác nhận qua console: trang có **nhiều bảng trùng cấu trúc cột** (cùng có cột "NH gửi") — bảng **đầu tiên** khớp tên cột lại **rỗng** (0 dòng, khả năng là bảng mẫu/bản sao ẩn phục vụ mục đích khác), còn bảng có dữ liệu thật (13 dòng) nằm ở vị trí khác trong trang
    + Extension trước đây chọn đại bảng đầu tiên khớp tên cột mà không kiểm tra bảng đó có dữ liệu hay không, nên luôn vớ trúng bảng rỗng — dù bảng thật vẫn còn nguyên, tưởng "không có kết quả"
    + Nay bỏ qua mọi bảng rỗng trước khi so khớp tên cột, chỉ chọn bảng vừa đúng tên cột vừa có ít nhất 1 dòng dữ liệu
    + ⚠️ **Phải tải lại `.zip` và cài lại Extension** — vào `/doi_chieu_citad` → **Tải Extension**, giải nén, *Load unpacked* lại

- 11/08/2026 Đối chiếu CITAD - Extension lên **bản 2.13**, tìm ra nguyên nhân thật khiến không đọc được cột "NH gửi":
    + Xác nhận qua lệnh kiểm tra trực tiếp trên trình duyệt (Console): cột "NH gửi" và "Số tiền" đều có sẵn trong bảng, chữ sạch — **không phải do tên cột lệch hay có icon** như 2 lần sửa trước (bản 2.11/2.12) từng đoán
    + Nguyên nhân thật: hàm dò cột tiêu đề chỉ tìm trong `<thead>` hoặc đúng dòng đầu tiên của bảng, nhưng bảng thật của trang này không đặt tiêu đề cột theo 1 trong 2 kiểu đó — dò trượt dù cột vẫn tồn tại. Nay dò mọi thẻ tiêu đề trong bảng, không giới hạn vị trí
    + ⚠️ **Phải tải lại `.zip` và cài lại Extension** — vào `/doi_chieu_citad` → **Tải Extension**, giải nén, *Load unpacked* lại

- 11/08/2026 Bàn giao chứng từ - Thêm nút **Chuyển trả GDV** để hậu kiểm chủ động trả chứng từ về cho giao dịch viên:
    + **Trước đây chứng từ đã xác nhận chỉ ra khỏi kho được khi giao dịch viên chủ động xin mượn.** Hậu kiểm cầm chứng từ trên tay, thấy thiếu chữ ký hay sai sót, muốn trả về cho cán bộ thì không có nút nào — phải nhờ chính cán bộ đó vào bấm *Mượn lại* rồi mình duyệt, vòng vèo và sai bản chất sự việc
    + Nay ở **bảng lịch sử của từng ô** (bấm vào ô trong lưới), phần *THAO TÁC* có thêm nút tím **"↪ Chuyển trả GDV"**. Nút **chỉ hiện với ô đang ở trạng thái *Đã xác nhận*** — ô đang chờ, đang mượn hay bị từ chối đều không có
    + **Bắt buộc nhập lý do chuyển trả**, không nhập thì không bấm được. Lý do hiện ngay trong dòng lịch sử của ô, ai cũng đọc được
    + Bấm xong ô chuyển sang **Đang mượn** (ô tím). Từ đây cán bộ dùng nút *Bàn giao lại* như bình thường, hậu kiểm xác nhận lại là xong — giống hệt luồng mượn cũ
    + ⚠️ **Phải cấp quyền thì nút mới hiện.** Vào *Phân quyền theo nhóm* → **Quản lý chứng từ → Bàn giao chứng từ → "Chuyển trả chứng từ cho GDV"**, tích cho nhóm hậu kiểm / kiểm soát viên. Chưa tích thì không ai thấy nút, kể cả người đang có quyền xác nhận
    + ℹ️ **12/08/2026**: nút này ban đầu tên là **"Trả lại"**, đã đổi thành **"Chuyển trả GDV"** cho rõ là trả về cho giao dịch viên. Chỉ đổi chữ hiển thị — cách dùng, quyền và các dòng lịch sử đã ghi trước đó giữ nguyên
    + **Giao dịch viên không được cấp quyền này** — hệ thống chặn ở máy chủ kể cả khi lỡ tích nhầm. Nếu cho, cán bộ sẽ tự rút được chứng từ đã chốt của chính mình mà không qua bước duyệt của hậu kiểm
    + ⚠️ **Ô đã đóng tập chứng từ vẫn chuyển trả được** — bìa tập đã in sẽ không còn khớp thực tế. Chức năng *Mượn lại* sẵn có cũng đang như vậy, nên lần này giữ nguyên cho nhất quán. Cần chặn thì báo để sửa cả hai chỗ cùng lúc

- 11/08/2026 Đối chiếu CITAD - Extension lên **bản 2.12**, sửa lỗi không đọc được cột "NH gửi" có sẵn trong bảng kết quả:
    + Xác nhận lại thực tế: cột "NH gửi" (dùng tách Napas/PSS-MDP) **có sẵn ngay trong bảng kết quả mặc định** (Loại lệnh: Lệnh quyết toán, NH gửi để "Tất cả") — kéo bảng sang phải là thấy, **không cần** bấm "Xem chi tiết lệnh" như bản 2.10/2.11 từng giả định
    + Lỗi thật: hàm bắt cột so khớp **tuyệt đối** tên cột ("NH gửi" phải khớp y hệt) — bảng có nút sắp xếp cột hay chèn icon/khoảng trắng phụ vào tiêu đề khiến so khớp trượt dù cột hiển thị đúng. Nay so khớp kiểu "chứa chuỗi" sau khi chuẩn hoá khoảng trắng, khoan dung hơn
    + Sửa luôn đường lọc theo bộ lọc "NH gửi" cụ thể (bản 2.11): trước đọc giá trị đang chọn qua chữ hiển thị (`innerText`), không đọc được nếu ô lọc là `<input>` với giá trị nằm trong thuộc tính `value`. Nay tự dò cả `value` của input/select lẫn chữ hiển thị
    + ⚠️ **Phải tải lại `.zip` và cài lại Extension** — vào `/doi_chieu_citad` → **Tải Extension**, giải nén, *Load unpacked* lại

- 11/08/2026 Đối soát CITAD ↔ IPCAS - Sửa 2 lỗi làm sai lệch số liệu ngoại tệ (rà soát code, chưa có báo cáo thực tế):
    + **File CITAD nhiều sheet đọc sai loại tiền từ sheet thứ 2 trở đi**: chỉ sheet đầu tiên được nhận diện VNĐ/USD/EUR, các sheet sau luôn bị coi mặc định là VNĐ — sai cả cột đọc số tiền lẫn nhãn loại tiền, khiến lệnh ngoại tệ ở sheet 2+ bị đẩy nhầm sang so khớp IPCAS (đáng lẽ phải so Hub ngoại tệ) và báo lệch "Chỉ CITAD" giả
    + **File Hub ngoại tệ có cột ngày dạng Date thật bị lọc rớt hết, không báo lỗi**: cột ngày so với ngày chấm bằng so chuỗi, nhưng ô kiểu Date thật (phổ biến với file xuất chuẩn) đọc ra "yyyy-mm-dd" — không bao giờ khớp "dd/mm/yyyy" người dùng nhập → toàn bộ file Hub bị coi như rỗng, mọi lệnh ngoại tệ báo lệch "Chỉ CITAD" dù thực ra khớp đủ trong file đã tải lên
    + Cả 2 lỗi đều **âm thầm, không cảnh báo trên giao diện** — người dùng có thể đã ký duyệt báo cáo với số lệch ngoại tệ giả mà không biết. Đã sửa. **Dấu hiệu nhận ra lần đối soát bị dính lỗi: kết quả ra 0 lệnh ngoại tệ khớp và toàn bộ đều rơi vào "Chỉ CITAD"** — đó gần như chắc chắn là lỗi này chứ không phải số liệu lệch thật. Gặp vậy thì đối soát lại bằng bản mới

- 11/08/2026 Đối chiếu CITAD - Extension lên **bản 2.11**, thêm cách tách Napas/PSS-MDP khi đã lọc sẵn theo "NH gửi":
    + Nếu tự lọc ở form tìm kiếm "NH gửi" = 01401001 (Napas) hoặc 01406001 (PSS-MDP) rồi mới Tìm kiếm — Extension nay đọc thẳng bảng kết quả (khỏi cần bấm "Xem chi tiết lệnh"), tự cộng dồn cột "Số tiền" của toàn bộ dòng vì trang không tự cộng sẵn tổng tiền kiểu lọc này (chỉ có "Tổng số giao dịch" đếm số món)
    + **An toàn phân trang**: nếu số dòng quét được ít hơn "Tổng số giao dịch" trang báo (còn trang sau chưa xem), Extension **không lưu** số liệu thiếu — kể cả lượt tự động — tránh nạp nhầm số liệu hụt vào form Đối chiếu CITAD
    + Cách tách cũ (không lọc "NH gửi", tự bung "Xem chi tiết lệnh" rồi đọc cột NH gửi theo từng dòng — bản 2.10) vẫn giữ nguyên, dùng khi không lọc theo NH gửi
    + ⚠️ **Phải tải lại `.zip` và cài lại Extension** — vào `/doi_chieu_citad` → **Tải Extension**, giải nén, *Load unpacked* lại

- 11/08/2026 Đối chiếu CITAD - Extension lên **bản 2.10**, tự tách Napas/PSS-MDP không cần bấm tay:
    + Trang "Chuyển tiền đến" (payment.agribank.com.vn) sau khi Tìm kiếm chỉ hiện bảng tóm tắt — cột "NH gửi" (dùng để phân biệt Napas/PSS-MDP) chỉ có ở bảng **chi tiết lệnh**, phải tự tích chọn dòng + bấm "Xem chi tiết lệnh" mới hiện ra. Trước đây không ai biết bước này nên bấm "Lưu Napas + PSS-MDP" báo nhầm *"Chưa có kết quả, hãy Tìm kiếm trước"* dù đã tìm kiếm ra kết quả
    + Nay Extension **tự tích "chọn tất cả" + tự bấm "Xem chi tiết lệnh"** ngay khi phát hiện có kết quả tìm kiếm mới — tách Napas/PSS-MDP theo mã NH gửi (01401001/01406001) hoàn toàn tự động, không cần thao tác tay nào ngoài bấm Tìm kiếm
    + ⚠️ **Phải tải lại `.zip` và cài lại Extension** — vào `/doi_chieu_citad` → **Tải Extension**, giải nén, *Load unpacked* lại
    + *Giới hạn biết trước*: nếu kết quả tìm kiếm trải nhiều trang, "chọn tất cả" chỉ chọn các dòng đang hiển thị trên trang hiện tại — giống hạn chế khi thao tác tay từ trước, không phải lỗi mới


- 11/08/2026 Quản lý User - Sửa lỗi trang không hiện được tài khoản nào:
    + **Màn hình *Quản lý User* báo lỗi đỏ và hiện *"Không có kết quả"*** dù trong hệ thống có 79 tài khoản. Không sửa, không xoá, không khoá được ai qua giao diện. Ảnh hưởng **Quản trị viên cấp 1 và cấp 2, Giám đốc, Phó Giám đốc**. Trưởng phòng không bị nên lỗi dễ bị bỏ qua khi người này báo còn người kia bảo vẫn dùng được
    + Nguyên nhân: **một tài khoản có ô trạng thái bỏ trống** — không phải *Hoạt động*, cũng không phải *Tạm khoá*. Chỉ một dòng như vậy là đủ để hệ thống bỏ luôn **cả danh sách**, chứ không phải bỏ riêng dòng đó
    + **Không phải làm gì thủ công.** Lần khởi động đầu tiên sau khi cập nhật, hệ thống tự đặt các tài khoản trạng thái trống thành **Tạm khoá** — đúng với cách nó vẫn đối xử với những tài khoản này từ trước (không đăng nhập được, không hiện trong danh sách đang hoạt động, xuất Excel cũng đã ghi *Tạm khoá*). Không tài khoản nào đang dùng bị đổi trạng thái
    + Trạng thái trống nếu **phát sinh lại về sau** (thường qua chức năng *Nhập DB*) thì trang vẫn hiện bình thường thay vì sập, và không cần khởi động lại
    + ⚠️ **Còn 2 tài khoản kiểm thử trong dữ liệu, nên xoá:** `u1` (*LD Một*, Trưởng phòng, **Phòng Thanh toán**) và `duty_mig_check` (*LD Kiểm Tra*, Trưởng phòng, Phòng QLTK Nostro Vostro). Đã kiểm: **chưa ai từng đăng nhập** vào hai tài khoản này và chúng **không dính chứng từ, bìa, đơn nghỉ phép hay ca trực nào** — xoá không mất dữ liệu. Đáng lưu ý là `u1` đang hiện **đầu danh sách** ô *Người phê duyệt (KSV)* khi chuyên viên phòng Thanh toán tạo đơn nghỉ phép, rất dễ bị chọn nhầm

- 10/08/2026 Đối chiếu CITAD - Extension lên **bản 2.9**, dùng được địa chỉ `apc-portal:9090`:
    + Thêm địa chỉ `apc-portal:9090` (một địa chỉ khác cùng trỏ về trang web TTTT) vào danh sách Extension được phép gọi. Máy trạm nào vào hệ thống bằng địa chỉ này trước đây sẽ báo *"Không kết nối server"* dù cấu hình đúng
    + ⚠️ **Phải tải lại `.zip` và cài lại Extension** thì mới có hiệu lực — bản đang cài không tự nhận. Vào `/doi_chieu_citad` → **Tải Extension**, giải nén, *Load unpacked* lại
    + Máy nào đang vào bằng `apc-portal:8080` hoặc `10.1.3.89` và chạy bình thường thì **không bắt buộc** cập nhật ngay

- 10/08/2026 Phân lịch trực - Khai số người mỗi ca, ca quyết toán chính/phụ, sửa tay được thành phần ca (PR #26):
    + **Số người mỗi ca không còn cứng trong hệ thống** — vào tab *Cài đặt* khai riêng cho ca thường và ca quyết toán (số Lãnh đạo, số nhân viên trực chính, số trực phụ). **Một ca có thể khai nhiều hơn một Lãnh đạo** (tối đa 5), nhất là ngày quyết toán. Lịch tạo sau khi lưu sẽ theo số này
    + ⚠️ **Thiếu người so với số đã khai thì hệ thống KHÔNG lập ca ngày đó**, kèm dòng cảnh báo nêu rõ thiếu ở đâu. Trước đây vẫn sinh ca thiếu người mà không báo gì
    + **Ngày quyết toán** nay là **một ca duy nhất** có nhóm trực chính và nhóm trực phụ (trực phụ về sớm hơn), thay vì hai dòng riêng như trước. Lịch cũ được gộp tự động khi khởi động
    + **Sửa tay được thành phần ca trực** — bấm biểu tượng bút ở cột phải. Chọn sai vai (xếp nhân viên vào chỗ Lãnh đạo) hoặc sai số người thì bị chặn; xếp người đang đi dự án / đã khai vắng mặt thì vẫn cho lưu nhưng có cảnh báo. **Sửa xong ca quay về bản thảo, phải xác nhận lại**
    + Người giữ vai **xử lý song phương** hệ thống tự xác định từ cờ *"biết song phương"* của cán bộ — không phải chọn tay nữa. Ca thiếu hoặc dư người song phương đều vẫn lập, chỉ hiện cảnh báo
    + **Bỏ cờ "Backup SP"** — nay chỉ còn một cờ *"biết song phương"* duy nhất. Ai đang được đánh dấu Backup SP sẽ tự chuyển sang cờ mới, không mất khả năng trực song phương
    + Lịch ngày thường **bốc ngẫu nhiên trong nhóm ít ca nhất** nên không còn đoán trước được ai trực ngày nào, nhưng số ca vẫn chia đều. Thứ 6 giữ luân phiên cố định như cũ
    + **Chia ca đều hơn hẳn.** Phân thử 2 tháng (49 ca) trên danh sách nhân sự thật cho thấy: các Lãnh đạo chênh nhau nhiều nhất 1 ca (9–10 ca mỗi người), và **không ai phải trực 2 lần trong cùng một tuần**. Trước đây có Lãnh đạo trực 15 ca trong khi người khác chỉ 6 ca, và 8 lượt phải trực từ 2 lần trở lên trong một tuần — có người 3 lần. *(Số đo trên danh sách hiện tại; phòng ít người đi hoặc nhiều người nghỉ cùng lúc thì vẫn có thể phải trực lặp trong tuần)*
    + Thêm cơ chế **tránh hai người cứ đi trực cùng nhau mãi** — trước đây một Lãnh đạo và một nhân viên có thể bị ghép cặp cả 10/10 ca
    + Bảng lịch tuần **5 cột** (Ngày trực · Nhân viên 1 · Nhân viên 2 · Lãnh đạo · Tình trạng), luôn hiện đủ 5 hàng T2→T6, và **trạng thái chung của cả tuần hiện ngay cạnh tiêu đề tuần**. Ngày quyết toán hiện tên người trực chính IN HOA đậm, trực phụ chữ nghiêng nhỏ bên dưới
    + Thống kê ca trực tách **2 cột riêng: trực chính và trực phụ** — không quy đổi lẫn nhau
    + Sửa lỗi: bỏ tick *"biết song phương"* cho một Lãnh đạo thì sau khi khởi động lại hệ thống **cờ tự bật lại**. Nay lựa chọn được giữ nguyên
    + Sửa lỗi: đổi *số nhân viên ca thường* rồi lưu có thể làm **cấu hình ca quyết toán bị trả về mặc định** mà không báo gì
    + Sửa lỗi: hết phiên đăng nhập trong lúc mở tab *Cài đặt* thì màn hình im lặng hiện số mặc định thay vì đưa về trang đăng nhập
    + ⚠️ **Bịt lỗ hổng phân quyền — hãy soát lại quyền đã cấp cho từng nhóm.** Trước đây hệ thống chỉ *ẩn nút* trên màn hình, còn bên dưới thì **bất kỳ ai đăng nhập được cũng có thể xoá cả tuần lịch đã xác nhận** nếu biết cách gọi thẳng. Nay quyền được kiểm ở máy chủ. Hệ quả: ai trước giờ vẫn thao tác được nhờ lỗ hổng này mà **chưa được cấp quyền đúng** sẽ bắt đầu bị báo *"Không có quyền truy cập tính năng này"* — vào *Phân quyền theo nhóm* cấp bổ sung. Admin không bị ảnh hưởng
    + Nút **sửa ca trực** nay yêu cầu quyền *Tạo lịch trực tự động* (`duty.generate`) thay vì hiện cho mọi người có bất kỳ quyền nào — sửa tay cũng là sửa lịch

- 10/08/2026 Đối chiếu / Đối soát CITAD - Thêm kênh PSS-MDP, bắt lệnh gửi trùng, tự lọc file theo ngày (PR #25):
    + ⚠️ **Số "Khớp" và "Lệch" sẽ khác các lần chấm trước — số mới mới là số đúng.** Trước đây một lệnh CITAD bị gửi trùng N lần được tính khớp N lần, trong khi IPCAS chỉ có 1 bản ghi. Nay chỉ lần đầu tính khớp, các lần trùng tách riêng. Ai đang theo dõi bằng file Excel riêng sẽ thấy vênh với hệ thống
    + **Lệnh gửi trùng nay hiện rõ** trong nhóm *Chỉ CITAD*, ghi luôn *"bị dup mấy lần, cổng nào"* — trước đây trùng bao nhiêu lần cũng im lặng tính là khớp
    + **Tải chung file CITAD của nhiều ngày cũng được** — hệ thống đọc dòng *"Ngày giao dịch"* trong từng file và tự bỏ file khác ngày chấm, không phải tự lọc tay nữa. File nào bị bỏ đều được liệt kê rõ dưới nút Đối soát
    + **Bắt được trường hợp IPCAS báo lệnh lỗi/huỷ (ERPO, CALD) nhưng CITAD cho thấy lệnh đã đi kênh thành công** — xếp vào *Lệch trạng thái* kèm ghi chú, không lẫn vào *Chỉ Agribank*. Còn lệnh lỗi mà CITAD cũng không có thì là thất bại bình thường, không báo nữa
    + Thêm nút **Reset** cạnh ô *Ngày chấm* (có hỏi lại trước khi xoá) để bắt đầu phiên chấm mới, khỏi phải tải lại trang
    + **Đối chiếu CITAD**: thêm kênh **PSS - MDP**, cách tính giống Napas (cộng vào tổng CITAD). Bỏ 2 dòng *Waiting for AUTO* / *Waiting for manual* không còn dùng trên file Excel xuất ra
    + Đổi tên menu cho rõ: *Đối chiếu CITAD* → **Đối chiếu CITAD cuối ngày**; *Đối soát CITAD ↔ IPCAS* → **Đối soát chênh lệch CITAD cuối ngày**
    + Extension lên **bản 2.8** — vào màn hình Đối chiếu CITAD tải lại `.zip` rồi cài lại để nhận kênh PSS-MDP

- 10/08/2026 Toàn hệ thống - Sửa lỗi log tiếng Việt bị hỏng chữ:
    + **File nhật ký kỹ thuật `logs\backend.log` và `logs\frontend.log` trước đây ghi sai chữ tiếng Việt.** Câu *"Backup hoàn tất"* bị ghi thành `Backup ho?n tất`, *"Đã xóa thành viên"* thành `Đ? x?a th?nh vi?n`. Lỗi có từ 11/05/2026, không ai để ý vì hệ thống vẫn chạy bình thường và không báo lỗi gì
    + **Không ảnh hưởng tới số liệu hay nghiệp vụ.** Chỉ hỏng phần chữ trong file nhật ký kỹ thuật dành cho người quản trị đọc khi có sự cố. Dữ liệu, báo cáo, file Excel xuất ra đều không liên quan
    + **Màn hình *Nhật ký hệ thống* trên web vẫn luôn đúng** — màn hình đó đọc file khác (`logs\app.log`), file này không bị lỗi
    + ⚠️ **Phần nhật ký cũ đã hỏng thì không khôi phục được.** Từ nay các dòng mới ghi đúng. **Không phải làm gì thủ công** — lần khởi động đầu tiên sau khi cập nhật, hệ thống tự chuyển phần nhật ký cũ sang `logs\backend.truoc-utf8.log` và `logs\frontend.truoc-utf8.log`, rồi ghi tiếp vào file mới sạch. Không xoá dòng nào, chỉ tách ra file bên cạnh
    + Ngoài ra bịt luôn một lỗi tiềm ẩn: nếu chạy các chức năng đối chiếu bằng công cụ dòng lệnh thay vì qua web, chỉ một dòng chữ tiếng Việt là đủ làm dừng giữa chừng cả tiến trình đối chiếu

- 07/08/2026 Đối chiếu CITAD - Extension lên **bản 2.6**, bắt buộc cài lại:
    + ⚠️ **PHẢI TẢI LẠI VÀ CÀI LẠI EXTENSION.** Bản 2.5 đang cài trên máy trạm sẽ tiếp tục báo *"Không kết nối server"* dù mọi thứ phía máy chủ đã đúng. Vào `/doi_chieu_citad` → **Tải Extension**, giải nén, rồi *Load unpacked* lại như lần đầu
    + Nguyên nhân: từ bản trước, nút **Tạo mã kết nối mới** tự điền địa chỉ máy chủ vào Extension — nhưng đường tự động đó **không xin được quyền truy cập địa chỉ** cho trình duyệt, nên Extension bị chặn ngay ở tầng quyền. Chỉ khi tự vào Tuỳ chọn bấm Lưu mới xin được. Nay quyền được cấp sẵn ngay lúc cài, không phụ thuộc cách cấu hình nữa
    + Sau khi cài lại, kiểm nhanh: mở `edge://extensions` (hoặc `chrome://extensions`) → phần **Site access** phải thấy `apc-portal:8080`. Không thấy nghĩa là chưa cài đúng bản mới
    + Không cần làm gì thêm — mã kết nối cũ vẫn dùng được, không phải tạo lại

- 07/08/2026 Bảo mật - Đóng cổng backend khỏi mạng nội bộ, tắt trang liệt kê API *(chưa deploy — cần sửa `.env` trên máy chính rồi khởi động lại)*:
    + **Gỡ 2 cảnh báo đỏ hiện mỗi lần khởi động hệ thống chính.** Cả hai đều báo đúng: cổng backend (8000) đang mở ra toàn mạng nội bộ dù không ai cần vào, và trang liệt kê toàn bộ API đang xem được công khai
    + Nay cổng 8000 **chỉ nghe trong máy chủ**. Người dùng không bị ảnh hưởng gì — trình duyệt vẫn vào bằng đúng địa chỉ cũ (cổng 8080), Extension CITAD vẫn đi chung cổng đó như từ 06/08
    + Đã đối chiếu nhật ký máy chính trước khi đổi: **419/419 lượt đăng nhập** và **toàn bộ** thao tác Đối chiếu CITAD đều đi qua đường trong máy chủ, **50 máy trạm** đang dùng đều vào bằng cổng 8080 — không máy nào phụ thuộc cổng vừa đóng
    + Nếu có máy nào từng *tự gõ tay* địa chỉ có `:8000` vào trang Tuỳ chọn của Extension thì sẽ báo *"Không kết nối server"*. Cách sửa: vào `/doi_chieu_citad` bấm **Tạo mã kết nối mới** — hệ thống tự điền lại địa chỉ đúng
    + Trang `/docs` (danh sách 180 đường dẫn API kèm cấu trúc dữ liệu) **không còn mở công khai**. Trước đây bất kỳ ai trong mạng gõ đúng địa chỉ đều xem được cả sơ đồ hệ thống. Không lấy được dữ liệu vì vẫn phải đăng nhập, nhưng là tấm bản đồ dâng sẵn cho người dò
    + Vá thêm một lỗ liên quan: tắt `/docs` theo cách cũ **chưa tắt hết** — vẫn còn một đường dẫn phụ trả về nguyên danh sách 180 API đó ở dạng dữ liệu thô. Nay đóng cả hai
    + **Không phải sửa tay gì trên máy chính** — chạy `deploy.bat` là nó tự hỏi và sửa `.env` giúp (bước 1/7). Hệ thống test giữ nguyên `/docs` để còn gỡ lỗi

- 07/08/2026 Nhật ký hệ thống - Sửa lỗi trang trắng khi có thông báo nhiều dòng *(chưa deploy)*:
    + ⚠️ **Trang *Nhật ký hệ thống* trước đây vỡ đúng lúc hệ thống có lỗi cần xem.** Bản ghi một dòng thì hiện bình thường, nhưng bản ghi nhiều dòng (mô tả lỗi chi tiết) làm trang không hiện được — đã xảy ra **94 lần** trên máy chính mà không ai báo
    + Nay xem được mọi bản ghi, nội dung nhiều dòng giữ nguyên cách xuống dòng cho dễ đọc
    + Không đổi gì về dữ liệu hay quyền xem — chỉ là cách hiển thị


- 06/08/2026 Đối soát CITAD - Đọc được file `.xlsx`, và Extension gọi được máy chủ thật (PR #20):
    + ✅ **GỠ CẢNH BÁO NGÀY 04/08: file CITAD định dạng `.xlsx` nay đọc bình thường.** Trước đây mọi file `.xlsx` bị đọc ra rỗng mà không báo lỗi — màn hình vẫn hiện "đối soát xong" nhưng số khớp bằng 0 và toàn bộ lệnh bị xếp vào "Chỉ IPCAS". Từ nay dùng `.xls` hay `.xlsx` đều được
    + ⚠️ **Ai đã đối soát bằng file `.xlsx` trước ngày 06/08 thì làm lại.** Kết quả cũ và bản đã lưu ở tab *Lịch sử* của những lần đó đều sai — không phải số liệu lệch thật
    + **Extension nay gọi được máy chủ thật.** Trước đây máy chủ chỉ mở cổng giao diện ra máy trạm nên Extension luôn báo *"Không kết nối server"* dù cấu hình đúng. Nay đi chung một cổng với web, không phải mở thêm gì trên tường lửa
    + Nút **Tạo mã kết nối mới** trước đây ghi vào Extension một địa chỉ chỉ đúng trên máy chủ, nên vừa không dùng được vừa **xoá mất cấu hình đúng ai đã điền tay**. Nay lấy đúng địa chỉ đang mở trên trình duyệt
    + Vá một lỗ hổng: có thể giả mạo địa chỉ IP ghi vào Nhật ký hệ thống cho các thao tác Đối chiếu CITAD. **Nhật ký cũ vẫn đúng** — lỗ hổng chỉ mở đường cho ai cố tình, không làm sai dữ liệu đang có

- 06/08/2026 Nghỉ phép - Sửa loạt lỗi hạn mức, số liệu Dashboard và thao tác duyệt (PR #18):
    + **Đổi tab trong màn Nghỉ phép không còn trắng màn hình** — chuyển tab tức thì thay vì tải lại cả trang
    + ⚠️ **Ô "Đã dùng" ở tab Hạn mức phép trước đây cộng dồn mỗi lần bấm Lưu** — mở dialog rồi bấm Lưu mà không sửa gì cũng làm số ngày đã dùng tăng gấp đôi. Nay bấm Lưu bao nhiêu lần giá trị vẫn giữ nguyên. **Cần soát lại hạn mức của các nhân viên đã từng sửa tay trước ngày 06/08**
    + ⚠️ **Nhập file hạn mức Excel dính đúng lỗi trên** — nhân viên đã có đơn nghỉ thật trong năm bị cộng dồn ngay từ lần nhập đầu tiên. Nay hệ thống trừ đúng phần đơn thật rồi mới ghi phần chênh lệch
    + Nhập số "Đã nghỉ" **thấp hơn số ngày đã nghỉ thật** thì hệ thống giữ theo số thật và **báo rõ tên những người bị giữ**, không âm thầm để lệch số
    + Số liệu nhập hạn mức (từ file Excel hoặc sửa tay) **không còn hiện lẫn như một đơn nghỉ thật** ở Lịch nghỉ phép, "Đơn của tôi", danh sách toàn trung tâm, kiểm tra trùng ngày và số liệu Dashboard
    + **5 ô số liệu ở Dashboard đổi theo khoảng ngày** chọn ở Bộ lọc tìm kiếm, đúng phạm vi vai trò của từng người
    + **Bắt buộc chọn Ban lãnh đạo phê duyệt** khi tạo đơn và khi nộp lại — trước đây bỏ trống được, đơn sẽ kẹt vĩnh viễn ở bước Tổng hợp
    + Sửa nút **Phê duyệt / Từ chối** ở bảng Dashboard không phản hồi khi tick chọn; đổi tab nay tự bỏ tick để không xử lý nhầm đơn đã chọn ở tab khác
    + Nhãn trạng thái thống nhất một kiểu ở mọi màn hình: **"Chờ Ban lãnh đạo duyệt"** và **"Hoàn thành"**
    + Tải dữ liệu trang lỗi thì **báo rõ**, không âm thầm hiện số 0

- 06/08/2026 Báo cáo bàn giao chứng từ - Sửa cách trừ ngày nghỉ phép của người nhận:
    + Báo cáo chấm đúng hạn/quá hạn có **trừ những ngày người nhận bàn giao đi nghỉ phép** (người nhận vắng thì không thể trách người nộp). Nhưng số liệu hạn mức phép nhập từ Excel bị tính nhầm thành ngày nghỉ thật, khiến **chứng từ nộp quá hạn trong tháng 1 bị chấm thành đúng hạn**
    + Nay báo cáo chỉ trừ đơn nghỉ phép thật. **Số liệu các kỳ đã xem trước đây không đổi** (hệ thống chưa có dữ liệu hạn mức nhập vào) — đây là vá phòng ngừa trước khi bắt đầu dùng thật
    + Nhật ký hệ thống ghi rõ thao tác **"Sửa số ngày phép đã dùng"** thay vì mô tả chung chung

- 05/08/2026 Phòng Thanh toán - Thêm màn hình **Đối chiếu ACH** (GL02 ↔ MIS):
    + Menu *Phòng Thanh toán → Đối chiếu* có thêm **Đối chiếu ACH**. Công cụ trước đây chạy riêng trên một máy nay vào thẳng phần mềm, dùng chung tài khoản và phân quyền như mọi màn hình khác
    + Cách dùng: chọn (hoặc kéo thả) đủ bộ file của một ngày — file GL02, file GW, 2 file MIS chiều ĐI, 2 file MIS chiều ĐẾN và file PDF sao kê. Màn hình có **bảng kiểm tra đã đủ file chưa**, thiếu loại nào báo ngay chứ không để chạy xong mới lỗi
    + **Ngày đối chiếu để trống là được** — hệ thống tự lấy từ tên file PDF. Nếu tên file không đúng mẫu thì **báo lỗi rõ ràng**, không tự dùng một ngày khác
    + Kết quả là 1 file Excel gồm bảng tổng kết, bảng phân tích có **cảnh báo tự động** (lệnh TPAY chưa xử lý, lệnh timeout không đi kênh, cặp chi nhánh + số tiền nghi sai số trace) và các sheet chi tiết khớp / chưa khớp từng chiều. Sheet nào **trên 15.000 dòng** được tách ra file CSV riêng, tải lẻ từng file hoặc bấm **Tải tất cả (ZIP)**
    + ⚠️ **Mở file CSV bằng Excel → Data → Từ Văn bản/CSV, đừng double-click.** Double-click sẽ mất số 0 đứng đầu ở cột TRACE, MSGSEQ và sai định dạng số tiền
    + Trong lúc chạy có **thanh tiến độ và nhật ký xử lý**; bấm **Dừng** thì hệ thống dừng ở bước gần nhất chứ không cắt ngang giữa chừng (cắt ngang dễ làm treo máy chủ). Dừng xong báo *"Đã dừng đối chiếu theo yêu cầu"* — không phải báo lỗi đỏ
    + Bấm ✕ để bỏ file chọn nhầm: nếu máy chủ chưa xoá được (Windows đang khoá file vừa ghi) thì **báo rõ và giữ nguyên file trong danh sách**, không để màn hình nói đã xoá trong khi file vẫn còn
    + Một lúc chỉ chạy **một lần đối chiếu**; người bấm sau sẽ thấy trạng thái đang xếp hàng. Kết quả giữ trên máy chủ **4 giờ** rồi tự xoá — cần thì tải về máy, không lưu lịch sử tra cứu lại
    + Cần bật quyền trong *Phân quyền theo nhóm* (`menu.doi_chieu_ach`, `doi_chieu_ach.process`), nếu không chỉ admin nhìn thấy menu
    + ⚠️ **Máy chủ phải chạy lại `pip install -r requirements.txt`** (thêm 2 thư viện `xlsxwriter`, `python-calamine`), nếu không backend không khởi động được

- 05/08/2026 Đối chiếu CITAD - Extension lấy đúng số tiền lẻ và tự điền được mã kết nối:
    + ⚠️ **Số tiền USD/EUR lấy tự động từ Extension trước đây sai gấp 100 lần.** Phần xu bị nhập vào thành phần nguyên — `1.234,56` USD thành `123.456`. Nay lấy đúng cả phần lẻ
    + **Số món không dính lỗi này, và VNĐ cũng không** (không có đơn vị lẻ). Chỉ ảnh hưởng cột số tiền của USD và EUR
    + ⚠️ **Cần soát lại các bản đã lưu có USD/EUR nạp bằng Extension trước ngày 05/08.** Số liệu gõ tay không dính
    + Nút **Tạo mã kết nối mới** nay đẩy mã thẳng vào Extension, không phải sao chép dán tay. Trước đây luôn rơi về cách dán tay vì địa chỉ máy chủ thật chưa khai trong Extension
    + Extension lên **bản 2.5** — vào màn hình Đối chiếu CITAD tải lại file `.zip` rồi cập nhật để nhận thay đổi. Máy chưa cập nhật vẫn dùng được nhưng còn nguyên lỗi số tiền lẻ ở trên

- 05/08/2026 Báo cáo bàn giao chứng từ - Thêm nút xuất file Word:
    + Nút **Xuất file Word** nằm ngay cạnh nút *Xem báo cáo*. File ra dạng **A4 ngang**, tiêu đề *"Báo cáo bàn giao chứng từ tháng xx năm xxxx"*
    + Nội dung: bảng tổng hợp theo phòng (tổng chứng từ, nộp đúng hạn, nộp quá hạn, tỷ lệ đúng hạn, có dòng **TỔNG CỘNG**) và phần chi tiết chứng từ nộp quá hạn tách theo từng phòng
    + Phần chi tiết chỉ ghi **họ và tên** cán bộ — không in User IPCAS (màn hình vẫn giữ cột này để tra cứu). Chứng từ của cùng một cán bộ được **xếp liền nhau và gộp ô họ tên thành một**, trong cụm sắp theo ngày giao dịch
    + Xuất đúng **kỳ đang xem trên màn hình**: đổi ô Tháng/Năm mà chưa bấm *Xem báo cáo* thì file vẫn ra tháng đang hiển thị, không bị lệch âm thầm
    + Số liệu trong file dùng chung một hàm tính với màn hình và Trang chủ — không có chuyện file Word lệch với bảng đang xem

- 04/08/2026 Phòng KSNB & HTVH - Thêm màn hình Danh sách CN TTQT:
    + Menu *Phòng KSNB & HTVH → **Danh sách CN TTQT*** — tra cứu danh sách chi nhánh thực hiện thanh toán quốc tế trực tiếp ngay trên hệ thống, không phải mở file Excel dùng chung nữa. Đã nạp sẵn **218 chi nhánh** theo file *Danh sách CN thực hiện TTQT* bản 06.01.26 (204 đang hoạt động, 14 đã đóng BIC)
    + Tìm theo **mã CN, tên CN hoặc mã SWIFT BIC** — **gõ không dấu cũng ra** (`dien bien` ra *Điện Biên*), không phân biệt chữ hoa chữ thường; lọc thêm theo *loại CN* và *trạng thái*. Mặc định chỉ hiện CN **đang hoạt động** — muốn xem CN đã đóng BIC thì đổi ô *Trạng thái*, khi xem chung hai nhóm thì dòng đã đóng BIC được **tô xám**
    + **Thêm / sửa / xoá từng chi nhánh** ngay trên màn hình. Mọi thao tác đều được ghi vào Nhật ký hệ thống
    + **Nhập từ Excel**: chọn thẳng file gốc phòng KSNB phát hành, **không phải sửa gì trước khi nhập** — hệ thống hiểu dòng đánh dấu *Đóng BICCODE* và tự xếp các CN phía dưới vào nhóm đã đóng BIC
    + **Xuất Excel** đúng phần đang lọc, định dạng giống file gốc nên **nhập lại được** — dùng để phát hành bản cập nhật cho các chi nhánh
    + ⚠️ **Nhập Excel mặc định KHÔNG xoá chi nhánh nào** — chỉ thêm mới và cập nhật CN có trong file. Nếu file mới đã bỏ bớt chi nhánh và muốn hệ thống bỏ theo thì phải **tự tích ô *"Xoá CN không có trong file"*** trước khi chọn file. Không tích thì các CN cũ vẫn nằm nguyên trong danh sách
    + ⚠️ Nhập nhầm file **không hoàn tác được** — chưa có lịch sử nhập như màn *Hạn mức phép*. Kiểm kỹ file trước khi chọn, nhất là khi đã tích ô xoá
    + ⚠️ Menu này **phải được cấp quyền** ở màn *Phân quyền chức năng* (mục *Danh sách CN TTQT* trong nhóm Phòng KSNB & HTVH). Quyền xem, thêm, sửa, xoá, nhập, xuất cấp riêng từng loại — không cấp thì mục menu không hiện
    + ⚠️ **Tên chi nhánh trong file gốc có 11 dòng gõ dấu kiểu cũ** (chữ và dấu tách rời). Hệ thống tự chuẩn hoá khi nhập nên tìm kiếm vẫn ra. Nếu sau này gõ tay tên CN từ nguồn khác dán vào mà tìm không ra, báo lại để kiểm tra

- 04/08/2026 Tài khoản - Đặt lại mật khẩu cho người dùng khác:
    + Ô *Chọn người dùng* nay **gõ được để tìm**, không phải cuộn hết danh sách nhân sự. Cách dùng giống hệt ô *Thêm nhân viên* ở màn *Quản lý nhóm quyền*

- 04/08/2026 Bàn giao chứng từ - Phân lại quyền xem và quyền nhập liệu:
    + **Trưởng phòng, Phó phòng** nay vào được màn hình *Bàn giao chứng từ* — xem lưới **phòng của mình**. Cần quản trị cấp mục *Bàn giao chứng từ* trong màn *Phân quyền chức năng* cho nhóm của họ thì mới hiện menu
    + **Quyền nhập/sửa số tờ của Trưởng phòng, Phó phòng vẫn theo nhóm quyền như mọi người khác** — không cấp *Lưu số tờ chứng từ* thì chỉ xem, không gõ được
    + ⚠️ **Admin, Giám đốc, Phó giám đốc từ nay CHỈ XEM, không nhập/sửa/xác nhận được chứng từ.** Đổi lại các vị này xem được **tất cả các phòng** và xuất Excel toàn bộ. Trước đây tài khoản admin sửa được dữ liệu bàn giao — nay không còn. **Cần chữa số liệu nhập sai thì phải dùng tài khoản hậu kiểm hoặc tài khoản trong đúng phòng đó**, không nhờ admin được nữa
    + Ô nhập trên lưới nay **khoá hẳn** với người không có quyền lưu. Trước đây vẫn gõ được vào ô nhưng bấm Lưu thì không có gì xảy ra — nhìn như hệ thống nuốt mất số vừa nhập

- 04/08/2026 Phòng Thanh toán - Thêm 2 màn hình Đối chiếu CITAD và Đối soát CITAD ↔ IPCAS:
    + Menu *Phòng Thanh toán → Đối chiếu* có thêm **Đối chiếu CITAD** (đối chiếu số liệu với PaymentHub) và **Đối soát CITAD ↔ IPCAS** (khớp từng lệnh chuyển tiền). Cả hai chuyển từ công cụ chạy riêng trên máy vào thẳng phần mềm, dùng chung tài khoản và phân quyền như mọi màn hình khác
    + **Đối chiếu CITAD**: nhập số liệu 5 cổng × 3 loại tiền, chênh lệch tự tính ngay khi gõ. Mỗi ngày là **một bản ghi chung của cả phòng**, kèm tab *Lịch sử* xem lại từng lần lưu. Xuất Excel đúng mẫu báo cáo NHNN đã duyệt
    + **Đối soát CITAD ↔ IPCAS**: tải file CITAD, IPCAS và Hub ngoại tệ lên, hệ thống khớp lệnh rồi liệt kê phần lệch theo 4 nhóm, xuất Excel 4 sheet. Có lưu lịch sử để xem lại đúng số liệu của lần đối soát cũ. Hệ thống **cảnh báo khi chọn trùng file** (so nội dung từng byte, không dựa vào tên file)
    + Kèm **Extension trình duyệt** tự lấy số liệu từ trang CITAD và PaymentHub sang, khỏi chép tay. Tải ngay trên màn hình Đối chiếu CITAD, ghép nối bằng *mã kết nối* riêng của từng người
    + ~~⚠️ **Đối soát CITAD: dùng file CITAD định dạng `.xls`, KHÔNG dùng `.xlsx`.** File `.xlsx` hiện bị đọc ra rỗng mà **không báo lỗi**~~ — **ĐÃ SỬA ngày 06/08, xem entry đầu trang.** Từ nay `.xls` và `.xlsx` đều dùng được
    + ⚠️ **Đối chiếu CITAD lưu chung một bản cho cả phòng** — hai người cùng chấm một ngày thì ai bấm Lưu sau cùng là bản hiện hành. Bản của người trước không mất, xem lại ở tab *Lịch sử*
    + ⚠️ Extension **phải cài tay trên từng máy** và chỉ chạy trên **Chrome, Edge, Cốc Cốc** (không có Firefox, Safari). Hướng dẫn cài nằm trong file tải về
    + ⚠️ Nút *Tạo mã kết nối* có thể báo "đã tự động kết nối" nhưng Extension vẫn không gửi được — đang còn lỗi địa chỉ máy chủ. Nếu gặp, mở *Tuỳ chọn* của Extension điền tay địa chỉ và mã kết nối

- 04/08/2026 Bàn giao chứng từ - Cột "Ngày bàn giao" hiện đúng ngày nộp thật:
    + Trước đây cột **Ngày bàn giao** ở màn hình *Công việc chờ xử lý* luôn trùng khít cột *Ngày chứng từ* — chứng từ ngày 03/08 nộp ngày 04/08 vẫn báo bàn giao 03/08. Nay lấy đúng **thời điểm chuyên viên thực sự nộp** ghi trong lịch sử thao tác
    + Ô chi tiết bên phải lưới nhập nay ghi rõ **hai dòng có nhãn**: *Ngày chứng từ* và *Ngày bàn giao*. Trước đây chỉ có một dòng "Ngày ..." lấy theo thao tác gần nhất — sau khi hậu kiểm xác nhận, ngày đó bị đổi theo ngày xác nhận, nhìn tưởng là ngày nộp
    + ⚠️ Chứng từ nhập từ **trước khi hệ thống ghi lịch sử** không có ngày nộp ở bất kỳ đâu trong dữ liệu → hiện dấu `—` thay vì đoán bừa
    + Cùng cách tính với báo cáo *Tỷ lệ nộp đúng hạn*, nên hai màn hình không còn nói hai con số khác nhau

- 03/08/2026 Đối chiếu điện SWIFT - Nạp nhiều file một lúc và xuất Excel theo đúng biểu mẫu:
    + Mỗi ô chọn file nay **nhận nhiều file cùng lúc**. SAA phải xuất làm nhiều đợt trong ngày thì cứ thả hết vào đúng ô đó, hệ thống tự gộp lại trước khi đối chiếu — không phải đối chiếu từng đợt rồi tự cộng tay
    + Mỗi file vẫn báo riêng ✅/❌ và **số dòng đọc được ngay khi vừa chọn**, kèm dòng tổng cộng. Chọn nhầm thì bấm ✕ ở cạnh tên file để bỏ ra, không phải làm lại từ đầu
    + Giới hạn **10 file hoặc 100 MB mỗi ô**. Vượt quá thì báo ngay và không nạp thêm — tránh làm hệ thống hết bộ nhớ ảnh hưởng sang các màn hình khác
    + Thêm **2 nút xuất Excel theo biểu mẫu**: *Tổng hợp theo biểu mẫu* (Mẫu 04) và *Chi tiết lệch theo biểu mẫu* (Mẫu 05). File tải về đã có sẵn quốc hiệu, tiêu đề, dòng ký — in ra trình ký được ngay, không phải chép số sang mẫu Word thủ công
    + Hai biểu mẫu này tự phân loại điện về **SWIFT / IPCAS / P-HUB** dựa trên cột *Channel Process* có sẵn trong file Quản lý điện
    + ⚠️ **Cột "Chênh lệch" đổi cách tính — số sẽ khác trước.** Trước đây lấy hiệu số lượng hai bên; nay đếm đúng số điện **thực sự không khớp**. Ví dụ một loại điện có 5 bản ghi ở mỗi bên nhưng là 5 giao dịch hoàn toàn khác nhau: trước báo *Chênh lệch = 0* (trông như khớp), nay báo đúng *10*. Số mới mới là số đúng, nhưng ai đang theo dõi bằng file riêng sẽ thấy lệch với hệ thống
    + ⚠️ **Các lần đối chiếu đã lưu ở tab Lịch sử TRƯỚC đợt này vẫn giữ con số theo cách tính cũ.** Không so trực tiếp cột Chênh lệch của bản ghi cũ với bản ghi mới
    + ⚠️ Trên hai biểu mẫu mới, ô **ngày đối chiếu** đang bị điền ngày in báo cáo. Đối chiếu số liệu của ngày hôm trước thì **sửa lại ngày này bằng tay trước khi trình ký**

- 31/07/2026 Đăng nhập - Thêm lối tắt tới các hệ thống nghiệp vụ ngay ở màn hình đăng nhập:
    + Hai bên ô đăng nhập nay có **3 cụm đường dẫn**: *Thanh toán trong nước* (10 lối tắt), *Thanh toán quốc tế* (2), *Nội bộ* (4). Click là mở tab mới, không phải nhớ hay gõ lại địa chỉ
    + Mỗi lối tắt hiện **tên tiếng Việt** thay vì địa chỉ khó nhớ — ví dụ *"Hệ thống TT ĐTLNH - Cổng 12"* thay cho `http://10.0.85.100/CITAD9212`. Rê chuột lên vẫn xem được địa chỉ đầy đủ trước khi bấm
    + Các lối tắt **vẫn dùng được khi hệ thống đang lỗi** — chúng không phụ thuộc vào máy chủ của phần mềm này
    + Sửa lỗi ô *Tên đăng nhập* và *Mật khẩu* bị **tô nền xanh** khi trình duyệt tự điền mật khẩu đã lưu

- 31/07/2026 Toàn hệ thống - Đầu mỗi trang hiện rõ đang đứng ở đâu trong menu:
    + Trước đây đầu trang chỉ có tên màn hình (*"Báo cáo hậu kiểm"*), không biết mục đó nằm ở phòng nào, nhóm nào. Nay hiện cả đường đi: *Phòng KSNB & HTVH / Báo cáo / **Báo cáo hậu kiểm***
    + Áp dụng cho **tất cả các màn hình** có trong menu. Trang chủ và Quản lý User nằm ở cấp ngoài cùng nên không có phần dẫn đường

- 30/07/2026 Trang chủ - Xem hết trang không phải cuộn:
    + Trang chủ trước đây **dài hơn màn hình**, phải cuộn xuống mới thấy hết biểu đồ nộp chứng từ. Nay toàn bộ nằm vừa trong một màn hình, không còn thanh cuộn
    + Ô "Người dùng" và "Phòng nghiệp vụ" chuyển lên nằm cùng hàng với tiêu đề — vẫn đủ thông tin, gọn hơn
    + Khối **Nghỉ phép hôm nay** phóng to: số nghỉ to và rõ hơn hẳn
    + Biểu đồ nộp chứng từ thu gọn lại, cột không còn bè ra choán màn hình
    + Ô phòng Nostro rút gọn thành **"Phòng QLTK Nostro, Vostro"** để nhãn nằm một dòng như các ô khác. Tên đầy đủ trên phiếu nghỉ phép, bìa tập và báo cáo **không đổi**

- 30/07/2026 Khởi động - `start.bat` không cài lại thư viện mỗi lần đổi máy:
    + Mang thư mục dự án (chạy từ USB) sang máy khác thì mỗi lần bấm `start.bat` đều báo *".venv bị hỏng"* rồi **cài lại toàn bộ thư viện, mất vài phút**. Nay script vá môi trường tại chỗ, **khoảng 2 giây là chạy được**
    + Khi thật sự có lỗi, script **in rõ nguyên văn lỗi** ra màn hình thay vì im lặng cài lại
    + ⚠️ Máy mới cần **Python 3.10.x**. Máy chỉ có 3.11/3.12 thì vẫn phải cài lại thư viện và **cần internet**
    + Lần chạy đầu sau đợt cập nhật này sẽ cài lại thư viện **một lần** (khoảng 10 giây), sau đó bỏ qua

- 29/07/2026 Bàn giao chứng từ - Mỗi phòng chỉ còn thấy chứng từ của phòng mình:
    + Trước đây bất kỳ ai đăng nhập được đều **tải được file Excel chứa toàn bộ chứng từ của mọi phòng** — kể cả tài khoản không được cấp quyền gì trong menu Bàn giao. Xem lịch sử một chứng từ bất kỳ cũng vậy
    + Người có quyền nhập còn **xem được lưới của phòng khác và nhập chứng từ cho cán bộ phòng khác**
    + Nay ô chọn Phòng chỉ hiện phòng của chính mình; mọi thao tác trên chứng từ phòng khác đều bị chặn, kể cả khi gọi thẳng vào hệ thống mà không qua màn hình
    + **Hậu kiểm viên, Trưởng/Phó phòng KSNB và Giám đốc/Phó Giám đốc không đổi** — vẫn xem và làm việc trên mọi phòng như trước
    + ⚠️ **Cán bộ đã chuyển phòng không tự mở lại được chứng từ tháng còn ở phòng cũ.** Chứng từ vẫn nằm nguyên ở phòng cũ và không mất đi, nhưng từ nay việc nhập bù cho những tháng đó phải nhờ hậu kiểm viên làm

- 29/07/2026 Nghỉ phép - Tính đúng hạn mức khi nghỉ vắt qua giao thừa dương lịch:
    + Đơn nghỉ liền mạch bắc qua ngày 31/12 (ví dụ nghỉ từ 29/12 đến 02/01) trước đây bị **trừ trọn vào năm cũ**, kể cả những ngày thực tế đã sang năm mới. Người nghỉ bị mất oan số ngày phép đúng bằng phần vắt sang năm sau
    + Nay mỗi ngày được tính vào đúng năm của nó. Ví dụ nghỉ 29/12 → 02/01 thì 3 ngày làm việc cuối tháng 12 trừ vào năm cũ, 2 ngày đầu tháng 1 trừ vào năm mới
    + ⚠️ **Số ngày phép chuyển kỳ của một số người sẽ tăng lên sau đợt cập nhật này.** Đây là con số đúng, không phải lỗi — nhưng ai đang theo dõi số phép bằng sổ tay hoặc file Excel riêng sẽ thấy lệch với hệ thống. Cần đối chiếu lại với những người từng nghỉ bắc qua Tết dương lịch

- 29/07/2026 Nghỉ phép - Không còn trừ phép hai lần khi bấm duyệt nhanh:
    + Bấm nút duyệt hai lần liên tiếp, hoặc hai người cùng duyệt một đơn ở hai máy, trước đây có thể **trừ hạn mức phép hai lần** cho cùng một đơn
    + Nay chỉ lần bấm đầu tiên có hiệu lực, lần sau báo *"Đơn đã được xử lý bởi một yêu cầu khác, vui lòng tải lại trang"*

- 29/07/2026 Nghỉ phép - Ô "Phép còn lại" hiện đúng số:
    + Ô này trước đây tính theo công thức thâm niên, **bỏ qua hạn mức phòng Tổng hợp nhập tay và bỏ qua ngày phép chuyển từ năm trước sang**. Người xem thấy một số ở đầu trang, bấm vào tab Hạn mức phép lại thấy số khác
    + Nay hai chỗ dùng chung một cách tính, không còn lệch

- 29/07/2026 Nghỉ phép - Phiếu in ra và quyền xem đơn:
    + Phiếu nghỉ phép trước đây **luôn in cứng chức danh "TUQ. GIÁM ĐỐC / PHÓ GIÁM ĐỐC"** ở ô ký, kể cả khi người duyệt là Giám đốc. Nay in đúng chức danh của người thực sự ký
    + Nghỉ nhiều ngày liền nhau mà chỉ cách nhau thứ 7, Chủ nhật (ví dụ nghỉ thứ 6 rồi nghỉ tiếp thứ 2) nay ghi gọn *"Từ ngày… đến hết ngày…"* thay vì liệt kê rời từng ngày
    + **Người khai báo hộ nay xem lại được chính đơn mình đã khai.** Trước đây khai xong thì không mở ra xem, không xem lịch sử, cũng không tải phiếu về được

- 29/07/2026 Nghỉ phép - Số ngày trong báo cáo và bảng hạn mức:
    + Cột "Số ngày" ở Trang tổng hợp của lãnh đạo và ở file Excel báo cáo năm trước đây **đếm cả thứ 7, Chủ nhật và ngày lễ**, nên luôn cao hơn số ngày thực bị trừ vào hạn mức. Nay tính giống hệt cách trừ hạn mức
    + Công thức gợi ý khi sửa hạn mức thủ công sửa lại thành **12 ngày + 1 ngày mỗi 4 năm công tác** (trước ghi nhầm mỗi 5 năm, lệch với cách hệ thống thực sự tính)
    + Bảng Hạn mức phép thêm cột **Mã cán bộ**
    + Nhập hạn mức từ Excel: ô "Đã nghỉ" ghi số lẻ nửa ngày nay **hiện cảnh báo trước khi áp dụng**, vì hệ thống không có khái niệm nửa ngày phép và sẽ làm tròn

- 29/07/2026 Trang chủ - Bảng nghỉ hôm nay giữ nguyên cách đếm:
    + Bảng "Nghỉ phép hôm nay" **chỉ đếm đơn đã được duyệt xong**. Người vừa nộp đơn mà cấp trên chưa duyệt thì vẫn tính là đang đi làm
    + Lịch tháng trong menu Nghỉ phép thì ngược lại — có hiện cả đơn đang chờ, nhưng ở đó mỗi dòng đều kèm nhãn trạng thái nên không gây nhầm. Hai chỗ khác nhau là **có chủ đích**

- 28/07/2026 Sidebar - Việc chờ xử lý hiện ở mọi trang:
    + Số việc đang chờ trước đây chỉ hiện ở **3 trong 21 trang**. Đứng ở trang Lưu trữ thì không hề biết mình có 12 chứng từ chờ xác nhận. Nay khối **Công việc chờ xử lý** nằm đầu sidebar, theo người dùng đi khắp hệ thống, tự ẩn khi không còn việc
    + Bấm vào mở **màn hình theo dõi riêng**: chứng từ của ai, phòng nào, ai nộp, ngày nào — và bấm tiếp là nhảy thẳng tới đúng ô cần xử lý, không phải tự tìm lại
    + Khối "Công việc đang chờ" trên Trang chủ đã gỡ. Cùng một thông tin không nên có hai chỗ hiển thị, nhất là khi một chỗ bắt phải quay về Trang chủ mới thấy
    + Số trên sidebar cập nhật khi chuyển trang, **không tự làm mới tại chỗ**. Duyệt xong một đơn thì số đúng ngay ở trang kế tiếp

- 28/07/2026 Phân quyền - Chuyên viên vào được Trang chủ:
    + Chuyên viên bấm "Trang chủ" trước đây bị bật ngược về Bàn giao chứng từ — mục menu nhìn thấy nhưng không bao giờ vào được. Nay **mọi vai trò đều đăng nhập vào Trang chủ** và ra vào bình thường
    + Ô "Người dùng" trên Trang chủ đổi nhãn thành **"Nhân sự phòng"** với chuyên viên / trưởng phòng / phó phòng, vì con số họ nhận được vốn chỉ tính phòng mình — nhãn cũ dễ bị đọc nhầm thành toàn trung tâm
    + ⚠️ **Phân quyền nhóm nay có tác dụng thật với chuyên viên.** Trước đây admin cấp quyền Báo cáo / Lưu trữ / Nhân sự / Đóng tập cho một chuyên viên thì màn hình phân quyền báo đã cấp, menu cũng hiện ra, nhưng bấm vào bị đá ra mà không báo gì — do còn một lớp chặn cứng theo chức danh nằm đè lên. Đã gỡ lớp đó. **Chuyên viên không tự nhiên có thêm quyền gì**; chỉ khác là quyền đã cấp thì dùng được

- 28/07/2026
    + Khoá ký phiên đăng nhập trước đây nằm cứng trong mã nguồn
    + `start.bat` **tự sinh khoá mới** nếu file `.env` chưa có
    + Thư viện giao diện được nâng cấp

- 28/07/2026 Bảo mật - Vá thư viện xử lý file tải lên:
    + Thư viện đọc file tải lên đang dùng có **16 lỗ hổng đã biết**, trong đó 4 lỗi nghiêm trọng (1 lỗi cho phép ghi file tuỳ ý, 3 lỗi làm treo máy chủ). Đã nâng lên bản vá sạch hoàn toàn
    + Ảnh hưởng mọi chỗ tải file: nạp ZIP đối chiếu SWIFT, chấm 459901, nhập hạn mức phép, nhập DB nhân sự
    + Khoá ký phiên đăng nhập chuyển từ trong mã nguồn ra file cấu hình — trước đây ai đọc được mã nguồn đều có thể giả mạo phiên của người khác

- 28/07/2026 Toàn hệ thống - Tải nhầm file không còn làm treo trang:
    + Tải lên file `.zip` **hỏng hoặc bị đổi tên đuôi** trước đây báo "Internal Server Error" khó hiểu. Nay báo rõ: *"File tải lên không phải file .zip hợp lệ — có thể tải bị lỗi, bị cắt dở, hoặc chỉ được đổi đuôi tên thành .zip"*
    + File `.zip` **có đặt mật khẩu** nay báo *"hãy giải nén ra rồi tải lại file bên trong"* thay vì lỗi hệ thống
    + Chấm 459901: ZIP không chứa file `.csv`, hoặc file `.csv` thiếu cột, nay **báo đúng thiếu cột nào** thay vì dòng chữ "list index out of range"
    + Sửa lỗi ngầm: mỗi lần tải nhầm file, máy chủ để lại một thư mục rác không bao giờ xoá. Lặp lại nhiều lần sẽ làm đầy ổ đĩa

- 28/07/2026 Phòng KSNB&HTVH - Sửa lỗi tháng/năm không hợp lệ:
    + Gọi lưới bàn giao với tháng ngoài 1–12 (qua đường dẫn trực tiếp, không qua giao diện) làm treo trang. Nay báo lỗi rõ ràng
    + **Báo cáo bàn giao trả sai số liệu âm thầm**: hỏi "tháng 0" thì hệ thống lặng lẽ trả về số liệu **tháng hiện tại** kèm nhãn tháng hiện tại, không cảnh báo gì. Nay báo *"Tháng phải nằm trong khoảng 1–12"*
    + Lịch nghỉ phép cũng chặn năm ngoài 2000–2100 (trước đó mới chặn tháng)

- 28/07/2026 Giao diện - Chữ dễ đọc hơn và thống nhất phông:
    + Chữ ghi chú màu xám nhạt trên toàn hệ thống (**72 chỗ**) đổi sang đậm hơn một bậc — trước đây độ tương phản chỉ đạt 2,5 trên chuẩn tối thiểu 4,5, khó đọc với người phải nhìn bảng số liệu cả ngày
    + **Phông chữ Inter nay dùng cho cả 21 trang**. Trước đây chỉ trang Đăng nhập và Đổi mật khẩu có, 19 trang còn lại rơi về phông mặc định — đăng nhập một kiểu chữ, vào việc lại một kiểu khác
    + Thống nhất nhãn trạng thái chứng từ: "Bị từ chối" ở màn Bàn giao và "Từ chối" ở màn Nghỉ phép nay dùng chung một chữ **"Từ chối"**

- 28/07/2026 Kỹ thuật - Dọn nền
    + Nâng thư viện giao diện lên bản mới (vượt qua một mốc thay đổi lớn). Đã đối chiếu từng dòng CSS của hai bản để chắc chắn **không có gì đổi hình dạng** — 70 khung thẻ trong hệ thống giữ nguyên
    + Sửa bẫy trong hệ thống nâng cấp cơ sở dữ liệu: có 18 câu lệnh trỏ sai tên bảng và **thất bại im lặng** mỗi lần khởi động. Chưa gây hại, nhưng người viết tính năng tiếp theo mà chép nhầm mẫu này thì cột dữ liệu sẽ không được thêm mà không ai biết
    + Cảnh báo khi khởi động nếu máy chủ đang mở ra mạng nội bộ mà chưa cấu hình đúng — gồm cả việc **trang liệt kê toàn bộ 144 cửa giao tiếp đang mở công khai** cho ai vào được cổng 8000
    + Sửa 4 chỗ tài liệu hướng dẫn nội bộ mô tả sai kiến trúc (chỉ tới file không tồn tại, sai tên bảng dữ liệu)
    + Thêm `frontend/ui_kit.py` — gom màu, nhãn trạng thái, khung chờ về một chỗ. Trước đây nhãn trạng thái được định nghĩa ở 3 nơi theo 3 cách khác nhau

- 27/07/2026 Giao diện - Nới rộng vùng nội dung trên màn hình nhỏ:
    + Máy có màn hình rộng từ 1440px trở xuống (máy trạm 1366×768) khi mở phần mềm sẽ **tự thu gọn sidebar**, vùng xem bảng rộng thêm khoảng 184px. Ai đã tự bấm nút thu gọn/mở rộng một lần thì phần mềm nghe theo lựa chọn đó, không tự đổi nữa
    + Bảng rộng hơn màn hình nay **kéo ngang xem được**. Trước đây phần vượt khung bị cắt mất, không có cách nào kéo ra xem
    + Sửa lỗi tính chiều rộng làm mọi trang thừa ra một khoảng bằng đúng bề rộng thanh cuộn dọc

- 27/07/2026 Giao diện - Sidebar (thu gọn/mở rộng):
    + Sidebar **chỉ đóng/mở bằng nút ở góc trên cùng bên trái**. Trước đây click vào mục menu thì sidebar tự thu lại, còn click vùng trống khi đang thu gọn lại tự mở ra — cùng một thao tác cho hai kết quả ngược nhau tuỳ chỗ bấm
    + Click mục menu giờ chỉ chuyển trang, không đụng tới sidebar. Trạng thái đóng/mở giữ nguyên khi chuyển trang
    + Icon trên nút đổi theo trạng thái để biết bấm sẽ đóng hay mở

- 27/07/2026 Phòng Thanh toán - Gom menu Đối chiếu:
    + **Chấm 459901** và **Đối chiếu Song phương** chuyển thành 2 mục con của menu mới **Đối chiếu** (hover ra flyout cấp 2, giống nhóm "Báo cáo" bên KSNB). Phân quyền theo nhóm giữ nguyên (`menu.cham_459901`, `menu.doi_chieu_song_phuong`); nhóm "Đối chiếu" tự ẩn nếu user không có quyền cả 2 mục
    + Tiện thể fix: bấm mục trong menu con cấp 2 nay cũng tự thu gọn sidebar như mục cấp 1 (trước đó bị sót, ảnh hưởng cả 2 nhóm "Báo cáo")

- 22/07/2026 Quản lý User - Nhóm & phân cấp Quản trị viên:
    + Gom các tài khoản quản trị vào **nhóm "Quản trị viên"** trong danh sách Quản lý User Admin **không thuộc phòng nào**: tạo/sửa admin sẽ ẩn ô chọn Phòng, `department_id` để trống
    + Tách quyền quản trị thành **2 cấp**:
        • **Quản trị viên cấp 1** (role cũ `admin`, chỉ đổi nhãn): toàn quyền như trước
        • **Quản trị viên cấp 2** (`admin_l2`, mới): quyền hạn cấu hình qua **Phân quyền theo nhóm** (như các role thường), không mặc định all-access
    + **Chống leo thang quyền**: cấp 2 không được tạo/sửa/xóa hay nâng ai lên cấp 1 — chặn ở cả giao diện (ẩn tùy chọn "cấp 1" khỏi dropdown, khóa nút thao tác trên hàng cấp 1) lẫn backend (trả 403)

- 21/07/2026 Giao diện - Sidebar:
    + Fix nút thu gọn menu (góc trên trái): lỗi thu gọn được nhưng bấm lần nữa không mở lại. 

- 20/07/2026 Phòng KSNB&HTVH - Lưu trữ (sửa số chứng từ trên bảng):
    + Tra cứu lưu trữ cho phép chỉnh trực tiếp cột "Số chứng từ": nhập số vào ô trống để **thêm một tập** cho ngày đó, sửa số hiện có về **0 để xoá tập**. Sau khi lưu, "Số tập" và dòng tổng tự cộng lại (backend đếm lại số tập của nhóm)
    + Cột "Số chứng từ" mở rộng tối thiểu **5 cột** (luôn chừa ô trống để nhập thêm)
    + *Đánh đổi*: tập thêm tay không gắn chứng từ thật (chỉ ngày + số tờ); xoá tập có thể làm lệch số thứ tự "x/tổng" khi in bìa các tập còn lại — chấp nhận vì đây là màn hình chỉnh tay của HKV, tổng số tập đã được tính lại đúng

- 20/07/2026 Toàn hệ thống - Nghỉ phép (Big update):
    + **Nghỉ thai sản / bảo hiểm**: không trừ vào hạn mức phép năm; chọn khoảng ngày bằng lịch cuộn (calendar dropdown); template phiếu hỗ trợ điều kiện 2 năm
    + **Nhập hạn mức phép hàng loạt từ file Excel**: xem trước → áp dụng → hoàn tác (rollback). Cột "Đã nghỉ" tạo bản ghi tổng hợp thay vì ghi từng trường mồ côi
    + **Carry-over**: chuyển tiếp ngày phép chưa dùng của năm trước sang Q1 năm sau
    + **Khai báo hộ** (nhập đơn thay cán bộ khác) + ngày nghỉ lẻ không liên tục (`spread_dates`)
    + Bảng "Nghỉ phép hôm nay" trên Trang chủ, tách theo từng phòng
    + Thống nhất **một nguồn sự thật** cho "số ngày đã dùng": loại thai sản/bảo hiểm khỏi hạn mức phép năm nhất quán ở mọi nơi (thống kê, xuất quota, phiếu) — trước đây mỗi chỗ tính một kiểu
    + Bảng **ủy quyền Giám đốc** chia cột rõ ràng; hoàn thiện luồng duyệt bước Giám đốc (GĐ/PGĐ theo ủy quyền còn hiệu lực)
    + Phân quyền admin (403 đúng chỗ), thêm `leaves.schedule` vào danh mục phân quyền nhóm
    + Xử lý **17 lỗi** phát hiện qua rà soát nghỉ phép

- 20/07/2026 Toàn hệ thống - Nhật ký thao tác (audit log):
    + Ghi tập trung mọi thao tác thay đổi dữ liệu (POST/PUT/PATCH/DELETE) vào bảng `audit_logs` qua middleware `AuditMiddleware` — mỗi request để lại 1 dòng: ai thực hiện, phương thức, đối tượng, kết quả HTTP, IP, thời gian. Không phải rải lệnh ghi log ở từng endpoint
    + Thêm menu "Nhật ký hệ thống" (trang `audit-logs`): lọc theo phương thức, tìm theo tên cán bộ / đối tượng / nội dung, phân trang
    + Tự dọn `audit_logs` cũ hơn 365 ngày

- 20/07/2026 Toàn hệ thống - Cảnh báo lệch giờ máy chủ (NTP):
    + Khi khởi động, so đồng hồ máy chủ với nguồn giờ chuẩn NTP; lệch quá ngưỡng thì ghi CẢNH BÁO vào log. Chỉ cảnh báo, KHÔNG tự sửa giờ (đồng bộ giờ là việc của hệ điều hành / domain), phục vụ độ tin cậy của nhật ký
    + Cấu hình qua `.env`: `NTP_ENABLED`, `NTP_SERVER`, `NTP_TIMEOUT_SEC`, `NTP_DRIFT_THRESHOLD_SEC`. Mạng nội bộ cô lập: trỏ về NTP nội bộ hoặc đặt `NTP_ENABLED=false` để tắt

- 20/07/2026 Phòng KSNB&HTVH - Lưu trữ (tổng hợp cả năm):
    + Thêm bảng tổng hợp lưu trữ theo năm: số tờ / số tập theo từng phòng nghiệp vụ × 12 tháng (endpoint `/storage-summary`). Dùng lại đúng hàm dựng bảng chi tiết nên số liệu luôn khớp với màn hình tra cứu chi tiết

- 20/07/2026 Trang chủ - Biểu đồ bàn giao chứng từ:
    + Thay bảng số liệu "đúng hạn / muộn theo phòng" bằng biểu đồ cột nhóm (4 phòng: Thanh toán, Kế toán, Swift, NosVos × 2 cột đúng hạn/nộp muộn)
    + Ô thống kê "Người dùng" bỏ đếm quản trị viên; "Phòng nghiệp vụ" bỏ đếm Ban Giám đốc

- 20/07/2026 Phòng KSNB&HTVH - Bàn giao chứng từ (giao diện lưới):
    + Cột ngày co giãn để vừa bề ngang màn hình, chỉ cuộn ngang khi hẹp hơn mức tối thiểu; căn header khớp cột nhập bằng `box-sizing:border-box`

- 20/07/2026 Phòng KSNB&HTVH - Bàn giao chứng từ (cán bộ chuyển phòng):
    + Cán bộ chuyển phòng nghiệp vụ vẫn hiển thị đúng phòng cũ cho các tháng **trước** ngày chuyển, phòng mới **từ** ngày chuyển trở đi. Trước đây lưới bàn giao lọc theo phòng hiện tại của cán bộ nên toàn bộ chứng từ cũ "biến mất" khỏi phòng cũ ngay khi họ đổi phòng
    + Thêm bảng lịch sử đổi phòng (`staff_department_history`): mỗi lần quản trị viên đổi phòng cho cán bộ sẽ ghi một mốc theo ngày đổi. Chứng từ được định tuyến về đúng phòng theo **ngày giao dịch** — nhập bù chứng từ tháng cũ cho cán bộ đã chuyển phòng vẫn vào đúng phòng cũ (không rơi nhầm sang phòng mới)
    + Lưới bàn giao hiện cán bộ **từng thuộc** phòng đó trong tháng để nhập bù (kể cả người đã chuyển đi phòng khác)
    + Tự backfill lịch sử phòng cho toàn bộ cán bộ hiện có khi khởi động; báo cáo/xuất Excel/gom tập vốn đã dùng phòng đóng băng trong phiếu nên không đổi
    + *Lưu ý vận hành*: chuyên viên bị khóa ô chọn phòng (chỉ phòng hiện tại) → nhập bù cho cán bộ đã chuyển phòng do HKV / cán bộ phòng cũ chọn phòng cũ + tháng rồi nhập hộ

- 16/07/2026 Phòng Thanh toán - Đối chiếu Song phương (module mới):
    + Định tuyến lệnh IPCAS phục vụ đối chiếu song phương: upload file ZIP (mã hoá AES-256) chứa dữ liệu IPCAS, xử lý bất đồng bộ, theo dõi tiến độ real-time
    + Phân loại mỗi dòng theo 4 ngân hàng (Vietinbank 201, BIDV 202, Vietcombank 203, MBBank 311) × 2 chiều: ĐẾN (`CRAMOUNT=0`) / ĐI (`DRAMOUNT=0`) → xuất 8 file CSV
    + Thêm menu "Đối chiếu Song phương" cho Phòng Thanh toán; phân quyền riêng theo nhóm (`menu.doi_chieu_song_phuong`, `doi_chieu_song_phuong.process`)
    + Thêm thư viện `pyzipper` (đọc ZIP mã hoá AES-256)

- 16/07/2026 Cấu hình - Nạp biến môi trường:
    + `load_dotenv(..., override=True)` ở `config.py`, `api_client.py`, `frontend/main.py`, `run.py` — ép `.env` ghi đè biến môi trường sẵn có của hệ thống, tránh trường hợp máy đã set biến cũ khiến `.env` bị bỏ qua khi chuyển sang máy mới

- 10/07/2026 Phòng KSNB&HTVH - Bàn giao chứng từ (màu trạng thái):
    + Tách bạch màu 3 trạng thái cho dễ nhận biết: "Đang mượn" đổi từ cam sang tím (cam nằm giữa vàng và đỏ nên dễ lẫn). Nay: Chờ xác nhận = vàng, Đang mượn = tím, Bị từ chối = đỏ, Đã xác nhận = xanh lá

- 10/07/2026 Phòng KSNB&HTVH - Báo cáo hậu kiểm:
    + Bỏ chặn tạo báo cáo khi cột "GD Hậu kiểm sai" khác 0 — trước đây báo lỗi và bỏ qua dữ liệu file, nay tạo báo cáo bình thường
    + Fix cột tổng TC (I)/TC (II) và cột tỷ lệ bị trống trên một số máy: báo cáo phòng cũ ghi công thức Excel (=SUM, =IFERROR) nhưng để ô kết quả rỗng, máy nào không tự tính lại (Excel chế độ tính tay, WPS, LibreOffice, xem nhanh) thì hiện trống. Nay tính sẵn số bằng Python, ghi thẳng giá trị vào ô

- 10/07/2026 Phòng KSNB&HTVH - Bàn giao chứng từ:
    + HKV từ chối chứng từ mới: ô chuyển trạng thái "Bị từ chối" (đỏ), giữ lịch sử + lý do thay vì xóa
    + GDV nộp lại ô bị từ chối (nút "Nộp lại" hoặc gõ số khác rồi Lưu) để đưa về "Chờ xác nhận"
    + Thêm màu đỏ + nhãn "Bị từ chối" vào chú thích lưới

- 09/07/2026 Phòng KSNB&HTVH - Báo cáo:
    + Menu "Báo cáo" tách thành menu con: "Báo cáo hậu kiểm" (màn hình cũ) và "Báo cáo bàn giao chứng từ" (mới)
    + Báo cáo bàn giao chứng từ: số chứng từ nộp đúng hạn/quá hạn theo từng phòng nghiệp vụ; chi tiết cán bộ nào nộp chậm chứng từ ngày nào, chậm bao nhiêu ngày làm việc
    + Fix KPI "Tỷ lệ nộp chứng từ đúng hạn" ở Trang chủ luôn hiển thị 100%: cũ so `handover_date` với `transaction_date` nhưng hai cột này luôn bằng nhau khi nhập qua lưới. Nay lấy ngày nộp đầu tiên từ lịch sử thao tác (`entry_change_logs`)
    + Trang chủ và Báo cáo bàn giao dùng chung một hàm tính (`handover_report_service.compute_period`) để không lệch số

- 09/07/2026 Phòng KSNB&HTVH - Bàn giao chứng từ (dọn code chết):
    + Xóa 2 trang cũ `/handovers/new` (lập phiếu bàn giao) và `/handovers/{id}` (chi tiết phiếu) — tàn dư thiết kế cũ, chưa bao giờ có menu/nút dẫn tới và chưa từng được dùng (0/148 phiếu có "người giao", 0 phiếu từng được xác nhận)
    + Xóa 7 endpoint chết kèm theo: `GET /api/handovers/`, `GET|POST|DELETE /api/handovers/{id}`, `POST /api/handovers/{id}/entries`, `DELETE /api/handovers/{id}/entries/{eid}`, `POST /api/handovers/{id}/confirm` (16 route còn 9)

- 05/07/2026 Giao diện 
    + Đăng nhập: đổi theme trang login sang tông đỏ đô + viền vàng đồng
    + Thêm thanh top bar, hoạ tiết vòng tròn trang trí, footer bản quyền; fix set nền trực tiếp trên container thay vì chỉ dựa vào `body` để tránh mất màu khi NiceGUI/Quasar phủ nền riêng
- 16:02:36 05/07/2026 Phòng Swift - Đối chiếu điện SWIFT:
    + Thêm module đối chiếu điện SAA
    + Màn hình quản lý điện (2 chiều Điện đến/Điện đi)
    + 3 nút xuất Excel mỗi chiều (Tổng hợp/Chi tiết lệch/Bản ghi đang lọc)
    + Tab Lịch sử đối chiếu lưu vào DB chung (bảng `swift_recon_history`)
- 14:25 02/07/2026 Phòng Tổng hợp - Báo cáo - Báo cáo thanh toán:
    + Fix lỗi "Worksheet named 'Result' not found" khi upload file IN/OUT — file export tháng mới đặt tên sheet dữ liệu là "Export Worksheet" thay vì "Result", nay tự nhận diện cả hai tên
- 14:25 02/07/2026 Giao diện - Sidebar:
    + Thêm nút thu gọn/mở rộng menu (nhớ trạng thái qua localStorage)
    + Sửa flyout menu con dùng `position: fixed` để không bị cắt khi sidebar cuộn
