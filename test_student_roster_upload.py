import openpyxl
import io
import db
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_student_roster_upload_and_profile_retrieval():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Student Roster"

    # Header row
    ws.append([
        "Register Number", "Full Name", "Student Email", "Department",
        "CGPA", "10th Percentage", "12th Percentage", "Technical Skills"
    ])

    # Rows
    ws.append(["2026STUDENT01", "Ananya Verma", "ananya.v@college.edu", "CSE", 9.1, 95.0, 93.5, "Python, DSA, System Design"])

    excel_file = io.BytesIO()
    wb.save(excel_file)
    excel_file.seek(0)

    res = client.post(
        "/api/upload/student-roster",
        files={"file": ("roster_test.xlsx", excel_file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )

    assert res.status_code == 200, f"Upload failed: {res.text}"
    json_data = res.json()
    assert json_data["success"] is True
    assert json_data["imported_count"] == 1

    # Test GET /api/student/profile for the uploaded student
    profile_res = client.get("/api/student/profile?gmail=ananya.v@college.edu")
    assert profile_res.status_code == 200
    p_data = profile_res.json()
    assert p_data["success"] is True
    prof = p_data["profile"]

    assert prof["register_number"] == "2026STUDENT01"
    assert prof["name"] == "Ananya Verma"
    assert prof["department"] == "CSE"
    assert prof["cgpa"] == 9.1
    assert prof["tenth_percentage"] == 95.0
    assert prof["twelfth_percentage"] == 93.5
    assert "Python" in prof["skills_list"]

if __name__ == "__main__":
    test_student_roster_upload_and_profile_retrieval()
    print("ALL STUDENT ROSTER & PROFILE TESTS PASSED!")
