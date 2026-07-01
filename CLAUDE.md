# CLAUDE.md — Gunaso Developer North Star

> This document is the authoritative reference for all development decisions on the Gunaso platform.
> Read it before writing any code. Keep it updated when architectural decisions change.
> When in doubt: this document wins over instinct.

---

## Table of Contents

1. [Project Overview & Mission](#1-project-overview--mission)
2. [Tech Stack & Rationale](#2-tech-stack--rationale)
3. [Project Structure](#3-project-structure)
4. [Domain Model & Key Concepts](#4-domain-model--key-concepts)
5. [Status Workflow](#5-status-workflow)
6. [API Design Philosophy](#6-api-design-philosophy)
7. [Frontend Architecture](#7-frontend-architecture)
8. [Real-time Architecture (WebSockets)](#8-real-time-architecture-websockets)
9. [Async Task Architecture (Celery)](#9-async-task-architecture-celery)
10. [Authentication & Authorization](#10-authentication--authorization)
11. [Dev Environment Setup](#11-dev-environment-setup)
12. [Docker Compose Usage](#12-docker-compose-usage)
13. [Environment Variables Reference](#13-environment-variables-reference)
14. [Coding Conventions](#14-coding-conventions)
15. [Testing Standards](#15-testing-standards)
16. [Security Patterns](#16-security-patterns)
17. [Adding New Features — Checklist](#17-adding-new-features--checklist)

---

## 1. Project Overview & Mission

**Gunaso** (गुनासो — Nepali for *complaint* or *grievance*) is a civic-tech platform designed to give citizens a structured, trackable channel to hold organizations accountable.

### The Problem We Solve

Citizens often have no clear, reliable way to surface complaints to:
- Government bodies (ward offices, municipality departments)
- Public utilities (water, electricity, transport)
- NGOs and development organizations
- Private service providers operating in the public interest

Existing feedback mechanisms (phone calls, paper forms, social media) are untrackable, easily ignored, and produce no audit trail.

### What Gunaso Does

1. **Organizations register** on the platform and define their internal departments, categories of complaints, and routing rules.
2. **Citizens submit** complaints, feedback, or suggestions — attaching evidence (photos, documents).
3. **The platform routes** each submission to the correct stakeholder (department head, assigned officer, ward office, etc.) based on category and routing rules.
4. **Stakeholders respond** and update the status as work progresses.
5. **Citizens track** their submission in real time, receiving notifications at every status change.
6. **Unresolved submissions escalate** automatically after a configurable period.

### Design Principles

- **Citizen-first UX** — submitting a complaint must take under 2 minutes with zero account required (anonymous submissions allowed).
- **Organization accountability** — every submission has a paper trail; organizations cannot silently delete or ignore.
- **Transparency by default** — resolution status is public unless marked sensitive.
- **Extensible routing** — organizations configure their own routing logic without developer involvement.

---

## 2. Tech Stack & Rationale

### Backend: Django 5 + Django REST Framework

**Why Django?**
Django's "batteries included" philosophy makes it ideal for a data-heavy platform with complex relational models. The ORM handles the intricate relationships between organizations, departments, routing rules, and submissions cleanly. Django Admin provides a powerful back-office for platform management with zero custom code.

**Why DRF?**
DRF is the standard for Django APIs. Serializer-based validation, viewset patterns, permission classes, and browsable API accelerate development without sacrificing control. Its integration with `drf-spectacular` gives us auto-generated OpenAPI docs.

**Django apps structure (inside `backend/apps/`):**
- `accounts` — Custom User model, JWT auth views, profile management
- `organizations` — Organization, Department, Member models and CRUD
- `submissions` — Submission, Category, Attachment models; core business logic
- `routing` — RoutingRule, StakeholderAssignment; the routing engine
- `notifications` — Channels consumers, email tasks, in-app notification model
- `analytics` — Read-only aggregate endpoints for dashboards

### Database: PostgreSQL 16

**Why Postgres?**
- JSONB support for flexible metadata on submissions without schema migrations
- Full-text search for searching submission content
- Row-level security (future) for multi-tenant data isolation
- Reliable, battle-tested, excellent Django ORM support
- `pg_trgm` extension for similarity search on organization/category names

### Cache & Message Broker: Redis 7

Redis plays two roles:
1. **Cache** — Django cache backend for session data, rate limiting, and frequently-read lookups (categories, organization metadata)
2. **Celery broker** — the message queue for async tasks (email dispatch, notification fan-out, auto-escalation)

Using separate Redis databases (db 0 for cache, db 1 for Celery broker, db 2 for Celery results) keeps concerns isolated.

### Async Tasks: Celery + Celery Beat

**Why Celery?**
Sending emails, pushing WebSocket notifications to many subscribers, and running auto-escalation checks are not synchronous operations. Celery workers handle these off the request/response cycle so API responses stay fast (<200ms for all writes).

**Celery Beat** runs scheduled tasks:
- Auto-escalation check (every 6 hours): find submissions past their SLA and escalate
- Daily digest emails for stakeholders
- Periodic cleanup of expired anonymous session tokens

### WebSockets: Django Channels

Citizens and organization staff see real-time status updates without polling. Django Channels extends Django's request/response cycle to handle long-lived WebSocket connections. Each submission has its own channel group (`submission_{uuid}`) — stakeholders and the submitter are added to the group when they open the submission detail page.

**Channel layer backend:** Redis (via `channels_redis`).

### Frontend: Vue 3 + Vite + Pinia + Vue Router

**Why Vue 3?**
Vue 3's Composition API provides clean, testable logic in composables. The Options API is explicitly forbidden in this project — all components use `<script setup>` syntax.

**Why Vite?**
Sub-second HMR for a fast developer experience. Native ESM, tree-shaking, and rollup bundling for optimized production builds.

**Why Pinia?**
Pinia is the official Vue store. Simpler than Vuex, fully TypeScript-compatible, and devtools-friendly. Stores are organized per-domain (auth, submissions, organizations, notifications).

**Why Tailwind CSS?**
Utility-first CSS eliminates style naming overhead. Design tokens (colors, spacing, typography) are configured in `tailwind.config.js` to match the Gunaso brand. Component-level styles that can't be expressed as utilities go in `<style scoped>` blocks.

### Containerization: Docker + Docker Compose

Every developer runs the same stack. Docker Compose orchestrates all services with a single command. Production deployments use the same images, eliminating "works on my machine" issues.

### Reverse Proxy: Nginx

Nginx sits in front of all services:
- Routes `/api/` and `/admin/` to the Django backend
- Routes `/ws/` WebSocket connections to Django Channels (with `Upgrade` header)
- Routes `/` to the Vue/Vite dev server (or to the built static files in production)
- Serves `/static/` and `/media/` directly from named Docker volumes in production

---

## 3. Project Structure

```
gunaso/
├── backend/
│   ├── config/                    # Django project package
│   │   ├── settings/
│   │   │   ├── base.py            # Shared settings
│   │   │   ├── development.py     # DEBUG=True, console email, relaxed CORS
│   │   │   └── production.py      # S3 media, HTTPS, strict CORS
│   │   ├── urls.py                # Root URL config
│   │   ├── asgi.py                # ASGI entry point (Channels + HTTP)
│   │   ├── wsgi.py                # WSGI fallback
│   │   └── celery.py              # Celery app definition
│   ├── apps/
│   │   ├── accounts/
│   │   │   ├── models.py          # User (extends AbstractUser)
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── urls.py
│   │   │   └── tests/
│   │   ├── organizations/
│   │   │   ├── models.py          # Organization, Department, OrganizationMember
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── urls.py
│   │   │   ├── admin.py
│   │   │   └── tests/
│   │   ├── submissions/
│   │   │   ├── models.py          # Submission, Category, Attachment, StatusHistory
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── urls.py
│   │   │   ├── tasks.py           # Celery tasks for this domain
│   │   │   ├── admin.py
│   │   │   └── tests/
│   │   ├── routing/
│   │   │   ├── models.py          # RoutingRule, StakeholderAssignment
│   │   │   ├── engine.py          # Pure routing logic — given a submission, return stakeholders
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   └── tests/
│   │   ├── notifications/
│   │   │   ├── consumers.py       # Django Channels WebSocket consumers
│   │   │   ├── routing.py         # Channels URL routing
│   │   │   ├── models.py          # Notification (in-app)
│   │   │   ├── tasks.py           # Email dispatch, push notification tasks
│   │   │   └── tests/
│   │   └── analytics/
│   │       ├── views.py           # Read-only aggregates
│   │       ├── serializers.py
│   │       └── urls.py
│   ├── requirements.txt
│   ├── requirements-dev.txt       # pytest, factory-boy, etc.
│   ├── manage.py
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/                   # Axios instance + per-domain modules
│   │   │   ├── client.ts          # Base axios config, interceptors
│   │   │   ├── submissions.ts
│   │   │   ├── organizations.ts
│   │   │   └── auth.ts
│   │   ├── stores/                # Pinia stores
│   │   │   ├── auth.ts
│   │   │   ├── submissions.ts
│   │   │   ├── organizations.ts
│   │   │   └── notifications.ts
│   │   ├── router/
│   │   │   └── index.ts           # Vue Router config + navigation guards
│   │   ├── composables/           # Reusable Composition API logic
│   │   │   ├── useSubmission.ts
│   │   │   ├── useWebSocket.ts
│   │   │   └── useToast.ts
│   │   ├── views/                 # Route-level page components
│   │   │   ├── HomeView.vue
│   │   │   ├── SubmitView.vue
│   │   │   ├── SubmissionDetailView.vue
│   │   │   ├── OrganizationView.vue
│   │   │   └── dashboard/
│   │   │       ├── DashboardView.vue
│   │   │       └── SubmissionsListView.vue
│   │   ├── components/            # Reusable UI components
│   │   │   ├── ui/                # Atomic: Button, Input, Badge, Modal
│   │   │   ├── submission/        # SubmissionCard, StatusBadge, FileUpload
│   │   │   └── layout/            # AppHeader, AppSidebar, AppFooter
│   │   ├── types/                 # TypeScript interfaces matching API shapes
│   │   ├── utils/                 # Pure helper functions (no side effects)
│   │   ├── App.vue
│   │   └── main.ts
│   ├── public/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── package.json
│   └── Dockerfile
├── nginx/
│   └── nginx.conf
├── docker-compose.yml
├── .env.example
├── .gitignore
├── CLAUDE.md
└── README.md
```

---

## 4. Domain Model & Key Concepts

### Organization

An `Organization` is any entity that registers on the platform to receive and manage submissions.

**Fields:**
- `id` (UUID)
- `name` — official organization name
- `slug` — URL-friendly identifier (`ward-office-kathmandu-5`)
- `type` — enum: `government`, `ngo`, `private`, `utility`, `education`, `healthcare`, `other`
- `description`
- `logo`
- `verified` — boolean, platform-verified official organizations get a badge
- `is_active`
- `contact_email`, `contact_phone`, `website`
- `address`, `latitude`, `longitude`
- `created_at`, `updated_at`

**Related:**
- `departments` → Department (one-to-many)
- `members` → OrganizationMember (through table with roles)
- `categories` → Category (one-to-many, org-defined)
- `routing_rules` → RoutingRule (one-to-many)

---

### Department

A subdivision within an Organization. Submissions can be routed to a specific Department rather than the top-level organization.

**Fields:**
- `id` (UUID)
- `organization` (FK)
- `name`
- `head_user` (FK → User, nullable)
- `email` — department contact email for notifications
- `is_active`

---

### Category

Categories are the taxonomy by which submissions are classified. Each organization defines their own categories.

**Fields:**
- `id` (UUID)
- `organization` (FK)
- `name` (e.g., "Road Damage", "Water Supply", "Corruption")
- `description`
- `icon` — emoji or icon identifier
- `is_active`
- `parent` (FK → self, nullable) — supports subcategories

**Platform-level categories** (available to all organizations) are owned by `organization=None`.

---

### Submission

The core entity — a citizen's complaint, feedback, or suggestion directed at an organization.

**Fields:**
- `id` (UUID, exposed publicly as tracking ID)
- `tracking_code` — human-readable short code (e.g., `GUN-2024-00042`)
- `organization` (FK)
- `category` (FK)
- `title`
- `description` (rich text)
- `status` — see Status Workflow below
- `priority` — enum: `low`, `medium`, `high`, `urgent` (set by organization staff)
- `is_anonymous` — if True, submitter identity is hidden from organization
- `submitter` (FK → User, nullable — None for anonymous)
- `submitter_name`, `submitter_email`, `submitter_phone` — collected for anonymous submissions
- `location_text` — free-text location description
- `latitude`, `longitude` — optional coordinates
- `metadata` (JSONB) — flexible extra data, org-specific
- `is_public` — whether the submission appears in public feed
- `created_at`, `updated_at`, `resolved_at`, `escalated_at`

**Related:**
- `attachments` → Attachment (one-to-many)
- `status_history` → StatusHistory (one-to-many, append-only audit log)
- `assignments` → StakeholderAssignment (one-to-many)
- `comments` → Comment (one-to-many, stakeholder ↔ citizen thread)

---

### Attachment

File evidence attached to a Submission.

**Fields:**
- `id` (UUID)
- `submission` (FK)
- `file` — uploaded to `media/submissions/{submission_id}/`
- `file_type` — enum: `image`, `document`, `audio`, `video`, `other`
- `original_name`
- `size_bytes`
- `uploaded_by` (FK → User, nullable)
- `uploaded_at`

**Constraints:**
- Max `MAX_ATTACHMENT_SIZE_MB` per file (default 10MB)
- Max `MAX_ATTACHMENTS_PER_SUBMISSION` per submission (default 5)

---

### RoutingRule

Defines how a submission should be automatically routed to a stakeholder when it matches certain conditions.

**Fields:**
- `id` (UUID)
- `organization` (FK)
- `name` — human-readable rule name ("Road complaints → Infrastructure Dept")
- `priority` — integer, lower = evaluated first
- `is_active`
- **Conditions** (all must match for rule to trigger):
  - `category` (FK, nullable) — match by category
  - `category_name_contains` (text, nullable) — fuzzy match on category name
  - `keywords` (JSONB array) — if submission title/description contains any of these words
- **Action:**
  - `route_to_department` (FK → Department, nullable)
  - `route_to_user` (FK → User, nullable)
  - `assign_priority` — override submission priority if matched

**Routing Engine (`routing/engine.py`):**
The routing engine is a pure function:
```python
def resolve_stakeholders(submission: Submission) -> list[StakeholderAssignment]:
    """
    Evaluates all active RoutingRules for the submission's organization
    in priority order. Returns a list of assignments for the first matching rule.
    Falls back to organization's default department head if no rule matches.
    """
```

---

### StakeholderAssignment

Records that a specific User or Department has been assigned to handle a Submission.

**Fields:**
- `id` (UUID)
- `submission` (FK)
- `assigned_to_user` (FK → User, nullable)
- `assigned_to_department` (FK → Department, nullable)
- `assigned_by` (FK → User, nullable — None for auto-routing)
- `assigned_at`
- `is_primary` — the primary assignee responsible for resolution

---

### StatusHistory

Immutable append-only log of every status change on a Submission.

**Fields:**
- `id` (UUID)
- `submission` (FK)
- `from_status` (nullable — None for initial creation)
- `to_status`
- `changed_by` (FK → User, nullable)
- `comment` — optional note explaining the status change (visible to citizen)
- `is_internal` — if True, comment is only visible to organization staff
- `changed_at`

**Rule: StatusHistory records are NEVER deleted or updated.** They are the audit trail.

---

### User Roles

Within an Organization, members have roles:

| Role | Permissions |
|------|------------|
| `owner` | Full admin; can delete org, manage all members and settings |
| `admin` | Manage members, categories, routing rules, all submissions |
| `staff` | View and update submissions assigned to them or their department |
| `viewer` | Read-only access to the organization's dashboard |

Platform-level roles:
- `citizen` — the default role; can submit and track own submissions
- `platform_admin` — Gunaso staff with platform-wide access

---

## 5. Status Workflow

Every Submission moves through a defined lifecycle:

```
                     ┌─────────────┐
                     │  submitted  │  ← Initial state on creation
                     └──────┬──────┘
                            │ Organization acknowledges receipt
                            ▼
                     ┌─────────────┐
                     │acknowledged │
                     └──────┬──────┘
                            │ Investigation/work begins
                            ▼
                     ┌─────────────┐
                     │  in_review  │
                     └──────┬──────┘
                            │
               ┌────────────┼────────────────┐
               ▼            ▼                ▼
        ┌──────────┐  ┌──────────┐   ┌────────────┐
        │ resolved │  │ rejected │   │  escalated │
        └──────────┘  └──────────┘   └────────────┘
                                            │
                                            │ Can be resolved after escalation
                                            ▼
                                      ┌──────────┐
                                      │ resolved │
                                      └──────────┘
```

### Status Definitions

| Status | Who can set it | Meaning |
|--------|---------------|---------|
| `submitted` | System (auto) | Submission created; pending review |
| `acknowledged` | Org staff | Org has received and noted the submission |
| `in_review` | Org staff | Active investigation or work in progress |
| `resolved` | Org staff | Issue addressed; resolution note required |
| `rejected` | Org staff | Submission out of scope or invalid; reason required |
| `escalated` | System (auto) or Org admin | SLA breached or citizen escalation requested |

### SLA & Auto-escalation

- Each Organization can define an SLA (default: 7 days from `submitted` to `resolved`).
- Celery Beat runs an escalation check every 6 hours.
- A submission in `submitted` or `acknowledged` status past its SLA is automatically transitioned to `escalated`, and a `StatusHistory` entry is created with `changed_by=None` (system action).
- Organization admins receive an email digest of escalated submissions each morning.

### Valid Transitions

Only valid transitions are permitted. The backend enforces this in the `Submission.transition_status()` method:

```python
VALID_TRANSITIONS = {
    "submitted":     {"acknowledged", "escalated"},
    "acknowledged":  {"in_review", "escalated"},
    "in_review":     {"resolved", "rejected", "escalated"},
    "escalated":     {"resolved", "in_review"},
    "resolved":      set(),   # terminal
    "rejected":      set(),   # terminal
}
```

Any attempt to make an invalid transition raises `InvalidStatusTransitionError`.

---

## 6. API Design Philosophy

### Versioning

All endpoints are prefixed with `/api/v1/`. When breaking changes are needed, `/api/v2/` is introduced alongside v1 (never remove v1 without a migration period).

### URL Naming

Follow RESTful resource naming:
- Collections: `GET /api/v1/submissions/`
- Single resource: `GET /api/v1/submissions/{uuid}/`
- Sub-resources: `GET /api/v1/submissions/{uuid}/comments/`
- Actions (non-CRUD): `POST /api/v1/submissions/{uuid}/status/` (status transition)

Do not use verbs in URLs except for actions (`/resend-notification/`, `/verify/`).

### HTTP Methods

| Method | Use |
|--------|-----|
| `GET` | Read; always idempotent |
| `POST` | Create new resource |
| `PUT` | Full replace (rarely used) |
| `PATCH` | Partial update |
| `DELETE` | Delete (organization data only; submissions are soft-deleted) |

### Response Shape

All responses follow a consistent envelope:

```json
{
  "data": { ... },
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 143
  }
}
```

Error responses:
```json
{
  "error": {
    "code": "INVALID_STATUS_TRANSITION",
    "message": "Cannot transition from 'resolved' to 'in_review'.",
    "field_errors": {}
  }
}
```

### Pagination

All list endpoints paginate with `?page=N&page_size=20` (max 100). Use `django.core.paginator` via DRF's `PageNumberPagination`.

### Filtering

List endpoints support filtering via query parameters:
- `GET /api/v1/submissions/?status=in_review&category=road-damage&organization=ward-5`
- `GET /api/v1/submissions/?created_after=2024-01-01&ordering=-created_at`

Implemented via `django-filter`.

### Permissions

Every view declares explicit permission classes. The hierarchy:

| Permission Class | Used for |
|-----------------|---------|
| `IsAuthenticated` | Must be logged in |
| `IsAnonymousOrAuthenticated` | Submission creation (allows anonymous) |
| `IsOrganizationMember` | Must be a member of the org |
| `IsOrganizationAdmin` | Must be admin/owner of the org |
| `IsSubmissionOwner` | Can only see own submissions (citizen) |
| `IsAssignedStakeholder` | Must be assigned to the submission |

### OpenAPI Docs

`drf-spectacular` generates the OpenAPI 3 schema.

- Schema JSON: `GET /api/v1/schema/`
- Swagger UI: `GET /api/v1/schema/swagger-ui/`
- ReDoc: `GET /api/v1/schema/redoc/`

All serializers and views must have docstrings consumed by drf-spectacular for accurate docs.

---

## 7. Frontend Architecture

### Component Hierarchy

```
App.vue
├── <RouterView>
│   ├── HomeView.vue           — Public landing page, search/browse orgs
│   ├── SubmitView.vue         — Multi-step submission form (wizard)
│   ├── SubmissionDetailView.vue — Citizen tracking view with live updates
│   ├── OrganizationView.vue   — Public org profile + submission form
│   └── dashboard/
│       ├── DashboardView.vue  — Staff home: KPIs, recent activity
│       └── SubmissionsListView.vue — Filterable/sortable submissions table
└── <Teleport> — Toast notifications
```

### Component Rules

1. **`<script setup>` only** — never use Options API.
2. **No business logic in templates** — computed properties and composables only.
3. **Props are typed** — use TypeScript `defineProps<T>()` syntax.
4. **Emit are typed** — use `defineEmits<{ (e: 'update:modelValue', v: string): void }>()`.
5. **Max 150 lines per SFC** — extract logic to composables if exceeding this.
6. **No direct API calls from components** — all API calls go through Pinia stores or composables.

### Pinia Store Structure

Each store follows this pattern:

```typescript
// stores/submissions.ts
export const useSubmissionsStore = defineStore('submissions', () => {
  // State
  const items = ref<Submission[]>([])
  const current = ref<Submission | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters (computed)
  const byStatus = computed(() =>
    (status: Status) => items.value.filter(s => s.status === status)
  )

  // Actions
  async function fetchSubmissions(filters: SubmissionFilters) { ... }
  async function createSubmission(payload: CreateSubmissionPayload) { ... }
  async function updateStatus(id: string, status: Status, comment: string) { ... }

  return { items, current, loading, error, byStatus, fetchSubmissions, createSubmission, updateStatus }
})
```

### API Client

The base Axios client lives in `src/api/client.ts`:
- Base URL from `import.meta.env.VITE_API_BASE_URL`
- Request interceptor adds `Authorization: Bearer <token>` from auth store
- Response interceptor handles 401 → automatic token refresh → retry
- Response interceptor unwraps the `data` envelope from all responses

Domain modules (`auth.ts`, `submissions.ts`, etc.) export typed functions that call the client.

### Vue Router Guards

```typescript
router.beforeEach((to, from) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresOrgRole && !auth.hasOrgRole(to.params.orgSlug)) {
    return { name: 'forbidden' }
  }
})
```

### WebSocket in Frontend

`src/composables/useWebSocket.ts` manages the WS connection:
- Connects to `VITE_WS_BASE_URL/ws/submissions/{id}/` when a submission detail is open
- Receives `status_change` events and updates the Pinia store in place
- Auto-reconnects with exponential backoff on disconnect
- Cleans up on component unmount

---

## 8. Real-time Architecture (WebSockets)

### Django Channels Setup

`config/asgi.py` routes WebSocket connections to Channels consumers:

```python
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(notifications.routing.websocket_urlpatterns)
    ),
})
```

### Consumer: SubmissionConsumer

Each submission has a channel group named `submission_{submission_uuid}`.

- **On connect:** verify JWT from query param (`?token=...`), check permission to view submission, add to group
- **On status change (server → clients):** `notifications/tasks.py` calls `channel_layer.group_send()` — this fan-outs to all connected clients
- **On disconnect:** remove from group

### Message Types

```python
# Status change notification
{
    "type": "status_change",
    "submission_id": "uuid",
    "from_status": "submitted",
    "to_status": "acknowledged",
    "changed_by": "user display name",
    "comment": "We have received your complaint.",
    "changed_at": "2024-03-15T10:30:00Z"
}

# Comment added
{
    "type": "new_comment",
    "submission_id": "uuid",
    "author": "Staff Name",
    "content": "...",
    "is_internal": false,
    "created_at": "..."
}
```

---

## 9. Async Task Architecture (Celery)

### Task File Location

Each Django app that needs async tasks has a `tasks.py`:
- `submissions/tasks.py` — post-creation routing, attachment processing
- `notifications/tasks.py` — email dispatch, WebSocket fan-out
- `routing/tasks.py` — auto-escalation check

### Key Tasks

```python
# On submission creation (triggered by post_save signal or serializer .save())
@shared_task
def route_submission(submission_id: str):
    """Run routing engine and create StakeholderAssignments."""

@shared_task
def notify_stakeholders(submission_id: str):
    """Email assigned stakeholders that a new submission needs attention."""

@shared_task
def send_submission_confirmation(submission_id: str):
    """Email/SMS the citizen their tracking code."""

@shared_task
def check_and_escalate_submissions():
    """Periodic: find overdue submissions and transition to 'escalated'."""

@shared_task
def send_stakeholder_digest():
    """Periodic: daily email digest of open submissions to each stakeholder."""
```

### Task Naming

All tasks are named explicitly: `@shared_task(name="submissions.route_submission")`. This avoids import path changes breaking existing queued tasks.

### Error Handling

Tasks that call external services (email, SMS) use `autoretry_for=(Exception,)` with `max_retries=3` and exponential backoff. Failed tasks are visible in Django Celery Results.

---

## 10. Authentication & Authorization

### JWT Setup (djangorestframework-simplejwt)

- **Access token** — 60 minutes (configurable via `JWT_ACCESS_TOKEN_LIFETIME_MINUTES`)
- **Refresh token** — 7 days (configurable via `JWT_REFRESH_TOKEN_LIFETIME_DAYS`)
- Access token is stored in memory on the frontend (not localStorage) to mitigate XSS
- Refresh token is stored in an `httpOnly`, `Secure`, `SameSite=Strict` cookie

### Anonymous Submissions

Citizens can submit without an account. The submission form collects `submitter_name`, `submitter_email`, and `submitter_phone` optionally. An anonymous session token is returned so the citizen can track their submission without an account (stored in `sessionStorage`).

### Permission Checks

Permission checks happen at two layers:
1. **DRF permission classes** — coarse-grained per view
2. **Object-level permissions** — `has_object_permission()` for fine-grained checks

Never skip object-level permissions for multi-tenant data. Always check that the requesting user belongs to the organization that owns the resource.

---

## 11. Dev Environment Setup

### Requirements

- Docker Desktop ≥ 4.x
- Git
- (Optional for local dev without Docker) Python 3.12+, Node.js 20+, PostgreSQL 16, Redis 7

### First-time Setup

```bash
# Clone
git clone https://github.com/your-org/gunaso.git
cd gunaso

# Configure environment
cp .env.example .env
# Edit .env — set SECRET_KEY, POSTGRES_PASSWORD, JWT_SIGNING_KEY

# Build and start all services
docker compose up --build

# Create platform superuser (first time only)
docker compose exec backend python manage.py createsuperuser

# (Optional) Load sample data fixtures
docker compose exec backend python manage.py loaddata fixtures/sample_data.json
```

### Local Backend (without Docker)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt

# Point to local postgres/redis in .env (change DATABASE_URL host from 'postgres' to 'localhost')
export DJANGO_SETTINGS_MODULE=config.settings.development

python manage.py migrate
python manage.py runserver

# In separate terminals:
celery -A config worker --loglevel=info
celery -A config beat --loglevel=info
```

### Local Frontend (without Docker)

```bash
cd frontend
npm install
# Set VITE_API_BASE_URL=http://localhost:8000/api/v1 in .env
npm run dev
```

---

## 12. Docker Compose Usage

```bash
# Start all services (foreground)
docker compose up

# Start in background
docker compose up -d

# Rebuild images after dependency changes
docker compose up --build

# View logs for a specific service
docker compose logs -f backend
docker compose logs -f celery_worker

# Open a shell in a running container
docker compose exec backend bash
docker compose exec frontend sh

# Run Django management commands
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py shell
docker compose exec backend python manage.py createsuperuser

# Run backend tests
docker compose exec backend pytest

# Run frontend tests
docker compose exec frontend npm run test

# Stop all services
docker compose down

# Stop and remove volumes (DESTRUCTIVE — wipes database)
docker compose down -v

# Scale workers (run more Celery workers)
docker compose up --scale celery_worker=3
```

### Services and Ports

| Service | Internal Port | Exposed Port | Purpose |
|---------|--------------|--------------|---------|
| `postgres` | 5432 | 5432 | PostgreSQL database |
| `redis` | 6379 | 6379 | Cache and Celery broker |
| `backend` | 8000 | 8000 | Django ASGI server (direct access) |
| `frontend` | 5173 | 5173 | Vite dev server (direct access) |
| `nginx` | 80 | 80 | Reverse proxy (primary access point) |
| `celery_worker` | — | — | No external port |
| `celery_beat` | — | — | No external port |

**In development, access everything through `http://localhost` (port 80 via Nginx).**

---

## 13. Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DEBUG` | Yes | `True` | Django debug mode |
| `SECRET_KEY` | Yes | — | Django secret key (50+ random chars) |
| `ALLOWED_HOSTS` | Yes | `localhost,127.0.0.1` | Comma-separated allowed hosts |
| `POSTGRES_DB` | Yes | `gunaso_db` | Database name |
| `POSTGRES_USER` | Yes | `gunaso_user` | Database user |
| `POSTGRES_PASSWORD` | Yes | — | Database password |
| `DATABASE_URL` | Yes | — | Full DSN (must match above) |
| `REDIS_URL` | Yes | `redis://redis:6379/0` | Redis for cache/channels |
| `CELERY_BROKER_URL` | Yes | `redis://redis:6379/1` | Celery task broker |
| `CELERY_RESULT_BACKEND` | Yes | `redis://redis:6379/2` | Celery result storage |
| `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` | No | `60` | Access token expiry |
| `JWT_REFRESH_TOKEN_LIFETIME_DAYS` | No | `7` | Refresh token expiry |
| `JWT_SIGNING_KEY` | Yes | — | JWT HMAC signing key |
| `EMAIL_BACKEND` | No | `console` | Django email backend class |
| `EMAIL_HOST` | No | `smtp.gmail.com` | SMTP host |
| `EMAIL_PORT` | No | `587` | SMTP port |
| `EMAIL_USE_TLS` | No | `True` | SMTP TLS |
| `EMAIL_HOST_USER` | No | — | SMTP username |
| `EMAIL_HOST_PASSWORD` | No | — | SMTP password |
| `DEFAULT_FROM_EMAIL` | No | `noreply@gunaso.gov.np` | Sender address |
| `VITE_API_BASE_URL` | Yes | `http://localhost/api/v1` | API base URL for frontend |
| `VITE_WS_BASE_URL` | Yes | `ws://localhost/ws` | WebSocket base URL |
| `USE_S3` | No | `False` | Enable S3 file storage |
| `AWS_ACCESS_KEY_ID` | If USE_S3 | — | AWS credentials |
| `AWS_SECRET_ACCESS_KEY` | If USE_S3 | — | AWS credentials |
| `AWS_STORAGE_BUCKET_NAME` | If USE_S3 | — | S3 bucket name |
| `AWS_S3_REGION_NAME` | If USE_S3 | `ap-south-1` | S3 region |
| `CORS_ALLOWED_ORIGINS` | No | `http://localhost:5173` | CORS whitelist |
| `MAX_ATTACHMENT_SIZE_MB` | No | `10` | Max file size per attachment |
| `MAX_ATTACHMENTS_PER_SUBMISSION` | No | `5` | Max files per submission |
| `AUTO_ESCALATION_DAYS` | No | `7` | Days before auto-escalation |

---

## 14. Coding Conventions

### Python / Django

**General:**
- Python 3.12+. Use type hints everywhere.
- Max function length: 40 lines. Extract helpers ruthlessly.
- Max module length: 300 lines. Split by responsibility.
- Use `dataclasses` or `pydantic` for internal data structures, not dicts.
- Pure functions in `engine.py` and `utils.py` — no side effects, no DB calls, fully testable.

**Models:**
- Always define `__str__`, `Meta.ordering`, and `Meta.verbose_name_plural`.
- Use `UUIDField(primary_key=True, default=uuid.uuid4, editable=False)` on all models.
- Use `auto_now_add=True` for `created_at`, `auto_now=True` for `updated_at`.
- Never put business logic in `save()`. Use service functions or signals explicitly.
- Soft-delete pattern: `is_deleted` + `deleted_at` fields on Submission (never hard-delete citizen data).

**Serializers:**
- Validate all fields explicitly. Never trust client input.
- Use `SerializerMethodField` for computed read-only fields.
- Write-only serializers (create/update) separate from read serializers when shape differs significantly.

**Views:**
- Use `ModelViewSet` for standard CRUD; use `APIView` for complex custom logic.
- Declare `permission_classes`, `authentication_classes`, and `throttle_classes` on every view.
- No business logic in views — delegate to service functions.

**Naming:**
- Models: `PascalCase` singular (`Submission`, not `submissions`)
- URL names: `kebab-case` (`submission-detail`, not `submissionDetail`)
- Celery tasks: `snake_case` verbs (`route_submission`, `send_confirmation`)
- Constants: `UPPER_SNAKE_CASE` in `constants.py`

**Imports order** (enforced by `isort`):
1. Standard library
2. Third-party packages
3. Django
4. DRF
5. Local apps (absolute: `from apps.submissions.models import Submission`)

**Linting:** `ruff` for linting and formatting (replaces flake8 + black). Config in `pyproject.toml`.

---

### TypeScript / Vue

**TypeScript:**
- Strict mode enabled (`"strict": true` in `tsconfig.json`).
- No `any`. Use `unknown` + type guards when necessary.
- Export types from `src/types/` — one file per domain (`submission.ts`, `organization.ts`).
- API response types mirror Django serializer output exactly.

**Vue SFC:**
- `<script setup lang="ts">` always — never Options API.
- `<template>` comes last in the SFC (order: `<script>`, `<style>`, `<template>`).
- Component names: `PascalCase` in `<script>`, `kebab-case` in templates.
- Prop names: `camelCase` in `<script>`, `kebab-case` in templates.
- No inline styles — use Tailwind utilities only; `<style scoped>` for unavoidable exceptions.

**Naming:**
- Composables: `useXxx.ts` — return an object of refs and functions
- Stores: `useXxxStore` — `defineStore('xxx', () => { ... })`
- API modules: noun (e.g. `submissions.ts`) — export typed async functions
- Views: `XxxView.vue` (always in `views/`)
- Layout components: `AppXxx.vue`
- UI atoms: `BaseXxx.vue` (e.g. `BaseButton.vue`, `BaseInput.vue`)

**ESLint:** `eslint-plugin-vue` + `@typescript-eslint/eslint-plugin`. No `console.log` in committed code.

---

### Git Conventions

**Branch naming:**
- `feature/short-description`
- `fix/short-description`
- `chore/short-description`
- `docs/short-description`

**Commit message format (Conventional Commits):**
```
<type>(<scope>): <subject>

<body — optional>
```

Types: `feat`, `fix`, `chore`, `docs`, `style`, `refactor`, `test`, `perf`

Examples:
```
feat(submissions): add auto-escalation after SLA breach
fix(routing): handle missing department head in routing engine
chore(docker): pin postgres image to 16.2-alpine
```

**PR rules:**
- All PRs must pass CI (tests + linting) before merge
- Squash merge to keep main history clean
- Delete branch after merge

---

## 15. Testing Standards

### Backend (pytest + pytest-django)

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=apps --cov-report=html

# Run tests for one app
pytest apps/submissions/
```

**File layout:**
```
apps/submissions/
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_serializers.py
    ├── test_views.py
    └── test_tasks.py
```

**Rules:**
- Use `pytest` fixtures, not `unittest.TestCase`.
- Use `factory_boy` for test data — never raw `Model.objects.create()` in tests.
- Test structure: Arrange → Act → Assert (no exceptions).
- Mock external services (email, Redis pub/sub, S3) in unit tests.
- Integration tests (in `tests/integration/`) may hit the real test database but mock external I/O.
- **Target: 90%+ coverage on `apps/` — 100% on `routing/engine.py` (pure function, must be fully tested).**

**Factory example:**
```python
class SubmissionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Submission

    organization = factory.SubFactory(OrganizationFactory)
    category = factory.SubFactory(CategoryFactory)
    title = factory.Sequence(lambda n: f"Submission {n}")
    status = "submitted"
```

### Frontend (Vitest + Vue Test Utils)

```bash
npm run test          # run all tests
npm run test:coverage # with coverage
```

**Rules:**
- Test composables and stores in isolation with mocked API.
- Test components with `mount()` + interaction (`userEvent`), not implementation details.
- Snapshot tests are forbidden — they break on trivial UI changes and provide no signal.
- Mock `fetch`/`axios` at the module level, not per-test.

---

## 16. Security Patterns

- **Never expose `SECRET_KEY`, database credentials, or JWT signing keys** in code, logs, or error responses. All secrets come from environment variables.
- **All API endpoints require explicit permission classes** — no endpoint is accidentally public.
- **Rate limiting** on auth endpoints: `AnonRateThrottle` at 5 requests/minute for `/api/v1/auth/`.
- **File upload validation:** check MIME type server-side (not just extension), scan for malware in production (ClamAV or cloud equivalent), store in non-public path.
- **SQL injection:** Django ORM only. Raw SQL (`connection.execute()`) is forbidden except in migrations.
- **XSS prevention:** DRF serializers escape output. Vue's template compiler auto-escapes. `v-html` is forbidden unless sanitized with `DOMPurify`.
- **CORS:** `CORS_ALLOWED_ORIGINS` is an explicit allowlist — never `CORS_ALLOW_ALL_ORIGINS=True` in production.
- **CSRF:** DRF uses JWT (stateless), so Django's CSRF middleware is bypassed for API views. The Django Admin still uses CSRF cookies.
- **Sensitive submissions:** submissions marked `is_anonymous=True` — the submitter's identity fields must never appear in API responses visible to organization staff, only to platform admins.
- **Audit trail:** `StatusHistory` and Django's admin `LogEntry` provide a full audit trail. Never delete audit records.

---

## 17. Adding New Features — Checklist

Before opening a PR for any new feature, verify:

**Backend:**
- [ ] Model has UUID PK, `created_at`, `updated_at`, `__str__`, `Meta`
- [ ] Migration created and reviewed
- [ ] Serializer validates all fields; write tests for invalid inputs
- [ ] View declares `permission_classes` explicitly
- [ ] URL added to app `urls.py` and registered in `config/urls.py`
- [ ] Admin registered for new model
- [ ] Celery tasks named explicitly with `name=` param
- [ ] Tests: model, serializer, view — AAA pattern, factory-boy data
- [ ] Coverage: new code ≥ 90%
- [ ] drf-spectacular docstrings updated

**Frontend:**
- [ ] Types defined in `src/types/`
- [ ] API function added to domain module in `src/api/`
- [ ] Pinia store action added if needed
- [ ] Component uses `<script setup lang="ts">` with typed props/emits
- [ ] Loading and error states handled in UI
- [ ] Component tested with Vitest + Vue Test Utils

**Both:**
- [ ] New env vars documented in `.env.example` and this CLAUDE.md (Section 13)
- [ ] No secrets hardcoded anywhere
- [ ] Conventional commit message used
- [ ] PR description explains what and why (not just what)
