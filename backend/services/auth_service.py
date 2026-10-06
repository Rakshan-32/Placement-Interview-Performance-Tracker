import db


def authenticate(gmail: str, password: str):
    user = db.get_user_by_gmail(gmail)
    if not user:
        return None

    access_status = user.get("access_status") or ("ACTIVE" if user.get("is_active", True) else "REVOKED")
    if access_status == "INVITED":
        return {"blocked": True, "reason": "activation_required"}
    if access_status == "REVOKED" or not user.get("is_active", True):
        return {"blocked": True, "reason": "revoked"}

    if not db.verify_password(password, user["password"]):
        return None

    if not db.is_hashed(user["password"]):
        db.migrate_legacy_password(user["uuid"], password)

    return {
        "uuid": user["uuid"],
        "gmail": user["gmail"],
        "role": user["role"],
        "department": user.get("department") or "CSE",
    }


def list_users():
    return db.get_all_users()


def grant_access(gmail: str, role: str, password: str = None):
    return db.grant_single_user_access(gmail=gmail, role=role, password=password)


def bulk_grant_access(records):
    return db.bulk_grant_user_access(records)
