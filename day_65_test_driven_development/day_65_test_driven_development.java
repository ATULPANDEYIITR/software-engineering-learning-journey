import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import java.util.function.Supplier;
import java.util.stream.Collectors;

/**
 * Test-Driven Development and enterprise repository governance.
 *
 * Compile:
 *   javac TddWorkflow.java
 *
 * Run:
 *   java TddWorkflow
 */
public class TddWorkflow {

    // ========================================================
    // ENUMERATIONS
    // ========================================================

    enum TddStage {
        RED,
        GREEN,
        REFACTOR
    }

    enum PullRequestState {
        DRAFT,
        OPEN,
        CLOSED,
        MERGED
    }

    enum ReviewDecision {
        APPROVED,
        CHANGES_REQUESTED,
        COMMENTED
    }

    enum CheckStatus {
        PENDING,
        PASSED,
        FAILED
    }

    enum MergeStrategy {
        MERGE_COMMIT,
        SQUASH,
        REBASE
    }

    // ========================================================
    // CUSTOM EXCEPTIONS
    // ========================================================

    static class DomainException extends RuntimeException {
        DomainException(String message) {
            super(message);
        }
    }

    static class ValidationException extends DomainException {
        ValidationException(String message) {
            super(message);
        }
    }

    static class WorkflowException extends DomainException {
        WorkflowException(String message) {
            super(message);
        }
    }

    static class PolicyException extends DomainException {
        PolicyException(String message) {
            super(message);
        }
    }

    // ========================================================
    // IMMUTABLE DOMAIN RECORDS
    // ========================================================

    record Commit(
        String hash,
        String message,
        Instant createdAt
    ) {
        Commit {
            if (
                hash == null || hash.isBlank() ||
                message == null || message.isBlank()
            ) {
                throw new ValidationException("Invalid commit.");
            }

            Objects.requireNonNull(createdAt);
        }
    }

    record Review(
        String reviewer,
        ReviewDecision decision,
        boolean eligible,
        boolean stale,
        boolean dismissed
    ) {
        Review {
            if (reviewer == null || reviewer.isBlank()) {
                throw new ValidationException("Reviewer is required.");
            }

            Objects.requireNonNull(decision);
        }

        Review markStale() {
            return new Review(
                reviewer,
                decision,
                eligible,
                true,
                dismissed
            );
        }

        Review dismiss() {
            return new Review(
                reviewer,
                decision,
                eligible,
                stale,
                true
            );
        }
    }

    record EligibilityResult(
        boolean eligible,
        int validApprovals,
        List<String> reasons
    ) {
        EligibilityResult {
            reasons = List.copyOf(reasons);
        }
    }

    // ========================================================
    // BRANCH DOMAIN
    // ========================================================

    static final class Branch {

        private final String name;
        private final boolean protectedBranch;
        private final boolean allowDirectPush;
        private final boolean allowForcePush;
        private final boolean allowDeletion;

        Branch(
            String name,
            boolean protectedBranch,
            boolean allowDirectPush,
            boolean allowForcePush,
            boolean allowDeletion
        ) {
            if (name == null || name.isBlank()) {
                throw new ValidationException("Branch name is required.");
            }

            this.name = name;
            this.protectedBranch = protectedBranch;
            this.allowDirectPush = allowDirectPush;
            this.allowForcePush = allowForcePush;
            this.allowDeletion = allowDeletion;
        }

        String name() {
            return name;
        }

        boolean isProtected() {
            return protectedBranch;
        }

        boolean allowsDirectPush() {
            return allowDirectPush;
        }

        boolean allowsForcePush() {
            return allowForcePush;
        }

        boolean allowsDeletion() {
            return allowDeletion;
        }
    }

    // ========================================================
    // BRANCH PROTECTION POLICY
    // ========================================================

    static final class BranchProtectionPolicy {

        private final int requiredApprovals;
        private final Set<String> requiredChecks;
        private final boolean requireResolvedConversations;
        private final boolean requireLinearHistory;
        private final boolean requireSynchronizedBase;
        private final boolean allowAdministratorBypass;

        BranchProtectionPolicy(
            int requiredApprovals,
            Set<String> requiredChecks,
            boolean requireResolvedConversations,
            boolean requireLinearHistory,
            boolean requireSynchronizedBase,
            boolean allowAdministratorBypass
        ) {
            if (requiredApprovals < 0) {
                throw new ValidationException(
                    "Approval count cannot be negative."
                );
            }

            this.requiredApprovals = requiredApprovals;
            this.requiredChecks = Set.copyOf(requiredChecks);
            this.requireResolvedConversations =
                requireResolvedConversations;
            this.requireLinearHistory = requireLinearHistory;
            this.requireSynchronizedBase = requireSynchronizedBase;
            this.allowAdministratorBypass =
                allowAdministratorBypass;
        }
    }

    // ========================================================
    // PULL REQUEST AGGREGATE
    // ========================================================

    static final class PullRequest {

        private final String id;
        private final Branch source;
        private final Branch target;

        private final List<Commit> commits = new ArrayList<>();
        private final Map<String, Review> reviews = new HashMap<>();
        private final Map<String, CheckStatus> checks = new HashMap<>();
        private final Set<String> unresolvedConversations = new HashSet<>();

        private PullRequestState state = PullRequestState.DRAFT;
        private boolean baseSynchronized = true;
        private boolean linearHistory = true;

        PullRequest(
            String id,
            Branch source,
            Branch target
        ) {
            if (id == null || id.isBlank()) {
                throw new ValidationException("Request ID is required.");
            }

            Objects.requireNonNull(source);
            Objects.requireNonNull(target);

            if (source.name().equals(target.name())) {
                throw new ValidationException(
                    "Source and target must differ."
                );
            }

            this.id = id;
            this.source = source;
            this.target = target;
        }

        void addCommit(Commit commit) {
            ensureModifiable();

            boolean duplicate = commits.stream().anyMatch(
                existing -> existing.hash().equals(commit.hash())
            );

            if (duplicate) {
                throw new ValidationException("Duplicate commit.");
            }

            commits.add(commit);

            reviews.replaceAll(
                (name, review) ->
                    review.decision() == ReviewDecision.APPROVED
                        ? review.markStale()
                        : review
            );
        }

        void open() {
            if (state != PullRequestState.DRAFT || commits.isEmpty()) {
                throw new WorkflowException(
                    "A draft with commits is required."
                );
            }

            state = PullRequestState.OPEN;
        }

        void close() {
            if (
                state != PullRequestState.OPEN &&
                state != PullRequestState.DRAFT
            ) {
                throw new WorkflowException("Cannot close request.");
            }

            state = PullRequestState.CLOSED;
        }

        void reopen() {
            if (state != PullRequestState.CLOSED) {
                throw new WorkflowException("Request is not closed.");
            }

            state = PullRequestState.OPEN;
        }

        void synchronizeBase() {
            if (state != PullRequestState.OPEN) {
                throw new WorkflowException("Request must be open.");
            }

            baseSynchronized = true;

            reviews.replaceAll(
                (name, review) ->
                    review.decision() == ReviewDecision.APPROVED
                        ? review.markStale()
                        : review
            );
        }

        void markBaseOutdated() {
            baseSynchronized = false;
        }

        void setLinearHistory(boolean value) {
            linearHistory = value;
        }

        void requestReview(String reviewer, boolean eligible) {
            if (state != PullRequestState.OPEN) {
                throw new WorkflowException("Request must be open.");
            }

            if (!eligible) {
                throw new PolicyException("Reviewer is not eligible.");
            }

            if (reviewer == null || reviewer.isBlank()) {
                throw new ValidationException("Reviewer is required.");
            }

            reviews.put(
                reviewer,
                new Review(
                    reviewer,
                    ReviewDecision.COMMENTED,
                    true,
                    false,
                    false
                )
            );
        }

        void submitReview(
            String reviewer,
            ReviewDecision decision
        ) {
            Review existing = reviews.get(reviewer);

            if (existing == null) {
                throw new PolicyException(
                    "Reviewer was not requested."
                );
            }

            reviews.put(
                reviewer,
                new Review(
                    reviewer,
                    decision,
                    existing.eligible(),
                    false,
                    false
                )
            );
        }

        void dismissReview(String reviewer) {
            Review review = reviews.get(reviewer);

            if (review == null) {
                throw new ValidationException("Review does not exist.");
            }

            reviews.put(reviewer, review.dismiss());
        }

        void updateCheck(String name, CheckStatus status) {
            if (name == null || name.isBlank()) {
                throw new ValidationException("Check name is required.");
            }

            checks.put(name, Objects.requireNonNull(status));
        }

        void addConversation(String id) {
            if (id == null || id.isBlank()) {
                throw new ValidationException("Conversation ID required.");
            }

            unresolvedConversations.add(id);
        }

        void resolveConversation(String id) {
            if (!unresolvedConversations.remove(id)) {
                throw new ValidationException(
                    "Unknown review conversation."
                );
            }
        }

        int validApprovals() {
            return (int) reviews.values().stream()
                .filter(Review::eligible)
                .filter(review -> !review.stale())
                .filter(review -> !review.dismissed())
                .filter(
                    review -> review.decision() == ReviewDecision.APPROVED
                )
                .count();
        }

        boolean hasRequestedChanges() {
            return reviews.values().stream()
                .filter(Review::eligible)
                .filter(review -> !review.stale())
                .filter(review -> !review.dismissed())
                .anyMatch(
                    review ->
                        review.decision() ==
                        ReviewDecision.CHANGES_REQUESTED
                );
        }

        Map<String, CheckStatus> checks() {
            return Collections.unmodifiableMap(checks);
        }

        Set<String> conversations() {
            return Collections.unmodifiableSet(
                unresolvedConversations
            );
        }

        PullRequestState state() {
            return state;
        }

        Branch target() {
            return target;
        }

        boolean baseSynchronized() {
            return baseSynchronized;
        }

        boolean linearHistory() {
            return linearHistory;
        }

        int commitCount() {
            return commits.size();
        }

        void markMerged() {
            state = PullRequestState.MERGED;
        }

        private void ensureModifiable() {
            if (
                state == PullRequestState.CLOSED ||
                state == PullRequestState.MERGED
            ) {
                throw new WorkflowException(
                    "Closed or merged request cannot change."
                );
            }
        }
    }

    // ========================================================
    // ENTERPRISE MERGE ELIGIBILITY SERVICE
    // ========================================================

    static final class MergeEligibilityService {

        EligibilityResult evaluate(
            PullRequest request,
            BranchProtectionPolicy policy,
            boolean administrator
        ) {
            List<String> reasons = new ArrayList<>();

            int approvals = request.validApprovals();

            if (request.state() != PullRequestState.OPEN) {
                reasons.add("Request must be open.");
            }

            if (!request.target().isProtected()) {
                reasons.add("Target branch is not protected.");
            }

            if (request.commitCount() == 0) {
                reasons.add("No commits exist.");
            }

            if (approvals < policy.requiredApprovals) {
                reasons.add("Insufficient valid approvals.");
            }

            if (request.hasRequestedChanges()) {
                reasons.add("Review changes are still requested.");
            }

            policy.requiredChecks.forEach(check -> {
                if (
                    request.checks().get(check) != CheckStatus.PASSED
                ) {
                    reasons.add("Required check missing or failed: " + check);
                }
            });

            if (
                policy.requireResolvedConversations &&
                !request.conversations().isEmpty()
            ) {
                reasons.add("Unresolved conversations exist.");
            }

            if (
                policy.requireSynchronizedBase &&
                !request.baseSynchronized()
            ) {
                reasons.add("Base branch is outdated.");
            }

            if (
                policy.requireLinearHistory &&
                !request.linearHistory()
            ) {
                reasons.add("Linear history is required.");
            }

            boolean bypass =
                administrator && policy.allowAdministratorBypass;

            boolean eligible = reasons.isEmpty() || bypass;

            if (bypass && eligible) {
                reasons.clear();
                reasons.add("Authorized administrator bypass.");
            }

            return new EligibilityResult(
                eligible,
                approvals,
                reasons
            );
        }

        void merge(
            PullRequest request,
            BranchProtectionPolicy policy,
            MergeStrategy strategy,
            boolean administrator
        ) {
            EligibilityResult result = evaluate(
                request,
                policy,
                administrator
            );

            if (!result.eligible()) {
                throw new PolicyException(
                    String.join("; ", result.reasons())
                );
            }

            if (
                strategy == MergeStrategy.REBASE &&
                policy.requireLinearHistory &&
                !request.linearHistory()
            ) {
                throw new PolicyException(
                    "Rebase cannot satisfy the configured history policy."
                );
            }

            request.markMerged();
        }
    }

    // ========================================================
    // TEST-DRIVEN DEVELOPMENT TRACKER
    // ========================================================

    static final class TddCycle {

        private TddStage stage = TddStage.RED;
        private final List<String> history = new ArrayList<>();
        private int implementationVersion;

        void transition(
            TddStage next,
            boolean testsPassed,
            boolean behaviorPreserved
        ) {
            boolean valid = switch (stage) {
                case RED ->
                    next == TddStage.GREEN;
                case GREEN ->
                    next == TddStage.REFACTOR;
                case REFACTOR ->
                    next == TddStage.RED ||
                    next == TddStage.GREEN;
            };

            if (!valid) {
                throw new WorkflowException(
                    "Invalid TDD stage transition."
                );
            }

            if (
                (next == TddStage.GREEN ||
                 next == TddStage.REFACTOR) &&
                !testsPassed
            ) {
                throw new WorkflowException(
                    "Passing tests are required."
                );
            }

            if (
                next == TddStage.REFACTOR &&
                !behaviorPreserved
            ) {
                throw new WorkflowException(
                    "Refactoring must preserve behavior."
                );
            }

            stage = next;

            if (next == TddStage.REFACTOR) {
                implementationVersion++;
            }

            history.add(
                Instant.now() + " " + stage
            );
        }
    }

    // ========================================================
    // LIGHTWEIGHT TEST FRAMEWORK
    // ========================================================

    record TestResult(
        String name,
        boolean passed,
        String message
    ) {}

    static final class TestRunner {

        private final Map<String, Runnable> tests =
            new HashMap<>();

        private final List<TestResult> results =
            new ArrayList<>();

        void register(String name, Runnable test) {
            if (
                name == null || name.isBlank() ||
                test == null
            ) {
                throw new ValidationException("Invalid test.");
            }

            if (tests.putIfAbsent(name, test) != null) {
                throw new ValidationException("Duplicate test: " + name);
            }
        }

        void run() {
            results.clear();

            tests.forEach((name, test) -> {
                try {
                    test.run();

                    results.add(
                        new TestResult(name, true, "")
                    );

                } catch (Throwable error) {
                    results.add(
                        new TestResult(
                            name,
                            false,
                            error.getMessage()
                        )
                    );
                }
            });
        }

        long passed() {
            return results.stream()
                .filter(TestResult::passed)
                .count();
        }

        long failed() {
            return results.size() - passed();
        }

        void printReport() {
            results.forEach(result -> {
                System.out.printf(
                    "[%s] %s%s%n",
                    result.passed() ? "PASS" : "FAIL",
                    result.name(),
                    result.passed() ? "" : " : " + result.message()
                );
            });

            System.out.println(
                "Passed: " + passed() +
                " | Failed: " + failed() +
                " | Total: " + results.size()
            );
        }
    }

    // ========================================================
    // ASSERTION HELPERS
    // ========================================================

    static void check(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    static void expectException(
        Class<? extends Throwable> expected,
        Runnable operation
    ) {
        try {
            operation.run();
        } catch (Throwable error) {
            if (expected.isInstance(error)) {
                return;
            }

            throw new AssertionError(
                "Unexpected exception: " + error.getClass().getName()
            );
        }

        throw new AssertionError("Expected exception was not thrown.");
    }

    // ========================================================
    // TEST EXECUTION
    // ========================================================

    public static void main(String[] args) {

        TestRunner runner = new TestRunner();

        Branch main = new Branch(
            "main",
            true,
            false,
            false,
            false
        );

        runner.register("valid pull request", () -> {
            Branch feature = new Branch(
                "feature/auth",
                false,
                true,
                true,
                true
            );

            PullRequest request = new PullRequest(
                "PR-201",
                feature,
                main
            );

            request.addCommit(
                new Commit(
                    "a1",
                    "Add authentication",
                    Instant.now()
                )
            );

            request.open();

            check(
                request.state() == PullRequestState.OPEN,
                "Request should be open."
            );
        });

        runner.register("identical branches rejected", () -> {
            expectException(
                ValidationException.class,
                () -> new PullRequest(
                    "PR-202",
                    main,
                    main
                )
            );
        });

        runner.register("valid approval counted", () -> {
            Branch feature = new Branch(
                "feature/api",
                false,
                true,
                true,
                true
            );

            PullRequest request = new PullRequest(
                "PR-203",
                feature,
                main
            );

            request.addCommit(
                new Commit("b1", "Add API", Instant.now())
            );

            request.open();
            request.requestReview("reviewer-1", true);

            request.submitReview(
                "reviewer-1",
                ReviewDecision.APPROVED
            );

            check(
                request.validApprovals() == 1,
                "Expected one approval."
            );
        });

        runner.register("new commit makes approval stale", () -> {
            Branch feature = new Branch(
                "feature/cache",
                false,
                true,
                true,
                true
            );

            PullRequest request = new PullRequest(
                "PR-204",
                feature,
                main
            );

            request.addCommit(
                new Commit("c1", "Add cache", Instant.now())
            );

            request.open();
            request.requestReview("reviewer-1", true);

            request.submitReview(
                "reviewer-1",
                ReviewDecision.APPROVED
            );

            request.addCommit(
                new Commit("c2", "Fix cache", Instant.now())
            );

            check(
                request.validApprovals() == 0,
                "Stale approval must not count."
            );
        });

        runner.register("merge requires all conditions", () -> {
            Branch feature = new Branch(
                "feature/payment",
                false,
                true,
                true,
                true
            );

            PullRequest request = new PullRequest(
                "PR-205",
                feature,
                main
            );

            request.addCommit(
                new Commit("d1", "Add payments", Instant.now())
            );

            request.open();
            request.requestReview("reviewer-1", true);

            request.submitReview(
                "reviewer-1",
                ReviewDecision.APPROVED
            );

            request.updateCheck(
                "unit-tests",
                CheckStatus.PASSED
            );

            request.updateCheck(
                "integration-tests",
                CheckStatus.PASSED
            );

            BranchProtectionPolicy policy =
                new BranchProtectionPolicy(
                    1,
                    Set.of("unit-tests", "integration-tests"),
                    true,
                    true,
                    true,
                    false
                );

            MergeEligibilityService service =
                new MergeEligibilityService();

            EligibilityResult result = service.evaluate(
                request,
                policy,
                false
            );

            check(result.eligible(), "Merge should be eligible.");

            service.merge(
                request,
                policy,
                MergeStrategy.SQUASH,
                false
            );

            check(
                request.state() == PullRequestState.MERGED,
                "Request should be merged."
            );
        });

        runner.register("unresolved conversation blocks merge", () -> {
            Branch feature = new Branch(
                "feature/report",
                false,
                true,
                true,
                true
            );

            PullRequest request = new PullRequest(
                "PR-206",
                feature,
                main
            );

            request.addCommit(
                new Commit("e1", "Add reporting", Instant.now())
            );

            request.open();
            request.requestReview("reviewer-1", true);

            request.submitReview(
                "reviewer-1",
                ReviewDecision.APPROVED
            );

            request.addConversation("thread-1");

            BranchProtectionPolicy policy =
                new BranchProtectionPolicy(
                    1,
                    Set.of(),
                    true,
                    false,
                    true,
                    false
                );

            EligibilityResult result =
                new MergeEligibilityService().evaluate(
                    request,
                    policy,
                    false
                );

            check(!result.eligible(), "Conversation must block merge.");
        });

        runner.register("TDD transition enforcement", () -> {
            TddCycle cycle = new TddCycle();

            expectException(
                WorkflowException.class,
                () -> cycle.transition(
                    TddStage.REFACTOR,
                    true,
                    true
                )
            );

            cycle.transition(TddStage.GREEN, true, false);
            cycle.transition(TddStage.REFACTOR, true, true);
        });

        runner.register("reviewer eligibility enforcement", () -> {
            Branch feature = new Branch(
                "feature/security",
                false,
                true,
                true,
                true
            );

            PullRequest request = new PullRequest(
                "PR-207",
                feature,
                main
            );

            request.addCommit(
                new Commit("f1", "Add security validation", Instant.now())
            );

            request.open();

            expectException(
                PolicyException.class,
                () -> request.requestReview("external-user", false)
            );
        });

        runner.run();
        runner.printReport();

        TddCycle cycle = new TddCycle();

        cycle.transition(TddStage.GREEN, true, false);
        cycle.transition(TddStage.REFACTOR, true, true);

        System.out.println("\nTDD STAGE HISTORY");

        cycle.history.forEach(System.out::println);

        if (runner.failed() > 0) {
            System.exit(1);
        }

        System.out.println("\nAll enterprise governance tests passed.");
    }
}
