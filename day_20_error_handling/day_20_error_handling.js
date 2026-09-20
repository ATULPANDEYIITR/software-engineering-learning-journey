// File: web/app.js

"use strict";

/*
 * Client-side implementation of defensive programming.
 *
 * The browser is an untrusted boundary. Values from form controls are
 * validated before they are used by application logic.
 */

const state = {
    balance: 0,
};

class ValidationError extends Error {
    constructor(message) {
        super(message);
        this.name = "ValidationError";
    }
}

class BusinessRuleError extends Error {
    constructor(message) {
        super(message);
        this.name = "BusinessRuleError";
    }
}

function parsePositiveAmount(rawValue) {
    if (typeof rawValue !== "string" || rawValue.trim() === "") {
        throw new ValidationError("Amount is required.");
    }

    const amount = Number(rawValue);

    if (!Number.isFinite(amount)) {
        throw new ValidationError("Amount must be a valid number.");
    }

    if (amount <= 0) {
        throw new ValidationError("Amount must be greater than zero.");
    }

    if (amount > 100000) {
        throw new BusinessRuleError("A transaction cannot exceed 100000.");
    }

    return Math.round((amount + Number.EPSILON) * 100) / 100;
}

function deposit(rawValue) {
    const amount = parsePositiveAmount(rawValue);
    state.balance = Math.round((state.balance + amount) * 100) / 100;
    return state.balance;
}

function withdraw(rawValue) {
    const amount = parsePositiveAmount(rawValue);

    if (amount > state.balance) {
        throw new BusinessRuleError("Insufficient account balance.");
    }

    state.balance = Math.round((state.balance - amount) * 100) / 100;
    return state.balance;
}

function setMessage(message, isError = false) {
    const element = document.querySelector("#message");
    element.textContent = message;
    element.className = isError ? "message error" : "message success";
}

function updateBalance() {
    document.querySelector("#balance").textContent =
        state.balance.toFixed(2);
}

function executeOperation(operation) {
    const amountInput = document.querySelector("#amount");

    try {
        const newBalance = operation(amountInput.value);
        setMessage(`Operation completed. New balance: ${newBalance.toFixed(2)}`);
        updateBalance();
        amountInput.value = "";
    } catch (error) {
        if (error instanceof ValidationError ||
            error instanceof BusinessRuleError) {
            setMessage(error.message, true);
            return;
        }

        console.error("Unexpected client-side error:", error);
        setMessage("An unexpected error occurred.", true);
    }
}

document.querySelector("#deposit").addEventListener("click", () => {
    executeOperation(deposit);
});

document.querySelector("#withdraw").addEventListener("click", () => {
    executeOperation(withdraw);
});

updateBalance();
