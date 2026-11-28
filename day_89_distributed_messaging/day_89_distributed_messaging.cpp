#include <algorithm>
#include <cstdint>
#include <deque>
#include <functional>
#include <iostream>
#include <map>
#include <memory>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

/*
 * Distributed Messaging and Repository-Independent
 * Message Delivery Governance Engine.
 *
 * C++17
 *
 * Implements:
 * - Queue and stream domain models
 * - Message delivery states
 * - Delivery guarantees
 * - Consumer groups and partition offsets
 * - Acknowledgement and retry policies
 * - Dead-letter handling
 * - Idempotent processing
 * - Merge-free transactional processing boundaries
 */

enum class DeliveryGuarantee {
    AtMostOnce,
    AtLeastOnce,
    ExactlyOnce
};

enum class MessageState {
    Pending,
    InFlight,
    Acknowledged,
    DeadLettered
};

struct Message {
    std::string id;
    std::string topic;
    std::string key;
    std::string payload;
    std::uint64_t timestamp;
};

struct Delivery {
    Message message;
    unsigned int attempts = 0;
    MessageState state = MessageState::Pending;
};

struct QueueMetrics {
    std::size_t published = 0;
    std::size_t acknowledged = 0;
    std::size_t retried = 0;
    std::size_t deadLettered = 0;
};

class MessagingException : public std::runtime_error {
public:
    explicit MessagingException(const std::string& message)
        : std::runtime_error(message) {}
};


class MessageQueue {
private:
    std::string name;
    unsigned int maxRetries;
    std::size_t capacity;

    std::deque<Delivery> pending;

    std::unordered_map<std::string, Delivery> inFlight;

    std::vector<Delivery> deadLetters;

    QueueMetrics metrics;

public:
    MessageQueue(
        std::string queueName,
        unsigned int retries = 3,
        std::size_t maxCapacity = 10000
    )
        : name(std::move(queueName)),
          maxRetries(retries),
          capacity(maxCapacity) {

        if (name.empty() || capacity == 0) {
            throw MessagingException("Invalid queue configuration");
        }
    }

    void publish(const Message& message) {
        if (pending.size() + inFlight.size() >= capacity) {
            throw MessagingException("Queue capacity exceeded");
        }

        if (message.id.empty() || message.topic.empty()) {
            throw MessagingException("Invalid message");
        }

        pending.push_back(Delivery{message});
        metrics.published++;
    }

    std::optional<Delivery> receive() {
        if (pending.empty()) {
            return std::nullopt;
        }

        Delivery delivery = pending.front();
        pending.pop_front();

        delivery.attempts++;
        delivery.state = MessageState::InFlight;

        const std::string id = delivery.message.id;

        if (inFlight.count(id)) {
            throw MessagingException("Duplicate in-flight message");
        }

        inFlight.emplace(id, delivery);

        return delivery;
    }

    void acknowledge(const std::string& id) {
        auto it = inFlight.find(id);

        if (it == inFlight.end()) {
            throw MessagingException("Message is not in flight");
        }

        it->second.state = MessageState::Acknowledged;

        inFlight.erase(it);
        metrics.acknowledged++;
    }

    void reject(const std::string& id) {
        auto it = inFlight.find(id);

        if (it == inFlight.end()) {
            throw MessagingException("Unknown delivery");
        }

        Delivery delivery = it->second;
        inFlight.erase(it);

        if (delivery.attempts <= maxRetries) {
            delivery.state = MessageState::Pending;
            pending.push_back(delivery);
            metrics.retried++;
        } else {
            delivery.state = MessageState::DeadLettered;
            deadLetters.push_back(delivery);
            metrics.deadLettered++;
        }
    }

    std::size_t recover() {
        std::size_t count = inFlight.size();

        for (auto& entry : inFlight) {
            Delivery delivery = entry.second;
            delivery.state = MessageState::Pending;
            pending.push_front(delivery);
        }

        inFlight.clear();

        return count;
    }

    const std::vector<Delivery>& getDeadLetters() const {
        return deadLetters;
    }

    const QueueMetrics& getMetrics() const {
        return metrics;
    }

    std::size_t pendingCount() const {
        return pending.size();
    }

    std::size_t inFlightCount() const {
        return inFlight.size();
    }
};


class EventStream {
private:
    std::string name;

    std::vector<std::vector<Message>> partitions;

    std::map<std::string, std::vector<std::size_t>> consumerOffsets;

    std::size_t partitionFor(const std::string& key) const {
        // Deterministic hash is used for stable partition assignment.
        return std::hash<std::string>{}(key) % partitions.size();
    }

public:
    EventStream(std::string streamName, std::size_t partitionCount)
        : name(std::move(streamName)),
          partitions(partitionCount) {

        if (name.empty() || partitionCount == 0) {
            throw MessagingException("Invalid stream configuration");
        }
    }

    std::pair<std::size_t, std::size_t> append(
        const Message& message
    ) {
        if (message.id.empty() || message.key.empty()) {
            throw MessagingException("Invalid event");
        }

        std::size_t partition = partitionFor(message.key);

        std::size_t offset = partitions[partition].size();

        partitions[partition].push_back(message);

        return {partition, offset};
    }

    void registerGroup(const std::string& group) {
        if (group.empty()) {
            throw MessagingException("Consumer group required");
        }

        consumerOffsets.try_emplace(
            group,
            partitions.size(),
            0
        );
    }

    std::vector<std::pair<std::size_t, Message>> poll(
        const std::string& group,
        std::size_t partition,
        std::size_t batchSize
    ) const {

        auto it = consumerOffsets.find(group);

        if (it == consumerOffsets.end()) {
            throw MessagingException("Unknown consumer group");
        }

        if (partition >= partitions.size() || batchSize == 0) {
            throw MessagingException("Invalid polling parameters");
        }

        std::vector<std::pair<std::size_t, Message>> result;

        std::size_t start = it->second[partition];

        std::size_t end = std::min(
            start + batchSize,
            partitions[partition].size()
        );

        for (std::size_t offset = start; offset < end; ++offset) {
            result.emplace_back(
                offset,
                partitions[partition][offset]
            );
        }

        return result;
    }

    void commit(
        const std::string& group,
        std::size_t partition,
        std::size_t nextOffset
    ) {

        auto it = consumerOffsets.find(group);

        if (it == consumerOffsets.end()) {
            throw MessagingException("Unknown consumer group");
        }

        if (partition >= partitions.size()) {
            throw MessagingException("Invalid partition");
        }

        std::size_t current = it->second[partition];
        std::size_t maximum = partitions[partition].size();

        if (nextOffset < current || nextOffset > maximum) {
            throw MessagingException("Invalid offset transition");
        }

        it->second[partition] = nextOffset;
    }

    void seek(
        const std::string& group,
        std::size_t partition,
        std::size_t offset
    ) {
        auto it = consumerOffsets.find(group);

        if (it == consumerOffsets.end() ||
            partition >= partitions.size() ||
            offset > partitions[partition].size()) {
            throw MessagingException("Invalid replay position");
        }

        it->second[partition] = offset;
    }

    const std::vector<std::size_t>& offsets(
        const std::string& group
    ) const {
        auto it = consumerOffsets.find(group);

        if (it == consumerOffsets.end()) {
            throw MessagingException("Unknown group");
        }

        return it->second;
    }
};


class IdempotentProcessor {
private:
    std::set<std::string> processed;
    std::map<std::string, double> balances;

public:
    bool process(
        const Message& message,
        const std::string& account,
        double amount
    ) {

        if (message.id.empty() || account.empty()) {
            throw MessagingException("Invalid transaction");
        }

        if (amount <= 0) {
            throw MessagingException("Amount must be positive");
        }

        if (processed.count(message.id)) {
            return false;
        }

        // Both state changes occur inside this local critical operation.
        // Persistent distributed systems need a database transaction.
        balances[account] += amount;
        processed.insert(message.id);

        return true;
    }

    double balance(const std::string& account) const {
        auto it = balances.find(account);

        return it == balances.end() ? 0.0 : it->second;
    }

    std::size_t processedCount() const {
        return processed.size();
    }
};


class DeliveryService {
private:
    MessageQueue& queue;
    IdempotentProcessor& processor;

public:
    DeliveryService(
        MessageQueue& q,
        IdempotentProcessor& p
    ) : queue(q), processor(p) {}

    bool consume(
        const std::string& account,
        double amount,
        DeliveryGuarantee guarantee
    ) {
        auto delivery = queue.receive();

        if (!delivery.has_value()) {
            return false;
        }

        const std::string id = delivery->message.id;

        try {
            if (guarantee == DeliveryGuarantee::AtMostOnce) {
                queue.acknowledge(id);

                processor.process(
                    delivery->message,
                    account,
                    amount
                );

            } else if (
                guarantee == DeliveryGuarantee::AtLeastOnce ||
                guarantee == DeliveryGuarantee::ExactlyOnce
            ) {
                processor.process(
                    delivery->message,
                    account,
                    amount
                );

                queue.acknowledge(id);
            }

            return true;

        } catch (...) {
            queue.reject(id);
            throw;
        }
    }
};


Message createMessage(
    const std::string& id,
    const std::string& topic,
    const std::string& key,
    const std::string& payload,
    std::uint64_t timestamp
) {
    return Message{
        id,
        topic,
        key,
        payload,
        timestamp
    };
}


void demonstrateQueue() {
    std::cout << "\n=== POINT-TO-POINT QUEUE ===\n";

    MessageQueue queue("payment-events", 2);

    IdempotentProcessor processor;

    DeliveryService service(queue, processor);

    Message payment = createMessage(
        "payment-001",
        "payments",
        "account-100",
        "{\"amount\":2500}",
        1000
    );

    queue.publish(payment);

    service.consume(
        "account-100",
        2500,
        DeliveryGuarantee::AtLeastOnce
    );

    // A duplicate message does not modify the account twice.
    processor.process(payment, "account-100", 2500);

    std::cout << "Balance: "
              << processor.balance("account-100")
              << '\n';

    std::cout << "Processed unique messages: "
              << processor.processedCount()
              << '\n';

    const auto& metrics = queue.getMetrics();

    std::cout << "Published: " << metrics.published << '\n';
    std::cout << "Acknowledged: " << metrics.acknowledged << '\n';
}


void demonstrateStream() {
    std::cout << "\n=== PARTITIONED EVENT STREAM ===\n";

    EventStream stream("orders", 3);

    stream.registerGroup("analytics");
    stream.registerGroup("billing");

    for (int i = 1; i <= 8; ++i) {
        Message message = createMessage(
            "order-" + std::to_string(i),
            "orders",
            "customer-" + std::to_string(i % 2),
            "{\"order_id\":" + std::to_string(i) + "}",
            static_cast<std::uint64_t>(i)
        );

        auto position = stream.append(message);

        std::cout << "Appended order-" << i
                  << " to partition " << position.first
                  << " offset " << position.second
                  << '\n';
    }

    for (std::size_t partition = 0; partition < 3; ++partition) {
        auto events = stream.poll(
            "analytics",
            partition,
            100
        );

        for (const auto& event : events) {
            std::cout << "Analytics processed offset "
                      << event.first
                      << " message "
                      << event.second.id
                      << '\n';
        }

        const auto& offsets = stream.offsets("analytics");

        stream.commit(
            "analytics",
            partition,
            offsets[partition] + events.size()
        );
    }

    std::cout << "Analytics offsets: ";

    for (auto offset : stream.offsets("analytics")) {
        std::cout << offset << ' ';
    }

    std::cout << "\nBilling offsets: ";

    for (auto offset : stream.offsets("billing")) {
        std::cout << offset << ' ';
    }

    std::cout << '\n';
}


void demonstrateFailureHandling() {
    std::cout << "\n=== RETRIES AND DEAD LETTERS ===\n";

    MessageQueue queue("notifications", 2);

    queue.publish(
        createMessage(
            "notification-001",
            "notifications",
            "user-10",
            "{\"event\":\"password_changed\"}",
            100
        )
    );

    for (int i = 0; i < 4; ++i) {
        auto delivery = queue.receive();

        if (!delivery) {
            break;
        }

        std::cout << "Processing attempt "
                  << delivery->attempts
                  << '\n';

        queue.reject(delivery->message.id);
    }

    std::cout << "Dead-letter count: "
              << queue.getDeadLetters().size()
              << '\n';
}


int main() {
    try {
        demonstrateQueue();
        demonstrateStream();
        demonstrateFailureHandling();

        std::cout << "\nMessaging engine completed.\n";

    } catch (const std::exception& exception) {
        std::cerr << "Messaging failure: "
                  << exception.what()
                  << '\n';

        return 1;
    }

    return 0;
}
