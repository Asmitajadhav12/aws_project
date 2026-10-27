"""Analysis history and running a detection pass over the imported data."""
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from services import alert_service
from services.security import admin_required, login_required

bp = Blueprint("analysis", __name__)


@bp.route("/analysis")
@login_required
def history():
    runs = alert_service.list_analysis_runs(limit=100)
    return render_template("analysis/history.html", runs=runs)


@bp.route("/analysis/run", methods=["POST"])
@admin_required
def run():
    rule_code = request.form.get("rule_code", "")
    if alert_service.get_rule_row_by_code(rule_code) is None:
        abort(400)
    try:
        result = alert_service.run_analysis(rule_code, g.user["id"])
    except Exception as exc:  # noqa: BLE001 - the analyst needs to see the reason
        flash(f"The analysis failed: {exc}", "error")
        return redirect(url_for("analysis.history"))
    flash(
        f"Analysis finished: {result['alert_count']} alert(s) from "
        f"{result['evaluated_rows']} evaluated record(s).",
        "success",
    )
    return redirect(url_for("analysis.run_detail", run_id=result["run_id"]))


@bp.route("/analysis/<int:run_id>")
@login_required
def run_detail(run_id):
    run = alert_service.get_analysis_run(run_id)
    if run is None:
        abort(404)
    alerts = alert_service.list_alerts_for_run(run_id, limit=500)
    return render_template("analysis/run.html", run=run, alerts=alerts)
