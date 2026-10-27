"""Cancellation analysis and product trends -- read-only analytical views."""
from flask import Blueprint, render_template, request

from services import db
from services.security import login_required

bp = Blueprint("insights", __name__)


@bp.route("/cancellations")
@login_required
def cancellations():
    summary = db.query_one(
        "SELECT COUNT(*) AS total_lines, "
        "       SUM(is_cancellation) AS cancellation_lines, "
        "       COUNT(DISTINCT CASE WHEN is_cancellation = 1 THEN invoice_number END) AS cancellation_invoices, "
        "       COUNT(DISTINCT CASE WHEN is_cancellation = 1 THEN customer_id END) AS customers_with_cancellations "
        "FROM transactions"
    ) or {}
    by_month = db.query_all(
        "SELECT DATE_FORMAT(invoice_date, '%%Y-%%m') AS month, "
        "       SUM(is_cancellation) AS cancellation_lines, COUNT(*) AS total_lines "
        "FROM transactions GROUP BY month ORDER BY month"
    )
    top_customers = db.query_all(
        "SELECT customer_id, COUNT(*) AS cancellation_lines, "
        "       SUM(quantity * unit_price) AS cancelled_value "
        "FROM transactions WHERE is_cancellation = 1 AND customer_id IS NOT NULL "
        "GROUP BY customer_id ORDER BY cancellation_lines DESC LIMIT 10"
    )
    top_products = db.query_all(
        "SELECT stock_code, MAX(description) AS description, COUNT(*) AS cancellation_lines, "
        "       SUM(quantity) AS cancelled_quantity "
        "FROM transactions WHERE is_cancellation = 1 "
        "GROUP BY stock_code ORDER BY cancellation_lines DESC LIMIT 10"
    )
    return render_template(
        "insights/cancellations.html",
        summary=summary,
        by_month=by_month,
        top_customers=top_customers,
        top_products=top_products,
    )


@bp.route("/product-trends")
@login_required
def product_trends():
    """Compare product quantity between two months using the imported data."""
    months = db.query_all(
        "SELECT DISTINCT DATE_FORMAT(invoice_date, '%%Y-%%m') AS month "
        "FROM transactions ORDER BY month DESC LIMIT 24"
    )
    month_list = [m["month"] for m in months]
    current = request.args.get("current") or (month_list[0] if month_list else "")
    previous = request.args.get("previous") or (month_list[1] if len(month_list) > 1 else "")

    rows = []
    if current and previous:
        rows = db.query_all(
            "SELECT stock_code, MAX(description) AS description, "
            "       SUM(CASE WHEN DATE_FORMAT(invoice_date, '%%Y-%%m') = %s THEN quantity ELSE 0 END) AS current_qty, "
            "       SUM(CASE WHEN DATE_FORMAT(invoice_date, '%%Y-%%m') = %s THEN quantity ELSE 0 END) AS previous_qty "
            "FROM transactions WHERE is_valid_sale = 1 "
            "  AND DATE_FORMAT(invoice_date, '%%Y-%%m') IN (%s, %s) "
            "GROUP BY stock_code "
            "HAVING current_qty <> previous_qty "
            "ORDER BY ABS(SUM(CASE WHEN DATE_FORMAT(invoice_date, '%%Y-%%m') = %s THEN quantity ELSE 0 END) "
            "           - SUM(CASE WHEN DATE_FORMAT(invoice_date, '%%Y-%%m') = %s THEN quantity ELSE 0 END)) DESC "
            "LIMIT 25",
            (current, previous, current, previous, current, previous),
        )
        for row in rows:
            previous_qty = float(row["previous_qty"] or 0)
            current_qty = float(row["current_qty"] or 0)
            row["change"] = current_qty - previous_qty
            row["change_pct"] = (
                round(100.0 * (current_qty - previous_qty) / previous_qty, 1)
                if previous_qty else None
            )

    return render_template(
        "insights/product_trends.html",
        months=month_list,
        current=current,
        previous=previous,
        rows=rows,
    )
