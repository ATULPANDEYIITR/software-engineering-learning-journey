#include <algorithm>
#include <cassert>
#include <cstdint>
#include <exception>
#include <iostream>
#include <map>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

/*
 * CAP Theorem: Distributed Repository-Independent Storage Engine
 *
 * C++17 implementation.
 *
 * Models:
 * - Distributed replica membership
 * - Network partitions
 * - CP quorum requirements
 * - AP local writes
 * - Replica versions
 * - Conflict resolution
 * - Failure handling
 * - Merge and reconciliation of replica state
 *
 * The model is educational. It does not implement Raft or Paxos.
 */

enum class CAPMode {
    CP,
    AP
};

enum class ResultStatus {
    Success,
    Rejected,
    Unavailable
};

struct Version {
    std::uint64_t logicalTime;
    std::string writer;

    bool operator<(const Version& other) const {
        if (logicalTime != other.logicalTime) {
            return logicalTime < other.logicalTime;
        }
        return writer < other.writer;
    }
};

struct Record {
    std::string key;
    std::string value;
    Version version;
};

struct OperationResult {
    ResultStatus status;
    std::string message;
    std::optional<std::string> value;
};

class ValidationError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

class Replica {
private:
    std::string id_;
    bool available_;
    int partition_;
    std::unordered_map<std::string, Record> records_;

public:
    explicit Replica(std::string id)
        : id_(std::move(id)),
          available_(true),
          partition_(0) {
        if (id_.empty()) {
            throw ValidationError("Replica ID cannot be empty.");
        }
    }

    const std::string& id() const {
        return id_;
    }

    bool available() const {
        return available_;
    }

    int partition() const {
        return partition_;
    }

    void setAvailable(bool value) {
        available_ = value;
    }

    void setPartition(int value) {
        partition_ = value;
    }

    const std::unordered_map<std::string, Record>& records() const {
        return records_;
    }

    std::optional<Record> read(const std::string& key) const {
        if (!available_) {
            throw std::runtime_error("Replica unavailable: " + id_);
        }

        auto it = records_.find(key);

        if (it == records_.end()) {
            return std::nullopt;
        }

        return it->second;
    }

    void apply(const Record& record) {
        if (!available_) {
            throw std::runtime_error("Cannot write to unavailable replica.");
        }

        auto it = records_.find(record.key);

        if (it == records_.end() ||
            it->second.version < record.version) {
            records_[record.key] = record;
        }
    }
};

class DistributedCluster {
private:
    CAPMode mode_;
    std::vector<Replica> replicas_;
    std::uint64_t logicalClock_;

    Replica& findReplica(const std::string& id) {
        auto it = std::find_if(
            replicas_.begin(),
            replicas_.end(),
            [&](const Replica& replica) {
                return replica.id() == id;
            }
        );

        if (it == replicas_.end()) {
            throw ValidationError("Unknown replica: " + id);
        }

        return *it;
    }

    const Replica& findReplica(const std::string& id) const {
        auto it = std::find_if(
            replicas_.begin(),
            replicas_.end(),
            [&](const Replica& replica) {
                return replica.id() == id;
            }
        );

        if (it == replicas_.end()) {
            throw ValidationError("Unknown replica: " + id);
        }

        return *it;
    }

    std::vector<Replica*> connectedReplicas(const std::string& id) {
        Replica& requester = findReplica(id);
        std::vector<Replica*> connected;

        if (!requester.available()) {
            return connected;
        }

        for (auto& replica : replicas_) {
            if (replica.available() &&
                replica.partition() == requester.partition()) {
                connected.push_back(&replica);
            }
        }

        return connected;
    }

    static bool newer(const Record& a, const Record& b) {
        return b.version < a.version;
    }

public:
    explicit DistributedCluster(
        std::size_t nodeCount,
        CAPMode mode
    )
        : mode_(mode), logicalClock_(0) {

        if (nodeCount == 0 || nodeCount > 1000) {
            throw ValidationError("Node count must be between 1 and 1000.");
        }

        for (std::size_t i = 0; i < nodeCount; ++i) {
            replicas_.emplace_back("node-" + std::to_string(i + 1));
        }
    }

    std::size_t quorum() const {
        return replicas_.size() / 2 + 1;
    }

    void partition(
        const std::vector<std::vector<std::string>>& groups
    ) {
        if (groups.empty()) {
            throw ValidationError("At least one partition is required.");
        }

        std::map<std::string, int> assignments;
        int groupNumber = 0;

        for (const auto& group : groups) {
            if (group.empty()) {
                throw ValidationError("Empty partition group.");
            }

            for (const auto& id : group) {
                findReplica(id);

                if (assignments.count(id)) {
                    throw ValidationError("Duplicate replica in partition.");
                }

                assignments[id] = groupNumber;
            }

            ++groupNumber;
        }

        for (auto& replica : replicas_) {
            auto it = assignments.find(replica.id());

            replica.setPartition(
                it == assignments.end()
                    ? groupNumber++
                    : it->second
            );
        }
    }

    void setAvailability(
        const std::string& id,
        bool available
    ) {
        findReplica(id).setAvailable(available);
    }

    OperationResult write(
        const std::string& nodeId,
        const std::string& key,
        const std::string& value
    ) {
        if (key.empty()) {
            throw ValidationError("Key cannot be empty.");
        }

        if (key.size() > 255 || value.size() > 10000) {
            throw ValidationError("Record exceeds configured limits.");
        }

        auto connected = connectedReplicas(nodeId);

        if (connected.empty()) {
            return {
                ResultStatus::Unavailable,
                "Requesting replica is unavailable.",
                std::nullopt
            };
        }

        if (mode_ == CAPMode::CP &&
            connected.size() < quorum()) {
            return {
                ResultStatus::Rejected,
                "Majority quorum unavailable.",
                std::nullopt
            };
        }

        Record record{
            key,
            value,
            Version{++logicalClock_, nodeId}
        };

        if (mode_ == CAPMode::CP) {
            for (Replica* replica : connected) {
                replica->apply(record);
            }
        } else {
            findReplica(nodeId).apply(record);
        }

        return {
            ResultStatus::Success,
            "Write acknowledged.",
            value
        };
    }

    OperationResult read(
        const std::string& nodeId,
        const std::string& key
    ) {
        auto connected = connectedReplicas(nodeId);

        if (connected.empty()) {
            return {
                ResultStatus::Unavailable,
                "No available replica.",
                std::nullopt
            };
        }

        if (mode_ == CAPMode::CP &&
            connected.size() < quorum()) {
            return {
                ResultStatus::Unavailable,
                "Quorum unavailable for read.",
                std::nullopt
            };
        }

        if (mode_ == CAPMode::AP) {
            auto record = findReplica(nodeId).read(key);

            return {
                ResultStatus::Success,
                "Local replica read.",
                record ? std::optional<std::string>(record->value)
                       : std::nullopt
            };
        }

        std::optional<Record> latest;

        for (Replica* replica : connected) {
            auto record = replica->read(key);

            if (record &&
                (!latest || newer(*record, *latest))) {
                latest = record;
            }
        }

        return {
            ResultStatus::Success,
            "Quorum read completed.",
            latest ? std::optional<std::string>(latest->value)
                   : std::nullopt
        };
    }

    void healPartition() {
        for (auto& replica : replicas_) {
            replica.setPartition(0);
        }

        std::unordered_map<std::string, Record> merged;

        for (const auto& replica : replicas_) {
            if (!replica.available()) {
                continue;
            }

            for (const auto& entry : replica.records()) {
                const std::string& key = entry.first;
                const Record& record = entry.second;

                auto it = merged.find(key);

                if (it == merged.end() ||
                    newer(record, it->second)) {
                    merged[key] = record;
                }
            }
        }

        for (auto& replica : replicas_) {
            if (!replica.available()) {
                continue;
            }

            for (const auto& entry : merged) {
                replica.apply(entry.second);
            }
        }
    }

    bool isConsistent() const {
        std::optional<std::map<std::string, std::string>> reference;

        for (const auto& replica : replicas_) {
            if (!replica.available()) {
                continue;
            }

            std::map<std::string, std::string> snapshot;

            for (const auto& entry : replica.records()) {
                snapshot[entry.first] = entry.second.value;
            }

            if (!reference) {
                reference = snapshot;
            } else if (*reference != snapshot) {
                return false;
            }
        }

        return true;
    }

    void printState() const {
        std::cout << "\nCluster mode: "
                  << (mode_ == CAPMode::CP ? "CP" : "AP")
                  << "\nQuorum: " << quorum() << "\n";

        for (const auto& replica : replicas_) {
            std::cout << replica.id()
                      << " | partition=" << replica.partition()
                      << " | available="
                      << (replica.available() ? "yes" : "no")
                      << "\n";

            for (const auto& entry : replica.records()) {
                std::cout << "  "
                          << entry.first << " = "
                          << entry.second.value
                          << " (version "
                          << entry.second.version.logicalTime
                          << ")\n";
            }
        }

        std::cout << "Consistent: "
                  << (isConsistent() ? "yes" : "no")
                  << "\n";
    }
};

void demonstrateCP() {
    std::cout << "\n========== CP SYSTEM ==========\n";

    DistributedCluster cluster(3, CAPMode::CP);

    assert(
        cluster.write("node-1", "account", "1000").status
        == ResultStatus::Success
    );

    cluster.partition({
        {"node-1"},
        {"node-2", "node-3"}
    });

    auto minority = cluster.write("node-1", "account", "2000");
    auto majority = cluster.write("node-2", "account", "1500");

    assert(minority.status == ResultStatus::Rejected);
    assert(majority.status == ResultStatus::Success);

    cluster.printState();

    cluster.healPartition();

    cluster.printState();
}

void demonstrateAP() {
    std::cout << "\n========== AP SYSTEM ==========\n";

    DistributedCluster cluster(3, CAPMode::AP);

    cluster.write("node-1", "inventory", "100");

    cluster.partition({
        {"node-1"},
        {"node-2", "node-3"}
    });

    auto first = cluster.write("node-1", "inventory", "80");
    auto second = cluster.write("node-2", "inventory", "90");

    assert(first.status == ResultStatus::Success);
    assert(second.status == ResultStatus::Success);

    cluster.printState();

    cluster.healPartition();

    cluster.printState();

    assert(cluster.isConsistent());
}

void runTests() {
    DistributedCluster cp(3, CAPMode::CP);

    cp.partition({
        {"node-1"},
        {"node-2", "node-3"}
    });

    assert(
        cp.write("node-1", "k", "v1").status
        == ResultStatus::Rejected
    );

    assert(
        cp.write("node-2", "k", "v2").status
        == ResultStatus::Success
    );

    cp.healPartition();
    assert(cp.isConsistent());

    DistributedCluster ap(3, CAPMode::AP);

    ap.partition({
        {"node-1"},
        {"node-2", "node-3"}
    });

    assert(
        ap.write("node-1", "k", "A").status
        == ResultStatus::Success
    );

    assert(
        ap.write("node-2", "k", "B").status
        == ResultStatus::Success
    );

    ap.healPartition();
    assert(ap.isConsistent());

    ap.setAvailability("node-1", false);

    assert(
        ap.read("node-1", "k").status
        == ResultStatus::Unavailable
    );

    try {
        DistributedCluster invalid(0, CAPMode::CP);
        assert(false);
    } catch (const ValidationError&) {
        // Invalid cluster size correctly rejected.
    }

    std::cout << "\nAll C++17 assertions passed.\n";
}

int main() {
    try {
        demonstrateCP();
        demonstrateAP();
        runTests();
    } catch (const std::exception& error) {
        std::cerr << "Execution error: "
                  << error.what() << "\n";
        return 1;
    }

    return 0;
}
