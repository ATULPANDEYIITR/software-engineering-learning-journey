#include <algorithm>
#include <chrono>
#include <functional>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace std;

enum class PipelineStatus {
    Pending,
    Running,
    Success,
    Failed,
    Cancelled
};

enum class JobStatus {
    Pending,
    Running,
    Success,
    Failed,
    Skipped
};

enum class Trigger {
    Push,
    PullRequest,
    Schedule,
    Manual
};

string toString(PipelineStatus status) {
    switch (status) {
        case PipelineStatus::Pending: return "PENDING";
        case PipelineStatus::Running: return "RUNNING";
        case PipelineStatus::Success: return "SUCCESS";
        case PipelineStatus::Failed: return "FAILED";
        case PipelineStatus::Cancelled: return "CANCELLED";
    }
    return "UNKNOWN";
}

string toString(JobStatus status) {
    switch (status) {
        case JobStatus::Pending: return "PENDING";
        case JobStatus::Running: return "RUNNING";
        case JobStatus::Success: return "SUCCESS";
        case JobStatus::Failed: return "FAILED";
        case JobStatus::Skipped: return "SKIPPED";
    }
    return "UNKNOWN";
}

struct Commit {
    string hash;
    string branch;
    string author;
    string message;
};

struct CheckResult {
    bool passed;
    string message;
    double durationMs;
};

struct Artifact {
    string name;
    string content;
    string checksum;
};

struct Job {
    string name;
    vector<string> dependencies;
    int maxRetries = 0;
    int attempts = 0;
    JobStatus status = JobStatus::Pending;
    string error;
    vector<CheckResult> results;
    function<CheckResult()> execute;
};

struct Pipeline {
    string id;
    Commit commit;
    Trigger trigger;
    PipelineStatus status = PipelineStatus::Pending;
    vector<Job> jobs;
    vector<Artifact> artifacts;
    vector<string> events;
};

class ValidationError : public runtime_error {
public:
    explicit ValidationError(const string& message)
        : runtime_error(message) {}
};

class PipelineEngine {

private:
    map<string, size_t> jobIndex;

    static bool validHash(const string& hash) {
        if (hash.size() < 7 || hash.size() > 40) {
            return false;
        }

        return all_of(
            hash.begin(),
            hash.end(),
            [](unsigned char c) {
                return isxdigit(c);
            }
        );
    }

    static bool validBranch(const string& branch) {
        if (branch.empty()) return false;

        return all_of(
            branch.begin(),
            branch.end(),
            [](unsigned char c) {
                return isalnum(c) ||
                    c == '/' || c == '-' ||
                    c == '_' || c == '.';
            }
        );
    }

    static string pseudoChecksum(const string& content) {
        // Deterministic demonstration checksum.
        // Production artifacts should use a cryptographic digest.
        unsigned long long hash = 14695981039346656037ULL;

        for (unsigned char c : content) {
            hash ^= c;
            hash *= 1099511628211ULL;
        }

        stringstream output;
        output << hex << hash;
        return output.str();
    }

    void log(Pipeline& pipeline, const string& message) {
        pipeline.events.push_back(message);
        cout << "[CI] " << message << '\n';
    }

    void validate(const Pipeline& pipeline) {
        if (pipeline.id.empty()) {
            throw ValidationError("Pipeline ID is required.");
        }

        if (!validHash(pipeline.commit.hash)) {
            throw ValidationError("Invalid commit hash.");
        }

        if (!validBranch(pipeline.commit.branch)) {
            throw ValidationError("Invalid branch name.");
        }

        if (pipeline.commit.author.empty()) {
            throw ValidationError("Commit author is required.");
        }

        set<string> names;

        for (const auto& job : pipeline.jobs) {
            if (job.name.empty()) {
                throw ValidationError("Job name cannot be empty.");
            }

            if (!names.insert(job.name).second) {
                throw ValidationError("Duplicate job name.");
            }

            if (job.maxRetries < 0) {
                throw ValidationError("Invalid retry configuration.");
            }

            if (!job.execute) {
                throw ValidationError("Job has no execution function.");
            }
        }

        for (const auto& job : pipeline.jobs) {
            for (const auto& dependency : job.dependencies) {
                if (!names.count(dependency)) {
                    throw ValidationError(
                        "Unknown dependency: " + dependency
                    );
                }

                if (dependency == job.name) {
                    throw ValidationError(
                        "Self-dependency is prohibited."
                    );
                }
            }
        }

        // Dependency cycle detection.
        map<string, vector<string>> graph;

        for (const auto& job : pipeline.jobs) {
            graph[job.name] = job.dependencies;
        }

        set<string> visited;
        set<string> active;

        function<void(const string&)> visit =
            [&](const string& name) {
                if (active.count(name)) {
                    throw ValidationError(
                        "Circular dependency detected."
                    );
                }

                if (visited.count(name)) return;

                active.insert(name);

                for (const auto& dependency : graph[name]) {
                    visit(dependency);
                }

                active.erase(name);
                visited.insert(name);
            };

        for (const auto& name : names) {
            visit(name);
        }
    }

    bool dependenciesPassed(
        const Job& job,
        const Pipeline& pipeline
    ) const {
        for (const auto& dependency : job.dependencies) {
            auto index = jobIndex.at(dependency);

            if (pipeline.jobs[index].status != JobStatus::Success) {
                return false;
            }
        }

        return true;
    }

    bool dependencyFailed(
        const Job& job,
        const Pipeline& pipeline
    ) const {
        for (const auto& dependency : job.dependencies) {
            auto index = jobIndex.at(dependency);
            const auto status = pipeline.jobs[index].status;

            if (
                status == JobStatus::Failed ||
                status == JobStatus::Skipped
            ) {
                return true;
            }
        }

        return false;
    }

    bool executeJob(Job& job, Pipeline& pipeline) {
        job.status = JobStatus::Running;

        log(pipeline, "Starting job: " + job.name);

        for (int attempt = 0; attempt <= job.maxRetries; ++attempt) {
            job.attempts++;

            try {
                CheckResult result = job.execute();
                job.results.push_back(result);

                if (!result.passed) {
                    throw runtime_error(result.message);
                }

                job.status = JobStatus::Success;

                log(
                    pipeline,
                    "Job succeeded: " + job.name
                );

                return true;

            } catch (const exception& error) {
                job.error = error.what();

                log(
                    pipeline,
                    "Job attempt failed: " + job.name +
                    " | " + job.error
                );
            }
        }

        job.status = JobStatus::Failed;

        log(pipeline, "Job exhausted retries: " + job.name);

        return false;
    }

    void createArtifact(Pipeline& pipeline) {
        string content =
            "Pipeline=" + pipeline.id +
            "\nCommit=" + pipeline.commit.hash +
            "\nBranch=" + pipeline.commit.branch +
            "\nStatus=SUCCESS\n";

        Artifact artifact;

        artifact.name = pipeline.id + "-build.txt";
        artifact.content = content;
        artifact.checksum = pseudoChecksum(content);

        if (
            pseudoChecksum(artifact.content) != artifact.checksum
        ) {
            throw runtime_error("Artifact integrity failure.");
        }

        pipeline.artifacts.push_back(artifact);

        log(pipeline, "Build artifact generated and verified.");
    }

public:

    void execute(Pipeline& pipeline) {
        if (pipeline.status != PipelineStatus::Pending) {
            throw ValidationError(
                "Pipeline must be pending before execution."
            );
        }

        validate(pipeline);

        jobIndex.clear();

        for (size_t i = 0; i < pipeline.jobs.size(); ++i) {
            jobIndex[pipeline.jobs[i].name] = i;
        }

        pipeline.status = PipelineStatus::Running;

        log(pipeline, "Pipeline started: " + pipeline.id);

        size_t completed = 0;
        const size_t total = pipeline.jobs.size();

        while (completed < total) {
            bool progress = false;

            for (auto& job : pipeline.jobs) {
                if (job.status != JobStatus::Pending) {
                    continue;
                }

                if (dependencyFailed(job, pipeline)) {
                    job.status = JobStatus::Skipped;
                    job.error = "A dependency failed.";

                    log(
                        pipeline,
                        "Job skipped: " + job.name
                    );

                    completed++;
                    progress = true;
                    continue;
                }

                if (dependenciesPassed(job, pipeline)) {
                    executeJob(job, pipeline);

                    completed++;
                    progress = true;
                }
            }

            if (!progress) {
                pipeline.status = PipelineStatus::Failed;

                log(
                    pipeline,
                    "Pipeline halted: unresolved dependencies."
                );

                return;
            }
        }

        bool failed = any_of(
            pipeline.jobs.begin(),
            pipeline.jobs.end(),
            [](const Job& job) {
                return job.status == JobStatus::Failed ||
                       job.status == JobStatus::Skipped;
            }
        );

        if (failed) {
            pipeline.status = PipelineStatus::Failed;
            log(pipeline, "Pipeline failed.");
            return;
        }

        createArtifact(pipeline);

        pipeline.status = PipelineStatus::Success;

        log(pipeline, "Pipeline completed successfully.");
    }

    void report(const Pipeline& pipeline) const {
        cout << "\n========== CI REPORT ==========\n";

        cout << "Pipeline: " << pipeline.id << '\n';
        cout << "Commit: " << pipeline.commit.hash << '\n';
        cout << "Branch: " << pipeline.commit.branch << '\n';
        cout << "Status: " << toString(pipeline.status) << '\n';

        cout << "\nJOB RESULTS\n";

        for (const auto& job : pipeline.jobs) {
            cout << left << setw(18) << job.name
                 << setw(12) << toString(job.status)
                 << "Attempts: " << job.attempts
                 << '\n';

            if (!job.error.empty()) {
                cout << "  Error: " << job.error << '\n';
            }
        }

        cout << "\nARTIFACTS\n";

        for (const auto& artifact : pipeline.artifacts) {
            cout << artifact.name
                 << " | Checksum: " << artifact.checksum
                 << '\n';
        }

        cout << "===============================\n";
    }
};


int main() {
    try {
        Pipeline pipeline;

        pipeline.id = "CI-CPP-001";

        pipeline.commit = {
            "a123456",
            "feature/payment",
            "developer@example.com",
            "Add payment validation"
        };

        pipeline.trigger = Trigger::PullRequest;

        pipeline.jobs = {
            {
                "lint",
                {},
                0,
                0,
                JobStatus::Pending,
                "",
                {},
                []() {
                    return CheckResult{
                        true,
                        "Source validation passed.",
                        12.5
                    };
                }
            },
            {
                "unit-tests",
                {"lint"},
                0,
                0,
                JobStatus::Pending,
                "",
                {},
                []() {
                    vector<pair<int, int>> tests = {
                        {10, 20},
                        {0, 0},
                        {-5, 5}
                    };

                    for (const auto& test : tests) {
                        if (test.first + test.second < -1000) {
                            return CheckResult{
                                false,
                                "Invalid arithmetic result.",
                                0
                            };
                        }
                    }

                    return CheckResult{
                        true,
                        "Unit tests passed.",
                        24.0
                    };
                }
            },
            {
                "security",
                {"lint"},
                0,
                0,
                JobStatus::Pending,
                "",
                {},
                []() {
                    bool credentialsSafe = true;

                    return CheckResult{
                        credentialsSafe,
                        "Credential validation passed.",
                        18.0
                    };
                }
            },
            {
                "build",
                {"unit-tests", "security"},
                1,
                0,
                JobStatus::Pending,
                "",
                {},
                []() {
                    return CheckResult{
                        true,
                        "Build package created.",
                        42.0
                    };
                }
            }
        };

        PipelineEngine engine;

        engine.execute(pipeline);
        engine.report(pipeline);

        if (pipeline.status != PipelineStatus::Success) {
            return 1;
        }

        cout << "\nAll CI checks passed.\n";

        return 0;

    } catch (const exception& error) {
        cerr << "Pipeline error: " << error.what() << '\n';
        return 1;
    }
}
