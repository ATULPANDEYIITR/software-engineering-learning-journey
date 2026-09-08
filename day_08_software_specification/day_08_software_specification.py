"""
Software Specification Tutorial
Topics:
- Software Requirements Specification (SRS)
- Acceptance Criteria
- Requirement Traceability

This self-contained script teaches software specification concepts from beginner
to advanced level using executable Python examples.

The examples model a simple online banking transfer system because it contains
functional requirements, business rules, security constraints, acceptance
criteria, tests, defects, and traceability relationships.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Set, Tuple
import re


# =============================================================================
# 1. FUNDAMENTAL CONCEPTS
# =============================================================================

# A software specification describes what a system must do and the constraints
# under which it must operate.
#
# Important distinction:
#
# Requirement:
#     A needed capability, behavior, quality, or constraint.
#
# Specification:
#     A precise description of requirements that can be reviewed and verified.
#
# Implementation:
#     The code, configuration, infrastructure, and other artifacts used to
#     satisfy the specification.
#
# Test:
#     Evidence used to verify whether an implementation satisfies requirements.


class RequirementType(Enum):
    """Classification of software requirements."""

    FUNCTIONAL = "Functional"
    NON_FUNCTIONAL = "Non-Functional"
    BUSINESS = "Business"
    INTERFACE = "Interface"
    DATA = "Data"
    SECURITY = "Security"
    CONSTRAINT = "Constraint"


class RequirementPriority(Enum):
    """A simple MoSCoW-style priority classification."""

    MUST = "Must Have"
    SHOULD = "Should Have"
    COULD = "Could Have"
    WONT = "Won't Have for Current Scope"


class RequirementStatus(Enum):
    """Lifecycle status of a requirement."""

    DRAFT = "Draft"
    REVIEWED = "Reviewed"
    APPROVED = "Approved"
    IMPLEMENTED = "Implemented"
    VERIFIED = "Verified"
    REJECTED = "Rejected"


class TestStatus(Enum):
    """Possible execution results for a test case."""

    NOT_RUN = "Not Run"
    PASSED = "Passed"
    FAILED = "Failed"
    BLOCKED = "Blocked"


class DefectSeverity(Enum):
    """Severity classification for defects."""

    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


# =============================================================================
# 2. WHAT MAKES A GOOD REQUIREMENT?
# =============================================================================

# Strong requirements are commonly expected to be:
#
# - Clear
# - Unambiguous
# - Complete
# - Consistent
# - Feasible
# - Necessary
# - Verifiable or testable
# - Traceable
# - Atomic, where practical
#
# Weak:
#     "The system should be fast."
#
# Better:
#     "The system shall display the account balance within 2 seconds for
#      95 percent of requests under normal operating load."
#
# Weak:
#     "The system should have strong security."
#
# Better:
#     "The system shall lock an account for 15 minutes after five consecutive
#      unsuccessful authentication attempts."


AMBIGUOUS_WORDS = {
    "fast",
    "quick",
    "easy",
    "user-friendly",
    "efficient",
    "robust",
    "sufficient",
    "appropriate",
    "high-performance",
    "secure",
    "reliable",
    "simple",
}


def find_ambiguous_language(text: str) -> List[str]:
    """
    Detect selected words that often make a requirement difficult to verify.

    This is not a complete natural-language validator. A word can be acceptable
    in context, but its presence should trigger a review.
    """
    words = re.findall(r"[A-Za-z-]+", text.lower())
    return sorted(set(words) & AMBIGUOUS_WORDS)


def demonstrate_requirement_quality() -> None:
    print("\n" + "=" * 80)
    print("REQUIREMENT QUALITY")
    print("=" * 80)

    weak_requirement = "The application shall provide a fast and secure transfer process."
    strong_requirement = (
        "The application shall complete transfer validation within 2 seconds "
        "for 95 percent of requests and shall require authenticated users."
    )

    print("Weak requirement:")
    print(" ", weak_requirement)
    print("Potentially ambiguous words:")
    print(" ", find_ambiguous_language(weak_requirement))

    print("\nImproved requirement:")
    print(" ", strong_requirement)
    print("Potentially ambiguous words:")
    print(" ", find_ambiguous_language(strong_requirement))


# =============================================================================
# 3. SOFTWARE REQUIREMENTS SPECIFICATION (SRS)
# =============================================================================

# An SRS is a structured specification of what a software system is expected to
# do. Its exact structure depends on the organization, methodology, domain, and
# regulatory environment.
#
# A practical SRS may include:
#
# 1. Purpose and scope
# 2. Stakeholders
# 3. Definitions and terminology
# 4. System overview
# 5. Functional requirements
# 6. Non-functional requirements
# 7. Business rules
# 8. Data requirements
# 9. Interface requirements
# 10. Security requirements
# 11. Constraints and assumptions
# 12. Dependencies
# 13. Acceptance criteria
# 14. Traceability information


@dataclass
class Requirement:
    """
    Represents a structured requirement.

    Requirement IDs should be stable and unique. Stable IDs are important
    because tests, design documents, defects, and release evidence may all
    reference them.
    """

    requirement_id: str
    title: str
    description: str
    requirement_type: RequirementType
    priority: RequirementPriority
    status: RequirementStatus = RequirementStatus.DRAFT
    source: str = ""
    rationale: str = ""
    assumptions: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)

    def validate(self) -> List[str]:
        """Return specification quality problems found in this requirement."""
        errors: List[str] = []

        if not self.requirement_id.strip():
            errors.append("Requirement ID is required.")

        if not self.title.strip():
            errors.append("Requirement title is required.")

        if not self.description.strip():
            errors.append("Requirement description is required.")

        ambiguous = find_ambiguous_language(self.description)
        if ambiguous:
            errors.append(
                "Potentially ambiguous terms require clarification: "
                + ", ".join(ambiguous)
            )

        return errors


@dataclass
class SRS:
    """A simplified Software Requirements Specification document."""

    document_id: str
    system_name: str
    version: str
    purpose: str
    scope: str
    requirements: Dict[str, Requirement] = field(default_factory=dict)
    assumptions: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)

    def add_requirement(self, requirement: Requirement) -> None:
        if requirement.requirement_id in self.requirements:
            raise ValueError(
                f"Duplicate requirement ID: {requirement.requirement_id}"
            )

        self.requirements[requirement.requirement_id] = requirement

    def validate(self) -> Dict[str, List[str]]:
        """Validate all requirements and return only requirements with issues."""
        issues: Dict[str, List[str]] = {}

        for requirement_id, requirement in self.requirements.items():
            requirement_errors = requirement.validate()
            if requirement_errors:
                issues[requirement_id] = requirement_errors

        return issues


def build_example_srs() -> SRS:
    """Create an example SRS for an online banking transfer feature."""

    srs = SRS(
        document_id="SRS-BANK-001",
        system_name="Online Banking Transfer System",
        version="1.0",
        purpose=(
            "Specify requirements for domestic account-to-account transfers."
        ),
        scope=(
            "The system supports authenticated customers transferring funds "
            "between eligible accounts."
        ),
        assumptions=[
            "The banking identity service is available.",
            "Account balances are maintained by the core banking system.",
        ],
        constraints=[
            "All monetary values must use decimal arithmetic.",
            "Transfer authorization must require an authenticated user.",
        ],
    )

    srs.add_requirement(
        Requirement(
            requirement_id="FR-001",
            title="Initiate Transfer",
            description=(
                "The system shall allow an authenticated customer to initiate "
                "a transfer by specifying a source account, destination "
                "account, and amount greater than zero."
            ),
            requirement_type=RequirementType.FUNCTIONAL,
            priority=RequirementPriority.MUST,
            status=RequirementStatus.APPROVED,
            source="Product Owner",
        )
    )

    srs.add_requirement(
        Requirement(
            requirement_id="FR-002",
            title="Reject Insufficient Balance",
            description=(
                "The system shall reject a transfer when the available balance "
                "of the source account is lower than the requested amount."
            ),
            requirement_type=RequirementType.FUNCTIONAL,
            priority=RequirementPriority.MUST,
            status=RequirementStatus.APPROVED,
            source="Risk and Compliance",
        )
    )

    srs.add_requirement(
        Requirement(
            requirement_id="BR-001",
            title="Daily Transfer Limit",
            description=(
                "The total value of transfers initiated by a customer during "
                "one calendar day shall not exceed 100000 currency units."
            ),
            requirement_type=RequirementType.BUSINESS,
            priority=RequirementPriority.MUST,
            status=RequirementStatus.APPROVED,
            source="Banking Policy",
        )
    )

    srs.add_requirement(
        Requirement(
            requirement_id="SEC-001",
            title="Authenticated Access",
            description=(
                "The system shall reject transfer requests from unauthenticated "
                "users."
            ),
            requirement_type=RequirementType.SECURITY,
            priority=RequirementPriority.MUST,
            status=RequirementStatus.APPROVED,
            source="Security Policy",
        )
    )

    srs.add_requirement(
        Requirement(
            requirement_id="NFR-001",
            title="Transfer Validation Performance",
            description=(
                "The system shall complete transfer validation within 2 seconds "
                "for at least 95 percent of requests under normal operating load."
            ),
            requirement_type=RequirementType.NON_FUNCTIONAL,
            priority=RequirementPriority.SHOULD,
            status=RequirementStatus.APPROVED,
            source="Architecture Team",
        )
    )

    return srs


# =============================================================================
# 4. FUNCTIONAL VS NON-FUNCTIONAL REQUIREMENTS
# =============================================================================

# Functional requirements define WHAT the system does.
#
# Examples:
# - Authenticate a user.
# - Calculate a total.
# - Create an invoice.
# - Transfer funds.
#
# Non-functional requirements define qualities, constraints, or conditions
# under which the system operates.
#
# Examples:
# - Performance
# - Availability
# - Scalability
# - Reliability
# - Security
# - Accessibility
# - Maintainability
# - Compatibility
#
# Important subtlety:
#
# Security can be represented as a non-functional quality attribute, but many
# organizations classify security requirements separately because of their
# importance, ownership, compliance obligations, and verification methods.


# =============================================================================
# 5. USER STORIES AND ACCEPTANCE CRITERIA
# =============================================================================

# A user story is a lightweight requirement expression frequently used in agile
# development.
#
# Common format:
#
# As a <user role>,
# I want <capability>,
# so that <business value>.
#
# Example:
#
# As an authenticated customer,
# I want to transfer money between accounts,
# so that I can manage my funds digitally.
#
# A user story does not automatically provide enough precision for development
# and testing. Acceptance criteria define observable conditions that determine
# whether the story is acceptable.


@dataclass
class UserStory:
    """Represents a simplified agile user story."""

    story_id: str
    role: str
    capability: str
    benefit: str

    def render(self) -> str:
        return (
            f"As a {self.role}, I want {self.capability}, "
            f"so that {self.benefit}."
        )


class AcceptanceCriterionType(Enum):
    """Different ways to express acceptance criteria."""

    GIVEN_WHEN_THEN = "Given-When-Then"
    RULE = "Business Rule"
    EXAMPLE = "Example"


@dataclass
class AcceptanceCriterion:
    """
    A condition used to determine whether a requirement or story is accepted.

    A strong acceptance criterion should be observable and testable.
    """

    criterion_id: str
    requirement_id: str
    description: str
    criterion_type: AcceptanceCriterionType
    given: Optional[str] = None
    when: Optional[str] = None
    then: Optional[str] = None

    def render(self) -> str:
        if (
            self.criterion_type == AcceptanceCriterionType.GIVEN_WHEN_THEN
            and self.given
            and self.when
            and self.then
        ):
            return (
                f"Given {self.given}, "
                f"When {self.when}, "
                f"Then {self.then}."
            )

        return self.description


def build_acceptance_criteria() -> List[AcceptanceCriterion]:
    return [
        AcceptanceCriterion(
            criterion_id="AC-001",
            requirement_id="FR-001",
            description="Authenticated users can submit valid transfers.",
            criterion_type=AcceptanceCriterionType.GIVEN_WHEN_THEN,
            given="an authenticated customer has selected two eligible accounts",
            when="the customer enters an amount greater than zero",
            then="the system accepts the transfer request for validation",
        ),
        AcceptanceCriterion(
            criterion_id="AC-002",
            requirement_id="FR-002",
            description="Transfers with insufficient funds are rejected.",
            criterion_type=AcceptanceCriterionType.GIVEN_WHEN_THEN,
            given="the source account has an available balance of 500",
            when="the customer requests a transfer of 600",
            then="the system rejects the transfer and leaves account balances unchanged",
        ),
        AcceptanceCriterion(
            criterion_id="AC-003",
            requirement_id="BR-001",
            description="The daily transfer limit is enforced.",
            criterion_type=AcceptanceCriterionType.GIVEN_WHEN_THEN,
            given="the customer has already transferred 90000 today",
            when="the customer requests a transfer of 20000",
            then="the system rejects the transfer because the daily limit would be exceeded",
        ),
        AcceptanceCriterion(
            criterion_id="AC-004",
            requirement_id="SEC-001",
            description="Unauthenticated users cannot transfer funds.",
            criterion_type=AcceptanceCriterionType.GIVEN_WHEN_THEN,
            given="a transfer request is received without an authenticated user",
            when="the request is submitted",
            then="the system rejects the request before modifying any account balance",
        ),
    ]


# =============================================================================
# 6. ACCEPTANCE CRITERIA VS REQUIREMENTS
# =============================================================================

# Requirement:
#     States what the system must achieve.
#
# Acceptance criterion:
#     Defines specific observable conditions used to determine whether the
#     requirement is satisfied.
#
# Example:
#
# Requirement:
#     "The system shall reject transfers with insufficient funds."
#
# Acceptance criterion:
#     Given an account balance of 500,
#     When a transfer of 600 is requested,
#     Then the transfer is rejected and the balance remains 500.
#
# The requirement provides the rule. The acceptance criterion provides a
# concrete verification condition.


# =============================================================================
# 7. DOMAIN IMPLEMENTATION USED FOR SPECIFICATION EXAMPLES
# =============================================================================


@dataclass
class Account:
    """A simplified bank account."""

    account_id: str
    owner_id: str
    balance: int

    def __post_init__(self) -> None:
        if self.balance < 0:
            raise ValueError("Initial balance cannot be negative.")


@dataclass
class TransferRequest:
    """Input required to request a transfer."""

    user_id: Optional[str]
    source_account_id: str
    destination_account_id: str
    amount: int


@dataclass
class TransferResult:
    """Result of transfer processing."""

    accepted: bool
    message: str
    source_balance: Optional[int] = None
    destination_balance: Optional[int] = None


class TransferError(Exception):
    """Base exception for transfer processing errors."""


class AuthenticationError(TransferError):
    """Raised when authentication requirements are not satisfied."""


class ValidationError(TransferError):
    """Raised when transfer input violates validation rules."""


class InsufficientFundsError(TransferError):
    """Raised when source funds are insufficient."""


class DailyLimitExceededError(TransferError):
    """Raised when the daily transfer limit would be exceeded."""


class AccountOwnershipError(TransferError):
    """Raised when a user attempts to transfer from an unauthorized account."""


class TransferService:
    """
    Simplified implementation for demonstrating how specifications become code.

    This implementation intentionally uses integer currency units for simplicity.
    Production financial systems should use carefully designed decimal money
    representations and explicit currency handling.
    """

    DAILY_TRANSFER_LIMIT = 100_000

    def __init__(self, accounts: Dict[str, Account]) -> None:
        self.accounts = accounts
        self.daily_transferred: Dict[str, int] = {}

    def transfer(self, request: TransferRequest) -> TransferResult:
        """
        Process a transfer while enforcing selected requirements.

        Requirements implemented:
        - SEC-001: User must be authenticated.
        - FR-001: Amount must be positive and accounts must be valid.
        - FR-002: Source balance must be sufficient.
        - BR-001: Daily limit must not be exceeded.
        """

        # SEC-001: Authentication validation.
        if not request.user_id:
            raise AuthenticationError(
                "Transfer rejected because the user is not authenticated."
            )

        # Input validation.
        if request.amount <= 0:
            raise ValidationError(
                "Transfer amount must be greater than zero."
            )

        if request.source_account_id == request.destination_account_id:
            raise ValidationError(
                "Source and destination accounts must be different."
            )

        source = self.accounts.get(request.source_account_id)
        destination = self.accounts.get(request.destination_account_id)

        if source is None:
            raise ValidationError("Source account does not exist.")

        if destination is None:
            raise ValidationError("Destination account does not exist.")

        # Authorization and ownership validation.
        if source.owner_id != request.user_id:
            raise AccountOwnershipError(
                "Authenticated user does not own the source account."
            )

        # FR-002: Prevent overdrawing the account.
        if source.balance < request.amount:
            raise InsufficientFundsError(
                "Transfer rejected because the source account has insufficient funds."
            )

        # BR-001: Enforce the daily transfer limit.
        transferred_today = self.daily_transferred.get(request.user_id, 0)

        if transferred_today + request.amount > self.DAILY_TRANSFER_LIMIT:
            raise DailyLimitExceededError(
                "Transfer rejected because the daily transfer limit would be exceeded."
            )

        # A production implementation would require transaction boundaries.
        # Both balance updates must succeed together or be rolled back.
        source.balance -= request.amount
        destination.balance += request.amount

        self.daily_transferred[request.user_id] = (
            transferred_today + request.amount
        )

        return TransferResult(
            accepted=True,
            message="Transfer completed successfully.",
            source_balance=source.balance,
            destination_balance=destination.balance,
        )


def demonstrate_transfer_service() -> None:
    print("\n" + "=" * 80)
    print("IMPLEMENTATION FROM REQUIREMENTS")
    print("=" * 80)

    accounts = {
        "A-100": Account(
            account_id="A-100",
            owner_id="USER-1",
            balance=50_000,
        ),
        "A-200": Account(
            account_id="A-200",
            owner_id="USER-2",
            balance=10_000,
        ),
    }

    service = TransferService(accounts)

    valid_request = TransferRequest(
        user_id="USER-1",
        source_account_id="A-100",
        destination_account_id="A-200",
        amount=10_000,
    )

    result = service.transfer(valid_request)
    print(result)

    invalid_request = TransferRequest(
        user_id="USER-1",
        source_account_id="A-100",
        destination_account_id="A-200",
        amount=100_000,
    )

    try:
        service.transfer(invalid_request)
    except TransferError as error:
        print("Expected error:", error)


# =============================================================================
# 8. ACCEPTANCE TESTING
# =============================================================================

# Acceptance testing evaluates whether the system satisfies agreed acceptance
# criteria. The exact participants vary by organization and may include:
#
# - Product owners
# - Business stakeholders
# - Customers
# - Quality assurance teams
# - Domain experts
#
# Acceptance testing differs from implementation-focused unit testing.
#
# Unit testing asks:
#     Does this function or component behave correctly?
#
# Acceptance testing asks:
#     Does the implemented system satisfy agreed business expectations?


@dataclass
class TestCase:
    """Represents a test case linked to specification artifacts."""

    test_id: str
    title: str
    requirement_ids: List[str]
    acceptance_criterion_ids: List[str]
    execute: Callable[[], None]
    status: TestStatus = TestStatus.NOT_RUN
    failure_message: str = ""

    def run(self) -> TestStatus:
        """Execute the test and store the result."""
        try:
            self.execute()
            self.status = TestStatus.PASSED
            self.failure_message = ""
        except AssertionError as error:
            self.status = TestStatus.FAILED
            self.failure_message = str(error)
        except Exception as error:
            self.status = TestStatus.FAILED
            self.failure_message = (
                f"Unexpected exception: {type(error).__name__}: {error}"
            )

        return self.status


def assert_raises(
    expected_exception: type[Exception],
    function: Callable[[], object],
) -> None:
    """
    Minimal assertion helper demonstrating exception expectations without
    requiring an external testing framework.
    """
    try:
        function()
    except expected_exception:
        return
    except Exception as error:
        raise AssertionError(
            f"Expected {expected_exception.__name__}, "
            f"but received {type(error).__name__}."
        ) from error

    raise AssertionError(
        f"Expected {expected_exception.__name__}, but no exception was raised."
    )


def create_test_cases() -> List[TestCase]:
    """Create executable tests mapped to requirements and criteria."""

    def build_service() -> TransferService:
        return TransferService(
            {
                "A-100": Account("A-100", "USER-1", 1_000),
                "A-200": Account("A-200", "USER-2", 500),
            }
        )

    def test_valid_transfer() -> None:
        service = build_service()

        result = service.transfer(
            TransferRequest(
                user_id="USER-1",
                source_account_id="A-100",
                destination_account_id="A-200",
                amount=300,
            )
        )

        assert result.accepted is True
        assert service.accounts["A-100"].balance == 700
        assert service.accounts["A-200"].balance == 800

    def test_insufficient_funds() -> None:
        service = build_service()

        original_source = service.accounts["A-100"].balance
        original_destination = service.accounts["A-200"].balance

        assert_raises(
            InsufficientFundsError,
            lambda: service.transfer(
                TransferRequest(
                    user_id="USER-1",
                    source_account_id="A-100",
                    destination_account_id="A-200",
                    amount=2_000,
                )
            ),
        )

        # Important acceptance behavior: rejection must not partially modify data.
        assert service.accounts["A-100"].balance == original_source
        assert service.accounts["A-200"].balance == original_destination

    def test_unauthenticated_transfer() -> None:
        service = build_service()

        assert_raises(
            AuthenticationError,
            lambda: service.transfer(
                TransferRequest(
                    user_id=None,
                    source_account_id="A-100",
                    destination_account_id="A-200",
                    amount=100,
                )
            ),
        )

    def test_zero_amount() -> None:
        service = build_service()

        assert_raises(
            ValidationError,
            lambda: service.transfer(
                TransferRequest(
                    user_id="USER-1",
                    source_account_id="A-100",
                    destination_account_id="A-200",
                    amount=0,
                )
            ),
        )

    def test_negative_amount() -> None:
        service = build_service()

        assert_raises(
            ValidationError,
            lambda: service.transfer(
                TransferRequest(
                    user_id="USER-1",
                    source_account_id="A-100",
                    destination_account_id="A-200",
                    amount=-10,
                )
            ),
        )

    def test_same_account_transfer() -> None:
        service = build_service()

        assert_raises(
            ValidationError,
            lambda: service.transfer(
                TransferRequest(
                    user_id="USER-1",
                    source_account_id="A-100",
                    destination_account_id="A-100",
                    amount=100,
                )
            ),
        )

    def test_daily_limit() -> None:
        service = TransferService(
            {
                "A-100": Account("A-100", "USER-1", 200_000),
                "A-200": Account("A-200", "USER-2", 0),
            }
        )

        service.transfer(
            TransferRequest(
                user_id="USER-1",
                source_account_id="A-100",
                destination_account_id="A-200",
                amount=90_000,
            )
        )

        assert_raises(
            DailyLimitExceededError,
            lambda: service.transfer(
                TransferRequest(
                    user_id="USER-1",
                    source_account_id="A-100",
                    destination_account_id="A-200",
                    amount=20_000,
                )
            ),
        )

    return [
        TestCase(
            test_id="TC-001",
            title="Valid authenticated transfer",
            requirement_ids=["FR-001", "SEC-001"],
            acceptance_criterion_ids=["AC-001"],
            execute=test_valid_transfer,
        ),
        TestCase(
            test_id="TC-002",
            title="Reject transfer with insufficient funds",
            requirement_ids=["FR-002"],
            acceptance_criterion_ids=["AC-002"],
            execute=test_insufficient_funds,
        ),
        TestCase(
            test_id="TC-003",
            title="Reject unauthenticated transfer",
            requirement_ids=["SEC-001"],
            acceptance_criterion_ids=["AC-004"],
            execute=test_unauthenticated_transfer,
        ),
        TestCase(
            test_id="TC-004",
            title="Reject zero transfer amount",
            requirement_ids=["FR-001"],
            acceptance_criterion_ids=["AC-001"],
            execute=test_zero_amount,
        ),
        TestCase(
            test_id="TC-005",
            title="Reject negative transfer amount",
            requirement_ids=["FR-001"],
            acceptance_criterion_ids=["AC-001"],
            execute=test_negative_amount,
        ),
        TestCase(
            test_id="TC-006",
            title="Reject transfer to the same account",
            requirement_ids=["FR-001"],
            acceptance_criterion_ids=["AC-001"],
            execute=test_same_account_transfer,
        ),
        TestCase(
            test_id="TC-007",
            title="Reject transfer exceeding daily limit",
            requirement_ids=["BR-001"],
            acceptance_criterion_ids=["AC-003"],
            execute=test_daily_limit,
        ),
    ]


def run_tests(test_cases: List[TestCase]) -> None:
    """Execute and display acceptance-oriented tests."""
    print("\n" + "=" * 80)
    print("TEST EXECUTION")
    print("=" * 80)

    for test_case in test_cases:
        status = test_case.run()
        print(f"{test_case.test_id}: {status.value} - {test_case.title}")

        if test_case.failure_message:
            print("  Failure:", test_case.failure_message)


# =============================================================================
# 9. REQUIREMENT TRACEABILITY
# =============================================================================

# Requirement traceability is the ability to follow a requirement through the
# software lifecycle.
#
# Typical relationships may include:
#
# Business Need
#     -> Requirement
#     -> Acceptance Criterion
#     -> Design
#     -> Implementation
#     -> Test Case
#     -> Test Result
#     -> Defect
#     -> Release Evidence
#
# Traceability helps answer questions such as:
#
# - Why does this feature exist?
# - Which requirements does this test verify?
# - Which tests are affected if a requirement changes?
# - Are all approved requirements implemented?
# - Are all requirements verified?
# - Is a feature implemented without an approved requirement?
#
# Types of traceability:
#
# Forward traceability:
#     Requirement -> downstream artifacts.
#
# Backward traceability:
#     Implementation/test -> originating requirement.
#
# Bidirectional traceability:
#     Supports both directions.


@dataclass
class TraceLink:
    """Represents a directed relationship between two artifacts."""

    source_id: str
    target_id: str
    relationship: str


@dataclass
class Defect:
    """Represents a defect linked to requirements and tests."""

    defect_id: str
    title: str
    severity: DefectSeverity
    requirement_ids: List[str]
    discovered_by_test_id: Optional[str]
    status: str = "Open"


class TraceabilityMatrix:
    """
    Stores traceability relationships between specification artifacts.

    This is a simplified Requirement Traceability Matrix (RTM) implementation.
    """

    def __init__(self) -> None:
        self.links: List[TraceLink] = []

    def add_link(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
    ) -> None:
        link = TraceLink(
            source_id=source_id,
            target_id=target_id,
            relationship=relationship,
        )

        if link not in self.links:
            self.links.append(link)

    def forward_links(self, source_id: str) -> List[TraceLink]:
        """Return direct downstream links from an artifact."""
        return [
            link
            for link in self.links
            if link.source_id == source_id
        ]

    def backward_links(self, target_id: str) -> List[TraceLink]:
        """Return direct upstream links to an artifact."""
        return [
            link
            for link in self.links
            if link.target_id == target_id
        ]

    def reachable_forward(self, source_id: str) -> Set[str]:
        """
        Return all artifacts reachable from a source using graph traversal.

        This supports multi-level impact analysis.
        """
        visited: Set[str] = set()
        stack = [source_id]

        adjacency: Dict[str, List[str]] = {}

        for link in self.links:
            adjacency.setdefault(link.source_id, []).append(
                link.target_id
            )

        while stack:
            current = stack.pop()

            for neighbor in adjacency.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append(neighbor)

        return visited

    def print_matrix(self) -> None:
        """Display all traceability links."""
        print("\nTRACEABILITY LINKS")
        print("-" * 80)

        for link in self.links:
            print(
                f"{link.source_id:12} -> "
                f"{link.target_id:12} "
                f"[{link.relationship}]"
            )


def build_traceability_matrix(
    srs: SRS,
    criteria: List[AcceptanceCriterion],
    tests: List[TestCase],
) -> TraceabilityMatrix:
    """Create traceability links for the example system."""

    matrix = TraceabilityMatrix()

    # Requirements -> acceptance criteria.
    for criterion in criteria:
        matrix.add_link(
            criterion.requirement_id,
            criterion.criterion_id,
            "defined by",
        )

    # Requirements -> tests.
    for test_case in tests:
        for requirement_id in test_case.requirement_ids:
            if requirement_id not in srs.requirements:
                raise ValueError(
                    f"Test {test_case.test_id} references unknown requirement "
                    f"{requirement_id}."
                )

            matrix.add_link(
                requirement_id,
                test_case.test_id,
                "verified by",
            )

    # Acceptance criteria -> tests.
    for test_case in tests:
        for criterion_id in test_case.acceptance_criterion_ids:
            matrix.add_link(
                criterion_id,
                test_case.test_id,
                "tested by",
            )

    # Requirements -> implementation components.
    implementation_links = {
        "FR-001": "COMP-TransferService",
        "FR-002": "COMP-TransferService",
        "BR-001": "COMP-TransferService",
        "SEC-001": "COMP-TransferService",
        "NFR-001": "COMP-PerformanceMonitoring",
    }

    for requirement_id, component_id in implementation_links.items():
        matrix.add_link(
            requirement_id,
            component_id,
            "implemented by",
        )

    return matrix


# =============================================================================
# 10. TRACEABILITY COVERAGE ANALYSIS
# =============================================================================


def analyze_requirement_coverage(
    srs: SRS,
    matrix: TraceabilityMatrix,
) -> Dict[str, Dict[str, bool]]:
    """
    Determine whether requirements have selected downstream relationships.

    A production RTM may track many additional artifact types.
    """

    coverage: Dict[str, Dict[str, bool]] = {}

    for requirement_id in srs.requirements:
        links = matrix.forward_links(requirement_id)

        targets = {link.target_id for link in links}

        coverage[requirement_id] = {
            "has_acceptance_criteria": any(
                target.startswith("AC-")
                for target in targets
            ),
            "has_test_case": any(
                target.startswith("TC-")
                for target in targets
            ),
            "has_implementation_link": any(
                target.startswith("COMP-")
                for target in targets
            ),
        }

    return coverage


def print_coverage_report(
    srs: SRS,
    coverage: Dict[str, Dict[str, bool]],
) -> None:
    print("\n" + "=" * 80)
    print("REQUIREMENT TRACEABILITY COVERAGE")
    print("=" * 80)

    for requirement_id, result in coverage.items():
        print(f"\n{requirement_id}: {srs.requirements[requirement_id].title}")

        for metric, covered in result.items():
            status = "YES" if covered else "NO"
            print(f"  {metric}: {status}")


# =============================================================================
# 11. ORPHAN ARTIFACT DETECTION
# =============================================================================

# Orphan requirements:
#     Requirements without appropriate downstream verification.
#
# Orphan tests:
#     Tests that are not linked to any approved requirement.
#
# Orphan implementation:
#     Components that cannot be justified by requirements.
#
# Traceability does not prove correctness by itself. It proves relationships and
# coverage. A fully traceable but incorrect requirement is still incorrect.


def find_untested_requirements(
    srs: SRS,
    tests: List[TestCase],
) -> List[str]:
    """Return requirement IDs with no linked test."""

    tested_requirements = {
        requirement_id
        for test_case in tests
        for requirement_id in test_case.requirement_ids
    }

    return [
        requirement_id
        for requirement_id in srs.requirements
        if requirement_id not in tested_requirements
    ]


def find_orphan_tests(
    srs: SRS,
    tests: List[TestCase],
) -> List[str]:
    """Return test IDs that reference no valid requirement."""

    orphan_tests = []

    for test_case in tests:
        if not test_case.requirement_ids:
            orphan_tests.append(test_case.test_id)
            continue

        if not any(
            requirement_id in srs.requirements
            for requirement_id in test_case.requirement_ids
        ):
            orphan_tests.append(test_case.test_id)

    return orphan_tests


# =============================================================================
# 12. CHANGE IMPACT ANALYSIS
# =============================================================================

# Requirements change because of:
#
# - Business policy changes
# - Regulatory changes
# - Stakeholder feedback
# - Technical discoveries
# - Security findings
# - Defects
# - Changed assumptions
#
# A changed requirement should trigger impact analysis.
#
# Example:
#
# BR-001 daily transfer limit changes from 100000 to 50000.
#
# Potential impacts:
#
# - Acceptance criteria
# - Unit tests
# - Integration tests
# - Business documentation
# - Transfer implementation
# - User interface validation
# - API documentation
# - Monitoring and reporting


def demonstrate_impact_analysis(
    matrix: TraceabilityMatrix,
    requirement_id: str,
) -> None:
    print("\n" + "=" * 80)
    print("CHANGE IMPACT ANALYSIS")
    print("=" * 80)

    impacted = matrix.reachable_forward(requirement_id)

    print(f"Requirement changed: {requirement_id}")
    print("Potentially impacted artifacts:")

    for artifact_id in sorted(impacted):
        print(" ", artifact_id)


# =============================================================================
# 13. REQUIREMENT VALIDATION AND VERIFICATION
# =============================================================================

# Validation and verification are related but distinct.
#
# Validation:
#     Are we specifying the right thing for the intended need?
#
# Verification:
#     Does an artifact satisfy the specified requirement?
#
# Examples:
#
# Validation question:
#     Is a 100000 daily transfer limit actually the correct business policy?
#
# Verification question:
#     Does the implementation reject a transfer exceeding 100000?
#
# Common requirement review activities:
#
# - Stakeholder review
# - Consistency checking
# - Completeness checking
# - Feasibility analysis
# - Testability analysis
# - Compliance review
# - Security review
# - Traceability review


def validate_srs_and_print_results(srs: SRS) -> None:
    print("\n" + "=" * 80)
    print("SRS VALIDATION")
    print("=" * 80)

    issues = srs.validate()

    if not issues:
        print("No automated quality warnings were found.")
        return

    for requirement_id, requirement_issues in issues.items():
        print(f"\n{requirement_id}")

        for issue in requirement_issues:
            print(" ", issue)


# =============================================================================
# 14. REQUIREMENT CONFLICT DETECTION
# =============================================================================

# Conflicts can exist between requirements.
#
# Example:
#
# Requirement A:
#     Store logs for 10 years.
#
# Requirement B:
#     Delete all user data after 30 days.
#
# These may require clarification about which data is included, legal exceptions,
# anonymization, retention obligations, and precedence.
#
# Automated conflict detection is difficult because natural language is complex.
# Structured rules can still detect selected technical conflicts.


@dataclass
class NumericConstraint:
    """A simplified structured numeric requirement constraint."""

    requirement_id: str
    metric: str
    operator: str
    value: float


def constraints_conflict(
    first: NumericConstraint,
    second: NumericConstraint,
) -> bool:
    """
    Detect selected obvious conflicts.

    Supported patterns:
    - metric X <= A versus metric X >= B where B > A
    - metric X == A versus metric X == B where A != B
    """

    if first.metric != second.metric:
        return False

    if first.operator == "==" and second.operator == "==":
        return first.value != second.value

    if first.operator == "<=" and second.operator == ">=":
        return second.value > first.value

    if first.operator == ">=" and second.operator == "<=":
        return first.value > second.value

    return False


def demonstrate_constraint_conflicts() -> None:
    print("\n" + "=" * 80)
    print("STRUCTURED REQUIREMENT CONFLICT DETECTION")
    print("=" * 80)

    maximum = NumericConstraint(
        requirement_id="NFR-A",
        metric="response_time_seconds",
        operator="<=",
        value=2.0,
    )

    minimum = NumericConstraint(
        requirement_id="NFR-B",
        metric="response_time_seconds",
        operator=">=",
        value=5.0,
    )

    print(
        "Constraints conflict:",
        constraints_conflict(maximum, minimum),
    )


# =============================================================================
# 15. COMMON REQUIREMENT MISTAKES
# =============================================================================

# Mistake 1: Implementation disguised as a requirement.
#
# "The system shall use PostgreSQL."
#
# This may be a valid technical constraint, but it should not be presented as a
# business requirement unless the database technology itself is mandatory.
#
# Mistake 2: Combining multiple independent behaviors.
#
# "The system shall authenticate users, calculate balances, send notifications,
# and generate reports."
#
# Such a statement is difficult to prioritize, change, and test independently.
#
# Mistake 3: Unmeasurable quality language.
#
# "The application shall be highly scalable."
#
# Better:
#
# "The application shall support 10000 concurrent sessions while maintaining
# 95th percentile response time below 500 milliseconds."
#
# Mistake 4: Missing error behavior.
#
# A specification that describes only successful behavior is incomplete.
#
# Mistake 5: Missing state and data consequences.
#
# If an operation fails, the specification should clarify whether data remains
# unchanged, is partially processed, or is retried.
#
# Mistake 6: Acceptance criteria that duplicate vague requirements.
#
# Requirement:
#     "The application shall be easy to use."
#
# Criterion:
#     "The application must be easy to use."
#
# The criterion does not make the requirement more testable.


# =============================================================================
# 16. ADVANCED ACCEPTANCE CRITERIA DESIGN
# =============================================================================

# Good acceptance criteria frequently cover:
#
# 1. Happy path
# 2. Invalid input
# 3. Boundary conditions
# 4. Authorization
# 5. Error handling
# 6. Data consistency
# 7. Business rules
# 8. Relevant non-functional behavior
#
# Boundary examples for amount > 0:
#
# -1  -> invalid
#  0  -> invalid boundary
#  1  -> smallest valid integer unit in this simplified model
#
# Boundary examples for daily limit <= 100000:
#
#  99999  -> valid if balance permits
# 100000  -> valid if total equals the limit
# 100001  -> invalid


def demonstrate_boundary_conditions() -> None:
    print("\n" + "=" * 80)
    print("BOUNDARY CONDITION TESTING")
    print("=" * 80)

    service = TransferService(
        {
            "A-100": Account("A-100", "USER-1", 200_000),
            "A-200": Account("A-200", "USER-2", 0),
        }
    )

    boundary_amounts = [-1, 0, 1]

    for amount in boundary_amounts:
        isolated_service = TransferService(
            {
                "A-100": Account("A-100", "USER-1", 200_000),
                "A-200": Account("A-200", "USER-2", 0),
            }
        )

        try:
            result = isolated_service.transfer(
                TransferRequest(
                    user_id="USER-1",
                    source_account_id="A-100",
                    destination_account_id="A-200",
                    amount=amount,
                )
            )

            print(f"Amount {amount}: accepted={result.accepted}")

        except TransferError as error:
            print(f"Amount {amount}: rejected ({type(error).__name__})")

    # Test the exact daily limit.
    result = service.transfer(
        TransferRequest(
            user_id="USER-1",
            source_account_id="A-100",
            destination_account_id="A-200",
            amount=100_000,
        )
    )

    print(
        "Exact daily limit:",
        result.accepted,
        result.message,
    )

    # Any additional positive transfer exceeds the limit.
    try:
        service.transfer(
            TransferRequest(
                user_id="USER-1",
                source_account_id="A-100",
                destination_account_id="A-200",
                amount=1,
            )
        )
    except DailyLimitExceededError as error:
        print("Limit + 1:", error)


# =============================================================================
# 17. DEFECT TRACEABILITY
# =============================================================================

# Defects should often be linked to:
#
# - The requirement affected
# - The test that exposed the defect
# - The implementation change that corrected it
# - Regression tests added or updated
#
# This improves root-cause analysis and prevents recurring defects.


def demonstrate_defect_traceability(
    matrix: TraceabilityMatrix,
) -> Defect:
    defect = Defect(
        defect_id="BUG-001",
        title="Daily limit not enforced after multiple transfers",
        severity=DefectSeverity.HIGH,
        requirement_ids=["BR-001"],
        discovered_by_test_id="TC-007",
    )

    matrix.add_link(
        defect.requirement_ids[0],
        defect.defect_id,
        "affected by defect",
    )

    matrix.add_link(
        defect.defect_id,
        defect.discovered_by_test_id or "",
        "discovered by",
    )

    matrix.add_link(
        defect.defect_id,
        "COMP-TransferService",
        "corrected in component",
    )

    print("\n" + "=" * 80)
    print("DEFECT TRACEABILITY")
    print("=" * 80)

    print(defect)
    return defect


# =============================================================================
# 18. TRACEABILITY MATRIX REPRESENTATION
# =============================================================================

# A Requirement Traceability Matrix can be represented as a table.
#
# Typical columns:
#
# Requirement ID
# Requirement Description
# Priority
# Status
# Acceptance Criteria
# Design Component
# Implementation Component
# Test Case
# Test Result
# Defect
# Release Version
#
# The exact structure should match project governance requirements.


def generate_textual_rtm(
    srs: SRS,
    criteria: List[AcceptanceCriterion],
    tests: List[TestCase],
) -> None:
    print("\n" + "=" * 80)
    print("SIMPLIFIED REQUIREMENT TRACEABILITY MATRIX")
    print("=" * 80)

    criteria_by_requirement: Dict[str, List[str]] = {}
    for criterion in criteria:
        criteria_by_requirement.setdefault(
            criterion.requirement_id,
            [],
        ).append(criterion.criterion_id)

    tests_by_requirement: Dict[str, List[str]] = {}
    for test_case in tests:
        for requirement_id in test_case.requirement_ids:
            tests_by_requirement.setdefault(
                requirement_id,
                [],
            ).append(
                f"{test_case.test_id} ({test_case.status.value})"
            )

    for requirement_id, requirement in srs.requirements.items():
        criterion_ids = ", ".join(
            criteria_by_requirement.get(requirement_id, ["None"])
        )

        test_ids = ", ".join(
            tests_by_requirement.get(requirement_id, ["None"])
        )

        print(f"\nRequirement: {requirement_id}")
        print(f"Title:       {requirement.title}")
        print(f"Priority:    {requirement.priority.value}")
        print(f"Status:      {requirement.status.value}")
        print(f"Criteria:    {criterion_ids}")
        print(f"Tests:       {test_ids}")


# =============================================================================
# 19. NON-FUNCTIONAL REQUIREMENTS AND MEASUREMENT
# =============================================================================

# Non-functional requirements require measurable definitions.
#
# Common performance metrics:
#
# Average response time:
#     Arithmetic mean. Can hide slow outliers.
#
# Median:
#     Middle value. Represents a typical request but can hide tail latency.
#
# Percentiles:
#     p95 means 95 percent of observed values are at or below the threshold.
#
# Availability:
#     Uptime / Total time
#
# Reliability:
#     Depends on context and may involve failure rates, error rates, or
#     successful operation probability.


def percentile(values: List[float], percentile_value: float) -> float:
    """
    Calculate a simple nearest-rank percentile.

    For production analytics, definitions should be standardized because
    percentile calculation methods can differ.
    """
    if not values:
        raise ValueError("Cannot calculate percentile of an empty list.")

    if not 0 < percentile_value <= 100:
        raise ValueError("Percentile must be greater than 0 and at most 100.")

    ordered = sorted(values)
    rank = int(
        (percentile_value / 100) * len(ordered) + 0.999999
    )

    index = max(0, min(rank - 1, len(ordered) - 1))
    return ordered[index]


def demonstrate_performance_requirement() -> None:
    print("\n" + "=" * 80)
    print("NON-FUNCTIONAL REQUIREMENT MEASUREMENT")
    print("=" * 80)

    response_times = [
        0.20, 0.25, 0.30, 0.35, 0.40,
        0.45, 0.50, 0.60, 0.70, 0.80,
        0.90, 1.00, 1.10, 1.20, 1.50,
        1.60, 1.70, 1.80, 1.90, 2.50,
    ]

    p95 = percentile(response_times, 95)
    requirement_limit = 2.0

    print(f"p95 response time: {p95:.2f} seconds")
    print(f"Required limit:    {requirement_limit:.2f} seconds")
    print("Requirement met:", p95 <= requirement_limit)


# =============================================================================
# 20. PRODUCTION DESIGN CONSIDERATIONS
# =============================================================================

# Specifications must consider the difference between demonstration code and
# production software.
#
# Important production concerns for transfer processing include:
#
# Atomicity:
#     A debit and credit should not leave inconsistent partial state.
#
# Concurrency:
#     Simultaneous requests can create race conditions.
#
# Idempotency:
#     Retrying the same request should not unintentionally transfer money twice.
#
# Auditability:
#     Important operations should create reliable audit records.
#
# Authorization:
#     Authentication alone is insufficient; the authenticated user must also be
#     authorized for the requested action.
#
# Input validation:
#     All externally controlled input should be validated.
#
# Precision:
#     Floating-point arithmetic can introduce financial calculation errors.
#
# Observability:
#     Production systems require logs, metrics, traces, and alerts.
#
# Failure handling:
#     Network, database, and dependency failures require defined behavior.
#
# Security:
#     Specifications should identify authentication, authorization, encryption,
#     data handling, logging restrictions, abuse prevention, and audit needs.


@dataclass
class IdempotentTransferRequest:
    """Transfer request containing an idempotency key."""

    request_id: str
    user_id: str
    source_account_id: str
    destination_account_id: str
    amount: int


class IdempotentTransferService(TransferService):
    """
    Demonstrates a simplified idempotency mechanism.

    If the same request ID is submitted twice, the previously stored result is
    returned rather than applying the transfer again.

    Real systems must persist idempotency records durably and handle concurrent
    requests safely.
    """

    def __init__(self, accounts: Dict[str, Account]) -> None:
        super().__init__(accounts)
        self.processed_requests: Dict[str, TransferResult] = {}

    def transfer_idempotent(
        self,
        request: IdempotentTransferRequest,
    ) -> TransferResult:

        if request.request_id in self.processed_requests:
            return self.processed_requests[request.request_id]

        result = self.transfer(
            TransferRequest(
                user_id=request.user_id,
                source_account_id=request.source_account_id,
                destination_account_id=request.destination_account_id,
                amount=request.amount,
            )
        )

        self.processed_requests[request.request_id] = result
        return result


def demonstrate_idempotency() -> None:
    print("\n" + "=" * 80)
    print("IDEMPOTENCY")
    print("=" * 80)

    service = IdempotentTransferService(
        {
            "A-100": Account("A-100", "USER-1", 1_000),
            "A-200": Account("A-200", "USER-2", 0),
        }
    )

    request = IdempotentTransferRequest(
        request_id="REQ-123",
        user_id="USER-1",
        source_account_id="A-100",
        destination_account_id="A-200",
        amount=250,
    )

    first_result = service.transfer_idempotent(request)
    second_result = service.transfer_idempotent(request)

    print("First request:", first_result)
    print("Repeated request:", second_result)
    print("Source balance:", service.accounts["A-100"].balance)
    print("Destination balance:", service.accounts["A-200"].balance)

    # Balances should reflect one transfer, not two.


# =============================================================================
# 21. REQUIREMENT PRIORITIZATION AND SCOPE
# =============================================================================

# Prioritization helps manage limited time, budget, and engineering capacity.
#
# MoSCoW:
#
# Must Have:
#     Required for the solution to meet its essential objective.
#
# Should Have:
#     Important but potentially deferred.
#
# Could Have:
#     Desirable when resources permit.
#
# Won't Have for Current Scope:
#     Explicitly excluded from the current release.
#
# Priority is not the same as implementation order. A lower-priority requirement
# may need earlier technical work because other requirements depend on it.


def print_prioritized_requirements(srs: SRS) -> None:
    print("\n" + "=" * 80)
    print("REQUIREMENT PRIORITIZATION")
    print("=" * 80)

    priority_order = {
        RequirementPriority.MUST: 1,
        RequirementPriority.SHOULD: 2,
        RequirementPriority.COULD: 3,
        RequirementPriority.WONT: 4,
    }

    ordered = sorted(
        srs.requirements.values(),
        key=lambda requirement: (
            priority_order[requirement.priority],
            requirement.requirement_id,
        ),
    )

    for requirement in ordered:
        print(
            f"{requirement.requirement_id}: "
            f"{requirement.priority.value} - "
            f"{requirement.title}"
        )


# =============================================================================
# 22. ADVANCED TRACEABILITY GRAPH ANALYSIS
# =============================================================================

# Traceability can be modeled as a directed graph.
#
# Nodes:
#     Requirements, tests, components, defects, releases, and other artifacts.
#
# Edges:
#     Relationships such as "verified by", "implemented by", and "affected by".
#
# Graph modeling enables:
#
# - Change impact analysis
# - Orphan detection
# - Dependency analysis
# - Coverage analysis
# - Audit evidence generation


def demonstrate_traceability_graph(
    matrix: TraceabilityMatrix,
) -> None:
    print("\n" + "=" * 80)
    print("BIDIRECTIONAL TRACEABILITY EXAMPLE")
    print("=" * 80)

    requirement_id = "FR-002"

    print("Forward links from FR-002:")
    for link in matrix.forward_links(requirement_id):
        print(
            f"  {link.source_id} -> {link.target_id} "
            f"({link.relationship})"
        )

    test_id = "TC-002"

    print(f"\nBackward links to {test_id}:")
    for link in matrix.backward_links(test_id):
        print(
            f"  {link.source_id} -> {link.target_id} "
            f"({link.relationship})"
        )


# =============================================================================
# 23. MAIN PROGRAM
# =============================================================================


def main() -> None:
    """Run the complete software specification tutorial."""

    print("=" * 80)
    print("SOFTWARE SPECIFICATION: SRS, ACCEPTANCE CRITERIA, AND TRACEABILITY")
    print("=" * 80)

    demonstrate_requirement_quality()

    srs = build_example_srs()

    print("\n" + "=" * 80)
    print("SRS OVERVIEW")
    print("=" * 80)

    print("Document ID:", srs.document_id)
    print("System:", srs.system_name)
    print("Version:", srs.version)
    print("Purpose:", srs.purpose)
    print("Scope:", srs.scope)

    print("\nRequirements:")
    for requirement in srs.requirements.values():
        print(
            f"  {requirement.requirement_id}: "
            f"{requirement.title} "
            f"[{requirement.requirement_type.value}]"
        )

    validate_srs_and_print_results(srs)

    story = UserStory(
        story_id="US-001",
        role="authenticated banking customer",
        capability="transfer funds between eligible accounts",
        benefit="manage money digitally",
    )

    print("\n" + "=" * 80)
    print("USER STORY")
    print("=" * 80)
    print(story.render())

    criteria = build_acceptance_criteria()

    print("\n" + "=" * 80)
    print("ACCEPTANCE CRITERIA")
    print("=" * 80)

    for criterion in criteria:
        print(f"\n{criterion.criterion_id} -> {criterion.requirement_id}")
        print(criterion.render())

    demonstrate_transfer_service()

    tests = create_test_cases()
    run_tests(tests)

    matrix = build_traceability_matrix(
        srs=srs,
        criteria=criteria,
        tests=tests,
    )

    matrix.print_matrix()

    coverage = analyze_requirement_coverage(
        srs=srs,
        matrix=matrix,
    )

    print_coverage_report(
        srs=srs,
        coverage=coverage,
    )

    untested = find_untested_requirements(
        srs=srs,
        tests=tests,
    )

    orphan_tests = find_orphan_tests(
        srs=srs,
        tests=tests,
    )

    print("\n" + "=" * 80)
    print("ORPHAN ARTIFACT ANALYSIS")
    print("=" * 80)

    print("Untested requirements:", untested or "None")
    print("Orphan tests:", orphan_tests or "None")

    demonstrate_impact_analysis(
        matrix=matrix,
        requirement_id="BR-001",
    )

    demonstrate_constraint_conflicts()
    demonstrate_boundary_conditions()

    demonstrate_defect_traceability(matrix)

    generate_textual_rtm(
        srs=srs,
        criteria=criteria,
        tests=tests,
    )

    demonstrate_performance_requirement()
    demonstrate_idempotency()
    print_prioritized_requirements(srs)
    demonstrate_traceability_graph(matrix)


if __name__ == "__main__":
    main()
