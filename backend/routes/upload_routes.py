from fastapi import APIRouter

from backend.controllers import upload_controller

router = APIRouter()
router.add_api_route("/api/upload/drive-shortlist/{drive_id}", upload_controller.upload_drive_shortlist, methods=["POST"])
router.add_api_route("/api/upload/drive-results/{drive_id}", upload_controller.upload_drive_results_endpoint, methods=["POST"])
router.add_api_route("/api/drives/{drive_id}/upload-results", upload_controller.upload_drive_results, methods=["POST"])
router.add_api_route("/api/upload/user-access", upload_controller.upload_user_access, methods=["POST"])
router.add_api_route("/api/users/upload-access", upload_controller.upload_user_access, methods=["POST"])
router.add_api_route("/api/upload/student-roster", upload_controller.upload_student_roster, methods=["POST"])
router.add_api_route("/api/upload/company-drives", upload_controller.upload_company_drives, methods=["POST"])
