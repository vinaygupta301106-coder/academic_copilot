from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.security import issue_session_token, normalize_demo_role

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"] )

class DemoSessionRequest(BaseModel):
    role: str = Field(default="Student")
    student_id: int | None = None

@router.post("/demo-session")
def create_demo_session(payload: DemoSessionRequest):
    try:
        role = normalize_demo_role(payload.role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if role == "Student" and payload.student_id is None:
        raise HTTPException(status_code=400, detail="Student ID is required for a Student session.")
    return {"access_token": issue_session_token(role, payload.student_id), "token_type": "bearer", "expires_in": 28800, "role": role, "student_id": payload.student_id}
