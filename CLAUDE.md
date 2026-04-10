# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Workspace Overview

This workspace has two repositories:

| Repo | Path | Purpose |
|------|------|---------|
| **Backend** | `/home/tife/Lavoo-Business-Decision-Engine` | FastAPI + PostgreSQL SaaS backend |
| **Frontend** | `/home/tife/lavoo_main_app` | Next.js 16 (React 19) frontend |

The developer primarily works on the **backend** and pulls frontend updates from a collaborator. The backend serves the frontend via a REST API.

---

## Backend – Lavoo Business Decision Engine

### What It Is

A SaaS platform providing AI-powered business analysis and decision-making. Core features:
- **Decision Engine**: xAI Grok-powered business goal analysis → bottlenecks, action plans, roadmaps
- **Opportunity Alerts & Insights**: Curated business intelligence content
- **Missions**: Gamified action tracking derived from analyses
- **Chops**: Points/gamification system earned through engagement
- **Referral & Commission System**: Affiliate earnings with Stripe/Flutterwave/PayPal payouts
- **Subscriptions**: Stripe-based billing with Flutterwave for Nigerian users
- **Admin**: Dashboard, security management, firewall, revenue analytics

### Tech Stack

- **Framework**: FastAPI 0.115 + Uvicorn
- **Database**: PostgreSQL (Neon cloud) — no SQLite fallback
- **ORM**: SQLAlchemy 2.0 + Alembic migrations
- **Auth**: JWT via `python-jose`, Argon2 password hashing
- **AI**: xAI Grok (primary), Cohere (fallback), sentence-transformers (local embeddings)
- **Payments**: Stripe, Flutterwave, PayPal
- **Email**: MailerLite API
- **Cache**: Redis (falls back to in-memory)
- **Monitoring**: Sentry, Logtail
- **Deploy**: Railway (Docker, Python 3.12)

### Commands

```bash
# Install dependencies (uses UV package manager)
pip install uv
uv pip install -r requirements.txt

# Run locally
uvicorn api.main:app --reload --port 8000

# Run database migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description"

# Run tests
pytest

# Run a single test file
pytest tests/test_billing.py -v

# Docker build
docker build -t lavoo-backend .
```

Environment: copy `.env.local` for local dev. The app auto-loads `.env.local` before `.env`.

### Directory Structure

```
api/
  main.py               # App entry, middleware, router registration, startup migrations
  routes/
    auth/               # login.py, signup.py, forgot_password.py, google_oauth.py
    user/               # stats.py, alerts.py, insights.py, earnings.py, referrals.py,
                        # missions.py, settings.py, profile.py (⚠️ NOT REGISTERED — see issues)
    decision_engine/    # analyzer.py (business analysis), tools.py
    admin/              # admin.py, dashboard.py, revenue.py, security.py, firewall_scanner.py,
                        # users.py, settings.py
    support/            # customer_service.py, reviews.py
    missions/           # missions.py (duplicate — see issues below)
    notifications.py
  security/             # firewall.py, vulnerability_scanner.py
  cache.py
  utils/
decision_engine/        # agentic_analyzer.py, vector_recommender.py, recommender_db.py
                        # multimodal/ (document/image parsing)
database/
  pg_models.py          # All 28 SQLAlchemy ORM models
  pg_connections.py     # Engine, SessionLocal, get_db
  alembic/              # Migrations
subscriptions/          # stripe.py, flutterwave.py, paypal.py, commissions.py, stripe_connect.py
emailing/               # email_service.py (MailerLite)
config/                 # logging.py
```

### Authentication Pattern

All protected routes use `Depends(get_current_user)` from `api/routes/auth/login.py`. Login returns a flat JWT payload including `id`, `name`, `email`, `role`, `subscription_status`.

### Startup Migrations

`api/main.py` runs raw `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` SQL on every startup as a fallback migration layer. Use Alembic for proper migrations, but be aware this startup code can mask migration issues.

---

## Frontend – lavoo_main_app

### Tech Stack

Next.js 16 / React 19 / TypeScript, Tailwind CSS v4, Shadcn UI, Zustand (persisted to localStorage), native `fetch` API.

### API Client

All API calls flow through `lib/api.ts`:
- Base URL: `process.env.NEXT_PUBLIC_API_URL` (default: `http://localhost:8000`)
- Auth: `Authorization: Bearer {token}` from `localStorage.access_token`
- Handles both `{ data: ... }` wrapped and direct responses via `response.data || response`

### State Management

Zustand store in `lib/store/app_state_store.ts`, persisted under key `lavoo-app-storage`. All major domains (auth, alerts, missions, earnings, community, settings) have dedicated state slices and selectors.

### Frontend Commands

```bash
cd /home/tife/lavoo_main_app
npm install
npm run dev      # Starts on port 3000
npm run build
npm run lint
```

---

## Integration: Known Issues & Gaps

These are confirmed mismatches between what the frontend calls and what the backend implements. Address these when integrating.

### 🔴 Critical — Broken Endpoints

**1. `/api/profile` not registered in `main.py`**
- `api/routes/user/profile.py` exists and is correct but is **never imported or registered** in `main.py`.
- Frontend calls `GET /api/profile` and `PUT /api/profile`.
- Fix: Add to `main.py`:
  ```python
  from api.routes.user import profile as user_profile
  app.include_router(user_profile.router)  # prefix is /api/profile internally
  ```

**2. Route ordering bug in missions router (`api/routes/user/missions.py`)**
- `GET /constraints/active` and `POST /constraints/{constraint_id}/resolve` are defined **after** `GET /{analysis_id}`.
- FastAPI matches routes in definition order, so `constraints` will be treated as an `analysis_id` integer → `422 Unprocessable Entity`.
- Fix: Move the `/constraints/*` routes **before** `/{analysis_id}` in the file.

### 🟠 Missing Backend Endpoints

**3. Settings sub-endpoints**
- Backend has `GET /api/settings` and `PUT /api/settings` (full object).
- Backend has `GET /api/settings/notifications` and `GET /api/settings/privacy` only.
- Frontend also calls:
  - `PUT /api/settings/notifications`
  - `PUT /api/settings/privacy`
  - `GET /api/settings/display` + `PUT /api/settings/display`
  - `GET /api/settings/decision-engine` + `PUT /api/settings/decision-engine`
  - `POST /api/settings/reset`
- Add the missing PUT handlers and display/decision-engine/reset sub-routes to `api/routes/user/settings.py`.

**4. Community feature — entirely missing from backend**
- Frontend has extensive community API calls under `/api/community/*`:
  - Channels: CRUD, join, leave, `my`
  - Discussions: CRUD, like, reply
  - Events: list, register, unregister, `my`
  - Leaderboard, activity, profile, saved items
- **No `/api/community/` router exists in the backend.**
- This is the largest missing feature. A new module `api/routes/community/` needs to be created.

### 🟡 Minor / Verification Needed

**5. CORS missing production frontend URL**
- `main.py` CORS `origins` list only includes `localhost` variants.
- When deploying to production, add the production frontend domain.

**6. Duplicate missions router**
- Both `api/routes/user/missions.py` and `api/routes/missions/missions.py` exist.
- Only `user/missions.py` is registered in `main.py`. Verify `api/routes/missions/missions.py` is either removed or intentionally separate.

**7. Frontend signup uses `application/x-www-form-urlencoded`**
- `api.auth.signup()` sends form-encoded data to `/api/signup`.
- Ensure the backend signup route accepts `Form(...)` fields, not a JSON body.

**8. `auth_debug.log` written to disk**
- `api/routes/auth/login.py` writes a debug log file (`auth_debug.log`) unconditionally.
- Remove or gate behind `DEBUG` env var before production.

---

## Key Architectural Decisions

- **No SQLite**: PostgreSQL (Neon) exclusively. Connection recycled at 120s to beat Neon's idle timeout.
- **Dual billing tracks**: Track A (event-driven Stripe webhooks) + Track B (scheduled batch processing). See `docs/BILLING_OPERATIONAL_MODEL.md`.
- **APP_MODE env var**: `'launch'` vs `'beta'` controls billing behavior. Understand this before touching subscription code.
- **Firewall middleware**: Added before CORS in middleware stack; FastAPI processes them in reverse addition order (CORS runs first on inbound).
- **Startup migrations**: `main.py` runs DDL on startup alongside Alembic. Don't let these drift from the actual Alembic migration history.
