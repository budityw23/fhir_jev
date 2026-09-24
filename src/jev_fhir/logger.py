"""Structured logging for Jev decisions."""

from collections.abc import Mapping
from typing import Any, cast

import structlog


def configure_logging() -> None:
    """Configure structlog to emit one JSON object per log record."""
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ]
    )


def get_logger() -> structlog.stdlib.BoundLogger:
    """Get the project logger."""
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger("jev_fhir"))


def log_decision(
    *,
    module: str,
    resource_reference: str,
    decision: str | bool | int,
    confidence: float,
    latency_ms: float,
    extra: Mapping[str, Any] | None = None,
) -> None:
    """Emit the common structured record required for every decision."""
    event: dict[str, Any] = {
        "module": module,
        "resource_reference": resource_reference,
        "decision": decision,
        "confidence": confidence,
        "latency_ms": latency_ms,
    }
    if extra is not None:
        event.update(extra)
    get_logger().info("jev_decision", **event)
