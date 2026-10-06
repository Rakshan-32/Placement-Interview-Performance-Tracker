from fastapi import APIRouter

from backend.controllers import auth_controller
from backend.schemas import GrantSingleAccessRequest, LoginRequest

router = APIRouter()
router.add_api_route("/api/login", auth_controller.login, methods=["POST"])
router.add_api_route("/api/users", auth_controller.list_users, methods=["GET"])
router.add_api_route("/api/users/grant-single-access", auth_controller.grant_single_access, methods=["POST"], response_model=None)
