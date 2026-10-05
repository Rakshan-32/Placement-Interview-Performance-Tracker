import os
import sys

# Ensure parent directory is in sys.path for direct pytest invocation
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient

from app import app
from config import TEMPLATES_DIR
import database as db

client = TestClient(app)

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Ensure clean database for test run."""
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS student_drive_results")
    cursor.execute("DROP TABLE IF EXISTS authenticate")
    cursor.execute("DROP TABLE IF EXISTS students_roster")
    cursor.execute("DROP TABLE IF EXISTS drives")
    cursor.execute("DROP TABLE IF EXISTS upload_logs")
    conn.commit()
    conn.close()
    db.init_db()

def test_health_and_root():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "Bulk Upload" in res_root.json()["service"]
    assert "Export" in res_root.json()["service"]

def test_list_and_download_templates():
    # 1. List templates
    res = client.get("/api/templates")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert len(data["templates"]) == 5

    # 2. Download Excel template
    res_dl_xlsx = client.get("/api/templates/download/sample_drive_shortlist.xlsx")
    assert res_dl_xlsx.status_code == 200
    assert len(res_dl_xlsx.content) > 0
    assert "spreadsheetml" in res_dl_xlsx.headers["content-type"]

    # 3. Download CSV template
    res_dl_csv = client.get("/api/templates/download/sample_drive_shortlist.csv")
    assert res_dl_csv.status_code == 200
    assert len(res_dl_csv.content) > 0
    assert "text/csv" in res_dl_csv.headers["content-type"]

def test_upload_drive_shortlist_excel():
    template_path = os.path.join(TEMPLATES_DIR, "sample_drive_shortlist.xlsx")
    assert os.path.exists(template_path), "Sample template file must exist"

    with open(template_path, "rb") as f:
        file_bytes = f.read()

    files = {"file": ("sample_drive_shortlist.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    res = client.post("/api/upload/drive-shortlist/tcs-drive-2026", files=files)

    assert res.status_code == 200, res.text
    data = res.json()
    assert data["success"] is True
    assert data["promoted_count"] > 0
    assert "Shortlist Mode" in data["mode"]

    # Verify candidate promoted to round 2 in DB
    results_res = client.get("/api/drives/tcs-drive-2026/results")
    assert results_res.status_code == 200
    records = results_res.json()["results"]
    assert len(records) > 0
    assert records[0]["round"] == 2
    assert "Shortlisted for Round 2" in records[0]["result"]

def test_upload_drive_results_csv():
    template_path = os.path.join(TEMPLATES_DIR, "sample_drive_results.csv")
    assert os.path.exists(template_path)

    with open(template_path, "rb") as f:
        file_bytes = f.read()

    files = {"file": ("sample_drive_results.csv", file_bytes, "text/csv")}
    res = client.post("/api/upload/drive-results/zoho-drive-2026", files=files)

    assert res.status_code == 200, res.text
    data = res.json()
    assert data["success"] is True
    assert data["updated_count"] > 0
    assert "Verdict Mode" in data["mode"]

    # Check updated results
    results_res = client.get("/api/drives/zoho-drive-2026/results")
    assert results_res.status_code == 200
    records = results_res.json()["results"]
    assert any(r["result"] == "Selected" for r in records)

def test_upload_user_access_excel():
    template_path = os.path.join(TEMPLATES_DIR, "sample_user_access.xlsx")
    assert os.path.exists(template_path)

    with open(template_path, "rb") as f:
        file_bytes = f.read()

    files = {"file": ("sample_user_access.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    res = client.post("/api/upload/user-access", files=files, data={"default_role": "Student"})

    assert res.status_code == 200, res.text
    data = res.json()
    assert data["success"] is True
    assert data["total_rows"] > 0

    # Verify user accounts in DB
    users_res = client.get("/api/users")
    assert users_res.status_code == 200
    users = users_res.json()["users"]
    assert any(u["role"] == "Mentor" for u in users)
    assert any(u["role"] == "Coordinator" for u in users)

def test_upload_student_roster_excel():
    template_path = os.path.join(TEMPLATES_DIR, "sample_student_roster.xlsx")
    assert os.path.exists(template_path)

    with open(template_path, "rb") as f:
        file_bytes = f.read()

    files = {"file": ("sample_student_roster.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    res = client.post("/api/upload/student-roster", files=files)

    assert res.status_code == 200, res.text
    data = res.json()
    assert data["success"] is True
    assert data["imported_count"] > 0

    # Verify students roster
    students_res = client.get("/api/students")
    assert students_res.status_code == 200
    students = students_res.json()["students"]
    assert len(students) >= 7
    rahul = next(s for s in students if s["register_number"] == "2021CS101")
    assert rahul["department"] == "CSE"
    assert rahul["cgpa"] == 7.8
    assert "Python" in rahul["skills"]

def test_upload_company_drives_excel():
    template_path = os.path.join(TEMPLATES_DIR, "sample_company_drives.xlsx")
    assert os.path.exists(template_path)

    with open(template_path, "rb") as f:
        file_bytes = f.read()

    files = {"file": ("sample_company_drives.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    res = client.post("/api/upload/company-drives", files=files)

    assert res.status_code == 200, res.text
    data = res.json()
    assert data["success"] is True
    assert data["created_count"] > 0
    assert len(data["drives"]) >= 5

    # Verify drive in DB
    drives_res = client.get("/api/drives")
    assert drives_res.status_code == 200
    drives = drives_res.json()["drives"]
    google_drive = next((d for d in drives if "google" in d["company_name"].lower()), None)
    assert google_drive is not None
    assert google_drive["ctc_lpa"] == 24.5
    assert google_drive["company_type"] == "PRODUCT"

def test_upload_company_drives_csv():
    template_path = os.path.join(TEMPLATES_DIR, "sample_company_drives.csv")
    assert os.path.exists(template_path)

    with open(template_path, "rb") as f:
        file_bytes = f.read()

    files = {"file": ("sample_company_drives.csv", file_bytes, "text/csv")}
    res = client.post("/api/upload/company-drives", files=files)

    assert res.status_code == 200, res.text
    data = res.json()
    assert data["success"] is True

def test_error_handling_empty_and_bad_file():
    # Empty file error
    files = {"file": ("empty.csv", b"", "text/csv")}
    res = client.post("/api/upload/drive-shortlist/tcs-drive-2026", files=files)
    assert res.status_code == 400
    assert "empty" in res.json()["detail"].lower()

    # Missing email column error
    bad_csv = b"Name,Branch\nRahul,CSE\n"
    files2 = {"file": ("no_email.csv", bad_csv, "text/csv")}
    res2 = client.post("/api/upload/drive-shortlist/tcs-drive-2026", files=files2)
    assert res2.status_code == 400
    assert "email" in res2.json()["detail"].lower()


def test_export_company_drives():
    # 1. Excel export
    res_xlsx = client.get("/api/export/company-drives?format=xlsx")
    assert res_xlsx.status_code == 200
    assert "spreadsheetml" in res_xlsx.headers["content-type"]
    assert "company_drives_export.xlsx" in res_xlsx.headers["content-disposition"]
    assert len(res_xlsx.content) > 0

    # 2. CSV export
    res_csv = client.get("/api/export/company-drives?format=csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "company_drives_export.csv" in res_csv.headers["content-disposition"]
    csv_text = res_csv.content.decode("utf-8-sig")
    assert "Company Name" in csv_text
    assert "Job Role" in csv_text


def test_export_drive_results():
    # 1. Excel export for TCS Drive
    res_xlsx = client.get("/api/export/drive-results/tcs-drive-2026?format=xlsx")
    assert res_xlsx.status_code == 200
    assert "spreadsheetml" in res_xlsx.headers["content-type"]
    assert "results.xlsx" in res_xlsx.headers["content-disposition"]
    assert len(res_xlsx.content) > 0

    # 2. CSV export for TCS Drive
    res_csv = client.get("/api/export/drive-results/tcs-drive-2026?format=csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "results.csv" in res_csv.headers["content-disposition"]
    csv_text = res_csv.content.decode("utf-8-sig")
    assert "Student Gmail" in csv_text
    assert "Current Round" in csv_text

    # 3. Nonexistent drive returns 404
    res_404 = client.get("/api/export/drive-results/non-existent-drive-id")
    assert res_404.status_code == 404
    assert "not found" in res_404.json()["detail"].lower()


def test_export_student_roster():
    # 1. Excel export
    res_xlsx = client.get("/api/export/student-roster?format=xlsx")
    assert res_xlsx.status_code == 200
    assert "spreadsheetml" in res_xlsx.headers["content-type"]
    assert "student_roster_export.xlsx" in res_xlsx.headers["content-disposition"]
    assert len(res_xlsx.content) > 0

    # 2. CSV export
    res_csv = client.get("/api/export/student-roster?format=csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "student_roster_export.csv" in res_csv.headers["content-disposition"]
    csv_text = res_csv.content.decode("utf-8-sig")
    assert "Register Number" in csv_text
    assert "Full Name" in csv_text


def test_export_user_access():
    # 1. Excel export
    res_xlsx = client.get("/api/export/user-access?format=xlsx")
    assert res_xlsx.status_code == 200
    assert "spreadsheetml" in res_xlsx.headers["content-type"]
    assert "user_accounts_export.xlsx" in res_xlsx.headers["content-disposition"]
    assert len(res_xlsx.content) > 0

    # 2. CSV export
    res_csv = client.get("/api/export/user-access?format=csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "user_accounts_export.csv" in res_csv.headers["content-disposition"]
    csv_text = res_csv.content.decode("utf-8-sig")
    assert "User Email" in csv_text
    assert "Role" in csv_text

