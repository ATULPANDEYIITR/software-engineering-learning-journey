# Build Systems: Dependencies, Compilation, and Packaging

## 1. Technical Scope

A build system automates the transformation of source code and its dependencies into executable programs, libraries, and distributable packages.

The build process involves three connected responsibilities:

1. **Dependency management:** Determines which components are required and their relationships.
2. **Compilation:** Transforms source files into object files, libraries, and executable artifacts.
3. **Packaging:** Organizes validated build artifacts into distributable units.

A reliable build system must also manage configuration, caching, reproducibility, failure recovery, artifact integrity, and execution order.

## 2. Build System Architecture

A typical build pipeline follows this structure:

Source Files
    |
    v
Dependency Resolution
    |
    v
Build Configuration
    |
    v
Compilation Planning
    |
    v
Compilation
    |
    v
Artifact Validation
    |
    v
Incremental Build Cache
    |
    v
Packaging
    |
    v
Distribution

The implementations use a repository-oriented domain model containing projects, targets, dependencies, configurations, build executions, artifacts, and packages.

## 3. Dependency Management

A dependency represents a component required by another component.

For example:

- `core` provides fundamental application functionality.
- `database` uses `core`.
- `network` uses `core`.
- `application` uses `database` and `network`.

The resulting dependency graph is:

core
 |
 +------ database
 |
 +------ network
           |
database --+
           |
           v
      application

The graph is directed because dependency relationships have a direction.

If target A requires target B, B must be available before A can be built.

### 3.1 Dependency Types

| Dependency type | Meaning |
|---|---|
| Direct | Explicitly declared by a target |
| Transitive | Required through another dependency |
| Optional | Not mandatory for every configuration |
| Versioned | Requires a compatible dependency version |
| Development | Required during development or testing |
| Runtime | Required when the application executes |
| Build-time | Required to compile or generate artifacts |

The implementations use explicit target relationships. The PostgreSQL model also records minimum dependency versions and optional dependency metadata.

### 3.2 Dependency Graph

A dependency graph is commonly represented as a directed graph:

G = (V, E)

Where:

- V represents build targets.
- E represents dependency relationships.

A directed acyclic graph (DAG) is required for ordinary dependency-first compilation.

A cycle such as:

A -> B -> C -> A

prevents a valid topological build order.

The Python, JavaScript, C++, and Java implementations detect cycles before executing the build.

The PostgreSQL implementation uses a recursive query and a trigger to reject dependency cycles when relationships are registered.

## 4. Compilation and Build Ordering

Compilation transforms source code into machine code or intermediate artifacts.

A build target can represent:

- A static library.
- A shared library.
- An executable.
- A generated resource.
- A separately compiled application module.

A target may require multiple dependencies.

### 4.1 Topological Sorting

Topological sorting determines an order in which every dependency precedes its dependent target.

For the example graph:

1. Compile `core`.
2. Compile `database` and `network`.
3. Compile `application`.

The algorithm uses depth-first traversal.

Its time complexity is:

O(V + E)

Where V is the number of targets and E is the number of dependency relationships.

### 4.2 Build Stages

Targets with no unresolved dependencies can be compiled independently.

The example produces:

| Stage | Targets |
|---|---|
| 0 | core |
| 1 | database, network |
| 2 | application |

These stages identify possible parallel execution.

Actual parallel execution requires additional controls, including resource limits, isolated output paths, and thread-safe state management.

### 4.3 Compilation Failure

Compilation can fail because of:

- Syntax errors.
- Missing header files.
- Incompatible compiler versions.
- Missing libraries.
- Invalid compiler flags.
- Unsupported language standards.
- Insufficient storage.
- Permission failures.

A failed dependency must prevent its dependent targets from being treated as successfully compiled.

The implementations represent compilation outcomes through explicit states.

## 5. Build Configurations

A build configuration defines how source code is compiled.

The primary profiles are:

| Profile | Purpose | Typical settings |
|---|---|---|
| Debug | Development and troubleshooting | Debug symbols, limited optimization |
| Release | Distribution and production | Optimization, controlled debug information |

Other configuration dimensions include:

- Compiler and compiler version.
- Target operating system.
- Processor architecture.
- Compiler flags.
- Environment variables.
- Include directories.
- Library search paths.
- Feature flags.

A build fingerprint should include all inputs that can affect the resulting artifact.

Changing a compiler version or relevant compilation flag should invalidate an incompatible cached artifact.

## 6. Incremental Builds and Caching

An incremental build recompiles only targets affected by relevant changes.

A complete rebuild may be expensive when a project contains hundreds of targets.

An incremental build avoids unnecessary work by identifying unchanged inputs.

### 6.1 Build Fingerprints

A fingerprint represents the effective inputs used to produce an artifact.

A practical fingerprint can include:

- Source file contents.
- Dependency fingerprints.
- Compiler identity and version.
- Compiler flags.
- Build profile.
- Target configuration.
- Relevant environment inputs.

Conceptually:

Build Fingerprint =
    Hash(
        Source
        + Dependencies
        + Compiler
        + Flags
        + Configuration
    )

If the fingerprint matches a previously successful build, its artifact may be reused after integrity validation.

### 6.2 Cache Invalidation

Cache invalidation is necessary when:

- Source files change.
- A dependency changes.
- Compiler settings change.
- Compiler versions change.
- Build profiles change.
- Previously cached artifacts become corrupted.

The Python and JavaScript implementations demonstrate fingerprint-based reuse.

The C++ implementation uses FNV-1a as a deterministic demonstration fingerprint, not a cryptographic integrity mechanism.

The Java implementation uses SHA-256.

The PostgreSQL implementation records build fingerprints and cache validity independently of actual compiler execution.

### 6.3 Reproducible Builds

A reproducible build produces equivalent artifacts when the same controlled inputs are used.

Reproducibility requires control over:

- Dependency versions.
- Compiler versions.
- Build flags.
- Operating system assumptions.
- Environment variables.
- File ordering.
- Generated timestamps.
- External downloads.
- Build scripts.

A fingerprint alone does not guarantee reproducibility. The build environment and source inputs must also be controlled.

## 7. Packaging

Packaging organizes compiled artifacts and metadata into a distributable unit.

A package commonly contains:

- Executables.
- Libraries.
- Configuration files.
- Dependency metadata.
- Version information.
- Build manifests.
- Checksums.
- Distribution metadata.

Example package structure:

enterprise_application-1.0.0/
    application.exe
    core.lib
    database.lib
    network.lib
    manifest.json

The implementations generate package manifests containing artifact names, versions, profiles, fingerprints, sizes, and checksums.

### 7.1 Artifact Integrity

SHA-256 can verify that an artifact has not changed between compilation and packaging.

For an artifact A:

Checksum(A) = SHA256(A)

The packaging process recalculates checksums and compares them with recorded values.

A mismatch prevents the artifact from being accepted.

A checksum verifies content consistency. It does not establish who produced the artifact or whether the artifact is trustworthy.

Digital signatures and trusted build provenance are separate security mechanisms.

### 7.2 Atomic Packaging

A package should not become visible as a complete release while it is still being assembled.

A safer process is:

1. Create a staging directory.
2. Copy validated artifacts.
3. Verify checksums.
4. Generate the manifest.
5. Rename the staging directory to its final destination.

The Python, JavaScript, and Java implementations demonstrate staging-based packaging.

Production deployments should also define behavior for interrupted filesystem operations and concurrent publishers.

## 8. Python Implementation

The Python implementation provides a complete build-system simulation using standard-library functionality.

### Main components

| Component | Responsibility |
|---|---|
| `Dependency` | Represents a versioned dependency |
| `BuildTarget` | Defines a compilation target |
| `DependencyGraph` | Validates relationships and computes build order |
| `BuildSystem` | Coordinates compilation and packaging |
| `BuildArtifact` | Stores artifact metadata |
| `BuildProfile` | Selects debug or release configuration |

The `DependencyGraph` class uses depth-first traversal to produce a dependency-first order.

The `build_levels()` method identifies independent compilation stages.

The `fingerprint()` method creates a SHA-256 key from target inputs and dependency fingerprints.

The `compile_target()` method handles cache reuse, compilation failure simulation, artifact creation, and checksum calculation.

The `package()` method validates artifacts and creates a manifest.

Assertions test dependency ordering, cycle detection, and version validation.

The implementation is a build-system simulator. It does not invoke an actual C++ compiler.

## 9. JavaScript Implementation

The JavaScript implementation focuses on asynchronous build orchestration and event-driven execution.

### Main components

| Component | Responsibility |
|---|---|
| `BuildTarget` | Holds target configuration and lifecycle state |
| `BuildSystem` | Coordinates asynchronous compilation |
| `Map` | Stores registered targets and cache entries |
| `Set` | Tracks pending and completed targets |
| `Promise.all` | Coordinates independent compilation operations |
| `EventEmitter` | Publishes build lifecycle events |

The build system uses bounded concurrency.

Independent targets can compile concurrently, while dependent targets wait for their prerequisites.

The event interface publishes:

- `compileStart`
- `compileSuccess`
- `compileFailure`
- `cacheHit`
- `buildComplete`
- `packageComplete`

Atomic file replacement reduces the risk of exposing incomplete artifacts.

The cache checks the stored artifact checksum before reuse.

The implementation uses Node.js filesystem operations, cryptographic hashing, promises, and event handling without third-party packages.

## 10. C++17 Implementation

The C++ implementation emphasizes explicit domain modeling and dependency planning.

### Main components

| Component | Responsibility |
|---|---|
| `BuildTarget` | Represents a target |
| `Artifact` | Stores generated artifact information |
| `BuildPlanner` | Manages build execution |
| `BuildState` | Tracks target lifecycle |
| `BuildProfile` | Represents compilation configuration |
| `BuildException` | Represents build failures |

The implementation uses:

- `std::map` for deterministic target storage.
- `std::set` for cycle detection.
- `std::vector` for dependency lists and build stages.
- `std::function` for recursive graph traversal.
- `std::all_of` for input validation.
- File streams for artifact creation.

The planner calculates dependency fingerprints before compiling targets.

The build stages identify parallelizable work, although this implementation executes targets sequentially.

The FNV-1a fingerprint is suitable for demonstrating deterministic change detection but is not suitable for cryptographic integrity verification.

The implementation uses standard C++17 libraries and a POSIX-style directory creation command in its demonstration environment.

## 11. Java 17 Implementation

The Java implementation models an enterprise-oriented build management service.

### Main components

| Component | Responsibility |
|---|---|
| `BuildTarget` | Immutable target configuration with controlled lifecycle state |
| `Dependency` | Versioned dependency metadata |
| `BuildArtifact` | Immutable artifact record |
| `BuildPolicy` | Enforces build acceptance conditions |
| `BuildService` | Manages dependency resolution and compilation |
| `BuildEventListener` | Receives build events |

Java records represent immutable metadata.

Collections manage targets, dependencies, and build results.

`CompletableFuture` coordinates dependent asynchronous compilation operations.

`ExecutorService` controls parallel execution.

The implementation also uses:

- SHA-256 checksums.
- Temporary artifact files.
- Atomic file replacement where supported.
- Build lifecycle events.
- Explicit failure handling.
- Packaging policy validation.

The build policy checks the number of successful artifacts before packaging.

The implementation demonstrates dependency-aware asynchronous execution rather than merely translating the Python workflow.

## 12. PostgreSQL Implementation

The PostgreSQL implementation provides a relational model for persistent build management.

### Database entities

| Table | Purpose |
|---|---|
| `projects` | Project registration |
| `build_targets` | Compilation targets |
| `target_dependencies` | Dependency relationships |
| `build_configurations` | Compiler settings |
| `build_runs` | Individual build executions |
| `target_executions` | Per-target compilation outcomes |
| `build_artifacts` | Generated artifact metadata |
| `build_cache` | Cached build references |
| `packages` | Release package records |
| `package_artifacts` | Package-to-artifact relationships |
| `build_audit_log` | Build activity history |

### 12.1 Referential Integrity

Primary keys uniquely identify records.

Foreign keys enforce relationships between projects, targets, executions, artifacts, and packages.

Unique constraints prevent duplicate target registrations and duplicate dependency relationships.

Check constraints validate versions, checksums, file sizes, and lifecycle-related fields.

### 12.2 Recursive Dependency Processing

The `get_build_order()` function uses a recursive common table expression to determine dependency levels.

The `detect_dependency_cycle()` trigger rejects newly introduced circular dependencies.

The recursive query is appropriate for the acyclic sample graph. Production systems should also validate graph-wide consistency and handle concurrent dependency changes through suitable transaction isolation or project-level locking.

### 12.3 Build Lifecycle

The `create_build_run()` procedure:

- Validates project and configuration relationships.
- Rejects inactive configurations.
- Checks request metadata.
- Creates a build execution record.
- Records an audit event.

Target execution records represent individual compiler outcomes.

The database records those outcomes but does not execute the compiler itself.

### 12.4 Eligibility and Reporting

The `build_eligibility` view determines whether all registered executions succeeded or used valid cached results.

The `build_statistics` view aggregates project-level build performance.

Other queries retrieve:

- Dependency order.
- Compilation outcomes.
- Artifact checksums.
- Cache utilization.
- Package contents.
- Audit history.

The transaction groups related schema and sample-data operations into a consistent database operation.

## 13. Important Technical Distinctions

| Concept | Responsibility |
|---|---|
| Dependency management | Determines required components |
| Dependency resolution | Selects compatible dependency versions |
| Build graph | Represents dependency relationships |
| Compilation | Transforms source code |
| Linking | Combines object files and libraries |
| Build orchestration | Coordinates build operations |
| Incremental build | Avoids unnecessary recompilation |
| Build cache | Reuses previously generated outputs |
| Artifact management | Stores and validates build outputs |
| Packaging | Creates a distributable unit |
| Build provenance | Records how an artifact was produced |

These responsibilities are related but not interchangeable.

A successful compilation does not automatically establish that a package is complete or suitable for distribution.

## 14. Build System Security

Build infrastructure can become a security-sensitive part of software delivery.

Important risks include:

- Dependency confusion.
- Malicious package versions.
- Compromised build scripts.
- Untrusted compiler plugins.
- Exposed credentials.
- Unsafe shell command execution.
- Artifact substitution.
- Cache poisoning.
- Insecure temporary directories.
- Unauthorized package publication.

Relevant controls include:

1. Pin dependency versions and verify package sources.
2. Use trusted and isolated build environments.
3. Restrict build-worker permissions.
4. Avoid embedding secrets in build configurations.
5. Validate compiler and packaging inputs.
6. Verify artifact checksums.
7. Sign release artifacts.
8. Protect build logs and provenance records.
9. Separate compilation permissions from publication permissions.
10. Restrict access to cached artifacts.

Checksums should not be treated as a replacement for digital signatures or trusted build provenance.

## 15. Performance Considerations

Build performance depends on project size, dependency relationships, compiler efficiency, storage, and available compute resources.

| Technique | Performance effect |
|---|---|
| Incremental compilation | Avoids rebuilding unchanged targets |
| Parallel compilation | Executes independent targets concurrently |
| Dependency caching | Reduces repeated dependency retrieval |
| Artifact caching | Avoids repeated compilation |
| Precompiled headers | Reduces repeated header processing |
| Distributed compilation | Uses multiple build workers |
| Build graph optimization | Reduces unnecessary dependency work |
| Content-addressed storage | Enables reliable artifact reuse |

Parallel compilation must account for shared resources and output conflicts.

Excessive concurrency can increase memory consumption and reduce performance.

## 16. Limitations of the Implementations

The five implementations deliberately demonstrate build orchestration rather than providing complete replacements for established native build tools.

| Implementation | Main limitation |
|---|---|
| Python | Simulates compilation instead of invoking a compiler |
| JavaScript | Uses simulated source compilation |
| C++17 | Sequential execution and demonstration hashing |
| Java 17 | Uses simulated compiler output |
| PostgreSQL | Stores build metadata without executing compilation |

The implementations do not provide complete support for:

- Native object-file generation.
- Shared-library linking.
- Operating-system-specific compiler discovery.
- Package repository synchronization.
- Full semantic version constraint resolution.
- Distributed build execution.
- Cryptographic artifact signing.
- Container image creation.
- Software bill of materials generation.

The database model records build state and release metadata, while actual compilation remains the responsibility of an external build worker.

## 17. Cross-Language Comparison

| Capability | Python | JavaScript | C++17 | Java 17 | PostgreSQL |
|---|---|---|---|---|---|
| Dependency graph | Yes | Yes | Yes | Yes | Yes |
| Cycle detection | Yes | Yes | Yes | Yes | Trigger |
| Topological sorting | Yes | Yes | Yes | Yes | Recursive query |
| Incremental cache | Yes | Yes | Yes | Yes | Persistent records |
| Parallel execution | Build stages | Promises | Stage planning | CompletableFuture | Metadata |
| Artifact checksum | SHA-256 | SHA-256 | Demonstration hash | SHA-256 | Recorded checksum |
| Packaging | Yes | Yes | Yes | Yes | Package records |
| Lifecycle events | Logging | EventEmitter | Console | Listener interface | Audit trigger |

## 18. Practical Build Workflow

A controlled enterprise build workflow can be expressed as:

1. Register the project and its targets.
2. Declare dependency relationships.
3. Validate dependency versions and graph integrity.
4. Select a compiler configuration.
5. Resolve a dependency-first execution order.
6. Calculate target fingerprints.
7. Reuse verified cached artifacts.
8. Compile targets whose inputs have changed.
9. Record compilation outcomes.
10. Verify generated artifacts.
11. Validate release eligibility.
12. Assemble the package.
13. Generate a manifest.
14. Verify package integrity.
15. Publish the release through an authorized process.

The separation of dependency resolution, compilation, artifact validation, and packaging provides clear failure boundaries and makes build operations easier to audit.
