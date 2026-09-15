import base64
import hashlib
import hmac
import json
import time

import pytest

from app.security import (
    SESSION_SECRET,
    issue_session_token,
    require_session,
    verify_session_token,
)


def test_signed_student_session_is_valid():
    token = issue_session_token("Student", 1)
    payload = verify_session_token(token)
    assert payload["role"] == "Student"
    assert payload["student_id"] == 1


def test_tampered_session_token_is_rejected():
    token = issue_session_token("Student", 1)
    parts = token.split(".")
    parts[1] = parts[1][::-1]
    tampered = ".".join(parts)
    with pytest.raises(PermissionError):
        verify_session_token(tampered)


def test_missing_bearer_session_is_rejected():
    with pytest.raises(PermissionError):
        require_session(None, "Student", "1")


def test_session_role_header_mismatch_is_rejected():
    token = issue_session_token("Student", 1)
    with pytest.raises(PermissionError):
        require_session(f"Bearer {token}", "Advisor", None)


def test_session_student_scope_mismatch_is_rejected():
    token = issue_session_token("Student", 1)
    with pytest.raises(PermissionError):
        require_session(f"Bearer {token}", "Student", "2")


def test_expired_session_is_rejected():
    payload = {
        "role": "Student",
        "student_id": 1,
        "iat": int(time.time()) - 120,
        "exp": int(time.time()) - 60,
    }
    body = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    ).rstrip(b"=").decode("ascii")
    signature = base64.urlsafe_b64encode(
        hmac.new(SESSION_SECRET.encode(), body.encode(), hashlib.sha256).digest()
    ).rstrip(b"=").decode("ascii")
    token = f"ac1.{body}.{signature}"

    with pytest.raises(PermissionError):
        verify_session_token(token)
