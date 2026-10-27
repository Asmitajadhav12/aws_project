"""Overview page: dataset scale, alert workload, recent runs."""
from flask import Blueprint, render_template

from services import alert_service
from services.security import login_required

bp = Blueprint("dashboard", __name__)


@bp.route("/")
@login_required
def overview():
    stats = alert_service.dashboard_stats()
    has_data = bool(stats["totals"] and stats["totals"].get("line_count"))
    return render_template("dashboard.html", stats=stats, has_data=has_data)
