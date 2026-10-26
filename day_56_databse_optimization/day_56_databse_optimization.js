'use strict';

/*
 * Database Optimization Case Study
 *
 * This implementation models query planning as an event-driven workload
 * analyzer. It evaluates access paths, joins, sorting, aggregation, and
 * optimization recommendations using JavaScript-specific Maps, Sets,
 * classes, Promises, and EventEmitter.
 */

const { EventEmitter } = require('node:events');

class ValidationError extends Error {
    constructor(message) {
        super(message);
        this.name = 'ValidationError';
    }
}

class ColumnStats {
    constructor(name, distinctValues, nullFraction = 0) {
        if (!name || distinctValues < 1 || nullFraction < 0 || nullFraction > 1) {
            throw new ValidationError(`Invalid statistics for column ${name}`);
        }

        this.name = name;
        this.distinctValues = distinctValues;
        this.nullFraction = nullFraction;
    }
}

class IndexDefinition {
    constructor(name, columns, { unique = false, covering = [] } = {}) {
        if (!name || !Array.isArray(columns) || columns.length === 0) {
            throw new ValidationError('An index requires a name and columns.');
        }

        this.name = name;
        this.columns = [...columns];
        this.unique = unique;
        this.covering = new Set(covering);
    }

    matches(column) {
        return this.columns[0] === column;
    }

    covers(columns) {
        const available = new Set([...this.columns, ...this.covering]);
        return columns.every(column => available.has(column));
    }
}

class TableStats {
    constructor(name, rows, pages, columns, indexes = []) {
        if (!name || rows < 1 || pages < 1) {
            throw new ValidationError('Invalid table statistics.');
        }

        this.name = name;
        this.rows = rows;
        this.pages = pages;
        this.columns = new Map(Object.entries(columns));
        this.indexes = indexes;
    }

    findIndex(column) {
        return this.indexes.find(index => index.matches(column));
    }
}

class Predicate {
    constructor(column, operator, value) {
        this.column = column;
        this.operator = operator;
        this.value = value;
    }

    selectivity(table) {
        const stats = table.columns.get(this.column);

        if (!stats) {
            return 0.1;
        }

        switch (this.operator) {
            case '=':
                return Math.max(1 / stats.distinctValues, 0.000001);
            case '<':
            case '<=':
            case '>':
            case '>=':
                return 0.33;
            case 'IS NULL':
                return Math.max(stats.nullFraction, 0.000001);
            case 'IS NOT NULL':
                return Math.max(1 - stats.nullFraction, 0.000001);
            case 'LIKE':
                return 0.05;
            default:
                return 0.25;
        }
    }
}

class QueryOptimizer {
    constructor() {
        this.seqPageCost = 1.0;
        this.randomPageCost = 4.0;
        this.cpuTupleCost = 0.01;
        this.cpuIndexTupleCost = 0.005;
    }

    estimateScan(table, predicates, projectedColumns) {
        let selectivity = 1.0;

        for (const predicate of predicates) {
            selectivity *= predicate.selectivity(table);
        }

        const estimatedRows = Math.max(1, table.rows * selectivity);
        const indexPredicates = predicates.filter(
            predicate => table.findIndex(predicate.column)
        );

        const usableIndex = indexPredicates.length > 0
            ? table.findIndex(indexPredicates[0].column)
            : null;

        const selectiveEnough = estimatedRows < table.rows * 0.20;

        if (usableIndex && selectiveEnough) {
            const covering = usableIndex.covers(projectedColumns);
            const accessPath = covering ? 'Index Only Scan' : 'Index Scan';

            const indexPages = Math.max(1, Math.log2(Math.max(table.pages, 2)));
            const heapPages = Math.min(
                table.pages,
                Math.max(1, estimatedRows / Math.max(table.rows / table.pages, 1))
            );

            const startupCost = indexPages * this.randomPageCost;
            const totalCost =
                startupCost +
                heapPages * this.randomPageCost +
                estimatedRows * this.cpuIndexTupleCost;

            return {
                table: table.name,
                accessPath,
                estimatedRows,
                startupCost,
                totalCost,
                reason: `Selective predicate (${(selectivity * 100).toFixed(4)}%) favors ${accessPath}.`
            };
        }

        const totalCost =
            table.pages * this.seqPageCost +
            table.rows * this.cpuTupleCost;

        return {
            table: table.name,
            accessPath: 'Sequential Scan',
            estimatedRows,
            startupCost: 0,
            totalCost,
            reason: usableIndex
                ? 'The available index is not selective enough under the cost model.'
                : 'No suitable predicate index is available.'
        };
    }

    chooseJoin(leftRows, rightRows, selectivity, indexedInner) {
        const outputRows = Math.max(1, leftRows * rightRows * selectivity);

        const nestedLoop =
            leftRows *
            (indexedInner
                ? Math.log2(Math.max(rightRows, 2))
                : rightRows) *
            0.01;

        const hashJoin = (leftRows + rightRows) * 0.03;

        const mergeJoin =
            (
                leftRows * Math.log2(Math.max(leftRows, 2)) +
                rightRows * Math.log2(Math.max(rightRows, 2))
            ) * 0.005;

        const candidates = [
            {
                algorithm: 'Nested Loop',
                cost: nestedLoop,
                reason: 'Useful when the outer relation is small or the inner side is indexed.'
            },
            {
                algorithm: 'Hash Join',
                cost: hashJoin,
                reason: 'Suitable for large equality joins when hashing fits the workload.'
            },
            {
                algorithm: 'Merge Join',
                cost: mergeJoin,
                reason: 'Useful when both inputs are already ordered or cheaply sortable.'
            }
        ];

        return {
            ...candidates.reduce((best, current) =>
                current.cost < best.cost ? current : best
            ),
            outputRows
        };
    }
}

class QueryPlan {
    constructor(sql, scans, joins, sortCost, aggregateCost) {
        this.sql = sql;
        this.scans = scans;
        this.joins = joins;
        this.sortCost = sortCost;
        this.aggregateCost = aggregateCost;
    }

    get totalCost() {
        return (
            this.scans.reduce((sum, scan) => sum + scan.totalCost, 0) +
            this.joins.reduce((sum, join) => sum + join.cost, 0) +
            this.sortCost +
            this.aggregateCost
        );
    }

    bottlenecks() {
        const findings = [];

        for (const scan of this.scans) {
            findings.push({
                cost: scan.totalCost,
                message: `${scan.table}: ${scan.reason}`
            });
        }

        for (const join of this.joins) {
            findings.push({
                cost: join.cost,
                message: `${join.algorithm}: ${join.reason}`
            });
        }

        findings.push({
            cost: this.sortCost,
            message: 'Sorting contributes to query cost.'
        });

        findings.push({
            cost: this.aggregateCost,
            message: 'Aggregation processes the joined result.'
        });

        return findings
            .filter(item => item.cost > 0)
            .sort((a, b) => b.cost - a.cost);
    }
}

class WorkloadAnalyzer extends EventEmitter {
    constructor(optimizer) {
        super();
        this.optimizer = optimizer;
        this.history = [];
    }

    async analyze(name, buildPlan) {
        this.emit('analysisStarted', { name });

        await new Promise(resolve => setImmediate(resolve));

        try {
            const plan = buildPlan();
            this.history.push({
                name,
                cost: plan.totalCost,
                timestamp: new Date().toISOString()
            });

            this.emit('analysisCompleted', {
                name,
                cost: plan.totalCost
            });

            return plan;
        } catch (error) {
            this.emit('analysisFailed', {
                name,
                error: error.message
            });
            throw error;
        }
    }
}

function createDatabase() {
    const orders = new TableStats(
        'orders',
        2500000,
        125000,
        {
            id: new ColumnStats('id', 2500000),
            customer_id: new ColumnStats('customer_id', 180000),
            status: new ColumnStats('status', 5),
            created_at: new ColumnStats('created_at', 900),
            total_amount: new ColumnStats('total_amount', 1000000)
        },
        [
            new IndexDefinition('orders_pkey', ['id'], { unique: true }),
            new IndexDefinition('idx_orders_customer', ['customer_id']),
            new IndexDefinition('idx_orders_created', ['created_at']),
            new IndexDefinition('idx_orders_status_created', ['status', 'created_at'])
        ]
    );

    const customers = new TableStats(
        'customers',
        180000,
        12000,
        {
            id: new ColumnStats('id', 180000),
            region: new ColumnStats('region', 8),
            customer_tier: new ColumnStats('customer_tier', 4),
            email: new ColumnStats('email', 180000)
        },
        [
            new IndexDefinition('customers_pkey', ['id'], { unique: true }),
            new IndexDefinition('idx_customers_region', ['region'])
        ]
    );

    return { orders, customers };
}

function createPlan(database, optimized) {
    const optimizer = new QueryOptimizer();

    let orders = database.orders;

    if (optimized) {
        orders = new TableStats(
            'orders',
            database.orders.rows,
            database.orders.pages,
            Object.fromEntries(database.orders.columns),
            [
                ...database.orders.indexes,
                new IndexDefinition(
                    'idx_orders_status_created_covering',
                    ['status', 'created_at'],
                    {
                        covering: ['customer_id', 'total_amount']
                    }
                )
            ]
        );
    }

    const orderScan = optimizer.estimateScan(
        orders,
        [
            new Predicate('status', '=', 'completed'),
            new Predicate('created_at', '>=', '2026-01-01')
        ],
        ['customer_id', 'total_amount']
    );

    const customerScan = optimizer.estimateScan(
        database.customers,
        [],
        ['id', 'region']
    );

    const join = optimizer.chooseJoin(
        orderScan.estimatedRows,
        customerScan.estimatedRows,
        1 / database.customers.rows,
        true
    );

    return new QueryPlan(
        `
SELECT c.region, SUM(o.total_amount)
FROM orders o
JOIN customers c ON c.id = o.customer_id
WHERE o.status = 'completed'
  AND o.created_at >= DATE '2026-01-01'
GROUP BY c.region
ORDER BY SUM(o.total_amount) DESC;
        `.trim(),
        [orderScan, customerScan],
        [join],
        join.outputRows * Math.log2(Math.max(join.outputRows, 2)) * 0.02,
        join.outputRows * 0.02
    );
}

async function main() {
    const database = createDatabase();
    const analyzer = new WorkloadAnalyzer(new QueryOptimizer());

    analyzer.on('analysisStarted', event =>
        console.log(`Analysis started: ${event.name}`)
    );

    analyzer.on('analysisCompleted', event =>
        console.log(`Analysis completed: ${event.name}, cost=${event.cost.toFixed(2)}`)
    );

    analyzer.on('analysisFailed', event =>
        console.error(`Analysis failed: ${event.name}: ${event.error}`)
    );

    const before = await analyzer.analyze(
        'baseline-query',
        () => createPlan(database, false)
    );

    const after = await analyzer.analyze(
        'optimized-query',
        () => createPlan(database, true)
    );

    console.log('\nBASELINE');
    console.log('='.repeat(72));
    console.log(`Cost: ${before.totalCost.toFixed(2)}`);
    console.table(before.scans);

    console.log('\nOPTIMIZED');
    console.log('='.repeat(72));
    console.log(`Cost: ${after.totalCost.toFixed(2)}`);
    console.table(after.scans);

    const improvement =
        ((before.totalCost - after.totalCost) / before.totalCost) * 100;

    console.log(`\nEstimated cost change: ${improvement.toFixed(2)}%`);

    console.log('\nBOTTLENECKS');
    for (const [index, item] of after.bottlenecks().slice(0, 5).entries()) {
        console.log(`${index + 1}. ${item.message}`);
    }

    // Security boundary: values should be passed as parameterized query
    // parameters when this model is connected to a real database.
    console.log('\nSECURITY CHECKS');
    console.log('Use parameterized SQL rather than string interpolation.');
    console.log('Restrict EXPLAIN ANALYZE access when executing arbitrary statements.');
    console.log('Avoid granting application roles permission to create arbitrary indexes.');
}

main().catch(error => {
    console.error(error);
    process.exitCode = 1;
});
