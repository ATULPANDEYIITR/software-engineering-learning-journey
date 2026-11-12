import java.util.*;
import java.util.regex.Pattern;
import java.security.MessageDigest;
import java.nio.charset.StandardCharsets;

/**
 * Package Management: Enterprise Dependency Governance
 *
 * Java 17 implementation featuring:
 * - Immutable domain records
 * - Semantic versioning
 * - Dependency resolution
 * - Version policies
 * - Installation lifecycle
 * - Security validation
 * - Dependency auditing
 * - Transactional state updates
 */

public class PackageManagement {

    enum PackageStatus {
        AVAILABLE,
        DEPRECATED,
        VULNERABLE
    }

    enum InstallationStatus {
        PLANNED,
        VALIDATED,
        INSTALLED,
        REJECTED
    }

    static class PackageException extends RuntimeException {
        PackageException(String message) {
            super(message);
        }
    }

    record Version(int major, int minor, int patch)
            implements Comparable<Version> {

        Version {
            if (major < 0 || minor < 0 || patch < 0) {
                throw new PackageException("Negative version component");
            }
        }

        static Version parse(String value) {
            if (value == null ||
                !Pattern.matches(
                    "(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)",
                    value
                )) {
                throw new PackageException(
                    "Invalid semantic version: " + value
                );
            }

            try {
                String[] parts = value.split("\\.");
                return new Version(
                    Integer.parseInt(parts[0]),
                    Integer.parseInt(parts[1]),
                    Integer.parseInt(parts[2])
                );
            } catch (NumberFormatException error) {
                throw new PackageException("Version component overflow");
            }
        }

        @Override
        public int compareTo(Version other) {
            int result = Integer.compare(major, other.major);

            if (result == 0) {
                result = Integer.compare(minor, other.minor);
            }

            if (result == 0) {
                result = Integer.compare(patch, other.patch);
            }

            return result;
        }

        @Override
        public String toString() {
            return major + "." + minor + "." + patch;
        }
    }

    record VersionRequirement(String expression) {

        VersionRequirement {
            Objects.requireNonNull(expression);

            if (expression.isBlank()) {
                throw new PackageException("Empty version requirement");
            }

            // Validate every expression when the policy is created.
            if (!expression.equals("*")) {
                for (String part : expression.split(",")) {
                    parseExpression(part.trim());
                }
            }
        }

        private static String[] parseExpression(String expression) {
            var matcher = Pattern.compile(
                "^(>=|<=|>|<|=|\\^|~)?(.+)$"
            ).matcher(expression);

            if (!matcher.matches()) {
                throw new PackageException(
                    "Invalid version constraint: " + expression
                );
            }

            Version.parse(matcher.group(2));

            return new String[] {
                matcher.group(1) == null ? "=" : matcher.group(1),
                matcher.group(2)
            };
        }

        boolean matches(Version version) {
            if (expression.equals("*")) return true;

            for (String part : expression.split(",")) {
                String[] parsed = parseExpression(part.trim());
                String operator = parsed[0];
                Version target = Version.parse(parsed[1]);

                int comparison = version.compareTo(target);

                boolean valid = switch (operator) {
                    case "=" -> comparison == 0;
                    case ">" -> comparison > 0;
                    case "<" -> comparison < 0;
                    case ">=" -> comparison >= 0;
                    case "<=" -> comparison <= 0;
                    case "^" -> {
                        Version upper = target.major() > 0
                            ? new Version(target.major() + 1, 0, 0)
                            : target.minor() > 0
                                ? new Version(0, target.minor() + 1, 0)
                                : new Version(0, 0, target.patch() + 1);

                        yield comparison >= 0 &&
                            version.compareTo(upper) < 0;
                    }
                    case "~" -> {
                        Version upper = new Version(
                            target.major(),
                            target.minor() + 1,
                            0
                        );

                        yield comparison >= 0 &&
                            version.compareTo(upper) < 0;
                    }
                    default -> false;
                };

                if (!valid) return false;
            }

            return true;
        }
    }

    record PackageDefinition(
        String name,
        Version version,
        Map<String, VersionRequirement> dependencies,
        PackageStatus status,
        String checksum
    ) {
        PackageDefinition {
            if (name == null ||
                !Pattern.matches(
                    "[a-zA-Z0-9][a-zA-Z0-9_.-]{0,99}",
                    name
                )) {
                throw new PackageException("Invalid package name");
            }

            Objects.requireNonNull(version);
            Objects.requireNonNull(status);

            dependencies = Collections.unmodifiableMap(
                new TreeMap<>(dependencies)
            );

            String calculated = calculateChecksum(
                name, version, dependencies
            );

            if (checksum == null || checksum.isBlank()) {
                checksum = calculated;
            }
        }

        boolean verifyIntegrity() {
            return checksum.equals(
                calculateChecksum(name, version, dependencies)
            );
        }

        private static String calculateChecksum(
            String name,
            Version version,
            Map<String, VersionRequirement> dependencies
        ) {
            try {
                String canonical = name + ":" + version + ":" +
                    new TreeMap<>(dependencies);

                byte[] digest = MessageDigest.getInstance("SHA-256")
                    .digest(canonical.getBytes(StandardCharsets.UTF_8));

                return HexFormat.of().formatHex(digest);

            } catch (Exception error) {
                throw new PackageException(
                    "Unable to calculate package checksum"
                );
            }
        }
    }

    interface InstallationPolicy {
        void validate(
            PackageDefinition definition,
            PackageDefinition currentlyInstalled
        );
    }

    static final class EnterprisePolicy
            implements InstallationPolicy {

        private final boolean permitVulnerable;
        private final boolean permitDowngrades;
        private final int maximumPackages;

        EnterprisePolicy(
            boolean permitVulnerable,
            boolean permitDowngrades,
            int maximumPackages
        ) {
            if (maximumPackages < 1) {
                throw new PackageException("Invalid package limit");
            }

            this.permitVulnerable = permitVulnerable;
            this.permitDowngrades = permitDowngrades;
            this.maximumPackages = maximumPackages;
        }

        int maximumPackages() {
            return maximumPackages;
        }

        @Override
        public void validate(
            PackageDefinition definition,
            PackageDefinition currentlyInstalled
        ) {
            if (definition.status() != PackageStatus.AVAILABLE &&
                !(permitVulnerable &&
                  definition.status() == PackageStatus.VULNERABLE)) {
                throw new PackageException(
                    "Package rejected by status policy: " +
                    definition.name()
                );
            }

            if (!definition.verifyIntegrity()) {
                throw new PackageException(
                    "Package integrity verification failed"
                );
            }

            if (currentlyInstalled != null &&
                definition.version().compareTo(
                    currentlyInstalled.version()
                ) < 0 &&
                !permitDowngrades) {
                throw new PackageException(
                    "Downgrade prohibited: " + definition.name()
                );
            }
        }
    }

    static final class PackageRegistry {
        private final Map<String, List<PackageDefinition>> catalog =
            new HashMap<>();

        void publish(PackageDefinition definition) {
            List<PackageDefinition> versions =
                catalog.computeIfAbsent(
                    definition.name(),
                    ignored -> new ArrayList<>()
                );

            if (versions.stream().anyMatch(
                existing -> existing.version().equals(
                    definition.version()
                )
            )) {
                throw new PackageException("Duplicate package version");
            }

            versions.add(definition);

            versions.sort(
                Comparator.comparing(PackageDefinition::version)
                    .reversed()
            );
        }

        List<PackageDefinition> findVersions(String name) {
            List<PackageDefinition> versions = catalog.get(name);

            if (versions == null) {
                throw new PackageException(
                    "Unknown package: " + name
                );
            }

            return List.copyOf(versions);
        }

        Optional<PackageDefinition> select(
            String name,
            List<VersionRequirement> requirements
        ) {
            return findVersions(name).stream()
                .filter(pkg -> pkg.status() == PackageStatus.AVAILABLE)
                .filter(pkg -> requirements.stream().allMatch(
                    requirement -> requirement.matches(pkg.version())
                ))
                .findFirst();
        }
    }

    static final class DependencyResolver {
        private final PackageRegistry registry;

        DependencyResolver(PackageRegistry registry) {
            this.registry = registry;
        }

        Map<String, PackageDefinition> resolve(
            Map<String, VersionRequirement> requirements
        ) {
            Map<String, List<VersionRequirement>> constraints =
                new TreeMap<>();

            requirements.forEach((name, requirement) ->
                constraints.computeIfAbsent(
                    name, ignored -> new ArrayList<>()
                ).add(requirement)
            );

            Map<String, PackageDefinition> selected =
                new TreeMap<>();

            if (!search(
                constraints,
                selected,
                new HashSet<>(),
                new HashSet<>()
            )) {
                throw new PackageException(
                    "Dependency resolution failed"
                );
            }

            return Collections.unmodifiableMap(
                new TreeMap<>(selected)
            );
        }

        private boolean search(
            Map<String, List<VersionRequirement>> constraints,
            Map<String, PackageDefinition> selected,
            Set<String> resolving,
            Set<String> resolved
        ) {
            String next = constraints.keySet().stream()
                .filter(name -> !resolved.contains(name))
                .findFirst()
                .orElse(null);

            if (next == null) return true;
            if (resolving.contains(next)) return false;

            List<PackageDefinition> candidates;

            try {
                candidates = registry.findVersions(next).stream()
                    .filter(pkg -> pkg.status() ==
                        PackageStatus.AVAILABLE)
                    .filter(pkg -> constraints.get(next).stream()
                        .allMatch(rule -> rule.matches(pkg.version())))
                    .toList();
            } catch (PackageException error) {
                return false;
            }

            for (PackageDefinition candidate : candidates) {
                Map<String, PackageDefinition> oldSelected =
                    new TreeMap<>(selected);

                Map<String, List<VersionRequirement>> oldConstraints =
                    new TreeMap<>();

                constraints.forEach((key, value) ->
                    oldConstraints.put(key, new ArrayList<>(value))
                );

                Set<String> oldResolving = new HashSet<>(resolving);
                Set<String> oldResolved = new HashSet<>(resolved);

                selected.put(next, candidate);
                resolving.add(next);

                boolean cycle = false;

                for (var dependency :
                    candidate.dependencies().entrySet()) {

                    constraints.computeIfAbsent(
                        dependency.getKey(),
                        ignored -> new ArrayList<>()
                    ).add(dependency.getValue());

                    if (resolving.contains(dependency.getKey())) {
                        cycle = true;
                        break;
                    }
                }

                resolving.remove(next);

                if (!cycle) {
                    resolved.add(next);

                    if (search(
                        constraints,
                        selected,
                        resolving,
                        resolved
                    )) {
                        return true;
                    }
                }

                selected.clear();
                selected.putAll(oldSelected);

                constraints.clear();
                constraints.putAll(oldConstraints);

                resolving.clear();
                resolving.addAll(oldResolving);

                resolved.clear();
                resolved.addAll(oldResolved);
            }

            return false;
        }
    }

    record InstallationResult(
        InstallationStatus status,
        Map<String, PackageDefinition> packages,
        String message
    ) {
        InstallationResult {
            packages = Collections.unmodifiableMap(
                new TreeMap<>(packages)
            );
        }
    }

    static final class InstallationService {
        private final PackageRegistry registry;
        private final InstallationPolicy policy;

        private Map<String, PackageDefinition> installed =
            new TreeMap<>();

        InstallationService(
            PackageRegistry registry,
            InstallationPolicy policy
        ) {
            this.registry = registry;
            this.policy = policy;
        }

        synchronized InstallationResult install(
            Map<String, VersionRequirement> requirements
        ) {
            Map<String, PackageDefinition> plan =
                new DependencyResolver(registry).resolve(requirements);

            if (plan.size() > ((EnterprisePolicy) policy)
                    .maximumPackages()) {
                throw new PackageException(
                    "Enterprise package limit exceeded"
                );
            }

            // Stage changes separately to preserve atomicity.
            Map<String, PackageDefinition> nextState =
                new TreeMap<>(installed);

            for (var entry : plan.entrySet()) {
                PackageDefinition definition = entry.getValue();

                policy.validate(
                    definition,
                    installed.get(entry.getKey())
                );

                nextState.put(entry.getKey(), definition);
            }

            installed = nextState;

            return new InstallationResult(
                InstallationStatus.INSTALLED,
                plan,
                "Installation committed successfully"
            );
        }

        synchronized void uninstall(String name) {
            if (!installed.containsKey(name)) {
                throw new PackageException("Package not installed");
            }

            boolean required = installed.values().stream()
                .anyMatch(pkg ->
                    !pkg.name().equals(name) &&
                    pkg.dependencies().containsKey(name)
                );

            if (required) {
                throw new PackageException(
                    "Package is still required: " + name
                );
            }

            Map<String, PackageDefinition> next =
                new TreeMap<>(installed);

            next.remove(name);
            installed = next;
        }

        synchronized Map<String, PackageDefinition> installed() {
            return Collections.unmodifiableMap(
                new TreeMap<>(installed)
            );
        }

        List<String> audit() {
            return installed.values().stream()
                .filter(pkg -> pkg.status() != PackageStatus.AVAILABLE)
                .map(pkg -> pkg.name() + " requires investigation")
                .toList();
        }
    }

    public static void main(String[] args) {
        PackageRegistry registry = new PackageRegistry();

        registry.publish(new PackageDefinition(
            "core",
            Version.parse("1.0.0"),
            Map.of(),
            PackageStatus.AVAILABLE,
            null
        ));

        registry.publish(new PackageDefinition(
            "core",
            Version.parse("1.2.0"),
            Map.of(),
            PackageStatus.AVAILABLE,
            null
        ));

        registry.publish(new PackageDefinition(
            "database",
            Version.parse("1.0.0"),
            Map.of(
                "core",
                new VersionRequirement("^1.0.0")
            ),
            PackageStatus.AVAILABLE,
            null
        ));

        registry.publish(new PackageDefinition(
            "api-service",
            Version.parse("1.0.0"),
            Map.of(
                "core",
                new VersionRequirement("^1.0.0"),
                "database",
                new VersionRequirement("^1.0.0")
            ),
            PackageStatus.AVAILABLE,
            null
        ));

        registry.publish(new PackageDefinition(
            "api-service",
            Version.parse("1.1.0"),
            Map.of(
                "core",
                new VersionRequirement("^1.0.0"),
                "database",
                new VersionRequirement("^1.0.0")
            ),
            PackageStatus.AVAILABLE,
            null
        ));

        EnterprisePolicy policy = new EnterprisePolicy(
            false,
            false,
            100
        );

        InstallationService service =
            new InstallationService(registry, policy);

        System.out.println("ENTERPRISE PACKAGE MANAGEMENT");
        System.out.println("=============================");

        InstallationResult result = service.install(
            Map.of(
                "api-service",
                new VersionRequirement("^1.0.0")
            )
        );

        System.out.println("\nInstallation state: " + result.status());

        result.packages().forEach((name, definition) ->
            System.out.println(
                name + "@" + definition.version()
            )
        );

        System.out.println("\nInstalled inventory:");

        service.installed().forEach((name, definition) ->
            System.out.println(
                name + "@" + definition.version()
            )
        );

        System.out.println("\nVersion evaluation:");

        System.out.println(
            new VersionRequirement("^1.0.0")
                .matches(Version.parse("1.5.0"))
        );

        System.out.println(
            new VersionRequirement("^1.0.0")
                .matches(Version.parse("2.0.0"))
        );

        System.out.println("\nConflict test:");

        try {
            service.install(Map.of(
                "core", new VersionRequirement("^1.0.0"),
                "database", new VersionRequirement("^2.0.0")
            ));
        } catch (PackageException error) {
            System.out.println("Rejected: " + error.getMessage());
        }

        System.out.println("\nUninstallation test:");

        try {
            service.uninstall("core");
        } catch (PackageException error) {
            System.out.println("Rejected: " + error.getMessage());
        }

        System.out.println("\nSecurity audit:");

        service.audit().forEach(System.out::println);

        System.out.println("\nEnterprise checks completed.");
    }
}
