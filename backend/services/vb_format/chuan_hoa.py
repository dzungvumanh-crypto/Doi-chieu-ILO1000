"""Điều phối một lượt chuẩn hoá: đọc .docx → sửa → trả .docx mới + nhật ký.

## Vì sao chia làm hai lượt sửa chữ

Lượt 1 sửa hoa/thường và đánh số. Lượt 2 mới ghép cụm từ liền dòng, và tính
lại trên chữ ĐÃ sửa của lượt 1.

Gộp một lượt thì hai luật giẫm chân nhau ở đúng chỗ hay gặp nhất: "tổng giám
đốc" vừa nằm trong từ điển viết hoa vừa nằm trong danh sách cụm từ liền dòng.
Cả hai cùng đòi ghi vào một khoảng ký tự, chỉ một cái được ghi, cái còn lại rơi
mất — mà rơi cái nào thì tuỳ thứ tự trong danh sách, tức là không đoán được.

## Vì sao không bôi màu những sửa đổi áp cho cả văn bản

Giãn dòng, cách đoạn, phông chữ, thụt dòng đầu gần như luôn phải sửa ở **mọi**
đoạn — văn bản soạn bằng mặc định của Word không đoạn nào đúng. Bôi màu hết thì
cả trang vàng khè và người kiểm tra không còn chỗ nào để nhìn. Những sửa đổi
đó vào phần "Sửa chung cho cả văn bản" của nhật ký; màu chỉ dành cho chỗ khác
biệt riêng của từng đoạn (cỡ chữ, đậm/nghiêng, căn lề) và cho chữ bị sửa.
"""
import io
import logging

from docx import Document
from docx.shared import Cm

from . import ap_dung, bien_doi, do_chu, duong_ke, nhan_dien, quy_chuan

_log = logging.getLogger(__name__)

# Thành phần thể thức PHẢI nằm gọn một dòng. Lời văn không có trong danh sách:
# xuống dòng là chuyện bình thường của nó, nén lại chỉ làm chữ dính vô cớ.
_MOT_DONG = frozenset({
    "quoc_hieu", "tieu_ngu", "ten_dv_chu_quan", "ten_dv_ban_hanh",
    "so_ky_hieu", "dia_danh_ngay", "ten_loai", "quyen_han_chuc_vu",
    "ho_ten_nguoi_ky", "phu_luc_so",
})

def _gon_mot_dong(txt: str, gioi_han: int = 46) -> str:
    t = " ".join((txt or "").split())
    return t if len(t) <= gioi_han else t[:gioi_han] + "…"


def _loc_chong_lan(sua: list[tuple[int, int, str]]) -> list[tuple[int, int, str]]:
    """Bỏ những khoảng sửa đè lên khoảng đã nhận trước đó.

    Hai luật khác nhau cùng đòi ghi vào một khoảng ký tự thì chỉ luật đứng
    trước được ghi. Không lọc thì `ap_sua_text()` ghi chồng: khoảng sau ghi đè
    lên chữ mới của khoảng trước, kết quả là một chuỗi lai không giống cả hai.
    """
    ket_qua: list[tuple[int, int, str]] = []
    da_chiem: list[tuple[int, int]] = []
    for dau, cuoi, moi in sua:
        if any(dau < c and d < cuoi for d, c in da_chiem):
            continue
        ket_qua.append((dau, cuoi, moi))
        da_chiem.append((dau, cuoi))
    return ket_qua


def _sua_chu(p, ma: str, tp: dict, cfg: dict, tu_dien,
             txt_truoc: str | None, ky_tu_gach: str | None = None) -> set[int]:
    """Lượt 1 — ép hoa/thường, chuẩn đánh số, viết hoa. Trả chỉ số run đã sửa."""
    txt = p.text
    if not txt.strip():
        return set()

    som: set[int] = set()

    # Thụt đầu dòng gõ bằng tab: chỉ bỏ khi quy chuẩn TỰ ĐẶT mức thụt cho thành
    # phần này (`thut_cm`), vì lúc đó tab thành khoảng trống cộng thêm và dòng
    # bị thụt gấp đôi. Chạy đầu tiên để mọi luật sau đọc chuỗi đã sạch đầu dòng.
    if tp.get("thut_cm") is not None:
        som = ap_dung.ap_sua_text(p, bien_doi.bo_thut_thu_cong(txt))
        if som:
            txt = p.text

    # Tiêu ngữ có luật riêng về dấu nối, dấu cách và hoa/thường (Điều 7.2),
    # không liên quan tới nhóm dưới nên chạy trước và độc lập.
    if ma == "tieu_ngu" and cfg["chung"].get("chuan_tieu_ngu"):
        da_sua = ap_dung.ap_sua_text(p, bien_doi.chuan_tieu_ngu(txt))
        if da_sua:
            return som | da_sua

    # Dấu cách sau tiền tố đề ký ("TL.TỔNG GIÁM ĐỐC"). Phải nằm TRƯỚC nhánh ép
    # in hoa bên dưới: `quyen_han_chuc_vu` khai `hoa="hoa"`, mà nhánh đó thoát
    # hàm ngay nên mọi luật sửa chữ đặt sau nó không bao giờ chạy tới.
    if ma == "quyen_han_chuc_vu":
        them = ap_dung.ap_sua_text(p, bien_doi.chuan_tien_to_quyen_han(txt))
        if them:
            som |= them
            txt = p.text

    # Ép in hoa cả đoạn thì mọi luật viết hoa khác thành vô nghĩa: kết quả đằng
    # nào cũng là chữ hoa. Chạy riêng, không trộn với nhóm dưới.
    if tp.get("hoa"):
        return som | ap_dung._ep_hoa_thuong(p, tp["hoa"])

    sua: list[tuple[int, int, str]] = []
    sua += bien_doi.chuan_danh_so(txt, ma, cfg["danh_so"], ky_tu_gach)
    vh = cfg["viet_hoa"]
    if vh.get("vien_dan"):
        sua += bien_doi.viet_hoa_vien_dan(txt)
    if vh.get("tu_dien"):
        sua += bien_doi.viet_hoa_tu_dien(txt, tu_dien)
    if vh.get("dau_cau"):
        sua += bien_doi.viet_hoa_dau_cau(
            txt, bien_doi.cho_phep_hoa_dau_doan(ma, txt_truoc))
    return som | ap_dung.ap_sua_text(p, _loc_chong_lan(sua))


def chuan_hoa(du_lieu: bytes, cau_hinh: dict | None = None) -> tuple[bytes, dict]:
    """Chuẩn hoá một file .docx theo quy chuẩn.

    Trả `(bytes file kết quả, báo cáo)`. Báo cáo gồm:
      `sua_chung`  danh sách sửa đổi áp cho cả văn bản (lề trang, giãn dòng…)
      `doan`       từng đoạn đã sửa: vị trí, thành phần thể thức, trích dẫn, việc đã làm
      `luu_y`      những chỗ CỐ Ý không đụng tới, kèm lý do
      `thong_ke`   số đoạn đọc được / số đoạn đã sửa
    """
    cfg = quy_chuan.hop_nhat(cau_hinh)
    doc = Document(io.BytesIO(du_lieu))

    dd = cfg["danh_dau"]
    bat_mau = bool(dd.get("bat"))
    tu_dien = bien_doi.TuDien(cfg["viet_hoa"].get("cum_tu") or [])
    mau_lien_dong = (bien_doi.regex_lien_dong(cfg["lien_dong"].get("cum_tu") or [])
                     if cfg["lien_dong"].get("ap_dung") else None)

    sua_chung = ap_dung.dat_trang(doc, cfg["trang"])

    # Gỡ ngắt trang TRƯỚC khi lấy danh sách đoạn: việc này xoá bớt đoạn, mà
    # `ma_list` lại khớp với `khoi` theo đúng thứ tự chỉ số. Gỡ sau là hai
    # danh sách lệch nhau một nhịp và mọi đoạn sau đó bị áp nhầm thể thức.
    so_ngat = (ap_dung.bo_ngat_trang_thu_cong(doc)
               if cfg["chung"].get("bo_ngat_trang_thu_cong") else 0)
    if so_ngat:
        sua_chung.append(f"bỏ {so_ngat} ngắt trang thủ công")

    khoi = ap_dung.duyet_doan(doc)

    # Đổi danh sách chấm tròn tự động thành gạch đầu dòng gõ tay TRƯỚC khi phân
    # loại: dấu chấm tròn không nằm trong `p.text` nên bộ nhận diện không thấy
    # gạch đầu dòng nào, và cả khối Nơi nhận / Kính gửi dựng bằng danh sách tự
    # động sẽ trượt khỏi mọi luật nhận khối. Xem `ap_dung.go_bullet_tu_dong`.
    bullet_da_doi: set[int] = (
        ap_dung.go_bullet_tu_dong(doc, khoi, cfg["danh_so"].get("ky_tu_gach", "-"))
        if cfg["danh_so"].get("bo_bullet_tu_dong") else set())

    ma_list = nhan_dien.phan_loai([(p.text, tb) for p, tb in khoi],
                                  ap_dung.nhom_bang(doc, khoi))
    # Chia lại khối tên đơn vị theo chữ đậm tác giả đã đặt — phải làm TRƯỚC khi
    # `_dinh_dang_doan` ép đậm/thường theo mã, vì lúc đó tín hiệu gốc mất sạch.
    nhan_dien.theo_dam_khoi_ten_dv(
        ma_list,
        [bool(p.runs) and bool(ap_dung._hieu_luc_run(p.runs[0], p, "bold"))
         for p, _ in khoi],
    )

    cap_gach = (nhan_dien.cap_gach_dau_dong(ma_list, [p.text for p, _ in khoi])
                if cfg["chung"].get("phan_cap_gach_dau_dong")
                else [0] * len(ma_list))

    nhat_ky: list[dict] = []
    luu_y: list[str] = []
    if so_ngat:
        luu_y.append(
            f"Đã gỡ {so_ngat} chỗ ngắt trang do người soạn đặt tay. Chúng được "
            "đặt theo bố cục cũ, mà chuẩn hoá làm chữ cao lên (giãn dòng 1,2, "
            "lề trên 20 mm) nên giữ lại thì hay đẻ ra một trang gần như trống. "
            "Văn bản thật sự cần sang trang mới — Phụ lục ban hành kèm theo "
            "Quyết định chẳng hạn — thì tắt ô «Bỏ ngắt trang thủ công» trong "
            "tab Cấu hình rồi chạy lại."
        )
    so_doan_sua = 0
    da_canh_bao_so_tu_dong = False
    da_canh_bao_tran = False
    # Đoạn CÓ CHỮ liền trước — dùng để biết đoạn hiện tại có mở đầu một câu
    # mới hay chỉ là phần xuống dòng của câu trên (xem `cho_phep_hoa_dau_doan`).
    txt_truoc: str | None = None

    for stt, ((p, _tb), ma) in enumerate(zip(khoi, ma_list), start=1):
        if ma == "trong":
            continue
        txt_hien_tai = p.text
        if dd.get("xoa_danh_dau_cu"):
            ap_dung._xoa_danh_dau(p)

        tp = cfg["thanh_phan"].get(ma, {})
        viec: list[str] = []

        # ── Danh sách tự động của Word ──
        # Loại chấm tròn đã đổi ở lượt trước vòng lặp; ở đây chỉ ghi nhật ký.
        if stt - 1 in bullet_da_doi:
            viec.append("chuyển dấu chấm tròn tự động thành gạch đầu dòng")
        kieu = ap_dung._kieu_danh_so(doc, p)
        if kieu == "so" and not cfg["danh_so"].get("bo_so_tu_dong"):
            if not da_canh_bao_so_tu_dong:
                luu_y.append(
                    "Văn bản có danh sách ĐÁNH SỐ tự động của Word. Số hiển thị do "
                    "Word tự tính nên không đọc ra được để chuẩn hoá — phần mềm giữ "
                    "nguyên. Muốn đúng quy định thì gõ số thẳng vào dòng (1. 2. 3. "
                    "hoặc a) b) c)) rồi tắt đánh số tự động."
                )
                da_canh_bao_so_tu_dong = True

        # ── Lượt 1: sửa chữ ──
        cap = cap_gach[stt - 1]
        run_noi_dung = _sua_chu(
            p, ma, tp, cfg, tu_dien, txt_truoc,
            cfg["danh_so"].get("ky_tu_gach_cap2", "+") if cap >= 2 else None)
        if run_noi_dung:
            viec.append("sửa chữ (viết hoa / đánh số / gạch đầu dòng)")

        # ── Lượt 2: ghép cụm từ liền dòng, tính trên chữ đã sửa ở lượt 1 ──
        run_lien_dong: set[int] = set()
        if mau_lien_dong is not None:
            gd = bien_doi.ghep_lien_dong(p.text, mau_lien_dong)
            run_lien_dong = ap_dung.ap_sua_text(p, gd)
            if run_lien_dong:
                viec.append("ghép cụm từ không cho tách dòng")

        # ── Định dạng ──
        dinh_dang = ap_dung._dinh_dang_doan(p, ma, tp, cfg["chung"])
        rieng = [mo_ta for loai, mo_ta in dinh_dang if loai == "rieng"]
        for loai, mo_ta in dinh_dang:
            if loai == "chung":
                if mo_ta not in sua_chung:
                    sua_chung.append(mo_ta)
            else:
                viec.append(mo_ta)

        # ── Thụt lề mục con ──
        # Chỉ thụt khi đoạn chưa có lề trái. Tác giả đã tự thụt thì `_dinh_dang_doan`
        # giữ nguyên mức của họ, ép lại theo mức mình tính là sửa một thứ đang đúng.
        if cap >= 2 and not p.paragraph_format.left_indent:
            p.paragraph_format.left_indent = Cm(
                (cap - 1) * float(cfg["chung"].get("thut_muc_con_cm") or 1.0))
            viec.append(f"thụt lề mục con (cấp {cap})")

        # ── Nén cho vừa một dòng ──
        # Chạy SAU khi áp cỡ chữ: nén bao nhiêu phụ thuộc cỡ chữ cuối cùng,
        # tính trước là tính trên con số sắp bị thay.
        if ma in _MOT_DONG and cfg["chung"].get("nen_chu_cho_vua_dong"):
            co = tp.get("co") or (
                lambda v: v.pt if v is not None else None)(
                    ap_dung._hieu_luc_run(p.runs[0], p, "size") if p.runs else None)
            if co:
                da_nen, con_tran = do_chu.nen_cho_vua_dong(
                    p, doc, co,
                    dam=bool(tp.get("dam")), nghieng=bool(tp.get("nghieng")),
                    tran_twip=int(cfg["chung"].get("nen_toi_da_twip") or 24),
                )
                if da_nen:
                    viec.append("nén chữ cho vừa một dòng")
                elif con_tran and not da_canh_bao_tran:
                    luu_y.append(
                        f"Dòng «{_gon_mot_dong(p.text)}» dài hơn chỗ trống của nó, "
                        "nén hết mức cho phép vẫn không vừa nên phần mềm giữ nguyên "
                        "— Word sẽ đẩy phần cuối xuống dòng dưới. Cách xử lý: nới "
                        "cột chứa nó, hoặc tự tách thành hai dòng ở chỗ hợp lý "
                        "(Điều 8.2 cho phép tên đơn vị dài trình bày nhiều dòng)."
                    )
                    da_canh_bao_tran = True

        # ── Đường kẻ ngang dưới dòng thể thức ──
        # Sau bước nén: độ dài vạch tính theo bề rộng chữ, mà bề rộng đó chỉ
        # chốt khi cỡ chữ và mức nén đã xong.
        # Cụm nhiều dòng (trích yếu dài, tên đơn vị dài) chỉ được MỘT vạch, ở
        # dưới dòng CUỐI. Không kiểm thì trích yếu hai dòng có một vạch chen
        # vào giữa hai dòng — nhìn ra ngay là hỏng.
        ma_ke = next((m for m in ma_list[stt:] if m != "trong"), None)
        if ma in duong_ke.TY_LE and ma_ke != ma:
            if cfg["chung"].get("go_gach_chan_the_thuc") and duong_ke.go_gach_chan(p):
                viec.append("bỏ gạch chân / viền đoạn (quy định dùng đường kẻ ngang rời)")
            if cfg["chung"].get("ve_duong_ke_ngang"):
                co_ve = tp.get("co") or (
                    lambda v: v.pt if v is not None else None)(
                        ap_dung._hieu_luc_run(p.runs[0], p, "size") if p.runs else None)
                if co_ve and duong_ke.ve_duong_ke(
                        p, ma, co_ve, dam=bool(tp.get("dam")),
                        nghieng=bool(tp.get("nghieng"))):
                    viec.append("vẽ đường kẻ ngang bên dưới")

        # ── Đánh dấu: cụ thể đè lên tổng quát ──
        if bat_mau and (rieng or run_noi_dung or run_lien_dong):
            if rieng:
                ap_dung._to_mau(p, None, dd.get("mau_dinh_dang", "YELLOW"))
            if run_noi_dung:
                ap_dung._to_mau(p, run_noi_dung, dd.get("mau_noi_dung", "BRIGHT_GREEN"))
            if run_lien_dong:
                ap_dung._to_mau(p, run_lien_dong, dd.get("mau_lien_dong", "TURQUOISE"))

        txt_truoc = txt_hien_tai

        if viec:
            so_doan_sua += 1
            nhat_ky.append({
                "stt": stt,
                "ma": ma,
                "nhan": quy_chuan.NHAN_THANH_PHAN.get(ma, "Ô bảng" if ma == "bang" else ma),
                "trich": (p.text or "")[:90],
                "viec": viec,
            })

    ra = io.BytesIO()
    doc.save(ra)
    return ra.getvalue(), {
        "sua_chung": sua_chung,
        "doan": nhat_ky,
        "luu_y": luu_y,
        "thong_ke": {
            "tong_doan": sum(1 for m in ma_list if m != "trong"),
            "doan_da_sua": so_doan_sua,
        },
    }
