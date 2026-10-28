import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

public class CacheGovernanceDemo {

    enum ReviewDecision {
        COMMENTED,
        APPROVED,
        CHANGES_REQUESTED,
        DISMISSED
    }

    enum PullRequestState {
        DRAFT,
        OPEN,
        CLOSED,
        MERGED
    }

    enum CheckStatus {
        PENDING,
        PASSED,
        FAILED
    }

    record Commit(String sha, String message) {
        Commit {
            if (sha == null || sha.isBlank()) {
                throw new IllegalArgumentException("Commit SHA is required");
            }
            if (message == null || message.isBlank()) {
                throw new IllegalArgumentException("Commit message is required");
            }
        }
    }

    record Review(
            String reviewer,
            ReviewDecision decision,
            boolean stale
    ) {
        Review {
            if (reviewer == null || reviewer.isBlank()) {
                throw new IllegalArgumentException("Reviewer is required");
            }
            Objects.requireNonNull(decision, "Review decision is required");
        }
    }

    record StatusCheck(String name, CheckStatus status) {
        StatusCheck {
            if (name == null || name.isBlank()) {
                throw new IllegalArgumentException("Check name is required");
            }
            Objects.requireNonNull(status, "Check status is required");
        }
    }

    record BranchProtectionPolicy(
            int requiredApprovals,
            boolean requireSuccessfulChecks,
            boolean requireResolvedConversations,
            boolean preventForcePush,
            boolean preventDirectPush
    ) {
        BranchProtectionPolicy {
            if (requiredApprovals < 0) {
                throw new IllegalArgumentException(
                        "Required approvals cannot be negative");
            }
        }
    }

    static final class PullRequest {
        private final int id;
        private final String sourceBranch;
        private final String targetBranch;
        private final List<Commit> commits;
        private final List<Review> reviews = new ArrayList<>();
        private final List<StatusCheck> checks = new ArrayList<>();

        private PullRequestState state;
        private int unresolvedConversations;
        private boolean sourceSynchronized;

        PullRequest(
                int id,
                String sourceBranch,
                String targetBranch,
                List<Commit> commits,
                PullRequestState state,
                boolean sourceSynchronized
        ) {
            if (id <= 0) {
                throw new IllegalArgumentException("Invalid Pull Request ID");
            }
            if (sourceBranch == null || sourceBranch.isBlank()
                    || targetBranch == null || targetBranch.isBlank()) {
                throw new IllegalArgumentException(
                        "Source and target branches are required");
            }

            this.id = id;
            this.sourceBranch = sourceBranch;
            this.targetBranch = targetBranch;
            this.commits = List.copyOf(commits);
            this.state = Objects.requireNonNull(state);
            this.sourceSynchronized = sourceSynchronized;
        }

        void addReview(Review review) {
            reviews.add(Objects.requireNonNull(review));
        }

        void addCheck(StatusCheck check) {
            checks.add(Objects.requireNonNull(check));
        }

        void setUnresolvedConversations(int count) {
            if (count < 0) {
                throw new IllegalArgumentException(
                        "Conversation count cannot be negative");
            }
            unresolvedConversations = count;
        }

        void synchronizeSourceBranch() {
            sourceSynchronized = true;
        }

        int id() {
            return id;
        }

        String targetBranch() {
            return targetBranch;
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

        int unresolvedConversations() {
            return unresolvedConversations;
        }

        boolean sourceSynchronized() {
            return sourceSynchronized;
        }

        void merge() {
            if (state != PullRequestState.OPEN) {
                throw new IllegalStateException(
                        "Only open Pull Requests can transition to merged");
            }
            state = PullRequestState.MERGED;
        }
    }

    record MergeDecision(boolean eligible, List<String> reasons) {
        MergeDecision {
            reasons = List.copyOf(reasons);
        }
    }

    static final class MergeEligibilityService {
        private final Map<String, BranchProtectionPolicy> policies =
                new HashMap<>();

        void registerPolicy(
                String branch,
                BranchProtectionPolicy policy
        ) {
            if (branch == null || branch.isBlank()) {
                throw new IllegalArgumentException(
                        "Protected branch is required");
            }
            policies.put(branch, Objects.requireNonNull(policy));
        }

        MergeDecision evaluate(PullRequest pr) {
            List<String> reasons = new ArrayList<>();

            if (pr.state() != PullRequestState.OPEN) {
                reasons.add("Pull Request is not open");
            }

            if (pr.reviews().isEmpty()) {
                reasons.add("No reviews have been submitted");
            }

            if (pr.sourceSynchronized() == false) {
                reasons.add("Source branch is not synchronized");
            }

            BranchProtectionPolicy policy =
                    policies.get(pr.targetBranch());

            if (policy == null) {
                reasons.add("Target branch is not governed by a policy");
                return new MergeDecision(false, reasons);
            }

            if (pr.unresolvedConversations()
                    > 0 && policy.requireResolvedConversations()) {
                reasons.add("Review conversations remain unresolved");
            }

            Set<String> approvingReviewers = new HashSet<>();

            for (Review review : pr.reviews()) {
                if (!review.stale()
                        && review.decision() == ReviewDecision.APPROVED) {
                    approvingReviewers.add(review.reviewer());
                }
            }

            if (approvingReviewers.size()
                    < policy.requiredApprovals()) {
                reasons.add(
                        "Required non-stale approvals are missing");
            }

            if (policy.requireSuccessfulChecks()) {
                if (pr.checks().isEmpty()) {
                    reasons.add("No required status checks exist");
                } else {
                    boolean allPassed = pr.checks()
                            .stream()
                            .allMatch(
                                    check -> check.status()
                                            == CheckStatus.PASSED);

                    if (!allPassed) {
                        reasons.add(
                                "One or more required checks have not passed");
                    }
                }
            }

            return new MergeDecision(reasons.isEmpty(), reasons);
        }

        void mergeIfEligible(PullRequest pr) {
            MergeDecision decision = evaluate(pr);

            if (!decision.eligible()) {
                throw new IllegalStateException(
                        "Merge denied: " + String.join(
                                "; ", decision.reasons()));
            }

            pr.merge();
        }
    }

    static final class ExpiringCache<K, V> {
        private record Entry<V>(
                V value,
                Instant expiresAt
        ) {}

        private final Map<K, Entry<V>> entries = new HashMap<>();
        private final Duration ttl;

        ExpiringCache(Duration ttl) {
            if (ttl.isZero() || ttl.isNegative()) {
                throw new IllegalArgumentException(
                        "TTL must be positive");
            }
            this.ttl = ttl;
        }

        synchronized void put(K key, V value) {
            Objects.requireNonNull(key);
            Objects.requireNonNull(value);

            entries.put(
                    key,
                    new Entry<>(value, Instant.now().plus(ttl))
            );
        }

        synchronized V get(K key) {
            Entry<V> entry = entries.get(key);

            if (entry == null) {
                return null;
            }

            if (Instant.now().isAfter(entry.expiresAt())) {
                entries.remove(key);
                return null;
            }

            return entry.value();
        }

        synchronized boolean invalidate(K key) {
            return entries.remove(key) != null;
        }

        synchronized int size() {
            return entries.size();
        }
    }

    public static void main(String[] args) {
        MergeEligibilityService governance =
                new MergeEligibilityService();

        governance.registerPolicy(
                "main",
                new BranchProtectionPolicy(
                        2,
                        true,
                        true,
                        true,
                        true
                )
        );

        PullRequest pr = new PullRequest(
                701,
                "feature/cache-aside",
                "main",
                List.of(
                        new Commit(
                                "a1b2c3",
                                "Implement cache-aside reads"
                        ),
                        new Commit(
                                "d4e5f6",
                                "Add TTL expiration"
                        )
                ),
                PullRequestState.OPEN,
                true
        );

        pr.addReview(
                new Review(
                        "reviewer-1",
                        ReviewDecision.APPROVED,
                        false
                )
        );

        pr.addReview(
                new Review(
                        "reviewer-2",
                        ReviewDecision.APPROVED,
                        false
                )
        );

        pr.addCheck(
                new StatusCheck(
                        "unit-tests",
                        CheckStatus.PASSED
                )
        );

        pr.addCheck(
                new StatusCheck(
                        "integration-tests",
                        CheckStatus.PASSED
                )
        );

        pr.addCheck(
                new StatusCheck(
                        "security-scan",
                        CheckStatus.PASSED
                )
        );

        pr.setUnresolvedConversations(0);

        MergeDecision decision = governance.evaluate(pr);

        System.out.println(
                "PR #" + pr.id()
                        + " eligible: " + decision.eligible()
        );

        if (!decision.eligible()) {
            decision.reasons()
                    .forEach(reason -> System.out.println(
                            "  - " + reason));
        } else {
            governance.mergeIfEligible(pr);
            System.out.println("PR state: " + pr.state());
        }

        PullRequest staleApproval = new PullRequest(
                702,
                "feature/cache-invalidation",
                "main",
                List.of(
                        new Commit(
                                "111aaa",
                                "Invalidate cache after writes"
                        )
                ),
                PullRequestState.OPEN,
                true
        );

        staleApproval.addReview(
                new Review(
                        "reviewer-1",
                        ReviewDecision.APPROVED,
                        true
                )
        );

        staleApproval.addReview(
                new Review(
                        "reviewer-2",
                        ReviewDecision.APPROVED,
                        false
                )
        );

        staleApproval.addCheck(
                new StatusCheck(
                        "unit-tests",
                        CheckStatus.PASSED
                )
        );

        staleApproval.addCheck(
                new StatusCheck(
                        "integration-tests",
                        CheckStatus.PASSED
                )
        );

        MergeDecision staleDecision =
                governance.evaluate(staleApproval);

        System.out.println(
                "PR #" + staleApproval.id()
                        + " eligible: " + staleDecision.eligible()
        );

        staleDecision.reasons()
                .forEach(reason -> System.out.println("  - " + reason));

        ExpiringCache<String, String> cache =
                new ExpiringCache<>(Duration.ofSeconds(1));

        cache.put("user:101", "cached-user");
        System.out.println(
                "Cache value: " + cache.get("user:101"));
        System.out.println(
                "Cache invalidated: "
                        + cache.invalidate("user:101"));
        System.out.println(
                "Cache after invalidation: "
                        + cache.get("user:101"));
    }
}
