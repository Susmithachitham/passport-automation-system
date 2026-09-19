# Passport Automation System

## Project Description

The Passport Automation System is a Flask and MySQL application for managing passport applications, applicant documents, mock payments, and application status tracking. It currently delivers the foundation/authentication work and the complete Applicant Module.

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

The data model supports `applicant`, `officer`, `police`, and `admin` roles. Only the Applicant Module is implemented in the current release; the other roles are reserved for future phases.

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
- ⏳ NOT STARTED: Phase 3 - Passport Officer Module
- ⏳ NOT STARTED: Phase 4 - Police Verification Module
- ⏳ NOT STARTED: Phase 5 - Admin Module
- ⏳ NOT STARTED: Phase 6 - Passport Generation and Dispatch
- ⏳ NOT STARTED: Phase 7 - Final Integration, Security, and Testing

Phase 2 verification completed 20 automated tests and a live flow covering login, dashboard access, application creation and update, five document uploads, mock payment, submission, and final `SUBMITTED` status.

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

Use `.env.example` as the safe template. Set a strong local `SECRET_KEY`, database connection values, and private demo passwords. The application reads `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, and `SECRET_KEY` from the environment.

## Database Setup

`database/schema.sql` creates the `passport_automation` database and the `users`, `applications`, `documents`, and `payments` tables. `database/seed.py` creates or refreshes local demo users and hashes their passwords; it requires the four `DEMO_*_PASSWORD` variables to be set.

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

## Development Phases

- ✅ COMPLETE: Phase 1 - Foundation and Authentication
- ✅ COMPLETE: Phase 2 - Applicant Module
- ⏳ NOT STARTED: Phase 3 - Passport Officer Module
- ⏳ NOT STARTED: Phase 4 - Police Verification Module
- ⏳ NOT STARTED: Phase 5 - Admin Module
- ⏳ NOT STARTED: Phase 6 - Passport Generation and Dispatch
- ⏳ NOT STARTED: Phase 7 - Final Integration, Security, and Testing

Do not claim or implement Phase 3 or later work without an explicit project decision.

## Collaboration Instructions

Read [docs/DEVELOPMENT_GUIDE.md](docs/DEVELOPMENT_GUIDE.md) before starting. Pull the latest `main`, create a feature branch for your assigned phase, work only within that scope, run all tests, commit your changes, push the feature branch, and open a Pull Request. Wait for review before merging and never modify another developer's branch directly.

Recommended branch names include `feature/phase-3-officer-module`, `feature/phase-4-police-module`, `feature/phase-5-admin-module`, and `feature/phase-6-passport-dispatch`.

## Current Known Warnings

- The frontend currently loads Tailwind from its CDN; production deployments should install and build Tailwind locally.
- Tests may emit a non-blocking `ResourceWarning` related to temporary upload-file cleanup.

## Future Development Roadmap

Future work is intentionally not implemented yet: officer review and document verification, police verification, administration, passport generation and dispatch, then final integration, security hardening, and broader testing.
