import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.*;

/*
 * Build Systems: Enterprise Build and Release Management
 *
 * Java 17 implementation.
 *
 * Covers:
 * - Build target domain modeling
 * - Dependency resolution
 * - Topological compilation planning
 * - Parallel compilation
 * - Incremental build caching
 * - Artifact validation
 * - Release packaging
 * - Build lifecycle management
 *
 * Compile:
 * javac BuildSystem.java
 *
 * Run:
 * java BuildSystem
 */

public class BuildSystem {

    enum Profile {
        DEBUG, RELEASE
    }

    enum TargetType {
        LIBRARY, EXECUTABLE
    }

    enum State {
        PENDING, BUILDING, SUCCESS, CACHED, FAILED
    }

    interface BuildEventListener {
        void onEvent(String event, String target);
    }

    static class BuildException extends RuntimeException {
        BuildException(String message) {
            super(message);
        }

        BuildException(String message, Throwable cause) {
            super(message, cause);
        }
    }

    static class DependencyException extends BuildException {
        DependencyException(String message) {
            super(message);
        }
    }

    static class CompilationException extends BuildException {
        CompilationException(String message) {
            super(message);
        }
    }

    static class PackagingException extends BuildException {
        PackagingException(String message) {
            super(message);
        }
    }

    record Dependency(
        String name,
        String minimumVersion,
        boolean optional
    ) {
        Dependency {
            Objects.requireNonNull(name);
            Objects.requireNonNull(minimumVersion);

            if (!name.matches("[A-Za-z0-9_-]+")) {
                throw new IllegalArgumentException(
                    "Invalid dependency name."
                );
            }

            if (!minimumVersion.matches("\\d+\\.\\d+\\.\\d+")) {
                throw new IllegalArgumentException(
                    "Invalid dependency version."
                );
            }
        }
    }

    record BuildArtifact(
        String target,
        Path path,
        String checksum,
        String fingerprint,
        long size,
        Profile profile,
        boolean cached
    ) {}

    static final class BuildTarget {

        private final String name;
        private final String source;
        private final String version;
        private final TargetType type;
        private final List<String> dependencies;
        private final boolean enabled;

        private volatile State state = State.PENDING;
        private volatile BuildArtifact artifact;

        BuildTarget(
            String name,
            String source,
            String version,
            TargetType type,
            List<String> dependencies,
            boolean enabled
        ) {
            if (name == null ||
                !name.matches("[A-Za-z0-9_-]+")) {
                throw new IllegalArgumentException(
                    "Invalid target name."
                );
            }

            if (source == null || source.isBlank()) {
                throw new IllegalArgumentException(
                    "Source cannot be empty."
                );
            }

            if (version == null ||
                !version.matches("\\d+\\.\\d+\\.\\d+")) {
                throw new IllegalArgumentException(
                    "Invalid semantic version."
                );
            }

            this.name = name;
            this.source = source;
            this.version = version;
            this.type = Objects.requireNonNull(type);

            this.dependencies = List.copyOf(
                new LinkedHashSet<>(dependencies)
            );

            this.enabled = enabled;
        }
    }

    static final class BuildPolicy {

        private final Profile profile;
        private final int requiredSuccessfulTargets;
        private final boolean requireAllEnabledTargets;

        BuildPolicy(
            Profile profile,
            int requiredSuccessfulTargets,
            boolean requireAllEnabledTargets
        ) {
            if (requiredSuccessfulTargets < 1) {
                throw new IllegalArgumentException(
                    "Minimum successful targets must be positive."
                );
            }

            this.profile = profile;
            this.requiredSuccessfulTargets =
                requiredSuccessfulTargets;

            this.requireAllEnabledTargets =
                requireAllEnabledTargets;
        }

        void validate(List<BuildArtifact> artifacts) {
            if (artifacts.size() < requiredSuccessfulTargets) {
                throw new BuildException(
                    "Build policy minimum not satisfied."
                );
            }

            if (requireAllEnabledTargets &&
                artifacts.isEmpty()) {
                throw new BuildException(
                    "No successful build artifacts."
                );
            }
        }
    }

    static final class BuildService {

        private final Map<String, BuildTarget> targets =
            new TreeMap<>();

        private final Map<String, BuildArtifact> cache =
            new ConcurrentHashMap<>();

        private final Path outputDirectory;
        private final Profile profile;
        private final int parallelism;

        private final List<BuildEventListener> listeners =
            new CopyOnWriteArrayList<>();

        BuildService(
            Path outputDirectory,
            Profile profile,
            int parallelism
        ) {
            this.outputDirectory = outputDirectory;
            this.profile = profile;

            if (parallelism < 1) {
                throw new IllegalArgumentException(
                    "Parallelism must be positive."
                );
            }

            this.parallelism = parallelism;
        }

        void addListener(BuildEventListener listener) {
            listeners.add(listener);
        }

        private void emit(String event, String target) {
            for (BuildEventListener listener : listeners) {
                listener.onEvent(event, target);
            }
        }

        void register(BuildTarget target) {
            if (targets.containsKey(target.name)) {
                throw new DependencyException(
                    "Duplicate target: " + target.name
                );
            }

            targets.put(target.name, target);
        }

        void validateGraph() {
            for (BuildTarget target : targets.values()) {
                for (String dependency : target.dependencies) {
                    if (!targets.containsKey(dependency)) {
                        throw new DependencyException(
                            target.name +
                            " requires missing dependency " +
                            dependency
                        );
                    }

                    if (target.name.equals(dependency)) {
                        throw new DependencyException(
                            "Self dependency: " + target.name
                        );
                    }
                }
            }
        }

        List<String> resolveOrder() {
            validateGraph();

            Set<String> temporary = new HashSet<>();
            Set<String> permanent = new HashSet<>();

            List<String> result = new ArrayList<>();

            for (String name : targets.keySet()) {
                visit(name, temporary, permanent, result);
            }

            return List.copyOf(result);
        }

        private void visit(
            String name,
            Set<String> temporary,
            Set<String> permanent,
            List<String> result
        ) {
            if (permanent.contains(name)) {
                return;
            }

            if (!temporary.add(name)) {
                throw new DependencyException(
                    "Circular dependency detected: " + name
                );
            }

            BuildTarget target = targets.get(name);

            List<String> dependencies =
                new ArrayList<>(target.dependencies);

            Collections.sort(dependencies);

            for (String dependency : dependencies) {
                visit(
                    dependency,
                    temporary,
                    permanent,
                    result
                );
            }

            temporary.remove(name);
            permanent.add(name);

            result.add(name);
        }

        Map<Integer, List<String>> resolveBuildStages() {
            List<String> order = resolveOrder();

            Map<String, Integer> levels = new HashMap<>();

            for (String name : order) {
                BuildTarget target = targets.get(name);

                int level = 0;

                for (String dependency : target.dependencies) {
                    level = Math.max(
                        level,
                        levels.get(dependency) + 1
                    );
                }

                levels.put(name, level);
            }

            Map<Integer, List<String>> stages =
                new TreeMap<>();

            for (String name : order) {
                int level = levels.get(name);

                stages.computeIfAbsent(
                    level,
                    ignored -> new ArrayList<>()
                ).add(name);
            }

            stages.replaceAll(
                (level, names) -> List.copyOf(names)
            );

            return Collections.unmodifiableMap(stages);
        }

        private String hash(String content) {
            try {
                MessageDigest digest =
                    MessageDigest.getInstance("SHA-256");

                byte[] result = digest.digest(
                    content.getBytes(StandardCharsets.UTF_8)
                );

                return HexFormat.of().formatHex(result);

            } catch (NoSuchAlgorithmException error) {
                throw new BuildException(
                    "SHA-256 unavailable.",
                    error
                );
            }
        }

        private String fingerprint(BuildTarget target) {
            StringBuilder content = new StringBuilder();

            content.append(target.name)
                .append(target.source)
                .append(target.version)
                .append(profile);

            for (String dependency :
                 new TreeSet<>(target.dependencies)) {

                BuildArtifact artifact =
                    targets.get(dependency).artifact;

                if (artifact == null) {
                    throw new CompilationException(
                        "Missing dependency artifact: " + dependency
                    );
                }

                content.append(dependency)
                    .append(artifact.fingerprint());
            }

            return hash(content.toString());
        }

        private BuildArtifact compile(BuildTarget target) {
            if (!target.enabled) {
                throw new CompilationException(
                    "Target disabled: " + target.name
                );
            }

            target.state = State.BUILDING;
            emit("COMPILATION_STARTED", target.name);

            try {
                String fingerprint = fingerprint(target);

                BuildArtifact cached = cache.get(fingerprint);

                if (cached != null) {
                    if (!Files.isRegularFile(cached.path())) {
                        throw new CompilationException(
                            "Cached artifact missing: " +
                            target.name
                        );
                    }

                    String actual = hash(
                        Files.readString(cached.path())
                    );

                    if (!actual.equals(cached.checksum())) {
                        throw new CompilationException(
                            "Cached artifact corrupted: " +
                            target.name
                        );
                    }

                    BuildArtifact reused = new BuildArtifact(
                        cached.target(),
                        cached.path(),
                        cached.checksum(),
                        cached.fingerprint(),
                        cached.size(),
                        cached.profile(),
                        true
                    );

                    target.artifact = reused;
                    target.state = State.CACHED;

                    emit("CACHE_HIT", target.name);

                    return reused;
                }

                if (target.source.contains("COMPILE_ERROR")) {
                    throw new CompilationException(
                        "Compilation rejected: " + target.name
                    );
                }

                Files.createDirectories(outputDirectory);

                String extension =
                    target.type == TargetType.EXECUTABLE
                    ? ".exe"
                    : ".lib";

                Path destination = outputDirectory.resolve(
                    target.name + extension
                );

                String compiled = """
                    TARGET=%s
                    VERSION=%s
                    PROFILE=%s
                    SOURCE=%s
                    FINGERPRINT=%s
                    """.formatted(
                        target.name,
                        target.version,
                        profile,
                        target.source,
                        fingerprint
                    );

                Path temporary = Files.createTempFile(
                    outputDirectory,
                    target.name,
                    ".tmp"
                );

                try {
                    Files.writeString(
                        temporary,
                        compiled,
                        StandardCharsets.UTF_8
                    );

                    try {
                        Files.move(
                            temporary,
                            destination,
                            StandardCopyOption.REPLACE_EXISTING,
                            StandardCopyOption.ATOMIC_MOVE
                        );
                    } catch (AtomicMoveNotSupportedException error) {
                        Files.move(
                            temporary,
                            destination,
                            StandardCopyOption.REPLACE_EXISTING
                        );
                    }

                } finally {
                    Files.deleteIfExists(temporary);
                }

                BuildArtifact artifact = new BuildArtifact(
                    target.name,
                    destination,
                    hash(compiled),
                    fingerprint,
                    Files.size(destination),
                    profile,
                    false
                );

                cache.put(fingerprint, artifact);

                target.artifact = artifact;
                target.state = State.SUCCESS;

                emit("COMPILATION_SUCCESS", target.name);

                return artifact;

            } catch (IOException error) {
                target.state = State.FAILED;

                emit("COMPILATION_FAILED", target.name);

                throw new CompilationException(
                    "I/O failure for " + target.name +
                    ": " + error.getMessage()
                );

            } catch (RuntimeException error) {
                target.state = State.FAILED;

                emit("COMPILATION_FAILED", target.name);

                throw error;
            }
        }

        List<BuildArtifact> build() {
            List<String> order = resolveOrder();

            Map<String, CompletableFuture<BuildArtifact>> futures =
                new HashMap<>();

            ExecutorService executor =
                Executors.newFixedThreadPool(parallelism);

            try {
                for (String name : order) {
                    BuildTarget target = targets.get(name);

                    CompletableFuture<?>[] dependencies =
                        target.dependencies.stream()
                            .map(futures::get)
                            .toArray(CompletableFuture[]::new);

                    CompletableFuture<BuildArtifact> future =
                        CompletableFuture.allOf(dependencies)
                            .thenApplyAsync(
                                ignored -> compile(target),
                                executor
                            );

                    futures.put(name, future);
                }

                List<BuildArtifact> results =
                    new ArrayList<>();

                for (String name : order) {
                    results.add(
                        futures.get(name).join()
                    );
                }

                return List.copyOf(results);

            } catch (CompletionException error) {
                throw new CompilationException(
                    "Build pipeline failed: " +
                    error.getCause().getMessage()
                );

            } finally {
                executor.shutdownNow();
            }
        }

        Path packageArtifacts(
            String packageName,
            String version,
            BuildPolicy policy
        ) {
            if (!packageName.matches("[A-Za-z0-9_-]+") ||
                !version.matches("\\d+\\.\\d+\\.\\d+")) {
                throw new PackagingException(
                    "Invalid package metadata."
                );
            }

            List<BuildArtifact> artifacts =
                targets.values().stream()
                    .map(target -> target.artifact)
                    .filter(Objects::nonNull)
                    .toList();

            policy.validate(artifacts);

            Path destination = outputDirectory.resolve(
                packageName + "-" + version
            );

            Path staging = outputDirectory.resolve(
                packageName + "-" + version +
                "-" + UUID.randomUUID() + ".staging"
            );

            try {
                Files.createDirectories(staging);

                StringBuilder manifest = new StringBuilder();

                manifest.append("NAME=").append(packageName)
                    .append("\nVERSION=").append(version)
                    .append("\nPROFILE=").append(profile)
                    .append("\nCREATED=").append(Instant.now())
                    .append('\n');

                for (BuildArtifact artifact : artifacts) {
                    String content = Files.readString(
                        artifact.path()
                    );

                    if (!hash(content).equals(artifact.checksum())) {
                        throw new PackagingException(
                            "Checksum mismatch: " + artifact.target()
                        );
                    }

                    Path output = staging.resolve(
                        artifact.path().getFileName()
                    );

                    Files.copy(
                        artifact.path(),
                        output
                    );

                    manifest.append("ARTIFACT=")
                        .append(artifact.target())
                        .append(" CHECKSUM=")
                        .append(artifact.checksum())
                        .append(" SIZE=")
                        .append(artifact.size())
                        .append('\n');
                }

                Files.writeString(
                    staging.resolve("manifest.txt"),
                    manifest.toString()
                );

                if (Files.exists(destination)) {
                    throw new PackagingException(
                        "Package destination already exists: " +
                        destination
                    );
                }

                Files.move(
                    staging,
                    destination,
                    StandardCopyOption.ATOMIC_MOVE
                );

                return destination;

            } catch (IOException error) {
                try {
                    deleteRecursively(staging);
                } catch (IOException ignored) {
                    // Preserve the original packaging error.
                }

                throw new PackagingException(
                    "Packaging failed: " + error.getMessage()
                );
            }
        }

        private void deleteRecursively(Path directory)
            throws IOException {

            if (!Files.exists(directory)) {
                return;
            }

            try (var paths = Files.walk(directory)) {
                for (Path item :
                     paths.sorted(Comparator.reverseOrder()).toList()) {
                    Files.deleteIfExists(item);
                }
            }
        }
    }

    private static void runTests() {
        BuildService service = new BuildService(
            Path.of("java_test_output"),
            Profile.DEBUG,
            2
        );

        service.register(new BuildTarget(
            "base",
            "base.cpp",
            "1.0.0",
            TargetType.LIBRARY,
            List.of(),
            true
        ));

        service.register(new BuildTarget(
            "service",
            "service.cpp",
            "1.0.0",
            TargetType.LIBRARY,
            List.of("base"),
            true
        ));

        List<String> order = service.resolveOrder();

        if (!order.equals(List.of("base", "service"))) {
            throw new BuildException(
                "Dependency ordering test failed."
            );
        }

        if (service.resolveBuildStages().size() != 2) {
            throw new BuildException(
                "Build stage test failed."
            );
        }

        BuildService cyclic = new BuildService(
            Path.of("cycle_output"),
            Profile.DEBUG,
            1
        );

        cyclic.register(new BuildTarget(
            "first", "first.cpp", "1.0.0",
            TargetType.LIBRARY, List.of("second"), true
        ));

        cyclic.register(new BuildTarget(
            "second", "second.cpp", "1.0.0",
            TargetType.LIBRARY, List.of("first"), true
        ));

        try {
            cyclic.resolveOrder();

            throw new BuildException(
                "Circular dependency test failed."
            );

        } catch (DependencyException expected) {
            System.out.println("CYCLE TEST PASSED");
        }

        System.out.println("ALL TESTS PASSED");
    }

    public static void main(String[] args) {
        try {
            runTests();

            BuildService service = new BuildService(
                Path.of("java_build_output"),
                Profile.RELEASE,
                3
            );

            service.addListener(
                (event, target) ->
                    System.out.println(event + ": " + target)
            );

            service.register(new BuildTarget(
                "core", "core.cpp", "1.0.0",
                TargetType.LIBRARY, List.of(), true
            ));

            service.register(new BuildTarget(
                "database", "database.cpp", "1.0.0",
                TargetType.LIBRARY, List.of("core"), true
            ));

            service.register(new BuildTarget(
                "network", "network.cpp", "1.0.0",
                TargetType.LIBRARY, List.of("core"), true
            ));

            service.register(new BuildTarget(
                "application", "main.cpp", "1.0.0",
                TargetType.EXECUTABLE,
                List.of("database", "network"), true
            ));

            System.out.println("\nBUILD STAGES");

            service.resolveBuildStages().forEach(
                (level, names) ->
                    System.out.println(level + ": " + names)
            );

            System.out.println("\nBUILD EXECUTION");

            List<BuildArtifact> artifacts = service.build();

            artifacts.forEach(System.out::println);

            System.out.println("\nINCREMENTAL BUILD");

            service.build();

            BuildPolicy policy = new BuildPolicy(
                Profile.RELEASE,
                4,
                true
            );

            System.out.println("\nPACKAGING");

            Path packagePath = service.packageArtifacts(
                "enterprise_application",
                "1.0.0",
                policy
            );

            System.out.println(
                "PACKAGE CREATED: " + packagePath
            );

        } catch (BuildException error) {
            System.err.println(
                "BUILD FAILURE: " + error.getMessage()
            );

            System.exit(1);
        }
    }
}
