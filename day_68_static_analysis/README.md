# Static Analysis: Linters, Formatters, and Code Analyzers

## 1. Technical Scope

Static analysis examines source code without executing the application under analysis. It identifies potential defects, security weaknesses, inconsistent formatting, maintainability problems, and violations of coding policies.

The implementations provide five complementary perspectives:

| Deliverable | Main responsibility |
|---|---|
| Python | Source inspection using abstract syntax trees, diagnostics, and formatting |
| JavaScript | Event-driven analysis, asynchronous file processing, and policy evaluation |
| C++17 | Rule-based analysis engine and quality-gate evaluation |
| Java 17 | Enterprise analysis services, immutable domain objects, and governance policies |
| PostgreSQL | Persistent analysis records, findings, suppressions, and compliance reporting |

The three principal categories have different responsibilities.

### Linters

A linter identifies suspicious code patterns and coding-standard violations.

Typical checks include:

- Unused or inappropriate coding constructs.
- Unsafe dynamic evaluation.
- Broad exception handling.
- Duplicate declarations.
- Unnecessary debugging statements.
- Inconsistent variable declarations.
- Potential reliability problems.

Linter findings are diagnostic records. They do not necessarily indicate that a program will fail.

### Formatters

A formatter applies consistent source-code presentation rules.

Typical operations include:

- Removing trailing whitespace.
- Normalizing indentation.
- Enforcing line-ending conventions.
- Applying consistent layout rules.
- Ensuring a final newline.

A formatter changes source representation while intending to preserve program behavior.

Formatting and linting should remain separate operations. A formatting violation does not automatically imply a programming defect.

### Code Analyzers

Code analyzers examine source-code properties to identify deeper problems.

Relevant analysis areas include:

- Security weaknesses.
- Potential runtime errors.
- Complexity.
- Reliability.
- Performance.
- Dependency and architectural constraints.
- Compliance with engineering policies.

Some analyzers use lexical rules, while others require syntax trees, control-flow graphs, data-flow analysis, or type information.

## 2. Static Analysis Processing Architecture

The implementations follow a common conceptual processing pipeline.

Source files  
→ File validation  
→ Lexical inspection  
→ Syntax or structural inspection  
→ Rule evaluation  
→ Diagnostic generation  
→ Optional formatting  
→ Quality assessment  
→ Reporting

Each stage has a distinct responsibility.

| Stage | Responsibility |
|---|---|
| File validation | Check file availability, encoding, and size |
| Lexical inspection | Detect whitespace and recognizable source patterns |
| Structural inspection | Examine syntax and program constructs |
| Rule evaluation | Apply configured analysis rules |
| Diagnostics | Record severity, location, and explanation |
| Formatting | Apply safe presentation corrections |
| Quality assessment | Evaluate findings against configured thresholds |
| Reporting | Present results for developers and maintainers |

The pipeline separates detecting an issue from deciding whether that issue prevents a release.

## 3. Diagnostic Model and Severity

A diagnostic identifies an individual source-code problem.

The implementations use a common conceptual structure.

| Field | Meaning |
|---|---|
| File | Source file containing the finding |
| Line | Source line number |
| Column | Position within the source line |
| Rule ID | Unique identifier of the analysis rule |
| Severity | Importance of the finding |
| Message | Explanation of the detected problem |
| Suggestion | Recommended corrective action |

Three severity levels are represented:

- **Error:** A serious violation, such as unsafe dynamic execution.
- **Warning:** A potential defect or significant coding-standard violation.
- **Info:** A lower-priority observation that may require engineering consideration.

Severity describes the importance of a finding. It does not independently determine whether the finding is accepted by a repository policy.

A quality gate evaluates findings using configurable thresholds.

## 4. Python Implementation

The Python implementation uses standard-library capabilities to create a source-analysis toolkit.

### Structural analysis with AST

The `ast` module converts Python source code into an abstract syntax tree.

An abstract syntax tree represents the structure of a program rather than its original formatting.

For example, a function definition is represented as a function node containing its arguments and body.

The `PythonAnalyzer` class extends `ast.NodeVisitor`.

Its specialized visitors inspect:

- Function calls.
- Function definitions.
- Exception handlers.
- Import statements.

This enables structural checks that are more reliable than searching for arbitrary text.

Implemented rules include:

| Rule | Detection |
|---|---|
| SEC001 | Unsafe use of `eval()` or `exec()` |
| SEC002 | Potentially unsafe pickle usage |
| BUG001 | Mutable function default arguments |
| ERR001 | Bare exception handling |
| DES001 | Empty function implementations |
| STYLE001 | Direct print statements |

### Formatting checks

The `StaticAnalyzer` class checks:

- Trailing whitespace.
- Excessive line length.
- Tab characters.
- Missing final newline.

The `format_source()` method performs safe formatting corrections.

The formatter does not attempt to rewrite Python expressions or reconstruct program syntax.

### Reporting

`AnalysisResult` stores diagnostics and calculates error and warning totals.

The command-line interface supports:

- Multiple input files.
- JSON reporting.
- Maximum line-length configuration.
- Automatic formatting corrections.
- Warning-sensitive exit codes.

The script also provides an executable demonstration when no file arguments are supplied.

### Practical limitations

The AST rules do not constitute a complete Python type checker or security analyzer.

For example, detecting `eval()` does not establish whether a particular input is attacker-controlled. More advanced analysis would require data-flow tracking and context-sensitive inspection.

The formatting implementation intentionally limits itself to transformations that do not require reconstructing Python syntax.

## 5. JavaScript Implementation

The JavaScript implementation emphasizes asynchronous processing, event-driven diagnostics, and configurable analysis policies.

### Analysis policy

The `AnalysisPolicy` class centralizes configuration.

It controls:

- Maximum line length.
- Console-output restrictions.
- Debugger-statement restrictions.
- Dynamic-evaluation restrictions.

The policy is immutable after construction.

### Event-driven diagnostics

`JavaScriptAnalyzer` extends Node.js `EventEmitter`.

It emits two important events:

| Event | Purpose |
|---|---|
| `diagnostic` | Reports an individual finding |
| `analysisComplete` | Reports the completed analysis result |

This allows reporting, logging, and other consumers to respond to findings without coupling them to the analysis rules.

### Asynchronous file processing

`AnalysisService` processes multiple files using asynchronous file operations.

Its worker-based approach limits concurrent processing.

The concurrency setting prevents an unnecessarily large number of simultaneous file operations.

File-size validation also prevents the service from loading arbitrarily large files into memory.

### Implemented checks

- Excessive line length.
- Trailing whitespace.
- Tab characters.
- Missing final newline.
- Debugger statements.
- Console output.
- Dynamic evaluation.
- Loose equality.
- Legacy `var` declarations.
- Repeated declaration names.

The implementation uses Node.js parsing through `Function` construction to detect syntax errors. This validates parseability but does not execute the supplied application statements.

The checks are intentionally lightweight. They do not replace a full JavaScript AST or lexical-scope analyzer.

### Failure handling

Each file is analyzed independently.

A file-access failure becomes a diagnostic rather than terminating the entire repository scan.

The CLI supports JSON output and optional formatting corrections.

## 6. C++17 Implementation

The C++ implementation models a configurable static-analysis engine for repository code-quality assessment.

### Rule registry

`RuleRegistry` maintains a map of rule identifiers to rule definitions.

Each rule contains:

- Unique identifier.
- Description.
- Severity.
- Category.
- Enabled state.

The map provides efficient lookup by rule identifier.

Duplicate identifiers are rejected.

### Domain model

The program defines separate enumerations for:

- `Severity`
- `RuleCategory`
- `GateStatus`

The `Diagnostic` structure represents an individual finding.

The `AnalysisReport` structure maintains the findings associated with one source file.

### Rule suppression

The analyzer supports explicit rule suppression.

Suppression is implemented through a set of rule identifiers.

This allows an analysis policy to disable selected checks without removing their definitions from the registry.

Suppression should be governed carefully in production environments because disabling security rules can conceal genuine weaknesses.

### Quality gate

`QualityGate` evaluates the analysis report against configured limits.

The decision considers:

- Maximum permitted errors.
- Maximum permitted warnings.

A failed gate indicates that the report violates the configured quality thresholds.

### Engineering decisions

The implementation uses:

- `std::map` for rule registration.
- `std::set` for suppression tracking.
- `std::vector` for diagnostics.
- STL algorithms for aggregation and sorting.
- Regular expressions for recognizable source patterns.

The resulting implementation is suitable for demonstrating rule-based source inspection and policy evaluation.

Its regular-expression checks are not a substitute for C++ parsing. For example, a keyword inside a string literal or comment can produce a false positive.

A production C++ analyzer would need to understand preprocessing, language grammar, scopes, types, and control flow.

## 7. Java 17 Implementation

The Java implementation models static analysis as an enterprise service with explicit domain types and policy management.

### Immutable domain records

Java 17 records represent:

- `AnalysisRule`
- `Diagnostic`
- `AnalysisResult`
- `Suppression`

Records provide concise data models and automatically generated accessors.

The implementation uses defensive copying with `List.copyOf()` to prevent callers from modifying completed diagnostic collections.

### Rule registry

`RuleRegistry` maintains a concurrent map of analysis rules.

It rejects duplicate rule identifiers and provides a sorted view of enabled rules.

This separates rule configuration from source inspection.

### Analysis policy

`AnalysisPolicy` stores:

- Maximum line length.
- Maximum permitted errors.
- Maximum permitted warnings.
- Console-output policy.
- Suppressed rules.

The policy is established during construction and is not subsequently modified.

### Formatter service

`SourceFormatter` performs whitespace normalization and final-newline handling.

When formatting a file, it first writes the updated contents to a temporary file.

It then attempts an atomic replacement.

If atomic replacement is unsupported, it uses a normal replacement operation.

This reduces the risk of leaving a partially written source file.

### Analysis service

`AnalysisService` coordinates:

1. Optional formatting.
2. File validation.
3. Source inspection.
4. Diagnostic collection.
5. Result generation.

An unsuccessful formatting operation produces a failed analysis result.

### Quality governance

`QualityGate` determines whether all analysis executions satisfy configured thresholds.

The gate rejects incomplete analysis when successful completion is required.

This distinction is important: a repository should not be considered compliant merely because an analysis process failed to execute its checks.

### Enterprise considerations

The implementation separates:

- Rule definitions.
- Analysis policies.
- Source inspection.
- Formatting.
- Execution services.
- Quality-gate decisions.

This separation allows individual components to be replaced or extended without redesigning the entire workflow.

## 8. PostgreSQL Implementation

The PostgreSQL script implements persistent storage for a static-analysis governance workflow.

### Relational architecture

The database contains the following major entities:

| Entity | Responsibility |
|---|---|
| `projects` | Software repository information |
| `source_files` | Source-file inventory |
| `analysis_tools` | Registered analysis tools |
| `analysis_rules` | Central rule definitions |
| `tool_rules` | Tool-to-rule relationships |
| `analysis_runs` | Individual analysis executions |
| `findings` | Detected source-code issues |
| `formatter_runs` | Formatting execution records |
| `governance_users` | Authorized governance participants |
| `finding_suppressions` | Finding suppression requests |
| `quality_gate_policies` | Repository quality thresholds |
| `quality_gate_evaluations` | Recorded gate decisions |

### Entity relationships

Projects  
→ Source files  
→ Analysis runs  
→ Findings  
→ Analysis rules

Analysis tools  
→ Tool-rule mappings  
→ Analysis rules

Findings  
→ Suppression requests  
→ Governance users

Analysis runs  
→ Quality gate evaluations  
→ Quality gate policies

This structure separates the definition of a rule from the individual occurrences detected by that rule.

### Analysis execution states

An analysis execution can have these states:

| State | Meaning |
|---|---|
| `queued` | Waiting for execution |
| `running` | Analysis is underway |
| `completed` | Analysis completed successfully |
| `failed` | Analysis execution failed |
| `cancelled` | Analysis execution was cancelled |

A database trigger validates terminal-state transitions and automatically records execution timestamps.

A completed run cannot be changed back to a running state.

A failed run requires an error description.

### Finding management

Each finding references:

- Its analysis execution.
- Its source file.
- Its originating rule.

The fingerprint provides a stable identifier for distinguishing findings within an execution.

The uniqueness constraint prevents duplicate fingerprints within the same analysis run.

Finding resolution is tracked independently of analysis execution.

### Suppression governance

A suppression is a controlled exception to a finding.

The workflow distinguishes pending, approved, rejected, and expired requests.

The authorization trigger prevents:

- Self-approval.
- Approval without an authorized account.
- Approval without an approver identifier.

Approved suppressions can have an expiration date.

An expired suppression no longer contributes to exclusion from quality-gate calculations.

Suppression does not delete the original finding. This preserves the historical record.

### Quality gates

The `quality_gate_policies` table stores repository-level thresholds.

The `evaluate_quality_gate()` function evaluates:

- Error count.
- Warning count.
- Critical security finding count.
- Analysis execution completion.

A pending analysis produces a pending gate decision when successful completion is mandatory.

A completed execution can pass or fail according to the active policy.

The evaluation is stored for reporting and audit purposes.

### Database performance

The implementation creates indexes for common access patterns:

- Project analysis history.
- Analysis execution status.
- Findings by run and severity.
- Rule-based finding retrieval.
- Unresolved findings.
- Pending suppression requests.
- Quality-gate status.

Partial indexes reduce unnecessary index entries for frequently queried subsets, such as unresolved findings.

The views provide reusable reporting structures without duplicating the underlying records.

## 9. Distinctions Between Analysis Mechanisms

The three mechanisms should not be treated as interchangeable.

| Dimension | Linter | Formatter | Code analyzer |
|---|---|---|---|
| Primary purpose | Identify suspicious code | Normalize presentation | Evaluate code properties |
| Typical input | Source code | Source code | Source code and context |
| Typical output | Diagnostics | Modified source | Findings and metrics |
| Changes source | Usually no | Yes | Usually no |
| Security analysis | Possible | No | Possible |
| Syntax awareness | Varies | Usually required | Often required |
| Complexity analysis | Possible | No | Common |
| Quality-gate input | Yes | Sometimes | Yes |

A formatter can remove trailing whitespace without identifying a security vulnerability.

A linter can identify an unsafe construct without proving that the application is exploitable.

A deeper analyzer can inspect control flow and data flow to establish more meaningful relationships between source-code operations.

## 10. Static Analysis and Continuous Integration

Static analysis is most useful when integrated into the normal software-development workflow.

A practical pipeline is:

Developer changes source files  
→ Commit  
→ Automated build pipeline  
→ Static analysis  
→ Linter execution  
→ Formatting verification  
→ Security checks  
→ Diagnostic aggregation  
→ Quality-gate evaluation  
→ Build or release decision

The analysis should run against the exact commit being evaluated.

This avoids a mismatch between the source code that was analyzed and the source code eventually released.

### Analysis modes

| Mode | Purpose |
|---|---|
| Local analysis | Immediate developer feedback |
| Commit analysis | Validate a committed changeset |
| Pull-request analysis | Assess proposed changes |
| Scheduled analysis | Detect accumulated code-quality problems |
| Release analysis | Enforce production quality requirements |

For large repositories, incremental analysis can reduce execution time by analyzing changed files and relevant dependencies.

A full repository scan remains useful for detecting issues outside the changed files.

## 11. False Positives, False Negatives, and Suppression

Static analysis is not perfect.

A false positive occurs when an analyzer reports a problem that is not actually present.

A false negative occurs when an analyzer fails to detect a real problem.

Common causes include:

- Incomplete syntax understanding.
- Dynamic language behavior.
- Reflection.
- Conditional compilation.
- External dependencies.
- Incorrect assumptions about input data.
- Missing type information.
- Incomplete interprocedural analysis.

Suppression mechanisms should therefore require justification and, where appropriate, independent approval.

A suppression should be traceable to the original finding and should have a defined review or expiration policy.

## 12. Performance and Scalability

Analysis performance depends on source size, rule complexity, dependency resolution, and the depth of inspection.

For basic lexical analysis, processing time is generally proportional to the number of source characters.

AST-based analysis typically adds processing and memory costs proportional to the size of the parsed program structure, although individual rules may be more expensive.

Important optimization techniques include:

- Reusing parsed syntax trees.
- Caching results using content hashes.
- Running independent file analysis concurrently.
- Limiting file sizes.
- Using indexed diagnostic storage.
- Analyzing only changed files where appropriate.
- Separating inexpensive checks from expensive security analysis.

The JavaScript implementation limits asynchronous concurrency.

The PostgreSQL implementation uses indexes to support repository reporting and finding retrieval.

The Python implementation processes source files independently.

## 13. Security and Operational Considerations

Static-analysis infrastructure itself requires security controls.

Important considerations include:

- Never execute analyzed source code as part of routine inspection.
- Treat source files as untrusted input.
- Avoid unrestricted dynamic evaluation.
- Restrict access to repository credentials.
- Protect analysis reports containing sensitive source excerpts.
- Validate file paths and file sizes.
- Avoid exposing secrets through diagnostic messages.
- Protect formatter operations from accidental source replacement.
- Require authorization for suppression approvals.
- Preserve analysis history for auditability.

The example implementations use lightweight syntax or pattern checks. They should not be represented as complete security verification systems.

In particular, detecting a dangerous function name does not establish whether an exploit is possible. Security conclusions require examination of input sources, validation, data flow, execution context, and application behavior.

## 14. Testing and Validation Strategy

The implementations include executable demonstrations and validation paths.

A broader test strategy should evaluate the following cases:

| Test case | Expected behavior |
|---|---|
| Clean source file | No relevant diagnostics |
| Trailing whitespace | Formatting warning |
| Excessive line length | Line-length warning |
| Missing final newline | Formatting warning |
| Unsafe dynamic evaluation | Security error |
| Bare exception handling | Reliability warning |
| Invalid source syntax | Syntax error where supported |
| Missing file | File-access diagnostic |
| Duplicate rule identifier | Registration rejected |
| Unknown suppression rule | Suppression rejected |
| Expired suppression | Finding remains active |
| Analysis failure | Quality gate does not pass |
| Error threshold exceeded | Quality gate fails |
| Valid completed analysis | Policy-based evaluation |

Tests should also verify that formatting preserves program behavior, suppression cannot bypass authorization, and analysis reports correspond to the correct source revision.

## 15. Practical Engineering Limitations

The five implementations intentionally demonstrate different analysis architectures rather than claiming complete language coverage.

| Implementation | Main limitation |
|---|---|
| Python | Limited AST rules; no complete type or data-flow analysis |
| JavaScript | Lightweight pattern checks; no complete scope-aware AST analysis |
| C++17 | Regex-based source inspection; no C++ grammar or type analysis |
| Java 17 | Basic source-pattern inspection; no compiler-level semantic analysis |
| PostgreSQL | Stores and evaluates analysis results; does not independently parse source languages |

The distinction between a demonstration analyzer and a production analyzer is important.

A production implementation needs language-aware parsing, configurable rule definitions, reliable source locations, testable rule behavior, controlled formatting, audit trails, and integration with repository development processes.

The central engineering principle is that source inspection, formatting, diagnostic interpretation, and quality-policy enforcement are separate operations that should remain independently configurable and auditable.
