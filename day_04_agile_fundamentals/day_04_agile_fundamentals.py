"""
AGILE FUNDAMENTALS
Topic Coverage:
- Meaning and purpose of Agile
- Historical background
- Agile Manifesto
- Agile values
- Agile principles
- Adaptability
- Empirical process control
- Iterative and incremental development
- Feedback loops
- Customer collaboration
- Responding to change
- Cross-functional teams
- Self-organizing teams
- Agile planning
- Agile requirements
- Agile delivery
- Agile metrics
- Common Agile frameworks
- Practical scenarios
- Misconceptions and limitations

This script is designed as an executable learning document. It uses
Python concepts, examples, simulations, and structured explanations
to demonstrate Agile Fundamentals from basic to advanced levels.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import statistics


# ============================================================================
# 1. UNDERSTANDING AGILE
# ============================================================================

print("\n" + "=" * 80)
print("AGILE FUNDAMENTALS")
print("=" * 80)

agile_definition = """
Agile is an approach to product and project development based on
iterative delivery, continuous feedback, collaboration, adaptability,
and incremental improvement.

Agile is not a single methodology.

It is a collection of values and principles that guide how teams
approach uncertain, changing, and complex work.

The central idea is that when requirements, technology, customer needs,
or business conditions are likely to change, a team should avoid making
large irreversible commitments too early.

Instead, the team works in smaller cycles, produces usable results,
collects feedback, learns from the outcome, and adapts its future work.
"""

print(agile_definition)


# ============================================================================
# 2. WHY AGILE BECAME IMPORTANT
# ============================================================================

print("\n" + "=" * 80)
print("WHY AGILE EMERGED")
print("=" * 80)

traditional_vs_agile = {
    "Traditional predictive approach": {
        "Planning": "Extensive planning at the beginning",
        "Requirements": "Expected to remain relatively stable",
        "Delivery": "Often concentrated near the end",
        "Feedback": "May arrive late",
        "Change": "Usually controlled through formal processes",
        "Risk": "Problems may remain hidden until later stages"
    },
    "Agile adaptive approach": {
        "Planning": "Planning occurs continuously",
        "Requirements": "Expected to evolve",
        "Delivery": "Incremental and frequent",
        "Feedback": "Collected regularly",
        "Change": "Evaluated and incorporated when valuable",
        "Risk": "Reduced through early validation and delivery"
    }
}

for approach, characteristics in traditional_vs_agile.items():
    print(f"\n{approach}")
    print("-" * len(approach))

    for category, description in characteristics.items():
        print(f"{category}: {description}")


# ============================================================================
# 3. THE AGILE MANIFESTO
# ============================================================================

print("\n" + "=" * 80)
print("THE AGILE MANIFESTO")
print("=" * 80)

"""
The Agile Manifesto was created by a group of software practitioners
who wanted to identify better ways of developing software.

The manifesto contains four fundamental values.

Each value compares two concepts.

The concept on the right is not considered useless. The manifesto states
that the concept on the left is valued more when trade-offs are necessary.
"""

agile_values = [
    {
        "left": "Individuals and interactions",
        "right": "Processes and tools",
        "meaning": (
            "Processes and tools are useful, but successful work depends "
            "heavily on effective communication, collaboration, judgment, "
            "and human interaction."
        )
    },
    {
        "left": "Working software",
        "right": "Comprehensive documentation",
        "meaning": (
            "Documentation has value, but the primary evidence of progress "
            "is a working product that provides real functionality."
        )
    },
    {
        "left": "Customer collaboration",
        "right": "Contract negotiation",
        "meaning": (
            "Contracts define relationships and expectations, but continuous "
            "customer involvement helps ensure that the delivered product "
            "continues to solve relevant problems."
        )
    },
    {
        "left": "Responding to change",
        "right": "Following a plan",
        "meaning": (
            "Planning remains important, but plans should be revised when "
            "new evidence demonstrates that change is necessary."
        )
    }
]

for index, value in enumerate(agile_values, start=1):
    print(f"\nVALUE {index}")
    print(f"{value['left']} over {value['right']}")
    print(f"Explanation: {value['meaning']}")


# ============================================================================
# 4. VALUE 1: INDIVIDUALS AND INTERACTIONS
# ============================================================================

print("\n" + "=" * 80)
print("INDIVIDUALS AND INTERACTIONS")
print("=" * 80)

"""
An Agile team does not assume that a process can replace human judgment.

Complex work often creates situations that cannot be predicted entirely
in advance. Team members need to communicate, discuss trade-offs,
resolve ambiguity, and make decisions.

A highly sophisticated project management tool cannot compensate for:

- Poor communication
- Unclear responsibilities
- Lack of trust
- Knowledge silos
- Slow decision-making
- Poor collaboration

Agile therefore emphasizes direct and effective interaction.
"""


@dataclass
class TeamMember:
    name: str
    skills: List[str]
    availability: int


team = [
    TeamMember("Asha", ["Python", "Backend Development"], 8),
    TeamMember("Rohan", ["UI Development", "User Experience"], 8),
    TeamMember("Meera", ["Testing", "Quality Assurance"], 8),
    TeamMember("Arjun", ["Product Analysis", "Requirements"], 8)
]

print("Example cross-functional team:\n")

for member in team:
    print(
        f"Name: {member.name}\n"
        f"Skills: {', '.join(member.skills)}\n"
        f"Daily Availability: {member.availability} hours\n"
    )

print("""
The team contains different capabilities. Instead of transferring work
through isolated departments with long delays, Agile encourages
collaboration among people who collectively possess the skills needed
to create a usable product increment.
""")


# ============================================================================
# 5. VALUE 2: WORKING PRODUCT OVER EXCESSIVE DOCUMENTATION
# ============================================================================

print("\n" + "=" * 80)
print("WORKING PRODUCT AS EVIDENCE OF PROGRESS")
print("=" * 80)

"""
Documentation can describe an intended system.

A working product demonstrates what the system actually does.

This distinction is important because assumptions can exist in
documentation that are not validated in real use.

For example:

A document may state that users need Feature X.

A prototype may reveal that users rarely use Feature X.

Actual product usage produces evidence that planning documents alone
cannot provide.
"""


@dataclass
class ProductFeature:
    name: str
    planned: bool
    developed: bool
    tested: bool
    accepted: bool

    def is_working(self):
        return (
            self.planned
            and self.developed
            and self.tested
            and self.accepted
        )


features = [
    ProductFeature("User Registration", True, True, True, True),
    ProductFeature("Login", True, True, True, True),
    ProductFeature("Dashboard", True, True, False, False),
    ProductFeature("Analytics", True, False, False, False)
]

print("\nProduct feature status:\n")

for feature in features:
    status = "WORKING" if feature.is_working() else "NOT YET COMPLETE"
    print(f"{feature.name}: {status}")


# ============================================================================
# 6. VALUE 3: CUSTOMER COLLABORATION
# ============================================================================

print("\n" + "=" * 80)
print("CUSTOMER COLLABORATION")
print("=" * 80)

"""
Agile assumes that understanding customer needs is an ongoing activity.

A customer's understanding of a problem may change.

Market conditions may change.

Competitors may introduce alternatives.

Technical possibilities may create new opportunities.

For these reasons, requirements should not always be treated as
permanently fixed after an initial discussion.
"""


class CustomerFeedback:
    def __init__(self, feature, feedback, priority):
        self.feature = feature
        self.feedback = feedback
        self.priority = priority


feedback_items = [
    CustomerFeedback(
        "Dashboard",
        "Users want faster access to important information.",
        "High"
    ),
    CustomerFeedback(
        "Reports",
        "Export functionality would improve usability.",
        "Medium"
    ),
    CustomerFeedback(
        "Profile",
        "Users want additional customization options.",
        "Low"
    )
]

print("\nCustomer feedback:\n")

for item in feedback_items:
    print(f"Feature: {item.feature}")
    print(f"Feedback: {item.feedback}")
    print(f"Priority: {item.priority}")
    print()


# ============================================================================
# 7. VALUE 4: RESPONDING TO CHANGE
# ============================================================================

print("\n" + "=" * 80)
print("RESPONDING TO CHANGE")
print("=" * 80)

"""
Responding to change does not mean changing direction without discipline.

Agile teams evaluate change.

They ask questions such as:

- What new information caused the change?
- What value will the change create?
- What is the opportunity cost?
- What work will be delayed?
- Does the change align with the product objective?
- Is there evidence that the change is necessary?

Adaptability is therefore evidence-based rather than random.
"""


class ChangeRequest:
    def __init__(
        self,
        description,
        expected_value,
        effort,
        urgency
    ):
        self.description = description
        self.expected_value = expected_value
        self.effort = effort
        self.urgency = urgency

    def value_effort_ratio(self):
        if self.effort == 0:
            return float("inf")

        return self.expected_value / self.effort


changes = [
    ChangeRequest(
        "Improve application performance",
        expected_value=90,
        effort=20,
        urgency=10
    ),
    ChangeRequest(
        "Add decorative animation",
        expected_value=20,
        effort=30,
        urgency=2
    ),
    ChangeRequest(
        "Fix payment processing issue",
        expected_value=100,
        effort=10,
        urgency=10
    )
]

print("\nEvaluating change requests:\n")

for change in changes:
    print(f"Change: {change.description}")
    print(f"Expected Value: {change.expected_value}")
    print(f"Effort: {change.effort}")
    print(f"Urgency: {change.urgency}")
    print(
        f"Value/Effort Ratio: "
        f"{change.value_effort_ratio():.2f}"
    )
    print()


# ============================================================================
# 8. THE TWELVE AGILE PRINCIPLES
# ============================================================================

print("\n" + "=" * 80)
print("THE TWELVE AGILE PRINCIPLES")
print("=" * 80)

agile_principles = [
    (
        "Customer Satisfaction",
        "Deliver valuable outcomes early and continuously."
    ),
    (
        "Welcome Change",
        "Accept changing requirements, including late changes when they "
        "provide meaningful value."
    ),
    (
        "Frequent Delivery",
        "Deliver usable increments regularly."
    ),
    (
        "Business and Technical Collaboration",
        "Business stakeholders and technical teams work together closely."
    ),
    (
        "Motivated Individuals",
        "Create an environment where capable people can perform effectively."
    ),
    (
        "Direct Communication",
        "Use efficient communication and interaction."
    ),
    (
        "Working Product",
        "Use functioning product increments as a primary indicator of progress."
    ),
    (
        "Sustainable Pace",
        "Maintain a pace that can be continued over time."
    ),
    (
        "Technical Excellence",
        "Improve technical quality continuously."
    ),
    (
        "Simplicity",
        "Avoid unnecessary work and complexity."
    ),
    (
        "Self-Organizing Teams",
        "Allow capable teams to determine effective ways of completing work."
    ),
    (
        "Continuous Reflection",
        "Regularly examine how the team can improve."
    )
]

for number, (principle, explanation) in enumerate(
    agile_principles,
    start=1
):
    print(f"{number}. {principle}")
    print(f"   {explanation}\n")


# ============================================================================
# 9. ITERATIVE DEVELOPMENT
# ============================================================================

print("\n" + "=" * 80)
print("ITERATIVE DEVELOPMENT")
print("=" * 80)

"""
Iteration means repeating a process with the purpose of improving the
result using knowledge gained from previous attempts.

Example:

Version 1:
Basic implementation

Feedback:
Users find navigation confusing.

Version 2:
Navigation structure is improved.

Feedback:
Users want faster access to frequently used features.

Version 3:
Quick access functionality is introduced.

Each iteration incorporates learning from the previous state.
"""


class ProductIteration:
    def __init__(self, iteration_number, improvement):
        self.iteration_number = iteration_number
        self.improvement = improvement


iterations = [
    ProductIteration(1, "Basic product workflow implemented"),
    ProductIteration(2, "Navigation improved using user feedback"),
    ProductIteration(3, "Performance optimized"),
    ProductIteration(4, "Frequently used actions simplified")
]

for iteration in iterations:
    print(
        f"Iteration {iteration.iteration_number}: "
        f"{iteration.improvement}"
    )


# ============================================================================
# 10. INCREMENTAL DEVELOPMENT
# ============================================================================

print("\n" + "=" * 80)
print("INCREMENTAL DEVELOPMENT")
print("=" * 80)

"""
Incremental development means delivering the product in usable parts.

Consider an e-commerce platform.

Instead of waiting until every feature is complete, the product may be
developed incrementally:

Increment 1:
User registration

Increment 2:
Product catalog

Increment 3:
Shopping cart

Increment 4:
Payment processing

Increment 5:
Order tracking

Each increment expands the available product capability.
"""

product_increment = [
    "User Registration",
    "Product Catalog",
    "Shopping Cart",
    "Payment Processing",
    "Order Tracking"
]

for number, increment in enumerate(product_increment, start=1):
    print(f"Increment {number}: {increment}")


# ============================================================================
# 11. ITERATION AND INCREMENT ARE NOT THE SAME
# ============================================================================

print("\n" + "=" * 80)
print("ITERATION VS INCREMENT")
print("=" * 80)

comparison = {
    "Iteration": (
        "Repeating work to improve understanding, design, quality, "
        "or implementation."
    ),
    "Increment": (
        "Adding new usable functionality to the existing product."
    )
}

for concept, meaning in comparison.items():
    print(f"{concept}: {meaning}\n")

print("""
A product team may iterate on an existing feature and simultaneously
create a new increment.

For example:

Iteration:
Improving search relevance.

Increment:
Adding a saved search feature.
""")


# ============================================================================
# 12. EMPIRICAL PROCESS CONTROL
# ============================================================================

print("\n" + "=" * 80)
print("EMPIRICISM IN AGILE")
print("=" * 80)

"""
Agile relies heavily on empiricism.

Empiricism means making decisions based on observation and evidence.

Instead of assuming that a plan will remain correct indefinitely,
the team observes actual results and adapts.

Empirical process control has three important elements:

1. Transparency
2. Inspection
3. Adaptation
"""


empirical_process = {
    "Transparency": (
        "Important aspects of work must be visible and understandable."
    ),
    "Inspection": (
        "The team regularly examines product and process outcomes."
    ),
    "Adaptation": (
        "The team adjusts when inspection reveals significant deviation "
        "or improvement opportunities."
    )
}

for element, explanation in empirical_process.items():
    print(f"\n{element}")
    print(explanation)


# ============================================================================
# 13. TRANSPARENCY
# ============================================================================

print("\n" + "=" * 80)
print("TRANSPARENCY")
print("=" * 80)

"""
Transparency means that relevant information is visible.

Examples include:

- Current work
- Product priorities
- Known risks
- Quality status
- Dependencies
- Progress toward objectives

Without transparency, decisions may be based on assumptions rather than
the actual state of work.
"""


work_items = {
    "Completed": [
        "User authentication",
        "Database configuration"
    ],
    "In Progress": [
        "Payment integration"
    ],
    "Not Started": [
        "Order tracking"
    ],
    "Blocked": [
        "External payment provider dependency"
    ]
}

for status, tasks in work_items.items():
    print(f"\n{status}:")
    for task in tasks:
        print(f"  - {task}")


# ============================================================================
# 14. INSPECTION
# ============================================================================

print("\n" + "=" * 80)
print("INSPECTION")
print("=" * 80)

"""
Inspection means regularly evaluating actual outcomes.

Examples:

- Reviewing completed product functionality
- Checking product quality
- Examining customer feedback
- Reviewing delivery performance
- Identifying bottlenecks
- Examining risks

Inspection without adaptation produces little value.

The purpose of inspection is to generate information that can influence
future decisions.
"""


# ============================================================================
# 15. ADAPTATION
# ============================================================================

print("\n" + "=" * 80)
print("ADAPTATION")
print("=" * 80)

"""
Adaptation occurs when evidence leads to a meaningful adjustment.

Example:

Observation:
Users abandon the registration process.

Inspection:
Data shows that most users leave when asked for unnecessary information.

Adaptation:
The registration process is simplified.

Agility exists not merely because feedback is collected, but because
feedback can influence future action.
"""


def adapt_product(user_abandonment_rate):
    if user_abandonment_rate > 50:
        return "Simplify the registration process."

    if user_abandonment_rate > 25:
        return "Investigate the user experience."

    return "Continue monitoring performance."


abandonment_rates = [15, 32, 65]

for rate in abandonment_rates:
    decision = adapt_product(rate)
    print(f"Abandonment Rate: {rate}%")
    print(f"Decision: {decision}\n")


# ============================================================================
# 16. ADAPTABILITY
# ============================================================================

print("\n" + "=" * 80)
print("ADAPTABILITY AS A CORE AGILE CAPABILITY")
print("=" * 80)

"""
Adaptability is the ability to modify plans, priorities, processes,
or product decisions when new information becomes available.

Adaptability does not mean:

- No planning
- No discipline
- Constant uncontrolled change
- Ignoring commitments
- Changing direction every day

Effective adaptability requires:

1. Awareness of change
2. Understanding the impact
3. Evaluating alternatives
4. Making a decision
5. Implementing the adjustment
6. Observing the result
"""


@dataclass
class AdaptationDecision:
    new_information: str
    impact: str
    action: str


adaptation_example = AdaptationDecision(
    new_information="Customers primarily use mobile devices.",
    impact="Desktop-first design creates unnecessary friction.",
    action="Prioritize mobile user experience improvements."
)

print(f"New Information: {adaptation_example.new_information}")
print(f"Impact: {adaptation_example.impact}")
print(f"Action: {adaptation_example.action}")


# ============================================================================
# 17. THE AGILE FEEDBACK LOOP
# ============================================================================

print("\n" + "=" * 80)
print("THE AGILE FEEDBACK LOOP")
print("=" * 80)

feedback_loop = [
    "Plan",
    "Build",
    "Deliver",
    "Observe",
    "Collect Feedback",
    "Inspect",
    "Adapt"
]

for step_number, step in enumerate(feedback_loop, start=1):
    print(f"{step_number}. {step}")

print("""
The important characteristic is that learning influences subsequent work.

A team that repeats the same process despite receiving useful evidence
is not effectively using the feedback loop.
""")


# ============================================================================
# 18. AGILE PLANNING
# ============================================================================

print("\n" + "=" * 80)
print("AGILE PLANNING")
print("=" * 80)

"""
Agile planning is continuous.

Planning may exist at different horizons.

A team may have:

Strategic direction:
Longer-term purpose and objectives.

Product direction:
Major outcomes and capabilities.

Near-term planning:
Work expected in upcoming periods.

Immediate planning:
Detailed decisions about the next iteration or delivery cycle.

Planning becomes more detailed when uncertainty decreases.
"""


planning_horizons = {
    "Long-term": "Strategic goals and product direction",
    "Medium-term": "Major capabilities and expected outcomes",
    "Short-term": "Prioritized work",
    "Immediate": "Detailed execution tasks"
}

for horizon, purpose in planning_horizons.items():
    print(f"{horizon}: {purpose}")


# ============================================================================
# 19. PROGRESSIVE ELABORATION
# ============================================================================

print("\n" + "=" * 80)
print("PROGRESSIVE ELABORATION")
print("=" * 80)

"""
Progressive elaboration means that understanding develops over time.

At the beginning of a complex initiative, a team may know:

- The problem
- The target users
- The desired outcome

The team may not know:

- The exact technical architecture
- The final user interface
- Every requirement
- Every risk

Instead of pretending that uncertainty does not exist, Agile allows
details to become clearer through learning.
"""


uncertainty_levels = {
    "Initial concept": 90,
    "Prototype": 60,
    "Early user testing": 40,
    "Validated solution": 20
}

for stage, uncertainty in uncertainty_levels.items():
    print(f"{stage}: Approximate uncertainty = {uncertainty}%")


# ============================================================================
# 20. AGILE REQUIREMENTS
# ============================================================================

print("\n" + "=" * 80)
print("AGILE REQUIREMENTS")
print("=" * 80)

"""
Agile requirements are often expressed in smaller units.

A common example is a user story.

A typical structure is:

As a [type of user],
I want [capability],
so that [benefit].

The structure encourages teams to connect functionality with user value.
"""


@dataclass
class UserStory:
    user_type: str
    capability: str
    benefit: str

    def display(self):
        return (
            f"As a {self.user_type}, "
            f"I want {self.capability}, "
            f"so that {self.benefit}."
        )


story = UserStory(
    user_type="customer",
    capability="view previous orders",
    benefit="I can track my purchase history"
)

print(story.display())


# ============================================================================
# 21. ACCEPTANCE CRITERIA
# ============================================================================

print("\n" + "=" * 80)
print("ACCEPTANCE CRITERIA")
print("=" * 80)

"""
Acceptance criteria define conditions that help determine whether a
requirement has been satisfactorily implemented.

Example:

User Story:
As a customer, I want to reset my password.

Acceptance Criteria:

- The user can request a password reset.
- A secure reset mechanism is used.
- The reset link expires after a defined period.
- The user receives confirmation.
- The user can log in using the new password.
"""


acceptance_criteria = [
    "User can request password reset",
    "Secure verification is performed",
    "Reset link has an expiry period",
    "Confirmation is provided",
    "New password can be used for login"
]

for criterion in acceptance_criteria:
    print(f"- {criterion}")


# ============================================================================
# 22. PRIORITIZATION
# ============================================================================

print("\n" + "=" * 80)
print("PRIORITIZATION IN AGILE")
print("=" * 80)

"""
Agile does not mean completing every requested feature.

Prioritization is necessary because:

- Resources are limited.
- Time is limited.
- Opportunities compete.
- Customer needs differ.
- Some work creates more value than other work.

A useful decision considers value, effort, urgency, risk, and strategic
importance.
"""


@dataclass
class BacklogItem:
    name: str
    value: int
    effort: int
    risk_reduction: int

    def priority_score(self):
        return (
            self.value +
            self.risk_reduction -
            self.effort
        )


backlog = [
    BacklogItem("Fix payment failure", 100, 15, 50),
    BacklogItem("Improve search", 70, 25, 20),
    BacklogItem("Add profile theme", 25, 20, 5),
    BacklogItem("Improve security", 90, 30, 60)
]

ranked_backlog = sorted(
    backlog,
    key=lambda item: item.priority_score(),
    reverse=True
)

print("\nPrioritized backlog:\n")

for item in ranked_backlog:
    print(
        f"{item.name} | "
        f"Priority Score: {item.priority_score()}"
    )


# ============================================================================
# 23. CUSTOMER VALUE
# ============================================================================

print("\n" + "=" * 80)
print("CUSTOMER VALUE")
print("=" * 80)

"""
Agile work is commonly evaluated in terms of value.

Value may include:

- Revenue generation
- Cost reduction
- Improved customer satisfaction
- Risk reduction
- Regulatory compliance
- Improved efficiency
- Better user experience
- Strategic positioning

Value is context-dependent.

A feature that appears technically impressive may have limited business
value. A small improvement may produce significant value if it removes
an important customer problem.
"""


value_types = [
    "Economic value",
    "Customer value",
    "Strategic value",
    "Risk reduction value",
    "Operational value",
    "Learning value"
]

for value_type in value_types:
    print(f"- {value_type}")


# ============================================================================
# 24. SELF-ORGANIZING AND SELF-MANAGING TEAMS
# ============================================================================

print("\n" + "=" * 80)
print("SELF-ORGANIZING TEAMS")
print("=" * 80)

"""
Agile teams are generally expected to have significant autonomy in
determining how work is completed.

Leadership may establish:

- Objectives
- Constraints
- Strategic direction
- Expected outcomes

The team can then determine:

- Technical approach
- Task allocation
- Collaboration methods
- Implementation details

Self-organization does not mean absence of accountability.

Autonomy and accountability operate together.
"""


class AgileTeam:
    def __init__(self, members):
        self.members = members
        self.tasks = {}

    def assign_task(self, task, member):
        self.tasks[task] = member

    def show_assignments(self):
        for task, member in self.tasks.items():
            print(f"{task} -> {member}")


agile_team = AgileTeam(
    ["Asha", "Rohan", "Meera", "Arjun"]
)

agile_team.assign_task(
    "Design API",
    "Asha"
)

agile_team.assign_task(
    "Create Interface",
    "Rohan"
)

agile_team.assign_task(
    "Validate Quality",
    "Meera"
)

agile_team.assign_task(
    "Clarify Requirements",
    "Arjun"
)

agile_team.show_assignments()


# ============================================================================
# 25. CROSS-FUNCTIONALITY
# ============================================================================

print("\n" + "=" * 80)
print("CROSS-FUNCTIONAL TEAMS")
print("=" * 80)

"""
A cross-functional team collectively contains the capabilities needed
to create meaningful outcomes.

The objective is to reduce unnecessary dependency chains.

Example:

A product feature may require:

- Product understanding
- Design
- Development
- Testing
- Deployment
- User feedback analysis

When these capabilities collaborate closely, feedback and decision
cycles can become faster.
"""


cross_functional_capabilities = {
    "Product": "Understands customer and business needs",
    "Design": "Creates usable interactions",
    "Development": "Builds functionality",
    "Quality": "Validates expected behavior",
    "Operations": "Supports deployment and reliability"
}

for capability, responsibility in cross_functional_capabilities.items():
    print(f"{capability}: {responsibility}")


# ============================================================================
# 26. SUSTAINABLE PACE
# ============================================================================

print("\n" + "=" * 80)
print("SUSTAINABLE PACE")
print("=" * 80)

"""
Agile emphasizes a pace that can be maintained.

Continuous overwork may temporarily increase output but can create:

- Burnout
- Increased defects
- Poor decision-making
- Employee turnover
- Reduced creativity
- Long-term productivity decline

Sustainable pace recognizes that consistent performance is more useful
than repeated cycles of excessive effort followed by exhaustion.
"""


weekly_hours = [42, 43, 41, 44, 42]

average_hours = statistics.mean(weekly_hours)

print(f"Average weekly working hours: {average_hours}")

if average_hours <= 45:
    print("The workload appears relatively sustainable.")
else:
    print("The workload may require examination.")


# ============================================================================
# 27. TECHNICAL EXCELLENCE
# ============================================================================

print("\n" + "=" * 80)
print("TECHNICAL EXCELLENCE")
print("=" * 80)

"""
Agility depends on the ability to change.

Poor technical quality can make change increasingly expensive.

Technical excellence may involve:

- Automated testing
- Refactoring
- Clean architecture
- Code reviews
- Continuous integration
- Security practices
- Performance monitoring
- Maintainable design

Technical quality is therefore connected directly to adaptability.

A system that is difficult to modify reduces the organization's ability
to respond to changing requirements.
"""


technical_practices = [
    "Automated testing",
    "Code review",
    "Continuous integration",
    "Refactoring",
    "Modular architecture",
    "Performance monitoring"
]

for practice in technical_practices:
    print(f"- {practice}")


# ============================================================================
# 28. SIMPLICITY
# ============================================================================

print("\n" + "=" * 80)
print("SIMPLICITY")
print("=" * 80)

"""
Simplicity means maximizing the amount of work not done.

This does not mean avoiding important work.

It means questioning unnecessary work.

Examples:

Instead of:

Building ten features that might be useful.

An Agile approach may prefer:

Building the most valuable feature, validating its usefulness, and then
deciding what should happen next.
"""


features_requested = 10
features_validated_as_valuable = 4

print(f"Features Requested: {features_requested}")
print(
    f"Features Demonstrated as Valuable: "
    f"{features_validated_as_valuable}"
)
print(
    f"Potential unnecessary work avoided: "
    f"{features_requested - features_validated_as_valuable}"
)


# ============================================================================
# 29. AGILE DELIVERY
# ============================================================================

print("\n" + "=" * 80)
print("AGILE DELIVERY")
print("=" * 80)

"""
Agile delivery focuses on producing usable outcomes in smaller intervals.

A simplified delivery flow may be:

1. Identify valuable work
2. Prioritize
3. Plan near-term execution
4. Develop
5. Test
6. Integrate
7. Review
8. Collect feedback
9. Adapt priorities
"""


delivery_flow = [
    "Identify Value",
    "Prioritize",
    "Plan",
    "Develop",
    "Test",
    "Integrate",
    "Review",
    "Collect Feedback",
    "Adapt"
]

for index, stage in enumerate(delivery_flow, start=1):
    print(f"{index}. {stage}")


# ============================================================================
# 30. AGILE AND UNCERTAINTY
# ============================================================================

print("\n" + "=" * 80)
print("AGILE AND UNCERTAINTY")
print("=" * 80)

"""
Agile is particularly useful when work contains uncertainty.

Uncertainty may exist in:

- Customer preferences
- Technology
- Market conditions
- Requirements
- Implementation methods

When uncertainty is high, detailed long-term predictions become less
reliable.

Shorter feedback cycles reduce the period between assumption and
validation.
"""


class Assumption:
    def __init__(self, statement, validated=False):
        self.statement = statement
        self.validated = validated


assumptions = [
    Assumption(
        "Customers prefer a mobile application."
    ),
    Assumption(
        "Users need real-time notifications."
    ),
    Assumption(
        "Users will pay for premium analytics."
    )
]

for assumption in assumptions:
    status = (
        "VALIDATED"
        if assumption.validated
        else "NOT VALIDATED"
    )

    print(
        f"{assumption.statement} -> {status}"
    )


# ============================================================================
# 31. AGILE METRICS
# ============================================================================

print("\n" + "=" * 80)
print("AGILE METRICS")
print("=" * 80)

"""
Metrics should support learning rather than encourage unhealthy behavior.

Useful metrics may include:

- Lead time
- Cycle time
- Delivery frequency
- Defect rate
- Customer satisfaction
- Product usage
- Escaped defects

A metric should not automatically become a performance target.

For example:

If developers are rewarded only for the number of features completed,
they may prioritize quantity over quality and value.
"""


delivery_days = [4, 5, 3, 6, 4, 5]

average_cycle_time = statistics.mean(delivery_days)

print(
    f"Average Cycle Time: "
    f"{average_cycle_time:.2f} days"
)


# ============================================================================
# 32. VELOCITY AND ITS LIMITATIONS
# ============================================================================

print("\n" + "=" * 80)
print("VELOCITY")
print("=" * 80)

"""
Velocity generally represents the amount of estimated work completed by
a team during a time period.

It can help with internal forecasting.

Velocity should not automatically be used to compare teams.

Different teams may:

- Estimate differently
- Work on different types of problems
- Have different definitions of complexity

Therefore, velocity is primarily useful within its own context.
"""


team_velocity = [30, 34, 32, 36, 33]

print(f"Historical velocity: {team_velocity}")
print(
    f"Average velocity: "
    f"{statistics.mean(team_velocity):.2f}"
)


# ============================================================================
# 33. AGILE FRAMEWORKS
# ============================================================================

print("\n" + "=" * 80)
print("COMMON AGILE FRAMEWORKS")
print("=" * 80)

frameworks = {
    "Scrum": (
        "A framework using defined roles, events, and artifacts to "
        "support empirical product development."
    ),
    "Kanban": (
        "A method focused on visualizing work, managing flow, and "
        "improving delivery systems."
    ),
    "Extreme Programming": (
        "An approach emphasizing technical practices and engineering "
        "quality."
    ),
    "Lean": (
        "An approach emphasizing value, waste reduction, learning, "
        "and continuous improvement."
    )
}

for framework, description in frameworks.items():
    print(f"\n{framework}")
    print(description)


# ============================================================================
# 34. SCRUM AND AGILE
# ============================================================================

print("\n" + "=" * 80)
print("SCRUM IS NOT SYNONYMOUS WITH AGILE")
print("=" * 80)

"""
Agile is a broad philosophy represented through values and principles.

Scrum is a specific framework.

Therefore:

Agile ≠ Scrum

A team can use Agile principles without using Scrum.

Scrum is one structured approach for applying empirical and Agile
thinking to complex work.
"""


# ============================================================================
# 35. KANBAN AND FLOW
# ============================================================================

print("\n" + "=" * 80)
print("KANBAN AND FLOW")
print("=" * 80)

"""
Kanban focuses strongly on the flow of work.

A simple workflow may include:

To Do -> In Progress -> Testing -> Done

One important idea is limiting work in progress.

Too much simultaneous work can create:

- Context switching
- Delays
- Bottlenecks
- Reduced focus
"""


class KanbanBoard:
    def __init__(self):
        self.columns = {
            "To Do": [],
            "In Progress": [],
            "Testing": [],
            "Done": []
        }

    def add_task(self, column, task):
        self.columns[column].append(task)

    def display(self):
        for column, tasks in self.columns.items():
            print(f"\n{column}")
            print("-" * len(column))

            for task in tasks:
                print(f"- {task}")


board = KanbanBoard()

board.add_task("To Do", "Implement notifications")
board.add_task("In Progress", "Develop payment API")
board.add_task("Testing", "Test user login")
board.add_task("Done", "Create registration page")

board.display()


# ============================================================================
# 36. WORK IN PROGRESS
# ============================================================================

print("\n" + "=" * 80)
print("WORK IN PROGRESS")
print("=" * 80)

"""
Starting more work does not necessarily mean completing more work.

Consider two situations.

Situation A:

10 tasks are started.
Only 2 are completed.

Situation B:

5 tasks are started.
4 are completed.

The second system may demonstrate better flow.

Agile systems often emphasize finishing valuable work rather than
maximizing the amount of work started.
"""


started_tasks = 10
completed_tasks = 2

completion_ratio = completed_tasks / started_tasks

print(
    f"Completion ratio: "
    f"{completion_ratio:.2%}"
)


# ============================================================================
# 37. CONTINUOUS IMPROVEMENT
# ============================================================================

print("\n" + "=" * 80)
print("CONTINUOUS IMPROVEMENT")
print("=" * 80)

"""
Agility applies to both products and processes.

Teams should periodically examine questions such as:

- What worked effectively?
- What created delays?
- What created quality problems?
- What should be changed?
- What should continue?

Improvement becomes meaningful when observations result in specific
changes.
"""


retrospective = {
    "What Worked": [
        "Earlier collaboration with users",
        "Automated testing"
    ],
    "Problems": [
        "Delayed dependency communication",
        "Unclear acceptance criteria"
    ],
    "Actions": [
        "Discuss dependencies earlier",
        "Define acceptance criteria before development"
    ]
}

for category, items in retrospective.items():
    print(f"\n{category}:")
    for item in items:
        print(f"- {item}")


# ============================================================================
# 38. ADAPTABILITY AND ORGANIZATIONAL CULTURE
# ============================================================================

print("\n" + "=" * 80)
print("ADAPTABILITY AND ORGANIZATIONAL CULTURE")
print("=" * 80)

"""
A team cannot become truly adaptive if the organization punishes every
unexpected result.

Adaptability requires an environment where people can:

- Raise risks
- Report problems
- Challenge assumptions
- Discuss mistakes
- Propose improvements

Psychological safety can therefore influence Agile effectiveness.

A team that hides problems cannot inspect reality accurately.

Without accurate inspection, meaningful adaptation becomes difficult.
"""


# ============================================================================
# 39. COMMON AGILE MISCONCEPTIONS
# ============================================================================

print("\n" + "=" * 80)
print("COMMON AGILE MISCONCEPTIONS")
print("=" * 80)

misconceptions = {
    "Agile means no planning": (
        "Incorrect. Agile uses continuous and adaptive planning."
    ),
    "Agile means no documentation": (
        "Incorrect. Documentation is created when it provides sufficient value."
    ),
    "Agile means requirements constantly change": (
        "Incorrect. Changes are evaluated rather than accepted automatically."
    ),
    "Agile means working without management": (
        "Incorrect. Agile requires coordination, leadership, accountability, "
        "and decision-making."
    ),
    "Agile guarantees faster delivery": (
        "Incorrect. Agile improves learning and adaptability but does not "
        "eliminate complexity."
    ),
    "Scrum and Agile are identical": (
        "Incorrect. Scrum is one framework that can support Agile principles."
    )
}

for misconception, correction in misconceptions.items():
    print(f"\nMisconception: {misconception}")
    print(f"Reality: {correction}")


# ============================================================================
# 40. WHEN AGILE IS CHALLENGING
# ============================================================================

print("\n" + "=" * 80)
print("CHALLENGES IN APPLYING AGILE")
print("=" * 80)

"""
Agile adoption can be difficult when:

- Teams lack authority to make decisions.
- Feedback is unavailable.
- Priorities change without discipline.
- Work is highly fragmented across departments.
- Technical quality is poor.
- Leadership expects predictability without accepting uncertainty.
- Teams focus on ceremonies instead of outcomes.

Agile practices cannot automatically solve organizational problems.

A team may conduct Agile meetings while still operating with:

- Slow decision-making
- Hidden information
- Excessive approval layers
- Rigid communication structures

In such situations, the organization may be performing Agile activities
without developing genuine agility.
"""


# ============================================================================
# 41. AGILITY VERSUS AGILE CEREMONIES
# ============================================================================

print("\n" + "=" * 80)
print("AGILITY VERSUS CEREMONIES")
print("=" * 80)

"""
Agility is a capability.

A ceremony is an activity.

For example:

Holding a daily meeting does not automatically create agility.

Using a task board does not automatically create agility.

Working in fixed iterations does not automatically create agility.

The critical question is whether the system can:

- Learn
- Detect problems
- Deliver value
- Respond to evidence
- Improve continuously

Tools and ceremonies should support these capabilities.
"""


# ============================================================================
# 42. A COMPLETE AGILE SCENARIO
# ============================================================================

print("\n" + "=" * 80)
print("COMPLETE AGILE SCENARIO")
print("=" * 80)

"""
Scenario:

A company wants to create an online learning platform.

Initial assumption:

Students need a large catalog of courses.

The team creates an initial product increment containing:

- Registration
- Course browsing
- Course enrollment

Users provide feedback.

Observation:

Students are more concerned about course completion than course discovery.

Inspection:

Usage data shows that students frequently abandon courses.

Adaptation:

The team prioritizes:

- Progress tracking
- Reminders
- Smaller learning modules
- Improved course navigation

This demonstrates an Agile sequence:

Assumption
    ↓
Increment
    ↓
User Interaction
    ↓
Feedback
    ↓
Inspection
    ↓
Adaptation
"""


class AgileScenario:
    def __init__(self):
        self.history = []

    def add_event(self, event):
        self.history.append(event)

    def show_history(self):
        for number, event in enumerate(
            self.history,
            start=1
        ):
            print(f"{number}. {event}")


scenario = AgileScenario()

scenario.add_event(
    "Initial assumption: large course catalog is the main customer need"
)

scenario.add_event(
    "Initial increment: registration, browsing, enrollment"
)

scenario.add_event(
    "Observation: users abandon courses frequently"
)

scenario.add_event(
    "Inspection: course completion is a greater problem"
)

scenario.add_event(
    "Adaptation: prioritize progress tracking and learning support"
)

scenario.show_history()


# ============================================================================
# 43. AGILE MATURITY
# ============================================================================

print("\n" + "=" * 80)
print("AGILE MATURITY")
print("=" * 80)

"""
An organization can adopt Agile practices at different levels of maturity.

Early stage:

Teams use Agile terminology and basic practices.

Intermediate stage:

Teams consistently deliver in smaller increments and collect feedback.

Advanced stage:

The organization makes decisions using evidence and adapts priorities.

High maturity:

Agility becomes embedded in product strategy, organizational culture,
leadership behavior, technical systems, and customer relationships.

The objective is not to perform the maximum number of Agile practices.

The objective is to develop the capability to respond intelligently to
complexity and change.
"""


agile_maturity = {
    1: "Practices are introduced",
    2: "Teams establish iterative delivery",
    3: "Feedback influences product decisions",
    4: "Adaptation becomes systematic",
    5: "Organizational agility becomes embedded"
}

for level, description in agile_maturity.items():
    print(f"Level {level}: {description}")


# ============================================================================
# 44. FINAL APPLICATION OF AGILE FUNDAMENTALS
# ============================================================================

print("\n" + "=" * 80)
print("APPLYING AGILE FUNDAMENTALS")
print("=" * 80)

"""
Agile can be understood as a system for managing uncertainty through
shorter learning cycles.

The practical sequence is:

1. Establish a meaningful objective.
2. Identify the most valuable available work.
3. Make assumptions visible.
4. Deliver a usable result.
5. Observe actual outcomes.
6. Collect relevant feedback.
7. Inspect evidence.
8. Adapt decisions.
9. Improve the process.
10. Repeat while maintaining focus on value.

The effectiveness of Agile depends on the quality of learning.

Rapid delivery without learning can produce rapid waste.

Frequent meetings without transparency can produce unnecessary activity.

Constant change without evidence can produce instability.

The defining capability is disciplined adaptability.
"""

print("""
Agile Fundamentals can therefore be viewed as the combination of:

VALUES
+
PRINCIPLES
+
ITERATIVE DELIVERY
+
INCREMENTAL DELIVERY
+
CUSTOMER COLLABORATION
+
TRANSPARENCY
+
INSPECTION
+
ADAPTATION
+
CONTINUOUS IMPROVEMENT
+
DISCIPLINED RESPONSE TO CHANGE
""")
