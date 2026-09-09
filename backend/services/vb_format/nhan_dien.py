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
#
# "TRƯỞNG" để trần, không liệt kê từng chức danh ghép. Liệt kê thì danh sách
# không bao giờ đủ: gặp thật trên "Bao cao nghiem thu NPA.docx" là dòng
# "TRƯỞNG NHÓM" — có "TRƯỞNG PHÒNG", "TRƯỞNG BAN", "TRƯỞNG ĐƠN VỊ",
# "TRƯỞNG BỘ PHẬN" trong danh sách mà vẫn lọt, nên cả khối chữ ký không được
# áp thể thức. "TRƯỞNG" trần cũng nuốt luôn "KẾ TOÁN TRƯỞNG", "THỦ TRƯỞNG",
# "TỔ TRƯỞNG" mà không phải khai thêm dòng nào.
TU_KHOA_CHUC_DANH = (
    "GIÁM ĐỐC", "CHỦ TỊCH", "TRƯỞNG", "CHÁNH VĂN PHÒNG",
    "PHÓ", "QUYỀN", "HỘI ĐỒNG", "BAN KIỂM SOÁT",
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
# "Kính trình" là dạng của Tờ trình / Phiếu trình chuyển — Mẫu 16 Phụ lục V in
# đúng chữ "Kính trình:". Cùng vai thể thức với "Kính gửi", cùng cách trình bày.
RE_KINH_GUI    = re.compile(r"^Kính\s+(?:gửi|trình)\s*:?\s*(.*)$", re.I)
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


def _noi_dai_trich_yeu(ma: list[str], txt: list[str], i: int, ke_tiep,
                       ma_dich: str = "trich_yeu") -> None:
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
        ma[j] = ma_dich
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


# Chỉ xét gạch đầu dòng trong LỜI VĂN. Danh sách nơi nhận và Kính gửi cũng
# dùng "-" nhưng là danh sách phẳng, cỡ chữ riêng — đụng vào là hỏng khối cuối.
_MA_XET_CAP_GACH = frozenset({"noi_dung"})


def cap_gach_dau_dong(ma: list[str], txt: list[str]) -> list[int]:
    """Cấp của từng dòng gạch đầu dòng: 0 = không phải, 1 = cấp ngoài, 2 = mục con…

    QĐ 979 chỉ đánh số tới *điểm* (a, b, c); dưới đó không có cấp nào được khai,
    nên người soạn thể hiện mục con bằng mắt chứ không bằng cấu trúc. Đo trên
    "Bao cao nghiem thu NPA.docx": bốn mục con của "- 04 Mẫu biểu, bao gồm:"
    giống hệt dòng cha về mọi thứ đọc được — cùng dấu "-", cùng thụt dòng đầu
    1 cm, không lề trái, không danh sách tự động. Không có gì để đọc ra ngoài
    chính con chữ.

    ## Mở danh sách con: dòng kết thúc bằng dấu hai chấm

    "- 04 Mẫu biểu, bao gồm:" — dấu ":" cuối một dòng gạch đầu dòng là lời hứa
    "liệt kê ngay dưới đây".

    ## Đóng danh sách con: quy ước ";" … "." của chính văn bản

    Điều 15.4 đặt quy ước cho danh sách: **cuối mỗi dòng dấu chấm phẩy, dòng
    CUỐI CÙNG dấu chấm**. Không dùng dấu hiệu đóng thì danh sách con chạy tới
    tận dòng không-gạch-đầu-dòng đầu tiên, và trong chính file trên có ngay một
    ca sai:

        - Xây dựng phương pháp luận …:      ← mở danh sách con
        - Phương pháp xác định …;            ← con
        - Quy trình phê duyệt …;             ← con
        - Các mẫu biểu, báo cáo liên quan.   ← con CUỐI (dấu chấm)
        - Sản phẩm bàn giao: Tài liệu …      ← mục ngang cấp, KHÔNG phải con

    Thiếu quy tắc đóng thì dòng cuối bị tụt xuống làm mục con — đổi nghĩa văn bản.

    Chỉ đóng khi văn bản **đã chứng minh là có dùng quy ước**: trong cùng danh
    sách con đó phải có ít nhất một dòng kết thúc bằng ";". Người soạn chấm câu
    mọi dòng bằng "." thì dấu chấm không còn nói lên điều gì, và đóng theo nó là
    cắt danh sách ngay sau mục con đầu tiên.

    Dòng trống không ngắt danh sách; dòng không phải gạch đầu dòng thì ngắt hết.
    """
    cap = [0] * len(ma)
    hien = 0                    # cấp của danh sách đang mở, 0 = không ở trong danh sách nào
    co_cham_phay = False        # danh sách con hiện tại đã dùng quy ước ";" chưa
    for i, (m, t) in enumerate(zip(ma, txt)):
        s = _gon(t)
        if not s:
            continue
        if m not in _MA_XET_CAP_GACH or not RE_GACH_DAU.match(s):
            hien, co_cham_phay = 0, False
            continue
        if hien == 0:
            hien, co_cham_phay = 1, False
        cap[i] = hien
        if s.endswith(":"):
            hien += 1
            co_cham_phay = False
        elif hien > 1 and s.endswith(";"):
            co_cham_phay = True
        elif hien > 1 and s.endswith(".") and co_cham_phay:
            hien -= 1
            co_cham_phay = False
    return cap


def theo_dam_khoi_ten_dv(ma: list[str], dam: list[bool]) -> bool:
    """Chia lại khối tên đơn vị theo CHỮ ĐẬM tác giả đã đặt. Trả True nếu có đổi.

    Điều 8.2 cho hai vai và chỉ khác nhau đúng một thứ nhìn thấy được:
    tên đơn vị **ban hành** in đậm và có đường kẻ, tên đơn vị **quản lý trực
    tiếp** thì không. Cùng điều đó còn cho phép *"tên đơn vị ban hành văn bản,
    tên đơn vị quản lý trực tiếp dài có thể trình bày thành nhiều dòng"* — nên
    "dòng cuối là ban hành, các dòng trên là chủ quản" chỉ đúng khi mỗi vai vừa
    một dòng.

    Đoán bằng chữ (`_gom_ten_dv_nhieu_dong`) chỉ bắt được chỗ ngắt dòng có liên
    từ mở đầu. Gặp khối bốn dòng như:

        NGÂN HÀNG NÔNG NGHIỆP                 (thường)
        VÀ PHÁT TRIỂN NÔNG THÔN VIỆT NAM      (thường)
        BAN TRIỂN KHAI GP QLRR HOẠT ĐỘNG      (ĐẬM)
        TỔ TRIỂN KHAI NGHIỆP VỤ               (ĐẬM)

    thì "TỔ TRIỂN KHAI NGHIỆP VỤ" mở đầu bằng danh từ, không có dấu hiệu chữ
    nào nói nó thuộc cùng tên với dòng trên — và dòng "BAN…" bị bỏ đậm.

    Nhưng tác giả ĐÃ nói rồi: họ bôi đậm đúng những dòng thuộc tên đơn vị ban
    hành. Đó là dấu hiệu thật, do người viết đặt, chắc hơn mọi phép đoán trên
    con chữ. Hàm này đọc chính dấu hiệu đó.

    Hai hàng rào, thiếu cái nào cũng biến một tín hiệu tốt thành phép đoán:

    * **Phải có cả đậm lẫn không đậm.** Tác giả bôi đậm cả khối (hoặc không bôi
      dòng nào) nghĩa là họ không phân biệt hai vai — quay về đoán bằng chữ.
    * **Các dòng đậm phải nằm liền nhau ở CUỐI khối.** Điều 8.2 đặt tên đơn vị
      ban hành *"dưới tên đơn vị quản lý trực tiếp"*; đậm rải rác giữa khối là
      định dạng lỗi, không phải phân vai.
    """
    khoi = [i for i, m in enumerate(ma)
            if m in ("ten_dv_chu_quan", "ten_dv_ban_hanh")]
    if not khoi:
        return False
    d = [i for i in khoi if dam[i]]
    if not d or len(d) == len(khoi):
        return False
    if d != khoi[len(khoi) - len(d):]:
        return False

    cu = list(ma)
    for i in khoi:
        ma[i] = "ten_dv_chu_quan"
    for i in d:
        ma[i] = "ten_dv_ban_hanh"
    return ma != cu


# ── Lượt 2: sửa theo ngữ cảnh ────────────────────────────────────────────────
def _sua_theo_ngu_canh(ma: list[str], txt: list[str], trong_bang: list[bool],
                       nhom_bang: list[int | None] | None = None) -> None:
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

    # ── Trích yếu CÔNG VĂN xuống dòng ──
    # Công văn không có tên loại nên nhánh trên không với tới nó. Gặp thật:
    # "V/v Thông báo thay đổi tên/địa chỉ đăng ký" xuống dòng thành "trên hệ
    # thống SWIFT" — dòng dưới rơi vào `noi_dung` rồi bị áp cỡ 14, căn đều hai
    # bên, thụt dòng đầu 1 cm, trong khi dòng trên là cỡ 12 canh giữa. Hai nửa
    # của MỘT cụm từ ra hai kiểu chữ khác nhau, nhìn ra ngay là hỏng.
    #
    # Dùng chung hàm nối dài với trích yếu thường, nên cũng chung mọi hàng rào:
    # dừng khi dòng trên đã kết câu, khi đoạn sau đã có mã riêng (Kính gửi, Căn
    # cứ…), và nhiều nhất 2 dòng.
    for i in range(n):
        if ma[i] == "trich_yeu_cong_van":
            _noi_dai_trich_yeu(ma, txt, i, _ke_tiep, "trich_yeu_cong_van")

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
    # Quyền hạn chiếm được HAI dòng. Điều 13.2: ký thay thì dòng trên là hình
    # thức đề ký ("TL. TỔNG GIÁM ĐỐC"), dòng dưới là chức vụ của chính người
    # đặt bút ("GIÁM ĐỐC TRUNG TÂM THANH TOÁN"). Đo trên "TB Swift code Quảng
    # Ninh.docx": dòng thứ hai lọt qua `_la_ten_rieng` (5 từ, từ nào cũng mở
    # đầu bằng chữ hoa, không có số) nên bị nhận là HỌ TÊN, và họ tên thật
    # "Nguyễn Quốc Hùng" nằm dưới khoảng trống chừa chữ ký thì không còn ai
    # nhận — ở nguyên mã `bang`, không được áp thể thức nào.
    #
    # Xét `_la_chuc_danh` TRƯỚC `_la_ten_rieng`: một dòng khớp cả hai thì nó là
    # chức danh, vì không họ tên nào chứa "GIÁM ĐỐC" hay "TRƯỞNG".
    #
    # Chặn ở 2 dòng. Không chặn thì một khối in hoa nhiều dòng (danh sách đơn
    # vị chẳng hạn) bị nuốt trọn làm quyền hạn rồi ép căn giữa cả khối.
    for i in range(n):
        if ma[i] in ("quoc_hieu", "ten_dv_ban_hanh", "ten_dv_chu_quan", "ten_loai"):
            continue
        if ma[i] not in ("noi_dung", "bang", "muc_la_ma", "khoan", "diem"):
            continue
        if not _la_chuc_danh(_gon(txt[i])):
            continue
        ma[i] = "quyen_han_chuc_vu"
        j = _ke_tiep(i)
        for _ in range(2):
            if j < 0 or ma[j] not in ("noi_dung", "bang"):
                break
            if not _la_chuc_danh(_gon(txt[j])):
                break
            ma[j] = "quyen_han_chuc_vu"
            j = _ke_tiep(j)
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

    # ── Ô bảng nằm trong khối "Kính gửi / Kính trình" ──
    # Khối này hay được dựng bằng bảng cho dễ canh: một ô chứa "Kính trình:",
    # ô bên cạnh chứa tên người nhận. Ô thứ hai không khớp thành phần nào nên
    # rơi vào `bang` và GIỮ NGUYÊN cỡ chữ gốc — kết quả là nửa dòng cỡ 14, nửa
    # dòng cỡ 11, ngay giữa khối đầu văn bản.
    #
    # Điều 4.2 để cỡ chữ cho người soạn tự quyết là nói về BẢNG SỐ LIỆU. Bảng
    # dựng để canh chỗ cho một thành phần thể thức thì không phải bảng số liệu —
    # nó vẫn phải theo thể thức của thành phần đó (người dùng chốt 08/09/2026).
    #
    # Chỉ lan trong ĐÚNG cái bảng chứa dòng "Kính gửi / Kính trình" —
    # `nhom_bang` cho biết ô nào thuộc bảng nào. Lan theo "ô liền kề" thì hỏng:
    # ô vừa nâng lại thành điểm xuất phát mới, và một bảng số liệu dán sát ngay
    # sau bị kéo theo trọn vẹn. Đã thử, đúng là như vậy.
    #
    # `nhom_bang = None` (gọi `phan_loai` trực tiếp, không qua `chuan_hoa`) thì
    # BỎ QUA luật này — thà không sửa còn hơn đoán nhầm ranh giới bảng.
    if nhom_bang is not None:
        cua_khoi = {nhom_bang[i]: ma[i] for i in range(n)
                    if ma[i] in ("kinh_gui", "kinh_gui_ds")
                    and nhom_bang[i] is not None}
        for i in range(n):
            if ma[i] == "bang" and nhom_bang[i] in cua_khoi:
                ma[i] = cua_khoi[nhom_bang[i]]

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


def phan_loai(doan: list[tuple[str, bool]],
              nhom_bang: list[int | None] | None = None) -> list[str]:
    """Trả mã thành phần thể thức cho từng đoạn.

    `doan` là danh sách `(text, nằm_trong_bảng)` theo đúng thứ tự xuất hiện
    trong file. Mã `trong` = đoạn rỗng, `bang` = ô bảng không thuộc thể thức
    nào (bước áp dụng chỉ sửa phông chữ cho nhóm này).

    `nhom_bang` (từ `ap_dung.nhom_bang()`) nói mỗi đoạn thuộc BẢNG NÀO. Có nó
    thì những ô cùng bảng với dòng "Kính gửi / Kính trình" được kéo theo thể
    thức của khối đó; không có thì bỏ qua luật ấy chứ không đoán.
    """
    txt = [t for t, _ in doan]
    tb = [b for _, b in doan]
    ma = [_doan_doc_lap(t, b) for t, b in doan]
    _sua_theo_ngu_canh(ma, txt, tb, nhom_bang)
    return ma
