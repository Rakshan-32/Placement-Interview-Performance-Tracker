from fastapi import status
from fastapi.responses import JSONResponse

from backend.schemas import GrantSingleAccessRequest, LoginRequest
from backend.services import auth_service


def login(credentials: LoginRequest):
    gmail = credentials.gmail.strip()
    if not gmail or not credentials.password:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"success": False, "message": "Gmail and password are required"})
    user = auth_service.authenticate(gmail, credentials.password)
    if not user:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"success": False, "message": "Invalid Gmail or password"})
    return {"success": True, "message": "Logged in successfully", "user": user}


def list_users():
    users = auth_service.list_users()
    return {"success": True, "users": users, "count": len(users)}


def grant_single_access(request: GrantSingleAccessRequest):
    gmail = request.gmail.strip().lower()
    if not gmail or "@" not in gmail:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"success": False, "message": "Please enter a valid Gmail address."})
    result = auth_service.grant_access(gmail, request.role, request.password)
    return {"success": True, "message": f"Successfully granted {result['role']} access to {gmail}.", "user": result}
