"""Hypothetical transaction simulator.

Lets an analyst type in a hypothetical line and see exactly which configured
rules would fire, with the same explanation text the engine produces. It does
not write anything to the database.
"""
from flask import Blueprint, render_template, request

from services import alert_service
from services.rule_engine import (
    RULE_HIGH_INVOICE_VALUE, RULE_HIGH_LINE_QTY, RULE_PRODUCT_QTY_IQR, RULE_CATALOGUE,
)
from services.security import login_required

bp = Blueprint("simulator", __name__)

FIELDS = ("quantity", "unit_price", "invoice_value", "product_median", "product_iqr")


def _number(form, name, default=0.0):
    raw = (form.get(name) or "").strip()
    if raw == "":
        return float(default)
    return float(raw)


@bp.route("/simulator", methods=["GET", "POST"])
@login_required
def index():
    configuration = alert_service.enabled_configuration()
    values = {"quantity": "1000", "unit_price": "12.50", "invoice_value": "6500",
              "product_median": "40", "product_iqr": "25"}
    results = []
    error = None

    if request.method == "POST":
        values = {name: request.form.get(name, "") for name in FIELDS}
        try:
            quantity = _number(request.form, "quantity")
            unit_price = _number(request.form, "unit_price")
            invoice_value = _number(request.form, "invoice_value")
            product_median = _number(request.form, "product_median")
            product_iqr = _number(request.form, "product_iqr")
        except ValueError:
            error = "Enter numbers only in every field."
        else:
            line_value = round(quantity * unit_price, 2)

            line_params = configuration.get(RULE_HIGH_LINE_QTY, {})
            line_limit = float(line_params.get("min_quantity", 0))
            results.append({
                "rule": RULE_CATALOGUE[RULE_HIGH_LINE_QTY]["name"],
                "triggered": quantity > line_limit,
                "explanation": (
                    f"Line quantity {quantity:,.0f} compared with the configured "
                    f"limit of {line_limit:,.0f} units."
                ),
            })

            value_params = configuration.get(RULE_HIGH_INVOICE_VALUE, {})
            value_limit = float(value_params.get("min_invoice_value", 0))
            results.append({
                "rule": RULE_CATALOGUE[RULE_HIGH_INVOICE_VALUE]["name"],
                "triggered": invoice_value > value_limit,
                "explanation": (
                    f"Hypothetical invoice value {invoice_value:,.2f} (this line alone "
                    f"contributes {line_value:,.2f}) compared with the configured limit "
                    f"of {value_limit:,.2f}."
                ),
            })

            iqr_params = configuration.get(RULE_PRODUCT_QTY_IQR, {})
            k = float(iqr_params.get("k", 0))
            upper = product_median + k * product_iqr
            results.append({
                "rule": RULE_CATALOGUE[RULE_PRODUCT_QTY_IQR]["name"],
                "triggered": quantity > upper,
                "explanation": (
                    f"Line quantity {quantity:,.0f} compared with the supplied product "
                    f"baseline limit of {upper:,.2f} "
                    f"(median {product_median:,.2f} + {k:g} x IQR {product_iqr:,.2f})."
                ),
            })

    return render_template(
        "simulator.html", values=values, results=results, error=error,
        configuration=configuration,
    )
