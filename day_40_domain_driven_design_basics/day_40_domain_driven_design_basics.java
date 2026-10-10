import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;

/*
 * Java 17 DDD case study: enterprise subscription domain.
 *
 * The domain distinguishes:
 *
 * Value objects:
 *   CustomerId, PlanCode, Money and EmailAddress.
 *
 * Entities:
 *   Subscription has identity and a lifecycle.
 *
 * Aggregate:
 *   Subscription is the aggregate root and controls SubscriptionItem
 *   entities. The root enforces state-transition and plan invariants.
 *
 * Domain services:
 *   SubscriptionPolicy evaluates whether a subscription is eligible
 *   for activation without becoming part of the entity's identity.
 *
 * The program uses Java records for immutable value objects, enums for
 * explicit domain states, interfaces for policy abstractions, collections
 * for aggregate internals, and exceptions for invalid domain operations.
 */

public class DomainDrivenDesignBasics {

    enum SubscriptionStatus {
        PENDING,
        ACTIVE,
        SUSPENDED,
        CANCELLED
    }

    record CustomerId(UUID value) {
        CustomerId {
            Objects.requireNonNull(value, "Customer ID is required");
        }

        static CustomerId create() {
            return new CustomerId(UUID.randomUUID());
        }
    }

    record PlanCode(String value) {
        PlanCode {
            if (value == null || value.isBlank()) {
                throw new DomainException("Plan code cannot be empty");
            }

            value = value.trim().toUpperCase();

            if (!value.matches("[A-Z0-9-]{2,30}")) {
                throw new DomainException("Invalid plan code");
            }
        }
    }

    record EmailAddress(String value) {
        EmailAddress {
            if (value == null || value.isBlank()) {
                throw new DomainException("Email address cannot be empty");
            }

            value = value.trim().toLowerCase();

            if (!value.matches("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$")) {
                throw new DomainException("Invalid email address");
            }
        }
    }

    record Money(long minorUnits, String currency) {
        Money {
            if (minorUnits < 0) {
                throw new DomainException("Money cannot be negative");
            }

            if (currency == null || !currency.matches("[A-Z]{3}")) {
                throw new DomainException("Currency must be a three-letter code");
            }
        }

        Money add(Money other) {
            if (!currency.equals(other.currency)) {
                throw new DomainException("Currencies do not match");
            }

            return new Money(minorUnits + other.minorUnits, currency);
        }

        Money multiply(int quantity) {
            if (quantity < 0) {
                throw new DomainException("Quantity cannot be negative");
            }

            return new Money(minorUnits * quantity, currency);
        }

        @Override
        public String toString() {
            return currency + " " + String.format(
                java.util.Locale.ROOT,
                "%.2f",
                minorUnits / 100.0
            );
        }
    }

    static final class DomainException extends RuntimeException {
        DomainException(String message) {
            super(message);
        }
    }

    /*
     * SubscriptionItem is an entity inside the Subscription aggregate.
     * Its identity distinguishes the item even when its values later change.
     */
    static final class SubscriptionItem {
        private final UUID itemId;
        private final PlanCode plan;
        private final Money monthlyPrice;
        private int seats;

        SubscriptionItem(
            UUID itemId,
            PlanCode plan,
            Money monthlyPrice,
            int seats
        ) {
            this.itemId = Objects.requireNonNull(itemId);
            this.plan = Objects.requireNonNull(plan);
            this.monthlyPrice = Objects.requireNonNull(monthlyPrice);

            if (seats <= 0) {
                throw new DomainException("Seats must be positive");
            }

            this.seats = seats;
        }

        void increaseSeats(int additionalSeats) {
            if (additionalSeats <= 0) {
                throw new DomainException(
                    "Additional seats must be positive"
                );
            }

            seats += additionalSeats;
        }

        Money monthlyCost() {
            return monthlyPrice.multiply(seats);
        }

        UUID itemId() {
            return itemId;
        }

        PlanCode plan() {
            return plan;
        }

        int seats() {
            return seats;
        }
    }

    /*
     * Repository policy is represented as an interface because policy
     * evaluation is domain behavior that can have multiple implementations.
     */
    interface SubscriptionPolicy {
        boolean canActivate(Subscription subscription);

        String explainFailure(Subscription subscription);
    }

    static final class StandardSubscriptionPolicy
        implements SubscriptionPolicy {

        @Override
        public boolean canActivate(Subscription subscription) {
            return subscription.hasAtLeastOneItem()
                && subscription.hasValidBillingIdentity()
                && subscription.monthlyCost().minorUnits() > 0;
        }

        @Override
        public String explainFailure(Subscription subscription) {
            List<String> failures = new ArrayList<>();

            if (!subscription.hasAtLeastOneItem()) {
                failures.add("subscription has no plan items");
            }

            if (!subscription.hasValidBillingIdentity()) {
                failures.add("billing identity is incomplete");
            }

            if (subscription.monthlyCost().minorUnits() <= 0) {
                failures.add("monthly cost is not positive");
            }

            return String.join("; ", failures);
        }
    }

    /*
     * Subscription is the aggregate root. The item map is private so external
     * callers cannot mutate the aggregate without passing through root methods.
     */
    static final class Subscription {
        private final UUID subscriptionId;
        private final CustomerId customerId;
        private EmailAddress billingEmail;
        private SubscriptionStatus status;
        private final Map<UUID, SubscriptionItem> items =
            new LinkedHashMap<>();

        Subscription(CustomerId customerId, EmailAddress billingEmail) {
            this.subscriptionId = UUID.randomUUID();
            this.customerId = Objects.requireNonNull(customerId);
            this.billingEmail = Objects.requireNonNull(billingEmail);
            this.status = SubscriptionStatus.PENDING;
        }

        UUID subscriptionId() {
            return subscriptionId;
        }

        SubscriptionStatus status() {
            return status;
        }

        void changeBillingEmail(EmailAddress email) {
            if (status == SubscriptionStatus.CANCELLED) {
                throw new DomainException(
                    "Cancelled subscription cannot be modified"
                );
            }

            billingEmail = Objects.requireNonNull(email);
        }

        void addPlan(
            PlanCode plan,
            Money monthlyPrice,
            int seats
        ) {
            ensurePendingOrSuspended();

            for (SubscriptionItem item : items.values()) {
                if (item.plan().equals(plan)) {
                    item.increaseSeats(seats);
                    return;
                }
            }

            SubscriptionItem item = new SubscriptionItem(
                UUID.randomUUID(),
                plan,
                monthlyPrice,
                seats
            );

            items.put(item.itemId(), item);
        }

        void removePlan(UUID itemId) {
            ensurePendingOrSuspended();

            if (items.remove(itemId) == null) {
                throw new DomainException("Subscription item not found");
            }
        }

        void activate(SubscriptionPolicy policy) {
            if (status != SubscriptionStatus.PENDING) {
                throw new DomainException(
                    "Only pending subscriptions can be activated"
                );
            }

            if (!policy.canActivate(this)) {
                throw new DomainException(
                    "Activation rejected: " +
                    policy.explainFailure(this)
                );
            }

            status = SubscriptionStatus.ACTIVE;
        }

        void suspend(String reason) {
            if (status != SubscriptionStatus.ACTIVE) {
                throw new DomainException(
                    "Only active subscriptions can be suspended"
                );
            }

            if (reason == null || reason.isBlank()) {
                throw new DomainException(
                    "Suspension reason is required"
                );
            }

            status = SubscriptionStatus.SUSPENDED;
        }

        void reactivate(SubscriptionPolicy policy) {
            if (status != SubscriptionStatus.SUSPENDED) {
                throw new DomainException(
                    "Only suspended subscriptions can be reactivated"
                );
            }

            if (!policy.canActivate(this)) {
                throw new DomainException(
                    "Reactivation rejected: " +
                    policy.explainFailure(this)
                );
            }

            status = SubscriptionStatus.ACTIVE;
        }

        void cancel(String reason) {
            if (status == SubscriptionStatus.CANCELLED) {
                throw new DomainException(
                    "Subscription is already cancelled"
                );
            }

            if (reason == null || reason.isBlank()) {
                throw new DomainException(
                    "Cancellation reason is required"
                );
            }

            status = SubscriptionStatus.CANCELLED;
        }

        boolean hasAtLeastOneItem() {
            return !items.isEmpty();
        }

        boolean hasValidBillingIdentity() {
            return billingEmail != null;
        }

        Money monthlyCost() {
            Money total = new Money(0, "INR");

            for (SubscriptionItem item : items.values()) {
                total = total.add(item.monthlyCost());
            }

            return total;
        }

        List<String> itemDescriptions() {
            List<String> descriptions = new ArrayList<>();

            for (SubscriptionItem item : items.values()) {
                descriptions.add(
                    item.plan().value() +
                    " seats=" + item.seats() +
                    " monthly=" + item.monthlyCost()
                );
            }

            return Collections.unmodifiableList(descriptions);
        }

        private void ensurePendingOrSuspended() {
            if (
                status != SubscriptionStatus.PENDING &&
                status != SubscriptionStatus.SUSPENDED
            ) {
                throw new DomainException(
                    "Plan changes are not allowed while subscription is " +
                    status
                );
            }
        }
    }

    static final class SubscriptionApplicationService {
        private final Map<UUID, Subscription> subscriptions =
            new HashMap<>();

        void save(Subscription subscription) {
            subscriptions.put(subscription.subscriptionId(), subscription);
        }

        Subscription find(UUID id) {
            Subscription subscription = subscriptions.get(id);

            if (subscription == null) {
                throw new DomainException("Subscription not found");
            }

            return subscription;
        }

        void activate(UUID id, SubscriptionPolicy policy) {
            Subscription subscription = find(id);
            subscription.activate(policy);
            save(subscription);
        }
    }

    public static void main(String[] args) {
        System.out.println(
            "=== Domain-Driven Design: Enterprise Subscription Domain ==="
        );

        CustomerId customerId = CustomerId.create();

        Subscription subscription = new Subscription(
            customerId,
            new EmailAddress("billing@example.com")
        );

        SubscriptionPolicy policy = new StandardSubscriptionPolicy();
        SubscriptionApplicationService service =
            new SubscriptionApplicationService();

        service.save(subscription);

        subscription.addPlan(
            new PlanCode("PRO"),
            new Money(499900, "INR"),
            3
        );

        subscription.addPlan(
            new PlanCode("PRO"),
            new Money(499900, "INR"),
            2
        );

        System.out.println(
            "Subscription ID: " + subscription.subscriptionId()
        );
        System.out.println(
            "Status: " + subscription.status()
        );
        System.out.println(
            "Monthly cost: " + subscription.monthlyCost()
        );

        System.out.println("Items:");
        for (String description : subscription.itemDescriptions()) {
            System.out.println("  " + description);
        }

        service.activate(subscription.subscriptionId(), policy);

        System.out.println(
            "After activation: " + subscription.status()
        );

        try {
            subscription.addPlan(
                new PlanCode("BASIC"),
                new Money(99900, "INR"),
                1
            );
        } catch (DomainException exception) {
            System.out.println(
                "Protected aggregate rule: " +
                exception.getMessage()
            );
        }

        subscription.suspend("Billing verification required");

        System.out.println(
            "After suspension: " + subscription.status()
        );

        subscription.changeBillingEmail(
            new EmailAddress("finance@example.com")
        );

        subscription.reactivate(policy);

        System.out.println(
            "After reactivation: " + subscription.status()
        );

        subscription.cancel("Customer terminated service");

        System.out.println(
            "Final status: " + subscription.status()
        );

        try {
            subscription.reactivate(policy);
        } catch (DomainException exception) {
            System.out.println(
                "Invalid state transition: " +
                exception.getMessage()
            );
        }

        Money first = new Money(12500, "INR");
        Money second = new Money(12500, "INR");

        System.out.println(
            "Value-object equality: " + first.equals(second)
        );
    }
}
