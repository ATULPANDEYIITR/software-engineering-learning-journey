# Semantic Versioning (SemVer) 2.0.0

## Technical Overview

Semantic Versioning is a structured version-identification system for software packages, APIs, libraries, applications, and services.

It provides a consistent way to communicate the significance of software changes through version numbers.

The standard version format is:

`MAJOR.MINOR.PATCH`

Example:

`2.5.3`

| Component | Meaning | Example |
|---|---|---|
| MAJOR | Introduces incompatible public API changes | 2.0.0 → 3.0.0 |
| MINOR | Introduces backward-compatible functionality | 2.4.0 → 2.5.0 |
| PATCH | Introduces backward-compatible bug fixes | 2.4.5 → 2.4.6 |

Semantic Versioning follows the SemVer 2.0.0 specification.

Its central principle is that a released version communicates the compatibility implications of changes to the software's public interface.

## 1. Semantic Versioning Fundamentals

### 1.1 Major Version

A major version increment indicates an incompatible change to the public API.

Example:

`2.4.6 → 3.0.0`

Possible changes include:

- Removing an existing public function.
- Renaming an API endpoint.
- Changing a required request parameter.
- Removing a database field exposed through a public contract.
- Changing a method signature incompatibly.
- Altering documented behavior in a way that breaks existing consumers.

For software that has reached version `1.0.0`, incompatible changes require a major increment.

Before version `1.0.0`, the public API is considered unstable. Developers may introduce breaking changes through minor increments.

### 1.2 Minor Version

A minor version increment introduces backward-compatible functionality.

Example:

`2.4.6 → 2.5.0`

Typical changes include:

- Adding a new API endpoint.
- Introducing an optional request parameter.
- Adding a new public method.
- Adding a backward-compatible configuration option.
- Introducing a new feature without breaking existing functionality.

A minor increment resets the patch component to zero.

### 1.3 Patch Version

A patch version increment introduces backward-compatible bug fixes.

Example:

`2.4.6 → 2.4.7`

Typical changes include:

- Correcting a calculation error.
- Fixing an exception-handling defect.
- Correcting an incorrect response value.
- Resolving a performance defect without changing public behavior.
- Correcting a security vulnerability without introducing incompatible behavior.

A patch increment preserves the major and minor components.

### 1.4 Version Increment Rules

| Change classification | Previous version | New version |
|---|---|---|
| Breaking API change | 2.4.6 | 3.0.0 |
| New backward-compatible feature | 2.4.6 | 2.5.0 |
| Backward-compatible bug fix | 2.4.6 | 2.4.7 |
| Multiple changes including breaking change | 2.4.6 | 3.0.0 |
| Feature and bug fix without breaking change | 2.4.6 | 2.5.0 |

The highest-impact change determines the release increment.

A release containing both a new feature and a breaking change requires a major increment.

## 2. Version Structure and Syntax

A complete SemVer version has the following structure:

`MAJOR.MINOR.PATCH-PRERELEASE+BUILD`

Example:

`2.5.0-beta.2+build.104`

Its components are:

| Component | Example | Purpose |
|---|---|---|
| Major | 2 | Compatibility boundary |
| Minor | 5 | Backward-compatible functionality |
| Patch | 0 | Backward-compatible fixes |
| Prerelease | beta.2 | Identifies a prerelease |
| Build metadata | build.104 | Identifies build information |

The major, minor, and patch components must be non-negative integers without leading zeros.

Examples of valid versions:

- `0.1.0`
- `1.0.0`
- `2.4.6`
- `10.25.100`
- `1.0.0-alpha`
- `1.0.0-beta.2`
- `1.0.0-rc.1`
- `1.0.0+build.25`
- `2.5.0-beta.2+build.104`

Examples of invalid versions:

| Version | Reason |
|---|---|
| `01.2.3` | Leading zero in major |
| `1.02.3` | Leading zero in minor |
| `1.2.03` | Leading zero in patch |
| `1.2` | Missing patch |
| `v1.2.3` | Prefix is outside the SemVer version syntax |
| `1.2.3-01` | Leading zero in numeric prerelease identifier |
| `1.2.3+` | Empty build metadata |

## 3. Prerelease Versions

Prereleases identify software that has not yet reached its final release state.

Common prerelease identifiers include:

| Identifier | Typical purpose |
|---|---|
| alpha | Early development |
| beta | Feature-complete or testing-stage release |
| rc | Release candidate |
| dev | Development build |

Example release progression:

`1.0.0-alpha`

`1.0.0-alpha.1`

`1.0.0-beta`

`1.0.0-beta.2`

`1.0.0-rc.1`

`1.0.0`

A prerelease version has lower precedence than the corresponding stable version.

For example:

`1.0.0-rc.1 < 1.0.0`

Prerelease identifiers are separated by periods.

Their precedence rules are:

1. Numeric identifiers are compared numerically.
2. Numeric identifiers have lower precedence than nonnumeric identifiers.
3. Nonnumeric identifiers are compared lexically using ASCII ordering.
4. If the preceding identifiers are equal, the version with fewer identifiers has lower precedence.
5. A stable version has higher precedence than its corresponding prerelease.

Build metadata does not influence any of these comparisons.

## 4. Build Metadata

Build metadata provides additional information about a particular software build.

Example:

`2.5.0+build.104`

Other examples:

- `1.0.0+20261113`
- `2.1.0+commit.abc123`
- `3.0.0-rc.1+pipeline.45`

Build metadata may identify:

- CI/CD pipeline execution.
- Source-control commit references.
- Build numbers.
- Compilation environments.
- Internal artifact identifiers.

A critical distinction is that build metadata does not affect version precedence.

Therefore:

`1.0.0+build.1`

and

`1.0.0+build.2`

have equal SemVer precedence.

A release-management system may retain these identifiers for artifact traceability, but it must not interpret them as different compatibility levels.

## 5. Version Precedence

Version precedence determines which semantic version is greater.

Consider:

`1.0.0-alpha`

`1.0.0-alpha.1`

`1.0.0-alpha.beta`

`1.0.0-beta`

`1.0.0-beta.2`

`1.0.0-beta.11`

`1.0.0-rc.1`

`1.0.0`

The correct precedence is:

| Order | Version |
|---:|---|
| 1 | 1.0.0-alpha |
| 2 | 1.0.0-alpha.1 |
| 3 | 1.0.0-alpha.beta |
| 4 | 1.0.0-beta |
| 5 | 1.0.0-beta.2 |
| 6 | 1.0.0-beta.11 |
| 7 | 1.0.0-rc.1 |
| 8 | 1.0.0 |

Version comparison must not be implemented using ordinary string sorting.

For example, lexical sorting can incorrectly position `1.10.0` before `1.2.0`.

A correct implementation compares:

1. Major component.
2. Minor component.
3. Patch component.
4. Prerelease identifiers, when the numeric components are equal.

Build metadata is ignored.

The implementations use component-based comparison rather than string-based ordering.

## 6. Version Compatibility and Dependency Constraints

Software dependencies often specify which versions of another package they can use.

A version constraint defines an acceptable set of versions.

This project implements five basic comparison operators.

| Operator | Meaning | Example |
|---|---|---|
| `=` | Exactly equal precedence | `= 2.5.0` |
| `>` | Greater precedence | `> 2.0.0` |
| `>=` | Greater than or equal | `>= 2.0.0` |
| `<` | Lower precedence | `< 3.0.0` |
| `<=` | Lower than or equal | `<= 2.9.9` |

Consider a dependency that requires:

`>= 2.0.0`

and

`< 3.0.0`

The acceptable interval is:

`[2.0.0, 3.0.0)`

| Candidate | Result |
|---|---|
| 1.9.9 | Incompatible |
| 2.0.0 | Compatible |
| 2.5.3 | Compatible |
| 2.9.9 | Compatible |
| 3.0.0 | Incompatible |

These operators provide basic comparison constraints, not a complete implementation of every package manager's range syntax.

### 6.1 Compatibility Is Not Guaranteed by Version Numbers Alone

A version number communicates the developer's compatibility claim.

It does not prove that the software is actually backward-compatible.

A developer may accidentally introduce an incompatible change without incrementing the major component.

A release process should therefore combine SemVer classification with:

- Automated testing.
- API contract testing.
- Integration testing.
- Regression testing.
- Dependency validation.
- Documentation review.
- Release artifact verification.

## 7. Release Management Workflow

The five implementations model different aspects of version management.

A typical software release follows this sequence:

`Change Identification`
        |
        v
`Change Classification`
        |
        v
`Version Selection`
        |
        v
`Prerelease or Stable Candidate`
        |
        v
`Automated Validation`
        |
        v
`Dependency Compatibility`
        |
        v
`Release Approval`
        |
        v
`Publication`
        |
        v
`Release History`

### 7.1 Change Identification

Changes are classified according to their effect on the public interface.

Examples:

- Breaking change.
- New functionality.
- Bug fix.
- Security correction.
- Documentation update.
- Performance improvement.

### 7.2 Change Classification

The highest-impact change determines the version increment.

The classification priority is:

`MAJOR > MINOR > PATCH`

For example, a release containing a new feature and a backward-incompatible endpoint change must use a major increment.

### 7.3 Candidate Creation

A release candidate can be represented by a prerelease identifier.

Example:

`3.0.0-beta.1`

Candidate versions can be tested without representing themselves as final stable releases.

### 7.4 Validation

Before publication, the release system evaluates:

- Version syntax.
- Version precedence.
- Automated test results.
- Documentation completeness.
- Migration documentation for breaking changes.
- Dependency compatibility.
- Stable versus prerelease classification.

### 7.5 Publication

A release becomes published only after the applicable validation conditions are satisfied.

The published release becomes part of the project's permanent version history.

Production systems should preserve artifact checksums, source commit references, publication timestamps, and release provenance.

## 8. Python Implementation

File: `semantic_versioning.py`

The Python implementation provides a complete version-management model using standard-library capabilities.

### 8.1 Core Components

| Component | Responsibility |
|---|---|
| `Version` | Represents and compares semantic versions |
| `ChangeType` | Defines major, minor, and patch changes |
| `VersionConstraint` | Evaluates compatibility conditions |
| `Release` | Represents a release candidate |
| `ReleaseManager` | Manages release registration and publication |
| `VersionError` | Handles invalid version operations |
| `ReleaseError` | Handles invalid release operations |

### 8.2 Version Parsing

The `Version.parse()` method validates the complete SemVer structure.

It separates:

- Major.
- Minor.
- Patch.
- Prerelease identifiers.
- Build metadata.

The implementation rejects malformed versions and invalid leading zeros.

### 8.3 Comparison Algorithm

The comparison process first examines the numeric components.

If those components are equal, prerelease identifiers are compared individually.

Numeric prerelease identifiers are interpreted numerically rather than lexically.

Build metadata is intentionally excluded.

### 8.4 Release Management

The `ReleaseManager` maintains:

- Project identity.
- Registered releases.
- Publication state.
- Current version.
- Release history.
- Release dependencies.

Dependencies must already exist and be published before a dependent release can be published.

The implementation also supports atomic JSON export using a temporary file followed by replacement.

### 8.5 Testing

The script includes automated tests for:

- Valid and invalid version strings.
- Prerelease precedence.
- Build metadata.
- Version increments.
- Compatibility constraints.
- Release classification.
- Duplicate release registration.
- Publication behavior.

Run:

`python semantic_versioning.py`

## 9. JavaScript Implementation

File: `semantic-versioning.js`

The JavaScript implementation emphasizes event-driven release management and policy evaluation.

### 9.1 Core Components

| Component | Responsibility |
|---|---|
| `SemVer` | Immutable semantic version representation |
| `VersionConstraint` | Compatibility comparison |
| `ReleasePolicy` | Release eligibility rules |
| `ReleaseRegistry` | Release registration and publication |
| `EventEmitter` | Release lifecycle notifications |
| `determineReleaseType()` | Change classification |

### 9.2 Immutable Version Objects

The `SemVer` class validates its components and freezes its state.

This prevents accidental modification of a registered version.

### 9.3 Event-Driven Architecture

The registry emits two important events:

- `release:registered`
- `release:published`

These events allow other application components to respond to release lifecycle changes.

For example, a monitoring component can record publication events, while an artifact-management component can respond to newly registered releases.

### 9.4 Asynchronous Publication

The `publish()` method is asynchronous.

It validates dependencies before changing publication state.

This provides a foundation for integrating external artifact registries and asynchronous release workflows.

The demonstration uses an in-memory registry. It does not provide distributed transaction guarantees or persistent database storage.

### 9.5 Policy Evaluation

The release policy checks:

- Test completion.
- Documentation updates.
- Migration notes.
- Production eligibility.

A failed policy evaluation prevents registration.

Run:

`node semantic-versioning.js`

## 10. C++17 Implementation

File: `semantic_versioning.cpp`

The C++ implementation emphasizes a repository-level release governance engine.

### 10.1 Core Data Structures

| Structure | Purpose |
|---|---|
| `Version` | Stores semantic version components |
| `VersionConstraint` | Stores a dependency comparison |
| `Release` | Represents a release and its state |
| `GovernanceEngine` | Controls release validation and publication |

### 10.2 Enumerations

`ChangeType` identifies the type of release increment.

`ReleaseState` represents the lifecycle of a release:

- DRAFT
- VALIDATED
- PUBLISHED
- REJECTED

### 10.3 Governance Engine

The engine enforces:

- Unique release versions.
- Increasing release precedence.
- Release descriptions.
- Automated test completion.
- Documentation requirements.
- Breaking-change migration notes.
- Dependency availability.

Publication is performed only after validation.

### 10.4 Data Structure Decisions

The implementation uses `std::map` for ordered release storage and efficient lookup by version string.

It uses `std::vector` for prerelease identifiers and dependency lists.

`std::optional` represents the absence of a current published version.

The implementation uses digit-string comparison for numeric prerelease identifiers to avoid integer overflow.

### 10.5 Error Handling

Custom exceptions distinguish:

- Invalid version structures.
- Unsupported comparison operations.
- Duplicate releases.
- Invalid publication transitions.
- Missing dependencies.
- Numeric overflow.

Compile and execute:

`g++ -std=c++17 -O2 -Wall -Wextra -pedantic semantic_versioning.cpp -o semantic_versioning`

`./semantic_versioning`

## 11. Java 17 Implementation

File: `SemanticVersioning.java`

The Java implementation emphasizes enterprise release governance and explicit domain modeling.

### 11.1 Domain Types

| Type | Responsibility |
|---|---|
| `Version` | Immutable version representation |
| `Constraint` | Dependency compatibility rule |
| `ReleaseMetadata` | Release documentation and validation metadata |
| `Release` | Release state and transition management |
| `ReleaseRule` | Validation interface |
| `ReleasePolicy` | Collection of validation rules |
| `ReleaseService` | Release registration and publication |

### 11.2 Java Records

The implementation uses Java records for immutable value-oriented domain objects.

`Version`, `Constraint`, and `ReleaseMetadata` use defensive copying for collection properties.

This reduces accidental state modification.

### 11.3 Policy Objects

The implementation separates release rules into independent classes.

- `TestRule`
- `DocumentationRule`
- `BreakingChangeRule`
- `ProductionRule`

The `ReleasePolicy` evaluates all rules and returns the failures.

This design makes policy changes easier to maintain without embedding every validation condition in the release service.

### 11.4 State Transitions

The release lifecycle is:

`DRAFT → VALIDATED → PUBLISHED`

A failed validation can produce:

`DRAFT → REJECTED`

Published and rejected releases are terminal states in this implementation.

The `ReleaseService` controls transitions through synchronized operations.

### 11.5 Dependency Validation

A release cannot be published if a required dependency is missing or unpublished.

The service also verifies version constraints independently of the release's own version.

Compile and execute:

`javac SemanticVersioning.java`

`java -ea SemanticVersioning`

The `-ea` option enables Java assertions.

## 12. PostgreSQL Implementation

File: `semantic_versioning.sql`

The database implementation models a relational release-management system.

It provides persistent records for projects, versions, release changes, dependencies, validation results, and audit events.

### 12.1 Database Architecture

`semver.projects`
        |
        +---- `semver.releases`
        |          |
        |          +---- `semver.release_changes`
        |          |
        |          +---- `semver.release_validations`
        |          |
        |          +---- `semver.release_audit`
        |
        +---- `semver.dependencies`

### 12.2 Database Objects

| Object | Purpose |
|---|---|
| `projects` | Stores software project information |
| `releases` | Stores version and publication information |
| `release_changes` | Stores categorized release changes |
| `dependencies` | Stores dependency compatibility requirements |
| `release_validations` | Stores validation outcomes |
| `release_audit` | Records release state transitions |

### 12.3 Semantic Version Functions

The database implements:

- `is_valid_semver()`
- `semver_major()`
- `semver_minor()`
- `semver_patch()`
- `semver_compare_identifiers()`
- `semver_compare()`
- `version_satisfies()`

These functions allow version validation and comparison directly inside PostgreSQL.

The comparison function ignores build metadata, as required by SemVer.

### 12.4 Triggers

The release-component trigger automatically extracts major, minor, and patch components whenever a release version is inserted or changed.

The audit trigger records release state transitions.

These mechanisms reduce the risk of inconsistent records.

### 12.5 Release Validation

The `validate_release()` function evaluates release-specific rules.

It checks:

- Automated tests.
- Documentation.
- Migration notes.
- Prerelease classification.
- Major version structure.
- Minor version structure.

The `release_is_eligible()` function determines whether a release passes the implemented validation rules.

### 12.6 Publication Procedure

The `publish_release()` procedure:

1. Locks the release row.
2. Confirms that the release exists.
3. Verifies the draft state.
4. Checks prerelease restrictions.
5. Evaluates validation rules.
6. Verifies published dependencies.
7. Records validation results.
8. Changes the release state.
9. Records publication time.

PostgreSQL transactions provide atomic execution when the procedure is called within a transaction.

### 12.7 Views and Reporting

The implementation includes:

- `published_release_catalog`
- `release_validation_report`
- `project_release_statistics`

These views provide reusable reporting interfaces without repeating the underlying joins.

### 12.8 Execute the Database Script

Run the SQL file against a PostgreSQL database:

`psql -U postgres -d postgres -f semantic_versioning.sql`

The script creates the `semver` schema and inserts sample projects, releases, dependencies, and validation scenarios.

The SQL demonstrates database-side validation and workflow processing. It is an educational release-management model, not a complete package-registry implementation.

## 13. Distinctions Between the Five Implementations

The implementations share SemVer 2.0.0 rules but emphasize different engineering concerns.

| Implementation | Primary engineering perspective |
|---|---|
| Python | Version modeling, release history, testing, and file export |
| JavaScript | Event-driven release management and asynchronous policies |
| C++17 | Release governance and dependency eligibility |
| Java 17 | Enterprise domain modeling and controlled state transitions |
| PostgreSQL | Persistent relational workflow and auditability |

The same semantic version should have equivalent precedence across all five implementations.

The differences are in architecture, state management, validation responsibilities, and persistence.

## 14. Practical Release Scenarios

### Scenario A: Bug Fix

An existing payment API has version:

`1.4.2`

A defect in transaction pagination is corrected without changing the API contract.

New version:

`1.4.3`

Classification: PATCH.

### Scenario B: New Feature

An optional transaction-search endpoint is introduced.

Existing endpoints remain unchanged.

Previous version:

`1.4.3`

New version:

`1.5.0`

Classification: MINOR.

### Scenario C: Breaking API Change

The payment request schema is redesigned and existing consumers must modify their integrations.

Previous version:

`1.5.0`

New version:

`2.0.0`

Classification: MAJOR.

Migration documentation should describe the incompatible changes.

### Scenario D: Release Candidate

A new major release is undergoing integration testing.

Candidate:

`2.0.0-rc.1`

After successful validation, the stable release becomes:

`2.0.0`

The release candidate and stable release have different precedence.

### Scenario E: Dependency Compatibility

An inventory application requires a payment service version satisfying:

`>= 2.0.0`

and

`< 3.0.0`

The following outcomes apply:

| Payment API version | Result |
|---|---|
| 1.9.9 | Rejected |
| 2.0.0 | Accepted |
| 2.5.3 | Accepted |
| 2.9.9 | Accepted |
| 3.0.0 | Rejected |

## 15. Performance Considerations

### Version Parsing

Parsing requires examining the version string.

For a version string of length \(n\), parsing is approximately:

\(O(n)\)

### Version Comparison

The comparison algorithm processes at most the number of prerelease identifiers in the two versions.

If the total number of identifiers is \(k\), comparison is:

\(O(k)\)

Numeric identifier comparison also depends on identifier length.

### Release Lookup

The implementations use different data structures.

| Implementation | Data structure | Typical lookup complexity |
|---|---|---|
| Python | Dictionary | Average \(O(1)\) |
| JavaScript | Map | Average \(O(1)\) |
| C++17 | Ordered map | \(O(\log n)\) |
| Java 17 | TreeMap | \(O(\log n)\) |
| PostgreSQL | B-tree indexes | Approximately \(O(\log n)\) |

Database indexes are particularly useful when release histories grow and queries filter by project, state, or publication date.

### Dependency Evaluation

Evaluating \(d\) dependency constraints requires \(O(d)\) constraint checks, excluding database lookup costs.

Large dependency graphs require additional graph-based validation to detect circular dependencies and incompatible transitive requirements.

## 16. Security and Reliability Considerations

Semantic Versioning does not guarantee that a package is safe.

It only communicates version precedence and compatibility intent.

A production release-management system should also consider:

- Authentication for release publication.
- Role-based publication permissions.
- Immutable published artifacts.
- Release provenance.
- Source commit verification.
- Artifact checksums.
- Dependency vulnerability analysis.
- Protected release records.
- Audit logging.
- Backup and recovery.
- Atomic publication operations.
- Reproducible builds.

Version strings should be validated before they are stored or used in dependency resolution.

Database functions should run with appropriate privileges.

Application roles should not receive unrestricted permissions to modify published release records or audit history.

## 17. Limitations and Design Boundaries

The implementations deliberately focus on the core SemVer 2.0.0 specification and basic release governance.

They do not implement every feature of package managers such as npm, Cargo, Maven, or Python packaging tools.

Specific limitations include:

- No complete wildcard version-range syntax.
- No complete caret or tilde range implementation.
- No full transitive dependency solver.
- No circular dependency detection.
- No distributed publication protocol.
- No external artifact registry integration.
- No cryptographic signing of published artifacts.
- No automatic source-code API compatibility analysis.
- No distributed concurrency control in the in-memory implementations.

The PostgreSQL schema provides basic dependency constraints and release validation, but a production dependency resolver would require a more extensive dependency graph and range-evaluation model.

SemVer also relies on disciplined release classification. Incorrectly classifying an incompatible change as a minor or patch release can still break downstream applications.

## 18. Technical Terminology

| Term | Definition |
|---|---|
| Semantic Versioning | Standardized software version identification |
| Public API | Interface exposed to software consumers |
| Major release | Release introducing incompatible changes |
| Minor release | Release introducing backward-compatible features |
| Patch release | Release introducing backward-compatible fixes |
| Prerelease | Version preceding a stable release |
| Build metadata | Additional build identification information |
| Version precedence | Ordering of semantic versions |
| Compatibility constraint | Condition defining acceptable dependency versions |
| Release candidate | Prerelease intended for final validation |
| Backward compatibility | Ability of existing consumers to continue working |
| Dependency resolution | Determining whether required package versions are available |
| Release governance | Rules controlling validation and publication |
| Release provenance | Information identifying how and from which source a release was produced |
| Artifact | A packaged software output associated with a release |

## 19. Verification Matrix

The following cases define the expected behavior across the implementations.

| Test case | Expected result |
|---|---|
| Parse `1.2.3` | Valid |
| Parse `01.2.3` | Invalid |
| Parse `1.2.3-01` | Invalid |
| Compare `1.0.0-alpha` and `1.0.0` | Alpha is lower |
| Compare `1.0.0-beta.2` and `1.0.0-beta.11` | Beta.2 is lower |
| Compare `1.0.0+build.1` and `1.0.0+build.2` | Equal precedence |
| Increment `2.4.6` as major | `3.0.0` |
| Increment `2.4.6` as minor | `2.5.0` |
| Increment `2.4.6` as patch | `2.4.7` |
| Evaluate `2.5.3` against `>=2.0.0` and `<3.0.0` | Compatible |
| Evaluate `3.0.0` against `>=2.0.0` and `<3.0.0` | Incompatible |
| Publish a release with failing tests | Rejected |
| Publish a release with missing dependencies | Rejected |
| Publish an already published release | Rejected |

The verification cases establish the expected behavior of parsing, precedence, version increments, compatibility evaluation, and release governance across the five implementations.
