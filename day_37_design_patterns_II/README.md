# Design Patterns II: Strategy, Observer, Adapter

## Scope

This module presents three complementary design patterns through a repository governance domain:

- **Strategy** encapsulates interchangeable algorithms or policies.
- **Observer** establishes a publisher-subscriber relationship between a domain event source and independent consumers.
- **Adapter** converts one interface or data model into another interface expected by the application.

The implementations use a common technical setting, but they deliberately solve different design problems. A merge policy is an example of behavior that can vary, repository lifecycle notifications are events that can have multiple consumers, and an external CI service is an example of an incompatible interface that must be translated.

The code does not treat these patterns as interchangeable. Strategy changes how a decision is made, Observer changes how interested components are notified, and Adapter changes how an incompatible dependency can participate in an existing abstraction.

---

## The Core Design Problem

A repository governance service commonly has several independent concerns.

A Pull Request has a current state, a source branch, a target branch, commits, reviews, and status checks. A development branch may use a lightweight merge policy, while a production branch may require multiple eligible approvals and additional checks.

At the same time, events such as review requests, review submissions, status updates, and merges may need to be consumed by an audit log, notification service, metrics collector, or other infrastructure.

The status information itself may come from an external CI platform whose API does not match the internal application's status model.

A single large class containing all of these rules would become tightly coupled. The three patterns provide separate mechanisms for reducing those dependencies.

---

## Strategy Pattern

The Strategy pattern encapsulates a family of interchangeable algorithms or policies behind a common interface.

In this module, the common abstraction is `MergeStrategy`.

The Python implementation defines `FastForwardStrategy` and `ProtectedBranchStrategy`. The JavaScript implementation uses `DevelopmentBranchStrategy` and `ProductionBranchStrategy`. The C++ and Java implementations use corresponding policy objects.

The important property is that the Pull Request does not contain the merge policy itself.

A service can receive a strategy such as:

`FastForwardStrategy`

or:

`ProtectedBranchStrategy`

and call the same operation:

`evaluate(pull_request)`

The returned `MergeDecision` contains both the decision and the reasons for rejection.

### Why Strategy is appropriate here

Development and production branches can have materially different governance rules.

A development policy can require passing checks and a conflict-free Pull Request while allowing a lower approval threshold. A production policy can require two distinct eligible reviewers, all required checks, no current change request, and a conflict-free Pull Request.

Embedding those alternatives directly into `PullRequest` would force the domain object to know every possible governance policy.

Strategy moves the variable policy outside the domain object.

### Strategy boundary

The stable part is the interface:

`evaluate(PullRequest) -> MergeDecision`

The variable part is the policy implementation.

This makes the application service independent of the detailed algorithm used to determine merge eligibility.

A production policy can therefore be replaced by another policy without rewriting the Pull Request model.

### Important state consideration

Reviews and status checks are associated with a particular commit.

If a Pull Request receives a new commit after a review, the new head represents a different version of the change. A policy that counts an approval from an older commit as current would incorrectly treat an outdated review as evidence for the new version.

The implementations therefore compare review and status-check commit identifiers with the Pull Request's current head.

This is a critical part of the example because Strategy is not merely an abstraction exercise. The strategy evaluates domain state that has temporal meaning.

---

## Observer Pattern

The Observer pattern allows one publisher to notify multiple independent subscribers.

The publisher does not need to know the internal implementation of each subscriber.

The implementations model this with a repository event bus.

Events include:

- review requested
- review submitted
- changes requested
- status updated
- merged

An audit observer records events. A notification observer reacts to review-related events. A metrics observer counts event types.

The Pull Request service publishes an event without directly calling the audit logger or metrics collector.

For example, the service can publish a `review_requested` event. The audit observer can record it while the notification observer sends a reviewer-oriented notification.

### Publisher and subscriber responsibilities

The event bus is responsible for maintaining subscribers and dispatching events.

Observers are responsible for interpreting events.

The domain service is responsible for deciding when a meaningful domain event has occurred.

This separation prevents the Pull Request service from becoming a collection of unrelated integration calls.

### Observer failure isolation

The examples intentionally protect the event dispatch loop from an exception thrown by one observer.

This matters in real event-driven applications. A failure in metrics processing should not necessarily prevent an audit observer from receiving a security-sensitive repository event.

The Python, C++, and Java implementations catch observer failures during dispatch. The JavaScript implementation similarly isolates listener execution.

This does not mean every production event system should silently swallow failures. In a real system, observer failures may require retry queues, durable event storage, alerting, or dead-letter handling. The example focuses on the core Observer relationship and basic failure isolation.

### Subscription lifecycle

The JavaScript event emitter returns an unsubscribe function. The other implementations expose explicit subscription mechanisms.

Observer lifecycle matters because long-lived publishers can retain references to observers that should no longer receive events.

Without controlled subscription and unsubscription, event-driven systems can accumulate stale listeners and unnecessary memory usage.

---

## Adapter Pattern

The Adapter pattern allows an object with one interface to be used where another interface is expected.

The repository governance system expects a normalized `StatusProvider`.

The external CI service uses its own model. Its result values include strings such as:

`SUCCESS`

`FAILURE`

`CANCELLED`

The governance model instead uses:

`PASSING`

`FAILING`

`PENDING`

The adapter translates between those models.

### Why the Adapter is needed

Without the adapter, the governance service would need to understand the external CI provider's API.

That would couple the governance domain to a specific vendor or external protocol.

With the adapter, the governance service only knows that a `StatusProvider` can return a `StatusCheck`.

The external CI client can change without forcing the governance policy implementation to change.

### Fail-closed handling

An unknown external build is represented as `PENDING`.

This is deliberate.

Treating an unknown CI result as passing would create a fail-open condition in which missing evidence is interpreted as successful evidence.

A merge policy should distinguish:

- confirmed success
- confirmed failure
- incomplete or unavailable information

That distinction is especially important when the status check is a prerequisite for a protected branch.

---

## Relationship Between the Three Patterns

The patterns solve different dependency problems.

| Pattern | Primary question | Example in this module |
|---|---|---|
| Strategy | Which algorithm or policy should evaluate this situation? | Development versus production merge policy |
| Observer | Who needs to know that something happened? | Audit, metrics, and notification subscribers |
| Adapter | How can an incompatible dependency fit an existing interface? | External CI client to internal status provider |

They can also cooperate.

A governance service can use an Adapter to obtain normalized CI status. It can pass the resulting domain state to a Strategy that evaluates merge eligibility. After a successful merge, the service can publish an Observer event.

The three patterns therefore address different axes of change:

`Strategy -> changing decision policy`

`Observer -> changing event consumers`

`Adapter -> changing external interface compatibility`

---

## Python Implementation

The Python program provides the most direct domain simulation.

`PullRequest`, `Commit`, `Review`, and `StatusCheck` form the core model.

The Strategy implementation uses an abstract `MergeStrategy` class. `FastForwardStrategy` provides a lighter policy, while `ProtectedBranchStrategy` requires eligible approvals and passing current checks.

The Observer implementation uses `EventBus` and a protocol-based observer contract. `AuditLogger`, `ReviewNotifier`, and `MetricsCollector` are independent consumers.

The Adapter implementation uses `StatusProvider` as the internal contract and `CiAdapter` to translate the simulated external CI system.

`PullRequestService` composes all three mechanisms. It does not need to know the internal implementation details of the selected strategy, observers, or external CI provider.

The script also demonstrates an unknown CI revision and intentionally maps it to a pending state.

---

## JavaScript Implementation

The JavaScript program emphasizes JavaScript's event-driven programming model.

The Observer implementation uses a custom `EventEmitter` with event-specific listener collections. The `on()` method returns an unsubscribe function, which demonstrates a useful lifecycle pattern for long-running JavaScript processes.

The Adapter uses an asynchronous `ExternalCiClient`. Its `fetchBuild()` method returns a Promise, reflecting the asynchronous nature of external service integration in Node.js.

`CiStatusAdapter` converts external build results into the internal `CheckStatus` vocabulary.

The Strategy implementation uses polymorphic objects rather than duplicating policy logic inside the Pull Request object.

The service coordinates the objects while remaining independent of the external CI representation.

---

## C++ Case Study

The C++ program models a repository governance engine using explicit ownership and polymorphism.

`MergeStrategy` is an abstract base class. `DevelopmentMergeStrategy` and `ProductionMergeStrategy` implement distinct policy algorithms.

`EventBus` owns shared references to `Observer` implementations through `std::shared_ptr`. Event dispatch takes a snapshot of the observer collection before invoking callbacks, reducing the risk of collection mutation during notification.

The Adapter layer uses the `StatusProvider` interface and `CiAdapter`. `std::optional<ExternalBuild>` represents the possibility that an external build does not exist.

The production strategy uses `std::set` for eligible reviewers and approvals. This provides distinct-reviewer semantics naturally because inserting the same reviewer twice does not increase the approval count.

The case study therefore demonstrates both the pattern and relevant C++ design concerns:

- abstract interfaces
- runtime polymorphism
- RAII-compatible ownership
- standard containers
- optional external data
- validation
- exception-based failure handling
- explicit complexity trade-offs

The approval collection is effectively linear in the number of reviews, with set insertion and lookup providing logarithmic complexity for the ordered `std::set` implementation.

---

## Java Implementation

The Java program presents the same domain through stronger enterprise-oriented type boundaries.

Java records are used for immutable value objects such as `Commit`, `Review`, `StatusCheck`, and `RepositoryEvent`.

`MergeStrategy` defines the policy abstraction. The production strategy explicitly stores eligible reviewers and the required approval count.

`RepositoryEventBus` manages Observer subscriptions. A copied observer list is used during dispatch so an observer cannot destabilize iteration by modifying the underlying subscription collection while notifications are being processed.

The Adapter is represented by `StatusProvider` and `ExternalCiAdapter`.

The Java service combines these abstractions through constructor injection. This makes the dependencies explicit and allows a different strategy or status provider to be supplied without modifying the service.

The production policy uses a `Set<String>` for eligible reviewers and another set for distinct approvals. This avoids counting multiple reviews from the same eligible reviewer as multiple independent approvals.

---

## SQL Data Model

The PostgreSQL script models the same technical domain relationally rather than reproducing the object-oriented implementations.

The major entities are:

- `repositories` represents repository-level identity and configuration.
- `repository_members` represents users and their repository roles.
- `branches` represents source and target branches and their protection status.
- `commits` represents repository commits.
- `pull_requests` represents proposed changes and their current head commit.
- `pull_request_commits` associates commits with Pull Requests.
- `reviews` represents review decisions against specific commits.
- `review_comments` represents discussion associated with reviews.
- `status_checks` represents normalized CI results.
- `external_ci_builds` preserves the external provider's vocabulary.
- `branch_protection_policies` stores target-branch governance.
- `required_status_checks` stores policy-specific check requirements.
- `protected_reviewers` stores eligible reviewers.
- `repository_events` represents the persistent form of Observer-style lifecycle events.

The schema uses foreign keys so that relationships cannot silently reference nonexistent entities.

---

## Database-Level Strategy Representation

The database does not implement an object-oriented Strategy interface because SQL has a different execution model.

Instead, the policy is represented by relational configuration.

`branch_protection_policies.required_approvals` specifies the approval threshold.

`protected_reviewers` identifies reviewers eligible to satisfy that threshold.

`required_status_checks` specifies which checks are mandatory.

The merge-eligibility query then evaluates those policy values against the current Pull Request state.

This is analogous to Strategy because the decision behavior can be driven by policy data rather than being hard-coded into the Pull Request record.

The distinction is important: the database stores and evaluates governance rules, while the application-level Strategy objects encapsulate executable policy algorithms.

---

## Database Representation of Observer Behavior

The `repository_events` table provides a durable event history.

An event contains:

- repository identity
- Pull Request identity
- event type
- actor
- JSON payload
- creation time

This allows lifecycle events to be queried after the original operation.

A transient in-memory Observer can disappear when a process terminates. Persisting events creates an auditable history that can later support analytics, operational reporting, or asynchronous processing.

The SQL model does not pretend that a table is automatically an Observer implementation. The table represents persisted event data, while the application-level event bus demonstrates actual subscriber notification.

---

## Database Representation of Adapter Behavior

The `external_ci_builds` table preserves source-system terminology.

For example, the external provider can record `SUCCESS`.

The normalized `status_checks` table stores `passing`.

This separation is useful because an integration boundary should not force external terminology into the internal domain model.

The Adapter in Python, JavaScript, C++, and Java performs this translation at runtime. The SQL model records both sides of that boundary for auditability.

---

## Code Review Versus Approval

A review is not necessarily an approval.

A reviewer may submit:

`comment`

`request_changes`

or:

`approve`

The SQL `reviews` table explicitly stores the decision.

This prevents the system from treating every review as approval evidence.

Approval is a specific decision with governance consequences.

The production Strategy and SQL merge query count only eligible `approve` decisions against the current Pull Request head.

Review comments are stored separately in `review_comments` because discussion is not equivalent to the review decision itself.

---

## Current-Commit Semantics

The examples consistently associate reviews and status checks with a commit.

Suppose a reviewer approves commit `abc123`. The author then pushes commit `def456`.

The Pull Request's head is now `def456`.

An approval attached to `abc123` should not automatically be interpreted as approval of `def456`.

This is why the implementations compare:

`review.commitSha == pullRequest.headSha`

and:

`check.commitSha == pullRequest.headSha`

The SQL implementation performs equivalent comparisons using `reviewed_commit_id`, `head_commit_id`, and `commit_id`.

This design prevents stale evidence from being treated as current evidence.

---

## Branch Protection and Merge Policy

Branch protection is a repository governance mechanism, while Strategy is an application design mechanism.

A branch protection policy may require two approvals, specific status checks, conversation resolution, linear history, and restrictions on direct pushes.

A Strategy object can implement an application-level evaluation of those rules.

The database stores the actual policy configuration.

These layers should not be confused.

A Strategy object does not itself make a branch protected. It represents executable policy logic.

Similarly, a protected branch is not merely an approval count. Protection can include multiple independent constraints governing how changes reach the branch.

---

## Validation and Failure Conditions

The implementations deliberately reject invalid domain states.

A Pull Request cannot be constructed without a commit.

A review cannot be attached to a closed or merged Pull Request.

A review must identify the commit it evaluates.

A status check must identify the commit it describes.

A production policy requires a positive approval threshold.

An unknown CI result is pending rather than passing.

A Pull Request with unresolved conflicts cannot satisfy the merge policy.

These validations reduce ambiguity at system boundaries.

---

## Performance Considerations

The examples use simple in-memory collections because their purpose is pattern demonstration.

For a small Pull Request, scanning reviews and checks is straightforward. The cost is generally proportional to the number of reviews and status checks attached to the Pull Request.

The C++ implementation uses ordered sets for distinct reviewer tracking. The Java implementation uses hash-based sets, which normally provide expected constant-time membership operations.

The SQL implementation adds indexes around frequently queried relationships such as:

`pull_requests(repository_id, target_branch, state)`

`reviews(pull_request_id, reviewed_commit_id)`

`status_checks(pull_request_id, commit_id, status)`

These indexes are relevant because merge evaluation repeatedly filters by Pull Request, current commit, reviewer, and status.

In a high-volume repository platform, merge evaluation should also consider transaction isolation, concurrent updates, event durability, and caching rather than relying solely on application-memory state.

---

## Common Design Mistakes

### Using Strategy as a collection of unrelated conditionals

A Strategy should represent a coherent policy or algorithm. Splitting every individual boolean check into a separate strategy class would add unnecessary indirection.

The examples instead use a strategy for a meaningful policy boundary such as development versus protected production merging.

### Putting all event consumers inside the Pull Request service

Direct calls such as `audit.log()`, `metrics.record()`, and `notifications.send()` would tightly couple the service to every consumer.

Observer removes that direct dependency.

### Treating Observer as a replacement for durable messaging

An in-memory Observer is not automatically a reliable distributed event system.

Process failure, retries, ordering, duplication, persistence, and delivery guarantees require additional infrastructure in production systems.

### Treating an Adapter as business policy

The Adapter should translate an interface or representation.

The external CI adapter converts build results into status checks. It should not decide whether the Pull Request is allowed to merge. That responsibility belongs to the governance policy.

### Counting every review as an approval

A review can be a comment or a request for changes.

Approval must be represented explicitly.

### Ignoring the reviewed commit

An approval against an older commit can become stale when the Pull Request changes.

The examples deliberately attach decisions to commits to make that distinction explicit.

### Failing open on unknown status

An unavailable CI result should not silently become success.

The Adapter maps unknown information to `PENDING`, allowing the merge strategy to block until reliable evidence is available.

---

## Practical Architectural Boundary

A clean dependency direction for this domain is:

`External CI -> Adapter -> StatusProvider -> Governance Service -> Strategy`

and independently:

`Governance Service -> Event Bus -> Observers`

The Pull Request domain model remains unaware of the external CI provider and unaware of individual event consumers.

The Strategy knows how to evaluate domain state but does not need to know how status data was obtained.

The Adapter knows how to translate an external system but does not need to know whether the Pull Request will ultimately be merged.

Observers know how to react to events but do not control the core merge policy.

This separation keeps the three patterns technically distinct while allowing them to cooperate inside one repository governance system.
