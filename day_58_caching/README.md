# Cache-aside, TTL, and Invalidation

## Scope

This project models application caching through three related but distinct mechanisms:

- **Cache-aside** defines how application code reads and writes cached data around a source of truth.
- **TTL (time-to-live)** defines how long a cached representation remains usable.
- **Invalidation** defines how an application removes or marks cached data unusable when the underlying data changes.

The implementations use a repository as the authoritative source and a cache as a temporary representation:

    Application
        |
        v
    Cache lookup
      /       \
    HIT       MISS
     |          |
     v          v
  Return     Source repository
                |
                v
             Cache fill
                |
                v
             Return

A write follows a different path:

    Application
        |
        v
    Source of truth
        |
        v
    Successful update
        |
        v
    Cache invalidation
        |
        v
    Next read repopulates cache

The cache is therefore not treated as the authoritative data store.

## Core Concepts

### Cache-aside

Cache-aside is an application-controlled caching pattern.

For a read, the application first attempts a cache lookup. A cache hit returns the cached representation without accessing the backing store. A cache miss causes the application to retrieve the current value from the backing store and populate the cache before returning the result.

The important property is that the application owns cache population. The cache does not automatically know when an application object changes.

The Python implementation expresses this behavior through `CacheAsideService.get_user()`. The JavaScript implementation uses asynchronous repository calls and a `UserService`. The Java and C++ programs concentrate more strongly on explicit governance and state evaluation while still providing cache-related models.

### TTL

TTL limits the useful lifetime of a cache entry.

An entry contains an expiration timestamp rather than relying on an unlimited lifetime. When the current time reaches the expiration point, the entry is considered stale and is removed during lookup.

TTL provides an automatic upper bound on how long an unchanged cached value can remain available.

TTL does not guarantee immediate consistency. A source value can change immediately after a cache entry is populated, leaving the old representation available until its TTL expires unless explicit invalidation occurs.

### Invalidation

Invalidation removes a cached representation before its natural TTL expiration.

The source update should succeed before invalidation. This avoids deleting a cache entry because of a failed source operation.

The implementations include explicit key invalidation and tag-based invalidation. Tag invalidation is useful when one source change affects several related cached objects.

Example:

    update source
        |
        +-- success --> invalidate key/tag
        |                  |
        |                  v
        |              next read
        |                  |
        |                  v
        |              cache miss
        |                  |
        |                  v
        |              source reload

## Cache-aside Read and Write Rules

A read follows these rules:

1. Validate the cache key.
2. Attempt a cache lookup.
3. Treat an absent entry as a miss.
4. Treat an expired entry as stale and remove it.
5. Read the source of truth after a miss.
6. Populate the cache with the source value.
7. Return the source value.

A write follows these rules:

1. Validate the resource identifier.
2. Update the source of truth.
3. Stop if the source update fails.
4. Invalidate the corresponding cache key.
5. Allow the next read to repopulate the cache.

This ordering avoids the particularly dangerous situation in which the cache is invalidated and then a failed source update leaves the system without either the old cache value or the new source value.

## TTL Semantics

A cache entry contains:

| Field | Purpose |
|---|---|
| `value` | Cached representation |
| `created_at` | Entry creation time |
| `expires_at` | Absolute expiration time |
| `version` | Cache-entry version |
| `tags` | Groups used for related invalidation |

An entry is usable only when its expiration time is still in the future.

The Python implementation uses `time.monotonic()` for TTL measurement. This avoids incorrect duration calculations caused by system-clock adjustments.

The JavaScript implementation uses `performance.now()` for the same reason: TTL measurement is based on elapsed runtime rather than wall-clock calendar time.

The Java cache uses `Instant` for explicit expiration timestamps. The PostgreSQL model uses `TIMESTAMPTZ` because the database needs an absolute timestamp for persisted cache metadata.

## Stale Data

TTL and invalidation address different causes of stale data.

TTL handles time-based staleness:

    cache populated
        |
        | valid
        v
    expiration point
        |
        v
    stale

Invalidation handles event-based staleness:

    cache populated
        |
        v
    source changes
        |
        v
    invalidate cache
        |
        v
    next read reloads source

Using both mechanisms provides a bounded fallback when an invalidation event is missed. TTL should not be treated as a substitute for reliable invalidation when strong freshness requirements exist.

## Python Implementation

The Python file contains a complete cache-aside service with an in-memory TTL cache.

### `TTLCache`

`TTLCache` provides:

- key validation
- TTL validation
- expiration detection
- explicit invalidation
- tag-based invalidation
- version increments
- bounded entry count
- metrics
- thread-safe access

The cache uses a `dict` for constant-average-time key lookup. `RLock` protects shared state when multiple threads access the cache.

The cache records hits, misses, stale entries, and invalidations. These metrics make cache behavior observable without changing the cache's external semantics.

### `Repository`

`Repository` represents the source of truth. It deliberately does not depend on the cache.

This separation demonstrates an important architectural property: losing or clearing the cache does not destroy application data.

### `CacheAsideService`

The service performs the actual cache-aside workflow.

`get_user()` attempts the cache first. On a miss, it retrieves the user from the repository and stores the result with a TTL.

`update_user()` updates the repository first and then invalidates the corresponding cache key.

The implementation also assigns resource tags such as `users`, allowing related entries to be invalidated as a group.

### Python Failure Handling

The implementation distinguishes:

- invalid cache configuration
- cache misses
- source failures
- invalid keys

A cache miss is an expected control-flow event rather than a system failure. A source failure is different because the authoritative store could not provide the requested value.

The self-tests cover hits, misses, invalidation, tag invalidation, configuration validation, source updates, and version changes.

## JavaScript Implementation

The JavaScript implementation uses Node.js standard-library facilities and asynchronous repository access.

### Event-driven Cache

`TTLCache` extends `EventEmitter`.

It emits events for:

- cache hits
- cache misses
- stale entries
- cache writes
- explicit invalidation
- tag invalidation
- complete clearing

This provides an event-driven observation model suitable for logging, metrics, tracing, or operational monitoring.

### Asynchronous Source

`UserRepository` exposes asynchronous operations. The service therefore demonstrates an important practical difference from a purely in-memory synchronous example: a cache miss can require an asynchronous database or network operation.

The `UserService` handles this using `async` and `await`.

### Defensive Value Handling

The cache uses `structuredClone()` when storing and returning values. This prevents callers from modifying an object reference held internally by the cache.

That behavior is useful when cached objects are mutable JavaScript structures.

### JavaScript TTL Behavior

`performance.now()` is used for elapsed-time measurement. Cache expiration does not depend on calendar-clock changes.

The cache uses a `Map`, while each entry uses a `Set` for tags. This gives direct key lookup and efficient membership testing for tag-based invalidation.

## C++17 Governance Perspective

The C++17 program models cache-related repository governance as a merge-eligibility engine.

The engineering focus is deliberately different from the application-service implementations. It treats repository state as a set of constraints that must all be satisfied before a Pull Request can be merged.

The model includes:

- Pull Request state
- source and target branches
- commits
- reviews
- stale approvals
- status checks
- unresolved conversations
- protected branch policy
- merge eligibility

A Pull Request can be blocked because:

- it is not open
- it is a draft
- it has no commits
- the source branch is behind
- required approvals are missing
- approvals are stale
- status checks have failed
- conversations remain unresolved
- the target branch has no applicable governance policy

The implementation uses STL containers such as `unordered_map`, `unordered_set`, and `vector`.

Approval evaluation uses distinct reviewer identities so that multiple approval records from the same reviewer do not incorrectly satisfy a policy requiring independent reviewers.

## Java 17 Enterprise Model

The Java implementation uses explicit domain types to model repository governance.

Records represent immutable value concepts such as:

- `Commit`
- `Review`
- `StatusCheck`
- `BranchProtectionPolicy`
- `MergeDecision`

`PullRequest` represents mutable workflow state and explicitly controls transitions.

The `MergeEligibilityService` separates policy evaluation from the Pull Request entity. This makes the policy rules explicit and keeps merge decisions reproducible.

### Approval Evaluation

Only reviews that are:

- approved
- non-stale
- associated with distinct reviewers

count toward the approval requirement.

A stale approval remains historical information but does not satisfy the current policy.

### Status Evaluation

When successful checks are required, every configured check must be passed. A missing check set is not silently treated as success.

### Conversation State

The model tracks unresolved review conversations independently from approval decisions. A reviewer can approve a Pull Request while unresolved discussion remains, and the branch policy can still block merging.

This distinction prevents approval state from being confused with final merge eligibility.

### Expiring Cache

The Java file also contains a generic `ExpiringCache<K, V>`.

It demonstrates:

- generic cache keys and values
- immutable entry records
- TTL validation
- synchronized cache operations
- explicit invalidation
- expiration during reads

The generic design allows the same cache abstraction to store different domain value types without losing compile-time type safety.

## PostgreSQL Relational Model

The PostgreSQL script models the source system and cached representations using relational structures.

### Source-of-truth entities

The schema contains:

- `repositories`
- `branches`
- `commits`
- `pull_requests`
- `pull_request_commits`
- `reviewers`
- `reviews`
- `review_comments`
- `status_checks`
- `branch_protection_policies`

These tables provide the operational state used by merge-eligibility queries.

### Cache representation

`cache_entries` stores:

- cache key
- resource type
- resource identifier
- JSON representation
- version
- creation timestamp
- expiration timestamp
- invalidation timestamp

The cache entry deliberately has no authority over the underlying relational record.

`cache_invalidation_events` records why entries were invalidated. This provides an audit trail for explicit invalidation and source-update workflows.

### Database Constraints

The schema uses:

- primary keys
- foreign keys
- unique constraints
- check constraints
- partial indexes
- trigger validation

The TTL trigger prevents a cache entry from being created with an expiration timestamp that is not later than its creation timestamp.

## PostgreSQL Cache Queries

The script demonstrates several operational queries.

### Freshness Detection

A cache entry can be classified as:

- `fresh`
- `expired`
- `invalidated`

This classification is calculated from persisted timestamps and invalidation state.

### Expired Entry Detection

Expired entries can be identified using the expiration index. A production cleanup process can use this information to remove old records or archive cache statistics.

### Merge Eligibility

A CTE-based query combines:

- Pull Request state
- source synchronization
- approval counts
- reviewer activity
- review staleness
- status-check results
- branch protection policy
- unresolved conversations

The result is a final eligibility decision rather than a simple approval count.

This demonstrates an important distinction: approval is one input into merge eligibility, not the entire merge decision.

## Data and State Relationships

The source system and cache have different responsibilities.

    Repository
        |
        +--> Branch
        |      |
        |      +--> Commit
        |
        +--> Pull Request
               |
               +--> Reviews
               |
               +--> Review Comments
               |
               +--> Status Checks
               |
               +--> Policy
               
    Source state
        |
        v
    Cache entry
        |
        +--> TTL
        +--> version
        +--> invalidation state

A cache entry represents a temporary projection of source data. It does not replace source validation or source persistence.

## Consistency Considerations

Cache-aside systems normally accept a period during which cached data can differ from source data.

Two mechanisms reduce this window:

1. Explicit invalidation after successful writes.
2. TTL expiration as a bounded fallback.

Neither mechanism makes the system universally strongly consistent.

A race can still occur when concurrent readers and writers operate on the same resource. For example, a reader may retrieve an old source value at the same time that another process updates the source.

Systems with strict consistency requirements may need version checks, transactional coordination, write-through mechanisms, distributed locking, or a different consistency architecture.

## Cache Stampede

A cache stampede can occur when a heavily requested entry expires and many requests simultaneously observe a miss.

Without coordination:

    Request A --> miss --> source
    Request B --> miss --> source
    Request C --> miss --> source
    Request D --> miss --> source

All requests can overload the backing store.

The implementations intentionally keep the core cache-aside mechanism explicit rather than hiding stampede prevention inside the basic cache. Production systems can add request coalescing, per-key locks, stale-while-revalidate behavior, or probabilistic early refresh.

## Invalidation Granularity

There are several useful invalidation levels.

| Mechanism | Scope | Typical use |
|---|---|---|
| Key invalidation | One object | One resource changed |
| Tag invalidation | Related objects | A group of dependent entries changed |
| TTL expiration | Time boundary | Fallback freshness control |
| Full clear | Entire cache | Emergency reset or deployment event |

Fine-grained invalidation reduces unnecessary cache misses. Broad invalidation is simpler but can cause unnecessary source traffic.

## Versioning

The Python and cache-oriented models maintain entry versions.

Versioning can help detect whether a cached representation corresponds to an older source state. A production distributed cache can use source version numbers or entity revision identifiers to prevent an older response from overwriting a newer cached representation.

A version alone does not solve every race condition. The source and cache update protocol must define which version is authoritative.

## Performance

Typical in-memory cache lookup is expected to be O(1) average time for key access.

Tag invalidation is O(n) in the number of cached entries when implemented by scanning all entries. A large production cache can maintain a reverse index:

    tag -> set of cache keys

This changes tag invalidation from a full cache scan toward work proportional to the number of entries associated with the tag.

The PostgreSQL expiration index is partial because invalidated entries do not need to participate in active-expiration lookups.

The database indexes on Pull Request state, reviews, and status checks target the merge-eligibility workload rather than indexing every column.

## Security Considerations

Cached data can contain sensitive information even when the cache is not authoritative.

Important controls include:

- avoid placing secrets directly into cache values
- apply access control before returning cached objects
- include authorization-relevant identity or scope in cache keys where necessary
- prevent cross-user cache-key collisions
- validate externally supplied cache keys
- protect distributed cache transport
- restrict administrative cache inspection
- consider encryption for sensitive persisted cache data
- avoid logging complete sensitive cache payloads
- define appropriate retention periods

A cache hit must not bypass authorization checks that would have been applied to a source read.

For example, a key such as `user:101` may be insufficient if different callers have different permissions to view that user's fields. A production design may require authorization-aware keys or post-cache authorization filtering.

## Failure Handling

A cache failure and a source failure have different consequences.

If the cache is unavailable, the application may be able to fall back to the source.

If the source is unavailable on a cache miss, the application cannot reconstruct the requested value unless another authoritative or fallback source exists.

This produces a practical resilience hierarchy:

    Cache available + fresh
        -> fast response

    Cache miss + source available
        -> source response + cache fill

    Cache unavailable + source available
        -> source response

    Cache miss + source unavailable
        -> request failure

The Python and JavaScript examples explicitly distinguish cache misses from source failures.

## Operational Metrics

Useful cache metrics include:

| Metric | Interpretation |
|---|---|
| Hit count | Successful cache lookups |
| Miss count | Requests requiring another source |
| Stale count | Misses caused by expiration |
| Invalidation count | Explicitly removed entries |
| Cache size | Current number of entries |
| Source latency | Cost of cache misses |
| Fill rate | Frequency of cache population |
| Eviction count | Capacity pressure |

Hit rate is commonly calculated as:

`hits / (hits + misses)`

A high hit rate does not automatically mean correct behavior. A cache can achieve a high hit rate while serving data that is too old for the application's consistency requirements.

## Edge Cases Covered

The implementations account for:

- empty cache keys
- invalid TTL values
- expired entries
- explicit invalidation
- tag-based invalidation
- missing source records
- source update failures
- duplicate reviewers
- stale approvals
- failed status checks
- absent status checks
- unresolved conversations
- unsynchronized source branches
- missing branch policies
- bounded cache capacity
- mutable cached JavaScript objects
- invalid database expiration timestamps

## Practical Design Distinctions

The three central mechanisms should not be treated as interchangeable.

| Mechanism | Primary question |
|---|---|
| Cache-aside | How is cached data read and populated? |
| TTL | How long can a cached entry remain usable? |
| Invalidation | When should a cached entry stop being used before TTL expiration? |

A complete caching design commonly combines them:

    Cache-aside
        +
    TTL
        +
    Explicit invalidation
        =
    Controlled temporary representation

Cache-aside determines the workflow, TTL provides a time-based freshness boundary, and invalidation reacts to known source changes.

## File Responsibilities

| File | Primary perspective | Main implementation |
|---|---|---|
| Python | Application service | Thread-safe cache-aside service with TTL and tag invalidation |
| JavaScript | Event-driven service | Async cache, events, cloning, TTL, and invalidation |
| C++17 | Governance engine | Structured policy and eligibility evaluation |
| Java 17 | Enterprise domain model | Explicit domain types, policies, state transitions, and expiring cache |
| PostgreSQL | Persistent data model | Relational source state, cache metadata, constraints, indexes, triggers, and eligibility queries |

The five implementations deliberately use different engineering perspectives while preserving the same core distinction: cached data is temporary, the source of truth remains authoritative, TTL controls time-based validity, and invalidation responds to known changes.
