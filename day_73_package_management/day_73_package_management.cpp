#include <algorithm>
#include <functional>
#include <iostream>
#include <map>
#include <optional>
#include <regex>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace std;

class PackageException : public runtime_error {
public:
    using runtime_error::runtime_error;
};

struct Version {
    int major, minor, patch;

    static Version parse(const string& value) {
        static const regex pattern(
            R"(^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$)"
        );

        smatch match;

        if (!regex_match(value, match, pattern)) {
            throw PackageException("Invalid semantic version: " + value);
        }

        try {
            return {
                stoi(match[1]),
                stoi(match[2]),
                stoi(match[3])
            };
        } catch (const exception&) {
            throw PackageException("Version component out of range");
        }
    }

    bool operator<(const Version& other) const {
        return tie(major, minor, patch) <
               tie(other.major, other.minor, other.patch);
    }

    bool operator==(const Version& other) const {
        return tie(major, minor, patch) ==
               tie(other.major, other.minor, other.patch);
    }

    bool operator<=(const Version& other) const {
        return *this < other || *this == other;
    }

    bool operator>(const Version& other) const {
        return other < *this;
    }

    bool operator>=(const Version& other) const {
        return other <= *this;
    }

    string str() const {
        return to_string(major) + "." +
               to_string(minor) + "." +
               to_string(patch);
    }
};

struct Constraint {
    static bool matches(const Version& version, const string& expression) {
        if (expression.empty() || expression == "*") {
            return true;
        }

        stringstream stream(expression);
        string token;

        while (getline(stream, token, ',')) {
            if (token.empty()) {
                throw PackageException("Empty version constraint");
            }

            string op = "=";
            string target = token;

            for (const string& candidate :
                 {">=", "<=", ">", "<", "=", "^", "~"}) {
                if (token.rfind(candidate, 0) == 0) {
                    op = candidate;
                    target = token.substr(candidate.size());
                    break;
                }
            }

            Version required = Version::parse(target);

            if (op == "=" && !(version == required)) return false;
            if (op == ">" && !(version > required)) return false;
            if (op == "<" && !(version < required)) return false;
            if (op == ">=" && !(version >= required)) return false;
            if (op == "<=" && !(version <= required)) return false;

            if (op == "^") {
                Version upper = required.major > 0
                    ? Version{required.major + 1, 0, 0}
                    : required.minor > 0
                        ? Version{0, required.minor + 1, 0}
                        : Version{0, 0, required.patch + 1};

                if (!(version >= required && version < upper)) {
                    return false;
                }
            }

            if (op == "~") {
                Version upper{
                    required.major,
                    required.minor + 1,
                    0
                };

                if (!(version >= required && version < upper)) {
                    return false;
                }
            }
        }

        return true;
    }
};

enum class PackageStatus {
    Available,
    Deprecated,
    Vulnerable
};

struct Package {
    string name;
    Version version;
    map<string, string> dependencies;
    PackageStatus status = PackageStatus::Available;
};

struct Installation {
    map<string, Package> packages;
};

class Registry {
private:
    map<string, vector<Package>> packages;

public:
    void publish(const Package& package) {
        static const regex validName(
            R"(^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,99}$)"
        );

        if (!regex_match(package.name, validName)) {
            throw PackageException("Invalid package name");
        }

        auto& versions = packages[package.name];

        for (const auto& existing : versions) {
            if (existing.version == package.version) {
                throw PackageException("Duplicate package version");
            }
        }

        versions.push_back(package);

        sort(
            versions.begin(),
            versions.end(),
            [](const Package& a, const Package& b) {
                return b.version < a.version;
            }
        );
    }

    const vector<Package>& getVersions(const string& name) const {
        auto iterator = packages.find(name);

        if (iterator == packages.end()) {
            throw PackageException("Unknown package: " + name);
        }

        return iterator->second;
    }

    vector<Package> candidates(
        const string& name,
        const vector<string>& constraints
    ) const {
        vector<Package> result;

        for (const auto& package : getVersions(name)) {
            if (package.status != PackageStatus::Available) {
                continue;
            }

            bool valid = all_of(
                constraints.begin(),
                constraints.end(),
                [&](const string& constraint) {
                    return Constraint::matches(
                        package.version, constraint
                    );
                }
            );

            if (valid) result.push_back(package);
        }

        return result;
    }
};

class DependencyResolver {
private:
    const Registry& registry;

    map<string, Package> selected;
    map<string, vector<string>> constraints;

    set<string> resolving;
    set<string> resolved;

    bool search() {
        string next;

        for (const auto& [name, rules] : constraints) {
            if (!resolved.count(name)) {
                next = name;
                break;
            }
        }

        if (next.empty()) return true;

        if (resolving.count(next)) {
            return false;
        }

        vector<Package> choices;

        try {
            choices = registry.candidates(next, constraints[next]);
        } catch (const PackageException&) {
            return false;
        }

        for (const auto& candidate : choices) {
            auto oldSelected = selected;
            auto oldConstraints = constraints;
            auto oldResolving = resolving;
            auto oldResolved = resolved;

            selected[next] = candidate;
            resolving.insert(next);

            bool cycle = false;

            for (const auto& [dependency, requirement] :
                 candidate.dependencies) {
                constraints[dependency].push_back(requirement);

                if (resolving.count(dependency)) {
                    cycle = true;
                    break;
                }
            }

            resolving.erase(next);

            if (!cycle) {
                resolved.insert(next);

                if (search()) return true;
            }

            selected = move(oldSelected);
            constraints = move(oldConstraints);
            resolving = move(oldResolving);
            resolved = move(oldResolved);
        }

        return false;
    }

public:
    explicit DependencyResolver(const Registry& source)
        : registry(source) {}

    Installation resolve(
        const map<string, string>& requirements
    ) {
        selected.clear();
        constraints.clear();
        resolving.clear();
        resolved.clear();

        for (const auto& [name, rule] : requirements) {
            constraints[name].push_back(rule);
        }

        if (!search()) {
            throw PackageException(
                "Dependency graph cannot be resolved"
            );
        }

        return {selected};
    }
};

class GovernanceEngine {
private:
    const Registry& registry;
    Installation installed;

public:
    explicit GovernanceEngine(const Registry& source)
        : registry(source) {}

    Installation install(
        const map<string, string>& requirements
    ) {
        DependencyResolver resolver(registry);

        Installation plan = resolver.resolve(requirements);

        // Validate the complete plan before committing the state.
        for (const auto& [name, package] : plan.packages) {
            if (package.status != PackageStatus::Available) {
                throw PackageException(
                    "Package is not permitted: " + name
                );
            }

            auto existing = installed.packages.find(name);

            if (existing != installed.packages.end() &&
                package.version < existing->second.version) {
                throw PackageException(
                    "Downgrade rejected: " + name
                );
            }
        }

        Installation nextState = installed;

        for (const auto& [name, package] : plan.packages) {
            nextState.packages[name] = package;
        }

        installed = move(nextState);

        return plan;
    }

    void uninstall(const string& name) {
        if (!installed.packages.count(name)) {
            throw PackageException("Package not installed");
        }

        for (const auto& [other, package] : installed.packages) {
            if (other != name && package.dependencies.count(name)) {
                throw PackageException(
                    "Cannot remove dependency of " + other
                );
            }
        }

        installed.packages.erase(name);
    }

    void display() const {
        cout << "\nInstalled dependency graph:\n";

        for (const auto& [name, package] : installed.packages) {
            cout << name << "@" << package.version.str() << "\n";

            for (const auto& [dependency, requirement] :
                 package.dependencies) {
                cout << "  -> " << dependency
                     << " (" << requirement << ")\n";
            }
        }
    }

    size_t packageCount() const {
        return installed.packages.size();
    }
};

int main() {
    try {
        Registry registry;

        registry.publish({
            "core",
            Version::parse("1.0.0"),
            {}
        });

        registry.publish({
            "core",
            Version::parse("1.2.0"),
            {}
        });

        registry.publish({
            "core",
            Version::parse("2.0.0"),
            {}
        });

        registry.publish({
            "database",
            Version::parse("1.0.0"),
            {{"core", "^1.0.0"}}
        });

        registry.publish({
            "database",
            Version::parse("2.0.0"),
            {{"core", "^2.0.0"}}
        });

        registry.publish({
            "api-server",
            Version::parse("1.0.0"),
            {
                {"core", "^1.0.0"},
                {"database", "^1.0.0"}
            }
        });

        registry.publish({
            "api-server",
            Version::parse("1.1.0"),
            {
                {"core", "^1.0.0"},
                {"database", "^1.0.0"}
            }
        });

        GovernanceEngine engine(registry);

        cout << "PACKAGE GOVERNANCE ENGINE\n";
        cout << "=========================\n";

        auto result = engine.install({
            {"api-server", "^1.0.0"}
        });

        cout << "\nInstallation plan:\n";

        for (const auto& [name, package] : result.packages) {
            cout << name << "@" << package.version.str() << "\n";
        }

        engine.display();

        cout << "\nInstalled package count: "
             << engine.packageCount() << "\n";

        cout << "\nConstraint evaluation:\n";

        cout << Constraint::matches(
            Version::parse("1.5.0"), "^1.0.0"
        ) << "\n";

        cout << Constraint::matches(
            Version::parse("2.0.0"), "^1.0.0"
        ) << "\n";

        cout << "\nConflict test:\n";

        try {
            engine.install({
                {"core", "^1.0.0"},
                {"database", "^2.0.0"}
            });
        } catch (const PackageException& error) {
            cout << "Rejected: " << error.what() << "\n";
        }

        cout << "\nUninstallation test:\n";

        try {
            engine.uninstall("core");
        } catch (const PackageException& error) {
            cout << "Rejected: " << error.what() << "\n";
        }

        cout << "\nAll governance checks completed.\n";

    } catch (const exception& error) {
        cerr << "Fatal error: " << error.what() << "\n";
        return 1;
    }

    return 0;
}
