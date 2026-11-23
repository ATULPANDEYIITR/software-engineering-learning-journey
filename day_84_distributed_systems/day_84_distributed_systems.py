#!/usr/bin/env python3
"""
Distributed Systems: Nodes, Networks, and Distributed State

A self-contained distributed key-value store simulator demonstrating:
- Distributed nodes and network topology
- Message delivery, delay, duplication, and loss
- Network partitions and recovery
- Lamport logical clocks
- Replicated state and eventual consistency
- Last-Write-Wins conflict resolution
- Quorum-based reads and writes
- Node failure detection
- Anti-entropy synchronization
- Idempotent message processing
- Consistency validation and failure handling

Run:
    python distributed_systems.py
"""

from __future__ import annotations

import copy
import random
import time
import uuid

from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ============================================================
# CONFIGURATION
# ============================================================

RANDOM_SEED = 42
random.seed(RANDOM_SEED)

REPLICATION_FACTOR = 3


# ============================================================
# DOMAIN TYPES
# ============================================================

class NodeStatus(Enum):
    ACTIVE = "active"
    UNREACHABLE = "unreachable"
    STOPPED = "stopped"


class MessageType(Enum):
    REPLICATION = "replication"
    HEARTBEAT = "heartbeat"
    ANTI_ENTROPY = "anti_entropy"


class ConsistencyLevel(Enum):
    ONE = 1
    QUORUM = 2
    ALL = 3


class DistributedSystemError(Exception):
    """Base exception for distributed-system failures."""


class NodeUnavailableError(DistributedSystemError):
    pass


class QuorumUnavailableError(DistributedSystemError):
    pass


class NetworkPartitionError(DistributedSystemError):
    pass


# ============================================================
# DISTRIBUTED VERSIONING
# ============================================================

@dataclass(frozen=True, order=True)
class Version:
    """
    A deterministic version identifier.

    Logical clock establishes causal ordering where possible.
    Node identifier provides deterministic conflict resolution
    when concurrent writes have equal logical timestamps.
    """

    logical_time: int
    node_id: str

    def __post_init__(self):
        if self.logical_time < 0:
            raise ValueError("Logical time cannot be negative")

        if not self.node_id:
            raise ValueError("Node identifier cannot be empty")


@dataclass
class Record:
    key: str
    value: Any
    version: Version
    updated_at: float = field(default_factory=time.time)

    def __post_init__(self):
        if not self.key:
            raise ValueError("Record key cannot be empty")

        if len(self.key) > 256:
            raise ValueError("Record key exceeds maximum length")


@dataclass
class Message:
    message_id: str
    sender: str
    receiver: str
    message_type: MessageType
    payload: Any
    created_at: float = field(default_factory=time.time)


# ============================================================
# NETWORK SIMULATION
# ============================================================

class Network:
    """
    Simulates communication between distributed nodes.

    Supports:
    - Network partitions
    - Message loss
    - Message duplication
    - Delayed delivery
    - FIFO delivery queue
    """

    def __init__(
        self,
        packet_loss_rate: float = 0.0,
        duplication_rate: float = 0.0,
        seed: int = RANDOM_SEED
    ):
        if not 0 <= packet_loss_rate <= 1:
            raise ValueError("Invalid packet loss rate")

        if not 0 <= duplication_rate <= 1:
            raise ValueError("Invalid duplication rate")

        self.packet_loss_rate = packet_loss_rate
        self.duplication_rate = duplication_rate
        self.random = random.Random(seed)

        self.partitions: set[frozenset[str]] = set()
        self.queue: deque[Message] = deque()

        self.dropped_messages = 0
        self.delivered_messages = 0

    def partition(self, node_a: str, node_b: str):
        if node_a == node_b:
            raise ValueError("A node cannot be partitioned from itself")

        self.partitions.add(frozenset((node_a, node_b)))

    def heal(self):
        self.partitions.clear()

    def is_connected(self, node_a: str, node_b: str) -> bool:
        return (
            node_a != node_b
            and frozenset((node_a, node_b)) not in self.partitions
        )

    def send(self, message: Message) -> bool:
        if not self.is_connected(message.sender, message.receiver):
            self.dropped_messages += 1
            return False

        if self.random.random() < self.packet_loss_rate:
            self.dropped_messages += 1
            return False

        self.queue.append(message)

        if self.random.random() < self.duplication_rate:
            duplicate = copy.deepcopy(message)
            self.queue.append(duplicate)

        return True

    def deliver_all(self, nodes: dict[str, "Node"]):
        """
        Deliver queued messages.

        Messages are checked against current connectivity.
        A message can be rejected after a partition forms.
        """

        while self.queue:
            message = self.queue.popleft()

            receiver = nodes.get(message.receiver)

            if receiver is None or receiver.status != NodeStatus.ACTIVE:
                self.dropped_messages += 1
                continue

            if not self.is_connected(message.sender, message.receiver):
                self.dropped_messages += 1
                continue

            receiver.receive(message)
            self.delivered_messages += 1


# ============================================================
# DISTRIBUTED NODE
# ============================================================

class Node:

    def __init__(self, node_id: str, network: Network):
        if not node_id:
            raise ValueError("Node ID is required")

        self.node_id = node_id
        self.network = network

        self.status = NodeStatus.ACTIVE
        self.logical_clock = 0

        self.data: dict[str, Record] = {}
        self.processed_messages: set[str] = set()

        self.peers: set[str] = set()

        self.metrics = defaultdict(int)

    def add_peer(self, peer_id: str):
        if peer_id != self.node_id:
            self.peers.add(peer_id)

    def tick(self) -> int:
        self.logical_clock += 1
        return self.logical_clock

    def observe(self, version: Version):
        self.logical_clock = max(
            self.logical_clock,
            version.logical_time
        ) + 1

    def write_local(self, key: str, value: Any) -> Record:
        if self.status != NodeStatus.ACTIVE:
            raise NodeUnavailableError(self.node_id)

        version = Version(self.tick(), self.node_id)

        record = Record(
            key=key,
            value=value,
            version=version
        )

        self.data[key] = record
        self.metrics["local_writes"] += 1

        return record

    def apply_replica(self, incoming: Record) -> bool:
        """
        Last-Write-Wins resolution.

        Version comparison is deterministic.
        Older replicas cannot overwrite newer records.
        """

        existing = self.data.get(incoming.key)

        if existing is not None and existing.version >= incoming.version:
            self.metrics["stale_updates"] += 1
            return False

        self.observe(incoming.version)
        self.data[incoming.key] = copy.deepcopy(incoming)

        self.metrics["replicated_updates"] += 1
        return True

    def receive(self, message: Message):
        if self.status != NodeStatus.ACTIVE:
            return

        if message.message_id in self.processed_messages:
            self.metrics["duplicate_messages"] += 1
            return

        self.processed_messages.add(message.message_id)

        if message.message_type == MessageType.REPLICATION:
            self.apply_replica(message.payload)

        elif message.message_type == MessageType.HEARTBEAT:
            self.metrics["heartbeats_received"] += 1

        elif message.message_type == MessageType.ANTI_ENTROPY:
            for record in message.payload:
                self.apply_replica(record)

    def replicate(self, record: Record, peers: list[str]) -> int:
        successful = 0

        for peer_id in peers:
            message = Message(
                message_id=str(uuid.uuid4()),
                sender=self.node_id,
                receiver=peer_id,
                message_type=MessageType.REPLICATION,
                payload=copy.deepcopy(record)
            )

            if self.network.send(message):
                successful += 1

        return successful

    def snapshot(self) -> dict[str, Any]:
        return {
            key: {
                "value": record.value,
                "logical_time": record.version.logical_time,
                "origin": record.version.node_id
            }
            for key, record in sorted(self.data.items())
        }


# ============================================================
# DISTRIBUTED CLUSTER
# ============================================================

class DistributedCluster:

    def __init__(self, node_ids: list[str]):
        if len(node_ids) < 3:
            raise ValueError("Cluster requires at least three nodes")

        if len(set(node_ids)) != len(node_ids):
            raise ValueError("Node identifiers must be unique")

        self.network = Network()

        self.nodes = {
            node_id: Node(node_id, self.network)
            for node_id in node_ids
        }

        for node in self.nodes.values():
            for peer_id in node_ids:
                node.add_peer(peer_id)

        self.replication_factor = min(
            REPLICATION_FACTOR,
            len(node_ids)
        )

    @property
    def quorum(self) -> int:
        return self.replication_factor // 2 + 1

    def active_nodes(self) -> list[Node]:
        return [
            node
            for node in self.nodes.values()
            if node.status == NodeStatus.ACTIVE
        ]

    def write(
        self,
        coordinator_id: str,
        key: str,
        value: Any,
        consistency: ConsistencyLevel = ConsistencyLevel.QUORUM
    ) -> Record:

        coordinator = self.nodes.get(coordinator_id)

        if coordinator is None or coordinator.status != NodeStatus.ACTIVE:
            raise NodeUnavailableError(coordinator_id)

        if consistency == ConsistencyLevel.ONE:
            required = 1
        elif consistency == ConsistencyLevel.QUORUM:
            required = self.quorum
        else:
            required = self.replication_factor

        record = coordinator.write_local(key, value)

        targets = [
            node.node_id
            for node in self.active_nodes()
            if node.node_id != coordinator_id
            and self.network.is_connected(coordinator_id, node.node_id)
        ]

        targets = targets[:self.replication_factor - 1]

        acknowledged = 1

        for target in targets:
            message = Message(
                message_id=str(uuid.uuid4()),
                sender=coordinator_id,
                receiver=target,
                message_type=MessageType.REPLICATION,
                payload=copy.deepcopy(record)
            )

            if self.network.send(message):
                acknowledged += 1

        if acknowledged < required:
            raise QuorumUnavailableError(
                f"Write requires {required} acknowledgements; "
                f"received {acknowledged}. "
                "The coordinator's local write may still exist."
            )

        self.network.deliver_all(self.nodes)

        return record

    def read(
        self,
        key: str,
        consistency: ConsistencyLevel = ConsistencyLevel.QUORUM
    ) -> Optional[Record]:

        if consistency == ConsistencyLevel.ONE:
            required = 1
        elif consistency == ConsistencyLevel.QUORUM:
            required = self.quorum
        else:
            required = self.replication_factor

        replicas = [
            node.data[key]
            for node in self.active_nodes()
            if key in node.data
        ]

        if len(replicas) < required:
            raise QuorumUnavailableError(
                f"Read requires {required} replicas; "
                f"found {len(replicas)}"
            )

        latest = max(replicas, key=lambda record: record.version)

        if consistency != ConsistencyLevel.ONE:
            for node in self.active_nodes():
                if self.network.is_connected(
                    replicas[0].version.node_id,
                    node.node_id
                ):
                    node.apply_replica(latest)

        return copy.deepcopy(latest)

    def stop_node(self, node_id: str):
        self.nodes[node_id].status = NodeStatus.STOPPED

    def start_node(self, node_id: str):
        self.nodes[node_id].status = NodeStatus.ACTIVE

    def create_partition(self, node_a: str, node_b: str):
        self.network.partition(node_a, node_b)

    def heal_network(self):
        self.network.heal()

    def anti_entropy(self):
        """
        Exchange complete local snapshots between reachable nodes.

        The newest version wins independently for every key.
        """

        active = self.active_nodes()

        for source in active:
            for target in active:
                if source.node_id == target.node_id:
                    continue

                if not self.network.is_connected(
                    source.node_id,
                    target.node_id
                ):
                    continue

                records = [
                    copy.deepcopy(record)
                    for record in source.data.values()
                ]

                message = Message(
                    message_id=str(uuid.uuid4()),
                    sender=source.node_id,
                    receiver=target.node_id,
                    message_type=MessageType.ANTI_ENTROPY,
                    payload=records
                )

                self.network.send(message)

        self.network.deliver_all(self.nodes)

    def check_convergence(self) -> bool:
        active = self.active_nodes()

        if not active:
            return True

        reference = active[0].snapshot()

        return all(
            node.snapshot() == reference
            for node in active[1:]
        )

    def cluster_report(self) -> dict[str, Any]:
        return {
            "nodes": {
                node_id: {
                    "status": node.status.value,
                    "records": len(node.data),
                    "logical_clock": node.logical_clock,
                    "metrics": dict(node.metrics)
                }
                for node_id, node in self.nodes.items()
            },
            "network": {
                "delivered": self.network.delivered_messages,
                "dropped": self.network.dropped_messages,
                "pending": len(self.network.queue)
            },
            "converged": self.check_convergence()
        }


# ============================================================
# NODE FAILURE DETECTION
# ============================================================

class FailureDetector:

    def __init__(self, timeout_seconds: float = 5.0):
        if timeout_seconds <= 0:
            raise ValueError("Timeout must be positive")

        self.timeout = timeout_seconds
        self.last_seen: dict[str, float] = {}

    def heartbeat(self, node_id: str, timestamp: float):
        self.last_seen[node_id] = timestamp

    def suspected_nodes(self, current_time: float) -> set[str]:
        return {
            node_id
            for node_id, timestamp in self.last_seen.items()
            if current_time - timestamp > self.timeout
        }


# ============================================================
# TESTS AND DEMONSTRATION
# ============================================================

def run_tests():
    cluster = DistributedCluster(["node-1", "node-2", "node-3"])

    # Basic replicated write.
    record = cluster.write(
        "node-1",
        "account:1001",
        {"balance": 5000},
        ConsistencyLevel.QUORUM
    )

    assert record.value["balance"] == 5000
    assert cluster.read("account:1001").value["balance"] == 5000
    assert cluster.check_convergence()

    # Network partition.
    cluster.create_partition("node-1", "node-2")
    cluster.create_partition("node-1", "node-3")

    try:
        cluster.write(
            "node-1",
            "account:1001",
            {"balance": 6000},
            ConsistencyLevel.QUORUM
        )
        raise AssertionError("Quorum failure was expected")
    except QuorumUnavailableError:
        pass

    # Restore connectivity and synchronize.
    cluster.heal_network()
    cluster.anti_entropy()

    assert cluster.check_convergence()

    # Node failure.
    cluster.stop_node("node-3")

    assert len(cluster.active_nodes()) == 2

    cluster.start_node("node-3")
    cluster.anti_entropy()

    assert cluster.check_convergence()

    # Logical-clock ordering.
    node_a = cluster.nodes["node-1"]
    node_b = cluster.nodes["node-2"]

    first = node_a.write_local("clock:test", "first")
    second = node_b.write_local("clock:test", "second")

    winner = max(first, second, key=lambda item: item.version)

    node_a.apply_replica(winner)
    node_b.apply_replica(winner)

    assert node_a.data["clock:test"].version == winner.version
    assert node_b.data["clock:test"].version == winner.version

    # Idempotent message handling.
    message = Message(
        message_id="fixed-message-id",
        sender="node-1",
        receiver="node-2",
        message_type=MessageType.HEARTBEAT,
        payload={}
    )

    node_b.receive(message)
    node_b.receive(message)

    assert node_b.metrics["duplicate_messages"] >= 1

    # Failure detector.
    detector = FailureDetector(timeout_seconds=5)

    detector.heartbeat("node-1", 100.0)

    assert "node-1" in detector.suspected_nodes(106.0)

    print("All distributed-system tests passed.")


def main():
    print("=" * 65)
    print("DISTRIBUTED SYSTEMS SIMULATION")
    print("=" * 65)

    run_tests()

    cluster = DistributedCluster([
        "node-1",
        "node-2",
        "node-3",
        "node-4",
        "node-5"
    ])

    print("\n1. Distributed write")

    cluster.write(
        "node-1",
        "inventory:product-101",
        {
            "product": "Industrial Sensor",
            "quantity": 250,
            "warehouse": "Lucknow"
        },
        ConsistencyLevel.QUORUM
    )

    print("\n2. Replicated state")

    for node_id, node in cluster.nodes.items():
        print(node_id, node.snapshot())

    print("\n3. Simulating network partition")

    cluster.create_partition("node-1", "node-4")
    cluster.create_partition("node-1", "node-5")

    try:
        cluster.write(
            "node-1",
            "inventory:product-101",
            {"quantity": 200},
            ConsistencyLevel.QUORUM
        )
    except QuorumUnavailableError as error:
        print("Expected failure:", error)

    print("\n4. Recovering network")

    cluster.heal_network()
    cluster.anti_entropy()

    print("Convergence:", cluster.check_convergence())

    print("\n5. Cluster report")

    import json
    print(json.dumps(cluster.cluster_report(), indent=2))

    print("\nSimulation completed.")


if __name__ == "__main__":
    main()
