"""The rule engine.

Three transparent, configurable rules -- no machine learning, no scoring,
no black box. Every alert carries the observed value, the threshold it was
compared against, and a sentence explaining the comparison.

All rules operate on a cleaned DataFrame produced by
services.data_cleaning.clean_transactions().
"""
from __future__ import annotations

import numpy as np
import pandas as pd

RULE_HIGH_LINE_QTY = "HIGH_LINE_QTY"
RULE_HIGH_INVOICE_VALUE = "HIGH_INVOICE_VALUE"
RULE_PRODUCT_QTY_IQR = "PRODUCT_QTY_IQR"

# ---------------------------------------------------------------------------
# Catalogue: the single source of truth for rule metadata and defaults.
# The same structures seed database/schema.sql.
# ---------------------------------------------------------------------------
RULE_CATALOGUE = {
    RULE_HIGH_LINE_QTY: {
        "code": RULE_HIGH_LINE_QTY,
        "name": "Unusually high line quantity",
        "level": "line",
        "summary": (
            "Flags a single invoice line whose quantity exceeds an absolute "
            "limit set by the analyst. It is the simplest rule in the system "
            "and the easiest to explain during a review."
        ),
        "formula": "line.quantity > min_quantity",
        "default_parameters": {"min_quantity": 500},
        "parameter_labels": {"min_quantity": "Minimum quantity per line (units)"},
        "uses": ["quantity", "invoice_number", "stock_code"],
    },
    RULE_HIGH_INVOICE_VALUE: {
        "code": RULE_HIGH_INVOICE_VALUE,
        "name": "High-value invoice",
        "level": "invoice",
        "summary": (
            "Adds up the value of the eligible sale lines on each invoice and "
            "flags invoices above a configured value. Cancellation lines and "
            "non-positive prices are excluded from the total, so the figure is "
            "a review indicator rather than a settled payment amount."
        ),
        "formula": "SUM(quantity * unit_price) over valid sale lines > min_invoice_value",
        "default_parameters": {"min_invoice_value": 5000.0},
        "parameter_labels": {"min_invoice_value": "Minimum invoice value"},
        "uses": ["quantity", "unit_price", "invoice_number"],
    },
    RULE_PRODUCT_QTY_IQR: {
        "code": RULE_PRODUCT_QTY_IQR,
        "name": "Quantity far above product baseline (median + k x IQR)",
        "level": "product",
        "summary": (
            "Compares each sale line with the historical quantity distribution "
            "of the same product. The baseline is the product's median quantity "
            "plus k times its interquartile range, so a product that normally "
            "sells in small quantities is judged against its own history rather "
            "than against every other product."
        ),
        "formula": "quantity > median(history) + k * IQR(history)",
        "default_parameters": {"k": 1.5, "min_history": 20, "prior_only": True},
        "parameter_labels": {
            "k": "IQR multiplier (k)",
            "min_history": "Minimum prior observations per product",
            "prior_only": "Use only earlier lines as the baseline",
        },
        "uses": ["quantity", "stock_code", "invoice_date"],
    },
}

RULE_ORDER = [RULE_HIGH_LINE_QTY, RULE_HIGH_INVOICE_VALUE, RULE_PRODUCT_QTY_IQR]


def get_rule(rule_code: str) -> dict:
    rule = RULE_CATALOGUE.get(rule_code)
    if rule is None:
        raise KeyError(f"Unknown rule code: {rule_code}")
    return rule


def _require_columns(df: pd.DataFrame, columns) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(
            "The dataset is missing column(s) needed by this rule: " + ", ".join(missing)
        )


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure the derived columns exist even if the caller passed a raw frame."""
    from services.data_cleaning import clean_transactions

    if "is_valid_sale" not in df.columns:
        df = clean_transactions(df)
    return df


def _fmt(value) -> str:
    if isinstance(value, (int, np.integer)):
        return f"{int(value):,}"
    if isinstance(value, (float, np.floating)):
        return f"{value:,.2f}"
    return str(value)


def _customer(row) -> str:
    customer = row.get("customer_id")
    return "unknown customer" if customer in (None, "", np.nan) else f"customer {customer}"


# --------------------------------------------------------------- rule 1 ----
def evaluate_high_line_quantity(df: pd.DataFrame, params: dict | None = None) -> dict:
    params = {**RULE_CATALOGUE[RULE_HIGH_LINE_QTY]["default_parameters"], **(params or {})}
    threshold = float(params["min_quantity"])
    _require_columns(df, ["quantity", "invoice_number", "stock_code", "is_valid_sale"])

    eligible = df[df["is_valid_sale"]]
    flagged = eligible[eligible["quantity"] > threshold].sort_values("quantity", ascending=False)

    alerts = []
    for row in flagged.to_dict("records"):
        product = row.get("description") or row["stock_code"]
        alerts.append(
            {
                "transaction_id": row.get("id"),
                "invoice_number": row["invoice_number"],
                "stock_code": row["stock_code"],
                "customer_id": row.get("customer_id"),
                "invoice_date": _fmt_date(row.get("invoice_date")),
                "observed_value": float(row["quantity"]),
                "threshold_value": threshold,
                "explanation": (
                    f"Line quantity {_fmt(int(row['quantity']))} of {product} "
                    f"({row['stock_code']}) on invoice {row['invoice_number']} for "
                    f"{_customer(row)} is above the configured limit of "
                    f"{_fmt(int(threshold))} units."
                ),
            }
        )
    return {
        "rule_code": RULE_HIGH_LINE_QTY,
        "parameters": params,
        "evaluated_rows": int(len(eligible)),
        "alert_count": len(alerts),
        "alerts": alerts,
    }


# --------------------------------------------------------------- rule 2 ----
def evaluate_high_invoice_value(df: pd.DataFrame, params: dict | None = None) -> dict:
    params = {**RULE_CATALOGUE[RULE_HIGH_INVOICE_VALUE]["default_parameters"], **(params or {})}
    threshold = float(params["min_invoice_value"])
    _require_columns(df, ["quantity", "unit_price", "invoice_number", "is_valid_sale"])

    eligible = df[df["is_valid_sale"]].copy()
    if eligible.empty:
        return {
            "rule_code": RULE_HIGH_INVOICE_VALUE,
            "parameters": params,
            "evaluated_rows": 0,
            "alert_count": 0,
            "alerts": [],
        }

    grouped = (
        eligible.groupby("invoice_number", dropna=False)
        .agg(
            invoice_total=("line_value", "sum"),
            line_count=("line_value", "size"),
            invoice_date=("invoice_date", "min"),
            customer_id=("customer_id", "first"),
        )
        .reset_index()
    )
    flagged = grouped[grouped["invoice_total"] > threshold].sort_values(
        "invoice_total", ascending=False
    )

    alerts = []
    for row in flagged.to_dict("records"):
        invoice = row["invoice_number"]
        lines = eligible[eligible["invoice_number"] == invoice].nlargest(3, "line_value")
        contributors = "; ".join(
            f"{line['stock_code']} x{_fmt(int(line['quantity']))} = {_fmt(float(line['line_value']))}"
            for line in lines.to_dict("records")
        )
        alerts.append(
            {
                "transaction_id": None,
                "invoice_number": invoice,
                "stock_code": None,
                "customer_id": row.get("customer_id"),
                "invoice_date": _fmt_date(row.get("invoice_date")),
                "observed_value": float(row["invoice_total"]),
                "threshold_value": threshold,
                "explanation": (
                    f"Invoice {invoice} totals {_fmt(float(row['invoice_total']))} across "
                    f"{int(row['line_count'])} eligible sale lines, above the configured "
                    f"limit of {_fmt(threshold)}. Largest contributors: {contributors}. "
                    "Cancellation lines and non-positive prices are excluded from the total."
                ),
            }
        )
    return {
        "rule_code": RULE_HIGH_INVOICE_VALUE,
        "parameters": params,
        "evaluated_rows": int(len(grouped)),
        "alert_count": len(alerts),
        "alerts": alerts,
    }


# --------------------------------------------------------------- rule 3 ----
def product_baseline(df: pd.DataFrame, min_history: int = 20, prior_only: bool = True) -> pd.DataFrame:
    """Return per-line baseline statistics for each product.

    prior_only=True uses only lines that occurred *before* the line being
    evaluated (expanding window), which avoids leaking future data into the
    comparison. It is slower on the full dataset, so the Rule Tuning Lab can
    switch it off for quick sweeps.
    """
    _require_columns(df, ["quantity", "stock_code", "invoice_date", "is_valid_sale"])
    eligible = df[df["is_valid_sale"]].sort_values("invoice_date").copy()

    if eligible.empty:
        eligible["baseline_median"] = np.nan
        eligible["baseline_q3"] = np.nan
        eligible["baseline_q1"] = np.nan
        eligible["history_count"] = 0
        return eligible

    grouped = eligible.groupby("stock_code")["quantity"]

    if prior_only:
        def _stat(quantile):
            return grouped.transform(
                lambda s: s.shift().expanding(min_periods=max(1, min_history)).quantile(quantile)
            )

        eligible["baseline_median"] = _stat(0.5)
        eligible["baseline_q1"] = _stat(0.25)
        eligible["baseline_q3"] = _stat(0.75)
        eligible["history_count"] = grouped.transform(lambda s: s.shift().expanding().count())
    else:
        eligible["baseline_median"] = grouped.transform("median")
        eligible["baseline_q1"] = grouped.transform(lambda s: s.quantile(0.25))
        eligible["baseline_q3"] = grouped.transform(lambda s: s.quantile(0.75))
        eligible["history_count"] = grouped.transform("size")

    eligible["baseline_iqr"] = eligible["baseline_q3"] - eligible["baseline_q1"]
    return eligible


def evaluate_product_qty_iqr(df: pd.DataFrame, params: dict | None = None) -> dict:
    params = {**RULE_CATALOGUE[RULE_PRODUCT_QTY_IQR]["default_parameters"], **(params or {})}
    k = float(params["k"])
    min_history = int(params["min_history"])
    prior_only = bool(params.get("prior_only", True))

    scored = product_baseline(df, min_history=min_history, prior_only=prior_only)
    if scored.empty:
        return {
            "rule_code": RULE_PRODUCT_QTY_IQR,
            "parameters": params,
            "evaluated_rows": 0,
            "alert_count": 0,
            "alerts": [],
        }

    scored = scored[scored["history_count"] >= min_history]
    scored["upper_limit"] = scored["baseline_median"] + k * scored["baseline_iqr"]
    flagged = scored[scored["quantity"] > scored["upper_limit"]].sort_values(
        "quantity", ascending=False
    )

    alerts = []
    for row in flagged.to_dict("records"):
        product = row.get("description") or row["stock_code"]
        alerts.append(
            {
                "transaction_id": row.get("id"),
                "invoice_number": row["invoice_number"],
                "stock_code": row["stock_code"],
                "customer_id": row.get("customer_id"),
                "invoice_date": _fmt_date(row.get("invoice_date")),
                "observed_value": float(row["quantity"]),
                "threshold_value": float(row["upper_limit"]),
                "explanation": (
                    f"Quantity {_fmt(int(row['quantity']))} of {product} ({row['stock_code']}) "
                    f"on invoice {row['invoice_number']} is above this product's baseline limit "
                    f"of {_fmt(float(row['upper_limit']))} units, calculated as median "
                    f"{_fmt(float(row['baseline_median']))} + {k:g} x IQR "
                    f"{_fmt(float(row['baseline_iqr']))} from {int(row['history_count'])} "
                    f"{'earlier' if prior_only else 'historical'} sale lines."
                ),
            }
        )
    return {
        "rule_code": RULE_PRODUCT_QTY_IQR,
        "parameters": params,
        "evaluated_rows": int(len(scored)),
        "alert_count": len(alerts),
        "alerts": alerts,
    }


# ------------------------------------------------------------- dispatch ----
_EVALUATORS = {
    RULE_HIGH_LINE_QTY: evaluate_high_line_quantity,
    RULE_HIGH_INVOICE_VALUE: evaluate_high_invoice_value,
    RULE_PRODUCT_QTY_IQR: evaluate_product_qty_iqr,
}


def evaluate_rule(rule_code: str, df: pd.DataFrame, params: dict | None = None) -> dict:
    """Evaluate one rule and return a result dict with alerts and metadata."""
    if rule_code not in _EVALUATORS:
        raise KeyError(f"Unknown rule code: {rule_code}")
    prepared = _prepare(df)
    return _EVALUATORS[rule_code](prepared, params)


def evaluate_all(df: pd.DataFrame, configuration: dict | None = None) -> list[dict]:
    """Evaluate every rule in RULE_ORDER. configuration maps rule_code -> params."""
    configuration = configuration or {}
    return [
        evaluate_rule(code, df, configuration.get(code))
        for code in RULE_ORDER
    ]


def _fmt_date(value) -> str | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return pd.Timestamp(value).strftime("%Y-%m-%d %H:%M:%S")
