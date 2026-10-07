from fastapi import HTTPException, Header, status
from fastapi.responses import JSONResponse

import db
import email_service
from backend.schemas import (
    ActivateAccountRequest,
    ForgotPasswordRequest,
    GrantSingleAccessRequest,
    LoginRequest,
    ReactivateRequest,
    ResendInvitationRequest,
    ResetPasswordRequest,
    RevokeRequest,
    RoleUpdateRequest,
)
from backend.services import auth_service


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


def login(credentials: LoginRequest):
    gmail = credentials.gmail.strip()
    if not gmail or not credentials.password:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"success": False, "message": "Gmail and password are required"})
    user = auth_service.authenticate(gmail, credentials.password)
    if not user:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"success": False, "message": "Invalid Gmail or password"})
    if user.get("blocked"):
        if user["reason"] == "activation_required":
            return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"success": False, "message": "Account activation is required. Please check your email for the activation link."})
        if user["reason"] == "revoked":
            return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"success": False, "message": "Your account access has been revoked. Please contact the coordinator."})
    return {"success": True, "message": "Logged in successfully", "user": user}


def list_users():
    users = auth_service.list_users()
    return {"success": True, "users": users, "count": len(users)}


def grant_single_access(request: GrantSingleAccessRequest, x_user_id: str = Header(None)):
    gmail = request.gmail.strip().lower()
    if not gmail or "@" not in gmail:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"success": False, "message": "Please enter a valid Gmail address."})

    actor = None
    if x_user_id:
        actor = _require_coordinator(x_user_id)

    result = db.grant_single_user_access(
        gmail=gmail, role=request.role,
        actor_uuid=actor["uuid"] if actor else None,
        actor_gmail=actor["gmail"] if actor else None
    )

    access_status = result.get("access_status", "")

    if access_status == "REVOKED":
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"success": False, "message": f"Account {gmail} is revoked. Use 'Reactivate' to restore access.", "user": {"uuid": result["uuid"], "gmail": result["gmail"], "role": result["role"], "is_active": False, "access_status": "REVOKED"}}
        )

    if result.get("action") == "Already Invited - use resend":
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"success": False, "message": f"Account {gmail} is already invited but not yet activated. Use 'Resend Invitation'.", "user": {"uuid": result["uuid"], "gmail": result["gmail"], "role": result["role"], "is_active": 0, "access_status": "INVITED"}}
        )

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

    resp = {"success": True, "message": msg, "email_sent": email_result.get("sent", False), "delivery_mode": email_result.get("delivery_mode", "none"), "user": safe_result}
    if activation_token and not email_result.get("sent"):
        resp["dev_activation_url"] = f"{email_service.APP_BASE_URL}/#/activate/{activation_token}"

    return JSONResponse(status_code=status.HTTP_200_OK, content=resp)


def list_managed_users(x_user_id: str = Header(None)):
    _require_coordinator(x_user_id)
    users = db.get_all_users()
    return {"success": True, "users": users, "count": len(users)}


def revoke_user_access(req: RevokeRequest, x_user_id: str = Header(None)):
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
        return JSONResponse(status_code=status.HTTP_200_OK, content={"success": True, "message": f"Access for {gmail} is already revoked.", "user": {"uuid": user["uuid"], "gmail": user["gmail"], "role": user["role"], "is_active": 0}})
    return {"success": True, "message": f"Access revoked for {gmail}.", "user": {"uuid": user["uuid"], "gmail": user["gmail"], "role": user["role"], "is_active": 0}}


def reactivate_user_access(req: ReactivateRequest, x_user_id: str = Header(None)):
    actor = _require_coordinator(x_user_id)
    gmail = req.gmail.strip().lower()
    if not gmail or "@" not in gmail:
        raise HTTPException(status_code=400, detail="Invalid email address")
    user, result = db.reactivate_user_access(gmail, actor_uuid=actor["uuid"], actor_gmail=actor["gmail"])
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if result == "already_active":
        return JSONResponse(status_code=status.HTTP_200_OK, content={"success": True, "message": f"Access for {gmail} is already active.", "user": {"uuid": user["uuid"], "gmail": user["gmail"], "role": user["role"], "is_active": 1, "access_status": "ACTIVE"}})
    if result == "invited_not_activated":
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"success": False, "message": f"Account {gmail} is INVITED but not yet activated. Use 'Resend Invitation' instead.", "user": {"uuid": user["uuid"], "gmail": user["gmail"], "role": user["role"], "is_active": 0, "access_status": "INVITED"}})
    return {"success": True, "message": f"Access reactivated for {gmail}.", "user": {"uuid": user["uuid"], "gmail": user["gmail"], "role": user["role"], "is_active": 1, "access_status": "ACTIVE"}}


def update_user_role(req: RoleUpdateRequest, x_user_id: str = Header(None)):
    actor = _require_coordinator(x_user_id)
    gmail = req.gmail.strip().lower()
    if not gmail or "@" not in gmail:
        raise HTTPException(status_code=400, detail="Invalid email address")
    normalized = db.normalize_role(req.new_role)
    if not normalized or normalized not in db.VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(sorted(db.VALID_ROLES))}")
    user, result = db.update_user_role(gmail, normalized, actor_uuid=actor["uuid"], actor_gmail=actor["gmail"])
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if result == "same_role":
        return {"success": True, "message": f"User {gmail} already has role {normalized}.", "user": {"uuid": user["uuid"], "gmail": user["gmail"], "role": user["role"], "is_active": user.get("is_active", 1)}}
    return {"success": True, "message": f"Role for {gmail} updated to {normalized}.", "user": {"uuid": user["uuid"], "gmail": user["gmail"], "role": user["role"], "is_active": user.get("is_active", 1)}}


def get_access_history(gmail: str = None, x_user_id: str = Header(None)):
    _require_coordinator(x_user_id)
    history = db.get_access_history(user_gmail=gmail)
    return {"success": True, "history": history, "count": len(history)}


def validate_token(token: str, purpose: str = "ACTIVATION"):
    result = db.validate_auth_token(token, purpose)
    if not result["valid"]:
        return JSONResponse(status_code=400, content={"valid": False, "error": result["error"]})
    user = db.get_user_by_id(result["user_uuid"])
    return {"valid": True, "gmail": user["gmail"] if user else None, "role": user["role"] if user else None}


def activate_account(req: ActivateAccountRequest):
    success, result = db.activate_user(req.token, req.password)
    if not success:
        return JSONResponse(status_code=400, content={"success": False, "message": result})
    return {"success": True, "message": "Account activated successfully. You can now log in.", "user": result}


def forgot_password(req: ForgotPasswordRequest):
    gmail = req.gmail.strip().lower()
    raw_token, user = db.request_password_reset(gmail)
    response = {"success": True, "message": "If an account exists for this email, a password reset link has been generated."}
    if raw_token and user:
        reset_url = f"{email_service.APP_BASE_URL}/#/reset-password/{raw_token}"
        email_result = email_service.send_password_reset_email(gmail, reset_url)
        response["email_sent"] = email_result.get("sent", False)
        response["delivery_mode"] = email_result.get("delivery_mode", "none")
        if not email_result.get("sent"):
            response["dev_reset_url"] = reset_url
    return response


def reset_password(req: ResetPasswordRequest):
    success, message = db.reset_password(req.token, req.password)
    if not success:
        return JSONResponse(status_code=400, content={"success": False, "message": message})
    return {"success": True, "message": message}


def resend_invitation(req: ResendInvitationRequest, x_user_id: str = Header(None)):
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
    resp = {"success": True, "message": msg, "email_sent": email_sent, "delivery_mode": delivery_mode}
    if not email_sent:
        resp["dev_activation_url"] = activation_url
    return resp
