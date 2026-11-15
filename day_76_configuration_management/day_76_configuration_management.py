#!/usr/bin/env python3
"""
Configuration Management System
Environment Variables, Secrets, Configuration Validation and Deployment.

Python 3.10+
Standard-library implementation.
"""

from __future__ import annotations

import json
import os
import re
import hashlib
import hmac
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger("configuration")


class ConfigurationError(Exception):
    pass


class SecretAccessError(ConfigurationError):
    pass


class Environment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class ConfigType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    FLOAT = "float"


@dataclass(frozen=True)
class ConfigDefinition:
    name: str
    config_type: ConfigType
    default: Any = None
    required: bool = False
    minimum: float | None = None
    maximum: float | None = None
    choices: tuple = ()
    sensitive: bool = False

    def __post_init__(self):
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", self.name):
            raise ConfigurationError(
                f"Invalid configuration name: {self.name}"
            )

        if self.minimum is not None and self.maximum is not None:
            if self.minimum > self.maximum:
                raise ConfigurationError(
                    f"Invalid range for {self.name}"
                )


@dataclass
class AuditEvent:
    action: str
    key: str
    environment: str
    actor: str
    success: bool
    detail: str


class ConfigurationSchema:
    def __init__(self):
        self.definitions: dict[str, ConfigDefinition] = {}

    def register(self, definition: ConfigDefinition):
        if definition.name in self.definitions:
            raise ConfigurationError(
                f"Duplicate configuration: {definition.name}"
            )

        self.definitions[definition.name] = definition

    def validate_value(self, name: str, value: Any) -> Any:
        definition = self.definitions.get(name)

        if definition is None:
            raise ConfigurationError(
                f"Unknown configuration: {name}"
            )

        if value is None:
            if definition.required:
                raise ConfigurationError(
                    f"{name} is required"
                )
            return None

        try:
            if definition.config_type == ConfigType.STRING:
                if not isinstance(value, str):
                    raise ValueError("Expected string")
                result = value

            elif definition.config_type == ConfigType.INTEGER:
                if isinstance(value, bool):
                    raise ValueError("Boolean is not an integer setting")
                result = int(value)

            elif definition.config_type == ConfigType.FLOAT:
                if isinstance(value, bool):
                    raise ValueError("Boolean is not a numeric setting")
                result = float(value)

            elif definition.config_type == ConfigType.BOOLEAN:
                if isinstance(value, bool):
                    result = value
                elif isinstance(value, str):
                    normalized = value.lower()
                    if normalized in ("true", "1", "yes"):
                        result = True
                    elif normalized in ("false", "0", "no"):
                        result = False
                    else:
                        raise ValueError("Invalid boolean")
                else:
                    raise ValueError("Expected boolean")

            else:
                raise ValueError("Unsupported configuration type")

        except (ValueError, TypeError) as exc:
            raise ConfigurationError(
                f"Invalid value for {name}: {exc}"
            ) from exc

        if definition.config_type in (
            ConfigType.INTEGER,
            ConfigType.FLOAT
        ):
            if definition.minimum is not None:
                if result < definition.minimum:
                    raise ConfigurationError(
                        f"{name} is below minimum"
                    )

            if definition.maximum is not None:
                if result > definition.maximum:
                    raise ConfigurationError(
                        f"{name} exceeds maximum"
                    )

        if definition.choices and result not in definition.choices:
            raise ConfigurationError(
                f"{name} must be one of {definition.choices}"
            )

        return result


class SecretStore:
    """
    Demonstration-only in-memory secret store.

    Production deployments should use a dedicated secrets manager.
    This class deliberately does not implement custom encryption.
    """

    def __init__(self):
        self._secrets: dict[str, str] = {}

    def put(self, name: str, value: str):
        if not name or not value:
            raise SecretAccessError(
                "Secret name and value are required"
            )

        self._secrets[name] = value

    def get(self, name: str, authorized: bool = False) -> str:
        if not authorized:
            raise SecretAccessError(
                "Secret access denied"
            )

        if name not in self._secrets:
            raise SecretAccessError(
                f"Secret not found: {name}"
            )

        return self._secrets[name]

    def exists(self, name: str) -> bool:
        return name in self._secrets

    def remove(self, name: str):
        self._secrets.pop(name, None)

    def __repr__(self):
        return f"SecretStore(secrets={len(self._secrets)})"


class ConfigurationManager:
    def __init__(
        self,
        schema: ConfigurationSchema,
        environment: Environment,
        secret_store: SecretStore
    ):
        self.schema = schema
        self.environment = environment
        self.secret_store = secret_store
        self._values: dict[str, Any] = {}
        self._version = 0
        self.audit_log: list[AuditEvent] = []

    def _audit(
        self,
        action: str,
        key: str,
        actor: str,
        success: bool,
        detail: str
    ):
        self.audit_log.append(
            AuditEvent(
                action=action,
                key=key,
                environment=self.environment.value,
                actor=actor,
                success=success,
                detail=detail
            )
        )

    def load_defaults(self):
        for name, definition in self.schema.definitions.items():
            if definition.default is not None:
                self._values[name] = (
                    self.schema.validate_value(
                        name,
                        definition.default
                    )
                )

    def set(
        self,
        name: str,
        value: Any,
        actor: str = "system"
    ):
        try:
            definition = self.schema.definitions.get(name)

            if definition is None:
                raise ConfigurationError(
                    f"Unknown setting: {name}"
                )

            if definition.sensitive:
                raise SecretAccessError(
                    f"{name} must be managed through SecretStore"
                )

            validated = self.schema.validate_value(name, value)
            self._values[name] = validated
            self._version += 1

            self._audit(
                "SET", name, actor, True,
                "Configuration updated"
            )

        except ConfigurationError as exc:
            self._audit(
                "SET", name, actor, False, str(exc)
            )
            raise

    def get(self, name: str) -> Any:
        definition = self.schema.definitions.get(name)

        if definition is None:
            raise ConfigurationError(
                f"Unknown setting: {name}"
            )

        if definition.sensitive:
            raise SecretAccessError(
                "Sensitive settings cannot be retrieved as plain configuration"
            )

        if name not in self._values:
            raise ConfigurationError(
                f"Configuration not loaded: {name}"
            )

        return self._values[name]

    def get_secret(self, name: str, authorized: bool = False):
        definition = self.schema.definitions.get(name)

        if definition is None or not definition.sensitive:
            raise ConfigurationError(
                "The requested setting is not a registered secret"
            )

        return self.secret_store.get(name, authorized)

    def load_environment(self, environ: dict[str, str] | None = None):
        source = os.environ if environ is None else environ

        for name, definition in self.schema.definitions.items():
            if definition.sensitive:
                continue

            if name in source:
                self.set(
                    name,
                    source[name],
                    actor="environment-loader"
                )

    def validate_complete(self):
        errors = []

        for name, definition in self.schema.definitions.items():
            if definition.sensitive:
                if definition.required:
                    if not self.secret_store.exists(name):
                        errors.append(
                            f"Required secret missing: {name}"
                        )
                continue

            if name not in self._values and definition.required:
                errors.append(
                    f"Required configuration missing: {name}"
                )

        if errors:
            raise ConfigurationError(
                "; ".join(errors)
            )

        return True

    def snapshot(self, include_sensitive=False):
        result = {}

        for name, definition in self.schema.definitions.items():
            if definition.sensitive:
                result[name] = (
                    "[REDACTED]"
                    if include_sensitive
                    else "[SECRET]"
                )
            else:
                result[name] = self._values.get(name)

        return {
            "environment": self.environment.value,
            "version": self._version,
            "configuration": result
        }

    def export_json(self, path: str | Path):
        """
        Exports non-secret configuration only.
        Atomic replacement avoids partially written files.
        """
        destination = Path(path)
        destination.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        payload = self.snapshot()

        temporary = destination.with_suffix(
            destination.suffix + ".tmp"
        )

        try:
            temporary.write_text(
                json.dumps(payload, indent=2),
                encoding="utf-8"
            )
            temporary.replace(destination)

        except OSError:
            temporary.unlink(missing_ok=True)
            raise

    @property
    def version(self):
        return self._version


class ConfigurationTransaction:
    """
    Applies multiple configuration changes atomically
    from the perspective of this in-memory manager.
    """

    def __init__(self, manager: ConfigurationManager):
        self.manager = manager
        self.pending: dict[str, Any] = {}
        self.committed = False

    def set(self, name: str, value: Any):
        self.pending[name] = value

    def commit(self):
        validated = {}

        for name, value in self.pending.items():
            definition = self.manager.schema.definitions.get(name)

            if definition is None or definition.sensitive:
                raise ConfigurationError(
                    f"Invalid transactional setting: {name}"
                )

            validated[name] = (
                self.manager.schema.validate_value(
                    name,
                    value
                )
            )

        self.manager._values.update(validated)

        if validated:
            self.manager._version += 1

        self.committed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None and not self.committed:
            self.commit()

        return False


def configuration_fingerprint(
    values: dict[str, Any]
) -> str:
    """
    Produces a deterministic fingerprint of non-secret settings.
    Never include secret values in this operation.
    """
    encoded = json.dumps(
        values,
        sort_keys=True,
        separators=(",", ":")
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


def compare_configurations(
    first: dict[str, Any],
    second: dict[str, Any]
) -> dict[str, tuple[Any, Any]]:
    differences = {}

    for key in sorted(set(first) | set(second)):
        old = first.get(key)
        new = second.get(key)

        if old != new:
            differences[key] = (old, new)

    return differences


def main():
    schema = ConfigurationSchema()

    schema.register(
        ConfigDefinition(
            "APP_NAME",
            ConfigType.STRING,
            default="InventoryService",
            required=True
        )
    )

    schema.register(
        ConfigDefinition(
            "APP_PORT",
            ConfigType.INTEGER,
            default=8000,
            minimum=1024,
            maximum=65535
        )
    )

    schema.register(
        ConfigDefinition(
            "DEBUG",
            ConfigType.BOOLEAN,
            default=False
        )
    )

    schema.register(
        ConfigDefinition(
            "DATABASE_POOL_SIZE",
            ConfigType.INTEGER,
            default=10,
            minimum=1,
            maximum=100
        )
    )

    schema.register(
        ConfigDefinition(
            "LOG_LEVEL",
            ConfigType.STRING,
            default="INFO",
            choices=("DEBUG", "INFO", "WARNING", "ERROR")
        )
    )

    schema.register(
        ConfigDefinition(
            "DATABASE_PASSWORD",
            ConfigType.STRING,
            required=True,
            sensitive=True
        )
    )

    secrets = SecretStore()

    manager = ConfigurationManager(
        schema,
        Environment.DEVELOPMENT,
        secrets
    )

    manager.load_defaults()

    secrets.put(
        "DATABASE_PASSWORD",
        "development-only-example-secret"
    )

    manager.load_environment({
        "APP_PORT": "8080",
        "DEBUG": "false",
        "LOG_LEVEL": "INFO"
    })

    manager.validate_complete()

    print("\nCONFIGURATION SNAPSHOT")
    print(json.dumps(manager.snapshot(), indent=2))

    print("\nTRANSACTION")

    with ConfigurationTransaction(manager) as transaction:
        transaction.set("APP_PORT", "8081")
        transaction.set("DATABASE_POOL_SIZE", 20)

    print("Updated port:", manager.get("APP_PORT"))
    print("Pool size:", manager.get("DATABASE_POOL_SIZE"))

    print("\nSECRET ACCESS")

    try:
        manager.get_secret(
            "DATABASE_PASSWORD",
            authorized=False
        )
    except SecretAccessError as exc:
        print("Expected access denial:", exc)

    print(
        "Authorized secret retrieved:",
        bool(
            manager.get_secret(
                "DATABASE_PASSWORD",
                authorized=True
            )
        )
    )

    print("\nCONFIGURATION COMPARISON")

    differences = compare_configurations(
        {"APP_PORT": 8000, "DEBUG": False},
        {"APP_PORT": 8081, "DEBUG": False}
    )

    print(differences)

    print("\nCONFIGURATION FINGERPRINT")

    safe_values = {
        key: value
        for key, value in manager._values.items()
        if not schema.definitions[key].sensitive
    }

    print(configuration_fingerprint(safe_values))

    print("\nINVALID CONFIGURATION")

    try:
        manager.set("APP_PORT", 70000)
    except ConfigurationError as exc:
        print("Validation rejected:", exc)

    print("\nAUDIT LOG")

    for event in manager.audit_log:
        print(
            event.action,
            event.key,
            event.actor,
            event.success,
            event.detail
        )

    print("\nAll configuration demonstrations completed.")


if __name__ == "__main__":
    main()
