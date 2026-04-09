from __future__ import annotations

import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ]
)


def get_logger(name: str) -> structlog.BoundLogger:
    return structlog.get_logger(name)
