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
    
    for item in r_data1:
        if item["gmail"] in ["student1@example.com", "student2@example.com"]:
            assert item["round"] == 2, f"Expected round 2, got {item['round']}"
            assert "Round 2" in item["result"]
            
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
    assert student1_rec["round"] == 3, f"Expected round 3 for student1, got {student1_rec['round']}"
    assert "Round 3" in student1_rec["result"]
    
    print("SECOND UPLOAD PASSED: student1 promoted to Round 3!")
    
    # 5. Check student dashboard results endpoint
    student_res = client.get("/api/student/results?gmail=student1@example.com")
    assert student_res.status_code == 200
    st_data = student_res.json()["results"]
    assert len(st_data) > 0
    assert st_data[0]["round"] == 3
    print("STUDENT DASHBOARD ENDPOINT PASSED!")

if __name__ == "__main__":
    test_drive_result_upload_and_round_increment()
    print("\nALL ROUND INCREMENT TESTS PASSED SUCCESSFULLY!")
