"""
SOFTWARE DEVELOPMENT LIFECYCLE
==============================

A detailed academic and practical learning program covering the Software
Development Lifecycle (SDLC) from fundamentals to advanced concepts.

The program is intentionally written as executable Python. Most of the
learning material is presented through structured functions, examples,
tables, simulations, calculations, and case studies.

Run:
    python software_development_lifecycle.py

No external libraries are required.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime


# =============================================================================
# 1. INTRODUCTION
# =============================================================================

def section(title):
    print("\n" + "=" * 80)
    print(title.upper())
    print("=" * 80)


def subsection(title):
    print("\n" + "-" * 80)
    print(title)
    print("-" * 80)


def explain(text):
    print(text)


def show(label, value):
    print(f"{label}: {value}")


def introduction():
    section("1. What Is the Software Development Lifecycle?")

    explain("""
The Software Development Lifecycle, commonly called SDLC, is a structured
approach used to plan, create, test, deploy, operate, maintain, and eventually
retire software.

Software development is not simply the activity of writing source code.

A complete software product involves:

    Business problems
        ↓
    Stakeholder needs
        ↓
    Requirements
        ↓
    Planning
        ↓
    Architecture and design
        ↓
    Development
        ↓
    Testing
        ↓
    Deployment
        ↓
    Operations
        ↓
    Maintenance
        ↓
    Retirement

The important idea is that software has a lifecycle.

A piece of software begins with a need or problem. It is transformed into
requirements, implemented as a technical solution, validated through testing,
released to users, maintained during its useful life, and eventually replaced
or retired.

SDLC provides a framework for controlling this process.

The exact activities vary between organizations. A safety-critical system,
a banking application, a mobile application, an internal business tool, and
a machine-learning platform may all use different processes.

Therefore, SDLC should not be understood as one fixed sequence of activities.

It is better understood as a collection of disciplines that help teams answer:

1. What problem are we solving?
2. Why are we solving it?
3. Who needs the solution?
4. What should the software do?
5. How should it be designed?
6. How will it be built?
7. How will we know that it works?
8. How will it be released safely?
9. How will it be operated?
10. How will it be changed over time?
11. When should it eventually be retired?
""")


# =============================================================================
# 2. WHY SDLC EXISTS
# =============================================================================

def why_sdlc_exists():
    section("2. Why Software Development Needs a Lifecycle")

    explain("""
Software projects become difficult when decisions are made without structure.

A team can write technically correct code and still produce a failed product.

For example:

    A system may work but solve the wrong business problem.
    A feature may exist but be unusable.
    A database may work but not scale.
    An application may pass functional testing but contain security flaws.
    A product may be released but have no monitoring.
    A project may be technically successful but financially unsuccessful.

SDLC addresses these problems by introducing discipline.

The major objectives are:

    - Understand requirements
    - Control project scope
    - Estimate resources
    - Manage risks
    - Design before implementation
    - Build systematically
    - Verify quality
    - Control releases
    - Operate production systems
    - Maintain and improve software
    - Preserve knowledge through documentation
    - Establish accountability

SDLC also creates checkpoints.

At different points, organizations can ask:

    Should we continue?
    Should we change direction?
    Should we stop?
    Is the solution technically feasible?
    Is the business case still valid?
    Are the risks acceptable?

These checkpoints are particularly important in large projects.
""")


# =============================================================================
# 3. CORE SDLC PHASES
# =============================================================================

def core_phases():
    section("3. Core Phases of the SDLC")

    phases = [
        ("Planning",
         "Define the problem, objectives, scope, stakeholders, resources, "
         "timeline, constraints, assumptions, and feasibility."),
        ("Requirements Analysis",
         "Identify and document what the system must accomplish."),
        ("System Design",
         "Define architecture, components, interfaces, data structures, "
         "security controls, infrastructure, and user experience."),
        ("Implementation",
         "Translate approved designs and requirements into working software."),
        ("Testing",
         "Verify that the software behaves correctly and satisfies requirements."),
        ("Deployment",
         "Move validated software into an environment where users can access it."),
        ("Operations",
         "Monitor, support, secure, and operate the production system."),
        ("Maintenance",
         "Correct defects, improve performance, adapt to changes, and add features."),
        ("Retirement",
         "Safely discontinue the system and migrate users and data where necessary.")
    ]

    for number, (name, description) in enumerate(phases, start=1):
        print(f"\n{number}. {name}")
        print(f"   {description}")

    explain("""
These phases are conceptual rather than universally sequential.

In a traditional lifecycle, a team may perform them in large sequential
stages.

In Agile and DevOps environments, the same activities occur repeatedly in
small cycles.

For example:

    Requirements → Design → Code → Test → Deploy → Monitor

may occur every two weeks, every week, every day, or even several times per
day.

The activities remain relevant even when the organizational process changes.
""")


# =============================================================================
# 4. SOFTWARE PROJECT VS SOFTWARE PRODUCT
# =============================================================================

def project_vs_product():
    section("4. Software Project and Software Product")

    explain("""
A project is temporary work performed to create a defined outcome.

A product is an evolving solution that continues to provide value to users.

This distinction matters because traditional project thinking often focuses
on completion:

    "Did we finish the project?"

Product thinking asks:

    "Is the software continuously delivering useful outcomes?"

For example, developing version 1.0 of a banking application may be a project.

Operating and continuously improving the banking application is a product
lifecycle.

The SDLC can therefore exist inside a broader product lifecycle.

Product lifecycle concerns may include:

    - Market research
    - Product strategy
    - Product-market fit
    - Pricing
    - Customer adoption
    - Competitive positioning
    - Product growth
    - Product retirement

SDLC concentrates more heavily on the software engineering lifecycle.
""")


# =============================================================================
# 5. STAKEHOLDERS
# =============================================================================

def stakeholders():
    section("5. Stakeholders in SDLC")

    stakeholder_map = {
        "Customer": "Pays for or commissions the solution.",
        "End User": "Actually uses the software.",
        "Product Manager": "Defines product direction and prioritization.",
        "Project Manager": "Coordinates project scope, schedule, resources, and risks.",
        "Business Analyst": "Analyzes business needs and translates them into requirements.",
        "Software Architect": "Defines major technical structures and architectural decisions.",
        "Developer": "Implements software.",
        "UI/UX Designer": "Designs user interaction and experience.",
        "QA Engineer": "Designs and executes quality validation.",
        "DevOps Engineer": "Automates delivery and operational infrastructure.",
        "Security Engineer": "Addresses security requirements and threats.",
        "Database Engineer": "Designs and manages data systems.",
        "Site Reliability Engineer": "Focuses on reliability, availability, and operations.",
        "Compliance Team": "Ensures regulatory and policy requirements are satisfied.",
        "Support Team": "Handles operational and user issues."
    }

    for role, responsibility in stakeholder_map.items():
        print(f"\n{role}")
        print(f"  {responsibility}")

    explain("""
A common SDLC mistake is treating developers as the only important participants.

Software is socio-technical.

Technical decisions interact with:

    Business
    Finance
    Legal requirements
    Security
    Operations
    Users
    Organizational policies

A technically elegant system can still fail if stakeholders disagree about
the actual objective.
""")


# =============================================================================
# 6. FEASIBILITY STUDY
# =============================================================================

def feasibility():
    section("6. Feasibility Analysis")

    explain("""
Before significant development begins, organizations may evaluate whether
the proposed system is worth pursuing.

Common feasibility dimensions are:

1. Technical feasibility
   Can the required technology be built and operated?

2. Economic feasibility
   Is the expected value justified by the cost?

3. Operational feasibility
   Can the organization actually use and support the system?

4. Legal feasibility
   Does the solution comply with applicable laws and regulations?

5. Schedule feasibility
   Can the solution be delivered within the required timeframe?

6. Organizational feasibility
   Does the organization have the capabilities and willingness required?

A feasibility study reduces the chance of spending substantial resources on
an idea that cannot realistically succeed.
""")

    development_cost = 1200000
    annual_benefit = 700000
    annual_operating_cost = 150000

    net_annual_benefit = annual_benefit - annual_operating_cost
    payback_period = development_cost / net_annual_benefit

    show("Development cost", f"₹{development_cost:,}")
    show("Annual benefit", f"₹{annual_benefit:,}")
    show("Annual operating cost", f"₹{annual_operating_cost:,}")
    show("Net annual benefit", f"₹{net_annual_benefit:,}")
    show("Approximate payback period", f"{payback_period:.2f} years")

    explain("""
Payback period is only one financial measure.

More sophisticated evaluation may consider:

    Net Present Value
    Internal Rate of Return
    Return on Investment
    Total Cost of Ownership
    Opportunity Cost
    Risk-adjusted value

Economic feasibility should not be reduced to a single number.
""")


# =============================================================================
# 7. REQUIREMENTS ENGINEERING
# =============================================================================

def requirements_engineering():
    section("7. Requirements Engineering")

    explain("""
Requirements engineering is the systematic process of discovering,
analyzing, documenting, validating, prioritizing, and managing requirements.

A requirement describes something that the system needs to provide or satisfy.

Requirements are commonly divided into:

    Functional requirements
    Non-functional requirements
    Business requirements
    User requirements
    System requirements
    Regulatory requirements
    Technical constraints
""")

    subsection("Functional Requirements")

    explain("""
Functional requirements describe behavior.

Examples:

    - A user can create an account.
    - A customer can reset a password.
    - A manager can approve an expense.
    - The system calculates tax.
    - The application generates a monthly report.

Functional requirements answer:

    "What should the system do?"
""")

    subsection("Non-Functional Requirements")

    explain("""
Non-functional requirements describe qualities, constraints, and operational
characteristics.

Examples:

    - The API should respond within 300 milliseconds for 95% of requests.
    - The system should support 50,000 concurrent users.
    - Customer passwords must be stored securely.
    - The service should achieve 99.9% availability.
    - The interface should support keyboard navigation.

They answer questions such as:

    How fast?
    How secure?
    How available?
    How scalable?
    How usable?
    How maintainable?
    How observable?
""")

    subsection("Requirement Quality")

    explain("""
Good requirements should be:

    Clear
    Unambiguous
    Testable
    Feasible
    Consistent
    Traceable
    Prioritized
    Understandable

A requirement such as:

    "The system should be fast."

is weak because "fast" is not measurable.

A stronger requirement is:

    "95% of authenticated API requests shall complete within 300 ms
     under a load of 2,000 requests per second."

The second requirement can be tested.
""")


# =============================================================================
# 8. USER STORIES
# =============================================================================

def user_stories():
    section("8. User Stories")

    explain("""
Agile teams frequently express requirements as user stories.

A common structure is:

    As a [type of user],
    I want [capability],
    so that [reason/value].

Example:

    As a customer,
    I want to download my transaction history,
    so that I can maintain my financial records.

The format forces the team to connect functionality with user value.

Acceptance criteria define the conditions under which the story is considered
complete.

Example:

    Given that the customer is authenticated,
    when the customer requests a transaction statement,
    then the system provides the statement for the selected period.

Acceptance criteria are important because they make requirements testable.
""")


# =============================================================================
# 9. REQUIREMENTS PRIORITIZATION
# =============================================================================

def prioritization():
    section("9. Requirements Prioritization")

    explain("""
Projects rarely have unlimited time and resources.

Requirements therefore need prioritization.

One popular approach is MoSCoW:

    M = Must have
    S = Should have
    C = Could have
    W = Won't have in the current release

Example for an online banking application:

    Must:
        Login
        Account balance
        Transaction history

    Should:
        Download statements

    Could:
        Spending visualization

    Won't:
        AI-generated financial advice

Prioritization prevents every requirement from being treated as equally
important.

Other prioritization techniques include:

    Value vs effort
    RICE
    WSJF
    Cost of delay
    Kano analysis
    Risk-based prioritization
    Business impact analysis
""")


# =============================================================================
# 10. REQUIREMENTS TRACEABILITY
# =============================================================================

def traceability():
    section("10. Requirements Traceability")

    explain("""
Requirements traceability means maintaining relationships between requirements
and other development artifacts.

A requirement may be connected to:

    Business objective
        ↓
    Requirement
        ↓
    Design component
        ↓
    Code
        ↓
    Test case
        ↓
    Release

This is especially important in regulated and safety-critical environments.

A traceability matrix can look like this:

    Requirement ID | Design | Implementation | Test
    -------------------------------------------------
    REQ-001        | D-01   | AUTH-01        | T-01
    REQ-002        | D-03   | PAY-02         | T-09

Traceability helps answer:

    Has every requirement been implemented?
    Has every requirement been tested?
    What will be affected if a requirement changes?
""")


# =============================================================================
# 11. SCOPE MANAGEMENT
# =============================================================================

def scope_management():
    section("11. Scope Management")

    explain("""
Scope defines what is included and excluded from the product or project.

Scope creep occurs when uncontrolled requirements are continuously added.

Example:

Initial project:

    "Build an employee attendance system."

Later requests:

    Payroll integration
    Face recognition
    Mobile application
    GPS tracking
    AI predictions
    Leave management
    Performance analytics
    Recruitment module

Each feature may be reasonable individually.

The problem is uncontrolled expansion.

Scope management establishes:

    What is included
    What is excluded
    What is deferred
    Who can approve changes
    How changes affect cost and schedule
""")

    explain("""
A change request should ideally be evaluated against:

    Scope
    Cost
    Schedule
    Quality
    Security
    Architecture
    Dependencies
    Operational impact

A change that looks small from the user's perspective may have substantial
technical consequences.
""")


# =============================================================================
# 12. SDLC MODELS
# =============================================================================

def lifecycle_models():
    section("12. SDLC Models")

    explain("""
Different development models organize SDLC activities differently.

Major models include:

    Waterfall
    V-Model
    Iterative
    Incremental
    Spiral
    Prototyping
    RAD
    Agile
    DevOps-oriented continuous delivery
    Hybrid models
""")


# =============================================================================
# 13. WATERFALL
# =============================================================================

def waterfall():
    section("13. Waterfall Model")

    explain("""
Waterfall organizes development into relatively sequential stages.

Typical flow:

    Requirements
        ↓
    Design
        ↓
    Implementation
        ↓
    Testing
        ↓
    Deployment
        ↓
    Maintenance

The model works best when requirements are relatively stable and predictable.

Advantages:

    - Clear stages
    - Extensive documentation
    - Predictable governance
    - Easier milestone tracking
    - Useful for highly regulated environments

Disadvantages:

    - Feedback arrives late
    - Changes can be expensive
    - User validation may occur too late
    - Assumptions can remain untested

The main weakness is not that sequential development is always wrong.

The problem is that assumptions may remain unvalidated until late in the
lifecycle.
""")


# =============================================================================
# 14. V MODEL
# =============================================================================

def v_model():
    section("14. V-Model")

    explain("""
The V-Model emphasizes the relationship between development activities and
corresponding testing activities.

A simplified representation is:

        Requirements
       /            \
  System Design   Acceptance Testing
     /                \
Architecture        System Testing
   /                    \
Module Design       Integration Testing
       \              /
        Implementation

The central idea is that testing is planned alongside development rather than
being treated as an activity that starts only after coding finishes.

This model is particularly useful where verification and validation are
critical.
""")


# =============================================================================
# 15. ITERATIVE MODEL
# =============================================================================

def iterative():
    section("15. Iterative Development")

    explain("""
Iterative development builds the system through repeated cycles.

Instead of attempting to define the final solution perfectly at the beginning:

    Plan
      ↓
    Build
      ↓
    Evaluate
      ↓
    Learn
      ↓
    Improve
      ↓
    Repeat

Each iteration improves understanding or capability.

This is useful when requirements are uncertain or when user feedback is
valuable.
""")


# =============================================================================
# 16. INCREMENTAL MODEL
# =============================================================================

def incremental():
    section("16. Incremental Development")

    explain("""
Incremental development delivers the system in functional pieces.

Example:

    Increment 1:
        Registration + Login

    Increment 2:
        Profile management

    Increment 3:
        Payments

    Increment 4:
        Reporting

Each increment adds capability.

Iterative and incremental approaches are related but different.

Iterative emphasizes repeated refinement.

Incremental emphasizes adding functional pieces.

A project can be both iterative and incremental.
""")


# =============================================================================
# 17. SPIRAL MODEL
# =============================================================================

def spiral():
    section("17. Spiral Model")

    explain("""
The Spiral Model combines iterative development with explicit risk analysis.

A cycle can involve:

    1. Define objectives
    2. Identify alternatives
    3. Analyze risks
    4. Develop and validate
    5. Review results
    6. Plan the next cycle

The defining characteristic is risk-driven development.

High-risk assumptions are investigated early.

For example:

    Can the architecture handle the expected traffic?
    Can the required algorithm achieve acceptable accuracy?
    Can sensitive data be processed legally?
    Can a third-party dependency meet reliability requirements?

Instead of discovering these issues after full development, the team attempts
to investigate them early.
""")


# =============================================================================
# 18. PROTOTYPING
# =============================================================================

def prototyping():
    section("18. Prototyping")

    explain("""
A prototype is an experimental representation of a system or feature.

It can be:

    Paper prototype
    UI mockup
    Clickable interface
    Proof of concept
    Technical prototype
    Working prototype

Prototypes reduce uncertainty.

There is an important distinction between:

    Throwaway prototype

and

    Evolutionary prototype

A throwaway prototype is built mainly to learn.

An evolutionary prototype gradually becomes part of the final product.

A prototype should not automatically be treated as production-ready software.

Prototype code may lack:

    Security
    Scalability
    Maintainability
    Error handling
    Testing
    Documentation
    Operational controls
""")


# =============================================================================
# 19. AGILE
# =============================================================================

def agile():
    section("19. Agile Software Development")

    explain("""
Agile is a family of approaches emphasizing:

    Individuals and interactions
    Working software
    Customer collaboration
    Responding to change

Agile does not mean:

    "No planning."

Agile means planning in a way that allows learning and adaptation.

Agile development typically uses:

    Short iterations
    Frequent feedback
    Prioritized backlogs
    Continuous refinement
    Incremental delivery
    Cross-functional teams
    Regular retrospectives
""")

    explain("""
Agile does not eliminate requirements, architecture, testing, documentation,
or project management.

Instead, these activities become more continuous and adaptive.
""")


# =============================================================================
# 20. SCRUM
# =============================================================================

def scrum():
    section("20. Scrum")

    explain("""
Scrum is an Agile framework.

Common Scrum roles/accountabilities include:

    Product Owner
    Scrum Master
    Developers

Common Scrum artifacts include:

    Product Backlog
    Sprint Backlog
    Increment

Common events include:

    Sprint
    Sprint Planning
    Daily Scrum
    Sprint Review
    Sprint Retrospective

A sprint is a fixed development period.

The product backlog contains potential work.

The sprint backlog represents work selected for the sprint.

The increment is the usable result produced during the sprint.
""")


# =============================================================================
# 21. AGILE TERMINOLOGY
# =============================================================================

def agile_terminology():
    section("21. Important Agile Concepts")

    concepts = {
        "Epic": "Large body of work that can be decomposed into smaller items.",
        "Feature": "A user-visible capability.",
        "User Story": "A concise expression of user need.",
        "Task": "A specific piece of implementation work.",
        "Acceptance Criteria": "Conditions used to determine whether work is acceptable.",
        "Definition of Done": "Shared criteria for considering work complete.",
        "Backlog": "Prioritized collection of potential work.",
        "Velocity": "Historical amount of work completed by a team per iteration.",
        "Retrospective": "Structured reflection on how the team can improve.",
        "Refinement": "Activity used to clarify and prepare backlog items."
    }

    for term, meaning in concepts.items():
        print(f"\n{term}:")
        print(f"  {meaning}")


# =============================================================================
# 22. PRODUCT BACKLOG
# =============================================================================

def backlog():
    section("22. Product Backlog")

    explain("""
A backlog is not simply a list of developer tasks.

A useful backlog represents potential product value and technical work.

Example:

    Priority 1:
        User authentication

    Priority 2:
        Transaction history

    Priority 3:
        Statement download

    Priority 4:
        Spending dashboard

Backlog items can change as the team learns more.

This makes the backlog a living representation of product priorities.
""")


# =============================================================================
# 23. SYSTEM DESIGN
# =============================================================================

def system_design():
    section("23. System Design")

    explain("""
System design translates requirements into a technical structure.

Design decisions can include:

    Application architecture
    Database architecture
    API design
    Component boundaries
    Communication protocols
    Data models
    Caching
    Authentication
    Authorization
    Logging
    Monitoring
    Error handling
    Scalability
    Reliability
    Security
    Deployment architecture

A design should be evaluated against actual requirements.

For example:

Requirement:
    "The service must support rapid growth."

Possible architectural considerations:

    Horizontal scaling
    Stateless services
    Load balancing
    Caching
    Database scaling
    Queue-based processing
    Partitioning

Architecture is therefore connected directly to requirements.
""")


# =============================================================================
# 24. ARCHITECTURAL STYLES
# =============================================================================

def architecture_styles():
    section("24. Architectural Styles")

    styles = {
        "Monolithic": "Most application functionality is deployed as one unit.",
        "Layered": "System is organized into layers such as presentation, business logic, and data.",
        "Client-Server": "Clients interact with centralized services.",
        "Microservices": "Application capabilities are separated into independently deployable services.",
        "Event-Driven": "Components communicate through events.",
        "Serverless": "Cloud provider manages much of the underlying execution infrastructure.",
        "Hexagonal": "Business logic is isolated from external systems through ports and adapters.",
        "Clean Architecture": "Core business rules are separated from infrastructure and delivery concerns."
    }

    for name, description in styles.items():
        print(f"\n{name}")
        print(f"  {description}")

    explain("""
There is no universally best architecture.

Architecture should be selected according to:

    Requirements
    Team capabilities
    Scale
    Complexity
    Organizational structure
    Operational maturity
    Cost
    Security
    Reliability requirements

Microservices are not automatically better than monoliths.

A simple system may benefit from a well-structured modular monolith.
""")


# =============================================================================
# 25. ARCHITECTURAL TRADE-OFFS
# =============================================================================

def architectural_tradeoffs():
    section("25. Architectural Trade-Offs")

    explain("""
Architecture involves trade-offs.

Examples:

    Strong consistency vs availability
    Simplicity vs flexibility
    Performance vs maintainability
    Cost vs redundancy
    Centralization vs autonomy
    Speed of development vs technical debt
    Customization vs standardization

A design decision should therefore be evaluated in context.

An architecture that is optimal for 1,000 users may be unnecessarily complex
for 100 users.

Similarly, architecture designed for 100 users may fail at 10 million users.

Architecture must correspond to actual constraints.
""")


# =============================================================================
# 26. DATABASE DESIGN
# =============================================================================

def database_design():
    section("26. Database Design")

    explain("""
Database design is part of SDLC because application requirements determine
how data must be stored, accessed, protected, and maintained.

Important concepts include:

    Entities
    Attributes
    Relationships
    Primary keys
    Foreign keys
    Constraints
    Indexes
    Transactions
    Normalization
    Denormalization
    Replication
    Backup
    Recovery
    Partitioning

A database design must consider both correctness and performance.
""")

    explain("""
Normalization reduces unnecessary duplication.

For example, instead of repeatedly storing:

    Customer ID
    Customer Name
    Customer Address

inside every transaction record, customer information can be represented in
a separate customer entity and referenced through a key.

Indexes can improve lookup speed but also create costs:

    Additional storage
    Additional write overhead
    Maintenance overhead

Every optimization has a trade-off.
""")


# =============================================================================
# 27. API DESIGN
# =============================================================================

def api_design():
    section("27. API Design")

    explain("""
An API defines how software components communicate.

An API design may specify:

    Endpoints
    HTTP methods
    Request formats
    Response formats
    Authentication
    Authorization
    Validation
    Error responses
    Pagination
    Rate limiting
    Versioning

Example conceptual API:

    POST /users
    GET /users/{id}
    PUT /users/{id}
    DELETE /users/{id}

A well-designed API should have predictable behavior.

API contracts should be treated as important system interfaces.
""")


# =============================================================================
# 28. DEVELOPMENT
# =============================================================================

def development():
    section("28. Software Development")

    explain("""
Implementation converts approved requirements and design decisions into
working software.

Professional development includes much more than typing code.

It involves:

    Source control
    Coding standards
    Code review
    Branch management
    Dependency management
    Configuration management
    Error handling
    Logging
    Testing
    Security
    Documentation
    Refactoring

Source code should be treated as one artifact within a larger engineering
system.
""")


# =============================================================================
# 29. VERSION CONTROL
# =============================================================================

def version_control():
    section("29. Version Control")

    explain("""
Version control records changes to source code and related artifacts.

Git is a common distributed version-control system.

Typical workflow:

    Working directory
        ↓
    Staging
        ↓
    Commit
        ↓
    Remote repository
        ↓
    Pull request
        ↓
    Review
        ↓
    Merge

Version control enables:

    History
    Collaboration
    Branching
    Reverting
    Auditing
    Parallel development

A commit should ideally represent a coherent change.
""")


# =============================================================================
# 30. CODE REVIEW
# =============================================================================

def code_review():
    section("30. Code Review")

    explain("""
Code review is a systematic examination of source code by other developers.

Reviewers may inspect:

    Correctness
    Readability
    Security
    Performance
    Maintainability
    Error handling
    Test coverage
    Architectural consistency

A code review is not simply a search for syntax mistakes.

It is a mechanism for transferring knowledge and maintaining engineering
standards.
""")


# =============================================================================
# 31. SOFTWARE TESTING
# =============================================================================

def testing():
    section("31. Software Testing")

    explain("""
Testing provides evidence about software behavior.

Testing is not the same as proving that software contains no defects.

Testing can reveal defects.

It cannot establish that every possible defect has been eliminated.

Major testing levels include:

    Unit testing
    Integration testing
    System testing
    Acceptance testing
""")

    subsection("Unit Testing")

    explain("""
Unit tests validate small units of behavior, often functions or classes.

They should generally be:

    Fast
    Isolated
    Deterministic
    Repeatable
""")

    subsection("Integration Testing")

    explain("""
Integration tests examine interactions between components.

Examples:

    Application + database
    Service + payment provider
    API + authentication service
""")

    subsection("System Testing")

    explain("""
System testing validates the behavior of the complete system against its
requirements.
""")

    subsection("Acceptance Testing")

    explain("""
Acceptance testing evaluates whether the system is acceptable to the intended
customer or business.

It connects software behavior with business expectations.
""")


# =============================================================================
# 32. TESTING TYPES
# =============================================================================

def testing_types():
    section("32. Important Testing Types")

    types = {
        "Functional Testing": "Checks whether required functionality works.",
        "Regression Testing": "Checks that existing behavior has not been broken by changes.",
        "Smoke Testing": "Performs basic checks to determine whether a build is suitable for deeper testing.",
        "Sanity Testing": "Focused validation after a limited change.",
        "Performance Testing": "Evaluates speed, responsiveness, throughput, and resource behavior.",
        "Load Testing": "Evaluates behavior under expected load.",
        "Stress Testing": "Evaluates behavior beyond expected operating conditions.",
        "Security Testing": "Identifies security weaknesses and validates controls.",
        "Usability Testing": "Evaluates how effectively users can interact with the system.",
        "Accessibility Testing": "Evaluates usability for people with disabilities.",
        "Compatibility Testing": "Evaluates behavior across supported environments.",
        "Recovery Testing": "Evaluates recovery after failures.",
        "Exploratory Testing": "Uses investigation and tester judgment to discover unexpected behavior."
    }

    for name, description in types.items():
        print(f"\n{name}:")
        print(f"  {description}")


# =============================================================================
# 33. VERIFICATION AND VALIDATION
# =============================================================================

def verification_validation():
    section("33. Verification and Validation")

    explain("""
Verification asks:

    "Are we building the product correctly?"

Examples:

    Code review
    Static analysis
    Design review
    Requirement inspection

Validation asks:

    "Are we building the correct product?"

Examples:

    User acceptance testing
    Usability evaluation
    Product demonstrations
    Real-world validation

A system can be correctly implemented according to an incorrect requirement.

Therefore both verification and validation are necessary.
""")


# =============================================================================
# 34. DEFECT MANAGEMENT
# =============================================================================

@dataclass
class Defect:
    defect_id: str
    severity: str
    priority: str
    status: str
    description: str


def defect_management():
    section("34. Defect Management")

    defects = [
        Defect("BUG-001", "Critical", "P1", "Open",
               "Authentication bypass discovered."),
        Defect("BUG-002", "Medium", "P2", "In Progress",
               "Incorrect date formatting."),
        Defect("BUG-003", "Low", "P3", "Closed",
               "Minor alignment issue.")
    ]

    for defect in defects:
        print(f"\n{defect.defect_id}")
        print(f"Severity: {defect.severity}")
        print(f"Priority: {defect.priority}")
        print(f"Status: {defect.status}")
        print(f"Description: {defect.description}")

    explain("""
Severity describes the technical or business impact of a defect.

Priority describes how urgently the organization wants it addressed.

A defect can therefore be:

    High severity + high priority
    High severity + lower priority
    Low severity + high priority
    Low severity + low priority

Severity and priority are not interchangeable.
""")


# =============================================================================
# 35. QUALITY ASSURANCE
# =============================================================================

def quality_assurance():
    section("35. Quality Assurance")

    explain("""
Quality Assurance focuses on improving the processes used to produce software.

Quality Control focuses more directly on identifying defects in the resulting
product.

A simplified distinction is:

    QA:
        "How can we improve the process so defects are less likely?"

    QC:
        "Does this product meet the required quality?"

Quality engineering increasingly combines both approaches.
""")


# =============================================================================
# 36. SOFTWARE QUALITY ATTRIBUTES
# =============================================================================

def quality_attributes():
    section("36. Software Quality Attributes")

    attributes = [
        "Correctness",
        "Reliability",
        "Availability",
        "Performance",
        "Scalability",
        "Security",
        "Usability",
        "Accessibility",
        "Maintainability",
        "Testability",
        "Portability",
        "Interoperability",
        "Observability",
        "Recoverability"
    ]

    for item in attributes:
        print(f"- {item}")

    explain("""
Quality attributes are important because functional correctness alone does
not define software quality.

A payment system that calculates the correct amount but is unavailable 30%
of the time is not a successful payment system.

A system that is fast but insecure is not a successful production system.

Quality is multidimensional.
""")


# =============================================================================
# 37. SECURITY IN SDLC
# =============================================================================

def security_sdlc():
    section("37. Security in the SDLC")

    explain("""
Security should not be postponed until the final testing phase.

A secure lifecycle integrates security into:

    Requirements
    Architecture
    Design
    Development
    Testing
    Deployment
    Operations
    Maintenance

This is often described as a Secure SDLC.

Security requirements may include:

    Authentication
    Authorization
    Encryption
    Secure session management
    Input validation
    Secrets management
    Audit logging
    Dependency management
    Vulnerability management
    Secure configuration
    Incident response
""")

    explain("""
Threat modeling can be performed during design.

A team can ask:

    What are we protecting?
    Who might attack the system?
    What could an attacker do?
    What are the attack surfaces?
    What controls reduce the risk?

Finding a security issue during architecture is usually less expensive than
discovering it after production deployment.
""")


# =============================================================================
# 38. DEVSECOPS
# =============================================================================

def devsecops():
    section("38. DevSecOps")

    explain("""
DevSecOps integrates security into development and operations rather than
treating security as an isolated final gate.

Typical automated controls can include:

    Static Application Security Testing
    Dependency scanning
    Secret detection
    Container scanning
    Infrastructure-as-code scanning
    Dynamic application testing

The objective is to detect problems early and continuously.
""")


# =============================================================================
# 39. DEVOPS
# =============================================================================

def devops():
    section("39. DevOps")

    explain("""
DevOps connects software development and IT operations through collaboration,
automation, continuous feedback, and shared responsibility.

A simplified lifecycle is:

    Plan
      ↓
    Code
      ↓
    Build
      ↓
    Test
      ↓
    Release
      ↓
    Deploy
      ↓
    Operate
      ↓
    Monitor
      ↓
    Feedback
      ↺

DevOps does not mean simply installing a CI/CD tool.

It represents changes in:

    Culture
    Process
    Automation
    Infrastructure
    Ownership
    Feedback
""")


# =============================================================================
# 40. CI/CD
# =============================================================================

def cicd():
    section("40. Continuous Integration and Continuous Delivery")

    explain("""
Continuous Integration means developers frequently integrate changes into a
shared codebase and automatically validate those changes.

A CI pipeline might perform:

    Checkout
        ↓
    Install dependencies
        ↓
    Lint
        ↓
    Unit tests
        ↓
    Build
        ↓
    Security scans
        ↓
    Integration tests

Continuous Delivery means software is maintained in a releasable state and
can be deployed through a controlled process.

Continuous Deployment goes one step further by automatically deploying
validated changes to production.
""")


# =============================================================================
# 41. DEPLOYMENT STRATEGIES
# =============================================================================

def deployment_strategies():
    section("41. Deployment Strategies")

    strategies = {
        "Big Bang": "Release the new version broadly at once.",
        "Rolling Deployment": "Gradually replace old instances with new ones.",
        "Blue-Green": "Maintain two environments and switch traffic between them.",
        "Canary": "Release to a small subset of users before wider rollout.",
        "Feature Flags": "Deploy code while controlling feature activation separately."
    }

    for name, description in strategies.items():
        print(f"\n{name}")
        print(f"  {description}")

    explain("""
Deployment strategy should reflect risk.

A critical financial system may require controlled rollout, monitoring, and
rollback mechanisms.

A low-risk internal tool may tolerate a simpler process.
""")


# =============================================================================
# 42. RELEASE MANAGEMENT
# =============================================================================

def release_management():
    section("42. Release Management")

    explain("""
A release is a controlled distribution of a software version.

Release management can include:

    Version identification
    Release notes
    Change approval
    Deployment planning
    Dependency validation
    Rollback planning
    Stakeholder communication
    Monitoring
    Post-release verification

A release should have a known state.

Teams should be able to answer:

    What changed?
    Which version is running?
    Who approved it?
    What dependencies changed?
    How can it be rolled back?
""")


# =============================================================================
# 43. CONFIGURATION MANAGEMENT
# =============================================================================

def configuration_management():
    section("43. Configuration Management")

    explain("""
Configuration management controls software and infrastructure configuration.

Examples include:

    Environment variables
    Feature flags
    Database settings
    Service endpoints
    Infrastructure definitions
    Dependency versions

Development, testing, staging, and production environments may have different
configuration values.

Configuration should be controlled and reproducible.

Sensitive values such as passwords and API keys should not be embedded in
source code.
""")


# =============================================================================
# 44. INFRASTRUCTURE AS CODE
# =============================================================================

def infrastructure_as_code():
    section("44. Infrastructure as Code")

    explain("""
Infrastructure as Code represents infrastructure configuration through
machine-readable definitions.

Instead of manually creating infrastructure, teams define resources such as:

    Networks
    Servers
    Databases
    Load balancers
    Permissions
    Storage

Benefits include:

    Reproducibility
    Version control
    Automation
    Auditability
    Consistency

Infrastructure becomes another artifact that can participate in the SDLC.
""")


# =============================================================================
# 45. CLOUD AND SDLC
# =============================================================================

def cloud():
    section("45. Cloud Computing and SDLC")

    explain("""
Cloud platforms change how infrastructure is provisioned and operated.

Common capabilities include:

    Compute
    Object storage
    Databases
    Networking
    Queues
    Containers
    Serverless functions
    Monitoring
    Identity management

Cloud does not eliminate architecture.

It changes the set of available architectural options.

Cloud systems still require decisions about:

    Cost
    Availability
    Security
    Performance
    Data residency
    Disaster recovery
    Scaling
    Vendor dependency
""")


# =============================================================================
# 46. OBSERVABILITY
# =============================================================================

def observability():
    section("46. Observability")

    explain("""
Observability is the ability to understand internal system behavior from
externally visible signals.

Three commonly discussed signals are:

    Logs
    Metrics
    Traces

Logs provide event details.

Metrics provide numerical measurements.

Traces help follow a request across distributed components.

Operational teams may monitor:

    Error rate
    Latency
    Throughput
    CPU utilization
    Memory usage
    Queue depth
    Database performance
    Availability
""")


# =============================================================================
# 47. INCIDENT MANAGEMENT
# =============================================================================

def incident_management():
    section("47. Incident Management")

    explain("""
An incident is an event that disrupts or threatens normal service.

A typical incident process may involve:

    Detection
        ↓
    Triage
        ↓
    Severity classification
        ↓
    Investigation
        ↓
    Mitigation
        ↓
    Recovery
        ↓
    Communication
        ↓
    Root-cause analysis
        ↓
    Corrective actions

The immediate goal during a serious incident is usually restoration of service.

The deeper goal is preventing recurrence.
""")


# =============================================================================
# 48. ROOT CAUSE ANALYSIS
# =============================================================================

def root_cause_analysis():
    section("48. Root Cause Analysis")

    explain("""
Root-cause analysis attempts to understand why an incident or defect occurred.

A common technique is the Five Whys.

Example:

    Why did users receive incorrect balances?
        Because the balance calculation used stale data.

    Why was stale data used?
        Because cache invalidation failed.

    Why did cache invalidation fail?
        Because one service bypassed the invalidation mechanism.

    Why was that possible?
        Because cache access was not centralized.

    Why was this not detected?
        Because integration tests did not cover that path.

The objective is not to blame an individual.

The objective is to identify system-level causes and corrective actions.
""")


# =============================================================================
# 49. MAINTENANCE
# =============================================================================

def maintenance():
    section("49. Software Maintenance")

    explain("""
Software maintenance continues after deployment.

Common categories include:

    Corrective maintenance
        Fix defects.

    Adaptive maintenance
        Adapt to changes in environments, platforms, regulations, or dependencies.

    Perfective maintenance
        Improve functionality, usability, or performance.

    Preventive maintenance
        Reduce future maintenance problems.

Maintenance can consume a substantial portion of the total software lifecycle.

Software therefore should be designed for change, not merely for initial release.
""")


# =============================================================================
# 50. TECHNICAL DEBT
# =============================================================================

def technical_debt():
    section("50. Technical Debt")

    explain("""
Technical debt represents future cost created by technical shortcuts,
suboptimal decisions, or deferred engineering work.

Examples:

    Duplicated code
    Outdated dependencies
    Missing tests
    Poor architecture
    Manual deployment
    Weak documentation
    Inconsistent configuration

Technical debt is not automatically bad.

Sometimes a team deliberately takes a shortcut to validate a business idea.

The problem occurs when debt is ignored or allowed to accumulate without
control.

Technical debt has carrying costs.

It can increase:

    Development time
    Defect rates
    Operational risk
    Security exposure
    Change difficulty
""")


# =============================================================================
# 51. REFACTORING
# =============================================================================

def refactoring():
    section("51. Refactoring")

    explain("""
Refactoring changes the internal structure of software without intentionally
changing its externally observable behavior.

Examples:

    Extracting functions
    Removing duplication
    Simplifying conditional logic
    Renaming unclear variables
    Splitting large classes
    Improving module boundaries

Refactoring reduces complexity and can make future changes safer.

Good automated tests provide confidence during refactoring.
""")


# =============================================================================
# 52. RISK MANAGEMENT
# =============================================================================

@dataclass
class Risk:
    risk_id: str
    description: str
    probability: float
    impact: float

    @property
    def exposure(self):
        return self.probability * self.impact


def risk_management():
    section("52. Risk Management")

    explain("""
Risk is the possibility of an uncertain event affecting project or product
objectives.

Common software risks include:

    Requirements volatility
    Technology uncertainty
    Security threats
    Dependency failure
    Vendor lock-in
    Skill shortages
    Schedule pressure
    Budget limitations
    Integration problems
    Performance problems
    Regulatory changes
    Data quality problems
""")

    risks = [
        Risk("R1", "Third-party payment API instability", 0.30, 90),
        Risk("R2", "Requirements change", 0.60, 50),
        Risk("R3", "Critical developer unavailable", 0.20, 80),
        Risk("R4", "Performance target missed", 0.40, 85),
    ]

    print("\nRisk Register:")
    print(f"{'ID':<8}{'Probability':<15}{'Impact':<12}{'Exposure':<12}")
    print("-" * 50)

    for risk in risks:
        print(
            f"{risk.risk_id:<8}"
            f"{risk.probability:<15.2f}"
            f"{risk.impact:<12.2f}"
            f"{risk.exposure:<12.2f}"
        )

    explain("""
Risk exposure can be approximated as:

    Probability × Impact

This is a simplification.

Real risk analysis may consider:

    Detectability
    Time horizon
    Dependencies
    Uncertainty
    Secondary effects
    Mitigation cost
""")


# =============================================================================
# 53. PROJECT PLANNING
# =============================================================================

def project_planning():
    section("53. Project Planning")

    explain("""
Planning determines how work will be organized.

Important planning dimensions include:

    Scope
    Deliverables
    Work breakdown
    Dependencies
    Resources
    Schedule
    Budget
    Risks
    Quality
    Communication
    Governance

A Work Breakdown Structure decomposes large work into manageable pieces.

Example:

    E-commerce Platform

        Authentication
            Registration
            Login
            Password reset

        Product Catalog
            Product database
            Search
            Filters

        Checkout
            Cart
            Payment
            Order confirmation

        Operations
            Monitoring
            Logging
            Deployment
""")


# =============================================================================
# 54. ESTIMATION
# =============================================================================

def estimation():
    section("54. Software Estimation")

    explain("""
Software estimation is difficult because software work contains uncertainty.

Common estimation approaches include:

    Expert judgment
    Analogous estimation
    Parametric estimation
    Three-point estimation
    Story points
    Function points
    Use-case points

Three-point estimation may use:

    Optimistic estimate = O
    Most likely estimate = M
    Pessimistic estimate = P

A simple expected estimate can be:

    E = (O + 4M + P) / 6
""")

    optimistic = 10
    most_likely = 16
    pessimistic = 30

    expected = (
        optimistic +
        4 * most_likely +
        pessimistic
    ) / 6

    show("Optimistic", optimistic)
    show("Most likely", most_likely)
    show("Pessimistic", pessimistic)
    show("Expected estimate", round(expected, 2))

    explain("""
Estimation should be treated as a forecast rather than a promise.

As knowledge improves, estimates should be updated.
""")


# =============================================================================
# 55. DEPENDENCY MANAGEMENT
# =============================================================================

def dependency_management():
    section("55. Dependency Management")

    explain("""
Modern software depends heavily on external components.

Dependencies may include:

    Libraries
    Frameworks
    APIs
    Cloud services
    Operating systems
    Databases
    Infrastructure components

Dependencies create both productivity and risk.

Risks include:

    Vulnerabilities
    Breaking changes
    License restrictions
    Abandonment
    Availability problems
    Version conflicts

Dependency management should therefore be part of SDLC.
""")


# =============================================================================
# 56. DOCUMENTATION
# =============================================================================

def documentation():
    section("56. Software Documentation")

    explain("""
Documentation preserves knowledge.

Important documents may include:

    Business requirements
    Product requirements
    Architecture diagrams
    API specifications
    Database documentation
    Deployment procedures
    Runbooks
    Test plans
    Test reports
    Release notes
    Security documentation
    Incident reports
    Decision records

Architecture Decision Records are particularly useful for recording important
technical decisions.

A decision record can capture:

    Context
    Decision
    Alternatives
    Consequences

This prevents teams from repeatedly asking why an important decision was made.
""")


# =============================================================================
# 57. CHANGE MANAGEMENT
# =============================================================================

def change_management():
    section("57. Change Management")

    explain("""
Software systems change continuously.

Changes can originate from:

    Users
    Business strategy
    Regulations
    Security findings
    Technology changes
    Market conditions
    Operational incidents

Change management evaluates:

    What is changing?
    Why?
    What is affected?
    What is the risk?
    How will it be tested?
    How will it be deployed?
    How will it be reversed?

The larger the risk, the stronger the control required.
""")


# =============================================================================
# 58. CONFIGURATION ITEMS
# =============================================================================

def configuration_items():
    section("58. Configuration Items")

    explain("""
A configuration item is an artifact that needs controlled management.

Examples:

    Source code
    Database schema
    Infrastructure definition
    Configuration file
    API specification
    Deployment manifest
    Documentation

Configuration management ensures that the organization knows:

    Which version exists
    Where it is used
    What changed
    Who changed it
    What other components depend on it
""")


# =============================================================================
# 59. SOFTWARE METRICS
# =============================================================================

def metrics():
    section("59. Software Metrics")

    explain("""
Metrics help organizations understand software delivery and system behavior.

Examples include:

    Lead time
    Cycle time
    Deployment frequency
    Change failure rate
    Mean time to recovery
    Defect density
    Test coverage
    Availability
    Error rate
    Latency
    Customer satisfaction
    Escaped defects
""")

    explain("""
DORA-style delivery metrics are often discussed in DevOps contexts:

    Deployment frequency
    Lead time for changes
    Change failure rate
    Time to restore service

Metrics should be interpreted carefully.

Optimizing a metric without understanding the underlying system can produce
undesirable behavior.

For example, increasing deployment frequency alone does not necessarily mean
that software delivery improved.
""")


# =============================================================================
# 60. LEAD TIME AND CYCLE TIME
# =============================================================================

def lead_cycle_time():
    section("60. Lead Time and Cycle Time")

    explain("""
Lead time measures elapsed time from a defined starting point to delivery.

Cycle time generally focuses on the period during which active work is being
performed.

Example:

    Requirement requested:
        January 1

    Development begins:
        January 10

    Production deployment:
        January 20

Lead time:
        January 1 → January 20

Cycle time may be:
        January 10 → January 20

The exact definitions should be standardized within the organization.
""")


# =============================================================================
# 61. TEST COVERAGE
# =============================================================================

def test_coverage():
    section("61. Test Coverage")

    explain("""
Test coverage describes which parts of software or behavior are exercised by
tests.

Common forms include:

    Statement coverage
    Branch coverage
    Function coverage
    Condition coverage

High coverage does not automatically mean high quality.

A poorly designed test suite can execute many lines while failing to validate
important behavior.

Coverage is therefore an indicator, not proof of correctness.
""")


# =============================================================================
# 62. RELIABILITY
# =============================================================================

def reliability():
    section("62. Reliability and Availability")

    explain("""
Reliability describes the ability of a system to perform correctly over time.

Availability describes the proportion of time a service is operational.

A simplified availability formula is:

    Availability =
        Uptime / (Uptime + Downtime)

Suppose a service has:

    99.9% availability

The approximate annual downtime allowance is:

    365 × 24 × 60 × 0.001 minutes
""")

    annual_minutes = 365 * 24 * 60
    downtime = annual_minutes * 0.001

    show("Annual minutes", annual_minutes)
    show("Approximate downtime at 99.9%", f"{downtime:.2f} minutes")


# =============================================================================
# 63. SCALABILITY
# =============================================================================

def scalability():
    section("63. Scalability")

    explain("""
Scalability describes the ability of a system to handle increased demand.

Vertical scaling:

    Increase resources of an existing machine.

Horizontal scaling:

    Add more machines or service instances.

Scalability can also involve:

    Caching
    Database replication
    Partitioning
    Asynchronous processing
    Queues
    Load balancing
    Content delivery networks

Scaling is not simply "adding more servers."

Bottlenecks must first be understood.
""")


# =============================================================================
# 64. PERFORMANCE ENGINEERING
# =============================================================================

def performance():
    section("64. Performance Engineering")

    explain("""
Performance engineering considers performance throughout SDLC.

Important measures include:

    Latency
    Throughput
    Response time
    Resource utilization
    Concurrency

For example:

    Throughput = requests / second

    Average response time =
        total response time / number of requests

Performance requirements should be measurable.

Optimization should begin with evidence.

Profiling and measurement are preferable to assumptions about where the
bottleneck exists.
""")


# =============================================================================
# 65. DATA PRIVACY
# =============================================================================

def privacy():
    section("65. Privacy in SDLC")

    explain("""
Privacy should be considered during requirements and design.

Questions include:

    What personal data is collected?
    Why is it collected?
    How long is it retained?
    Who can access it?
    Where is it stored?
    Is it encrypted?
    Can users modify or delete it?
    Is the collection legally justified?

Privacy-by-design treats data protection as an architectural concern rather
than a final compliance checklist.
""")


# =============================================================================
# 66. COMPLIANCE
# =============================================================================

def compliance():
    section("66. Compliance and Governance")

    explain("""
Some software systems must comply with industry or organizational controls.

Examples may involve:

    Financial controls
    Data protection
    Healthcare requirements
    Security standards
    Audit requirements
    Record retention
    Access control

Compliance requirements can influence:

    Architecture
    Logging
    Access management
    Documentation
    Testing
    Deployment
    Data storage
    Change approval

Compliance should be translated into concrete engineering requirements.
""")


# =============================================================================
# 67. ENVIRONMENTS
# =============================================================================

def environments():
    section("67. Software Environments")

    explain("""
Common environments include:

    Development
    Testing
    Integration
    Staging
    Production

Development is used for active implementation.

Testing is used for validation.

Staging attempts to resemble production closely enough for meaningful
pre-production validation.

Production serves real users.

Environment differences can create deployment failures.

Therefore environment configuration should be controlled and reproducible.
""")


# =============================================================================
# 68. BACKUP AND DISASTER RECOVERY
# =============================================================================

def disaster_recovery():
    section("68. Backup and Disaster Recovery")

    explain("""
Production systems need recovery strategies.

Important concepts include:

    Backup
    Restore
    Replication
    Failover
    Disaster recovery
    Business continuity

Two important recovery objectives are:

    RPO = Recovery Point Objective
    RTO = Recovery Time Objective

RPO answers:

    "How much data loss can we tolerate?"

RTO answers:

    "How quickly must the service be restored?"

Example:

    RPO = 15 minutes
    RTO = 1 hour

This means the organization may tolerate approximately 15 minutes of data
loss and expects service restoration within one hour, assuming the stated
objectives are technically achievable.
""")


# =============================================================================
# 69. HIGH AVAILABILITY
# =============================================================================

def high_availability():
    section("69. High Availability")

    explain("""
High availability uses redundancy and failure-handling mechanisms to reduce
service interruption.

Possible techniques:

    Multiple application instances
    Load balancing
    Database replication
    Failover
    Health checks
    Redundant networks
    Multiple availability zones

High availability introduces complexity and cost.

It must therefore be justified by business requirements.
""")


# =============================================================================
# 70. FAILURE MODES
# =============================================================================

def failure_modes():
    section("70. Failure Analysis")

    explain("""
Systems can fail in many ways.

Examples:

    Application crash
    Database failure
    Network failure
    Dependency outage
    Authentication failure
    Capacity exhaustion
    Data corruption
    Configuration error
    Deployment error

Failure Mode and Effects Analysis can help teams evaluate:

    Failure mode
    Effect
    Cause
    Severity
    Likelihood
    Detectability
    Mitigation
""")


# =============================================================================
# 71. AGILE VS WATERFALL
# =============================================================================

def agile_vs_waterfall():
    section("71. Agile and Waterfall Comparison")

    comparison = [
        ("Requirements",
         "Often defined more completely upfront",
         "Continuously refined"),
        ("Delivery",
         "Often later in lifecycle",
         "Frequent increments"),
        ("Feedback",
         "Can arrive relatively late",
         "Frequent"),
        ("Change",
         "Usually controlled through formal change process",
         "Expected and managed continuously"),
        ("Planning",
         "Detailed upfront planning",
         "Rolling and adaptive planning"),
        ("Testing",
         "Often concentrated after implementation",
         "Integrated throughout iterations"),
        ("Risk",
         "Can accumulate if assumptions remain untested",
         "Frequent feedback can expose risk earlier")
    ]

    print(f"{'Area':<18}{'Waterfall':<45}{'Agile'}")
    print("-" * 105)

    for area, waterfall_value, agile_value in comparison:
        print(
            f"{area:<18}"
            f"{waterfall_value:<45}"
            f"{agile_value}"
        )

    explain("""
Neither approach should be treated as universally superior.

The appropriate process depends on:

    Requirement stability
    Risk
    Regulatory constraints
    Customer feedback needs
    Organizational structure
    Product uncertainty
    Delivery frequency
""")


# =============================================================================
# 72. DEVOPS VS AGILE
# =============================================================================

def devops_vs_agile():
    section("72. Agile and DevOps")

    explain("""
Agile primarily focuses on adaptive product development and frequent delivery.

DevOps extends the concern into deployment and operations.

A simplified relationship is:

    Agile:
        Build the right software and deliver it iteratively.

    DevOps:
        Build, deliver, operate, observe, and improve software continuously.

They are complementary rather than competing concepts.
""")


# =============================================================================
# 73. SDLC AND CI/CD
# =============================================================================

def sdlc_cicd():
    section("73. SDLC and CI/CD Relationship")

    explain("""
CI/CD is an implementation mechanism that automates parts of the SDLC.

For example:

    Code change
        ↓
    CI pipeline
        ↓
    Automated tests
        ↓
    Security checks
        ↓
    Build artifact
        ↓
    Deployment
        ↓
    Monitoring
        ↓
    Feedback

CI/CD does not replace requirements engineering, architecture, product
management, user research, or operational planning.

It automates repeatable engineering activities.
""")


# =============================================================================
# 74. SOFTWARE LIFECYCLE ARTIFACTS
# =============================================================================

def artifacts():
    section("74. SDLC Artifacts")

    artifacts = [
        "Business case",
        "Project charter",
        "Requirements specification",
        "User stories",
        "Acceptance criteria",
        "Product backlog",
        "Architecture diagrams",
        "Architecture decision records",
        "Database schema",
        "API specification",
        "Source code",
        "Build artifacts",
        "Test plan",
        "Test cases",
        "Defect reports",
        "Security assessment",
        "Deployment configuration",
        "Release notes",
        "Runbooks",
        "Monitoring dashboards",
        "Incident reports",
        "Retirement plan"
    ]

    for artifact in artifacts:
        print(f"- {artifact}")


# =============================================================================
# 75. SOFTWARE CONFIGURATION ITEMS AND BASELINES
# =============================================================================

def baselines():
    section("75. Baselines")

    explain("""
A baseline is an approved version of a set of artifacts that serves as a
reference point.

Examples:

    Requirements baseline
    Design baseline
    Release baseline

Once baselined, changes may require controlled approval depending on the
process.

Baselines are useful in environments where traceability and controlled change
are important.
""")


# =============================================================================
# 76. GOVERNANCE
# =============================================================================

def governance():
    section("76. Software Governance")

    explain("""
Governance establishes how decisions are made and controlled.

Governance can define:

    Roles
    Approval authority
    Policies
    Standards
    Risk thresholds
    Security requirements
    Architecture principles
    Compliance controls
    Release criteria

Good governance should provide control without creating unnecessary
bureaucracy.

The required level of governance should correspond to the risk of the system.
""")


# =============================================================================
# 77. DEFINITION OF DONE
# =============================================================================

def definition_of_done():
    section("77. Definition of Done")

    explain("""
Definition of Done is a shared quality standard for completed work.

Example:

    - Code implemented
    - Peer reviewed
    - Unit tests passed
    - Integration tests passed
    - Security checks completed
    - Documentation updated
    - Acceptance criteria satisfied
    - Deployable artifact produced

Without a clear definition, "done" can mean different things to different
people.

A developer may consider code complete.

QA may consider testing incomplete.

Operations may consider deployment incomplete.

A shared definition removes much of this ambiguity.
""")


# =============================================================================
# 78. DEFINITION OF READY
# =============================================================================

def definition_of_ready():
    section("78. Definition of Ready")

    explain("""
Some Agile teams use a Definition of Ready to describe whether a work item
is sufficiently understood to begin implementation.

Possible criteria:

    Clear objective
    Acceptance criteria
    Dependencies identified
    Reasonable size
    Known constraints
    Required designs available

Definition of Ready is a team practice, not a universal requirement of Agile.
""")


# =============================================================================
# 79. QUALITY GATES
# =============================================================================

def quality_gates():
    section("79. Quality Gates")

    explain("""
A quality gate is a decision point requiring specified conditions before work
can proceed.

Examples:

    No critical security vulnerabilities
    Required tests passed
    Code review completed
    Acceptance criteria satisfied
    Performance target achieved
    Compliance evidence available

Quality gates can reduce risk when used appropriately.

Excessive gates can slow delivery without providing proportional value.
""")


# =============================================================================
# 80. BUILD VS RELEASE VS DEPLOY
# =============================================================================

def build_release_deploy():
    section("80. Build, Release, and Deployment")

    explain("""
These concepts are related but distinct.

Build:

    Transform source code into a deployable artifact.

Release:

    Approve and prepare a version for distribution.

Deployment:

    Install or make the version available in an environment.

A system may support:

    Build once
    Test the same artifact
    Promote the same artifact through environments

This reduces the risk of environment-specific differences.
""")


# =============================================================================
# 81. FEATURE FLAGS
# =============================================================================

def feature_flags():
    section("81. Feature Flags")

    explain("""
Feature flags separate deployment from feature activation.

For example:

    Code is deployed:
        Feature = OFF

    Later:
        Feature = ON

This can allow:

    Canary releases
    A/B experiments
    Gradual rollout
    Emergency disabling
    User segmentation

Feature flags themselves require lifecycle management.

Old flags should eventually be removed.
""")


# =============================================================================
# 82. BLUE GREEN DEPLOYMENT
# =============================================================================

def blue_green():
    section("82. Blue-Green Deployment")

    explain("""
Blue-Green deployment maintains two environments.

Suppose:

    Blue = current production
    Green = new version

The new version is deployed to Green and validated.

Traffic can then be redirected from Blue to Green.

If serious problems occur, traffic can potentially be returned to Blue.

The feasibility of rollback depends on database changes and other stateful
components.

Therefore database migration strategy must be considered.
""")


# =============================================================================
# 83. CANARY DEPLOYMENT
# =============================================================================

def canary():
    section("83. Canary Deployment")

    explain("""
Canary deployment exposes a new version to a small percentage of traffic.

Example:

    95% → Version A
     5% → Version B

The team monitors:

    Error rate
    Latency
    Conversion
    Crashes
    Business metrics

If Version B performs acceptably, traffic can be increased.

This reduces the blast radius of a defective release.
""")


# =============================================================================
# 84. ROLLBACK
# =============================================================================

def rollback():
    section("84. Rollback")

    explain("""
Rollback means returning to a previously known-good version or state.

A rollback strategy must consider:

    Application code
    Database schema
    Data migrations
    Configuration
    External integrations
    Cached data

Rolling back code is not always enough.

For example:

    Version A database schema
            ↓
    Version B migration
            ↓
    Version B application

If the migration permanently changes data, simply deploying Version A may not
restore compatibility.

This is why database migrations need careful backward-compatibility planning.
""")


# =============================================================================
# 85. DATABASE MIGRATION
# =============================================================================

def database_migration():
    section("85. Database Migration")

    explain("""
Database migrations change database structures or data.

Safer migration patterns often separate:

    Expand
        Add compatible structures.

    Migrate
        Move or transform data.

    Contract
        Remove obsolete structures after old code is no longer required.

This approach reduces the risk of deploying application versions that expect
different database schemas.
""")


# =============================================================================
# 86. SOFTWARE RETIREMENT
# =============================================================================

def retirement():
    section("86. Software Retirement")

    explain("""
Software retirement is an actual SDLC phase.

A system may be retired because:

    Business value has declined
    Replacement system exists
    Technology is obsolete
    Maintenance is too expensive
    Security risk is too high
    Regulatory requirements changed

Retirement activities may include:

    User migration
    Data migration
    Data retention
    Contract termination
    Infrastructure removal
    Access revocation
    Documentation
    Security cleanup

Simply shutting down a server does not necessarily complete retirement.
""")


# =============================================================================
# 87. LEGACY SYSTEMS
# =============================================================================

def legacy_systems():
    section("87. Legacy Systems")

    explain("""
Legacy software is not necessarily bad software.

A legacy system is often an important system built using older technologies,
architectures, or practices.

Legacy systems may be difficult to change because of:

    Missing documentation
    Old technology
    Tight coupling
    Fragile integrations
    Lack of tests
    Specialized knowledge
    Business criticality

Possible strategies include:

    Maintain
    Refactor
    Replatform
    Rehost
    Replace
    Encapsulate
    Gradually modernize
""")


# =============================================================================
# 88. STRANGLER PATTERN
# =============================================================================

def strangler_pattern():
    section("88. Strangler Modernization Pattern")

    explain("""
The Strangler approach gradually replaces parts of a legacy system.

Instead of:

    Legacy system → immediate replacement

the organization may use:

    Legacy system
       +
    New component
       +
    New component
       +
    New component

Over time, responsibility moves toward the new architecture.

This reduces the risk associated with a large one-time rewrite.

The pattern requires careful routing, data synchronization, and boundary design.
""")


# =============================================================================
# 89. SOFTWARE DEVELOPMENT LIFECYCLE FOR A BANKING APPLICATION
# =============================================================================

def banking_case_study():
    section("89. Case Study: Banking Application")

    explain("""
Suppose an organization wants to develop a digital banking application.

STEP 1: Business Problem

Customers need secure digital access to accounts.

STEP 2: Requirements

Functional:

    Login
    Balance inquiry
    Transaction history
    Fund transfer

Non-functional:

    High availability
    Strong authentication
    Low latency
    Auditability
    Security
    Regulatory compliance

STEP 3: Architecture

Possible components:

    Mobile/Web Client
          ↓
    API Gateway
          ↓
    Authentication
          ↓
    Banking Services
          ↓
    Transaction Database

STEP 4: Development

Developers implement services using version control and code review.

STEP 5: Testing

Testing includes:

    Unit
    Integration
    Security
    Performance
    Acceptance
    Regression

STEP 6: Deployment

A controlled deployment strategy is used.

STEP 7: Operations

Monitor:

    Failed transactions
    Latency
    Availability
    Authentication failures
    Database health

STEP 8: Maintenance

Security updates, defect correction, regulatory changes, and new features are
continuously handled.

This example demonstrates that SDLC extends well beyond coding.
""")


# =============================================================================
# 90. CASE STUDY: E-COMMERCE
# =============================================================================

def ecommerce_case_study():
    section("90. Case Study: E-Commerce Platform")

    explain("""
Business objective:

    Allow customers to discover products and purchase them online.

Core requirements:

    User registration
    Product catalog
    Search
    Cart
    Checkout
    Payment
    Order management
    Notifications

Important non-functional requirements:

    Scalability
    Availability
    Security
    Performance
    Observability

Potential risks:

    Payment provider outage
    Inventory inconsistency
    Traffic spikes
    Fraud
    Data leakage
    Deployment failures

The SDLC must therefore connect business objectives with technical design,
testing, deployment, and operational controls.
""")


# =============================================================================
# 91. CASE STUDY: SOFTWARE DEVELOPMENT FLOW
# =============================================================================

def complete_flow():
    section("91. Complete SDLC Example")

    explain("""
Imagine a company wants to build an employee leave-management system.

1. Planning

    Define business objective and scope.

2. Requirements

    Employees request leave.
    Managers approve or reject requests.
    HR views reports.

3. Design

    Define:
        Users
        Roles
        APIs
        Database
        Authentication
        Notification mechanism

4. Development

    Implement backend and frontend.

5. Testing

    Test:
        Login
        Leave calculation
        Approval workflow
        Authorization
        Notifications

6. Deployment

    Deploy to staging.
    Validate.
    Release to production.

7. Operations

    Monitor errors and availability.

8. Maintenance

    Fix defects and support policy changes.

9. Retirement

    If replaced by another HR platform, migrate data and safely decommission
    the old system.

This is SDLC in practical terms.
""")


# =============================================================================
# 92. COMMON SDLC FAILURE MODES
# =============================================================================

def common_failures():
    section("92. Common SDLC Failures")

    failures = {
        "Unclear requirements":
            "The team builds functionality that does not solve the actual problem.",
        "Poor scope control":
            "Continuous additions cause schedule and resource problems.",
        "Architecture without requirements":
            "Technical complexity is introduced without business justification.",
        "Testing too late":
            "Defects are discovered when correction is expensive.",
        "No production monitoring":
            "Failures remain invisible until users report them.",
        "Weak security":
            "Security becomes a last-minute activity.",
        "Poor documentation":
            "Knowledge becomes dependent on individual team members.",
        "Manual deployment":
            "Human error becomes a recurring operational risk.",
        "Ignoring technical debt":
            "Future changes become increasingly expensive.",
        "No rollback strategy":
            "Failed releases become difficult to recover from.",
        "Metrics without context":
            "Teams optimize numbers instead of outcomes."
    }

    for failure, consequence in failures.items():
        print(f"\n{failure}")
        print(f"  {consequence}")


# =============================================================================
# 93. SDLC DECISION FRAMEWORK
# =============================================================================

def decision_framework():
    section("93. Choosing an SDLC Approach")

    explain("""
When selecting a development approach, consider:

    1. Requirement stability
    2. Product uncertainty
    3. Technical risk
    4. Regulatory requirements
    5. Customer feedback frequency
    6. Release frequency
    7. Organizational maturity
    8. Team structure
    9. System criticality
    10. Cost of failure

For example:

Stable + highly regulated:
    More formal lifecycle controls may be appropriate.

Highly uncertain product:
    Iterative experimentation may be valuable.

High deployment frequency:
    Strong automation and CI/CD may be appropriate.

Safety-critical system:
    Extensive verification, traceability, documentation, and governance may
    be required.

The process should fit the problem.
""")


# =============================================================================
# 94. SDLC AND ORGANIZATIONAL MATURITY
# =============================================================================

def maturity():
    section("94. Engineering Maturity")

    explain("""
Organizations often mature through progressively stronger engineering
capabilities.

A simplified progression could be:

    Ad hoc
        ↓
    Repeatable
        ↓
    Defined
        ↓
    Measured
        ↓
    Continuously improved

An immature process may depend heavily on individual knowledge.

A mature process tends to have:

    Standard practices
    Automated validation
    Clear ownership
    Measurable outcomes
    Reproducible deployments
    Documented architecture
    Security controls
    Monitoring
    Continuous improvement

Maturity does not mean bureaucracy.

The goal is predictable delivery and controlled risk.
""")


# =============================================================================
# 95. PEOPLE, PROCESS, TECHNOLOGY
# =============================================================================

def people_process_technology():
    section("95. People, Process, and Technology")

    explain("""
SDLC performance depends on three broad dimensions:

    People
    Process
    Technology

People include:

    Skills
    Communication
    Leadership
    Collaboration
    Ownership

Process includes:

    Planning
    Requirements
    Testing
    Change management
    Release management

Technology includes:

    Programming languages
    Frameworks
    Databases
    Cloud
    CI/CD
    Monitoring
    Security tools

A powerful tool cannot compensate for fundamentally unclear ownership.

Likewise, a skilled team can still struggle when the process is chaotic.

Software engineering is a system of interacting factors.
""")


# =============================================================================
# 96. SDLC ECONOMICS
# =============================================================================

def economics():
    section("96. Economics of Software Development")

    explain("""
Software decisions have economic consequences.

Important concepts include:

    Development cost
    Operating cost
    Maintenance cost
    Cost of delay
    Cost of defects
    Opportunity cost
    Technical debt
    Total cost of ownership

The cost of correcting a defect often increases when the defect remains
undetected for longer.

For example:

    Requirement stage:
        Cheap to change.

    Design stage:
        More expensive.

    Development:
        More expensive.

    Testing:
        More expensive.

    Production:
        Potentially much more expensive.

Production defects can create:

    Revenue loss
    Support costs
    Reputation damage
    Security incidents
    Regulatory consequences
    Customer churn
""")


# =============================================================================
# 97. SHIFT LEFT
# =============================================================================

def shift_left():
    section("97. Shift Left")

    explain("""
Shift left means moving quality and security activities earlier in the
lifecycle.

Traditional thinking:

    Requirements → Development → Testing → Security

Shift-left thinking:

    Requirements
         ↓
    Security + Quality
         ↓
    Design
         ↓
    Security + Quality
         ↓
    Development
         ↓
    Automated validation

Examples:

    Unit tests during development
    Security requirements during planning
    Threat modeling during architecture
    Static analysis during CI

The objective is earlier feedback.
""")


# =============================================================================
# 98. SHIFT RIGHT
# =============================================================================

def shift_right():
    section("98. Shift Right")

    explain("""
Shift right emphasizes learning from software after deployment.

Examples:

    Production monitoring
    Feature experiments
    Canary releases
    Real-user monitoring
    Incident analysis
    Feedback systems

Shift left and shift right complement each other.

Shift left improves prevention.

Shift right improves learning from real-world behavior.
""")


# =============================================================================
# 99. CONTINUOUS IMPROVEMENT
# =============================================================================

def continuous_improvement():
    section("99. Continuous Improvement")

    explain("""
SDLC processes should evolve.

Teams can inspect:

    What worked?
    What failed?
    Where did work wait?
    Where did defects originate?
    Where did deployment slow down?
    Which manual steps can be automated?
    Which controls provide value?
    Which controls create unnecessary friction?

Continuous improvement should be evidence-based.

The purpose is to improve the system of work, not merely to increase activity.
""")


# =============================================================================
# 100. SDLC KNOWLEDGE MAP
# =============================================================================

def knowledge_map():
    section("100. SDLC Knowledge Map")

    explain("""
The major relationships can be understood as follows:

BUSINESS
    ↓
Problem
    ↓
Objectives
    ↓
Requirements
    ↓
Prioritization
    ↓
Architecture
    ↓
Design
    ↓
Development
    ↓
Testing
    ↓
Release
    ↓
Deployment
    ↓
Operations
    ↓
Monitoring
    ↓
Feedback
    ↓
Maintenance
    ↓
Evolution
    ↓
Retirement

Across every stage:

    Security
    Quality
    Risk management
    Documentation
    Governance
    Change management
    Communication

The lifecycle is therefore not simply:

    Requirements → Code → Testing

It is a continuous system connecting business value, engineering decisions,
quality, security, operations, and user outcomes.
""")


# =============================================================================
# 101. IMPORTANT DISTINCTIONS
# =============================================================================

def important_distinctions():
    section("101. Important SDLC Distinctions")

    distinctions = [
        ("Requirement vs Design",
         "Requirement states what is needed; design explains how it will be achieved."),

        ("Verification vs Validation",
         "Verification checks whether the product is built correctly; validation checks whether the correct product is being built."),

        ("Severity vs Priority",
         "Severity describes impact; priority describes urgency."),

        ("Iteration vs Increment",
         "Iteration emphasizes refinement; increment emphasizes additional functionality."),

        ("QA vs Testing",
         "Testing is one quality activity; QA concerns the broader process of achieving quality."),

        ("Deployment vs Release",
         "Deployment moves software into an environment; release concerns making a version available under a controlled process."),

        ("Reliability vs Availability",
         "Reliability concerns correct operation over time; availability concerns operational accessibility."),

        ("Lead Time vs Cycle Time",
         "Lead time measures elapsed time across a broader flow; cycle time usually measures active work duration."),

        ("Agile vs Scrum",
         "Agile is a broader philosophy and family of approaches; Scrum is a specific framework."),

        ("DevOps vs CI/CD",
         "DevOps is broader than automation; CI/CD is a set of practices and pipelines supporting frequent integration and delivery.")
    ]

    for first, explanation in distinctions:
        print(f"\n{first}")
        print(f"  {explanation}")


# =============================================================================
# 102. PRACTICAL SDLC CHECKLIST
# =============================================================================

def checklist():
    section("102. Practical SDLC Checklist")

    checklist_items = [
        "Business objective defined",
        "Stakeholders identified",
        "Scope defined",
        "Requirements documented",
        "Requirements prioritized",
        "Acceptance criteria defined",
        "Feasibility assessed",
        "Risks identified",
        "Architecture designed",
        "Security requirements considered",
        "Data design completed",
        "API contracts defined",
        "Development standards established",
        "Version control configured",
        "Testing strategy defined",
        "Automated tests implemented",
        "Performance requirements validated",
        "Security testing performed",
        "Deployment strategy defined",
        "Rollback strategy defined",
        "Monitoring configured",
        "Logging configured",
        "Incident process established",
        "Documentation maintained",
        "Maintenance responsibilities assigned",
        "Retirement considerations documented"
    ]

    for index, item in enumerate(checklist_items, start=1):
        print(f"[ ] {index:02d}. {item}")


# =============================================================================
# 103. MINI SIMULATION
# =============================================================================

def lifecycle_simulation():
    section("103. SDLC Mini Simulation")

    project = {
        "Project": "Employee Leave Management System",
        "Phase": "Planning",
        "Status": "Initiated"
    }

    print("\nInitial Project State")
    for key, value in project.items():
        print(f"{key}: {value}")

    transitions = [
        ("Requirements", "Requirements approved"),
        ("Design", "Architecture approved"),
        ("Development", "Core functionality implemented"),
        ("Testing", "Critical test cases passed"),
        ("Staging", "Release candidate deployed"),
        ("Production", "Production deployment completed"),
        ("Operations", "Monitoring active"),
        ("Maintenance", "Continuous improvement underway")
    ]

    for phase, status in transitions:
        project["Phase"] = phase
        project["Status"] = status

        print(f"\nPhase: {phase}")
        print(f"Status: {status}")

    explain("""
The simulation illustrates a simplified sequential representation.

In an Agile/DevOps environment, the same project would repeatedly cycle
through requirements, design, development, testing, deployment, and feedback
for individual increments.
""")


# =============================================================================
# 104. ADVANCED SDLC PRINCIPLE
# =============================================================================

def advanced_principle():
    section("104. Advanced Principle: Feedback Loops")

    explain("""
One of the most important advanced ideas in modern SDLC is the feedback loop.

Traditional lifecycle thinking may appear linear:

    Requirement
        ↓
    Design
        ↓
    Code
        ↓
    Test
        ↓
    Deploy

Modern engineering recognizes many feedback loops:

    User feedback → Requirements
    Testing → Design
    Production monitoring → Architecture
    Incidents → Engineering practices
    Security findings → Development
    Performance data → Infrastructure
    Business metrics → Product priorities

The lifecycle is therefore better represented as a network of feedback loops
than as a simple straight line.

The earlier useful feedback is received, the earlier incorrect assumptions can
be corrected.
""")


# =============================================================================
# 105. ADVANCED PRINCIPLE: BLAST RADIUS
# =============================================================================

def blast_radius():
    section("105. Advanced Principle: Blast Radius")

    explain("""
Blast radius describes the extent of damage caused by a failure.

A deployment affecting:

    100% of users

has a larger blast radius than one affecting:

    1% of users.

Techniques that reduce blast radius include:

    Canary deployments
    Feature flags
    Isolation
    Rate limits
    Circuit breakers
    Independent services
    Gradual rollout
    Automated rollback

Reducing blast radius is a major reliability principle.
""")


# =============================================================================
# 106. ADVANCED PRINCIPLE: DEFENSE IN DEPTH
# =============================================================================

def defense_in_depth():
    section("106. Advanced Principle: Defense in Depth")

    explain("""
Defense in depth means using multiple independent layers of protection.

For example:

    Authentication
        +
    Authorization
        +
    Input validation
        +
    Encryption
        +
    Network controls
        +
    Monitoring
        +
    Audit logging

If one control fails, another may still reduce the impact.

This principle applies to security, reliability, and operational resilience.
""")


# =============================================================================
# 107. ADVANCED PRINCIPLE: AUTOMATION
# =============================================================================

def automation():
    section("107. Automation Across SDLC")

    explain("""
Automation can be applied throughout SDLC.

Requirements:
    Automated traceability and reporting

Development:
    Formatting
    Linting
    Static analysis

Testing:
    Unit tests
    Integration tests
    Regression tests

Security:
    Dependency scanning
    Secret detection
    Security testing

Build:
    Automated artifact creation

Deployment:
    Infrastructure automation
    Release pipelines

Operations:
    Monitoring
    Alerting
    Auto-scaling

Automation is most valuable when it makes a repeatable process reliable,
fast, and observable.
""")


# =============================================================================
# 108. FINAL INTEGRATED MODEL
# =============================================================================

def integrated_model():
    section("108. Integrated SDLC Model")

    explain("""
A mature software lifecycle can be represented as:

    BUSINESS NEED
          ↓
    PRODUCT OBJECTIVE
          ↓
    STAKEHOLDER ANALYSIS
          ↓
    REQUIREMENTS
          ↓
    FEASIBILITY + RISK
          ↓
    PRIORITIZATION
          ↓
    ARCHITECTURE
          ↓
    DESIGN
          ↓
    IMPLEMENTATION
          ↓
    AUTOMATED VALIDATION
          ↓
    SECURITY VALIDATION
          ↓
    ACCEPTANCE
          ↓
    RELEASE
          ↓
    DEPLOYMENT
          ↓
    OBSERVABILITY
          ↓
    OPERATIONS
          ↓
    INCIDENT RESPONSE
          ↓
    MAINTENANCE
          ↓
    CONTINUOUS IMPROVEMENT
          ↓
    RETIREMENT

Security, quality, risk, governance, documentation, and communication operate
across the lifecycle rather than belonging to only one phase.

The fundamental purpose of SDLC is controlled transformation:

    Need
      →
    Understanding
      →
    Design
      →
    Software
      →
    Validated Product
      →
    Operational Service
      →
    Evolving System

The lifecycle continues for as long as the software provides value.
""")


# =============================================================================
# 109. PROGRAM EXECUTION
# =============================================================================

def run_course():
    introduction()
    why_sdlc_exists()
    core_phases()
    project_vs_product()
    stakeholders()
    feasibility()
    requirements_engineering()
    user_stories()
    prioritization()
    traceability()
    scope_management()

    lifecycle_models()
    waterfall()
    v_model()
    iterative()
    incremental()
    spiral()
    prototyping()

    agile()
    scrum()
    agile_terminology()
    backlog()

    system_design()
    architecture_styles()
    architectural_tradeoffs()
    database_design()
    api_design()

    development()
    version_control()
    code_review()

    testing()
    testing_types()
    verification_validation()
    defect_management()
    quality_assurance()
    quality_attributes()

    security_sdlc()
    devsecops()
    devops()
    cicd()
    deployment_strategies()
    release_management()
    configuration_management()
    infrastructure_as_code()
    cloud()
    observability()
    incident_management()
    root_cause_analysis()

    maintenance()
    technical_debt()
    refactoring()

    risk_management()
    project_planning()
    estimation()
    dependency_management()
    documentation()
    change_management()
    configuration_items()
    metrics()
    lead_cycle_time()
    test_coverage()

    reliability()
    scalability()
    performance()
    privacy()
    compliance()
    environments()
    disaster_recovery()
    high_availability()
    failure_modes()

    agile_vs_waterfall()
    devops_vs_agile()
    sdlc_cicd()
    artifacts()
    baselines()
    governance()
    definition_of_done()
    definition_of_ready()
    quality_gates()

    build_release_deploy()
    feature_flags()
    blue_green()
    canary()
    rollback()
    database_migration()

    retirement()
    legacy_systems()
    strangler_pattern()

    banking_case_study()
    ecommerce_case_study()
    complete_flow()

    common_failures()
    decision_framework()
    maturity()
    people_process_technology()
    economics()
    shift_left()
    shift_right()
    continuous_improvement()

    knowledge_map()
    important_distinctions()
    checklist()
    lifecycle_simulation()
    advanced_principle()
    blast_radius()
    defense_in_depth()
    automation()
    integrated_model()


if __name__ == "__main__":
    print("\n" + "#" * 80)
    print("# SOFTWARE DEVELOPMENT LIFECYCLE - COMPLETE STUDY PROGRAM")
    print("#" * 80)
    print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    run_course()
    print("\n" + "#" * 80)
    print("# END OF SOFTWARE DEVELOPMENT LIFECYCLE STUDY PROGRAM")
    print("#" * 80)
