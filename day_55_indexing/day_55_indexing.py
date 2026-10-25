#!/usr/bin/env python3

"""
Indexing and Query Performance: executable repository-style database simulation.

The script models:
- heap/table storage
- B-tree indexes
- composite indexes
- partial indexes
- covering indexes
- selectivity
- index scans versus sequential scans
- simple cost estimation
- query-plan selection
- write amplification from maintaining indexes
- validation of index design
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from bisect import bisect_left, bisect_right
from collections import defaultdict
from typing import Any, Iterable


class ScanType(Enum):
    SEQUENTIAL = "sequential_scan"
    INDEX = "index_scan"
    INDEX_ONLY = "index_only_scan"


class IndexType(Enum):
    BTREE = "btree"
    HASH = "hash"


@dataclass(frozen=True)
class Row:
    order_id: int
    customer_id: int
    status: str
    region: str
    total_amount: float
    created_at: str


@dataclass
class Index:
    name: str
    columns: tuple[str, ...]
    index_type: IndexType = IndexType.BTREE
    included_columns: tuple[str, ...] = ()
    predicate: tuple[str, Any] | None = None
    entries: list[tuple[tuple[Any, ...], int]] = field(default_factory=list)

    def supports_equality_prefix(self, filters: dict[str, Any]) -> bool:
        if not self.columns:
            return False

        # A B-tree can use a contiguous equality prefix.
        prefix_length = 0
        for column in self.columns:
            if column in filters:
                prefix_length += 1
            else:
                break

        return prefix_length > 0

    def covers(self, requested_columns: Iterable[str]) -> bool:
        available = set(self.columns) | set(self.included_columns)
        return set(requested_columns).issubset(available)

    def applicable(self, filters: dict[str, Any]) -> bool:
        if self.predicate is None:
            return True

        column, expected = self.predicate
        return filters.get(column) == expected


@dataclass(frozen=True)
class Query:
    filters: dict[str, Any]
    selected_columns: tuple[str, ...]


@dataclass
class QueryPlan:
    scan_type: ScanType
    index_name: str | None
    estimated_rows: int
    estimated_cost: float
    reason: str


class Table:
    def __init__(self, name: str):
        self.name = name
        self.rows: dict[int, Row] = {}
        self.indexes: dict[str, Index] = {}
        self.write_operations = 0

    @staticmethod
    def row_key(row: Row) -> int:
        return row.order_id

    def insert(self, row: Row) -> None:
        if row.order_id in self.rows:
            raise ValueError(f"Duplicate primary key: {row.order_id}")

        if row.total_amount < 0:
            raise ValueError("total_amount cannot be negative")

        if row.status not in {"pending", "paid", "cancelled", "shipped"}:
            raise ValueError(f"Invalid status: {row.status}")

        self.rows[row.order_id] = row
        self.write_operations += 1

        # Every maintained secondary index requires an additional write.
        for index in self.indexes.values():
            if index.applicable(row.__dict__):
                self._add_index_entry(index, row)

    def create_index(
        self,
        name: str,
        columns: tuple[str, ...],
        included_columns: tuple[str, ...] = (),
        predicate: tuple[str, Any] | None = None,
    ) -> None:
        if name in self.indexes:
            raise ValueError(f"Index already exists: {name}")

        valid_columns = set(Row.__dataclass_fields__)
        if not set(columns).issubset(valid_columns):
            raise ValueError("Index references an unknown column")

        if not set(included_columns).issubset(valid_columns):
            raise ValueError("Included column does not exist")

        if not columns:
            raise ValueError("An index must contain at least one key column")

        index = Index(
            name=name,
            columns=columns,
            included_columns=included_columns,
            predicate=predicate,
        )

        self.indexes[name] = index

        for row in self.rows.values():
            if index.applicable(row.__dict__):
                self._add_index_entry(index, row)

        index.entries.sort()

    def _add_index_entry(self, index: Index, row: Row) -> None:
        key = tuple(getattr(row, column) for column in index.columns)
        index.entries.append((key, row.order_id))

    def analyze(self) -> dict[str, Any]:
        total_rows = len(self.rows)

        distributions: dict[str, dict[Any, int]] = {}
        for column in ("customer_id", "status", "region"):
            counts: dict[Any, int] = defaultdict(int)
            for row in self.rows.values():
                counts[getattr(row, column)] += 1
            distributions[column] = dict(counts)

        return {
            "rows": total_rows,
            "indexes": list(self.indexes),
            "distinct_values": {
                column: len(values)
                for column, values in distributions.items()
            },
            "write_operations": self.write_operations,
        }

    def _estimate_selectivity(self, filters: dict[str, Any]) -> float:
        if not filters:
            return 1.0

        selectivity = 1.0

        for column, value in filters.items():
            values = [getattr(row, column) for row in self.rows.values()]
            if not values:
                return 0.0

            frequency = values.count(value)
            selectivity *= frequency / len(values)

        return min(selectivity, 1.0)

    def explain(self, query: Query) -> QueryPlan:
        total_rows = len(self.rows)

        if total_rows == 0:
            return QueryPlan(
                ScanType.SEQUENTIAL,
                None,
                0,
                0,
                "The table is empty.",
            )

        sequential_cost = float(total_rows)

        candidates: list[QueryPlan] = []

        for index in self.indexes.values():
            if not index.applicable(query.filters):
                continue

            if not index.supports_equality_prefix(query.filters):
                continue

            selectivity = self._estimate_selectivity(query.filters)
            estimated_rows = max(1, int(total_rows * selectivity))

            # Approximate B-tree traversal plus qualifying entries.
            index_cost = 3.0 + estimated_rows * 0.8

            if index.covers(query.selected_columns):
                scan_type = ScanType.INDEX_ONLY
                index_cost *= 0.75
                reason = (
                    f"{index.name} matches the equality prefix and covers "
                    "the requested columns."
                )
            else:
                scan_type = ScanType.INDEX
                reason = (
                    f"{index.name} matches the equality prefix; table lookup "
                    "is still required for requested columns."
                )

            candidates.append(
                QueryPlan(
                    scan_type,
                    index.name,
                    estimated_rows,
                    index_cost,
                    reason,
                )
            )

        if not candidates:
            return QueryPlan(
                ScanType.SEQUENTIAL,
                None,
                total_rows,
                sequential_cost,
                "No usable index matches the query predicates.",
            )

        best = min(candidates, key=lambda plan: plan.estimated_cost)

        if best.estimated_cost >= sequential_cost:
            return QueryPlan(
                ScanType.SEQUENTIAL,
                None,
                total_rows,
                sequential_cost,
                "The estimated index cost is not lower than scanning the table.",
            )

        return best

    def execute(self, query: Query) -> tuple[QueryPlan, list[dict[str, Any]]]:
        plan = self.explain(query)

        candidate_rows: Iterable[Row]

        if plan.scan_type in {ScanType.INDEX, ScanType.INDEX_ONLY}:
            index = self.indexes[plan.index_name]  # type: ignore[index]
            row_ids = []

            for key, row_id in index.entries:
                row = self.rows[row_id]
                if all(getattr(row, column) == value for column, value in query.filters.items()):
                    row_ids.append(row_id)

            candidate_rows = (self.rows[row_id] for row_id in row_ids)
        else:
            candidate_rows = self.rows.values()

        result = []

        for row in candidate_rows:
            if all(getattr(row, column) == value for column, value in query.filters.items()):
                result.append(
                    {column: getattr(row, column) for column in query.selected_columns}
                )

        return plan, result


def seed_table() -> Table:
    table = Table("orders")

    regions = ["north", "south", "east", "west"]
    statuses = ["pending", "paid", "shipped", "cancelled"]

    for order_id in range(1, 1001):
        customer_id = (order_id * 17) % 100 + 1
        status = statuses[order_id % len(statuses)]
        region = regions[order_id % len(regions)]
        amount = float(100 + (order_id * 37) % 4900)
        created_at = f"2026-10-{(order_id % 28) + 1:02d}"

        table.insert(
            Row(
                order_id=order_id,
                customer_id=customer_id,
                status=status,
                region=region,
                total_amount=amount,
                created_at=created_at,
            )
        )

    return table


def demonstrate() -> None:
    table = seed_table()

    table.create_index(
        "idx_orders_customer",
        ("customer_id",),
    )

    table.create_index(
        "idx_orders_status_region",
        ("status", "region"),
        included_columns=("total_amount", "created_at"),
    )

    table.create_index(
        "idx_orders_paid_customer",
        ("customer_id",),
        included_columns=("total_amount",),
        predicate=("status", "paid"),
    )

    print("TABLE STATISTICS")
    print(table.analyze())
    print()

    queries = [
        Query(
            filters={"customer_id": 42},
            selected_columns=("order_id", "customer_id", "total_amount"),
        ),
        Query(
            filters={"status": "paid", "region": "north"},
            selected_columns=("order_id", "total_amount", "created_at"),
        ),
        Query(
            filters={"region": "north"},
            selected_columns=("order_id", "customer_id"),
        ),
        Query(
            filters={},
            selected_columns=("order_id", "total_amount"),
        ),
    ]

    for query in queries:
        plan, rows = table.execute(query)
        print("QUERY")
        print(query)
        print("PLAN")
        print(plan)
        print(f"ROWS RETURNED: {len(rows)}")
        print(f"SAMPLE: {rows[:3]}")
        print("-" * 72)

    # A write after index creation demonstrates maintenance overhead.
    before = table.write_operations
    table.insert(
        Row(
            order_id=5001,
            customer_id=42,
            status="paid",
            region="north",
            total_amount=725.50,
            created_at="2026-10-25",
        )
    )
    print(f"BASE TABLE WRITES BEFORE INSERT: {before}")
    print(f"BASE TABLE WRITES AFTER INSERT:  {table.write_operations}")

    # Security/validation edge case.
    try:
        table.insert(
            Row(
                order_id=5002,
                customer_id=43,
                status="invalid",
                region="north",
                total_amount=100,
                created_at="2026-10-25",
            )
        )
    except ValueError as exc:
        print(f"VALIDATION FAILURE: {exc}")


if __name__ == "__main__":
    demonstrate()
