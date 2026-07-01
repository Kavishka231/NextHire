# NextHire

NextHire is a job search and job tracking platform. It combines a FastAPI backend, PostgreSQL database, Redis/Celery background jobs, and a static HTML/CSS/JavaScript frontend served by Nginx.

The app is designed to help users:

- Register, log in, and manage an authenticated session.
- Search jobs from Adzuna, with mock results available when API keys are not configured.
- Save jobs into a personal job pipeline.
- Track saved jobs by status, such as saved, applied, interview, offer, and rejected.
- Add notes to saved jobs.
- View dashboard statistics for saved jobs, activity, companies, and salaries.
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
- python-jose and Passlib for authentication/security

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
  requirements.txt           Root-level requirements placeholder
  README.md                  Project documentation
```

## Main Services

`docker-compose.yml` defines these services:

| Service | Purpose | Port |
| --- | --- | --- |
| `db` | PostgreSQL database | `5432` |
| `redis` | Redis broker/result backend | `6379` |
| `backend` | FastAPI API server | `8000` |
| `worker` | Celery worker for reminders | none |
| `frontend` | Static frontend served by Nginx | `5500` |

## Environment Variables

Create a `.env` file in the project root: `NextHire/.env`.

Example:

```env
APP_NAME=NextHire
SECRET_KEY=change-this-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

DATABASE_URL=postgresql://postgres:postgres@localhost:5432/nexthire
REDIS_URL=redis://localhost:6379/0

ADZUNA_APP_ID=
ADZUNA_APP_KEY=

MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_FROM=noreply@nexthire.com
MAIL_FROM_NAME=NextHire
MAIL_SERVER=smtp.mailtrap.io
MAIL_PORT=587
```

Notes:

- `SECRET_KEY` is required by `backend/app/config.py`.
- `DATABASE_URL` is required by SQLAlchemy and Alembic.
- `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` are optional during development. If they are empty, the Adzuna service can return mock job data.
- Email variables are used by `backend/services/email_service.py` and the Celery reminder task.

## Run With Docker

From the project root:

```bash
cd NextHire
docker compose up --build
```

After startup:

- Frontend: `http://localhost:5500`
- Backend API: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`
- ReDoc docs: `http://localhost:8000/redoc`
- Health check: `http://localhost:8000/health`

Run migrations inside the backend container:

```bash
docker compose exec backend alembic upgrade head
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

If you serve it manually, make sure the frontend can reach the backend API. `frontend/js/api.js` currently points to:

```js
const BASE_URL = "http://localhost:8000/api/v1";
```

## Database

The backend uses SQLAlchemy models and Alembic migrations.

Main tables:

- `users`
- `refresh_tokens`
- `jobs`
- `saved_jobs`
- `notes`

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

Base URL:

```text
http://localhost:8000/api/v1
```

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

## Development Workflow

Recommended branch strategy:

```bash
git checkout main
git pull origin main
git checkout -b feature/my-feature
```

After changes:

```bash
git add <files>
git commit -m "Describe the change"
git push -u origin feature/my-feature
```

Open a pull request, test the branch, then merge into `main`.

## Current Feature Branches

These branches were created to separate backend fixes/features before merging to `main`:

| Branch | Purpose |
| --- | --- |
| `feature/auth-api-fixes` | Auth routes, token flow, password hashing, and user response fixes |
| `feature/job-search-api` | Job search and cached job route wiring |
| `feature/saved-jobs-api` | Saved job create/list/status response fixes |
| `fix/stats-service-syntax` | Restores the stats service implementation after a duplicate-paste syntax issue |

If `main` does not pass the full test suite, merge or test these branches together before treating the API as complete.

## Known Notes

- The codebase currently contains both older and newer frontend/API flows. The newer dashboard/search/jobs pages expect the fuller API described above.
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
