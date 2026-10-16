# Authorization, RBAC, Permissions, and Access Control

## Scope and architectural model

Authorization determines whether an authenticated identity may perform a particular action on a particular resource under the current policy. Authentication establishes identity; authorization evaluates access. A successful login does not automatically grant permission to read a repository, approve a release, change a production configuration, or administer another user's account.

This project models authorization in a repository-hosting environment. Users have organizational attributes and assigned roles. Roles supply permissions, resources carry ownership and environment attributes, and policy rules constrain access. Temporary grants provide narrowly scoped access for exceptional situations. Decisions are recorded in an audit trail.

The implementations distinguish four related mechanisms:

| Mechanism | Responsibility | Example |
|---|---|---|
| Authentication | Establish the identity making a request | A developer signs in using an authenticated account. |
| Permission | Represent an allowed resource-action combination | `repository:write` permits repository modification when no overriding policy prohibits it. |
| Role-based access control (RBAC) | Assign collections of permissions to roles and roles to users | The `developer` role inherits read permissions and adds repository write access. |
| Policy-based access control | Evaluate contextual conditions and explicit restrictions | A production deployment requires MFA and a trusted network. |

A useful conceptual relationship is:

`Identity → Role assignments → Effective permissions → Resource and context policies → Decision → Audit event`

The relationship is not a universal rule that every authorization system must implement in precisely this order. It is the evaluation model used throughout these examples, with explicit denials taking precedence over grants.

## Permissions and access-control decisions

A permission is modeled as a resource type and an action. Examples include `repository:read`, `repository:write`, `pull_request:review`, and `pull_request:approve`.

Resource types describe categories of objects. Actions describe operations on those objects. Separating them prevents a role that can review a pull request from automatically receiving permission to delete a repository.

Wildcard permissions such as `repository:*` can simplify administration, but they increase the consequences of assigning a broad role. Wildcards should be supported deliberately, documented, and restricted to trusted administrative roles where possible. None of the implementations treats an unknown action as permitted.

The Python, JavaScript, and C++ implementations support wildcard matching through explicit comparison logic. The Java implementation uses immutable permission records. PostgreSQL represents permissions as normalized rows with a unique constraint on the resource-action pair.

The default behavior is denial. A request without a matching permission does not succeed merely because no rule explicitly rejects it. This approach reduces the risk that a newly introduced resource type or action becomes accessible through an incomplete policy configuration.

An access decision has two separate outputs: whether the request is allowed and why that decision was made. Reasons such as `missing_permission`, `inactive_user`, `explicit_deny`, and `trusted_network_required` help distinguish configuration errors from policy violations.

## Role-based access control

RBAC organizes permissions around responsibilities rather than assigning every permission individually to every user.

The repository scenario uses the following roles:

| Role | Assigned responsibility |
|---|---|
| `reader` | Read repository and pull-request information. |
| `developer` | Modify repository content and create pull requests. |
| `reviewer` | Review and approve pull requests. |
| `release_manager` | Deploy and administer production releases. |
| `security_admin` | Perform security review and designated sensitive operations. |

A developer inherits the reader role. A reviewer also inherits the reader role. This inheritance represents a role hierarchy: permissions assigned to a parent role contribute to the effective permissions of the child role.

Role inheritance should be explicit and acyclic. If role A inherits from role B while role B inherits from role A, the hierarchy is invalid. The Python, JavaScript, C++, and Java implementations validate inheritance relationships and track visited roles during traversal. The SQL implementation uses a recursive common table expression with `UNION` to remove duplicate role paths and terminate traversal even if malformed legacy data contains a cycle.

Inheritance can reduce repeated assignments, but excessive nesting makes effective permissions difficult to understand. Production role hierarchies should remain small enough to audit, with automated tests covering the effective permissions of sensitive roles.

### Least privilege

Least privilege means granting only the access required for a user's responsibilities. A reviewer can approve pull requests without receiving repository deletion privileges. A release manager can deploy without automatically gaining permission to change every repository's content.

The examples deliberately separate read, write, review, approval, deployment, and deletion permissions. This distinction is more important than the number of roles: a small role set is useful only if its permissions match the organization's real responsibilities.

Role assignments must also be validated. Assigning an undefined role is a configuration error, not a reason to silently ignore the assignment. The application implementations reject unknown role names. PostgreSQL foreign keys prevent assignments to nonexistent users or roles.

## Policy evaluation and explicit denial

RBAC is a useful baseline, but role membership alone cannot express every access requirement. A production operation may depend on the resource environment, user department, source network, authentication strength, ownership, or temporary approval.

The implementations combine role permissions with contextual restrictions.

The production deployment rule requires both verified MFA and a source address within the illustrative trusted `10.` network range. A release manager with `repository:deploy` is denied if either condition fails. The network test is deliberately simplified for an educational example; production code should parse IP addresses and compare them against explicitly configured CIDR ranges rather than using a string prefix.

Explicit denial is evaluated before ordinary grants. For example, a user may hold a role that supplies `repository:delete`, yet a policy can still prohibit deletion of production resources by a designated department.

This precedence rule is important when several sources contribute permissions. Role membership, temporary grants, resource ownership, and contextual rules should not accidentally combine into a broader entitlement than the security policy intended.

The exact policy-combination semantics must be defined before implementation. In these examples, a matching explicit denial is decisive, while the other checks follow the rules implemented by each language version. Production systems should use a single documented policy contract across all service boundaries.

## Python implementation

The Python script implements `AuthorizationService` as a centralized policy evaluator.

### Domain model

`Permission`, `Role`, `User`, `Resource`, `AccessGrant`, `PolicyRule`, and `AccessContext` represent the authorization domain. Dataclasses make the fields explicit, and frozen dataclasses prevent accidental reassignment of policy values after construction.

The service maintains indexed dictionaries for users, resources, and roles. These maps support direct lookup by identifier. The audit log stores an `AuditEvent` for every evaluated request, including denied requests.

### Permission resolution

`effective_permissions()` recursively collects permissions from assigned roles and inherited roles. A visited set ensures that a role encountered through multiple inheritance paths is processed only once.

This avoids duplicate work and protects traversal from looping indefinitely if the underlying hierarchy is corrupted. Inheritance validation remains necessary because termination alone does not make a cyclic hierarchy valid.

### Decision evaluation

`authorize()` validates the request context and looks up the user and resource before calling `_evaluate()`. The evaluator resolves permissions, incorporates active temporary grants, evaluates explicit denial rules, checks matching permissions, and applies additional ownership and production-environment conditions.

`require_access()` provides a fail-closed interface for protected application operations. It raises `AuthorizationError` rather than returning a resource to a caller whose request has been denied.

The example tests cover inherited permissions, default denial, inactive accounts, network restrictions, explicit-deny precedence, inheritance configuration, and audit recording.

### Temporary grants

`AccessGrant` includes a recipient, permission, expiry timestamp, and justification. A grant is effective only when the request time is earlier than its expiry.

The demonstration evaluates a grant before and after expiration. This shows why a temporary entitlement should be evaluated against the current request time rather than copied permanently into a user's role assignments.

The demonstration uses an injected clock in the access context. Clock injection makes expiration behavior reproducible in tests and avoids relying on timing-sensitive sleeps.

## JavaScript implementation

The JavaScript implementation uses Node.js event handling to represent authorization as a service that emits observable decisions.

`PolicyEngine` maintains roles, users, resources, grants, and audit events in maps and arrays. `effectivePermissions()` resolves inherited role permissions. `evaluate()` calculates a decision and emits an `authorization:decision` event after recording an immutable audit entry.

### Event-driven auditing

The `on()` method registers listeners and returns an unsubscribe function. The caller can stop receiving events when the listener is no longer needed. This avoids uncontrolled listener accumulation in long-running processes.

The event emitter catches listener failures so a monitoring callback cannot alter the already-computed access decision. In a production system, listener failures should be sent to a reliable monitoring channel rather than merely printed to the console.

### Protected operations

`execute()` evaluates authorization before invoking the asynchronous business operation. The callback is not executed when access is denied.

This pattern is useful for protecting repository administration endpoints, deployment handlers, and other operations that must not run without authorization. The protected operation itself can still fail for unrelated reasons, such as an unavailable deployment service.

The caller must handle both authorization failures and business-operation failures. Successful authorization means the operation is permitted, not that the operation is guaranteed to succeed.

### Runtime considerations

The example uses Node.js's built-in `crypto` module to generate request identifiers and requires no npm dependencies. Its in-memory maps are suitable for a demonstration but do not provide durable storage or coordination between application instances.

A distributed deployment would need shared policy data, durable audit storage, consistent policy versions, and carefully defined behavior when a policy store becomes unavailable. A stale local permission cache can otherwise continue granting access after a role has been revoked.

## C++ repository governance case study

The C++ program models a repository governance service with a typed domain model and explicit access-decision reasons.

The `GovernanceEngine` owns maps of roles, users, and resources, plus collections of rules, temporary grants, and audit records. Ordered maps provide predictable iteration and logarithmic key lookup. Permission evaluation scans a user's effective permissions and the configured rules, making the example straightforward to inspect.

### Scenario

The case study contains a restricted production repository, a development pull request, an engineering developer, a security reviewer, a platform release manager, and an inactive account.

The developer can write to the repository through inherited role permissions. The reviewer can approve the pull request. The release manager has deployment privileges but cannot deploy from an untrusted network. A department-specific explicit-deny rule prevents production deletion by the platform department.

### Validation and failure handling

`addRole()` validates the role hierarchy and removes a newly inserted role if validation fails. User creation checks role references, and resource creation checks that the owner exists.

`authorize()` distinguishes unknown users, inactive users, missing resources, missing permissions, and policy restrictions. It appends an audit record for every evaluated request.

The engine rejects invalid configuration through exceptions. The executable entry point catches configuration failures and returns a nonzero exit code.

### Performance and design trade-offs

Role resolution is proportional to the reachable role graph and the permissions collected. A production implementation could cache effective permissions, but any cache would require reliable invalidation when a role assignment, inherited role, or permission changes.

The code uses standard C++17 facilities without external dependencies. It does not persist its audit records, synchronize concurrent mutations, or implement cryptographic identity verification. Those responsibilities would require separate production components.

## Java enterprise implementation

The Java program emphasizes explicit domain types and service boundaries.

Records represent immutable values such as `Permission`, `PolicyRule`, `AccessContext`, `TemporaryGrant`, `Decision`, and `AuditEvent`. The `Role` class exposes immutable permission and inheritance sets, while `User` permits a controlled active-state transition.

`AuthorizationService` owns the repository authorization state. Its methods separate role registration, inheritance validation, user and resource registration, temporary grants, permission resolution, decision evaluation, and auditing.

### Typed policy conditions

`PolicyCondition` makes department, environment, ownership, MFA, and trusted-network requirements explicit. `PolicyRule` pairs these conditions with a permission and an effect.

This model reduces ambiguity compared with loosely structured policy dictionaries. It also makes validation and test construction easier because the required fields are known at compile time.

The service evaluates matching explicit-deny rules before relying on an ordinary role grant. It rejects inactive accounts and missing resources, then checks the resolved permissions and applicable contextual restrictions.

### Exceptions and state management

`requireAccess()` converts a negative decision into `AuthorizationException`. Callers that need a protected resource therefore cannot accidentally treat a denial as a successful result.

The example validates role inheritance when roles are registered and rejects duplicate identifiers. Temporary grants include expiry times and justifications. Audit events are exposed through immutable list copies so callers cannot directly alter the service's stored audit collection.

### Enterprise limitations

The example is a single-process service. Its collections are not designed for concurrent policy updates, and its audit log is in memory. A production implementation would need an explicit concurrency model, durable persistence, transactional updates to role assignments, and controlled administrative operations.

The service also illustrates why typed policy data matters: a policy condition that is not evaluated consistently can become a security defect. Each supported condition should have an explicit enforcement point and a corresponding test.

## PostgreSQL relational authorization model

The SQL script represents authorization as normalized relational data. It is designed for PostgreSQL 15 or later and recreates the `authorization_lab` schema.

### Core relationships

`app_users` stores identities and active status. `roles` stores named responsibilities. `permissions` defines resource-action pairs. `role_permissions` maps roles to permissions, while `user_roles` maps users to assigned roles.

`role_inheritance` records parent-child role relationships. The recursive `effective_user_permissions` view resolves inherited permissions for active users.

The repository domain is represented by `repositories`, `pull_requests`, `repository_commits`, `pull_request_commits`, `reviews`, `review_comments`, and `status_checks`. These entities allow access policy to be examined alongside the repository workflow that consumes it.

`branch_protection_policies` and `policy_required_checks` demonstrate a separate governance mechanism. They describe conditions on a target branch rather than assigning a user permission to access an object.

### Integrity constraints

Primary keys identify records, foreign keys preserve relationships, and unique constraints prevent duplicate usernames, role names, permission definitions, and repeated role assignments.

Check constraints reject invalid classifications, unsupported pull-request states, negative approval requirements, invalid review states, and empty policy names. A resource cannot refer to an owner who does not exist.

These constraints protect data integrity even when records are written by multiple applications. They do not replace authorization checks: a valid foreign key does not prove that the requesting user is allowed to perform an operation.

### Temporary grants and audit records

`temporary_grants` stores the recipient, permission, justification, granting user, expiry, and optional revocation time. The supporting partial index targets grants that have not been revoked.

`access_audit` records the request identifier, actor, resource, action, decision, reason, and timestamp. The audit indexes support recent-event inspection and denial-focused investigations.

The `record_access_decision()` function validates the decision vocabulary and writes an audit event. A production deployment should further restrict direct table modification and establish an auditable method for recording decisions from trusted application services.

### Approval freshness and merge eligibility

The `current_pull_request_approvals` view counts only the latest decision by each reviewer when it is an approval of the latest associated commit. Dismissed reviews do not count, and an author's own review is excluded.

The `pull_request_merge_eligibility` view combines the pull request state, author status, repository state, required approval count, required status checks, and unresolved review conversations.

This is a repository governance example, not a complete replacement for a hosting platform's branch-protection implementation. The simplified schema does not model every possible branch pattern, commit synchronization event, bypass authorization, or concurrent merge race. Production merge eligibility must be revalidated atomically against the latest repository state.

### Transactions and database enforcement

The script wraps schema creation, sample data, and demonstration queries in a transaction. Nested exception blocks inside the demonstration `DO` statement isolate deliberately invalid inserts, allowing constraint failures to be shown without aborting the remaining examples.

PostgreSQL-specific mechanisms include identity columns, PL/pgSQL functions, recursive common table expressions, filtered aggregate counts, partial indexes, and `TIMESTAMPTZ` timestamps.

The script is intended for a disposable learning database because it drops and recreates its own schema. Its transaction does not imply that external application operations are automatically authorized or that a recorded audit event is tamper-proof.

## Approval boundaries, ownership, and policy conflicts

Ownership is an attribute of a resource, not a substitute for a permission model. A user may own a repository but still be subject to organizational restrictions on production deletion or privileged deployment.

Similarly, a temporary grant is an additional entitlement, not an automatic override of explicit denial rules or contextual security requirements.

Policy conflicts should be resolved by documented precedence rather than by whichever permission happens to be found first. The examples use explicit-deny precedence, but the exact treatment of ownership, contextual conditions, and explicit allow rules must remain consistent across implementations.

Approval requirements should be kept separate from the underlying permission to approve. A user can be authorized to approve a pull request while a particular pull request still lacks the required number of valid approvals. Conversely, a record showing an approval does not prove that the reviewer was eligible, that the approval remains current, or that the target branch's protection requirements have been satisfied.

## Failure modes and operational safeguards

| Failure mode | Consequence | Required control |
|---|---|---|
| Default allow when no policy matches | Newly introduced actions may become publicly accessible. | Deny requests without a valid matching grant. |
| Cyclic or invalid role inheritance | Permission resolution may loop or produce confusing results. | Validate role graphs and track visited roles. |
| Stale role or permission cache | Revoked access may remain effective. | Invalidate caches on policy changes and bound cache lifetimes. |
| Expired grant still honored | Emergency access persists longer than intended. | Check expiry during every relevant authorization evaluation. |
| Missing object-level checks | A user with general permission may access another user's resource. | Apply ownership and resource-attribute policies where required. |
| Audit failures | Investigators cannot reconstruct access decisions. | Use durable audit delivery and monitor write failures. |
| Policy-store outage | Services may make inconsistent or unsafe decisions. | Define an explicit fail-closed policy for sensitive operations. |
| Check-then-act race | A resource or entitlement changes after authorization. | Revalidate sensitive operations and use transactional or concurrency controls. |

## Security and production considerations

Authorization should be enforced at the service boundary that performs the protected operation. Hiding a user-interface button does not prevent a direct API request. Every sensitive endpoint must independently establish the identity, identify the target resource, evaluate permissions, and enforce the result.

Production deployments should distinguish user-facing error messages from internal audit details. Detailed denial reasons are valuable to operators but may reveal resource existence or policy configuration to unauthorized callers.

Network trust should use parsed IP addresses and explicit CIDR policy. MFA status must come from a trusted authentication context rather than a caller-controlled request field. Request identifiers should be correlated with authenticated identities and service logs.

Role changes and grant revocations should become effective within a documented interval. High-risk actions such as deletion, privilege escalation, secret access, and production deployment warrant narrower permissions and stronger contextual checks.

Audit data should be protected against unauthorized modification, retained according to a defined policy, and monitored for suspicious denial patterns, unusual grant activity, inactive-account requests, and privileged actions outside expected operating conditions.

Finally, authorization decisions should be tested as policy outcomes, not merely as successful method calls. Tests should cover allowed requests, denied requests, conflicting rules, role inheritance, expiration boundaries, inactive identities, missing resources, and changes to the underlying policy. A policy is reliable only when its intended boundaries are enforced consistently across the code and data layers.
