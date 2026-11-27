#!/usr/bin/env python3
"""
Distributed Transactions: Two-Phase Commit and Sagas

Simulates distributed transaction coordination using:
1. Two-Phase Commit (2PC)
2. Saga orchestration
3. Participant state management
4. Commit and rollback decisions
5. Compensating transactions
6. Failure injection and recovery
7. Transaction event auditing

Requires Python 3.10+.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("distributed_transactions")


class TransactionError(Exception):
    pass


class ValidationError(TransactionError):
    pass


class ParticipantError(TransactionError):
    pass


class TransactionState(Enum):
    CREATED = "CREATED"
    PREPARING = "PREPARING"
    PREPARED = "PREPARED"
    COMMITTING = "COMMITTING"
    COMMITTED = "COMMITTED"
    ABORTING = "ABORTING"
    ABORTED = "ABORTED"
    COMPENSATING = "COMPENSATING"
    COMPENSATED = "COMPENSATED"
    FAILED = "FAILED"
    IN_DOUBT = "IN_DOUBT"


class ParticipantState(Enum):
    ACTIVE = "ACTIVE"
    PREPARED = "PREPARED"
    COMMITTED = "COMMITTED"
    ABORTED = "ABORTED"


class TransactionMode(Enum):
    TWO_PHASE_COMMIT = "2PC"
    SAGA = "SAGA"


@dataclass
class Event:
    transaction_id: str
    action: str
    participant: str
    details: str


@dataclass
class TransactionLog:
    transaction_id: str
    events: list[Event] = field(default_factory=list)

    def record(self, action: str, participant: str, details: str) -> None:
        event = Event(
            self.transaction_id,
            action,
            participant,
            details,
        )
        self.events.append(event)
        logger.info(
            "%s | %s | %s",
            action,
            participant,
            details,
        )


class Participant:
    """
    Represents a transactional service.

    The participant keeps its own local state. In a real system,
    these operations must be persisted in a local database.
    """

    def __init__(
        self,
        name: str,
        prepare_rule: Optional[Callable[[], bool]] = None,
        fail_commit: bool = False,
    ):
        self.name = name
        self.state = ParticipantState.ACTIVE
        self.prepare_rule = prepare_rule or (lambda: True)
        self.fail_commit = fail_commit
        self.operations: list[str] = []

    def prepare(self) -> bool:
        if self.state != ParticipantState.ACTIVE:
            raise ParticipantError(
                f"{self.name}: invalid prepare state"
            )

        if not self.prepare_rule():
            return False

        self.state = ParticipantState.PREPARED
        self.operations.append("PREPARE")
        return True

    def commit(self) -> None:
        if self.state != ParticipantState.PREPARED:
            raise ParticipantError(
                f"{self.name}: participant not prepared"
            )

        if self.fail_commit:
            raise ParticipantError(
                f"{self.name}: simulated commit failure"
            )

        self.state = ParticipantState.COMMITTED
        self.operations.append("COMMIT")

    def abort(self) -> None:
        if self.state == ParticipantState.COMMITTED:
            raise ParticipantError(
                f"{self.name}: cannot abort committed work"
            )

        if self.state == ParticipantState.ABORTED:
            return

        self.state = ParticipantState.ABORTED
        self.operations.append("ABORT")

    def execute(self) -> None:
        """Execute one local saga transaction."""
        if self.state != ParticipantState.ACTIVE:
            raise ParticipantError(
                f"{self.name}: cannot execute in current state"
            )

        self.operations.append("EXECUTE")
        self.state = ParticipantState.COMMITTED

    def compensate(self) -> None:
        """
        Apply a business-level reversal.

        Compensation is not a database rollback. It is a new
        operation that attempts to reverse a previous effect.
        """
        if self.state != ParticipantState.COMMITTED:
            raise ParticipantError(
                f"{self.name}: no committed operation to compensate"
            )

        self.operations.append("COMPENSATE")
        self.state = ParticipantState.ABORTED


@dataclass
class DistributedTransaction:
    participants: list[Participant]
    mode: TransactionMode
    transaction_id: str = field(
        default_factory=lambda: str(uuid.uuid4())
    )
    state: TransactionState = TransactionState.CREATED
    log: TransactionLog = field(init=False)

    def __post_init__(self) -> None:
        self.log = TransactionLog(self.transaction_id)

        if not self.participants:
            raise ValidationError(
                "At least one participant is required"
            )

        names = [p.name for p in self.participants]

        if len(names) != len(set(names)):
            raise ValidationError(
                "Participant names must be unique"
            )

    def transition(self, new_state: TransactionState) -> None:
        self.state = new_state
        self.log.record(
            "STATE_CHANGE",
            "COORDINATOR",
            new_state.value,
        )

    def execute_2pc(self) -> bool:
        """
        Two-phase commit.

        Phase 1: Prepare every participant.
        Phase 2: Commit all participants or abort prepared work.

        A production coordinator must persist its decision before
        broadcasting commit or abort.
        """

        if self.state != TransactionState.CREATED:
            raise TransactionError("Transaction already started")

        self.transition(TransactionState.PREPARING)

        prepared: list[Participant] = []

        try:
            for participant in self.participants:
                self.log.record(
                    "PREPARE_REQUEST",
                    participant.name,
                    "Requesting readiness",
                )

                if not participant.prepare():
                    self.log.record(
                        "VOTE_NO",
                        participant.name,
                        "Participant rejected transaction",
                    )
                    raise TransactionError(
                        f"{participant.name} voted NO"
                    )

                prepared.append(participant)

                self.log.record(
                    "VOTE_YES",
                    participant.name,
                    "Participant prepared successfully",
                )

            self.transition(TransactionState.PREPARED)

        except Exception as exc:
            self.log.record(
                "PREPARE_FAILURE",
                "COORDINATOR",
                str(exc),
            )

            self.transition(TransactionState.ABORTING)

            for participant in prepared:
                participant.abort()

            for participant in self.participants:
                if participant.state == ParticipantState.ACTIVE:
                    participant.abort()

            self.transition(TransactionState.ABORTED)
            return False

        # The coordinator records its global decision before
        # sending commit messages.
        self.transition(TransactionState.COMMITTING)

        try:
            for participant in self.participants:
                participant.commit()
                self.log.record(
                    "COMMIT_ACK",
                    participant.name,
                    "Local transaction committed",
                )

        except Exception as exc:
            # A failed commit acknowledgement does not mean that
            # already committed participants can be rolled back.
            self.log.record(
                "COMMIT_UNCERTAIN",
                "COORDINATOR",
                str(exc),
            )
            self.transition(TransactionState.IN_DOUBT)
            return False

        self.transition(TransactionState.COMMITTED)
        return True

    def execute_saga(self) -> bool:
        """
        Saga orchestration.

        Each successful local transaction is recorded.
        On failure, completed transactions are compensated
        in reverse execution order.
        """

        if self.state != TransactionState.CREATED:
            raise TransactionError("Transaction already started")

        completed: list[Participant] = []

        try:
            for participant in self.participants:
                participant.execute()
                completed.append(participant)

                self.log.record(
                    "LOCAL_COMMIT",
                    participant.name,
                    "Saga step completed",
                )

            self.transition(TransactionState.COMMITTED)
            return True

        except Exception as exc:
            self.log.record(
                "SAGA_FAILURE",
                "COORDINATOR",
                str(exc),
            )

            self.transition(TransactionState.COMPENSATING)

            compensation_failed = False

            for participant in reversed(completed):
                try:
                    participant.compensate()

                    self.log.record(
                        "COMPENSATION_SUCCESS",
                        participant.name,
                        "Business operation reversed",
                    )

                except Exception as compensation_error:
                    compensation_failed = True

                    self.log.record(
                        "COMPENSATION_FAILURE",
                        participant.name,
                        str(compensation_error),
                    )

            if compensation_failed:
                self.transition(TransactionState.FAILED)
            else:
                self.transition(TransactionState.COMPENSATED)

            return False

    def report(self) -> None:
        print("\nTRANSACTION REPORT")
        print("=" * 55)
        print("ID:", self.transaction_id)
        print("Mode:", self.mode.value)
        print("State:", self.state.value)

        for participant in self.participants:
            print(
                participant.name,
                "|",
                participant.state.value,
                "|",
                participant.operations,
            )

        print("\nAUDIT EVENTS")

        for event in self.log.events:
            print(
                event.action,
                "|",
                event.participant,
                "|",
                event.details,
            )


class TransactionFactory:
    @staticmethod
    def create_2pc(
        participants: list[Participant],
    ) -> DistributedTransaction:
        return DistributedTransaction(
            participants,
            TransactionMode.TWO_PHASE_COMMIT,
        )

    @staticmethod
    def create_saga(
        participants: list[Participant],
    ) -> DistributedTransaction:
        return DistributedTransaction(
            participants,
            TransactionMode.SAGA,
        )


def demonstrate_2pc_success() -> None:
    print("\nCASE 1: SUCCESSFUL TWO-PHASE COMMIT")

    transaction = TransactionFactory.create_2pc([
        Participant("InventoryService"),
        Participant("PaymentService"),
        Participant("OrderService"),
    ])

    assert transaction.execute_2pc()
    assert transaction.state == TransactionState.COMMITTED

    transaction.report()


def demonstrate_2pc_rejection() -> None:
    print("\nCASE 2: PARTICIPANT REJECTS PREPARE")

    transaction = TransactionFactory.create_2pc([
        Participant("InventoryService"),
        Participant(
            "PaymentService",
            prepare_rule=lambda: False,
        ),
        Participant("OrderService"),
    ])

    assert not transaction.execute_2pc()
    assert transaction.state == TransactionState.ABORTED

    transaction.report()


def demonstrate_2pc_uncertain_commit() -> None:
    print("\nCASE 3: UNCERTAIN COMMIT OUTCOME")

    transaction = TransactionFactory.create_2pc([
        Participant("InventoryService"),
        Participant("PaymentService", fail_commit=True),
    ])

    assert not transaction.execute_2pc()
    assert transaction.state == TransactionState.IN_DOUBT

    transaction.report()


def demonstrate_saga_success() -> None:
    print("\nCASE 4: SUCCESSFUL SAGA")

    transaction = TransactionFactory.create_saga([
        Participant("ReserveInventory"),
        Participant("ChargePayment"),
        Participant("CreateShipment"),
    ])

    assert transaction.execute_saga()
    transaction.report()


def demonstrate_saga_compensation() -> None:
    print("\nCASE 5: SAGA COMPENSATION")

    transaction = TransactionFactory.create_saga([
        Participant("ReserveInventory"),
        Participant("ChargePayment"),
        Participant(
            "CreateShipment",
            prepare_rule=lambda: False,
        ),
    ])

    # The third participant rejects execution in this simulation.
    original_execute = transaction.participants[2].execute

    def failing_execute() -> None:
        raise ParticipantError("Shipping provider unavailable")

    transaction.participants[2].execute = failing_execute

    assert not transaction.execute_saga()
    assert transaction.state == TransactionState.COMPENSATED

    transaction.report()


def run_tests() -> None:
    assert ParticipantState.ACTIVE.value == "ACTIVE"

    # Empty transactions are rejected.
    try:
        TransactionFactory.create_2pc([])
        raise AssertionError("Empty transaction was accepted")
    except ValidationError:
        pass

    # Duplicate participant names are rejected.
    try:
        TransactionFactory.create_saga([
            Participant("Payment"),
            Participant("Payment"),
        ])
        raise AssertionError("Duplicate names were accepted")
    except ValidationError:
        pass

    print("\nAll validation tests passed.")


def main() -> None:
    demonstrate_2pc_success()
    demonstrate_2pc_rejection()
    demonstrate_2pc_uncertain_commit()
    demonstrate_saga_success()
    demonstrate_saga_compensation()
    run_tests()


if __name__ == "__main__":
    main()
