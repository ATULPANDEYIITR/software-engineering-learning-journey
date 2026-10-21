import java.util.ArrayList;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

public class RepositoryGovernance {

    enum PullRequestState {
        DRAFT, OPEN, CLOSED, MERGED
    }

    enum ReviewState {
        COMMENTED, APPROVED, CHANGES_REQUESTED, DISMISSED
    }

    enum MergeStrategy {
        MERGE_COMMIT, SQUASH, REBASE
    }

    enum CheckState {
        PENDING, PASSED, FAILED
    }

    record Commit(String sha, String message, String author) {
        Commit {
            requireText(sha, "Commit SHA");
            requireText(message, "Commit message");
            requireText(author, "Commit author");
        }
    }

    record Review(
        String reviewer,
        ReviewState state,
        String commitSha,
        List<String> comments
    ) {
        Review {
            requireText(reviewer, "Reviewer");
            Objects.requireNonNull(state, "Review state");
            requireText(commitSha, "Review commit SHA");
            comments = List.copyOf(comments == null ? List.of() : comments);
        }
    }

    record StatusCheck(String name, CheckState state) {
        StatusCheck {
            requireText(name, "Status check name");
            Objects.requireNonNull(state, "Status check state");
        }
    }

    record BranchProtectionPolicy(
        String branch,
        int requiredApprovals,
        Set<String> requiredChecks,
        boolean requireConversationResolution,
        boolean requireLinearHistory,
        boolean allowDirectPush,
        boolean allowForcePush,
        boolean allowDeletion,
        Set<String> bypassUsers
    ) {
        BranchProtectionPolicy {
            requireText(branch, "Protected branch");

            if (requiredApprovals < 0) {
                throw new IllegalArgumentException(
                    "Required approvals cannot be negative."
                );
            }

            requiredChecks = Set.copyOf(requiredChecks);
            bypassUsers = Set.copyOf(bypassUsers);
        }
    }

    record GovernanceResult(
        boolean eligible,
        List<String> failures,
        boolean bypassed
    ) {
        static GovernanceResult allowed() {
            return new GovernanceResult(true, List.of(), false);
        }
    }

    static final class PullRequest {
        private final int number;
        private final String sourceBranch;
        private final String targetBranch;
        private final String author;
        private final String title;

        private PullRequestState state = PullRequestState.DRAFT;
        private final List<Commit> commits = new ArrayList<>();
        private final Set<String> reviewers = new HashSet<>();
        private final List<Review> reviews = new ArrayList<>();
        private final Map<String, StatusCheck> checks = new HashMap<>();
        private final Map<Integer, Boolean> conversations = new HashMap<>();
        private MergeStrategy mergeStrategy;

        PullRequest(
            int number,
            String sourceBranch,
            String targetBranch,
            String author,
            String title
        ) {
            if (number <= 0) {
                throw new IllegalArgumentException("PR number must be positive.");
            }

            this.number = number;
            this.sourceBranch = requireText(sourceBranch, "Source branch");
            this.targetBranch = requireText(targetBranch, "Target branch");
            this.author = requireText(author, "Author");
            this.title = requireText(title, "Title");
        }

        void addCommit(Commit commit) {
            if (state == PullRequestState.CLOSED ||
                state == PullRequestState.MERGED) {
                throw new IllegalStateException(
                    "Closed and merged Pull Requests cannot be modified."
                );
            }

            if (commits.stream().anyMatch(
                existing -> existing.sha().equals(commit.sha())
            )) {
                throw new IllegalArgumentException(
                    "Commit SHA already exists in the Pull Request."
                );
            }

            commits.add(commit);
        }

        void requestReview(String reviewer) {
            requireText(reviewer, "Reviewer");

            if (reviewer.equals(author)) {
                throw new IllegalArgumentException(
                    "The author cannot act as their own reviewer."
                );
            }

            reviewers.add(reviewer);
        }

        void addReview(
            String reviewer,
            ReviewState state,
            String commitSha,
            List<String> comments
        ) {
            if (!reviewers.contains(reviewer)) {
                throw new IllegalArgumentException(
                    "Reviewer has not been requested."
                );
            }

            if (commits.stream().noneMatch(
                commit -> commit.sha().equals(commitSha)
            )) {
                throw new IllegalArgumentException(
                    "Review references an unknown commit."
                );
            }

            reviews.add(new Review(reviewer, state, commitSha, comments));
        }

        void setStatusCheck(String name, CheckState state) {
            checks.put(name, new StatusCheck(name, state));
        }

        void setConversation(int commentId, boolean resolved) {
            if (commentId <= 0) {
                throw new IllegalArgumentException(
                    "Conversation ID must be positive."
                );
            }
            conversations.put(commentId, resolved);
        }

        void open() {
            if (state != PullRequestState.DRAFT) {
                throw new IllegalStateException(
                    "Only draft Pull Requests can be opened."
                );
            }
            state = PullRequestState.OPEN;
        }

        void close() {
            if (state == PullRequestState.MERGED) {
                throw new IllegalStateException(
                    "Merged Pull Requests cannot be closed."
                );
            }
            state = PullRequestState.CLOSED;
        }

        void reopen() {
            if (state != PullRequestState.CLOSED) {
                throw new IllegalStateException(
                    "Only closed Pull Requests can be reopened."
                );
            }
            state = PullRequestState.OPEN;
        }

        int number() {
            return number;
        }

        String author() {
            return author;
        }

        String targetBranch() {
            return targetBranch;
        }

        PullRequestState state() {
            return state;
        }

        String latestCommitSha() {
            if (commits.isEmpty()) {
                return null;
            }
            return commits.get(commits.size() - 1).sha();
        }

        List<Review> reviews() {
            return List.copyOf(reviews);
        }

        Set<String> reviewers() {
            return Set.copyOf(reviewers);
        }

        Map<String, StatusCheck> checks() {
            return Map.copyOf(checks);
        }

        Map<Integer, Boolean> conversations() {
            return Map.copyOf(conversations);
        }

        void merge(MergeStrategy strategy) {
            this.mergeStrategy = strategy;
            this.state = PullRequestState.MERGED;
        }

        MergeStrategy mergeStrategy() {
            return mergeStrategy;
        }
    }

    static final class GovernanceService {
        private final Map<String, BranchProtectionPolicy> policies =
            new HashMap<>();

        void registerPolicy(BranchProtectionPolicy policy) {
            policies.put(policy.branch(), policy);
        }

        GovernanceResult evaluate(PullRequest pr) {
            List<String> failures = new ArrayList<>();

            if (pr.state() != PullRequestState.OPEN) {
                failures.add("Pull Request is not open.");
            }

            if (pr.latestCommitSha() == null) {
                failures.add("Pull Request contains no commits.");
            }

            BranchProtectionPolicy policy =
                policies.get(pr.targetBranch());

            if (policy == null) {
                failures.add(
                    "No branch-protection policy exists for target branch."
                );
                return new GovernanceResult(false, failures, false);
            }

            if (policy.bypassUsers().contains(pr.author())) {
                return new GovernanceResult(true, List.of(), true);
            }

            String latestSha = pr.latestCommitSha();

            Set<String> currentApprovers = new HashSet<>();

            if (latestSha != null) {
                pr.reviews().stream()
                    .filter(review ->
                        review.state() == ReviewState.APPROVED
                        && review.commitSha().equals(latestSha)
                        && pr.reviewers().contains(review.reviewer())
                        && !review.reviewer().equals(pr.author())
                    )
                    .map(Review::reviewer)
                    .forEach(currentApprovers::add);
            }

            if (currentApprovers.size() < policy.requiredApprovals()) {
                failures.add(
                    "Required approvals: "
                    + policy.requiredApprovals()
                    + "; current approvals: "
                    + currentApprovers.size()
                );
            }

            for (String requiredCheck : policy.requiredChecks()) {
                StatusCheck check = pr.checks().get(requiredCheck);

                if (check == null ||
                    check.state() != CheckState.PASSED) {
                    failures.add(
                        "Required status check failed or is missing: "
                        + requiredCheck
                    );
                }
            }

            if (policy.requireConversationResolution()) {
                pr.conversations().forEach((id, resolved) -> {
                    if (!resolved) {
                        failures.add(
                            "Unresolved review conversation: " + id
                        );
                    }
                });
            }

            if (policy.requireLinearHistory() &&
                pr.mergeStrategy() == MergeStrategy.MERGE_COMMIT) {
                failures.add(
                    "Merge commits violate the linear-history policy."
                );
            }

            return new GovernanceResult(
                failures.isEmpty(),
                List.copyOf(failures),
                false
            );
        }

        void merge(PullRequest pr, MergeStrategy strategy) {
            pr.merge(strategy);

            GovernanceResult result = evaluate(pr);

            // The state is rolled into the domain object only after eligibility
            // is established in normal operation. This guard protects callers
            // from accidentally persisting an invalid merged state.
            if (!result.eligible()) {
                throw new IllegalStateException(
                    "Merge rejected after state validation: "
                    + String.join("; ", result.failures())
                );
            }
        }
    }

    public static void main(String[] args) {
        GovernanceService service = new GovernanceService();

        service.registerPolicy(
            new BranchProtectionPolicy(
                "main",
                2,
                Set.of("unit-tests", "security-scan"),
                true,
                true,
                false,
                false,
                false,
                Set.of()
            )
        );

        PullRequest pr = new PullRequest(
            501,
            "feature/customer-validation",
            "main",
            "alice",
            "Validate customer records"
        );

        pr.addCommit(
            new Commit("e001", "Validate customer identifiers", "alice")
        );
        pr.addCommit(
            new Commit("e002", "Add boundary validation", "alice")
        );

        pr.requestReview("bob");
        pr.requestReview("carol");
        pr.open();

        pr.setStatusCheck("unit-tests", CheckState.PASSED);
        pr.setStatusCheck("security-scan", CheckState.PASSED);

        pr.setConversation(301, true);
        pr.setConversation(302, false);

        pr.addReview(
            "bob",
            ReviewState.APPROVED,
            "e002",
            List.of("Validation structure is acceptable.")
        );

        GovernanceResult initial = service.evaluate(pr);

        System.out.println("Initial eligibility: " + initial.eligible());
        initial.failures().forEach(f -> System.out.println("  - " + f));

        // New commits invalidate approvals tied to the old commit context.
        pr.addCommit(
            new Commit("e003", "Reject malformed identifiers", "alice")
        );
        pr.setConversation(302, true);

        GovernanceResult synchronizedResult = service.evaluate(pr);

        System.out.println(
            "\nAfter synchronization: "
            + synchronizedResult.eligible()
        );
        synchronizedResult.failures()
            .forEach(f -> System.out.println("  - " + f));

        pr.addReview(
            "bob",
            ReviewState.APPROVED,
            "e003",
            List.of("Reviewed the new validation.")
        );

        pr.addReview(
            "carol",
            ReviewState.APPROVED,
            "e003",
            List.of("Security and edge cases checked.")
        );

        GovernanceResult finalResult = service.evaluate(pr);

        System.out.println(
            "\nFinal eligibility: "
            + finalResult.eligible()
        );

        if (finalResult.eligible()) {
            /*
             * Rebase is selected because the protected branch requires
             * linear history.
             */
            pr.merge(MergeStrategy.REBASE);
        }

        System.out.println("Final PR state: " + pr.state());
        System.out.println("Merge strategy: " + pr.mergeStrategy());
    }

    private static String requireText(String value, String field) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(
                field + " cannot be empty."
            );
        }
        return value;
    }
}
