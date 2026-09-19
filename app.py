import logging
import os

from flask import Flask, jsonify, send_from_directory
from sqlalchemy import inspect, text
from werkzeug.exceptions import HTTPException

from config import Config
from backend.extensions import cors, db
from backend.models import Application, Document, Payment, User
from backend.routes.applicant_routes import applicant_bp
from backend.routes.auth_routes import auth_bp
from backend.routes.officer_routes import officer_bp
from backend.routes.police_routes import police_bp
from backend.routes.passport_routes import passport_bp
from backend.routes.dispatch_routes import dispatch_bp


def _ensure_officer_columns():
    columns = {
        "applications": {
            "forwarded_by_id": "INTEGER NULL",
            "forwarded_at": "DATETIME NULL",
            "rejected_by_id": "INTEGER NULL",
            "rejection_reason": "TEXT NULL",
            "rejected_at": "DATETIME NULL",
        },
        "documents": {
            "verified_by_id": "INTEGER NULL",
            "verification_remarks": "TEXT NULL",
        },
    }
    inspector = inspect(db.engine)
    for table_name, table_columns in columns.items():
        try:
            existing = {column["name"] for column in inspector.get_columns(table_name)}
        except Exception:
            continue
        for column_name, column_definition in table_columns.items():
            if column_name not in existing:
                db.session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"))
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


def _ensure_police_verification_table():
    db.create_all()


def create_app(config_object=None):
    app = Flask(__name__)
    if isinstance(config_object, dict):
        app.config.from_mapping(config_object)
    else:
        app.config.from_object(config_object or Config)

    db.init_app(app)
    cors.init_app(app, supports_credentials=True)
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(applicant_bp, url_prefix="/api")
    app.register_blueprint(officer_bp, url_prefix="/api/officer")
    app.register_blueprint(police_bp, url_prefix="/api/police")
    app.register_blueprint(passport_bp, url_prefix="/api")
    app.register_blueprint(dispatch_bp, url_prefix="/api")

    upload_dir = app.config.get("UPLOAD_FOLDER", os.path.join(os.getcwd(), "uploads", "documents"))
    os.makedirs(upload_dir, exist_ok=True)
    with app.app_context():
        try:
            db.create_all()
            _ensure_officer_columns()
            _ensure_police_verification_table()
        except Exception as exc:
            logging.warning("Database initialization warning: %s", exc)

    @app.get("/api/health")
    def health_check():
        return jsonify(
            success=True,
            message="Passport Automation System API is running",
        )

    @app.errorhandler(400)
    def handle_400(error):
        return jsonify(success=False, message=getattr(error, "description", "Bad request")), 400

    @app.errorhandler(401)
    def handle_401(error):
        return jsonify(success=False, message=getattr(error, "description", "Authentication required")), 401

    @app.errorhandler(403)
    def handle_403(error):
        return jsonify(success=False, message=getattr(error, "description", "Insufficient permissions")), 403

    @app.errorhandler(404)
    def handle_404(error):
        if error.description and error.description != "Not Found":
            return jsonify(success=False, message=error.description), 404
        # For API routes return JSON, otherwise let frontend serve handle it
        if "/api/" in (error.description or "") or (hasattr(error, "request") and "/api/" in getattr(error.request, "path", "")):
            return jsonify(success=False, message="Resource not found"), 404
        return jsonify(success=False, message="Resource not found"), 404

    @app.errorhandler(409)
    def handle_409(error):
        return jsonify(success=False, message=getattr(error, "description", "Conflict")), 409

    @app.errorhandler(413)
    def handle_413(error):
        return jsonify(success=False, message="File is too large. Maximum size is 5MB"), 413

    @app.errorhandler(422)
    def handle_422(error):
        return jsonify(success=False, message=getattr(error, "description", "Unprocessable entity")), 422

    @app.errorhandler(500)
    def handle_500(error):
        logging.exception("Unhandled server error")
        return jsonify(success=False, message="An internal error occurred. Please try again."), 500

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        if error.code and error.code >= 400 and error.code < 600:
            if error.code == 404:
                return jsonify(success=False, message="Resource not found"), 404
            return jsonify(success=False, message=error.description or error.name), error.code
        return jsonify(success=False, message="An error occurred"), 500

    @app.errorhandler(Exception)
    def handle_exception(error):
        if isinstance(error, HTTPException):
            raise error
        logging.exception("Unhandled exception")
        return jsonify(success=False, message="An internal error occurred. Please try again."), 500

    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    @app.get("/")
    def serve_homepage():
        return send_from_directory("frontend", "index.html")

    @app.get("/<page>.html")
    def serve_frontend_page(page):
        # Prevent path traversal
        if ".." in page or "/" in page or "\\" in page:
            return jsonify(success=False, message="Resource not found"), 404
        return send_from_directory("frontend", f"{page}.html")

    @app.get("/css/<path:filename>")
    def serve_css(filename):
        if ".." in filename:
            return jsonify(success=False, message="Resource not found"), 404
        return send_from_directory("frontend/css", filename)

    @app.get("/js/<path:filename>")
    def serve_javascript(filename):
        if ".." in filename:
            return jsonify(success=False, message="Resource not found"), 404
        return send_from_directory("frontend/js", filename)

    return app


app = create_app()


if __name__ == "__main__":
    debug_mode = app.config.get("DEBUG", False)
    app.run(debug=debug_mode)
