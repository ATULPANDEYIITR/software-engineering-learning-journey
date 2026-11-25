#!/usr/bin/env python3
"""
CAP Theorem: Consistency, Availability, and Partition Tolerance

Executable distributed key-value store simulation.

Demonstrates:
- Distributed nodes and replica state
- Network partitions and partition healing
- CP behavior using majority quorum
- AP behavior using local writes
- Versioned records and deterministic conflict resolution
- Read/write availability
- Replication and consistency checks
- Failure handling and validation
- Automated assertions

Python 3.10+
Standard library only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import json
import logging
import time


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger("cap-theorem")


class CAPMode(Enum):
    CP = "Consistency + Partition Tolerance"
    AP = "Availability + Partition Tolerance"


class OperationStatus(Enum):
    SUCCESS = "success"
    REJECTED = "rejected"
    UNAVAILABLE = "unavailable"
    CONFLICT = "conflict"


class CAPError(Exception):
    """Base exception for distributed storage failures."""


class InvalidConfiguration(CAPError):
    pass


class NodeUnavailable(CAPError):
    pass


class QuorumUnavailable(CAPError):
    pass


@dataclass(frozen=True)
class Version:
    logical_time: int
    writer_id: str

    def ordering_key(self) -> tuple[int, str]:
        return self.logical_time, self.writer_id


@dataclass
class Record:
    key: str
    value: str
    version: Version
    updated_at: float = field(default_factory=time.time)


@dataclass
class Node:
    node_id: str
    available: bool = True
    partition_group: int = 0
    records: dict[str, Record] = field(default_factory=dict)

    def read(self, key: str) -> Optional[Record]:
        if not self.available:
            raise NodeUnavailable(self.node_id)
        return self.records.get(key)

    def write(self, record: Record) -> None:
        if not self.available:
            raise NodeUnavailable(self.node_id)

        current = self.records.get(record.key)

        if current is None or record.version.ordering_key() > current.version.ordering_key():
            self.records[record.key] = record


@dataclass
class OperationResult:
    status: OperationStatus
    message: str
    node_id: str
    value: Optional[str] = None


class DistributedCluster:
    """
    Simulates a distributed key-value cluster.

    CP:
        A write requires a majority quorum in the requester's
        connected partition. Minority partitions reject writes.

    AP:
        Available nodes accept local writes. Conflicting versions
        are reconciled deterministically after partition healing.

    This is an educational model, not a production consensus protocol.
    """

    def __init__(
        self,
        node_count: int = 3,
        mode: CAPMode = CAPMode.CP
    ):
        if node_count < 1:
            raise InvalidConfiguration("At least one node is required.")

        if not isinstance(mode, CAPMode):
            raise InvalidConfiguration("Invalid CAP mode.")

        self.mode = mode
        self.nodes = {
            f"node-{i + 1}": Node(f"node-{i + 1}")
            for i in range(node_count)
        }
        self.clock = 0
        self.operation_log: list[dict] = []

    @property
    def quorum(self) -> int:
        return len(self.nodes) // 2 + 1

    def get_node(self, node_id: str) -> Node:
        if node_id not in self.nodes:
            raise InvalidConfiguration(f"Unknown node: {node_id}")
        return self.nodes[node_id]

    def connected_nodes(self, node_id: str) -> list[Node]:
        """
        Nodes in the same partition group can communicate.
        Unavailable nodes are excluded.
        """
        requester = self.get_node(node_id)

        if not requester.available:
            return []

        return [
            node for node in self.nodes.values()
            if node.available
            and node.partition_group == requester.partition_group
        ]

    def partition(self, groups: list[list[str]]) -> None:
        assigned = set()

        for group_number, group in enumerate(groups):
            if not group:
                raise InvalidConfiguration("Partition groups cannot be empty.")

            for node_id in group:
                node = self.get_node(node_id)

                if node_id in assigned:
                    raise InvalidConfiguration(
                        f"Node appears in multiple groups: {node_id}"
                    )

                assigned.add(node_id)
                node.partition_group = group_number

        for node_id, node in self.nodes.items():
            if node_id not in assigned:
                node.partition_group = len(groups)

        logger.info("Network partition created: %s", groups)

    def heal_partition(self) -> None:
        """
        Restore communication and reconcile replicas.

        The highest logical version wins. Writer ID breaks ties.
        Production systems should use an explicitly designed
        conflict-resolution policy.
        """
        for node in self.nodes.values():
            node.partition_group = 0

        self.reconcile()
        logger.info("Network partition healed.")

    def set_node_availability(self, node_id: str, available: bool) -> None:
        self.get_node(node_id).available = available

    def reconcile(self) -> None:
        merged: dict[str, Record] = {}

        for node in self.nodes.values():
            if not node.available:
                continue

            for key, record in node.records.items():
                current = merged.get(key)

                if (
                    current is None
                    or record.version.ordering_key()
                    > current.version.ordering_key()
                ):
                    merged[key] = record

        for node in self.nodes.values():
            if node.available:
                node.records.update(merged)

    def write(
        self,
        node_id: str,
        key: str,
        value: str
    ) -> OperationResult:
        if not key or not key.strip():
            raise ValueError("Key cannot be empty.")

        if not isinstance(value, str):
            raise ValueError("Value must be a string.")

        connected = self.connected_nodes(node_id)

        if not connected:
            return OperationResult(
                OperationStatus.UNAVAILABLE,
                "No available connection to the requesting node.",
                node_id
            )

        if self.mode == CAPMode.CP and len(connected) < self.quorum:
            result = OperationResult(
                OperationStatus.REJECTED,
                f"Write rejected: quorum {self.quorum} unavailable.",
                node_id
            )
            self._log("WRITE", result, key)
            return result

        self.clock += 1

        record = Record(
            key=key,
            value=value,
            version=Version(self.clock, node_id)
        )

        if self.mode == CAPMode.CP:
            # A majority must participate in this educational
            # quorum model before the write is acknowledged.
            for node in connected:
                node.write(record)
        else:
            # AP accepts the write on the local replica.
            self.get_node(node_id).write(record)

        result = OperationResult(
            OperationStatus.SUCCESS,
            "Write acknowledged.",
            node_id,
            value
        )

        self._log("WRITE", result, key)
        return result

    def read(self, node_id: str, key: str) -> OperationResult:
        connected = self.connected_nodes(node_id)

        if not connected:
            return OperationResult(
                OperationStatus.UNAVAILABLE,
                "No available replica.",
                node_id
            )

        if self.mode == CAPMode.CP:
            if len(connected) < self.quorum:
                return OperationResult(
                    OperationStatus.UNAVAILABLE,
                    "Read rejected because quorum is unavailable.",
                    node_id
                )

            candidates = [
                node.records[key]
                for node in connected
                if key in node.records
            ]

            if not candidates:
                return OperationResult(
                    OperationStatus.SUCCESS,
                    "Key does not exist.",
                    node_id
                )

            latest = max(
                candidates,
                key=lambda record: record.version.ordering_key()
            )

            return OperationResult(
                OperationStatus.SUCCESS,
                "Quorum read completed.",
                node_id,
                latest.value
            )

        # AP reads return the locally available replica value.
        record = self.get_node(node_id).records.get(key)

        return OperationResult(
            OperationStatus.SUCCESS,
            "Local read completed.",
            node_id,
            record.value if record else None
        )

    def _log(
        self,
        operation: str,
        result: OperationResult,
        key: str
    ) -> None:
        self.operation_log.append({
            "operation": operation,
            "key": key,
            "node": result.node_id,
            "status": result.status.value,
            "message": result.message
        })

    def consistency_report(self) -> dict:
        snapshots = {}

        for node in self.nodes.values():
            if node.available:
                snapshots[node.node_id] = {
                    key: record.value
                    for key, record in node.records.items()
                }

        return {
            "mode": self.mode.value,
            "quorum": self.quorum,
            "replicas": snapshots,
            "consistent": len({
                json.dumps(snapshot, sort_keys=True)
                for snapshot in snapshots.values()
            }) <= 1
        }


def demonstrate_cp() -> None:
    print("\n========== CP DEMONSTRATION ==========")

    cluster = DistributedCluster(3, CAPMode.CP)

    print(cluster.write("node-1", "account-101", "5000"))

    cluster.partition([
        ["node-1"],
        ["node-2", "node-3"]
    ])

    result = cluster.write("node-1", "account-101", "6000")
    print("Minority write:", result.status.value)

    result = cluster.write("node-2", "account-101", "5500")
    print("Majority write:", result.status.value)

    cluster.heal_partition()

    print("Final state:", cluster.consistency_report())


def demonstrate_ap() -> None:
    print("\n========== AP DEMONSTRATION ==========")

    cluster = DistributedCluster(3, CAPMode.AP)

    cluster.write("node-1", "product-stock", "100")
    cluster.partition([
        ["node-1"],
        ["node-2", "node-3"]
    ])

    result1 = cluster.write("node-1", "product-stock", "80")
    result2 = cluster.write("node-2", "product-stock", "90")

    print("Partition A write:", result1.status.value)
    print("Partition B write:", result2.status.value)

    print("Before healing:", cluster.consistency_report())

    cluster.heal_partition()

    print("After healing:", cluster.consistency_report())


def run_tests() -> None:
    cp = DistributedCluster(3, CAPMode.CP)

    assert cp.write("node-1", "k", "v1").status == OperationStatus.SUCCESS

    cp.partition([
        ["node-1"],
        ["node-2", "node-3"]
    ])

    assert cp.write("node-1", "k", "v2").status == OperationStatus.REJECTED
    assert cp.write("node-2", "k", "v3").status == OperationStatus.SUCCESS

    cp.heal_partition()

    ap = DistributedCluster(3, CAPMode.AP)

    ap.partition([
        ["node-1"],
        ["node-2", "node-3"]
    ])

    assert ap.write("node-1", "k", "A").status == OperationStatus.SUCCESS
    assert ap.write("node-2", "k", "B").status == OperationStatus.SUCCESS

    ap.heal_partition()

    assert ap.consistency_report()["consistent"]

    ap.set_node_availability("node-1", False)

    assert ap.read("node-1", "k").status == OperationStatus.UNAVAILABLE

    try:
        DistributedCluster(0)
        raise AssertionError("Invalid configuration was accepted.")
    except InvalidConfiguration:
        pass

    print("\nAll automated assertions passed.")


def main() -> None:
    demonstrate_cp()
    demonstrate_ap()
    run_tests()


if __name__ == "__main__":
    main()
