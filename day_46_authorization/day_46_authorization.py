#!/usr/bin/env python3
"""Authorization, role-based access control, permissions, and access control.

A self-contained repository administration service demonstrating permission
checks, role inheritance, resource ownership, separation of duties, temporary
grants, explicit denials, audit logging, and policy testing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Iterable
import json
import unittest


class Effect(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


class DecisionReason(str, Enum):
    ALLOWED = "permission_granted"
    USER_INACTIVE = "user_inactive"
    RESOURCE_MISSING = "resource_missing"
    EXPLICIT_DENY = "explicit_deny"
    NO_PERMISSION = "no_matching_permission"
    OWNERSHIP_REQUIRED = "ownership_required"
    ENVIRONMENT_REJECTED = "environment_rejected"
    GRANT_EXPIRED = "grant_expired"
    INVALID_CONTEXT = "invalid_context"


@dataclass(frozen=True)
class Permission:
    resource_type: str
    action: str

    def __post_init__(self) -> None:
        if not self.resource_type.strip() or not self.action.strip():
            raise ValueError("Permission resource and action are required.")

    def matches(self, resource_type: str, action: str) -> bool:
        resource_match = self.resource_type in ("*", resource_type)
        action_match = self.action in ("*", action)
        return resource_match and action_match


@dataclass(frozen=True)
class Role:
    name: str
    permissions: frozenset[Permission]
    inherits: frozenset[str] = frozenset()


@dataclass
class User:
    user_id: str
    roles: set[str] = field(default_factory=set)
    active: bool = True
    attributes: dict[str, str] = field(default_factory=dict)


@dataclass
class Resource:
    resource_id: str
    resource_type: str
    owner_id: str
    attributes: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class AccessGrant:
    user_id: str
    permission: Permission
    expires_at: datetime
    reason: str


@dataclass(frozen=True)
class PolicyRule:
    name: str
    effect: Effect
    permission: Permission
    require_owner: bool = False
    required_attributes: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class AccessContext:
    source_ip: str
    mfa_verified: bool
    request_id: str
    now: datetime


@dataclass(frozen=True)
class AccessDecision:
    allowed: bool
    reason: DecisionReason
    matched_policy: str | None = None


@dataclass(frozen=True)
class AuditEvent:
    timestamp: str
    request_id: str
    user_id: str
    resource_id: str
    action: str
    allowed: bool
    reason: str
    matched_policy: str | None


class AuthorizationError(Exception):
    """Raised when an operation requires authorization and access is denied."""


class AuthorizationService:
    """Evaluate authorization independently of application business logic."""

    def __init__(self) -> None:
        self.users: dict[str, User] = {}
        self.resources: dict[str, Resource] = {}
        self.roles: dict[str, Role] = {}
        self.grants: list[AccessGrant] = []
        self.rules: list[PolicyRule] = []
        self.audit_log: list[AuditEvent] = []

    def add_role(self, role: Role) -> None:
        if role.name in self.roles:
            raise ValueError(f"Role already exists: {role.name}")
        self.roles[role.name] = role
        try:
            self._validate_role_graph()
        except ValueError:
            del self.roles[role.name]
            raise

    def _validate_role_graph(self) -> None:
        for role in self.roles.values():
            unknown = role.inherits - self.roles.keys()
            if unknown:
                raise ValueError(
                    f"Role {role.name} inherits unknown roles: {sorted(unknown)}"
                )

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(name: str) -> None:
            if name in visiting:
                raise ValueError(f"Role inheritance cycle detected at {name}")
            if name in visited:
                return
            visiting.add(name)
            for parent in self.roles[name].inherits:
                visit(parent)
            visiting.remove(name)
            visited.add(name)

        for name in self.roles:
            visit(name)

    def add_user(self, user: User) -> None:
        if not user.user_id or user.user_id in self.users:
            raise ValueError("User ID must be nonempty and unique.")
        if not user.roles.issubset(self.roles.keys()):
            raise ValueError("User references an undefined role.")
        self.users[user.user_id] = user

    def add_resource(self, resource: Resource) -> None:
        if not resource.resource_id or resource.resource_id in self.resources:
            raise ValueError("Resource ID must be nonempty and unique.")
        if resource.owner_id not in self.users:
            raise ValueError("Resource owner must exist.")
        self.resources[resource.resource_id] = resource

    def add_rule(self, rule: PolicyRule) -> None:
        if not rule.name.strip():
            raise ValueError("Policy rule requires a name.")
        self.rules.append(rule)

    def add_temporary_grant(self, grant: AccessGrant) -> None:
        if grant.user_id not in self.users:
            raise ValueError("Temporary grant references an unknown user.")
        if grant.expires_at.tzinfo is None:
            raise ValueError("Grant expiry must be timezone-aware.")
        if not grant.reason.strip():
            raise ValueError("Temporary grants require an audit reason.")
        self.grants.append(grant)

    def effective_permissions(self, user: User) -> set[Permission]:
        """Resolve inherited permissions without repeating inherited roles."""
        effective: set[Permission] = set()
        visited: set[str] = set()

        def collect(role_name: str) -> None:
            if role_name in visited:
                return
            visited.add(role_name)
            role = self.roles[role_name]
            effective.update(role.permissions)
            for parent in role.inherits:
                collect(parent)

        for role_name in user.roles:
            collect(role_name)
        return effective

    @staticmethod
    def _valid_request(context: AccessContext) -> bool:
        return (
            bool(context.request_id.strip())
            and bool(context.source_ip.strip())
            and context.now.tzinfo is not None
        )

    def authorize(
        self,
        user_id: str,
        resource_id: str,
        action: str,
        context: AccessContext,
    ) -> AccessDecision:
        user = self.users.get(user_id)
        resource = self.resources.get(resource_id)

        if not self._valid_request(context):
            decision = AccessDecision(False, DecisionReason.INVALID_CONTEXT)
        elif user is None or not user.active:
            decision = AccessDecision(False, DecisionReason.USER_INACTIVE)
        elif resource is None:
            decision = AccessDecision(False, DecisionReason.RESOURCE_MISSING)
        else:
            decision = self._evaluate(user, resource, action, context)

        self.audit_log.append(
            AuditEvent(
                timestamp=context.now.isoformat(),
                request_id=context.request_id,
                user_id=user_id,
                resource_id=resource_id,
                action=action,
                allowed=decision.allowed,
                reason=decision.reason.value,
                matched_policy=decision.matched_policy,
            )
        )
        return decision

    def _evaluate(
        self,
        user: User,
        resource: Resource,
        action: str,
        context: AccessContext,
    ) -> AccessDecision:
        permissions = self.effective_permissions(user)

        active_grants = [
            grant
            for grant in self.grants
            if grant.user_id == user.user_id
            and context.now < grant.expires_at
            and grant.permission.matches(resource.resource_type, action)
        ]
        permissions.update(grant.permission for grant in active_grants)

        # A matching explicit deny takes precedence over every allow.
        for rule in self.rules:
            if (
                rule.effect == Effect.DENY
                and rule.permission.matches(resource.resource_type, action)
                and self._conditions_match(rule, user, resource, context)
            ):
                return AccessDecision(
                    False, DecisionReason.EXPLICIT_DENY, rule.name
                )

        for rule in self.rules:
            if (
                rule.effect == Effect.ALLOW
                and rule.permission.matches(resource.resource_type, action)
                and self._conditions_match(rule, user, resource, context)
            ):
                return AccessDecision(True, DecisionReason.ALLOWED, rule.name)

        matching_permissions = [
            permission
            for permission in permissions
            if permission.matches(resource.resource_type, action)
        ]

        if not matching_permissions:
            return AccessDecision(False, DecisionReason.NO_PERMISSION)

        # A global permission does not automatically override resource policy.
        owner_required = any(
            rule.require_owner
            for rule in self.rules
            if rule.effect == Effect.ALLOW
            and rule.permission.matches(resource.resource_type, action)
        )
        if owner_required and resource.owner_id != user.user_id:
            return AccessDecision(False, DecisionReason.OWNERSHIP_REQUIRED)

        # Sensitive production actions require MFA and a trusted network.
        if (
            resource.attributes.get("environment") == "production"
            and action in {"deploy", "delete"}
            and (
                not context.mfa_verified
                or not context.source_ip.startswith("10.")
            )
        ):
            return AccessDecision(False, DecisionReason.ENVIRONMENT_REJECTED)

        return AccessDecision(True, DecisionReason.ALLOWED)

    @staticmethod
    def _conditions_match(
        rule: PolicyRule,
        user: User,
        resource: Resource,
        context: AccessContext,
    ) -> bool:
        for key, expected in rule.required_attributes:
            if key == "user.department":
                actual = user.attributes.get("department")
            elif key.startswith("resource."):
                actual = resource.attributes.get(key.removeprefix("resource."))
            elif key == "context.mfa":
                actual = str(context.mfa_verified).lower()
            else:
                return False
            if actual != expected:
                return False
        return True

    def require_access(
        self,
        user_id: str,
        resource_id: str,
        action: str,
        context: AccessContext,
    ) -> Resource:
        decision = self.authorize(user_id, resource_id, action, context)
        if not decision.allowed:
            raise AuthorizationError(
                f"Access denied: {decision.reason.value}"
            )
        return self.resources[resource_id]


def build_example_service() -> AuthorizationService:
    service = AuthorizationService()

    service.add_role(
        Role(
            "reader",
            frozenset(
                {
                    Permission("repository", "read"),
                    Permission("pull_request", "read"),
                }
            ),
        )
    )
    service.add_role(
        Role(
            "developer",
            frozenset(
                {
                    Permission("repository", "write"),
                    Permission("pull_request", "create"),
                }
            ),
            inherits=frozenset({"reader"}),
        )
    )
    service.add_role(
        Role(
            "reviewer",
            frozenset(
                {
                    Permission("pull_request", "review"),
                    Permission("pull_request", "approve"),
                }
            ),
            inherits=frozenset({"reader"}),
        )
    )
    service.add_role(
        Role(
            "release_manager",
            frozenset(
                {
                    Permission("repository", "deploy"),
                    Permission("repository", "delete"),
                }
            ),
        )
    )

    service.add_user(
        User("alice", {"developer"}, attributes={"department": "engineering"})
    )
    service.add_user(
        User("bob", {"reviewer"}, attributes={"department": "security"})
    )
    service.add_user(
        User("carol", {"release_manager"}, attributes={"department": "platform"})
    )
    service.add_user(User("dave", {"reader"}, active=False))

    service.add_resource(
        Resource(
            "repo-payments",
            "repository",
            "alice",
            {"environment": "production", "classification": "confidential"},
        )
    )
    service.add_resource(
        Resource(
            "pr-842",
            "pull_request",
            "alice",
            {"environment": "development", "repository": "repo-payments"},
        )
    )

    service.add_rule(
        PolicyRule(
            "deny-cross-department-production-delete",
            Effect.DENY,
            Permission("repository", "delete"),
            required_attributes=(
                ("user.department", "platform"),
                ("resource.environment", "production"),
            ),
        )
    )
    return service


def run_demonstration() -> None:
    service = build_example_service()
    now = datetime.now(timezone.utc)

    scenarios = [
        ("alice", "repo-payments", "read", "10.2.1.4", True),
        ("alice", "pr-842", "create", "10.2.1.4", True),
        ("alice", "repo-payments", "delete", "10.2.1.4", True),
        ("bob", "pr-842", "approve", "10.2.1.8", True),
        ("carol", "repo-payments", "deploy", "10.2.1.9", True),
        ("carol", "repo-payments", "deploy", "203.0.113.7", True),
        ("dave", "repo-payments", "read", "10.2.1.4", True),
        ("alice", "missing-repo", "read", "10.2.1.4", True),
    ]

    print("Repository authorization decisions")
    for index, (user, resource, action, ip, mfa) in enumerate(scenarios, 1):
        context = AccessContext(
            source_ip=ip,
            mfa_verified=mfa,
            request_id=f"req-{index:03d}",
            now=now,
        )
        decision = service.authorize(user, resource, action, context)
        print(
            f"{context.request_id}: {user} {action} {resource} -> "
            f"{'ALLOW' if decision.allowed else 'DENY'} "
            f"({decision.reason.value})"
        )

    # Temporary grants expire automatically according to the supplied clock.
    service.add_temporary_grant(
        AccessGrant(
            "alice",
            Permission("repository", "deploy"),
            now + timedelta(minutes=15),
            "Approved emergency release window",
        )
    )
    before_expiry = AccessContext("10.2.1.4", True, "grant-before", now)
    after_expiry = AccessContext(
        "10.2.1.4", True, "grant-after", now + timedelta(minutes=16)
    )
    print(
        "Temporary grant before expiry:",
        service.authorize(
            "alice", "repo-payments", "deploy", before_expiry
        ).allowed,
    )
    print(
        "Temporary grant after expiry:",
        service.authorize(
            "alice", "repo-payments", "deploy", after_expiry
        ).allowed,
    )

    print("\nAudit sample")
    print(json.dumps(service.audit_log[-2].__dict__, indent=2))


class AuthorizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = build_example_service()
        self.now = datetime(2026, 10, 16, 12, tzinfo=timezone.utc)

    def context(self, request_id: str = "test") -> AccessContext:
        return AccessContext("10.1.1.1", True, request_id, self.now)

    def test_inherited_permission(self) -> None:
        result = self.service.authorize(
            "alice", "repo-payments", "read", self.context()
        )
        self.assertTrue(result.allowed)

    def test_default_deny(self) -> None:
        result = self.service.authorize(
            "bob", "repo-payments", "write", self.context()
        )
        self.assertFalse(result.allowed)

    def test_inactive_user_denied(self) -> None:
        result = self.service.authorize(
            "dave", "repo-payments", "read", self.context()
        )
        self.assertEqual(result.reason, DecisionReason.USER_INACTIVE)

    def test_sensitive_operation_requires_trusted_network(self) -> None:
        context = AccessContext(
            "203.0.113.4", True, "external-deploy", self.now
        )
        result = self.service.authorize(
            "carol", "repo-payments", "deploy", context
        )
        self.assertEqual(
            result.reason, DecisionReason.ENVIRONMENT_REJECTED
        )

    def test_explicit_deny_precedes_role_permission(self) -> None:
        self.service.add_role(
            Role(
                "security_admin",
                frozenset({Permission("repository", "delete")}),
            )
        )
        self.service.users["carol"].roles.add("security_admin")
        result = self.service.authorize(
            "carol", "repo-payments", "delete", self.context()
        )
        self.assertEqual(result.reason, DecisionReason.EXPLICIT_DENY)

    def test_role_cycle_rejected(self) -> None:
        self.service.add_role(Role("temporary", frozenset()))
        with self.assertRaises(ValueError):
            self.service.add_role(
                Role("cycle", frozenset(), frozenset({"temporary"}))
            )
            # A separate cycle cannot be introduced through an immutable role.
            self.service.roles["temporary"] = Role(
                "temporary", frozenset(), frozenset({"cycle"})
            )
            self.service._validate_role_graph()

    def test_audit_records_denials(self) -> None:
        before = len(self.service.audit_log)
        self.service.authorize(
            "bob", "repo-payments", "write", self.context("audit-test")
        )
        self.assertEqual(len(self.service.audit_log), before + 1)
        self.assertFalse(self.service.audit_log[-1].allowed)


if __name__ == "__main__":
    run_demonstration()
    print("\nAuthorization policy tests")
    unittest.main(argv=["authorization_demo.py"], exit=False)
