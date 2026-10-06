import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from typing import Optional

from .config import TEMPLATES_DIR, MAX_FILE_SIZE_BYTES
from . import database as db
from . import parser
from . import exporter

# Initialize tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield

app = FastAPI(
    title="Placement Portal - Bulk Upload & Export Engine",
    description="Standalone Microservice for Ingestion & Export of Company Drives, Student Drive Results, User Accounts, and Academic Rosters.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for web frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "service": "Placement Bulk Upload & Export Backend Engine",
        "status": "online",
        "docs_url": "/docs",
        "template_endpoints": "/api/templates",
        "upload_endpoints": [
            "POST /api/upload/drive-shortlist/{drive_id}",
            "POST /api/upload/drive-results/{drive_id}",
            "POST /api/upload/user-access",
            "POST /api/upload/student-roster",
            "POST /api/upload/company-drives"
        ],
        "export_endpoints": [
            "GET /api/export/company-drives?format=xlsx|csv",
            "GET /api/export/drive-results/{drive_id}?format=xlsx|csv",
            "GET /api/export/student-roster?format=xlsx|csv",
            "GET /api/export/user-access?format=xlsx|csv"
        ]
    }

@app.get("/health")
def health():
    return {"status": "ok"}


# ==============================================================
# 1. SAMPLE TEMPLATES ENDPOINTS
# ==============================================================

@app.get("/api/templates")
def list_sample_templates():
    """Lists all available sample templates with download links and column schemas."""
    templates = [
        {
            "name": "sample_drive_shortlist",
            "title": "Drive Shortlist Template (Emails Only)",
            "description": "Upload candidate emails to automatically advance them to the next interview round.",
            "formats": ["sample_drive_shortlist.xlsx", "sample_drive_shortlist.csv"],
            "required_columns": ["Student Gmail / Email"],
            "optional_columns": ["Student Name", "Branch"],
            "mode": "Shortlist Mode (Auto-increments round by +1)"
        },
        {
            "name": "sample_drive_results",
            "title": "Drive Results / Verdicts Template",
            "description": "Upload candidate evaluations with explicit statuses (Selected, Rejected, On Hold) and scores.",
            "formats": ["sample_drive_results.xlsx", "sample_drive_results.csv"],
            "required_columns": ["Student Gmail / Email", "Result Status / Verdict"],
            "optional_columns": ["Round", "Score", "Student Name"],
            "mode": "Verdict Mode (Sets exact status)"
        },
        {
            "name": "sample_user_access",
            "title": "User Accounts & Role Provisioning Template",
            "description": "Bulk create or update accounts for Students, Mentors, Coordinators, and Recruiters.",
            "formats": ["sample_user_access.xlsx", "sample_user_access.csv"],
            "required_columns": ["User Email"],
            "optional_columns": ["Role (Student, Mentor, etc.)", "Password"],
            "mode": "Role Access Mode"
        },
        {
            "name": "sample_student_roster",
            "title": "Student Academic Profiles Template",
            "description": "Bulk import academic records, CGPA, 10th/12th percentages, and technical skills.",
            "formats": ["sample_student_roster.xlsx", "sample_student_roster.csv"],
            "required_columns": ["Register Number", "Full Name", "Student Email", "Department", "CGPA"],
            "optional_columns": ["10th Percentage", "12th Percentage", "Technical Skills"],
            "mode": "Academic Roster Mode"
        },
        {
            "name": "sample_company_drives",
            "title": "Company Placement Drives Template",
            "description": "Bulk schedule on-campus placement drives with company type, CTC LPA, eligibility criteria, and rounds.",
            "formats": ["sample_company_drives.xlsx", "sample_company_drives.csv"],
            "required_columns": ["Company Name", "Job Role", "CTC LPA"],
            "optional_columns": ["Company Type", "Required CGPA", "Allowed Branches", "Total Rounds", "Location", "Drive Date", "Status"],
            "mode": "Company Drive Scheduling Mode"
        }
    ]
    return {"success": True, "templates": templates}


@app.get("/api/templates/download/{filename}")
def download_template(filename: str):
    """Downloads a specific Excel (.xlsx) or CSV sample template file."""
    filepath = os.path.join(TEMPLATES_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template file '{filename}' was not found. Call /api/templates to see available files."
        )

    mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if filename.endswith(".xlsx") else "text/csv"
    return FileResponse(filepath, media_type=mime_type, filename=filename)


# ==============================================================
# 2. BULK UPLOAD: DRIVE SHORTLIST (AUTO-INCREMENT ROUND)
# ==============================================================

@app.post("/api/upload/drive-shortlist/{drive_id}")
async def upload_drive_shortlist(drive_id: str, file: UploadFile = File(...)):
    """
    Shortlist Mode Ingestion:
    Uploads an Excel (.xlsx) or CSV containing shortlisted student emails.
    Automatically increments each candidate's round by +1 (e.g., Round 1 -> Round 2)
    and updates their status to 'Shortlisted for Round N'.
    """
    drive = db.get_drive(drive_id)
    if not drive:
        raise HTTPException(status_code=404, detail=f"Drive with ID '{drive_id}' was not found.")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowed 10MB limit.")

    try:
        records, skipped_count, is_verdict_mode = parser.parse_drive_records(content, file.filename)
    except ValueError as e:
        db.record_upload_log("Drive Shortlist", file.filename, 0, 0, 0, status=f"FAILED: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    processed_records = []
    for item in records:
        res = db.process_shortlist_record(drive_id, item["email"], base_round=drive.get("current_round", 1))
        processed_records.append(res)

    db.record_upload_log(
        upload_type=f"Drive Shortlist ({drive['company_name']})",
        filename=file.filename,
        total_rows=len(records) + skipped_count,
        processed_count=len(processed_records),
        skipped_count=skipped_count,
        status="SUCCESS"
    )

    return JSONResponse(status_code=status.HTTP_200_OK, content={
        "success": True,
        "mode": "Shortlist Mode (Auto-promoted candidates to next round)",
        "drive_id": drive_id,
        "company_name": drive["company_name"],
        "total_rows": len(records) + skipped_count,
        "promoted_count": len(processed_records),
        "skipped_count": skipped_count,
        "records": processed_records
    })


# ==============================================================
# 3. BULK UPLOAD: DRIVE RESULTS / VERDICTS
# ==============================================================

@app.post("/api/upload/drive-results/{drive_id}")
async def upload_drive_results(drive_id: str, file: UploadFile = File(...)):
    """
    Verdict Mode Ingestion:
    Uploads an Excel (.xlsx) or CSV containing student emails and explicit status/results
    (e.g., 'Selected', 'Rejected', 'On Hold') along with optional round number and scores.
    """
    drive = db.get_drive(drive_id)
    if not drive:
        raise HTTPException(status_code=404, detail=f"Drive with ID '{drive_id}' was not found.")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowed 10MB limit.")

    try:
        records, skipped_count, is_verdict_mode = parser.parse_drive_records(content, file.filename)
    except ValueError as e:
        db.record_upload_log("Drive Results", file.filename, 0, 0, 0, status=f"FAILED: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    processed_records = []
    for item in records:
        verdict = item.get("verdict") or "Shortlisted"
        res = db.process_verdict_record(
            drive_id=drive_id,
            email=item["email"],
            verdict=verdict,
            round_num=item.get("round"),
            score=item.get("score")
        )
        processed_records.append(res)

    db.record_upload_log(
        upload_type=f"Drive Results ({drive['company_name']})",
        filename=file.filename,
        total_rows=len(records) + skipped_count,
        processed_count=len(processed_records),
        skipped_count=skipped_count,
        status="SUCCESS"
    )

    return JSONResponse(status_code=status.HTTP_200_OK, content={
        "success": True,
        "mode": "Verdict Mode (Updated explicit status and scores)",
        "drive_id": drive_id,
        "company_name": drive["company_name"],
        "total_rows": len(records) + skipped_count,
        "updated_count": len(processed_records),
        "skipped_count": skipped_count,
        "records": processed_records
    })


# ==============================================================
# 4. BULK UPLOAD: USER ACCESS & ROLE PROVISIONING
# ==============================================================

@app.post("/api/upload/user-access")
async def upload_user_access(
    file: UploadFile = File(...),
    default_role: str = Form("Student")
):
    """
    User Account Provisioning Ingestion:
    Uploads an Excel (.xlsx) or CSV containing user emails.
    Assigns role ('Student', 'Mentor', 'Coordinator', 'Recruiter') and optional custom password.
    Updates existing accounts and creates new accounts without collision.
    """
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowed 10MB limit.")

    try:
        records, skipped_count = parser.parse_user_access_records(content, file.filename, default_role=default_role)
    except ValueError as e:
        db.record_upload_log("User Access", file.filename, 0, 0, 0, status=f"FAILED: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    created_count = 0
    updated_count = 0
    processed_users = []

    for item in records:
        res = db.upsert_user_account(
            email=item["email"],
            role=item["role"],
            password=item.get("password")
        )
        if res["action"] == "Created":
            created_count += 1
        else:
            updated_count += 1
        processed_users.append(res)

    db.record_upload_log(
        upload_type="User Access Onboarding",
        filename=file.filename,
        total_rows=len(records) + skipped_count,
        processed_count=len(processed_users),
        skipped_count=skipped_count,
        status="SUCCESS"
    )

    return JSONResponse(status_code=status.HTTP_200_OK, content={
        "success": True,
        "message": f"Successfully onboarded {len(processed_users)} user accounts.",
        "total_rows": len(records) + skipped_count,
        "created_count": created_count,
        "updated_count": updated_count,
        "skipped_count": skipped_count,
        "users": processed_users
    })


# ==============================================================
# 5. BULK UPLOAD: STUDENT ACADEMIC ROSTER
# ==============================================================

@app.post("/api/upload/student-roster")
async def upload_student_roster(file: UploadFile = File(...)):
    """
    Academic Roster Ingestion:
    Uploads an Excel (.xlsx) or CSV containing complete student academic records:
    Register Number, Full Name, Email, Department, CGPA, 10th%, 12th%, Technical Skills.
    """
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowed 10MB limit.")

    try:
        records, skipped_count = parser.parse_student_roster_records(content, file.filename)
    except ValueError as e:
        db.record_upload_log("Student Roster", file.filename, 0, 0, 0, status=f"FAILED: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    processed_students = []
    for item in records:
        res = db.upsert_student_roster_record(
            register_number=item["register_number"],
            name=item["name"],
            email=item["email"],
            department=item["department"],
            cgpa=item["cgpa"],
            tenth=item.get("tenth_percentage"),
            twelfth=item.get("twelfth_percentage"),
            skills=item.get("skills", "")
        )
        processed_students.append(res)

    db.record_upload_log(
        upload_type="Student Academic Roster",
        filename=file.filename,
        total_rows=len(records) + skipped_count,
        processed_count=len(processed_students),
        skipped_count=skipped_count,
        status="SUCCESS"
    )

    return JSONResponse(status_code=status.HTTP_200_OK, content={
        "success": True,
        "message": f"Successfully imported {len(processed_students)} student academic profiles.",
        "total_rows": len(records) + skipped_count,
        "imported_count": len(processed_students),
        "skipped_count": skipped_count,
        "students": processed_students
    })


# ==============================================================
# 6. BULK UPLOAD: COMPANY PLACEMENT DRIVES
# ==============================================================

@app.post("/api/upload/company-drives")
async def upload_company_drives(file: UploadFile = File(...)):
    """
    Company Drives Scheduling Ingestion:
    Uploads an Excel (.xlsx) or CSV containing company placement drive schedules:
    Company Name, Job Role, CTC LPA, Company Type, Required CGPA, Allowed Branches,
    Total Rounds, Location, Drive Date, Status.
    """
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowed 10MB limit.")

    try:
        records, skipped_count = parser.parse_company_drives_records(content, file.filename)
    except ValueError as e:
        db.record_upload_log("Company Drives", file.filename, 0, 0, 0, status=f"FAILED: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    created_count = 0
    updated_count = 0
    processed_drives = []

    for item in records:
        res = db.upsert_company_drive_record(
            company_name=item["company_name"],
            job_role=item["job_role"],
            ctc_lpa=item["ctc_lpa"],
            company_type=item["company_type"],
            required_cgpa=item["required_cgpa"],
            allowed_branches=item["allowed_branches"],
            location=item["location"],
            total_rounds=item["total_rounds"],
            drive_date=item["drive_date"],
            status=item["status"]
        )
        if res["action"] == "Created":
            created_count += 1
        else:
            updated_count += 1
        processed_drives.append(res)

    db.record_upload_log(
        upload_type="Company Drives Scheduling",
        filename=file.filename,
        total_rows=len(records) + skipped_count,
        processed_count=len(processed_drives),
        skipped_count=skipped_count,
        status="SUCCESS"
    )

    return JSONResponse(status_code=status.HTTP_200_OK, content={
        "success": True,
        "message": f"Successfully processed {len(processed_drives)} company placement drives ({created_count} created, {updated_count} updated).",
        "total_rows": len(records) + skipped_count,
        "created_count": created_count,
        "updated_count": updated_count,
        "skipped_count": skipped_count,
        "drives": processed_drives
    })


# ==============================================================
# 7. DATA VIEWING & VERIFICATION ENDPOINTS
# ==============================================================

@app.get("/api/drives")
def list_drives():
    """Returns all available placement drives."""
    return {"success": True, "drives": db.get_all_drives()}

@app.get("/api/drives/{drive_id}/results")
def get_drive_results(drive_id: str):
    """Returns candidate results recorded for a specific placement drive."""
    results = db.get_drive_results(drive_id)
    return {"success": True, "drive_id": drive_id, "count": len(results), "results": results}

@app.get("/api/users")
def list_users():
    """Returns all onboarded user accounts in authenticate table."""
    users = db.get_all_users()
    return {"success": True, "count": len(users), "users": users}

@app.get("/api/students")
def list_students():
    """Returns all academic student profiles in roster table."""
    students = db.get_all_student_roster()
    return {"success": True, "count": len(students), "students": students}

@app.get("/api/logs")
def list_upload_logs():
    """Returns audit history of all bulk upload operations."""
    logs = db.get_upload_logs()
    return {"success": True, "count": len(logs), "logs": logs}


# ==============================================================
# 8. DATA EXPORT ENDPOINTS (EXCEL & CSV DOWNLOAD)
# ==============================================================

@app.get("/api/export/company-drives")
def export_company_drives(format: str = "xlsx"):
    """
    Exports all company placement drives to an Excel (.xlsx) or CSV file.
    Query param format: 'xlsx' or 'csv' (defaults to 'xlsx').
    """
    drives = db.get_all_drives()
    return exporter.export_company_drives_data(drives, format_type=format)


@app.get("/api/export/drive-results/{drive_id}")
def export_drive_results(drive_id: str, format: str = "xlsx"):
    """
    Exports student candidate results for a specific drive to an Excel (.xlsx) or CSV file.
    Query param format: 'xlsx' or 'csv' (defaults to 'xlsx').
    """
    drive = db.get_drive(drive_id)
    if not drive:
        raise HTTPException(status_code=404, detail=f"Drive with ID '{drive_id}' was not found.")

    results = db.get_drive_results(drive_id)
    return exporter.export_drive_results_data(results, drive_info=drive, format_type=format)


@app.get("/api/export/student-roster")
def export_student_roster(format: str = "xlsx"):
    """
    Exports all student academic profiles in roster to an Excel (.xlsx) or CSV file.
    Query param format: 'xlsx' or 'csv' (defaults to 'xlsx').
    """
    students = db.get_all_student_roster()
    return exporter.export_student_roster_data(students, format_type=format)


@app.get("/api/export/user-access")
def export_user_access(format: str = "xlsx"):
    """
    Exports all user accounts in authenticate table to an Excel (.xlsx) or CSV file.
    Query param format: 'xlsx' or 'csv' (defaults to 'xlsx').
    """
    users = db.get_all_users()
    return exporter.export_user_access_data(users, format_type=format)


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8001, reload=True)
