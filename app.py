from fastapi import FastAPI, HTTPException, status, Form, UploadFile, File, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import os
import uvicorn
import io
import csv
import openpyxl
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

import db
import intervention_service
import bulk_upload_module.parser as bulk_parser
import bulk_upload_module.exporter as bulk_exporter
from bulk_upload_module.config import TEMPLATES_DIR, MAX_FILE_SIZE_BYTES


# Initialize database on startup
db.init_db()

app = FastAPI(
    title="Placement Portal & Dedicated Bulk Upload Engine",
    description="Integrated API for Authentication, Placement Drives, Student Profiles, and Bulk Ingestion/Export."
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins during dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LoginRequest(BaseModel):
    gmail: str = Field(..., json_schema_extra={"example": "student@gmail.com"})
    password: str = Field(..., json_schema_extra={"example": "student123"})

@app.post("/api/login")
async def login(credentials: LoginRequest):
    gmail = credentials.gmail.strip()
    password = credentials.password
    
    if not gmail or not password:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": "Gmail and password are required"}
        )
    
    # Query database table 'authenticate' for user record
    user = db.get_user_by_gmail(gmail)
    
    # Check if user exists and compare stored password
    if not user or user["password"] != password:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "success": False,
                "message": "Invalid Gmail or password"
            }
        )
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "message": "Logged in successfully",
            "user": {
                "uuid": user["uuid"],
                "gmail": user["gmail"],
                "role": user["role"],
                "department": user.get("department") or "CSE"
            }
        }
    )

class CreateDriveRequest(BaseModel):
    company_name: str
    job_role: str
    ctc_lpa: float
    min_cgpa: float = 0.0
    allowed_branches: str = "All"
    location: str = "On Campus"
    status: str = "Active"
    deadline: str = None

@app.get("/api/users")
async def list_demo_users():
    """Helper endpoint to list available demo accounts for convenience."""
    users = db.get_all_users()
    return {"success": True, "users": users, "count": len(users)}

@app.get("/api/drives")
async def list_drives():
    """Endpoint to retrieve all placement drives from SQLite."""
    drives = db.get_all_drives()
    for d in drives:
        d["results_count"] = db.get_drive_results_count(d["id"])
    return {"success": True, "drives": drives}

@app.post("/api/drives")
async def create_new_drive(drive_data: CreateDriveRequest):
    """Endpoint for Coordinator to create a new placement drive."""
    if not drive_data.company_name.strip() or not drive_data.job_role.strip():
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": "Company name and job role are required."}
        )
    
    new_drive = db.create_drive(
        company_name=drive_data.company_name.strip(),
        job_role=drive_data.job_role.strip(),
        ctc_lpa=drive_data.ctc_lpa,
        min_cgpa=drive_data.min_cgpa,
        allowed_branches=drive_data.allowed_branches.strip(),
        location=drive_data.location.strip(),
        status=drive_data.status.strip() if drive_data.status else "Active",
        deadline=drive_data.deadline
    )
    new_drive["results_count"] = 0
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"success": True, "message": "Drive created successfully!", "drive": new_drive}
    )

@app.get("/api/drives/{drive_id}/results")
async def get_drive_results(drive_id: str):
    """Retrieve all student evaluation results for a specific drive."""
    results = db.get_drive_results(drive_id)
    return {"success": True, "results": results, "count": len(results)}


# ==============================================================
# SAMPLE TEMPLATES ENDPOINTS
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
# BULK UPLOAD INGESTION ENDPOINTS
# ==============================================================

@app.post("/api/upload/drive-shortlist/{drive_id}")
async def upload_drive_shortlist(drive_id: str, file: UploadFile = File(...)):
    drive = db.get_drive(drive_id)
    if not drive:
        raise HTTPException(status_code=404, detail=f"Drive with ID '{drive_id}' was not found.")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowed 10MB limit.")

    try:
        records, skipped_count, is_verdict_mode = bulk_parser.parse_drive_records(content, file.filename)
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


@app.post("/api/upload/drive-results/{drive_id}")
async def upload_drive_results_endpoint(drive_id: str, file: UploadFile = File(...)):
    drive = db.get_drive(drive_id)
    if not drive:
        raise HTTPException(status_code=404, detail=f"Drive with ID '{drive_id}' was not found.")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowed 10MB limit.")

    try:
        records, skipped_count, is_verdict_mode = bulk_parser.parse_drive_records(content, file.filename)
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


@app.post("/api/drives/{drive_id}/upload-results")
async def upload_drive_results(drive_id: str, file: UploadFile = File(...)):
    """
    Upload Excel (.xlsx) or CSV file containing candidate results.
    Auto-detects Shortlist Mode vs Verdict Mode and updates student statuses for this company drive.
    """
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        return JSONResponse(status_code=400, content={"success": False, "message": "File size exceeds maximum allowed 10MB limit.", "detail": "File size exceeds limit."})

    try:
        records, skipped_count, is_verdict_mode = bulk_parser.parse_drive_records(content, file.filename)
    except ValueError as e:
        db.record_upload_log("Drive Upload", file.filename, 0, 0, 0, status=f"FAILED: {str(e)}")
        return JSONResponse(status_code=400, content={"success": False, "message": str(e), "detail": str(e)})

    drive = db.get_drive(drive_id)
    base_round = drive.get("current_round", 1) if drive else 1

    processed_records = []
    for item in records:
        if is_verdict_mode and item.get("verdict"):
            res = db.process_verdict_record(
                drive_id=drive_id,
                email=item["email"],
                verdict=item["verdict"],
                round_num=item.get("round"),
                score=item.get("score"),
                max_score=item.get("max_score"),
                feedback=item.get("feedback"),
                weakness_area=item.get("weakness_area"),
                rejection_reason=item.get("rejection_reason"),
                attempt_date=item.get("attempt_date")
            )
        else:
            res = db.process_shortlist_record(drive_id, item["email"], base_round=base_round)
        processed_records.append(res)

    db.record_upload_log(
        upload_type=f"Drive Candidate Upload ({drive_id})",
        filename=file.filename,
        total_rows=len(records) + skipped_count,
        processed_count=len(processed_records),
        skipped_count=skipped_count,
        status="SUCCESS"
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "message": f"Successfully processed {len(processed_records)} student result records.",
            "total_rows": len(records) + skipped_count,
            "updated_count": len(processed_records),
            "skipped_count": skipped_count,
            "processed_records": processed_records
        }
    )


@app.post("/api/upload/user-access")
@app.post("/api/users/upload-access")
async def upload_user_access(
    file: UploadFile = File(...),
    default_role: str = Form("Student")
):
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        return JSONResponse(status_code=400, content={"success": False, "message": "File size exceeds maximum allowed 10MB limit.", "detail": "File size exceeds limit."})

    try:
        records, skipped_count = bulk_parser.parse_user_access_records(content, file.filename, default_role=default_role)
    except ValueError as e:
        db.record_upload_log("User Access", file.filename, 0, 0, 0, status=f"FAILED: {str(e)}")
        return JSONResponse(status_code=400, content={"success": False, "message": str(e), "detail": str(e)})

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
        "message": f"Successfully granted access to {len(processed_users)} user accounts ({created_count} created, {updated_count} updated).",
        "total_rows": len(records) + skipped_count,
        "total_processed": len(processed_users),
        "created_count": created_count,
        "updated_count": updated_count,
        "skipped_count": skipped_count,
        "processed_users": processed_users,
        "users": processed_users
    })


@app.post("/api/upload/student-roster")
async def upload_student_roster(file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowed 10MB limit.")

    try:
        records, skipped_count = bulk_parser.parse_student_roster_records(content, file.filename)
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


@app.post("/api/upload/company-drives")
async def upload_company_drives(file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowed 10MB limit.")

    try:
        records, skipped_count = bulk_parser.parse_company_drives_records(content, file.filename)
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


class GrantSingleAccessRequest(BaseModel):
    gmail: str
    role: str = "Student"
    password: str = None

@app.post("/api/users/grant-single-access")
async def grant_single_access(req: GrantSingleAccessRequest):
    gmail = req.gmail.strip().lower()
    if not gmail or "@" not in gmail:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": "Please enter a valid Gmail address."}
        )
    
    result = db.grant_single_user_access(gmail=gmail, role=req.role, password=req.password)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "message": f"Successfully granted {result['role']} access to {gmail}.",
            "user": result
        }
    )


# ==============================================================
# AUDIT LOGS & DATA VIEWING ENDPOINTS
# ==============================================================

@app.get("/api/students")
def list_students():
    students = db.get_all_student_roster()
    return {"success": True, "count": len(students), "students": students}

@app.get("/api/logs")
def list_upload_logs():
    logs = db.get_upload_logs()
    return {"success": True, "count": len(logs), "logs": logs}


# ==============================================================
# EXPORT ENDPOINTS (EXCEL & CSV DOWNLOAD)
# ==============================================================

@app.get("/api/export/company-drives")
def export_company_drives(format: str = "xlsx"):
    drives = db.get_all_drives()
    return bulk_exporter.export_company_drives_data(drives, format_type=format)

@app.get("/api/export/drive-results/{drive_id}")
def export_drive_results(drive_id: str, format: str = "xlsx"):
    drive = db.get_drive(drive_id)
    if not drive:
        raise HTTPException(status_code=404, detail=f"Drive with ID '{drive_id}' was not found.")
    results = db.get_drive_results(drive_id)
    return bulk_exporter.export_drive_results_data(results, drive_info=drive, format_type=format)

@app.get("/api/export/student-roster")
def export_student_roster(format: str = "xlsx"):
    students = db.get_all_student_roster()
    return bulk_exporter.export_student_roster_data(students, format_type=format)

@app.get("/api/export/user-access")
def export_user_access(format: str = "xlsx"):
    users = db.get_all_users()
    return bulk_exporter.export_user_access_data(users, format_type=format)


# ==========================================
# STUDENT API ENDPOINTS
# ==========================================

class StudentApplyRequest(BaseModel):
    gmail: str
    drive_id: str

@app.get("/api/student/profile")
async def get_student_profile(gmail: str):
    """viewStudentProfile() — Retrieve a student's personal & academic profile information updated by coordinator."""
    profile = db.get_student_profile_by_email(gmail)
    if not profile:
        email_clean = gmail.strip().lower()
        default_name = email_clean.split("@")[0].replace(".", " ").title()
        profile = {
            "student_id": "demo-id",
            "register_number": "312321104012",
            "name": default_name,
            "email": email_clean,
            "department": "CSE",
            "cgpa": 8.4,
            "tenth_percentage": 91.5,
            "twelfth_percentage": 88.0,
            "skills": "Python, Data Structures, React, SQL",
            "skills_list": ["Python", "Data Structures", "React", "SQL"]
        }
    return {"success": True, "profile": profile}

@app.get("/api/student/results")
async def get_student_results(gmail: str):
    """viewRoundStatus() — Retrieve all evaluation results for a student across drives."""
    results = db.get_student_drive_results(gmail)
    return {"success": True, "results": results}

@app.get("/api/student/applications")
async def get_student_applications(gmail: str):
    """viewJobApplication() — Retrieve all drives registered by student."""
    results = db.get_student_drive_results(gmail)
    apps = []
    for r in results:
        apps.append({
            "registration_id": r["id"],
            "drive_id": r["drive_id"],
            "company_name": r.get("company_name", "Drive"),
            "job_role": r.get("job_role", "Role"),
            "ctc_lpa": r.get("ctc_lpa", 10.0),
            "final_status": "REGISTERED" if "Shortlisted" in r.get("result", "") else r.get("result", "REGISTERED"),
            "registered_at": r.get("updated_at", "")
        })
    return {"success": True, "applications": apps}

@app.post("/api/student/apply")
async def apply_student_drive(req: StudentApplyRequest):
    """applyJobApplication() — Apply student to a placement drive."""
    res = db.increment_student_drive_round(req.drive_id, req.gmail)
    return {"success": True, "message": "Successfully registered for drive", "registration": res}

@app.get("/api/student/analysis")
async def get_student_analysis(gmail: str):
    """viewAnalysis() — Performance & failure pattern analysis."""
    results = db.get_student_drive_results(gmail)
    patterns = intervention_service.analyse_student_patterns(results)
    failed_rounds = patterns["failed_by_round"]
    most_failed_round = max(failed_rounds, key=failed_rounds.get) if failed_rounds else None

    return {
        "success": True,
        "pass_rate": patterns["pass_rate"],
        "total_drives_applied": len(set(r["drive_id"] for r in results)),
        "total_rounds_attempted": patterns["total_rounds"],
        "rounds_passed": patterns["passed_rounds"],
        "rounds_failed": patterns["failed_rounds"],
        "most_failed_round": most_failed_round,
        "top_weaknesses": patterns["top_weaknesses"],
        "risk_level": patterns["risk_level"]
    }


# ==========================================
# INTERVENTION AND FAILURE ANALYSIS API
# ==========================================


class InterventionGenerateRequest(BaseModel):
    student_id: str = None
    gmail: str = None


class InterventionStatusRequest(BaseModel):
    status: str


class InterventionActionRequest(BaseModel):
    completed: bool = None
    notes: str = None


def _requester(user_id: str, role: str, department: str):
    if not user_id:
        raise HTTPException(status_code=401, detail="X-User-Id is required")
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Unknown user")
    if role and role.strip().lower() != user["role"].strip().lower():
        raise HTTPException(status_code=403, detail="User role does not match the authenticated account")
    user["department"] = department or user.get("department") or "CSE"
    return user


def _scoped_student(user: dict, student_id: str = None, gmail: str = None):
    students = db.get_students_for_scope(user["uuid"], user["role"], user.get("department"))
    target = None
    for student in students:
        if (student_id and student["uuid"] == student_id) or (gmail and student["gmail"].lower() == gmail.strip().lower()):
            target = student
            break
    if not target:
        raise HTTPException(status_code=403, detail="You are not allowed to access this student")
    return target


def _visible_interventions(user: dict):
    students = db.get_students_for_scope(user["uuid"], user["role"], user.get("department"))
    return db.get_interventions(student_gmails=[student["gmail"] for student in students])


@app.get("/api/interventions")
async def list_interventions(
    x_user_id: str = Header(None),
    x_user_role: str = Header(None),
    x_department: str = Header(None),
):
    user = _requester(x_user_id, x_user_role, x_department)
    return {"success": True, "interventions": _visible_interventions(user)}


@app.get("/api/interventions/students")
async def list_intervention_students(
    x_user_id: str = Header(None),
    x_user_role: str = Header(None),
    x_department: str = Header(None),
):
    user = _requester(x_user_id, x_user_role, x_department)
    students = db.get_students_for_scope(user["uuid"], user["role"], user.get("department"))
    visible_interventions = db.get_interventions(student_gmails=[student["gmail"] for student in students])
    by_gmail = {}
    for intervention in visible_interventions:
        by_gmail.setdefault(intervention["student_gmail"].lower(), []).append(intervention)
    for student in students:
        student["interventions"] = by_gmail.get(student["gmail"].lower(), [])[:3]
        student["intervention_count"] = len(student["interventions"])
    return {"success": True, "students": students}


@app.get("/api/interventions/{student_id}")
async def get_student_interventions(
    student_id: str,
    x_user_id: str = Header(None),
    x_user_role: str = Header(None),
    x_department: str = Header(None),
):
    user = _requester(x_user_id, x_user_role, x_department)
    student = _scoped_student(user, student_id=student_id)
    return {
        "success": True,
        "student": student,
        "interventions": db.get_interventions(student_gmail=student["gmail"]),
        "analysis": intervention_service.analyse_student_patterns(db.get_student_analysis_records(student["gmail"])),
    }


@app.post("/api/interventions/generate")
async def generate_intervention(
    request: InterventionGenerateRequest,
    x_user_id: str = Header(None),
    x_user_role: str = Header(None),
    x_department: str = Header(None),
):
    user = _requester(x_user_id, x_user_role, x_department)
    if user["role"].strip().lower() == "student":
        raise HTTPException(status_code=403, detail="Students cannot generate interventions")
    if not request.student_id and not request.gmail:
        raise HTTPException(status_code=400, detail="student_id or gmail is required")

    student = _scoped_student(user, request.student_id, request.gmail)
    records = db.get_student_analysis_records(student["gmail"])
    patterns = intervention_service.analyse_student_patterns(records)
    previous = db.get_interventions(student_gmail=student["gmail"])
    previous_actions = [action for item in previous for action in item.get("actions", [])]

    try:
        intervention, actions = intervention_service.build_intervention(
            student, patterns, previous_actions, user["uuid"]
        )
        saved = db.save_intervention(intervention, actions)
    except intervention_service.AgentRateLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail=str(exc),
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
    except intervention_service.AgentConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except intervention_service.AgentResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Intervention generation failed: {exc}") from exc

    return {"success": True, "intervention": saved, "analysis": patterns}


@app.post("/api/interventions/generate-all")
async def generate_all_interventions(
    x_user_id: str = Header(None),
    x_user_role: str = Header(None),
    x_department: str = Header(None),
):
    user = _requester(x_user_id, x_user_role, x_department)
    if user["role"].strip().lower() == "student":
        raise HTTPException(status_code=403, detail="Students cannot generate interventions")

    students = db.get_students_for_scope(user["uuid"], user["role"], user.get("department"))
    generated = []
    failures = []
    for student in students:
        records = db.get_student_analysis_records(student["gmail"])
        patterns = intervention_service.analyse_student_patterns(records)
        previous = db.get_interventions(student_gmail=student["gmail"])
        previous_actions = [action for item in previous for action in item.get("actions", [])]
        try:
            intervention, actions = intervention_service.build_intervention(
                student, patterns, previous_actions, user["uuid"]
            )
            generated.append(db.save_intervention(intervention, actions))
        except intervention_service.AgentConfigurationError as exc:
            failures.append({"student_id": student["uuid"], "gmail": student["gmail"], "error": str(exc)})
        except intervention_service.AgentResponseError as exc:
            failures.append({"student_id": student["uuid"], "gmail": student["gmail"], "error": str(exc)})
        except Exception as exc:
            failures.append({"student_id": student["uuid"], "gmail": student["gmail"], "error": f"Generation failed: {exc}"})

    return {"success": len(failures) == 0, "generated": generated, "failures": failures}


@app.patch("/api/interventions/{intervention_id}/status")
async def change_intervention_status(
    intervention_id: str,
    request: InterventionStatusRequest,
    x_user_id: str = Header(None),
    x_user_role: str = Header(None),
    x_department: str = Header(None),
):
    user = _requester(x_user_id, x_user_role, x_department)
    if user["role"].strip().lower() == "student":
        raise HTTPException(status_code=403, detail="Students cannot update intervention status")
    allowed = {"OPEN", "IN_PROGRESS", "COMPLETED", "CANCELLED"}
    new_status = request.status.strip().upper()
    if new_status not in allowed:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(allowed)}")
    visible = {item["id"] for item in _visible_interventions(user)}
    if intervention_id not in visible:
        raise HTTPException(status_code=403, detail="You are not allowed to update this intervention")
    db.update_intervention_status(intervention_id, new_status)
    return {"success": True, "status": new_status}


@app.patch("/api/intervention/actions/{action_id}")
async def change_intervention_action(
    action_id: str,
    request: InterventionActionRequest,
    x_user_id: str = Header(None),
    x_user_role: str = Header(None),
    x_department: str = Header(None),
):
    user = _requester(x_user_id, x_user_role, x_department)
    if user["role"].strip().lower() == "student":
        raise HTTPException(status_code=403, detail="Students cannot update intervention actions")
    visible_action_ids = {
        action["id"]
        for item in _visible_interventions(user)
        for action in item.get("actions", [])
    }
    if action_id not in visible_action_ids:
        raise HTTPException(status_code=403, detail="You are not allowed to update this action")
    if not db.update_intervention_action(action_id, request.completed, request.notes):
        raise HTTPException(status_code=404, detail="Action not found")
    return {"success": True, "action_id": action_id}

@app.post("/api/student/resume-upload")
async def upload_student_resume(file: UploadFile = File(...), gmail: str = Form("student@gmail.com")):
    """resumeUpload() — Upload student resume file."""
    filename = file.filename.lower()
    if not (filename.endswith(".pdf") or filename.endswith(".doc") or filename.endswith(".docx")):
        return JSONResponse(status_code=400, content={"success": False, "message": "Only PDF and Word documents are allowed."})
    
    return {"success": True, "message": "Resume uploaded successfully.", "resume_path": file.filename}


# ==========================================
# MENTOR API ENDPOINTS
# ==========================================

class MentorNoteRequest(BaseModel):
    student_id: str
    content: str

class MentorNoteUpdateRequest(BaseModel):
    content: str

@app.get("/api/mentor/demo/mentees")
async def get_mentor_demo_data():
    """Retrieve mentor's assigned mentees, placed list, interventions, and metrics dynamically from SQLite DB."""
    data = db.get_mentor_dashboard_data("mentor@gmail.com")
    return {
        "success": True,
        **data
    }

@app.get("/api/mentor/notes")
async def get_notes(student_id: str):
    notes = db.get_mentor_notes("demo-mentor", student_id)
    return {"success": True, "notes": notes}

@app.post("/api/mentor/notes")
async def create_note(note_req: MentorNoteRequest):
    note = db.create_mentor_note("demo-mentor", note_req.student_id, note_req.content)
    return {"success": True, "note": note}

@app.put("/api/mentor/notes/{note_id}")
async def update_note(note_id: str, note_req: MentorNoteUpdateRequest):
    note = db.update_mentor_note(note_id, note_req.content)
    if not note:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"success": False, "message": "Note not found"})
    return {"success": True, "note": note}

@app.delete("/api/mentor/notes/{note_id}")
async def delete_note(note_id: str):
    db.delete_mentor_note(note_id)
    return {"success": True, "message": "Note deleted successfully"}


# ==========================================
# DEPARTMENT API ENDPOINTS
# ==========================================

@app.get("/api/department/dashboard")
async def get_department_dashboard(dept: str = "CSE"):
    """Retrieve full department overview: students, mentors, placed stats, interventions, and metrics."""
    data = db.get_department_dashboard_data(dept)
    return {
        "success": True,
        **data
    }


# Serve static frontend files
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "public")
if os.path.exists(PUBLIC_DIR):
    app.mount("/static", StaticFiles(directory=PUBLIC_DIR), name="static")

@app.get("/")
async def serve_index():
    index_path = os.path.join(PUBLIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Placement Tracking API is running."}

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
