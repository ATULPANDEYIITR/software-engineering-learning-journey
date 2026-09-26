/*
 * GitHub Repository Operations Case Study
 * ========================================
 *
 * C++17 implementation of a realistic local engineering-management system
 * modeled around GitHub concepts:
 *
 *   Repository
 *       |
 *       +-- Issues
 *       |
 *       +-- Project planning
 *       |
 *       +-- Releases
 *               |
 *               +-- Semantic version
 *               +-- Release assets
 *
 * This program does not require an external GitHub SDK. It models the
 * important data structures, workflows, validation rules, algorithms,
 * state transitions, and reporting that a production integration could use.
 *
 * Compile:
 *   g++ -std=c++17 -O2 -Wall -Wextra -pedantic github_case_study.cpp -o github_case_study
 *
 * Run:
 *   ./github_case_study
 *
 * The standard library is intentionally used so the case study is portable.
 */

#include <algorithm>
#include <cassert>
#include <cctype>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <regex>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

using namespace std;


// ============================================================================
// 1. GENERAL UTILITIES
// ============================================================================

string trim(const string& value) {
    const auto first = value.find_first_not_of(" \t\n\r");

    if (first == string::npos) {
        return "";
    }

    const auto last = value.find_last_not_of(" \t\n\r");

    return value.substr(
        first,
        last - first + 1
    );
}

string toLower(string value) {
    transform(
        value.begin(),
        value.end(),
        value.begin(),
        [](unsigned char character) {
            return static_cast<char>(
                tolower(character)
            );
        }
    );

    return value;
}

bool isValidRepositoryName(const string& name) {
    if (name.empty()) {
        return false;
    }

    static const regex pattern(
        R"([A-Za-z0-9._-]+)"
    );

    return regex_match(name, pattern);
}


// ============================================================================
// 2. ENUMERATIONS
// ============================================================================

enum class Visibility {
    Public,
    Private,
    Internal
};

enum class IssueState {
    Open,
    Closed
};

enum class ProjectStatus {
    Todo,
    InProgress,
    Done,
    Blocked
};

string toString(Visibility visibility) {
    switch (visibility) {
        case Visibility::Public:
            return "public";
        case Visibility::Private:
            return "private";
        case Visibility::Internal:
            return "internal";
    }

    return "unknown";
}

string toString(IssueState state) {
    return state == IssueState::Open
        ? "open"
        : "closed";
}

string toString(ProjectStatus status) {
    switch (status) {
        case ProjectStatus::Todo:
            return "Todo";
        case ProjectStatus::InProgress:
            return "In Progress";
        case ProjectStatus::Done:
            return "Done";
        case ProjectStatus::Blocked:
            return "Blocked";
    }

    return "Unknown";
}


// ============================================================================
// 3. REPOSITORY
// ============================================================================

class Repository {
private:
    string owner_;
    string name_;
    string description_;
    Visibility visibility_;
    string defaultBranch_;
    bool archived_ = false;

    set<string> topics_;

public:
    Repository(
        string owner,
        string name,
        string description,
        Visibility visibility,
        string defaultBranch = "main"
    )
        : owner_(move(owner)),
          name_(move(name)),
          description_(move(description)),
          visibility_(visibility),
          defaultBranch_(move(defaultBranch)) {

        if (owner_.empty()) {
            throw invalid_argument(
                "Repository owner cannot be empty."
            );
        }

        if (!isValidRepositoryName(name_)) {
            throw invalid_argument(
                "Invalid repository name."
            );
        }

        if (defaultBranch_.empty()) {
            throw invalid_argument(
                "Default branch cannot be empty."
            );
        }
    }

    const string& owner() const {
        return owner_;
    }

    const string& name() const {
        return name_;
    }

    string fullName() const {
        return owner_ + "/" + name_;
    }

    Visibility visibility() const {
        return visibility_;
    }

    const string& defaultBranch() const {
        return defaultBranch_;
    }

    bool archived() const {
        return archived_;
    }

    void archive() {
        archived_ = true;
    }

    void addTopic(const string& topic) {
        const string normalized = toLower(trim(topic));

        if (normalized.empty()) {
            throw invalid_argument(
                "Repository topic cannot be empty."
            );
        }

        topics_.insert(normalized);
    }

    void removeTopic(const string& topic) {
        topics_.erase(
            toLower(trim(topic))
        );
    }

    const set<string>& topics() const {
        return topics_;
    }
};


// ============================================================================
// 4. ISSUE
// ============================================================================

struct Comment {
    string author;
    string body;
};

class Issue {
private:
    int number_;
    string title_;
    string body_;
    IssueState state_ = IssueState::Open;

    set<string> labels_;
    set<string> assignees_;
    optional<string> milestone_;
    vector<Comment> comments_;

public:
    Issue(
        int number,
        string title,
        string body
    )
        : number_(number),
          title_(move(title)),
          body_(move(body)) {

        if (trim(title_).empty()) {
            throw invalid_argument(
                "Issue title cannot be empty."
            );
        }
    }

    int number() const {
        return number_;
    }

    const string& title() const {
        return title_;
    }

    IssueState state() const {
        return state_;
    }

    void addLabel(const string& label) {
        const string normalized = trim(label);

        if (normalized.empty()) {
            throw invalid_argument(
                "Issue label cannot be empty."
            );
        }

        labels_.insert(normalized);
    }

    void assign(const string& username) {
        const string normalized = trim(username);

        if (normalized.empty()) {
            throw invalid_argument(
                "Assignee cannot be empty."
            );
        }

        assignees_.insert(normalized);
    }

    void setMilestone(const string& milestone) {
        const string normalized = trim(milestone);

        if (normalized.empty()) {
            throw invalid_argument(
                "Milestone cannot be empty."
            );
        }

        milestone_ = normalized;
    }

    void addComment(
        const string& author,
        const string& body
    ) {
        if (trim(author).empty()) {
            throw invalid_argument(
                "Comment author cannot be empty."
            );
        }

        if (trim(body).empty()) {
            throw invalid_argument(
                "Comment body cannot be empty."
            );
        }

        comments_.push_back({
            author,
            body
        });
    }

    void close() {
        state_ = IssueState::Closed;
    }

    void reopen() {
        state_ = IssueState::Open;
    }

    bool hasLabel(const string& label) const {
        return labels_.contains(label);
    }

    const set<string>& labels() const {
        return labels_;
    }

    string summary() const {
        ostringstream output;

        output
            << "#" << number_
            << " [" << toString(state_) << "] "
            << title_;

        return output.str();
    }
};


// ============================================================================
// 5. ISSUE TRACKER
// ============================================================================

class IssueTracker {
private:
    unordered_map<int, Issue> issues_;
    int nextNumber_ = 1;

public:
    Issue& createIssue(
        const string& title,
        const string& body = ""
    ) {
        const int number = nextNumber_++;

        auto [iterator, inserted] =
            issues_.emplace(
                piecewise_construct,
                forward_as_tuple(number),
                forward_as_tuple(
                    number,
                    title,
                    body
                )
            );

        if (!inserted) {
            throw runtime_error(
                "Unable to create issue."
            );
        }

        return iterator->second;
    }

    Issue& get(int number) {
        auto iterator = issues_.find(number);

        if (iterator == issues_.end()) {
            throw out_of_range(
                "Issue number does not exist."
            );
        }

        return iterator->second;
    }

    const unordered_map<int, Issue>& all() const {
        return issues_;
    }

    vector<reference_wrapper<const Issue>> list(
        optional<IssueState> state = nullopt,
        optional<string> label = nullopt
    ) const {
        vector<reference_wrapper<const Issue>> result;

        for (const auto& [number, issue] : issues_) {
            if (state && issue.state() != *state) {
                continue;
            }

            if (label && !issue.hasLabel(*label)) {
                continue;
            }

            result.push_back(
                cref(issue)
            );
        }

        sort(
            result.begin(),
            result.end(),
            [](const auto& left, const auto& right) {
                return left.get().number()
                    < right.get().number();
            }
        );

        return result;
    }
};


// ============================================================================
// 6. PROJECT ITEMS
// ============================================================================

struct ProjectItem {
    int id;
    string title;
    ProjectStatus status = ProjectStatus::Todo;
    int priority = 3;
    optional<int> linkedIssue;
    set<string> labels;
};

class ProjectBoard {
private:
    string name_;
    map<int, ProjectItem> items_;
    int nextId_ = 1;

public:
    explicit ProjectBoard(string name)
        : name_(move(name)) {

        if (trim(name_).empty()) {
            throw invalid_argument(
                "Project name cannot be empty."
            );
        }
    }

    ProjectItem& addItem(
        const string& title,
        int priority,
        optional<int> linkedIssue = nullopt
    ) {
        if (trim(title).empty()) {
            throw invalid_argument(
                "Project item title cannot be empty."
            );
        }

        if (priority < 1 || priority > 5) {
            throw invalid_argument(
                "Priority must be between 1 and 5."
            );
        }

        ProjectItem item{
            nextId_++,
            title,
            ProjectStatus::Todo,
            priority,
            linkedIssue,
            {}
        };

        const int id = item.id;

        auto [iterator, inserted] =
            items_.emplace(id, move(item));

        if (!inserted) {
            throw runtime_error(
                "Unable to create project item."
            );
        }

        return iterator->second;
    }

    ProjectItem& getItem(int id) {
        auto iterator = items_.find(id);

        if (iterator == items_.end()) {
            throw out_of_range(
                "Project item does not exist."
            );
        }

        return iterator->second;
    }

    void moveItem(
        int id,
        ProjectStatus status
    ) {
        getItem(id).status = status;
    }

    double progress() const {
        if (items_.empty()) {
            return 0.0;
        }

        size_t completed = 0;

        for (const auto& [id, item] : items_) {
            if (item.status == ProjectStatus::Done) {
                ++completed;
            }
        }

        return (
            static_cast<double>(completed)
            / static_cast<double>(items_.size())
        ) * 100.0;
    }

    const map<int, ProjectItem>& items() const {
        return items_;
    }

    void print() const {
        cout << "\nProject: " << name_ << "\n";

        for (const auto& [id, item] : items_) {
            cout
                << "  #"
                << id
                << " "
                << item.title
                << " | "
                << toString(item.status)
                << " | priority="
                << item.priority;

            if (item.linkedIssue) {
                cout
                    << " | issue=#"
                    << *item.linkedIssue;
            }

            cout << "\n";
        }

        cout
            << fixed
            << setprecision(1)
            << "Completion: "
            << progress()
            << "%\n";
    }
};


// ============================================================================
// 7. SEMANTIC VERSION
// ============================================================================

class SemanticVersion {
private:
    int major_;
    int minor_;
    int patch_;
    string prerelease_;
    string build_;

public:
    SemanticVersion(
        int major,
        int minor,
        int patch,
        string prerelease = "",
        string build = ""
    )
        : major_(major),
          minor_(minor),
          patch_(patch),
          prerelease_(move(prerelease)),
          build_(move(build)) {

        if (major < 0 || minor < 0 || patch < 0) {
            throw invalid_argument(
                "Semantic-version components cannot be negative."
            );
        }
    }

    static SemanticVersion parse(
        const string& value
    ) {
        static const regex pattern(
            R"(^v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-([0-9A-Za-z.-]+))?(?:\+([0-9A-Za-z.-]+))?$)"
        );

        smatch match;

        if (!regex_match(value, match, pattern)) {
            throw invalid_argument(
                "Invalid semantic version: " + value
            );
        }

        return SemanticVersion(
            stoi(match[1].str()),
            stoi(match[2].str()),
            stoi(match[3].str()),
            match[4].matched
                ? match[4].str()
                : "",
            match[5].matched
                ? match[5].str()
                : ""
        );
    }

    int major() const {
        return major_;
    }

    int minor() const {
        return minor_;
    }

    int patch() const {
        return patch_;
    }

    SemanticVersion bumpMajor() const {
        return SemanticVersion(
            major_ + 1,
            0,
            0
        );
    }

    SemanticVersion bumpMinor() const {
        return SemanticVersion(
            major_,
            minor_ + 1,
            0
        );
    }

    SemanticVersion bumpPatch() const {
        return SemanticVersion(
            major_,
            minor_,
            patch_ + 1
        );
    }

    string toString() const {
        ostringstream output;

        output
            << "v"
            << major_
            << "."
            << minor_
            << "."
            << patch_;

        if (!prerelease_.empty()) {
            output
                << "-"
                << prerelease_;
        }

        if (!build_.empty()) {
            output
                << "+"
                << build_;
        }

        return output.str();
    }
};


// ============================================================================
// 8. RELEASE
// ============================================================================

struct ReleaseAsset {
    string name;
    long long sizeBytes;
    string contentType;
};

class Release {
private:
    SemanticVersion version_;
    string name_;
    string notes_;
    string tagName_;
    bool draft_;
    bool prerelease_;

    vector<ReleaseAsset> assets_;

public:
    Release(
        SemanticVersion version,
        string name,
        string notes,
        string tagName,
        bool draft = false,
        bool prerelease = false
    )
        : version_(move(version)),
          name_(move(name)),
          notes_(move(notes)),
          tagName_(move(tagName)),
          draft_(draft),
          prerelease_(prerelease) {

        if (name_.empty()) {
            throw invalid_argument(
                "Release name cannot be empty."
            );
        }

        if (tagName_.empty()) {
            throw invalid_argument(
                "Release tag cannot be empty."
            );
        }
    }

    void addAsset(ReleaseAsset asset) {
        if (trim(asset.name).empty()) {
            throw invalid_argument(
                "Asset name cannot be empty."
            );
        }

        if (asset.sizeBytes < 0) {
            throw invalid_argument(
                "Asset size cannot be negative."
            );
        }

        const auto duplicate =
            find_if(
                assets_.begin(),
                assets_.end(),
                [&](const ReleaseAsset& existing) {
                    return existing.name == asset.name;
                }
            );

        if (duplicate != assets_.end()) {
            throw invalid_argument(
                "Duplicate release asset: "
                + asset.name
            );
        }

        assets_.push_back(move(asset));
    }

    const SemanticVersion& version() const {
        return version_;
    }

    const string& name() const {
        return name_;
    }

    const vector<ReleaseAsset>& assets() const {
        return assets_;
    }

    bool validTag() const {
        return tagName_ == version_.toString();
    }
};


// ============================================================================
// 9. INTEGRATED WORKSPACE
// ============================================================================

class EngineeringWorkspace {
private:
    Repository repository_;
    IssueTracker issues_;
    ProjectBoard project_;
    map<string, Release> releases_;

public:
    explicit EngineeringWorkspace(
        Repository repository
    )
        : repository_(move(repository)),
          project_(
              repository_.name()
              + " Delivery Board"
          ) {}

    Issue& createWorkItem(
        const string& title,
        const string& body,
        int priority,
        const vector<string>& labels
    ) {
        Issue& issue =
            issues_.createIssue(
                title,
                body
            );

        for (const auto& label : labels) {
            issue.addLabel(label);
        }

        ProjectItem& projectItem =
            project_.addItem(
                title,
                priority,
                issue.number()
            );

        // The project item is intentionally retained through the board.
        // This demonstrates a relationship between an issue and a planning
        // record without assuming their identifiers are globally identical.
        (void)projectItem;

        return issue;
    }

    Release& createRelease(
        const string& version,
        const string& name,
        const string& notes
    ) {
        SemanticVersion parsed =
            SemanticVersion::parse(version);

        Release release(
            parsed,
            name,
            notes,
            parsed.toString()
        );

        auto [iterator, inserted] =
            releases_.emplace(
                parsed.toString(),
                move(release)
            );

        if (!inserted) {
            throw invalid_argument(
                "Release version already exists."
            );
        }

        return iterator->second;
    }

    Repository& repository() {
        return repository_;
    }

    IssueTracker& issues() {
        return issues_;
    }

    ProjectBoard& project() {
        return project_;
    }

    const map<string, Release>& releases() const {
        return releases_;
    }

    void report() const {
        cout << "\n";
        cout << string(80, '=') << "\n";
        cout << "INTEGRATED ENGINEERING WORKSPACE\n";
        cout << string(80, '=') << "\n";

        cout
            << "Repository: "
            << repository_.fullName()
            << "\n";

        cout
            << "Visibility: "
            << toString(repository_.visibility())
            << "\n";

        cout
            << "Default branch: "
            << repository_.defaultBranch()
            << "\n";

        cout << "\nIssues:\n";

        const auto issueList =
            issues_.list();

        for (const auto& issueReference : issueList) {
            cout
                << "  "
                << issueReference.get().summary()
                << "\n";
        }

        project_.print();

        cout << "\nReleases:\n";

        for (const auto& [version, release] : releases_) {
            cout
                << "  "
                << version
                << " | "
                << release.name()
                << " | assets="
                << release.assets().size()
                << "\n";
        }
    }
};


// ============================================================================
// 10. VALIDATION CASES
// ============================================================================

void validationExamples() {
    cout << "\n";
    cout << string(80, '=') << "\n";
    cout << "VALIDATION AND FAILURE CONDITIONS\n";
    cout << string(80, '=') << "\n";

    try {
        Repository invalid(
            "owner",
            "invalid repository name!",
            "",
            Visibility::Public
        );

        (void)invalid;
    } catch (const exception& error) {
        cout
            << "Correctly rejected repository: "
            << error.what()
            << "\n";
    }

    try {
        SemanticVersion::parse(
            "version-two"
        );
    } catch (const exception& error) {
        cout
            << "Correctly rejected version: "
            << error.what()
            << "\n";
    }

    try {
        ProjectBoard project(
            "Validation Project"
        );

        project.addItem(
            "Invalid priority",
            99
        );
    } catch (const exception& error) {
        cout
            << "Correctly rejected project item: "
            << error.what()
            << "\n";
    }

    try {
        IssueTracker tracker;

        tracker.createIssue(
            ""
        );
    } catch (const exception& error) {
        cout
            << "Correctly rejected issue: "
            << error.what()
            << "\n";
    }
}


// ============================================================================
// 11. SEARCH
// ============================================================================

vector<reference_wrapper<const Issue>> searchIssues(
    const IssueTracker& tracker,
    const string& text
) {
    vector<reference_wrapper<const Issue>> results;

    const string query =
        toLower(trim(text));

    for (const auto& [number, issue] : tracker.all()) {
        const string title =
            toLower(issue.title());

        if (title.find(query) != string::npos) {
            results.push_back(
                cref(issue)
            );
        }
    }

    sort(
        results.begin(),
        results.end(),
        [](const auto& left, const auto& right) {
            return left.get().number()
                < right.get().number();
        }
    );

    return results;
}


// ============================================================================
// 12. AUTOMATION RULES
// ============================================================================

struct AutomationRule {
    string name;
    string trigger;
    string action;
};

class AutomationEngine {
private:
    vector<AutomationRule> rules_;

public:
    void addRule(
        string name,
        string trigger,
        string action
    ) {
        if (trim(name).empty()) {
            throw invalid_argument(
                "Automation rule name cannot be empty."
            );
        }

        rules_.push_back({
            move(name),
            move(trigger),
            move(action)
        });
    }

    void printRules() const {
        for (const auto& rule : rules_) {
            cout
                << "  "
                << rule.name
                << ": WHEN "
                << rule.trigger
                << " THEN "
                << rule.action
                << "\n";
        }
    }
};


// ============================================================================
// 13. TESTS
// ============================================================================

void runTests() {
    cout << "\n";
    cout << string(80, '=') << "\n";
    cout << "AUTOMATED TESTS\n";
    cout << string(80, '=') << "\n";

    Repository repository(
        "test-owner",
        "test-repository",
        "Test repository",
        Visibility::Public
    );

    assert(
        repository.fullName()
        == "test-owner/test-repository"
    );

    repository.addTopic("C++");

    assert(
        repository.topics().contains("c++")
    );

    IssueTracker tracker;

    Issue& issue =
        tracker.createIssue(
            "Test issue"
        );

    issue.addLabel("bug");
    issue.assign("tester");
    issue.close();

    assert(
        issue.state()
        == IssueState::Closed
    );

    assert(
        issue.hasLabel("bug")
    );

    ProjectBoard project(
        "Test Project"
    );

    ProjectItem& item =
        project.addItem(
            "Testing task",
            1
        );

    assert(
        project.progress()
        == 0.0
    );

    project.moveItem(
        item.id,
        ProjectStatus::Done
    );

    assert(
        project.progress()
        == 100.0
    );

    const SemanticVersion version =
        SemanticVersion::parse(
            "v1.2.3"
        );

    assert(version.major() == 1);
    assert(version.minor() == 2);
    assert(version.patch() == 3);

    assert(
        version.bumpPatch().toString()
        == "v1.2.4"
    );

    Release release(
        version,
        "Test Release",
        "Testing release behavior.",
        "v1.2.3"
    );

    release.addAsset({
        "test.zip",
        100,
        "application/zip"
    });

    assert(
        release.assets().size()
        == 1
    );

    assert(
        release.validTag()
    );

    cout
        << "All assertions passed.\n";
}


// ============================================================================
// 14. MAIN CASE STUDY
// ============================================================================

int main() {
    try {
        cout << string(80, '=') << "\n";
        cout << "GITHUB REPOSITORY / ISSUE / PROJECT / RELEASE CASE STUDY\n";
        cout << string(80, '=') << "\n";

        /*
         * Step 1:
         * Create the repository model.
         */
        Repository repository(
            "example-owner",
            "asset-management-system",
            "A production-style asset management platform.",
            Visibility::Public,
            "main"
        );

        repository.addTopic("github");
        repository.addTopic("asset-management");
        repository.addTopic("cpp");
        repository.addTopic("project-management");

        cout
            << "\nRepository created: "
            << repository.fullName()
            << "\n";

        cout
            << "Topics: ";

        for (const auto& topic : repository.topics()) {
            cout << topic << " ";
        }

        cout << "\n";

        /*
         * Step 2:
         * Build the integrated workspace.
         */
        EngineeringWorkspace workspace(
            move(repository)
        );

        /*
         * Step 3:
         * Create issues that represent actual engineering work.
         */
        Issue& databaseIssue =
            workspace.createWorkItem(
                "Design asset database",
                "Create normalized tables for assets, locations, owners, and status.",
                1,
                {
                    "feature",
                    "database"
                }
            );

        Issue& apiIssue =
            workspace.createWorkItem(
                "Implement asset API",
                "Create validated endpoints for asset operations.",
                1,
                {
                    "feature",
                    "api"
                }
            );

        Issue& securityIssue =
            workspace.createWorkItem(
                "Audit authentication flow",
                "Review authentication and authorization boundaries.",
                1,
                {
                    "security"
                }
            );

        databaseIssue.assign("developer-a");
        apiIssue.assign("developer-b");
        securityIssue.assign("security-team");

        databaseIssue.setMilestone("v1.0.0");
        apiIssue.setMilestone("v1.0.0");
        securityIssue.setMilestone("v1.1.0");

        apiIssue.addComment(
            "developer-b",
            "Initial API contract has been drafted."
        );

        /*
         * Step 4:
         * Move Project items based on issue relationships.
         *
         * The project stores its own IDs. We locate the item through its
         * linked issue number instead of assuming the IDs are equal.
         */
        for (const auto& [id, item] :
             workspace.project().items()) {

            if (
                item.linkedIssue &&
                *item.linkedIssue
                == databaseIssue.number()
            ) {
                workspace.project().moveItem(
                    id,
                    ProjectStatus::Done
                );
            }

            if (
                item.linkedIssue &&
                *item.linkedIssue
                == apiIssue.number()
            ) {
                workspace.project().moveItem(
                    id,
                    ProjectStatus::InProgress
                );
            }

            if (
                item.linkedIssue &&
                *item.linkedIssue
                == securityIssue.number()
            ) {
                workspace.project().moveItem(
                    id,
                    ProjectStatus::Blocked
                );
            }
        }

        /*
         * Step 5:
         * Create a release and attach build artifacts.
         */
        Release& release =
            workspace.createRelease(
                "v1.0.0",
                "Asset Management Platform 1.0",
                "Initial production release containing the database and core API."
            );

        release.addAsset({
            "asset-platform-v1.0.0-windows.zip",
            9100000,
            "application/zip"
        });

        release.addAsset({
            "asset-platform-v1.0.0-linux.tar.gz",
            8500000,
            "application/gzip"
        });

        /*
         * Step 6:
         * Demonstrate a second release version.
         */
        Release& secondRelease =
            workspace.createRelease(
                "v1.1.0",
                "Asset Management Platform 1.1",
                "Security and authentication improvements."
            );

        secondRelease.addAsset({
            "asset-platform-v1.1.0-linux.tar.gz",
            8700000,
            "application/gzip"
        });

        /*
         * Step 7:
         * Display integrated state.
         */
        workspace.report();

        /*
         * Step 8:
         * Search issues.
         */
        cout << "\n";
        cout << string(80, '=') << "\n";
        cout << "ISSUE SEARCH: API\n";
        cout << string(80, '=') << "\n";

        const auto matches =
            searchIssues(
                workspace.issues(),
                "API"
            );

        for (const auto& match : matches) {
            cout
                << "  "
                << match.get().summary()
                << "\n";
        }

        /*
         * Step 9:
         * Demonstrate automation rules.
         */
        cout << "\n";
        cout << string(80, '=') << "\n";
        cout << "AUTOMATION RULES\n";
        cout << string(80, '=') << "\n";

        AutomationEngine automation;

        automation.addRule(
            "Issue completion",
            "linked issue is closed",
            "move Project item to Done"
        );

        automation.addRule(
            "Release tracking",
            "release is published",
            "update release-related Project items"
        );

        automation.addRule(
            "Security routing",
            "security label is added",
            "route item to security workflow"
        );

        automation.printRules();

        /*
         * Step 10:
         * Validation and tests.
         */
        validationExamples();
        runTests();

        /*
         * Complexity notes:
         *
         * - Issue lookup by number uses unordered_map and is average O(1).
         * - Project item lookup by ID uses map and is O(log n).
         * - Issue search scans all issues and is O(n).
         * - Sorting search results is O(n log n).
         * - Release lookup by version uses map and is O(log n).
         * - Network operations in a real GitHub client are dominated by
         *   network latency, server processing, pagination, and rate limits.
         */
        cout << "\n";
        cout << string(80, '=') << "\n";
        cout << "CASE STUDY COMPLETE\n";
        cout << string(80, '=') << "\n";

        return 0;
    }
    catch (const exception& error) {
        cerr
            << "Fatal error: "
            << error.what()
            << "\n";

        return 1;
    }
}
