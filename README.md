# Passport Automation System

## Project Description

The Passport Automation System is a Flask and MySQL application for managing passport applications, applicant documents, mock payments, Officer and Police review, simulated passport generation, and Admin passport dispatch. It delivers complete, verified Phase 1 through Phase 7 functionality and is deployment-ready.

## Problem Statement

Passport applications often rely on fragmented forms, manual document handling, and limited status visibility. This project provides a structured workflow where applicants can create an application, maintain their details, upload required documents, make a mock payment, submit the application, and track its status.

## Objectives

- Provide secure session-based registration and authentication.
- Support new passport, renewal, and reissue applications.
- Validate application data and uploaded files on the server.
- Protect applicant data with role and ownership checks.
- Provide a foundation for later officer, police, admin, and dispatch modules.

## Complete Applicant Workflow

1. Register or sign in as an applicant.
2. Create a NEW, RENEWAL, or REISSUE application.
3. Complete personal, address, family, and passport details.
4. Upload the required identity, address, date-of-birth, photograph, and signature documents.
5. Complete the mock payment flow and receive a transaction ID.
6. Confirm and submit the application.
7. View the application status and profile information.

## User Roles

The data model supports `applicant`, `officer`, `police`, and `admin` roles. Applicant, Officer, Police, passport generation, Admin dispatch, and final integration workflows are implemented and verified; the system is deployment-ready.

## Technology Stack

- Python 3
- Flask 3
- Flask-SQLAlchemy and SQLAlchemy
- MySQL with PyMySQL
- Flask-CORS and python-dotenv
- HTML5, CSS3, vanilla JavaScript
- Tailwind CSS via CDN for the current frontend
- unittest with an in-memory SQLite test database

## Current Implementation Status

- ✅ COMPLETE: Phase 1 - Foundation and Authentication
- ✅ COMPLETE: Phase 2 - Applicant Module, including live verification
- ✅ COMPLETE: Phase 3 - Passport Officer Module, including live verification
- ✅ COMPLETE: Phase 4 - Police Verification Module, including live verification
- ✅ COMPLETE: Phase 5 - Passport Generation Module, including live verification
- ✅ COMPLETE: Phase 6 - Admin Passport Dispatch, including live verification
- ✅ COMPLETE: Phase 7 - Final Integration, Security, Hardening, and Deployment Readiness

Phase 2 verification completed 20 automated tests and a live applicant flow. Phase 3 adds 21 Officer tests and a live Officer flow through document verification, interview completion, and `POLICE_VERIFICATION` forwarding. Phase 4 adds 15 Police tests and live CLEAR/NOT_CLEAR verification flows. Phase 5 adds 14 Passport Generation tests and live Admin generation/retrieval verification. Phase 6 adds 12 Dispatch tests and live Admin dispatch verification. Phase 7 adds full integration audit, security hardening, responsive polish, applicant timeline, 82-test regression, and E2E workflow verification through `PASSPORT_DISPATCHED`.

## Project Structure

```text
app.py                 Flask app factory, route registration, and entry point
config.py              Environment-backed database and upload configuration
backend/               Extensions, models, routes, and authentication utilities
database/              MySQL schema and repeatable demo-user seed script
frontend/              HTML pages, CSS, and browser-side JavaScript
tests/                 Automated authentication and applicant workflow tests
uploads/               Runtime document storage; uploaded files are ignored by Git
docs/                  Project status and developer documentation
requirements.txt       Python dependencies
.env.example           Safe environment-variable template
```

## Setup Instructions

1. Clone the repository and enter its directory.
2. Create and activate a virtual environment.
3. Install dependencies with `pip install -r requirements.txt`.
4. Copy `.env.example` to `.env` and set local values. Never commit `.env`.
5. Create the MySQL database using `database/schema.sql`.
6. Optionally seed demo users after setting local demo passwords.
7. Start Flask with `python app.py`.
8. Open `http://127.0.0.1:5000/`.

Windows example:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
mysql -u root -p < database\schema.sql
python database\seed.py
python app.py
```

## Environment Configuration

Use `.env.example` as the safe template. Set a strong local `SECRET_KEY`, `PASSPORT_VALIDITY_YEARS`, `FLASK_ENV`/`FLASK_DEBUG`/`SESSION_COOKIE_SECURE`, database connection values, `UPLOAD_FOLDER`, and private demo passwords. The application reads `SECRET_KEY`, `PASSPORT_VALIDITY_YEARS`, `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, and related flags from the environment. Production must use a strong `SECRET_KEY` and `FLASK_DEBUG=false`.

## Database Setup

`database/schema.sql` creates the `passport_automation` database and the `users`, `applications`, `documents`, `payments`, `interviews`, `police_verifications`, `passports`, and `dispatches` tables. Phases 3 through 6 add non-destructive workflow fields. `database/seed.py` creates or refreshes local demo users and hashes their passwords; it requires the four `DEMO_*_PASSWORD` variables to be set.

## Run Backend and Tests

Start the backend and frontend-serving Flask process:

```powershell
python app.py
```

Run all automated tests:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

Tests use SQLite and do not alter the configured MySQL database.

## Demo Roles

The seed script creates these local accounts using passwords supplied only through `.env`:

| Role | Email |
| --- | --- |
| Applicant | applicant@example.com |
| Officer | officer@example.com |
| Police | police@example.com |
| Admin | admin@example.com |

No passwords or secrets are stored in this repository.

## API Overview

Authentication endpoints are under `/api/auth`: registration, login, logout, and current-user lookup. Applicant endpoints include:

- `GET/POST /api/applications`
- `GET/PUT/DELETE /api/applications/<application_id>`
- `POST /api/applications/<application_id>/submit`
- `POST/GET /api/applications/<application_id>/documents`
- `DELETE /api/applications/<application_id>/documents/<document_id>`
- `POST/GET /api/applications/<application_id>/payment(s)`
- `GET /api/applications/<application_id>/status`
- `GET/PUT /api/profile`
- `POST /api/profile/change-password`

All applicant endpoints require an authenticated applicant session and enforce application ownership.

Officer endpoints are under `/api/officer` and require an authenticated `officer` session:

- `GET /api/officer/dashboard`
- `GET /api/officer/applications`
- `GET /api/officer/applications/<application_id>`
- `GET /api/officer/applications/<application_id>/documents`
- `POST /api/officer/applications/<application_id>/documents/<document_id>/verify`
- `POST /api/officer/applications/<application_id>/documents/<document_id>/reject`
- `POST/GET/PUT /api/officer/applications/<application_id>/interview`
- `POST /api/officer/applications/<application_id>/interview/complete`
- `POST /api/officer/applications/<application_id>/forward-to-police`
- `POST /api/officer/applications/<application_id>/reject`

Police endpoints are under `/api/police` and require an authenticated `police` session:

- `GET /api/police/dashboard`
- `GET /api/police/applications`
- `GET /api/police/applications/<application_id>`
- `GET /api/police/applications/<application_id>/verification`
- `POST/PUT /api/police/applications/<application_id>/verification`

Admin dispatch endpoints are under `/api/admin/dispatch`:

- `GET /api/admin/dispatch/dashboard`
- `GET /api/admin/dispatch`
- `GET /api/admin/dispatch/eligible`
- `GET /api/admin/dispatch/<application_id>`
- `POST /api/admin/dispatch/<application_id>`
- `GET /api/dispatch/<application_id>` for the owning Applicant or Admin

Passport Generation endpoints are under `/api/admin/passports` and require an authenticated `admin` session:

- `GET /api/admin/passports/eligible`
- `POST /api/admin/passports/generate/<application_id>`
- `GET /api/passports/<application_id>` for an authorized Admin or owning Applicant

## Development Phases

- ✅ COMPLETE: Phase 1 - Foundation and Authentication
- ✅ COMPLETE: Phase 2 - Applicant Module
- ✅ COMPLETE: Phase 3 - Passport Officer Module
- ✅ COMPLETE: Phase 4 - Police Verification Module
- ✅ COMPLETE: Phase 5 - Passport Generation Module
- ✅ COMPLETE: Phase 6 - Admin Passport Dispatch
- ✅ COMPLETE: Phase 7 - Final Integration, Security, Hardening, and Deployment Readiness

All phases are complete and verified. The workflow ends at `PASSPORT_DISPATCHED` with full integration, security headers, error handling, responsive design, and deployment readiness satisfied.

## Collaboration Instructions

Read [docs/DEVELOPMENT_GUIDE.md](docs/DEVELOPMENT_GUIDE.md) before starting. Pull the latest `main`, create a feature branch for your assigned phase, work only within that scope, run all tests, commit your changes, push the feature branch, and open a Pull Request. Wait for review before merging and never modify another developer's branch directly.

Recommended branch names include `feature/phase-3-officer-module`, `feature/phase-4-police-module`, `feature/phase-5-admin-module`, and `feature/phase-6-passport-dispatch`.

## Current Known Warnings

- The frontend currently loads Tailwind from its CDN; production deployments should install and build Tailwind locally.
- Tests may emit a non-blocking `ResourceWarning` related to temporary upload-file cleanup.

## Deployment Readiness

- Set `SECRET_KEY` to a strong random value via `.env`; default `dev-secret-key` is for local development only.
- Set `FLASK_DEBUG=false` and `FLASK_ENV=production` in production.
- Configure `DB_*` values and `UPLOAD_FOLDER` per environment.
- Ensure `.env` is excluded via `.gitignore` (already configured).
- Ensure `uploads/` is writable; the app creates `UPLOAD_FOLDER` on startup.
- Run `mysql < database/schema.sql` and `python database/seed.py` for initial setup.
- Install dependencies from `requirements.txt` with pinned versions.
- Security headers (`X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`) are set for all responses.

## Future Development Roadmap

The current system is feature-complete through dispatch. Future enhancements could include email notifications, local Tailwind build, and containerized deployment.
