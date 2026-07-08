# Gunaso — Civic Feedback & Grievance Platform

> **Gunaso** (गुनासो) means *complaint* or *grievance* in Nepali.

Gunaso is an open civic-tech platform that lets citizens submit complaints, feedback, and concerns about any organization or public service — and routes them directly to the right people.

Organizations register on the platform, define their internal departments and routing rules, and citizens get transparent, trackable resolution for every submission they make.

---

## Features

- **Multi-organization support** — NGOs, government bodies, private companies, ward offices, and more
- **Anonymous & guest submissions** — no account required; anonymous identity is never revealed to organizations
- **Public tracking** — every submission gets a `GUN-YYYY-NNNNN` reference for status tracking
- **Validated status lifecycle** — `submitted → acknowledged → in_review → resolved / rejected (→ closed)`, with `escalated`; every change recorded in an append-only audit trail
- **JWT authentication** — short-lived access tokens in memory, rotating refresh tokens in httpOnly cookies
- **File attachments** — validated server-side (size, type, magic bytes)
- **Org dashboard** — organization staff manage submissions through a clean Vue 3 interface
- **API docs** — OpenAPI schema with Swagger UI at `/api/v1/schema/swagger-ui/`

See `INSTRUCTION.md` for setup and `CLAUDE.md` for the full architecture reference (including the roadmap: Channels, Celery, routing engine).

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | Django 5 + Django REST Framework |
| Frontend | Vue 3 + Vite + Pinia + Vue Router |
| Styling | Tailwind CSS |
| Database | PostgreSQL 16 |
| Cache / Rate limiting | Redis 7 |
| Auth | JWT (djangorestframework-simplejwt, rotating refresh + blacklist) |
| API Docs | drf-spectacular (Swagger UI) |
| Containerization | Docker + Docker Compose |
| Reverse Proxy | Nginx |

---

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Compose)
- Git

### 1. Clone the repository

```bash
git clone https://github.com/your-org/gunaso.git
cd gunaso
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and set at minimum:
- `SECRET_KEY` — generate with `python -c "import secrets; print(secrets.token_urlsafe(50))"`
- `POSTGRES_PASSWORD` — a strong database password
- `JWT_SIGNING_KEY` — another secret token

### 3. Start the full stack

```bash
docker compose up --build
```

Services will start in dependency order. First boot may take a few minutes to build images.

### 4. Access the application

| Service | URL |
|---------|-----|
| Frontend (Vue) | http://localhost |
| API (REST) | http://localhost/api/v1/ |
| API docs (Swagger UI) | http://localhost/api/v1/schema/swagger-ui/ |
| Django Admin | http://localhost/admin/ |

### 5. Seed sample data & create a superuser (first time only)

```bash
docker compose exec backend python manage.py seed_data
docker compose exec backend python manage.py createsuperuser
```

---

## Development Workflow

### Backend only (without Docker)

```bash
cd backend/gunaso-api
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env             # sqlite by default; set DATABASE_URL for Postgres
python manage.py migrate
python manage.py seed_data
python manage.py runserver       # http://localhost:8000
```

### Frontend only (without Docker)

```bash
cd frontend/gunaso-ui
npm install
npm run dev                      # http://localhost:3000 (proxies /api to :8000)
```

### Run tests

```bash
# Backend (bare metal)
cd backend/gunaso-api && pytest

# Backend (Docker)
docker compose exec backend pytest
```

### Useful Compose commands

```bash
docker compose up -d              # start in background
docker compose logs -f backend    # tail backend logs
docker compose exec backend bash  # open shell in backend container
docker compose down               # stop all services
docker compose down -v            # stop and delete volumes (wipes DB)
```

---

## Project Structure

```
gunaso/
├── backend/gunaso-api/    # Django project (Python)
│   ├── gunaso/            # Settings, urls, pagination, error envelope
│   ├── apps/
│   │   ├── accounts/      # User model, JWT auth (register/login/refresh/logout)
│   │   ├── organizations/ # Organization, Stakeholder models
│   │   └── submissions/   # Submission, Category, StatusUpdate + services
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/gunaso-ui/    # Vue 3 application
│   ├── src/
│   │   ├── api/           # Axios client (in-memory token + cookie refresh)
│   │   ├── stores/        # Pinia stores
│   │   ├── views/         # Page-level components
│   │   ├── components/    # Reusable UI components
│   │   └── router/
│   ├── package.json
│   └── Dockerfile
├── nginx/
│   └── nginx.conf
├── docker-compose.yml
├── .env.example
├── INSTRUCTION.md         # Full setup & run guide
├── CLAUDE.md              # Developer north-star document
└── README.md
```

---

## API Overview

All endpoints are versioned under `/api/v1/`.

```
POST   /api/v1/auth/register/            # create account (sets refresh cookie)
POST   /api/v1/auth/login/               # email + password
POST   /api/v1/auth/refresh/             # rotate refresh cookie → new access token
POST   /api/v1/auth/logout/              # blacklist refresh token
GET    /api/v1/auth/me/

GET    /api/v1/organizations/            # verified orgs (search, filter, paginate)
POST   /api/v1/organizations/            # register an organization
GET    /api/v1/organizations/{slug}/
GET    /api/v1/organizations/{slug}/submissions/   # org admin
GET    /api/v1/organizations/{slug}/stats/         # org admin

POST   /api/v1/submissions/              # guests allowed (throttled)
GET    /api/v1/submissions/my/           # own submissions
GET    /api/v1/submissions/track/{ref}/  # public tracking (identity redacted)
GET    /api/v1/submissions/{ref}/
PATCH  /api/v1/submissions/{ref}/status/ # validated transitions, org admin

GET    /api/v1/categories/
GET    /api/v1/org/submissions/          # org-admin dashboard
GET    /api/v1/org/stats/
GET    /api/v1/health/
```

Full API documentation is generated by drf-spectacular and available at `/api/v1/schema/swagger-ui/`.

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes following the conventions in [CLAUDE.md](./CLAUDE.md)
4. Write tests for new functionality
5. Ensure all tests pass: `docker compose exec backend pytest`
6. Open a pull request with a clear description of what and why

Please read [CLAUDE.md](./CLAUDE.md) before contributing — it is the authoritative guide for all architecture decisions, coding conventions, and domain concepts.

---

## License

MIT License — see [LICENSE](./LICENSE) for details.

---

## Acknowledgements

Built to empower citizens and strengthen accountability in public and private institutions.
