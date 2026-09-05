"""Logic đối chiếu ILO1000: tính Trace, Map dc, phát hiện Hủy, điền TT."""

import pandas as pd

from .config import (
    HUB_COL_SO_GD, HUB_COL_STC, HUB_COL_TRACE, HUB_COL_TRACE2_RAW,
    HUB_COL_TRANG_THAI, HUB_COL_NGAY_GIO, HUB_COL_NOI_DUNG, HUB_COL_SO_TIEN,
)


def _safe_str(s) -> pd.Series:
    return s.fillna('').astype(str).str.strip()


def _first_match(keys: pd.Series, values: pd.Series) -> dict:
    """Giữ lần xuất hiện ĐẦU TIÊN của key — hành vi VLOOKUP của Excel."""
    mask = keys.astype(bool) & ~keys.duplicated(keep='first')
    return dict(zip(keys[mask], values[mask]))


# ── HUB ──────────────────────────────────────────────────────────────────────

def process_hub(hub_df: pd.DataFrame, eicp_maps: dict, ngay_int: int) -> tuple[pd.DataFrame, dict]:
    """
    Trả về (hub_df đã xử lý, lookup_dicts).
    lookup_dicts = {
        'stc_to_trace':    {STC → Trace text}  ← để citad dùng
        'trace_trangthai': {Trace text → Trạng thái}
        'trace_sotien':    {Trace text → Số tiền}
    }
    """
    df = hub_df.copy()

    if df.empty:
        empty_dicts = {k: {} for k in ('stc_to_trace', 'trace_trangthai', 'trace_sotien')}
        return df, empty_dicts

    hub_to_core: dict = eicp_maps.get('hub_to_core', {})

    # ── Tính Trace ──
    # Theo tài liệu gốc: chỉ giao dịch có "Số giao dịch" chứa 'S' mới qua bước
    # BFX/EICP. Giao dịch KHÔNG chứa 'S' (chủ yếu loại "OT" — hoàn trả lệnh gốc)
    # dùng thẳng "Số Trace 2" — xác nhận qua đối chiếu dữ liệu thật 06/07/2026:
    # nhóm không chứa 'S' khớp 96,5% qua Số Trace 2 (so với chỉ 50% qua Số Trace 1);
    # riêng OT khớp 100% qua Số Trace 2.
    so_gd = _safe_str(df[HUB_COL_SO_GD])
    noi_dung = _safe_str(df[HUB_COL_NOI_DUNG])
    s_mask = so_gd.str.contains('S', case=False, na=False)
    bfx_mask = noi_dung.str.contains('BFX', case=False, na=False)
    # "Số giao dịch" chứa 'SMF' → luôn giữ nguyên Số Trace 1 gốc, không VLOOKUP
    # qua EICP dù thuộc nhóm 'S' không BFX (xác nhận từ người dùng 2026-07-16).
    smf_mask = so_gd.str.contains('SMF', case=False, na=False)

    # Giá trị Trace ban đầu (Số Trace 1, từ pHub)
    trace = _safe_str(df[HUB_COL_TRACE]).copy()

    if HUB_COL_TRACE2_RAW in df.columns:
        trace2_raw = _safe_str(df[HUB_COL_TRACE2_RAW])
        use_trace2 = ~s_mask & (trace2_raw != '')
        trace.loc[use_trace2] = trace2_raw.loc[use_trace2]

    # BFX (chỉ trong nhóm "Số giao dịch" chứa 'S'): right(nội dung, 16)
    bfx_apply_mask = s_mask & bfx_mask & ~smf_mask
    trace.loc[bfx_apply_mask] = noi_dung.loc[bfx_apply_mask].str[-16:]

    # Non-BFX trong nhóm 'S' (trừ SMF): lookup qua EICP, giữ nguyên Số Trace 1
    # nếu không tìm thấy. Map toàn bộ so_gd để tránh vấn đề index alignment khi
    # df đã bị filter.
    eicp_apply_mask = s_mask & ~bfx_mask & ~smf_mask
    eicp_all = so_gd.map(hub_to_core).fillna('')
    update_mask = eicp_apply_mask & (eicp_all != '')
    trace.loc[update_mask] = eicp_all.loc[update_mask]

    df['Trace'] = trace.values

    # Trace thuần chữ số có thể có số 0 thừa ở đầu tùy đợt export pHub (VD "063403118"
    # vs "63403118" — cùng 1 giá trị nhưng khác text) — Core tính Trace độc lập từ
    # REFERENCE không có số 0 đầu, khiến Map dc (ghép chuỗi) không khớp dù cùng giao dịch.
    # Chỉ strip cho Trace toàn chữ số — không đụng Trace BFX/EICP (có ký tự chữ, có ý nghĩa).
    numeric_mask = df['Trace'].str.match(r'^\d+$', na=False)
    stripped = df['Trace'].str.lstrip('0')
    stripped = stripped.mask(stripped == '', '0')
    df.loc[numeric_mask, 'Trace'] = stripped[numeric_mask]

    df['Trace2'] = pd.to_numeric(df['Trace'], errors='coerce')

    # ── Ngày (ngày trong tháng) — parse đầy đủ vì ngày đơn digit "5/05/..." bị lỗi khi dùng str[:2] ──
    ngay_gio = _safe_str(df[HUB_COL_NGAY_GIO])
    df['Ngày'] = pd.to_datetime(ngay_gio, dayfirst=True, errors='coerce').dt.day.astype(float)

    # ── Flag "Chờ đi kênh": ngày > ngày đối chiếu (giao dịch xử lý sau ngày đối chiếu) ──
    ngay_dc_day = ngay_int % 100  # DD
    after_mask = df['Ngày'].fillna(0) > ngay_dc_day
    df.loc[after_mask, HUB_COL_TRANG_THAI] = 'Chờ đi kênh'

    df['ngay'] = ngay_int

    # ── Build lookup dicts ──
    stc   = _safe_str(df[HUB_COL_STC])
    trace_col  = df['Trace'].fillna('').astype(str)
    tt_col     = _safe_str(df[HUB_COL_TRANG_THAI])
    sotien_col = _safe_str(df[HUB_COL_SO_TIEN])

    # Giữ lần xuất hiện đầu tiên — VLOOKUP behavior
    stc_to_trace    = _first_match(stc,       trace_col)
    trace_trangthai = _first_match(trace_col, tt_col)
    trace_sotien    = _first_match(trace_col, sotien_col)

    lookups = {
        'stc_to_trace':    stc_to_trace,
        'trace_trangthai': trace_trangthai,
        'trace_sotien':    trace_sotien,
    }
    return df, lookups


# ── CITAD ─────────────────────────────────────────────────────────────────────

def process_citad(citad_df: pd.DataFrame, hub_lookups: dict, ngay_int: int) -> tuple[pd.DataFrame, dict]:
    """
    Trả về (citad_df đã xử lý, citad_mapdc_to_ngay dict).
    """
    df = citad_df.copy()

    # ── Clean AMOUNT: "ltd" → lấy từ TRX_STATUS ──
    # Fix chính đã chạy sớm hơn, ở load_citad.py::_load_one() (TRƯỚC khi gộp
    # 5 cổng + dedup theo SERIAL_NO — bắt buộc theo đúng thứ tự nghiệp vụ, xem
    # comment ở đó). Giữ lại ở đây làm lưới an toàn cho caller không qua
    # load_citad() — no-op nếu AMOUNT đã sạch.
    amount_str = _safe_str(df['AMOUNT'])
    ltd_mask = amount_str.str.lower().str.contains('ltd', na=False)
    df.loc[ltd_mask, 'AMOUNT'] = _safe_str(df.loc[ltd_mask, 'TRX_STATUS'])
    df['AMOUNT'] = pd.to_numeric(df['AMOUNT'], errors='coerce').fillna(0)

    # ── Trace: vlookup(SERIAL_NO, hub!STC→Trace) ──
    stc_to_trace = hub_lookups.get('stc_to_trace', {})
    serial = _safe_str(df['SERIAL_NO'])
    df['Trace'] = serial.map(stc_to_trace).fillna('')

    # ── Map đối chiếu: LEFT(RELATION_NO, 4) & Trace & AMOUNT ──
    rel4 = _safe_str(df['RELATION_NO']).str[:4]
    trace_s = df['Trace'].fillna('').astype(str)
    amount_s = df['AMOUNT'].fillna(0).astype(int).astype(str)
    df['Map dc'] = rel4 + trace_s + amount_s

    df['Ngày'] = ngay_int

    # Label TT cho citad match: 'citad {day}.{month}' — khớp format thủ công
    day   = ngay_int % 100
    month = (ngay_int // 100) % 100
    citad_label = f'citad {day}.{month}'

    # ── Build lookup: Map dc → label citad (để core tra TT) — giữ first match ──
    citad_label_series = pd.Series(citad_label, index=df.index)
    mapdc_to_ngay = _first_match(df['Map dc'], citad_label_series)

    return df, mapdc_to_ngay


# ── CORE ──────────────────────────────────────────────────────────────────────

def detect_huy(df: pd.DataFrame) -> dict:
    """
    Phát hiện giao dịch Hủy: gom theo (REFERENCE, TRBRCD). Hai tín hiệu ĐỘC
    LẬP, kết hợp OR (một mình tín hiệu (1) không đủ — xem lý do dưới):

    1. Tổng Nợ = tổng Có trong batch (net-zero) — bắt được khi CẢ vế gốc lẫn vế
       hủy cùng nằm trong batch đang xử lý (`df` nên là Core GỘP TOÀN BỘ các
       ngày trong batch, không phải chỉ 1 ngày).
    2. Có ít nhất 1 dòng CRAMOUNT < 0 — bản dịch trực tiếp quy tắc docx gốc
       "nếu Số tiền (-) thì là hủy lệnh ngày cũ". Bắt được cả khi vế gốc (+X)
       nằm ở một ngày KHÔNG được nạp trong batch hiện tại — Core (khác
       Hub/Eicp) không có carryover T-1, nên khi đó net ≠ 0 và tín hiệu (1)
       một mình bỏ sót ca này. Xác nhận qua dữ liệu thật 11-12/8/2026: 91
       REFERENCE có CRAMOUNT âm, 47/91 (52%) không có vế gốc dương cùng
       REFERENCE trong batch 2 ngày đó — đúng số ca tín hiệu (1) bỏ sót.

    Xác nhận nghiệp vụ 2026-07-16: "Hủy" và "Đã hủy" là 2 trạng thái KHÁC NHAU
    (không phải lỗi gõ tay như từng nhầm tưởng trước đó):
    - 'Hủy'    — net-zero VÀ ngày lập/ngày hủy CÙNG 1 ngày (TRDATE)
    - 'Đã hủy' — mọi trường hợp còn lại (khác ngày, hoặc thiếu vế gốc trong batch)

    Gộp thêm TRBRCD vào khóa nhóm (không chỉ REFERENCE) — xác nhận qua phản
    hồi người chấm + dữ liệu thật 26/8/2026: các lệnh chi trả trợ cấp xã hội
    hàng loạt (REFERENCE dạng "1000OTT...") dùng CHUNG một REFERENCE giữa
    NHIỀU chi nhánh khác nhau trong cùng batch (VD "1000OTT261006174" xuất
    hiện ở cả 3 chi nhánh 1410/2008/5708). Chỉ 1 chi nhánh (2008) có cặp
    Nợ/Có net-zero thật sự là hủy lệnh; nếu gom theo REFERENCE một mình, tín
    hiệu hủy của chi nhánh đó lây lan sai sang 2 chi nhánh còn lại (giao dịch
    bình thường, khớp Hub "Hoàn thành") — khiến core bị gắn nhầm 'Đã hủy'.

    Trả về dict (REFERENCE, TRBRCD) → 'Hủy' | 'Đã hủy'.
    """
    if df.empty or 'REFERENCE' not in df.columns:
        return {}

    ref    = _safe_str(df['REFERENCE'])
    brcd   = _safe_str(df.get('TRBRCD', pd.Series('', index=df.index)))
    dr     = pd.to_numeric(df.get('DRAMOUNT', 0), errors='coerce').fillna(0)
    cr     = pd.to_numeric(df.get('CRAMOUNT', 0), errors='coerce').fillna(0)
    trdate = _safe_str(df.get('TRDATE', pd.Series('', index=df.index)))

    tmp = pd.DataFrame({'REFERENCE': ref, 'TRBRCD': brcd, '_DR': dr, '_CR': cr, '_TRDATE': trdate})
    tmp = tmp[tmp['REFERENCE'] != '']
    tmp['_KEY'] = list(zip(tmp['REFERENCE'], tmp['TRBRCD']))

    sums   = tmp.groupby('_KEY', sort=False)[['_DR', '_CR']].sum()
    n_days = tmp.groupby('_KEY', sort=False)['_TRDATE'].nunique()

    net_zero_keys = set(sums[sums['_CR'] - sums['_DR'] == 0].index)
    neg_cr_keys   = set(tmp.loc[tmp['_CR'] < 0, '_KEY'])
    huy_keys      = net_zero_keys | neg_cr_keys

    def _label(k) -> str:
        if k in net_zero_keys and n_days.get(k, 1) <= 1:
            return 'Hủy'
        return 'Đã hủy'

    return {k: _label(k) for k in huy_keys}


def process_core(
    core_df: pd.DataFrame,
    citad_mapdc: dict,
    hub_lookups: dict,
    ngay_int: int,
    huy_map: dict | None = None,
) -> pd.DataFrame:
    """
    Điền Trace, Map dc, TT cho sheet Core.
    `huy_map` ((REFERENCE, TRBRCD) → 'Hủy'/'Đã hủy') nên được tính trước trên
    Core GỘP toàn batch bằng detect_huy() rồi truyền vào, để bắt được cả Hủy
    khác ngày. Nếu không truyền (VD gọi lẻ trong test), tự tính trên chính
    core_df này — khi đó chỉ phát hiện được Hủy cùng ngày (đúng theo dữ liệu
    đang có).
    """
    df = core_df.copy()

    ref  = _safe_str(df.get('REFERENCE', pd.Series('', index=df.index)))
    brcd = _safe_str(df.get('TRBRCD',    pd.Series('', index=df.index)))

    # ── Tính Trace từ REFERENCE ──
    api_mask = ref.str.contains('API', case=False, na=False)
    ott_mask = ref.str.contains('OTT', case=False, na=False) & ~api_mask
    bfx_mask = ref.str.contains('BFX', case=False, na=False) & ~api_mask & ~ott_mask
    hi_mask  = ref.str.contains('HI', na=False) & ~api_mask & ~ott_mask & ~bfx_mask

    trace = pd.Series('', index=df.index)
    trace[api_mask] = ref[api_mask].str[7:23]
    trace[ott_mask] = brcd[ott_mask] + ref[ott_mask].str[4:16]
    trace[bfx_mask] = brcd[bfx_mask] + ref[bfx_mask].str[4:16]
    trace[hi_mask]  = 'Quyết toán'

    df['Trace']  = trace
    df['Trace2'] = pd.to_numeric(trace, errors='coerce')

    # ── Map đối chiếu: TRBRCD & Trace & CRAMOUNT ──
    cramount = pd.to_numeric(df.get('CRAMOUNT', 0), errors='coerce').fillna(0).astype(int)
    df['Map dc']  = brcd + trace + cramount.astype(str)
    df['Ngày']    = ngay_int

    if huy_map is None:
        huy_map = detect_huy(df)

    # ── Tính TT theo thứ tự ưu tiên ──
    tt = pd.Series('', index=df.index)

    # 1. Hủy / Đã hủy — khóa (REFERENCE, TRBRCD), xem detect_huy()
    huy_key   = pd.Series(list(zip(ref, brcd)), index=df.index)
    huy_label = huy_key.map(huy_map)
    huy_mask  = huy_label.notna()
    tt[huy_mask] = huy_label[huy_mask]

    # 1.5. HI type (Quyết toán) — giao dịch quyết toán, không cần tra Hub/Citad
    qt_mask = (tt == '') & (df['Trace'] == 'Quyết toán')
    tt[qt_mask] = 'quyết toán'

    # 1.6. Kênh OSB — REMARK chứa "IBPSILO" là giao dịch kênh OSB, không thuộc
    # phạm vi đối chiếu Citad/Hub của ILO1000 (sẽ có module Chấm TK OSB riêng
    # sau này). Xác nhận qua dữ liệu thật 04-06/7/2026: 3/3 dòng IBPSILO đều
    # được bài chấm tay ghi TT = "OSB", không dòng nào trùng điều kiện Hủy —
    # nên chỉ gán cho dòng CHƯA có TT, không ghi đè Hủy/Quyết toán.
    remark = _safe_str(df.get('REMARK', pd.Series('', index=df.index)))
    osb_mask = (tt == '') & remark.str.contains('IBPSILO', case=False, na=False)
    tt[osb_mask] = 'OSB'

    # 2. Khớp CITAD qua Map dc (TRBRCD + Trace + AMOUNT)
    mask = tt == ''
    if mask.any():
        citad_result = df.loc[mask, 'Map dc'].astype(str).map(citad_mapdc)
        found_idx = citad_result.dropna().index
        tt.loc[found_idx] = citad_result.loc[found_idx].astype(str)

    # 3. Khớp Hub qua Trace → Trạng thái
    trace_tt   = hub_lookups.get('trace_trangthai', {})
    trace_sot  = hub_lookups.get('trace_sotien',    {})

    mask = tt == ''
    if mask.any():
        hub_result = df.loc[mask, 'Trace'].astype(str).map(trace_tt)
        found_idx  = hub_result.dropna().index
        tt.loc[found_idx] = hub_result.loc[found_idx].astype(str)

    # 4. Khớp Hub qua Trace → Số tiền (fallback cuối)
    mask = tt == ''
    if mask.any():
        hub_result2 = df.loc[mask, 'Trace'].astype(str).map(trace_sot)
        found_idx   = hub_result2.dropna().index
        tt.loc[found_idx] = hub_result2.loc[found_idx].astype(str)

    df['TT'] = tt
    return df


def used_citad_keys(core_out: pd.DataFrame, citad_mapdc: dict) -> set:
    """
    Tập các `Map dc` Citad đã thực sự được ít nhất 1 dòng Core CHỌN TRÚNG để
    gán TT — không phải mọi key có mặt trong `citad_mapdc` (dict chứa TOÀN BỘ
    Citad, kể cả những dòng không có Core nào tra tới, hoặc có tra tới nhưng
    bị ưu tiên cao hơn — Hủy/Quyết toán/OSB — ghi đè trước bước khớp Citad).

    Chỉ dựa vào `core_out` (đã có TT) + `citad_mapdc`, không cần sửa
    `process_core()` — tránh đổi chữ ký hàm đang được gọi ở rất nhiều test.
    """
    if core_out.empty or 'Map dc' not in core_out.columns:
        return set()
    map_dc = core_out['Map dc'].astype(str)
    citad_label = map_dc.map(citad_mapdc)
    really_used = core_out['TT'].astype(str) == citad_label.fillna('\0__none__')
    return set(map_dc[really_used])


def match_citad_leftover_with_osb(
    citad_df: pd.DataFrame,
    used_citad_mapdc: set,
    osb_key: 'pd.Series | None' = None,
) -> pd.DataFrame:
    """
    Với các dòng Citad CÒN THỪA (Map dc KHÔNG nằm trong `used_citad_mapdc` —
    Core không khớp trúng), so trực tiếp với tập khóa OSB (`osb_key`, xem
    `load_osb.build_osb_key()`). Thêm cột 'TT': 'OSB' nếu khớp; để RỖNG nếu
    vẫn còn thừa sau cả Core lẫn OSB — không tự suy luận thêm, xuất cho người
    chấm tay xem xét (đúng nguyên tắc "không có định danh đáng tin → xuất
    toàn bộ nhóm cho người dùng chấm tay").

    Dòng Citad ĐÃ khớp Core (Map dc nằm trong `used_citad_mapdc`) không đụng
    tới cột 'TT' (giữ rỗng) — đã được coi là xử lý xong ở sheet Core.
    """
    df = citad_df.copy()
    df['TT'] = ''

    if df.empty or 'Map dc' not in df.columns:
        return df

    map_dc = df['Map dc'].astype(str)
    leftover_mask = ~map_dc.isin(used_citad_mapdc)
    if not leftover_mask.any() or osb_key is None or osb_key.empty:
        return df

    osb_key_set = set(osb_key.astype(str))
    matched = leftover_mask & map_dc.isin(osb_key_set)
    df.loc[matched, 'TT'] = 'OSB'
    return df
