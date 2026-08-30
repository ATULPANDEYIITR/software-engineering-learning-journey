# ============================================================
# DAY 01: SOFTWARE ENGINEERING FUNDAMENTALS
# ============================================================

print("DAY 01 - SOFTWARE ENGINEERING FUNDAMENTALS")


# ============================================================
# 1. WHAT IS SOFTWARE ENGINEERING?
# ============================================================

print("\n1. WHAT IS SOFTWARE ENGINEERING?")

print("Software Engineering is the systematic approach to")
print("designing, developing, testing, deploying, and maintaining")
print("software systems.")


# ============================================================
# 2. PROGRAMMING VS SOFTWARE ENGINEERING
# ============================================================

print("\n2. PROGRAMMING VS SOFTWARE ENGINEERING")

programming = "Writing code to solve a specific problem"

software_engineering = (
    "Applying structured processes to build, test, "
    "deploy, and maintain reliable software"
)

print("Programming:", programming)
print("Software Engineering:", software_engineering)


# ============================================================
# 3. SOFTWARE REQUIREMENTS
# ============================================================

print("\n3. SOFTWARE REQUIREMENTS")

requirements = [
    "User should be able to create an account",
    "User should be able to log in",
    "User should be able to view their profile",
    "System should securely store user data"
]

for requirement in requirements:
    print("-", requirement)


# ============================================================
# 4. FUNCTIONAL AND NON-FUNCTIONAL REQUIREMENTS
# ============================================================

print("\n4. FUNCTIONAL AND NON-FUNCTIONAL REQUIREMENTS")

functional_requirements = [
    "User login",
    "User registration",
    "Profile management"
]

non_functional_requirements = [
    "Security",
    "Performance",
    "Reliability",
    "Scalability"
]

print("Functional Requirements:")

for requirement in functional_requirements:
    print("-", requirement)

print("\nNon-Functional Requirements:")

for requirement in non_functional_requirements:
    print("-", requirement)


# ============================================================
# 5. SOFTWARE DEVELOPMENT LIFE CYCLE
# ============================================================

print("\n5. SOFTWARE DEVELOPMENT LIFE CYCLE")

sdlc = [
    "Requirements",
    "Planning",
    "Design",
    "Development",
    "Testing",
    "Deployment",
    "Maintenance"
]

for stage in sdlc:
    print("-", stage)


# ============================================================
# 6. BASIC SOFTWARE DESIGN
# ============================================================

print("\n6. BASIC SOFTWARE DESIGN")

components = {
    "User Interface": "Allows users to interact with the system",
    "Application Logic": "Processes business rules",
    "Database": "Stores application data",
    "API": "Enables communication between systems"
}

for component, purpose in components.items():
    print(component, "->", purpose)


# ============================================================
# 7. FUNCTIONS AND MODULARITY
# ============================================================

print("\n7. FUNCTIONS AND MODULARITY")


def calculate_total(price, quantity):
    return price * quantity


price = 500
quantity = 3

total = calculate_total(price, quantity)

print("Price:", price)
print("Quantity:", quantity)
print("Total:", total)

print("\nFunctions help divide software into smaller")
print("and reusable components.")


# ============================================================
# 8. ERROR HANDLING
# ============================================================

print("\n8. ERROR HANDLING")

try:
    number = int("100")
    print("Converted number:", number)

except ValueError:
    print("Invalid number")


# ============================================================
# 9. TESTING
# ============================================================

print("\n9. SOFTWARE TESTING")


def add(a, b):
    return a + b


expected = 10
actual = add(6, 4)

print("Expected:", expected)
print("Actual:", actual)

if actual == expected:
    print("Test Passed")
else:
    print("Test Failed")


# ============================================================
# 10. VERSION CONTROL
# ============================================================

print("\n10. VERSION CONTROL")

version_control = {
    "Repository": "software-project",
    "Branch": "main",
    "Version": "1.0"
}

for item, value in version_control.items():
    print(item + ":", value)

print("\nVersion control helps track changes to software.")


# ============================================================
# 11. DOCUMENTATION
# ============================================================

print("\n11. DOCUMENTATION")

documentation = [
    "Project README",
    "Code Comments",
    "API Documentation",
    "Setup Instructions"
]

for document in documentation:
    print("-", document)


# ============================================================
# 12. SOFTWARE QUALITY
# ============================================================

print("\n12. SOFTWARE QUALITY")

quality_attributes = [
    "Correctness",
    "Reliability",
    "Security",
    "Performance",
    "Maintainability",
    "Scalability",
    "Usability"
]

for attribute in quality_attributes:
    print("-", attribute)


# ============================================================
# 13. SOFTWARE ENGINEERING FLOW
# ============================================================

print("\n13. BASIC SOFTWARE ENGINEERING FLOW")

print("""
Requirements
     ↓
Planning
     ↓
Design
     ↓
Development
     ↓
Testing
     ↓
Deployment
     ↓
Maintenance
     ↓
Continuous Improvement
""")


# ============================================================
# SUMMARY
# ============================================================

print("=" * 60)
print("DAY 01 COMPLETED")
print("=" * 60)

print("""
Today you learned:

1. What Software Engineering is
2. Programming vs Software Engineering
3. Software Requirements
4. Functional and Non-Functional Requirements
5. SDLC
6. Basic Software Design
7. Functions and Modularity
8. Error Handling
9. Software Testing
10. Version Control
11. Documentation
12. Software Quality
13. Software Engineering Workflow
""")
