#include <algorithm>
#include <chrono>
#include <cctype>
#include <iomanip>
#include <iostream>
#include <map>
#include <mutex>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

using Clock = std::chrono::steady_clock;
using SystemClock = std::chrono::system_clock;

enum class HttpMethod {
    Get,
    Post,
    Patch,
    Delete
};

enum class TaskStatus {
    Pending,
    InProgress,
    Completed,
    Cancelled
};

std::string toString(TaskStatus status) {
    switch (status) {
        case TaskStatus::Pending: return "pending";
        case TaskStatus::InProgress: return "in_progress";
        case TaskStatus::Completed: return "completed";
        case TaskStatus::Cancelled: return "cancelled";
    }
    throw std::logic_error("Unknown task status.");
}

std::optional<TaskStatus> parseStatus(const std::string& value) {
    if (value == "pending") return TaskStatus::Pending;
    if (value == "in_progress") return TaskStatus::InProgress;
    if (value == "completed") return TaskStatus::Completed;
    if (value == "cancelled") return TaskStatus::Cancelled;
    return std::nullopt;
}

bool validTransition(TaskStatus from, TaskStatus to) {
    switch (from) {
        case TaskStatus::Pending:
            return to == TaskStatus::InProgress ||
                   to == TaskStatus::Cancelled;

        case TaskStatus::InProgress:
            return to == TaskStatus::Pending ||
                   to == TaskStatus::Completed ||
                   to == TaskStatus::Cancelled;

        case TaskStatus::Completed:
        case TaskStatus::Cancelled:
            return false;
    }
    return false;
}

std::string currentTimestamp() {
    const auto now = SystemClock::now();
    const std::time_t value = SystemClock::to_time_t(now);

    std::tm utc{};
#ifdef _WIN32
    gmtime_s(&utc, &value);
#else
    gmtime_r(&value, &utc);
#endif

    std::ostringstream output;
    output << std::put_time(&utc, "%Y-%m-%dT%H:%M:%SZ");
    return output.str();
}

std::string jsonEscape(const std::string& input) {
    std::ostringstream output;

    for (unsigned char character : input) {
        switch (character) {
            case '"': output << "\\\""; break;
            case '\\': output << "\\\\"; break;
            case '\b': output << "\\b"; break;
            case '\f': output << "\\f"; break;
            case '\n': output << "\\n"; break;
            case '\r': output << "\\r"; break;
            case '\t': output << "\\t"; break;
            default:
                if (character < 0x20) {
                    output << "\\u"
                           << std::hex << std::setw(4)
                           << std::setfill('0')
                           << static_cast<int>(character)
                           << std::dec;
                } else {
                    output << static_cast<char>(character);
                }
        }
    }

    return output.str();
}

bool secureEqual(const std::string& left, const std::string& right) {
    // The comparison does not return early when a character differs.
    const std::size_t length = std::max(left.size(), right.size());
    unsigned int difference =
        static_cast<unsigned int>(left.size() ^ right.size());

    for (std::size_t index = 0; index < length; ++index) {
        const unsigned char a =
            index < left.size()
                ? static_cast<unsigned char>(left[index])
                : 0;
        const unsigned char b =
            index < right.size()
                ? static_cast<unsigned char>(right[index])
                : 0;
        difference |= static_cast<unsigned int>(a ^ b);
    }

    return difference == 0;
}

class ApiError : public std::runtime_error {
public:
    ApiError(int status, std::string code, std::string message)
        : std::runtime_error(std::move(message)),
          status_(status),
          code_(std::move(code)) {}

    int status() const noexcept { return status_; }
    const std::string& code() const noexcept { return code_; }

private:
    int status_;
    std::string code_;
};

struct Task {
    std::string id;
    std::string title;
    std::string description;
    TaskStatus status{TaskStatus::Pending};
    int version{1};
    std::string createdAt;
    std::string updatedAt;
};

struct Request {
    HttpMethod method{HttpMethod::Get};
    std::string path;
    std::string clientAddress;
    std::map<std::string, std::string> headers;
    std::map<std::string, std::string> fields;
    std::map<std::string, std::string> query;
};

struct Response {
    int status{200};
    std::string body;
    std::map<std::string, std::string> headers;
};

std::string serializeTask(const Task& task) {
    std::ostringstream output;
    output
        << "{"
        << "\"id\":\"" << jsonEscape(task.id) << "\","
        << "\"title\":\"" << jsonEscape(task.title) << "\","
        << "\"description\":\"" << jsonEscape(task.description) << "\","
        << "\"status\":\"" << toString(task.status) << "\","
        << "\"version\":" << task.version << ","
        << "\"created_at\":\"" << jsonEscape(task.createdAt) << "\","
        << "\"updated_at\":\"" << jsonEscape(task.updatedAt) << "\""
        << "}";
    return output.str();
}

class RateLimiter {
public:
    RateLimiter(
        std::size_t maximum = 120,
        std::chrono::seconds window = std::chrono::seconds(60)
    ) : maximum_(maximum), window_(window) {}

    bool allow(const std::string& client) {
        const auto now = Clock::now();
        std::lock_guard<std::mutex> guard(mutex_);

        auto& bucket = buckets_[client];

        while (!bucket.empty() && now - bucket.front() >= window_) {
            bucket.erase(bucket.begin());
        }

        if (bucket.size() >= maximum_) {
            return false;
        }

        bucket.push_back(now);

        if (buckets_.size() > 10'000) {
            for (auto iterator = buckets_.begin();
                 iterator != buckets_.end();) {
                auto& values = iterator->second;

                if (values.empty() || now - values.back() >= window_) {
                    iterator = buckets_.erase(iterator);
                } else {
                    ++iterator;
                }
            }
        }

        return true;
    }

private:
    std::size_t maximum_;
    std::chrono::seconds window_;
    std::mutex mutex_;
    std::unordered_map<std::string, std::vector<Clock::time_point>> buckets_;
};

class TaskRepository {
public:
    struct CreateResult {
        Task task;
        bool replayed;
    };

    CreateResult create(
        const std::string& title,
        const std::string& description,
        const std::string& idempotencyKey
    ) {
        std::lock_guard<std::mutex> guard(mutex_);

        const auto previous = idempotency_.find(idempotencyKey);
        const std::string fingerprint = title + '\0' + description;

        if (previous != idempotency_.end()) {
            if (previous->second.fingerprint != fingerprint) {
                throw ApiError(
                    409,
                    "idempotency_conflict",
                    "The key was previously used with a different request."
                );
            }

            const auto foundTask = tasks_.find(previous->second.taskId);
            if (foundTask == tasks_.end()) {
                throw ApiError(
                    409,
                    "idempotency_record_unavailable",
                    "The original resource is no longer available."
                );
            }

            return {foundTask->second, true};
        }

        const std::string id =
            "task-" + std::to_string(nextId_++);

        const std::string now = currentTimestamp();
        Task task{
            id,
            title,
            description,
            TaskStatus::Pending,
            1,
            now,
            now
        };

        tasks_.emplace(id, task);
        idempotency_.emplace(
            idempotencyKey,
            IdempotencyRecord{fingerprint, id}
        );

        return {task, false};
    }

    Task get(const std::string& id) const {
        std::lock_guard<std::mutex> guard(mutex_);
        const auto found = tasks_.find(id);

        if (found == tasks_.end()) {
            throw ApiError(404, "task_not_found", "Task does not exist.");
        }

        return found->second;
    }

    std::vector<Task> list(
        const std::optional<TaskStatus>& status,
        std::size_t limit,
        std::size_t offset
    ) const {
        std::lock_guard<std::mutex> guard(mutex_);

        std::vector<Task> result;
        result.reserve(tasks_.size());

        for (const auto& entry : tasks_) {
            if (!status || entry.second.status == *status) {
                result.push_back(entry.second);
            }
        }

        std::sort(
            result.begin(),
            result.end(),
            [](const Task& left, const Task& right) {
                if (left.createdAt != right.createdAt) {
                    return left.createdAt > right.createdAt;
                }
                return left.id < right.id;
            }
        );

        if (offset >= result.size()) {
            return {};
        }

        const auto first = result.begin() +
            static_cast<std::ptrdiff_t>(offset);
        const auto last = result.begin() +
            static_cast<std::ptrdiff_t>(
                std::min(result.size(), offset + limit)
            );

        return {first, last};
    }

    Task update(
        const std::string& id,
        int expectedVersion,
        const std::map<std::string, std::string>& fields
    ) {
        std::lock_guard<std::mutex> guard(mutex_);

        auto found = tasks_.find(id);
        if (found == tasks_.end()) {
            throw ApiError(404, "task_not_found", "Task does not exist.");
        }

        Task& task = found->second;

        if (task.version != expectedVersion) {
            throw ApiError(
                412,
                "version_conflict",
                "The task changed. Retrieve its latest version."
            );
        }

        Task updated = task;

        for (const auto& [key, value] : fields) {
            if (key == "title") {
                if (value.empty() || value.size() > 160) {
                    throw ApiError(
                        400,
                        "invalid_title",
                        "Title must contain between 1 and 160 bytes."
                    );
                }
                updated.title = value;
            } else if (key == "description") {
                if (value.size() > 2000) {
                    throw ApiError(
                        400,
                        "invalid_description",
                        "Description cannot exceed 2000 bytes."
                    );
                }
                updated.description = value;
            } else if (key == "status") {
                const auto newStatus = parseStatus(value);
                if (!newStatus) {
                    throw ApiError(
                        400,
                        "invalid_status",
                        "Unsupported task status."
                    );
                }

                if (
                    *newStatus != task.status &&
                    !validTransition(task.status, *newStatus)
                ) {
                    throw ApiError(
                        409,
                        "invalid_state_transition",
                        "The requested status transition is not permitted."
                    );
                }

                updated.status = *newStatus;
            } else {
                throw ApiError(
                    400,
                    "unknown_field",
                    "Unsupported task field: " + key
                );
            }
        }

        if (fields.empty()) {
            throw ApiError(
                400,
                "empty_patch",
                "At least one field must be supplied."
            );
        }

        updated.version += 1;
        updated.updatedAt = currentTimestamp();
        task = updated;

        return task;
    }

    void remove(const std::string& id, int expectedVersion) {
        std::lock_guard<std::mutex> guard(mutex_);

        const auto found = tasks_.find(id);
        if (found == tasks_.end()) {
            throw ApiError(404, "task_not_found", "Task does not exist.");
        }

        if (found->second.version != expectedVersion) {
            throw ApiError(
                412,
                "version_conflict",
                "The task changed before deletion."
            );
        }

        tasks_.erase(found);

        for (auto iterator = idempotency_.begin();
             iterator != idempotency_.end();) {
            if (iterator->second.taskId == id) {
                iterator = idempotency_.erase(iterator);
            } else {
                ++iterator;
            }
        }
    }

private:
    struct IdempotencyRecord {
        std::string fingerprint;
        std::string taskId;
    };

    mutable std::mutex mutex_;
    std::unordered_map<std::string, Task> tasks_;
    std::unordered_map<std::string, IdempotencyRecord> idempotency_;
    std::uint64_t nextId_{1};
};

class ApiGateway {
public:
    explicit ApiGateway(std::string token)
        : token_(std::move(token)) {
        if (token_.size() < 16) {
            throw std::invalid_argument(
                "API token must contain at least 16 characters."
            );
        }
    }

    Response handle(const Request& request) {
        try {
            if (request.path == "/health") {
                if (request.method != HttpMethod::Get) {
                    throw ApiError(
                        405,
                        "method_not_allowed",
                        "Use GET for the health endpoint."
                    );
                }

                return success(
                    200,
                    "{\"status\":\"healthy\"}"
                );
            }

            if (request.path.rfind("/v1/", 0) != 0) {
                throw ApiError(404, "route_not_found", "Route does not exist.");
            }

            if (!rateLimiter_.allow(request.clientAddress)) {
                throw ApiError(
                    429,
                    "rate_limit_exceeded",
                    "Too many requests."
                );
            }

            const auto authorization =
                request.headers.find("Authorization");

            const std::string supplied =
                authorization == request.headers.end()
                    ? ""
                    : authorization->second;

            const std::string prefix = "Bearer ";
            const std::string candidate =
                supplied.rfind(prefix, 0) == 0
                    ? supplied.substr(prefix.size())
                    : "";

            if (!secureEqual(candidate, token_)) {
                throw ApiError(
                    401,
                    "unauthorized",
                    "A valid bearer token is required."
                );
            }

            if (request.path == "/v1/tasks") {
                return handleCollection(request);
            }

            const std::string itemPrefix = "/v1/tasks/";
            if (request.path.rfind(itemPrefix, 0) == 0) {
                return handleItem(
                    request,
                    request.path.substr(itemPrefix.size())
                );
            }

            throw ApiError(404, "route_not_found", "Route does not exist.");
        } catch (const ApiError& error) {
            std::ostringstream body;
            body
                << "{\"error\":{\"code\":\""
                << jsonEscape(error.code())
                << "\",\"message\":\""
                << jsonEscape(error.what())
                << "\"}}";

            return {
                error.status(),
                body.str(),
                {{"Content-Type", "application/json"}}
            };
        } catch (const std::exception&) {
            return {
                500,
                "{\"error\":{\"code\":\"internal_server_error\","
                "\"message\":\"An unexpected server error occurred.\"}}",
                {{"Content-Type", "application/json"}}
            };
        }
    }

private:
    Response success(
        int status,
        const std::string& body,
        const std::map<std::string, std::string>& extra = {}
    ) const {
        auto headers = extra;
        headers["Content-Type"] = "application/json";
        headers["Cache-Control"] = "no-store";
        return {status, body, std::move(headers)};
    }

    static int parseVersion(const Request& request) {
        const auto found = request.headers.find("If-Match");

        if (found == request.headers.end()) {
            throw ApiError(
                428,
                "precondition_required",
                "If-Match is required for modification."
            );
        }

        std::string value = found->second;
        if (value.size() >= 2 &&
            value.front() == '"' &&
            value.back() == '"') {
            value = value.substr(1, value.size() - 2);
        }

        if (value.empty() ||
            !std::all_of(
                value.begin(),
                value.end(),
                [](unsigned char character) {
                    return std::isdigit(character);
                }
            )) {
            throw ApiError(
                400,
                "invalid_if_match",
                "If-Match must contain a positive integer."
            );
        }

        try {
            const int version = std::stoi(value);
            if (version <= 0) {
                throw std::invalid_argument("Version must be positive.");
            }
            return version;
        } catch (const std::exception&) {
            throw ApiError(
                400,
                "invalid_if_match",
                "If-Match contains an invalid version."
            );
        }
    }

    static std::size_t parseSize(
        const std::map<std::string, std::string>& query,
        const std::string& key,
        std::size_t defaultValue,
        std::size_t minimum,
        std::size_t maximum
    ) {
        const auto found = query.find(key);
        if (found == query.end()) {
            return defaultValue;
        }

        try {
            std::size_t consumed = 0;
            const unsigned long long parsed =
                std::stoull(found->second, &consumed);

            if (consumed != found->second.size() ||
                parsed < minimum ||
                parsed > maximum) {
                throw std::invalid_argument("Out of range.");
            }

            return static_cast<std::size_t>(parsed);
        } catch (const std::exception&) {
            throw ApiError(
                400,
                "invalid_" + key,
                key + " must be within the permitted integer range."
            );
        }
    }

    Response handleCollection(const Request& request) {
        if (request.method == HttpMethod::Get) {
            std::optional<TaskStatus> filter;

            const auto statusFound = request.query.find("status");
            if (statusFound != request.query.end()) {
                filter = parseStatus(statusFound->second);
                if (!filter) {
                    throw ApiError(
                        400,
                        "invalid_status",
                        "Unsupported task status."
                    );
                }
            }

            const auto limit = parseSize(
                request.query, "limit", 20, 1, 100
            );
            const auto offset = parseSize(
                request.query, "offset", 0, 0, 1'000'000
            );

            const auto tasks = repository_.list(filter, limit, offset);
            std::ostringstream body;
            body << "{\"data\":[";

            for (std::size_t index = 0; index < tasks.size(); ++index) {
                if (index > 0) body << ',';
                body << serializeTask(tasks[index]);
            }

            body << "],\"pagination\":{\"limit\":" << limit
                 << ",\"offset\":" << offset
                 << ",\"returned\":" << tasks.size() << "}}";

            return success(200, body.str());
        }

        if (request.method == HttpMethod::Post) {
            const auto titleFound = request.fields.find("title");
            const auto keyFound = request.headers.find("Idempotency-Key");

            if (titleFound == request.fields.end()) {
                throw ApiError(
                    400,
                    "invalid_title",
                    "Title is required."
                );
            }

            if (titleFound->second.empty() ||
                titleFound->second.size() > 160) {
                throw ApiError(
                    400,
                    "invalid_title",
                    "Title must contain between 1 and 160 bytes."
                );
            }

            const auto descriptionFound =
                request.fields.find("description");
            const std::string description =
                descriptionFound == request.fields.end()
                    ? ""
                    : descriptionFound->second;

            if (description.size() > 2000) {
                throw ApiError(
                    400,
                    "invalid_description",
                    "Description cannot exceed 2000 bytes."
                );
            }

            if (
                keyFound == request.headers.end() ||
                keyFound->second.size() < 8 ||
                keyFound->second.size() > 128
            ) {
                throw ApiError(
                    400,
                    "invalid_idempotency_key",
                    "A permitted Idempotency-Key is required."
                );
            }

            const auto result = repository_.create(
                titleFound->second,
                description,
                keyFound->second
            );

            const int status = result.replayed ? 200 : 201;
            std::map<std::string, std::string> headers{
                {"ETag", "\"" + std::to_string(result.task.version) + "\""}
            };

            if (result.replayed) {
                headers["Idempotent-Replayed"] = "true";
            }

            return success(
                status,
                "{\"data\":" + serializeTask(result.task) + "}",
                headers
            );
        }

        throw ApiError(
            405,
            "method_not_allowed",
            "Collection methods are GET and POST."
        );
    }

    Response handleItem(
        const Request& request,
        const std::string& taskId
    ) {
        if (taskId.empty() || taskId.find('/') != std::string::npos) {
            throw ApiError(404, "task_not_found", "Task does not exist.");
        }

        if (request.method == HttpMethod::Get) {
            const Task task = repository_.get(taskId);
            return success(
                200,
                "{\"data\":" + serializeTask(task) + "}",
                {{"ETag", "\"" + std::to_string(task.version) + "\""}}
            );
        }

        if (request.method == HttpMethod::Patch) {
            const int expectedVersion = parseVersion(request);
            const Task task = repository_.update(
                taskId,
                expectedVersion,
                request.fields
            );

            return success(
                200,
                "{\"data\":" + serializeTask(task) + "}",
                {{"ETag", "\"" + std::to_string(task.version) + "\""}}
            );
        }

        if (request.method == HttpMethod::Delete) {
            const int expectedVersion = parseVersion(request);
            repository_.remove(taskId, expectedVersion);

            return success(
                200,
                "{\"data\":{\"id\":\"" + jsonEscape(taskId) +
                    "\",\"deleted\":true}}"
            );
        }

        throw ApiError(
            405,
            "method_not_allowed",
            "Item methods are GET, PATCH and DELETE."
        );
    }

    std::string token_;
    RateLimiter rateLimiter_;
    TaskRepository repository_;
};

void printResponse(const std::string& label, const Response& response) {
    std::cout
        << label
        << " -> HTTP "
        << response.status
        << '\n'
        << response.body
        << "\n\n";
}

int main() {
    try {
        ApiGateway api("development-secret-change-this-token");

        Request health;
        health.method = HttpMethod::Get;
        health.path = "/health";
        health.clientAddress = "127.0.0.1";
        printResponse("Health", api.handle(health));

        Request create;
        create.method = HttpMethod::Post;
        create.path = "/v1/tasks";
        create.clientAddress = "127.0.0.1";
        create.headers["Authorization"] =
            "Bearer development-secret-change-this-token";
        create.headers["Idempotency-Key"] = "create-task-0001";
        create.fields["title"] = "Implement API authentication";
        create.fields["description"] =
            "Validate bearer credentials and reject unauthenticated requests.";

        const Response created = api.handle(create);
        printResponse("Create", created);

        // A retry with the same key and payload returns the original task.
        printResponse("Idempotent replay", api.handle(create));

        const std::string taskId = "task-1";

        Request retrieve;
        retrieve.method = HttpMethod::Get;
        retrieve.path = "/v1/tasks/" + taskId;
        retrieve.clientAddress = "127.0.0.1";
        retrieve.headers["Authorization"] =
            "Bearer development-secret-change-this-token";
        printResponse("Retrieve", api.handle(retrieve));

        Request update;
        update.method = HttpMethod::Patch;
        update.path = "/v1/tasks/" + taskId;
        update.clientAddress = "127.0.0.1";
        update.headers["Authorization"] =
            "Bearer development-secret-change-this-token";
        update.headers["If-Match"] = "\"1\"";
        update.fields["status"] = "in_progress";
        printResponse("Update", api.handle(update));

        // Version 1 is now stale because the successful update produced version 2.
        printResponse("Stale update", api.handle(update));

        Request invalidTransition = update;
        invalidTransition.headers["If-Match"] = "\"2\"";
        invalidTransition.fields["status"] = "pending";
        printResponse(
            "Permitted transition back to pending",
            api.handle(invalidTransition)
        );

        Request invalidAuthentication = retrieve;
        invalidAuthentication.headers["Authorization"] = "Bearer invalid-token";
        printResponse(
            "Authentication failure",
            api.handle(invalidAuthentication)
        );
    } catch (const std::exception& error) {
        std::cerr << "Fatal error: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
