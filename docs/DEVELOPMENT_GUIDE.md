# Passport Automation System — Development Guide

This guide is for developers joining the project. The current implementation includes the complete, verified Phase 1 Authentication, Phase 2 Applicant, Phase 3 Passport Officer, Phase 4 Police Verification, Phase 5 Passport Generation, Phase 6 Admin Dispatch, and Phase 7 Final Integration modules. All phases are deployment-ready.

## 1. Clone the Repository

```powershell
git clone <repository-url>
cd Passport-Automation-System
```

Pull the latest shared branch before beginning work:

```powershell
git checkout main
git pull origin main
```

## 2. Create a Python Virtual Environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Install Dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Configure `.env`

Copy the safe template and fill in local values:

```powershell
Copy-Item .env.example .env
```

Set a strong local `SECRET_KEY`, MySQL connection values, and private passwords for any demo users you want to seed. Never commit `.env`, database passwords, or other secrets.

## 5. Create the MySQL Database

Ensure MySQL is running, then execute the schema:

```powershell
mysql -u root -p < database\schema.sql
```

The schema creates the `passport_automation` database and the current tables for users, applications, documents, payments, interviews, police verifications, passports, and dispatches.

## 6. Initialize the Schema

The recommended source of truth is `database/schema.sql`. The Flask app also runs a non-destructive `db.create_all()` startup bootstrap for missing tables. Use the SQL schema when setting up a new shared or local database so the intended MySQL types and constraints are applied.

## 7. Seed Demo Users If Required

Set these variables in your local `.env` file:

```text
DEMO_APPLICANT_PASSWORD=<local-secret>
DEMO_OFFICER_PASSWORD=<local-secret>
DEMO_POLICE_PASSWORD=<local-secret>
DEMO_ADMIN_PASSWORD=<local-secret>
```

Then run:

```powershell
python database\seed.py
```

The seed script hashes passwords before storing them. Do not place real passwords in documentation, source control, or Pull Requests.

## 8. Start Flask

```powershell
python app.py
```

The application is served at `http://127.0.0.1:5000/` by default.

## 9. Run Tests

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

The automated tests use an in-memory SQLite database and should not modify the MySQL database.

## 10. Open the Application

Open `http://127.0.0.1:5000/` in a browser. The frontend serves authentication, applicant dashboard with status timeline, officer review, police verification, admin passport generation, and admin dispatch.

## Phase 7 Highlights

- Centralized error handling with JSON responses for 400/401/403/404/409/413/422/500 without exposing stack traces.
- Security headers (X-Content-Type-Options, X-Frame-Options, X-XSS-Protection).
- Deployment-ready `config.py` with `FLASK_ENV`, `FLASK_DEBUG`, `SESSION_COOKIE_SECURE`, and production defaults.
- Applicant status timeline at `/application-details.html?application_id=<id>` covering all 8 stages through `PASSPORT_DISPATCHED`.
- Responsive table wrappers and mobile polish via `frontend/css/style.css`.
- Transaction-safe dispatch and passport generation with `IntegrityError` duplicate protection.
- Full test suite (82 tests) plus E2E workflow verification.

## Codebase Guide

- `app.py`: Flask app creation, blueprint registration, startup setup, and frontend page serving.
- `config.py`: environment-backed configuration, database URI, upload path, and session settings.
- `backend/extensions.py`: shared Flask-SQLAlchemy extension.
- `backend/models/`: SQLAlchemy models for users, applications, documents, payments, interviews, police verifications, passports, and dispatches.
- `backend/routes/`: authentication, applicant, officer, police, passport-generation, and dispatch API blueprints.
- `backend/utils/`: authentication decorators and related helpers.
- `frontend/`: HTML pages, CSS, and browser-side JavaScript.
- `database/schema.sql`: MySQL database and table definitions.
- `database/seed.py`: repeatable local demo-user seeding script.
- `tests/`: automated authentication and applicant workflow tests.
- `uploads/documents/`: runtime document storage. Uploaded files must stay local and are ignored by Git.
- `uploads/photos/`: reserved runtime photo storage, also ignored by Git.

## Collaboration Workflow

1. Pull the latest `main`.
2. Create your own feature branch.
3. Work only on your assigned phase.
4. Run all tests.
5. Commit the changes on your feature branch.
6. Push the feature branch.
7. Open a Pull Request.
8. Wait for review before merging.

Recommended branch names:

- `feature/phase-3-officer-module`
- `feature/phase-4-police-module`
- `feature/phase-5-admin-module`
- `feature/phase-6-passport-dispatch`

Do not directly modify another person's branch. Do not commit or push from a task that only asks for local preparation.

## Safety Rules

- Keep `.env` local and untracked.
- Keep uploaded documents out of Git.
- Do not expose passwords, API keys, or database credentials.
- Preserve the existing Phase 1 and Phase 2 behavior.
- Consider existing data before changing database structures.
- Do not use browser `localStorage` as a database.
- Phase 7 is complete and the system is deployment-ready; do not claim an earlier phase as incomplete.
