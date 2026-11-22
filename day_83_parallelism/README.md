# Parallelism: Multithreading and Multiprocessing

## 1. Technical Foundation

Parallelism is the execution of multiple computational operations at the same time using multiple processing resources.

Concurrency and parallelism are related but different concepts.

- **Concurrency** describes the management of multiple tasks whose execution periods overlap.
- **Parallelism** describes multiple tasks executing simultaneously.
- **Multithreading** divides application execution into multiple threads within a process.
- **Multiprocessing** uses multiple operating-system processes to execute work independently.
- **Asynchronous execution** allows an operation to continue without blocking the execution flow while it waits for another event or resource.

A concurrent application is not necessarily parallel. A single-threaded event loop can coordinate many network requests concurrently without executing their JavaScript instructions simultaneously.

A multicore processor can execute multiple threads or processes in parallel, subject to operating-system scheduling and available resources.

### Execution model

| Property | Sequential | Multithreading | Multiprocessing |
|---|---|---|---|
| Execution units | One execution flow | Multiple threads | Multiple processes |
| Address space | One process | Shared process memory | Separate process memory |
| Communication | Direct function calls | Shared memory or messages | IPC or messages |
| Creation overhead | Low | Usually moderate | Usually higher |
| Shared-state complexity | Low | High | Lower for private memory |
| CPU parallelism | Generally one execution core | Possible | Possible |
| Isolation | Process-level | Limited between threads | Stronger process isolation |
| Typical applications | Small sequential tasks | I/O and concurrent services | CPU-intensive computation |

The actual performance depends on workload characteristics, scheduling, memory access, synchronization, and hardware.

---

## 2. Processes, Threads, and Execution Resources

### 2.1 Process

A process is an independently scheduled operating-system execution environment.

A process normally contains:

- Virtual address space.
- Executable code.
- Heap memory.
- One or more threads.
- Open file descriptors or operating-system handles.
- Process-specific resources.
- Security and permission context.

Processes do not normally share ordinary heap memory. They communicate using mechanisms such as:

- Pipes.
- Sockets.
- Shared memory.
- Message queues.
- Files.
- Remote procedure calls.

Process isolation reduces accidental interference between workloads. Communication and process creation introduce additional costs.

### 2.2 Thread

A thread is an execution path inside a process.

Threads in the same process generally share:

- Heap memory.
- Global variables.
- Process resources.
- Open file descriptors.

Each thread has its own:

- Stack.
- Program counter.
- Register state.
- Thread-local storage.

Shared memory makes communication efficient but creates synchronization requirements.

A thread can corrupt shared state if multiple execution paths modify the same data without appropriate coordination.

### 2.3 CPU cores and hardware threads

A CPU core provides physical execution resources. Simultaneous multithreading allows a physical core to maintain multiple hardware execution contexts.

The following quantities are not equivalent:

- Number of application threads.
- Number of operating-system processes.
- Number of logical processors.
- Number of physical CPU cores.

Creating 100 threads does not create 100 physical CPU cores.

The operating system schedules runnable threads onto available processors.

---

## 3. Workload Classification

The correct execution model depends primarily on the workload.

### 3.1 CPU-bound workloads

CPU-bound operations spend most of their execution time performing calculations.

Examples:

- Prime-number computation.
- Image transformations.
- Cryptographic calculations.
- Scientific simulations.
- Numerical optimization.
- Large-scale data transformations.

For CPU-bound tasks, multiprocessing can provide actual parallel execution without requiring multiple threads to share one interpreter execution lock.

In Python implementations using the conventional GIL-enabled CPython runtime, the Global Interpreter Lock restricts simultaneous execution of Python bytecode by multiple threads within one interpreter. Multiprocessing uses independent interpreters and processes, allowing CPU-bound work to execute across multiple cores.

This behavior is implementation-dependent. Free-threaded Python builds and other Python implementations have different execution characteristics.

### 3.2 I/O-bound workloads

I/O-bound operations spend much of their time waiting for external resources.

Examples:

- HTTP requests.
- Database queries.
- File access.
- Network communication.
- Remote API calls.

Threads are useful because another thread can perform work while one thread waits.

Asynchronous programming can also coordinate large numbers of I/O operations without creating one operating-system thread for every operation.

### 3.3 Memory-bound workloads

Memory-bound workloads are limited by memory bandwidth, cache behavior, or memory latency.

Examples:

- Large matrix traversal.
- Dataframe transformations.
- Memory-intensive analytics.
- Large-scale array processing.

Adding workers does not guarantee higher performance. Workers can compete for memory bandwidth and cache capacity.

### 3.4 Mixed workloads

A mixed workload contains multiple resource demands.

For example, an analytics pipeline might:

1. Retrieve records from a database.
2. Decode and validate them.
3. Perform numerical calculations.
4. Store processed results.

A suitable design may use asynchronous I/O for retrieval and a bounded CPU worker pool for numerical calculations.

---

## 4. Multithreading Mechanics

Multithreading allows multiple threads to execute within a shared process.

A thread pool is generally preferable to repeatedly creating new threads for individual tasks.

A pool provides:

- Worker reuse.
- Controlled concurrency.
- Reduced thread-creation overhead.
- Centralized task submission.
- Consistent lifecycle management.

### 4.1 Thread lifecycle

A typical thread progresses through these conceptual states:

| State | Meaning |
|---|---|
| New | Thread has been created |
| Runnable | Thread can be scheduled |
| Running | Thread is executing |
| Blocked | Waiting for a lock or resource |
| Waiting | Waiting for another execution path |
| Terminated | Execution has finished |

The exact operating-system and runtime state models vary.

### 4.2 Synchronization

Synchronization controls access to shared mutable state.

Common mechanisms include:

| Mechanism | Purpose |
|---|---|
| Mutex | Exclusive access to shared data |
| Lock | Controls entry into a critical section |
| Atomic variable | Provides atomic operations |
| Semaphore | Controls access to a limited resource |
| Condition variable | Allows threads to wait for conditions |
| Barrier | Synchronizes multiple participants |
| Read-write lock | Allows concurrent readers and exclusive writers |

A critical section is a portion of code that accesses shared state and requires coordination.

### 4.3 Race conditions

A race condition occurs when the result depends on the timing or interleaving of concurrent operations.

Consider a shared counter.

The logical operation:

1. Read counter.
2. Add one.
3. Write updated counter.

is not necessarily atomic.

Two threads can read the same value and overwrite each other's updates.

An atomic increment or mutex-protected critical section prevents this lost-update behavior.

### 4.4 Deadlocks

A deadlock occurs when execution paths wait indefinitely for resources held by one another.

The four classical deadlock conditions are:

- Mutual exclusion.
- Hold and wait.
- No preemption.
- Circular wait.

Practical prevention techniques include:

- Acquiring locks in a consistent order.
- Minimizing lock duration.
- Avoiding unnecessary nested locks.
- Using timeouts where appropriate.
- Avoiding external calls while holding critical locks.

### 4.5 Producer-consumer architecture

The producer-consumer pattern separates task creation from task execution.

A producer inserts work into a queue. A consumer retrieves and processes it.

A bounded queue provides backpressure by limiting pending work.

Without backpressure, a producer can create tasks faster than consumers can process them, leading to excessive memory consumption.

The C++ implementation uses a bounded queue, mutex, and condition variables. The Java implementation uses `ArrayBlockingQueue`. The Python implementation uses `queue.Queue`.

---

## 5. Multiprocessing Mechanics

Multiprocessing uses independent operating-system processes.

Each process normally owns a separate virtual address space.

### 5.1 Process creation

Operating systems provide different process-creation mechanisms.

- Unix-like systems commonly support `fork`.
- Windows uses process creation mechanisms based on process startup and executable initialization.
- Python multiprocessing supports `spawn`, `fork`, and, where available, `forkserver`.

The startup method affects initialization, resource inheritance, and serialization requirements.

Python process-pool functions should be defined at module scope when they must be serialized.

The `if __name__ == "__main__"` guard prevents unintended process creation during module import on platforms using spawn-based initialization.

### 5.2 Inter-process communication

Processes need explicit communication mechanisms.

| Mechanism | Characteristics |
|---|---|
| Pipe | Stream communication between processes |
| Socket | Local or network communication |
| Shared memory | Shared data region |
| Message queue | Structured message exchange |
| File | Persistent exchange through storage |
| RPC | Remote operation invocation |

Shared memory can reduce data-copying overhead, but it reintroduces synchronization and memory-consistency requirements.

### 5.3 Process pools

A process pool maintains a controlled collection of reusable processes.

A typical workflow is:

1. Define independent tasks.
2. Submit tasks to the pool.
3. Serialize task arguments where required.
4. Execute tasks in worker processes.
5. Collect results.
6. Handle exceptions.
7. Shut down the pool.

The Python implementation uses `ProcessPoolExecutor`.

### 5.4 Multiprocessing tradeoffs

Multiprocessing offers stronger isolation but introduces:

- Process startup overhead.
- Serialization costs.
- Memory duplication.
- Inter-process communication costs.
- More complex resource management.
- Additional failure and recovery handling.

It is generally most beneficial when computational work is sufficiently large to justify these costs.

---

## 6. Asynchronous Execution and Event-Driven Concurrency

Asynchronous execution is not synonymous with multithreading.

An asynchronous function can suspend while waiting for an operation and allow other tasks to progress.

A typical event-driven architecture contains:

- An event loop.
- A task scheduler.
- Awaitable operations.
- Completion callbacks.
- Error propagation.
- Cancellation handling.

The JavaScript implementation demonstrates this model using Promises and asynchronous functions.

### 6.1 Event-loop execution

JavaScript normally executes application code on a main event-loop thread.

When an asynchronous operation waits for a timer, network response, or other event, the event loop can process other ready work.

This allows substantial I/O concurrency without requiring one thread per operation.

### 6.2 Worker threads

Node.js worker threads provide separate JavaScript execution environments.

They are useful for CPU-intensive operations that would otherwise block the main event loop.

Worker threads can communicate using:

- Message passing.
- Structured-clone data transfer.
- Transferable objects.
- SharedArrayBuffer.
- Atomic operations.

The JavaScript implementation uses worker threads to distribute prime-counting tasks.

### 6.3 SharedArrayBuffer and Atomics

`SharedArrayBuffer` provides memory that can be accessed by multiple worker threads.

`Atomics.add()` performs an atomic update.

Atomic operations prevent concurrent workers from losing updates to shared values.

Shared memory should be used carefully because synchronization mistakes can produce difficult concurrency defects.

---

## 7. Parallel Scheduling and Task Distribution

Task scheduling determines which worker executes which task and when.

### 7.1 Static scheduling

Static scheduling assigns tasks before execution.

Example:

- Worker 1 receives tasks 1 and 4.
- Worker 2 receives tasks 2 and 5.
- Worker 3 receives tasks 3 and 6.

Advantages:

- Low scheduling overhead.
- Predictable assignment.
- Simple implementation.

Disadvantages:

- Poor load balancing when task durations differ.
- Some workers may finish early and remain idle.

### 7.2 Dynamic scheduling

Dynamic scheduling assigns work as workers become available.

A shared task queue can distribute work according to worker availability.

Advantages:

- Better handling of variable task durations.
- Improved worker utilization.
- Natural support for producer-consumer systems.

Disadvantages:

- Queue coordination overhead.
- Potential contention.
- More complicated scheduling behavior.

### 7.3 Work stealing

Work stealing allows an idle worker to obtain tasks from another worker's queue.

The Java implementation demonstrates the `ForkJoinPool` and recursive divide-and-conquer processing.

A computation is split into smaller tasks until each task reaches a configured threshold.

This reduces centralized scheduling pressure and supports dynamic load balancing.

### 7.4 Chunk size

Chunk size determines how much work is assigned to each task.

Small chunks:

- Improve scheduling flexibility.
- Increase scheduling overhead.

Large chunks:

- Reduce scheduling overhead.
- May create load imbalance.

The correct chunk size depends on workload duration, scheduling costs, and resource characteristics.

---

## 8. Performance Engineering

Parallelism should be evaluated through measurement rather than assumptions.

### 8.1 Execution time

Execution time is the elapsed duration between the beginning and completion of a workload.

\[
T = t_{\text{end}} - t_{\text{start}}
\]

For reliable benchmarks:

- Use equivalent input.
- Compare identical output.
- Perform multiple runs.
- Separate initialization from steady-state execution.
- Control worker counts.
- Account for background system activity.

The implementations use high-resolution timing facilities appropriate to their respective runtimes.

### 8.2 Speedup

Speedup compares sequential execution time with parallel execution time.

\[
S(p) = \frac{T_1}{T_p}
\]

Where:

- \(T_1\) is sequential execution time.
- \(T_p\) is execution time using \(p\) workers.

A speedup of 2 means the measured parallel execution takes half the sequential execution time.

### 8.3 Parallel efficiency

Parallel efficiency measures how effectively available workers contribute to execution.

\[
E(p) = \frac{S(p)}{p}
\]

An efficiency of 1 represents ideal linear scaling.

Real applications usually experience scheduling, synchronization, and resource overhead.

### 8.4 Amdahl's Law

Amdahl's Law explains the effect of the sequential portion of a workload on achievable speedup.

\[
S(p) =
\frac{1}
{(1-f)+\frac{f}{p}}
\]

Where:

- \(f\) is the parallelizable fraction.
- \(1-f\) is the sequential fraction.
- \(p\) is the number of processing resources.

Even with an unlimited number of workers, the sequential portion limits maximum speedup.

### 8.5 Gustafson's Law

Gustafson's Law considers workloads that grow with available processing resources.

It explains why larger problems can sometimes scale effectively even when a fixed-size benchmark shows limited speedup.

### 8.6 Overhead and bottlenecks

Performance can be reduced by:

- Thread creation.
- Process startup.
- Task serialization.
- Lock contention.
- Memory allocation.
- Cache misses.
- Context switching.
- Queue contention.
- Network communication.
- Excessive task scheduling.

A practical implementation should measure these costs separately when possible.

---

## 9. Python Implementation

The Python script provides a comparative execution framework.

### 9.1 Sequential execution

`execute_sequential()` processes tasks one at a time.

It provides the reference result against which concurrent implementations are checked.

### 9.2 ThreadPoolExecutor

`execute_with_threads()` submits tasks to a bounded thread pool.

`as_completed()` retrieves completed futures without requiring tasks to finish in submission order.

Exceptions are captured independently, allowing other tasks to continue.

### 9.3 ProcessPoolExecutor

`execute_with_processes()` uses independent processes.

The CPU-intensive prime-counting function is defined at module level so that it can be serialized for process execution.

The main guard ensures safe process initialization.

### 9.4 Synchronization

`ThreadSafeCounter` protects a compound counter update with a mutex.

The expected result is 80,000 increments across eight threads.

### 9.5 Producer-consumer processing

`demonstrate_producer_consumer()` uses a bounded queue.

The producer inserts ten items, while the consumer retrieves them independently.

A sentinel indicates the end of production.

### 9.6 Failure handling

The implementation includes:

- Input validation.
- Per-task exception isolation.
- Worker-pool cleanup.
- Logging.
- Result ordering.
- Output equivalence assertions.

### Execution

- Python 3.10 or later.
- No third-party dependencies.

Supported commands:

| Command | Behavior |
|---|---|
| `python parallelism.py` | Executes both workloads |
| `python parallelism.py --workload cpu` | Executes CPU benchmarks |
| `python parallelism.py --workload io` | Executes I/O benchmarks |
| `python parallelism.py --tasks 10 --limit 100000` | Configures task count and computation limit |

---

## 10. JavaScript Implementation

The JavaScript file emphasizes event-driven execution and worker-based parallelism.

### 10.1 Promise-based scheduling

`executeWithConcurrency()` implements a bounded asynchronous worker pattern.

A shared task index distributes work among asynchronous workers.

Each operation is awaited before that worker retrieves its next task.

The design prevents unrestricted submission of asynchronous work.

### 10.2 Worker-thread computation

`executeWithWorkers()` distributes CPU-intensive tasks across worker threads.

Each worker executes an independent batch and sends structured results through its parent port.

The main thread collects results and sorts them by task ID.

### 10.3 Failure isolation

The worker execution layer handles:

- Worker errors.
- Non-zero worker exit codes.
- Invalid task definitions.
- Failed asynchronous operations.
- Inconsistent result detection.

A production worker supervisor should also implement explicit timeouts, termination policies, and retry limits.

### 10.4 Atomic shared state

`demonstrateSharedMemory()` creates shared integer memory.

Four workers each perform 10,000 atomic increments.

The expected result is 40,000.

### Execution

Requires Node.js 18 or later.

Run:

`node parallelism.js`

No external npm packages are required.

---

## 11. C++17 Implementation

The C++ program demonstrates explicit control over threads, synchronization, and execution resources.

### 11.1 Thread creation

`executeParallel()` creates a bounded collection of threads.

Workers obtain task indexes using `std::atomic`.

Each task writes to a separate result-vector element.

The main thread joins every worker before accessing completed results.

### 11.2 Atomic synchronization

`demonstrateAtomicCounter()` uses `std::atomic<std::uint64_t>`.

The `memory_order_relaxed` setting is appropriate for this counter because the counter itself is the only shared information being coordinated.

It guarantees atomic updates without establishing additional synchronization ordering for unrelated memory.

### 11.3 Mutex-protected account

`BankAccount` protects balance modifications using `std::mutex`.

Withdrawal and deposit operations validate their inputs and prevent invalid balance updates.

### 11.4 Producer-consumer queue

`BoundedQueue<T>` combines:

- `std::queue`.
- `std::mutex`.
- `std::condition_variable`.

The producer waits when the queue is full.

The consumer waits when the queue is empty.

Closing the queue wakes waiting participants and permits orderly shutdown.

### 11.5 Futures and asynchronous execution

`executeAsync()` uses `std::async` and `std::future`.

The `std::launch::async` policy explicitly requests asynchronous execution.

Calling `future.get()` retrieves the result and propagates task exceptions.

### Compilation

Requires a C++17-compatible compiler and thread support.

Compile:

`g++ -std=c++17 -O2 -pthread parallelism.cpp -o parallelism`

Execute:

`./parallelism`

On Windows with a compatible MinGW toolchain:

`g++ -std=c++17 -O2 -pthread parallelism.cpp -o parallelism.exe`

---

## 12. Java 17 Implementation

The Java implementation models enterprise-oriented task execution.

### 12.1 ExecutorService

`ExecutorService` manages reusable worker threads.

The fixed thread pool controls the maximum number of simultaneously executing tasks.

The implementation explicitly shuts down its executor and attempts graceful termination.

### 12.2 Callable and Future

A `Callable` represents a computation that returns a value and can throw an exception.

A `Future` provides access to the result of an asynchronous computation.

`Future.get()` blocks until completion and exposes execution failures through `ExecutionException`.

### 12.3 CompletableFuture

`CompletableFuture` supports asynchronous composition and coordination.

The implementation submits tasks to an explicitly configured executor.

`allOf()` represents completion of the submitted task set.

### 12.4 ForkJoinPool

The `PrimeCountTask` class extends `RecursiveTask<Long>`.

The computation is recursively divided into smaller ranges.

When a range reaches the configured threshold, it is calculated directly.

This demonstrates divide-and-conquer parallelism and work stealing.

### 12.5 LongAdder

`LongAdder` supports highly contended statistical counters.

It reduces contention compared with a single heavily contended atomic counter by distributing update activity internally.

Its `sum()` method provides the aggregated count.

It is suitable for statistical accumulation, not for enforcing transactional invariants.

### 12.6 ReentrantLock

The account implementation uses `ReentrantLock` to protect balance updates.

The lock is always released through a `finally` block.

### Compilation

Requires Java 17.

Compile:

`javac ParallelismLab.java`

Execute:

`java ParallelismLab`

---

## 13. PostgreSQL Implementation

The PostgreSQL implementation models an application-managed parallel execution platform.

It distinguishes database persistence and task scheduling from the actual execution of operating-system threads and processes.

PostgreSQL stores workload definitions, task ownership, execution state, worker capacity, and audit information.

### 13.1 Relational model

| Table | Responsibility |
|---|---|
| `compute_clusters` | Logical worker clusters |
| `workers` | Worker registration and available capacity |
| `workloads` | Workload characteristics and resource requirements |
| `execution_tasks` | Individual executable tasks |
| `execution_events` | Historical execution events |

The relationship is:

`Compute Cluster → Workers → Execution Tasks`

`Workload → Execution Tasks → Execution Events`

### 13.2 Workload classification

Each workload has a type:

- `CPU_BOUND`
- `IO_BOUND`
- `MEMORY_BOUND`
- `MIXED`

Each workload also declares an execution mode:

- `SEQUENTIAL`
- `MULTITHREADING`
- `MULTIPROCESSING`
- `DISTRIBUTED`

These classifications describe execution requirements rather than guaranteeing that a particular worker has sufficient resources.

### 13.3 Task state management

Tasks use the following states:

| State | Meaning |
|---|---|
| `QUEUED` | Waiting for execution |
| `RUNNING` | Assigned to a worker |
| `COMPLETED` | Successfully executed |
| `FAILED` | Permanently failed or exhausted retries |
| `CANCELLED` | Administratively cancelled |

The database enforces assignment and lease constraints.

A running task must have an assigned worker and an expiration timestamp.

A non-running task cannot retain an active worker assignment.

### 13.4 Concurrent task claiming

`claim_next_task()` uses:

`FOR UPDATE SKIP LOCKED`

This mechanism is important for concurrent workers.

Suppose two worker transactions attempt to retrieve the same highest-priority task.

The first transaction locks the selected row.

The second transaction skips that locked row and can claim another available task.

This prevents duplicate claims through the database queue.

The worker should commit its claim transaction before beginning lengthy computation.

### 13.5 Worker capacity

The worker registry tracks:

- CPU cores.
- Memory capacity.
- Maximum concurrent tasks.
- Active task count.
- Worker availability.
- Heartbeat timestamp.

The eligibility function checks whether a worker satisfies the declared workload requirements.

Resource declarations are scheduling metadata. They do not guarantee actual physical resource availability.

### 13.6 Leases and recovery

A lease gives a worker temporary ownership of a task.

The lease prevents an abandoned task from remaining permanently assigned after worker failure.

`recover_expired_tasks()` finds expired running tasks and returns retryable tasks to the queue.

Tasks that exhaust their retry allowance become failed.

This is a basic at-least-once execution design.

A worker may finish a computation but fail before recording completion. The task may subsequently be reassigned.

Consequently, production workloads should use idempotent task operations or deduplication keys.

### 13.7 Retry policies

`fail_task()` implements bounded retry handling.

Retry delays use exponential backoff, with a maximum delay of 300 seconds.

Retries reduce the impact of temporary failures, but they should not be unlimited.

Permanent input errors should be distinguished from temporary infrastructure failures.

### 13.8 Audit events

`execution_events` records:

- Task submission.
- Task claims.
- Completion.
- Failure.
- Retry.
- Cancellation.
- Lease expiration.

This supports operational reporting and execution-history analysis.

### 13.9 Performance considerations

The database uses partial indexes for queued tasks and running leases.

Partial indexes reduce the index population when only a subset of task states requires frequent lookup.

The workload aggregation queries use filtered aggregates to report completed, failed, queued, and running tasks separately.

`EXPLAIN (ANALYZE, BUFFERS)` supports execution-plan inspection.

The database is intended to coordinate execution, not perform all computational work inside SQL transactions.

Long-running computations should occur outside transactions to avoid holding database locks and connections unnecessarily.

---

## 14. Comparison of the Five Implementations

| Engineering concept | Python | JavaScript | C++17 | Java 17 | PostgreSQL |
|---|---|---|---|---|---|
| Sequential processing | Direct function calls | Direct execution | Direct function calls | Direct method calls | SQL queries |
| Thread execution | ThreadPoolExecutor | Worker Threads | std::thread | ExecutorService | External workers |
| Process execution | ProcessPoolExecutor | External processes not implemented | External processes not implemented | External processes not implemented | External workers |
| Asynchronous execution | Futures | Promises | std::async | CompletableFuture | Transaction coordination |
| Shared state | Locks | SharedArrayBuffer | Atomics and mutex | LongAdder and locks | Transactional rows |
| Task distribution | Futures | Bounded task scheduling | Atomic task indexing | Executor and ForkJoinPool | SKIP LOCKED |
| Producer-consumer | queue.Queue | Promise-based bounded workers | Condition variables | ArrayBlockingQueue | Persistent task queue |
| Failure management | Future exceptions | Worker errors and rejected operations | Exception propagation | Future exceptions | Retries and leases |
| Persistence | Not required | Not required | Not required | Not required | Relational tables |

The implementations use different mechanisms because each language and runtime exposes different concurrency abstractions.

The examples are complementary engineering models rather than identical benchmark environments.

---

## 15. Important Concurrency Failure Modes

| Failure | Cause | Mitigation |
|---|---|---|
| Race condition | Unsynchronized shared updates | Atomics or locks |
| Deadlock | Circular resource dependency | Consistent lock ordering |
| Starvation | Worker repeatedly denied resources | Fair scheduling where required |
| Livelock | Workers repeatedly react without progress | Backoff and coordination |
| Thread exhaustion | Excessive thread creation | Bounded thread pools |
| Memory exhaustion | Excessive task submission | Backpressure |
| Process failure | Worker crash or termination | Supervision and retries |
| Lost update | Concurrent writes overwrite each other | Synchronization or transactional updates |
| Duplicate execution | Retry after uncertain completion | Idempotency and deduplication |
| Stale ownership | Worker disappears while holding a task | Leases and heartbeat monitoring |
| Poor scaling | Scheduling overhead exceeds useful work | Appropriate task granularity |
| Resource contention | Workers compete for shared resources | Capacity-aware scheduling |

---

## 16. Security and Production Considerations

Parallel execution introduces security and operational concerns beyond ordinary sequential applications.

### Process isolation

Processes should run with only the permissions required for their tasks.

Sensitive credentials should not be unnecessarily inherited by child processes.

### Input validation

Task payloads should be validated before submission and again before execution.

The database should enforce structural and relational constraints.

### Resource limits

Control:

- Worker counts.
- Maximum pending tasks.
- CPU consumption.
- Memory allocation.
- Execution time.
- Retry counts.
- Queue capacity.

### Thread safety

Shared objects should have clearly defined ownership and synchronization rules.

Avoid exposing mutable internal state without protection.

### Failure recovery

A production system should include:

- Worker health monitoring.
- Task timeouts.
- Lease renewal.
- Bounded retries.
- Graceful shutdown.
- Dead-letter handling.
- Idempotent completion operations.

### Observability

Useful operational measurements include:

- Task throughput.
- Queue waiting time.
- Average execution duration.
- Worker utilization.
- Failed task percentage.
- Retry percentage.
- Memory utilization.
- CPU utilization.
- Context-switch activity.

### Benchmark integrity

A faster execution time is meaningful only when both implementations perform equivalent work and produce equivalent results.

Benchmarking should include repeated measurements and distinguish cold-start performance from steady-state performance.

---

## 17. Complexity Analysis

Let:

- \(n\) represent the number of input tasks.
- \(m\) represent the computational workload of an individual task.
- \(p\) represent the number of workers.
- \(k\) represent the number of producer-consumer queue operations.

| Operation | Approximate complexity |
|---|---|
| Task submission | \(O(1)\) per task, excluding scheduling overhead |
| Result collection | \(O(n)\) |
| Result sorting | \(O(n \log n)\) |
| Atomic increment | \(O(1)\) per operation, excluding contention |
| Mutex acquisition | Depends on contention |
| Queue insertion | \(O(1)\) amortized for the demonstrated queues |
| Queue removal | \(O(1)\) |
| Prime checking | \(O(\sqrt{x})\) |
| Prime counting up to \(N\) using trial division | Approximately \(O(N\sqrt{N})\) |
| Parallel task scheduling | Depends on queue and scheduler design |

For independent tasks, ideal execution time approaches the sequential work divided by the worker count.

Actual execution time also includes:

- Initialization.
- Scheduling.
- Synchronization.
- Communication.
- Serialization.
- Memory access.
- Resource contention.

---

## 18. Technical Boundaries

These examples are executable educational implementations, not complete production orchestration platforms.

The following distinctions are important:

1. Threads share process memory, while ordinary processes have independent address spaces.
2. Asynchronous execution can provide concurrency without simultaneous CPU execution.
3. Worker pools control execution resources but do not guarantee linear speedup.
4. Atomic operations protect specific updates, not arbitrary multi-step business transactions.
5. Locks protect shared state but can introduce contention and deadlocks.
6. Process isolation improves fault containment but increases communication overhead.
7. Task retries require careful handling of duplicate execution.
8. Database task claiming coordinates workers but does not execute application code.
9. PostgreSQL query parallelism is an independent database-engine feature and is not equivalent to an application-managed process pool.
10. CPU count is a useful scheduling input, not a universal worker-count prescription.

The appropriate parallel execution architecture is determined by workload characteristics, resource constraints, failure requirements, and the cost of coordinating independent execution paths.
