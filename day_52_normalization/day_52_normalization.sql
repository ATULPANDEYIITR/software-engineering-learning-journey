DROP SCHEMA IF EXISTS normalization_lab CASCADE;
CREATE SCHEMA normalization_lab;
SET search_path TO normalization_lab;

-- The schema separates atomic facts, partial dependencies, and transitive
-- dependencies. A denormalized reporting table is retained only where
-- deliberate redundancy is useful for read-heavy reporting.

CREATE TABLE customer (
    customer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_name TEXT NOT NULL,
    city TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT customer_name_not_blank
        CHECK (btrim(customer_name) <> ''),
    CONSTRAINT customer_city_not_blank
        CHECK (btrim(city) <> '')
);

CREATE TABLE customer_phone (
    customer_id BIGINT NOT NULL,
    phone_number TEXT NOT NULL,
    phone_type TEXT NOT NULL,
    PRIMARY KEY (customer_id, phone_number),
    CONSTRAINT customer_phone_customer_fk
        FOREIGN KEY (customer_id)
        REFERENCES customer(customer_id)
        ON DELETE CASCADE,
    CONSTRAINT customer_phone_type_ck
        CHECK (phone_type IN ('mobile', 'office', 'home')),
    CONSTRAINT customer_phone_number_ck
        CHECK (phone_number ~ '^[0-9]{7,15}$')
);

-- This relation demonstrates 2NF by keeping student facts, course facts,
-- and enrollment facts separate. The composite enrollment key determines
-- only attributes belonging to the enrollment itself.
CREATE TABLE student (
    student_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    student_name TEXT NOT NULL,
    CONSTRAINT student_name_not_blank
        CHECK (btrim(student_name) <> '')
);

CREATE TABLE course (
    course_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    course_name TEXT NOT NULL UNIQUE,
    CONSTRAINT course_name_not_blank
        CHECK (btrim(course_name) <> '')
);

CREATE TABLE enrollment (
    student_id BIGINT NOT NULL,
    course_id BIGINT NOT NULL,
    grade TEXT,
    enrolled_at DATE NOT NULL DEFAULT CURRENT_DATE,
    PRIMARY KEY (student_id, course_id),
    CONSTRAINT enrollment_student_fk
        FOREIGN KEY (student_id)
        REFERENCES student(student_id)
        ON DELETE CASCADE,
    CONSTRAINT enrollment_course_fk
        FOREIGN KEY (course_id)
        REFERENCES course(course_id)
        ON DELETE RESTRICT,
    CONSTRAINT enrollment_grade_ck
        CHECK (
            grade IS NULL
            OR grade IN ('A+', 'A', 'A-', 'B+', 'B', 'B-', 'C', 'F')
        )
);

-- This decomposition demonstrates 3NF. Department name depends on
-- department_id, not directly on employee_id, so it belongs in department.
CREATE TABLE department (
    department_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    department_name TEXT NOT NULL UNIQUE,
    CONSTRAINT department_name_not_blank
        CHECK (btrim(department_name) <> '')
);

CREATE TABLE employee (
    employee_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_name TEXT NOT NULL,
    department_id BIGINT NOT NULL,
    CONSTRAINT employee_name_not_blank
        CHECK (btrim(employee_name) <> ''),
    CONSTRAINT employee_department_fk
        FOREIGN KEY (department_id)
        REFERENCES department(department_id)
        ON DELETE RESTRICT
);

CREATE TABLE customer_order (
    order_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    order_amount NUMERIC(12,2) NOT NULL,
    ordered_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT order_customer_fk
        FOREIGN KEY (customer_id)
        REFERENCES customer(customer_id)
        ON DELETE RESTRICT,
    CONSTRAINT order_amount_positive
        CHECK (order_amount > 0)
);

-- This index supports the common foreign-key/reporting lookup from orders
-- to a customer's recent activity.
CREATE INDEX customer_order_customer_date_idx
    ON customer_order (customer_id, ordered_at DESC);

CREATE INDEX enrollment_course_idx
    ON enrollment (course_id);

CREATE INDEX employee_department_idx
    ON employee (department_id);

INSERT INTO customer (customer_name, city)
VALUES
    ('Nisha', 'Lucknow'),
    ('Arjun', 'Delhi'),
    ('Meera', 'Pune');

INSERT INTO customer_phone (customer_id, phone_number, phone_type)
VALUES
    (1, '9876543210', 'mobile'),
    (1, '0522123456', 'office'),
    (2, '9988776655', 'mobile');

INSERT INTO student (student_name)
VALUES
    ('Anika'),
    ('Rohan'),
    ('Kabir');

INSERT INTO course (course_name)
VALUES
    ('Database Systems'),
    ('Distributed Systems'),
    ('Information Security');

INSERT INTO enrollment (student_id, course_id, grade)
VALUES
    (1, 1, 'A'),
    (1, 2, 'B+'),
    (2, 1, 'A-'),
    (3, 3, 'A');

INSERT INTO department (department_name)
VALUES
    ('Engineering'),
    ('Finance'),
    ('Operations');

INSERT INTO employee (employee_name, department_id)
VALUES
    ('Meera', 1),
    ('Kabir', 2),
    ('Sanjay', 3);

INSERT INTO customer_order (customer_id, order_amount)
VALUES
    (1, 2500.00),
    (1, 1750.00),
    (2, 1800.00),
    (3, 3200.00);

-- 1NF query: each phone value is atomic and each customer-phone pair
-- has a unique key.
SELECT
    customer_id,
    phone_number,
    phone_type
FROM customer_phone
ORDER BY customer_id, phone_number;

-- 2NF query: enrollment facts can be joined to student and course facts
-- without storing student_name or course_name in the composite-key table.
SELECT
    e.student_id,
    s.student_name,
    e.course_id,
    c.course_name,
    e.grade
FROM enrollment AS e
JOIN student AS s
    ON s.student_id = e.student_id
JOIN course AS c
    ON c.course_id = e.course_id
ORDER BY e.student_id, e.course_id;

-- 3NF query: department_name is obtained through department_id rather
-- than being redundantly stored in employee.
SELECT
    e.employee_id,
    e.employee_name,
    d.department_id,
    d.department_name
FROM employee AS e
JOIN department AS d
    ON d.department_id = e.department_id
ORDER BY e.employee_id;

-- A CTE makes the normalized reporting path explicit before aggregation.
WITH customer_order_totals AS (
    SELECT
        customer_id,
        COUNT(*) AS order_count,
        SUM(order_amount) AS total_amount
    FROM customer_order
    GROUP BY customer_id
)
SELECT
    c.customer_id,
    c.customer_name,
    c.city,
    cot.order_count,
    cot.total_amount
FROM customer AS c
JOIN customer_order_totals AS cot
    ON cot.customer_id = c.customer_id
ORDER BY cot.total_amount DESC;

-- Functional-dependency audit for the department relation:
-- every employee references exactly one department, while department_name
-- is uniquely determined by department_id.
SELECT
    department_id,
    COUNT(*) AS employees_in_department
FROM employee
GROUP BY department_id
ORDER BY department_id;

-- The following view is a controlled denormalized read model. It is derived
-- from normalized source tables and therefore does not become an independent
-- source of truth.
CREATE VIEW order_reporting AS
SELECT
    o.order_id,
    o.customer_id,
    c.customer_name,
    c.city AS customer_city,
    o.order_amount,
    o.ordered_at
FROM customer_order AS o
JOIN customer AS c
    ON c.customer_id = o.customer_id;

SELECT *
FROM order_reporting
ORDER BY ordered_at DESC;

-- A trigger protects a deliberately denormalized reporting cache from
-- storing a stale customer city when the source customer changes.
CREATE TABLE customer_order_snapshot (
    order_id BIGINT PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    customer_name TEXT NOT NULL,
    customer_city TEXT NOT NULL,
    order_amount NUMERIC(12,2) NOT NULL,
    snapshot_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT snapshot_customer_fk
        FOREIGN KEY (customer_id)
        REFERENCES customer(customer_id)
        ON DELETE RESTRICT,
    CONSTRAINT snapshot_amount_ck
        CHECK (order_amount > 0)
);

CREATE OR REPLACE FUNCTION refresh_order_snapshot()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO customer_order_snapshot (
        order_id,
        customer_id,
        customer_name,
        customer_city,
        order_amount
    )
    SELECT
        NEW.order_id,
        NEW.customer_id,
        c.customer_name,
        c.city,
        NEW.order_amount
    FROM customer AS c
    WHERE c.customer_id = NEW.customer_id
    ON CONFLICT (order_id)
    DO UPDATE SET
        customer_id = EXCLUDED.customer_id,
        customer_name = EXCLUDED.customer_name,
        customer_city = EXCLUDED.customer_city,
        order_amount = EXCLUDED.order_amount,
        snapshot_at = CURRENT_TIMESTAMP;

    RETURN NEW;
END;
$$;

CREATE TRIGGER customer_order_snapshot_trigger
AFTER INSERT OR UPDATE
ON customer_order
FOR EACH ROW
EXECUTE FUNCTION refresh_order_snapshot();

INSERT INTO customer_order_snapshot (
    order_id,
    customer_id,
    customer_name,
    customer_city,
    order_amount
)
SELECT
    o.order_id,
    o.customer_id,
    c.customer_name,
    c.city,
    o.order_amount
FROM customer_order AS o
JOIN customer AS c
    ON c.customer_id = o.customer_id
ON CONFLICT (order_id) DO NOTHING;

-- Demonstrate transactional behavior: the attempted invalid row is rolled
-- back while existing normalized data remains intact.
BEGIN;

SAVEPOINT before_invalid_enrollment;

INSERT INTO enrollment (student_id, course_id, grade)
VALUES (1, 999999, 'A');

ROLLBACK TO SAVEPOINT before_invalid_enrollment;

COMMIT;

-- Demonstrate update-anomaly prevention. Changing a city once changes the
-- authoritative fact. The reporting view immediately reflects the change.
BEGIN;

UPDATE customer
SET city = 'Kanpur'
WHERE customer_id = 1;

COMMIT;

SELECT
    customer_id,
    customer_name,
    city
FROM customer
WHERE customer_id = 1;

SELECT
    order_id,
    customer_name,
    customer_city
FROM order_reporting
WHERE customer_id = 1
ORDER BY order_id;

-- Refresh the derived denormalized snapshot after the authoritative update.
INSERT INTO customer_order_snapshot (
    order_id,
    customer_id,
    customer_name,
    customer_city,
    order_amount
)
SELECT
    o.order_id,
    o.customer_id,
    c.customer_name,
    c.city,
    o.order_amount
FROM customer_order AS o
JOIN customer AS c
    ON c.customer_id = o.customer_id
WHERE o.customer_id = 1
ON CONFLICT (order_id)
DO UPDATE SET
    customer_id = EXCLUDED.customer_id,
    customer_name = EXCLUDED.customer_name,
    customer_city = EXCLUDED.customer_city,
    order_amount = EXCLUDED.order_amount,
    snapshot_at = CURRENT_TIMESTAMP;

SELECT
    order_id,
    customer_id,
    customer_name,
    customer_city,
    order_amount
FROM customer_order_snapshot
ORDER BY order_id;

-- The following statements are intentionally executable failure cases when
-- tested individually. PostgreSQL constraints reject duplicate keys,
-- invalid foreign keys, non-positive amounts, and invalid grade values.
-- They are represented here as comments so the complete script remains
-- successfully executable from start to finish.
--
-- INSERT INTO customer (customer_id, customer_name, city)
-- VALUES (1, 'Duplicate', 'Delhi');
--
-- INSERT INTO enrollment (student_id, course_id, grade)
-- VALUES (1, 999999, 'A');
--
-- INSERT INTO customer_order (customer_id, order_amount)
-- VALUES (1, -100.00);
--
-- INSERT INTO enrollment (student_id, course_id, grade)
-- VALUES (1, 1, 'INVALID');
