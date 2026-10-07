import java.util.ArrayList;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

/**
 * Design Patterns II: Strategy, Observer, Adapter.
 *
 * Enterprise-oriented repository governance model.
 *
 * Strategy:
 *   MergeStrategy implementations represent different repository policies.
 *
 * Observer:
 *   RepositoryEventBus publishes lifecycle events to independent observers.
 *
 * Adapter:
 *   ExternalCiAdapter converts an external CI model into the application's
 *   internal StatusProvider contract.
 *
 * Java 17+.
 */
public class DesignPatternsII {

    // -------------------------------------------------------------------------
    // Domain enums
    // -------------------------------------------------------------------------

    enum PullRequestState {
        DRAFT,
        OPEN,
        MERGED,
        CLOSED
    }

    enum ReviewDecision {
        APPROVE,
        REQUEST_CHANGES,
        COMMENT
    }

    enum CheckStatus {
        PASSING,
        FAILING,
        PENDING
    }

    enum EventType {
        OPENED,
        REVIEW_REQUESTED,
        REVIEW_SUBMITTED,
        CHANGES_REQUESTED,
        STATUS_UPDATED,
        MERGED
    }

    // -------------------------------------------------------------------------
    // Immutable domain records
    // -------------------------------------------------------------------------

    record Commit(String sha, String message) {
        Commit {
            if (sha == null || sha.isBlank()) {
                throw new IllegalArgumentException("Commit SHA is required.");
            }
            if (message == null || message.isBlank()) {
                throw new IllegalArgumentException("Commit message is required.");
            }
        }
    }

    record Review(
        String reviewer,
        ReviewDecision decision,
        String commitSha,
        String comment
    ) {
        Review {
            Objects.requireNonNull(reviewer);
            Objects.requireNonNull(decision);
            Objects.requireNonNull(commitSha);
            comment = comment == null ? "" : comment;
        }
    }

    record StatusCheck(
        String name,
        CheckStatus status,
        String commitSha
    ) {
        StatusCheck {
            Objects.requireNonNull(name);
            Objects.requireNonNull(status);
            Objects.requireNonNull(commitSha);
        }
    }

    record RepositoryEvent(
        EventType type,
        int pullRequestNumber,
        String actor,
        String message
    ) {
        RepositoryEvent {
            Objects.requireNonNull(type);
            Objects.requireNonNull(actor);
            Objects.requireNonNull(message);
        }
    }

    record MergeDecision(
        boolean allowed,
        List<String> reasons
    ) {
        MergeDecision {
            reasons = List.copyOf(reasons);
        }
    }

    // -------------------------------------------------------------------------
    // Pull Request aggregate
    // -------------------------------------------------------------------------

    static final class PullRequest {
        private final int number;
        private final String title;
        private final String author;
        private final String sourceBranch;
        private final String targetBranch;
        private final List<Commit> commits;
        private final List<Review> reviews = new ArrayList<>();
        private final List<StatusCheck> checks = new ArrayList<>();

        private PullRequestState state = PullRequestState.OPEN;
        private boolean mergeable = true;

        PullRequest(
            int number,
            String title,
            String author,
            String sourceBranch,
            String targetBranch,
            List<Commit> commits
        ) {
            if (number <= 0) {
                throw new IllegalArgumentException(
                    "Pull Request number must be positive."
                );
            }

            if (commits == null || commits.isEmpty()) {
                throw new IllegalArgumentException(
                    "Pull Request must contain a commit."
                );
            }

            this.number = number;
            this.title = Objects.requireNonNull(title);
            this.author = Objects.requireNonNull(author);
            this.sourceBranch = Objects.requireNonNull(sourceBranch);
            this.targetBranch = Objects.requireNonNull(targetBranch);
            this.commits = new ArrayList<>(commits);
        }

        int number() {
            return number;
        }

        String headSha() {
            return commits.get(commits.size() - 1).sha();
        }

        PullRequestState state() {
            return state;
        }

        List<Review> reviews() {
            return List.copyOf(reviews);
        }

        List<StatusCheck> checks() {
            return List.copyOf(checks);
        }

        boolean mergeable() {
            return mergeable;
        }

        void setMergeable(boolean mergeable) {
            this.mergeable = mergeable;
        }

        void addReview(Review review) {
            if (state == PullRequestState.MERGED ||
                state == PullRequestState.CLOSED) {
                throw new IllegalStateException(
                    "A closed or merged Pull Request cannot receive reviews."
                );
            }

            if (!review.commitSha().equals(headSha())) {
                throw new IllegalArgumentException(
                    "Review must target the current commit."
                );
            }

            reviews.add(review);
        }

        void addCheck(StatusCheck check) {
            if (!check.commitSha().equals(headSha())) {
                throw new IllegalArgumentException(
                    "Status check must target the current commit."
                );
            }

            checks.add(check);
        }

        void merge() {
            if (state != PullRequestState.OPEN) {
                throw new IllegalStateException(
                    "Only an open Pull Request can be merged."
                );
            }

            state = PullRequestState.MERGED;
        }
    }

    // -------------------------------------------------------------------------
    // Strategy pattern
    // -------------------------------------------------------------------------

    interface MergeStrategy {
        MergeDecision evaluate(PullRequest pullRequest);
    }

    static final class DevelopmentBranchStrategy
        implements MergeStrategy {

        @Override
        public MergeDecision evaluate(PullRequest pullRequest) {
            List<String> reasons = new ArrayList<>();

            if (pullRequest.state() != PullRequestState.OPEN) {
                reasons.add("Pull Request is not open.");
            }

            List<StatusCheck> currentChecks = pullRequest.checks()
                .stream()
                .filter(
                    check -> check.commitSha().equals(pullRequest.headSha())
                )
                .toList();

            if (currentChecks.isEmpty()) {
                reasons.add("No status checks exist for the current commit.");
            }

            currentChecks.stream()
                .filter(check -> check.status() != CheckStatus.PASSING)
                .forEach(
                    check -> reasons.add(
                        check.name() + " is " + check.status()
                    )
                );

            boolean changesRequested = pullRequest.reviews()
                .stream()
                .anyMatch(
                    review ->
                        review.commitSha().equals(pullRequest.headSha()) &&
                        review.decision() == ReviewDecision.REQUEST_CHANGES
                );

            if (changesRequested) {
                reasons.add(
                    "The current commit has a change request."
                );
            }

            if (!pullRequest.mergeable()) {
                reasons.add("Pull Request contains unresolved conflicts.");
            }

            return new MergeDecision(reasons.isEmpty(), reasons);
        }
    }

    static final class ProductionBranchStrategy
        implements MergeStrategy {

        private final Set<String> eligibleReviewers;
        private final int requiredApprovals;

        ProductionBranchStrategy(
            Set<String> eligibleReviewers,
            int requiredApprovals
        ) {
            if (requiredApprovals < 1) {
                throw new IllegalArgumentException(
                    "At least one approval is required."
                );
            }

            this.eligibleReviewers = Set.copyOf(eligibleReviewers);
            this.requiredApprovals = requiredApprovals;
        }

        @Override
        public MergeDecision evaluate(PullRequest pullRequest) {
            List<String> reasons = new ArrayList<>();

            if (pullRequest.state() != PullRequestState.OPEN) {
                reasons.add("Pull Request is not open.");
            }

            Set<String> approvals = new HashSet<>();

            for (Review review : pullRequest.reviews()) {
                if (review.commitSha().equals(pullRequest.headSha()) &&
                    review.decision() == ReviewDecision.APPROVE &&
                    eligibleReviewers.contains(review.reviewer())) {
                    approvals.add(review.reviewer());
                }

                if (review.commitSha().equals(pullRequest.headSha()) &&
                    review.decision() == ReviewDecision.REQUEST_CHANGES) {
                    reasons.add(
                        "The current commit has a change request."
                    );
                }
            }

            if (approvals.size() < requiredApprovals) {
                reasons.add(
                    requiredApprovals +
                    " eligible approvals required; " +
                    approvals.size() +
                    " available."
                );
            }

            List<StatusCheck> currentChecks = pullRequest.checks()
                .stream()
                .filter(
                    check -> check.commitSha().equals(pullRequest.headSha())
                )
                .toList();

            if (currentChecks.isEmpty()) {
                reasons.add(
                    "No status checks exist for the current commit."
                );
            }

            currentChecks.stream()
                .filter(check -> check.status() != CheckStatus.PASSING)
                .forEach(
                    check -> reasons.add(
                        check.name() +
                        " is " +
                        check.status()
                    )
                );

            if (!pullRequest.mergeable()) {
                reasons.add("Pull Request contains unresolved conflicts.");
            }

            return new MergeDecision(reasons.isEmpty(), reasons);
        }
    }

    // -------------------------------------------------------------------------
    // Observer pattern
    // -------------------------------------------------------------------------

    interface RepositoryObserver {
        void update(RepositoryEvent event);
    }

    static final class RepositoryEventBus {
        private final List<RepositoryObserver> observers = new ArrayList<>();

        void subscribe(RepositoryObserver observer) {
            observers.add(Objects.requireNonNull(observer));
        }

        void unsubscribe(RepositoryObserver observer) {
            observers.remove(observer);
        }

        void publish(RepositoryEvent event) {
            // Snapshotting prevents an observer from modifying the subscriber
            // collection while it is being traversed.
            List<RepositoryObserver> snapshot = List.copyOf(observers);

            for (RepositoryObserver observer : snapshot) {
                try {
                    observer.update(event);
                } catch (RuntimeException exception) {
                    // An analytics or notification failure must not suppress
                    // unrelated repository observers.
                    System.err.println(
                        "[observer-error] " + exception.getMessage()
                    );
                }
            }
        }
    }

    static final class AuditObserver
        implements RepositoryObserver {

        private final List<String> entries = new ArrayList<>();

        @Override
        public void update(RepositoryEvent event) {
            String entry =
                event.type() +
                ": PR #" +
                event.pullRequestNumber() +
                " by " +
                event.actor() +
                " - " +
                event.message();

            entries.add(entry);
            System.out.println("[audit] " + entry);
        }
    }

    static final class NotificationObserver
        implements RepositoryObserver {

        @Override
        public void update(RepositoryEvent event) {
            if (event.type() == EventType.REVIEW_REQUESTED ||
                event.type() == EventType.CHANGES_REQUESTED) {
                System.out.println(
                    "[notification] " + event.message()
                );
            }
        }
    }

    static final class MetricsObserver
        implements RepositoryObserver {

        private final Map<EventType, Integer> counts =
            new EnumMap<>(EventType.class);

        @Override
        public void update(RepositoryEvent event) {
            counts.merge(event.type(), 1, Integer::sum);
        }

        void print() {
            counts.forEach(
                (type, count) ->
                    System.out.println("  " + type + ": " + count)
            );
        }
    }

    // -------------------------------------------------------------------------
    // Adapter pattern
    // -------------------------------------------------------------------------

    record ExternalBuild(
        String buildId,
        String result,
        String revision
    ) {}

    static final class ExternalCiClient {
        private final Map<String, ExternalBuild> builds = Map.of(
            "abc123",
            new ExternalBuild("build-9001", "SUCCESS", "abc123"),
            "def456",
            new ExternalBuild("build-9002", "FAILURE", "def456")
        );

        ExternalBuild findBuild(String revision) {
            return builds.get(revision);
        }
    }

    interface StatusProvider {
        StatusCheck getStatus(String commitSha);
    }

    static final class ExternalCiAdapter
        implements StatusProvider {

        private final ExternalCiClient client;

        ExternalCiAdapter(ExternalCiClient client) {
            this.client = Objects.requireNonNull(client);
        }

        @Override
        public StatusCheck getStatus(String commitSha) {
            ExternalBuild build = client.findBuild(commitSha);

            if (build == null) {
                // Unknown external state maps to PENDING. Treating it as
                // PASSING would create a fail-open merge condition.
                return new StatusCheck(
                    "external-ci",
                    CheckStatus.PENDING,
                    commitSha
                );
            }

            CheckStatus status = switch (build.result()) {
                case "SUCCESS" -> CheckStatus.PASSING;
                case "FAILURE", "CANCELLED" -> CheckStatus.FAILING;
                default -> CheckStatus.PENDING;
            };

            return new StatusCheck(
                "external-ci/" + build.buildId(),
                status,
                commitSha
            );
        }
    }

    // -------------------------------------------------------------------------
    // Application service
    // -------------------------------------------------------------------------

    static final class RepositoryGovernanceService {
        private final MergeStrategy mergeStrategy;
        private final StatusProvider statusProvider;
        private final RepositoryEventBus eventBus;

        RepositoryGovernanceService(
            MergeStrategy mergeStrategy,
            StatusProvider statusProvider,
            RepositoryEventBus eventBus
        ) {
            this.mergeStrategy = Objects.requireNonNull(mergeStrategy);
            this.statusProvider = Objects.requireNonNull(statusProvider);
            this.eventBus = Objects.requireNonNull(eventBus);
        }

        void requestReview(
            PullRequest pullRequest,
            String actor,
            String reviewer
        ) {
            eventBus.publish(
                new RepositoryEvent(
                    EventType.REVIEW_REQUESTED,
                    pullRequest.number(),
                    actor,
                    "Review requested from " + reviewer + "."
                )
            );
        }

        void synchronizeStatus(
            PullRequest pullRequest,
            String actor
        ) {
            StatusCheck check =
                statusProvider.getStatus(pullRequest.headSha());

            pullRequest.addCheck(check);

            eventBus.publish(
                new RepositoryEvent(
                    EventType.STATUS_UPDATED,
                    pullRequest.number(),
                    actor,
                    check.name() +
                    " is " +
                    check.status()
                )
            );
        }

        MergeDecision evaluate(PullRequest pullRequest) {
            return mergeStrategy.evaluate(pullRequest);
        }

        boolean merge(
            PullRequest pullRequest,
            String actor
        ) {
            MergeDecision decision = evaluate(pullRequest);

            if (!decision.allowed()) {
                System.out.println("[merge] blocked");

                decision.reasons().forEach(
                    reason -> System.out.println("  - " + reason)
                );

                return false;
            }

            pullRequest.merge();

            eventBus.publish(
                new RepositoryEvent(
                    EventType.MERGED,
                    pullRequest.number(),
                    actor,
                    "Pull Request merged."
                )
            );

            return true;
        }
    }

    // -------------------------------------------------------------------------
    // Executable scenario
    // -------------------------------------------------------------------------

    public static void main(String[] args) {
        System.out.println("=== Strategy ===");

        PullRequest pullRequest = new PullRequest(
            42,
            "Harden payment authorization",
            "alice",
            "feature/payment-auth",
            "main",
            List.of(
                new Commit(
                    "abc123",
                    "Implement payment authorization"
                )
            )
        );

        DevelopmentBranchStrategy developmentStrategy =
            new DevelopmentBranchStrategy();

        ProductionBranchStrategy productionStrategy =
            new ProductionBranchStrategy(
                Set.of("bob", "carol", "david"),
                2
            );

        pullRequest.addCheck(
            new StatusCheck(
                "unit-tests",
                CheckStatus.PASSING,
                pullRequest.headSha()
            )
        );

        pullRequest.addReview(
            new Review(
                "bob",
                ReviewDecision.APPROVE,
                pullRequest.headSha(),
                "Authorization boundary is clear."
            )
        );

        System.out.println(
            "Development policy: " +
            developmentStrategy.evaluate(pullRequest)
        );

        System.out.println(
            "Production policy: " +
            productionStrategy.evaluate(pullRequest)
        );

        System.out.println("\n=== Observer + Adapter ===");

        RepositoryEventBus eventBus =
            new RepositoryEventBus();

        AuditObserver audit = new AuditObserver();
        NotificationObserver notifications =
            new NotificationObserver();
        MetricsObserver metrics = new MetricsObserver();

        eventBus.subscribe(audit);
        eventBus.subscribe(notifications);
        eventBus.subscribe(metrics);

        ExternalCiClient externalCi =
            new ExternalCiClient();

        ExternalCiAdapter adapter =
            new ExternalCiAdapter(externalCi);

        RepositoryGovernanceService service =
            new RepositoryGovernanceService(
                developmentStrategy,
                adapter,
                eventBus
            );

        service.requestReview(
            pullRequest,
            "alice",
            "carol"
        );

        service.synchronizeStatus(
            pullRequest,
            "ci-bot"
        );

        MergeDecision decision =
            service.evaluate(pullRequest);

        System.out.println(
            "Merge eligibility: " + decision.allowed()
        );

        service.merge(
            pullRequest,
            "release-bot"
        );

        System.out.println("\nMetrics:");
        metrics.print();

        System.out.println("\nUnknown external revision:");

        StatusCheck unknown =
            adapter.getStatus("unknown-sha");

        System.out.println(
            unknown.name() +
            " -> " +
            unknown.status()
        );
    }
}
