"""Prometheus metrics shared by the HTTP API routes."""

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

HTTP_REQUESTS = Counter(
    "jev_fhir_http_requests_total",
    "HTTP requests handled by endpoint",
    ["endpoint", "method", "status"],
)
HTTP_LATENCY = Histogram(
    "jev_fhir_http_request_duration_seconds", "HTTP request duration by endpoint", ["endpoint"]
)
JEV_DECISIONS = Counter(
    "jev_fhir_decisions_total", "Jev decisions by module and outcome", ["module", "decision"]
)
JEV_CONFIDENCE = Histogram(
    "jev_fhir_decision_confidence", "Jev decision confidence by module", ["module"]
)


def record_decision(module: str, decision: str, confidence: float) -> None:
    """Record the outcome and confidence of a decision-module call."""
    JEV_DECISIONS.labels(module=module, decision=decision).inc()
    JEV_CONFIDENCE.labels(module=module).observe(confidence)


def metrics_payload() -> tuple[bytes, str]:
    """Return the Prometheus exposition payload and its required media type."""
    return generate_latest(), CONTENT_TYPE_LATEST
