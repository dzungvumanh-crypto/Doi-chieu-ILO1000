"""Job management cho "Đối chiếu đi" — Kênh↔Hub + Hub↔Core chạy TỰ ĐỘNG nối tiếp trong 1 job.

Mirror `doi_chieu_song_phuong_kenh_core_service.py` (chiều đến) — cùng kiến trúc job/1 báo cáo
cuối, "lỗi 1 bước không chặn bước còn lại". Tách file riêng (không tham số hoá `chieu` trong cùng
1 service) vì thuật toán Hub↔Core khác nhau đủ nhiều (`doi_chieu_song_phuong_core_di/` là package
riêng, không phải nhánh `if/else` trong package "đến") — xem PLAN.md.

Khác "đến" ở 1 điểm tối ưu hiệu năng CHƯA làm: không tái dùng HUB đã đọc ở bước Kênh↔Hub cho bước
Hub↔Core (`hub_t_override` của "đến") — vì Kênh↔Hub-đi trả về `hub_raw` CHƯA lọc SCNL (đi không
lọc gì trước khi khớp kênh, xem `kenh/pipeline.py`), trong khi Hub↔Core-đi cần bản ĐÃ lọc SCNL —
tái dùng thẳng sẽ sai. Hub↔Core-đi tự đọc lại HUB T từ đĩa (chi phí thêm nhỏ, đổi lấy đơn giản +
đúng đắn — có thể tối ưu sau khi "đi" đã chạy ổn định, giống cách "đến" cũng thêm tối ưu này sau
khi phần cơ bản đã chạy được, 2026-08-31)."""

import os
import shutil
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import pandas as pd

from backend.services import doi_chieu_song_phuong_common as common
from backend.services.doi_chieu_song_phuong_common import do_thoi_gian
from backend.services.doi_chieu_song_phuong_core_di import export as core_di_export
from backend.services.doi_chieu_song_phuong_core_di.export import export_excel_di
from backend.services.doi_chieu_song_phuong_core_di.pipeline import doi_chieu_hub_core_di
from backend.services.doi_chieu_song_phuong_kenh import export as kenh_export
from backend.services.doi_chieu_song_phuong_kenh.export import export_bao_cao
from backend.services.doi_chieu_song_phuong_kenh.load_hub import hub_filename_glob
from backend.services.doi_chieu_song_phuong_kenh.pipeline import main_from_dir as kenh_main_from_dir

TEMP_DIR = Path("data/temp_doi_chieu_song_phuong_kenh_core_di")
CLEANUP_TTL = 4 * 3600
CAC_NGAN_HANG = ("201", "202", "203", "311")

STAGE_LABELS = ["Kênh↔Hub", "Hub↔Core", "Hoàn tất"]

_jobs: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def _new_job(ngay: str, ma_nh: str) -> tuple[str, dict]:
    job_id = uuid.uuid4().hex[:12]
    job = {
        "status": "pending",   # pending | running | done | error | cancelled
        "logs": [],
        "files": [],
        "error": None,
        "ngay": ngay,
        "ma_nh": ma_nh,
        "ket_qua": {
            "kenh_hub_di": None, "hub_core_di": None,  # None nếu bước đó lỗi/bỏ qua
            "trang_thai": {"kenh_hub_di": None, "hub_core_di": None},
        },
        "stage": 0,
        "cancel_event": threading.Event(),
        "_ts": time.time(),
        "output_dir": str(TEMP_DIR / job_id),
    }
    with _lock:
        _jobs[job_id] = job
    return job_id, job


def get_job(job_id: str) -> dict | None:
    with _lock:
        return _jobs.get(job_id)


def cancel_job(job_id: str) -> bool:
    job = get_job(job_id)
    if job and job["status"] in ("pending", "running"):
        job["cancel_event"].set()
        return True
    return False


def tao_job(ngay: str, ma_nh: str) -> tuple[str, Path]:
    """Đăng ký job mới cho "Đối chiếu đi" và trả về (job_id, input_dir) — lớp API ghi THẲNG từng
    khối file tải lên vào `input_dir` (`save_upload_to()`), không gom vào RAM trước. Upload hỏng
    giữa chừng thì lớp API phải gọi `bo_job()` để trả lại chỗ."""
    if ma_nh not in CAC_NGAN_HANG:
        raise ValueError(f"Mã ngân hàng không hợp lệ: {ma_nh}")
    job_id, job = _new_job(ngay, ma_nh)
    input_dir = Path(job["output_dir"]) / "_upload"
    input_dir.mkdir(parents=True, exist_ok=True)
    job["input_dir"] = str(input_dir)
    return job_id, input_dir


def bo_job(job_id: str) -> None:
    """Huỷ một job chưa chạy (upload lỗi/đứt) — xoá khỏi store và xoá thư mục."""
    with _lock:
        _jobs.pop(job_id, None)
    shutil.rmtree(TEMP_DIR / job_id, ignore_errors=True)


def chay_job(job_id: str) -> None:
    """Khởi chạy "Đối chiếu đi" cho job đã nhận đủ file (xem `tao_job()`)."""
    job = get_job(job_id)
    if job is None:
        raise LookupError("Job không tồn tại.")
    threading.Thread(
        target=_run,
        args=(job_id, job["input_dir"], job["ngay"], job["ma_nh"], job["output_dir"]),
        daemon=True,
    ).start()


_NHAN_TRANG_THAI = {"da_doi_chieu": "Đã đối chiếu", "chua_doi_chieu": "CHƯA ĐỐI CHIẾU"}

# Giai đoạn 2 (2026-09-09, card 123 Implementation-notes.html) — người soát báo "bảng tổng hợp
# Kênh↔Hub và file chi tiết hub_chi_tiet.csv không khớp số dòng" tưởng là lỗi số liệu; thật ra 2
# file CỐ Ý khác phạm vi (Bảng 1 chỉ tính HUB "SCNL", file chi tiết giữ nguyên mọi trạng thái) —
# điều này trước đây chỉ giải thích được qua hội thoại, không có trong chính file kết quả. Ghi
# thẳng vào sheet "GhiChu" để người đọc file một mình cũng biết, không hiểu nhầm là bỏ sót.
_GHI_CHU_PHAM_VI_KENH_HUB = (
    "Bang1_KenhHub chỉ tính HUB có TRANG_THAI_LENH=\"SCNL\" (đúng docx) — 2 file chi tiết CSV "
    "(hub_chi_tiet/kenh_chi_tiet, tải riêng ở màn hình kết quả) giữ NGUYÊN mọi trạng thái HUB "
    "(SCNL/ERPO/CALD/TPAY...) để tra cứu sâu. Số dòng 2 bên khác nhau là CỐ Ý theo đúng phạm vi "
    "từng file, KHÔNG phải sai lệch số liệu."
)


def _export_bao_cao_tong_hop(
    ket_qua_kenh: dict | None, ket_qua_core: dict | None, trang_thai: dict, out_path: Path,
) -> Path | None:
    """Gộp sheet TrangThai + Bảng 1 (Kênh↔Hub) + TongHop (Hub↔Core) + GhiChu vào 1 workbook —
    mirror `doi_chieu_song_phuong_kenh_core_service.py::_export_bao_cao_tong_hop`. `kenh_export.
    build_bang1_rows()` DÙNG CHUNG được cho cả 2 chiều — nó chỉ đọc `summary`/`chi_tiet` theo dict
    shape chung, không hardcode nhãn "đến" (xem `process.summarize_unit_di()` trả đúng shape)."""
    if ket_qua_kenh is None and ket_qua_core is None:
        return None
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
        pd.DataFrame([
            {
                "Bước": nhan,
                "Trạng thái": _NHAN_TRANG_THAI.get((trang_thai.get(key) or {}).get("trang_thai"), "—"),
                "Lý do": (trang_thai.get(key) or {}).get("ly_do") or "",
            }
            for key, nhan in (("kenh_hub_di", "Kênh↔Hub"), ("hub_core_di", "Hub↔Core"))
        ]).to_excel(writer, sheet_name="TrangThai", index=False)
        if ket_qua_kenh is not None:
            kenh_export.build_bang1_rows([ket_qua_kenh]).to_excel(
                writer, sheet_name="Bang1_KenhHub", index=False,
            )
        if ket_qua_core is not None:
            core_di_export.build_tong_hop_di(
                ket_qua_core["core_df"], ket_qua_core["hub_df"],
            ).to_excel(writer, sheet_name="TongHop_HubCore", index=False)

        ghi_chu: list[str] = []
        if ket_qua_kenh is not None:
            ghi_chu.append(_GHI_CHU_PHAM_VI_KENH_HUB)
        if ket_qua_core is not None:
            ghi_chu.extend(ket_qua_core.get("ghi_chu") or [])
        if not ghi_chu:
            ghi_chu = ["Không có ghi chú."]
        pd.DataFrame({"Ghi chú": ghi_chu}).to_excel(writer, sheet_name="GhiChu", index=False)
    return out_path


def _run(job_id: str, goc_dir: str, ngay: str, ma_nh: str, output_dir: str) -> None:
    job = get_job(job_id)
    if job is None:
        return
    job["status"] = "running"
    t_job0 = time.perf_counter()
    goc_dir_p = Path(goc_dir)
    output_dir_p = Path(output_dir)
    files: list[str] = []
    loi: list[str] = []
    ket_qua_kenh: dict | None = None
    ket_qua_core: dict | None = None

    def log(msg: str) -> None:
        with _lock:
            job["logs"].append(msg)

    try:
        log(f"[JOB {job_id}] Bắt đầu Đối chiếu đi — NH {ma_nh}, ngày {ngay}...")

        # ── Bước 1/2 — Kênh↔Hub ──────────────────────────────────────────────
        log("=== Bước 1/2 — Kênh↔Hub ===")
        hub_matches = common.tim_file_glob(goc_dir_p, ngay, hub_filename_glob(ngay, ma_nh, "DI"))
        hub_path = None
        if len(hub_matches) > 1:
            log(f"[Kênh↔Hub] [LỖI] {len(hub_matches)} file HUB khớp cùng lúc trong "
                f"{hub_matches[0].parent} — KHÔNG tự chọn (tránh đọc nhầm khi nhiều người dùng "
                f"chung thư mục): {', '.join(p.name for p in hub_matches)}. Cần dọn bớt file "
                f"trùng hoặc dùng thư mục riêng cho mỗi phiên.")
        elif hub_matches:
            hub_path = hub_matches[0]

        if hub_path is None:
            ly_do = (
                "nhiều file HUB khớp cùng lúc, không tự chọn được — xem log"
                if hub_matches else "không tìm thấy file HUB"
            )
            loi.append(f"Kênh↔Hub: {ly_do} — bỏ qua bước này.")
            log(f"[Kênh↔Hub] {loi[-1]}")
            job["ket_qua"]["trang_thai"]["kenh_hub_di"] = {
                "trang_thai": "chua_doi_chieu", "ly_do": ly_do,
            }
        else:
            if job["cancel_event"].is_set():
                job["status"] = "cancelled"
                log("[JOB] Đã dừng theo yêu cầu.")
                return
            with do_thoi_gian(log, "Bước 1/2 Kênh↔Hub (tổng)"):
                ket_qua_kenh = kenh_main_from_dir(
                    hub_path.parent, ngay=ngay, ma_nh=ma_nh,
                    log_callback=lambda m: log(f"[Kênh↔Hub] {m}"),
                    cancel_event=job["cancel_event"],
                    hub_path_override=hub_path,
                    chieu="DI",
                )
            if ket_qua_kenh is None:
                if job["cancel_event"].is_set():
                    job["status"] = "cancelled"
                    log("[JOB] Đã dừng theo yêu cầu.")
                    return
                loi.append("Kênh↔Hub: không xác định được kết quả (xem log).")
                job["ket_qua"]["trang_thai"]["kenh_hub_di"] = {
                    "trang_thai": "chua_doi_chieu", "ly_do": "không xác định được kết quả (xem log)",
                }
            else:
                with do_thoi_gian(log, "ghi Excel+CSV Kênh↔Hub"):
                    kenh_files = export_bao_cao([ket_qua_kenh], output_dir_p)
                files.extend(p.name for p in kenh_files)

                chenh_lech: dict[str, dict] = {}
                canh_bao: list[dict] = []
                for dv in ket_qua_kenh["don_vi"]:
                    if dv["trang_thai"] != "ok":
                        continue
                    key = f"{dv['ma_nh']}-{dv['loai']}"
                    s = dv["summary"]
                    chenh_lech[key] = {"chenh_so_mon": s["chenh_so_mon"], "chenh_so_tien": s["chenh_so_tien"]}
                    if dv["canh_bao_trang_thai"]:
                        canh_bao.append({"don_vi": key, "trang_thai": dv["canh_bao_trang_thai"]})
                job["ket_qua"]["kenh_hub_di"] = {"chenh_lech": chenh_lech, "canh_bao": canh_bao}
                job["ket_qua"]["trang_thai"]["kenh_hub_di"] = {"trang_thai": "da_doi_chieu", "ly_do": None}

        job["stage"] = 1

        # ── Bước 2/2 — Hub↔Core ──────────────────────────────────────────────
        log("=== Bước 2/2 — Hub↔Core ===")
        if job["cancel_event"].is_set():
            job["status"] = "cancelled"
            log("[JOB] Đã dừng theo yêu cầu.")
            return
        try:
            with do_thoi_gian(log, "Bước 2/2 Hub↔Core (tổng)"):
                ket_qua_core = doi_chieu_hub_core_di(
                    goc_dir_p, ngay, ma_nh, log_callback=lambda m: log(f"[Hub↔Core] {m}"),
                )
        except ValueError as e:
            loi.append(f"Hub↔Core: {e}")
            log(f"[Hub↔Core] {e}")
            job["ket_qua"]["trang_thai"]["hub_core_di"] = {"trang_thai": "chua_doi_chieu", "ly_do": str(e)}
        else:
            base_name = f"hub_core_di_{ma_nh}_{ngay}"
            with do_thoi_gian(log, "ghi Excel+CSV Hub↔Core"):
                hub_core_files = export_excel_di(ket_qua_core, output_dir_p, base_name)
            files.extend(p.name for p in hub_core_files)

            core_df, hub_df = ket_qua_core["core_df"], ket_qua_core["hub_df"]
            job["ket_qua"]["hub_core_di"] = {
                "so_dong_core": len(core_df),
                "so_dong_hub": len(hub_df),
                "phan_bo_core": core_df["KETQUADOICHIEU"].value_counts().to_dict(),
                "phan_bo_hub": hub_df["KETQUADOICHIEU"].value_counts().to_dict(),
            }
            job["ket_qua"]["trang_thai"]["hub_core_di"] = {"trang_thai": "da_doi_chieu", "ly_do": None}

        job["stage"] = 2

        if job["ket_qua"]["kenh_hub_di"] is None and job["ket_qua"]["hub_core_di"] is None:
            job["status"] = "error"
            job["error"] = " | ".join(loi) or "Cả 2 bước đều không có kết quả."
            log(f"[JOB] {job['error']}")
            return

        with do_thoi_gian(log, "ghi báo cáo tổng hợp"):
            bao_cao_path = _export_bao_cao_tong_hop(
                ket_qua_kenh, ket_qua_core, job["ket_qua"]["trang_thai"],
                output_dir_p / f"bao_cao_tong_hop_di_{ma_nh}_{ngay}.xlsx",
            )
        if bao_cao_path:
            files.insert(0, bao_cao_path.name)
            log(f"[JOB] Đã gộp báo cáo tổng kết: {bao_cao_path.name}")

        job["files"] = files
        job["status"] = "done"
        log(f"[JOB] Hoàn thành — {len(files)} file kết quả."
            + (f" Lỗi/bỏ qua: {' | '.join(loi)}" if loi else ""))
        log(f"[TIMING] Tổng thời gian job: {time.perf_counter() - t_job0:.1f}s")

    except Exception as e:
        import traceback
        job["error"] = str(e)
        job["status"] = "error"
        log(f"[ERROR] {e}")
        log(traceback.format_exc())

    finally:
        job["_ts"] = time.time()
        _cleanup_old_jobs()


def get_output_file(job_id: str, filename: str) -> Path | None:
    job = get_job(job_id)
    if not job:
        return None
    safe_name = os.path.basename(filename)
    path = Path(job["output_dir"]) / safe_name
    return path if path.is_file() else None


def _cleanup_old_jobs() -> None:
    now = time.time()
    with _lock:
        expired = [
            jid for jid, j in _jobs.items()
            if j["status"] in ("done", "error", "cancelled") and now - j["_ts"] > CLEANUP_TTL
        ]
        for jid in expired:
            del _jobs[jid]
    for jid in expired:
        job_dir = TEMP_DIR / jid
        if job_dir.exists():
            shutil.rmtree(job_dir, ignore_errors=True)
