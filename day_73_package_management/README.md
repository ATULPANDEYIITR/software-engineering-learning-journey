# Package Management: Dependency Management and Versioning

## 1. Domain Overview

Package management is the controlled process of discovering, publishing, selecting, installing, updating, removing, and auditing reusable software components.

A package typically contains executable code, metadata, configuration, documentation, and references to other packages. Its dependencies determine which additional components must be available for correct execution.

Dependency management addresses compatibility between packages, while version management establishes how changes to packages are identified and selected.

A package management workflow must maintain consistency between:

- Declared dependency requirements.
- Available package releases.
- Selected package versions.
- Installed package versions.
- Transitive dependencies.
- Lockfile contents.
- Security and integrity policies.

The implementations model these mechanisms through Python, JavaScript, C++17, Java 17, and PostgreSQL.

## 2. Core Terminology

| Term | Meaning |
|---|---|
| Package | A distributable software component. |
| Package registry | A repository containing published packages and releases. |
| Dependency | Another package required by a component. |
| Direct dependency | A dependency explicitly declared by an application. |
| Transitive dependency | A dependency required by another dependency. |
| Version | An identifier representing a particular package release. |
| Version constraint | A rule specifying acceptable package versions. |
| Dependency resolution | Selection of compatible versions across a dependency graph. |
| Dependency conflict | A situation in which requirements cannot be satisfied simultaneously. |
| Lockfile | A record of exact selected versions and associated metadata. |
| Installation | Adding a selected package release to an environment. |
| Upgrade | Replacing an installed release with a newer compatible release. |
| Downgrade | Replacing an installed release with an older release. |
| Integrity verification | Checking whether package content matches its expected cryptographic digest. |
| Dependency audit | Examination of installed dependencies for security and maintenance risks. |
| Reproducible installation | Recreating an environment using the same resolved dependency versions and verified artifacts. |

## 3. Semantic Versioning

Semantic Versioning, commonly abbreviated as SemVer, identifies releases using three numeric components:

`MAJOR.MINOR.PATCH`

For example, `2.4.3` represents:

- Major version: 2
- Minor version: 4
- Patch version: 3

### 3.1 Major version

A major version increment indicates incompatible changes to the public interface or behavior.

Example:

`1.8.2 → 2.0.0`

Applications may require code modifications before adopting the new release.

### 3.2 Minor version

A minor version increment introduces backward-compatible functionality.

Example:

`1.8.2 → 1.9.0`

Existing functionality should remain compatible under the publisher's versioning contract.

### 3.3 Patch version

A patch version increment introduces backward-compatible fixes.

Example:

`1.8.2 → 1.8.3`

Typical changes include defect corrections and security fixes that preserve the declared compatibility contract.

### 3.4 Version comparison

Versions are compared numerically by their individual components.

For example:

`1.10.0 > 1.9.0`

Lexicographical string comparison is incorrect because the character `1` in `1.10.0` does not represent the complete numeric ordering of the minor version.

The implementations use numeric component comparison.

The examples use stable three-component versions without prerelease identifiers or build metadata. Full SemVer implementations must also handle prerelease precedence, build metadata, and the specification's additional validation rules.

## 4. Version Constraints

Version constraints describe which releases are acceptable.

The implementations support a practical subset of common constraint expressions.

| Constraint | Interpretation |
|---|---|
| `1.2.3` | Exact version 1.2.3 |
| `=1.2.3` | Exact version 1.2.3 |
| `>1.2.3` | Greater than 1.2.3 |
| `>=1.2.3` | Greater than or equal to 1.2.3 |
| `<2.0.0` | Less than 2.0.0 |
| `<=1.9.9` | Less than or equal to 1.9.9 |
| `^1.2.0` | Compatible versions below 2.0.0 |
| `~1.2.0` | Compatible patch releases below 1.3.0 |
| `>=1.0.0,<2.0.0` | Versions satisfying both conditions |
| `*` | Any available version |

### 4.1 Caret constraints

The caret operator permits changes that do not violate the specified compatibility boundary.

Examples:

- `^1.2.0` permits versions from `1.2.0` to below `2.0.0`.
- `^0.2.0` permits versions from `0.2.0` to below `0.3.0`.
- `^0.0.3` permits versions from `0.0.3` to below `0.0.4`.

The behavior of zero-major versions is particularly important because their compatibility guarantees are generally more restrictive.

### 4.2 Tilde constraints

The tilde operator restricts updates to the specified minor-version range.

For example:

`~1.2.0`

Permitted range:

`>=1.2.0,<1.3.0`

### 4.3 Combined constraints

A package may require a version satisfying multiple conditions.

For example:

`>=1.0.0,<2.0.0`

Both conditions must evaluate to true.

The implementations reject a candidate when any constraint fails.

## 5. Package Registries and Releases

A package registry stores published package versions and their metadata.

A package identity and a package release are separate concepts.

For example:

| Package | Release |
|---|---|
| core-engine | 1.0.0 |
| core-engine | 1.2.0 |
| core-engine | 2.0.0 |
| database-driver | 1.0.0 |
| database-driver | 2.0.0 |

The package name identifies the software component. The release identifies a particular version of that component.

A registry should maintain:

- Unique package identities.
- Unique releases within each package.
- Publisher or maintainer information.
- Release timestamps.
- Dependency metadata.
- Package status.
- Artifact integrity information.

A withdrawn release should not be selected for a new installation.

A deprecated release may remain available for compatibility but should be subject to explicit installation policy.

## 6. Dependency Management

### 6.1 Direct dependencies

Direct dependencies are declared by the application.

Consider an application requiring:

- `api-framework ^1.0.0`

The application does not necessarily declare every package required by the framework.

### 6.2 Transitive dependencies

Suppose the dependency relationships are:

Application
  |
  +-- api-framework ^1.0.0
        |
        +-- core-engine ^1.0.0
        |
        +-- database-driver ^1.0.0
              |
              +-- core-engine ^1.0.0

The application indirectly depends on `core-engine` through the framework and database driver.

The package manager must resolve all dependencies, not just those explicitly declared by the application.

### 6.3 Dependency graph

A dependency graph represents packages as vertices and dependency relationships as directed edges.

For example:

`api-framework → database-driver`

means that the framework requires the database driver.

A dependency graph can contain:

- Independent packages.
- Shared dependencies.
- Multiple dependency levels.
- Version conflicts.
- Circular dependencies.
- Optional dependencies.

The graph must be validated before installation.

### 6.4 Dependency resolution

Dependency resolution determines a compatible release for each required package.

The process involves:

1. Reading direct requirements.
2. Retrieving candidate package releases.
3. Evaluating version constraints.
4. Examining each candidate's dependencies.
5. Adding transitive requirements.
6. Detecting incompatible requirements.
7. Detecting dependency cycles.
8. Selecting a consistent installation plan.

The implementations prefer the highest available compatible release.

This strategy is a selection policy, not a universal guarantee of optimal dependency resolution.

## 7. Dependency Conflicts

A dependency conflict occurs when requirements cannot be satisfied by the available package releases.

Consider:

- Application requires `core-engine ^1.0.0`.
- Another dependency requires `core-engine ^2.0.0`.

If the environment supports only one selected version of `core-engine`, these requirements cannot both be satisfied.

The resulting dependency plan must be rejected.

Conflict detection is necessary because installing packages independently without evaluating their combined requirements can produce an inconsistent environment.

Some ecosystems support multiple versions of the same dependency through isolated dependency trees. The implementations primarily model a single-version-per-package environment.

## 8. Circular Dependencies

A circular dependency occurs when packages form a directed cycle.

Example:

`package-a → package-b → package-c → package-a`

Such a graph creates a dependency cycle.

A depth-first traversal can detect cycles by maintaining:

- A set of currently resolving packages.
- A set of completed packages.
- A record of selected releases.

Encountering a package already in the active resolution path indicates a cycle.

The Python, JavaScript, C++17, and Java 17 implementations use this general approach.

A production resolver should also retain the complete dependency path so that the error identifies every package participating in the cycle.

## 9. Dependency Resolution Algorithms

### 9.1 Depth-first resolution

Depth-first traversal examines a package and then recursively examines its dependencies.

Its main advantage is that it follows the actual dependency structure rather than treating packages as unrelated records.

### 9.2 Backtracking

Backtracking is necessary when selecting one package version introduces an incompatible dependency.

The resolver:

1. Selects a candidate release.
2. Adds its dependency requirements.
3. Attempts to resolve the resulting graph.
4. Restores the previous state when resolution fails.
5. Tries another candidate.

The implementations demonstrate this technique.

Backtracking can become computationally expensive when many packages have numerous candidate versions.

Practical resolvers use candidate prioritization, constraint propagation, memoization, graph simplification, and search heuristics to reduce unnecessary exploration.

### 9.3 Complexity

Let:

- V represent the number of selected package nodes.
- E represent the number of dependency edges.
- K represent the average number of candidate versions per package.

A basic graph traversal is approximately:

`O(V + E)`

This describes traversal after a compatible selection has been established.

Backtracking may require exploring multiple candidate combinations. Its worst-case behavior can grow exponentially with the number of packages and candidates.

Registry lookups and version comparisons also contribute to execution cost.

## 10. Lockfiles and Reproducible Environments

A dependency declaration and a lockfile serve different purposes.

| Dependency declaration | Lockfile |
|---|---|
| Defines acceptable versions | Records selected versions |
| Expresses compatibility requirements | Captures a resolved dependency plan |
| Supports controlled upgrades | Supports repeatable installations |
| May permit several versions | Records exact resolved releases |

For example, an application may declare:

`api-framework ^1.0.0`

The package manager may select:

- `api-framework 1.1.0`
- `core-engine 1.2.0`
- `database-driver 1.0.0`

The lockfile records those exact selections.

A useful lockfile contains:

- Lockfile format version.
- Package names.
- Exact release versions.
- Dependency relationships.
- Artifact checksums.
- Registry or source information where relevant.

The Python implementation writes a JSON lockfile. The JavaScript implementation writes a corresponding lockfile using asynchronous filesystem operations.

The other implementations demonstrate the underlying resolution and installation models.

A lockfile alone does not guarantee reproducibility. The referenced artifacts must remain accessible and immutable, and their integrity must be verified.

## 11. Package Installation and Updating

Installation is a controlled state transition.

The preferred workflow is:

Declared requirements
        |
        v
Dependency resolution
        |
        v
Candidate selection
        |
        v
Policy validation
        |
        v
Integrity verification
        |
        v
Installation plan
        |
        v
State commit
        |
        v
Updated environment

The complete installation plan should be validated before the environment changes.

This prevents partial installation when a later dependency fails validation.

### 11.1 Installation

Installation selects compatible releases and adds them to the environment.

### 11.2 Upgrade

An upgrade replaces an installed package with a newer compatible version.

The resolver must reevaluate dependent packages because a newer release can introduce different dependency requirements.

### 11.3 Downgrade

A downgrade replaces an installed version with an older release.

Downgrades can introduce compatibility problems or reintroduce known vulnerabilities.

The implementations include policy controls that can reject downgrades.

### 11.4 Uninstallation

A package should not be removed while another installed package still requires it.

The implementations perform dependent-package checks before allowing removal.

Production systems should calculate the full reverse dependency graph before uninstalling a package.

## 12. Python Implementation

The Python script models package management as an object-oriented repository workflow.

### 12.1 Main components

| Component | Responsibility |
|---|---|
| `Version` | Represents and validates numeric versions. |
| `VersionConstraint` | Evaluates version compatibility. |
| `Package` | Stores package metadata and dependencies. |
| `PackageRegistry` | Publishes and retrieves package releases. |
| `DependencyResolver` | Resolves the dependency graph. |
| `PackageManager` | Controls installation and removal. |
| `PackageState` | Represents package lifecycle status. |

### 12.2 Important mechanisms

The implementation uses:

- Dataclasses for package records.
- Dictionaries for registry and installation state.
- Sets for dependency traversal.
- Exceptions for conflict and validation failures.
- SHA-256 for package metadata fingerprints.
- JSON for lockfile generation.
- Atomic file replacement for lockfile writing.

The resolver snapshots its current state before trying another candidate. When resolution fails, it restores the previous state.

This makes the backtracking operation easier to reason about.

### 12.3 Validation scenarios

The script demonstrates:

- Compatible version selection.
- Major-version incompatibility.
- Combined constraints.
- Dependency conflicts.
- Prevention of removal of required packages.
- Lockfile creation.
- Package auditing.

The checksum in this demonstration represents canonical package metadata. It is not a digest of an actual downloaded package archive.

## 13. JavaScript Implementation

The JavaScript implementation uses an event-driven package management architecture.

### 13.1 Main components

| Component | Responsibility |
|---|---|
| `SemVer` | Numeric version representation. |
| `PackageRegistry` | Asynchronous package publication and retrieval. |
| `InstallPolicy` | Installation eligibility decisions. |
| `PackageManager` | Dependency resolution and installation. |
| `EventEmitter` | Communicates installation lifecycle events. |

### 13.2 Event-driven architecture

The manager emits events representing significant operations:

- `published`
- `installationStarted`
- `installationCompleted`
- `installationFailed`

This separates package-management operations from logging, monitoring, and other event consumers.

An enterprise application can use similar events to update dashboards, record audit entries, and notify deployment systems.

### 13.3 Asynchronous operations

Registry access uses asynchronous methods.

This design supports network-based registry integration without blocking the main event loop during I/O.

The filesystem operations use Node.js promises.

The installation operation also prevents overlapping installation attempts within the same manager instance.

### 13.4 Policy evaluation

The installation policy evaluates:

- Vulnerability status.
- Downgrade permissions.
- Maximum package count.
- Package checksum consistency.

All package checks occur before the installed-state map is replaced.

The implementation uses in-memory state. It does not provide distributed installation locking or durable transactional storage.

## 14. C++17 Implementation

The C++17 implementation focuses on a repository governance engine.

### 14.1 Main components

| Component | Responsibility |
|---|---|
| `Version` | Semantic version representation. |
| `Constraint` | Version requirement evaluation. |
| `Package` | Package domain structure. |
| `Registry` | Stores available releases. |
| `DependencyResolver` | Performs graph traversal and backtracking. |
| `Installation` | Represents a resolved installation plan. |
| `GovernanceEngine` | Controls installation and removal. |

### 14.2 STL design decisions

The implementation uses:

- `std::map` for ordered package inventories.
- `std::vector` for release candidates.
- `std::set` for cycle detection.
- `std::all_of` for constraint validation.
- `std::sort` for candidate prioritization.
- `std::move` for efficient state restoration.
- Exceptions for invalid operations.

Ordered maps provide predictable iteration and deterministic display output.

The resolver copies its state when exploring alternative candidates. This improves clarity but introduces memory and copying costs.

A production implementation could use persistent data structures, undo logs, or more selective state snapshots.

### 14.3 Governance behavior

The engine rejects:

- Invalid package versions.
- Duplicate releases.
- Unsatisfied dependencies.
- Circular dependencies.
- Deprecated or vulnerable packages.
- Downgrades.
- Uninstallation of required dependencies.

The example uses a single-version-per-package environment.

## 15. Java 17 Implementation

The Java implementation models package management as an enterprise service with explicit domain types and policies.

### 15.1 Main components

| Component | Responsibility |
|---|---|
| `Version` | Immutable version representation. |
| `VersionRequirement` | Validates and evaluates constraints. |
| `PackageDefinition` | Immutable package metadata. |
| `PackageRegistry` | Stores and selects releases. |
| `InstallationPolicy` | Defines policy validation. |
| `EnterprisePolicy` | Enforces enterprise installation rules. |
| `DependencyResolver` | Resolves compatible dependency graphs. |
| `InstallationService` | Manages installation state transitions. |
| `InstallationResult` | Represents an installation outcome. |

### 15.2 Java 17 features

The implementation uses records for immutable domain data.

Records reduce boilerplate and provide clear data ownership.

Collections are exposed through unmodifiable views or defensive copies.

The `InstallationPolicy` interface separates policy definitions from installation processing.

The enterprise implementation evaluates package status, checksum integrity, downgrade restrictions, and package-count limits.

### 15.3 Service architecture

The installation service follows a staged process:

1. Resolve dependencies.
2. Validate the installation limit.
3. Evaluate every package against policy.
4. Construct a new installation inventory.
5. Replace the previous state only after validation succeeds.

The synchronized installation operation prevents simultaneous state modifications within one service instance.

The example is an in-memory model. Persistent enterprise deployments require database transactions and coordination across service instances.

## 16. PostgreSQL Implementation

The PostgreSQL implementation models package management as a relational workflow.

### 16.1 Database relationship

Registry
  |
  +-- Packages
        |
        +-- Package Releases
              |
              +-- Semantic Versions
              |
              +-- Package Dependencies
              |
              +-- Security Advisories

Projects
  |
  +-- Installation Policies
  |
  +-- Package Installations
  |
  +-- Installation Audit

### 16.2 Relational tables

| Table | Purpose |
|---|---|
| `registries` | Stores package registry information. |
| `semantic_versions` | Stores numeric version components. |
| `packages` | Stores package identities and maintainers. |
| `package_releases` | Stores individual package releases. |
| `package_dependencies` | Stores version requirements. |
| `projects` | Represents managed application environments. |
| `package_installations` | Tracks installation states. |
| `security_advisories` | Stores affected version ranges and severity. |
| `installation_policies` | Stores environment-specific restrictions. |
| `installation_audit` | Records installation decisions and outcomes. |

### 16.3 Referential integrity

Primary keys identify records.

Foreign keys ensure that dependency and installation records reference existing packages and releases.

Unique constraints prevent duplicate package identities, release versions, and dependency relationships.

Check constraints enforce valid values for package names, version components, checksums, installation states, and policy limits.

Indexes support package release lookup, dependency retrieval, project installation reporting, and audit queries.

### 16.4 Database functions

`version_compare` performs numeric version comparison.

`version_satisfies` evaluates supported version constraints.

`check_package_eligibility` evaluates whether a package release satisfies project policy.

The eligibility function checks:

- Package release status.
- Active installation policy.
- Registry trust.
- Security advisory applicability.
- Package-count restrictions.

### 16.5 Triggers

`trg_validate_package_dependency` prevents a package from directly depending on itself.

`trg_validate_installation` ensures that installed releases are available and that installation timestamps are maintained consistently.

These triggers enforce integrity at the database boundary rather than relying exclusively on application validation.

### 16.6 Installation procedure

`install_package` provides a controlled installation operation.

It:

1. Locks the relevant project row.
2. Identifies the requested package release.
3. Checks downgrade restrictions.
4. Evaluates installation eligibility.
5. Records rejected operations.
6. Updates installation records.
7. Writes successful operations to the audit table.

The procedure is designed to execute within a PostgreSQL transaction.

The project-level row lock serializes installation operations targeting the same project.

The example records installation decisions but does not download or extract package archives.

## 17. Security and Supply-Chain Integrity

Package management introduces software supply-chain risks because applications execute code obtained from external or internal publishers.

Important security controls include the following.

### 17.1 Trusted registries

Applications should use approved registries.

An untrusted registry can publish malicious packages, replace expected artifacts, or distribute compromised dependencies.

Registry trust should be controlled through organizational policy.

### 17.2 Integrity verification

A checksum identifies package content.

SHA-256 can detect changes when the expected digest comes from a trusted source.

A checksum does not independently establish publisher identity. Stronger systems should verify signed package metadata, trusted signing keys, and authenticated provenance.

### 17.3 Vulnerability management

Security advisories identify packages and versions affected by known vulnerabilities.

An audit should evaluate installed releases against affected version ranges.

Critical and high-severity vulnerabilities may require blocking installation or deployment.

### 17.4 Dependency confusion

Dependency confusion occurs when a package manager retrieves an unintended package from an external registry instead of the expected internal package source.

Controls include:

- Registry namespace restrictions.
- Explicit registry configuration.
- Package ownership controls.
- Trusted-source policies.
- Dependency provenance verification.

### 17.5 Malicious lifecycle scripts

Some package ecosystems execute scripts during installation or build operations.

Such scripts can access files, credentials, environment variables, and network resources.

Installation should use restricted permissions and isolated execution environments.

### 17.6 Lockfile security

Lockfiles should be reviewed and version-controlled.

Unexpected dependency changes can introduce vulnerabilities or malicious package substitutions.

Production environments should verify both the selected version and the actual artifact digest.

## 18. Dependency Types

Different dependency relationships serve different purposes.

| Type | Purpose |
|---|---|
| Runtime | Required when the application executes. |
| Development | Required for development, testing, or building. |
| Optional | Used only when a particular feature is enabled. |
| Peer | Expected to be supplied by the consuming application or surrounding environment. |

The PostgreSQL implementation represents these categories using the `dependency_type` enumeration.

A mature package manager must distinguish these categories during installation, environment creation, and deployment.

## 19. Common Failure Modes

| Failure | Cause | Appropriate response |
|---|---|---|
| Version conflict | Requirements cannot be jointly satisfied. | Reevaluate compatible release ranges. |
| Missing package | Registry has no matching package. | Verify package identity and registry configuration. |
| Circular dependency | Dependency graph contains a cycle. | Restructure package relationships. |
| Integrity failure | Artifact digest differs from expected metadata. | Reject the artifact and investigate. |
| Vulnerable dependency | Selected release matches a security advisory. | Block or explicitly authorize the release. |
| Downgrade rejection | Installation policy prohibits older releases. | Evaluate compatibility and migration requirements. |
| Uninstallation failure | Another package depends on the target. | Resolve reverse dependencies first. |
| Registry failure | Registry unavailable or inaccessible. | Apply controlled retries and approved caching. |
| Partial installation | Installation fails after some changes. | Use transactional installation or rollback. |
| Lockfile inconsistency | Recorded versions differ from installed artifacts. | Reconcile the environment against the lockfile. |

## 20. Implementation Comparison

| Dimension | Python | JavaScript | C++17 | Java 17 | PostgreSQL |
|---|---|---|---|---|---|
| Primary focus | Workflow simulation | Event-driven package operations | Governance engine | Enterprise service | Relational workflow |
| Version modeling | Dataclass | Immutable class | Struct | Record | Relational version table |
| Dependency storage | Dictionary | Map | Ordered map | Collections | Foreign keys |
| Cycle detection | Set | Set | Set | Set | Application-level graph processing required |
| Backtracking | Yes | Yes | Yes | Yes | Not implemented as a recursive resolver |
| Policy validation | Manager | Policy object | Governance engine | Policy interface | Eligibility function |
| Installation state | Dictionary | Map | Installation structure | Service inventory | Installation table |
| Lockfile | JSON | JSON | Not implemented | Not implemented | Relational records |
| Security auditing | Package state | Vulnerability flag | Package status | Package status | Advisory tables |

## 21. Design Limitations

The implementations demonstrate practical dependency-management principles but intentionally use a restricted model.

The following production capabilities are not fully implemented:

- Complete Semantic Versioning 2.0.0 parsing, including prerelease and build metadata.
- Ecosystem-specific version syntax.
- Cryptographic package-signature verification.
- Actual package archive downloading and extraction.
- Dependency isolation and multiple installed versions.
- Full recursive dependency removal.
- Distributed installation locking.
- Registry authentication and authorization.
- Dependency graph optimization.
- Full lockfile compatibility with existing package managers.
- Automated vulnerability database synchronization.
- Sandboxed lifecycle script execution.

The PostgreSQL implementation also requires additional recursive dependency validation and deployment-level permissions before being used as a complete package installation service.

The Python and JavaScript checksum demonstrations cover canonical metadata, not downloaded archive verification.

The code examples use compatible dependency ranges and controlled package catalogs to demonstrate the core resolution mechanisms.

## 22. Practical Engineering Considerations

A reliable package management system should distinguish four separate concerns:

**Dependency declaration**

Defines what an application requires and the acceptable version ranges.

**Dependency resolution**

Determines which package releases satisfy all requirements.

**Installation execution**

Obtains, verifies, and places selected package artifacts into an environment.

**Environment governance**

Controls which versions and publishers are permitted and records the resulting software inventory.

These operations should not be treated as interchangeable.

A successful dependency resolution does not prove that a package is safe.

A successful integrity check does not prove that its publisher is trustworthy.

A valid lockfile does not prove that all referenced artifacts remain available.

A successful installation does not guarantee application-level compatibility.

Reliable package management therefore combines version constraints, graph resolution, artifact verification, security policies, transactional state management, and auditable installation records.
