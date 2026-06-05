# SmartFinance

A personal finance tracker built with Django, Django REST Framework, Bootstrap 5, and Chart.js.

This is a **runnable core**, not the full spec in the original brief. See "Scope & honest status" below for what is and isn't here, and why.

## What works right now

- Email/username registration, login, logout, password change, password reset (Django built-ins)
- Expense CRUD with search + category/date filtering and pagination
- Income CRUD with source filtering
- Monthly per-category budgets with live utilization (spent / limit / % / remaining) and progress bars
- Savings goals with progress tracking
- Bill reminders (data + dashboard widget — see caveat on automated emails below)
- Dashboard: income/expense/balance/budget-utilization cards, 6-month trend chart, category doughnut, recent transactions, upcoming bills
- Analytics page: line trend, category pie, budget-vs-actual bar
- Insights page: a **deterministic rule engine** (month-over-month category jumps, savings rate, top category). No external API, no cost, no data leaves the server.
- Reports with CSV / Excel / PDF export
- REST API (DRF) for expenses, income, budgets, goals, bills, notifications — all scoped to the authenticated user
- Django admin for all models
- Dark / light theme toggle
- Runs on SQLite out of the box; switches to PostgreSQL automatically when `DATABASE_URL` is set

## Scope & honest status

The original brief asked for a "production-ready" app spanning ~10 models, full REST APIs, 12 templates, 6 chart types, exports, scheduled email reminders, an AI advisor, Docker, and four deployment targets. That is multiple weeks of work and cannot be delivered complete and correct in one pass. Decisions made:

1. **"AI advisor" is a rule engine, not an LLM.** Every example output in the brief ("Food rose 25%", "Transport above average") is arithmetic on your own data. The rule engine in `core/services/insights.py` produces those deterministically. An **LLM layer exists as a swappable stub** (`generate_llm_insight`) behind `LLM_INSIGHTS_ENABLED`. It receives only an aggregated, anonymized summary — never raw transactions — so the privacy surface is one reviewable function. It is **not wired to any vendor**; you fill it in.

2. **No automated/scheduled emails yet.** Bill reminders and notifications require a scheduler (Celery + a broker, or a cron-driven management command). That was deliberately deferred — it roughly doubles deployment complexity. The bill *data* and dashboard widget work; recurring email delivery is the missing piece. Add a management command + cron, or Celery beat, when ready.

3. **Receipt uploads use local filesystem storage.** On ephemeral hosts (Render/Railway free tiers) uploaded files vanish on redeploy. For persistence, configure S3-compatible object storage (e.g. via `django-storages`).

4. **Money is `DecimalField`**, never float. Do not change this.

5. **RBAC** for the two roles (user/admin) is Django's built-in `is_staff`/admin plus per-user queryset scoping in the API (`OwnedModelViewSet`). No separate role framework — it would be over-engineering for two roles.

6. **One deployment path is documented (Docker + Postgres)**, not four. The Docker setup is portable to Render, Railway, DigitalOcean App Platform, or a VM. Vendor-specific configs are intentionally omitted.

## Local setup

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate          # seeds default categories
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/ — register an account, add a few transactions, then visit Insights and Reports.

## Run with Docker + PostgreSQL

```bash
docker compose up --build
# create an admin user in the running container:
docker compose exec web python manage.py createsuperuser
```

## Configuration

Copy `.env.example` to `.env`. Key variables:

- `DJANGO_SECRET_KEY` — required in production
- `DJANGO_DEBUG` — `False` in production (enables HTTPS redirect, secure cookies, HSTS)
- `DJANGO_ALLOWED_HOSTS` — comma-separated
- `DATABASE_URL` — if set, uses Postgres; otherwise SQLite
- `LLM_INSIGHTS_ENABLED` / `LLM_API_KEY` — optional LLM insight layer (stub)

## Project layout

```
smartfinance/
  smartfinance/        # settings, root urls, wsgi
  core/
    models.py          # 9 models, DecimalField money, indexed
    forms.py           # Bootstrap-styled ModelForms
    views.py           # auth, dashboard, CRUD, charts JSON, reports, exports
    api.py             # DRF viewsets (user-scoped)
    serializers.py
    admin.py
    context_processors.py   # unread notifications
    services/insights.py    # rule engine + LLM stub
    migrations/0002_seed_categories.py
  templates/           # base + 12 pages + auth
  Dockerfile, docker-compose.yml, requirements.txt
```

## REST API

Session-authenticated. Browse at `/api/` when logged in. Endpoints: `/api/expenses/`, `/api/income/`, `/api/budgets/`, `/api/goals/`, `/api/bills/`, `/api/notifications/`. Each returns only the current user's records.

## Suggested next steps (in priority order)

1. Add a `send_bill_reminders` management command + cron (or Celery beat) to make reminders real.
2. Wire object storage for receipt uploads before relying on them in production.
3. Add automated tests (the smoke test used during development covered views, API, insights, and ownership — port it into `core/tests.py`).
4. Add per-object rate limiting on auth endpoints (e.g. `django-axes`).
5. If the LLM layer is wanted, implement `generate_llm_insight` and review the privacy summary it sends.
