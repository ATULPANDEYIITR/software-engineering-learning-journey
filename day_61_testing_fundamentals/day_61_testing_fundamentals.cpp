#include <algorithm>
#include <cassert>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

namespace fs = std::filesystem;

struct User {
    int id;
    std::string name;
    std::string email;
};

enum class TestLevel {
    Unit,
    Integration,
    System
};

std::string levelName(TestLevel level) {
    switch (level) {
        case TestLevel::Unit: return "UNIT";
        case TestLevel::Integration: return "INTEGRATION";
        case TestLevel::System: return "SYSTEM";
    }
    return "UNKNOWN";
}

bool isValidEmail(const std::string& email) {
    const auto at = email.find('@');
    if (at == std::string::npos || at == 0 || at + 1 >= email.size()) {
        return false;
    }

    const auto dot = email.find('.', at + 1);
    return dot != std::string::npos &&
           dot + 1 < email.size() &&
           email.find(' ') == std::string::npos;
}

double calculateDiscount(double total, double percentage) {
    if (total < 0.0) {
        throw std::invalid_argument("total cannot be negative");
    }
    if (percentage < 0.0 || percentage > 100.0) {
        throw std::invalid_argument("percentage must be between 0 and 100");
    }

    const double result = total * (1.0 - percentage / 100.0);
    return std::round(result * 100.0) / 100.0;
}

class UserRepository {
private:
    std::unordered_map<int, User> users;

public:
    void save(const User& user) {
        if (user.id <= 0) {
            throw std::invalid_argument("id must be positive");
        }
        if (user.name.empty()) {
            throw std::invalid_argument("name must not be empty");
        }
        if (!isValidEmail(user.email)) {
            throw std::invalid_argument("invalid email");
        }
        if (users.contains(user.id)) {
            throw std::runtime_error("user already exists");
        }

        users.emplace(user.id, user);
    }

    std::optional<User> find(int id) const {
        auto it = users.find(id);
        if (it == users.end()) {
            return std::nullopt;
        }
        return it->second;
    }
};

class UserService {
private:
    UserRepository& repository;

public:
    explicit UserService(UserRepository& repository)
        : repository(repository) {}

    void registerUser(const User& user) {
        repository.save(user);
    }

    User getUser(int id) const {
        auto user = repository.find(id);
        if (!user) {
            throw std::runtime_error("user not found");
        }
        return *user;
    }

    fs::path exportUser(int id, const fs::path& directory) const {
        const User user = getUser(id);
        fs::create_directories(directory);

        const fs::path output = directory / ("user-" + std::to_string(id) + ".txt");
        std::ofstream file(output, std::ios::out | std::ios::trunc);

        if (!file) {
            throw std::runtime_error("unable to create export file");
        }

        file << "id=" << user.id << '\n';
        file << "name=" << user.name << '\n';
        file << "email=" << user.email << '\n';

        if (!file.good()) {
            throw std::runtime_error("failed while writing export file");
        }

        return output;
    }
};

void testEmailValidation() {
    assert(isValidEmail("user@example.com"));
    assert(!isValidEmail("user example.com"));
    assert(!isValidEmail("user@example"));
}

void testDiscount() {
    assert(calculateDiscount(1000.0, 20.0) == 800.0);
    assert(calculateDiscount(1000.0, 0.0) == 1000.0);
    assert(calculateDiscount(1000.0, 100.0) == 0.0);

    try {
        calculateDiscount(-1.0, 10.0);
        assert(false);
    } catch (const std::invalid_argument&) {
        // Expected failure path.
    }

    try {
        calculateDiscount(100.0, 101.0);
        assert(false);
    } catch (const std::invalid_argument&) {
        // Expected failure path.
    }
}

void testRepositoryServiceIntegration() {
    UserRepository repository;
    UserService service(repository);

    User user{1, "Atul", "atul@example.com"};
    service.registerUser(user);

    const User loaded = service.getUser(1);
    assert(loaded.id == 1);
    assert(loaded.name == "Atul");

    try {
        service.registerUser(user);
        assert(false);
    } catch (const std::runtime_error&) {
        // Duplicate identity is rejected at the repository boundary.
    }
}

void testSystemWorkflow() {
    UserRepository repository;
    UserService service(repository);

    service.registerUser({7, "System User", "system@example.com"});

    const fs::path directory =
        fs::temp_directory_path() / "testing_fundamentals_cpp";

    fs::remove_all(directory);

    const fs::path output = service.exportUser(7, directory);
    assert(fs::exists(output));

    std::ifstream file(output);
    std::string contents(
        (std::istreambuf_iterator<char>(file)),
        std::istreambuf_iterator<char>()
    );

    assert(contents.find("id=7") != std::string::npos);
    assert(contents.find("System User") != std::string::npos);
    assert(contents.find("system@example.com") != std::string::npos);

    fs::remove_all(directory);
}

struct TestCase {
    std::string name;
    TestLevel level;
    void (*function)();
};

int main() {
    const std::vector<TestCase> tests = {
        {"email validation", TestLevel::Unit, testEmailValidation},
        {"discount rules", TestLevel::Unit, testDiscount},
        {"repository and service", TestLevel::Integration,
         testRepositoryServiceIntegration},
        {"registration and file export", TestLevel::System, testSystemWorkflow}
    };

    std::size_t passed = 0;

    for (const auto& test : tests) {
        try {
            test.function();
            ++passed;
            std::cout << "[PASS] "
                      << levelName(test.level)
                      << " - "
                      << test.name
                      << '\n';
        } catch (const std::exception& error) {
            std::cerr << "[FAIL] "
                      << levelName(test.level)
                      << " - "
                      << test.name
                      << ": "
                      << error.what()
                      << '\n';
            return 1;
        } catch (...) {
            std::cerr << "[FAIL] "
                      << levelName(test.level)
                      << " - "
                      << test.name
                      << ": unknown exception\n";
            return 1;
        }
    }

    std::cout << "\nPassed " << passed
              << " of " << tests.size()
              << " tests.\n";

    std::cout << "\nTesting boundaries:\n"
              << "- Unit tests isolate deterministic rules.\n"
              << "- Integration tests verify component collaboration.\n"
              << "- System tests exercise an end-to-end workflow.\n"
              << "- Invalid input and duplicate data are explicit failure cases.\n"
              << "- File operations are tested as an external system boundary.\n";

    return 0;
}
