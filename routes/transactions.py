"""Transaction search, pagination and invoice drill-down."""
from flask import Blueprint, abort, render_template, request

from services import alert_service, db
from services.security import login_required

bp = Blueprint("transactions", __name__)

PER_PAGE = 25


def _filters():
    return {
        "invoice": (request.args.get("invoice") or "").strip(),
        "customer": (request.args.get("customer") or "").strip(),
        "stock": (request.args.get("stock") or "").strip(),
        "country": (request.args.get("country") or "").strip(),
        "date_from": (request.args.get("date_from") or "").strip(),
        "date_to": (request.args.get("date_to") or "").strip(),
        "only_flagged": request.args.get("only_flagged") == "1",
    }


def _build_where(filters):
    clauses, params = [], []
    if filters["invoice"]:
        clauses.append("t.invoice_number LIKE %s")
        params.append(f"%{filters['invoice'].upper()}%")
    if filters["customer"]:
        clauses.append("t.customer_id = %s")
        params.append(filters["customer"])
    if filters["stock"]:
        clauses.append("t.stock_code LIKE %s")
        params.append(f"%{filters['stock'].upper()}%")
    if filters["country"]:
        clauses.append("t.country = %s")
        params.append(filters["country"])
    if filters["date_from"]:
        clauses.append("t.invoice_date >= %s")
        params.append(f"{filters['date_from']} 00:00:00")
    if filters["date_to"]:
        clauses.append("t.invoice_date <= %s")
        params.append(f"{filters['date_to']} 23:59:59")
    if filters["only_flagged"]:
        clauses.append(
            "EXISTS (SELECT 1 FROM alerts a WHERE a.invoice_number = t.invoice_number)"
        )
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, tuple(params)


@bp.route("/transactions")
@login_required
def index():
    filters = _filters()
    where, params = _build_where(filters)
    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1

    total = int(db.scalar(f"SELECT COUNT(*) FROM transactions t {where}", params))
    rows = db.query_all(
        f"SELECT t.id, t.invoice_number, t.stock_code, t.description, t.quantity, "
        f"       t.invoice_date, t.unit_price, t.customer_id, t.country, "
        f"       t.is_cancellation, t.line_value, "
        f"       EXISTS (SELECT 1 FROM alerts a WHERE a.invoice_number = t.invoice_number) AS flagged "
        f"FROM transactions t {where} ORDER BY t.invoice_date DESC, t.id DESC "
        f"LIMIT %s OFFSET %s",
        params + (PER_PAGE, (page - 1) * PER_PAGE),
    )
    countries = db.query_all(
        "SELECT DISTINCT country FROM transactions WHERE country IS NOT NULL ORDER BY country"
    )
    return render_template(
        "transactions/list.html",
        rows=rows,
        filters=filters,
        countries=[c["country"] for c in countries],
        total=total,
        page=page,
        per_page=PER_PAGE,
        total_pages=max(1, -(-total // PER_PAGE)),
    )


@bp.route("/transactions/invoice/<invoice_number>")
@login_required
def invoice_detail(invoice_number):
    lines = db.query_all(
        "SELECT id, stock_code, description, quantity, unit_price, line_value, "
        "       invoice_date, customer_id, country, is_cancellation, is_valid_sale "
        "FROM transactions WHERE invoice_number = %s ORDER BY id",
        (invoice_number,),
    )
    if not lines:
        abort(404)
    sale_total = sum(float(l["line_value"]) for l in lines if l["is_valid_sale"])
    alerts = alert_service.alerts_for_invoice(invoice_number)
    return render_template(
        "transactions/detail.html",
        invoice_number=invoice_number,
        lines=lines,
        alerts=alerts,
        sale_total=sale_total,
        customer_id=lines[0]["customer_id"],
        invoice_date=lines[0]["invoice_date"],
        country=lines[0]["country"],
        is_cancellation=any(l["is_cancellation"] for l in lines),
    )
