import db


def authenticate(gmail: str, password: str):
    user = db.get_user_by_gmail(gmail)
    if not user or user["password"] != password:
        return None
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
