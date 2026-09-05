"""Logs, traces and metrics.

The 2026-07-28 revision deprecated protocol-level logging in
favour of stderr for stdio and OpenTelemetry for structured
observability. This module does both, and nothing here writes
to stdout.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from collections import Counter
from dataclasses import dataclass, field

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer("aiops")

# Fields that must never reach a log line, whatever a handler
# passes. SecretStr covers the settings object; this covers
# everything assembled by hand.
REDACT = frozenset(
    {"token", "password", "dsn", "authorization", "secret"}
)


class JSONFormatter(logging.Formatter):
    """One JSON object per line, on stderr."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        span = trace.get_current_span().get_span_context()
        if span.is_valid:
            # The join between a log line and its trace.
            payload["trace_id"] = format(span.trace_id, "032x")
            payload["span_id"] = format(span.span_id, "016x")
        for key, value in getattr(record, "fields", {}).items():
            payload[key] = (
                "[redacted]"
                if key.lower() in REDACT
                else value
            )
        if record.exc_info:
            payload["exception"] = self.formatException(
                record.exc_info
            )
        return json.dumps(payload)


def configure_logging(level: str = "INFO") -> None:
    """Structured logs on stderr. Never stdout: under stdio
    that stream is the protocol, and under HTTP a shared
    format matters more than a pretty one."""
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JSONFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(os.environ.get("AIOPS_LOG_LEVEL", level))


def log(logger: logging.Logger, level: int, msg: str, **fields):
    """Log with structured fields rather than interpolation."""
    logger.log(level, msg, extra={"fields": fields})


@dataclass
class Metrics:
    """The four numbers worth having, per tool."""

    calls: Counter = field(default_factory=Counter)
    errors: Counter = field(default_factory=Counter)
    duration_ms: dict[str, list[float]] = field(
        default_factory=dict
    )

    def record(
        self, tool: str, elapsed_ms: float, failed: bool
    ) -> None:
        self.calls[tool] += 1
        if failed:
            self.errors[tool] += 1
        self.duration_ms.setdefault(tool, []).append(elapsed_ms)

    def snapshot(self) -> dict[str, dict[str, float]]:
        out: dict[str, dict[str, float]] = {}
        for tool, count in self.calls.items():
            samples = sorted(self.duration_ms.get(tool, []))
            index = max(0, int(len(samples) * 0.95) - 1)
            out[tool] = {
                "calls": count,
                "errors": self.errors[tool],
                "p50_ms": round(
                    samples[len(samples) // 2], 1
                )
                if samples
                else 0.0,
                "p95_ms": round(samples[index], 1)
                if samples
                else 0.0,
            }
        return out


METRICS = Metrics()
logger = logging.getLogger("aiops.tools")


class MetricsMiddleware:
    """Counts, durations and error rates per tool.

    Deliberately not a tracing middleware. The SDK already
    emits a SERVER span per request named `tools/call <name>`,
    and propagates trace context from the caller, so writing
    spans here would duplicate them. What the SDK does not
    give you is aggregate numbers, which is what this adds.
    """

    async def __call__(self, ctx, call_next):
        if ctx.request_id is None:
            return await call_next(ctx)

        method = ctx.method or "unknown"
        name = (ctx.params or {}).get("name") or ""
        label = f"{method}:{name}" if name else method
        started = time.monotonic()
        failed = False
        try:
            result = await call_next(ctx)
        except Exception:
            # A protocol error: the request was never served.
            failed = True
            raise
        else:
            # A tool that ran and failed returns rather than
            # raising, so the error rate is read off the
            # result. Middleware sits at the wire layer, so
            # the key is camelCase: `isError`, not
            # `is_error`. Chapter 3 established the split.
            if isinstance(result, dict):
                failed = bool(result.get("isError"))
            return result
        finally:
            elapsed = (time.monotonic() - started) * 1000
            METRICS.record(label, elapsed, failed)
            # Attach the outcome to the SDK's own span, so a
            # trace and these numbers agree.
            span = trace.get_current_span()
            if span.is_recording():
                span.set_attribute("mcp.duration_ms", elapsed)
                span.set_attribute("mcp.failed", failed)
            log(
                logger,
                logging.INFO,
                "request",
                method=method,
                tool=name or None,
                duration_ms=round(elapsed, 1),
                failed=failed,
            )
