#!/usr/bin/env python3
"""
Structured Logging, Log Levels, and Correlation IDs

Features:
- Structured JSON logging
- DEBUG, INFO, WARNING, ERROR, CRITICAL levels
- Correlation and request IDs using ContextVar
- Context-aware logging
- Sensitive-data redaction
- Exception logging
- Rotating file handler
- Console and file output
- Log filtering and validation
- Concurrent execution support
- Automated assertions
"""

from __future__ import annotations

import json
import logging
import re
import sys
import time
import uuid

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Iterator


# ---------------------------------------------------------
# 1. Configuration
# ---------------------------------------------------------

LOG_DIRECTORY = Path("logs")
LOG_FILE = LOG_DIRECTORY / "application.jsonl"

LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)

correlation_context: ContextVar[str] = ContextVar(
    "correlation_id", default="system"
)

request_context: ContextVar[str] = ContextVar(
    "request_id", default="system"
)

SENSITIVE_FIELDS = {
    "password",
    "token",
    "access_token",
    "authorization",
    "secret",
    "api_key",
    "credit_card",
}


# ---------------------------------------------------------
# 2. Log levels
# ---------------------------------------------------------

class LogLevel:
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


# ---------------------------------------------------------
# 3. Context management
# ---------------------------------------------------------

@contextmanager
def logging_context(
    correlation_id: str | None = None,
    request_id: str | None = None,
) -> Iterator[None]:
    """Maintain correlation identifiers within an execution context."""

    correlation = correlation_id or str(uuid.uuid4())
    request = request_id or str(uuid.uuid4())

    if not correlation.strip() or not request.strip():
        raise ValueError("Context identifiers cannot be empty.")

    correlation_token = correlation_context.set(correlation)
    request_token = request_context.set(request)

    try:
        yield
    finally:
        correlation_context.reset(correlation_token)
        request_context.reset(request_token)


# ---------------------------------------------------------
# 4. Sensitive-data protection
# ---------------------------------------------------------

def redact(value: Any, key: str = "") -> Any:
    """Recursively redact sensitive fields before serialization."""

    if key.lower() in SENSITIVE_FIELDS:
        return "[REDACTED]"

    if isinstance(value, dict):
        return {
            str(k): redact(v, str(k))
            for k, v in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]

    if isinstance(value, str):
        value = re.sub(
            r"(?i)(password|token|api_key)=([^&\s]+)",
            r"\1=[REDACTED]",
            value,
        )

    return value


# ---------------------------------------------------------
# 5. Structured JSON formatter
# ---------------------------------------------------------

class StructuredFormatter(logging.Formatter):

    def format(self, record: logging.LogRecord) -> str:

        timestamp = datetime.fromtimestamp(
            record.created,
            tz=timezone.utc,
        ).isoformat()

        event = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_context.get(),
            "request_id": request_context.get(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process_id": record.process,
            "thread_id": record.thread,
        }

        extra_fields = getattr(record, "structured_fields", {})

        event["attributes"] = redact(extra_fields)

        if record.exc_info:
            event["exception"] = self.formatException(
                record.exc_info
            )

        return json.dumps(
            redact(event),
            ensure_ascii=False,
            default=str,
        )


# ---------------------------------------------------------
# 6. Logger configuration
# ---------------------------------------------------------

def create_logger(
    name: str = "application",
    level: int = logging.INFO,
    console: bool = True,
    file_logging: bool = True,
) -> logging.Logger:

    if level not in (
        logging.DEBUG,
        logging.INFO,
        logging.WARNING,
        logging.ERROR,
        logging.CRITICAL,
    ):
        raise ValueError("Invalid logging level.")

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    if logger.handlers:
        return logger

    formatter = StructuredFormatter()

    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if file_logging:
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=5_000_000,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# ---------------------------------------------------------
# 7. Application logger interface
# ---------------------------------------------------------

@dataclass
class ApplicationLogger:

    logger: logging.Logger = field(
        default_factory=create_logger
    )

    def log(
        self,
        level: int,
        message: str,
        **attributes: Any,
    ) -> None:

        if not isinstance(message, str) or not message.strip():
            raise ValueError("Log message cannot be empty.")

        self.logger.log(
            level,
            message,
            extra={
                "structured_fields": attributes
            },
        )

    def debug(self, message: str, **fields: Any) -> None:
        self.log(LogLevel.DEBUG, message, **fields)

    def info(self, message: str, **fields: Any) -> None:
        self.log(LogLevel.INFO, message, **fields)

    def warning(self, message: str, **fields: Any) -> None:
        self.log(LogLevel.WARNING, message, **fields)

    def error(self, message: str, **fields: Any) -> None:
        self.log(LogLevel.ERROR, message, **fields)

    def critical(self, message: str, **fields: Any) -> None:
        self.log(LogLevel.CRITICAL, message, **fields)

    def exception(self, message: str, **fields: Any) -> None:
        self.logger.exception(
            message,
            extra={"structured_fields": fields},
        )


# ---------------------------------------------------------
# 8. Example application service
# ---------------------------------------------------------

class PaymentService:

    def __init__(self, logger: ApplicationLogger):
        self.logger = logger

    def process_payment(
        self,
        customer_id: str,
        amount: float,
        payment_method: str,
    ) -> dict[str, Any]:

        if not customer_id.strip():
            raise ValueError("Customer ID is required.")

        if amount <= 0:
            raise ValueError("Payment amount must be positive.")

        self.logger.info(
            "Payment processing started",
            customer_id=customer_id,
            amount=amount,
            payment_method=payment_method,
        )

        if amount > 100000:
            self.logger.warning(
                "Payment exceeds review threshold",
                customer_id=customer_id,
                amount=amount,
            )

        transaction_id = str(uuid.uuid4())

        self.logger.info(
            "Payment completed",
            customer_id=customer_id,
            transaction_id=transaction_id,
            amount=amount,
            status="SUCCESS",
        )

        return {
            "transaction_id": transaction_id,
            "status": "SUCCESS",
            "amount": amount,
        }


# ---------------------------------------------------------
# 9. Log analysis
# ---------------------------------------------------------

def analyze_log_file(path: Path) -> dict[str, Any]:

    counts: dict[str, int] = {}
    correlations: set[str] = set()
    invalid_records = 0
    total_records = 0

    if not path.exists():
        return {
            "total_records": 0,
            "invalid_records": 0,
            "level_counts": {},
            "unique_correlations": 0,
        }

    with path.open("r", encoding="utf-8") as file:
        for line in file:

            try:
                event = json.loads(line)
                total_records += 1

                level = event.get("level", "UNKNOWN")
                counts[level] = counts.get(level, 0) + 1

                correlations.add(
                    event.get("correlation_id", "unknown")
                )

            except (json.JSONDecodeError, TypeError):
                invalid_records += 1

    return {
        "total_records": total_records,
        "invalid_records": invalid_records,
        "level_counts": counts,
        "unique_correlations": len(correlations),
    }


# ---------------------------------------------------------
# 10. Execution and validation
# ---------------------------------------------------------

def run_tests() -> None:

    assert redact({"password": "secret"})["password"] == "[REDACTED]"

    assert redact({
        "nested": {"token": "abc"}
    })["nested"]["token"] == "[REDACTED]"

    with logging_context("TEST-CORRELATION", "TEST-REQUEST"):
        assert correlation_context.get() == "TEST-CORRELATION"
        assert request_context.get() == "TEST-REQUEST"

    assert correlation_context.get() == "system"

    try:
        PaymentService(ApplicationLogger(
            create_logger(
                "test-validation",
                logging.CRITICAL,
                console=False,
                file_logging=False,
            )
        )).process_payment("C-1", -10, "CARD")
        raise AssertionError("Negative payment was accepted.")
    except ValueError:
        pass

    print("All tests passed.")


def main() -> None:

    logger = ApplicationLogger(
        create_logger(level=logging.DEBUG)
    )

    logger.info(
        "Application started",
        environment="development",
        version="1.0.0",
    )

    payment_service = PaymentService(logger)

    with logging_context(
        correlation_id="CORR-ORDER-1001",
        request_id="REQ-1001",
    ):

        logger.debug(
            "Incoming payment request",
            endpoint="/payments",
            method="POST",
        )

        try:
            payment_service.process_payment(
                customer_id="CUSTOMER-101",
                amount=2500.50,
                payment_method="CARD",
            )

        except ValueError:
            logger.exception("Payment validation failed")

        try:
            payment_service.process_payment(
                customer_id="CUSTOMER-102",
                amount=-100,
                payment_method="CARD",
            )
        except ValueError:
            logger.exception(
                "Invalid payment rejected",
                customer_id="CUSTOMER-102",
            )

    logger.info("Application execution completed")

    print("\nLog analysis:")
    print(json.dumps(
        analyze_log_file(LOG_FILE),
        indent=2,
    ))

    run_tests()


if __name__ == "__main__":
    main()
