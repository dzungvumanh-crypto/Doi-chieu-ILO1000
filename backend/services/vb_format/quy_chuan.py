"""Quy chuẩn trình bày văn bản — bản mã hoá của QĐ 979/QyĐ-NHNo-PC.

Nguồn: Điều 4–17 (khổ giấy, lề, phông chữ, từng thành phần thể thức),
Phụ lục III (bảng cỡ chữ / kiểu chữ), Phụ lục IV (viết hoa).

Quy định cho **dải** cỡ chữ ("13 - 14"), không cho một con số. Ở đây chọn số
lớn của dải làm mặc định vì cột "Cỡ chữ" trong ví dụ minh hoạ của Phụ lục III
dùng đúng số đó; người dùng đổi lại trong tab Cấu hình quy chuẩn. Dải hợp lệ
ghi ở `DAI_CO_CHU` để màn cấu hình cảnh báo khi nhập ra ngoài dải — cảnh báo,
KHÔNG chặn: quy định là dải khuyến nghị, đơn vị có thể có lý do riêng.
"""
from copy import deepcopy

# ── Khoá thành phần thể thức → nhãn tiếng Việt hiển thị trên màn cấu hình ────
NHAN_THANH_PHAN: dict[str, str] = {
    "quoc_hieu":           "Quốc hiệu (CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM)",
    "tieu_ngu":            "Tiêu ngữ (Độc lập - Tự do - Hạnh phúc)",
    "ten_dv_chu_quan":     "Tên đơn vị quản lý trực tiếp",
    "ten_dv_ban_hanh":     "Tên đơn vị ban hành văn bản",
    "so_ky_hieu":          "Số, ký hiệu của văn bản",
    "dia_danh_ngay":       "Địa danh và thời gian ban hành",
    "ten_loai":            "Tên loại văn bản (QUYẾT ĐỊNH, BÁO CÁO…)",
    "trich_yeu":           "Trích yếu nội dung (văn bản có tên loại)",
    "trich_yeu_cong_van":  "Trích yếu nội dung công văn (V/v …)",
    "can_cu":              "Căn cứ ban hành văn bản",
    "phan_chuong":         "Từ “Phần”, “Chương” và số thứ tự",
    "tieu_de_phan_chuong": "Tiêu đề của phần, chương",
    "muc":                 "Từ “Mục”, “Tiểu mục” và số thứ tự",
    "tieu_de_muc":         "Tiêu đề của mục, tiểu mục",
    "muc_la_ma":           "Mục đánh số La Mã (I. NHỮNG KẾT QUẢ…)",
    "dieu":                "Điều",
    "khoan":               "Khoản (1. 2. 3.…)",
    "khoan_co_tieu_de":    "Khoản có tiêu đề",
    "diem":                "Điểm (a) b) c)…)",
    "noi_dung":            "Lời văn (đoạn nội dung thường)",
    "kinh_gui":            "Kính gửi — gửi MỘT nơi (cùng một dòng)",
    "kinh_gui_ds":         "Kính gửi — gửi NHIỀU nơi (liệt kê xuống dòng)",
    "noi_nhan_tieu_de":    "Từ “Nơi nhận:”",
    "noi_nhan_ds":         "Danh sách nơi nhận",
    "quyen_han_chuc_vu":   "Quyền hạn, chức vụ của người ký",
    "ho_ten_nguoi_ky":     "Họ tên của người ký",
    "phu_luc_so":          "Từ “Phụ lục” và số thứ tự",
    "tieu_de_phu_luc":     "Tiêu đề của phụ lục",
    "ky_hieu_nguoi_soan":  "Ký hiệu người soạn thảo và số lượng bản",
    "bang_the_thuc":       "Ô bảng trong khối đầu văn bản (không nhận ra là thành phần nào)",
}

# Dải cỡ chữ quy định cho phép, theo Phụ lục III.
DAI_CO_CHU: dict[str, tuple[float, float]] = {
    "quoc_hieu":           (12, 13),
    "tieu_ngu":            (13, 14),
    "ten_dv_chu_quan":     (12, 13),
    "ten_dv_ban_hanh":     (12, 13),
    "so_ky_hieu":          (13, 13),
    "dia_danh_ngay":       (13, 14),
    "ten_loai":            (13, 14),
    "trich_yeu":           (13, 14),
    "trich_yeu_cong_van":  (12, 13),
    "can_cu":              (13, 14),
    "phan_chuong":         (13, 14),
    "tieu_de_phan_chuong": (13, 14),
    "muc":                 (13, 14),
    "tieu_de_muc":         (13, 14),
    "muc_la_ma":           (13, 14),
    "dieu":                (13, 14),
    "khoan":               (13, 14),
    "khoan_co_tieu_de":    (13, 14),
    "diem":                (13, 14),
    "noi_dung":            (13, 14),
    "kinh_gui":            (13, 14),
    "kinh_gui_ds":         (13, 14),
    "noi_nhan_tieu_de":    (12, 12),
    "noi_nhan_ds":         (11, 11),
    "quyen_han_chuc_vu":   (13, 14),
    "ho_ten_nguoi_ky":     (13, 14),
    "phu_luc_so":          (14, 14),
    "tieu_de_phu_luc":     (13, 14),
    "ky_hieu_nguoi_soan":  (11, 11),
}


# ── Mặc định ─────────────────────────────────────────────────────────────────
# Ý nghĩa các khoá trong một mục "thanh_phan":
#   co       cỡ chữ (pt)
#   dam / nghieng   True/False = ép, None = giữ nguyên của người soạn
#   hoa      "hoa" = ép in hoa toàn bộ, "thuong" = ép in thường, None = không đụng
#   can      left / center / right / justify / None
#   thut_cm  thụt dòng ĐẦU của đoạn (cm), None = không đặt
#   le_trai_cm  thụt CẢ đoạn khỏi lề trái (cm), None = không đặt
#   gian_dong / cach_doan_pt   None = theo giá trị chung của cả văn bản.
#       Có giá trị = ÉP CHÍNH XÁC cho riêng thành phần này (kể cả ép về 0).
#       Cần thiết vì khối thể thức đầu và cuối trang KHÔNG dùng giãn dòng của
#       lời văn: Điều 7.3 và Điều 8.2 nói thẳng Quốc hiệu / Tiêu ngữ / tên đơn
#       vị "trình bày cách nhau dòng đơn". Áp 1,2 và 6pt cho cả khối đó thì
#       Tiêu ngữ bị đẩy xa Quốc hiệu, nhìn không còn giống mẫu Phụ lục V.
def _tp(co, dam=None, nghieng=None, hoa=None, can=None, thut_cm=None, le_trai_cm=None,
        gian_dong=None, cach_doan_pt=None):
    return {"co": co, "dam": dam, "nghieng": nghieng, "hoa": hoa,
            "can": can, "thut_cm": thut_cm, "le_trai_cm": le_trai_cm,
            "gian_dong": gian_dong, "cach_doan_pt": cach_doan_pt}


QUY_CHUAN_MAC_DINH: dict = {
    # ── Điều 4: khổ giấy, định lề ───────────────────────────────────────────
    "trang": {
        "ap_dung": True,
        "rong_mm": 210.0, "cao_mm": 297.0,
        "le_tren_mm": 20.0, "le_duoi_mm": 20.0,
        "le_trai_mm": 30.0, "le_phai_mm": 20.0,
        # Điều 4.4: số trang canh giữa trong phần lề trên, không hiện ở trang 1.
        "danh_so_trang": True,
        "co_so_trang": 14.0,
    },
    # ── Điều 5 + Điều 12 khoản 6: phông chữ và lời văn ──────────────────────
    "chung": {
        "phong_chu": "Times New Roman",
        "ep_phong_chu": True,
        "ep_mau_den": True,
        # Điều 12.6 cho một DẢI: giãn dòng tối thiểu dòng đơn, tối đa 1,5 lines.
        # Lấy 1,2 vì đó là con số đo được trong chính phần lời văn của QĐ 979
        # (`Phần VB_Hướng dẫn thể thức văn bản.docx`, mọi đoạn Căn cứ / Điều /
        # khoản / điểm đều là MULTIPLE 1.2). Lấy 1,5 là lấy đúng cận TRÊN của
        # dải — hợp lệ nhưng thưa hơn hẳn mẫu, in ra dài thêm mấy trang.
        "gian_dong": 1.2,
        "cach_doan_pt": 6.0,      # Điều 12.6: khoảng cách giữa các đoạn tối thiểu 6pt
        "thut_dau_dong_cm": 1.0,  # Điều 12.6: 1 cm hoặc 1,27 cm
        # Tiêu ngữ đúng mẫu là "Độc lập - Tự do - Hạnh phúc": gạch NỐI (-), mỗi
        # bên đúng một dấu cách (Điều 7.2). Người soạn hay gõ gạch ngang dài
        # (– —) hoặc chèn nhiều dấu cách cho dòng dài bằng Quốc hiệu.
        "chuan_tieu_ngu": True,
        # Khoảng cách giữa hai đoạn = `space_after` của đoạn trên CỘNG
        # `space_before` của đoạn dưới. Để cả hai cùng có giá trị là mất kiểm
        # soát: file người dùng đặt 7pt/7pt thì khoảng cách thật là 14pt, gấp
        # hơn hai lần mức Điều 12.6 nêu, mà không ô nào trong hộp Paragraph
        # hiện con số 14 đó. Đưa `space_before` về 0 để chỉ còn MỘT nguồn
        # quyết định khoảng cách.
        "bo_khoang_truoc_doan": True,
        # Dòng thể thức (Quốc hiệu, Tiêu ngữ, tên đơn vị…) phải nằm gọn một
        # dòng. Tràn thì nén ký tự lại đúng cách mẫu 979 làm — Phụ lục V có
        # dòng tên đơn vị đầy đủ đặt w:spacing = -24. Trần lấy đúng mức đó:
        # nén quá tay thì chữ dính nhau, đọc còn khó hơn là để xuống dòng.
        "nen_chu_cho_vua_dong": True,
        "nen_toi_da_twip": 24,
        # Điều 7.2 / 8.2 / 11.2: dưới Tiêu ngữ, tên đơn vị ban hành và trích
        # yếu có ĐƯỜNG KẺ NGANG nét liền — không phải gạch chân. Mẫu 979 vẽ
        # bằng 7 thẻ <v:line>, không dùng gạch chân chỗ nào.
        "go_gach_chan_the_thuc": True,
        "ve_duong_ke_ngang": True,
        # Ngắt trang tay được đặt theo bố cục CŨ. Chuẩn hoá làm chữ cao lên
        # (giãn dòng 1,2, lề trên 20 mm) nên chỗ xuống trang dịch đi và dấu
        # ngắt cũ đẻ ra một trang gần như trống. Tắt ô này khi văn bản thật sự
        # cần sang trang mới — Phụ lục ban hành kèm theo Quyết định chẳng hạn.
        "bo_ngat_trang_thu_cong": True,
        # QĐ 979 chỉ đánh số tới *điểm* (a, b, c) — dưới đó không có cấp nào
        # được khai, nên phân cấp chỉ còn trông vào thụt lề. Gạch đầu dòng thụt
        # sâu hơn mức chung là tác giả đang nói "đây là mục con"; ép về 0 là xoá
        # phẳng phân cấp đó.
        "giu_thut_muc_con": True,
        # Suy ra mục con khi tác giả KHÔNG để lại dấu hiệu nào: dòng gạch đầu
        # dòng kết thúc bằng ":" thì các dòng gạch đầu dòng ngay sau là mục con.
        # Xem `nhan_dien.cap_gach_dau_dong` để biết danh sách con đóng ở đâu.
        "phan_cap_gach_dau_dong": True,
        "thut_muc_con_cm": 1.0,
    },
    "thanh_phan": {
        # Cỡ chữ khối đầu lấy theo con số ĐẾM ĐƯỢC trên cả 18 mẫu của Phụ lục V
        # (Quốc hiệu 12 ở 17/18 mẫu, tên đơn vị 12, trích yếu công văn 12), không
        # lấy cận trên của dải "12 - 13". Chên lệch một điểm ở đây không phải chuyện
        # thẩm mỹ: dòng "NGÂN HÀNG NÔNG NGHIỆP VÀ PHÁT TRIỂN NÔNG THÔN VIỆT NAM"
        # ở cỡ 13 tràn khỏi cột bên trái và đẩy chữ "NAM" xuống một dòng riêng.
        "quoc_hieu":           _tp(12, dam=True,  nghieng=False, hoa="hoa", can="center", gian_dong=1.0, cach_doan_pt=0.0),
        "tieu_ngu":            _tp(13, dam=True,  nghieng=False, can="center", gian_dong=1.0, cach_doan_pt=0.0),
        "ten_dv_chu_quan":     _tp(12, dam=False, nghieng=False, hoa="hoa", can="center", gian_dong=1.0, cach_doan_pt=0.0),
        "ten_dv_ban_hanh":     _tp(12, dam=True,  nghieng=False, hoa="hoa", can="center", gian_dong=1.0, cach_doan_pt=0.0),
        "so_ky_hieu":          _tp(13, dam=False, nghieng=False, can="center", gian_dong=1.0, cach_doan_pt=0.0),
        "dia_danh_ngay":       _tp(14, dam=False, nghieng=True,  can="center", gian_dong=1.0, cach_doan_pt=0.0),
        "ten_loai":            _tp(14, dam=True,  nghieng=False, hoa="hoa", can="center", gian_dong=1.0, cach_doan_pt=0.0),
        "trich_yeu":           _tp(14, dam=True,  nghieng=False, can="center", gian_dong=1.0, cach_doan_pt=0.0),
        "trich_yeu_cong_van":  _tp(12, dam=False, nghieng=False, can="center", gian_dong=1.0, cach_doan_pt=0.0),
        # Lời văn để `dam=None` (giữ nguyên): một câu trong văn bản hay có cụm in
        # đậm cố ý — tên văn bản được viện dẫn, số tiền, mốc thời hạn. Ép tắt đậm là
        # xoá sạch những chỗ đó, mà Phụ lục III không hề cấm in đậm trong lời văn — cột
        # "Kiểu chữ" của nó nói về kiểu chủ đạo của đoạn. Ai muốn ép thì bật trong
        # tab Cấu hình. Riêng "nghiêng" của căn cứ và địa danh là quy định nói thẳng.
        "can_cu":              _tp(14, dam=None,  nghieng=True,  can="justify", thut_cm=1.0, le_trai_cm=0.0),
        "phan_chuong":         _tp(14, dam=True,  nghieng=False, can="center"),
        "tieu_de_phan_chuong": _tp(14, dam=True,  nghieng=False, hoa="hoa", can="center"),
        "muc":                 _tp(14, dam=True,  nghieng=False, can="center"),
        "tieu_de_muc":         _tp(14, dam=True,  nghieng=False, hoa="hoa", can="center"),
        "muc_la_ma":           _tp(14, dam=True,  nghieng=False, hoa="hoa", can="justify", thut_cm=0.0),
        "dieu":                _tp(14, dam=True,  nghieng=False, can="justify", thut_cm=1.0, le_trai_cm=0.0),
        "khoan":               _tp(14, dam=None,  nghieng=None,  can="justify", thut_cm=1.0, le_trai_cm=0.0),
        "khoan_co_tieu_de":    _tp(14, dam=True,  nghieng=False, can="justify", thut_cm=1.0, le_trai_cm=0.0),
        "diem":                _tp(14, dam=None,  nghieng=None,  can="justify", thut_cm=1.0, le_trai_cm=0.0),
        "noi_dung":            _tp(14, dam=None,  nghieng=None,  can="justify", thut_cm=1.0, le_trai_cm=0.0),
        # Điều 15.4.a: gửi MỘT nơi thì "Kính gửi" và tên đơn vị nằm trên cùng một
        # dòng — mẫu 06 và 09 của Phụ lục V đều canh giữa dòng đó. Gửi NHIỀU nơi
        # thì chỉ có chữ "Kính gửi:" đứng riêng rồi liệt kê xuống dòng, lúc đó canh
        # giữa là sai — mẫu 08 để sát trái. Hai tình huống, hai mã riêng.
        "kinh_gui":            _tp(14, dam=None,  nghieng=None,  can="center", thut_cm=0.0, le_trai_cm=0.0, gian_dong=1.0, cach_doan_pt=0.0),
        "kinh_gui_ds":         _tp(14, dam=None,  nghieng=None,  can="left",   thut_cm=0.0, le_trai_cm=0.0, gian_dong=1.0, cach_doan_pt=0.0),
        "noi_nhan_tieu_de":    _tp(12, dam=True,  nghieng=True,  can="left", thut_cm=0.0, le_trai_cm=0.0, gian_dong=1.0, cach_doan_pt=0.0),
        "noi_nhan_ds":         _tp(11, dam=False, nghieng=False, can="left", thut_cm=0.0, le_trai_cm=0.0, gian_dong=1.0, cach_doan_pt=0.0),
        "quyen_han_chuc_vu":   _tp(14, dam=True,  nghieng=False, hoa="hoa", can="center", gian_dong=1.0, cach_doan_pt=0.0),
        "ho_ten_nguoi_ky":     _tp(14, dam=True,  nghieng=False, can="center", gian_dong=1.0, cach_doan_pt=0.0),
        "phu_luc_so":          _tp(14, dam=True,  nghieng=False, can="center", gian_dong=1.0, cach_doan_pt=0.0),
        "tieu_de_phu_luc":     _tp(14, dam=True,  nghieng=False, hoa="hoa", can="center", gian_dong=1.0, cach_doan_pt=0.0),
        "ky_hieu_nguoi_soan":  _tp(11, dam=False, nghieng=False, can="left", thut_cm=0.0, gian_dong=1.0, cach_doan_pt=0.0),
        # Ô bảng nằm trong khối đầu văn bản mà không nhận ra là thành phần nào.
        # Không đụng cỡ chữ và căn lề (không biết nó là gì thì không áp luật của ai),
        # nhưng VẪN phải kéo giãn dòng và cách đoạn về 0: khối đầu thường được dựng
        # bằng bảng hai cột, bỏ sót là còn nguyên các ô spacing 7pt/7pt của người soạn
        # và khối đầu vẫn giãn xa dù mọi đoạn nhận ra đều đã về 0.
        "bang_the_thuc":       _tp(None, gian_dong=1.0, cach_doan_pt=0.0),
    },
    # ── Cụm từ không được tách qua hai dòng ─────────────────────────────────
    # Cách làm: thay dấu cách BÊN TRONG cụm bằng dấu cách không ngắt (U+00A0).
    # Word không xuống dòng ở dấu cách không ngắt nên cả cụm luôn đi liền nhau.
    "lien_dong": {
        "ap_dung": True,
        # Chỉ để cụm NGẮN. Một cụm dài được ghim liền dòng sẽ thành một khối
        # không bẻ được: Word phải đẩy cả khối xuống dòng dưới và để lại một
        # khoảng trống dài ở cuối dòng trên — văn bản căn đều hai bên thì thành
        # giãn chữ thưa thớt, nhìn còn xấu hơn lúc bị tách dòng.
        "cum_tu": [
            "Tổng Giám đốc", "Phó Tổng Giám đốc", "Giám đốc", "Phó Giám đốc",
            "Trưởng phòng", "Phó Trưởng phòng", "Chánh Văn phòng",
            "Kế toán trưởng", "Chủ tịch", "Thủ trưởng đơn vị",
            # Tên nước không được tách đôi. Gặp thật: dòng tên đơn vị bị ngắt
            # thành "…NÔNG THÔN VIỆT" và "NAM" nằm một mình ở dòng thứ ba.
            "Việt Nam",
        ],
    },
    # ── Phụ lục IV: viết hoa ────────────────────────────────────────────────
    "viet_hoa": {
        "dau_cau": True,    # I. Viết hoa vì phép đặt câu
        "vien_dan": True,   # V.7. Phần/Chương/Mục/Tiểu mục/Điều viết hoa; khoản, điểm viết thường
        "tu_dien": True,    # V. Danh từ đặc biệt + tên cơ quan, tổ chức
        "cum_tu": [
            "Nhà nước", "Nhân dân", "Chính phủ", "Quốc hội", "Thủ tướng Chính phủ",
            "Ngân hàng Nhà nước Việt Nam", "Ngân hàng Nhà nước",
            "Ngân hàng Nông nghiệp và Phát triển nông thôn Việt Nam",
            "Agribank", "Hội đồng thành viên", "Tổng Giám đốc", "Phó Tổng Giám đốc",
            "Ban Kiểm soát", "Ban Pháp chế", "Phòng Tổng hợp", "Trụ sở chính",
            "Văn phòng đại diện", "Đơn vị sự nghiệp", "Phòng Giao dịch",
            "Việt Nam", "Hà Nội", "Thành phố Hồ Chí Minh",
        ],
    },
    # ── Đánh số và gạch đầu dòng ────────────────────────────────────────────
    "danh_so": {
        "gach_dau_dong": True,      # mọi ký tự gạch đầu dòng → "- " (đúng một dấu cách)
        "ky_tu_gach": "-",
        # Mục con dùng ký tự khác cấp ngoài. QĐ 979 không quy định gì dưới cấp
        # *điểm*, nên đây là thói quen văn bản hành chính chứ không phải điều
        # khoản: cấp ngoài "-", cấp trong "+".
        "ky_tu_gach_cap2": "+",
        "chuan_khoan_diem": True,   # "1)" / "1/" → "1."   |   "a." / "a/" → "a)"
        "chuan_muc_la_ma": True,    # "I)" / "I/" → "I."
        "bo_bullet_tu_dong": True,  # danh sách chấm tròn của Word → gõ thẳng "- "
        # Danh sách ĐÁNH SỐ tự động của Word: mặc định TẮT — xem docstring danh_so.py.
        "bo_so_tu_dong": False,
    },
    # ── Đánh dấu vùng đã sửa ────────────────────────────────────────────────
    "danh_dau": {
        "bat": True,
        "mau_dinh_dang": "YELLOW",        # sửa phông / cỡ / kiểu / căn lề / giãn dòng
        "mau_noi_dung": "BRIGHT_GREEN",   # sửa chữ: viết hoa, đánh số, gạch đầu dòng
        "mau_lien_dong": "TURQUOISE",     # cụm từ được ghép liền dòng
        "xoa_danh_dau_cu": False,         # gỡ mọi highlight sẵn có trước khi chạy
    },
}

# Màu highlight Word cho phép — khoá là tên WD_COLOR_INDEX, giá trị là nhãn.
MAU_DANH_DAU: dict[str, str] = {
    "YELLOW": "Vàng", "BRIGHT_GREEN": "Xanh lá", "TURQUOISE": "Xanh ngọc",
    "PINK": "Hồng", "GRAY_25": "Xám nhạt", "TEAL": "Xanh mòng két",
    "VIOLET": "Tím", "RED": "Đỏ", "DARK_YELLOW": "Vàng đậm", "BLUE": "Xanh dương",
}


def mac_dinh() -> dict:
    """Bản sao SÂU của quy chuẩn gốc.

    Trả bản sao chứ không trả chính `QUY_CHUAN_MAC_DINH`: người gọi hợp nhất
    cấu hình người dùng lên trên rồi sửa tại chỗ — đụng thẳng vào hằng số này
    thì mọi request sau đó chạy với dữ liệu của request trước.
    """
    return deepcopy(QUY_CHUAN_MAC_DINH)


def hop_nhat(nguoi_dung: dict | None) -> dict:
    """Đắp cấu hình người dùng lên quy chuẩn gốc, theo từng khoá con.

    Không dùng `{**mac_dinh, **nguoi_dung}`: cấu hình lưu trong DB có thể được
    ghi từ một phiên bản cũ hơn, thiếu hẳn một nhóm khoá. Trộn nông sẽ nuốt cả
    nhóm mặc định của khoá đó và code phía sau vỡ vì `KeyError` — trong khi
    đúng ra chỉ cần lấy mặc định cho đúng phần còn thiếu.
    """
    ket_qua = mac_dinh()
    if not nguoi_dung:
        return ket_qua
    for nhom, gia_tri in nguoi_dung.items():
        if nhom not in ket_qua:
            continue                       # khoá lạ: bỏ qua, không dựng thêm nhánh
        if nhom == "thanh_phan":
            for ma, tp in (gia_tri or {}).items():
                if ma in ket_qua["thanh_phan"] and isinstance(tp, dict):
                    ket_qua["thanh_phan"][ma].update(tp)
        elif isinstance(ket_qua[nhom], dict) and isinstance(gia_tri, dict):
            ket_qua[nhom].update(gia_tri)
        else:
            ket_qua[nhom] = gia_tri
    return ket_qua
