# Placement Portal V2

A full-stack campus placement management system. **Students** browse and apply to placement drives, **companies** create drives and manage applicants, and the **admin** (placement cell) approves companies and drives and manages users.

## Features

**Student** - register / login, edit profile (branch, CGPA, graduation year, resume link), browse open drives with search, automatic eligibility check (CGPA, branch, year, deadline), apply, withdraw an application, track status, export application history as CSV (background job), delete own account.

**Company** - register (needs admin approval), edit profile, full CRUD on placement drives, view applicants per drive, shortlist / select / reject (the student is emailed by a background job).

**Admin** - dashboard statistics, approve / reject / blacklist / delete companies, blacklist / delete students, approve / reject / close / delete drives, search across companies, students, drives and applications.

**Background jobs (Celery + Redis)**

| Job | Trigger | What it does |
|---|---|---|
| `export_applications_csv` | Student clicks *Export* | Builds a CSV, emails it and makes it downloadable |
| `send_status_update_email` | Company changes an application status | Emails the student |
| `daily_deadline_reminders` | Celery beat, daily 08:00 | Emails eligible students about drives closing within 48 hours |
| `monthly_activity_report` | Celery beat, 1st of the month 09:00 | Emails admins an HTML report (also saved in `backend/exports/`) |

## Requirements coverage

| Requirement | Where it is implemented |
|---|---|
| User authentication (login + registration) | `backend/routes/auth.py`; Flask-Security-Too handles password hashing, roles and users; Vue pages `Login`, `StudentRegister`, `CompanyRegister` |
| Token-based authentication | Login returns a Flask-Security access token; every protected route uses `@auth_required("token")` and a role check; the Axios interceptor in `frontend/src/api.js` sends the `Authentication-Token` header |
| RESTful API | Resource-based endpoints under `/api` for auth, student, company and admin, with correct HTTP verbs and status codes (see *API documentation*) |
| CRUD operations | Drives: create, read, update, delete (company and admin). Applications: create (apply), read, update status, delete (withdraw). Profiles: read and update. Users: admin and self delete |
| Backend jobs (optional) | Celery + Redis: CSV export, status e-mails, daily deadline reminders, monthly report (see *Background jobs*) |
| Stack | Flask, SQLAlchemy, Flask-Security-Too, Vue 3, Axios, Celery, Redis |

## Tech stack

- **Backend:** Flask, Flask-SQLAlchemy (SQLAlchemy 2), Flask-Security-Too (token authentication + roles), Flask-Mail, Flask-CORS
- **Frontend:** Vue 3, Vue Router, Axios, Bootstrap 5
- **Jobs:** Celery, Redis, MailHog (local email testing)
- **Database:** SQLite (any SQLAlchemy URL works via `DATABASE_URL`)

## Project structure

```
placement-portal-v2/
├── backend/
│   ├── app.py              # app factory (Security, CORS, Celery, blueprints)
│   ├── config.py           # all settings, read from environment / .env
│   ├── models.py           # SQLAlchemy models + Flask-Security datastore
│   ├── seed.py             # roles + default admin
│   ├── utils.py            # validation helpers, token_roles decorator
│   ├── routes/             # auth.py, admin.py, company.py, student.py
│   ├── tasks.py            # Celery jobs
│   ├── celery_worker.py    # Celery entry point
│   ├── smoke_test.py       # end-to-end API test (no Redis needed)
│   └── requirements.txt
└── frontend/               # Vue 3 app (src/api.js, router, store, views)
```

## Installation

### Prerequisites
Python 3.10+, Node.js 18+, and (only for background jobs) Redis. MailHog is optional.

### 1. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # then edit the secrets
python app.py                     # http://127.0.0.1:5000
```
Tables and the default admin are created automatically on first start.

**Default admin (demo only - change in `.env`):** `admin@example.com` / `admin123`

### 2. Frontend
```bash
cd frontend
npm install
npm run serve                     # http://localhost:8080
```
The dev server proxies `/api` to Flask, so no extra configuration is needed.

### 3. Background jobs (optional)
```bash
redis-server                                                      # terminal 1
cd backend && celery -A celery_worker.celery_app worker -l info   # terminal 2
cd backend && celery -A celery_worker.celery_app beat -l info     # terminal 3 (scheduled jobs)
```
For email testing run MailHog (`mailhog`) and open http://localhost:8025. Without Redis the app still works; the export button reports that the job service is unavailable.
On Windows, add `--pool=solo` to the worker command.

### 4. Run the tests
```bash
cd backend && python smoke_test.py
```

## Authentication

Login returns an access token issued by Flask-Security. Send it on every protected request:

```
Authentication-Token: <token>
```

Tokens expire after 8 hours and are invalidated on logout or when the account is blacklisted. Missing / invalid token -> `401`; wrong role -> `403`.

```bash
curl -X POST http://127.0.0.1:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}'

curl http://127.0.0.1:5000/api/admin/stats -H "Authentication-Token: <token>"
```

## API documentation

All endpoints are under `/api`, accept and return JSON, and report errors as `{"message": "..."}`.

### Auth
| Method | Endpoint | Auth | Body / notes |
|---|---|---|---|
| POST | `/auth/register/student` | - | `email`, `password` (min 8), `full_name` |
| POST | `/auth/register/company` | - | `email`, `password`, `full_name`, `company_name`, `hr_contact?`, `website?` |
| POST | `/auth/login` | - | `email`, `password` -> `{token, user}` |
| POST | `/auth/logout` | token | invalidates the user's tokens |
| GET | `/auth/me` | token | current user |
| GET | `/health` | - | health check |

### Student (role `student`)
| Method | Endpoint | Description |
|---|---|---|
| GET / PUT | `/student/profile` | read / update profile (`full_name`, `branch`, `cgpa` 0-10, `graduation_year`, `resume_path`) |
| DELETE | `/student/account` | delete own account |
| GET | `/student/drives?q=&eligible=true` | open approved drives with `eligible`, `ineligible_reason`, `applied` |
| POST | `/student/drives/<id>/apply` | apply (checks deadline + eligibility; 409 if already applied) |
| GET | `/student/applications` | own applications |
| DELETE | `/student/applications/<id>` | withdraw (only while status is `Applied`) |
| POST | `/student/export` | start CSV export job -> `202 {task_id}` |
| GET | `/student/export/<task_id>` | `202` while running, `200` + CSV file when done |

### Company (role `company`)
| Method | Endpoint | Description |
|---|---|---|
| GET / PUT | `/company/profile` | read / update company profile |
| GET | `/company/drives` | own drives |
| POST | `/company/drives` | create (approved companies only): `job_title`, `job_description`, `application_deadline` (ISO 8601), `eligible_branches`, `min_cgpa`, `eligible_years` |
| GET / PUT / DELETE | `/company/drives/<id>` | read / update / delete (editing sends the drive back to `Pending`) |
| GET | `/company/drives/<id>/applications` | applicants of a drive |
| PUT | `/company/applications/<id>/status` | `{"status": "Shortlisted" \| "Selected" \| "Rejected"}` |

### Admin (role `admin`)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/admin/stats` | totals and status breakdowns |
| GET | `/admin/companies?q=` | list / search companies |
| PUT | `/admin/companies/<user_id>/status` | `{"action": "approve" \| "reject" \| "blacklist" \| "activate"}` |
| DELETE | `/admin/companies/<user_id>` | delete company and its drives |
| GET | `/admin/students?q=` | list / search students |
| PUT | `/admin/students/<user_id>/status` | `{"action": "blacklist" \| "activate"}` |
| DELETE | `/admin/students/<user_id>` | delete student |
| GET | `/admin/drives?q=&status=` | list / search drives |
| PUT | `/admin/drives/<id>/status` | `{"status": "Pending" \| "Approved" \| "Rejected" \| "Closed"}` |
| DELETE | `/admin/drives/<id>` | delete drive |
| GET | `/admin/applications?q=` | list / search applications |

## Demo walkthrough (about 3 minutes)

1. Start the backend and frontend (see *Installation*) and open http://localhost:8080.
2. Log in as the admin (`admin@example.com` / `admin123`).
3. In a private window register a **company**, log in, and note that creating drives is disabled until approval.
4. As admin, open *Companies* and **Approve** it. The company can now create a drive, which starts as `Pending`.
5. As admin, **Approve** the drive under *Drives*.
6. Register a **student**, fill in branch, CGPA and graduation year, open the drive and apply. Applying is blocked if the student is not eligible or the deadline has passed.
7. As the company, open the drive's applicants and set a status (Shortlisted, Selected or Rejected). With Redis, the worker and MailHog running, the student receives an e-mail.
8. As the student, click *Export* to receive the CSV of the application history.

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: flask_security` | Activate the virtual environment and run `pip install -r requirements.txt` inside `backend/` |
| Frontend shows network errors | Make sure the backend is running on port 5000; the dev server proxies `/api` to it (`frontend/vue.config.js`) |
| Export button says the job service is unavailable | Start Redis and the Celery worker (see *Background jobs*); the rest of the app works without them |
| Login returns 401 after a long time | Tokens expire after 8 hours or after logout; log in again |
| Want a fresh database | Stop the server, delete `backend/placement_portal.db`, start again (the admin account is re-created) |
| Windows: Celery worker does not start | Add `--pool=solo` to the worker command |

## Data model

`User` (+ `Role`, Flask-Security) 1-1 `StudentProfile` or `CompanyProfile`; `CompanyProfile` 1-N `PlacementDrive`; `StudentProfile` N-M `PlacementDrive` through `Application` (unique per student and drive).

## Security notes

- Passwords are hashed by Flask-Security; the API is stateless and token based (no cookies, so no CSRF surface).
- Secrets come from `.env` (not committed). Change `SECRET_KEY`, `SECURITY_PASSWORD_SALT` and the admin password before any real deployment.
- All input is validated server-side; role checks use `@auth_required('token')` + `@roles_required(...)`.
