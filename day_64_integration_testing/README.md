# Integration Testing: Database and API Integration Tests

## Scope

This project models integration testing as part of a repository-development workflow. The implementations use Pull Requests, Code Review, approvals, status checks, and Branch Protection to represent how database and API integration tests are validated before production code is merged.

The central distinction is:

| Mechanism | Primary responsibility |
|---|---|
| Pull Request | Proposes a set of changes from a source branch toward a target branch |
| Code Review | Evaluates the proposed changes |
| Approval | Records a reviewer's explicit review decision |
| Branch Protection | Enforces repository-level conditions before merge |
| Integration tests | Validate interactions between application components, APIs, databases, and related infrastructure |
| Status checks | Report automated validation results against a particular commit |
| Merge eligibility | Determines whether all repository-level conditions are satisfied |

A Pull Request is therefore not itself a test, review, approval, or protection rule. It is the workflow object that connects the proposed changes with these other controls.

## Integration Testing Model

Integration testing verifies interactions between components rather than testing an isolated function in complete isolation.

A database integration test may validate:

- transaction creation
- persistence
- foreign-key enforcement
- rollback behavior
- query results
- constraint violations
- concurrent state changes
- connection failures

An API integration test may validate:

- request validation
- authentication behavior
- HTTP status codes
- serialization
- service-to-database interaction
- transaction boundaries
- error propagation
- idempotency
- authorization

A repository integration workflow can connect these tests to a Pull Request:

```text
Feature Branch
     |
     v
Commits
     |
     v
Pull Request
     |
     +--------------------+
     |                    |
     v                    v
Code Review          Automated Checks
     |                    |
     v                    +--> API Integration Tests
Approvals                 |
                          +--> Database Integration Tests
                          |
                          +--> Security Checks
     |                    |
     +---------+----------+
               |
               v
       Branch Protection
               |
               v
       Merge Eligibility
               |
               v
              Merge
```

## Pull Request Lifecycle

The Python, JavaScript, C++17, Java 17, and PostgreSQL implementations model the principal Pull Request states:

| State    | Meaning                                                                    |
| -------- | -------------------------------------------------------------------------- |
| `draft`  | Work is proposed but not ready for normal merge processing                 |
| `open`   | Changes are actively proposed for review and validation                    |
| `closed` | The proposal is closed without being merged                                |
| `merged` | The proposed changes have passed the required controls and were integrated |

The source branch contains the proposed development state. The target branch contains the repository state into which the changes may eventually be integrated.

A Pull Request captures a changeset through its commits and changed files. It can also contain review decisions, review conversations, automated status checks, and merge information.

Synchronizing a Pull Request with the source branch is important because the proposal can change after review begins. A new commit changes the commit against which current approvals and automated checks must be evaluated.

Draft Pull Requests are deliberately treated as non-mergeable in the implementations. This prevents incomplete work from satisfying ordinary merge conditions.

A closed Pull Request can be reopened in a complete repository implementation. A merged Pull Request is terminal for ordinary lifecycle purposes because its changes have already been integrated.

## Proposed Changes Versus Branch State

A critical integration-testing distinction is the difference between the proposed changes and the state of the branches.

The source branch can receive a new commit after a review decision. The Pull Request must then be synchronized so that its latest proposed commit reflects the new branch state.

The target branch can also advance independently.

```text
Source Branch
A -> B -> C
          |
          +--> Pull Request proposal

Target Branch
A -> D -> E
          |
          +--> protected target state
```

The Pull Request is not simply a permanent copy of either branch. It represents a proposal to combine the source-side changes with the target-side repository state.

This distinction matters for integration testing because an automated result tied to commit `B` does not necessarily validate a later source commit `C`.

## Code Review

Code Review evaluates the proposed changes.

The implementations model reviews with explicit states such as:

- commented
- approved
- changes requested
- dismissed

A review can contain comments and discussions. Comments may remain unresolved until the reviewer or an authorized workflow marks the discussion resolved.

Review quality depends on the scope of the proposed change and the correctness of the review criteria. A reviewer should evaluate behavior, correctness, error handling, security-sensitive operations, transaction boundaries, API contracts, test coverage, and unintended side effects where relevant.

The Code Review object is separate from the Pull Request object.

The Pull Request answers:

> What change is being proposed?

The Code Review answers:

> What did reviewers determine about that proposed change?

A review can become stale when new commits change the proposed code.

## Approvals

An approval is a review decision.

The implementations require approvals to be associated with the latest Pull Request commit. This prevents an approval for an older version of the code from automatically approving a newer version.

For example:

```text
Commit A
  |
  +--> Bob approves
  |
  v
Commit B added
  |
  +--> previous approval becomes stale
  |
  v
New review required
```

The examples also prevent the author from approving their own Pull Request.

Approval count is therefore not merely the number of historical approval records. Merge eligibility requires the appropriate number of current, eligible approvals for the current proposed commit.

Dismissed approvals do not contribute to the current approval count.

## Branch Protection

Branch Protection enforces repository-level governance.

The modeled policies can require:

- a minimum number of approvals
- specific status checks
- resolved review conversations
- restrictions on direct pushes
- restrictions on force pushes
- branch deletion restrictions
- linear history where required
- administrator bypass policy

Branch Protection is different from Code Review. A reviewer may evaluate a change without having authority to alter repository merge enforcement.

Likewise, an approval is not itself a complete merge policy. The approval becomes relevant to merge eligibility because Branch Protection can require a specified number of valid approvals.

A protected branch can therefore reject a Pull Request even when the reviewers approve it if another required condition has failed.

## Status Checks and Integration Tests

The examples treat integration tests as automated status checks.

Representative checks include:

| Check                  | Purpose                                                 |
| ---------------------- | ------------------------------------------------------- |
| `api-integration`      | Validates interaction between API components            |
| `database-integration` | Validates database persistence and transaction behavior |
| `security-scan`        | Validates a repository-level security condition         |

Each status check is associated with a commit SHA.

This prevents an earlier successful test from being treated as proof that a later commit is still valid.

For example:

```text
Commit 2222222
    |
    +--> API test: PASS
    +--> Database test: PASS
    +--> Approval: PASS
    |
    v
Commit 3333333
    |
    +--> Source changed
    |
    +--> old validation is no longer sufficient
```

This is an important property of integration testing in repository workflows.

## Database Integration Testing

The PostgreSQL implementation models a repository-development database rather than an application database alone.

The relational structure includes:

- repositories
- branches
- commits
- Pull Requests
- Pull Request commits
- changed files
- reviewers
- reviews
- review comments
- status checks
- Branch Protection policies
- required status checks

Foreign keys enforce relationships between these entities.

For example, a review cannot exist without a corresponding Pull Request and reviewer. A Pull Request cannot reference nonexistent branches. A required status check must belong to an existing Branch Protection policy.

The schema also uses check constraints for conditions such as non-empty commit messages, valid review counts, valid branch relationships, and valid review-comment line numbers.

## API Integration Testing

The Python and JavaScript models demonstrate how automated API-oriented integration checks can participate in the repository workflow.

The test scenario treats API validation and database validation as separate automated conditions:

```text
Pull Request
    |
    +--> API Integration
    |       |
    |       +--> request/service behavior
    |
    +--> Database Integration
            |
            +--> persistence/transaction behavior
```

This separation makes failures easier to diagnose.

An API integration failure does not imply that the database integration layer is incorrect. Conversely, a successful API test does not prove that every database transaction scenario is correct.

## Python Implementation

The Python implementation uses dataclasses and enums to model repository state.

Important domain types include:

- `Commit`
- `Review`
- `StatusCheck`
- `BranchProtection`
- `Branch`
- `PullRequest`
- `Repository`

The repository service evaluates merge eligibility through several independent conditions.

The integration tests verify:

- successful approval and status-check processing
- stale approvals after a new commit
- failed integration checks
- distinction between Pull Request state and changed-file state

Python's `unittest` framework provides executable verification without external dependencies.

The implementation uses sets for changed files and approval identities, giving efficient membership checks and preventing duplicate approval counting.

## JavaScript Implementation

The JavaScript implementation uses Node.js standard-library assertions and an event-oriented repository model.

The `Repository` class maintains:

- branches
- Pull Requests
- protection policies
- workflow events

The event collection records important transitions such as Pull Request creation, synchronization, review submission, and merging.

This gives the JavaScript implementation a different engineering perspective from the Python dataclass model.

The asynchronous ecosystem of Node.js is not required for the deterministic domain simulation itself, but the model is structured around events so that real API clients or CI adapters can later consume equivalent state transitions.

## C++17 Implementation

The C++17 implementation emphasizes explicit domain structures and deterministic merge evaluation.

It uses:

- `struct`
- `enum class`
- `std::map`
- `std::set`
- `std::vector`
- exceptions
- explicit eligibility results

The merge engine collects failure reasons rather than returning only a Boolean result.

This allows a failed merge to explain conditions such as:

- insufficient approvals
- failed checks
- missing checks
- unresolved conversations
- absent changed files
- missing protection policy

The use of sets makes approval identity and required-check membership efficient for the modeled workload.

## Java 17 Implementation

The Java implementation uses an enterprise-oriented domain model.

Java records represent immutable value-oriented entities such as:

- `Commit`
- `StatusCheck`
- `Review`
- `BranchProtection`
- `MergeEligibility`

The `Repository` service coordinates state transitions while the Pull Request object represents domain state.

Java collections and streams are used for current approval evaluation and status-check processing.

The model explicitly distinguishes policy configuration from operational state. This is useful for enterprise governance because a repository can have a stable policy while individual Pull Requests move through different lifecycle states.

## PostgreSQL Implementation

The PostgreSQL implementation provides persistent relational state for the same conceptual workflow.

The schema uses:

- primary keys
- foreign keys
- unique constraints
- check constraints
- indexes
- triggers
- PL/pgSQL functions
- CTEs
- transactions
- reporting queries

The `merge_eligibility` function evaluates repository-level conditions directly from relational state.

The function checks:

1. Pull Request existence
2. Pull Request state
3. draft state
4. Branch Protection presence
5. current approvals
6. reviewer activity
7. required status checks
8. unresolved review discussions
9. changed-file presence

The final transaction demonstrates conditional transition into a merged state.

## Failure Handling

The implementations deliberately model failure rather than assuming successful workflow execution.

Representative failures include:

| Failure                        | Effect                              |
| ------------------------------ | ----------------------------------- |
| Source branch does not exist   | Pull Request creation fails         |
| Source equals target           | Pull Request creation fails         |
| No commits exist               | Pull Request creation fails         |
| Author attempts approval       | Review operation fails              |
| Approval references old commit | Approval becomes stale or dismissed |
| Required check fails           | Merge is rejected                   |
| Required check is missing      | Merge is rejected                   |
| Unresolved discussion exists   | Merge is rejected                   |
| Target lacks protection policy | Merge is rejected                   |
| Pull Request is a draft        | Merge is rejected                   |
| Pull Request is not open       | Merge is rejected                   |

These failures are important because integration testing should verify negative behavior as well as successful behavior.

## Security Considerations

Repository integration workflows can become security controls because merge eligibility determines what code enters protected branches.

Important controls include:

- preventing self-approval
- requiring eligible reviewers
- associating reviews with specific commits
- requiring successful automated checks
- restricting direct pushes
- restricting force pushes
- controlling branch deletion
- separating administrative bypass from ordinary developer permissions
- resolving review conversations before merge

Integration tests should also avoid using production credentials or production databases.

Database integration environments should use isolated credentials, controlled test data, and disposable or resettable state where possible.

API integration tests should validate authentication and authorization behavior without exposing secrets in test output.

## Performance Considerations

The repository models are designed around indexed and set-based lookups.

The PostgreSQL schema includes indexes for:

- Pull Request target branch and state
- reviews by Pull Request, commit, and state
- status checks by Pull Request, commit, and name
- review-comment resolution
- commits by branch and creation time

The application implementations use sets for operations where uniqueness and membership are important.

Merge eligibility can be more expensive in a large repository because it may require evaluating many reviews, comments, checks, files, and policy rules. Database indexes reduce the cost of these lookups.

## Transaction Boundaries

Database integration tests should verify not only successful persistence but also atomic failure behavior.

A representative transaction is:

```text
BEGIN
  |
  +--> evaluate eligibility
  |
  +--> update merge state
  |
COMMIT
```

If a required condition fails, the merge-state transition should not be applied.

This is particularly important when several database records must remain consistent. A partially applied merge state can produce incorrect repository governance data.

## Merge Strategies

The implementations distinguish common merge strategies:

| Strategy     | Main behavior                                                       |
| ------------ | ------------------------------------------------------------------- |
| Merge commit | Creates a new merge commit joining the proposed history             |
| Squash       | Combines the Pull Request changes into a consolidated target commit |
| Rebase       | Applies the proposed commits onto the target history                |

The choice affects commit history and can interact with linear-history requirements.

A merge strategy is therefore a repository integration decision rather than a review decision.

## Review-Related Failure Modes

Several failure modes require explicit treatment:

### Stale approvals

A reviewer approves commit `A`, then commit `B` is added. The approval for `A` cannot automatically validate `B`.

### Failed integration test

An approval may exist while a required API or database integration test fails. Branch Protection still rejects the merge.

### Unresolved discussion

Reviewers may approve the change while a required conversation remains unresolved. The repository policy can still prevent merging.

### Missing check

A check that never ran is different from a successful check. The implementations treat a missing required check as a failure.

### Direct push

A protected branch can prohibit direct pushes even when the developer has repository write access.

### Force push

Force-push restrictions reduce the risk of silently rewriting protected branch history.

## Educational Distinctions

The four repository mechanisms should not be treated as interchangeable.

```text
Pull Request
    = proposal workflow

Code Review
    = evaluation of proposed changes

Approval
    = explicit reviewer decision

Branch Protection
    = repository-level merge enforcement
```

Integration tests operate alongside these mechanisms as automated evidence about the behavior of the proposed changes.

A successful integration test does not automatically constitute an approval.

An approval does not automatically bypass Branch Protection.

A Pull Request does not guarantee that the proposed code has passed integration tests.

Branch Protection does not perform the integration tests itself. It enforces the conditions under which their results become relevant to merge eligibility.

## Practical Workflow

A realistic development sequence represented by the artifacts is:

```text
Create feature branch
       |
       v
Implement API/database changes
       |
       v
Add integration tests
       |
       v
Commit changes
       |
       v
Open Pull Request
       |
       +------> Code Review
       |
       +------> API integration tests
       |
       +------> Database integration tests
       |
       +------> Security checks
       |
       v
Synchronize after new commits
       |
       v
Refresh stale approvals/checks
       |
       v
Evaluate Branch Protection
       |
       v
Merge if eligible
```

This workflow makes the relationship between development changes, human review, automated validation, repository governance, and final integration explicit.

## Limitations

The implementations are deterministic simulations rather than complete implementations of a production Git hosting platform.

They do not implement:

- network transport
- real Git object storage
- authentication infrastructure
- distributed CI workers
- external review services
- real HTTP endpoints
- production database connection pooling
- repository replication
- cryptographic commit verification
- multi-repository dependency graphs

The PostgreSQL implementation models repository governance relationally, but it does not implement a complete Git server.

The application programs similarly model the workflow and integration-testing decisions without contacting a real Git hosting service.

These limitations keep the examples self-contained while preserving the important state transitions, validation rules, failure conditions, and governance relationships.
