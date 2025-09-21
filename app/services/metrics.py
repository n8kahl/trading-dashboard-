from __future__ import annotations

from prometheus_client import Counter, Histogram

# Track Polygon REST request counts by status code / outcome.
polygon_request_total = Counter(
    "polygon_request_total",
    "Polygon REST requests grouped by resolved path and status.",
    ("path", "status"),
)

# Capture retryable responses (e.g., 429, 5xx, timeouts).
polygon_request_retry_total = Counter(
    "polygon_request_retry_total",
    "Polygon REST retries grouped by path and reason.",
    ("path", "reason"),
)

# Measure end-to-end latency per Polygon REST path.
polygon_request_latency = Histogram(
    "polygon_request_latency_seconds",
    "Polygon REST request latency in seconds by path.",
    ("path",),
)

__all__ = [
    "polygon_request_total",
    "polygon_request_retry_total",
    "polygon_request_latency",
]
