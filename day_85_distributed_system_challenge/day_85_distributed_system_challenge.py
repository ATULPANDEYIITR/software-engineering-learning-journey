#!/usr/bin/env python3
"""
Distributed System Challenges: Latency, Failures, and Consistency

A self-contained distributed key-value store simulator demonstrating:
- Network latency and timeout handling
- Node failures and network partitions
- Replication and quorum writes
- Strong and eventual consistency
- Versioned records and conflict resolution
- Idempotent retries
- Read repair and replica synchronization
- Availability and consistency trade-offs
"""

from __future__ import annotations

import random
import statistics
import time
import uuid

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class NodeState(Enum):
    HEALTHY = "healthy"
    UNAVAILABLE = "unavailable"
    PARTITIONED = "partitioned"


class ConsistencyLevel(Enum):
    ONE = "one"
    QUORUM = "quorum"
    ALL = "all"


class DistributedSystemError(Exception):
    pass


class NetworkTimeout(DistributedSystemError):
    pass


class QuorumUnavailable(DistributedSystemError):
    pass


class ConsistencyViolation(DistributedSystemError):
    pass


@dataclass(frozen=True)
class VersionedValue:
    key: str
    value: str
    version: int
    timestamp: float
    operation_id: str

    def ordering_key(self) -> tuple[int, float, str]:
        return self.version, self.timestamp, self.operation_id


@dataclass
class Node:
    node_id: str
    state: NodeState = NodeState.HEALTHY
    data: dict[str, VersionedValue] = field(default_factory=dict)
    applied_operations: set[str] = field(default_factory=set)

    def is_available(self) -> bool:
        return self.state == NodeState.HEALTHY

    def write(self, record: VersionedValue) -> bool:
        if not self.is_available():
            return False

        if record.operation_id in self.applied_operations:
            return True

        current = self.data.get(record.key)

        if current is None or record.ordering_key() > current.ordering_key():
            self.data[record.key] = record

        self.applied_operations.add(record.operation_id)
        return True

    def read(self, key: str) -> Optional[VersionedValue]:
        if not self.is_available():
            return None
        return self.data.get(key)


@dataclass
class OperationMetrics:
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    timeouts: int = 0
    replica_writes: int = 0
    retries: int = 0
    latency_samples: list[float] = field(default_factory=list)

    def record(self, latency: float, success: bool) -> None:
        self.total_operations += 1
        self.latency_samples.append(latency)

        if success:
            self.successful_operations += 1
        else:
            self.failed_operations += 1

    def report(self) -> None:
        print("\nSYSTEM METRICS")
        print("-" * 48)
        print(f"Operations: {self.total_operations}")
        print(f"Successful: {self.successful_operations}")
        print(f"Failed: {self.failed_operations}")
        print(f"Timeouts: {self.timeouts}")
        print(f"Retries: {self.retries}")
        print(f"Replica writes: {self.replica_writes}")

        if self.latency_samples:
            ordered = sorted(self.latency_samples)
            print(
                f"Average latency: "
                f"{statistics.mean(ordered):.2f} ms"
            )
            print(
                f"Median latency: "
                f"{statistics.median(ordered):.2f} ms"
            )
            index = min(
                len(ordered) - 1,
                int(0.95 * len(ordered))
            )
            print(f"P95 latency: {ordered[index]:.2f} ms")


class Network:
    """Simulates message latency, packet loss, and connectivity."""

    def __init__(
        self,
        base_latency_ms: float = 15.0,
        jitter_ms: float = 5.0,
        packet_loss: float = 0.0,
        seed: int = 42,
    ):
        if base_latency_ms < 0 or jitter_ms < 0:
            raise ValueError("Latency parameters cannot be negative")

        if not 0 <= packet_loss <= 1:
            raise ValueError("Packet loss must be between 0 and 1")

        self.base_latency_ms = base_latency_ms
        self.jitter_ms = jitter_ms
        self.packet_loss = packet_loss
        self.random = random.Random(seed)
        self.blocked_links: set[tuple[str, str]] = set()

    def send(self, source: str, destination: str) -> float:
        if (source, destination) in self.blocked_links:
            raise NetworkTimeout("Network partition detected")

        if self.random.random() < self.packet_loss:
            raise NetworkTimeout("Packet lost")

        latency = (
            self.base_latency_ms
            + self.random.uniform(0, self.jitter_ms)
        )
        return latency


class DistributedKeyValueStore:
    def __init__(
        self,
        node_count: int = 3,
        replication_factor: int = 3,
        network: Optional[Network] = None,
    ):
        if node_count < 1:
            raise ValueError("At least one node is required")

        if not 1 <= replication_factor <= node_count:
            raise ValueError("Invalid replication factor")

        self.nodes = [
            Node(f"node-{i + 1}")
            for i in range(node_count)
        ]

        self.replication_factor = replication_factor
        self.network = network or Network()
        self.metrics = OperationMetrics()
        self.logical_clock = 0
        self.coordinator_id = "coordinator"
        self.operation_results: dict[str, bool] = {}

    @property
    def quorum_size(self) -> int:
        return self.replication_factor // 2 + 1

    def set_node_state(
        self,
        node_id: str,
        state: NodeState,
    ) -> None:
        node = self._find_node(node_id)
        node.state = state

    def _find_node(self, node_id: str) -> Node:
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        raise ValueError(f"Unknown node: {node_id}")

    def _replicas(self, key: str) -> list[Node]:
        # Deterministic replica selection keeps the simulation reproducible.
        start = sum(key.encode("utf-8")) % len(self.nodes)
        selected = []

        for offset in range(self.replication_factor):
            selected.append(
                self.nodes[(start + offset) % len(self.nodes)]
            )

        return selected

    def write(
        self,
        key: str,
        value: str,
        consistency: ConsistencyLevel = ConsistencyLevel.QUORUM,
        operation_id: Optional[str] = None,
        max_retries: int = 2,
    ) -> bool:
        if not isinstance(key, str) or not key.strip():
            raise ValueError("Key cannot be empty")

        if not isinstance(value, str):
            raise ValueError("Value must be a string")

        if len(key) > 256 or len(value) > 10000:
            raise ValueError("Key or value exceeds the size limit")

        if max_retries < 0:
            raise ValueError("Retry count cannot be negative")

        operation_id = operation_id or str(uuid.uuid4())

        if operation_id in self.operation_results:
            return self.operation_results[operation_id]

        start = time.perf_counter()
        required = self._required_acknowledgements(consistency)
        replicas = self._replicas(key)

        self.logical_clock += 1

        record = VersionedValue(
            key=key,
            value=value,
            version=self.logical_clock,
            timestamp=time.time(),
            operation_id=operation_id,
        )

        acknowledgements = 0
        last_error = None

        try:
            for attempt in range(max_retries + 1):
                if attempt:
                    self.metrics.retries += 1

                for node in replicas:
                    if node.node_id in {
                        n.node_id for n in replicas[:0]
                    }:
                        continue

                    try:
                        self.network.send(
                            self.coordinator_id,
                            node.node_id,
                        )
                        if node.write(record):
                            acknowledgements += 1
                            self.metrics.replica_writes += 1

                    except NetworkTimeout as exc:
                        last_error = exc

                    if acknowledgements >= required:
                        self.operation_results[operation_id] = True
                        return True

                if acknowledgements >= required:
                    break

                # A failed attempt may already have reached some replicas.
                # Retry with the same operation ID to preserve idempotency.

            raise QuorumUnavailable(
                f"Required {required} acknowledgements; "
                f"received {acknowledgements}. Last error: {last_error}"
            )

        except DistributedSystemError:
            self.metrics.failed_operations += 1
            self.operation_results[operation_id] = False
            raise

        finally:
            elapsed = (
                time.perf_counter() - start
            ) * 1000

            self.metrics.record(
                elapsed,
                self.operation_results.get(operation_id, False),
            )

    def _required_acknowledgements(
        self,
        consistency: ConsistencyLevel,
    ) -> int:
        if consistency == ConsistencyLevel.ONE:
            return 1
        if consistency == ConsistencyLevel.QUORUM:
            return self.quorum_size
        return self.replication_factor

    def read(
        self,
        key: str,
        consistency: ConsistencyLevel = ConsistencyLevel.QUORUM,
        repair: bool = True,
    ) -> Optional[VersionedValue]:

        if not key:
            raise ValueError("Key cannot be empty")

        start = time.perf_counter()
        replicas = self._replicas(key)
        responses = []

        try:
            for node in replicas:
                try:
                    self.network.send(
                        self.coordinator_id,
                        node.node_id,
                    )
                    if not node.is_available():
                        continue

                    responses.append((node, node.read(key)))

                except NetworkTimeout:
                    self.metrics.timeouts += 1

            required = self._required_acknowledgements(consistency)

            if len(responses) < required:
                raise QuorumUnavailable(
                    f"Read requires {required} responses; "
                    f"received {len(responses)}"
                )

            records = [
                record
                for _, record in responses
                if record is not None
            ]

            if not records:
                return None

            latest = max(records, key=lambda r: r.ordering_key())

            if repair:
                for node, record in responses:
                    if record is None or (
                        latest.ordering_key() > record.ordering_key()
                    ):
                        node.write(latest)

            return latest

        finally:
            self.metrics.record(
                (time.perf_counter() - start) * 1000,
                True,
            )

    def partition(
        self,
        source: str,
        destination: str,
    ) -> None:
        self.network.blocked_links.add((source, destination))
        self.network.blocked_links.add((destination, source))

    def heal_partition(
        self,
        source: str,
        destination: str,
    ) -> None:
        self.network.blocked_links.discard(
            (source, destination)
        )
        self.network.blocked_links.discard(
            (destination, source)
        )

    def synchronize_replicas(self, key: str) -> int:
        replicas = self._replicas(key)

        records = [
            node.data[key]
            for node in replicas
            if node.is_available() and key in node.data
        ]

        if not records:
            return 0

        latest = max(records, key=lambda r: r.ordering_key())
        repaired = 0

        for node in replicas:
            if node.is_available():
                current = node.data.get(key)

                if (
                    current is None
                    or latest.ordering_key() > current.ordering_key()
                ):
                    node.write(latest)
                    repaired += 1

        return repaired

    def consistency_report(self, key: str) -> dict:
        versions = defaultdict(list)

        for node in self._replicas(key):
            if node.is_available():
                record = node.data.get(key)
                versions[
                    record.version if record else "missing"
                ].append(node.node_id)

        return dict(versions)


def demonstrate() -> None:
    print("=" * 58)
    print("DISTRIBUTED SYSTEM CHALLENGES")
    print("=" * 58)

    network = Network(
        base_latency_ms=12,
        jitter_ms=4,
        packet_loss=0.0,
    )

    store = DistributedKeyValueStore(
        node_count=5,
        replication_factor=3,
        network=network,
    )

    print("\n1. QUORUM WRITE")
    operation_id = "payment-transaction-001"

    store.write(
        "account:1001",
        "balance:9500",
        ConsistencyLevel.QUORUM,
        operation_id,
    )

    print("Write successfully replicated.")

    print("\n2. IDEMPOTENT RETRY")
    store.write(
        "account:1001",
        "balance:9500",
        ConsistencyLevel.QUORUM,
        operation_id,
    )
    print("Duplicate operation did not create another version.")

    print("\n3. QUORUM READ")
    result = store.read("account:1001")
    print(f"Read result: {result.value if result else None}")

    print("\n4. NODE FAILURE")
    store.set_node_state(
        "node-1",
        NodeState.UNAVAILABLE,
    )

    store.write(
        "account:1002",
        "balance:5000",
    )
    print("Write succeeded with an unavailable replica.")

    print("\n5. PARTITION")
    store.partition("coordinator", "node-2")

    try:
        store.write(
            "account:1003",
            "balance:3000",
            ConsistencyLevel.ALL,
            max_retries=0,
        )
    except QuorumUnavailable as exc:
        print(f"Expected failure: {exc}")

    print("\n6. PARTITION RECOVERY")
    store.heal_partition("coordinator", "node-2")
    store.set_node_state("node-1", NodeState.HEALTHY)

    repaired = store.synchronize_replicas("account:1001")
    print(f"Replica repairs: {repaired}")

    print("\n7. CONSISTENCY REPORT")
    print(store.consistency_report("account:1001"))

    print("\n8. INVALID INPUT")
    try:
        store.write("", "invalid")
    except ValueError as exc:
        print(f"Validation: {exc}")

    store.metrics.report()


if __name__ == "__main__":
    demonstrate()
