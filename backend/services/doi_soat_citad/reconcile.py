# -*- coding: utf-8 -*-
"""
reconcile.py
------------
Port thuật toán đối soát từ `DoiSoatCITAD.py::run_doiSoat_ram` của tool
desktop gốc — quy tắc nghiệp vụ cốt lõi ĐÃ DUYỆT và giữ nguyên khi port:
khớp theo msgref (Đi) / txid (Đến), ưu tiên trạng thái IPCAS Đến theo
PRIORITY_TT khi trùng txid, chỉ nhận SCNL là thành công cho lệnh Đi (khác đi
→ 'lech_trang_thai').

Ngoại lệ "bỏ PYED/PYEK khi tính dư IPCAS Đến" (có từ bản gốc) đã BỎ ngày
23/08/2026 — xác nhận nghiệp vụ (Phòng Thanh toán): chênh lệch SỐ LƯỢNG lệnh
áp dụng cho MỌI trạng thái, không riêng gì trạng thái nào. Xem ghi chú tại
vòng lặp "IPCAS Đến dư" trong `run_doiSoat_ram()`.

Ghi chú review (phát hiện khi chuẩn bị PR, ĐÃ SỬA — không phải thay đổi quy
tắc nghiệp vụ đã duyệt): bản gốc có 1 nhánh "phân biệt theo nh_nhan khi
msgref trùng" (map phụ `ipcas_di_map2`) nhưng chưa từng chạy được — map phụ
được dựng từ CÙNG vòng lặp, CÙNG thứ tự với map chính nên luôn suy ra lại
đúng map chính (dict đầu tiên theo msgref thắng ở cả 2 map); hơn nữa dữ liệu
CITAD parse ra (`parsers.py`) không có field `nh_nhan` nên không có gì để so
khớp. Đã bỏ hẳn map phụ chết này thay vì giữ code không chạy — hành vi khớp
lệnh KHÔNG đổi (map phụ chưa bao giờ ảnh hưởng tới kết quả).
"""
from __future__ import annotations

# CGBR ưu tiên CAO NHẤT — xác nhận nghiệp vụ 23/08/2026 (Phòng Thanh toán),
# đúng mục "Lệnh chuyển chi nhánh Đến: 1 lệnh gốc → nhiều dòng con IPCAS →
# chỉ tính dòng gốc" đã ghi trong tài liệu bàn giao gốc nhưng chưa cài đặt.
# Xác nhận qua dữ liệu thật 19/08/2026: TXID Đến dạng "gốc-dãy số dài" —
# dòng GỐC luôn ở chi nhánh 1000, trạng thái CGBR; dòng CON (chuyển sang
# chi nhánh khác xử lý) cùng số tiền, khác chi nhánh, trạng thái RFED/WFPG/
# WTBR/PYED. Dòng con chỉ là thao tác nội bộ IPCAS, KHÔNG phải 1 lệnh thật
# cần đối chiếu riêng — nguyên tắc đúng là 1 lệnh CITAD cân với 1 lệnh GỐC
# IPCAS. Gốc/con dùng CHUNG khoá khớp lệnh (txid, loai, so_tien) nên tự va
# nhau ở build ipcas_den_map(); TRƯỚC khi thêm CGBR, nó không có trong bảng
# nên bị coi ưu tiên thấp nhất (mặc định 99) — dòng CON (RFED=3) luôn thắng
# NHẦM dòng GỐC. Thêm CGBR=0 để dòng gốc luôn thắng, dòng con thua tự biến
# mất khỏi map (không tạo dòng "Chỉ IPCAS" giả — đúng ý "không phải chênh
# lệch, chỉ là hoạt động nội bộ").
PRIORITY_TT = {'CGBR': 0, 'PYED': 1, 'PYEK': 2, 'WFPG': 3, 'RFED': 4, 'SDEB': 5, 'SBFL': 6, 'SBSC': 7}
VALID_DI = {'SCNL'}  # Đi: chỉ SCNL là thành công
# ERPO/CALD = IPCAS báo lệnh Đi thất bại/huỷ. Nếu CITAD KHÔNG có lệnh này
# thì đúng bản chất (chưa từng đi kênh) — không phải bất thường. Nhưng nếu
# CITAD VẪN CÓ (đi kênh thành công thật) thì IPCAS đang sai — bất thường
# thật, phải bắt vào 'lech_trang_thai' kèm ghi chú rõ (xem bên dưới và vòng
# lặp "IPCAS Đi dư").
ERR_DI = {'ERPO', 'CALD'}
# Ưu tiên khi 1 msgref có NHIỀU dòng IPCAS Đi — số nhỏ thắng.
# Cần từ khi ERR_DI được giữ lại khi parse: trước đó chỉ có trạng thái thành
# công/đang xử lý nên "dòng đầu tiên thắng" vô hại, nay một msgref có thể có
# cả ERPO/CALD lẫn SCNL và dòng đầu tiên là dòng nào thì phụ thuộc THỨ TỰ
# DÒNG TRONG FILE — mà thứ tự đó đổi được thật (người dùng chọn file theo thứ
# tự khác, hoặc thứ tự entry trong ZIP khác). Đã đo: cùng dữ liệu, ERPO đứng
# trước cho n_khop=0, SCNL đứng trước cho n_khop=1. Một cỗ máy đối soát không
# được phụ thuộc thứ tự đọc, nên cho SCNL luôn thắng. Cùng khuôn mẫu với
# PRIORITY_TT của chiều Đến ngay bên dưới.
PRIORITY_DI = {'SCNL': 0}


def _ghi_chu_khop_du_nguon(cong, n_dup, n_citad, nguon, chieu_lbl):
    """Ghi_chú cho dòng ĐÃ khớp ('both') khi nguồn đối ứng (IPCAS/Hub) có
    NHIỀU HƠN `n_citad` dòng cho khoá này — đối xứng `dup_citad` (CITAD gửi
    trùng, nguồn đối ứng chỉ 1 dòng): ở đây CITAD ít dòng hơn, nguồn đối ứng
    mới là bên trùng. Chỉ tính khớp đúng `n_citad` lần (n_khop không đổi);
    phần dư (n_dup - n_citad) dòng tự hiện thành dòng "Chỉ Agribank"/"Chỉ
    Hub" RIÊNG (xem `_dong_thua_nguon` bên dưới) — không chỉ 1 câu ghi chú
    trên dòng khớp, vì bản chất đó là SỐ LƯỢNG chênh lệch thật (phát hiện
    thật 23/08/2026: copy thêm 1 dòng IPCAS y hệt để test, dòng dư phải tự
    thành dòng riêng mới đúng ý nghiệp vụ, không phải ẩn trong 1 dòng khớp).

    `n_citad` KHÔNG được giả định luôn là 1 — SỬA LẠI 23/08/2026: VND Đi
    luôn đúng 1 (CITAD trùng đã lọc riêng thành dup_citad), nhưng VND Đến
    và Hub cho phép CITAD tự trùng khoá thật (xem citad_den_vnd_count/
    citad_hub_*_count ở run_doiSoat_ram) — bug cũ viết cứng "chỉ tính khớp
    1 lần" sẽ sai câu chữ (dù không sai n_khop/n_lech, đã sửa riêng ở
    _dong_thua_nguon) nếu CITAD thật có ≥2 dòng khớp cùng lúc IPCAS/Hub
    cũng trùng — phát hiện qua rà soát, chưa từng xảy ra trên dữ liệu đã
    chấm nhưng là lỗi thật, sửa cho nhất quán với _dong_thua_nguon()."""
    if n_dup <= n_citad:
        return None
    return (
        f'{nguon} ghi nhận lệnh {chieu_lbl} này {n_dup} lần (khớp {n_citad} lần — '
        f'xem thêm {n_dup - n_citad} dòng ở nhóm Chỉ {nguon}), cổng CITAD {cong or "?"}'
    )


def _ipcas_identity_key(r):
    """Khoá MỊN — "đây có phải CÙNG 1 bản ghi IPCAS bị lặp lại y hệt hay
    không". KHÁC khoá khớp lệnh (msgref, hoặc (txid, loai, so_tien) — cố ý
    làm thô để khớp lệnh linh hoạt, xem ghi chú build ipcas_den_map()).
    Dùng khoá thô để đếm "trùng" là SAI: xác nhận thật (dữ liệu 19/08/2026,
    phát hiện khi kiểm lại trước khi ship) — IPCAS dùng CHUNG 1 txid cho
    NHIỀU LỆNH THẬT KHÁC NHAU (khác `nh_nhan` — ngân hàng nhận), có lúc còn
    trùng ngẫu nhiên cả `so_tien`. Đếm theo khoá thô sẽ hiểu nhầm 2 lệnh
    THẬT độc lập (khác ngân hàng nhận) thành "IPCAS hạch toán trùng" — đo
    được: n_lech nhảy từ 12 lên 1.556 khi dùng nhầm khoá thô để đếm.
    Khoá mịn gồm `nh_nhan`/`chi_nhanh`/`trang_thai`/`ngay` — 2 dòng chỉ tính
    "trùng nhau thật" khi khớp ĐỦ mọi trường này, đúng bản chất "bị lặp lại
    y hệt", không phải chỉ trùng vài trường nhận dạng.

    KHÔNG đưa `trace` vào khoá — SỬA LẠI sau khi kiểm bằng cách xoá thử 1
    dòng trùng để test (23/08/2026): cả 5/5 nhóm trùng phát hiện trước đó
    thực ra có 3 dòng, không phải 2 — 2 dòng trùng y hệt CẢ trace, dòng thứ
    3 giống hệt mọi trường (chi nhánh, ngân hàng, trạng thái, ngày, số
    tiền, kể cả REFHUB — mã lẽ ra phải riêng cho từng bản ghi) nhưng KHÁC
    trace. Có `trace` trong khoá làm dòng thứ 3 rơi ra một khoá riêng, tự
    "biến mất" hoàn toàn (không khớp, không hiện Chỉ IPCAS) vì bị
    `ipcas_den_map` giữ lại đúng 1 dòng cho khoá khớp lệnh — không một cơ
    chế nào trong reconcile.py nhắc tới dòng thua.

    XÁC NHẬN NGHIỆP VỤ (Phòng Thanh toán, 23/08/2026) — không còn là suy
    đoán: mỗi lần 1 lệnh được hạch toán vào IPCAS, hệ thống SINH RA 1 số
    trace MỚI, kể cả khi hạch toán trùng lặp cùng 1 giao dịch trong cùng 1
    ngày. Vì vậy trace KHÔNG BAO GIỜ được dùng làm tín hiệu phân biệt "có
    phải cùng 1 lệnh hay không" — khác trace không có nghĩa là khác lệnh.
    Việc phân biệt "gốc/con" (chuyển chi nhánh) là việc của
    chi_nhanh/trạng_thái (xem PRIORITY_TT/CGBR), không phải trace."""
    return (
        r['chieu'], r['txid'], r['loai'], r['so_tien'], r.get('nh_nhan', ''),
        r.get('chi_nhanh', ''), r['trang_thai'], r['ngay'],
    )


def _loc_hach_toan_nham_huy(ipcas_rows):
    """Loại các dòng IPCAS Đến là cặp "hạch toán nhầm rồi huỷ" — xác nhận
    nghiệp vụ 23/08/2026 (Phòng Thanh toán), giải thích ĐÚNG nguyên nhân của
    hiện tượng "trùng trace" phát hiện ở card 100 (23/08): khi GDV hạch toán
    thủ công 1 lệnh Đến bị NHẦM (sai chi nhánh), phải HUỶ bút toán đó rồi
    hạch toán lại thủ công đúng nơi. Bút toán HUỶ dùng LẠI đúng số trace của
    bút toán bị huỷ (2 dòng CÙNG chi nhánh + CÙNG trace), còn bút toán hạch
    toán lại ĐÚNG luôn được cấp trace MỚI — và có thể ở CHI NHÁNH KHÁC với
    cặp nhầm/huỷ đó (xác nhận của Phòng Thanh toán), nên KHÔNG được yêu cầu
    "cùng chi nhánh" khi nhóm theo 1 lệnh.

    Nhóm theo `refhub` (mã tham chiếu điện đến gốc) chứ KHÔNG theo (txid,
    loai, so_tien) — xác nhận qua dữ liệu thật 19/08/2026: refhub có ở
    100% dòng Đến, và với cả 5 nhóm "Chỉ IPCAS" đang bị báo hôm nay, refhub
    tách ĐÚNG 3 dòng liên quan ra khỏi hàng chục dòng khác trùng ngẫu nhiên
    txid (IPCAS tái dùng txid cho nhiều lệnh khác nhau, xem ghi chú
    build ipcas_den_map() — refhub không bị vấn đề này).

    An toàn: chỉ loại khi trong CÙNG 1 refhub còn sót lại ít nhất 1 dòng
    sau khi loại — nếu loại hết sạch (không có dòng nào trace riêng, tức
    không tìm được bút toán ĐÚNG) thì GIỮ NGUYÊN, không loại gì (xác nhận
    nghiệp vụ: trường hợp này không xảy ra trong thực tế).

    Trả về set các `id(row)` cần loại bỏ khỏi đối soát — không tính khớp,
    không tính lệch, coi như dòng đó chưa từng có trong file."""
    by_refhub = {}
    for r in ipcas_rows:
        if r['chieu'] != 'den' or not r.get('refhub'):
            continue
        by_refhub.setdefault(r['refhub'], []).append(r)

    loai_bo = set()
    for rows in by_refhub.values():
        if len(rows) < 2:
            continue
        cn_trace_count = {}
        for r in rows:
            ck = (r.get('chi_nhanh', ''), r.get('trace', ''))
            cn_trace_count[ck] = cn_trace_count.get(ck, 0) + 1
        ung_vien = [r for r in rows
                    if cn_trace_count[(r.get('chi_nhanh', ''), r.get('trace', ''))] >= 2]
        if ung_vien and len(ung_vien) < len(rows):
            loai_bo.update(id(r) for r in ung_vien)
    return loai_bo


# Lệnh ngoại tệ chuyển chi nhánh (Hub) — xác nhận nghiệp vụ 23/08/2026
# (Phòng Thanh toán), đúng cơ chế đã xử lý cho IPCAS (CGBR, xem PRIORITY_TT
# ở trên): 1 lệnh Đến/Đi sinh nhiều dòng CÙNG "Số thành công" (so_gd) nhưng
# khác chi nhánh — dòng GỐC mang trạng thái "Đã trả KH", các dòng CÒN LẠI
# là chi nhánh trung gian, chỉ là thao tác nội bộ Hub, không phải chênh
# lệch cần đối chiếu riêng — nguyên tắc "1 lệnh CITAD cân với 1 lệnh gốc"
# áp dụng như nhau cho cả IPCAS lẫn Hub.
HUB_ROOT_STATUS = 'Đã trả KH'


def _hub_priority(trang_thai):
    """0 = dòng gốc (thắng), 1 = dòng khác (chi nhánh trung gian hoặc rỗng
    nếu file không có cột Trạng thái — không đổi hành vi khi thiếu cột)."""
    return 0 if trang_thai == HUB_ROOT_STATUS else 1


def _hub_identity_key(r):
    """Như `_ipcas_identity_key()` nhưng cho dòng Hub ngoại tệ — khoá khớp
    lệnh Hub chỉ là `so_gd` (thô hơn cả IPCAS), nên khoá mịn ở đây thêm
    `so_tien`/`nh_nhan`/`ngay`/`trang_thai`. BẮT BUỘC có `trang_thai` trong
    khoá: dòng gốc ("Đã trả KH") và dòng con (chuyển chi nhánh) của CÙNG 1
    lệnh có thể giống nhau ở mọi trường còn lại — thiếu trang_thai trong
    khoá sẽ hiểu nhầm cặp gốc/con là "Hub ghi nhận trùng", đúng lỗi vừa sửa
    cho IPCAS (xem _ipcas_identity_key) tái diễn ở đây nếu không cẩn thận."""
    return (
        r['chieu'], r['so_gd'], r.get('loai_tien', ''), r['so_tien'],
        r.get('nh_nhan', ''), r.get('ngay', ''), r.get('trang_thai', ''),
    )


def _dong_thua_nguon(r, chieu, so_gd_key, status, n_dup, n_citad, cong, nguon):
    """1 trong các dòng "thừa" khi nguồn đối ứng (IPCAS/Hub) có nhiều dòng
    hơn số lệnh CITAD THẬT xác nhận cho khoá này — xem `_ghi_chu_khop_du_nguon`.
    `n_citad` là số dòng CITAD thật đếm được (0, 1, hoặc nhiều — VND Đến/Hub
    cho phép CITAD tự trùng khoá thật, xem citad_den_vnd_count/citad_hub_*_count
    ở nơi gọi), KHÔNG giả định luôn là 1 (bug cũ). `cong` là cổng CITAD của
    lệnh đã khớp (None nếu khoá này CITAD không hề có lệnh nào)."""
    row = {
        # 'so_gd' (cột "Số GD (CITAD)") ĐỂ TRỐNG — đúng đối xứng với
        # 'only_citad' (để trống 'key_agri', cột "Số GD (Agribank)"): dòng
        # này là "Chỉ IPCAS/Hub" nghĩa là CITAD KHÔNG hề có lệnh này, hiện
        # số ở cột CITAD sẽ khiến người xem tưởng nhầm CITAD cũng có số đó
        # (bug có sẵn từ trước — phát hiện qua câu hỏi trực tiếp của người
        # dùng khi xem dòng "Chỉ IPCAS" 23/08/2026).
        'so_gd': '', 'dich_vu': r.get('kenh', '') or r.get('dich_vu', ''),
        'loai': r.get('loai', ''), 'chieu': chieu, 'loai_tien': r.get('loai_tien', 'VND'),
        'so_tien': r.get('so_tien', 0), 'ngay': r.get('ngay', ''), 'status': status,
        'key_agri': so_gd_key, 'nh_nhan': r.get('nh_nhan', ''),
        'trang_thai': r.get('trang_thai', ''),
        # `refhub` chỉ có thật khi `nguon='IPCAS'` (Hub không parse field
        # này) — `.get()` tự trả '' cho trường hợp Hub, không cần nhánh
        # riêng (cùng lý do đồng nhất đã áp dụng ở nhánh Hub khớp trong
        # run_doiSoat_ram()).
        'refhub': r.get('refhub', ''),
    }
    ghi_chu = f'1 trong {n_dup} lần {nguon} ghi nhận lệnh này'
    if n_citad > 0:
        cong_txt = f', cổng {cong}' if cong else ''
        ghi_chu += f' — CITAD chỉ có {n_citad} lệnh{cong_txt}'
    else:
        ghi_chu += ' — không có lệnh CITAD tương ứng'
    ghi_chu += f' — cần kiểm tra lại {nguon}'
    row['ghi_chu'] = ghi_chu
    return row


def run_doiSoat_ram(citad_rows, ipcas_rows, hub_rows):
    """Đối soát trong RAM bằng dict Python — xem docstring module để biết
    quy tắc khớp lệnh và ghi chú về nhánh dead-code đã bỏ khi chuẩn bị PR."""
    # Loại cặp "hạch toán nhầm rồi huỷ" TRƯỚC khi dựng bất kỳ map/đếm nào —
    # xem docstring _loc_hach_toan_nham_huy(). Chỉ đụng dòng Đến IPCAS (VND);
    # Đi và Hub ngoại tệ không đổi.
    _loai_bo = _loc_hach_toan_nham_huy(ipcas_rows)
    if _loai_bo:
        ipcas_rows = [r for r in ipcas_rows if id(r) not in _loai_bo]

    # Build map IPCAS Đi/Đến — msgref/txid -> row. Đi ưu tiên theo PRIORITY_DI,
    # Đến ưu tiên theo PRIORITY_TT (cả hai bên dưới) — không bên nào để "dòng
    # đầu tiên thắng" thuần tuý, vì thứ tự dòng trong file không ổn định.
    ipcas_di_map = {}
    ipcas_den_map = {}
    # Dòng IPCAS SCNL nhưng thiếu ngày kênh trả (`nkt_thieu`, xem
    # parsers.py) — KHÔNG cho vào `ipcas_di_map` (không được tự động khớp,
    # đúng ý gốc 27/08/2026) nhưng vẫn giữ riêng ở đây để lấy `refhub` khi
    # ghép vào dòng "Chỉ CITAD" tương ứng (xác nhận Phòng Thanh toán
    # 09/09/2026: case này lệnh RẤT CÓ THỂ vẫn tồn tại ở Agribank, không
    # giống "Chỉ CITAD" thường — người chấm cần refhub để tự tra cứu).
    ipcas_di_nkt_thieu_map = {}
    # Đếm theo khoá MỊN (_ipcas_identity_key, xem docstring) — "dòng này bị
    # lặp lại y hệt bao nhiêu lần", KHÔNG PHẢI đếm theo khoá khớp lệnh thô
    # (msgref / txid+loai+so_tien) ở map bên dưới. Hai việc khác nhau: map
    # dùng khoá thô để khớp lệnh linh hoạt (IPCAS có thể tái dùng txid cho
    # nhiều lệnh khác nhau — xem ghi chú build ipcas_den_map()); đếm trùng
    # phải dùng khoá mịn để không hiểu nhầm 2 lệnh thật khác nhau là trùng.
    ipcas_identity_count = {}
    for r in ipcas_rows:
        # Loại `nkt_thieu` khỏi đếm khoá mịn (09/09/2026, phát hiện qua rà
        # soát): dòng này KHÔNG tham gia khớp lệnh (bị loại khỏi
        # ipcas_di_map ngay dưới đây), giữ nguyên hành vi CŨ trước khi có cờ
        # `nkt_thieu` — lúc đó dòng này còn bị `continue` ngay ở parsers.py
        # nên chưa từng vào tới đây. Nếu không loại, dòng nkt_thieu có thể
        # trùng khoá mịn với 1 dòng KHỚP khác (msgref khác — khoá mịn cố ý
        # không có msgref) và làm dòng khớp đó bị tính dư 1 lần "trùng":
        # vừa sai ghi_chú "IPCAS ghi nhận N lần", vừa sinh thêm 1 dòng "Chỉ
        # IPCAS" ma ở khoá không liên quan — trong khi dòng nkt_thieu đã tự
        # có đại diện đúng riêng (dòng "Chỉ CITAD" kèm refhub, xem bên dưới).
        if not r.get('nkt_thieu'):
            ik = _ipcas_identity_key(r)
            ipcas_identity_count[ik] = ipcas_identity_count.get(ik, 0) + 1
        if r['chieu'] == 'di':
            k = r['msgref']
            if not k:
                continue
            if r.get('nkt_thieu'):
                ipcas_di_nkt_thieu_map.setdefault(k, r)
                continue
            if k not in ipcas_di_map:
                ipcas_di_map[k] = r
            elif (PRIORITY_DI.get(r['trang_thai'], 9)
                  < PRIORITY_DI.get(ipcas_di_map[k]['trang_thai'], 9)):
                ipcas_di_map[k] = r
        else:
            # Khoá (txid, loai, so_tien) chứ KHÔNG chỉ txid — xác nhận thực
            # tế (dữ liệu thật 19/08/2026): IPCAS dùng CHUNG 1 txid cho
            # nhiều dòng KHÁC NHAU trong cùng phiên/lô (vd lệnh IH giá trị
            # cao Napas/PSS-MDP trùng túi với hàng loạt dòng IL giá trị
            # thấp không liên quan). Trước đây chỉ khoá theo txid: dòng IL
            # trạng thái PYED/PYEK (ưu tiên PRIORITY_TT cao hơn SBSC) ĐÈ MẤT
            # dòng IH SBSC thật, rồi dòng IL "thắng" đó lại bị vòng lặp
            # "IPCAS Đến dư" loại vì đúng PYED/PYEK — hậu quả: lệnh
            # Napas/PSS-MDP thật biến mất khỏi báo cáo lệch dù CITAD hoàn
            # toàn không có, không phải "khớp" thật.
            #
            # Thêm `loai` vẫn CHƯA đủ: đã gặp thật 2 dòng CÙNG txid CÙNG
            # loai (vd mã 10006020 — 1 dòng SBSC số tiền thật, 1 dòng PYED
            # số tiền khác hẳn, không liên quan) — PYED vẫn thắng theo
            # PRIORITY_TT, đè mất dòng SBSC đúng. Thêm `so_tien` vào khoá để
            # AN TOÀN HƠN: 2 dòng chỉ thật sự "cùng 1 lệnh" khi khớp CẢ 3
            # (txid, loai, so_tien) — khác số tiền thì tách thành 2 lệnh độc
            # lập, không còn đè lẫn nhau nữa. Tác dụng phụ có lợi: CITAD và
            # IPCAS cùng txid+loai nhưng LỆCH số tiền (dữ liệu sai thật) giờ
            # không còn bị tính nhầm là "khớp" — sẽ tự hiện ra ở cả 2 nhóm
            # "chỉ CITAD"/"chỉ IPCAS" thay vì bị nuốt im lặng.
            k = (r['txid'], r['loai'], r['so_tien'])
            if not r['txid']:
                continue
            if k not in ipcas_den_map:
                ipcas_den_map[k] = r
            else:
                cur_pri = PRIORITY_TT.get(ipcas_den_map[k]['trang_thai'], 99)
                new_pri = PRIORITY_TT.get(r['trang_thai'], 99)
                if new_pri < cur_pri:
                    ipcas_den_map[k] = r

    # Build map Hub — đếm theo khoá MỊN (_hub_identity_key) như IPCAS ở
    # trên, áp dụng chung cho ngoại tệ theo đúng yêu cầu: cơ chế phát hiện
    # "nguồn đối ứng ghi nhận trùng" phải nhất quán giữa VND và ngoại tệ.
    hub_di_map = {}
    hub_den_map = {}
    hub_identity_count = {}
    for r in hub_rows:
        ik = _hub_identity_key(r)
        hub_identity_count[ik] = hub_identity_count.get(ik, 0) + 1
        k = r['so_gd']
        # Ưu tiên dòng gốc ("Đã trả KH") khi trùng Số thành công — xem
        # HUB_ROOT_STATUS/_hub_priority() ở trên. File không có cột Trạng
        # thái thì mọi dòng đều priority=1, "dòng đầu tiên thắng" như cũ,
        # không đổi hành vi.
        if r['chieu'] == 'di':
            if k not in hub_di_map:
                hub_di_map[k] = r
            elif _hub_priority(r.get('trang_thai')) < _hub_priority(hub_di_map[k].get('trang_thai')):
                hub_di_map[k] = r
        else:
            if k not in hub_den_map:
                hub_den_map[k] = r
            elif _hub_priority(r.get('trang_thai')) < _hub_priority(hub_den_map[k].get('trang_thai')):
                hub_den_map[k] = r

    n_khop = 0
    lech = []
    # Dòng lệnh ĐÃ khớp — trước đây chỉ đếm (n_khop), không giữ chi tiết
    # từng dòng, vì màn hình chỉ cần hiện SỐ khớp. Giữ lại đây để phục vụ
    # "Xuất tất cả lệnh" (xem doi_soat_citad.py API/frontend) — cùng cấu
    # trúc dict với `lech` (status='both') để exporters.py dùng chung 1
    # hàm vẽ Excel cho cả 2 loại dòng.
    khop = []
    # 4 tập RIÊNG cho VND (IPCAS) và ngoại tệ (Hub) — KHÔNG dùng chung 2 tập
    # theo chiều như trước. Bug thật đã xác nhận (23/08/2026, rà soát cuối
    # ngày): so_gd VND và so_gd ngoại tệ là 2 hệ đánh số ĐỘC LẬP, hoàn toàn
    # có thể trùng số ngẫu nhiên trong cùng 1 ngày (vd CITAD VND và CITAD
    # ngoại tệ cùng đánh số "700001"). Nếu dùng chung 1 tập theo khoá
    # `so_gd`, 1 lệnh CITAD ngoại tệ khớp Hub sẽ vô tình đánh dấu luôn
    # msgref IPCAS VND trùng số đó là "đã khớp" — vòng lặp "IPCAS dư" bỏ
    # qua, lệnh IPCAS thật (không hề có CITAD VND tương ứng) BIẾN MẤT hoàn
    # toàn khỏi báo cáo, không khớp cũng không "Chỉ IPCAS". Xác nhận bằng
    # test dựng tay: CITAD ngoại tệ so_gd='999' khớp Hub, IPCAS VND
    # msgref='999' không có CITAD nào — trước khi tách, IPCAS msgref='999'
    # biến mất thay vì hiện "Chỉ IPCAS".
    citad_matched_di_ipcas = set()
    citad_matched_den_ipcas = set()
    citad_matched_di_hub = set()
    citad_matched_den_hub = set()
    # Cổng CITAD của lệnh ĐÃ khớp, theo đúng khoá của map tương ứng — dùng
    # để ghi rõ "cổng CITAD nào" khi nguồn đối ứng (IPCAS/Hub) hạch toán
    # trùng lệnh này (xem _dong_thua_nguon() ở trên và 2 vòng lặp "dư" bên
    # dưới). CITAD luôn có field 'cong' bất kể loại tiền.
    citad_cong_di = {}
    citad_cong_den = {}
    citad_cong_hub_di = {}
    citad_cong_hub_den = {}

    # Phát hiện CITAD gửi TRÙNG cùng 1 so_gd cho lệnh Đi VND — bug thật đã
    # xác nhận qua test thực tế (và có sẵn trong bản gốc citad-fixed): vòng
    # lặp bên dưới chạy theo TỪNG DÒNG CITAD, không loại trùng trước khi
    # khớp, nên 1 so_gd trùng N lần mà IPCAS chỉ có 1 bản ghi sẽ bị tính
    # "khớp" thêm N-1 lần một cách im lặng. Chỉ áp dụng lệnh Đi theo yêu cầu
    # — đếm TRƯỚC vòng lặp chính, dùng `di_vnd_seen` để chỉ dòng ĐẦU TIÊN
    # của mỗi so_gd trùng đi qua khớp lệnh bình thường (không đổi kết quả
    # khớp/lệch cho trường hợp không trùng), các dòng trùng SAU đó tách
    # riêng thành lệch 'dup_citad', không tính khớp.
    #
    # ĐÃ THỬ mở rộng chốt chặn này sang VND Đến + ngoại tệ (22/08/2026),
    # RỒI RÚT LẠI: kiểm bằng đúng dữ liệu thật 19/08/2026 phát hiện VND Đến
    # có 1.154 nhóm (so_gd, loai, so_tien) xuất hiện ≥2 lần thật trong ngày
    # — 942 nhóm cùng 1 cổng CITAD, 212 nhóm khác cổng (so_gd đánh số theo
    # từng cổng, trùng số giữa 2 cổng không phải trùng thật). Thử phân biệt
    # thêm bằng `dich_vu` cũng không tách được vì phần lớn dòng trùng có
    # dich_vu giống hệt nhau ("Chuyển có giá trị cao") — không phải lỗi
    # kiểu "2 dòng khác dich_vu" như ca NSNN quan sát được ở nơi khác.
    # Không đủ căn cứ nghiệp vụ để biết đây là CITAD gửi trùng thật hay một
    # đặc điểm cấu trúc báo cáo Đến (vd điện báo Có + điện xác nhận riêng
    # cho cùng 1 lệnh) — áp nhầm sẽ làm mất hàng nghìn lệnh khớp thật mỗi
    # ngày (đo được: n_khop tụt từ 38.130 xuống 36.715~36.720 trên đúng bộ
    # dữ liệu 19/08/2026). Giữ nguyên phạm vi CHỈ VND Đi (đã xác nhận thật,
    # đã duyệt) cho tới khi Phòng Thanh toán xác nhận được quy tắc đúng cho
    # Đến/ngoại tệ bằng dữ liệu thật, giống cách ca Đi đã được xác nhận.
    di_vnd_count = {}
    di_vnd_congs = {}
    for r in citad_rows:
        if r['chieu'] == 'di' and r['loai_tien'] == 'VND':
            k = r['so_gd']
            di_vnd_count[k] = di_vnd_count.get(k, 0) + 1
            di_vnd_congs.setdefault(k, []).append(r.get('cong') or '?')
    di_vnd_seen = set()

    # Đếm số dòng CITAD THẬT theo khoá khớp lệnh — dùng để tính đúng số
    # dòng "thừa" khi nguồn đối ứng (IPCAS/Hub) trùng lặp, THAY VÌ giả định
    # CITAD luôn chỉ có 1 dòng cho mỗi khoá. Bug thật phát hiện 23/08/2026
    # qua câu hỏi trực tiếp của người dùng ("lệch có chắc CITAD không có
    # không, nếu đủ cả 2 bên thì không phải lệch") — kiểm bằng dữ liệu thật
    # 19/08/2026 thấy 1.154 khoá VND Đến mà CITAD có ≥2 dòng trùng khoá
    # THẬT (đã xác nhận là hiện tượng có thật, không phải lỗi — xem ghi chú
    # `di_vnd_count` phía trên), và không có cơ chế nào chặn Hub ngoại tệ
    # tương tự. Trước bản sửa này, hàm sinh dòng thừa coi CITAD luôn là 1
    # (chữ "CITAD chỉ có 1 lệnh" viết cứng) — nếu 1 ngày nào đó CITAD trùng
    # 2 dòng thật mà IPCAS/Hub trùng 3 dòng, sẽ báo dư 2 dòng thay vì đúng
    # 1, đồng thời in sai "chỉ có 1 lệnh". VND Đi KHÔNG cần đếm lại vì
    # dòng CITAD trùng đã bị lọc riêng thành `dup_citad` ở trên
    # (di_vnd_seen) — mỗi khoá matched luôn ứng đúng 1 dòng CITAD thật.
    citad_den_vnd_count = {}
    citad_hub_di_count = {}
    citad_hub_den_count = {}
    for r in citad_rows:
        if r['loai_tien'] == 'VND':
            if r['chieu'] == 'den':
                k = (r['so_gd'], r['loai'], r['so_tien'])
                citad_den_vnd_count[k] = citad_den_vnd_count.get(k, 0) + 1
        elif r['chieu'] == 'di':
            citad_hub_di_count[r['so_gd']] = citad_hub_di_count.get(r['so_gd'], 0) + 1
        else:
            citad_hub_den_count[r['so_gd']] = citad_hub_den_count.get(r['so_gd'], 0) + 1

    for r in citad_rows:
        sogd = r['so_gd']
        chieu = r['chieu']
        lt = r['loai_tien']

        if lt != 'VND':
            # Ngoại tệ: khớp Hub
            m = hub_di_map.get(sogd) if chieu == 'di' else hub_den_map.get(sogd)
            if m:
                n_khop += 1
                row = {
                    **r, 'status': 'both', 'key_agri': m.get('so_gd', sogd),
                    'nh_nhan': m.get('nh_nhan', ''), 'trang_thai': '',
                    # Hub hiện KHÔNG parse `refhub` (field chỉ có ở
                    # _parse_ipcas_text) nên luôn ra '' ở nhánh này — giữ
                    # dòng này cho ĐỒNG NHẤT với 2 nhánh IPCAS phía dưới
                    # (cứ dòng nào có refhub thì hiện, không hardcode loại
                    # trừ riêng ngoại tệ), tự động hiện đúng nếu sau này Hub
                    # có thêm field này.
                    'refhub': m.get('refhub', ''),
                }
                n_dup_m = hub_identity_count.get(_hub_identity_key(m), 1)
                if chieu == 'di':
                    citad_matched_di_hub.add(sogd)
                    citad_cong_hub_di[sogd] = r.get('cong')
                    ghi_chu = _ghi_chu_khop_du_nguon(
                        r.get('cong'), n_dup_m, citad_hub_di_count.get(sogd, 1), 'Hub', 'đi')
                else:
                    citad_matched_den_hub.add(sogd)
                    citad_cong_hub_den[sogd] = r.get('cong')
                    ghi_chu = _ghi_chu_khop_du_nguon(
                        r.get('cong'), n_dup_m, citad_hub_den_count.get(sogd, 1), 'Hub', 'đến')
                if ghi_chu:
                    row['ghi_chu'] = ghi_chu
                khop.append(row)
            else:
                lech.append({**r, 'status': 'only_citad', 'key_agri': '', 'nh_nhan': '', 'trang_thai': ''})

        elif chieu == 'di':
            if sogd in di_vnd_seen:
                n_dup = di_vnd_count.get(sogd, 1)
                congs = ', '.join(sorted(set(di_vnd_congs.get(sogd, [])), key=lambda x: (len(x), x)))
                lech.append({
                    **r,
                    'status': 'dup_citad', 'key_agri': '', 'nh_nhan': '', 'trang_thai': '',
                    'ghi_chu': f'Phát hiện lệnh đi kênh bị dup {n_dup} lần, cổng {congs}',
                })
                continue
            di_vnd_seen.add(sogd)
            # VND Đi: tìm theo msgref
            m = ipcas_di_map.get(sogd)
            if m:
                citad_matched_di_ipcas.add(sogd)
                citad_cong_di[sogd] = r.get('cong')
                tt = m.get('trang_thai', '')
                if tt in VALID_DI:
                    # Khớp hoàn toàn
                    n_khop += 1
                    row = {
                        **r, 'status': 'both', 'key_agri': m.get('msgref', sogd),
                        'nh_nhan': m.get('nh_nhan', ''), 'trang_thai': tt,
                        # `refhub` chỉ có ở dòng gốc IPCAS (`m`), không có ở
                        # `r` (CITAD) — chép qua đây để cột "Số RefHub" ở
                        # exporters.py hiện ĐÚNG cho mọi lệnh có refhub, kể cả
                        # đã khớp (yêu cầu Phòng Thanh toán 09/09/2026, trước
                        # đó dòng khớp luôn trống vì merge không chép field
                        # này — chỉ dòng "Chỉ Agribank" chưa khớp mới có).
                        'refhub': m.get('refhub', ''),
                    }
                    ghi_chu = _ghi_chu_khop_du_nguon(
                        r.get('cong'), ipcas_identity_count.get(_ipcas_identity_key(m), 1), 1,
                        'IPCAS', 'đi')
                    if ghi_chu:
                        row['ghi_chu'] = ghi_chu
                    khop.append(row)
                else:
                    # Có ở cả 2 bên nhưng IPCAS chưa SCNL → lệch trạng thái
                    row = {
                        **r,
                        'status': 'lech_trang_thai',
                        'key_agri': m.get('msgref', sogd),
                        'nh_nhan': m.get('nh_nhan', ''),
                        'trang_thai': tt,
                    }
                    ghi_chu_parts = []
                    if tt in ERR_DI:
                        ghi_chu_parts.append(
                            f'IPCAS ghi nhận {tt} (thất bại) nhưng lệnh THỰC TẾ đã '
                            f'đi kênh CITAD thành công — cần kiểm tra lại'
                        )
                    # Dòng thừa (nếu có) đã tự hiện riêng ở vòng lặp "IPCAS Đi
                    # dư" bên dưới bất kể nhánh này — nhưng dòng CHÍNH ở đây
                    # (lech_trang_thai) trước đây không được gắn ghi_chú "N
                    # lần" như nhánh 'both' phía trên, dễ gây hiểu lầm là
                    # IPCAS không hề trùng. Gắn thêm cho nhất quán.
                    ghi_chu_dup = _ghi_chu_khop_du_nguon(
                        r.get('cong'), ipcas_identity_count.get(_ipcas_identity_key(m), 1), 1,
                        'IPCAS', 'đi')
                    if ghi_chu_dup:
                        ghi_chu_parts.append(ghi_chu_dup)
                    if ghi_chu_parts:
                        row['ghi_chu'] = ' | '.join(ghi_chu_parts)
                    lech.append(row)
            else:
                row = {**r, 'status': 'only_citad', 'key_agri': '', 'nh_nhan': '', 'trang_thai': ''}
                # Case đặc biệt (xác nhận Phòng Thanh toán 09/09/2026): lệnh
                # này rơi vào "Chỉ CITAD" KHÔNG PHẢI vì IPCAS thật sự không
                # có — mà vì IPCAS báo SCNL nhưng thiếu ngày kênh trả nên bị
                # loại khỏi diện tự động khớp (xem `nkt_thieu` ở parsers.py).
                # Lệnh RẤT CÓ THỂ vẫn tồn tại ở Agribank — gắn refhub để
                # người chấm tự tra cứu, không để trống như "Chỉ CITAD" thường.
                nkt_thieu_row = ipcas_di_nkt_thieu_map.get(sogd)
                if nkt_thieu_row:
                    row['refhub'] = nkt_thieu_row.get('refhub', '')
                lech.append(row)

        else:
            # VND Đến: giữ nguyên như cũ, không check trạng thái — khoá tra
            # cứu (sogd, loai, so_tien) khớp đúng cách build ipcas_den_map()
            # ở trên. Lệch số tiền dù trùng so_gd/txid+loai giờ KHÔNG còn
            # tính khớp nhầm — rơi xuống nhánh else, tự hiện ra ở nhóm "chỉ
            # CITAD" (và phía IPCAS tương ứng hiện ở "chỉ IPCAS" vì không
            # dòng CITAD nào khớp đúng khoá của nó).
            k_den = (sogd, r['loai'], r['so_tien'])
            m = ipcas_den_map.get(k_den)
            if m:
                n_khop += 1
                row = {
                    **r, 'status': 'both', 'key_agri': m.get('txid', sogd),
                    'nh_nhan': m.get('nh_nhan', ''), 'trang_thai': m.get('trang_thai', ''),
                    # Chép `refhub` từ dòng IPCAS đã khớp — xem ghi chú ở
                    # nhánh VND Đi phía trên, cùng lý do.
                    'refhub': m.get('refhub', ''),
                }
                citad_cong_den[k_den] = r.get('cong')
                ghi_chu = _ghi_chu_khop_du_nguon(
                    r.get('cong'), ipcas_identity_count.get(_ipcas_identity_key(m), 1),
                    citad_den_vnd_count.get(k_den, 1), 'IPCAS', 'đến')
                if ghi_chu:
                    row['ghi_chu'] = ghi_chu
                khop.append(row)
                citad_matched_den_ipcas.add(k_den)
            else:
                lech.append({**r, 'status': 'only_citad', 'key_agri': '', 'nh_nhan': '', 'trang_thai': ''})

    # IPCAS Đi dư - bỏ ERPO/CALD không khớp CITAD (thất bại bình thường,
    # chưa từng đi kênh — không phải chênh lệch cần xử lý, xem ERR_DI).
    #
    # Cùng vòng lặp này sinh thêm dòng THỪA khi dòng IPCAS "thắng" của khoá
    # này (r) bị LẶP LẠI Y HỆT (đếm theo khoá MỊN `_ipcas_identity_key`,
    # KHÔNG phải theo khoá khớp lệnh thô `k`) — đối xứng dup_citad: CITAD
    # chỉ có tối đa 1 lệnh cho 1 msgref, nên (n_dup - 1) dòng thừa đó là số
    # liệu IPCAS không có gì đối chứng, đúng bản chất "Chỉ IPCAS". Sinh CẢ
    # KHI khoá đã khớp CITAD (matched=True) lẫn chưa khớp — chỉ bỏ qua khi
    # dòng đại diện thuộc diện ERR_DI (thất bại bình thường, không phải
    # chênh lệch cần xử lý — matched luôn kéo theo tt=SCNL nên không bao
    # giờ rơi vào nhánh này).
    for k, r in ipcas_di_map.items():
        n_dup = ipcas_identity_count.get(_ipcas_identity_key(r), 1)
        matched = k in citad_matched_di_ipcas
        excluded = r.get('trang_thai') in ERR_DI
        if not matched and not excluded:
            # 'so_gd' để trống — xem ghi chú tương tự trong _dong_thua_nguon():
            # "Chỉ IPCAS" nghĩa là CITAD không có lệnh này, cột "Số GD (CITAD)"
            # không nên hiện số nào.
            lech.append({
                'so_gd': '', 'dich_vu': r.get('kenh', ''), 'loai': r.get('loai', ''),
                'chieu': 'di', 'loai_tien': 'VND', 'so_tien': r.get('so_tien', 0),
                'ngay': r.get('ngay', ''), 'status': 'only_ipcas',
                'key_agri': k, 'nh_nhan': r.get('nh_nhan', ''), 'trang_thai': r.get('trang_thai', ''),
                # `refhub` — dict này liệt kê tường minh từng field thay vì
                # `**r` nên thiếu field mới thêm sau (bug thật, phát hiện qua
                # ảnh chụp thật 09/09/2026: dòng "Chỉ IPCAS" — đúng nơi
                # refhub có sẵn 100% — lại trống trơn). `r` ở đây CHÍNH LÀ
                # dòng gốc IPCAS nên field này luôn có sẵn, không cần đi qua
                # đâu khác như 3 nhánh 'both' ở trên.
                'refhub': r.get('refhub', ''),
            })
        # n_citad: VND Đi luôn đúng 1 khi matched (CITAD trùng đã lọc riêng
        # thành dup_citad ở trên) — trừ thêm 1 khi KHÔNG matched vì dòng
        # "chỉ IPCAS" đại diện đã được sinh riêng ở nhánh `if not matched`
        # phía trên, tránh đếm dòng đó 2 lần (xem citad_den_vnd_count/
        # citad_hub_*_count ở đầu hàm để biết vì sao Đến/Hub cần đếm thật).
        n_citad = 1 if matched else 0
        so_thua = max(n_dup - n_citad - (0 if matched else 1), 0)
        if so_thua > 0 and (matched or not excluded):
            cong = citad_cong_di.get(k) if matched else None
            for _ in range(so_thua):
                lech.append(_dong_thua_nguon(r, 'di', k, 'only_ipcas', n_dup, n_citad, cong, 'IPCAS'))

    # IPCAS Đến dư — k là tuple (txid, loai, so_tien), xem ghi_chú build
    # ipcas_den_map() ở trên; 'key_agri' xuất ra báo cáo chỉ cần phần txid
    # (k[0]), 'so_gd' để trống (xem ghi chú only_ipcas ở nhánh Đi phía
    # trên), 'loai'/'so_tien' lấy thẳng từ r cho đúng. Sinh dòng thừa cùng
    # cách với Đi ở trên.
    #
    # ĐÃ BỎ ngoại lệ PYED/PYEK (có từ 20/08, "đang xử lý nên chưa tính
    # chênh lệch") — xác nhận nghiệp vụ 23/08/2026 (Phòng Thanh toán), phát
    # hiện qua tự kiểm thử: thêm 1 lệnh KHÔNG CÓ THẬT (không khớp CITAD nào)
    # mang trạng thái PYED vào file IPCAS, đối soát không báo gì — vì ngoại
    # lệ này không phân biệt được "PYED thật đang chờ CITAD xử lý" với "PYED
    # giả/bất thường sẽ không bao giờ có CITAD tương ứng". Nguyên tắc đúng:
    # "chênh lệch SỐ LƯỢNG lệnh áp dụng cho MỌI trạng thái, không riêng gì
    # trạng thái nào" — không có CITAD khớp thì luôn phải hiện, bất kể
    # PYED/PYEK/RFED/SBSC hay gì khác.
    for k, r in ipcas_den_map.items():
        n_dup = ipcas_identity_count.get(_ipcas_identity_key(r), 1)
        matched = k in citad_matched_den_ipcas
        excluded = False
        if not matched and not excluded:
            lech.append({
                'so_gd': '', 'dich_vu': r.get('kenh', ''), 'loai': r.get('loai', ''),
                'chieu': 'den', 'loai_tien': 'VND', 'so_tien': r.get('so_tien', 0),
                'ngay': r.get('ngay', ''), 'status': 'only_ipcas',
                'key_agri': k[0], 'nh_nhan': r.get('nh_nhan', ''), 'trang_thai': r.get('trang_thai', ''),
                'refhub': r.get('refhub', ''),  # xem ghi chú nhánh Đi phía trên
            })
        # n_citad = số dòng CITAD Đến THẬT trùng khoá này (có thể > 1 — xem
        # ghi chú citad_den_vnd_count ở đầu hàm), KHÔNG giả định luôn là 1.
        n_citad = citad_den_vnd_count.get(k, 0) if matched else 0
        so_thua = max(n_dup - n_citad - (0 if matched else 1), 0)
        if so_thua > 0:
            cong = citad_cong_den.get(k) if matched else None
            for _ in range(so_thua):
                lech.append(_dong_thua_nguon(r, 'den', k[0], 'only_ipcas', n_dup, n_citad, cong, 'IPCAS'))

    # Hub dư — áp dụng ĐÚNG cơ chế đếm/sinh dòng thừa như IPCAS ở trên cho
    # ngoại tệ (USD/EUR...), không riêng VND — Hub không có trạng thái nào
    # cần loại trừ (khác ERR_DI/PYED-PYEK của IPCAS) nên không có `excluded`.
    for k, r in hub_di_map.items():
        n_dup = hub_identity_count.get(_hub_identity_key(r), 1)
        matched = k in citad_matched_di_hub
        if not matched:
            lech.append({**r, 'so_gd': '', 'status': 'only_hub', 'key_agri': k, 'trang_thai': ''})
        # n_citad = số dòng CITAD ngoại tệ THẬT trùng so_gd này (có thể > 1
        # — xem ghi chú citad_hub_di_count ở đầu hàm), KHÔNG giả định 1.
        n_citad = citad_hub_di_count.get(k, 0) if matched else 0
        so_thua = max(n_dup - n_citad - (0 if matched else 1), 0)
        if so_thua > 0:
            cong = citad_cong_hub_di.get(k) if matched else None
            for _ in range(so_thua):
                lech.append(_dong_thua_nguon(r, 'di', k, 'only_hub', n_dup, n_citad, cong, 'Hub'))
    for k, r in hub_den_map.items():
        n_dup = hub_identity_count.get(_hub_identity_key(r), 1)
        matched = k in citad_matched_den_hub
        if not matched:
            lech.append({**r, 'so_gd': '', 'status': 'only_hub', 'key_agri': k, 'trang_thai': ''})
        # n_citad = số dòng CITAD ngoại tệ THẬT trùng so_gd này (có thể > 1
        # — xem ghi chú citad_hub_den_count ở đầu hàm), KHÔNG giả định 1.
        n_citad = citad_hub_den_count.get(k, 0) if matched else 0
        so_thua = max(n_dup - n_citad - (0 if matched else 1), 0)
        if so_thua > 0:
            cong = citad_cong_hub_den.get(k) if matched else None
            for _ in range(so_thua):
                lech.append(_dong_thua_nguon(r, 'den', k, 'only_hub', n_dup, n_citad, cong, 'Hub'))

    return n_khop, lech, khop
