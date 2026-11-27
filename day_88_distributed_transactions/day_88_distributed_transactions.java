import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import java.util.function.Supplier;
import java.util.stream.Collectors;

/**
 * Distributed Transactions:
 * Enterprise Two-Phase Commit and Saga Processing.
 *
 * Java 17, no external dependencies.
 */
public class DistributedTransactions {

    enum TransactionMode {
        TWO_PHASE_COMMIT,
        SAGA
    }

    enum TransactionState {
        CREATED,
        PREPARING,
        PREPARED,
        COMMITTING,
        COMMITTED,
        ABORTING,
        ABORTED,
        COMPENSATING,
        COMPENSATED,
        IN_DOUBT,
        FAILED
    }

    enum ParticipantState {
        ACTIVE,
        PREPARED,
        COMMITTED,
        ABORTED
    }

    enum OperationType {
        PREPARE,
        COMMIT,
        ABORT,
        EXECUTE,
        COMPENSATE
    }

    record TransactionEvent(
        String transactionId,
        String participant,
        String action,
        String details,
        Instant timestamp
    ) {}

    record ParticipantResult(
        String participant,
        boolean successful,
        String message
    ) {}

    static class TransactionException extends RuntimeException {
        TransactionException(String message) {
            super(message);
        }
    }

    static class ParticipantException extends TransactionException {
        ParticipantException(String message) {
            super(message);
        }
    }

    static class AuditService {
        private final List<TransactionEvent> events =
            new ArrayList<>();

        public void record(
            String transactionId,
            String participant,
            String action,
            String details
        ) {
            TransactionEvent event = new TransactionEvent(
                transactionId,
                participant,
                action,
                details,
                Instant.now()
            );

            events.add(event);

            System.out.printf(
                "[%s] %s: %s%n",
                action,
                participant,
                details
            );
        }

        public List<TransactionEvent> getEvents() {
            return List.copyOf(events);
        }

        public long count(String action) {
            return events.stream()
                .filter(event -> event.action().equals(action))
                .count();
        }
    }

    interface TransactionParticipant {
        String name();

        boolean prepare(String transactionId);

        void commit(String transactionId);

        void abort(String transactionId);

        void execute(String transactionId);

        void compensate(String transactionId);

        ParticipantState state();
    }

    static class ServiceParticipant
            implements TransactionParticipant {

        private final String name;
        private final Supplier<Boolean> preparePolicy;
        private final Runnable execution;
        private final Runnable compensation;
        private final boolean failCommit;

        private ParticipantState state =
            ParticipantState.ACTIVE;

        private final Set<String> executedTransactions =
            new HashSet<>();

        private final Set<String> compensatedTransactions =
            new HashSet<>();

        ServiceParticipant(
            String name,
            Supplier<Boolean> preparePolicy,
            Runnable execution,
            Runnable compensation,
            boolean failCommit
        ) {
            this.name = Objects.requireNonNull(name);

            if (name.isBlank()) {
                throw new IllegalArgumentException(
                    "Participant name cannot be blank"
                );
            }

            this.preparePolicy = Objects.requireNonNull(preparePolicy);
            this.execution = Objects.requireNonNull(execution);
            this.compensation = Objects.requireNonNull(compensation);
            this.failCommit = failCommit;
        }

        @Override
        public String name() {
            return name;
        }

        @Override
        public ParticipantState state() {
            return state;
        }

        @Override
        public boolean prepare(String transactionId) {
            if (state != ParticipantState.ACTIVE) {
                throw new ParticipantException(
                    name + " cannot prepare from " + state
                );
            }

            if (!preparePolicy.get()) {
                return false;
            }

            state = ParticipantState.PREPARED;
            return true;
        }

        @Override
        public void commit(String transactionId) {
            if (state != ParticipantState.PREPARED) {
                throw new ParticipantException(
                    name + " is not prepared"
                );
            }

            if (failCommit) {
                throw new ParticipantException(
                    name + " commit failed"
                );
            }

            state = ParticipantState.COMMITTED;
        }

        @Override
        public void abort(String transactionId) {
            if (state == ParticipantState.COMMITTED) {
                throw new ParticipantException(
                    "Cannot abort committed work"
                );
            }

            if (state == ParticipantState.ABORTED) {
                return;
            }

            state = ParticipantState.ABORTED;
        }

        @Override
        public void execute(String transactionId) {
            if (state != ParticipantState.ACTIVE) {
                throw new ParticipantException(
                    name + " is not active"
                );
            }

            if (executedTransactions.contains(transactionId)) {
                return;
            }

            execution.run();

            executedTransactions.add(transactionId);
            state = ParticipantState.COMMITTED;
        }

        @Override
        public void compensate(String transactionId) {
            if (state != ParticipantState.COMMITTED) {
                throw new ParticipantException(
                    name + " has no committed operation"
                );
            }

            if (compensatedTransactions.contains(transactionId)) {
                return;
            }

            compensation.run();

            compensatedTransactions.add(transactionId);
            state = ParticipantState.ABORTED;
        }
    }

    static final class TransactionPolicy {

        private final int minimumParticipants;
        private final boolean requireAllVotes;

        TransactionPolicy(
            int minimumParticipants,
            boolean requireAllVotes
        ) {
            if (minimumParticipants < 1) {
                throw new IllegalArgumentException(
                    "Minimum participant count must be positive"
                );
            }

            this.minimumParticipants = minimumParticipants;
            this.requireAllVotes = requireAllVotes;
        }

        void validate(List<TransactionParticipant> participants) {
            if (participants.size() < minimumParticipants) {
                throw new TransactionException(
                    "Insufficient transaction participants"
                );
            }

            Set<String> names = participants.stream()
                .map(TransactionParticipant::name)
                .collect(Collectors.toSet());

            if (names.size() != participants.size()) {
                throw new TransactionException(
                    "Duplicate participant names"
                );
            }
        }

        boolean requireAllVotes() {
            return requireAllVotes;
        }
    }

    static class TransactionCoordinator {

        private final String transactionId;
        private final TransactionMode mode;
        private final List<TransactionParticipant> participants;
        private final TransactionPolicy policy;
        private final AuditService audit;

        private TransactionState state =
            TransactionState.CREATED;

        TransactionCoordinator(
            TransactionMode mode,
            List<TransactionParticipant> participants,
            TransactionPolicy policy,
            AuditService audit
        ) {
            this.transactionId = UUID.randomUUID().toString();
            this.mode = Objects.requireNonNull(mode);
            this.participants = List.copyOf(participants);
            this.policy = Objects.requireNonNull(policy);
            this.audit = Objects.requireNonNull(audit);

            policy.validate(this.participants);
        }

        private void transition(TransactionState next) {
            TransactionState previous = state;
            state = next;

            audit.record(
                transactionId,
                "COORDINATOR",
                "STATE_CHANGE",
                previous + " -> " + next
            );
        }

        private void ensureCreated() {
            if (state != TransactionState.CREATED) {
                throw new TransactionException(
                    "Transaction has already started"
                );
            }
        }

        private void abortAll() {
            boolean failed = false;

            for (TransactionParticipant participant : participants) {
                if (participant.state() == ParticipantState.COMMITTED) {
                    continue;
                }

                try {
                    participant.abort(transactionId);

                    audit.record(
                        transactionId,
                        participant.name(),
                        "ABORT",
                        "Participant aborted"
                    );

                } catch (RuntimeException error) {
                    failed = true;

                    audit.record(
                        transactionId,
                        participant.name(),
                        "ABORT_FAILURE",
                        error.getMessage()
                    );
                }
            }

            transition(
                failed
                    ? TransactionState.IN_DOUBT
                    : TransactionState.ABORTED
            );
        }

        public boolean execute2PC() {
            if (mode != TransactionMode.TWO_PHASE_COMMIT) {
                throw new TransactionException(
                    "Transaction is not configured for 2PC"
                );
            }

            ensureCreated();
            transition(TransactionState.PREPARING);

            List<ParticipantResult> votes = new ArrayList<>();

            // Phase 1: Prepare all participants.
            for (TransactionParticipant participant : participants) {
                try {
                    boolean accepted = participant.prepare(transactionId);

                    votes.add(new ParticipantResult(
                        participant.name(),
                        accepted,
                        accepted ? "YES" : "NO"
                    ));

                    audit.record(
                        transactionId,
                        participant.name(),
                        accepted ? "VOTE_YES" : "VOTE_NO",
                        "Prepare response received"
                    );

                } catch (RuntimeException error) {
                    votes.add(new ParticipantResult(
                        participant.name(),
                        false,
                        error.getMessage()
                    ));
                }
            }

            boolean allAccepted = votes.stream()
                .allMatch(ParticipantResult::successful);

            if (policy.requireAllVotes() && !allAccepted) {
                transition(TransactionState.ABORTING);
                abortAll();
                return false;
            }

            if (!allAccepted) {
                transition(TransactionState.ABORTING);
                abortAll();
                return false;
            }

            transition(TransactionState.PREPARED);

            /*
             * Production systems must persist the global decision
             * before broadcasting the commit instruction.
             */
            transition(TransactionState.COMMITTING);

            List<ParticipantResult> commitResults = new ArrayList<>();

            for (TransactionParticipant participant : participants) {
                try {
                    participant.commit(transactionId);

                    commitResults.add(new ParticipantResult(
                        participant.name(),
                        true,
                        "COMMITTED"
                    ));

                    audit.record(
                        transactionId,
                        participant.name(),
                        "COMMIT_ACK",
                        "Commit confirmed"
                    );

                } catch (RuntimeException error) {
                    commitResults.add(new ParticipantResult(
                        participant.name(),
                        false,
                        error.getMessage()
                    ));

                    audit.record(
                        transactionId,
                        participant.name(),
                        "COMMIT_UNCERTAIN",
                        error.getMessage()
                    );
                }
            }

            boolean complete = commitResults.stream()
                .allMatch(ParticipantResult::successful);

            transition(
                complete
                    ? TransactionState.COMMITTED
                    : TransactionState.IN_DOUBT
            );

            return complete;
        }

        public boolean executeSaga() {
            if (mode != TransactionMode.SAGA) {
                throw new TransactionException(
                    "Transaction is not configured for Saga"
                );
            }

            ensureCreated();

            List<TransactionParticipant> completed =
                new ArrayList<>();

            try {
                // Each service commits its own local transaction.
                for (TransactionParticipant participant : participants) {
                    participant.execute(transactionId);
                    completed.add(participant);

                    audit.record(
                        transactionId,
                        participant.name(),
                        "LOCAL_COMMIT",
                        "Saga step completed"
                    );
                }

                transition(TransactionState.COMMITTED);
                return true;

            } catch (RuntimeException error) {
                audit.record(
                    transactionId,
                    "COORDINATOR",
                    "SAGA_FAILURE",
                    error.getMessage()
                );
            }

            transition(TransactionState.COMPENSATING);

            boolean compensationSuccessful = true;

            Collections.reverse(completed);

            for (TransactionParticipant participant : completed) {
                try {
                    participant.compensate(transactionId);

                    audit.record(
                        transactionId,
                        participant.name(),
                        "COMPENSATED",
                        "Compensation successful"
                    );

                } catch (RuntimeException error) {
                    compensationSuccessful = false;

                    audit.record(
                        transactionId,
                        participant.name(),
                        "COMPENSATION_FAILURE",
                        error.getMessage()
                    );
                }
            }

            transition(
                compensationSuccessful
                    ? TransactionState.COMPENSATED
                    : TransactionState.FAILED
            );

            return false;
        }

        public void printReport() {
            System.out.println("\nTRANSACTION REPORT");
            System.out.println("ID: " + transactionId);
            System.out.println("Mode: " + mode);
            System.out.println("State: " + state);

            for (TransactionParticipant participant : participants) {
                System.out.printf(
                    "%s -> %s%n",
                    participant.name(),
                    participant.state()
                );
            }

            System.out.println(
                "Audit events: " + audit.getEvents().size()
            );
        }

        public TransactionState getState() {
            return state;
        }
    }

    private static ServiceParticipant participant(
        String name,
        boolean prepareAccepted,
        boolean failCommit,
        boolean failExecution
    ) {
        return new ServiceParticipant(
            name,
            () -> prepareAccepted,
            () -> {
                if (failExecution) {
                    throw new ParticipantException(
                        "Simulated service failure"
                    );
                }

                System.out.println(name + " local transaction committed");
            },
            () -> System.out.println(
                name + " compensation executed"
            ),
            failCommit
        );
    }

    public static void main(String[] args) {

        AuditService audit = new AuditService();

        TransactionPolicy policy = new TransactionPolicy(
            2,
            true
        );

        System.out.println("\nCASE 1: 2PC SUCCESS");

        TransactionCoordinator twoPhase =
            new TransactionCoordinator(
                TransactionMode.TWO_PHASE_COMMIT,
                List.of(
                    participant("InventoryService", true, false, false),
                    participant("PaymentService", true, false, false),
                    participant("OrderService", true, false, false)
                ),
                policy,
                audit
            );

        if (!twoPhase.execute2PC()) {
            throw new IllegalStateException("2PC should succeed");
        }

        twoPhase.printReport();

        System.out.println("\nCASE 2: 2PC REJECTION");

        TransactionCoordinator rejected =
            new TransactionCoordinator(
                TransactionMode.TWO_PHASE_COMMIT,
                List.of(
                    participant("InventoryService", true, false, false),
                    participant("PaymentService", false, false, false)
                ),
                policy,
                audit
            );

        rejected.execute2PC();

        if (rejected.getState() != TransactionState.ABORTED) {
            throw new IllegalStateException("Expected ABORTED");
        }

        rejected.printReport();

        System.out.println("\nCASE 3: UNCERTAIN COMMIT");

        TransactionCoordinator uncertain =
            new TransactionCoordinator(
                TransactionMode.TWO_PHASE_COMMIT,
                List.of(
                    participant("AccountService", true, false, false),
                    participant("LedgerService", true, true, false)
                ),
                policy,
                audit
            );

        uncertain.execute2PC();

        if (uncertain.getState() != TransactionState.IN_DOUBT) {
            throw new IllegalStateException("Expected IN_DOUBT");
        }

        uncertain.printReport();

        System.out.println("\nCASE 4: SAGA SUCCESS");

        TransactionCoordinator saga =
            new TransactionCoordinator(
                TransactionMode.SAGA,
                List.of(
                    participant("InventoryService", true, false, false),
                    participant("PaymentService", true, false, false),
                    participant("ShippingService", true, false, false)
                ),
                policy,
                audit
            );

        saga.executeSaga();
        saga.printReport();

        System.out.println("\nCASE 5: SAGA COMPENSATION");

        TransactionCoordinator failedSaga =
            new TransactionCoordinator(
                TransactionMode.SAGA,
                List.of(
                    participant("InventoryService", true, false, false),
                    participant("PaymentService", true, false, false),
                    participant("ShippingService", true, false, true)
                ),
                policy,
                audit
            );

        failedSaga.executeSaga();

        if (failedSaga.getState() != TransactionState.COMPENSATED) {
            throw new IllegalStateException(
                "Expected successful compensation"
            );
        }

        failedSaga.printReport();

        System.out.println("\nAll scenarios completed.");
    }
}
