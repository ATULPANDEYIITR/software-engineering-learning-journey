#include <algorithm>
#include <cctype>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <regex>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

/*
 * C++17 Static Analysis and Code Quality Engine
 *
 * Models source-code analysis for a software repository.
 * Includes:
 * - Rule registry
 * - Diagnostic classification
 * - Source inspection
 * - Security checks
 * - Formatting checks
 * - Suppression management
 * - Quality-gate evaluation
 * - Repository-level reporting
 */

enum class Severity {
    Error,
    Warning,
    Info
};

enum class RuleCategory {
    Security,
    Formatting,
    Reliability,
    Maintainability,
    Performance
};

enum class GateStatus {
    Passed,
    Failed
};

std::string toString(Severity severity) {
    switch (severity) {
        case Severity::Error: return "ERROR";
        case Severity::Warning: return "WARNING";
        case Severity::Info: return "INFO";
    }
    return "UNKNOWN";
}

std::string toString(RuleCategory category) {
    switch (category) {
        case RuleCategory::Security: return "Security";
        case RuleCategory::Formatting: return "Formatting";
        case RuleCategory::Reliability: return "Reliability";
        case RuleCategory::Maintainability: return "Maintainability";
        case RuleCategory::Performance: return "Performance";
    }
    return "Unknown";
}

struct Rule {
    std::string id;
    std::string description;
    Severity severity;
    RuleCategory category;
    bool enabled = true;
};

struct Diagnostic {
    std::string filename;
    int line;
    int column;
    std::string ruleId;
    Severity severity;
    std::string message;
    std::string suggestion;
};

struct AnalysisReport {
    std::string filename;
    std::vector<Diagnostic> diagnostics;
    std::size_t linesAnalyzed = 0;

    std::size_t count(Severity severity) const {
        return std::count_if(
            diagnostics.begin(),
            diagnostics.end(),
            [severity](const Diagnostic& d) {
                return d.severity == severity;
            }
        );
    }
};

class RuleRegistry {
private:
    std::map<std::string, Rule> rules;

public:
    RuleRegistry() {
        registerRule({
            "SEC001", "Unsafe dynamic evaluation",
            Severity::Error, RuleCategory::Security
        });
        registerRule({
            "SEC002", "Unsafe shell execution",
            Severity::Error, RuleCategory::Security
        });
        registerRule({
            "FMT001", "Trailing whitespace",
            Severity::Warning, RuleCategory::Formatting
        });
        registerRule({
            "FMT002", "Excessive line length",
            Severity::Warning, RuleCategory::Formatting
        });
        registerRule({
            "REL001", "Unreachable-looking debug statement",
            Severity::Warning, RuleCategory::Reliability
        });
        registerRule({
            "MAINT001", "Long source line",
            Severity::Info, RuleCategory::Maintainability
        });
        registerRule({
            "PERF001", "Potentially expensive repeated operation",
            Severity::Info, RuleCategory::Performance
        });
    }

    void registerRule(const Rule& rule) {
        if (rule.id.empty()) {
            throw std::invalid_argument("Rule ID cannot be empty.");
        }

        if (!rules.emplace(rule.id, rule).second) {
            throw std::invalid_argument("Duplicate rule ID: " + rule.id);
        }
    }

    const Rule* find(const std::string& id) const {
        auto it = rules.find(id);
        return it == rules.end() ? nullptr : &it->second;
    }

    void setEnabled(const std::string& id, bool enabled) {
        auto it = rules.find(id);
        if (it == rules.end()) {
            throw std::invalid_argument("Unknown rule: " + id);
        }
        it->second.enabled = enabled;
    }

    const std::map<std::string, Rule>& all() const {
        return rules;
    }
};

class StaticAnalyzer {
private:
    const RuleRegistry& registry;
    std::set<std::string> suppressedRules;
    std::size_t maxLineLength;

    bool enabled(const std::string& id) const {
        const Rule* rule = registry.find(id);
        return rule && rule->enabled &&
               suppressedRules.count(id) == 0;
    }

    static std::string trimRight(const std::string& text) {
        std::size_t end = text.find_last_not_of(" \t\r");
        return end == std::string::npos
            ? ""
            : text.substr(0, end + 1);
    }

    void add(
        AnalysisReport& report,
        const std::string& rule,
        int line,
        int column,
        const std::string& message,
        const std::string& suggestion
    ) const {
        if (!enabled(rule)) return;

        const Rule* definition = registry.find(rule);
        if (!definition) return;

        report.diagnostics.push_back({
            report.filename,
            line,
            column,
            rule,
            definition->severity,
            message,
            suggestion
        });
    }

public:
    explicit StaticAnalyzer(
        const RuleRegistry& ruleRegistry,
        std::size_t maximumLength = 100
    )
        : registry(ruleRegistry), maxLineLength(maximumLength) {
        if (maximumLength < 20) {
            throw std::invalid_argument(
                "Maximum line length must be at least 20."
            );
        }
    }

    void suppress(const std::string& ruleId) {
        if (!registry.find(ruleId)) {
            throw std::invalid_argument(
                "Cannot suppress unknown rule: " + ruleId
            );
        }
        suppressedRules.insert(ruleId);
    }

    AnalysisReport analyze(
        const std::string& source,
        const std::string& filename
    ) const {
        AnalysisReport report;
        report.filename = filename;

        std::istringstream input(source);
        std::string line;
        int lineNumber = 0;

        const std::regex evalPattern(R"(\beval\s*\()");
        const std::regex systemPattern(R"(\bsystem\s*\()");
        const std::regex debugPattern(R"(\bassert\s*\()");
        const std::regex repeatedPattern(R"(find\s*\()");

        while (std::getline(input, line)) {
            ++lineNumber;
            ++report.linesAnalyzed;

            std::string trimmed = trimRight(line);

            if (trimmed.size() != line.size()) {
                add(
                    report, "FMT001", lineNumber,
                    static_cast<int>(trimmed.size()) + 1,
                    "Trailing whitespace detected.",
                    "Remove spaces and tabs at the end of the line."
                );
            }

            if (line.size() > maxLineLength) {
                add(
                    report, "FMT002", lineNumber,
                    static_cast<int>(maxLineLength + 1),
                    "Line exceeds configured maximum length.",
                    "Break the expression into smaller statements."
                );
            }

            std::smatch match;

            if (std::regex_search(line, match, evalPattern)) {
                add(
                    report, "SEC001", lineNumber,
                    static_cast<int>(match.position() + 1),
                    "Dynamic evaluation using eval() detected.",
                    "Replace dynamic evaluation with validated logic."
                );
            }

            if (std::regex_search(line, match, systemPattern)) {
                add(
                    report, "SEC002", lineNumber,
                    static_cast<int>(match.position() + 1),
                    "Shell command execution detected.",
                    "Avoid shell execution or strictly validate inputs."
                );
            }

            if (std::regex_search(line, match, debugPattern)) {
                add(
                    report, "REL001", lineNumber,
                    static_cast<int>(match.position() + 1),
                    "Assertion used in source code.",
                    "Do not rely on assertions for runtime validation."
                );
            }

            if (line.size() > 80) {
                add(
                    report, "MAINT001", lineNumber, 81,
                    "Long line may reduce readability.",
                    "Consider extracting expressions."
                );
            }

            if (std::regex_search(line, repeatedPattern)) {
                add(
                    report, "PERF001", lineNumber, 1,
                    "Search operation detected.",
                    "Evaluate repeated searches in performance-critical loops."
                );
            }
        }

        std::sort(
            report.diagnostics.begin(),
            report.diagnostics.end(),
            [](const Diagnostic& a, const Diagnostic& b) {
                if (a.line != b.line) return a.line < b.line;
                if (a.column != b.column) return a.column < b.column;
                return a.ruleId < b.ruleId;
            }
        );

        return report;
    }

    AnalysisReport analyzeFile(const std::string& filename) const {
        std::ifstream file(filename);

        if (!file) {
            AnalysisReport report;
            report.filename = filename;
            report.diagnostics.push_back({
                filename, 1, 1, "FILE001",
                Severity::Error,
                "Unable to open source file.",
                "Check file existence and read permissions."
            });
            return report;
        }

        std::ostringstream contents;
        contents << file.rdbuf();

        if (file.bad()) {
            throw std::runtime_error("Failed while reading " + filename);
        }

        return analyze(contents.str(), filename);
    }
};

class QualityGate {
private:
    std::size_t maxErrors;
    std::size_t maxWarnings;

public:
    QualityGate(std::size_t errors, std::size_t warnings)
        : maxErrors(errors), maxWarnings(warnings) {}

    GateStatus evaluate(const AnalysisReport& report) const {
        if (report.count(Severity::Error) > maxErrors ||
            report.count(Severity::Warning) > maxWarnings) {
            return GateStatus::Failed;
        }
        return GateStatus::Passed;
    }
};

void printReport(const AnalysisReport& report) {
    std::cout << "\nFile: " << report.filename << '\n';
    std::cout << "Lines analyzed: " << report.linesAnalyzed << '\n';

    for (const auto& diagnostic : report.diagnostics) {
        std::cout
            << diagnostic.filename << ':'
            << diagnostic.line << ':'
            << diagnostic.column << ' '
            << toString(diagnostic.severity)
            << " [" << diagnostic.ruleId << "] "
            << diagnostic.message << '\n';

        std::cout << "  Suggestion: "
                  << diagnostic.suggestion << '\n';
    }

    std::cout
        << "Errors: " << report.count(Severity::Error)
        << " | Warnings: " << report.count(Severity::Warning)
        << " | Info: " << report.count(Severity::Info)
        << '\n';
}

int main(int argc, char* argv[]) {
    try {
        RuleRegistry registry;
        StaticAnalyzer analyzer(registry, 100);
        QualityGate gate(0, 5);

        std::vector<AnalysisReport> reports;

        if (argc > 1) {
            for (int i = 1; i < argc; ++i) {
                reports.push_back(analyzer.analyzeFile(argv[i]));
            }
        } else {
            const std::string source =
                "#include <iostream>   \n"
                "int main() {\n"
                "    system(\"echo unsafe\");\n"
                "    assert(true);\n"
                "    std::string value = \"test\";\n"
                "    return 0;\n"
                "}\n";

            reports.push_back(
                analyzer.analyze(source, "sample.cpp")
            );
        }

        std::size_t totalErrors = 0;
        std::size_t totalWarnings = 0;

        for (const auto& report : reports) {
            printReport(report);

            totalErrors += report.count(Severity::Error);
            totalWarnings += report.count(Severity::Warning);

            GateStatus status = gate.evaluate(report);

            std::cout << "Quality gate: "
                      << (status == GateStatus::Passed
                              ? "PASSED" : "FAILED")
                      << '\n';
        }

        std::cout << "\nRepository analysis\n";
        std::cout << "Files: " << reports.size() << '\n';
        std::cout << "Errors: " << totalErrors << '\n';
        std::cout << "Warnings: " << totalWarnings << '\n';

        return totalErrors > 0 ? 1 : 0;

    } catch (const std::exception& exception) {
        std::cerr << "Analysis failure: "
                  << exception.what() << '\n';
        return 2;
    }
}
