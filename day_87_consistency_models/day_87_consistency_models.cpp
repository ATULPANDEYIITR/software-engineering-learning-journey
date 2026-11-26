#include <algorithm>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <map>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

using namespace std;

enum class ConsistencyModel {
    STRONG,
    EVENTUAL,
    CAUSAL
};

string modelName(ConsistencyModel model) {
    switch (model) {
        case ConsistencyModel::STRONG: return "STRONG";
        case ConsistencyModel::EVENTUAL: return "EVENTUAL";
        case ConsistencyModel::CAUSAL: return "CAUSAL";
    }
    throw logic_error("Unknown consistency model");
}

class VectorClock {
private:
    map<string, uint64_t> values;

public:
    uint64_t get(const string& node) const {
        auto it = values.find(node);
        return it == values.end() ? 0 : it->second;
    }

    void increment(const string& node) {
        ++values[node];
    }

    void merge(const VectorClock& other) {
        for (const auto& [node, count] : other.values) {
            values[node] = max(values[node], count);
        }
    }

    bool dominates(const VectorClock& other) const {
        for (const auto& [node, count] : other.values) {
            if (get(node) < count) return false;
        }
        return true;
    }

    bool concurrent(const VectorClock& other) const {
        return !dominates(other) && !other.dominates(*this);
    }

    bool operator==(const VectorClock& other) const {
        return dominates(other) && other.dominates(*this);
    }

    string toString() const {
        string result = "{";
        bool first = true;

        for (const auto& [node, count] : values) {
            if (!first) result += ", ";
            result += node + ":" + to_string(count);
            first = false;
        }

        return result + "}";
    }
};

struct WriteEvent {
    string id;
    string key;
    string value;
    string origin;
    VectorClock clock;
    VectorClock dependencies;
    uint64_t timestamp;
};

struct Replica {
    string id;
    bool available = true;
    VectorClock clock;
    unordered_map<string, WriteEvent> data;
    vector<WriteEvent> pending;

    bool apply(const WriteEvent& event) {
        auto it = data.find(event.key);

        if (it != data.end()) {
            const WriteEvent& current = it->second;

            if (current.clock.dominates(event.clock)) {
                return false;
            }

            if (current.clock.concurrent(event.clock)) {
                if (
                    current.timestamp > event.timestamp ||
                    (current.timestamp == event.timestamp &&
                     current.origin >= event.origin)
                ) {
                    return false;
                }
            }
        }

        data[event.key] = event;
        clock.merge(event.clock);
        return true;
    }

    optional<string> read(const string& key) const {
        auto it = data.find(key);

        if (it == data.end()) return nullopt;
        return it->second.value;
    }
};

class DistributedStore {
private:
    map<string, Replica> replicas;
    ConsistencyModel model;
    uint64_t sequence = 0;

    static uint64_t currentTimestamp() {
        return static_cast<uint64_t>(
            chrono::duration_cast<chrono::microseconds>(
                chrono::system_clock::now().time_since_epoch()
            ).count()
        );
    }

    Replica& getReplica(const string& id) {
        auto it = replicas.find(id);

        if (it == replicas.end()) {
            throw invalid_argument("Unknown replica: " + id);
        }

        return it->second;
    }

    WriteEvent createEvent(
        Replica& origin,
        const string& key,
        const string& value,
        const VectorClock& context
    ) {
        VectorClock next = origin.clock;
        next.merge(context);
        next.increment(origin.id);

        ++sequence;

        return {
            "event-" + to_string(sequence),
            key,
            value,
            origin.id,
            next,
            context,
            currentTimestamp() + sequence
        };
    }

public:
    DistributedStore(
        const vector<string>& replicaIds,
        ConsistencyModel initialModel
    ) : model(initialModel) {
        if (replicaIds.size() < 2) {
            throw invalid_argument("At least two replicas are required");
        }

        set<string> uniqueIds(
            replicaIds.begin(), replicaIds.end()
        );

        if (uniqueIds.size() != replicaIds.size()) {
            throw invalid_argument("Replica IDs must be unique");
        }

        for (const string& id : replicaIds) {
            if (id.empty()) {
                throw invalid_argument("Replica ID cannot be empty");
            }

            Replica replica;
            replica.id = id;
            replicas.emplace(id, move(replica));
        }
    }

    void setModel(ConsistencyModel newModel) {
        model = newModel;
    }

    void setAvailability(const string& id, bool available) {
        getReplica(id).available = available;
    }

    WriteEvent write(
        const string& replicaId,
        const string& key,
        const string& value,
        const VectorClock& context = VectorClock()
    ) {
        if (key.empty() || key.size() > 200) {
            throw invalid_argument("Key must contain 1 to 200 characters");
        }

        if (value.size() > 1000000) {
            throw invalid_argument("Value exceeds the configured limit");
        }

        Replica& origin = getReplica(replicaId);

        if (!origin.available) {
            throw runtime_error("Origin replica is unavailable");
        }

        if (
            model == ConsistencyModel::CAUSAL &&
            !origin.clock.dominates(context)
        ) {
            throw runtime_error(
                "Causal dependency has not been observed"
            );
        }

        WriteEvent event = createEvent(
            origin, key, value, context
        );

        if (model == ConsistencyModel::STRONG) {
            for (const auto& [id, replica] : replicas) {
                if (!replica.available) {
                    throw runtime_error(
                        "Strong write rejected: " + id + " is unavailable"
                    );
                }
            }

            // No replica is modified until availability validation succeeds.
            for (auto& [id, replica] : replicas) {
                replica.apply(event);
            }
        } else {
            origin.apply(event);

            for (auto& [id, replica] : replicas) {
                if (id != replicaId) {
                    replica.pending.push_back(event);
                }
            }
        }

        return event;
    }

    optional<string> read(
        const string& replicaId,
        const string& key,
        const optional<VectorClock>& context = nullopt
    ) {
        Replica& replica = getReplica(replicaId);

        if (!replica.available) {
            throw runtime_error("Replica is unavailable");
        }

        const WriteEvent* selected = nullptr;

        if (model == ConsistencyModel::STRONG) {
            for (auto& [id, candidate] : replicas) {
                auto it = candidate.data.find(key);

                if (it == candidate.data.end()) continue;

                if (
                    selected == nullptr ||
                    it->second.timestamp > selected->timestamp
                ) {
                    selected = &it->second;
                }
            }
        } else {
            auto it = replica.data.find(key);

            if (it != replica.data.end()) {
                selected = &it->second;
            }
        }

        if (!selected) return nullopt;

        if (
            context.has_value() &&
            !selected->clock.dominates(*context)
        ) {
            throw runtime_error(
                "Read violates the requested causal context"
            );
        }

        return selected->value;
    }

    size_t synchronize() {
        size_t applied = 0;

        for (auto& [id, replica] : replicas) {
            if (!replica.available) continue;

            bool progress = true;

            while (progress && !replica.pending.empty()) {
                progress = false;
                vector<WriteEvent> remaining;

                for (const WriteEvent& event : replica.pending) {
                    if (
                        model == ConsistencyModel::CAUSAL &&
                        !replica.clock.dominates(event.dependencies)
                    ) {
                        remaining.push_back(event);
                        continue;
                    }

                    if (replica.apply(event)) {
                        ++applied;
                    }

                    progress = true;
                }

                replica.pending = move(remaining);
            }
        }

        return applied;
    }

    void printReplicaState(const string& key) const {
        cout << "\nKey: " << key << "\n";

        for (const auto& [id, replica] : replicas) {
            cout << "Replica " << id << ": ";

            auto it = replica.data.find(key);

            if (it == replica.data.end()) {
                cout << "NOT FOUND";
            } else {
                cout << it->second.value
                     << " | clock=" << it->second.clock.toString();
            }

            cout << " | available=" << boolalpha << replica.available
                 << " | pending=" << replica.pending.size()
                 << "\n";
        }
    }

    bool converged(const string& key) const {
        optional<string> reference;

        for (const auto& [id, replica] : replicas) {
            auto value = replica.read(key);

            if (!value.has_value()) return false;

            if (!reference.has_value()) {
                reference = value;
            } else if (reference != value) {
                return false;
            }
        }

        return true;
    }
};

void demonstrateStrong() {
    cout << "\n1. STRONG CONSISTENCY\n";

    DistributedStore store(
        {"mumbai", "delhi", "singapore"},
        ConsistencyModel::STRONG
    );

    store.write("mumbai", "account:1", "balance=50000");

    cout << "Delhi read: "
         << store.read("delhi", "account:1").value() << "\n";

    store.setAvailability("singapore", false);

    try {
        store.write("mumbai", "account:1", "balance=40000");
    } catch (const exception& e) {
        cout << "Write rejected: " << e.what() << "\n";
    }

    store.setAvailability("singapore", true);
    store.printReplicaState("account:1");
}

void demonstrateEventual() {
    cout << "\n2. EVENTUAL CONSISTENCY\n";

    DistributedStore store(
        {"region-a", "region-b", "region-c"},
        ConsistencyModel::EVENTUAL
    );

    store.write("region-a", "inventory:10", "quantity=100");

    store.printReplicaState("inventory:10");

    cout << "Events applied: " << store.synchronize() << "\n";

    store.printReplicaState("inventory:10");

    cout << "Converged: " << boolalpha
         << store.converged("inventory:10") << "\n";
}

void demonstrateCausal() {
    cout << "\n3. CAUSAL CONSISTENCY\n";

    DistributedStore store(
        {"node-a", "node-b", "node-c"},
        ConsistencyModel::CAUSAL
    );

    WriteEvent first = store.write(
        "node-a", "order:1", "CREATED"
    );

    WriteEvent second = store.write(
        "node-a", "payment:1", "INITIATED", first.clock
    );

    cout << "First clock: " << first.clock.toString() << "\n";
    cout << "Second clock: " << second.clock.toString() << "\n";

    store.synchronize();

    cout << "Node B payment: "
         << store.read("node-b", "payment:1").value() << "\n";

    store.printReplicaState("payment:1");
}

void demonstrateFailures() {
    cout << "\n4. FAILURE HANDLING\n";

    DistributedStore store(
        {"primary", "secondary"},
        ConsistencyModel::EVENTUAL
    );

    try {
        store.write("primary", "", "invalid");
    } catch (const exception& e) {
        cout << "Invalid key: " << e.what() << "\n";
    }

    store.setAvailability("secondary", false);

    store.write("primary", "session:1", "ACTIVE");

    cout << "Secondary queue: "
         << "one pending event while offline\n";

    store.setAvailability("secondary", true);
    store.synchronize();

    cout << "Recovered value: "
         << store.read("secondary", "session:1").value() << "\n";
}

int main() {
    try {
        demonstrateStrong();
        demonstrateEventual();
        demonstrateCausal();
        demonstrateFailures();
    } catch (const exception& e) {
        cerr << "Fatal error: " << e.what() << "\n";
        return 1;
    }

    return 0;
}
