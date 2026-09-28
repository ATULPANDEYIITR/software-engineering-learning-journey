/*
    Software Engineering Project: Build a Small CLI Application with Git

    C++17 case study:
    A small release/task management CLI for a software team.

    The application models a realistic workflow:

        project
          |
          +-- tasks
          |
          +-- release notes
          |
          +-- Git repository
                |
                +-- status
                +-- add
                +-- commit
                +-- branch
                +-- log

    The implementation demonstrates:
      - classes and encapsulation
      - vectors, maps, and algorithms
      - filesystem operations
      - validation
      - subprocess execution
      - Git integration
      - error handling
      - command dispatch
      - persistence
      - complexity considerations
      - testable architecture

    Compile:
        g++ -std=c++17 -Wall -Wextra -pedantic git_project_cli.cpp -o git_project_cli

    Examples:
        ./git_project_cli init demo
        ./git_project_cli add-task demo "Implement authentication"
        ./git_project_cli list-tasks demo
        ./git_project_cli complete-task demo 1
        ./git_project_cli status demo
        ./git_project_cli commit demo "Add authentication task"
        ./git_project_cli log demo
        ./git_project_cli branch demo feature-auth
*/

#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <system_error>
#include <vector>

namespace fs = std::filesystem;

namespace config {
    constexpr const char* MetadataFile = ".project.meta";
    constexpr const char* TasksFile = "tasks.db";
    constexpr const char* ReadmeFile = "README.md";
}


// -----------------------------------------------------------------------------
// Utility functions
// -----------------------------------------------------------------------------

std::string trim(const std::string& value) {
    const auto first = value.find_first_not_of(" \t\r\n");

    if (first == std::string::npos) {
        return "";
    }

    const auto last = value.find_last_not_of(" \t\r\n");
    return value.substr(first, last - first + 1);
}


std::string nowUtc() {
    const auto current = std::chrono::system_clock::now();
    const std::time_t currentTime =
        std::chrono::system_clock::to_time_t(current);

    std::tm utcTime{};

#ifdef _WIN32
    gmtime_s(&utcTime, &currentTime);
#else
    gmtime_r(&currentTime, &utcTime);
#endif

    std::ostringstream output;
    output << std::put_time(&utcTime, "%Y-%m-%dT%H:%M:%SZ");
    return output.str();
}


bool isPositiveInteger(const std::string& value) {
    if (value.empty()) {
        return false;
    }

    return std::all_of(
        value.begin(),
        value.end(),
        [](unsigned char character) {
            return std::isdigit(character) != 0;
        }
    );
}


int parsePositiveInteger(const std::string& value) {
    if (!isPositiveInteger(value)) {
        throw std::invalid_argument(
            "Expected a positive integer."
        );
    }

    const long long parsed = std::stoll(value);

    if (parsed > static_cast<long long>(INT_MAX)) {
        throw std::invalid_argument(
            "Integer value is too large."
        );
    }

    return static_cast<int>(parsed);
}


bool validBranchName(const std::string& name) {
    if (name.empty() || name.front() == '/' || name.back() == '/') {
        return false;
    }

    return std::all_of(
        name.begin(),
        name.end(),
        [](unsigned char character) {
            return std::isalnum(character) ||
                   character == '-' ||
                   character == '_' ||
                   character == '/';
        }
    );
}


// -----------------------------------------------------------------------------
// Data model
// -----------------------------------------------------------------------------

struct Task {
    int id{};
    std::string title;
    bool completed{false};
    std::string createdAt;
};


// -----------------------------------------------------------------------------
// Repository layer
// -----------------------------------------------------------------------------

class TaskRepository {
public:
    explicit TaskRepository(fs::path projectRoot)
        : root_(std::move(projectRoot)) {}

    fs::path taskFile() const {
        return root_ / config::TasksFile;
    }

    std::vector<Task> load() const {
        std::vector<Task> tasks;

        std::ifstream input(taskFile());

        if (!input) {
            return tasks;
        }

        /*
            A deliberately simple line format is used:

                id|completed|createdAt|title

            The format is easy to inspect and requires no external database.
            A production system with concurrent writers or complex queries
            would normally use a transactional database.
        */
        std::string line;

        while (std::getline(input, line)) {
            if (line.empty()) {
                continue;
            }

            std::stringstream stream(line);

            std::string idText;
            std::string completedText;
            std::string createdAt;
            std::string title;

            if (!std::getline(stream, idText, '|') ||
                !std::getline(stream, completedText, '|') ||
                !std::getline(stream, createdAt, '|') ||
                !std::getline(stream, title)) {
                throw std::runtime_error(
                    "Corrupt task database entry."
                );
            }

            Task task;
            task.id = parsePositiveInteger(idText);
            task.completed = completedText == "1";
            task.createdAt = createdAt;
            task.title = title;

            tasks.push_back(task);
        }

        return tasks;
    }

    void save(const std::vector<Task>& tasks) const {
        /*
            Write to a temporary file first and then replace the original.
            This reduces the chance of leaving a partially written task file
            if the process is interrupted during output.
        */
        const fs::path temporary = taskFile().string() + ".tmp";

        {
            std::ofstream output(temporary, std::ios::trunc);

            if (!output) {
                throw std::runtime_error(
                    "Unable to write temporary task database."
                );
            }

            for (const Task& task : tasks) {
                output
                    << task.id << '|'
                    << (task.completed ? "1" : "0") << '|'
                    << task.createdAt << '|'
                    << task.title << '\n';
            }
        }

        std::error_code error;

        fs::rename(temporary, taskFile(), error);

        if (error) {
            fs::remove(taskFile(), error);
            error.clear();
            fs::rename(temporary, taskFile(), error);

            if (error) {
                throw std::runtime_error(
                    "Unable to replace task database: " +
                    error.message()
                );
            }
        }
    }

private:
    fs::path root_;
};


// -----------------------------------------------------------------------------
// Git integration layer
// -----------------------------------------------------------------------------

class GitClient {
public:
    explicit GitClient(fs::path root)
        : root_(std::move(root)) {}

    void initialize() const {
        execute({"git", "init"});
    }

    bool isRepository() const {
        const int result = std::system(
            buildCommand({"git", "rev-parse", "--is-inside-work-tree"})
                .c_str()
        );

        return result == 0;
    }

    void addAll() const {
        execute({"git", "add", "."});
    }

    void commit(const std::string& message) const {
        if (trim(message).empty()) {
            throw std::invalid_argument(
                "Commit message cannot be empty."
            );
        }

        /*
            This case study uses std::system for portability and simplicity.
            Production software should prefer a dedicated process API when
            available, because it provides stronger control over argument
            boundaries and process behavior.
        */
        execute({
            "git",
            "commit",
            "-m",
            message
        });
    }

    void createBranch(const std::string& name) const {
        if (!validBranchName(name)) {
            throw std::invalid_argument(
                "Invalid branch name."
            );
        }

        execute({
            "git",
            "switch",
            "-c",
            name
        });
    }

    std::string status() const {
        return capture({
            "git",
            "status",
            "--short",
            "--branch"
        });
    }

    std::string log(int limit) const {
        if (limit < 1) {
            throw std::invalid_argument(
                "Log limit must be positive."
            );
        }

        return capture({
            "git",
            "log",
            "-" + std::to_string(limit),
            "--date=short",
            "--pretty=format:%h | %ad | %an | %s"
        });
    }

    std::string currentBranch() const {
        return capture({
            "git",
            "branch",
            "--show-current"
        });
    }

private:
    fs::path root_;

    std::string shellQuote(const std::string& argument) const {
#ifdef _WIN32
        /*
            Windows command-line quoting is more complicated than POSIX
            quoting. This conservative transformation handles spaces and
            embedded quotes for this educational case study.
        */
        std::string result = "\"";

        for (char character : argument) {
            if (character == '"') {
                result += "\\\"";
            } else {
                result += character;
            }
        }

        result += "\"";
        return result;
#else
        std::string result = "'";

        for (char character : argument) {
            if (character == '\'') {
                result += "'\\''";
            } else {
                result += character;
            }
        }

        result += "'";
        return result;
#endif
    }

    std::string buildCommand(
        const std::vector<std::string>& arguments
    ) const {
        std::ostringstream command;

        for (const auto& argument : arguments) {
            command << shellQuote(argument) << ' ';
        }

        return command.str();
    }

    void execute(
        const std::vector<std::string>& arguments
    ) const {
        const fs::path previousPath = fs::current_path();

        try {
            fs::current_path(root_);

            const int result = std::system(
                buildCommand(arguments).c_str()
            );

            fs::current_path(previousPath);

            if (result != 0) {
                throw std::runtime_error(
                    "Git command failed."
                );
            }
        } catch (...) {
            fs::current_path(previousPath);
            throw;
        }
    }

    std::string capture(
        const std::vector<std::string>& arguments
    ) const {
        /*
            Temporary output capture is used to keep the example within the
            C++ standard library. A real production implementation should
            use a platform-specific process API or a carefully selected
            subprocess library.
        */
        const fs::path temporary =
            fs::temp_directory_path() /
            ("git_cli_capture_" + std::to_string(std::rand()) + ".txt");

        const fs::path previousPath = fs::current_path();

        try {
            fs::current_path(root_);

            const std::string command =
                buildCommand(arguments) +
                " > " + shellQuote(temporary.string());

            const int result = std::system(command.c_str());

            fs::current_path(previousPath);

            if (result != 0) {
                fs::remove(temporary);
                throw std::runtime_error(
                    "Git command failed."
                );
            }

            std::ifstream input(temporary);
            std::ostringstream output;
            output << input.rdbuf();

            fs::remove(temporary);

            return trim(output.str());
        } catch (...) {
            fs::current_path(previousPath);
            fs::remove(temporary);
            throw;
        }
    }
};


// -----------------------------------------------------------------------------
// Application service layer
// -----------------------------------------------------------------------------

class ProjectService {
public:
    static void createProject(const fs::path& directory) {
        const fs::path root = fs::absolute(directory);

        if (fs::exists(root) && !fs::is_directory(root)) {
            throw std::runtime_error(
                "Project path exists but is not a directory."
            );
        }

        if (fs::exists(root) && !fs::is_empty(root)) {
            throw std::runtime_error(
                "Project directory exists and is not empty."
            );
        }

        fs::create_directories(root);

        std::ofstream metadata(root / config::MetadataFile);

        if (!metadata) {
            throw std::runtime_error(
                "Unable to create project metadata."
            );
        }

        metadata
            << "name=" << root.filename().string() << '\n'
            << "created_at=" << nowUtc() << '\n'
            << "version=1.0.0\n";

        std::ofstream tasks(root / config::TasksFile);

        if (!tasks) {
            throw std::runtime_error(
                "Unable to create task database."
            );
        }

        std::ofstream readme(root / config::ReadmeFile);

        if (!readme) {
            throw std::runtime_error(
                "Unable to create README."
            );
        }

        readme
            << "# " << root.filename().string() << "\n\n"
            << "This project is managed by a Git-backed CLI application.\n";

        GitClient git(root);
        git.initialize();
    }

    static Task addTask(
        const fs::path& projectRoot,
        const std::string& title
    ) {
        const std::string cleanTitle = trim(title);

        if (cleanTitle.empty()) {
            throw std::invalid_argument(
                "Task title cannot be empty."
            );
        }

        if (cleanTitle.size() > 200) {
            throw std::invalid_argument(
                "Task title cannot exceed 200 characters."
            );
        }

        TaskRepository repository(projectRoot);
        auto tasks = repository.load();

        int nextId = 1;

        for (const Task& task : tasks) {
            nextId = std::max(nextId, task.id + 1);
        }

        Task task{
            nextId,
            cleanTitle,
            false,
            nowUtc()
        };

        tasks.push_back(task);
        repository.save(tasks);

        return task;
    }

    static Task completeTask(
        const fs::path& projectRoot,
        int taskId
    ) {
        TaskRepository repository(projectRoot);
        auto tasks = repository.load();

        for (Task& task : tasks) {
            if (task.id == taskId) {
                task.completed = true;
                repository.save(tasks);
                return task;
            }
        }

        throw std::invalid_argument(
            "Task does not exist."
        );
    }

    static void removeTask(
        const fs::path& projectRoot,
        int taskId
    ) {
        TaskRepository repository(projectRoot);
        auto tasks = repository.load();

        const auto originalSize = tasks.size();

        tasks.erase(
            std::remove_if(
                tasks.begin(),
                tasks.end(),
                [taskId](const Task& task) {
                    return task.id == taskId;
                }
            ),
            tasks.end()
        );

        if (tasks.size() == originalSize) {
            throw std::invalid_argument(
                "Task does not exist."
            );
        }

        repository.save(tasks);
    }

    static std::vector<Task> listTasks(
        const fs::path& projectRoot
    ) {
        TaskRepository repository(projectRoot);
        return repository.load();
    }
};


// -----------------------------------------------------------------------------
// CLI presentation
// -----------------------------------------------------------------------------

void printUsage() {
    std::cout
        << "git-project-cli\n\n"
        << "Commands:\n"
        << "  init <project>\n"
        << "  add-task <project> <title>\n"
        << "  list-tasks <project>\n"
        << "  complete-task <project> <id>\n"
        << "  remove-task <project> <id>\n"
        << "  status <project>\n"
        << "  commit <project> <message>\n"
        << "  log <project> [limit]\n"
        << "  branch <project> <name>\n";
}


void requireProject(const fs::path& project) {
    if (!fs::exists(project)) {
        throw std::runtime_error(
            "Project directory does not exist."
        );
    }

    if (!fs::exists(project / config::MetadataFile)) {
        throw std::runtime_error(
            "Directory is not a managed project."
        );
    }
}


std::string joinArguments(
    int start,
    int argc,
    char* argv[]
) {
    std::ostringstream output;

    for (int index = start; index < argc; ++index) {
        if (index > start) {
            output << ' ';
        }

        output << argv[index];
    }

    return output.str();
}


int run(int argc, char* argv[]) {
    if (argc < 2) {
        printUsage();
        return 0;
    }

    const std::string command = argv[1];

    if (command == "init") {
        if (argc != 3) {
            throw std::invalid_argument(
                "Usage: init <project>"
            );
        }

        ProjectService::createProject(argv[2]);

        std::cout
            << "Project created: "
            << fs::absolute(argv[2])
            << "\n";

        return 0;
    }

    if (command == "add-task") {
        if (argc < 4) {
            throw std::invalid_argument(
                "Usage: add-task <project> <title>"
            );
        }

        const fs::path project = argv[2];
        requireProject(project);

        const Task task =
            ProjectService::addTask(
                project,
                joinArguments(3, argc, argv)
            );

        std::cout
            << "Added task "
            << task.id
            << ": "
            << task.title
            << "\n";

        return 0;
    }

    if (command == "list-tasks") {
        if (argc != 3) {
            throw std::invalid_argument(
                "Usage: list-tasks <project>"
            );
        }

        const fs::path project = argv[2];
        requireProject(project);

        const auto tasks =
            ProjectService::listTasks(project);

        if (tasks.empty()) {
            std::cout << "No tasks.\n";
            return 0;
        }

        for (const Task& task : tasks) {
            std::cout
                << '['
                << (task.completed ? 'x' : ' ')
                << "] "
                << task.id
                << ": "
                << task.title
                << '\n';
        }

        return 0;
    }

    if (command == "complete-task") {
        if (argc != 4) {
            throw std::invalid_argument(
                "Usage: complete-task <project> <id>"
            );
        }

        const fs::path project = argv[2];
        requireProject(project);

        const int id = parsePositiveInteger(argv[3]);

        const Task task =
            ProjectService::completeTask(project, id);

        std::cout
            << "Completed task "
            << task.id
            << ": "
            << task.title
            << '\n';

        return 0;
    }

    if (command == "remove-task") {
        if (argc != 4) {
            throw std::invalid_argument(
                "Usage: remove-task <project> <id>"
            );
        }

        const fs::path project = argv[2];
        requireProject(project);

        const int id = parsePositiveInteger(argv[3]);

        ProjectService::removeTask(project, id);

        std::cout
            << "Removed task "
            << id
            << ".\n";

        return 0;
    }

    if (command == "status") {
        if (argc != 3) {
            throw std::invalid_argument(
                "Usage: status <project>"
            );
        }

        const fs::path project = argv[2];
        requireProject(project);

        GitClient git(project);

        std::cout << git.status() << '\n';
        return 0;
    }

    if (command == "commit") {
        if (argc < 4) {
            throw std::invalid_argument(
                "Usage: commit <project> <message>"
            );
        }

        const fs::path project = argv[2];
        requireProject(project);

        GitClient git(project);

        const std::string message =
            joinArguments(3, argc, argv);

        git.addAll();
        git.commit(message);

        std::cout << "Commit created.\n";
        return 0;
    }

    if (command == "log") {
        if (argc < 3 || argc > 4) {
            throw std::invalid_argument(
                "Usage: log <project> [limit]"
            );
        }

        const fs::path project = argv[2];
        requireProject(project);

        int limit = 10;

        if (argc == 4) {
            limit = parsePositiveInteger(argv[3]);
        }

        GitClient git(project);

        std::cout << git.log(limit) << '\n';
        return 0;
    }

    if (command == "branch") {
        if (argc != 4) {
            throw std::invalid_argument(
                "Usage: branch <project> <name>"
            );
        }

        const fs::path project = argv[2];
        requireProject(project);

        GitClient git(project);

        git.createBranch(argv[3]);

        std::cout
            << "Current branch: "
            << git.currentBranch()
            << '\n';

        return 0;
    }

    if (command == "help" || command == "--help") {
        printUsage();
        return 0;
    }

    throw std::invalid_argument(
        "Unknown command: " + command
    );
}


// -----------------------------------------------------------------------------
// Entry point
// -----------------------------------------------------------------------------

int main(int argc, char* argv[]) {
    try {
        return run(argc, argv);
    } catch (const std::exception& error) {
        std::cerr
            << "Error: "
            << error.what()
            << '\n';

        return 1;
    }
}
