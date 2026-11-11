"use strict";

/*
 * Build Systems: Dependency Resolution, Compilation,
 * Incremental Builds, and Asynchronous Packaging.
 *
 * Runtime: Node.js 18+
 * Dependencies: Node.js standard library only.
 *
 * Run: node build_system.js
 */

const fs = require("node:fs/promises");
const path = require("node:path");
const crypto = require("node:crypto");
const os = require("node:os");
const EventEmitter = require("node:events");

class BuildError extends Error {}
class DependencyError extends BuildError {}
class CycleError extends BuildError {}
class CompilationError extends BuildError {}
class PackagingError extends BuildError {}

const BuildState = Object.freeze({
    PENDING: "pending",
    BUILDING: "building",
    SUCCESS: "success",
    FAILED: "failed",
    CACHED: "cached"
});

const BuildProfile = Object.freeze({
    DEBUG: "debug",
    RELEASE: "release"
});

function validateName(name) {
    if (
        typeof name !== "string" ||
        !/^[A-Za-z0-9_-]+$/.test(name)
    ) {
        throw new TypeError(`Invalid target name: ${name}`);
    }
}

function validateVersion(version) {
    if (
        typeof version !== "string" ||
        !/^\d+\.\d+\.\d+$/.test(version)
    ) {
        throw new TypeError(`Invalid version: ${version}`);
    }
}

function sha256(content) {
    return crypto
        .createHash("sha256")
        .update(content)
        .digest("hex");
}

class BuildTarget {
    constructor({
        name,
        source,
        dependencies = [],
        version = "1.0.0",
        type = "library",
        enabled = true
    }) {
        validateName(name);
        validateVersion(version);

        if (
            typeof source !== "string" ||
            source.trim().length === 0
        ) {
            throw new TypeError("Source cannot be empty.");
        }

        if (!Array.isArray(dependencies)) {
            throw new TypeError("Dependencies must be an array.");
        }

        if (!["library", "executable"].includes(type)) {
            throw new TypeError("Invalid target type.");
        }

        this.name = name;
        this.source = source;
        this.dependencies = [...new Set(dependencies)];
        this.version = version;
        this.type = type;
        this.enabled = enabled;
        this.state = BuildState.PENDING;
        this.artifact = null;
    }
}

class BuildSystem extends EventEmitter {
    constructor({
        outputDirectory = "build_output",
        profile = BuildProfile.DEBUG,
        concurrency = os.availableParallelism
            ? os.availableParallelism()
            : os.cpus().length
    } = {}) {
        super();

        if (!Object.values(BuildProfile).includes(profile)) {
            throw new TypeError("Invalid build profile.");
        }

        if (!Number.isInteger(concurrency) || concurrency < 1) {
            throw new TypeError("Concurrency must be positive.");
        }

        this.outputDirectory = path.resolve(outputDirectory);
        this.profile = profile;
        this.concurrency = concurrency;

        this.targets = new Map();
        this.cache = new Map();
        this.states = new Map();
    }

    register(target) {
        if (!(target instanceof BuildTarget)) {
            throw new TypeError("Expected BuildTarget.");
        }

        if (this.targets.has(target.name)) {
            throw new DependencyError(
                `Duplicate target: ${target.name}`
            );
        }

        this.targets.set(target.name, target);
        this.states.set(target.name, BuildState.PENDING);
    }

    validateGraph() {
        for (const target of this.targets.values()) {
            for (const dependency of target.dependencies) {
                if (!this.targets.has(dependency)) {
                    throw new DependencyError(
                        `${target.name} requires ${dependency}`
                    );
                }

                if (dependency === target.name) {
                    throw new CycleError(
                        `${target.name} depends on itself`
                    );
                }
            }
        }
    }

    resolveOrder() {
        this.validateGraph();

        const temporary = new Set();
        const permanent = new Set();
        const order = [];

        const visit = (name) => {
            if (permanent.has(name)) return;

            if (temporary.has(name)) {
                throw new CycleError(
                    `Circular dependency at ${name}`
                );
            }

            temporary.add(name);

            const target = this.targets.get(name);

            for (const dependency of [...target.dependencies].sort()) {
                visit(dependency);
            }

            temporary.delete(name);
            permanent.add(name);
            order.push(name);
        };

        for (const name of [...this.targets.keys()].sort()) {
            visit(name);
        }

        return order;
    }

    fingerprint(target) {
        const dependencyHashes = {};

        for (const dependency of [...target.dependencies].sort()) {
            const artifact = this.targets.get(dependency).artifact;

            if (!artifact) {
                throw new CompilationError(
                    `Dependency not built: ${dependency}`
                );
            }

            dependencyHashes[dependency] = artifact.buildHash;
        }

        return sha256(JSON.stringify({
            name: target.name,
            source: target.source,
            version: target.version,
            dependencies: dependencyHashes,
            profile: this.profile,
            compiler: "node-build-simulator-1.0"
        }));
    }

    async compile(target) {
        if (!target.enabled) {
            throw new CompilationError(
                `Target disabled: ${target.name}`
            );
        }

        const buildHash = this.fingerprint(target);

        if (this.cache.has(buildHash)) {
            const cached = this.cache.get(buildHash);

            // Verify the cached artifact before reuse.
            const bytes = await fs.readFile(cached.path);

            if (sha256(bytes) !== cached.checksum) {
                throw new CompilationError(
                    `Cached artifact corrupted: ${target.name}`
                );
            }

            target.artifact = {
                ...cached,
                cached: true
            };

            target.state = BuildState.CACHED;
            this.states.set(target.name, BuildState.CACHED);

            this.emit("cacheHit", target.name);

            return target.artifact;
        }

        target.state = BuildState.BUILDING;
        this.states.set(target.name, BuildState.BUILDING);

        this.emit("compileStart", target.name);

        try {
            // Simulate compiler failure.
            if (target.source.includes("COMPILE_ERROR")) {
                throw new CompilationError(
                    `Compiler rejected ${target.name}`
                );
            }

            const extension = target.type === "executable"
                ? ".exe"
                : ".lib";

            const artifactPath = path.join(
                this.outputDirectory,
                target.name + extension
            );

            const content = [
                `TARGET=${target.name}`,
                `VERSION=${target.version}`,
                `PROFILE=${this.profile}`,
                `SOURCE=${target.source}`,
                `BUILD_HASH=${buildHash}`
            ].join("\n");

            // Atomic replacement avoids exposing partially written files.
            const temporaryPath =
                `${artifactPath}.${process.pid}.tmp`;

            await fs.writeFile(
                temporaryPath,
                content,
                { encoding: "utf8", flag: "wx" }
            );

            await fs.rename(temporaryPath, artifactPath);

            const bytes = await fs.readFile(artifactPath);

            const artifact = {
                target: target.name,
                path: artifactPath,
                checksum: sha256(bytes),
                buildHash,
                profile: this.profile,
                size: bytes.length,
                cached: false
            };

            this.cache.set(buildHash, artifact);
            target.artifact = artifact;
            target.state = BuildState.SUCCESS;

            this.states.set(target.name, BuildState.SUCCESS);

            this.emit("compileSuccess", artifact);

            return artifact;

        } catch (error) {
            target.state = BuildState.FAILED;
            this.states.set(target.name, BuildState.FAILED);

            this.emit("compileFailure", {
                target: target.name,
                error: error.message
            });

            if (error instanceof BuildError) {
                throw error;
            }

            throw new CompilationError(error.message);
        }
    }

    async build() {
        const order = this.resolveOrder();

        await fs.mkdir(
            this.outputDirectory,
            { recursive: true }
        );

        const pending = new Set(order);
        const completed = new Set();

        while (pending.size > 0) {
            const ready = [...pending]
                .filter(name => {
                    const dependencies =
                        this.targets.get(name).dependencies;

                    return dependencies.every(
                        dependency => completed.has(dependency)
                    );
                })
                .sort();

            if (ready.length === 0) {
                throw new CycleError(
                    "No buildable targets remain."
                );
            }

            // Run independent targets concurrently, respecting the limit.
            for (
                let index = 0;
                index < ready.length;
                index += this.concurrency
            ) {
                const batch = ready.slice(
                    index,
                    index + this.concurrency
                );

                await Promise.all(
                    batch.map(async name => {
                        await this.compile(
                            this.targets.get(name)
                        );

                        completed.add(name);
                        pending.delete(name);
                    })
                );
            }
        }

        const artifacts = order.map(
            name => this.targets.get(name).artifact
        );

        this.emit("buildComplete", artifacts);

        return artifacts;
    }

    async package(name = "application", version = "1.0.0") {
        validateName(name);
        validateVersion(version);

        const artifacts = [...this.targets.values()]
            .map(target => target.artifact)
            .filter(Boolean);

        if (artifacts.length === 0) {
            throw new PackagingError("No artifacts to package.");
        }

        const destination = path.join(
            this.outputDirectory,
            `${name}-${version}`
        );

        const staging = `${destination}.${process.pid}.staging`;

        await fs.rm(staging, { recursive: true, force: true });
        await fs.mkdir(staging, { recursive: true });

        try {
            const manifestArtifacts = [];

            for (const artifact of artifacts) {
                const source = await fs.readFile(artifact.path);

                if (sha256(source) !== artifact.checksum) {
                    throw new PackagingError(
                        `Checksum failure: ${artifact.target}`
                    );
                }

                const filename = path.basename(artifact.path);

                await fs.writeFile(
                    path.join(staging, filename),
                    source,
                    { flag: "wx" }
                );

                manifestArtifacts.push({
                    target: artifact.target,
                    file: filename,
                    checksum: artifact.checksum,
                    size: artifact.size
                });
            }

            const manifest = {
                name,
                version,
                profile: this.profile,
                createdAt: new Date().toISOString(),
                artifacts: manifestArtifacts
            };

            await fs.writeFile(
                path.join(staging, "manifest.json"),
                JSON.stringify(manifest, null, 2),
                { flag: "wx" }
            );

            await fs.rm(destination, {
                recursive: true,
                force: true
            });

            await fs.rename(staging, destination);

            this.emit("packageComplete", destination);

            return destination;

        } catch (error) {
            await fs.rm(staging, {
                recursive: true,
                force: true
            });

            throw new PackagingError(error.message);
        }
    }
}

async function run() {
    const system = new BuildSystem({
        outputDirectory: "build_output",
        profile: BuildProfile.RELEASE,
        concurrency: 2
    });

    system.on("compileStart", name => {
        console.log(`COMPILING: ${name}`);
    });

    system.on("compileSuccess", artifact => {
        console.log(
            `SUCCESS: ${artifact.target} ${artifact.checksum.slice(0, 12)}`
        );
    });

    system.on("cacheHit", name => {
        console.log(`CACHE HIT: ${name}`);
    });

    system.on("compileFailure", result => {
        console.error(`FAILED: ${result.target}: ${result.error}`);
    });

    system.register(new BuildTarget({
        name: "core",
        source: "core.cpp"
    }));

    system.register(new BuildTarget({
        name: "database",
        source: "database.cpp",
        dependencies: ["core"]
    }));

    system.register(new BuildTarget({
        name: "network",
        source: "network.cpp",
        dependencies: ["core"]
    }));

    system.register(new BuildTarget({
        name: "application",
        source: "main.cpp",
        dependencies: ["database", "network"],
        type: "executable"
    }));

    console.log("\nDEPENDENCY ORDER");
    console.log(system.resolveOrder().join(" -> "));

    console.log("\nBUILD");
    await system.build();

    console.log("\nINCREMENTAL BUILD");
    await system.build();

    console.log("\nPACKAGE");
    console.log(
        await system.package("enterprise_application", "1.0.0")
    );
}

run().catch(error => {
    console.error(`BUILD SYSTEM ERROR: ${error.message}`);
    process.exitCode = 1;
});
