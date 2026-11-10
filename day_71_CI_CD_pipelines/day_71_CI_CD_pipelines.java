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
import java.util.UUID;
import java.util.stream.Collectors;

/*
 * CI/CD Enterprise Pipeline Governance System
 *
 * Java 17
 *
 * Enterprise capabilities:
 * - Typed pipeline domain model
 * - Pipeline lifecycle management
 * - Stage dependency validation
 * - Automated execution
 * - Retry policies
 * - Quality and security gates
 * - Immutable artifacts
 * - Approval policies
 * - Environment deployment rules
 * - Audit events
 * - Failure and rollback handling
 */

public class CICDPipeline {

    enum StageStatus {
        PENDING,
        RUNNING,
        SUCCESS,
        FAILED,
        SKIPPED
    }

    enum PipelineStatus {
        CREATED,
        RUNNING,
        SUCCESS,
        FAILED
    }

    enum Environment {
        DEVELOPMENT,
        STAGING,
        PRODUCTION
    }

    enum ReviewDecision {
        APPROVED,
        CHANGES_REQUESTED,
        COMMENTED
    }

    enum DeploymentStatus {
        NOT_STARTED,
        DEPLOYED,
        REJECTED,
        ROLLED_BACK
    }

    static class PipelineException extends RuntimeException {
        PipelineException(String message) {
            super(message);
        }
    }

    static class ValidationException extends PipelineException {
        ValidationException(String message) {
            super(message);
        }
    }

    record Commit(
        String sha,
        String author,
        Instant timestamp
    ) {
        Commit {
            if (sha == null || !sha.matches("[a-fA-F0-9]{40}")) {
                throw new ValidationException("Invalid commit SHA.");
            }

            Objects.requireNonNull(author);
            Objects.requireNonNull(timestamp);
        }
    }

    record Artifact(
        String name,
        String version,
        String checksum,
        long sizeBytes
    ) {
        Artifact {
            if (name == null || name.isBlank()) {
                throw new ValidationException("Artifact name required.");
            }

            if (version == null || version.isBlank()) {
                throw new ValidationException("Artifact version required.");
            }

            if (checksum == null || checksum.isBlank()) {
                throw new ValidationException("Artifact checksum required.");
            }

            if (sizeBytes < 0) {
                throw new ValidationException("Invalid artifact size.");
            }
        }
    }

    record AuditEvent(
        Instant timestamp,
        String eventType,
        String actor,
        String details
    ) {}

    record StageExecution(
        String stageName,
        StageStatus status,
        int attempts,
        long durationMillis,
        String error,
        Map<String, String> output
    ) {
        StageExecution {
            output = Map.copyOf(output);
        }
    }

    interface StageAction {
        Map<String, String> execute(PipelineContext context);
    }

    static class PipelineContext {
        private final String pipelineId = UUID.randomUUID().toString();
        private final String repository;
        private final Commit commit;
        private final Environment environment;
        private final Map<String, Artifact> artifacts = new LinkedHashMap<>();
        private final Map<String, String> variables = new HashMap<>();
        private final List<AuditEvent> auditEvents = new ArrayList<>();
        private boolean deploymentApproval;

        PipelineContext(
            String repository,
            Commit commit,
            Environment environment,
            boolean deploymentApproval
        ) {
            if (repository == null || repository.isBlank()) {
                throw new ValidationException("Repository is required.");
            }

            this.repository = repository;
            this.commit = Objects.requireNonNull(commit);
            this.environment = Objects.requireNonNull(environment);
            this.deploymentApproval = deploymentApproval;
        }

        void addArtifact(Artifact artifact) {
            if (artifacts.putIfAbsent(
                artifact.name(),
                artifact
            ) != null) {
                throw new ValidationException(
                    "Duplicate artifact: " + artifact.name()
                );
            }
        }

        void audit(String type, String actor, String details) {
            auditEvents.add(
                new AuditEvent(
                    Instant.now(),
                    type,
                    actor,
                    details
                )
            );
        }

        public String pipelineId() {
            return pipelineId;
        }

        public String repository() {
            return repository;
        }

        public Commit commit() {
            return commit;
        }

        public Environment environment() {
            return environment;
        }

        public Map<String, Artifact> artifacts() {
            return Collections.unmodifiableMap(artifacts);
        }

        public List<AuditEvent> auditEvents() {
            return Collections.unmodifiableList(auditEvents);
        }

        public boolean deploymentApproval() {
            return deploymentApproval;
        }
    }

    static class PipelineStage {
        private final String name;
        private final List<String> dependencies;
        private final StageAction action;
        private final int maximumAttempts;
        private final boolean approvalRequired;
        private StageStatus status = StageStatus.PENDING;

        PipelineStage(
            String name,
            List<String> dependencies,
            StageAction action,
            int maximumAttempts,
            boolean approvalRequired
        ) {
            if (name == null || name.isBlank()) {
                throw new ValidationException("Stage name required.");
            }

            if (maximumAttempts < 1) {
                throw new ValidationException(
                    "At least one attempt required."
                );
            }

            this.name = name;
            this.dependencies = List.copyOf(dependencies);
            this.action = Objects.requireNonNull(action);
            this.maximumAttempts = maximumAttempts;
            this.approvalRequired = approvalRequired;
        }
    }

    static class Pipeline {
        private final PipelineContext context;
        private final Map<String, PipelineStage> stages =
            new LinkedHashMap<>();

        private final Map<String, StageExecution> results =
            new LinkedHashMap<>();

        private PipelineStatus status = PipelineStatus.CREATED;

        Pipeline(PipelineContext context) {
            this.context = Objects.requireNonNull(context);
        }

        void addStage(PipelineStage stage) {
            if (status != PipelineStatus.CREATED) {
                throw new PipelineException(
                    "Cannot modify a running pipeline."
                );
            }

            if (stages.putIfAbsent(stage.name, stage) != null) {
                throw new ValidationException(
                    "Duplicate stage: " + stage.name
                );
            }
        }

        private List<String> resolveExecutionOrder() {
            Map<String, Integer> indegree = new HashMap<>();
            Map<String, List<String>> dependents = new HashMap<>();

            stages.keySet().forEach(name -> {
                indegree.put(name, 0);
                dependents.put(name, new ArrayList<>());
            });

            for (PipelineStage stage : stages.values()) {
                for (String dependency : stage.dependencies) {
                    if (!stages.containsKey(dependency)) {
                        throw new ValidationException(
                            "Unknown dependency: " + dependency
                        );
                    }

                    if (dependency.equals(stage.name)) {
                        throw new ValidationException(
                            "Self-dependency detected."
                        );
                    }

                    indegree.merge(stage.name, 1, Integer::sum);
                    dependents.get(dependency).add(stage.name);
                }
            }

            List<String> ready = new ArrayList<>();

            indegree.forEach((name, degree) -> {
                if (degree == 0) ready.add(name);
            });

            Collections.sort(ready);

            List<String> order = new ArrayList<>();

            while (!ready.isEmpty()) {
                String current = ready.remove(0);
                order.add(current);

                for (String dependent : dependents.get(current)) {
                    int degree = indegree.merge(
                        dependent,
                        -1,
                        Integer::sum
                    );

                    if (degree == 0) {
                        ready.add(dependent);
                        Collections.sort(ready);
                    }
                }
            }

            if (order.size() != stages.size()) {
                throw new ValidationException(
                    "Circular dependency detected."
                );
            }

            return order;
        }

        private StageExecution executeStage(PipelineStage stage) {
            for (String dependency : stage.dependencies) {
                StageExecution result = results.get(dependency);

                if (
                    result == null ||
                    result.status() != StageStatus.SUCCESS
                ) {
                    stage.status = StageStatus.SKIPPED;

                    return new StageExecution(
                        stage.name,
                        StageStatus.SKIPPED,
                        0,
                        0,
                        "Dependency failed.",
                        Map.of()
                    );
                }
            }

            if (
                stage.approvalRequired &&
                !context.deploymentApproval()
            ) {
                stage.status = StageStatus.FAILED;

                return new StageExecution(
                    stage.name,
                    StageStatus.FAILED,
                    0,
                    0,
                    "Manual approval required.",
                    Map.of()
                );
            }

            stage.status = StageStatus.RUNNING;

            long start = System.nanoTime();
            String error = null;
            int attempts = 0;
            Map<String, String> output = Map.of();

            for (
                int attempt = 1;
                attempt <= stage.maximumAttempts;
                attempt++
            ) {
                attempts = attempt;

                try {
                    output = stage.action.execute(context);

                    if (output == null) {
                        throw new PipelineException(
                            "Stage returned null output."
                        );
                    }

                    error = null;
                    stage.status = StageStatus.SUCCESS;
                    break;

                } catch (RuntimeException exception) {
                    error = exception.getClass().getSimpleName()
                        + ": " + exception.getMessage();

                    context.audit(
                        "STAGE_ATTEMPT_FAILED",
                        "pipeline-engine",
                        stage.name + ": " + error
                    );
                }
            }

            long duration =
                (System.nanoTime() - start) / 1_000_000;

            StageExecution execution = new StageExecution(
                stage.name,
                stage.status,
                attempts,
                duration,
                error,
                output
            );

            context.audit(
                "STAGE_COMPLETED",
                "pipeline-engine",
                stage.name + "=" + stage.status
            );

            return execution;
        }

        PipelineStatus run() {
            if (status != PipelineStatus.CREATED) {
                throw new PipelineException(
                    "Pipeline can only execute once."
                );
            }

            if (stages.isEmpty()) {
                throw new ValidationException("Empty pipeline.");
            }

            List<String> order = resolveExecutionOrder();
            status = PipelineStatus.RUNNING;

            context.audit(
                "PIPELINE_STARTED",
                "pipeline-engine",
                context.repository()
            );

            for (String name : order) {
                PipelineStage stage = stages.get(name);
                StageExecution result = executeStage(stage);

                results.put(name, result);

                if (result.status() == StageStatus.FAILED) {
                    status = PipelineStatus.FAILED;

                    for (String remaining : order) {
                        if (results.containsKey(remaining)) continue;

                        PipelineStage pending = stages.get(remaining);
                        pending.status = StageStatus.SKIPPED;

                        results.put(
                            remaining,
                            new StageExecution(
                                remaining,
                                StageStatus.SKIPPED,
                                0,
                                0,
                                "Pipeline stopped after failure.",
                                Map.of()
                            )
                        );
                    }

                    break;
                }
            }

            if (status != PipelineStatus.FAILED) {
                status = PipelineStatus.SUCCESS;
            }

            context.audit(
                "PIPELINE_FINISHED",
                "pipeline-engine",
                status.name()
            );

            return status;
        }

        PipelineStatus status() {
            return status;
        }

        Map<String, StageExecution> results() {
            return Collections.unmodifiableMap(results);
        }
    }

    record ApprovalPolicy(
        int requiredApprovals,
        boolean requireIndependentReviewer,
        boolean requireSecurityApproval
    ) {
        ApprovalPolicy {
            if (requiredApprovals < 0) {
                throw new ValidationException(
                    "Invalid approval count."
                );
            }
        }
    }

    record PullRequest(
        int id,
        String sourceBranch,
        String targetBranch,
        boolean open,
        boolean draft,
        boolean conversationsResolved,
        boolean conflictsPresent,
        boolean sourceSynchronized,
        int approvals,
        boolean independentApproval,
        boolean securityApproval,
        boolean changesRequested
    ) {
        PullRequest {
            if (id <= 0 || approvals < 0) {
                throw new ValidationException(
                    "Invalid Pull Request attributes."
                );
            }
        }
    }

    record EligibilityResult(
        boolean eligible,
        List<String> reasons
    ) {
        EligibilityResult {
            reasons = List.copyOf(reasons);
        }
    }

    static class MergeEligibilityService {
        private final ApprovalPolicy policy;

        MergeEligibilityService(ApprovalPolicy policy) {
            this.policy = policy;
        }

        EligibilityResult evaluate(
            PullRequest pr,
            Pipeline pipeline,
            boolean requiredChecksPassed
        ) {
            List<String> reasons = new ArrayList<>();

            if (!pr.open()) reasons.add("Pull Request is closed.");
            if (pr.draft()) reasons.add("Draft Pull Request.");
            if (!pr.conversationsResolved()) {
                reasons.add("Unresolved conversations.");
            }
            if (pr.conflictsPresent()) {
                reasons.add("Merge conflicts exist.");
            }
            if (!pr.sourceSynchronized()) {
                reasons.add("Source branch is outdated.");
            }
            if (pr.approvals() < policy.requiredApprovals()) {
                reasons.add("Insufficient approvals.");
            }
            if (
                policy.requireIndependentReviewer() &&
                !pr.independentApproval()
            ) {
                reasons.add("Independent reviewer required.");
            }
            if (
                policy.requireSecurityApproval() &&
                !pr.securityApproval()
            ) {
                reasons.add("Security approval required.");
            }
            if (pr.changesRequested()) {
                reasons.add("Outstanding change request.");
            }
            if (pipeline.status() != PipelineStatus.SUCCESS) {
                reasons.add("Pipeline has not succeeded.");
            }
            if (!requiredChecksPassed) {
                reasons.add("Required status checks failed.");
            }

            return new EligibilityResult(
                reasons.isEmpty(),
                reasons
            );
        }
    }

    static class DeploymentService {
        private DeploymentStatus status =
            DeploymentStatus.NOT_STARTED;

        DeploymentStatus deploy(
            Pipeline pipeline,
            PipelineContext context,
            Artifact artifact,
            boolean approved
        ) {
            if (pipeline.status() != PipelineStatus.SUCCESS) {
                status = DeploymentStatus.REJECTED;
                return status;
            }

            if (
                context.environment() == Environment.PRODUCTION &&
                !approved
            ) {
                status = DeploymentStatus.REJECTED;
                return status;
            }

            if (
                !context.artifacts().containsKey(artifact.name()) ||
                !context.artifacts().get(artifact.name()).equals(artifact)
            ) {
                status = DeploymentStatus.REJECTED;
                return status;
            }

            status = DeploymentStatus.DEPLOYED;

            context.audit(
                "DEPLOYMENT_COMPLETED",
                "deployment-service",
                artifact.name() + "@" + artifact.version()
            );

            return status;
        }

        DeploymentStatus rollback() {
            if (status != DeploymentStatus.DEPLOYED) {
                throw new PipelineException(
                    "Only a completed deployment can be rolled back."
                );
            }

            status = DeploymentStatus.ROLLED_BACK;
            return status;
        }
    }

    static StageAction checkout() {
        return context -> Map.of(
            "repository", context.repository(),
            "commit", context.commit().sha(),
            "result", "CHECKED_OUT"
        );
    }

    static StageAction build() {
        return context -> {
            String checksum =
                "sha256:" + context.commit().sha();

            context.addArtifact(
                new Artifact(
                    "payment-service",
                    "1.4.2",
                    checksum,
                    5242880
                )
            );

            return Map.of(
                "artifact", "payment-service",
                "checksum", checksum
            );
        };
    }

    static StageAction tests() {
        return context -> {
            Map<String, Boolean> tests = Map.of(
                "unit", true,
                "integration", true,
                "configuration", true,
                "validation", true
            );

            long failures = tests.values()
                .stream()
                .filter(passed -> !passed)
                .count();

            if (failures > 0) {
                throw new PipelineException(
                    "Automated test suite failed."
                );
            }

            return Map.of(
                "executed", Integer.toString(tests.size()),
                "failed", "0"
            );
        };
    }

    static StageAction securityScan() {
        return context -> {
            int criticalFindings = 0;
            int highFindings = 0;

            if (criticalFindings > 0 || highFindings > 0) {
                throw new PipelineException(
                    "Security policy violation."
                );
            }

            return Map.of(
                "critical", "0",
                "high", "0",
                "result", "PASSED"
            );
        };
    }

    static StageAction packageApplication() {
        return context -> {
            if (!context.artifacts().containsKey("payment-service")) {
                throw new PipelineException(
                    "Build artifact unavailable."
                );
            }

            return Map.of(
                "package", "payment-service.tar",
                "result", "PACKAGED"
            );
        };
    }

    public static void main(String[] args) {
        Commit commit = new Commit(
            "a".repeat(40),
            "engineering-team",
            Instant.now()
        );

        PipelineContext context = new PipelineContext(
            "engineering/payment-service",
            commit,
            Environment.PRODUCTION,
            true
        );

        Pipeline pipeline = new Pipeline(context);

        pipeline.addStage(
            new PipelineStage(
                "checkout",
                List.of(),
                checkout(),
                1,
                false
            )
        );

        pipeline.addStage(
            new PipelineStage(
                "build",
                List.of("checkout"),
                build(),
                2,
                false
            )
        );

        pipeline.addStage(
            new PipelineStage(
                "tests",
                List.of("build"),
                tests(),
                2,
                false
            )
        );

        pipeline.addStage(
            new PipelineStage(
                "security_scan",
                List.of("build"),
                securityScan(),
                1,
                false
            )
        );

        pipeline.addStage(
            new PipelineStage(
                "package",
                List.of("tests", "security_scan"),
                packageApplication(),
                1,
                false
            )
        );

        pipeline.addStage(
            new PipelineStage(
                "deployment_gate",
                List.of("package"),
                context -> Map.of(
                    "approval", "GRANTED"
                ),
                1,
                true
            )
        );

        PipelineStatus result = pipeline.run();

        System.out.println(
            "\nPipeline status: " + result
        );

        pipeline.results().values().forEach(stage ->
            System.out.printf(
                "%-20s %-10s %d attempts%n",
                stage.stageName(),
                stage.status(),
                stage.attempts()
            )
        );

        PullRequest pr = new PullRequest(
            104,
            "feature/payment-validation",
            "main",
            true,
            false,
            true,
            false,
            true,
            2,
            true,
            true,
            false
        );

        MergeEligibilityService eligibilityService =
            new MergeEligibilityService(
                new ApprovalPolicy(2, true, true)
            );

        EligibilityResult eligibility =
            eligibilityService.evaluate(
                pr,
                pipeline,
                true
            );

        System.out.println(
            "\nMerge eligible: " + eligibility.eligible()
        );

        eligibility.reasons().forEach(
            reason -> System.out.println(" - " + reason)
        );

        Artifact artifact =
            context.artifacts().get("payment-service");

        DeploymentService deployment = new DeploymentService();

        DeploymentStatus deploymentResult = deployment.deploy(
            pipeline,
            context,
            artifact,
            true
        );

        System.out.println(
            "\nDeployment: " + deploymentResult
        );

        if (deploymentResult == DeploymentStatus.DEPLOYED) {
            System.out.println(
                "Rollback: " + deployment.rollback()
            );
        }

        System.out.println(
            "\nAudit events: " + context.auditEvents().size()
        );

        if (result != PipelineStatus.SUCCESS) {
            System.exit(1);
        }
    }
}
