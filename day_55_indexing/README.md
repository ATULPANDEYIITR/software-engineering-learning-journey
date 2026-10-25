# Indexing and Query Performance

## Scope

This project studies database indexing as a performance mechanism rather than as a generic database feature.

The central distinction is between the logical table and the physical access paths used to find rows efficiently.

The implementations model:

- table storage
- B-tree-style indexes
- composite indexes
- partial indexes
- covering indexes
- selectivity
- sequential scans
- index scans
- index-only scans
- query-cost estimation
- index maintenance
- validation and failure handling
- PostgreSQL execution-plan inspection

The examples use an order-processing workload because it produces realistic equality filters, composite predicates, reporting queries, selective lookups, and write-heavy maintenance considerations.

## Core Model

A useful abstraction is:

Table rows
|
+-- Primary table storage
|
+-- Index: customer_id
|
+-- Index: status + region + created_at
|
+-- Partial index: paid customer_id
|
+-- Covering index: region + created_at
|
+-- Query planner
|
+-- Access path
|
+-- Result rows

An index does not change the logical meaning of a query. It changes the physical route used to locate the qualifying rows.

A query can therefore be correct without an index while still being inefficient at scale.

## Index Structures

An index stores searchable keys separately from the main table representation.

For a B-tree index on `customer_id`, a conceptual structure is:

`customer_id -> row location`

A composite index on `(customer_id, created_at)` is conceptually:

`customer_id -> created_at -> row location`

The order of composite keys matters. A query constraining the leading column can normally exploit the index much more directly than a query constraining only a later column.

Indexes therefore represent access paths rather than arbitrary collections of columns.

## B-Tree Indexes

B-trees are suited to ordered access patterns.

They support efficient operations such as:

- equality lookup
- range predicates
- ordered retrieval
- prefix-based composite-key searches
- retrieving the first or last values efficiently

A typical lookup has an approximate structure of:

`root -> internal node -> leaf -> matching entries`

The exact implementation is database-specific, but the important performance property is that the search does not normally require inspecting every table row.

The Python, JavaScript, C++17, and Java 17 implementations use sorted index-entry representations to model this behavior.

The PostgreSQL implementation uses native B-tree indexes.

## Composite Indexes

Consider an index:

`(customer_id, created_at)`

A query such as:

`customer_id = 42`

can use the first key.

A query such as:

`customer_id = 42 AND created_at >= ...`

can use both dimensions more effectively.

A query that filters only on:

`created_at >= ...`

does not have the same direct leading-key advantage because `customer_id` is the first indexed dimension.

This is the reason index column order is a design decision rather than a cosmetic choice.

The PostgreSQL script explicitly demonstrates this distinction through `EXPLAIN (ANALYZE, BUFFERS)`.

## Selectivity

Selectivity describes how much a predicate reduces the candidate row set.

A highly selective predicate may reduce:

`1,000,000 rows -> 50 rows`

A weakly selective predicate may reduce:

`1,000,000 rows -> 800,000 rows`

An index is not automatically faster merely because it exists.

If a query needs a large percentage of the table, PostgreSQL may correctly choose a sequential scan because following an index and then retrieving many table rows can cost more than reading the table sequentially.

The planner therefore evaluates an access path against estimated workload cost.

## Query Cost

The source implementations use simplified cost models rather than reproducing PostgreSQL's internal planner.

The model uses:

`sequential cost ≈ number of table rows`

and:

`index cost ≈ traversal cost + qualifying row cost`

A covering index receives a lower modeled cost because fewer table lookups are required.

These values are educational approximations. They are not PostgreSQL cost constants.

Real PostgreSQL planning considers factors such as:

- relation statistics
- page counts
- random page cost
- sequential page cost
- CPU costs
- correlation
- estimated cardinality
- available indexes
- join strategies
- sort costs
- parallel execution
- visibility information

## Sequential Scans

A sequential scan examines table storage from beginning to end.

It can be appropriate when:

- the table is small
- the predicate is not selective
- most rows are required
- an index would cause excessive random access
- statistics indicate that the index path is more expensive

The four source implementations model this explicitly as `SEQUENTIAL_SCAN` or the equivalent language-specific representation.

The PostgreSQL script demonstrates cases where PostgreSQL can choose between an index path and a sequential path.

## Index Scans

An index scan first searches an index and then obtains the qualifying table rows.

The conceptual sequence is:

`predicate`
→ `index lookup`
→ `row identifiers`
→ `table rows`
→ `projection`

This can significantly reduce work for selective queries.

The trade-off is that the index itself must be maintained and table-row access may still be required.

## Index-Only Scans

A covering index contains enough information to satisfy the requested projection without fetching every corresponding table row.

For example, an index can use:

`region, created_at`

as key columns and include:

`customer_id, total_amount`

A query requesting those fields can potentially be satisfied primarily from the index.

PostgreSQL's actual ability to perform an index-only scan also depends on visibility-map state and other physical conditions. A covering index does not guarantee an index-only scan.

The Python, JavaScript, C++17, and Java 17 models treat coverage as a planning factor.

The PostgreSQL implementation uses `INCLUDE` columns and `EXPLAIN (ANALYZE, BUFFERS)` to inspect the actual plan.

## Covering Indexes

A covering index is designed around a complete query access pattern.

For a query that filters on `region` and orders by `created_at`, an index such as:

`(region, created_at DESC) INCLUDE (customer_id, total_amount)`

can support both filtering and result projection.

The advantage is reduced table access.

The cost is additional index storage and additional work during writes.

Covering indexes should therefore be justified by important query workloads rather than added indiscriminately.

## Partial Indexes

A partial index contains only rows satisfying a predicate.

The PostgreSQL implementation contains:

`WHERE status = 'paid'`

This is useful when a workload repeatedly accesses a relatively small subset of rows.

Advantages can include:

- smaller index size
- fewer index entries
- reduced maintenance work for rows outside the predicate
- efficient access to the targeted subset

The query predicate must be compatible with the partial-index condition for the optimizer to use that index appropriately.

Partial indexing is therefore both a physical-design decision and a workload-specific decision.

## Python Implementation

The Python implementation models a complete in-memory table.

The `Row` dataclass represents an order.

The `Index` dataclass stores:

- index name
- key columns
- included columns
- optional predicate
- sorted index entries

The `Table` class manages:

- row insertion
- index creation
- index maintenance
- selectivity estimation
- plan selection
- query execution
- validation

The `QueryPlan` object separates planning from execution.

The planner considers whether an index:

1. is applicable,
2. matches an equality prefix,
3. covers the requested columns,
4. has a lower estimated cost than a sequential scan.

The script also demonstrates write amplification by maintaining multiple indexes after a new row is inserted.

## JavaScript Implementation

The JavaScript implementation uses an event-driven model.

`RepositoryDatabase` extends Node.js `EventEmitter`.

Events include:

- `rowInserted`
- `indexCreated`
- `queryExecuted`

This separates database operations from operational observation.

The JavaScript index model uses:

- classes
- arrays
- `Map`
- `Set`
- immutable object copies
- validation exceptions
- event emission

The implementation intentionally differs from the Python structure by emphasizing asynchronous-service-style event boundaries and immutable data handling.

The partial-index representation uses a predicate object, while the planner evaluates equality-prefix compatibility and index coverage.

## C++17 Implementation

The C++17 implementation treats the indexing engine as a compact systems-oriented component.

Its main domain types are:

- `Order`
- `Query`
- `QueryPlan`
- `Index`
- `OrderTable`

The `Index` stores sorted entries consisting of:

`key + rowId`

The implementation uses STL containers such as:

- `vector`
- `map`
- `unordered_map`
- `optional`

The query planner calculates an estimated cost for each applicable index and compares it with the sequential-scan cost.

C++ exception handling is used for invalid states such as:

- duplicate identifiers
- invalid status
- negative monetary amounts
- unknown indexed columns
- missing rows referenced by index entries

This provides a systems-oriented perspective on data structures and explicit resource relationships.

## Java 17 Implementation

The Java implementation models indexing as an enterprise service boundary.

Java records represent immutable domain values such as:

`Order`

`Query`

`QueryPlan`

The `Index` class encapsulates:

- key columns
- included columns
- predicates
- index entries
- equality-prefix checks
- coverage checks

The repository service separates:

- data validation
- index creation
- index maintenance
- selectivity estimation
- query planning
- query execution

A functional `IndexPredicate` allows partial-index behavior to be represented explicitly.

The implementation also uses Java collections and stream operations for statistics and validation.

## PostgreSQL Relational Model

The PostgreSQL script creates the `indexing_lab` schema.

The principal tables are:

| Table | Purpose |
|---|---|
| `repositories` | Repository ownership and identity |
| `customers` | Customer and regional attributes |
| `orders` | Main transactional workload |
| `order_events` | Order lifecycle events |

The model uses:

- primary keys
- foreign keys
- unique constraints
- check constraints
- indexes
- triggers
- functions
- views
- CTEs
- transactions

The database itself enforces important validity conditions rather than relying exclusively on application code.

## PostgreSQL Index Design

The script creates several deliberately different indexes.

| Index | Design purpose |
|---|---|
| `idx_orders_customer` | Customer equality lookup |
| `idx_orders_customer_created` | Customer filtering plus date ordering |
| `idx_orders_status_region_created` | Composite status and regional filtering |
| `idx_orders_paid_customer` | Partial index for paid orders |
| `idx_orders_region_covering` | Filtering, ordering, and projection coverage |

These indexes represent different workload assumptions.

They should not be interpreted as universally optimal.

A production database should retain indexes that correspond to actual query patterns and remove indexes that provide insufficient value relative to their storage and write-maintenance cost.

## Query Planning Workflow

The conceptual workflow is:

`SQL query`
→ `parse`
→ `candidate access paths`
→ `statistics`
→ `cost estimation`
→ `chosen plan`
→ `execution`
→ `rows`

The source-language implementations simplify this process to make the access-path decision visible.

PostgreSQL performs the actual planning process and can expose the resulting plan through `EXPLAIN`.

## EXPLAIN and EXPLAIN ANALYZE

The PostgreSQL script uses:

`EXPLAIN (ANALYZE, BUFFERS)`

`EXPLAIN` describes the selected execution plan.

`ANALYZE` executes the statement and reports actual execution information.

`BUFFERS` provides buffer-access information useful for understanding physical I/O behavior.

Important plan attributes include:

- estimated rows
- actual rows
- scan type
- index chosen
- execution time
- buffer activity

A performance investigation should compare estimated and actual cardinalities rather than looking only at the presence of an index.

## Statistics

Query planners depend on statistics.

The PostgreSQL script runs `ANALYZE` after loading sample data.

Statistics help PostgreSQL estimate:

- value distributions
- cardinality
- selectivity
- likely row counts

Poor or stale statistics can lead to an inappropriate access path even when a suitable index exists.

This is why indexing and statistics management are connected aspects of query performance.

## Index Maintenance Cost

Indexes improve read paths but increase write work.

For an insert:

`table write`
+
`index maintenance`
+
`index maintenance`
+
`index maintenance`

The exact work depends on the number and type of indexes.

Updates can also be expensive when indexed columns change because index entries may need modification.

This creates a fundamental trade-off:

`faster important reads`
versus
`more storage and write maintenance`

An index should therefore be justified by workload value.

## Write Amplification

Suppose a table has four secondary indexes.

A single inserted row may require:

`1 table insertion + 4 index insertions`

This is a simplified conceptual model.

Real database behavior includes page management, WAL generation, locking, visibility information, and other storage-engine operations.

The source implementations explicitly count base writes and maintain index entries to make this trade-off visible.

## Index Bloat and Storage

Indexes consume storage.

Frequent updates, deletes, and changing workloads can increase physical fragmentation or bloat depending on the database and workload.

PostgreSQL uses MVCC, so updates create new row versions rather than simply replacing data in place.

Index design therefore needs to consider:

- index size
- update frequency
- vacuum behavior
- table growth
- write volume
- query frequency

A theoretically useful index can become operationally expensive if it is rarely used.

## Validation and Failure Handling

The implementations reject invalid records such as:

- duplicate identifiers
- unknown statuses
- negative monetary values
- unknown columns

The PostgreSQL database adds trigger-based rules for status transitions.

For example, a cancelled order cannot return to an active state.

These rules are separate from indexing itself, but they demonstrate an important production principle:

Performance structures should not weaken data integrity.

## Transactional Integrity

The PostgreSQL script uses an explicit transaction for a multi-step write.

The workflow is:

`BEGIN`
→ insert order
→ insert corresponding event
→ `COMMIT`

If a failure occurs before commit, the transaction can be rolled back rather than leaving an incomplete multi-table operation.

Indexes participate in the same transactional database system.

The application does not need to treat index maintenance as an independent business transaction.

## Performance Trade-offs

| Design choice | Primary benefit | Primary cost |
|---|---|---|
| Single-column index | Simple selective lookup | Limited query coverage |
| Composite index | Multiple related predicates | More storage and maintenance |
| Covering index | Reduced table access | Larger index |
| Partial index | Small targeted index | Limited applicability |
| Sequential scan | Efficient for large result sets | Reads many rows |
| Index scan | Efficient for selective queries | Random/table access may remain |
| Index-only scan | Can avoid table fetches | Requires sufficient index coverage and favorable visibility state |

## Common Indexing Errors

### Indexing every column

Adding an index to every column increases storage and write overhead.

It also creates more choices for the planner without guaranteeing a useful access path.

### Ignoring column order

For a composite index, `(customer_id, created_at)` and `(created_at, customer_id)` are not equivalent.

The leading column strongly influences which predicates can exploit the index efficiently.

### Assuming every index will be used

A valid index can remain unused because:

- the predicate is not selective
- another index is cheaper
- a sequential scan is cheaper
- statistics favor another plan
- the query cannot exploit the index structure
- the query accesses a different column pattern

### Ignoring write workload

A read-heavy system may justify many indexes.

A write-heavy transactional system may require a much smaller index set.

### Using a covering index without measuring

Included columns increase index size.

Coverage should be based on important queries and measured workload behavior.

## Security Considerations

Indexing is primarily a performance concern, but production implementations still require secure data handling.

Important controls include:

- parameterized SQL rather than string-built queries
- least-privilege database roles
- restricted administrative access
- protection of sensitive indexed values
- controlled access to query-plan information
- avoidance of exposing internal database structure unnecessarily
- validation of application inputs

Indexes can contain copies of data values. Sensitive columns should therefore not be indexed casually without considering storage, access, and operational exposure.

## Edge Cases

Important cases represented in the implementations include:

- empty tables
- no matching index
- no matching rows
- low-selectivity predicates
- composite-index leading-column mismatch
- duplicate primary keys
- invalid status values
- negative monetary values
- partial-index applicability
- covering versus non-covering projections
- write maintenance after index creation

These cases demonstrate why index selection cannot be reduced to the rule "indexes make queries faster."

## Practical Investigation Workflow

A disciplined indexing investigation can follow:

`Identify slow query`
→ `capture actual SQL`
→ `inspect predicates`
→ `inspect ordering`
→ `inspect row counts`
→ `EXPLAIN ANALYZE`
→ `check statistics`
→ `evaluate existing indexes`
→ `test candidate index`
→ `measure read improvement`
→ `measure write/storage cost`
→ `retain or reject`

The important step is measurement.

An index should solve an observed workload problem rather than being created solely because a column appears frequently in queries.

## Repository Structure

The five executable artifacts have distinct implementation roles:

| File | Role |
|---|---|
| Python | In-memory indexing and query-plan simulation |
| JavaScript | Event-driven indexing and query service |
| C++17 | Systems-oriented governance and access-path engine |
| Java 17 | Enterprise domain and service model |
| PostgreSQL | Executable relational database implementation |

The implementations share the same conceptual domain but use language-specific structures and engineering decisions.

## Educational Mapping

The progression across the implementations is:

`Data model`
→ `Index structure`
→ `Predicate matching`
→ `Selectivity`
→ `Cost estimation`
→ `Access-path selection`
→ `Execution`
→ `Write maintenance`
→ `Database-level enforcement`

This separates logical correctness from physical performance.

A query must first produce the correct result. Indexing then determines whether that result can be produced efficiently under the workload's physical constraints.

## Limitations of the Simulation

The Python, JavaScript, C++17, and Java 17 programs are educational query engines rather than database storage engines.

They do not reproduce:

- PostgreSQL page layout
- WAL
- MVCC visibility rules
- buffer management
- locking
- vacuum
- parallel query execution
- PostgreSQL's full cost model
- actual disk I/O
- planner statistics internals

Their purpose is to expose the important relationships among predicates, indexes, selectivity, coverage, and access-path selection.

The PostgreSQL implementation provides the actual database execution environment for the corresponding concepts.

## Central Distinction

The most important distinction in this project is:

`Index existence` is not the same as `index usefulness`.

A useful index is one whose structure matches an important workload, provides a sufficiently selective or otherwise advantageous access path, and produces enough performance value to justify its storage and maintenance cost.

That distinction connects index structure directly to real query performance rather than treating indexing as a purely syntactic database feature.
