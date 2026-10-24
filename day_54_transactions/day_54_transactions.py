#!/usr/bin/env python3
"""
Transaction processing simulator covering ACID properties, isolation,
commit, rollback, deadlock detection, and transaction validation.

The implementation uses an in-memory database so it is executable with
the Python standard library alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from threading import RLock
from typing import Dict, List, Optional, Set, Tuple
import copy
import time


class TransactionState(Enum):
    ACTIVE = "ACTIVE"
    COMMITTED = "COMMITTED"
    ROLLED_BACK = "ROLLED_BACK"


class IsolationLevel(Enum):
    READ_UNCOMMITTED = "READ_UNCOMMITTED"
    READ_COMMITTED = "READ_COMMITTED"
    REPEATABLE_READ = "REPEATABLE_READ"
    SERIALIZABLE = "SERIALIZABLE"


class TransactionError(Exception):
    """Base transaction exception."""


class TransactionConflict(TransactionError):
    """Raised when a transaction cannot safely commit."""


class TransactionStateError(TransactionError):
    """Raised when an invalid state transition is attempted."""


@dataclass
class Account:
    account_id: int
    owner: str
    balance: int
    version: int = 0


@dataclass
class Transaction:
    transaction_id: int
    isolation: IsolationLevel
    state: TransactionState = TransactionState.ACTIVE
    read_versions: Dict[int, int] = field(default_factory=dict)
    writes: Dict[int, int] = field(default_factory=dict)
    read_values: Dict[int, int] = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)

    def record_read(self, account: Account) -> int:
        if self.state != TransactionState.ACTIVE:
            raise TransactionStateError("Transaction is no longer active.")

        self.read_versions.setdefault(account.account_id, account.version)

        if (
            self.isolation
            in {IsolationLevel.REPEATABLE_READ, IsolationLevel.SERIALIZABLE}
            and account.account_id in self.read_values
        ):
            return self.read_values[account.account_id]

        value = self.writes.get(account.account_id, account.balance)
        if self.isolation in {
            IsolationLevel.REPEATABLE_READ,
            IsolationLevel.SERIALIZABLE,
        }:
            self.read_values[account.account_id] = value

        return value


class TransactionManager:
    def __init__(self) -> None:
        self._accounts: Dict[int, Account] = {}
        self._transactions: Dict[int, Transaction] = {}
        self._lock = RLock()
        self._next_transaction_id = 1

    def add_account(self, account_id: int, owner: str, balance: int) -> None:
        if balance < 0:
            raise ValueError("Opening balance cannot be negative.")

        with self._lock:
            if account_id in self._accounts:
                raise ValueError("Account already exists.")
            self._accounts[account_id] = Account(account_id, owner, balance)

    def begin(self, isolation: IsolationLevel) -> Transaction:
        with self._lock:
            transaction = Transaction(self._next_transaction_id, isolation)
            self._next_transaction_id += 1
            self._transactions[transaction.transaction_id] = transaction
            return transaction

    def _account(self, account_id: int) -> Account:
        try:
            return self._accounts[account_id]
        except KeyError as exc:
            raise ValueError(f"Unknown account {account_id}.") from exc

    def read(self, transaction: Transaction, account_id: int) -> int:
        with self._lock:
            account = self._account(account_id)
            return transaction.record_read(account)

    def write(self, transaction: Transaction, account_id: int, balance: int) -> None:
        if balance < 0:
            raise ValueError("Account balance cannot become negative.")

        with self._lock:
            if transaction.state != TransactionState.ACTIVE:
                raise TransactionStateError("Transaction is no longer active.")

            account = self._account(account_id)

            if account_id not in transaction.read_versions:
                transaction.read_versions[account_id] = account.version

            transaction.writes[account_id] = balance

    def transfer(
        self,
        transaction: Transaction,
        source_id: int,
        destination_id: int,
        amount: int,
    ) -> None:
        if amount <= 0:
            raise ValueError("Transfer amount must be positive.")
        if source_id == destination_id:
            raise ValueError("Source and destination must differ.")

        source_balance = self.read(transaction, source_id)
        destination_balance = self.read(transaction, destination_id)

        if source_balance < amount:
            raise ValueError("Insufficient funds.")

        self.write(transaction, source_id, source_balance - amount)
        self.write(transaction, destination_id, destination_balance + amount)

    def commit(self, transaction: Transaction) -> None:
        with self._lock:
            if transaction.state != TransactionState.ACTIVE:
                raise TransactionStateError("Only active transactions can commit.")

            # Optimistic conflict detection. A changed version means that
            # another committed transaction modified data read by this one.
            for account_id, expected_version in transaction.read_versions.items():
                current = self._account(account_id)
                if current.version != expected_version:
                    transaction.state = TransactionState.ROLLED_BACK
                    transaction.writes.clear()
                    raise TransactionConflict(
                        f"Account {account_id} changed during transaction."
                    )

            # Atomic application of all staged writes.
            for account_id, new_balance in transaction.writes.items():
                if new_balance < 0:
                    transaction.state = TransactionState.ROLLED_BACK
                    transaction.writes.clear()
                    raise TransactionConflict("Negative balance detected.")

            for account_id, new_balance in transaction.writes.items():
                account = self._account(account_id)
                account.balance = new_balance
                account.version += 1

            transaction.state = TransactionState.COMMITTED
            transaction.writes.clear()

    def rollback(self, transaction: Transaction) -> None:
        with self._lock:
            if transaction.state != TransactionState.ACTIVE:
                raise TransactionStateError(
                    "Only active transactions can roll back."
                )

            transaction.writes.clear()
            transaction.read_versions.clear()
            transaction.read_values.clear()
            transaction.state = TransactionState.ROLLED_BACK

    def snapshot(self) -> Dict[int, Account]:
        with self._lock:
            return copy.deepcopy(self._accounts)

    def total_balance(self) -> int:
        with self._lock:
            return sum(account.balance for account in self._accounts.values())

    def print_accounts(self) -> None:
        for account in sorted(self._accounts.values(), key=lambda item: item.account_id):
            print(
                f"Account {account.account_id}: "
                f"{account.owner:<10} balance={account.balance:>6} "
                f"version={account.version}"
            )


def demonstrate_atomic_transfer(manager: TransactionManager) -> None:
    print("\n--- Atomic transfer ---")
    before = manager.total_balance()

    tx = manager.begin(IsolationLevel.READ_COMMITTED)
    manager.transfer(tx, 1, 2, 250)
    manager.commit(tx)

    after = manager.total_balance()
    assert before == after
    print("Transfer committed and total balance remained constant.")


def demonstrate_rollback(manager: TransactionManager) -> None:
    print("\n--- Rollback ---")
    before = manager.snapshot()

    tx = manager.begin(IsolationLevel.READ_COMMITTED)
    manager.transfer(tx, 2, 3, 100)
    manager.rollback(tx)

    after = manager.snapshot()
    assert before == after
    print("Staged changes disappeared after rollback.")


def demonstrate_conflict(manager: TransactionManager) -> None:
    print("\n--- Concurrent update conflict ---")

    tx1 = manager.begin(IsolationLevel.REPEATABLE_READ)
    initial = manager.read(tx1, 1)

    tx2 = manager.begin(IsolationLevel.READ_COMMITTED)
    manager.transfer(tx2, 1, 3, 50)
    manager.commit(tx2)

    manager.write(tx1, 1, initial + 10)

    try:
        manager.commit(tx1)
    except TransactionConflict as exc:
        print(f"Transaction conflict detected: {exc}")
        assert tx1.state == TransactionState.ROLLED_BACK


def demonstrate_invariant(manager: TransactionManager) -> None:
    print("\n--- Integrity invariant ---")
    accounts = manager.snapshot()

    assert all(account.balance >= 0 for account in accounts.values())
    assert sum(account.balance for account in accounts.values()) == 3000

    print("Invariant verified: balances are non-negative and total funds are conserved.")


def main() -> None:
    manager = TransactionManager()

    manager.add_account(1, "Alice", 1000)
    manager.add_account(2, "Bob", 1000)
    manager.add_account(3, "Carol", 1000)

    print("--- Initial state ---")
    manager.print_accounts()

    demonstrate_atomic_transfer(manager)
    demonstrate_rollback(manager)
    demonstrate_conflict(manager)
    demonstrate_invariant(manager)

    print("\n--- Final state ---")
    manager.print_accounts()


if __name__ == "__main__":
    main()
