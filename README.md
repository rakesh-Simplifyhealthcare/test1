# queue

A FastAPI service

A lightweight, standard-layout FastAPI project: JWT auth, async SQLAlchemy 2.0, Alembic
migrations, pytest, ruff, mypy, and Docker. No framework-specific magic beyond FastAPI itself,
so it's easy to read top to bottom and extend.

## Project layout

```
app/
├── main.py              app factory, middleware, router wiring
├── core/                config, security (JWT/hashing), logging, exception handlers
├── api/
│   ├── deps.py          shared dependencies (DB session, current user)
│   └── v1/
│       ├── router.py    aggregates versioned routers
│       └── endpoints/   one module per resource (health, auth, users)
├── models/               SQLAlchemy ORM models
├── schemas/               Pydantic request/response models
├── crud/                  database access, generic base + per-model subclasses
└── db/                    engine, session factory, declarative base

alembic/                  migration environment and versions
tests/                    pytest suite (httpx AsyncClient against the ASGI app)
```

This mirrors the layering most FastAPI teams converge on: **api -> crud -> models**, with
**schemas** as the boundary type and **core** holding cross-cutting concerns. See
[BEST_PRACTICES.md](BEST_PRACTICES.md) for the reasoning and the rules to keep following as the
project grows.

## Getting started

Requires Python 3.11+.

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows PowerShell
# source .venv/bin/activate       # macOS/Linux

pip install -e ".[dev]"
cp .env.example .env              # then edit SECRET_KEY at minimum
```

Generate a real secret key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Run the app (SQLite by default, zero setup):

```bash
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for interactive API docs.

## Database migrations

The app never auto-creates tables outside of tests. Use Alembic:

```bash
alembic revision --autogenerate -m "create users table"
alembic upgrade head
```

## Switching to Postgres

Set `DATABASE_URL` to a `postgresql+asyncpg://...` URL and install the extra:

```bash
pip install -e ".[postgres]"
```

`docker-compose.yml` already wires up the app against a local Postgres container:

```bash
docker compose up --build
```

## Quality checks

```bash
ruff check .
ruff format --check .
mypy app
pytest
```

Or with `make`: `make lint`, `make format`, `make typecheck`, `make test`.

Install the git hooks once so these run automatically on commit:

```bash
pre-commit install
```

## Adding a new resource

1. Add a SQLAlchemy model in `app/models/`.
2. Import it in `app/db/base.py` so Alembic autogenerate picks it up.
3. Add Pydantic schemas in `app/schemas/`.
4. Add a CRUD class in `app/crud/` (subclass `CRUDBase`).
5. Add an endpoints module in `app/api/v1/endpoints/` and register it in
   `app/api/v1/router.py`.
6. Add tests in `tests/`.
7. Generate and review a migration: `alembic revision --autogenerate -m "..."`.
