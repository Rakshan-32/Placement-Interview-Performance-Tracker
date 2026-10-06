"""
Shared pytest fixtures — cleans up test-created users before each session
so tests don't trip on state from a previous run.
"""
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
                "INSERT INTO authenticate (uuid, gmail, password, role, is_active, access_status) VALUES (?, ?, ?, ?, 1, 'ACTIVE')",
                (str(_uuid.uuid4()), email, pwd, role)
            )
    conn.commit()
    conn.close()


def pytest_sessionstart(session):
    db.init_db()
    _cleanup_test_users()
