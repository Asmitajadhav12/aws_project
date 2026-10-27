"""Database-facing services: rules, analysis runs, alerts, imports, stats.

Keeping SQL here (and out of the route modules) means a route only has to
deal with HTTP concerns. Every statement is parameterised.
"""
from __future__ import annotations

import json
from datetime import datetime

import pandas as pd

from services import db
from services.data_cleaning import clean_transactions, to_insert_rows, validate_dataset
from services.rule_engine import RULE_CATALOGUE, RULE_ORDER, evaluate_rule

INSERT_TRANSACTION_SQL = """
INSERT IGNORE INTO transactions
    (import_batch_id, invoice_number, stock_code, description, quantity,
     invoice_date, unit_price, customer_id, country, is_cancellation,
     line_value, is_valid_sale, line_fingerprint)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


# ---------------------------------------------------------------- rules ----
def _loads(value):
    if value in (None, ""):
        return {}
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return {}


def list_rules() -> list[dict]:
    rows = db.query_all(
        "SELECT r.id, r.rule_code, r.rule_name, r.level, r.description, r.parameters, "
        "       r.is_enabled, r.updated_at, u.username AS updated_by "
        "FROM detection_rules r LEFT JOIN users u ON u.id = r.updated_by "
        "ORDER BY r.id"
    )
    for row in rows:
        row["parameters"] = _loads(row["parameters"])
        row["meta"] = RULE_CATALOGUE.get(row["rule_code"], {})
    return rows


def get_rule_row(rule_id: int):
    row = db.query_one(
        "SELECT id, rule_code, rule_name, level, description, parameters, is_enabled "
        "FROM detection_rules WHERE id = %s",
        (rule_id,),
    )
    if row:
        row["parameters"] = _loads(row["parameters"])
    return row


def get_rule_row_by_code(rule_code: str):
    row = db.query_one(
        "SELECT id, rule_code, rule_name, level, description, parameters, is_enabled "
        "FROM detection_rules WHERE rule_code = %s",
        (rule_code,),
    )
    if row:
        row["parameters"] = _loads(row["parameters"])
    return row


def enabled_configuration() -> dict:
    """rule_code -> parameters for every enabled rule."""
    rows = db.query_all(
        "SELECT rule_code, parameters FROM detection_rules WHERE is_enabled = 1"
    )
    return {row["rule_code"]: _loads(row["parameters"]) for row in rows}


def record_rule_version(rule_id: int, parameters: dict, user_id: int | None, note: str = "") -> int:
    """Snapshot the configuration so historical alerts stay explainable."""
    current = db.scalar(
        "SELECT COALESCE(MAX(version_no), 0) FROM rule_versions WHERE rule_id = %s",
        (rule_id,),
    )
    _, _ = db.execute(
        "INSERT INTO rule_versions (rule_id, version_no, parameters, changed_by, note) "
        "VALUES (%s, %s, %s, %s, %s)",
        (rule_id, int(current) + 1, json.dumps(parameters), user_id, note[:255]),
    )
    return int(db.scalar("SELECT MAX(id) FROM rule_versions WHERE rule_id = %s", (rule_id,)))


def update_rule(rule_id: int, parameters: dict, enabled: bool, user_id: int) -> int:
    version_id = record_rule_version(rule_id, parameters, user_id, note="Configuration change")
    db.execute(
        "UPDATE detection_rules SET parameters = %s, is_enabled = %s, updated_by = %s "
        "WHERE id = %s",
        (json.dumps(parameters), 1 if enabled else 0, user_id, rule_id),
    )
    return version_id


def toggle_rule(rule_id: int, enabled: bool, user_id: int) -> None:
    db.execute(
        "UPDATE detection_rules SET is_enabled = %s, updated_by = %s WHERE id = %s",
        (1 if enabled else 0, user_id, rule_id),
    )


def validate_parameters(rule_code: str, raw: dict) -> dict:
    """Coerce and sanity-check the values submitted from the rule form."""
    rule = RULE_CATALOGUE.get(rule_code)
    if rule is None:
        raise ValueError("Unknown rule.")
    defaults = rule["default_parameters"]
    cleaned = {}
    for name, default in defaults.items():
        if isinstance(default, bool):
            cleaned[name] = bool(raw.get(name))
            continue
        value = raw.get(name, default)
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{rule['parameter_labels'].get(name, name)} must be a number.") from exc
        if number <= 0:
            raise ValueError(f"{rule['parameter_labels'].get(name, name)} must be greater than zero.")
        if isinstance(default, int) and float(default).is_integer():
            if not float(number).is_integer():
                raise ValueError(
                    f"{rule['parameter_labels'].get(name, name)} must be a whole number."
                )
            cleaned[name] = int(number)
        else:
            cleaned[name] = round(number, 4)
    return cleaned


# ---------------------------------------------------------- transactions ----
def load_transactions_dataframe(limit: int | None = None) -> pd.DataFrame:
    sql = (
        "SELECT id, invoice_number, stock_code, description, quantity, invoice_date, "
        "       unit_price, customer_id, country, is_cancellation, line_value, is_valid_sale "
        "FROM transactions ORDER BY invoice_date"
    )
    params = None
    if limit:
        sql += " LIMIT %s"
        params = (int(limit),)
    rows = db.query_all(sql, params)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["invoice_date"] = pd.to_datetime(df["invoice_date"])
    df["quantity"] = pd.to_numeric(df["quantity"])
    df["unit_price"] = pd.to_numeric(df["unit_price"])
    df["line_value"] = pd.to_numeric(df["line_value"])
    df["is_valid_sale"] = df["is_valid_sale"].astype(bool)
    df["is_cancellation"] = df["is_cancellation"].astype(bool)
    df["customer_id"] = df["customer_id"].astype(object).where(df["customer_id"].notna(), None)
    return df


def dataset_is_loaded() -> bool:
    return int(db.scalar("SELECT COUNT(*) FROM transactions")) > 0


# -------------------------------------------------------- analysis runs ----
def create_analysis_run(run_type: str, rule_id, user_id, parameters: dict, rule_version_id=None) -> int:
    db.execute(
        "INSERT INTO analysis_runs (run_type, rule_id, initiated_by, status, "
        "parameters_snapshot, rule_version_id) VALUES (%s, %s, %s, 'running', %s, %s)",
        (run_type, rule_id, user_id, json.dumps(parameters), rule_version_id),
    )
    return int(db.scalar("SELECT MAX(id) FROM analysis_runs"))


def finish_analysis_run(run_id: int, status: str, summary: dict, error: str | None = None) -> None:
    db.execute(
        "UPDATE analysis_runs SET status = %s, summary = %s, error_message = %s, "
        "completed_at = %s WHERE id = %s",
        (status, json.dumps(summary), error, datetime.now(), run_id),
    )


def persist_alerts(run_id: int, rule_id: int, rule_version_id, alerts: list[dict]) -> int:
    if not alerts:
        return 0
    rows = [
        (
            run_id,
            rule_id,
            rule_version_id,
            alert.get("transaction_id"),
            alert.get("invoice_number"),
            alert.get("stock_code"),
            alert.get("customer_id"),
            alert.get("invoice_date"),
            alert.get("observed_value"),
            alert.get("threshold_value"),
            alert.get("explanation"),
        )
        for alert in alerts
    ]
    return db.execute_many(
        "INSERT INTO alerts (analysis_run_id, rule_id, rule_version_id, transaction_id, "
        "invoice_number, stock_code, customer_id, invoice_date, observed_value, "
        "threshold_value, explanation) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        rows,
    )


def run_analysis(rule_code: str, user_id: int, params: dict | None = None, limit: int | None = None) -> dict:
    """Evaluate one rule against the imported data and store the result."""
    rule_row = get_rule_row_by_code(rule_code)
    if rule_row is None:
        raise ValueError("That rule is not present in detection_rules.")

    parameters = {**rule_row["parameters"], **(params or {})}
    version_id = db.scalar(
        "SELECT MAX(id) FROM rule_versions WHERE rule_id = %s", (rule_row["id"],), default=None
    )
    run_id = create_analysis_run("full_scan", rule_row["id"], user_id, parameters, version_id)

    try:
        df = load_transactions_dataframe(limit=limit)
        if df.empty:
            finish_analysis_run(run_id, "completed", {"alert_count": 0, "note": "No transactions imported."})
            return {"run_id": run_id, "alert_count": 0, "evaluated_rows": 0}
        outcome = evaluate_rule(rule_code, df, parameters)
        stored = persist_alerts(run_id, rule_row["id"], version_id, outcome["alerts"])
        summary = {
            "rule_code": rule_code,
            "rule_name": rule_row["rule_name"],
            "alert_count": outcome["alert_count"],
            "evaluated_rows": outcome["evaluated_rows"],
            "alerts_stored": stored,
            "parameters": parameters,
        }
        finish_analysis_run(run_id, "completed", summary)
        return {"run_id": run_id, **summary}
    except Exception as exc:  # noqa: BLE001 - recorded for the analyst, not hidden
        finish_analysis_run(run_id, "failed", {}, error=str(exc)[:500])
        raise


def list_analysis_runs(limit: int = 50) -> list[dict]:
    rows = db.query_all(
        "SELECT r.id, r.run_type, r.status, r.started_at, r.completed_at, r.summary, "
        "       r.error_message, d.rule_code, d.rule_name, u.username AS initiated_by "
        "FROM analysis_runs r "
        "LEFT JOIN detection_rules d ON d.id = r.rule_id "
        "LEFT JOIN users u ON u.id = r.initiated_by "
        "ORDER BY r.id DESC LIMIT %s",
        (limit,),
    )
    # MySQL returns JSON columns as strings; parse them so templates can use
    # run.summary.alert_count instead of choking on a str.
    for row in rows:
        row["summary"] = _loads(row.get("summary"))
    return rows



def get_analysis_run(run_id: int):
    row = db.query_one(
        "SELECT r.*, d.rule_code, d.rule_name, u.username AS initiated_by "
        "FROM analysis_runs r "
        "LEFT JOIN detection_rules d ON d.id = r.rule_id "
        "LEFT JOIN users u ON u.id = r.initiated_by "
        "WHERE r.id = %s",
        (run_id,),
    )
    if row:
        row["summary"] = _loads(row.get("summary"))
        row["parameters_snapshot"] = _loads(row.get("parameters_snapshot"))
    return row


# --------------------------------------------------------------- alerts ----
def list_alerts(status: str | None = None, rule_code: str | None = None, limit: int = 100) -> list[dict]:
    clauses, params = [], []
    if status in {"open", "under_review", "reviewed"}:
        clauses.append("a.review_status = %s")
        params.append(status)
    if rule_code:
        clauses.append("d.rule_code = %s")
        params.append(rule_code)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(limit)
    return db.query_all(
        f"SELECT a.id, a.invoice_number, a.stock_code, a.customer_id, a.invoice_date, "
        f"       a.observed_value, a.threshold_value, a.explanation, a.review_status, "
        f"       a.created_at, d.rule_code, d.rule_name, rv.version_no "
        f"FROM alerts a "
        f"JOIN detection_rules d ON d.id = a.rule_id "
        f"LEFT JOIN rule_versions rv ON rv.id = a.rule_version_id "
        f"{where} ORDER BY a.id DESC LIMIT %s",
        tuple(params),
    )


def get_alert(alert_id: int):
    row = db.query_one(
        "SELECT a.*, d.rule_code, d.rule_name, rv.version_no, rv.parameters AS version_parameters "
        "FROM alerts a JOIN detection_rules d ON d.id = a.rule_id "
        "LEFT JOIN rule_versions rv ON rv.id = a.rule_version_id WHERE a.id = %s",
        (alert_id,),
    )
    if row:
        row["version_parameters"] = _loads(row.get("version_parameters"))
    return row


def review_alert(alert_id: int, status: str, user_id: int) -> None:
    if status not in {"open", "under_review", "reviewed"}:
        raise ValueError("Unknown review status.")
    db.execute(
        "UPDATE alerts SET review_status = %s, reviewed_by = %s, reviewed_at = %s WHERE id = %s",
        (status, user_id, datetime.now(), alert_id),
    )



def list_alerts_for_run(run_id: int, limit: int = 500) -> list[dict]:
    """Alerts produced by one specific analysis run."""
    return db.query_all(
        "SELECT a.id, a.invoice_number, a.stock_code, a.customer_id, a.observed_value, "
        "       a.threshold_value, a.explanation, a.review_status, d.rule_code "
        "FROM alerts a JOIN detection_rules d ON d.id = a.rule_id "
        "WHERE a.analysis_run_id = %s ORDER BY a.observed_value DESC LIMIT %s",
        (run_id, limit),
    )

def alerts_for_invoice(invoice_number: str) -> list[dict]:
    return db.query_all(
        "SELECT a.id, a.observed_value, a.threshold_value, a.explanation, a.review_status, "
        "       d.rule_code, d.rule_name "
        "FROM alerts a JOIN detection_rules d ON d.id = a.rule_id "
        "WHERE a.invoice_number = %s ORDER BY a.id DESC",
        (invoice_number,),
    )


# --------------------------------------------------------------- import ----
def import_dataframe(df: pd.DataFrame, file_name: str, user_id: int, source_note: str = "") -> dict:
    """Validate, clean and load a dataset file into the transactions table."""
    report = validate_dataset(df)
    db.execute(
        "INSERT INTO import_batches (file_name, source_note, row_count, status, "
        "validation_report, imported_by) VALUES (%s, %s, %s, 'pending', %s, %s)",
        (file_name[:255], source_note[:255], report["total_rows"], json.dumps(report), user_id),
    )
    batch_id = int(db.scalar("SELECT MAX(id) FROM import_batches"))

    try:
        cleaned = clean_transactions(df)
        cleaned["import_batch_id"] = batch_id
        chunk = 5000
        inserted = 0
        for start in range(0, len(cleaned), chunk):
            part = cleaned.iloc[start:start + chunk]
            inserted += db.execute_many(INSERT_TRANSACTION_SQL, list(to_insert_rows(part)))
        rejected = int(report["total_rows"]) - inserted
        db.execute(
            "UPDATE import_batches SET status = 'completed', imported_rows = %s, "
            "rejected_rows = %s WHERE id = %s",
            (inserted, max(rejected, 0), batch_id),
        )
        return {"batch_id": batch_id, "imported": inserted, "rejected": max(rejected, 0), "report": report}
    except Exception as exc:  # noqa: BLE001
        db.execute(
            "UPDATE import_batches SET status = 'failed', validation_report = %s WHERE id = %s",
            (json.dumps({**report, "error": str(exc)[:500]}), batch_id),
        )
        raise


def list_import_batches(limit: int = 20) -> list[dict]:
    return db.query_all(
        "SELECT b.id, b.file_name, b.row_count, b.imported_rows, b.rejected_rows, "
        "       b.status, b.created_at, u.username AS imported_by "
        "FROM import_batches b LEFT JOIN users u ON u.id = b.imported_by "
        "ORDER BY b.id DESC LIMIT %s",
        (limit,),
    )


def get_import_batch(batch_id: int):
    row = db.query_one("SELECT * FROM import_batches WHERE id = %s", (batch_id,))
    if row:
        row["validation_report"] = _loads(row.get("validation_report"))
    return row


# ---------------------------------------------------------------- stats ----
def dashboard_stats() -> dict:
    totals = db.query_one(
        "       SELECT COUNT(*) AS line_count, COUNT(DISTINCT invoice_number) AS invoices, "
        "       COUNT(DISTINCT customer_id) AS customers, "
        "       COUNT(DISTINCT stock_code) AS products, "
        "       MIN(invoice_date) AS first_date, MAX(invoice_date) AS last_date, "
        "       SUM(is_cancellation) AS cancellation_lines, "
        "       SUM(CASE WHEN is_valid_sale = 1 THEN line_value ELSE 0 END) AS sale_value "
        "FROM transactions"
    ) or {}
    alerts = db.query_one(
        "SELECT COUNT(*) AS total, "
        "       SUM(review_status = 'open') AS open_count, "
        "       SUM(review_status = 'under_review') AS review_count, "
        "       SUM(review_status = 'reviewed') AS reviewed_count "
        "FROM alerts"
    ) or {}
    by_rule = db.query_all(
        "SELECT d.rule_code, d.rule_name, COUNT(a.id) AS alert_count "
        "FROM detection_rules d LEFT JOIN alerts a ON a.rule_id = d.id "
        "GROUP BY d.id, d.rule_code, d.rule_name ORDER BY alert_count DESC"
    )
    return {
        "totals": totals,
        "alerts": alerts,
        "alerts_by_rule": by_rule,
        "recent_runs": list_analysis_runs(limit=5),
        "rule_count": len(RULE_ORDER),
    }
