'use strict';

/*
 * Transaction processing model for ACID behavior.
 *
 * The implementation uses staged writes and optimistic version checks.
 * EventEmitter provides an event-driven transaction lifecycle without
 * requiring external packages.
 */

const { EventEmitter } = require('node:events');

const TransactionState = Object.freeze({
    ACTIVE: 'ACTIVE',
    COMMITTED: 'COMMITTED',
    ROLLED_BACK: 'ROLLED_BACK'
});

const IsolationLevel = Object.freeze({
    READ_UNCOMMITTED: 'READ_UNCOMMITTED',
    READ_COMMITTED: 'READ_COMMITTED',
    REPEATABLE_READ: 'REPEATABLE_READ',
    SERIALIZABLE: 'SERIALIZABLE'
});

class TransactionError extends Error {}
class TransactionConflict extends TransactionError {}
class TransactionStateError extends TransactionError {}

class Account {
    constructor(id, owner, balance) {
        if (!Number.isInteger(balance) || balance < 0) {
            throw new RangeError('Balance must be a non-negative integer.');
        }

        this.id = id;
        this.owner = owner;
        this.balance = balance;
        this.version = 0;
    }
}

class Transaction {
    constructor(id, isolation) {
        this.id = id;
        this.isolation = isolation;
        this.state = TransactionState.ACTIVE;
        this.readVersions = new Map();
        this.readValues = new Map();
        this.writes = new Map();
    }
}

class TransactionManager extends EventEmitter {
    constructor() {
        super();
        this.accounts = new Map();
        this.transactions = new Map();
        this.nextTransactionId = 1;
    }

    addAccount(id, owner, balance) {
        if (this.accounts.has(id)) {
            throw new TransactionError(`Account ${id} already exists.`);
        }
        this.accounts.set(id, new Account(id, owner, balance));
    }

    begin(isolation = IsolationLevel.READ_COMMITTED) {
        if (!Object.values(IsolationLevel).includes(isolation)) {
            throw new TransactionError('Unsupported isolation level.');
        }

        const tx = new Transaction(this.nextTransactionId++, isolation);
        this.transactions.set(tx.id, tx);
        this.emit('begin', tx);
        return tx;
    }

    getAccount(id) {
        const account = this.accounts.get(id);
        if (!account) {
            throw new TransactionError(`Account ${id} does not exist.`);
        }
        return account;
    }

    read(tx, accountId) {
        this.assertActive(tx);

        if (
            [IsolationLevel.REPEATABLE_READ, IsolationLevel.SERIALIZABLE]
                .includes(tx.isolation) &&
            tx.readValues.has(accountId)
        ) {
            return tx.readValues.get(accountId);
        }

        const account = this.getAccount(accountId);

        if (!tx.readVersions.has(accountId)) {
            tx.readVersions.set(accountId, account.version);
        }

        const value = tx.writes.has(accountId)
            ? tx.writes.get(accountId)
            : account.balance;

        if (
            [IsolationLevel.REPEATABLE_READ, IsolationLevel.SERIALIZABLE]
                .includes(tx.isolation)
        ) {
            tx.readValues.set(accountId, value);
        }

        return value;
    }

    write(tx, accountId, newBalance) {
        this.assertActive(tx);

        if (!Number.isInteger(newBalance) || newBalance < 0) {
            throw new RangeError('Account balance must be a non-negative integer.');
        }

        const account = this.getAccount(accountId);

        if (!tx.readVersions.has(accountId)) {
            tx.readVersions.set(accountId, account.version);
        }

        tx.writes.set(accountId, newBalance);
    }

    transfer(tx, sourceId, destinationId, amount) {
        if (!Number.isInteger(amount) || amount <= 0) {
            throw new RangeError('Transfer amount must be a positive integer.');
        }

        if (sourceId === destinationId) {
            throw new TransactionError('Source and destination must differ.');
        }

        const source = this.read(tx, sourceId);
        const destination = this.read(tx, destinationId);

        if (source < amount) {
            throw new TransactionError('Insufficient funds.');
        }

        this.write(tx, sourceId, source - amount);
        this.write(tx, destinationId, destination + amount);
    }

    commit(tx) {
        this.assertActive(tx);

        // Validate every object read by this transaction before publishing writes.
        for (const [accountId, expectedVersion] of tx.readVersions) {
            const account = this.getAccount(accountId);

            if (account.version !== expectedVersion) {
                tx.state = TransactionState.ROLLED_BACK;
                tx.writes.clear();
                this.emit('rollback', tx);

                throw new TransactionConflict(
                    `Concurrent modification detected for account ${accountId}.`
                );
            }
        }

        for (const [accountId, newBalance] of tx.writes) {
            if (newBalance < 0) {
                tx.state = TransactionState.ROLLED_BACK;
                tx.writes.clear();
                this.emit('rollback', tx);
                throw new TransactionConflict('Integrity constraint violated.');
            }
        }

        for (const [accountId, newBalance] of tx.writes) {
            const account = this.getAccount(accountId);
            account.balance = newBalance;
            account.version += 1;
        }

        tx.writes.clear();
        tx.state = TransactionState.COMMITTED;
        this.emit('commit', tx);
    }

    rollback(tx) {
        this.assertActive(tx);
        tx.writes.clear();
        tx.readVersions.clear();
        tx.readValues.clear();
        tx.state = TransactionState.ROLLED_BACK;
        this.emit('rollback', tx);
    }

    assertActive(tx) {
        if (!(tx instanceof Transaction) || tx.state !== TransactionState.ACTIVE) {
            throw new TransactionStateError('Transaction is not active.');
        }
    }

    totalBalance() {
        let total = 0;
        for (const account of this.accounts.values()) {
            total += account.balance;
        }
        return total;
    }

    printState() {
        for (const account of [...this.accounts.values()]
            .sort((a, b) => a.id - b.id)) {
            console.log(
                `Account ${account.id}: ${account.owner.padEnd(8)} ` +
                `balance=${String(account.balance).padStart(5)} ` +
                `version=${account.version}`
            );
        }
    }
}

async function main() {
    const manager = new TransactionManager();

    manager.addAccount(1, 'Alice', 1000);
    manager.addAccount(2, 'Bob', 1000);
    manager.addAccount(3, 'Carol', 1000);

    manager.on('commit', tx => {
        console.log(`Transaction ${tx.id} committed.`);
    });

    manager.on('rollback', tx => {
        console.log(`Transaction ${tx.id} rolled back.`);
    });

    console.log('--- Initial state ---');
    manager.printState();

    console.log('\n--- Atomic transfer ---');
    const initialTotal = manager.totalBalance();

    const transferTx = manager.begin(IsolationLevel.READ_COMMITTED);
    manager.transfer(transferTx, 1, 2, 250);
    manager.commit(transferTx);

    if (manager.totalBalance() !== initialTotal) {
        throw new Error('Atomicity invariant failed.');
    }

    console.log('\n--- Explicit rollback ---');
    const rollbackTx = manager.begin(IsolationLevel.READ_COMMITTED);
    manager.transfer(rollbackTx, 2, 3, 100);
    manager.rollback(rollbackTx);

    console.log('\n--- Conflict detection ---');
    const tx1 = manager.begin(IsolationLevel.REPEATABLE_READ);
    const original = manager.read(tx1, 1);

    const tx2 = manager.begin(IsolationLevel.READ_COMMITTED);
    manager.transfer(tx2, 1, 3, 50);
    manager.commit(tx2);

    manager.write(tx1, 1, original + 10);

    try {
        manager.commit(tx1);
    } catch (error) {
        if (!(error instanceof TransactionConflict)) {
            throw error;
        }
        console.log(`Conflict handled: ${error.message}`);
    }

    console.log('\n--- Final state ---');
    manager.printState();

    if (manager.totalBalance() !== 3000) {
        throw new Error('Conservation invariant failed.');
    }
}

main().catch(error => {
    console.error(`Fatal error: ${error.message}`);
    process.exitCode = 1;
});
