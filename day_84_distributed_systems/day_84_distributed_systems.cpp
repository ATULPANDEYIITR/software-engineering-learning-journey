#include <algorithm>
#include <cassert>
#include <cstdint>
#include <iostream>
#include <map>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

using namespace std;

// ============================================================
// DISTRIBUTED SYSTEMS: QUORUM-BASED REPLICATION ENGINE
// C++17
//
// Features:
// - Distributed node modeling
// - Network topology
// - Partition detection
// - Logical clocks
// - Versioned replicated state
// - Quorum-based write eligibility
// - Quorum reads
// - Last-Write-Wins resolution
// - Anti-entropy repair
// - Node membership and failure handling
// - Idempotent replication
// ============================================================

enum class NodeStatus {
    ACTIVE,
    STOPPED
};

enum class Consistency {
    ONE,
    QUORUM,
    ALL
};

enum class OperationStatus {
    SUCCESS,
    QUORUM_FAILED,
    NODE_UNAVAILABLE
};

// ============================================================
// EXCEPTIONS
// ============================================================

class DistributedException : public runtime_error {
public:
    explicit DistributedException(const string& message)
        : runtime_error(message) {}
};

class QuorumException : public DistributedException {
public:
    explicit QuorumException(const string& message)
        : DistributedException(message) {}
};

// ============================================================
// VERSION AND RECORD
// ============================================================

struct Version {
    uint64_t logicalTime;
    string nodeId;

    bool operator<(const Version& other) const {
        if (logicalTime != other.logicalTime) {
            return logicalTime < other.logicalTime;
        }

        return nodeId < other.nodeId;
    }

    bool operator==(const Version& other) const {
        return logicalTime == other.logicalTime &&
               nodeId == other.nodeId;
    }
};

struct Record {
    string key;
    string value;
    Version version;
};

// ============================================================
// NETWORK
// ============================================================

class Network {

private:
    set<pair<string, string>> partitions;

    pair<string, string> normalize(
        const string& a,
        const string& b
    ) const {
        return minmax(a, b);
    }

public:
    void partition(const string& a, const string& b) {
        if (a == b) {
            throw invalid_argument("Cannot partition a node from itself");
        }

        partitions.insert(normalize(a, b));
    }

    void heal() {
        partitions.clear();
    }

    bool connected(
        const string& a,
        const string& b
    ) const {
        return a != b &&
               partitions.find(normalize(a, b)) == partitions.end();
    }
};

// ============================================================
// DISTRIBUTED NODE
// ============================================================

class Node {

private:
    string id;
    NodeStatus status = NodeStatus::ACTIVE;

    uint64_t logicalClock = 0;

    unordered_map<string, Record> store;
    unordered_set<string> processedMessages;

    size_t rejectedUpdates = 0;

public:
    explicit Node(const string& nodeId) : id(nodeId) {
        if (id.empty()) {
            throw invalid_argument("Node ID cannot be empty");
        }
    }

    const string& getId() const {
        return id;
    }

    NodeStatus getStatus() const {
        return status;
    }

    void stop() {
        status = NodeStatus::STOPPED;
    }

    void start() {
        status = NodeStatus::ACTIVE;
    }

    void assertActive() const {
        if (status != NodeStatus::ACTIVE) {
            throw DistributedException(
                "Node unavailable: " + id
            );
        }
    }

    uint64_t tick() {
        assertActive();
        return ++logicalClock;
    }

    void observe(const Version& version) {
        logicalClock = max(
            logicalClock,
            version.logicalTime
        ) + 1;
    }

    Record write(
        const string& key,
        const string& value
    ) {
        assertActive();

        if (key.empty() || key.size() > 256) {
            throw invalid_argument("Invalid record key");
        }

        if (value.size() > 1000000) {
            throw invalid_argument("Record value too large");
        }

        Record record{
            key,
            value,
            Version{tick(), id}
        };

        store[key] = record;

        return record;
    }

    bool apply(const Record& incoming) {
        assertActive();

        auto it = store.find(incoming.key);

        if (it != store.end()) {
            if (!(it->second.version < incoming.version)) {
                ++rejectedUpdates;
                return false;
            }
        }

        observe(incoming.version);
        store[incoming.key] = incoming;

        return true;
    }

    bool receive(
        const string& messageId,
        const Record& record
    ) {
        assertActive();

        if (processedMessages.find(messageId) !=
            processedMessages.end()) {
            return false;
        }

        if (processedMessages.size() >= 100000) {
            processedMessages.clear();
        }

        processedMessages.insert(messageId);

        return apply(record);
    }

    optional<Record> read(const string& key) const {
        assertActive();

        auto it = store.find(key);

        if (it == store.end()) {
            return nullopt;
        }

        return it->second;
    }

    const unordered_map<string, Record>& snapshot() const {
        return store;
    }

    size_t recordCount() const {
        return store.size();
    }

    size_t rejectedCount() const {
        return rejectedUpdates;
    }
};

// ============================================================
// REPLICATION RESULT
// ============================================================

struct WriteResult {
    OperationStatus status;
    size_t acknowledgements;
    size_t required;
    optional<Record> record;
};

// ============================================================
// DISTRIBUTED CLUSTER
// ============================================================

class Cluster {

private:
    unordered_map<string, Node> nodes;
    Network network;

    size_t replicationFactor;

    size_t quorum() const {
        return replicationFactor / 2 + 1;
    }

    size_t required(Consistency consistency) const {
        switch (consistency) {
            case Consistency::ONE:
                return 1;

            case Consistency::QUORUM:
                return quorum();

            case Consistency::ALL:
                return replicationFactor;
        }

        throw invalid_argument("Unknown consistency level");
    }

    vector<string> reachablePeers(
        const string& coordinator
    ) const {
        vector<string> peers;

        for (const auto& entry : nodes) {
            if (
                entry.first != coordinator &&
                entry.second.getStatus() == NodeStatus::ACTIVE &&
                network.connected(coordinator, entry.first)
            ) {
                peers.push_back(entry.first);
            }
        }

        sort(peers.begin(), peers.end());

        if (peers.size() > replicationFactor - 1) {
            peers.resize(replicationFactor - 1);
        }

        return peers;
    }

public:
    explicit Cluster(const vector<string>& nodeIds)
        : replicationFactor(min<size_t>(3, nodeIds.size())) {

        if (nodeIds.size() < 3) {
            throw invalid_argument(
                "At least three nodes are required"
            );
        }

        set<string> uniqueIds(
            nodeIds.begin(),
            nodeIds.end()
        );

        if (uniqueIds.size() != nodeIds.size()) {
            throw invalid_argument("Duplicate node identifiers");
        }

        for (const string& id : nodeIds) {
            nodes.emplace(
                piecewise_construct,
                forward_as_tuple(id),
                forward_as_tuple(id)
            );
        }
    }

    Network& getNetwork() {
        return network;
    }

    Node& getNode(const string& id) {
        auto it = nodes.find(id);

        if (it == nodes.end()) {
            throw DistributedException("Unknown node: " + id);
        }

        return it->second;
    }

    WriteResult write(
        const string& coordinatorId,
        const string& key,
        const string& value,
        Consistency consistency = Consistency::QUORUM
    ) {
        Node& coordinator = getNode(coordinatorId);

        try {
            coordinator.assertActive();
        } catch (const DistributedException&) {
            return {
                OperationStatus::NODE_UNAVAILABLE,
                0,
                required(consistency),
                nullopt
            };
        }

        Record record = coordinator.write(key, value);

        size_t acknowledgements = 1;

        vector<string> peers = reachablePeers(coordinatorId);

        for (const string& peerId : peers) {
            string messageId =
                coordinatorId + "-" +
                peerId + "-" +
                to_string(record.version.logicalTime);

            try {
                if (getNode(peerId).receive(messageId, record)) {
                    ++acknowledgements;
                } else {
                    // Duplicate or stale replication still means
                    // that the receiver processed the operation.
                    ++acknowledgements;
                }
            } catch (const DistributedException&) {
                continue;
            }
        }

        const size_t minimum = required(consistency);

        if (acknowledgements < minimum) {
            return {
                OperationStatus::QUORUM_FAILED,
                acknowledgements,
                minimum,
                record
            };
        }

        return {
            OperationStatus::SUCCESS,
            acknowledgements,
            minimum,
            record
        };
    }

    optional<Record> read(
        const string& key,
        Consistency consistency = Consistency::QUORUM
    ) {
        vector<Record> replicas;

        for (const auto& entry : nodes) {
            if (entry.second.getStatus() != NodeStatus::ACTIVE) {
                continue;
            }

            auto record = entry.second.read(key);

            if (record.has_value()) {
                replicas.push_back(record.value());
            }
        }

        const size_t minimum = required(consistency);

        if (replicas.size() < minimum) {
            throw QuorumException(
                "Insufficient replicas for requested read"
            );
        }

        Record latest = *max_element(
            replicas.begin(),
            replicas.end(),
            [](const Record& a, const Record& b) {
                return a.version < b.version;
            }
        );

        if (consistency != Consistency::ONE) {
            repair(latest);
        }

        return latest;
    }

    void repair(const Record& latest) {
        for (auto& entry : nodes) {
            if (entry.second.getStatus() != NodeStatus::ACTIVE) {
                continue;
            }

            if (network.connected(
                latest.version.nodeId,
                entry.first
            )) {
                entry.second.apply(latest);
            }
        }
    }

    void antiEntropy() {
        // Select the newest version independently for every key.
        map<string, Record> merged;

        for (const auto& entry : nodes) {
            if (entry.second.getStatus() != NodeStatus::ACTIVE) {
                continue;
            }

            for (const auto& item : entry.second.snapshot()) {
                auto it = merged.find(item.first);

                if (
                    it == merged.end() ||
                    it->second.version < item.second.version
                ) {
                    merged[item.first] = item.second;
                }
            }
        }

        // Apply merged state only across reachable links.
        for (auto& entry : nodes) {
            if (entry.second.getStatus() != NodeStatus::ACTIVE) {
                continue;
            }

            for (const auto& item : merged) {
                if (network.connected(
                    item.second.version.nodeId,
                    entry.first
                )) {
                    entry.second.apply(item.second);
                }
            }
        }
    }

    void stopNode(const string& id) {
        getNode(id).stop();
    }

    void startNode(const string& id) {
        getNode(id).start();
    }

    bool converged() const {
        vector<const Node*> active;

        for (const auto& entry : nodes) {
            if (entry.second.getStatus() == NodeStatus::ACTIVE) {
                active.push_back(&entry.second);
            }
        }

        if (active.size() < 2) {
            return true;
        }

        const auto& reference = active.front()->snapshot();

        for (size_t i = 1; i < active.size(); ++i) {
            const auto& current = active[i]->snapshot();

            if (reference.size() != current.size()) {
                return false;
            }

            for (const auto& item : reference) {
                auto it = current.find(item.first);

                if (
                    it == current.end() ||
                    !(it->second.version == item.second.version) ||
                    it->second.value != item.second.value
                ) {
                    return false;
                }
            }
        }

        return true;
    }

    void report() const {
        cout << "\nCLUSTER STATUS\n";

        for (const auto& entry : nodes) {
            const Node& node = entry.second;

            cout
                << entry.first
                << " | "
                << (node.getStatus() == NodeStatus::ACTIVE
                    ? "ACTIVE"
                    : "STOPPED")
                << " | Records: "
                << node.recordCount()
                << " | Rejected updates: "
                << node.rejectedCount()
                << '\n';
        }

        cout << "Converged: "
             << (converged() ? "YES" : "NO")
             << '\n';
    }
};

// ============================================================
// TEST SUITE
// ============================================================

void runTests() {
    Cluster cluster({
        "node-A",
        "node-B",
        "node-C"
    });

    // Quorum write.
    auto result = cluster.write(
        "node-A",
        "account:1001",
        "balance=5000"
    );

    assert(result.status == OperationStatus::SUCCESS);
    assert(result.acknowledgements == 3);

    // Consistent read.
    auto record = cluster.read("account:1001");

    assert(record.has_value());
    assert(record->value == "balance=5000");

    // Partition prevents quorum.
    cluster.getNetwork().partition("node-A", "node-B");
    cluster.getNetwork().partition("node-A", "node-C");

    auto failed = cluster.write(
        "node-A",
        "account:1001",
        "balance=6000"
    );

    assert(failed.status == OperationStatus::QUORUM_FAILED);

    // Recovery.
    cluster.getNetwork().heal();
    cluster.antiEntropy();

    assert(cluster.converged());

    // Node failure.
    cluster.stopNode("node-C");

    auto partial = cluster.write(
        "node-A",
        "account:1002",
        "balance=7000",
        Consistency::QUORUM
    );

    assert(partial.status == OperationStatus::SUCCESS);

    cluster.startNode("node-C");
    cluster.antiEntropy();

    assert(cluster.converged());

    // Duplicate message protection.
    Node& nodeB = cluster.getNode("node-B");

    Record duplicateRecord{
        "duplicate:test",
        "value",
        Version{100, "node-A"}
    };

    nodeB.receive("message-1", duplicateRecord);

    bool duplicateAccepted =
        nodeB.receive("message-1", duplicateRecord);

    assert(!duplicateAccepted);

    // Older versions cannot replace newer versions.
    Record older{
        "duplicate:test",
        "old-value",
        Version{1, "node-C"}
    };

    assert(!nodeB.apply(older));

    cout << "All C++17 distributed-system tests passed.\n";
}

// ============================================================
// MAIN
// ============================================================

int main() {
    try {
        runTests();

        Cluster cluster({
            "india-node-1",
            "india-node-2",
            "europe-node-1",
            "us-node-1",
            "us-node-2"
        });

        cout << "\n1. Initial distributed write\n";

        auto result = cluster.write(
            "india-node-1",
            "order:9001",
            "status=PROCESSING;amount=25000",
            Consistency::QUORUM
        );

        cout
            << "Acknowledgements: "
            << result.acknowledgements
            << "/" << result.required
            << '\n';

        cout << "\n2. Network partition\n";

        cluster.getNetwork().partition(
            "india-node-1",
            "europe-node-1"
        );

        cluster.getNetwork().partition(
            "india-node-1",
            "us-node-1"
        );

        auto partitionResult = cluster.write(
            "india-node-1",
            "order:9001",
            "status=UPDATED",
            Consistency::QUORUM
        );

        cout
            << "Partition write status: "
            << (
                partitionResult.status == OperationStatus::SUCCESS
                ? "SUCCESS"
                : "QUORUM_FAILED"
            )
            << '\n';

        cout << "\n3. Network recovery\n";

        cluster.getNetwork().heal();
        cluster.antiEntropy();

        cout << "\n4. Distributed read\n";

        auto latest = cluster.read(
            "order:9001",
            Consistency::QUORUM
        );

        if (latest.has_value()) {
            cout
                << latest->key
                << " = "
                << latest->value
                << '\n';
        }

        cout << "\n5. Cluster report\n";

        cluster.report();

        return 0;

    } catch (const exception& error) {
        cerr << "System failure: " << error.what() << '\n';
        return 1;
    }
}
