"""
Shared pytest fixtures — isolate tests in temp databases and
clean up test-created users before each session.
"""
import os
import tempfile

TEST_DIR = tempfile.gettempdir()
ROOT_TEST_DB = os.path.join(TEST_DIR, f"placement_tracker_root_{os.getpid()}.db")
BULK_TEST_DB = os.path.join(TEST_DIR, f"placement_tracker_bulk_{os.getpid()}.db")

for test_db in (ROOT_TEST_DB, BULK_TEST_DB):
    if os.path.exists(test_db):
        os.remove(test_db)

os.environ["DATABASE_URL"] = f"sqlite:///{ROOT_TEST_DB.replace(os.sep, '/')}"
os.environ["BULK_UPLOAD_DB_PATH"] = BULK_TEST_DB

import pytest
import db


def _cleanup_test_users():
    """Remove all non-seed users and their tokens/history so each test session starts clean."""
    seed_emails = {
        "coordinator@gmail.com",
        "student@gmail.com",
        "mentor@gmail.com",
        "department@gmail.com",
        "dept.cse@gmail.com",
        "recruiter@gmail.com",
    }
    conn = db.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT uuid, gmail FROM authenticate")
    all_users = cursor.fetchall()
    for row in all_users:
        if row["gmail"].lower() not in seed_emails:
            cursor.execute("DELETE FROM auth_tokens WHERE user_uuid = ?", (row["uuid"],))
            cursor.execute("DELETE FROM access_history WHERE user_uuid = ?", (row["uuid"],))
            cursor.execute("DELETE FROM authenticate WHERE uuid = ?", (row["uuid"],))

    import uuid as _uuid
    seed_accounts = [
        ("coordinator@gmail.com", "coord123", "Coordinator"),
        ("student@gmail.com", "student123", "Student"),
        ("mentor@gmail.com", "mentor123", "Mentor"),
        ("department@gmail.com", "dept123", "Department"),
        ("dept.cse@gmail.com", "dept123", "Department"),
        ("recruiter@gmail.com", "recruiter123", "Recruiter"),
    ]
    for email, pwd, role in seed_accounts:
        cursor.execute(
            "SELECT uuid FROM authenticate WHERE LOWER(gmail) = ?", (email,)
        )
        if cursor.fetchone():
            cursor.execute(
                "UPDATE authenticate SET password = ?, is_active = 1, access_status = 'ACTIVE' WHERE LOWER(gmail) = ?",
                (pwd, email)
            )
        else:
            cursor.execute(
                "INSERT INTO authenticate (uuid, gmail, password, role, is_active, access_status, created_at) VALUES (?, ?, ?, ?, 1, 'ACTIVE', datetime('now'))",
                (str(_uuid.uuid4()), email, pwd, role)
            )
    conn.commit()
    conn.close()


def pytest_sessionstart(session):
    db.init_db()
    _cleanup_test_users()
