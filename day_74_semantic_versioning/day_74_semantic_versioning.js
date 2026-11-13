"use strict";

/**
 * Semantic Versioning 2.0.0
 *
 * Event-driven release management, dependency compatibility,
 * release policy evaluation, and version precedence.
 *
 * Runtime: Node.js 18+
 */

const { EventEmitter } = require("node:events");
const fs = require("node:fs/promises");

class SemanticVersionError extends Error {}
class ReleasePolicyError extends Error {}

const VERSION_PATTERN =
    /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$/;

class SemVer {
    constructor(major, minor, patch, prerelease = [], build = []) {
        for (const [name, value] of Object.entries({
            major, minor, patch
        })) {
            if (!Number.isSafeInteger(value) || value < 0) {
                throw new SemanticVersionError(
                    `${name} must be a non-negative safe integer`
                );
            }
        }

        this.major = major;
        this.minor = minor;
        this.patch = patch;
        this.prerelease = [...prerelease];
        this.build = [...build];

        for (const id of this.prerelease) {
            SemVer.validateIdentifier(id, true);
        }

        for (const id of this.build) {
            SemVer.validateIdentifier(id, false);
        }

        Object.freeze(this.prerelease);
        Object.freeze(this.build);
        Object.freeze(this);
    }

    static validateIdentifier(identifier, prerelease) {
        if (
            typeof identifier !== "string" ||
            !/^[0-9A-Za-z-]+$/.test(identifier)
        ) {
            throw new SemanticVersionError(
                "Invalid version identifier"
            );
        }

        if (
            prerelease &&
            /^\d+$/.test(identifier) &&
            identifier.length > 1 &&
            identifier.startsWith("0")
        ) {
            throw new SemanticVersionError(
                "Numeric prerelease identifiers cannot contain leading zeros"
            );
        }
    }

    static parse(value) {
        if (typeof value !== "string") {
            throw new SemanticVersionError(
                "Version must be a string"
            );
        }

        const match = VERSION_PATTERN.exec(value);

        if (!match) {
            throw new SemanticVersionError(
                `Invalid semantic version: ${value}`
            );
        }

        const [, major, minor, patch, pre, build] = match;

        return new SemVer(
            Number(major),
            Number(minor),
            Number(patch),
            pre ? pre.split(".") : [],
            build ? build.split(".") : []
        );
    }

    toString() {
        let result =
            `${this.major}.${this.minor}.${this.patch}`;

        if (this.prerelease.length) {
            result += `-${this.prerelease.join(".")}`;
        }

        if (this.build.length) {
            result += `+${this.build.join(".")}`;
        }

        return result;
    }

    static compareIdentifiers(a, b) {
        const an = /^\d+$/.test(a);
        const bn = /^\d+$/.test(b);

        if (an && bn) {
            const left = BigInt(a);
            const right = BigInt(b);

            return left < right ? -1 : left > right ? 1 : 0;
        }

        if (an) return -1;
        if (bn) return 1;

        return a < b ? -1 : a > b ? 1 : 0;
    }

    compare(other) {
        if (!(other instanceof SemVer)) {
            throw new TypeError(
                "Comparison requires a SemVer instance"
            );
        }

        for (const key of ["major", "minor", "patch"]) {
            if (this[key] !== other[key]) {
                return this[key] < other[key] ? -1 : 1;
            }
        }

        const a = this.prerelease;
        const b = other.prerelease;

        if (!a.length && !b.length) return 0;
        if (!a.length) return 1;
        if (!b.length) return -1;

        const length = Math.min(a.length, b.length);

        for (let i = 0; i < length; i++) {
            const result = SemVer.compareIdentifiers(a[i], b[i]);

            if (result !== 0) return result;
        }

        return Math.sign(a.length - b.length);
    }

    increment(type) {
        switch (type) {
            case "major":
                return new SemVer(this.major + 1, 0, 0);

            case "minor":
                return new SemVer(
                    this.major,
                    this.minor + 1,
                    0
                );

            case "patch":
                return new SemVer(
                    this.major,
                    this.minor,
                    this.patch + 1
                );

            default:
                throw new SemanticVersionError(
                    `Unsupported increment: ${type}`
                );
        }
    }

    static compare(a, b) {
        return a.compare(b);
    }
}

class VersionConstraint {
    constructor(operator, version) {
        if (!["=", ">", ">=", "<", "<="].includes(operator)) {
            throw new SemanticVersionError(
                `Unsupported operator: ${operator}`
            );
        }

        this.operator = operator;
        this.version = version;
        Object.freeze(this);
    }

    matches(candidate) {
        const result = candidate.compare(this.version);

        switch (this.operator) {
            case "=": return result === 0;
            case ">": return result > 0;
            case ">=": return result >= 0;
            case "<": return result < 0;
            case "<=": return result <= 0;
            default: return false;
        }
    }
}

class ReleasePolicy {
    constructor({
        requireTests = true,
        requireDocumentation = true,
        requireBreakingChangeNotes = true
    } = {}) {
        this.requireTests = requireTests;
        this.requireDocumentation = requireDocumentation;
        this.requireBreakingChangeNotes =
            requireBreakingChangeNotes;
    }

    evaluate(metadata) {
        const failures = [];

        if (this.requireTests && metadata.testsPassed !== true) {
            failures.push("Automated tests have not passed");
        }

        if (
            this.requireDocumentation &&
            metadata.documentationUpdated !== true
        ) {
            failures.push("Documentation must be updated");
        }

        if (
            this.requireBreakingChangeNotes &&
            metadata.breaking &&
            !metadata.migrationNotes
        ) {
            failures.push(
                "Breaking changes require migration notes"
            );
        }

        if (
            metadata.version.prerelease.length &&
            metadata.production === true
        ) {
            failures.push(
                "Prerelease versions cannot be production releases"
            );
        }

        return {
            eligible: failures.length === 0,
            failures
        };
    }
}

class ReleaseRegistry extends EventEmitter {
    #releases = new Map();
    #dependencies = new Map();
    #current = null;

    constructor(project, policy = new ReleasePolicy()) {
        super();

        if (!project || !project.trim()) {
            throw new ReleasePolicyError(
                "Project name is required"
            );
        }

        this.project = project.trim();
        this.policy = policy;
    }

    get currentVersion() {
        return this.#current;
    }

    get releases() {
        return [...this.#releases.values()].map(
            release => ({ ...release })
        );
    }

    register(versionText, metadata) {
        const version = SemVer.parse(versionText);
        const key = version.toString();

        if (this.#releases.has(key)) {
            throw new ReleasePolicyError(
                `Version already registered: ${key}`
            );
        }

        if (this.#current && version.compare(this.#current) <= 0) {
            throw new ReleasePolicyError(
                "Version precedence must increase"
            );
        }

        const policyResult = this.policy.evaluate({
            ...metadata,
            version
        });

        if (!policyResult.eligible) {
            throw new ReleasePolicyError(
                policyResult.failures.join("; ")
            );
        }

        const release = {
            version,
            description: metadata.description,
            published: false,
            dependencies: [...(metadata.dependencies || [])]
        };

        this.#releases.set(key, release);
        this.#dependencies.set(key, new Set(release.dependencies));

        this.emit("release:registered", {
            version: key
        });

        return release;
    }

    async publish(versionText) {
        const release = this.#releases.get(versionText);

        if (!release) {
            throw new ReleasePolicyError(
                "Unknown release"
            );
        }

        if (release.published) {
            throw new ReleasePolicyError(
                "Release already published"
            );
        }

        // Validate every dependency before changing state.
        for (const dependency of release.dependencies) {
            const required = this.#releases.get(dependency);

            if (!required || !required.published) {
                throw new ReleasePolicyError(
                    `Dependency is unavailable: ${dependency}`
                );
            }
        }

        // Yield control before publication to support event consumers.
        await Promise.resolve();

        release.published = true;
        this.#current = release.version;

        this.emit("release:published", {
            version: versionText,
            project: this.project
        });

        return release;
    }

    compatible(versionText, constraints) {
        const candidate = SemVer.parse(versionText);

        return constraints.every(
            constraint => constraint.matches(candidate)
        );
    }

    async export(filename) {
        const data = {
            project: this.project,
            currentVersion: this.#current
                ? this.#current.toString()
                : null,
            releases: this.#releases.size
        };

        await fs.writeFile(
            filename,
            JSON.stringify(data, null, 2),
            { encoding: "utf8", mode: 0o600 }
        );
    }
}

function determineReleaseType({
    breaking = false,
    feature = false,
    bugFix = false
}) {
    if (breaking) return "major";
    if (feature) return "minor";
    if (bugFix) return "patch";

    throw new SemanticVersionError(
        "No release-worthy change was identified"
    );
}

async function main() {
    console.log("SEMANTIC VERSIONING 2.0.0");

    const sequence = [
        "1.0.0-alpha",
        "1.0.0-alpha.1",
        "1.0.0-beta",
        "1.0.0-rc.1",
        "1.0.0"
    ];

    console.log("\nVersion precedence:");

    sequence
        .map(SemVer.parse)
        .sort((a, b) => a.compare(b))
        .forEach(version => console.log(version.toString()));

    const baseline = SemVer.parse("2.4.6");

    console.log("\nVersion increments:");

    for (const type of ["major", "minor", "patch"]) {
        console.log(type, baseline.increment(type).toString());
    }

    console.log("\nDependency compatibility:");

    const constraints = [
        new VersionConstraint(
            ">=",
            SemVer.parse("2.0.0")
        ),
        new VersionConstraint(
            "<",
            SemVer.parse("3.0.0")
        )
    ];

    const registry = new ReleaseRegistry("Payment API");

    registry.on("release:registered", event => {
        console.log("Registered:", event.version);
    });

    registry.on("release:published", event => {
        console.log("Published:", event.version);
    });

    registry.register("1.0.0", {
        description: "Initial stable API",
        testsPassed: true,
        documentationUpdated: true,
        production: true,
        breaking: false
    });

    await registry.publish("1.0.0");

    registry.register("1.1.0", {
        description: "Added transaction search",
        testsPassed: true,
        documentationUpdated: true,
        production: true,
        breaking: false,
        dependencies: ["1.0.0"]
    });

    await registry.publish("1.1.0");

    console.log(
        "\n2.5.3 compatible:",
        registry.compatible("2.5.3", constraints)
    );

    console.log(
        "\nRelease classification:",
        determineReleaseType({
            breaking: false,
            feature: true,
            bugFix: true
        })
    );

    console.log("\nRelease history:");

    for (const release of registry.releases) {
        console.log({
            version: release.version.toString(),
            description: release.description,
            published: release.published
        });
    }
}

async function runTests() {
    const assert = require("node:assert/strict");

    assert.equal(
        SemVer.parse("1.2.3").toString(),
        "1.2.3"
    );

    assert.throws(() => SemVer.parse("01.2.3"));

    assert.throws(() => SemVer.parse("1.2.3-01"));

    assert.equal(
        SemVer.parse("1.0.0-alpha").compare(
            SemVer.parse("1.0.0")
        ),
        -1
    );

    assert.equal(
        SemVer.parse("1.0.0+build.1").compare(
            SemVer.parse("1.0.0+build.2")
        ),
        0
    );

    assert.equal(
        SemVer.parse("2.4.6").increment("minor").toString(),
        "2.5.0"
    );

    assert.equal(
        determineReleaseType({
            breaking: true,
            feature: true
        }),
        "major"
    );

    const policy = new ReleasePolicy();

    assert.equal(
        policy.evaluate({
            version: SemVer.parse("1.0.0"),
            testsPassed: false,
            documentationUpdated: true,
            production: true,
            breaking: false
        }).eligible,
        false
    );

    const registry = new ReleaseRegistry("Test API");

    registry.register("1.0.0", {
        description: "Initial release",
        testsPassed: true,
        documentationUpdated: true,
        production: true,
        breaking: false
    });

    await registry.publish("1.0.0");

    assert.equal(registry.currentVersion.toString(), "1.0.0");

    await assert.rejects(
        registry.publish("2.0.0")
    );

    console.log("\nAll JavaScript tests passed.");
}

if (require.main === module) {
    main()
        .then(runTests)
        .catch(error => {
            console.error("Execution failed:", error.message);
            process.exitCode = 1;
        });
}

module.exports = {
    SemVer,
    VersionConstraint,
    ReleasePolicy,
    ReleaseRegistry,
    determineReleaseType
};
