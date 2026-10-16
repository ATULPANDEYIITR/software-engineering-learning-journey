"use strict";

/*
 * Event-driven authorization model for a repository hosting service.
 * Demonstrates RBAC, object-level ownership, policy evaluation, expiring
 * grants, immutable audit events, and safe handling of asynchronous requests.
 * Run with Node.js 18 or later.
 */

const { randomUUID } = require("node:crypto");

class AuthorizationError extends Error {
  constructor(message, decision) {
    super(message);
    this.name = "AuthorizationError";
    this.decision = decision;
  }
}

const permission = (resource, action) => `${resource}:${action}`;

function matchesPermission(granted, requested) {
  const [grantedResource, grantedAction] = granted.split(":");
  const [requestedResource, requestedAction] = requested.split(":");

  return (
    (grantedResource === "*" || grantedResource === requestedResource) &&
    (grantedAction === "*" || grantedAction === requestedAction)
  );
}

class PolicyEngine {
  constructor() {
    this.roles = new Map();
    this.users = new Map();
    this.resources = new Map();
    this.temporaryGrants = [];
    this.auditEvents = [];
    this.listeners = new Map();
  }

  on(eventName, listener) {
    if (!this.listeners.has(eventName)) {
      this.listeners.set(eventName, new Set());
    }
    this.listeners.get(eventName).add(listener);

    // Returning an unsubscribe function prevents listeners from accumulating.
    return () => this.listeners.get(eventName)?.delete(listener);
  }

  emit(eventName, payload) {
    for (const listener of this.listeners.get(eventName) ?? []) {
      try {
        listener(payload);
      } catch (error) {
        // Monitoring failures must not change the authorization decision.
        console.error(`Listener failure for ${eventName}: ${error.message}`);
      }
    }
  }

  addRole(name, permissions, inherits = []) {
    if (!name || this.roles.has(name)) {
      throw new Error("Role name must be nonempty and unique.");
    }

    this.roles.set(name, {
      name,
      permissions: new Set(permissions),
      inherits: new Set(inherits),
    });

    try {
      this.validateRoleGraph();
    } catch (error) {
      this.roles.delete(name);
      throw error;
    }
  }

  validateRoleGraph() {
    const visiting = new Set();
    const visited = new Set();

    const visit = (name) => {
      if (!this.roles.has(name)) {
        throw new Error(`Undefined inherited role: ${name}`);
      }
      if (visiting.has(name)) {
        throw new Error(`Role inheritance cycle at ${name}`);
      }
      if (visited.has(name)) return;

      visiting.add(name);
      for (const parent of this.roles.get(name).inherits) {
        visit(parent);
      }
      visiting.delete(name);
      visited.add(name);
    };

    for (const name of this.roles.keys()) visit(name);
  }

  addUser(user) {
    if (!user.id || this.users.has(user.id)) {
      throw new Error("User ID must be nonempty and unique.");
    }
    for (const role of user.roles) {
      if (!this.roles.has(role)) throw new Error(`Unknown role: ${role}`);
    }
    this.users.set(user.id, {
      ...user,
      roles: new Set(user.roles),
      attributes: { ...user.attributes },
    });
  }

  addResource(resource) {
    if (!resource.id || this.resources.has(resource.id)) {
      throw new Error("Resource ID must be nonempty and unique.");
    }
    if (!this.users.has(resource.ownerId)) {
      throw new Error("Resource owner does not exist.");
    }
    this.resources.set(resource.id, {
      ...resource,
      attributes: { ...resource.attributes },
    });
  }

  effectivePermissions(user) {
    const permissions = new Set();
    const visited = new Set();

    const collect = (roleName) => {
      if (visited.has(roleName)) return;
      visited.add(roleName);
      const role = this.roles.get(roleName);
      if (!role) throw new Error(`Unknown role: ${roleName}`);

      role.permissions.forEach((value) => permissions.add(value));
      role.inherits.forEach(collect);
    };

    user.roles.forEach(collect);
    return permissions;
  }

  addTemporaryGrant(grant) {
    if (!this.users.has(grant.userId)) {
      throw new Error("Grant references an unknown user.");
    }
    if (!Number.isFinite(grant.expiresAt)) {
      throw new Error("Grant expiry must be a valid timestamp.");
    }
    if (grant.expiresAt <= Date.now()) {
      throw new Error("A new temporary grant must expire in the future.");
    }
    if (!grant.reason?.trim()) {
      throw new Error("Grant reason is required for auditing.");
    }

    this.temporaryGrants.push(Object.freeze({ ...grant }));
  }

  evaluate({ userId, resourceId, action, context = {} }) {
    const timestamp = context.now ?? Date.now();
    const requestId = context.requestId ?? randomUUID();
    const user = this.users.get(userId);
    const resource = this.resources.get(resourceId);

    let decision;

    if (!Number.isFinite(timestamp) || !context.sourceIp) {
      decision = { allowed: false, reason: "invalid_context" };
    } else if (!user || !user.active) {
      decision = { allowed: false, reason: "inactive_or_unknown_user" };
    } else if (!resource) {
      decision = { allowed: false, reason: "resource_not_found" };
    } else {
      const requested = permission(resource.type, action);
      const effective = this.effectivePermissions(user);

      for (const grant of this.temporaryGrants) {
        if (
          grant.userId === userId &&
          timestamp < grant.expiresAt &&
          matchesPermission(grant.permission, requested)
        ) {
          effective.add(grant.permission);
        }
      }

      const explicitlyDenied =
        resource.attributes.blockedActions?.includes(action) ?? false;

      if (explicitlyDenied) {
        decision = { allowed: false, reason: "explicit_resource_denial" };
      } else if (![...effective].some((p) => matchesPermission(p, requested))) {
        decision = { allowed: false, reason: "no_matching_permission" };
      } else if (
        resource.attributes.ownerOnly?.includes(action) &&
        resource.ownerId !== userId
      ) {
        decision = { allowed: false, reason: "ownership_required" };
      } else if (
        resource.attributes.environment === "production" &&
        ["deploy", "delete"].includes(action) &&
        (!context.mfaVerified || !context.sourceIp.startsWith("10."))
      ) {
        decision = {
          allowed: false,
          reason: "production_security_conditions_failed",
        };
      } else {
        decision = { allowed: true, reason: "permission_granted" };
      }
    }

    const auditEvent = Object.freeze({
      requestId,
      timestamp: new Date(timestamp).toISOString(),
      userId,
      resourceId,
      action,
      allowed: decision.allowed,
      reason: decision.reason,
    });

    this.auditEvents.push(auditEvent);
    this.emit("authorization:decision", auditEvent);
    return decision;
  }

  async execute(request, operation) {
    // Authorization occurs before invoking the protected business operation.
    const decision = this.evaluate(request);
    if (!decision.allowed) {
      throw new AuthorizationError(
        `Operation rejected: ${decision.reason}`,
        decision,
      );
    }

    // The callback runs only after a positive decision.
    const result = await operation();
    this.emit("authorization:operation-completed", {
      requestId: request.context?.requestId,
      resourceId: request.resourceId,
      action: request.action,
    });
    return result;
  }

  auditSummary() {
    const summary = new Map();

    for (const event of this.auditEvents) {
      const key = `${event.action}:${event.allowed ? "allow" : "deny"}`;
      summary.set(key, (summary.get(key) ?? 0) + 1);
    }

    return Object.fromEntries(summary);
  }
}

function buildEngine() {
  const engine = new PolicyEngine();

  engine.addRole("reader", [
    permission("repository", "read"),
    permission("pullRequest", "read"),
  ]);
  engine.addRole(
    "developer",
    [
      permission("repository", "write"),
      permission("pullRequest", "create"),
    ],
    ["reader"],
  );
  engine.addRole(
    "reviewer",
    [
      permission("pullRequest", "review"),
      permission("pullRequest", "approve"),
    ],
    ["reader"],
  );
  engine.addRole("release-manager", [
    permission("repository", "deploy"),
    permission("repository", "delete"),
  ]);

  engine.addUser({
    id: "maya",
    roles: ["developer"],
    active: true,
    attributes: { department: "engineering" },
  });
  engine.addUser({
    id: "noah",
    roles: ["reviewer"],
    active: true,
    attributes: { department: "security" },
  });
  engine.addUser({
    id: "olivia",
    roles: ["release-manager"],
    active: true,
    attributes: { department: "platform" },
  });

  engine.addResource({
    id: "repository-17",
    type: "repository",
    ownerId: "maya",
    attributes: {
      environment: "production",
      classification: "restricted",
      ownerOnly: ["write"],
    },
  });
  engine.addResource({
    id: "pull-request-91",
    type: "pullRequest",
    ownerId: "maya",
    attributes: { environment: "development" },
  });

  return engine;
}

async function main() {
  const engine = buildEngine();
  const unsubscribe = engine.on("authorization:decision", (event) => {
    console.log(
      `[audit] ${event.requestId}: ${event.action} -> ${
        event.allowed ? "ALLOW" : "DENY"
      } (${event.reason})`,
    );
  });

  const now = Date.now();
  const requests = [
    {
      userId: "maya",
      resourceId: "repository-17",
      action: "read",
      context: { sourceIp: "10.1.0.8", mfaVerified: true, now },
    },
    {
      userId: "noah",
      resourceId: "repository-17",
      action: "write",
      context: { sourceIp: "10.1.0.8", mfaVerified: true, now },
    },
    {
      userId: "olivia",
      resourceId: "repository-17",
      action: "deploy",
      context: { sourceIp: "10.1.0.8", mfaVerified: true, now },
    },
    {
      userId: "olivia",
      resourceId: "repository-17",
      action: "deploy",
      context: { sourceIp: "198.51.100.9", mfaVerified: true, now },
    },
  ];

  for (const request of requests) {
    const decision = engine.evaluate({
      ...request,
      context: { ...request.context, requestId: randomUUID() },
    });
    console.log(JSON.stringify({ action: request.action, ...decision }));
  }

  engine.addTemporaryGrant({
    userId: "maya",
    permission: permission("repository", "deploy"),
    expiresAt: now + 60_000,
    reason: "Time-limited emergency release",
  });

  try {
    const result = await engine.execute(
      {
        userId: "maya",
        resourceId: "repository-17",
        action: "deploy",
        context: {
          sourceIp: "10.1.0.8",
          mfaVerified: true,
          requestId: "emergency-release",
          now,
        },
      },
      async () => ({ deployment: "release-2026.10", state: "completed" }),
    );
    console.log("Protected operation:", result);
  } catch (error) {
    if (error instanceof AuthorizationError) {
      console.error(error.message);
    } else {
      throw error;
    }
  }

  console.log("Audit counts:", engine.auditSummary());
  unsubscribe();
}

main().catch((error) => {
  console.error("Authorization demonstration failed:", error.message);
  process.exitCode = 1;
});
