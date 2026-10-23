'use strict';

/*
 * Advanced SQL concepts modeled through an event-driven analytics pipeline.
 * The JavaScript implementation deliberately emphasizes Map, Set, immutable
 * records, asynchronous processing, and composable transformations.
 */

const sales = Object.freeze([
  Object.freeze({ id: 1, customerId: 101, customer: 'Asha', region: 'North', product: 'Laptop', category: 'Electronics', amount: 1200, month: '2026-01' }),
  Object.freeze({ id: 2, customerId: 102, customer: 'Ravi', region: 'South', product: 'Phone', category: 'Electronics', amount: 850, month: '2026-01' }),
  Object.freeze({ id: 3, customerId: 103, customer: 'Meera', region: 'North', product: 'Desk', category: 'Furniture', amount: 450, month: '2026-01' }),
  Object.freeze({ id: 4, customerId: 101, customer: 'Asha', region: 'North', product: 'Monitor', category: 'Electronics', amount: 400, month: '2026-02' }),
  Object.freeze({ id: 5, customerId: 104, customer: 'Kabir', region: 'West', product: 'Chair', category: 'Furniture', amount: 300, month: '2026-02' }),
  Object.freeze({ id: 6, customerId: 102, customer: 'Ravi', region: 'South', product: 'Laptop', category: 'Electronics', amount: 1300, month: '2026-02' }),
  Object.freeze({ id: 7, customerId: 105, customer: 'Nisha', region: 'West', product: 'Phone', category: 'Electronics', amount: 900, month: '2026-03' }),
  Object.freeze({ id: 8, customerId: 103, customer: 'Meera', region: 'North', product: 'Chair', category: 'Furniture', amount: 280, month: '2026-03' }),
  Object.freeze({ id: 9, customerId: 101, customer: 'Asha', region: 'North', product: 'Phone', category: 'Electronics', amount: 820, month: '2026-03' }),
  Object.freeze({ id: 10, customerId: 104, customer: 'Kabir', region: 'West', product: 'Laptop', category: 'Electronics', amount: 1250, month: '2026-04' })
]);

function validateSales(rows) {
  if (!Array.isArray(rows)) {
    throw new TypeError('Sales input must be an array');
  }

  for (const row of rows) {
    if (!Number.isInteger(row.id) || row.id <= 0) {
      throw new Error(`Invalid sale id: ${row.id}`);
    }

    if (!Number.isFinite(row.amount) || row.amount < 0) {
      throw new Error(`Invalid amount for sale ${row.id}`);
    }

    if (!/^\d{4}-\d{2}$/.test(row.month)) {
      throw new Error(`Invalid month for sale ${row.id}`);
    }
  }
}

function innerJoin(leftRows, rightRows, leftKey, rightKey) {
  const index = new Map();

  for (const right of rightRows) {
    const key = right[rightKey];
    if (!index.has(key)) index.set(key, []);
    index.get(key).push(right);
  }

  return leftRows.flatMap(left => {
    const matches = index.get(left[leftKey]) ?? [];
    return matches.map(right => ({ left, right }));
  });
}

function groupBy(rows, keySelector) {
  const groups = new Map();

  for (const row of rows) {
    const key = keySelector(row);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(row);
  }

  return groups;
}

function aggregateCustomerTotals(rows) {
  return [...groupBy(rows, row => row.customerId)]
    .map(([customerId, customerRows]) => ({
      customerId,
      customer: customerRows[0].customer,
      total: customerRows.reduce((sum, row) => sum + row.amount, 0)
    }))
    .sort((a, b) => b.total - a.total);
}

function scalarSubqueryFilter(rows) {
  const totals = aggregateCustomerTotals(rows);
  const average = totals.reduce((sum, row) => sum + row.total, 0) / totals.length;

  return totals.filter(row => row.total >= average);
}

function cteStyleMonthlyAnalysis(rows) {
  const monthlyTotals = [...groupBy(rows, row => row.month)]
    .map(([month, monthRows]) => ({
      month,
      total: monthRows.reduce((sum, row) => sum + row.amount, 0)
    }))
    .sort((a, b) => a.month.localeCompare(b.month));

  const baseline = monthlyTotals.reduce((sum, row) => sum + row.total, 0) / monthlyTotals.length;

  return monthlyTotals.map(row => ({
    ...row,
    aboveAverage: row.total > baseline
  }));
}

function windowRunningTotal(rows) {
  const partitions = groupBy(rows, row => row.customerId);
  const result = [];

  for (const [customerId, customerRows] of partitions) {
    let runningTotal = 0;

    const ordered = [...customerRows].sort(
      (a, b) => a.month.localeCompare(b.month) || a.id - b.id
    );

    for (const row of ordered) {
      runningTotal += row.amount;

      result.push({
        customerId,
        customer: row.customer,
        month: row.month,
        saleId: row.id,
        amount: row.amount,
        runningTotal
      });
    }
  }

  return result.sort((a, b) =>
    a.customerId - b.customerId ||
    a.month.localeCompare(b.month) ||
    a.saleId - b.saleId
  );
}

function windowRankByRegion(rows) {
  const regions = groupBy(rows, row => row.region);
  const result = [];

  for (const [region, regionRows] of regions) {
    const customers = [...groupBy(regionRows, row => row.customerId)]
      .map(([customerId, customerRows]) => ({
        customerId,
        total: customerRows.reduce((sum, row) => sum + row.amount, 0)
      }))
      .sort((a, b) => b.total - a.total || a.customerId - b.customerId);

    customers.forEach((customer, index) => {
      result.push({
        region,
        customerId: customer.customerId,
        total: customer.total,
        rowNumber: index + 1
      });
    });
  }

  return result;
}

async function runAnalytics() {
  validateSales(sales);

  const customers = [
    { id: 101, name: 'Asha' },
    { id: 102, name: 'Ravi' },
    { id: 103, name: 'Meera' },
    { id: 104, name: 'Kabir' },
    { id: 105, name: 'Nisha' },
    { id: 106, name: 'Dev' }
  ];

  console.log('INNER JOIN');
  console.table(innerJoin(sales, customers, 'customerId', 'id'));

  console.log('SUBQUERY FILTER');
  console.table(scalarSubqueryFilter(sales));

  console.log('CTE-STYLE ANALYSIS');
  console.table(cteStyleMonthlyAnalysis(sales));

  console.log('WINDOW RUNNING TOTAL');
  console.table(windowRunningTotal(sales));

  console.log('WINDOW RANKING');
  console.table(windowRankByRegion(sales));
}

runAnalytics().catch(error => {
  console.error(`Analytics failed: ${error.message}`);
  process.exitCode = 1;
});
