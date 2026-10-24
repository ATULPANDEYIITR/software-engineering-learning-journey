import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.Objects;

public class TransactionDemo {

    enum IsolationLevel {
        READ_UNCOMMITTED,
        READ_COMMITTED,
        REPEATABLE_READ,
        SERIALIZABLE
    }

    enum TransactionState {
        ACTIVE,
        COMMITTED,
        ROLLED_BACK
    }

    static class TransactionException extends RuntimeException {
        TransactionException(String message) {
            super(message);
        }
    }

    static final class TransactionConflict extends TransactionException {
        TransactionConflict(String message) {
            super(message);
        }
    }

    static final class Account {
        private final long id;
        private final String owner;
        private long balance;
        private long version;

        Account(long id, String owner, long balance) {
            if (balance < 0) {
                throw new IllegalArgumentException(
                    "Balance cannot be negative."
                );
            }

            this.id = id;
            this.owner = Objects.requireNonNull(owner);
            this.balance = balance;
        }
    }

    static final class Transaction {
        private final long id;
        private final IsolationLevel isolation;
        private TransactionState state = TransactionState.ACTIVE;

        private final Map<Long, Long> readVersions = new HashMap<>();
        private final Map<Long, Long> repeatableReads = new HashMap<>();
        private final Map<Long, Long> writes = new HashMap<>();

        Transaction(long id, IsolationLevel isolation) {
            this.id = id;
            this.isolation = Objects.requireNonNull(isolation);
        }
    }

    static final class RepositoryService {
        private final Map<Long, Account> accounts = new HashMap<>();
        private long nextTransactionId = 1;

        void addAccount(long id, String owner, long balance) {
            if (accounts.containsKey(id)) {
                throw new IllegalArgumentException(
                    "Account already exists."
                );
            }

            accounts.put(id, new Account(id, owner, balance));
        }

        Transaction begin(IsolationLevel isolation) {
            return new Transaction(nextTransactionId++, isolation);
        }

        private Account account(long id) {
            Account account = accounts.get(id);

            if (account == null) {
                throw new TransactionException(
                    "Unknown account: " + id
                );
            }

            return account;
        }

        private void requireActive(Transaction tx) {
            if (tx.state != TransactionState.ACTIVE) {
                throw new TransactionException(
                    "Transaction is no longer active."
                );
            }
        }

        long read(Transaction tx, long accountId) {
            requireActive(tx);

            if ((tx.isolation == IsolationLevel.REPEATABLE_READ
                    || tx.isolation == IsolationLevel.SERIALIZABLE)
                    && tx.repeatableReads.containsKey(accountId)) {
                return tx.repeatableReads.get(accountId);
            }

            Account account = account(accountId);
            tx.readVersions.putIfAbsent(accountId, account.version);

            long value = tx.writes.getOrDefault(
                accountId,
                account.balance
            );

            if (tx.isolation == IsolationLevel.REPEATABLE_READ
                    || tx.isolation == IsolationLevel.SERIALIZABLE) {
                tx.repeatableReads.put(accountId, value);
            }

            return value;
        }

        void write(Transaction tx, long accountId, long newBalance) {
            requireActive(tx);

            if (newBalance < 0) {
                throw new IllegalArgumentException(
                    "Balance cannot be negative."
                );
            }

            Account account = account(accountId);
            tx.readVersions.putIfAbsent(accountId, account.version);
            tx.writes.put(accountId, newBalance);
        }

        void transfer(
            Transaction tx,
            long sourceId,
            long destinationId,
            long amount
        ) {
            if (amount <= 0) {
                throw new IllegalArgumentException(
                    "Transfer amount must be positive."
                );
            }

            if (sourceId == destinationId) {
                throw new IllegalArgumentException(
                    "Source and destination must differ."
                );
            }

            long source = read(tx, sourceId);
            long destination = read(tx, destinationId);

            if (source < amount) {
                throw new TransactionException("Insufficient funds.");
            }

            write(tx, sourceId, source - amount);
            write(tx, destinationId, destination + amount);
        }

        void commit(Transaction tx) {
            requireActive(tx);

            // Validate the read set before making any changes visible.
            for (Map.Entry<Long, Long> entry :
                    tx.readVersions.entrySet()) {

                Account account = account(entry.getKey());

                if (account.version != entry.getValue()) {
                    rollbackAfterFailure(tx);
                    throw new TransactionConflict(
                        "Concurrent modification detected for account "
                            + entry.getKey()
                    );
                }
            }

            for (long balance : tx.writes.values()) {
                if (balance < 0) {
                    rollbackAfterFailure(tx);
                    throw new TransactionConflict(
                        "Negative balance detected."
                    );
                }
            }

            for (Map.Entry<Long, Long> entry :
                    tx.writes.entrySet()) {

                Account account = account(entry.getKey());
                account.balance = entry.getValue();
                account.version++;
            }

            tx.writes.clear();
            tx.state = TransactionState.COMMITTED;
        }

        private void rollbackAfterFailure(Transaction tx) {
            tx.writes.clear();
            tx.state = TransactionState.ROLLED_BACK;
        }

        void rollback(Transaction tx) {
            requireActive(tx);

            tx.writes.clear();
            tx.readVersions.clear();
            tx.repeatableReads.clear();
            tx.state = TransactionState.ROLLED_BACK;
        }

        long totalBalance() {
            return accounts.values()
                .stream()
                .mapToLong(account -> account.balance)
                .sum();
        }

        Map<Long, Long> balances() {
            Map<Long, Long> result = new HashMap<>();

            for (Account account : accounts.values()) {
                result.put(account.id, account.balance);
            }

            return Collections.unmodifiableMap(result);
        }

        void printAccounts() {
            accounts.values()
                .stream()
                .sorted((a, b) -> Long.compare(a.id, b.id))
                .forEach(account ->
                    System.out.printf(
                        "Account %d: %-8s balance=%5d version=%d%n",
                        account.id,
                        account.owner,
                        account.balance,
                        account.version
                    )
                );
        }
    }

    public static void main(String[] args) {
        RepositoryService service = new RepositoryService();

        service.addAccount(1, "Alice", 1000);
        service.addAccount(2, "Bob", 1000);
        service.addAccount(3, "Carol", 1000);

        System.out.println("--- Initial state ---");
        service.printAccounts();

        System.out.println("\n--- Commit ---");
        long initialTotal = service.totalBalance();

        Transaction transfer =
            service.begin(IsolationLevel.READ_COMMITTED);

        service.transfer(transfer, 1, 2, 250);
        service.commit(transfer);

        if (service.totalBalance() != initialTotal) {
            throw new AssertionError("Atomicity invariant failed.");
        }

        System.out.println("Transfer committed.");

        System.out.println("\n--- Rollback ---");
        Transaction cancelled =
            service.begin(IsolationLevel.READ_COMMITTED);

        service.transfer(cancelled, 2, 3, 100);
        service.rollback(cancelled);

        System.out.println("Transfer rolled back.");

        System.out.println("\n--- Conflict detection ---");
        Transaction first =
            service.begin(IsolationLevel.REPEATABLE_READ);

        long original = service.read(first, 1);

        Transaction second =
            service.begin(IsolationLevel.READ_COMMITTED);

        service.transfer(second, 1, 3, 50);
        service.commit(second);

        service.write(first, 1, original + 10);

        try {
            service.commit(first);
        } catch (TransactionConflict exception) {
            System.out.println(
                "Conflict handled: " + exception.getMessage()
            );
        }

        System.out.println("\n--- Final state ---");
        service.printAccounts();

        if (service.totalBalance() != 3000) {
            throw new AssertionError(
                "Conservation invariant failed."
            );
        }

        System.out.println("\nFinal balances: " + service.balances());
    }
}
