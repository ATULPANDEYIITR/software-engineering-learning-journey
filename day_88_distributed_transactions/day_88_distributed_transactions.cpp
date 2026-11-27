#include <algorithm>
#include <chrono>
#include <exception>
#include <functional>
#include <iostream>
#include <map>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

using namespace std;

enum class TransactionMode {
    TWO_PHASE_COMMIT,
    SAGA
};

enum class TransactionState {
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
};

enum class ParticipantState {
    ACTIVE,
    PREPARED,
    COMMITTED,
    ABORTED
};

string toString(TransactionState state) {
    static const map<TransactionState, string> names = {
        {TransactionState::CREATED, "CREATED"},
        {TransactionState::PREPARING, "PREPARING"},
        {TransactionState::PREPARED, "PREPARED"},
        {TransactionState::COMMITTING, "COMMITTING"},
        {TransactionState::COMMITTED, "COMMITTED"},
        {TransactionState::ABORTING, "ABORTING"},
        {TransactionState::ABORTED, "ABORTED"},
        {TransactionState::COMPENSATING, "COMPENSATING"},
        {TransactionState::COMPENSATED, "COMPENSATED"},
        {TransactionState::IN_DOUBT, "IN_DOUBT"},
        {TransactionState::FAILED, "FAILED"}
    };

    return names.at(state);
}

string toString(ParticipantState state) {
    static const map<ParticipantState, string> names = {
        {ParticipantState::ACTIVE, "ACTIVE"},
        {ParticipantState::PREPARED, "PREPARED"},
        {ParticipantState::COMMITTED, "COMMITTED"},
        {ParticipantState::ABORTED, "ABORTED"}
    };

    return names.at(state);
}

struct AuditEvent {
    string participant;
    string action;
    string details;
};

class AuditLog {
private:
    vector<AuditEvent> events;

public:
    void record(
        const string& participant,
        const string& action,
        const string& details
    ) {
        events.push_back({
            participant,
            action,
            details
        });

        cout << "[" << action << "] "
             << participant << ": "
             << details << '\n';
    }

    const vector<AuditEvent>& getEvents() const {
        return events;
    }
};

class Participant {
private:
    string name;
    ParticipantState state = ParticipantState::ACTIVE;
    bool canPrepare;
    bool commitFailure;
    bool executionFailure;
    bool compensationFailure;

public:
    Participant(
        string participantName,
        bool prepareAccepted = true,
        bool failCommit = false,
        bool failExecution = false,
        bool failCompensation = false
    )
        : name(move(participantName)),
          canPrepare(prepareAccepted),
          commitFailure(failCommit),
          executionFailure(failExecution),
          compensationFailure(failCompensation) {

        if (name.empty()) {
            throw invalid_argument(
                "Participant name cannot be empty"
            );
        }
    }

    const string& getName() const {
        return name;
    }

    ParticipantState getState() const {
        return state;
    }

    bool prepare() {
        if (state != ParticipantState::ACTIVE) {
            throw logic_error("Invalid prepare transition");
        }

        if (!canPrepare) {
            return false;
        }

        state = ParticipantState::PREPARED;
        return true;
    }

    void commit() {
        if (state != ParticipantState::PREPARED) {
            throw logic_error("Participant is not prepared");
        }

        if (commitFailure) {
            throw runtime_error("Commit acknowledgement unavailable");
        }

        state = ParticipantState::COMMITTED;
    }

    void abort() {
        if (state == ParticipantState::COMMITTED) {
            throw logic_error(
                "Cannot abort a committed participant"
            );
        }

        if (state != ParticipantState::ABORTED) {
            state = ParticipantState::ABORTED;
        }
    }

    void execute() {
        if (state != ParticipantState::ACTIVE) {
            throw logic_error("Invalid saga execution state");
        }

        if (executionFailure) {
            throw runtime_error("Local business operation failed");
        }

        state = ParticipantState::COMMITTED;
    }

    void compensate() {
        if (state != ParticipantState::COMMITTED) {
            throw logic_error("No completed operation to compensate");
        }

        if (compensationFailure) {
            throw runtime_error("Compensation operation failed");
        }

        state = ParticipantState::ABORTED;
    }
};

class DistributedTransaction {
private:
    string transactionId;
    TransactionMode mode;
    TransactionState state = TransactionState::CREATED;
    vector<Participant> participants;
    AuditLog audit;

    void transition(TransactionState next) {
        state = next;

        audit.record(
            "COORDINATOR",
            "STATE_CHANGE",
            toString(next)
        );
    }

    void abortParticipants() {
        bool failed = false;

        for (auto& participant : participants) {
            if (participant.getState() == ParticipantState::COMMITTED) {
                continue;
            }

            try {
                participant.abort();

                audit.record(
                    participant.getName(),
                    "ABORT",
                    "Participant aborted"
                );

            } catch (const exception& error) {
                failed = true;

                audit.record(
                    participant.getName(),
                    "ABORT_FAILURE",
                    error.what()
                );
            }
        }

        transition(
            failed
                ? TransactionState::IN_DOUBT
                : TransactionState::ABORTED
        );
    }

public:
    DistributedTransaction(
        string id,
        TransactionMode transactionMode,
        vector<Participant> transactionParticipants
    )
        : transactionId(move(id)),
          mode(transactionMode),
          participants(move(transactionParticipants)) {

        if (transactionId.empty()) {
            throw invalid_argument("Transaction ID is required");
        }

        if (participants.empty()) {
            throw invalid_argument(
                "At least one participant is required"
            );
        }

        set<string> names;

        for (const auto& participant : participants) {
            if (!names.insert(participant.getName()).second) {
                throw invalid_argument(
                    "Duplicate participant name"
                );
            }
        }
    }

    bool execute2PC() {
        if (mode != TransactionMode::TWO_PHASE_COMMIT) {
            throw logic_error("Incorrect transaction mode");
        }

        if (state != TransactionState::CREATED) {
            throw logic_error("Transaction already started");
        }

        transition(TransactionState::PREPARING);

        bool allPrepared = true;

        // Phase 1: Prepare and collect votes.
        for (auto& participant : participants) {
            try {
                bool accepted = participant.prepare();

                audit.record(
                    participant.getName(),
                    accepted ? "VOTE_YES" : "VOTE_NO",
                    accepted
                        ? "Prepared"
                        : "Participant rejected transaction"
                );

                if (!accepted) {
                    allPrepared = false;
                }

            } catch (const exception& error) {
                allPrepared = false;

                audit.record(
                    participant.getName(),
                    "PREPARE_FAILURE",
                    error.what()
                );
            }
        }

        if (!allPrepared) {
            transition(TransactionState::ABORTING);
            abortParticipants();
            return false;
        }

        transition(TransactionState::PREPARED);

        // A production coordinator must durably record COMMIT
        // before transmitting the decision.
        transition(TransactionState::COMMITTING);

        bool commitUncertain = false;

        // Phase 2: Broadcast commit.
        for (auto& participant : participants) {
            try {
                participant.commit();

                audit.record(
                    participant.getName(),
                    "COMMIT_ACK",
                    "Local transaction committed"
                );

            } catch (const exception& error) {
                commitUncertain = true;

                audit.record(
                    participant.getName(),
                    "COMMIT_UNCERTAIN",
                    error.what()
                );
            }
        }

        if (commitUncertain) {
            // Committed participants cannot be safely rolled back.
            // Recovery must retry the durable commit decision.
            transition(TransactionState::IN_DOUBT);
            return false;
        }

        transition(TransactionState::COMMITTED);
        return true;
    }

    bool executeSaga() {
        if (mode != TransactionMode::SAGA) {
            throw logic_error("Incorrect transaction mode");
        }

        if (state != TransactionState::CREATED) {
            throw logic_error("Transaction already started");
        }

        vector<size_t> completed;

        try {
            // Each participant performs its own local transaction.
            for (size_t i = 0; i < participants.size(); ++i) {
                participants[i].execute();

                completed.push_back(i);

                audit.record(
                    participants[i].getName(),
                    "LOCAL_COMMIT",
                    "Saga step completed"
                );
            }

            transition(TransactionState::COMMITTED);
            return true;

        } catch (const exception& error) {
            audit.record(
                "COORDINATOR",
                "SAGA_FAILURE",
                error.what()
            );
        }

        transition(TransactionState::COMPENSATING);

        bool compensationFailed = false;

        // Reverse order maintains dependency consistency.
        for (auto it = completed.rbegin();
             it != completed.rend();
             ++it) {

            Participant& participant = participants[*it];

            try {
                participant.compensate();

                audit.record(
                    participant.getName(),
                    "COMPENSATED",
                    "Business effect reversed"
                );

            } catch (const exception& error) {
                compensationFailed = true;

                audit.record(
                    participant.getName(),
                    "COMPENSATION_FAILURE",
                    error.what()
                );
            }
        }

        transition(
            compensationFailed
                ? TransactionState::FAILED
                : TransactionState::COMPENSATED
        );

        return false;
    }

    void report() const {
        cout << "\nTRANSACTION REPORT\n";
        cout << "Transaction: " << transactionId << '\n';
        cout << "Mode: "
             << (mode == TransactionMode::SAGA ? "SAGA" : "2PC")
             << '\n';

        cout << "State: " << toString(state) << '\n';

        cout << "\nPARTICIPANTS\n";

        for (const auto& participant : participants) {
            cout << participant.getName()
                 << " -> "
                 << toString(participant.getState())
                 << '\n';
        }

        cout << "\nAUDIT EVENT COUNT: "
             << audit.getEvents().size()
             << '\n';
    }

    TransactionState getState() const {
        return state;
    }
};

void demonstrate2PC() {
    cout << "\n========== 2PC SUCCESS ==========\n";

    DistributedTransaction transaction(
        "TX-1001",
        TransactionMode::TWO_PHASE_COMMIT,
        {
            Participant("InventoryService"),
            Participant("PaymentService"),
            Participant("OrderService")
        }
    );

    if (!transaction.execute2PC()) {
        throw runtime_error("Expected 2PC success");
    }

    transaction.report();
}

void demonstrate2PCFailure() {
    cout << "\n========== 2PC REJECTION ==========\n";

    DistributedTransaction transaction(
        "TX-1002",
        TransactionMode::TWO_PHASE_COMMIT,
        {
            Participant("InventoryService"),
            Participant("PaymentService", false),
            Participant("OrderService")
        }
    );

    if (transaction.execute2PC()) {
        throw runtime_error("Expected 2PC abort");
    }

    if (transaction.getState() != TransactionState::ABORTED) {
        throw runtime_error("Unexpected transaction state");
    }

    transaction.report();
}

void demonstrateUncertainCommit() {
    cout << "\n========== UNCERTAIN COMMIT ==========\n";

    DistributedTransaction transaction(
        "TX-1003",
        TransactionMode::TWO_PHASE_COMMIT,
        {
            Participant("AccountService"),
            Participant("LedgerService", true, true)
        }
    );

    if (transaction.execute2PC()) {
        throw runtime_error("Expected uncertain outcome");
    }

    if (transaction.getState() != TransactionState::IN_DOUBT) {
        throw runtime_error("Expected IN_DOUBT");
    }

    transaction.report();
}

void demonstrateSaga() {
    cout << "\n========== SAGA SUCCESS ==========\n";

    DistributedTransaction transaction(
        "TX-2001",
        TransactionMode::SAGA,
        {
            Participant("ReserveInventory"),
            Participant("ChargePayment"),
            Participant("CreateShipment")
        }
    );

    transaction.executeSaga();
    transaction.report();
}

void demonstrateSagaCompensation() {
    cout << "\n========== SAGA COMPENSATION ==========\n";

    DistributedTransaction transaction(
        "TX-2002",
        TransactionMode::SAGA,
        {
            Participant("ReserveInventory"),
            Participant("ChargePayment"),
            Participant("CreateShipment", true, false, true)
        }
    );

    if (transaction.executeSaga()) {
        throw runtime_error("Expected saga failure");
    }

    if (transaction.getState() != TransactionState::COMPENSATED) {
        throw runtime_error("Expected compensation");
    }

    transaction.report();
}

int main() {
    try {
        demonstrate2PC();
        demonstrate2PCFailure();
        demonstrateUncertainCommit();
        demonstrateSaga();
        demonstrateSagaCompensation();

        cout << "\nAll scenarios completed.\n";

    } catch (const exception& error) {
        cerr << "Fatal error: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
