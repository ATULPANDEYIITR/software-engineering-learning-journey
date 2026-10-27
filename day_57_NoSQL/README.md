# NoSQL Data Models: Document, Key-Value, Column-Family, and Graph Databases

## Scope

This project implements four major NoSQL data models as related but technically distinct storage approaches:

| Model | Primary organization | Typical access pattern | Main strength |
|---|---|---|---|
| Document | Self-contained records | Retrieve or update an aggregate | Flexible nested data |
| Key-value | Key mapped directly to a value | Exact-key lookup | Simple, fast access |
| Column-family | Sparse rows and grouped columns | Row or column-oriented retrieval | Large sparse datasets |
| Graph | Nodes and relationships | Traversal across connected entities | Relationship-centric queries |

The implementations use a common operational scenario involving devices, telemetry, services, teams, repositories, sessions, and databases. The scenario is intentionally shared so that the data-model differences can be compared without treating the models as interchangeable.

The central distinction is the shape of the access problem:

`Document -> aggregate record`

`Key -> value`

`Row key -> sparse columns`

`Node -> relationship -> node`

## Domain Model

The technical scenario contains four different representations of operational information.

A document record represents an entity whose attributes naturally belong together. A device document can contain identity, department, region, capabilities, security information, and nested state.

A key-value record represents directly addressable state such as a session, counter, cache entry, or temporary token state.

A column-family record represents a sparse operational row. Different devices may have different populated measurements, so a row does not require every possible column to exist.

A graph represents relationships among teams, repositories, services, databases, and devices. The important information is not only the node attributes but also how nodes are connected.

## Document Databases

Document databases store records as documents, commonly represented using JSON-like structures. A document can contain nested objects, arrays, and fields that are not shared by every record.

The Python implementation uses `Document` objects containing dictionaries and maintains secondary field indexes for scalar values. Updates replace or add fields while incrementing a document version. This models an aggregate-oriented workflow in which related attributes are normally read together.

The JavaScript implementation uses objects and `structuredClone` to isolate stored values from caller-owned objects. A `Map` stores document records, while another `Map` structure maintains field indexes.

The C++ implementation represents document fields using `std::variant`. This makes the permitted scalar types explicit instead of allowing arbitrary executable or pointer-like values.

The Java implementation uses immutable `record` instances. Updating a document constructs a new record with an incremented version rather than mutating the existing record in place.

The PostgreSQL representation uses `JSONB`. A GIN index supports containment and key-oriented JSON queries. This provides a relational implementation of flexible document storage while retaining PostgreSQL transaction and constraint facilities.

### Document characteristics

Documents are useful when:

- related attributes are normally retrieved together;
- record structures evolve over time;
- nested data is meaningful;
- application aggregates map naturally to stored documents.

A flexible schema does not eliminate the need for validation. The implementations still validate identifiers, enforce valid states, and reject invalid operations.

A document database also does not automatically make arbitrary joins inexpensive. If an application repeatedly requires relationships across independent documents, a graph or another data model may represent the workload more directly.

## Key-Value Databases

A key-value database organizes information around a unique key. The database does not need to understand the internal structure of the value for a basic lookup.

The Python implementation stores values with optional expiration timestamps and supports compare-and-set behavior. This is appropriate for sessions, counters, cached results, and other state that can be retrieved directly.

The JavaScript implementation uses `Map` and provides asynchronous event processing around key-value operations. Expiration is checked when values are accessed.

The C++ implementation uses `std::unordered_map`, giving average constant-time key lookup. TTL values are represented using `std::chrono`, making expiration behavior explicit in the type system.

The Java implementation models key-value entries with a private immutable `Entry` record containing the value and expiration timestamp. A compare-and-set operation provides conditional state replacement.

The PostgreSQL implementation uses a primary key on `key`, JSONB for the stored value, and an optional `expires_at` column. A partial index targets rows where expiration is present.

### Key-value characteristics

Key-value storage is a strong fit for:

- sessions;
- feature flags;
- counters;
- temporary state;
- cache entries;
- idempotency keys;
- direct object retrieval.

Its simplicity is also its principal constraint. A workload requiring arbitrary queries over many value attributes may be better represented by a document, column-family, relational, or graph model.

TTL is a lifecycle mechanism rather than a security mechanism. Expiring a session record does not replace authentication, authorization, encryption, access control, or audit requirements.

## Column-Family Databases

Column-family systems organize data around rows and columns while allowing records to remain sparse. They are particularly useful for workloads where the access pattern is known in advance and data volume can be very large.

The Python implementation stores each row as a `ColumnFamilyRow` containing a dictionary of populated columns. One device can contain temperature, signal quality, and firmware while another may contain only signal quality.

The JavaScript implementation represents each row as a `Map`. This makes column presence explicit and avoids requiring every row to contain the same fields.

The C++ implementation uses an `unordered_map` of `WideRow` objects. The design emphasizes sparse access and predictable lookup rather than arbitrary object nesting.

The Java implementation uses nested collections and provides projection through a requested-column set. This models an application that reads only the measurements needed by a particular operation.

The PostgreSQL implementation uses nullable columns in `column_family_rows`. The sparse representation is demonstrated through rows with different populated attributes. An index on signal quality supports a common filtering operation.

### Column-family characteristics

Column-family storage is useful when:

- records are naturally identified by a row key;
- the dataset is sparse;
- access patterns are predictable;
- very large datasets require partition-oriented design;
- applications commonly retrieve selected columns.

A column-family model requires careful key and partition design. A poorly chosen partition key can create hotspots or excessively large partitions in distributed systems.

The presence of nullable columns in the PostgreSQL representation should not be interpreted as a complete implementation of a distributed column-family database. It is a relational simulation of the sparse data model and its access patterns.

## Graph Databases

Graph databases model entities as nodes and relationships as edges. Properties can be attached to both nodes and relationships.

The Python implementation uses dictionaries for nodes and adjacency lists for directed edges. Breadth-first search computes an unweighted shortest path.

The JavaScript implementation uses `Map` objects for nodes and adjacency lists. Its traversal method demonstrates how graph-oriented queries differ from ordinary key-based retrieval.

The C++ implementation uses explicit `Node` and `Edge` structures and a relationship enumeration. `std::queue` and visited-node tracking implement breadth-first traversal without recursively risking excessive call-stack growth.

The Java implementation separates nodes, edges, relationships, and graph services. Immutable records represent graph elements while collections maintain the adjacency structure.

The PostgreSQL implementation stores nodes and edges in separate tables. Foreign keys guarantee that graph endpoints exist, while a recursive CTE performs bounded traversal.

### Graph characteristics

Graph storage is appropriate when the primary questions concern relationships:

- Which services depend on a database?
- Which devices are monitored by a service?
- How is one entity connected to another?
- What entities are reachable within a specified number of hops?
- What path connects two entities?

A graph database is not automatically the best choice for every relationship. A simple foreign-key relationship may be sufficient when traversal depth and relationship complexity are limited.

Graph traversal can become expensive as branching factor and traversal depth increase. Production systems therefore commonly constrain traversal depth, use indexes on node identifiers, and carefully define relationship direction and query predicates.

## Relationship Between the Four Models

The four models solve different primary access problems.

`Document`
`   |`
`   +-- flexible aggregate`
``
`Key-Value`
`   |`
`   +-- exact key lookup`
``
`Column-Family`
`   |`
`   +-- sparse row/column access`
``
`Graph`
`   |`
`   +-- connected entity traversal`

The same operational domain can contain all four patterns.

For example, a device profile can be represented as a document, its active session can be stored as a key-value entry, its high-volume measurements can use a column-family layout, and its relationships to services and teams can be represented in a graph.

This does not mean the four systems should be merged indiscriminately. The correct model depends on the dominant access pattern, consistency requirements, query shape, scale, partitioning strategy, and operational constraints.

## Python Implementation

The Python program provides four independent storage classes:

| Class | Model | Main mechanism |
|---|---|---|
| `DocumentStore` | Document | Dictionary-backed documents and field indexes |
| `KeyValueStore` | Key-value | TTL-aware dictionary |
| `ColumnFamilyStore` | Column-family | Sparse row dictionaries |
| `GraphStore` | Graph | Nodes, edges, and BFS traversal |

`dataclasses` provide explicit domain structures for documents, rows, nodes, and edges.

Validation errors and missing-record conditions use separate exception types. This prevents a missing entity from being silently interpreted as an empty result.

The document store maintains indexes for scalar fields. The index reduces repeated scans for common equality lookups, although index maintenance adds write overhead.

The graph implementation uses breadth-first search. For an unweighted graph, BFS finds a shortest path by number of edges with time complexity proportional to the reachable vertices and edges.

## JavaScript Implementation

The JavaScript implementation emphasizes runtime-oriented data processing.

`Map` is used for direct key storage, document records, column rows, and graph adjacency. `Set` is used for indexed identifiers and node labels.

The document store uses `structuredClone` to prevent accidental mutation of stored state through references held by callers.

The key-value implementation supports TTL and compare-and-set behavior.

The `processEvents` function demonstrates asynchronous event processing with bounded concurrency. Each worker consumes a distinct event position and records either a successful result or a structured failure.

This pattern is useful for ingestion pipelines where independent NoSQL operations can be processed concurrently while errors remain associated with their original event positions.

## C++17 Implementation

The C++ program treats NoSQL storage as an engineering case study rather than as a collection of syntax examples.

The document model uses `std::variant` to constrain scalar values. The key-value model uses `std::unordered_map` and `std::chrono` for TTL handling.

The column-family implementation uses sparse unordered maps. This reflects a design where absent columns have different semantics from columns whose values are explicitly present.

The graph implementation uses typed relationship values through `enum class Relationship`. Its adjacency list and BFS traversal avoid recursive graph processing.

Exception classes distinguish validation failures from missing resources. The main function catches failures at the application boundary and reports them without exposing implementation internals.

## Java 17 Implementation

The Java implementation models NoSQL storage as an enterprise service layer.

Java records provide immutable representations for document records, graph nodes, graph edges, and key-value entries.

`DocumentRepository`, `KeyValueRepository`, `ColumnFamilyRepository`, and `GraphRepository` separate persistence-oriented behavior.

The `EligibilityPolicy` interface demonstrates explicit policy behavior. `ActiveDevicePolicy` determines whether a device is eligible before the service evaluates signal quality.

`DeviceService` therefore represents a higher-level workflow rather than merely exposing storage operations. A device can be structurally valid but still enter a blocked state because its operational attributes do not satisfy the policy.

This separation is important in enterprise systems because storage validity and business eligibility are different concerns.

## PostgreSQL Implementation

The PostgreSQL script creates the `nosql_lab` schema and models all four NoSQL approaches.

The document model uses:

- `JSONB` payloads;
- a GIN index;
- document state;
- version numbers;
- a repository foreign key.

The key-value model uses:

- a primary key on `key`;
- JSONB values;
- optional expiration;
- a partial expiration index.

The column-family model uses:

- a row key;
- sparse nullable attributes;
- signal-quality validation;
- an index for signal filtering.

The graph model uses:

- `graph_nodes`;
- `graph_edges`;
- foreign keys;
- relationship uniqueness;
- property JSONB;
- indexes on both edge directions.

The script also contains a recursive CTE for bounded graph traversal.

## Validation and Failure Handling

The implementations intentionally reject invalid states.

Examples include:

| Failure | Handling |
|---|---|
| Empty document identifier | Validation exception |
| Duplicate document key | Rejected |
| Invalid TTL | Validation exception |
| Missing key-value record | Empty result |
| Missing column-family row | Not-found error |
| Missing graph endpoint | Rejected relationship |
| Duplicate graph node | Validation error |
| Invalid workflow failure state | PostgreSQL trigger exception |
| Expired key-value record | Purged or classified as expired |

The examples distinguish absence from invalidity. A missing optional record may be a normal condition, while attempting to create a duplicate identifier is a validation failure.

## Consistency and Transactions

NoSQL systems often make different trade-offs among consistency, availability, partition tolerance, latency, and operational complexity. The data model alone does not determine the consistency guarantees of a particular database product.

The PostgreSQL implementation demonstrates transactional integrity explicitly. Workflow state transitions are performed within a transaction so that the database does not intentionally commit only part of the state transition.

The application implementations demonstrate local state consistency rather than distributed transaction guarantees. A Python dictionary or Java `HashMap` is not equivalent to a distributed NoSQL cluster.

## Performance Considerations

The dominant performance characteristics differ by model.

| Model | Representative operation | Typical local structure |
|---|---|---|
| Document | Equality lookup | Hash/index lookup |
| Key-value | Exact key lookup | Hash table |
| Column-family | Row lookup | Hash table |
| Graph | Reachability/path | Adjacency traversal |

Hash-based structures provide average constant-time lookup, subject to implementation and workload characteristics.

The graph BFS has time complexity `O(V + E)` for the reachable portion of the graph and requires additional memory for the queue and visited state.

Document indexes improve reads but require index maintenance during writes.

Column-family systems depend heavily on partition and row-key design in distributed deployments. The small in-memory implementations here do not reproduce network, replication, compaction, partitioning, or consensus costs.

## Security Considerations

NoSQL data models do not remove application security requirements.

Important controls include:

- validate keys and identifiers;
- enforce authorization before accessing records;
- avoid interpreting stored data as executable instructions;
- protect credentials and connection strings;
- encrypt sensitive data in transit;
- encrypt sensitive data at rest where required;
- restrict administrative database privileges;
- audit sensitive operations;
- control graph traversal depth where queries can expose connected information;
- apply retention rules to temporary key-value records;
- validate document structure at trust boundaries.

Flexible schemas require particular attention to validation because a permissive storage layer can otherwise accept malformed or unexpected application state.

Graph databases also require careful authorization design because a single relationship traversal can expose information indirectly through connected entities.

## Practical Model Selection

A model should be selected from the dominant workload rather than from the label "NoSQL."

| Requirement | Suitable model |
|---|---|
| Flexible customer or device aggregate | Document |
| Session or cache lookup | Key-value |
| Large sparse telemetry measurements | Column-family |
| Dependency and relationship traversal | Graph |

A real architecture can legitimately use multiple models when different workloads have materially different data-access patterns.

The important engineering decision is to keep each model's responsibility explicit rather than forcing every workload into the same storage structure.

## Limitations of the Implementations

The five source files are educational engineering models rather than distributed database engines.

They do not reproduce:

- replication protocols;
- consensus algorithms;
- network partitions;
- distributed transactions;
- shard rebalancing;
- compaction;
- replica repair;
- production authentication protocols;
- distributed locking;
- multi-node failure recovery.

The PostgreSQL implementation provides durable relational enforcement and demonstrates how NoSQL concepts can be represented using JSONB, sparse columns, and graph tables. It should not be interpreted as a full implementation of a distributed document, key-value, column-family, or graph database.

The Python, JavaScript, C++, and Java implementations are in-memory models. Their primary purpose is to expose the data structures, access patterns, validation boundaries, lifecycle rules, and algorithmic behavior that distinguish the four models.

## Technical Distinctions

The key distinction is not that one model is universally faster or more flexible than another.

The distinction is the representation of the application's dominant access pattern:

- Documents optimize around aggregates.
- Key-value systems optimize around direct identity.
- Column-family systems optimize around sparse, partition-oriented access.
- Graph systems optimize around relationships and traversal.

A sound design begins with the entities, access paths, consistency requirements, scale characteristics, failure modes, and security boundaries of the workload. The storage model follows from those requirements rather than replacing them.
