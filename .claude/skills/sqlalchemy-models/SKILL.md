---
name: sqlalchemy-models
description: Use when creating or modifying SQLAlchemy ORM models, database queries, or repository patterns. Triggers on ORM, models, queries, joins, or database schema changes.
---

# SQLAlchemy Models

## Conventions
- SQLAlchemy 2.0 style: `Mapped[]`, `mapped_column()`, `DeclarativeBase`
- Models in `app/models/<resource>.py`, one class per file for large models
- Always `id: Mapped[int] = mapped_column(primary_key=True)` unless UUID required
- Timestamps via mixin: `created_at`, `updated_at` with `server_default=func.now()`
- Use `relationship()` with explicit `back_populates`, never `backref`

## Querying
- Async sessions only: `AsyncSession`
- Use `select()` statements, never legacy `Query`
- Eager load with `selectinload()` for collections, `joinedload()` for single relations
- Repository pattern: `app/repositories/<resource>_repo.py` wraps all queries

## Rules
- No lazy loading in async context (will raise)
- Always `await session.commit()` explicitly, use `async with session.begin()` for atomic ops
- Index foreign keys and frequently-queried columns
- Use `Numeric` for money, never `Float`