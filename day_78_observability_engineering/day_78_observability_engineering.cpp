#include <algorithm>
#include <cmath>
#include <cstdint>
#include <deque>
#include <exception>
#include <iomanip>
#include <iostream>
#include <map>
#include <memory>
#include <numeric>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

/*
 * Observability Engineering
 *
 * C++17 observability engine for a distributed payment platform.
 *
 * Features:
 * - Structured logs
 * - Metric series and aggregation
 * - Histograms and percentile calculations
 * - Distributed traces and parent-child spans
 * - Trace correlation
 * - Alert rules and state transitions
 * - Service-level reporting
 * - Validation and failure handling
 *
 * Build:
 * g++ -std=c++17 -O2 -Wall -Wextra -pedantic observability.cpp -o observability
 */

namespace observability {

// ============================================================
// 1. ENUMERATIONS AND EXCEPTIONS
// ============================================================

enum class LogLevel {
    Debug,
    Info,
    Warning,
    Error,
    Critical
};

enum class MetricType {
    Counter,
    Gauge,
    Histogram
};

enum class SpanStatus {
    Unset,
    Ok,
    Error
};

enum class AlertState {
    Normal,
    Firing,
    Resolved
};

class ObservabilityException : public std::runtime_error {
public:
    explicit ObservabilityException(const std::string& message)
        : std::runtime_error(message) {}
};

class ValidationException : public ObservabilityException {
public:
    using ObservabilityException::ObservabilityException;
};

class CapacityException : public ObservabilityException {
public:
    using ObservabilityException::ObservabilityException;
};

// ============================================================
// 2. VALIDATION UTILITIES
// ============================================================

void validateName(
    const std::string& value,
    const std::string& field
) {
    if (value.empty() || value.size() > 128) {
        throw ValidationException("Invalid " + field);
    }

    for (unsigned char character : value) {
        const bool allowed =
            (character >= 'a' && character <= 'z') ||
            (character >= 'A' && character <= 'Z') ||
            (character >= '0' && character <= '9') ||
            character == '_' ||
            character == '-' ||
            character == '.' ||
            character == ':' ||
            character == '/';

        if (!allowed) {
            throw ValidationException("Invalid " + field);
        }
    }
}

void validateFinite(double value, const std::string& field) {
    if (!std::isfinite(value)) {
        throw ValidationException(field + " must be finite");
    }
}

std::string toString(LogLevel level) {
    switch (level) {
        case LogLevel::Debug: return "DEBUG";
        case LogLevel::Info: return "INFO";
        case LogLevel::Warning: return "WARNING";
        case LogLevel::Error: return "ERROR";
        case LogLevel::Critical: return "CRITICAL";
    }

    throw ValidationException("Unknown log level");
}

std::string toString(SpanStatus status) {
    switch (status) {
        case SpanStatus::Unset: return "UNSET";
        case SpanStatus::Ok: return "OK";
        case SpanStatus::Error: return "ERROR";
    }

    throw ValidationException("Unknown span status");
}

std::string toString(AlertState state) {
    switch (state) {
        case AlertState::Normal: return "NORMAL";
        case AlertState::Firing: return "FIRING";
        case AlertState::Resolved: return "RESOLVED";
    }

    throw ValidationException("Unknown alert state");
}

// ============================================================
// 3. STRUCTURED LOGGING
// ============================================================

using Attributes = std::map<std::string, std::string>;

struct LogRecord {
    std::string timestamp;
    LogLevel level;
    std::string service;
    std::string message;
    std::string traceId;
    std::string spanId;
    Attributes attributes;
};

class SecurityRedactor {
private:
    static const std::set<std::string>& sensitiveKeys() {
        static const std::set<std::string> keys = {
            "password",
            "token",
            "authorization",
            "api_key",
            "secret",
            "credit_card",
            "ssn"
        };

        return keys;
    }

public:
    static std::string redact(
        const std::string& key,
        const std::string& value
    ) {
        std::string normalized = key;

        std::transform(
            normalized.begin(),
            normalized.end(),
            normalized.begin(),
            [](unsigned char character) {
                return static_cast<char>(std::tolower(character));
            }
        );

        if (sensitiveKeys().count(normalized)) {
            return "[REDACTED]";
        }

        return value;
    }

    static Attributes sanitize(const Attributes& attributes) {
        Attributes result;

        for (const auto& [key, value] : attributes) {
            result[key] = redact(key, value);
        }

        return result;
    }
};

class Logger {
private:
    std::string service_;
    std::vector<LogRecord> records_;

public:
    explicit Logger(std::string service)
        : service_(std::move(service)) {
        validateName(service_, "service");
    }

    void write(
        LogLevel level,
        const std::string& message,
        const std::string& traceId = "",
        const std::string& spanId = "",
        const Attributes& attributes = {}
    ) {
        if (message.empty() || message.size() > 4096) {
            throw ValidationException("Invalid log message");
        }

        records_.push_back({
            "2026-11-17T10:00:00Z",
            level,
            service_,
            message,
            traceId,
            spanId,
            SecurityRedactor::sanitize(attributes)
        });
    }

    std::vector<LogRecord> findByTrace(
        const std::string& traceId
    ) const {
        std::vector<LogRecord> result;

        std::copy_if(
            records_.begin(),
            records_.end(),
            std::back_inserter(result),
            [&](const LogRecord& record) {
                return record.traceId == traceId;
            }
        );

        return result;
    }

    const std::vector<LogRecord>& records() const {
        return records_;
    }

    const std::string& service() const {
        return service_;
    }
};

// ============================================================
// 4. METRIC SERIES
// ============================================================

struct MetricKey {
    std::string name;
    std::string service;
    Attributes labels;

    bool operator<(const MetricKey& other) const {
        return std::tie(name, service, labels) <
               std::tie(other.name, other.service, other.labels);
    }
};

struct MetricSeries {
    MetricType type;
    double value = 0.0;
    std::vector<double> observations;
};

struct HistogramSummary {
    std::size_t count;
    double sum;
    double average;
    double minimum;
    double maximum;
    double p50;
    double p95;
    double p99;
};

class MetricRegistry {
private:
    std::map<MetricKey, MetricSeries> series_;

    MetricSeries& get(
        const MetricKey& key,
        MetricType type
    ) {
        auto iterator = series_.find(key);

        if (iterator == series_.end()) {
            return series_.emplace(
                key,
                MetricSeries{type, 0.0, {}}
            ).first->second;
        }

        if (iterator->second.type != type) {
            throw ValidationException("Metric type conflict");
        }

        return iterator->second;
    }

    static double percentile(
        std::vector<double> values,
        double percent
    ) {
        if (values.empty() || percent < 0 || percent > 100) {
            throw ValidationException("Invalid percentile");
        }

        std::sort(values.begin(), values.end());

        const double position =
            (values.size() - 1) * percent / 100.0;

        const auto lower = static_cast<std::size_t>(
            std::floor(position)
        );

        const auto upper = static_cast<std::size_t>(
            std::ceil(position)
        );

        const double fraction = position - lower;

        return values[lower] * (1 - fraction) +
               values[upper] * fraction;
    }

public:
    void increment(
        const std::string& name,
        const std::string& service,
        double amount = 1.0,
        const Attributes& labels = {}
    ) {
        validateName(name, "metric");
        validateName(service, "service");
        validateFinite(amount, "counter increment");

        if (amount < 0) {
            throw ValidationException("Counter cannot decrease");
        }

        MetricKey key{name, service, labels};

        get(key, MetricType::Counter).value += amount;
    }

    void setGauge(
        const std::string& name,
        const std::string& service,
        double value,
        const Attributes& labels = {}
    ) {
        validateName(name, "metric");
        validateName(service, "service");
        validateFinite(value, "gauge");

        MetricKey key{name, service, labels};

        get(key, MetricType::Gauge).value = value;
    }

    void observe(
        const std::string& name,
        const std::string& service,
        double value,
        const Attributes& labels = {}
    ) {
        validateName(name, "metric");
        validateName(service, "service");
        validateFinite(value, "observation");

        if (value < 0) {
            throw ValidationException("Negative duration");
        }

        MetricKey key{name, service, labels};

        get(key, MetricType::Histogram)
            .observations.push_back(value);
    }

    HistogramSummary summarize(
        const std::string& name,
        const std::string& service,
        const Attributes& labels = {}
    ) const {
        MetricKey key{name, service, labels};

        auto iterator = series_.find(key);

        if (iterator == series_.end() ||
            iterator->second.type != MetricType::Histogram ||
            iterator->second.observations.empty()) {
            throw ValidationException("Histogram unavailable");
        }

        const auto& values = iterator->second.observations;

        const double sum = std::accumulate(
            values.begin(),
            values.end(),
            0.0
        );

        const auto limits = std::minmax_element(
            values.begin(),
            values.end()
        );

        return {
            values.size(),
            sum,
            sum / values.size(),
            *limits.first,
            *limits.second,
            percentile(values, 50),
            percentile(values, 95),
            percentile(values, 99)
        };
    }

    const std::map<MetricKey, MetricSeries>& series() const {
        return series_;
    }
};

// ============================================================
// 5. DISTRIBUTED TRACE MODEL
// ============================================================

struct Span {
    std::string traceId;
    std::string spanId;
    std::optional<std::string> parentSpanId;
    std::string service;
    std::string operation;
    double startMs;
    double endMs = -1.0;
    SpanStatus status = SpanStatus::Unset;
    Attributes attributes;

    double durationMs() const {
        if (endMs < 0) {
            throw ValidationException("Span is incomplete");
        }

        return endMs - startMs;
    }
};

class Trace {
private:
    std::string traceId_;
    std::map<std::string, Span> spans_;
    std::uint64_t nextId_ = 1;

    static double currentTimeMs() {
        using Clock = std::chrono::steady_clock;

        return std::chrono::duration<double, std::milli>(
            Clock::now().time_since_epoch()
        ).count();
    }

public:
    explicit Trace(std::string traceId)
        : traceId_(std::move(traceId)) {}

    Span& startSpan(
        const std::string& service,
        const std::string& operation,
        const std::optional<std::string>& parentId = std::nullopt,
        const Attributes& attributes = {}
    ) {
        validateName(service, "service");
        validateName(operation, "operation");

        if (parentId.has_value()) {
            auto parent = spans_.find(*parentId);

            if (parent == spans_.end()) {
                throw ValidationException("Parent span missing");
            }

            if (parent->second.endMs >= 0) {
                throw ValidationException("Parent span completed");
            }
        }

        std::ostringstream identifier;
        identifier << std::hex << std::setw(16)
                   << std::setfill('0') << nextId_++;

        std::string spanId = identifier.str();

        auto [iterator, inserted] = spans_.emplace(
            spanId,
            Span{
                traceId_,
                spanId,
                parentId,
                service,
                operation,
                currentTimeMs(),
                -1.0,
                SpanStatus::Unset,
                attributes
            }
        );

        if (!inserted) {
            throw ObservabilityException("Duplicate span identifier");
        }

        return iterator->second;
    }

    void endSpan(
        const std::string& spanId,
        SpanStatus status = SpanStatus::Ok
    ) {
        auto iterator = spans_.find(spanId);

        if (iterator == spans_.end()) {
            throw ValidationException("Span not found");
        }

        if (iterator->second.endMs >= 0) {
            throw ValidationException("Span already completed");
        }

        iterator->second.endMs = currentTimeMs();
        iterator->second.status = status;
    }

    void validate() const {
        for (const auto& [id, span] : spans_) {
            if (span.endMs < 0) {
                throw ValidationException("Active span remains");
            }

            if (!span.parentSpanId.has_value()) {
                continue;
            }

            if (!spans_.count(*span.parentSpanId)) {
                throw ValidationException("Invalid parent reference");
            }

            std::set<std::string> visited;
            const Span* current = &span;

            while (current->parentSpanId.has_value()) {
                if (!visited.insert(current->spanId).second) {
                    throw ValidationException("Trace cycle detected");
                }

                auto parent = spans_.find(*current->parentSpanId);

                if (parent == spans_.end()) {
                    throw ValidationException("Broken trace hierarchy");
                }

                current = &parent->second;
            }
        }
    }

    const std::string& id() const {
        return traceId_;
    }

    const std::map<std::string, Span>& spans() const {
        return spans_;
    }
};

// ============================================================
// 6. ALERT ENGINE
// ============================================================

struct AlertRule {
    std::string name;
    std::string metric;
    double threshold;
    std::string operation;
    std::size_t windowSize;
};

struct AlertEvent {
    std::string name;
    AlertState previous;
    AlertState current;
    double observed;
};

class AlertEngine {
private:
    std::map<std::string, AlertRule> rules_;
    std::map<std::string, AlertState> states_;
    std::map<std::string, std::deque<double>> history_;
    std::vector<AlertEvent> events_;

    static bool compare(
        double value,
        double threshold,
        const std::string& operation
    ) {
        if (operation == ">") return value > threshold;
        if (operation == ">=") return value >= threshold;
        if (operation == "<") return value < threshold;
        if (operation == "<=") return value <= threshold;

        throw ValidationException("Invalid alert comparison");
    }

public:
    void addRule(const AlertRule& rule) {
        validateName(rule.name, "alert name");
        validateName(rule.metric, "metric");

        validateFinite(rule.threshold, "threshold");

        if (rule.windowSize == 0) {
            throw ValidationException("Window cannot be zero");
        }

        if (
            rule.operation != ">" &&
            rule.operation != ">=" &&
            rule.operation != "<" &&
            rule.operation != "<="
        ) {
            throw ValidationException("Unsupported operator");
        }

        if (rules_.count(rule.name)) {
            throw ValidationException("Duplicate alert rule");
        }

        rules_.emplace(rule.name, rule);
        states_[rule.name] = AlertState::Normal;
    }

    AlertState evaluate(
        const std::string& name,
        double value
    ) {
        validateFinite(value, "alert value");

        auto ruleIterator = rules_.find(name);

        if (ruleIterator == rules_.end()) {
            throw ValidationException("Alert rule missing");
        }

        const auto& rule = ruleIterator->second;
        auto& values = history_[name];

        values.push_back(value);

        if (values.size() > rule.windowSize) {
            values.pop_front();
        }

        if (values.size() < rule.windowSize) {
            return states_[name];
        }

        const double average =
            std::accumulate(values.begin(), values.end(), 0.0) /
            values.size();

        const AlertState next = compare(
            average,
            rule.threshold,
            rule.operation
        ) ? AlertState::Firing : AlertState::Normal;

        const AlertState previous = states_[name];

        if (previous != next) {
            states_[name] = next;

            events_.push_back({
                name,
                previous,
                next,
                average
            });
        }

        return next;
    }

    const std::vector<AlertEvent>& events() const {
        return events_;
    }
};

// ============================================================
// 7. OBSERVABILITY ENGINE
// ============================================================

class ObservabilityEngine {
private:
    std::map<std::string, Logger> loggers_;
    MetricRegistry metrics_;
    std::map<std::string, std::unique_ptr<Trace>> traces_;
    AlertEngine alerts_;

public:
    Logger& logger(const std::string& service) {
        auto iterator = loggers_.find(service);

        if (iterator == loggers_.end()) {
            iterator = loggers_.emplace(
                service,
                Logger(service)
            ).first;
        }

        return iterator->second;
    }

    Trace& createTrace(const std::string& traceId) {
        validateName(traceId, "trace identifier");

        if (traces_.count(traceId)) {
            throw ValidationException("Duplicate trace");
        }

        auto trace = std::make_unique<Trace>(traceId);
        Trace& reference = *trace;

        traces_.emplace(traceId, std::move(trace));
        return reference;
    }

    MetricRegistry& metrics() {
        return metrics_;
    }

    AlertEngine& alerts() {
        return alerts_;
    }

    std::vector<LogRecord> correlate(
        const std::string& traceId
    ) const {
        std::vector<LogRecord> result;

        for (const auto& [service, log] : loggers_) {
            auto records = log.findByTrace(traceId);

            result.insert(
                result.end(),
                records.begin(),
                records.end()
            );
        }

        return result;
    }

    const auto& traces() const {
        return traces_;
    }

    const auto& loggers() const {
        return loggers_;
    }
};

// ============================================================
// 8. PAYMENT SERVICE SIMULATION
// ============================================================

std::string processPayment(
    ObservabilityEngine& engine,
    double amount,
    bool shouldFail
) {
    validateFinite(amount, "payment amount");

    if (amount <= 0 || amount > 1'000'000) {
        throw ValidationException("Payment amount outside limits");
    }

    static std::uint64_t sequence = 1;

    const std::string traceId =
        "payment-trace-" + std::to_string(sequence++);

    Trace& trace = engine.createTrace(traceId);
    Logger& logger = engine.logger("payment-api");

    Span& root = trace.startSpan(
        "payment-api",
        "POST /payments",
        std::nullopt,
        {{"amount", std::to_string(amount)}}
    );

    logger.write(
        LogLevel::Info,
        "Payment request received",
        traceId,
        root.spanId
    );

    engine.metrics().increment(
        "payment_requests_total",
        "payment-api"
    );

    Span& database = trace.startSpan(
        "payment-database",
        "INSERT payment",
        root.spanId
    );

    trace.endSpan(database.spanId);

    Span& processor = trace.startSpan(
        "payment-processor",
        "authorize transaction",
        root.spanId
    );

    if (shouldFail) {
        trace.endSpan(processor.spanId, SpanStatus::Error);
        trace.endSpan(root.spanId, SpanStatus::Error);

        logger.write(
            LogLevel::Error,
            "Payment authorization failed",
            traceId,
            processor.spanId
        );

        engine.metrics().increment(
            "payment_failures_total",
            "payment-api"
        );
    } else {
        trace.endSpan(processor.spanId);
        trace.endSpan(root.spanId);

        logger.write(
            LogLevel::Info,
            "Payment completed",
            traceId,
            root.spanId
        );

        engine.metrics().increment(
            "payment_success_total",
            "payment-api"
        );
    }

    engine.metrics().observe(
        "payment_latency_ms",
        "payment-api",
        shouldFail ? 250.0 : 125.0
    );

    trace.validate();

    return traceId;
}

// ============================================================
// 9. REPORTING
// ============================================================

void printReport(const ObservabilityEngine& engine) {
    std::cout << "\nOBSERVABILITY ENGINE REPORT\n";
    std::cout << "===========================\n";

    std::cout << "\nSTRUCTURED LOGS\n";

    for (const auto& [service, logger] : engine.loggers()) {
        for (const auto& record : logger.records()) {
            std::cout
                << record.service << " "
                << toString(record.level) << " "
                << record.message
                << " trace=" << record.traceId
                << " span=" << record.spanId
                << '\n';
        }
    }

    std::cout << "\nMETRIC SERIES\n";

    for (const auto& [key, series] : engine.metrics().series()) {
        std::cout
            << key.service << "."
            << key.name << " = "
            << series.value
            << '\n';
    }

    std::cout << "\nDISTRIBUTED TRACES\n";

    for (const auto& [traceId, trace] : engine.traces()) {
        std::cout << "\nTrace: " << traceId << '\n';

        for (const auto& [spanId, span] : trace->spans()) {
            std::cout
                << span.service << " | "
                << span.operation << " | "
                << toString(span.status) << " | "
                << std::fixed << std::setprecision(3)
                << span.durationMs() << " ms\n";
        }
    }

    std::cout << "\nALERT EVENTS\n";

    for (const auto& event : engine.alerts().events()) {
        std::cout
            << event.name << ": "
            << toString(event.previous)
            << " -> "
            << toString(event.current)
            << " average=" << event.observed
            << '\n';
    }
}

// ============================================================
// 10. TESTS
// ============================================================

void runTests() {
    ObservabilityEngine engine;

    const std::string successfulTrace =
        processPayment(engine, 1500.0, false);

    const std::string failedTrace =
        processPayment(engine, 2500.0, true);

    const auto successfulLogs = engine.correlate(
        successfulTrace
    );

    const auto failedLogs = engine.correlate(
        failedTrace
    );

    if (successfulLogs.size() != 2) {
        throw ObservabilityException("Successful correlation failed");
    }

    if (failedLogs.size() != 2) {
        throw ObservabilityException("Failed correlation failed");
    }

    Logger& security = engine.logger("security-service");

    security.write(
        LogLevel::Warning,
        "Authentication event",
        "",
        "",
        {
            {"username", "operator"},
            {"password", "confidential"}
        }
    );

    const auto& securityRecord = security.records().back();

    if (securityRecord.attributes.at("password") != "[REDACTED]") {
        throw ObservabilityException("Sensitive value was not redacted");
    }

    engine.metrics().observe("test_latency", "test", 10);
    engine.metrics().observe("test_latency", "test", 20);
    engine.metrics().observe("test_latency", "test", 30);

    const auto summary = engine.metrics().summarize(
        "test_latency",
        "test"
    );

    if (summary.count != 3 || summary.p50 != 20) {
        throw ObservabilityException("Histogram calculation failed");
    }

    engine.metrics().setGauge(
        "active_connections",
        "payment-api",
        12
    );

    engine.alerts().addRule({
        "high_latency",
        "payment_latency_ms",
        200.0,
        ">",
        2
    });

    engine.alerts().evaluate("high_latency", 220);
    engine.alerts().evaluate("high_latency", 240);

    if (
        engine.alerts().events().empty() ||
        engine.alerts().events().back().current != AlertState::Firing
    ) {
        throw ObservabilityException("Alert did not fire");
    }

    engine.alerts().evaluate("high_latency", 100);
    engine.alerts().evaluate("high_latency", 120);

    if (
        engine.alerts().events().back().current != AlertState::Normal
    ) {
        throw ObservabilityException("Alert did not resolve");
    }

    try {
        processPayment(engine, -100, false);
        throw ObservabilityException("Invalid payment accepted");
    } catch (const ValidationException&) {
        // Expected validation failure.
    }

    try {
        engine.metrics().increment(
            "invalid_counter",
            "payment-api",
            -1
        );

        throw ObservabilityException("Negative counter accepted");
    } catch (const ValidationException&) {
        // Expected validation failure.
    }

    printReport(engine);

    std::cout
        << "\nALL C++17 OBSERVABILITY TESTS PASSED\n";
}

} // namespace observability

// ============================================================
// 11. MAIN
// ============================================================

int main() {
    try {
        observability::runTests();
        return 0;
    } catch (const std::exception& error) {
        std::cerr
            << "Execution failed: "
            << error.what()
            << '\n';

        return 1;
    }
}
