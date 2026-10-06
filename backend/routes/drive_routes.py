from fastapi import APIRouter

from backend.controllers import drive_controller
from backend.schemas import CreateDriveRequest

router = APIRouter()
router.add_api_route("/api/drives", drive_controller.list_drives, methods=["GET"])
router.add_api_route("/api/drives", drive_controller.create_drive, methods=["POST"])
router.add_api_route("/api/drives/{drive_id}/results", drive_controller.get_results, methods=["GET"])
