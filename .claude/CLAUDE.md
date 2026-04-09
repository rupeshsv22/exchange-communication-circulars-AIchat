# Project: <name>

## Stack
- Python 3.12, FastAPI, SQLAlchemy, Alembic, Postgres, Redis
- Package manager: uv (or poetry)
- Tests: pytest + pytest-asyncio
- Lint/format: ruff + black, type-check: mypy --strict

## Conventions
- Type hints mandatory, prefer `from __future__ import annotations`
- Async-first for I/O, use `httpx.AsyncClient` not requests
- Pydantic v2 models for all boundaries (API, DB, config)
- Settings via pydantic-settings, never hardcode env
- Raise domain-specific exceptions, handle at router layer
- Structured logging with `structlog`, no print()

## Commands
- Install: `uv sync`
- Run: `uvicorn app.main:app --reload`
- Test: `pytest -xvs`
- Lint: `ruff check . && black --check . && mypy .`
- Migrate: `alembic upgrade head`

## Rules
- No new deps without asking
- Run tests + lint before declaring done
- Keep functions < 50 lines, modules < 300