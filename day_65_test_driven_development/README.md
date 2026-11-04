# Test-Driven Development: Red-Green-Refactor

## 1. Technical Scope

This project implements Test-Driven Development (TDD) through executable examples in Python, JavaScript, C++17, Java 17, and PostgreSQL.

The central development method is the Red-Green-Refactor cycle:

- **Red:** Write a test that describes required behavior and verify that it fails for the expected reason.
- **Green:** Implement the smallest change necessary to make the test pass.
- **Refactor:** Improve the internal structure without changing externally observable behavior.

The implementations also model repository governance to demonstrate how tests participate in a wider software delivery process.

The five implementations provide different engineering perspectives:

| Language | Primary implementation |
|---|---|
| Python | Order-processing service and executable unit tests |
| JavaScript | Asynchronous test runner and event-driven governance evaluation |
| C++17 | Repository governance and merge-eligibility engine |
| Java 17 | Enterprise repository governance with domain records and services |
| PostgreSQL | Relational TDD, review, policy, and merge workflow |

## 2. Test-Driven Development Concepts

### 2.1 Red

The Red stage begins with a behavioral requirement.

For example, an order-processing system may require that an order cannot be created without at least one item.

The test describes the expected result before the implementation is written.

A correct Red result requires more than a failed test. The failure must demonstrate the missing or incorrect behavior.

A test that fails because of an unrelated syntax error, unavailable dependency, incorrect fixture, or broken environment does not establish a valid Red stage.

The developer should verify:

- The test is discovered.
- The test reaches the intended behavior.
- The failure is caused by the missing requirement.
- The assertion expresses the expected result accurately.

### 2.2 Green

Green means that the test passes after implementing the minimum required behavior.

The implementation should avoid unnecessary functionality.

For example, if a test requires rejecting an empty order, the implementation should enforce that condition without introducing an unrelated order-management framework.

The objective is to establish correct behavior through executable evidence.

### 2.3 Refactor

Refactoring changes internal implementation without changing externally observable behavior.

Typical refactoring operations include:

- Extracting repeated logic into functions.
- Improving class responsibilities.
- Replacing duplicated validation with shared rules.
- Simplifying conditional statements.
- Improving naming.
- Separating domain logic from infrastructure.
- Reducing unnecessary dependencies.

The existing test suite must pass after each behavior-preserving refactoring.

If refactoring changes externally observable behavior, the change requires an appropriate test and should not be treated as a purely structural modification.

## 3. TDD Cycle and State Management

The intended workflow is:

RED
 |
 v
Write a failing behavioral test
 |
 v
GREEN
 |
 v
Implement minimum required behavior
 |
 v
REFACTOR
 |
 v
Improve internal design
 |
 v
Run regression tests
 |
 +------> Begin the next RED stage

The cycle is repeated for individual behaviors.

A complete feature may contain several smaller TDD cycles.

The Python implementation uses `unittest` to exercise order creation, price calculations, discount validation, and order-state transitions.

The JavaScript, C++17, and Java 17 implementations explicitly model TDD stage transitions and reject invalid transitions.

The PostgreSQL implementation stores stage history and enforces transition conditions through a database trigger.

## 4. Test Design and Test Execution

### 4.1 Unit Tests

Unit tests examine individual functions, methods, or domain components.

Examples include:

- Validating an order quantity.
- Calculating an order total.
- Checking a discount percentage.
- Counting eligible approvals.
- Rejecting invalid workflow transitions.

Unit tests should have a limited scope and should avoid unnecessary dependence on external systems.

### 4.2 Integration Tests

Integration tests examine interactions between components.

Examples include:

- Database persistence combined with application validation.
- An API request that invokes several services.
- A repository workflow that combines reviews and status checks.
- A payment service that interacts with a transaction processor.

The supplied implementations focus primarily on unit and domain-level integration behavior. They do not claim to execute external repository platforms or payment systems.

### 4.3 Regression Tests

Regression tests preserve previously verified behavior.

A regression test should remain in the suite after the defect it identifies has been corrected.

This prevents an earlier defect from silently returning during later development.

### 4.4 Boundary and Negative Tests

Boundary tests examine values at the limits of permitted input.

The Python order service tests include:

- Zero quantity.
- Boolean quantity.
- Negative price.
- Non-finite monetary values.
- Excessive decimal precision.
- Negative discounts.
- Discounts above 100%.

Negative tests establish that invalid operations are rejected through defined exceptions rather than producing unpredictable behavior.

### 4.5 Test Isolation

A test should not depend on another test having executed first.

The Python implementation uses `setUp()` to construct fresh test objects.

The other implementations use independent test scenarios and explicit domain instances.

Database tests should use controlled transactions or isolated test schemas to prevent test data from leaking between executions.

## 5. Python Implementation

**File:** `tdd_workflow.py`

### 5.1 Domain Model

The Python implementation models an order-processing service.

Its primary domain objects are:

- `OrderItem`
- `Order`
- `OrderService`
- `OrderStatus`

The `OrderItem` dataclass validates product identifiers, quantities, and monetary values.

The `Order` dataclass stores immutable item collections while allowing controlled status transitions.

### 5.2 Decimal Arithmetic

Financial calculations use `Decimal` rather than binary floating-point arithmetic.

For example, the total for two products is calculated as:

- Two laptops at 50,000.00 each.
- Three mice at 1,000.00 each.
- Total: 103,000.00.

The discount function validates its input and returns a two-decimal result.

This avoids common floating-point representation problems in financial calculations.

### 5.3 State Transitions

The order service supports:

| Current state | Operation | Result |
|---|---|---|
| CREATED | Pay | PAID |
| CREATED | Cancel | CANCELLED |
| PAID | Pay | Rejected |
| PAID | Cancel | Rejected |
| CANCELLED | Cancel | Rejected |

State-transition exceptions make invalid behavior explicit.

### 5.4 Test Execution

The test suite uses `unittest.TestCase`.

The custom result and runner classes record successful tests, failures, and execution errors.

The report contains:

- Total tests.
- Passed tests.
- Failed tests.
- Execution errors.
- Overall success status.

The report is serialized to JSON through a temporary file followed by atomic replacement.

This prevents consumers from reading a partially written report.

### 5.5 Running the Program

Execute:

`python tdd_workflow.py`

The process returns exit code `0` when all tests pass and `1` when the suite fails.

## 6. JavaScript Implementation

**File:** `tdd_workflow.js`

The JavaScript implementation focuses on asynchronous execution, event-driven reporting, and merge-policy evaluation.

### 6.1 Asynchronous Test Runner

`TestRunner` extends Node.js `EventEmitter`.

It maintains registered tests in a `Map`, preventing duplicate test names.

Each test is represented by a `TestCase` containing:

- A unique identifier.
- A test name.
- An execution function.
- A timeout.
- A result status.
- Execution duration.
- Failure information.

The runner supports bounded concurrency.

A fixed number of workers retrieve tests from a shared queue. This limits simultaneous execution and prevents the runner from creating an unrestricted number of concurrent tasks.

### 6.2 Promise-Based Execution

Tests may return ordinary values or promises.

The runner uses `Promise.resolve()` to support both synchronous and asynchronous functions.

`Promise.race()` enforces the configured timeout.

A timed-out test is recorded as failed.

A timeout does not necessarily terminate the underlying asynchronous operation. Production systems should use cancellable operations, cooperative cancellation, or isolated processes where actual termination is required.

### 6.3 Event-Driven Reporting

The runner emits events when tests are registered and completed.

This separates execution from reporting.

A reporting service can listen for completion events without modifying the internal test-execution mechanism.

### 6.4 Governance Evaluation

The `ChangeSet` class models:

- Source and target branches.
- Commits.
- Review decisions.
- Automated checks.
- Unresolved conversations.
- Base-branch synchronization.

`MergePolicyEngine` evaluates repository-level merge conditions.

This separates the review decision from the final authorization to merge.

### 6.5 TDD Stage Tracking

`TddCycle` validates permitted transitions.

It does not allow a transition into GREEN or REFACTOR without passing-test evidence.

The implementation records stage history and increments its implementation version during refactoring.

### 6.6 Running the Program

Execute:

`node tdd_workflow.js`

The program uses Node.js standard-library modules and requires no npm installation.

## 7. C++17 Implementation

**File:** `tdd_workflow.cpp`

The C++ implementation emphasizes explicit domain modeling, strong typing, and repository governance.

### 7.1 Domain Structures

The implementation defines:

- `Commit`
- `Review`
- `StatusCheck`
- `Branch`
- `ProtectionPolicy`
- `PullRequest`
- `EligibilityResult`

Enumerations represent review decisions, check results, merge strategies, and pull-request states.

This prevents arbitrary string values from being used for controlled workflow states.

### 7.2 Pull Request State

A pull request maintains separate information about:

- Its source branch.
- Its target branch.
- Its proposed commits.
- Review decisions.
- Status checks.
- Unresolved conversations.
- Synchronization state.

The proposed changes are not identical to the current state of either branch.

A changeset represents the commits proposed for integration. The source branch can continue changing while the target branch also advances.

### 7.3 Stale Approvals

When a new commit is added, existing approvals are marked stale.

A stale approval is excluded from the valid approval count.

This is important because an approval applies to the changes that were reviewed. A subsequent commit may introduce behavior that the reviewer has not evaluated.

The model uses a simplified invalidation policy. Real repository platforms may support more configurable rules for dismissing stale approvals.

### 7.4 Merge Eligibility

`GovernanceEngine` evaluates:

- Pull-request state.
- Commit availability.
- Target branch protection.
- Required approvals.
- Requested changes.
- Required status checks.
- Unresolved conversations.
- Base-branch synchronization.
- Linear-history requirements.
- Administrator bypass authorization.

The engine returns a structured eligibility result containing failure reasons.

A merge is rejected when a mandatory condition is not satisfied.

### 7.5 Merge Strategies

Three strategies are modeled:

| Strategy | Meaning |
|---|---|
| Merge commit | Combines branch histories through a merge commit |
| Squash | Combines proposed changes into one target-branch commit |
| Rebase | Replays commits onto an updated base |

The program models strategy selection and merge eligibility. It does not implement a complete Git object database or actual Git merge algorithms.

### 7.6 STL Usage

The implementation uses:

- `vector` for ordered commits and test results.
- `map` for reviewer and status-check lookup.
- `set` for unique unresolved conversations and required checks.
- `find_if` for duplicate detection.
- `any_of` for review-policy evaluation.
- `count_if` for test-result aggregation.

For \(n\) commits, duplicate detection through a linear vector search is \(O(n)\) per insertion.

A hash-based container would provide average \(O(1)\) lookup and is appropriate for repositories with large changesets.

## 8. Java 17 Implementation

**File:** `TddWorkflow.java`

The Java implementation models an enterprise repository-governance service.

### 8.1 Domain-Driven Structure

The application separates:

- Domain records.
- Branch objects.
- Pull-request aggregates.
- Branch protection policies.
- Merge eligibility services.
- TDD stage tracking.
- Test execution.

Java records represent immutable values such as commits, reviews, and eligibility results.

Mutable workflow state remains inside the relevant domain objects.

### 8.2 Pull Request Aggregate

The `PullRequest` class controls modifications to its commits, reviews, checks, and conversations.

Its methods validate operations before changing state.

For example:

- A draft must contain commits before opening.
- A closed request cannot be modified.
- A reviewer must be eligible.
- A reviewer must have been requested before submitting a decision.
- A merged request cannot be modified.
- A new commit invalidates existing approvals.

These controls keep related business rules within the domain object.

### 8.3 Immutable Review Records

The `Review` record represents an individual review decision.

Operations such as marking a review stale or dismissing it produce a new record.

This avoids modifying an existing immutable review value.

### 8.4 Merge Eligibility Service

`MergeEligibilityService` performs policy evaluation independently of the pull-request aggregate.

Its result identifies:

- Whether merging is allowed.
- How many approvals remain valid.
- Which policy requirements have failed.

The merge operation calls the evaluation service before changing the request state.

This design avoids treating the existence of an approval as automatic permission to merge.

### 8.5 Administrator Bypass

Administrator bypass is explicitly represented in the policy.

A bypass is accepted only when the configured policy permits it.

The example does not treat administrative identity as automatic permission to ignore every restriction.

Production governance should record the identity, reason, timestamp, and affected policy for each bypass.

### 8.6 Java 17 Features

The implementation uses:

- Records.
- Enums.
- Immutable collection copies.
- Streams.
- Lambdas.
- Switch expressions.
- Generic collections.
- Custom exceptions.
- Explicit service classes.

### 8.7 Running the Program

Compile:

`javac TddWorkflow.java`

Execute:

`java TddWorkflow`

No third-party dependencies are required.

## 9. PostgreSQL Implementation

**File:** `tdd_workflow.sql`

The PostgreSQL implementation stores development and repository-governance information in a relational schema named `tdd_lab`.

### 9.1 Relational Domain Model

The principal relationships are:

Repository
  |
  +-- Repository Users
  |
  +-- Branches
  |     |
  |     +-- Branch Commits
  |
  +-- Commits
  |
  +-- TDD Cycles
  |     |
  |     +-- TDD Stage History
  |     +-- Test Cases
  |           |
  |           +-- Test Executions
  |
  +-- Pull Requests
        |
        +-- Pull Request Commits
        +-- Review Requests
        +-- Reviews
        +-- Review Conversations
        |     |
        |     +-- Review Comments
        +-- Status Checks
        +-- Merge Audit

Branch Protection Policies are associated with target branches and define the conditions required for integration.

### 9.2 Primary and Foreign Keys

Primary keys uniquely identify records.

Foreign keys enforce relationships between:

- Repositories and branches.
- Repositories and users.
- Branches and commits.
- Pull requests and changeset commits.
- Pull requests and reviews.
- Reviews and requested reviewers.
- Pull requests and status checks.
- Branches and protection policies.

Composite foreign keys ensure that branch and user references belong to the same repository.

### 9.3 TDD Stage History

`tdd_cycles` stores the current development stage.

`tdd_stage_history` records changes to the stage.

The `validate_tdd_stage_transition()` trigger enforces permitted transitions.

The database checks the latest execution of each active test case before allowing a transition into GREEN or REFACTOR.

This makes the database responsible for enforcing part of the TDD workflow rather than relying exclusively on application-level validation.

### 9.4 Test Execution Records

The `test_executions` table stores individual test runs.

Each record contains:

- Test case.
- Implementation version.
- Execution status.
- Duration.
- Error information.
- Execution timestamp.
- Executing user.

The schema retains historical results rather than replacing earlier executions.

This supports regression analysis and performance comparisons.

### 9.5 Pull Request Changesets

`pull_requests` stores the relationship between a source branch and a target branch.

`pull_request_commits` stores the proposed commits.

The changeset is distinct from the current branch state.

A pull request may therefore require synchronization when the target branch advances.

The `base_synchronized` field represents whether that condition has been satisfied.

### 9.6 Code Reviews

`review_requests` records requested reviewers.

`reviews` stores their decisions.

A review decision can be:

- APPROVED
- CHANGES_REQUESTED
- COMMENTED

The schema also tracks:

- Reviewer eligibility at submission.
- Stale approvals.
- Dismissed reviews.
- Review timestamps.

The review-request trigger rejects inactive or ineligible reviewers and prevents review requests against non-open pull requests.

### 9.7 Review Conversations

A review conversation represents a discussion associated with proposed changes.

`review_conversations` stores the file path, optional line number, resolution status, and timestamps.

`review_comments` stores individual messages.

A conversation can contain multiple comments.

The conversation requirement is evaluated separately from the number of approvals.

### 9.8 Automated Status Checks

`status_checks` records automated validation results.

Examples include:

- Unit tests.
- Integration tests.
- Security scans.

The status constraint ensures that pending checks do not have a completion timestamp and completed checks do.

The branch protection policy identifies which checks are mandatory.

### 9.9 Branch Protection

`branch_protection_policies` stores repository-level enforcement settings.

`policy_required_checks` stores the mandatory automated checks associated with each policy.

The schema models:

- Required approval counts.
- Required status checks.
- Conversation resolution.
- Linear history.
- Base synchronization.
- Administrator bypass.
- Administrator enforcement.

Branch configuration independently records direct-push, force-push, and deletion restrictions.

### 9.10 Merge Eligibility

`evaluate_merge_eligibility()` evaluates the current state of a pull request against its target branch policy.

It returns:

| Field | Meaning |
|---|---|
| `eligible` | Whether the merge conditions are satisfied |
| `valid_approvals` | Number of eligible, current approvals |
| `reasons` | Conditions preventing a merge or documenting an authorized bypass |

The function evaluates the review state and automated checks independently.

A successful review does not override a failed mandatory status check.

### 9.11 Transactional Merge

`merge_pull_request()` performs merge eligibility evaluation and records the final merge.

It uses row locking to reduce concurrent modification risks.

The pull request state and merge audit record are written within the same transaction.

If an operation fails, PostgreSQL can roll back the transaction and preserve consistency.

### 9.12 Reporting Views

The SQL implementation defines two reporting views.

**`test_execution_summary`**

Provides:

- Test executions.
- Passed executions.
- Failed executions.
- Average execution duration.

**`pull_request_review_summary`**

Provides:

- Pull-request status.
- Valid approvals.
- Unresolved conversations.
- Failed checks.

The views provide reusable reporting structures without duplicating aggregation queries.

### 9.13 Indexing Strategy

Indexes support common lookup operations:

- Repository users by repository and eligibility.
- Commits by repository and timestamp.
- Test executions by test case and execution time.
- Failed test executions through a partial index.
- Pull requests by target branch and status.
- Reviews by pull request and approval state.
- Unresolved review conversations.
- Status checks by pull request and result.

Index selection should be reviewed against actual query plans and data volume.

Indexes improve selected read operations but introduce storage requirements and additional write costs.

## 10. Pull Requests, Code Review, Approvals, and Branch Protection

These concepts operate at different levels of the repository development process.

### 10.1 Pull Requests

A Pull Request (PR) is the workflow for proposing changes from a source branch into a target branch.

A typical lifecycle is:

1. Create a source branch.
2. Commit changes.
3. Open a draft pull request.
4. Synchronize with the target branch when necessary.
5. Request reviewers.
6. Execute automated checks.
7. Address review feedback.
8. Satisfy merge conditions.
9. Merge or close the request.

A draft PR communicates that work is not ready for final review or integration.

A PR changeset describes the proposed integration. It does not mean that the source or target branch has already changed.

A PR can be reopened after closure when repository policy and workflow permit it.

### 10.2 Code Review

Code Review evaluates the technical quality of proposed changes.

Reviewers examine:

- Functional correctness.
- Security.
- Maintainability.
- Error handling.
- Performance.
- Test adequacy.
- Compatibility.
- Architectural consistency.

Inline comments identify specific concerns within a proposed change.

Review discussions can involve multiple comments and responses.

A requested-change decision indicates that the reviewer identified issues requiring attention.

A review conversation should be resolved when the concern has been addressed or otherwise appropriately closed.

Code Review evaluates changes. It does not independently enforce every repository merge restriction.

### 10.3 Approvals

An approval is an explicit review decision.

It indicates that an eligible reviewer accepts the reviewed changes under the applicable review process.

Approval eligibility depends on repository policy.

An approval may become stale when new commits change the proposed changeset.

It may also be dismissed when the applicable review rules or administrative actions require its removal from consideration.

The number of approvals required is determined by repository governance.

An approval contributes to merge eligibility but does not independently guarantee permission to merge.

### 10.4 Branch Protection

Branch Protection defines repository-level restrictions on changes to important branches.

Typical controls include:

- Required reviews.
- Required status checks.
- Direct-push restrictions.
- Force-push restrictions.
- Branch deletion restrictions.
- Conversation resolution.
- Linear-history requirements.
- Merge restrictions.
- Administrator enforcement.
- Authorized bypass mechanisms.

The exact controls depend on the repository platform and its configuration.

Branch protection evaluates whether a proposed change satisfies the configured conditions before integration.

### 10.5 Relationship Between the Four Areas

| Mechanism | Primary responsibility |
|---|---|
| Pull Request | Proposes changes |
| Code Review | Evaluates proposed changes |
| Approval | Records a review decision |
| Branch Protection | Enforces repository-level merge conditions |

The relationship can be expressed as:

Pull Request
    |
    v
Code Review
    |
    v
Approval Decisions
    |
    +------ Automated Status Checks
    |
    +------ Conversation Resolution
    |
    +------ Branch Synchronization
    |
    v
Branch Protection Evaluation
    |
    v
Merge Eligibility
    |
    v
Merge or Rejection

These mechanisms are related but not interchangeable.

## 11. Failure Handling

A reliable TDD workflow must distinguish between a failed test and a failure in the testing infrastructure.

| Failure | Required handling |
|---|---|
| Assertion failure | Record failed behavior |
| Test timeout | Record timeout and investigate execution |
| Invalid fixture | Correct test data |
| Test discovery failure | Correct test configuration |
| Missing required check | Block merge |
| Stale approval | Obtain a fresh review |
| Ineligible reviewer | Reject review request |
| Unresolved discussion | Resolve the conversation |
| Outdated source branch | Synchronize with target |
| Invalid state transition | Reject the operation |
| Unauthorized bypass | Reject merge |

A test runner should retain failure details rather than recording only a Boolean result.

## 12. Security Considerations

### 12.1 Test Isolation

Tests should not share mutable state unintentionally.

Temporary databases, isolated test schemas, and controlled fixtures reduce interference.

### 12.2 Sensitive Test Data

Test fixtures should avoid production credentials and unnecessary personal information.

Secrets should be provided through controlled configuration rather than committed to source repositories.

### 12.3 Test Execution Security

Test execution can involve untrusted code.

A production test service should consider:

- Process isolation.
- Execution time limits.
- Memory limits.
- Restricted filesystem access.
- Network restrictions.
- Controlled environment variables.
- Dependency verification.

### 12.4 Repository Governance

Approval identity and status-check results must be protected against unauthorized modification.

Merge decisions should be auditable.

Administrator bypass should be restricted and recorded.

### 12.5 Database Security

The SQL schema demonstrates integrity constraints and workflow enforcement.

A production deployment should also apply:

- Role-based access control.
- Least-privilege database permissions.
- Restricted function execution.
- Secure connection configuration.
- Audit retention.
- Parameterized application queries.

Database constraints do not replace application authentication or authorization.

## 13. Performance and Scalability

TDD introduces execution overhead, particularly when the test suite grows.

A practical test strategy separates tests by execution cost.

| Test category | Typical execution frequency |
|---|---|
| Unit tests | Every relevant code change |
| Integration tests | During feature validation and CI |
| Regression tests | Before integration |
| Security tests | According to risk and release policy |
| Performance tests | At defined validation milestones |

### 13.1 Parallel Execution

Independent tests can execute concurrently.

The JavaScript implementation uses bounded concurrency to limit resource consumption.

Parallel tests must not compete over shared mutable fixtures or use the same external resources without isolation.

### 13.2 Test Selection

Large systems can use dependency-aware test selection.

A change to a database repository should prioritize tests covering the affected repository and its dependent services.

Selective testing should not eliminate the full regression suite from appropriate release gates.

### 13.3 Test Duration

Execution duration should be monitored over time.

Unexpected increases may indicate:

- Additional database operations.
- Network dependence.
- Inefficient algorithms.
- Excessive fixture initialization.
- Resource contention.

### 13.4 Database Query Performance

The PostgreSQL implementation uses indexes on common filtering and joining columns.

For large datasets, query plans should be examined using `EXPLAIN ANALYZE`.

Historical test records can grow substantially, so archival and retention policies are important.

## 14. Limitations and Design Trade-offs

The implementations are educational domain models rather than complete replacements for production testing frameworks or repository platforms.

| Implementation | Important limitation |
|---|---|
| Python | Uses a local unit-test suite without external infrastructure |
| JavaScript | Timeout does not forcibly terminate the underlying asynchronous task |
| C++17 | Models governance but does not manipulate actual Git objects |
| Java 17 | Uses an in-memory domain model rather than a persistent enterprise service |
| PostgreSQL | Models a simplified repository workflow and approval policy |

The repository models use simplified approval invalidation rules.

Actual platforms can support more sophisticated rules involving commit changes, review dismissal, reviewer identity, policy exceptions, and branch-specific requirements.

The PostgreSQL stage trigger also represents a simplified test-evidence policy. A production system should account for concurrent test executions, execution provenance, test selection, and the exact implementation version being validated.

## 15. Execution Reference

| File | Command |
|---|---|
| Python | `python tdd_workflow.py` |
| JavaScript | `node tdd_workflow.js` |
| C++17 | `g++ -std=c++17 -O2 -Wall -Wextra -pedantic tdd_workflow.cpp -o tdd_workflow` followed by `./tdd_workflow` |
| Java 17 | `javac TddWorkflow.java` followed by `java TddWorkflow` |
| PostgreSQL | Execute `tdd_workflow.sql` in a dedicated PostgreSQL database |

The source files require no third-party programming-language dependencies.

The SQL implementation requires PostgreSQL with support for identity columns, JSONB, PL/pgSQL, filtered aggregates, and the other PostgreSQL features used in the script.
