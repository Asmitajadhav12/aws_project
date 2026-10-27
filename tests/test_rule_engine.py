"""Unit tests for the detection rules -- no database, no web layer."""
from __future__ import annotations

import pandas as pd
import pytest

from services.rule_engine import (
    RULE_HIGH_INVOICE_VALUE, RULE_HIGH_LINE_QTY, RULE_PRODUCT_QTY_IQR,
    evaluate_high_invoice_value, evaluate_high_line_quantity,
    evaluate_product_qty_iqr, evaluate_rule, get_rule,
)


def frame(rows):
    df = pd.DataFrame(
        rows,
        columns=["invoice_number", "stock_code", "description", "quantity",
                 "invoice_date", "unit_price", "customer_id"],
    )
    df["invoice_date"] = pd.to_datetime(df["invoice_date"])
    df["customer_id"] = df["customer_id"].astype(object)
    # Derive the flags the same way the cleaning pipeline does.
    df["is_cancellation"] = df["invoice_number"].str.startswith("C")
    df["is_valid_sale"] = (~df["is_cancellation"]) & (df["quantity"] > 0) & (df["unit_price"] > 0)
    df["line_value"] = (df["quantity"] * df["unit_price"]).round(2)
    return df


def test_catalogue_has_three_rules():
    for code in (RULE_HIGH_LINE_QTY, RULE_HIGH_INVOICE_VALUE, RULE_PRODUCT_QTY_IQR):
        rule = get_rule(code)
        assert rule["code"] == code
        assert rule["default_parameters"]


def test_high_line_quantity_flags_only_above_threshold():
    df = frame([
        ("1001", "A", "Widget", 600, "2011-01-01 09:00", 2.0, "1"),
        ("1002", "A", "Widget", 100, "2011-01-02 09:00", 2.0, "1"),
    ])
    result = evaluate_high_line_quantity(df, {"min_quantity": 500})
    assert result["alert_count"] == 1
    alert = result["alerts"][0]
    assert alert["invoice_number"] == "1001"
    assert alert["observed_value"] == 600
    assert alert["threshold_value"] == 500
    assert "above the configured limit of 500" in alert["explanation"]


def test_high_line_quantity_ignores_cancellations_and_zero_prices():
    df = frame([
        ("C1003", "A", "Widget", 900, "2011-01-03 09:00", 2.0, "1"),   # cancellation
        ("1004", "A", "Sample", 900, "2011-01-04 09:00", 0.0, "1"),    # free line
    ])
    result = evaluate_high_line_quantity(df, {"min_quantity": 500})
    assert result["alert_count"] == 0


def test_high_invoice_value_sums_only_eligible_lines():
    df = frame([
        ("2001", "A", "Widget", 100, "2011-02-01 09:00", 30.0, "7"),   # 3000
        ("2001", "B", "Gadget", 100, "2011-02-01 09:00", 30.0, "7"),   # 3000 -> total 6000
        ("2002", "A", "Widget", 10, "2011-02-02 09:00", 30.0, "7"),    # 300
    ])
    result = evaluate_high_invoice_value(df, {"min_invoice_value": 5000})
    assert result["alert_count"] == 1
    alert = result["alerts"][0]
    assert alert["invoice_number"] == "2001"
    assert alert["observed_value"] == pytest.approx(6000.0)
    assert "Cancellation lines" in alert["explanation"]


def test_high_invoice_value_excludes_cancellation_credit():
    df = frame([
        ("3001", "A", "Widget", 100, "2011-03-01 09:00", 60.0, "9"),   # 6000
        ("C3002", "A", "Widget", -100, "2011-03-02 09:00", 60.0, "9"),  # -6000 ignored
    ])
    result = evaluate_high_invoice_value(df, {"min_invoice_value": 5000})
    assert [a["invoice_number"] for a in result["alerts"]] == ["3001"]


def test_product_baseline_requires_minimum_history():
    rows = [("9%03d" % i, "P1", "Widget", 10, f"2011-04-{i % 28 + 1:02d} 09:00", 1.0, "1")
            for i in range(1, 26)]
    rows.append(("9100", "P1", "Widget", 500, "2011-05-01 09:00", 1.0, "1"))
    df = frame(rows)
    result = evaluate_product_qty_iqr(df, {"k": 1.5, "min_history": 20, "prior_only": True})
    assert result["alert_count"] == 1
    alert = result["alerts"][0]
    assert alert["invoice_number"] == "9100"
    # A constant baseline has IQR 0, so the limit is the median itself.
    assert alert["threshold_value"] == pytest.approx(10.0)
    assert "median" in alert["explanation"]


def test_product_baseline_skips_products_with_little_history():
    df = frame([
        ("9200", "P2", "Rare", 5, "2011-06-01 09:00", 1.0, "1"),
        ("9201", "P2", "Rare", 500, "2011-06-02 09:00", 1.0, "1"),
    ])
    result = evaluate_product_qty_iqr(df, {"k": 1.5, "min_history": 20, "prior_only": True})
    assert result["alert_count"] == 0


def test_dispatch_rejects_unknown_rule():
    with pytest.raises(KeyError):
        evaluate_rule("NOT_A_RULE", frame([]))
