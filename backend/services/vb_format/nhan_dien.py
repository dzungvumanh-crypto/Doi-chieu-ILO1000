"""Nhận diện thành phần thể thức của từng đoạn văn.

Đầu vào là danh sách đoạn đã lấy phẳng khỏi file .docx (kèm cờ "nằm trong
bảng"), đầu ra là mã thành phần cho từng đoạn — `quoc_hieu`, `dieu`, `khoan`,
`noi_nhan_ds`… Mã này quyết định cỡ chữ / kiểu chữ nào được áp ở bước sau.

## Vì sao đoán bằng mẫu chữ chứ không hỏi người dùng

Người dùng chỉ tải lên một file Word bất kỳ, không có siêu dữ liệu nào nói
"đoạn này là trích yếu". Word cũng không lưu ý nghĩa thể thức — nó chỉ lưu chữ
và định dạng. Vậy chỉ còn cách đọc chính con chữ.

## Hai lượt, không phải một

Lượt 1 đoán độc lập từng đoạn theo mẫu chữ (`^Điều\\s+\\d+\\.`, `^Căn cứ`…).
Lượt 2 sửa lại theo ngữ cảnh, vì có những thành phần KHÔNG có dấu hiệu riêng:

* Trích yếu chỉ là "đoạn ngay dưới tên loại văn bản" — bản thân nó là một câu
  in thường như mọi câu khác.
* Danh sách nơi nhận chỉ là "các dòng dưới chữ Nơi nhận:" — chúng bắt đầu bằng
  gạch đầu dòng y hệt mọi gạch đầu dòng trong lời văn.
* Họ tên người ký chỉ là "dòng dưới chức vụ người ký".

Đoán một lượt sẽ gán nhầm cả ba thành `noi_dung` và áp sai cỡ chữ — riêng danh
sách nơi nhận là cỡ 11 chứ không phải 14, sai một trời một vực.

## Đoạn nằm trong bảng

Khối Quốc hiệu / tên đơn vị đầu trang thường được người soạn dựng bằng một
bảng hai cột (cách làm phổ biến để hai khối nằm cạnh nhau). Nên vẫn phải nhận
diện đoạn trong bảng. Nhưng bảng SỐ LIỆU giữa văn bản thì cỡ chữ do người soạn
tự quyết (Điều 4.2 cho phép cả xoay ngang trang vì bảng biểu) — đoạn trong bảng
không khớp thành phần nào được gắn mã `bang` và bước sau chỉ sửa phông chữ,
không đụng cỡ chữ hay căn lề.
"""
import re
import unicodedata

# ── Tên loại văn bản (Điều 3) ────────────────────────────────────────────────
TEN_LOAI_VB = {
    "ĐIỀU LỆ", "QUY CHẾ", "QUY ĐỊNH", "QUY TRÌNH", "QUYẾT ĐỊNH",
    "NỘI QUY LAO ĐỘNG", "HƯỚNG DẪN", "NGHỊ QUYẾT", "VĂN BẢN HỢP NHẤT",
    "TỜ TRÌNH", "THƯ CÔNG TÁC", "THÔNG BÁO", "BÁO CÁO", "KẾ HOẠCH",
    "ĐỀ ÁN", "PHƯƠNG ÁN", "DỰ ÁN", "BIÊN BẢN", "HỢP ĐỒNG", "BẢN THỎA THUẬN",
    "BẢN GHI NHỚ", "GIẤY ỦY QUYỀN", "GIẤY GIỚI THIỆU", "GIẤY ĐI ĐƯỜNG",
    "GIẤY MỜI", "GIẤY BIÊN NHẬN", "ĐƠN XIN NGHỈ PHÉP", "PHIẾU TRÌNH CHUYỂN",
    "BIÊN BẢN BÀN GIAO", "CHƯƠNG TRÌNH", "THÔNG CÁO",
}

# Từ khoá chức danh — dùng để tách "quyền hạn, chức vụ người ký" khỏi một dòng
# in hoa bất kỳ. Không có danh sách này thì mọi tiêu đề in hoa cuối văn bản đều
# bị nhận nhầm là chức danh và bị căn giữa.
TU_KHOA_CHUC_DANH = (
    "GIÁM ĐỐC", "CHỦ TỊCH", "TRƯỞNG PHÒNG", "TRƯỞNG BAN", "CHÁNH VĂN PHÒNG",
    "KẾ TOÁN TRƯỞNG", "THỦ TRƯỞNG", "TRƯỞNG ĐƠN VỊ", "PHÓ", "QUYỀN",
    "TỔNG GIÁM ĐỐC", "HỘI ĐỒNG", "BAN KIỂM SOÁT", "TRƯỞNG BỘ PHẬN",
)
TIEN_TO_QUYEN_HAN = ("TM.", "KT.", "TL.", "TUQ.", "Q.")

# Chữ cái tiếng Việt dùng đánh thứ tự điểm (Điều 12.5.b)
CHU_CAI_DIEM = "abcdđeghiklmnopqrstuvxy"

# ── Biểu thức nhận dạng ──────────────────────────────────────────────────────
RE_SO_KY_HIEU  = re.compile(r"^Số\s*:", re.I)
# Địa danh + thời gian ban hành (Điều 10): khớp CẢ DÒNG, không phải "có chứa".
# Hai điểm dễ hỏng nếu làm qua loa:
#   • Phần số ĐỂ TRỐNG là chuyện thường — dự thảo trình ký và mọi mẫu
#     trong Phụ lục V đều ghi "ngày      tháng      năm 2023". Đòi `\\d{1,2}`
#     là bỏ sót đúng loại file người dùng mang tới để chuẩn hoá.
#   • Phải kết thúc ở năm. Không ràng buộc điều đó thì câu lời văn viện dẫn
#     "… Quyết định số 05/QĐ ngày 05 tháng 01 năm 2026 của Tổng Giám đốc…"
#     cũng bị nhận là địa danh - ngày tháng rồi bị căn giữa và in nghiêng.
RE_DIA_DANH_NGAY = re.compile(
    r"^.{1,45}?,\s*ngày\s*\d{0,2}\s*tháng\s*\d{0,2}\s*năm\s*\d{0,4}\s*\.?$", re.I)
RE_CAN_CU      = re.compile(r"^Căn\s+cứ\b", re.I)
RE_TRICH_YEU_CV = re.compile(r"^V/v\b", re.I)
RE_PHAN_CHUONG = re.compile(r"^(Phần|Chương)\s+([IVXLCDM]+|\d+)\s*\.?$", re.I)
RE_MUC         = re.compile(r"^(Tiểu\s+mục|Mục)\s+(\d+|[IVXLCDM]+)\s*\.?$", re.I)
RE_MUC_LA_MA   = re.compile(r"^([IVXLCDM]+)\s*[.)/]\s*(.+)$")
RE_DIEU        = re.compile(r"^Điều\s+\d+\s*[.:]")
RE_KHOAN       = re.compile(r"^(\d{1,2})\s*[.)/]\s*(.*)$")
RE_DIEM        = re.compile(rf"^([{CHU_CAI_DIEM}]{{1,2}})\s*[).]\s+(.*)$")
# Mẫu 06 của Phụ lục V ghi "Kính gửi ……." không có dấu hai chấm — đòi dấu
# hai chấm là bỏ sót. Nhóm 1 giữ phần đứng SAU để phân biệt gửi một nơi
# (có tên đơn vị ngay trên cùng dòng) với gửi nhiều nơi (liệt kê xuống dòng).
RE_KINH_GUI    = re.compile(r"^Kính\s+gửi\s*:?\s*(.*)$", re.I)
RE_NOI_NHAN    = re.compile(r"^Nơi\s+nhận\s*:", re.I)
RE_LUU         = re.compile(r"^-?\s*Lưu\s*:", re.I)
RE_PHU_LUC     = re.compile(r"^Phụ\s+lục\s+([IVXLCDM]+|\d+)\s*:?$", re.I)
RE_KY_HIEU_SOAN = re.compile(r"^[A-ZĐ]{1,6}\.?\s*\(\d+\)\.?$")
RE_GACH_DAU    = re.compile(r"^[-–—‒‑•·*+]\s*")

def bo_dau(s: str) -> str:
    """Bỏ dấu tiếng Việt — chỉ dùng để SO SÁNH, không dùng để ghi ra file."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    ).replace("đ", "d").replace("Đ", "D")


def _gon(s: str) -> str:
    """Gộp mọi khoảng trắng liên tiếp thành một dấu cách và cắt hai đầu."""
    return re.sub(r"\s+", " ", (s or "").replace(" ", " ")).strip()


def la_in_hoa(s: str) -> bool:
    """Đoạn có phải toàn chữ in hoa không (bỏ qua số và dấu câu).

    Dùng `str.islower()` chứ KHÔNG dùng dải ký tự `[ạ-ỹ]`: khối Latin Extended
    Additional xếp xen kẽ hoa và thường (Ạ U+1EA0, ạ U+1EA1, Ả U+1EA2…), nên một dải
    "chữ thường" kiểu đó nuốt luôn toàn bộ chữ HOA có dấu. Hậu quả đã gặp thật:
    "QUY ĐỊNH CHUNG" bị coi là có chữ thường (vì chứa "Ị"), tiêu đề chương
    không được nhận ra và bị căn đều hai bên như lời văn thường.
    """
    co_chu = False
    for c in s:
        if c.isalpha():
            co_chu = True
            if c.islower():
                return False
    return co_chu


def _la_ten_rieng(s: str) -> bool:
    """Chuỗi có dáng một họ tên người: 2–7 từ, mỗi từ viết hoa chữ đầu, không số."""
    tu = s.split()
    if not 2 <= len(tu) <= 7 or any(c.isdigit() for c in s):
        return False
    return all(t[:1].isupper() for t in tu if t[:1].isalpha())


def _la_chuc_danh(s: str) -> bool:
    hoa = s.upper().rstrip(":. ")
    if hoa.startswith(TIEN_TO_QUYEN_HAN):
        return True
    return la_in_hoa(s) and len(s) <= 70 and any(k in hoa for k in TU_KHOA_CHUC_DANH)


# ── Lượt 1: đoán độc lập từng đoạn ───────────────────────────────────────────
def _doan_doc_lap(txt: str, trong_bang: bool) -> str | None:
    t = _gon(txt)
    if not t:
        return "trong"

    khong_dau = bo_dau(t).upper()
    # Phải là cả dòng đúng bằng Quốc hiệu, không phải "có chứa". Một văn bản
    # nói VỀ thể thức sẽ có câu “1. Quốc hiệu “CỘNG HÒA…”: được trình bày…” —
    # đã từng bị nhận nhầm là Quốc hiệu rồi bị ép IN HOA cả câu.
    if khong_dau.startswith("CONG HOA XA HOI CHU NGHIA VIET NAM") and len(t) <= 60:
        return "quoc_hieu"
    if (khong_dau.startswith("DOC LAP") and "TU DO" in khong_dau
            and "HANH PHUC" in khong_dau and len(t) <= 60):
        return "tieu_ngu"
    if RE_SO_KY_HIEU.match(t):
        return "so_ky_hieu"
    if RE_DIA_DANH_NGAY.match(t):
        return "dia_danh_ngay"
    if RE_TRICH_YEU_CV.match(t):
        return "trich_yeu_cong_van"
    m = RE_KINH_GUI.match(t)
    if m:
        # Còn chữ sau "Kính gửi" → gửi một nơi, cả cụm nằm trên một dòng.
        con_lai = m.group(1).strip(" .…:")
        return "kinh_gui" if con_lai else "kinh_gui_ds"
    if RE_NOI_NHAN.match(t):
        return "noi_nhan_tieu_de"
    if RE_PHU_LUC.match(t):
        return "phu_luc_so"
    if RE_KY_HIEU_SOAN.match(t):
        return "ky_hieu_nguoi_soan"
    if RE_CAN_CU.match(t):
        return "can_cu"
    if RE_PHAN_CHUONG.match(t):
        return "phan_chuong"
    if RE_MUC.match(t):
        return "muc"
    if RE_DIEU.match(t):
        return "dieu"
    # Tên loại văn bản: cả dòng đúng bằng một tên loại, không kèm gì thêm.
    if t.upper().rstrip(".:") in TEN_LOAI_VB:
        return "ten_loai"
    # Mục La Mã kiểu b ("I. NHỮNG KẾT QUẢ ĐẠT ĐƯỢC") — phần sau số phải in hoa,
    # nếu không thì đó là câu thường mở đầu bằng chữ I/V/X viết hoa.
    m = RE_MUC_LA_MA.match(t)
    if m and la_in_hoa(m.group(2)):
        return "muc_la_ma"
    if RE_DIEM.match(t):
        return "diem"
    if RE_KHOAN.match(t):
        return "khoan"
    if trong_bang:
        return "bang"
    return "noi_dung"


# Trích yếu kết thúc ở đây thì dòng sau là phần khác của văn bản.
_KET_TRICH_YEU = (".", "!", "?", ";", ":")


def _noi_dai_trich_yeu(ma: list[str], txt: list[str], i: int, ke_tiep) -> None:
    """Trích yếu dài bị xuống dòng thì các dòng sau CŨNG là trích yếu.

    Người soạn ngắt dòng để hai dòng cân nhau, không phải vì hết câu. Chỉ nhận
    dòng đầu thì dòng thứ hai rơi vào `noi_dung`: nó bị căn đều hai bên trong
    khi dòng trên căn giữa, và không được in đậm theo — nhìn ra ngay là hai
    khối lệch nhau, đúng lỗi người dùng chỉ ra.

    Dấu hiệu "còn dở": dòng trên KHÔNG kết thúc bằng dấu chấm / chấm phẩy /
    hai chấm. Trong văn bản thật dòng trên hay kết thúc bằng dấu phẩy.

    Chặn hai đầu để không nuốt cả phần nội dung phía sau:
      * chỉ nối tiếp khi đoạn sau vẫn là `noi_dung` / `bang` (gặp Căn cứ, Điều,
        Kính gửi… là dừng — chúng đã có mã riêng);
      * nhiều nhất 3 dòng. Trích yếu dài hơn thế thì gần như chắc chắn đã lấn
        sang lời văn, và ép đậm + canh giữa cả một đoạn lời văn là hỏng to hơn
        việc bỏ sót một dòng trích yếu.
    """
    for _ in range(2):
        truoc = _gon(txt[i])
        if truoc.endswith(_KET_TRICH_YEU):
            return
        j = ke_tiep(i)
        if j < 0 or ma[j] not in ("noi_dung", "bang"):
            return
        if len(_gon(txt[j])) > 200:
            return
        ma[j] = "trich_yeu"
        i = j


# Tên đơn vị dài được phép trình bày trên NHIỀU DÒNG (Điều 8.2). Dòng nối tiếp
# mở đầu bằng liên từ hoặc gạch nối — không tên cơ quan nào bắt đầu như vậy,
# nên đây là dấu hiệu chắc chắn chứ không phải phỏng đoán.
_NOI_TIEP_TEN_DV = ("VÀ ", "VÀ ", "- ", "– ", "— ")


def _gom_ten_dv_nhieu_dong(khoi: list[int], txt: list[str]) -> list[list[int]]:
    """Gộp các dòng in hoa đầu văn bản thành từng CỤM = từng tên đơn vị.

    Trước đây quy tắc là "dòng cuối là đơn vị ban hành, các dòng trên là đơn vị
    chủ quản". Quy tắc đó đọc mỗi dòng là một cấp đơn vị, nên gặp một tên dài
    xuống dòng thì cắt đôi chính cái tên ấy:

        NGÂN HÀNG NÔNG NGHIỆP              → tưởng là đơn vị chủ quản → BỎ đậm
        VÀ PHÁT TRIỂN NÔNG THÔN VIỆT NAM   → tưởng là đơn vị ban hành → in đậm

    Bản gốc in đậm cả hai dòng vì đó là MỘT tên. Chuẩn hoá xong nửa trên hoá
    chữ thường — sai ngay dòng đầu tiên của văn bản, và sai theo kiểu "phần mềm
    tự tin làm đúng" nên người dùng dễ tin là đúng.

    Ngược lại, khối HAI CẤP thật thì dòng sau là một tên độc lập:

        NGÂN HÀNG NÔNG NGHIỆP VÀ PHÁT TRIỂN NÔNG THÔN VIỆT NAM   → chủ quản
        CHI NHÁNH HÀ NỘI                                          → ban hành

    Phân biệt bằng chữ mở đầu: "CHI NHÁNH" bắt đầu một tên mới, "VÀ" thì không.
    Cố ý chỉ nhận đúng liên từ và gạch nối — hẹp nhưng chắc. Chỗ xuống dòng
    giữa cụm danh từ ("… VÀ PHÁT TRIỂN / NÔNG THÔN VIỆT NAM") không có dấu hiệu
    nào đọc ra được, và đoán bừa ở đây là gộp nhầm hai cấp đơn vị thật thành
    một — hỏng nặng hơn hẳn cái nó định chữa.
    """
    cum: list[list[int]] = []
    for i in khoi:
        t = _gon(txt[i]).upper()
        if cum and t.startswith(_NOI_TIEP_TEN_DV):
            cum[-1].append(i)
        else:
            cum.append([i])
    return cum


# ── Lượt 2: sửa theo ngữ cảnh ────────────────────────────────────────────────
def _sua_theo_ngu_canh(ma: list[str], txt: list[str], trong_bang: list[bool]) -> None:
    n = len(ma)

    def _ke_tiep(i: int) -> int:
        """Chỉ số đoạn có chữ kế tiếp; -1 nếu hết."""
        for j in range(i + 1, n):
            if ma[j] != "trong":
                return j
        return -1

    # ── Tên loại văn bản không có trong danh sách Điều 3 ──
    # Điều 3 khoản 2 điểm aa cho phép "các loại văn bản xử lý công việc cụ thể
    # KHÁC phù hợp với thực tiễn hoạt động" — nên danh sách tên loại không bao
    # giờ đủ. Gặp thật: "ĐỀ CƯƠNG" (đề cương kiểm tra) không có trong Điều 3,
    # bị xếp thành lời văn và bị căn đều hai bên thay vì canh giữa.
    #
    # Nhận theo hình thức, nhưng chỉ khi có MỐC chắc chắn là số ký hiệu hoặc
    # địa danh - ngày tháng: tên loại luôn nằm DƯỚI mốc đó (Phụ lục II). Không
    # có mốc thì không đoán — một dòng in hoa đứng riêng giữa văn bản có thể là
    # tiêu đề bảng, tên phụ lục, bất cứ thứ gì.
    if "ten_loai" not in ma:
        moc = next((i for i in range(n) if ma[i] in ("so_ky_hieu", "dia_danh_ngay")), -1)
        if moc >= 0:
            for i in range(moc + 1, min(n, moc + 16)):
                if ma[i] in ("dieu", "phan_chuong", "muc", "muc_la_ma", "can_cu",
                             "kinh_gui", "noi_nhan_tieu_de", "trich_yeu_cong_van"):
                    break                       # đã sang phần nội dung, thôi tìm
                if ma[i] not in ("noi_dung", "bang"):
                    continue
                t = _gon(txt[i])
                if (la_in_hoa(t) and len(t) <= 60
                        and not t.endswith((";", ":", ","))
                        and not _la_chuc_danh(t)):
                    ma[i] = "ten_loai"
                    break

    # ── Trích yếu: đoạn có chữ ngay dưới tên loại văn bản ──
    for i in range(n):
        if ma[i] != "ten_loai":
            continue
        j = _ke_tiep(i)
        # Chỉ nhận khi đoạn kế là câu thường ngắn; "Căn cứ …" hay "Điều 1." đi
        # ngay sau tên loại nghĩa là văn bản KHÔNG có trích yếu.
        if j >= 0 and ma[j] in ("noi_dung", "bang") and len(_gon(txt[j])) <= 200:
            ma[j] = "trich_yeu"
            _noi_dai_trich_yeu(ma, txt, j, _ke_tiep)

    # ── Tên đơn vị: các dòng in hoa ở đầu văn bản, trước tên loại ──
    # CỤM cuối của khối là tên đơn vị ban hành (in đậm, có đường kẻ), các cụm
    # trên là tên đơn vị quản lý trực tiếp. "Cụm" chứ không phải "dòng" — xem
    # `_gom_ten_dv_nhieu_dong`.
    gioi_han = next((i for i in range(n) if ma[i] in ("ten_loai", "so_ky_hieu",
                                                      "dia_danh_ngay")), min(n, 12))
    khoi_dv = [i for i in range(gioi_han)
               if ma[i] in ("noi_dung", "bang") and la_in_hoa(txt[i]) and _gon(txt[i])]
    if khoi_dv:
        cum = _gom_ten_dv_nhieu_dong(khoi_dv, txt)
        for nhom in cum:
            for i in nhom:
                ma[i] = "ten_dv_chu_quan"
        for i in cum[-1]:
            ma[i] = "ten_dv_ban_hanh"

    # ── Danh sách nơi nhận: mọi dòng sau "Nơi nhận:" tới hết khối ──
    for i in range(n):
        if ma[i] != "noi_nhan_tieu_de":
            continue
        for j in range(i + 1, n):
            t = _gon(txt[j])
            if not t:
                continue
            # Khối nơi nhận kết thúc ở dòng "Lưu: …" (Điều 15.4.b). Sau đó
            # thường chỉ còn ký hiệu người soạn thảo.
            if RE_GACH_DAU.match(t) or RE_LUU.match(t):
                ma[j] = "noi_nhan_ds"
                if RE_LUU.match(t):
                    break
            else:
                break

    # ── Người ký: chức danh in hoa + họ tên ngay dưới ──
    for i in range(n):
        if ma[i] in ("quoc_hieu", "ten_dv_ban_hanh", "ten_dv_chu_quan", "ten_loai"):
            continue
        if ma[i] not in ("noi_dung", "bang", "muc_la_ma", "khoan", "diem"):
            continue
        if not _la_chuc_danh(_gon(txt[i])):
            continue
        ma[i] = "quyen_han_chuc_vu"
        j = _ke_tiep(i)
        if j >= 0 and ma[j] in ("noi_dung", "bang") and _la_ten_rieng(_gon(txt[j])):
            ma[j] = "ho_ten_nguoi_ky"

    # ── Tiêu đề của phần / chương / mục: dòng in hoa ngay dưới "Chương I" ──
    for i in range(n):
        if ma[i] not in ("phan_chuong", "muc"):
            continue
        j = _ke_tiep(i)
        if j >= 0 and la_in_hoa(txt[j]) and ma[j] in ("noi_dung", "bang", "ten_loai"):
            ma[j] = "tieu_de_phan_chuong" if ma[i] == "phan_chuong" else "tieu_de_muc"

    # ── Tiêu đề của phụ lục ──
    for i in range(n):
        if ma[i] != "phu_luc_so":
            continue
        j = _ke_tiep(i)
        if j >= 0 and la_in_hoa(txt[j]):
            ma[j] = "tieu_de_phu_luc"

    # ── Ô bảng thuộc khối đầu văn bản ──
    # Khối Quốc hiệu / tên đơn vị hay được dựng bằng bảng hai cột, trong đó có
    # những ô không khớp thành phần nào (ô trống, dòng kẻ, chú thích). Chúng vẫn
    # phải được kéo giãn dòng và cách đoạn về 0 — bỏ sót thì khối đầu vẫn giãn xa
    # dù mọi đoạn nhận ra đều đã về 0. Chỉ xét phần TRƯỚC chỗ nội dung bắt đầu:
    # bảng số liệu giữa văn bản có cách trình bày riêng, không được đụng tới.
    het_khoi_dau = next(
        (i for i in range(n) if ma[i] in ("ten_loai", "trich_yeu", "kinh_gui",
                                          "kinh_gui_ds", "can_cu", "dieu",
                                          "phan_chuong", "muc", "muc_la_ma",
                                          "noi_nhan_tieu_de")),
        min(n, 20),
    )
    for i in range(het_khoi_dau):
        if ma[i] == "bang":
            ma[i] = "bang_the_thuc"

    # ── Khoản có tiêu đề: dòng ngắn không kết câu, đoạn sau là điểm/gạch đầu ──
    for i in range(n):
        if ma[i] != "khoan":
            continue
        t = _gon(txt[i])
        if len(t) > 80 or t.endswith((".", ";", ":", "!", "?")):
            continue
        j = _ke_tiep(i)
        if j >= 0 and (ma[j] == "diem" or RE_GACH_DAU.match(_gon(txt[j]))):
            ma[i] = "khoan_co_tieu_de"


def phan_loai(doan: list[tuple[str, bool]]) -> list[str]:
    """Trả mã thành phần thể thức cho từng đoạn.

    `doan` là danh sách `(text, nằm_trong_bảng)` theo đúng thứ tự xuất hiện
    trong file. Mã `trong` = đoạn rỗng, `bang` = ô bảng không thuộc thể thức
    nào (bước áp dụng chỉ sửa phông chữ cho nhóm này).
    """
    txt = [t for t, _ in doan]
    tb = [b for _, b in doan]
    ma = [_doan_doc_lap(t, b) for t, b in doan]
    _sua_theo_ngu_canh(ma, txt, tb)
    return ma
