from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FunctionalDependency:
    determinant: tuple[str, ...]
    dependent: tuple[str, ...]

    def is_partial(self, candidate_key: set[str]) -> bool:
        determinant = set(self.determinant)
        return (
            bool(determinant)
            and determinant < candidate_key
            and determinant != set(self.determinant)
        )


@dataclass
class Relation:
    name: str
    columns: list[str]
    primary_key: tuple[str, ...]
    rows: list[dict[str, Any]] = field(default_factory=list)
    foreign_keys: dict[str, tuple[str, str]] = field(default_factory=dict)

    def validate_columns(self) -> None:
        declared = set(self.columns)
        if len(declared) != len(self.columns):
            raise ValueError(f"{self.name}: duplicate column names")
        if not set(self.primary_key).issubset(declared):
            raise ValueError(f"{self.name}: primary key contains unknown columns")

    def validate_1nf(self) -> None:
        self.validate_columns()

        for row_number, row in enumerate(self.rows, start=1):
            if set(row) != set(self.columns):
                raise ValueError(
                    f"{self.name}: row {row_number} does not match relation columns"
                )

            for column, value in row.items():
                if isinstance(value, (list, tuple, set, dict)):
                    raise ValueError(
                        f"{self.name}: row {row_number}, column {column} "
                        "contains a non-atomic value"
                    )

        seen_keys: set[tuple[Any, ...]] = set()
        for row_number, row in enumerate(self.rows, start=1):
            key = tuple(row[column] for column in self.primary_key)
            if any(value is None for value in key):
                raise ValueError(
                    f"{self.name}: row {row_number} contains NULL in primary key"
                )
            if key in seen_keys:
                raise ValueError(f"{self.name}: duplicate primary key {key}")
            seen_keys.add(key)

    def validate_foreign_keys(self, referenced: dict[str, "Relation"]) -> None:
        for column, (table_name, referenced_column) in self.foreign_keys.items():
            if table_name not in referenced:
                raise ValueError(
                    f"{self.name}: referenced relation {table_name} does not exist"
                )

            target = referenced[table_name]
            target_values = {
                row[referenced_column] for row in target.rows
            }

            for row in self.rows:
                value = row[column]
                if value is not None and value not in target_values:
                    raise ValueError(
                        f"{self.name}: {column}={value!r} violates "
                        f"foreign key to {table_name}.{referenced_column}"
                    )


def project(rows: list[dict[str, Any]], columns: list[str]) -> list[dict[str, Any]]:
    return [{column: row[column] for column in columns} for row in rows]


def distinct(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    seen = set()

    for row in rows:
        key = tuple(sorted(row.items()))
        if key not in seen:
            seen.add(key)
            result.append(row)

    return result


def demonstrate_1nf() -> Relation:
    # A repeating phone-number group would violate 1NF:
    # {"customer_id": 1, "phones": ["111", "222"]}.
    # The atomic design stores one phone number per row.
    customer_phone = Relation(
        name="customer_phone",
        columns=["customer_id", "phone_number", "phone_type"],
        primary_key=("customer_id", "phone_number"),
        rows=[
            {
                "customer_id": 1,
                "phone_number": "9876543210",
                "phone_type": "mobile",
            },
            {
                "customer_id": 1,
                "phone_number": "0522123456",
                "phone_type": "office",
            },
            {
                "customer_id": 2,
                "phone_number": "9988776655",
                "phone_type": "mobile",
            },
        ],
    )

    customer_phone.validate_1nf()
    return customer_phone


def demonstrate_2nf() -> tuple[Relation, Relation]:
    # Original enrollment relation:
    #
    # enrollment(student_id, course_id, student_name, course_name, grade)
    #
    # Candidate key = (student_id, course_id).
    #
    # student_name depends only on student_id.
    # course_name depends only on course_id.
    # Those are partial dependencies, so the relation is not in 2NF.
    #
    # Decomposition removes the partial dependencies.
    students = Relation(
        name="student",
        columns=["student_id", "student_name"],
        primary_key=("student_id",),
        rows=[
            {"student_id": 101, "student_name": "Anika"},
            {"student_id": 102, "student_name": "Rohan"},
        ],
    )

    courses = Relation(
        name="course",
        columns=["course_id", "course_name"],
        primary_key=("course_id",),
        rows=[
            {"course_id": 501, "course_name": "Database Systems"},
            {"course_id": 502, "course_name": "Distributed Systems"},
        ],
    )

    enrollment = Relation(
        name="enrollment",
        columns=["student_id", "course_id", "grade"],
        primary_key=("student_id", "course_id"),
        rows=[
            {"student_id": 101, "course_id": 501, "grade": "A"},
            {"student_id": 101, "course_id": 502, "grade": "B+"},
            {"student_id": 102, "course_id": 501, "grade": "A-"},
        ],
        foreign_keys={
            "student_id": ("student", "student_id"),
            "course_id": ("course", "course_id"),
        },
    )

    for relation in (students, courses, enrollment):
        relation.validate_1nf()

    relations = {
        "student": students,
        "course": courses,
        "enrollment": enrollment,
    }
    enrollment.validate_foreign_keys(relations)

    return students, enrollment


def demonstrate_3nf() -> tuple[Relation, Relation]:
    # A typical transitive dependency:
    #
    # employee(employee_id, employee_name, department_id, department_name)
    #
    # employee_id -> department_id
    # department_id -> department_name
    # therefore employee_id -> department_name transitively.
    #
    # 3NF decomposition separates department attributes.
    department = Relation(
        name="department",
        columns=["department_id", "department_name"],
        primary_key=("department_id",),
        rows=[
            {"department_id": 10, "department_name": "Engineering"},
            {"department_id": 20, "department_name": "Finance"},
        ],
    )

    employee = Relation(
        name="employee",
        columns=["employee_id", "employee_name", "department_id"],
        primary_key=("employee_id",),
        rows=[
            {
                "employee_id": 1001,
                "employee_name": "Meera",
                "department_id": 10,
            },
            {
                "employee_id": 1002,
                "employee_name": "Kabir",
                "department_id": 20,
            },
        ],
        foreign_keys={"department_id": ("department", "department_id")},
    )

    for relation in (department, employee):
        relation.validate_1nf()

    relations = {
        "department": department,
        "employee": employee,
    }
    employee.validate_foreign_keys(relations)

    return department, employee


def demonstrate_denormalization() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    # Normalized order reporting requires a join between order and customer.
    customers = [
        {"customer_id": 1, "customer_name": "Nisha", "city": "Lucknow"},
        {"customer_id": 2, "customer_name": "Arjun", "city": "Delhi"},
    ]

    orders = [
        {"order_id": 9001, "customer_id": 1, "amount": 2500},
        {"order_id": 9002, "customer_id": 2, "amount": 1800},
    ]

    normalized_report = [
        {
            "order_id": order["order_id"],
            "customer_name": customer["customer_name"],
            "city": customer["city"],
            "amount": order["amount"],
        }
        for order in orders
        for customer in customers
        if order["customer_id"] == customer["customer_id"]
    ]

    # A deliberately denormalized reporting structure stores frequently
    # requested customer attributes beside the order. This reduces joins
    # for read-heavy reporting but introduces update-anomaly risk.
    denormalized_report = [
        {
            "order_id": 9001,
            "customer_id": 1,
            "customer_name": "Nisha",
            "customer_city": "Lucknow",
            "amount": 2500,
        },
        {
            "order_id": 9002,
            "customer_id": 2,
            "customer_name": "Arjun",
            "customer_city": "Delhi",
            "amount": 1800,
        },
    ]

    return normalized_report, denormalized_report


def demonstrate_anomaly_detection() -> None:
    # A deliberately duplicated customer value illustrates an update anomaly.
    bad_orders = [
        {
            "order_id": 1,
            "customer_id": 10,
            "customer_name": "Priya",
            "city": "Lucknow",
        },
        {
            "order_id": 2,
            "customer_id": 10,
            "customer_name": "Priya",
            "city": "Kanpur",
        },
    ]

    cities = {}
    for row in bad_orders:
        customer_id = row["customer_id"]
        city = row["city"]

        if customer_id in cities and cities[customer_id] != city:
            raise ValueError(
                "Update anomaly detected: one customer has conflicting "
                "duplicated city values"
            )

        cities[customer_id] = city


def print_relation(relation: Relation) -> None:
    print(f"\n{relation.name}")
    print("-" * len(relation.name))

    for row in relation.rows:
        print(row)


def main() -> None:
    print("DATABASE NORMALIZATION CASE STUDY")

    customer_phone = demonstrate_1nf()
    print_relation(customer_phone)

    students, enrollment = demonstrate_2nf()
    print_relation(students)
    print_relation(enrollment)

    department, employee = demonstrate_3nf()
    print_relation(department)
    print_relation(employee)

    normalized, denormalized = demonstrate_denormalization()

    print("\nNormalized reporting result")
    for row in normalized:
        print(row)

    print("\nDenormalized reporting result")
    for row in denormalized:
        print(row)

    try:
        demonstrate_anomaly_detection()
    except ValueError as exc:
        print(f"\nExpected anomaly check: {exc}")

    # Projection and duplicate elimination are useful relational operations
    # when demonstrating how normalized relations can be queried safely.
    projected = project(employee.rows, ["employee_id", "department_id"])
    print("\nEmployee department projection")
    print(distinct(projected))

    print("\nNormalization checks completed successfully.")
    print(
        "1NF: atomic values and unique rows\n"
        "2NF: no partial dependency on a composite key\n"
        "3NF: no non-key attribute depends transitively on a key\n"
        "Denormalization: intentional redundancy for a justified workload"
    )


if __name__ == "__main__":
    main()
