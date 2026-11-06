#!/usr/bin/env python3
"""
Test Coverage: Coverage Metrics and Meaningful Testing

Demonstrates:
- Statement, branch, and function coverage
- Test execution tracking
- Coverage thresholds
- Boundary and negative testing
- Coverage gaps
- Test quality checks
- JSON coverage reports
- Failure handling
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable
import json
import unittest


class CoverageType(Enum):
    STATEMENT = "statement"
    BRANCH = "branch"
    FUNCTION = "function"


@dataclass
class CoverageMetric:
    total: set[str] = field(default_factory=set)
    covered: set[str] = field(default_factory=set)

    def register(self, item: str) -> None:
        self.total.add(item)

    def hit(self, item: str) -> None:
        if item not in self.total:
            raise ValueError(f"Unknown coverage item: {item}")
        self.covered.add(item)

    @property
    def percentage(self) -> float:
        if not self.total:
            return 100.0
        return len(self.covered) / len(self.total) * 100

    @property
    def missed(self) -> set[str]:
        return self.total - self.covered


class CoverageTracker:
    def __init__(self):
        self.metrics = {
            metric: CoverageMetric()
            for metric in CoverageType
        }
        self.test_results = []

    def register(self, metric: CoverageType, item: str) -> None:
        self.metrics[metric].register(item)

    def hit(self, metric: CoverageType, item: str) -> None:
        self.metrics[metric].hit(item)

    def record_test(self, name: str, passed: bool, error=None):
        self.test_results.append({
            "name": name,
            "passed": passed,
            "error": str(error) if error else None
        })

    def report(self) -> dict:
        result = {}

        for metric, data in self.metrics.items():
            result[metric.value] = {
                "total": len(data.total),
                "covered": len(data.covered),
                "missed": sorted(data.missed),
                "percentage": round(data.percentage, 2)
            }

        result["tests"] = {
            "total": len(self.test_results),
            "passed": sum(t["passed"] for t in self.test_results),
            "failed": sum(not t["passed"] for t in self.test_results)
        }

        return result

    def meets_threshold(self, threshold: float = 80.0) -> bool:
        if not 0 <= threshold <= 100:
            raise ValueError("Threshold must be between 0 and 100")

        return all(
            metric.percentage >= threshold
            for metric in self.metrics.values()
        )


coverage = CoverageTracker()


def initialize_coverage():
    definitions = {
        CoverageType.STATEMENT: [
            "divide.validation",
            "divide.calculation",
            "classify.validation",
            "classify.negative",
            "classify.zero",
            "classify.positive",
            "classify.large",
        ],
        CoverageType.BRANCH: [
            "divide.zero_denominator",
            "classify.negative",
            "classify.zero",
            "classify.positive",
            "classify.large",
        ],
        CoverageType.FUNCTION: [
            "safe_divide",
            "classify_number",
        ]
    }

    for metric, items in definitions.items():
        for item in items:
            coverage.register(metric, item)


def safe_divide(a: float, b: float) -> float:
    coverage.hit(CoverageType.FUNCTION, "safe_divide")
    coverage.hit(CoverageType.STATEMENT, "divide.validation")

    if not isinstance(a, (int, float)) or isinstance(a, bool):
        raise TypeError("Numerator must be numeric")

    if not isinstance(b, (int, float)) or isinstance(b, bool):
        raise TypeError("Denominator must be numeric")

    if b == 0:
        coverage.hit(CoverageType.BRANCH, "divide.zero_denominator")
        raise ZeroDivisionError("Cannot divide by zero")

    coverage.hit(CoverageType.STATEMENT, "divide.calculation")
    return a / b


def classify_number(value: float) -> str:
    coverage.hit(CoverageType.FUNCTION, "classify_number")
    coverage.hit(CoverageType.STATEMENT, "classify.validation")

    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError("Value must be numeric")

    if value < 0:
        coverage.hit(CoverageType.BRANCH, "classify.negative")
        coverage.hit(CoverageType.STATEMENT, "classify.negative")
        return "negative"

    if value == 0:
        coverage.hit(CoverageType.BRANCH, "classify.zero")
        coverage.hit(CoverageType.STATEMENT, "classify.zero")
        return "zero"

    coverage.hit(CoverageType.BRANCH, "classify.positive")
    coverage.hit(CoverageType.STATEMENT, "classify.positive")

    if value >= 100:
        coverage.hit(CoverageType.BRANCH, "classify.large")
        coverage.hit(CoverageType.STATEMENT, "classify.large")
        return "large"

    return "positive"


class TestApplication(unittest.TestCase):

    def test_normal_division(self):
        self.assertEqual(safe_divide(10, 2), 5)

    def test_negative_division(self):
        self.assertEqual(safe_divide(-10, 2), -5)

    def test_zero_division(self):
        with self.assertRaises(ZeroDivisionError):
            safe_divide(10, 0)

    def test_invalid_numerator(self):
        with self.assertRaises(TypeError):
            safe_divide("10", 2)

    def test_invalid_denominator(self):
        with self.assertRaises(TypeError):
            safe_divide(10, "2")

    def test_negative_number(self):
        self.assertEqual(classify_number(-5), "negative")

    def test_zero_number(self):
        self.assertEqual(classify_number(0), "zero")

    def test_positive_number(self):
        self.assertEqual(classify_number(25), "positive")

    def test_large_number(self):
        self.assertEqual(classify_number(100), "large")

    def test_invalid_classification(self):
        with self.assertRaises(TypeError):
            classify_number("invalid")

    def test_boolean_rejection(self):
        with self.assertRaises(TypeError):
            classify_number(True)


class RecordingTestResult(unittest.TextTestResult):
    def addSuccess(self, test):
        super().addSuccess(test)
        coverage.record_test(test.id(), True)

    def addFailure(self, test, err):
        super().addFailure(test, err)
        coverage.record_test(test.id(), False, err[1])

    def addError(self, test, err):
        super().addError(test, err)
        coverage.record_test(test.id(), False, err[1])


def save_report(report: dict, filename: str = "coverage-report.json"):
    path = Path(filename)

    # Prevent accidental writing outside the current working directory.
    if path.name != filename or path.is_absolute():
        raise ValueError("Invalid report filename")

    path.write_text(
        json.dumps(report, indent=4),
        encoding="utf-8"
    )


def main():
    initialize_coverage()

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        TestApplication
    )

    runner = unittest.TextTestRunner(
        verbosity=2,
        resultclass=RecordingTestResult
    )

    result = runner.run(suite)
    report = coverage.report()

    print("\nCOVERAGE REPORT")

    for metric in CoverageType:
        data = report[metric.value]
        print(
            f"{metric.value.title():12} "
            f"{data['covered']}/{data['total']} "
            f"({data['percentage']}%)"
        )

        if data["missed"]:
            print("  Uncovered:", ", ".join(data["missed"]))

    print("\nTEST RESULTS")
    print(json.dumps(report["tests"], indent=4))

    threshold = 80.0
    passed = (
        result.wasSuccessful()
        and coverage.meets_threshold(threshold)
    )

    print(f"\nCoverage threshold: {threshold}%")
    print("Quality gate:", "PASSED" if passed else "FAILED")

    save_report(report)
    print("Report saved to coverage-report.json")

    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
