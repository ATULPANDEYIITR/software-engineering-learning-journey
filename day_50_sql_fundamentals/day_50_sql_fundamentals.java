import java.time.Instant;
import java.util.ArrayList;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class RepositoryGovernance {

    enum PullRequestState {
        OPEN, CLOSED, MERGED
    }

    enum ReviewState {
        APPROVED, CHANGES_REQUESTED, COMMENTED
    }

    enum CheckState {
        PASSING, FAILING, PENDING
    }

    record Commit(String id, String message, Instant createdAt) {
        Commit {
            if (id == null || id.isBlank()) {
                throw new IllegalArgumentException("Commit ID is required.");
            }
            if (message == null || message.isBlank()) {
                throw new IllegalArgumentException("Commit message is required.");
            }
        }
    }

    record Review(
        String reviewer,
        ReviewState state,
        String comment,
        Instant submittedAt
    ) {
        Review {
            if (reviewer == null || reviewer.isBlank()) {
                throw new IllegalArgumentException("Reviewer is required.");
            }
            if (state == null) {
                throw new IllegalArgumentException("Review state is required.");
            }
        }
    }

    record BranchProtectionPolicy(
        String branch,
        int requiredApprovals,
        Set<String> requiredChecks,
        boolean restrictDirectPush,
        boolean restrictForcePush,
        boolean requireConversationResolution
    ) {
        BranchProtectionPolicy {
            if (branch == null || branch.isBlank()) {
                throw new IllegalArgumentException("Protected branch is required.");
            }
            if (requiredApprovals < 0) {
                throw new IllegalArgumentException(
                    "Required approvals cannot be negative."
                );
            }
            requiredChecks = Set.copyOf(requiredChecks);
        }
    }

    static final class PullRequest {
        private final int number;
        private final String title;
        private final String sourceBranch;
        private final String targetBranch;
        private final String author;
        private final List<Commit> commits = new ArrayList<>();
        private final List<Review> reviews = new ArrayList<>();
        private final Map<String, CheckState> statusChecks = new HashMap<>();
        private PullRequestState state = PullRequestState.OPEN;
        private boolean draft;

        PullRequest(
            int number,
            String title,
            String sourceBranch,
            String targetBranch,
            String author,
            boolean draft
        ) {
            if (title == null || title.isBlank()) {
                throw new IllegalArgumentException("Title is required.");
            }
            if (sourceBranch == null || sourceBranch.isBlank()) {
                throw new IllegalArgumentException("Source branch is required.");
            }
            if (targetBranch == null || targetBranch.isBlank()) {
                throw new IllegalArgumentException("Target branch is required.");
            }
            if (sourceBranch.equals(targetBranch)) {
                throw new IllegalArgumentException(
                    "Source and target branches must differ."
                );
            }

            this.number = number;
            this.title = title;
            this.sourceBranch = sourceBranch;
            this.targetBranch = targetBranch;
            this.author = author;
            this.draft = draft;
        }

        void addCommit(Commit commit) {
            if (state == PullRequestState.CLOSED) {
                throw new IllegalStateException(
                    "Closed pull requests cannot receive commits."
                );
            }
            commits.add(commit);
        }

        void addReview(Review review) {
            if (review.state() == ReviewState.APPROVED &&
                review.reviewer().equals(author)) {
                throw new IllegalArgumentException(
                    "Authors cannot approve their own pull request."
                );
            }
            reviews.add(review);
        }

        void setStatusCheck(String name, CheckState state) {
            if (name == null || name.isBlank()) {
                throw new IllegalArgumentException(
                    "Status-check name is required."
                );
            }
            statusChecks.put(name, state);
        }

        void merge() {
            state = PullRequestState.MERGED;
        }

        List<Review> reviews() {
            return List.copyOf(reviews);
        }

        Map<String, CheckState> statusChecks() {
            return Map.copyOf(statusChecks);
        }

        String targetBranch() {
            return targetBranch;
        }

        PullRequestState state() {
            return state;
        }

        boolean draft() {
            return draft;
        }

        int number() {
            return number;
        }

        String title() {
            return title;
        }
    }

    static final class MergeDecision {
        private final boolean eligible;
        private final List<String> reasons;

        MergeDecision(boolean eligible, List<String> reasons) {
            this.eligible = eligible;
            this.reasons = List.copyOf(reasons);
        }

        boolean eligible() {
            return eligible;
        }

        List<String> reasons() {
            return reasons;
        }
    }

    static final class RepositoryService {
        private final Map<String, String> branches = new HashMap<>();
        private final Map<Integer, PullRequest> pullRequests = new HashMap<>();
        private final Map<String, BranchProtectionPolicy> policies = new HashMap<>();
        private int nextPullRequestNumber = 1;

        RepositoryService() {
            branches.put("main", "c100");
            branches.put("feature/sql-crud", "c104");
        }

        void protect(BranchProtectionPolicy policy) {
            policies.put(policy.branch(), policy);
        }

        PullRequest createPullRequest(
            String title,
            String source,
            String target,
            String author,
            boolean draft
        ) {
            if (!branches.containsKey(source) || !branches.containsKey(target)) {
                throw new IllegalArgumentException("Unknown branch.");
            }

            PullRequest pr = new PullRequest(
                nextPullRequestNumber++,
                title,
                source,
                target,
                author,
                draft
            );

            pullRequests.put(pr.number(), pr);
            return pr;
        }

        MergeDecision evaluate(int number) {
            PullRequest pr = find(number);
            BranchProtectionPolicy policy = policies.get(pr.targetBranch());

            if (policy == null) {
                return new MergeDecision(true, List.of());
            }

            List<String> reasons = new ArrayList<>();

            if (pr.state() != PullRequestState.OPEN) {
                reasons.add("Pull request is not open.");
            }

            if (pr.draft()) {
                reasons.add("Draft pull requests cannot be merged.");
            }

            Set<String> approvers = new HashSet<>();

            pr.reviews().stream()
                .filter(review -> review.state() == ReviewState.APPROVED)
                .map(Review::reviewer)
                .forEach(approvers::add);

            if (approvers.size() < policy.requiredApprovals()) {
                reasons.add(
                    "Required approvals: "
                    + policy.requiredApprovals()
                    + ", available: "
                    + approvers.size()
                );
            }

            for (String check : policy.requiredChecks()) {
                if (pr.statusChecks().get(check) != CheckState.PASSING) {
                    reasons.add("Required check is not passing: " + check);
                }
            }

            if (policy.requireConversationResolution()) {
                boolean unresolved = pr.reviews().stream()
                    .anyMatch(
                        review ->
                            review.state() == ReviewState.CHANGES_REQUESTED
                    );

                if (unresolved) {
                    reasons.add(
                        "At least one review has requested changes."
                    );
                }
            }

            return new MergeDecision(reasons.isEmpty(), reasons);
        }

        void merge(int number) {
            PullRequest pr = find(number);
            MergeDecision decision = evaluate(number);

            if (!decision.eligible()) {
                throw new IllegalStateException(
                    "Merge blocked: " +
                    String.join("; ", decision.reasons())
                );
            }

            branches.put(pr.targetBranch(), branches.get(pr.targetBranch()));
            pr.merge();
        }

        private PullRequest find(int number) {
            PullRequest pr = pullRequests.get(number);

            if (pr == null) {
                throw new IllegalArgumentException(
                    "Pull request does not exist."
                );
            }

            return pr;
        }
    }

    public static void main(String[] args) {
        RepositoryService service = new RepositoryService();

        BranchProtectionPolicy policy =
            new BranchProtectionPolicy(
                "main",
                2,
                Set.of("unit-tests", "sql-validation"),
                true,
                true,
                true
            );

        service.protect(policy);

        PullRequest pr = service.createPullRequest(
            "Add safe CRUD examples",
            "feature/sql-crud",
            "main",
            "developer",
            false
        );

        pr.addCommit(
            new Commit(
                "a81f2d",
                "Add SELECT and INSERT examples",
                Instant.now()
            )
        );

        pr.addCommit(
            new Commit(
                "b93c10",
                "Add UPDATE and DELETE safeguards",
                Instant.now()
            )
        );

        pr.addReview(
            new Review(
                "alice",
                ReviewState.APPROVED,
                "Constraints are appropriate.",
                Instant.now()
            )
        );

        pr.addReview(
            new Review(
                "bob",
                ReviewState.APPROVED,
                "Transaction behavior is valid.",
                Instant.now()
            )
        );

        pr.setStatusCheck("unit-tests", CheckState.PASSING);
        pr.setStatusCheck("sql-validation", CheckState.PASSING);

        MergeDecision decision = service.evaluate(pr.number());

        System.out.println("Pull Request #" + pr.number());
        System.out.println("Title: " + pr.title());
        System.out.println("Merge eligible: " + decision.eligible());

        if (!decision.eligible()) {
            decision.reasons().forEach(
                reason -> System.out.println("Blocked: " + reason)
            );
        } else {
            service.merge(pr.number());
            System.out.println("Pull request merged successfully.");
        }
    }
}
