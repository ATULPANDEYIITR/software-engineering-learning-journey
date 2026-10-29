import java.time.Instant;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Queue;
import java.util.Set;
import java.util.UUID;

public class MessageQueueEnterpriseDemo {

    enum MessageState {
        READY, PROCESSING, ACKNOWLEDGED, FAILED, DEAD_LETTERED
    }

    enum ReviewState {
        COMMENTED, APPROVED, CHANGES_REQUESTED, DISMISSED
    }

    record Message(
            String id,
            String topic,
            Map<String, Object> payload,
            Instant createdAt,
            int attempts
    ) {
        Message {
            Objects.requireNonNull(id);
            Objects.requireNonNull(topic);
            Objects.requireNonNull(payload);

            if (id.isBlank() || topic.isBlank()) {
                throw new IllegalArgumentException("Message identity is invalid");
            }

            payload = Collections.unmodifiableMap(new HashMap<>(payload));
        }

        Message retry() {
            return new Message(id, topic, payload, createdAt, attempts + 1);
        }
    }

    record StatusCheck(String name, boolean passed) {}

    record Review(
            String reviewer,
            ReviewState state,
            boolean stale
    ) {
        Review {
            Objects.requireNonNull(reviewer);
            Objects.requireNonNull(state);
        }
    }

    record BranchProtectionPolicy(
            String branch,
            int requiredApprovals,
            Set<String> eligibleReviewers,
            Set<String> requiredChecks,
            boolean requireResolvedConversations,
            boolean restrictDirectPush,
            boolean restrictForcePush,
            boolean requireLinearHistory
    ) {
        BranchProtectionPolicy {
            if (branch == null || branch.isBlank()) {
                throw new IllegalArgumentException("Protected branch is required");
            }
            if (requiredApprovals < 0) {
                throw new IllegalArgumentException("Approval count cannot be negative");
            }
            if (eligibleReviewers == null || requiredChecks == null) {
                throw new IllegalArgumentException("Policy collections are required");
            }

            eligibleReviewers = Set.copyOf(eligibleReviewers);
            requiredChecks = Set.copyOf(requiredChecks);
        }
    }

    record PullRequest(
            int number,
            String sourceBranch,
            String targetBranch,
            List<String> commits,
            List<Review> reviews,
            List<StatusCheck> checks,
            boolean draft,
            boolean mergeConflict,
            boolean open,
            boolean conversationsResolved,
            boolean synchronizedWithBase
    ) {
        PullRequest {
            if (number <= 0) {
                throw new IllegalArgumentException("PR number must be positive");
            }
            if (sourceBranch == null || targetBranch == null ||
                    sourceBranch.isBlank() || targetBranch.isBlank()) {
                throw new IllegalArgumentException("Branches are required");
            }

            commits = List.copyOf(commits);
            reviews = List.copyOf(reviews);
            checks = List.copyOf(checks);
        }
    }

    static final class MergeEligibilityException extends Exception {
        MergeEligibilityException(String message) {
            super(message);
        }
    }

    static final class ApprovalPolicyService {
        int validApprovals(
                PullRequest pr,
                BranchProtectionPolicy policy
        ) {
            Set<String> approvedReviewers = new HashSet<>();

            for (Review review : pr.reviews()) {
                if (review.state() == ReviewState.APPROVED
                        && !review.stale()
                        && policy.eligibleReviewers()
                        .contains(review.reviewer())) {
                    approvedReviewers.add(review.reviewer());
                }
            }

            return approvedReviewers.size();
        }
    }

    static final class MergeEligibilityService {
        private final ApprovalPolicyService approvalService =
                new ApprovalPolicyService();

        void validate(
                PullRequest pr,
                BranchProtectionPolicy policy
        ) throws MergeEligibilityException {

            if (!pr.open()) {
                throw new MergeEligibilityException("Pull Request is closed");
            }

            if (pr.draft()) {
                throw new MergeEligibilityException("Pull Request is a draft");
            }

            if (!pr.synchronizedWithBase()) {
                throw new MergeEligibilityException(
                        "Source branch is behind the target branch"
                );
            }

            if (pr.mergeConflict()) {
                throw new MergeEligibilityException(
                        "Merge conflicts are unresolved"
                );
            }

            if (policy.requireResolvedConversations()
                    && !pr.conversationsResolved()) {
                throw new MergeEligibilityException(
                        "Required conversations remain unresolved"
                );
            }

            Map<String, Boolean> checkResults = new HashMap<>();
            for (StatusCheck check : pr.checks()) {
                checkResults.put(check.name(), check.passed());
            }

            for (String required : policy.requiredChecks()) {
                if (!Boolean.TRUE.equals(checkResults.get(required))) {
                    throw new MergeEligibilityException(
                            "Required status check failed: " + required
                    );
                }
            }

            int approvals = approvalService.validApprovals(pr, policy);

            if (approvals < policy.requiredApprovals()) {
                throw new MergeEligibilityException(
                        "Required approvals: " + policy.requiredApprovals()
                                + ", valid approvals: " + approvals
                );
            }
        }
    }

    static final class MessageBroker {
        private final int maxAttempts;
        private final Queue<Message> queue = new ArrayDeque<>();
        private final List<Message> deadLetters = new ArrayList<>();
        private final Map<MessageState, Integer> counters =
                new EnumMap<>(MessageState.class);

        MessageBroker(int maxAttempts) {
            if (maxAttempts <= 0) {
                throw new IllegalArgumentException(
                        "Maximum attempts must be positive"
                );
            }
            this.maxAttempts = maxAttempts;

            for (MessageState state : MessageState.values()) {
                counters.put(state, 0);
            }
        }

        void publish(Message message) {
            queue.add(message);
            increment(MessageState.READY);
        }

        Message receive() {
            Message message = queue.poll();
            if (message == null) {
                return null;
            }

            increment(MessageState.PROCESSING);
            return message;
        }

        void acknowledge(Message message) {
            increment(MessageState.ACKNOWLEDGED);
        }

        void reject(Message message) {
            increment(MessageState.FAILED);

            if (message.attempts() + 1 >= maxAttempts) {
                Message dead = message.retry();
                deadLetters.add(dead);
                increment(MessageState.DEAD_LETTERED);
                return;
            }

            queue.add(message.retry());
            increment(MessageState.READY);
        }

        int depth() {
            return queue.size();
        }

        int deadLetterCount() {
            return deadLetters.size();
        }

        private void increment(MessageState state) {
            counters.merge(state, 1, Integer::sum);
        }
    }

    static void runMessageWorkflow() {
        MessageBroker broker = new MessageBroker(3);

        broker.publish(new Message(
                UUID.randomUUID().toString(),
                "orders.created",
                Map.of("orderId", "ORD-9001", "amount", 250.50),
                Instant.now(),
                0
        ));

        broker.publish(new Message(
                UUID.randomUUID().toString(),
                "email.send",
                Map.of("recipient", "customer@example.test"),
                Instant.now(),
                0
        ));

        while (broker.depth() > 0) {
            Message message = broker.receive();

            if ("email.send".equals(message.topic())) {
                // Simulates a repeatedly unavailable downstream provider.
                broker.reject(message);
            } else {
                broker.acknowledge(message);
            }
        }

        while (broker.depth() > 0) {
            broker.reject(broker.receive());
        }

        System.out.println(
                "message_workflow dead_letters=" + broker.deadLetterCount()
        );
    }

    static void runGovernanceWorkflow() {
        BranchProtectionPolicy policy =
                new BranchProtectionPolicy(
                        "main",
                        2,
                        Set.of("alice", "bob", "carol"),
                        Set.of("unit-tests", "integration-tests"),
                        true,
                        true,
                        true,
                        true
                );

        PullRequest pr = new PullRequest(
                108,
                "feature/async-worker",
                "main",
                List.of("a1", "b2", "c3"),
                List.of(
                        new Review("alice", ReviewState.APPROVED, false),
                        new Review("bob", ReviewState.APPROVED, false),
                        new Review("mallory", ReviewState.APPROVED, false)
                ),
                List.of(
                        new StatusCheck("unit-tests", true),
                        new StatusCheck("integration-tests", true)
                ),
                false,
                false,
                true,
                true,
                true
        );

        MergeEligibilityService service = new MergeEligibilityService();

        try {
            service.validate(pr, policy);
            System.out.println(
                    "pr=" + pr.number() + " merge_eligible=true"
            );
        } catch (MergeEligibilityException error) {
            System.out.println(
                    "pr=" + pr.number()
                            + " merge_eligible=false reason="
                            + error.getMessage()
            );
        }

        // A stale approval cannot satisfy the current policy.
        PullRequest staleApproval = new PullRequest(
                pr.number(),
                pr.sourceBranch(),
                pr.targetBranch(),
                pr.commits(),
                List.of(
                        new Review("alice", ReviewState.APPROVED, true),
                        new Review("bob", ReviewState.APPROVED, false)
                ),
                pr.checks(),
                pr.draft(),
                pr.mergeConflict(),
                pr.open(),
                pr.conversationsResolved(),
                pr.synchronizedWithBase()
        );

        try {
            service.validate(staleApproval, policy);
        } catch (MergeEligibilityException error) {
            System.out.println(
                    "stale_approval_rejected=true reason="
                            + error.getMessage()
            );
        }
    }

    public static void main(String[] args) {
        runMessageWorkflow();
        runGovernanceWorkflow();
    }
}
