# CLAUDE.md — Gunaso Developer North Star

> This document is the authoritative reference for all development decisions on the Gunaso platform.
> It describes the codebase **as it actually is**. Aspirational features live in the Roadmap section
> at the bottom — do not document features that do not exist yet as if they do.
> When in doubt: this document wins over instinct.

---

## 1. Project Overview & Mission

**Gunaso** (गुनासो — Nepali for *complaint* or *grievance*) is a civic-tech platform that gives
citizens a structured, trackable channel to hold organizations accountable.

1. **Organizations register** on the platform (verified by platform admins before appearing publicly).
2. **Citizens submit** complaints, feedback, or suggestions — with optional file evidence — with or
   without an account, and optionally anonymously.
3. **Each submission gets a reference number** (`GUN-YYYY-NNNNN`) for public status tracking.
4. **Organization admins respond** and move submissions through a validated status lifecycle.
5. **Every status change is recorded** in an append-only audit log visible to the citizen.

### Design Principles

- **Citizen-first UX** — submitting takes under 2 minutes; no account required; anonymous allowed.
- **Organization accountability** — every submission has an immutable audit trail.
- **Anonymity is sacred** — anonymous submitters' identity is never exposed to organizations,
  only to platform staff.
- **Secure by default** — explicit permissions on every endpoint, strict CORS, throttling everywhere.

---

## 2. Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | Django 5.1 + Django REST Framework 3.15 |
| Database | PostgreSQL 16 (via `DATABASE_URL`; sqlite fallback for bare-metal dev only) |
| Cache / rate-limit state | Redis 7 (`django-redis`), optional in bare-metal dev |
| Auth | JWT — `djangorestframework-simplejwt` with rotating refresh tokens in httpOnly cookies |
| API schema | drf-spectacular (Swagger UI at `/api/v1/schema/swagger-ui/`) |
| Frontend | Vue 3 (Composition API, `<script setup>`) + Vite + Pinia + Vue Router |
| Styling | Tailwind CSS 3 |
| Maps | Leaflet 1.9 + OpenStreetMap tiles (public `/map`, settings location picker) |
| Containerization | Docker + Docker Compose |
| Reverse proxy | Nginx (single entry point, rate-limits auth endpoints) |
| WSGI server | gunicorn (in Docker) |

The frontend is currently **JavaScript** (not TypeScript). Follow the existing JS style;
a TS migration is on the roadmap.

---

## 3. Project Structure

```
gunaso/
├── backend/gunaso-api/            # Django project root
│   ├── gunaso/                    # Project package
│   │   ├── settings.py            # Single env-driven settings module
│   │   ├── urls.py                # Root URLs (+ /api/v1/health/, OpenAPI schema)
│   │   ├── pagination.py          # StandardPagination (page/page_size, max 100)
│   │   ├── exceptions.py          # Error envelope handler
│   │   └── wsgi.py
│   ├── apps/
│   │   ├── accounts/              # User model, register/login/refresh/logout/me
│   │   ├── organizations/         # Organization, Stakeholder + org endpoints
│   │   ├── submissions/           # Submission, Category, StatusUpdate
│   │   │   ├── services.py        # Business logic (reference gen, transitions, stats)
│   │   │   ├── validators.py      # Attachment validation (size/ext/magic bytes)
│   │   │   ├── org_urls.py        # /api/v1/org/* convenience endpoints
│   │   │   └── management/commands/seed_data.py
│   │   ├── platform_admin/        # Superadmin dashboard: PlatformAuditLog + /api/v1/admin/*
│   │   │   ├── permissions.py     # IsSuperAdmin (gates on User.is_superuser)
│   │   │   └── services.py        # verify/activate org, block/promote user, platform_overview()
│   │   └── ai_insights/           # AI classification/sujhav/reports — SubmissionInsight
│   │       ├── client.py          # Anthropic SDK boundary (is_ai_enabled, classify_submission)
│   │       ├── services.py        # classify_and_store() — auto-apply guardrail
│   │       └── management/commands/classify_submissions.py  # batch backfill
│   ├── conftest.py                # Shared pytest fixtures
│   ├── pytest.ini
│   ├── requirements.txt           # Pinned production deps
│   ├── requirements-dev.txt       # + pytest
│   ├── Dockerfile                 # python:3.12-slim, non-root, gunicorn
│   ├── docker-entrypoint.sh       # migrate + collectstatic on boot
│   └── .env.example
├── frontend/gunaso-ui/
│   ├── src/
│   │   ├── api/                   # axios client (in-memory token + cookie refresh)
│   │   ├── stores/                # Pinia: auth, organization, submission, admin, ui
│   │   ├── router/                # Routes + auth guards
│   │   ├── layouts/               # OrgLayout.vue, AdminLayout.vue
│   │   ├── views/                 # Page components (incl. Admin*Page.vue — superadmin dashboard)
│   │   └── components/            # Reusable UI components
│   ├── vite.config.js             # Dev proxy: /api and /media → localhost:8000
│   ├── Dockerfile                 # Multi-stage: node build → nginx static
│   └── nginx.conf                 # Internal SPA server (history fallback)
├── nginx/nginx.conf               # Central reverse proxy
├── docker-compose.yml             # postgres, redis, backend, frontend, nginx
├── .env.example                   # Compose stack env template
├── INSTRUCTION.md                 # Setup & run guide
└── CLAUDE.md                      # This file
```

---

## 4. Domain Model

### User (`apps/accounts`)
Extends `AbstractUser`. Login identifier is **email** (unique). `user_type`:
`citizen` (default), `org_admin`, `stakeholder` (admin-assigned only — self-service
registration may only pick citizen/org_admin). Also `phone`, `avatar`.

`is_staff`/`is_superuser` (inherited from `AbstractUser`) carry platform-wide meaning
here — see section 8's permission model for how the two are distinct.

### Organization (`apps/organizations`)
`name`, unique auto-generated `slug`, `description`, `category` (free text sector),
`logo`, `website`, `contact_email`, `contact_phone`, `address`,
`latitude`/`longitude` (nullable decimals — set both for the org to appear on the public map),
`show_rating` (default `True`; when `False` the average rating is hidden from everyone
except the org's own admin and platform staff),
`is_verified` (platform admin sets via Django admin; only verified orgs appear publicly),
`is_active`, `admin` (FK → User; creating an org upgrades the creator to `org_admin`).

### Branch (`apps/organizations`)
A physical location of an organization (a branch office, ward desk, etc.).
`organization` FK, `name` (unique per org), `code` (8-char random, non-enumerable —
same philosophy as `Submission.reference_number`; embedded in that branch's QR
target URL as `?branch=<code>`), `address`, `latitude`/`longitude` (both required
for the branch to appear on any map), `is_active`. A citizen who scans a branch's
QR code has that branch recorded on their `Submission` (see below), giving the
organization per-branch traceability and stats in the dashboard.

### OrganizationRating (`apps/organizations`)
A citizen's 1–5 star rating of an organization — score only, no review text.
One row per `(organization, user)`; re-rating upserts (see
`apps/organizations/services.py::rate_organization`). The public average
(`average_rating`, `rating_count` on the org serializer) is subject to `show_rating`.

### Category (`apps/submissions`)
Per-organization taxonomy; `organization=None` means a global category.
Unique per `(name, organization)`. Auto-created on first use by submission create.

### Submission (`apps/submissions`)
The core entity. Key fields: `reference_number` (`GUN-YYYY-NNNNN`, random, unique,
non-enumerable), `organization`, `branch` (FK, nullable — set when the citizen
scanned a branch-specific QR code; `SET_NULL` on branch deletion), `category`,
`submission_type` (`complaint|feedback|suggestion`), `title`, `description`,
`attachment` (validated), `status`, `priority` (`low|medium|high|urgent`),
`is_anonymous`, `citizen` (FK, null for guests), `citizen_name/email/phone`
(blank when anonymous), `created_at`, `updated_at`, `resolved_at`.

**API field mapping:** the API exposes `type` (↔ `submission_type`) and
`submitter_name/email/phone` (↔ `citizen_*`). `category` is written as a plain name
string and resolved/created server-side. `branch` is written as `branch_code` (the
non-enumerable code from the scanned QR URL, org-scoped and resolved server-side —
never a raw `Branch` id) and read back as `branch_name`.

**Simplified submit flow:** `title` and `category` are both optional on create —
the public submit form only requires `description` (min 20 chars) plus contact
info unless anonymous. When `title` is omitted or blank, `apps/submissions/services.py::derive_title()`
generates one from the description (first sentence/clause, or the first ~60
chars trimmed to a word boundary). An explicitly provided title is still
validated (min 5 chars) and kept verbatim.

### SubmissionInsight (`apps/ai_insights`)
AI-generated classification for one submission — a **suggestion**, not an
edit. OneToOne with `Submission` (`related_name='ai_insight'`); re-classifying
replaces the row (`update_or_create`). Fields: `suggested_category`,
`confidence` (0–1), `sentiment` (`positive|neutral|negative`),
`suggested_title`, `applied` (whether the suggestion was auto-applied to
`Submission.category`). See §9 for the auto-apply guardrail and the
never-leak-identity rule for the prompt sent to Claude.

### AISuggestion (`apps/ai_insights`)
AI-generated "sujhav" (सुझाव) — a suggested resolution/response for one
submission, bilingual (`suggestion_nepali` + `suggestion_english`, both full
independent versions, not a translation pair). OneToOne with `Submission`
(`related_name='ai_suggestion'`); regenerating replaces the row.

### AIReport (`apps/ai_insights`)
A persisted, browsable AI-generated report summarizing an organization's
submissions over a `[date_from, date_to]` range: bilingual executive summary,
`themes` (JSON list of `{name, count, summary}`), `sentiment_overview`, and
`recommendations` (JSON list of strings). Generated on demand and kept so
staff can revisit past reports without re-generating (and re-billing). Capped
at the most recent `REPORT_SUBMISSION_LIMIT` (150) submissions in the range
regardless of how large the range is (`apps/ai_insights/services.py`).

### StatusUpdate (`apps/submissions`)
**Append-only audit log** — never updated or deleted (enforced in Django admin too).
`submission`, `updated_by`, `old_status`, `new_status`, `note`, `created_at`.
Serialized to the frontend as `timeline`.

### PlatformAuditLog (`apps/platform_admin`)
**Append-only audit log** of every superadmin dashboard action (organization
verify/activate, user block/unblock/promote/demote) — same append-only contract as
`StatusUpdate` (admin change/delete permissions disabled). `actor` (FK → User,
`SET_NULL`), `action` (choices — see `apps/platform_admin/models.py`), `target_type`,
`target_id`, `target_repr` (a snapshot label so the log stays readable even if the
target is later renamed/deleted), `note`, `created_at`. Written exclusively by
`apps/platform_admin/services.py` — never construct one directly from a view.

---

## 5. Status Workflow

Statuses: `submitted → acknowledged → in_review → resolved | rejected`, plus
`escalated` (from any active state) and `closed` (terminal, after resolved/rejected).

```python
VALID_TRANSITIONS = {
    'submitted':    {'acknowledged', 'in_review', 'rejected', 'escalated'},
    'acknowledged': {'in_review', 'rejected', 'escalated'},
    'in_review':    {'resolved', 'rejected', 'escalated'},
    'escalated':    {'in_review', 'resolved', 'rejected'},
    'resolved':     {'closed'},
    'rejected':     {'closed'},
    'closed':       set(),      # terminal
}
```

- Enforced in `apps/submissions/services.py::transition_status()` — raises
  `InvalidStatusTransitionError`, surfaced to the API as **HTTP 409**.
- Every transition appends a `StatusUpdate`; `resolved` also stamps `resolved_at`.
- The frontend mirrors this map in `OrgDashboardPage.vue` to only offer legal next states.
- Keep backend and frontend transition maps in sync when changing the workflow.

---

## 6. API Design

All endpoints are under `/api/v1/`. OpenAPI docs: `/api/v1/schema/swagger-ui/`.

### Endpoints

| Method & Path | Auth | Purpose |
|---|---|---|
| `POST /auth/register/` | — (throttled) | Create account; returns `{access, user}` + refresh cookie |
| `POST /auth/login/` | — (throttled) | Email+password login; returns `{access, user}` + refresh cookie |
| `POST /auth/refresh/` | refresh cookie | Rotate refresh token, return new access token |
| `POST /auth/logout/` | refresh cookie | Blacklist refresh token, clear cookie |
| `GET/PATCH /auth/me/` | Bearer | Own profile |
| `GET /organizations/` | — | Verified orgs (paginated, `?search=`, `?category=`) |
| `POST /organizations/` | Bearer | Register org (starts unverified; creator becomes org_admin) |
| `GET /organizations/mine/` | Bearer | Org managed by current user |
| `GET /organizations/locations/` | — | Unpaginated map payload: verified orgs with coordinates (+ rating when public) |
| `GET /organizations/{slug}/` | — | Public org profile |
| `PATCH /organizations/{slug}/settings/` | org admin / `manage_org_profile` | Edit org profile fields, location, `show_rating` |
| `GET/PUT/DELETE /organizations/{slug}/rating/` | Bearer | Current user's own 1–5 rating (PUT upserts) |
| `GET /organizations/{slug}/submissions/` | org admin | Org's submissions (filterable by `?branch=`) |
| `GET /organizations/{slug}/stats/` | org admin | Aggregate stats (incl. `by_branch` and `by_category` breakdowns) |
| `GET /organizations/{slug}/branches/` | — (public: active only) / org admin sees all | List branches; `POST` requires `manage_branches` |
| `PATCH/DELETE /organizations/{slug}/branches/{id}/` | `manage_branches` | Edit/remove a branch |
| `GET /organizations/{slug}/branches/{id}/qrcode/` | — | PNG/base64 QR whose target URL carries `?branch=<code>` |
| `GET /categories/` | — | Categories (`?org=`, `?org_slug=`) |
| `POST /submissions/` | — (throttled) | Create submission (guests allowed) |
| `GET /submissions/my/` | Bearer | Own submissions |
| `GET /submissions/track/{ref}/` | — | Public tracking (contact details never included) |
| `GET /submissions/{ref}/` | owner/org admin/staff | Full detail |
| `PATCH /submissions/{ref}/status/` | org admin | Validated status transition |
| `GET/POST /submissions/{ref}/updates/` | participants / org admin | Audit trail / staff note |
| `PATCH /submissions/{ref}/category/` | `manage_submissions` | Manual categorization |
| `POST /submissions/{ref}/ai-classify/` | `manage_submissions` (throttled) | AI classification (apps.ai_insights); 503 if AI unconfigured, 502 on AI failure |
| `POST /submissions/{ref}/ai-suggestion/` | `manage_submissions` (throttled) | AI सुझाव — bilingual resolution suggestion; same 503/502 contract |
| `GET /org/submissions/`, `GET /org/stats/` | org admin | Dashboard convenience endpoints |
| `GET/POST /org/ai-reports/` | `view_stats` (throttled) | List / generate bilingual period reports (`{date_from, date_to}`) |
| `GET /org/map-feed/` | `view_submissions` | Branches with coordinates + a rolling window of recent branch-linked submission excerpts, for the animated branch map |
| `GET /admin/overview/` | superadmin | Platform-wide analytics (orgs/users/submissions totals, 30-day trend) |
| `GET /admin/organizations/` | superadmin | Every organization, verified or not (paginated, `?search=`, `?is_verified=`, `?is_active=`) |
| `PATCH /admin/organizations/{slug}/` | superadmin | Verify/unverify and/or activate/deactivate an organization |
| `GET /admin/organizations/{slug}/staff/` | superadmin | That organization's staff roster |
| `GET /admin/users/` | superadmin | Every user (paginated, `?search=`, `?user_type=`, `?is_active=`, `?is_superuser=`) |
| `POST /admin/users/{id}/block/`, `.../unblock/` | superadmin | Deactivate/reactivate an account; block also revokes its refresh tokens |
| `POST /admin/users/{id}/promote/`, `.../demote/` | superadmin | Grant/revoke superadmin (`is_staff` + `is_superuser`) |
| `GET /admin/submissions/` | superadmin | Cross-organization submission feed, incl. anonymous submitter identity |
| `GET /admin/audit-log/` | superadmin | Append-only record of every superadmin action (`PlatformAuditLog`) |
| `GET /health/` | — | DB-checking liveness probe |

### Conventions

- **Pagination**: all list endpoints — `?page=N&page_size=M` (max 100); response
  `{count, next, previous, results}`.
- **Error envelope** (from `gunaso/exceptions.py`):
  ```json
  {"error": {"code": "PERMISSION_DENIED", "message": "...", "field_errors": {}}}
  ```
- **Throttling**: anon 60/min, user 120/min, auth endpoints 10/min,
  submission creation 10/hour (configurable via env). Counters live in Redis when
  `REDIS_URL` is set — required in production (multi-worker correctness).
- Every view declares `permission_classes` explicitly. Object-level ownership checks
  are mandatory for multi-tenant data (see `IsOrgAdminOfOrg`).

---

## 7. Frontend Architecture

### Auth flow (important — do not regress this)

- **Access token lives in memory only** (`src/api/index.js`), never in localStorage.
- **Refresh token lives in an httpOnly, SameSite=Lax cookie** scoped to `/api/v1/auth/`,
  set by the backend. JS can never read it.
- On 401, the axios interceptor performs a **single-flight refresh** and retries the request;
  if refresh fails it emits `gunaso:session-expired` and the auth store clears the session.
- On app boot, `authStore.init()` silently restores the session from the cookie before
  the router mounts.
- Only the non-sensitive user profile is persisted in localStorage for instant UI.
- Requests must stay **same-origin** for the cookie to work: keep `VITE_API_BASE_URL=/api/v1`
  and go through the Vite dev proxy (dev) or Nginx (Docker/production).

### Onboarding

- After first authentication on a device, users land on `/welcome` (`OnboardingPage.vue`) —
  a 3-step, role-aware flow (welcome → how it works → first action).
- Completion is a per-device UX flag in localStorage keyed by user id
  (`stores/onboarding.js`); it is not account data and has no backend field.
- Login/Register push `onboardingStore.postAuthRoute(user)` after auth; an explicit
  `?redirect=` query on login takes precedence.

### Design system

- Typography: `font-display` = Bricolage Grotesque (headings, loaded in `index.html`),
  `font-sans` = Public Sans (body). Headings get `font-display` via base CSS.
- Motion utilities (`animate-fade-up`, `.stagger`, `.skeleton`, `ease-spring`) live in
  `tailwind.config.js` + `src/assets/main.css`; `prefers-reduced-motion` is respected globally.

### Rules

1. `<script setup>` only — never the Options API.
2. No direct API calls from components — go through Pinia stores or `src/api/` modules.
3. **No mock-data fallbacks.** Failed API calls must surface an error state, never fake data.
4. Use `apiErrorMessage(err, fallback)` from `src/api/index.js` to display server errors.
5. Status vocabulary in UI components must match the backend statuses
   (`submitted, acknowledged, in_review, resolved, rejected, escalated, closed`).

---

## 8. Authentication & Authorization

- Access token: 60 min (env `JWT_ACCESS_TOKEN_LIFETIME_MINUTES`).
- Refresh token: 7 days (env `JWT_REFRESH_TOKEN_LIFETIME_DAYS`), **rotated on every use**,
  old token blacklisted (`rest_framework_simplejwt.token_blacklist`).
- Login is by **email**; wrong-password and unknown-email return identical errors
  (no account enumeration).
- Password policy: Django validators, min length 8, common-password check.
- `SECRET_KEY` and `JWT_SIGNING_KEY` come from env; the app **refuses to boot** with
  `DEBUG=False` and no `SECRET_KEY`.

### Permission model

| Actor | Can |
|---|---|
| Guest | Browse verified orgs, submit (throttled), track by reference |
| Citizen | + own submissions list, own profile |
| Org admin | + their org's submissions/stats, status transitions on them |
| Platform staff (`is_staff`) | + Django admin, sees anonymous submitter identity |
| Platform superadmin (`is_superuser`) | + `/admin` dashboard: verify/deactivate any organization, block/unblock any user, promote/demote other superadmins, cross-org submission feed, `PlatformAuditLog` |

**Anonymity rule:** when `is_anonymous=True`, submitter identity fields are redacted in every
API response except to platform staff. The public track endpoint never includes contact fields
for anyone. This is enforced in `SubmissionSerializer.to_representation` — never bypass it.

**`is_staff` vs `is_superuser`:** these are deliberately two different gates, not synonyms.
`is_staff` is the long-standing "platform staff" bypass used throughout the app (anonymity
reveal, `IsOrgAdminOfOrg`, `HasOrgPrivilege` — see `apps/organizations/permissions.py`).
`is_superuser` is checked only by `apps/platform_admin/permissions.py::IsSuperAdmin` and gates
the `/admin` dashboard specifically. `services.promote_to_superadmin` sets **both** flags, so a
superadmin also inherits every existing `is_staff` bypass — but a plain `is_staff=True` account
(e.g. the `platform_staff` test fixture) must never reach `/admin`. Guardrails in
`apps/platform_admin/services.py`: a superadmin cannot block or demote their own account, and
the last remaining superadmin cannot be demoted.

---

## 9. Security Patterns (enforced — keep them that way)

- Secrets only from environment variables. No secrets in code, logs, or error responses.
- `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` are explicit allowlists —
  never wildcard, never `CORS_ALLOW_ALL_ORIGINS=True`.
- Production TLS settings activate when `DEBUG=False`: HSTS, secure cookies,
  `SECURE_PROXY_SSL_HEADER`, nosniff, `X-Frame-Options: DENY`.
- File uploads: size cap (`MAX_ATTACHMENT_SIZE_MB`), extension allowlist, magic-byte content
  check (`apps/submissions/validators.py`). Nginx serves `/media/` with
  `Content-Disposition: attachment` so uploads can never render/execute in-origin.
- Rate limiting at two layers: DRF throttles (app) + nginx `limit_req` on `/api/v1/auth/`.
- Reference numbers are random, not sequential — no enumeration of submissions.
- ORM only — raw SQL is forbidden outside migrations.
- `v-html` is forbidden in the frontend unless sanitized with DOMPurify.
- `StatusUpdate` and `PlatformAuditLog` records are append-only; admin change/delete
  permissions are disabled for both.
- Blocking a user (`apps/platform_admin/services.py::block_user`) sets `is_active=False`
  (rejected immediately by `JWTAuthentication`/`RefreshView` on every subsequent request,
  no need to wait out the access token's lifetime) and blacklists every outstanding refresh
  token for that user as defense in depth.
- Unhandled exceptions return an opaque 500 envelope; details go to server logs only.
- **AI prompts never carry submitter identity.** `apps/ai_insights/client.py::_build_prompt`
  sends only `submission_type`/`title`/`description` (plus the org's existing category
  names) to the Anthropic API — never `citizen_name`/`citizen_email`/`citizen_phone`,
  regardless of `is_anonymous`. This is a hard rule, not a redaction step applied
  after the fact — the payload builder simply never reads those fields. Any new
  AI feature (Phase 5's sujhav/reports) must follow the same rule.

---

## 10. Testing

```bash
cd backend/gunaso-api
.venv/Scripts/activate          # Windows (source .venv/bin/activate on Unix)
pytest                          # runs 300+ tests
```

- pytest + pytest-django; fixtures in `conftest.py`. AAA structure.
- The throttle cache is cleared between tests automatically (autouse fixture).
- **Required coverage for new code:** auth flows, permission boundaries (positive AND
  negative cases), status transitions, and anonymity redaction. A permission test that
  only checks the happy path is not done.
- Frontend tests are not yet set up (roadmap: Vitest + Vue Test Utils).

---

## 11. Environment Variables

Root `.env` (Docker stack — see `.env.example`): `DEBUG`, `SECRET_KEY`, `JWT_SIGNING_KEY`,
`ALLOWED_HOSTS`, `POSTGRES_DB/USER/PASSWORD`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`,
`SECURE_SSL_REDIRECT`, `MAX_ATTACHMENT_SIZE_MB`, `ANTHROPIC_API_KEY` (optional — AI features
run disabled without it), optional `EMAIL_*`.

Backend-only extras: `DATABASE_URL`, `REDIS_URL`, `JWT_*_LIFETIME_*`, `THROTTLE_*`,
`LOG_LEVEL`, `DB_CONN_MAX_AGE`, `STAFF_INVITE_EXPIRY_DAYS` (default 7 — how long a staff
invite link stays valid; see `apps/organizations/services.py`), `AI_CLASSIFICATION_MODEL`
(default `claude-opus-4-8`).

Frontend: `VITE_API_BASE_URL` (keep it `/api/v1`).

When adding a new env var: document it in `.env.example` **and** here.

---

## 12. Coding Conventions

**Python:** type hints on public functions; business logic in `services.py`, not views or
`save()`; serializers validate everything; views declare `permission_classes` explicitly;
models define `__str__` + `Meta.ordering`; migrations reviewed before commit.
Imports: stdlib → third-party → Django/DRF → local (`from apps.x import ...`).

**Vue/JS:** `<script setup>`; stores per domain; components in `PascalCase.vue`;
Tailwind utilities over custom CSS; no `console.log` in committed code.

**Git:** Conventional Commits (`feat(submissions): ...`), branches
`feature/...` / `fix/...` / `chore/...`.

---

## 13. Roadmap (not yet implemented — do not document as existing)

- Real-time updates via Django Channels (WebSockets)
- Async tasks via Celery (+ Beat: SLA auto-escalation, digest emails)
- Departments, routing rules engine, stakeholder assignments
- Email/SMS notifications on status changes
- TypeScript migration + Vitest suite for the frontend
- S3 media storage, ClamAV upload scanning
- Frontend anonymous-session tokens for tracking guest submissions in one place
