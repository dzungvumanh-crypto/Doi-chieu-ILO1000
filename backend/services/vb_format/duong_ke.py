"""Đường kẻ ngang dưới Tiêu ngữ, tên đơn vị ban hành và trích yếu.

## Đây không phải gạch chân

Điều 7.2 và 8.2 nói "phía dưới có **đường kẻ ngang, nét liền**", kèm độ dài
riêng: dưới Tiêu ngữ dài **bằng** dòng chữ, dưới tên đơn vị và trích yếu dài
**1/3 đến 1/2** dòng chữ. Gạch chân (`w:u`) không làm được điều đó — nó luôn
dài đúng bằng chữ, không ngắn hơn được, và nằm sát chân chữ.

Mẫu 979 vẽ bằng đối tượng đường thẳng rời: đếm trong `document.xml` của
`Phần VB_Hướng dẫn thể thức văn bản.docx` có **7 thẻ `<v:line>`**, và **không
có** thẻ gạch chân nào, cũng không có viền đoạn (`w:pBdr`). Module này làm
đúng như vậy.

## Vì sao không dùng viền đoạn cho gọn

`w:pBdr/w:bottom` dễ viết hơn nhiều, nhưng nó kéo dài hết bề ngang của đoạn.
Quy định đòi 1/3–1/2 dòng chữ — viền đoạn không cắt ngắn được, nên dùng nó là
đổi một cái sai (gạch chân) lấy một cái sai khác.

## Chạy lại lần hai không vẽ chồng

`da_co_duong_ke()` dò cả `<v:line>` lẫn `<w:drawing>` ở đoạn kế tiếp trước khi
vẽ. Thiếu bước này thì mỗi lần chuẩn hoá lại chồng thêm một vạch nữa.
"""
import logging

from docx.oxml import parse_xml
from docx.oxml.ns import qn

from . import do_chu

_log = logging.getLogger(__name__)

_VML = 'xmlns:v="urn:schemas-microsoft-com:vml"'
_W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'

# Tỷ lệ độ dài đường kẻ so với dòng chữ, theo Điều 7.2 / 8.2 / 11.2.
# Tiêu ngữ lấy trọn 1,0; hai chỗ còn lại lấy 0,4 — giữa dải "1/3 đến 1/2".
TY_LE = {
    "tieu_ngu": 1.0,
    "ten_dv_ban_hanh": 0.4,
    "trich_yeu": 0.4,
}

_DAI_TOI_THIEU_PT = 20.0


# Dấu hiệu của một đối tượng ĐƯỜNG THẲNG. Word cũ ghi bằng VML (`<v:line>`),
# Word từ 2007 ghi bằng DrawingML: một shape có hình dựng sẵn là "line" (menu
# Insert → Shapes → Line, Word gọi là "Straight Connector").
_HINH_DUONG_KE = ('<v:line', 'prstGeom prst="line"', 'prst="straightConnector1"')


def _co_hinh_duong_ke(xml: str) -> bool:
    return any(dau in xml for dau in _HINH_DUONG_KE)


def da_co_duong_ke(p) -> bool:
    """Đã có sẵn một đường kẻ cho đoạn `p` rồi hay chưa.

    Phải soi HAI chỗ, vì có hai cách người soạn đặt vạch:

    * **Đoạn kế tiếp** — cách phần mềm này vẽ: một đoạn riêng chỉ chứa vạch.
    * **Chính đoạn `p`** — cách Word đặt khi người dùng vẽ tay: hình được
      *neo* vào đoạn có chữ, `positionV relativeFrom="paragraph"` đẩy nó
      xuống dưới dòng chữ. Nhìn trên màn hình y hệt, nhưng nằm trong cùng một
      `<w:p>` với chữ.

    Bỏ sót vế thứ hai là **vẽ chồng vạch thứ hai lên văn bản vốn đã đúng** —
    đã xảy ra thật với "TB Swift code Quảng Ninh.docx": cả Tiêu ngữ lẫn tên
    đơn vị ban hành đều có sẵn một Straight Connector neo trong đoạn, chuẩn
    hoá xong thành hai vạch chồng nhau.

    Ở chính đoạn `p` chỉ nhận đúng hình ĐƯỜNG THẲNG, không nhận mọi
    `<w:drawing>`: đoạn tên đơn vị hay có logo kèm theo, coi logo là vạch thì
    văn bản thiếu hẳn đường kẻ mà không có lỗi nào báo.
    """
    if _co_hinh_duong_ke(p._p.xml):
        return True
    ke = p._p.getnext()
    if ke is None or ke.tag != qn("w:p"):
        return False
    xml = ke.xml
    # Đoạn kế tiếp: nới tay hơn — một đoạn RỖNG chỉ chứa hình thì hình đó gần
    # như chắc chắn là vạch, và đó cũng đúng thứ phần mềm này tự vẽ ra.
    return _co_hinh_duong_ke(xml) or "<w:drawing" in xml or "<v:rect" in xml


def go_gach_chan(p) -> bool:
    """Bỏ gạch chân trên đoạn. Trả True nếu có gì bị gỡ."""
    da_go = False
    for r in p.runs:
        if r.font.underline:
            r.font.underline = False
            da_go = True
    return da_go


def _dai_duong_ke(p, ma: str, co_pt: float, dam: bool, nghieng: bool) -> float | None:
    rong = do_chu.be_rong_pt(p.text.strip(), co_pt, dam, nghieng)
    if not rong:
        return None
    dai = rong * TY_LE.get(ma, 0.4)
    return max(dai, _DAI_TOI_THIEU_PT)


def ve_duong_ke(p, ma: str, co_pt: float, dam: bool = False,
                nghieng: bool = False) -> bool:
    """Chèn một đoạn chứa đường kẻ ngang ngay dưới `p`. Trả True nếu đã vẽ."""
    if da_co_duong_ke(p):
        return False
    dai = _dai_duong_ke(p, ma, co_pt, dam, nghieng)
    if dai is None:
        return False

    # `mso-position-horizontal:center` canh giữa vạch so với cột chứa nó, nên
    # vạch tự cân dưới dòng chữ mà không phải tính toạ độ trái/phải.
    xml = (
        f'<w:p {_W}>'
        f'<w:pPr><w:spacing w:before="0" w:after="0" w:line="60" '
        f'w:lineRule="exact"/><w:jc w:val="center"/></w:pPr>'
        f'<w:r><w:pict {_VML}>'
        f'<v:line style="position:absolute;mso-position-horizontal:center;'
        f'mso-position-horizontal-relative:text;z-index:1" '
        f'from="0,0" to="{dai:.1f}pt,0" strokeweight=".5pt" '
        f'strokecolor="#000000"/>'
        f'</w:pict></w:r></w:p>'
    )
    try:
        p._p.addnext(parse_xml(xml))
    except Exception as e:                                        # noqa: BLE001
        _log.warning("Không chèn được đường kẻ ngang: %s", e)
        return False
    return True
