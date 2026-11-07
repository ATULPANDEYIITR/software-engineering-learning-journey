#!/usr/bin/env python3
"""
Static Analysis Toolkit
Demonstrates source-code linting, formatting, AST analysis,
security checks, diagnostic reporting, and automatic corrections.

Python standard library only.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import tokenize
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class Diagnostic:
    file: str
    line: int
    column: int
    rule: str
    severity: Severity
    message: str
    suggestion: str = ""


@dataclass
class AnalysisResult:
    file: str
    diagnostics: list[Diagnostic]
    lines_analyzed: int

    @property
    def error_count(self) -> int:
        return sum(d.severity == Severity.ERROR for d in self.diagnostics)

    @property
    def warning_count(self) -> int:
        return sum(d.severity == Severity.WARNING for d in self.diagnostics)


class PythonAnalyzer(ast.NodeVisitor):
    """AST-based rules that inspect Python program structure."""

    def __init__(self, filename: str):
        self.filename = filename
        self.diagnostics: list[Diagnostic] = []

    def report(
        self,
        node: ast.AST,
        rule: str,
        severity: Severity,
        message: str,
        suggestion: str = "",
    ) -> None:
        self.diagnostics.append(
            Diagnostic(
                self.filename,
                getattr(node, "lineno", 1),
                getattr(node, "col_offset", 0) + 1,
                rule,
                severity,
                message,
                suggestion,
            )
        )

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            if node.func.id in {"eval", "exec"}:
                self.report(
                    node,
                    "SEC001",
                    Severity.ERROR,
                    f"Use of potentially unsafe {node.func.id}().",
                    "Use explicit parsing or a restricted operation.",
                )
            elif node.func.id == "print":
                self.report(
                    node,
                    "STYLE001",
                    Severity.INFO,
                    "Direct print() call found.",
                    "Use a configured logger in production applications.",
                )

        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is None:
            self.report(
                node,
                "ERR001",
                Severity.WARNING,
                "Bare except catches all exceptions.",
                "Catch specific exception classes.",
            )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if len(node.args.defaults) > 0:
            defaults = node.args.defaults
            for default in defaults:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    self.report(
                        default,
                        "BUG001",
                        Severity.ERROR,
                        f"Mutable default argument in function '{node.name}'.",
                        "Use None and initialize the value inside the function.",
                    )

        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            self.report(
                node,
                "DES001",
                Severity.WARNING,
                f"Function '{node.name}' has no implementation.",
                "Implement the function or remove it.",
            )

        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == "pickle":
                self.report(
                    node,
                    "SEC002",
                    Severity.WARNING,
                    "Pickle can execute code when loading untrusted data.",
                    "Use a safe data serialization format for untrusted input.",
                )
        self.generic_visit(node)


class StaticAnalyzer:
    """Coordinates lexical checks, AST rules, and formatting."""

    def __init__(self, max_line_length: int = 88):
        if max_line_length < 20:
            raise ValueError("Maximum line length must be at least 20.")
        self.max_line_length = max_line_length

    def analyze_text(self, source: str, filename: str = "<memory>") -> AnalysisResult:
        diagnostics: list[Diagnostic] = []
        lines = source.splitlines()

        for number, line in enumerate(lines, start=1):
            if line.rstrip(" \t") != line:
                diagnostics.append(
                    Diagnostic(
                        filename, number, len(line.rstrip(" \t")) + 1,
                        "FMT001", Severity.WARNING,
                        "Trailing whitespace detected.",
                        "Remove trailing whitespace.",
                    )
                )

            if len(line) > self.max_line_length:
                diagnostics.append(
                    Diagnostic(
                        filename, number, self.max_line_length + 1,
                        "FMT002", Severity.WARNING,
                        f"Line exceeds {self.max_line_length} characters.",
                        "Split the statement into shorter lines.",
                    )
                )

            if "\t" in line:
                diagnostics.append(
                    Diagnostic(
                        filename, number, line.index("\t") + 1,
                        "FMT003", Severity.WARNING,
                        "Tab character detected.",
                        "Use spaces for indentation.",
                    )
                )

        if source and not source.endswith("\n"):
            diagnostics.append(
                Diagnostic(
                    filename, len(lines), 1,
                    "FMT004", Severity.WARNING,
                    "Missing final newline.",
                    "Add a newline at the end of the file.",
                )
            )

        try:
            # AST parsing catches syntax errors before semantic inspection.
            tree = ast.parse(source, filename=filename)
            visitor = PythonAnalyzer(filename)
            visitor.visit(tree)
            diagnostics.extend(visitor.diagnostics)

        except SyntaxError as exc:
            diagnostics.append(
                Diagnostic(
                    filename,
                    exc.lineno or 1,
                    exc.offset or 1,
                    "SYN001",
                    Severity.ERROR,
                    exc.msg,
                    "Correct the syntax error before further analysis.",
                )
            )

        diagnostics.sort(key=lambda d: (d.line, d.column, d.rule))

        return AnalysisResult(filename, diagnostics, len(lines))

    def analyze_file(self, path: Path) -> AnalysisResult:
        try:
            with tokenize.open(str(path)) as file:
                source = file.read()
        except (OSError, UnicodeError, SyntaxError) as exc:
            diagnostic = Diagnostic(
                str(path), 1, 1, "FILE001", Severity.ERROR,
                f"Unable to read source file: {exc}",
            )
            return AnalysisResult(str(path), [diagnostic], 0)

        return self.analyze_text(source, str(path))

    @staticmethod
    def format_source(source: str) -> str:
        """Apply safe, non-semantic formatting corrections."""
        formatted_lines = [
            line.rstrip(" \t").expandtabs(4)
            for line in source.splitlines()
        ]
        result = "\n".join(formatted_lines)
        return result + "\n" if result else ""

    def analyze_and_format(
        self, path: Path, write: bool = False
    ) -> AnalysisResult:
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            return AnalysisResult(
                str(path),
                [Diagnostic(
                    str(path), 1, 1, "FILE001",
                    Severity.ERROR, str(exc)
                )],
                0,
            )

        result = self.analyze_text(source, str(path))

        if write:
            formatted = self.format_source(source)
            if formatted != source:
                temporary = path.with_suffix(path.suffix + ".tmp")
                try:
                    temporary.write_text(formatted, encoding="utf-8")
                    temporary.replace(path)
                except OSError:
                    temporary.unlink(missing_ok=True)
                    raise

        return result


def create_demo_source() -> str:
    return (
        "def calculate_total(items=[]):   \n"
        "\ttry:\n"
        "\t\treturn eval('1 + 2')\n"
        "\texcept:\n"
        "\t\treturn 0\n"
        "\n"
        "def unfinished():\n"
        "\tpass\n"
    )


def print_result(result: AnalysisResult) -> None:
    print(f"\nFile: {result.file}")
    print(f"Lines analyzed: {result.lines_analyzed}")

    if not result.diagnostics:
        print("No issues found.")
        return

    for item in result.diagnostics:
        print(
            f"{item.file}:{item.line}:{item.column}: "
            f"{item.severity.value.upper()} "
            f"[{item.rule}] {item.message}"
        )
        if item.suggestion:
            print(f"    Suggestion: {item.suggestion}")

    print(
        f"Errors: {result.error_count} | "
        f"Warnings: {result.warning_count}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Static analysis and formatting toolkit."
    )
    parser.add_argument("files", nargs="*", type=Path)
    parser.add_argument("--max-line-length", type=int, default=88)
    parser.add_argument("--fix", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--fail-on-warning", action="store_true")

    args = parser.parse_args()

    try:
        analyzer = StaticAnalyzer(args.max_line_length)
    except ValueError as exc:
        parser.error(str(exc))

    if args.files:
        paths = args.files
    else:
        paths = []
        demo = create_demo_source()
        result = analyzer.analyze_text(demo, "demo.py")
        print_result(result)
        return int(
            result.error_count > 0
            or (args.fail_on_warning and result.warning_count > 0)
        )

    all_results = []

    for path in paths:
        if not path.is_file():
            result = AnalysisResult(
                str(path),
                [Diagnostic(
                    str(path), 1, 1, "FILE002",
                    Severity.ERROR, "File does not exist."
                )],
                0,
            )
        elif path.suffix != ".py":
            result = AnalysisResult(
                str(path),
                [Diagnostic(
                    str(path), 1, 1, "FILE003",
                    Severity.ERROR, "Only Python files are supported."
                )],
                0,
            )
        else:
            try:
                result = analyzer.analyze_and_format(path, args.fix)
            except OSError as exc:
                result = AnalysisResult(
                    str(path),
                    [Diagnostic(
                        str(path), 1, 1, "FILE004",
                        Severity.ERROR, f"Formatting failed: {exc}"
                    )],
                    0,
                )

        all_results.append(result)

    if args.json:
        print(json.dumps(
            [
                {
                    "file": r.file,
                    "lines_analyzed": r.lines_analyzed,
                    "errors": r.error_count,
                    "warnings": r.warning_count,
                    "diagnostics": [
                        {
                            **asdict(d),
                            "severity": d.severity.value,
                        }
                        for d in r.diagnostics
                    ],
                }
                for r in all_results
            ],
            indent=2,
        ))
    else:
        for result in all_results:
            print_result(result)

    errors = sum(r.error_count for r in all_results)
    warnings = sum(r.warning_count for r in all_results)

    print(f"\nTotal files: {len(all_results)}")
    print(f"Total errors: {errors}")
    print(f"Total warnings: {warnings}")

    return int(errors > 0 or (args.fail_on_warning and warnings > 0))


if __name__ == "__main__":
    sys.exit(main())
