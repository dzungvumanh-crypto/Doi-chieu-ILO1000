"""Chuẩn hoá văn bản theo QĐ 979 — nhận diện thể thức, sửa chữ, đánh dấu.

Văn bản mẫu trong `_van_ban_sai()` được dựng cố ý sai đủ kiểu hay gặp: phông
Arial, cỡ 11, lề mặc định của Word, gạch đầu dòng bằng "•", khoản đánh "1)",
điểm đánh "a.", danh sách nơi nhận cùng cỡ chữ với lời văn. Test khẳng định
đúng những gì phần mềm HỨA sẽ sửa — và cũng khẳng định vài thứ nó hứa KHÔNG
đụng tới.
"""
import io
import pathlib
import zipfile

import pytest
from docx import Document
from docx.shared import Mm, Pt

from backend.services.vb_format import (
    ap_dung, bien_doi, do_chu, duong_ke, nhan_dien, quy_chuan,
)
from backend.services.vb_format.chuan_hoa import chuan_hoa


# ── Dựng văn bản mẫu ─────────────────────────────────────────────────────────
def _van_ban_sai() -> bytes:
    doc = Document()
    s = doc.sections[0]
    s.left_margin = s.right_margin = Mm(25)
    s.top_margin = s.bottom_margin = Mm(25)
    style = doc.styles["Normal"]
    style.font.name = "Arial"
    style.font.size = Pt(11)

    for dong in [
        "NGÂN HÀNG NÔNG NGHIỆP VÀ PHÁT TRIỂN NÔNG THÔN VIỆT NAM",
        "CHI NHÁNH HÀ NỘI",
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
        "Độc lập - Tự do - Hạnh phúc",
        "Số: 05/QĐ-NHNo.HN-KTNQ",
        "Hà Nội, ngày 05 tháng 01 năm 2026",
        "QUYẾT ĐỊNH",
        "Về việc điều động cán bộ",
        "Căn cứ Quy chế số 616/QC-HĐTV-PC ngày 30/9/2022 của Hội đồng thành viên;",
        "Điều 1. Phạm vi điều chỉnh",
        "1) Quy định này áp dụng cho toàn hệ thống. quyết định có hiệu lực từ ngày ký.",
        "a. Các đơn vị tại trụ sở chính thực hiện theo khoản 2 điều 5 của quy chế.",
        "• Phòng Kế toán Ngân quỹ chịu trách nhiệm thi hành.",
        "Điều 2. Trách nhiệm thi hành",
        "2) nhà nước giao Tổng Giám đốc tổ chức thực hiện.",
        "Nơi nhận:",
        "- Như trên;",
        "- Ban kiểm soát;",
        "- Lưu: VT, PC.",
        "GIÁM ĐỐC",
        "Nguyễn Văn A",
    ]:
        doc.add_paragraph(dong)

    ra = io.BytesIO()
    doc.save(ra)
    return ra.getvalue()


@pytest.fixture(scope="module")
def ket_qua():
    du_lieu, bao_cao = chuan_hoa(_van_ban_sai())
    doc = Document(io.BytesIO(du_lieu))
    doan = ap_dung.duyet_doan(doc)
    return doc, [p for p, _ in doan], bao_cao


def _tim(dsach, mo_dau: str):
    for p in dsach:
        if p.text.strip().startswith(mo_dau):
            return p
    raise AssertionError(f"Không tìm thấy đoạn bắt đầu bằng {mo_dau!r}")


# ── Nhận diện thành phần thể thức ────────────────────────────────────────────
def test_nhan_dien_du_thanh_phan_the_thuc():
    doc = Document(io.BytesIO(_van_ban_sai()))
    khoi = ap_dung.duyet_doan(doc)
    ma = nhan_dien.phan_loai([(p.text, tb) for p, tb in khoi])
    theo_text = {p.text.strip(): m for (p, _), m in zip(khoi, ma)}

    assert theo_text["CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM"] == "quoc_hieu"
    assert theo_text["Độc lập - Tự do - Hạnh phúc"] == "tieu_ngu"
    assert theo_text["CHI NHÁNH HÀ NỘI"] == "ten_dv_ban_hanh"
    assert theo_text["NGÂN HÀNG NÔNG NGHIỆP VÀ PHÁT TRIỂN NÔNG THÔN VIỆT NAM"] == "ten_dv_chu_quan"
    assert theo_text["Số: 05/QĐ-NHNo.HN-KTNQ"] == "so_ky_hieu"
    assert theo_text["Hà Nội, ngày 05 tháng 01 năm 2026"] == "dia_danh_ngay"
    assert theo_text["QUYẾT ĐỊNH"] == "ten_loai"
    assert theo_text["Về việc điều động cán bộ"] == "trich_yeu"
    assert theo_text["Căn cứ Quy chế số 616/QC-HĐTV-PC ngày 30/9/2022 của Hội đồng thành viên;"] == "can_cu"
    assert theo_text["Điều 1. Phạm vi điều chỉnh"] == "dieu"
    assert theo_text["Nơi nhận:"] == "noi_nhan_tieu_de"
    assert theo_text["- Như trên;"] == "noi_nhan_ds"
    assert theo_text["- Lưu: VT, PC."] == "noi_nhan_ds"
    assert theo_text["GIÁM ĐỐC"] == "quyen_han_chuc_vu"
    assert theo_text["Nguyễn Văn A"] == "ho_ten_nguoi_ky"


def test_quoc_hieu_trong_cau_van_khong_bi_nham():
    """Câu NÓI VỀ Quốc hiệu không được nhận là Quốc hiệu rồi bị ép in hoa."""
    cau = '1. Quốc hiệu “CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM”: được trình bày bằng chữ in hoa.'
    ma = nhan_dien.phan_loai([(cau, False)])
    assert ma[0] != "quoc_hieu"


def test_la_in_hoa_nhan_dung_chu_hoa_co_dau():
    # "QUY ĐỊNH CHUNG" chứa "Ị" (U+1ECA) — từng bị dải [ạ-ỹ] hiểu là chữ thường
    assert nhan_dien.la_in_hoa("QUY ĐỊNH CHUNG")
    assert nhan_dien.la_in_hoa("TỔNG GIÁM ĐỐC")
    assert not nhan_dien.la_in_hoa("Quy định chung")


# ── Định dạng ────────────────────────────────────────────────────────────────
def test_le_trang_ve_dung_quy_dinh(ket_qua):
    doc, _, _ = ket_qua
    s = doc.sections[0]
    assert round(s.left_margin.mm) == 30
    assert round(s.right_margin.mm) == 20
    assert round(s.top_margin.mm) == 20
    assert round(s.bottom_margin.mm) == 20


def test_phong_chu_va_co_chu_theo_thanh_phan(ket_qua):
    _, doan, _ = ket_qua
    quoc_hieu = _tim(doan, "CỘNG HÒA")
    assert quoc_hieu.runs[0].font.name == "Times New Roman"
    # 12 chứ không phải 13: đếm trên cả 18 mẫu Phụ lục V thì Quốc hiệu là cỡ 12
    # ở 17 mẫu. Dải Phụ lục III ghi "12 - 13" — lấy cận trên làm dòng tên đơn vị
    # dài tràn cột và đẩy chữ "NAM" xuống một dòng riêng.
    assert quoc_hieu.runs[0].font.size.pt == 12
    assert _tim(doan, "CHI NHÁNH HÀ NỘI").runs[0].font.size.pt == 12

    # Danh sách nơi nhận cỡ 11, từ "Nơi nhận:" cỡ 12 nghiêng đậm (Điều 15.4.b).
    # Đọc cỡ chữ ĐANG CÓ HIỆU LỰC chứ không đọc `run.font.size`: văn bản mẫu đặt
    # style Normal 11pt, mà quy chuẩn cũng đòi 11 — đúng rồi thì phần mềm KHÔNG ghi đè,
    # nên trên run không có giá trị nào cả. Đó chính là hành vi mong muốn.
    o_noi_nhan = _tim(doan, "- Như trên")
    assert ap_dung._hieu_luc_run(o_noi_nhan.runs[0], o_noi_nhan, "size").pt == 11
    tieu_de = _tim(doan, "Nơi nhận:")
    assert tieu_de.runs[0].font.size.pt == 12
    assert tieu_de.runs[0].font.italic is True
    assert tieu_de.runs[0].font.bold is True

    # Lời văn cỡ 14
    assert _tim(doan, "Điều 1.").runs[0].font.size.pt == 14


def test_phong_chu_dat_ca_nhanh_complex_script(ket_qua):
    """Chữ tiếng Việt có dấu hay rơi vào nhánh w:cs — bỏ sót là hai kiểu chữ
    trên cùng một dòng khi mở ở máy khác."""
    from docx.oxml.ns import qn
    _, doan, _ = ket_qua
    r = _tim(doan, "Điều 1.").runs[0]
    rFonts = r._element.rPr.rFonts
    for thuoc in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        assert rFonts.get(qn(thuoc)) == "Times New Roman"


# ── Sửa chữ ──────────────────────────────────────────────────────────────────
def test_chuan_hoa_danh_so_va_gach_dau_dong(ket_qua):
    _, doan, _ = ket_qua
    chu = [p.text.strip() for p in doan]
    assert any(t.startswith("1. Quy định này") for t in chu), "khoản «1)» phải thành «1.»"
    assert any(t.startswith("a) Các đơn vị") for t in chu), "điểm «a.» phải thành «a)»"
    assert any(t.startswith("- Phòng Kế toán") for t in chu), "«•» phải thành «- »"


def test_viet_hoa_dau_cau_va_tu_dien(ket_qua):
    _, doan, _ = ket_qua
    chu = "\n".join(p.text for p in doan)
    assert "Quyết định có hiệu lực" in chu          # sau dấu chấm → viết hoa
    assert "2. Nhà nước giao" in chu                 # đầu dòng + từ điển "Nhà nước"
    assert "Ban Kiểm soát" in chu                    # từ điển


def test_vien_dan_dieu_khoan_diem(ket_qua):
    _, doan, _ = ket_qua
    chu = "\n".join(p.text for p in doan)
    # Phụ lục IV mục V.7: Điều viết hoa, khoản viết thường
    assert "khoản 2 Điều 5" in chu


def test_ten_don_vi_giu_nguyen_in_hoa(ket_qua):
    """Từ điển có "Ngân hàng Nông nghiệp…" nhưng dòng tên đơn vị đang IN HOA
    toàn bộ — hạ nó xuống dạng từ điển là làm sai đúng chỗ quy định bắt đúng."""
    _, doan, _ = ket_qua
    assert _tim(doan, "NGÂN HÀNG").text.strip() == (
        "NGÂN HÀNG NÔNG NGHIỆP VÀ PHÁT TRIỂN NÔNG THÔN VIỆT\u00a0NAM"), \
        "chỉ dấu cách giữa VIỆT và NAM được đổi thành dấu cách không ngắt"


def test_cum_tu_lien_dong_dung_dau_cach_khong_ngat(ket_qua):
    """Cụm chức danh phải dính liền bằng dấu cách KHÔNG NGẮT (U+00A0).

    Viết hẳn \\u00a0 chứ không dán ký tự thật vào chuỗi: dấu cách
    không ngắt nhìn y hệt dấu cách thường trên màn hình, dán thật thì người
    đọc test không biết nó đang kiểm tra cái gì, mà sửa nhầm một ký tự là
    test vẫn xanh.
    """
    _, doan, _ = ket_qua
    chu = "\n".join(p.text for p in doan)
    assert "Tổng\u00a0Giám\u00a0đốc" in chu
    assert "Tổng Giám đốc" not in chu, "dấu cách thường phải được thay hết"


# ── Đánh dấu ─────────────────────────────────────────────────────────────────
def test_co_danh_dau_va_dung_ba_mau(ket_qua):
    _, doan, _ = ket_qua
    mau = {str(r.font.highlight_color) for p in doan for r in p.runs
           if r.font.highlight_color is not None}
    assert mau, "phải có vùng được đánh dấu"
    assert any("YELLOW" in m for m in mau)
    assert any("BRIGHT_GREEN" in m for m in mau)


def test_tat_danh_dau_thi_khong_boi_mau():
    du_lieu, _ = chuan_hoa(_van_ban_sai(), {"danh_dau": {"bat": False}})
    doc = Document(io.BytesIO(du_lieu))
    assert not [r for p, _ in ap_dung.duyet_doan(doc) for r in p.runs
                if r.font.highlight_color is not None]


# ── Báo cáo ──────────────────────────────────────────────────────────────────
def test_bao_cao_co_thong_ke_va_nhat_ky(ket_qua):
    _, _, bc = ket_qua
    assert bc["thong_ke"]["tong_doan"] == 21
    assert 0 < bc["thong_ke"]["doan_da_sua"] <= 21
    assert any("lề trái" in m for m in bc["sua_chung"])
    assert any("phông chữ" in m for m in bc["sua_chung"])
    assert all({"stt", "ma", "nhan", "trich", "viec"} <= set(d) for d in bc["doan"])


def test_gia_tri_chung_vao_sua_chung_khong_lap_o_tung_doan(ket_qua):
    """Giãn dòng / cách đoạn CỦA LỜI VĂN nằm ở «sửa chung», không lặp từng đoạn.

    Khối thể thức đầu và cuối trang thì ngược lại: chúng khai giãn dòng riêng
    (dòng đơn, 0pt) nên phải hiện ở đúng đoạn đó và được bôi màu — đó là khác
    biệt của riêng đoạn, không phải luật áp cho cả văn bản.
    """
    _, _, bc = ket_qua
    moi_viec = [v for d in bc["doan"] for v in d["viec"]]

    assert "giãn dòng → 1,2" in bc["sua_chung"]
    assert "cách đoạn → 6 pt" in bc["sua_chung"]
    assert "giãn dòng → 1,2" not in moi_viec
    assert "cách đoạn → 6 pt" not in moi_viec
    assert not [v for v in moi_viec if v.startswith("phông chữ")]


def test_khoi_the_thuc_dau_trang_dung_dong_don_khong_cach_doan(ket_qua):
    """Điều 7.3 / 8.2: Quốc hiệu, Tiêu ngữ, tên đơn vị cách nhau DÒNG ĐƠN.

    Ép 1,2 và 6pt cho cả khối này là lỗi đã gặp: Tiêu ngữ bị đẩy xa Quốc hiệu,
    khối đầu trang cao gấp đôi mẫu Phụ lục V.
    """
    def _cach_doan(p) -> float:
        # Đọc giá trị ĐANG CÓ HIỆU LỰC: đúng sẵn thì phần mềm không ghi đè, khi
        # đó `paragraph_format.space_after` là None chứ không phải 0.
        v = ap_dung._hieu_luc_doan(p, "space_after")
        return 0.0 if v is None else v.pt

    _, doan, _ = ket_qua
    for mo_dau in ("CỘNG HÒA", "Độc lập", "CHI NHÁNH HÀ NỘI", "Số:", "QUYẾT ĐỊNH"):
        p = _tim(doan, mo_dau)
        assert ap_dung._hieu_luc_doan(p, "line_spacing") == 1.0, mo_dau
        assert _cach_doan(p) == 0, mo_dau

    # Lời văn vẫn theo giá trị chung
    p = _tim(doan, "Điều 1.")
    assert ap_dung._hieu_luc_doan(p, "line_spacing") == 1.2
    assert _cach_doan(p) == 6


# ── Giữ nguyên định dạng bên trong đoạn ──────────────────────────────────────
def test_sua_chu_khong_lam_mat_dinh_dang_giua_cau():
    """Sửa một chỗ trong câu không được xoá phần in đậm ở chỗ khác của cùng câu."""
    doc = Document()
    p = doc.add_paragraph()
    p.add_run("Căn cứ ")
    r_dam = p.add_run("Quyết định số 600/QĐ-HĐTV")
    r_dam.bold = True
    p.add_run(" của hội đồng thành viên. quyết định này có hiệu lực.")
    ra = io.BytesIO()
    doc.save(ra)

    du_lieu, _ = chuan_hoa(ra.getvalue())
    lai = Document(io.BytesIO(du_lieu))
    doan = lai.paragraphs[0]
    assert "Quyết định này có hiệu lực" in doan.text        # đã sửa viết hoa đầu câu
    assert any(r.bold and "600/QĐ-HĐTV" in r.text for r in doan.runs), \
        "phần in đậm giữa câu phải còn nguyên"


def test_ap_sua_text_vat_qua_nhieu_run():
    doc = Document()
    p = doc.add_paragraph()
    p.add_run("nhà ")
    p.add_run("nước")
    p.add_run(" giao.")
    ap_dung.ap_sua_text(p, [(0, 8, "Nhà nước")])
    assert p.text == "Nhà nước giao."


# ── Cấu hình ─────────────────────────────────────────────────────────────────
def test_hop_nhat_giu_mac_dinh_cho_khoa_thieu():
    cfg = quy_chuan.hop_nhat({"thanh_phan": {"noi_dung": {"co": 13}}})
    assert cfg["thanh_phan"]["noi_dung"]["co"] == 13
    assert cfg["thanh_phan"]["noi_dung"]["can"] == "justify"      # khoá không khai
    assert cfg["chung"]["phong_chu"] == "Times New Roman"          # cả nhóm không khai


def test_hop_nhat_bo_qua_khoa_la():
    cfg = quy_chuan.hop_nhat({"khong_ton_tai": {"a": 1}})
    assert "khong_ton_tai" not in cfg


def test_mac_dinh_tra_ban_sao_doc_lap():
    a = quy_chuan.mac_dinh()
    a["chung"]["phong_chu"] = "Arial"
    assert quy_chuan.mac_dinh()["chung"]["phong_chu"] == "Times New Roman"


def test_cau_hinh_co_chu_duoc_ton_trong():
    du_lieu, _ = chuan_hoa(_van_ban_sai(), {"thanh_phan": {"noi_dung": {"co": 13}}})
    doc = Document(io.BytesIO(du_lieu))
    doan = [p for p, _ in ap_dung.duyet_doan(doc)]
    assert _tim(doan, "- Phòng Kế toán").runs[0].font.size.pt == 13


# ── Viết tắt không bị hiểu là hết câu ────────────────────────────────────────
@pytest.mark.parametrize("cau, mong_doi", [
    ("Trụ sở tại TP. hà nội.", "Trụ sở tại TP. hà nội."),
    ("Gồm sổ sách, chứng từ v.v. các tài liệu khác.", "Gồm sổ sách, chứng từ v.v. các tài liệu khác."),
    ("Đơn vị thực hiện. đơn vị báo cáo.", "Đơn vị thực hiện. Đơn vị báo cáo."),
])
def test_viet_hoa_dau_cau_bo_qua_viet_tat(cau, mong_doi):
    sua = bien_doi.viet_hoa_dau_cau(cau)
    ra = cau
    for dau, cuoi, moi in sorted(sua, reverse=True):
        ra = ra[:dau] + moi + ra[cuoi:]
    assert ra == mong_doi


def test_danh_so_khong_dung_vao_so_ky_hieu():
    """«Số: 05/QĐ-…» mà đem chuẩn hoá theo luật khoản sẽ thành «Số. 05/QĐ-…»."""
    assert bien_doi.chuan_danh_so("Số: 05/QĐ-NHNo-PC", "so_ky_hieu",
                                  quy_chuan.mac_dinh()["danh_so"]) == []


# ── Danh sách tự động của Word ───────────────────────────────────────────────
def _van_ban_co_danh_sach() -> bytes:
    doc = Document()
    doc.add_paragraph("Điều 1. Trách nhiệm thi hành")
    doc.add_paragraph("Phòng Kế toán thực hiện.", style="List Bullet")
    doc.add_paragraph("Bước một", style="List Number")
    ra = io.BytesIO()
    doc.save(ra)
    return ra.getvalue()


def test_nhan_ra_danh_sach_tu_dong_khai_bao_tren_STYLE():
    """python-docx và nút style của Word đặt w:numPr trên STYLE, không trên đoạn.
    Chỉ đọc trên đoạn là bỏ sót, mà bỏ sót thì im lặng — không lỗi nào báo."""
    doc = Document(io.BytesIO(_van_ban_co_danh_sach()))
    kieu = {p.text: ap_dung._kieu_danh_so(doc, p) for p, _ in ap_dung.duyet_doan(doc)}
    assert kieu["Phòng Kế toán thực hiện."] == "bullet"
    assert kieu["Bước một"] == "so"
    assert kieu["Điều 1. Trách nhiệm thi hành"] is None


def test_bullet_tu_dong_thanh_gach_dau_dong_con_danh_so_thi_canh_bao():
    du_lieu, bao_cao = chuan_hoa(_van_ban_co_danh_sach())
    doan = [p for p, _ in ap_dung.duyet_doan(Document(io.BytesIO(du_lieu)))]
    chu = [p.text.strip() for p in doan]

    assert "- Phòng Kế toán thực hiện." in chu
    # Đổi style về Normal, KHÔNG xoá numPr của style dùng chung
    assert _tim(doan, "- Phòng Kế toán").style.name == "Normal"
    # Danh sách ĐÁNH SỐ giữ nguyên + có cảnh báo nói rõ vì sao
    assert "Bước một" in chu
    assert any("ĐÁNH SỐ tự động" in w for w in bao_cao["luu_y"])


# ── Tên loại ngoài danh sách Điều 3, ngày tháng để trống, Tiêu ngữ ──────────
def _de_cuong() -> bytes:
    """Khối đầu một đề cương kiểm tra — dựng theo đúng file người dùng gửi."""
    doc = Document()
    for t in [
        "NGÂN HÀNG NÔNG NGHIỆP",
        "VÀ PHÁT TRIỂN NÔNG THÔN VIỆT NAM",
        "TRUNG TÂM THANH TOÁN",
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
        "Độc lập %s Tự do %s Hạnh phúc" % ("–", "–"),
        "Số:……../TTTT-KSNB",
        "Hà Nội, ngày      tháng      năm 2026",
        "ĐỀ CƯƠNG",
        "KIỂM TRA HOẠT ĐỘNG TẠI TRUNG TÂM THANH TOÁN",
        "I. MỤC ĐÍCH, YÊU CẦU",
    ]:
        doc.add_paragraph(t)
    ra = io.BytesIO()
    doc.save(ra)
    return ra.getvalue()


def _ma_theo_text(du_lieu: bytes) -> dict:
    doc = Document(io.BytesIO(du_lieu))
    khoi = ap_dung.duyet_doan(doc)
    ma = nhan_dien.phan_loai([(p.text, tb) for p, tb in khoi])
    return {p.text.strip(): m for (p, _), m in zip(khoi, ma)}


def test_ten_loai_ngoai_danh_sach_dieu_3_van_duoc_nhan():
    """Điều 3.2.aa cho phép "các loại văn bản… khác phù hợp với thực tiễn" nên
    danh sách tên loại không bao giờ đủ. "ĐỀ CƯƠNG" từng bị xếp thành lời văn
    rồi bị căn đều hai bên thay vì canh giữa."""
    ma = _ma_theo_text(_de_cuong())
    assert ma["ĐỀ CƯƠNG"] == "ten_loai"
    assert ma["KIỂM TRA HOẠT ĐỘNG TẠI TRUNG TÂM THANH TOÁN"] == "trich_yeu"

    doan = [p for p, _ in ap_dung.duyet_doan(Document(io.BytesIO(chuan_hoa(_de_cuong())[0])))]
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    assert _tim(doan, "ĐỀ CƯƠNG").paragraph_format.alignment == WD_ALIGN_PARAGRAPH.CENTER


def test_ngay_thang_de_trong_van_la_dia_danh_ngay():
    """Dự thảo trình ký và mọi mẫu Phụ lục V đều ghi "ngày  tháng  năm 2026"."""
    ma = _ma_theo_text(_de_cuong())
    assert ma["Hà Nội, ngày      tháng      năm 2026"] == "dia_danh_ngay"


def test_cau_vien_dan_ngay_thang_khong_bi_nham_la_dia_danh():
    cau = ("Căn cứ Quyết định số 05/QĐ-NHNo ngày 05 tháng 01 năm 2026 của "
           "Tổng Giám đốc về việc ban hành quy chế;")
    assert nhan_dien.phan_loai([(cau, False)])[0] == "can_cu"


def test_chuan_hoa_tieu_ngu_ve_dung_gach_noi_mot_dau_cach():
    """Điều 7.2: giữa các cụm từ có gạch NỐI (-), có cách chữ."""
    for goc in ("Độc lập – Tự do – Hạnh phúc",
                "Độc lập — Tự  do — Hạnh phúc",
                "Độc  lập  -  Tự do  -  Hạnh phúc"):
        sua = bien_doi.chuan_tieu_ngu(goc)
        ra = goc
        for dau, cuoi, moi in sorted(sua, reverse=True):
            ra = ra[:dau] + moi + ra[cuoi:]
        assert ra == "Độc lập - Tự do - Hạnh phúc", goc
    # Đúng rồi thì không sửa — không bôi màu một đoạn không đổi gì
    assert bien_doi.chuan_tieu_ngu("Độc lập - Tự do - Hạnh phúc") == []


def test_tieu_ngu_trong_van_ban_that_duoc_chuan_hoa():
    doan = [p for p, _ in ap_dung.duyet_doan(Document(io.BytesIO(chuan_hoa(_de_cuong())[0])))]
    assert _tim(doan, "Độc lập").text.strip() == "Độc lập - Tự do - Hạnh phúc"


def test_gian_dong_mac_dinh_la_1_2_theo_van_ban_979():
    """1,5 là cận TRÊN của dải Điều 12.6; lời văn của chính QĐ 979 dùng 1,2."""
    assert quy_chuan.mac_dinh()["chung"]["gian_dong"] == 1.2


# ── Công văn: khối đầu dựng bằng bảng, Kính gửi, ngắt dòng thẩm mỹ ───────────
def _cong_van() -> bytes:
    """Dựng theo đúng file người dùng gửi: khối đầu là bảng hai cột, mọi đoạn
    đặt Spacing Before 7pt / After 7pt."""
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name = "Times New Roman"
    st.font.size = Pt(13)

    t = doc.add_table(rows=1, cols=2)
    trai, phai = t.rows[0].cells
    trai.text = ""
    phai.text = ""
    for o, dong in (
        (trai, ["NGÂN HÀNG NÔNG NGHIỆP",
                "VÀ PHÁT TRIỂN NÔNG THÔN VIỆT NAM",
                "Số:            /NHNo-TTTT",
                "V/v Thông báo thay đổi tên/địa chỉ đăng ký",
                "trên hệ thống SWIFT"]),
        (phai, ["CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM",
                "Độc lập - Tự do - Hạnh phúc",
                "Hà Nội, ngày 28 tháng 8 năm 2026"]),
    ):
        for txt in dong:
            p = o.add_paragraph(txt)
            p.paragraph_format.space_before = Pt(7)
            p.paragraph_format.space_after = Pt(7)

    for txt in ["Kính gửi: Giám đốc Agribank Quảng Ninh",
                "Ngày 20/8/2026, Trung tâm Thanh toán nhận được công văn.",
                "Trân trọng./."]:
        p = doc.add_paragraph(txt)
        p.paragraph_format.space_before = Pt(7)
        p.paragraph_format.space_after = Pt(7)

    ra = io.BytesIO()
    doc.save(ra)
    return ra.getvalue()


@pytest.fixture(scope="module")
def cong_van():
    du_lieu, bao_cao = chuan_hoa(_cong_van())
    doan = [p for p, _ in ap_dung.duyet_doan(Document(io.BytesIO(du_lieu)))]
    return doan, bao_cao


def test_ten_nuoc_khong_bi_tach_lam_hai_dong(cong_van):
    """Gặp thật: dòng tên đơn vị bị ngắt thành "…NÔNG THÔN VIỆT" rồi "NAM" nằm
    một mình ở dòng thứ ba."""
    doan, _ = cong_van
    assert _tim(doan, "VÀ PHÁT TRIỂN").text.strip().endswith("VIỆT NAM")
    assert _tim(doan, "CỘNG HO").text.strip().endswith("VIỆT NAM")


def test_co_chu_khoi_dau_theo_dung_mau_979(cong_van):
    """Quốc hiệu và tên đơn vị cỡ 12 (đếm trên 18 mẫu Phụ lục V), trích yếu
    công văn cỡ 12, số ký hiệu 13, Tiêu ngữ 13."""
    doan, _ = cong_van

    def co(mo_dau: str) -> float:
        # Đọc cỡ ĐANG CÓ HIỆU LỰC: đúng sẵn thì phần mềm không ghi đè lên run
        p = _tim(doan, mo_dau)
        return ap_dung._hieu_luc_run(p.runs[0], p, "size").pt
    assert co("CỘNG HO") == 12
    assert co("NGÂN HÀNG") == 12
    assert co("VÀ PHÁT TRIỂN") == 12
    assert co("V/v") == 12
    assert co("Số:") == 13
    assert co("Độc lập") == 13


def test_kinh_gui_mot_noi_thi_canh_giua(cong_van):
    """Điều 15.4.a: gửi MỘT nơi thì "Kính gửi" và tên đơn vị trên cùng một
    dòng — mẫu 06 và 09 của Phụ lục V canh giữa dòng đó."""
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    doan, _ = cong_van
    assert _tim(doan, "Kính gửi").paragraph_format.alignment == WD_ALIGN_PARAGRAPH.CENTER


def test_kinh_gui_nhieu_noi_thi_sat_trai():
    """Chỉ có chữ "Kính gửi:" rồi liệt kê xuống dòng → canh giữa là sai."""
    ma = nhan_dien.phan_loai([("Kính gửi:", False)])
    assert ma[0] == "kinh_gui_ds"
    assert nhan_dien.phan_loai([("Kính gửi: Ngân hàng Nhà nước Việt Nam", False)])[0] \
        == "kinh_gui"


def test_khoi_dau_ve_spacing_0_0_ke_ca_o_bang_khong_nhan_ra(cong_van):
    """Ô bảng không khớp thành phần nào VẪN phải về 0/0 — bỏ sót thì khối đầu
    vẫn giãn dù mọi đoạn nhận ra đều đã về 0."""
    doan, _ = cong_van

    def _sp(p):
        tr = ap_dung._hieu_luc_doan(p, "space_before")
        sa = ap_dung._hieu_luc_doan(p, "space_after")
        return (0.0 if tr is None else tr.pt, 0.0 if sa is None else sa.pt)

    for mo_dau in ("NGÂN HÀNG", "CỘNG HO", "Độc lập", "Số:", "V/v",
                   "trên hệ thống", "Hà Nội,", "Kính gửi"):
        assert _sp(_tim(doan, mo_dau)) == (0.0, 0.0), mo_dau


def test_loi_van_bo_khoang_truoc_giu_khoang_sau(cong_van):
    """Khoảng cách giữa hai đoạn = after của đoạn trên + before của đoạn dưới.
    7+7 cho ra 14pt mà hộp Paragraph chỉ hiện hai số 7 — đưa before về 0 để
    chỉ còn một nguồn. `after` giữ nguyên 7 vì Điều 12.6 chỉ nêu mức tối thiểu
    6pt, hạ xuống là sửa thứ không sai."""
    doan, _ = cong_van
    p = _tim(doan, "Ngày 20/8/2026")
    assert ap_dung._hieu_luc_doan(p, "space_before").pt == 0
    assert ap_dung._hieu_luc_doan(p, "space_after").pt == 7


def test_xuong_dong_tham_my_khong_bi_viet_hoa(cong_van):
    """Ô trích yếu xuống dòng cho cân ô, không phải hết câu — "trên hệ thống
    SWIFT" phải giữ chữ thường."""
    doan, _ = cong_van
    assert _tim(doan, "trên hệ thống").text.strip().startswith("trên")


def test_van_viet_hoa_khi_doan_truoc_da_ket_cau():
    """Ngược lại: đoạn trước kết thúc bằng dấu chấm thì đây là câu mới."""
    assert bien_doi.cho_phep_hoa_dau_doan("noi_dung", "Đơn vị thực hiện.")
    assert not bien_doi.cho_phep_hoa_dau_doan("noi_dung", "V/v Thông báo thay đổi")
    # Thành phần không phải lời văn thì không bao giờ áp luật viết hoa đầu dòng
    assert not bien_doi.cho_phep_hoa_dau_doan("trich_yeu_cong_van", "Đơn vị thực hiện.")
    assert not bien_doi.cho_phep_hoa_dau_doan("noi_nhan_ds", None)


# ── Trích yếu nhiều dòng, nén chữ, đường kẻ ngang ────────────────────────────
def _bao_cao(o_rong_dxa: int | None = None) -> bytes:
    """Báo cáo có trích yếu HAI dòng — dòng trên kết thúc bằng dấu phẩy."""
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name = "Times New Roman"
    st.font.size = Pt(13)

    dong_dau = ["NGÂN HÀNG NÔNG NGHIỆP", "VÀ PHÁT TRIỂN NÔNG THÔN VIỆT NAM",
                "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", "Độc lập - Tự do - Hạnh phúc",
                "Số:   /BC-TTTT", "Hà Nội, ngày   tháng   năm 2026"]
    if o_rong_dxa:
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn as _qn
        t = doc.add_table(rows=1, cols=1)
        o = t.rows[0].cells[0]
        o.text = ""
        tcPr = o._tc.get_or_add_tcPr()
        cu = tcPr.find(_qn("w:tcW"))
        if cu is not None:
            tcPr.remove(cu)
        w = OxmlElement("w:tcW")
        w.set(_qn("w:w"), str(o_rong_dxa))
        w.set(_qn("w:type"), "dxa")
        tcPr.append(w)
        for x in dong_dau:
            o.add_paragraph(x)
    else:
        for x in dong_dau:
            doc.add_paragraph(x)

    doc.add_paragraph("BÁO CÁO")
    p = doc.add_paragraph("Về kết quả xây dựng phương pháp luận thực hiện Quản lý sản phẩm mới,")
    p.runs[0].bold = True
    p2 = doc.add_paragraph("hoạt động trong thị trường mới (NPA)")
    p2.runs[0].italic = True
    doc.add_paragraph("Căn cứ Quyết định số 05/QĐ-NHNo ngày 01/9/2026;")
    ra = io.BytesIO()
    doc.save(ra)
    return ra.getvalue()


def test_trich_yeu_hai_dong_dong_bo_format_va_canh_giua():
    """Trích yếu dài xuống dòng cho cân — dòng dưới KHÔNG phải lời văn.

    Nhận mỗi dòng đầu thì dòng thứ hai rơi vào `noi_dung`: căn đều hai bên
    trong khi dòng trên căn giữa, lại không được in đậm theo.
    """
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    du_lieu, _ = chuan_hoa(_bao_cao())
    doan = [p for p, _ in ap_dung.duyet_doan(Document(io.BytesIO(du_lieu)))]

    for mo_dau in ("Về kết quả", "hoạt động trong thị trường"):
        p = _tim(doan, mo_dau)
        assert p.paragraph_format.alignment == WD_ALIGN_PARAGRAPH.CENTER, mo_dau
        # Đọc giá trị ĐANG CÓ HIỆU LỰC: dòng trên vốn đã đậm và không nghiêng
        # nên phần mềm không ghi đè, `run.font.*` là None chứ không phải False.
        assert ap_dung._hieu_luc_run(p.runs[0], p, "bold") is True, mo_dau
        assert not ap_dung._hieu_luc_run(p.runs[0], p, "italic"), mo_dau

    # Không được nuốt sang phần sau
    ma = _ma_theo_text(_bao_cao())
    assert ma["Căn cứ Quyết định số 05/QĐ-NHNo ngày 01/9/2026;"] == "can_cu"


def test_nen_chu_cho_dong_the_thuc_vua_mot_dong():
    """Ô hẹp: nén ký tự đúng cách mẫu 979 làm, thay vì để rớt chữ xuống dòng."""
    from docx.oxml.ns import qn
    du_lieu, _ = chuan_hoa(_bao_cao(o_rong_dxa=4400))
    doan = [p for p, _ in ap_dung.duyet_doan(Document(io.BytesIO(du_lieu)))]
    p = _tim(doan, "VÀ PHÁT TRIỂN")
    nen = [r._element.rPr.find(qn("w:spacing")) for r in p.runs
           if r._element.rPr is not None
           and r._element.rPr.find(qn("w:spacing")) is not None]
    assert nen, "dòng tên đơn vị dài hơn ô thì phải được nén lại"
    assert int(nen[0].get(qn("w:val"))) < 0
    assert abs(int(nen[0].get(qn("w:val")))) <= 24, "không được nén quá trần"


def test_o_rong_du_thi_khong_nen():
    """Vừa sẵn thì không đụng — nén vô cớ làm chữ dính vào nhau."""
    from docx.oxml.ns import qn
    du_lieu, _ = chuan_hoa(_bao_cao(o_rong_dxa=5040))
    doan = [p for p, _ in ap_dung.duyet_doan(Document(io.BytesIO(du_lieu)))]
    p = _tim(doan, "VÀ PHÁT TRIỂN")
    assert not [r for r in p.runs if r._element.rPr is not None
                and r._element.rPr.find(qn("w:spacing")) is not None]


def test_nen_het_tran_van_khong_vua_thi_canh_bao_chu_khong_ep():
    _, bao_cao = chuan_hoa(_bao_cao(o_rong_dxa=2600))
    assert any("nén hết mức" in w for w in bao_cao["luu_y"])


def _cac_duong_ke(du_lieu: bytes) -> list:
    doc = Document(io.BytesIO(du_lieu))
    return [p for p, _ in ap_dung.duyet_doan(doc) if "<v:line" in p._p.xml]


def test_ve_duong_ke_ngang_roi_khong_phai_gach_chan():
    """Điều 7.2 / 8.2: "đường kẻ ngang, nét liền" — mẫu 979 vẽ bằng <v:line>,
    không dùng gạch chân và cũng không dùng viền đoạn."""
    du_lieu, _ = chuan_hoa(_bao_cao())
    assert len(_cac_duong_ke(du_lieu)) == 3   # tên đơn vị, Tiêu ngữ, trích yếu


def test_go_gach_chan_sai_cho():
    doc = Document()
    doc.add_paragraph("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM")
    p = doc.add_paragraph("Độc lập - Tự do - Hạnh phúc")
    p.runs[0].underline = True
    ra = io.BytesIO()
    doc.save(ra)

    du_lieu, _ = chuan_hoa(ra.getvalue())
    doan = [p for p, _ in ap_dung.duyet_doan(Document(io.BytesIO(du_lieu)))]
    assert not _tim(doan, "Độc lập").runs[0].font.underline


def test_cum_nhieu_dong_chi_mot_duong_ke_o_duoi_cung():
    """Trích yếu hai dòng mà vẽ hai vạch thì có một vạch chen vào giữa."""
    du_lieu, _ = chuan_hoa(_bao_cao())
    doc = Document(io.BytesIO(du_lieu))
    thu_tu = []
    for p, _ in ap_dung.duyet_doan(doc):
        if "<v:line" in p._p.xml:
            thu_tu.append("KE")
        elif p.text.strip():
            thu_tu.append(p.text.strip())
    i = next(k for k, t in enumerate(thu_tu) if t.startswith("Về kết quả"))
    assert thu_tu[i + 1].startswith("hoạt động"), "không được chen vạch vào giữa trích yếu"
    assert thu_tu[i + 2] == "KE"


def test_chay_lai_khong_ve_chong_duong_ke():
    lan1, _ = chuan_hoa(_bao_cao())
    lan2, _ = chuan_hoa(lan1)
    assert len(_cac_duong_ke(lan1)) == len(_cac_duong_ke(lan2))

def test_vung_noi_dung_doc_duoc_khong_bi_nuot_loi():
    """Trừ hai `Length` trong python-docx cho ra `int` thường, không còn `.pt`.

    Viết thẳng `(page_width - left - right).pt` là AttributeError, mà chỗ gọi
    bắt `Exception` rộng nên lỗi bị nuốt — bước nén chữ tắt ngóm, không ai biết.
    """
    doc = Document()
    rong = do_chu._vung_noi_dung_pt(doc)
    assert rong is not None and rong > 100


def test_tinh_ca_viec_word_co_bang_khi_cot_rong_hon_trang():
    """`w:tcW` chỉ là bề rộng MONG MUỐN.

    Bảng không khai `tblLayout="fixed"` mà tổng cột rộng hơn vùng nội dung thì
    Word thu nhỏ toàn bộ cột theo cùng tỷ lệ. Đo theo số khai là đo rộng hơn
    thực tế → kết luận "vừa rồi" nên không nén, còn Word vẫn đẩy chữ xuống dòng.
    """
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    doc = Document()
    t = doc.add_table(rows=1, cols=2)
    for o, rong in zip(t.rows[0].cells, (5040, 5227)):
        o.text = ""
        tcPr = o._tc.get_or_add_tcPr()
        cu = tcPr.find(qn("w:tcW"))
        if cu is not None:
            tcPr.remove(cu)
        w = OxmlElement("w:tcW")
        w.set(qn("w:w"), str(rong))
        w.set(qn("w:type"), "dxa")
        tcPr.append(w)
    p = t.rows[0].cells[0].add_paragraph("VÀ PHÁT TRIỂN NÔNG THÔN VIỆT NAM")

    o = do_chu._o_bang_cua(p)
    ty_le = do_chu._ty_le_co_bang(o, doc)
    assert ty_le < 1.0, "bảng 181mm trong vùng 160mm thì Word phải co lại"

    kha_dung = do_chu.be_rong_kha_dung_pt(p, doc)
    theo_so_khai = 5040 / 20 - 10.8
    assert kha_dung < theo_so_khai - 20, "phải nhỏ hơn hẳn con số khai trong file"


def test_bang_khai_fixed_thi_khong_co():
    """`tblLayout="fixed"` là người soạn chốt bề rộng — Word không co."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    doc = Document()
    t = doc.add_table(rows=1, cols=2)
    lay = OxmlElement("w:tblLayout")
    lay.set(qn("w:type"), "fixed")
    t._tbl.tblPr.append(lay)
    for o, rong in zip(t.rows[0].cells, (5040, 5227)):
        tcPr = o._tc.get_or_add_tcPr()
        cu = tcPr.find(qn("w:tcW"))
        if cu is not None:
            tcPr.remove(cu)
        w = OxmlElement("w:tcW")
        w.set(qn("w:w"), str(rong))
        w.set(qn("w:type"), "dxa")
        tcPr.append(w)
    p = t.rows[0].cells[0].paragraphs[0]
    assert do_chu._ty_le_co_bang(do_chu._o_bang_cua(p), doc) == 1.0


# ── Ba lỗi trên "TB Swift code Quảng Ninh.docx" ──────────────────────────────
_NS_VE = (
    'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
    'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"'
)

# Đúng thứ Word sinh ra khi người dùng vẽ tay Insert → Shapes → Line: hình được
# NEO vào đoạn có chữ, không nằm ở đoạn riêng.
_DUONG_KE_NEO = f'''<w:r {_NS_VE}><w:drawing>
  <wp:anchor distT="0" distB="0" distL="0" distR="0" simplePos="0"
             relativeHeight="1" behindDoc="0" locked="0" layoutInCell="1" allowOverlap="1">
    <wp:simplePos x="0" y="0"/>
    <wp:positionH relativeFrom="column"><wp:posOffset>0</wp:posOffset></wp:positionH>
    <wp:positionV relativeFrom="paragraph"><wp:posOffset>180000</wp:posOffset></wp:positionV>
    <wp:extent cx="1714500" cy="0"/><wp:effectExtent l="0" t="0" r="0" b="0"/>
    <wp:wrapNone/><wp:docPr id="1" name="Straight Connector 1"/>
    <a:graphic><a:graphicData uri="http://schemas.microsoft.com/office/word/2010/wordprocessingShape">
      <wps:wsp><wps:cNvCnPr/><wps:spPr>
        <a:xfrm><a:off x="0" y="0"/><a:ext cx="1714500" cy="0"/></a:xfrm>
        <a:prstGeom prst="line"><a:avLst/></a:prstGeom>
      </wps:spPr></wps:wsp>
    </a:graphicData></a:graphic>
  </wp:anchor>
</w:drawing></w:r>'''


def _van_ban_co_san_duong_ke() -> bytes:
    """Khối đầu văn bản mà người soạn đã tự vẽ đường kẻ, neo trong đoạn có chữ."""
    from docx.oxml import parse_xml

    doc = Document()
    doc.add_paragraph("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM")
    p = doc.add_paragraph("Độc lập - Tự do - Hạnh phúc")
    p._p.append(parse_xml(_DUONG_KE_NEO))
    doc.add_paragraph("BÁO CÁO")
    doc.add_paragraph("Về kết quả kiểm tra quý III.")
    ra = io.BytesIO()
    doc.save(ra)
    return ra.getvalue()


def test_khong_ve_chong_len_duong_ke_da_neo_trong_doan():
    """Word neo hình vào ĐOẠN CÓ CHỮ, không đặt ở đoạn riêng.

    Chỉ soi đoạn kế tiếp thì không thấy gì và vẽ thêm vạch thứ hai — đúng lỗi
    gặp trên "TB Swift code Quảng Ninh.docx".
    """
    du_lieu, _ = chuan_hoa(_van_ban_co_san_duong_ke())
    doc = Document(io.BytesIO(du_lieu))
    tieu_ngu = _tim([p for p, _ in ap_dung.duyet_doan(doc)], "Độc lập")
    assert duong_ke.da_co_duong_ke(tieu_ngu)
    ke = tieu_ngu._p.getnext()
    assert ke is None or "<v:line" not in ke.xml, "đã có vạch rồi mà còn vẽ thêm"


def test_logo_trong_doan_khong_bi_coi_la_duong_ke():
    """Hình trong đoạn chỉ tính là vạch khi nó ĐÚNG là đường thẳng.

    Nhận mọi <w:drawing> thì đoạn tên đơn vị có logo sẽ không bao giờ được kẻ.
    """
    from docx.oxml import parse_xml

    doc = Document()
    p = doc.add_paragraph("Độc lập - Tự do - Hạnh phúc")
    p._p.append(parse_xml(_DUONG_KE_NEO.replace('prst="line"', 'prst="rect"')))
    assert not duong_ke.da_co_duong_ke(p)


def _sect_pr(du_lieu: bytes):
    from docx.oxml.ns import qn
    doc = Document(io.BytesIO(du_lieu))
    return doc.sections[0]._sectPr.find(qn("w:pgNumType")), qn


def test_so_trang_dem_lai_tu_1():
    """`pgNumType w:start` theo chân văn bản khi cắt một phần ra khỏi tài liệu
    dài. Chèn số trang đúng chỗ mà đếm từ 23 thì nhìn vẫn là sai."""
    from docx.oxml import parse_xml
    from docx.oxml.ns import qn

    doc = Document()
    doc.add_paragraph("Kính gửi: Giám đốc")
    doc.sections[0]._sectPr.append(parse_xml(
        '<w:pgNumType xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
        ' w:start="23"/>'))
    ra = io.BytesIO()
    doc.save(ra)

    du_lieu, bc = chuan_hoa(ra.getvalue())
    pgnum, _ = _sect_pr(du_lieu)
    assert pgnum is not None and pgnum.get(qn("w:start")) == "1"
    assert any("đánh số trang lại từ 1" in x for x in bc["sua_chung"])


def test_khong_dung_den_pgnumtype_khi_von_da_dung():
    doc = Document()
    doc.add_paragraph("Kính gửi: Giám đốc")
    ra = io.BytesIO()
    doc.save(ra)
    _, bc = chuan_hoa(ra.getvalue())
    assert not any("đánh số trang lại" in x for x in bc["sua_chung"])


def _van_ban_co_ngat_trang() -> bytes:
    from docx.oxml import parse_xml

    doc = Document()
    doc.add_paragraph("1. Nội dung thứ nhất.")
    doc.add_paragraph()._p.append(parse_xml(
        '<w:r xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:br w:type="page"/></w:r>'))
    p = doc.add_paragraph("2. Nội dung thứ hai.")
    p._p.insert(0, parse_xml(
        '<w:pPr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:pageBreakBefore/></w:pPr>'))
    ra = io.BytesIO()
    doc.save(ra)
    return ra.getvalue()


def _so_ngat_trang(du_lieu: bytes) -> int:
    from docx.oxml.ns import qn
    doc = Document(io.BytesIO(du_lieu))
    n = sum(1 for p in doc.paragraphs for b in p._p.iter(qn("w:br"))
            if b.get(qn("w:type")) == "page")
    n += sum(1 for p in doc.paragraphs
             if p._p.find(qn("w:pPr")) is not None
             and p._p.find(qn("w:pPr")).find(qn("w:pageBreakBefore")) is not None)
    return n


def test_bo_ngat_trang_thu_cong_ma_khong_mat_chu():
    """Ngắt trang tay đặt theo bố cục CŨ; chuẩn hoá làm chữ cao lên nên nó rơi
    vào giữa chừng và đẻ ra một trang gần như trống."""
    du_lieu, bc = chuan_hoa(_van_ban_co_ngat_trang())
    assert _so_ngat_trang(du_lieu) == 0
    doc = Document(io.BytesIO(du_lieu))
    chu = "\n".join(p.text for p in doc.paragraphs)
    assert "1. Nội dung thứ nhất." in chu and "2. Nội dung thứ hai." in chu
    assert any("ngắt trang thủ công" in x for x in bc["sua_chung"])
    assert any("ngắt trang" in x for x in bc["luu_y"])


def test_tat_cong_tac_thi_giu_nguyen_ngat_trang():
    """Phụ lục ban hành kèm theo Quyết định thật sự cần sang trang mới."""
    du_lieu, bc = chuan_hoa(_van_ban_co_ngat_trang(),
                            {"chung": {"bo_ngat_trang_thu_cong": False}})
    assert _so_ngat_trang(du_lieu) == 2
    assert not any("ngắt trang thủ công" in x for x in bc["sua_chung"])


def test_doan_co_chu_kem_ngat_trang_chi_mat_dau_ngat():
    from docx.oxml import parse_xml

    doc = Document()
    p = doc.add_paragraph("Nội dung quan trọng.")
    p._p.append(parse_xml(
        '<w:r xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:br w:type="page"/></w:r>'))
    ra = io.BytesIO()
    doc.save(ra)

    du_lieu, _ = chuan_hoa(ra.getvalue())
    doc2 = Document(io.BytesIO(du_lieu))
    assert _so_ngat_trang(du_lieu) == 0
    assert "Nội dung quan trọng." in "\n".join(p.text for p in doc2.paragraphs)


def test_khong_xoa_doan_dang_giu_dau_ngat_section():
    """Đoạn rỗng có `sectPr` là dấu ngắt SECTION — xoá là mất khổ giấy / lề
    riêng của phần sau, mà không lỗi nào báo."""
    from docx.oxml import parse_xml
    from docx.oxml.ns import qn

    doc = Document()
    doc.add_paragraph("Phần một.")
    p = doc.add_paragraph()
    p._p.append(parse_xml(
        '<w:r xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:br w:type="page"/></w:r>'))
    p._p.insert(0, parse_xml(
        '<w:pPr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:sectPr><w:pgSz w:w="16838" w:h="11906" w:orient="landscape"/></w:sectPr></w:pPr>'))
    doc.add_paragraph("Phần hai.")
    ra = io.BytesIO()
    doc.save(ra)

    du_lieu, _ = chuan_hoa(ra.getvalue())
    doc2 = Document(io.BytesIO(du_lieu))
    assert _so_ngat_trang(du_lieu) == 0, "vẫn phải gỡ dấu ngắt trang"
    assert len(doc2.sections) == 2, "không được nuốt mất dấu ngắt section"


# ── Tên đơn vị dài trình bày nhiều dòng (Điều 8.2) ───────────────────────────
def _khoi_dau(*dong: str) -> bytes:
    doc = Document()
    for t in dong:
        doc.add_paragraph(t)
    doc.add_paragraph("QUYẾT ĐỊNH")
    doc.add_paragraph("Về việc điều động cán bộ")
    ra = io.BytesIO()
    doc.save(ra)
    return ra.getvalue()


def _ma_cua(du_lieu: bytes) -> list[tuple[str, str]]:
    """Cụm từ liền dòng được ghép bằng dấu cách KHÔNG NGẮT (U+00A0) — trả về
    dấu cách thường để tra bằng chuỗi gõ tay trong test."""
    doc = Document(io.BytesIO(du_lieu))
    khoi = ap_dung.duyet_doan(doc)
    ma = nhan_dien.phan_loai([(p.text, tb) for p, tb in khoi])
    return [(p.text.replace(" ", " ").strip(), m)
            for (p, _), m in zip(khoi, ma) if p.text.strip()]


def _dam(du_lieu: bytes, chua: str) -> bool:
    doc = Document(io.BytesIO(du_lieu))
    p = _tim([q for q, _ in ap_dung.duyet_doan(doc)], chua)
    return bool(ap_dung._hieu_luc_run(p.runs[0], p, "bold"))


def test_ten_don_vi_dai_xuong_dong_van_la_mot_ten():
    """"NGÂN HÀNG NÔNG NGHIỆP / VÀ PHÁT TRIỂN…" là MỘT tên xuống dòng.

    Cắt đôi thành chủ quản + ban hành là bỏ in đậm nửa trên — sai ngay dòng đầu
    tiên của văn bản, đúng lỗi người dùng chỉ ra trên "TB Swift code Quảng Ninh".
    """
    du_lieu, _ = chuan_hoa(_khoi_dau("NGÂN HÀNG NÔNG NGHIỆP",
                                     "VÀ PHÁT TRIỂN NÔNG THÔN VIỆT NAM"))
    ma = dict(_ma_cua(du_lieu))
    assert ma["NGÂN HÀNG NÔNG NGHIỆP"] == "ten_dv_ban_hanh"
    assert ma["VÀ PHÁT TRIỂN NÔNG THÔN VIỆT NAM"] == "ten_dv_ban_hanh"
    assert _dam(du_lieu, "NGÂN HÀNG NÔNG NGHIỆP"), "cả hai dòng phải in đậm"
    assert _dam(du_lieu, "VÀ PHÁT TRIỂN")


def test_khoi_hai_cap_that_khong_bi_gop():
    """Dòng sau bắt đầu một tên MỚI thì vẫn là hai cấp đơn vị như cũ."""
    du_lieu, _ = chuan_hoa(_khoi_dau("NGÂN HÀNG NÔNG NGHIỆP VÀ PHÁT TRIỂN NÔNG THÔN VIỆT NAM",
                                     "CHI NHÁNH HÀ NỘI"))
    ma = dict(_ma_cua(du_lieu))
    assert ma["NGÂN HÀNG NÔNG NGHIỆP VÀ PHÁT TRIỂN NÔNG THÔN VIỆT NAM"] == "ten_dv_chu_quan"
    assert ma["CHI NHÁNH HÀ NỘI"] == "ten_dv_ban_hanh"
    assert not _dam(du_lieu, "NGÂN HÀNG NÔNG NGHIỆP VÀ"), "chủ quản không in đậm"
    assert _dam(du_lieu, "CHI NHÁNH HÀ NỘI")


def test_ten_chu_quan_dai_xuong_dong_van_la_chu_quan():
    """Ba dòng: hai dòng đầu là MỘT tên chủ quản, dòng ba mới là đơn vị ban hành."""
    du_lieu, _ = chuan_hoa(_khoi_dau("NGÂN HÀNG NÔNG NGHIỆP",
                                     "VÀ PHÁT TRIỂN NÔNG THÔN VIỆT NAM",
                                     "CHI NHÁNH QUẢNG NINH"))
    ma = dict(_ma_cua(du_lieu))
    assert ma["NGÂN HÀNG NÔNG NGHIỆP"] == "ten_dv_chu_quan"
    assert ma["VÀ PHÁT TRIỂN NÔNG THÔN VIỆT NAM"] == "ten_dv_chu_quan"
    assert ma["CHI NHÁNH QUẢNG NINH"] == "ten_dv_ban_hanh"


def test_cum_ten_don_vi_nhieu_dong_chi_mot_duong_ke():
    """Vạch nằm dưới dòng CUỐI của cụm, không chen vào giữa hai dòng."""
    du_lieu, _ = chuan_hoa(_khoi_dau("NGÂN HÀNG NÔNG NGHIỆP",
                                     "VÀ PHÁT TRIỂN NÔNG THÔN VIỆT NAM"))
    doc = Document(io.BytesIO(du_lieu))
    thu_tu = []
    for p, _ in ap_dung.duyet_doan(doc):
        if "<v:line" in p._p.xml:
            thu_tu.append("KE")
        elif p.text.strip():
            thu_tu.append(p.text.replace(" ", " ").strip())
    i = thu_tu.index("NGÂN HÀNG NÔNG NGHIỆP")
    assert thu_tu[i + 1] == "VÀ PHÁT TRIỂN NÔNG THÔN VIỆT NAM", "không chen vạch vào giữa"
    assert thu_tu[i + 2] == "KE", "cụm hai dòng chỉ được MỘT vạch, ở dưới dòng cuối"
    # Vạch thứ hai là của trích yếu (Điều 11.2) — đúng, không phải vạch thừa.
    assert thu_tu.count("KE") == 2


# ── Ba cách kẻ vạch sẵn: hình vẽ giữ nguyên, gạch chân và viền đoạn thì thay ──
_PBDR = ('<w:pPr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
         "<w:pBdr>{}</w:pBdr></w:pPr>")
_VIEN = '<w:{0} w:val="single" w:sz="6" w:space="1" w:color="000000"/>'


def _tieu_ngu_co(che_bien) -> bytes:
    doc = Document()
    doc.add_paragraph("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM")
    che_bien(doc.add_paragraph("Độc lập - Tự do - Hạnh phúc"))
    doc.add_paragraph("QUYẾT ĐỊNH")
    doc.add_paragraph("Về việc điều động cán bộ")
    ra = io.BytesIO()
    doc.save(ra)
    return ra.getvalue()


def _tieu_ngu_sau(du_lieu: bytes):
    doc = Document(io.BytesIO(du_lieu))
    ds = [p for p, _ in ap_dung.duyet_doan(doc)]
    i = next(k for k, p in enumerate(ds) if "Độc lập" in p.text)
    so_vach = sum(1 for p in ds[i:i + 2]
                  if "<v:line" in p._p.xml or 'prstGeom prst="line"' in p._p.xml)
    return ds[i], so_vach


def test_vien_duoi_cua_doan_bi_go_roi_moi_ve_vach():
    """`w:pBdr/w:bottom` luôn dài hết bề ngang đoạn, không làm được "1/3 đến
    1/2 dòng chữ". Coi nó là "đã có vạch" là chấp nhận một vạch sai độ dài;
    để nguyên rồi vẽ thêm là hai vạch chồng nhau. Phải gỡ rồi vẽ lại."""
    from docx.oxml import parse_xml

    du_lieu, _ = chuan_hoa(_tieu_ngu_co(
        lambda p: p._p.insert(0, parse_xml(_PBDR.format(_VIEN.format("bottom"))))))
    p, so_vach = _tieu_ngu_sau(du_lieu)
    assert "w:bottom" not in p._p.xml, "viền dưới phải được gỡ"
    assert so_vach == 1, "chỉ được đúng một vạch"


def test_giu_vien_khac_cua_doan():
    """Chỉ nhấc riêng `w:bottom` — viền trên là thứ người soạn cố ý đặt."""
    from docx.oxml import parse_xml

    du_lieu, _ = chuan_hoa(_tieu_ngu_co(lambda p: p._p.insert(
        0, parse_xml(_PBDR.format(_VIEN.format("top") + _VIEN.format("bottom"))))))
    p, so_vach = _tieu_ngu_sau(du_lieu)
    assert "w:top" in p._p.xml, "không được xoá lây viền trên"
    assert "w:bottom" not in p._p.xml
    assert so_vach == 1


@pytest.mark.parametrize("hinh", ["v_line", "straight_connector"])
def test_da_co_hinh_ve_thi_khong_them_vach(hinh):
    """Vạch là HÌNH VẼ thì giữ nguyên, không vẽ chồng — cả kiểu Word cũ
    (`<v:line>`) lẫn Word mới (Straight Connector)."""
    from docx.oxml import parse_xml

    xml = (f'<w:r {_NS_VE.split(" xmlns:wp")[0]} xmlns:v="urn:schemas-microsoft-com:vml">'
           '<w:pict><v:line style="position:absolute" from="0,0" to="120pt,0"/></w:pict></w:r>'
           if hinh == "v_line" else _DUONG_KE_NEO)
    du_lieu, _ = chuan_hoa(_tieu_ngu_co(lambda p: p._p.append(parse_xml(xml))))
    _, so_vach = _tieu_ngu_sau(du_lieu)
    assert so_vach == 1


# ── Mục con của gạch đầu dòng (không có trong QĐ 979, suy từ chữ) ────────────
def _van_ban_co_muc_con(*dong: str) -> bytes:
    doc = Document()
    doc.add_paragraph("a) Tài liệu giao phẩm bao gồm:")
    for t in dong:
        doc.add_paragraph(t)
    doc.add_paragraph("b) Nội dung tiếp theo")
    ra = io.BytesIO()
    doc.save(ra)
    return ra.getvalue()


def _dong_va_le(du_lieu: bytes) -> list[tuple[str, float]]:
    doc = Document(io.BytesIO(du_lieu))
    return [(p.text.replace(" ", " ").strip(),
             round(p.paragraph_format.left_indent.cm, 1)
             if p.paragraph_format.left_indent is not None else 0.0)
            for p in doc.paragraphs if p.text.strip()]


def test_muc_con_doi_dau_va_thut_le():
    """Dòng gạch đầu dòng kết thúc bằng ":" mở một danh sách con."""
    du_lieu, _ = chuan_hoa(_van_ban_co_muc_con(
        "- 04 Mẫu biểu, bao gồm:",
        "- Mẫu biểu 01 (MB01): Đề xuất ý tưởng;",
        "- Mẫu biểu 02 (MB02): Kế hoạch chi tiết."))
    ds = dict(_dong_va_le(du_lieu))
    assert ds["- 04 Mẫu biểu, bao gồm:"] == 0.0
    assert ds["+ Mẫu biểu 01 (MB01): Đề xuất ý tưởng;"] == 1.0
    assert ds["+ Mẫu biểu 02 (MB02): Kế hoạch chi tiết."] == 1.0


def test_danh_sach_con_dong_o_dong_ket_thuc_bang_dau_cham():
    """Điều 15.4: cuối mỗi dòng ";", dòng CUỐI CÙNG ".".

    Thiếu quy tắc đóng thì mục ngang cấp đứng ngay sau bị tụt xuống làm mục con
    — đã gặp thật trong "Bao cao nghiem thu NPA.docx" ở dòng "- Sản phẩm bàn
    giao: …".
    """
    du_lieu, _ = chuan_hoa(_van_ban_co_muc_con(
        "- Xây dựng phương pháp luận, gồm:",
        "- Phương pháp xác định sản phẩm mới;",
        "- Các mẫu biểu, báo cáo liên quan.",
        "- Sản phẩm bàn giao: Tài liệu phương pháp luận."))
    ds = dict(_dong_va_le(du_lieu))
    assert ds["+ Phương pháp xác định sản phẩm mới;"] == 1.0
    assert ds["+ Các mẫu biểu, báo cáo liên quan."] == 1.0
    assert ds["- Sản phẩm bàn giao: Tài liệu phương pháp luận."] == 0.0


def test_khong_dong_som_khi_moi_dong_deu_ket_thuc_bang_dau_cham():
    """Người soạn chấm câu mọi dòng bằng "." thì dấu chấm không nói lên điều gì.

    Đóng theo nó là cắt danh sách ngay sau mục con ĐẦU TIÊN.
    """
    du_lieu, _ = chuan_hoa(_van_ban_co_muc_con(
        "- Tài liệu gồm:",
        "- Mục con thứ nhất.",
        "- Mục con thứ hai.",
        "- Mục con thứ ba."))
    ds = dict(_dong_va_le(du_lieu))
    for t in ("+ Mục con thứ nhất.", "+ Mục con thứ hai.", "+ Mục con thứ ba."):
        assert ds[t] == 1.0, t


def test_danh_sach_noi_nhan_khong_bi_phan_cap():
    """Nơi nhận cũng dùng "-" nhưng là danh sách phẳng, cỡ chữ 11 riêng."""
    doc = Document()
    doc.add_paragraph("Nơi nhận:")
    for t in ("- Như trên:", "- Ban Giám đốc;", "- Lưu: VT, TH (2)."):
        doc.add_paragraph(t)
    ra = io.BytesIO()
    doc.save(ra)

    du_lieu, _ = chuan_hoa(ra.getvalue())
    chu = "\n".join(t for t, _ in _dong_va_le(du_lieu))
    assert "+" not in chu, "không được đụng vào danh sách nơi nhận"


def test_tat_phan_cap_thi_giu_nguyen():
    du_lieu, _ = chuan_hoa(
        _van_ban_co_muc_con("- 04 Mẫu biểu, bao gồm:", "- Mẫu biểu 01 (MB01): A."),
        {"chung": {"phan_cap_gach_dau_dong": False}})
    ds = dict(_dong_va_le(du_lieu))
    assert ds["- Mẫu biểu 01 (MB01): A."] == 0.0


def test_giu_thut_le_muc_con_tac_gia_da_dat():
    """Thụt lề là cách DUY NHẤT trong .docx để nói "đây là mục con" — QĐ 979
    chỉ đánh số tới *điểm*. Ép về 0 là xoá phẳng phân cấp tác giả đã viết."""
    from docx.shared import Cm

    doc = Document()
    doc.add_paragraph("a) Tài liệu bao gồm:")
    doc.add_paragraph("- Mục cha không kết thúc bằng hai chấm")
    p = doc.add_paragraph("- Mục con tác giả tự thụt")
    p.paragraph_format.left_indent = Cm(1.5)
    q = doc.add_paragraph("Đoạn lời văn bị thụt vô cớ")
    q.paragraph_format.left_indent = Cm(1.5)
    ra = io.BytesIO()
    doc.save(ra)

    ds = dict(_dong_va_le(chuan_hoa(ra.getvalue())[0]))
    assert ds["- Mục con tác giả tự thụt"] == 1.5, "giữ đúng mức tác giả đặt"
    assert ds["Đoạn lời văn bị thụt vô cớ"] == 0.0, "lời văn thường vẫn dọn về 0"


# ── Khối tên đơn vị: chia vai theo chữ đậm tác giả đã đặt (Điều 8.2) ─────────
def _khoi_ten_dv(*dong: tuple[str, bool]) -> bytes:
    doc = Document()
    for t, dam in dong:
        doc.add_paragraph().add_run(t).bold = dam
    doc.add_paragraph("QUYẾT ĐỊNH")
    doc.add_paragraph("Về việc điều động cán bộ")
    ra = io.BytesIO()
    doc.save(ra)
    return ra.getvalue()


def _dam_va_ke(du_lieu: bytes) -> dict[str, tuple[bool, bool]]:
    doc = Document(io.BytesIO(du_lieu))
    kq = {}
    for p, _ in ap_dung.duyet_doan(doc):
        t = p.text.replace(" ", " ").strip()
        if not t or not p.runs:
            continue
        ke = p._p.getnext()
        kq[t] = (bool(ap_dung._hieu_luc_run(p.runs[0], p, "bold")),
                 bool(ke is not None and "<v:line" in ke.xml))
    return kq


def test_khoi_ten_dv_chia_vai_theo_dam_tac_gia():
    """Tên đơn vị ban hành dài được trình bày nhiều dòng (Điều 8.2).

    "TỔ TRIỂN KHAI NGHIỆP VỤ" mở đầu bằng danh từ nên không có dấu hiệu chữ nào
    nói nó thuộc cùng tên với dòng trên — nhưng tác giả đã bôi đậm cả hai dòng,
    đó mới là dấu hiệu thật.
    """
    du_lieu, _ = chuan_hoa(_khoi_ten_dv(
        ("NGÂN HÀNG NÔNG NGHIỆP", False),
        ("VÀ PHÁT TRIỂN NÔNG THÔN VIỆT NAM", False),
        ("BAN TRIỂN KHAI GP QLRR HOẠT ĐỘNG", True),
        ("TỔ TRIỂN KHAI NGHIỆP VỤ", True)))
    kq = _dam_va_ke(du_lieu)
    assert kq["NGÂN HÀNG NÔNG NGHIỆP"] == (False, False)
    assert kq["VÀ PHÁT TRIỂN NÔNG THÔN VIỆT NAM"] == (False, False)
    assert kq["BAN TRIỂN KHAI GP QLRR HOẠT ĐỘNG"] == (True, False)
    assert kq["TỔ TRIỂN KHAI NGHIỆP VỤ"] == (True, True), "vạch chỉ ở dòng cuối"


def test_mau_979_chu_quan_nhieu_dong_van_khong_dam():
    """Ví dụ ngay trong Điều 8: chủ quản 3 dòng, ban hành 1 dòng."""
    du_lieu, _ = chuan_hoa(_khoi_ten_dv(
        ("NGÂN HÀNG NÔNG NGHIỆP", False),
        ("VÀ PHÁT TRIỂN NÔNG THÔN", False),
        ("VIỆT NAM – CHI NHÁNH THỦ ĐÔ", False),
        ("PHÒNG GIAO DỊCH CHỢ MƠ", True)))
    kq = _dam_va_ke(du_lieu)
    assert kq["VIỆT NAM – CHI NHÁNH THỦ ĐÔ"] == (False, False)
    assert kq["PHÒNG GIAO DỊCH CHỢ MƠ"] == (True, True)


def test_dam_ca_khoi_thi_quay_ve_doan_bang_chu():
    """Bôi đậm cả khối nghĩa là tác giả KHÔNG phân biệt hai vai — dấu hiệu vô
    nghĩa, phải quay về `_gom_ten_dv_nhieu_dong`."""
    du_lieu, _ = chuan_hoa(_khoi_ten_dv(
        ("NGÂN HÀNG NÔNG NGHIỆP", True),
        ("VÀ PHÁT TRIỂN NÔNG THÔN VIỆT NAM", True)))
    kq = _dam_va_ke(du_lieu)
    assert kq["NGÂN HÀNG NÔNG NGHIỆP"] == (True, False)
    assert kq["VÀ PHÁT TRIỂN NÔNG THÔN VIỆT NAM"] == (True, True)


def test_dam_rai_rac_giua_khoi_thi_bo_qua():
    """Điều 8.2 đặt tên đơn vị ban hành DƯỚI tên đơn vị quản lý trực tiếp.
    Đậm nằm giữa khối là định dạng lỗi, không phải phân vai."""
    assert not nhan_dien.theo_dam_khoi_ten_dv(
        ["ten_dv_chu_quan", "ten_dv_chu_quan", "ten_dv_ban_hanh"],
        [False, True, False])


def test_chia_vai_theo_dam_chay_lai_khong_doi():
    goc = _khoi_ten_dv(
        ("NGÂN HÀNG NÔNG NGHIỆP", False),
        ("VÀ PHÁT TRIỂN NÔNG THÔN VIỆT NAM", False),
        ("BAN TRIỂN KHAI GP QLRR HOẠT ĐỘNG", True),
        ("TỔ TRIỂN KHAI NGHIỆP VỤ", True))
    lan1, _ = chuan_hoa(goc)
    lan2, _ = chuan_hoa(lan1)
    assert _dam_va_ke(lan1) == _dam_va_ke(lan2)


# ── Số tự động của Word, số trang trùng, "Kính trình" ────────────────────────
_W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def _doan_danh_so_tu_dong(co_dau_doan: int = 16, phong: str = "") -> bytes:
    """Đoạn dùng danh sách đánh số TỰ ĐỘNG của Word, dấu đoạn để cỡ nhỏ."""
    from docx.oxml import parse_xml
    from docx.shared import Pt

    doc = Document()
    doc.add_paragraph("Các đơn vị phối hợp:")
    p = doc.add_paragraph("Ban Quản lý Tài sản Nợ - Tài sản Có")
    pPr = p._p.get_or_add_pPr()
    pPr.insert(0, parse_xml(
        f'<w:numPr {_W}><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>'))
    fonts = (f'<w:rFonts w:ascii="{phong}" w:hAnsi="{phong}" w:cs="{phong}"/>'
             if phong else "")
    pPr.append(parse_xml(
        f'<w:rPr {_W}>{fonts}<w:sz w:val="{co_dau_doan}"/>'
        f'<w:szCs w:val="{co_dau_doan}"/></w:rPr>'))
    for r in p.runs:
        r.font.size = Pt(14)
    ra = io.BytesIO()
    doc.save(ra)
    return ra.getvalue()


def _co_dau_doan(du_lieu: bytes, chua: str) -> float | None:
    from docx.oxml.ns import qn

    doc = Document(io.BytesIO(du_lieu))
    p = next(q for q, _ in ap_dung.duyet_doan(doc) if chua in q.text)
    pPr = p._p.find(qn("w:pPr"))
    rPr = pPr.find(qn("w:rPr")) if pPr is not None else None
    sz = rPr.find(qn("w:sz")) if rPr is not None else None
    return int(sz.get(qn("w:val"))) / 2 if sz is not None else None


def test_so_tu_dong_khong_con_be_hon_loi_van():
    """Số của danh sách tự động không nằm trong `<w:r>` nào — Word lấy định
    dạng từ `rPr` của DẤU ĐOẠN. Sửa cỡ chữ từng run không chạm tới nó."""
    # `bo_bullet_tu_dong` tắt để `numPr` còn nguyên — đúng tình huống danh sách
    # ĐÁNH SỐ tự động (mặc định `bo_so_tu_dong = False`, phần mềm giữ nguyên số).
    du_lieu, _ = chuan_hoa(_doan_danh_so_tu_dong(),
                           {"danh_so": {"bo_bullet_tu_dong": False}})
    assert _co_dau_doan(du_lieu, "Ban Quản lý") == 14.0

    doc = Document(io.BytesIO(du_lieu))
    p = next(q for q, _ in ap_dung.duyet_doan(doc) if "Ban Quản lý" in q.text)
    assert p.runs[-1].font.size.pt == 14.0, "lời văn vẫn phải đúng cỡ"


def test_dau_doan_von_dung_co_thi_khong_ghi_nhat_ky():
    """Đã đúng thì không sinh một dòng nhật ký rỗng nghĩa."""
    _, bc = chuan_hoa(
        _doan_danh_so_tu_dong(co_dau_doan=28, phong="Times New Roman"),
        {"danh_so": {"bo_bullet_tu_dong": False}})
    assert not any("số/gạch đầu dòng tự động" in x for x in bc["sua_chung"])


def _van_ban_co_so_trang(cho: str | None):
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls

    doc = Document()
    doc.add_paragraph("Nội dung văn bản.")
    s = doc.sections[0]
    s.different_first_page_header_footer = True
    if cho:
        phan = getattr(s, cho)
        phan.is_linked_to_previous = False
        par = phan.paragraphs[0] if phan.paragraphs else phan.add_paragraph()
        for kieu, nd in (("begin", None), (None, " PAGE "), ("end", None)):
            r = par.add_run()
            if kieu:
                r._r.append(parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="{kieu}"/>'))
            else:
                r._r.append(parse_xml(
                    f'<w:instrText {nsdecls("w")} xml:space="preserve">{nd}</w:instrText>'))
    ra = io.BytesIO()
    doc.save(ra)
    return ra.getvalue()


def _dem_truong_page(du_lieu: bytes) -> int:
    z = zipfile.ZipFile(io.BytesIO(du_lieu))
    return sum(z.read(n).decode("utf-8").count("PAGE")
               for n in z.namelist() if "header" in n or "footer" in n)


@pytest.mark.parametrize("cho", ["footer", "first_page_header", "header"])
def test_khong_danh_them_so_trang_khi_da_co(cho):
    """Soi đủ sáu chỗ đầu/chân trang. Chỉ soi header mặc định thì văn bản đã
    đánh số ở chân trang sẽ bị đánh thêm — in ra hai con số chồng nhau."""
    du_lieu, _ = chuan_hoa(_van_ban_co_so_trang(cho))
    assert _dem_truong_page(du_lieu) == 1


def test_van_danh_so_trang_khi_chua_co():
    du_lieu, bc = chuan_hoa(_van_ban_co_so_trang(None))
    assert _dem_truong_page(du_lieu) == 1
    assert any("đánh số trang" in x for x in bc["sua_chung"])


def test_kinh_trinh_duoc_nhan_nhu_kinh_gui():
    """Mẫu 16 Phụ lục V (Phiếu trình chuyển) in đúng chữ "Kính trình:"."""
    assert nhan_dien.phan_loai(
        [("Kính trình: Phó Tổng Giám đốc Vương Hồng Lĩnh.", False),
         ("Nội dung.", False)])[0] == "kinh_gui"
    assert nhan_dien.phan_loai(
        [("Kính trình:", False), ("- Ban Pháp chế;", False)])[0] == "kinh_gui_ds"


# ── Khối "Kính gửi / Kính trình" dựng bằng bảng ──────────────────────────────
def _to_trinh_bang(*o_bang: str, bang_so_lieu=None, doan_chen=True) -> bytes:
    """Khối Kính trình dựng bằng bảng — cách người soạn hay dùng để canh chỗ."""
    from docx.shared import Pt

    doc = Document()
    doc.add_paragraph("TỜ TRÌNH")
    doc.add_paragraph("V/v đề xuất triển khai thử nghiệm")
    t = doc.add_table(rows=1, cols=len(o_bang))
    for o, txt in zip(t.rows[0].cells, o_bang):
        if txt:
            o.paragraphs[0].add_run(txt).font.size = Pt(11)
    if doan_chen:
        doc.add_paragraph("Căn cứ Quy trình số 699/QTr-NHNo-TTTM;")
    if bang_so_lieu:
        t2 = doc.add_table(rows=len(bang_so_lieu), cols=len(bang_so_lieu[0]))
        for hang, bo in zip(t2.rows, bang_so_lieu):
            for o, txt in zip(hang.cells, bo):
                o.paragraphs[0].add_run(txt).font.size = Pt(11)
    ra = io.BytesIO()
    doc.save(ra)
    return ra.getvalue()


def _co_theo_dong(du_lieu: bytes) -> dict[str, float | None]:
    doc = Document(io.BytesIO(du_lieu))
    return {p.text.replace(" ", " ").strip():
            (p.runs[0].font.size.pt if p.runs and p.runs[0].font.size else None)
            for p, _ in ap_dung.duyet_doan(doc) if p.text.strip()}


def test_o_bang_cua_khoi_kinh_trinh_van_duoc_ap_the_thuc():
    """Người dùng chốt 08/09/2026: bảng dựng để CANH CHỖ cho một thành phần thể
    thức thì không phải bảng số liệu — Điều 4.2 không áp cho nó."""
    kq = _co_theo_dong(chuan_hoa(_to_trinh_bang(
        "Kính trình:", "Phó Tổng Giám đốc Vương Hồng Lĩnh."))[0])
    assert kq["Kính trình:"] == 14.0
    assert kq["Phó Tổng Giám đốc Vương Hồng Lĩnh."] == 14.0, "ô bên cạnh cũng phải theo"


def test_o_trong_canh_cho_khong_cat_khoi_kinh_trinh():
    kq = _co_theo_dong(chuan_hoa(_to_trinh_bang(
        "Kính trình:", "", "Phó Tổng Giám đốc Vương Hồng Lĩnh."))[0])
    assert kq["Phó Tổng Giám đốc Vương Hồng Lĩnh."] == 14.0


def test_bang_so_lieu_dan_sat_ngay_sau_khong_bi_keo_theo():
    """Ranh giới là CÁI BẢNG, không phải "ô liền kề".

    Lan theo ô liền kề thì ô vừa nâng thành điểm xuất phát mới và bảng số liệu
    dán sát bị kéo theo trọn vẹn — đã đo, đúng như vậy.
    """
    kq = _co_theo_dong(chuan_hoa(_to_trinh_bang(
        "Kính trình:", "Phó Tổng Giám đốc Vương Hồng Lĩnh.",
        bang_so_lieu=(("STT", "Nội dung", "Ghi chú"), ("1", "Kết nối", "x")),
        doan_chen=False))[0])
    assert kq["Phó Tổng Giám đốc Vương Hồng Lĩnh."] == 14.0
    for o in ("STT", "Nội dung", "Ghi chú", "Kết nối"):
        assert kq[o] == 11.0, f"ô «{o}» của bảng số liệu không được đụng tới"


def test_nhom_bang_khong_lan_lon_giua_hai_bang():
    """`id()` của proxy lxml bị cấp lại sau khi thu hồi — phải ghim tham chiếu.

    Không ghim thì ô cùng một bảng nhận số nhóm khác nhau, ô hai bảng khác nhau
    lại trùng số: bảng số liệu bị sửa xen kẽ từng ô, nhìn như lỗi ngẫu nhiên.
    """
    doc = Document(io.BytesIO(_to_trinh_bang(
        "Kính trình:", "Phó Tổng Giám đốc",
        bang_so_lieu=(("STT", "Nội dung"), ("1", "Kết nối")), doan_chen=False)))
    khoi = ap_dung.duyet_doan(doc)
    nhom = ap_dung.nhom_bang(doc, khoi)
    theo_o = {p.text.strip(): g for (p, _), g in zip(khoi, nhom) if p.text.strip()}
    assert theo_o["Kính trình:"] == theo_o["Phó Tổng Giám đốc"]
    assert theo_o["STT"] == theo_o["Nội dung"] == theo_o["Kết nối"]
    assert theo_o["Kính trình:"] != theo_o["STT"]
    assert theo_o["TỜ TRÌNH"] is None


def test_khong_co_nhom_bang_thi_khong_doan():
    """Gọi `phan_loai` trực tiếp thì thà không sửa còn hơn đoán ranh giới bảng."""
    ma = nhan_dien.phan_loai([("Kính trình:", True), ("Phó Tổng Giám đốc", True)])
    assert ma[1] == "bang"


# ── Rà soát 08/09/2026 trên hai văn bản thật ────────────────────────────────
def _van_ban_ket_thuc(cac_dong, kieu_noi_nhan=None) -> bytes:
    """Khối cuối một công văn: Nơi nhận + khối chữ ký.

    `kieu_noi_nhan` = "List Bullet" thì danh sách nơi nhận dựng bằng danh sách
    chấm tròn TỰ ĐỘNG của Word — dấu gạch không nằm trong `p.text`.
    """
    doc = Document()
    doc.add_paragraph("THÔNG BÁO")
    doc.add_paragraph("Về việc thử nghiệm")
    doc.add_paragraph("Nơi nhận:")
    for t in ("Như trên;", "Lưu: VP."):
        doc.add_paragraph(t, style=kieu_noi_nhan) if kieu_noi_nhan \
            else doc.add_paragraph("- " + t)
    for t in cac_dong:
        doc.add_paragraph(t)
    ra = io.BytesIO()
    doc.save(ra)
    return ra.getvalue()


def _co_theo_text(du_lieu: bytes) -> dict:
    doc = Document(io.BytesIO(du_lieu))
    ra = {}
    for p, _ in ap_dung.duyet_doan(doc):
        if p.text.strip() and p.runs:
            co = ap_dung._hieu_luc_run(p.runs[0], p, "size")
            ra[p.text.strip()] = co.pt if co is not None else None
    return ra


def test_noi_nhan_dung_bullet_tu_dong_van_duoc_nhan_dien():
    """Dấu chấm tròn tự động không nằm trong `p.text`.

    Luật nhận khối Nơi nhận đọc "dòng mở đầu bằng gạch đầu dòng, gặp dòng khác
    thì dừng" — không thấy gạch nào nên nó dừng ngay dòng đầu, cả khối rơi vào
    mã `bang` và giữ nguyên cỡ chữ gốc. Đo được trên "TB Swift code Quảng
    Ninh.docx": sáu dòng Nơi nhận không được áp thể thức nào.
    """
    co = _co_theo_text(chuan_hoa(_van_ban_ket_thuc([], "List Bullet"))[0])
    assert co["- Như trên;"] == 11.0
    assert co["- Lưu: VP."] == 11.0


def test_bullet_va_gach_go_tay_cho_cung_mot_ket_qua():
    """Dựng bằng danh sách tự động hay gõ tay đều phải ra một bản như nhau."""
    tu_dong = _co_theo_text(chuan_hoa(_van_ban_ket_thuc([], "List Bullet"))[0])
    go_tay = _co_theo_text(chuan_hoa(_van_ban_ket_thuc([]))[0])
    assert tu_dong["- Như trên;"] == go_tay["- Như trên;"]


def test_muc_trong_giua_danh_sach_bullet_khong_thanh_gach_dau_dong():
    """Gõ Enter hai lần giữa danh sách là có một mục TRỐNG.

    Đổi bullet chạy trước khi phân loại nên phải tự lọc đoạn rỗng: thêm "- "
    vào đó là biến dòng trắng thành gạch đầu dòng không có chữ, và đoạn ấy từ
    mã `trong` nhảy sang `noi_dung` — sai cả nhật ký lẫn số đoạn đếm được.
    """
    doc = Document()
    doc.add_paragraph("Điều 1. Trách nhiệm")
    doc.add_paragraph("Phòng Kế toán thực hiện.", style="List Bullet")
    doc.add_paragraph("", style="List Bullet")
    ra = io.BytesIO()
    doc.save(ra)
    du_lieu, bao_cao = chuan_hoa(ra.getvalue())
    chu = [p.text for p, _ in ap_dung.duyet_doan(Document(io.BytesIO(du_lieu)))]
    assert chu[2] == ""
    assert bao_cao["thong_ke"]["tong_doan"] == 2


def test_quyen_han_hai_dong_khong_nuot_ho_ten_nguoi_ky():
    """Điều 13.2: ký thay thì dòng dưới hình thức đề ký là chức vụ người ký.

    "GIÁM ĐỐC TRUNG TÂM THANH TOÁN" lọt qua phép thử họ tên (5 từ, từ nào cũng
    mở đầu chữ hoa) nên từng bị nhận là HỌ TÊN — và họ tên thật nằm dưới khoảng
    trống chừa chữ ký thì không còn ai nhận, ở nguyên mã `bang`.
    """
    ma = _ma_theo_text(_van_ban_ket_thuc(
        ["TL. TỔNG GIÁM ĐỐC", "GIÁM ĐỐC TRUNG TÂM THANH TOÁN", "",
         "Nguyễn Quốc Hùng"]))
    assert ma["TL. TỔNG GIÁM ĐỐC"] == "quyen_han_chuc_vu"
    assert ma["GIÁM ĐỐC TRUNG TÂM THANH TOÁN"] == "quyen_han_chuc_vu"
    assert ma["Nguyễn Quốc Hùng"] == "ho_ten_nguoi_ky"


def test_trich_yeu_cong_van_xuong_dong_duoc_noi_dai():
    """Công văn không có tên loại nên nhánh nối dài trích yếu không với tới nó.

    Gặp thật: "V/v Thông báo thay đổi tên/địa chỉ đăng ký" xuống dòng thành
    "trên hệ thống SWIFT" — dòng dưới rơi vào `noi_dung` rồi bị áp cỡ 14, căn
    đều hai bên, thụt dòng đầu 1 cm, trong khi dòng trên là cỡ 12 canh giữa.
    Hai nửa của MỘT cụm từ ra hai kiểu chữ khác nhau.
    """
    ma = nhan_dien.phan_loai([
        ("Số: 123/NHNo-TTTT", False),
        ("V/v Thông báo thay đổi tên/địa chỉ đăng ký", False),
        ("trên hệ thống SWIFT", False),
        ("Kính gửi: Giám đốc Agribank Quảng Ninh", False),
    ])
    assert ma[1] == ma[2] == "trich_yeu_cong_van"
    assert ma[3] == "kinh_gui"


def test_trich_yeu_cong_van_da_ket_cau_thi_khong_nuot_loi_van():
    """Dòng "V/v …" kết thúc bằng dấu chấm là đã hết — dòng sau là lời văn."""
    ma = nhan_dien.phan_loai([
        ("Số: 1/NHNo-TTTT", False),
        ("V/v Thông báo thay đổi địa chỉ.", False),
        ("Nội dung câu văn thường", False),
    ])
    assert ma[1] == "trich_yeu_cong_van"
    assert ma[2] == "noi_dung"


def test_chuc_danh_ghep_ngoai_danh_sach_van_duoc_nhan():
    """Liệt kê từng chức danh ghép thì danh sách không bao giờ đủ — "TRƯỞNG
    NHÓM" lọt qua dù đã có TRƯỞNG PHÒNG / TRƯỞNG BAN / TRƯỞNG ĐƠN VỊ."""
    ma = _ma_theo_text(_van_ban_ket_thuc(["TRƯỞNG NHÓM", "", "Nguyễn Đình Khánh"]))
    assert ma["TRƯỞNG NHÓM"] == "quyen_han_chuc_vu"
    assert ma["Nguyễn Đình Khánh"] == "ho_ten_nguoi_ky"


@pytest.mark.parametrize("goc, mong_doi", [
    ("Độc lập - Tự do - Hạnh Phúc", "Độc lập - Tự do - Hạnh phúc"),
    ("ĐỘC LẬP - TỰ DO - HẠNH PHÚC", "Độc lập - Tự do - Hạnh phúc"),
    ("Độc lập – Tự  do – Hạnh Phúc", "Độc lập - Tự do - Hạnh phúc"),
])
def test_tieu_ngu_sai_hoa_thuong_duoc_dua_ve_dung_dieu_7_2(goc, mong_doi):
    sua = bien_doi.chuan_tieu_ngu(goc)
    assert sua and sua[0][2] == mong_doi


def test_tieu_ngu_khong_du_ba_cum_thi_khong_viet_hoa_lai():
    """Thiếu một cụm nghĩa là chuỗi không còn là Tiêu ngữ chuẩn — viết hoa lại
    theo công thức lúc đó là đoán mò trên chữ của người soạn."""
    sua = bien_doi.chuan_tieu_ngu("Độc  lập – Tự do")
    assert sua and sua[0][2] == "Độc lập - Tự do"


def test_them_dau_cach_sau_tien_to_de_ky():
    """"TL.TỔNG GIÁM ĐỐC" gõ dính — không sai chính tả nên không ai để ý, nhưng
    khác mẫu Phụ lục V và khác mọi văn bản khác cùng tập."""
    # Bỏ dấu cách không ngắt trước khi so: "TỔNG GIÁM ĐỐC" nằm trong danh sách
    # cụm từ liền dòng nên các dấu cách bên trong đã thành U+00A0.
    chu = [p.text.replace(" ", " ").strip()
           for p, _ in ap_dung.duyet_doan(Document(io.BytesIO(
               chuan_hoa(_van_ban_ket_thuc(["TL.TỔNG GIÁM ĐỐC"]))[0])))]
    assert "TL. TỔNG GIÁM ĐỐC" in chu


@pytest.mark.parametrize("goc", ["tl.tổng giám đốc", "TL. TỔNG GIÁM ĐỐC"])
def test_tien_to_de_ky_khong_dung_toi_khi_da_dung_hoac_chu_thuong(goc):
    assert bien_doi.chuan_tien_to_quyen_han(goc) == []


def _loi_van_thut_tab() -> bytes:
    doc = Document()
    doc.add_paragraph("Điều 1. Trách nhiệm")
    doc.add_paragraph("\tTrong quá trình thực hiện, chi nhánh liên hệ Trụ sở chính.")
    doc.add_paragraph("- Swift Code\t\t: VBAAVNVX330")
    ra = io.BytesIO()
    doc.save(ra)
    return ra.getvalue()


def test_thut_dau_dong_bang_tab_bi_bo_khi_quy_chuan_tu_dat_thut():
    """Tab gõ tay + thụt dòng đầu 1 cm = thụt gấp đôi mọi dòng khác.

    Nhìn ra ngay là hỏng mà không có lỗi nào báo — quy chuẩn đã tự đặt mức thụt
    thì tab không còn là cách thụt lề nữa, chỉ còn là khoảng trống thừa.
    """
    doan = [p for p, _ in ap_dung.duyet_doan(
        Document(io.BytesIO(chuan_hoa(_loi_van_thut_tab())[0])))]
    dong = _tim(doan, "Trong quá trình")
    assert not dong.text.startswith("\t")
    assert dong.paragraph_format.first_line_indent.cm == pytest.approx(1.0, abs=0.01)


def test_tab_giua_dong_khong_bi_dung_toi():
    """Tab giữa dòng là người soạn canh cột — bỏ đi là phá cách trình bày."""
    doan = [p for p, _ in ap_dung.duyet_doan(
        Document(io.BytesIO(chuan_hoa(_loi_van_thut_tab())[0])))]
    assert "\t\t" in _tim(doan, "- Swift Code").text


def test_le_trai_doan_co_mat_tren_man_cau_hinh():
    """Mọi thuộc tính quy chuẩn ĐANG áp lên văn bản đều phải có ô trên màn hình.

    `le_trai_cm` từng bị áp ngầm: nó kéo lời văn về lề 0 mà không ô nào hiện ra,
    nên người dùng không có cách nào nhìn thấy hay tắt đi.
    """
    nguon = (pathlib.Path(__file__).resolve().parents[1]
             / "frontend" / "pages" / "vb_format.py").read_text(encoding="utf-8")
    thuoc_tinh = set(quy_chuan.QUY_CHUAN_MAC_DINH["thanh_phan"]["noi_dung"])
    thieu = [k for k in thuoc_tinh if f'"{k}"' not in nguon]
    assert not thieu, f"thuộc tính không có ô trên màn Cấu hình: {thieu}"
