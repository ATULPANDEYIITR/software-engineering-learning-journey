#include <algorithm>
#include <fstream>
#include <functional>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

/*
 * Build Systems: C++17 Repository Build Planner
 *
 * Implements:
 * - Target registration
 * - Dependency graph validation
 * - Topological sorting
 * - Parallel build-stage identification
 * - Incremental build fingerprints
 * - Compilation state management
 * - Artifact integrity verification
 * - Packaging manifests
 *
 * Compile:
 * g++ -std=c++17 -O2 -Wall -Wextra -pedantic build_system.cpp -o build_system
 *
 * Run:
 * ./build_system
 */

enum class TargetType {
    Library,
    Executable
};

enum class BuildState {
    Pending,
    Building,
    Success,
    Cached,
    Failed
};

enum class BuildProfile {
    Debug,
    Release
};

struct BuildTarget {
    std::string name;
    std::string source;
    std::vector<std::string> dependencies;
    TargetType type = TargetType::Library;
    BuildState state = BuildState::Pending;
    std::string version = "1.0.0";
    bool enabled = true;
};

struct Artifact {
    std::string target;
    std::string filename;
    std::string fingerprint;
    std::string checksum;
    std::size_t size = 0;
    bool cached = false;
};

class BuildException : public std::runtime_error {
public:
    explicit BuildException(const std::string& message)
        : std::runtime_error(message) {}
};

class DependencyException : public BuildException {
public:
    using BuildException::BuildException;
};

class CompilationException : public BuildException {
public:
    using BuildException::BuildException;
};

class BuildPlanner {
private:
    std::map<std::string, BuildTarget> targets;

    std::map<std::string, Artifact> artifacts;

    std::map<std::string, Artifact> cache;

    BuildProfile profile;

    std::string outputDirectory;

    static std::string profileName(BuildProfile value) {
        return value == BuildProfile::Debug
            ? "debug"
            : "release";
    }

    static bool validName(const std::string& name) {
        return !name.empty() &&
            std::all_of(
                name.begin(),
                name.end(),
                [](unsigned char ch) {
                    return std::isalnum(ch) ||
                        ch == '_' || ch == '-';
                }
            );
    }

    static bool validVersion(const std::string& version) {
        std::istringstream input(version);

        int major, minor, patch;
        char first, second;

        if (!(input >> major >> first >> minor >> second >> patch)) {
            return false;
        }

        std::string remaining;

        return first == '.' &&
            second == '.' &&
            major >= 0 &&
            minor >= 0 &&
            patch >= 0 &&
            !(input >> remaining);
    }

    static std::string hashText(const std::string& input) {
        // FNV-1a is used for deterministic demonstration fingerprints.
        // Production systems should use a cryptographic hash such as SHA-256.
        std::uint64_t hash = 14695981039346656037ULL;

        for (unsigned char byte : input) {
            hash ^= byte;
            hash *= 1099511628211ULL;
        }

        std::ostringstream result;
        result << std::hex << std::setw(16)
               << std::setfill('0') << hash;

        return result.str();
    }

    std::string fingerprint(const BuildTarget& target) const {
        std::ostringstream data;

        data << target.name
             << target.source
             << target.version
             << profileName(profile);

        for (const auto& dependency : target.dependencies) {
            auto iterator = artifacts.find(dependency);

            if (iterator == artifacts.end()) {
                throw DependencyException(
                    "Dependency artifact missing: " + dependency
                );
            }

            data << dependency
                 << iterator->second.fingerprint;
        }

        return hashText(data.str());
    }

    void compileTarget(const std::string& name) {
        auto& target = targets.at(name);

        if (!target.enabled) {
            throw CompilationException(
                "Target disabled: " + name
            );
        }

        target.state = BuildState::Building;

        const std::string key = fingerprint(target);

        auto cached = cache.find(key);

        if (cached != cache.end()) {
            std::ifstream existing(
                cached->second.filename,
                std::ios::binary
            );

            if (!existing) {
                throw CompilationException(
                    "Cached artifact is missing: " + name
                );
            }

            Artifact artifact = cached->second;
            artifact.cached = true;

            artifacts[name] = artifact;
            target.state = BuildState::Cached;

            std::cout << "CACHE HIT: " << name << '\n';
            return;
        }

        if (target.source.find("COMPILE_ERROR") !=
            std::string::npos) {
            target.state = BuildState::Failed;

            throw CompilationException(
                "Compiler error in target: " + name
            );
        }

        const std::string extension =
            target.type == TargetType::Executable
            ? ".exe"
            : ".lib";

        const std::string filename =
            outputDirectory + "/" + name + extension;

        std::ostringstream content;

        content << "TARGET=" << name << '\n'
                << "SOURCE=" << target.source << '\n'
                << "VERSION=" << target.version << '\n'
                << "PROFILE=" << profileName(profile) << '\n'
                << "FINGERPRINT=" << key << '\n';

        const std::string compiled = content.str();

        // Write to a temporary file before replacing the artifact.
        const std::string temporary = filename + ".tmp";

        {
            std::ofstream output(temporary, std::ios::binary);

            if (!output) {
                target.state = BuildState::Failed;

                throw CompilationException(
                    "Cannot create artifact: " + temporary
                );
            }

            output << compiled;

            if (!output.good()) {
                target.state = BuildState::Failed;

                throw CompilationException(
                    "Artifact write failed: " + temporary
                );
            }
        }

        if (std::rename(temporary.c_str(), filename.c_str()) != 0) {
            std::remove(temporary.c_str());

            target.state = BuildState::Failed;

            throw CompilationException(
                "Cannot replace artifact: " + filename
            );
        }

        Artifact artifact;

        artifact.target = name;
        artifact.filename = filename;
        artifact.fingerprint = key;
        artifact.checksum = hashText(compiled);
        artifact.size = compiled.size();

        cache[key] = artifact;
        artifacts[name] = artifact;

        target.state = BuildState::Success;

        std::cout << "COMPILED: " << name << '\n';
    }

public:
    explicit BuildPlanner(
        std::string directory = "build_output",
        BuildProfile selectedProfile = BuildProfile::Release
    )
        : profile(selectedProfile),
          outputDirectory(std::move(directory)) {

        const std::string command =
            "mkdir -p \"" + outputDirectory + "\"";

        if (std::system(command.c_str()) != 0) {
            throw BuildException(
                "Cannot create build directory."
            );
        }
    }

    void registerTarget(BuildTarget target) {
        if (!validName(target.name)) {
            throw DependencyException("Invalid target name.");
        }

        if (!validVersion(target.version)) {
            throw DependencyException("Invalid target version.");
        }

        if (target.source.empty()) {
            throw DependencyException("Empty source.");
        }

        if (targets.count(target.name)) {
            throw DependencyException(
                "Duplicate target: " + target.name
            );
        }

        std::set<std::string> uniqueDependencies;

        for (const auto& dependency : target.dependencies) {
            if (!uniqueDependencies.insert(dependency).second) {
                throw DependencyException(
                    "Duplicate dependency: " + dependency
                );
            }
        }

        targets.emplace(target.name, std::move(target));
    }

    void validate() const {
        for (const auto& entry : targets) {
            for (const auto& dependency :
                 entry.second.dependencies) {

                if (!targets.count(dependency)) {
                    throw DependencyException(
                        entry.first +
                        " requires missing target " +
                        dependency
                    );
                }
            }
        }
    }

    std::vector<std::string> topologicalSort() const {
        validate();

        std::set<std::string> temporary;
        std::set<std::string> permanent;

        std::vector<std::string> order;

        std::function<void(const std::string&)> visit;

        visit = [&](const std::string& name) {
            if (permanent.count(name)) return;

            if (temporary.count(name)) {
                throw DependencyException(
                    "Circular dependency: " + name
                );
            }

            temporary.insert(name);

            auto dependencies =
                targets.at(name).dependencies;

            std::sort(
                dependencies.begin(),
                dependencies.end()
            );

            for (const auto& dependency : dependencies) {
                visit(dependency);
            }

            temporary.erase(name);
            permanent.insert(name);

            order.push_back(name);
        };

        for (const auto& entry : targets) {
            visit(entry.first);
        }

        return order;
    }

    std::vector<std::vector<std::string>> buildStages() const {
        auto order = topologicalSort();

        std::map<std::string, std::size_t> levels;
        std::size_t maximum = 0;

        for (const auto& name : order) {
            std::size_t level = 0;

            for (const auto& dependency :
                 targets.at(name).dependencies) {
                level = std::max(
                    level,
                    levels.at(dependency) + 1
                );
            }

            levels[name] = level;
            maximum = std::max(maximum, level);
        }

        std::vector<std::vector<std::string>> stages;

        for (std::size_t level = 0;
             level <= maximum && !order.empty();
             ++level) {

            std::vector<std::string> stage;

            for (const auto& entry : levels) {
                if (entry.second == level) {
                    stage.push_back(entry.first);
                }
            }

            stages.push_back(std::move(stage));
        }

        return stages;
    }

    std::vector<Artifact> build() {
        artifacts.clear();

        const auto order = topologicalSort();

        for (const auto& name : order) {
            compileTarget(name);
        }

        std::vector<Artifact> result;

        for (const auto& name : order) {
            result.push_back(artifacts.at(name));
        }

        return result;
    }

    void package(
        const std::string& packageName,
        const std::string& version
    ) const {
        if (!validName(packageName) ||
            !validVersion(version)) {
            throw BuildException("Invalid package metadata.");
        }

        if (artifacts.empty()) {
            throw BuildException("No artifacts to package.");
        }

        const std::string directory =
            outputDirectory + "/" +
            packageName + "-" + version;

        const std::string command =
            "mkdir -p \"" + directory + "\"";

        if (std::system(command.c_str()) != 0) {
            throw BuildException("Cannot create package directory.");
        }

        const std::string manifestPath =
            directory + "/manifest.txt";

        std::ofstream manifest(manifestPath);

        if (!manifest) {
            throw BuildException("Cannot create manifest.");
        }

        manifest << "PACKAGE=" << packageName << '\n'
                 << "VERSION=" << version << '\n'
                 << "PROFILE=" << profileName(profile) << '\n';

        for (const auto& entry : artifacts) {
            std::ifstream source(
                entry.second.filename,
                std::ios::binary
            );

            if (!source) {
                throw BuildException(
                    "Missing artifact: " + entry.first
                );
            }

            const std::string destination =
                directory + "/" +
                entry.first +
                (targets.at(entry.first).type ==
                    TargetType::Executable
                    ? ".exe"
                    : ".lib");

            std::ofstream output(
                destination,
                std::ios::binary
            );

            if (!output) {
                throw BuildException(
                    "Cannot copy artifact: " + destination
                );
            }

            output << source.rdbuf();

            if (!output.good()) {
                throw BuildException(
                    "Package copy failed: " + destination
                );
            }

            manifest << "ARTIFACT=" << entry.first
                     << " CHECKSUM=" << entry.second.checksum
                     << " SIZE=" << entry.second.size
                     << '\n';
        }

        std::cout << "PACKAGE CREATED: "
                  << directory << '\n';
    }
};

void runTests() {
    BuildPlanner planner(
        "build_test_output",
        BuildProfile::Debug
    );

    planner.registerTarget({
        "base", "base.cpp", {}
    });

    planner.registerTarget({
        "service", "service.cpp", {"base"}
    });

    const auto order = planner.topologicalSort();

    if (order.size() != 2 ||
        order[0] != "base" ||
        order[1] != "service") {
        throw BuildException("Topological sorting test failed.");
    }

    if (planner.buildStages().size() != 2) {
        throw BuildException("Build stage test failed.");
    }

    bool detected = false;

    try {
        BuildPlanner cycle("build_cycle");

        cycle.registerTarget({
            "first", "first.cpp", {"second"}
        });

        cycle.registerTarget({
            "second", "second.cpp", {"first"}
        });

        cycle.topologicalSort();

    } catch (const DependencyException&) {
        detected = true;
    }

    if (!detected) {
        throw BuildException("Cycle detection test failed.");
    }

    std::cout << "ALL TESTS PASSED\n";
}

int main() {
    try {
        runTests();

        BuildPlanner planner(
            "build_output",
            BuildProfile::Release
        );

        planner.registerTarget({
            "core",
            "core.cpp",
            {},
            TargetType::Library
        });

        planner.registerTarget({
            "database",
            "database.cpp",
            {"core"},
            TargetType::Library
        });

        planner.registerTarget({
            "network",
            "network.cpp",
            {"core"},
            TargetType::Library
        });

        planner.registerTarget({
            "application",
            "main.cpp",
            {"database", "network"},
            TargetType::Executable
        });

        std::cout << "\nBUILD STAGES\n";

        const auto stages = planner.buildStages();

        for (std::size_t index = 0;
             index < stages.size();
             ++index) {

            std::cout << "Stage " << index << ": ";

            for (const auto& name : stages[index]) {
                std::cout << name << " ";
            }

            std::cout << '\n';
        }

        std::cout << "\nFIRST BUILD\n";

        planner.build();

        std::cout << "\nINCREMENTAL BUILD\n";

        planner.build();

        std::cout << "\nPACKAGING\n";

        planner.package(
            "enterprise_application",
            "1.0.0"
        );

    } catch (const std::exception& error) {
        std::cerr << "BUILD FAILURE: "
                  << error.what() << '\n';

        return 1;
    }

    return 0;
}
