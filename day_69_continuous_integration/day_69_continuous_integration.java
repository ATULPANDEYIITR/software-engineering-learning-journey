import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.regex.Pattern;

/*
 * Enterprise Continuous Integration Governance
 *
 * Java 17
 *
 * Features:
 * - Immutable domain records
 * - Repository and commit modeling
 * - Pipeline configuration
 * - Dependency validation
 * - Asynchronous job execution
 * - Automated quality gates
 * - Retry policies
 * - Failure propagation
 * - Build artifact validation
 * - Pipeline audit events
 * - Execution reporting
 */

public class ContinuousIntegration {

    enum PipelineStatus {
        PENDING,
        RUNNING,
        SUCCESS,
        FAILED,
        CANCELLED
    }

    enum JobStatus {
        PENDING,
        RUNNING,
        SUCCESS,
        FAILED,
        SKIPPED
    }

    enum TriggerType {
        PUSH,
        PULL_REQUEST,
        SCHEDULE,
        MANUAL
    }

    static class CIException extends RuntimeException {
        CIException(String message) {
            super(message);
        }
    }

    static class ConfigurationException extends CIException {
        ConfigurationException(String message) {
            super(message);
        }
    }

    static class JobExecutionException extends CIException {
        JobExecutionException(String message) {
            super(message);
        }
    }

    record Repository(
        String name,
        String owner,
        String defaultBranch
    ) {
        Repository {
            Objects.requireNonNull(name);
            Objects.requireNonNull(owner);
            Objects.requireNonNull(defaultBranch);

            if (
                name.isBlank() ||
                owner.isBlank() ||
                defaultBranch.isBlank()
            ) {
                throw new ConfigurationException(
                    "Invalid repository configuration."
                );
            }
        }
    }

    record Commit(
        String hash,
        String branch,
        String author,
        String message
    ) {
        private static final Pattern HASH =
            Pattern.compile("[a-f0-9]{7,40}");

        Commit {
            if (
                hash == null ||
                !HASH.matcher(hash).matches()
            ) {
                throw new ConfigurationException(
                    "Invalid commit hash."
                );
            }

            if (
                branch == null ||
                !branch.matches("[A-Za-z0-9._/-]+")
            ) {
                throw new ConfigurationException(
                    "Invalid branch."
                );
            }

            if (author == null || author.isBlank()) {
                throw new ConfigurationException(
                    "Commit author is required."
                );
            }
        }
    }

    record CheckResult(
        boolean passed,
        String message,
        long durationMs
    ) {}

    record BuildArtifact(
        String name,
        String content,
        String checksum,
        Instant createdAt
    ) {}

    record JobReport(
        String name,
        JobStatus status,
        int attempts,
        String error
    ) {}

    record PipelineReport(
        String pipelineId,
        PipelineStatus status,
        String commitHash,
        List<JobReport> jobs,
        List<BuildArtifact> artifacts,
        Instant startedAt,
        Instant completedAt
    ) {
        PipelineReport {
            jobs = List.copyOf(jobs);
            artifacts = List.copyOf(artifacts);
        }
    }

    @FunctionalInterface
    interface Check {
        CheckResult execute() throws Exception;
    }

    static final class Job {

        private final String name;
        private final List<String> dependencies;
        private final int maxRetries;
        private final Check check;

        private JobStatus status = JobStatus.PENDING;
        private int attempts;
        private String error;
        private CheckResult result;

        Job(
            String name,
            List<String> dependencies,
            int maxRetries,
            Check check
        ) {
            if (name == null || name.isBlank()) {
                throw new ConfigurationException(
                    "Job name is required."
                );
            }

            if (maxRetries < 0) {
                throw new ConfigurationException(
                    "Invalid retry count."
                );
            }

            this.name = name;
            this.dependencies = List.copyOf(dependencies);
            this.maxRetries = maxRetries;
            this.check = Objects.requireNonNull(check);
        }

        String name() {
            return name;
        }

        List<String> dependencies() {
            return dependencies;
        }

        JobStatus status() {
            return status;
        }

        int attempts() {
            return attempts;
        }

        String error() {
            return error;
        }
    }

    static final class Pipeline {

        private final String id;
        private final Repository repository;
        private final Commit commit;
        private final TriggerType trigger;
        private final List<Job> jobs;

        private final List<BuildArtifact> artifacts =
            new ArrayList<>();

        private final List<String> auditEvents =
            new ArrayList<>();

        private PipelineStatus status =
            PipelineStatus.PENDING;

        private Instant startedAt;
        private Instant completedAt;

        Pipeline(
            String id,
            Repository repository,
            Commit commit,
            TriggerType trigger,
            List<Job> jobs
        ) {
            if (id == null || id.isBlank()) {
                throw new ConfigurationException(
                    "Pipeline identifier is required."
                );
            }

            this.id = id;
            this.repository = Objects.requireNonNull(repository);
            this.commit = Objects.requireNonNull(commit);
            this.trigger = Objects.requireNonNull(trigger);
            this.jobs = new ArrayList<>(jobs);

            if (jobs.isEmpty()) {
                throw new ConfigurationException(
                    "Pipeline requires at least one job."
                );
            }
        }

        void audit(String event) {
            auditEvents.add(
                Instant.now() + " | " + event
            );
        }
    }

    static final class PipelineValidator {

        static void validate(List<Job> jobs) {
            Map<String, Job> index = new LinkedHashMap<>();

            for (Job job : jobs) {
                if (index.putIfAbsent(job.name(), job) != null) {
                    throw new ConfigurationException(
                        "Duplicate job: " + job.name()
                    );
                }
            }

            for (Job job : jobs) {
                for (String dependency : job.dependencies()) {
                    if (!index.containsKey(dependency)) {
                        throw new ConfigurationException(
                            "Unknown dependency: " + dependency
                        );
                    }

                    if (dependency.equals(job.name())) {
                        throw new ConfigurationException(
                            "Self-dependency detected."
                        );
                    }
                }
            }

            Set<String> visited = new HashSet<>();
            Set<String> active = new HashSet<>();

            for (String name : index.keySet()) {
                visit(name, index, visited, active);
            }
        }

        private static void visit(
            String name,
            Map<String, Job> index,
            Set<String> visited,
            Set<String> active
        ) {
            if (active.contains(name)) {
                throw new ConfigurationException(
                    "Circular job dependency detected."
                );
            }

            if (visited.contains(name)) return;

            active.add(name);

            for (String dependency :
                    index.get(name).dependencies()) {
                visit(dependency, index, visited, active);
            }

            active.remove(name);
            visited.add(name);
        }
    }

    static final class AutomatedChecks {

        static CheckResult lint() {
            String source =
                "public class PaymentService { }";

            boolean passed =
                source.contains("class") &&
                !source.contains("\t");

            return new CheckResult(
                passed,
                "Source validation completed.",
                12
            );
        }

        static CheckResult unitTests() {
            int[][] testCases = {
                {10, 20, 30},
                {0, 0, 0},
                {-5, 5, 0}
            };

            for (int[] test : testCases) {
                if (test[0] + test[1] != test[2]) {
                    return new CheckResult(
                        false,
                        "Unit test failed.",
                        20
                    );
                }
            }

            return new CheckResult(
                true,
                "All unit tests passed.",
                20
            );
        }

        static CheckResult security() {
            String configuration = """
                DATABASE_URL=${DATABASE_URL}
                API_TOKEN=${API_TOKEN}
                """;

            boolean safe =
                !configuration.matches(
                    "(?is).*password\\s*=\\s*['\"][^'\"]+['\"].*"
                );

            return new CheckResult(
                safe,
                "Credential exposure validation completed.",
                15
            );
        }

        static CheckResult build() {
            String packageName = "payment-service-1.0.0";

            return new CheckResult(
                !packageName.isBlank(),
                "Application package generated.",
                40
            );
        }
    }

    static final class ArtifactService {

        private static String checksum(String content) {
            try {
                var digest = java.security.MessageDigest
                    .getInstance("SHA-256");

                byte[] bytes = digest.digest(
                    content.getBytes(
                        java.nio.charset.StandardCharsets.UTF_8
                    )
                );

                StringBuilder result = new StringBuilder();

                for (byte value : bytes) {
                    result.append(
                        String.format("%02x", value & 0xff)
                    );
                }

                return result.toString();

            } catch (Exception error) {
                throw new CIException(
                    "Artifact checksum calculation failed."
                );
            }
        }

        static BuildArtifact create(Pipeline pipeline) {
            String content =
                "Pipeline=" + pipeline.id +
                "\nRepository=" + pipeline.repository.name() +
                "\nCommit=" + pipeline.commit.hash() +
                "\nStatus=SUCCESS";

            return new BuildArtifact(
                pipeline.id + ".artifact",
                content,
                checksum(content),
                Instant.now()
            );
        }

        static boolean verify(BuildArtifact artifact) {
            return checksum(artifact.content())
                .equals(artifact.checksum());
        }
    }

    static final class PipelineService {

        private final ExecutorService executor;

        private final AtomicBoolean running =
            new AtomicBoolean(false);

        PipelineService(int concurrency) {
            if (concurrency < 1) {
                throw new ConfigurationException(
                    "Concurrency must be positive."
                );
            }

            executor = Executors.newFixedThreadPool(concurrency);
        }

        private boolean runJob(Job job) {
            job.status = JobStatus.RUNNING;

            for (
                int attempt = 0;
                attempt <= job.maxRetries;
                attempt++
            ) {
                job.attempts++;

                try {
                    CheckResult result = job.check.execute();

                    job.result = result;

                    if (!result.passed()) {
                        throw new JobExecutionException(
                            result.message()
                        );
                    }

                    job.status = JobStatus.SUCCESS;

                    return true;

                } catch (Exception error) {
                    job.error = error.getMessage();
                }
            }

            job.status = JobStatus.FAILED;

            return false;
        }

        private boolean dependenciesPassed(
            Job job,
            Map<String, Job> index
        ) {
            return job.dependencies().stream()
                .map(index::get)
                .allMatch(parent ->
                    parent.status() == JobStatus.SUCCESS
                );
        }

        private boolean dependencyFailed(
            Job job,
            Map<String, Job> index
        ) {
            return job.dependencies().stream()
                .map(index::get)
                .anyMatch(parent ->
                    parent.status() == JobStatus.FAILED ||
                    parent.status() == JobStatus.SKIPPED
                );
        }

        PipelineReport execute(Pipeline pipeline) {
            if (!running.compareAndSet(false, true)) {
                throw new CIException(
                    "Another pipeline is running."
                );
            }

            try {
                if (pipeline.status != PipelineStatus.PENDING) {
                    throw new CIException(
                        "Pipeline is not pending."
                    );
                }

                PipelineValidator.validate(pipeline.jobs);

                pipeline.status = PipelineStatus.RUNNING;
                pipeline.startedAt = Instant.now();

                pipeline.audit("Pipeline execution started.");

                Map<String, Job> index = new LinkedHashMap<>();

                pipeline.jobs.forEach(
                    job -> index.put(job.name(), job)
                );

                int completed = 0;

                while (completed < pipeline.jobs.size()) {
                    List<Job> ready = new ArrayList<>();

                    for (Job job : pipeline.jobs) {
                        if (job.status() != JobStatus.PENDING) {
                            continue;
                        }

                        if (dependencyFailed(job, index)) {
                            job.status = JobStatus.SKIPPED;
                            job.error = "Dependency failure.";

                            completed++;
                            continue;
                        }

                        if (dependenciesPassed(job, index)) {
                            ready.add(job);
                        }
                    }

                    if (ready.isEmpty()) {
                        if (completed < pipeline.jobs.size()) {
                            throw new CIException(
                                "Pipeline scheduling deadlock."
                            );
                        }

                        break;
                    }

                    List<CompletableFuture<Boolean>> futures =
                        ready.stream()
                            .map(job ->
                                CompletableFuture.supplyAsync(
                                    () -> runJob(job),
                                    executor
                                )
                            )
                            .toList();

                    for (int i = 0; i < futures.size(); i++) {
                        futures.get(i).join();
                        completed++;
                    }
                }

                boolean failed = pipeline.jobs.stream()
                    .anyMatch(job ->
                        job.status() == JobStatus.FAILED ||
                        job.status() == JobStatus.SKIPPED
                    );

                if (failed) {
                    pipeline.status = PipelineStatus.FAILED;
                } else {
                    BuildArtifact artifact =
                        ArtifactService.create(pipeline);

                    if (!ArtifactService.verify(artifact)) {
                        throw new CIException(
                            "Artifact integrity verification failed."
                        );
                    }

                    pipeline.artifacts.add(artifact);
                    pipeline.status = PipelineStatus.SUCCESS;
                }

                pipeline.audit(
                    "Pipeline completed: " + pipeline.status
                );

            } catch (Exception error) {
                pipeline.status = PipelineStatus.FAILED;
                pipeline.audit(
                    "Pipeline failure: " + error.getMessage()
                );

                for (Job job : pipeline.jobs) {
                    if (job.status() == JobStatus.PENDING) {
                        job.status = JobStatus.SKIPPED;
                    }
                }

            } finally {
                pipeline.completedAt = Instant.now();
                running.set(false);
            }

            List<JobReport> jobReports =
                pipeline.jobs.stream()
                    .map(job -> new JobReport(
                        job.name(),
                        job.status(),
                        job.attempts(),
                        job.error()
                    ))
                    .toList();

            return new PipelineReport(
                pipeline.id,
                pipeline.status,
                pipeline.commit.hash(),
                jobReports,
                pipeline.artifacts,
                pipeline.startedAt,
                pipeline.completedAt
            );
        }

        void shutdown() {
            executor.shutdown();

            try {
                if (!executor.awaitTermination(10, TimeUnit.SECONDS)) {
                    executor.shutdownNow();
                }
            } catch (InterruptedException error) {
                executor.shutdownNow();
                Thread.currentThread().interrupt();
            }
        }
    }

    static List<Job> createJobs() {
        return List.of(
            new Job(
                "lint",
                List.of(),
                0,
                AutomatedChecks::lint
            ),
            new Job(
                "unit-tests",
                List.of("lint"),
                0,
                AutomatedChecks::unitTests
            ),
            new Job(
                "security",
                List.of("lint"),
                0,
                AutomatedChecks::security
            ),
            new Job(
                "build",
                List.of("unit-tests", "security"),
                1,
                AutomatedChecks::build
            )
        );
    }

    static void printReport(PipelineReport report) {
        System.out.println("\nENTERPRISE CI REPORT");

        System.out.println("Pipeline: " + report.pipelineId());
        System.out.println("Commit: " + report.commitHash());
        System.out.println("Status: " + report.status());

        System.out.println("\nJOB EXECUTION");

        for (JobReport job : report.jobs()) {
            System.out.printf(
                "%-15s %-12s Attempts: %d%n",
                job.name(),
                job.status(),
                job.attempts()
            );

            if (job.error() != null) {
                System.out.println("Error: " + job.error());
            }
        }

        System.out.println("\nARTIFACTS");

        report.artifacts().forEach(
            artifact -> System.out.println(
                artifact.name() +
                " | SHA-256: " + artifact.checksum()
            )
        );
    }

    public static void main(String[] args) {
        Repository repository = new Repository(
            "payment-service",
            "engineering",
            "main"
        );

        Commit commit = new Commit(
            "a123456",
            "feature/payment",
            "developer@example.com",
            "Implement payment validation"
        );

        Pipeline pipeline = new Pipeline(
            "CI-JAVA-001",
            repository,
            commit,
            TriggerType.PULL_REQUEST,
            createJobs()
        );

        PipelineService service = new PipelineService(2);

        try {
            PipelineReport report = service.execute(pipeline);

            printReport(report);

            if (report.status() != PipelineStatus.SUCCESS) {
                throw new CIException(
                    "Continuous integration failed."
                );
            }

            System.out.println(
                "\nEnterprise CI execution successful."
            );

        } finally {
            service.shutdown();
        }
    }
}
