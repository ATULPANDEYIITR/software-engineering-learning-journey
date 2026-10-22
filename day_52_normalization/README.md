# Database Normalization: 1NF, 2NF, 3NF, and Denormalization

## Scope

This project models relational database normalization through four distinct design concerns:

| Area | Primary concern | Main design objective |
|---|---|---|
| 1NF | Atomic attributes and row identity | Remove repeating or multivalued attributes |
| 2NF | Partial functional dependencies | Ensure non-key attributes depend on the complete candidate key |
| 3NF | Transitive functional dependencies | Ensure non-key attributes do not depend on other non-key attributes |
| Denormalization | Intentional redundancy | Improve selected read workloads while controlling consistency risk |

The implementations use a common relational scenario involving customers, orders, students, courses, enrollments, employees, and departments. The examples distinguish structural normalization from deliberate redundancy for reporting.

A useful dependency progression is:

`1NF → atomic facts`

`2NF → complete-key dependency`

`3NF → direct dependency on the key`

`Denormalization → controlled redundancy for a measured workload`

## Functional Dependencies

A functional dependency `X → Y` means that the value of attribute set `X` determines the value of attribute set `Y`.

For example:

`customer_id → customer_name, city`

means that a customer identifier determines the customer's name and city.

For an enrollment relation with the candidate key `(student_id, course_id)`:

`student_id, course_id → grade`

is a dependency on the complete composite key.

If the same relation also contains:

`student_id → student_name`

then `student_name` depends on only part of the composite key. That is a partial dependency and is incompatible with the intended 2NF decomposition.

A 3NF example is:

`employee_id → department_id`

and

`department_id → department_name`

This creates the transitive dependency:

`employee_id → department_id → department_name`

The department fact therefore belongs in a separate department relation.

## First Normal Form

First Normal Form requires attributes to contain atomic values rather than repeating groups or unstructured collections inside a single relational attribute.

An unsuitable conceptual representation would store several phone numbers in one field:

`customer_id | phone_numbers`

with a value such as `"9876543210,0522123456"`.

The project instead uses:

`customer_id | phone_number | phone_type`

with one phone number per row.

The composite primary key `(customer_id, phone_number)` prevents the same phone number from being recorded twice for the same customer.

The Python implementation checks rows for:

- Complete column coverage
- Atomic values
- Non-null primary-key components
- Duplicate primary keys

The JavaScript implementation applies the same structural idea through `TableSchema.insert()`, rejecting arrays and structured objects where atomic attributes are required.

The Java implementation uses `NormalizationPolicy.inspect1NF()` to identify list, set, and map values that represent non-atomic attributes.

The PostgreSQL implementation expresses atomicity through relational columns and constraints. A phone number is stored as one `TEXT` value and validated with a regular expression.

## Second Normal Form

Second Normal Form becomes important when a relation has a composite candidate key.

Consider the conceptual relation:

`enrollment(student_id, course_id, student_name, course_name, grade)`

with candidate key:

`(student_id, course_id)`

The dependencies include:

`student_id → student_name`

`course_id → course_name`

`student_id, course_id → grade`

The first two dependencies are partial because their determinants contain only part of the composite key.

The normalized decomposition is:

| Relation | Key | Facts |
|---|---|---|
| `student` | `student_id` | Student attributes |
| `course` | `course_id` | Course attributes |
| `enrollment` | `(student_id, course_id)` | Enrollment-specific attributes |

The enrollment relation therefore stores `grade`, because the grade belongs to the particular student-course association.

This decomposition reduces update anomalies. A student's name does not need to be changed in every enrollment row.

The Python implementation explicitly represents the three relations and validates their foreign-key relationships.

The JavaScript implementation evaluates functional dependencies and emits a `violation` event when a determinant is a proper subset of a composite candidate key while determining a non-key attribute.

The C++ implementation focuses on dependency analysis through sets and identifies partial dependencies independently from the storage model.

The Java implementation represents functional dependencies with immutable records and evaluates whether a determinant is a proper subset of the candidate key.

The PostgreSQL model enforces the decomposition structurally through `student`, `course`, and `enrollment` tables. The enrollment primary key is `(student_id, course_id)`.

## Third Normal Form

Third Normal Form addresses transitive dependencies.

Consider:

`employee(employee_id, employee_name, department_id, department_name)`

with:

`employee_id → department_id`

and:

`department_id → department_name`

The department name is not a direct fact about the employee identifier. It is a fact about the department.

The normalized design is:

`employee(employee_id, employee_name, department_id)`

`department(department_id, department_name)`

The foreign key from `employee.department_id` to `department.department_id` preserves the relationship without copying the department name into every employee row.

This is different from the 2NF problem. 2NF focuses on dependencies on part of a composite key. 3NF focuses on non-key attributes determining other non-key attributes.

The Python model demonstrates this through separate `employee` and `department` relations.

The JavaScript analyzer searches for a complete-key dependency followed by a dependency from an intermediate non-key attribute.

The C++ implementation uses a dependency graph-like representation to detect:

`key → intermediate → final attribute`

The Java implementation stores dependencies as immutable records and uses maps to detect transitive relationships.

The PostgreSQL implementation gives `department.department_id` a unique primary key and references it from `employee.department_id`.

## Denormalization

Denormalization is not another normal form. It is an intentional decision to introduce controlled redundancy after considering workload characteristics.

A normalized order report requires a relationship between:

`customer_order`

and:

`customer`

A read model may instead expose:

`order_id | customer_id | customer_name | customer_city | order_amount`

The customer attributes are redundant because they already exist in `customer`.

The benefit is a simpler or faster read path for a workload dominated by reporting queries. The cost is consistency management. If the customer's city changes, every redundant copy must remain consistent.

The project therefore treats the normalized tables as authoritative and the denormalized representation as derived.

The Python implementation compares normalized join results with a denormalized reporting structure and deliberately detects conflicting duplicated customer values.

The JavaScript implementation provides `DenormalizationAdvisor`, which compares estimated read benefit against update and consistency risk.

The C++ program maintains normalized customer and order storage while generating a denormalized reporting snapshot.

The Java program separates authoritative domain storage from a derived projection.

The PostgreSQL implementation provides both `order_reporting` as a view and `customer_order_snapshot` as a physical denormalized table.

## Relationship Between the Four Concepts

The four concepts address different questions.

| Question | Concept |
|---|---|
| Does each attribute contain one atomic value? | 1NF |
| Does a non-key attribute depend on the whole composite key? | 2NF |
| Does a non-key attribute depend on another non-key attribute? | 3NF |
| Is redundancy deliberately introduced for a workload benefit? | Denormalization |

They should not be treated as interchangeable.

A design can satisfy 1NF while still violating 2NF.

A design can satisfy 2NF while still containing a transitive dependency that should be addressed for 3NF.

A denormalized design can intentionally move away from a highly normalized structure when measured read performance, reporting simplicity, or operational requirements justify the additional consistency burden.

## Python Implementation

The Python file uses `Relation` as a compact relational model.

Its important mechanisms are:

- `columns` describes relation attributes.
- `primary_key` identifies row identity.
- `rows` contains concrete relation instances.
- `foreign_keys` records cross-relation dependencies.
- `validate_1nf()` checks atomicity and key uniqueness.
- `validate_foreign_keys()` checks referential integrity.
- `project()` performs a relational projection.
- `distinct()` removes duplicate projected rows.

The implementation progresses from atomic customer-phone storage to 2NF enrollment decomposition, then to 3NF employee-department decomposition and finally to controlled denormalized reporting.

The anomaly example intentionally constructs contradictory duplicated customer data. The failure demonstrates why redundant facts can become inconsistent when they are independently writable.

## JavaScript Implementation

The JavaScript implementation emphasizes event-driven policy evaluation.

`SchemaRegistry` manages table definitions.

`TableSchema` validates schema structure and rejects:

- Unknown or missing columns
- Duplicate primary keys
- Arrays used as atomic values
- Structured objects used as atomic values

`NormalizationAnalyzer` extends `EventEmitter`. It emits a `violation` event when functional dependency analysis finds a 2NF or 3NF issue.

This makes the implementation useful as a policy engine rather than merely a data container.

`DenormalizationAdvisor` models a workload decision using:

`read benefit = read frequency × join cost`

and:

`write risk = update frequency × consistency risk`

The formula is intentionally a simplified engineering heuristic rather than a database optimizer. Real decisions should use measured query plans, workload traces, write amplification, storage cost, and operational consistency requirements.

## C++ Implementation

The C++ implementation treats normalization as a dependency-analysis problem and uses standard library containers for explicit set operations.

`FunctionalDependency` stores determinant and dependent attribute sets.

`NormalizationEngine` provides:

- Subset testing
- Proper-subset testing
- 2NF partial-dependency detection
- 3NF transitive-dependency detection
- A simple 1NF atomicity check

The `ReportingStore` represents a normalized application-side domain model with:

- Customer records
- Order records
- Primary-key uniqueness
- Foreign-key-like validation
- Positive monetary amounts
- Normalized reporting
- Derived denormalized reporting

The implementation uses `std::map` for deterministic identifiers and `std::set` for dependency analysis. This makes the functional dependency rules explicit rather than hiding them behind a database abstraction.

## Java Implementation

The Java implementation models normalization as an enterprise policy layer.

The domain includes:

- `Customer`
- `Order`
- `FunctionalDependency`
- `Finding`
- `NormalizationPolicy`
- `Repository`
- `DenormalizationDecision`

Java records provide immutable representations for functional dependencies and domain values.

The policy layer distinguishes:

`ATOMICITY_VIOLATION`

`PARTIAL_DEPENDENCY`

`TRANSITIVE_DEPENDENCY`

`DUPLICATE_KEY`

`REFERENTIAL_INTEGRITY`

The repository validates customer existence before accepting an order, preventing an order from referencing an unknown customer.

The denormalization policy is separated from the normalized repository so that a reporting optimization does not silently become a second authoritative data store.

## PostgreSQL Implementation

The SQL script creates a dedicated `normalization_lab` schema and recreates it on each execution, making the script repeatable.

The relational model includes:

- `customer`
- `customer_phone`
- `student`
- `course`
- `enrollment`
- `department`
- `employee`
- `customer_order`
- `customer_order_snapshot`

Primary keys establish row identity.

Foreign keys enforce relationships.

Check constraints enforce domain rules such as:

- Non-empty names
- Valid phone formats
- Allowed grades
- Positive order amounts
- Valid phone types

Unique constraints enforce facts such as unique course and department names.

The composite key on `enrollment` demonstrates a natural 2NF scenario:

`PRIMARY KEY (student_id, course_id)`

The employee-department model demonstrates 3NF by keeping department attributes in `department`.

The `order_reporting` view demonstrates a normalized read path.

The `customer_order_snapshot` table demonstrates physical denormalization for reporting. It is explicitly treated as a derived representation rather than the authoritative customer source.

The PostgreSQL script also demonstrates:

- CTE-based aggregation
- Reporting views
- Transaction boundaries
- Savepoints
- Trigger-based snapshot maintenance
- Foreign-key enforcement
- Indexed lookup paths
- Update-anomaly prevention

## Update, Insert, and Delete Anomalies

Normalization is closely related to modification anomalies.

### Update anomaly

If a department name is duplicated across many employee rows, renaming the department requires updating every copy. Missing one row creates contradictory data.

The 3NF design stores the department name once in `department`.

### Insert anomaly

If department information exists only as part of an employee record, a new department may be impossible to represent before its first employee is hired.

A separate `department` relation removes this dependency.

### Delete anomaly

If the last employee belonging to a department is deleted from a poorly designed combined relation, the department's only stored representation may disappear.

Separating department facts preserves the department independently from employee membership.

## Performance Considerations

Normalization can increase the number of joins required for some read queries. That is not automatically a performance problem.

The appropriate design depends on:

- Query frequency
- Join selectivity
- Index quality
- Data volume
- Update frequency
- Storage cost
- Transaction requirements
- Cache behavior
- Reporting latency requirements

The SQL implementation creates indexes where the access pattern is clear.

`customer_order(customer_id, ordered_at DESC)` supports customer-specific recent-order queries.

`enrollment(course_id)` supports reverse lookup from courses to enrolled students.

`employee(department_id)` supports department-to-employee lookups.

Indexes also have costs. They consume storage and increase write work because index entries must be maintained when rows change.

Denormalization should therefore be justified by measured workload behavior rather than assumed to be faster.

## Integrity and Security Considerations

Database-level constraints are important because application validation alone cannot protect data when multiple applications, scripts, administrators, or integration processes can write to the database.

The PostgreSQL model therefore places important invariants at the database boundary.

Foreign keys prevent orphaned relationships.

Check constraints reject invalid domain values.

Primary keys prevent duplicate identities.

Unique constraints protect candidate-key-like business facts.

Transactions prevent partial updates from becoming committed database state.

The denormalized snapshot illustrates an additional concern: redundant data creates more locations where stale or inconsistent information can exist. Derived representations should have a defined refresh or synchronization mechanism and should not be treated as independent authorities unless that architecture is explicitly intended.

## Failure Conditions

The implementations deliberately exercise failure conditions rather than silently accepting invalid state.

Examples include:

- Duplicate primary keys
- Non-atomic values
- Unknown foreign-key targets
- Invalid monetary values
- Invalid grades
- Invalid phone formats
- Missing required attributes
- Contradictory duplicated data
- Partial functional dependencies
- Transitive functional dependencies

These failures represent structural or domain violations rather than ordinary application exceptions that can safely be ignored.

## Architectural View

The central dependency flow can be represented as:

`Atomic facts`

→ `1NF`

→ `Remove partial dependencies`

→ `2NF`

→ `Remove transitive dependencies`

→ `3NF`

→ `Measure workload`

→ `Controlled denormalization when justified`

The direction is not a requirement that every production database remain maximally normalized. The important design principle is that redundancy should be intentional, bounded, measurable, and governed by clear ownership of authoritative data.

## File Responsibilities

| File | Technical perspective |
|---|---|
| Python | Relational modeling, validation, functional dependency examples, anomaly detection |
| JavaScript | Event-driven normalization analysis and workload-based denormalization evaluation |
| C++17 | Dependency-analysis engine and application-side normalized reporting store |
| Java 17 | Enterprise domain model, immutable policy records, validation, and repository behavior |
| PostgreSQL | Executable relational schema, constraints, indexes, views, CTEs, transactions, triggers, and reporting model |
| README.md | Conceptual distinctions and explanation of the implemented normalization workflow |

The five executable implementations intentionally approach the same database-design subject from different technical perspectives rather than reproducing one language's design in another language.
