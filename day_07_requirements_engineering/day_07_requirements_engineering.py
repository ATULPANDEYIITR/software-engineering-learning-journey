"""
Requirements Engineering: Elicitation, Analysis, Validation, and Documentation
===============================================================================

This self-contained study script demonstrates the major activities involved in
Requirements Engineering using executable Python examples.

Requirements Engineering is the systematic process of discovering, analyzing,
specifying, validating, managing, and maintaining stakeholder needs and system
requirements.

The script covers:

1. Requirements Engineering fundamentals
2. Stakeholders and requirement sources
3. Requirement elicitation
4. Functional and non-functional requirements
5. Constraints, assumptions, dependencies, and business rules
6. Requirement analysis and classification
7. Quality characteristics
8. Ambiguity and conflict detection
9. Requirement prioritization
10. Requirements validation
11. Requirements documentation
12. Traceability
13. Change management
14. Acceptance criteria
15. Use cases and user stories
16. Risk analysis
17. Dependency analysis
18. Versioning
19. Testing requirements
20. Production-oriented requirement management patterns

The examples use only the Python standard library.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
import re
import uuid


# =============================================================================
# SECTION 1: FUNDAMENTAL TERMINOLOGY
# =============================================================================


class RequirementType(Enum):
    """
    Major classifications of requirements.

    BUSINESS:
        Explains organizational goals and desired outcomes.

    FUNCTIONAL:
        Describes what the system must do.

    NON_FUNCTIONAL:
        Describes quality attributes and constraints on system behavior.

    CONSTRAINT:
        Restricts implementation or operation.

    BUSINESS_RULE:
        Defines organizational policies or rules.

    ASSUMPTION:
        A condition believed to be true for planning purposes.
    """

    BUSINESS = "Business"
    FUNCTIONAL = "Functional"
    NON_FUNCTIONAL = "Non-Functional"
    CONSTRAINT = "Constraint"
    BUSINESS_RULE = "Business Rule"
    ASSUMPTION = "Assumption"


class RequirementPriority(Enum):
    """
    MoSCoW prioritization categories.

    MUST:
        Mandatory for the system or release.

    SHOULD:
        Important but temporary workarounds may exist.

    COULD:
        Valuable but lower priority.

    WONT:
        Explicitly excluded from the current scope.
    """

    MUST = "Must Have"
    SHOULD = "Should Have"
    COULD = "Could Have"
    WONT = "Won't Have"


class RequirementStatus(Enum):
    """
    Common lifecycle states for requirements.
    """

    DRAFT = "Draft"
    PROPOSED = "Proposed"
    ANALYZED = "Analyzed"
    VALIDATED = "Validated"
    APPROVED = "Approved"
    IMPLEMENTED = "Implemented"
    VERIFIED = "Verified"
    REJECTED = "Rejected"
    OBSOLETE = "Obsolete"


class StakeholderType(Enum):
    """
    Categories of people or organizations affected by a system.
    """

    CUSTOMER = "Customer"
    END_USER = "End User"
    BUSINESS_OWNER = "Business Owner"
    PRODUCT_MANAGER = "Product Manager"
    DEVELOPER = "Developer"
    TESTER = "Tester"
    OPERATIONS = "Operations"
    REGULATOR = "Regulator"
    EXTERNAL_SYSTEM = "External System"


# =============================================================================
# SECTION 2: STAKEHOLDER MODELING
# =============================================================================


@dataclass
class Stakeholder:
    """
    Represents an individual, role, organization, or system with an interest
    in the project.
    """

    name: str
    stakeholder_type: StakeholderType
    interests: List[str]
    influence: int
    importance: int

    def engagement_priority(self) -> int:
        """
        A simple stakeholder engagement score.

        Real projects may use more sophisticated stakeholder analysis models.
        """
        return self.influence * self.importance


def demonstrate_stakeholder_analysis() -> List[Stakeholder]:
    """
    Demonstrates stakeholder identification and prioritization.
    """

    stakeholders = [
        Stakeholder(
            name="Chief Operations Officer",
            stakeholder_type=StakeholderType.BUSINESS_OWNER,
            interests=[
                "Reduce order processing cost",
                "Improve operational efficiency",
            ],
            influence=5,
            importance=5,
        ),
        Stakeholder(
            name="Customer",
            stakeholder_type=StakeholderType.END_USER,
            interests=[
                "Fast checkout",
                "Accurate order information",
                "Secure payments",
            ],
            influence=3,
            importance=5,
        ),
        Stakeholder(
            name="Software Development Team",
            stakeholder_type=StakeholderType.DEVELOPER,
            interests=[
                "Clear specifications",
                "Stable requirements",
                "Technical feasibility",
            ],
            influence=4,
            importance=4,
        ),
        Stakeholder(
            name="Financial Regulator",
            stakeholder_type=StakeholderType.REGULATOR,
            interests=[
                "Compliance",
                "Auditability",
                "Data protection",
            ],
            influence=5,
            importance=4,
        ),
    ]

    ranked = sorted(
        stakeholders,
        key=lambda stakeholder: stakeholder.engagement_priority(),
        reverse=True,
    )

    print("\n" + "=" * 80)
    print("STAKEHOLDER ANALYSIS")
    print("=" * 80)

    for stakeholder in ranked:
        print(
            f"{stakeholder.name}: "
            f"engagement score={stakeholder.engagement_priority()}"
        )

    return stakeholders


# =============================================================================
# SECTION 3: REQUIREMENT DATA MODEL
# =============================================================================


@dataclass
class Requirement:
    """
    A structured requirement.

    A high-quality requirement should normally have:

    - Unique identifier
    - Clear description
    - Classification
    - Priority
    - Source
    - Acceptance criteria
    - Status
    - Traceability information
    """

    requirement_id: str
    title: str
    description: str
    requirement_type: RequirementType
    priority: RequirementPriority
    source: str
    rationale: str
    acceptance_criteria: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    status: RequirementStatus = RequirementStatus.DRAFT
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def update_description(self, new_description: str) -> None:
        """
        Updates a requirement while increasing its version.

        Versioning is important because requirements frequently change during
        product development.
        """

        self.description = new_description
        self.version += 1
        self.updated_at = datetime.now()

    def is_testable(self) -> bool:
        """
        A basic approximation of testability.

        A requirement should ideally contain measurable or verifiable
        acceptance criteria.
        """

        return len(self.acceptance_criteria) > 0

    def to_dictionary(self) -> Dict:
        """
        Converts the requirement into a serializable dictionary.
        """

        data = asdict(self)

        data["requirement_type"] = self.requirement_type.value
        data["priority"] = self.priority.value
        data["status"] = self.status.value
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()

        return data


def generate_requirement_id(prefix: str = "REQ") -> str:
    """
    Generates a readable unique requirement identifier.

    Example:
        REQ-A1B2C3D4
    """

    random_component = uuid.uuid4().hex[:8].upper()
    return f"{prefix}-{random_component}"


# =============================================================================
# SECTION 4: REQUIREMENT ELICITATION
# =============================================================================


class ElicitationTechnique(Enum):
    """
    Common requirement elicitation techniques.
    """

    INTERVIEW = "Interview"
    QUESTIONNAIRE = "Questionnaire"
    WORKSHOP = "Workshop"
    OBSERVATION = "Observation"
    DOCUMENT_ANALYSIS = "Document Analysis"
    PROTOTYPING = "Prototyping"
    BRAINSTORMING = "Brainstorming"
    FOCUS_GROUP = "Focus Group"
    INTERFACE_ANALYSIS = "Interface Analysis"


@dataclass
class ElicitationFinding:
    """
    Represents raw information collected during elicitation.

    Raw stakeholder statements are not automatically valid requirements.
    They usually require analysis, clarification, decomposition, and
    validation.
    """

    technique: ElicitationTechnique
    stakeholder: str
    raw_statement: str
    context: str
    discovered_at: datetime = field(default_factory=datetime.now)


def demonstrate_elicitation() -> List[ElicitationFinding]:
    """
    Demonstrates collection of raw stakeholder information.
    """

    findings = [
        ElicitationFinding(
            technique=ElicitationTechnique.INTERVIEW,
            stakeholder="Customer",
            raw_statement="The checkout process should be very fast.",
            context="Online retail application",
        ),
        ElicitationFinding(
            technique=ElicitationTechnique.OBSERVATION,
            stakeholder="Operations Team",
            raw_statement=(
                "Employees manually copy customer addresses between two systems."
            ),
            context="Order fulfillment workflow",
        ),
        ElicitationFinding(
            technique=ElicitationTechnique.WORKSHOP,
            stakeholder="Product Manager",
            raw_statement=(
                "Customers must receive order confirmation immediately after payment."
            ),
            context="Customer experience workshop",
        ),
        ElicitationFinding(
            technique=ElicitationTechnique.DOCUMENT_ANALYSIS,
            stakeholder="Regulatory Department",
            raw_statement=(
                "Financial transaction records must be retained for seven years."
            ),
            context="Compliance policy",
        ),
    ]

    print("\n" + "=" * 80)
    print("REQUIREMENT ELICITATION FINDINGS")
    print("=" * 80)

    for finding in findings:
        print(
            f"[{finding.technique.value}] "
            f"{finding.stakeholder}: {finding.raw_statement}"
        )

    return findings


# =============================================================================
# SECTION 5: TRANSFORMING RAW STATEMENTS INTO REQUIREMENTS
# =============================================================================


def transform_vague_statement() -> Tuple[str, str]:
    """
    Demonstrates transformation from ambiguity to measurable specification.

    A vague requirement:
        "The system should be fast."

    Problems:
        - What does "fast" mean?
        - Which operation is being measured?
        - Under what workload?
        - What percentage of users is considered?
        - How will it be tested?

    A measurable replacement:
        "The system shall display the checkout confirmation page within
         2 seconds for 95% of requests under normal operating load."
    """

    vague_requirement = "The checkout process should be very fast."

    measurable_requirement = (
        "The system shall display the checkout confirmation page within "
        "2 seconds for at least 95% of requests when the number of concurrent "
        "users is less than or equal to 5,000."
    )

    return vague_requirement, measurable_requirement


# =============================================================================
# SECTION 6: REQUIREMENT QUALITY ANALYSIS
# =============================================================================


AMBIGUOUS_TERMS = {
    "fast",
    "easy",
    "simple",
    "efficient",
    "user-friendly",
    "quick",
    "quickly",
    "secure",
    "reliable",
    "appropriate",
    "sufficient",
    "minimal",
    "maximum",
    "best",
    "high-quality",
    "modern",
}


@dataclass
class QualityIssue:
    """
    Represents a potential quality problem identified during requirement review.
    """

    issue_type: str
    message: str
    severity: str


def detect_ambiguous_language(requirement: Requirement) -> List[QualityIssue]:
    """
    Searches for commonly ambiguous terms.

    This is not a complete natural-language analysis system. It demonstrates
    why automated checks can support human requirement reviews.
    """

    issues = []
    normalized_text = requirement.description.lower()

    for term in AMBIGUOUS_TERMS:
        if term in normalized_text:
            issues.append(
                QualityIssue(
                    issue_type="Ambiguity",
                    message=(
                        f"The requirement contains the potentially ambiguous "
                        f"term '{term}'."
                    ),
                    severity="Medium",
                )
            )

    return issues


def detect_multiple_obligations(requirement: Requirement) -> List[QualityIssue]:
    """
    Detects a common requirement-writing problem.

    A statement such as:

        "The system shall validate the order and process payment and send an
        email and update inventory."

    contains several obligations. A failure in one part makes verification and
    traceability difficult.

    The function performs a simple heuristic analysis.
    """

    issues = []

    conjunction_count = len(
        re.findall(r"\b(and|or)\b", requirement.description.lower())
    )

    if conjunction_count >= 3:
        issues.append(
            QualityIssue(
                issue_type="Compound Requirement",
                message=(
                    "The requirement may contain multiple independent "
                    "obligations and may need decomposition."
                ),
                severity="Medium",
            )
        )

    return issues


def detect_missing_acceptance_criteria(
    requirement: Requirement,
) -> List[QualityIssue]:
    """
    A requirement without verification criteria may be difficult to test.
    """

    if not requirement.acceptance_criteria:
        return [
            QualityIssue(
                issue_type="Missing Acceptance Criteria",
                message=(
                    "The requirement does not define acceptance criteria."
                ),
                severity="High",
            )
        ]

    return []


def analyze_requirement_quality(
    requirement: Requirement,
) -> List[QualityIssue]:
    """
    Runs multiple quality checks.
    """

    issues = []

    issues.extend(detect_ambiguous_language(requirement))
    issues.extend(detect_multiple_obligations(requirement))
    issues.extend(detect_missing_acceptance_criteria(requirement))

    return issues


# =============================================================================
# SECTION 7: FUNCTIONAL REQUIREMENTS
# =============================================================================


def demonstrate_functional_requirement() -> Requirement:
    """
    Functional requirements describe system behavior.

    Typical structure:

        Actor/System + action + object + condition + expected result

    Example:
        "The system shall allow registered customers to reset their passwords
         after successful identity verification."
    """

    requirement = Requirement(
        requirement_id="FR-001",
        title="Password Reset",
        description=(
            "The system shall allow a registered customer to reset a forgotten "
            "password after successful identity verification."
        ),
        requirement_type=RequirementType.FUNCTIONAL,
        priority=RequirementPriority.MUST,
        source="Customer support and security stakeholders",
        rationale=(
            "Customers must be able to regain access without requiring manual "
            "support intervention."
        ),
        acceptance_criteria=[
            (
                "Given a registered customer requests password recovery, "
                "when identity verification succeeds, then the system shall "
                "allow the customer to create a new password."
            ),
            (
                "Given identity verification fails, when the customer attempts "
                "to reset the password, then the system shall deny the reset."
            ),
        ],
    )

    return requirement


# =============================================================================
# SECTION 8: NON-FUNCTIONAL REQUIREMENTS
# =============================================================================


class QualityAttribute(Enum):
    """
    Common quality attributes for non-functional requirements.
    """

    PERFORMANCE = "Performance"
    SECURITY = "Security"
    AVAILABILITY = "Availability"
    RELIABILITY = "Reliability"
    USABILITY = "Usability"
    SCALABILITY = "Scalability"
    MAINTAINABILITY = "Maintainability"
    COMPATIBILITY = "Compatibility"
    ACCESSIBILITY = "Accessibility"


@dataclass
class NonFunctionalRequirement:
    """
    Represents a measurable quality requirement.
    """

    requirement: Requirement
    quality_attribute: QualityAttribute
    measurement: str
    threshold: str


def demonstrate_non_functional_requirement() -> NonFunctionalRequirement:
    """
    Non-functional requirements should avoid vague quality claims.

    Poor:
        "The application shall be highly available."

    Better:
        "The application shall maintain 99.9% monthly availability,
         excluding scheduled maintenance announced at least 48 hours in advance."
    """

    requirement = Requirement(
        requirement_id="NFR-001",
        title="Checkout Availability",
        description=(
            "The checkout service shall maintain at least 99.9% monthly "
            "availability, excluding approved scheduled maintenance."
        ),
        requirement_type=RequirementType.NON_FUNCTIONAL,
        priority=RequirementPriority.MUST,
        source="Business and operations stakeholders",
        rationale=(
            "Checkout unavailability directly prevents revenue generation."
        ),
        acceptance_criteria=[
            (
                "Monthly service availability calculated from monitored service "
                "uptime shall be greater than or equal to 99.9%."
            ),
        ],
    )

    return NonFunctionalRequirement(
        requirement=requirement,
        quality_attribute=QualityAttribute.AVAILABILITY,
        measurement="Percentage of monitored service uptime per calendar month",
        threshold=">= 99.9%",
    )


# =============================================================================
# SECTION 9: USER STORIES AND ACCEPTANCE CRITERIA
# =============================================================================


@dataclass
class UserStory:
    """
    Agile-oriented representation of a requirement.

    Standard format:

        As a <role>,
        I want <capability>,
        so that <business value>.
    """

    story_id: str
    role: str
    capability: str
    business_value: str
    acceptance_criteria: List[str]
    priority: RequirementPriority

    def statement(self) -> str:
        return (
            f"As a {self.role}, I want {self.capability}, "
            f"so that {self.business_value}."
        )


def demonstrate_user_story() -> UserStory:
    """
    Demonstrates a user story with testable acceptance criteria.
    """

    return UserStory(
        story_id="US-001",
        role="registered customer",
        capability="view my order history",
        business_value="I can track my previous purchases",
        priority=RequirementPriority.SHOULD,
        acceptance_criteria=[
            (
                "Given the customer is authenticated, when the customer opens "
                "the order history page, then the system shall display orders "
                "belonging only to that customer."
            ),
            (
                "Orders shall be displayed with order identifier, date, status, "
                "and total amount."
            ),
            (
                "If the customer has no previous orders, the system shall display "
                "a message indicating that no orders are available."
            ),
        ],
    )


# =============================================================================
# SECTION 10: USE CASE MODELING
# =============================================================================


@dataclass
class UseCase:
    """
    A structured use case describing interactions between an actor and a system.
    """

    use_case_id: str
    name: str
    primary_actor: str
    preconditions: List[str]
    trigger: str
    main_flow: List[str]
    alternative_flows: List[str]
    postconditions: List[str]


def demonstrate_use_case() -> UseCase:
    """
    Demonstrates a complete checkout use case.
    """

    return UseCase(
        use_case_id="UC-001",
        name="Complete Purchase",
        primary_actor="Customer",
        preconditions=[
            "The customer has at least one item in the shopping cart.",
            "The selected items are available for purchase.",
        ],
        trigger="The customer selects the checkout action.",
        main_flow=[
            "The system displays the checkout page.",
            "The customer provides delivery information.",
            "The customer selects a payment method.",
            "The system validates the order.",
            "The system requests payment authorization.",
            "The payment provider approves the transaction.",
            "The system creates the order.",
            "The system displays an order confirmation.",
        ],
        alternative_flows=[
            (
                "If payment authorization fails, the system shall not create "
                "the order and shall inform the customer."
            ),
            (
                "If an item becomes unavailable before payment completion, "
                "the system shall request the customer to modify the order."
            ),
        ],
        postconditions=[
            "A successful purchase has a unique order identifier.",
            "Successful payment information is associated with the order.",
        ],
    )


# =============================================================================
# SECTION 11: REQUIREMENT CONFLICT DETECTION
# =============================================================================


@dataclass
class RequirementConflict:
    """
    Represents a conflict between requirements.
    """

    requirement_a: str
    requirement_b: str
    description: str
    severity: str


def detect_simple_numeric_conflict(
    requirement_a: Requirement,
    requirement_b: Requirement,
) -> Optional[RequirementConflict]:
    """
    Demonstrates a simplified conflict detector.

    Real conflict analysis requires domain understanding.

    This example detects contradictory statements about maximum password
    length.
    """

    text_a = requirement_a.description.lower()
    text_b = requirement_b.description.lower()

    pattern = r"maximum password length.*?(\d+)"

    match_a = re.search(pattern, text_a)
    match_b = re.search(pattern, text_b)

    if match_a and match_b:
        value_a = int(match_a.group(1))
        value_b = int(match_b.group(1))

        if value_a != value_b:
            return RequirementConflict(
                requirement_a=requirement_a.requirement_id,
                requirement_b=requirement_b.requirement_id,
                description=(
                    f"Conflicting maximum password lengths: "
                    f"{value_a} versus {value_b}."
                ),
                severity="High",
            )

    return None


# =============================================================================
# SECTION 12: PRIORITIZATION
# =============================================================================


@dataclass
class WeightedRequirement:
    """
    Requirement prioritization using weighted criteria.
    """

    requirement: Requirement
    business_value: int
    urgency: int
    risk_reduction: int
    implementation_cost: int

    def score(self) -> float:
        """
        A simplified weighted prioritization formula.

        Higher value, urgency, and risk reduction increase priority.
        Higher implementation cost reduces the resulting score.

        This formula is illustrative rather than universally correct.
        """

        value_score = self.business_value * 0.4
        urgency_score = self.urgency * 0.3
        risk_score = self.risk_reduction * 0.2
        cost_penalty = self.implementation_cost * 0.1

        return value_score + urgency_score + risk_score - cost_penalty


def demonstrate_prioritization(
    requirements: List[Requirement],
) -> List[WeightedRequirement]:
    """
    Demonstrates quantitative prioritization.
    """

    weighted_requirements = [
        WeightedRequirement(
            requirement=requirements[0],
            business_value=10,
            urgency=9,
            risk_reduction=8,
            implementation_cost=5,
        ),
        WeightedRequirement(
            requirement=requirements[1],
            business_value=8,
            urgency=6,
            risk_reduction=5,
            implementation_cost=3,
        ),
        WeightedRequirement(
            requirement=requirements[2],
            business_value=6,
            urgency=4,
            risk_reduction=7,
            implementation_cost=2,
        ),
    ]

    return sorted(
        weighted_requirements,
        key=lambda item: item.score(),
        reverse=True,
    )


# =============================================================================
# SECTION 13: VALIDATION
# =============================================================================


@dataclass
class ValidationResult:
    """
    Result of validating a requirement.
    """

    requirement_id: str
    passed: bool
    issues: List[QualityIssue]


class RequirementValidator:
    """
    Performs basic requirement validation.

    Validation asks questions such as:

    - Is the requirement correct?
    - Is it complete?
    - Is it consistent?
    - Is it feasible?
    - Is it necessary?
    - Is it unambiguous?
    - Is it testable?
    - Is it traceable?
    """

    def validate(self, requirement: Requirement) -> ValidationResult:
        """
        Executes automated quality checks.
        """

        issues = analyze_requirement_quality(requirement)

        if not requirement.requirement_id:
            issues.append(
                QualityIssue(
                    issue_type="Missing Identifier",
                    message="The requirement has no unique identifier.",
                    severity="High",
                )
            )

        if not requirement.title.strip():
            issues.append(
                QualityIssue(
                    issue_type="Missing Title",
                    message="The requirement has no meaningful title.",
                    severity="Medium",
                )
            )

        if not requirement.description.strip():
            issues.append(
                QualityIssue(
                    issue_type="Missing Description",
                    message="The requirement description is empty.",
                    severity="Critical",
                )
            )

        critical_or_high = {
            "Critical",
            "High",
        }

        passed = not any(
            issue.severity in critical_or_high
            for issue in issues
        )

        return ValidationResult(
            requirement_id=requirement.requirement_id,
            passed=passed,
            issues=issues,
        )


# =============================================================================
# SECTION 14: TRACEABILITY
# =============================================================================


class TraceabilityMatrix:
    """
    Maintains relationships between requirements and downstream artifacts.

    Common traceability links include:

        Business Goal -> Requirement
        Requirement -> Design Component
        Requirement -> User Story
        Requirement -> Test Case
        Requirement -> Release
    """

    def __init__(self) -> None:
        self.links: Dict[str, Set[str]] = {}

    def add_link(self, source_id: str, target_id: str) -> None:
        """
        Adds a traceability relationship.
        """

        self.links.setdefault(source_id, set()).add(target_id)

    def get_links(self, source_id: str) -> Set[str]:
        """
        Returns artifacts linked to a source.
        """

        return self.links.get(source_id, set())

    def impact_analysis(self, changed_requirement_id: str) -> Set[str]:
        """
        Returns directly linked artifacts that may require review.

        Real systems often require transitive graph analysis.
        """

        return self.get_links(changed_requirement_id)


def demonstrate_traceability() -> TraceabilityMatrix:
    """
    Creates a sample traceability matrix.
    """

    matrix = TraceabilityMatrix()

    matrix.add_link("BUS-001", "FR-001")
    matrix.add_link("FR-001", "DESIGN-AUTH-001")
    matrix.add_link("FR-001", "TC-001")
    matrix.add_link("FR-001", "TC-002")
    matrix.add_link("NFR-001", "TC-PERF-001")

    return matrix


# =============================================================================
# SECTION 15: CHANGE MANAGEMENT
# =============================================================================


@dataclass
class ChangeRequest:
    """
    Represents a proposed requirement change.
    """

    change_id: str
    requirement_id: str
    requested_by: str
    reason: str
    proposed_change: str
    business_impact: str
    technical_impact: str
    risk_impact: str
    approved: bool = False


class ChangeManager:
    """
    Maintains a basic requirement change process.
    """

    def __init__(self) -> None:
        self.change_requests: Dict[str, ChangeRequest] = {}

    def submit_change(
        self,
        requirement_id: str,
        requested_by: str,
        reason: str,
        proposed_change: str,
        business_impact: str,
        technical_impact: str,
        risk_impact: str,
    ) -> ChangeRequest:
        """
        Creates and stores a change request.
        """

        change_id = f"CR-{uuid.uuid4().hex[:8].upper()}"

        change_request = ChangeRequest(
            change_id=change_id,
            requirement_id=requirement_id,
            requested_by=requested_by,
            reason=reason,
            proposed_change=proposed_change,
            business_impact=business_impact,
            technical_impact=technical_impact,
            risk_impact=risk_impact,
        )

        self.change_requests[change_id] = change_request

        return change_request

    def approve_change(
        self,
        change_id: str,
        requirement: Requirement,
    ) -> None:
        """
        Approves a change and updates the requirement.

        In production environments, approval may require workflow controls,
        access controls, audit logs, and multiple approvers.
        """

        if change_id not in self.change_requests:
            raise KeyError(f"Unknown change request: {change_id}")

        change_request = self.change_requests[change_id]

        requirement.update_description(
            change_request.proposed_change
        )

        change_request.approved = True


# =============================================================================
# SECTION 16: REQUIREMENT DEPENDENCY ANALYSIS
# =============================================================================


class DependencyGraph:
    """
    Directed graph representing requirement dependencies.

    If A depends on B, B should generally be considered before A.
    """

    def __init__(self) -> None:
        self.dependencies: Dict[str, Set[str]] = {}

    def add_requirement(self, requirement_id: str) -> None:
        """
        Adds a requirement node.
        """

        self.dependencies.setdefault(requirement_id, set())

    def add_dependency(
        self,
        requirement_id: str,
        depends_on: str,
    ) -> None:
        """
        States that requirement_id depends on depends_on.
        """

        self.add_requirement(requirement_id)
        self.add_requirement(depends_on)

        self.dependencies[requirement_id].add(depends_on)

    def detect_cycle(self) -> bool:
        """
        Detects circular dependencies using depth-first search.

        Example circular dependency:

            A depends on B
            B depends on C
            C depends on A

        Circular dependencies can indicate problematic planning or incorrect
        decomposition.
        """

        visited: Set[str] = set()
        recursion_stack: Set[str] = set()

        def visit(node: str) -> bool:
            if node in recursion_stack:
                return True

            if node in visited:
                return False

            visited.add(node)
            recursion_stack.add(node)

            for dependency in self.dependencies.get(node, set()):
                if visit(dependency):
                    return True

            recursion_stack.remove(node)

            return False

        return any(
            visit(node)
            for node in self.dependencies
            if node not in visited
        )

    def dependency_order(self) -> List[str]:
        """
        Produces a dependency-aware order.

        Raises ValueError when circular dependencies exist.
        """

        if self.detect_cycle():
            raise ValueError(
                "Cannot produce dependency order because a cycle exists."
            )

        visited: Set[str] = set()
        ordered: List[str] = []

        def visit(node: str) -> None:
            if node in visited:
                return

            visited.add(node)

            for dependency in self.dependencies[node]:
                visit(dependency)

            ordered.append(node)

        for node in self.dependencies:
            visit(node)

        return ordered


# =============================================================================
# SECTION 17: RISK ANALYSIS
# =============================================================================


class RiskLevel(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


@dataclass
class RequirementRisk:
    """
    Risk associated with implementing or misunderstanding a requirement.
    """

    risk_id: str
    description: str
    probability: int
    impact: int
    mitigation: str

    def score(self) -> int:
        """
        Simple probability-impact risk score.

        Probability and impact are assumed to be between 1 and 5.
        """

        return self.probability * self.impact

    def level(self) -> RiskLevel:
        """
        Maps the numerical score to a qualitative level.
        """

        risk_score = self.score()

        if risk_score >= 20:
            return RiskLevel.CRITICAL

        if risk_score >= 12:
            return RiskLevel.HIGH

        if risk_score >= 6:
            return RiskLevel.MEDIUM

        return RiskLevel.LOW


# =============================================================================
# SECTION 18: REQUIREMENT DOCUMENTATION
# =============================================================================


class RequirementsDocument:
    """
    Represents a simplified Software Requirements Specification.

    A production SRS may contain:

    - Purpose
    - Scope
    - Definitions
    - Stakeholders
    - Business requirements
    - Functional requirements
    - Non-functional requirements
    - Constraints
    - Assumptions
    - Dependencies
    - Interfaces
    - Data requirements
    - Acceptance criteria
    - Traceability information
    """

    def __init__(
        self,
        project_name: str,
        version: str,
    ) -> None:
        self.project_name = project_name
        self.version = version
        self.requirements: List[Requirement] = []

    def add_requirement(self, requirement: Requirement) -> None:
        """
        Adds a requirement while preventing duplicate identifiers.
        """

        existing_ids = {
            item.requirement_id
            for item in self.requirements
        }

        if requirement.requirement_id in existing_ids:
            raise ValueError(
                f"Duplicate requirement identifier: "
                f"{requirement.requirement_id}"
            )

        self.requirements.append(requirement)

    def by_type(
        self,
        requirement_type: RequirementType,
    ) -> List[Requirement]:
        """
        Filters requirements by classification.
        """

        return [
            requirement
            for requirement in self.requirements
            if requirement.requirement_type == requirement_type
        ]

    def render_markdown(self) -> str:
        """
        Generates a Markdown representation.

        This demonstrates the principle that structured requirements can be
        transformed into human-readable documentation.
        """

        lines = [
            f"# {self.project_name}",
            "",
            f"Version: {self.version}",
            "",
            "## Requirements",
            "",
        ]

        for requirement in self.requirements:
            lines.extend(
                [
                    f"### {requirement.requirement_id}: "
                    f"{requirement.title}",
                    "",
                    f"**Type:** {requirement.requirement_type.value}",
                    "",
                    f"**Priority:** {requirement.priority.value}",
                    "",
                    f"**Status:** {requirement.status.value}",
                    "",
                    "**Description:**",
                    "",
                    requirement.description,
                    "",
                    "**Rationale:**",
                    "",
                    requirement.rationale,
                    "",
                    "**Acceptance Criteria:**",
                ]
            )

            for criterion in requirement.acceptance_criteria:
                lines.append(f"- {criterion}")

            lines.append("")

        return "\n".join(lines)


# =============================================================================
# SECTION 19: REQUIREMENT TESTING
# =============================================================================


@dataclass
class TestCase:
    """
    Test case linked to a requirement.
    """

    test_case_id: str
    requirement_id: str
    name: str
    preconditions: List[str]
    steps: List[str]
    expected_result: str


def demonstrate_requirement_to_test_case(
    requirement: Requirement,
) -> TestCase:
    """
    Converts a requirement into a testable verification artifact.
    """

    return TestCase(
        test_case_id="TC-001",
        requirement_id=requirement.requirement_id,
        name="Successful Password Reset",
        preconditions=[
            "A registered customer account exists.",
            "The customer can access the password recovery page.",
        ],
        steps=[
            "Enter the registered account identifier.",
            "Complete identity verification successfully.",
            "Enter a valid new password.",
            "Submit the password reset request.",
        ],
        expected_result=(
            "The system updates the password and confirms successful reset."
        ),
    )


# =============================================================================
# SECTION 20: REQUIREMENT REPOSITORY
# =============================================================================


class RequirementRepository:
    """
    In-memory repository for requirement management.

    Production systems would typically persist this information in a database
    or specialized requirements management platform.
    """

    def __init__(self) -> None:
        self.requirements: Dict[str, Requirement] = {}

    def add(self, requirement: Requirement) -> None:
        """
        Adds a requirement.
        """

        if requirement.requirement_id in self.requirements:
            raise ValueError(
                f"Requirement {requirement.requirement_id} already exists."
            )

        self.requirements[requirement.requirement_id] = requirement

    def get(self, requirement_id: str) -> Requirement:
        """
        Retrieves a requirement.

        Raises KeyError for unknown identifiers.
        """

        return self.requirements[requirement_id]

    def search(self, keyword: str) -> List[Requirement]:
        """
        Performs simple keyword search.
        """

        keyword = keyword.lower()

        return [
            requirement
            for requirement in self.requirements.values()
            if keyword in requirement.title.lower()
            or keyword in requirement.description.lower()
        ]

    def update_status(
        self,
        requirement_id: str,
        status: RequirementStatus,
    ) -> None:
        """
        Updates lifecycle status.
        """

        requirement = self.get(requirement_id)
        requirement.status = status
        requirement.updated_at = datetime.now()

    def all_requirements(self) -> List[Requirement]:
        """
        Returns requirements sorted by identifier.
        """

        return sorted(
            self.requirements.values(),
            key=lambda requirement: requirement.requirement_id,
        )


# =============================================================================
# SECTION 21: SECURITY REQUIREMENTS
# =============================================================================


def demonstrate_security_requirement() -> Requirement:
    """
    Security requirements should be specific and verifiable.

    Poor:
        "The system shall be secure."

    Better:
        Define authentication, authorization, encryption, logging,
        retention, and measurable security controls.
    """

    return Requirement(
        requirement_id="SEC-001",
        title="Administrative Access Control",
        description=(
            "The system shall require multi-factor authentication for all "
            "administrative accounts before granting access to administrative "
            "functions."
        ),
        requirement_type=RequirementType.NON_FUNCTIONAL,
        priority=RequirementPriority.MUST,
        source="Security team",
        rationale=(
            "Administrative accounts can perform high-impact operations and "
            "require stronger authentication controls."
        ),
        acceptance_criteria=[
            (
                "An administrative user shall not access administrative "
                "functions until both required authentication factors succeed."
            ),
            (
                "Failed authentication attempts shall be recorded in the "
                "security audit log."
            ),
        ],
    )


# =============================================================================
# SECTION 22: PERFORMANCE REQUIREMENTS
# =============================================================================


def simulate_response_time_validation(
    response_times_seconds: List[float],
    threshold_seconds: float,
    required_percentage: float,
) -> bool:
    """
    Demonstrates measurable performance validation.

    Example:
        At least 95% of requests must complete within 2 seconds.
    """

    if not response_times_seconds:
        raise ValueError(
            "At least one response time measurement is required."
        )

    successful_requests = sum(
        response_time <= threshold_seconds
        for response_time in response_times_seconds
    )

    achieved_percentage = (
        successful_requests / len(response_times_seconds)
    ) * 100

    print(
        f"Performance result: {achieved_percentage:.2f}% "
        f"of requests completed within {threshold_seconds} seconds."
    )

    return achieved_percentage >= required_percentage


# =============================================================================
# SECTION 23: REQUIREMENT FEASIBILITY ANALYSIS
# =============================================================================


@dataclass
class FeasibilityAssessment:
    """
    Simplified feasibility assessment.

    Common dimensions include:

    - Technical feasibility
    - Economic feasibility
    - Operational feasibility
    - Legal feasibility
    - Schedule feasibility
    """

    requirement_id: str
    technical_score: int
    economic_score: int
    operational_score: int
    legal_score: int
    schedule_score: int
    notes: List[str]

    def average_score(self) -> float:
        """
        Calculates the average feasibility score.
        """

        scores = [
            self.technical_score,
            self.economic_score,
            self.operational_score,
            self.legal_score,
            self.schedule_score,
        ]

        return sum(scores) / len(scores)

    def is_feasible(
        self,
        minimum_average: float = 3.0,
    ) -> bool:
        """
        Determines whether the assessment reaches a minimum threshold.
        """

        return self.average_score() >= minimum_average


# =============================================================================
# SECTION 24: END-TO-END REQUIREMENTS ENGINEERING WORKFLOW
# =============================================================================


def build_sample_requirements() -> List[Requirement]:
    """
    Builds a sample collection representing multiple requirement categories.
    """

    requirements = [
        Requirement(
            requirement_id="BUS-001",
            title="Reduce Checkout Abandonment",
            description=(
                "The organization shall reduce checkout abandonment by "
                "improving the efficiency and reliability of the checkout "
                "process."
            ),
            requirement_type=RequirementType.BUSINESS,
            priority=RequirementPriority.MUST,
            source="Executive leadership",
            rationale="Checkout abandonment reduces completed sales.",
            acceptance_criteria=[
                (
                    "The business shall define and monitor checkout "
                    "abandonment metrics after deployment."
                ),
            ],
        ),
        Requirement(
            requirement_id="FR-002",
            title="Order Confirmation",
            description=(
                "The system shall generate an order confirmation after a "
                "successful payment authorization."
            ),
            requirement_type=RequirementType.FUNCTIONAL,
            priority=RequirementPriority.MUST,
            source="Customer experience workshop",
            rationale=(
                "Customers require confirmation that their purchase was "
                "successfully completed."
            ),
            acceptance_criteria=[
                (
                    "A unique order identifier shall be generated after "
                    "successful payment authorization."
                ),
                (
                    "The confirmation shall contain the order identifier "
                    "and order total."
                ),
            ],
        ),
        Requirement(
            requirement_id="NFR-002",
            title="Order Confirmation Performance",
            description=(
                "The system shall display the order confirmation within "
                "2 seconds for at least 95% of successful checkout requests."
            ),
            requirement_type=RequirementType.NON_FUNCTIONAL,
            priority=RequirementPriority.SHOULD,
            source="Product and operations teams",
            rationale=(
                "Delayed confirmation can cause duplicate customer actions "
                "and uncertainty."
            ),
            acceptance_criteria=[
                (
                    "Performance monitoring shall show that at least 95% of "
                    "successful checkout confirmations complete within 2 seconds."
                ),
            ],
        ),
        Requirement(
            requirement_id="CON-001",
            title="Supported Browser Constraint",
            description=(
                "The web application shall support the currently maintained "
                "versions of Chrome, Firefox, Edge, and Safari."
            ),
            requirement_type=RequirementType.CONSTRAINT,
            priority=RequirementPriority.MUST,
            source="Technology standards",
            rationale=(
                "Supported browsers define compatibility testing boundaries."
            ),
            acceptance_criteria=[
                (
                    "Regression testing shall be executed on the supported "
                    "browser versions."
                ),
            ],
        ),
    ]

    return requirements


def demonstrate_full_workflow() -> None:
    """
    Executes an end-to-end educational workflow.

    The workflow follows a simplified sequence:

        1. Identify stakeholders
        2. Elicit information
        3. Transform information into requirements
        4. Analyze quality
        5. Validate
        6. Prioritize
        7. Establish traceability
        8. Assess dependencies
        9. Document
        10. Connect requirements to tests
        11. Manage change
    """

    print("\n" + "#" * 80)
    print("REQUIREMENTS ENGINEERING END-TO-END WORKFLOW")
    print("#" * 80)

    stakeholders = demonstrate_stakeholder_analysis()
    findings = demonstrate_elicitation()

    vague, measurable = transform_vague_statement()

    print("\nVAGUE REQUIREMENT:")
    print(vague)

    print("\nMEASURABLE REQUIREMENT:")
    print(measurable)

    requirements = build_sample_requirements()

    password_requirement = demonstrate_functional_requirement()
    security_requirement = demonstrate_security_requirement()

    requirements.extend(
        [
            password_requirement,
            security_requirement,
        ]
    )

    print("\n" + "=" * 80)
    print("REQUIREMENT QUALITY ANALYSIS")
    print("=" * 80)

    for requirement in requirements:
        issues = analyze_requirement_quality(requirement)

        print(
            f"\n{requirement.requirement_id}: "
            f"{requirement.title}"
        )

        if not issues:
            print("  No automated quality issues detected.")

        for issue in issues:
            print(
                f"  [{issue.severity}] "
                f"{issue.issue_type}: {issue.message}"
            )

    print("\n" + "=" * 80)
    print("REQUIREMENT VALIDATION")
    print("=" * 80)

    validator = RequirementValidator()

    for requirement in requirements:
        result = validator.validate(requirement)

        print(
            f"{result.requirement_id}: "
            f"{'PASS' if result.passed else 'REVIEW REQUIRED'}"
        )

    print("\n" + "=" * 80)
    print("PRIORITIZATION")
    print("=" * 80)

    prioritized = demonstrate_prioritization(
        requirements[:3]
    )

    for item in prioritized:
        print(
            f"{item.requirement.requirement_id}: "
            f"score={item.score():.2f}"
        )

    print("\n" + "=" * 80)
    print("TRACEABILITY")
    print("=" * 80)

    traceability = demonstrate_traceability()

    affected_artifacts = traceability.impact_analysis(
        "FR-001"
    )

    print(
        "Artifacts affected by changes to FR-001:"
    )

    for artifact in sorted(affected_artifacts):
        print(f"  - {artifact}")

    print("\n" + "=" * 80)
    print("DEPENDENCY ANALYSIS")
    print("=" * 80)

    graph = DependencyGraph()

    graph.add_dependency("FR-002", "FR-001")
    graph.add_dependency("NFR-002", "FR-002")
    graph.add_dependency("SEC-001", "FR-001")

    print(
        f"Circular dependency detected: "
        f"{graph.detect_cycle()}"
    )

    print(
        "Suggested dependency order:"
    )

    for requirement_id in graph.dependency_order():
        print(f"  - {requirement_id}")

    print("\n" + "=" * 80)
    print("RISK ANALYSIS")
    print("=" * 80)

    risks = [
        RequirementRisk(
            risk_id="RISK-001",
            description=(
                "Payment requirements may be misunderstood because the "
                "payment provider interface is externally controlled."
            ),
            probability=4,
            impact=5,
            mitigation=(
                "Validate interface requirements with the payment provider "
                "and perform integration testing."
            ),
        ),
        RequirementRisk(
            risk_id="RISK-002",
            description=(
                "Stakeholders may disagree about acceptable checkout "
                "performance."
            ),
            probability=3,
            impact=4,
            mitigation=(
                "Define measurable performance targets and obtain stakeholder "
                "approval."
            ),
        ),
    ]

    for risk in risks:
        print(
            f"{risk.risk_id}: "
            f"score={risk.score()}, level={risk.level().value}"
        )

    print("\n" + "=" * 80)
    print("PERFORMANCE VALIDATION")
    print("=" * 80)

    response_times = [
        1.1,
        1.5,
        1.8,
        2.1,
        1.9,
        1.4,
        1.7,
        1.6,
        2.5,
        1.2,
    ]

    passed = simulate_response_time_validation(
        response_times_seconds=response_times,
        threshold_seconds=2.0,
        required_percentage=80.0,
    )

    print(f"Performance requirement passed: {passed}")

    print("\n" + "=" * 80)
    print("FEASIBILITY ANALYSIS")
    print("=" * 80)

    feasibility = FeasibilityAssessment(
        requirement_id="FR-002",
        technical_score=5,
        economic_score=4,
        operational_score=4,
        legal_score=5,
        schedule_score=3,
        notes=[
            "Existing payment infrastructure supports the requirement.",
            "Integration testing is required.",
        ],
    )

    print(
        f"Average feasibility score: "
        f"{feasibility.average_score():.2f}"
    )

    print(
        f"Feasible according to threshold: "
        f"{feasibility.is_feasible()}"
    )

    print("\n" + "=" * 80)
    print("REQUIREMENT REPOSITORY")
    print("=" * 80)

    repository = RequirementRepository()

    for requirement in requirements:
        repository.add(requirement)

    search_results = repository.search("password")

    for result in search_results:
        print(
            f"Found requirement: "
            f"{result.requirement_id} - {result.title}"
        )

    repository.update_status(
        "FR-001",
        RequirementStatus.VALIDATED,
    )

    print(
        f"FR-001 status: "
        f"{repository.get('FR-001').status.value}"
    )

    print("\n" + "=" * 80)
    print("CHANGE MANAGEMENT")
    print("=" * 80)

    change_manager = ChangeManager()

    change_request = change_manager.submit_change(
        requirement_id="NFR-002",
        requested_by="Operations Team",
        reason=(
            "Peak traffic analysis requires a more explicit workload condition."
        ),
        proposed_change=(
            "The system shall display the order confirmation within 2 seconds "
            "for at least 95% of successful checkout requests when concurrent "
            "checkout sessions do not exceed 5,000."
        ),
        business_impact="Improves clarity of the service expectation.",
        technical_impact=(
            "Performance testing must simulate the specified workload."
        ),
        risk_impact=(
            "The requirement may require infrastructure scaling."
        ),
    )

    requirement_to_change = repository.get("NFR-002")

    old_version = requirement_to_change.version

    change_manager.approve_change(
        change_id=change_request.change_id,
        requirement=requirement_to_change,
    )

    print(
        f"Requirement version changed from "
        f"{old_version} to {requirement_to_change.version}."
    )

    print(
        f"Change approved: {change_request.approved}"
    )

    print("\n" + "=" * 80)
    print("REQUIREMENT DOCUMENTATION")
    print("=" * 80)

    document = RequirementsDocument(
        project_name="Online Commerce System Requirements",
        version="1.0",
    )

    for requirement in repository.all_requirements():
        document.add_requirement(requirement)

    markdown_document = document.render_markdown()

    print(
        f"Generated requirements document containing "
        f"{len(document.requirements)} requirements."
    )

    print("\n" + "=" * 80)
    print("REQUIREMENT-TO-TEST TRACEABILITY")
    print("=" * 80)

    test_case = demonstrate_requirement_to_test_case(
        password_requirement
    )

    print(
        f"Test case {test_case.test_case_id} verifies "
        f"{test_case.requirement_id}."
    )

    print("\n" + "=" * 80)
    print("USER STORY")
    print("=" * 80)

    user_story = demonstrate_user_story()

    print(user_story.statement())

    for criterion in user_story.acceptance_criteria:
        print(f"  - {criterion}")

    print("\n" + "=" * 80)
    print("USE CASE")
    print("=" * 80)

    use_case = demonstrate_use_case()

    print(
        f"{use_case.use_case_id}: {use_case.name}"
    )

    print(
        f"Primary actor: {use_case.primary_actor}"
    )

    print("Main flow:")

    for step_number, step in enumerate(
        use_case.main_flow,
        start=1,
    ):
        print(f"  {step_number}. {step}")


# =============================================================================
# SECTION 25: EDGE CASE DEMONSTRATIONS
# =============================================================================


def demonstrate_edge_cases() -> None:
    """
    Demonstrates important exceptions and unusual situations.
    """

    print("\n" + "#" * 80)
    print("REQUIREMENTS ENGINEERING EDGE CASES")
    print("#" * 80)

    repository = RequirementRepository()

    requirement = Requirement(
        requirement_id="EDGE-001",
        title="Example Requirement",
        description=(
            "The system shall store submitted information."
        ),
        requirement_type=RequirementType.FUNCTIONAL,
        priority=RequirementPriority.SHOULD,
        source="Example stakeholder",
        rationale="Demonstration",
        acceptance_criteria=[
            "Submitted information shall be retrievable.",
        ],
    )

    repository.add(requirement)

    try:
        repository.add(requirement)

    except ValueError as error:
        print(
            f"Duplicate requirement handling: {error}"
        )

    empty_graph = DependencyGraph()

    print(
        f"Empty dependency graph contains cycle: "
        f"{empty_graph.detect_cycle()}"
    )

    circular_graph = DependencyGraph()

    circular_graph.add_dependency("A", "B")
    circular_graph.add_dependency("B", "C")
    circular_graph.add_dependency("C", "A")

    print(
        f"Circular dependency graph contains cycle: "
        f"{circular_graph.detect_cycle()}"
    )

    try:
        circular_graph.dependency_order()

    except ValueError as error:
        print(
            f"Circular dependency handling: {error}"
        )

    try:
        simulate_response_time_validation(
            response_times_seconds=[],
            threshold_seconds=2.0,
            required_percentage=95.0,
        )

    except ValueError as error:
        print(
            f"Empty performance data handling: {error}"
        )


# =============================================================================
# SECTION 26: COMMON REQUIREMENT MISTAKES
# =============================================================================


def demonstrate_common_mistakes() -> None:
    """
    Demonstrates examples of poor requirement specifications.
    """

    examples = [
        (
            "Ambiguous",
            "The system shall be fast.",
            (
                "No measurable performance threshold, workload, or operation "
                "is defined."
            ),
        ),
        (
            "Implementation-biased",
            "The system shall use a specific programming language.",
            (
                "A technology choice may be a legitimate constraint, but it "
                "should not be imposed unless justified by business or "
                "technical constraints."
            ),
        ),
        (
            "Compound",
            (
                "The system shall validate the customer, process payment, "
                "send an email, and update inventory."
            ),
            (
                "Multiple independently testable obligations are combined "
                "into one requirement."
            ),
        ),
        (
            "Incomplete",
            "The system shall notify the user.",
            (
                "The recipient, event, notification channel, timing, and "
                "content are unspecified."
            ),
        ),
        (
            "Unverifiable",
            "The interface shall be user-friendly.",
            (
                "User-friendliness requires measurable usability criteria "
                "or explicit evaluation methods."
            ),
        ),
    ]

    print("\n" + "=" * 80)
    print("COMMON REQUIREMENT MISTAKES")
    print("=" * 80)

    for category, example, problem in examples:
        print(f"\nCategory: {category}")
        print(f"Requirement: {example}")
        print(f"Problem: {problem}")


# =============================================================================
# SECTION 27: MAIN PROGRAM
# =============================================================================


def main() -> None:
    """
    Executes the complete study demonstration.
    """

    demonstrate_full_workflow()
    demonstrate_edge_cases()
    demonstrate_common_mistakes()

    print("\n" + "#" * 80)
    print("COMPLETED REQUIREMENTS ENGINEERING STUDY DEMONSTRATION")
    print("#" * 80)


if __name__ == "__main__":
    main()
