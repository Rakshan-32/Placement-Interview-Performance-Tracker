from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    gmail: str = Field(..., json_schema_extra={"example": "student@gmail.com"})
    password: str = Field(..., json_schema_extra={"example": "student123"})


class CreateDriveRequest(BaseModel):
    company_name: str
    job_role: str
    ctc_lpa: float
    min_cgpa: float = 0.0
    allowed_branches: str = "All"
    location: str = "On Campus"
    status: str = "Active"
    deadline: str = None


class GrantSingleAccessRequest(BaseModel):
    gmail: str
    role: str = "Student"
    password: str = None


class RevokeRequest(BaseModel):
    gmail: str


class ReactivateRequest(BaseModel):
    gmail: str


class RoleUpdateRequest(BaseModel):
    gmail: str
    new_role: str


class ActivateAccountRequest(BaseModel):
    token: str
    password: str


class ForgotPasswordRequest(BaseModel):
    gmail: str


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


class ResendInvitationRequest(BaseModel):
    gmail: str
