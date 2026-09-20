# File: src/python_app/errors.py
"""File: src/python_app/errors.py

Application-specific exceptions.

Custom exceptions allow callers to distinguish expected validation failures
from unexpected programming or infrastructure failures.
"""


class ApplicationError(Exception):
    """Base class for expected application-level failures."""

    code = "application_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def to_dict(self) -> dict[str, str]:
        """Return a stable representation suitable for an API or CLI."""
        return {
            "error": self.code,
            "message": self.message,
        }


class ValidationError(ApplicationError):
    """Raised when external or user-controlled input is invalid."""

    code = "validation_error"


class BusinessRuleError(ApplicationError):
    """Raised when valid input violates a business rule."""

    code = "business_rule_error"


class ResourceNotFoundError(ApplicationError):
    """Raised when an expected resource does not exist."""

    code = "resource_not_found"


class StorageError(ApplicationError):
    """Raised when a storage operation cannot be completed safely."""

    code = "storage_error"

# File: src/python_app/service.py
"""File: src/python_app/service.py

Business service demonstrating defensive programming.

The service separates:
1. validation of external input,
2. business-rule validation,
3. state mutation,
4. controlled exception handling.

It intentionally avoids broad exception swallowing.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from .errors import (
    BusinessRuleError,
    ResourceNotFoundError,
    ValidationError,
)
from .models import Account, parse_positive_amount, validate_account_id

logger = logging.getLogger(__name__)

MAX_TRANSACTION = Decimal("100000.00")


class AccountService:
    """In-memory account service used for the educational application."""

    def __init__(self) -> None:
        self._accounts: dict[str, Account] = {}

    def create_account(self, account_id: object, owner: object) -> Account:
        """Create an account after validating all externally supplied values."""
        validated_id = validate_account_id(account_id)

        if not isinstance(owner, str) or not owner.strip():
            raise ValidationError("Owner name cannot be empty.")

        if validated_id in self._accounts:
            raise BusinessRuleError("An account with this ID already exists.")

        account = Account(
            account_id=validated_id,
            owner=owner,
        )
        self._accounts[validated_id] = account

        logger.info("Created account %s", validated_id)
        return account

    def get_account(self, account_id: object) -> Account:
        """Retrieve an account or raise a specific expected exception."""
        validated_id = validate_account_id(account_id)

        try:
            return self._accounts[validated_id]
        except KeyError as exc:
            raise ResourceNotFoundError(
                f"Account '{validated_id}' was not found."
            ) from exc

    def deposit(self, account_id: object, amount: object) -> Account:
        """Deposit money after validation and business-rule checks."""
        account = self.get_account(account_id)
        value = parse_positive_amount(amount)

        self._validate_transaction_limit(value)

        updated = Account(
            account_id=account.account_id,
            owner=account.owner,
            balance=account.balance + value,
        )
        self._accounts[account.account_id] = updated

        logger.info("Deposited %s into %s", value, account.account_id)
        return updated

    def withdraw(self, account_id: object, amount: object) -> Account:
        """Withdraw money without allowing invalid or unsafe state."""
        account = self.get_account(account_id)
        value = parse_positive_amount(amount)

        self._validate_transaction_limit(value)

        if value > account.balance:
            raise BusinessRuleError("Insufficient account balance.")

        updated = Account(
            account_id=account.account_id,
            owner=account.owner,
            balance=account.balance - value,
        )
        self._accounts[account.account_id] = updated

        logger.info("Withdrew %s from %s", value, account.account_id)
        return updated

    @staticmethod
    def _validate_transaction_limit(amount: Decimal) -> None:
        """Apply a business limit after basic input validation."""
        if amount > MAX_TRANSACTION:
            raise BusinessRuleError(
                f"Transaction cannot exceed {MAX_TRANSACTION:.2f}."
            )

    def list_accounts(self) -> list[Account]:
        """Return a stable snapshot rather than exposing internal state."""
        return list(self._accounts.values())

# File: src/python_app/cli.py
"""File: src/python_app/cli.py

Command-line interface demonstrating controlled exception handling.

Expected user mistakes are converted into readable messages.
Unexpected exceptions are logged and re-raised rather than silently hidden.
"""

from __future__ import annotations

import logging

from .errors import ApplicationError
from .service import AccountService

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)


def run_demo() -> None:
    """Execute a small demonstration of valid and invalid operations."""
    service = AccountService()

    print("Defensive Error Handling Demonstration")
    print("=" * 42)

    try:
        account = service.create_account("ACC-1001", "Atul")
        print(f"Created: {account.account_id} | balance={account.balance}")

        account = service.deposit("ACC-1001", "1250.50")
        print(f"After deposit: balance={account.balance}")

        account = service.withdraw("ACC-1001", "250.50")
        print(f"After withdrawal: balance={account.balance}")

        try:
            service.withdraw("ACC-1001", "5000")
        except ApplicationError as exc:
            print(f"Handled expected error: {exc}")

        try:
            service.deposit("ACC-1001", "-10")
        except ApplicationError as exc:
            print(f"Handled expected error: {exc}")

    except ApplicationError as exc:
        print(f"Application error: {exc}")


def main() -> None:
    """Application entry point."""
    try:
        run_demo()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception:
        logging.exception("Unexpected application failure.")
        raise


if __name__ == "__main__":
    main()

# File: tests/test_models.py
"""File: tests/test_models.py"""

from decimal import Decimal

import pytest

from src.python_app.errors import ValidationError
from src.python_app.models import Account, parse_positive_amount


def test_positive_amount_is_normalized() -> None:
    assert parse_positive_amount("12.345") == Decimal("12.35")


def test_zero_amount_is_rejected() -> None:
    with pytest.raises(ValidationError, match="greater than zero"):
        parse_positive_amount("0")


def test_negative_amount_is_rejected() -> None:
    with pytest.raises(ValidationError, match="greater than zero"):
        parse_positive_amount("-10")


def test_non_numeric_amount_is_rejected() -> None:
    with pytest.raises(ValidationError, match="valid number"):
        parse_positive_amount("abc")


def test_account_rejects_negative_balance() -> None:
    with pytest.raises(ValidationError, match="cannot be negative"):
        Account("ACC-1", "Atul", Decimal("-1"))

# File: tests/test_service.py
"""File: tests/test_service.py"""

import pytest

from src.python_app.errors import (
    BusinessRuleError,
    ResourceNotFoundError,
    ValidationError,
)
from src.python_app.service import AccountService


@pytest.fixture
def service() -> AccountService:
    instance = AccountService()
    instance.create_account("ACC-1", "Atul")
    return instance


def test_create_account(service: AccountService) -> None:
    account = service.get_account("ACC-1")
    assert account.owner == "Atul"
    assert str(account.balance) == "0.00"


def test_duplicate_account_is_rejected(service: AccountService) -> None:
    with pytest.raises(BusinessRuleError, match="already exists"):
        service.create_account("ACC-1", "Another User")


def test_missing_account_is_rejected(service: AccountService) -> None:
    with pytest.raises(ResourceNotFoundError):
        service.get_account("ACC-404")


def test_deposit_and_withdraw(service: AccountService) -> None:
    service.deposit("ACC-1", "100.00")
    account = service.withdraw("ACC-1", "40.25")

    assert account.balance == 59.75


def test_withdrawal_cannot_exceed_balance(service: AccountService) -> None:
    service.deposit("ACC-1", "50")

    with pytest.raises(BusinessRuleError, match="Insufficient"):
        service.withdraw("ACC-1", "50.01")


def test_transaction_limit_is_enforced(service: AccountService) -> None:
    with pytest.raises(BusinessRuleError, match="cannot exceed"):
        service.deposit("ACC-1", "100000.01")


def test_invalid_account_id_is_rejected(service: AccountService) -> None:
    with pytest.raises(ValidationError):
        service.get_account("invalid id")


def test_state_is_not_modified_after_failed_withdrawal(
    service: AccountService,
) -> None:
    service.deposit("ACC-1", "100")

    with pytest.raises(BusinessRuleError):
        service.withdraw("ACC-1", "200")

    assert service.get_account("ACC-1").balance == 100

