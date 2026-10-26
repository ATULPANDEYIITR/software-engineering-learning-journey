#!/usr/bin/env python3

"""
Database Optimization Case Study

A self-contained simulation of query-plan analysis and optimization.
It models:
- table statistics
- sequential and index scans
- joins
- filtering selectivity
- sorting
- aggregation
- estimated execution cost
- bottleneck detection
- optimization recommendations

No external dependencies are required.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
import math
import random


class AccessPath(Enum):
    SEQUENTIAL_SCAN = "Sequential Scan"
    INDEX_SCAN = "Index Scan"
    INDEX_ONLY_SCAN = "Index Only Scan"


class JoinAlgorithm(Enum):
    NESTED_LOOP = "Nested Loop"
    HASH_JOIN = "Hash Join"
    MERGE_JOIN = "Merge Join"


@dataclass(frozen=True)
class Index:
    name: str
    columns: Tuple[str, ...]
    unique: bool = False
    covering_columns: Tuple[str, ...] = ()


@dataclass
class ColumnStats:
    name: str
    distinct_values: int
    null_fraction: float = 0.0


@dataclass
class TableStats:
    name: str
    rows: int
    pages: int
    columns: Dict[str, ColumnStats]
    indexes: List[Index] = field(default_factory=list)

    def has_index(self, columns: Tuple[str, ...]) -> bool:
        return any(
            index.columns[: len(columns)] == columns
            for index in self.indexes
        )


@dataclass
class Predicate:
    column: str
    operator: str
    value: object

    def selectivity(self, table: TableStats) -> float:
        stats = table.columns.get(self.column)

        if stats is None:
            return 0.1

        if self.operator == "=":
            return max(1.0 / max(stats.distinct_values, 1), 0.000001)

        if self.operator in {"<", "<=", ">", ">="}:
            return 0.33

        if self.operator == "IS NULL":
            return max(stats.null_fraction, 0.000001)

        if self.operator == "IS NOT NULL":
            return max(1.0 - stats.null_fraction, 0.000001)

        if self.operator == "LIKE":
            return 0.05

        return 0.25


@dataclass
class ScanPlan:
    table: TableStats
    predicates: List[Predicate]
    access_path: AccessPath
    estimated_rows: float
    startup_cost: float
    total_cost: float
    bottleneck_score: float
    reason: str


@dataclass
class JoinPlan:
    algorithm: JoinAlgorithm
    left_rows: float
    right_rows: float
    output_rows: float
    cost: float
    reason: str


@dataclass
class QueryPlan:
    sql: str
    scans: List[ScanPlan]
    joins: List[JoinPlan]
    sort_cost: float
    aggregate_cost: float

    @property
    def total_cost(self) -> float:
        return (
            sum(scan.total_cost for scan in self.scans)
            + sum(join.cost for join in self.joins)
            + self.sort_cost
            + self.aggregate_cost
        )

    def bottlenecks(self) -> List[str]:
        findings: List[Tuple[float, str]] = []

        for scan in self.scans:
            findings.append(
                (
                    scan.bottleneck_score,
                    f"{scan.table.name}: {scan.reason}",
                )
            )

        for join in self.joins:
            findings.append(
                (
                    join.cost,
                    f"{join.algorithm.value}: {join.reason}",
                )
            )

        if self.sort_cost > 0:
            findings.append(
                (self.sort_cost, "Explicit sort operation contributes significant cost.")
            )

        if self.aggregate_cost > 0:
            findings.append(
                (self.aggregate_cost, "Aggregation requires processing the filtered result.")
            )

        return [message for _, message in sorted(findings, reverse=True)]


class QueryOptimizer:
    SEQ_PAGE_COST = 1.0
    RANDOM_PAGE_COST = 4.0
    CPU_TUPLE_COST = 0.01
    CPU_INDEX_TUPLE_COST = 0.005
    SORT_FACTOR = 0.02

    def estimate_scan(
        self,
        table: TableStats,
        predicates: List[Predicate],
        projected_columns: Tuple[str, ...],
    ) -> ScanPlan:
        selectivity = 1.0

        for predicate in predicates:
            selectivity *= predicate.selectivity(table)

        estimated_rows = max(1.0, table.rows * selectivity)

        indexed_predicates = [
            predicate
            for predicate in predicates
            if table.has_index((predicate.column,))
        ]

        if indexed_predicates:
            index_columns = tuple(p.column for p in indexed_predicates)
            index_available = table.has_index(index_columns[:1])
        else:
            index_available = False

        if index_available and estimated_rows < table.rows * 0.20:
            covering = any(
                set(projected_columns).issubset(
                    set(index.columns) | set(index.covering_columns)
                )
                for index in table.indexes
            )

            access_path = (
                AccessPath.INDEX_ONLY_SCAN
                if covering
                else AccessPath.INDEX_SCAN
            )

            index_pages = max(1.0, math.log2(max(table.pages, 2)))
            heap_pages = min(
                table.pages,
                max(1.0, estimated_rows / max(table.rows / table.pages, 1)),
            )

            startup = index_pages * self.RANDOM_PAGE_COST
            total = (
                startup
                + heap_pages * self.RANDOM_PAGE_COST
                + estimated_rows * self.CPU_INDEX_TUPLE_COST
            )

            reason = (
                f"Selective predicate estimated at {selectivity:.4%}; "
                f"index access avoids scanning approximately "
                f"{table.rows - estimated_rows:,.0f} rows."
            )

        else:
            access_path = AccessPath.SEQUENTIAL_SCAN
            startup = 0.0
            total = (
                table.pages * self.SEQ_PAGE_COST
                + table.rows * self.CPU_TUPLE_COST
            )

            if indexed_predicates:
                reason = (
                    f"An index exists, but estimated selectivity "
                    f"({selectivity:.2%}) is too low for the simplified cost model "
                    f"to prefer it."
                )
            else:
                reason = (
                    "No suitable predicate index exists, so the optimizer "
                    "must inspect the table sequentially."
                )

        bottleneck_score = total

        return ScanPlan(
            table=table,
            predicates=predicates,
            access_path=access_path,
            estimated_rows=estimated_rows,
            startup_cost=startup,
            total_cost=total,
            bottleneck_score=bottleneck_score,
            reason=reason,
        )

    def choose_join(
        self,
        left_rows: float,
        right_rows: float,
        join_selectivity: float,
        indexes_on_inner_side: bool,
    ) -> JoinPlan:
        output_rows = max(1.0, left_rows * right_rows * join_selectivity)

        nested_loop_cost = (
            left_rows
            * (
                math.log2(max(right_rows, 2))
                if indexes_on_inner_side
                else right_rows
            )
            * 0.01
        )

        hash_join_cost = (left_rows + right_rows) * 0.03

        merge_join_cost = (
            (left_rows * math.log2(max(left_rows, 2)))
            + (right_rows * math.log2(max(right_rows, 2)))
        ) * 0.005

        candidates = [
            (
                nested_loop_cost,
                JoinAlgorithm.NESTED_LOOP,
                "Nested Loop is competitive when the outer relation is small or the inner side is indexed.",
            ),
            (
                hash_join_cost,
                JoinAlgorithm.HASH_JOIN,
                "Hash Join processes both inputs and is effective for large equality joins.",
            ),
            (
                merge_join_cost,
                JoinAlgorithm.MERGE_JOIN,
                "Merge Join benefits when inputs are already ordered or cheaply sortable.",
            ),
        ]

        cost, algorithm, reason = min(candidates, key=lambda item: item[0])

        return JoinPlan(
            algorithm=algorithm,
            left_rows=left_rows,
            right_rows=right_rows,
            output_rows=output_rows,
            cost=cost,
            reason=reason,
        )


def build_demo_database() -> Dict[str, TableStats]:
    return {
        "orders": TableStats(
            name="orders",
            rows=2_500_000,
            pages=125_000,
            columns={
                "id": ColumnStats("id", 2_500_000),
                "customer_id": ColumnStats("customer_id", 180_000),
                "status": ColumnStats("status", 5),
                "created_at": ColumnStats("created_at", 900),
                "total_amount": ColumnStats("total_amount", 1_000_000),
            },
            indexes=[
                Index("orders_pkey", ("id",), unique=True),
                Index("idx_orders_customer", ("customer_id",)),
                Index("idx_orders_created_at", ("created_at",)),
                Index(
                    "idx_orders_status_created",
                    ("status", "created_at"),
                ),
            ],
        ),
        "customers": TableStats(
            name="customers",
            rows=180_000,
            pages=12_000,
            columns={
                "id": ColumnStats("id", 180_000),
                "region": ColumnStats("region", 8),
                "customer_tier": ColumnStats("customer_tier", 4),
                "email": ColumnStats("email", 180_000),
            },
            indexes=[
                Index("customers_pkey", ("id",), unique=True),
                Index("idx_customers_region", ("region",)),
            ],
        ),
    }


def print_plan(plan: QueryPlan) -> None:
    print("\n" + "=" * 78)
    print("QUERY PLAN ANALYSIS")
    print("=" * 78)
    print(plan.sql)
    print()

    for scan in plan.scans:
        print(f"Table:           {scan.table.name}")
        print(f"Access path:     {scan.access_path.value}")
        print(f"Estimated rows:  {scan.estimated_rows:,.0f}")
        print(f"Startup cost:    {scan.startup_cost:,.2f}")
        print(f"Total cost:      {scan.total_cost:,.2f}")
        print(f"Reason:          {scan.reason}")
        print()

    for join in plan.joins:
        print(f"Join algorithm:   {join.algorithm.value}")
        print(f"Left rows:        {join.left_rows:,.0f}")
        print(f"Right rows:       {join.right_rows:,.0f}")
        print(f"Output rows:      {join.output_rows:,.0f}")
        print(f"Join cost:        {join.cost:,.2f}")
        print(f"Reason:           {join.reason}")
        print()

    print(f"Sort cost:        {plan.sort_cost:,.2f}")
    print(f"Aggregate cost:   {plan.aggregate_cost:,.2f}")
    print(f"Estimated total:  {plan.total_cost:,.2f}")

    print("\nTop bottlenecks:")
    for index, finding in enumerate(plan.bottlenecks()[:5], 1):
        print(f"{index}. {finding}")


def optimize_customer_order_query(
    database: Dict[str, TableStats],
) -> Tuple[QueryPlan, QueryPlan]:
    optimizer = QueryOptimizer()
    orders = database["orders"]
    customers = database["customers"]

    sql_before = """
SELECT c.region, SUM(o.total_amount)
FROM orders o
JOIN customers c ON c.id = o.customer_id
WHERE o.status = 'completed'
  AND o.created_at >= DATE '2026-01-01'
GROUP BY c.region
ORDER BY SUM(o.total_amount) DESC;
""".strip()

    # The first model intentionally has only the existing single-column indexes.
    before_order_scan = optimizer.estimate_scan(
        orders,
        [
            Predicate("status", "=", "completed"),
            Predicate("created_at", ">=", "2026-01-01"),
        ],
        ("customer_id", "total_amount"),
    )

    customer_scan = optimizer.estimate_scan(
        customers,
        [],
        ("id", "region"),
    )

    before_join = optimizer.choose_join(
        before_order_scan.estimated_rows,
        customer_scan.estimated_rows,
        join_selectivity=1.0 / max(customers.rows, 1),
        indexes_on_inner_side=True,
    )

    before = QueryPlan(
        sql=sql_before,
        scans=[before_order_scan, customer_scan],
        joins=[before_join],
        sort_cost=before_join.output_rows
        * math.log2(max(before_join.output_rows, 2))
        * QueryOptimizer.SORT_FACTOR,
        aggregate_cost=before_join.output_rows * 0.02,
    )

    # Simulate the effect of a composite index matching the most selective
    # predicates and including columns needed by the aggregation.
    optimized_orders = TableStats(
        name="orders",
        rows=orders.rows,
        pages=orders.pages,
        columns=orders.columns,
        indexes=orders.indexes
        + [
            Index(
                "idx_orders_status_created_customer_amount",
                ("status", "created_at"),
                covering_columns=("customer_id", "total_amount"),
            )
        ],
    )

    optimized_order_scan = optimizer.estimate_scan(
        optimized_orders,
        [
            Predicate("status", "=", "completed"),
            Predicate("created_at", ">=", "2026-01-01"),
        ],
        ("customer_id", "total_amount"),
    )

    optimized_join = optimizer.choose_join(
        optimized_order_scan.estimated_rows,
        customer_scan.estimated_rows,
        join_selectivity=1.0 / max(customers.rows, 1),
        indexes_on_inner_side=True,
    )

    optimized = QueryPlan(
        sql=sql_before,
        scans=[optimized_order_scan, customer_scan],
        joins=[optimized_join],
        sort_cost=optimized_join.output_rows
        * math.log2(max(optimized_join.output_rows, 2))
        * QueryOptimizer.SORT_FACTOR,
        aggregate_cost=optimized_join.output_rows * 0.02,
    )

    return before, optimized


def validate_edge_cases() -> None:
    database = build_demo_database()
    optimizer = QueryOptimizer()

    empty_predicate_scan = optimizer.estimate_scan(
        database["orders"],
        [],
        ("id",),
    )

    assert empty_predicate_scan.access_path == AccessPath.SEQUENTIAL_SCAN
    assert empty_predicate_scan.estimated_rows == database["orders"].rows

    unknown_column_scan = optimizer.estimate_scan(
        database["orders"],
        [Predicate("unknown_column", "=", "x")],
        ("id",),
    )

    assert unknown_column_scan.estimated_rows >= 1

    null_scan = optimizer.estimate_scan(
        database["orders"],
        [Predicate("status", "IS NULL", None)],
        ("id",),
    )

    assert null_scan.estimated_rows >= 1


def demonstrate_statistics_effect() -> None:
    database = build_demo_database()
    orders = database["orders"]

    print("\nSTATISTICS SENSITIVITY")
    print("-" * 78)

    original = orders.columns["status"].distinct_values
    orders.columns["status"].distinct_values = 100

    optimizer = QueryOptimizer()
    plan = optimizer.estimate_scan(
        orders,
        [Predicate("status", "=", "completed")],
        ("id",),
    )

    print(
        f"Changing status distinct-value statistics from {original} to "
        f"{orders.columns['status'].distinct_values} changes estimated "
        f"selectivity and can change access-path decisions."
    )
    print(f"Estimated rows: {plan.estimated_rows:,.0f}")
    print(f"Access path:    {plan.access_path.value}")

    orders.columns["status"].distinct_values = original


def main() -> None:
    random.seed(42)

    database = build_demo_database()
    validate_edge_cases()

    before, optimized = optimize_customer_order_query(database)

    print_plan(before)

    print("\n" + "=" * 78)
    print("OPTIMIZED PLAN")
    print("=" * 78)
    print_plan(optimized)

    improvement = (
        (before.total_cost - optimized.total_cost)
        / before.total_cost
        * 100
        if before.total_cost
        else 0
    )

    print("\n" + "=" * 78)
    print("OPTIMIZATION RESULT")
    print("=" * 78)
    print(f"Before cost:       {before.total_cost:,.2f}")
    print(f"After cost:        {optimized.total_cost:,.2f}")
    print(f"Estimated change:  {improvement:.2f}%")

    demonstrate_statistics_effect()

    print("\nPRODUCTION CHECKS")
    print("-" * 78)
    print("1. Compare estimated and actual row counts with EXPLAIN ANALYZE.")
    print("2. Refresh statistics after major data distribution changes.")
    print("3. Verify indexes against real workload frequency, not one query.")
    print("4. Watch write amplification caused by excessive indexes.")
    print("5. Never interpolate untrusted values into SQL.")
    print("6. Benchmark representative data volumes before deploying changes.")


if __name__ == "__main__":
    main()
