# Database Design: Tables, Keys, and Relationships

## Purpose

This project models repository-development governance as a relational database problem.

The central design separates four related mechanisms:

| Mechanism | Database responsibility |
|---|---|
| Pull Request | Stores a proposed change between a source branch and a target branch |
| Code Review | Stores reviewer decisions and review comments against specific commits |
| Approvals | Determines whether current eligible approvals satisfy policy requirements |
| Branch Protection | Stores repository-level rules that control merge eligibility |

The relationship is:

**Pull Request → Code Review → Approval Decision → Branch Protection Evaluation → Merge Eligibility**

A Pull Request is the workflow object. A review evaluates its changes. An approval is a particular review decision. Branch protection defines the conditions that must be satisfied before the proposed change can be merged.

These concepts are deliberately modeled separately rather than represented by one generic status field.

---

## Relational Model

The PostgreSQL implementation uses the following core entities:

| Table | Purpose |
|---|---|
| `repositories` | Repository identity and default branch |
| `users` | Developers, reviewers, and maintainers |
| `branches` | Repository branches |
| `commits` | Immutable commit identities and ancestry |
| `pull_requests` | Proposed changes between source and target branches |
| `pull_request_commits` | Many-to-many relationship between Pull Requests and commits |
| `review_requests` | Reviewers requested for a Pull Request |
| `reviews` | Review decisions associated with commits |
| `review_comments` | Inline or general review discussions |
| `status_checks` | Automated validation results |
| `branch_protection_policies` | Protected-branch governance rules |
| `required_status_checks` | Status checks required by a protection policy |
| `policy_bypass_users` | Explicit policy bypass assignments |

The main foreign-key structure is:

`repositories`  
→ `branches`  
→ `pull_requests`  
→ `pull_request_commits`  
→ `commits`

A Pull Request also connects to:

`review_requests`  
→ `reviews`  
→ `review_comments`

And:

`branch_protection_policies`  
→ `required_status_checks`

This structure prevents review decisions, automated checks, and branch policies from becoming attributes of the wrong entity.

---

## Keys and Relationships

Primary keys use PostgreSQL `BIGSERIAL` identifiers for relational identity.

Natural identifiers remain constrained where they have domain meaning:

- Repository names are unique.
- Usernames are unique.
- Branch names are unique within a repository.
- Commit SHAs are unique within a repository.
- Pull Request numbers are unique within a repository.
- A reviewer can only be requested once for a Pull Request.
- A branch can have only one active default designation.
- A branch-protection policy is unique for a repository and protected branch.

The Pull Request-to-commit relationship uses `pull_request_commits` rather than placing one commit identifier directly on the Pull Request. This represents the fact that a Pull Request contains an ordered changeset.

`commit_position` preserves the order in which commits are associated with the Pull Request.

---

## Pull Request Lifecycle

The database represents Pull Request state explicitly:

`draft → open → merged`

Or:

`draft → open → closed → open`

A merged Pull Request is terminal in the model.

The lifecycle timestamps are maintained by a PostgreSQL trigger:

- `opened_at`
- `closed_at`
- `merged_at`

The trigger ensures that timestamps are created when the corresponding state transition occurs.

A Pull Request cannot contain the same commit twice because the relationship table has a composite primary key.

A Pull Request cannot use the same commit position twice because `(pull_request_id, commit_position)` is unique.

---

## Pull Request Mechanics

A Pull Request contains:

- Source branch
- Target branch
- Author
- Title
- State
- Associated commits
- Requested reviewers
- Reviews
- Status checks
- Review conversations
- Merge strategy

The source branch represents where the proposed changes originate.

The target branch represents the branch into which the changes would be integrated.

The source and target branch identifiers are required to differ.

The implementation does not treat a Pull Request as a simple file comparison. Its database representation captures the changeset, review context, automated checks, and governance relationship necessary for merge evaluation.

### Base-Branch Synchronization

A new commit is associated with the Pull Request when the source branch is updated.

This matters because approvals are associated with specific commits.

If a reviewer approves commit `a100002` and a later commit `a100003` is introduced, the earlier approval is not counted as a current approval.

The SQL view `pull_request_latest_commit` identifies the latest commit associated with each Pull Request.

The approval calculation uses that latest commit.

This provides an explicit database representation of stale approvals.

---

## Code Review

Code review is represented through two related entities:

- `reviews`
- `review_comments`

A review contains:

- Reviewer
- Review state
- Reviewed commit
- Submission timestamp

A review can be:

- `commented`
- `approved`
- `changes_requested`
- `dismissed`

Review comments contain the discussion detail.

A comment may contain:

- Body
- File path
- Line number
- Resolution state
- Creation time

The separation is intentional.

A review represents a review decision or review submission.

A review comment represents a particular discussion item.

This allows one review to contain multiple comments without treating every comment as an independent approval decision.

---

## Review Quality and Scope

The database requires reviews to reference a real commit.

It also requires the reviewer to have been requested for the Pull Request.

A trigger prevents a Pull Request author from submitting their own review.

These constraints enforce important review boundaries at the database layer rather than relying only on application code.

A reviewer can provide a comment without approving the changes.

A reviewer can request changes.

A reviewer can approve a particular commit.

A dismissed review remains historical information but does not qualify as a current approval.

---

## Approvals

Approval is represented by a review whose state is `approved`.

An approval is not treated as a permanent property of the Pull Request.

The current approval calculation considers:

- The reviewer
- Reviewer eligibility
- Requested-reviewer membership
- The Pull Request author
- The latest Pull Request commit
- The review state

The implementation therefore distinguishes:

**Historical approval**

A reviewer approved an earlier commit.

**Current approval**

A reviewer approved the latest commit associated with the Pull Request.

Only current eligible approvals contribute to merge eligibility.

The view `pull_request_approval_status` calculates these values without modifying historical review records.

---

## Stale Approvals

Stale approvals are a consequence of associating reviews with commit identity.

For example:

    a100001 → a100002
                 ↑
              approval

After synchronization:

    a100001 → a100002 → a100003
                             ↑
                        latest commit

The approval attached to `a100002` remains in the database as historical evidence.

It is simply excluded from the current approval count.

A new approval attached to `a100003` becomes eligible.

This approach preserves auditability while preventing old review decisions from silently satisfying a policy intended for newer code.

---

## Branch Protection

Branch protection is modeled independently of Pull Requests and reviews.

`branch_protection_policies` defines repository-level rules for a protected branch.

The example policy for `main` requires:

- Two current approvals
- Successful `unit-tests`
- Successful `security-scan`
- Resolved review conversations
- Linear history
- No direct push
- No force push
- No branch deletion

The policy does not itself contain a Pull Request.

Instead, the policy is evaluated against a Pull Request targeting the protected branch.

This distinction allows multiple Pull Requests to be evaluated against the same governance policy.

---

## Required Status Checks

Required checks are normalized into `required_status_checks`.

The protection policy determines which checks are mandatory.

The `status_checks` table records actual check results for a Pull Request.

This produces a clear separation:

    Branch Protection Policy
            |
            +-- Required Check: unit-tests
            |
            +-- Required Check: security-scan
                        |
                        v
                 Pull Request Results

A check is satisfied only when a corresponding result exists and its status is `passed`.

A missing check is therefore treated as a failure rather than as an implicit success.

---

## Conversation Resolution

Review discussions are stored as review comments.

Each comment has a `resolved` flag.

When branch protection requires conversation resolution, the merge-eligibility view checks for unresolved comments.

This prevents an otherwise fully approved Pull Request from becoming mergeable while review discussions remain unresolved.

The implementation does not confuse conversation resolution with approval.

A discussion can be resolved without producing an approval.

An approval can exist without being the mechanism that resolves every discussion.

---

## Merge Eligibility

The PostgreSQL view `pull_request_merge_eligibility` combines the independent governance conditions.

A Pull Request is eligible only when all required conditions are satisfied.

Conceptually:

    Pull Request is open
            AND
    current approvals >= required approvals
            AND
    all required checks passed
            AND
    all required conversations resolved
            AND
    merge strategy satisfies branch policy
            =
    merge eligible

This is an evaluation result, not a replacement for the underlying records.

The underlying reviews, comments, commits, checks, and policies remain independently queryable.

---

## Merge Strategies

The model recognizes three merge strategies:

| Strategy | Meaning |
|---|---|
| `merge_commit` | Integrates the Pull Request with an explicit merge commit |
| `squash` | Combines the Pull Request changes into a consolidated commit |
| `rebase` | Replays commits onto the target history |

The branch-protection example requires linear history.

Therefore, a merge-commit strategy is rejected when the policy is configured with `require_linear_history = TRUE`.

This demonstrates an important distinction:

**Merge strategy is a Pull Request decision.**

**Whether that strategy is permitted is a branch-governance decision.**

---

## Python Implementation

The Python program models repository workflow behavior using domain classes.

`PullRequest` owns the lifecycle and changeset state.

`Review`, `StatusCheck`, and `Commit` represent individual domain records.

`BranchProtection` contains target-branch governance requirements.

`RepositoryGovernance` performs merge-eligibility evaluation.

The Python implementation explicitly demonstrates:

- Draft-to-open transition
- Reviewer requests
- Commit additions
- Review decisions
- Status checks
- Unresolved conversations
- Base-branch synchronization
- Stale approvals
- Current approvals
- Merge-strategy selection
- Protected-branch validation

The important behavioral point is that an approval associated with an old commit does not satisfy the current approval requirement after synchronization.

---

## JavaScript Implementation

The JavaScript implementation uses an event-oriented application model.

It uses:

- `Set` for reviewer membership
- `Map` for status checks and conversations
- Classes for domain behavior
- Asynchronous merge handling
- Immutable constant enumerations
- Explicit exceptions through `GovernanceError`

The asynchronous merge operation represents the fact that a production governance service may need to coordinate with external status-check or repository systems.

The JavaScript implementation does not simply translate the Python classes. Its emphasis is on event-driven state evaluation and asynchronous policy execution.

---

## C++ Implementation

The C++17 implementation treats repository governance as a deterministic merge-eligibility engine.

The domain model uses:

- Strongly typed `enum class` values
- `std::set` for reviewer and policy membership
- `std::map` for status checks and conversations
- `std::optional` for the latest commit and merge strategy
- Exceptions for invalid domain operations

The engine evaluates:

- Pull Request state
- Existence of commits
- Protected-branch policy
- Bypass assignments
- Current approvals
- Required status checks
- Unresolved conversations
- Linear-history restrictions

The design uses the latest commit SHA as the review context.

This makes approval staleness explicit and prevents an approval on an older changeset from satisfying a current policy.

---

## Java Implementation

The Java 17 implementation emphasizes enterprise domain modeling.

Records represent immutable value-like objects:

- `Commit`
- `Review`
- `StatusCheck`
- `BranchProtectionPolicy`
- `GovernanceResult`

Enums represent controlled state transitions and policies.

`PullRequest` owns domain state.

`GovernanceService` evaluates repository governance rules.

The service distinguishes policy evaluation from the underlying Pull Request state.

Java collections are used to represent reviewer membership, status-check lookup, and conversation resolution.

Validation occurs at object boundaries so invalid domain objects are rejected before they enter the workflow.

The example also demonstrates a policy requiring two approvals, successful automated checks, resolved discussions, and linear history.

---

## PostgreSQL Design

The SQL implementation uses PostgreSQL-specific features where they provide meaningful integrity or evaluation behavior.

### Constraints

Primary keys establish row identity.

Foreign keys enforce relationships.

Unique constraints prevent duplicate domain identifiers.

Check constraints restrict:

- Pull Request states
- Review states
- Status-check states
- Merge strategies
- Positive identifiers
- Non-empty names
- Valid commit SHA formats

### Partial Index

The default-branch index `ux_one_default_branch` enforces uniqueness only for active default branches.

This is appropriate because deleted branches should not prevent the repository from assigning a future active default branch.

### Filtered Index

The unresolved-comment index focuses on:

`WHERE NOT resolved`

This supports queries concerned specifically with outstanding review discussions.

### Triggers

The self-review trigger prevents an author from submitting a review against their own Pull Request.

The lifecycle trigger maintains Pull Request timestamps based on state transitions.

These constraints are intentionally implemented in the database because governance rules should not depend exclusively on one application client.

---

## Transactional Merge

The `merge_pull_request` function performs a transactional merge operation.

It:

- Validates the requested merge strategy
- Locks the Pull Request row
- Retrieves current merge eligibility
- Rejects ineligible Pull Requests
- Changes the Pull Request state to `merged`
- Records the selected merge strategy
- Records merge timestamps

The row lock is important because merge eligibility can become invalid if another transaction changes the Pull Request while the merge decision is being made.

The final demonstration executes the merge inside:

`BEGIN`

followed by:

`COMMIT`

This provides an explicit transaction boundary for the state-changing operation.

---

## Failure Conditions

The implementations intentionally reject invalid states and actions.

| Failure | Enforcement |
|---|---|
| Duplicate commit | Application validation and primary relationship key |
| Empty branch name | Check constraint and application validation |
| Self-review | PostgreSQL trigger and application validation |
| Review of unknown commit | Application validation |
| Missing required status check | Merge evaluation |
| Failed status check | Merge evaluation |
| Unresolved discussion | Merge evaluation |
| Stale approval | Latest-commit comparison |
| Insufficient approvals | Merge evaluation |
| Merge commit under linear-history policy | Merge evaluation |
| Modification after merge | Application state validation |
| Missing branch policy | Merge evaluation |
| Invalid merge strategy | Application and PostgreSQL function validation |

---

## Relationship Between the Four Governance Areas

The four areas have different responsibilities.

### Pull Requests

A Pull Request provides the mechanism for proposing a changeset.

It establishes:

- Source branch
- Target branch
- Commits
- Author
- Lifecycle state
- Merge strategy

It answers:

**What change is being proposed and where should it go?**

### Code Review

Code review evaluates the proposed changes.

It establishes:

- Reviewer participation
- Review state
- Review comments
- Discussion resolution
- Review context

It answers:

**What did reviewers determine about the proposed changes?**

### Approvals

Approvals are review decisions with governance significance.

They establish whether eligible reviewers have accepted the current changeset.

They answer:

**Does the current Pull Request have enough valid approval decisions?**

### Branch Protection

Branch protection defines repository-level merge conditions.

It establishes:

- Required approval count
- Required status checks
- Conversation requirements
- History restrictions
- Direct-push restrictions
- Force-push restrictions
- Deletion restrictions
- Bypass assignments

It answers:

**What must be true before this protected branch can accept the change?**

These responsibilities should not be collapsed into one concept.

---

## Performance Considerations

The relational model indexes the access paths used by governance evaluation.

`pull_requests(target_branch_id, state)` supports protected-branch Pull Request lookup.

`reviews(pull_request_id, state)` supports review-state evaluation.

`status_checks(pull_request_id)` supports required-check validation.

The partial unresolved-comment index avoids indexing resolved comments for workloads focused on outstanding review discussions.

The application implementations use hash-based collections such as sets and maps for reviewer membership, policy membership, status-check lookup, and conversation lookup.

The C++ implementation uses `std::map` and `std::set` for deterministic ordered access. A production implementation handling very large repository datasets could use hash-based containers where deterministic ordering is not required.

---

## Security and Governance Considerations

Repository governance should fail closed.

A missing required status check is not treated as successful.

A missing branch-protection policy does not automatically grant merge permission in the application models.

An approval from the Pull Request author is rejected.

An approval against an older commit does not satisfy the current approval requirement.

Bypass users are modeled explicitly rather than inferred from ordinary reviewer status.

Direct pushes, force pushes, and branch deletion are represented as independent protection properties because they are different governance controls.

In a production system, bypass assignments would normally require strong authorization and auditing because they can intentionally override ordinary merge conditions.

---

## Practical Workflow

A realistic repository change proceeds through the following state relationships:

    Feature Branch
         |
         v
    Pull Request
         |
         +--> Commits
         |
         +--> Review Requests
         |       |
         |       v
         |    Code Reviews
         |       |
         |       +--> Comments
         |       |
         |       +--> Approval Decisions
         |
         +--> Status Checks
         |
         v
    Protected Target Branch
         |
         v
    Merge Eligibility
         |
         +--> Blocked
         |
         +--> Eligible
                 |
                 v
              Merge

The database design keeps each stage independently queryable while allowing the governance layer to evaluate them together.

---

## Educational Focus

The five implementations provide different views of the same repository-governance problem.

| Implementation | Primary perspective |
|---|---|
| Python | Workflow simulation and domain behavior |
| JavaScript | Event-driven policy evaluation |
| C++17 | Deterministic merge-eligibility engine |
| Java 17 | Enterprise domain and policy modeling |
| PostgreSQL | Relational integrity and transactional governance |

The implementations are intentionally not identical translations.

The shared domain model provides conceptual consistency, while each implementation uses the strengths of its environment to express repository workflow, review decisions, approval validity, branch policy, and merge eligibility.
