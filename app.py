import os

from flask import Flask, jsonify, send_from_directory
from sqlalchemy import inspect, text

from config import Config
from backend.extensions import cors, db
from backend.models import Application, Document, Payment, User
from backend.routes.applicant_routes import applicant_bp
from backend.routes.auth_routes import auth_bp
from backend.routes.officer_routes import officer_bp
from backend.routes.police_routes import police_bp
from backend.routes.passport_routes import passport_bp


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
        existing = {column["name"] for column in inspector.get_columns(table_name)}
        for column_name, column_definition in table_columns.items():
            if column_name not in existing:
                db.session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"))
    db.session.commit()


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

    upload_dir = app.config.get("UPLOAD_FOLDER", os.path.join(os.getcwd(), "uploads", "documents"))
    os.makedirs(upload_dir, exist_ok=True)
    with app.app_context():
        db.create_all()
        _ensure_officer_columns()
        _ensure_police_verification_table()

    @app.get("/api/health")
    def health_check():
        return jsonify(
            success=True,
            message="Passport Automation System API is running",
        )

    @app.get("/")
    def serve_homepage():
        return send_from_directory("frontend", "index.html")

    @app.get("/<page>.html")
    def serve_frontend_page(page):
        return send_from_directory("frontend", f"{page}.html")

    @app.get("/css/<path:filename>")
    def serve_css(filename):
        return send_from_directory("frontend/css", filename)

    @app.get("/js/<path:filename>")
    def serve_javascript(filename):
        return send_from_directory("frontend/js", filename)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
