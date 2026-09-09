"""Chuẩn hoá văn bản theo QĐ 979/QyĐ-NHNo-PC — tải file Word lên, nhận bản đã sửa.

Hai tab: "Chuẩn hoá văn bản" (việc hằng ngày) và "Cấu hình quy chuẩn" (thông số).

Tab Cấu hình dựng form THẲNG TỪ dữ liệu backend trả về (`nhan`, `dai_co_chu`,
`mac_dinh`) chứ không gõ lại danh sách 28 thành phần thể thức ở đây. Gõ lại là
có hai bản danh sách: thêm một thành phần bên `quy_chuan.py` mà quên sửa ở đây
thì nó vẫn được áp dụng khi chuẩn hoá nhưng KHÔNG hiện trên màn hình — người
dùng không có cách nào biết vì sao văn bản bị sửa theo một luật họ không thấy.
"""
import asyncio

from nicegui import ui

import frontend.api_client as api
from frontend.shared import (
    _sidebar, _content_area, _page_header, _require_auth, _handle_api_error, _card,
)

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

# Gom 28 thành phần thể thức thành 4 khối theo vị trí trên trang giấy — người
# dùng tìm theo "chỗ nào trên văn bản", không tìm theo tên khoá kỹ thuật.
_NHOM = [
    ("Phần đầu văn bản", [
        "quoc_hieu", "tieu_ngu", "ten_dv_chu_quan", "ten_dv_ban_hanh",
        "so_ky_hieu", "dia_danh_ngay", "ten_loai", "trich_yeu", "trich_yeu_cong_van",
    ]),
    ("Bố cục nội dung", [
        "can_cu", "phan_chuong", "tieu_de_phan_chuong", "muc", "tieu_de_muc",
        "muc_la_ma", "dieu", "khoan", "khoan_co_tieu_de", "diem", "noi_dung",
    ]),
    ("Phần cuối văn bản", [
        "kinh_gui", "kinh_gui_ds", "noi_nhan_tieu_de", "noi_nhan_ds",
        "quyen_han_chuc_vu", "ho_ten_nguoi_ky", "ky_hieu_nguoi_soan",
    ]),
    ("Phụ lục", ["phu_luc_so", "tieu_de_phu_luc"]),
    ("Ô bảng", ["bang_the_thuc"]),
]

_CAN_LE = {"left": "Trái", "center": "Giữa", "right": "Phải", "justify": "Đều hai bên"}
_HOA = {"": "Giữ nguyên", "hoa": "Ép IN HOA", "thuong": "Ép in thường"}
_BA_TRANG_THAI = {"": "Giữ nguyên", "co": "Bật", "khong": "Tắt"}

_CSS = """<style>
.vb-legend span { display:inline-flex; align-items:center; gap:6px; margin-right:18px;
                  font-size:12px; color:#374151; }
.vb-chip { width:14px; height:14px; border-radius:3px; display:inline-block;
           border:1px solid rgba(0,0,0,.15); }
.vb-row  { border-bottom:1px solid #f1f5f9; }
.vb-row:last-child { border-bottom:none; }
</style>"""


def _bool_sang_ma(v) -> str:
    return "" if v is None else ("co" if v else "khong")


def _ma_sang_bool(v: str):
    return None if not v else (v == "co")


@ui.page("/vb_format")
async def vb_format_page():
    if not _require_auth():
        return
    if not api.has_feature("menu.vb_format"):
        ui.navigate.to("/home")
        return

    duoc_sua_cau_hinh = api.has_feature("vb_format.config")

    await _sidebar("vb_format")
    ui.add_head_html(_CSS)

    # Trạng thái dùng chung giữa hai tab
    state: dict = {"file": None, "ten": "", "token": None, "cfg": None, "meta": None}

    with _content_area():
        _page_header(
            "Chuẩn hoá văn bản",
            "Tải file Word lên, phần mềm sửa về đúng thể thức và kỹ thuật trình bày "
            "theo QĐ 979/QyĐ-NHNo-PC và đánh dấu những chỗ đã sửa",
        )

        with ui.tabs().classes("w-full") as tabs:
            tab_chuan = ui.tab("Chuẩn hoá văn bản", icon="auto_fix_high")
            tab_mau = ui.tab("Mẫu trình bày sẵn", icon="library_books")
            tab_cfg = ui.tab("Cấu hình quy chuẩn", icon="tune")

        with ui.tab_panels(tabs, value=tab_chuan).classes("w-full bg-transparent"):

            # ══ TAB 1 — Chuẩn hoá ═══════════════════════════════════════════
            with ui.tab_panel(tab_chuan).classes("p-0 pt-4"):
                with _card("Tải văn bản cần chuẩn hoá"):
                    with ui.column().classes("w-full p-4 gap-2"):
                        ten_label = ui.label("Chưa chọn file").classes(
                            "text-sm text-gray-500 italic")

                        def on_upload(e):
                            state["file"] = e.content.read()
                            state["ten"] = e.name
                            ten_label.set_text(f"Đã chọn: {e.name}")
                            ten_label.classes(remove="text-gray-500 italic",
                                              add="text-green-700 font-medium")

                        uploader = ui.upload(
                            on_upload=on_upload, auto_upload=True, multiple=False,
                        ).props('accept=".docx" flat dense '
                                'label="Chọn file Word (.docx)..."').classes("w-full")

                        ui.label(
                            "Chỉ nhận .docx. File .doc đời cũ cần mở bằng Word rồi "
                            "chọn Lưu thành .docx trước khi tải lên."
                        ).classes("text-xs text-gray-500")

                        with ui.row().classes("items-center gap-2 mt-1"):
                            nut_chay = ui.button("Chuẩn hoá", icon="auto_fix_high").classes(
                                "bg-red-800 text-white")

                            def _xoa():
                                state.update(file=None, ten="", token=None)
                                uploader.reset()
                                ten_label.set_text("Chưa chọn file")
                                ten_label.classes(remove="text-green-700 font-medium",
                                                  add="text-gray-500 italic")
                                ket_qua.clear()

                            ui.button("Chọn file khác", icon="delete_outline", color="grey-6",
                                      on_click=_xoa).props("flat dense").classes("text-xs")

                ket_qua = ui.column().classes("w-full mt-4")

                def _ve_bao_cao(bc: dict):
                    ket_qua.clear()
                    tk = bc["thong_ke"]
                    with ket_qua:
                        # ── Tóm tắt + nút tải ──
                        with _card("Kết quả"):
                            with ui.column().classes("w-full p-4 gap-3"):
                                with ui.row().classes("items-center gap-6 flex-wrap"):
                                    for nhan, so in (("Đoạn đọc được", tk["tong_doan"]),
                                                     ("Đoạn đã sửa", tk["doan_da_sua"])):
                                        with ui.column().classes("gap-0"):
                                            ui.label(str(so)).classes(
                                                "text-2xl font-bold text-red-900")
                                            ui.label(nhan).classes("text-xs text-gray-500")

                                    async def _tai():
                                        try:
                                            data = await asyncio.to_thread(
                                                api.get_bytes,
                                                f"/api/vb-format/tai-ve/{bc['token']}")
                                        except Exception as ex:
                                            if _handle_api_error(ex):
                                                return
                                            ui.notify(str(ex), type="negative")
                                            return
                                        ui.download(data, filename=bc["ten_file"])

                                    ui.button("Tải văn bản đã chuẩn hoá",
                                              icon="download", on_click=_tai).classes(
                                        "bg-green-700 text-white ml-auto")

                                ui.html(
                                    '<div class="vb-legend">'
                                    '<span><i class="vb-chip" style="background:#ffff00"></i>'
                                    'Sửa định dạng riêng của đoạn (cỡ chữ, đậm/nghiêng, căn lề)</span>'
                                    '<span><i class="vb-chip" style="background:#00ff00"></i>'
                                    'Sửa chữ (viết hoa, đánh số, gạch đầu dòng)</span>'
                                    '<span><i class="vb-chip" style="background:#40e0d0"></i>'
                                    'Cụm từ được ghép không cho tách dòng</span></div>'
                                )

                        # ── Lưu ý ──
                        if bc["luu_y"]:
                            with ui.column().classes(
                                "w-full mt-4 gap-1 bg-amber-50 border border-amber-300 "
                                "rounded-lg p-3"
                            ):
                                with ui.row().classes("items-center gap-1"):
                                    ui.icon("warning_amber").classes("text-amber-700")
                                    ui.label("Phần mềm cố ý KHÔNG sửa").classes(
                                        "font-semibold text-amber-900 text-sm")
                                for w in bc["luu_y"]:
                                    ui.label("• " + w).classes("text-xs text-amber-900")

                        # ── Sửa chung ──
                        if bc["sua_chung"]:
                            with _card("Sửa chung cho cả văn bản (không bôi màu)"):
                                with ui.column().classes("w-full p-4 gap-1"):
                                    ui.label(
                                        "Những mục dưới đây gần như đoạn nào cũng phải sửa "
                                        "nên không bôi màu — bôi hết thì cả trang vàng khè, "
                                        "không còn nhìn ra chỗ nào đáng chú ý."
                                    ).classes("text-xs text-gray-500 mb-1")
                                    for m in bc["sua_chung"]:
                                        ui.label("• " + m).classes("text-sm text-gray-700")

                        # ── Bảng đoạn ──
                        with _card(f"Chi tiết {len(bc['doan'])} đoạn đã sửa"):
                            if not bc["doan"]:
                                ui.label("Văn bản đã đúng quy chuẩn — không có đoạn nào "
                                         "phải sửa riêng.").classes("text-sm text-gray-500 p-4")
                            else:
                                ui.table(
                                    columns=[
                                        {"name": "stt", "label": "Đoạn", "field": "stt",
                                         "align": "right", "sortable": True},
                                        {"name": "nhan", "label": "Thành phần thể thức",
                                         "field": "nhan", "align": "left"},
                                        {"name": "trich", "label": "Trích nội dung",
                                         "field": "trich", "align": "left"},
                                        {"name": "viec", "label": "Đã sửa",
                                         "field": "viec", "align": "left"},
                                    ],
                                    rows=[{"stt": d["stt"], "nhan": d["nhan"],
                                           "trich": d["trich"],
                                           "viec": ", ".join(d["viec"])} for d in bc["doan"]],
                                    row_key="stt", pagination=25,
                                ).classes("w-full").props("flat dense wrap-cells")

                async def do_chuan_hoa():
                    if not state["file"]:
                        ui.notify("Vui lòng chọn một file Word (.docx)", type="warning")
                        return
                    nut_chay.props("loading disable")
                    ket_qua.clear()
                    try:
                        bc = await asyncio.to_thread(
                            api.post_upload, "/api/vb-format/chuan-hoa",
                            {"file": (state["ten"], state["file"], _DOCX_MIME)},
                            None, 180.0,
                        )
                    except Exception as ex:
                        if _handle_api_error(ex):
                            return
                        ui.notify(str(ex), type="negative", timeout=9000)
                        return
                    finally:
                        nut_chay.props(remove="loading disable")
                    state["token"] = bc["token"]
                    _ve_bao_cao(bc)
                    ui.notify(
                        f"Đã chuẩn hoá: sửa {bc['thong_ke']['doan_da_sua']}"
                        f"/{bc['thong_ke']['tong_doan']} đoạn", type="positive")

                nut_chay.on_click(do_chuan_hoa)

            # ══ TAB 2 — Mẫu trình bày sẵn ═══════════════════════════════════
            with ui.tab_panel(tab_mau).classes("p-0 pt-4"):
                with _card("18 mẫu trình bày theo Phụ lục V"):
                    with ui.column().classes("w-full p-4 gap-3"):
                        ui.label(
                            "Bản trắng của 18 mẫu trong Phụ lục V — tải về rồi điền nội "
                            "dung vào là văn bản đã đúng thể thức ngay từ đầu. Lề trang "
                            "đã đặt về đúng quy chuẩn (20/20/30/20 mm); phần Ghi chú của "
                            "Phụ lục được giữ nguyên, xoá đi trước khi phát hành."
                        ).classes("text-sm text-gray-600")
                        khung_mau = ui.column().classes("w-full gap-0")
                        with khung_mau:
                            ui.spinner(size="2em", color="red")

                async def _tai_mau(m: dict):
                    try:
                        data = await asyncio.to_thread(
                            api.get_bytes, f"/api/vb-format/mau/{m['so']}")
                    except Exception as ex:
                        if _handle_api_error(ex):
                            return
                        ui.notify(str(ex), type="negative")
                        return
                    ui.download(data, filename=f"Mau {m['so']:02d} - {m['ten']}.docx")

                def _ve_mau(ds: list):
                    khung_mau.clear()
                    with khung_mau:
                        if not ds:
                            ui.label(
                                "Chưa có mẫu nào trên máy chủ — người quản trị cần chạy "
                                "scripts/tach_mau_vb.py rồi triển khai lại."
                            ).classes("text-sm text-red-700")
                            return
                        for m in ds:
                            with ui.row().classes(
                                    "vb-row w-full items-center gap-3 py-2 px-1"):
                                ui.label(f"{m['so']:02d}").classes(
                                    "w-8 text-center text-sm font-semibold text-red-900")
                                ui.label(m["ten"]).classes("text-sm flex-grow")
                                # Truyền thẳng coroutine, KHÔNG bọc create_task —
                                # xem mục "Event handler async" trong docs/DESIGN.md.
                                ui.button("Tải mẫu", icon="download",
                                          on_click=lambda m=m: _tai_mau(m)).props(
                                    "flat dense").classes("text-red-800")

                async def _nap_mau():
                    try:
                        ds = await asyncio.to_thread(api.get, "/api/vb-format/mau")
                    except Exception as ex:
                        khung_mau.clear()
                        if _handle_api_error(ex):
                            return
                        with khung_mau:
                            ui.label("Không tải được danh sách mẫu.").classes(
                                "text-sm text-red-700")
                        return
                    _ve_mau(ds)

            # ══ TAB 3 — Cấu hình ════════════════════════════════════════════
            with ui.tab_panel(tab_cfg).classes("p-0 pt-4"):
                khung_cfg = ui.column().classes("w-full gap-4")
                with khung_cfg:
                    ui.spinner(size="2em", color="red")

                # Widget của form, gom theo đường dẫn khoá để lúc Lưu chỉ việc đọc
                w: dict = {}

                def _o_so(nhom: str, khoa: str, nhan: str, cfg: dict, hau_to="",
                          buoc=0.5, rong="w-40"):
                    o = ui.number(label=nhan, value=cfg[nhom][khoa], step=buoc,
                                  format="%g").props("dense outlined").classes(rong)
                    if hau_to:
                        o.props(f'suffix="{hau_to}"')
                    w[(nhom, khoa)] = o
                    return o

                def _o_bat(nhom: str, khoa: str, nhan: str, cfg: dict):
                    o = ui.switch(nhan, value=bool(cfg[nhom][khoa])).props("dense")
                    w[(nhom, khoa)] = o
                    return o

                def _ve_thanh_phan(ma: str, cfg: dict, meta: dict):
                    tp = cfg["thanh_phan"][ma]
                    dai = meta["dai_co_chu"].get(ma)
                    with ui.row().classes("vb-row w-full items-center gap-2 py-1.5 flex-wrap"):
                        ui.label(meta["nhan"].get(ma, ma)).classes(
                            "text-sm text-gray-800 w-72 shrink-0")

                        o_co = ui.number(label="Cỡ chữ", value=tp["co"], step=1,
                                         format="%g").props("dense outlined").classes("w-24")
                        canh_bao = ui.icon("warning_amber").classes("text-amber-600")
                        canh_bao.set_visibility(False)

                        def _kiem(_=None, o=o_co, cb=canh_bao, d=dai):
                            # Cảnh báo chứ KHÔNG chặn: quy định cho một dải cỡ chữ
                            # khuyến nghị, đơn vị vẫn có thể có lý do đi ra ngoài dải.
                            if not d or o.value is None:
                                cb.set_visibility(False)
                                return
                            ngoai = not (d[0] <= float(o.value) <= d[1])
                            cb.set_visibility(ngoai)
                            if ngoai:
                                cb.tooltip(f"QĐ 979 quy định cỡ chữ {_g(d[0])}–{_g(d[1])}")
                        o_co.on_value_change(_kiem)
                        _kiem()

                        o_dam = ui.select(_BA_TRANG_THAI, value=_bool_sang_ma(tp["dam"]),
                                          label="Đậm").props("dense outlined").classes("w-32")
                        o_ngh = ui.select(_BA_TRANG_THAI, value=_bool_sang_ma(tp["nghieng"]),
                                          label="Nghiêng").props("dense outlined").classes("w-32")
                        o_hoa = ui.select(_HOA, value=tp["hoa"] or "",
                                          label="Hoa/thường").props("dense outlined").classes("w-36")
                        o_can = ui.select({**{"": "Giữ nguyên"}, **_CAN_LE},
                                          value=tp["can"] or "",
                                          label="Căn lề").props("dense outlined").classes("w-36")
                        o_thut = ui.number(label="Thụt dòng đầu", value=tp["thut_cm"],
                                           step=0.1, format="%g").props(
                            'dense outlined clearable suffix="cm"').classes("w-32")
                        o_thut.tooltip("Để trống = không đụng tới thụt dòng đầu")
                        # Lề trái của CẢ đoạn. Trước đây thuộc tính này có
                        # trong quy chuẩn và vẫn được áp lên văn bản, nhưng
                        # không có ô nào trên màn hình — đúng thứ docstring đầu
                        # file dặn phải tránh: một luật sửa văn bản mà người
                        # dùng không có cách nào nhìn thấy hay tắt đi.
                        o_le = ui.number(label="Lề trái đoạn",
                                         value=tp.get("le_trai_cm"),
                                         step=0.5, format="%g").props(
                            'dense outlined clearable suffix="cm"').classes("w-32")
                        o_le.tooltip("Để trống = không đụng tới lề trái của đoạn")
                        # Để TRỐNG = theo giá trị chung của cả văn bản. Khối thể
                        # thức đầu và cuối trang khai riêng dòng đơn / 0pt vì
                        # Điều 7.3 và 8.2 đòi chúng "cách nhau dòng đơn".
                        o_gd = ui.number(label="Giãn dòng riêng", value=tp.get("gian_dong"),
                                         step=0.05, format="%g").props(
                            "dense outlined clearable").classes("w-36")
                        o_gd.tooltip("Để trống = theo giãn dòng chung của cả văn bản")
                        o_cd = ui.number(label="Cách đoạn riêng", value=tp.get("cach_doan_pt"),
                                         step=1, format="%g").props(
                            'dense outlined clearable suffix="pt"').classes("w-36")
                        o_cd.tooltip("Để trống = theo cách đoạn chung của cả văn bản")
                        w[("thanh_phan", ma)] = (o_co, o_dam, o_ngh, o_hoa, o_can,
                                                 o_thut, o_le, o_gd, o_cd)

                def _g(v) -> str:
                    f = float(v)
                    return str(int(f)) if f == int(f) else f"{f:g}"

                def _ve_cau_hinh(cfg: dict, meta: dict):
                    khung_cfg.clear()
                    with khung_cfg:
                        if not duoc_sua_cau_hinh:
                            with ui.row().classes(
                                "w-full items-center gap-2 bg-blue-50 border "
                                "border-blue-200 rounded-lg p-3"
                            ):
                                ui.icon("lock").classes("text-blue-700")
                                ui.label(
                                    "Bạn chỉ được xem thông số. Liên hệ quản trị viên để "
                                    "được cấp quyền «Sửa thông số quy chuẩn trình bày»."
                                ).classes("text-sm text-blue-900")

                        if meta.get("cap_nhat_luc"):
                            ui.label(
                                f"Lần sửa gần nhất: {meta['cap_nhat_luc']}"
                                + (f" — {meta['cap_nhat_boi']}" if meta.get("cap_nhat_boi") else "")
                            ).classes("text-xs text-gray-500")

                        # ── Khổ giấy và lề ──
                        with _card("Khổ giấy và định lề (Điều 4)"):
                            with ui.column().classes("w-full p-4 gap-3"):
                                _o_bat("trang", "ap_dung", "Đặt lại khổ giấy và lề trang", cfg)
                                with ui.row().classes("gap-3 flex-wrap"):
                                    _o_so("trang", "le_tren_mm", "Lề trên", cfg, "mm")
                                    _o_so("trang", "le_duoi_mm", "Lề dưới", cfg, "mm")
                                    _o_so("trang", "le_trai_mm", "Lề trái", cfg, "mm")
                                    _o_so("trang", "le_phai_mm", "Lề phải", cfg, "mm")
                                ui.label(
                                    "QĐ 979: trên/dưới 20–25 mm, trái 30–35 mm, phải 15–20 mm."
                                ).classes("text-xs text-gray-500")
                                with ui.row().classes("gap-4 items-center flex-wrap"):
                                    _o_bat("trang", "danh_so_trang",
                                           "Đánh số trang (canh giữa lề trên, bỏ trang 1)", cfg)
                                    _o_so("trang", "co_so_trang", "Cỡ chữ số trang", cfg, "pt",
                                          1, "w-36")

                        # ── Định dạng chung ──
                        with _card("Phông chữ và lời văn (Điều 5, Điều 12)"):
                            with ui.column().classes("w-full p-4 gap-3"):
                                with ui.row().classes("gap-3 flex-wrap items-center"):
                                    o = ui.input(label="Phông chữ",
                                                 value=cfg["chung"]["phong_chu"]).props(
                                        "dense outlined").classes("w-56")
                                    w[("chung", "phong_chu")] = o
                                    _o_so("chung", "gian_dong", "Giãn dòng", cfg, "", 0.05)
                                    _o_so("chung", "cach_doan_pt", "Cách đoạn", cfg, "pt", 1)
                                with ui.row().classes("gap-4 flex-wrap"):
                                    _o_bat("chung", "ep_phong_chu",
                                           "Ép phông chữ cho toàn văn bản", cfg)
                                    _o_bat("chung", "ep_mau_den", "Ép màu chữ về đen", cfg)
                                    _o_bat("chung", "chuan_tieu_ngu",
                                           "Chuẩn hoá Tiêu ngữ («Độc lập - Tự do - Hạnh phúc»)",
                                           cfg)
                                    _o_bat("chung", "bo_khoang_truoc_doan",
                                           "Bỏ khoảng trống trước đoạn (Spacing Before → 0)", cfg)
                                with ui.row().classes("gap-4 flex-wrap items-center"):
                                    _o_bat("chung", "nen_chu_cho_vua_dong",
                                           "Nén chữ cho dòng thể thức vừa một dòng", cfg)
                                    _o_so("chung", "nen_toi_da_twip",
                                          "Nén tối đa", cfg, "twip", 1)
                                    _o_bat("chung", "go_gach_chan_the_thuc",
                                           "Bỏ gạch chân ở dòng thể thức", cfg)
                                    _o_bat("chung", "ve_duong_ke_ngang",
                                           "Vẽ đường kẻ ngang dưới Tiêu ngữ / tên đơn vị / trích yếu",
                                           cfg)
                                    _o_bat("chung", "bo_ngat_trang_thu_cong",
                                           "Bỏ ngắt trang thủ công", cfg)
                                ui.label(
                                    "Ngắt trang tay được đặt theo bố cục CŨ. Chuẩn hoá làm chữ "
                                    "cao lên nên chỗ xuống trang dịch đi, giữ lại thì hay đẻ ra "
                                    "một trang gần như trống. Tắt ô này khi văn bản thật sự cần "
                                    "sang trang mới — Phụ lục ban hành kèm theo Quyết định."
                                ).classes("text-xs text-gray-500")
                                ui.label(
                                    "Điều 12.6 cho một dải: giãn dòng tối thiểu dòng đơn (1), "
                                    "tối đa 1,5; cách đoạn tối thiểu 6 pt. Mặc định lấy 1,2 vì "
                                    "đó là con số dùng trong chính lời văn của QĐ 979."
                                ).classes("text-xs text-gray-500")
                                ui.label(
                                    "Hai số này áp cho LỜI VĂN. Khối thể thức đầu và cuối trang "
                                    "(Quốc hiệu, Tiêu ngữ, tên đơn vị, Nơi nhận, người ký) có "
                                    "giãn dòng riêng là dòng đơn và không cách đoạn — Điều 7.3 "
                                    "và 8.2 đòi chúng «trình bày cách nhau dòng đơn». Sửa được "
                                    "ở hai cột cuối của bảng thành phần thể thức bên dưới."
                                ).classes("text-xs text-gray-500")

                        # ── 28 thành phần thể thức ──
                        with _card("Cỡ chữ và kiểu chữ từng thành phần thể thức (Phụ lục III)"):
                            with ui.column().classes("w-full p-4 gap-2"):
                                ui.label(
                                    "«Giữ nguyên» nghĩa là phần mềm không đụng tới thuộc "
                                    "tính đó — dùng khi người soạn cần tự quyết."
                                ).classes("text-xs text-gray-500")
                                for ten_nhom, danh_sach in _NHOM:
                                    with ui.expansion(ten_nhom).classes(
                                        "w-full border border-gray-200 rounded-lg"
                                    ).props("dense header-class=font-semibold"):
                                        for ma in danh_sach:
                                            if ma in cfg["thanh_phan"]:
                                                _ve_thanh_phan(ma, cfg, meta)

                        # ── Cụm từ liền dòng ──
                        with _card("Cụm từ không được tách qua hai dòng"):
                            with ui.column().classes("w-full p-4 gap-2"):
                                _o_bat("lien_dong", "ap_dung",
                                       "Ghép các cụm từ dưới đây cho luôn nằm cùng một dòng", cfg)
                                o = ui.textarea(
                                    label="Mỗi dòng một cụm từ",
                                    value="\n".join(cfg["lien_dong"]["cum_tu"]),
                                ).props("dense outlined autogrow").classes("w-full")
                                w[("lien_dong", "cum_tu")] = o
                                ui.label(
                                    "Ví dụ «Tổng Giám đốc» sẽ không bao giờ bị Word ngắt "
                                    "thành «Tổng» ở cuối dòng và «Giám đốc» ở dòng dưới. "
                                    "Chỉ nên khai cụm NGẮN: một cụm dài bị ghim liền dòng "
                                    "sẽ đẩy cả khối xuống dòng dưới và để lại khoảng trống "
                                    "dài ở dòng trên."
                                ).classes("text-xs text-gray-500")

                        # ── Viết hoa ──
                        with _card("Viết hoa (Phụ lục IV)"):
                            with ui.column().classes("w-full p-4 gap-2"):
                                _o_bat("viet_hoa", "dau_cau",
                                       "Viết hoa chữ đầu câu và đầu dòng", cfg)
                                _o_bat("viet_hoa", "vien_dan",
                                       "Viện dẫn: Phần/Chương/Mục/Tiểu mục/Điều viết hoa, "
                                       "khoản và điểm viết thường", cfg)
                                _o_bat("viet_hoa", "tu_dien",
                                       "Sửa hoa/thường theo từ điển cụm từ dưới đây", cfg)
                                o = ui.textarea(
                                    label="Từ điển cụm từ — mỗi dòng một cụm, gõ đúng dạng cần có",
                                    value="\n".join(cfg["viet_hoa"]["cum_tu"]),
                                ).props("dense outlined autogrow").classes("w-full")
                                w[("viet_hoa", "cum_tu")] = o
                                ui.label(
                                    "Phụ lục IV phần lớn đòi hiểu ngữ cảnh (tên người, tên "
                                    "địa lý, tên sự kiện) — máy không đoán được nên chỉ sửa "
                                    "những cụm khai ở đây. Cụm đang viết HOA TOÀN BỘ được bỏ "
                                    "qua để không phá tên đơn vị trên đầu văn bản."
                                ).classes("text-xs text-gray-500")

                        # ── Đánh số ──
                        with _card("Đánh số và gạch đầu dòng"):
                            with ui.column().classes("w-full p-4 gap-2"):
                                with ui.row().classes("items-center gap-3"):
                                    _o_bat("danh_so", "gach_dau_dong",
                                           "Chuẩn hoá mọi ký tự gạch đầu dòng", cfg)
                                    o = ui.input(label="Ký tự dùng",
                                                 value=cfg["danh_so"]["ky_tu_gach"]).props(
                                        "dense outlined").classes("w-28")
                                    w[("danh_so", "ky_tu_gach")] = o
                                    o2 = ui.input(label="Ký tự mục con",
                                                  value=cfg["danh_so"].get(
                                                      "ky_tu_gach_cap2", "+")).props(
                                        "dense outlined").classes("w-28")
                                    w[("danh_so", "ky_tu_gach_cap2")] = o2
                                with ui.row().classes("items-center gap-3 flex-wrap"):
                                    _o_bat("chung", "phan_cap_gach_dau_dong",
                                           "Tự nhận mục con (dòng kết thúc bằng «:» mở "
                                           "danh sách con)", cfg)
                                    _o_so("chung", "thut_muc_con_cm",
                                          "Thụt mỗi cấp", cfg, "cm", 0.5)
                                    _o_bat("chung", "giu_thut_muc_con",
                                           "Giữ thụt lề mục con tác giả đã tự đặt", cfg)
                                ui.label(
                                    "QĐ 979 chỉ đánh số tới cấp «điểm» (a, b, c) — dưới đó "
                                    "không có cấp nào được quy định, nên đây là thói quen "
                                    "trình bày, không phải điều khoản. Danh sách con đóng lại "
                                    "ở dòng kết thúc bằng dấu chấm (khi các dòng trên đã dùng "
                                    "dấu chấm phẩy), hoặc ở dòng đầu tiên không phải gạch đầu dòng."
                                ).classes("text-xs text-gray-500")
                                _o_bat("danh_so", "chuan_khoan_diem",
                                       "Chuẩn hoá số khoản «1)» «1/» → «1.» và điểm «a.» «a/» → «a)»",
                                       cfg)
                                _o_bat("danh_so", "chuan_muc_la_ma",
                                       "Chuẩn hoá mục La Mã «I)» «I/» → «I.»", cfg)
                                _o_bat("danh_so", "bo_bullet_tu_dong",
                                       "Chuyển danh sách chấm tròn tự động của Word thành "
                                       "gạch đầu dòng gõ tay", cfg)
                                _o_bat("danh_so", "bo_so_tu_dong",
                                       "Chuyển danh sách ĐÁNH SỐ tự động của Word thành số gõ tay",
                                       cfg)
                                ui.label(
                                    "Mục cuối để TẮT: số của danh sách đánh số tự động do Word "
                                    "tính lúc hiển thị, không nằm trong file dưới dạng chữ nên "
                                    "phần mềm phải tự đếm lại — lệch một chỗ là sai số cả văn "
                                    "bản mà không có gì báo. Cách chắc chắn là gõ số thẳng vào "
                                    "dòng rồi tắt đánh số tự động trong Word."
                                ).classes("text-xs text-gray-500")

                        # ── Đánh dấu ──
                        with _card("Đánh dấu vùng đã sửa"):
                            with ui.column().classes("w-full p-4 gap-3"):
                                _o_bat("danh_dau", "bat", "Bôi màu những chỗ đã sửa", cfg)
                                with ui.row().classes("gap-3 flex-wrap"):
                                    for khoa, nhan in (
                                        ("mau_dinh_dang", "Màu cho sửa định dạng"),
                                        ("mau_noi_dung", "Màu cho sửa chữ"),
                                        ("mau_lien_dong", "Màu cho cụm từ liền dòng"),
                                    ):
                                        o = ui.select(meta["mau_danh_dau"],
                                                      value=cfg["danh_dau"][khoa],
                                                      label=nhan).props(
                                            "dense outlined").classes("w-52")
                                        w[("danh_dau", khoa)] = o
                                _o_bat("danh_dau", "xoa_danh_dau_cu",
                                       "Gỡ mọi highlight sẵn có trong file trước khi chạy", cfg)
                                ui.label(
                                    "Bật mục cuối khi chạy lại một file đã chuẩn hoá lần "
                                    "trước — nếu không, màu của lần trước còn nguyên và "
                                    "không phân biệt được với lần này. Lưu ý: nó gỡ CẢ "
                                    "highlight do người soạn tự bôi."
                                ).classes("text-xs text-gray-500")

                        # ── Nút ──
                        with ui.row().classes("w-full justify-end gap-2 pb-4"):
                            nut_mac_dinh = ui.button(
                                "Khôi phục mặc định theo QĐ 979", icon="restart_alt",
                                color="grey-7").props("outline")
                            nut_luu = ui.button("Lưu thông số", icon="save").classes(
                                "bg-red-800 text-white")
                            if not duoc_sua_cau_hinh:
                                nut_luu.props("disable")
                                nut_mac_dinh.props("disable")
                            nut_luu.on_click(lambda: _luu())
                            nut_mac_dinh.on_click(lambda: _mac_dinh())

                    # ── Không có quyền sửa: khoá MỌI ô nhập, không chỉ hai nút ──
                    # Khoá mỗi nút thì gần 200 ô vẫn gõ được: người dùng chỉnh cả
                    # loạt thông số, thấy số đổi ngay trên màn hình và tin là đã
                    # sửa xong — tới lúc bấm Lưu (đang xám) mới biết là không.
                    # Backend vẫn trả 403 nên dữ liệu không hề đổi, nhưng công
                    # chỉnh tay thì mất và người dùng có lý do nghĩ phần mềm hỏng.
                    #
                    # Khoá ở đây, SAU khi dựng xong toàn bộ, chứ không truyền cờ
                    # vào từng chỗ tạo widget: thêm một ô mới mà quên truyền cờ là
                    # thủng đúng một chỗ, và không có gì báo.
                    if not duoc_sua_cau_hinh:
                        for o in w.values():
                            for e in (o if isinstance(o, tuple) else (o,)):
                                e.disable()

                def _thu_thap() -> dict:
                    """Đọc ngược mọi widget về đúng cấu trúc cấu hình."""
                    cfg = {"trang": {}, "chung": {}, "thanh_phan": {}, "lien_dong": {},
                           "viet_hoa": {}, "danh_so": {}, "danh_dau": {}}
                    for khoa, o in w.items():
                        nhom, ten = khoa
                        if nhom == "thanh_phan":
                            (o_co, o_dam, o_ngh, o_hoa, o_can, o_thut, o_le,
                             o_gd, o_cd) = o
                            cfg["thanh_phan"][ten] = {
                                "co": o_co.value,
                                "dam": _ma_sang_bool(o_dam.value),
                                "nghieng": _ma_sang_bool(o_ngh.value),
                                "hoa": o_hoa.value or None,
                                "can": o_can.value or None,
                                "thut_cm": o_thut.value,
                                "le_trai_cm": o_le.value,
                                # Ô trống → None → thành phần này đi theo giá trị
                                # chung. Không đổi 0 thành None: 0 pt là một lựa
                                # chọn có thật (khối đầu trang không cách đoạn).
                                "gian_dong": o_gd.value,
                                "cach_doan_pt": o_cd.value,
                            }
                        elif ten == "cum_tu":
                            cfg[nhom][ten] = [d.strip() for d in (o.value or "").splitlines()
                                              if d.strip()]
                        else:
                            cfg[nhom][ten] = o.value
                    return cfg

                async def _luu():
                    try:
                        res = await asyncio.to_thread(
                            api.put, "/api/vb-format/cau-hinh", _thu_thap())
                    except Exception as ex:
                        if _handle_api_error(ex):
                            return
                        ui.notify(str(ex), type="negative")
                        return
                    state["cfg"] = res["cau_hinh"]
                    ui.notify("Đã lưu thông số quy chuẩn", type="positive")

                async def _mac_dinh():
                    try:
                        res = await asyncio.to_thread(
                            api.post, "/api/vb-format/cau-hinh/mac-dinh")
                    except Exception as ex:
                        if _handle_api_error(ex):
                            return
                        ui.notify(str(ex), type="negative")
                        return
                    w.clear()
                    state["cfg"] = res["cau_hinh"]
                    _ve_cau_hinh(res["cau_hinh"], state["meta"])
                    ui.notify("Đã khôi phục quy chuẩn mặc định theo QĐ 979", type="positive")

                async def _nap():
                    try:
                        res = await asyncio.to_thread(api.get, "/api/vb-format/cau-hinh")
                    except Exception as ex:
                        khung_cfg.clear()
                        if _handle_api_error(ex):
                            return
                        with khung_cfg:
                            ui.label("Không tải được cấu hình.").classes("text-sm text-red-700")
                        return
                    state["cfg"] = res["cau_hinh"]
                    state["meta"] = res
                    _ve_cau_hinh(res["cau_hinh"], res)

                # Tuần tự, KHÔNG asyncio.gather: gather bọc mỗi coroutine
                # thành task mới, mà hai hàm này có gọi `_handle_api_error()`
                # → `ui.navigate.to()` trong task rời sẽ ném "slot stack empty"
                # và rơi vào handler toàn cục — màn hình đứng im, không báo gì.
                # Hai request đều nhỏ, chạy nối nhau không đáng kể.
                await _nap()
                await _nap_mau()
