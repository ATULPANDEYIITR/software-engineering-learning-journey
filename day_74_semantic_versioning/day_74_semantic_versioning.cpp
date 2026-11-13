#include <algorithm>
#include <cassert>
#include <cctype>
#include <iostream>
#include <map>
#include <optional>
#include <regex>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

using namespace std;

/*
 * Semantic Versioning 2.0.0
 *
 * Repository release governance and dependency compatibility engine.
 * C++17 implementation without external dependencies.
 */

class VersionError : public invalid_argument {
public:
    using invalid_argument::invalid_argument;
};

class ReleaseError : public runtime_error {
public:
    using runtime_error::runtime_error;
};

enum class ChangeType {
    PATCH,
    MINOR,
    MAJOR
};

enum class ReleaseState {
    DRAFT,
    VALIDATED,
    PUBLISHED,
    REJECTED
};

struct Version {
    uint64_t major = 0;
    uint64_t minor = 0;
    uint64_t patch = 0;

    vector<string> prerelease;
    vector<string> build;

    static bool numeric(const string& value) {
        return !value.empty() &&
            all_of(value.begin(), value.end(), [](unsigned char c) {
                return isdigit(c);
            });
    }

    static void validateIdentifier(
        const string& value,
        bool isPrerelease
    ) {
        if (value.empty()) {
            throw VersionError("Empty version identifier");
        }

        for (unsigned char c : value) {
            if (!isalnum(c) && c != '-') {
                throw VersionError("Invalid version identifier");
            }
        }

        if (
            isPrerelease &&
            numeric(value) &&
            value.size() > 1 &&
            value.front() == '0'
        ) {
            throw VersionError(
                "Numeric prerelease identifier has leading zeros"
            );
        }
    }

    static vector<string> split(const string& value) {
        vector<string> result;
        stringstream stream(value);
        string part;

        while (getline(stream, part, '.')) {
            if (part.empty()) {
                throw VersionError("Empty identifier");
            }
            result.push_back(part);
        }

        if (!value.empty() && value.back() == '.') {
            throw VersionError("Trailing identifier separator");
        }

        return result;
    }

    static Version parse(const string& input) {
        static const regex pattern(
            R"(^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$)"
        );

        smatch match;

        if (!regex_match(input, match, pattern)) {
            throw VersionError("Invalid semantic version: " + input);
        }

        try {
            Version version;

            auto parseNumber = [](const string& value) {
                size_t consumed = 0;
                unsigned long long number = stoull(value, &consumed);

                if (consumed != value.size()) {
                    throw VersionError("Invalid numeric component");
                }

                return static_cast<uint64_t>(number);
            };

            version.major = parseNumber(match[1]);
            version.minor = parseNumber(match[2]);
            version.patch = parseNumber(match[3]);

            if (match[4].matched) {
                version.prerelease = split(match[4]);
            }

            if (match[5].matched) {
                version.build = split(match[5]);
            }

            for (const auto& id : version.prerelease) {
                validateIdentifier(id, true);
            }

            for (const auto& id : version.build) {
                validateIdentifier(id, false);
            }

            return version;

        } catch (const out_of_range&) {
            throw VersionError("Version component exceeds uint64 range");
        }
    }

    string str() const {
        string result =
            to_string(major) + "." +
            to_string(minor) + "." +
            to_string(patch);

        if (!prerelease.empty()) {
            result += "-";

            for (size_t i = 0; i < prerelease.size(); ++i) {
                if (i) result += ".";
                result += prerelease[i];
            }
        }

        if (!build.empty()) {
            result += "+";

            for (size_t i = 0; i < build.size(); ++i) {
                if (i) result += ".";
                result += build[i];
            }
        }

        return result;
    }

    static int compareIdentifiers(
        const string& a,
        const string& b
    ) {
        bool an = numeric(a);
        bool bn = numeric(b);

        if (an && bn) {
            // Compare digit strings without integer overflow.
            if (a.size() != b.size()) {
                return a.size() < b.size() ? -1 : 1;
            }

            return a < b ? -1 : a > b ? 1 : 0;
        }

        if (an) return -1;
        if (bn) return 1;

        return a < b ? -1 : a > b ? 1 : 0;
    }

    int compare(const Version& other) const {
        auto left = tie(major, minor, patch);
        auto right = tie(
            other.major,
            other.minor,
            other.patch
        );

        if (left < right) return -1;
        if (left > right) return 1;

        if (prerelease.empty() && other.prerelease.empty()) {
            return 0;
        }

        if (prerelease.empty()) return 1;
        if (other.prerelease.empty()) return -1;

        size_t count = min(
            prerelease.size(),
            other.prerelease.size()
        );

        for (size_t i = 0; i < count; ++i) {
            int result = compareIdentifiers(
                prerelease[i],
                other.prerelease[i]
            );

            if (result != 0) return result;
        }

        return prerelease.size() < other.prerelease.size()
            ? -1
            : prerelease.size() > other.prerelease.size()
                ? 1
                : 0;
    }

    bool operator<(const Version& other) const {
        return compare(other) < 0;
    }

    bool operator==(const Version& other) const {
        return compare(other) == 0;
    }

    bool operator<=(const Version& other) const {
        return compare(other) <= 0;
    }

    Version increment(ChangeType type) const {
        Version result;

        switch (type) {
            case ChangeType::MAJOR:
                if (major == UINT64_MAX) {
                    throw VersionError("Major version overflow");
                }

                result.major = major + 1;
                break;

            case ChangeType::MINOR:
                if (minor == UINT64_MAX) {
                    throw VersionError("Minor version overflow");
                }

                result.major = major;
                result.minor = minor + 1;
                break;

            case ChangeType::PATCH:
                if (patch == UINT64_MAX) {
                    throw VersionError("Patch version overflow");
                }

                result.major = major;
                result.minor = minor;
                result.patch = patch + 1;
                break;
        }

        return result;
    }
};

struct VersionConstraint {
    string operation;
    Version required;

    bool matches(const Version& candidate) const {
        int result = candidate.compare(required);

        if (operation == "=") return result == 0;
        if (operation == ">") return result > 0;
        if (operation == ">=") return result >= 0;
        if (operation == "<") return result < 0;
        if (operation == "<=") return result <= 0;

        throw VersionError("Unsupported constraint operator");
    }
};

struct Release {
    Version version;
    string description;
    ChangeType change;
    ReleaseState state = ReleaseState::DRAFT;
    vector<string> dependencies;
    bool testsPassed = false;
    bool documentationUpdated = false;
    bool migrationNotes = false;
};

class GovernanceEngine {
private:
    map<string, Release> releases;
    optional<Version> currentVersion;

public:
    void registerRelease(const Release& release) {
        string key = release.version.str();

        if (releases.count(key)) {
            throw ReleaseError("Duplicate release: " + key);
        }

        if (
            currentVersion &&
            release.version.compare(*currentVersion) <= 0
        ) {
            throw ReleaseError(
                "New release must increase version precedence"
            );
        }

        if (release.description.empty()) {
            throw ReleaseError("Release description is required");
        }

        if (release.state != ReleaseState::DRAFT) {
            throw ReleaseError(
                "New releases must begin in DRAFT state"
            );
        }

        releases.emplace(key, release);
    }

    vector<string> validate(const string& key) const {
        auto it = releases.find(key);

        if (it == releases.end()) {
            throw ReleaseError("Release does not exist");
        }

        const Release& release = it->second;
        vector<string> errors;

        if (!release.testsPassed) {
            errors.push_back("Automated tests have not passed");
        }

        if (!release.documentationUpdated) {
            errors.push_back("Documentation is incomplete");
        }

        if (
            release.change == ChangeType::MAJOR &&
            !release.migrationNotes
        ) {
            errors.push_back("Major release requires migration notes");
        }

        if (
            !release.version.prerelease.empty() &&
            currentVersion &&
            release.version.major > currentVersion->major
        ) {
            // Prereleases may be published as prereleases, but must
            // not be treated as stable production releases.
            errors.push_back(
                "Major prerelease requires separate prerelease handling"
            );
        }

        for (const string& dependency : release.dependencies) {
            auto dep = releases.find(dependency);

            if (
                dep == releases.end() ||
                dep->second.state != ReleaseState::PUBLISHED
            ) {
                errors.push_back(
                    "Dependency unavailable: " + dependency
                );
            }
        }

        return errors;
    }

    void publish(const string& key) {
        auto it = releases.find(key);

        if (it == releases.end()) {
            throw ReleaseError("Unknown release");
        }

        if (it->second.state == ReleaseState::PUBLISHED) {
            throw ReleaseError("Release already published");
        }

        vector<string> errors = validate(key);

        if (!errors.empty()) {
            it->second.state = ReleaseState::REJECTED;

            string message = "Publication rejected:";

            for (const string& error : errors) {
                message += "\n- " + error;
            }

            throw ReleaseError(message);
        }

        it->second.state = ReleaseState::VALIDATED;

        // State changes only after every publication condition passes.
        it->second.state = ReleaseState::PUBLISHED;
        currentVersion = it->second.version;
    }

    bool compatible(
        const Version& candidate,
        const vector<VersionConstraint>& constraints
    ) const {
        return all_of(
            constraints.begin(),
            constraints.end(),
            [&](const VersionConstraint& constraint) {
                return constraint.matches(candidate);
            }
        );
    }

    optional<Version> current() const {
        return currentVersion;
    }

    void printHistory() const {
        for (const auto& [key, release] : releases) {
            string state;

            switch (release.state) {
                case ReleaseState::DRAFT:
                    state = "DRAFT";
                    break;
                case ReleaseState::VALIDATED:
                    state = "VALIDATED";
                    break;
                case ReleaseState::PUBLISHED:
                    state = "PUBLISHED";
                    break;
                case ReleaseState::REJECTED:
                    state = "REJECTED";
                    break;
            }

            cout << key << " | "
                 << release.description << " | "
                 << state << '\n';
        }
    }
};

ChangeType classifyChange(
    bool breaking,
    bool feature,
    bool bugFix
) {
    if (breaking) return ChangeType::MAJOR;
    if (feature) return ChangeType::MINOR;
    if (bugFix) return ChangeType::PATCH;

    throw VersionError("No release-worthy change specified");
}

void runTests() {
    Version a = Version::parse("1.0.0-alpha");
    Version b = Version::parse("1.0.0");
    Version c = Version::parse("2.4.6+build.10");

    assert(a < b);
    assert(c.increment(ChangeType::PATCH).str() == "2.4.7");

    assert(
        Version::parse("1.0.0+build.1") ==
        Version::parse("1.0.0+build.2")
    );

    assert(
        Version::parse("1.0.0-beta.2") <
        Version::parse("1.0.0-beta.11")
    );

    assert(
        Version::parse("1.0.0-alpha") <
        Version::parse("1.0.0-alpha.1")
    );

    bool rejected = false;

    try {
        Version::parse("01.2.3");
    } catch (const VersionError&) {
        rejected = true;
    }

    assert(rejected);

    rejected = false;

    try {
        Version::parse("1.2.3-01");
    } catch (const VersionError&) {
        rejected = true;
    }

    assert(rejected);

    VersionConstraint lower{
        ">=",
        Version::parse("2.0.0")
    };

    VersionConstraint upper{
        "<",
        Version::parse("3.0.0")
    };

    assert(lower.matches(Version::parse("2.5.0")));
    assert(upper.matches(Version::parse("2.5.0")));

    assert(
        classifyChange(true, true, true) == ChangeType::MAJOR
    );

    cout << "All C++17 tests passed.\n";
}

int main() {
    try {
        runTests();

        cout << "\nSEMANTIC VERSIONING 2.0.0\n";

        vector<Version> versions = {
            Version::parse("1.0.0"),
            Version::parse("1.0.0-alpha"),
            Version::parse("1.0.0-beta"),
            Version::parse("1.0.0-rc.1"),
            Version::parse("1.0.0-alpha.1")
        };

        sort(versions.begin(), versions.end());

        cout << "\nVersion precedence:\n";

        for (const auto& version : versions) {
            cout << version.str() << '\n';
        }

        Version baseline = Version::parse("2.4.6");

        cout << "\nVersion increments:\n";
        cout << "Major: "
             << baseline.increment(ChangeType::MAJOR).str()
             << '\n';

        cout << "Minor: "
             << baseline.increment(ChangeType::MINOR).str()
             << '\n';

        cout << "Patch: "
             << baseline.increment(ChangeType::PATCH).str()
             << '\n';

        GovernanceEngine engine;

        Release first;
        first.version = Version::parse("1.0.0");
        first.description = "Initial stable API";
        first.change = ChangeType::MAJOR;
        first.testsPassed = true;
        first.documentationUpdated = true;
        first.migrationNotes = true;

        engine.registerRelease(first);
        engine.publish("1.0.0");

        Release second;
        second.version = Version::parse("1.1.0");
        second.description = "Added transaction search";
        second.change = ChangeType::MINOR;
        second.testsPassed = true;
        second.documentationUpdated = true;
        second.dependencies = {"1.0.0"};

        engine.registerRelease(second);
        engine.publish("1.1.0");

        cout << "\nCurrent release: "
             << engine.current()->str() << '\n';

        cout << "\nRelease history:\n";
        engine.printHistory();

        vector<VersionConstraint> constraints = {
            {">=", Version::parse("2.0.0")},
            {"<", Version::parse("3.0.0")}
        };

        cout << "\nDependency compatibility:\n";

        cout << "2.5.3: "
             << (
                 engine.compatible(
                     Version::parse("2.5.3"),
                     constraints
                 )
                 ? "COMPATIBLE"
                 : "INCOMPATIBLE"
             )
             << '\n';

        cout << "3.0.0: "
             << (
                 engine.compatible(
                     Version::parse("3.0.0"),
                     constraints
                 )
                 ? "COMPATIBLE"
                 : "INCOMPATIBLE"
             )
             << '\n';

    } catch (const exception& error) {
        cerr << "Execution error: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
