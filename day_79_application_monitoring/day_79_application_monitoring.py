#!/usr/bin/env python3
"""
Application Monitoring System
Health checks, alert management, service availability, and dashboards.

Runtime: Python 3.10+
Dependencies: Python standard library only.
"""

from __future__ import annotations

import json
import logging
import statistics
import time
import uuid

from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Optional


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

logger = logging.getLogger("application_monitor")


# ============================================================
# DOMAIN TYPES
# ============================================================

class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


class Severity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertState(str, Enum):
    FIRING = "FIRING"
    RESOLVED = "RESOLVED"


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    service: str
    status: HealthStatus
    latency_ms: float
    message: str
    checked_at: str
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.latency_ms < 0:
            raise ValueError("Latency cannot be negative")

        if not self.service.strip():
            raise ValueError("Service name cannot be empty")


@dataclass
class Alert:
    alert_id: str
    service: str
    severity: Severity
    state: AlertState
    message: str
    first_seen: str
    last_seen: str
    occurrences: int = 1
    resolved_at: Optional[str] = None


@dataclass(frozen=True)
class ServiceConfig:
    name: str
    warning_latency_ms: float = 500.0
    critical_latency_ms: float = 1500.0
    failure_threshold: int = 2
    recovery_threshold: int = 2

    def __post_init__(self):
        if not self.name.strip():
            raise ValueError("Service name is required")

        if self.warning_latency_ms < 0:
            raise ValueError("Warning threshold cannot be negative")

        if self.critical_latency_ms < self.warning_latency_ms:
            raise ValueError("Critical threshold must exceed warning threshold")

        if self.failure_threshold < 1 or self.recovery_threshold < 1:
            raise ValueError("Threshold counts must be positive")


# ============================================================
# HEALTH CHECKS
# ============================================================

class HealthCheck:
    """Base class for independently executable health checks."""

    def __init__(self, service: str, timeout_seconds: float = 3.0):
        if timeout_seconds <= 0:
            raise ValueError("Timeout must be positive")

        self.service = service
        self.timeout_seconds = timeout_seconds

    def execute(self) -> CheckResult:
        started = time.perf_counter()
        check_id = str(uuid.uuid4())

        try:
            success, message, metadata = self.perform()

            latency = (time.perf_counter() - started) * 1000

            status = (
                HealthStatus.HEALTHY
                if success
                else HealthStatus.UNHEALTHY
            )

            return CheckResult(
                check_id=check_id,
                service=self.service,
                status=status,
                latency_ms=round(latency, 2),
                message=message,
                checked_at=datetime.now(timezone.utc).isoformat(),
                metadata=metadata
            )

        except Exception as exc:
            latency = (time.perf_counter() - started) * 1000

            logger.exception("Health check failed: %s", self.service)

            return CheckResult(
                check_id=check_id,
                service=self.service,
                status=HealthStatus.UNHEALTHY,
                latency_ms=round(latency, 2),
                message=f"Check execution error: {type(exc).__name__}",
                checked_at=datetime.now(timezone.utc).isoformat()
            )

    def perform(self) -> tuple[bool, str, dict]:
        raise NotImplementedError


class ApplicationCheck(HealthCheck):

    def perform(self):
        return True, "Application responding", {
            "component": "application",
            "endpoint": "/health"
        }


class DatabaseCheck(HealthCheck):

    def __init__(self, service: str, available: bool = True):
        super().__init__(service)
        self.available = available

    def perform(self):
        if not self.available:
            return False, "Database connection unavailable", {
                "component": "database"
            }

        return True, "Database connection successful", {
            "component": "database",
            "connection_pool": "available"
        }


class MemoryCheck(HealthCheck):

    def __init__(self, service: str, usage_percent: float):
        super().__init__(service)

        if not 0 <= usage_percent <= 100:
            raise ValueError("Memory usage must be between 0 and 100")

        self.usage_percent = usage_percent

    def perform(self):
        success = self.usage_percent < 90

        return success, (
            "Memory utilization normal"
            if success
            else "Memory utilization exceeded threshold"
        ), {
            "usage_percent": self.usage_percent
        }


class DependencyCheck(HealthCheck):

    def __init__(self, service: str, dependency_available: bool):
        super().__init__(service)
        self.dependency_available = dependency_available

    def perform(self):
        return (
            self.dependency_available,
            "Dependency available"
            if self.dependency_available
            else "External dependency unavailable",
            {"component": "external_dependency"}
        )


# ============================================================
# SERVICE MONITORING
# ============================================================

class ServiceMonitor:

    def __init__(self, config: ServiceConfig):
        self.config = config
        self.checks: list[HealthCheck] = []
        self.history: deque[CheckResult] = deque(maxlen=1000)

        self.consecutive_failures = 0
        self.consecutive_successes = 0

        self.status = HealthStatus.UNKNOWN

    def register_check(self, check: HealthCheck):
        if check.service != self.config.name:
            raise ValueError("Check belongs to another service")

        self.checks.append(check)

    def evaluate(self) -> list[CheckResult]:
        if not self.checks:
            raise RuntimeError(
                f"No health checks registered for {self.config.name}"
            )

        results = [check.execute() for check in self.checks]

        for result in results:
            self.history.append(result)

        failed = any(
            result.status == HealthStatus.UNHEALTHY
            for result in results
        )

        critical_latency = any(
            result.latency_ms >= self.config.critical_latency_ms
            for result in results
        )

        warning_latency = any(
            result.latency_ms >= self.config.warning_latency_ms
            for result in results
        )

        if failed or critical_latency:
            self.consecutive_failures += 1
            self.consecutive_successes = 0

            if self.consecutive_failures >= self.config.failure_threshold:
                self.status = HealthStatus.UNHEALTHY
            else:
                self.status = HealthStatus.DEGRADED

        else:
            self.consecutive_successes += 1
            self.consecutive_failures = 0

            if warning_latency:
                self.status = HealthStatus.DEGRADED
            elif self.consecutive_successes >= self.config.recovery_threshold:
                self.status = HealthStatus.HEALTHY

        return results

    def metrics(self) -> dict:
        if not self.history:
            return {
                "service": self.config.name,
                "status": self.status.value,
                "samples": 0
            }

        latencies = [item.latency_ms for item in self.history]

        healthy = sum(
            item.status == HealthStatus.HEALTHY
            for item in self.history
        )

        return {
            "service": self.config.name,
            "status": self.status.value,
            "samples": len(latencies),
            "average_latency_ms": round(statistics.mean(latencies), 2),
            "maximum_latency_ms": round(max(latencies), 2),
            "minimum_latency_ms": round(min(latencies), 2),
            "availability_percent": round(
                healthy / len(latencies) * 100, 2
            )
        }


# ============================================================
# ALERT MANAGEMENT
# ============================================================

class AlertManager:

    def __init__(self):
        self.alerts: dict[str, Alert] = {}
        self.active_by_service: dict[str, str] = {}

    def process(self, monitor: ServiceMonitor):
        service = monitor.config.name
        status = monitor.status

        active_id = self.active_by_service.get(service)

        if status == HealthStatus.UNHEALTHY:
            severity = Severity.CRITICAL
            message = "Service is unhealthy"

        elif status == HealthStatus.DEGRADED:
            severity = Severity.WARNING
            message = "Service performance is degraded"

        else:
            if active_id:
                self.resolve(active_id)

            return

        now = datetime.now(timezone.utc).isoformat()

        if active_id and self.alerts[active_id].state == AlertState.FIRING:
            alert = self.alerts[active_id]
            alert.last_seen = now
            alert.occurrences += 1
            alert.severity = severity
            alert.message = message
            return

        alert_id = str(uuid.uuid4())

        alert = Alert(
            alert_id=alert_id,
            service=service,
            severity=severity,
            state=AlertState.FIRING,
            message=message,
            first_seen=now,
            last_seen=now
        )

        self.alerts[alert_id] = alert
        self.active_by_service[service] = alert_id

        logger.warning(
            "ALERT %s: %s - %s",
            severity.value,
            service,
            message
        )

    def resolve(self, alert_id: str):
        alert = self.alerts.get(alert_id)

        if alert is None:
            raise KeyError("Alert does not exist")

        if alert.state == AlertState.RESOLVED:
            return

        alert.state = AlertState.RESOLVED
        alert.resolved_at = datetime.now(timezone.utc).isoformat()

        self.active_by_service.pop(alert.service, None)

        logger.info("Alert resolved: %s", alert.service)

    def active_alerts(self) -> list[Alert]:
        return [
            alert
            for alert in self.alerts.values()
            if alert.state == AlertState.FIRING
        ]


# ============================================================
# DASHBOARD
# ============================================================

class MonitoringDashboard:

    def __init__(
        self,
        monitors: dict[str, ServiceMonitor],
        alert_manager: AlertManager
    ):
        self.monitors = monitors
        self.alert_manager = alert_manager

    def generate(self) -> dict:
        services = {
            name: monitor.metrics()
            for name, monitor in self.monitors.items()
        }

        statuses = [monitor.status for monitor in self.monitors.values()]

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_services": len(services),
            "healthy_services": statuses.count(HealthStatus.HEALTHY),
            "degraded_services": statuses.count(HealthStatus.DEGRADED),
            "unhealthy_services": statuses.count(HealthStatus.UNHEALTHY),
            "unknown_services": statuses.count(HealthStatus.UNKNOWN),
            "active_alert_count": len(
                self.alert_manager.active_alerts()
            ),
            "services": services,
            "active_alerts": [
                asdict(alert)
                for alert in self.alert_manager.active_alerts()
            ]
        }

    def display(self):
        print(json.dumps(self.generate(), indent=4))


# ============================================================
# MONITORING ENGINE
# ============================================================

class MonitoringEngine:

    def __init__(self):
        self.monitors: dict[str, ServiceMonitor] = {}
        self.alert_manager = AlertManager()

    def register_service(self, monitor: ServiceMonitor):
        name = monitor.config.name

        if name in self.monitors:
            raise ValueError(f"Duplicate service: {name}")

        self.monitors[name] = monitor

    def run_cycle(self):
        for name, monitor in self.monitors.items():
            try:
                monitor.evaluate()
                self.alert_manager.process(monitor)

            except Exception:
                logger.exception("Monitoring cycle failed for %s", name)

    def dashboard(self) -> MonitoringDashboard:
        return MonitoringDashboard(
            self.monitors,
            self.alert_manager
        )


# ============================================================
# TESTS AND EXECUTABLE SCENARIO
# ============================================================

def run_tests():
    config = ServiceConfig(
        name="test-service",
        failure_threshold=2,
        recovery_threshold=2
    )

    monitor = ServiceMonitor(config)

    monitor.register_check(
        ApplicationCheck("test-service")
    )

    monitor.register_check(
        DatabaseCheck("test-service", available=False)
    )

    monitor.evaluate()
    assert monitor.status == HealthStatus.DEGRADED

    monitor.evaluate()
    assert monitor.status == HealthStatus.UNHEALTHY

    alerts = AlertManager()
    alerts.process(monitor)

    assert len(alerts.active_alerts()) == 1

    monitor.checks[1].available = True

    monitor.evaluate()
    assert monitor.status == HealthStatus.UNHEALTHY

    monitor.evaluate()
    assert monitor.status == HealthStatus.HEALTHY

    alerts.process(monitor)
    assert len(alerts.active_alerts()) == 0

    try:
        ServiceConfig(
            name="invalid",
            warning_latency_ms=1000,
            critical_latency_ms=500
        )
        raise AssertionError("Invalid thresholds were accepted")
    except ValueError:
        pass

    print("All monitoring tests passed.")


def main():
    run_tests()

    engine = MonitoringEngine()

    application = ServiceMonitor(
        ServiceConfig(
            name="payment-api",
            warning_latency_ms=300,
            critical_latency_ms=1000,
            failure_threshold=2,
            recovery_threshold=2
        )
    )

    application.register_check(
        ApplicationCheck("payment-api")
    )

    application.register_check(
        DatabaseCheck("payment-api", available=True)
    )

    application.register_check(
        MemoryCheck("payment-api", usage_percent=72)
    )

    application.register_check(
        DependencyCheck("payment-api", dependency_available=True)
    )

    engine.register_service(application)

    database_service = ServiceMonitor(
        ServiceConfig(name="database-service")
    )

    database_service.register_check(
        DatabaseCheck("database-service", available=False)
    )

    engine.register_service(database_service)

    print("\nExecuting monitoring cycles...")

    for cycle in range(3):
        print(f"\nMonitoring cycle {cycle + 1}")

        engine.run_cycle()
        engine.dashboard().display()

        # Simulate database recovery.
        if cycle == 1:
            database_service.checks[0].available = True


if __name__ == "__main__":
    main()
