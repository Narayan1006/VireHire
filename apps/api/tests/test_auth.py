"""
Tests for authentication: registration, login, JWT validation, rate limiting, and security rules
"""

from datetime import datetime, timedelta, timezone
import jwt

from app.config import get_settings


def test_register_success(client):
    res = client.post(
        "/auth/register",
        json={"email": "Test.User@example.com", "password": "Password123!"},
    )
    assert res.status_code == 201
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "test.user@example.com"
    assert "password" not in data
    assert "password_hash" not in data


def test_register_duplicate_email_409(client):
    client.post(
        "/auth/register",
        json={"email": "duplicate@example.com", "password": "Password123!"},
    )
    res = client.post(
        "/auth/register",
        json={"email": "DUPLICATE@example.com", "password": "Password123!"},
    )
    assert res.status_code == 409
    assert res.json()["detail"] == "An account with this email already exists"


def test_register_weak_password_rejected(client):
    # Too short (< 8 chars)
    res_short = client.post(
        "/auth/register",
        json={"email": "short@example.com", "password": "short"},
    )
    assert res_short.status_code == 422
    assert "Password must be between 8 and 128 characters" in res_short.json()["detail"]
    assert "short" not in res_short.json()["detail"]

    # Too long (> 128 chars)
    res_long = client.post(
        "/auth/register",
        json={"email": "long@example.com", "password": "a" * 129},
    )
    assert res_long.status_code == 422
    assert "Password must be between 8 and 128 characters" in res_long.json()["detail"]


def test_login_success(client):
    client.post(
        "/auth/register",
        json={"email": "login@example.com", "password": "Password123!"},
    )
    res = client.post(
        "/auth/login",
        json={"email": "login@example.com", "password": "Password123!"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "password" not in data


def test_wrong_password_and_unknown_email_return_identical_response(client):
    client.post(
        "/auth/register",
        json={"email": "existing@example.com", "password": "Password123!"},
    )

    # Wrong password for existing user
    res_wrong_pw = client.post(
        "/auth/login",
        json={"email": "existing@example.com", "password": "WrongPassword123!"},
    )

    # Non-existent user
    res_unknown_user = client.post(
        "/auth/login",
        json={"email": "nonexistent@example.com", "password": "Password123!"},
    )

    assert res_wrong_pw.status_code == 401
    assert res_unknown_user.status_code == 401
    assert res_wrong_pw.json() == res_unknown_user.json()
    assert res_wrong_pw.json() == {"detail": "Invalid email or password"}


def test_expired_token_401(client):
    settings = get_settings()
    past = datetime.now(timezone.utc) - timedelta(hours=2)
    expired_token = jwt.encode(
        {"sub": "00000000-0000-0000-0000-000000000001", "exp": int(past.timestamp()), "iat": int(past.timestamp()) - 3600},
        settings.jwt_secret,
        algorithm="HS256",
    )

    res = client.get("/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Token has expired"


def test_tampered_token_401(client):
    reg = client.post(
        "/auth/register",
        json={"email": "tamper@example.com", "password": "Password123!"},
    )
    token = reg.json()["access_token"]
    tampered = token[:-4] + "abcd"

    res = client.get("/me", headers={"Authorization": f"Bearer {tampered}"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid token"


def test_token_with_alg_none_rejected(client):
    # Construct an unverified/alg:none token
    header = {"alg": "none", "typ": "JWT"}
    payload = {"sub": "00000000-0000-0000-0000-000000000001", "exp": int(datetime.now(timezone.utc).timestamp()) + 3600}
    import base64
    import json

    def b64(data):
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")

    none_token = f"{b64(header)}.{b64(payload)}."

    res = client.get("/me", headers={"Authorization": f"Bearer {none_token}"})
    assert res.status_code == 401


def test_login_rate_limiting_429(client):
    # Attempt 5 wrong logins
    for _ in range(5):
        res = client.post(
            "/auth/login",
            json={"email": "brute@example.com", "password": "WrongPassword123!"},
        )
        assert res.status_code == 401

    # 6th attempt should be blocked with 429
    res_blocked = client.post(
        "/auth/login",
        json={"email": "brute@example.com", "password": "WrongPassword123!"},
    )
    assert res_blocked.status_code == 429
    assert "Too many failed login attempts" in res_blocked.json()["detail"]
    assert "Retry-After" in res_blocked.headers


def test_password_never_appears_in_responses(client):
    secret_pw = "SuperSecretPassword123!"
    reg = client.post(
        "/auth/register",
        json={"email": "secret@example.com", "password": secret_pw},
    )
    assert secret_pw not in reg.text

    login = client.post(
        "/auth/login",
        json={"email": "secret@example.com", "password": secret_pw},
    )
    assert secret_pw not in login.text

    failed = client.post(
        "/auth/login",
        json={"email": "secret@example.com", "password": "WrongPassword123!"},
    )
    assert "WrongPassword123!" not in failed.text
