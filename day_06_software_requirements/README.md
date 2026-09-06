# Software Requirements: Functional and Non-Functional Requirements

## 1. Topic Introduction

Software requirements describe what a software system must provide, how it must behave, the quality characteristics it must achieve, and the constraints under which it must operate.

Requirements form the connection between business objectives and technical implementation. A business stakeholder may describe an objective such as reducing checkout abandonment. Users may express a need to purchase products easily. Software requirements translate those needs into statements that can be analyzed, designed, implemented, tested, and accepted.

Two fundamental categories are:

- **Functional requirements**: describe what the system must do.
- **Non-functional requirements**: describe qualities, performance characteristics, operational conditions, or constraints that the system must satisfy.

A complete requirements-engineering process does not stop at writing requirements. It includes elicitation, analysis, classification, prioritization, specification, validation, traceability, baseline management, change control, verification, and acceptance.

The accompanying Python script implements examples of these concepts rather than merely describing them.

---

## 2. What Is a Software Requirement?

A software requirement is a documented statement of a capability, behavior, quality, constraint, or condition that a software system must satisfy.

Examples include:

- The system shall allow a customer to create an account.
- The system shall authenticate registered users.
- The API shall respond within 500 ms for 95% of requests under a specified workload.
- Privileged accounts shall require multi-factor authentication.
- Production deployment shall use an approved hosting environment.

A requirement should describe an actual need or mandatory condition rather than an arbitrary implementation preference.

### Requirement Versus Design

The distinction between requirement and design is fundamental.

A requirement might state:

> The system shall allow customers to reset forgotten passwords.

A design decision might state:

> The application will use a particular database to store password-reset tokens.

The requirement specifies the expected capability. The design specifies one way to implement it.

A technology can legitimately appear in a requirement when it is itself a constraint. For example, an organization may require production systems to use an approved hosting platform.

---

## 3. Levels and Types of Requirements

Software requirements can exist at several levels.

### 3.1 Business Requirements

Business requirements describe organizational goals or desired outcomes.

Example:

> The business shall increase completed online purchases by 10% within the defined measurement period.

A business requirement usually focuses on **why** the initiative exists.

### 3.2 Stakeholder Requirements

Stakeholder requirements represent needs of particular stakeholder groups.

Stakeholders can include:

- Customers
- Employees
- Managers
- Administrators
- Security teams
- Operations teams
- Finance teams
- Regulators
- Business owners
- External partners

### 3.3 User Requirements

User requirements describe what users need to accomplish.

Example:

> A customer shall be able to view their previous orders.

User requirements are often expressed in user-oriented language.

### 3.4 System or Software Requirements

System requirements provide more precise statements about what the software must do or satisfy.

They can include functional behavior, quality requirements, interfaces, constraints, domain rules, and regulatory obligations.

### 3.5 Functional Requirements

Functional requirements specify system behavior and capabilities.

### 3.6 Non-Functional Requirements

Non-functional requirements specify qualities, measurable characteristics, operational conditions, or constraints.

### 3.7 Domain Requirements

Domain requirements originate from the business or technical domain in which the software operates.

For example, an e-commerce system may need to comply with tax rules. A banking application may have domain-specific transaction rules.

### 3.8 Constraints

Constraints restrict the solution space.

Examples:

- Use an approved hosting environment.
- Integrate with an existing payment provider.
- Follow a contractual technical standard.
- Comply with an applicable regulation.

### 3.9 Interface Requirements

Interface requirements specify interactions with:

- Other software systems
- APIs
- Hardware
- External services
- Human users
- Communication protocols

---

# 4. Functional Requirements

Functional requirements answer:

> **What must the system do?**

They describe observable behavior, capabilities, processing, workflows, business rules, data operations, and interactions.

Common categories include:

### Authentication

The system shall authenticate a registered customer using approved credentials.

### Authorization

The system shall prevent one customer from viewing another customer's private order information.

### Data Management

The system shall create, retrieve, update, and delete records according to defined permissions.

### Business Rules

The system shall apply a 10% discount when an eligible order exceeds the specified threshold.

### Workflow

The system shall change an order from `Pending` to `Paid` after successful payment confirmation.

### Search

The system shall return products matching the specified search criteria.

### Notifications

The system shall generate an order confirmation after successful payment.

### Reporting

The system shall allow authorized managers to export monthly sales data.

### Integration

The system shall send payment requests to the approved payment provider.

---

## 5. Functional Requirement Structure

A useful functional requirement often identifies:

1. Actor
2. Trigger or input
3. System behavior
4. Business rules
5. Observable result
6. Exception behavior where necessary

A useful general structure is:

> The system shall [perform action] when [condition or trigger], resulting in [observable outcome].

For example:

> The system shall allow an authenticated customer to add an available product to a cart.

The Python script demonstrates functional behavior through functions such as discount calculation and order quantity validation.

---

# 6. Non-Functional Requirements

Non-functional requirements answer questions such as:

- How fast?
- How secure?
- How available?
- How reliable?
- How scalable?
- How maintainable?
- How usable?
- Under what constraints?
- According to which compliance requirements?

They describe characteristics of the system rather than only individual capabilities.

Important categories include:

- Performance
- Availability
- Reliability
- Scalability
- Security
- Usability
- Accessibility
- Maintainability
- Compatibility
- Portability
- Recoverability
- Compliance

---

# 7. Why Non-Functional Requirements Must Be Measurable

A vague quality statement is difficult to verify.

Weak:

> The system shall be fast.

The word "fast" has no objective threshold.

Better:

> The product-search API shall return a response within 500 ms for at least 95% of requests under 200 requests per second.

The second requirement defines:

- Operation: product search
- Metric: response time
- Threshold: 500 ms
- Percentile: 95th percentile
- Workload: 200 requests per second

It can therefore be tested.

Another weak requirement is:

> The system shall be highly available.

A measurable alternative is:

> The production API shall achieve at least 99.95% monthly availability excluding approved maintenance windows.

The second statement allows monitoring data to determine whether the requirement was achieved.

---

# 8. Functional Versus Non-Functional Requirements

| Dimension | Functional Requirement | Non-Functional Requirement |
|---|---|---|
| Main question | What must the system do? | How well or under what constraint? |
| Focus | Behavior and capability | Quality, performance, constraint |
| Example | User can reset password | Reset operation completes within 2 seconds |
| Typical verification | Functional test | Performance, security, reliability, audit, or specialized testing |
| Scope | Often feature-specific | Can affect an entire system |
| Failure | Expected behavior is absent or incorrect | Required quality threshold is not achieved |

A single feature can have both.

Example:

**Functional**

> The system shall allow users to upload profile photographs.

**Non-functional**

> The profile-image service shall accept files up to 10 MB and complete processing within 3 seconds for 95% of valid uploads.

The functional requirement defines the capability. The non-functional requirement defines operational characteristics.

---

# 9. Requirement Quality Characteristics

Good requirements should generally be:

### Correct

The requirement represents the actual stakeholder need.

### Unambiguous

The statement should have one reasonable interpretation.

Avoid terms such as:

- Fast
- Easy
- Efficient
- Appropriate
- Reasonable
- Soon
- User-friendly
- Large
- Robust

unless these terms have been explicitly defined.

### Complete

A requirement should contain enough information to understand and verify it.

### Consistent

It should not contradict another requirement.

### Feasible

It should be technically, financially, legally, and operationally realistic.

### Necessary

There should be a valid reason for including it.

### Verifiable

There should be an objective way to determine whether it has been satisfied.

### Traceable

The requirement should be connected to its source, implementation, tests, and relevant business objectives.

### Prioritized

Its importance should be understood.

### Atomic

A requirement should express one coherent obligation instead of combining unrelated obligations.

### Understandable

The wording should be appropriate for its intended audience.

---

# 10. Requirement Statement Patterns

Different requirement types benefit from different structures.

### Functional

> The system shall [perform action] when [trigger/input], resulting in [observable outcome].

### Performance

> The system shall [perform operation] within [threshold] under [defined workload].

### Availability

> The service shall maintain at least [percentage] availability during [measurement period].

### Security

> The system shall [security behavior] for [scope] using [approved mechanism/control].

### Capacity

> The system shall support at least [quantity] users/requests/data while maintaining [quality threshold].

### Recovery

> The system shall restore [service/data] within [RTO] after [failure scenario] with no more than [RPO] data loss.

The exact structure should be adapted to the requirement rather than mechanically applied.

---

# 11. Requirements Elicitation

Requirements elicitation is the systematic discovery of stakeholder needs, expectations, constraints, business rules, assumptions, and operational conditions.

Common techniques include:

### Interviews

Useful for understanding detailed knowledge held by individual stakeholders.

### Workshops

Useful when multiple teams must reach a shared understanding.

### Observation

Useful when actual workflows differ from documented procedures.

### Surveys and Questionnaires

Useful when input is needed from a large population.

### Document Analysis

Useful when existing policies, contracts, procedures, specifications, or legacy documentation contain requirements.

### Prototyping

Useful for discovering interaction and usability requirements.

### Use Cases and Scenarios

Useful for understanding user goals and system responses.

### Interface Analysis

Useful when the system must communicate with other systems.

---

# 12. Stated Requirements Versus Actual Requirements

A stakeholder's first statement is not necessarily a complete requirement.

For example:

> "I need a dashboard."

This leaves many questions unanswered:

- Who uses the dashboard?
- What information is required?
- How frequently should it update?
- Which decisions depend on it?
- What permissions are required?
- What happens when source data is unavailable?
- Which historical period must be supported?
- What performance is expected?

Elicitation therefore involves clarification rather than merely recording stakeholder statements.

---

# 13. Acceptance Criteria

Acceptance criteria define observable conditions that must be satisfied for a requirement or feature to be accepted.

A common scenario structure is:

- **Given**: Initial state or precondition
- **When**: Action or event
- **Then**: Expected result

Example:

**Given:** the customer is authenticated.

**When:** the customer submits valid payment details.

**Then:** the order status becomes `Paid` and a confirmation is generated.

Acceptance criteria help connect requirements to testing.

---

# 14. Negative and Exception Requirements

Requirements should not describe only successful workflows.

Important exceptions can include:

- Invalid input
- Missing input
- Unauthorized access
- Duplicate requests
- Timeouts
- External service failures
- Concurrent operations
- Partial failures
- Boundary values
- Data inconsistencies
- Recovery after interruption

For example:

> The payment service shall not create a second charge when an identical payment request is retried using the same idempotency key.

This describes important behavior under retry conditions.

---

# 15. Edge Cases

The Python script demonstrates an order quantity rule:

- Values below 1 are rejected.
- 1 is accepted.
- 100 is accepted.
- Values above 100 are rejected.

Boundary testing is important because requirements frequently define ranges.

A requirement such as:

> The system shall support quantities from 1 to 100.

should lead to tests involving:

- 0
- 1
- 2
- 99
- 100
- 101

The boundaries often expose defects that normal cases do not.

---

# 16. MoSCoW Prioritization

MoSCoW provides four priority categories.

| Category | Meaning |
|---|---|
| Must | Essential for the agreed release or scope |
| Should | Important but not absolutely essential |
| Could | Desirable but lower priority |
| Won't | Explicitly excluded from the current scope |

Prioritization should consider:

- Business value
- User impact
- Regulatory necessity
- Security risk
- Risk reduction
- Cost
- Dependencies
- Feasibility
- Schedule
- Operational consequences

Priority should not be assigned solely based on which stakeholder asks most forcefully.

---

# 17. Risk and Value Prioritization

Requirements can also be evaluated through combinations of:

- Business value
- User impact
- Risk reduction
- Implementation cost

The Python script uses a simple illustrative score:

> `(business value + user impact + risk reduction) / implementation cost`

This is not a universal prioritization standard. It demonstrates how decision criteria can be represented programmatically.

Real projects may use more sophisticated prioritization methods involving weighted scoring, financial value, risk exposure, dependencies, regulatory requirements, or portfolio constraints.

---

# 18. Requirements Traceability

Traceability establishes relationships between requirements and other project artifacts.

A requirement may be connected to:

- Business objectives
- Stakeholders
- Design decisions
- Architecture components
- Implementation work
- Test cases
- Defects
- Change requests
- Regulatory evidence

A simplified traceability chain is:

> Business objective → Requirement → Design → Implementation → Test

Traceability supports:

- Impact analysis
- Change management
- Test coverage
- Auditability
- Regulatory compliance
- Completeness analysis
- Verification

Bidirectional traceability is particularly useful.

A forward relationship asks:

> Which requirement supports this business objective?

A backward relationship asks:

> Which business objective justifies this requirement?

---

# 19. Requirement Dependencies

Requirements can depend on one another.

For example:

1. The system creates an account.
2. The system authenticates the account.
3. The system displays private account information.

The second requirement depends on the first. The third depends on the second.

The Python script implements dependency-aware ordering using a topological sorting algorithm.

It also detects cycles.

For example:

> A depends on B  
> B depends on A

creates a dependency cycle that cannot be resolved into a simple implementation sequence.

Dependencies can also exist outside the requirement set, including dependencies on:

- External APIs
- Vendors
- Legal decisions
- Infrastructure
- Data sources
- Other teams
- Third-party identity providers

---

# 20. Performance Requirements

Performance requirements commonly involve:

- Latency
- Response time
- Throughput
- Requests per second
- Transactions per second
- Concurrent users
- Resource utilization
- Error rate

A good performance requirement identifies:

> Workload + environment + metric + threshold + measurement method

Example:

> The product-search API shall return responses within 500 ms for at least 95% of requests under 200 requests per second.

### Percentiles

The Python script demonstrates average, P95, and maximum response time.

Average latency alone can hide poor experiences for a subset of users.

Percentiles provide additional information about the distribution.

For example:

- P50 approximates the median
- P95 describes the threshold below which approximately 95% of observations fall
- P99 focuses on the high-latency tail

Performance requirements should specify the appropriate percentile rather than relying only on averages.

---

# 21. Availability

Availability describes the proportion of time a service is operational.

A simplified calculation is:

> Availability = Uptime / Total Measurement Time × 100

The Python script demonstrates availability calculations and the corresponding downtime allowed by different targets.

Examples:

- 99.0%
- 99.9%
- 99.95%
- 99.99%

Small differences in percentage can represent substantial differences in allowable downtime over a long period.

Availability is affected by:

- Redundancy
- Failover
- Monitoring
- Health checks
- Recovery procedures
- Infrastructure design
- Dependency availability
- Maintenance practices

---

# 22. Availability Versus Reliability

These concepts are related but not identical.

### Availability

Asks:

> Is the service operational when required?

### Reliability

Asks:

> Does the system perform correctly and consistently over time?

Two useful operational metrics are:

- **MTBF**: Mean Time Between Failures
- **MTTR**: Mean Time To Repair or Restore

A system can have high availability through rapid recovery even if failures occur relatively frequently.

---

# 23. Recovery Requirements

Recovery requirements describe behavior after failures.

Important concepts include:

### RTO

**Recovery Time Objective** specifies the targeted maximum time to restore service after a qualifying failure.

Example:

> Critical ordering capability shall be restored within 30 minutes.

### RPO

**Recovery Point Objective** specifies the maximum targeted amount of data loss measured in time.

Example:

> No more than five minutes of transaction data may be lost after a qualifying disaster.

Recovery requirements should be verified through actual recovery exercises rather than assumed to be satisfied merely because backup systems exist.

---

# 24. Scalability

Scalability is the ability of a system to handle changing workload.

### Vertical Scaling

Increasing resources available to an existing system component.

Examples include:

- More CPU
- More memory
- Faster storage

### Horizontal Scaling

Adding more instances or nodes.

A measurable scalability requirement could be:

> The order service shall support 5,000 requests per second while maintaining P95 latency below 500 ms.

The phrase "the system shall be scalable" is insufficient because it does not define workload or quality targets.

Scalability can introduce trade-offs involving:

- Cost
- Complexity
- Data partitioning
- Consistency
- Network traffic
- Coordination
- Operational effort

---

# 25. Security Requirements

Security requirements protect systems, users, data, and operations.

Important areas include:

### Authentication

Determines who the user or system actor is.

### Authorization

Determines what an authenticated actor is allowed to do.

### Confidentiality

Protects information from unauthorized disclosure.

### Integrity

Protects information from unauthorized modification.

### Accountability

Makes relevant actions attributable to users or systems.

### Auditability

Ensures important security events can be recorded and investigated.

The Python script demonstrates a basic password-policy validator for educational purposes.

A real authentication implementation requires much more, including secure password hashing, session protection, appropriate authentication controls, rate limiting, secure credential handling, and other protections.

---

# 26. Advanced Security Requirements

Security requirements should consider:

- Assets
- Threats
- Attack paths
- Trust boundaries
- Least privilege
- Defense in depth
- Secure failure
- Auditability
- Data minimization
- Secrets management
- Rate limiting
- Input validation
- Authentication
- Authorization
- Session security

Examples include:

> Privileged actions shall require multi-factor authentication.

> Sensitive personal data shall not be written to application logs.

> Authentication endpoints shall apply rate limiting after repeated failed attempts.

Security requirements should be connected to the system's actual threat model and applicable obligations.

---

# 27. Usability Requirements

Usability requirements should describe observable outcomes rather than subjective adjectives.

Weak:

> The interface shall be user-friendly.

Better:

> At least 90% of representative first-time users shall complete checkout without assistance during defined usability testing.

Other useful usability requirements can address:

- Task completion
- Error recovery
- Navigation
- Information clarity
- Form validation
- Feedback
- Learnability
- Consistency

---

# 28. Accessibility Requirements

Accessibility concerns whether people with different abilities can use the software effectively.

Requirements may address:

- Keyboard operation
- Focus behavior
- Alternative text
- Error communication
- Content presentation
- Assistive technology compatibility
- Input methods
- Navigation

Accessibility can be both a quality requirement and a compliance obligation depending on the application and applicable jurisdiction.

---

# 29. Maintainability

Maintainability concerns how easily a system can be:

- Modified
- Diagnosed
- Tested
- Repaired
- Extended
- Operated

Maintainability requirements may include measurable characteristics such as:

- Maximum acceptable change lead time
- Test coverage expectations
- Deployment constraints
- Static-analysis thresholds
- Documentation requirements
- Diagnostic logging requirements

"Easy to maintain" is not sufficiently precise unless "easy" is explicitly defined.

---

# 30. Compatibility and Portability

### Compatibility

Describes the ability of software to work with specified systems, platforms, interfaces, browsers, protocols, or environments.

### Portability

Describes the ability to move software between environments.

Weak:

> The application shall support all common browsers.

Better:

> The application shall support the specified browser versions listed in the approved compatibility matrix.

Requirements should identify the environment rather than using vague terms such as "common" or "modern."

---

# 31. Constraints

A constraint restricts the solution.

Examples:

- Production services shall use the approved hosting environment.
- The system shall integrate with the organization's existing identity provider.
- The application shall comply with a contractual interface specification.
- The system shall use a mandated communication protocol.

Constraints are different from ordinary functional behavior because they restrict how the solution may be constructed or operated.

---

# 32. Assumptions

An assumption is a condition treated as true for planning purposes.

Examples:

- Users have network connectivity.
- An external service remains available.
- Product catalog data is supplied daily.

Assumptions should not silently become requirements.

Important assumptions should be documented because a changed assumption can invalidate design decisions, estimates, or requirements.

---

# 33. Requirement Dependencies

A requirement can depend on:

- Another requirement
- An external API
- A vendor
- Infrastructure
- A business decision
- Regulatory interpretation
- Data availability
- Another team

Dependency tracking is particularly important when requirements are implemented in stages.

A dependency graph can reveal:

- Implementation ordering
- Blocking requirements
- Circular dependencies
- High-risk external dependencies

---

# 34. Conflicting Requirements

Requirements can conflict.

For example:

> The system shall store user information indefinitely.

versus:

> The system shall delete personal information after the applicable retention period expires.

Resolving such a conflict requires:

1. Identifying the conflict.
2. Determining the authority of each requirement.
3. Checking legal and regulatory constraints.
4. Understanding business objectives.
5. Analyzing technical consequences.
6. Negotiating a compatible rule.
7. Recording the decision.
8. Updating requirements and traceability.

Conflicts should be resolved explicitly rather than left for developers to interpret.

---

# 35. Common Requirement Defects

### Ambiguity

A statement has multiple reasonable interpretations.

Example:

> The system shall respond quickly.

### Incompleteness

Important conditions, actors, outputs, or exceptions are missing.

### Inconsistency

Two requirements cannot both be satisfied as written.

### Non-Verifiability

No objective test can establish satisfaction.

### Compound Requirements

Several independent obligations are combined into one sentence.

### Solution Bias

The requirement unnecessarily dictates implementation.

### Gold Plating

Capabilities are added without a justified requirement.

### Scope Leakage

Requirements expand beyond the agreed product boundary.

### Hidden Assumptions

The requirement depends on an unstated condition.

---

# 36. Requirements Validation

Validation asks whether the requirements represent the right needs and whether they are sufficiently complete and coherent.

A validation process should examine:

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

The Python script implements a lightweight validation function that checks for:

- Duplicate IDs
- Empty statements
- Missing acceptance criteria
- Unknown dependencies

These automated checks are useful but cannot replace expert review.

---

# 37. Verification Versus Validation

The distinction is important.

### Verification

Asks:

> Did we build the system according to the specified requirements?

Examples:

- Execute functional tests.
- Perform load tests.
- Review security controls.
- Inspect configurations.
- Perform recovery exercises.

### Validation

Asks:

> Did we specify and build the right thing for the actual need?

A system can technically satisfy a poorly written requirement and still fail to solve the business problem.

---

# 38. Requirements Traceability Matrix

A requirements traceability matrix can connect requirements to:

- Business objectives
- Design elements
- Test cases

For example:

| Requirement | Business Objective | Design | Test |
|---|---|---|---|
| FR-001 | OBJ-01 | DESIGN-AUTH | TC-LOGIN-001 |
| NFR-001 | OBJ-02 | DESIGN-CACHE | TC-PERF-001 |

Traceability provides evidence that important requirements have corresponding design and verification activities.

It also helps determine the impact of proposed changes.

---

# 39. Requirements Repository

The Python script includes an in-memory requirements repository demonstrating:

- Add
- Retrieve
- Update
- Delete
- Search
- Dependency protection

A production requirements-management system would normally require additional capabilities such as:

- Persistent storage
- Version control
- Access control
- Audit history
- Approval workflows
- Change history
- Traceability
- Search
- Reporting
- Integration with development and testing systems

The in-memory implementation is intended to demonstrate the underlying concepts.

---

# 40. Change Management

Requirements are subject to change because:

- Business priorities change.
- Regulations change.
- User expectations change.
- Technical constraints become clearer.
- Security threats evolve.
- External services change.
- Production evidence reveals missing requirements.

A controlled change process generally includes:

1. Change request
2. Reason
3. Impact analysis
4. Decision
5. Approval
6. Baseline update
7. Traceability update
8. Test and implementation updates

Change management does not attempt to prevent all change. It makes change visible and controlled.

---

# 41. Baselines and Versioning

A baseline is an approved version of requirements against which future changes can be controlled.

Versioning answers questions such as:

- What was approved?
- When was it approved?
- What changed?
- Who approved it?
- Which tests correspond to that version?

A baseline is particularly important in projects involving contracts, audits, regulated environments, or multiple development teams.

---

# 42. Requirement Verification Methods

Different requirements require different verification methods.

### Test

Execute the software and observe the result.

### Inspection

Review an artifact, configuration, or document.

### Analysis

Use calculations, models, static analysis, or other analytical techniques.

### Demonstration

Show the required behavior in a representative environment.

### Audit

Evaluate evidence against a policy, contract, or compliance requirement.

For example:

| Requirement | Suitable Verification |
|---|---|
| Login succeeds with valid credentials | Functional test |
| API P95 latency <= 500 ms | Load test |
| MFA required for administrators | Security test |
| Availability >= 99.95% | Monitoring analysis |
| Recovery <= 30 minutes | Recovery exercise |
| Approved hosting environment | Configuration inspection/audit |

---

# 43. Performance Measurement Considerations

Performance requirements are meaningful only when their measurement conditions are defined.

A statement such as:

> API response time must be less than 500 ms.

raises additional questions:

- At what load?
- Which endpoint?
- Which environment?
- Which request size?
- What percentage of requests?
- Does the measurement include network time?
- What monitoring system is authoritative?
- Are cache hits and misses included?
- What is the test duration?

Good performance requirements make these conditions explicit enough to support repeatable verification.

---

# 44. Production Considerations

Requirements should remain connected to production operations.

Before implementation:

- Identify objectives.
- Identify stakeholders.
- Define scope.
- Define constraints.
- Identify dependencies.
- Establish priorities.
- Define acceptance criteria.

During implementation:

- Maintain traceability.
- Control requirement changes.
- Review assumptions.
- Test edge cases.
- Keep acceptance criteria synchronized.

During testing:

- Test functional behavior.
- Test negative scenarios.
- Test boundaries.
- Test security controls.
- Test performance under representative workloads.
- Test recovery behavior.

Before release:

- Confirm mandatory requirements.
- Review compliance requirements.
- Verify monitoring.
- Confirm operational readiness.
- Confirm rollback and recovery procedures.

After release:

- Monitor NFRs.
- Compare production behavior with requirements.
- Analyze incidents.
- Capture newly discovered requirements.
- Control subsequent changes.

---

# 45. Requirements and Architecture Trade-Offs

Non-functional requirements frequently interact with one another.

Examples:

### Caching

Can improve:

- Latency
- Throughput
- Backend load

But can introduce:

- Stale data
- Cache invalidation complexity
- Additional operational components

### Multi-Region Deployment

Can improve:

- Availability
- Geographic resilience

But can increase:

- Cost
- Operational complexity
- Consistency challenges

### Stronger Authentication

Can improve:

- Security

But can introduce:

- User friction
- Additional operational complexity

Requirements engineering therefore needs to consider interactions among quality attributes rather than evaluating each requirement in isolation.

---

# 46. Requirement Metrics

Possible requirements metrics include:

- Requirements volatility
- Percentage with acceptance criteria
- Requirements test coverage
- Traceability coverage
- Number of open requirement defects
- Number of ambiguous requirements
- Requirement approval rate
- Change request count
- Rework rate
- Percentage with identified source

Metrics should be interpreted carefully.

A high percentage of requirements with acceptance criteria does not necessarily mean that the requirements are correct. A project can optimize a metric while still failing to satisfy its actual business objectives.

---

# 47. Requirements in an E-Commerce System

The Python script constructs a miniature e-commerce requirements set containing:

### Business

> The business shall increase completed online purchases by 10% within the defined measurement period.

### Functional

> The system shall allow a customer to create an account.

> The system shall authenticate a registered customer.

> The system shall allow an authenticated customer to add an available product to a cart.

> The system shall calculate the order total using product prices, quantity, discounts, taxes, and shipping charges.

> The system shall submit a payment request to the approved payment provider.

### Performance

> The product-search API shall return responses within 500 ms for at least 95% of requests under 200 requests per second.

### Availability

> The production API shall achieve at least 99.95% monthly availability excluding approved maintenance windows.

### Security

> The system shall require multi-factor authentication for privileged administrative accounts.

### Recovery

> The service shall restore critical ordering capability within 30 minutes after a qualifying production failure.

### Constraint

> Production deployment shall use the organization's approved hosting environment.

### Domain

> Tax calculation shall comply with applicable jurisdiction-specific tax rules.

This combination illustrates why real systems require more than functional feature descriptions.

---

# 48. Requirement Versus Design Versus Implementation Versus Test

These layers should not be confused.

| Layer | Example |
|---|---|
| Business requirement | Reduce failed online purchases |
| Functional requirement | Customer can retry a failed payment |
| Non-functional requirement | Payment retry receives an outcome within 2 seconds for 95% of requests |
| Design | Use an idempotency key and payment-service adapter |
| Implementation | Code that stores and validates idempotency keys |
| Test | Submit the same payment twice and verify only one charge occurs |

The requirement specifies the expected outcome. Design and implementation describe how the outcome is achieved.

---

# 49. Requirements Engineering Lifecycle

A disciplined lifecycle can be represented as:

1. Identify business objectives.
2. Identify stakeholders.
3. Elicit needs and constraints.
4. Analyze and classify requirements.
5. Resolve ambiguity and conflicts.
6. Prioritize requirements.
7. Specify requirements precisely.
8. Define acceptance and verification criteria.
9. Validate requirements.
10. Baseline approved requirements.
11. Trace requirements through design and testing.
12. Control changes.
13. Verify implementation.
14. Validate business outcomes.

The process is iterative rather than strictly linear.

New requirements or changes can arise from prototypes, technical analysis, security reviews, user testing, legal reviews, production incidents, market changes, and external dependencies.

---

# 50. Advanced Requirement Completeness

A requirement can be technically valid while still being insufficiently complete.

Useful review questions include:

- Is the requirement uniquely identified?
- Is the source known?
- Is the actor known?
- Is the expected behavior clear?
- Is the trigger known?
- Are inputs defined?
- Are outputs defined?
- Are important exceptions addressed?
- Is the requirement measurable?
- Is acceptance criteria defined?
- Is the verification method known?
- Are dependencies known?
- Is the rationale understood?
- Is the priority established?

The Python script implements a simple heuristic completeness score to demonstrate how structured review criteria can be represented programmatically.

Such a score is only a review aid. It cannot replace domain expertise.

---

# 51. Automated Requirement Checking

Natural-language requirements are difficult to validate automatically because meaning depends on context.

Automated checks can identify likely problems such as:

- Missing requirement IDs
- Empty statements
- Duplicate IDs
- Missing acceptance criteria
- Unknown dependencies
- Vague words
- Missing measurable signals
- Potential ambiguity

The Python script deliberately treats these as heuristics rather than proof.

For example, detecting the word "or" may identify possible ambiguity, but an "or" can be perfectly valid when the alternatives are explicitly defined.

Similarly, the presence of a number does not automatically make a requirement measurable.

---

# 52. Requirement Normalization

The script demonstrates basic whitespace normalization.

For example:

> The   system shall   allow   authenticated users   to   export reports.

can be normalized to:

> The system shall allow authenticated users to export reports.

Formatting normalization is relatively safe.

Semantic rewriting is much more dangerous because changing wording can accidentally alter:

- Scope
- Actors
- Timing
- Conditions
- Exceptions
- Thresholds
- Legal meaning

Automation should therefore be conservative when modifying requirement content.

---

# 53. Requirements-to-Test Mapping

Acceptance criteria create a direct bridge between requirements and test cases.

For example:

Requirement:

> The system shall allow a customer to update their email address.

Acceptance criteria may include:

- Valid email is accepted.
- Invalid email is rejected.
- Confirmation is generated after successful update.
- Unauthorized users cannot update another customer's email.

Each criterion can produce one or more test cases.

Testing should include:

- Positive cases
- Negative cases
- Boundary cases
- Authorization cases
- Failure cases
- Integration cases
- Performance cases where relevant

A requirement having one test case does not necessarily mean that it is fully covered.

---

# 54. Common Mistakes

## Mistake 1: Writing Only Functional Requirements

A team may describe every feature while ignoring:

- Performance
- Security
- Availability
- Recovery
- Accessibility
- Scalability
- Maintainability
- Compliance

This produces an incomplete specification.

## Mistake 2: Using Vague Quality Terms

Examples:

- Fast
- Secure
- Easy
- Efficient
- User-friendly
- Robust

These should be replaced by measurable or explicitly defined criteria.

## Mistake 3: Writing Implementation as a Requirement

Example:

> The system shall use a particular database.

This is only a requirement when the database choice is genuinely constrained.

Otherwise, the statement may prematurely prescribe design.

## Mistake 4: Ignoring Exceptions

A requirement that defines only the successful path may leave major failure behavior unspecified.

## Mistake 5: No Acceptance Criteria

Without acceptance criteria, teams may disagree about whether a requirement has been satisfied.

## Mistake 6: No Traceability

Untraceable requirements make impact analysis and test coverage difficult.

## Mistake 7: Uncontrolled Requirement Changes

Allowing requirements to change without recording impact can produce scope drift, inconsistent documentation, and incorrect tests.

---

# 55. Limitations of Requirements Engineering

Requirements cannot eliminate all uncertainty.

Some needs are difficult to express precisely because:

- Stakeholders may not know what they need initially.
- Business conditions can change.
- Technical feasibility may be uncertain.
- Users may discover needs through experimentation.
- External systems may change.
- Regulations can evolve.
- Some quality attributes are difficult to measure directly.

Requirements engineering therefore combines structured documentation with iterative discovery, validation, negotiation, and change control.

---

# 56. Important Distinctions

| Concept | Meaning |
|---|---|
| Requirement | What must be satisfied |
| Design | How the requirement will be implemented |
| Specification | Structured documentation of requirements |
| Acceptance criterion | Observable condition for acceptance |
| Constraint | Restriction on the solution |
| Assumption | Condition treated as true |
| Dependency | Relationship requiring another element |
| Verification | Checking implementation against specification |
| Validation | Checking that the solution addresses the real need |
| Baseline | Approved version under change control |
| Traceability | Relationships among requirements and related artifacts |
| Functional | Capability or behavior |
| Non-functional | Quality, performance, operational condition, or constraint |

---

# 57. Quick Reference

| Term | Definition |
|---|---|
| Functional requirement | Specifies what the system must do |
| Non-functional requirement | Specifies quality, performance, operational condition, or constraint |
| Business requirement | Specifies an organizational goal or outcome |
| Stakeholder requirement | Specifies a stakeholder's need |
| User requirement | Specifies a user's need |
| Domain requirement | Originates from the application domain |
| Constraint | Restricts the solution |
| Acceptance criterion | Defines an observable condition for acceptance |
| Elicitation | Discovery of needs and constraints |
| Traceability | Linking requirements to related artifacts |
| Baseline | Approved version of requirements |
| RTO | Targeted time to restore service |
| RPO | Targeted maximum data-loss interval |
| Latency | Time taken to respond or complete an operation |
| Throughput | Work processed per unit time |
| Availability | Proportion of time a service is operational |
| Reliability | Ability to operate correctly and consistently |
| Scalability | Ability to handle changing workload |
| Maintainability | Ease of modifying, diagnosing, testing, and operating software |

---

# 58. Python Script Coverage

The Python script provides executable demonstrations of:

- Software requirement fundamentals
- Requirement classification
- Functional requirements
- Non-functional requirements
- Functional versus non-functional comparisons
- Requirement quality checks
- Requirement statement patterns
- Requirements elicitation concepts
- Acceptance criteria
- MoSCoW prioritization
- Value/risk prioritization
- Requirements traceability
- Requirement dependency graphs
- Dependency-cycle detection
- Performance measurements
- Percentiles
- Availability calculations
- Reliability concepts
- Security requirements
- Password-policy validation
- Usability requirements
- Accessibility requirements
- Scalability requirements
- Constraints and assumptions
- Requirement conflicts
- Ambiguity detection
- Edge-case handling
- Requirement repositories
- Requirement change management
- Baselines and versioning
- Verification methods
- Requirement-set validation
- E-commerce requirements
- Requirement metrics
- Production considerations
- Requirement/design/implementation/test distinctions
- Requirements lifecycle
- Quality-attribute trade-offs
- Requirement normalization
- Requirement-to-test mapping
- Advanced security considerations
- Requirement completeness heuristics
- Automated self-tests

The script uses only Python's standard library and is designed to execute as a single standalone study program.
