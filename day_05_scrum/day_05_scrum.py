"""
SCRUM: ROLES, EVENTS, ARTIFACTS, AND SPRINT LIFECYCLE
=======================================================

A self-contained executable study guide for Scrum, progressing from beginner
concepts to advanced practical implementation.

The examples use only Python's standard library.

Scrum is a lightweight framework for generating value through adaptive
solutions for complex problems. This file models the core Scrum accountabilities,
events, artifacts, commitments, workflow, estimation, prioritization, quality,
and several advanced situations.

Important terminology:
- Product Owner: accountable for maximizing product value and effective
  Product Backlog management.
- Scrum Master: accountable for establishing Scrum and helping the Scrum Team
  and organization understand and use Scrum effectively.
- Developers: people in the Scrum Team who create a usable Increment each
  Sprint.
- Scrum Team: one Product Owner, one Scrum Master, and Developers.
- Sprint: a fixed-length event of one month or less in which a usable,
  valuable Increment is created.
- Product Backlog: an emergent, ordered list of what is needed to improve the
  product.
- Sprint Backlog: the Sprint Goal, selected Product Backlog Items, and the
  actionable plan for delivering the Increment.
- Increment: a concrete stepping stone toward the Product Goal that must meet
  the Definition of Done.
- Product Goal: the long-term objective for the product.
- Sprint Goal: the single objective for the Sprint.
- Definition of Done: a formal description of the state of the Increment when
  it meets the quality measures required for the product.

The script is educational. It models Scrum mechanics without pretending that
Scrum is a software library or that every organizational process can be
reduced to code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


# =============================================================================
# 1. SCRUM FUNDAMENTALS
# =============================================================================

print("=" * 78)
print("SCRUM STUDY GUIDE: FUNDAMENTALS TO ADVANCED PRACTICE")
print("=" * 78)


class ScrumValue(Enum):
    """
    The five Scrum values.

    Scrum depends on people behaving according to these values:
    Commitment, Focus, Openness, Respect, and Courage.
    """

    COMMITMENT = "Commitment"
    FOCUS = "Focus"
    OPENNESS = "Openness"
    RESPECT = "Respect"
    COURAGE = "Courage"


SCRUM_VALUES = {
    ScrumValue.COMMITMENT: "People commit to achieving the goals of the Scrum Team.",
    ScrumValue.FOCUS: "People focus on the work of the Sprint and the goals of the Scrum Team.",
    ScrumValue.OPENNESS: "The Scrum Team and stakeholders are open about the work and challenges.",
    ScrumValue.RESPECT: "People respect one another as capable, independent professionals.",
    ScrumValue.COURAGE: "People have the courage to do the right thing and work on difficult problems.",
}

print("\nTHE FIVE SCRUM VALUES")
for value, meaning in SCRUM_VALUES.items():
    print(f"- {value.value}: {meaning}")


# =============================================================================
# 2. EMPIRICISM: TRANSPARENCY, INSPECTION, ADAPTATION
# =============================================================================

@dataclass
class EmpiricalProcess:
    """
    A small model of Scrum's empirical process control.

    Scrum uses empiricism because complex work cannot reliably be planned
    completely in advance. Knowledge comes from experience and observation.
    """

    observation: str
    decision: str
    adaptation: str

    def describe(self) -> None:
        print(f"Observation: {self.observation}")
        print(f"Decision:    {self.decision}")
        print(f"Adaptation:  {self.adaptation}")


print("\nEMPIRICISM")
empirical_example = EmpiricalProcess(
    observation="Users abandon the checkout flow at the payment step.",
    decision="Inspect payment usability and technical failure data.",
    adaptation="Prioritize payment-flow improvements for upcoming work.",
)
empirical_example.describe()

print(
    "\nThe three pillars are transparency, inspection, and adaptation. "
    "Inspection without transparency is weak because hidden information "
    "prevents meaningful inspection. Adaptation without inspection is guesswork."
)


# =============================================================================
# 3. SCRUM TEAM AND ACCOUNTABILITIES
# =============================================================================

class Accountability(Enum):
    PRODUCT_OWNER = "Product Owner"
    SCRUM_MASTER = "Scrum Master"
    DEVELOPER = "Developer"


@dataclass
class TeamMember:
    name: str
    accountability: Accountability


@dataclass
class ScrumTeam:
    """
    A Scrum Team consists of one Product Owner, one Scrum Master, and Developers.

    The team is cross-functional: it has the skills necessary to create value
    during a Sprint. The team is self-managing: it decides internally who does
    what, when, and how.
    """

    product_owner: TeamMember
    scrum_master: TeamMember
    developers: List[TeamMember]

    def validate(self) -> List[str]:
        problems: List[str] = []

        if self.product_owner.accountability != Accountability.PRODUCT_OWNER:
            problems.append("The Product Owner accountability is invalid.")

        if self.scrum_master.accountability != Accountability.SCRUM_MASTER:
            problems.append("The Scrum Master accountability is invalid.")

        if not self.developers:
            problems.append("A Scrum Team requires Developers.")

        for developer in self.developers:
            if developer.accountability != Accountability.DEVELOPER:
                problems.append(
                    f"{developer.name} is listed as a Developer but has "
                    f"accountability {developer.accountability.value}."
                )

        return problems

    def show(self) -> None:
        print(f"Product Owner: {self.product_owner.name}")
        print(f"Scrum Master:  {self.scrum_master.name}")
        print("Developers:    " + ", ".join(d.name for d in self.developers))


team = ScrumTeam(
    product_owner=TeamMember("Priya", Accountability.PRODUCT_OWNER),
    scrum_master=TeamMember("Arjun", Accountability.SCRUM_MASTER),
    developers=[
        TeamMember("Maya", Accountability.DEVELOPER),
        TeamMember("Rahul", Accountability.DEVELOPER),
        TeamMember("Neha", Accountability.DEVELOPER),
    ],
)

print("\nSCRUM TEAM")
team.show()
print("Validation:", "valid" if not team.validate() else team.validate())


# =============================================================================
# 4. ACCOUNTABILITY DETAILS
# =============================================================================

print("\nACCOUNTABILITY DISTINCTIONS")

ACCOUNTABILITY_DESCRIPTIONS = {
    Accountability.PRODUCT_OWNER: [
        "Accountable for maximizing product value.",
        "Accountable for effective Product Backlog management.",
        "Develops and communicates the Product Goal.",
        "Creates and communicates Product Backlog Items.",
        "Orders Product Backlog Items.",
        "Ensures the Product Backlog is transparent, visible, and understood.",
        "May delegate Product Backlog management work, but accountability remains.",
    ],
    Accountability.SCRUM_MASTER: [
        "Accountable for establishing Scrum as defined in the Scrum Guide.",
        "Helps the Scrum Team improve effectiveness.",
        "Coaches team members in self-management and cross-functionality.",
        "Helps remove impediments.",
        "Facilitates useful Scrum events when needed.",
        "Helps the organization understand Scrum.",
    ],
    Accountability.DEVELOPER: [
        "Creates a plan for the Sprint, the Sprint Backlog.",
        "Instills quality by adhering to the Definition of Done.",
        "Adapts the plan toward the Sprint Goal.",
        "Holds one another accountable as professionals.",
        "Creates a usable Increment every Sprint.",
    ],
}

for accountability, responsibilities in ACCOUNTABILITY_DESCRIPTIONS.items():
    print(f"\n{accountability.value}")
    for responsibility in responsibilities:
        print(f"  - {responsibility}")


# =============================================================================
# 5. PRODUCT GOAL
# =============================================================================

@dataclass
class ProductGoal:
    description: str
    achieved: bool = False

    def status(self) -> str:
        return "ACHIEVED" if self.achieved else "ACTIVE"


product_goal = ProductGoal(
    "Increase the percentage of customers who complete checkout successfully."
)

print("\nPRODUCT GOAL")
print(product_goal.description)
print("Status:", product_goal.status())

print(
    "\nThe Product Goal describes a future state of the product. "
    "It provides a longer-term target for the Scrum Team."
)


# =============================================================================
# 6. PRODUCT BACKLOG
# =============================================================================

class Priority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class ProductBacklogItem:
    id: str
    title: str
    value: int
    effort: int
    priority: Priority
    acceptance_criteria: List[str] = field(default_factory=list)
    status: str = "Ready"

    def value_density(self) -> float:
        """
        A simple prioritization aid.

        This is NOT a Scrum-mandated formula. It demonstrates how a Product
        Owner might reason about value relative to estimated effort.
        """
        if self.effort <= 0:
            return float("inf")
        return self.value / self.effort

    def describe(self) -> None:
        print(
            f"{self.id}: {self.title} | value={self.value} | "
            f"effort={self.effort} | priority={self.priority.name}"
        )


backlog = [
    ProductBacklogItem(
        "PBI-01",
        "Simplify payment form",
        value=100,
        effort=5,
        priority=Priority.CRITICAL,
        acceptance_criteria=[
            "Payment fields are reduced to essential information.",
            "Validation messages are understandable.",
        ],
    ),
    ProductBacklogItem(
        "PBI-02",
        "Add saved payment method",
        value=85,
        effort=8,
        priority=Priority.HIGH,
        acceptance_criteria=[
            "A customer can securely select a saved method.",
            "Sensitive payment information is not stored directly by the application.",
        ],
    ),
    ProductBacklogItem(
        "PBI-03",
        "Improve order confirmation",
        value=60,
        effort=3,
        priority=Priority.HIGH,
    ),
    ProductBacklogItem(
        "PBI-04",
        "Add delivery preference",
        value=45,
        effort=5,
        priority=Priority.MEDIUM,
    ),
    ProductBacklogItem(
        "PBI-05",
        "Add promotional animation",
        value=10,
        effort=8,
        priority=Priority.LOW,
    ),
]

print("\nPRODUCT BACKLOG")
for item in backlog:
    item.describe()


# =============================================================================
# 7. ORDERING VS NUMERICAL PRIORITY
# =============================================================================

def order_backlog(items: Sequence[ProductBacklogItem]) -> List[ProductBacklogItem]:
    """
    Demonstrates one possible ordering approach.

    In real Scrum, Product Backlog ordering is a Product Owner decision and
    cannot be reduced to a universal mathematical formula.
    """
    return sorted(
        items,
        key=lambda item: (-item.priority.value, -item.value_density()),
    )


ordered_backlog = order_backlog(backlog)

print("\nORDERED BACKLOG")
for position, item in enumerate(ordered_backlog, start=1):
    print(
        f"{position}. {item.id} | {item.title} | "
        f"value density={item.value_density():.2f}"
    )

print(
    "\nImportant distinction: Product Backlog ordering is not simply "
    "'assign priority numbers and sort.' Value, risk, dependencies, "
    "learning, market timing, compliance, and other product considerations "
    "may influence ordering."
)


# =============================================================================
# 8. USER STORIES AND PRODUCT BACKLOG ITEMS
# =============================================================================

@dataclass
class UserStory:
    """
    User stories are a common Product Backlog Item format.

    Scrum itself does not require user stories. A PBI can use whatever form
    communicates useful work clearly.
    """

    as_a: str
    i_want: str
    so_that: str

    def statement(self) -> str:
        return (
            f"As a {self.as_a}, I want {self.i_want}, "
            f"so that {self.so_that}."
        )


story = UserStory(
    as_a="customer",
    i_want="to pay using a simple form",
    so_that="I can complete my purchase with less friction",
)

print("\nUSER STORY")
print(story.statement())

print(
    "\nA common mistake is treating the user-story template as Scrum itself. "
    "It is only one technique for expressing a Product Backlog Item."
)


# =============================================================================
# 9. DEFINITION OF DONE
# =============================================================================

@dataclass
class DefinitionOfDone:
    """
    The Definition of Done describes the quality state required of an Increment.
    """

    criteria: List[str]

    def evaluate(self, checks: Dict[str, bool]) -> Tuple[bool, List[str]]:
        missing: List[str] = []

        for criterion in self.criteria:
            if not checks.get(criterion, False):
                missing.append(criterion)

        return not missing, missing


definition_of_done = DefinitionOfDone(
    criteria=[
        "Code reviewed",
        "Automated tests pass",
        "Security checks pass",
        "Acceptance criteria satisfied",
        "Documentation updated",
        "Deployable to production",
    ]
)

print("\nDEFINITION OF DONE")
for criterion in definition_of_done.criteria:
    print(f"- {criterion}")

example_checks = {
    "Code reviewed": True,
    "Automated tests pass": True,
    "Security checks pass": True,
    "Acceptance criteria satisfied": True,
    "Documentation updated": False,
    "Deployable to production": True,
}

done, missing = definition_of_done.evaluate(example_checks)

print("\nDefinition of Done satisfied:", done)
print("Missing criteria:", missing)

print(
    "\nA Product Backlog Item that does not meet the Definition of Done "
    "does not become part of a usable Increment."
)


# =============================================================================
# 10. SPRINT GOAL
# =============================================================================

@dataclass
class SprintGoal:
    description: str

    def is_clear(self) -> bool:
        return bool(self.description.strip())


sprint_goal = SprintGoal(
    "Reduce payment friction by delivering a simpler checkout payment flow."
)

print("\nSPRINT GOAL")
print(sprint_goal.description)
print("Clear:", sprint_goal.is_clear())

print(
    "\nThe Sprint Goal creates coherence and focus. The Developers have "
    "flexibility in how they accomplish the work, while the Sprint Goal "
    "provides the objective that guides decisions."
)


# =============================================================================
# 11. SPRINT BACKLOG
# =============================================================================

@dataclass
class SprintBacklog:
    sprint_goal: SprintGoal
    selected_items: List[ProductBacklogItem]
    plan: Dict[str, List[str]]

    def show(self) -> None:
        print("Sprint Goal:", self.sprint_goal.description)
        print("Selected Product Backlog Items:")
        for item in self.selected_items:
            print(f"  - {item.id}: {item.title}")

        print("Plan:")
        for item_id, tasks in self.plan.items():
            print(f"  {item_id}:")
            for task in tasks:
                print(f"    * {task}")


sprint_backlog = SprintBacklog(
    sprint_goal=sprint_goal,
    selected_items=[ordered_backlog[0], ordered_backlog[1]],
    plan={
        "PBI-01": [
            "Review current checkout flow",
            "Implement simplified form",
            "Implement validation",
            "Write automated tests",
        ],
        "PBI-02": [
            "Design saved-method interaction",
            "Integrate payment provider tokenization",
            "Implement selection flow",
            "Test security and error cases",
        ],
    },
)

print("\nSPRINT BACKLOG")
sprint_backlog.show()

print(
    "\nThe Sprint Backlog consists of the Sprint Goal, the selected Product "
    "Backlog Items, and an actionable plan for delivering the Increment."
)


# =============================================================================
# 12. SPRINT LIFECYCLE
# =============================================================================

print("\nSPRINT LIFECYCLE")
lifecycle = [
    "1. Product Goal provides long-term direction.",
    "2. Product Backlog contains ordered work.",
    "3. Sprint Planning establishes the Sprint Goal and Sprint Backlog.",
    "4. Developers work toward the Sprint Goal.",
    "5. Daily Scrum provides an opportunity to inspect progress and adapt the plan.",
    "6. Developers create an Increment that meets the Definition of Done.",
    "7. Sprint Review inspects the outcome with stakeholders and adapts future work.",
    "8. Sprint Retrospective inspects how the team worked and identifies improvements.",
    "9. The next Sprint begins immediately after the previous Sprint.",
]

for step in lifecycle:
    print(step)


# =============================================================================
# 13. SPRINT
# =============================================================================

@dataclass
class Sprint:
    number: int
    start_date: date
    duration_days: int
    goal: SprintGoal
    backlog: SprintBacklog

    @property
    def end_date(self) -> date:
        return self.start_date + timedelta(days=self.duration_days)

    def validate_duration(self) -> bool:
        # Scrum limits a Sprint to one month or less.
        # A month is not treated as exactly 30 calendar days by definition.
        return 1 <= self.duration_days <= 31

    def show(self) -> None:
        print(f"Sprint {self.number}")
        print(f"Start: {self.start_date}")
        print(f"End:   {self.end_date}")
        print(f"Duration: {self.duration_days} days")
        print(f"Goal: {self.goal.description}")


sprint = Sprint(
    number=1,
    start_date=date(2026, 9, 7),
    duration_days=14,
    goal=sprint_goal,
    backlog=sprint_backlog,
)

print("\nSPRINT")
sprint.show()
print("Duration valid for this model:", sprint.validate_duration())


# =============================================================================
# 14. SPRINT PLANNING
# =============================================================================

@dataclass
class SprintPlanningDecision:
    why: str
    what: List[str]
    how: List[str]

    def show(self) -> None:
        print("WHY:")
        print(f"  {self.why}")
        print("WHAT:")
        for item in self.what:
            print(f"  - {item}")
        print("HOW:")
        for task in self.how:
            print(f"  - {task}")


planning = SprintPlanningDecision(
    why=sprint_goal.description,
    what=[
        "Simplify payment form",
        "Improve saved-payment experience",
    ],
    how=[
        "Developers inspect the work and determine a feasible plan.",
        "The plan is adjusted as more is learned during the Sprint.",
    ],
)

print("\nSPRINT PLANNING")
planning.show()

print(
    "\nSprint Planning addresses why the Sprint is valuable, what can be "
    "accomplished, and how the chosen work can be delivered."
)


# =============================================================================
# 15. DAILY SCRUM
# =============================================================================

@dataclass
class DailyScrumObservation:
    developer: str
    completed: List[str]
    next_focus: List[str]
    impediments: List[str]

    def inspect(self) -> None:
        print(f"\nDeveloper: {self.developer}")
        print("Completed:")
        for item in self.completed:
            print(f"  - {item}")
        print("Next focus:")
        for item in self.next_focus:
            print(f"  - {item}")
        print("Impediments:")
        if self.impediments:
            for item in self.impediments:
                print(f"  - {item}")
        else:
            print("  - None reported")


daily_observations = [
    DailyScrumObservation(
        "Maya",
        ["Payment form component"],
        ["Validation behavior"],
        [],
    ),
    DailyScrumObservation(
        "Rahul",
        ["Payment provider integration"],
        ["Error handling"],
        ["Sandbox API is intermittently unavailable"],
    ),
    DailyScrumObservation(
        "Neha",
        ["Automated checkout tests"],
        ["Security test coverage"],
        [],
    ),
]

print("\nDAILY SCRUM")
for observation in daily_observations:
    observation.inspect()

print(
    "\nThe Daily Scrum is a 15-minute event for the Developers. Its purpose "
    "is to inspect progress toward the Sprint Goal and adapt the Sprint "
    "Backlog as necessary. It is not a mandatory three-question reporting "
    "ceremony."
)


# =============================================================================
# 16. SPRINT REVIEW
# =============================================================================

@dataclass
class IncrementInspection:
    increment_name: str
    usable: bool
    done: bool
    stakeholder_feedback: List[str]

    def show(self) -> None:
        print(f"Increment: {self.increment_name}")
        print(f"Usable: {self.usable}")
        print(f"Meets Definition of Done: {self.done}")
        print("Stakeholder feedback:")
        for feedback in self.stakeholder_feedback:
            print(f"  - {feedback}")


review = IncrementInspection(
    increment_name="Simplified payment flow",
    usable=True,
    done=True,
    stakeholder_feedback=[
        "Customers understand the payment errors more easily.",
        "Mobile users still report unnecessary form steps.",
        "Consider reducing mobile-specific friction next.",
    ],
)

print("\nSPRINT REVIEW")
review.show()

print(
    "\nThe Sprint Review is a working session where the Scrum Team and "
    "stakeholders inspect the Sprint outcome and discuss what changed in "
    "the environment. The Product Backlog may be adjusted based on what "
    "is learned."
)


# =============================================================================
# 17. SPRINT RETROSPECTIVE
# =============================================================================

@dataclass
class Retrospective:
    went_well: List[str]
    problems: List[str]
    actions: List[str]

    def show(self) -> None:
        print("Went well:")
        for item in self.went_well:
            print(f"  + {item}")

        print("Problems:")
        for item in self.problems:
            print(f"  - {item}")

        print("Improvement actions:")
        for item in self.actions:
            print(f"  -> {item}")


retrospective = Retrospective(
    went_well=[
        "Developers collaborated directly on payment integration.",
        "Automated tests caught validation defects early.",
    ],
    problems=[
        "External sandbox failures delayed integration testing.",
        "Some acceptance criteria were clarified too late.",
    ],
    actions=[
        "Clarify payment acceptance criteria before Sprint Planning.",
        "Create a documented fallback procedure for external sandbox failures.",
    ],
)

print("\nSPRINT RETROSPECTIVE")
retrospective.show()

print(
    "\nThe Sprint Retrospective focuses on people, interactions, processes, "
    "tools, and the Definition of Done. Improvement actions should be "
    "specific enough to influence future work."
)


# =============================================================================
# 18. INCREMENT
# =============================================================================

@dataclass
class Increment:
    """
    An Increment is a concrete stepping stone toward the Product Goal.

    Multiple increments can be created during a Sprint. An Increment must be
    usable and meet the Definition of Done.
    """

    version: str
    features: List[str]
    meets_definition_of_done: bool

    def is_usable(self) -> bool:
        return self.meets_definition_of_done and bool(self.features)


increment = Increment(
    version="1.1",
    features=[
        "Simplified payment form",
        "Improved payment validation",
    ],
    meets_definition_of_done=True,
)

print("\nINCREMENT")
print("Version:", increment.version)
print("Features:", increment.features)
print("Usable:", increment.is_usable())


# =============================================================================
# 19. EVENTS AND THEIR PURPOSES
# =============================================================================

SCRUM_EVENTS = {
    "Sprint": "Container event in which all other Scrum events occur and an Increment is created.",
    "Sprint Planning": "Starts the Sprint by establishing the Sprint Goal, selected work, and plan.",
    "Daily Scrum": "Developers inspect progress toward the Sprint Goal and adapt the plan.",
    "Sprint Review": "Inspect the outcome and determine future adaptations with stakeholders.",
    "Sprint Retrospective": "Plan ways to increase quality and effectiveness.",
}

print("\nSCRUM EVENTS")
for event, purpose in SCRUM_EVENTS.items():
    print(f"- {event}: {purpose}")

print(
    "\nThe Sprint is itself an event. Sprint Planning, Daily Scrum, Sprint "
    "Review, and Sprint Retrospective are events within the Sprint."
)


# =============================================================================
# 20. ARTIFACTS AND COMMITMENTS
# =============================================================================

ARTIFACT_COMMITMENTS = {
    "Product Backlog": "Product Goal",
    "Sprint Backlog": "Sprint Goal",
    "Increment": "Definition of Done",
}

print("\nARTIFACTS AND THEIR COMMITMENTS")
for artifact, commitment in ARTIFACT_COMMITMENTS.items():
    print(f"- {artifact} -> {commitment}")

print(
    "\nThese relationships are important because each commitment increases "
    "transparency and provides a clear basis for inspection."
)


# =============================================================================
# 21. ESTIMATION AND STORY POINTS
# =============================================================================

FIBONACCI_SCALE = [1, 2, 3, 5, 8, 13, 21]

@dataclass
class Estimate:
    item_id: str
    story_points: int

    def validate(self) -> bool:
        return self.story_points in FIBONACCI_SCALE


estimates = [
    Estimate("PBI-01", 5),
    Estimate("PBI-02", 8),
    Estimate("PBI-03", 3),
]

print("\nESTIMATION")
for estimate in estimates:
    print(
        f"{estimate.item_id}: {estimate.story_points} points | "
        f"valid scale={estimate.validate()}"
    )

print(
    "\nStory points are a common estimation technique, not a mandatory Scrum "
    "artifact. Points are generally intended to express relative size or "
    "complexity rather than hours worked."
)


# =============================================================================
# 22. VELOCITY
# =============================================================================

@dataclass
class TeamVelocity:
    completed_points_by_sprint: List[int]

    def average(self) -> float:
        if not self.completed_points_by_sprint:
            return 0.0
        return sum(self.completed_points_by_sprint) / len(
            self.completed_points_by_sprint
        )

    def range(self) -> Tuple[int, int]:
        if not self.completed_points_by_sprint:
            return 0, 0
        return (
            min(self.completed_points_by_sprint),
            max(self.completed_points_by_sprint),
        )


velocity = TeamVelocity([18, 21, 19, 23, 20])

print("\nVELOCITY")
print("Sprint results:", velocity.completed_points_by_sprint)
print(f"Average: {velocity.average():.2f}")
print("Range:", velocity.range())

print(
    "\nVelocity is a planning metric rather than a Scrum requirement. "
    "It becomes misleading when used to compare teams, rank individuals, "
    "or pressure a team into artificially increasing estimates."
)


# =============================================================================
# 23. CAPACITY VS VELOCITY
# =============================================================================

@dataclass
class DeveloperCapacity:
    name: str
    available_hours: float

    def usable_capacity(self, focus_factor: float = 0.7) -> float:
        """
        Capacity is expressed in hours here only as an example planning aid.

        Focus factor is a modeling assumption, not a Scrum rule.
        """
        if not 0 <= focus_factor <= 1:
            raise ValueError("focus_factor must be between 0 and 1.")
        return self.available_hours * focus_factor


capacity = [
    DeveloperCapacity("Maya", 70),
    DeveloperCapacity("Rahul", 63),
    DeveloperCapacity("Neha", 56),
]

print("\nCAPACITY")
for person in capacity:
    print(
        f"{person.name}: available={person.available_hours}h, "
        f"modeled usable={person.usable_capacity():.1f}h"
    )

print(
    "\nCapacity describes available time or people. Velocity describes "
    "historical delivery of estimated work. They should not be treated as "
    "interchangeable measurements."
)


# =============================================================================
# 24. PRIORITIZATION: VALUE, RISK, AND COST OF DELAY
# =============================================================================

@dataclass
class PrioritizationFactors:
    business_value: float
    time_criticality: float
    risk_reduction: float
    effort: float

    def weighted_score(
        self,
        value_weight: float = 0.4,
        time_weight: float = 0.2,
        risk_weight: float = 0.2,
        effort_weight: float = 0.2,
    ) -> float:
        if self.effort <= 0:
            return float("inf")

        benefit = (
            self.business_value * value_weight
            + self.time_criticality * time_weight
            + self.risk_reduction * risk_weight
        )

        return benefit / (self.effort * effort_weight)


prioritization = PrioritizationFactors(
    business_value=90,
    time_criticality=80,
    risk_reduction=70,
    effort=8,
)

print("\nPRIORITIZATION MODEL")
print(f"Illustrative score: {prioritization.weighted_score():.2f}")

print(
    "\nThis is an illustrative decision-support model, not a Scrum rule. "
    "Product Owners must use product context rather than blindly applying "
    "a formula."
)


# =============================================================================
# 25. REFINEMENT
# =============================================================================

@dataclass
class BacklogRefinementActivity:
    """
    Product Backlog refinement is an ongoing activity, not one of the five
    formal Scrum events.
    """

    activities: List[str]

    def show(self) -> None:
        for activity in self.activities:
            print(f"- {activity}")


refinement = BacklogRefinementActivity(
    activities=[
        "Clarify Product Backlog Items.",
        "Split oversized items when useful.",
        "Add or revise acceptance information.",
        "Identify dependencies and uncertainties.",
        "Improve shared understanding.",
        "Update estimates when appropriate.",
    ]
)

print("\nPRODUCT BACKLOG REFINEMENT")
refinement.show()


# =============================================================================
# 26. SPLITTING LARGE BACKLOG ITEMS
# =============================================================================

def split_large_item(item: ProductBacklogItem) -> List[ProductBacklogItem]:
    """
    Example of splitting an oversized PBI.

    Splitting should preserve user/product value rather than simply dividing
    technical layers into separate tasks.
    """
    if item.effort < 13:
        return [item]

    midpoint_value = max(1, item.value // 2)

    return [
        ProductBacklogItem(
            id=item.id + "-A",
            title=item.title + " - essential flow",
            value=midpoint_value,
            effort=max(1, item.effort // 2),
            priority=item.priority,
        ),
        ProductBacklogItem(
            id=item.id + "-B",
            title=item.title + " - remaining flow",
            value=item.value - midpoint_value,
            effort=item.effort - max(1, item.effort // 2),
            priority=item.priority,
        ),
    ]


large_item = ProductBacklogItem(
    "PBI-06",
    "Build complete international checkout experience",
    value=100,
    effort=21,
    priority=Priority.HIGH,
)

print("\nSPLITTING AN OVERSIZED PBI")
for smaller_item in split_large_item(large_item):
    smaller_item.describe()

print(
    "\nA useful split often follows customer-visible slices. Splitting solely "
    "into 'frontend task', 'backend task', and 'testing task' can preserve "
    "technical decomposition without producing independently useful value."
)


# =============================================================================
# 27. SPRINT CANCELLATION
# =============================================================================

@dataclass
class SprintCancellation:
    sprint_number: int
    reason: str
    product_owner_approved: bool = True

    def can_cancel(self) -> bool:
        # A Sprint can be cancelled if its Sprint Goal becomes obsolete.
        # The Product Owner has the authority to cancel the Sprint.
        return self.product_owner_approved and bool(self.reason.strip())


cancellation = SprintCancellation(
    sprint_number=3,
    reason="A regulatory change makes the Sprint Goal obsolete.",
)

print("\nSPRINT CANCELLATION")
print("Can cancel:", cancellation.can_cancel())
print("Reason:", cancellation.reason)

print(
    "\nSprint cancellation is an exception rather than a routine mechanism "
    "for changing commitments whenever work becomes difficult."
)


# =============================================================================
# 28. CHANGES DURING A SPRINT
# =============================================================================

@dataclass
class SprintChangeDecision:
    change: str
    threatens_sprint_goal: bool
    can_adapt_without_destroying_goal: bool

    def decide(self) -> str:
        if self.threatens_sprint_goal and not self.can_adapt_without_destroying_goal:
            return "Discuss whether the Sprint Goal has become obsolete."
        return "Adapt the Sprint Backlog as necessary while protecting the Sprint Goal."


change_decision = SprintChangeDecision(
    change="A new payment error is discovered.",
    threatens_sprint_goal=False,
    can_adapt_without_destroying_goal=True,
)

print("\nCHANGE DURING SPRINT")
print(change_decision.decide())

print(
    "\nThe Sprint Backlog can be updated during the Sprint as more is learned. "
    "Developers and the Product Owner collaborate as appropriate. The Sprint "
    "Goal provides the boundary for adaptation."
)


# =============================================================================
# 29. EDGE CASE: PARTIALLY COMPLETED WORK
# =============================================================================

def classify_increment(
    completed: Iterable[ProductBacklogItem],
    definition_checks: Dict[str, bool],
) -> str:
    """
    Demonstrates an important edge case.

    Work that does not meet the Definition of Done is not part of the Increment.
    It can return to the Product Backlog for future consideration or revision.
    """
    completed = list(completed)

    if not completed:
        return "No completed Product Backlog Items."

    done, _ = definition_of_done.evaluate(definition_checks)

    if done:
        return "Completed work qualifies for the Increment."

    return "Work does not meet the Definition of Done and is not part of the Increment."


print("\nPARTIALLY COMPLETED WORK")
print(
    classify_increment(
        [backlog[0]],
        {
            "Code reviewed": True,
            "Automated tests pass": True,
            "Security checks pass": False,
            "Acceptance criteria satisfied": True,
            "Documentation updated": True,
            "Deployable to production": True,
        },
    )
)


# =============================================================================
# 30. TECHNICAL DEBT
# =============================================================================

@dataclass
class TechnicalDebtItem:
    description: str
    risk: int
    cost_to_fix: int

    def urgency_score(self) -> float:
        if self.cost_to_fix <= 0:
            return float("inf")
        return self.risk / self.cost_to_fix


technical_debt = TechnicalDebtItem(
    description="Payment module has duplicated validation logic.",
    risk=8,
    cost_to_fix=3,
)

print("\nTECHNICAL DEBT")
print("Issue:", technical_debt.description)
print("Illustrative urgency:", f"{technical_debt.urgency_score():.2f}")

print(
    "\nTechnical debt is not automatically an excuse for creating separate "
    "technical-only work. Its product impact, risk, cost, and relationship "
    "to the Sprint Goal should be made transparent and considered in "
    "Product Backlog decisions."
)


# =============================================================================
# 31. DEPENDENCIES
# =============================================================================

@dataclass
class Dependency:
    item: str
    depends_on: str

    def description(self) -> str:
        return f"{self.item} depends on {self.depends_on}"


dependencies = [
    Dependency("Saved payment selection", "Payment provider tokenization"),
    Dependency("Checkout analytics", "Event tracking implementation"),
]

print("\nDEPENDENCIES")
for dependency in dependencies:
    print("-", dependency.description())

print(
    "\nDependencies increase uncertainty. A cross-functional Scrum Team "
    "should reduce unnecessary dependencies where possible rather than "
    "using dependencies as a permanent substitute for team capability."
)


# =============================================================================
# 32. IMPEDIMENTS
# =============================================================================

@dataclass
class Impediment:
    description: str
    severity: int
    owner: Optional[str] = None

    def is_critical(self) -> bool:
        return self.severity >= 8


impediment = Impediment(
    description="Production-like payment test environment is unavailable.",
    severity=9,
    owner="Platform Team",
)

print("\nIMPEDIMENT")
print(impediment.description)
print("Severity:", impediment.severity)
print("Critical:", impediment.is_critical())
print("Owner:", impediment.owner)

print(
    "\nA Scrum Master helps the Scrum Team address impediments, but the Scrum "
    "Master is not simply an administrative ticket manager. The goal is to "
    "improve the team's effectiveness and the environment in which it works."
)


# =============================================================================
# 33. SELF-MANAGEMENT VS SELF-ORGANIZATION
# =============================================================================

@dataclass
class SelfManagementExample:
    team_decision: str
    management_instruction: str

    def compare(self) -> None:
        print("Team decision:", self.team_decision)
        print("Contrasting command:", self.management_instruction)


self_management = SelfManagementExample(
    team_decision="Developers decide how to divide technical work to achieve the Sprint Goal.",
    management_instruction="A manager assigns every task to an individual Developer.",
)

print("\nSELF-MANAGEMENT")
self_management.compare()

print(
    "\nSelf-management does not mean absence of accountability. It means the "
    "Scrum Team decides internally who does what, when, and how, while "
    "remaining accountable for creating a valuable, usable Increment."
)


# =============================================================================
# 34. CROSS-FUNCTIONALITY
# =============================================================================

@dataclass
class Skill:
    name: str


@dataclass
class DeveloperProfile:
    name: str
    skills: List[Skill]

    def skill_names(self) -> List[str]:
        return [skill.name for skill in self.skills]


developer_profiles = [
    DeveloperProfile(
        "Maya",
        [Skill("Frontend"), Skill("Accessibility"), Skill("Testing")],
    ),
    DeveloperProfile(
        "Rahul",
        [Skill("Backend"), Skill("Payments"), Skill("Security")],
    ),
    DeveloperProfile(
        "Neha",
        [Skill("Testing"), Skill("Data"), Skill("Observability")],
    ),
]

print("\nCROSS-FUNCTIONALITY")
for developer in developer_profiles:
    print(f"{developer.name}: {', '.join(developer.skill_names())}")

print(
    "\nCross-functional does not mean every Developer must possess every skill. "
    "It means the Scrum Team collectively has the skills needed to create value."
)


# =============================================================================
# 35. STAKEHOLDERS AND THE SPRINT REVIEW
# =============================================================================

@dataclass
class Stakeholder:
    name: str
    interest: str

    def provide_feedback(self, observation: str) -> str:
        return f"{self.name}: {observation}"


stakeholders = [
    Stakeholder("Customer Support", "Payment complaints"),
    Stakeholder("Marketing", "Checkout conversion"),
    Stakeholder("Compliance", "Payment requirements"),
]

print("\nSTAKEHOLDER INPUT")
for stakeholder in stakeholders:
    print(
        stakeholder.provide_feedback(
            f"Interested in {stakeholder.interest.lower()}."
        )
    )


# =============================================================================
# 36. QUALITY AND THE DEFINITION OF DONE
# =============================================================================

def evaluate_quality(
    test_pass_rate: float,
    security_issues: int,
    acceptance_criteria_passed: bool,
) -> bool:
    """
    Example quality gate.

    The exact thresholds are organizational/product decisions. Scrum requires
    a Definition of Done but does not prescribe these particular measurements.
    """
    if not 0 <= test_pass_rate <= 100:
        raise ValueError("test_pass_rate must be between 0 and 100.")

    return (
        test_pass_rate == 100
        and security_issues == 0
        and acceptance_criteria_passed
    )


print("\nQUALITY EVALUATION")
print(
    "Quality acceptable:",
    evaluate_quality(
        test_pass_rate=100,
        security_issues=0,
        acceptance_criteria_passed=True,
    ),
)


# =============================================================================
# 37. SECURITY CONSIDERATIONS IN SCRUM
# =============================================================================

@dataclass
class SecurityRequirement:
    requirement: str
    checked: bool

    def status(self) -> str:
        return "PASS" if self.checked else "FAIL"


security_requirements = [
    SecurityRequirement("Authentication behavior tested", True),
    SecurityRequirement("Authorization rules tested", True),
    SecurityRequirement("Sensitive data handling reviewed", True),
    SecurityRequirement("Dependency vulnerabilities reviewed", False),
]

print("\nSECURITY AND SCRUM")
for requirement in security_requirements:
    print(f"- {requirement.requirement}: {requirement.status()}")

print(
    "\nSecurity should be part of product quality rather than treated as "
    "something that automatically happens after development. If security "
    "requirements are necessary for the Increment to be considered Done, "
    "they belong in the Definition of Done or equivalent quality criteria."
)


# =============================================================================
# 38. SCRUM AND WATERFALL COMPARISON
# =============================================================================

@dataclass
class MethodComparison:
    characteristic: str
    scrum: str
    sequential_project_model: str


comparisons = [
    MethodComparison(
        "Planning",
        "Adaptive and repeated through Sprints",
        "Typically concentrated earlier with sequential phases",
    ),
    MethodComparison(
        "Feedback",
        "Frequent inspection and adaptation",
        "Often concentrated at defined phase boundaries",
    ),
    MethodComparison(
        "Scope",
        "Can adapt while pursuing the Product Goal and Sprint Goal",
        "Often defined more rigidly before execution",
    ),
    MethodComparison(
        "Delivery",
        "Usable Increment each Sprint",
        "Often associated with later-stage integrated delivery",
    ),
]

print("\nSCRUM VS SEQUENTIAL PROJECT MODEL")
for comparison in comparisons:
    print(f"\n{comparison.characteristic}")
    print("  Scrum:", comparison.scrum)
    print("  Sequential model:", comparison.sequential_project_model)

print(
    "\nScrum is not simply 'waterfall with two-week meetings.' Its central "
    "difference is empirical adaptation around usable product increments."
)


# =============================================================================
# 39. SCRUM VS KANBAN
# =============================================================================

kanban_comparison = [
    ("Cadence", "Scrum uses Sprints", "Kanban can use continuous flow"),
    ("Primary control", "Sprint Goal and Sprint Backlog", "Flow and work-in-progress management"),
    ("Events", "Defined Scrum events", "No requirement for Scrum events"),
    ("Roles", "Defined Scrum accountabilities", "No requirement for Scrum accountabilities"),
    ("Metrics", "Velocity may be used, but is optional", "Lead time, cycle time, throughput are common"),
]

print("\nSCRUM VS KANBAN")
for characteristic, scrum_description, kanban_description in kanban_comparison:
    print(f"- {characteristic}:")
    print(f"    Scrum:  {scrum_description}")
    print(f"    Kanban: {kanban_description}")


# =============================================================================
# 40. FLOW METRICS
# =============================================================================

@dataclass
class FlowMetrics:
    cycle_times_days: List[float]
    throughput_per_week: float

    def average_cycle_time(self) -> float:
        if not self.cycle_times_days:
            return 0.0
        return sum(self.cycle_times_days) / len(self.cycle_times_days)


flow_metrics = FlowMetrics(
    cycle_times_days=[2.0, 3.5, 2.5, 4.0, 3.0],
    throughput_per_week=12,
)

print("\nFLOW METRICS")
print(f"Average cycle time: {flow_metrics.average_cycle_time():.2f} days")
print(f"Throughput: {flow_metrics.throughput_per_week} items/week")

print(
    "\nFlow metrics can complement Scrum metrics. They measure characteristics "
    "of work movement and are useful for identifying bottlenecks without "
    "turning a single metric into a target that distorts behavior."
)


# =============================================================================
# 41. CARRYOVER AND SPRINT FORECASTING
# =============================================================================

def forecast_sprints(
    remaining_points: int,
    historical_velocity: Sequence[int],
) -> Tuple[int, int]:
    """
    Returns a conservative and optimistic Sprint-count estimate.

    This is a simple forecasting model, not a Scrum rule.
    """
    valid_velocity = [v for v in historical_velocity if v > 0]

    if remaining_points <= 0:
        return 0, 0

    if not valid_velocity:
        raise ValueError("Historical velocity must contain a positive value.")

    slowest = min(valid_velocity)
    fastest = max(valid_velocity)

    minimum_sprints = (remaining_points + fastest - 1) // fastest
    maximum_sprints = (remaining_points + slowest - 1) // slowest

    return minimum_sprints, maximum_sprints


print("\nFORECASTING")
minimum, maximum = forecast_sprints(
    remaining_points=50,
    historical_velocity=[18, 21, 19, 23, 20],
)
print(f"Illustrative forecast: {minimum} to {maximum} Sprints")


# =============================================================================
# 42. PROBABILISTIC FORECASTING
# =============================================================================

import random


def monte_carlo_forecast(
    remaining_work: int,
    historical_velocity: Sequence[int],
    simulations: int = 10000,
    seed: int = 42,
) -> Dict[int, float]:
    """
    A simple Monte Carlo forecast using historical velocity samples.

    This demonstrates uncertainty instead of pretending that a single
    velocity value is a guaranteed future capacity.
    """
    if remaining_work < 0:
        raise ValueError("remaining_work cannot be negative.")

    if simulations <= 0:
        raise ValueError("simulations must be positive.")

    velocities = [v for v in historical_velocity if v > 0]

    if not velocities:
        raise ValueError("At least one positive historical velocity is required.")

    if remaining_work == 0:
        return {0: 1.0}

    generator = random.Random(seed)
    counts: Dict[int, int] = {}

    for _ in range(simulations):
        completed = 0
        sprints = 0

        while completed < remaining_work:
            completed += generator.choice(velocities)
            sprints += 1

        counts[sprints] = counts.get(sprints, 0) + 1

    return {
        sprint_count: count / simulations
        for sprint_count, count in sorted(counts.items())
    }


forecast_distribution = monte_carlo_forecast(
    remaining_work=50,
    historical_velocity=[18, 21, 19, 23, 20],
)

print("\nMONTE CARLO FORECAST")
for sprint_count, probability in forecast_distribution.items():
    if probability >= 0.01:
        print(f"{sprint_count} Sprints: {probability:.1%}")


# =============================================================================
# 43. CONFIDENCE LEVELS
# =============================================================================

def probability_by_deadline(
    distribution: Dict[int, float],
    sprint_deadline: int,
) -> float:
    if sprint_deadline < 0:
        raise ValueError("sprint_deadline cannot be negative.")

    return sum(
        probability
        for sprint_count, probability in distribution.items()
        if sprint_count <= sprint_deadline
    )


print("\nFORECAST CONFIDENCE")
for deadline in range(1, 6):
    probability = probability_by_deadline(forecast_distribution, deadline)
    print(f"Complete within {deadline} Sprints: {probability:.1%}")

print(
    "\nProbabilistic forecasting communicates uncertainty more honestly than "
    "a single date presented as certainty. Forecasts are based on historical "
    "patterns and assumptions, not guarantees."
)


# =============================================================================
# 44. METRICS THAT CAN BE MISUSED
# =============================================================================

@dataclass
class MetricRisk:
    metric: str
    healthy_use: str
    harmful_target: str


metric_risks = [
    MetricRisk(
        "Velocity",
        "Use historical results as one planning input.",
        "Require every Sprint to increase velocity.",
    ),
    MetricRisk(
        "Story points completed",
        "Inspect delivery patterns.",
        "Use points to rank individuals.",
    ),
    MetricRisk(
        "Defect count",
        "Inspect quality trends.",
        "Reward teams for minimizing reported defects at any cost.",
    ),
    MetricRisk(
        "Utilization",
        "Understand capacity constraints.",
        "Demand 100% utilization, eliminating room for learning and adaptation.",
    ),
]

print("\nMETRIC MISUSE")
for risk in metric_risks:
    print(f"\n{risk.metric}")
    print("  Healthy use:", risk.healthy_use)
    print("  Harmful target:", risk.harmful_target)


# =============================================================================
# 45. ANTI-PATTERNS
# =============================================================================

@dataclass
class AntiPattern:
    name: str
    symptom: str
    consequence: str
    corrective_direction: str


anti_patterns = [
    AntiPattern(
        "Daily Status Meeting",
        "Developers report individually to a manager.",
        "The Daily Scrum becomes a reporting ceremony.",
        "Focus inspection on progress toward the Sprint Goal and adaptation.",
    ),
    AntiPattern(
        "Mini-Waterfalls",
        "Requirements, development, and testing are separated into stages.",
        "Feedback arrives too late.",
        "Create cross-functional slices that can become Done.",
    ),
    AntiPattern(
        "Velocity Competition",
        "Teams are ranked by velocity.",
        "Estimates become inflated or manipulated.",
        "Use velocity only as contextual historical information.",
    ),
    AntiPattern(
        "Proxy Product Owner",
        "A stakeholder makes product decisions while the Product Owner lacks authority.",
        "Accountability becomes unclear.",
        "Ensure Product Owner accountability and effective decision-making.",
    ),
    AntiPattern(
        "Scrum Master as Project Secretary",
        "The Scrum Master spends most time maintaining boards and scheduling.",
        "Systemic impediments remain unresolved.",
        "Focus on coaching, facilitation, Scrum understanding, and effectiveness.",
    ),
    AntiPattern(
        "Done Means Code Complete",
        "Testing and integration happen later.",
        "The Increment may be unusable.",
        "Make quality expectations explicit in the Definition of Done.",
    ),
]

print("\nCOMMON SCRUM ANTI-PATTERNS")
for anti_pattern in anti_patterns:
    print(f"\n{anti_pattern.name}")
    print("  Symptom:", anti_pattern.symptom)
    print("  Consequence:", anti_pattern.consequence)
    print("  Corrective direction:", anti_pattern.corrective_direction)


# =============================================================================
# 46. EDGE CASE: URGENT PRODUCTION ISSUE
# =============================================================================

@dataclass
class UrgentIssueDecision:
    issue: str
    severity: str
    sprint_goal_impact: bool

    def evaluate(self) -> str:
        if self.severity.lower() == "critical":
            return (
                "Inspect the issue immediately. Adapt the Sprint Backlog and "
                "protect the Sprint Goal if possible."
            )

        if self.sprint_goal_impact:
            return (
                "Discuss trade-offs and adapt the Sprint Backlog based on "
                "the impact on the Sprint Goal."
            )

        return "Handle through normal Product Backlog ordering and planning."


urgent_issue = UrgentIssueDecision(
    issue="Critical payment outage",
    severity="critical",
    sprint_goal_impact=True,
)

print("\nURGENT PRODUCTION ISSUE")
print(urgent_issue.evaluate())

print(
    "\nScrum does not provide a universal emergency algorithm. The team "
    "must use transparency, inspection, adaptation, product priorities, "
    "and the Sprint Goal to make an informed decision."
)


# =============================================================================
# 47. EDGE CASE: STAKEHOLDER REQUESTS MID-SPRINT
# =============================================================================

@dataclass
class MidSprintRequest:
    request: str
    aligned_with_goal: bool
    required_for_done: bool

    def handle(self) -> str:
        if self.required_for_done:
            return (
                "Incorporate the necessary work into the Sprint plan while "
                "continuing to pursue the Sprint Goal."
            )

        if self.aligned_with_goal:
            return (
                "Discuss the request with the Product Owner and Developers; "
                "adapt the Sprint Backlog if appropriate."
            )

        return (
            "Consider the request for Product Backlog ordering unless the "
            "Sprint Goal or product circumstances make immediate adaptation necessary."
        )


mid_sprint_request = MidSprintRequest(
    request="Add validation for a newly discovered payment failure.",
    aligned_with_goal=True,
    required_for_done=True,
)

print("\nMID-SPRINT REQUEST")
print(mid_sprint_request.handle())


# =============================================================================
# 48. EDGE CASE: ABSENCE OF PRODUCT OWNER
# =============================================================================

@dataclass
class ProductOwnerAvailability:
    available: bool
    decision_criticality: str

    def evaluate(self) -> str:
        if self.available:
            return "Product decisions can be made through the accountable Product Owner."

        if self.decision_criticality == "high":
            return (
                "The organization has a serious accountability and decision-making "
                "risk; delegation may support execution but does not transfer accountability."
            )

        return "The team may continue within established product boundaries."


owner_availability = ProductOwnerAvailability(
    available=False,
    decision_criticality="high",
)

print("\nPRODUCT OWNER AVAILABILITY")
print(owner_availability.evaluate())


# =============================================================================
# 49. EDGE CASE: MULTIPLE SCRUM TEAMS ON ONE PRODUCT
# =============================================================================

@dataclass
class ProductTeam:
    name: str
    product: str
    product_goal: str

    def shares_goal_with(self, other: "ProductTeam") -> bool:
        return (
            self.product == other.product
            and self.product_goal == other.product_goal
        )


team_a = ProductTeam(
    "Checkout Team",
    "Commerce Platform",
    product_goal.description,
)

team_b = ProductTeam(
    "Payments Team",
    "Commerce Platform",
    product_goal.description,
)

print("\nMULTIPLE TEAMS")
print("Same product:", team_a.product == team_b.product)
print("Same Product Goal:", team_a.shares_goal_with(team_b))

print(
    "\nWhen multiple teams work on one product, coordination, integration, "
    "dependencies, and transparency become important. Scaling frameworks "
    "should not be adopted merely to compensate for poorly designed teams "
    "or organizational dependencies."
)


# =============================================================================
# 50. SCALING CONSIDERATIONS
# =============================================================================

scaling_risks = {
    "Shared dependencies": "Can slow adaptation and increase coordination cost.",
    "Different quality standards": "Can make the product Increment inconsistent.",
    "Separate backlogs for one product": "Can fragment product priorities.",
    "Team-local optimization": "Can conflict with product-level value.",
    "Excessive coordination meetings": "Can consume capacity without improving outcomes.",
}

print("\nSCALING RISKS")
for risk, consequence in scaling_risks.items():
    print(f"- {risk}: {consequence}")


# =============================================================================
# 51. SCRUM MASTER COACHING
# =============================================================================

@dataclass
class CoachingSituation:
    symptom: str
    likely_systemic_issue: str
    coaching_direction: str


coaching_cases = [
    CoachingSituation(
        "Developers wait for a manager to assign tasks.",
        "Low self-management.",
        "Coach the team toward ownership of the Sprint Backlog and Sprint Goal.",
    ),
    CoachingSituation(
        "Stakeholders bypass the Product Owner.",
        "Unclear product decision accountability.",
        "Clarify Product Owner accountability and stakeholder collaboration.",
    ),
    CoachingSituation(
        "Every Sprint finishes with unfinished testing.",
        "Definition of Done does not reflect actual product quality.",
        "Inspect quality expectations and team workflow.",
    ),
]

print("\nSCRUM MASTER COACHING CASES")
for case in coaching_cases:
    print(f"\nSymptom: {case.symptom}")
    print(f"Systemic issue: {case.likely_systemic_issue}")
    print(f"Direction: {case.coaching_direction}")


# =============================================================================
# 52. PRODUCT OWNER DECISION MODEL
# =============================================================================

@dataclass
class ProductDecision:
    option: str
    customer_value: float
    strategic_alignment: float
    risk_reduction: float
    urgency: float
    cost: float

    def score(self) -> float:
        if self.cost <= 0:
            return float("inf")

        weighted_benefit = (
            self.customer_value * 0.4
            + self.strategic_alignment * 0.25
            + self.risk_reduction * 0.2
            + self.urgency * 0.15
        )

        return weighted_benefit / self.cost


decisions = [
    ProductDecision(
        "Reduce payment form fields",
        customer_value=95,
        strategic_alignment=90,
        risk_reduction=50,
        urgency=80,
        cost=5,
    ),
    ProductDecision(
        "Redesign marketing animation",
        customer_value=30,
        strategic_alignment=40,
        risk_reduction=5,
        urgency=20,
        cost=8,
    ),
]

print("\nPRODUCT DECISION MODEL")
for decision in sorted(decisions, key=lambda d: d.score(), reverse=True):
    print(f"{decision.option}: score={decision.score():.2f}")

print(
    "\nProduct decisions should not be delegated to a mechanical scoring "
    "system. A scoring model is useful only when it improves transparent "
    "reasoning about trade-offs."
)


# =============================================================================
# 53. SPRINT HEALTH CHECK
# =============================================================================

@dataclass
class SprintHealth:
    sprint_goal_clarity: int
    product_backlog_transparency: int
    quality: int
    collaboration: int
    stakeholder_feedback: int

    def validate_scores(self) -> None:
        scores = [
            self.sprint_goal_clarity,
            self.product_backlog_transparency,
            self.quality,
            self.collaboration,
            self.stakeholder_feedback,
        ]

        if any(score < 1 or score > 5 for score in scores):
            raise ValueError("Health scores must be between 1 and 5.")

    def average(self) -> float:
        self.validate_scores()
        scores = [
            self.sprint_goal_clarity,
            self.product_backlog_transparency,
            self.quality,
            self.collaboration,
            self.stakeholder_feedback,
        ]
        return sum(scores) / len(scores)


health = SprintHealth(
    sprint_goal_clarity=5,
    product_backlog_transparency=4,
    quality=4,
    collaboration=5,
    stakeholder_feedback=3,
)

print("\nSPRINT HEALTH CHECK")
print(f"Average score: {health.average():.2f}/5")

print(
    "\nA health check is a facilitation technique, not a Scrum artifact. "
    "Teams should avoid turning such assessments into performance rankings."
)


# =============================================================================
# 54. SCRUM MASTER FACILITATION VS CONTROL
# =============================================================================

@dataclass
class FacilitationChoice:
    situation: str
    controlling_behavior: str
    enabling_behavior: str


facilitation_examples = [
    FacilitationChoice(
        "Daily Scrum is unfocused.",
        "Scrum Master tells every Developer exactly what to say.",
        "Scrum Master helps Developers understand the event's purpose and lets them manage the discussion.",
    ),
    FacilitationChoice(
        "Retrospective produces no actions.",
        "Scrum Master assigns improvement tasks.",
        "Scrum Master helps the team identify meaningful experiments and ownership.",
    ),
]

print("\nFACILITATION VS CONTROL")
for example in facilitation_examples:
    print(f"\nSituation: {example.situation}")
    print("Control:", example.controlling_behavior)
    print("Enable:", example.enabling_behavior)


# =============================================================================
# 55. TESTING THE SCRUM MODEL
# =============================================================================

def test_definition_of_done() -> None:
    checks = {criterion: True for criterion in definition_of_done.criteria}
    done, missing = definition_of_done.evaluate(checks)

    assert done is True
    assert missing == []


def test_incomplete_definition_of_done() -> None:
    checks = {criterion: True for criterion in definition_of_done.criteria}
    checks["Security checks pass"] = False

    done, missing = definition_of_done.evaluate(checks)

    assert done is False
    assert "Security checks pass" in missing


def test_invalid_focus_factor() -> None:
    person = DeveloperCapacity("Test", 40)

    try:
        person.usable_capacity(1.5)
    except ValueError:
        return

    raise AssertionError("Invalid focus factor should raise ValueError.")


def test_forecast_zero_work() -> None:
    distribution = monte_carlo_forecast(
        remaining_work=0,
        historical_velocity=[10, 20],
        simulations=100,
    )

    assert distribution == {0: 1.0}


print("\nUNIT TESTS")
test_definition_of_done()
test_incomplete_definition_of_done()
test_invalid_focus_factor()
test_forecast_zero_work()
print("All educational tests passed.")


# =============================================================================
# 56. DEBUGGING SCRUM PROBLEMS
# =============================================================================

@dataclass
class ScrumProblem:
    symptom: str
    inspection_questions: List[str]

    def debug(self) -> None:
        print(f"\nSYMPTOM: {self.symptom}")
        print("Inspect:")
        for question in self.inspection_questions:
            print(f"  ? {question}")


debugging_cases = [
    ScrumProblem(
        "Sprints repeatedly fail to produce usable Increments.",
        [
            "Is the Definition of Done clear?",
            "Is the team cross-functional enough to create the Increment?",
            "Are Product Backlog Items sliced into valuable increments?",
            "Is testing integrated throughout the Sprint?",
        ],
    ),
    ScrumProblem(
        "The Product Backlog is constantly reprioritized by many stakeholders.",
        [
            "Is Product Owner accountability clear?",
            "Are stakeholders collaborating through the Product Owner?",
            "Is the Product Goal understood?",
            "Are product decisions transparent?",
        ],
    ),
]

print("\nDEBUGGING SCRUM")
for case in debugging_cases:
    case.debug()


# =============================================================================
# 57. PRODUCTION CONSIDERATIONS
# =============================================================================

production_considerations = [
    "Definition of Done should reflect production-quality expectations appropriate to the product.",
    "Security, privacy, reliability, accessibility, and observability may be quality requirements.",
    "Deployment should be integrated into the product workflow when appropriate.",
    "Operational feedback can influence Product Backlog ordering.",
    "Incidents can affect Sprint plans and product priorities.",
    "Technical quality should not be deferred indefinitely in pursuit of short-term feature output.",
]

print("\nPRODUCTION CONSIDERATIONS")
for consideration in production_considerations:
    print(f"- {consideration}")


# =============================================================================
# 58. RELEASE VS SPRINT
# =============================================================================

@dataclass
class Release:
    version: str
    increment_versions: List[str]

    def show(self) -> None:
        print(f"Release {self.version}")
        print("Includes increments:", ", ".join(self.increment_versions))


release = Release(
    version="2.0",
    increment_versions=["1.7", "1.8", "1.9", "2.0"],
)

print("\nRELEASE VS SPRINT")
release.show()

print(
    "\nA Sprint and a release are not synonymous. A usable Increment can be "
    "released when appropriate, and release timing is a product decision. "
    "Scrum does not require waiting for a special release event."
)


# =============================================================================
# 59. DEFINITION OF READY: IMPORTANT DISTINCTION
# =============================================================================

@dataclass
class DefinitionOfReadyExample:
    """
    'Definition of Ready' is a commonly used team practice, but it is not
    one of Scrum's required artifacts or commitments.
    """

    conditions: List[str]

    def evaluate(self, item: ProductBacklogItem) -> bool:
        if not item.title.strip():
            return False

        if not item.acceptance_criteria:
            return False

        if item.effort <= 0:
            return False

        return True


definition_of_ready = DefinitionOfReadyExample(
    conditions=[
        "Item has a clear title.",
        "Acceptance criteria are understood.",
        "An estimate exists.",
    ]
)

print("\nDEFINITION OF READY")
print("Conditions:")
for condition in definition_of_ready.conditions:
    print("-", condition)

print(
    "PBI-01 ready:",
    definition_of_ready.evaluate(backlog[0]),
)

print(
    "\nA rigid Definition of Ready can become a gate that blocks useful "
    "conversation. It should not undermine the empirical nature of Scrum."
)


# =============================================================================
# 60. USER STORY ACCEPTANCE CRITERIA
# =============================================================================

@dataclass
class AcceptanceTest:
    criterion: str
    observed: bool

    def passed(self) -> bool:
        return self.observed


acceptance_tests = [
    AcceptanceTest("Payment form accepts valid card details", True),
    AcceptanceTest("Invalid payment details produce clear feedback", True),
    AcceptanceTest("Sensitive payment data is not logged", True),
]

print("\nACCEPTANCE TESTS")
for test in acceptance_tests:
    print(f"- {test.criterion}: {'PASS' if test.passed() else 'FAIL'}")


# =============================================================================
# 61. SPRINT SIMULATION
# =============================================================================

@dataclass
class SprintDay:
    day_number: int
    completed_points: int
    remaining_points: int
    impediments: List[str] = field(default_factory=list)

    def show(self) -> None:
        print(
            f"Day {self.day_number}: "
            f"completed={self.completed_points}, "
            f"remaining={self.remaining_points}"
        )
        if self.impediments:
            print("  Impediments:", "; ".join(self.impediments))


sprint_days = [
    SprintDay(1, 2, 11),
    SprintDay(2, 4, 9),
    SprintDay(3, 5, 8, ["Payment sandbox instability"]),
    SprintDay(4, 7, 6),
    SprintDay(5, 9, 4),
    SprintDay(6, 11, 2),
    SprintDay(7, 13, 0),
]

print("\nSPRINT PROGRESS SIMULATION")
for day in sprint_days:
    day.show()

print(
    "\nThe point of inspection is not to preserve a predetermined plan at all "
    "costs. New information should change the plan when that improves the "
    "chance of achieving the Sprint Goal."
)


# =============================================================================
# 62. BURN-DOWN EXAMPLE
# =============================================================================

def print_burn_down(
    remaining_work: Sequence[int],
) -> None:
    print("\nBURN-DOWN DATA")
    for day, remaining in enumerate(remaining_work, start=1):
        print(f"Day {day:2}: {remaining:3} points remaining")


print_burn_down([13, 11, 9, 8, 6, 4, 2, 0])

print(
    "\nA burn-down chart is a common visualization technique, not a required "
    "Scrum artifact. A flat line is information to inspect, not automatically "
    "evidence that individuals are underperforming."
)


# =============================================================================
# 63. CUMULATIVE FLOW IDEA
# =============================================================================

@dataclass
class WorkState:
    todo: int
    in_progress: int
    done: int

    def total(self) -> int:
        return self.todo + self.in_progress + self.done


work_state = WorkState(todo=8, in_progress=3, done=5)

print("\nWORK STATE")
print("To Do:", work_state.todo)
print("In Progress:", work_state.in_progress)
print("Done:", work_state.done)
print("Total:", work_state.total())


# =============================================================================
# 64. WORK IN PROGRESS
# =============================================================================

def wip_warning(in_progress: int, team_size: int) -> str:
    """
    WIP limits are strongly associated with Kanban and flow practices.
    This function is merely a diagnostic aid for Scrum teams.
    """
    if team_size <= 0:
        raise ValueError("team_size must be positive.")

    if in_progress > team_size * 2:
        return "High WIP: consider finishing existing work before starting more."
    if in_progress > team_size:
        return "Moderate WIP: inspect whether parallel work is creating delays."
    return "WIP level is not obviously excessive."


print("\nWIP DIAGNOSTIC")
print(wip_warning(in_progress=8, team_size=3))


# =============================================================================
# 65. SCRUM DECISION RULES
# =============================================================================

decision_rules = [
    (
        "Sprint Goal is threatened",
        "Inspect the situation and adapt the Sprint Backlog; do not blindly preserve the original task list.",
    ),
    (
        "PBI does not meet Definition of Done",
        "Do not count it as part of the Increment.",
    ),
    (
        "Stakeholder proposes new work",
        "Product Owner considers it in Product Backlog ordering and Sprint context.",
    ),
    (
        "Developers discover new information",
        "Adapt their plan and Sprint Backlog as appropriate.",
    ),
    (
        "Sprint Goal becomes obsolete",
        "The Product Owner may cancel the Sprint.",
    ),
    (
        "Team wants to change task ownership",
        "Developers can self-manage who does what and when.",
    ),
]

print("\nPRACTICAL DECISION RULES")
for situation, response in decision_rules:
    print(f"\nSituation: {situation}")
    print(f"Response:  {response}")


# =============================================================================
# 66. WHAT SCRUM DOES NOT PRESCRIBE
# =============================================================================

not_prescribed = [
    "Specific programming languages",
    "Specific project management software",
    "User stories as the only Product Backlog Item format",
    "Story points",
    "Planning Poker",
    "Burndown charts",
    "Burnup charts",
    "Velocity",
    "Daily three-question format",
    "A mandatory release schedule",
    "A manager assigning tasks to Developers",
    "A specific technical architecture",
]

print("\nPRACTICES NOT REQUIRED BY SCRUM")
for item in not_prescribed:
    print(f"- {item}")

print(
    "\nThe distinction between the Scrum framework and optional practices "
    "prevents teams from confusing local habits with Scrum itself."
)


# =============================================================================
# 67. SCRUM COMPONENT RELATIONSHIPS
# =============================================================================

relationships = [
    "Product Goal -> gives direction to the Product Backlog.",
    "Product Backlog -> provides ordered possibilities for product development.",
    "Sprint Planning -> selects work and creates the Sprint Goal and Sprint Backlog.",
    "Sprint Goal -> gives the Sprint a coherent objective.",
    "Sprint Backlog -> guides Developers during the Sprint.",
    "Daily Scrum -> supports inspection and adaptation of the Sprint plan.",
    "Definition of Done -> establishes the quality boundary for the Increment.",
    "Increment -> provides a usable step toward the Product Goal.",
    "Sprint Review -> adapts the Product Backlog using product and stakeholder learning.",
    "Sprint Retrospective -> adapts how the team works.",
]

print("\nSCRUM SYSTEM RELATIONSHIPS")
for relationship in relationships:
    print("-", relationship)


# =============================================================================
# 68. ADVANCED SCENARIO
# =============================================================================

@dataclass
class AdvancedScenario:
    """
    Integrated example combining product value, risk, quality, Sprint Goal,
    stakeholder feedback, and adaptation.
    """

    product_goal: ProductGoal
    sprint_goal: SprintGoal
    product_backlog: List[ProductBacklogItem]
    quality_requirements: DefinitionOfDone

    def inspect_and_adapt(
        self,
        new_customer_data: str,
        urgent_risk: bool,
    ) -> None:
        print("\nADVANCED SCENARIO INSPECTION")
        print("New customer data:", new_customer_data)
        print("Urgent risk:", urgent_risk)

        if urgent_risk:
            print(
                "Adaptation: elevate risk-reducing work while preserving the "
                "Sprint Goal if possible."
            )
        else:
            print(
                "Adaptation: reorder future Product Backlog Items based on "
                "new evidence."
            )


advanced = AdvancedScenario(
    product_goal=product_goal,
    sprint_goal=sprint_goal,
    product_backlog=ordered_backlog,
    quality_requirements=definition_of_done,
)

advanced.inspect_and_adapt(
    new_customer_data="Mobile customers have a substantially higher payment abandonment rate.",
    urgent_risk=False,
)


# =============================================================================
# 69. COMPLEXITY AND EMPIRICISM
# =============================================================================

@dataclass
class ComplexityIndicator:
    condition: str
    implication: str


complexity_indicators = [
    ComplexityIndicator(
        "Requirements change as users interact with the product.",
        "Short feedback cycles become valuable.",
    ),
    ComplexityIndicator(
        "Technical feasibility is uncertain.",
        "Incremental experimentation can reduce uncertainty.",
    ),
    ComplexityIndicator(
        "Stakeholder priorities compete.",
        "Transparent Product Backlog ordering becomes important.",
    ),
    ComplexityIndicator(
        "Quality failures emerge late.",
        "Frequent integration and a strong Definition of Done become important.",
    ),
]

print("\nCOMPLEXITY INDICATORS")
for indicator in complexity_indicators:
    print(f"- {indicator.condition}")
    print(f"  Implication: {indicator.implication}")


# =============================================================================
# 70. COMMON MISTAKES
# =============================================================================

common_mistakes = [
    (
        "Treating the Product Owner as a requirements secretary",
        "The Product Owner is accountable for product value and Product Backlog management.",
    ),
    (
        "Treating the Scrum Master as a project manager",
        "The Scrum Master is accountable for establishing Scrum and improving effectiveness.",
    ),
    (
        "Treating Developers as individual task executors",
        "Developers self-manage their work toward the Sprint Goal.",
    ),
    (
        "Counting incomplete work as delivered",
        "Only work meeting the Definition of Done belongs to the Increment.",
    ),
    (
        "Changing the Sprint Goal whenever a stakeholder asks",
        "The Sprint Goal provides stability while the Sprint Backlog remains adaptable.",
    ),
    (
        "Using velocity as a productivity score",
        "Velocity is a contextual planning metric, not an individual performance measure.",
    ),
    (
        "Adding meetings to solve every Scrum problem",
        "Many problems require better transparency, team design, accountability, or product decisions.",
    ),
]

print("\nCOMMON MISTAKES")
for mistake, correction in common_mistakes:
    print(f"- Mistake: {mistake}")
    print(f"  Better interpretation: {correction}")


# =============================================================================
# 71. LIMITATIONS AND TRADE-OFFS
# =============================================================================

limitations = [
    (
        "Fixed Sprint cadence",
        "Creates a useful inspection rhythm but may feel restrictive for highly interrupt-driven work.",
    ),
    (
        "Cross-functional team expectation",
        "Can require organizational restructuring and broader skill development.",
    ),
    (
        "Product Owner accountability",
        "Can become difficult when organizations have many conflicting decision makers.",
    ),
    (
        "Empirical adaptation",
        "Requires genuine transparency and stakeholder access; otherwise decisions become speculative.",
    ),
    (
        "Definition of Done",
        "A weak definition creates false confidence about quality; a strong definition can expose organizational constraints.",
    ),
]

print("\nLIMITATIONS AND TRADE-OFFS")
for issue, tradeoff in limitations:
    print(f"- {issue}: {tradeoff}")


# =============================================================================
# 72. MINI SCRUM SIMULATION ENGINE
# =============================================================================

@dataclass
class ScrumSimulation:
    sprint_number: int
    sprint_goal: SprintGoal
    items: List[ProductBacklogItem]
    completed: List[ProductBacklogItem] = field(default_factory=list)
    rejected: List[ProductBacklogItem] = field(default_factory=list)

    def execute_item(
        self,
        item_id: str,
        meets_definition_of_done: bool,
    ) -> None:
        item = next(
            (candidate for candidate in self.items if candidate.id == item_id),
            None,
        )

        if item is None:
            raise KeyError(f"Unknown Product Backlog Item: {item_id}")

        if meets_definition_of_done:
            item.status = "Done"
            self.completed.append(item)
        else:
            item.status = "Not Done"
            self.rejected.append(item)

    def report(self) -> None:
        print(f"\nSprint {self.sprint_number} simulation report")
        print("Goal:", self.sprint_goal.description)

        print("Completed:")
        for item in self.completed:
            print(f"  + {item.id}: {item.title}")

        print("Not Done:")
        for item in self.rejected:
            print(f"  - {item.id}: {item.title}")


simulation = ScrumSimulation(
    sprint_number=2,
    sprint_goal=SprintGoal(
        "Improve payment error recovery without increasing checkout complexity."
    ),
    items=[
        ProductBacklogItem(
            "PBI-07",
            "Retry failed payment safely",
            value=90,
            effort=5,
            priority=Priority.CRITICAL,
            acceptance_criteria=["Retry does not create duplicate charges."],
        ),
        ProductBacklogItem(
            "PBI-08",
            "Improve payment error messages",
            value=75,
            effort=3,
            priority=Priority.HIGH,
            acceptance_criteria=["Messages explain the next useful action."],
        ),
    ],
)

simulation.execute_item("PBI-07", meets_definition_of_done=True)
simulation.execute_item("PBI-08", meets_definition_of_done=False)
simulation.report()


# =============================================================================
# 73. PRACTICAL END-TO-END SCRUM EXAMPLE
# =============================================================================

print("\nEND-TO-END EXAMPLE")
print("-" * 78)

end_to_end_product_goal = ProductGoal(
    "Increase successful mobile checkout completion."
)

end_to_end_backlog = [
    ProductBacklogItem(
        "M-01",
        "Reduce mobile payment fields",
        value=100,
        effort=5,
        priority=Priority.CRITICAL,
        acceptance_criteria=[
            "Only necessary payment information is requested.",
            "The form works on supported mobile screen sizes.",
        ],
    ),
    ProductBacklogItem(
        "M-02",
        "Improve mobile validation messages",
        value=80,
        effort=3,
        priority=Priority.HIGH,
        acceptance_criteria=[
            "Validation identifies the field and corrective action.",
        ],
    ),
    ProductBacklogItem(
        "M-03",
        "Improve mobile order confirmation",
        value=70,
        effort=5,
        priority=Priority.HIGH,
        acceptance_criteria=[
            "Confirmation clearly identifies order status.",
        ],
    ),
]

end_to_end_sprint_goal = SprintGoal(
    "Reduce mobile checkout friction in the payment step."
)

end_to_end_sprint_backlog = SprintBacklog(
    sprint_goal=end_to_end_sprint_goal,
    selected_items=end_to_end_backlog[:2],
    plan={
        "M-01": [
            "Inspect mobile analytics",
            "Implement reduced field set",
            "Test supported devices",
            "Run accessibility checks",
        ],
        "M-02": [
            "Define error messages",
            "Implement validation",
            "Test invalid input paths",
        ],
    },
)

print("Product Goal:")
print(end_to_end_product_goal.description)

print("\nSprint Goal:")
print(end_to_end_sprint_goal.description)

print("\nSprint Backlog:")
end_to_end_sprint_backlog.show()

print("\nIncrement candidate:")
end_to_end_increment = Increment(
    version="mobile-checkout-1",
    features=[
        "Reduced payment fields",
        "Improved validation feedback",
    ],
    meets_definition_of_done=True,
)
print("Usable:", end_to_end_increment.is_usable())

print("\nSprint Review learning:")
print("- Mobile customers complete payment more frequently.")
print("- Some users still abandon when a saved card expires.")

print("\nProduct Backlog adaptation:")
print("- Investigate expired-card recovery.")
print("- Reorder mobile payment recovery based on observed value.")

print("\nRetrospective improvement:")
print("- Bring mobile analytics into refinement earlier.")


# =============================================================================
# 74. SCRUM KNOWLEDGE CHECK
# =============================================================================

@dataclass
class KnowledgeQuestion:
    question: str
    expected_answer: str

    def check(self, answer: str) -> bool:
        normalized = answer.strip().lower()
        return normalized == self.expected_answer.strip().lower()


knowledge_questions = [
    KnowledgeQuestion(
        "Who is accountable for maximizing product value?",
        "Product Owner",
    ),
    KnowledgeQuestion(
        "What commitment belongs to the Sprint Backlog?",
        "Sprint Goal",
    ),
    KnowledgeQuestion(
        "What commitment belongs to the Increment?",
        "Definition of Done",
    ),
    KnowledgeQuestion(
        "Who creates the plan for the Sprint?",
        "Developers",
    ),
    KnowledgeQuestion(
        "What event inspects the Sprint outcome with stakeholders?",
        "Sprint Review",
    ),
    KnowledgeQuestion(
        "What event focuses on improving team effectiveness?",
        "Sprint Retrospective",
    ),
]

print("\nKNOWLEDGE CHECK")
sample_answers = [
    "Product Owner",
    "Sprint Goal",
    "Definition of Done",
    "Developers",
    "Sprint Review",
    "Sprint Retrospective",
]

for question, answer in zip(knowledge_questions, sample_answers):
    print(f"Q: {question.question}")
    print(f"A: {answer}")
    print("Correct:", question.check(answer))


# =============================================================================
# 75. FINAL INTEGRATED SCRUM MODEL
# =============================================================================

@dataclass
class ScrumFramework:
    """
    A compact representation of the central Scrum framework relationships.
    """

    product_goal: ProductGoal
    product_backlog: List[ProductBacklogItem]
    definition_of_done: DefinitionOfDone
    team: ScrumTeam

    def inspect(self) -> None:
        print("\n" + "=" * 78)
        print("INTEGRATED SCRUM MODEL")
        print("=" * 78)

        print("\nProduct Goal:")
        print(self.product_goal.description)

        print("\nProduct Backlog:")
        for position, item in enumerate(self.product_backlog, start=1):
            print(f"{position}. {item.id} - {item.title}")

        print("\nDefinition of Done:")
        for criterion in self.definition_of_done.criteria:
            print(f"- {criterion}")

        print("\nScrum Team:")
        self.team.show()

        print("\nEmpirical loop:")
        print("1. Make work and quality transparent.")
        print("2. Inspect the product, progress, and process.")
        print("3. Adapt the Product Backlog, Sprint Backlog, product, or working methods.")


framework = ScrumFramework(
    product_goal=product_goal,
    product_backlog=ordered_backlog,
    definition_of_done=definition_of_done,
    team=team,
)

framework.inspect()


# =============================================================================
# 76. IMPORTANT TERMINOLOGY REFERENCE
# =============================================================================

terminology = {
    "Scrum": "A lightweight framework for generating value through adaptive solutions for complex problems.",
    "Scrum Team": "One Product Owner, one Scrum Master, and Developers.",
    "Product Owner": "Accountability for maximizing product value and effective Product Backlog management.",
    "Scrum Master": "Accountability for establishing Scrum and improving Scrum Team and organizational effectiveness.",
    "Developers": "Members of the Scrum Team accountable for creating a usable Increment each Sprint.",
    "Product Goal": "The future state of the product that serves as a target for the Scrum Team.",
    "Product Backlog": "An emergent, ordered list of what is needed to improve the product.",
    "Sprint": "A fixed-length event of one month or less during which a usable, valuable Increment is created.",
    "Sprint Goal": "The single objective for the Sprint.",
    "Sprint Backlog": "The Sprint Goal, selected Product Backlog Items, and the actionable plan for delivering the Increment.",
    "Increment": "A concrete stepping stone toward the Product Goal that must be usable and meet the Definition of Done.",
    "Definition of Done": "A formal description of the state of the Increment when it meets required quality measures.",
    "Sprint Planning": "Event that establishes the Sprint Goal, selected work, and plan.",
    "Daily Scrum": "15-minute event for Developers to inspect progress toward the Sprint Goal and adapt the plan.",
    "Sprint Review": "Event for inspecting the Sprint outcome and discussing future adaptations with stakeholders.",
    "Sprint Retrospective": "Event for planning ways to increase quality and effectiveness.",
    "Product Backlog Refinement": "Ongoing activity of adding detail, estimates, and order to Product Backlog Items.",
    "Empiricism": "Decision-making based on transparency, inspection, and adaptation.",
    "Cross-functional": "The team collectively has the skills needed to create value.",
    "Self-management": "The team decides internally who does what, when, and how.",
}

print("\nTERMINOLOGY")
for term, definition in terminology.items():
    print(f"\n{term}")
    print(f"  {definition}")


# =============================================================================
# 77. EXECUTION CHECK
# =============================================================================

def run_execution_check() -> None:
    """
    A final lightweight validation of the educational model.
    """
    assert len(SCRUM_VALUES) == 5
    assert len(SCRUM_EVENTS) == 5
    assert len(ARTIFACT_COMMITMENTS) == 3
    assert framework.team.validate() == []
    assert sprint.validate_duration()
    assert sprint_goal.is_clear()
    assert product_goal.status() == "ACTIVE"

    for item in ordered_backlog:
        assert item.effort > 0
        assert item.value >= 0

    print("\nExecution check: PASSED")


run_execution_check()

print("\n" + "=" * 78)
print("END OF SCRUM STUDY SCRIPT")
print("=" * 78)
print(
    "\nCore mental model: Scrum creates short empirical learning cycles "
    "around a Product Goal, with clear accountabilities, transparent "
    "artifacts, explicit commitments, usable Increments, and repeated "
    "inspection and adaptation."
)
