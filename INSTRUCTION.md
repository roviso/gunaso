# Gunaso — Setup & Run Instructions

Two ways to run the project:

- **Option A — Docker Compose** (recommended): the full production-like stack — PostgreSQL 16,
  Redis 7, Django API (gunicorn), built Vue SPA, and Nginx — with one command.
- **Option B — Bare metal**: Django dev server + Vite dev server directly on your machine,
  for day-to-day development with hot reload.

---

## Option A — Docker Compose (full stack)

### Prerequisites
- Docker Desktop ≥ 4.x (includes Docker Compose v2)

### Steps

```bash
# 1. Clone and enter the project
git clone <repo-url> gunaso
cd gunaso

# 2. Create your environment file
cp .env.example .env
```

Edit `.env` and set real values — at minimum:

| Variable | What to set |
|---|---|
| `SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `JWT_SIGNING_KEY` | A second, different random key (same command) |
| `POSTGRES_PASSWORD` | A strong database password |
| `DEBUG` | `True` for local, **`False` for production** |

```bash
# 3. Build and start everything
docker compose up --build -d

# 4. (First time) load sample data — orgs, categories, demo submissions
docker compose exec backend python manage.py seed_data

# 5. (Optional) create your own superuser for /admin/
docker compose exec backend python manage.py createsuperuser
```

### Open the app

| URL | What |
|---|---|
| http://localhost | The Gunaso web app (via Nginx) |
| http://localhost/api/v1/health/ | API health check |
| http://localhost/api/v1/schema/swagger-ui/ | Interactive API docs |
| http://localhost/admin/ | Django admin |

### Sample logins (after `seed_data`)

| Email | Password | Role |
|---|---|---|
| `citizen@gmail.com` | `password123` | Citizen |
| `admin@nepaltel.com` | `password123` | Org admin (Nepal Telecom) |
| `admin@kmcity.gov.np` | `password123` | Org admin (Kathmandu Metro) |
| `superadmin@gunaso.com` | `admin123` | Platform superuser |

### Useful commands

```bash
docker compose logs -f backend        # follow API logs
docker compose exec backend pytest    # run the backend test suite
docker compose exec backend python manage.py migrate
docker compose down                   # stop everything
docker compose down -v                # stop AND wipe the database (destructive!)
```

---

## Option B — Bare metal (development)

### Prerequisites
- Python 3.11+ (3.12 recommended)
- Node.js 20+
- (Optional) PostgreSQL 16 — without it, the backend falls back to a local sqlite file
- (Optional) Redis 7 — without it, rate-limit counters use in-process memory

### 1. Backend

```bash
cd backend/gunaso-api

# Create and activate a virtualenv
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS / Linux

pip install -r requirements-dev.txt

# Environment
cp .env.example .env
# To use PostgreSQL, uncomment and adjust DATABASE_URL in .env:
#   DATABASE_URL=postgresql://gunaso_user:password@localhost:5432/gunaso_db
# (create the database first: createdb gunaso_db)

# Migrate + seed + run
python manage.py migrate
python manage.py seed_data
python manage.py runserver        # http://localhost:8000
```

> Windows shortcut: `backend\gunaso-api\start.bat` does all of the above.

### 2. Frontend (separate terminal)

```bash
cd frontend/gunaso-ui
npm install
npm run dev                       # http://localhost:3000
```

The Vite dev server proxies `/api` and `/media` to `http://localhost:8000`, so auth
cookies work out of the box. Don't point the browser at the Django port directly.

### 3. Run tests

```bash
cd backend/gunaso-api
pytest
```

---

## Production checklist

Before deploying, make sure:

- [ ] `DEBUG=False` in `.env` (the app refuses to boot without a real `SECRET_KEY`)
- [ ] `SECRET_KEY` and `JWT_SIGNING_KEY` are unique 50+ char random values
- [ ] `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` list your real domain(s)
- [ ] TLS terminated in front of the stack (then set `SECURE_SSL_REDIRECT=True`)
- [ ] `POSTGRES_PASSWORD` is strong; database port is **not** exposed publicly
- [ ] Database backups scheduled (`pg_dump` the `postgres_data` volume host)
- [ ] `docker compose exec backend pytest` passes
- [ ] Default seeded accounts removed or passwords changed (don't run `seed_data` in prod)

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `SECRET_KEY environment variable is required` | You set `DEBUG=False` without a `SECRET_KEY` — set one in `.env` |
| 401 loops in the browser | You're bypassing the proxy; use http://localhost (Docker) or :3000 (Vite), not the raw API port |
| `password authentication failed for user` | `.env` Postgres credentials changed after the volume was created — `docker compose down -v` (wipes data) or fix the password |
| CORS errors in console | Add your origin to `CORS_ALLOWED_ORIGINS` in `.env` and restart the backend |
| Attachment rejected | Allowed: jpg, jpeg, png, gif, webp, pdf, doc, docx, ≤ 10MB (env `MAX_ATTACHMENT_SIZE_MB`) |
| 429 Too Many Requests | You hit a throttle (auth 10/min, submissions 10/hour) — wait, or tune `THROTTLE_*` env vars |
