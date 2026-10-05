import pytest
from fastapi.testclient import TestClient
from app import app
import db

client = TestClient(app)

def test_list_interventions_and_students():
    coord = db.get_user_by_gmail("coordinator@gmail.com")
    assert coord is not None
    coord_uuid = coord["uuid"]

    res = client.get(
        "/api/interventions/students",
        headers={
            "x-user-id": coord_uuid,
            "x-user-role": "Coordinator",
            "x-department": "CSE"
        }
    )
    assert res.status_code == 200
    json_data = res.json()
    assert json_data["success"] is True
    assert "students" in json_data

def test_student_interventions_endpoint():
    coord = db.get_user_by_gmail("coordinator@gmail.com")
    assert coord is not None
    coord_uuid = coord["uuid"]

    students = db.get_students_for_scope(coord_uuid, "Coordinator", "CSE")
    assert len(students) > 0
    student_uuid = students[0]["uuid"]

    res = client.get(
        f"/api/interventions/{student_uuid}",
        headers={
            "x-user-id": coord_uuid,
            "x-user-role": "Coordinator",
            "x-department": "CSE"
        }
    )
    assert res.status_code == 200
    json_data = res.json()
    assert json_data["success"] is True
    assert "interventions" in json_data
