import java.util.ArrayList;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

public class RepositoryIntegrationTest {

    enum PullRequestState {
        DRAFT,
        OPEN,
        CLOSED,
        MERGED
    }

    enum ReviewState {
        COMMENTED,
        APPROVED,
        CHANGES_REQUESTED,
        DISMISSED
    }

    enum MergeStrategy {
        MERGE_COMMIT,
        SQUASH,
        REBASE
    }

    record Commit(String sha, String message, String branch) {
        public Commit {
            if (sha == null || sha.length() < 7 || sha.length() > 40) {
                throw new IllegalArgumentException("Invalid commit SHA");
            }
            if (message == null || message.isBlank()) {
                throw new IllegalArgumentException(
                    "Commit message cannot be empty"
                );
            }
        }
    }

    record StatusCheck(
        String name,
        boolean passed,
        String commitSha
    ) {}

    record Review(
        String reviewer,
        ReviewState state,
        String commitSha,
        boolean resolved
    ) {}

    record BranchProtection(
        int requiredReviews,
        Set<String> requiredChecks,
        boolean allowDirectPush,
        boolean allowForcePush,
        boolean allowDeletion,
        boolean requireConversationResolution,
        boolean requireLinearHistory
    ) {
        public BranchProtection {
            if (requiredReviews < 0) {
                throw new IllegalArgumentException(
                    "Required reviews cannot be negative"
                );
            }

            requiredChecks = Set.copyOf(requiredChecks);
        }
    }

    static final class Branch {
        private final String name;
        private final List<Commit> commits = new ArrayList<>();
        private boolean protectedBranch;

        Branch(String name) {
            this.name = Objects.requireNonNull(name);
        }
    }

    static final class PullRequest {
        private final int number;
        private final String title;
        private final String sourceBranch;
        private final String targetBranch;
        private final String author;
        private final Set<String> changedFiles;

        private PullRequestState state;
        private boolean draft;
        private List<Commit> commits;
        private final List<Review> reviews = new ArrayList<>();
        private final List<StatusCheck> checks = new ArrayList<>();
        private int unresolvedConversations;
        private MergeStrategy mergeStrategy;

        PullRequest(
            int number,
            String title,
            String sourceBranch,
            String targetBranch,
            String author,
            boolean draft,
            List<Commit> commits,
            Set<String> changedFiles
        ) {
            this.number = number;
            this.title = title;
            this.sourceBranch = sourceBranch;
            this.targetBranch = targetBranch;
            this.author = author;
            this.draft = draft;
            this.state = draft
                ? PullRequestState.DRAFT
                : PullRequestState.OPEN;
            this.commits = new ArrayList<>(commits);
            this.changedFiles = new HashSet<>(changedFiles);
        }

        String latestCommit() {
            if (commits.isEmpty()) {
                return null;
            }
            return commits.get(commits.size() - 1).sha();
        }
    }

    record MergeEligibility(
        boolean eligible,
        List<String> reasons
    ) {}

    static final class Repository {
        private final String name;
        private int nextPullRequest = 1;

        private final Map<String, Branch> branches = new HashMap<>();
        private final Map<Integer, PullRequest> pullRequests =
            new HashMap<>();
        private final Map<String, BranchProtection> policies =
            new HashMap<>();

        Repository(String name) {
            this.name = Objects.requireNonNull(name);
        }

        void addBranch(String name) {
            if (branches.containsKey(name)) {
                throw new IllegalStateException(
                    "Branch already exists: " + name
                );
            }

            branches.put(name, new Branch(name));
        }

        void protectBranch(
            String branchName,
            BranchProtection policy
        ) {
            Branch branch = requireBranch(branchName);
            branch.protectedBranch = true;
            policies.put(branchName, policy);
        }

        void addCommit(
            String branchName,
            Commit commit
        ) {
            requireBranch(branchName).commits.add(commit);
        }

        PullRequest createPullRequest(
            String title,
            String source,
            String target,
            String author,
            Set<String> changedFiles,
            boolean draft
        ) {
            Branch sourceBranch = requireBranch(source);
            requireBranch(target);

            if (source.equals(target)) {
                throw new IllegalArgumentException(
                    "Source and target branches must differ"
                );
            }

            if (sourceBranch.commits.isEmpty()) {
                throw new IllegalArgumentException(
                    "Pull Request must contain a commit"
                );
            }

            PullRequest pr = new PullRequest(
                nextPullRequest++,
                title,
                source,
                target,
                author,
                draft,
                sourceBranch.commits,
                changedFiles
            );

            pullRequests.put(pr.number, pr);
            return pr;
        }

        void synchronize(int number) {
            PullRequest pr = requirePR(number);
            Branch source = requireBranch(pr.sourceBranch);

            pr.commits = new ArrayList<>(source.commits);

            String latest = pr.latestCommit();

            for (int i = 0; i < pr.reviews.size(); i++) {
                Review review = pr.reviews.get(i);

                if (!review.commitSha().equals(latest)) {
                    pr.reviews.set(
                        i,
                        new Review(
                            review.reviewer(),
                            ReviewState.DISMISSED,
                            review.commitSha(),
                            review.resolved()
                        )
                    );
                }
            }
        }

        void submitReview(
            int number,
            String reviewer,
            ReviewState state,
            String commitSha
        ) {
            PullRequest pr = requirePR(number);

            if (pr.author.equals(reviewer)) {
                throw new IllegalArgumentException(
                    "Authors cannot approve their own changes"
                );
            }

            if (!commitSha.equals(pr.latestCommit())) {
                state = ReviewState.DISMISSED;
            }

            pr.reviews.add(
                new Review(
                    reviewer,
                    state,
                    commitSha,
                    true
                )
            );
        }

        void addStatusCheck(
            int number,
            String name,
            boolean passed,
            String commitSha
        ) {
            requirePR(number).checks.add(
                new StatusCheck(name, passed, commitSha)
            );
        }

        void addUnresolvedConversation(int number) {
            requirePR(number).unresolvedConversations++;
        }

        void resolveConversation(int number) {
            PullRequest pr = requirePR(number);

            if (pr.unresolvedConversations > 0) {
                pr.unresolvedConversations--;
            }
        }

        MergeEligibility evaluateMergeEligibility(int number) {
            PullRequest pr = requirePR(number);
            BranchProtection policy = policies.get(pr.targetBranch);

            List<String> reasons = new ArrayList<>();

            if (policy == null) {
                return new MergeEligibility(
                    false,
                    List.of("Target branch has no protection policy")
                );
            }

            if (pr.state != PullRequestState.OPEN) {
                reasons.add("Pull Request is not open");
            }

            if (pr.draft) {
                reasons.add("Pull Request is still a draft");
            }

            String latest = pr.latestCommit();

            Set<String> currentApprovers = new HashSet<>();

            for (Review review : pr.reviews) {
                if (
                    review.state() == ReviewState.APPROVED &&
                    review.commitSha().equals(latest)
                ) {
                    currentApprovers.add(review.reviewer());
                }
            }

            if (currentApprovers.size() < policy.requiredReviews()) {
                reasons.add(
                    "Required current approvals: " +
                    policy.requiredReviews() +
                    ", found: " +
                    currentApprovers.size()
                );
            }

            for (String requiredCheck : policy.requiredChecks()) {
                boolean passed = pr.checks.stream().anyMatch(check ->
                    check.name().equals(requiredCheck) &&
                    check.commitSha().equals(latest) &&
                    check.passed()
                );

                if (!passed) {
                    reasons.add(
                        "Required check failed or missing: " +
                        requiredCheck
                    );
                }
            }

            if (
                policy.requireConversationResolution() &&
                pr.unresolvedConversations > 0
            ) {
                reasons.add(
                    "Unresolved review conversations remain"
                );
            }

            if (pr.changedFiles.isEmpty()) {
                reasons.add("Pull Request has no changed files");
            }

            return new MergeEligibility(
                reasons.isEmpty(),
                List.copyOf(reasons)
            );
        }

        void merge(
            int number,
            MergeStrategy strategy
        ) {
            PullRequest pr = requirePR(number);
            MergeEligibility result =
                evaluateMergeEligibility(number);

            if (!result.eligible()) {
                throw new IllegalStateException(
                    "Merge rejected: " +
                    String.join("; ", result.reasons())
                );
            }

            Branch target = requireBranch(pr.targetBranch);

            if (strategy == MergeStrategy.MERGE_COMMIT) {
                target.commits.add(
                    new Commit(
                        "merge" + pr.number,
                        "Merge PR #" + pr.number +
                        ": " + pr.title,
                        target.name
                    )
                );
            } else if (strategy == MergeStrategy.SQUASH) {
                target.commits.add(
                    new Commit(
                        "squash" + pr.number,
                        pr.title,
                        target.name
                    )
                );
            } else {
                target.commits.addAll(
                    pr.commits.stream()
                        .map(commit -> new Commit(
                            commit.sha(),
                            commit.message(),
                            target.name
                        ))
                        .toList()
                );
            }

            pr.mergeStrategy = strategy;
            pr.state = PullRequestState.MERGED;
        }

        private Branch requireBranch(String name) {
            Branch branch = branches.get(name);

            if (branch == null) {
                throw new IllegalArgumentException(
                    "Unknown branch: " + name
                );
            }

            return branch;
        }

        private PullRequest requirePR(int number) {
            PullRequest pr = pullRequests.get(number);

            if (pr == null) {
                throw new IllegalArgumentException(
                    "Unknown Pull Request #" + number
                );
            }

            return pr;
        }
    }

    static void successfulWorkflowTest() {
        Repository repository =
            new Repository("enterprise-integration");

        repository.addBranch("main");
        repository.addBranch("feature/integration");

        repository.protectBranch(
            "main",
            new BranchProtection(
                2,
                Set.of(
                    "api-integration",
                    "database-integration"
                ),
                false,
                false,
                false,
                true,
                false
            )
        );

        repository.addCommit(
            "feature/integration",
            new Commit(
                "2222222",
                "Add API and database integration tests",
                "feature/integration"
            )
        );

        PullRequest pr = repository.createPullRequest(
            "Integration test coverage",
            "feature/integration",
            "main",
            "alice",
            Set.of(
                "src/api-test.java",
                "src/database-test.java"
            ),
            false
        );

        String latest = pr.latestCommit();

        repository.submitReview(
            pr.number,
            "bob",
            ReviewState.APPROVED,
            latest
        );

        repository.submitReview(
            pr.number,
            "carol",
            ReviewState.APPROVED,
            latest
        );

        repository.addStatusCheck(
            pr.number,
            "api-integration",
            true,
            latest
        );

        repository.addStatusCheck(
            pr.number,
            "database-integration",
            true,
            latest
        );

        repository.addUnresolvedConversation(pr.number);

        MergeEligibility before =
            repository.evaluateMergeEligibility(pr.number);

        if (before.eligible()) {
            throw new AssertionError(
                "Unresolved conversation must block merge"
            );
        }

        repository.resolveConversation(pr.number);

        MergeEligibility after =
            repository.evaluateMergeEligibility(pr.number);

        if (!after.eligible()) {
            throw new AssertionError(
                "Expected PR to become merge eligible"
            );
        }

        repository.merge(
            pr.number,
            MergeStrategy.SQUASH
        );

        if (pr.state != PullRequestState.MERGED) {
            throw new AssertionError("PR was not merged");
        }

        System.out.println(
            "PASS: Java enterprise integration workflow"
        );
    }

    static void staleApprovalTest() {
        Repository repository =
            new Repository("stale-approval");

        repository.addBranch("main");
        repository.addBranch("feature");

        repository.protectBranch(
            "main",
            new BranchProtection(
                2,
                Set.of("integration-tests"),
                false,
                false,
                false,
                true,
                false
            )
        );

        repository.addCommit(
            "feature",
            new Commit(
                "2222222",
                "Initial integration tests",
                "feature"
            )
        );

        PullRequest pr = repository.createPullRequest(
            "Database integration tests",
            "feature",
            "main",
            "alice",
            Set.of("database-test.java"),
            false
        );

        repository.submitReview(
            pr.number,
            "bob",
            ReviewState.APPROVED,
            "2222222"
        );

        repository.submitReview(
            pr.number,
            "carol",
            ReviewState.APPROVED,
            "2222222"
        );

        repository.addCommit(
            "feature",
            new Commit(
                "3333333",
                "Fix transaction rollback test",
                "feature"
            )
        );

        repository.synchronize(pr.number);

        repository.addStatusCheck(
            pr.number,
            "integration-tests",
            true,
            "3333333"
        );

        MergeEligibility result =
            repository.evaluateMergeEligibility(pr.number);

        if (result.eligible()) {
            throw new AssertionError(
                "Stale approvals must not satisfy current policy"
            );
        }

        System.out.println(
            "PASS: Java stale approval handling"
        );
    }

    static void failedCheckTest() {
        Repository repository =
            new Repository("failed-check");

        repository.addBranch("main");
        repository.addBranch("feature");

        repository.protectBranch(
            "main",
            new BranchProtection(
                1,
                Set.of("integration-tests"),
                false,
                false,
                false,
                true,
                false
            )
        );

        repository.addCommit(
            "feature",
            new Commit(
                "2222222",
                "Add API integration tests",
                "feature"
            )
        );

        PullRequest pr = repository.createPullRequest(
            "API integration validation",
            "feature",
            "main",
            "alice",
            Set.of("api-test.java"),
            false
        );

        repository.submitReview(
            pr.number,
            "bob",
            ReviewState.APPROVED,
            "2222222"
        );

        repository.addStatusCheck(
            pr.number,
            "integration-tests",
            false,
            "2222222"
        );

        MergeEligibility result =
            repository.evaluateMergeEligibility(pr.number);

        if (result.eligible()) {
            throw new AssertionError(
                "Failed integration check must block merge"
            );
        }

        System.out.println(
            "PASS: Java failed-check handling"
        );
    }

    public static void main(String[] args) {
        successfulWorkflowTest();
        staleApprovalTest();
        failedCheckTest();

        System.out.println(
            "\nAll Java 17 integration tests passed."
        );
    }
}
