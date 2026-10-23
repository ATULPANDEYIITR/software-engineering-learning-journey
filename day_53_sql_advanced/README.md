# SQL Advanced: Joins, Subqueries, CTEs, and Window Functions

## Scope

This project treats advanced SQL as a set of relational techniques for combining data, deriving intermediate results, and performing analytical calculations without losing row-level detail.

The five implementations use the same business domain, but each emphasizes a different computational perspective:

| File | Perspective | Main implementation |
|---|---|---|
| Python | Algorithmic simulation | Joins, grouped aggregation, subquery-style filtering, CTE-style stages, running totals, ranking |
| JavaScript | Event-driven data processing | Indexed joins, `Map`-based grouping, asynchronous execution, analytical transformations |
| C++17 | Performance-oriented engine | Hash-indexed joins, staged aggregation, partitions, running totals, ranking |
| Java 17 | Enterprise domain model | Records, immutable collections, validation, aggregation policies, analytical services |
| PostgreSQL | Relational execution | Joins, subqueries, CTEs, window functions, constraints, indexes, views, triggers, transactions |

The central relationship is:

**Joins combine relations → subqueries derive dependent results → CTEs structure multi-stage queries → window functions calculate across related rows while preserving detail.**

---

## Relational Scenario

The domain represents a sales analytics system containing customers, products, and sales transactions.

The core relationships are:

    customers
        │
        │ customer_id
        ▼
      sales ──────────► products

A customer can have many sales. A product can appear in many sales. Each sale records quantity, unit price, and date.

This model is useful because advanced SQL operations can be applied to the same underlying facts without artificially changing the business problem.

---

## Joins

Joins answer questions that require data from more than one relation.

### Inner Join

An inner join returns rows where the join condition matches on both sides.

The PostgreSQL implementation joins `sales` to `customers` and `products` to produce a transaction-level reporting relation containing:

- sale identifier
- customer name
- customer region
- product name
- quantity
- calculated revenue

The Python and JavaScript implementations model the same operation with keyed lookup structures. The C++ implementation uses an `unordered_map` as an explicit hash index. The Java implementation uses an immutable customer map for efficient key-based lookup.

A useful performance distinction is that a relational join is a logical operation, while PostgreSQL chooses a physical execution strategy such as nested-loop, hash, or merge join.

### Left Join

The SQL implementation also uses a left join to preserve customers that have no sales.

This distinction is important for reporting. An inner join would eliminate a customer with no matching transaction. A left join retains that customer and uses `COALESCE` to represent the missing aggregate as zero.

The result therefore answers a different business question:

**What is every customer's revenue, including customers who have not purchased anything?**

---

## Subqueries

A subquery allows one query to use the result of another query.

The customer-performance example first calculates lifetime revenue for each customer. An outer query then compares each customer's revenue against the average revenue across customers.

Conceptually:

    customer totals
          │
          ▼
    average customer total
          │
          ▼
    customers at or above average

The important distinction is that the inner aggregation produces a value or relation consumed by the outer query.

The same idea is implemented algorithmically in Python, JavaScript, C++, and Java. Each implementation first produces customer totals and then calculates the threshold used for filtering.

Subqueries can be scalar, correlated, or relation-producing. Their execution characteristics depend on the optimizer and query structure. A logically simple subquery is not necessarily executed as a separate independent operation.

---

## Common Table Expressions

A Common Table Expression, or CTE, gives a name to an intermediate relational result using `WITH`.

The SQL implementation uses multiple CTE stages for monthly analysis:

    sales
      │
      ▼
    monthly_sales
      │
      ▼
    monthly_baseline
      │
      ▼
    performance classification

The first CTE aggregates sales by month. The second derives the average monthly revenue. The final query compares each month against that baseline.

CTEs improve readability when a query contains multiple dependent transformations. They also provide a clear logical structure for complex analytical SQL.

A CTE should not automatically be interpreted as a performance optimization. PostgreSQL's optimizer can inline eligible CTEs or materialize them depending on the query and planner behavior.

---

## Window Functions

Window functions perform calculations across a related set of rows while retaining individual rows in the result.

This is the major distinction from `GROUP BY`.

`GROUP BY` reduces multiple rows into aggregate rows.

A window function calculates an aggregate or analytical value while preserving the original row.

### Running Total

The PostgreSQL implementation calculates customer running revenue with:

`SUM(revenue) OVER (PARTITION BY customer_id ORDER BY sale_date, sale_id ...)`

The logical stages are:

    sales
      │
      ├── partition by customer
      │
      ├── order within customer
      │
      └── accumulate revenue

For a customer with three transactions, the result can contain:

| Sale | Revenue | Running Revenue |
|---|---:|---:|
| 1 | 1200 | 1200 |
| 2 | 400 | 1600 |
| 3 | 820 | 2420 |

The Python, C++, and Java implementations explicitly maintain a running accumulator after partitioning and ordering the data.

### Ranking

The PostgreSQL implementation demonstrates:

- `RANK`
- `DENSE_RANK`
- `ROW_NUMBER`

These functions have different behavior when values tie.

`ROW_NUMBER` assigns a unique sequential position.

`RANK` gives equal values the same rank and leaves gaps after ties.

`DENSE_RANK` gives equal values the same rank without gaps.

This difference matters when producing leaderboards or regional customer rankings.

### Previous-Row Analysis

`LAG` accesses a preceding row in the same analytical partition.

The monthly analysis uses it to compare a customer's current monthly revenue with the previous available month.

This avoids procedural loops and allows change analysis to remain part of a declarative SQL query.

### Bucketing

`NTILE(4)` divides ordered customers into four groups.

This is useful for segmentation when a business wants relative groups such as high-, medium-, and low-value customers rather than fixed monetary thresholds.

---

## Python Implementation

The Python program models relational operations using standard-library data structures.

`Sale` is an immutable dataclass representing a transaction.

Dictionaries provide indexed grouping behavior:

- customer identifier → sales
- customer identifier → total
- month → aggregate

The program separates analytical operations into functions rather than embedding all processing inside the main execution path.

The subquery-style operation first calculates customer totals and then derives the average threshold.

The CTE-style operation creates an intermediate monthly aggregate before returning the final result.

The window-style implementation partitions sales by customer, orders each partition, and maintains a running value.

Validation rejects invalid identifiers, negative amounts, and malformed months.

The implementation is useful for understanding the algorithmic mechanics behind SQL without depending on a database engine.

---

## JavaScript Implementation

The JavaScript implementation uses `Map` and immutable objects to model relational transformations.

The `innerJoin` function builds an index for the lookup relation. This avoids scanning the entire right-side collection for every left-side row.

`groupBy` provides a reusable partitioning mechanism.

The analytical functions then operate over these partitions:

- customer aggregation
- subquery-style threshold filtering
- CTE-style monthly processing
- running totals
- regional ranking

The program uses `async` execution at the application boundary so the analytics pipeline can be integrated naturally into an asynchronous Node.js service.

Input validation checks collection type, identifiers, numeric amounts, and month representation.

The implementation emphasizes that a JavaScript data-processing pipeline can model relational logic, but database systems remain preferable for large persistent datasets because they provide indexing, transaction management, concurrency control, query optimization, and durable storage.

---

## C++17 Implementation

The C++ implementation treats advanced SQL concepts as a small analytical execution engine.

The `AnalyticsEngine` owns validated sales data and exposes separate operations for joins, aggregates, subquery-style filtering, CTE-style monthly processing, and window-style calculations.

The inner join uses an `unordered_map` as a hash index.

This illustrates a physical implementation concept:

    lookup relation
          │
          ▼
      hash index
          │
          ▼
    probe using foreign key
          │
          ▼
    matching joined rows

The C++ implementation also explicitly partitions rows before calculating running totals.

This makes memory and computational trade-offs visible. Building indexes and partitions improves lookup performance but requires additional memory.

The regional ranking implementation uses dense-ranking semantics so tied revenue values receive the same rank.

Input validation occurs before analytical processing, preventing malformed records from contaminating later calculations.

---

## Java 17 Implementation

The Java implementation uses an enterprise-oriented domain structure.

Records model immutable domain values:

- `Customer`
- `Sale`
- `CustomerTotal`
- `RunningSale`
- `RegionRank`

The constructor validation of records establishes domain invariants at object creation time.

The repository maintains an immutable customer lookup map and immutable sales collection.

Java Streams are used where they improve the expression of aggregation and transformation operations. Explicit loops remain where stateful window-style calculations are clearer.

The regional ranking operation models `RANK` behavior by comparing adjacent ordered aggregate values.

The use of `BigDecimal` rather than binary floating-point arithmetic is deliberate because monetary calculations require predictable decimal precision.

The `AggregationPolicy` interface also demonstrates how analytical behavior can be represented as a domain abstraction rather than embedded into unrelated application code.

---

## PostgreSQL Relational Model

The PostgreSQL implementation provides the most complete database representation.

The schema contains:

| Table | Role |
|---|---|
| `customers` | Customer dimension |
| `products` | Product dimension |
| `sales` | Transaction fact table |
| `customer_targets` | Customer-level performance targets |

Foreign keys preserve referential integrity.

Check constraints prevent invalid quantities, prices, names, regions, and categories.

A generated `revenue` column derives transaction revenue from quantity and unit price. This prevents duplicated application-side calculations for the stored value.

---

## Indexing

The SQL implementation creates indexes that support realistic access paths:

`(customer_id, sale_date)` supports customer transaction history and ordered customer analysis.

`product_id` supports product-based joins and filtering.

`sale_date` supports date-range filtering.

Indexes are not created indiscriminately. Each index consumes storage and increases write cost because index entries must also be maintained during inserts and updates.

The `EXPLAIN (ANALYZE, BUFFERS)` statement provides an operational method for examining whether the planner's selected execution strategy is appropriate.

---

## Constraints and Database-Level Validation

The database enforces important invariants independently of application code.

Examples include:

- positive quantities
- non-negative prices
- valid product categories
- valid foreign-key references
- unique product names
- valid customer names
- positive performance targets

The trigger adds rules that depend on the transaction being written, including preventing future sale dates.

Application validation is useful for user feedback, but database constraints are essential when multiple applications or services can write to the same database.

---

## Transaction Processing

The SQL script includes an explicit transaction for inserting a sale.

The transaction boundary demonstrates atomicity: either the operation commits successfully or an error prevents the invalid operation from becoming a partially committed database state.

In production systems, transaction boundaries should reflect business consistency requirements rather than being added mechanically around every query.

---

## Performance Considerations

Join performance depends on relation size, indexes, data distribution, and the optimizer's selected plan.

Aggregation can require sorting or hashing.

Window functions commonly require ordered processing within partitions.

CTEs improve logical organization but should not automatically be treated as faster than equivalent inline queries.

Subqueries can sometimes be transformed by the optimizer into joins or semi-joins.

For large datasets, execution plans should be examined rather than assuming that a particular SQL formulation is always faster.

The SQL implementation therefore includes `EXPLAIN ANALYZE` rather than making unsupported performance claims.

---

## Edge Cases

The implementations account for several cases that commonly cause analytical errors:

- customers without sales
- empty analytical result sets
- zero-value aggregates
- tied ranking values
- multiple sales on the same date
- ordering ambiguity
- invalid identifiers
- negative transaction values
- malformed month values
- future-dated transactions
- missing join matches
- division and average calculations over empty sets

A deterministic secondary key such as `sale_id` is used where chronological rows can otherwise have identical dates.

This is important for running totals because window ordering must be deterministic when cumulative results depend on row sequence.

---

## Conceptual Distinctions

| Mechanism | Primary purpose | Result behavior |
|---|---|---|
| `JOIN` | Combine related relations | Adds columns from matching rows |
| `LEFT JOIN` | Preserve the left relation | Keeps unmatched left rows |
| Subquery | Use a derived query result | Supplies a value or relation to another query |
| CTE | Name an intermediate query result | Structures multi-stage relational logic |
| `GROUP BY` | Aggregate groups | Reduces rows |
| Window function | Analyze related rows | Preserves individual rows |
| `RANK` | Rank with gaps after ties | Same rank for equal values |
| `DENSE_RANK` | Rank without gaps | Same rank for equal values |
| `ROW_NUMBER` | Unique sequential ordering | Every row receives a distinct number |
| `LAG` | Access a previous row | Enables period-over-period analysis |
| `NTILE` | Divide ordered rows into buckets | Produces analytical segments |

These mechanisms are related but are not interchangeable. A query becomes easier to reason about when each operation is selected according to the relational question being answered.

---

## Practical Query Architecture

A complex analytical query can often be understood as a sequence:

    Base relations
         │
         ▼
    Join related entities
         │
         ▼
    Filter invalid or irrelevant rows
         │
         ▼
    CTE / derived relation
         │
         ▼
    Aggregate or calculate thresholds
         │
         ▼
    Window analysis
         │
         ▼
    Final reporting order

This structure separates data combination, intermediate derivation, aggregation, and row-aware analytics.

The five implementations apply this architecture differently while preserving the same analytical concepts.
