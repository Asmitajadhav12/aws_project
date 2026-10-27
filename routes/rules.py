"""Rule configuration and the Rule Tuning Lab."""
from flask import (
    Blueprint, abort, flash, g, redirect, render_template, request, url_for,
)

from services import alert_service, db
from services.rule_engine import RULE_CATALOGUE, RULE_ORDER
from services.rule_replay import parse_thresholds, sweep_thresholds
from services.security import admin_required, login_required

bp = Blueprint("rules", __name__)

# Upper bound on rows pulled into memory for a sweep, so a lab request on the
# full dataset cannot exhaust the server.
SWEEP_ROW_LIMIT = 120_000


@bp.route("/rules")
@login_required
def index():
    rules = alert_service.list_rules()
    return render_template("rules/list.html", rules=rules)


@bp.route("/rules/<int:rule_id>/update", methods=["POST"])
@admin_required
def update(rule_id):
    rule = alert_service.get_rule_row(rule_id)
    if rule is None:
        abort(404)
    submitted = {key: request.form.get(key) for key in request.form}
    try:
        parameters = alert_service.validate_parameters(rule["rule_code"], submitted)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("rules.index"))
    enabled = request.form.get("is_enabled") == "1"
    alert_service.update_rule(rule_id, parameters, enabled, g.user["id"])
    flash(
        f"{rule['rule_name']} saved as a new configuration version. "
        "Alerts already generated keep their original version.",
        "success",
    )
    return redirect(url_for("rules.index"))


@bp.route("/rules/<int:rule_id>/toggle", methods=["POST"])
@admin_required
def toggle(rule_id):
    rule = alert_service.get_rule_row(rule_id)
    if rule is None:
        abort(404)
    enable = not bool(rule["is_enabled"])
    alert_service.toggle_rule(rule_id, enable, g.user["id"])
    flash(f"{rule['rule_name']} is now {'enabled' if enable else 'disabled'}.", "success")
    return redirect(url_for("rules.index"))


@bp.route("/rules/tuning-lab", methods=["GET", "POST"])
@login_required
def tuning_lab():
    rules = alert_service.list_rules()
    selected = request.values.get("rule_code") or RULE_ORDER[0]
    thresholds_text = request.values.get("thresholds") or ""
    sweep = None
    error = None

    if request.method == "POST":
        try:
            thresholds = parse_thresholds(thresholds_text)
        except ValueError as exc:
            error = str(exc)
            thresholds = []
        if not error:
            if selected not in RULE_CATALOGUE:
                abort(400)
            df = alert_service.load_transactions_dataframe(limit=SWEEP_ROW_LIMIT)
            if df.empty:
                error = "No transactions are imported yet, so there is nothing to sweep."
            else:
                base = alert_service.enabled_configuration().get(selected, {})
                sweep = sweep_thresholds(df, selected, thresholds, base_params=base)

    return render_template(
        "rules/tuning_lab.html",
        rules=rules,
        selected=selected,
        thresholds_text=thresholds_text,
        sweep=sweep,
        error=error,
        row_limit=SWEEP_ROW_LIMIT,
    )


@bp.route("/rules/tuning-lab/apply", methods=["POST"])
@admin_required
def apply_threshold():
    """Adopt a swept threshold as the live configuration for that rule."""
    rule_code = request.form.get("rule_code", "")
    rule = alert_service.get_rule_row_by_code(rule_code)
    if rule is None:
        abort(404)
    parameter = request.form.get("parameter", "")
    value = request.form.get("value", "")
    try:
        parameters = alert_service.validate_parameters(rule_code, {parameter: value})
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("rules.tuning_lab", rule_code=rule_code))
    alert_service.update_rule(rule["id"], parameters, bool(rule["is_enabled"]), g.user["id"])
    flash(
        f"{rule['rule_name']} now uses {parameter} = {parameters.get(parameter)}.",
        "success",
    )
    return redirect(url_for("rules.index"))
