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
import email_service
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

    user = db.get_user_by_gmail(gmail)

    if not user:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"success": False, "message": "Invalid Gmail or password"}
        )

    # INVITED accounts cannot login
    access_status = user.get("access_status") or ("ACTIVE" if user.get("is_active", True) else "REVOKED")
    if access_status == "INVITED":
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"success": False, "message": "Account activation is required. Please check your email for the activation link."}
        )

    # REVOKED accounts cannot login
    if access_status == "REVOKED" or not user.get("is_active", True):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"success": False, "message": "Your account access has been revoked. Please contact the coordinator."}
        )

    # Verify password (supports both hashed and legacy plaintext)
    if not db.verify_password(password, user["password"]):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"success": False, "message": "Invalid Gmail or password"}
        )

    # Migrate legacy plaintext password to bcrypt on successful login
    if not db.is_hashed(user["password"]):
        db.migrate_legacy_password(user["uuid"], password)

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
    default_role: str = Form("Student"),
    x_user_id: str = Header(None)
):
    actor = None
    if x_user_id:
        actor = _require_coordinator(x_user_id)

    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        return JSONResponse(status_code=400, content={"success": False, "message": "File size exceeds maximum allowed 10MB limit.", "detail": "File size exceeds limit."})

    try:
        records, skipped_count = bulk_parser.parse_user_access_records(content, file.filename, default_role=default_role)
    except ValueError as e:
        db.record_upload_log("User Access", file.filename, 0, 0, 0, status=f"FAILED: {str(e)}")
        return JSONResponse(status_code=400, content={"success": False, "message": str(e), "detail": str(e)})

    invited_count = 0
    updated_count = 0
    skipped_revoked = 0
    skipped_invited = 0
    email_sent_count = 0
    email_failed_count = 0
    processed_users = []

    for item in records:
        res = db.upsert_user_account(
            email=item["email"],
            role=item["role"],
            password=item.get("password"),
            actor_uuid=actor["uuid"] if actor else None,
            actor_gmail=actor["gmail"] if actor else None
        )
        if res["action"] == "Invited":
            invited_count += 1
            activation_token = res.get("activation_token")
            if activation_token:
                activation_url = f"{email_service.APP_BASE_URL}/#/activate/{activation_token}"
                email_result = email_service.send_invitation_email(item["email"], item["role"], activation_url)
                if email_result.get("sent"):
                    email_sent_count += 1
                else:
                    email_failed_count += 1
                    res["dev_activation_url"] = activation_url
                res.pop("activation_token", None)
        elif res["action"] == "Skipped (Revoked)":
            skipped_revoked += 1
        elif res["action"] == "Skipped (Invited)":
            skipped_invited += 1
        else:
            updated_count += 1
        processed_users.append(res)

    total_skipped = skipped_count + skipped_revoked + skipped_invited

    db.record_upload_log(
        upload_type="User Access Onboarding",
        filename=file.filename,
        total_rows=len(records) + skipped_count,
        processed_count=len(processed_users),
        skipped_count=total_skipped,
        status="SUCCESS"
    )

    return JSONResponse(status_code=status.HTTP_200_OK, content={
        "success": True,
        "message": f"Processed {len(processed_users)} accounts ({invited_count} invited, {updated_count} updated, {skipped_revoked} skipped-revoked, {skipped_invited} skipped-invited).",
        "total_rows": len(records) + skipped_count,
        "total_processed": len(processed_users),
        "created_count": invited_count,
        "invited_count": invited_count,
        "updated_count": updated_count,
        "skipped_count": total_skipped,
        "skipped_revoked": skipped_revoked,
        "skipped_invited": skipped_invited,
        "email_sent": email_sent_count,
        "email_failed": email_failed_count,
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

def _require_coordinator(x_user_id: str = None):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Authentication required (X-User-Id header missing)")
    actor = db.get_user_by_id(x_user_id)
    if not actor:
        raise HTTPException(status_code=401, detail="Unknown user")
    if actor["role"].strip().lower() not in ("coordinator", "admin"):
        raise HTTPException(status_code=403, detail="Only Coordinators can perform this action")
    access_status = actor.get("access_status") or ("ACTIVE" if actor.get("is_active", True) else "REVOKED")
    if access_status == "INVITED":
        raise HTTPException(status_code=403, detail="Account activation is required")
    if access_status == "REVOKED" or not actor.get("is_active", True):
        raise HTTPException(status_code=403, detail="Your account has been revoked")
    return actor


@app.post("/api/users/grant-single-access")
async def grant_single_access(req: GrantSingleAccessRequest, x_user_id: str = Header(None)):
    gmail = req.gmail.strip().lower()
    if not gmail or "@" not in gmail:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": "Please enter a valid Gmail address."}
        )

    actor = None
    if x_user_id:
        actor = _require_coordinator(x_user_id)

    result = db.grant_single_user_access(
        gmail=gmail, role=req.role,
        actor_uuid=actor["uuid"] if actor else None,
        actor_gmail=actor["gmail"] if actor else None
    )

    access_status = result.get("access_status", "")

    if access_status == "REVOKED":
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "success": False,
                "message": f"Account {gmail} is revoked. Use 'Reactivate' to restore access.",
                "user": {"uuid": result["uuid"], "gmail": result["gmail"], "role": result["role"], "is_active": False, "access_status": "REVOKED"}
            }
        )

    if result.get("action") == "Already Invited - use resend":
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "success": False,
                "message": f"Account {gmail} is already invited but not yet activated. Use 'Resend Invitation'.",
                "user": {"uuid": result["uuid"], "gmail": result["gmail"], "role": result["role"], "is_active": 0, "access_status": "INVITED"}
            }
        )

    # For newly invited users, attempt to send email
    email_result = {"sent": False, "delivery_mode": "none"}
    activation_token = result.get("activation_token")
    if activation_token:
        activation_url = f"{email_service.APP_BASE_URL}/#/activate/{activation_token}"
        email_result = email_service.send_invitation_email(gmail, result["role"], activation_url)

    safe_result = {k: v for k, v in result.items() if k not in ("password", "activation_token")}

    if result.get("action") == "Invited":
        email_sent = email_result.get("sent", False)
        delivery_mode = email_result.get("delivery_mode", "none")
        if email_sent:
            msg = f"Invitation email sent to {gmail} ({result['role']})."
        elif delivery_mode == "development":
            msg = f"Invitation created for {gmail} ({result['role']}), but email delivery is not configured."
        else:
            msg = f"Invitation created for {gmail} ({result['role']}), but the email could not be delivered."
    else:
        msg = f"Updated {result['role']} access for {gmail}."

    resp = {
        "success": True,
        "message": msg,
        "email_sent": email_result.get("sent", False),
        "delivery_mode": email_result.get("delivery_mode", "none"),
        "user": safe_result,
    }

    if activation_token and not email_result.get("sent"):
        dev_activation_url = f"{email_service.APP_BASE_URL}/#/activate/{activation_token}"
        resp["dev_activation_url"] = dev_activation_url

    return JSONResponse(status_code=status.HTTP_200_OK, content=resp)


# ==============================================================
# USER ACCESS MANAGEMENT ENDPOINTS
# ==============================================================

class RevokeRequest(BaseModel):
    gmail: str

class ReactivateRequest(BaseModel):
    gmail: str

class RoleUpdateRequest(BaseModel):
    gmail: str
    new_role: str


@app.get("/api/users/managed")
async def list_managed_users(x_user_id: str = Header(None)):
    actor = _require_coordinator(x_user_id)
    users = db.get_all_users()
    return {"success": True, "users": users, "count": len(users)}


@app.patch("/api/users/revoke")
async def revoke_user_access(req: RevokeRequest, x_user_id: str = Header(None)):
    actor = _require_coordinator(x_user_id)
    gmail = req.gmail.strip().lower()
    if not gmail or "@" not in gmail:
        raise HTTPException(status_code=400, detail="Invalid email address")

    if gmail == actor["gmail"].lower():
        raise HTTPException(status_code=400, detail="You cannot revoke your own access")

    user, result = db.revoke_user_access(gmail, actor_uuid=actor["uuid"], actor_gmail=actor["gmail"])
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if result == "already_revoked":
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"success": True, "message": f"Access for {gmail} is already revoked.", "user": {"uuid": user["uuid"], "gmail": user["gmail"], "role": user["role"], "is_active": 0}}
        )
    return {"success": True, "message": f"Access revoked for {gmail}.", "user": {"uuid": user["uuid"], "gmail": user["gmail"], "role": user["role"], "is_active": 0}}


@app.patch("/api/users/reactivate")
async def reactivate_user_access(req: ReactivateRequest, x_user_id: str = Header(None)):
    actor = _require_coordinator(x_user_id)
    gmail = req.gmail.strip().lower()
    if not gmail or "@" not in gmail:
        raise HTTPException(status_code=400, detail="Invalid email address")

    user, result = db.reactivate_user_access(gmail, actor_uuid=actor["uuid"], actor_gmail=actor["gmail"])
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if result == "already_active":
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"success": True, "message": f"Access for {gmail} is already active.", "user": {"uuid": user["uuid"], "gmail": user["gmail"], "role": user["role"], "is_active": 1, "access_status": "ACTIVE"}}
        )
    if result == "invited_not_activated":
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": f"Account {gmail} is INVITED but not yet activated. Use 'Resend Invitation' instead.", "user": {"uuid": user["uuid"], "gmail": user["gmail"], "role": user["role"], "is_active": 0, "access_status": "INVITED"}}
        )
    return {"success": True, "message": f"Access reactivated for {gmail}.", "user": {"uuid": user["uuid"], "gmail": user["gmail"], "role": user["role"], "is_active": 1, "access_status": "ACTIVE"}}


@app.patch("/api/users/update-role")
async def update_user_role(req: RoleUpdateRequest, x_user_id: str = Header(None)):
    actor = _require_coordinator(x_user_id)
    gmail = req.gmail.strip().lower()
    if not gmail or "@" not in gmail:
        raise HTTPException(status_code=400, detail="Invalid email address")

    normalized = db.normalize_role(req.new_role)
    if not normalized or normalized not in db.VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(sorted(db.VALID_ROLES))}")

    user, result = db.update_user_role(gmail, normalized,
                                        actor_uuid=actor["uuid"], actor_gmail=actor["gmail"])
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if result == "same_role":
        return {"success": True, "message": f"User {gmail} already has role {normalized}.", "user": {"uuid": user["uuid"], "gmail": user["gmail"], "role": user["role"], "is_active": user.get("is_active", 1)}}

    return {"success": True, "message": f"Role for {gmail} updated to {normalized}.", "user": {"uuid": user["uuid"], "gmail": user["gmail"], "role": user["role"], "is_active": user.get("is_active", 1)}}


@app.get("/api/users/access-history")
async def get_access_history(gmail: str = None, x_user_id: str = Header(None)):
    actor = _require_coordinator(x_user_id)
    history = db.get_access_history(user_gmail=gmail)
    return {"success": True, "history": history, "count": len(history)}


# ==============================================================
# ACTIVATION / PASSWORD RESET / INVITATION ENDPOINTS
# ==============================================================

class ActivateAccountRequest(BaseModel):
    token: str
    password: str

class ForgotPasswordRequest(BaseModel):
    gmail: str

class ResetPasswordRequest(BaseModel):
    token: str
    password: str

class ResendInvitationRequest(BaseModel):
    gmail: str


@app.get("/api/auth/validate-token")
async def validate_token(token: str, purpose: str = "ACTIVATION"):
    result = db.validate_auth_token(token, purpose)
    if not result["valid"]:
        return JSONResponse(status_code=400, content={"valid": False, "error": result["error"]})
    user = db.get_user_by_id(result["user_uuid"])
    return {"valid": True, "gmail": user["gmail"] if user else None, "role": user["role"] if user else None}


@app.post("/api/auth/activate")
async def activate_account(req: ActivateAccountRequest):
    success, result = db.activate_user(req.token, req.password)
    if not success:
        return JSONResponse(status_code=400, content={"success": False, "message": result})
    return {"success": True, "message": "Account activated successfully. You can now log in.", "user": result}


@app.post("/api/auth/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    gmail = req.gmail.strip().lower()
    raw_token, user = db.request_password_reset(gmail)

    # Generic response regardless of whether user exists
    response = {"success": True, "message": "If an account exists for this email, a password reset link has been generated."}

    if raw_token and user:
        reset_url = f"{email_service.APP_BASE_URL}/#/reset-password/{raw_token}"
        email_result = email_service.send_password_reset_email(gmail, reset_url)
        response["email_sent"] = email_result.get("sent", False)
        response["delivery_mode"] = email_result.get("delivery_mode", "none")
        if not email_result.get("sent"):
            response["dev_reset_url"] = reset_url

    return response


@app.post("/api/auth/reset-password")
async def reset_password_endpoint(req: ResetPasswordRequest):
    success, message = db.reset_password(req.token, req.password)
    if not success:
        return JSONResponse(status_code=400, content={"success": False, "message": message})
    return {"success": True, "message": message}


@app.post("/api/users/resend-invitation")
async def resend_invitation(req: ResendInvitationRequest, x_user_id: str = Header(None)):
    actor = _require_coordinator(x_user_id)
    gmail = req.gmail.strip().lower()
    if not gmail or "@" not in gmail:
        raise HTTPException(status_code=400, detail="Invalid email address")

    user, result = db.resend_invitation(gmail, actor_uuid=actor["uuid"], actor_gmail=actor["gmail"])
    if user is None:
        raise HTTPException(status_code=400, detail=result)

    raw_token = result
    activation_url = f"{email_service.APP_BASE_URL}/#/activate/{raw_token}"
    email_result = email_service.send_invitation_email(gmail, user["role"], activation_url)

    email_sent = email_result.get("sent", False)
    delivery_mode = email_result.get("delivery_mode", "none")
    if email_sent:
        msg = f"Invitation email resent to {gmail}."
    elif delivery_mode == "development":
        msg = f"New invitation created for {gmail}, but email delivery is not configured."
    else:
        msg = f"New invitation created for {gmail}, but the email could not be delivered."

    resp = {
        "success": True,
        "message": msg,
        "email_sent": email_sent,
        "delivery_mode": delivery_mode,
    }
    if not email_sent:
        resp["dev_activation_url"] = activation_url

    return resp


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
    access_status = user.get("access_status") or ("ACTIVE" if user.get("is_active", True) else "REVOKED")
    if access_status == "INVITED":
        raise HTTPException(status_code=403, detail="Account activation is required")
    if access_status == "REVOKED" or not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Your account access has been revoked")
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
