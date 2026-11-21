# Concurrency, Race Conditions, Locks, and Synchronization

## 1. Introduction

Concurrency is the execution of multiple operations during overlapping periods. A concurrent application may execute tasks through operating-system threads, asynchronous event loops, worker pools, or database transactions.

Concurrency improves resource utilization and application responsiveness, but it introduces coordination problems when multiple operations access shared state.

The central engineering challenge is maintaining correctness when execution order is not guaranteed.

This implementation examines concurrency through four connected mechanisms:

1. Race-condition prevention.
2. Mutual exclusion and synchronization.
3. Coordination of concurrent tasks.
4. Consistency management for shared resources.

The five implementations use Python, JavaScript, C++17, Java 17, and PostgreSQL to demonstrate different approaches to these problems.

## 2. Fundamental Concepts

### 2.1 Concurrency

Concurrency means that multiple operations make progress during overlapping periods.

For example, an inventory application may simultaneously process:

- A customer reservation.
- A warehouse stock update.
- A stock availability query.
- A reporting operation.
- A background inventory reconciliation task.

These operations may access the same resource.

Concurrency does not necessarily mean that instructions execute simultaneously. A single-threaded event loop can execute overlapping asynchronous operations, while a multicore processor can execute multiple threads in parallel.

### 2.2 Parallelism

Parallelism is the simultaneous execution of multiple operations.

| Characteristic | Concurrency | Parallelism |
|---|---|---|
| Primary concern | Coordinating overlapping operations | Executing operations simultaneously |
| Execution | Interleaved or simultaneous | Simultaneous |
| Typical mechanism | Threads, asynchronous tasks | Multiple processor cores |
| Main challenge | Shared-state correctness | Shared-state correctness and coordination |
| Example | Multiple pending database requests | Multiple CPU-intensive calculations |

Concurrency is a software execution model. Parallelism is an execution capability.

### 2.3 Shared State

Shared state is information accessible by multiple execution contexts.

Examples include:

- Account balances.
- Inventory quantities.
- Configuration maps.
- Counters.
- Task queues.
- Database records.
- Cached application data.

A shared resource becomes particularly difficult to manage when multiple operations can modify it.

### 2.4 Critical Section

A critical section is a portion of a program that accesses shared mutable state and requires controlled execution.

Consider an inventory quantity of 10.

Two requests attempt to reserve 7 units each.

The following logical sequence is unsafe:

1. Request A reads 10.
2. Request B reads 10.
3. Request A checks that 7 units are available.
4. Request B checks that 7 units are available.
5. Request A subtracts 7.
6. Request B subtracts 7.

Both requests may report successful reservations even though only 10 units existed.

The availability check and quantity update must be treated as one coordinated operation.

## 3. Race Conditions

A race condition occurs when the result of an operation depends on the unpredictable timing or ordering of concurrent execution.

### 3.1 Read-Modify-Write Race

A common race condition involves three operations:

- Read a shared value.
- Modify the value.
- Write the result.

For a counter initially equal to 0, two threads may execute:

| Step | Thread A | Thread B | Counter |
|---|---|---|---:|
| 1 | Read 0 | | 0 |
| 2 | | Read 0 | 0 |
| 3 | Calculate 1 | | 0 |
| 4 | | Calculate 1 | 0 |
| 5 | Write 1 | | 1 |
| 6 | | Write 1 | 1 |

The expected result is 2, but the actual result is 1.

This is called a lost update.

### 3.2 Types of Race Conditions

| Type | Mechanism | Consequence |
|---|---|---|
| Data race | Unsynchronized concurrent memory access involving a write | Undefined behavior in languages such as C++ |
| Lost update | One modification overwrites another | Incorrect counters or balances |
| Check-then-act | A condition changes between checking and acting | Invalid reservations |
| Read skew | Related values are read at inconsistent times | Incorrect calculations |
| Write skew | Concurrent transactions modify different records based on the same outdated condition | Violation of business invariants |
| Initialization race | Multiple execution contexts initialize shared state | Duplicate or incomplete initialization |

Not every race condition is technically a data race. A database application can experience lost updates or write skew without violating the programming language's memory model.

### 3.3 Practical Prevention

The main prevention strategies are:

- Protect critical sections.
- Use atomic operations where suitable.
- Make related updates transactional.
- Apply database constraints.
- Use version-based conflict detection.
- Minimize shared mutable state.
- Coordinate access to shared resources.

## 4. Locks and Mutual Exclusion

A lock controls access to a shared resource.

Mutual exclusion ensures that only one permitted execution context enters a protected critical section at a time.

### 4.1 Mutex

A mutex, or mutual exclusion lock, provides exclusive access.

The typical lifecycle is:

1. Acquire the lock.
2. Enter the critical section.
3. Read or modify shared state.
4. Release the lock.

A competing execution context waits until the lock becomes available.

**Python implementation**

The `SafeCounter` class uses `threading.Lock` to protect a shared counter.

The `with` statement ensures that the lock is released even when an exception occurs.

**JavaScript implementation**

The `AsyncMutex` class implements FIFO asynchronous lock acquisition using promises and a waiting queue.

The lock protects asynchronous operations that would otherwise interleave across `await` boundaries.

**C++ implementation**

The banking implementation uses `std::mutex` and `std::scoped_lock`.

RAII-based lock management ensures that locks are released when their owning scope exits.

**Java implementation**

The banking service uses `ReentrantLock` to coordinate access to account records.

### 4.2 Reentrant Locks

A reentrant lock allows the same thread to acquire a lock it already owns.

For example:

- Method A acquires a lock.
- Method A calls method B.
- Method B acquires the same lock.
- Method B completes.
- Method A completes.

A conventional non-reentrant mutex may cause self-deadlock in this situation.

Python's `threading.RLock` and Java's `ReentrantLock` provide reentrant locking.

Reentrancy does not make arbitrary nested locking safe. Lock ownership, acquisition order, and release behavior still require careful design.

### 4.3 Lock Granularity

Lock granularity describes how much shared state a lock protects.

| Strategy | Characteristics | Trade-off |
|---|---|---|
| Coarse-grained locking | One lock protects a large shared resource | Simple correctness, potentially high contention |
| Fine-grained locking | Different locks protect independent resources | Greater concurrency, more complex coordination |
| Partitioned locking | Resources are distributed across lock groups | Reduced contention with additional design complexity |

The Python `PartitionedCounter` demonstrates partitioned synchronization.

Independent keys may update under different locks, allowing unrelated operations to progress concurrently.

The implementation acquires all partition locks in a consistent order when taking a complete snapshot.

## 5. Atomic Operations

An atomic operation executes as an indivisible operation from the perspective of other participating operations.

An atomic increment prevents the lost-update behavior associated with an unprotected read-modify-write sequence.

### 5.1 Atomic Counters

C++ provides `std::atomic`.

Java provides classes such as:

- `AtomicInteger`
- `AtomicLong`
- `AtomicBoolean`
- `AtomicReference`

Atomic variables are appropriate for simple state transitions and counters.

They do not automatically make a collection of multiple operations transactional.

For example, independently incrementing two account balances with atomic variables does not guarantee that a transfer is atomic as a whole.

### 5.2 Memory Ordering

Atomic operations can also control memory visibility.

C++ memory-ordering options include:

- `memory_order_relaxed`
- `memory_order_acquire`
- `memory_order_release`
- `memory_order_acq_rel`
- `memory_order_seq_cst`

Relaxed ordering guarantees atomicity without imposing the synchronization ordering of stronger memory models.

The C++ implementation uses relaxed ordering for independent counters whose correctness does not depend on publishing other shared data.

Choosing memory ordering requires understanding the relationship between operations, not simply selecting the weakest available option.

### 5.3 Compare-and-Set

Compare-and-set operations update a value only if it still matches an expected state.

This is useful for:

- State transitions.
- Version checks.
- Lock-free algorithms.
- Concurrent configuration updates.

The Python, JavaScript, C++, and Java implementations demonstrate version-based comparison before accepting an update.

## 6. Synchronization Mechanisms

Synchronization coordinates the execution and communication of concurrent operations.

### 6.1 Semaphore

A semaphore controls access to a limited number of resource permits.

For example, a service may allow only three concurrent operations against a restricted external resource.

A semaphore initialized with three permits allows:

- Three operations to execute simultaneously.
- Additional operations to wait.
- Waiting operations to continue when permits are released.

The JavaScript implementation demonstrates a semaphore-based task limit.

A semaphore differs from a mutex:

| Property | Mutex | Semaphore |
|---|---|---|
| Primary purpose | Exclusive access | Limited concurrent access |
| Capacity | One owner | One or more permits |
| Ownership | Generally associated with an acquiring thread or execution context | Permit-based coordination |
| Common use | Protecting shared mutable state | Connection and worker limits |

### 6.2 Condition Variables

A condition variable allows an execution context to wait until a particular condition becomes true.

A producer-consumer queue is a common application.

The producer waits when the queue is full.

The consumer waits when the queue is empty.

The waiting operation releases its associated lock so that another execution context can change the condition.

The condition must be checked in a loop because wake-ups do not guarantee that the condition remains true when execution resumes.

The C++ implementation uses:

- `std::condition_variable`
- `std::unique_lock`
- `wait`
- `notify_one`
- `notify_all`

The Java implementation uses:

- `Condition`
- `await`
- `signal`
- `signalAll`

The Python implementation uses `threading.Condition`.

### 6.3 Read-Write Locks

Read-write locks distinguish between reading and modifying shared data.

Multiple readers can access the resource concurrently.

A writer requires exclusive access.

They are useful when reads are substantially more frequent than writes.

The C++ implementation uses `std::shared_mutex`.

The Java implementation uses `ReentrantReadWriteLock`.

The JavaScript implementation demonstrates a promise-based read-write lock.

A read-write lock is not automatically faster than a mutex. Lock management overhead, workload distribution, and writer starvation can affect performance.

### 6.4 Producer-Consumer Synchronization

The producer-consumer model separates task creation from task execution.

Its components are:

- Producer: creates work.
- Queue: stores pending work.
- Consumer: processes available work.
- Synchronization mechanism: coordinates access.

A bounded queue limits memory consumption and prevents an unrestricted producer from overwhelming consumers.

A queue should also define what happens during shutdown.

The implementations use a closed-state mechanism to wake blocked producers and consumers and allow pending items to be processed before termination.

## 7. Deadlocks

A deadlock occurs when two or more execution contexts wait indefinitely for resources held by one another.

### 7.1 Four Necessary Conditions

The classical deadlock conditions are:

| Condition | Explanation |
|---|---|
| Mutual exclusion | A resource can be held exclusively |
| Hold and wait | An execution context holds one resource while requesting another |
| No preemption | Resources cannot be forcibly removed |
| Circular wait | A circular dependency exists between waiting contexts |

All four conditions must be present for a classical resource-allocation deadlock.

### 7.2 Example

Consider two locks, A and B.

- Thread 1 acquires A and waits for B.
- Thread 2 acquires B and waits for A.

Neither thread can proceed.

### 7.3 Deadlock Prevention

Useful prevention strategies include:

1. Acquire multiple locks in a consistent global order.
2. Minimize the duration of lock ownership.
3. Avoid unnecessary nested locking.
4. Use scoped lock management.
5. Apply lock timeouts where appropriate.
6. Avoid calling unpredictable external operations while holding locks.

The C++ implementation uses `std::scoped_lock` for simultaneous acquisition of two mutexes.

The Java banking service uses a single transaction lock, trading concurrency for simpler correctness.

The PostgreSQL section demonstrates the importance of acquiring database rows in a consistent order.

### 7.4 Starvation and Livelock

Deadlock is not the only synchronization failure.

**Starvation** occurs when an execution context repeatedly fails to acquire the resources needed to progress.

**Livelock** occurs when execution contexts remain active but repeatedly change state without making useful progress.

Fair locks and carefully designed scheduling policies can reduce some starvation risks.

They do not guarantee that every application-level operation completes.

## 8. Optimistic and Pessimistic Concurrency Control

Concurrency control determines how conflicting operations are managed.

### 8.1 Pessimistic Concurrency Control

Pessimistic concurrency assumes that conflicts are sufficiently likely to justify locking resources before modification.

Typical mechanisms include:

- Mutexes.
- Reentrant locks.
- Database row locks.
- `SELECT FOR UPDATE`.

The operation obtains exclusive access before modifying the shared resource.

This approach is useful for highly contested resources or operations that must inspect and modify several related values.

Its disadvantages include lock contention, waiting, and deadlock risk.

### 8.2 Optimistic Concurrency Control

Optimistic concurrency assumes that conflicts are relatively uncommon.

A typical workflow is:

1. Read a resource and its version.
2. Perform calculations.
3. Submit the update with the expected version.
4. Accept the update if the version is unchanged.
5. Reject the update if another operation has modified the resource.

Example:

| Operation | Version | Value |
|---|---:|---:|
| Initial read | 0 | 100 |
| First update | 1 | 150 |
| Second update using version 0 | Rejected | Conflict |

The implementations use a version field to prevent stale updates from silently overwriting newer values.

Optimistic concurrency is useful for document editing, application APIs, configuration management, and database records.

It requires a retry or conflict-resolution policy when updates are rejected.

### 8.3 Comparison

| Characteristic | Pessimistic | Optimistic |
|---|---|---|
| Conflict assumption | Conflicts are likely | Conflicts are less frequent |
| Coordination | Before modification | During update validation |
| Main mechanism | Locks | Version checks |
| Contention | Can cause waiting | Can cause retries |
| Suitable workloads | Highly contested resources | Read-heavy, low-conflict workloads |

## 9. Python Implementation

The Python script is a repository-independent concurrency laboratory using standard-library functionality.

### 9.1 Race Condition Simulation

`UnsafeCounter` demonstrates an unprotected read-modify-write sequence.

The test deliberately introduces a scheduling opportunity between reading and writing.

The actual result is not guaranteed to differ from the expected result on every execution. The purpose is to expose the absence of synchronization, not to depend on a particular incorrect output.

### 9.2 Thread-Safe Counter

`SafeCounter` protects updates using `threading.Lock`.

The `ThreadPoolExecutor` manages worker execution without requiring manual thread lifecycle management.

An assertion verifies that the expected total is maintained.

### 9.3 Reentrant Inventory

`ReentrantInventory` uses `threading.RLock`.

Its reservation method calls the availability method while holding the same lock.

This demonstrates a situation where reentrant acquisition is useful.

### 9.4 Banking and Lock Ordering

`BankingService` transfers funds between accounts.

The implementation acquires both account locks in deterministic account-ID order.

This prevents the circular-wait pattern caused by inconsistent lock acquisition.

The banking stress test verifies conservation of the total balance.

### 9.5 Producer-Consumer Processing

`BoundedBuffer` uses a condition variable and a bounded list.

Its `close` method wakes waiting execution contexts.

The consumer drains existing items before terminating.

### 9.6 Optimistic Store

`OptimisticStore` maintains an immutable versioned state.

`compare_and_set` rejects stale updates through `ConcurrencyConflictError`.

### 9.7 Partitioned Synchronization

`PartitionedCounter` uses separate locks for groups of keys.

This illustrates lock granularity and contention management.

The implementation copies shared state only while holding all relevant locks.

### 9.8 Execution and Validation

The `main` function executes the demonstrations and validates invariants.

The main checks include:

- Expected counter total.
- Nonnegative inventory.
- Conservation of account balances.
- Complete producer-consumer processing.
- Optimistic update conflict detection.
- Partitioned counter totals.

Run the script with Python 3.10 or later:

`python concurrency.py`

No third-party packages are required.

## 10. JavaScript Implementation

JavaScript requires a different understanding of concurrency because standard Node.js execution commonly uses an event loop for JavaScript callbacks.

An asynchronous function can yield execution at an `await` statement, allowing other asynchronous operations to progress.

This can produce race conditions even without multiple JavaScript threads modifying memory directly.

### 10.1 Event-Loop Race Conditions

The `UnsafeBalance` class demonstrates two withdrawals that read the same balance before either writes its result.

The asynchronous boundary allows their operations to interleave.

This is an asynchronous race condition, not necessarily a low-level data race.

### 10.2 Promise-Based Mutex

`AsyncMutex` implements:

- Exclusive asynchronous acquisition.
- FIFO waiter processing.
- Timeout handling.
- Abort-signal support.
- Protected execution through `runExclusive`.
- Automatic release in a `finally` block.

This model is useful when multiple asynchronous operations must modify one shared JavaScript object.

The mutex is intended for coordination within one JavaScript execution environment. It does not coordinate independent Node.js processes or worker threads.

### 10.3 Semaphore

The semaphore limits the number of simultaneous operations.

The execution example verifies that no more than three tasks are active at once.

### 10.4 Read-Write Lock

`ReadWriteLock` allows multiple queued readers to execute together while giving a queued writer exclusive access.

The implementation processes requests in FIFO order to prevent readers arriving after a waiting writer from indefinitely bypassing that writer.

### 10.5 Event-Driven Processing

`TaskProcessor` extends `EventEmitter`.

It publishes:

- `started`
- `completed`
- `failed`

This separates task execution from event observation.

The processor also tracks successful and failed operations.

### 10.6 Important Limitation

JavaScript promises and asynchronous locks do not automatically provide cross-process synchronization.

Applications using Node.js worker threads, multiple processes, or distributed servers need additional coordination mechanisms.

Possible solutions include shared-memory synchronization, database transactions, distributed locks, or centralized resource ownership.

Run:

`node concurrency.js`

No third-party npm packages are required.

## 11. C++17 Implementation

C++ provides explicit control over threads, memory synchronization, atomic operations, and resource ownership.

Incorrect synchronization can introduce undefined behavior.

The C++ program uses the standard threading library.

### 11.1 Mutex and RAII

`std::mutex` provides exclusive synchronization.

The implementation uses:

- `std::lock_guard`
- `std::unique_lock`
- `std::scoped_lock`

These mechanisms automatically release locks when their associated objects leave scope.

RAII reduces the risk of leaving a mutex locked after an exception or early return.

### 11.2 Scoped Locking

`std::scoped_lock` supports acquiring multiple mutexes safely.

It is particularly useful when an operation requires simultaneous access to multiple independent objects.

The banking implementation protects both account balances during transfers.

### 11.3 Atomic Counters

`std::atomic` provides atomic access to supported data types.

The counter uses `fetch_add` with relaxed memory ordering because the counter does not publish other shared state.

The task executor also uses atomic counters to record completed and failed tasks.

### 11.4 Shared Mutex

`std::shared_mutex` supports shared and exclusive locking.

Multiple readers can acquire shared ownership.

A writer requires exclusive ownership.

`ConfigurationStore` demonstrates this model.

### 11.5 Bounded Queue

`BoundedQueue` combines:

- `std::queue`
- `std::mutex`
- `std::condition_variable`
- `std::unique_lock`

The queue waits for available capacity before accepting new items.

Consumers wait until data becomes available or the queue closes.

The queue uses predicates in its condition-variable waits to handle spurious wake-ups correctly.

### 11.6 Task Executor

`TaskExecutor` uses worker threads to process submitted functions.

Its queue has a fixed capacity.

Worker exceptions are captured so that one failing task does not terminate the entire processing system.

Shutdown closes the queue and joins worker threads.

### 11.7 Execution

Compile:

`g++ -std=c++17 -O2 -pthread concurrency.cpp -o concurrency`

Run:

`./concurrency`

The program validates:

- Atomic counter correctness.
- Banking balance conservation.
- Producer-consumer processing.
- Inventory constraints.
- Optimistic conflict detection.
- Task execution totals.

## 12. Java 17 Enterprise Implementation

The Java implementation uses explicit domain objects and service boundaries to represent enterprise concurrency management.

### 12.1 Domain Modeling

The program defines:

- `Account`
- `AccountSnapshot`
- `TransferResult`
- `VersionedValue`
- `OperationStatus`

Java records provide immutable representations of returned snapshots and results.

The `Account` class owns its mutable balance and version.

The banking service coordinates access to these objects.

### 12.2 ReentrantLock

`BankingService` uses a fair `ReentrantLock`.

The lock protects the complete transfer operation.

This avoids a partially completed transfer becoming visible through the service's public operations.

The implementation uses a single transaction lock for simplicity.

A more complex system could use per-account locks with deterministic acquisition ordering to increase concurrency.

### 12.3 ReadWriteLock

`ConfigurationService` separates read and write operations.

Readers acquire the read lock.

Updates acquire the write lock.

The snapshot operation returns an immutable copy instead of exposing the mutable internal map.

### 12.4 Optimistic Concurrency

`VersionedDocument` uses synchronized methods to ensure that reading and updating its versioned state are coordinated.

An update succeeds only when the expected version matches the current version.

A stale version causes `OptimisticConflictException`.

### 12.5 Condition-Based Queue

`BoundedQueue` uses `ReentrantLock` and two conditions.

- `notEmpty` signals that consumers may proceed.
- `notFull` signals that producers may proceed.

Its `close` method wakes both groups of waiting operations.

### 12.6 ExecutorService

`TaskProcessor` uses a fixed-size executor.

Its generic `submit` method accepts a `Callable`.

Atomic counters record completed and failed tasks.

The service also manages executor shutdown and interruption.

### 12.7 Enterprise Implications

Enterprise concurrency design must consider more than whether a method is synchronized.

Important requirements include:

- Consistent business invariants.
- Explicit transaction boundaries.
- Safe failure handling.
- Controlled resource usage.
- Lock ownership.
- Immutable external snapshots.
- Conflict detection.
- Graceful shutdown.
- Observability.

Compile:

`javac ConcurrencyEnterprise.java`

Run:

`java ConcurrencyEnterprise`

No third-party dependencies are required.

## 13. PostgreSQL Concurrency Model

Concurrency in relational databases involves transactions, isolation levels, locks, constraints, and conflict detection.

The SQL implementation models an inventory reservation and background task-processing system.

### 13.1 Transaction

A transaction groups operations into one logical unit.

PostgreSQL provides the ACID properties:

| Property | Meaning |
|---|---|
| Atomicity | All transaction changes succeed or are rolled back |
| Consistency | Transactions preserve applicable integrity rules |
| Isolation | Concurrent transactions are controlled according to the selected isolation level |
| Durability | Committed changes survive normal database restart conditions |

The SQL script uses explicit transactions for resource reservations, updates, task claiming, and rollback demonstrations.

### 13.2 Row-Level Locks

PostgreSQL supports row-level locking through statements such as:

- `SELECT FOR UPDATE`
- `SELECT FOR NO KEY UPDATE`
- `SELECT FOR SHARE`
- `SELECT FOR KEY SHARE`

`SELECT FOR UPDATE` is useful when an application needs to inspect a row and then modify it without allowing a competing transaction to modify that row first.

The `inspect_resource_with_lock` function demonstrates this mechanism.

The lock remains active until the surrounding transaction completes.

### 13.3 Atomic Conditional Updates

The `reserve_resource` function performs a conditional update:

- Identify the resource.
- Check that sufficient stock exists.
- Decrease stock.
- Create the reservation.
- Record an audit event.

The conditional update protects the stock invariant.

If another transaction updates the same resource concurrently, PostgreSQL coordinates access through row-level locking and re-evaluates the applicable update condition against the current row.

This prevents two competing transactions from successfully consuming the same available units.

The database constraint independently prohibits negative inventory.

### 13.4 Optimistic Version Control

The `resources` table includes a `version` column.

`update_resource_optimistically` requires an expected version.

The update is accepted only if the stored version matches the submitted version.

The trigger increments the version during updates.

A stale request receives a `CONFLICT` result rather than silently replacing newer data.

### 13.5 SKIP LOCKED

`SKIP LOCKED` is particularly useful for task queues.

Suppose three workers claim pending tasks simultaneously.

Without appropriate coordination, multiple workers might attempt to process the same task.

The `claim_next_task` function uses:

`FOR UPDATE SKIP LOCKED`

Each worker can claim an available task without waiting for another worker's already-locked task.

The task state changes to `PROCESSING` inside the same transaction.

This makes the claiming operation atomic.

`SKIP LOCKED` is designed for queue-like workloads. It does not guarantee strict fairness, and skipped rows may remain unprocessed while their locks are held.

### 13.6 NOWAIT

`NOWAIT` is useful when waiting for a conflicting lock is unacceptable.

A statement using `FOR UPDATE NOWAIT` immediately reports a lock conflict rather than waiting.

This is appropriate when the application can return a temporary-busy response or retry later.

### 13.7 Advisory Locks

Advisory locks provide application-defined coordination.

They do not depend on a particular table row being locked.

PostgreSQL supports:

- Session-level advisory locks.
- Transaction-level advisory locks.
- Blocking advisory lock acquisition.
- Nonblocking advisory lock acquisition.

The SQL implementation demonstrates a transaction-level advisory lock.

The application must define a consistent lock-key convention and ensure that all participating processes follow it.

### 13.8 Deadlock Detection

PostgreSQL automatically detects deadlocks.

Consider two transactions:

- Transaction A locks resource 1 and requests resource 2.
- Transaction B locks resource 2 and requests resource 1.

This creates a circular wait.

PostgreSQL detects the deadlock and aborts one transaction.

The application must handle the error and, where appropriate, retry the entire transaction.

A useful prevention strategy is to acquire multiple resources in a consistent order.

### 13.9 Isolation Levels

PostgreSQL supports four standard transaction isolation levels:

| Isolation level | Main behavior |
|---|---|
| Read Uncommitted | Behaves as Read Committed in PostgreSQL |
| Read Committed | Each statement obtains a new snapshot |
| Repeatable Read | The transaction operates on a consistent snapshot |
| Serializable | Prevents serialization anomalies through conflict detection and possible transaction aborts |

PostgreSQL's default isolation level is Read Committed.

Serializable transactions provide stronger guarantees but may require application-level retries after serialization failures.

The correct isolation level depends on the business invariant and transaction workload.

### 13.10 Database Integrity

The SQL implementation uses:

- Primary keys.
- Foreign keys.
- Unique request references.
- Quantity constraints.
- State constraints.
- Partial indexes.
- Audit triggers.

These controls prevent invalid data from entering the database through concurrent operations or different application paths.

Application-level locking alone is insufficient for database integrity because multiple applications or processes may access the same tables.

## 14. Important Concurrency Design Distinctions

Several mechanisms solve related but different problems.

| Mechanism | Primary responsibility |
|---|---|
| Mutex | Exclusive access to protected state |
| Reentrant lock | Exclusive access with same-owner reacquisition |
| Semaphore | Limits concurrent resource usage |
| Condition variable | Coordinates execution around a condition |
| Atomic operation | Provides indivisible access to a supported value |
| Read-write lock | Separates concurrent readers from exclusive writers |
| Optimistic version check | Detects stale modifications |
| Database transaction | Groups database operations into a logical unit |
| Row-level lock | Coordinates conflicting operations on database rows |
| Advisory lock | Coordinates application-defined logical resources |
| Thread pool | Reuses a controlled set of worker threads |
| Bounded queue | Limits pending work and coordinates producers and consumers |

These mechanisms are complementary.

For example, an application may use a thread pool to manage execution, a semaphore to limit external connections, a mutex to protect an in-memory cache, and a database transaction to maintain inventory consistency.

## 15. Performance Considerations

Synchronization introduces overhead.

The main performance concerns include:

### Lock Contention

When many execution contexts request the same lock, waiting time increases.

Possible improvements:

- Reduce critical-section duration.
- Separate independent resources.
- Partition shared data.
- Avoid unnecessary locking.
- Use immutable snapshots where appropriate.

### Excessive Thread Creation

Creating a new thread for every task increases memory consumption and scheduling overhead.

Thread pools provide a more controlled execution model.

### Unbounded Queues

Unbounded queues can consume excessive memory when producers generate work faster than consumers can process it.

Bounded queues introduce backpressure.

### Database Lock Duration

Long-running transactions hold locks for longer periods.

This increases contention and can delay unrelated operations.

Database transactions should avoid unnecessary external calls and expensive computation while holding locks.

### Atomic Operations

Atomic operations can be more efficient than mutexes for simple independent values.

They are not universally faster.

Contention on one atomic variable can become a scalability bottleneck.

### Lock Granularity

Fine-grained locks can improve parallel progress, but they introduce more complex acquisition and release rules.

The appropriate granularity depends on workload characteristics and correctness requirements.

## 16. Security and Reliability Considerations

Concurrency errors can have direct security and financial consequences.

Examples include:

- Duplicate payments.
- Oversold inventory.
- Incorrect account balances.
- Duplicate job execution.
- Unauthorized state transitions.
- Inconsistent access-control changes.
- Corrupted shared files.
- Resource exhaustion.

Important controls include:

1. Validate all inputs before modifying shared state.
2. Enforce business invariants inside the database.
3. Use unique idempotency references for externally retried operations.
4. Limit concurrent resource consumption.
5. Avoid exposing mutable internal collections.
6. Keep critical sections small.
7. Use explicit shutdown and cancellation behavior.
8. Handle transaction failures and retryable conflicts.
9. Audit important state transitions.
10. Avoid relying exclusively on in-memory locks for distributed systems.

A database transaction cannot automatically reverse an external payment, email, or network request. Such workflows need explicit coordination mechanisms, such as idempotency controls and transactional outbox processing.

## 17. Complexity and Engineering Trade-offs

| Mechanism | Typical operation cost | Main trade-off |
|---|---|---|
| Mutex acquisition | Constant-time uncontended in typical implementations | Waiting under contention |
| Atomic increment | Constant-time operation | Cache-line contention |
| Semaphore acquisition | Depends on contention and waiter management | Permit management |
| Condition variable | Depends on wake-up and scheduling | More complex state coordination |
| Read-write lock | Depends on readers, writers, and contention | Writer starvation or additional overhead |
| Version check | Constant-time comparison and update | Conflict retries |
| Hash-partitioned locking | Average constant-time key lookup plus lock acquisition | Hash collisions and snapshot coordination |
| Database row update | Depends on indexes, locks, and transaction workload | Lock contention and transaction overhead |
| Serializable transaction | Depends on conflict detection and retries | Higher transaction abort probability |

These are conceptual operation costs rather than universal performance guarantees. Actual costs depend on implementation, scheduling, hardware, workload, and contention.

## 18. Edge Cases and Failure Modes

A production concurrency system should explicitly handle the following conditions.

| Failure condition | Possible consequence | Control |
|---|---|---|
| Lock not released | Permanent waiting | RAII, `finally`, structured locking |
| Double release | Invalid synchronization state | Release-state validation |
| Stale version | Lost update | Version comparison |
| Deadlock | Transaction or thread cannot progress | Consistent acquisition order and retries |
| Starvation | Delayed execution | Fair scheduling policies |
| Spurious wake-up | Incorrect queue processing | Predicate-based condition waits |
| Queue shutdown | Blocked producers or consumers | Explicit close and notification |
| Thread interruption | Incomplete task execution | Interruption handling |
| Worker failure | Lost or incomplete work | Failure tracking and retry policy |
| Duplicate request | Duplicate state modification | Idempotency keys |
| Integer overflow | Invalid financial or inventory values | Range validation |
| Process crash | In-memory state loss | Durable database transactions |
| Distributed lock expiration | Concurrent ownership | Fencing tokens and ownership validation |

## 19. Implementation Comparison

| Feature | Python | JavaScript | C++17 | Java 17 | PostgreSQL |
|---|---|---|---|---|---|
| Main concurrency model | Threads and futures | Event loop and promises | Native threads | Threads and executors | Concurrent transactions |
| Mutual exclusion | `threading.Lock` | Promise mutex | `std::mutex` | `ReentrantLock` | Row-level locks |
| Reentrant locking | `threading.RLock` | Custom implementation | Custom design or recursive mutex | `ReentrantLock` | Transaction and lock semantics |
| Atomic operations | Lock-protected updates | Synchronous execution within one isolate | `std::atomic` | Atomic classes | Atomic SQL statements |
| Condition synchronization | `Condition` | Promise queues | `condition_variable` | `Condition` | Lock and transaction coordination |
| Read-write synchronization | Application-specific | Custom read-write lock | `shared_mutex` | `ReentrantReadWriteLock` | MVCC and row locks |
| Bounded processing | Bounded buffer | Semaphore | Bounded queue | Bounded queue | `SKIP LOCKED` |
| Optimistic control | Versioned state | Versioned document | Versioned state | Versioned document | Version columns |
| Failure management | Exceptions and futures | Promise rejection | Exceptions and RAII | Exceptions and executor lifecycle | Rollback and transaction errors |

## 20. Execution and Verification

The implementations are independent and can be executed separately.

| File | Execution |
|---|---|
| `concurrency.py` | `python concurrency.py` |
| `concurrency.js` | `node concurrency.js` |
| `concurrency.cpp` | `g++ -std=c++17 -O2 -pthread concurrency.cpp -o concurrency` |
| `ConcurrencyEnterprise.java` | `javac ConcurrencyEnterprise.java` followed by `java ConcurrencyEnterprise` |
| `concurrency.sql` | Execute using PostgreSQL through `psql` or a compatible SQL client |

The PostgreSQL script recreates its dedicated `concurrency_lab` schema. It should therefore be executed in a database reserved for this exercise.

The programming implementations use standard libraries rather than external dependencies.

The verification procedures focus on invariants rather than assuming a particular thread scheduling order.

Important invariants include:

- Account balances cannot become negative.
- Transfers preserve the total account balance.
- Inventory quantities cannot become negative.
- A bounded queue cannot exceed its configured capacity.
- A semaphore cannot exceed its permitted concurrent operations.
- Stale optimistic updates are rejected.
- Every successfully claimed task has an identifiable worker.
- Completed concurrent processing preserves expected totals.

## 21. Practical Implications

Concurrency correctness depends on selecting the right synchronization boundary.

A mutex protects an in-memory critical section. An atomic operation protects an individual supported state transition. A condition variable coordinates waiting execution contexts. A semaphore limits concurrent resource consumption. A version check detects stale updates. A database transaction protects a group of persistent operations.

These mechanisms should be selected according to the resource being protected, the scope of competing operations, the expected conflict frequency, and the consequences of inconsistent state.

A reliable concurrent system combines synchronization, validation, controlled execution, explicit failure handling, and independently enforced data integrity.
