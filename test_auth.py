from fastapi.testclient import TestClient
import db
from app import app

# Initialize test database
db.init_db()

client = TestClient(app)

def test_successful_login():
    print("Test 1: Valid credentials login...")
    response = client.post("/api/login", json={
        "gmail": "coordinator@gmail.com",
        "password": "coord123"
    })
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    data = response.json()
    assert data["success"] is True, "Expected success to be True"
    assert data["message"] == "Logged in successfully", f"Unexpected message: {data['message']}"
    assert "user" in data, "User object missing in response"
    assert data["user"]["gmail"] == "coordinator@gmail.com", "Gmail mismatch"
    assert data["user"]["role"] == "Coordinator", "Role mismatch"
    assert "uuid" in data["user"], "UUID missing in response"
    print("[OK] Test 1 PASSED: Valid credentials login returned 200 OK and 'Logged in successfully'")

def test_successful_student_login():
    response = client.post("/api/login", json={
        "gmail": "student@gmail.com",
        "password": "student123"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["user"]["gmail"] == "student@gmail.com"
    assert data["user"]["role"] == "Student"

def test_invalid_password():
    print("\nTest 2: Invalid password login...")
    response = client.post("/api/login", json={
        "gmail": "admin@gmail.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401, f"Expected 401 Unauthorized, got {response.status_code}"
    data = response.json()
    assert data["success"] is False, "Expected success to be False"
    assert data["message"] == "Invalid Gmail or password", f"Unexpected message: {data['message']}"
    print("[OK] Test 2 PASSED: Invalid password returned 401 Unauthorized and 'Invalid Gmail or password'")

def test_nonexistent_gmail():
    print("\nTest 3: Non-existent Gmail login...")
    response = client.post("/api/login", json={
        "gmail": "nonexistent@gmail.com",
        "password": "somepassword"
    })
    assert response.status_code == 401, f"Expected 401 Unauthorized, got {response.status_code}"
    data = response.json()
    assert data["success"] is False, "Expected success to be False"
    assert data["message"] == "Invalid Gmail or password", f"Unexpected message: {data['message']}"
    print("[OK] Test 3 PASSED: Non-existent Gmail returned 401 Unauthorized and 'Invalid Gmail or password'")

if __name__ == "__main__":
    test_successful_login()
    test_invalid_password()
    test_nonexistent_gmail()
    print("\nALL AUTOMATED TESTS PASSED SUCCESSFULLY!")
