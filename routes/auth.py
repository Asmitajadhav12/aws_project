"""Login and logout."""
from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from services.security import authenticate, login_user, logout_user

bp = Blueprint("auth", __name__)


def _safe_next(target: str | None) -> str:
    """Only allow same-site relative redirects (prevents open redirects)."""
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return url_for("dashboard.overview")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.get("user"):
        return redirect(url_for("dashboard.overview"))

    error = None
    username = ""
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        if not username or not password:
            error = "Enter both your username and password."
        else:
            user = authenticate(username, password)
            if user is None:
                error = "Those credentials were not recognised."
            else:
                login_user(user)
                flash(f"Signed in as {user['username']}.", "success")
                return redirect(_safe_next(request.args.get("next")))

    return render_template("auth/login.html", error=error, username=username)


@bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    flash("You have been signed out.", "success")
    return redirect(url_for("auth.login"))
