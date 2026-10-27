"""Every page must render with data present, and templates must compile."""
from __future__ import annotations

from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

PAGES = [
    "/",
    "/transactions",
    "/transactions/invoice/536365",
    "/alerts",
    "/alerts/1",
    "/rules",
    "/rules/tuning-lab",
    "/analysis",
    "/analysis/1",
    "/cancellations",
    "/product-trends",
    "/data",
    "/data/batches/1",
    "/simulator",
]


@pytest.mark.parametrize("path", PAGES)
def test_page_renders(admin_client, path):
    response = admin_client.get(path)
    assert response.status_code == 200, f"{path} returned {response.status_code}"
    assert b"<!doctype html>" in response.data.lower()


def test_login_page_renders(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Sign in" in response.data


def test_anonymous_user_is_redirected_to_login(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_unknown_invoice_returns_404(admin_client, monkeypatch):
    from services import db as db_module

    monkeypatch.setattr(db_module, "query_all", lambda sql, params=None: [])
    response = admin_client.get("/transactions/invoice/does-not-exist")
    assert response.status_code == 404


def test_healthz_reports_database_state(client, monkeypatch):
    from services import db as db_module

    monkeypatch.setattr(db_module, "is_available", lambda: True)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.get_json()["database"] == "connected"


def test_all_templates_compile():
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    failures = []
    for path in sorted(TEMPLATE_DIR.rglob("*.html")):
        name = path.relative_to(TEMPLATE_DIR).as_posix()
        try:
            env.parse(path.read_text(encoding="utf-8"), name=name)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{name}: {exc}")
    assert not failures, "Template syntax errors:\n" + "\n".join(failures)
