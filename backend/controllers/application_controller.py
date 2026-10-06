import os

import db
import intervention_service
import bulk_upload_module.exporter as bulk_exporter
from bulk_upload_module.config import TEMPLATES_DIR
from fastapi import File, Form, Header, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel


class StudentApplyRequest(BaseModel):
    gmail: str
    drive_id: str


class InterventionGenerateRequest(BaseModel):
    student_id: str = None
    gmail: str = None


class InterventionStatusRequest(BaseModel):
    status: str


class InterventionActionRequest(BaseModel):
    completed: bool = None
    notes: str = None


class MentorNoteRequest(BaseModel):
    student_id: str
    content: str


class MentorNoteUpdateRequest(BaseModel):
    content: str


def list_sample_templates():
    return {"success": True, "templates": [
        {"name": "sample_drive_shortlist", "title": "Drive Shortlist Template (Emails Only)", "description": "Upload candidate emails to automatically advance them to the next interview round.", "formats": ["sample_drive_shortlist.xlsx", "sample_drive_shortlist.csv"], "required_columns": ["Student Gmail / Email"], "optional_columns": ["Student Name", "Branch"], "mode": "Shortlist Mode (Auto-increments round by +1)"},
        {"name": "sample_drive_results", "title": "Drive Results / Verdicts Template", "description": "Upload candidate evaluations with explicit statuses (Selected, Rejected, On Hold) and scores.", "formats": ["sample_drive_results.xlsx", "sample_drive_results.csv"], "required_columns": ["Student Gmail / Email", "Result Status / Verdict"], "optional_columns": ["Round", "Score", "Student Name"], "mode": "Verdict Mode (Sets exact status)"},
        {"name": "sample_user_access", "title": "User Accounts & Role Provisioning Template", "description": "Bulk create or update accounts for Students, Mentors, Coordinators, and Recruiters.", "formats": ["sample_user_access.xlsx", "sample_user_access.csv"], "required_columns": ["User Email"], "optional_columns": ["Role (Student, Mentor, etc.)", "Password"], "mode": "Role Access Mode"},
        {"name": "sample_student_roster", "title": "Student Academic Profiles Template", "description": "Bulk import academic records, CGPA, 10th/12th percentages, and technical skills.", "formats": ["sample_student_roster.xlsx", "sample_student_roster.csv"], "required_columns": ["Register Number", "Full Name", "Student Email", "Department", "CGPA"], "optional_columns": ["10th Percentage", "12th Percentage", "Technical Skills"], "mode": "Academic Roster Mode"},
        {"name": "sample_company_drives", "title": "Company Placement Drives Template", "description": "Bulk schedule on-campus placement drives with company type, CTC LPA, eligibility criteria, and rounds.", "formats": ["sample_company_drives.xlsx", "sample_company_drives.csv"], "required_columns": ["Company Name", "Job Role", "CTC LPA"], "optional_columns": ["Company Type", "Required CGPA", "Allowed Branches", "Total Rounds", "Location", "Drive Date", "Status"], "mode": "Company Drive Scheduling Mode"},
    ]}


def download_template(filename: str):
    filepath = os.path.join(TEMPLATES_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Template file '{filename}' was not found. Call /api/templates to see available files.")
    mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if filename.endswith(".xlsx") else "text/csv"
    return FileResponse(filepath, media_type=mime_type, filename=filename)


def list_students():
    students = db.get_all_student_roster()
    return {"success": True, "count": len(students), "students": students}


def list_upload_logs():
    logs = db.get_upload_logs()
    return {"success": True, "count": len(logs), "logs": logs}


def export_company_drives(format: str = "xlsx"):
    return bulk_exporter.export_company_drives_data(db.get_all_drives(), format_type=format)


def export_drive_results(drive_id: str, format: str = "xlsx"):
    drive = db.get_drive(drive_id)
    if not drive:
        raise HTTPException(status_code=404, detail=f"Drive with ID '{drive_id}' was not found.")
    return bulk_exporter.export_drive_results_data(db.get_drive_results(drive_id), drive_info=drive, format_type=format)


def export_student_roster(format: str = "xlsx"):
    return bulk_exporter.export_student_roster_data(db.get_all_student_roster(), format_type=format)


def export_user_access(format: str = "xlsx"):
    return bulk_exporter.export_user_access_data(db.get_all_users(), format_type=format)


def get_student_profile(gmail: str):
    profile = db.get_student_profile_by_email(gmail)
    if not profile:
        email = gmail.strip().lower()
        profile = {"student_id": "demo-id", "register_number": "312321104012", "name": email.split("@")[0].replace(".", " ").title(), "email": email, "department": "CSE", "cgpa": 8.4, "tenth_percentage": 91.5, "twelfth_percentage": 88.0, "skills": "Python, Data Structures, React, SQL", "skills_list": ["Python", "Data Structures", "React", "SQL"]}
    return {"success": True, "profile": profile}


def get_student_results(gmail: str):
    return {"success": True, "results": db.get_student_drive_results(gmail)}


def get_student_applications(gmail: str):
    applications = [{"registration_id": item["id"], "drive_id": item["drive_id"], "company_name": item.get("company_name", "Drive"), "job_role": item.get("job_role", "Role"), "ctc_lpa": item.get("ctc_lpa", 10.0), "final_status": "REGISTERED" if "Shortlisted" in item.get("result", "") else item.get("result", "REGISTERED"), "registered_at": item.get("updated_at", "")} for item in db.get_student_drive_results(gmail)]
    return {"success": True, "applications": applications}


def apply_student_drive(request: StudentApplyRequest):
    return {"success": True, "message": "Successfully registered for drive", "registration": db.increment_student_drive_round(request.drive_id, request.gmail)}


def get_student_analysis(gmail: str):
    results = db.get_student_drive_results(gmail)
    patterns = intervention_service.analyse_student_patterns(results)
    failed_rounds = patterns["failed_by_round"]
    return {"success": True, "pass_rate": patterns["pass_rate"], "total_drives_applied": len({item["drive_id"] for item in results}), "total_rounds_attempted": patterns["total_rounds"], "rounds_passed": patterns["passed_rounds"], "rounds_failed": patterns["failed_rounds"], "most_failed_round": max(failed_rounds, key=failed_rounds.get) if failed_rounds else None, "top_weaknesses": patterns["top_weaknesses"], "risk_level": patterns["risk_level"]}


def _requester(user_id, role, department):
    if not user_id:
        raise HTTPException(status_code=401, detail="X-User-Id is required")
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Unknown user")
    if role and role.strip().lower() != user["role"].strip().lower():
        raise HTTPException(status_code=403, detail="User role does not match the authenticated account")
    user["department"] = department or user.get("department") or "CSE"
    return user


def _scoped_student(user, student_id=None, gmail=None):
    students = db.get_students_for_scope(user["uuid"], user["role"], user.get("department"))
    for student in students:
        if (student_id and student["uuid"] == student_id) or (gmail and student["gmail"].lower() == gmail.strip().lower()):
            return student
    raise HTTPException(status_code=403, detail="You are not allowed to access this student")


def _visible_interventions(user):
    students = db.get_students_for_scope(user["uuid"], user["role"], user.get("department"))
    return db.get_interventions(student_gmails=[student["gmail"] for student in students])


def list_interventions(x_user_id: str = Header(None), x_user_role: str = Header(None), x_department: str = Header(None)):
    return {"success": True, "interventions": _visible_interventions(_requester(x_user_id, x_user_role, x_department))}


def list_intervention_students(x_user_id: str = Header(None), x_user_role: str = Header(None), x_department: str = Header(None)):
    user = _requester(x_user_id, x_user_role, x_department)
    students = db.get_students_for_scope(user["uuid"], user["role"], user.get("department"))
    grouped = {}
    for intervention in _visible_interventions(user):
        grouped.setdefault(intervention["student_gmail"].lower(), []).append(intervention)
    for student in students:
        student["interventions"] = grouped.get(student["gmail"].lower(), [])[:3]
        student["intervention_count"] = len(student["interventions"])
    return {"success": True, "students": students}


def get_student_interventions(student_id: str, x_user_id: str = Header(None), x_user_role: str = Header(None), x_department: str = Header(None)):
    user = _requester(x_user_id, x_user_role, x_department)
    student = _scoped_student(user, student_id=student_id)
    return {"success": True, "student": student, "interventions": db.get_interventions(student_gmail=student["gmail"]), "analysis": intervention_service.analyse_student_patterns(db.get_student_analysis_records(student["gmail"]))}


def generate_intervention(request: InterventionGenerateRequest, x_user_id: str = Header(None), x_user_role: str = Header(None), x_department: str = Header(None)):
    user = _requester(x_user_id, x_user_role, x_department)
    if user["role"].lower() == "student":
        raise HTTPException(status_code=403, detail="Students cannot generate interventions")
    if not request.student_id and not request.gmail:
        raise HTTPException(status_code=400, detail="student_id or gmail is required")
    student = _scoped_student(user, request.student_id, request.gmail)
    records = db.get_student_analysis_records(student["gmail"])
    patterns = intervention_service.analyse_student_patterns(records)
    previous = db.get_interventions(student_gmail=student["gmail"])
    actions = [action for item in previous for action in item.get("actions", [])]
    try:
        intervention, action_items = intervention_service.build_intervention(student, patterns, actions, user["uuid"])
        saved = db.save_intervention(intervention, action_items)
    except intervention_service.AgentRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc), headers={"Retry-After": str(exc.retry_after)}) from exc
    except intervention_service.AgentConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except intervention_service.AgentResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Intervention generation failed: {exc}") from exc
    return {"success": True, "intervention": saved, "analysis": patterns}


def generate_all_interventions(x_user_id: str = Header(None), x_user_role: str = Header(None), x_department: str = Header(None)):
    user = _requester(x_user_id, x_user_role, x_department)
    if user["role"].lower() == "student":
        raise HTTPException(status_code=403, detail="Students cannot generate interventions")
    generated, failures = [], []
    for student in db.get_students_for_scope(user["uuid"], user["role"], user.get("department")):
        try:
            records = db.get_student_analysis_records(student["gmail"])
            patterns = intervention_service.analyse_student_patterns(records)
            previous = db.get_interventions(student_gmail=student["gmail"])
            actions = [action for item in previous for action in item.get("actions", [])]
            intervention, action_items = intervention_service.build_intervention(student, patterns, actions, user["uuid"])
            generated.append(db.save_intervention(intervention, action_items))
        except Exception as exc:
            failures.append({"student_id": student["uuid"], "gmail": student["gmail"], "error": str(exc)})
    return {"success": not failures, "generated": generated, "failures": failures}


def change_intervention_status(intervention_id: str, request: InterventionStatusRequest, x_user_id: str = Header(None), x_user_role: str = Header(None), x_department: str = Header(None)):
    user = _requester(x_user_id, x_user_role, x_department)
    if user["role"].lower() == "student":
        raise HTTPException(status_code=403, detail="Students cannot update intervention status")
    new_status = request.status.strip().upper()
    if new_status not in {"OPEN", "IN_PROGRESS", "COMPLETED", "CANCELLED"}:
        raise HTTPException(status_code=400, detail="status must be one of ['CANCELLED', 'COMPLETED', 'IN_PROGRESS', 'OPEN']")
    if intervention_id not in {item["id"] for item in _visible_interventions(user)}:
        raise HTTPException(status_code=403, detail="You are not allowed to update this intervention")
    db.update_intervention_status(intervention_id, new_status)
    return {"success": True, "status": new_status}


def change_intervention_action(action_id: str, request: InterventionActionRequest, x_user_id: str = Header(None), x_user_role: str = Header(None), x_department: str = Header(None)):
    user = _requester(x_user_id, x_user_role, x_department)
    if user["role"].lower() == "student":
        raise HTTPException(status_code=403, detail="Students cannot update intervention actions")
    visible = {action["id"] for item in _visible_interventions(user) for action in item.get("actions", [])}
    if action_id not in visible:
        raise HTTPException(status_code=403, detail="You are not allowed to update this action")
    if not db.update_intervention_action(action_id, request.completed, request.notes):
        raise HTTPException(status_code=404, detail="Action not found")
    return {"success": True, "action_id": action_id}


def upload_student_resume(file: UploadFile = File(...), gmail: str = Form("student@gmail.com")):
    if not file.filename.lower().endswith((".pdf", ".doc", ".docx")):
        return JSONResponse(status_code=400, content={"success": False, "message": "Only PDF and Word documents are allowed."})
    return {"success": True, "message": "Resume uploaded successfully.", "resume_path": file.filename}


def get_mentor_demo_data():
    return {"success": True, **db.get_mentor_dashboard_data("mentor@gmail.com")}


def get_notes(student_id: str):
    return {"success": True, "notes": db.get_mentor_notes("demo-mentor", student_id)}


def create_note(request: MentorNoteRequest):
    return {"success": True, "note": db.create_mentor_note("demo-mentor", request.student_id, request.content)}


def update_note(note_id: str, request: MentorNoteUpdateRequest):
    note = db.update_mentor_note(note_id, request.content)
    if not note:
        return JSONResponse(status_code=404, content={"success": False, "message": "Note not found"})
    return {"success": True, "note": note}


def delete_note(note_id: str):
    db.delete_mentor_note(note_id)
    return {"success": True, "message": "Note deleted successfully"}


def get_department_dashboard(dept: str = "CSE"):
    return {"success": True, **db.get_department_dashboard_data(dept)}
