import os
import sys
import sqlite3
import pytest
import numpy as np
import cv2
import base64
import io
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use an isolated test database
os.environ["SECRET_KEY"] = "test-secret"
import app as facet_app

@pytest.fixture
def client(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_attendance.db")
    test_dataset = str(tmp_path / "dataset")
    test_trainer = str(tmp_path / "trainer")
    test_model = os.path.join(test_trainer, "trainer.yml")

    os.makedirs(test_dataset, exist_ok=True)
    os.makedirs(test_trainer, exist_ok=True)

    monkeypatch.setattr(facet_app, "DATABASE", test_db)
    monkeypatch.setattr(facet_app, "DATASET", test_dataset)
    monkeypatch.setattr(facet_app, "TRAINER", test_trainer)
    monkeypatch.setattr(facet_app, "MODEL_PATH", test_model)
    monkeypatch.setattr(facet_app, "model_ready", False)

    facet_app.initialize_database()

    facet_app.app.config["TESTING"] = True
    facet_app.app.config["WTF_CSRF_ENABLED"] = False

    with facet_app.app.test_client() as client:
        yield client

def login_admin(client, username="admin", password="admin123"):
    return client.post("/", data={"username": username, "password": password}, follow_redirects=True)

def test_admin_login_success(client):
    response = login_admin(client)
    assert response.status_code == 200
    assert b"Facet" in response.data
    assert b"Student Biometric Registration" in response.data

def test_admin_login_invalid(client):
    response = login_admin(client, "admin", "wrongpassword")
    assert b"Invalid username or password" in response.data

def test_login_required_protection(client):
    # Without login, accessing dashboard should redirect to login
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")

def test_logout(client):
    login_admin(client)
    response = client.get("/logout", follow_redirects=True)
    assert response.status_code == 200
    # Following request to dashboard should require login again
    res2 = client.get("/dashboard")
    assert res2.status_code == 302

def test_student_registration_and_duplicate(client):
    login_admin(client)

    # Register first student
    res = client.post("/register_student", data={
        "name": "Alice Johnson",
        "roll_number": "MCA2026001",
        "department": "Computer Applications",
        "semester": "Semester 4"
    })
    data = res.get_json()
    assert data["success"] is True
    assert data["student_id"] > 0
    student_id = data["student_id"]

    # Verify student directory exists
    assert os.path.isdir(os.path.join(facet_app.DATASET, str(student_id)))

    # Attempt duplicate registration with same roll number
    res_dup = client.post("/register_student", data={
        "name": "Alice Duplicate",
        "roll_number": "MCA2026001",
        "department": "Computer Applications",
        "semester": "Semester 4"
    })
    data_dup = res_dup.get_json()
    assert data_dup["success"] is False
    assert "already exists" in data_dup["message"]

def test_empty_student_registration(client):
    login_admin(client)
    res = client.post("/register_student", data={"name": "", "roll_number": ""})
    data = res.get_json()
    assert data["success"] is False
    assert "required" in data["message"]

def test_face_capture_invalid_image(client):
    login_admin(client)
    res = client.post("/capture_face", data={
        "student_id": "1",
        "image": "not-a-valid-base64"
    })
    data = res.get_json()
    assert data["success"] is False

def test_train_model_no_samples(client):
    login_admin(client)
    res = client.post("/train_model")
    data = res.get_json()
    assert data["success"] is False
    assert "No face samples available" in data["message"]

def test_attendance_and_export_csv(client):
    login_admin(client)

    # Register student
    reg_res = client.post("/register_student", data={
        "name": "Bob Smith",
        "roll_number": "MCA2026002",
        "department": "MCA",
        "semester": "4"
    })
    student_id = reg_res.get_json()["student_id"]

    # Manually insert attendance
    conn = facet_app.get_db()
    conn.execute(
        "INSERT INTO attendance(student_id, date, time) VALUES (?, '2026-11-09', '09:30:00')",
        (student_id,)
    )
    conn.commit()
    conn.close()

    # Query attendance
    att_res = client.get("/attendance?date=2026-11-09")
    assert att_res.status_code == 200
    assert b"Bob Smith" in att_res.data
    assert b"MCA2026002" in att_res.data

    # Export CSV
    csv_res = client.get("/export")
    assert csv_res.status_code == 200
    assert csv_res.headers["Content-Type"].startswith("text/csv")
    csv_text = csv_res.data.decode("utf-8")
    assert "Bob Smith" in csv_text
    assert "MCA2026002" in csv_text

def test_delete_student(client):
    login_admin(client)

    reg_res = client.post("/register_student", data={
        "name": "Charlie Brown",
        "roll_number": "MCA2026003",
        "department": "MCA",
        "semester": "4"
    })
    student_id = reg_res.get_json()["student_id"]
    folder = os.path.join(facet_app.DATASET, str(student_id))
    assert os.path.isdir(folder)

    # Delete student
    del_res = client.post(f"/delete_student/{student_id}", follow_redirects=True)
    assert del_res.status_code == 200

    # Ensure removed from DB and folder deleted
    conn = facet_app.get_db()
    st = conn.execute("SELECT id FROM students WHERE id = ?", (student_id,)).fetchone()
    conn.close()
    assert st is None
    assert not os.path.exists(folder)
