"use strict";

/*
 * DESIGN PATTERNS III
 * Repository, Facade, Decorator
 *
 * This Node.js program models a subscription-management platform.
 * The three patterns solve different architectural problems:
 *
 * Repository  -> separates domain logic from data storage.
 * Facade       -> exposes a simple workflow over multiple services.
 * Decorator    -> adds behavior around an existing service without changing it.
 *
 * JavaScript-specific features used here include classes, private fields,
 * Maps, async functions, Promises, event-driven notifications, and
 * function decorators implemented through higher-order functions.
 */

// ============================================================
// Repository Pattern
// ============================================================

class Subscription {
    constructor(id, customerId, plan, monthlyPrice, active = true) {
        if (!Number.isInteger(id) || id <= 0) {
            throw new Error("Subscription ID must be a positive integer.");
        }

        if (!customerId || !customerId.trim()) {
            throw new Error("Customer ID is required.");
        }

        if (!plan || !plan.trim()) {
            throw new Error("Plan is required.");
        }

        if (!Number.isFinite(monthlyPrice) || monthlyPrice <= 0) {
            throw new Error("Monthly price must be positive.");
        }

        this.id = id;
        this.customerId = customerId.trim();
        this.plan = plan.trim();
        this.monthlyPrice = Number(monthlyPrice.toFixed(2));
        this.active = active;
    }
}

class SubscriptionRepository {
    async save(subscription) {
        throw new Error("save() must be implemented by a concrete repository.");
    }

    async findById(id) {
        throw new Error("findById() must be implemented.");
    }

    async findByCustomer(customerId) {
        throw new Error("findByCustomer() must be implemented.");
    }

    async remove(id) {
        throw new Error("remove() must be implemented.");
    }
}

class MemorySubscriptionRepository extends SubscriptionRepository {
    #records = new Map();

    async save(subscription) {
        this.#records.set(subscription.id, subscription);
        return subscription;
    }

    async findById(id) {
        return this.#records.get(id) ?? null;
    }

    async findByCustomer(customerId) {
        return [...this.#records.values()].filter(
            subscription => subscription.customerId === customerId
        );
    }

    async remove(id) {
        return this.#records.delete(id);
    }
}

// ============================================================
// Repository-driven domain service
// ============================================================

class SubscriptionService {
    constructor(repository) {
        this.repository = repository;
    }

    async createSubscription(id, customerId, plan, price) {
        const existing = await this.repository.findById(id);

        if (existing) {
            throw new Error(`Subscription ${id} already exists.`);
        }

        const subscription = new Subscription(
            id,
            customerId,
            plan,
            price
        );

        return this.repository.save(subscription);
    }

    async cancelSubscription(id) {
        const subscription = await this.repository.findById(id);

        if (!subscription) {
            throw new Error(`Subscription ${id} was not found.`);
        }

        if (!subscription.active) {
            throw new Error(`Subscription ${id} is already inactive.`);
        }

        subscription.active = false;
        await this.repository.save(subscription);
        return subscription;
    }
}

// ============================================================
// Facade Pattern
// ============================================================

class BillingService {
    async authorize(customerId, amount) {
        if (!customerId) {
            throw new Error("Billing requires a customer ID.");
        }

        if (!Number.isFinite(amount) || amount <= 0) {
            throw new Error("Billing amount must be positive.");
        }

        return {
            authorizationId: `AUTH-${customerId}-${Math.floor(amount * 100)}`,
            amount
        };
    }
}

class ProvisioningService {
    async provision(customerId, plan) {
        if (!customerId || !plan) {
            throw new Error("Provisioning requires customer and plan.");
        }

        return {
            resourceId: `RESOURCE-${customerId}-${plan.toUpperCase()}`,
            state: "PROVISIONED"
        };
    }
}

class EmailService {
    async sendWelcome(customerId, plan) {
        return {
            customerId,
            message: `Welcome email queued for ${customerId} on ${plan}.`
        };
    }
}

class SubscriptionFacade {
    constructor(subscriptionService, billing, provisioning, email) {
        this.subscriptionService = subscriptionService;
        this.billing = billing;
        this.provisioning = provisioning;
        this.email = email;
    }

    /*
     * The facade controls the workflow order. The caller does not need
     * to coordinate persistence, billing, provisioning, and notification.
     */
    async onboardCustomer({
        subscriptionId,
        customerId,
        plan,
        monthlyPrice
    }) {
        const subscription =
            await this.subscriptionService.createSubscription(
                subscriptionId,
                customerId,
                plan,
                monthlyPrice
            );

        try {
            const billingResult =
                await this.billing.authorize(customerId, monthlyPrice);

            const resource =
                await this.provisioning.provision(customerId, plan);

            const email =
                await this.email.sendWelcome(customerId, plan);

            return {
                subscription,
                billingResult,
                resource,
                email,
                state: "ACTIVE"
            };
        } catch (error) {
            // The repository entry is removed because this example models
            // a compensating action when downstream onboarding fails.
            await this.subscriptionService.repository.remove(subscriptionId);
            throw error;
        }
    }
}

// ============================================================
// Decorator Pattern
// ============================================================

class SubscriptionQuery {
    async execute() {
        throw new Error("execute() must be implemented.");
    }
}

class RepositorySubscriptionQuery extends SubscriptionQuery {
    constructor(repository) {
        super();
        this.repository = repository;
    }

    async execute(customerId) {
        return this.repository.findByCustomer(customerId);
    }
}

class SubscriptionQueryDecorator extends SubscriptionQuery {
    constructor(wrapped) {
        super();
        this.wrapped = wrapped;
    }

    async execute(customerId) {
        return this.wrapped.execute(customerId);
    }
}

class LoggingQueryDecorator extends SubscriptionQueryDecorator {
    async execute(customerId) {
        console.log(`QUERY start customer=${customerId}`);

        try {
            const result = await this.wrapped.execute(customerId);
            console.log(`QUERY success count=${result.length}`);
            return result;
        } catch (error) {
            console.error(`QUERY failure: ${error.message}`);
            throw error;
        }
    }
}

class TimingQueryDecorator extends SubscriptionQueryDecorator {
    async execute(customerId) {
        const started = process.hrtime.bigint();

        try {
            return await this.wrapped.execute(customerId);
        } finally {
            const elapsedNs = process.hrtime.bigint() - started;
            console.log(`QUERY duration=${Number(elapsedNs) / 1_000_000} ms`);
        }
    }
}

class ActiveOnlyQueryDecorator extends SubscriptionQueryDecorator {
    async execute(customerId) {
        const subscriptions = await this.wrapped.execute(customerId);
        return subscriptions.filter(subscription => subscription.active);
    }
}

// ============================================================
// JavaScript function decorator
// ============================================================

function withRetry(operation, attempts = 3) {
    if (!Number.isInteger(attempts) || attempts < 1) {
        throw new Error("Retry attempts must be a positive integer.");
    }

    return async function decoratedOperation(...args) {
        let lastError;

        for (let attempt = 1; attempt <= attempts; attempt++) {
            try {
                return await operation(...args);
            } catch (error) {
                lastError = error;

                if (attempt < attempts) {
                    await new Promise(resolve => setTimeout(resolve, 10));
                }
            }
        }

        throw lastError;
    };
}

// ============================================================
// Event-driven behavior
// ============================================================

class SubscriptionEventBus {
    #listeners = new Map();

    on(eventName, listener) {
        if (!this.#listeners.has(eventName)) {
            this.#listeners.set(eventName, []);
        }

        this.#listeners.get(eventName).push(listener);
    }

    emit(eventName, payload) {
        const listeners = this.#listeners.get(eventName) ?? [];

        for (const listener of listeners) {
            listener(payload);
        }
    }
}

// ============================================================
// Demonstration
// ============================================================

async function main() {
    console.log("DESIGN PATTERNS III: REPOSITORY, FACADE, DECORATOR");

    const repository = new MemorySubscriptionRepository();
    const subscriptionService = new SubscriptionService(repository);

    await subscriptionService.createSubscription(
        1,
        "CUS-100",
        "PRO",
        49.99
    );

    await subscriptionService.createSubscription(
        2,
        "CUS-100",
        "TEAM",
        99.99
    );

    await subscriptionService.createSubscription(
        3,
        "CUS-200",
        "BASIC",
        19.99
    );

    console.log("\nRepository result:");
    console.log(await repository.findByCustomer("CUS-100"));

    const facade = new SubscriptionFacade(
        subscriptionService,
        new BillingService(),
        new ProvisioningService(),
        new EmailService()
    );

    console.log("\nFacade workflow:");

    const onboarding = await facade.onboardCustomer({
        subscriptionId: 4,
        customerId: "CUS-300",
        plan: "ENTERPRISE",
        monthlyPrice: 499.99
    });

    console.log(onboarding);

    const baseQuery = new RepositorySubscriptionQuery(repository);

    const decoratedQuery =
        new LoggingQueryDecorator(
            new TimingQueryDecorator(
                new ActiveOnlyQueryDecorator(baseQuery)
            )
        );

    console.log("\nDecorator pipeline:");
    console.log(await decoratedQuery.execute("CUS-100"));

    const eventBus = new SubscriptionEventBus();

    eventBus.on("subscription.cancelled", payload => {
        console.log(
            `EVENT cancellation received for subscription ${payload.id}`
        );
    });

    const cancellation =
        await subscriptionService.cancelSubscription(3);

    eventBus.emit("subscription.cancelled", cancellation);

    console.log("\nRetry decorator:");

    let invocationCount = 0;

    const unreliableOperation = withRetry(async () => {
        invocationCount++;

        if (invocationCount < 3) {
            throw new Error("Temporary service failure.");
        }

        return "Operation succeeded after retry.";
    });

    console.log(await unreliableOperation());

    console.log("\nEdge-case validation:");

    try {
        await subscriptionService.createSubscription(
            1,
            "CUS-999",
            "BASIC",
            10
        );
    } catch (error) {
        console.log(`Duplicate protection: ${error.message}`);
    }

    try {
        await subscriptionService.cancelSubscription(999);
    } catch (error) {
        console.log(`Missing entity protection: ${error.message}`);
    }
}

main().catch(error => {
    console.error(`Application failure: ${error.message}`);
    process.exitCode = 1;
});
