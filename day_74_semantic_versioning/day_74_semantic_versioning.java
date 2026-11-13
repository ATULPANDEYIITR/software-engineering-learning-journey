import java.util.*;
import java.util.stream.Collectors;

/**
 * Semantic Versioning 2.0.0
 *
 * Enterprise software release governance.
 * Includes immutable version objects, release policies,
 * dependency validation, state transitions, and compatibility checks.
 *
 * Requires Java 17.
 */

public class SemanticVersioning {

    public static final class VersionException
            extends IllegalArgumentException {

        public VersionException(String message) {
            super(message);
        }
    }

    public static final class ReleaseException
            extends RuntimeException {

        public ReleaseException(String message) {
            super(message);
        }
    }

    public enum ChangeType {
        PATCH,
        MINOR,
        MAJOR
    }

    public enum ReleaseState {
        DRAFT,
        VALIDATED,
        PUBLISHED,
        REJECTED
    }

    public record Version(
            long major,
            long minor,
            long patch,
            List<String> prerelease,
            List<String> build
    ) implements Comparable<Version> {

        private static final String PATTERN =
                "^(0|[1-9]\\d*)\\."
                + "(0|[1-9]\\d*)\\."
                + "(0|[1-9]\\d*)"
                + "(?:-([0-9A-Za-z-]+(?:\\.[0-9A-Za-z-]+)*))?"
                + "(?:\\+([0-9A-Za-z-]+(?:\\.[0-9A-Za-z-]+)*))?$";

        public Version {
            if (major < 0 || minor < 0 || patch < 0) {
                throw new VersionException(
                        "Version components cannot be negative"
                );
            }

            prerelease = List.copyOf(prerelease);
            build = List.copyOf(build);

            prerelease.forEach(
                    id -> validateIdentifier(id, true)
            );

            build.forEach(
                    id -> validateIdentifier(id, false)
            );
        }

        private static void validateIdentifier(
                String id,
                boolean prerelease
        ) {
            if (id == null || !id.matches("[0-9A-Za-z-]+")) {
                throw new VersionException(
                        "Invalid version identifier"
                );
            }

            if (
                    prerelease &&
                    id.matches("\\d+") &&
                    id.length() > 1 &&
                    id.startsWith("0")
            ) {
                throw new VersionException(
                        "Numeric prerelease identifiers cannot have leading zeros"
                );
            }
        }

        public static Version parse(String value) {
            if (value == null) {
                throw new VersionException(
                        "Version cannot be null"
                );
            }

            java.util.regex.Matcher matcher =
                    java.util.regex.Pattern.compile(PATTERN)
                            .matcher(value);

            if (!matcher.matches()) {
                throw new VersionException(
                        "Invalid semantic version: " + value
                );
            }

            try {
                return new Version(
                        Long.parseLong(matcher.group(1)),
                        Long.parseLong(matcher.group(2)),
                        Long.parseLong(matcher.group(3)),
                        matcher.group(4) == null
                                ? List.of()
                                : List.of(matcher.group(4).split("\\.")),
                        matcher.group(5) == null
                                ? List.of()
                                : List.of(matcher.group(5).split("\\."))
                );

            } catch (NumberFormatException exception) {
                throw new VersionException(
                        "Version component exceeds supported range"
                );
            }
        }

        @Override
        public String toString() {
            StringBuilder result = new StringBuilder()
                    .append(major)
                    .append(".")
                    .append(minor)
                    .append(".")
                    .append(patch);

            if (!prerelease.isEmpty()) {
                result.append("-")
                        .append(String.join(".", prerelease));
            }

            if (!build.isEmpty()) {
                result.append("+")
                        .append(String.join(".", build));
            }

            return result.toString();
        }

        private static int compareIdentifiers(
                String a,
                String b
        ) {
            boolean aNumeric = a.matches("\\d+");
            boolean bNumeric = b.matches("\\d+");

            if (aNumeric && bNumeric) {
                // BigInteger avoids overflow in arbitrarily long identifiers.
                return new java.math.BigInteger(a)
                        .compareTo(new java.math.BigInteger(b));
            }

            if (aNumeric) return -1;
            if (bNumeric) return 1;

            return a.compareTo(b);
        }

        @Override
        public int compareTo(Version other) {
            int result = Long.compare(major, other.major);

            if (result != 0) return result;

            result = Long.compare(minor, other.minor);

            if (result != 0) return result;

            result = Long.compare(patch, other.patch);

            if (result != 0) return result;

            if (prerelease.isEmpty() && other.prerelease.isEmpty()) {
                return 0;
            }

            if (prerelease.isEmpty()) return 1;
            if (other.prerelease.isEmpty()) return -1;

            int count = Math.min(
                    prerelease.size(),
                    other.prerelease.size()
            );

            for (int i = 0; i < count; i++) {
                result = compareIdentifiers(
                        prerelease.get(i),
                        other.prerelease.get(i)
                );

                if (result != 0) return result;
            }

            return Integer.compare(
                    prerelease.size(),
                    other.prerelease.size()
            );
        }

        /*
         * Build metadata is intentionally excluded from equality
         * because it does not affect SemVer precedence.
         */
        @Override
        public boolean equals(Object object) {
            if (this == object) return true;

            if (!(object instanceof Version other)) {
                return false;
            }

            return compareTo(other) == 0;
        }

        @Override
        public int hashCode() {
            return Objects.hash(
                    major,
                    minor,
                    patch,
                    prerelease
            );
        }

        public Version increment(ChangeType type) {
            try {
                return switch (type) {
                    case MAJOR -> new Version(
                            Math.addExact(major, 1),
                            0,
                            0,
                            List.of(),
                            List.of()
                    );

                    case MINOR -> new Version(
                            major,
                            Math.addExact(minor, 1),
                            0,
                            List.of(),
                            List.of()
                    );

                    case PATCH -> new Version(
                            major,
                            minor,
                            Math.addExact(patch, 1),
                            List.of(),
                            List.of()
                    );
                };
            } catch (ArithmeticException exception) {
                throw new VersionException(
                        "Version increment overflow"
                );
            }
        }
    }

    public record Constraint(
            String operator,
            Version required
    ) {
        public Constraint {
            if (!Set.of("=", ">", ">=", "<", "<=")
                    .contains(operator)) {
                throw new VersionException(
                        "Unsupported constraint operator"
                );
            }

            Objects.requireNonNull(required);
        }

        public boolean matches(Version candidate) {
            int result = candidate.compareTo(required);

            return switch (operator) {
                case "=" -> result == 0;
                case ">" -> result > 0;
                case ">=" -> result >= 0;
                case "<" -> result < 0;
                case "<=" -> result <= 0;
                default -> false;
            };
        }
    }

    public record ReleaseMetadata(
            String description,
            ChangeType changeType,
            boolean testsPassed,
            boolean documentationUpdated,
            boolean migrationNotes,
            boolean production,
            List<String> dependencies
    ) {
        public ReleaseMetadata {
            if (
                    description == null ||
                    description.isBlank()
            ) {
                throw new ReleaseException(
                        "Release description is required"
                );
            }

            Objects.requireNonNull(changeType);

            dependencies = List.copyOf(dependencies);
        }
    }

    public interface ReleaseRule {
        Optional<String> validate(
                Version version,
                ReleaseMetadata metadata
        );
    }

    public static final class TestRule implements ReleaseRule {
        @Override
        public Optional<String> validate(
                Version version,
                ReleaseMetadata metadata
        ) {
            return metadata.testsPassed()
                    ? Optional.empty()
                    : Optional.of(
                            "Automated tests have not passed"
                    );
        }
    }

    public static final class DocumentationRule
            implements ReleaseRule {

        @Override
        public Optional<String> validate(
                Version version,
                ReleaseMetadata metadata
        ) {
            return metadata.documentationUpdated()
                    ? Optional.empty()
                    : Optional.of(
                            "Documentation is incomplete"
                    );
        }
    }

    public static final class BreakingChangeRule
            implements ReleaseRule {

        @Override
        public Optional<String> validate(
                Version version,
                ReleaseMetadata metadata
        ) {
            if (
                    metadata.changeType() == ChangeType.MAJOR &&
                    !metadata.migrationNotes()
            ) {
                return Optional.of(
                        "Major releases require migration notes"
                );
            }

            return Optional.empty();
        }
    }

    public static final class ProductionRule
            implements ReleaseRule {

        @Override
        public Optional<String> validate(
                Version version,
                ReleaseMetadata metadata
        ) {
            if (
                    metadata.production() &&
                    !version.prerelease().isEmpty()
            ) {
                return Optional.of(
                        "Prerelease versions cannot be production releases"
                );
            }

            return Optional.empty();
        }
    }

    public static final class ReleasePolicy {

        private final List<ReleaseRule> rules;

        public ReleasePolicy(List<ReleaseRule> rules) {
            this.rules = List.copyOf(rules);
        }

        public List<String> evaluate(
                Version version,
                ReleaseMetadata metadata
        ) {
            return rules.stream()
                    .map(rule -> rule.validate(version, metadata))
                    .flatMap(Optional::stream)
                    .toList();
        }
    }

    public static final class Release {

        private final Version version;
        private final ReleaseMetadata metadata;

        private ReleaseState state = ReleaseState.DRAFT;

        private Release(
                Version version,
                ReleaseMetadata metadata
        ) {
            this.version = version;
            this.metadata = metadata;
        }

        public Version version() {
            return version;
        }

        public ReleaseMetadata metadata() {
            return metadata;
        }

        public ReleaseState state() {
            return state;
        }

        private void transition(ReleaseState next) {
            boolean allowed = switch (state) {
                case DRAFT ->
                        next == ReleaseState.VALIDATED ||
                        next == ReleaseState.REJECTED;

                case VALIDATED ->
                        next == ReleaseState.PUBLISHED ||
                        next == ReleaseState.REJECTED;

                case REJECTED, PUBLISHED -> false;
            };

            if (!allowed) {
                throw new ReleaseException(
                        "Invalid transition: " +
                        state + " -> " + next
                );
            }

            state = next;
        }
    }

    public static final class ReleaseService {

        private final Map<Version, Release> releases =
                new TreeMap<>();

        private final ReleasePolicy policy;

        private Version currentVersion;

        public ReleaseService(ReleasePolicy policy) {
            this.policy = Objects.requireNonNull(policy);
        }

        public synchronized Release register(
                Version version,
                ReleaseMetadata metadata
        ) {
            if (releases.containsKey(version)) {
                throw new ReleaseException(
                        "Version already exists: " + version
                );
            }

            if (
                    currentVersion != null &&
                    version.compareTo(currentVersion) <= 0
            ) {
                throw new ReleaseException(
                        "Release precedence must increase"
                );
            }

            Release release = new Release(version, metadata);
            releases.put(version, release);

            return release;
        }

        public synchronized List<String> validate(
                Release release
        ) {
            if (!releases.containsValue(release)) {
                throw new ReleaseException(
                        "Release does not belong to this service"
                );
            }

            List<String> failures = new ArrayList<>(
                    policy.evaluate(
                            release.version(),
                            release.metadata()
                    )
            );

            for (String dependency :
                    release.metadata().dependencies()) {

                Version required = Version.parse(dependency);
                Release dependencyRelease = releases.get(required);

                if (
                        dependencyRelease == null ||
                        dependencyRelease.state() != ReleaseState.PUBLISHED
                ) {
                    failures.add(
                            "Dependency is not published: " + dependency
                    );
                }
            }

            return failures;
        }

        public synchronized void publish(Release release) {
            if (release.state() != ReleaseState.DRAFT) {
                throw new ReleaseException(
                        "Only draft releases can be published"
                );
            }

            List<String> failures = validate(release);

            if (!failures.isEmpty()) {
                release.transition(ReleaseState.REJECTED);

                throw new ReleaseException(
                        String.join("; ", failures)
                );
            }

            release.transition(ReleaseState.VALIDATED);
            release.transition(ReleaseState.PUBLISHED);

            currentVersion = release.version();
        }

        public synchronized Optional<Version> currentVersion() {
            return Optional.ofNullable(currentVersion);
        }

        public synchronized List<Release> history() {
            return releases.values().stream().toList();
        }

        public boolean satisfies(
                Version candidate,
                List<Constraint> constraints
        ) {
            return constraints.stream()
                    .allMatch(
                            constraint -> constraint.matches(candidate)
                    );
        }
    }

    private static ReleasePolicy standardPolicy() {
        return new ReleasePolicy(List.of(
                new TestRule(),
                new DocumentationRule(),
                new BreakingChangeRule(),
                new ProductionRule()
        ));
    }

    private static ReleaseMetadata metadata(
            String description,
            ChangeType type,
            boolean migrationNotes,
            List<String> dependencies
    ) {
        return new ReleaseMetadata(
                description,
                type,
                true,
                true,
                migrationNotes,
                true,
                dependencies
        );
    }

    private static void runTests() {
        Version version = Version.parse("2.4.6");

        assert Version.parse("1.0.0-alpha")
                .compareTo(Version.parse("1.0.0")) < 0;

        assert Version.parse("1.0.0-beta.2")
                .compareTo(Version.parse("1.0.0-beta.11")) < 0;

        assert Version.parse("1.0.0+build.1")
                .equals(Version.parse("1.0.0+build.2"));

        assert version.increment(ChangeType.MAJOR).toString()
                .equals("3.0.0");

        assert version.increment(ChangeType.MINOR).toString()
                .equals("2.5.0");

        assert version.increment(ChangeType.PATCH).toString()
                .equals("2.4.7");

        assert Version.parse("1.0.0-rc.1")
                .compareTo(Version.parse("1.0.0")) < 0;

        boolean invalid = false;

        try {
            Version.parse("01.2.3");
        } catch (VersionException exception) {
            invalid = true;
        }

        assert invalid;

        invalid = false;

        try {
            Version.parse("1.0.0-01");
        } catch (VersionException exception) {
            invalid = true;
        }

        assert invalid;

        Constraint constraint = new Constraint(
                ">=",
                Version.parse("2.0.0")
        );

        assert constraint.matches(Version.parse("2.5.0"));

        System.out.println("All Java 17 tests passed.");
    }

    public static void main(String[] args) {

        runTests();

        System.out.println("\nSEMANTIC VERSIONING 2.0.0");

        List<Version> sequence = new ArrayList<>(List.of(
                Version.parse("1.0.0"),
                Version.parse("1.0.0-alpha"),
                Version.parse("1.0.0-beta"),
                Version.parse("1.0.0-rc.1"),
                Version.parse("1.0.0-alpha.1")
        ));

        sequence.sort(Comparator.naturalOrder());

        System.out.println("\nVersion precedence:");

        sequence.forEach(System.out::println);

        Version baseline = Version.parse("2.4.6");

        System.out.println("\nVersion increments:");

        for (ChangeType type : ChangeType.values()) {
            System.out.println(
                    type + ": " + baseline.increment(type)
            );
        }

        ReleaseService service = new ReleaseService(
                standardPolicy()
        );

        Release first = service.register(
                Version.parse("1.0.0"),
                metadata(
                        "Initial stable API",
                        ChangeType.MAJOR,
                        true,
                        List.of()
                )
        );

        service.publish(first);

        Release second = service.register(
                Version.parse("1.1.0"),
                metadata(
                        "Added transaction search",
                        ChangeType.MINOR,
                        false,
                        List.of("1.0.0")
                )
        );

        service.publish(second);

        System.out.println(
                "\nCurrent version: " +
                service.currentVersion().orElseThrow()
        );

        System.out.println("\nRelease history:");

        service.history().forEach(release ->
                System.out.println(
                        release.version() +
                        " | " +
                        release.metadata().description() +
                        " | " +
                        release.state()
                )
        );

        List<Constraint> constraints = List.of(
                new Constraint(">=", Version.parse("2.0.0")),
                new Constraint("<", Version.parse("3.0.0"))
        );

        System.out.println("\nDependency compatibility:");

        for (String candidate :
                List.of("2.5.3", "2.0.0", "3.0.0", "1.9.9")) {

            boolean compatible = service.satisfies(
                    Version.parse(candidate),
                    constraints
            );

            System.out.println(
                    candidate + ": " +
                    (compatible ? "COMPATIBLE" : "INCOMPATIBLE")
            );
        }
    }
}
