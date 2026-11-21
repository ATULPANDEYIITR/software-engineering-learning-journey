"""
CONCURRENCY, RACE CONDITIONS, LOCKS, AND SYNCHRONIZATION

Demonstrates:
1. Shared-state concurrency
2. Race conditions
3. Thread-safe counters
4. Mutex locks
5. Reentrant locks
6. Condition variables
7. Producer-consumer synchronization
8. Deadlock prevention
9. Atomic-style operations
10. Optimistic concurrency control
11. Thread pools
12. Stress testing and invariants

Python standard library only.
"""

from __future__ import annotations

import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from queue import Queue
from typing import Optional


# ---------------------------------------------------------
# 1. DOMAIN MODEL
# ---------------------------------------------------------

@dataclass
class Account:
    account_id: str
    balance: int

    def __post_init__(self):
        if not self.account_id:
            raise ValueError("Account ID cannot be empty")
        if self.balance < 0:
            raise ValueError("Initial balance cannot be negative")


class InsufficientFundsError(Exception):
    pass


class ConcurrencyConflictError(Exception):
    pass


# ---------------------------------------------------------
# 2. DEMONSTRATING A RACE CONDITION
# ---------------------------------------------------------

class UnsafeCounter:
    """
    Multiple threads update shared state without synchronization.

    The read-modify-write sequence is not protected.
    """

    def __init__(self):
        self.value = 0

    def increment(self):
        current = self.value
        time.sleep(0)
        self.value = current + 1


def demonstrate_race_condition():
    counter = UnsafeCounter()
    thread_count = 8
    iterations = 1000

    def worker():
        for _ in range(iterations):
            counter.increment()

    threads = [
        threading.Thread(target=worker)
        for _ in range(thread_count)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    expected = thread_count * iterations

    print("\n1. Race condition demonstration")
    print("Expected:", expected)
    print("Observed:", counter.value)
    print("Result may vary because updates are unsynchronized.")


# ---------------------------------------------------------
# 3. MUTEX-STYLE LOCK SYNCHRONIZATION
# ---------------------------------------------------------

class SafeCounter:
    def __init__(self):
        self.value = 0
        self._lock = threading.Lock()

    def increment(self):
        with self._lock:
            self.value += 1

    def get_value(self):
        with self._lock:
            return self.value


def demonstrate_mutex():
    counter = SafeCounter()

    def worker():
        for _ in range(5000):
            counter.increment()

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(lambda _: worker(), range(8)))

    assert counter.get_value() == 40000

    print("\n2. Mutex synchronization")
    print("Final counter:", counter.get_value())


# ---------------------------------------------------------
# 4. REENTRANT LOCK
# ---------------------------------------------------------

class ReentrantInventory:
    """
    RLock allows the same thread to acquire the same lock
    multiple times.
    """

    def __init__(self, quantity: int):
        if quantity < 0:
            raise ValueError("Quantity cannot be negative")

        self.quantity = quantity
        self._lock = threading.RLock()

    def available(self):
        with self._lock:
            return self.quantity

    def reserve(self, amount: int):
        if amount <= 0:
            raise ValueError("Reservation must be positive")

        with self._lock:
            if self.available() < amount:
                return False

            self.quantity -= amount
            return True


# ---------------------------------------------------------
# 5. BANK ACCOUNT WITH DEADLOCK PREVENTION
# ---------------------------------------------------------

class BankAccount:
    def __init__(self, account_id: str, balance: int):
        self.account = Account(account_id, balance)
        self._lock = threading.Lock()

    @property
    def account_id(self):
        return self.account.account_id

    def get_balance(self):
        with self._lock:
            return self.account.balance


class BankingService:
    """
    Acquires account locks in deterministic account-ID order.

    Deterministic ordering prevents circular wait between
    simultaneous transfers.
    """

    @staticmethod
    def transfer(source: BankAccount,
                 destination: BankAccount,
                 amount: int):

        if amount <= 0:
            raise ValueError("Transfer amount must be positive")

        if source is destination:
            raise ValueError("Source and destination must differ")

        first, second = sorted(
            [source, destination],
            key=lambda account: account.account_id
        )

        with first._lock:
            with second._lock:
                if source.account.balance < amount:
                    raise InsufficientFundsError(
                        f"Insufficient funds in {source.account_id}"
                    )

                source.account.balance -= amount
                destination.account.balance += amount

                return True


# ---------------------------------------------------------
# 6. CONDITION VARIABLE: PRODUCER-CONSUMER
# ---------------------------------------------------------

class BoundedBuffer:
    """
    A condition variable coordinates producers and consumers.

    Producers wait when the buffer is full.
    Consumers wait when the buffer is empty.
    """

    def __init__(self, capacity: int):
        if capacity <= 0:
            raise ValueError("Capacity must be positive")

        self.capacity = capacity
        self.items = []
        self.condition = threading.Condition()
        self.closed = False

    def put(self, item):
        with self.condition:
            while len(self.items) >= self.capacity and not self.closed:
                self.condition.wait()

            if self.closed:
                raise RuntimeError("Buffer is closed")

            self.items.append(item)
            self.condition.notify_all()

    def get(self) -> Optional[int]:
        with self.condition:
            while not self.items and not self.closed:
                self.condition.wait()

            if not self.items:
                return None

            item = self.items.pop(0)
            self.condition.notify_all()
            return item

    def close(self):
        with self.condition:
            self.closed = True
            self.condition.notify_all()


def demonstrate_producer_consumer():
    buffer = BoundedBuffer(capacity=3)
    results = []

    def producer():
        for number in range(10):
            buffer.put(number)
        buffer.close()

    def consumer():
        while True:
            item = buffer.get()

            if item is None:
                break

            results.append(item)

    producer_thread = threading.Thread(target=producer)
    consumer_thread = threading.Thread(target=consumer)

    producer_thread.start()
    consumer_thread.start()

    producer_thread.join()
    consumer_thread.join()

    assert sorted(results) == list(range(10))

    print("\n3. Producer-consumer synchronization")
    print("Consumed items:", sorted(results))


# ---------------------------------------------------------
# 7. OPTIMISTIC CONCURRENCY CONTROL
# ---------------------------------------------------------

@dataclass(frozen=True)
class VersionedValue:
    value: int
    version: int


class OptimisticStore:
    """
    Reads are lightweight snapshots.

    Updates succeed only when the expected version matches
    the current version.
    """

    def __init__(self, initial_value: int):
        self._state = VersionedValue(initial_value, 0)
        self._lock = threading.Lock()

    def read(self):
        with self._lock:
            return self._state

    def compare_and_set(self, expected_version: int, new_value: int):
        with self._lock:
            if self._state.version != expected_version:
                raise ConcurrencyConflictError(
                    "The value was modified by another operation"
                )

            self._state = VersionedValue(
                new_value,
                self._state.version + 1
            )

            return self._state


def demonstrate_optimistic_control():
    store = OptimisticStore(100)

    snapshot = store.read()
    updated = store.compare_and_set(
        snapshot.version,
        snapshot.value + 50
    )

    print("\n4. Optimistic concurrency control")
    print("Updated state:", updated)

    try:
        store.compare_and_set(snapshot.version, 200)
    except ConcurrencyConflictError as error:
        print("Conflict detected:", error)


# ---------------------------------------------------------
# 8. THREAD-SAFE SHARED RESOURCE
# ---------------------------------------------------------

class InventoryService:
    def __init__(self):
        self._stock = {
            "LAPTOP": 20,
            "KEYBOARD": 50,
            "MOUSE": 100
        }
        self._lock = threading.Lock()

    def reserve(self, product: str, quantity: int):
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        with self._lock:
            if product not in self._stock:
                raise KeyError(f"Unknown product: {product}")

            if self._stock[product] < quantity:
                return False

            self._stock[product] -= quantity
            return True

    def snapshot(self):
        with self._lock:
            return self._stock.copy()


# ---------------------------------------------------------
# 9. STRESS TESTING AND INVARIANTS
# ---------------------------------------------------------

def stress_test_inventory():
    service = InventoryService()

    def reserve_worker(_):
        service.reserve("MOUSE", 1)

    with ThreadPoolExecutor(max_workers=20) as executor:
        list(executor.map(reserve_worker, range(150)))

    state = service.snapshot()

    assert state["MOUSE"] == 0
    assert all(quantity >= 0 for quantity in state.values())

    print("\n5. Concurrent inventory stress test")
    print("Inventory:", state)


def stress_test_banking():
    first = BankAccount("A001", 100000)
    second = BankAccount("A002", 100000)

    service = BankingService()

    def forward_transfer(_):
        service.transfer(first, second, 10)

    def reverse_transfer(_):
        service.transfer(second, first, 10)

    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = []

        for index in range(1000):
            if index % 2 == 0:
                futures.append(
                    executor.submit(forward_transfer, index)
                )
            else:
                futures.append(
                    executor.submit(reverse_transfer, index)
                )

        for future in futures:
            future.result()

    total = first.get_balance() + second.get_balance()

    assert total == 200000

    print("\n6. Concurrent banking stress test")
    print("Account A:", first.get_balance())
    print("Account B:", second.get_balance())
    print("Total balance:", total)


# ---------------------------------------------------------
# 10. LOCK GRANULARITY
# ---------------------------------------------------------

class PartitionedCounter:
    """
    Independent locks reduce contention between unrelated keys.
    """

    def __init__(self, partitions: int = 8):
        if partitions <= 0:
            raise ValueError("Partitions must be positive")

        self._values = {}
        self._locks = [
            threading.Lock()
            for _ in range(partitions)
        ]

    def increment(self, key: str):
        if not key:
            raise ValueError("Key cannot be empty")

        index = hash(key) % len(self._locks)

        with self._locks[index]:
            self._values[key] = self._values.get(key, 0) + 1

    def snapshot(self):
        # Acquire every lock in a consistent order.
        for lock in self._locks:
            lock.acquire()

        try:
            return self._values.copy()
        finally:
            for lock in reversed(self._locks):
                lock.release()


# ---------------------------------------------------------
# 11. EXECUTION
# ---------------------------------------------------------

def main():
    print("=" * 60)
    print("CONCURRENCY AND SYNCHRONIZATION LABORATORY")
    print("=" * 60)

    demonstrate_race_condition()
    demonstrate_mutex()

    inventory = ReentrantInventory(10)
    print("\nReentrant lock reservation:", inventory.reserve(3))
    print("Remaining inventory:", inventory.available())

    demonstrate_producer_consumer()
    demonstrate_optimistic_control()

    stress_test_inventory()
    stress_test_banking()

    partitioned = PartitionedCounter()

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(
            executor.map(
                lambda index: partitioned.increment(
                    f"KEY-{index % 4}"
                ),
                range(4000)
            )
        )

    assert sum(partitioned.snapshot().values()) == 4000

    print("\n7. Partitioned synchronization")
    print("Counters:", partitioned.snapshot())

    print("\nAll synchronization invariants passed.")


if __name__ == "__main__":
    main()
