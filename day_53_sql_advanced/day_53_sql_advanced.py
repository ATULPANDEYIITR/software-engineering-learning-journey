from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable


@dataclass(frozen=True)
class Sale:
    sale_id: int
    customer_id: int
    customer_name: str
    region: str
    product_id: int
    product_name: str
    category: str
    amount: Decimal
    sale_month: str


SALES = [
    Sale(1, 101, "Asha", "North", 1001, "Laptop", "Electronics", Decimal("1200.00"), "2026-01"),
    Sale(2, 102, "Ravi", "South", 1002, "Phone", "Electronics", Decimal("850.00"), "2026-01"),
    Sale(3, 103, "Meera", "North", 1003, "Desk", "Furniture", Decimal("450.00"), "2026-01"),
    Sale(4, 101, "Asha", "North", 1004, "Monitor", "Electronics", Decimal("400.00"), "2026-02"),
    Sale(5, 104, "Kabir", "West", 1005, "Chair", "Furniture", Decimal("300.00"), "2026-02"),
    Sale(6, 102, "Ravi", "South", 1001, "Laptop", "Electronics", Decimal("1300.00"), "2026-02"),
    Sale(7, 105, "Nisha", "West", 1002, "Phone", "Electronics", Decimal("900.00"), "2026-03"),
    Sale(8, 103, "Meera", "North", 1005, "Chair", "Furniture", Decimal("280.00"), "2026-03"),
    Sale(9, 101, "Asha", "North", 1002, "Phone", "Electronics", Decimal("820.00"), "2026-03"),
    Sale(10, 104, "Kabir", "West", 1001, "Laptop", "Electronics", Decimal("1250.00"), "2026-04"),
]


def inner_join_sales_by_customer(rows: Iterable[Sale]) -> dict[int, list[Sale]]:
    """Models an INNER JOIN by grouping matching customer keys."""
    result: dict[int, list[Sale]] = {}

    for row in rows:
        result.setdefault(row.customer_id, []).append(row)

    return result


def left_join_customer_totals(rows: Iterable[Sale]) -> dict[int, Decimal]:
    """A LEFT JOIN would retain customers without sales.

    The customer set is known independently, so zero totals are retained.
    """
    customers = {101, 102, 103, 104, 105, 106}
    totals = {customer_id: Decimal("0") for customer_id in customers}

    for row in rows:
        totals[row.customer_id] += row.amount

    return totals


def correlated_subquery_top_customers(rows: Iterable[Sale]) -> list[tuple[int, Decimal]]:
    """Equivalent conceptually to:

    SELECT customer_id, SUM(amount)
    FROM sales s
    GROUP BY customer_id
    HAVING SUM(amount) >= (
        SELECT AVG(customer_total)
        FROM (
            SELECT SUM(amount) AS customer_total
            FROM sales
            GROUP BY customer_id
        ) x
    );
    """
    totals = left_join_customer_totals(rows)
    active_totals = [value for value in totals.values() if value > 0]

    if not active_totals:
        return []

    average_total = sum(active_totals, Decimal("0")) / Decimal(len(active_totals))

    return sorted(
        [
            (customer_id, total)
            for customer_id, total in totals.items()
            if total >= average_total
        ],
        key=lambda item: item[1],
        reverse=True,
    )


def cte_style_monthly_totals(rows: Iterable[Sale]) -> dict[str, Decimal]:
    """Builds an intermediate result equivalent to a CTE."""
    monthly = {}

    for row in rows:
        monthly[row.sale_month] = monthly.get(
            row.sale_month, Decimal("0")
        ) + row.amount

    return dict(sorted(monthly.items()))


def window_running_totals(rows: Iterable[Sale]) -> list[dict]:
    """Equivalent to SUM(amount) OVER (
        PARTITION BY customer_id
        ORDER BY sale_month, sale_id
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )."""
    grouped = inner_join_sales_by_customer(rows)
    result = []

    for customer_id, customer_sales in grouped.items():
        running = Decimal("0")

        for sale in sorted(customer_sales, key=lambda item: (item.sale_month, item.sale_id)):
            running += sale.amount
            result.append(
                {
                    "customer_id": customer_id,
                    "customer_name": sale.customer_name,
                    "sale_month": sale.sale_month,
                    "sale_id": sale.sale_id,
                    "amount": sale.amount,
                    "running_total": running,
                }
            )

    return sorted(result, key=lambda item: (item["customer_id"], item["sale_month"], item["sale_id"]))


def window_rank_by_region(rows: Iterable[Sale]) -> list[dict]:
    """Implements a ROW_NUMBER-style ranking inside each region."""
    regional_totals: dict[str, dict[int, Decimal]] = {}

    for row in rows:
        regional_totals.setdefault(row.region, {})
        regional_totals[row.region][row.customer_id] = (
            regional_totals[row.region].get(row.customer_id, Decimal("0"))
            + row.amount
        )

    result = []

    for region, customer_totals in regional_totals.items():
        ranked = sorted(
            customer_totals.items(),
            key=lambda item: (-item[1], item[0]),
        )

        for position, (customer_id, total) in enumerate(ranked, start=1):
            result.append(
                {
                    "region": region,
                    "customer_id": customer_id,
                    "total": total,
                    "row_number": position,
                }
            )

    return result


def demonstrate() -> None:
    print("INNER JOIN-style customer grouping")
    for customer_id, rows in inner_join_sales_by_customer(SALES).items():
        print(customer_id, len(rows), "sales")

    print("\nLEFT JOIN-style customer totals")
    for customer_id, total in left_join_customer_totals(SALES).items():
        print(customer_id, total)

    print("\nSubquery-style customers at or above average")
    for customer_id, total in correlated_subquery_top_customers(SALES):
        print(customer_id, total)

    print("\nCTE-style monthly aggregation")
    for month, total in cte_style_monthly_totals(SALES).items():
        print(month, total)

    print("\nWindow running totals")
    for row in window_running_totals(SALES):
        print(row)

    print("\nWindow ranking by region")
    for row in window_rank_by_region(SALES):
        print(row)


if __name__ == "__main__":
    demonstrate()
