"""Alert list, alert investigation, review status changes."""
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from services import alert_service
from services.security import login_required

bp = Blueprint("alerts", __name__)

STATUSES = ("open", "under_review", "reviewed")


@bp.route("/alerts")
@login_required
def index():
    status = request.args.get("status") or ""
    rule_code = request.args.get("rule") or ""
    rows = alert_service.list_alerts(
        status=status or None, rule_code=rule_code or None, limit=200
    )
    rules = alert_service.list_rules()
    return render_template(
        "alerts/list.html", rows=rows, status=status, rule_code=rule_code, rules=rules
    )


@bp.route("/alerts/<int:alert_id>")
@login_required
def detail(alert_id):
    alert = alert_service.get_alert(alert_id)
    if alert is None:
        abort(404)
    return render_template("alerts/detail.html", alert=alert, statuses=STATUSES)


@bp.route("/alerts/<int:alert_id>/review", methods=["POST"])
@login_required
def review(alert_id):
    status = request.form.get("review_status", "")
    if status not in STATUSES:
        abort(400)
    alert = alert_service.get_alert(alert_id)
    if alert is None:
        abort(404)
    alert_service.review_alert(alert_id, status, g.user["id"])
    flash(
        "Review status updated. A reviewed alert is a closed investigation, "
        "not a confirmed fraud or a confirmed legitimate transaction.",
        "success",
    )
    return redirect(url_for("alerts.detail", alert_id=alert_id))
