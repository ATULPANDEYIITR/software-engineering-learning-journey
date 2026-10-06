"""
Design Patterns I: Factory, Builder, Singleton

A self-contained progression from fundamental object creation to a small
production-oriented notification service demonstrating:

- Factory Pattern: encapsulating selection and creation of related objects.
- Builder Pattern: constructing complex, validated immutable-style objects.
- Singleton Pattern: maintaining one shared application-wide service instance.

The examples intentionally keep the three patterns distinct. Factory decides
WHAT concrete object should be created. Builder controls HOW a complex object
is assembled. Singleton controls HOW MANY instances of a shared service are
allowed within the process.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from typing import Dict, List, Optional, Protocol
import json
import re
import tempfile
from pathlib import Path


# ---------------------------------------------------------------------------
# Factory Pattern
# ---------------------------------------------------------------------------

class NotificationChannel(Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class NotificationSender(Protocol):
    """Common interface implemented by all notification products."""

    def send(self, recipient: str, message: str) -> str:
        ...


class EmailSender:
    def send(self, recipient: str, message: str) -> str:
        if "@" not in recipient:
            raise ValueError("Email recipient must contain '@'.")
        return f"EMAIL -> {recipient}: {message}"


class SmsSender:
    def send(self, recipient: str, message: str) -> str:
        if not re.fullmatch(r"\+?[0-9]{8,15}", recipient):
            raise ValueError("SMS recipient must contain 8-15 digits.")
        return f"SMS -> {recipient}: {message}"


class PushSender:
    def send(self, recipient: str, message: str) -> str:
        if not recipient.strip():
            raise ValueError("Push recipient cannot be empty.")
        return f"PUSH -> device:{recipient}: {message}"


class NotificationFactory:
    """
    Simple Factory.

    The caller supplies a business-level channel rather than directly
    constructing EmailSender, SmsSender, or PushSender.
    """

    _constructors = {
        NotificationChannel.EMAIL: EmailSender,
        NotificationChannel.SMS: SmsSender,
        NotificationChannel.PUSH: PushSender,
    }

    @classmethod
    def create(cls, channel: NotificationChannel) -> NotificationSender:
        try:
            constructor = cls._constructors[channel]
        except KeyError as exc:
            raise ValueError(f"Unsupported notification channel: {channel}") from exc
        return constructor()


def demonstrate_factory() -> None:
    print("\n=== Factory Pattern ===")

    requests = [
        (NotificationChannel.EMAIL, "developer@example.com", "Build completed"),
        (NotificationChannel.SMS, "+919876543210", "Deployment completed"),
        (NotificationChannel.PUSH, "device-7a91", "Review is ready"),
    ]

    for channel, recipient, message in requests:
        sender = NotificationFactory.create(channel)
        print(sender.send(recipient, message))

    try:
        NotificationFactory.create("email")  # type: ignore[arg-type]
    except (ValueError, KeyError):
        print("Factory rejected an unsupported channel.")

    """
    Why this is a Factory:
    Client code does not need to know which concrete class corresponds to a
    channel. Adding construction logic to one place prevents creation rules
    from being scattered throughout application code.
    """


# ---------------------------------------------------------------------------
# Builder Pattern
# ---------------------------------------------------------------------------

class Priority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class Notification:
    """
    Final product.

    frozen=True prevents accidental mutation after construction. The Builder
    performs validation before creating this object.
    """

    title: str
    body: str
    recipient: str
    channel: NotificationChannel
    priority: Priority = Priority.NORMAL
    tags: tuple[str, ...] = ()
    metadata: Dict[str, str] = field(default_factory=dict)
    retry_count: int = 3


class NotificationBuilder:
    """
    Builder for a Notification with several optional fields.

    The constructor contains only required information. Optional properties
    are progressively configured through fluent methods.
    """

    def __init__(
        self,
        title: str,
        body: str,
        recipient: str,
        channel: NotificationChannel,
    ) -> None:
        self._title = title
        self._body = body
        self._recipient = recipient
        self._channel = channel
        self._priority = Priority.NORMAL
        self._tags: List[str] = []
        self._metadata: Dict[str, str] = {}
        self._retry_count = 3

    def priority(self, value: Priority) -> "NotificationBuilder":
        self._priority = value
        return self

    def add_tag(self, value: str) -> "NotificationBuilder":
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Tag cannot be empty.")
        if cleaned not in self._tags:
            self._tags.append(cleaned)
        return self

    def metadata(self, key: str, value: str) -> "NotificationBuilder":
        key = key.strip()
        if not key:
            raise ValueError("Metadata key cannot be empty.")
        self._metadata[key] = value
        return self

    def retry_count(self, value: int) -> "NotificationBuilder":
        if not 0 <= value <= 10:
            raise ValueError("Retry count must be between 0 and 10.")
        self._retry_count = value
        return self

    def build(self) -> Notification:
        if not self._title.strip():
            raise ValueError("Notification title is required.")
        if not self._body.strip():
            raise ValueError("Notification body is required.")
        if not self._recipient.strip():
            raise ValueError("Notification recipient is required.")

        if self._channel == NotificationChannel.EMAIL:
            if "@" not in self._recipient:
                raise ValueError("An email notification requires a valid email recipient.")
        elif self._channel == NotificationChannel.SMS:
            if not re.fullmatch(r"\+?[0-9]{8,15}", self._recipient):
                raise ValueError("An SMS notification requires a valid phone number.")

        return Notification(
            title=self._title.strip(),
            body=self._body.strip(),
            recipient=self._recipient.strip(),
            channel=self._channel,
            priority=self._priority,
            tags=tuple(self._tags),
            metadata=dict(self._metadata),
            retry_count=self._retry_count,
        )


def demonstrate_builder() -> Notification:
    print("\n=== Builder Pattern ===")

    notification = (
        NotificationBuilder(
            title="Production deployment",
            body="Version 4.2.0 is ready for verification.",
            recipient="release@example.com",
            channel=NotificationChannel.EMAIL,
        )
        .priority(Priority.HIGH)
        .add_tag("deployment")
        .add_tag("production")
        .metadata("service", "release-manager")
        .metadata("version", "4.2.0")
        .retry_count(5)
        .build()
    )

    print(json.dumps(
        {
            "title": notification.title,
            "body": notification.body,
            "recipient": notification.recipient,
            "channel": notification.channel.value,
            "priority": notification.priority.value,
            "tags": notification.tags,
            "metadata": notification.metadata,
            "retry_count": notification.retry_count,
        },
        indent=2,
        default=str,
    ))

    try:
        (
            NotificationBuilder(
                title="",
                body="Invalid notification",
                recipient="user@example.com",
                channel=NotificationChannel.EMAIL,
            )
            .build()
        )
    except ValueError as exc:
        print(f"Builder validation: {exc}")

    return notification


# ---------------------------------------------------------------------------
# Singleton Pattern
# ---------------------------------------------------------------------------

class AuditLogger:
    """
    Thread-safe Singleton.

    A Singleton is appropriate here because the application wants one shared
    audit sink and one shared in-memory event history for this process.

    The pattern should not be used merely because global state is convenient.
    Shared mutable state creates coupling, so a Singleton is justified only
    when one process-wide resource genuinely has one logical owner.
    """

    _instance: Optional["AuditLogger"] = None
    _lock = Lock()

    def __new__(cls) -> "AuditLogger":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._events = []
                    cls._instance = instance
        return cls._instance

    def record(self, event: str) -> None:
        self._events.append(event)

    def events(self) -> tuple[str, ...]:
        return tuple(self._events)

    def clear(self) -> None:
        self._events.clear()


def demonstrate_singleton() -> None:
    print("\n=== Singleton Pattern ===")

    logger_a = AuditLogger()
    logger_b = AuditLogger()

    logger_a.record("notification.created")
    logger_b.record("notification.sent")

    print(f"Same object: {logger_a is logger_b}")
    print(f"Shared events: {logger_a.events()}")

    logger_a.clear()
    print(f"Events after shared clear: {logger_b.events()}")


# ---------------------------------------------------------------------------
# Combined application architecture
# ---------------------------------------------------------------------------

class NotificationService:
    """
    Combines the patterns without confusing their responsibilities.

    Builder creates a validated Notification.
    Factory chooses the transport implementation.
    Singleton supplies the process-wide audit logger.
    """

    def __init__(self, audit_logger: Optional[AuditLogger] = None) -> None:
        self._audit_logger = audit_logger or AuditLogger()

    def send(self, notification: Notification) -> str:
        self._audit_logger.record(
            f"notification.dispatch.requested:{notification.channel.value}"
        )

        sender = NotificationFactory.create(notification.channel)

        try:
            result = sender.send(notification.recipient, notification.body)
        except ValueError:
            self._audit_logger.record("notification.dispatch.validation_failed")
            raise

        self._audit_logger.record("notification.dispatch.completed")
        return result


def demonstrate_combined_workflow(notification: Notification) -> None:
    print("\n=== Combined Workflow ===")

    service = NotificationService()
    result = service.send(notification)

    print(result)
    print("Audit trail:")
    for event in service._audit_logger.events():
        print(f"  {event}")


# ---------------------------------------------------------------------------
# File-backed configuration example
# ---------------------------------------------------------------------------

class ConfigurationError(ValueError):
    pass


class ConfigurationLoader:
    """
    Reads a small JSON configuration file and validates values before they
    reach the Builder. File handling demonstrates a realistic boundary where
    malformed external data must not silently become domain objects.
    """

    @staticmethod
    def load(path: Path) -> Notification:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ConfigurationError(f"Configuration file not found: {path}") from exc
        except json.JSONDecodeError as exc:
            raise ConfigurationError("Configuration contains invalid JSON.") from exc

        required = {"title", "body", "recipient", "channel"}
        missing = required - raw.keys()
        if missing:
            raise ConfigurationError(
                f"Missing configuration fields: {sorted(missing)}"
            )

        try:
            channel = NotificationChannel(raw["channel"])
        except ValueError as exc:
            raise ConfigurationError(
                f"Unsupported channel: {raw['channel']}"
            ) from exc

        builder = NotificationBuilder(
            title=str(raw["title"]),
            body=str(raw["body"]),
            recipient=str(raw["recipient"]),
            channel=channel,
        )

        if "priority" in raw:
            try:
                builder.priority(Priority(raw["priority"]))
            except ValueError as exc:
                raise ConfigurationError(
                    f"Unsupported priority: {raw['priority']}"
                ) from exc

        for tag in raw.get("tags", []):
            builder.add_tag(str(tag))

        return builder.build()


def demonstrate_external_configuration() -> None:
    print("\n=== Factory + Builder at an External Data Boundary ===")

    configuration = {
        "title": "Security alert",
        "body": "A privileged deployment was detected.",
        "recipient": "+919876543210",
        "channel": "sms",
        "priority": "critical",
        "tags": ["security", "deployment"],
    }

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "notification.json"
        path.write_text(json.dumps(configuration), encoding="utf-8")

        notification = ConfigurationLoader.load(path)
        print(
            f"Loaded {notification.priority.value} "
            f"{notification.channel.value} notification."
        )


# ---------------------------------------------------------------------------
# Testing the actual pattern boundaries
# ---------------------------------------------------------------------------

def run_invariant_tests() -> None:
    print("\n=== Pattern Invariant Tests ===")

    # Factory invariant: each supported channel produces the correct product.
    assert isinstance(
        NotificationFactory.create(NotificationChannel.EMAIL), EmailSender
    )
    assert isinstance(
        NotificationFactory.create(NotificationChannel.SMS), SmsSender
    )
    assert isinstance(
        NotificationFactory.create(NotificationChannel.PUSH), PushSender
    )

    # Builder invariant: final objects are independent of later builder use.
    builder = NotificationBuilder(
        "Release",
        "Released successfully",
        "team@example.com",
        NotificationChannel.EMAIL,
    )
    first = builder.add_tag("release").build()
    builder.add_tag("second")
    assert first.tags == ("release",)

    # Singleton invariant: repeated access returns the same instance.
    assert AuditLogger() is AuditLogger()

    # Validation invariant: bad recipient cannot enter the domain model.
    try:
        (
            NotificationBuilder(
                "Invalid",
                "Invalid recipient",
                "not-an-email",
                NotificationChannel.EMAIL,
            )
            .build()
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid email was accepted.")

    print("All pattern invariants passed.")


def main() -> None:
    demonstrate_factory()
    notification = demonstrate_builder()
    demonstrate_singleton()
    demonstrate_combined_workflow(notification)
    demonstrate_external_configuration()
    run_invariant_tests()

    print("\n=== Design Boundary ===")
    print("Factory: chooses and creates a concrete product.")
    print("Builder: assembles and validates a complex product.")
    print("Singleton: provides one shared process-wide instance.")


if __name__ == "__main__":
    main()
