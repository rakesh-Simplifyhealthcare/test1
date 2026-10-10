# FastAPI Best Practices

This document explains the conventions this starter kit follows and why, so the reasoning
doesn't get lost as the project grows past its first few endpoints. Treat it as a living
document: update it when the team deliberately deviates from a rule here.

## 1. Project structure

Organize by layer, not by feature, until the project is large enough that feature folders
pay for themselves (typically once a single layer's folder has 15+ unrelated files).

- `api/` only knows about HTTP: request parsing, response shaping, status codes, and routing.
  It depends on `crud` and `schemas`, never the other way around.
- `schemas/` (Pydantic models) define what crosses the HTTP boundary. Never return a SQLAlchemy
  model directly from an endpoint; always map it to a schema with `model_config = ConfigDict(from_attributes=True)`.
- `models/` (SQLAlchemy models) define what is persisted. Keep them free of request/response
  concerns such as password fields that shouldn't round-trip to clients.
- `crud/` is the only layer allowed to touch the database session. Business logic that
  coordinates multiple models belongs in a `services/` layer if one grows naturally; don't
  create it preemptively.
- `core/` holds configuration, security primitives, logging setup, and exception handling.
  Nothing here should import from `api/`, `crud/`, or `models/`.

Keep the dependency direction one-way: `api -> crud -> models`, with `schemas` and `core` as
shared, dependency-free building blocks. A linter such as `import-linter` can enforce this once
the team is large enough to need it; for a small project, code review is enough.

## 2. Configuration and secrets

- Load all configuration through a single `pydantic-settings` `BaseSettings` class
  (`app/core/config.py`). Never read `os.environ` directly elsewhere in the codebase; it makes
  configuration impossible to audit.
- Keep `.env` out of version control. Commit `.env.example` with every variable the app needs,
  documented, with safe non-production defaults.
- Fail loudly on missing required settings (`secret_key` has no default in this kit on purpose).
  A `KeyError` or validation error at startup is far cheaper than a silent misconfiguration in
  production.
- Never log secret values. Review log statements in `core/config.py` and anywhere settings are
  passed around.
- Use `@lru_cache` (or an equivalent singleton pattern) for the settings object so environment
  variables are parsed once per process, and so tests can override it cleanly via dependency
  overrides rather than monkeypatching environment variables mid-run.

## 3. Async all the way down

FastAPI's performance advantage disappears if a request path blocks the event loop.

- Use async database drivers (`asyncpg`, `aiosqlite`) and the SQLAlchemy 2.0 async API
  consistently. Mixing sync and async database calls in the same app is a common source of
  connection pool exhaustion under load.
- Never call blocking I/O (`requests`, synchronous file I/O, `time.sleep`) inside an `async def`
  endpoint or dependency. If you must call a blocking library, run it in a thread pool with
  `anyio.to_thread.run_sync` or FastAPI's `run_in_threadpool`.
- CPU-bound work (image processing, heavy computation) does not belong in a request handler at
  all. Offload it to a background worker (Celery, arq, or a cloud task queue) and return
  immediately with a job id, or use FastAPI's `BackgroundTasks` only for short, best-effort work
  that doesn't need a retry guarantee.

## 4. Dependency injection

- Use `Depends()` for anything a route needs but doesn't own: database sessions, the current
  user, pagination parameters, feature flags. This keeps endpoint functions thin and makes
  dependencies trivially mockable in tests via `app.dependency_overrides`.
- Keep dependencies small and composable. `get_current_user` should depend on `get_db_session`,
  not duplicate its logic.
- Scope database sessions per request (see `app/db/session.py`). Never share a session across
  requests or stash one on a module-level global.

## 5. Validation and schemas

- Let Pydantic do all input validation. Don't hand-roll type checks or manual field validation
  in endpoint bodies.
- Define separate schemas for create, update, and read operations even when they overlap today
  (`UserCreate` includes a password; `UserRead` never does). This prevents an API from
  accidentally leaking a field added for one purpose through an endpoint that was never meant
  to expose it.
- Use `Field(min_length=..., max_length=...)` and explicit types (`EmailStr`, `PositiveInt`,
  etc.) instead of validating after the fact in route handlers.
- Set `response_model` on every route. It documents the contract, strips unexpected fields,
  and is what populates the OpenAPI schema correctly.

## 6. Error handling

- Raise typed exceptions (`NotFoundError`, `ConflictError`, `UnauthorizedError` in this kit's
  `core/exceptions.py`) from business logic, and translate them to HTTP responses in one place
  via `app.exception_handler`. Don't scatter `raise HTTPException(...)` through CRUD code; it
  couples persistence logic to the web framework.
- Never let an unhandled exception leak internal details (stack traces, SQL, file paths) to a
  client. Let FastAPI's default 500 handler catch truly unexpected errors, and make sure
  `debug=False` in any non-local environment so Starlette doesn't return a debug traceback page.
- Return consistent error shapes. This kit uses `{"detail": "..."}` to match FastAPI's own
  convention; if you need machine-readable error codes, add a `code` field rather than
  inventing a second shape.

## 7. Security

- Hash passwords with `bcrypt` (or `argon2`) and a per-password salt; this kit uses `bcrypt`
  directly. Never store or log plaintext passwords.
- Sign JWTs with a secret that is generated per environment and long enough to resist brute
  force (32+ random bytes). Rotate it like any other credential if it's ever exposed.
- Set a short access token expiry (this kit defaults to 30 minutes) and add a refresh-token flow
  before shipping anything that needs longer sessions; don't just extend the access token
  lifetime.
- Validate the `Authorization` header via `OAuth2PasswordBearer` and a dependency, not by
  parsing headers manually in each route.
- Restrict CORS (`backend_cors_origins`) to known origins. Never set `allow_origins=["*"]`
  together with `allow_credentials=True`; browsers reject it and it's a bad default even when
  they don't.
- Keep dependencies patched. Run `pip list --outdated` or a dedicated tool (Dependabot,
  `pip-audit`) regularly; FastAPI, Pydantic, and SQLAlchemy all ship security fixes.
- Treat every user-supplied value that reaches a database query as untrusted. SQLAlchemy's
  query builder (used throughout this kit) parameterizes values automatically; avoid raw string
  interpolation into `text()` queries.

## 8. Database and migrations

- Never call `Base.metadata.create_all()` outside of local dev convenience scripts and tests
  (see `app/db/init_db.py`'s docstring). Every schema change in a real environment goes through
  an Alembic migration, reviewed like any other code change.
- Generate migrations with `alembic revision --autogenerate`, then read the generated file. 
  Autogenerate misses some changes (renames, some constraint changes) and occasionally proposes
  destructive drops; never apply one you haven't read.
- Keep one Alembic head. If two branches each add a migration, merge them with
  `alembic merge heads` rather than letting the history fork silently.
- Add indexes for columns used in `WHERE`, `JOIN`, or `ORDER BY` clauses (see the `index=True`
  on `User.email`). Review slow queries with `EXPLAIN ANALYZE` before guessing at fixes.

## 9. Testing

- Test through the HTTP layer with `httpx.AsyncClient` against the ASGI app (see
  `tests/conftest.py`), not by calling route functions directly. This exercises dependency
  injection, validation, and serialization the way a real client would.
- Override dependencies (`app.dependency_overrides`) for things like the database session;
  don't monkeypatch internals.
- Give tests a real, disposable database (SQLite file or a throwaway Postgres schema/container)
  rather than mocking the ORM. Mocked database tests pass while the real migration or query is
  broken, which defeats the point of the test.
- Keep tests independent and order-agnostic. The `autouse` fixture in this kit creates and
  drops all tables around every test; don't rely on state left over from a previous test.

## 10. Logging and observability

- Log structured, not formatted strings, once the project needs to query logs (JSON lines
  work well with most log aggregators). This kit ships a minimal `logging` setup;
  swap in `structlog` or similar when that need shows up.
- Never log request bodies or headers wholesale; they can contain passwords, tokens, or PII.
  Log identifiers (user id, request id) instead of full payloads.
- Add a request id (middleware or `contextvars`) once you have more than one service, so a
  single request can be traced across logs.
- Expose a `/health` endpoint (already included) for load balancers and orchestrators, and keep
  it fast and dependency-free unless you specifically want it to also check the database.

## 11. API design and versioning

- Prefix all routes with a version (`/api/v1`, already wired up). When a breaking change is
  unavoidable, add `/api/v2` rather than breaking existing clients in place.
- Use plural nouns for resource collections (`/users`, not `/user` or `/getUsers`) and let HTTP
  methods carry the verb.
- Set `response_model` and realistic example values so `/docs` is actually useful to API
  consumers, including the future version of your own team.

## 12. Performance

- Use connection pooling (SQLAlchemy's engine does this by default; tune `pool_size` under
  real load, don't guess upfront).
- Paginate any endpoint that can return an unbounded list (`skip`/`limit` as a baseline;
  cursor-based pagination once offsets get expensive at scale).
- Add caching (Redis, or FastAPI's own response caching via a library) only once you've
  measured a real bottleneck. Premature caching hides correctness bugs behind stale data.

## 13. Deployment

- Build a multi-stage, non-root Docker image (see `Dockerfile`). Don't run the app as root in
  a container.
- Run with a production ASGI setup (Uvicorn workers behind Gunicorn, or multiple Uvicorn
  workers directly) rather than a single `--reload` process.
- Keep `/docs` and `/redoc` available in development and staging, and decide deliberately
  whether to disable them in production (this kit disables them when `ENVIRONMENT=production`);
  an exposed schema isn't a vulnerability by itself, but don't expose it by accident.
- Run migrations (`alembic upgrade head`) as an explicit deploy step, before the new app version
  starts serving traffic, not automatically on app startup in a multi-replica deployment (two
  replicas racing to migrate on boot is a classic source of corrupted migration state).

## 14. Code quality tooling

- Format and lint with `ruff` (this kit configures both `ruff check` and `ruff format`).
  Consistent formatting removes an entire category of review comments.
- Type-check with `mypy --strict` or close to it. FastAPI and Pydantic are typed well enough
  that strict mode catches real bugs, not just style issues.
- Wire both into `pre-commit` so they run before code is committed, not just in CI where
  feedback is slower.
- Keep CI doing the same checks as local tooling (lint, format check, type check, tests) so
  "works on my machine" can't slip through.

## Notes on this document

This file describes the practices this specific starter kit follows out of the box, and the
reasoning behind each one, drawn from widely used FastAPI community conventions (the official
FastAPI documentation's project structure guidance and SQLAlchemy 2.0's async patterns). It is
not an industry standard or a compliance artifact; review and adapt it for your team's own
constraints before treating it as policy.
