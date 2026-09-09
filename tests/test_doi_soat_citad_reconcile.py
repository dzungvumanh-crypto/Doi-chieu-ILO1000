# -*- coding: utf-8 -*-
"""
test_doi_soat_citad_reconcile.py
---------------------------------
Test thuật toán khớp lệnh `backend/services/doi_soat_citad/reconcile.py`.

Trước bộ test này, module KHÔNG có test tự động nào (chỉ kiểm bằng tay với
1 bộ dữ liệu thật) — dù đây là nơi vừa phát hiện 2 lỗi sai số liệu thật
(20/08/2026): file Hub bị bỏ trắng vì đọc nhầm dòng "Tổng số giao dịch",
và txid IPCAS dùng chung cho nhiều lệnh khác nhau đè mất lệnh thật.

Bộ test này khoá lại quy tắc khớp (Đi/Đến × VND/ngoại tệ) và đặc biệt là
"CITAD gửi trùng" cho VND Đi — bug thật đã xác nhận (20/08/2026).

Đã THỬ mở rộng chốt chặn dup này sang VND Đến + ngoại tệ (22/08/2026) rồi
RÚT LẠI ngay trong ngày: kiểm bằng đúng dữ liệu thật 19/08/2026 phát hiện
VND Đến có 1.154 nhóm (so_gd, loai, so_tien) lặp thật trong 1 ngày — phần
lớn (942 nhóm) do CITAD đánh số so_gd RIÊNG theo từng cổng (cổng 1, 9, 12,
17, 18), số trùng giữa 2 cổng không phải trùng thật. Không đủ căn cứ
nghiệp vụ để phân biệt trùng thật/giả cho Đến, và áp nhầm làm mất ~1.400
lệnh khớp thật mỗi ngày. Các test dưới đây khoá lại ĐÚNG phạm vi hiện tại
(chỉ Đi) và khoá luôn việc KHÔNG được coi 2 lệnh Đến trùng so_gd là dup.
"""
from backend.services.doi_soat_citad import parsers
from backend.services.doi_soat_citad.reconcile import run_doiSoat_ram


def _citad(so_gd, chieu='di', loai_tien='VND', loai='il', so_tien=1000, cong='1', **kw):
    row = {
        'so_gd': so_gd, 'dich_vu': 'Chuyển có giá trị thấp', 'loai': loai,
        'chieu': chieu, 'loai_tien': loai_tien, 'so_tien': so_tien,
        'ngay': '19/08/2026', 'cong': cong,
    }
    row.update(kw)
    return row


def _ipcas(chieu='di', msgref='', txid='', loai='il', so_tien=1000,
           trang_thai='SCNL', **kw):
    row = {
        'txid': txid, 'msgref': msgref, 'loai': loai, 'chieu': chieu,
        'so_tien': so_tien, 'trang_thai': trang_thai, 'nkt': '',
        'kenh': '', 'nh_nhan': 'NH TEST', 'ngay': '19/08/2026',
    }
    row.update(kw)
    return row


def _hub(so_gd, chieu='di', loai_tien='USD', so_tien=500, trang_thai='', **kw):
    row = {
        'so_gd': so_gd, 'loai': 'ih', 'chieu': chieu, 'loai_tien': loai_tien,
        'so_tien': so_tien, 'nh_nhan': 'NH HUB', 'ngay': '19/08/2026',
        'trang_thai': trang_thai,
    }
    row.update(kw)
    return row


# ── VND Đi ──────────────────────────────────────────────────────────
def test_vnd_di_khop_scnl():
    citad = [_citad('100001', chieu='di')]
    ipcas = [_ipcas(chieu='di', msgref='100001', trang_thai='SCNL')]
    n_khop, lech, khop = run_doiSoat_ram(citad, ipcas, [])
    assert n_khop == 1
    assert lech == []
    assert khop[0]['status'] == 'both'


def test_vnd_di_khop_chep_refhub_tu_ipcas():
    """Bug thật (review 09/09/2026, ảnh chụp thật): dòng ĐÃ KHỚP trước đây
    trống cột "Số RefHub" dù lệnh CÓ tồn tại ở Agribank — vì dòng 'both'
    được dựng từ `{**r, ...}` (r = CITAD, không có refhub), chỉ chép đúng
    3 field key_agri/nh_nhan/trang_thai từ `m` (IPCAS), bỏ sót refhub. `m`
    (IPCAS) LUÔN có field này (`_parse_ipcas_text`) nên phải chép qua."""
    citad = [_citad('100005', chieu='di')]
    ipcas = [_ipcas(chieu='di', msgref='100005', trang_thai='SCNL', refhub='RH-DI-100005')]
    n_khop, lech, khop = run_doiSoat_ram(citad, ipcas, [])
    assert n_khop == 1
    assert khop[0]['refhub'] == 'RH-DI-100005'


def test_vnd_di_lech_trang_thai_khong_scnl():
    citad = [_citad('100002', chieu='di')]
    ipcas = [_ipcas(chieu='di', msgref='100002', trang_thai='WFPG')]
    n_khop, lech, khop = run_doiSoat_ram(citad, ipcas, [])
    assert n_khop == 0
    assert lech[0]['status'] == 'lech_trang_thai'
    assert lech[0]['trang_thai'] == 'WFPG'


def test_vnd_di_lech_trang_thai_van_ghi_chu_khi_ipcas_trung():
    """Nhất quán với nhánh 'both' (khớp SCNL): dòng lech_trang_thai (IPCAS
    chưa SCNL) mà IPCAS cũng có dữ liệu trùng thì vẫn phải ghi rõ ở ghi_chú
    — trước đây chỉ nhánh 'both' mới gắn ghi_chú này, nhánh lech_trang_thai
    im lặng dù dòng "Chỉ IPCAS" thừa vẫn tự hiện riêng (dễ gây hiểu lầm là
    IPCAS không trùng khi nhìn đúng dòng lech_trang_thai)."""
    citad = [_citad('500001', chieu='di', cong='9')]
    ipcas = [
        _ipcas(chieu='di', msgref='500001', trang_thai='WFPG'),
        _ipcas(chieu='di', msgref='500001', trang_thai='WFPG'),
    ]
    n_khop, lech, khop = run_doiSoat_ram(citad, ipcas, [])
    assert n_khop == 0
    lech_tt = [r for r in lech if r['status'] == 'lech_trang_thai']
    assert len(lech_tt) == 1
    assert '2 lần' in lech_tt[0]['ghi_chu']


def test_vnd_di_erpo_voi_citad_la_bat_thuong():
    """IPCAS báo ERPO (thất bại) nhưng CITAD lại CÓ lệnh này → bất thường
    thật (đi kênh thành công), phải bắt vào lech_trang_thai kèm ghi chú,
    KHÔNG được coi là bình thường rồi bỏ qua."""
    citad = [_citad('100003', chieu='di')]
    ipcas = [_ipcas(chieu='di', msgref='100003', trang_thai='ERPO')]
    n_khop, lech, khop = run_doiSoat_ram(citad, ipcas, [])
    assert n_khop == 0
    assert lech[0]['status'] == 'lech_trang_thai'
    assert 'kiểm tra lại' in lech[0]['ghi_chu']


def test_scnl_thieu_ngay_kenh_tra_rot_vao_chi_citad_kem_refhub():
    """Case đặc biệt (xác nhận Phòng Thanh toán 09/09/2026): IPCAS báo SCNL
    (đã sang kênh) nhưng thiếu ngày kênh trả (`nkt_thieu=True`, xem
    parsers.py) — KHÔNG được tự động khớp (giữ nguyên ý gốc 27/08/2026,
    lệnh CITAD rơi đúng vào "Chỉ CITAD" để người chấm tự xác minh), nhưng
    KHÁC "Chỉ CITAD" thường (không hề có gì bên IPCAS): lệnh này rất có thể
    vẫn tồn tại thật ở Agribank, nên dòng "Chỉ CITAD" phải kèm `refhub` để
    người chấm tự tra cứu, không được để trống."""
    citad = [_citad('900001', chieu='di')]
    ipcas = [_ipcas(chieu='di', msgref='900001', trang_thai='SCNL',
                     refhub='RH-NKTTHIEU-900001', nkt_thieu=True)]
    n_khop, lech, khop = run_doiSoat_ram(citad, ipcas, [])
    assert n_khop == 0
    assert khop == []
    assert len(lech) == 1
    assert lech[0]['status'] == 'only_citad'
    assert lech[0]['refhub'] == 'RH-NKTTHIEU-900001'


def test_nkt_thieu_khong_lam_dong_khop_khac_bi_tinh_nham_la_trung():
    """Bug thật (rà soát 09/09/2026, phát hiện sau khi thêm cờ `nkt_thieu`):
    dòng IPCAS 'di' SCNL-thiếu-ngày-kênh-trả trước đây bị `continue` ngay ở
    parsers.py — KHÔNG BAO GIỜ vào `ipcas_identity_count`. Từ khi giữ lại
    dòng này (nkt_thieu=True) để lấy refhub, nó vẫn CỘNG VÀO
    `ipcas_identity_count` theo khoá mịn (khoá này KHÔNG có msgref) — nếu
    tình cờ trùng khoá mịn với 1 dòng KHỚP khác (msgref khác), dòng khớp
    kia bị tính nhầm "IPCAS ghi nhận 2 lần" và còn sinh thêm 1 dòng "Chỉ
    IPCAS" ma không có thật, trong khi dòng nkt_thieu đã tự có đại diện
    đúng riêng (dòng "Chỉ CITAD" kèm refhub) — báo trùng 2 lần cho đúng 1
    chênh lệch."""
    citad = [
        _citad('950001', chieu='di'),  # khớp bình thường
        _citad('950002', chieu='di'),  # rơi vào "Chỉ CITAD" vì IPCAS thiếu ngày kênh trả
    ]
    ipcas = [
        _ipcas(chieu='di', msgref='950001', trang_thai='SCNL'),
        _ipcas(chieu='di', msgref='950002', trang_thai='SCNL', nkt_thieu=True,
               refhub='RH-950002'),
    ]
    n_khop, lech, khop = run_doiSoat_ram(citad, ipcas, [])
    assert n_khop == 1
    assert khop[0]['status'] == 'both'
    assert not khop[0].get('ghi_chu')  # KHÔNG được báo "2 lần" sai
    assert len(lech) == 1
    assert lech[0]['status'] == 'only_citad'
    assert lech[0]['refhub'] == 'RH-950002'
    assert not any(r['status'] == 'only_ipcas' for r in lech)  # không dòng ma


def test_vnd_di_erpo_khong_co_citad_bi_bo_qua():
    """ERPO/CALD mà CITAD KHÔNG có → thất bại bình thường (chưa từng đi
    kênh), không được tính vào 'chỉ IPCAS'."""
    citad = []
    ipcas = [_ipcas(chieu='di', msgref='100004', trang_thai='ERPO')]
    n_khop, lech, khop = run_doiSoat_ram(citad, ipcas, [])
    assert n_khop == 0
    assert lech == []


# ── VND Đến ─────────────────────────────────────────────────────────
def test_vnd_den_khop_theo_txid_loai_so_tien():
    citad = [_citad('200001', chieu='den', loai='il', so_tien=5000)]
    ipcas = [_ipcas(chieu='den', txid='200001', loai='il', so_tien=5000, trang_thai='SBSC')]
    n_khop, lech, khop = run_doiSoat_ram(citad, ipcas, [])
    assert n_khop == 1
    assert lech == []


def test_vnd_den_khop_chep_refhub_tu_ipcas():
    """Cùng lỗi/cùng lý do với nhánh VND Đi — xem
    test_vnd_di_khop_chep_refhub_tu_ipcas()."""
    citad = [_citad('200002', chieu='den', loai='il', so_tien=5000)]
    ipcas = [_ipcas(chieu='den', txid='200002', loai='il', so_tien=5000,
                     trang_thai='SBSC', refhub='RH-DEN-200002')]
    n_khop, lech, khop = run_doiSoat_ram(citad, ipcas, [])
    assert n_khop == 1
    assert khop[0]['refhub'] == 'RH-DEN-200002'


def test_vnd_den_txid_dung_chung_khong_de_mat_lenh_that():
    """IPCAS dùng chung 1 txid cho 2 lệnh khác nhau (khác loai/so_tien) —
    khoá 3 phần (txid, loai, so_tien) phải tách đúng 2 lệnh độc lập, không
    để dòng PYED (ưu tiên cao hơn SBSC) đè mất dòng SBSC thật (regression
    lỗi thật 19/08/2026)."""
    citad = [
        _citad('300001', chieu='den', loai='ih', so_tien=900_000_000),  # Napas/PSS-MDP giá trị cao
    ]
    ipcas = [
        _ipcas(chieu='den', txid='300001', loai='ih', so_tien=900_000_000, trang_thai='SBSC'),
        _ipcas(chieu='den', txid='300001', loai='il', so_tien=15_000, trang_thai='PYED'),
    ]
    n_khop, lech, khop = run_doiSoat_ram(citad, ipcas, [])
    assert n_khop == 1
    assert khop[0]['trang_thai'] == 'SBSC'
    # Dòng IL/PYED không có CITAD tương ứng — từ 23/08/2026 KHÔNG còn bị
    # loại vì lý do trạng thái PYED nữa (xem test riêng ở dưới), phải hiện
    # thành "Chỉ IPCAS".
    assert len(lech) == 1
    assert lech[0]['status'] == 'only_ipcas'
    assert lech[0]['trang_thai'] == 'PYED'


def test_vnd_den_lenh_chuyen_chi_nhanh_dong_goc_cgbr_luon_thang():
    """Xác nhận nghiệp vụ 23/08/2026 (Phòng Thanh toán) + tài liệu bàn giao
    gốc (mục "Lệnh chuyển chi nhánh Đến ... chỉ tính dòng gốc"): IPCAS ghi
    lệnh chuyển chi nhánh thành 2 dòng CÙNG (txid, loai, so_tien) — dòng
    GỐC (CGBR) và dòng CON (RFED, ở chi nhánh khác, chỉ là thao tác nội bộ
    IPCAS). Dòng gốc PHẢI thắng ưu tiên, không phải dòng con — trước khi
    thêm CGBR vào PRIORITY_TT, CGBR không có trong bảng nên bị coi ưu tiên
    thấp nhất, dòng con (RFED) thắng NHẦM (regression thật 19/08/2026)."""
    citad = [_citad('400002', chieu='den', loai='il', so_tien=3_632_794)]
    ipcas = [
        _ipcas(chieu='den', txid='400002', loai='il', so_tien=3_632_794,
               trang_thai='RFED', nh_nhan='NH CON'),
        _ipcas(chieu='den', txid='400002', loai='il', so_tien=3_632_794,
               trang_thai='CGBR', nh_nhan='NH GOC'),
    ]
    n_khop, lech, khop = run_doiSoat_ram(citad, ipcas, [])
    assert n_khop == 1
    assert khop[0]['trang_thai'] == 'CGBR'
    assert khop[0]['nh_nhan'] == 'NH GOC'
    # Dòng con thua bị loại hẳn khỏi map — không tạo dòng "Chỉ IPCAS" giả
    # (đúng ý "không phải chênh lệch, chỉ là hoạt động nội bộ").
    assert lech == []


def test_vnd_den_hai_lenh_that_cung_so_gd_khac_so_tien_khong_bi_coi_la_dup():
    """2 lệnh Đến THẬT khác nhau (khác so_tien) trùng so_gd — không phải
    lỗi dup CITAD, phải khớp cả 2 với đúng 2 dòng IPCAS tương ứng, KHÔNG
    được gộp thành 1 dòng 'dup_citad'."""
    citad = [
        _citad('400001', chieu='den', loai='il', so_tien=1000),
        _citad('400001', chieu='den', loai='il', so_tien=2000),
    ]
    ipcas = [
        _ipcas(chieu='den', txid='400001', loai='il', so_tien=1000, trang_thai='SBSC'),
        _ipcas(chieu='den', txid='400001', loai='il', so_tien=2000, trang_thai='SBSC'),
    ]
    n_khop, lech, khop = run_doiSoat_ram(citad, ipcas, [])
    assert n_khop == 2
    assert lech == []
    assert not any(r['status'] == 'dup_citad' for r in khop + lech)


def test_vnd_den_cap_nsnn_khac_dich_vu_khong_bi_coi_la_dup():
    """Ca quan sát được ở dữ liệu khác (22/08/2026): lệnh Đến có thu NSNN —
    CITAD tách thành 2 dòng THẬT cùng so_gd/loai/so_tien nhưng khác
    dich_vu (dòng chính + dòng phụ '...(có thông tin thu NSNN)'). Không
    được gạt dòng thứ 2 thành 'dup_citad' — cả 2 phải khớp độc lập, đúng
    phạm vi hiện tại (Đến không có chốt chặn dup)."""
    citad = [
        _citad('900001', chieu='den', loai='il', so_tien=51_968_000, dich_vu='CITAD THAP'),
        _citad('900001', chieu='den', loai='il', so_tien=51_968_000,
                dich_vu='Chuyển có giá trị thấp (có thông tin thu NSNN)'),
    ]
    ipcas = [_ipcas(chieu='den', txid='900001', loai='il', so_tien=51_968_000, trang_thai='SBSC')]
    n_khop, lech, khop = run_doiSoat_ram(citad, ipcas, [])
    assert not any(r['status'] == 'dup_citad' for r in lech)
    assert n_khop == 2
    assert len(khop) == 2
    assert all(r['status'] == 'both' for r in khop)


def test_vnd_den_trung_so_gd_khac_cong_khong_bi_coi_la_dup():
    """Regression thật (dữ liệu 19/08/2026): CITAD đánh số so_gd RIÊNG theo
    từng cổng (1, 9, 12, 17, 18) — 2 dòng Đến trùng y hệt so_gd/loai/so_tien
    nhưng khác `cong` là 2 lệnh THẬT độc lập (942/1.154 nhóm trùng thật
    trong ngày rơi vào ca này), không phải CITAD gửi trùng. Đến hiện KHÔNG
    có chốt chặn dup nên cả 2 phải khớp bình thường — khoá lại để không ai
    vô tình thêm lại chốt chặn dup cho Đến mà chưa xác nhận được quy tắc
    đúng (xem docstring module)."""
    citad = [
        _citad('1000001', chieu='den', loai='ih', so_tien=500_000_000, cong='1'),
        _citad('1000001', chieu='den', loai='ih', so_tien=500_000_000, cong='9'),
    ]
    ipcas = [_ipcas(chieu='den', txid='1000001', loai='ih', so_tien=500_000_000, trang_thai='SBSC')]
    n_khop, lech, khop = run_doiSoat_ram(citad, ipcas, [])
    assert not any(r['status'] == 'dup_citad' for r in khop + lech)
    assert n_khop == 2


# ── Ngoại tệ (Hub) ──────────────────────────────────────────────────
def test_ngoai_te_di_khop_hub():
    citad = [_citad('600001', chieu='di', loai_tien='USD')]
    hub = [_hub('600001', chieu='di', loai_tien='USD')]
    n_khop, lech, khop = run_doiSoat_ram(citad, [], hub)
    assert n_khop == 1
    assert lech == []


def test_ngoai_te_den_khop_hub():
    citad = [_citad('600002', chieu='den', loai_tien='EUR')]
    hub = [_hub('600002', chieu='den', loai_tien='EUR')]
    n_khop, lech, khop = run_doiSoat_ram(citad, [], hub)
    assert n_khop == 1
    assert lech == []


def test_ngoai_te_khong_khop_hub_la_only_citad():
    citad = [_citad('700003', chieu='di', loai_tien='USD')]
    n_khop, lech, khop = run_doiSoat_ram(citad, [], [])
    assert n_khop == 0
    assert lech[0]['status'] == 'only_citad'


def test_hub_du_khong_khop_citad_la_only_hub():
    hub = [_hub('700004', chieu='di', loai_tien='USD')]
    n_khop, lech, khop = run_doiSoat_ram([], [], hub)
    assert n_khop == 0
    assert lech[0]['status'] == 'only_hub'


def test_ngoai_te_lenh_chuyen_chi_nhanh_dong_goc_da_tra_kh_luon_thang():
    """Xác nhận nghiệp vụ 23/08/2026 (Phòng Thanh toán): Hub ngoại tệ cũng
    có lệnh chuyển chi nhánh như IPCAS — cùng Số thành công, dòng GỐC mang
    trạng thái "Đã trả KH", dòng còn lại là chi nhánh trung gian. Dòng gốc
    phải luôn thắng khi trùng Số thành công, và cặp gốc/con KHÔNG được coi
    là "Hub ghi nhận trùng" (khác trạng thái nên khác khoá mịn)."""
    citad = [_citad('800001', chieu='den', loai_tien='USD', so_tien=2000)]
    hub = [
        _hub('800001', chieu='den', loai_tien='USD', so_tien=2000,
             trang_thai='Đang xử lý', nh_nhan='NH CON'),
        _hub('800001', chieu='den', loai_tien='USD', so_tien=2000,
             trang_thai='Đã trả KH', nh_nhan='NH GOC'),
    ]
    n_khop, lech, khop = run_doiSoat_ram(citad, [], hub)
    assert n_khop == 1
    assert khop[0]['nh_nhan'] == 'NH GOC'
    assert not khop[0].get('ghi_chu')
    assert lech == []


# ── IPCAS Đến dư ────────────────────────────────────────────────────
def test_ipcas_den_pyed_khong_khop_van_hien_chi_ipcas():
    """Xác nhận nghiệp vụ 23/08/2026 (Phòng Thanh toán), phát hiện qua tự
    kiểm thử: thêm 1 lệnh KHÔNG CÓ THẬT (không khớp CITAD nào) mang trạng
    thái PYED vào IPCAS, đối soát không báo gì — vì ngoại lệ cũ (PYED/PYEK
    "đang xử lý" nên bỏ qua) không phân biệt được PYED thật đang chờ CITAD
    với PYED giả sẽ không bao giờ có CITAD. Nguyên tắc đúng: chênh lệch SỐ
    LƯỢNG lệnh áp dụng cho MỌI trạng thái — PYED/PYEK KHÔNG còn là ngoại lệ,
    phải hiện 'only_ipcas' như mọi trạng thái khác."""
    ipcas = [_ipcas(chieu='den', txid='800001', loai='il', so_tien=1000, trang_thai='PYED')]
    n_khop, lech, khop = run_doiSoat_ram([], ipcas, [])
    assert n_khop == 0
    assert len(lech) == 1
    assert lech[0]['status'] == 'only_ipcas'
    assert lech[0]['trang_thai'] == 'PYED'


def test_ipcas_den_sbsc_khong_khop_la_only_ipcas():
    ipcas = [_ipcas(chieu='den', txid='800002', loai='il', so_tien=1000, trang_thai='SBSC')]
    n_khop, lech, khop = run_doiSoat_ram([], ipcas, [])
    assert n_khop == 0
    assert lech[0]['status'] == 'only_ipcas'


def test_only_ipcas_de_trong_cot_so_gd_citad():
    """Phát hiện qua câu hỏi trực tiếp của người dùng (23/08/2026): dòng
    "Chỉ IPCAS" trước đây hiện CÙNG 1 số ở cả cột "Số GD (CITAD)" lẫn "Số
    GD (Agribank)" — sai, vì "Chỉ IPCAS" nghĩa là CITAD KHÔNG hề có lệnh
    này. Đúng đối xứng với "Chỉ CITAD" (để trống cột Agribank): "Chỉ IPCAS"
    phải để trống cột CITAD, chỉ cột Agribank (`key_agri`) có số."""
    ipcas = [_ipcas(chieu='di', msgref='800003', trang_thai='SCNL')]
    n_khop, lech, khop = run_doiSoat_ram([], ipcas, [])
    assert lech[0]['status'] == 'only_ipcas'
    assert lech[0]['so_gd'] == ''
    assert lech[0]['key_agri'] == '800003'


def test_only_ipcas_giu_dung_refhub():
    """Bug thật (review 09/09/2026, ảnh chụp thật — đây CHÍNH LÀ trường hợp
    trong ảnh, dòng "Chỉ IPCAS" chưa khớp): dict dòng 'only_ipcas' liệt kê
    tường minh từng field thay vì `{**r, ...}` nên thiếu hẳn `refhub`, dù
    `r` (dòng gốc IPCAS) LUÔN có sẵn field này."""
    ipcas = [_ipcas(chieu='di', msgref='800004', trang_thai='SCNL', refhub='RH-ONLY-800004')]
    n_khop, lech, khop = run_doiSoat_ram([], ipcas, [])
    assert lech[0]['status'] == 'only_ipcas'
    assert lech[0]['refhub'] == 'RH-ONLY-800004'


def test_only_hub_de_trong_cot_so_gd_citad():
    hub = [_hub('900002', chieu='di', loai_tien='USD')]
    n_khop, lech, khop = run_doiSoat_ram([], [], hub)
    assert lech[0]['status'] == 'only_hub'
    assert lech[0]['so_gd'] == ''
    assert lech[0]['key_agri'] == '900002'


# ── Nguồn đối ứng (IPCAS/Hub) hạch toán trùng (CITAD 1 lần, nguồn N lần) ─
# Phát hiện thật (23/08/2026): người dùng tự dán thêm dòng y hệt vào file
# IPCAS nguồn để kiểm tra, đối soát KHÔNG báo gì — vì _parse_ipcas_text()
# bỏ âm thầm dòng trùng lúc đọc file, trước khi tới bước đối soát. Đây là
# chiều NGƯỢC LẠI của dup_citad (CITAD gửi trùng, nguồn đối ứng chỉ 1
# dòng): ở đây CITAD chỉ 1 dòng, IPCAS/Hub mới là bên hạch toán trùng.
#
# Thiết kế: (n_dup - 1) dòng thừa phải tự hiện thành dòng "Chỉ IPCAS"/"Chỉ
# Hub" RIÊNG (không chỉ 1 câu ghi chú trên dòng đã khớp) — đúng bản chất
# CITAD chỉ xác nhận 1 lệnh, phần dư ra là số liệu không có gì đối chứng.
# Đếm theo SỐ DÒNG THẬT trong danh sách truyền vào (không phải 1 field
# đếm sẵn) — parsers.py không còn lọc bỏ dòng trùng nữa, xem test cuối file.
def test_vnd_di_ipcas_dup_sinh_dong_thua_va_ghi_ro_cong():
    citad = [_citad('110001', chieu='di', cong='9')]
    ipcas = [
        _ipcas(chieu='di', msgref='110001', trang_thai='SCNL'),
        _ipcas(chieu='di', msgref='110001', trang_thai='SCNL'),
        _ipcas(chieu='di', msgref='110001', trang_thai='SCNL'),
    ]
    n_khop, lech, khop = run_doiSoat_ram(citad, ipcas, [])
    assert n_khop == 1  # chỉ tính khớp 1 lần dù IPCAS có 3 dòng
    assert khop[0]['status'] == 'both'
    assert '3 lần' in khop[0]['ghi_chu']
    assert 'cổng CITAD 9' in khop[0]['ghi_chu']
    # 2 dòng thừa (3 - 1) phải tự hiện thành "Chỉ IPCAS" riêng
    du = [r for r in lech if r['status'] == 'only_ipcas']
    assert len(du) == 2
    for r in du:
        assert '3 lần' in r['ghi_chu']
        assert 'cổng 9' in r['ghi_chu']


def test_vnd_den_ipcas_dup_sinh_dong_thua_va_ghi_ro_cong():
    citad = [_citad('110002', chieu='den', loai='il', so_tien=2000, cong='1')]
    ipcas = [
        _ipcas(chieu='den', txid='110002', loai='il', so_tien=2000, trang_thai='SBSC'),
        _ipcas(chieu='den', txid='110002', loai='il', so_tien=2000, trang_thai='SBSC'),
    ]
    n_khop, lech, khop = run_doiSoat_ram(citad, ipcas, [])
    assert n_khop == 1
    assert '2 lần' in khop[0]['ghi_chu']
    du = [r for r in lech if r['status'] == 'only_ipcas']
    assert len(du) == 1
    assert 'cổng 1' in du[0]['ghi_chu']


def test_vnd_den_ipcas_dup_khac_trace_van_tinh_la_trung():
    """Regression thật (23/08/2026, phát hiện qua tự kiểm thử — xoá thử 1
    dòng để test): 3 dòng IPCAS giống hệt nhau mọi trường (chi nhánh, ngân
    hàng, trạng thái, ngày, số tiền) nhưng KHÁC trace — trước khi sửa,
    dòng thứ 3 (trace khác 2 dòng kia) rơi ra 1 khoá nhận dạng riêng, biến
    mất hoàn toàn khỏi báo cáo (không khớp, không "Chỉ IPCAS"). trace
    KHÔNG được coi là tín hiệu phân biệt — IPCAS có thể cấp trace mới mỗi
    lần ghi trùng 1 bút toán."""
    citad = [_citad('120001', chieu='den', loai='il', so_tien=24_566_000, cong='9')]
    ipcas = [
        _ipcas(chieu='den', txid='120001', loai='il', so_tien=24_566_000,
               trang_thai='RFED', chi_nhanh='2000', trace='001'),
        _ipcas(chieu='den', txid='120001', loai='il', so_tien=24_566_000,
               trang_thai='RFED', chi_nhanh='2000', trace='001'),
        _ipcas(chieu='den', txid='120001', loai='il', so_tien=24_566_000,
               trang_thai='RFED', chi_nhanh='2000', trace='002'),  # trace khác
    ]
    n_khop, lech, khop = run_doiSoat_ram(citad, ipcas, [])
    assert n_khop == 1
    assert '3 lần' in khop[0]['ghi_chu']
    # Cả 2 dòng thừa đều phải hiện — không dòng nào biến mất vì khác trace
    du = [r for r in lech if r['status'] == 'only_ipcas']
    assert len(du) == 2


def test_vnd_den_citad_trung_2_dong_ipcas_trung_3_dong_chi_du_1():
    """Bug thật (23/08/2026, phát hiện qua câu hỏi trực tiếp của người
    dùng: "lệch có chắc CITAD không có không, nếu đủ cả 2 bên thì không
    phải lệch"). VND Đến CHO PHÉP CITAD tự trùng khoá thật (đã xác nhận
    1.154 nhóm ngày 19/08/2026) — code cũ giả định CITAD luôn chỉ có 1
    dòng cho mỗi khoá khi tính dòng thừa, nên CITAD trùng 2 + IPCAS trùng 3
    sẽ bị báo dư SAI 2 dòng (3-1) thay vì ĐÚNG 1 dòng (3-2), kèm ghi chú
    sai "CITAD chỉ có 1 lệnh" dù CITAD thật có 2."""
    citad = [
        _citad('130001', chieu='den', loai='il', so_tien=5000, cong='1'),
        _citad('130001', chieu='den', loai='il', so_tien=5000, cong='1'),
    ]
    ipcas = [
        _ipcas(chieu='den', txid='130001', loai='il', so_tien=5000, trang_thai='SBSC', trace='001'),
        _ipcas(chieu='den', txid='130001', loai='il', so_tien=5000, trang_thai='SBSC', trace='002'),
        _ipcas(chieu='den', txid='130001', loai='il', so_tien=5000, trang_thai='SBSC', trace='003'),
    ]
    n_khop, lech, khop = run_doiSoat_ram(citad, ipcas, [])
    assert n_khop == 2
    du = [r for r in lech if r['status'] == 'only_ipcas']
    assert len(du) == 1
    assert 'CITAD chỉ có 2 lệnh' in du[0]['ghi_chu']
    # Câu ghi chú trên 2 dòng ĐÃ khớp cũng phải nói đúng "khớp 2 lần — xem
    # thêm 1 dòng" — bug thật khác (rà soát 23/08/2026): _ghi_chu_khop_du_nguon
    # từng viết cứng "chỉ tính khớp 1 lần" bất kể CITAD thật khớp bao nhiêu.
    for r in khop:
        assert 'khớp 2 lần' in r['ghi_chu']
        assert 'xem thêm 1 dòng' in r['ghi_chu']


def test_ipcas_den_hach_toan_nham_huy_loai_khoi_dem():
    """Xác nhận nghiệp vụ 23/08/2026 (Phòng Thanh toán) — giải thích ĐÚNG
    nguyên nhân hiện tượng "trùng trace" ở card 100: GDV hạch toán thủ công
    lệnh Đến nhầm chi nhánh, phải HUỶ (bút toán huỷ dùng LẠI trace của bút
    toán nhầm — cùng chi nhánh) rồi hạch toán lại ĐÚNG (trace MỚI). Cặp
    trùng chi nhánh+trace phải bị loại HOÀN TOÀN, không tính khớp thừa,
    không hiện "Chỉ IPCAS" — chỉ dòng trace riêng dùng để đối chiếu CITAD.
    Đúng mẫu thật của cả 5/5 nhóm đang bị báo lệch ngày 19/08/2026."""
    citad = [_citad('140001', chieu='den', loai='il', so_tien=399_800, cong='9')]
    ipcas = [
        _ipcas(chieu='den', txid='140001', loai='il', so_tien=399_800,
               trang_thai='RFED', chi_nhanh='2000', trace='519472', refhub='REF1'),
        _ipcas(chieu='den', txid='140001', loai='il', so_tien=399_800,
               trang_thai='RFED', chi_nhanh='2000', trace='519472', refhub='REF1'),
        _ipcas(chieu='den', txid='140001', loai='il', so_tien=399_800,
               trang_thai='RFED', chi_nhanh='2000', trace='581138', refhub='REF1'),
    ]
    n_khop, lech, khop = run_doiSoat_ram(citad, ipcas, [])
    assert n_khop == 1
    assert len([r for r in lech if r['status'] == 'only_ipcas']) == 0


def test_ipcas_den_hach_toan_nham_huy_dong_dung_o_chi_nhanh_khac():
    """Bút toán ĐÚNG (trace riêng) có thể ở CHI NHÁNH KHÁC với cặp nhầm/huỷ
    (xác nhận Phòng Thanh toán) — vẫn phải giữ lại, chỉ loại đúng cặp trùng
    CHI NHÁNH + trace, không yêu cầu cùng chi nhánh với dòng còn lại."""
    citad = [_citad('160001', chieu='den', loai='il', so_tien=70_000, cong='1')]
    ipcas = [
        _ipcas(chieu='den', txid='160001', loai='il', so_tien=70_000,
               trang_thai='RFED', chi_nhanh='2000', trace='111', refhub='REF3'),
        _ipcas(chieu='den', txid='160001', loai='il', so_tien=70_000,
               trang_thai='RFED', chi_nhanh='2000', trace='111', refhub='REF3'),
        _ipcas(chieu='den', txid='160001', loai='il', so_tien=70_000,
               trang_thai='SBSC', chi_nhanh='3000', trace='222', refhub='REF3'),
    ]
    n_khop, lech, khop = run_doiSoat_ram(citad, ipcas, [])
    assert n_khop == 1
    assert len([r for r in lech if r['status'] == 'only_ipcas']) == 0


def test_ipcas_den_hach_toan_nham_huy_khong_co_dong_dung_thi_giu_nguyen():
    """An toàn: nếu TOÀN BỘ dòng cùng refhub đều trùng chi nhánh+trace —
    không có dòng nào trace riêng để xác định bút toán ĐÚNG — KHÔNG loại gì
    cả, giữ nguyên hành vi cũ (báo lệch bình thường) — xác nhận Phòng Thanh
    toán: trường hợp này không xảy ra trong thực tế, chỉ là chốt an toàn."""
    citad = [_citad('150001', chieu='den', loai='il', so_tien=50_000, cong='1')]
    ipcas = [
        _ipcas(chieu='den', txid='150001', loai='il', so_tien=50_000,
               trang_thai='RFED', chi_nhanh='2000', trace='999', refhub='REF2'),
        _ipcas(chieu='den', txid='150001', loai='il', so_tien=50_000,
               trang_thai='RFED', chi_nhanh='2000', trace='999', refhub='REF2'),
    ]
    n_khop, lech, khop = run_doiSoat_ram(citad, ipcas, [])
    assert n_khop == 1
    du = [r for r in lech if r['status'] == 'only_ipcas']
    assert len(du) == 1


def test_so_gd_vnd_trung_so_gd_ngoai_te_khong_lam_mat_lenh_ipcas():
    """Bug thật (23/08/2026, tự rà soát): so_gd VND và so_gd ngoại tệ là 2
    hệ đánh số ĐỘC LẬP, có thể trùng số ngẫu nhiên. CITAD ngoại tệ so_gd
    trùng số với 1 msgref IPCAS VND (không hề có CITAD VND tương ứng) —
    trước khi tách riêng tập theo dõi "đã khớp" cho VND/ngoại tệ, lệnh
    ngoại tệ khớp Hub sẽ vô tình đánh dấu luôn msgref VND trùng số là
    "đã khớp", khiến lệnh IPCAS thật biến mất hoàn toàn khỏi báo cáo."""
    citad = [
        {'so_gd': '999', 'dich_vu': 'x', 'loai': 'ih', 'chieu': 'di',
         'loai_tien': 'USD', 'so_tien': 500, 'ngay': '19/08/2026', 'cong': '1'},
    ]
    hub = [
        {'so_gd': '999', 'loai': 'ih', 'chieu': 'di', 'loai_tien': 'USD',
         'so_tien': 500, 'nh_nhan': 'NH HUB', 'ngay': '19/08/2026', 'trang_thai': ''},
    ]
    ipcas = [_ipcas(chieu='di', msgref='999', trang_thai='SCNL')]
    n_khop, lech, khop = run_doiSoat_ram(citad, ipcas, hub)
    assert n_khop == 1  # chỉ lệnh ngoại tệ khớp Hub
    assert len(lech) == 1
    assert lech[0]['status'] == 'only_ipcas'
    assert lech[0]['key_agri'] == '999'


def test_ngoai_te_hub_dup_ap_dung_dung_co_che_nhu_ipcas():
    """Đúng yêu cầu: cơ chế phải áp dụng cho cả VND (IPCAS) và ngoại tệ
    (Hub), không riêng VND."""
    citad = [_citad('120001', chieu='den', loai_tien='USD', cong='12')]
    hub = [
        _hub('120001', chieu='den', loai_tien='USD'),
        _hub('120001', chieu='den', loai_tien='USD'),
    ]
    n_khop, lech, khop = run_doiSoat_ram(citad, [], hub)
    assert n_khop == 1
    assert '2 lần' in khop[0]['ghi_chu']
    du = [r for r in lech if r['status'] == 'only_hub']
    assert len(du) == 1
    assert 'cổng 12' in du[0]['ghi_chu']


def test_ipcas_khong_dup_thi_khong_co_ghi_chu():
    """Chỉ 1 dòng IPCAS (không trùng) thì không được tự sinh ghi_chú hay
    dòng thừa nào — chỉ báo khi THẬT SỰ phát hiện trùng."""
    citad = [_citad('110003', chieu='di')]
    ipcas = [_ipcas(chieu='di', msgref='110003', trang_thai='SCNL')]
    n_khop, lech, khop = run_doiSoat_ram(citad, ipcas, [])
    assert n_khop == 1
    assert not khop[0].get('ghi_chu')
    assert lech == []


def test_ipcas_dup_ma_citad_khong_co_lenh_van_ra_2_dong_chi_ipcas():
    """IPCAS trùng 2 lần nhưng CITAD KHÔNG hề có lệnh này — không có cổng
    CITAD nào để ghi, nhưng vẫn phải ra ĐỦ 2 dòng "Chỉ IPCAS" (đúng số
    lượng thật), không được gộp thành 1 dòng như trước."""
    ipcas = [
        _ipcas(chieu='di', msgref='130001', trang_thai='SCNL'),
        _ipcas(chieu='di', msgref='130001', trang_thai='SCNL'),
    ]
    n_khop, lech, khop = run_doiSoat_ram([], ipcas, [])
    assert n_khop == 0
    assert len(lech) == 2
    assert all(r['status'] == 'only_ipcas' for r in lech)


def test_parse_ipcas_khong_con_loc_bo_dong_trung():
    """Khoá tại nguồn: _parse_ipcas_text() KHÔNG được tự lọc bỏ dòng trùng
    y hệt nữa (bug thật 23/08/2026: lọc ở đây khiến reconcile.py không có
    gì để đếm, mọi cơ chế ở trên vô dụng) — phải trả về ĐỦ cả 2 dòng."""
    text = (
        "NGAY_GIAO_DICH,CHI_NHANH,TXID,SO_TIEN,TRACE,TRANG_THAI_LENH,MSGREF,KENH_THANH_TOAN,NH_NHAN\n"
        "19/08/2026,1000,900123,50000,TR001,SCNL,MSG900123,IL,NH TEST\n"
        "19/08/2026,1000,900123,50000,TR001,SCNL,MSG900123,IL,NH TEST\n"
    )
    rows = parsers._parse_ipcas_text(text, "test.csv", None)
    assert len(rows) == 2


def test_parse_ipcas_scnl_khong_co_ngay_kenh_tra_danh_dau_nkt_thieu():
    """Yêu cầu Phòng Thanh toán 27/08/2026: SCNL báo đã sang kênh thành công
    nhưng NGAY_KENH_TRA vẫn trống — kênh CHƯA THỰC SỰ xác nhận, không được
    coi là khớp IPCAS thật nữa (để lệnh CITAD tương ứng, nếu có, rơi vào
    "Chỉ CITAD" thay vì khớp khống).

    09/09/2026: TRƯỚC ĐÂY dòng này bị loại HẲN khỏi kết quả (`rows == []`)
    — sửa lại theo yêu cầu Phòng Thanh toán: lệnh này rất có thể vẫn tồn
    tại thật ở Agribank, xoá sạch làm mất luôn `refhub` (thứ người chấm cần
    để tự tra cứu khi thấy dòng "Chỉ CITAD"). Nay GIỮ LẠI dòng, chỉ đánh
    dấu `nkt_thieu=True` để reconcile.py biết không cho vào diện tự động
    khớp (xem test_scnl_thieu_ngay_kenh_tra_rot_vao_chi_citad_kem_refhub
    ở trên — hành vi đầu cuối không đổi, chỉ đổi CÁCH đạt được nó)."""
    text = (
        "NGAY_GIAO_DICH,CHI_NHANH,TXID,SO_TIEN,TRACE,TRANG_THAI_LENH,MSGREF,KENH_THANH_TOAN,NH_NHAN,NGAY_KENH_TRA,REFHUB\n"
        "19/08/2026,1000,900123,50000,TR001,SCNL,MSG900123,IL,NH TEST,,RH-900123\n"
    )
    rows = parsers._parse_ipcas_text(text, "test.csv", None)
    assert len(rows) == 1
    assert rows[0]['nkt_thieu'] is True
    assert rows[0]['refhub'] == 'RH-900123'
    assert rows[0]['msgref'] == 'MSG900123'


def test_parse_ipcas_scnl_co_ngay_kenh_tra_van_giu():
    """Đối chứng: SCNL có đủ NGAY_KENH_TRA vẫn phải giữ nguyên như cũ (chỉ
    đánh dấu `nkt_thieu` đúng ca thiếu NGAY_KENH_TRA, không phải mọi dòng
    SCNL)."""
    text = (
        "NGAY_GIAO_DICH,CHI_NHANH,TXID,SO_TIEN,TRACE,TRANG_THAI_LENH,MSGREF,KENH_THANH_TOAN,NH_NHAN,NGAY_KENH_TRA\n"
        "19/08/2026,1000,900124,50000,TR002,SCNL,MSG900124,IL,NH TEST,19/08/2026\n"
    )
    rows = parsers._parse_ipcas_text(text, "test.csv", None)
    assert len(rows) == 1
    assert rows[0]['msgref'] == 'MSG900124'
    assert rows[0]['nkt_thieu'] is False


def test_parse_ipcas_khong_co_cot_ngay_kenh_tra_khong_bi_loai_nham():
    """File KHÔNG có cột NGAY_KENH_TRA (has_nkt=False) — không đủ căn cứ để
    kết luận "trống", không được áp quy tắc loại SCNL mới ở trên (khác hẳn
    trường hợp có cột nhưng để trống)."""
    text = (
        "NGAY_GIAO_DICH,CHI_NHANH,TXID,SO_TIEN,TRACE,TRANG_THAI_LENH,MSGREF,KENH_THANH_TOAN,NH_NHAN\n"
        "19/08/2026,1000,900125,50000,TR003,SCNL,MSG900125,IL,NH TEST\n"
    )
    rows = parsers._parse_ipcas_text(text, "test.csv", None)
    assert len(rows) == 1
