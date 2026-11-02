import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class MockingEnterpriseExample {

    enum PaymentStatus {
        APPROVED,
        DECLINED
    }

    record Payment(
            String id,
            String customerId,
            double amount,
            String currency
    ) {}

    interface PaymentGateway {
        PaymentStatus authorize(Payment payment);
    }

    interface FraudService {
        boolean isSuspicious(Payment payment);
    }

    interface PaymentRepository {
        void save(Payment payment, PaymentStatus status);
    }

    static final class ValidationException extends RuntimeException {
        ValidationException(String message) {
            super(message);
        }
    }

    static final class PaymentService {
        private final PaymentGateway gateway;
        private final FraudService fraudService;
        private final PaymentRepository repository;

        PaymentService(
                PaymentGateway gateway,
                FraudService fraudService,
                PaymentRepository repository
        ) {
            this.gateway = gateway;
            this.fraudService = fraudService;
            this.repository = repository;
        }

        PaymentStatus process(Payment payment) {
            validate(payment);

            PaymentStatus status = fraudService.isSuspicious(payment)
                    ? PaymentStatus.DECLINED
                    : gateway.authorize(payment);

            repository.save(payment, status);
            return status;
        }

        private void validate(Payment payment) {
            if (payment == null) {
                throw new ValidationException("Payment is required");
            }
            if (payment.id() == null || payment.id().isBlank()) {
                throw new ValidationException("Payment ID is required");
            }
            if (payment.customerId() == null || payment.customerId().isBlank()) {
                throw new ValidationException("Customer ID is required");
            }
            if (!Double.isFinite(payment.amount()) || payment.amount() <= 0) {
                throw new ValidationException("Amount must be positive and finite");
            }
            if (payment.currency() == null || !payment.currency().matches("[A-Z]{3}")) {
                throw new ValidationException("Currency must contain three uppercase letters");
            }
        }
    }

    static final class StubGateway implements PaymentGateway {
        private final PaymentStatus result;
        private int callCount;

        StubGateway(PaymentStatus result) {
            this.result = result;
        }

        @Override
        public PaymentStatus authorize(Payment payment) {
            callCount++;
            return result;
        }

        int callCount() {
            return callCount;
        }
    }

    static final class FakeFraudService implements FraudService {
        private final Set<String> blockedCustomers;

        FakeFraudService(Set<String> blockedCustomers) {
            this.blockedCustomers = new HashSet<>(blockedCustomers);
        }

        @Override
        public boolean isSuspicious(Payment payment) {
            return blockedCustomers.contains(payment.customerId());
        }
    }

    static final class FakeRepository implements PaymentRepository {
        private final Map<String, PaymentStatus> records = new HashMap<>();

        @Override
        public void save(Payment payment, PaymentStatus status) {
            records.put(payment.id(), status);
        }

        PaymentStatus find(String id) {
            return records.get(id);
        }
    }

    static final class MockGateway implements PaymentGateway {
        private final PaymentStatus result;
        private final List<Payment> calls = new ArrayList<>();

        MockGateway(PaymentStatus result) {
            this.result = result;
        }

        @Override
        public PaymentStatus authorize(Payment payment) {
            calls.add(payment);
            return result;
        }

        void verifyCalledOnceWith(Payment expected) {
            if (calls.size() != 1 || !calls.getFirst().equals(expected)) {
                throw new AssertionError("Gateway interaction expectation failed");
            }
        }

        List<Payment> calls() {
            return List.copyOf(calls);
        }
    }

    static final class MockFraudService implements FraudService {
        private final boolean result;
        private final List<Payment> calls = new ArrayList<>();

        MockFraudService(boolean result) {
            this.result = result;
        }

        @Override
        public boolean isSuspicious(Payment payment) {
            calls.add(payment);
            return result;
        }

        List<Payment> calls() {
            return List.copyOf(calls);
        }
    }

    static void testStub() {
        Payment payment = new Payment("P-100", "C-10", 100, "USD");
        StubGateway gateway = new StubGateway(PaymentStatus.APPROVED);
        FakeRepository repository = new FakeRepository();

        PaymentService service = new PaymentService(
                gateway,
                new FakeFraudService(Set.of()),
                repository
        );

        assert service.process(payment) == PaymentStatus.APPROVED;
        assert gateway.callCount() == 1;
        assert repository.find("P-100") == PaymentStatus.APPROVED;
    }

    static void testFake() {
        Payment payment = new Payment("P-101", "BLOCKED", 100, "USD");
        StubGateway gateway = new StubGateway(PaymentStatus.APPROVED);
        FakeRepository repository = new FakeRepository();

        PaymentService service = new PaymentService(
                gateway,
                new FakeFraudService(Set.of("BLOCKED")),
                repository
        );

        assert service.process(payment) == PaymentStatus.DECLINED;
        assert gateway.callCount() == 0;
        assert repository.find("P-101") == PaymentStatus.DECLINED;
    }

    static void testMock() {
        Payment payment = new Payment("P-102", "C-20", 300, "USD");
        MockGateway gateway = new MockGateway(PaymentStatus.APPROVED);
        MockFraudService fraud = new MockFraudService(false);

        PaymentService service = new PaymentService(
                gateway,
                fraud,
                new FakeRepository()
        );

        service.process(payment);

        gateway.verifyCalledOnceWith(payment);
        assert fraud.calls().equals(List.of(payment));
    }

    static void testValidation() {
        Payment invalid = new Payment("P-103", "C-20", -1, "USD");
        MockGateway gateway = new MockGateway(PaymentStatus.APPROVED);
        MockFraudService fraud = new MockFraudService(false);

        PaymentService service = new PaymentService(
                gateway,
                fraud,
                new FakeRepository()
        );

        boolean failed = false;
        try {
            service.process(invalid);
        } catch (ValidationException expected) {
            failed = true;
        }

        assert failed;
        assert gateway.calls().isEmpty();
        assert fraud.calls().isEmpty();
    }

    static void testInteractionFailureDetection() {
        Payment payment = new Payment("P-104", "C-20", 400, "USD");
        MockGateway gateway = new MockGateway(PaymentStatus.APPROVED);

        gateway.authorize(payment);
        gateway.authorize(payment);

        boolean failed = false;
        try {
            gateway.verifyCalledOnceWith(payment);
        } catch (AssertionError expected) {
            failed = true;
        }

        assert failed;
    }

    public static void main(String[] args) {
        testStub();
        testFake();
        testMock();
        testValidation();
        testInteractionFailureDetection();

        System.out.println("All Java 17 mocking and dependency-isolation tests passed.");
    }
}
