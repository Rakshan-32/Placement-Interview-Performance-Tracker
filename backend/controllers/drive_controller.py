from fastapi import status
from fastapi.responses import JSONResponse

from backend.schemas import CreateDriveRequest
from backend.services import drive_service


def list_drives():
    return {"success": True, "drives": drive_service.list_drives()}


def create_drive(data: CreateDriveRequest):
    if not data.company_name.strip() or not data.job_role.strip():
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"success": False, "message": "Company name and job role are required."})
    drive = drive_service.create_drive(data)
    drive["results_count"] = 0
    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"success": True, "message": "Drive created successfully!", "drive": drive})


def get_results(drive_id: str):
    results = drive_service.get_results(drive_id)
    return {"success": True, "results": results, "count": len(results)}
