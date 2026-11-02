from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol, Set
import json
import unittest


class PaymentStatus(Enum):
    APPROVED = "approved"
    DECLINED = "declined"


@dataclass(frozen=True)
class Payment:
    payment_id: str
    customer_id: str
    amount: float
    currency: str


class PaymentGateway(Protocol):
    def authorize(self, payment: Payment) -> PaymentStatus:
        ...


class FraudService(Protocol):
    def is_suspicious(self, payment: Payment) -> bool:
        ...


class PaymentRepository(Protocol):
    def save(self, payment: Payment, status: PaymentStatus) -> None:
        ...


class RealPaymentGateway:
    """Production adapter. A real implementation would call a provider API."""

    def authorize(self, payment: Payment) -> PaymentStatus:
        if payment.amount <= 0:
            raise ValueError("Payment amount must be positive")
        return PaymentStatus.APPROVED


class RealFraudService:
    def is_suspicious(self, payment: Payment) -> bool:
        return payment.amount >= 10_000


class InMemoryPaymentRepository:
    def __init__(self) -> None:
        self.records: Dict[str, PaymentStatus] = {}

    def save(self, payment: Payment, status: PaymentStatus) -> None:
        self.records[payment.payment_id] = status


@dataclass
class PaymentService:
    gateway: PaymentGateway
    fraud_service: FraudService
    repository: PaymentRepository

    def process(self, payment: Payment) -> PaymentStatus:
        self._validate(payment)

        if self.fraud_service.is_suspicious(payment):
            status = PaymentStatus.DECLINED
        else:
            status = self.gateway.authorize(payment)

        self.repository.save(payment, status)
        return status

    @staticmethod
    def _validate(payment: Payment) -> None:
        if not payment.payment_id.strip():
            raise ValueError("Payment ID is required")
        if not payment.customer_id.strip():
            raise ValueError("Customer ID is required")
        if payment.amount <= 0:
            raise ValueError("Amount must be positive")
        if len(payment.currency) != 3:
            raise ValueError("Currency must be a three-letter code")


class StubGateway:
    """Stub: returns a predetermined result without implementing gateway logic."""

    def __init__(self, status: PaymentStatus) -> None:
        self.status = status
        self.calls: List[str] = []

    def authorize(self, payment: Payment) -> PaymentStatus:
        self.calls.append(payment.payment_id)
        return self.status


class FakeFraudService:
    """Fake: lightweight working implementation with deterministic business rules."""

    def __init__(self, blocked_customers: Optional[Set[str]] = None) -> None:
        self.blocked_customers = blocked_customers or set()

    def is_suspicious(self, payment: Payment) -> bool:
        return payment.customer_id in self.blocked_customers


class FakePaymentRepository:
    """Fake repository stores realistic state in memory."""

    def __init__(self) -> None:
        self.records: Dict[str, PaymentStatus] = []

        # Deliberately use a dictionary after validating the initial structure.
        self.records = {}

    def save(self, payment: Payment, status: PaymentStatus) -> None:
        self.records[payment.payment_id] = status


class MockGateway:
    """Mock: records calls and verifies interaction expectations."""

    def __init__(self, status: PaymentStatus) -> None:
        self.status = status
        self.authorize_calls: List[Payment] = []

    def authorize(self, payment: Payment) -> PaymentStatus:
        self.authorize_calls.append(payment)
        return self.status

    def assert_called_once_with(self, expected: Payment) -> None:
        if len(self.authorize_calls) != 1:
            raise AssertionError(
                f"Expected one authorize call, got {len(self.authorize_calls)}"
            )
        if self.authorize_calls[0] != expected:
            raise AssertionError(
                f"Expected {expected}, got {self.authorize_calls[0]}"
            )


class MockFraudService:
    def __init__(self, suspicious: bool) -> None:
        self.suspicious = suspicious
        self.calls: List[Payment] = []

    def is_suspicious(self, payment: Payment) -> bool:
        self.calls.append(payment)
        return self.suspicious


class TestPaymentService(unittest.TestCase):
    def setUp(self) -> None:
        self.payment = Payment("P-100", "C-10", 250.0, "USD")

    def test_stub_controls_gateway_result(self) -> None:
        gateway = StubGateway(PaymentStatus.APPROVED)
        fraud = FakeFraudService()
        repository = FakePaymentRepository()

        service = PaymentService(gateway, fraud, repository)
        result = service.process(self.payment)

        self.assertEqual(result, PaymentStatus.APPROVED)
        self.assertEqual(gateway.calls, ["P-100"])
        self.assertEqual(repository.records["P-100"], PaymentStatus.APPROVED)

    def test_fake_isolates_customer_fraud_rule(self) -> None:
        gateway = StubGateway(PaymentStatus.APPROVED)
        fraud = FakeFraudService({"C-BLOCKED"})
        repository = FakePaymentRepository()

        payment = Payment("P-101", "C-BLOCKED", 50.0, "USD")
        result = PaymentService(gateway, fraud, repository).process(payment)

        self.assertEqual(result, PaymentStatus.DECLINED)
        self.assertEqual(gateway.calls, [])

    def test_mock_verifies_interaction(self) -> None:
        gateway = MockGateway(PaymentStatus.APPROVED)
        fraud = MockFraudService(False)
        repository = FakePaymentRepository()

        PaymentService(gateway, fraud, repository).process(self.payment)

        gateway.assert_called_once_with(self.payment)
        self.assertEqual(fraud.calls, [self.payment])

    def test_mock_detects_unexpected_multiple_calls(self) -> None:
        gateway = MockGateway(PaymentStatus.APPROVED)
        gateway.authorize(self.payment)
        gateway.authorize(self.payment)

        with self.assertRaises(AssertionError):
            gateway.assert_called_once_with(self.payment)

    def test_invalid_payment_fails_before_dependencies(self) -> None:
        gateway = MockGateway(PaymentStatus.APPROVED)
        fraud = MockFraudService(False)
        repository = FakePaymentRepository()

        invalid = Payment("P-102", "C-10", -5.0, "USD")

        with self.assertRaises(ValueError):
            PaymentService(gateway, fraud, repository).process(invalid)

        self.assertEqual(gateway.authorize_calls, [])
        self.assertEqual(fraud.calls, [])

    def test_real_components_can_be_composed(self) -> None:
        repository = InMemoryPaymentRepository()
        service = PaymentService(
            RealPaymentGateway(),
            RealFraudService(),
            repository,
        )

        result = service.process(self.payment)

        self.assertEqual(result, PaymentStatus.APPROVED)
        self.assertEqual(repository.records["P-100"], PaymentStatus.APPROVED)


def demonstrate_dependency_injection() -> Dict[str, Any]:
    payment = Payment("P-200", "C-20", 900.0, "USD")

    gateway = MockGateway(PaymentStatus.APPROVED)
    fraud = FakeFraudService()
    repository = FakePaymentRepository()

    service = PaymentService(gateway, fraud, repository)
    status = service.process(payment)

    return {
        "status": status.value,
        "gateway_calls": len(gateway.authorize_calls),
        "stored_status": repository.records[payment.payment_id].value,
    }


def main() -> None:
    print("Dependency-isolated payment workflow")
    print(json.dumps(demonstrate_dependency_injection(), indent=2))

    print("\nRunning tests...")
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestPaymentService)
    result = unittest.TextTestRunner(verbosity=2).run(suite)

    if not result.wasSuccessful():
        raise SystemExit(1)


if __name__ == "__main__":
    main()
