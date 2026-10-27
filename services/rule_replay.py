"""Threshold sweeps for the Rule Tuning Lab.

The question the lab answers is operational: *which threshold gives the
analyst a workload they can actually review?* A sweep runs one rule over a
list of thresholds and reports the alert volume each one produces.
"""
from __future__ import annotations

import pandas as pd

from services import rule_engine as engine


def _parameter_name(rule_code: str) -> str:
    rule = engine.get_rule(rule_code)
    return next(iter(rule["default_parameters"]))


def sweep_thresholds(df: pd.DataFrame, rule_code: str, thresholds, base_params: dict | None = None) -> list[dict]:
    """Run one rule for each threshold. Returns one row per threshold."""
    rule = engine.get_rule(rule_code)
    param = _parameter_name(rule_code)
    prepared = engine._prepare(df)
    results = []
    for raw in thresholds:
        value = float(raw)
        params = {**(base_params or {}), param: value}
        outcome = engine.evaluate_rule(rule_code, prepared, params)
        results.append(
            {
                "threshold": value,
                "parameter": param,
                "alert_count": outcome["alert_count"],
                "evaluated_rows": outcome["evaluated_rows"],
                "alerts_per_1000": round(
                    1000.0 * outcome["alert_count"] / outcome["evaluated_rows"], 2
                ) if outcome["evaluated_rows"] else 0.0,
                "sample_alerts": outcome["alerts"][:3],
            }
        )
    return results


def parse_thresholds(text: str) -> list[float]:
    """Parse a comma or space separated list of numbers from the lab form."""
    cleaned = (text or "").replace(",", " ").split()
    values = []
    for token in cleaned:
        try:
            values.append(float(token))
        except ValueError as exc:
            raise ValueError(f"'{token}' is not a number.") from exc
    if not values:
        raise ValueError("Enter at least one threshold value.")
    if len(values) > 12:
        raise ValueError("Enter at most 12 threshold values per sweep.")
    return sorted(dict.fromkeys(values))
