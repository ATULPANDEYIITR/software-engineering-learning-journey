import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

/*
 * Enterprise Static Analysis and Quality Governance System.
 *
 * Implements:
 * - Rule definitions and ownership
 * - Linter diagnostics
 * - Formatter policies
 * - Source-code quality analysis
 * - Security checks
 * - Suppression governance
 * - Quality gates
 * - Analysis execution and reporting
 *
 * Java 17, standard library only.
 */

public class StaticAnalysisEnterprise {

    enum Severity {
        ERROR, WARNING, INFO
    }

    enum Category {
        SECURITY, FORMATTING, RELIABILITY,
        MAINTAINABILITY, PERFORMANCE
    }

    enum RunStatus {
        COMPLETED, FAILED, REJECTED
    }

    record AnalysisRule(
        String id,
        String description,
        Severity severity,
        Category category,
        boolean enabled
    ) {
        AnalysisRule {
            Objects.requireNonNull(id);
            Objects.requireNonNull(description);
            Objects.requireNonNull(severity);
            Objects.requireNonNull(category);

            if (!id.matches("[A-Z]+[0-9]{3}")) {
                throw new IllegalArgumentException("Invalid rule ID.");
            }
        }
    }

    record Diagnostic(
        String filename,
        int line,
        int column,
        String ruleId,
        Severity severity,
        String message,
        String suggestion
    ) {
        Diagnostic {
            Objects.requireNonNull(filename);
            Objects.requireNonNull(ruleId);
            Objects.requireNonNull(severity);
            Objects.requireNonNull(message);

            if (line < 1 || column < 1) {
                throw new IllegalArgumentException(
                    "Diagnostic positions must be positive."
                );
            }
        }
    }

    record AnalysisResult(
        String filename,
        List<Diagnostic> diagnostics,
        int linesAnalyzed,
        RunStatus status
    ) {
        AnalysisResult {
            diagnostics = List.copyOf(diagnostics);
        }

        long count(Severity severity) {
            return diagnostics.stream()
                .filter(d -> d.severity() == severity)
                .count();
        }

        boolean hasErrors() {
            return count(Severity.ERROR) > 0;
        }
    }

    record Suppression(
        String ruleId,
        String reason,
        String approvedBy
    ) {
        Suppression {
            if (reason == null || reason.isBlank()) {
                throw new IllegalArgumentException(
                    "Suppression requires a reason."
                );
            }

            if (approvedBy == null || approvedBy.isBlank()) {
                throw new IllegalArgumentException(
                    "Suppression requires an approver."
                );
            }
        }
    }

    static final class RuleRegistry {
        private final Map<String, AnalysisRule> rules =
            new ConcurrentHashMap<>();

        void register(AnalysisRule rule) {
            AnalysisRule previous = rules.putIfAbsent(
                rule.id(), rule
            );

            if (previous != null) {
                throw new IllegalArgumentException(
                    "Duplicate rule: " + rule.id()
                );
            }
        }

        AnalysisRule get(String id) {
            return rules.get(id);
        }

        List<AnalysisRule> enabledRules() {
            return rules.values().stream()
                .filter(AnalysisRule::enabled)
                .sorted(Comparator.comparing(AnalysisRule::id))
                .toList();
        }
    }

    static final class AnalysisPolicy {
        private final int maximumLineLength;
        private final int maximumErrors;
        private final int maximumWarnings;
        private final boolean allowConsole;
        private final Set<String> suppressedRules;

        AnalysisPolicy(
            int maximumLineLength,
            int maximumErrors,
            int maximumWarnings,
            boolean allowConsole,
            List<Suppression> suppressions
        ) {
            if (maximumLineLength < 20 ||
                maximumErrors < 0 ||
                maximumWarnings < 0) {
                throw new IllegalArgumentException(
                    "Invalid analysis policy limits."
                );
            }

            this.maximumLineLength = maximumLineLength;
            this.maximumErrors = maximumErrors;
            this.maximumWarnings = maximumWarnings;
            this.allowConsole = allowConsole;

            this.suppressedRules = suppressions.stream()
                .map(Suppression::ruleId)
                .collect(Collectors.toUnmodifiableSet());
        }

        int maximumLineLength() {
            return maximumLineLength;
        }

        int maximumErrors() {
            return maximumErrors;
        }

        int maximumWarnings() {
            return maximumWarnings;
        }

        boolean allowConsole() {
            return allowConsole;
        }

        boolean isSuppressed(String rule) {
            return suppressedRules.contains(rule);
        }
    }

    static final class SourceFormatter {

        String format(String source) {
            Objects.requireNonNull(source);

            String[] lines = source.split("\\R", -1);
            List<String> formatted = new ArrayList<>();

            for (int i = 0; i < lines.length; i++) {
                String line = lines[i]
                    .replace("\t", "    ")
                    .replaceAll("[ \\t]+$", "");

                formatted.add(line);
            }

            // split(..., -1) preserves the final empty element.
            return String.join("\n", formatted);
        }

        void formatFile(Path path) throws IOException {
            String original = Files.readString(
                path, StandardCharsets.UTF_8
            );

            String formatted = format(original);

            if (!original.equals(formatted)) {
                Path temporary = Files.createTempFile(
                    path.getParent(),
                    "format-",
                    ".tmp"
                );

                try {
                    Files.writeString(
                        temporary,
                        formatted,
                        StandardCharsets.UTF_8
                    );

                    try {
                        Files.move(
                            temporary,
                            path,
                            java.nio.file.StandardCopyOption.REPLACE_EXISTING,
                            java.nio.file.StandardCopyOption.ATOMIC_MOVE
                        );
                    } catch (java.nio.file.AtomicMoveNotSupportedException e) {
                        Files.move(
                            temporary,
                            path,
                            java.nio.file.StandardCopyOption.REPLACE_EXISTING
                        );
                    }
                } finally {
                    Files.deleteIfExists(temporary);
                }
            }
        }
    }

    static final class StaticAnalyzer {
        private final RuleRegistry registry;
        private final AnalysisPolicy policy;

        StaticAnalyzer(
            RuleRegistry registry,
            AnalysisPolicy policy
        ) {
            this.registry = registry;
            this.policy = policy;
        }

        private void report(
            List<Diagnostic> diagnostics,
            String filename,
            String ruleId,
            int line,
            int column,
            String message,
            String suggestion
        ) {
            AnalysisRule rule = registry.get(ruleId);

            if (rule == null ||
                !rule.enabled() ||
                policy.isSuppressed(ruleId)) {
                return;
            }

            diagnostics.add(new Diagnostic(
                filename,
                line,
                column,
                ruleId,
                rule.severity(),
                message,
                suggestion
            ));
        }

        AnalysisResult analyze(
            String filename,
            String source
        ) {
            Objects.requireNonNull(filename);
            Objects.requireNonNull(source);

            List<Diagnostic> diagnostics = new ArrayList<>();
            String[] lines = source.split("\\R", -1);

            for (int i = 0; i < lines.length; i++) {
                String line = lines[i];
                int number = i + 1;

                if (line.length() > policy.maximumLineLength()) {
                    report(
                        diagnostics, filename, "FMT001",
                        number, policy.maximumLineLength() + 1,
                        "Line exceeds configured length.",
                        "Split the expression."
                    );
                }

                if (line.matches(".*[ \\t]+$")) {
                    report(
                        diagnostics, filename, "FMT002",
                        number, line.length(),
                        "Trailing whitespace found.",
                        "Remove trailing spaces and tabs."
                    );
                }

                if (line.contains("\t")) {
                    report(
                        diagnostics, filename, "FMT003",
                        number, line.indexOf('\t') + 1,
                        "Tab indentation found.",
                        "Use spaces consistently."
                    );
                }

                if (line.matches(".*\\beval\\s*\\(.*")) {
                    report(
                        diagnostics, filename, "SEC001",
                        number, line.indexOf("eval") + 1,
                        "Dynamic code evaluation detected.",
                        "Replace eval with validated operations."
                    );
                }

                if (line.matches(".*\\bRuntime\\.getRuntime\\s*\\(.*")) {
                    report(
                        diagnostics, filename, "SEC002",
                        number,
                        line.indexOf("Runtime") + 1,
                        "Runtime execution API detected.",
                        "Avoid constructing shell commands from input."
                    );
                }

                if (!policy.allowConsole() &&
                    line.matches(".*\\bSystem\\.out\\.(print|println)\\s*\\(.*")) {
                    report(
                        diagnostics, filename, "STYLE001",
                        number,
                        line.indexOf("System.out") + 1,
                        "Direct console output found.",
                        "Use structured application logging."
                    );
                }

                if (line.matches(".*\\bTODO\\b.*")) {
                    report(
                        diagnostics, filename, "MAINT001",
                        number, line.indexOf("TODO") + 1,
                        "Unresolved TODO marker found.",
                        "Resolve the issue before release."
                    );
                }
            }

            if (!source.isEmpty() && !source.endsWith("\n")) {
                report(
                    diagnostics, filename, "FMT004",
                    lines.length, 1,
                    "Missing final newline.",
                    "Add a newline at the end of the file."
                );
            }

            diagnostics.sort(
                Comparator.comparingInt(Diagnostic::line)
                    .thenComparingInt(Diagnostic::column)
                    .thenComparing(Diagnostic::ruleId)
            );

            return new AnalysisResult(
                filename,
                diagnostics,
                lines.length,
                RunStatus.COMPLETED
            );
        }

        AnalysisResult analyzeFile(Path path) {
            try {
                if (!Files.isRegularFile(path)) {
                    throw new IOException("Not a regular file.");
                }

                if (Files.size(path) > 5 * 1024 * 1024) {
                    throw new IOException("File exceeds 5 MB.");
                }

                return analyze(
                    path.toString(),
                    Files.readString(path, StandardCharsets.UTF_8)
                );

            } catch (IOException e) {
                return new AnalysisResult(
                    path.toString(),
                    List.of(new Diagnostic(
                        path.toString(), 1, 1,
                        "FILE001", Severity.ERROR,
                        e.getMessage(),
                        "Check file permissions and encoding."
                    )),
                    0,
                    RunStatus.FAILED
                );
            }
        }
    }

    static final class QualityGate {
        private final AnalysisPolicy policy;

        QualityGate(AnalysisPolicy policy) {
            this.policy = policy;
        }

        boolean permitsMerge(List<AnalysisResult> results) {
            long errors = results.stream()
                .mapToLong(r -> r.count(Severity.ERROR))
                .sum();

            long warnings = results.stream()
                .mapToLong(r -> r.count(Severity.WARNING))
                .sum();

            boolean executionSucceeded = results.stream()
                .allMatch(r -> r.status() == RunStatus.COMPLETED);

            return executionSucceeded
                && errors <= policy.maximumErrors()
                && warnings <= policy.maximumWarnings();
        }
    }

    static final class AnalysisService {
        private final StaticAnalyzer analyzer;
        private final SourceFormatter formatter;

        AnalysisService(
            StaticAnalyzer analyzer,
            SourceFormatter formatter
        ) {
            this.analyzer = analyzer;
            this.formatter = formatter;
        }

        List<AnalysisResult> analyzeRepository(
            List<Path> files,
            boolean formatFirst
        ) {
            List<AnalysisResult> results = new ArrayList<>();

            for (Path file : files) {
                if (formatFirst) {
                    try {
                        formatter.formatFile(file);
                    } catch (IOException e) {
                        results.add(new AnalysisResult(
                            file.toString(),
                            List.of(new Diagnostic(
                                file.toString(), 1, 1,
                                "FILE002", Severity.ERROR,
                                "Formatting failed: " + e.getMessage(),
                                "Check file access and write permissions."
                            )),
                            0,
                            RunStatus.FAILED
                        ));
                        continue;
                    }
                }

                results.add(analyzer.analyzeFile(file));
            }

            return List.copyOf(results);
        }
    }

    private static RuleRegistry createRegistry() {
        RuleRegistry registry = new RuleRegistry();

        registry.register(new AnalysisRule(
            "SEC001", "Dynamic code evaluation",
            Severity.ERROR, Category.SECURITY, true
        ));

        registry.register(new AnalysisRule(
            "SEC002", "Unsafe process execution",
            Severity.ERROR, Category.SECURITY, true
        ));

        registry.register(new AnalysisRule(
            "FMT001", "Maximum line length",
            Severity.WARNING, Category.FORMATTING, true
        ));

        registry.register(new AnalysisRule(
            "FMT002", "Trailing whitespace",
            Severity.WARNING, Category.FORMATTING, true
        ));

        registry.register(new AnalysisRule(
            "FMT003", "Tab indentation",
            Severity.WARNING, Category.FORMATTING, true
        ));

        registry.register(new AnalysisRule(
            "FMT004", "Final newline",
            Severity.WARNING, Category.FORMATTING, true
        ));

        registry.register(new AnalysisRule(
            "STYLE001", "Direct console output",
            Severity.INFO, Category.MAINTAINABILITY, true
        ));

        registry.register(new AnalysisRule(
            "MAINT001", "Unresolved TODO",
            Severity.WARNING, Category.MAINTAINABILITY, true
        ));

        return registry;
    }

    private static void printResults(
        List<AnalysisResult> results,
        boolean mergeAllowed
    ) {
        for (AnalysisResult result : results) {
            System.out.println("\nFile: " + result.filename());
            System.out.println("Status: " + result.status());

            for (Diagnostic diagnostic : result.diagnostics()) {
                System.out.printf(
                    "%s:%d:%d %s [%s] %s%n",
                    diagnostic.filename(),
                    diagnostic.line(),
                    diagnostic.column(),
                    diagnostic.severity(),
                    diagnostic.ruleId(),
                    diagnostic.message()
                );
                System.out.println(
                    "  Suggestion: " + diagnostic.suggestion()
                );
            }

            System.out.printf(
                "Errors: %d | Warnings: %d | Info: %d%n",
                result.count(Severity.ERROR),
                result.count(Severity.WARNING),
                result.count(Severity.INFO)
            );
        }

        System.out.println("\nRepository quality gate: " +
            (mergeAllowed ? "PASSED" : "FAILED"));
    }

    public static void main(String[] args) {
        try {
            RuleRegistry registry = createRegistry();

            AnalysisPolicy policy = new AnalysisPolicy(
                100,
                0,
                5,
                false,
                Collections.emptyList()
            );

            StaticAnalyzer analyzer = new StaticAnalyzer(
                registry, policy
            );

            AnalysisService service = new AnalysisService(
                analyzer, new SourceFormatter()
            );

            List<Path> files = new ArrayList<>();
            boolean formatFirst = false;

            for (String arg : args) {
                if (arg.equals("--fix")) {
                    formatFirst = true;
                } else {
                    files.add(Path.of(arg));
                }
            }

            List<AnalysisResult> results;

            if (files.isEmpty()) {
                String sample = """
                    public class PaymentService {
                        public void process(String input) {
                            System.out.println("Processing");
                            Object value = eval(input);
                        }
                    }
                    """;

                results = List.of(
                    analyzer.analyze("PaymentService.java", sample)
                );
            } else {
                results = service.analyzeRepository(
                    files, formatFirst
                );
            }

            QualityGate gate = new QualityGate(policy);
            boolean allowed = gate.permitsMerge(results);

            printResults(results, allowed);

            System.exit(allowed ? 0 : 1);

        } catch (IllegalArgumentException e) {
            System.err.println("Configuration error: " + e.getMessage());
            System.exit(2);
        }
    }
}
