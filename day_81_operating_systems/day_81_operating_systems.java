import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.locks.ReentrantLock;
import java.util.stream.Collectors;

/*
 * Operating Systems: Enterprise Resource Management Model.
 *
 * Java 17 implementation featuring:
 * - Immutable records for resource and execution results.
 * - Explicit process and thread state transitions.
 * - Enterprise process registry.
 * - Round-robin scheduling service.
 * - Thread synchronization.
 * - Physical memory allocation.
 * - Virtual memory and LRU page replacement.
 * - Filesystem access-control policies.
 * - Resource accounting and validation.
 *
 * Compile:
 * javac OperatingSystems.java
 *
 * Run:
 * java OperatingSystems
 */

public class OperatingSystems {

    enum ProcessState {
        NEW, READY, RUNNING, BLOCKED, TERMINATED
    }

    enum ThreadState {
        READY, RUNNING, BLOCKED, TERMINATED
    }

    enum Access {
        READ, WRITE, DELETE
    }

    static class ResourceException extends RuntimeException {
        ResourceException(String message) {
            super(message);
        }
    }

    static class InvalidStateException extends RuntimeException {
        InvalidStateException(String message) {
            super(message);
        }
    }

    static class AccessDeniedException extends RuntimeException {
        AccessDeniedException(String message) {
            super(message);
        }
    }

    record ProcessSnapshot(
        int pid,
        String name,
        ProcessState state,
        long memory,
        int threadCount,
        long cpuTime
    ) {}

    record ExecutionSlice(
        int pid,
        int tid,
        int duration,
        int remainingTime,
        long clock
    ) {}

    static final class OSProcess {
        private final int pid;
        private final String name;
        private final long memory;
        private final Map<Integer, OSThread> threads =
            new LinkedHashMap<>();

        private ProcessState state = ProcessState.READY;
        private long cpuTime;

        OSProcess(int pid, String name, long memory) {
            this.pid = pid;
            this.name = name;
            this.memory = memory;
        }

        int pid() {
            return pid;
        }

        String name() {
            return name;
        }

        long memory() {
            return memory;
        }

        ProcessState state() {
            return state;
        }

        Collection<OSThread> threads() {
            return Collections.unmodifiableCollection(
                threads.values()
            );
        }

        void addThread(OSThread thread) {
            if (state == ProcessState.TERMINATED) {
                throw new InvalidStateException(
                    "Cannot modify a terminated process"
                );
            }

            threads.put(thread.tid(), thread);
        }

        void execute(int duration) {
            if (state == ProcessState.TERMINATED) {
                throw new InvalidStateException(
                    "Terminated process cannot execute"
                );
            }

            state = ProcessState.RUNNING;
            cpuTime += duration;
        }

        void terminate() {
            if (state == ProcessState.TERMINATED) {
                throw new InvalidStateException(
                    "Process already terminated"
                );
            }

            state = ProcessState.TERMINATED;

            threads.values().forEach(OSThread::terminate);
        }

        ProcessSnapshot snapshot() {
            return new ProcessSnapshot(
                pid,
                name,
                state,
                state == ProcessState.TERMINATED ? 0 : memory,
                threads.size(),
                cpuTime
            );
        }
    }

    static final class OSThread {
        private final int tid;
        private final String name;
        private final int burstTime;

        private int remainingTime;
        private long cpuTime;
        private ThreadState state = ThreadState.READY;

        OSThread(int tid, String name, int burstTime) {
            if (name == null || name.isBlank() || burstTime <= 0) {
                throw new IllegalArgumentException(
                    "Invalid thread configuration"
                );
            }

            this.tid = tid;
            this.name = name;
            this.burstTime = burstTime;
            this.remainingTime = burstTime;
        }

        int tid() {
            return tid;
        }

        String name() {
            return name;
        }

        int remainingTime() {
            return remainingTime;
        }

        ThreadState state() {
            return state;
        }

        void execute(int duration) {
            if (state == ThreadState.TERMINATED ||
                state == ThreadState.BLOCKED) {
                throw new InvalidStateException(
                    "Thread is not executable"
                );
            }

            if (duration <= 0 || duration > remainingTime) {
                throw new IllegalArgumentException(
                    "Invalid execution duration"
                );
            }

            state = ThreadState.RUNNING;
            remainingTime -= duration;
            cpuTime += duration;

            if (remainingTime == 0) {
                state = ThreadState.TERMINATED;
            } else {
                state = ThreadState.READY;
            }
        }

        void terminate() {
            state = ThreadState.TERMINATED;
            remainingTime = 0;
        }
    }

    static final class ProcessService {
        private final long memoryCapacity;
        private long allocatedMemory;

        private final AtomicInteger pidSequence =
            new AtomicInteger(1000);

        private final AtomicInteger tidSequence =
            new AtomicInteger(1);

        private final Map<Integer, OSProcess> registry =
            new ConcurrentHashMap<>();

        ProcessService(long memoryCapacity) {
            if (memoryCapacity <= 0) {
                throw new IllegalArgumentException(
                    "Memory capacity must be positive"
                );
            }

            this.memoryCapacity = memoryCapacity;
        }

        public synchronized OSProcess createProcess(
            String name,
            long memory
        ) {
            if (name == null || name.isBlank() || memory <= 0) {
                throw new IllegalArgumentException(
                    "Invalid process configuration"
                );
            }

            if (memory > memoryCapacity - allocatedMemory) {
                throw new ResourceException(
                    "Insufficient memory"
                );
            }

            OSProcess process = new OSProcess(
                pidSequence.getAndIncrement(),
                name,
                memory
            );

            registry.put(process.pid(), process);
            allocatedMemory += memory;

            return process;
        }

        public OSThread createThread(
            int pid,
            String name,
            int burstTime
        ) {
            OSProcess process = getProcess(pid);

            OSThread thread = new OSThread(
                tidSequence.getAndIncrement(),
                name,
                burstTime
            );

            process.addThread(thread);
            return thread;
        }

        public OSProcess getProcess(int pid) {
            OSProcess process = registry.get(pid);

            if (process == null) {
                throw new ResourceException(
                    "Unknown process: " + pid
                );
            }

            return process;
        }

        public synchronized void terminate(int pid) {
            OSProcess process = getProcess(pid);

            process.terminate();
            allocatedMemory -= process.memory();
        }

        public synchronized long availableMemory() {
            return memoryCapacity - allocatedMemory;
        }

        public List<ProcessSnapshot> report() {
            return registry.values()
                .stream()
                .map(OSProcess::snapshot)
                .sorted(Comparator.comparingInt(ProcessSnapshot::pid))
                .collect(Collectors.toList());
        }
    }

    static final class Scheduler {
        private final int quantum;
        private long clock;

        private final Queue<OSProcess> readyProcesses =
            new ArrayDeque<>();

        Scheduler(int quantum) {
            if (quantum <= 0) {
                throw new IllegalArgumentException(
                    "Quantum must be positive"
                );
            }

            this.quantum = quantum;
        }

        void submit(OSProcess process) {
            if (process.state() == ProcessState.TERMINATED) {
                throw new InvalidStateException(
                    "Cannot schedule terminated process"
                );
            }

            readyProcesses.add(process);
        }

        List<ExecutionSlice> run() {
            List<ExecutionSlice> history = new ArrayList<>();

            while (!readyProcesses.isEmpty()) {
                OSProcess process = readyProcesses.poll();

                for (OSThread thread : process.threads()) {
                    if (thread.state() != ThreadState.READY) {
                        continue;
                    }

                    int duration = Math.min(
                        quantum,
                        thread.remainingTime()
                    );

                    thread.execute(duration);
                    process.execute(duration);
                    clock += duration;

                    history.add(new ExecutionSlice(
                        process.pid(),
                        thread.tid(),
                        duration,
                        thread.remainingTime(),
                        clock
                    ));
                }
            }

            return Collections.unmodifiableList(history);
        }
    }

    /*
     * Thread-safe shared counter.
     * ReentrantLock protects compound read-modify-write operations.
     */
    static final class SharedCounter {
        private final ReentrantLock lock = new ReentrantLock();
        private long value;

        void increment(int count) {
            if (count < 0) {
                throw new IllegalArgumentException(
                    "Negative increment count"
                );
            }

            for (int i = 0; i < count; i++) {
                lock.lock();

                try {
                    value++;
                } finally {
                    lock.unlock();
                }
            }
        }

        long getValue() {
            lock.lock();

            try {
                return value;
            } finally {
                lock.unlock();
            }
        }
    }

    record MemoryBlock(
        long start,
        long size,
        Integer ownerPid
    ) {}

    static final class MemoryAllocator {
        private final long capacity;
        private final List<MemoryBlock> blocks =
            new ArrayList<>();

        MemoryAllocator(long capacity) {
            if (capacity <= 0) {
                throw new IllegalArgumentException(
                    "Invalid memory capacity"
                );
            }

            this.capacity = capacity;
            blocks.add(new MemoryBlock(0, capacity, null));
        }

        synchronized long allocate(int pid, long size) {
            if (pid <= 0 || size <= 0) {
                throw new IllegalArgumentException(
                    "Invalid allocation request"
                );
            }

            if (blocks.stream().anyMatch(
                b -> Objects.equals(b.ownerPid(), pid)
            )) {
                throw new ResourceException(
                    "PID already owns a block"
                );
            }

            for (int i = 0; i < blocks.size(); i++) {
                MemoryBlock block = blocks.get(i);

                if (block.ownerPid() == null &&
                    block.size() >= size) {

                    long address = block.start();

                    blocks.set(
                        i,
                        new MemoryBlock(address, size, pid)
                    );

                    long remainder = block.size() - size;

                    if (remainder > 0) {
                        blocks.add(
                            i + 1,
                            new MemoryBlock(
                                address + size,
                                remainder,
                                null
                            )
                        );
                    }

                    return address;
                }
            }

            throw new ResourceException(
                "No contiguous free block available"
            );
        }

        synchronized void release(int pid) {
            boolean found = false;

            for (int i = 0; i < blocks.size(); i++) {
                MemoryBlock block = blocks.get(i);

                if (Objects.equals(block.ownerPid(), pid)) {
                    blocks.set(
                        i,
                        new MemoryBlock(
                            block.start(),
                            block.size(),
                            null
                        )
                    );

                    found = true;
                    break;
                }
            }

            if (!found) {
                throw new ResourceException(
                    "Allocation not found"
                );
            }

            List<MemoryBlock> merged = new ArrayList<>();

            for (MemoryBlock block : blocks) {
                if (!merged.isEmpty()) {
                    MemoryBlock previous =
                        merged.get(merged.size() - 1);

                    if (previous.ownerPid() == null &&
                        block.ownerPid() == null) {

                        merged.set(
                            merged.size() - 1,
                            new MemoryBlock(
                                previous.start(),
                                previous.size() + block.size(),
                                null
                            )
                        );

                        continue;
                    }
                }

                merged.add(block);
            }

            blocks.clear();
            blocks.addAll(merged);
        }

        synchronized List<MemoryBlock> snapshot() {
            return List.copyOf(blocks);
        }

        long capacity() {
            return capacity;
        }
    }

    static final class VirtualMemory {
        private record Frame(int page, long lastUsed) {}

        private final int frameCount;
        private final Map<Integer, Integer> pageTable =
            new HashMap<>();

        private final Map<Integer, Long> usage =
            new HashMap<>();

        private final List<Integer> frames =
            new ArrayList<>();

        private long clock;
        private int hits;
        private int faults;

        VirtualMemory(int frameCount) {
            if (frameCount <= 0) {
                throw new IllegalArgumentException(
                    "Frame count must be positive"
                );
            }

            this.frameCount = frameCount;
        }

        synchronized String access(int page) {
            if (page < 0) {
                throw new IllegalArgumentException(
                    "Invalid page number"
                );
            }

            clock++;

            if (pageTable.containsKey(page)) {
                hits++;
                usage.put(page, clock);

                return "HIT page=" + page;
            }

            faults++;

            if (frames.size() < frameCount) {
                frames.add(page);
            } else {
                int victim = frames.stream()
                    .min(Comparator.comparingLong(
                        p -> usage.get(p)
                    ))
                    .orElseThrow();

                frames.set(frames.indexOf(victim), page);
                pageTable.remove(victim);
                usage.remove(victim);
            }

            int frame = frames.indexOf(page);

            pageTable.put(page, frame);
            usage.put(page, clock);

            return "FAULT page=" + page + " frame=" + frame;
        }

        synchronized void report() {
            int total = hits + faults;

            System.out.println("Frames: " + frames);
            System.out.println("Hits: " + hits);
            System.out.println("Faults: " + faults);

            System.out.printf(
                "Hit ratio: %.2f%%%n",
                total == 0 ? 0 : 100.0 * hits / total
            );
        }
    }

    static final class VirtualFile {
        private final String owner;
        private String content;

        private final Map<String, Set<Access>> permissions =
            new HashMap<>();

        VirtualFile(
            String owner,
            String content,
            Map<String, Set<Access>> permissions
        ) {
            this.owner = owner;
            this.content = content;

            permissions.forEach((user, actions) ->
                this.permissions.put(
                    user,
                    EnumSet.copyOf(actions)
                )
            );
        }
    }

    static final class FileSystem {
        private final Map<String, VirtualFile> files =
            new HashMap<>();

        private String validatePath(String input) {
            if (input == null ||
                !input.startsWith("/") ||
                input.indexOf('\0') >= 0) {
                throw new IllegalArgumentException(
                    "Invalid absolute path"
                );
            }

            String[] segments = input.split("/");

            for (String segment : segments) {
                if (segment.equals("..")) {
                    throw new AccessDeniedException(
                        "Path traversal is prohibited"
                    );
                }
            }

            String normalized = input.replaceAll("/+", "/");

            if (normalized.equals("/")) {
                throw new IllegalArgumentException(
                    "Root is not a file"
                );
            }

            return normalized;
        }

        void create(
            String inputPath,
            String owner,
            String content,
            Map<String, Set<Access>> permissions
        ) {
            String filePath = validatePath(inputPath);

            if (owner == null || owner.isBlank()) {
                throw new IllegalArgumentException(
                    "Owner is required"
                );
            }

            if (files.containsKey(filePath)) {
                throw new ResourceException(
                    "File already exists"
                );
            }

            Map<String, Set<Access>> access =
                new HashMap<>(permissions);

            access.put(
                owner,
                EnumSet.allOf(Access.class)
            );

            files.put(
                filePath,
                new VirtualFile(owner, content, access)
            );
        }

        private VirtualFile authorize(
            String inputPath,
            String user,
            Access action
        ) {
            String filePath = validatePath(inputPath);
            VirtualFile file = files.get(filePath);

            if (file == null) {
                throw new ResourceException("File not found");
            }

            if (!file.permissions
                .getOrDefault(user, Set.of())
                .contains(action)) {

                throw new AccessDeniedException(
                    "Access denied: " + action
                );
            }

            return file;
        }

        String read(String filePath, String user) {
            return authorize(
                filePath,
                user,
                Access.READ
            ).content;
        }

        void write(
            String filePath,
            String user,
            String content
        ) {
            authorize(
                filePath,
                user,
                Access.WRITE
            ).content = content;
        }

        void delete(String filePath, String user) {
            String normalized = validatePath(filePath);

            authorize(
                normalized,
                user,
                Access.DELETE
            );

            files.remove(normalized);
        }

        int fileCount() {
            return files.size();
        }
    }

    public static void main(String[] args)
        throws InterruptedException, ExecutionException {

        System.out.println("OPERATING SYSTEM ENTERPRISE SIMULATOR");

        // Process lifecycle.
        ProcessService processService =
            new ProcessService(4096);

        OSProcess application =
            processService.createProcess("PaymentService", 1024);

        OSProcess database =
            processService.createProcess("TransactionDB", 2048);

        processService.createThread(
            application.pid(),
            "RequestHandler",
            8
        );

        processService.createThread(
            application.pid(),
            "AuditLogger",
            4
        );

        processService.createThread(
            database.pid(),
            "QueryExecutor",
            6
        );

        processService.createThread(
            database.pid(),
            "CacheManager",
            3
        );

        System.out.println("\nPROCESS REGISTRY");
        processService.report().forEach(System.out::println);

        // CPU scheduling.
        Scheduler scheduler = new Scheduler(3);

        scheduler.submit(application);
        scheduler.submit(database);

        System.out.println("\nSCHEDULER EXECUTION");

        scheduler.run().forEach(System.out::println);

        // Concurrent execution.
        System.out.println("\nTHREAD SYNCHRONIZATION");

        SharedCounter counter = new SharedCounter();

        ExecutorService executor =
            Executors.newFixedThreadPool(4);

        List<Future<?>> futures = new ArrayList<>();

        for (int i = 0; i < 4; i++) {
            futures.add(
                executor.submit(() -> counter.increment(10000))
            );
        }

        for (Future<?> future : futures) {
            future.get();
        }

        executor.shutdown();

        if (!executor.awaitTermination(
            10,
            TimeUnit.SECONDS
        )) {
            executor.shutdownNow();
            throw new ResourceException(
                "Worker shutdown timed out"
            );
        }

        System.out.println(
            "Synchronized counter: " + counter.getValue()
        );

        // Physical memory.
        System.out.println("\nPHYSICAL MEMORY MANAGEMENT");

        MemoryAllocator allocator =
            new MemoryAllocator(2048);

        allocator.allocate(1001, 512);
        allocator.allocate(1002, 768);
        allocator.allocate(1003, 256);

        allocator.snapshot().forEach(System.out::println);

        allocator.release(1002);

        System.out.println("After releasing PID 1002:");

        allocator.snapshot().forEach(System.out::println);

        // Virtual memory.
        System.out.println("\nVIRTUAL MEMORY MANAGEMENT");

        VirtualMemory virtualMemory = new VirtualMemory(3);

        for (int page : new int[]{1, 2, 3, 1, 4, 2, 5}) {
            System.out.println(virtualMemory.access(page));
        }

        virtualMemory.report();

        // Filesystem.
        System.out.println("\nFILESYSTEM MANAGEMENT");

        FileSystem fileSystem = new FileSystem();

        fileSystem.create(
            "/srv/application/config.txt",
            "administrator",
            "mode=production",
            Map.of(
                "auditor",
                EnumSet.of(Access.READ)
            )
        );

        System.out.println(
            fileSystem.read(
                "/srv/application/config.txt",
                "auditor"
            )
        );

        try {
            fileSystem.write(
                "/srv/application/config.txt",
                "auditor",
                "mode=unsafe"
            );
        } catch (AccessDeniedException error) {
            System.out.println(
                "SECURITY CONTROL: " + error.getMessage()
            );
        }

        // Release process resources.
        processService.terminate(application.pid());
        processService.terminate(database.pid());

        System.out.println("\nFINAL PROCESS REPORT");

        processService.report().forEach(System.out::println);

        System.out.println(
            "Available kernel memory: " +
            processService.availableMemory()
        );

        System.out.println(
            "Stored files: " + fileSystem.fileCount()
        );

        System.out.println("\nSIMULATION COMPLETED");
    }
}
