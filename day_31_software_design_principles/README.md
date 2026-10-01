# Software Design Principles: DRY, KISS, YAGNI, and Separation of Concerns

## Scope

This project examines four software design principles through a single technical scenario: a deployment-management system that validates a deployment request, checks authorization, evaluates deployment policy, executes the deployment, records the result, and reports the outcome.

The four principles address different forms of software complexity:

| Principle | Primary concern | Question it answers |
|---|---|---|
| DRY | Duplication | Where should one rule or piece of knowledge have a single authoritative representation? |
| KISS | Unnecessary complexity | Can this behavior be implemented more directly without obscuring the decision? |
| YAGNI | Speculative functionality | Is this capability required by a real current requirement? |
| Separation of Concerns | Responsibility boundaries | Which component should own this behavior? |

These principles overlap in practice, but they are not interchangeable. DRY concerns duplicated knowledge, KISS concerns unnecessary complexity, YAGNI concerns unnecessary capability, and separation of concerns concerns responsibility boundaries.

The implementations deliberately use the same domain scenario while approaching it differently in Python, JavaScript, and C++.

## The Deployment Scenario

A software team needs a deployment service for two environments:

- `staging` is available to active developers.
- `production` requires an active platform engineer.
- Production deployments require passing tests.
- High-risk changes cannot be automatically deployed.
- Very large changes require additional review.
- Deployment results must be auditable.
- The current system does not require multi-cloud deployment, plugin marketplaces, predictive capacity management, or a general-purpose workflow language.

A deployment request contains information such as:

`request_id`, `service`, `version`, `environment`, `requester`, test status, changed-file count, and risk score.

The workflow is intentionally separated:

`request -> validation -> authorization -> policy evaluation -> execution -> persistence -> notification`

This separation makes it possible to change one responsibility without forcing unrelated components to change.

---

## DRY: Don't Repeat Yourself

DRY is about duplicated knowledge rather than merely duplicated text.

Two code fragments can look different while encoding the same business rule. Conversely, two similar-looking statements may legitimately be separate because they represent different knowledge.

In the deployment system, the automatic-deployment risk threshold is business knowledge. If one part of the system uses a threshold of `4` and another independently uses `5`, the software can make contradictory decisions.

The Python implementation places policy thresholds in `DeploymentPolicy` and evaluates them through `PolicyEngine`.

The JavaScript implementation uses `DeploymentPolicy.violations()` as the central policy evaluation mechanism.

The C++ implementation represents the same policy through `DeploymentPolicy` and `PolicyEngine`.

### Why centralized knowledge matters

Suppose the organization changes the automatic deployment threshold from risk `4` to risk `3`.

A DRY implementation allows the policy configuration to change in one authoritative location.

A duplicated implementation may contain conditions such as:

`request.risk_score <= 4`

in several services, command handlers, tests, and environment-specific branches.

The problem is not the number of characters. The problem is that the same business decision has multiple owners.

### What DRY does not mean

DRY does not mean that every similar line must be extracted into a shared function.

For example, two unrelated components may both check whether a string is empty. Extracting every common expression into a global utility layer can create coupling without reducing meaningful duplication.

DRY should be applied to duplicated knowledge where maintaining multiple copies can produce inconsistent behavior.

### Executable DRY contrast

The Python file contains `DuplicatedDeploymentRules`, where staging and production methods independently encode the same risk and test condition.

The JavaScript file contains `duplicatedPolicyExample()` for the same conceptual contrast.

The C++ file contains `DuplicatedRulesExample`.

These examples are intentionally kept separate from the production workflow so that the maintenance problem can be observed without making duplication part of the main architecture.

---

## KISS: Keep It Simple

KISS addresses unnecessary complexity.

A simple requirement should normally have a proportionately simple implementation. Complexity should be introduced when it solves a real problem rather than because a more elaborate architecture is theoretically possible.

The case study contains simple predicates such as the small-safe-change rule.

The Python implementation uses `is_safe_small_change()`.

The JavaScript implementation uses `isSmallSafeChange()`.

The C++ implementation uses `is_small_safe_change()`.

Each directly evaluates the current rule instead of introducing a strategy registry, factory hierarchy, plugin system, or configuration language.

### KISS and readability

A function that directly expresses a business rule can be easier to verify:

`tests_passed and changed_files <= 10`

A much larger abstraction may technically provide the same result while forcing a reader to navigate several classes before discovering the actual condition.

KISS does not mean avoiding abstraction completely. The deployment system does need abstractions around persistence and responsibilities because those boundaries represent actual design concerns.

The principle is to avoid complexity that does not provide corresponding value.

### KISS and change

Simple code can still be designed for change.

For example, the repository interface exists because storage is a meaningful boundary. The workflow does not need to know whether records are stored in memory or in a file.

By contrast, there is no separate abstraction for every possible deployment provider because the current scenario only requires one execution boundary.

---

## YAGNI: You Aren't Gonna Need It

YAGNI addresses speculative functionality.

The deployment system currently needs:

- request validation
- authorization
- policy evaluation
- deployment execution
- audit persistence
- notifications

It does not currently require:

- multi-cloud failover
- a deployment plugin marketplace
- arbitrary workflow scripting
- predictive infrastructure scaling
- a distributed event-sourcing platform
- a custom policy programming language

Building those systems before their requirements exist increases code volume, testing requirements, operational burden, documentation needs, and maintenance cost.

### YAGNI is not an argument against architecture

YAGNI does not mean that a system should be written without structure.

The repository boundary in the examples is justified because persistence is an actual concern. The validation component is justified because validation is an actual responsibility. The policy engine is justified because deployment eligibility contains multiple business rules.

The distinction is between an abstraction that supports a known requirement and an abstraction created for a hypothetical future.

### YAGNI and premature generalization

Consider a deployment executor.

If the current requirement is one deployment mechanism, a small executor boundary can be sufficient.

Creating interfaces for ten providers, provider discovery, dynamic plugin loading, provider capability negotiation, regional routing, and failover policy may create substantial complexity before any requirement needs it.

When a second concrete requirement appears, the design can evolve using evidence from that requirement.

---

## Separation of Concerns

Separation of concerns assigns different responsibilities to different parts of the system.

The deployment workflow separates:

| Concern | Component |
|---|---|
| Input validation | `DeploymentValidator` |
| User authorization | `AuthorizationService` |
| Business deployment rules | `PolicyEngine` / `DeploymentPolicy` |
| Persistence | Repository implementations |
| Deployment operation | `DeploymentExecutor` |
| User-facing notifications | `NotificationService` |
| Workflow coordination | `DeploymentService` or `DeploymentWorkflow` |

This is different from DRY.

DRY asks whether one piece of knowledge has been duplicated.

Separation of concerns asks which component should own a responsibility.

A system can have no obvious duplicated code and still have poor separation of concerns if one class validates requests, authenticates users, evaluates business policy, writes files, deploys services, and sends notifications.

---

## Responsibility Boundaries

### Validation

Validation determines whether the structure and values of a request satisfy input rules.

Examples include:

- a deployment identifier must exist
- a service name must exist
- the version must use the expected `x.y.z` representation
- the environment must be recognized
- the changed-file count cannot be negative
- the risk score must remain within the allowed range

Validation does not decide whether a developer is authorized to deploy to production.

### Authorization

Authorization answers whether the requester is permitted to perform the operation.

In the case study, production access requires an active platform engineer.

That decision belongs to authorization rather than version validation or persistence.

### Policy Evaluation

Policy evaluation determines whether a valid and authorized request satisfies business deployment rules.

Examples include:

- production requires passing tests
- risk above the automatic threshold is rejected
- large changes require additional review

These rules are centralized so they do not become environment-specific copies scattered across the application.

### Execution

The executor performs the deployment operation after the request has passed earlier gates.

The executor does not decide whether the requester is authorized. That decision has already been assigned to another responsibility.

### Persistence

The repository records deployment results.

The workflow can use an in-memory repository for tests or a file-backed repository for audit storage without changing the policy rules.

This is a practical example of separating business logic from infrastructure.

### Notification

Notifications communicate results.

A notification mechanism should not independently decide whether deployment is allowed. Otherwise, a communication concern becomes coupled to authorization and policy logic.

---

## Python Implementation

The Python program models the deployment domain using dataclasses, protocols, dictionaries, exceptions, dependency injection, and interchangeable repository implementations.

### Domain representation

`DeploymentRequest` is an immutable dataclass containing the information required by the deployment workflow.

`DeploymentRecord` stores the resulting state and reason.

`DeploymentStatus` is an enum that prevents status values from being scattered as unrelated strings throughout the application.

### Validation boundary

`DeploymentValidator` owns request validation.

It raises `ValidationError` when a request violates structural rules.

The validator does not write audit records or execute deployments. This keeps input correctness separate from application behavior.

### Authorization boundary

`AuthorizationService` stores developers by username and evaluates environment-specific access.

Production authorization is intentionally represented as a domain rule rather than being mixed into request parsing.

### Central policy

`DeploymentPolicy` contains policy configuration.

`PolicyEngine` evaluates that configuration against a request and returns policy violations.

This provides a single place where deployment rules are interpreted.

### Repository abstraction

`DeploymentRepository` is represented as a Python protocol.

`InMemoryDeploymentRepository` supports deterministic testing.

`JsonDeploymentRepository` provides file-backed persistence using only the standard library.

The application service does not depend directly on either storage implementation.

### Workflow orchestration

`DeploymentService` coordinates the process:

`validate -> authorize -> evaluate policy -> execute -> persist -> notify`

It does not perform all of those operations itself. It coordinates components that each own a specific responsibility.

### Executable edge cases

The Python assertions cover:

- successful production deployment
- unauthorized production deployment
- high-risk deployment
- production deployment with failed tests
- invalid version input
- persistence through a temporary JSON audit file

The assertions make design behavior executable rather than leaving it as documentation only.

---

## JavaScript Implementation

The JavaScript program presents the same domain through a different technical structure.

Its main distinction is an event-driven workflow combined with asynchronous file persistence.

### Immutable domain request

`DeploymentRequest` calculates the initial risk and freezes the resulting object.

This prevents later workflow stages from silently modifying the request that earlier stages evaluated.

### Event-driven lifecycle

`DeploymentEvents` extends Node.js `EventEmitter`.

The workflow emits events such as:

`deployment:accepted`

`deployment:rejected`

`deployment:deployed`

`NotificationSubscriber` listens to these events.

This demonstrates separation between the workflow's state transition and notification consumers.

The workflow does not need to call a particular notification implementation every time an event occurs.

### Asynchronous persistence

`JsonAuditRepository` uses Node.js promises and `fs/promises`.

The asynchronous boundary reflects how JavaScript applications commonly interact with filesystem, database, HTTP, and cloud APIs.

The repository writes a temporary file and then renames it into place. This reduces the chance that the canonical audit file remains partially written if the process encounters an interruption during the write.

### Policy evaluation

`DeploymentPolicy.violations()` returns all applicable policy failures rather than immediately throwing on the first one.

That allows the caller to report multiple independent policy problems from one request.

### YAGNI in the JavaScript design

The program does not create a provider registry or dynamically loaded deployment plugin architecture.

`DeploymentExecutor` is an explicit boundary because execution is a genuine responsibility. More elaborate provider management would require a concrete requirement before becoming justified.

---

## C++ Case Study

The C++ implementation treats the deployment manager as a small governance-oriented system.

The main architectural components are:

`DeploymentValidator`

`AuthorizationService`

`PolicyEngine`

`DeploymentRepository`

`DeploymentExecutor`

`NotificationService`

`DeploymentService`

### C++ domain model

The program uses `enum class DeploymentStatus` instead of unrestricted strings for deployment state.

`DeploymentRequest` and `DeploymentRecord` are value-oriented structures.

The use of explicit types makes invalid states less likely to spread through the application.

### Repository interface

`DeploymentRepository` defines the persistence boundary.

`MemoryDeploymentRepository` is useful for deterministic tests and in-process execution.

`AuditFileRepository` demonstrates a separate persistent implementation using the standard C++ library.

The workflow depends on the repository interface rather than a specific storage mechanism.

### Policy engine

`PolicyEngine` owns business rules and uses `DeploymentPolicy` as configuration.

It produces a collection of policy violations.

This keeps policy evaluation separate from authorization and storage.

### Dependency injection

`DeploymentService` receives references to its collaborators through its constructor.

This avoids constructing every dependency internally.

It also makes testing easier because a different repository implementation can be supplied without rewriting the deployment workflow.

### Case-study workflow

A valid request follows:

`DeploymentRequest`

then `DeploymentValidator`

then `AuthorizationService`

then `PolicyEngine`

then `DeploymentExecutor`

then `DeploymentRepository`

then `NotificationService`

A rejected request is persisted and reported without reaching the deployment executor.

### Failure handling

The C++ implementation explicitly handles:

- empty identifiers
- empty service names
- malformed versions
- unsupported environments
- empty requesters
- negative change counts
- invalid risk values
- inactive developers
- unauthorized production deployments
- failed tests
- excessive risk
- oversized changes
- unavailable audit files

This makes the design boundaries observable during execution.

---

## How the Four Principles Interact

The principles reinforce one another but solve different problems.

A deployment class containing validation, authorization, persistence, and notifications can violate separation of concerns because unrelated responsibilities are coupled.

If that class also repeats the same risk condition in multiple methods, it has a DRY problem.

If the class introduces a large strategy framework for a rule that has only one implementation, it has a KISS problem.

If it also implements unused multi-cloud routing and predictive scaling because those capabilities might be useful later, it has a YAGNI problem.

A disciplined design therefore asks four separate questions:

- Is the same business knowledge represented in multiple places?
- Is the implementation more complicated than the current problem requires?
- Does this capability correspond to a real current requirement?
- Does each responsibility have a clear owner?

These questions should not be collapsed into one generic idea of "clean code."

---

## Practical Design Changes

Consider a request to change the production risk threshold from `4` to `3`.

With centralized policy, the change belongs to the deployment policy configuration.

Consider a request to add a database audit repository.

The repository boundary already isolates persistence from the workflow, so the storage mechanism can change without moving authorization rules into the database layer.

Consider a request to add a second deployment provider.

That is a new concrete requirement. The existing execution boundary can then be evaluated to determine whether an abstraction for multiple providers is justified.

Consider a request to change notification delivery from console output to another mechanism.

Notification behavior can change independently because it is not responsible for deployment authorization or policy evaluation.

These changes demonstrate why responsibility boundaries matter during maintenance, not only during initial development.

---

## Common Design Failure Modes

### Extracting abstractions too early

A developer sees two similar functions and immediately creates a hierarchy of interfaces, factories, strategies, and registries.

The result can be more difficult to understand than the original code.

The relevant question is whether the duplicated behavior represents shared knowledge or merely superficial similarity.

### Hiding simple rules behind abstractions

A simple boolean business rule may become difficult to verify if it is spread across several classes.

KISS favors a direct implementation when the domain does not justify additional indirection.

### Copying policy into environment-specific code

Duplicating production and staging rules can produce divergence.

For example, one environment might use risk `4` while another silently uses risk `5`.

Central policy evaluation prevents this form of accidental inconsistency.

### Building hypothetical infrastructure

Implementing a full multi-cloud deployment engine before a second provider exists adds maintenance costs without satisfying a current requirement.

YAGNI does not prohibit future evolution. It avoids paying the cost of speculative features before their requirements are understood.

### Combining unrelated responsibilities

A deployment manager that parses requests, authenticates users, calculates risk, writes database records, performs network deployment, and sends notifications becomes difficult to test and modify.

Separation of concerns gives those responsibilities clearer owners.

---

## Edge Cases

The implementations intentionally reject malformed or unsafe inputs rather than allowing invalid values to travel through the workflow.

Important cases include malformed semantic-style versions, unsupported environments, negative change counts, invalid risk ranges, inactive users, unauthorized production deployments, failed tests, high-risk changes, and oversized changes.

A useful property of the design is that many failures occur before deployment execution.

That is important because validation and policy failures should not trigger side effects such as an actual deployment.

---

## Performance Considerations

The case-study data volumes are small, so simple structures are appropriate.

Python uses dictionaries for developer and in-memory deployment lookups, giving average constant-time lookup behavior.

JavaScript uses `Map` for developer lookup and asynchronous filesystem operations for audit persistence.

C++ uses `std::unordered_map` for in-memory developer and record lookup.

Policy evaluation is linear in the number of policy rules. The number of rules in this system is deliberately small, so a more complicated rule engine would not provide meaningful performance benefits.

The repository implementations have different performance characteristics. An append-only file repository is appropriate for a small audit demonstration but would not automatically provide the indexing, concurrent access control, transactional guarantees, retention management, or query performance expected from a production database.

---

## Security Considerations

Authorization must be performed independently of input validation.

A syntactically valid request is not automatically an authorized request.

The examples prevent ordinary application developers from deploying directly to production by applying an explicit authorization rule.

Production policy also requires passing tests.

In a real deployment platform, the authorization decision should be based on trusted identity and role information rather than a username supplied by the request itself. Audit records should be protected against unauthorized modification, and deployment credentials should never be stored in source code or ordinary request objects.

The examples intentionally avoid implementing credential storage because that is outside the current case-study requirement.

---

## Testing and Debugging

The executable implementations include assertions for normal and failure paths.

Testing should verify each responsibility independently where possible:

- validation tests should focus on malformed requests
- authorization tests should focus on identity and environment rules
- policy tests should focus on risk and change-size rules
- repository tests should focus on persistence behavior
- executor tests should focus on deployment execution results
- orchestration tests should verify the order and interaction of these components

A useful debugging strategy is to identify which responsibility owns the incorrect behavior before modifying code.

For example, if a valid production request is rejected because the requester lacks platform authorization, changing the version validator would address the wrong concern.

---

## Design Trade-offs

Strict separation can itself become excessive.

Creating a separate class for every two-line operation can make a system harder to navigate.

Likewise, extracting every repeated expression can produce utility modules with weak cohesion.

The appropriate boundary depends on whether a behavior represents a meaningful responsibility, a stable policy, an infrastructure boundary, or a requirement that genuinely benefits from independent testing and change.

The examples therefore do not attempt to maximize the number of abstractions.

They deliberately combine:

- simple functions for simple rules
- dedicated classes for meaningful responsibilities
- interfaces where substitution has practical value
- centralized policy where business knowledge must remain consistent
- direct implementations where speculative complexity is unnecessary

This balance is the practical relationship between DRY, KISS, YAGNI, and separation of concerns.
