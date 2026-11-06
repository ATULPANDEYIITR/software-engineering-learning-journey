import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.EnumMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Supplier;

/**
 * Enterprise Test Coverage Management
 *
 * Implements:
 * - Coverage measurement
 * - Test execution management
 * - Statement, branch and function coverage
 * - Coverage policies
 * - Test ownership and traceability
 * - Quality gates
 * - Immutable report snapshots
 * - Failure classification
 */

public class TestCoverageManager {

    enum MetricType {
        STATEMENT,
        BRANCH,
        FUNCTION
    }

    enum TestStatus {
        PASSED,
        FAILED
    }

    enum FailureCategory {
        ASSERTION,
        VALIDATION,
        UNEXPECTED
    }

    record CoverageItem(
        String id,
        MetricType type,
        String component
    ) {
        CoverageItem {
            if (id == null || id.isBlank()) {
                throw new IllegalArgumentException(
                    "Coverage item ID is required"
                );
            }

            if (component == null || component.isBlank()) {
                throw new IllegalArgumentException(
                    "Component is required"
                );
            }
        }
    }

    record TestCaseResult(
        String testId,
        TestStatus status,
        FailureCategory failureCategory,
        String message
    ) {}

    record MetricReport(
        int total,
        int covered,
        double percentage,
        Set<String> uncovered
    ) {
        MetricReport {
            uncovered = Set.copyOf(uncovered);
        }
    }

    record CoverageReport(
        Map<MetricType, MetricReport> metrics,
        int totalTests,
        int passedTests,
        int failedTests
    ) {
        CoverageReport {
            metrics = Map.copyOf(metrics);
        }
    }

    record CoveragePolicy(
        double minimumStatementCoverage,
        double minimumBranchCoverage,
        double minimumFunctionCoverage,
        int minimumPassingTests
    ) {
        CoveragePolicy {
            if (!validPercentage(minimumStatementCoverage)
                || !validPercentage(minimumBranchCoverage)
                || !validPercentage(minimumFunctionCoverage)
                || minimumPassingTests < 0) {
                throw new IllegalArgumentException(
                    "Invalid coverage policy"
                );
            }
        }

        private static boolean validPercentage(double value) {
            return Double.isFinite(value) && value >= 0 && value <= 100;
        }
    }

    static class CoverageException extends RuntimeException {
        CoverageException(String message) {
            super(message);
        }
    }

    static class CoverageService {

        private final Map<MetricType, Set<String>> registered =
            new EnumMap<>(MetricType.class);

        private final Map<MetricType, Set<String>> covered =
            new EnumMap<>(MetricType.class);

        private final List<TestCaseResult> testResults =
            new ArrayList<>();

        CoverageService() {
            for (MetricType type : MetricType.values()) {
                registered.put(type, new LinkedHashSet<>());
                covered.put(type, new LinkedHashSet<>());
            }
        }

        void register(CoverageItem item) {
            if (!registered.get(item.type()).add(item.id())) {
                throw new CoverageException(
                    "Duplicate coverage item: " + item.id()
                );
            }
        }

        void record(MetricType type, String id) {
            if (!registered.get(type).contains(id)) {
                throw new CoverageException(
                    "Unknown coverage item: " + id
                );
            }

            covered.get(type).add(id);
        }

        void recordTest(TestCaseResult result) {
            testResults.add(result);
        }

        private MetricReport calculate(MetricType type) {
            Set<String> total = registered.get(type);
            Set<String> executed = covered.get(type);

            Set<String> missing = new LinkedHashSet<>(total);
            missing.removeAll(executed);

            double percentage = total.isEmpty()
                ? 100.0
                : 100.0 * executed.size() / total.size();

            return new MetricReport(
                total.size(),
                executed.size(),
                percentage,
                missing
            );
        }

        CoverageReport generateReport() {
            Map<MetricType, MetricReport> reports =
                new EnumMap<>(MetricType.class);

            for (MetricType type : MetricType.values()) {
                reports.put(type, calculate(type));
            }

            int passed = (int) testResults.stream()
                .filter(t -> t.status() == TestStatus.PASSED)
                .count();

            return new CoverageReport(
                reports,
                testResults.size(),
                passed,
                testResults.size() - passed
            );
        }

        boolean evaluate(CoveragePolicy policy) {
            CoverageReport report = generateReport();

            return report.metrics().get(MetricType.STATEMENT)
                    .percentage() >= policy.minimumStatementCoverage()
                && report.metrics().get(MetricType.BRANCH)
                    .percentage() >= policy.minimumBranchCoverage()
                && report.metrics().get(MetricType.FUNCTION)
                    .percentage() >= policy.minimumFunctionCoverage()
                && report.passedTests() >= policy.minimumPassingTests()
                && report.failedTests() == 0;
        }
    }

    static class BusinessService {

        private final CoverageService coverage;

        BusinessService(CoverageService coverage) {
            this.coverage = coverage;
        }

        double divide(double numerator, double denominator) {
            coverage.record(MetricType.FUNCTION, "divide");
            coverage.record(MetricType.STATEMENT, "divide.validation");

            if (!Double.isFinite(numerator)
                || !Double.isFinite(denominator)) {
                throw new IllegalArgumentException(
                    "Inputs must be finite"
                );
            }

            if (denominator == 0.0) {
                coverage.record(MetricType.BRANCH, "divide.zero");
                throw new ArithmeticException("Division by zero");
            }

            coverage.record(MetricType.STATEMENT, "divide.calculation");

            double result = numerator / denominator;

            if (!Double.isFinite(result)) {
                throw new ArithmeticException("Invalid result");
            }

            return result;
        }

        String classify(double value) {
            coverage.record(MetricType.FUNCTION, "classify");
            coverage.record(MetricType.STATEMENT, "classify.validation");

            if (!Double.isFinite(value)) {
                throw new IllegalArgumentException(
                    "Value must be finite"
                );
            }

            if (value < 0) {
                coverage.record(MetricType.BRANCH, "classify.negative");
                coverage.record(
                    MetricType.STATEMENT,
                    "classify.negative"
                );
                return "negative";
            }

            if (value == 0) {
                coverage.record(MetricType.BRANCH, "classify.zero");
                coverage.record(
                    MetricType.STATEMENT,
                    "classify.zero"
                );
                return "zero";
            }

            coverage.record(MetricType.BRANCH, "classify.positive");
            coverage.record(
                MetricType.STATEMENT,
                "classify.positive"
            );

            if (value >= 100) {
                coverage.record(MetricType.BRANCH, "classify.large");
                coverage.record(
                    MetricType.STATEMENT,
                    "classify.large"
                );
                return "large";
            }

            return "positive";
        }
    }

    static class TestExecutor {

        private final CoverageService coverage;

        TestExecutor(CoverageService coverage) {
            this.coverage = coverage;
        }

        void execute(String testId, Runnable test) {
            try {
                test.run();

                coverage.recordTest(
                    new TestCaseResult(
                        testId,
                        TestStatus.PASSED,
                        null,
                        "Test passed"
                    )
                );

                System.out.println("[PASS] " + testId);

            } catch (AssertionError error) {
                recordFailure(
                    testId,
                    FailureCategory.ASSERTION,
                    error
                );

            } catch (IllegalArgumentException | ArithmeticException error) {
                recordFailure(
                    testId,
                    FailureCategory.VALIDATION,
                    error
                );

            } catch (RuntimeException error) {
                recordFailure(
                    testId,
                    FailureCategory.UNEXPECTED,
                    error
                );
            }
        }

        private void recordFailure(
            String testId,
            FailureCategory category,
            RuntimeException error
        ) {
            coverage.recordTest(
                new TestCaseResult(
                    testId,
                    TestStatus.FAILED,
                    category,
                    error.getMessage()
                )
            );

            System.out.println(
                "[FAIL] " + testId + ": " + error.getMessage()
            );
        }
    }

    static void registerDefinitions(CoverageService coverage) {

        Map<MetricType, List<String>> definitions =
            new EnumMap<>(MetricType.class);

        definitions.put(
            MetricType.STATEMENT,
            List.of(
                "divide.validation",
                "divide.calculation",
                "classify.validation",
                "classify.negative",
                "classify.zero",
                "classify.positive",
                "classify.large"
            )
        );

        definitions.put(
            MetricType.BRANCH,
            List.of(
                "divide.zero",
                "classify.negative",
                "classify.zero",
                "classify.positive",
                "classify.large"
            )
        );

        definitions.put(
            MetricType.FUNCTION,
            List.of("divide", "classify")
        );

        for (var entry : definitions.entrySet()) {
            for (String id : entry.getValue()) {
                coverage.register(
                    new CoverageItem(
                        id,
                        entry.getKey(),
                        "business-service"
                    )
                );
            }
        }
    }

    static void assertEquals(double actual, double expected) {
        if (Math.abs(actual - expected) > 1e-9) {
            throw new AssertionError(
                "Expected " + expected + ", received " + actual
            );
        }
    }

    static void assertEquals(String actual, String expected) {
        if (!expected.equals(actual)) {
            throw new AssertionError(
                "Expected " + expected + ", received " + actual
            );
        }
    }

    static void assertThrows(
        Class<? extends RuntimeException> expected,
        Runnable operation
    ) {
        try {
            operation.run();
        } catch (RuntimeException error) {
            if (expected.isInstance(error)) {
                return;
            }

            throw new AssertionError(
                "Unexpected exception: " + error.getClass().getSimpleName()
            );
        }

        throw new AssertionError("Expected exception was not thrown");
    }

    static void printReport(CoverageReport report) {
        System.out.println("\nENTERPRISE COVERAGE REPORT");

        for (MetricType type : MetricType.values()) {
            MetricReport metric = report.metrics().get(type);

            System.out.printf(
                "%-12s %d/%d (%.2f%%)%n",
                type,
                metric.covered(),
                metric.total(),
                metric.percentage()
            );

            if (!metric.uncovered().isEmpty()) {
                System.out.println(
                    "  Uncovered: " + metric.uncovered()
                );
            }
        }

        System.out.println(
            "\nTests: " + report.passedTests()
            + "/" + report.totalTests()
            + " passed"
        );
    }

    static void saveReport(
        CoverageReport report,
        Path file
    ) throws IOException {

        StringBuilder json = new StringBuilder();
        json.append("{\n  \"metrics\": {\n");

        int index = 0;

        for (MetricType type : MetricType.values()) {
            MetricReport metric = report.metrics().get(type);

            json.append("    \"")
                .append(type)
                .append("\": {")
                .append("\"total\": ")
                .append(metric.total())
                .append(", \"covered\": ")
                .append(metric.covered())
                .append(", \"percentage\": ")
                .append(String.format("%.2f", metric.percentage()))
                .append(", \"uncovered\": ")
                .append(metric.uncovered())
                .append("}");

            if (++index < MetricType.values().length) {
                json.append(",");
            }

            json.append("\n");
        }

        json.append("  },\n")
            .append("  \"tests\": {\n")
            .append("    \"total\": ").append(report.totalTests()).append(",\n")
            .append("    \"passed\": ").append(report.passedTests()).append(",\n")
            .append("    \"failed\": ").append(report.failedTests()).append("\n")
            .append("  }\n")
            .append("}\n");

        Files.writeString(file, json.toString());
    }

    public static void main(String[] args) {

        CoverageService coverage = new CoverageService();
        registerDefinitions(coverage);

        BusinessService service = new BusinessService(coverage);
        TestExecutor executor = new TestExecutor(coverage);

        executor.execute("TC-001-normal-division", () ->
            assertEquals(service.divide(20, 4), 5)
        );

        executor.execute("TC-002-negative-division", () ->
            assertEquals(service.divide(-20, 4), -5)
        );

        executor.execute("TC-003-zero-denominator", () ->
            assertThrows(
                ArithmeticException.class,
                () -> service.divide(10, 0)
            )
        );

        executor.execute("TC-004-invalid-input", () ->
            assertThrows(
                IllegalArgumentException.class,
                () -> service.divide(Double.NaN, 2)
            )
        );

        executor.execute("TC-005-negative-value", () ->
            assertEquals(service.classify(-5), "negative")
        );

        executor.execute("TC-006-zero-value", () ->
            assertEquals(service.classify(0), "zero")
        );

        executor.execute("TC-007-positive-value", () ->
            assertEquals(service.classify(25), "positive")
        );

        executor.execute("TC-008-large-value", () ->
            assertEquals(service.classify(100), "large")
        );

        executor.execute("TC-009-invalid-classification", () ->
            assertThrows(
                IllegalArgumentException.class,
                () -> service.classify(Double.POSITIVE_INFINITY)
            )
        );

        CoveragePolicy policy = new CoveragePolicy(
            80,
            80,
            80,
            9
        );

        CoverageReport report = coverage.generateReport();

        printReport(report);

        boolean eligible = coverage.evaluate(policy);

        System.out.println(
            "\nQuality gate: " + (eligible ? "PASSED" : "FAILED")
        );

        try {
            Path output = Path.of("coverage-report.json")
                .toAbsolutePath()
                .normalize();

            if (!output.getParent().equals(
                Path.of("").toAbsolutePath().normalize()
            )) {
                throw new IOException("Unsafe report destination");
            }

            saveReport(report, output);
            System.out.println("Report saved: " + output);

        } catch (IOException error) {
            System.err.println(
                "Report generation failed: " + error.getMessage()
            );
            System.exit(2);
        }

        if (!eligible) {
            System.exit(1);
        }
    }
}
