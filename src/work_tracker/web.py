"""Flask web application for work-tracker GUI."""

from __future__ import annotations

import mimetypes
import os
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory, send_file

from work_tracker.config import load_config
from work_tracker.db import (
    insert_entry,
    query_entries,
    delete_entry,
    update_entry,
    date_range_for,
    insert_attachment,
    get_attachments,
    delete_attachment,
)
from work_tracker.models import CATEGORIES, WorkEntry


def _attachments_dir() -> Path:
    xdg = os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
    d = Path(xdg) / "work-tracker" / "attachments"
    d.mkdir(parents=True, exist_ok=True)
    return d


def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
        static_url_path="/static",
    )
    app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB

    cfg = load_config()
    dsn = cfg["database_url"]

    @app.route("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    # --- Entries API ---

    @app.route("/api/entries", methods=["GET"])
    def api_entries():
        start = request.args.get("start")
        end = request.args.get("end")
        category = request.args.get("category")
        limit = request.args.get("limit", 100, type=int)
        entries = query_entries(dsn, start=start, end=end, category=category, limit=limit, order="DESC")
        result = []
        for e in entries:
            attachments = get_attachments(dsn, e.id)
            result.append({
                "id": e.id,
                "timestamp": e.timestamp,
                "source": e.source,
                "category": e.category,
                "raw_text": e.raw_text,
                "summary": e.summary,
                "duration_minutes": e.duration_minutes,
                "attachments": attachments,
            })
        return jsonify(result)

    @app.route("/api/entries", methods=["POST"])
    def api_create_entry():
        data = request.get_json(force=True, silent=True) or {}
        raw_text = data.get("raw_text", "").strip()
        if not raw_text:
            return jsonify({"error": "raw_text is required"}), 400
        entry = WorkEntry(
            raw_text=raw_text,
            category=data.get("category", "other"),
            duration_minutes=data.get("duration_minutes"),
            source="gui",
        )
        insert_entry(dsn, entry)
        return jsonify({"id": entry.id, "status": "created"}), 201

    @app.route("/api/entries/<entry_id>", methods=["PUT"])
    def api_update_entry(entry_id):
        data = request.get_json(force=True, silent=True) or {}
        fields = {}
        if "raw_text" in data:
            fields["raw_text"] = data["raw_text"]
        if "category" in data:
            fields["category"] = data["category"]
        if "duration_minutes" in data:
            fields["duration_minutes"] = data["duration_minutes"]
        if not fields:
            return jsonify({"error": "No fields to update"}), 400
        ok = update_entry(dsn, entry_id, **fields)
        if not ok:
            return jsonify({"error": "Entry not found"}), 404
        return jsonify({"status": "updated"})

    @app.route("/api/entries/<entry_id>", methods=["DELETE"])
    def api_delete_entry(entry_id):
        ok = delete_entry(dsn, entry_id)
        if not ok:
            return jsonify({"error": "Entry not found"}), 404
        return jsonify({"status": "deleted"})

    @app.route("/api/periods/<period>")
    def api_period(period):
        start, end = date_range_for(period)
        return jsonify({"start": start, "end": end})

    @app.route("/api/categories")
    def api_categories():
        return jsonify(list(CATEGORIES))

    # --- Reminders API ---

    @app.route("/api/reminders/status")
    def api_reminder_status():
        from work_tracker.scheduler import reminder_status
        return jsonify(reminder_status())

    @app.route("/api/reminders", methods=["POST"])
    def api_reminder_install():
        from work_tracker.scheduler import install_reminder
        data = request.get_json(force=True, silent=True) or {}
        minutes = data.get("interval_minutes", 90)
        install_reminder(minutes)
        return jsonify({"status": "installed", "interval_minutes": minutes})

    @app.route("/api/reminders", methods=["DELETE"])
    def api_reminder_remove():
        from work_tracker.scheduler import remove_reminder
        remove_reminder()
        return jsonify({"status": "removed"})

    @app.route("/api/reminders/oneshot", methods=["POST"])
    def api_reminder_oneshot():
        from work_tracker.scheduler import schedule_oneshot
        data = request.get_json(force=True, silent=True) or {}
        minutes = data.get("minutes", 30)
        schedule_oneshot(minutes)
        return jsonify({"status": "scheduled", "minutes": minutes})

    # --- Attachments API ---

    @app.route("/api/entries/<entry_id>/attachments", methods=["POST"])
    def api_upload_attachment(entry_id):
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400
        f = request.files["file"]
        if not f.filename:
            return jsonify({"error": "Empty filename"}), 400

        att_id = str(uuid.uuid4())
        ext = Path(f.filename).suffix
        stored_name = f"{att_id}{ext}"
        dest = _attachments_dir() / stored_name
        f.save(str(dest))

        mime = f.content_type or mimetypes.guess_type(f.filename)[0] or "application/octet-stream"
        attachment = {
            "id": att_id,
            "entry_id": entry_id,
            "filename": f.filename,
            "filepath": str(dest),
            "mime_type": mime,
            "size_bytes": dest.stat().st_size,
            "created_at": datetime.now().astimezone().isoformat(),
        }
        insert_attachment(dsn, attachment)
        return jsonify(attachment), 201

    @app.route("/api/attachments/<att_id>/file")
    def api_serve_attachment(att_id):
        # Look up the attachment filepath from DB
        conn = __import__("psycopg2").connect(dsn)
        with conn.cursor() as cur:
            cur.execute("SELECT filepath, filename, mime_type FROM attachments WHERE id = %s", (att_id,))
            row = cur.fetchone()
        conn.close()
        if not row:
            return jsonify({"error": "Not found"}), 404
        filepath, filename, mime_type = row
        return send_file(filepath, mimetype=mime_type, download_name=filename)

    @app.route("/api/attachments/<att_id>", methods=["DELETE"])
    def api_delete_attachment(att_id):
        # Get filepath before deleting
        conn = __import__("psycopg2").connect(dsn)
        with conn.cursor() as cur:
            cur.execute("SELECT filepath FROM attachments WHERE id = %s", (att_id,))
            row = cur.fetchone()
        conn.close()
        if row:
            try:
                os.unlink(row[0])
            except OSError:
                pass
        ok = delete_attachment(dsn, att_id)
        if not ok:
            return jsonify({"error": "Not found"}), 404
        return jsonify({"status": "deleted"})

    return app


def run_gui():
    """Launch the work-tracker GUI as a desktop window."""
    import threading
    import webview

    # Set GDK_BACKEND and program name so the dock matches our .desktop file
    os.environ.setdefault("GDK_PROGRAM_CLASS", "work-tracker")
    try:
        import gi
        gi.require_version("Gdk", "3.0")
        from gi.repository import GLib
        GLib.set_prgname("work-tracker")
        GLib.set_application_name("Work Tracker")
    except Exception:
        pass

    app = create_app()

    # Run Flask on a local port in a background thread
    server = threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=5213, use_reloader=False),
        daemon=True,
    )
    server.start()

    icon = os.path.join(os.path.dirname(__file__), "static", "icon.png")
    window = webview.create_window(
        "Work Tracker",
        "http://127.0.0.1:5213",
        width=1000,
        height=700,
        min_size=(600, 400),
    )
    webview.start(icon=icon)
