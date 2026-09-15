import re
from dataclasses import dataclass

MAX_AI_INPUT_LENGTH = 1200

PROMPT_INJECTION_PATTERNS = [
    r"\bignore (all|any|the|previous|prior) instructions\b",
    r"\bdisregard (all|any|the|previous|prior) instructions\b",
    r"\bforget (all|any|the|previous|prior) instructions\b",
    r"\breveal (the )?(system|developer) prompt\b",
    r"\bshow (me )?(the )?(system|developer) message\b",
    r"\bact as (an? )?(admin|system|developer)\b",
    r"\bdisable (the )?(safety|security) rules\b",
    r"\bbypass (the )?(approval|security|permission)\b",
]

SENSITIVE_PATTERNS = [
    r"(?i)\b(api[_ -]?key|secret|access[_ -]?token)\s*[:=]\s*[^\s]+",
    r"(?i)\b(password|passwd|pwd)\s*[:=]\s*[^\s]+",
    r"(?i)\b(authorization|bearer)\s*[:=]\s*[^\s]+",
]

@dataclass(frozen=True)
class SecurityDecision:
    allowed: bool
    reason: str | None = None
    risk_type: str | None = None


def inspect_ai_input(value: str) -> SecurityDecision:
    text = str(value or "").strip()
    if not text:
        return SecurityDecision(False, "Question cannot be empty.", "invalid_input")
    if len(text) > MAX_AI_INPUT_LENGTH:
        return SecurityDecision(False, f"Question is too long. Maximum length is {MAX_AI_INPUT_LENGTH} characters.", "input_length")

    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return SecurityDecision(False, "The request was blocked by the AI safety policy because it attempts to override system instructions or approval boundaries.", "prompt_injection")

    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, text):
            return SecurityDecision(False, "The request was blocked because it appears to contain a secret or credential. Do not send passwords, API keys, tokens, or authorization headers to the Copilot.", "sensitive_data")

    return SecurityDecision(True)


def normalize_demo_role(role: str) -> str:
    value = str(role or "Student").strip().title()
    if value not in {"Student", "Advisor", "Coordinator"}:
        raise ValueError("Role must be Student, Advisor, or Coordinator.")
    return value

ROLE_PERMISSIONS = {
    "Student": {
        "view_own_academics", "use_copilot", "run_what_if",
        "view_own_recommendations", "request_approval"
    },
    "Advisor": {
        "view_student_academics", "review_approval", "view_audit"
    },
    "Coordinator": {
        "view_student_academics", "review_approval", "view_audit", "view_workflow_summary"
    },
}


def require_role_header(header_role: str | None, allowed_roles: set[str]) -> str:
    """Validate the server-side demo role header against an allow-list."""
    role = normalize_demo_role(header_role or "")
    if role not in allowed_roles:
        raise PermissionError("This role is not authorized for the requested action.")
    return role


def require_student_scope(header_role: str | None, header_student_id: str | None, requested_student_id: int) -> str:
    """Enforce that Student demo sessions can only access their selected student record."""
    role = normalize_demo_role(header_role or "")
    if role == "Student":
        try:
            scoped_id = int(str(header_student_id or ""))
        except (TypeError, ValueError):
            raise PermissionError("Student scope is required for this action.")
        if scoped_id != int(requested_student_id):
            raise PermissionError("Students may only access their own academic record.")
    return role


# ---------------------------------------------------------------------------
# Signed demo-session authorization
# ---------------------------------------------------------------------------
import base64
import hashlib
import hmac
import json
import os
import time

SESSION_TTL_SECONDS = int(os.getenv("COPILOT_SESSION_TTL", "28800"))
SESSION_SECRET = os.getenv("COPILOT_SESSION_SECRET", "academic-copilot-demo-change-this-secret")

def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

def _unb64url(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

def issue_session_token(role: str, student_id: int | None = None) -> str:
    role = normalize_demo_role(role)
    payload = {"role": role, "student_id": student_id, "iat": int(time.time()), "exp": int(time.time()) + SESSION_TTL_SECONDS}
    body = _b64url(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    sig = _b64url(hmac.new(SESSION_SECRET.encode(), body.encode(), hashlib.sha256).digest())
    return f"ac1.{body}.{sig}"

def verify_session_token(token: str | None) -> dict:
    if not token or not token.startswith("ac1."):
        raise PermissionError("A valid Academic Copilot session is required.")
    try:
        _, body, sig = token.split(".", 2)
        expected = _b64url(hmac.new(SESSION_SECRET.encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            raise ValueError
        payload = json.loads(_unb64url(body).decode())
        if int(payload.get("exp", 0)) < int(time.time()):
            raise ValueError
        return payload
    except Exception as exc:
        raise PermissionError("Invalid or expired Academic Copilot session.") from exc

def require_session(authorization: str | None, header_role: str | None = None, header_student_id: str | None = None) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise PermissionError("Authorization session is required for this action.")
    session = verify_session_token(authorization.split(" ", 1)[1].strip())
    role = normalize_demo_role(session.get("role"))
    if header_role is not None and normalize_demo_role(header_role) != role:
        raise PermissionError("Session role does not match the requested role.")
    if role == "Student":
        try:
            scoped = int(session.get("student_id"))
        except (TypeError, ValueError):
            raise PermissionError("Student scope is required for this action.")
        if header_student_id is not None and int(str(header_student_id)) != scoped:
            raise PermissionError("Student scope does not match the active session.")
    return session
