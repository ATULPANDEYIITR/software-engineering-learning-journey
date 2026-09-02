# Software Development Lifecycle

## Introduction

The Software Development Lifecycle, commonly known as SDLC, is a structured way of understanding how software moves from an initial business need to a working system and then through operation, maintenance, improvement, and eventual retirement.

The Python program studies SDLC as a complete engineering and product lifecycle rather than treating software development as only programming and testing.

The lifecycle connects business objectives, requirements, planning, architecture, design, development, testing, security, deployment, operations, maintenance, and retirement.

---

## Understanding SDLC

I learned that software development is not simply the process of writing code.

A software system normally begins with a problem, requirement, or business objective. That need is analyzed and converted into requirements. The requirements influence architecture and design. Design is implemented through software development. The resulting system is tested and validated before deployment.

Once deployed, the software becomes an operational system that must be monitored, maintained, secured, improved, and eventually retired.

A simplified lifecycle is:

**Business Need → Requirements → Design → Development → Testing → Deployment → Operations → Maintenance → Retirement**

Modern development processes can repeat these activities many times rather than performing them only once.

---

## Why SDLC Is Important

SDLC provides structure to software development.

Without an organized lifecycle, teams can experience problems such as unclear requirements, uncontrolled scope, poor architecture, insufficient testing, security weaknesses, deployment failures, and difficult maintenance.

SDLC helps organizations establish responsibility and control over important questions:

- What problem is being solved?
- Who are the users?
- What does the system need to do?
- What constraints exist?
- Is the solution technically and economically feasible?
- How should the system be designed?
- How will quality be measured?
- How will security be addressed?
- How will the software be deployed?
- How will production behavior be monitored?
- How will failures be handled?
- How will the software evolve?

SDLC therefore provides a framework for managing both technical and business uncertainty.

---

## Major SDLC Phases

The program covers the major phases of a software lifecycle.

### Planning

Planning establishes the problem, objectives, scope, stakeholders, resources, constraints, risks, and expected outcomes.

### Requirements Analysis

Requirements analysis identifies what the system should accomplish.

It includes understanding business requirements, user requirements, functional requirements, non-functional requirements, technical constraints, regulatory requirements, and acceptance criteria.

### System Design

System design determines how the requirements will be converted into a technical solution.

This can include architecture, databases, APIs, security, infrastructure, interfaces, data models, scalability, reliability, and integration decisions.

### Implementation

Implementation converts design decisions into working software.

Professional implementation includes source control, coding standards, testing, code review, dependency management, security, error handling, and documentation.

### Testing

Testing provides evidence that software behaves according to expected requirements.

Different forms of testing are used for different purposes, including unit testing, integration testing, system testing, acceptance testing, regression testing, performance testing, security testing, usability testing, and recovery testing.

### Deployment

Deployment moves software into an environment where it can be used.

Deployment strategies include rolling deployment, blue-green deployment, canary deployment, feature flags, and controlled releases.

### Operations

Once software reaches production, it needs continuous operational attention.

Operations include monitoring, logging, incident management, reliability management, capacity management, security, backup, and recovery.

### Maintenance

Maintenance includes correcting defects, adapting software to changing environments, improving functionality, improving performance, and reducing future problems.

### Retirement

Software eventually reaches the end of its useful life.

Retirement may involve user migration, data migration, infrastructure removal, access revocation, contract termination, data retention, and security cleanup.

---

## Software Project and Software Product

The program explains the distinction between a software project and a software product.

A project is generally temporary work performed to create a defined result.

A product continues to evolve and deliver value over time.

This distinction changes the way software success is measured.

Project thinking may focus on whether the planned work was completed.

Product thinking asks whether the resulting software continues to solve meaningful problems and provide value.

SDLC is therefore closely connected with product management and the broader product lifecycle.

---

## Stakeholders in SDLC

Software development involves many different roles.

The program covers the responsibilities of:

- Customers
- End users
- Product managers
- Project managers
- Business analysts
- Software architects
- Developers
- UI/UX designers
- QA engineers
- DevOps engineers
- Security engineers
- Database engineers
- Site reliability engineers
- Compliance teams
- Support teams

Software is a socio-technical system. Technical decisions interact with people, business processes, financial constraints, security requirements, regulations, and operational capabilities.

---

## Feasibility Analysis

Before committing significant resources, organizations may evaluate whether a software initiative is practical.

The program covers:

- Technical feasibility
- Economic feasibility
- Operational feasibility
- Legal feasibility
- Schedule feasibility
- Organizational feasibility

Economic evaluation can involve development cost, operating cost, expected benefits, return on investment, total cost of ownership, payback period, opportunity cost, and risk.

Feasibility analysis helps determine whether an idea is realistic before substantial development resources are consumed.

---

## Requirements Engineering

Requirements engineering is one of the most important parts of SDLC.

It involves:

- Discovering requirements
- Analyzing requirements
- Documenting requirements
- Validating requirements
- Prioritizing requirements
- Managing changes
- Maintaining traceability

### Functional Requirements

Functional requirements describe what the software should do.

Examples include:

- Creating an account
- Logging into a system
- Processing a payment
- Generating a report
- Approving a request

### Non-Functional Requirements

Non-functional requirements describe qualities or constraints.

Examples include:

- Response time
- Availability
- Security
- Scalability
- Reliability
- Usability
- Accessibility
- Maintainability

A statement such as "the application should be fast" is difficult to test.

A measurable requirement such as "95% of API requests should complete within 300 milliseconds under a specified load" provides a much clearer basis for validation.

---

## User Stories and Acceptance Criteria

The program introduces user stories as a common Agile way of expressing user needs.

A typical user story follows the structure:

> As a [type of user], I want [capability], so that [value].

Acceptance criteria then define the conditions that must be satisfied for the requirement to be considered acceptable.

Acceptance criteria make requirements more precise and easier to test.

---

## Requirements Prioritization

Not every requirement has equal importance.

The program introduces the MoSCoW prioritization technique:

- Must have
- Should have
- Could have
- Won't have in the current release

Other prioritization approaches include:

- Value versus effort
- RICE
- WSJF
- Cost of delay
- Kano analysis
- Risk-based prioritization
- Business impact analysis

Prioritization helps teams focus limited resources on the most important outcomes.

---

## Requirements Traceability

Requirements traceability connects requirements with other software artifacts.

A requirement may be linked to:

**Business Objective → Requirement → Design → Implementation → Test → Release**

Traceability helps determine whether requirements were implemented and tested.

It is particularly important in regulated, safety-critical, and highly controlled environments.

---

## Scope Management

Scope defines what belongs within a project or product release.

The program explains scope creep and why uncontrolled additions can create problems with:

- Cost
- Schedule
- Resources
- Architecture
- Security
- Quality
- Dependencies

A change should be evaluated according to its broader impact rather than simply being treated as a small feature request.

---

# SDLC Models

Different organizations organize SDLC activities differently.

The program covers:

- Waterfall
- V-Model
- Iterative development
- Incremental development
- Spiral Model
- Prototyping
- Agile
- DevOps-oriented development
- Hybrid approaches

---

## Waterfall Model

Waterfall organizes software development into relatively sequential phases.

A typical flow is:

**Requirements → Design → Implementation → Testing → Deployment → Maintenance**

It can work well when requirements are stable and predictable.

Its major limitations arise when requirements change frequently or when important assumptions are not validated until late in the lifecycle.

---

## V-Model

The V-Model emphasizes the relationship between development and testing.

Requirements are associated with acceptance testing, system design with system testing, architecture with integration testing, and detailed design with lower-level testing.

The central principle is that validation planning should occur alongside development rather than being postponed until the end.

---

## Iterative Development

Iterative development uses repeated cycles.

A team:

1. Builds something.
2. Evaluates it.
3. Learns from the result.
4. Improves the solution.
5. Repeats the process.

This is useful when requirements or technical solutions are uncertain.

---

## Incremental Development

Incremental development delivers functionality in pieces.

For example, a product might first deliver authentication, then profile management, then payments, and then reporting.

An incremental process focuses on adding functional capability over multiple releases.

---

## Spiral Model

The Spiral Model combines iterative development with explicit risk analysis.

Each cycle can include:

- Defining objectives
- Identifying alternatives
- Analyzing risks
- Developing and validating
- Reviewing results
- Planning the next cycle

The model is particularly relevant when technical or business risks are significant.

---

## Prototyping

A prototype is an experimental representation of a proposed system.

Prototypes may be:

- Paper prototypes
- UI mockups
- Clickable designs
- Proofs of concept
- Technical prototypes
- Working prototypes

A prototype is primarily used to reduce uncertainty.

Prototype code should not automatically be treated as production-quality software because it may lack proper security, testing, scalability, maintainability, and operational controls.

---

# Agile Development

Agile emphasizes:

- Individuals and interactions
- Working software
- Customer collaboration
- Responding to change

Agile does not mean that planning, documentation, requirements, architecture, or testing are unnecessary.

Instead, these activities are performed in a more adaptive and continuous way.

Agile development commonly involves:

- Short iterations
- Frequent feedback
- Prioritized backlogs
- Incremental delivery
- Cross-functional teams
- Continuous refinement
- Retrospectives

---

## Scrum

Scrum is an Agile framework.

The program covers:

- Product Owner
- Scrum Master
- Developers
- Product Backlog
- Sprint Backlog
- Increment
- Sprint Planning
- Daily Scrum
- Sprint Review
- Sprint Retrospective

A sprint provides a fixed period during which the team works toward producing a usable increment.

---

## Agile Terminology

The program explains several important Agile concepts:

- Epic
- Feature
- User Story
- Task
- Acceptance Criteria
- Definition of Done
- Backlog
- Velocity
- Retrospective
- Refinement

These concepts help organize and manage incremental development.

---

# System Design

System design translates requirements into a technical structure.

Important design areas include:

- Application architecture
- Database architecture
- API design
- Component boundaries
- Data models
- Authentication
- Authorization
- Caching
- Logging
- Monitoring
- Error handling
- Security
- Scalability
- Reliability
- Deployment architecture

Architecture should be driven by actual requirements and constraints.

There is no universally best architecture.

---

## Architectural Styles

The program covers several architectural approaches:

- Monolithic architecture
- Layered architecture
- Client-server architecture
- Microservices
- Event-driven architecture
- Serverless architecture
- Hexagonal architecture
- Clean Architecture

Each architecture involves trade-offs.

A microservice architecture is not automatically superior to a monolithic architecture.

For a relatively simple product, a modular monolith may provide lower complexity and easier operation.

---

## Architectural Trade-Offs

Architecture involves balancing competing qualities.

Examples include:

- Consistency versus availability
- Simplicity versus flexibility
- Performance versus maintainability
- Cost versus redundancy
- Centralization versus autonomy
- Development speed versus technical debt

Architecture should be appropriate for the actual scale, risk, complexity, and requirements of the system.

---

# Database Design

Database design includes:

- Entities
- Attributes
- Relationships
- Primary keys
- Foreign keys
- Constraints
- Indexes
- Transactions
- Normalization
- Denormalization
- Replication
- Backup
- Recovery
- Partitioning

Normalization reduces unnecessary duplication.

Indexes can improve read performance but can also increase storage and write costs.

Database decisions therefore involve trade-offs between correctness, performance, scalability, and maintainability.

---

# API Design

An API defines how software components communicate.

An API can define:

- Endpoints
- HTTP methods
- Request formats
- Response formats
- Authentication
- Authorization
- Validation
- Error handling
- Pagination
- Rate limiting
- Versioning

API contracts are important interfaces between systems and should be designed carefully.

---

# Software Development

Implementation is the stage where design and requirements become working software.

Professional development involves much more than writing source code.

Important practices include:

- Version control
- Coding standards
- Code review
- Branch management
- Dependency management
- Configuration management
- Error handling
- Logging
- Testing
- Security
- Documentation
- Refactoring

---

# Version Control

Version control allows teams to maintain a history of changes.

Git-based workflows commonly involve:

**Working Directory → Staging → Commit → Remote Repository → Pull Request → Review → Merge**

Version control provides:

- History
- Collaboration
- Branching
- Reverting
- Auditing
- Parallel development

---

# Code Review

Code review provides a structured examination of source code.

Reviews can evaluate:

- Correctness
- Readability
- Security
- Performance
- Maintainability
- Error handling
- Testing
- Architectural consistency

Code review is also a mechanism for knowledge sharing and maintaining engineering standards.

---

# Software Testing

Testing provides evidence about whether software behaves as expected.

Testing does not prove that a system contains no defects. It provides a systematic method for finding problems and validating expected behavior.

Important testing levels include:

- Unit testing
- Integration testing
- System testing
- Acceptance testing

---

## Types of Testing

The program covers:

- Functional testing
- Regression testing
- Smoke testing
- Sanity testing
- Performance testing
- Load testing
- Stress testing
- Security testing
- Usability testing
- Accessibility testing
- Compatibility testing
- Recovery testing
- Exploratory testing

Different testing types answer different questions.

---

## Verification and Validation

Verification asks:

**Are we building the product correctly?**

Examples include:

- Code review
- Static analysis
- Design review
- Requirement inspection

Validation asks:

**Are we building the correct product?**

Examples include:

- User acceptance testing
- Usability evaluation
- Product demonstrations
- Real-world validation

Both are necessary.

---

# Defect Management

A defect is an identified problem in software.

The program distinguishes between severity and priority.

**Severity** describes the impact of the problem.

**Priority** describes how urgently the organization wants it addressed.

A high-severity problem does not necessarily have the same priority as another high-severity problem because business context can affect urgency.

---

# Quality Assurance

Quality Assurance focuses on improving the processes used to produce software.

Quality Control focuses more directly on evaluating the resulting product.

Testing is one part of quality engineering, while quality assurance has a broader process-oriented focus.

---

# Software Quality Attributes

The program covers important quality characteristics including:

- Correctness
- Reliability
- Availability
- Performance
- Scalability
- Security
- Usability
- Accessibility
- Maintainability
- Testability
- Portability
- Interoperability
- Observability
- Recoverability

Software quality is multidimensional.

A system can be functionally correct while still failing because it is insecure, unreliable, unavailable, slow, or difficult to maintain.

---

# Security and Secure SDLC

Security should be considered throughout the lifecycle.

Security-related activities can occur during:

- Requirements
- Architecture
- Design
- Development
- Testing
- Deployment
- Operations
- Maintenance

Important security areas include:

- Authentication
- Authorization
- Encryption
- Input validation
- Secure sessions
- Secrets management
- Audit logging
- Dependency management
- Vulnerability management
- Secure configuration
- Incident response

---

# Threat Modeling

Threat modeling is performed to identify potential security risks before they become production problems.

Questions include:

- What assets are being protected?
- Who might attack the system?
- What are the attack surfaces?
- What could an attacker accomplish?
- Which controls reduce the risk?

Finding a security weakness during architecture is usually preferable to discovering the same weakness after deployment.

---

# DevSecOps

DevSecOps integrates security into development and operations.

Automated security activities can include:

- Static application security testing
- Dependency scanning
- Secret detection
- Container scanning
- Infrastructure-as-code scanning
- Dynamic application security testing

The objective is continuous security validation rather than a single final security review.

---

# DevOps

DevOps connects software development and operations through:

- Collaboration
- Automation
- Continuous feedback
- Shared responsibility
- Reliable delivery
- Operational visibility

A simplified DevOps lifecycle is:

**Plan → Code → Build → Test → Release → Deploy → Operate → Monitor → Feedback**

DevOps is broader than simply using a CI/CD tool.

---

# CI/CD

Continuous Integration involves frequently integrating code changes and automatically validating them.

A CI pipeline may perform:

- Dependency installation
- Formatting
- Linting
- Unit testing
- Building
- Security scanning
- Integration testing

Continuous Delivery keeps software in a releasable condition.

Continuous Deployment automatically deploys validated changes to production.

CI/CD therefore automates repeatable portions of the SDLC.

---

# Deployment Strategies

The program covers:

- Big Bang deployment
- Rolling deployment
- Blue-green deployment
- Canary deployment
- Feature flags

Deployment strategy should reflect system risk.

A critical system may require gradual rollout, extensive monitoring, and reliable rollback.

---

# Release Management

Release management controls how a software version becomes available.

Activities can include:

- Version identification
- Release notes
- Change approval
- Deployment planning
- Dependency validation
- Rollback planning
- Stakeholder communication
- Post-release verification

A controlled release process allows teams to understand exactly what has changed and how the release can be recovered if problems occur.

---

# Configuration Management

Configuration management controls settings and environments.

Examples include:

- Environment variables
- Feature flags
- Database settings
- Service endpoints
- Infrastructure definitions
- Dependency versions

Sensitive credentials should not be embedded directly into source code.

---

# Infrastructure as Code

Infrastructure as Code represents infrastructure through machine-readable definitions.

Infrastructure can include:

- Networks
- Servers
- Databases
- Load balancers
- Storage
- Permissions

Infrastructure as Code improves:

- Reproducibility
- Version control
- Automation
- Auditability
- Consistency

---

# Cloud and SDLC

Cloud computing provides services such as:

- Compute
- Storage
- Databases
- Networking
- Containers
- Serverless functions
- Queues
- Monitoring
- Identity management

Cloud changes the available infrastructure options but does not remove the need for architecture.

Cloud systems still require decisions about:

- Security
- Cost
- Availability
- Scalability
- Performance
- Data residency
- Disaster recovery
- Vendor dependency

---

# Observability

Observability allows engineers to understand system behavior through external signals.

Three major signals are:

- Logs
- Metrics
- Traces

Logs provide detailed events.

Metrics provide numerical measurements.

Traces show how requests move through distributed components.

Important operational measurements can include:

- Error rate
- Latency
- Throughput
- CPU usage
- Memory usage
- Queue depth
- Database performance
- Availability

---

# Incident Management

An incident disrupts or threatens normal service.

A typical incident lifecycle includes:

**Detection → Triage → Classification → Investigation → Mitigation → Recovery → Communication → Root-Cause Analysis → Corrective Actions**

During a serious incident, restoring service is usually the immediate priority.

Understanding the underlying cause is necessary for long-term improvement.

---

# Root-Cause Analysis

Root-cause analysis attempts to identify why an incident or defect occurred.

The Five Whys technique can repeatedly ask why a failure happened until deeper process, architecture, or organizational causes become visible.

The purpose is not to assign blame.

The purpose is to understand the conditions that allowed the failure to happen and identify ways to prevent recurrence.

---

# Software Maintenance

Maintenance includes four broad categories:

### Corrective Maintenance

Fixing defects.

### Adaptive Maintenance

Adapting software to changes in its environment, platform, regulations, or dependencies.

### Perfective Maintenance

Improving functionality, usability, or performance.

### Preventive Maintenance

Reducing the probability of future problems.

Maintenance is a major part of the software lifecycle because software continues to change after its original release.

---

# Technical Debt

Technical debt represents future cost caused by shortcuts, deferred work, or suboptimal technical decisions.

Examples include:

- Duplicated code
- Outdated dependencies
- Missing tests
- Poor architecture
- Manual deployments
- Weak documentation
- Inconsistent configuration

Technical debt is not always accidental.

A deliberate shortcut can be reasonable when used to reduce uncertainty or validate a product idea.

The problem occurs when technical debt is ignored and its carrying cost grows.

---

# Refactoring

Refactoring improves internal software structure without intentionally changing externally observable behavior.

Examples include:

- Extracting functions
- Removing duplication
- Simplifying logic
- Renaming unclear variables
- Splitting large classes
- Improving module boundaries

Automated tests provide confidence when refactoring changes internal implementation.

---

# Risk Management

Software projects face many risks.

Examples include:

- Requirement changes
- Technical uncertainty
- Security threats
- Dependency failures
- Vendor lock-in
- Skill shortages
- Schedule pressure
- Budget limitations
- Integration failures
- Performance problems
- Regulatory changes
- Data quality issues

A simple risk exposure calculation is:

**Risk Exposure = Probability × Impact**

More sophisticated risk analysis can also consider detectability, uncertainty, time horizon, dependencies, secondary effects, and mitigation cost.

---

# Project Planning

Planning determines how work will be organized.

Important planning areas include:

- Scope
- Deliverables
- Work breakdown
- Dependencies
- Resources
- Schedule
- Budget
- Risk
- Quality
- Communication
- Governance

A Work Breakdown Structure decomposes large objectives into smaller manageable units.

---

# Software Estimation

Software estimation is difficult because software contains uncertainty.

Common approaches include:

- Expert judgment
- Analogous estimation
- Parametric estimation
- Three-point estimation
- Story points
- Function points
- Use-case points

Three-point estimation uses:

- Optimistic estimate
- Most likely estimate
- Pessimistic estimate

A commonly used expected-value calculation is:

**E = (O + 4M + P) / 6**

Estimates are forecasts, not guarantees.

---

# Dependency Management

Modern software relies heavily on external dependencies.

Dependencies may include:

- Libraries
- Frameworks
- APIs
- Cloud services
- Databases
- Operating systems
- Infrastructure

Dependencies create risks such as:

- Vulnerabilities
- Breaking changes
- License issues
- Abandonment
- Availability problems
- Version conflicts

Dependency management is therefore part of SDLC and software maintenance.

---

# Documentation

Documentation preserves technical and organizational knowledge.

Important documentation may include:

- Business requirements
- Product requirements
- Architecture diagrams
- API specifications
- Database documentation
- Deployment procedures
- Runbooks
- Test plans
- Security documentation
- Release notes
- Incident reports
- Decision records
- Retirement plans

Architecture Decision Records can capture the context, decision, alternatives, and consequences of important technical choices.

---

# Change Management

Software changes continuously because of:

- User needs
- Business strategy
- Regulations
- Security findings
- Technology changes
- Market conditions
- Incidents

A change should be evaluated according to its effect on:

- Scope
- Cost
- Schedule
- Architecture
- Security
- Quality
- Dependencies
- Operations

---

# Software Metrics

Metrics provide information about software delivery and system behavior.

The program covers:

- Lead time
- Cycle time
- Deployment frequency
- Change failure rate
- Time to restore service
- Defect density
- Test coverage
- Availability
- Error rate
- Latency
- Customer satisfaction
- Escaped defects

Metrics must be interpreted in context.

Optimizing a metric without understanding the underlying system can create undesirable behavior.

---

# DORA-Style Metrics

The program introduces commonly used DevOps delivery metrics:

- Deployment frequency
- Lead time for changes
- Change failure rate
- Time to restore service

These metrics help evaluate delivery performance and operational recovery.

They should be used to understand the system of work rather than simply to create pressure to increase numerical performance.

---

# Lead Time and Cycle Time

Lead time measures the elapsed period from a defined starting point to delivery.

Cycle time generally focuses on the period during which work is actively being performed.

Understanding the difference helps teams identify waiting time and process bottlenecks.

---

# Test Coverage

Test coverage measures how much of the software or behavior is exercised by tests.

Forms of coverage include:

- Statement coverage
- Branch coverage
- Function coverage
- Condition coverage

High coverage does not automatically mean high-quality testing.

Coverage is an indicator, not proof that software is correct.

---

# Reliability and Availability

Reliability concerns correct operation over time.

Availability concerns how often a service is operational and accessible.

A simplified availability calculation is:

**Availability = Uptime / (Uptime + Downtime)**

For example, 99.9% availability corresponds to approximately 8.76 hours of downtime per year under a simple 365-day calculation.

Availability requirements should therefore be connected to actual business needs.

---

# Scalability

Scalability is the ability of a system to handle increased demand.

Vertical scaling increases the resources available to an existing system.

Horizontal scaling increases the number of system instances.

Other scalability mechanisms include:

- Caching
- Replication
- Partitioning
- Queues
- Asynchronous processing
- Load balancing
- Content delivery networks

Scalability should be based on actual bottlenecks rather than assumptions.

---

# Performance Engineering

Performance engineering covers:

- Latency
- Throughput
- Response time
- Resource utilization
- Concurrency

Performance requirements should be measurable.

Performance optimization should rely on measurement and profiling rather than assumptions.

---

# Privacy

Privacy must be considered during system design.

Important questions include:

- What personal data is collected?
- Why is it collected?
- How long is it retained?
- Who can access it?
- Where is it stored?
- Is it protected?
- Can users modify or delete it?

Privacy is therefore an architectural and lifecycle concern.

---

# Compliance and Governance

Software can be affected by legal, regulatory, security, financial, and organizational requirements.

Compliance requirements can influence:

- Architecture
- Access management
- Logging
- Testing
- Documentation
- Data storage
- Change management
- Deployment
- Security controls

Governance defines how important technical and business decisions are controlled.

---

# Software Environments

Common environments include:

- Development
- Testing
- Integration
- Staging
- Production

Each environment serves a different purpose.

Staging is often used to validate release candidates under conditions similar to production.

Differences between environments can create deployment problems, so configuration and infrastructure should be controlled and reproducible.

---

# Backup and Disaster Recovery

Production systems need recovery capabilities.

Important concepts include:

- Backup
- Restore
- Replication
- Failover
- Disaster recovery
- Business continuity

Two important objectives are:

**RPO: Recovery Point Objective**

Defines the amount of data loss that can be tolerated.

**RTO: Recovery Time Objective**

Defines how quickly service should be restored.

These objectives influence architecture, backup frequency, replication, and operational processes.

---

# High Availability

High availability uses redundancy and failure-handling mechanisms to reduce service interruption.

Possible mechanisms include:

- Multiple application instances
- Load balancing
- Database replication
- Failover
- Health checks
- Redundant infrastructure

High availability increases complexity and cost, so it should be aligned with business requirements.

---

# Failure Analysis

Software can fail because of:

- Application crashes
- Database failures
- Network failures
- Dependency outages
- Authentication problems
- Capacity exhaustion
- Data corruption
- Configuration errors
- Deployment errors

Failure analysis helps teams understand failure modes and establish appropriate controls.

---

# Agile and Waterfall

The program compares Agile and Waterfall across:

- Requirements
- Delivery
- Feedback
- Change
- Planning
- Testing
- Risk

Waterfall generally relies more heavily on sequential planning and defined stages.

Agile emphasizes short feedback cycles and adaptive planning.

Neither should be treated as universally correct.

The appropriate approach depends on the nature of the system, requirements, risks, regulatory constraints, organizational structure, and customer feedback needs.

---

# Agile and DevOps

Agile primarily emphasizes adaptive product development and frequent delivery.

DevOps extends the lifecycle into deployment and operations.

They are complementary.

Agile helps teams build and deliver software incrementally.

DevOps helps teams build, deliver, operate, monitor, and improve software continuously.

---

# SDLC and CI/CD

CI/CD automates repeatable portions of the SDLC.

A pipeline can connect:

**Code → Build → Test → Security Validation → Artifact → Deployment → Monitoring**

CI/CD does not replace requirements engineering, architecture, product management, user research, or operational planning.

It automates suitable repeatable engineering processes.

---

# SDLC Artifacts

The program covers many artifacts that may exist throughout the lifecycle:

- Business case
- Project charter
- Requirements
- User stories
- Acceptance criteria
- Product backlog
- Architecture diagrams
- Architecture decision records
- Database schemas
- API specifications
- Source code
- Build artifacts
- Test plans
- Test cases
- Defect reports
- Security assessments
- Deployment configurations
- Release notes
- Runbooks
- Monitoring dashboards
- Incident reports
- Retirement plans

These artifacts provide evidence, traceability, knowledge, and operational control.

---

# Baselines

A baseline is an approved version of a set of artifacts used as a reference point.

Examples include:

- Requirements baseline
- Design baseline
- Release baseline

Baselines are particularly useful in environments requiring controlled changes and strong traceability.

---

# Quality Gates

A quality gate is a decision point requiring certain conditions to be satisfied before proceeding.

Examples include:

- Critical tests passed
- No unacceptable security vulnerabilities
- Code review completed
- Acceptance criteria satisfied
- Performance targets achieved
- Compliance evidence available

Quality gates should provide meaningful risk reduction without creating unnecessary bureaucracy.

---

# Build, Release, and Deployment

These concepts are related but different.

**Build** transforms source code into a deployable artifact.

**Release** concerns approving and preparing a version for distribution.

**Deployment** moves the version into an environment.

A mature pipeline can build one artifact and promote the same artifact through different environments.

---

# Feature Flags

Feature flags separate software deployment from feature activation.

Code can be deployed while a feature remains disabled.

Later, the feature can be activated for selected users or gradually rolled out.

Feature flags support:

- Canary releases
- Experiments
- Gradual rollout
- User segmentation
- Emergency feature disabling

Feature flags themselves should eventually be removed when they are no longer necessary.

---

# Blue-Green Deployment

Blue-green deployment maintains two environments.

One environment serves the current production version while the other contains the new version.

Traffic can be switched between the environments.

This can simplify rollback, although database changes and stateful components still need careful planning.

---

# Canary Deployment

Canary deployment exposes a new release to a small percentage of users.

For example:

**95% → Old Version**

**5% → New Version**

The new version can be evaluated using:

- Error rate
- Latency
- Crashes
- Business metrics
- User behavior

Traffic can be increased if the new version performs acceptably.

---

# Rollback

Rollback means returning to a previously known-good state.

Rollback planning must consider:

- Application code
- Database schema
- Data migrations
- Configuration
- External services
- Cached information

A code rollback may not be sufficient if database changes are incompatible with the previous application version.

---

# Database Migration

Database migration changes database structures or data.

A useful modernization pattern is:

**Expand → Migrate → Contract**

The system first introduces compatible structures, migrates data, and removes obsolete structures only after old software versions are no longer dependent on them.

This helps reduce compatibility problems during deployment.

---

# Software Retirement

Retirement is a legitimate SDLC phase.

A system can become a candidate for retirement because:

- Its business value has declined.
- A replacement system exists.
- Technology is obsolete.
- Maintenance has become too expensive.
- Security risks are unacceptable.
- Business or regulatory requirements have changed.

Retirement involves more than shutting down infrastructure.

It can require:

- Data migration
- User migration
- Data retention
- Access revocation
- Infrastructure removal
- Contract termination
- Security cleanup
- Documentation

---

# Legacy Systems

Legacy systems are often business-critical systems built with older technologies or architectures.

Legacy systems can be difficult to modify because of:

- Tight coupling
- Missing documentation
- Old technology
- Lack of tests
- Fragile integrations
- Specialized knowledge

Possible strategies include:

- Maintain
- Refactor
- Replatform
- Rehost
- Replace
- Encapsulate
- Gradually modernize

Legacy does not automatically mean useless.

---

# Strangler Modernization

The Strangler approach gradually replaces portions of a legacy system.

Instead of replacing everything at once, new functionality is introduced around existing functionality.

Over time, more responsibilities move to the modern system.

This can reduce the risk of a large one-time rewrite.

---

# SDLC Case Studies

The Python program contains practical examples involving:

- Banking applications
- E-commerce platforms
- Employee leave-management systems

These examples demonstrate how requirements, architecture, development, testing, security, deployment, monitoring, maintenance, and retirement connect in real systems.

---

# Common SDLC Failures

Important failure patterns covered in the program include:

- Unclear requirements
- Poor scope management
- Architecture without clear requirements
- Late testing
- Lack of production monitoring
- Weak security
- Poor documentation
- Manual deployment
- Ignoring technical debt
- Lack of rollback planning
- Metrics without context

These problems demonstrate why SDLC must be treated as an interconnected system rather than a collection of isolated phases.

---

# Decision-Making in SDLC

Selecting an SDLC approach requires consideration of:

- Requirement stability
- Product uncertainty
- Technical risk
- Regulatory constraints
- Customer feedback
- Release frequency
- Organizational maturity
- Team structure
- System criticality
- Cost of failure

The process should fit the problem.

A highly regulated system may require strong traceability and formal verification.

A highly uncertain product may benefit from experimentation and iterative development.

A product requiring frequent releases may benefit from extensive automation and CI/CD.

---

# Engineering Maturity

The program presents a simplified maturity progression:

**Ad Hoc → Repeatable → Defined → Measured → Continuously Improved**

A mature engineering organization tends to have:

- Clear ownership
- Standard practices
- Automated validation
- Reproducible deployments
- Documented architecture
- Security controls
- Monitoring
- Measurable outcomes
- Continuous improvement

Maturity does not simply mean having more processes.

The objective is predictable delivery, controlled risk, and effective learning.

---

# People, Process, and Technology

SDLC performance depends on the interaction of:

**People + Process + Technology**

People contribute:

- Skills
- Communication
- Leadership
- Collaboration
- Ownership

Processes provide:

- Planning
- Requirements management
- Testing
- Change control
- Release management

Technology provides:

- Programming languages
- Frameworks
- Databases
- Cloud infrastructure
- CI/CD
- Monitoring
- Security tools

A strong technology stack cannot compensate for poor ownership or unclear requirements.

---

# Economics of Software Development

Software has economic consequences beyond the initial development cost.

Relevant concepts include:

- Development cost
- Operating cost
- Maintenance cost
- Cost of delay
- Cost of defects
- Opportunity cost
- Technical debt
- Total cost of ownership

Defects generally become more expensive to correct when they remain undetected for longer.

A defect found during requirements analysis may be relatively easy to correct.

The same incorrect assumption discovered in production can result in technical work, customer impact, support costs, revenue loss, reputational damage, and regulatory consequences.

---

# Shift Left

Shift left means moving quality and security activities earlier in the lifecycle.

Examples include:

- Security requirements during planning
- Threat modeling during architecture
- Unit testing during development
- Static analysis during development
- Automated security checks in CI

The objective is earlier feedback and earlier defect discovery.

---

# Shift Right

Shift right focuses on learning from software after deployment.

Examples include:

- Production monitoring
- Canary releases
- Feature experiments
- Real-user monitoring
- Incident analysis
- Operational feedback

Shift left emphasizes prevention.

Shift right emphasizes learning from real-world operation.

Both are part of modern software engineering.

---

# Continuous Improvement

Software lifecycle processes should evolve based on evidence.

Teams can examine:

- Where work waits
- Where defects originate
- Where deployments fail
- Which manual activities are repetitive
- Which controls reduce risk
- Which controls create unnecessary friction
- Which architectural decisions cause recurring problems

Continuous improvement focuses on improving the complete system of work rather than merely increasing activity.

---

# Important SDLC Distinctions

The program establishes several important distinctions.

### Requirement vs Design

A requirement explains what is needed.

A design explains how the requirement will be achieved.

### Verification vs Validation

Verification asks whether the product is being built correctly.

Validation asks whether the correct product is being built.

### Severity vs Priority

Severity describes impact.

Priority describes urgency.

### Iteration vs Increment

Iteration emphasizes repeated refinement.

Increment emphasizes adding functionality.

### QA vs Testing

Testing is a quality activity.

QA has a broader process-oriented focus.

### Deployment vs Release

Deployment moves software into an environment.

Release concerns making a version available through a controlled process.

### Reliability vs Availability

Reliability concerns correct operation over time.

Availability concerns operational accessibility.

### Lead Time vs Cycle Time

Lead time measures a broader elapsed period.

Cycle time generally measures active work.

### Agile vs Scrum

Agile is a broader family of approaches and principles.

Scrum is a specific framework.

### DevOps vs CI/CD

DevOps is a broader engineering and organizational approach.

CI/CD is a collection of practices and automation mechanisms that support frequent integration and delivery.

---

# Advanced SDLC Concepts

The program also covers several advanced engineering principles.

## Feedback Loops

Modern SDLC is not simply linear.

Feedback can move in many directions:

- User feedback can change requirements.
- Testing can influence design.
- Production monitoring can influence architecture.
- Security findings can influence development.
- Incidents can influence engineering practices.
- Business metrics can influence product priorities.

The lifecycle is therefore better understood as a system of feedback loops.

---

## Blast Radius

Blast radius describes how widely the effects of a failure spread.

A release affecting 1% of users has a smaller blast radius than one immediately affecting 100% of users.

Techniques for reducing blast radius include:

- Canary deployments
- Feature flags
- Isolation
- Rate limiting
- Circuit breakers
- Gradual rollout
- Automated rollback

---

## Defense in Depth

Defense in depth means using multiple layers of protection.

Security controls can include:

- Authentication
- Authorization
- Input validation
- Encryption
- Network controls
- Monitoring
- Audit logging

If one control fails, another may still reduce the impact.

---

## Automation

Automation can exist throughout SDLC.

Requirements can have automated reporting and traceability.

Development can use formatting and static analysis.

Testing can be automated.

Security can use automated scanning.

Builds can be automated.

Infrastructure can be created from code.

Deployments can be automated.

Operations can use automated monitoring and alerting.

Automation is particularly valuable for repeatable processes where consistency and speed matter.

---

# Complete SDLC Relationship

The major relationship studied in the program is:

**Business Need**

↓

**Product Objective**

↓

**Stakeholder Analysis**

↓

**Requirements**

↓

**Feasibility and Risk**

↓

**Prioritization**

↓

**Architecture**

↓

**Design**

↓

**Implementation**

↓

**Automated Validation**

↓

**Security Validation**

↓

**Acceptance**

↓

**Release**

↓

**Deployment**

↓

**Observability**

↓

**Operations**

↓

**Incident Response**

↓

**Maintenance**

↓

**Continuous Improvement**

↓

**Retirement**

Security, quality, risk management, documentation, governance, and communication operate across the lifecycle rather than belonging to only one phase.

The Software Development Lifecycle is therefore a complete system for transforming a need into software, validating that software, operating it reliably, managing its evolution, and eventually bringing it to the end of its useful life.
