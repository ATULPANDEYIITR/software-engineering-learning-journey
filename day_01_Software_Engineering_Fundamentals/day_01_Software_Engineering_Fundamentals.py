# ============================================================
# SOFTWARE ENGINEERING FUNDAMENTALS
# ============================================================
#
# Topics Covered:
#
# 1. What is Software Engineering?
# 2. What is Software?
# 3. What is a Program?
# 4. Software vs Program
# 5. Why Software Engineering Exists
# 6. Software Engineering vs Just Coding
# 7. The Engineering Mindset
# 8. Requirements and Problem Understanding
# 9. Design Before Implementation
# 10. Reliability
# 11. Maintainability
# 12. Scalability
# 13. Security
# 14. Testing
# 15. Documentation
# 16. Version Control
# 17. Automation
# 18. Handling Failure
# 19. Technical Debt
# 20. Real-World Software Engineering Example
#
# ============================================================


print("=" * 70)
print("        SOFTWARE ENGINEERING FUNDAMENTALS")
print("=" * 70)


# ============================================================
# 1. WHAT IS SOFTWARE?
# ============================================================

print("\n1. WHAT IS SOFTWARE?")
print("-" * 70)

print("""
Software is a collection of instructions, programs, data, and
related components that tell a computer how to perform tasks.

In simple language:

Software = Instructions + Logic + Data + Supporting Components

Examples of software include:

- Web browsers
- Mobile applications
- Banking applications
- Operating systems
- Video games
- Database systems
- Cloud platforms
- AI applications
- Enterprise applications
- Hospital management systems
- Railway reservation systems

For example:

Google Chrome is software.

A banking application is software.

Windows is software.

A Python application is software.

Software is not a physical object like a keyboard or monitor.
It exists primarily as digital instructions and data.
""")

print("\nSimple example:")

name = "Atul"
age = 33

print("Name:", name)
print("Age:", age)

print("""
The variables above contain data.

The Python instructions that process this data are software
instructions.

Even this small Python file can be considered a very small
piece of software.
""")


# ============================================================
# 2. WHAT IS A PROGRAM?
# ============================================================

print("\n2. WHAT IS A PROGRAM?")
print("-" * 70)

print("""
A program is a set of instructions written to make a computer
perform a particular task.

For example, imagine we want a computer to calculate the
area of a rectangle.

The program could contain:

1. Get length.
2. Get width.
3. Multiply length by width.
4. Display the result.
""")

length = 10
width = 5

area = length * width

print("Length:", length)
print("Width:", width)
print("Area:", area)

print("""
This is a simple program.

It performs one specific task:

Calculate the area of a rectangle.

Programs can be extremely small or extremely large.
""")


# ============================================================
# 3. PROGRAM VS SOFTWARE
# ============================================================

print("\n3. SOFTWARE VS PROGRAM")
print("-" * 70)

print("""
A program and software are related concepts, but they are not
exactly the same.

A program is generally a set of instructions designed to
perform a task.

Software is a broader concept.

Software can contain:

- Programs
- Libraries
- Configuration
- Documentation
- Data
- User interfaces
- APIs
- Databases
- Deployment components
- Monitoring systems
- Supporting services
""")

print("\nThink about it like this:")

print("""
PROGRAM
    |
    +-- Instructions
    +-- Logic
    +-- Functions
    +-- Algorithms


SOFTWARE SYSTEM
    |
    +-- Programs
    +-- Database
    +-- APIs
    +-- Configuration
    +-- User Interface
    +-- Documentation
    +-- Tests
    +-- Deployment
    +-- Monitoring
""")

print("""
Therefore:

Program = A set of instructions.

Software = A broader system consisting of programs and
           supporting components.

A calculator program may be only a few lines of code.

A banking software platform may contain millions of lines
of code, databases, APIs, security systems, monitoring,
authentication, payment integrations, and many other
components.
""")


# ============================================================
# 4. A SIMPLE COMPARISON
# ============================================================

print("\n4. SIMPLE COMPARISON")
print("-" * 70)

comparison = {
    "Program": "Specific set of instructions",
    "Software": "Broader collection of programs and components",
    "Program example": "Calculator script",
    "Software example": "Banking platform",
    "Main purpose": "Perform a task",
    "System complexity": "Can be small or large"
}

for key, value in comparison.items():
    print(f"{key}: {value}")


# ============================================================
# 5. WHAT IS SOFTWARE ENGINEERING?
# ============================================================

print("\n5. WHAT IS SOFTWARE ENGINEERING?")
print("-" * 70)

print("""
Software Engineering is the systematic application of
engineering principles, processes, methods, tools, and
practices to the development, operation, maintenance, and
evolution of software.

In simpler words:

Software engineering is not just writing code.

It is the discipline of building software in a structured,
reliable, maintainable, secure, scalable, and repeatable way.

A software engineer thinks about the entire life of software.

That includes:

1. Understanding the problem
2. Gathering requirements
3. Designing the solution
4. Writing code
5. Testing
6. Debugging
7. Deploying
8. Monitoring
9. Maintaining
10. Improving
11. Securing
12. Scaling
""")

print("""
A useful mental model is:

Problem
   ↓
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
Monitoring
   ↓
Maintenance
   ↓
Improvement
""")


# ============================================================
# 6. CODING VS SOFTWARE ENGINEERING
# ============================================================

print("\n6. CODING VS SOFTWARE ENGINEERING")
print("-" * 70)

print("""
Coding means writing instructions that a computer can execute.

Software engineering includes coding, but goes far beyond it.

For example:

A programmer might ask:

    "How do I implement this feature?"

A software engineer may ask:

    "Why do we need this feature?"

    "Who will use it?"

    "What happens if it fails?"

    "How many users will use it?"

    "How will we test it?"

    "How will we secure it?"

    "How will another engineer maintain it?"

    "How will we deploy it?"

    "How will we monitor it?"

    "What happens when traffic increases?"

    "What happens when the database goes down?"

This difference is extremely important.
""")


# ============================================================
# 7. SIMPLE CODING EXAMPLE
# ============================================================

print("\n7. SIMPLE CODING EXAMPLE")
print("-" * 70)

print("A beginner might write:")

price = 1000
discount = 10

final_price = price - (price * discount / 100)

print("Final Price:", final_price)

print("""
The code works.

But a software engineer starts asking additional questions:

- What if price is negative?
- What if discount is greater than 100?
- What if price is not a number?
- Should the discount be represented as 10 or 0.10?
- Should currency be included?
- Should tax be calculated?
- How should the function be tested?
- Where should this logic live?
- How will this work for millions of transactions?
""")


# ============================================================
# 8. ENGINEERING MINDSET
# ============================================================

print("\n8. THE ENGINEERING MINDSET")
print("-" * 70)

print("""
The engineering mindset is one of the most important concepts
in software engineering.

An engineering mindset means thinking systematically about
problems instead of immediately jumping into implementation.

A beginner often thinks:

    "How can I write this code?"

An engineer thinks:

    "What problem are we solving?"

    "What constraints exist?"

    "What solution is appropriate?"

    "What can go wrong?"

    "How can we verify the solution?"

    "How can we maintain it?"

    "How can we improve it?"
""")


# ============================================================
# 9. PROBLEM SOLVING BEFORE CODING
# ============================================================

print("\n9. PROBLEM SOLVING BEFORE CODING")
print("-" * 70)

print("""
Imagine someone says:

    "Build me a food delivery application."

A beginner may immediately start coding.

An engineer first asks questions.

Who are the users?

Possible users:

- Customers
- Restaurants
- Delivery partners
- Administrators

What does the customer need?

- Search restaurants
- View menus
- Add food to cart
- Place orders
- Make payments
- Track deliveries

What does the restaurant need?

- Receive orders
- Accept/reject orders
- Update menu
- Update prices

What does the delivery partner need?

- Receive delivery requests
- Navigate to restaurant
- Pick up food
- Deliver food
- Update delivery status

This is engineering thinking.
""")


# ============================================================
# 10. REQUIREMENTS
# ============================================================

print("\n10. REQUIREMENTS")
print("-" * 70)

print("""
Before building software, engineers need to understand
requirements.

Requirements describe what the software should accomplish.

For example:

Requirement:

    "Users should be able to create an account."

This sounds simple.

But engineering questions immediately appear:

- What information is required?
- Is email required?
- Is phone number required?
- What makes a password valid?
- How is the password stored?
- How is the email verified?
- What happens if the email already exists?
- What happens if the database is unavailable?
- What happens if the user forgets the password?

The requirement must eventually become a well-defined
technical behavior.
""")


# ============================================================
# 11. DESIGN
# ============================================================

print("\n11. SOFTWARE DESIGN")
print("-" * 70)

print("""
Software design is the process of deciding how the system
will be structured.

For example, a simple application might contain:

User Interface
       |
       ↓
Application Logic
       |
       ↓
Database

A larger system might contain:

Client
   |
   ↓
API Gateway
   |
   +------ User Service
   |
   +------ Payment Service
   |
   +------ Order Service
   |
   +------ Notification Service
   |
   ↓
Databases
""")


# ============================================================
# 12. MODULARITY
# ============================================================

print("\n12. MODULARITY")
print("-" * 70)

print("""
Good software is often divided into smaller modules.

Instead of putting everything into one enormous function,
we separate responsibilities.
""")

def calculate_total(price, quantity):
    return price * quantity


def calculate_tax(amount, tax_rate):
    return amount * tax_rate / 100


def calculate_final_price(price, quantity, tax_rate):
    subtotal = calculate_total(price, quantity)
    tax = calculate_tax(subtotal, tax_rate)
    return subtotal + tax


price = 100
quantity = 3
tax_rate = 18

final_price = calculate_final_price(price, quantity, tax_rate)

print("Final price:", final_price)

print("""
This design separates responsibilities.

calculate_total()
    handles subtotal calculation.

calculate_tax()
    handles tax calculation.

calculate_final_price()
    combines the operations.

This makes the system easier to understand and test.
""")


# ============================================================
# 13. RELIABILITY
# ============================================================

print("\n13. RELIABILITY")
print("-" * 70)

print("""
Reliability means that software should perform correctly
and consistently under expected conditions.

Consider a banking system.

If a customer has:

    Account balance = 100000

and transfers:

    10000

the expected result is:

    New balance = 90000

But imagine the application crashes after deducting money
from one account but before adding it to the destination.

That creates a serious problem.

Software engineering therefore considers:

- Transactions
- Failure recovery
- Data consistency
- Error handling
- Backups
- Redundancy
- Monitoring
""")


# ============================================================
# 14. ERROR HANDLING
# ============================================================

print("\n14. ERROR HANDLING")
print("-" * 70)

print("""
Software engineers assume that things can fail.

For example:

- Users enter invalid data.
- Files may not exist.
- Networks may fail.
- Databases may become unavailable.
- APIs may return errors.
- Servers may crash.
- Services may become overloaded.
""")

try:
    number = int("ABC")
    print(number)

except ValueError:
    print("Error: Invalid number provided.")

print("""
Instead of allowing an unexpected error to crash the entire
application, we can handle known failure scenarios.
""")


# ============================================================
# 15. INPUT VALIDATION
# ============================================================

print("\n15. INPUT VALIDATION")
print("-" * 70)

print("""
Never blindly trust input.

Suppose an application asks for age.

Valid examples:

18
25
40

Invalid examples:

-5
"hello"
999999
""")

age = 25

if isinstance(age, int) and 0 <= age <= 120:
    print("Valid age:", age)
else:
    print("Invalid age")

print("""
Validation protects the application from unexpected data.
""")


# ============================================================
# 16. MAINTAINABILITY
# ============================================================

print("\n16. MAINTAINABILITY")
print("-" * 70)

print("""
Software is rarely written once and forgotten.

Real software changes.

Requirements change.

Businesses change.

Users change.

Technology changes.

Therefore software should be maintainable.

Maintainability means that engineers can understand,
modify, debug, and extend the software without excessive
difficulty.
""")


# ============================================================
# 17. BAD VS BETTER DESIGN
# ============================================================

print("\n17. BAD VS BETTER DESIGN")
print("-" * 70)

print("Hard-to-maintain example:")

x = 100
y = 5
z = x * y
print(z)

print("""
The code works, but variable names do not clearly explain
what x, y, and z represent.
""")

print("More readable design:")

price = 100
quantity = 5
total_cost = price * quantity

print("Total cost:", total_cost)

print("""
The second version communicates intent more clearly.

Readable code is an engineering concern.
""")


# ============================================================
# 18. SCALABILITY
# ============================================================

print("\n18. SCALABILITY")
print("-" * 70)

print("""
Scalability means the ability of a system to handle growth.

Imagine an application initially has:

    100 users

Later:

    10,000 users

Later:

    1,000,000 users

A system that works perfectly for 100 users may fail
under one million users.

Engineers therefore think about:

- CPU
- Memory
- Storage
- Database capacity
- Network traffic
- Caching
- Load balancing
- Horizontal scaling
- Vertical scaling
- Distributed systems
""")


# ============================================================
# 19. SECURITY
# ============================================================

print("\n19. SECURITY")
print("-" * 70)

print("""
Software engineering must consider security.

Examples include:

- Authentication
- Authorization
- Encryption
- Password protection
- Input validation
- Secure APIs
- Access control
- Logging
- Secrets management

For example, passwords should not simply be stored as
plain text.
""")

password = "MySecretPassword"

print("Password exists:", bool(password))

print("""
The example above only demonstrates the concept.

In a real system, passwords should be processed using
appropriate password hashing mechanisms and never stored
as plain text.
""")


# ============================================================
# 20. TESTING
# ============================================================

print("\n20. TESTING")
print("-" * 70)

print("""
Testing determines whether software behaves as expected.

Suppose we create a function that adds two numbers.
""")

def add(a, b):
    return a + b


print("2 + 3 =", add(2, 3))

print("10 + 20 =", add(10, 20))

print("""
An engineer does not simply assume that the function works.

We can define expected behavior.
""")

assert add(2, 3) == 5
assert add(10, 20) == 30
assert add(-1, 1) == 0

print("All basic tests passed.")

print("""
Testing gives us confidence that changes to the software
do not unintentionally break existing behavior.
""")


# ============================================================
# 21. UNIT TESTING CONCEPT
# ============================================================

print("\n21. UNIT TESTING")
print("-" * 70)

print("""
A unit test usually tests a small, isolated part of software.

For example:

    add(2, 3)

Expected result:

    5

A larger application can contain thousands or millions
of automated tests.

Different levels of testing can include:

- Unit testing
- Integration testing
- System testing
- End-to-end testing
- Performance testing
- Security testing
""")


# ============================================================
# 22. DOCUMENTATION
# ============================================================

print("\n22. DOCUMENTATION")
print("-" * 70)

print("""
Software engineering also involves documentation.

Documentation helps developers understand:

- What the system does
- How it works
- How to install it
- How to configure it
- How to use it
- How to troubleshoot it
- How APIs behave
- What design decisions were made
""")


# ============================================================
# 23. VERSION CONTROL
# ============================================================

print("\n23. VERSION CONTROL")
print("-" * 70)

print("""
Imagine five developers working on the same project.

Without version control, managing changes becomes difficult.

Version control systems such as Git allow developers to:

- Track changes
- Create branches
- Collaborate
- Review code
- Revert changes
- Investigate history
- Merge work

A typical workflow might look like:

Developer
    ↓
Create branch
    ↓
Write code
    ↓
Run tests
    ↓
Commit changes
    ↓
Push changes
    ↓
Code review
    ↓
Merge
""")


# ============================================================
# 24. AUTOMATION
# ============================================================

print("\n24. AUTOMATION")
print("-" * 70)

print("""
Engineers automate repetitive processes whenever practical.

For example, imagine a team must manually perform:

1. Download code
2. Install dependencies
3. Run tests
4. Build application
5. Package application
6. Deploy application

Every time this happens manually, human error is possible.

Automation can perform these steps consistently.

This eventually leads toward:

CI/CD
DevOps
Infrastructure as Code
Automated Testing
Automated Deployment
""")


# ============================================================
# 25. FAILURE IS EXPECTED
# ============================================================

print("\n25. FAILURE IS EXPECTED")
print("-" * 70)

print("""
One of the biggest differences between beginner thinking
and engineering thinking is the treatment of failure.

A beginner may think:

    "This code works."

An engineer thinks:

    "This code works under these conditions.
     What happens under other conditions?"

Possible failures:

- Empty input
- Invalid input
- Network failure
- Database failure
- Server failure
- Unexpected traffic
- Software bugs
- Hardware failure
- Configuration mistakes
- Human mistakes
""")


# ============================================================
# 26. DEFENSIVE THINKING
# ============================================================

print("\n26. DEFENSIVE THINKING")
print("-" * 70)

print("""
Defensive programming means anticipating incorrect,
unexpected, or malicious conditions.
""")

def divide_numbers(a, b):

    if b == 0:
        return "Cannot divide by zero."

    return a / b


print(divide_numbers(10, 2))
print(divide_numbers(10, 0))

print("""
The function explicitly handles a known failure condition.

This is part of engineering thinking.
""")


# ============================================================
# 27. TECHNICAL DEBT
# ============================================================

print("\n27. TECHNICAL DEBT")
print("-" * 70)

print("""
Technical debt occurs when a team chooses a quick or
suboptimal technical solution that creates additional
maintenance or improvement work later.

For example:

A developer thinks:

    "I'll write this quickly now.
     I'll clean it up later."

If this happens repeatedly, the codebase can become:

- Difficult to understand
- Difficult to modify
- Difficult to test
- Difficult to scale
- Difficult to debug

Technical debt is not always bad.

Sometimes businesses intentionally accept technical debt
to release something quickly.

The engineering challenge is managing it intelligently.
""")


# ============================================================
# 28. QUALITY ATTRIBUTES
# ============================================================

print("\n28. SOFTWARE QUALITY ATTRIBUTES")
print("-" * 70)

quality_attributes = [
    "Correctness",
    "Reliability",
    "Maintainability",
    "Scalability",
    "Security",
    "Performance",
    "Usability",
    "Availability",
    "Testability",
    "Portability"
]

for number, attribute in enumerate(quality_attributes, start=1):
    print(f"{number}. {attribute}")


# ============================================================
# 29. REAL-WORLD EXAMPLE
# ============================================================

print("\n29. REAL-WORLD EXAMPLE: BANKING APPLICATION")
print("-" * 70)

print("""
Imagine we need to build a banking application.

A beginner may think:

    "I need screens for balance, transfer and transactions."

A software engineer thinks about the entire ecosystem.

USER
 |
 ↓
Mobile/Web Application
 |
 ↓
Authentication
 |
 ↓
API
 |
 +------ Account Service
 |
 +------ Transaction Service
 |
 +------ Payment Service
 |
 +------ Notification Service
 |
 ↓
Database
 |
 ↓
Monitoring + Logging + Security

Now engineering questions appear.

What if the user enters the wrong password?

What if the database is unavailable?

What if two transactions happen simultaneously?

What if a payment request is duplicated?

What if the network disconnects?

What if the application receives one million requests?

What if someone attempts unauthorized access?

What if data is accidentally deleted?

What if a server crashes?

This is software engineering.
""")


# ============================================================
# 30. REQUIREMENT TO SOFTWARE
# ============================================================

print("\n30. FROM REQUIREMENT TO SOFTWARE")
print("-" * 70)

print("""
A professional software development process can be thought
of as a sequence of transformations.

BUSINESS PROBLEM
       ↓
REQUIREMENTS
       ↓
SYSTEM DESIGN
       ↓
ARCHITECTURE
       ↓
IMPLEMENTATION
       ↓
TESTING
       ↓
DEPLOYMENT
       ↓
MONITORING
       ↓
MAINTENANCE
       ↓
EVOLUTION
""")


# ============================================================
# 31. ENGINEERING TRADE-OFFS
# ============================================================

print("\n31. ENGINEERING TRADE-OFFS")
print("-" * 70)

print("""
There is rarely one perfect solution.

Engineers make trade-offs.

For example:

Solution A:

    Simple
    Cheap
    Easy to maintain
    Limited scalability

Solution B:

    Highly scalable
    More complex
    More expensive
    Requires specialized knowledge

Which one is better?

It depends on the problem.

For a small startup with 100 users, Solution A may be
perfectly reasonable.

For a global platform with hundreds of millions of users,
Solution B might be necessary.

Engineering is therefore about choosing an appropriate
solution based on requirements and constraints.
""")


# ============================================================
# 32. COST OF SOFTWARE
# ============================================================

print("\n32. SOFTWARE ENGINEERING IS ALSO ABOUT COST")
print("-" * 70)

print("""
Software has multiple costs.

Examples:

Development cost
Infrastructure cost
Maintenance cost
Testing cost
Security cost
Operational cost
Human cost
Downtime cost

An engineer must consider the complete lifecycle.

A solution that is cheap to build but extremely expensive
to operate may not be the best solution.

Likewise, an extremely sophisticated system may be wasteful
if the problem is simple.
""")


# ============================================================
# 33. ENGINEERING MINDSET QUESTIONS
# ============================================================

print("\n33. QUESTIONS AN ENGINEER SHOULD ASK")
print("-" * 70)

questions = [
    "What problem are we solving?",
    "Who are the users?",
    "What are the requirements?",
    "What are the constraints?",
    "What can fail?",
    "How should failure be handled?",
    "How will we test the system?",
    "How secure is the system?",
    "How will the system scale?",
    "How easy will it be to maintain?",
    "How will we monitor it?",
    "How will we deploy it?",
    "What happens when requirements change?",
    "What are the costs?",
    "What trade-offs are we making?"
]

for question in questions:
    print("->", question)


# ============================================================
# 34. SOFTWARE ENGINEERING LIFECYCLE
# ============================================================

print("\n34. SOFTWARE ENGINEERING LIFECYCLE")
print("-" * 70)

lifecycle = [
    "Problem Definition",
    "Requirements Analysis",
    "Planning",
    "System Design",
    "Architecture",
    "Implementation",
    "Testing",
    "Code Review",
    "Deployment",
    "Monitoring",
    "Maintenance",
    "Optimization",
    "Continuous Improvement"
]

for step_number, step in enumerate(lifecycle, start=1):
    print(f"{step_number}. {step}")


# ============================================================
# 35. SMALL ENGINEERING EXERCISE
# ============================================================

print("\n35. SMALL ENGINEERING EXERCISE")
print("-" * 70)

print("""
Suppose we need to build a simple temperature converter.

Requirement:

    Convert Celsius to Fahrenheit.

Mathematical formula:

    Fahrenheit = Celsius * 9 / 5 + 32
""")

def celsius_to_fahrenheit(celsius):

    if not isinstance(celsius, (int, float)):
        raise TypeError("Temperature must be numeric.")

    return celsius * 9 / 5 + 32


temperature = 25

fahrenheit = celsius_to_fahrenheit(temperature)

print("Celsius:", temperature)
print("Fahrenheit:", fahrenheit)

print("""
Notice that we did more than simply write the formula.

We also considered input validation.

That is a small example of engineering thinking.
""")


# ============================================================
# 36. SOFTWARE ENGINEERING MINDSET SUMMARY
# ============================================================

print("\n36. SOFTWARE ENGINEERING MINDSET SUMMARY")
print("-" * 70)

print("""
A strong software engineering mindset can be summarized as:

UNDERSTAND
    Understand the actual problem.

PLAN
    Think about requirements and constraints.

DESIGN
    Create an appropriate solution structure.

IMPLEMENT
    Write clean and understandable code.

TEST
    Verify that the software behaves correctly.

SECURE
    Protect the system and its data.

MONITOR
    Observe the system in production.

MAINTAIN
    Keep the software healthy over time.

SCALE
    Prepare the system for growth.

IMPROVE
    Continuously make the system better.
""")


# ============================================================
# 37. PROGRAMMER VS SOFTWARE ENGINEER
# ============================================================

print("\n37. PROGRAMMER VS SOFTWARE ENGINEER")
print("-" * 70)

print("""
PROGRAMMER

Primary focus:

    Writing code that performs a task.

Typical question:

    "How do I implement this?"

SOFTWARE ENGINEER

Broader focus:

    Building and maintaining reliable software systems.

Typical questions:

    "What problem are we solving?"

    "What architecture should we use?"

    "What can go wrong?"

    "How will we test it?"

    "How secure is it?"

    "How will it scale?"

    "How will another engineer maintain it?"

Neither role is simply about typing code.

The important difference is the breadth of responsibility
and engineering thinking applied to the software lifecycle.
""")


# ============================================================
# 38. FINAL CONCEPT
# ============================================================

print("\n38. THE CORE IDEA")
print("-" * 70)

print("""
Software engineering is ultimately about solving problems
with software in a disciplined and sustainable way.

Writing code is one part of the process.

The larger goal is to create software that is:

    Correct
    Reliable
    Secure
    Maintainable
    Testable
    Scalable
    Understandable
    Observable
    Adaptable

A program may simply work.

An engineered software system should continue to work,
be understandable, be maintainable, handle failures,
protect users, and evolve as requirements change.
""")


# ============================================================
# 39. FINAL TAKEAWAYS
# ============================================================

print("\n39. FINAL TAKEAWAYS")
print("-" * 70)

takeaways = [
    "Software is broader than a single program.",
    "A program is a set of instructions for performing tasks.",
    "Software engineering is much more than coding.",
    "Engineering begins with understanding the problem.",
    "Requirements should be understood before implementation.",
    "Design determines how software components work together.",
    "Good software should be maintainable.",
    "Reliable software must handle failure.",
    "Secure software protects data and users.",
    "Testing provides confidence in software behavior.",
    "Scalability becomes important as systems grow.",
    "Documentation helps people understand systems.",
    "Version control enables collaboration and history.",
    "Automation reduces repetitive manual work.",
    "Technical debt must be consciously managed.",
    "Engineers continuously consider trade-offs.",
    "Engineering is about building systems that can evolve."
]

for number, takeaway in enumerate(takeaways, start=1):
    print(f"{number}. {takeaway}")


# ============================================================
# END OF SOFTWARE ENGINEERING FUNDAMENTALS
# ============================================================

print("\n" + "=" * 70)
print("       SOFTWARE ENGINEERING FUNDAMENTALS COMPLETE")
print("=" * 70)

print("""
Remember:

    CODING
       ↓
    Writing instructions

    SOFTWARE DEVELOPMENT
       ↓
    Building software

    SOFTWARE ENGINEERING
       ↓
    Engineering software systems that solve real problems
    reliably, securely, maintainably, and at appropriate scale.

The transition from "I can write code" to
"I can engineer software" begins with this mindset.
""")
