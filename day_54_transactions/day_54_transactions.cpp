#include <algorithm>
#include <exception>
#include <iomanip>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

enum class IsolationLevel {
    ReadUncommitted,
    ReadCommitted,
    RepeatableRead,
    Serializable
};

enum class TransactionState {
    Active,
    Committed,
    RolledBack
};

class TransactionException : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

class ConflictException : public TransactionException {
public:
    using TransactionException::TransactionException;
};

struct Account {
    int id;
    std::string owner;
    long long balance;
    unsigned long long version{0};
};

struct Transaction {
    int id;
    IsolationLevel isolation;
    TransactionState state{TransactionState::Active};

    // Optimistic concurrency metadata.
    std::unordered_map<int, unsigned long long> readVersions;
    std::unordered_map<int, long long> writes;
    std::unordered_map<int, long long> repeatableReads;
};

class TransactionManager {
private:
    std::map<int, Account> accounts;
    int nextTransactionId{1};

    Account& account(int id) {
        auto it = accounts.find(id);
        if (it == accounts.end()) {
            throw TransactionException("Account does not exist.");
        }
        return it->second;
    }

    static void requireActive(const Transaction& tx) {
        if (tx.state != TransactionState::Active) {
            throw TransactionException("Transaction is no longer active.");
        }
    }

public:
    void addAccount(int id, std::string owner, long long balance) {
        if (balance < 0) {
            throw std::invalid_argument("Opening balance cannot be negative.");
        }

        if (accounts.contains(id)) {
            throw std::invalid_argument("Account already exists.");
        }

        accounts.emplace(id, Account{id, std::move(owner), balance});
    }

    Transaction begin(IsolationLevel isolation) {
        return Transaction{nextTransactionId++, isolation};
    }

    long long read(Transaction& tx, int id) {
        requireActive(tx);
        Account& acc = account(id);

        if (tx.isolation == IsolationLevel::RepeatableRead ||
            tx.isolation == IsolationLevel::Serializable) {
            auto cached = tx.repeatableReads.find(id);
            if (cached != tx.repeatableReads.end()) {
                return cached->second;
            }
        }

        tx.readVersions.try_emplace(id, acc.version);

        long long value = acc.balance;

        auto pending = tx.writes.find(id);
        if (pending != tx.writes.end()) {
            value = pending->second;
        }

        if (tx.isolation == IsolationLevel::RepeatableRead ||
            tx.isolation == IsolationLevel::Serializable) {
            tx.repeatableReads[id] = value;
        }

        return value;
    }

    void write(Transaction& tx, int id, long long balance) {
        requireActive(tx);

        if (balance < 0) {
            throw std::invalid_argument("Balance cannot be negative.");
        }

        Account& acc = account(id);
        tx.readVersions.try_emplace(id, acc.version);
        tx.writes[id] = balance;
    }

    void transfer(
        Transaction& tx,
        int sourceId,
        int destinationId,
        long long amount
    ) {
        if (amount <= 0) {
            throw std::invalid_argument("Transfer amount must be positive.");
        }

        if (sourceId == destinationId) {
            throw std::invalid_argument("Source and destination must differ.");
        }

        long long source = read(tx, sourceId);
        long long destination = read(tx, destinationId);

        if (source < amount) {
            throw TransactionException("Insufficient funds.");
        }

        write(tx, sourceId, source - amount);
        write(tx, destinationId, destination + amount);
    }

    void commit(Transaction& tx) {
        requireActive(tx);

        // First phase: validate the transaction's read set.
        for (const auto& [id, expectedVersion] : tx.readVersions) {
            const Account& acc = account(id);

            if (acc.version != expectedVersion) {
                tx.state = TransactionState::RolledBack;
                tx.writes.clear();

                throw ConflictException(
                    "Optimistic concurrency conflict on account " +
                    std::to_string(id)
                );
            }
        }

        // Second phase: validate staged state before publishing it.
        for (const auto& [id, newBalance] : tx.writes) {
            if (newBalance < 0) {
                tx.state = TransactionState::RolledBack;
                tx.writes.clear();
                throw ConflictException("Negative balance would be committed.");
            }
        }

        // Publish all writes as one logical commit.
        for (const auto& [id, newBalance] : tx.writes) {
            Account& acc = account(id);
            acc.balance = newBalance;
            ++acc.version;
        }

        tx.writes.clear();
        tx.state = TransactionState::Committed;
    }

    void rollback(Transaction& tx) {
        requireActive(tx);

        tx.writes.clear();
        tx.readVersions.clear();
        tx.repeatableReads.clear();
        tx.state = TransactionState::RolledBack;
    }

    long long totalBalance() const {
        long long total = 0;
        for (const auto& [id, acc] : accounts) {
            total += acc.balance;
        }
        return total;
    }

    void printAccounts() const {
        for (const auto& [id, acc] : accounts) {
            std::cout
                << "Account " << id
                << ": " << std::left << std::setw(10) << acc.owner
                << " balance=" << std::right << std::setw(5) << acc.balance
                << " version=" << acc.version << '\n';
        }
    }
};

int main() {
    try {
        TransactionManager manager;

        manager.addAccount(1, "Alice", 1000);
        manager.addAccount(2, "Bob", 1000);
        manager.addAccount(3, "Carol", 1000);

        std::cout << "--- Initial state ---\n";
        manager.printAccounts();

        std::cout << "\n--- Atomic transfer ---\n";
        const long long initialTotal = manager.totalBalance();

        Transaction transfer =
            manager.begin(IsolationLevel::ReadCommitted);

        manager.transfer(transfer, 1, 2, 250);
        manager.commit(transfer);

        if (manager.totalBalance() != initialTotal) {
            throw TransactionException("Atomicity invariant failed.");
        }

        std::cout << "Transfer committed without changing total funds.\n";

        std::cout << "\n--- Rollback ---\n";
        Transaction aborted =
            manager.begin(IsolationLevel::ReadCommitted);

        manager.transfer(aborted, 2, 3, 100);
        manager.rollback(aborted);

        std::cout << "Uncommitted changes were discarded.\n";

        std::cout << "\n--- Concurrent conflict ---\n";
        Transaction first =
            manager.begin(IsolationLevel::RepeatableRead);

        long long original = manager.read(first, 1);

        Transaction second =
            manager.begin(IsolationLevel::ReadCommitted);

        manager.transfer(second, 1, 3, 50);
        manager.commit(second);

        manager.write(first, 1, original + 10);

        try {
            manager.commit(first);
        } catch (const ConflictException& ex) {
            std::cout << "Conflict detected: " << ex.what() << '\n';
        }

        std::cout << "\n--- Final state ---\n";
        manager.printAccounts();

        if (manager.totalBalance() != 3000) {
            throw TransactionException(
                "Conservation invariant failed."
            );
        }

        std::cout << "\nAll transaction invariants passed.\n";
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "Fatal error: " << ex.what() << '\n';
        return 1;
    }
}
