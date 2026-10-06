from fastapi.testclient import TestClient
import db
from app import app
import io
import openpyxl

# Initialize database
db.init_db()

client = TestClient(app)

def test_drive_result_upload_and_round_increment():
    print("Testing Excel upload without 'result' column & round incrementing...")
    
    # 1. Fetch drives
    drives_res = client.get("/api/drives")
    assert drives_res.status_code == 200
    drives = drives_res.json()["drives"]
    assert len(drives) > 0, "No drives found"
    
    drive_id = drives[0]["id"]
    print(f"Target drive ID: {drive_id} ({drives[0]['company_name']})")

    # Clean previous test entries to ensure clean starting state
    conn = db.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM student_drive_results WHERE gmail IN ('student1@example.com', 'student2@example.com')")
    cursor.execute("UPDATE drives SET current_round = 1 WHERE id = ?", (drive_id,))
    conn.commit()
    conn.close()
    
    # 2. Create sample Excel file in memory with ONLY 'gmail' column header
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Student Gmail", "Student Name", "Branch"]) # NO 'result' column!
    ws.append(["student1@example.com", "Student One", "CSE"])
    ws.append(["student2@example.com", "Student Two", "ECE"])
    
    excel_bytes = io.BytesIO()
    wb.save(excel_bytes)
    excel_bytes.seek(0)
    
    # 3. Upload Excel file for the drive (Round 1 -> Round 2)
    files = {
        "file": ("shortlist_round1.xlsx", excel_bytes.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    }
    
    res1 = client.post(f"/api/drives/{drive_id}/upload-results", files=files)
    print("Upload 1 Status:", res1.status_code)
    print("Upload 1 Response:", res1.json())
    assert res1.status_code == 200, f"Expected 200 OK, got {res1.status_code}: {res1.text}"
    data1 = res1.json()
    assert data1["success"] is True
    assert data1["updated_count"] == 2
    
    # Check results in DB for this drive
    results_res1 = client.get(f"/api/drives/{drive_id}/results")
    assert results_res1.status_code == 200
    r_data1 = results_res1.json()["results"]
    print("Results after Upload 1:", r_data1)
    
    uploaded_records = {
        item["gmail"]: item for item in r_data1
        if item["gmail"] in {"student1@example.com", "student2@example.com"}
    }
    assert set(uploaded_records) == {"student1@example.com", "student2@example.com"}
    assert all(item["round"] == 2 for item in uploaded_records.values())
    assert all("Round 2" in item["result"] for item in uploaded_records.values())

    conn = db.get_db_connection()
    stored_count = conn.execute(
        "SELECT COUNT(*) FROM student_drive_results WHERE drive_id = ? AND gmail IN (?, ?)",
        (drive_id, "student1@example.com", "student2@example.com")
    ).fetchone()[0]
    conn.close()
    assert stored_count == 2, "Uploaded records were not persisted in SQLite"
            
    print("FIRST UPLOAD PASSED: Students promoted to Round 2!")
    
    # 4. Upload Excel file again for the same drive (Round 2 -> Round 3)
    wb2 = openpyxl.Workbook()
    ws2 = wb2.active
    ws2.append(["email"]) # Only student1 selected for Round 3
    ws2.append(["student1@example.com"])
    
    excel_bytes2 = io.BytesIO()
    wb2.save(excel_bytes2)
    excel_bytes2.seek(0)
    
    files2 = {
        "file": ("shortlist_round2.xlsx", excel_bytes2.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    }
    
    res2 = client.post(f"/api/drives/{drive_id}/upload-results", files=files2)
    print("Upload 2 Status:", res2.status_code)
    print("Upload 2 Response:", res2.json())
    assert res2.status_code == 200
    
    results_res2 = client.get(f"/api/drives/{drive_id}/results")
    r_data2 = results_res2.json()["results"]
    print("Results after Upload 2:", r_data2)
    
    student1_rec = next(r for r in r_data2 if r["gmail"] == "student1@example.com")
    student2_rec = next(r for r in r_data2 if r["gmail"] == "student2@example.com")
    assert student1_rec["round"] == 3, f"Expected round 3 for student1, got {student1_rec['round']}"
    assert "Round 3" in student1_rec["result"]
    assert student2_rec["round"] == 2, "A later upload must not change omitted candidates"
    
    print("SECOND UPLOAD PASSED: student1 promoted to Round 3!")
    
    # 5. Check student dashboard results endpoint
    student_res = client.get("/api/student/results?gmail=student1@example.com")
    assert student_res.status_code == 200
    st_data = student_res.json()["results"]
    assert len(st_data) > 0
    assert st_data[0]["round"] == 3
    print("STUDENT DASHBOARD ENDPOINT PASSED!")

def test_upload_rejects_unknown_drive():
    response = client.post(
        "/api/drives/does-not-exist/upload-results",
        files={"file": ("results.csv", b"email\nstudent@example.com\n", "text/csv")}
    )
    assert response.status_code == 404
    assert response.json()["success"] is False

def test_verdict_upload_persists_status_and_score():
    drives = client.get("/api/drives").json()["drives"]
    drive_id = drives[0]["id"]
    csv_data = (
        "Student Gmail,Result Status / Verdict,Round,Score\n"
        "verdict.student@example.com,Selected,4,91.5\n"
    ).encode()

    response = client.post(
        f"/api/drives/{drive_id}/upload-results",
        files={"file": ("verdict.csv", csv_data, "text/csv")}
    )

    assert response.status_code == 200
    assert response.json()["updated_count"] == 1
    record = next(
        result for result in client.get(f"/api/drives/{drive_id}/results").json()["results"]
        if result["gmail"] == "verdict.student@example.com"
    )
    assert record["result"] == "Selected"
    assert record["round"] == 4
    assert record["score"] == 91.5

def test_upload_rejects_malformed_file_without_writing_records():
    drives = client.get("/api/drives").json()["drives"]
    drive_id = drives[0]["id"]
    response = client.post(
        f"/api/drives/{drive_id}/upload-results",
        files={"file": ("bad.csv", b"Name,Branch\nNo Email,CSE\n", "text/csv")}
    )

    assert response.status_code == 400
    assert response.json()["success"] is False
    conn = db.get_db_connection()
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM student_drive_results WHERE drive_id = ? AND gmail = ?",
            (drive_id, "no email")
        ).fetchone()[0]
    finally:
        conn.close()
    assert count == 0

def test_database_uses_sqlalchemy_engine_for_sqlite():
    assert db.engine.dialect.name == "sqlite"
    conn = db.get_db_connection()
    try:
        assert conn.execute("SELECT 1").fetchone()[0] == 1
    finally:
        conn.close()

if __name__ == "__main__":
    test_drive_result_upload_and_round_increment()
    print("\nALL ROUND INCREMENT TESTS PASSED SUCCESSFULLY!")
