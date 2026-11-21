import java.time.Instant;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;
import java.util.Map;
import java.util.HashMap;
import java.util.Objects;
import java.util.concurrent.Callable;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.locks.Condition;
import java.util.concurrent.locks.ReentrantLock;
import java.util.concurrent.locks.ReentrantReadWriteLock;

/*
 * CONCURRENCY, RACE CONDITIONS, LOCKS, AND SYNCHRONIZATION
 *
 * Enterprise resource-processing model.
 *
 * Demonstrates:
 * - Explicit domain types
 * - Race conditions
 * - Intrinsic synchronization
 * - ReentrantLock
 * - Lock ordering
 * - ReadWriteLock
 * - Condition variables
 * - Bounded producer-consumer processing
 * - Optimistic version control
 * - ExecutorService
 * - CompletableFuture
 * - Atomic counters
 *
 * Compile: javac ConcurrencyEnterprise.java
 * Run: java ConcurrencyEnterprise
 */

public class ConcurrencyEnterprise {

    // ---------------------------------------------------
    // 1. DOMAIN TYPES AND EXCEPTIONS
    // ---------------------------------------------------

    enum OperationStatus {
        ACCEPTED,
        REJECTED,
        COMPLETED,
        CONFLICT
    }

    record AccountSnapshot(
        String accountId,
        long balance,
        long version
    ) {}

    record TransferResult(
        OperationStatus status,
        String message,
        long sourceBalance,
        long destinationBalance
    ) {}

    record VersionedValue(
        long value,
        long version
    ) {}

    static class ValidationException extends RuntimeException {
        ValidationException(String message) {
            super(message);
        }
    }

    static class InsufficientFundsException extends RuntimeException {
        InsufficientFundsException(String message) {
            super(message);
        }
    }

    static class OptimisticConflictException extends RuntimeException {
        OptimisticConflictException(String message) {
            super(message);
        }
    }


    // ---------------------------------------------------
    // 2. ACCOUNT AGGREGATE
    // ---------------------------------------------------

    static final class Account {
        private final String id;
        private long balance;
        private long version;

        Account(String id, long initialBalance) {
            if (id == null || id.isBlank()) {
                throw new ValidationException("Invalid account ID");
            }

            if (initialBalance < 0) {
                throw new ValidationException("Negative initial balance");
            }

            this.id = id;
            this.balance = initialBalance;
            this.version = 0;
        }

        String id() {
            return id;
        }

        long balance() {
            return balance;
        }

        long version() {
            return version;
        }

        void debit(long amount) {
            if (balance < amount) {
                throw new InsufficientFundsException(
                    "Insufficient funds in " + id
                );
            }

            balance -= amount;
            version++;
        }

        void credit(long amount) {
            balance = Math.addExact(balance, amount);
            version++;
        }

        AccountSnapshot snapshot() {
            return new AccountSnapshot(id, balance, version);
        }
    }


    // ---------------------------------------------------
    // 3. ENTERPRISE BANKING SERVICE
    // ---------------------------------------------------

    static final class BankingService {
        private final Map<String, Account> accounts = new HashMap<>();

        private final ReentrantLock transactionLock =
            new ReentrantLock(true);

        BankingService() {
            accounts.put("A001", new Account("A001", 100_000));
            accounts.put("A002", new Account("A002", 100_000));
        }

        TransferResult transfer(
            String sourceId,
            String destinationId,
            long amount
        ) {
            if (sourceId == null || destinationId == null ||
                sourceId.equals(destinationId)) {
                throw new ValidationException(
                    "Source and destination must differ"
                );
            }

            if (amount <= 0) {
                throw new ValidationException(
                    "Transfer amount must be positive"
                );
            }

            transactionLock.lock();

            try {
                Account source = accounts.get(sourceId);
                Account destination = accounts.get(destinationId);

                if (source == null || destination == null) {
                    throw new ValidationException("Unknown account");
                }

                if (source.balance() < amount) {
                    return new TransferResult(
                        OperationStatus.REJECTED,
                        "Insufficient funds",
                        source.balance(),
                        destination.balance()
                    );
                }

                // Calculate destination before changing source.
                Math.addExact(destination.balance(), amount);

                source.debit(amount);
                destination.credit(amount);

                return new TransferResult(
                    OperationStatus.COMPLETED,
                    "Transfer completed",
                    source.balance(),
                    destination.balance()
                );

            } finally {
                transactionLock.unlock();
            }
        }

        List<AccountSnapshot> snapshot() {
            transactionLock.lock();

            try {
                return accounts.values()
                    .stream()
                    .map(Account::snapshot)
                    .toList();
            } finally {
                transactionLock.unlock();
            }
        }

        long totalBalance() {
            return snapshot().stream()
                .mapToLong(AccountSnapshot::balance)
                .sum();
        }
    }


    // ---------------------------------------------------
    // 4. READ-WRITE SYNCHRONIZATION
    // ---------------------------------------------------

    static final class ConfigurationService {
        private final Map<String, String> settings = new HashMap<>();

        private final ReentrantReadWriteLock lock =
            new ReentrantReadWriteLock();

        void update(String key, String value) {
            if (key == null || key.isBlank() || value == null) {
                throw new ValidationException("Invalid configuration");
            }

            lock.writeLock().lock();

            try {
                settings.put(key, value);
            } finally {
                lock.writeLock().unlock();
            }
        }

        String read(String key) {
            lock.readLock().lock();

            try {
                String value = settings.get(key);

                if (value == null) {
                    throw new ValidationException("Setting not found");
                }

                return value;
            } finally {
                lock.readLock().unlock();
            }
        }

        Map<String, String> snapshot() {
            lock.readLock().lock();

            try {
                return Map.copyOf(settings);
            } finally {
                lock.readLock().unlock();
            }
        }
    }


    // ---------------------------------------------------
    // 5. OPTIMISTIC CONCURRENCY CONTROL
    // ---------------------------------------------------

    static final class VersionedDocument {
        private long value;
        private long version;

        synchronized VersionedValue read() {
            return new VersionedValue(value, version);
        }

        synchronized VersionedValue update(
            long expectedVersion,
            long newValue
        ) {
            if (version != expectedVersion) {
                throw new OptimisticConflictException(
                    "Expected version " + expectedVersion +
                    ", current version " + version
                );
            }

            if (version == Long.MAX_VALUE) {
                throw new ValidationException("Version overflow");
            }

            value = newValue;
            version++;

            return new VersionedValue(value, version);
        }
    }


    // ---------------------------------------------------
    // 6. CONDITION-BASED BOUNDED QUEUE
    // ---------------------------------------------------

    static final class BoundedQueue<T> {
        private final Deque<T> queue = new ArrayDeque<>();
        private final int capacity;

        private final ReentrantLock lock = new ReentrantLock();

        private final Condition notEmpty = lock.newCondition();
        private final Condition notFull = lock.newCondition();

        private boolean closed = false;

        BoundedQueue(int capacity) {
            if (capacity <= 0) {
                throw new ValidationException("Invalid queue capacity");
            }

            this.capacity = capacity;
        }

        void put(T item) throws InterruptedException {
            Objects.requireNonNull(item);

            lock.lockInterruptibly();

            try {
                while (queue.size() == capacity && !closed) {
                    notFull.await();
                }

                if (closed) {
                    throw new IllegalStateException("Queue is closed");
                }

                queue.addLast(item);
                notEmpty.signal();

            } finally {
                lock.unlock();
            }
        }

        T take() throws InterruptedException {
            lock.lockInterruptibly();

            try {
                while (queue.isEmpty() && !closed) {
                    notEmpty.await();
                }

                if (queue.isEmpty()) {
                    return null;
                }

                T item = queue.removeFirst();
                notFull.signal();

                return item;

            } finally {
                lock.unlock();
            }
        }

        void close() {
            lock.lock();

            try {
                closed = true;
                notEmpty.signalAll();
                notFull.signalAll();
            } finally {
                lock.unlock();
            }
        }
    }


    // ---------------------------------------------------
    // 7. ENTERPRISE TASK PROCESSOR
    // ---------------------------------------------------

    static final class TaskProcessor implements AutoCloseable {
        private final ExecutorService executor;
        private final AtomicLong completed = new AtomicLong();
        private final AtomicLong failed = new AtomicLong();

        TaskProcessor(int workerCount) {
            if (workerCount <= 0) {
                throw new ValidationException("Invalid worker count");
            }

            executor = Executors.newFixedThreadPool(workerCount);
        }

        <T> Future<T> submit(Callable<T> operation) {
            Objects.requireNonNull(operation);

            return executor.submit(() -> {
                try {
                    T result = operation.call();
                    completed.incrementAndGet();
                    return result;
                } catch (Exception error) {
                    failed.incrementAndGet();
                    throw error;
                }
            });
        }

        Map<String, Long> statistics() {
            return Map.of(
                "completed", completed.get(),
                "failed", failed.get()
            );
        }

        @Override
        public void close() {
            executor.shutdown();

            try {
                if (!executor.awaitTermination(10, TimeUnit.SECONDS)) {
                    executor.shutdownNow();
                }
            } catch (InterruptedException error) {
                executor.shutdownNow();
                Thread.currentThread().interrupt();
            }
        }
    }


    // ---------------------------------------------------
    // 8. SHARED RESOURCE INVENTORY
    // ---------------------------------------------------

    static final class InventoryService {
        private final Map<String, Integer> stock = new HashMap<>();

        private final ReentrantLock lock = new ReentrantLock();

        InventoryService() {
            stock.put("LAPTOP", 20);
            stock.put("MOUSE", 100);
            stock.put("KEYBOARD", 50);
        }

        boolean reserve(String product, int quantity) {
            if (product == null || quantity <= 0) {
                throw new ValidationException("Invalid reservation");
            }

            lock.lock();

            try {
                Integer available = stock.get(product);

                if (available == null) {
                    throw new ValidationException("Unknown product");
                }

                if (available < quantity) {
                    return false;
                }

                stock.put(product, available - quantity);
                return true;

            } finally {
                lock.unlock();
            }
        }

        Map<String, Integer> snapshot() {
            lock.lock();

            try {
                return Map.copyOf(stock);
            } finally {
                lock.unlock();
            }
        }
    }


    // ---------------------------------------------------
    // 9. CONCURRENT EXECUTION
    // ---------------------------------------------------

    static void testBanking() throws Exception {
        BankingService service = new BankingService();

        try (TaskProcessor processor = new TaskProcessor(12)) {
            List<Future<TransferResult>> operations = new ArrayList<>();

            for (int i = 0; i < 1000; i++) {
                final boolean forward = i % 2 == 0;

                operations.add(processor.submit(() ->
                    forward
                        ? service.transfer("A001", "A002", 10)
                        : service.transfer("A002", "A001", 10)
                ));
            }

            for (Future<TransferResult> operation : operations) {
                operation.get();
            }

            if (service.totalBalance() != 200_000) {
                throw new IllegalStateException("Banking invariant failed");
            }

            System.out.println("\n1. Banking state");

            service.snapshot().forEach(System.out::println);

            System.out.println("Total: " + service.totalBalance());
            System.out.println("Processor: " + processor.statistics());
        }
    }


    static void testInventory() throws Exception {
        InventoryService inventory = new InventoryService();

        ExecutorService executor = Executors.newFixedThreadPool(20);

        try {
            List<Future<Boolean>> results = new ArrayList<>();

            for (int i = 0; i < 150; i++) {
                results.add(
                    executor.submit(() -> inventory.reserve("MOUSE", 1))
                );
            }

            int successful = 0;

            for (Future<Boolean> result : results) {
                if (result.get()) {
                    successful++;
                }
            }

            if (successful != 100 ||
                inventory.snapshot().get("MOUSE") != 0) {
                throw new IllegalStateException("Inventory invariant failed");
            }

            System.out.println("\n2. Inventory");
            System.out.println("Reservations: " + successful);
            System.out.println(inventory.snapshot());

        } finally {
            executor.shutdown();
            executor.awaitTermination(10, TimeUnit.SECONDS);
        }
    }


    static void testOptimisticConcurrency() {
        VersionedDocument document = new VersionedDocument();

        VersionedValue initial = document.read();

        VersionedValue updated = document.update(
            initial.version(),
            500
        );

        System.out.println("\n3. Optimistic concurrency");
        System.out.println(updated);

        try {
            document.update(initial.version(), 900);
            throw new IllegalStateException("Conflict was not detected");
        } catch (OptimisticConflictException error) {
            System.out.println("Conflict detected: " + error.getMessage());
        }
    }


    static void testProducerConsumer() throws Exception {
        BoundedQueue<Integer> queue = new BoundedQueue<>(5);

        AtomicLong total = new AtomicLong();

        Thread producer = new Thread(() -> {
            try {
                for (int i = 1; i <= 100; i++) {
                    queue.put(i);
                }
            } catch (InterruptedException error) {
                Thread.currentThread().interrupt();
            } finally {
                queue.close();
            }
        });

        Thread consumer = new Thread(() -> {
            try {
                Integer value;

                while ((value = queue.take()) != null) {
                    total.addAndGet(value);
                }
            } catch (InterruptedException error) {
                Thread.currentThread().interrupt();
            }
        });

        producer.start();
        consumer.start();

        producer.join();
        consumer.join();

        if (total.get() != 5050) {
            throw new IllegalStateException("Queue invariant failed");
        }

        System.out.println("\n4. Producer-consumer total: " + total.get());
    }


    static void testConfiguration() {
        ConfigurationService configuration = new ConfigurationService();

        configuration.update("environment", "production");
        configuration.update("maxConnections", "100");

        ExecutorService readers = Executors.newFixedThreadPool(8);

        try {
            List<CompletableFuture<String>> tasks = new ArrayList<>();

            for (int i = 0; i < 100; i++) {
                tasks.add(CompletableFuture.supplyAsync(
                    () -> configuration.read("environment"),
                    readers
                ));
            }

            CompletableFuture.allOf(
                tasks.toArray(CompletableFuture[]::new)
            ).join();

            System.out.println("\n5. Read-write synchronization");
            System.out.println(configuration.snapshot());

        } finally {
            readers.shutdown();
        }
    }


    // ---------------------------------------------------
    // 10. APPLICATION ENTRY POINT
    // ---------------------------------------------------

    public static void main(String[] args) {
        System.out.println("ENTERPRISE CONCURRENCY ENGINE");

        try {
            testBanking();
            testInventory();
            testOptimisticConcurrency();
            testProducerConsumer();
            testConfiguration();

            System.out.println(
                "\nAll concurrency and synchronization checks passed."
            );

        } catch (Exception error) {
            System.err.println("Execution failed: " + error.getMessage());
            error.printStackTrace();
            System.exit(1);
        }
    }
}
