# Operating Systems: Processes, Threads, Memory, and Filesystems

## 1. Project Description

This project implements an operating-system resource-management simulator using five different technical perspectives: Python, JavaScript, C++17, Java 17, and PostgreSQL.

It covers four fundamental operating-system subsystems:

1. Process management and CPU scheduling.
2. Thread management and synchronization.
3. Physical and virtual memory management.
4. Filesystem organization and access control.

The implementations use executable models to demonstrate how operating systems manage execution, allocate resources, isolate workloads, and control access to stored information.

The models are educational simulations. They do not implement a bootable operating system, hardware interrupt handling, actual CPU context switching, kernel page tables, or a production disk filesystem.

## 2. Operating System Architecture

An operating system acts as an intermediary between application programs and computer hardware.

Its responsibilities include:

- Managing CPU execution.
- Creating and terminating processes.
- Scheduling threads.
- Allocating and reclaiming memory.
- Translating virtual addresses into physical addresses.
- Managing files and directories.
- Enforcing access permissions.
- Handling resource exhaustion and execution failures.

### Logical architecture

    User Applications
           |
           v
    System Call Interface
           |
           v
    Operating System Kernel
           |
           +----------------------+
           |                      |
           v                      v
    Process Management      Memory Management
           |                      |
           v                      v
    CPU Scheduling          Virtual Memory
           |                      |
           +----------+-----------+
                      |
                      v
               Filesystem Layer
                      |
                      v
                Storage Devices
                      |
                      v
                  Hardware

The kernel coordinates these components while maintaining resource ownership and isolation.

## 3. Processes and Process Management

### 3.1 Process definition

A process is an executing instance of a program.

A program is a passive collection of instructions stored on a storage device. A process represents an active execution environment containing resources and execution state.

A process typically includes:

- Process identifier (PID).
- Process state.
- Program instructions.
- Virtual address space.
- Stack and heap.
- Open file descriptors.
- Security credentials.
- One or more threads.
- Scheduling information.

### 3.2 Process Control Block

The Process Control Block (PCB) is the operating system's data structure for maintaining process information.

A typical PCB contains:

| Field | Purpose |
|---|---|
| PID | Unique process identifier |
| State | Current execution state |
| Program counter | Next instruction position |
| CPU registers | Saved processor state |
| Scheduling data | Priority and scheduling information |
| Memory information | Address-space and memory mappings |
| Accounting information | CPU time and resource usage |
| I/O information | Open files and pending operations |
| Credentials | User and security context |

The Python and Java implementations model important PCB attributes using process classes and state fields.

The C++ implementation uses structures and a process registry.

The JavaScript implementation uses structured objects stored in a `Map`.

PostgreSQL stores persistent representations in the `processes` and `threads` tables.

### 3.3 Process lifecycle

A process normally moves through several states.

| State | Meaning |
|---|---|
| New | Process is being created |
| Ready | Process can execute when scheduled |
| Running | Process currently owns CPU execution |
| Blocked | Process waits for an event or resource |
| Terminated | Process has completed or been stopped |

    NEW
     |
     v
    READY <-------------------+
     |                        |
     v                        |
    RUNNING                   |
     |                        |
     +----> BLOCKED ----------+
     |
     v
    TERMINATED

The transition from Running to Ready occurs when the scheduler preempts a process or its execution time slice expires.

The transition from Running to Blocked occurs when execution requires an unavailable resource, such as an I/O operation.

A terminated process cannot normally return to an active state. A new process instance must be created.

### 3.4 Process creation and termination

Process creation involves allocating identifiers, initializing execution state, establishing resource ownership, and preparing the process for scheduling.

The implementations validate memory requirements and reject requests that exceed available capacity.

Termination involves:

- Changing the process state.
- Terminating associated threads.
- Releasing allocated memory.
- Recording the exit status.
- Removing pending scheduling work.

The Python `ProcessManager`, JavaScript `Kernel`, C++ `ProcessManager`, and Java `ProcessService` implement these responsibilities.

## 4. Threads and Concurrency

### 4.1 Thread definition

A thread is an independently schedulable execution path within a process.

Threads belonging to the same process normally share:

- Code.
- Heap memory.
- Global variables.
- Process-level resources.
- Open file descriptors, subject to operating-system semantics.

Each thread maintains its own:

- Thread identifier.
- Program counter.
- CPU registers.
- Stack.
- Scheduling state.

A process can contain multiple threads executing different tasks.

Example:

    Database Process
         |
         +---- Query Execution Thread
         |
         +---- Cache Management Thread
         |
         +---- Logging Thread
         |
         +---- Network Thread

Threads improve concurrency and responsiveness without requiring a separate process address space for every execution path.

### 4.2 Concurrency and parallelism

These terms describe different execution properties.

| Concept | Meaning |
|---|---|
| Concurrency | Multiple tasks make progress during overlapping periods |
| Parallelism | Multiple tasks execute simultaneously |
| Multithreading | Multiple threads exist within a process |
| Multiprocessing | Multiple processes execute independently |
| Context switching | CPU execution changes from one task to another |

Concurrency can occur on a single CPU core through time slicing.

Parallelism requires multiple execution resources, such as multiple CPU cores.

### 4.3 Thread synchronization

Shared memory introduces synchronization problems.

Consider two threads incrementing a shared variable:

    counter = counter + 1

The operation consists conceptually of:

1. Reading the current value.
2. Adding one.
3. Writing the updated value.

Without synchronization, concurrent updates may overwrite each other.

This is a race condition.

A mutex protects a critical section by allowing only one participating thread to access the protected operation at a time.

The Python implementation uses `threading.Lock`.

The JavaScript implementation uses a promise-chain-based asynchronous mutex.

The C++ implementation focuses on process scheduling and resource ownership, while the Java implementation uses `ReentrantLock` and `ExecutorService` for actual concurrent execution.

### 4.4 Deadlocks

A deadlock occurs when two or more execution entities wait indefinitely for resources held by one another.

Four necessary conditions are commonly identified:

| Condition | Meaning |
|---|---|
| Mutual exclusion | A resource cannot be shared simultaneously |
| Hold and wait | A task holds one resource while waiting for another |
| No preemption | Resources cannot be forcibly taken away |
| Circular wait | Tasks form a circular dependency |

A system can reduce deadlock risk through:

- Consistent resource acquisition ordering.
- Resource-allocation policies.
- Deadlock detection.
- Timeout-based acquisition.
- Avoiding unnecessary resource retention.

The mutex examples demonstrate mutual exclusion but do not implement a complete deadlock detector.

## 5. CPU Scheduling

### 5.1 Scheduling objectives

CPU scheduling determines which ready thread receives processor time.

Important objectives include:

- High CPU utilization.
- High throughput.
- Low waiting time.
- Low turnaround time.
- Good response time.
- Fair allocation of processor resources.

### 5.2 Scheduling algorithms

| Algorithm | Operating principle | Main tradeoff |
|---|---|---|
| FCFS | First task to arrive executes first | Long tasks can delay short tasks |
| SJF | Shortest execution time is selected | Burst-time estimation is required |
| Priority | Highest-priority task executes first | Starvation can occur |
| Round Robin | Each task receives a fixed time quantum | Excessive switching can increase overhead |

### 5.3 Round-robin scheduling

Round Robin is a preemptive scheduling algorithm.

Each ready thread receives a fixed CPU time quantum.

If its remaining execution time exceeds the quantum, the thread returns to the end of the ready queue.

Example:

| Thread | Burst time |
|---|---:|
| T1 | 5 |
| T2 | 3 |
| T3 | 7 |

With a quantum of two time units:

| Execution | Duration |
|---|---:|
| T1 | 2 |
| T2 | 2 |
| T3 | 2 |
| T1 | 2 |
| T2 | 1 |
| T3 | 2 |
| T1 | 1 |
| T3 | 2 |
| T3 | 1 |

The scheduler maintains a queue of ready threads and records execution progress.

A very small quantum increases context-switching overhead. A very large quantum makes Round Robin behave more like FCFS.

The Python, C++, and Java implementations provide executable round-robin scheduling models.

The JavaScript implementation adds event-driven execution notifications.

### 5.4 Scheduling measurements

**Turnaround time**

    Turnaround Time = Completion Time - Arrival Time

**Waiting time**

    Waiting Time = Turnaround Time - CPU Burst Time

**Response time**

    Response Time = First CPU Start Time - Arrival Time

These measurements help evaluate scheduling policies.

The PostgreSQL `execution_slices` table records individual CPU execution intervals for reporting and comparison.

## 6. Memory Management

Memory management controls the allocation, protection, mapping, and reclamation of memory.

It allows multiple processes to use physical memory while maintaining separate address spaces.

### 6.1 Physical memory

Physical memory refers to actual RAM available to the processor.

The operating system tracks allocated and free memory regions.

A simplified memory layout may contain:

    Physical Memory
    +-------------------------+
    | Operating System        |
    +-------------------------+
    | Process A               |
    +-------------------------+
    | Process B               |
    +-------------------------+
    | Free Memory             |
    +-------------------------+
    | Process C               |
    +-------------------------+

### 6.2 Contiguous allocation

Contiguous allocation assigns each process a continuous memory region.

The implementations use first-fit allocation.

First-fit searches for the first available block large enough to satisfy a request.

Example:

| Block | Size | State |
|---|---:|---|
| A | 256 MB | Allocated |
| B | 384 MB | Allocated |
| C | 128 MB | Allocated |
| D | 256 MB | Free |

When an allocated block is released, adjacent free blocks can be combined.

This process is called coalescing.

### 6.3 Fragmentation

Memory fragmentation reduces the effectiveness of available memory.

**Internal fragmentation**

Occurs when an allocated block contains unused space.

**External fragmentation**

Occurs when free memory is divided into multiple non-contiguous regions.

A system may have sufficient total free memory but still fail a contiguous allocation request because no individual region is large enough.

The JavaScript, C++, and Java memory allocators demonstrate this condition and implement adjacent-block merging.

The Python implementation instead focuses on process-level memory accounting.

### 6.4 Virtual memory

Virtual memory provides each process with a logical address space that is mapped to physical memory.

A virtual address is translated through memory-management hardware and operating-system-maintained structures.

The principal concepts include:

- Virtual address.
- Physical address.
- Page.
- Page frame.
- Page table.
- Page fault.
- Translation Lookaside Buffer (TLB).
- Demand paging.

A virtual address is divided into a virtual page number and an offset.

The page number identifies a page, while the offset identifies a position within that page.

The page table maps virtual pages to physical frames.

### 6.5 Paging

Paging divides virtual address spaces into fixed-size pages and physical memory into equally sized frames.

Example:

    Virtual Address Space
    +---------+
    | Page 0  |
    +---------+
    | Page 1  |
    +---------+
    | Page 2  |
    +---------+
    | Page 3  |
    +---------+

    Physical Memory
    +-----------+
    | Frame 0   |
    +-----------+
    | Frame 1   |
    +-----------+
    | Frame 2   |
    +-----------+

Virtual pages do not need to occupy adjacent physical frames.

This reduces external fragmentation associated with contiguous allocation.

### 6.6 Page faults

A page fault occurs when a process references a virtual page that is not currently resident in the required physical-memory mapping.

A simplified demand-paging workflow is:

    Memory Reference
           |
           v
    Check Page Table
           |
           v
    Is Page Present?
       /       \
     Yes        No
      |          |
      v          v
    Access    Page Fault
    Memory       |
                 v
           Locate Page
                 |
                 v
           Obtain Frame
                 |
                 v
           Update Mapping
                 |
                 v
           Resume Execution

Actual operating systems also distinguish valid and invalid references, handle protection violations, and manage backing storage.

### 6.7 Page replacement

When physical frames are occupied, the operating system may need to replace an existing page.

| Algorithm | Replacement principle |
|---|---|
| FIFO | Replace the oldest loaded page |
| LRU | Replace the least recently used page |
| Optimal | Replace the page whose next use is farthest in the future |

The Python implementation uses LRU.

The JavaScript implementation uses FIFO.

The C++ implementation uses LRU.

The Java implementation also uses LRU.

These algorithms are educational approximations of page-replacement behavior.

The FIFO and LRU implementations maintain frame information and page lookup structures to identify hits and faults.

### 6.8 Page-fault rate

    Page Fault Rate = Page Faults / Total Page References

A lower page-fault rate can indicate better memory locality or a more suitable allocation of frames.

The PostgreSQL implementation stores page residency and page-access events separately, allowing fault-rate aggregation.

## 7. Filesystem Management

### 7.1 Filesystem definition

A filesystem organizes information into files and directories and provides mechanisms for storing, retrieving, and protecting data.

Common filesystem responsibilities include:

- File creation.
- File deletion.
- Reading and writing.
- Directory management.
- Metadata management.
- File ownership.
- Access permissions.
- Space allocation.
- Recovery and consistency.

### 7.2 Files and directories

A directory organizes filesystem entries.

A file stores data and associated metadata.

A hierarchical filesystem can be represented as:

    /
    |
    +-- home/
    |    |
    |    +-- user/
    |         |
    |         +-- document.txt
    |
    +-- var/
    |    |
    |    +-- log/
    |         |
    |         +-- system.log
    |
    +-- etc/
         |
         +-- application.conf

Absolute paths begin at the filesystem root.

Relative paths are interpreted in relation to a current working directory.

The implementations use absolute-path validation and reject parent-directory traversal.

### 7.3 File metadata and inodes

Unix-like filesystems commonly use inode-based metadata structures.

An inode can contain:

- File type.
- Ownership.
- Permissions.
- File size.
- Timestamps.
- Data-block references.
- Link count.

The directory maps filenames to filesystem objects.

The PostgreSQL model represents files with identifiers, inode numbers, ownership, size, and timestamps.

It separates directories from file records.

### 7.4 File permissions

Access-control systems determine which users can perform operations on files.

The model uses three principal permissions:

| Permission | Meaning |
|---|---|
| Read | Retrieve file contents |
| Write | Modify file contents |
| Delete | Remove the file |

A typical ownership arrangement is:

- Administrator: full access.
- Operator: permitted operational access.
- Auditor: read-only access.
- Application user: access limited by assigned permissions.

The Python, JavaScript, C++, and Java implementations enforce access checks before file operations.

The PostgreSQL implementation stores delegated permissions in `file_permissions` and records access events in `filesystem_audit`.

### 7.5 Filesystem security

Important filesystem security risks include:

- Unauthorized file access.
- Path traversal.
- Incorrect ownership.
- Excessive privileges.
- Accidental deletion.
- Unauthorized modification.
- Insecure file handling.

Path traversal occurs when an application accepts a path containing parent-directory references to access an unintended location.

The implementations reject paths containing `..`.

A production filesystem must also defend against symbolic-link attacks, race conditions between path validation and file access, unsafe mount configurations, and permission inconsistencies.

String validation alone is not sufficient for production filesystem security.

## 8. Implementation Architecture

Each language implements the same operating-system concepts using different engineering approaches.

| Deliverable | Main implementation |
|---|---|
| Python | Object-oriented operating-system simulator |
| JavaScript | Asynchronous event-driven kernel model |
| C++17 | STL-based resource and scheduling engine |
| Java 17 | Enterprise-oriented process and resource services |
| PostgreSQL | Relational operating-system resource model |

### 8.1 Python

The Python implementation uses dataclasses and enums for explicit process, thread, and memory states.

Its major components are:

| Component | Responsibility |
|---|---|
| `ProcessManager` | Process creation and termination |
| `RoundRobinScheduler` | CPU time-slice allocation |
| `ThreadSafeCounter` | Mutual exclusion |
| `VirtualMemory` | LRU page replacement |
| `VirtualFileSystem` | File operations and permissions |

The implementation uses dictionaries for process and page lookup.

The scheduler uses a deque to maintain ready-thread ordering.

The filesystem uses normalized absolute paths and explicit access checks.

The script uses standard-library components and does not require external packages.

### 8.2 JavaScript

The JavaScript implementation models resource management through asynchronous operations and events.

Its components include:

| Component | Responsibility |
|---|---|
| `Kernel` | Process registry and scheduling |
| `AsyncMutex` | Promise-based critical-section protection |
| `SharedCounter` | Synchronized shared state |
| `PhysicalMemory` | First-fit allocation |
| `PageTable` | FIFO page replacement |
| `VirtualFileSystem` | Permission-controlled file operations |

The `EventEmitter` mechanism publishes process creation, CPU execution, thread completion, and termination events.

Promises and `setImmediate` demonstrate asynchronous scheduling behavior.

The memory allocator uses contiguous blocks and merges adjacent free regions.

The implementation requires Node.js 18 or later.

### 8.3 C++17

The C++ implementation emphasizes explicit domain structures and resource ownership.

Its major components include:

- `ProcessManager`
- `Scheduler`
- `MemoryAllocator`
- `VirtualMemory`
- `FileSystem`

The program uses:

- `unordered_map` for process lookup.
- `deque` for ready queues.
- `vector` for threads and memory blocks.
- `optional` for free-memory ownership.
- STL algorithms for searching and selecting resources.
- Exceptions for invalid operations.

The memory allocator performs first-fit selection and free-block coalescing.

The virtual-memory component maintains an LRU timestamp for each resident page.

The filesystem uses ownership and explicit access permissions.

The implementation is compiled with C++17 and has no external library dependency.

### 8.4 Java 17

The Java implementation uses domain-oriented service classes.

Its components include:

| Component | Responsibility |
|---|---|
| `ProcessService` | Process registry and resource accounting |
| `OSProcess` | Process state and thread ownership |
| `OSThread` | Thread execution state |
| `Scheduler` | CPU execution slices |
| `SharedCounter` | Lock-based synchronization |
| `MemoryAllocator` | Physical memory management |
| `VirtualMemory` | LRU page replacement |
| `FileSystem` | File access and ownership |

Records provide immutable representations of process snapshots, memory blocks, and execution slices.

Enums represent lifecycle states and permissions.

`ConcurrentHashMap` supports concurrent process lookup.

`AtomicInteger` generates identifiers.

`ExecutorService` runs concurrent tasks.

`ReentrantLock` protects shared counter updates.

The design separates domain state from process-management and scheduling services.

### 8.5 PostgreSQL

The SQL implementation models operating-system resources through relational entities.

The main tables are:

| Table | Purpose |
|---|---|
| `operating_systems` | System configuration |
| `users` | System identities and roles |
| `processes` | Process lifecycle and memory requirements |
| `threads` | Thread execution state |
| `scheduling_runs` | Scheduler executions |
| `execution_slices` | CPU time-slice history |
| `memory_allocations` | Physical memory ownership |
| `virtual_pages` | Virtual-to-physical mappings |
| `page_accesses` | Page access and fault history |
| `directories` | Filesystem directory hierarchy |
| `files` | File metadata and content |
| `file_permissions` | Delegated file access |
| `filesystem_audit` | Filesystem activity history |

The schema uses primary keys, foreign keys, unique constraints, check constraints, indexes, views, functions, procedures, and triggers.

The `process_resource_report` view aggregates process and thread information.

The `memory_utilization` view reports active memory allocations.

The `scheduling_report` view summarizes CPU execution.

The `record_page_access` function records page references and faults.

The `allocate_memory` and `release_memory` procedures manage allocation records.

The `terminate_process` procedure terminates associated threads and releases allocated memory.

The `check_process_eligibility` function evaluates whether a process has active execution threads.

The SQL implementation uses transactions to keep related resource updates consistent.

## 9. Important Technical Distinctions

The four major operating-system subsystems have different responsibilities.

| Area | Primary responsibility | Main resource |
|---|---|---|
| Process management | Manage independent execution environments | Process resources |
| Thread management | Manage execution paths within processes | CPU execution |
| Memory management | Allocate and protect address spaces | RAM and virtual memory |
| Filesystem management | Organize persistent information | Files and storage |

Several additional distinctions are important.

**Process versus thread**

A process provides an execution environment and resource ownership boundary. A thread provides an execution path within that environment.

**Concurrency versus parallelism**

Concurrency concerns overlapping task progress. Parallelism means simultaneous execution.

**Physical versus virtual memory**

Physical memory refers to actual RAM. Virtual memory provides logical address spaces mapped onto physical resources.

**Paging versus segmentation**

Paging divides memory into fixed-size units. Segmentation divides memory into logically variable-sized regions.

**Page fault versus segmentation fault**

A page fault is a memory-management event that may be resolved by loading a page or handling a protection condition. A segmentation fault generally indicates an invalid or prohibited memory access.

**File versus directory**

A file stores data and metadata. A directory organizes filesystem entries.

**Scheduling versus synchronization**

Scheduling determines which execution entity receives CPU time. Synchronization coordinates access to shared resources.

## 10. Failure Conditions and Edge Cases

The implementations explicitly handle several operational failures.

| Failure | Expected behavior |
|---|---|
| Invalid process memory | Reject creation |
| Insufficient memory | Raise a resource exception |
| Unknown PID | Reject the operation |
| Repeated termination | Reject invalid state transition |
| Invalid thread burst time | Reject thread creation |
| Zero scheduling quantum | Reject scheduler configuration |
| Negative page number | Reject memory reference |
| Page replacement | Evict a resident page |
| Duplicate file | Reject file creation |
| Unauthorized file write | Deny access |
| Parent-directory traversal | Reject the path |
| Missing allocation | Reject memory release |
| Free-memory fragmentation | Reject an unsatisfied contiguous allocation |
| Concurrent counter updates | Protect the critical section |

Some implementation limitations remain important:

- The CPU schedulers simulate execution rather than switching real hardware contexts.
- The asynchronous JavaScript scheduler is an event-loop simulation.
- The page-replacement models do not implement a complete hardware memory-management unit.
- The memory allocators do not provide real physical addresses.
- The virtual filesystems store data in process memory.
- The PostgreSQL database represents resource history rather than controlling a real kernel.

The PostgreSQL model also uses simplified allocation-address assignment. Its allocation procedure does not perform physical compaction or implement a complete first-fit free-region allocator.

## 11. Performance and Complexity

The following estimates describe the main data-structure operations in the educational implementations.

| Operation | Typical complexity |
|---|---|
| Process lookup using hash maps | O(1) average |
| Process lookup using ordered maps | O(log n) |
| Ready-queue insertion | O(1) |
| Ready-queue removal | O(1) |
| Round-robin execution | O(k), excluding application work |
| LRU victim selection by scanning frames | O(f) |
| LRU lookup using hash maps | O(1) average |
| FIFO page lookup using a hash set | O(1) average |
| First-fit allocation | O(b) |
| Memory-block coalescing | O(b) |
| Filesystem lookup using hash maps | O(1) average |
| Filesystem lookup using ordered maps | O(log n) |

Where:

- `n` is the number of processes.
- `k` is the number of scheduling slices.
- `f` is the number of physical frames.
- `b` is the number of memory blocks.

A production scheduler may require priority queues, multiple ready queues, CPU affinity, preemption controls, and workload-aware policies.

A production memory manager requires additional mechanisms such as TLB management, page-table hierarchies, protection bits, page-cache integration, and memory reclamation.

A production filesystem requires persistent metadata, block allocation, journaling or another consistency mechanism, recovery handling, and concurrency control.

## 12. Security and Reliability Considerations

Operating-system resource management is closely related to system security.

Important controls include:

- Process isolation.
- User and group ownership.
- Memory protection.
- Privilege separation.
- Filesystem permissions.
- Resource limits.
- Input validation.
- Audit logging.
- Safe process termination.
- Controlled access to shared resources.

A process should not be able to read or modify another process's protected memory without authorization.

A user should not gain access to files merely by constructing a different pathname.

A resource manager should prevent memory accounting from becoming inconsistent during concurrent allocation and release operations.

A scheduler should not execute terminated threads.

A filesystem should not permit unauthorized modifications or deletions.

The implementations demonstrate simplified versions of these controls. Actual operating systems enforce security through hardware privilege levels, system calls, virtual-memory protection, credentials, access-control mechanisms, and kernel-level validation.

## 13. Execution Requirements

| Deliverable | Runtime | Execution |
|---|---|---|
| Python | Python 3.10+ | `python operating_systems.py` |
| JavaScript | Node.js 18+ | `node operating_systems.js` |
| C++17 | C++17 compiler | `g++ -std=c++17 -O2 -Wall -Wextra -pedantic operating_systems.cpp -o os_sim` |
| Java | Java 17 | `javac OperatingSystems.java` followed by `java OperatingSystems` |
| PostgreSQL | PostgreSQL 14+ | Execute the SQL script using `psql` |

The Python, JavaScript, C++, and Java implementations use standard language facilities without third-party dependencies.

The PostgreSQL script creates its own `os_lab` schema and populates it with representative operating-system resource records.

## 14. Practical Applications

The concepts implemented in this project apply to:

- Server operating systems.
- Database execution environments.
- Web-server process management.
- Multithreaded applications.
- Container resource allocation.
- Virtual machines.
- Memory-intensive applications.
- File servers.
- Access-control systems.
- Performance monitoring.
- Resource accounting.
- Operating-system diagnostics.

The relationship between these subsystems is fundamental: processes own execution resources, threads provide concurrent execution, memory management supplies protected address spaces, and filesystems provide persistent data organization.
