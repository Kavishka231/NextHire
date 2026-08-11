# NextHire

NextHire is a job search and job tracking platform. It combines a FastAPI backend, PostgreSQL database, Redis/Celery background jobs, and a static HTML/CSS/JavaScript frontend served by Nginx.

The app is designed to help users:

- Register, log in, and manage an authenticated session.
- Search jobs from Adzuna, with mock results available when API keys are not configured.
- Save jobs into a personal job pipeline.
- Track saved jobs by status, such as saved, applied, interview, offer, and rejected.
- Add notes to saved jobs.
- View dashboard statistics for saved jobs, activity, companies, and salaries.
- Maintain candidate profiles and notifications.
- Let employers publish jobs and manage candidate applications.
- Provide role-controlled administration and audited security actions.
- Send reminder emails for stale applications through a Celery worker.

## Tech Stack

Backend:

- Python
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Redis
- Celery
- Pydantic
- PyJWT and Passlib for authentication/security

Frontend:

- Static HTML
- CSS
- Vanilla JavaScript
- Nginx for containerized static file serving

Infrastructure:

- Docker Compose
- PostgreSQL 15
- Redis 7

## Project Structure

```text
NextHire/
  backend/
    alembic/                 Database migration environment
    api/v1/routers/          FastAPI route modules
    app/                     App configuration and database setup
    core/                    Security, dependencies, and exceptions
    models/                  SQLAlchemy ORM models
    schemas/                 Pydantic request/response schemas
    services/                Business logic and external integrations
    tasks/                   Celery app and scheduled reminder task
    tests/                   Pytest test suite
    main.py                  FastAPI app entry point
    requirements.txt         Backend Python dependencies
    Dockerfile               Backend container image
  frontend/
    css/                     Stylesheets
    js/                      Browser-side JavaScript
    *.html                   Static pages
    Dockerfile               Optional frontend image
    nginx.conf               Nginx config with API proxy
  docker-compose.yml         Local multi-service environment
  README.md                  Project documentation
```

## Main Services

`docker-compose.yml` defines these services:

| Service | Purpose | Port |
| --- | --- | --- |
| `db` | PostgreSQL database | private |
| `redis` | Redis broker/result backend | private |
| `backend` | FastAPI API server | private |
| `worker` | Celery worker for reminders | none |
| `scheduler` | Celery Beat daily reminder scheduler | none |
| `frontend` | Static frontend served by Nginx | `5500` |

## Environment Variables

Copy `.env.example` to `.env` and replace every placeholder. Never commit
`.env`. Production configuration and administrator bootstrap instructions are
in `DEPLOYMENT.md`.

Notes:

- Production requires a strong `SECRET_KEY` and PostgreSQL `DATABASE_URL`.
- `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` are optional during development. If they are empty, the Adzuna service can return mock job data.
- Email variables are used by `backend/services/email_service.py` and the Celery reminder task.
- Password-reset links are one-time, expire after 30 minutes by default, and
  require the Celery worker plus working SMTP credentials.

## Run With Docker

From the project root:

```bash
cd NextHire
docker compose up -d --build
```

After startup:

- Frontend: `http://localhost:5500`
- Backend API: `http://localhost:5500/api/v1`
- Swagger and ReDoc are available on the private backend network.
- Liveness/readiness: `/health` and `/ready` on the private backend network.

Run migrations as the controlled operations service:

```bash
docker compose --profile operations run --rm migrate
```

Stop services:

```bash
docker compose down
```

Stop services and remove the PostgreSQL volume:

```bash
docker compose down -v
```

## Run Backend Locally

Start PostgreSQL and Redis first. You can use Docker for only those services:

```bash
cd NextHire
docker compose up db redis
```

In another terminal:

```bash
cd NextHire/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m alembic upgrade head
python -m uvicorn main:app --reload
```

The API will run at:

```text
http://localhost:8000
```

## Run Frontend Locally

The frontend is static HTML/CSS/JS. The Docker Compose setup serves it through Nginx at `http://localhost:5500`.

The browser uses the same-origin `/api/v1` path, which Nginx proxies to the
private backend service. A separate frontend host can explicitly set
`window.NEXTHIRE_API_URL` before loading `frontend/js/api.js`.

## Database

The backend uses SQLAlchemy models and Alembic migrations.

Main tables:

- `users`
- `refresh_tokens`
- `jobs`
- `saved_jobs`
- `notes`
- `user_profiles`
- `notifications`
- `job_applications`
- `password_reset_tokens`
- `search_logs`
- `admin_audit_logs`

Run migrations:

```bash
cd NextHire/backend
python -m alembic upgrade head
```

Create a new migration after model changes:

```bash
python -m alembic revision --autogenerate -m "describe change"
```

## API Overview

Public API path:

```text
/api/v1
```

Application routes use this prefix. The `/health` and `/ready` operational
endpoints are served at the site root.

Health:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Check API health |

Authentication:

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/auth/register` | Create a user account |
| `POST` | `/auth/login` | Log in and receive tokens |
| `GET` | `/auth/me` | Return the current authenticated user |
| `POST` | `/auth/refresh` | Refresh an access token |
| `POST` | `/auth/logout` | Revoke/logout refresh token |
| `POST` | `/auth/forgot-password` | Start password reset flow |
| `PUT` | `/auth/change-password` | Change authenticated user's password |

Job search:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/search/jobs` | Search jobs with filters |
| `GET` | `/search/categories` | Get job categories |

Example search query:

```text
GET /api/v1/search/jobs?keywords=python&location=London&page=1&results_per_page=20
```

Jobs:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/jobs` | List cached jobs |
| `GET` | `/jobs/{job_id}` | Get one cached job |

Saved jobs:

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/saved-jobs` | Save a job for the current user |
| `GET` | `/saved-jobs` | List saved jobs for the current user |
| `DELETE` | `/saved-jobs/{job_id}` | Remove a saved job |
| `PATCH` | `/saved-jobs/{saved_job_id}/status` | Update saved job status |

Notes:

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/notes` | Add a note to a saved job |
| `GET` | `/notes/job/{saved_job_id}` | List notes for a saved job |
| `PUT` | `/notes/{note_id}` | Update a note |
| `DELETE` | `/notes/{note_id}` | Delete a note |

Stats:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/stats` | Return dashboard statistics for the current user |

Most app routes require an `Authorization: Bearer <access_token>` header.

## Frontend Pages

Important frontend pages:

| Page | Purpose |
| --- | --- |
| `index.html` | Entry page/redirect behavior |
| `login.html` | Login form |
| `register.html` | Registration form |
| `forgot-password.html` | Password reset request |
| `dashboard.html` | User dashboard and analytics |
| `search.html` | Job search page |
| `jobs.html` | Saved jobs board, status tracking, and notes UI |

Important frontend scripts:

| Script | Purpose |
| --- | --- |
| `frontend/js/api.js` | Shared API helper |
| `frontend/js/auth.js` | Authentication UI/session helpers |
| `frontend/js/search.js` | Job search UI |
| `frontend/js/jobs.js` | Saved jobs board UI |
| `frontend/js/stats.js` | Dashboard stats UI |

## Background Jobs

Celery is configured in:

```text
backend/tasks/celery_app.py
```

The reminder task is in:

```text
backend/tasks/reminder_task.py
```

It is intended to email users about applications that have stayed in the `applied` status for more than 7 days.

Run the worker with Docker Compose:

```bash
docker compose up worker
```

Run a worker locally:

```bash
cd NextHire/backend
celery -A tasks.celery_app worker --loglevel=info
```

## Testing

The backend test suite uses Pytest and FastAPI's test client.

Run tests:

```bash
cd NextHire/backend
python -m pytest
```

The tests cover:

- Authentication
- Token refresh/logout/change-password flows
- Job search and categories
- Notes
- Saved job status changes
- Dashboard statistics
- Profiles and notifications
- Employer jobs and candidate applications
- Administration, audit logging, rate limits, and production configuration
- PostgreSQL integrity constraints

## Development Workflow

Changes should go through a reviewed pull request. CI runs backend tests,
PostgreSQL migration and integrity checks, frontend JavaScript validation,
dependency and secret audits, Compose validation, and container image builds.

## Known Notes

- Some files contain encoding artifacts in comments or display text. They do not usually affect runtime behavior, but they can be cleaned up later.
- `.env`, databases, virtual environments, cache files, and logs are intentionally ignored by `.gitignore`.
- `__pycache__` files should not be committed.

## Useful Commands

```bash
# Start everything
docker compose up --build

# Start only database and Redis
docker compose up db redis

# Run backend locally
cd backend
python -m uvicorn main:app --reload

# Run migrations
cd backend
python -m alembic upgrade head

# Run tests
cd backend
python -m pytest

# Run Celery worker locally
cd backend
celery -A tasks.celery_app worker --loglevel=info
```

## License

No license file is currently included. Add a license before publishing or distributing the project publicly.
