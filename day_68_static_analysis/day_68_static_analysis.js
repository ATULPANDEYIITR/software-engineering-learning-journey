#!/usr/bin/env node
"use strict";

/*
 * Static Analysis Engine for JavaScript
 *
 * Features:
 * - Lexical scanning
 * - Basic syntax-pattern checks
 * - Security and quality rules
 * - Formatting corrections
 * - Asynchronous multi-file processing
 * - JSON diagnostics
 *
 * Runtime: Node.js 18+
 * Dependencies: Node.js standard library
 */

const fs = require("node:fs/promises");
const path = require("node:path");
const EventEmitter = require("node:events");

const Severity = Object.freeze({
    ERROR: "error",
    WARNING: "warning",
    INFO: "info"
});

class Diagnostic {
    constructor(file, line, column, rule, severity, message, suggestion = "") {
        Object.assign(this, {
            file, line, column, rule, severity, message, suggestion
        });
    }
}

class AnalysisPolicy {
    constructor({
        maxLineLength = 100,
        allowConsole = false,
        allowDebugger = false,
        allowEval = false
    } = {}) {
        if (!Number.isInteger(maxLineLength) || maxLineLength < 20) {
            throw new RangeError("maxLineLength must be at least 20.");
        }

        this.maxLineLength = maxLineLength;
        this.allowConsole = allowConsole;
        this.allowDebugger = allowDebugger;
        this.allowEval = allowEval;
        Object.freeze(this);
    }
}

class JavaScriptAnalyzer extends EventEmitter {
    constructor(policy = new AnalysisPolicy()) {
        super();
        this.policy = policy;
    }

    analyze(source, filename = "<memory>") {
        if (typeof source !== "string") {
            throw new TypeError("Source must be a string.");
        }

        const diagnostics = [];
        const lines = source.split(/\r?\n/);

        const add = (line, column, rule, severity, message, suggestion = "") => {
            const diagnostic = new Diagnostic(
                filename, line, column, rule, severity, message, suggestion
            );
            diagnostics.push(diagnostic);
            this.emit("diagnostic", diagnostic);
        };

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            const lineNumber = i + 1;

            if (line.length > this.policy.maxLineLength) {
                add(
                    lineNumber,
                    this.policy.maxLineLength + 1,
                    "FMT001",
                    Severity.WARNING,
                    "Line exceeds configured maximum length.",
                    "Split the statement into smaller expressions."
                );
            }

            if (/\s+$/.test(line)) {
                add(
                    lineNumber,
                    line.length,
                    "FMT002",
                    Severity.WARNING,
                    "Trailing whitespace detected.",
                    "Remove trailing whitespace."
                );
            }

            if (/\t/.test(line)) {
                add(
                    lineNumber,
                    line.indexOf("\t") + 1,
                    "FMT003",
                    Severity.WARNING,
                    "Tab character detected.",
                    "Use spaces consistently."
                );
            }

            if (!this.policy.allowDebugger && /\bdebugger\s*;?/.test(line)) {
                add(
                    lineNumber,
                    line.search(/\bdebugger\b/) + 1,
                    "DBG001",
                    Severity.WARNING,
                    "Debugger statement found.",
                    "Remove debugger statements before deployment."
                );
            }

            if (!this.policy.allowConsole && /\bconsole\.(log|debug)\s*\(/.test(line)) {
                add(
                    lineNumber,
                    line.search(/\bconsole\./) + 1,
                    "STYLE001",
                    Severity.INFO,
                    "Console output found.",
                    "Use an application logging facility."
                );
            }

            if (!this.policy.allowEval && /\beval\s*\(/.test(line)) {
                add(
                    lineNumber,
                    line.search(/\beval\s*\(/) + 1,
                    "SEC001",
                    Severity.ERROR,
                    "Dynamic evaluation using eval() is unsafe.",
                    "Use explicit parsing and validated operations."
                );
            }

            if (/==(?!=)/.test(line)) {
                add(
                    lineNumber,
                    line.search(/==(?!=)/) + 1,
                    "STYLE002",
                    Severity.WARNING,
                    "Loose equality operator detected.",
                    "Use strict equality when appropriate."
                );
            }

            if (/^\s*var\s+/.test(line)) {
                add(
                    lineNumber,
                    line.search(/\bvar\b/) + 1,
                    "STYLE003",
                    Severity.INFO,
                    "var declaration found.",
                    "Prefer const or let."
                );
            }
        }

        if (source.length > 0 && !source.endsWith("\n")) {
            add(
                lines.length,
                1,
                "FMT004",
                Severity.WARNING,
                "Missing final newline.",
                "Add a newline at the end of the file."
            );
        }

        // Detect duplicate declarations within a simple function-independent
        // scope approximation. Full scope analysis requires a JavaScript AST.
        const declarationNames = new Map();

        for (let i = 0; i < lines.length; i++) {
            const match = lines[i].match(
                /^\s*(?:const|let|var)\s+([A-Za-z_$][\w$]*)/
            );

            if (match) {
                const name = match[1];
                if (declarationNames.has(name)) {
                    add(
                        i + 1,
                        lines[i].indexOf(name) + 1,
                        "DUP001",
                        Severity.WARNING,
                        `Repeated declaration name '${name}'.`,
                        "Check the declaration scope and variable naming."
                    );
                } else {
                    declarationNames.set(name, i + 1);
                }
            }
        }

        // Node's parser is used to catch JavaScript syntax errors.
        // The analysis rules above remain deliberately dependency-free.
        try {
            new Function(source);
        } catch (error) {
            const match = error.stack?.match(/<anonymous>:(\d+):(\d+)/);
            add(
                Number(match?.[1] || 1),
                Number(match?.[2] || 1),
                "SYN001",
                Severity.ERROR,
                `Syntax validation failed: ${error.message}`,
                "Correct the JavaScript syntax."
            );
        }

        diagnostics.sort(
            (a, b) => a.line - b.line || a.column - b.column
        );

        const result = {
            file: filename,
            linesAnalyzed: lines.length,
            diagnostics,
            errors: diagnostics.filter(
                d => d.severity === Severity.ERROR
            ).length,
            warnings: diagnostics.filter(
                d => d.severity === Severity.WARNING
            ).length
        };

        this.emit("analysisComplete", result);
        return result;
    }

    format(source) {
        if (typeof source !== "string") {
            throw new TypeError("Source must be a string.");
        }

        const lines = source.split(/\r?\n/).map(
            line => line.replace(/[ \t]+$/g, "").replace(/\t/g, "    ")
        );

        let formatted = lines.join("\n");

        if (formatted && !formatted.endsWith("\n")) {
            formatted += "\n";
        }

        return formatted;
    }
}

class AnalysisService {
    constructor(analyzer, concurrency = 4) {
        if (!Number.isInteger(concurrency) || concurrency < 1) {
            throw new RangeError("Concurrency must be positive.");
        }

        this.analyzer = analyzer;
        this.concurrency = concurrency;
    }

    async analyzeFile(filename, options = {}) {
        const absolutePath = path.resolve(filename);

        try {
            const stat = await fs.stat(absolutePath);

            if (!stat.isFile()) {
                throw new Error("Path is not a regular file.");
            }

            if (stat.size > 5 * 1024 * 1024) {
                throw new Error("File exceeds the 5 MB analysis limit.");
            }

            let source = await fs.readFile(absolutePath, "utf8");

            if (options.fix) {
                const formatted = this.analyzer.format(source);

                if (formatted !== source) {
                    const handle = await fs.open(absolutePath, "r+");
                    try {
                        await handle.truncate(0);
                        await handle.writeFile(formatted, "utf8");
                    } finally {
                        await handle.close();
                    }
                    source = formatted;
                }
            }

            return this.analyzer.analyze(source, absolutePath);
        } catch (error) {
            return {
                file: absolutePath,
                linesAnalyzed: 0,
                diagnostics: [
                    new Diagnostic(
                        absolutePath, 1, 1,
                        "FILE001", Severity.ERROR,
                        error.message
                    )
                ],
                errors: 1,
                warnings: 0
            };
        }
    }

    async analyzeFiles(filenames, options = {}) {
        const results = new Array(filenames.length);
        let nextIndex = 0;

        const workers = Array.from(
            { length: Math.min(this.concurrency, filenames.length) },
            async () => {
                while (true) {
                    const index = nextIndex++;

                    if (index >= filenames.length) {
                        break;
                    }

                    results[index] = await this.analyzeFile(
                        filenames[index], options
                    );
                }
            }
        );

        await Promise.all(workers);
        return results;
    }
}

function summarize(results) {
    return results.reduce(
        (summary, result) => {
            summary.files++;
            summary.errors += result.errors;
            summary.warnings += result.warnings;
            summary.lines += result.linesAnalyzed;
            return summary;
        },
        { files: 0, errors: 0, warnings: 0, lines: 0 }
    );
}

async function main() {
    const args = process.argv.slice(2);

    const jsonMode = args.includes("--json");
    const fixMode = args.includes("--fix");
    const files = args.filter(arg => !arg.startsWith("--"));

    const analyzer = new JavaScriptAnalyzer(
        new AnalysisPolicy({
            maxLineLength: 100,
            allowConsole: false,
            allowDebugger: false,
            allowEval: false
        })
    );

    analyzer.on("diagnostic", diagnostic => {
        if (!jsonMode) {
            process.stderr.write(
                `${diagnostic.file}:${diagnostic.line}:` +
                `${diagnostic.column} ${diagnostic.severity.toUpperCase()} ` +
                `[${diagnostic.rule}] ${diagnostic.message}\n`
            );
        }
    });

    const service = new AnalysisService(analyzer, 4);

    if (files.length === 0) {
        const sample = [
            "var total = 10;  ",
            "if (total == 10) {",
            "    console.log(eval('2 + 3'));",
            "    debugger;",
            "}"
        ].join("\n");

        const result = analyzer.analyze(sample, "example.js");

        if (jsonMode) {
            process.stdout.write(JSON.stringify(result, null, 2) + "\n");
        } else {
            process.stdout.write(
                `Errors: ${result.errors}\nWarnings: ${result.warnings}\n`
            );
        }

        return result.errors > 0 ? 1 : 0;
    }

    const results = await service.analyzeFiles(files, {
        fix: fixMode
    });

    if (jsonMode) {
        process.stdout.write(JSON.stringify(results, null, 2) + "\n");
    } else {
        const summary = summarize(results);
        process.stdout.write(
            `\nFiles: ${summary.files}\n` +
            `Lines: ${summary.lines}\n` +
            `Errors: ${summary.errors}\n` +
            `Warnings: ${summary.warnings}\n`
        );
    }

    return results.some(r => r.errors > 0) ? 1 : 0;
}

main()
    .then(code => {
        process.exitCode = code;
    })
    .catch(error => {
        process.stderr.write(`Analysis failure: ${error.message}\n`);
        process.exitCode = 2;
    });
