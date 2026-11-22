#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <condition_variable>
#include <cstdint>
#include <exception>
#include <functional>
#include <future>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <numeric>
#include <queue>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

/*
 * Parallelism: Multithreading and Multiprocessing
 *
 * C++17 implementation.
 *
 * Demonstrates:
 * 1. Sequential and parallel prime computation.
 * 2. Explicit thread creation and joining.
 * 3. Atomic synchronization.
 * 4. Mutex-protected shared state.
 * 5. Condition-variable producer-consumer coordination.
 * 6. std::async and future-based execution.
 * 7. Exception propagation.
 * 8. Benchmarking.
 *
 * Compile:
 * g++ -std=c++17 -O2 -pthread parallelism.cpp -o parallelism
 */


// --------------------------------------------------
// 1. Domain model
// --------------------------------------------------

enum class ExecutionMode {
    Sequential,
    Multithreaded,
    Async
};

struct Task {
    int id;
    std::uint64_t limit;
};

struct TaskResult {
    int id;
    std::uint64_t primeCount;
};

struct BenchmarkResult {
    std::string name;
    double elapsedMilliseconds;
    std::vector<TaskResult> results;
};


// --------------------------------------------------
// 2. Validation
// --------------------------------------------------

void validateTask(const Task& task) {
    if (task.id < 0) {
        throw std::invalid_argument(
            "Task ID cannot be negative."
        );
    }

    if (task.limit > 10'000'000) {
        throw std::invalid_argument(
            "Task limit exceeds the configured maximum."
        );
    }
}


// --------------------------------------------------
// 3. CPU-bound operation
// --------------------------------------------------

bool isPrime(std::uint64_t number) {
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
        std::uint64_t divisor = 5;
        divisor <= number / divisor;
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


std::uint64_t countPrimes(
    std::uint64_t start,
    std::uint64_t end
) {
    if (end < start) {
        return 0;
    }

    std::uint64_t count = 0;

    for (auto number = start; number <= end; ++number) {
        if (isPrime(number)) {
            ++count;
        }

        if (number == end) {
            break;
        }
    }

    return count;
}


TaskResult executeTask(const Task& task) {
    validateTask(task);

    return {
        task.id,
        countPrimes(2, task.limit)
    };
}


// --------------------------------------------------
// 4. Sequential processing
// --------------------------------------------------

std::vector<TaskResult> executeSequential(
    const std::vector<Task>& tasks
) {
    std::vector<TaskResult> results;

    results.reserve(tasks.size());

    for (const auto& task : tasks) {
        results.push_back(executeTask(task));
    }

    return results;
}


// --------------------------------------------------
// 5. Multithreaded processing
// --------------------------------------------------

std::vector<TaskResult> executeParallel(
    const std::vector<Task>& tasks,
    unsigned int workerCount
) {
    if (workerCount == 0) {
        throw std::invalid_argument(
            "Worker count must be positive."
        );
    }

    if (tasks.empty()) {
        return {};
    }

    workerCount = std::min(
        workerCount,
        static_cast<unsigned int>(tasks.size())
    );

    std::vector<TaskResult> results(tasks.size());

    std::atomic<std::size_t> nextIndex{0};

    std::atomic<bool> failed{false};

    std::exception_ptr firstException;
    std::mutex exceptionMutex;

    std::vector<std::thread> workers;

    workers.reserve(workerCount);

    for (unsigned int worker = 0;
         worker < workerCount;
         ++worker) {

        workers.emplace_back([&]() {
            while (!failed.load(std::memory_order_relaxed)) {

                const std::size_t index =
                    nextIndex.fetch_add(1);

                if (index >= tasks.size()) {
                    break;
                }

                try {
                    results[index] = executeTask(tasks[index]);
                } catch (...) {
                    failed.store(true);

                    std::lock_guard<std::mutex> guard(
                        exceptionMutex
                    );

                    if (!firstException) {
                        firstException = std::current_exception();
                    }

                    break;
                }
            }
        });
    }

    // Every worker must finish before shared results are read.
    for (auto& worker : workers) {
        worker.join();
    }

    if (firstException) {
        std::rethrow_exception(firstException);
    }

    return results;
}


// --------------------------------------------------
// 6. Asynchronous execution with futures
// --------------------------------------------------

std::vector<TaskResult> executeAsync(
    const std::vector<Task>& tasks
) {
    std::vector<std::future<TaskResult>> futures;

    futures.reserve(tasks.size());

    for (const auto& task : tasks) {
        futures.push_back(
            std::async(
                std::launch::async,
                executeTask,
                task
            )
        );
    }

    std::vector<TaskResult> results;

    results.reserve(tasks.size());

    // Calling get() retrieves results and propagates exceptions.
    for (auto& future : futures) {
        results.push_back(future.get());
    }

    return results;
}


// --------------------------------------------------
// 7. Atomic shared counter
// --------------------------------------------------

std::uint64_t demonstrateAtomicCounter() {
    constexpr int workerCount = 8;
    constexpr int iterations = 10000;

    std::atomic<std::uint64_t> counter{0};

    std::vector<std::thread> workers;

    for (int i = 0; i < workerCount; ++i) {
        workers.emplace_back([&counter]() {
            for (int j = 0; j < iterations; ++j) {
                counter.fetch_add(
                    1,
                    std::memory_order_relaxed
                );
            }
        });
    }

    for (auto& worker : workers) {
        worker.join();
    }

    return counter.load();
}


// --------------------------------------------------
// 8. Mutex-protected account
// --------------------------------------------------

class BankAccount {
private:
    std::int64_t balance_;
    mutable std::mutex mutex_;

public:
    explicit BankAccount(std::int64_t initialBalance)
        : balance_(initialBalance) {

        if (initialBalance < 0) {
            throw std::invalid_argument(
                "Initial balance cannot be negative."
            );
        }
    }

    bool withdraw(std::int64_t amount) {
        if (amount <= 0) {
            throw std::invalid_argument(
                "Withdrawal must be positive."
            );
        }

        std::lock_guard<std::mutex> guard(mutex_);

        if (balance_ < amount) {
            return false;
        }

        balance_ -= amount;
        return true;
    }

    void deposit(std::int64_t amount) {
        if (amount <= 0) {
            throw std::invalid_argument(
                "Deposit must be positive."
            );
        }

        std::lock_guard<std::mutex> guard(mutex_);

        if (
            amount >
            std::numeric_limits<std::int64_t>::max() - balance_
        ) {
            throw std::overflow_error(
                "Balance overflow."
            );
        }

        balance_ += amount;
    }

    std::int64_t balance() const {
        std::lock_guard<std::mutex> guard(mutex_);
        return balance_;
    }
};


// --------------------------------------------------
// 9. Bounded producer-consumer queue
// --------------------------------------------------

template <typename T>
class BoundedQueue {
private:
    std::queue<T> queue_;
    const std::size_t capacity_;

    std::mutex mutex_;
    std::condition_variable notEmpty_;
    std::condition_variable notFull_;

    bool closed_ = false;

public:
    explicit BoundedQueue(std::size_t capacity)
        : capacity_(capacity) {

        if (capacity == 0) {
            throw std::invalid_argument(
                "Queue capacity must be positive."
            );
        }
    }

    void push(const T& item) {
        std::unique_lock<std::mutex> lock(mutex_);

        notFull_.wait(lock, [&]() {
            return queue_.size() < capacity_ || closed_;
        });

        if (closed_) {
            throw std::runtime_error(
                "Cannot insert into a closed queue."
            );
        }

        queue_.push(item);

        lock.unlock();
        notEmpty_.notify_one();
    }

    bool pop(T& item) {
        std::unique_lock<std::mutex> lock(mutex_);

        notEmpty_.wait(lock, [&]() {
            return !queue_.empty() || closed_;
        });

        if (queue_.empty()) {
            return false;
        }

        item = queue_.front();
        queue_.pop();

        lock.unlock();
        notFull_.notify_one();

        return true;
    }

    void close() {
        {
            std::lock_guard<std::mutex> guard(mutex_);
            closed_ = true;
        }

        notEmpty_.notify_all();
        notFull_.notify_all();
    }
};


std::vector<int> demonstrateProducerConsumer() {
    BoundedQueue<int> queue(3);

    std::vector<int> processed;
    std::mutex resultMutex;

    std::thread producer([&]() {
        for (int item = 1; item <= 10; ++item) {
            queue.push(item);
        }

        queue.close();
    });

    std::thread consumer([&]() {
        int item;

        while (queue.pop(item)) {
            std::lock_guard<std::mutex> guard(resultMutex);
            processed.push_back(item);
        }
    });

    producer.join();
    consumer.join();

    std::sort(processed.begin(), processed.end());

    return processed;
}


// --------------------------------------------------
// 10. Benchmark utilities
// --------------------------------------------------

template <typename Function>
double measureMilliseconds(Function&& function) {
    const auto start = std::chrono::steady_clock::now();

    function();

    const auto end = std::chrono::steady_clock::now();

    return std::chrono::duration<double, std::milli>(
        end - start
    ).count();
}


void printResults(
    const std::string& label,
    const std::vector<TaskResult>& results,
    double elapsed
) {
    std::cout << "\n" << label << "\n";

    std::cout << "Elapsed: "
              << std::fixed
              << std::setprecision(3)
              << elapsed
              << " ms\n";

    for (const auto& result : results) {
        std::cout
            << "Task " << result.id
            << " | Prime count: " << result.primeCount
            << '\n';
    }
}


bool equivalent(
    const std::vector<TaskResult>& first,
    const std::vector<TaskResult>& second
) {
    if (first.size() != second.size()) {
        return false;
    }

    for (std::size_t i = 0; i < first.size(); ++i) {
        if (
            first[i].id != second[i].id ||
            first[i].primeCount != second[i].primeCount
        ) {
            return false;
        }
    }

    return true;
}


// --------------------------------------------------
// 11. Application
// --------------------------------------------------

int main() {
    try {
        std::cout << "PARALLELISM ENGINEERING LAB\n";

        const unsigned int hardwareThreads =
            std::thread::hardware_concurrency();

        const unsigned int workerCount =
            std::max(1u, hardwareThreads);

        std::cout << "Hardware threads: "
                  << hardwareThreads << '\n';

        std::vector<Task> tasks = {
            {1, 50000},
            {2, 55000},
            {3, 60000},
            {4, 65000},
            {5, 70000},
            {6, 75000}
        };

        std::vector<TaskResult> sequentialResults;
        std::vector<TaskResult> parallelResults;
        std::vector<TaskResult> asyncResults;

        const double sequentialTime = measureMilliseconds(
            [&]() {
                sequentialResults = executeSequential(tasks);
            }
        );

        const double parallelTime = measureMilliseconds(
            [&]() {
                parallelResults = executeParallel(
                    tasks,
                    std::min(
                        workerCount,
                        static_cast<unsigned int>(tasks.size())
                    )
                );
            }
        );

        const double asyncTime = measureMilliseconds(
            [&]() {
                asyncResults = executeAsync(tasks);
            }
        );

        printResults(
            "SEQUENTIAL EXECUTION",
            sequentialResults,
            sequentialTime
        );

        printResults(
            "MULTITHREADED EXECUTION",
            parallelResults,
            parallelTime
        );

        printResults(
            "ASYNC EXECUTION",
            asyncResults,
            asyncTime
        );

        if (
            !equivalent(sequentialResults, parallelResults) ||
            !equivalent(sequentialResults, asyncResults)
        ) {
            throw std::runtime_error(
                "Execution results do not match."
            );
        }

        std::cout << "\nATOMIC SYNCHRONIZATION\n";

        const auto atomicResult =
            demonstrateAtomicCounter();

        std::cout << "Expected: 80000\n";
        std::cout << "Actual: " << atomicResult << '\n';

        if (atomicResult != 80000) {
            throw std::runtime_error(
                "Atomic counter validation failed."
            );
        }

        std::cout << "\nBANK ACCOUNT SYNCHRONIZATION\n";

        BankAccount account(100000);

        std::vector<std::thread> withdrawals;

        for (int i = 0; i < 8; ++i) {
            withdrawals.emplace_back([&account]() {
                account.withdraw(10000);
            });
        }

        for (auto& thread : withdrawals) {
            thread.join();
        }

        std::cout << "Remaining balance: "
                  << account.balance() << '\n';

        if (account.balance() != 20000) {
            throw std::runtime_error(
                "Account synchronization failed."
            );
        }

        std::cout << "\nPRODUCER-CONSUMER\n";

        const auto processed =
            demonstrateProducerConsumer();

        for (int item : processed) {
            std::cout << item << ' ';
        }

        std::cout << '\n';

        if (processed.size() != 10) {
            throw std::runtime_error(
                "Producer-consumer validation failed."
            );
        }

        std::cout << "\nAll validation checks passed.\n";

    } catch (const std::exception& error) {
        std::cerr << "Application failure: "
                  << error.what() << '\n';

        return 1;
    }

    return 0;
}
