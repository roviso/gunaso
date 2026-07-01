# Gunaso — Civic Feedback & Grievance Platform

> **Gunaso** (गुनासो) means *complaint* or *grievance* in Nepali.

Gunaso is an open civic-tech platform that lets citizens submit complaints, feedback, and concerns about any organization or public service — and routes them directly to the right people.

Organizations register on the platform, define their internal departments and routing rules, and citizens get transparent, trackable resolution for every submission they make.

---

## Features

- **Multi-organization support** — NGOs, government bodies, private companies, ward offices, and more
- **Smart routing** — submissions are routed to the right department or stakeholder based on category and routing rules
- **Full status lifecycle** — `submitted → acknowledged → in-review → resolved / escalated`
- **Real-time updates** — WebSocket-powered live notifications via Django Channels
- **JWT authentication** — secure, stateless auth for citizens and organization staff
- **File attachments** — attach photos, documents, or audio to submissions
- **Async processing** — emails, notifications, and escalations handled by Celery workers
- **Admin dashboard** — organization staff manage submissions through a clean Vue 3 interface

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | Django 5 + Django REST Framework |
| WebSockets | Django Channels + Daphne |
| Frontend | Vue 3 + Vite + Pinia + Vue Router |
| Styling | Tailwind CSS |
| Database | PostgreSQL 16 |
| Cache / Broker | Redis 7 |
| Task Queue | Celery + Celery Beat |
| Auth | JWT (djangorestframework-simplejwt) |
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
| Django Admin | http://localhost/admin/ |
| API directly (dev) | http://localhost:8000/api/v1/ |
| Frontend directly (dev) | http://localhost:5173/ |

### 5. Create a superuser (first time only)

```bash
docker compose exec backend python manage.py createsuperuser
```

---

## Development Workflow

### Backend only (without Docker)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example ../.env       # configure to point at local postgres/redis
python manage.py migrate
python manage.py runserver
```

### Frontend only (without Docker)

```bash
cd frontend
npm install
npm run dev
```

### Run tests

```bash
# Backend
docker compose exec backend pytest

# Frontend
docker compose exec frontend npm run test
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
├── backend/           # Django project (Python)
│   ├── config/        # Django settings, urls, asgi, wsgi, celery
│   ├── apps/
│   │   ├── accounts/      # User model, JWT auth
│   │   ├── organizations/ # Organization, Department models
│   │   ├── submissions/   # Submission, Category, Attachment models
│   │   ├── routing/       # RoutingRule, Stakeholder assignment
│   │   ├── notifications/ # WebSocket consumers, email tasks
│   │   └── analytics/     # Read-only reporting endpoints
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/          # Vue 3 application
│   ├── src/
│   │   ├── stores/    # Pinia stores
│   │   ├── views/     # Page-level components
│   │   ├── components/# Reusable UI components
│   │   ├── composables/
│   │   ├── router/
│   │   └── api/       # Axios client modules
│   ├── package.json
│   └── Dockerfile
├── nginx/
│   └── nginx.conf
├── docker-compose.yml
├── .env.example
├── .gitignore
├── CLAUDE.md          # Developer north-star document
└── README.md
```

---

## API Overview

All endpoints are versioned under `/api/v1/`.

```
POST   /api/v1/auth/register/
POST   /api/v1/auth/login/
POST   /api/v1/auth/refresh/

GET    /api/v1/organizations/
POST   /api/v1/organizations/
GET    /api/v1/organizations/{id}/

POST   /api/v1/submissions/
GET    /api/v1/submissions/{id}/
PATCH  /api/v1/submissions/{id}/status/

GET    /api/v1/categories/
GET    /api/v1/routing-rules/

WS     /ws/submissions/{id}/   # real-time status updates
```

Full API documentation is generated by drf-spectacular and available at `/api/v1/schema/redoc/`.

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
