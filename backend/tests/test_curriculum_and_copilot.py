import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import curriculum

client = TestClient(app)

def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "components" in data
    assert data["components"]["api"] == "online"

def test_curriculum_departments():
    depts = curriculum.get_departments()
    assert depts == ["Information Technology", "Computer Science", "AI & Data Science"]

def test_curriculum_120_credits():
    for dept in curriculum.get_departments():
        courses = curriculum.get_curriculum(dept)
        assert len(courses) == 32
        total_cr = sum(c["credits"] for c in courses)
        assert total_cr == 120, f"{dept} total credits {total_cr} != 120"
        for sem in range(1, 9):
            sem_courses = [c for c in courses if c["semester"] == sem]
            assert sum(c["credits"] for c in sem_courses) == 15, f"{dept} Sem {sem} != 15"

def test_credit_progress_calculation():
    completed = ["CS101", "CS102", "CS201", "MATH101", "CS301"]
    res = curriculum.calculate_progress(completed, "Computer Science")
    assert res["completed_credits"] == 18.0
    assert res["remaining_credits"] == 102.0
    assert res["progress_percentage"] == 15.0
    assert res["degree_required_credits"] == 120

def test_course_api_curriculum():
    res = client.get("/api/v1/courses/curriculum?department=Computer%20Science")
    assert res.status_code == 200
    data = res.json()
    assert data["department"] == "Computer Science"
    assert data["total_required_credits"] == 120
    assert len(data["courses"]) == 32
    assert "semester_1" in data["semesters"]
    assert data["semesters"]["semester_1"]["credits"] == 15

def test_course_prerequisites_api():
    res = client.get("/api/v1/courses/CS401/prerequisites")
    assert res.status_code == 200
    data = res.json()
    assert data["course"] == "CS401"
    assert "CS301" in data["prerequisites"]

def test_cs401_prerequisite_rule_eligibility():
    """Verify CS301 -> CS401 rule:
    - CS301 not completed -> CS401 locked / not eligible.
    - CS301 completed -> CS401 eligible / unlocked.
    """
    from app import curriculum
    from app.routers.copilot import _audit

    catalog = curriculum.get_curriculum("Computer Science")

    # Case A: CS301 not completed
    _, ready_a, locked_a = _audit(catalog, ["CS101", "CS102", "MATH101"])
    ready_codes_a = {c["code"] for c in ready_a}
    locked_codes_a = {c["code"] for c in locked_a}
    assert "CS401" not in ready_codes_a
    assert "CS401" in locked_codes_a

    # Case B: CS301 completed
    _, ready_b, locked_b = _audit(catalog, ["CS101", "CS102", "CS301"])
    ready_codes_b = {c["code"] for c in ready_b}
    assert "CS401" in ready_codes_b

def test_health_head_method():
    res_root = client.head("/health")
    assert res_root.status_code == 200
    res_api = client.head("/api/v1/health")
    assert res_api.status_code == 200

def test_copilot_deterministic_credit_questions():
    headers = {"X-Demo-Role": "Student", "X-Demo-Student-Id": "1"}

    # 1. Credits completed
    res = client.post("/api/v1/copilot/chat", json={
        "user_id": 1,
        "user_message": "How many credits have I completed?",
        "target_track": "Computer Science"
    }, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["ai_used"] is False
    assert "credits" in data["copilot_response"].lower()

    # 2. Credits remaining
    res = client.post("/api/v1/copilot/chat", json={
        "user_id": 1,
        "user_message": "How many credits remain?",
        "target_track": "Computer Science"
    }, headers=headers)
    assert res.status_code == 200
    assert res.json()["ai_used"] is False

    # 3. Eligibility question
    res = client.post("/api/v1/copilot/chat", json={
        "user_id": 1,
        "user_message": "Am I eligible for CS401?",
        "target_track": "Computer Science"
    }, headers=headers)
    assert res.status_code == 200
    assert res.json()["ai_used"] is False

    # 4. Locked question
    res = client.post("/api/v1/copilot/chat", json={
        "user_id": 1,
        "user_message": "Why is CS403 locked?",
        "target_track": "Computer Science"
    }, headers=headers)
    assert res.status_code == 200
    assert res.json()["ai_used"] is False
    assert "locked" in res.json()["copilot_response"].lower()

    # 5. Course comparison
    res = client.post("/api/v1/copilot/chat", json={
        "user_id": 1,
        "user_message": "Which should I choose: CS401 or CS402?",
        "target_track": "Computer Science"
    }, headers=headers)
    assert res.status_code == 200
    assert res.json()["ai_used"] is False

    # 6. Priority / recommendation
    res = client.post("/api/v1/copilot/chat", json={
        "user_id": 1,
        "user_message": "What should I prioritize to stay on track?",
        "target_track": "Computer Science"
    }, headers=headers)
    assert res.status_code == 200
    assert res.json()["ai_used"] is False
