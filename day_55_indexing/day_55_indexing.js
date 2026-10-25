'use strict';

/*
 * Indexing and Query Performance
 *
 * This program models an event-driven query service with:
 * - B-tree-like composite indexes
 * - covering indexes
 * - partial indexes
 * - query-plan selection
 * - index maintenance events
 * - validation and failure handling
 *
 * Run with:
 * node indexing-performance.js
 */

const EventEmitter = require('node:events');

const ScanType = Object.freeze({
    SEQUENTIAL: 'sequential_scan',
    INDEX: 'index_scan',
    INDEX_ONLY: 'index_only_scan'
});

class ValidationError extends Error {
    constructor(message) {
        super(message);
        this.name = 'ValidationError';
    }
}

class Query {
    constructor(filters, selectedColumns) {
        if (!filters || typeof filters !== 'object') {
            throw new ValidationError('filters must be an object');
        }

        if (!Array.isArray(selectedColumns) || selectedColumns.length === 0) {
            throw new ValidationError('selectedColumns must not be empty');
        }

        this.filters = Object.freeze({ ...filters });
        this.selectedColumns = Object.freeze([...selectedColumns]);
    }
}

class BTreeIndex {
    constructor({ name, columns, includedColumns = [], predicate = null }) {
        if (!name || !Array.isArray(columns) || columns.length === 0) {
            throw new ValidationError('An index requires a name and key columns');
        }

        this.name = name;
        this.columns = Object.freeze([...columns]);
        this.includedColumns = Object.freeze([...includedColumns]);
        this.predicate = predicate;
        this.entries = [];
    }

    applicable(row, filters) {
        if (!this.predicate) {
            return true;
        }

        return filters[this.predicate.column] === this.predicate.value ||
               row[this.predicate.column] === this.predicate.value;
    }

    matchesEqualityPrefix(filters) {
        let matched = 0;

        for (const column of this.columns) {
            if (Object.prototype.hasOwnProperty.call(filters, column)) {
                matched++;
            } else {
                break;
            }
        }

        return matched > 0;
    }

    covers(columns) {
        const available = new Set([
            ...this.columns,
            ...this.includedColumns
        ]);

        return columns.every(column => available.has(column));
    }

    keyFor(row) {
        return this.columns.map(column => row[column]).join('\u0001');
    }

    add(row) {
        this.entries.push({
            key: this.keyFor(row),
            rowId: row.orderId
        });
    }

    sort() {
        this.entries.sort((a, b) => a.key.localeCompare(b.key));
    }
}

class RepositoryDatabase extends EventEmitter {
    constructor() {
        super();

        this.rows = new Map();
        this.indexes = new Map();
        this.writeCount = 0;

        this.on('rowInserted', ({ row }) => {
            for (const index of this.indexes.values()) {
                if (index.applicable(row, {})) {
                    index.add(row);
                }
            }
        });
    }

    validateRow(row) {
        const required = [
            'orderId',
            'customerId',
            'status',
            'region',
            'totalAmount',
            'createdAt'
        ];

        for (const column of required) {
            if (!(column in row)) {
                throw new ValidationError(`Missing column: ${column}`);
            }
        }

        if (!Number.isInteger(row.orderId) || row.orderId <= 0) {
            throw new ValidationError('orderId must be a positive integer');
        }

        if (!Number.isInteger(row.customerId) || row.customerId <= 0) {
            throw new ValidationError('customerId must be a positive integer');
        }

        if (!['pending', 'paid', 'shipped', 'cancelled'].includes(row.status)) {
            throw new ValidationError(`Unsupported status: ${row.status}`);
        }

        if (typeof row.totalAmount !== 'number' || row.totalAmount < 0) {
            throw new ValidationError('totalAmount must be non-negative');
        }
    }

    insert(row) {
        this.validateRow(row);

        if (this.rows.has(row.orderId)) {
            throw new ValidationError(`Duplicate orderId: ${row.orderId}`);
        }

        const immutableRow = Object.freeze({ ...row });
        this.rows.set(row.orderId, immutableRow);
        this.writeCount++;

        this.emit('rowInserted', { row: immutableRow });
    }

    createIndex(config) {
        if (this.indexes.has(config.name)) {
            throw new ValidationError(`Index exists: ${config.name}`);
        }

        const index = new BTreeIndex(config);

        for (const row of this.rows.values()) {
            if (index.applicable(row, {})) {
                index.add(row);
            }
        }

        index.sort();
        this.indexes.set(index.name, index);

        this.emit('indexCreated', {
            name: index.name,
            columns: index.columns
        });
    }

    estimateSelectivity(filters) {
        if (Object.keys(filters).length === 0) {
            return 1;
        }

        let selectivity = 1;

        for (const [column, value] of Object.entries(filters)) {
            const rows = [...this.rows.values()];
            if (rows.length === 0) {
                return 0;
            }

            const matching = rows.filter(row => row[column] === value).length;
            selectivity *= matching / rows.length;
        }

        return Math.min(selectivity, 1);
    }

    explain(query) {
        const totalRows = this.rows.size;
        const sequentialCost = totalRows;

        const candidates = [];

        for (const index of this.indexes.values()) {
            if (!index.matchesEqualityPrefix(query.filters)) {
                continue;
            }

            const selectivity = this.estimateSelectivity(query.filters);
            const estimatedRows = Math.max(
                1,
                Math.floor(totalRows * selectivity)
            );

            let cost = 3 + estimatedRows * 0.8;
            let scanType = ScanType.INDEX;
            let reason = `${index.name} matches an equality prefix`;

            if (index.covers(query.selectedColumns)) {
                cost *= 0.75;
                scanType = ScanType.INDEX_ONLY;
                reason += ' and covers the requested columns';
            }

            candidates.push({
                scanType,
                indexName: index.name,
                estimatedRows,
                estimatedCost: cost,
                reason
            });
        }

        if (candidates.length === 0) {
            return {
                scanType: ScanType.SEQUENTIAL,
                indexName: null,
                estimatedRows: totalRows,
                estimatedCost: sequentialCost,
                reason: 'No usable index'
            };
        }

        candidates.sort((a, b) => a.estimatedCost - b.estimatedCost);
        const best = candidates[0];

        if (best.estimatedCost >= sequentialCost) {
            return {
                scanType: ScanType.SEQUENTIAL,
                indexName: null,
                estimatedRows: totalRows,
                estimatedCost: sequentialCost,
                reason: 'Sequential scan is estimated to be cheaper'
            };
        }

        return best;
    }

    execute(query) {
        const plan = this.explain(query);
        let candidateRows;

        if (plan.indexName) {
            const index = this.indexes.get(plan.indexName);
            candidateRows = index.entries
                .map(entry => this.rows.get(entry.rowId))
                .filter(Boolean);
        } else {
            candidateRows = [...this.rows.values()];
        }

        const rows = candidateRows
            .filter(row =>
                Object.entries(query.filters).every(
                    ([column, value]) => row[column] === value
                )
            )
            .map(row => {
                const result = {};
                for (const column of query.selectedColumns) {
                    result[column] = row[column];
                }
                return result;
            });

        this.emit('queryExecuted', {
            plan,
            resultCount: rows.length
        });

        return { plan, rows };
    }
}

function seedDatabase() {
    const db = new RepositoryDatabase();

    const statuses = ['pending', 'paid', 'shipped', 'cancelled'];
    const regions = ['north', 'south', 'east', 'west'];

    for (let orderId = 1; orderId <= 1000; orderId++) {
        db.insert({
            orderId,
            customerId: (orderId * 17) % 100 + 1,
            status: statuses[orderId % statuses.length],
            region: regions[orderId % regions.length],
            totalAmount: 100 + ((orderId * 37) % 4900),
            createdAt: `2026-10-${String((orderId % 28) + 1).padStart(2, '0')}`
        });
    }

    return db;
}

function main() {
    const db = seedDatabase();

    db.on('indexCreated', event => {
        console.log(`INDEX CREATED: ${event.name}`);
    });

    db.on('queryExecuted', event => {
        console.log(
            `EVENT queryExecuted: ${event.plan.scanType}, rows=${event.resultCount}`
        );
    });

    db.createIndex({
        name: 'idx_customer',
        columns: ['customerId']
    });

    db.createIndex({
        name: 'idx_status_region',
        columns: ['status', 'region'],
        includedColumns: ['totalAmount', 'createdAt']
    });

    db.createIndex({
        name: 'idx_customer_paid',
        columns: ['customerId'],
        includedColumns: ['totalAmount'],
        predicate: {
            column: 'status',
            value: 'paid'
        }
    });

    const queries = [
        new Query(
            { customerId: 42 },
            ['orderId', 'customerId', 'totalAmount']
        ),
        new Query(
            { status: 'paid', region: 'north' },
            ['orderId', 'totalAmount', 'createdAt']
        ),
        new Query(
            { region: 'north' },
            ['orderId', 'customerId']
        ),
        new Query(
            {},
            ['orderId', 'totalAmount']
        )
    ];

    for (const query of queries) {
        const { plan, rows } = db.execute(query);

        console.log('\nQUERY:', query.filters);
        console.log('PLAN:', plan);
        console.log('SAMPLE:', rows.slice(0, 3));
    }

    try {
        db.insert({
            orderId: 1001,
            customerId: 42,
            status: 'paid',
            region: 'north',
            totalAmount: 725.5,
            createdAt: '2026-10-25'
        });
    } catch (error) {
        console.error(`INSERT FAILED: ${error.message}`);
    }

    try {
        db.insert({
            orderId: 1002,
            customerId: 42,
            status: 'unknown',
            region: 'north',
            totalAmount: 100,
            createdAt: '2026-10-25'
        });
    } catch (error) {
        console.error(`VALIDATION FAILED: ${error.message}`);
    }

    console.log(`\nTABLE ROWS: ${db.rows.size}`);
    console.log(`BASE WRITES: ${db.writeCount}`);
    console.log(`INDEX COUNT: ${db.indexes.size}`);
}

main();
