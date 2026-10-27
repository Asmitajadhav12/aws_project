"""Dataset import, validation reports and import history (admin only)."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from flask import (
    Blueprint, abort, current_app, flash, g, redirect, render_template, request, url_for,
)
from werkzeug.utils import secure_filename

from services import alert_service
from services.data_cleaning import DatasetError, load_dataset
from services.security import admin_required

bp = Blueprint("data_management", __name__)


@bp.route("/data")
@admin_required
def index():
    batches = alert_service.list_import_batches(limit=20)
    has_data = alert_service.dataset_is_loaded()
    return render_template("data/management.html", batches=batches, has_data=has_data)


@bp.route("/data/import", methods=["POST"])
@admin_required
def import_file():
    upload = request.files.get("dataset")
    if upload is None or upload.filename == "":
        flash("Choose a .csv or .xlsx dataset file to upload.", "error")
        return redirect(url_for("data_management.index"))

    # Never trust the client filename: reduce it to a safe basename and check
    # the extension against an allow-list.
    safe_name = secure_filename(upload.filename)
    extension = Path(safe_name).suffix.lower()
    if extension not in current_app.config["ALLOWED_UPLOAD_EXTENSIONS"]:
        flash("Only .csv and .xlsx files are accepted.", "error")
        return redirect(url_for("data_management.index"))

    note = (request.form.get("source_note") or "").strip()
    tmp_dir = Path(tempfile.mkdtemp(prefix="upload-"))
    tmp_path = tmp_dir / safe_name
    try:
        upload.save(tmp_path)
        try:
            df = load_dataset(tmp_path)
        except DatasetError as exc:
            flash(str(exc), "error")
            return redirect(url_for("data_management.index"))
        result = alert_service.import_dataframe(df, safe_name, g.user["id"], note)
        flash(
            f"Imported {result['imported']:,} line(s); "
            f"{result['rejected']:,} row(s) were skipped as duplicates or unusable.",
            "success",
        )
        return redirect(url_for("data_management.batch_detail", batch_id=result["batch_id"]))
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
            os.rmdir(tmp_dir)
        except OSError:
            current_app.logger.warning("Could not clean up the temporary upload.")


@bp.route("/data/batches/<int:batch_id>")
@admin_required
def batch_detail(batch_id):
    batch = alert_service.get_import_batch(batch_id)
    if batch is None:
        abort(404)
    return render_template("data/batch.html", batch=batch)
