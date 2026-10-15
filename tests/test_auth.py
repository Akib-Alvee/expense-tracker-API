from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings
from app.security import create_access_token


def test_signup_returns_user_without_password(client):
    r = client.post("/auth/signup", json={"email": "a@example.com", "password": "password123"})
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "a@example.com"
    assert "password" not in body and "password_hash" not in body


def test_signup_duplicate_email_is_409_case_insensitive(client):
    client.post("/auth/signup", json={"email": "a@example.com", "password": "password123"})
    r = client.post("/auth/signup", json={"email": "A@Example.com", "password": "password123"})
    assert r.status_code == 409


def test_signup_validation(client):
    assert client.post("/auth/signup", json={"email": "nope", "password": "password123"}).status_code == 422
    assert client.post("/auth/signup", json={"email": "a@example.com", "password": "short"}).status_code == 422


def test_login_success_returns_bearer_token(client, make_user):
    make_user("a@example.com")
    r = client.post("/auth/login", data={"username": "a@example.com", "password": "password123"})
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"
    assert r.json()["access_token"]


def test_login_failures_are_indistinguishable(client, make_user):
    make_user("a@example.com")
    wrong_password = client.post("/auth/login", data={"username": "a@example.com", "password": "wrongpass1"})
    unknown_email = client.post("/auth/login", data={"username": "ghost@example.com", "password": "password123"})
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_me_requires_token(client):
    assert client.get("/auth/me").status_code == 401


def test_me_with_valid_token(client, make_user):
    headers = make_user("a@example.com")
    r = client.get("/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == "a@example.com"


def test_garbage_token_rejected(client):
    r = client.get("/auth/me", headers={"Authorization": "Bearer not.a.token"})
    assert r.status_code == 401


def test_expired_token_rejected(client, make_user):
    make_user()
    expired = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401


def test_token_signed_with_wrong_key_rejected(client, make_user):
    make_user()
    forged = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        "x" * 32,
        algorithm=settings.algorithm,
    )
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 401


def test_valid_token_for_nonexistent_user_rejected(client):
    token = create_access_token(9999)  # correctly signed, but no such user
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401