'use strict';

/*
 * A read-heavy order dashboard often needs customer information together
 * with order information. This file models the normalization decision as
 * an event-driven policy evaluation rather than translating the Python
 * relation model.
 */

const EventEmitter = require('node:events');

class NormalizationPolicyError extends Error {}

class SchemaRegistry {
    constructor() {
        this.tables = new Map();
    }

    register(table) {
        if (this.tables.has(table.name)) {
            throw new NormalizationPolicyError(
                `Table already registered: ${table.name}`
            );
        }

        table.validate();
        this.tables.set(table.name, table);
        return table;
    }

    get(name) {
        const table = this.tables.get(name);
        if (!table) {
            throw new NormalizationPolicyError(`Unknown table: ${name}`);
        }
        return table;
    }
}

class TableSchema {
    constructor(name, columns, primaryKey) {
        this.name = name;
        this.columns = [...columns];
        this.primaryKey = [...primaryKey];
        this.rows = [];
        this.foreignKeys = [];
    }

    addForeignKey(column, targetTable, targetColumn) {
        this.foreignKeys.push({
            column,
            targetTable,
            targetColumn
        });
        return this;
    }

    insert(row) {
        const expected = new Set(this.columns);
        const actual = new Set(Object.keys(row));

        if (expected.size !== actual.size ||
            [...expected].some(column => !actual.has(column))) {
            throw new NormalizationPolicyError(
                `${this.name}: row does not match schema`
            );
        }

        for (const column of this.columns) {
            const value = row[column];

            // Arrays and objects represent structured/multivalued attributes
            // that should be separated when strict 1NF is required.
            if (Array.isArray(value) ||
                (value !== null && typeof value === 'object')) {
                throw new NormalizationPolicyError(
                    `${this.name}.${column}: non-atomic value`
                );
            }
        }

        const key = JSON.stringify(
            this.primaryKey.map(column => row[column])
        );

        const duplicate = this.rows.some(existing =>
            JSON.stringify(
                this.primaryKey.map(column => existing[column])
            ) === key
        );

        if (duplicate) {
            throw new NormalizationPolicyError(
                `${this.name}: duplicate primary key`
            );
        }

        this.rows.push({ ...row });
        return row;
    }

    validate() {
        if (!this.name || this.columns.length === 0) {
            throw new NormalizationPolicyError('Invalid table definition');
        }

        const uniqueColumns = new Set(this.columns);

        if (uniqueColumns.size !== this.columns.length) {
            throw new NormalizationPolicyError(
                `${this.name}: duplicate columns`
            );
        }

        for (const keyColumn of this.primaryKey) {
            if (!uniqueColumns.has(keyColumn)) {
                throw new NormalizationPolicyError(
                    `${this.name}: invalid primary key`
                );
            }
        }
    }
}

class NormalizationAnalyzer extends EventEmitter {
    constructor(registry) {
        super();
        this.registry = registry;
    }

    analyzeFunctionalDependencies(dependencies, candidateKey) {
        const key = new Set(candidateKey);
        const findings = [];

        for (const dependency of dependencies) {
            const determinant = new Set(dependency.determinant);
            const dependent = new Set(dependency.dependent);

            const isPartial =
                determinant.size < key.size &&
                [...determinant].every(column => key.has(column)) &&
                [...dependent].some(column => !key.has(column));

            findings.push({
                determinant: [...determinant],
                dependent: [...dependent],
                partialDependency: isPartial
            });

            if (isPartial) {
                this.emit('violation', {
                    normalForm: '2NF',
                    dependency
                });
            }
        }

        return findings;
    }

    analyzeTransitivity(dependencies, key) {
        const direct = new Map();

        for (const dependency of dependencies) {
            const determinant = dependency.determinant.join('|');
            direct.set(determinant, new Set(dependency.dependent));
        }

        const transitive = [];

        for (const first of dependencies) {
            if (first.determinant.length !== key.length ||
                !first.determinant.every(column => key.includes(column))) {
                continue;
            }

            for (const middle of first.dependent) {
                const downstream = direct.get(middle);

                if (downstream) {
                    for (const finalColumn of downstream) {
                        if (!key.includes(finalColumn)) {
                            transitive.push({
                                key,
                                via: middle,
                                dependent: finalColumn
                            });

                            this.emit('violation', {
                                normalForm: '3NF',
                                key,
                                via: middle,
                                dependent: finalColumn
                            });
                        }
                    }
                }
            }
        }

        return transitive;
    }
}

class DenormalizationAdvisor {
    static evaluate({ readFrequency, joinCost, updateFrequency, consistencyRisk }) {
        if (
            readFrequency < 0 ||
            joinCost < 0 ||
            updateFrequency < 0 ||
            consistencyRisk < 0
        ) {
            throw new RangeError('Metrics cannot be negative');
        }

        const readBenefit = readFrequency * joinCost;
        const writeRisk = updateFrequency * consistencyRisk;

        return {
            readBenefit,
            writeRisk,
            recommended: readBenefit > writeRisk * 2,
            rationale:
                readBenefit > writeRisk * 2
                    ? 'Read savings justify controlled redundancy.'
                    : 'Keep the normalized design unless measured evidence changes.'
        };
    }
}

function buildNormalizedOrderModel() {
    const customers = new TableSchema(
        'customer',
        ['customer_id', 'customer_name', 'city'],
        ['customer_id']
    );

    const orders = new TableSchema(
        'order',
        ['order_id', 'customer_id', 'amount'],
        ['order_id']
    );

    orders.addForeignKey('customer_id', 'customer', 'customer_id');

    customers.insert({
        customer_id: 1,
        customer_name: 'Nisha',
        city: 'Lucknow'
    });

    customers.insert({
        customer_id: 2,
        customer_name: 'Arjun',
        city: 'Delhi'
    });

    orders.insert({
        order_id: 9001,
        customer_id: 1,
        amount: 2500
    });

    orders.insert({
        order_id: 9002,
        customer_id: 2,
        amount: 1800
    });

    return { customers, orders };
}

function demonstrateEventDrivenReview() {
    const registry = new SchemaRegistry();

    const enrollment = new TableSchema(
        'enrollment',
        ['student_id', 'course_id', 'grade'],
        ['student_id', 'course_id']
    );

    registry.register(enrollment);

    const analyzer = new NormalizationAnalyzer(registry);

    analyzer.on('violation', event => {
        console.log(
            `[${event.normalForm}] normalization issue detected`,
            event
        );
    });

    const dependencies = [
        {
            determinant: ['student_id'],
            dependent: ['student_name']
        },
        {
            determinant: ['course_id'],
            dependent: ['course_name']
        },
        {
            determinant: ['student_id', 'course_id'],
            dependent: ['grade']
        }
    ];

    console.log(
        '2NF analysis:',
        analyzer.analyzeFunctionalDependencies(
            dependencies,
            ['student_id', 'course_id']
        )
    );

    const employeeDependencies = [
        {
            determinant: ['employee_id'],
            dependent: ['department_id']
        },
        {
            determinant: ['department_id'],
            dependent: ['department_name']
        }
    ];

    console.log(
        '3NF analysis:',
        analyzer.analyzeTransitivity(
            employeeDependencies,
            ['employee_id']
        )
    );
}

async function main() {
    console.log('NORMALIZATION POLICY EVALUATION');

    const model = buildNormalizedOrderModel();

    console.log('Customers:', model.customers.rows);
    console.log('Orders:', model.orders.rows);

    demonstrateEventDrivenReview();

    const decision = DenormalizationAdvisor.evaluate({
        readFrequency: 1000,
        joinCost: 4,
        updateFrequency: 10,
        consistencyRisk: 20
    });

    console.log('Denormalization decision:', decision);

    try {
        model.customers.insert({
            customer_id: 1,
            customer_name: 'Duplicate',
            city: 'Delhi'
        });
    } catch (error) {
        console.error('Expected constraint failure:', error.message);
    }

    try {
        model.customers.insert({
            customer_id: 3,
            customer_name: 'Ravi',
            city: ['Lucknow', 'Delhi']
        });
    } catch (error) {
        console.error('Expected 1NF failure:', error.message);
    }

    await Promise.resolve();
    console.log('Normalization evaluation completed.');
}

main().catch(error => {
    console.error('Fatal error:', error);
    process.exitCode = 1;
});
