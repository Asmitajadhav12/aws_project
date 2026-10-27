"""Shared test fixtures.

The test suite deliberately does not need a MySQL server. A stub database layer
answers the handful of query shapes the pages use, so routes and Jinja
templates are exercised end to end without a live schema.
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import Config  # noqa: E402
from services import db as db_module  # noqa: E402
from services import security as security_module  # noqa: E402

NOW = dt.datetime(2011, 12, 9, 12, 30)
DATE = dt.date(2011, 12, 9)


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret-key"
    DB_HOST = "127.0.0.1"
    DB_USER = "test"
    DB_PASSWORD = "test"
    DB_NAME = "test_db"
    SESSION_COOKIE_SECURE = False


# --------------------------------------------------------------- stub data --
TOTALS = {
    "lines": 541909, "invoices": 25900, "customers": 4372, "products": 4070,
    "first_date": NOW, "last_date": NOW, "cancellation_lines": 9251,
    "sale_value": 9747747.93,
}
ALERT_COUNTS = {"total": 3, "open_count": 2, "review_count": 1, "reviewed_count": 0}
RULES = [
    {"id": 1, "rule_code": "HIGH_LINE_QTY", "rule_name": "Unusually high line quantity",
     "level": "line", "description": "Absolute quantity limit.",
     "parameters": {"min_quantity": 500}, "is_enabled": 1, "updated_at": NOW,
     "updated_by": "admin",
     "meta": {"formula": "line.quantity > min_quantity",
              "parameter_labels": {"min_quantity": "Minimum quantity per line (units)"}}},
    {"id": 2, "rule_code": "HIGH_INVOICE_VALUE", "rule_name": "High-value invoice",
     "level": "invoice", "description": "Invoice value limit.",
     "parameters": {"min_invoice_value": 5000.0}, "is_enabled": 1, "updated_at": NOW,
     "updated_by": "admin",
     "meta": {"formula": "SUM(line_value) > min_invoice_value",
              "parameter_labels": {"min_invoice_value": "Minimum invoice value"}}},
    {"id": 3, "rule_code": "PRODUCT_QTY_IQR", "rule_name": "Quantity far above product baseline",
     "level": "product", "description": "Median + k x IQR baseline.",
     "parameters": {"k": 1.5, "min_history": 20, "prior_only": True}, "is_enabled": 1,
     "updated_at": NOW, "updated_by": "admin",
     "meta": {"formula": "quantity > median + k * IQR",
              "parameter_labels": {"k": "IQR multiplier (k)",
                                   "min_history": "Minimum prior observations",
                                   "prior_only": "Prior only"}}},
]
ALERTS = [
    {"id": 1, "invoice_number": "536365", "stock_code": "22423", "customer_id": "17850",
     "invoice_date": NOW, "observed_value": 1200.0, "threshold_value": 500.0,
     "explanation": "Line quantity 1,200 exceeds 500.", "review_status": "open",
     "created_at": NOW, "rule_code": "HIGH_LINE_QTY", "rule_name": "Unusually high line quantity",
     "version_no": 1, "analysis_run_id": 1, "analysis_run_id_alias": 1},
]
RUNS = [
    {"id": 1, "run_type": "full_scan", "status": "completed", "started_at": NOW,
     "completed_at": NOW, "summary": {"alert_count": 1, "evaluated_rows": 100},
     "error_message": None, "rule_code": "HIGH_LINE_QTY",
     "rule_name": "Unusually high line quantity", "initiated_by": "admin",
     "rule_version_id": 1, "parameters_snapshot": {"min_quantity": 500}},
]
LINES = [
    {"id": 1, "stock_code": "22423", "description": "REGENCY CAKESTAND 3 TIER",
     "quantity": 12, "unit_price": 9.95, "line_value": 119.40, "invoice_date": NOW,
     "customer_id": "17850", "country": "United Kingdom", "is_cancellation": 0,
     "is_valid_sale": 1, "invoice_number": "536365", "flagged": 1},
]
BATCHES = [
    {"id": 1, "file_name": "Online Retail.xlsx", "row_count": 541909, "imported_rows": 536641,
     "rejected_rows": 5268, "status": "completed", "created_at": NOW, "imported_by": "admin"},
]
BATCH = {
    "id": 1, "file_name": "Online Retail.xlsx", "row_count": 541909, "imported_rows": 536641,
    "rejected_rows": 5268, "status": "completed", "created_at": NOW, "imported_by": "admin",
    "validation_report": {
        "total_rows": 541909, "total_columns": 8, "duplicate_rows": 5268,
        "rows_after_cleaning": 536641, "distinct_invoices": 25900, "distinct_products": 4070,
        "distinct_customers": 4372, "positive_quantity_rows": 531282,
        "non_positive_quantity_rows": 10627, "cancellation_invoice_rows": 9251,
        "cancellation_invoice_pct": 1.71, "non_positive_price_rows": 2515,
        "missing_customer_rows": 135080, "missing_customer_pct": 24.93,
        "date_min": "2010-12-01 08:26:00", "date_max": "2011-12-09 12:50:00",
        "columns": [{"name": "invoice_number", "dtype": "object"}],
        "missing_values": {"customer_id": 135080},
    },
}


def respond(sql: str, params=None):
    """Answer a query by inspecting its shape. Mirrors the real SQL closely."""
    s = " ".join(sql.split())
    if "COUNT(*) AS lines" in s:
        return TOTALS
    if "AS open_count" in s:
        return ALERT_COUNTS
    if "GROUP BY d.id, d.rule_code, d.rule_name" in s:
        return [{"rule_code": "HIGH_LINE_QTY", "rule_name": "Unusually high line quantity",
                 "alert_count": 3}]
    if "SELECT a.*, d.rule_code, d.rule_name, rv.version_no" in s:
        return {**ALERTS[0], "version_parameters": {"min_quantity": 500}}
    if "SELECT r.*, d.rule_code" in s:
        return RUNS[0]
    if "analysis_run_id = %s ORDER BY" in s:
        return ALERTS
    if "FROM alerts a JOIN detection_rules d ON d.id = a.rule_id WHERE a.invoice_number" in s:
        return ALERTS
    if "FROM alerts a JOIN detection_rules d ON d.id = a.rule_id" in s:
        return ALERTS
    if "FROM alerts a JOIN detection_rules d ON d.id = a.rule_id LEFT JOIN" in s:
        return ALERTS
    if "FROM detection_rules r LEFT JOIN users u" in s:
        return RULES
    if "FROM analysis_runs r" in s:
        return RUNS
    if "SELECT DISTINCT country" in s:
        return [{"country": "United Kingdom"}, {"country": "Germany"}]
    if "SELECT COUNT(*) FROM transactions t" in s:
        return {"n": 1}
    if "SELECT t.id, t.invoice_number" in s:
        return LINES
    if "FROM transactions WHERE invoice_number = %s" in s:
        return LINES
    if "FROM transactions ORDER BY invoice_date" in s:
        return LINES
    if "SELECT COUNT(*) FROM transactions" in s:
        return {"n": 1}
    if "SELECT * FROM import_batches WHERE id" in s:
        return BATCH
    if "FROM import_batches b" in s:
        return BATCHES
    if "AS month" in s:
        return [{"month": "2011-12", "cancellation_lines": 100, "total_lines": 5000}]
    if "COUNT(*) AS total_lines" in s:
        return {"total_lines": 541909, "cancellation_lines": 9251,
                "cancellation_invoices": 9251, "customers_with_cancellations": 3344}
    if "AS cancellation_lines, COUNT(*) AS total_lines" in s:
        return [{"month": "2011-12", "cancellation_lines": 100, "total_lines": 5000}]
    if "cancelled_value" in s:
        return [{"customer_id": "17850", "cancellation_lines": 12, "cancelled_value": -350.0}]
    if "cancelled_quantity" in s:
        return [{"stock_code": "22423", "description": "REGENCY CAKESTAND", "cancellation_lines": 8}]
    if "SELECT DISTINCT DATE_FORMAT" in s:
        return [{"month": "2011-12"}, {"month": "2011-11"}]
    if "current_qty" in s:
        return [{"stock_code": "22423", "description": "REGENCY CAKESTAND",
                 "current_qty": 120, "previous_qty": 100}]
    if "SELECT rule_code, parameters FROM detection_rules" in s:
        return [{"rule_code": "HIGH_LINE_QTY", "parameters": '{"min_quantity": 500}'},
                {"rule_code": "HIGH_INVOICE_VALUE", "parameters": '{"min_invoice_value": 5000.0}'},
                {"rule_code": "PRODUCT_QTY_IQR",
                 "parameters": '{"k": 1.5, "min_history": 20, "prior_only": true}'}]
    if "FROM detection_rules WHERE rule_code = %s" in s:
        return RULES[0]
    if "FROM detection_rules WHERE id = %s" in s:
        return RULES[0]
    if "FROM users WHERE id = %s" in s:
        return {"id": 1, "username": "admin", "full_name": "Asmita Jadhav",
                "role": "admin", "is_active": 1}
    if "FROM users WHERE username = %s" in s:
        return None
    return None


@pytest.fixture()
def app(monkeypatch):
    from app import create_app

    application = create_app(TestConfig)

    monkeypatch.setattr(db_module, "query_all", lambda sql, params=None: respond(sql, params) or [])
    monkeypatch.setattr(db_module, "query_one", lambda sql, params=None: respond(sql, params))
    monkeypatch.setattr(db_module, "scalar", lambda sql, params=None, default=0: _scalar(sql))
    monkeypatch.setattr(db_module, "execute", lambda sql, params=None: (1, 1))
    monkeypatch.setattr(db_module, "execute_many", lambda sql, seq: len(seq))
    monkeypatch.setattr(security_module, "query_one", lambda sql, params=None: respond(sql, params))
    return application


def _scalar(sql):
    result = respond(sql)
    if isinstance(result, dict):
        return next(iter(result.values()), 0)
    return 1


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def admin_client(app):
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["username"] = "admin"
        session["role"] = "admin"
        session["_csrf_token"] = "test-token"
    return client
