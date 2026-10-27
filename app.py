"""Application entry point.

Run locally with:
    flask --app app run --debug
or:
    python app.py

The MySQL schema is NOT created automatically. Execute database/schema.sql
first (see database/README.md), then start the application.
"""
from __future__ import annotations

import getpass
import sys

import click
from flask import Flask, jsonify, render_template
from werkzeug.exceptions import HTTPException
from werkzeug.security import generate_password_hash

from config import Config
from routes import register_blueprints
from services.db import DatabaseUnavailable, execute, init_app as init_db, query_one
from services.security import init_app as init_security


def create_app(config_object=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object)

    init_db(app)
    init_security(app)
    register_blueprints(app)
    _register_filters(app)
    _register_error_handlers(app)
    _register_cli(app)
    _register_healthcheck(app)
    return app


# --------------------------------------------------------------- filters ---
def _num(value):
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        try:
            return f"{float(value):,.2f}"
        except (TypeError, ValueError):
            return "—"


def _money(value):
    try:
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return "—"


def _dt(value, fmt="%d %b %Y, %H:%M"):
    if not value:
        return "—"
    try:
        return value.strftime(fmt)
    except AttributeError:
        return str(value)


def _date_only(value, fmt="%d %b %Y"):
    return _dt(value, fmt) if value else "—"


def _register_filters(app: Flask) -> None:
    app.jinja_env.filters["num"] = _num
    app.jinja_env.filters["money"] = _money
    app.jinja_env.filters["dt"] = _dt
    app.jinja_env.filters["date_only"] = _date_only


# ----------------------------------------------------------------- handlers --
def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(DatabaseUnavailable)
    def _database_unavailable(exc):
        return render_template("errors/database.html", message=str(exc)), 503

    @app.errorhandler(400)
    def _bad_request(exc):
        description = getattr(exc, "description", "The request could not be processed.")
        return render_template("errors/400.html", message=description), 400

    @app.errorhandler(403)
    def _forbidden(exc):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def _not_found(exc):
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def _too_large(exc):
        limit_mb = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
        return render_template(
            "errors/400.html",
            message=f"That upload is larger than the {limit_mb} MB limit.",
        ), 413

    @app.errorhandler(500)
    def _server_error(exc):
        app.logger.exception("Unhandled application error")
        return render_template("errors/500.html"), 500

    @app.errorhandler(Exception)
    def _unhandled(exc):
        if isinstance(exc, HTTPException):
            return exc
        app.logger.exception("Unhandled application error")
        return render_template("errors/500.html"), 500


# --------------------------------------------------------------------- CLI --
def _register_cli(app: Flask) -> None:
    @app.cli.command("check-db")
    def check_db():
        """Verify the database connection and print row counts per table."""
        tables = ["users", "detection_rules", "rule_versions", "transactions",
                  "import_batches", "analysis_runs", "alerts"]
        try:
            for table in tables:
                row = query_one(f"SELECT COUNT(*) AS n FROM {table}")
                click.echo(f"{table:<18} {row['n']:>10,} rows")
        except DatabaseUnavailable as exc:
            click.echo(f"FAILED: {exc}", err=True)
            sys.exit(1)
        except Exception as exc:  # noqa: BLE001
            click.echo(f"FAILED: {type(exc).__name__}: {exc}", err=True)
            sys.exit(1)
        click.echo("Database connection OK.")

    @app.cli.command("create-admin")
    @click.option("--username", prompt="Admin username")
    @click.option("--full-name", prompt="Full name", default="")
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin(username, full_name, password):
        """Create (or reactivate) an administrator account."""
        if len(password) < 8:
            click.echo("Use a password of at least 8 characters.", err=True)
            sys.exit(1)
        existing = query_one("SELECT id FROM users WHERE username = %s", (username,))
        password_hash = generate_password_hash(password)
        if existing:
            execute(
                "UPDATE users SET password_hash = %s, role = 'admin', is_active = 1 WHERE id = %s",
                (password_hash, existing["id"]),
            )
            click.echo(f"Updated existing user '{username}' as an active admin.")
        else:
            execute(
                "INSERT INTO users (username, full_name, password_hash, role) "
                "VALUES (%s, %s, %s, 'admin')",
                (username, full_name or None, password_hash),
            )
            click.echo(f"Created admin user '{username}'.")

    @app.cli.command("create-analyst")
    @click.option("--username", prompt="Analyst username")
    @click.option("--full-name", prompt="Full name", default="")
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_analyst(username, full_name, password):
        """Create an analyst account (read and investigate, no admin actions)."""
        if len(password) < 8:
            click.echo("Use a password of at least 8 characters.", err=True)
            sys.exit(1)
        execute(
            "INSERT INTO users (username, full_name, password_hash, role) "
            "VALUES (%s, %s, %s, 'analyst')",
            (username, full_name or None, generate_password_hash(password)),
        )
        click.echo(f"Created analyst user '{username}'.")


# ------------------------------------------------------------------ routes --
def _register_healthcheck(app: Flask) -> None:
    @app.route("/healthz")
    def healthz():
        from services.db import is_available

        connected = is_available()
        payload = {
            "status": "ok" if connected else "degraded",
            "database": "connected" if connected else "unavailable",
        }
        return jsonify(payload), 200 if connected else 503


app = create_app()


if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"])
