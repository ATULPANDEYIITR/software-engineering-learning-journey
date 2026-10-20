# SQL Fundamentals: SELECT, INSERT, UPDATE, DELETE

## Scope

This learning artifact uses SQL CRUD operations inside a realistic repository-governance model. The four database operations are taught through repository development data rather than unrelated employee or product examples.

The domain separates four related mechanisms:

| Area | Role in the workflow |
|---|---|
| Pull Request | Proposes a set of changes from a source branch to a target branch |
| Code Review | Evaluates the proposed changes through review states and discussions |
| Approvals | Records review decisions that can satisfy required-review policies |
| Branch Protection | Enforces repository-level conditions before a protected branch can receive a merge |

The central relationship is:

`Pull Request → Code Review → Approval Decision → Branch Protection → Merge Eligibility`

The SQL implementation uses these concepts as relational data so that `SELECT`, `INSERT`, `UPDATE`, and `DELETE` can be understood in a practical workflow.

## Relational Model

The PostgreSQL implementation contains these principal entities:

| Table | Purpose |
|---|---|
| `repositories` | Repository identity and default branch |
| `users` | Authors and reviewers |
| `branches` | Source and target branches with commit heads |
| `pull_requests` | Proposed changes and their lifecycle state |
| `commits` | Individual changesets |
| `pull_request_commits` | Associates commits with pull requests in sequence |
| `reviews` | Review decisions and review discussions |
| `review_comments` | Inline review comments and resolution state |
| `status_checks` | Automated validation results |
| `branch_protection` | Protected-branch governance rules |
| `required_status_checks` | Checks required by a protected branch |

The foreign-key relationships prevent orphaned review, commit-association, and status-check records.

## SELECT

`SELECT` retrieves existing repository information without changing it.

The SQL artifact uses it to retrieve open pull requests together with:

- Repository name
- Source branch
- Target branch
- Author
- Pull-request state
- Draft status

A second query aggregates commits and approvals. This demonstrates that retrieval can combine related tables instead of treating each table as an isolated data source.

A CTE evaluates required status checks. It separates the required checks from their observed results and determines whether all required checks are passing.

The JavaScript and Python implementations provide equivalent retrieval concepts through filtered collections and repository methods, while the C++ and Java versions focus more heavily on merge-policy evaluation.

## INSERT

`INSERT` creates new persistent records.

The SQL script inserts:

- A repository
- Users
- Branches
- Branch-protection rules
- Required status checks
- Commits
- Pull-request commit associations
- Reviews
- Status checks
- A review comment

The relationships are important. A review cannot reference a nonexistent pull request, and a pull-request changeset cannot reference a nonexistent commit.

The source branch and target branch are distinct because a pull request represents a proposed transition between branches.

## UPDATE

`UPDATE` modifies existing records.

The SQL example updates a pull-request title while requiring that the pull request remain open. It also updates a status check inside a transaction.

An update should normally use a restrictive `WHERE` clause. Without an appropriate condition, a single statement can modify every matching row in a table.

The source implementations also validate state transitions. For example, a merged pull request cannot simply be changed back into an arbitrary earlier state.

## DELETE

`DELETE` removes rows.

The SQL model deliberately demonstrates deletion on a closed temporary pull request rather than deleting merged history. Repository governance normally treats merged history as an auditable record.

Foreign-key `ON DELETE CASCADE` rules allow dependent records to be removed when a parent pull request is legitimately deleted. This prevents orphaned reviews, status checks, review comments, and commit-association records.

The implementation does not treat deletion as a substitute for changing workflow state. Closing a pull request and deleting a pull request have different meanings.

## Pull Request Lifecycle

A pull request connects two branches:

`feature/sql-crud ───────────────→ main`

The source branch contains the proposed changes. The target branch is where the changes are intended to land.

The modeled lifecycle is:

`OPEN → CLOSED`

or:

`OPEN → MERGED`

A draft pull request remains part of the proposal workflow but is not eligible for merging under the implemented protection policy.

The model also records commits belonging to the pull request. A changeset therefore has a concrete representation instead of being reduced to a title or description.

Base-branch synchronization is represented by changing the source branch's commit relationship or by recording synchronization activity in the non-SQL implementations. If the target branch advances while a pull request is open, the source branch may need to incorporate those changes before merge eligibility can be determined reliably.

Merge conflicts are a source-control condition rather than a basic SQL CRUD operation. The governance engines therefore treat merge eligibility as a policy decision and do not pretend that a database update itself resolves source-control conflicts.

## Code Review

Code review is distinct from the pull-request proposal mechanism.

A review belongs to a pull request and has one of these states:

| Review state | Meaning |
|---|---|
| `APPROVED` | Reviewer accepts the proposed changes |
| `CHANGES_REQUESTED` | Reviewer identifies changes required before acceptance |
| `COMMENTED` | Reviewer provides discussion without approving or rejecting the proposal |

Inline comments are represented separately from review records. Each comment identifies a file and line, contains review text, and has a resolution state.

This distinction prevents an approval decision from being confused with the individual discussion comments that led to that decision.

The implementations reject self-approval because the author should not satisfy an independent-review requirement by approving their own changes.

## Approvals

An approval is a specific review decision, not merely evidence that somebody opened a pull request.

The governance model counts unique reviewers whose review state is `APPROVED`.

This matters because repeated approvals from the same reviewer should not automatically satisfy a policy requiring multiple independent reviewers.

For example, a policy requiring two approvals is satisfied by:

`alice → APPROVED`

`bob → APPROVED`

but not by:

`alice → APPROVED`

`alice → APPROVED`

The SQL aggregation uses distinct reviewer identities to represent this rule.

The model also allows review states to change as development continues. In a production system, approval freshness and dismissal rules would normally be tied to changes to the pull request's commits and repository policy. The learning implementation keeps the rule explicit rather than hiding it inside a generic status field.

## Branch Protection

Branch protection operates at the repository-governance level.

The sample `main` branch requires:

- Two approvals
- Passing `unit-tests`
- Passing `sql-validation`
- Conversation resolution
- No direct push
- No force push
- No branch deletion
- No administrator bypass

These requirements are not themselves code-review comments or pull-request fields. They are policies attached to the protected target branch.

The distinction can be represented as:

`Pull Request`
→ proposes the change

`Code Review`
→ evaluates the change

`Approval`
→ records a review decision

`Branch Protection`
→ enforces conditions for merging into the protected branch

## Merge Eligibility

The SQL view `merge_eligibility` combines independent conditions.

A pull request is eligible only when:

- It is open.
- It is not a draft.
- The number of unique approvals meets the policy.
- Every required status check is passing.
- Required review discussions are resolved.

This is intentionally different from saying that an approval itself causes a merge.

An approval contributes one input to the branch-protection decision. The protected branch evaluates the complete policy.

## Python Implementation

The Python program uses domain classes for pull requests, reviews, and branch protection.

`Repository` owns the workflow state and provides operations for creating pull requests, adding commits, recording reviews, changing status checks, evaluating merge eligibility, and merging.

Python dictionaries provide efficient lookup by pull-request number. Sets are used when unique approval identities are required.

Validation is performed before state changes. Invalid branches, empty identifiers, self-approval, invalid review states, and invalid status-check states raise explicit exceptions.

The implementation is deliberately executable without third-party dependencies.

## JavaScript Implementation

The JavaScript implementation uses an event-driven asynchronous store.

`RepositoryStore` uses `Map` objects for keyed repository, pull-request, review, and status-check data. Operations return promises and schedule work through the microtask queue, giving the model an asynchronous API shape suitable for a Node.js service.

The implementation exposes CRUD-oriented methods:

- `insertRepository`
- `insertPullRequest`
- `selectPullRequests`
- `updatePullRequest`
- `insertReview`
- `updateStatusCheck`
- `deletePullRequest`

The policy evaluator then consumes those records to determine merge eligibility.

Deletion is explicitly blocked for merged pull requests, preserving historical repository records.

## C++ Implementation

The C++17 program treats merge eligibility as a governance-engineering problem.

Strongly typed enumerations represent pull-request states, review states, and status-check states.

`GovernanceEngine` owns branches, pull requests, and branch-protection policies. It uses `std::map` for keyed records and `std::set` for required checks and unique approval identities.

The merge evaluator collects independent failure conditions rather than returning only a Boolean. This makes blocked merges diagnosable:

`Merge eligible: no`

can be accompanied by specific reasons such as missing approvals or failing checks.

The design also prevents invalid operations on closed pull requests and rejects author self-approval.

## Java Implementation

The Java 17 implementation models repository governance with records, enums, collections, immutable record values, and explicit service behavior.

`Commit`, `Review`, and `BranchProtectionPolicy` are records because their core data is naturally value-oriented.

`PullRequest` owns its workflow state and associated domain data. `RepositoryService` owns repository-level operations and evaluates branch protection.

`MergeDecision` separates the result of a policy evaluation from the action that performs the merge. This prevents a policy check from being confused with the state transition itself.

Java streams are used for approval evaluation, while sets enforce unique reviewer identities.

## PostgreSQL Constraints

The database is responsible for structural integrity.

Examples include:

- Primary keys for row identity
- Foreign keys for relationships
- Unique constraints for repository names and branch names
- Check constraints for valid text and numeric values
- Enumerated types for controlled workflow states
- Partial indexing for unresolved review comments

The database therefore rejects structurally invalid records even if an application layer contains a programming error.

## Transactions

The SQL script uses a transaction when changing and inspecting a status check.

The important property is atomicity: the statements inside the transaction are treated as one database operation from the perspective of commit or rollback.

Transactions are particularly important when multiple records represent one workflow transition. A production merge process would normally coordinate pull-request state, branch references, audit information, and policy checks within carefully defined transactional boundaries.

## Performance Considerations

The relational implementation indexes the columns used by common workflow queries:

- Pull-request repository and state
- Review pull-request and state
- Status-check pull-request and state
- Unresolved review comments

The unique-reviewer approval calculation requires grouping or distinct aggregation. Its cost grows with the number of reviews associated with a pull request.

The in-memory Python, JavaScript, C++, and Java models use keyed collections so individual pull-request lookup is generally constant-time on average for hash-based structures or logarithmic for ordered maps, depending on the collection.

Database query performance should be evaluated against actual data volume rather than assuming that every index improves performance. Small tables can sometimes be faster with sequential scans.

## Validation and Failure Conditions

The implementations intentionally reject several invalid operations:

- Missing repository names
- Unknown branches
- Identical source and target branches
- Empty commit identifiers
- Invalid review states
- Author self-approval
- Invalid status-check states
- Negative required-review counts
- Merging a closed or already merged pull request
- Merging a draft pull request when policy forbids it
- Merging without sufficient approvals
- Merging with failing or missing required checks
- Deleting merged history

These failures illustrate why CRUD statements should not be treated as unrestricted data manipulation. Repository state has domain rules that must be enforced by both application logic and database constraints where appropriate.

## Security and Governance

CRUD operations can directly alter governance data, so authorization is important in a production system.

A caller capable of executing unrestricted `UPDATE` or `DELETE` statements could bypass application-level assumptions. PostgreSQL deployments should therefore use appropriately scoped roles and privileges.

Branch protection also reduces the risk of unauthorized changes to critical branches by restricting direct pushes and force pushes.

The sample schema models governance conditions but does not implement authentication or PostgreSQL row-level security. Those mechanisms would depend on the surrounding deployment architecture.

## Practical Workflow

A typical controlled change can be represented as:

`INSERT Pull Request`
  
`↓`

`INSERT Commits / Reviews / Status Checks`

`↓`

`SELECT Current Workflow State`

`↓`

`UPDATE Review or Check State`

`↓`

`SELECT Merge Eligibility`

`↓`

`UPDATE Pull Request State to MERGED`

A `DELETE` operation is reserved for records whose removal is explicitly allowed by the domain policy.

This workflow shows the distinction between manipulating data and enforcing meaning: CRUD provides the database operations, while constraints and governance rules determine which operations are valid.
