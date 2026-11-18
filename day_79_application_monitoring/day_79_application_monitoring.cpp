#include <algorithm>
#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <map>
#include <numeric>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace std;

// ============================================================
// APPLICATION MONITORING AND GOVERNANCE ENGINE
// C++17
// ============================================================

enum class HealthStatus {
    HEALTHY,
    DEGRADED,
    UNHEALTHY,
    UNKNOWN
};

enum class Severity {
    INFO,
    WARNING,
    CRITICAL
};

enum class AlertState {
    FIRING,
    RESOLVED
};

string toString(HealthStatus status) {
    switch (status) {
        case HealthStatus::HEALTHY: return "HEALTHY";
        case HealthStatus::DEGRADED: return "DEGRADED";
        case HealthStatus::UNHEALTHY: return "UNHEALTHY";
        default: return "UNKNOWN";
    }
}

string toString(Severity severity) {
    switch (severity) {
        case Severity::INFO: return "INFO";
        case Severity::WARNING: return "WARNING";
        default: return "CRITICAL";
    }
}

string currentTime() {
    auto now = chrono::system_clock::now();
    auto value = chrono::system_clock::to_time_t(now);

    stringstream stream;
    stream << put_time(gmtime(&value), "%Y-%m-%dT%H:%M:%SZ");

    return stream.str();
}

// ============================================================
// DOMAIN STRUCTURES
// ============================================================

struct HealthResult {
    string checkName;
    string service;
    HealthStatus status;
    double latencyMs;
    string message;
    string checkedAt;
};

struct ServicePolicy {
    double warningLatencyMs = 500.0;
    double criticalLatencyMs = 1500.0;
    int failureThreshold = 2;
    int recoveryThreshold = 2;

    void validate() const {
        if (warningLatencyMs < 0 ||
            criticalLatencyMs < warningLatencyMs ||
            failureThreshold < 1 ||
            recoveryThreshold < 1) {
            throw invalid_argument("Invalid service policy");
        }
    }
};

struct ServiceMetrics {
    size_t totalChecks = 0;
    size_t successfulChecks = 0;
    double totalLatencyMs = 0.0;
    double maximumLatencyMs = 0.0;

    void record(const HealthResult& result) {
        ++totalChecks;

        if (result.status == HealthStatus::HEALTHY) {
            ++successfulChecks;
        }

        totalLatencyMs += result.latencyMs;

        maximumLatencyMs = max(
            maximumLatencyMs,
            result.latencyMs
        );
    }

    double availability() const {
        if (totalChecks == 0) return 0.0;

        return 100.0 * successfulChecks / totalChecks;
    }

    double averageLatency() const {
        if (totalChecks == 0) return 0.0;

        return totalLatencyMs / totalChecks;
    }
};

struct Alert {
    int id;
    string service;
    Severity severity;
    AlertState state;
    string message;
    string createdAt;
    string resolvedAt;
    int occurrences;
};

// ============================================================
// HEALTH CHECK INTERFACE
// ============================================================

class IHealthCheck {
public:
    virtual ~IHealthCheck() = default;

    virtual string name() const = 0;

    virtual string service() const = 0;

    virtual HealthResult execute() const = 0;
};

class FunctionalHealthCheck : public IHealthCheck {
private:
    string checkName;
    string serviceName;
    bool available;
    double latencyMs;

public:
    FunctionalHealthCheck(
        string name,
        string service,
        bool available,
        double latency
    )
        : checkName(move(name)),
          serviceName(move(service)),
          available(available),
          latencyMs(latency) {

        if (checkName.empty() || serviceName.empty()) {
            throw invalid_argument("Invalid check identity");
        }

        if (!isfinite(latencyMs) || latencyMs < 0) {
            throw invalid_argument("Invalid latency");
        }
    }

    string name() const override {
        return checkName;
    }

    string service() const override {
        return serviceName;
    }

    void setAvailable(bool value) {
        available = value;
    }

    HealthResult execute() const override {
        return {
            checkName,
            serviceName,
            available
                ? HealthStatus::HEALTHY
                : HealthStatus::UNHEALTHY,
            latencyMs,
            available
                ? "Dependency available"
                : "Dependency unavailable",
            currentTime()
        };
    }
};

// ============================================================
// ALERT MANAGEMENT
// ============================================================

class AlertManager {
private:
    int nextId = 1;

    vector<Alert> history;
    map<string, int> activeAlerts;

public:
    void process(
        const string& service,
        HealthStatus status
    ) {
        auto existing = activeAlerts.find(service);

        if (status == HealthStatus::HEALTHY ||
            status == HealthStatus::UNKNOWN) {

            if (existing != activeAlerts.end()) {
                Alert& alert = history.at(existing->second);

                alert.state = AlertState::RESOLVED;
                alert.resolvedAt = currentTime();

                cout << "RESOLVED: " << service << '\n';

                activeAlerts.erase(existing);
            }

            return;
        }

        Severity severity =
            status == HealthStatus::UNHEALTHY
                ? Severity::CRITICAL
                : Severity::WARNING;

        if (existing != activeAlerts.end()) {
            Alert& alert = history.at(existing->second);

            alert.occurrences++;
            alert.severity = severity;

            return;
        }

        Alert alert {
            nextId++,
            service,
            severity,
            AlertState::FIRING,
            "Service status: " + toString(status),
            currentTime(),
            "",
            1
        };

        history.push_back(alert);

        activeAlerts[service] = history.size() - 1;

        cout << "ALERT [" << toString(severity)
             << "] " << service
             << ": " << alert.message << '\n';
    }

    size_t activeCount() const {
        return activeAlerts.size();
    }

    const vector<Alert>& getHistory() const {
        return history;
    }

    vector<Alert> getActive() const {
        vector<Alert> result;

        for (const auto& entry : activeAlerts) {
            result.push_back(history.at(entry.second));
        }

        return result;
    }
};

// ============================================================
// SERVICE MONITOR
// ============================================================

class ServiceMonitor {
private:
    string serviceName;
    ServicePolicy policy;

    vector<const IHealthCheck*> checks;
    vector<HealthResult> history;

    ServiceMetrics metrics;

    HealthStatus status = HealthStatus::UNKNOWN;

    int consecutiveFailures = 0;
    int consecutiveRecoveries = 0;

public:
    ServiceMonitor(
        string name,
        ServicePolicy policy
    )
        : serviceName(move(name)),
          policy(policy) {

        if (serviceName.empty()) {
            throw invalid_argument("Service name is required");
        }

        policy.validate();
    }

    void registerCheck(const IHealthCheck& check) {
        if (check.service() != serviceName) {
            throw invalid_argument("Service mismatch");
        }

        auto duplicate = find_if(
            checks.begin(),
            checks.end(),
            [&](const IHealthCheck* existing) {
                return existing->name() == check.name();
            }
        );

        if (duplicate != checks.end()) {
            throw invalid_argument("Duplicate health check");
        }

        checks.push_back(&check);
    }

    HealthStatus evaluate() {
        if (checks.empty()) {
            throw runtime_error("No health checks registered");
        }

        bool failed = false;
        bool criticalLatency = false;
        bool warningLatency = false;

        for (const auto* check : checks) {
            HealthResult result = check->execute();

            if (!isfinite(result.latencyMs) ||
                result.latencyMs < 0) {
                throw runtime_error("Invalid check result");
            }

            if (result.status == HealthStatus::UNHEALTHY) {
                failed = true;
            }

            if (result.latencyMs >= policy.criticalLatencyMs) {
                criticalLatency = true;
            } else if (
                result.latencyMs >= policy.warningLatencyMs
            ) {
                warningLatency = true;
            }

            metrics.record(result);
            history.push_back(result);
        }

        if (failed || criticalLatency) {
            ++consecutiveFailures;
            consecutiveRecoveries = 0;

            status = consecutiveFailures >= policy.failureThreshold
                ? HealthStatus::UNHEALTHY
                : HealthStatus::DEGRADED;

        } else {
            consecutiveFailures = 0;
            ++consecutiveRecoveries;

            if (warningLatency) {
                status = HealthStatus::DEGRADED;
            } else if (
                consecutiveRecoveries >= policy.recoveryThreshold
            ) {
                status = HealthStatus::HEALTHY;
            } else if (status == HealthStatus::UNKNOWN) {
                status = HealthStatus::DEGRADED;
            }
        }

        return status;
    }

    const string& name() const {
        return serviceName;
    }

    HealthStatus getStatus() const {
        return status;
    }

    const ServiceMetrics& getMetrics() const {
        return metrics;
    }

    size_t historySize() const {
        return history.size();
    }
};

// ============================================================
// MONITORING ENGINE
// ============================================================

class MonitoringEngine {
private:
    map<string, ServiceMonitor> services;
    AlertManager alerts;

public:
    void addService(ServiceMonitor monitor) {
        string name = monitor.name();

        auto result = services.emplace(name, move(monitor));

        if (!result.second) {
            throw invalid_argument("Duplicate monitored service");
        }
    }

    void runCycle() {
        for (auto& entry : services) {
            auto& service = entry.second;

            try {
                HealthStatus status = service.evaluate();

                alerts.process(service.name(), status);

            } catch (const exception& error) {
                cerr << "Monitoring failure for "
                     << service.name()
                     << ": " << error.what() << '\n';
            }
        }
    }

    void dashboard() const {
        size_t healthy = 0;
        size_t degraded = 0;
        size_t unhealthy = 0;
        size_t unknown = 0;

        cout << "\n========== MONITORING DASHBOARD ==========\n";

        for (const auto& entry : services) {
            const auto& service = entry.second;
            const auto& metrics = service.getMetrics();

            HealthStatus status = service.getStatus();

            switch (status) {
                case HealthStatus::HEALTHY: ++healthy; break;
                case HealthStatus::DEGRADED: ++degraded; break;
                case HealthStatus::UNHEALTHY: ++unhealthy; break;
                default: ++unknown;
            }

            cout << "\nService: " << service.name()
                 << "\nStatus: " << toString(status)
                 << "\nChecks: " << metrics.totalChecks
                 << "\nAvailability: "
                 << fixed << setprecision(2)
                 << metrics.availability() << "%"
                 << "\nAverage latency: "
                 << metrics.averageLatency() << " ms"
                 << "\nMaximum latency: "
                 << metrics.maximumLatencyMs << " ms\n";
        }

        cout << "\nServices: " << services.size()
             << "\nHealthy: " << healthy
             << "\nDegraded: " << degraded
             << "\nUnhealthy: " << unhealthy
             << "\nUnknown: " << unknown
             << "\nActive alerts: " << alerts.activeCount()
             << "\n==========================================\n";
    }

    const AlertManager& alertManager() const {
        return alerts;
    }
};

// ============================================================
// EXECUTABLE SCENARIO
// ============================================================

void runTests() {
    ServicePolicy policy;

    policy.validate();

    ServiceMetrics metrics;

    metrics.record({
        "application",
        "test",
        HealthStatus::HEALTHY,
        100,
        "Available",
        currentTime()
    });

    metrics.record({
        "database",
        "test",
        HealthStatus::UNHEALTHY,
        200,
        "Unavailable",
        currentTime()
    });

    if (metrics.totalChecks != 2 ||
        metrics.successfulChecks != 1 ||
        metrics.availability() != 50.0) {
        throw runtime_error("Metrics test failed");
    }

    AlertManager manager;

    manager.process("test", HealthStatus::UNHEALTHY);

    if (manager.activeCount() != 1) {
        throw runtime_error("Alert creation test failed");
    }

    manager.process("test", HealthStatus::HEALTHY);

    if (manager.activeCount() != 0) {
        throw runtime_error("Alert resolution test failed");
    }

    cout << "All C++ monitoring tests passed.\n";
}

int main() {
    try {
        runTests();

        FunctionalHealthCheck applicationCheck(
            "application",
            "payment-api",
            true,
            120
        );

        FunctionalHealthCheck databaseCheck(
            "database",
            "payment-api",
            false,
            180
        );

        FunctionalHealthCheck providerCheck(
            "external-provider",
            "payment-api",
            true,
            250
        );

        ServicePolicy policy {
            300.0,
            1000.0,
            2,
            2
        };

        ServiceMonitor payment(
            "payment-api",
            policy
        );

        payment.registerCheck(applicationCheck);
        payment.registerCheck(databaseCheck);
        payment.registerCheck(providerCheck);

        MonitoringEngine engine;

        engine.addService(move(payment));

        for (int cycle = 1; cycle <= 4; ++cycle) {
            cout << "\nMONITORING CYCLE " << cycle << '\n';

            if (cycle == 3) {
                databaseCheck.setAvailable(true);
            }

            engine.runCycle();
            engine.dashboard();
        }

    } catch (const exception& error) {
        cerr << "Fatal monitoring error: "
             << error.what() << '\n';

        return 1;
    }

    return 0;
}
