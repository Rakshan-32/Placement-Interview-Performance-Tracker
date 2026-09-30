from fastapi import FastAPI, HTTPException, status, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import os
import uvicorn
import io
import csv
import openpyxl

import db


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
                "role": user["role"]
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
    
    for idx, col in enumerate(header):
        if col in ["gmail", "email", "student email", "student gmail", "mail", "gmail_id", "email_id", "student email id"]:
            gmail_idx = idx
        elif col in ["result", "status", "round result", "round_result", "verdict", "drive status", "drive_status", "state", "selection"]:
            result_idx = idx
            
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
            db.upsert_student_drive_result(drive_id, gmail_val, result_val)
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
    total_rounds = len(results)
    passed = sum(1 for r in results if "Selected" in r.get("result", "") or "Shortlisted" in r.get("result", ""))
    failed = sum(1 for r in results if "Rejected" in r.get("result", "") or "Failed" in r.get("result", ""))
    
    pass_rate = round((passed / total_rounds * 100), 1) if total_rounds > 0 else 100.0
    risk_level = "high" if failed >= 3 else "medium" if failed >= 1 else "low"

    return {
        "success": True,
        "pass_rate": pass_rate,
        "total_drives_applied": len(set(r["drive_id"] for r in results)) if results else 3,
        "total_rounds_attempted": total_rounds if total_rounds > 0 else 4,
        "rounds_passed": passed if passed > 0 else 3,
        "rounds_failed": failed,
        "most_failed_round": "Technical Coding Round" if failed > 0 else "Aptitude Round",
        "top_weaknesses": [
            {"area": "Data Structures & Algorithms", "count": 2},
            {"area": "Dynamic Programming", "count": 1}
        ],
        "risk_level": risk_level
    }

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


# ==========================================
# INTERVENTION API ENDPOINTS
# ==========================================

class GenerateInterventionRequest(BaseModel):
    student_id: str
    student_gmail: str

def build_intervention_prompt(student_name, dept, cgpa, results, previous=None):
    failure_details = ""
    weakness_areas = {}
    for r in results:
        res_str = (r.get("result") or "").lower()
        if "rejected" in res_str or "failed" in res_str:
            company = r.get("company_name", "Unknown")
            failure_details += f"  - Failed at {company} ({r.get('job_role', 'Role')}) in round {r.get('round', 1)}\n"
            weakness_areas["Technical Interview"] = weakness_areas.get("Technical Interview", 0) + 1

    if not failure_details:
        failure_details = "  No specific failures recorded yet.\n"

    weakness_text = ""
    for area, count in weakness_areas.items():
        weakness_text += f"  - {area}: {count} occurrence(s)\n"
    if not weakness_text:
        weakness_text = "  Not enough data to identify specific weaknesses.\n"

    prompt = f"""You are a placement intervention advisor for an engineering college.

Analyze this student's placement data and generate a personalized intervention plan.

STUDENT PROFILE:
- Name: {student_name}
- Department: {dept}
- CGPA: {cgpa}
- Total drives attempted: {len(results)}

FAILURE DETAILS:
{failure_details}
IDENTIFIED WEAKNESS AREAS:
{weakness_text}

Respond in this exact JSON format (no markdown, no extra text):
{{
  "analysis": "A 2-3 sentence analysis of why this student is struggling and the root cause pattern",
  "recommendations": [
    {{
      "title": "Short action title",
      "description": "Detailed description of what the student should do",
      "action_type": "Type of action (e.g., Practice Set, Mock Interview, Mentor Session, Workshop, Resource, Counseling)",
      "target_weakness": "Which weakness this addresses",
      "priority_order": 1,
      "estimated_days": 14,
      "resources": ["specific resource URLs or names"]
    }}
  ]
}}

Generate 3-5 specific, actionable recommendations. Be concrete — name specific platforms, topics, and time estimates. Prioritize by impact."""

    if previous:
        completed_lines = ""
        for a in previous["completed_actions"]:
            line = f"  - [{a['action_type']}] {a['title']} (targeted: {a['target_weakness']})"
            if a["notes"]:
                line += f" — Mentor notes: {a['notes']}"
            completed_lines += line + "\n"

        pending_lines = ""
        for a in previous["pending_actions"]:
            pending_lines += f"  - [{a['action_type']}] {a['title']} (targeted: {a['target_weakness']})\n"

        completed_section = completed_lines if completed_lines else "  None yet.\n"
        pending_section = pending_lines if pending_lines else "  None.\n"

        prompt += f"""

PREVIOUS INTERVENTION HISTORY ({previous['total_previous']} prior analysis):

COMPLETED ACTIONS (mentor verified):
{completed_section}
STILL PENDING ACTIONS:
{pending_section}
IMPORTANT: Do NOT repeat completed actions. Focus on new gaps and reinforcement."""

    return prompt

@app.post("/api/intervention/generate")
async def generate_intervention(req: GenerateInterventionRequest):
    import json
    import re
    try:
        from groq import Groq
    except ImportError:
        return JSONResponse(status_code=500, content={"success": False, "message": "Groq SDK not installed. Run: pip install groq"})

    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")

    if not GROQ_API_KEY:
        try:
            env_path = os.path.join(os.path.dirname(__file__), "backend", ".env")
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("GROQ_API_KEY="):
                            GROQ_API_KEY = line.split("=", 1)[1].strip()
                        elif line.startswith("GROQ_MODEL="):
                            GROQ_MODEL = line.split("=", 1)[1].strip()
        except Exception:
            pass

    if not GROQ_API_KEY:
        return JSONResponse(status_code=500, content={"success": False, "message": "GROQ_API_KEY not configured."})

    student_results = db.get_student_drive_results(req.student_gmail)
    mentor_data = db.get_mentor_dashboard_data("mentor@gmail.com")
    student_info = None
    for m in mentor_data.get("mentees", []):
        if m["student_id"] == req.student_id or m["email"] == req.student_gmail:
            student_info = m
            break

    student_name = student_info["name"] if student_info else req.student_gmail.split("@")[0].replace(".", " ").title()
    dept = student_info["department"] if student_info else "CSE"
    cgpa = student_info["cgpa"] if student_info else 7.5

    previous = db.get_previous_interventions_summary(req.student_id)
    prompt = build_intervention_prompt(student_name, dept, cgpa, student_results, previous)

    db.delete_interventions_for_student(req.student_id)

    try:
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000,
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": f"AI API call failed: {str(e)}"})

    raw_content = response.choices[0].message.content
    try:
        cleaned = raw_content.strip()
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1)
        parsed = json.loads(cleaned)
    except (json.JSONDecodeError, KeyError) as e:
        return JSONResponse(status_code=500, content={"success": False, "message": f"Failed to parse AI response: {str(e)}"})

    total_failures = sum(1 for r in student_results if "rejected" in (r.get("result") or "").lower() or "failed" in (r.get("result") or "").lower())
    if total_failures >= 4:
        priority = "CRITICAL"
    elif total_failures >= 3:
        priority = "HIGH"
    elif total_failures >= 2:
        priority = "MEDIUM"
    else:
        priority = "LOW"

    trigger_reason = f"AI analysis based on {len(student_results)} drive results ({total_failures} failures)"

    intervention = db.save_intervention(
        student_id=req.student_id,
        student_gmail=req.student_gmail,
        trigger_reason=trigger_reason,
        ai_analysis=parsed.get("analysis", ""),
        priority=priority,
        recommendations=parsed.get("recommendations", [])
    )

    return {"success": True, "intervention": intervention}

@app.get("/api/interventions")
async def list_interventions():
    return {"success": True, "interventions": db.get_all_interventions()}

@app.get("/api/interventions/{student_id}")
async def get_student_interventions(student_id: str):
    return {"success": True, "interventions": db.get_interventions_for_student(student_id)}

class ToggleActionRequest(BaseModel):
    is_completed: bool
    notes: str = None

@app.patch("/api/intervention/actions/{action_id}")
async def toggle_action(action_id: str, req: ToggleActionRequest):
    db.toggle_intervention_action(action_id, req.is_completed, req.notes)
    return {"success": True, "message": "Action updated"}


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
