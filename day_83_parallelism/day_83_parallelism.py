#!/usr/bin/env python3
"""
Parallelism: Multithreading and Multiprocessing

Demonstrates:
1. Sequential execution.
2. Concurrent execution with threads.
3. Parallel execution with processes.
4. CPU-bound and I/O-bound workloads.
5. Shared state and synchronization.
6. Producer-consumer coordination.
7. Error handling and task management.
8. Performance measurement and comparison.

Requirements: Python 3.10+
Dependencies: Python standard library only.
"""

from __future__ import annotations

import argparse
import logging
import math
import os
import queue
import random
import threading
import time

from concurrent.futures import (
    Future,
    ProcessPoolExecutor,
    ThreadPoolExecutor,
    as_completed,
)
from dataclasses import dataclass
from enum import Enum
from multiprocessing import cpu_count
from typing import Callable, Iterable


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(threadName)s | %(message)s",
)
logger = logging.getLogger("parallelism")


# ---------------------------------------------------------
# 1. Domain models
# ---------------------------------------------------------

class ExecutionMode(Enum):
    SEQUENTIAL = "sequential"
    THREADS = "threads"
    PROCESSES = "processes"


@dataclass(frozen=True)
class Task:
    task_id: int
    number: int

    def validate(self) -> None:
        if self.task_id < 0:
            raise ValueError("Task ID cannot be negative.")
        if self.number < 0:
            raise ValueError("Task number cannot be negative.")


@dataclass
class ExecutionResult:
    mode: ExecutionMode
    results: list[tuple[int, int]]
    elapsed_seconds: float
    successful_tasks: int
    failed_tasks: int

    @property
    def throughput(self) -> float:
        if self.elapsed_seconds <= 0:
            return 0.0
        return self.successful_tasks / self.elapsed_seconds


# ---------------------------------------------------------
# 2. CPU-bound workload
# ---------------------------------------------------------

def is_prime(number: int) -> bool:
    """Check primality using trial division up to sqrt(n)."""
    if number < 2:
        return False

    if number in (2, 3):
        return True

    if number % 2 == 0 or number % 3 == 0:
        return False

    divisor = 5

    while divisor * divisor <= number:
        if number % divisor == 0:
            return False

        if number % (divisor + 2) == 0:
            return False

        divisor += 6

    return True


def count_primes(task: Task) -> tuple[int, int]:
    """
    CPU-intensive operation.

    Counts primes up to task.number.
    This function is intentionally defined at module level
    so that ProcessPoolExecutor can serialize it.
    """
    task.validate()

    count = sum(
        1
        for number in range(2, task.number + 1)
        if is_prime(number)
    )

    return task.task_id, count


# ---------------------------------------------------------
# 3. I/O-bound workload
# ---------------------------------------------------------

def simulate_network_request(task: Task) -> tuple[int, str]:
    """
    Simulates an I/O-bound operation.

    Real network requests spend much of their time waiting.
    Threads can overlap these waiting periods.
    """
    task.validate()

    delay = 0.05 + (task.task_id % 4) * 0.02
    time.sleep(delay)

    return task.task_id, f"response-{task.task_id}"


# ---------------------------------------------------------
# 4. Sequential execution
# ---------------------------------------------------------

def execute_sequential(
    tasks: Iterable[Task],
    operation: Callable,
) -> ExecutionResult:

    start = time.perf_counter()
    results = []
    failures = 0

    for task in tasks:
        try:
            results.append(operation(task))
        except Exception:
            failures += 1
            logger.exception("Sequential task %s failed", task.task_id)

    elapsed = time.perf_counter() - start

    return ExecutionResult(
        mode=ExecutionMode.SEQUENTIAL,
        results=results,
        elapsed_seconds=elapsed,
        successful_tasks=len(results),
        failed_tasks=failures,
    )


# ---------------------------------------------------------
# 5. Thread-based execution
# ---------------------------------------------------------

def execute_with_threads(
    tasks: list[Task],
    operation: Callable,
    max_workers: int = 4,
) -> ExecutionResult:

    if max_workers < 1:
        raise ValueError("Worker count must be positive.")

    start = time.perf_counter()
    results = []
    failures = 0

    with ThreadPoolExecutor(
        max_workers=max_workers,
        thread_name_prefix="worker",
    ) as executor:

        futures: dict[Future, Task] = {
            executor.submit(operation, task): task
            for task in tasks
        }

        for future in as_completed(futures):
            task = futures[future]

            try:
                results.append(future.result())
            except Exception:
                failures += 1
                logger.exception(
                    "Thread task %s failed",
                    task.task_id,
                )

    results.sort(key=lambda item: item[0])

    elapsed = time.perf_counter() - start

    return ExecutionResult(
        mode=ExecutionMode.THREADS,
        results=results,
        elapsed_seconds=elapsed,
        successful_tasks=len(results),
        failed_tasks=failures,
    )


# ---------------------------------------------------------
# 6. Process-based execution
# ---------------------------------------------------------

def execute_with_processes(
    tasks: list[Task],
    operation: Callable,
    max_workers: int | None = None,
) -> ExecutionResult:

    if max_workers is not None and max_workers < 1:
        raise ValueError("Worker count must be positive.")

    start = time.perf_counter()
    results = []
    failures = 0

    with ProcessPoolExecutor(
        max_workers=max_workers,
    ) as executor:

        futures = {
            executor.submit(operation, task): task
            for task in tasks
        }

        for future in as_completed(futures):
            task = futures[future]

            try:
                results.append(future.result())
            except Exception:
                failures += 1
                logger.exception(
                    "Process task %s failed",
                    task.task_id,
                )

    results.sort(key=lambda item: item[0])

    elapsed = time.perf_counter() - start

    return ExecutionResult(
        mode=ExecutionMode.PROCESSES,
        results=results,
        elapsed_seconds=elapsed,
        successful_tasks=len(results),
        failed_tasks=failures,
    )


# ---------------------------------------------------------
# 7. Thread synchronization and shared state
# ---------------------------------------------------------

class ThreadSafeCounter:
    """
    Protects shared mutable state with a mutex.

    A compound read-modify-write operation must be protected.
    """

    def __init__(self):
        self._value = 0
        self._lock = threading.Lock()

    def increment(self, amount: int = 1) -> None:
        if amount < 0:
            raise ValueError("Increment must be non-negative.")

        with self._lock:
            self._value += amount

    @property
    def value(self) -> int:
        with self._lock:
            return self._value


def demonstrate_synchronization() -> int:
    counter = ThreadSafeCounter()

    def worker():
        for _ in range(10_000):
            counter.increment()

    threads = [
        threading.Thread(target=worker)
        for _ in range(8)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    return counter.value


# ---------------------------------------------------------
# 8. Producer-consumer pattern
# ---------------------------------------------------------

def demonstrate_producer_consumer() -> list[int]:
    """
    A bounded queue provides backpressure.

    The producer cannot insert unlimited work.
    The consumer retrieves work independently.
    """
    work_queue: queue.Queue[int | None] = queue.Queue(maxsize=3)
    processed = []
    result_lock = threading.Lock()

    def producer():
        for item in range(1, 11):
            work_queue.put(item)

        work_queue.put(None)

    def consumer():
        while True:
            item = work_queue.get()

            try:
                if item is None:
                    return

                with result_lock:
                    processed.append(item)
            finally:
                work_queue.task_done()

    producer_thread = threading.Thread(target=producer)
    consumer_thread = threading.Thread(target=consumer)

    producer_thread.start()
    consumer_thread.start()

    producer_thread.join()
    work_queue.join()
    consumer_thread.join()

    return sorted(processed)


# ---------------------------------------------------------
# 9. Benchmark reporting
# ---------------------------------------------------------

def print_result(result: ExecutionResult) -> None:
    print(f"\nExecution mode: {result.mode.value}")
    print(f"Successful tasks: {result.successful_tasks}")
    print(f"Failed tasks: {result.failed_tasks}")
    print(f"Elapsed: {result.elapsed_seconds:.6f} seconds")
    print(f"Throughput: {result.throughput:.2f} tasks/second")
    print(f"Results: {result.results}")


def compare_execution_modes(
    tasks: list[Task],
    workload: str,
) -> None:

    operation = (
        count_primes
        if workload == "cpu"
        else simulate_network_request
    )

    print(f"\n{'=' * 65}")
    print(f"WORKLOAD: {workload.upper()}")
    print(f"CPU cores detected: {cpu_count()}")
    print(f"{'=' * 65}")

    sequential = execute_sequential(tasks, operation)
    threaded = execute_with_threads(tasks, operation, 4)
    processed = execute_with_processes(tasks, operation)

    for result in (sequential, threaded, processed):
        print_result(result)

    # All three execution models must produce equivalent results.
    assert sequential.results == threaded.results
    assert sequential.results == processed.results

    print("\nAll execution models produced identical results.")


# ---------------------------------------------------------
# 10. Failure handling
# ---------------------------------------------------------

def demonstrate_failure_handling() -> None:
    tasks = [
        Task(0, 100),
        Task(1, -10),
        Task(2, 200),
    ]

    result = execute_with_threads(
        tasks,
        count_primes,
        max_workers=2,
    )

    print("\nFailure-handling demonstration:")
    print(f"Successful: {result.successful_tasks}")
    print(f"Failed: {result.failed_tasks}")

    assert result.successful_tasks == 2
    assert result.failed_tasks == 1


# ---------------------------------------------------------
# 11. Command-line interface
# ---------------------------------------------------------

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Parallelism benchmark and synchronization demo."
    )

    parser.add_argument(
        "--workload",
        choices=["cpu", "io", "both"],
        default="both",
    )

    parser.add_argument(
        "--tasks",
        type=int,
        default=6,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=80_000,
    )

    args = parser.parse_args()

    if args.tasks < 1 or args.tasks > 100:
        parser.error("--tasks must be between 1 and 100.")

    if args.limit < 0:
        parser.error("--limit cannot be negative.")

    return args


# ---------------------------------------------------------
# 12. Application entry point
# ---------------------------------------------------------

def main() -> None:
    args = parse_arguments()

    print("PARALLELISM ENGINEERING LAB")
    print(f"Operating system: {os.name}")
    print(f"Available CPU count: {cpu_count()}")

    if args.workload in ("cpu", "both"):
        cpu_tasks = [
            Task(
                task_id=index,
                number=args.limit + index * 1000,
            )
            for index in range(args.tasks)
        ]

        compare_execution_modes(cpu_tasks, "cpu")

    if args.workload in ("io", "both"):
        io_tasks = [
            Task(
                task_id=index,
                number=0,
            )
            for index in range(args.tasks)
        ]

        compare_execution_modes(io_tasks, "io")

    counter_value = demonstrate_synchronization()

    print("\nTHREAD SYNCHRONIZATION")
    print(f"Expected counter: 80000")
    print(f"Actual counter: {counter_value}")
    assert counter_value == 80_000

    queue_results = demonstrate_producer_consumer()

    print("\nPRODUCER-CONSUMER")
    print(f"Processed items: {queue_results}")
    assert queue_results == list(range(1, 11))

    demonstrate_failure_handling()

    print("\nAll validation checks passed.")


if __name__ == "__main__":
    # The main guard is essential for safe process creation
    # on platforms that use the spawn multiprocessing method.
    main()
