from fastapi import File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

import db
from backend.services import upload_service
from bulk_upload_module.config import MAX_FILE_SIZE_BYTES


async def upload_drive_shortlist(drive_id: str, file: UploadFile = File(...)):
    drive = db.get_drive(drive_id)
    if not drive:
        raise HTTPException(status_code=404, detail=f"Drive with ID '{drive_id}' was not found.")
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowed 10MB limit.")
    try:
        records, skipped_count, _ = upload_service.parse_drive(content, file.filename)
    except ValueError as exc:
        upload_service.record_failure("Drive Shortlist", file.filename, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    processed = [db.process_shortlist_record(drive_id, item["email"], base_round=drive.get("current_round", 1)) for item in records]
    db.record_upload_log(f"Drive Shortlist ({drive['company_name']})", file.filename, len(records) + skipped_count, len(processed), skipped_count)
    return {"success": True, "mode": "Shortlist Mode (Auto-promoted candidates to next round)", "drive_id": drive_id, "company_name": drive["company_name"], "total_rows": len(records) + skipped_count, "promoted_count": len(processed), "skipped_count": skipped_count, "records": processed}


async def upload_drive_results_endpoint(drive_id: str, file: UploadFile = File(...)):
    drive = db.get_drive(drive_id)
    if not drive:
        raise HTTPException(status_code=404, detail=f"Drive with ID '{drive_id}' was not found.")
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowed 10MB limit.")
    try:
        records, skipped_count, _ = upload_service.parse_drive(content, file.filename)
    except ValueError as exc:
        upload_service.record_failure("Drive Results", file.filename, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    processed = [db.process_verdict_record(drive_id, item["email"], item.get("verdict") or "Shortlisted", item.get("round"), item.get("score")) for item in records]
    db.record_upload_log(f"Drive Results ({drive['company_name']})", file.filename, len(records) + skipped_count, len(processed), skipped_count)
    return {"success": True, "mode": "Verdict Mode (Updated explicit status and scores)", "drive_id": drive_id, "company_name": drive["company_name"], "total_rows": len(records) + skipped_count, "updated_count": len(processed), "skipped_count": skipped_count, "records": processed}


async def upload_drive_results(drive_id: str, file: UploadFile = File(...)):
    drive = db.get_drive(drive_id)
    if not drive:
        return JSONResponse(status_code=404, content={"success": False, "message": f"Drive with ID '{drive_id}' was not found."})
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        return JSONResponse(status_code=400, content={"success": False, "message": "File size exceeds maximum allowed 10MB limit.", "detail": "File size exceeds limit."})
    try:
        records, skipped_count, verdict_mode = upload_service.parse_drive(content, file.filename)
    except ValueError as exc:
        upload_service.record_failure("Drive Upload", file.filename, exc)
        return JSONResponse(status_code=400, content={"success": False, "message": str(exc), "detail": str(exc)})
    processed = []
    for item in records:
        if verdict_mode and item.get("verdict"):
            processed.append(db.process_verdict_record(drive_id, item["email"], item["verdict"], item.get("round"), item.get("score"), item.get("max_score"), item.get("feedback"), item.get("weakness_area"), item.get("rejection_reason"), item.get("attempt_date")))
        else:
            processed.append(db.process_shortlist_record(drive_id, item["email"], base_round=drive.get("current_round", 1)))
    db.record_upload_log(f"Drive Candidate Upload ({drive_id})", file.filename, len(records) + skipped_count, len(processed), skipped_count)
    return {"success": True, "message": f"Successfully processed {len(processed)} student result records.", "total_rows": len(records) + skipped_count, "updated_count": len(processed), "skipped_count": skipped_count, "processed_records": processed}


async def upload_user_access(file: UploadFile = File(...), default_role: str = Form("Student")):
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        return JSONResponse(status_code=400, content={"success": False, "message": "File size exceeds maximum allowed 10MB limit.", "detail": "File size exceeds limit."})
    try:
        records, skipped_count = upload_service.parse_user_access(content, file.filename, default_role)
    except ValueError as exc:
        upload_service.record_failure("User Access", file.filename, exc)
        return JSONResponse(status_code=400, content={"success": False, "message": str(exc), "detail": str(exc)})
    processed = [db.upsert_user_account(item["email"], item["role"], item.get("password")) for item in records]
    created = sum(item["action"] == "Created" for item in processed)
    updated = len(processed) - created
    db.record_upload_log("User Access Onboarding", file.filename, len(records) + skipped_count, len(processed), skipped_count)
    return {"success": True, "message": f"Successfully granted access to {len(processed)} user accounts ({created} created, {updated} updated).", "total_rows": len(records) + skipped_count, "total_processed": len(processed), "created_count": created, "updated_count": updated, "skipped_count": skipped_count, "processed_users": processed, "users": processed}


async def upload_student_roster(file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowed 10MB limit.")
    try:
        records, skipped_count = upload_service.parse_student_roster(content, file.filename)
    except ValueError as exc:
        upload_service.record_failure("Student Roster", file.filename, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    processed = [db.upsert_student_roster_record(item["register_number"], item["name"], item["email"], item["department"], item["cgpa"], item.get("tenth_percentage"), item.get("twelfth_percentage"), item.get("skills", "")) for item in records]
    db.record_upload_log("Student Academic Roster", file.filename, len(records) + skipped_count, len(processed), skipped_count)
    return {"success": True, "message": f"Successfully imported {len(processed)} student academic profiles.", "total_rows": len(records) + skipped_count, "imported_count": len(processed), "skipped_count": skipped_count, "students": processed}


async def upload_company_drives(file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowed 10MB limit.")
    try:
        records, skipped_count = upload_service.parse_company_drives(content, file.filename)
    except ValueError as exc:
        upload_service.record_failure("Company Drives", file.filename, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    processed = [db.upsert_company_drive_record(**item) for item in records]
    created = sum(item["action"] == "Created" for item in processed)
    updated = len(processed) - created
    db.record_upload_log("Company Drives Scheduling", file.filename, len(records) + skipped_count, len(processed), skipped_count)
    return {"success": True, "message": f"Successfully processed {len(processed)} company placement drives ({created} created, {updated} updated).", "total_rows": len(records) + skipped_count, "created_count": created, "updated_count": updated, "skipped_count": skipped_count, "drives": processed}
