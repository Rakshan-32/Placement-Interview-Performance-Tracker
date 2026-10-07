import pytest
from fastapi.testclient import TestClient
from app import app
import db
import intervention_service

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


def test_failure_risk_weights_drive_difficulty(monkeypatch):
    monkeypatch.setattr(
        intervention_service.db,
        "get_drive_failure_rates",
        lambda drive_ids: {"easy-drive": 0.15, "hard-drive": 0.85},
    )

    easy_drive_failure = intervention_service.analyse_student_patterns([
        {"drive_id": "easy-drive", "result": "Rejected", "round": 1}
    ])
    hard_drive_failure = intervention_service.analyse_student_patterns([
        {"drive_id": "hard-drive", "result": "Rejected", "round": 1}
    ])

    assert easy_drive_failure["risk_probability_mean"] > hard_drive_failure["risk_probability_mean"]
    assert 0 <= easy_drive_failure["risk_probability"] <= 1
    assert 0 <= hard_drive_failure["risk_probability"] <= 1
    assert len(easy_drive_failure["risk_interval"]) == 2


def test_risk_probability_is_sampled_from_posterior(monkeypatch):
    monkeypatch.setattr(
        intervention_service.db,
        "get_drive_failure_rates",
        lambda drive_ids: {"easy-drive": 0.15},
    )
    samples = {
        intervention_service.analyse_student_patterns([
            {"drive_id": "easy-drive", "result": "Rejected", "round": 1}
        ])["risk_probability"]
        for _ in range(8)
    }
    assert len(samples) > 1


def test_derived_failure_analysis_is_non_deterministic(monkeypatch):
    monkeypatch.setattr(
        intervention_service.db,
        "get_drive_failure_rates",
        lambda drive_ids: {"easy-drive": 0.15},
    )
    records = [
        {"drive_id": "easy-drive", "result": "Rejected", "round": 1, "weakness_area": "DSA"},
        {"drive_id": "easy-drive", "result": "Selected", "round": 2, "score": 80},
    ]
    analyses = [intervention_service.analyse_student_patterns(records) for _ in range(12)]
    derived_results = {
        (analysis["passed_rounds"], analysis["failed_rounds"], tuple(analysis["sampled_classifications"]))
        for analysis in analyses
    }
    assert len(derived_results) > 1
