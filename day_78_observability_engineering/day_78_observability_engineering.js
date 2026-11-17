'use strict';

/**
 * Observability Engineering
 *
 * Event-driven observability collector implementing:
 * - Structured logging
 * - Counters, gauges, and histograms
 * - Distributed tracing
 * - Trace context propagation
 * - Asynchronous telemetry processing
 * - Alert evaluation and state transitions
 * - Telemetry aggregation and export
 *
 * Runtime: Node.js 18+
 * Dependencies: None
 */

const crypto = require('node:crypto');
const fs = require('node:fs/promises');
const path = require('node:path');
const EventEmitter = require('node:events');

// ============================================================
// 1. DOMAIN CONSTANTS AND ERRORS
// ============================================================

const LogLevel = Object.freeze({
    DEBUG: 10,
    INFO: 20,
    WARN: 30,
    ERROR: 40,
    CRITICAL: 50
});

const SpanStatus = Object.freeze({
    UNSET: 'UNSET',
    OK: 'OK',
    ERROR: 'ERROR'
});

const AlertState = Object.freeze({
    NORMAL: 'NORMAL',
    FIRING: 'FIRING',
    RESOLVED: 'RESOLVED'
});

const MetricType = Object.freeze({
    COUNTER: 'COUNTER',
    GAUGE: 'GAUGE',
    HISTOGRAM: 'HISTOGRAM'
});

class ObservabilityError extends Error {}

class ValidationError extends ObservabilityError {}

class CapacityError extends ObservabilityError {}

class StorageError extends ObservabilityError {}

// ============================================================
// 2. VALIDATION
// ============================================================

function validateName(value, field) {
    if (
        typeof value !== 'string' ||
        value.length === 0 ||
        value.length > 128 ||
        !/^[A-Za-z0-9_.:/-]+$/.test(value)
    ) {
        throw new ValidationError(`Invalid ${field}: ${value}`);
    }
}

function validateNumber(value, field) {
    if (
        typeof value !== 'number' ||
        !Number.isFinite(value)
    ) {
        throw new ValidationError(`${field} must be finite.`);
    }

    return value;
}

function createId(bytes = 16) {
    return crypto.randomBytes(bytes).toString('hex');
}

function timestamp() {
    return new Date().toISOString();
}

// ============================================================
// 3. SECURITY AND REDACTION
// ============================================================

class Redactor {
    static sensitiveKeys = new Set([
        'password',
        'token',
        'access_token',
        'refresh_token',
        'authorization',
        'secret',
        'api_key',
        'credit_card',
        'ssn'
    ]);

    static redact(value, key = '') {
        if (Redactor.sensitiveKeys.has(key.toLowerCase())) {
            return '[REDACTED]';
        }

        if (Array.isArray(value)) {
            return value.map(item => Redactor.redact(item));
        }

        if (value !== null && typeof value === 'object') {
            const result = Object.create(null);

            for (const [field, item] of Object.entries(value)) {
                result[field] = Redactor.redact(item, field);
            }

            return result;
        }

        if (typeof value === 'string') {
            return value
                .replace(
                    /(\bAuthorization\s*[:=]\s*)(Bearer\s+)?[^\s,;]+/gi,
                    '$1[REDACTED]'
                )
                .replace(
                    /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g,
                    '[REDACTED_EMAIL]'
                );
        }

        return value;
    }
}

// ============================================================
// 4. STRUCTURED LOGGING
// ============================================================

class LogCollector {
    constructor(service, options = {}) {
        validateName(service, 'service');

        this.service = service;
        this.records = [];
        this.capacity = options.capacity ?? 10000;
        this.minimumLevel = options.minimumLevel ?? LogLevel.DEBUG;

        if (!Number.isInteger(this.capacity) || this.capacity < 1) {
            throw new ValidationError('Invalid log capacity.');
        }
    }

    write(level, message, context = {}) {
        if (!Object.values(LogLevel).includes(level)) {
            throw new ValidationError('Invalid log level.');
        }

        if (level < this.minimumLevel) {
            return null;
        }

        if (
            typeof message !== 'string' ||
            message.trim().length === 0 ||
            message.length > 4096
        ) {
            throw new ValidationError('Invalid log message.');
        }

        if (this.records.length >= this.capacity) {
            throw new CapacityError('Log buffer is full.');
        }

        const record = Object.freeze({
            timestamp: timestamp(),
            service: this.service,
            level,
            message: Redactor.redact(message),
            traceId: context.traceId ?? null,
            spanId: context.spanId ?? null,
            attributes: Redactor.redact(context.attributes ?? {})
        });

        this.records.push(record);
        return record;
    }

    search(predicate) {
        if (typeof predicate !== 'function') {
            throw new ValidationError('Predicate must be a function.');
        }

        return this.records.filter(predicate);
    }

    searchByTrace(traceId) {
        return this.search(record => record.traceId === traceId);
    }

    export() {
        return this.records.map(record => ({
            ...record,
            level: Object.keys(LogLevel).find(
                key => LogLevel[key] === record.level
            )
        }));
    }
}

// ============================================================
// 5. METRIC REGISTRY
// ============================================================

function canonicalLabels(labels = {}) {
    if (
        labels === null ||
        typeof labels !== 'object' ||
        Array.isArray(labels)
    ) {
        throw new ValidationError('Labels must be an object.');
    }

    const entries = Object.entries(labels).sort(
        ([a], [b]) => a.localeCompare(b)
    );

    if (entries.length > 20) {
        throw new ValidationError('Metric label limit exceeded.');
    }

    for (const [key, value] of entries) {
        validateName(key, 'label key');

        if (
            typeof value !== 'string' ||
            value.length > 128
        ) {
            throw new ValidationError('Invalid label value.');
        }
    }

    return JSON.stringify(entries);
}

class MetricRegistry {
    constructor() {
        this.series = new Map();
    }

    register(name, type, service, labels = {}) {
        validateName(name, 'metric name');
        validateName(service, 'service');

        if (!Object.values(MetricType).includes(type)) {
            throw new ValidationError('Invalid metric type.');
        }

        const labelKey = canonicalLabels(labels);
        const key = `${name}|${service}|${labelKey}`;

        if (!this.series.has(key)) {
            this.series.set(key, {
                name,
                type,
                service,
                labels: structuredClone(labels),
                value: 0,
                observations: []
            });
        } else if (this.series.get(key).type !== type) {
            throw new ValidationError('Metric type conflict.');
        }

        return this.series.get(key);
    }

    increment(name, service, amount = 1, labels = {}) {
        amount = validateNumber(amount, 'counter increment');

        if (amount < 0) {
            throw new ValidationError('Counter cannot decrease.');
        }

        const metric = this.register(
            name,
            MetricType.COUNTER,
            service,
            labels
        );

        metric.value += amount;
        return metric.value;
    }

    gauge(name, service, value, labels = {}) {
        value = validateNumber(value, 'gauge value');

        const metric = this.register(
            name,
            MetricType.GAUGE,
            service,
            labels
        );

        metric.value = value;
        return metric.value;
    }

    observe(name, service, value, labels = {}) {
        value = validateNumber(value, 'histogram value');

        if (value < 0) {
            throw new ValidationError('Negative duration.');
        }

        const metric = this.register(
            name,
            MetricType.HISTOGRAM,
            service,
            labels
        );

        metric.observations.push(value);
    }

    percentile(values, percentile) {
        if (
            values.length === 0 ||
            percentile < 0 ||
            percentile > 100
        ) {
            throw new ValidationError('Invalid percentile calculation.');
        }

        const sorted = [...values].sort((a, b) => a - b);
        const position = (sorted.length - 1) * percentile / 100;
        const lower = Math.floor(position);
        const upper = Math.ceil(position);

        return sorted[lower] +
            (sorted[upper] - sorted[lower]) *
            (position - lower);
    }

    histogramSummary(name, service, labels = {}) {
        const key = `${name}|${service}|${canonicalLabels(labels)}`;
        const metric = this.series.get(key);

        if (
            !metric ||
            metric.type !== MetricType.HISTOGRAM ||
            metric.observations.length === 0
        ) {
            throw new ValidationError('Histogram unavailable.');
        }

        const values = metric.observations;
        const sum = values.reduce((a, b) => a + b, 0);

        return {
            count: values.length,
            sum,
            average: sum / values.length,
            p50: this.percentile(values, 50),
            p95: this.percentile(values, 95),
            p99: this.percentile(values, 99),
            min: Math.min(...values),
            max: Math.max(...values)
        };
    }

    snapshot() {
        return [...this.series.values()].map(metric => ({
            ...metric,
            observations: [...metric.observations]
        }));
    }
}

// ============================================================
// 6. DISTRIBUTED TRACING
// ============================================================

class Span {
    constructor(traceId, service, operation, parentSpanId, attributes) {
        this.traceId = traceId;
        this.spanId = createId(8);
        this.parentSpanId = parentSpanId;
        this.service = service;
        this.operation = operation;
        this.startTime = process.hrtime.bigint();
        this.endTime = null;
        this.status = SpanStatus.UNSET;
        this.attributes = Redactor.redact(attributes);
        this.events = [];
    }

    get durationMs() {
        if (this.endTime === null) {
            return null;
        }

        return Number(this.endTime - this.startTime) / 1e6;
    }

    addEvent(name, attributes = {}) {
        if (this.endTime !== null) {
            throw new ValidationError('Cannot modify completed span.');
        }

        validateName(name, 'span event');

        this.events.push({
            name,
            timestamp: timestamp(),
            attributes: Redactor.redact(attributes)
        });
    }

    finish(status = SpanStatus.OK) {
        if (this.endTime !== null) {
            throw new ValidationError('Span already completed.');
        }

        if (!Object.values(SpanStatus).includes(status)) {
            throw new ValidationError('Invalid span status.');
        }

        this.endTime = process.hrtime.bigint();
        this.status = status;
    }

    toJSON() {
        return {
            traceId: this.traceId,
            spanId: this.spanId,
            parentSpanId: this.parentSpanId,
            service: this.service,
            operation: this.operation,
            durationMs: this.durationMs,
            status: this.status,
            attributes: this.attributes,
            events: this.events
        };
    }
}

class Trace {
    constructor() {
        this.traceId = createId(16);
        this.spans = new Map();
    }

    startSpan(service, operation, parentSpanId = null, attributes = {}) {
        validateName(service, 'service');
        validateName(operation, 'operation');

        if (parentSpanId !== null) {
            const parent = this.spans.get(parentSpanId);

            if (!parent) {
                throw new ValidationError('Parent span not found.');
            }

            if (parent.endTime !== null) {
                throw new ValidationError('Parent span is completed.');
            }
        }

        const span = new Span(
            this.traceId,
            service,
            operation,
            parentSpanId,
            attributes
        );

        this.spans.set(span.spanId, span);
        return span;
    }

    validate() {
        for (const span of this.spans.values()) {
            if (span.endTime === null) {
                throw new ValidationError('Trace contains active spans.');
            }

            if (
                span.parentSpanId !== null &&
                !this.spans.has(span.parentSpanId)
            ) {
                throw new ValidationError('Invalid parent relationship.');
            }

            const visited = new Set();
            let current = span;

            while (current.parentSpanId !== null) {
                if (visited.has(current.spanId)) {
                    throw new ValidationError('Trace cycle detected.');
                }

                visited.add(current.spanId);
                current = this.spans.get(current.parentSpanId);

                if (!current) {
                    throw new ValidationError('Broken span reference.');
                }
            }
        }

        return true;
    }

    export() {
        return {
            traceId: this.traceId,
            spans: [...this.spans.values()].map(
                span => span.toJSON()
            )
        };
    }
}

// ============================================================
// 7. ASYNCHRONOUS TELEMETRY PROCESSING
// ============================================================

class TelemetryPipeline extends EventEmitter {
    constructor(options = {}) {
        super();

        this.queue = [];
        this.maximumQueueSize = options.maximumQueueSize ?? 5000;
        this.batchSize = options.batchSize ?? 100;
        this.processed = 0;
        this.dropped = 0;
        this.closed = false;
        this.processing = false;
    }

    publish(event) {
        if (this.closed) {
            throw new ObservabilityError('Pipeline is closed.');
        }

        if (this.queue.length >= this.maximumQueueSize) {
            this.dropped++;
            this.emit('dropped', {
                timestamp: timestamp(),
                totalDropped: this.dropped
            });

            return false;
        }

        this.queue.push(Object.freeze({
            timestamp: timestamp(),
            ...event
        }));

        this.emit('published', event);
        return true;
    }

    async flush() {
        if (this.processing) {
            return;
        }

        this.processing = true;

        try {
            while (this.queue.length > 0) {
                const batch = this.queue.splice(
                    0,
                    this.batchSize
                );

                try {
                    await this.processBatch(batch);
                    this.processed += batch.length;
                    this.emit('batchProcessed', batch.length);
                } catch (error) {
                    // Restore failed events without exceeding capacity.
                    this.queue.unshift(...batch);
                    this.emit('processingError', error);
                    throw error;
                }
            }
        } finally {
            this.processing = false;
        }
    }

    async processBatch(batch) {
        if (!Array.isArray(batch)) {
            throw new ValidationError('Batch must be an array.');
        }

        for (const event of batch) {
            if (!event.type) {
                throw new ValidationError('Telemetry type is required.');
            }
        }

        // Represents an asynchronous exporter boundary.
        await Promise.resolve();

        return batch.length;
    }

    async close() {
        await this.flush();
        this.closed = true;
        this.emit('closed');
    }
}

// ============================================================
// 8. ALERT EVALUATION ENGINE
// ============================================================

class AlertRule {
    constructor({
        name,
        metric,
        operator,
        threshold,
        windowSize = 1
    }) {
        validateName(name, 'alert name');
        validateName(metric, 'metric name');

        if (!['>', '>=', '<', '<='].includes(operator)) {
            throw new ValidationError('Invalid comparison operator.');
        }

        validateNumber(threshold, 'alert threshold');

        if (!Number.isInteger(windowSize) || windowSize < 1) {
            throw new ValidationError('Invalid evaluation window.');
        }

        this.name = name;
        this.metric = metric;
        this.operator = operator;
        this.threshold = threshold;
        this.windowSize = windowSize;
    }
}

class AlertEngine extends EventEmitter {
    constructor() {
        super();

        this.rules = new Map();
        this.history = new Map();
        this.states = new Map();
    }

    addRule(rule) {
        if (!(rule instanceof AlertRule)) {
            throw new ValidationError('Expected AlertRule.');
        }

        if (this.rules.has(rule.name)) {
            throw new ValidationError('Duplicate alert rule.');
        }

        this.rules.set(rule.name, rule);
        this.history.set(rule.name, []);
        this.states.set(rule.name, AlertState.NORMAL);
    }

    evaluate(name, value) {
        const rule = this.rules.get(name);

        if (!rule) {
            throw new ValidationError('Unknown alert rule.');
        }

        validateNumber(value, 'alert value');

        const values = this.history.get(name);
        values.push(value);

        while (values.length > rule.windowSize) {
            values.shift();
        }

        if (values.length < rule.windowSize) {
            return this.states.get(name);
        }

        const average = values.reduce((a, b) => a + b, 0) /
            values.length;

        const comparison = {
            '>': average > rule.threshold,
            '>=': average >= rule.threshold,
            '<': average < rule.threshold,
            '<=': average <= rule.threshold
        };

        const nextState = comparison[rule.operator]
            ? AlertState.FIRING
            : AlertState.NORMAL;

        const previousState = this.states.get(name);

        if (nextState !== previousState) {
            this.states.set(name, nextState);

            this.emit('transition', {
                rule: name,
                previousState,
                state: nextState,
                average,
                threshold: rule.threshold,
                timestamp: timestamp()
            });
        }

        return nextState;
    }
}

// ============================================================
// 9. OBSERVABILITY APPLICATION
// ============================================================

class ObservabilityApplication {
    constructor() {
        this.loggers = new Map();
        this.metrics = new MetricRegistry();
        this.pipeline = new TelemetryPipeline({
            maximumQueueSize: 5000,
            batchSize: 100
        });
        this.alerts = new AlertEngine();
        this.traces = new Map();

        this.alerts.on('transition', event => {
            this.logger('alert-manager').write(
                event.state === AlertState.FIRING
                    ? LogLevel.ERROR
                    : LogLevel.INFO,
                `Alert ${event.rule}: ${event.state}`,
                {
                    attributes: event
                }
            );
        });

        this.pipeline.on('dropped', event => {
            this.logger('telemetry-pipeline').write(
                LogLevel.ERROR,
                'Telemetry capacity exceeded',
                { attributes: event }
            );
        });
    }

    logger(service) {
        validateName(service, 'service');

        if (!this.loggers.has(service)) {
            this.loggers.set(
                service,
                new LogCollector(service)
            );
        }

        return this.loggers.get(service);
    }

    createTrace() {
        const trace = new Trace();
        this.traces.set(trace.traceId, trace);
        return trace;
    }

    correlate(traceId) {
        const logs = [];

        for (const logger of this.loggers.values()) {
            logs.push(...logger.searchByTrace(traceId));
        }

        const trace = this.traces.get(traceId);

        return {
            traceId,
            logs,
            trace: trace ? trace.export() : null
        };
    }

    async exportToFile(filename) {
        const safeName = path.basename(filename);

        if (
            !safeName ||
            safeName !== filename ||
            !safeName.endsWith('.json')
        ) {
            throw new ValidationError('Invalid export filename.');
        }

        const document = {
            exportedAt: timestamp(),
            logs: [...this.loggers.values()].flatMap(
                logger => logger.export()
            ),
            metrics: this.metrics.snapshot(),
            traces: [...this.traces.values()].map(
                trace => trace.export()
            )
        };

        const output = path.resolve(process.cwd(), safeName);
        const temporary = `${output}.tmp`;

        try {
            await fs.writeFile(
                temporary,
                JSON.stringify(document, null, 2),
                { encoding: 'utf8', flag: 'wx', mode: 0o600 }
            );

            await fs.rename(temporary, output);
            return output;
        } catch (error) {
            await fs.rm(temporary, { force: true }).catch(() => {});

            throw new StorageError(
                `Telemetry export failed: ${error.message}`
            );
        }
    }
}

// ============================================================
// 10. REALISTIC PAYMENT SERVICE
// ============================================================

async function executePayment(app, amount, fail = false) {
    validateNumber(amount, 'payment amount');

    if (amount <= 0 || amount > 1_000_000) {
        throw new ValidationError('Payment amount outside limits.');
    }

    const trace = app.createTrace();
    const logger = app.logger('payment-api');

    const root = trace.startSpan(
        'payment-api',
        'POST /payments',
        null,
        { amount }
    );

    logger.write(
        LogLevel.INFO,
        'Payment request received',
        {
            traceId: trace.traceId,
            spanId: root.spanId,
            attributes: { amount }
        }
    );

    app.metrics.increment(
        'payment_requests_total',
        'payment-api'
    );

    const database = trace.startSpan(
        'payment-database',
        'INSERT payment',
        root.spanId
    );

    database.finish();

    const processor = trace.startSpan(
        'payment-processor',
        'authorize payment',
        root.spanId
    );

    if (fail) {
        processor.finish(SpanStatus.ERROR);
        root.finish(SpanStatus.ERROR);

        logger.write(
            LogLevel.ERROR,
            'Payment authorization failed',
            {
                traceId: trace.traceId,
                spanId: processor.spanId,
                attributes: {
                    errorCode: 'PAYMENT_DECLINED'
                }
            }
        );

        app.metrics.increment(
            'payment_failures_total',
            'payment-api'
        );
    } else {
        processor.finish();
        root.finish();

        logger.write(
            LogLevel.INFO,
            'Payment completed',
            {
                traceId: trace.traceId,
                spanId: root.spanId
            }
        );

        app.metrics.increment(
            'payment_success_total',
            'payment-api'
        );
    }

    app.metrics.observe(
        'payment_latency_ms',
        'payment-api',
        fail ? 250 : 125
    );

    trace.validate();

    app.pipeline.publish({
        type: 'trace',
        traceId: trace.traceId
    });

    return trace.traceId;
}

// ============================================================
// 11. TESTS
// ============================================================

async function runTests() {
    const app = new ObservabilityApplication();

    const successId = await executePayment(app, 1500);
    const failureId = await executePayment(app, 2500, true);

    const successfulCorrelation = app.correlate(successId);
    const failedCorrelation = app.correlate(failureId);

    console.assert(
        successfulCorrelation.logs.length === 2,
        'Successful request correlation failed.'
    );

    console.assert(
        failedCorrelation.logs.some(
            log => log.level === LogLevel.ERROR
        ),
        'Failed request was not correlated.'
    );

    const securityLog = app.logger('security').write(
        LogLevel.WARNING,
        'Credential validation',
        {
            attributes: {
                password: 'confidential',
                username: 'operator'
            }
        }
    );

    console.assert(
        securityLog.attributes.password === '[REDACTED]',
        'Sensitive data was not redacted.'
    );

    app.metrics.gauge(
        'active_connections',
        'payment-api',
        12
    );

    app.metrics.observe('test_latency', 'test', 10);
    app.metrics.observe('test_latency', 'test', 20);
    app.metrics.observe('test_latency', 'test', 30);

    const histogram = app.metrics.histogramSummary(
        'test_latency',
        'test'
    );

    console.assert(histogram.count === 3);
    console.assert(histogram.p50 === 20);

    const rule = new AlertRule({
        name: 'high_latency',
        metric: 'payment_latency_ms',
        operator: '>',
        threshold: 200,
        windowSize: 2
    });

    app.alerts.addRule(rule);

    const transitions = [];

    app.alerts.on('transition', event => {
        transitions.push(event);
    });

    app.alerts.evaluate('high_latency', 220);
    app.alerts.evaluate('high_latency', 240);
    app.alerts.evaluate('high_latency', 100);
    app.alerts.evaluate('high_latency', 120);

    console.assert(
        transitions.length === 2,
        'Alert transitions were not generated correctly.'
    );

    // Demonstrate queue processing and backpressure.
    await app.pipeline.flush();

    console.assert(
        app.pipeline.processed === 2,
        'Telemetry batch processing failed.'
    );

    // Validate malformed input.
    try {
        await executePayment(app, -50);
        throw new Error('Invalid payment was accepted.');
    } catch (error) {
        if (!(error instanceof ValidationError)) {
            throw error;
        }
    }

    // Validate closed-pipeline behavior.
    await app.pipeline.close();

    try {
        app.pipeline.publish({ type: 'log' });
        throw new Error('Closed pipeline accepted telemetry.');
    } catch (error) {
        if (!(error instanceof ObservabilityError)) {
            throw error;
        }
    }

    console.log('\nOBSERVABILITY REPORT');
    console.log('====================');

    console.log('\nMetrics:');

    for (const metric of app.metrics.snapshot()) {
        console.log(metric);
    }

    console.log('\nLatency distribution:');
    console.log(histogram);

    console.log('\nAlert transitions:');
    console.log(transitions);

    console.log('\nTrace correlation:');
    console.log(app.correlate(successId));

    console.log('\nAll JavaScript observability tests passed.');

    return app;
}

// ============================================================
// 12. APPLICATION ENTRY POINT
// ============================================================

if (require.main === module) {
    runTests()
        .then(async app => {
            const output = await app.exportToFile(
                'observability-report.json'
            );

            console.log(`\nExported report: ${output}`);
        })
        .catch(error => {
            console.error('Execution failed:', error);
            process.exitCode = 1;
        });
}

module.exports = {
    LogCollector,
    MetricRegistry,
    Trace,
    Span,
    AlertRule,
    AlertEngine,
    TelemetryPipeline,
    ObservabilityApplication,
    executePayment
};
