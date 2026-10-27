"""CSRF protection, role enforcement and login behaviour."""
from __future__ import annotations

from werkzeug.security import generate_password_hash


def test_post_without_csrf_token_is_rejected(admin_client):
    response = admin_client.post("/analysis/run", data={"rule_code": "HIGH_LINE_QTY"})
    assert response.status_code == 400


def test_post_with_wrong_csrf_token_is_rejected(admin_client):
    response = admin_client.post(
        "/analysis/run",
        data={"rule_code": "HIGH_LINE_QTY", "csrf_token": "wrong-token"},
    )
    assert response.status_code == 400


def test_admin_route_blocks_analyst(app, monkeypatch):
    from services import security as security_module

    monkeypatch.setattr(
        security_module, "query_one",
        lambda sql, params=None: {"id": 2, "username": "analyst", "full_name": "Analyst",
                                  "role": "analyst", "is_active": 1},
    )
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 2
        session["role"] = "analyst"
        session["_csrf_token"] = "token"
    response = client.get("/data")
    assert response.status_code == 403


def test_login_with_valid_credentials_sets_session(app, monkeypatch):
    from services import db as db_module
    from services import security as security_module

    hashed = generate_password_hash("correct-horse")
    monkeypatch.setattr(
        security_module, "query_one",
        lambda sql, params=None: {"id": 1, "username": "admin", "full_name": "Admin",
                                  "password_hash": hashed, "role": "admin", "is_active": 1},
    )
    client = app.test_client()
    client.get("/login")  # seeds the CSRF token in the session
    with client.session_transaction() as session:
        token = session["_csrf_token"]
    response = client.post(
        "/login",
        data={"username": "admin", "password": "correct-horse", "csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 302
    with client.session_transaction() as session:
        assert session["user_id"] == 1
        assert session["role"] == "admin"


def test_login_with_wrong_password_does_not_sign_in(app, monkeypatch):
    from services import security as security_module

    monkeypatch.setattr(
        security_module, "query_one",
        lambda sql, params=None: {"id": 1, "username": "admin", "full_name": "Admin",
                                  "password_hash": generate_password_hash("right"),
                                  "role": "admin", "is_active": 1},
    )
    client = app.test_client()
    client.get("/login")
    with client.session_transaction() as session:
        token = session["_csrf_token"]
    response = client.post(
        "/login",
        data={"username": "admin", "password": "wrong", "csrf_token": token},
    )
    assert response.status_code == 200
    assert b"not recognised" in response.data
    with client.session_transaction() as session:
        assert "user_id" not in session


def test_open_redirect_is_blocked(app, monkeypatch):
    from services import security as security_module

    monkeypatch.setattr(
        security_module, "query_one",
        lambda sql, params=None: {"id": 1, "username": "admin", "full_name": "Admin",
                                  "password_hash": generate_password_hash("pw"),
                                  "role": "admin", "is_active": 1},
    )
    client = app.test_client()
    client.get("/login?next=https://evil.example")
    with client.session_transaction() as session:
        token = session["_csrf_token"]
    response = client.post(
        "/login?next=https://evil.example",
        data={"username": "admin", "password": "pw", "csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "evil.example" not in response.headers["Location"]
