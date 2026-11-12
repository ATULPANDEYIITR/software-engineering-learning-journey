"use strict";

/*
 * Package Management: Dependency Management and Versioning
 *
 * Node.js implementation featuring:
 * - Semantic version comparison
 * - Dependency constraints
 * - Event-driven installation
 * - Asynchronous registry operations
 * - Dependency graph validation
 * - Installation policies
 * - Lockfile integrity
 * - Vulnerability auditing
 */

const crypto = require("node:crypto");
const fs = require("node:fs/promises");
const EventEmitter = require("node:events");

class PackageError extends Error {}
class VersionError extends PackageError {}
class ResolutionError extends PackageError {}
class IntegrityError extends PackageError {}
class PolicyError extends PackageError {}

class SemVer {
    constructor(major, minor, patch) {
        for (const value of [major, minor, patch]) {
            if (!Number.isSafeInteger(value) || value < 0) {
                throw new VersionError("Invalid version component");
            }
        }

        this.major = major;
        this.minor = minor;
        this.patch = patch;
        Object.freeze(this);
    }

    static parse(value) {
        const match = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/.exec(value);

        if (!match) {
            throw new VersionError(`Invalid semantic version: ${value}`);
        }

        return new SemVer(...match.slice(1).map(Number));
    }

    compare(other) {
        return (
            this.major - other.major ||
            this.minor - other.minor ||
            this.patch - other.patch
        );
    }

    toString() {
        return `${this.major}.${this.minor}.${this.patch}`;
    }
}

function satisfies(version, constraint) {
    if (!constraint || constraint === "*") return true;

    return constraint.split(",").every(expression => {
        const match = /^(>=|<=|>|<|=|\^|~)?(.+)$/.exec(expression.trim());

        if (!match) {
            throw new VersionError(`Invalid constraint: ${expression}`);
        }

        const operator = match[1] || "=";
        const target = SemVer.parse(match[2]);
        const comparison = version.compare(target);

        switch (operator) {
            case "=": return comparison === 0;
            case ">": return comparison > 0;
            case "<": return comparison < 0;
            case ">=": return comparison >= 0;
            case "<=": return comparison <= 0;

            case "^": {
                const upper = target.major > 0
                    ? new SemVer(target.major + 1, 0, 0)
                    : target.minor > 0
                        ? new SemVer(0, target.minor + 1, 0)
                        : new SemVer(0, 0, target.patch + 1);

                return comparison >= 0 && version.compare(upper) < 0;
            }

            case "~": {
                const upper = new SemVer(
                    target.major,
                    target.minor + 1,
                    0
                );

                return comparison >= 0 && version.compare(upper) < 0;
            }

            default:
                throw new VersionError(`Unsupported operator: ${operator}`);
        }
    });
}

function validateName(name) {
    if (
        typeof name !== "string" ||
        !/^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,99}$/.test(name)
    ) {
        throw new PackageError("Invalid package name");
    }
}

function checksum(name, version, dependencies) {
    const canonical = JSON.stringify({
        name,
        version: version.toString(),
        dependencies: Object.fromEntries(
            Object.entries(dependencies).sort(([a], [b]) => a.localeCompare(b))
        )
    });

    return crypto.createHash("sha256").update(canonical).digest("hex");
}

class PackageRegistry extends EventEmitter {
    #packages = new Map();

    async publish(definition) {
        const { name, version, dependencies = {}, vulnerable = false } = definition;

        validateName(name);

        const parsed = SemVer.parse(version);

        if (typeof dependencies !== "object" || dependencies === null ||
            Array.isArray(dependencies)) {
            throw new PackageError("Dependencies must be an object");
        }

        for (const [dependency, constraint] of Object.entries(dependencies)) {
            validateName(dependency);

            if (typeof constraint !== "string") {
                throw new PackageError("Dependency constraints must be strings");
            }

            // Validate syntax before publishing.
            satisfies(parsed, "*");
            if (constraint !== "*") {
                satisfies(SemVer.parse(
                    constraint.match(/(?:>=|<=|>|<|=|\^|~)?(.+)/)?.[1]
                ), constraint);
            }
        }

        const entries = this.#packages.get(name) || [];

        if (entries.some(pkg => pkg.version.compare(parsed) === 0)) {
            throw new PackageError("Duplicate package version");
        }

        const pkg = Object.freeze({
            name,
            version: parsed,
            dependencies: Object.freeze({ ...dependencies }),
            checksum: checksum(name, parsed, dependencies),
            vulnerable: Boolean(vulnerable)
        });

        entries.push(pkg);
        entries.sort((a, b) => b.version.compare(a.version));

        this.#packages.set(name, entries);

        this.emit("published", {
            name,
            version: parsed.toString()
        });

        return pkg;
    }

    async versions(name) {
        validateName(name);

        const entries = this.#packages.get(name);

        if (!entries) {
            throw new ResolutionError(`Unknown package: ${name}`);
        }

        return [...entries];
    }

    async select(name, constraint) {
        const versions = await this.versions(name);

        const result = versions.find(pkg =>
            satisfies(pkg.version, constraint)
        );

        if (!result) {
            throw new ResolutionError(
                `No matching version: ${name}@${constraint}`
            );
        }

        return result;
    }
}

class InstallPolicy {
    constructor({
        allowVulnerable = false,
        allowDowngrades = false,
        maxPackages = 100
    } = {}) {
        this.allowVulnerable = allowVulnerable;
        this.allowDowngrades = allowDowngrades;
        this.maxPackages = maxPackages;
        Object.freeze(this);
    }

    evaluate(packageDefinition) {
        if (packageDefinition.vulnerable && !this.allowVulnerable) {
            throw new PolicyError(
                `Vulnerable package rejected: ${packageDefinition.name}`
            );
        }
    }
}

class PackageManager extends EventEmitter {
    #registry;
    #installed = new Map();
    #policy;
    #operationRunning = false;

    constructor(registry, policy = new InstallPolicy()) {
        super();

        this.#registry = registry;
        this.#policy = policy;
    }

    get installed() {
        return new Map(this.#installed);
    }

    async resolve(requirements) {
        const constraints = new Map();
        const selected = new Map();
        const resolving = new Set();
        const resolved = new Set();

        for (const [name, constraint] of Object.entries(requirements)) {
            validateName(name);
            constraints.set(name, [constraint]);
        }

        const visit = async () => {
            const pending = [...constraints.keys()]
                .filter(name => !resolved.has(name))
                .sort();

            if (pending.length === 0) return;

            const name = pending[0];

            if (resolving.has(name)) {
                throw new ResolutionError(`Dependency cycle: ${name}`);
            }

            const versions = await this.#registry.versions(name);
            const required = constraints.get(name);

            const candidates = versions.filter(pkg =>
                required.every(rule => satisfies(pkg.version, rule))
            );

            for (const candidate of candidates) {
                const previous = {
                    selected: new Map(selected),
                    constraints: new Map(
                        [...constraints].map(([key, value]) => [key, [...value]])
                    ),
                    resolving: new Set(resolving),
                    resolved: new Set(resolved)
                };

                try {
                    selected.set(name, candidate);
                    resolving.add(name);

                    for (const [dependency, rule] of Object.entries(
                        candidate.dependencies
                    )) {
                        const rules = constraints.get(dependency) || [];
                        rules.push(rule);
                        constraints.set(dependency, rules);

                        if (resolving.has(dependency)) {
                            throw new ResolutionError("Circular dependency");
                        }
                    }

                    resolving.delete(name);
                    resolved.add(name);

                    await visit();
                    return;

                } catch (error) {
                    selected.clear();
                    for (const entry of previous.selected) selected.set(...entry);

                    constraints.clear();
                    for (const entry of previous.constraints) {
                        constraints.set(...entry);
                    }

                    resolving.clear();
                    for (const item of previous.resolving) resolving.add(item);

                    resolved.clear();
                    for (const item of previous.resolved) resolved.add(item);
                }
            }

            throw new ResolutionError(
                `Unable to resolve package: ${name}`
            );
        };

        await visit();

        if (selected.size > this.#policy.maxPackages) {
            throw new PolicyError("Package limit exceeded");
        }

        return selected;
    }

    async install(requirements) {
        if (this.#operationRunning) {
            throw new PackageError("Another installation is running");
        }

        this.#operationRunning = true;
        this.emit("installationStarted", requirements);

        try {
            const plan = await this.resolve(requirements);

            // Apply all policy checks before committing any changes.
            for (const pkg of plan.values()) {
                this.#policy.evaluate(pkg);

                const previous = this.#installed.get(pkg.name);

                if (
                    previous &&
                    pkg.version.compare(previous.version) < 0 &&
                    !this.#policy.allowDowngrades
                ) {
                    throw new PolicyError(
                        `Downgrade rejected: ${pkg.name}`
                    );
                }

                if (checksum(pkg.name, pkg.version, pkg.dependencies) !==
                    pkg.checksum) {
                    throw new IntegrityError(
                        `Checksum mismatch: ${pkg.name}`
                    );
                }
            }

            const nextState = new Map(this.#installed);

            for (const [name, pkg] of plan) {
                nextState.set(name, pkg);
            }

            this.#installed = nextState;

            const result = [...plan.values()].map(pkg => ({
                name: pkg.name,
                version: pkg.version.toString()
            }));

            this.emit("installationCompleted", result);
            return result;

        } catch (error) {
            this.emit("installationFailed", error);
            throw error;

        } finally {
            this.#operationRunning = false;
        }
    }

    async createLockfile(path) {
        const packages = {};

        for (const [name, pkg] of [...this.#installed].sort()) {
            packages[name] = {
                version: pkg.version.toString(),
                dependencies: pkg.dependencies,
                checksum: pkg.checksum
            };
        }

        const document = JSON.stringify({
            lockfileVersion: 1,
            packages
        }, null, 2);

        const temporary = `${path}.tmp`;

        try {
            await fs.writeFile(temporary, document, {
                encoding: "utf8",
                flag: "wx",
                mode: 0o600
            });

            await fs.rename(temporary, path);

        } catch (error) {
            await fs.unlink(temporary).catch(() => {});
            throw error;
        }
    }

    audit() {
        return [...this.#installed.values()]
            .filter(pkg => pkg.vulnerable)
            .map(pkg => ({
                package: pkg.name,
                version: pkg.version.toString(),
                severity: "HIGH"
            }));
    }
}

async function main() {
    const registry = new PackageRegistry();

    registry.on("published", event => {
        console.log(
            `Published ${event.name}@${event.version}`
        );
    });

    registry.on("error", error => {
        console.error("Registry error:", error.message);
    });

    await registry.publish({
        name: "core",
        version: "1.0.0"
    });

    await registry.publish({
        name: "core",
        version: "1.2.0"
    });

    await registry.publish({
        name: "database",
        version: "1.0.0",
        dependencies: { core: "^1.0.0" }
    });

    await registry.publish({
        name: "web-framework",
        version: "1.0.0",
        dependencies: {
            core: "^1.0.0",
            database: "^1.0.0"
        }
    });

    await registry.publish({
        name: "web-framework",
        version: "1.1.0",
        dependencies: {
            core: "^1.0.0",
            database: "^1.0.0"
        }
    });

    const manager = new PackageManager(
        registry,
        new InstallPolicy({
            allowVulnerable: false,
            allowDowngrades: false,
            maxPackages: 50
        })
    );

    manager.on("installationStarted", () => {
        console.log("\nInstallation started.");
    });

    manager.on("installationCompleted", result => {
        console.log("Installation completed:", result);
    });

    manager.on("installationFailed", error => {
        console.error("Installation failed:", error.message);
    });

    await manager.install({
        "web-framework": "^1.0.0"
    });

    await manager.createLockfile("package-lock.json");

    console.log("\nInstalled packages:");

    for (const [name, pkg] of manager.installed) {
        console.log(`${name}@${pkg.version}`);
    }

    console.log("\nSecurity audit:", manager.audit());

    console.log(
        "\nVersion test:",
        satisfies(SemVer.parse("1.2.0"), "^1.0.0")
    );

    try {
        await manager.install({
            core: "^2.0.0",
            database: "^1.0.0"
        });
    } catch (error) {
        console.log("\nExpected conflict:", error.message);
    }

    console.log("\nPackage management checks completed.");
}

main().catch(error => {
    console.error("Fatal error:", error.message);
    process.exitCode = 1;
});
