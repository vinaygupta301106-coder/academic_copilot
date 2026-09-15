from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STUDENTS = ROOT / "backend" / "app" / "routers" / "students.py"
ADVISOR = ROOT / "backend" / "app" / "routers" / "advisor.py"
APP_JS = ROOT / "frontend" / "js" / "app.js"
INDEX = ROOT / "frontend" / "index.html"


def test_enroll_endpoint_is_approval_gated():
    text = STUDENTS.read_text(encoding="utf-8")
    assert "Advisor approval requested for {code}" in text
    assert "INSERT INTO copilot_advisor_requests" in text
    assert "INSERT INTO copilot_student_courses" not in text.split('@router.post("/enroll")', 1)[1].split('@router.post("/{user_id}/course-records/adjust")', 1)[0]


def test_advisor_approval_creates_enrollment():
    text = ADVISOR.read_text(encoding="utf-8")
    assert 'if new_status == "Approved":' in text
    assert "status='enrolled'" in text
    assert "Enrollment created after approval" in text


def test_staff_record_adjustment_is_present_and_audited():
    text = STUDENTS.read_text(encoding="utf-8")
    assert '@router.post("/{user_id}/course-records/adjust")' in text
    assert 'require_role_header(x_demo_role, {"Advisor", "Coordinator"})' in text
    assert "Academic record removed" in text


def test_frontend_enroll_button_calls_approval_gated_endpoint():
    text = APP_JS.read_text(encoding="utf-8")
    assert '`${API_BASE}/students/enroll`' in text
    assert "Advisor approval requested" in text
    assert 'textContent = "Requesting..."' in text


def test_advisor_overview_has_record_management_controls():
    text = APP_JS.read_text(encoding="utf-8")
    assert 'data-adjust-course=' in text
    assert 'data-adjust-status="enrolled"' in text
    assert 'data-adjust-status="completed"' in text
    assert 'Student Academic Overview' in INDEX.read_text(encoding="utf-8")
