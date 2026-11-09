import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * Continuous Delivery Enterprise Governance System.
 *
 * Java 17 implementation featuring:
 * - Explicit domain types and immutable records
 * - Build, test, package and release stages
 * - Artifact provenance and integrity validation
 * - Environment-specific delivery policies
 * - Reviewer eligibility and approval management
 * - Status-check enforcement
 * - Release authorization
 * - Pipeline state transitions
 * - Audit events and failure reporting
 *
 * Compile: javac ContinuousDelivery.java
 * Run: java ContinuousDelivery
 */
public class ContinuousDelivery {

    enum Stage {
        BUILD,
        TEST,
        SECURITY_SCAN,
        PACKAGE,
        RELEASE
    }

    enum StageStatus {
        PENDING,
        RUNNING,
        PASSED,
        FAILED,
        SKIPPED
    }

    enum PipelineStatus {
        CREATED,
        RUNNING,
        FAILED,
        SUCCEEDED,
        RELEASED
    }

    enum Environment {
        DEVELOPMENT,
        STAGING,
        PRODUCTION
    }

    enum ApprovalDecision {
        APPROVED,
        REJECTED,
        COMMENTED,
        DISMISSED
    }

    enum MergeStrategy {
        MERGE_COMMIT,
        SQUASH,
        REBASE
    }

    static class DeliveryException extends RuntimeException {
        DeliveryException(String message) {
            super(message);
        }
    }

    static class PolicyViolationException extends DeliveryException {
        PolicyViolationException(String message) {
            super(message);
        }
    }

    static class IntegrityException extends DeliveryException {
        IntegrityException(String message) {
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

            if (name.isBlank() || owner.isBlank()) {
                throw new IllegalArgumentException(
                    "Repository identity is required"
                );
            }
        }
    }

    record Commit(
        String hash,
        String author,
        String message,
        Instant createdAt
    ) {
        Commit {
            Objects.requireNonNull(hash);
            Objects.requireNonNull(author);
            Objects.requireNonNull(message);
            Objects.requireNonNull(createdAt);

            if (hash.isBlank() || author.isBlank()) {
                throw new IllegalArgumentException("Invalid commit");
            }
        }
    }

    record Branch(
        String name,
        String headCommit,
        boolean protectedBranch,
        boolean allowDirectPush,
        boolean allowForcePush,
        boolean allowDeletion
    ) {
        Branch {
            Objects.requireNonNull(name);
            Objects.requireNonNull(headCommit);

            if (name.isBlank()) {
                throw new IllegalArgumentException("Invalid branch name");
            }
        }
    }

    record PullRequest(
        int id,
        String title,
        String sourceBranch,
        String targetBranch,
        String sourceCommit,
        String targetCommit,
        boolean draft,
        boolean open,
        boolean mergeConflict,
        MergeStrategy strategy
    ) {
        PullRequest {
            if (id <= 0 || title == null || title.isBlank()) {
                throw new IllegalArgumentException("Invalid Pull Request");
            }

            if (
                sourceBranch == null ||
                targetBranch == null ||
                sourceBranch.equals(targetBranch)
            ) {
                throw new IllegalArgumentException(
                    "Invalid source and target branches"
                );
            }

            Objects.requireNonNull(sourceCommit);
            Objects.requireNonNull(targetCommit);
            Objects.requireNonNull(strategy);
        }
    }

    record Approval(
        String reviewer,
        ApprovalDecision decision,
        boolean eligible,
        boolean stale,
        Instant submittedAt
    ) {
        Approval {
            Objects.requireNonNull(reviewer);
            Objects.requireNonNull(decision);
            Objects.requireNonNull(submittedAt);

            if (reviewer.isBlank()) {
                throw new IllegalArgumentException("Reviewer is required");
            }
        }
    }

    record StatusCheck(
        String name,
        StageStatus status,
        String details,
        Instant updatedAt
    ) {
        StatusCheck {
            Objects.requireNonNull(name);
            Objects.requireNonNull(status);
            Objects.requireNonNull(updatedAt);

            if (name.isBlank()) {
                throw new IllegalArgumentException("Check name is required");
            }
        }
    }

    record Artifact(
        String name,
        String version,
        String checksum,
        long sizeBytes,
        Instant createdAt,
        String sourceCommit
    ) {
        Artifact {
            Objects.requireNonNull(name);
            Objects.requireNonNull(version);
            Objects.requireNonNull(checksum);
            Objects.requireNonNull(createdAt);
            Objects.requireNonNull(sourceCommit);

            if (
                name.isBlank() ||
                version.isBlank() ||
                !checksum.matches("[a-fA-F0-9]{64}") ||
                sizeBytes <= 0
            ) {
                throw new IllegalArgumentException(
                    "Artifact metadata is invalid"
                );
            }
        }
    }

    record StageExecution(
        Stage stage,
        StageStatus status,
        Instant startedAt,
        Instant completedAt,
        String message
    ) {
        StageExecution {
            Objects.requireNonNull(stage);
            Objects.requireNonNull(status);
            Objects.requireNonNull(startedAt);
            Objects.requireNonNull(message);
        }
    }

    record AuditEvent(
        String eventId,
        String eventType,
        String actor,
        Instant timestamp,
        String details
    ) {}

    record EligibilityResult(
        boolean eligible,
        List<String> violations
    ) {
        EligibilityResult {
            violations = List.copyOf(violations);
        }
    }


    static final class ReviewPolicy {
        private final int requiredApprovals;
        private final Set<String> requiredChecks;
        private final boolean requireResolvedConversations;
        private final boolean requireLinearHistory;
        private final boolean prohibitDirectPush;
        private final boolean prohibitForcePush;
        private final boolean prohibitProtectedBranchDeletion;
        private final boolean productionAuthorizationRequired;
        private final boolean allowAdministratorBypass;

        ReviewPolicy(
            int requiredApprovals,
            Set<String> requiredChecks,
            boolean requireResolvedConversations,
            boolean requireLinearHistory,
            boolean prohibitDirectPush,
            boolean prohibitForcePush,
            boolean prohibitProtectedBranchDeletion,
            boolean productionAuthorizationRequired,
            boolean allowAdministratorBypass
        ) {
            if (requiredApprovals < 0) {
                throw new IllegalArgumentException(
                    "Approval count cannot be negative"
                );
            }

            this.requiredApprovals = requiredApprovals;
            this.requiredChecks = Set.copyOf(requiredChecks);
            this.requireResolvedConversations =
                requireResolvedConversations;
            this.requireLinearHistory = requireLinearHistory;
            this.prohibitDirectPush = prohibitDirectPush;
            this.prohibitForcePush = prohibitForcePush;
            this.prohibitProtectedBranchDeletion =
                prohibitProtectedBranchDeletion;
            this.productionAuthorizationRequired =
                productionAuthorizationRequired;
            this.allowAdministratorBypass = allowAdministratorBypass;
        }

        static ReviewPolicy productionDefaults() {
            return new ReviewPolicy(
                2,
                Set.of("build", "tests", "security-scan"),
                true,
                true,
                true,
                true,
                true,
                true,
                false
            );
        }
    }


    static final class PipelineRun {
        private final String id;
        private final String application;
        private final String version;
        private final Environment environment;
        private final String sourceCommit;

        private PipelineStatus status = PipelineStatus.CREATED;

        private final Map<Stage, StageExecution> stages =
            new EnumMap<>(Stage.class);

        private final Map<String, StatusCheck> checks =
            new HashMap<>();

        private final List<AuditEvent> auditEvents =
            new ArrayList<>();

        private Artifact artifact;
        private String failureReason;

        PipelineRun(
            String application,
            String version,
            Environment environment,
            String sourceCommit
        ) {
            if (
                application == null ||
                !application.matches("[a-zA-Z0-9_-]+")
            ) {
                throw new IllegalArgumentException(
                    "Invalid application identifier"
                );
            }

            if (
                version == null ||
                !version.matches("[a-zA-Z0-9.+-]+")
            ) {
                throw new IllegalArgumentException(
                    "Invalid application version"
                );
            }

            this.id = UUID.randomUUID().toString();
            this.application = application;
            this.version = version;
            this.environment = Objects.requireNonNull(environment);
            this.sourceCommit = Objects.requireNonNull(sourceCommit);
        }

        private void transition(
            PipelineStatus expected,
            PipelineStatus next
        ) {
            if (status != expected) {
                throw new DeliveryException(
                    "Invalid pipeline transition: " +
                    status + " -> " + next
                );
            }

            status = next;
            record("STATE_CHANGED", "New state: " + next);
        }

        private void record(String type, String details) {
            auditEvents.add(new AuditEvent(
                UUID.randomUUID().toString(),
                type,
                "delivery-system",
                Instant.now(),
                details
            ));
        }

        void addCheck(StatusCheck check) {
            checks.put(check.name(), check);
            record("CHECK_UPDATED", check.name() + ": " + check.status());
        }

        void attachArtifact(Artifact artifact) {
            if (status != PipelineStatus.RUNNING) {
                throw new DeliveryException(
                    "Artifact cannot be attached outside an active run"
                );
            }

            if (!artifact.version().equals(version)) {
                throw new IntegrityException("Artifact version mismatch");
            }

            if (!artifact.sourceCommit().equals(sourceCommit)) {
                throw new IntegrityException("Source commit mismatch");
            }

            this.artifact = artifact;
            record("ARTIFACT_CREATED", artifact.name());
        }

        void recordStage(
            Stage stage,
            StageStatus stageStatus,
            String message
        ) {
            Instant now = Instant.now();

            stages.put(
                stage,
                new StageExecution(
                    stage,
                    stageStatus,
                    now,
                    stageStatus == StageStatus.RUNNING ? null : now,
                    message
                )
            );

            record("STAGE_" + stageStatus, stage.name() + ": " + message);
        }

        void start() {
            transition(
                PipelineStatus.CREATED,
                PipelineStatus.RUNNING
            );
        }

        void succeed() {
            transition(
                PipelineStatus.RUNNING,
                PipelineStatus.SUCCEEDED
            );
        }

        void release() {
            transition(
                PipelineStatus.SUCCEEDED,
                PipelineStatus.RELEASED
            );
        }

        void fail(String reason) {
            if (
                status == PipelineStatus.RELEASED ||
                status == PipelineStatus.FAILED
            ) {
                throw new DeliveryException(
                    "Terminal state cannot be changed"
                );
            }

            failureReason = reason;
            status = PipelineStatus.FAILED;
            record("PIPELINE_FAILED", reason);
        }

        PipelineStatus status() {
            return status;
        }

        Artifact artifact() {
            return artifact;
        }

        Map<Stage, StageExecution> stages() {
            return Collections.unmodifiableMap(stages);
        }

        List<AuditEvent> auditEvents() {
            return List.copyOf(auditEvents);
        }

        Map<String, StatusCheck> checks() {
            return Collections.unmodifiableMap(checks);
        }

        String id() {
            return id;
        }

        String application() {
            return application;
        }

        String version() {
            return version;
        }

        Environment environment() {
            return environment;
        }

        String failureReason() {
            return failureReason;
        }
    }


    static final class GovernanceService {
        private final ReviewPolicy policy;
        private final Map<String, Branch> branches = new HashMap<>();
        private final Map<String, Commit> commits = new HashMap<>();

        GovernanceService(ReviewPolicy policy) {
            this.policy = Objects.requireNonNull(policy);
        }

        void registerCommit(Commit commit) {
            if (commits.putIfAbsent(commit.hash(), commit) != null) {
                throw new DeliveryException("Duplicate commit");
            }
        }

        void registerBranch(Branch branch) {
            if (!commits.containsKey(branch.headCommit())) {
                throw new DeliveryException(
                    "Branch references an unknown commit"
                );
            }

            if (branches.putIfAbsent(branch.name(), branch) != null) {
                throw new DeliveryException("Branch already exists");
            }
        }

        EligibilityResult evaluate(
            PullRequest request,
            List<Approval> approvals,
            Map<String, StatusCheck> checks,
            boolean conversationsResolved,
            boolean productionAuthorized,
            boolean administrator
        ) {
            List<String> violations = new ArrayList<>();

            if (!request.open()) {
                violations.add("Pull Request is closed");
            }

            if (request.draft()) {
                violations.add("Draft cannot be merged");
            }

            if (request.mergeConflict()) {
                violations.add("Merge conflict exists");
            }

            if (
                !branches.containsKey(request.sourceBranch()) ||
                !branches.containsKey(request.targetBranch())
            ) {
                violations.add("Source or target branch is unavailable");
            }

            if (!commits.containsKey(request.sourceCommit())) {
                violations.add("Proposed source commit is unavailable");
            }

            if (policy.requireResolvedConversations &&
                !conversationsResolved) {
                violations.add("Review conversations remain unresolved");
            }

            if (
                policy.requireLinearHistory &&
                request.strategy() == MergeStrategy.MERGE_COMMIT
            ) {
                violations.add("Linear history policy violated");
            }

            Set<String> eligibleApprovers = approvals.stream()
                .filter(a -> a.eligible())
                .filter(a -> !a.stale())
                .filter(a -> a.decision() == ApprovalDecision.APPROVED)
                .map(Approval::reviewer)
                .collect(Collectors.toSet());

            if (eligibleApprovers.size() < policy.requiredApprovals) {
                violations.add("Insufficient current approvals");
            }

            boolean rejected = approvals.stream()
                .anyMatch(a ->
                    a.eligible() &&
                    !a.stale() &&
                    a.decision() == ApprovalDecision.REJECTED
                );

            if (rejected) {
                violations.add("An eligible reviewer rejected the changes");
            }

            for (String required : policy.requiredChecks) {
                StatusCheck check = checks.get(required);

                if (
                    check == null ||
                    check.status() != StageStatus.PASSED
                ) {
                    violations.add(
                        "Required check missing or unsuccessful: " + required
                    );
                }
            }

            if (
                request.targetBranch().equals("main") &&
                !branches.get(request.targetBranch()).protectedBranch()
            ) {
                violations.add("Main branch is not protected");
            }

            if (
                request.targetBranch().equals("main") &&
                policy.prohibitDirectPush &&
                branches.get(request.targetBranch()).allowDirectPush()
            ) {
                violations.add("Main branch permits prohibited direct pushes");
            }

            if (
                request.targetBranch().equals("main") &&
                policy.prohibitForcePush &&
                branches.get(request.targetBranch()).allowForcePush()
            ) {
                violations.add("Main branch permits prohibited force pushes");
            }

            if (
                request.targetBranch().equals("main") &&
                policy.prohibitProtectedBranchDeletion &&
                branches.get(request.targetBranch()).allowDeletion()
            ) {
                violations.add("Main branch permits prohibited deletion");
            }

            if (
                request.targetBranch().equals("main") &&
                policy.productionAuthorizationRequired &&
                !productionAuthorized
            ) {
                violations.add("Production authorization is missing");
            }

            if (administrator && !policy.allowAdministratorBypass) {
                violations.add("Administrator bypass is prohibited");
            }

            return new EligibilityResult(
                violations.isEmpty(),
                violations
            );
        }

        void updateSourceBranch(String branchName, String newCommit) {
            Branch branch = branches.get(branchName);

            if (branch == null || !commits.containsKey(newCommit)) {
                throw new DeliveryException("Invalid branch update");
            }

            branches.put(
                branchName,
                new Branch(
                    branch.name(),
                    newCommit,
                    branch.protectedBranch(),
                    branch.allowDirectPush(),
                    branch.allowForcePush(),
                    branch.allowDeletion()
                )
            );
        }
    }


    static final class ReleaseService {
        private final Set<String> releasedArtifacts = new HashSet<>();

        void publish(
            PipelineRun run,
            boolean productionAuthorized
        ) {
            if (run.status() != PipelineStatus.SUCCEEDED) {
                throw new PolicyViolationException(
                    "Only successful pipeline runs can be released"
                );
            }

            if (
                run.environment() == Environment.PRODUCTION &&
                !productionAuthorized
            ) {
                throw new PolicyViolationException(
                    "Production approval is required"
                );
            }

            Artifact artifact = run.artifact();

            if (artifact == null) {
                throw new IntegrityException("Artifact is unavailable");
            }

            String releaseKey =
                run.application() + ":" + artifact.version();

            if (!releasedArtifacts.add(releaseKey)) {
                throw new PolicyViolationException(
                    "Artifact version has already been released"
                );
            }

            run.release();
        }

        void rollback(
            PipelineRun current,
            Artifact previous
        ) {
            Objects.requireNonNull(previous);

            if (current.status() != PipelineStatus.RELEASED) {
                throw new DeliveryException(
                    "Rollback requires a completed release"
                );
            }

            System.out.println(
                "Rollback target selected: " + previous.name() +
                " version " + previous.version()
            );

            // Rollback selects a verified previous immutable artifact.
            // Production infrastructure must perform the actual deployment.
        }
    }


    static final class PipelineService {
        PipelineRun execute(
            String application,
            String version,
            String sourceCommit,
            Environment environment,
            boolean testsPass,
            boolean securityPass
        ) {
            PipelineRun run = new PipelineRun(
                application,
                version,
                environment,
                sourceCommit
            );

            run.start();

            try {
                executeStage(run, Stage.BUILD, true, "Build successful");
                executeStage(run, Stage.TEST, testsPass, "Functional tests");

                run.addCheck(new StatusCheck(
                    "build",
                    StageStatus.PASSED,
                    "Compilation successful",
                    Instant.now()
                ));

                run.addCheck(new StatusCheck(
                    "tests",
                    testsPass ? StageStatus.PASSED : StageStatus.FAILED,
                    "Automated test execution",
                    Instant.now()
                ));

                executeStage(
                    run,
                    Stage.SECURITY_SCAN,
                    securityPass,
                    "Security analysis"
                );

                run.addCheck(new StatusCheck(
                    "security-scan",
                    securityPass ? StageStatus.PASSED : StageStatus.FAILED,
                    "Static security analysis",
                    Instant.now()
                ));

                executeStage(
                    run,
                    Stage.PACKAGE,
                    true,
                    "Package generated"
                );

                String checksum = "a".repeat(64);

                run.attachArtifact(new Artifact(
                    application + "-" + version + ".jar",
                    version,
                    checksum,
                    1024,
                    Instant.now(),
                    sourceCommit
                ));

                run.succeed();

                return run;

            } catch (RuntimeException exception) {
                run.fail(exception.getMessage());
                return run;
            }
        }

        private void executeStage(
            PipelineRun run,
            Stage stage,
            boolean success,
            String message
        ) {
            run.recordStage(stage, StageStatus.RUNNING, "Started");

            if (!success) {
                run.recordStage(stage, StageStatus.FAILED, message);
                throw new DeliveryException(
                    "Delivery stage failed: " + stage
                );
            }

            run.recordStage(stage, StageStatus.PASSED, message);
        }
    }


    private static void printPipeline(PipelineRun run) {
        System.out.println("\nPIPELINE EXECUTION");
        System.out.println("Run: " + run.id());
        System.out.println("Application: " + run.application());
        System.out.println("Version: " + run.version());
        System.out.println("Environment: " + run.environment());
        System.out.println("Status: " + run.status());

        run.stages().forEach((stage, execution) ->
            System.out.println(
                stage + " -> " + execution.status() +
                " | " + execution.message()
            )
        );

        if (run.failureReason() != null) {
            System.out.println("Failure: " + run.failureReason());
        }
    }


    public static void main(String[] args) {
        try {
            PipelineService pipelineService = new PipelineService();
            ReleaseService releaseService = new ReleaseService();

            PipelineRun successful = pipelineService.execute(
                "payment-platform",
                "4.0.0",
                "commit-a100",
                Environment.PRODUCTION,
                true,
                true
            );

            printPipeline(successful);

            releaseService.publish(successful, true);

            System.out.println(
                "Release state: " + successful.status()
            );

            PipelineRun failed = pipelineService.execute(
                "payment-platform",
                "4.1.0",
                "commit-a101",
                Environment.PRODUCTION,
                false,
                true
            );

            printPipeline(failed);

            try {
                releaseService.publish(failed, true);
            } catch (PolicyViolationException exception) {
                System.out.println(
                    "Expected release rejection: " + exception.getMessage()
                );
            }

            GovernanceService governance = new GovernanceService(
                ReviewPolicy.productionDefaults()
            );

            governance.registerCommit(new Commit(
                "commit-a100",
                "developer-a",
                "Initial application",
                Instant.now()
            ));

            governance.registerCommit(new Commit(
                "commit-a101",
                "developer-b",
                "Implement payment validation",
                Instant.now()
            ));

            governance.registerBranch(new Branch(
                "main",
                "commit-a100",
                true,
                false,
                false,
                false
            ));

            governance.registerBranch(new Branch(
                "feature/payment",
                "commit-a101",
                false,
                true,
                false,
                true
            ));

            PullRequest request = new PullRequest(
                501,
                "Payment validation",
                "feature/payment",
                "main",
                "commit-a101",
                "commit-a100",
                false,
                true,
                false,
                MergeStrategy.SQUASH
            );

            List<Approval> approvals = List.of(
                new Approval(
                    "reviewer-a",
                    ApprovalDecision.APPROVED,
                    true,
                    false,
                    Instant.now()
                ),
                new Approval(
                    "reviewer-b",
                    ApprovalDecision.APPROVED,
                    true,
                    false,
                    Instant.now()
                )
            );

            Map<String, StatusCheck> checks = new HashMap<>();

            for (String checkName :
                List.of("build", "tests", "security-scan")) {

                checks.put(
                    checkName,
                    new StatusCheck(
                        checkName,
                        StageStatus.PASSED,
                        "Passed",
                        Instant.now()
                    )
                );
            }

            EligibilityResult eligibility = governance.evaluate(
                request,
                approvals,
                checks,
                true,
                true,
                false
            );

            System.out.println("\nGOVERNANCE EVALUATION");
            System.out.println("Eligible: " + eligibility.eligible());

            eligibility.violations().forEach(
                violation -> System.out.println("BLOCKED: " + violation)
            );

            // Stale approvals cannot satisfy a current review requirement.
            List<Approval> staleApprovals = approvals.stream()
                .map(a -> new Approval(
                    a.reviewer(),
                    a.decision(),
                    a.eligible(),
                    true,
                    a.submittedAt()
                ))
                .toList();

            EligibilityResult staleResult = governance.evaluate(
                request,
                staleApprovals,
                checks,
                true,
                true,
                false
            );

            System.out.println(
                "\nStale approval scenario: " + staleResult.eligible()
            );

        } catch (Exception exception) {
            System.err.println(
                "Enterprise delivery error: " + exception.getMessage()
            );

            System.exitCode = 1;
        }
    }
}
