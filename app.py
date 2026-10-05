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


# Initialize database on startup
db.init_db()

app = FastAPI(
    title="Placement Tracking Authentication API",
    description="Gmail & Password Authentication against SQLite 'authenticate' table"
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
    gmail: str = Field(..., json_schema_extra={"example": "[EMAIL_ADDRESS]"})
    password: str = Field(..., json_schema_extra={"example": "admin123"})

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
    
    # Check if user exists and comparing stored password with entered password
    if not user or user["password"] != password:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "success": False,
                "message": "Invalid Gmail or password"
            }
        )
    
    # Passwords match -> User successfully authenticated
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
    return {"success": True, "users": users}

import io
import csv
import openpyxl

@app.get("/api/drives")
async def list_drives():
    """Endpoint to retrieve all placement drives from SQLite."""
    drives = db.get_all_drives()
    # Attach result count to each drive for convenience
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

from fastapi import UploadFile, File

@app.get("/api/drives/{drive_id}/results")
async def get_drive_results(drive_id: str):
    """Retrieve all student evaluation results for a specific drive."""
    results = db.get_drive_results(drive_id)
    return {"success": True, "results": results, "count": len(results)}

@app.post("/api/drives/{drive_id}/upload-results")
async def upload_drive_results(drive_id: str, file: UploadFile = File(...)):
    """
    Upload Excel (.xlsx) or CSV file containing candidate results.
    Extracts 'gmail' and 'result' columns and updates student statuses for this company drive.
    """
    filename = file.filename.lower()
    content = await file.read()
    
    rows = []
    
    if filename.endswith(".xlsx") or filename.endswith(".xls"):
        try:
            wb = openpyxl.load_workbook(filename=io.BytesIO(content), data_only=True)
            sheet = wb.active
            for row in sheet.iter_rows(values_only=True):
                if any(cell is not None for cell in row):
                    rows.append([str(cell) if cell is not None else "" for cell in row])
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "message": f"Error parsing Excel file: {str(e)}"}
            )
    elif filename.endswith(".csv"):
        try:
            decoded = content.decode("utf-8", errors="ignore")
            reader = csv.reader(io.StringIO(decoded))
            for r in reader:
                if any(c.strip() for c in r):
                    rows.append(r)
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "message": f"Error parsing CSV file: {str(e)}"}
            )
    else:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": "Unsupported file format. Please upload an .xlsx or .csv file."}
        )
        
    if not rows:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": "Uploaded file is empty."}
        )

    # Search header row for 'gmail' and 'result' columns
    header = [str(cell).strip().lower() for cell in rows[0]]
    
    gmail_idx = -1
    result_idx = -1
    round_idx = -1
    score_idx = -1
    max_score_idx = -1
    feedback_idx = -1
    weakness_idx = -1
    rejection_idx = -1
    attempt_date_idx = -1
    
    for idx, col in enumerate(header):
        if col in ["gmail", "email", "student email", "student gmail", "mail", "gmail_id", "email_id", "student email id"]:
            gmail_idx = idx
        elif col in ["result", "status", "round result", "round_result", "verdict", "drive status", "drive_status", "state", "selection"]:
            result_idx = idx
        elif col in ["round", "round number", "round_no", "round no"]:
            round_idx = idx
        elif col in ["score", "marks", "obtained marks"]:
            score_idx = idx
        elif col in ["max score", "maximum score", "total marks"]:
            max_score_idx = idx
        elif col in ["feedback", "remarks", "comments"]:
            feedback_idx = idx
        elif col in ["weakness", "weakness area", "weakness_area", "skill gap"]:
            weakness_idx = idx
        elif col in ["rejection reason", "rejection_reason", "failure reason"]:
            rejection_idx = idx
        elif col in ["attempt date", "attempt_date", "evaluation date", "date"]:
            attempt_date_idx = idx
            
    if gmail_idx == -1:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": f"Could not find a 'gmail' or 'email' column header in the spreadsheet. Found columns: {', '.join(header)}"}
        )
        
    updated_count = 0
    skipped_count = 0
    processed_records = []

    # Process data rows
    for row in rows[1:]:
        if len(row) <= gmail_idx:
            skipped_count += 1
            continue
            
        gmail_val = str(row[gmail_idx]).strip()
        if not gmail_val or "@" not in gmail_val:
            skipped_count += 1
            continue

        if result_idx != -1 and len(row) > result_idx:
            result_val = str(row[result_idx]).strip()
        else:
            result_val = None

        if result_val:
            def optional_float(index):
                if index == -1 or len(row) <= index or not str(row[index]).strip():
                    return None
                try:
                    return float(row[index])
                except (TypeError, ValueError):
                    return None

            round_value = None
            if round_idx != -1 and len(row) > round_idx:
                try:
                    round_value = int(float(row[round_idx]))
                except (TypeError, ValueError):
                    round_value = None
            db.upsert_student_drive_result(
                drive_id,
                gmail_val,
                result_val,
                round_number=round_value,
                score=optional_float(score_idx),
                max_score=optional_float(max_score_idx),
                feedback=str(row[feedback_idx]).strip() if feedback_idx != -1 and len(row) > feedback_idx else None,
                weakness_area=str(row[weakness_idx]).strip() if weakness_idx != -1 and len(row) > weakness_idx else None,
                rejection_reason=str(row[rejection_idx]).strip() if rejection_idx != -1 and len(row) > rejection_idx else None,
                attempt_date=str(row[attempt_date_idx]).strip() if attempt_date_idx != -1 and len(row) > attempt_date_idx else None,
            )
            updated_count += 1
            processed_records.append({"gmail": gmail_val, "result": result_val})
        else:
            # Shortlist upload: increment round for student
            inc_res = db.increment_student_drive_round(drive_id, gmail_val)
            updated_count += 1
            processed_records.append(inc_res)


    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "message": f"Successfully processed {updated_count} student result records.",
            "total_rows": len(rows) - 1,
            "updated_count": updated_count,
            "skipped_count": skipped_count,
            "processed_records": processed_records
        }
    )

@app.post("/api/users/upload-access")
async def upload_user_access(
    file: UploadFile = File(...),
    default_role: str = Form("Student")
):
    """
    Upload Excel (.xlsx) or CSV file containing user email addresses.
    Grants access and creates/updates account roles in the database.
    """
    filename = file.filename.lower()
    content = await file.read()
    
    rows = []
    
    if filename.endswith(".xlsx") or filename.endswith(".xls"):
        try:
            wb = openpyxl.load_workbook(filename=io.BytesIO(content), data_only=True)
            sheet = wb.active
            for row in sheet.iter_rows(values_only=True):
                if any(cell is not None for cell in row):
                    rows.append([str(cell) if cell is not None else "" for cell in row])
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "message": f"Error parsing Excel file: {str(e)}"}
            )
    elif filename.endswith(".csv"):
        try:
            decoded = content.decode("utf-8", errors="ignore")
            reader = csv.reader(io.StringIO(decoded))
            for r in reader:
                if any(c.strip() for c in r):
                    rows.append(r)
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "message": f"Error parsing CSV file: {str(e)}"}
            )
    else:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": "Unsupported file format. Please upload an .xlsx or .csv file."}
        )
        
    if not rows:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": "Uploaded file is empty."}
        )

    header = [str(cell).strip().lower() for cell in rows[0]]
    
    gmail_idx = -1
    role_idx = -1
    password_idx = -1
    
    for idx, col in enumerate(header):
        if col in ["gmail", "email", "student email", "user email", "mail", "gmail_id", "email_id", "student email id"]:
            gmail_idx = idx
        elif col in ["role", "user role", "access role", "account role", "type"]:
            role_idx = idx
        elif col in ["password", "pwd", "pass", "user password", "account password"]:
            password_idx = idx

    if gmail_idx == -1:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": f"Could not find a 'gmail' or 'email' column header in the spreadsheet. Found columns: {', '.join(header)}"}
        )

    users_to_process = []
    skipped_count = 0

    for row in rows[1:]:
        if len(row) <= gmail_idx:
            skipped_count += 1
            continue
            
        gmail_val = str(row[gmail_idx]).strip()
        role_val = str(row[role_idx]).strip() if (role_idx != -1 and len(row) > role_idx and str(row[role_idx]).strip()) else default_role
        password_val = str(row[password_idx]).strip() if (password_idx != -1 and len(row) > password_idx and str(row[password_idx]).strip()) else None

        if "@" in gmail_val:
            item = {"gmail": gmail_val, "role": role_val}
            if password_val:
                item["password"] = password_val
            users_to_process.append(item)
        else:
            skipped_count += 1


    if not users_to_process:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": "No valid Gmail addresses found in the spreadsheet."}
        )

    summary = db.bulk_grant_user_access(users_to_process)
    summary["skipped_count"] = skipped_count
    summary["total_rows"] = len(rows) - 1

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "message": f"Successfully granted access to {summary['total_processed']} users ({summary['created_count']} created, {summary['updated_count']} updated).",
            **summary
        }
    )

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


# ==========================================
# STUDENT API ENDPOINTS
# ==========================================

class StudentApplyRequest(BaseModel):
    gmail: str
    drive_id: str

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
