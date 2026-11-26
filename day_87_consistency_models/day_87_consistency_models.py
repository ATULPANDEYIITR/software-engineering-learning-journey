from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from threading import RLock
from typing import Any, Optional
from collections import defaultdict
import json
import time
import uuid


class ConsistencyModel(Enum):
    STRONG = "strong"
    EVENTUAL = "eventual"
    CAUSAL = "causal"


class ConsistencyError(Exception):
    """Raised when a consistency guarantee cannot be satisfied."""


class ReplicaUnavailable(ConsistencyError):
    pass


class CausalDependencyError(ConsistencyError):
    pass


@dataclass(frozen=True)
class VectorClock:
    values: dict[str, int] = field(default_factory=dict)

    def increment(self, replica_id: str) -> VectorClock:
        updated = dict(self.values)
        updated[replica_id] = updated.get(replica_id, 0) + 1
        return VectorClock(updated)

    def merge(self, other: VectorClock) -> VectorClock:
        keys = self.values.keys() | other.values.keys()
        return VectorClock({
            key: max(self.values.get(key, 0), other.values.get(key, 0))
            for key in keys
        })

    def dominates(self, other: VectorClock) -> bool:
        keys = self.values.keys() | other.values.keys()
        return all(
            self.values.get(key, 0) >= other.values.get(key, 0)
            for key in keys
        )

    def concurrent(self, other: VectorClock) -> bool:
        return not self.dominates(other) and not other.dominates(self)

    def to_dict(self) -> dict[str, int]:
        return dict(self.values)


@dataclass(frozen=True)
class WriteEvent:
    event_id: str
    key: str
    value: Any
    origin: str
    clock: VectorClock
    timestamp: float


@dataclass
class Replica:
    replica_id: str
    available: bool = True
    data: dict[str, WriteEvent] = field(default_factory=dict)
    clock: VectorClock = field(default_factory=VectorClock)
    pending: list[WriteEvent] = field(default_factory=list)

    def get(self, key: str) -> Optional[WriteEvent]:
        return self.data.get(key)

    def apply(self, event: WriteEvent) -> bool:
        """Apply an event if it is newer or resolves a concurrent update."""
        existing = self.data.get(event.key)

        if existing is not None:
            if existing.clock.dominates(event.clock):
                return False

            if existing.clock.concurrent(event.clock):
                # Deterministic conflict resolution for this demonstration.
                if (existing.timestamp, existing.origin) >= (
                    event.timestamp, event.origin
                ):
                    return False

        self.data[event.key] = event
        self.clock = self.clock.merge(event.clock)
        return True


class DistributedKeyValueStore:
    """
    Educational distributed key-value store.

    STRONG:
        Writes are committed to every available replica atomically.
        Reads use the authoritative state under a shared lock.

    EVENTUAL:
        Writes are accepted locally and propagated later.
        Concurrent updates use deterministic last-writer resolution.

    CAUSAL:
        Writes carry vector-clock dependencies.
        Replicas apply causally dependent events in dependency order.
    """

    def __init__(self, replica_ids: list[str]):
        if len(replica_ids) < 2:
            raise ValueError("At least two replicas are required.")

        if len(set(replica_ids)) != len(replica_ids):
            raise ValueError("Replica identifiers must be unique.")

        if any(not rid.strip() for rid in replica_ids):
            raise ValueError("Replica identifiers cannot be empty.")

        self.replicas = {
            rid: Replica(rid) for rid in replica_ids
        }
        self.events: dict[str, WriteEvent] = {}
        self.mode = ConsistencyModel.EVENTUAL
        self._lock = RLock()
        self._sequence = 0

    def set_mode(self, mode: ConsistencyModel) -> None:
        with self._lock:
            self.mode = mode

    def set_availability(self, replica_id: str, available: bool) -> None:
        replica = self._get_replica(replica_id)
        with self._lock:
            replica.available = available

    def _get_replica(self, replica_id: str) -> Replica:
        try:
            return self.replicas[replica_id]
        except KeyError:
            raise ValueError(f"Unknown replica: {replica_id}") from None

    @staticmethod
    def _validate(key: str, value: Any) -> None:
        if not isinstance(key, str) or not key.strip():
            raise ValueError("Key must be a non-empty string.")

        if len(key) > 200:
            raise ValueError("Key exceeds 200 characters.")

        try:
            json.dumps(value, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("Value must be JSON-compatible.") from exc

    def _create_event(
        self,
        replica: Replica,
        key: str,
        value: Any,
        context: Optional[VectorClock] = None
    ) -> WriteEvent:
        base = replica.clock
        if context is not None:
            base = base.merge(context)

        clock = base.increment(replica.replica_id)

        self._sequence += 1
        event = WriteEvent(
            event_id=str(uuid.uuid4()),
            key=key,
            value=value,
            origin=replica.replica_id,
            clock=clock,
            timestamp=time.time() + self._sequence * 1e-9
        )
        return event

    def write(
        self,
        replica_id: str,
        key: str,
        value: Any,
        context: Optional[VectorClock] = None
    ) -> WriteEvent:
        self._validate(key, value)

        with self._lock:
            replica = self._get_replica(replica_id)

            if not replica.available:
                raise ReplicaUnavailable(
                    f"Replica {replica_id} is unavailable."
                )

            event = self._create_event(replica, key, value, context)

            if self.mode == ConsistencyModel.STRONG:
                unavailable = [
                    r.replica_id
                    for r in self.replicas.values()
                    if not r.available
                ]

                if unavailable:
                    raise ReplicaUnavailable(
                        f"Strong write rejected. Unavailable replicas: "
                        f"{unavailable}"
                    )

                # Validate before changing any replica.
                for target in self.replicas.values():
                    target.apply(event)

            elif self.mode == ConsistencyModel.EVENTUAL:
                replica.apply(event)
                self.events[event.event_id] = event

                for target in self.replicas.values():
                    if target.replica_id != replica_id:
                        target.pending.append(event)

            elif self.mode == ConsistencyModel.CAUSAL:
                if context is not None and not replica.clock.dominates(context):
                    raise CausalDependencyError(
                        "The origin has not observed the supplied context."
                    )

                replica.apply(event)
                self.events[event.event_id] = event

                for target in self.replicas.values():
                    if target.replica_id != replica_id:
                        target.pending.append(event)

            return event

    def read(
        self,
        replica_id: str,
        key: str,
        context: Optional[VectorClock] = None
    ) -> Optional[Any]:
        with self._lock:
            replica = self._get_replica(replica_id)

            if not replica.available:
                raise ReplicaUnavailable(
                    f"Replica {replica_id} is unavailable."
                )

            if self.mode == ConsistencyModel.STRONG:
                # All strong writes update every replica.
                event = self._authoritative_read(key)

            else:
                event = replica.get(key)

            if event is None:
                return None

            if context is not None and not event.clock.dominates(context):
                raise CausalDependencyError(
                    "The replica has not observed the requested context."
                )

            return event.value

    def _authoritative_read(self, key: str) -> Optional[WriteEvent]:
        candidates = [
            replica.data[key]
            for replica in self.replicas.values()
            if key in replica.data
        ]

        if not candidates:
            return None

        return max(
            candidates,
            key=lambda event: (event.timestamp, event.origin)
        )

    def synchronize(self) -> int:
        """
        Propagate pending events.

        Causal dependencies are checked before application.
        Events that cannot yet be applied remain pending.
        """
        with self._lock:
            applied = 0

            for replica in self.replicas.values():
                if not replica.available:
                    continue

                remaining = list(replica.pending)
                replica.pending.clear()

                progress = True

                while remaining and progress:
                    progress = False
                    next_round = []

                    for event in remaining:
                        if self.mode == ConsistencyModel.CAUSAL:
                            if not replica.clock.dominates(event.clock):
                                # An event's origin clock includes its
                                # dependencies. Do not apply it prematurely.
                                dependency_clock = VectorClock({
                                    k: max(0, v - (1 if k == event.origin else 0))
                                    for k, v in event.clock.values.items()
                                })

                                if not replica.clock.dominates(dependency_clock):
                                    next_round.append(event)
                                    continue

                        if replica.apply(event):
                            applied += 1

                        progress = True

                    remaining = next_round

                replica.pending.extend(remaining)

            return applied

    def inspect(self, key: str) -> dict[str, Any]:
        with self._lock:
            result = {}

            for rid, replica in self.replicas.items():
                event = replica.get(key)

                result[rid] = {
                    "available": replica.available,
                    "value": event.value if event else None,
                    "clock": event.clock.to_dict() if event else {},
                    "pending_events": len(replica.pending)
                }

            return result

    def consistency_report(self, key: str) -> dict[str, Any]:
        with self._lock:
            values = {
                rid: (
                    replica.data[key].value
                    if key in replica.data else None
                )
                for rid, replica in self.replicas.items()
            }

            return {
                "key": key,
                "replica_values": values,
                "converged": len(set(map(repr, values.values()))) == 1,
                "pending_events": sum(
                    len(replica.pending)
                    for replica in self.replicas.values()
                )
            }


def demonstrate_strong_consistency() -> None:
    print("\n1. STRONG CONSISTENCY")

    store = DistributedKeyValueStore(["east", "west", "central"])
    store.set_mode(ConsistencyModel.STRONG)

    store.write("east", "account:100", {"balance": 5000})

    print("East:", store.read("east", "account:100"))
    print("West:", store.read("west", "account:100"))

    store.set_availability("central", False)

    try:
        store.write("east", "account:100", {"balance": 4000})
    except ReplicaUnavailable as exc:
        print("Rejected:", exc)

    print("Balance after rejected write:", store.read("east", "account:100"))


def demonstrate_eventual_consistency() -> None:
    print("\n2. EVENTUAL CONSISTENCY")

    store = DistributedKeyValueStore(["asia", "europe", "america"])
    store.set_mode(ConsistencyModel.EVENTUAL)

    store.write("asia", "inventory:product-1", 120)

    print("Before replication:")
    print(json.dumps(store.inspect("inventory:product-1"), indent=2))

    store.synchronize()

    print("After replication:")
    print(json.dumps(store.inspect("inventory:product-1"), indent=2))

    print("Convergence:", store.consistency_report("inventory:product-1"))


def demonstrate_causal_consistency() -> None:
    print("\n3. CAUSAL CONSISTENCY")

    store = DistributedKeyValueStore(["node-a", "node-b", "node-c"])
    store.set_mode(ConsistencyModel.CAUSAL)

    first = store.write("node-a", "message:1", "Order created")

    second = store.write(
        "node-a",
        "message:2",
        "Payment initiated",
        context=first.clock
    )

    print("First event:", first.clock.to_dict())
    print("Second event:", second.clock.to_dict())

    # Replication applies the causal chain in dependency order.
    store.synchronize()

    print("Node B message 1:", store.read("node-b", "message:1"))
    print("Node B message 2:", store.read("node-b", "message:2"))

    print("Causal clocks:")
    print(json.dumps(store.inspect("message:2"), indent=2))


def demonstrate_edge_cases() -> None:
    print("\n4. VALIDATION AND FAILURE HANDLING")

    store = DistributedKeyValueStore(["primary", "secondary"])

    try:
        store.write("primary", "", "invalid")
    except ValueError as exc:
        print("Validation:", exc)

    try:
        store.write("unknown", "key", "value")
    except ValueError as exc:
        print("Unknown replica:", exc)

    store.set_mode(ConsistencyModel.EVENTUAL)
    store.set_availability("secondary", False)

    store.write("primary", "offline:test", "accepted locally")
    print("Pending events:", len(store.replicas["secondary"].pending))

    store.set_availability("secondary", True)
    store.synchronize()

    print("Recovered replica:", store.read("secondary", "offline:test"))


def main() -> None:
    demonstrate_strong_consistency()
    demonstrate_eventual_consistency()
    demonstrate_causal_consistency()
    demonstrate_edge_cases()


if __name__ == "__main__":
    main()
