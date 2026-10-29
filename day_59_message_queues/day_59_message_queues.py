from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from collections import deque
from typing import Callable, Optional
import json
import time
import uuid


class MessageState(Enum):
    READY = "ready"
    PROCESSING = "processing"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"
    DEAD_LETTERED = "dead_lettered"


@dataclass
class Message:
    topic: str
    payload: dict
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    attempts: int = 0
    state: MessageState = MessageState.READY
    created_at: float = field(default_factory=time.time)
    available_at: float = 0.0

    def validate(self) -> None:
        if not self.topic or not self.topic.strip():
            raise ValueError("Message topic cannot be empty")
        if not isinstance(self.payload, dict):
            raise TypeError("Message payload must be a dictionary")
        if self.attempts < 0:
            raise ValueError("Message attempts cannot be negative")


class QueueError(Exception):
    pass


class QueueFullError(QueueError):
    pass


class MessageQueue:
    """In-memory durable-style queue with retry and dead-letter behavior."""

    def __init__(self, name: str, max_size: int = 100, max_attempts: int = 3):
        if max_size <= 0 or max_attempts <= 0:
            raise ValueError("Queue limits must be positive")
        self.name = name
        self.max_size = max_size
        self.max_attempts = max_attempts
        self._messages: deque[Message] = deque()
        self._dead_letters: list[Message] = []
        self.published = 0
        self.acknowledged = 0
        self.failed = 0

    def publish(self, message: Message) -> str:
        message.validate()
        if len(self._messages) >= self.max_size:
            raise QueueFullError(f"Queue {self.name} is full")
        self._messages.append(message)
        self.published += 1
        return message.message_id

    def consume(self) -> Optional[Message]:
        now = time.time()
        for _ in range(len(self._messages)):
            message = self._messages.popleft()
            if message.available_at <= now and message.state == MessageState.READY:
                message.state = MessageState.PROCESSING
                message.attempts += 1
                return message
            self._messages.append(message)
        return None

    def acknowledge(self, message: Message) -> None:
        if message.state != MessageState.PROCESSING:
            raise QueueError("Only processing messages can be acknowledged")
        message.state = MessageState.ACKNOWLEDGED
        self.acknowledged += 1

    def reject(self, message: Message, retry_delay: float = 0.05) -> None:
        if message.state != MessageState.PROCESSING:
            raise QueueError("Only processing messages can be rejected")

        self.failed += 1
        if message.attempts >= self.max_attempts:
            message.state = MessageState.DEAD_LETTERED
            self._dead_letters.append(message)
            return

        message.state = MessageState.READY
        message.available_at = time.time() + max(0.0, retry_delay)
        self._messages.append(message)

    def depth(self) -> int:
        return len(self._messages)

    def dead_letter_count(self) -> int:
        return len(self._dead_letters)

    def dead_letters(self) -> list[Message]:
        return list(self._dead_letters)


@dataclass
class Consumer:
    name: str
    handler: Callable[[Message], None]

    def process(self, queue: MessageQueue) -> bool:
        message = queue.consume()
        if message is None:
            return False

        try:
            self.handler(message)
            queue.acknowledge(message)
        except Exception:
            queue.reject(message)
        return True


def order_handler(message: Message) -> None:
    order_id = message.payload.get("order_id")
    amount = message.payload.get("amount")

    if not isinstance(order_id, str) or not order_id:
        raise ValueError("Invalid order identifier")
    if not isinstance(amount, (int, float)) or amount <= 0:
        raise ValueError("Order amount must be positive")

    # Simulate business processing. Real systems should make this operation
    # idempotent so retries cannot create duplicate side effects.
    print(f"processed order={order_id} amount={amount:.2f}")


def flaky_handler(message: Message) -> None:
    # Demonstrates bounded retry and dead-letter handling.
    if message.payload.get("always_fail"):
        raise RuntimeError("Simulated downstream failure")
    print(f"processed resilient message={message.message_id}")


def run_demo() -> None:
    orders = MessageQueue("orders", max_size=10, max_attempts=3)
    consumer = Consumer("order-worker", order_handler)

    for order_id, amount in [("ORD-1001", 149.50), ("ORD-1002", 299.00)]:
        orders.publish(
            Message(
                topic="orders.created",
                payload={"order_id": order_id, "amount": amount},
            )
        )

    while consumer.process(orders):
        pass

    print(
        json.dumps(
            {
                "queue": orders.name,
                "published": orders.published,
                "acknowledged": orders.acknowledged,
                "failed": orders.failed,
                "depth": orders.depth(),
            },
            indent=2,
        )
    )

    failures = MessageQueue("payments", max_size=10, max_attempts=3)
    failures.publish(
        Message(
            topic="payment.authorize",
            payload={"payment_id": "PAY-42", "always_fail": True},
        )
    )

    failing_consumer = Consumer("payment-worker", flaky_handler)

    # Retry messages after their small backoff window.
    while failures.depth() > 0:
        if not failing_consumer.process(failures):
            time.sleep(0.06)

    print(
        json.dumps(
            {
                "payment_queue_depth": failures.depth(),
                "dead_letters": failures.dead_letter_count(),
                "dead_letter_ids": [
                    item.message_id for item in failures.dead_letters()
                ],
            },
            indent=2,
        )
    )

    # Edge-case validation.
    try:
        orders.publish(Message(topic="", payload={}))
    except ValueError as exc:
        print(f"validation_error={exc}")

    # Performance characteristic:
    # publish and consume are O(1) for the common FIFO path. The current
    # delayed-message scan is O(n), which is acceptable for this compact
    # learning implementation but should use a priority queue in production.


if __name__ == "__main__":
    run_demo()
