// File: cpp/main.cpp

#include <algorithm>
#include <cmath>
#include <exception>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <unordered_map>

/*
 * C++17 implementation of defensive error handling.
 *
 * The program demonstrates:
 * - custom exception types,
 * - input validation,
 * - invariant preservation,
 * - RAII-friendly standard-library containers,
 * - explicit exception boundaries,
 * - and safe state mutation.
 */

class ApplicationError : public std::runtime_error {
public:
    explicit ApplicationError(const std::string& message)
        : std::runtime_error(message) {}
};

class ValidationError : public ApplicationError {
public:
    explicit ValidationError(const std::string& message)
        : ApplicationError(message) {}
};

class BusinessRuleError : public ApplicationError {
public:
    explicit BusinessRuleError(const std::string& message)
        : ApplicationError(message) {}
};

class ResourceNotFoundError : public ApplicationError {
public:
    explicit ResourceNotFoundError(const std::string& message)
        : ApplicationError(message) {}
};

struct Account {
    std::string id;
    std::string owner;
    double balance{0.0};

    Account(std::string account_id, std::string account_owner)
        : id(std::move(account_id)), owner(std::move(account_owner)) {
        if (id.empty()) {
            throw ValidationError("Account ID cannot be empty.");
        }

        if (owner.empty()) {
            throw ValidationError("Owner name cannot be empty.");
        }
    }
};

class AccountService {
private:
    static constexpr double MAX_TRANSACTION = 100000.0;
    std::unordered_map<std::string, Account> accounts_;

    static void validate_amount(double amount) {
        if (!std::isfinite(amount)) {
            throw ValidationError("Amount must be finite.");
        }

        if (amount <= 0.0) {
            throw ValidationError("Amount must be greater than zero.");
        }

        if (amount > MAX_TRANSACTION) {
            throw BusinessRuleError(
                "A transaction cannot exceed 100000.00."
            );
        }
    }

public:
    void create_account(
        const std::string& account_id,
        const std::string& owner
    ) {
        if (account_id.empty() || owner.empty()) {
            throw ValidationError("Account ID and owner are required.");
        }

        if (accounts_.contains(account_id)) {
            throw BusinessRuleError("Account already exists.");
        }

        accounts_.emplace(account_id, Account(account_id, owner));
    }

    Account& get_account(const std::string& account_id) {
        auto iterator = accounts_.find(account_id);

        if (iterator == accounts_.end()) {
            throw ResourceNotFoundError("Account was not found.");
        }

        return iterator->second;
    }

    double deposit(
        const std::string& account_id,
        double amount
    ) {
        validate_amount(amount);
        Account& account = get_account(account_id);

        account.balance += amount;
        return account.balance;
    }

    double withdraw(
        const std::string& account_id,
        double amount
    ) {
        validate_amount(amount);
        Account& account = get_account(account_id);

        if (amount > account.balance) {
            throw BusinessRuleError("Insufficient account balance.");
        }

        account.balance -= amount;
        return account.balance;
    }
};

int main() {
    try {
        AccountService service;

        std::cout << "Defensive Error Handling Demonstration\n";
        std::cout << "======================================\n";

        service.create_account("ACC-1001", "Atul");

        const double after_deposit =
            service.deposit("ACC-1001", 1250.50);

        std::cout << std::fixed << std::setprecision(2);
        std::cout << "After deposit: "
                  << after_deposit << '\n';

        const double after_withdrawal =
            service.withdraw("ACC-1001", 250.50);

        std::cout << "After withdrawal: "
                  << after_withdrawal << '\n';

        try {
            service.withdraw("ACC-1001", 5000.0);
        } catch (const ApplicationError& error) {
            std::cout << "Handled expected error: "
                      << error.what() << '\n';
        }

        try {
            service.deposit("ACC-1001", -10.0);
        } catch (const ApplicationError& error) {
            std::cout << "Handled expected error: "
                      << error.what() << '\n';
        }

        try {
            service.get_account("ACC-404");
        } catch (const ResourceNotFoundError& error) {
            std::cout << "Handled missing resource: "
                      << error.what() << '\n';
        }

        return 0;
    } catch (const ApplicationError& error) {
        std::cerr << "Application error: "
                  << error.what() << '\n';
        return 1;
    } catch (const std::exception& error) {
        std::cerr << "Unexpected standard-library error: "
                  << error.what() << '\n';
        return 2;
    }
}
