# Database Optimization: Query Plans, Bottlenecks, and Optimization

## Technical Scope

This project models database optimization as a measurable engineering process rather than as a collection of isolated indexing rules.

The central workflow is:

`SQL workload → statistics → query plan → execution cost → bottleneck → optimization change → re-measurement`

The five implementations use the same conceptual domain while emphasizing different engineering techniques.

| Area | Primary concern |
|---|---|
| Query plans | Access paths, cardinality, joins, sorting, aggregation, estimated cost |
| Bottlenecks | Expensive scans, joins, sorting, aggregation, I/O, poor cardinality estimates |
| Indexing | Selectivity, covering indexes, index maintenance cost |
| Statistics | Distinct values, null fractions, estimated rows, data distribution |
| Validation | Estimated versus actual execution behavior |
| Optimization | Changing access paths and measuring the resulting plan |

The implementations intentionally use simplified cost models. They explain the mechanics of optimization without pretending to reproduce PostgreSQL's complete planner.

## Core Optimization Model

A query optimizer attempts to select an execution strategy with an acceptable estimated cost.

A simplified model used by the source files is:

`Total Cost = Scan Cost + Join Cost + Sort Cost + Aggregate Cost`

Scan selection depends heavily on estimated cardinality.

For a predicate such as:

`status = 'completed'`

the model approximates equality selectivity using the number of distinct values:

`selectivity ≈ 1 / distinct_values`

Estimated rows then become:

`estimated_rows = table_rows × combined_selectivity`

This estimate influences whether sequential access or an index-based access path is preferable.

## Query Plans

A query plan describes how a database intends to execute a statement.

The implementations distinguish:

- Sequential Scan
- Index Scan
- Index Only Scan
- Nested Loop
- Hash Join
- Merge Join
- Sort
- Aggregation

The important distinction is between the logical SQL operation and its physical execution.

For example, a query may logically request a filtered set of orders joined with customers. The physical plan can execute that request using a sequential scan followed by a hash join, or an index-driven access path followed by a nested loop.

The plan is therefore an optimization decision, not merely a representation of the SQL syntax.

## Bottleneck Identification

The Python, JavaScript, C++17, and Java 17 implementations calculate cost contributions for individual plan components.

A bottleneck is treated as an operation whose estimated cost is large enough to affect the complete workload.

Typical bottlenecks represented in the project include:

- scanning a large table without a selective access path
- reading many heap pages after an index lookup
- joining two large relations
- sorting a large intermediate result
- aggregating excessive rows
- inaccurate cardinality estimates
- indexes that do not provide enough selectivity

The important operational rule is that an optimization should target a measured bottleneck rather than simply add indexes.

## Cardinality Estimation

Cardinality is the estimated number of rows produced by an operation.

It is one of the most important inputs to query planning because join and access-path decisions depend on it.

The project deliberately models a situation where:

`estimated_rows != actual_rows`

A substantial discrepancy can cause the optimizer to select a poor plan.

For example, if the optimizer expects a predicate to return 2,000 rows but the real execution produces 400,000 rows, a nested-loop strategy that looked inexpensive during planning can become expensive during execution.

The PostgreSQL implementation records both estimated and actual values and reports their ratio.

## Access Paths

### Sequential Scan

A sequential scan reads the table relation broadly.

It is often appropriate when:

- a large percentage of rows is required
- the table is small
- an index would cause excessive random access
- no suitable index exists

A sequential scan is not automatically a bad plan.

### Index Scan

An index scan uses an index to locate qualifying rows.

It is most useful when the predicate is selective enough that avoiding most table pages outweighs index traversal and heap-access costs.

### Index Only Scan

An index-only scan can avoid fetching table rows when the required columns are available from the index and PostgreSQL's visibility conditions permit index-only access.

The source implementations represent this through covering columns.

The SQL implementation records an example of a covering index on `status` and `created_at` with `customer_id` and `total_amount` included.

## Composite Indexes

The optimization scenario uses a workload containing:

`status = 'completed'`

and:

`created_at >= DATE '2026-01-01'`

A composite index beginning with:

`(status, created_at)`

matches the predicate structure more directly than unrelated single-column indexes.

The example also models included columns:

`customer_id`

and:

`total_amount`

This can reduce additional table access for workloads that only need those values.

The actual usefulness of such an index depends on data distribution, query frequency, write volume, storage, and competing indexes.

## Join Optimization

The implementations compare three conceptual join strategies.

| Join | Typical strength |
|---|---|
| Nested Loop | Small outer input or efficient indexed inner lookup |
| Hash Join | Large equality joins |
| Merge Join | Inputs already ordered or cheaply sortable |

A nested loop can be excellent for a small filtered relation joined into an indexed table.

The same strategy can become expensive when the outer relation is large and the inner relation cannot be efficiently searched.

A hash join can process large equality joins efficiently but requires memory for hash structures.

A merge join can benefit from existing ordering but may incur sorting costs when inputs are not already ordered.

## Sorting and Aggregation

The workload groups orders by customer region and orders the final result by aggregated value.

Sorting has a cost that grows with the number of rows being sorted.

Aggregation also becomes more expensive when unnecessary rows reach the aggregation stage.

This creates an important optimization principle:

`Reduce unnecessary rows as early as safely possible`

Selective predicates and appropriate access paths can reduce the size of intermediate results before joins, sorting, or aggregation.

## Python Implementation

The Python implementation models optimization using:

- `dataclass`
- `Enum`
- dictionaries
- lists
- tuples
- validation
- exceptions
- assertions
- explicit plan objects

`TableStats` stores table cardinality, page counts, column statistics, and indexes.

`Predicate` calculates simplified selectivity.

`QueryOptimizer` evaluates scan and join alternatives.

`QueryPlan` aggregates the estimated costs and exposes bottleneck information.

The script also compares a baseline plan with a plan containing a covering composite index.

It includes edge cases for:

- full-table scans
- unknown columns
- null predicates
- non-selective indexes
- statistics changes

The production checks emphasize comparing estimates with actual execution behavior and avoiding unsafe SQL construction.

## JavaScript Implementation

The JavaScript version treats optimization analysis as an asynchronous workload-analysis service.

It uses:

- classes
- `Map`
- `Set`
- Promises
- `EventEmitter`
- structured plan objects
- validation errors

`WorkloadAnalyzer` emits events when an analysis starts, completes, or fails.

This models an application that may evaluate multiple query workloads asynchronously rather than running a single procedural demonstration.

JavaScript's `Set` is used to represent covering-index columns, while `Map` stores column statistics.

The event-driven architecture separates workload orchestration from cost calculation.

## C++17 Implementation

The C++17 implementation presents optimization as a governance-oriented execution engine.

It uses:

- strongly typed enumerations
- structs
- STL containers
- `std::map`
- `std::vector`
- `std::optional`-compatible design
- algorithms
- exceptions
- explicit validation

The optimizer evaluates candidate join algorithms and selects the minimum estimated cost.

`GovernanceEngine` validates the structural integrity of table statistics before planning.

This design emphasizes deterministic computation, explicit ownership of data structures, and low-level control over the optimization model.

## Java 17 Implementation

The Java implementation uses an enterprise-oriented domain model.

Important domain types include:

- `TableStats`
- `IndexDefinition`
- `Predicate`
- `ScanPlan`
- `JoinPlan`
- `QueryPlan`
- `QueryContext`
- `QueryOptimizer`
- `RepositoryOptimizationService`

Java records provide immutable value objects for statistics and plan components.

`QueryContext` explicitly models state transitions:

`RECEIVED → PLANNED → ANALYZED → OPTIMIZED`

Invalid transitions produce an `OptimizationException`.

This separates query lifecycle management from optimization calculations and reflects the kind of explicit domain state commonly required in enterprise services.

## PostgreSQL Implementation

The PostgreSQL script provides the most database-oriented representation.

The schema stores:

- repositories
- users
- branches
- commits
- query workloads
- query executions
- indexes
- optimization findings

The core optimization information is represented by `query_workloads` and `query_executions`.

`query_workloads` stores estimated and actual cardinality and duration.

`query_executions` stores:

- plan hash
- access path
- join strategy
- sort method
- rows removed by filtering
- shared-buffer hits
- shared-buffer reads
- execution time

This allows optimization analysis to compare planner assumptions with observed execution behavior.

## PostgreSQL Constraints

The relational model uses database-level validation instead of relying entirely on application code.

Examples include:

- primary keys
- foreign keys
- unique constraints
- `CHECK` constraints
- enumerated status values
- partial indexes

For example, execution duration cannot be negative, and optimization severity is restricted to defined values.

This prevents invalid optimization telemetry from entering the database.

## PostgreSQL Views

`workload_performance_report` combines workload metadata with execution information.

It calculates:

`actual_to_estimated_ratio`

This provides a direct way to identify cardinality estimation problems.

`plan_regression_report` compares the most recent execution with the previous execution for the same workload.

This supports detection of performance changes across plan versions.

## PostgreSQL Function

`validate_workload()` evaluates workload health using SQL.

It detects:

- substantially underestimated row counts
- substantially overestimated row counts
- failed workloads

The function returns a workload identifier, issue description, and severity.

This makes validation reusable from SQL queries and transactional workflows.

## Transactional Workflow

The PostgreSQL script uses a transaction when inserting findings generated from workload validation.

The workflow is:

`validate workload → classify finding → record recommendation → commit`

If the transaction fails, PostgreSQL can roll back the complete operation rather than leaving a partially updated optimization record.

## Statistics and Plan Quality

Optimizer statistics influence cardinality estimation.

The examples model statistics such as:

- distinct-value count
- null fraction
- table row count
- page count

Real PostgreSQL planning uses substantially richer statistics.

The practical implication is that query optimization cannot be separated from statistics maintenance.

A query may remain unchanged while its optimal plan changes because:

- table size changes
- value distribution changes
- correlation changes
- data becomes skewed
- index selectivity changes

## Index Trade-offs

Indexes improve some reads but introduce costs.

| Benefit | Cost |
|---|---|
| Faster selective lookup | Additional storage |
| Possible index-only access | Additional write maintenance |
| Faster ordering for some queries | Vacuum and maintenance overhead |
| Better join access | More complex schema |
| Reduced heap access | More indexes to maintain |

An index should therefore be evaluated against workload frequency and measured benefit.

Adding an index merely because a query is slow can produce an unnecessarily large index set.

## Execution Metrics

The PostgreSQL model records shared-buffer hits and reads.

A high number of shared reads can indicate substantial physical I/O pressure, although buffer behavior must be interpreted with workload context.

Execution time is also recorded.

A useful diagnostic comparison is:

`estimated cost → actual execution time → actual rows → buffer activity`

No single metric is sufficient to explain every performance problem.

## Edge Cases

The implementations explicitly handle several cases:

- no predicates
- unknown predicate columns
- low-selectivity predicates
- missing indexes
- covering versus non-covering indexes
- failed workloads
- invalid state transitions
- inaccurate cardinality estimates
- zero-like values protected by validation
- excessive index storage

A sequential scan is allowed when it is cheaper than an index scan under the model.

This is important because optimization means selecting an appropriate plan, not maximizing index usage.

## Security Considerations

Query optimization tooling can expose sensitive information through SQL text, execution plans, identifiers, and workload statistics.

Production implementations should therefore:

- use parameterized SQL
- restrict access to diagnostic execution
- avoid storing unnecessary sensitive query literals
- separate application and administrative database roles
- restrict index-management privileges
- audit changes to performance-critical database structures

The source programs model optimization decisions but do not attempt to replace PostgreSQL's authorization system.

## Performance Considerations

The source implementations use simplified formulas rather than executing real database queries.

Their purpose is to make planning mechanics explicit.

The Python, JavaScript, C++17, and Java 17 models operate primarily on metadata, so their computational cost is small compared with executing the represented database workload.

The PostgreSQL implementation stores execution observations relationally and creates indexes only for frequently queried reporting paths.

The real performance question is always the database workload itself.

## Important Distinction

Database optimization should separate four different questions:

| Question | Meaning |
|---|---|
| What does the query request? | Logical SQL semantics |
| How will the database execute it? | Physical query plan |
| Why is execution expensive? | Bottleneck analysis |
| What change should be made? | Optimization decision |

Changing SQL, creating an index, refreshing statistics, changing a join strategy, or increasing available memory are different interventions.

They should not be treated as interchangeable solutions.

## Practical Optimization Workflow

The complete technical workflow represented by the project is:

`Workload`
→ `Measure`
→ `Inspect plan`
→ `Compare estimates with actuals`
→ `Identify dominant cost`
→ `Form optimization hypothesis`
→ `Change index/query/statistics`
→ `Re-plan`
→ `Benchmark`
→ `Validate regression risk`

The key principle is measurement before and after the optimization.

## Limitations

The cost models in the source programs are educational approximations.

They do not reproduce all PostgreSQL planner behavior, including:

- multivariate statistics
- visibility-map behavior
- detailed page-level costing
- parallel execution
- work memory spilling
- partition pruning
- incremental sort
- bitmap scan costing
- extended statistics
- planner configuration parameters
- concurrent workload effects
- operating-system cache behavior

The PostgreSQL artifacts provide the closest representation of real database optimization because they model actual relational structures and PostgreSQL-specific SQL constructs, while the other implementations isolate planning concepts for explicit comparison.
