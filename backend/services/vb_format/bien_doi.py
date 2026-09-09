"""Sửa CON CHỮ trong một đoạn: viết hoa (Phụ lục IV) và đánh số, gạch đầu dòng.

## Vì sao trả về danh sách "sửa" chứ không trả chuỗi mới

Một đoạn trong Word không phải một chuỗi — nó là dãy *run*, mỗi run mang định
dạng riêng. Câu "Căn cứ **Quyết định số 600/QĐ-HĐTV**…" là ba run: thường, đậm,
thường. Nếu hàm này trả về một chuỗi mới rồi bên gọi ghi đè cả đoạn bằng một
run duy nhất thì phần in đậm giữa câu biến mất — người soạn mất công định dạng,
mà chẳng có lỗi nào báo.

Nên mỗi hàm ở đây trả `[(đầu, cuối, chữ_mới), …]` tính theo chỉ số trên chuỗi
ghép của cả đoạn. Bên gọi (`ap_dung.py`) chiếu từng khoảng đó về đúng run chứa
nó và chỉ đụng vào chỗ cần đụng.

## Ba cơ chế viết hoa — và vì sao không có cơ chế thứ tư

Phụ lục IV có 5 mục, phần lớn đòi hiểu ngữ nghĩa ("tên người", "tên địa lý",
"tên sự kiện lịch sử"). Máy không phân biệt được "cửa Lò" (cửa sông) với
"Cửa Lò" (địa danh) nếu không biết đang nói về cái gì. Ép máy đoán là **sửa sai
câu chữ của người soạn**, tệ hơn để nguyên.

Chỉ ba mục dưới đây là quyết định được bằng hình thức, nên chỉ làm ba:

1. `dau_cau`  — mục I: chữ đầu câu và đầu dòng. Có danh sách viết tắt chặn để
   "TP. hà nội" không bị hiểu là hết câu.
2. `vien_dan` — mục V.7: viện dẫn thì Phần/Chương/Mục/Tiểu mục/Điều viết hoa,
   còn khoản, điểm viết thường. Đây là luật thuần hình thức, không cần ngữ nghĩa.
3. `tu_dien`  — mục V.1 và IV.1: một danh sách cụm từ cố định do người dùng tự
   quản trong tab Cấu hình quy chuẩn. Máy không đoán, người dùng khai.
"""
import re

from .nhan_dien import CHU_CAI_DIEM, RE_GACH_DAU

Sua = tuple[int, int, str]

# Viết tắt kết thúc bằng dấu chấm nhưng KHÔNG kết thúc câu.
VIET_TAT = {
    "tp.", "đt.", "v.v.", "vv.", "tm.", "kt.", "tl.", "tuq.", "q.", "tr.",
    "st.", "no.", "nxb.", "gs.", "ts.", "ths.", "pgs.", "cn.", "p.", "đ/c.",
    "vd.", "vt.", "kg.", "stt.", "đc.",
}

# Ký hiệu mở đầu đoạn (gạch đầu dòng / số thứ tự / chữ cái điểm). Chữ đầu CÂU
# nằm ngay sau ký hiệu này, không phải ở vị trí 0.
RE_KY_HIEU_DAU = re.compile(
    rf"^\s*(?:[-–—‒‑•·*+]\s*"
    rf"|\d{{1,2}}\s*[.)/]\s*"
    rf"|[{CHU_CAI_DIEM}]{{1,2}}\s*[).]\s+"
    rf"|[IVXLCDM]+\s*[.)/]\s+)?"
)

RE_HET_CAU = re.compile(r"[.!?]\s+")
_RE_TU_TRUOC = re.compile(r"([^\s]+\.)\s+$")

# Viện dẫn (Phụ lục IV mục V.7)
_HOA_KHI_VIEN_DAN = ("phần", "chương", "tiểu mục", "mục", "điều")
_THUONG_KHI_VIEN_DAN = ("khoản", "điểm")
RE_VIEN_DAN_HOA = re.compile(
    r"\b(phần|chương|tiểu\s+mục|mục|điều)(\s+)(?=[IVXLCDM]+\b|\d)", re.I)
RE_VIEN_DAN_THUONG = re.compile(r"\b(Khoản|Điểm)(\s+)(?=\d|[a-zđêôơư]\b)")


# ── Viết hoa ─────────────────────────────────────────────────────────────────
def _vi_tri_dau_cau(txt: str) -> list[int]:
    """Chỉ số các ký tự phải viết hoa vì đứng đầu một câu hoàn chỉnh."""
    vi_tri: list[int] = []
    dau = RE_KY_HIEU_DAU.match(txt)
    if dau and dau.end() < len(txt):
        vi_tri.append(dau.end())
    for m in RE_HET_CAU.finditer(txt):
        truoc = txt[: m.start() + 1]
        # "…" và ".." không phải dấu kết câu mà là dấu lược
        if truoc.endswith("..") or truoc.endswith("…."):
            continue
        tu = _RE_TU_TRUOC.search(txt[: m.end()])
        if tu:
            t = tu.group(1).lower()
            # Viết tắt một chữ cái ("A. Nguyễn") hoặc trong danh sách chặn
            if t in VIET_TAT or len(t) == 2:
                continue
        if m.end() < len(txt):
            vi_tri.append(m.end())
    return vi_tri


# Chỉ những thành phần DƯỚI ĐÂY mới được áp luật viết hoa đầu câu.
# Phụ lục IV mục I nói "đầu một CÂU HOÀN CHỈNH". Trích yếu, tên đơn vị,
# Kính gửi, Nơi nhận, chức danh… không phải câu — chúng là cụm từ, và chỗ
# xuống dòng trong đó là để trình bày cho cân chứ không phải hết câu.
THANH_PHAN_LA_CAU = frozenset({
    "noi_dung", "khoan", "khoan_co_tieu_de", "diem", "can_cu", "dieu",
    "muc_la_ma", "trong",
})

_KET_CAU = (".", "!", "?", ";", ":", "\u2026")


def cho_phep_hoa_dau_doan(ma: str, txt_truoc: str | None) -> bool:
    """Đoạn này có được viết hoa chữ đầu không.

    Hai điều kiện, phải đủ cả hai:

    1. Thành phần đó là lời văn thật (`THANH_PHAN_LA_CAU`).
    2. Đoạn liền trước đã kết thúc (dấu chấm, chấm phẩy, hai chấm…). Nếu chưa
       thì đoạn này là phần TIẾP của câu trên, xuống dòng chỉ để trình bày.

    Gặp thật: ô trích yếu công văn "V/v Thông báo thay đổi tên/địa chỉ đăng ký"
    xuống dòng thành "trên hệ thống SWIFT" cho cân ô; luật viết hoa đầu dòng đã
    biến nó thành "Trên hệ thống SWIFT" — sai chính tả giữa một cụm từ.
    """
    if ma not in THANH_PHAN_LA_CAU:
        return False
    if txt_truoc is None:
        return True
    truoc = (txt_truoc or "").strip()
    return not truoc or truoc.endswith(_KET_CAU)


def viet_hoa_dau_cau(txt: str, cho_phep_dau_doan: bool = True) -> list[Sua]:
    vi_tri = _vi_tri_dau_cau(txt)
    if not cho_phep_dau_doan and vi_tri:
        dau = RE_KY_HIEU_DAU.match(txt)
        moc_dau_doan = dau.end() if dau else 0
        vi_tri = [i for i in vi_tri if i != moc_dau_doan]
    return [(i, i + 1, txt[i].upper()) for i in vi_tri if txt[i].islower()]


def viet_hoa_vien_dan(txt: str) -> list[Sua]:
    """Phần/Chương/Mục/Tiểu mục/Điều → hoa; khoản, điểm → thường (mục V.7)."""
    sua: list[Sua] = []
    dau_cau = set(_vi_tri_dau_cau(txt))
    for m in RE_VIEN_DAN_HOA.finditer(txt):
        c = m.group(1)[0]
        if c.islower():
            sua.append((m.start(1), m.start(1) + 1, c.upper()))
    for m in RE_VIEN_DAN_THUONG.finditer(txt):
        # Đầu câu thì phép đặt câu thắng: "Khoản 2 Điều 5 được sửa như sau:"
        if m.start(1) in dau_cau or m.start(1) == 0:
            continue
        sua.append((m.start(1), m.start(1) + 1, m.group(1)[0].lower()))
    return sua


def _regex_tu_dien(cum_tu: list[str]) -> re.Pattern | None:
    """Một biểu thức cho cả từ điển, cụm DÀI đứng trước cụm ngắn.

    Thứ tự quan trọng: "Ngân hàng Nhà nước" là khúc đầu của "Ngân hàng Nhà nước
    Việt Nam". Nếu cụm ngắn khớp trước thì cụm dài không bao giờ tới lượt, và
    hai chữ "Việt Nam" ở đuôi bị bỏ lại nguyên trạng viết sai.
    """
    sach = sorted({c.strip() for c in cum_tu if c and c.strip()},
                  key=len, reverse=True)
    if not sach:
        return None
    return re.compile(
        r"(?<![\wÀ-ỹ])(" + "|".join(re.escape(c) for c in sach) + r")(?![\wÀ-ỹ])",
        re.I,
    )


class TuDien:
    """Từ điển cụm từ đã biên dịch: biểu thức tìm + bảng tra dạng chuẩn.

    Gói chung một chỗ thay vì trả hai giá trị rời — biểu thức và bảng tra phải
    dựng từ CÙNG một danh sách, tách ra là sớm muộn có chỗ gọi lệch nhau.
    """

    __slots__ = ("mau", "chuan")

    def __init__(self, cum_tu: list[str]):
        self.mau = _regex_tu_dien(cum_tu)
        self.chuan = {c.strip().lower(): c.strip() for c in cum_tu if c and c.strip()}


def viet_hoa_tu_dien(txt: str, td: "TuDien | None") -> list[Sua]:
    """Sửa hoa/thường của các cụm từ trong từ điển về đúng dạng đã khai.

    Bỏ qua đoạn khớp đang viết HOA TOÀN BỘ: đó là tên đơn vị trên đầu văn bản
    ("NGÂN HÀNG NÔNG NGHIỆP VÀ PHÁT TRIỂN NÔNG THÔN VIỆT NAM") — quy định bắt
    in hoa cả dòng, hạ xuống dạng từ điển là làm sai đúng chỗ quy định bắt đúng.
    """
    if td is None or td.mau is None:
        return []
    sua: list[Sua] = []
    for m in td.mau.finditer(txt):
        goc = m.group(1)
        if goc.isupper():
            continue
        chuan = td.chuan.get(goc.lower())
        if chuan and chuan != goc:
            sua.append((m.start(1), m.end(1), chuan))
    return sua


# ── Đánh số và gạch đầu dòng ─────────────────────────────────────────────────
RE_SO_DAU = re.compile(r"^(\d{1,2})\s*([.)/])\s*")
RE_CHU_DAU = re.compile(rf"^([{CHU_CAI_DIEM}]{{1,2}})\s*([).\/])\s+")
RE_LA_MA_DAU = re.compile(r"^([IVXLCDM]+)\s*([.)/])\s+")


def chuan_danh_so(txt: str, ma: str, cfg: dict,
                  ky_tu_gach: str | None = None) -> list[Sua]:
    """Chuẩn hoá ký hiệu mở đầu đoạn: gạch đầu dòng, "1.", "a)", "I.".

    `ky_tu_gach` ghi đè ký tự gạch đầu dòng cho riêng đoạn này — mục con dùng
    ký tự khác cấp ngoài (xem `nhan_dien.cap_gach_dau_dong`).

    `ma` là mã thành phần thể thức — vài thành phần phải MIỄN vì ký hiệu đầu
    dòng của chúng không phải số thứ tự: "Số: 05/NHNo-TCKT" mà đem chuẩn hoá
    theo luật khoản sẽ thành "Số. 05…"; danh sách nơi nhận thì gạch đầu dòng
    vốn đã đúng và cỡ chữ 11 khác hẳn lời văn.
    """
    if ma in ("so_ky_hieu", "dia_danh_ngay", "ky_hieu_nguoi_soan",
              "quoc_hieu", "tieu_ngu", "ten_dv_chu_quan", "ten_dv_ban_hanh",
              "bang", "trong"):
        return []

    # ── Gạch đầu dòng ──
    if cfg.get("gach_dau_dong"):
        m = RE_GACH_DAU.match(txt)
        if m:
            chuan = f"{ky_tu_gach or cfg.get('ky_tu_gach', '-')} "
            if m.group(0) != chuan and len(txt) > m.end():
                return [(0, m.end(), chuan)]
            return []

    # ── Số thứ tự khoản: "1)" "1/" "1 ." → "1." ──
    if cfg.get("chuan_khoan_diem"):
        m = RE_SO_DAU.match(txt)
        if m and ma in ("khoan", "khoan_co_tieu_de", "noi_dung"):
            chuan = f"{m.group(1)}. "
            if m.group(0) != chuan and len(txt) > m.end():
                return [(0, m.end(), chuan)]
            return []

        # ── Chữ cái điểm: "a." "a/" → "a)" ──
        # "v.v. các nội dung…" mở đầu bằng "v." nhưng không phải điểm — chặn riêng.
        if not txt[:4].lower().startswith("v.v"):
            m = RE_CHU_DAU.match(txt)
            if m and ma in ("diem", "noi_dung"):
                chuan = f"{m.group(1)}) "
                if m.group(0) != chuan and len(txt) > m.end():
                    return [(0, m.end(), chuan)]
                return []

    # ── Mục La Mã: "I)" "I/" → "I." ──
    if cfg.get("chuan_muc_la_ma") and ma == "muc_la_ma":
        m = RE_LA_MA_DAU.match(txt)
        if m:
            chuan = f"{m.group(1)}. "
            if m.group(0) != chuan and len(txt) > m.end():
                return [(0, m.end(), chuan)]
    return []


# ── Tiêu ngữ ─────────────────────────────────────────────────────────────────
# Điều 7.2: "chữ cái đầu của các cụm từ được viết hoa, giữa các cụm từ có gạch
# nối (-), có cách chữ". Gạch NỐI, không phải gạch ngang dài.
RE_GACH_NGANG = re.compile(r"\s*[\u2010-\u2015\u2212-]\s*")


def _hoa_thuong_tieu_ngu(s: str) -> str:
    """Mỗi cụm từ: chữ cái đầu viết hoa, phần còn lại viết thường.

    Điều 7.2 nói thẳng "chữ cái đầu của CÁC CỤM TỪ được viết hoa" — Tiêu ngữ có
    đúng một dạng đúng, không phải chuyện thẩm mỹ để mỗi nơi làm một kiểu. Gặp
    thật trên "TB Swift code Quảng Ninh.docx": "Độc lập - Tự do - Hạnh Phúc",
    chữ P hoa giữa cụm.

    Không đụng khi số cụm khác 3: lúc đó chuỗi không còn là Tiêu ngữ chuẩn nữa
    (dính thêm chữ, thiếu một cụm) và viết hoa lại theo công thức là đoán mò.
    `.lower()` giữ nguyên dấu tiếng Việt nên "Hoà" / "Hòa" không bị đổi kiểu bỏ dấu.
    """
    phan = s.split(" - ")
    if len(phan) != 3:
        return s
    ket_qua = []
    for cum in phan:
        cum = cum.lower()
        for i, c in enumerate(cum):
            if c.isalpha():
                cum = cum[:i] + c.upper() + cum[i + 1:]
                break
        ket_qua.append(cum)
    return " - ".join(ket_qua)


def chuan_tieu_ngu(txt: str) -> list[Sua]:
    """Đưa Tiêu ngữ về đúng dạng "Độc lập - Tự do - Hạnh phúc".

    Người soạn hay gõ gạch ngang dài (– —) hoặc chèn thêm dấu cách hai bên cho
    dòng Tiêu ngữ dài bằng dòng Quốc hiệu phía trên. Nhìn thì cân, nhưng đó là
    kéo giãn bằng dấu cách — đổi cỡ chữ hay đổi lề một cái là lệch ngay, và
    không đúng thứ Điều 7.2 mô tả.

    Sửa dấu nối, dấu cách và hoa/thường chữ cái đầu mỗi cụm — cả ba đều được
    Điều 7.2 nói thẳng. KHÔNG đụng tới cách bỏ dấu tiếng Việt ("Hòa" hay "Hoà"):
    đó là thói quen của từng đơn vị, quy định không nói gì.
    """
    goc = txt.strip()
    if not goc:
        return []
    moi = RE_GACH_NGANG.sub(" - ", goc)
    moi = re.sub(r"[ \t\u00a0]+", " ", moi).strip()
    moi = _hoa_thuong_tieu_ngu(moi)
    if moi == goc:
        return []
    dau = len(txt) - len(txt.lstrip())
    return [(dau, dau + len(goc), moi)]


# ── Quyền hạn người ký ───────────────────────────────────────────────────────
# Điều 13: hình thức đề ký viết tắt kèm dấu chấm ("TM.", "KT.", "TL.", "TUQ.",
# "Q."), rồi tới chức vụ. Mọi mẫu ở Phụ lục V đều có dấu cách sau dấu chấm.
RE_TIEN_TO_QUYEN_HAN = re.compile(r"^(TM|KT|TL|TUQ|Q)\.(?=[^\s.])")


def chuan_tien_to_quyen_han(txt: str) -> list[Sua]:
    """Thêm dấu cách sau "TL." "KT." "TM." "TUQ." "Q." khi bị gõ dính.

    Gặp thật: "TL.TỔNG GIÁM ĐỐC". Gõ dính không sai chính tả nên không ai để ý,
    nhưng nó khác mẫu và khác mọi văn bản khác trong cùng tập hồ sơ.

    Chỉ nhận tiền tố viết HOA đứng đầu dòng. Chữ thường ("tl.") thì đó là câu
    lời văn chứ không phải khối chữ ký.
    """
    m = RE_TIEN_TO_QUYEN_HAN.match(txt or "")
    if not m:
        return []
    return [(0, m.end(), m.group(0) + " ")]


# ── Thụt đầu dòng gõ tay ─────────────────────────────────────────────────────
RE_THUT_THU_CONG = re.compile(r"^[\t\u00a0 ]+")


def bo_thut_thu_cong(txt: str) -> list[Sua]:
    """Bỏ tab / dấu cách người soạn gõ ở ĐẦU đoạn để thụt dòng.

    Chỉ gọi cho thành phần mà quy chuẩn có khai `thut_cm` — tức là phần mềm
    đang tự đặt mức thụt dòng đầu cho đoạn đó. Lúc ấy tab gõ tay không còn là
    cách thụt lề nữa mà là khoảng trống CỘNG THÊM: đo trên "TB Swift code Quảng
    Ninh.docx", đoạn mở đầu bằng tab ra bản chuẩn hoá với thụt dòng đầu 1 cm mà
    tab vẫn nằm đó — dòng ấy thụt gấp đôi mọi dòng khác, nhìn ra ngay là hỏng
    mà không có lỗi nào báo.

    Chỉ bỏ khoảng trắng ở ĐẦU. Tab giữa dòng là người soạn canh cột
    ("- Swift Code<tab><tab> : VBAAVNVX330") — bỏ đi là phá cách trình bày của họ.
    """
    m = RE_THUT_THU_CONG.match(txt or "")
    if not m or not (txt or "").strip():
        return []
    return [(0, m.end(), "")]


# ── Cụm từ không tách dòng ───────────────────────────────────────────────────
KHONG_NGAT = " "


def ghep_lien_dong(txt: str, mau: re.Pattern | None) -> list[Sua]:
    """Thay dấu cách bên trong cụm từ bằng dấu cách KHÔNG NGẮT.

    Word chỉ xuống dòng ở dấu cách thường. Đổi sang U+00A0 là cả cụm dính liền
    nhau trong mọi trường hợp — không phụ thuộc bề rộng trang hay cỡ chữ, nên
    không vỡ ra khi người dùng đổi lề sau này.
    """
    if mau is None:
        return []
    sua: list[Sua] = []
    for m in mau.finditer(txt):
        goc = m.group(1)
        moi = re.sub(r"[ \t]+", KHONG_NGAT, goc)
        if moi != goc:
            sua.append((m.start(1), m.end(1), moi))
    return sua


def regex_lien_dong(cum_tu: list[str]) -> re.Pattern | None:
    """Cụm từ liền dòng — khớp cả bản đã có dấu cách không ngắt để không sửa lại."""
    sach = sorted({c.strip() for c in cum_tu if c and c.strip()},
                  key=len, reverse=True)
    if not sach:
        return None
    mau = "|".join(re.escape(c).replace(r"\ ", r"[  ]") for c in sach)
    # `re.I` vì cùng một cụm xuất hiện ở hai dạng: "Việt Nam" trong lời văn và
    # "VIỆT NAM" trong dòng tên đơn vị in hoa — cả hai đều không được tách đôi.
    # `ghep_lien_dong()` chỉ thay dấu cách, không đụng tới chữ, nên khớp không
    # phân biệt hoa thường là an toàn.
    return re.compile(r"(?<![\wÀ-ỹ])(" + mau + r")(?![\wÀ-ỹ])", re.I)
