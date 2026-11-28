#!/usr/bin/env python3
"""
Distributed Messaging: Queues, Streams, and Delivery Guarantees.

Demonstrates:
- Point-to-point message queues
- Append-only event streams
- Consumer groups and competing consumers
- At-most-once, at-least-once, and simulated exactly-once processing
- Acknowledgements, negative acknowledgements, retries, and dead-letter queues
- Idempotent message processing
- Offset management and replay
- Message validation, persistence, and failure handling

Python 3.10+
Standard library only.
"""

from __future__ import annotations

import json
import logging
import time
import uuid

from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Optional


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

logger = logging.getLogger("distributed-messaging")


class DeliveryGuarantee(Enum):
    AT_MOST_ONCE = "at-most-once"
    AT_LEAST_ONCE = "at-least-once"
    EXACTLY_ONCE = "exactly-once"


class MessageState(Enum):
    PENDING = "pending"
    IN_FLIGHT = "in_flight"
    ACKNOWLEDGED = "acknowledged"
    DEAD_LETTERED = "dead_lettered"


class MessagingError(Exception):
    pass


class MessageValidationError(MessagingError):
    pass


class MessageNotFoundError(MessagingError):
    pass


@dataclass(frozen=True)
class Message:
    message_id: str
    topic: str
    key: str
    payload: dict[str, Any]
    timestamp: float
    headers: dict[str, str] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        topic: str,
        key: str,
        payload: dict[str, Any],
        headers: Optional[dict[str, str]] = None
    ) -> "Message":

        if not topic or len(topic) > 128:
            raise MessageValidationError("Invalid topic")

        if not key or len(key) > 256:
            raise MessageValidationError("Invalid message key")

        if not isinstance(payload, dict):
            raise MessageValidationError("Payload must be an object")

        try:
            encoded = json.dumps(payload, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise MessageValidationError(
                "Payload must contain valid JSON values"
            ) from exc

        if len(encoded.encode("utf-8")) > 1_000_000:
            raise MessageValidationError("Message exceeds size limit")

        return cls(
            message_id=str(uuid.uuid4()),
            topic=topic,
            key=key,
            payload=payload,
            timestamp=time.time(),
            headers=headers or {}
        )


@dataclass
class Delivery:
    message: Message
    attempts: int = 0
    state: MessageState = MessageState.PENDING


class MessageQueue:
    """Point-to-point queue with explicit acknowledgement."""

    def __init__(self, name: str, max_retries: int = 3):
        if not name:
            raise ValueError("Queue name is required")

        if max_retries < 0:
            raise ValueError("Retry count cannot be negative")

        self.name = name
        self.max_retries = max_retries

        self.pending: deque[Delivery] = deque()
        self.in_flight: dict[str, Delivery] = {}
        self.dead_letters: list[Delivery] = []

        self.lock = RLock()

    def publish(self, message: Message) -> None:
        with self.lock:
            self.pending.append(Delivery(message))
            logger.info("Published %s to %s", message.message_id, self.name)

    def receive(self) -> Optional[Delivery]:
        with self.lock:
            if not self.pending:
                return None

            delivery = self.pending.popleft()
            delivery.state = MessageState.IN_FLIGHT
            delivery.attempts += 1

            self.in_flight[delivery.message.message_id] = delivery

            return delivery

    def acknowledge(self, message_id: str) -> None:
        with self.lock:
            delivery = self.in_flight.pop(message_id, None)

            if delivery is None:
                raise MessageNotFoundError(
                    f"Message {message_id} is not in flight"
                )

            delivery.state = MessageState.ACKNOWLEDGED
            logger.info("Acknowledged %s", message_id)

    def negative_acknowledge(self, message_id: str) -> None:
        with self.lock:
            delivery = self.in_flight.pop(message_id, None)

            if delivery is None:
                raise MessageNotFoundError(message_id)

            if delivery.attempts <= self.max_retries:
                delivery.state = MessageState.PENDING
                self.pending.append(delivery)

                logger.warning(
                    "Retrying %s, attempt %s",
                    message_id,
                    delivery.attempts
                )
            else:
                delivery.state = MessageState.DEAD_LETTERED
                self.dead_letters.append(delivery)

                logger.error("Dead-lettered %s", message_id)

    def recover_unacknowledged(self) -> int:
        """Requeue messages left in flight after consumer failure."""

        with self.lock:
            deliveries = list(self.in_flight.values())
            self.in_flight.clear()

            for delivery in deliveries:
                delivery.state = MessageState.PENDING
                self.pending.appendleft(delivery)

            return len(deliveries)

    def statistics(self) -> dict[str, int]:
        with self.lock:
            return {
                "pending": len(self.pending),
                "in_flight": len(self.in_flight),
                "dead_letters": len(self.dead_letters)
            }


class EventStream:
    """
    Append-only partitioned event stream.

    Each consumer group maintains an independent committed offset.
    Offsets identify positions within a partition.
    """

    def __init__(self, name: str, partitions: int = 3):
        if partitions < 1:
            raise ValueError("At least one partition is required")

        self.name = name
        self.partitions: list[list[Message]] = [
            [] for _ in range(partitions)
        ]

        self.offsets: dict[str, list[int]] = {}
        self.lock = RLock()

    def append(self, message: Message) -> tuple[int, int]:
        with self.lock:
            partition = hash(message.key) % len(self.partitions)

            offset = len(self.partitions[partition])
            self.partitions[partition].append(message)

            return partition, offset

    def register_consumer_group(self, group: str) -> None:
        if not group:
            raise ValueError("Consumer group is required")

        with self.lock:
            self.offsets.setdefault(
                group,
                [0] * len(self.partitions)
            )

    def poll(
        self,
        group: str,
        partition: int,
        batch_size: int = 10
    ) -> list[tuple[int, Message]]:

        if batch_size < 1:
            raise ValueError("Batch size must be positive")

        with self.lock:
            if group not in self.offsets:
                raise MessagingError("Unknown consumer group")

            if not 0 <= partition < len(self.partitions):
                raise ValueError("Invalid partition")

            start = self.offsets[group][partition]
            end = min(
                start + batch_size,
                len(self.partitions[partition])
            )

            return [
                (offset, self.partitions[partition][offset])
                for offset in range(start, end)
            ]

    def commit(
        self,
        group: str,
        partition: int,
        next_offset: int
    ) -> None:

        with self.lock:
            if group not in self.offsets:
                raise MessagingError("Unknown consumer group")

            current = self.offsets[group][partition]
            maximum = len(self.partitions[partition])

            if next_offset < current or next_offset > maximum:
                raise ValueError("Invalid offset transition")

            self.offsets[group][partition] = next_offset

    def replay(self, group: str, partition: int, offset: int) -> None:
        with self.lock:
            if group not in self.offsets:
                raise MessagingError("Unknown consumer group")

            if not 0 <= offset <= len(self.partitions[partition]):
                raise ValueError("Invalid replay offset")

            self.offsets[group][partition] = offset

    def get_offsets(self, group: str) -> list[int]:
        with self.lock:
            return list(self.offsets[group])


class IdempotentProcessor:
    """
    Simulates atomic deduplication and business-state updates.

    A real exactly-once guarantee across external systems requires
    transactional coordination or an equivalent atomic boundary.
    """

    def __init__(self):
        self.processed_ids: set[str] = set()
        self.account_balances: dict[str, float] = defaultdict(float)
        self.lock = RLock()

    def process(self, message: Message) -> bool:
        with self.lock:
            if message.message_id in self.processed_ids:
                logger.info("Duplicate ignored: %s", message.message_id)
                return False

            account = message.payload.get("account")
            amount = message.payload.get("amount")

            if not isinstance(account, str) or not account:
                raise MessageValidationError("Invalid account")

            if (
                not isinstance(amount, (int, float))
                or isinstance(amount, bool)
                or amount <= 0
            ):
                raise MessageValidationError("Invalid amount")

            # Deduplication and business update share one critical section.
            self.account_balances[account] += float(amount)
            self.processed_ids.add(message.message_id)

            return True


class Consumer:
    def __init__(
        self,
        name: str,
        processor: Callable[[Message], Any],
        guarantee: DeliveryGuarantee
    ):
        self.name = name
        self.processor = processor
        self.guarantee = guarantee

    def consume(self, queue: MessageQueue) -> bool:
        delivery = queue.receive()

        if delivery is None:
            return False

        message = delivery.message

        try:
            if self.guarantee == DeliveryGuarantee.AT_MOST_ONCE:
                # Acknowledge before processing: failure can lose work.
                queue.acknowledge(message.message_id)
                self.processor(message)

            elif self.guarantee == DeliveryGuarantee.AT_LEAST_ONCE:
                # Process before acknowledgement: failure can cause duplicates.
                self.processor(message)
                queue.acknowledge(message.message_id)

            elif self.guarantee == DeliveryGuarantee.EXACTLY_ONCE:
                # The processor must provide an atomic idempotency boundary.
                self.processor(message)
                queue.acknowledge(message.message_id)

            return True

        except Exception:
            if message.message_id in queue.in_flight:
                queue.negative_acknowledge(message.message_id)

            logger.exception(
                "Consumer %s failed on %s",
                self.name,
                message.message_id
            )

            return False


def save_stream(stream: EventStream, path: str) -> None:
    """Persist a snapshot for demonstration, not a production log."""

    records = []

    for partition_id, partition in enumerate(stream.partitions):
        for offset, message in enumerate(partition):
            records.append({
                "partition": partition_id,
                "offset": offset,
                "message": asdict(message)
            })

    Path(path).write_text(
        json.dumps(records, indent=2),
        encoding="utf-8"
    )


def run_queue_demo() -> None:
    print("\n=== MESSAGE QUEUE ===")

    queue = MessageQueue("payments", max_retries=2)
    processor = IdempotentProcessor()

    message = Message.create(
        "payments",
        "account-100",
        {"account": "account-100", "amount": 2500}
    )

    queue.publish(message)

    consumer = Consumer(
        "payment-worker-1",
        processor.process,
        DeliveryGuarantee.AT_LEAST_ONCE
    )

    consumer.consume(queue)

    # Simulate redelivery of the same message.
    processor.process(message)

    print("Account balances:", dict(processor.account_balances))
    print("Queue statistics:", queue.statistics())


def run_stream_demo() -> None:
    print("\n=== EVENT STREAM ===")

    stream = EventStream("orders", partitions=3)

    stream.register_consumer_group("analytics")
    stream.register_consumer_group("billing")

    for index in range(1, 6):
        message = Message.create(
            "orders",
            f"customer-{index % 2}",
            {
                "order_id": index,
                "amount": index * 100
            }
        )

        stream.append(message)

    # Analytics consumes every partition independently.
    for partition_id in range(3):
        events = stream.poll(
            "analytics",
            partition_id,
            batch_size=10
        )

        for offset, message in events:
            print(
                f"Partition={partition_id}, "
                f"Offset={offset}, "
                f"Order={message.payload['order_id']}"
            )

        stream.commit(
            "analytics",
            partition_id,
            stream.get_offsets("analytics")[partition_id]
            + len(events)
        )

    # Billing has independent offsets and can replay events.
    print("Analytics offsets:", stream.get_offsets("analytics"))
    print("Billing offsets:", stream.get_offsets("billing"))

    save_stream(stream, "event_stream_snapshot.json")


def run_retry_demo() -> None:
    print("\n=== RETRY AND DEAD-LETTER QUEUE ===")

    queue = MessageQueue("notifications", max_retries=2)

    message = Message.create(
        "notifications",
        "user-101",
        {"recipient": "user-101", "event": "password_changed"}
    )

    queue.publish(message)

    for attempt in range(4):
        delivery = queue.receive()

        if delivery is None:
            break

        print("Attempt:", delivery.attempts)

        queue.negative_acknowledge(message.message_id)

    print("Queue statistics:", queue.statistics())


def run_validation_demo() -> None:
    print("\n=== VALIDATION ===")

    try:
        Message.create(
            topic="",
            key="invalid",
            payload={}
        )
    except MessageValidationError as exc:
        print("Expected validation error:", exc)


def main() -> None:
    run_queue_demo()
    run_stream_demo()
    run_retry_demo()
    run_validation_demo()

    print("\nDistributed messaging demonstration completed.")


if __name__ == "__main__":
    main()
