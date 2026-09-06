"""
Software Requirements: Functional and Non-Functional Requirements
==================================================================

A standalone study script covering software requirements from beginner
through advanced level.

The script demonstrates:
    - What software requirements are
    - Stakeholders, elicitation, analysis, specification, validation
    - Functional requirements
    - Non-functional requirements
    - Business, user, system, domain, interface, and regulatory requirements
    - Requirement attributes and quality characteristics
    - Requirement statements and acceptance criteria
    - SMART and testable requirements
    - Functional vs non-functional distinctions
    - Quantitative NFRs and quality attributes
    - Constraints and assumptions
    - Dependencies, priorities, traceability, and change management
    - Ambiguity, incompleteness, inconsistency, and conflicts
    - Requirements traceability matrices
    - MoSCoW prioritization
    - Risk-based prioritization
    - Requirement validation
    - Basic requirements modeling
    - Performance, security, availability, scalability, usability,
      maintainability, compatibility, reliability, and compliance
    - A practical e-commerce example
    - Requirement quality scoring
    - Automated validation of requirement statements
    - A lightweight requirements repository implemented in Python
    - Testing and production-oriented considerations

The file intentionally uses only Python's standard library.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple
import re
import statistics
import time


# ============================================================================
# 1. FUNDAMENTALS
# ============================================================================

def section(title: str) -> None:
    """Print a readable section heading."""
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def explain_fundamentals() -> None:
    section("1. SOFTWARE REQUIREMENTS FUNDAMENTALS")

    print(
        """
A software requirement describes a capability, behavior, quality,
constraint, or condition that a software system must satisfy.

A requirement answers questions such as:
    - What must the system do?
    - How well must it do it?
    - Who needs the capability?
    - Under what conditions must it operate?
    - What constraints govern implementation or operation?
    - How will satisfaction of the requirement be verified?

A useful distinction is:

    Requirement:
        What the system must provide or satisfy.

    Design:
        How the requirement will be implemented.

For example:

    Requirement:
        "The system shall allow customers to reset their password."

    Design:
        "The application will use Redis to store password-reset tokens."

The first specifies required behavior. The second specifies an
implementation decision.

Requirements can exist at several levels:

    Business requirement
        Describes an organizational goal or business outcome.

    Stakeholder requirement
        Describes a need expressed from a stakeholder's perspective.

    User requirement
        Describes what a user needs to accomplish.

    System/software requirement
        Provides detailed, verifiable requirements for the system.

    Functional requirement
        Describes behavior or capability.

    Non-functional requirement
        Describes a quality, constraint, or measurable characteristic.

A strong requirements process normally includes:
    1. Elicitation
    2. Analysis
    3. Negotiation and prioritization
    4. Specification
    5. Validation
    6. Baseline and approval
    7. Traceability
    8. Change management
    9. Verification and acceptance
"""
    )


# ============================================================================
# 2. REQUIREMENT CLASSIFICATION
# ============================================================================

class RequirementType(Enum):
    BUSINESS = "Business"
    STAKEHOLDER = "Stakeholder"
    USER = "User"
    FUNCTIONAL = "Functional"
    NON_FUNCTIONAL = "Non-functional"
    DOMAIN = "Domain"
    CONSTRAINT = "Constraint"
    INTERFACE = "Interface"
    REGULATORY = "Regulatory"


class Priority(Enum):
    MUST = "Must"
    SHOULD = "Should"
    COULD = "Could"
    WONT = "Won't"


@dataclass
class Requirement:
    """
    Represents a software requirement.

    The class deliberately separates:
        - requirement identity
        - type
        - statement
        - priority
        - source
        - acceptance criteria
        - dependencies
        - risks
        - verification method
    """

    requirement_id: str
    requirement_type: RequirementType
    statement: str
    priority: Priority = Priority.SHOULD
    source: str = "Unknown"
    acceptance_criteria: List[str] = field(default_factory=list)
    dependencies: Set[str] = field(default_factory=set)
    risks: List[str] = field(default_factory=list)
    verification_method: str = "Test"
    rationale: str = ""

    def add_dependency(self, requirement_id: str) -> None:
        self.dependencies.add(requirement_id)

    def add_acceptance_criterion(self, criterion: str) -> None:
        self.acceptance_criteria.append(criterion)


def demonstrate_classification() -> None:
    section("2. REQUIREMENT CLASSIFICATION")

    requirements = [
        Requirement(
            "BR-001",
            RequirementType.BUSINESS,
            "The business shall reduce average checkout abandonment by 15%.",
            Priority.MUST,
            "Business Owner",
        ),
        Requirement(
            "FR-001",
            RequirementType.FUNCTIONAL,
            "The system shall allow authenticated customers to add products to a cart.",
            Priority.MUST,
            "Customer",
        ),
        Requirement(
            "NFR-001",
            RequirementType.NON_FUNCTIONAL,
            "The checkout API shall respond within 500 ms for at least 95% of requests under the defined load.",
            Priority.MUST,
            "Operations",
        ),
        Requirement(
            "CON-001",
            RequirementType.CONSTRAINT,
            "Production services shall run on the organization's approved cloud platform.",
            Priority.MUST,
            "Architecture Board",
        ),
        Requirement(
            "DR-001",
            RequirementType.DOMAIN,
            "Tax calculations shall comply with applicable regional tax rules.",
            Priority.MUST,
            "Finance",
        ),
    ]

    for requirement in requirements:
        print(
            f"{requirement.requirement_id}: "
            f"{requirement.requirement_type.value} | "
            f"{requirement.priority.value} | "
            f"{requirement.statement}"
        )

    print(
        """
Important distinction:

Functional requirements primarily describe:
    inputs, processing, outputs, business rules, workflows,
    state changes, integrations, and system behavior.

Non-functional requirements primarily describe:
    performance, security, reliability, availability, usability,
    scalability, maintainability, compatibility, compliance, and constraints.

A requirement's classification depends on what it is expressing.
"""
    )


# ============================================================================
# 3. FUNCTIONAL REQUIREMENTS
# ============================================================================

def explain_functional_requirements() -> None:
    section("3. FUNCTIONAL REQUIREMENTS")

    print(
        """
Functional requirements describe what a system must do.

Typical functional categories include:

    Authentication
        The system shall authenticate users using approved credentials.

    Authorization
        The system shall prevent customers from accessing another
        customer's order history.

    Data management
        The system shall create, read, update, and delete permitted records.

    Business rules
        The system shall apply a 10% discount when an eligible order
        exceeds the defined threshold.

    Workflow
        The system shall move an approved purchase from "Pending" to
        "Paid" after successful payment confirmation.

    Search
        The system shall return products matching the user's search criteria.

    Notifications
        The system shall send an order-confirmation notification after
        successful payment.

    Integration
        The system shall transmit payment requests to the approved
        payment provider.

    Reporting
        The system shall allow authorized managers to export monthly sales data.

A functional requirement should usually specify:
    actor + trigger/input + behavior + business rules + result/output
"""
    )

    # Progressive example
    def calculate_discount(order_total: float, eligible: bool) -> float:
        """Implement a functional business rule."""
        if order_total < 0:
            raise ValueError("Order total cannot be negative.")

        if eligible and order_total >= 1000:
            return order_total * 0.10

        return 0.0

    def final_order_total(order_total: float, eligible: bool) -> float:
        discount = calculate_discount(order_total, eligible)
        return order_total - discount

    print("Functional business-rule example:")
    print("Discount on ₹1,500 for eligible customer:", calculate_discount(1500, True))
    print("Final total:", final_order_total(1500, True))
    print("Discount on ₹1,500 for ineligible customer:", calculate_discount(1500, False))


# ============================================================================
# 4. NON-FUNCTIONAL REQUIREMENTS
# ============================================================================

def explain_non_functional_requirements() -> None:
    section("4. NON-FUNCTIONAL REQUIREMENTS")

    print(
        """
Non-functional requirements specify qualities, measurable performance
characteristics, operational conditions, or constraints.

Major categories include:

    Performance
        Response time, throughput, latency, resource utilization.

    Availability
        Percentage of time the service must remain operational.

    Reliability
        Ability to perform consistently without failure.

    Scalability
        Ability to handle increased workload or users.

    Security
        Confidentiality, integrity, authentication, authorization,
        auditing, resistance to attacks.

    Usability
        Ease with which intended users can learn and operate the system.

    Accessibility
        Ability of people with different abilities to use the system.

    Maintainability
        Ease of diagnosing, modifying, testing, and evolving the system.

    Compatibility
        Ability to operate with specified environments or systems.

    Portability
        Ability to move the software between environments.

    Recoverability
        Ability to restore service and data after failure.

    Compliance
        Requirements imposed by laws, regulations, contracts, or policies.

An NFR should be measurable whenever practical.

Weak:
    "The system shall be fast."

Strong:
    "The product-search endpoint shall return a response within 400 ms
     for at least 95% of requests at 200 requests per second."

Weak:
    "The system shall be highly available."

Strong:
    "The production API shall achieve at least 99.95% monthly availability,
     excluding approved maintenance windows."

The second forms allow objective verification.
"""
    )


# ============================================================================
# 5. FUNCTIONAL VS NON-FUNCTIONAL
# ============================================================================

def compare_functional_and_nonfunctional() -> None:
    section("5. FUNCTIONAL VS NON-FUNCTIONAL REQUIREMENTS")

    comparisons = [
        ("Primary question", "What must the system do?", "How well or under what constraints?"),
        ("Focus", "Behavior and capability", "Quality attributes and constraints"),
        ("Example", "User can reset password", "Reset request completes within 2 seconds"),
        ("Typical verification", "Functional test", "Performance, security, reliability, or other specialized test"),
        ("Failure", "Expected behavior is absent or incorrect", "Required quality threshold is not achieved"),
        ("Scope", "Often feature-specific", "May affect the entire system"),
    ]

    print(f"{'Dimension':<24} {'Functional':<34} {'Non-functional'}")
    print("-" * 78)
    for dimension, functional, nonfunctional in comparisons:
        print(f"{dimension:<24} {functional:<34} {nonfunctional}")

    print(
        """
A single feature can have both types.

Example:

    FR-010:
        The system shall allow users to upload profile photographs.

    NFR-010:
        The profile-image upload service shall accept files up to 10 MB
        and complete processing within 3 seconds for 95% of valid uploads.

The functional requirement defines capability.
The non-functional requirement defines operational characteristics.
"""
    )


# ============================================================================
# 6. REQUIREMENT QUALITY
# ============================================================================

def requirement_quality_checks(statement: str) -> Dict[str, bool]:
    """
    Perform lightweight checks on a requirement statement.

    This is not a complete requirements-engineering validator.
    Natural language is context-sensitive, so automated checks are
    useful for finding likely problems rather than proving correctness.
    """
    lower = statement.lower().strip()

    has_subject = bool(re.search(r"\b(system|application|service|platform|user|administrator|customer)\b", lower))
    has_shall = " shall " in f" {lower} "
    has_vague_word = bool(
        re.search(
            r"\b(fast|easy|quick|simple|user-friendly|efficient|robust|"
            r"appropriate|reasonable|soon|etc|as soon as possible)\b",
            lower,
        )
    )
    has_measurable_signal = bool(
        re.search(
            r"\b\d+(\.\d+)?\s*(ms|s|seconds?|minutes?|hours?|days?|%|percent|"
            r"requests?|users?|mb|gb)\b",
            lower,
        )
    )
    has_testable_verb = bool(
        re.search(
            r"\b(allow|create|delete|update|retrieve|display|send|"
            r"authenticate|authorize|reject|accept|calculate|respond|"
            r"store|encrypt|log|return|complete|process|support)\b",
            lower,
        )
    )
    has_ambiguous_or = " or " in lower

    return {
        "has_subject": has_subject,
        "uses_shall": has_shall,
        "contains_vague_language": has_vague_word,
        "contains_measurable_signal": has_measurable_signal,
        "contains_testable_action": has_testable_verb,
        "contains_possible_ambiguity": has_ambiguous_or,
    }


def demonstrate_quality_checks() -> None:
    section("6. REQUIREMENT QUALITY AND TESTABILITY")

    examples = [
        "The system shall respond quickly.",
        "The system shall return a search response within 400 ms for 95% of requests.",
        "The application shall allow an authenticated customer to download an invoice.",
        "The system shall be easy to use.",
    ]

    for statement in examples:
        print(f"\nRequirement: {statement}")
        checks = requirement_quality_checks(statement)
        for check, result in checks.items():
            print(f"  {check}: {result}")

    print(
        """
Good requirements are commonly expected to be:

    Correct
        Represents the actual need.

    Unambiguous
        Has one reasonable interpretation.

    Complete
        Contains enough information to understand and verify it.

    Consistent
        Does not conflict with other requirements.

    Feasible
        Can realistically be implemented within constraints.

    Necessary
        Provides genuine value or satisfies a required constraint.

    Verifiable
        Can be objectively checked.

    Traceable
        Can be connected to its source, implementation, and verification.

    Prioritized
        Has a clear importance or urgency.

    Atomic
        Expresses one coherent requirement rather than unrelated
        requirements joined together.

    Understandable
        Uses language appropriate for its intended audience.
"""
    )


# ============================================================================
# 7. REQUIREMENT STATEMENT PATTERNS
# ============================================================================

def demonstrate_statement_patterns() -> None:
    section("7. REQUIREMENT STATEMENT PATTERNS")

    patterns = {
        "Functional": (
            "The system shall [perform action] when [trigger/input], "
            "resulting in [observable outcome]."
        ),
        "Performance": (
            "The system shall [perform operation] within [measurable threshold] "
            "under [defined workload]."
        ),
        "Availability": (
            "The service shall maintain at least [percentage] availability "
            "during [measurement period]."
        ),
        "Security": (
            "The system shall [security behavior] for [defined scope] "
            "using [approved mechanism/control]."
        ),
        "Capacity": (
            "The system shall support at least [quantity] [users/requests/data] "
            "while maintaining [quality threshold]."
        ),
        "Recovery": (
            "The system shall restore [service/data] within [RTO] after "
            "[failure scenario] with no more than [RPO] data loss."
        ),
    }

    for category, pattern in patterns.items():
        print(f"{category:<15}: {pattern}")


# ============================================================================
# 8. ELICITATION
# ============================================================================

def explain_elicitation() -> None:
    section("8. REQUIREMENTS ELICITATION")

    print(
        """
Elicitation is the systematic discovery of stakeholder needs,
expectations, constraints, assumptions, and business rules.

Common techniques:

    Interviews
        Useful for detailed individual knowledge.

    Workshops
        Useful for resolving cross-functional requirements.

    Observation
        Useful when actual workflows differ from documented workflows.

    Surveys
        Useful for collecting input from large user populations.

    Questionnaires
        Useful for structured information collection.

    Document analysis
        Useful when policies, contracts, procedures, and legacy systems
        already contain requirements.

    Prototyping
        Useful for discovering usability and interaction requirements.

    Brainstorming
        Useful during early exploration.

    Interface analysis
        Useful when the system must integrate with other systems.

    Use cases and scenarios
        Useful for identifying user goals and system responses.

Elicitation should distinguish:
    stated requirements
    implied requirements
    assumptions
    constraints
    preferences
    technical proposals

A stakeholder saying "I need a dashboard" does not automatically
define a complete requirement. Questions may include:
    - Who uses it?
    - What information must it contain?
    - How frequently is it updated?
    - What decisions depend on it?
    - What permissions apply?
    - What happens when data is unavailable?
"""
    )


# ============================================================================
# 9. ACCEPTANCE CRITERIA
# ============================================================================

@dataclass
class Scenario:
    given: str
    when: str
    then: str

    def display(self) -> None:
        print(f"Given: {self.given}")
        print(f"When : {self.when}")
        print(f"Then : {self.then}")


def demonstrate_acceptance_criteria() -> None:
    section("9. ACCEPTANCE CRITERIA")

    print(
        """
Acceptance criteria define observable conditions that must be satisfied
for a requirement or feature to be accepted.

A common scenario structure is:

    Given
        Initial state or precondition.

    When
        Action or event.

    Then
        Expected observable result.
"""
    )

    scenarios = [
        Scenario(
            "the customer is authenticated",
            "the customer submits valid payment details",
            "the order status becomes Paid and a confirmation is generated",
        ),
        Scenario(
            "the customer submits an invalid card",
            "the payment provider rejects the transaction",
            "the order remains unpaid and the customer receives an error message",
        ),
        Scenario(
            "an unauthenticated visitor requests an account page",
            "the request is received",
            "the system denies access and does not expose account data",
        ),
    ]

    for index, scenario in enumerate(scenarios, 1):
        print(f"\nScenario {index}")
        scenario.display()


# ============================================================================
# 10. PRIORITIZATION
# ============================================================================

def moscow_prioritization() -> None:
    section("10. REQUIREMENT PRIORITIZATION: MoSCoW")

    print(
        """
MoSCoW classification:

    Must
        Essential for the release or agreed scope.

    Should
        Important but the system can operate without it temporarily.

    Could
        Desirable but lower priority.

    Won't
        Explicitly excluded from the current scope.

Prioritization should not be based solely on stakeholder volume.
Consider:
    - Business value
    - Regulatory necessity
    - Risk reduction
    - User impact
    - Dependencies
    - Cost
    - Time
    - Technical feasibility
    - Security consequences
"""
    )

    items = [
        ("FR-001", "Secure login", Priority.MUST),
        ("FR-002", "Order history", Priority.SHOULD),
        ("FR-003", "Product recommendations", Priority.COULD),
        ("FR-004", "Social sharing", Priority.WONT),
    ]

    for requirement_id, name, priority in items:
        print(f"{requirement_id:<10} {name:<28} {priority.value}")


# ============================================================================
# 11. RISK/VALUE PRIORITIZATION
# ============================================================================

def calculate_requirement_score(
    business_value: int,
    user_impact: int,
    risk_reduction: int,
    implementation_cost: int,
) -> float:
    """
    Example prioritization heuristic.

    Scores are intentionally simple:
        value = business value + user impact + risk reduction
        cost = implementation cost

    The formula is illustrative, not a universal industry standard.
    """
    if implementation_cost <= 0:
        raise ValueError("Implementation cost must be positive.")

    value = business_value + user_impact + risk_reduction
    return value / implementation_cost


def demonstrate_risk_prioritization() -> None:
    section("11. VALUE, RISK, AND COST PRIORITIZATION")

    candidates = [
        ("Payment security", 10, 10, 10, 5),
        ("Dark mode", 3, 3, 1, 3),
        ("Order export", 6, 5, 2, 4),
        ("Product recommendations", 7, 7, 2, 8),
    ]

    ranked = []

    for name, value, impact, risk, cost in candidates:
        score = calculate_requirement_score(value, impact, risk, cost)
        ranked.append((score, name))

    for score, name in sorted(ranked, reverse=True):
        print(f"{name:<30} priority score = {score:.2f}")


# ============================================================================
# 12. TRACEABILITY
# ============================================================================

@dataclass
class TraceabilityMatrix:
    """
    Lightweight requirements traceability matrix.

    Requirement IDs map to:
        business objectives
        design components
        test cases
    """

    business_links: Dict[str, Set[str]] = field(default_factory=dict)
    design_links: Dict[str, Set[str]] = field(default_factory=dict)
    test_links: Dict[str, Set[str]] = field(default_factory=dict)

    def link_business(self, requirement_id: str, objective_id: str) -> None:
        self.business_links.setdefault(requirement_id, set()).add(objective_id)

    def link_design(self, requirement_id: str, design_id: str) -> None:
        self.design_links.setdefault(requirement_id, set()).add(design_id)

    def link_test(self, requirement_id: str, test_id: str) -> None:
        self.test_links.setdefault(requirement_id, set()).add(test_id)

    def report(self, requirement_ids: Iterable[str]) -> None:
        for requirement_id in requirement_ids:
            print(
                requirement_id,
                "| business:", sorted(self.business_links.get(requirement_id, set())),
                "| design:", sorted(self.design_links.get(requirement_id, set())),
                "| tests:", sorted(self.test_links.get(requirement_id, set())),
            )


def demonstrate_traceability() -> None:
    section("12. REQUIREMENTS TRACEABILITY")

    matrix = TraceabilityMatrix()

    matrix.link_business("FR-001", "OBJ-01")
    matrix.link_design("FR-001", "DESIGN-AUTH")
    matrix.link_test("FR-001", "TC-LOGIN-001")
    matrix.link_test("FR-001", "TC-LOGIN-002")

    matrix.link_business("NFR-001", "OBJ-02")
    matrix.link_design("NFR-001", "DESIGN-CACHE")
    matrix.link_test("NFR-001", "TC-PERF-001")

    matrix.report(["FR-001", "NFR-001"])

    print(
        """
Traceability supports:

    - Impact analysis
    - Completeness analysis
    - Change management
    - Test coverage
    - Auditability
    - Regulatory evidence
    - Verification planning

Bidirectional traceability is especially valuable:
    business objective -> requirement -> design -> implementation -> test
and:
    test failure/change -> requirement -> business objective
"""
    )


# ============================================================================
# 13. REQUIREMENT DEPENDENCIES
# ============================================================================

def topological_sort(
    requirements: Sequence[Requirement],
) -> List[str]:
    """
    Return an implementation order for an acyclic dependency graph.

    Raises ValueError when a dependency cycle exists.
    """
    by_id = {requirement.requirement_id: requirement for requirement in requirements}

    indegree = {requirement_id: 0 for requirement_id in by_id}
    outgoing: Dict[str, Set[str]] = {requirement_id: set() for requirement_id in by_id}

    for requirement in requirements:
        for dependency in requirement.dependencies:
            if dependency not in by_id:
                raise ValueError(
                    f"Requirement {requirement.requirement_id} depends on "
                    f"unknown requirement {dependency}."
                )

            indegree[requirement.requirement_id] += 1
            outgoing[dependency].add(requirement.requirement_id)

    ready = sorted(
        requirement_id
        for requirement_id, degree in indegree.items()
        if degree == 0
    )

    result: List[str] = []

    while ready:
        current = ready.pop(0)
        result.append(current)

        for dependent in sorted(outgoing[current]):
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                ready.append(dependent)
                ready.sort()

    if len(result) != len(by_id):
        raise ValueError("Requirement dependency cycle detected.")

    return result


def demonstrate_dependencies() -> None:
    section("13. REQUIREMENT DEPENDENCIES")

    requirements = [
        Requirement("FR-001", RequirementType.FUNCTIONAL, "The system shall create accounts."),
        Requirement("FR-002", RequirementType.FUNCTIONAL, "The system shall authenticate accounts."),
        Requirement("FR-003", RequirementType.FUNCTIONAL, "The system shall display private account data."),
    ]

    requirements[1].add_dependency("FR-001")
    requirements[2].add_dependency("FR-002")

    print("Dependency-aware order:", topological_sort(requirements))

    cyclic = [
        Requirement("A", RequirementType.FUNCTIONAL, "Requirement A"),
        Requirement("B", RequirementType.FUNCTIONAL, "Requirement B"),
    ]
    cyclic[0].add_dependency("B")
    cyclic[1].add_dependency("A")

    try:
        topological_sort(cyclic)
    except ValueError as error:
        print("Expected cycle error:", error)


# ============================================================================
# 14. QUALITY ATTRIBUTES IN DETAIL
# ============================================================================

@dataclass
class QualityTarget:
    name: str
    target: str
    measurement: str
    verification: str


def demonstrate_quality_attributes() -> None:
    section("14. QUALITY ATTRIBUTES AND QUANTITATIVE NFRs")

    targets = [
        QualityTarget(
            "Performance",
            "p95 latency <= 500 ms",
            "95th percentile request latency",
            "Load test",
        ),
        QualityTarget(
            "Availability",
            ">= 99.95% per calendar month",
            "Monthly uptime",
            "Monitoring and incident records",
        ),
        QualityTarget(
            "Recovery",
            "RTO <= 30 minutes",
            "Time to restore service",
            "Recovery exercise",
        ),
        QualityTarget(
            "Data recovery",
            "RPO <= 5 minutes",
            "Maximum tolerated data loss",
            "Backup/restore test",
        ),
        QualityTarget(
            "Capacity",
            "10,000 concurrent sessions",
            "Concurrent active sessions",
            "Capacity test",
        ),
        QualityTarget(
            "Security",
            "MFA required for privileged accounts",
            "Authentication policy compliance",
            "Security test and configuration audit",
        ),
    ]

    print(f"{'Attribute':<18} {'Target':<32} {'Measurement':<34} Verification")
    print("-" * 120)

    for target in targets:
        print(
            f"{target.name:<18} "
            f"{target.target:<32} "
            f"{target.measurement:<34} "
            f"{target.verification}"
        )


# ============================================================================
# 15. PERFORMANCE CONCEPTS
# ============================================================================

def percentile(values: Sequence[float], p: float) -> float:
    """Calculate a simple nearest-rank percentile."""
    if not values:
        raise ValueError("Cannot calculate percentile of an empty sequence.")
    if not 0 <= p <= 100:
        raise ValueError("Percentile must be between 0 and 100.")

    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((p / 100) * len(ordered) + 0.999999) - 1))
    return ordered[index]


def demonstrate_performance_metrics() -> None:
    section("15. PERFORMANCE REQUIREMENTS")

    response_times_ms = [
        120, 135, 140, 145, 150,
        155, 160, 170, 190, 220,
        240, 250, 275, 300, 350,
        380, 410, 450, 500, 800,
    ]

    average = statistics.mean(response_times_ms)
    p95 = percentile(response_times_ms, 95)
    maximum = max(response_times_ms)

    print(f"Average latency: {average:.1f} ms")
    print(f"P95 latency:     {p95:.1f} ms")
    print(f"Maximum latency: {maximum:.1f} ms")

    print(
        """
Average latency and percentile latency answer different questions.

A system can have a good average while a significant minority of users
experience poor response times.

Common performance metrics:
    - Latency
    - Response time
    - Throughput
    - Requests per second
    - Transactions per second
    - Concurrent users
    - Error rate
    - CPU utilization
    - Memory utilization
    - Queue depth

A performance requirement should define:
    workload + environment + metric + threshold + measurement method.
"""
    )


# ============================================================================
# 16. AVAILABILITY AND RELIABILITY
# ============================================================================

def availability_percentage(uptime_minutes: float, total_minutes: float) -> float:
    if total_minutes <= 0:
        raise ValueError("Total time must be positive.")
    if uptime_minutes < 0 or uptime_minutes > total_minutes:
        raise ValueError("Uptime must be within the total measurement period.")

    return uptime_minutes / total_minutes * 100


def allowed_downtime_minutes(
    total_minutes: float,
    availability_target: float,
) -> float:
    if total_minutes < 0:
        raise ValueError("Total minutes cannot be negative.")
    if not 0 <= availability_target <= 100:
        raise ValueError("Availability target must be between 0 and 100.")

    return total_minutes * (1 - availability_target / 100)


def demonstrate_availability() -> None:
    section("16. AVAILABILITY AND RELIABILITY")

    monthly_minutes = 30 * 24 * 60

    for target in (99.0, 99.9, 99.95, 99.99):
        downtime = allowed_downtime_minutes(monthly_minutes, target)
        print(f"{target:>6.2f}% availability -> {downtime:.2f} minutes/month downtime")

    uptime = monthly_minutes - 30
    print(
        f"\nAvailability after 30 minutes downtime: "
        f"{availability_percentage(uptime, monthly_minutes):.4f}%"
    )

    print(
        """
Availability is not identical to reliability.

Availability asks:
    "Is the service operational when required?"

Reliability asks:
    "Does the system perform correctly and consistently over time?"

Related concepts:
    MTBF = Mean Time Between Failures
    MTTR = Mean Time To Repair/Restore

High availability often requires redundancy, health checks,
failover mechanisms, monitoring, graceful degradation, and tested recovery.
"""
    )


# ============================================================================
# 17. SECURITY REQUIREMENTS
# ============================================================================

def password_policy_is_valid(
    password: str,
    minimum_length: int = 12,
) -> bool:
    """
    Illustrative password-policy validator.

    Real production authentication should use a mature identity system,
    secure password hashing, rate limiting, MFA where appropriate,
    secure session management, and other controls.
    """
    if len(password) < minimum_length:
        return False

    has_upper = bool(re.search(r"[A-Z]", password))
    has_lower = bool(re.search(r"[a-z]", password))
    has_digit = bool(re.search(r"\d", password))
    has_special = bool(re.search(r"[^A-Za-z0-9]", password))

    return has_upper and has_lower and has_digit and has_special


def demonstrate_security_requirements() -> None:
    section("17. SECURITY REQUIREMENTS")

    test_passwords = [
        "short",
        "Password123",
        "StrongPassword123!",
        "Another$Secure99",
    ]

    for password in test_passwords:
        print(
            f"{password!r:<25} "
            f"policy result = {password_policy_is_valid(password)}"
        )

    print(
        """
Security requirements can cover:

    Authentication
        Who is the user?

    Authorization
        What may the user access or perform?

    Confidentiality
        Which information must remain protected?

    Integrity
        How must unauthorized modification be prevented or detected?

    Accountability
        Which security-relevant actions must be attributable?

    Auditability
        Which events must be recorded?

    Session security
        How are sessions created, protected, expired, and revoked?

    Input security
        Which inputs must be validated or constrained?

    Data protection
        Which data must be encrypted in transit or at rest?

A security requirement should identify the protected asset, threat/control
context, scope, and measurable or testable expectation where possible.

Example:
    "The system shall require multi-factor authentication for all
     privileged accounts."

Security should not be reduced to password complexity alone.
"""
    )


# ============================================================================
# 18. USABILITY AND ACCESSIBILITY
# ============================================================================

def demonstrate_usability_accessibility() -> None:
    section("18. USABILITY AND ACCESSIBILITY REQUIREMENTS")

    examples = [
        "A first-time customer shall be able to complete checkout without training.",
        "The interface shall provide an accessible keyboard-operable navigation path.",
        "Validation errors shall identify the affected field and explain the correction.",
        "The application shall preserve entered form data when recoverable validation errors occur.",
    ]

    for example in examples:
        print("-", example)

    print(
        """
Usability requirements should describe observable outcomes rather than
subjective adjectives.

Weak:
    "The interface shall be user-friendly."

Better:
    "At least 90% of representative first-time users shall complete
     checkout without assistance in usability testing."

Accessibility requirements should address the relevant interaction modes,
content presentation, keyboard operation, assistive technologies, focus
behavior, error communication, and other applicable accessibility criteria.

Accessibility is a quality requirement and can also be a legal or
organizational compliance requirement depending on context.
"""
    )


# ============================================================================
# 19. SCALABILITY
# ============================================================================

def demonstrate_scalability() -> None:
    section("19. SCALABILITY REQUIREMENTS")

    print(
        """
Scalability is the ability of a system to handle changing workload.

Vertical scaling:
    Increase resources of an existing machine or instance.

Horizontal scaling:
    Add more instances or nodes.

A scalable requirement should specify workload and quality constraints.

Example:
    "The order service shall support 5,000 requests per second while
     maintaining p95 latency below 500 ms."

A requirement that merely says:
    "The system shall be scalable."

is not sufficiently testable.

Scaling can introduce trade-offs involving:
    - Cost
    - Complexity
    - Consistency
    - Network traffic
    - Operational burden
    - Data partitioning
    - Coordination
"""
    )


# ============================================================================
# 20. CONSTRAINTS, ASSUMPTIONS, AND DEPENDENCIES
# ============================================================================

def explain_constraints_assumptions() -> None:
    section("20. CONSTRAINTS, ASSUMPTIONS, AND DEPENDENCIES")

    print(
        """
Constraint:
    A restriction on the solution or project.

Examples:
    - Must use an approved programming language.
    - Must integrate with an existing payment provider.
    - Must comply with a contractual requirement.
    - Must operate within a specified hardware environment.

Assumption:
    A condition treated as true for planning purposes.

Examples:
    - Users have internet connectivity.
    - The external identity provider remains available.
    - Product catalog data is supplied daily.

Dependency:
    A requirement depends on another requirement, system, organization,
    service, decision, or external condition.

Example:
    Password reset depends on email delivery.

Important distinction:
    An assumption is not automatically a requirement.
    A constraint is itself a requirement when the project must satisfy it.
"""
    )


# ============================================================================
# 21. REQUIREMENT CONFLICTS
# ============================================================================

def demonstrate_conflicts() -> None:
    section("21. CONFLICTS, CONTRADICTIONS, AND TRADE-OFFS")

    conflicting_requirements = [
        Requirement(
            "NFR-100",
            RequirementType.NON_FUNCTIONAL,
            "The application shall store all user data indefinitely.",
            Priority.SHOULD,
        ),
        Requirement(
            "NFR-101",
            RequirementType.NON_FUNCTIONAL,
            "The application shall delete personal data when retention obligations expire.",
            Priority.MUST,
        ),
    ]

    print("Potential conflict:")
    for requirement in conflicting_requirements:
        print(f"{requirement.requirement_id}: {requirement.statement}")

    print(
        """
Requirement conflicts should be resolved explicitly.

Typical resolution process:
    1. Identify the conflict.
    2. Determine the source and authority of each requirement.
    3. Identify legal, business, security, and technical constraints.
    4. Analyze consequences.
    5. Negotiate a compatible rule.
    6. Record the decision.
    7. Update affected requirements and traceability.

Common trade-offs include:
    security vs convenience
    latency vs consistency
    availability vs strong coordination
    cost vs performance
    flexibility vs simplicity
    customization vs maintainability
    retention vs privacy
"""
    )


# ============================================================================
# 22. AMBIGUITY AND BAD REQUIREMENTS
# ============================================================================

def demonstrate_bad_requirements() -> None:
    section("22. AMBIGUITY, INCOMPLETENESS, AND COMMON REQUIREMENT DEFECTS")

    bad_requirements = [
        "The system shall process requests quickly.",
        "The application shall support a large number of users.",
        "The administrator shall manage users efficiently.",
        "The system shall provide secure and easy access.",
        "The system shall send reports daily or weekly.",
        "The application shall support all common browsers.",
    ]

    for statement in bad_requirements:
        print(f"\nProblematic: {statement}")
        print("Potential issues:", requirement_quality_checks(statement))

    print(
        """
Frequent requirement defects:

    Ambiguous
        "quickly", "normally", "large", "appropriate", "easy".

    Incomplete
        Missing actor, trigger, exception, threshold, or output.

    Compound
        Multiple independent obligations are hidden in one sentence.

    Contradictory
        Conflicts with another requirement.

    Non-verifiable
        Cannot be objectively tested.

    Solution-biased
        Prescribes implementation when only behavior is needed.

    Overly technical
        Uses unnecessary implementation details before the design is known.

    Gold plating
        Includes capabilities not justified by a real requirement.

    Scope leakage
        Adds functionality outside the agreed product boundary.

    Hidden assumptions
        Depends on unstated environmental or operational conditions.
"""
    )


# ============================================================================
# 23. EDGE CASES AND EXCEPTIONS
# ============================================================================

def validate_order_quantity(quantity: int) -> int:
    """Example functional requirement with explicit boundary handling."""
    if quantity < 1:
        raise ValueError("Quantity must be at least 1.")

    if quantity > 100:
        raise ValueError("Quantity cannot exceed 100 per order.")

    return quantity


def demonstrate_edge_cases() -> None:
    section("23. EDGE CASES AND EXCEPTION REQUIREMENTS")

    test_values = [-1, 0, 1, 100, 101]

    for quantity in test_values:
        try:
            validated = validate_order_quantity(quantity)
            print(f"Quantity {quantity:>3}: accepted as {validated}")
        except ValueError as error:
            print(f"Quantity {quantity:>3}: rejected -> {error}")

    print(
        """
A requirement is incomplete if it defines only the happy path when
important exceptions are foreseeable.

Functional requirements should consider:
    - Missing input
    - Invalid input
    - Boundary values
    - Duplicate requests
    - Timeouts
    - Partial failures
    - Unauthorized access
    - Concurrent actions
    - External service failure
    - Data inconsistency
    - Recovery after interruption
    - Retry behavior
    - Idempotency

Example:
    "The payment service shall not create a second charge when an
     identical payment request is retried with the same idempotency key."

This is a functional behavior with strong reliability implications.
"""
    )


# ============================================================================
# 24. REQUIREMENT REPOSITORY
# ============================================================================

class RequirementRepository:
    """
    Small in-memory requirements repository.

    Demonstrates:
        - Add
        - Retrieve
        - Update
        - Delete
        - Search
        - Dependency validation
    """

    def __init__(self) -> None:
        self._requirements: Dict[str, Requirement] = {}

    def add(self, requirement: Requirement) -> None:
        if requirement.requirement_id in self._requirements:
            raise ValueError(
                f"Requirement {requirement.requirement_id} already exists."
            )
        self._requirements[requirement.requirement_id] = requirement

    def get(self, requirement_id: str) -> Requirement:
        try:
            return self._requirements[requirement_id]
        except KeyError:
            raise KeyError(f"Unknown requirement: {requirement_id}")

    def update_statement(self, requirement_id: str, statement: str) -> None:
        self.get(requirement_id).statement = statement

    def delete(self, requirement_id: str) -> None:
        requirement = self.get(requirement_id)

        for other in self._requirements.values():
            if requirement_id in other.dependencies:
                raise ValueError(
                    f"Cannot delete {requirement_id}; "
                    f"{other.requirement_id} depends on it."
                )

        del self._requirements[requirement_id]

    def search(self, keyword: str) -> List[Requirement]:
        keyword = keyword.lower()
        return [
            requirement
            for requirement in self._requirements.values()
            if keyword in requirement.statement.lower()
        ]

    def all(self) -> List[Requirement]:
        return list(self._requirements.values())


def demonstrate_repository() -> None:
    section("24. REQUIREMENTS REPOSITORY")

    repository = RequirementRepository()

    account = Requirement(
        "FR-201",
        RequirementType.FUNCTIONAL,
        "The system shall allow a customer to create an account.",
        Priority.MUST,
    )

    login = Requirement(
        "FR-202",
        RequirementType.FUNCTIONAL,
        "The system shall authenticate a registered customer.",
        Priority.MUST,
    )
    login.add_dependency("FR-201")

    repository.add(account)
    repository.add(login)

    print("Search for 'account':")
    for requirement in repository.search("account"):
        print(requirement.requirement_id, requirement.statement)

    print("\nStored requirements:")
    for requirement in repository.all():
        print(requirement.requirement_id, requirement.priority.value)

    try:
        repository.delete("FR-201")
    except ValueError as error:
        print("\nExpected dependency protection:", error)

    repository.update_statement(
        "FR-202",
        "The system shall authenticate a registered customer using approved credentials.",
    )

    print("\nUpdated:", repository.get("FR-202").statement)


# ============================================================================
# 25. CHANGE MANAGEMENT
# ============================================================================

@dataclass
class ChangeRequest:
    change_id: str
    requirement_id: str
    reason: str
    impact: str
    decision: str = "Pending"


def demonstrate_change_management() -> None:
    section("25. REQUIREMENTS CHANGE MANAGEMENT")

    change = ChangeRequest(
        change_id="CR-001",
        requirement_id="NFR-001",
        reason="Expected traffic has increased.",
        impact="Performance testing and infrastructure capacity must be reviewed.",
    )

    print(change)

    print(
        """
A controlled change process normally considers:

    Change request
        What is being requested?

    Reason
        Why is it necessary?

    Impact analysis
        Which requirements, designs, tests, schedules, costs, and risks change?

    Decision
        Approve, reject, defer, or request clarification.

    Baseline update
        Which approved version becomes authoritative?

    Traceability update
        Which linked artifacts must change?

Requirements are not necessarily immutable. Controlled change is preferable
to uncontrolled requirements drift.
"""
    )


# ============================================================================
# 26. BASELINES AND VERSIONING
# ============================================================================

def demonstrate_baselines() -> None:
    section("26. REQUIREMENT BASELINES AND VERSIONING")

    versions = [
        ("1.0", "Approved baseline", "Initial production scope"),
        ("1.1", "Approved change", "Added password reset"),
        ("2.0", "Major baseline", "Introduced multi-region deployment"),
    ]

    for version, state, description in versions:
        print(f"{version:<6} {state:<22} {description}")

    print(
        """
A baseline is an agreed version of requirements against which subsequent
changes can be controlled.

Versioning helps establish:
    - What was approved?
    - When was it approved?
    - What changed?
    - Who approved it?
    - Which tests correspond to that version?
"""
    )


# ============================================================================
# 27. VERIFICATION METHODS
# ============================================================================

def demonstrate_verification_methods() -> None:
    section("27. REQUIREMENT VERIFICATION METHODS")

    methods = [
        ("Test", "Execute the software and observe behavior."),
        ("Inspection", "Review artifact or configuration against criteria."),
        ("Analysis", "Use calculations, models, or static evaluation."),
        ("Demonstration", "Show behavior in a representative environment."),
        ("Audit", "Evaluate evidence against policy or compliance criteria."),
    ]

    for method, explanation in methods:
        print(f"{method:<15} {explanation}")

    print(
        """
Verification asks whether the implemented system satisfies its specified
requirements.

Validation asks whether the requirements and resulting product address
the actual stakeholder need.

A system can be verified against a poorly written requirement and still
fail to satisfy the real business need.
"""
    )


# ============================================================================
# 28. REQUIREMENTS VALIDATION CHECKLIST
# ============================================================================

def validate_requirement_set(requirements: Sequence[Requirement]) -> Dict[str, object]:
    ids = [requirement.requirement_id for requirement in requirements]

    duplicate_ids = {
        requirement_id
        for requirement_id in ids
        if ids.count(requirement_id) > 1
    }

    empty_statements = [
        requirement.requirement_id
        for requirement in requirements
        if not requirement.statement.strip()
    ]

    missing_acceptance_criteria = [
        requirement.requirement_id
        for requirement in requirements
        if requirement.requirement_type in {
            RequirementType.FUNCTIONAL,
            RequirementType.NON_FUNCTIONAL,
        }
        and not requirement.acceptance_criteria
    ]

    unknown_dependencies = []

    known_ids = set(ids)
    for requirement in requirements:
        for dependency in requirement.dependencies:
            if dependency not in known_ids:
                unknown_dependencies.append(
                    (requirement.requirement_id, dependency)
                )

    return {
        "duplicate_ids": sorted(duplicate_ids),
        "empty_statements": empty_statements,
        "missing_acceptance_criteria": missing_acceptance_criteria,
        "unknown_dependencies": unknown_dependencies,
    }


def demonstrate_validation() -> None:
    section("28. REQUIREMENTS VALIDATION")

    requirements = [
        Requirement(
            "FR-301",
            RequirementType.FUNCTIONAL,
            "The system shall create an order.",
            acceptance_criteria=["An order ID is generated after successful creation."],
        ),
        Requirement(
            "NFR-301",
            RequirementType.NON_FUNCTIONAL,
            "The order API shall respond within 500 ms for 95% of requests.",
            acceptance_criteria=["A defined load test demonstrates the target."],
        ),
        Requirement(
            "FR-302",
            RequirementType.FUNCTIONAL,
            "The system shall display the order status.",
        ),
    ]

    requirements[2].add_dependency("FR-999")

    report = validate_requirement_set(requirements)

    for key, value in report.items():
        print(f"{key:<32}: {value}")

    print(
        """
A validation process should review at least:

    - Correctness
    - Completeness
    - Consistency
    - Feasibility
    - Necessity
    - Testability
    - Traceability
    - Priority
    - Dependencies
    - Security implications
    - Regulatory implications
    - Operational implications
"""
    )


# ============================================================================
# 29. REAL-WORLD E-COMMERCE REQUIREMENT SET
# ============================================================================

def build_ecommerce_requirements() -> List[Requirement]:
    """Build a coherent miniature e-commerce requirement set."""

    requirements = [
        Requirement(
            "BR-001",
            RequirementType.BUSINESS,
            "The business shall increase completed online purchases by 10% within the defined measurement period.",
            Priority.MUST,
            "Executive Sponsor",
        ),
        Requirement(
            "FR-001",
            RequirementType.FUNCTIONAL,
            "The system shall allow a customer to create an account using valid registration information.",
            Priority.MUST,
            "Customer",
            [
                "A unique account is created for valid data.",
                "Duplicate email registration is rejected.",
            ],
        ),
        Requirement(
            "FR-002",
            RequirementType.FUNCTIONAL,
            "The system shall authenticate a registered customer using approved credentials.",
            Priority.MUST,
            "Customer",
            [
                "Valid credentials create an authenticated session.",
                "Invalid credentials do not create an authenticated session.",
            ],
        ),
        Requirement(
            "FR-003",
            RequirementType.FUNCTIONAL,
            "The system shall allow an authenticated customer to add an available product to a cart.",
            Priority.MUST,
            "Customer",
            [
                "The product appears in the customer's cart.",
                "The requested quantity is validated.",
            ],
        ),
        Requirement(
            "FR-004",
            RequirementType.FUNCTIONAL,
            "The system shall calculate the order total using product prices, quantity, discounts, taxes, and applicable shipping charges.",
            Priority.MUST,
            "Finance",
            [
                "The calculated total reflects each applicable pricing component.",
                "Invalid pricing data prevents order completion.",
            ],
        ),
        Requirement(
            "FR-005",
            RequirementType.FUNCTIONAL,
            "The system shall submit a payment request to the approved payment provider when the customer confirms payment.",
            Priority.MUST,
            "Payment Team",
            [
                "A payment request is submitted exactly once for a unique transaction.",
                "Payment failure leaves the order unpaid.",
            ],
        ),
        Requirement(
            "FR-006",
            RequirementType.FUNCTIONAL,
            "The system shall allow an authenticated customer to view their own previous orders.",
            Priority.SHOULD,
            "Customer",
            [
                "Only the authenticated customer's orders are returned.",
            ],
        ),
        Requirement(
            "NFR-001",
            RequirementType.NON_FUNCTIONAL,
            "The product-search API shall return responses within 500 ms for at least 95% of requests under 200 requests per second.",
            Priority.MUST,
            "Operations",
            [
                "The defined load test demonstrates p95 latency of 500 ms or less.",
            ],
            verification_method="Load test",
        ),
        Requirement(
            "NFR-002",
            RequirementType.NON_FUNCTIONAL,
            "The production API shall achieve at least 99.95% monthly availability excluding approved maintenance windows.",
            Priority.MUST,
            "Operations",
            [
                "Monthly monitoring data demonstrates at least 99.95% availability.",
            ],
            verification_method="Monitoring analysis",
        ),
        Requirement(
            "NFR-003",
            RequirementType.NON_FUNCTIONAL,
            "The system shall require multi-factor authentication for privileged administrative accounts.",
            Priority.MUST,
            "Security",
            [
                "A privileged account cannot complete authentication without the required second factor.",
            ],
            verification_method="Security test",
        ),
        Requirement(
            "NFR-004",
            RequirementType.NON_FUNCTIONAL,
            "The service shall restore critical ordering capability within 30 minutes after a qualifying production failure.",
            Priority.MUST,
            "Operations",
            [
                "A recovery exercise demonstrates restoration within 30 minutes.",
            ],
            verification_method="Recovery exercise",
        ),
        Requirement(
            "CON-001",
            RequirementType.CONSTRAINT,
            "Production deployment shall use the organization's approved hosting environment.",
            Priority.MUST,
            "Architecture Board",
        ),
        Requirement(
            "DR-001",
            RequirementType.DOMAIN,
            "Tax calculation shall comply with applicable jurisdiction-specific tax rules.",
            Priority.MUST,
            "Finance",
        ),
    ]

    requirements[1].add_dependency("BR-001")
    requirements[2].add_dependency("FR-001")
    requirements[3].add_dependency("FR-002")
    requirements[4].add_dependency("FR-003")
    requirements[5].add_dependency("FR-004")
    requirements[6].add_dependency("FR-002")

    return requirements


def demonstrate_real_world_requirements() -> None:
    section("29. REAL-WORLD E-COMMERCE REQUIREMENT SET")

    requirements = build_ecommerce_requirements()

    for requirement in requirements:
        print(
            f"{requirement.requirement_id:<8} "
            f"{requirement.requirement_type.value:<18} "
            f"{requirement.priority.value:<8} "
            f"{requirement.statement}"
        )

    print("\nDependency-aware order for functional dependencies:")
    functional = [
        requirement
        for requirement in requirements
        if requirement.requirement_id.startswith("FR-")
    ]

    try:
        print(topological_sort(functional))
    except ValueError as error:
        print("Dependency validation error:", error)


# ============================================================================
# 30. REQUIREMENT METRICS
# ============================================================================

def calculate_test_coverage(requirements: Sequence[Requirement]) -> float:
    """Percentage of requirements that have at least one acceptance criterion."""
    if not requirements:
        return 100.0

    covered = sum(
        bool(requirement.acceptance_criteria)
        for requirement in requirements
    )

    return covered / len(requirements) * 100


def calculate_traceability_coverage(
    requirements: Sequence[Requirement],
    matrix: TraceabilityMatrix,
) -> float:
    if not requirements:
        return 100.0

    linked = sum(
        bool(
            matrix.business_links.get(requirement.requirement_id)
            or matrix.design_links.get(requirement.requirement_id)
            or matrix.test_links.get(requirement.requirement_id)
        )
        for requirement in requirements
    )

    return linked / len(requirements) * 100


def demonstrate_metrics() -> None:
    section("30. REQUIREMENTS METRICS")

    requirements = build_ecommerce_requirements()

    print(
        f"Requirements with acceptance criteria: "
        f"{calculate_test_coverage(requirements):.1f}%"
    )

    matrix = TraceabilityMatrix()

    for requirement in requirements:
        matrix.link_business(requirement.requirement_id, "OBJ-E-COMMERCE")

        if requirement.requirement_type in {
            RequirementType.FUNCTIONAL,
            RequirementType.NON_FUNCTIONAL,
        }:
            matrix.link_test(
                requirement.requirement_id,
                f"TEST-{requirement.requirement_id}",
            )

    print(
        f"Requirements with traceability links: "
        f"{calculate_traceability_coverage(requirements, matrix):.1f}%"
    )

    print(
        """
Useful metrics include:

    - Requirements volatility
    - Percentage of requirements with acceptance criteria
    - Test coverage
    - Traceability coverage
    - Number of open requirement defects
    - Number of ambiguous requirements
    - Requirement approval rate
    - Change request count
    - Requirement rework rate
    - Percentage of requirements with identified source
    - Percentage of requirements verified

Metrics should be interpreted carefully. Optimizing a metric can produce
undesirable behavior if the metric becomes the objective rather than
a signal about requirements quality.
"""
    )


# ============================================================================
# 31. PRODUCTION CONSIDERATIONS
# ============================================================================

def explain_production_considerations() -> None:
    section("31. PRODUCTION AND IMPLEMENTATION CONSIDERATIONS")

    print(
        """
Requirements become operationally useful when they connect to the entire
software lifecycle.

Before implementation:
    - Confirm business objective.
    - Identify stakeholders.
    - Define scope.
    - Establish priorities.
    - Identify constraints and dependencies.
    - Define acceptance criteria.

During design and development:
    - Maintain traceability.
    - Detect requirement changes.
    - Avoid implementing assumptions as facts.
    - Review edge cases.
    - Keep acceptance criteria synchronized.

During testing:
    - Map tests to requirements.
    - Test positive and negative paths.
    - Test boundary conditions.
    - Test NFR thresholds under representative workloads.
    - Verify security and access controls.
    - Validate recovery behavior.

Before release:
    - Confirm mandatory requirements.
    - Confirm regulatory obligations.
    - Review known deviations.
    - Validate operational monitoring.
    - Confirm rollback/recovery requirements.

After release:
    - Monitor production quality attributes.
    - Compare actual behavior with NFR targets.
    - Track incidents against requirements.
    - Capture newly discovered requirements.
    - Control changes through the requirements process.
"""
    )


# ============================================================================
# 32. REQUIREMENTS VS DESIGN VS IMPLEMENTATION VS TEST
# ============================================================================

def demonstrate_requirement_layers() -> None:
    section("32. REQUIREMENT, DESIGN, IMPLEMENTATION, AND TEST DISTINCTION")

    layers = [
        (
            "Business requirement",
            "Reduce failed online purchases.",
        ),
        (
            "Functional requirement",
            "The system shall allow customers to retry a failed payment.",
        ),
        (
            "Non-functional requirement",
            "Payment retry requests shall receive an outcome within 2 seconds for 95% of requests.",
        ),
        (
            "Design decision",
            "Use an idempotency key and a payment-service adapter.",
        ),
        (
            "Implementation",
            "Python code stores and validates idempotency keys.",
        ),
        (
            "Test",
            "Submit the same payment request twice and verify that only one charge occurs.",
        ),
    ]

    for layer, content in layers:
        print(f"{layer:<24}: {content}")

    print(
        """
The distinction matters because requirements describe expected outcomes,
while design and implementation describe selected means.

An exception occurs when a technology, architectural standard, contractual
condition, or regulation is itself a constraint. In that case the constraint
can legitimately appear as a requirement.
"""
    )


# ============================================================================
# 33. REQUIREMENT ENGINEERING LIFECYCLE
# ============================================================================

def explain_lifecycle() -> None:
    section("33. REQUIREMENTS ENGINEERING LIFECYCLE")

    lifecycle = [
        "1. Identify business objectives and stakeholders",
        "2. Elicit needs, rules, constraints, and assumptions",
        "3. Analyze and classify requirements",
        "4. Resolve ambiguity and conflicts",
        "5. Prioritize requirements",
        "6. Specify requirements precisely",
        "7. Define acceptance and verification criteria",
        "8. Validate requirements with stakeholders",
        "9. Baseline approved requirements",
        "10. Trace requirements through design and testing",
        "11. Control changes",
        "12. Verify implementation and validate business outcomes",
    ]

    for item in lifecycle:
        print(item)

    print(
        """
Requirements engineering is iterative.

New information can emerge from:
    - Prototype feedback
    - Technical feasibility analysis
    - Security review
    - Legal review
    - User testing
    - Production incidents
    - Market changes
    - External dependencies

A disciplined process does not prevent change. It makes change visible,
understandable, evaluated, and controlled.
"""
    )


# ============================================================================
# 34. ADVANCED CONCEPT: QUALITY ATTRIBUTE TRADE-OFFS
# ============================================================================

@dataclass
class ArchitectureDecision:
    decision: str
    benefit: str
    cost: str
    affected_requirements: List[str]


def demonstrate_tradeoffs() -> None:
    section("34. ADVANCED QUALITY-ATTRIBUTE TRADE-OFFS")

    decisions = [
        ArchitectureDecision(
            "Add aggressive caching",
            "Can reduce latency and backend load.",
            "Can introduce stale data and invalidation complexity.",
            ["NFR-001", "FR-004"],
        ),
        ArchitectureDecision(
            "Use multi-region active-active deployment",
            "Can improve availability and geographic resilience.",
            "Increases cost, operational complexity, and consistency challenges.",
            ["NFR-002", "NFR-004"],
        ),
        ArchitectureDecision(
            "Require stronger authentication controls",
            "Can reduce unauthorized access risk.",
            "Can add friction to user workflows.",
            ["NFR-003"],
        ),
    ]

    for decision in decisions:
        print(f"\nDecision: {decision.decision}")
        print(f"Benefit: {decision.benefit}")
        print(f"Cost: {decision.cost}")
        print(f"Affected requirements: {', '.join(decision.affected_requirements)}")

    print(
        """
NFRs are often coupled.

Improving one quality attribute may negatively affect another.

For example:
    stronger security controls -> potentially lower convenience
    more redundancy -> potentially higher cost
    stronger consistency -> potentially higher latency
    extensive logging -> potentially higher storage and processing cost
    aggressive optimization -> potentially lower maintainability

Requirements analysis should therefore consider interactions rather than
evaluating every requirement independently.
"""
    )


# ============================================================================
# 35. ADVANCED CONCEPT: REQUIREMENT NORMALIZATION
# ============================================================================

def normalize_requirement(statement: str) -> str:
    """
    Perform basic whitespace normalization.

    This intentionally does not rewrite the requirement's meaning.
    Requirements should not be automatically paraphrased without human review.
    """
    return re.sub(r"\s+", " ", statement.strip())


def demonstrate_normalization() -> None:
    section("35. REQUIREMENT NORMALIZATION")

    raw = "  The   system shall   allow   authenticated users   to   export reports. "
    normalized = normalize_requirement(raw)

    print("Raw       :", repr(raw))
    print("Normalized:", normalized)

    print(
        """
Normalization can improve consistency in stored requirements, but automatic
rewriting must be conservative.

Changing wording can accidentally change:
    - Scope
    - Actor
    - Timing
    - Conditions
    - Exceptions
    - Quantitative thresholds
    - Legal meaning

Formatting automation is safer than semantic rewriting.
"""
    )


# ============================================================================
# 36. ADVANCED CONCEPT: REQUIREMENT TEST GENERATION
# ============================================================================

def generate_basic_test_cases(requirement: Requirement) -> List[str]:
    """Generate test-case prompts from acceptance criteria."""
    tests = []

    for index, criterion in enumerate(requirement.acceptance_criteria, 1):
        tests.append(
            f"TC-{requirement.requirement_id}-{index:03d}: "
            f"Verify criterion: {criterion}"
        )

    return tests


def demonstrate_test_generation() -> None:
    section("36. REQUIREMENTS TO TEST CASES")

    requirement = Requirement(
        "FR-401",
        RequirementType.FUNCTIONAL,
        "The system shall allow a customer to update their email address.",
        acceptance_criteria=[
            "A valid new email address is accepted.",
            "An invalid email address is rejected.",
            "The customer receives confirmation after successful update.",
            "An unauthorized user cannot update another customer's email address.",
        ],
    )

    print(requirement.statement)

    for test_case in generate_basic_test_cases(requirement):
        print(test_case)

    print(
        """
Acceptance criteria provide a bridge between requirements and verification.

Good test coverage should include:
    - Positive cases
    - Negative cases
    - Boundary cases
    - Authorization cases
    - Failure cases
    - Integration cases
    - Performance cases when NFRs require them

Automatically generated test descriptions are starting points, not proof
that a requirement is fully tested.
"""
    )


# ============================================================================
# 37. ADVANCED CONCEPT: SECURITY AND REQUIREMENT ABUSE
# ============================================================================

def demonstrate_security_design_considerations() -> None:
    section("37. SECURITY REQUIREMENTS: ADVANCED CONSIDERATIONS")

    print(
        """
Security requirements should account for:

    Threat model
        What assets, actors, threats, and attack paths matter?

    Trust boundaries
        Where does data or authority cross from one trust domain to another?

    Least privilege
        What is the minimum permission required?

    Defense in depth
        What happens if one security control fails?

    Secure failure
        Does failure deny unsafe actions rather than silently allowing them?

    Auditability
        Can security-relevant actions be investigated?

    Data minimization
        Is sensitive information collected and retained only when necessary?

    Secrets management
        Are credentials and keys protected from source code and logs?

    Rate limiting
        Can authentication and high-risk endpoints resist abuse?

    Input validation
        Are untrusted inputs constrained according to their intended use?

Security NFR examples:

    "Privileged actions shall require multi-factor authentication."

    "Authentication endpoints shall apply rate limiting after repeated
     failed authentication attempts."

    "Sensitive personal data shall not be written to application logs."

    "Security events shall be retained for the organization's defined
     audit period."

The precise requirements depend on the system's threat model and obligations.
"""
    )


# ============================================================================
# 38. ADVANCED CONCEPT: REQUIREMENT COMPLETENESS
# ============================================================================

def requirement_completeness_score(requirement: Requirement) -> float:
    """
    Simple heuristic score.

    The score is not an industry-standard metric. It demonstrates how
    structured review criteria can be represented programmatically.
    """
    score = 0

    if requirement.requirement_id.strip():
        score += 1

    if requirement.statement.strip():
        score += 1

    if requirement.source.strip() and requirement.source != "Unknown":
        score += 1

    if requirement.acceptance_criteria:
        score += 2

    if requirement.verification_method.strip():
        score += 1

    if requirement.rationale.strip():
        score += 1

    return score / 7 * 100


def demonstrate_completeness_score() -> None:
    section("38. REQUIREMENT COMPLETENESS HEURISTIC")

    complete = Requirement(
        "NFR-501",
        RequirementType.NON_FUNCTIONAL,
        "The API shall return within 500 ms for 95% of requests under 200 requests per second.",
        Priority.MUST,
        "Operations",
        ["A load test confirms p95 latency <= 500 ms at the specified workload."],
        verification_method="Load test",
        rationale="Protects checkout responsiveness.",
    )

    incomplete = Requirement(
        "NFR-502",
        RequirementType.NON_FUNCTIONAL,
        "The API shall be fast.",
    )

    print(
        f"{complete.requirement_id}: "
        f"{requirement_completeness_score(complete):.1f}% heuristic score"
    )
    print(
        f"{incomplete.requirement_id}: "
        f"{requirement_completeness_score(incomplete):.1f}% heuristic score"
    )

    print(
        """
A numeric score should not replace expert review.

Some requirements are inherently difficult to reduce to a checklist,
especially domain rules, safety constraints, legal language, and
cross-system requirements.
"""
    )


# ============================================================================
# 39. TESTS FOR THE EDUCATIONAL IMPLEMENTATIONS
# ============================================================================

def run_self_tests() -> None:
    section("39. SELF-TESTS")

    assert calculate_discount(1500, True) == 150
    assert calculate_discount(1500, False) == 0
    assert final_order_total(1500, True) == 1350

    assert availability_percentage(99, 100) == 99
    assert allowed_downtime_minutes(100, 99) == 1

    assert password_policy_is_valid("StrongPassword123!")
    assert not password_policy_is_valid("weak")

    assert validate_order_quantity(1) == 1
    assert validate_order_quantity(100) == 100

    try:
        validate_order_quantity(0)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected quantity validation error.")

    requirements = [
        Requirement("A", RequirementType.FUNCTIONAL, "A"),
        Requirement("B", RequirementType.FUNCTIONAL, "B"),
        Requirement("C", RequirementType.FUNCTIONAL, "C"),
    ]

    requirements[1].add_dependency("A")
    requirements[2].add_dependency("B")

    assert topological_sort(requirements) == ["A", "B", "C"]

    repository = RequirementRepository()
    repository.add(
        Requirement(
            "R1",
            RequirementType.FUNCTIONAL,
            "The system shall create an account.",
        )
    )

    assert len(repository.search("account")) == 1

    print("All self-tests passed.")


# ============================================================================
# 40. STUDY REFERENCE TABLE
# ============================================================================

def print_reference_table() -> None:
    section("40. QUICK REFERENCE")

    rows = [
        ("Functional requirement", "What the system must do"),
        ("Non-functional requirement", "Quality or constraint on the system"),
        ("Business requirement", "Business goal or outcome"),
        ("Stakeholder requirement", "Need of a stakeholder"),
        ("User requirement", "Need from a user's perspective"),
        ("Domain requirement", "Requirement originating from the application domain"),
        ("Constraint", "Restriction on the solution"),
        ("Acceptance criterion", "Observable condition for acceptance"),
        ("Traceability", "Links between requirements and related artifacts"),
        ("Baseline", "Approved version under change control"),
        ("Elicitation", "Discovery of needs and constraints"),
        ("Validation", "Checking that requirements represent the right need"),
        ("Verification", "Checking that implementation satisfies requirements"),
        ("RTO", "Maximum targeted time to restore service"),
        ("RPO", "Maximum targeted amount of data loss"),
        ("Latency", "Time taken to respond or complete an operation"),
        ("Throughput", "Amount of work processed per unit time"),
        ("Availability", "Proportion of time service is operational"),
        ("Scalability", "Ability to handle changing workload"),
        ("Maintainability", "Ease of modifying and operating the system"),
    ]

    print(f"{'Term':<28} Meaning")
    print("-" * 78)

    for term, meaning in rows:
        print(f"{term:<28} {meaning}")


# ============================================================================
# 41. MAIN
# ============================================================================

def main() -> None:
    """
    Run the complete educational demonstration.

    The demonstrations are intentionally ordered from fundamental concepts
    to advanced requirements-engineering practices.
    """
    start_time = time.perf_counter()

    explain_fundamentals()
    demonstrate_classification()
    explain_functional_requirements()
    explain_non_functional_requirements()
    compare_functional_and_nonfunctional()
    demonstrate_quality_checks()
    demonstrate_statement_patterns()
    explain_elicitation()
    demonstrate_acceptance_criteria()
    moscow_prioritization()
    demonstrate_risk_prioritization()
    demonstrate_traceability()
    demonstrate_dependencies()
    demonstrate_quality_attributes()
    demonstrate_performance_metrics()
    demonstrate_availability()
    demonstrate_security_requirements()
    demonstrate_usability_accessibility()
    demonstrate_scalability()
    explain_constraints_assumptions()
    demonstrate_conflicts()
    demonstrate_bad_requirements()
    demonstrate_edge_cases()
    demonstrate_repository()
    demonstrate_change_management()
    demonstrate_baselines()
    demonstrate_verification_methods()
    demonstrate_validation()
    demonstrate_real_world_requirements()
    demonstrate_metrics()
    explain_production_considerations()
    demonstrate_requirement_layers()
    explain_lifecycle()
    demonstrate_tradeoffs()
    demonstrate_normalization()
    demonstrate_test_generation()
    demonstrate_security_design_considerations()
    demonstrate_completeness_score()
    run_self_tests()
    print_reference_table()

    elapsed = time.perf_counter() - start_time

    section("END OF STUDY SCRIPT")
    print(f"Demonstrations completed in {elapsed:.4f} seconds.")
    print(
        """
The central distinction to retain is:

    Functional requirement
        What the system must do.

    Non-functional requirement
        How well it must perform, what quality it must exhibit,
        or what constraint it must satisfy.

Strong requirements make both statements precise enough to be understood,
prioritized, implemented, traced, and objectively verified.
"""
    )


if __name__ == "__main__":
    main()
