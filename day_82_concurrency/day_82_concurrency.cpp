#include <algorithm>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <exception>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <memory>
#include <mutex>
#include <queue>
#include <shared_mutex>
#include <stdexcept>
#include <string>
#include <thread>
#include <unordered_map>
#include <utility>
#include <vector>

/*
 * CONCURRENCY, RACE CONDITIONS, LOCKS, AND SYNCHRONIZATION
 *
 * C++17 repository-style resource management scenario:
 * - Shared mutable state
 * - Mutex synchronization
 * - RAII lock management
 * - Scoped locking
 * - Deadlock avoidance
 * - Atomic counters
 * - Read-write synchronization
 * - Condition variables
 * - Bounded producer-consumer queue
 * - Optimistic concurrency
 * - Concurrent inventory reservation
 *
 * Compile:
 * g++ -std=c++17 -O2 -pthread concurrency.cpp -o concurrency
 */

namespace concurrency {

class ValidationError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

class InsufficientResource : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

class VersionConflict : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};


// -------------------------------------------------------
// 1. SHARED RESOURCE DOMAIN
// -------------------------------------------------------

struct Account {
    std::string id;
    std::int64_t balance;

    Account(std::string accountId, std::int64_t initialBalance)
        : id(std::move(accountId)), balance(initialBalance) {

        if (id.empty() || initialBalance < 0) {
            throw ValidationError("Invalid account");
        }
    }
};


// -------------------------------------------------------
// 2. UNSYNCHRONIZED AND SYNCHRONIZED COUNTERS
// -------------------------------------------------------

class AtomicCounter {
private:
    std::atomic<std::uint64_t> value{0};

public:
    void increment() {
        value.fetch_add(1, std::memory_order_relaxed);
    }

    std::uint64_t get() const {
        return value.load(std::memory_order_relaxed);
    }
};


// -------------------------------------------------------
// 3. BANKING SERVICE
// -------------------------------------------------------

class BankingService {
private:
    struct LockedAccount {
        Account account;
        mutable std::mutex mutex;

        LockedAccount(std::string id, std::int64_t balance)
            : account(std::move(id), balance) {}
    };

    std::shared_ptr<LockedAccount> first;
    std::shared_ptr<LockedAccount> second;

public:
    BankingService()
        : first(std::make_shared<LockedAccount>("A001", 100000)),
          second(std::make_shared<LockedAccount>("A002", 100000)) {}

    void transfer(
        const std::shared_ptr<LockedAccount>& source,
        const std::shared_ptr<LockedAccount>& destination,
        std::int64_t amount
    ) {
        if (!source || !destination || source == destination) {
            throw ValidationError("Invalid transfer accounts");
        }

        if (amount <= 0) {
            throw ValidationError("Transfer must be positive");
        }

        // std::scoped_lock acquires both mutexes without
        // the conventional inconsistent lock-order deadlock.
        std::scoped_lock guard(
            source->mutex,
            destination->mutex
        );

        if (source->account.balance < amount) {
            throw InsufficientResource("Insufficient funds");
        }

        if (destination->account.balance >
            std::numeric_limits<std::int64_t>::max() - amount) {
            throw ValidationError("Balance overflow");
        }

        source->account.balance -= amount;
        destination->account.balance += amount;
    }

    void transferForward(std::int64_t amount) {
        transfer(first, second, amount);
    }

    void transferBackward(std::int64_t amount) {
        transfer(second, first, amount);
    }

    std::pair<std::int64_t, std::int64_t> snapshot() const {
        std::scoped_lock guard(first->mutex, second->mutex);

        return {
            first->account.balance,
            second->account.balance
        };
    }

    std::int64_t totalBalance() const {
        const auto state = snapshot();
        return state.first + state.second;
    }
};


// -------------------------------------------------------
// 4. READ-WRITE SYNCHRONIZATION
// -------------------------------------------------------

class ConfigurationStore {
private:
    mutable std::shared_mutex mutex;
    std::unordered_map<std::string, std::string> configuration;

public:
    void set(const std::string& key, const std::string& value) {
        if (key.empty()) {
            throw ValidationError("Configuration key cannot be empty");
        }

        std::unique_lock<std::shared_mutex> guard(mutex);
        configuration[key] = value;
    }

    std::string get(const std::string& key) const {
        std::shared_lock<std::shared_mutex> guard(mutex);

        auto it = configuration.find(key);

        if (it == configuration.end()) {
            throw std::out_of_range("Configuration key not found");
        }

        return it->second;
    }

    std::size_t size() const {
        std::shared_lock<std::shared_mutex> guard(mutex);
        return configuration.size();
    }
};


// -------------------------------------------------------
// 5. BOUNDED PRODUCER-CONSUMER QUEUE
// -------------------------------------------------------

template<typename T>
class BoundedQueue {
private:
    std::queue<T> queue;
    std::size_t capacity;
    bool closed = false;

    mutable std::mutex mutex;
    std::condition_variable notEmpty;
    std::condition_variable notFull;

public:
    explicit BoundedQueue(std::size_t maximumCapacity)
        : capacity(maximumCapacity) {

        if (capacity == 0) {
            throw ValidationError("Queue capacity must be positive");
        }
    }

    void push(T value) {
        std::unique_lock<std::mutex> lock(mutex);

        notFull.wait(lock, [&] {
            return queue.size() < capacity || closed;
        });

        if (closed) {
            throw std::runtime_error("Queue is closed");
        }

        queue.push(std::move(value));

        lock.unlock();
        notEmpty.notify_one();
    }

    bool pop(T& output) {
        std::unique_lock<std::mutex> lock(mutex);

        notEmpty.wait(lock, [&] {
            return !queue.empty() || closed;
        });

        if (queue.empty()) {
            return false;
        }

        output = std::move(queue.front());
        queue.pop();

        lock.unlock();
        notFull.notify_one();

        return true;
    }

    void close() {
        {
            std::lock_guard<std::mutex> guard(mutex);
            closed = true;
        }

        notEmpty.notify_all();
        notFull.notify_all();
    }
};


// -------------------------------------------------------
// 6. OPTIMISTIC CONCURRENCY CONTROL
// -------------------------------------------------------

struct VersionedState {
    std::int64_t value;
    std::uint64_t version;
};

class OptimisticStore {
private:
    mutable std::mutex mutex;
    VersionedState state;

public:
    explicit OptimisticStore(std::int64_t initialValue)
        : state{initialValue, 0} {}

    VersionedState read() const {
        std::lock_guard<std::mutex> guard(mutex);
        return state;
    }

    VersionedState compareAndSet(
        std::uint64_t expectedVersion,
        std::int64_t newValue
    ) {
        std::lock_guard<std::mutex> guard(mutex);

        if (state.version != expectedVersion) {
            throw VersionConflict("Version mismatch");
        }

        if (state.version == std::numeric_limits<std::uint64_t>::max()) {
            throw ValidationError("Version overflow");
        }

        state.value = newValue;
        state.version++;

        return state;
    }
};


// -------------------------------------------------------
// 7. CONCURRENT INVENTORY
// -------------------------------------------------------

class Inventory {
private:
    mutable std::mutex mutex;
    std::map<std::string, int> stock;

public:
    Inventory() {
        stock = {
            {"LAPTOP", 20},
            {"MOUSE", 100},
            {"KEYBOARD", 50}
        };
    }

    bool reserve(const std::string& product, int quantity) {
        if (quantity <= 0) {
            throw ValidationError("Quantity must be positive");
        }

        std::lock_guard<std::mutex> guard(mutex);

        auto it = stock.find(product);

        if (it == stock.end()) {
            throw std::out_of_range("Unknown product");
        }

        if (it->second < quantity) {
            return false;
        }

        it->second -= quantity;
        return true;
    }

    std::map<std::string, int> snapshot() const {
        std::lock_guard<std::mutex> guard(mutex);
        return stock;
    }
};


// -------------------------------------------------------
// 8. CONCURRENT EXECUTION ENGINE
// -------------------------------------------------------

class TaskExecutor {
private:
    BoundedQueue<std::function<void()>> tasks;
    std::vector<std::thread> workers;

    std::atomic<std::uint64_t> completed{0};
    std::atomic<std::uint64_t> failed{0};

public:
    TaskExecutor(std::size_t workerCount, std::size_t queueCapacity)
        : tasks(queueCapacity) {

        if (workerCount == 0) {
            throw ValidationError("Worker count must be positive");
        }

        for (std::size_t i = 0; i < workerCount; ++i) {
            workers.emplace_back([this] {
                std::function<void()> task;

                while (tasks.pop(task)) {
                    try {
                        task();
                        completed.fetch_add(
                            1,
                            std::memory_order_relaxed
                        );
                    } catch (const std::exception& error) {
                        failed.fetch_add(
                            1,
                            std::memory_order_relaxed
                        );

                        std::cerr << "Task failure: "
                                  << error.what() << '\n';
                    } catch (...) {
                        failed.fetch_add(
                            1,
                            std::memory_order_relaxed
                        );
                    }
                }
            });
        }
    }

    void submit(std::function<void()> task) {
        if (!task) {
            throw ValidationError("Empty task");
        }

        tasks.push(std::move(task));
    }

    void shutdown() {
        tasks.close();

        for (auto& worker : workers) {
            if (worker.joinable()) {
                worker.join();
            }
        }
    }

    std::uint64_t completedTasks() const {
        return completed.load();
    }

    std::uint64_t failedTasks() const {
        return failed.load();
    }

    ~TaskExecutor() {
        tasks.close();

        for (auto& worker : workers) {
            if (worker.joinable()) {
                worker.join();
            }
        }
    }
};

} // namespace concurrency


// -------------------------------------------------------
// 9. EXECUTABLE SCENARIOS
// -------------------------------------------------------

int main() {
    using namespace concurrency;

    try {
        std::cout << "CONCURRENCY ENGINEERING ENGINE\n";

        // Atomic counter.
        AtomicCounter counter;

        std::vector<std::thread> counterWorkers;

        for (int i = 0; i < 8; ++i) {
            counterWorkers.emplace_back([&counter] {
                for (int j = 0; j < 10000; ++j) {
                    counter.increment();
                }
            });
        }

        for (auto& worker : counterWorkers) {
            worker.join();
        }

        if (counter.get() != 80000) {
            throw std::runtime_error("Atomic counter invariant failed");
        }

        std::cout << "\n1. Atomic counter: "
                  << counter.get() << '\n';


        // Banking with simultaneous transfers.
        BankingService banking;

        std::vector<std::thread> transfers;

        for (int i = 0; i < 1000; ++i) {
            transfers.emplace_back([&banking, i] {
                if (i % 2 == 0) {
                    banking.transferForward(10);
                } else {
                    banking.transferBackward(10);
                }
            });
        }

        for (auto& worker : transfers) {
            worker.join();
        }

        const auto balances = banking.snapshot();

        if (balances.first + balances.second != 200000) {
            throw std::runtime_error("Banking invariant failed");
        }

        std::cout << "\n2. Banking synchronization\n";
        std::cout << "A001: " << balances.first << '\n';
        std::cout << "A002: " << balances.second << '\n';
        std::cout << "Total: " << banking.totalBalance() << '\n';


        // Read-write lock.
        ConfigurationStore config;

        config.set("environment", "production");
        config.set("max_connections", "100");

        std::vector<std::thread> readers;

        for (int i = 0; i < 10; ++i) {
            readers.emplace_back([&config] {
                for (int j = 0; j < 100; ++j) {
                    config.get("environment");
                }
            });
        }

        for (auto& reader : readers) {
            reader.join();
        }

        std::cout << "\n3. Shared configuration reads: "
                  << config.size() << " entries\n";


        // Producer-consumer.
        BoundedQueue<int> queue(5);

        std::atomic<int> consumed{0};

        std::thread producer([&queue] {
            for (int i = 1; i <= 100; ++i) {
                queue.push(i);
            }

            queue.close();
        });

        std::thread consumer([&queue, &consumed] {
            int value;

            while (queue.pop(value)) {
                consumed.fetch_add(value);
            }
        });

        producer.join();
        consumer.join();

        if (consumed.load() != 5050) {
            throw std::runtime_error("Producer-consumer invariant failed");
        }

        std::cout << "\n4. Producer-consumer sum: "
                  << consumed.load() << '\n';


        // Optimistic concurrency.
        OptimisticStore store(100);

        const auto original = store.read();

        const auto updated = store.compareAndSet(
            original.version,
            150
        );

        std::cout << "\n5. Optimistic concurrency\n";
        std::cout << "Value: " << updated.value
                  << ", version: " << updated.version << '\n';

        try {
            store.compareAndSet(original.version, 200);
        } catch (const VersionConflict& error) {
            std::cout << "Conflict detected: "
                      << error.what() << '\n';
        }


        // Inventory reservation.
        Inventory inventory;

        std::atomic<int> successfulReservations{0};

        std::vector<std::thread> reservationWorkers;

        for (int i = 0; i < 150; ++i) {
            reservationWorkers.emplace_back([&] {
                if (inventory.reserve("MOUSE", 1)) {
                    successfulReservations.fetch_add(1);
                }
            });
        }

        for (auto& worker : reservationWorkers) {
            worker.join();
        }

        const auto inventoryState = inventory.snapshot();

        if (successfulReservations.load() != 100 ||
            inventoryState.at("MOUSE") != 0) {
            throw std::runtime_error("Inventory invariant failed");
        }

        std::cout << "\n6. Inventory reservations: "
                  << successfulReservations.load() << '\n';


        // Bounded task execution.
        TaskExecutor executor(4, 20);

        std::atomic<int> processed{0};

        for (int i = 0; i < 100; ++i) {
            executor.submit([&processed] {
                processed.fetch_add(1);
            });
        }

        executor.shutdown();

        if (processed.load() != 100 ||
            executor.completedTasks() != 100) {
            throw std::runtime_error("Task executor invariant failed");
        }

        std::cout << "\n7. Task execution\n";
        std::cout << "Completed: "
                  << executor.completedTasks() << '\n';
        std::cout << "Failed: "
                  << executor.failedTasks() << '\n';

        std::cout << "\nAll concurrency invariants passed.\n";

    } catch (const std::exception& error) {
        std::cerr << "Execution failed: "
                  << error.what() << '\n';

        return 1;
    }

    return 0;
}
