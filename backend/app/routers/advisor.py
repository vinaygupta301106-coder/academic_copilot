import json
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Header
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

from app.config import MYSQL_DATABASE_URL, NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
from neo4j import GraphDatabase

from app.security import normalize_demo_role, require_student_scope, require_role_header, require_session

router = APIRouter(prefix="/api/v1/advisor", tags=["Advisor Workflow & Audit"])
mysql_engine = create_engine(MYSQL_DATABASE_URL, pool_pre_ping=True)

VALID_STATUSES = {"Pending", "Approved", "Rejected", "Changes Requested"}

class ApprovalRequest(BaseModel):
    student_id: int
    course_code: str = Field(min_length=1, max_length=30)
    reason: str = Field(default="Student requests advisor review of this academic pathway choice.", max_length=500)
    actor_role: str = Field(default="Student", max_length=30)

class DecisionRequest(BaseModel):
    decision: str = Field(min_length=1, max_length=30)
    note: str = Field(default="", max_length=1000)
    actor_role: str = Field(default="Advisor", max_length=30)
    actor_name: str = Field(default="Demo Advisor", max_length=100)

def init_advisor_storage():
    with mysql_engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS copilot_advisor_requests (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                course_code VARCHAR(30) NOT NULL,
                request_type VARCHAR(40) NOT NULL DEFAULT 'Course Approval',
                reason VARCHAR(500) NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'Pending',
                advisor_note VARCHAR(1000) NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                reviewed_by VARCHAR(100) NULL,
                reviewed_role VARCHAR(30) NULL,
                INDEX idx_advisor_student (student_id),
                INDEX idx_advisor_status (status),
                CONSTRAINT fk_advisor_student FOREIGN KEY (student_id) REFERENCES copilot_students(id) ON DELETE CASCADE
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS copilot_audit_log (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NULL,
                actor_role VARCHAR(30) NOT NULL,
                actor_name VARCHAR(100) NOT NULL,
                action VARCHAR(80) NOT NULL,
                entity_type VARCHAR(50) NOT NULL,
                entity_id VARCHAR(50) NULL,
                course_code VARCHAR(30) NULL,
                details TEXT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_audit_student (student_id),
                INDEX idx_audit_created (created_at),
                CONSTRAINT fk_audit_student FOREIGN KEY (student_id) REFERENCES copilot_students(id) ON DELETE SET NULL
            )
        """))

def _log(conn, student_id, actor_role, actor_name, action, entity_type, entity_id=None, course_code=None, details=None):
    conn.execute(text("""
        INSERT INTO copilot_audit_log
        (student_id, actor_role, actor_name, action, entity_type, entity_id, course_code, details)
        VALUES (:student_id, :actor_role, :actor_name, :action, :entity_type, :entity_id, :course_code, :details)
    """), {
        "student_id": student_id, "actor_role": actor_role, "actor_name": actor_name,
        "action": action, "entity_type": entity_type, "entity_id": str(entity_id) if entity_id is not None else None,
        "course_code": course_code, "details": details
    })

def _serialize(row):
    d = dict(row)
    for k in ("created_at", "updated_at"):
        if isinstance(d.get(k), datetime): d[k] = d[k].isoformat(sep=" ")
    return d

@router.post("/requests")
def create_approval_request(payload: ApprovalRequest, x_demo_role: str | None = Header(default=None), x_demo_student_id: str | None = Header(default=None), authorization: str | None = Header(default=None)):
    try: require_session(authorization, x_demo_role, x_demo_student_id)
    except PermissionError as exc: raise HTTPException(status_code=403, detail=str(exc))
    role = normalize_demo_role(x_demo_role or payload.actor_role)
    if role != normalize_demo_role(payload.actor_role):
        raise HTTPException(status_code=403, detail="Demo role header does not match the requested actor role.")
    if role != "Student":
        raise HTTPException(status_code=403, detail="Only the Student role can submit an advisor approval request.")
    try:
        require_student_scope(role, x_demo_student_id, payload.student_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    code = payload.course_code.strip().upper()
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    try:
        with driver.session() as session:
            course = session.run("MATCH (c:Course {code: $code}) RETURN c.code AS code, c.name AS name", code=code).single()
            if not course:
                raise HTTPException(status_code=404, detail=f"Course '{code}' was not found in the curriculum knowledge graph.")
    finally:
        driver.close()
    with mysql_engine.begin() as conn:
        student = conn.execute(text("SELECT id, name FROM copilot_students WHERE id=:id"), {"id": payload.student_id}).mappings().first()
        if not student: raise HTTPException(status_code=404, detail="Student not found.")
        existing = conn.execute(text("""SELECT id, status FROM copilot_advisor_requests WHERE student_id=:sid AND course_code=:code AND status IN ('Pending','Approved') ORDER BY id DESC LIMIT 1"""), {"sid":payload.student_id,"code":code}).mappings().first()
        if existing:
            return {"status":"EXISTS", "request":_serialize(existing), "message":f"{code} already has an {existing['status'].lower()} advisor request."}
        result = conn.execute(text("""INSERT INTO copilot_advisor_requests (student_id, course_code, reason) VALUES (:sid,:code,:reason)"""), {"sid":payload.student_id,"code":code,"reason":payload.reason.strip()})
        request_id = result.lastrowid
        _log(conn, payload.student_id, "Student", student["name"], "Approval requested", "advisor_request", request_id, code, payload.reason.strip())
        row = conn.execute(text("SELECT * FROM copilot_advisor_requests WHERE id=:id"), {"id":request_id}).mappings().first()
    return {"status":"SUCCESS", "request":_serialize(row), "message":f"Advisor approval requested for {code}."}

@router.get("/requests")
def list_requests(status: str = Query(default="all"), student_id: int | None = None, x_demo_role: str | None = Header(default=None), x_demo_student_id: str | None = Header(default=None), authorization: str | None = Header(default=None)):
    try: require_session(authorization, x_demo_role, x_demo_student_id)
    except PermissionError as exc: raise HTTPException(status_code=403, detail=str(exc))
    try:
        role = require_role_header(x_demo_role, {"Student", "Advisor", "Coordinator"})
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    if role == "Student":
        if student_id is None:
            raise HTTPException(status_code=403, detail="Students must provide a student_id scope.")
        try:
            require_student_scope(role, x_demo_student_id, student_id)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc))
    params = {}
    where=[]
    if status.lower() != "all": where.append("r.status = :status"); params["status"] = status.title()
    if student_id is not None: where.append("r.student_id = :student_id"); params["student_id"] = student_id
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    with mysql_engine.connect() as conn:
        rows=conn.execute(text(f"""SELECT r.*, s.name AS student_name, s.department, s.track, s.semester FROM copilot_advisor_requests r JOIN copilot_students s ON s.id=r.student_id {clause} ORDER BY CASE r.status WHEN 'Pending' THEN 0 WHEN 'Changes Requested' THEN 1 WHEN 'Approved' THEN 2 ELSE 3 END, r.updated_at DESC"""), params).mappings().all()
    return [_serialize(r) for r in rows]

@router.post("/requests/{request_id}/decision")
def decide_request(request_id: int, payload: DecisionRequest, x_demo_role: str | None = Header(default=None), authorization: str | None = Header(default=None)):
    try: require_session(authorization, x_demo_role)
    except PermissionError as exc: raise HTTPException(status_code=403, detail=str(exc))
    role = normalize_demo_role(x_demo_role or payload.actor_role)
    if role != normalize_demo_role(payload.actor_role):
        raise HTTPException(status_code=403, detail="Demo role header does not match the requested actor role.")
    decision = payload.decision.strip().lower()
    mapping={"approve":"Approved","approved":"Approved","reject":"Rejected","rejected":"Rejected","request changes":"Changes Requested","changes requested":"Changes Requested","changes":"Changes Requested"}
    new_status=mapping.get(decision)
    if not new_status: raise HTTPException(status_code=422, detail="Decision must be Approve, Reject, or Request Changes.")
    if role not in {"Advisor", "Coordinator"}:
        raise HTTPException(status_code=403, detail="Only Advisor or Coordinator roles can review requests.")
    with mysql_engine.begin() as conn:
        row=conn.execute(text("SELECT r.*, s.name AS student_name FROM copilot_advisor_requests r JOIN copilot_students s ON s.id=r.student_id WHERE r.id=:id FOR UPDATE"), {"id":request_id}).mappings().first()
        if not row: raise HTTPException(status_code=404, detail="Advisor request not found.")
        if row["status"] != "Pending" and new_status != "Changes Requested":
            raise HTTPException(status_code=409, detail=f"Request is already {row['status']}.")
        conn.execute(text("""UPDATE copilot_advisor_requests SET status=:status, advisor_note=:note, reviewed_by=:name, reviewed_role=:role WHERE id=:id"""), {"status":new_status,"note":payload.note.strip() or None,"name":payload.actor_name.strip() or "Demo Advisor","role":role,"id":request_id})
        details=json.dumps({"previous_status":row["status"],"new_status":new_status,"note":payload.note.strip()})
        _log(conn,row["student_id"],role,payload.actor_name.strip() or "Demo Advisor",f"Advisor decision: {new_status}","advisor_request",request_id,row["course_code"],details)
        updated=conn.execute(text("SELECT * FROM copilot_advisor_requests WHERE id=:id"), {"id":request_id}).mappings().first()
    return {"status":"SUCCESS","request":_serialize(updated),"message":f"Request #{request_id} marked {new_status}."}

@router.get("/audit-trail")
def audit_trail(student_id: int | None = None, limit: int = Query(default=50, ge=1, le=200), x_demo_role: str | None = Header(default=None), x_demo_student_id: str | None = Header(default=None), authorization: str | None = Header(default=None)):
    try: require_session(authorization, x_demo_role, x_demo_student_id)
    except PermissionError as exc: raise HTTPException(status_code=403, detail=str(exc))
    try:
        role = require_role_header(x_demo_role, {"Student", "Advisor", "Coordinator"})
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    if role == "Student":
        if student_id is None:
            raise HTTPException(status_code=403, detail="Students must provide a student_id scope.")
        try:
            require_student_scope(role, x_demo_student_id, student_id)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc))
    params={"limit":limit}
    clause=""
    if student_id is not None: clause="WHERE a.student_id=:student_id"; params["student_id"]=student_id
    with mysql_engine.connect() as conn:
        rows=conn.execute(text(f"SELECT a.*, s.name AS student_name FROM copilot_audit_log a LEFT JOIN copilot_students s ON s.id=a.student_id {clause} ORDER BY a.created_at DESC LIMIT :limit"), params).mappings().all()
    return [_serialize(r) for r in rows]

@router.get("/summary")
def advisor_summary(x_demo_role: str | None = Header(default=None), authorization: str | None = Header(default=None)):
    try: require_session(authorization, x_demo_role)
    except PermissionError as exc: raise HTTPException(status_code=403, detail=str(exc))
    try:
        require_role_header(x_demo_role, {"Advisor", "Coordinator"})
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    with mysql_engine.connect() as conn:
        counts=conn.execute(text("SELECT status, COUNT(*) AS count FROM copilot_advisor_requests GROUP BY status")).mappings().all()
        audit_count=conn.execute(text("SELECT COUNT(*) FROM copilot_audit_log")).scalar()
    summary={"Pending":0,"Approved":0,"Rejected":0,"Changes Requested":0}
    for r in counts: summary[r["status"]]=int(r["count"])
    return {"requests":summary,"total_audit_events":int(audit_count or 0)}
