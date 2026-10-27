#include <algorithm>
#include <chrono>
#include <functional>
#include <iomanip>
#include <iostream>
#include <optional>
#include <queue>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <variant>
#include <vector>

using Scalar = std::variant<std::string, long long, double, bool>;

class ValidationError : public std::runtime_error {
public:
    explicit ValidationError(const std::string& message)
        : std::runtime_error(message) {}
};

class NotFoundError : public std::runtime_error {
public:
    explicit NotFoundError(const std::string& message)
        : std::runtime_error(message) {}
};

enum class DataModel {
    Document,
    KeyValue,
    ColumnFamily,
    Graph
};

struct Document {
    std::string id;
    std::unordered_map<std::string, Scalar> fields;
    std::size_t version{1};
};

class DocumentRepository {
private:
    std::unordered_map<std::string, Document> documents;

public:
    void insert(const std::string& id,
                std::unordered_map<std::string, Scalar> fields) {
        if (id.empty()) {
            throw ValidationError("Document ID cannot be empty.");
        }
        if (documents.contains(id)) {
            throw ValidationError("Document ID already exists.");
        }

        documents.emplace(id, Document{id, std::move(fields), 1});
    }

    void update(const std::string& id,
                const std::unordered_map<std::string, Scalar>& changes) {
        auto it = documents.find(id);
        if (it == documents.end()) {
            throw NotFoundError("Document does not exist.");
        }

        for (const auto& [field, value] : changes) {
            it->second.fields[field] = value;
        }
        ++it->second.version;
    }

    const Document& get(const std::string& id) const {
        auto it = documents.find(id);
        if (it == documents.end()) {
            throw NotFoundError("Document does not exist.");
        }
        return it->second;
    }

    std::vector<std::string> findByField(
        const std::string& field, const Scalar& expected) const {

        std::vector<std::string> result;

        for (const auto& [id, document] : documents) {
            auto fieldIt = document.fields.find(field);
            if (fieldIt != document.fields.end() &&
                fieldIt->second == expected) {
                result.push_back(id);
            }
        }

        return result;
    }
};

class KeyValueStore {
private:
    struct Entry {
        Scalar value;
        std::optional<std::chrono::steady_clock::time_point> expiresAt;
    };

    std::unordered_map<std::string, Entry> values;

    bool expired(const Entry& entry) const {
        return entry.expiresAt.has_value() &&
               std::chrono::steady_clock::now() >= entry.expiresAt.value();
    }

public:
    void set(const std::string& key,
             Scalar value,
             std::optional<std::chrono::seconds> ttl = std::nullopt) {
        if (key.empty() || key.size() > 256) {
            throw ValidationError("Key must contain 1-256 characters.");
        }

        if (ttl.has_value() && ttl->count() <= 0) {
            throw ValidationError("TTL must be positive.");
        }

        std::optional<std::chrono::steady_clock::time_point> expiry;
        if (ttl.has_value()) {
            expiry = std::chrono::steady_clock::now() + ttl.value();
        }

        values[key] = Entry{std::move(value), expiry};
    }

    std::optional<Scalar> get(const std::string& key) {
        auto it = values.find(key);
        if (it == values.end()) {
            return std::nullopt;
        }

        if (expired(it->second)) {
            values.erase(it);
            return std::nullopt;
        }

        return it->second.value;
    }

    bool compareAndSet(const std::string& key,
                       const Scalar& expected,
                       Scalar replacement) {
        auto current = get(key);
        if (!current.has_value() || current.value() != expected) {
            return false;
        }

        set(key, std::move(replacement));
        return true;
    }
};

struct WideRow {
    std::string key;
    std::unordered_map<std::string, Scalar> columns;
};

class ColumnFamilyStore {
private:
    std::unordered_map<std::string, WideRow> rows;

public:
    void put(const std::string& rowKey,
             std::unordered_map<std::string, Scalar> columns) {
        if (rowKey.empty() || columns.empty()) {
            throw ValidationError("Row key and columns are required.");
        }

        auto& row = rows[rowKey];
        row.key = rowKey;

        for (auto& [column, value] : columns) {
            row.columns[column] = std::move(value);
        }
    }

    const WideRow& get(const std::string& rowKey) const {
        auto it = rows.find(rowKey);
        if (it == rows.end()) {
            throw NotFoundError("Wide row does not exist.");
        }
        return it->second;
    }

    std::vector<std::string> findByColumn(
        const std::string& column, const Scalar& expected) const {

        std::vector<std::string> result;

        for (const auto& [key, row] : rows) {
            auto it = row.columns.find(column);
            if (it != row.columns.end() && it->second == expected) {
                result.push_back(key);
            }
        }

        return result;
    }
};

enum class Relationship {
    Owns,
    Contains,
    Uses,
    DependsOn
};

struct Node {
    std::string id;
    std::unordered_set<std::string> labels;
};

struct Edge {
    std::string target;
    Relationship relationship;
};

class GraphStore {
private:
    std::unordered_map<std::string, Node> nodes;
    std::unordered_map<std::string, std::vector<Edge>> adjacency;

public:
    void addNode(std::string id,
                 std::unordered_set<std::string> labels) {
        if (id.empty() || nodes.contains(id)) {
            throw ValidationError("Node ID must be unique and non-empty.");
        }

        nodes.emplace(id, Node{std::move(id), std::move(labels)});
    }

    void addEdge(const std::string& source,
                 const std::string& target,
                 Relationship relationship) {
        if (!nodes.contains(source) || !nodes.contains(target)) {
            throw NotFoundError("Both graph endpoints must exist.");
        }

        adjacency[source].push_back(Edge{target, relationship});
    }

    std::optional<std::vector<std::string>>
    shortestPath(const std::string& start,
                 const std::string& target) const {

        if (!nodes.contains(start) || !nodes.contains(target)) {
            throw NotFoundError("Graph node does not exist.");
        }

        std::queue<std::string> queue;
        std::unordered_map<std::string, std::string> previous;
        std::unordered_set<std::string> visited;

        queue.push(start);
        visited.insert(start);

        while (!queue.empty()) {
            std::string current = queue.front();
            queue.pop();

            if (current == target) {
                std::vector<std::string> path;
                std::string node = target;

                while (node != start) {
                    path.push_back(node);
                    node = previous.at(node);
                }

                path.push_back(start);
                std::reverse(path.begin(), path.end());
                return path;
            }

            auto adjacencyIt = adjacency.find(current);
            if (adjacencyIt == adjacency.end()) {
                continue;
            }

            for (const auto& edge : adjacencyIt->second) {
                if (!visited.contains(edge.target)) {
                    visited.insert(edge.target);
                    previous[edge.target] = current;
                    queue.push(edge.target);
                }
            }
        }

        return std::nullopt;
    }
};

std::string scalarToString(const Scalar& value) {
    return std::visit(
        [](const auto& item) -> std::string {
            if constexpr (std::is_same_v<std::decay_t<decltype(item)>, bool>) {
                return item ? "true" : "false";
            } else {
                return std::to_string(item);
            }
        },
        value
    );
}

int main() {
    try {
        std::cout << "NoSQL Data-Model Governance Case Study\n";
        std::cout << "=====================================\n\n";

        DocumentRepository documents;
        documents.insert(
            "device-01",
            {
                {"name", std::string("GNSS-01")},
                {"region", std::string("Lucknow")},
                {"active", true},
                {"signal", 94LL}
            }
        );

        documents.insert(
            "device-02",
            {
                {"name", std::string("GNSS-02")},
                {"region", std::string("Delhi")},
                {"active", true},
                {"signal", 87LL}
            }
        );

        documents.update(
            "device-01",
            {{"firmware", std::string("3.2.1")}}
        );

        std::cout << "DOCUMENT MODEL\n";
        for (const auto& id : documents.findByField("region", std::string("Lucknow"))) {
            std::cout << "Matched: " << id << "\n";
        }

        KeyValueStore sessions;
        sessions.set(
            "session:device-01",
            std::string("authenticated"),
            std::chrono::seconds(60)
        );

        std::cout << "\nKEY-VALUE MODEL\n";
        auto session = sessions.get("session:device-01");
        if (session.has_value()) {
            std::cout << "Session state: "
                      << scalarToString(session.value()) << "\n";
        }

        ColumnFamilyStore telemetry;
        telemetry.put(
            "device-01",
            {
                {"region", std::string("Lucknow")},
                {"temperature", 31.5},
                {"signal", 94LL}
            }
        );

        telemetry.put(
            "device-02",
            {
                {"region", std::string("Delhi")},
                {"signal", 87LL}
            }
        );

        std::cout << "\nCOLUMN-FAMILY MODEL\n";
        for (const auto& key :
             telemetry.findByColumn("signal", 94LL)) {
            std::cout << "Strong signal row: " << key << "\n";
        }

        GraphStore graph;
        graph.addNode("team", {"Team"});
        graph.addNode("repository", {"Repository"});
        graph.addNode("service", {"Service"});
        graph.addNode("database", {"Database"});

        graph.addEdge("team", "repository", Relationship::Owns);
        graph.addEdge("repository", "service", Relationship::Contains);
        graph.addEdge("service", "database", Relationship::Uses);

        std::cout << "\nGRAPH MODEL\n";
        auto path = graph.shortestPath("team", "database");

        if (path.has_value()) {
            std::cout << "Path: ";
            for (std::size_t i = 0; i < path->size(); ++i) {
                if (i != 0) std::cout << " -> ";
                std::cout << path->at(i);
            }
            std::cout << "\n";
        }

        std::cout << "\nEDGE CASE VALIDATION\n";

        try {
            documents.insert("", {});
        } catch (const ValidationError& error) {
            std::cout << "Rejected invalid document: "
                      << error.what() << "\n";
        }

        try {
            graph.addEdge("missing", "database", Relationship::Uses);
        } catch (const NotFoundError& error) {
            std::cout << "Rejected invalid relationship: "
                      << error.what() << "\n";
        }

        std::cout << "\nENGINEERING TRADE-OFFS\n";
        std::cout << "Document: flexible records and aggregate-oriented reads.\n";
        std::cout << "Key-value: O(1)-average direct key lookup using hashing.\n";
        std::cout << "Column-family: sparse rows avoid requiring every column.\n";
        std::cout << "Graph: adjacency traversal is efficient for connected data.\n";
        std::cout << "Security: validate identifiers, isolate authorization,\n"
                     "and never treat arbitrary stored values as executable input.\n";

        return 0;
    } catch (const std::exception& error) {
        std::cerr << "Fatal error: " << error.what() << '\n';
        return 1;
    }
}
