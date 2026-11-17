#!/usr/bin/env python3
"""
Observability Engineering: Logs, Metrics, and Distributed Traces

A self-contained observability platform demonstrating:
- Structured logging and sensitive-data redaction
- Metrics collection, aggregation, and threshold evaluation
- Distributed tracing and span relationships
- Correlation through trace IDs
- Service health monitoring
- Alert evaluation and incident detection
- JSON Lines export
- Validation, failure handling, and automated assertions

Requires Python 3.10+.
Uses only the Python standard library.
"""

from __future__ import annotations

import json
import logging
import math
import re
import statistics
import sys
import time
import uuid

from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional


# ============================================================
# 1. DOMAIN TYPES
# ============================================================

class Severity(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class SpanStatus(str, Enum):
    UNSET = "UNSET"
    OK = "OK"
    ERROR = "ERROR"


class AlertState(str, Enum):
    NORMAL = "NORMAL"
    FIRING = "FIRING"
    RESOLVED = "RESOLVED"


class MetricType(str, Enum):
    COUNTER = "COUNTER"
    GAUGE = "GAUGE"
    HISTOGRAM = "HISTOGRAM"


# ============================================================
# 2. VALIDATION AND SECURITY
# ============================================================

class ObservabilityError(Exception):
    """Base exception for observability failures."""


class ValidationError(ObservabilityError):
    """Invalid telemetry or configuration."""


class DuplicateIdentifierError(ObservabilityError):
    """An identifier already exists."""


class StorageError(ObservabilityError):
    """Telemetry persistence failure."""


class SecurityPolicy:
    """
    Removes sensitive information before telemetry is exported.

    Production deployments should also apply structured field
    allowlists, access controls, encryption, and retention limits.
    """

    SENSITIVE_KEYS = {
        "password",
        "passwd",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "api_key",
        "secret",
        "credit_card",
        "ssn",
    }

    PATTERNS = [
        re.compile(
            r"(?i)(authorization\s*[:=]\s*)(bearer\s+)?[^\s,;]+"
        ),
        re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
        ),
    ]

    @classmethod
    def sanitize(cls, value: Any, key: str = "") -> Any:
        if key.lower() in cls.SENSITIVE_KEYS:
            return "[REDACTED]"

        if isinstance(value, dict):
            return {
                str(k): cls.sanitize(v, str(k))
                for k, v in value.items()
            }

        if isinstance(value, list):
            return [cls.sanitize(item) for item in value]

        if isinstance(value, tuple):
            return [cls.sanitize(item) for item in value]

        if isinstance(value, str):
            result = value

            for pattern in cls.PATTERNS:
                if "authorization" in pattern.pattern.lower():
                    result = pattern.sub(
                        lambda match: match.group(1) + "[REDACTED]",
                        result,
                    )
                else:
                    result = pattern.sub("[REDACTED_EMAIL]", result)

            return result

        return value


def validate_name(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} cannot be empty.")

    if len(value) > 128:
        raise ValidationError(f"{field_name} exceeds 128 characters.")

    if not re.fullmatch(r"[A-Za-z0-9_.:/-]+", value):
        raise ValidationError(f"Invalid {field_name}: {value!r}")


def validate_number(value: float, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{field_name} must be numeric.")

    result = float(value)

    if not math.isfinite(result):
        raise ValidationError(f"{field_name} must be finite.")

    return result


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# 3. STRUCTURED LOGGING
# ============================================================

@dataclass
class LogRecord:
    timestamp: str
    level: Severity
    service: str
    message: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["level"] = self.level.value
        return data


class StructuredLogger:
    """
    Stores structured events instead of relying exclusively
    on unstructured text messages.
    """

    def __init__(self, service: str):
        validate_name(service, "service")
        self.service = service
        self.records: list[LogRecord] = []

    def log(
        self,
        level: Severity,
        message: str,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        attributes: Optional[dict[str, Any]] = None,
    ) -> LogRecord:

        if not isinstance(level, Severity):
            raise ValidationError("Invalid log severity.")

        if not isinstance(message, str) or not message.strip():
            raise ValidationError("Log message cannot be empty.")

        if len(message) > 4096:
            raise ValidationError("Log message exceeds 4096 characters.")

        safe_attributes = SecurityPolicy.sanitize(
            attributes or {}
        )

        safe_message = SecurityPolicy.sanitize(message)

        record = LogRecord(
            timestamp=utc_now(),
            level=level,
            service=self.service,
            message=safe_message,
            trace_id=trace_id,
            span_id=span_id,
            attributes=safe_attributes,
        )

        self.records.append(record)
        return record

    def query(
        self,
        level: Optional[Severity] = None,
        trace_id: Optional[str] = None,
    ) -> list[LogRecord]:

        return [
            record
            for record in self.records
            if (level is None or record.level == level)
            and (trace_id is None or record.trace_id == trace_id)
        ]


# ============================================================
# 4. METRICS
# ============================================================

@dataclass
class Metric:
    name: str
    metric_type: MetricType
    value: float
    timestamp: str
    service: str
    labels: dict[str, str] = field(default_factory=dict)


class MetricsRegistry:
    """
    Implements counters, gauges, and histogram observations.

    Counters are monotonic.
    Gauges can increase or decrease.
    Histograms retain observations for aggregation.
    """

    def __init__(self):
        self.counters: dict[tuple, float] = defaultdict(float)
        self.gauges: dict[tuple, float] = {}
        self.histograms: dict[tuple, list[float]] = defaultdict(list)

    @staticmethod
    def _key(
        name: str,
        service: str,
        labels: Optional[dict[str, str]],
    ) -> tuple:

        validate_name(name, "metric name")
        validate_name(service, "service")

        normalized = tuple(
            sorted((str(k), str(v)) for k, v in (labels or {}).items())
        )

        if len(normalized) > 20:
            raise ValidationError("Too many metric labels.")

        for key, value in normalized:
            validate_name(key, "label key")

            if len(value) > 128:
                raise ValidationError("Metric label value too long.")

        return name, service, normalized

    def increment(
        self,
        name: str,
        service: str,
        amount: float = 1,
        labels: Optional[dict[str, str]] = None,
    ) -> float:

        amount = validate_number(amount, "counter increment")

        if amount < 0:
            raise ValidationError("Counters cannot decrease.")

        key = self._key(name, service, labels)
        self.counters[key] += amount
        return self.counters[key]

    def set_gauge(
        self,
        name: str,
        service: str,
        value: float,
        labels: Optional[dict[str, str]] = None,
    ) -> None:

        key = self._key(name, service, labels)
        self.gauges[key] = validate_number(value, "gauge value")

    def observe(
        self,
        name: str,
        service: str,
        value: float,
        labels: Optional[dict[str, str]] = None,
    ) -> None:

        key = self._key(name, service, labels)
        value = validate_number(value, "histogram observation")

        if value < 0:
            raise ValidationError("Duration observations cannot be negative.")

        self.histograms[key].append(value)

    @staticmethod
    def percentile(values: list[float], percentile_value: float) -> float:
        if not values:
            raise ValidationError("Cannot calculate empty percentile.")

        if not 0 <= percentile_value <= 100:
            raise ValidationError("Percentile must be between 0 and 100.")

        ordered = sorted(values)

        index = (len(ordered) - 1) * percentile_value / 100
        lower = math.floor(index)
        upper = math.ceil(index)

        if lower == upper:
            return ordered[lower]

        fraction = index - lower

        return (
            ordered[lower] * (1 - fraction)
            + ordered[upper] * fraction
        )

    def histogram_summary(
        self,
        name: str,
        service: str,
        labels: Optional[dict[str, str]] = None,
    ) -> dict[str, float]:

        key = self._key(name, service, labels)
        values = self.histograms.get(key, [])

        if not values:
            raise ValidationError("Histogram has no observations.")

        return {
            "count": len(values),
            "sum": sum(values),
            "average": statistics.fmean(values),
            "min": min(values),
            "max": max(values),
            "p50": self.percentile(values, 50),
            "p95": self.percentile(values, 95),
            "p99": self.percentile(values, 99),
        }

    def snapshot(self) -> list[Metric]:
        result = []

        for (name, service, labels), value in self.counters.items():
            result.append(
                Metric(
                    name, MetricType.COUNTER, value,
                    utc_now(), service, dict(labels)
                )
            )

        for (name, service, labels), value in self.gauges.items():
            result.append(
                Metric(
                    name, MetricType.GAUGE, value,
                    utc_now(), service, dict(labels)
                )
            )

        for (name, service, labels), values in self.histograms.items():
            if values:
                result.append(
                    Metric(
                        name,
                        MetricType.HISTOGRAM,
                        float(len(values)),
                        utc_now(),
                        service,
                        dict(labels),
                    )
                )

        return result


# ============================================================
# 5. DISTRIBUTED TRACING
# ============================================================

@dataclass
class Span:
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    service: str
    operation: str
    start_time: float
    end_time: Optional[float] = None
    status: SpanStatus = SpanStatus.UNSET
    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> Optional[float]:
        if self.end_time is None:
            return None

        return (self.end_time - self.start_time) * 1000


class Trace:
    def __init__(self, trace_id: str):
        self.trace_id = trace_id
        self.spans: dict[str, Span] = {}

    def start_span(
        self,
        service: str,
        operation: str,
        parent_span_id: Optional[str] = None,
        attributes: Optional[dict[str, Any]] = None,
    ) -> Span:

        validate_name(service, "service")
        validate_name(operation, "operation")

        if parent_span_id is not None:
            parent = self.spans.get(parent_span_id)

            if parent is None:
                raise ValidationError("Parent span does not exist.")

            if parent.end_time is not None:
                raise ValidationError("Cannot create child of completed span.")

        span_id = uuid.uuid4().hex[:16]

        while span_id in self.spans:
            span_id = uuid.uuid4().hex[:16]

        span = Span(
            trace_id=self.trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            service=service,
            operation=operation,
            start_time=time.perf_counter(),
            attributes=SecurityPolicy.sanitize(attributes or {}),
        )

        self.spans[span_id] = span
        return span

    def end_span(
        self,
        span_id: str,
        status: SpanStatus = SpanStatus.OK,
    ) -> None:

        span = self.spans.get(span_id)

        if span is None:
            raise ValidationError("Unknown span.")

        if span.end_time is not None:
            raise ValidationError("Span has already ended.")

        if not isinstance(status, SpanStatus):
            raise ValidationError("Invalid span status.")

        span.end_time = time.perf_counter()
        span.status = status

    def validate(self) -> None:
        for span in self.spans.values():

            if span.end_time is None:
                raise ValidationError(
                    f"Span {span.span_id} is still running."
                )

            if span.parent_span_id is not None:
                if span.parent_span_id not in self.spans:
                    raise ValidationError("Broken span relationship.")

        # Check parent relationships for cycles.
        for span in self.spans.values():
            visited = set()
            current = span

            while current.parent_span_id is not None:
                if current.span_id in visited:
                    raise ValidationError("Circular span relationship.")

                visited.add(current.span_id)
                current = self.spans[current.parent_span_id]


class TracingRegistry:
    def __init__(self):
        self.traces: dict[str, Trace] = {}

    def start_trace(self) -> Trace:
        trace_id = uuid.uuid4().hex

        while trace_id in self.traces:
            trace_id = uuid.uuid4().hex

        trace = Trace(trace_id)
        self.traces[trace_id] = trace
        return trace

    def get_trace(self, trace_id: str) -> Trace:
        if trace_id not in self.traces:
            raise ValidationError("Trace not found.")

        return self.traces[trace_id]


# ============================================================
# 6. ALERTING
# ============================================================

@dataclass
class AlertRule:
    name: str
    metric_name: str
    threshold: float
    comparison: str
    evaluation_window: int = 1

    def __post_init__(self):
        validate_name(self.name, "alert name")
        validate_name(self.metric_name, "metric name")

        self.threshold = validate_number(
            self.threshold, "alert threshold"
        )

        if self.comparison not in {">", ">=", "<", "<="}:
            raise ValidationError("Unsupported comparison operator.")

        if self.evaluation_window < 1:
            raise ValidationError("Evaluation window must be positive.")


@dataclass
class Alert:
    name: str
    state: AlertState
    value: float
    threshold: float
    timestamp: str


class AlertManager:
    def __init__(self):
        self.rules: dict[str, AlertRule] = {}
        self.states: dict[str, AlertState] = {}
        self.events: list[Alert] = {}
        self.history: dict[str, deque] = defaultdict(deque)

    def add_rule(self, rule: AlertRule) -> None:
        if rule.name in self.rules:
            raise DuplicateIdentifierError("Alert rule already exists.")

        self.rules[rule.name] = rule
        self.states[rule.name] = AlertState.NORMAL

    def evaluate(
        self,
        rule_name: str,
        metric_value: float,
    ) -> Alert:

        if rule_name not in self.rules:
            raise ValidationError("Unknown alert rule.")

        value = validate_number(metric_value, "metric value")
        rule = self.rules[rule_name]

        history = self.history[rule_name]
        history.append(value)

        while len(history) > rule.evaluation_window:
            history.popleft()

        if len(history) < rule.evaluation_window:
            state = self.states[rule_name]
        else:
            average = statistics.fmean(history)

            conditions = {
                ">": average > rule.threshold,
                ">=": average >= rule.threshold,
                "<": average < rule.threshold,
                "<=": average <= rule.threshold,
            }

            state = (
                AlertState.FIRING
                if conditions[rule.comparison]
                else AlertState.NORMAL
            )

        previous = self.states[rule_name]
        self.states[rule_name] = state

        if state != previous:
            event = Alert(
                rule_name,
                state,
                value,
                rule.threshold,
                utc_now(),
            )

            self.events.append(event)
            return event

        return Alert(
            rule_name,
            state,
            value,
            rule.threshold,
            utc_now(),
        )


# ============================================================
# 7. OBSERVABILITY PLATFORM
# ============================================================

class ObservabilityPlatform:
    def __init__(self, export_directory: str = "observability_data"):
        self.loggers: dict[str, StructuredLogger] = {}
        self.metrics = MetricsRegistry()
        self.tracing = TracingRegistry()
        self.alerts = AlertManager()
        self.export_directory = Path(export_directory)

    def logger(self, service: str) -> StructuredLogger:
        if service not in self.loggers:
            self.loggers[service] = StructuredLogger(service)

        return self.loggers[service]

    def correlate_logs(self, trace_id: str) -> list[LogRecord]:
        return [
            record
            for logger in self.loggers.values()
            for record in logger.query(trace_id=trace_id)
        ]

    def export_jsonl(self) -> Path:
        try:
            self.export_directory.mkdir(
                parents=True,
                exist_ok=True,
            )

            output = self.export_directory / "observability.jsonl"
            temporary = output.with_suffix(".tmp")

            records = []

            for logger in self.loggers.values():
                for record in logger.records:
                    records.append({
                        "type": "log",
                        "data": record.to_dict(),
                    })

            for metric in self.metrics.snapshot():
                records.append({
                    "type": "metric",
                    "data": asdict(metric),
                })

            for trace in self.tracing.traces.values():
                for span in trace.spans.values():
                    records.append({
                        "type": "span",
                        "data": {
                            **asdict(span),
                            "status": span.status.value,
                            "duration_ms": span.duration_ms,
                        },
                    })

            with temporary.open("w", encoding="utf-8") as file:
                for record in records:
                    file.write(json.dumps(record, allow_nan=False) + "\n")

            temporary.replace(output)
            return output

        except (OSError, TypeError, ValueError) as exc:
            raise StorageError(f"Telemetry export failed: {exc}") from exc


# ============================================================
# 8. REALISTIC SERVICE WORKFLOW
# ============================================================

def simulate_payment_request(
    platform: ObservabilityPlatform,
    amount: float,
    should_fail: bool = False,
) -> str:

    amount = validate_number(amount, "payment amount")

    if amount <= 0 or amount > 1_000_000:
        raise ValidationError("Payment amount is outside permitted limits.")

    trace = platform.tracing.start_trace()
    logger = platform.logger("payment-api")

    root = trace.start_span(
        "payment-api",
        "POST /payments",
        attributes={"payment_amount": amount},
    )

    logger.log(
        Severity.INFO,
        "Payment request received",
        trace.trace_id,
        root.span_id,
        {"amount": amount},
    )

    platform.metrics.increment(
        "payment_requests_total",
        "payment-api",
        labels={"environment": "production"},
    )

    platform.metrics.observe(
        "payment_request_duration_ms",
        "payment-api",
        125.0 if not should_fail else 250.0,
    )

    database = trace.start_span(
        "payment-database",
        "INSERT payment",
        root.span_id,
    )

    trace.end_span(database.span_id)

    processor = trace.start_span(
        "payment-processor",
        "authorize transaction",
        root.span_id,
    )

    if should_fail:
        trace.end_span(processor.span_id, SpanStatus.ERROR)
        trace.end_span(root.span_id, SpanStatus.ERROR)

        logger.log(
            Severity.ERROR,
            "Payment authorization failed",
            trace.trace_id,
            processor.span_id,
            {"error_code": "PAYMENT_DECLINED"},
        )

        platform.metrics.increment(
            "payment_failures_total",
            "payment-api",
        )

    else:
        trace.end_span(processor.span_id)
        trace.end_span(root.span_id)

        logger.log(
            Severity.INFO,
            "Payment completed",
            trace.trace_id,
            root.span_id,
        )

        platform.metrics.increment(
            "payment_success_total",
            "payment-api",
        )

    trace.validate()
    return trace.trace_id


# ============================================================
# 9. REPORTING
# ============================================================

def print_report(platform: ObservabilityPlatform) -> None:

    print("\n" + "=" * 65)
    print("OBSERVABILITY PLATFORM REPORT")
    print("=" * 65)

    print("\nLOGS")

    for logger in platform.loggers.values():
        print(f"\nService: {logger.service}")

        for record in logger.records:
            print(
                f"{record.timestamp} "
                f"{record.level.value:<8} "
                f"{record.message}"
            )

    print("\nMETRICS")

    for metric in platform.metrics.snapshot():
        print(
            f"{metric.name:<35} "
            f"{metric.metric_type.value:<10} "
            f"{metric.value}"
        )

    print("\nLATENCY DISTRIBUTION")

    for key in platform.metrics.histograms:
        name, service, labels = key

        summary = platform.metrics.histogram_summary(
            name,
            service,
            dict(labels),
        )

        print(f"{service}.{name}: {summary}")

    print("\nDISTRIBUTED TRACES")

    for trace in platform.tracing.traces.values():
        print(f"\nTrace ID: {trace.trace_id}")

        for span in trace.spans.values():
            print(
                f"{span.service:<22} "
                f"{span.operation:<28} "
                f"{span.status.value:<8} "
                f"{span.duration_ms:.3f} ms"
            )

    print("\nALERT EVENTS")

    for event in platform.alerts.events:
        print(
            f"{event.name}: "
            f"{event.state.value}, "
            f"value={event.value}, "
            f"threshold={event.threshold}"
        )


# ============================================================
# 10. TESTS AND EXECUTION
# ============================================================

def run_tests() -> None:

    platform = ObservabilityPlatform()

    successful_trace = simulate_payment_request(
        platform,
        amount=1500.00,
    )

    failed_trace = simulate_payment_request(
        platform,
        amount=2500.00,
        should_fail=True,
    )

    # Trace correlation must return records from the same request.
    correlated = platform.correlate_logs(successful_trace)
    assert len(correlated) == 2

    failed_logs = platform.correlate_logs(failed_trace)
    assert any(
        record.level == Severity.ERROR
        for record in failed_logs
    )

    # Verify sensitive information is redacted.
    logger = platform.logger("security-service")

    secure_record = logger.log(
        Severity.WARNING,
        "Authentication attempt",
        attributes={
            "password": "secret-value",
            "username": "operator",
        },
    )

    assert secure_record.attributes["password"] == "[REDACTED]"

    # Verify counter restrictions.
    try:
        platform.metrics.increment(
            "invalid_counter",
            "payment-api",
            -1,
        )
        raise AssertionError("Negative counter was accepted.")
    except ValidationError:
        pass

    # Verify histogram statistics.
    platform.metrics.observe("test_latency", "test", 10)
    platform.metrics.observe("test_latency", "test", 20)
    platform.metrics.observe("test_latency", "test", 30)

    summary = platform.metrics.histogram_summary(
        "test_latency",
        "test",
    )

    assert summary["count"] == 3
    assert summary["average"] == 20
    assert summary["p50"] == 20

    # Verify alert state transitions.
    rule = AlertRule(
        name="high_request_latency",
        metric_name="payment_request_duration_ms",
        threshold=200,
        comparison=">",
        evaluation_window=2,
    )

    platform.alerts.add_rule(rule)

    first = platform.alerts.evaluate(
        "high_request_latency",
        220,
    )

    second = platform.alerts.evaluate(
        "high_request_latency",
        240,
    )

    assert first.state == AlertState.NORMAL
    assert second.state == AlertState.FIRING

    resolved = platform.alerts.evaluate(
        "high_request_latency",
        100,
    )

    assert resolved.state == AlertState.FIRING

    recovered = platform.alerts.evaluate(
        "high_request_latency",
        120,
    )

    assert recovered.state == AlertState.RESOLVED

    # Invalid input must fail safely.
    try:
        simulate_payment_request(platform, amount=-100)
        raise AssertionError("Negative payment was accepted.")
    except ValidationError:
        pass

    output = platform.export_jsonl()

    assert output.exists()
    assert output.stat().st_size > 0

    print_report(platform)

    print("\n" + "=" * 65)
    print("ALL OBSERVABILITY TESTS PASSED")
    print(f"Exported telemetry: {output.resolve()}")
    print("=" * 65)


if __name__ == "__main__":
    try:
        run_tests()
    except (ObservabilityError, OSError) as error:
        logging.exception("Observability execution failed: %s", error)
        sys.exit(1)
