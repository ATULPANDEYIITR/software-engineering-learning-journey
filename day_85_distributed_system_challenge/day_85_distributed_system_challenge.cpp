#include <algorithm>
#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <random>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

using namespace std;

enum class NodeStatus {
    Healthy,
    Unavailable,
    Partitioned
};

enum class Consistency {
    One,
    Quorum,
    All
};

enum class ErrorCode {
    InvalidRequest,
    NetworkFailure,
    QuorumFailure,
    Conflict
};

struct DistributedException : runtime_error {
    ErrorCode code;

    DistributedException(
        ErrorCode errorCode,
        const string& message
    ) : runtime_error(message), code(errorCode) {}
};

struct Record {
    string key;
    string value;
    int version;
    long long timestamp;
    string operationId;
};

bool newer(const Record& a, const Record& b) {
    if (a.version != b.version) {
        return a.version > b.version;
    }

    if (a.timestamp != b.timestamp) {
        return a.timestamp > b.timestamp;
    }

    return a.operationId > b.operationId;
}

class Replica {
private:
    string id;
    NodeStatus status;
    unordered_map<string, Record> storage;
    unordered_set<string> appliedOperations;

public:
    explicit Replica(string nodeId)
        : id(move(nodeId)),
          status(NodeStatus::Healthy) {}

    const string& getId() const {
        return id;
    }

    void setStatus(NodeStatus newStatus) {
        status = newStatus;
    }

    bool available() const {
        return status == NodeStatus::Healthy;
    }

    bool apply(const Record& record) {
        if (!available()) {
            throw DistributedException(
                ErrorCode::NetworkFailure,
                id + " unavailable"
            );
        }

        if (appliedOperations.count(record.operationId)) {
            return true;
        }

        auto it = storage.find(record.key);

        if (it == storage.end() || newer(record, it->second)) {
            storage[record.key] = record;
        }

        appliedOperations.insert(record.operationId);
        return true;
    }

    optional<Record> read(const string& key) const {
        if (!available()) {
            throw DistributedException(
                ErrorCode::NetworkFailure,
                id + " unavailable"
            );
        }

        auto it = storage.find(key);

        if (it == storage.end()) {
            return nullopt;
        }

        return it->second;
    }

    size_t recordCount() const {
        return storage.size();
    }
};

class Network {
private:
    double baseLatency;
    double jitter;
    double packetLoss;
    mt19937 generator;
    uniform_real_distribution<double> probability;
    uniform_real_distribution<double> variation;

    set<pair<string, string>> partitions;

public:
    Network(
        double latency = 10,
        double jitterValue = 5,
        double loss = 0
    )
        : baseLatency(latency),
          jitter(jitterValue),
          packetLoss(loss),
          generator(42),
          probability(0.0, 1.0),
          variation(0.0, 1.0) {

        if (
            latency < 0 ||
            jitterValue < 0 ||
            loss < 0 ||
            loss > 1
        ) {
            throw invalid_argument("Invalid network configuration");
        }
    }

    void partition(
        const string& source,
        const string& destination
    ) {
        partitions.insert({source, destination});
        partitions.insert({destination, source});
    }

    void heal(
        const string& source,
        const string& destination
    ) {
        partitions.erase({source, destination});
        partitions.erase({destination, source});
    }

    double transmit(
        const string& source,
        const string& destination
    ) {
        if (partitions.count({source, destination})) {
            throw DistributedException(
                ErrorCode::NetworkFailure,
                "Network partition"
            );
        }

        if (probability(generator) < packetLoss) {
            throw DistributedException(
                ErrorCode::NetworkFailure,
                "Packet dropped"
            );
        }

        return baseLatency + jitter * variation(generator);
    }
};

struct Metrics {
    size_t writes = 0;
    size_t reads = 0;
    size_t failedWrites = 0;
    size_t timeouts = 0;
    size_t replicaWrites = 0;
    double totalLatency = 0;
};

class DistributedCluster {
private:
    vector<Replica> nodes;
    size_t replicationFactor;
    Network network;
    int logicalClock = 0;
    string coordinator = "coordinator";

    unordered_map<string, bool> completedOperations;

    Metrics metrics;

    size_t quorum() const {
        return replicationFactor / 2 + 1;
    }

    size_t required(Consistency consistency) const {
        switch (consistency) {
            case Consistency::One:
                return 1;

            case Consistency::Quorum:
                return quorum();

            case Consistency::All:
                return replicationFactor;
        }

        throw invalid_argument("Unknown consistency level");
    }

    vector<Replica*> replicas(const string& key) {
        size_t hash = 0;

        for (unsigned char c : key) {
            hash = hash * 31 + c;
        }

        size_t start = hash % nodes.size();
        vector<Replica*> result;

        for (size_t i = 0; i < replicationFactor; ++i) {
            result.push_back(
                &nodes[(start + i) % nodes.size()]
            );
        }

        return result;
    }

public:
    DistributedCluster(
        size_t nodeCount = 5,
        size_t replication = 3
    )
        : replicationFactor(replication),
          network(12, 5, 0) {

        if (
            nodeCount == 0 ||
            replication == 0 ||
            replication > nodeCount
        ) {
            throw invalid_argument("Invalid cluster configuration");
        }

        for (size_t i = 0; i < nodeCount; ++i) {
            nodes.emplace_back("node-" + to_string(i + 1));
        }
    }

    void setNodeStatus(
        const string& id,
        NodeStatus status
    ) {
        for (auto& node : nodes) {
            if (node.getId() == id) {
                node.setStatus(status);
                return;
            }
        }

        throw invalid_argument("Unknown node");
    }

    void partition(
        const string& source,
        const string& destination
    ) {
        network.partition(source, destination);
    }

    void heal(
        const string& source,
        const string& destination
    ) {
        network.heal(source, destination);
    }

    bool write(
        const string& key,
        const string& value,
        Consistency consistency = Consistency::Quorum,
        const string& operationId = "",
        int retries = 2
    ) {
        if (
            key.empty() ||
            key.size() > 256 ||
            value.size() > 10000 ||
            retries < 0
        ) {
            throw DistributedException(
                ErrorCode::InvalidRequest,
                "Invalid write request"
            );
        }

        string id = operationId.empty()
            ? "operation-" + to_string(++logicalClock)
            : operationId;

        auto existing = completedOperations.find(id);

        if (existing != completedOperations.end()) {
            return existing->second;
        }

        auto targets = replicas(key);
        size_t requiredAcks = required(consistency);
        size_t acknowledgements = 0;

        Record record {
            key,
            value,
            ++logicalClock,
            chrono::duration_cast<chrono::milliseconds>(
                chrono::system_clock::now().time_since_epoch()
            ).count(),
            id
        };

        auto start = chrono::steady_clock::now();

        try {
            // The operation ID remains constant across retries.
            // Acknowledgements are counted once per replica.
            unordered_set<string> acknowledged;

            for (int attempt = 0; attempt <= retries; ++attempt) {
                for (Replica* node : targets) {
                    if (acknowledged.count(node->getId())) {
                        continue;
                    }

                    try {
                        network.transmit(
                            coordinator,
                            node->getId()
                        );

                        node->apply(record);

                        acknowledged.insert(node->getId());
                        metrics.replicaWrites++;

                    } catch (const DistributedException&) {
                        metrics.timeouts++;
                    }

                    if (acknowledged.size() >= requiredAcks) {
                        completedOperations[id] = true;
                        return true;
                    }
                }
            }

            throw DistributedException(
                ErrorCode::QuorumFailure,
                "Insufficient replica acknowledgements"
            );

        } catch (...) {
            metrics.failedWrites++;
            completedOperations[id] = false;
            throw;

        } 
    }

    optional<Record> read(
        const string& key,
        Consistency consistency = Consistency::Quorum,
        bool repair = true
    ) {
        if (key.empty()) {
            throw invalid_argument("Read key cannot be empty");
        }

        auto targets = replicas(key);
        vector<pair<Replica*, optional<Record>>> responses;

        auto start = chrono::steady_clock::now();

        for (Replica* node : targets) {
            try {
                network.transmit(coordinator, node->getId());

                responses.push_back({
                    node,
                    node->read(key)
                });

            } catch (const DistributedException&) {
                metrics.timeouts++;
            }
        }

        if (responses.size() < required(consistency)) {
            throw DistributedException(
                ErrorCode::QuorumFailure,
                "Insufficient read responses"
            );
        }

        optional<Record> latest;

        for (const auto& response : responses) {
            if (!response.second.has_value()) {
                continue;
            }

            if (
                !latest.has_value() ||
                newer(response.second.value(), latest.value())
            ) {
                latest = response.second;
            }
        }

        if (repair && latest.has_value()) {
            for (auto& response : responses) {
                if (
                    !response.second.has_value() ||
                    newer(latest.value(), response.second.value())
                ) {
                    response.first->apply(latest.value());
                }
            }
        }

        metrics.reads++;

        auto elapsed = chrono::duration<double, milli>(
            chrono::steady_clock::now() - start
        ).count();

        metrics.totalLatency += elapsed;

        return latest;
    }

    size_t synchronize(const string& key) {
        auto targets = replicas(key);
        optional<Record> latest;

        for (Replica* node : targets) {
            if (!node->available()) {
                continue;
            }

            auto record = node->read(key);

            if (
                record.has_value() &&
                (
                    !latest.has_value() ||
                    newer(record.value(), latest.value())
                )
            ) {
                latest = record;
            }
        }

        if (!latest.has_value()) {
            return 0;
        }

        size_t repaired = 0;

        for (Replica* node : targets) {
            if (!node->available()) {
                continue;
            }

            auto current = node->read(key);

            if (
                !current.has_value() ||
                newer(latest.value(), current.value())
            ) {
                node->apply(latest.value());
                repaired++;
            }
        }

        return repaired;
    }

    void report() const {
        cout << "\nCLUSTER METRICS\n";
        cout << "-------------------------------\n";
        cout << "Writes: " << metrics.writes << "\n";
        cout << "Reads: " << metrics.reads << "\n";
        cout << "Failed writes: " << metrics.failedWrites << "\n";
        cout << "Network failures: " << metrics.timeouts << "\n";
        cout << "Replica writes: " << metrics.replicaWrites << "\n";
        cout << "Recorded latency: "
             << metrics.totalLatency << " ms\n";

        cout << "\nREPLICA STORAGE\n";

        for (const auto& node : nodes) {
            cout << node.getId()
                 << ": "
                 << node.recordCount()
                 << " records\n";
        }
    }
};

int main() {
    try {
        cout << "DISTRIBUTED SYSTEM CHALLENGES\n";
        cout << "==============================\n";

        DistributedCluster cluster(5, 3);

        cout << "\n1. QUORUM WRITE\n";

        cluster.write(
            "customer:101",
            "balance:7500",
            Consistency::Quorum,
            "transaction-101"
        );

        cout << "Transaction replicated.\n";

        cout << "\n2. IDEMPOTENT RETRY\n";

        cluster.write(
            "customer:101",
            "balance:7500",
            Consistency::Quorum,
            "transaction-101"
        );

        cout << "Duplicate transaction accepted safely.\n";

        cout << "\n3. QUORUM READ\n";

        auto result = cluster.read("customer:101");

        if (result.has_value()) {
            cout << "Value: " << result->value << "\n";
            cout << "Version: " << result->version << "\n";
        }

        cout << "\n4. NODE FAILURE\n";

        cluster.setNodeStatus(
            "node-1",
            NodeStatus::Unavailable
        );

        cluster.write(
            "customer:102",
            "balance:9000"
        );

        cout << "Quorum remained available.\n";

        cout << "\n5. NETWORK PARTITION\n";

        cluster.partition("coordinator", "node-2");

        try {
            cluster.write(
                "customer:103",
                "balance:1000",
                Consistency::All,
                "transaction-103",
                0
            );
        } catch (const DistributedException& error) {
            cout << "Expected failure: "
                 << error.what() << "\n";
        }

        cout << "\n6. PARTITION RECOVERY\n";

        cluster.heal("coordinator", "node-2");

        cluster.setNodeStatus(
            "node-1",
            NodeStatus::Healthy
        );

        cout << "Replica repairs: "
             << cluster.synchronize("customer:101")
             << "\n";

        cout << "\n7. INVALID REQUEST\n";

        try {
            cluster.write("", "invalid");
        } catch (const exception& error) {
            cout << "Validation: " << error.what() << "\n";
        }

        cluster.report();

    } catch (const exception& error) {
        cerr << "Fatal error: " << error.what() << "\n";
        return 1;
    }

    return 0;
}
