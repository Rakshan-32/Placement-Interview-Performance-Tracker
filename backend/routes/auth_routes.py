from fastapi import APIRouter

from backend.controllers import auth_controller

router = APIRouter()
router.add_api_route("/api/login", auth_controller.login, methods=["POST"])
router.add_api_route("/api/users", auth_controller.list_users, methods=["GET"])
router.add_api_route("/api/users/grant-single-access", auth_controller.grant_single_access, methods=["POST"], response_model=None)
router.add_api_route("/api/users/managed", auth_controller.list_managed_users, methods=["GET"])
router.add_api_route("/api/users/revoke", auth_controller.revoke_user_access, methods=["PATCH"])
router.add_api_route("/api/users/reactivate", auth_controller.reactivate_user_access, methods=["PATCH"])
router.add_api_route("/api/users/update-role", auth_controller.update_user_role, methods=["PATCH"])
router.add_api_route("/api/users/access-history", auth_controller.get_access_history, methods=["GET"])
router.add_api_route("/api/users/resend-invitation", auth_controller.resend_invitation, methods=["POST"])
router.add_api_route("/api/auth/validate-token", auth_controller.validate_token, methods=["GET"])
router.add_api_route("/api/auth/activate", auth_controller.activate_account, methods=["POST"])
router.add_api_route("/api/auth/forgot-password", auth_controller.forgot_password, methods=["POST"])
router.add_api_route("/api/auth/reset-password", auth_controller.reset_password, methods=["POST"])
