import json
from datetime import datetime

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from neo4j import GraphDatabase

from app.config import MYSQL_DATABASE_URL, NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
from app.security import require_student_scope, require_session, require_role_header

router = APIRouter(prefix="/api/v1/students", tags=["Students & Audit"])
mysql_engine = create_engine(MYSQL_DATABASE_URL, pool_pre_ping=True)


def get_neo4j_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))


class StudentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str | None = Field(default=None, max_length=150)
    department: str = Field(min_length=1, max_length=120)
    semester: int = Field(default=1, ge=1, le=8)
    role: str = Field(default="Student", max_length=50)



class EnrollRequest(BaseModel):
    user_id: int
    course_code: str


class CourseRecordAdjustment(BaseModel):
    course_code: str = Field(min_length=1, max_length=30)
    action: str = Field(default="remove", max_length=30)
    reason: str = Field(min_length=3, max_length=500)


def init_student_storage():
    """Create the persistent student/enrollment tables and seed the original demo student."""
    with mysql_engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS copilot_students (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(150) NULL,
                department VARCHAR(120) NOT NULL,
                track VARCHAR(120) NOT NULL DEFAULT 'AI & Data Science',
                semester INT NOT NULL DEFAULT 1,
                subjects TEXT NULL,
                role VARCHAR(50) NOT NULL DEFAULT 'Student',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS copilot_student_courses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                course_code VARCHAR(30) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'completed',
                enrolled_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_student_course (student_id, course_code),
                CONSTRAINT fk_copilot_student
                    FOREIGN KEY (student_id) REFERENCES copilot_students(id)
                    ON DELETE CASCADE
            )
        """))

        existing = conn.execute(text("SELECT id FROM copilot_students WHERE id = 1")).scalar()
        if existing is None:
            conn.execute(text("""
                INSERT INTO copilot_students
                    (id, name, email, department, track, semester, subjects, role)
                VALUES
                    (1, 'Kanhai', NULL, 'Computer Science', 'AI & Data Science', 4,
                     :subjects, 'Student')
            """), {"subjects": json.dumps(["CS101", "CS102", "CS201", "MATH101"])})

        seed_codes = ["CS101", "CS102", "CS201", "MATH101"]
        for code in seed_codes:
            conn.execute(text("""
                INSERT IGNORE INTO copilot_student_courses (student_id, course_code, status)
                VALUES (1, :course_code, 'completed')
            """), {"course_code": code})


def _student_row(student_id: int):
    with mysql_engine.connect() as conn:
        row = conn.execute(text("""
            SELECT id, name, email, department, track, semester, subjects, role, created_at
            FROM copilot_students
            WHERE id = :id
        """), {"id": student_id}).mappings().first()
    return dict(row) if row else None


def _enrolled_courses(student_id: int) -> list[str]:
    with mysql_engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT course_code
            FROM copilot_student_courses
            WHERE student_id = :id AND status = 'enrolled'
            ORDER BY enrolled_at, course_code
        """), {"id": student_id}).scalars().all()
    return [str(code) for code in rows]


def _write_audit(student_id: int, actor_role: str, actor_name: str, action: str, course_code: str | None, details: str):
    # Audit table is initialized by the advisor router at application startup.
    with mysql_engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO copilot_audit_log
            (student_id, actor_role, actor_name, action, entity_type, entity_id, course_code, details)
            VALUES (:student_id, :actor_role, :actor_name, :action, :entity_type, NULL, :course_code, :details)
        """), {
            "student_id": student_id, "actor_role": actor_role, "actor_name": actor_name,
            "action": action, "entity_type": "student_course", "course_code": course_code, "details": details
        })


def _completed_courses(student_id: int) -> list[str]:
    with mysql_engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT course_code
            FROM copilot_student_courses
            WHERE student_id = :id AND status = 'completed'
            ORDER BY enrolled_at, course_code
        """), {"id": student_id}).scalars().all()
    return [str(code) for code in rows]


def _public_student(row: dict):
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row.get("email"),
        "department": row["department"],
        "track": row["track"],
        "semester": row["semester"],
        "subjects": json.loads(row["subjects"] or "[]"),
        "role": row["role"],
        "created_at": row["created_at"].isoformat() if isinstance(row.get("created_at"), datetime) else row.get("created_at"),
    }


@router.get("/list")
def list_students():
    """Return persistent student profiles for the student switcher."""
    with mysql_engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, name, email, department, track, semester, subjects, role, created_at
            FROM copilot_students
            WHERE role = 'Student'
            ORDER BY id
        """)).mappings().all()
    return [_public_student(dict(row)) for row in rows]


@router.post("")
def create_student(payload: StudentCreate):
    """Create a persistent student profile."""
    with mysql_engine.begin() as conn:
        result = conn.execute(text("""
            INSERT INTO copilot_students
                (name, email, department, track, semester, subjects, role)
            VALUES
                (:name, :email, :department, :track, :semester, :subjects, :role)
        """), {
            "name": payload.name.strip(),
            "email": payload.email.strip() if payload.email else None,
            "department": payload.department.strip(),
            "track": "AI & Data Science",
            "semester": payload.semester,
            "subjects": json.dumps([]),
            "role": "Student",
        })
        student_id = result.lastrowid

    return {"status": "SUCCESS", "student": _public_student(_student_row(student_id))}


@router.get("/{user_id}")
def get_student(user_id: int, x_demo_role: str | None = Header(default=None), x_demo_student_id: str | None = Header(default=None), authorization: str | None = Header(default=None)):
    try: require_session(authorization, x_demo_role, x_demo_student_id)
    except PermissionError as exc: raise HTTPException(status_code=403, detail=str(exc))
    try:
        role = require_student_scope(x_demo_role, x_demo_student_id, user_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    row = _student_row(user_id)
    if not row:
        raise HTTPException(status_code=404, detail="Student not found.")
    student = _public_student(row)
    student["completed_courses"] = _completed_courses(user_id)
    student["enrolled_courses"] = _enrolled_courses(user_id)
    return student


@router.get("/{user_id}/audit")
def audit_student_progress(user_id: int, x_demo_role: str | None = Header(default=None), x_demo_student_id: str | None = Header(default=None), authorization: str | None = Header(default=None)):
    try: require_session(authorization, x_demo_role, x_demo_student_id)
    except PermissionError as exc: raise HTTPException(status_code=403, detail=str(exc))
    """Read persistent completion state and calculate eligibility from the Neo4j graph."""
    try:
        require_student_scope(x_demo_role, x_demo_student_id, user_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    row = _student_row(user_id)
    if not row:
        raise HTTPException(status_code=404, detail="Student not found.")

    completed_courses = _completed_courses(user_id)
    enrolled_courses = _enrolled_courses(user_id)
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            catalog_result = session.run("""
                MATCH (c:Course)
                OPTIONAL MATCH (prereq:Course)-[:PREREQUISITE_FOR]->(c)
                RETURN c.code AS code, c.name AS name, c.credits AS credits,
                       collect(DISTINCT prereq.code) AS required_prereqs
                ORDER BY c.code
            """)
            catalog = [record.data() for record in catalog_result]
            valid_codes = {str(item["code"]).upper() for item in catalog if item["code"]}
            completed_valid = [code for code in completed_courses if code.upper() in valid_codes]
            enrolled_valid = [code for code in enrolled_courses if code.upper() in valid_codes]
            occupied = {c.upper() for c in completed_valid + enrolled_valid}

            eligible = []
            for item in catalog:
                code = str(item["code"]).upper()
                if code in occupied:
                    continue
                required = [str(p).upper() for p in (item["required_prereqs"] or []) if p]
                if all(req in {c.upper() for c in completed_valid} for req in required):
                    eligible.append({
                        "code": code,
                        "name": item["name"],
                        "credits": item["credits"],
                        "required_prereqs": required,
                    })

            return {
                "user_id": user_id,
                "student": _public_student(row),
                "completed_courses": completed_valid,
                "enrolled_courses": enrolled_valid,
                "eligible_courses": eligible,
            }
    finally:
        driver.close()


@router.post("/enroll")
def enroll_course(payload: EnrollRequest, x_demo_role: str | None = Header(default=None), x_demo_student_id: str | None = Header(default=None), authorization: str | None = Header(default=None)):
    """Approval-gated enrollment entry point. The existing UI button creates a request; it never enrolls directly."""
    try:
        require_session(authorization, x_demo_role, x_demo_student_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    try:
        role = require_student_scope(x_demo_role, x_demo_student_id, payload.user_id)
        if role != "Student":
            raise PermissionError("Only the Student role can request course enrollment in this workflow.")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    row = _student_row(payload.user_id)
    if not row:
        raise HTTPException(status_code=404, detail="Student not found.")
    code = payload.course_code.strip().upper()

    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            course_result = session.run("""
                MATCH (c:Course {code: $code})
                OPTIONAL MATCH (prereq:Course)-[:PREREQUISITE_FOR]->(c)
                RETURN c.code AS code, c.name AS name, collect(DISTINCT prereq.code) AS prerequisites
            """, code=code).single()
            if not course_result:
                raise HTTPException(status_code=404, detail=f"Course '{code}' not found.")
            prerequisites = [str(p).upper() for p in (course_result["prerequisites"] or []) if p]
    finally:
        driver.close()

    completed = {c.upper() for c in _completed_courses(payload.user_id)}
    enrolled = {c.upper() for c in _enrolled_courses(payload.user_id)}
    if code in completed:
        return {"status": "COMPLETED", "message": f"{code} is already completed.", "course_code": code}
    if code in enrolled:
        return {"status": "ENROLLED", "message": f"{code} is already enrolled.", "course_code": code}
    missing = [p for p in prerequisites if p not in completed]
    if missing:
        raise HTTPException(status_code=409, detail=f"{code} is locked. Missing prerequisite(s): {', '.join(missing)}")

    with mysql_engine.begin() as conn:
        existing = conn.execute(text("""
            SELECT id, status FROM copilot_advisor_requests
            WHERE student_id=:sid AND course_code=:code AND status IN ('Pending','Approved')
            ORDER BY id DESC LIMIT 1
        """), {"sid": payload.user_id, "code": code}).mappings().first()
        if existing:
            return {"status": "PENDING" if existing["status"] == "Pending" else "APPROVED", "request_id": existing["id"], "course_code": code,
                    "message": f"{code} already has an {existing['status'].lower()} advisor request."}
        result = conn.execute(text("""
            INSERT INTO copilot_advisor_requests (student_id, course_code, reason)
            VALUES (:sid, :code, :reason)
        """), {"sid": payload.user_id, "code": code,
              "reason": f"Enrollment approval requested for {code} from the course enrollment action."})
        request_id = result.lastrowid
        conn.execute(text("""
            INSERT INTO copilot_audit_log
            (student_id, actor_role, actor_name, action, entity_type, entity_id, course_code, details)
            VALUES (:sid, 'Student', :name, 'Approval requested', 'advisor_request', :rid, :code, :details)
        """), {"sid": payload.user_id, "name": row["name"], "rid": str(request_id), "code": code,
              "details": "Enrollment requested through the course Enroll button; advisor approval required before enrollment."})

    return {"status": "PENDING", "request_id": request_id, "course_code": code,
            "message": f"Advisor approval requested for {code}. The course will be enrolled only after approval."}


@router.post("/{user_id}/course-records/adjust")
def adjust_course_record(user_id: int, payload: CourseRecordAdjustment,
                         x_demo_role: str | None = Header(default=None),
                         authorization: str | None = Header(default=None)):
    """Advisor/Coordinator can remove an enrolled or completed record with an auditable reason."""
    try:
        require_session(authorization, x_demo_role)
        role = require_role_header(x_demo_role, {"Advisor", "Coordinator"})
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    if payload.action.strip().lower() != "remove":
        raise HTTPException(status_code=422, detail="Only the 'remove' record adjustment is supported in this demo.")
    code = payload.course_code.strip().upper()
    with mysql_engine.begin() as conn:
        student = conn.execute(text("SELECT id, name FROM copilot_students WHERE id=:id"), {"id": user_id}).mappings().first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found.")
        row = conn.execute(text("""
            SELECT id, status FROM copilot_student_courses
            WHERE student_id=:sid AND course_code=:code
            FOR UPDATE
        """), {"sid": user_id, "code": code}).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail=f"No academic record exists for {code}.")
        old_status = str(row["status"])
        conn.execute(text("DELETE FROM copilot_student_courses WHERE id=:id"), {"id": row["id"]})
        details = json.dumps({"student": student["name"], "course_code": code, "previous_status": old_status,
                              "action": "remove", "reason": payload.reason.strip()})
        conn.execute(text("""
            INSERT INTO copilot_audit_log
            (student_id, actor_role, actor_name, action, entity_type, entity_id, course_code, details)
            VALUES (:sid, :role, :actor, :action, 'student_course', :entity_id, :code, :details)
        """), {"sid": user_id, "role": role, "actor": "Demo Coordinator" if role == "Coordinator" else "Demo Advisor",
              "action": f"Academic record removed ({old_status})", "entity_id": str(row["id"]), "code": code, "details": details})
    return {"status": "SUCCESS", "course_code": code, "previous_status": old_status,
            "message": f"{code} was removed from {student['name']}'s academic record and the action was audited."}
