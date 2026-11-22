import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.Callable;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionException;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.FutureTask;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.LongAdder;
import java.util.concurrent.locks.ReentrantLock;
import java.util.function.Function;

/*
 * Parallelism: Multithreading and Multiprocessing
 *
 * Java 17 enterprise-oriented implementation.
 *
 * Demonstrates:
 * - ExecutorService lifecycle management
 * - Fixed thread pools
 * - Callable and Future
 * - CompletableFuture pipelines
 * - ForkJoinPool parallel computation
 * - Concurrent collections
 * - Atomic and lock-based synchronization
 * - Bounded producer-consumer processing
 * - Exception handling and task isolation
 *
 * Compile:
 * javac ParallelismLab.java
 *
 * Run:
 * java ParallelismLab
 */

public class ParallelismLab {

    private static final int MAX_TASKS = 100;
    private static final int MAX_LIMIT = 10_000_000;

    // --------------------------------------------------
    // 1. Domain types
    // --------------------------------------------------

    enum ExecutionStatus {
        PENDING,
        RUNNING,
        COMPLETED,
        FAILED,
        CANCELLED
    }

    enum WorkloadType {
        CPU_BOUND,
        IO_BOUND
    }

    record Task(int id, int limit) {

        Task {
            if (id < 0) {
                throw new IllegalArgumentException(
                    "Task ID cannot be negative."
                );
            }

            if (limit < 0 || limit > MAX_LIMIT) {
                throw new IllegalArgumentException(
                    "Task limit is outside the permitted range."
                );
            }
        }
    }

    record TaskResult(
        int taskId,
        long primeCount,
        String workerName
    ) {}

    record ExecutionReport(
        String executionMode,
        List<TaskResult> results,
        long elapsedMilliseconds,
        int failedTasks
    ) {
        ExecutionReport {
            results = List.copyOf(results);
        }
    }

    // --------------------------------------------------
    // 2. Business exceptions
    // --------------------------------------------------

    static class TaskExecutionException extends RuntimeException {
        TaskExecutionException(String message, Throwable cause) {
            super(message, cause);
        }
    }

    // --------------------------------------------------
    // 3. CPU-bound computation
    // --------------------------------------------------

    static boolean isPrime(int number) {
        if (number < 2) {
            return false;
        }

        if (number <= 3) {
            return true;
        }

        if (number % 2 == 0 || number % 3 == 0) {
            return false;
        }

        for (
            int divisor = 5;
            (long) divisor * divisor <= number;
            divisor += 6
        ) {
            if (
                number % divisor == 0 ||
                number % (divisor + 2) == 0
            ) {
                return false;
            }
        }

        return true;
    }

    static long countPrimes(int limit) {
        long count = 0;

        for (int number = 2; number <= limit; number++) {
            if (isPrime(number)) {
                count++;
            }
        }

        return count;
    }

    static TaskResult executeTask(Task task) {
        Objects.requireNonNull(task);

        return new TaskResult(
            task.id(),
            countPrimes(task.limit()),
            Thread.currentThread().getName()
        );
    }

    // --------------------------------------------------
    // 4. Thread factory
    // --------------------------------------------------

    static ThreadFactory namedThreadFactory(String prefix) {
        AtomicInteger sequence = new AtomicInteger(1);

        return runnable -> {
            Thread thread = new Thread(
                runnable,
                prefix + "-" + sequence.getAndIncrement()
            );

            // Non-daemon workers ensure explicit lifecycle management.
            thread.setDaemon(false);

            return thread;
        };
    }

    // --------------------------------------------------
    // 5. Sequential execution
    // --------------------------------------------------

    static ExecutionReport executeSequential(
        List<Task> tasks
    ) {
        long start = System.nanoTime();

        List<TaskResult> results = new ArrayList<>();
        int failures = 0;

        for (Task task : tasks) {
            try {
                results.add(executeTask(task));
            } catch (RuntimeException error) {
                failures++;
                System.err.println(
                    "Task " + task.id() + " failed: " +
                    error.getMessage()
                );
            }
        }

        long elapsed =
            TimeUnit.NANOSECONDS.toMillis(
                System.nanoTime() - start
            );

        return new ExecutionReport(
            "Sequential",
            results,
            elapsed,
            failures
        );
    }

    // --------------------------------------------------
    // 6. ExecutorService processing
    // --------------------------------------------------

    static ExecutionReport executeWithExecutor(
        List<Task> tasks,
        int workerCount
    ) {
        if (workerCount < 1) {
            throw new IllegalArgumentException(
                "Worker count must be positive."
            );
        }

        long start = System.nanoTime();

        ExecutorService executor =
            Executors.newFixedThreadPool(
                workerCount,
                namedThreadFactory("compute-worker")
            );

        List<Future<TaskResult>> futures = new ArrayList<>();

        List<TaskResult> results = new ArrayList<>();

        int failures = 0;

        try {
            for (Task task : tasks) {
                futures.add(
                    executor.submit(() -> executeTask(task))
                );
            }

            for (Future<TaskResult> future : futures) {
                try {
                    results.add(future.get());

                } catch (ExecutionException error) {
                    failures++;

                    System.err.println(
                        "Execution failure: " +
                        error.getCause().getMessage()
                    );

                } catch (InterruptedException error) {
                    Thread.currentThread().interrupt();

                    throw new TaskExecutionException(
                        "Execution interrupted.",
                        error
                    );
                }
            }

        } finally {
            executor.shutdown();

            try {
                if (!executor.awaitTermination(
                    30,
                    TimeUnit.SECONDS
                )) {
                    executor.shutdownNow();
                }

            } catch (InterruptedException error) {
                executor.shutdownNow();
                Thread.currentThread().interrupt();
            }
        }

        results.sort(
            Comparator.comparingInt(TaskResult::taskId)
        );

        long elapsed =
            TimeUnit.NANOSECONDS.toMillis(
                System.nanoTime() - start
            );

        return new ExecutionReport(
            "ExecutorService",
            results,
            elapsed,
            failures
        );
    }

    // --------------------------------------------------
    // 7. CompletableFuture pipeline
    // --------------------------------------------------

    static List<TaskResult> executeWithCompletableFuture(
        List<Task> tasks,
        int workerCount
    ) {
        ExecutorService executor =
            Executors.newFixedThreadPool(
                workerCount,
                namedThreadFactory("async-worker")
            );

        try {
            List<CompletableFuture<TaskResult>> futures =
                tasks.stream()
                    .map(task ->
                        CompletableFuture.supplyAsync(
                            () -> executeTask(task),
                            executor
                        )
                    )
                    .toList();

            // allOf represents completion of the entire task set.
            CompletableFuture<Void> all =
                CompletableFuture.allOf(
                    futures.toArray(
                        new CompletableFuture<?>[0]
                    )
                );

            all.join();

            return futures.stream()
                .map(CompletableFuture::join)
                .sorted(
                    Comparator.comparingInt(
                        TaskResult::taskId
                    )
                )
                .toList();

        } catch (CompletionException error) {
            throw new TaskExecutionException(
                "Asynchronous pipeline failed.",
                error.getCause()
            );

        } finally {
            executor.shutdown();
        }
    }

    // --------------------------------------------------
    // 8. ForkJoinPool divide-and-conquer processing
    // --------------------------------------------------

    static class PrimeCountTask
        extends java.util.concurrent.RecursiveTask<Long> {

        private static final int THRESHOLD = 5000;

        private final int start;
        private final int end;

        PrimeCountTask(int start, int end) {
            this.start = start;
            this.end = end;
        }

        @Override
        protected Long compute() {
            if (end - start <= THRESHOLD) {
                long count = 0;

                for (int number = start; number <= end; number++) {
                    if (isPrime(number)) {
                        count++;
                    }
                }

                return count;
            }

            int midpoint = start + (end - start) / 2;

            PrimeCountTask left =
                new PrimeCountTask(start, midpoint);

            PrimeCountTask right =
                new PrimeCountTask(midpoint + 1, end);

            left.fork();

            long rightResult = right.compute();
            long leftResult = left.join();

            return leftResult + rightResult;
        }
    }

    static long executeForkJoin(
        int limit,
        int parallelism
    ) {
        if (limit < 0 || limit > MAX_LIMIT) {
            throw new IllegalArgumentException(
                "Invalid computation limit."
            );
        }

        if (parallelism < 1) {
            throw new IllegalArgumentException(
                "Parallelism must be positive."
            );
        }

        java.util.concurrent.ForkJoinPool pool =
            new java.util.concurrent.ForkJoinPool(parallelism);

        try {
            if (limit < 2) {
                return 0;
            }

            return pool.invoke(
                new PrimeCountTask(2, limit)
            );

        } finally {
            pool.shutdown();
        }
    }

    // --------------------------------------------------
    // 9. Shared state using LongAdder
    // --------------------------------------------------

    static long demonstrateAtomicCounter() {
        LongAdder counter = new LongAdder();

        int workers = 8;
        int iterations = 10_000;

        ExecutorService executor =
            Executors.newFixedThreadPool(workers);

        try {
            List<Future<?>> futures = new ArrayList<>();

            for (int i = 0; i < workers; i++) {
                futures.add(
                    executor.submit(() -> {
                        for (
                            int j = 0;
                            j < iterations;
                            j++
                        ) {
                            counter.increment();
                        }
                    })
                );
            }

            for (Future<?> future : futures) {
                future.get();
            }

            return counter.sum();

        } catch (InterruptedException error) {
            Thread.currentThread().interrupt();

            throw new TaskExecutionException(
                "Counter interrupted.",
                error
            );

        } catch (ExecutionException error) {
            throw new TaskExecutionException(
                "Counter worker failed.",
                error.getCause()
            );

        } finally {
            executor.shutdown();
        }
    }

    // --------------------------------------------------
    // 10. Lock-based account synchronization
    // --------------------------------------------------

    static class Account {
        private long balance;

        private final ReentrantLock lock =
            new ReentrantLock();

        Account(long initialBalance) {
            if (initialBalance < 0) {
                throw new IllegalArgumentException(
                    "Invalid initial balance."
                );
            }

            this.balance = initialBalance;
        }

        boolean withdraw(long amount) {
            if (amount <= 0) {
                throw new IllegalArgumentException(
                    "Withdrawal must be positive."
                );
            }

            lock.lock();

            try {
                if (balance < amount) {
                    return false;
                }

                balance -= amount;
                return true;

            } finally {
                lock.unlock();
            }
        }

        long getBalance() {
            lock.lock();

            try {
                return balance;

            } finally {
                lock.unlock();
            }
        }
    }

    // --------------------------------------------------
    // 11. Bounded producer-consumer processing
    // --------------------------------------------------

    static List<Integer> demonstrateProducerConsumer()
        throws InterruptedException {

        ArrayBlockingQueue<Integer> queue =
            new ArrayBlockingQueue<>(3);

        List<Integer> processed =
            new java.util.concurrent.CopyOnWriteArrayList<>();

        final int poisonPill = -1;

        Thread producer = new Thread(() -> {
            try {
                for (int item = 1; item <= 10; item++) {
                    queue.put(item);
                }

                queue.put(poisonPill);

            } catch (InterruptedException error) {
                Thread.currentThread().interrupt();
            }

        }, "producer");

        Thread consumer = new Thread(() -> {
            try {
                while (true) {
                    int item = queue.take();

                    if (item == poisonPill) {
                        break;
                    }

                    processed.add(item);
                }

            } catch (InterruptedException error) {
                Thread.currentThread().interrupt();
            }

        }, "consumer");

        producer.start();
        consumer.start();

        producer.join();
        consumer.join();

        return processed.stream()
            .sorted()
            .toList();
    }

    // --------------------------------------------------
    // 12. Reporting
    // --------------------------------------------------

    static void printReport(ExecutionReport report) {
        System.out.println(
            "\n" + report.executionMode()
        );

        System.out.println(
            "Elapsed: " +
            report.elapsedMilliseconds() +
            " ms"
        );

        System.out.println(
            "Failed tasks: " +
            report.failedTasks()
        );

        report.results().forEach(result ->
            System.out.println(
                "Task " + result.taskId() +
                " | Prime count: " + result.primeCount() +
                " | Worker: " + result.workerName()
            )
        );
    }

    static boolean equivalent(
        List<TaskResult> first,
        List<TaskResult> second
    ) {
        Map<Integer, Long> firstMap =
            first.stream().collect(
                java.util.stream.Collectors.toMap(
                    TaskResult::taskId,
                    TaskResult::primeCount
                )
            );

        Map<Integer, Long> secondMap =
            second.stream().collect(
                java.util.stream.Collectors.toMap(
                    TaskResult::taskId,
                    TaskResult::primeCount
                )
            );

        return firstMap.equals(secondMap);
    }

    // --------------------------------------------------
    // 13. Main application
    // --------------------------------------------------

    public static void main(String[] args)
        throws InterruptedException {

        System.out.println(
            "PARALLELISM ENGINEERING LAB"
        );

        int processors =
            Runtime.getRuntime().availableProcessors();

        System.out.println(
            "Available processors: " + processors
        );

        List<Task> tasks = List.of(
            new Task(1, 50000),
            new Task(2, 55000),
            new Task(3, 60000),
            new Task(4, 65000),
            new Task(5, 70000),
            new Task(6, 75000)
        );

        ExecutionReport sequential =
            executeSequential(tasks);

        ExecutionReport threaded =
            executeWithExecutor(
                tasks,
                Math.min(4, processors)
            );

        printReport(sequential);
        printReport(threaded);

        List<TaskResult> asynchronous =
            executeWithCompletableFuture(
                tasks,
                Math.min(4, processors)
            );

        long forkJoinCount =
            executeForkJoin(100000, Math.max(1, processors));

        long sequentialCount =
            countPrimes(100000);

        if (forkJoinCount != sequentialCount) {
            throw new IllegalStateException(
                "ForkJoin validation failed."
            );
        }

        if (!equivalent(
            sequential.results(),
            threaded.results()
        )) {
            throw new IllegalStateException(
                "Executor results do not match."
            );
        }

        if (!equivalent(
            sequential.results(),
            asynchronous
        )) {
            throw new IllegalStateException(
                "CompletableFuture results do not match."
            );
        }

        System.out.println(
            "\nFORKJOIN PRIME COUNT: " + forkJoinCount
        );

        long atomicResult =
            demonstrateAtomicCounter();

        System.out.println(
            "\nATOMIC COUNTER: " + atomicResult
        );

        if (atomicResult != 80000) {
            throw new IllegalStateException(
                "Atomic counter validation failed."
            );
        }

        Account account = new Account(100000);

        ExecutorService withdrawals =
            Executors.newFixedThreadPool(8);

        try {
            List<Future<?>> futures = new ArrayList<>();

            for (int i = 0; i < 8; i++) {
                futures.add(
                    withdrawals.submit(
                        () -> account.withdraw(10000)
                    )
                );
            }

            for (Future<?> future : futures) {
                future.get();
            }

        } catch (ExecutionException error) {
            throw new TaskExecutionException(
                "Withdrawal processing failed.",
                error.getCause()
            );

        } finally {
            withdrawals.shutdown();
        }

        System.out.println(
            "Account balance: " + account.getBalance()
        );

        if (account.getBalance() != 20000) {
            throw new IllegalStateException(
                "Account synchronization failed."
            );
        }

        List<Integer> consumed =
            demonstrateProducerConsumer();

        System.out.println(
            "\nPRODUCER-CONSUMER: " + consumed
        );

        if (!consumed.equals(
            java.util.stream.IntStream.rangeClosed(1, 10)
                .boxed()
                .toList()
        )) {
            throw new IllegalStateException(
                "Queue validation failed."
            );
        }

        System.out.println(
            "\nAll validation checks passed."
        );
    }
}
