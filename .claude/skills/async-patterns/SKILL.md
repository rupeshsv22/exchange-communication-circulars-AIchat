---
name: async-patterns
description: Use when writing async Python code, handling concurrency, or dealing with asyncio tasks, gathers, timeouts, or background jobs.
---

# Async Patterns

## Rules
- `async def` for all I/O functions; never mix sync blocking calls in async path
- Use `httpx.AsyncClient` (reuse instance), not `requests`
- Concurrency: `asyncio.gather()` for independent tasks, `asyncio.TaskGroup` (3.11+) preferred
- Timeouts mandatory on external calls: `async with asyncio.timeout(5):`
- Background work: Celery or arq, not `asyncio.create_task` in request handlers (lost on restart)

## Anti-patterns
- No `time.sleep` — use `asyncio.sleep`
- No blocking file I/O — use `aiofiles` or `run_in_executor`
- No unbounded `gather` — use `asyncio.Semaphore` to cap concurrency
- No fire-and-forget tasks without keeping a reference (GC will kill them)

## Error handling
- `asyncio.gather(..., return_exceptions=True)` when partial failure is acceptable
- Propagate cancellation: catch `asyncio.CancelledError` only to clean up, then re-raise