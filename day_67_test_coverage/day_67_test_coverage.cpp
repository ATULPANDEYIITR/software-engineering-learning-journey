#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace std;

enum class MetricType {
    Statement,
    Branch,
    Function
};

string metricName(MetricType type) {
    switch (type) {
        case MetricType::Statement: return "Statement";
        case MetricType::Branch: return "Branch";
        case MetricType::Function: return "Function";
    }
    throw logic_error("Unknown metric");
}

struct TestResult {
    string name;
    bool passed;
    string error;
};

struct MetricData {
    set<string> total;
    set<string> covered;

    double percentage() const {
        if (total.empty()) return 100.0;

        return 100.0 * covered.size() / total.size();
    }

    set<string> missed() const {
        set<string> result;

        for (const auto& item : total) {
            if (!covered.count(item)) {
                result.insert(item);
            }
        }

        return result;
    }
};

class CoverageEngine {
private:
    map<MetricType, MetricData> metrics;
    vector<TestResult> tests;

public:
    CoverageEngine() {
        metrics[MetricType::Statement];
        metrics[MetricType::Branch];
        metrics[MetricType::Function];
    }

    void registerItem(MetricType type, const string& id) {
        if (id.empty()) {
            throw invalid_argument("Coverage identifier cannot be empty");
        }

        metrics[type].total.insert(id);
    }

    void hit(MetricType type, const string& id) {
        auto& metric = metrics.at(type);

        if (!metric.total.count(id)) {
            throw invalid_argument("Unregistered coverage identifier: " + id);
        }

        metric.covered.insert(id);
    }

    void recordTest(const string& name, bool passed, const string& error = "") {
        tests.push_back({name, passed, error});

        cout << "[TEST] "
             << (passed ? "PASS " : "FAIL ")
             << name;

        if (!passed) {
            cout << " | " << error;
        }

        cout << '\n';
    }

    const MetricData& getMetric(MetricType type) const {
        return metrics.at(type);
    }

    bool testsPassed() const {
        return all_of(
            tests.begin(),
            tests.end(),
            [](const TestResult& test) {
                return test.passed;
            }
        );
    }

    bool meetsThreshold(double threshold) const {
        if (threshold < 0 || threshold > 100) {
            throw invalid_argument("Threshold must be between 0 and 100");
        }

        for (const auto& entry : metrics) {
            if (entry.second.percentage() < threshold) {
                return false;
            }
        }

        return true;
    }

    void printReport() const {
        cout << "\nCOVERAGE REPORT\n";

        for (const auto& entry : metrics) {
            const auto& data = entry.second;

            cout << metricName(entry.first) << ": "
                 << data.covered.size() << "/"
                 << data.total.size() << " ("
                 << fixed << setprecision(2)
                 << data.percentage() << "%)\n";

            for (const auto& missing : data.missed()) {
                cout << "  Uncovered: " << missing << '\n';
            }
        }

        int passed = 0;

        for (const auto& test : tests) {
            if (test.passed) ++passed;
        }

        cout << "\nTests: " << passed << "/" << tests.size()
             << " passed\n";
    }

    void saveReport(const string& filename) const {
        ofstream file(filename);

        if (!file.is_open()) {
            throw runtime_error("Cannot open coverage report");
        }

        file << "{\n  \"metrics\": {\n";

        int index = 0;

        for (const auto& entry : metrics) {
            const auto& data = entry.second;

            file << "    \"" << metricName(entry.first) << "\": {\n";
            file << "      \"total\": " << data.total.size() << ",\n";
            file << "      \"covered\": " << data.covered.size() << ",\n";
            file << "      \"percentage\": "
                 << fixed << setprecision(2)
                 << data.percentage() << "\n";
            file << "    }";

            if (++index < static_cast<int>(metrics.size())) {
                file << ",";
            }

            file << "\n";
        }

        file << "  },\n";
        file << "  \"tests\": {\n";

        int passed = 0;

        for (const auto& test : tests) {
            if (test.passed) ++passed;
        }

        file << "    \"total\": " << tests.size() << ",\n";
        file << "    \"passed\": " << passed << ",\n";
        file << "    \"failed\": " << tests.size() - passed << "\n";
        file << "  }\n}\n";

        if (!file.good()) {
            throw runtime_error("Failed to write coverage report");
        }
    }
};

CoverageEngine coverage;

void initializeCoverage() {
    const vector<pair<MetricType, vector<string>>> definitions = {
        {
            MetricType::Statement,
            {
                "divide.validation",
                "divide.calculation",
                "classify.validation",
                "classify.negative",
                "classify.zero",
                "classify.positive",
                "classify.large"
            }
        },
        {
            MetricType::Branch,
            {
                "divide.zero",
                "classify.negative",
                "classify.zero",
                "classify.positive",
                "classify.large"
            }
        },
        {
            MetricType::Function,
            {
                "safeDivide",
                "classifyNumber"
            }
        }
    };

    for (const auto& definition : definitions) {
        for (const auto& id : definition.second) {
            coverage.registerItem(definition.first, id);
        }
    }
}

double safeDivide(double a, double b) {
    coverage.hit(MetricType::Function, "safeDivide");
    coverage.hit(MetricType::Statement, "divide.validation");

    if (!isfinite(a) || !isfinite(b)) {
        throw invalid_argument("Inputs must be finite");
    }

    if (b == 0.0) {
        coverage.hit(MetricType::Branch, "divide.zero");
        throw domain_error("Division by zero");
    }

    coverage.hit(MetricType::Statement, "divide.calculation");

    double result = a / b;

    if (!isfinite(result)) {
        throw overflow_error("Division result is not finite");
    }

    return result;
}

string classifyNumber(double value) {
    coverage.hit(MetricType::Function, "classifyNumber");
    coverage.hit(MetricType::Statement, "classify.validation");

    if (!isfinite(value)) {
        throw invalid_argument("Input must be finite");
    }

    if (value < 0) {
        coverage.hit(MetricType::Branch, "classify.negative");
        coverage.hit(MetricType::Statement, "classify.negative");
        return "negative";
    }

    if (value == 0) {
        coverage.hit(MetricType::Branch, "classify.zero");
        coverage.hit(MetricType::Statement, "classify.zero");
        return "zero";
    }

    coverage.hit(MetricType::Branch, "classify.positive");
    coverage.hit(MetricType::Statement, "classify.positive");

    if (value >= 100) {
        coverage.hit(MetricType::Branch, "classify.large");
        coverage.hit(MetricType::Statement, "classify.large");
        return "large";
    }

    return "positive";
}

void expectEqual(
    const string& name,
    const string& actual,
    const string& expected
) {
    if (actual != expected) {
        throw runtime_error("Expected " + expected + ", received " + actual);
    }
}

void expectNear(
    const string& name,
    double actual,
    double expected,
    double tolerance = 1e-9
) {
    if (abs(actual - expected) > tolerance) {
        throw runtime_error("Numeric assertion failed: " + name);
    }
}

template <typename ExceptionType, typename Function>
void expectThrows(Function function) {
    try {
        function();
    } catch (const ExceptionType&) {
        return;
    }

    throw runtime_error("Expected exception was not thrown");
}

template <typename Function>
void runTest(const string& name, Function function) {
    try {
        function();
        coverage.recordTest(name, true);
    } catch (const exception& error) {
        coverage.recordTest(name, false, error.what());
    }
}

int main() {
    try {
        initializeCoverage();

        runTest("normal division", [] {
            expectNear("10 / 2", safeDivide(10, 2), 5);
        });

        runTest("negative division", [] {
            expectNear("negative division", safeDivide(-10, 2), -5);
        });

        runTest("division by zero", [] {
            expectThrows<domain_error>([] {
                safeDivide(10, 0);
            });
        });

        runTest("infinite input", [] {
            expectThrows<invalid_argument>([] {
                safeDivide(INFINITY, 2);
            });
        });

        runTest("negative classification", [] {
            expectEqual(
                "negative",
                classifyNumber(-5),
                "negative"
            );
        });

        runTest("zero classification", [] {
            expectEqual(
                "zero",
                classifyNumber(0),
                "zero"
            );
        });

        runTest("positive classification", [] {
            expectEqual(
                "positive",
                classifyNumber(25),
                "positive"
            );
        });

        runTest("large classification", [] {
            expectEqual(
                "large",
                classifyNumber(100),
                "large"
            );
        });

        runTest("decimal boundary", [] {
            expectEqual(
                "decimal",
                classifyNumber(99.99),
                "positive"
            );
        });

        runTest("invalid classification", [] {
            expectThrows<invalid_argument>([] {
                classifyNumber(NAN);
            });
        });

        coverage.printReport();

        const double threshold = 80.0;
        const bool qualityGate = coverage.meetsThreshold(threshold);
        const bool success = qualityGate && coverage.testsPassed();

        cout << "\nCoverage threshold: " << threshold << "%\n";
        cout << "Quality gate: " << (success ? "PASSED" : "FAILED") << '\n';

        coverage.saveReport("coverage-report.json");

        if (!success) {
            return 1;
        }

        cout << "Report saved to coverage-report.json\n";
        return 0;

    } catch (const exception& error) {
        cerr << "Execution error: " << error.what() << '\n';
        return 2;
    }
}
