"""
Test API-level cho "Đối chiếu đi" — mirror `test_doi_chieu_song_phuong_kenh_core_api.py` (chiều
đến). Không kiểm lại toán khớp (đã có ở `test_doi_chieu_song_phuong_core_di_algorithm.py`) —
chỉ kiểm lớp điều phối + upload thật qua API, đặc biệt: upload nhiều file ZIP/CSV cùng lúc có
chạy được không (câu hỏi người dùng 2026-09-08).

Chạy: .venv\\Scripts\\python.exe -m pytest tests/test_doi_chieu_song_phuong_kenh_core_di_api.py -v
"""

import io
import time
import zipfile

import pandas as pd
import pytest
import pyzipper

from backend.services import doi_chieu_song_phuong_kenh_core_di_service as svc
from backend.services import doi_chieu_song_phuong_service as ipcas_svc

_MK = "matkhau-test-kenh-core-di-api"
_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.fixture(autouse=True)
def _mat_khau_zip(monkeypatch):
    monkeypatch.setenv("DOI_CHIEU_ZIP_PASSWORD", _MK)


_HUB_COLS_DI = ["NGAY_GIAO_DICH", "CHI_NHANH", "REFHUB", "MSGREF", "MSGSEQ", "TXID",
                "KENH_THANH_TOAN", "TRANG_THAI_LENH", "SO_TIEN", "TRACE", "SE_TRACE",
                "SESSION", "LOAI_LENH_OSB", "NH_GUI", "NOI_DUNG"]
_KENH_COLS = ["STT", "Ngày GD", "Giờ truyền nhận", "MtId/MsgId", "Số tiền"]
_GL02_COLS_DI = ["TRBRCD", "USERID", "CUSTOMER", "CRAMOUNT", "DRAMOUNT", "REFERENCE", "REMARK"]

_MSG_202RT = "0200970488TESTRT202AAAA"


def _hub_row_di(msgref, txid, so_tien="100000", trace="000353682"):
    return {
        "NGAY_GIAO_DICH": "25/08/2026", "CHI_NHANH": "1000", "REFHUB": "REFHUB001",
        "MSGREF": f"'{msgref}", "MSGSEQ": f"'{msgref}", "TXID": f"'{txid}",
        "KENH_THANH_TOAN": "SP REALTIME", "TRANG_THAI_LENH": "SCNL", "SO_TIEN": so_tien,
        "TRACE": trace, "SE_TRACE": "", "SESSION": "20260825", "LOAI_LENH_OSB": "0",
        "NH_GUI": "01202001", "NOI_DUNG": "TEST",
    }


def _make_hub_zip_di(rows: list[dict]) -> bytes:
    df = pd.DataFrame(rows, columns=_HUB_COLS_DI)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("data.csv", df.to_csv(index=False).encode("utf-8-sig"))
    return buf.getvalue()


def _kenh_row(mtid, so_tien="100000"):
    return {"STT": "1", "Ngày GD": "25/08/2026", "Giờ truyền nhận": "25/08/2026 00:00:01",
            "MtId/MsgId": mtid, "Số tiền": so_tien}


def _gl02_row_di(customer="1000-003046328", cramount="500000"):
    return {"TRBRCD": "1000", "USERID": "1000API9", "CUSTOMER": customer,
            "CRAMOUNT": cramount, "DRAMOUNT": "0",
            "REFERENCE": "1000API001002080", "REMARK": "TEST"}


def _make_gl02_zip(rows: list[dict]) -> bytes:
    df = pd.DataFrame(rows, columns=_GL02_COLS_DI)
    buf = io.BytesIO()
    with pyzipper.AESZipFile(buf, "w", compression=pyzipper.ZIP_DEFLATED,
                              encryption=pyzipper.WZ_AES) as zf:
        zf.setpassword(ipcas_svc.zip_password())
        zf.writestr("gl02.csv", df.to_csv(index=False).encode("utf-8-sig"))
    return buf.getvalue()


def _hub_kenh_upload_files_di(ngay="20260825") -> list[tuple]:
    hub_bytes = _make_hub_zip_di([_hub_row_di(_MSG_202RT, "TXID202RT")])
    kenh_buf = io.BytesIO()
    pd.DataFrame([_kenh_row(_MSG_202RT, "100000")], columns=_KENH_COLS).to_excel(
        kenh_buf, index=False, engine="openpyxl"
    )
    return [
        ("files", (f"doichieugd_{ngay}__05_DI_9999_N.zip", hub_bytes, "application/zip")),
        ("files", ("kênh đi SPRT 202.xlsx", kenh_buf.getvalue(), _XLSX_MIME)),
    ]


def _gl02_upload_file_di(ngay="20260825") -> tuple:
    return ("files", (f"GL02_{ngay}_1000.zip", _make_gl02_zip([_gl02_row_di()]), "application/zip"))


def _core_csv_upload_file_trdate_di(filename: str, trdate: str) -> tuple:
    cols = ["TRDATE"] + _GL02_COLS_DI
    row = {"TRDATE": trdate, **_gl02_row_di()}
    df = pd.DataFrame([row], columns=cols)
    return ("files", (filename, df.to_csv(index=False).encode("utf-8-sig"), "text/csv"))


def _wait_done(admin_client, job_id, timeout_s=15):
    deadline = time.time() + timeout_s
    prog = None
    while time.time() < deadline:
        r = admin_client.get(f"/api/doi_chieu_song_phuong_kenh_core_di/poll/{job_id}")
        assert r.status_code == 200
        prog = r.json()
        if prog["status"] in ("done", "error", "cancelled"):
            return prog
        time.sleep(0.05)
    raise AssertionError(f"Job không hoàn thành sau {timeout_s}s: {prog}")


class TestStartUploadEndpointDi:
    def test_full_flow_qua_upload(self, admin_client, monkeypatch, tmp_path):
        monkeypatch.setattr(svc, "TEMP_DIR", tmp_path / "_out")
        monkeypatch.setattr(ipcas_svc, "TEMP_DIR", tmp_path / "_out_ipcas")

        r = admin_client.post(
            "/api/doi_chieu_song_phuong_kenh_core_di/start_upload",
            files=[*_hub_kenh_upload_files_di(), _gl02_upload_file_di()],
            data={"ngay": "20260825", "ma_nh": "202"},
        )
        assert r.status_code == 200, r.text
        job_id = r.json()["job_id"]
        prog = _wait_done(admin_client, job_id)
        assert prog["status"] == "done", prog
        assert prog["ket_qua"]["kenh_hub_di"] is not None
        assert prog["ket_qua"]["hub_core_di"] is not None

    def test_2_file_gl02_zip_khac_ngay_qua_upload_deu_dung_duoc(self, admin_client, monkeypatch, tmp_path):
        """Câu hỏi người dùng 2026-09-08: upload nhiều file ZIP cùng lúc có chạy được không —
        2 file GL02 khác ngày (T, T+1), mỗi file tự mang đúng ngày trong tên, không mơ hồ."""
        monkeypatch.setattr(svc, "TEMP_DIR", tmp_path / "_out")
        monkeypatch.setattr(ipcas_svc, "TEMP_DIR", tmp_path / "_out_ipcas")

        r = admin_client.post(
            "/api/doi_chieu_song_phuong_kenh_core_di/start_upload",
            files=[
                *_hub_kenh_upload_files_di(ngay="20260825"),
                _gl02_upload_file_di(ngay="20260825"),
                _gl02_upload_file_di(ngay="20260826"),
            ],
            data={"ngay": "20260825", "ma_nh": "202"},
        )
        assert r.status_code == 200, r.text
        job_id = r.json()["job_id"]
        prog = _wait_done(admin_client, job_id)
        assert prog["status"] == "done", prog
        assert prog["ket_qua"]["hub_core_di"] is not None

        logs = "\n".join(prog["logs"])
        assert "[CORE T] đang giải mã + phân loại GL02_20260825_1000.zip" in logs, logs
        assert "[CORE T+1] đang giải mã + phân loại GL02_20260826_1000.zip" in logs, logs

    def test_2_file_csv_core_khac_ngay_qua_upload_deu_dung_duoc(self, admin_client, monkeypatch, tmp_path):
        """Câu hỏi người dùng 2026-09-08: upload nhiều file CSV cùng lúc có chạy được không —
        2 file CSV core đã phân loại sẵn, tên KHÔNG mang ngày nhưng TRDATE khác nhau (T, T+1) —
        đúng kịch bản dữ liệu thật đã gặp khi chạy đối chiếu đi 5-9/9/2026."""
        monkeypatch.setattr(svc, "TEMP_DIR", tmp_path / "_out")
        monkeypatch.setattr(ipcas_svc, "TEMP_DIR", tmp_path / "_out_ipcas")

        r = admin_client.post(
            "/api/doi_chieu_song_phuong_kenh_core_di/start_upload",
            files=[
                *_hub_kenh_upload_files_di(ngay="20260825"),
                _core_csv_upload_file_trdate_di("202_DI_dot1.csv", "20260825"),
                _core_csv_upload_file_trdate_di("202_DI_dot2.csv", "20260826"),
            ],
            data={"ngay": "20260825", "ma_nh": "202"},
        )
        assert r.status_code == 200, r.text
        job_id = r.json()["job_id"]
        prog = _wait_done(admin_client, job_id)
        assert prog["status"] == "done", prog
        assert prog["ket_qua"]["hub_core_di"] is not None

        logs = "\n".join(prog["logs"])
        assert "[CORE T] đọc thẳng CSV đã phân loại sẵn 202_DI_dot1.csv" in logs, logs
        assert "[CORE T+1] đọc thẳng CSV đã phân loại sẵn 202_DI_dot2.csv" in logs, logs
