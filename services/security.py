"""Authentication, authorisation and CSRF protection.

Authentication is session based (server-side session cookie signed with
SECRET_KEY). Passwords are stored only as Werkzeug hashes.

Known limitations -- documented honestly rather than hidden:
* There is no account lockout or rate limiting on the login form.
* Sessions are not invalidated server-side on logout beyond clearing the
  cookie, so a stolen cookie stays valid until it expires.
* Password reset, 2FA and audit logging of admin actions are out of scope.
"""
from __future__ import annotations

import hmac
import secrets
from functools import wraps

from flask import abort, flash, g, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from services.db import query_one

CSRF_SESSION_KEY = "_csrf_token"
CSRF_FORM_FIELD = "csrf_token"
CSRF_HEADER = "X-CSRF-Token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}

ROLE_ADMIN = "admin"
ROLE_ANALYST = "analyst"


# ---------------------------------------------------------------- CSRF ----
def csrf_token() -> str:
    """Return the per-session CSRF token, creating it on first use."""
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def _csrf_is_valid() -> bool:
    expected = session.get(CSRF_SESSION_KEY)
    supplied = request.form.get(CSRF_FORM_FIELD) or request.headers.get(CSRF_HEADER)
    if not expected or not supplied:
        return False
    return hmac.compare_digest(str(expected), str(supplied))


# --------------------------------------------------------- authentication ----
def authenticate(username: str, password: str):
    """Return the user row for valid credentials, otherwise None."""
    if not username or not password:
        return None
    row = query_one(
        "SELECT id, username, full_name, password_hash, role, is_active "
        "FROM users WHERE username = %s",
        (username.strip(),),
    )
    if row is None or not row["is_active"]:
        return None
    if not check_password_hash(row["password_hash"], password):
        return None
    return row


def login_user(user) -> None:
    session.clear()
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["role"] = user["role"]
    session.permanent = True
    csrf_token()


def logout_user() -> None:
    session.clear()


def load_logged_in_user() -> None:
    g.user = None
    user_id = session.get("user_id")
    if user_id is None:
        return
    user = query_one(
        "SELECT id, username, full_name, role, is_active FROM users WHERE id = %s",
        (user_id,),
    )
    if user is None or not user["is_active"]:
        session.clear()
        return
    g.user = user


# -------------------------------------------------------- authorisation ----
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.get("user") is None:
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def role_required(*roles):
    """Restrict a route to the given roles. Enforced on the server."""

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if g.get("user") is None:
                flash("Please sign in to continue.", "warning")
                return redirect(url_for("auth.login", next=request.path))
            if g.user["role"] not in roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def admin_required(view):
    return role_required(ROLE_ADMIN)(view)


# ------------------------------------------------------------------ wiring ----
def _before_request():
    if request.method not in SAFE_METHODS and not _csrf_is_valid():
        abort(400, description="The form expired or the CSRF token was missing.")
    load_logged_in_user()


def init_app(app):
    app.before_request(_before_request)
    app.jinja_env.globals["csrf_token"] = csrf_token
    app.jinja_env.globals["ROLE_ADMIN"] = ROLE_ADMIN
    app.jinja_env.globals["ROLE_ANALYST"] = ROLE_ANALYST
