"""Danh sách CN thực hiện TTQT — tra cứu, thêm/sửa/xoá, nhập & xuất Excel."""
import asyncio
from datetime import date

from nicegui import ui

import frontend.api_client as api
from frontend.shared import _sidebar, _content_area, _page_header, _require_auth, _handle_api_error

_CSS = """<style>
/* Cột địa chỉ / ghi chú dài — bắt buộc cho xuống dòng, nếu không Quasar kéo
   bảng rộng ra vài nghìn pixel và cả trang phải cuộn ngang. */
.ttqt-table td { white-space: normal !important; vertical-align: top; }

/* Chỉ THÂN bảng cuộn, thanh lọc phía trên không trôi đi.
   Không dùng position:sticky cho thanh lọc: #app-content có overflow-x:auto
   nên trục dọc cũng thành auto — sticky sẽ neo vào hộp đó, mà hộp đó không tự
   cuộn, kết quả là thanh lọc vẫn trôi theo trang. Giới hạn chiều cao thân bảng
   thì cả trang vừa đúng một màn hình, không có gì để trôi.
   Số 290px chỉ là mức dự phòng — JS bên dưới đo lại theo vị trí thật. */
.ttqt-table .q-table__middle { max-height: calc(100vh - 290px); }
.ttqt-table thead th {
  position: sticky; top: 0; z-index: 2;
  background: #fef2f2; color: #7f1d1d; font-weight: 600;
}
.ttqt-table .q-table__top, .ttqt-table .q-table__bottom { padding: 2px 8px; min-height: 0; }

/* Ô chọn file: thu về cỡ một nút thường, bỏ thanh tiến trình và danh sách file */
.ttqt-upload .q-uploader { width: auto; min-width: 0; box-shadow: none; background: transparent; }
.ttqt-upload .q-uploader__header { min-height: 30px; border-radius: 6px; background: #15803d; }
.ttqt-upload .q-uploader__header-content { padding: 2px 10px; min-height: 30px; }
.ttqt-upload .q-uploader__title { font-size: 12px; font-weight: 500; line-height: 1.3; }
.ttqt-upload .q-uploader__subtitle, .ttqt-upload .q-uploader__list { display: none; }

/* Bảng lịch sử: giá trị cũ/mới có thể dài cả địa chỉ — cho xuống dòng, và
   giới hạn chiều cao để hộp thoại không tràn khỏi màn hình. */
.ttqt-hist td { white-space: normal !important; vertical-align: top; font-size: 12px; }
.ttqt-hist .q-table__middle { max-height: 60vh; }
.ttqt-hist thead th { position: sticky; top: 0; z-index: 2; background: #f3f4f6; font-weight: 600; }
</style>
<script>
/* Đo lại chiều cao thân bảng theo vị trí thật của nó trong khung nhìn.
   Cần thiết vì trên màn hẹp (máy trạm 1366px) thanh lọc xuống 2 dòng — chiều
   cao trừ cứng trong CSS sẽ dư ra và cả trang lại cuộn được, đúng thứ cần tránh. */
(function () {
  var pending = false;
  function fit() {
    pending = false;
    document.querySelectorAll('.ttqt-table .q-table__middle').forEach(function (m) {
      var h = window.innerHeight - m.getBoundingClientRect().top - 24;
      if (h > 160) m.style.maxHeight = h + 'px';
    });
  }
  function schedule() {           // gộp nhiều thay đổi DOM liên tiếp vào 1 lần đo
    if (pending) return;
    pending = true;
    requestAnimationFrame(fit);
  }
  window.addEventListener('resize', schedule);
  document.addEventListener('DOMContentLoaded', function () {
    schedule();
    new MutationObserver(schedule).observe(document.body, {childList: true, subtree: true});
  });
})();
</script>"""

_STATUS_OPTS = {"active": "Đang hoạt động", "closed": "Đã đóng BIC", "all": "Tất cả"}
_LOAI_OPTS = {0: "Tất cả loại", 1: "Loại 1", 2: "Loại 2"}

_COLUMNS = [
    {"name": "ma_cn",      "label": "Mã CN",   "field": "ma_cn",      "align": "left",  "sortable": True,
     "style": "width:80px"},
    {"name": "ten_cn",     "label": "Tên CN",  "field": "ten_cn",     "align": "left",  "sortable": True,
     "style": "min-width:150px"},
    {"name": "swift_bic",  "label": "SWIFT BIC", "field": "swift_bic", "align": "left", "sortable": True,
     "style": "width:120px"},
    {"name": "loai_cn",    "label": "Loại",    "field": "loai_cn_txt", "align": "center", "sortable": True,
     "style": "width:70px"},
    {"name": "duoc_phep",  "label": "Được phép", "field": "duoc_phep", "align": "left",
     "style": "width:110px"},
    {"name": "cn_quan_ly", "label": "CN loại I quản lý", "field": "cn_quan_ly", "align": "left",
     "style": "width:130px"},
    {"name": "sdt",        "label": "SĐT",     "field": "sdt",        "align": "left",
     "style": "width:130px"},
    {"name": "dia_chi",    "label": "Địa chỉ", "field": "dia_chi",    "align": "left",
     "style": "min-width:220px;max-width:320px"},
    {"name": "ghi_chu",    "label": "Ghi chú", "field": "ghi_chu",    "align": "left",
     "style": "min-width:180px;max-width:280px"},
    {"name": "actions",    "label": "", "field": "actions", "align": "center", "style": "width:110px"},
]


_HIST_COLUMNS = [
    {"name": "thoi_diem", "label": "Thời điểm", "field": "thoi_diem", "align": "left",
     "style": "width:130px"},
    {"name": "nguoi_sua", "label": "Người sửa", "field": "nguoi_sua", "align": "left",
     "style": "width:150px"},
    {"name": "thao_tac",  "label": "Thao tác",  "field": "thao_tac",  "align": "left",
     "style": "width:90px"},
    {"name": "noi_dung",  "label": "Sửa mục",   "field": "noi_dung",  "align": "left",
     "style": "width:150px"},
    {"name": "gia_tri_cu", "label": "Giá trị cũ", "field": "gia_tri_cu", "align": "left",
     "style": "min-width:180px"},
    {"name": "gia_tri_moi", "label": "Giá trị mới", "field": "gia_tri_moi", "align": "left",
     "style": "min-width:180px"},
]


def _fmt_dt(v: str) -> str:
    """'2026-09-04 08:15:23.4' → '04/09/2026 08:15'. Chuỗi lạ thì trả nguyên
    văn — thà hiện hơi xấu còn hơn nuốt mất thời điểm."""
    if not v:
        return "—"
    try:
        d, t = str(v).split(" ")[0], str(v).split(" ")[1]
        y, m, dd = d.split("-")
        return f"{dd}/{m}/{y} {t[:5]}"
    except Exception:
        return str(v)


def _to_row(b: dict, can_edit: bool, can_delete: bool, can_history: bool) -> dict:
    """Bản ghi API → dòng bảng. Ô trống hiện '—' cho dễ đọc.
    can_edit/can_delete gắn vào từng dòng vì slot Vue chỉ đọc được props.row."""
    r = {
        "id": b["id"],
        "loai_cn_txt": str(b["loai_cn"]) if b.get("loai_cn") else "—",
        "closed": bool(b.get("is_closed")),
        "can_edit": can_edit,
        "can_delete": can_delete,
        "can_history": can_history,
    }
    for f in ("ma_cn", "ten_cn", "swift_bic", "duoc_phep", "cn_quan_ly", "sdt", "dia_chi", "ghi_chu"):
        r[f] = b.get(f) or "—"
    return r


@ui.page("/ttqt_branches")
async def ttqt_branches_page():
    if not _require_auth():
        return
    if not api.has_feature("menu.ttqt_branches"):
        ui.navigate.to("/home")
        return

    can_create = api.has_feature("ttqt_branches.create")
    can_edit   = api.has_feature("ttqt_branches.edit")
    can_delete = api.has_feature("ttqt_branches.delete")
    can_import = api.has_feature("ttqt_branches.import")
    can_export = api.has_feature("ttqt_branches.export")
    can_history = api.has_feature("ttqt_branches.history")

    await _sidebar("ttqt_branches")
    ui.add_head_html(_CSS)

    with _content_area():
        _page_header("Danh sách CN TTQT", "Chi nhánh thực hiện thanh toán quốc tế trực tiếp")

        cache: list[dict] = []          # bản ghi gốc từ API, dùng lại khi mở form sửa
        edit_target = {"id": None}      # None = đang thêm mới

        # ── Form thêm / sửa ───────────────────────────────────────────────────
        with ui.dialog() as form_dialog, ui.card().classes("w-full max-w-3xl"):
            form_title = ui.label("").classes("text-lg font-bold text-red-900 mb-2")
            with ui.grid(columns=2).classes("w-full gap-3"):
                f_ma      = ui.input("Mã CN *").props("dense outlined")
                f_ten     = ui.input("Tên CN *").props("dense outlined")
                f_bic     = ui.input("SWIFT BIC").props("dense outlined")
                f_loai    = ui.select({None: "—", 1: "Loại 1", 2: "Loại 2"},
                                      label="Loại CN").props("dense outlined")
                f_phep    = ui.input("Được phép").props('dense outlined placeholder="VD: chuyển tiền"')
                f_ql      = ui.input("CN loại I quản lý").props("dense outlined")
                f_sdt     = ui.input("SĐT").props("dense outlined")
                f_closed  = ui.switch("Đã đóng BICCODE")
            f_diachi  = ui.textarea("Địa chỉ").props("dense outlined autogrow").classes("w-full")
            f_diachi_en = ui.textarea("Địa chỉ tiếng Anh").props("dense outlined autogrow").classes("w-full")
            f_ghichu  = ui.textarea("Ghi chú").props("dense outlined autogrow").classes("w-full")

            with ui.row().classes("w-full justify-end gap-2 mt-3"):
                ui.button("Hủy", on_click=form_dialog.close).props("flat").classes("text-gray-600")

                async def do_save():
                    if not f_ma.value or not f_ma.value.strip():
                        ui.notify("Vui lòng nhập Mã CN", type="warning")
                        return
                    if not f_ten.value or not f_ten.value.strip():
                        ui.notify("Vui lòng nhập Tên CN", type="warning")
                        return
                    body = {
                        "ma_cn": f_ma.value.strip(),
                        "ten_cn": f_ten.value.strip(),
                        "swift_bic": f_bic.value or None,
                        "loai_cn": f_loai.value or None,
                        "duoc_phep": f_phep.value or None,
                        "cn_quan_ly": f_ql.value or None,
                        "sdt": f_sdt.value or None,
                        "dia_chi": f_diachi.value or None,
                        "dia_chi_en": f_diachi_en.value or None,
                        "ghi_chu": f_ghichu.value or None,
                        "is_closed": bool(f_closed.value),
                    }
                    try:
                        if edit_target["id"] is None:
                            await asyncio.to_thread(api.post, "/api/ttqt-branches/", body)
                            msg = "Đã thêm chi nhánh"
                        else:
                            await asyncio.to_thread(
                                api.patch, f"/api/ttqt-branches/{edit_target['id']}", body)
                            msg = "Đã lưu thay đổi"
                    except Exception as e:
                        if _handle_api_error(e):
                            return
                        return
                    form_dialog.close()
                    ui.notify(msg, type="positive")
                    await load()

                ui.button("Lưu", icon="save", on_click=do_save).classes("bg-red-700 text-white")

        def open_form(b: dict = None):
            edit_target["id"] = b["id"] if b else None
            form_title.text = "Sửa chi nhánh" if b else "Thêm chi nhánh"
            b = b or {}
            f_ma.set_value(b.get("ma_cn") or "")
            f_ten.set_value(b.get("ten_cn") or "")
            f_bic.set_value(b.get("swift_bic") or "")
            f_loai.set_value(b.get("loai_cn"))
            f_phep.set_value(b.get("duoc_phep") or "")
            f_ql.set_value(b.get("cn_quan_ly") or "")
            f_sdt.set_value(b.get("sdt") or "")
            f_diachi.set_value(b.get("dia_chi") or "")
            f_diachi_en.set_value(b.get("dia_chi_en") or "")
            f_ghichu.set_value(b.get("ghi_chu") or "")
            f_closed.set_value(bool(b.get("is_closed")))
            form_dialog.open()

        # ── Hộp thoại lịch sử sửa đổi ─────────────────────────────────────────
        # Dựng MỘT lần rồi dùng lại: tạo dialog mới trong mỗi lần bấm sẽ để lại
        # dialog cũ trong DOM, mỗi lần mở lại nặng thêm một chút.
        with ui.dialog() as hist_dialog, ui.card().classes("w-full max-w-5xl"):
            hist_title = ui.label("").classes("text-lg font-bold text-red-900")
            hist_sub = ui.label("").classes("text-xs text-gray-500 mb-2")
            hist_area = ui.column().classes("w-full")
            with ui.row().classes("w-full justify-end mt-2"):
                ui.button("Đóng", on_click=hist_dialog.close).props("flat").classes("text-gray-600")

        async def show_history(b: dict):
            hist_title.text = f"Lịch sử sửa đổi — {b['ma_cn']} {b.get('ten_cn') or ''}"
            hist_sub.text = "Đang tải..."
            hist_area.clear()
            hist_dialog.open()
            try:
                data = await asyncio.to_thread(
                    api.get, f"/api/ttqt-branches/{b['id']}/history")
            except Exception as e:
                if _handle_api_error(e):
                    return
                hist_sub.text = ""
                with hist_area:
                    ui.label(str(e)).classes("text-red-600 text-sm py-4")
                return

            hist_sub.text = f"{len(data)} lượt thay đổi được ghi nhận"
            with hist_area:
                if not data:
                    ui.label(
                        "Chưa có thay đổi nào được ghi lại cho chi nhánh này."
                    ).classes("text-gray-500 text-center py-8 w-full")
                    return
                rows = [{
                    "id": h["id"],
                    "thoi_diem": _fmt_dt(h.get("created_at")),
                    "nguoi_sua": h.get("actor_name") or "—",
                    "thao_tac": h.get("action_label") or h.get("action"),
                    # Thêm mới / xoá không gắn với một trường nào — ghi rõ thay
                    # vì để trống, người đọc khỏi tưởng dữ liệu bị mất.
                    "noi_dung": h.get("field_label") or "(cả bản ghi)",
                    "gia_tri_cu": h.get("old_value") or "—",
                    "gia_tri_moi": h.get("new_value") or "—",
                } for h in data]
                ui.table(columns=_HIST_COLUMNS, rows=rows, row_key="id",
                         pagination={"rowsPerPage": 0}).props(
                    'bordered dense flat separator="cell"'
                ).classes("w-full ttqt-hist")

        async def do_delete(b: dict):
            with ui.dialog() as confirm, ui.card():
                ui.label(f"Xoá chi nhánh {b['ma_cn']} — {b['ten_cn']}?").classes("font-semibold")
                ui.label("Thao tác này không hoàn tác được.").classes("text-sm text-gray-500")
                with ui.row().classes("w-full justify-end gap-2 mt-3"):
                    ui.button("Hủy", on_click=lambda: confirm.submit(False)).props("flat")
                    ui.button("Xoá", on_click=lambda: confirm.submit(True)).classes("bg-red-700 text-white")
            if not await confirm:
                return
            try:
                await asyncio.to_thread(api.delete, f"/api/ttqt-branches/{b['id']}")
            except Exception as e:
                if _handle_api_error(e):
                    return
                return
            ui.notify("Đã xoá chi nhánh", type="positive")
            await load()

        # ── Bộ lọc + thao tác — gộp một hàng, cao ~48px để nhường chỗ cho bảng ──
        with ui.card().classes("w-full shadow-sm rounded-lg bg-white px-3 py-2 mb-3"):
            with ui.row().classes("items-center gap-2 flex-wrap"):
                s_q = ui.input(placeholder="Mã CN / Tên CN / SWIFT BIC").props(
                    "dense outlined clearable").classes("w-60")
                s_loai = ui.select(_LOAI_OPTS, value=0).props("dense outlined").classes("w-32")
                s_status = ui.select(_STATUS_OPTS, value="active").props("dense outlined").classes("w-40")
                ui.button("Tìm", icon="search", on_click=lambda: load()
                          ).props("dense no-caps").classes("bg-gray-700 text-white px-3")
                s_q.on("keydown.enter", lambda: load())

                ui.space()

                if can_create:
                    ui.button("Thêm CN", icon="add", on_click=lambda: open_form()
                              ).props("dense no-caps").classes("bg-red-700 text-white px-3")

                async def do_export():
                    try:
                        content = await asyncio.to_thread(
                            api.download, "/api/ttqt-branches/export", _filter_params())
                    except Exception as e:
                        if _handle_api_error(e):
                            return
                        ui.notify(str(e), type="negative")
                        return
                    ui.download(content, f"danh_sach_cn_ttqt_{date.today():%Y%m%d}.xlsx")

                if can_export:
                    ui.button("Xuất Excel", icon="download", on_click=do_export
                              ).props("dense no-caps").classes("bg-green-700 text-white px-3")

                if can_import:
                    # Tuỳ chọn xoá nằm ngay cạnh nút chọn file: tách xuống hàng
                    # riêng thì người nhập dễ bấm chọn file trước khi thấy nó.
                    imp_delete = ui.checkbox("Xoá CN thiếu").props("dense")
                    imp_delete.tooltip(
                        "Bỏ tích: chỉ thêm mới và cập nhật, giữ nguyên CN đã có. "
                        "Tích: xoá luôn các CN không có trong file (đồng bộ hoàn toàn)."
                    )

                    async def do_import(e):
                        # Báo ngay khi nhận file: nếu để im cho tới lúc có kết
                        # quả, người nhập không biết máy đang làm hay đã treo.
                        ui.notify(f"Đang nhập «{e.name}»...", type="ongoing", timeout=2000)
                        loading.classes(remove="hidden")
                        try:
                            result = await asyncio.to_thread(
                                api.post_upload,
                                f"/api/ttqt-branches/import?delete_missing="
                                f"{'true' if imp_delete.value else 'false'}",
                                {"file": (e.name, e.content.read(),
                                          "application/vnd.openxmlformats-officedocument."
                                          "spreadsheetml.sheet")},
                            )
                        except Exception as ex:
                            if _handle_api_error(ex):
                                return
                            ui.notify(str(ex), type="negative")
                            return
                        finally:
                            loading.classes(add="hidden")
                        ui.notify(
                            f"Nhập xong: +{result['inserted']} mới, ~{result['updated']} cập nhật, "
                            f"-{result['deleted']} xoá",
                            type="positive", timeout=5000,
                        )
                        # Cảnh báo (thiếu cột, mã trùng, loại CN sai kiểu) hiện riêng —
                        # gộp vào 1 notify sẽ bị cắt và người nhập không biết dòng nào lỗi
                        for w in result.get("errors", [])[:10]:
                            ui.notify(w, type="warning", timeout=8000)
                        await load()

                    with ui.element("div").classes("ttqt-upload"):
                        # Truyền THẲNG hàm async, không bọc trong
                        # `lambda e: asyncio.create_task(...)`. Bọc như vậy làm
                        # coroutine chạy ngoài slot của NiceGUI: `ui.notify` ném
                        # RuntimeError "slot stack is empty", lỗi bị nuốt, và
                        # người dùng nhập file xong không thấy phản hồi nào.
                        ui.upload(label="Nhập Excel", auto_upload=True,
                                  on_upload=do_import).props('accept=".xlsx" flat')

        def _filter_params() -> dict:
            p = {"status": s_status.value or "active"}
            if s_q.value and s_q.value.strip():
                p["q"] = s_q.value.strip()
            if s_loai.value in (1, 2):
                p["loai_cn"] = s_loai.value
            return p

        count_label = ui.label("").classes("text-xs text-gray-500 mb-1")
        loading = ui.row().classes("w-full justify-center items-center py-6 hidden")
        with loading:
            ui.spinner(size="2em", color="red")
            ui.label("Đang tải...").classes("text-gray-500 ml-2 text-sm")
        table_area = ui.column().classes("w-full")

        # ── Tải & vẽ bảng ─────────────────────────────────────────────────────
        async def load():
            loading.classes(remove="hidden")
            try:
                data = await asyncio.to_thread(api.get, "/api/ttqt-branches/", _filter_params())
            except Exception as e:
                _handle_api_error(e)
                return
            finally:
                loading.classes(add="hidden")

            cache.clear()
            cache.extend(data)
            table_area.clear()

            n_open = sum(1 for b in data if not b["is_closed"])
            n_closed = len(data) - n_open
            count_label.text = (
                f"{len(data)} chi nhánh — {n_open} đang hoạt động, {n_closed} đã đóng BIC"
            )

            with table_area:
                if not data:
                    ui.label("Không có chi nhánh nào khớp điều kiện lọc").classes(
                        "text-gray-500 text-center py-8 w-full")
                    return

                by_id = {b["id"]: b for b in data}
                rows = [_to_row(b, can_edit, can_delete, can_history) for b in data]
                cols = [c for c in _COLUMNS
                        if c["name"] != "actions" or can_edit or can_delete or can_history]
                # rowsPerPage=0 = hiện hết, không phân trang: người dùng cuộn
                # thẳng trong thân bảng thay vì bấm sang trang. 218 dòng là mức
                # Quasar dựng thoải mái, không cần virtual-scroll.
                table = ui.table(columns=cols, rows=rows, row_key="id",
                                 pagination={"rowsPerPage": 0}).props(
                    'bordered dense flat separator="cell"'
                ).classes("w-full ttqt-table")

                # Ghi đè cả dòng (không chỉ ô thao tác) để tô xám CN đã đóng BIC —
                # cần thiết khi lọc "Tất cả", lúc đó 2 nhóm nằm lẫn trong 1 bảng.
                table.add_slot("body", r"""
                    <q-tr :props="props" :class="props.row.closed ? 'bg-grey-3 text-grey-7' : ''">
                      <q-td v-for="col in props.cols" :key="col.name" :props="props">
                        <template v-if="col.name === 'actions'">
                          <q-btn dense flat round size="sm" color="primary" icon="edit"
                                 v-if="props.row.can_edit"
                                 @click="() => $parent.$emit('rowEdit', props.row.id)" />
                          <q-btn dense flat round size="sm" color="negative" icon="delete"
                                 v-if="props.row.can_delete"
                                 @click="() => $parent.$emit('rowDel', props.row.id)" />
                          <q-btn dense flat round size="sm" color="grey-8" icon="history"
                                 v-if="props.row.can_history"
                                 @click="() => $parent.$emit('rowHist', props.row.id)">
                            <q-tooltip>Lịch sử sửa đổi</q-tooltip>
                          </q-btn>
                        </template>
                        <template v-else>{{ col.value }}</template>
                      </q-td>
                    </q-tr>
                """)

                # Trả về coroutine cho NiceGUI await hộ (nó vào đúng slot trước
                # khi await) — `asyncio.create_task` ở đây sẽ chạy ngoài slot và
                # `ui.dialog()` trong do_delete lập tức hỏng.
                async def on_row_del(e):
                    await do_delete(by_id[int(e.args)])

                async def on_row_hist(e):
                    await show_history(by_id[int(e.args)])

                table.on("rowEdit", lambda e: open_form(by_id[int(e.args)]))
                table.on("rowDel", on_row_del)
                table.on("rowHist", on_row_hist)

        await load()
