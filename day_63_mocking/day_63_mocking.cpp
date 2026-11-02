#include <algorithm>
#include <cassert>
#include <exception>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

enum class PaymentStatus {
    Approved,
    Declined
};

std::string toString(PaymentStatus status) {
    return status == PaymentStatus::Approved ? "approved" : "declined";
}

struct Payment {
    std::string id;
    std::string customerId;
    double amount;
    std::string currency;

    bool operator==(const Payment& other) const {
        return id == other.id &&
               customerId == other.customerId &&
               amount == other.amount &&
               currency == other.currency;
    }
};

class IPaymentGateway {
public:
    virtual ~IPaymentGateway() = default;
    virtual PaymentStatus authorize(const Payment& payment) = 0;
};

class IFraudService {
public:
    virtual ~IFraudService() = default;
    virtual bool suspicious(const Payment& payment) = 0;
};

class IPaymentRepository {
public:
    virtual ~IPaymentRepository() = default;
    virtual void save(const Payment& payment, PaymentStatus status) = 0;
};

class ProductionGateway final : public IPaymentGateway {
public:
    PaymentStatus authorize(const Payment& payment) override {
        if (payment.amount <= 0.0) {
            throw std::invalid_argument("Amount must be positive");
        }
        return PaymentStatus::Approved;
    }
};

class StubGateway final : public IPaymentGateway {
    PaymentStatus result_;

public:
    explicit StubGateway(PaymentStatus result) : result_(result) {}

    PaymentStatus authorize(const Payment&) override {
        return result_;
    }
};

class MockGateway final : public IPaymentGateway {
    PaymentStatus result_;
    std::vector<Payment> calls_;

public:
    explicit MockGateway(PaymentStatus result) : result_(result) {}

    PaymentStatus authorize(const Payment& payment) override {
        calls_.push_back(payment);
        return result_;
    }

    const std::vector<Payment>& calls() const {
        return calls_;
    }

    void verifyCalledOnceWith(const Payment& expected) const {
        if (calls_.size() != 1 || !(calls_.front() == expected)) {
            throw std::runtime_error("Mock interaction expectation failed");
        }
    }
};

class FakeFraudService final : public IFraudService {
    std::set<std::string> blockedCustomers_;

public:
    explicit FakeFraudService(std::set<std::string> blockedCustomers)
        : blockedCustomers_(std::move(blockedCustomers)) {}

    bool suspicious(const Payment& payment) override {
        return blockedCustomers_.contains(payment.customerId);
    }
};

class MockFraudService final : public IFraudService {
    bool result_;
    std::vector<Payment> calls_;

public:
    explicit MockFraudService(bool result) : result_(result) {}

    bool suspicious(const Payment& payment) override {
        calls_.push_back(payment);
        return result_;
    }

    const std::vector<Payment>& calls() const {
        return calls_;
    }
};

class InMemoryRepository final : public IPaymentRepository {
    std::map<std::string, PaymentStatus> records_;

public:
    void save(const Payment& payment, PaymentStatus status) override {
        records_[payment.id] = status;
    }

    PaymentStatus get(const std::string& id) const {
        auto it = records_.find(id);
        if (it == records_.end()) {
            throw std::out_of_range("Payment was not stored");
        }
        return it->second;
    }
};

class PaymentService {
    IPaymentGateway& gateway_;
    IFraudService& fraud_;
    IPaymentRepository& repository_;

    static void validate(const Payment& payment) {
        if (payment.id.empty()) {
            throw std::invalid_argument("Payment ID is required");
        }
        if (payment.customerId.empty()) {
            throw std::invalid_argument("Customer ID is required");
        }
        if (payment.amount <= 0.0) {
            throw std::invalid_argument("Amount must be positive");
        }
        if (payment.currency.size() != 3) {
            throw std::invalid_argument("Currency must have three characters");
        }
    }

public:
    PaymentService(
        IPaymentGateway& gateway,
        IFraudService& fraud,
        IPaymentRepository& repository
    ) : gateway_(gateway), fraud_(fraud), repository_(repository) {}

    PaymentStatus process(const Payment& payment) {
        validate(payment);

        const PaymentStatus status =
            fraud_.suspicious(payment)
                ? PaymentStatus::Declined
                : gateway_.authorize(payment);

        repository_.save(payment, status);
        return status;
    }
};

void testStub() {
    Payment payment{"P-100", "C-10", 100.0, "USD"};
    StubGateway gateway(PaymentStatus::Approved);
    FakeFraudService fraud({});
    InMemoryRepository repository;

    PaymentService service(gateway, fraud, repository);

    assert(service.process(payment) == PaymentStatus::Approved);
    assert(repository.get("P-100") == PaymentStatus::Approved);
}

void testFakeFraudIsolation() {
    Payment payment{"P-101", "C-BLOCKED", 100.0, "USD"};
    StubGateway gateway(PaymentStatus::Approved);
    FakeFraudService fraud({"C-BLOCKED"});
    InMemoryRepository repository;

    PaymentService service(gateway, fraud, repository);

    assert(service.process(payment) == PaymentStatus::Declined);
    assert(repository.get("P-101") == PaymentStatus::Declined);
}

void testMockInteraction() {
    Payment payment{"P-102", "C-10", 200.0, "USD"};
    MockGateway gateway(PaymentStatus::Approved);
    MockFraudService fraud(false);
    InMemoryRepository repository;

    PaymentService service(gateway, fraud, repository);
    service.process(payment);

    gateway.verifyCalledOnceWith(payment);
    assert(fraud.calls().size() == 1);
    assert(fraud.calls().front() == payment);
}

void testInvalidInput() {
    Payment payment{"P-103", "C-10", -20.0, "USD"};
    MockGateway gateway(PaymentStatus::Approved);
    MockFraudService fraud(false);
    InMemoryRepository repository;

    PaymentService service(gateway, fraud, repository);

    bool failed = false;
    try {
        service.process(payment);
    } catch (const std::invalid_argument&) {
        failed = true;
    }

    assert(failed);
    assert(gateway.calls().empty());
    assert(fraud.calls().empty());
}

void testRealGatewayComposition() {
    Payment payment{"P-104", "C-20", 500.0, "USD"};
    ProductionGateway gateway;
    FakeFraudService fraud({});
    InMemoryRepository repository;

    PaymentService service(gateway, fraud, repository);

    assert(service.process(payment) == PaymentStatus::Approved);
}

int main() {
    try {
        testStub();
        testFakeFraudIsolation();
        testMockInteraction();
        testInvalidInput();
        testRealGatewayComposition();

        std::cout << "All C++17 dependency-isolation tests passed.\n";
        std::cout << "The service was tested with stubs, mocks, fakes, "
                     "and a production-style adapter.\n";
    } catch (const std::exception& ex) {
        std::cerr << "Test failure: " << ex.what() << '\n';
        return 1;
    }

    return 0;
}
