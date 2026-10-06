import pytest
import openpyxl
import io
import db
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def _get_coordinator():
    user = db.get_user_by_gmail("coordinator@gmail.com")
    assert user is not None, "Coordinator account must exist"
    return user


def _get_student():
    user = db.get_user_by_gmail("student@gmail.com")
    assert user is not None, "Student account must exist"
    return user


def _coord_headers():
    coord = _get_coordinator()
    return {"X-User-Id": coord["uuid"]}


# ==============================================================
# USER LISTING
# ==============================================================

class TestUserListing:
    def test_coordinator_can_list_users(self):
        res = client.get("/api/users/managed", headers=_coord_headers())
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["count"] > 0
        users = data["users"]
        for u in users:
            assert "uuid" in u
            assert "gmail" in u
            assert "role" in u
            assert "is_active" in u
            assert "password" not in u

    def test_unauthorized_role_rejected(self):
        student = _get_student()
        res = client.get("/api/users/managed", headers={"X-User-Id": student["uuid"]})
        assert res.status_code == 403

    def test_missing_auth_header_rejected(self):
        res = client.get("/api/users/managed")
        assert res.status_code == 401


# ==============================================================
# GRANT ACCESS
# ==============================================================

class TestGrantAccess:
    def test_grant_new_user(self):
        res = client.post("/api/users/grant-single-access", json={
            "gmail": "newgrant_test@gmail.com", "role": "Student"
        }, headers=_coord_headers())
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "password" not in data["user"]

        user = db.get_user_by_gmail("newgrant_test@gmail.com")
        assert user is not None
        assert user["role"] == "Student"
        assert user["is_active"] == 1

    def test_grant_creates_history(self):
        history = db.get_access_history(user_gmail="newgrant_test@gmail.com")
        granted = [h for h in history if h["action"] == "GRANTED"]
        assert len(granted) >= 1
        assert granted[0]["new_status"] == "ACTIVE"

    def test_grant_invalid_email(self):
        res = client.post("/api/users/grant-single-access", json={
            "gmail": "invalid-email", "role": "Student"
        }, headers=_coord_headers())
        assert res.status_code == 400

    def test_grant_existing_active_user_updates(self):
        res = client.post("/api/users/grant-single-access", json={
            "gmail": "newgrant_test@gmail.com", "role": "Mentor"
        }, headers=_coord_headers())
        assert res.status_code == 200
        user = db.get_user_by_gmail("newgrant_test@gmail.com")
        assert user["role"] == "Mentor"


# ==============================================================
# REVOKE ACCESS
# ==============================================================

class TestRevokeAccess:
    def test_revoke_active_user(self):
        db.grant_single_user_access("revoke_test@gmail.com", "Student")
        res = client.patch("/api/users/revoke", json={
            "gmail": "revoke_test@gmail.com"
        }, headers=_coord_headers())
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["user"]["is_active"] == 0

        user = db.get_user_by_gmail("revoke_test@gmail.com")
        assert user["is_active"] == 0

    def test_revoked_user_cannot_login(self):
        res = client.post("/api/login", json={
            "gmail": "revoke_test@gmail.com", "password": "student123"
        })
        assert res.status_code == 403
        data = res.json()
        assert data["success"] is False
        assert "revoked" in data["message"].lower()

    def test_revoke_creates_history(self):
        history = db.get_access_history(user_gmail="revoke_test@gmail.com")
        revoked = [h for h in history if h["action"] == "REVOKED"]
        assert len(revoked) >= 1
        assert revoked[0]["new_status"] == "REVOKED"

    def test_revoke_nonexistent_user(self):
        res = client.patch("/api/users/revoke", json={
            "gmail": "nonexistent99@gmail.com"
        }, headers=_coord_headers())
        assert res.status_code == 404

    def test_repeated_revoke_is_safe(self):
        res = client.patch("/api/users/revoke", json={
            "gmail": "revoke_test@gmail.com"
        }, headers=_coord_headers())
        assert res.status_code == 200
        data = res.json()
        assert "already" in data["message"].lower()

    def test_unauthorized_student_cannot_revoke(self):
        student = _get_student()
        res = client.patch("/api/users/revoke", json={
            "gmail": "revoke_test@gmail.com"
        }, headers={"X-User-Id": student["uuid"]})
        assert res.status_code == 403

    def test_cannot_revoke_self(self):
        coord = _get_coordinator()
        res = client.patch("/api/users/revoke", json={
            "gmail": coord["gmail"]
        }, headers=_coord_headers())
        assert res.status_code == 400

    def test_grant_revoked_user_returns_conflict(self):
        res = client.post("/api/users/grant-single-access", json={
            "gmail": "revoke_test@gmail.com", "role": "Student"
        }, headers=_coord_headers())
        assert res.status_code == 409


# ==============================================================
# REACTIVATE ACCESS
# ==============================================================

class TestReactivateAccess:
    def test_reactivate_revoked_user(self):
        res = client.patch("/api/users/reactivate", json={
            "gmail": "revoke_test@gmail.com"
        }, headers=_coord_headers())
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["user"]["is_active"] == 1

        user = db.get_user_by_gmail("revoke_test@gmail.com")
        assert user["is_active"] == 1

    def test_reactivated_user_can_login(self):
        res = client.post("/api/login", json={
            "gmail": "revoke_test@gmail.com", "password": "student123"
        })
        assert res.status_code == 200
        assert res.json()["success"] is True

    def test_reactivate_creates_history(self):
        history = db.get_access_history(user_gmail="revoke_test@gmail.com")
        reactivated = [h for h in history if h["action"] == "REACTIVATED"]
        assert len(reactivated) >= 1
        assert reactivated[0]["new_status"] == "ACTIVE"

    def test_reactivate_already_active_user(self):
        res = client.patch("/api/users/reactivate", json={
            "gmail": "revoke_test@gmail.com"
        }, headers=_coord_headers())
        assert res.status_code == 200
        data = res.json()
        assert "already" in data["message"].lower()

    def test_reactivate_nonexistent_user(self):
        res = client.patch("/api/users/reactivate", json={
            "gmail": "nonexistent99@gmail.com"
        }, headers=_coord_headers())
        assert res.status_code == 404

    def test_unauthorized_student_cannot_reactivate(self):
        student = _get_student()
        res = client.patch("/api/users/reactivate", json={
            "gmail": "revoke_test@gmail.com"
        }, headers={"X-User-Id": student["uuid"]})
        assert res.status_code == 403


# ==============================================================
# ROLE UPDATE
# ==============================================================

class TestRoleUpdate:
    def test_valid_role_update(self):
        db.grant_single_user_access("roletest@gmail.com", "Student")
        res = client.patch("/api/users/update-role", json={
            "gmail": "roletest@gmail.com", "new_role": "Mentor"
        }, headers=_coord_headers())
        assert res.status_code == 200
        data = res.json()
        assert data["user"]["role"] == "Mentor"

        user = db.get_user_by_gmail("roletest@gmail.com")
        assert user["role"] == "Mentor"

    def test_role_update_creates_history(self):
        history = db.get_access_history(user_gmail="roletest@gmail.com")
        role_updates = [h for h in history if h["action"] == "ROLE_UPDATED"]
        assert len(role_updates) >= 1
        assert role_updates[0]["old_role"] == "Student"
        assert role_updates[0]["new_role"] == "Mentor"

    def test_invalid_role_rejected(self):
        res = client.patch("/api/users/update-role", json={
            "gmail": "roletest@gmail.com", "new_role": "SuperAdmin"
        }, headers=_coord_headers())
        assert res.status_code == 400

    def test_same_role_handled(self):
        res = client.patch("/api/users/update-role", json={
            "gmail": "roletest@gmail.com", "new_role": "Mentor"
        }, headers=_coord_headers())
        assert res.status_code == 200
        data = res.json()
        assert "already" in data["message"].lower()

    def test_nonexistent_user_role_update(self):
        res = client.patch("/api/users/update-role", json={
            "gmail": "noone@gmail.com", "new_role": "Student"
        }, headers=_coord_headers())
        assert res.status_code == 404

    def test_unauthorized_student_cannot_update_role(self):
        student = _get_student()
        res = client.patch("/api/users/update-role", json={
            "gmail": "roletest@gmail.com", "new_role": "Department"
        }, headers={"X-User-Id": student["uuid"]})
        assert res.status_code == 403


# ==============================================================
# ACCESS HISTORY
# ==============================================================

class TestAccessHistory:
    def test_get_all_history(self):
        res = client.get("/api/users/access-history", headers=_coord_headers())
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["count"] > 0
        for h in data["history"]:
            assert "password" not in str(h).lower() or "password" not in h

    def test_get_user_history(self):
        res = client.get("/api/users/access-history?gmail=revoke_test@gmail.com", headers=_coord_headers())
        assert res.status_code == 200
        data = res.json()
        assert data["count"] > 0

    def test_history_ordering(self):
        res = client.get("/api/users/access-history", headers=_coord_headers())
        data = res.json()
        if data["count"] > 1:
            timestamps = [h["created_at"] for h in data["history"] if h["created_at"]]
            assert timestamps == sorted(timestamps, reverse=True)

    def test_unauthorized_history_access(self):
        student = _get_student()
        res = client.get("/api/users/access-history", headers={"X-User-Id": student["uuid"]})
        assert res.status_code == 403


# ==============================================================
# BULK GRANT
# ==============================================================

class TestBulkGrant:
    def test_bulk_creates_new_users_with_history(self):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["gmail", "role"])
        ws.append(["bulk_new1@gmail.com", "Student"])
        ws.append(["bulk_new2@gmail.com", "Mentor"])

        f = io.BytesIO()
        wb.save(f)
        f.seek(0)

        res = client.post("/api/users/upload-access",
            data={"default_role": "Student"},
            files={"file": ("test.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=_coord_headers()
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["created_count"] == 2

        u1 = db.get_user_by_gmail("bulk_new1@gmail.com")
        assert u1 is not None
        assert u1["is_active"] == 1

        h1 = db.get_access_history(user_gmail="bulk_new1@gmail.com")
        assert any(h["action"] == "GRANTED" for h in h1)

    def test_bulk_does_not_reactivate_revoked_user(self):
        db.grant_single_user_access("bulk_revoked@gmail.com", "Student")
        db.revoke_user_access("bulk_revoked@gmail.com")

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["gmail", "role"])
        ws.append(["bulk_revoked@gmail.com", "Student"])

        f = io.BytesIO()
        wb.save(f)
        f.seek(0)

        res = client.post("/api/users/upload-access",
            data={"default_role": "Student"},
            files={"file": ("test2.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=_coord_headers()
        )
        assert res.status_code == 200

        user = db.get_user_by_gmail("bulk_revoked@gmail.com")
        assert user["is_active"] == 0

    def test_bulk_handles_invalid_rows(self):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["gmail", "role"])
        ws.append(["invalid-no-at", "Student"])
        ws.append(["valid@gmail.com", "Student"])

        f = io.BytesIO()
        wb.save(f)
        f.seek(0)

        res = client.post("/api/users/upload-access",
            data={"default_role": "Student"},
            files={"file": ("test3.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=_coord_headers()
        )
        assert res.status_code == 200
        data = res.json()
        assert data["skipped_count"] >= 1


# ==============================================================
# DB PERSISTENCE CHECK
# ==============================================================

class TestPersistence:
    def test_access_state_persists_after_reinit(self):
        db.grant_single_user_access("persist_test@gmail.com", "Student")
        db.revoke_user_access("persist_test@gmail.com")

        db.init_db()

        user = db.get_user_by_gmail("persist_test@gmail.com")
        assert user is not None
        assert user["is_active"] == 0

        history = db.get_access_history(user_gmail="persist_test@gmail.com")
        assert len(history) >= 1


# ==============================================================
# REGRESSION: EXISTING TESTS STILL WORK
# ==============================================================

class TestRegression:
    def test_valid_login_still_works(self):
        res = client.post("/api/login", json={
            "gmail": "coordinator@gmail.com", "password": "coord123"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["user"]["role"] == "Coordinator"

    def test_invalid_login_still_rejected(self):
        res = client.post("/api/login", json={
            "gmail": "coordinator@gmail.com", "password": "wrong"
        })
        assert res.status_code == 401

    def test_drives_endpoint_still_works(self):
        res = client.get("/api/drives")
        assert res.status_code == 200
        assert res.json()["success"] is True

    def test_students_endpoint_still_works(self):
        res = client.get("/api/students")
        assert res.status_code == 200
        assert res.json()["success"] is True

    def test_demo_users_endpoint_still_works(self):
        res = client.get("/api/users")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True


# ==============================================================
# INTERVENTION ENDPOINT SECURITY (revoked user enforcement)
# ==============================================================

def _make_mentor():
    """Create a mentor account and return its user dict."""
    db.grant_single_user_access("intv_mentor@gmail.com", "Mentor")
    user = db.get_user_by_gmail("intv_mentor@gmail.com")
    assert user is not None
    return user


def _mentor_headers(user):
    return {
        "X-User-Id": user["uuid"],
        "X-User-Role": user["role"],
        "X-Department": user.get("department") or "CSE",
    }


class TestInterventionEndpointSecurity:
    """Proves that _requester() blocks revoked users from intervention APIs."""

    def test_active_user_can_access_interventions(self):
        mentor = _make_mentor()
        headers = _mentor_headers(mentor)
        res = client.get("/api/interventions", headers=headers)
        assert res.status_code == 200
        assert res.json()["success"] is True

    def test_active_user_can_access_intervention_students(self):
        mentor = _make_mentor()
        headers = _mentor_headers(mentor)
        res = client.get("/api/interventions/students", headers=headers)
        assert res.status_code == 200
        assert res.json()["success"] is True

    def test_revoked_user_blocked_from_interventions(self):
        db.grant_single_user_access("revoked_mentor@gmail.com", "Mentor")
        user = db.get_user_by_gmail("revoked_mentor@gmail.com")
        headers = _mentor_headers(user)

        res_before = client.get("/api/interventions", headers=headers)
        assert res_before.status_code == 200

        db.revoke_user_access("revoked_mentor@gmail.com")

        res_after = client.get("/api/interventions", headers=headers)
        assert res_after.status_code == 403
        assert "revoked" in res_after.json()["detail"].lower()

    def test_revoked_user_blocked_from_intervention_students(self):
        db.grant_single_user_access("revoked_mentor2@gmail.com", "Mentor")
        user = db.get_user_by_gmail("revoked_mentor2@gmail.com")
        headers = _mentor_headers(user)

        db.revoke_user_access("revoked_mentor2@gmail.com")

        res = client.get("/api/interventions/students", headers=headers)
        assert res.status_code == 403
        assert "revoked" in res.json()["detail"].lower()

    def test_revoked_coordinator_blocked_from_managed_users(self):
        db.grant_single_user_access("revoked_coord@gmail.com", "Coordinator")
        user = db.get_user_by_gmail("revoked_coord@gmail.com")
        headers = {"X-User-Id": user["uuid"]}

        res_before = client.get("/api/users/managed", headers=headers)
        assert res_before.status_code == 200

        db.revoke_user_access("revoked_coord@gmail.com")

        res_after = client.get("/api/users/managed", headers=headers)
        assert res_after.status_code == 403

    def test_unauthorized_role_still_rejected(self):
        db.grant_single_user_access("student_intv@gmail.com", "Student")
        user = db.get_user_by_gmail("student_intv@gmail.com")
        headers = _mentor_headers(user)
        headers["X-User-Role"] = "Student"

        res = client.get("/api/interventions", headers=headers)
        assert res.status_code in (200, 403)

    def test_reactivated_user_regains_access(self):
        db.grant_single_user_access("reactivated_mentor@gmail.com", "Mentor")
        user = db.get_user_by_gmail("reactivated_mentor@gmail.com")
        headers = _mentor_headers(user)

        db.revoke_user_access("reactivated_mentor@gmail.com")
        res_revoked = client.get("/api/interventions", headers=headers)
        assert res_revoked.status_code == 403

        db.reactivate_user_access("reactivated_mentor@gmail.com")
        res_reactivated = client.get("/api/interventions", headers=headers)
        assert res_reactivated.status_code == 200
        assert res_reactivated.json()["success"] is True

    def test_missing_user_id_rejected(self):
        res = client.get("/api/interventions", headers={})
        assert res.status_code == 401

    def test_unknown_user_id_rejected(self):
        res = client.get("/api/interventions", headers={
            "X-User-Id": "nonexistent-uuid-12345",
            "X-User-Role": "Mentor",
            "X-Department": "CSE",
        })
        assert res.status_code == 401
