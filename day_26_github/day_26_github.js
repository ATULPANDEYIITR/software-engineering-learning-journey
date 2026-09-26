/*
 * GitHub: Repositories, Issues, Projects, and Releases
 * =====================================================
 *
 * A self-contained JavaScript learning program covering:
 *   - Git and GitHub concepts
 *   - Repository modeling
 *   - Issues and issue lifecycle
 *   - Labels and milestones
 *   - GitHub Projects concepts
 *   - Releases and semantic versioning
 *   - REST API access with fetch
 *   - Pagination
 *   - Validation
 *   - Error handling
 *   - Search and filtering
 *   - Automation design
 *   - Performance and security
 *
 * Runtime:
 *   Node.js 18+ is recommended because it provides global fetch.
 *
 * Run:
 *   node github-management.js
 *
 * Optional API example:
 *   PowerShell:
 *     $env:GITHUB_TOKEN="your_token"
 *     $env:GITHUB_OWNER="octocat"
 *     $env:GITHUB_REPOSITORY="Hello-World"
 *     node github-management.js
 *
 * The network example is read-oriented and does not automatically mutate
 * repositories.
 */

"use strict";

// ============================================================================
// 1. FUNDAMENTALS
// ============================================================================

function explainFundamentals() {
    console.log("=".repeat(80));
    console.log("1. GITHUB FUNDAMENTALS");
    console.log("=".repeat(80));

    const concepts = {
        Git: "Distributed version control for recording and coordinating changes.",
        GitHub: "A collaboration and hosting platform built around Git repositories.",
        Repository: "A project space containing source code, history, documentation, and metadata.",
        Issue: "A trackable unit of work, bug, request, task, or discussion.",
        Project: "A planning workspace for organizing trackable work.",
        Release: "A published version associated with a Git tag and release notes.",
        Tag: "A Git reference identifying a particular point in repository history.",
        PullRequest: "A proposed change submitted for review and integration.",
        Branch: "An independent line of development in Git.",
        Commit: "A recorded snapshot of changes in Git history."
    };

    for (const [name, description] of Object.entries(concepts)) {
        console.log(`\n${name}`);
        console.log(`  ${description}`);
    }

    console.log("\nKey distinction:");
    console.log("Git manages version history.");
    console.log("GitHub adds collaboration, planning, hosting, automation,");
    console.log("issues, projects, releases, permissions, and repository services.");
}


// ============================================================================
// 2. REPOSITORY
// ============================================================================

class Repository {
    constructor({
        owner,
        name,
        description = "",
        visibility = "public",
        defaultBranch = "main"
    }) {
        this.owner = owner;
        this.name = name;
        this.description = description;
        this.visibility = visibility;
        this.defaultBranch = defaultBranch;
        this.archived = false;
        this.topics = new Set();
        this.stars = 0;
        this.forks = 0;
        this.openIssues = 0;
    }

    get fullName() {
        return `${this.owner}/${this.name}`;
    }

    addTopic(topic) {
        const normalized = String(topic).trim().toLowerCase();

        if (!normalized) {
            throw new Error("Repository topic cannot be empty.");
        }

        this.topics.add(normalized);
    }

    removeTopic(topic) {
        this.topics.delete(String(topic).trim().toLowerCase());
    }

    validate() {
        const errors = [];

        if (!this.owner.trim()) {
            errors.push("Repository owner is required.");
        }

        if (!this.name.trim()) {
            errors.push("Repository name is required.");
        }

        if (!/^[A-Za-z0-9._-]+$/.test(this.name)) {
            errors.push("Repository name contains unsupported characters.");
        }

        if (!this.defaultBranch.trim()) {
            errors.push("Default branch is required.");
        }

        if (this.stars < 0 || this.forks < 0 || this.openIssues < 0) {
            errors.push("Repository counters cannot be negative.");
        }

        return errors;
    }
}

function repositoryDemo() {
    console.log("\n" + "=".repeat(80));
    console.log("2. REPOSITORY MODEL");
    console.log("=".repeat(80));

    const repository = new Repository({
        owner: "example-owner",
        name: "asset-management-system",
        description: "An asset management platform.",
        visibility: "public"
    });

    repository.addTopic("GitHub");
    repository.addTopic("asset-management");
    repository.addTopic("JavaScript");

    console.log(`Full name: ${repository.fullName}`);
    console.log(`Visibility: ${repository.visibility}`);
    console.log(`Default branch: ${repository.defaultBranch}`);
    console.log(`Topics: ${[...repository.topics].join(", ")}`);
    console.log(`Validation errors: ${repository.validate().length}`);
}


// ============================================================================
// 3. ISSUES
// ============================================================================

class Issue {
    constructor(number, title, body = "") {
        if (!String(title).trim()) {
            throw new Error("Issue title cannot be empty.");
        }

        this.number = number;
        this.title = String(title).trim();
        this.body = body;
        this.state = "open";
        this.labels = new Set();
        this.assignees = new Set();
        this.milestone = null;
        this.comments = [];
        this.createdAt = new Date();
    }

    addLabel(label) {
        const normalized = String(label).trim();

        if (!normalized) {
            throw new Error("Issue label cannot be empty.");
        }

        this.labels.add(normalized);
    }

    assign(username) {
        const normalized = String(username).trim();

        if (!normalized) {
            throw new Error("Assignee cannot be empty.");
        }

        this.assignees.add(normalized);
    }

    addComment(author, body) {
        if (!String(author).trim()) {
            throw new Error("Comment author cannot be empty.");
        }

        if (!String(body).trim()) {
            throw new Error("Comment body cannot be empty.");
        }

        this.comments.push({
            author,
            body,
            createdAt: new Date()
        });
    }

    close() {
        this.state = "closed";
    }

    reopen() {
        this.state = "open";
    }

    summary() {
        return [
            `#${this.number} [${this.state}] ${this.title}`,
            `  Labels: ${[...this.labels].join(", ") || "none"}`,
            `  Assignees: ${[...this.assignees].join(", ") || "none"}`,
            `  Milestone: ${this.milestone ?? "none"}`,
            `  Comments: ${this.comments.length}`
        ].join("\n");
    }
}

class IssueTracker {
    constructor() {
        this.issues = new Map();
        this.nextNumber = 1;
    }

    createIssue(title, body = "") {
        const issue = new Issue(this.nextNumber, title, body);
        this.issues.set(issue.number, issue);
        this.nextNumber += 1;
        return issue;
    }

    get(number) {
        const issue = this.issues.get(number);

        if (!issue) {
            throw new Error(`Issue #${number} does not exist.`);
        }

        return issue;
    }

    listIssues({ state = null, label = null } = {}) {
        return [...this.issues.values()]
            .filter(issue => state === null || issue.state === state)
            .filter(issue => label === null || issue.labels.has(label))
            .sort((a, b) => a.number - b.number);
    }
}

function issueDemo() {
    console.log("\n" + "=".repeat(80));
    console.log("3. ISSUES");
    console.log("=".repeat(80));

    const tracker = new IssueTracker();

    const bug = tracker.createIssue(
        "Login fails after password reset",
        "Users receive an error after resetting credentials."
    );

    bug.addLabel("bug");
    bug.addLabel("security");
    bug.assign("developer-a");
    bug.milestone = "v2.0";
    bug.addComment(
        "developer-a",
        "The failure appears to involve an expired session token."
    );

    const feature = tracker.createIssue(
        "Add CSV export",
        "Users should be able to export filtered records."
    );

    feature.addLabel("enhancement");
    feature.assign("developer-b");

    const documentation = tracker.createIssue(
        "Improve installation documentation"
    );

    documentation.addLabel("documentation");
    documentation.close();

    for (const issue of tracker.listIssues()) {
        console.log(issue.summary());
    }

    console.log("\nOpen bugs:");

    for (const issue of tracker.listIssues({
        state: "open",
        label: "bug"
    })) {
        console.log(`  #${issue.number}: ${issue.title}`);
    }
}


// ============================================================================
// 4. ISSUE TEMPLATES
// ============================================================================

function issueTemplateDemo() {
    console.log("\n" + "=".repeat(80));
    console.log("4. ISSUE TEMPLATES");
    console.log("=".repeat(80));

    const bugTemplate = {
        titlePrefix: "[Bug]: ",
        sections: [
            "Description",
            "Steps to reproduce",
            "Expected behavior",
            "Actual behavior",
            "Environment",
            "Logs or screenshots",
            "Additional context"
        ]
    };

    const featureTemplate = {
        titlePrefix: "[Feature]: ",
        sections: [
            "Problem statement",
            "Proposed behavior",
            "Acceptance criteria",
            "Alternatives considered",
            "Additional context"
        ]
    };

    for (const [name, template] of [
        ["Bug template", bugTemplate],
        ["Feature template", featureTemplate]
    ]) {
        console.log(`\n${name}`);
        console.log(`Title prefix: ${template.titlePrefix}`);

        for (const section of template.sections) {
            console.log(`  - ${section}`);
        }
    }
}


// ============================================================================
// 5. PROJECTS
// ============================================================================

const ProjectStatus = Object.freeze({
    TODO: "Todo",
    IN_PROGRESS: "In Progress",
    DONE: "Done",
    BLOCKED: "Blocked"
});

class ProjectItem {
    constructor(id, title, priority = 3, linkedIssue = null) {
        if (!String(title).trim()) {
            throw new Error("Project item title cannot be empty.");
        }

        if (!Number.isInteger(priority) || priority < 1 || priority > 5) {
            throw new Error("Priority must be an integer from 1 to 5.");
        }

        this.id = id;
        this.title = title.trim();
        this.priority = priority;
        this.status = ProjectStatus.TODO;
        this.labels = new Set();
        this.linkedIssue = linkedIssue;
    }
}

class ProjectBoard {
    constructor(name) {
        if (!String(name).trim()) {
            throw new Error("Project name cannot be empty.");
        }

        this.name = name;
        this.items = new Map();
        this.nextId = 1;
    }

    addItem(title, priority = 3, linkedIssue = null) {
        const item = new ProjectItem(
            this.nextId,
            title,
            priority,
            linkedIssue
        );

        this.items.set(item.id, item);
        this.nextId += 1;

        return item;
    }

    moveItem(id, status) {
        if (!Object.values(ProjectStatus).includes(status)) {
            throw new Error(`Unknown project status: ${status}`);
        }

        const item = this.items.get(id);

        if (!item) {
            throw new Error(`Project item ${id} does not exist.`);
        }

        item.status = status;
    }

    itemsByStatus(status) {
        return [...this.items.values()]
            .filter(item => item.status === status);
    }

    progress() {
        if (this.items.size === 0) {
            return 0;
        }

        const completed = this.itemsByStatus(ProjectStatus.DONE).length;

        return completed / this.items.size * 100;
    }

    display() {
        console.log(`\nProject: ${this.name}`);

        for (const status of Object.values(ProjectStatus)) {
            console.log(`\n[${status}]`);

            const items = this.itemsByStatus(status);

            if (items.length === 0) {
                console.log("  -");
            }

            for (const item of items) {
                console.log(
                    `  #${item.id} ${item.title} ` +
                    `(priority=${item.priority})`
                );
            }
        }

        console.log(`\nCompletion: ${this.progress().toFixed(1)}%`);
    }
}

function projectDemo() {
    console.log("\n" + "=".repeat(80));
    console.log("5. GITHUB PROJECTS");
    console.log("=".repeat(80));

    const project = new ProjectBoard("Asset Management Platform");

    const database = project.addItem("Design database schema", 1);
    const api = project.addItem("Implement REST API", 1);
    const dashboard = project.addItem("Build dashboard", 2);
    const testing = project.addItem("Create integration tests", 2);

    project.addItem("Prepare production deployment", 3);

    project.moveItem(database.id, ProjectStatus.DONE);
    project.moveItem(api.id, ProjectStatus.IN_PROGRESS);
    project.moveItem(dashboard.id, ProjectStatus.TODO);
    project.moveItem(testing.id, ProjectStatus.BLOCKED);

    project.display();
}


// ============================================================================
// 6. SEMANTIC VERSIONING
// ============================================================================

class SemanticVersion {
    constructor(major, minor, patch, prerelease = null, build = null) {
        this.major = major;
        this.minor = minor;
        this.patch = patch;
        this.prerelease = prerelease;
        this.build = build;
    }

    static parse(value) {
        const pattern =
            /^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)` +
            `(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?` +
            `(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$/;

        const match = String(value).trim().match(pattern);

        if (!match) {
            throw new Error(`Invalid semantic version: ${value}`);
        }

        return new SemanticVersion(
            Number(match[1]),
            Number(match[2]),
            Number(match[3]),
            match[4] ?? null,
            match[5] ?? null
        );
    }

    toString() {
        let value = `v${this.major}.${this.minor}.${this.patch}`;

        if (this.prerelease) {
            value += `-${this.prerelease}`;
        }

        if (this.build) {
            value += `+${this.build}`;
        }

        return value;
    }

    bumpMajor() {
        return new SemanticVersion(this.major + 1, 0, 0);
    }

    bumpMinor() {
        return new SemanticVersion(this.major, this.minor + 1, 0);
    }

    bumpPatch() {
        return new SemanticVersion(
            this.major,
            this.minor,
            this.patch + 1
        );
    }
}


// ============================================================================
// 7. RELEASES
// ============================================================================

class Release {
    constructor({
        version,
        name,
        body,
        tagName,
        draft = false,
        prerelease = false
    }) {
        this.version = version;
        this.name = name;
        this.body = body;
        this.tagName = tagName;
        this.draft = draft;
        this.prerelease = prerelease;
        this.assets = [];
    }

    addAsset({ name, sizeBytes, contentType }) {
        if (!String(name).trim()) {
            throw new Error("Asset name cannot be empty.");
        }

        if (!Number.isFinite(sizeBytes) || sizeBytes < 0) {
            throw new Error("Asset size must be a non-negative number.");
        }

        if (this.assets.some(asset => asset.name === name)) {
            throw new Error(`Duplicate asset: ${name}`);
        }

        this.assets.push({
            name,
            sizeBytes,
            contentType
        });
    }

    validate() {
        const errors = [];

        if (this.tagName !== this.version.toString()) {
            errors.push("Tag name and version do not match.");
        }

        if (!this.name.trim()) {
            errors.push("Release name cannot be empty.");
        }

        return errors;
    }
}

function releaseDemo() {
    console.log("\n" + "=".repeat(80));
    console.log("6. RELEASES AND SEMANTIC VERSIONING");
    console.log("=".repeat(80));

    const version = SemanticVersion.parse("v1.4.2");

    console.log(`Current: ${version}`);
    console.log(`Patch:  ${version.bumpPatch()}`);
    console.log(`Minor:  ${version.bumpMinor()}`);
    console.log(`Major:  ${version.bumpMajor()}`);

    const release = new Release({
        version: SemanticVersion.parse("v2.0.0"),
        name: "Asset Management Platform 2.0",
        body: "Major production release.",
        tagName: "v2.0.0"
    });

    release.addAsset({
        name: "asset-management-windows-x64.zip",
        sizeBytes: 9100000,
        contentType: "application/zip"
    });

    release.addAsset({
        name: "asset-management-linux-x64.tar.gz",
        sizeBytes: 8500000,
        contentType: "application/gzip"
    });

    console.log(`\nRelease: ${release.name}`);
    console.log(`Tag: ${release.tagName}`);
    console.log(`Validation errors: ${release.validate().length}`);

    for (const asset of release.assets) {
        console.log(
            `  ${asset.name}: ` +
            `${asset.sizeBytes.toLocaleString()} bytes`
        );
    }
}


// ============================================================================
// 8. SEARCH AND FILTERING
// ============================================================================

function filterIssues(
    issues,
    {
        text = null,
        labels = new Set(),
        state = null
    } = {}
) {
    let result = [...issues];

    if (text) {
        const query = text.toLocaleLowerCase();

        result = result.filter(issue =>
            issue.title.toLocaleLowerCase().includes(query) ||
            issue.body.toLocaleLowerCase().includes(query)
        );
    }

    if (labels.size > 0) {
        result = result.filter(issue =>
            [...labels].every(label => issue.labels.has(label))
        );
    }

    if (state) {
        result = result.filter(issue => issue.state === state);
    }

    return result;
}

function searchDemo() {
    console.log("\n" + "=".repeat(80));
    console.log("7. SEARCH AND FILTERING");
    console.log("=".repeat(80));

    const tracker = new IssueTracker();

    const first = tracker.createIssue(
        "CSV export fails with comma-containing filters",
        "CSV parser rejects a filter containing commas."
    );

    first.addLabel("bug");
    first.addLabel("export");

    const second = tracker.createIssue(
        "Add CSV export scheduling",
        "Allow scheduled exports."
    );

    second.addLabel("enhancement");
    second.addLabel("export");

    const third = tracker.createIssue(
        "Improve export documentation",
        "Document CSV behavior."
    );

    third.addLabel("documentation");
    third.addLabel("export");

    const matches = filterIssues(
        tracker.listIssues(),
        {
            text: "CSV",
            labels: new Set(["export"])
        }
    );

    for (const issue of matches) {
        console.log(`#${issue.number}: ${issue.title}`);
    }
}


// ============================================================================
// 9. GITHUB REST API
// ============================================================================

class GitHubApiError extends Error {
    constructor(message, status = null, details = null) {
        super(message);
        this.name = "GitHubApiError";
        this.status = status;
        this.details = details;
    }
}

class GitHubClient {
    constructor({
        token = null,
        timeoutMs = 15000
    } = {}) {
        this.token = token;
        this.timeoutMs = timeoutMs;
        this.baseUrl = "https://api.github.com";
    }

    async request(method, path, {
        query = null,
        body = null
    } = {}) {
        const url = new URL(this.baseUrl + path);

        if (query) {
            for (const [key, value] of Object.entries(query)) {
                if (value !== undefined && value !== null) {
                    url.searchParams.set(key, String(value));
                }
            }
        }

        const headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "github-learning-example"
        };

        if (this.token) {
            headers.Authorization = `Bearer ${this.token}`;
        }

        const controller = new AbortController();
        const timer = setTimeout(
            () => controller.abort(),
            this.timeoutMs
        );

        try {
            const response = await fetch(url, {
                method,
                headers,
                body: body ? JSON.stringify(body) : undefined,
                signal: controller.signal
            });

            const text = await response.text();

            let data = null;

            if (text) {
                try {
                    data = JSON.parse(text);
                } catch {
                    data = text;
                }
            }

            if (!response.ok) {
                const message =
                    typeof data === "object" && data?.message
                        ? data.message
                        : `HTTP ${response.status}`;

                throw new GitHubApiError(
                    message,
                    response.status,
                    data
                );
            }

            return {
                status: response.status,
                headers: response.headers,
                data
            };
        } catch (error) {
            if (error instanceof GitHubApiError) {
                throw error;
            }

            if (error.name === "AbortError") {
                throw new GitHubApiError(
                    `Request timed out after ${this.timeoutMs} ms`
                );
            }

            throw new GitHubApiError(
                `Network request failed: ${error.message}`
            );
        } finally {
            clearTimeout(timer);
        }
    }

    async getRepository(owner, repository) {
        const path =
            `/repos/${encodeURIComponent(owner)}/` +
            `${encodeURIComponent(repository)}`;

        const response = await this.request("GET", path);

        return response.data;
    }

    async listIssues(
        owner,
        repository,
        {
            state = "open",
            perPage = 30,
            page = 1
        } = {}
    ) {
        if (!["open", "closed", "all"].includes(state)) {
            throw new Error("Invalid issue state.");
        }

        const path =
            `/repos/${encodeURIComponent(owner)}/` +
            `${encodeURIComponent(repository)}/issues`;

        const response = await this.request("GET", path, {
            query: {
                state,
                per_page: Math.min(Math.max(perPage, 1), 100),
                page: Math.max(page, 1)
            }
        });

        return response.data;
    }

    async listReleases(
        owner,
        repository,
        {
            perPage = 30,
            page = 1
        } = {}
    ) {
        const path =
            `/repos/${encodeURIComponent(owner)}/` +
            `${encodeURIComponent(repository)}/releases`;

        const response = await this.request("GET", path, {
            query: {
                per_page: Math.min(Math.max(perPage, 1), 100),
                page: Math.max(page, 1)
            }
        });

        return response.data;
    }

    async *paginate(path, {
        perPage = 100,
        maxPages = 10
    } = {}) {
        for (let page = 1; page <= maxPages; page += 1) {
            const response = await this.request("GET", path, {
                query: {
                    per_page: Math.min(Math.max(perPage, 1), 100),
                    page
                }
            });

            if (!Array.isArray(response.data)) {
                throw new GitHubApiError(
                    "Expected a paginated array response."
                );
            }

            if (response.data.length === 0) {
                return;
            }

            for (const item of response.data) {
                yield item;
            }

            if (response.data.length < perPage) {
                return;
            }
        }
    }
}

async function apiDemo() {
    console.log("\n" + "=".repeat(80));
    console.log("8. GITHUB REST API");
    console.log("=".repeat(80));

    const token = process.env.GITHUB_TOKEN;
    const owner = process.env.GITHUB_OWNER;
    const repository = process.env.GITHUB_REPOSITORY;

    if (!owner || !repository) {
        console.log(
            "GITHUB_OWNER and GITHUB_REPOSITORY are not configured."
        );
        console.log("Skipping network requests.");
        return;
    }

    const client = new GitHubClient({ token });

    try {
        const repositoryData =
            await client.getRepository(owner, repository);

        console.log(`Repository: ${repositoryData.full_name}`);
        console.log(`Description: ${repositoryData.description}`);
        console.log(`Visibility: ${repositoryData.visibility}`);
        console.log(
            `Default branch: ${repositoryData.default_branch}`
        );
        console.log(
            `Stars: ${repositoryData.stargazers_count}`
        );

        const issues = await client.listIssues(
            owner,
            repository,
            {
                state: "open",
                perPage: 10
            }
        );

        console.log(`\nReturned records: ${issues.length}`);

        for (const issue of issues) {
            console.log(
                `  #${issue.number}: ${issue.title}`
            );
        }

        const releases = await client.listReleases(
            owner,
            repository,
            {
                perPage: 10
            }
        );

        console.log(`\nReleases: ${releases.length}`);

        for (const release of releases) {
            console.log(
                `  ${release.tag_name}: ${release.name}`
            );
        }
    } catch (error) {
        console.error(
            `API request failed safely: ${error.message}`
        );
    }
}


// ============================================================================
// 10. ASYNCHRONOUS RETRY WITH EXPONENTIAL BACKOFF
// ============================================================================

function sleep(milliseconds) {
    return new Promise(resolve => {
        setTimeout(resolve, milliseconds);
    });
}

async function retryWithBackoff(
    operation,
    {
        attempts = 3,
        baseDelayMs = 500,
        shouldRetry = () => true
    } = {}
) {
    let lastError;

    for (let attempt = 1; attempt <= attempts; attempt += 1) {
        try {
            return await operation(attempt);
        } catch (error) {
            lastError = error;

            if (
                attempt === attempts ||
                !shouldRetry(error)
            ) {
                throw error;
            }

            const delay =
                baseDelayMs * (2 ** (attempt - 1));

            await sleep(delay);
        }
    }

    throw lastError;
}

async function retryDemo() {
    console.log("\n" + "=".repeat(80));
    console.log("9. RETRY AND BACKOFF");
    console.log("=".repeat(80));

    let failures = 0;

    const result = await retryWithBackoff(
        async () => {
            failures += 1;

            if (failures < 2) {
                throw new Error("Simulated transient failure.");
            }

            return "Operation succeeded.";
        },
        {
            attempts: 3,
            baseDelayMs: 100
        }
    );

    console.log(result);
}


// ============================================================================
// 11. SECURITY
// ============================================================================

function securityDemo() {
    console.log("\n" + "=".repeat(80));
    console.log("10. SECURITY");
    console.log("=".repeat(80));

    const rules = [
        "Never hard-code access tokens.",
        "Use environment variables or a secure secret store.",
        "Do not print tokens in logs.",
        "Use least privilege.",
        "Review repository visibility before publication.",
        "Do not store passwords or private keys in issues.",
        "Review GitHub Actions permissions.",
        "Treat pull-request automation as a security boundary.",
        "Rotate exposed credentials.",
        "Avoid blindly executing untrusted repository content."
    ];

    rules.forEach((rule, index) => {
        console.log(`${index + 1}. ${rule}`);
    });
}


// ============================================================================
// 12. PERFORMANCE
// ============================================================================

function performanceDemo() {
    console.log("\n" + "=".repeat(80));
    console.log("11. PERFORMANCE");
    console.log("=".repeat(80));

    const observations = [
        ["Map lookup", "Average O(1)", "Useful for issue IDs and project IDs."],
        ["Filtering", "O(n)", "Inspect each candidate once."],
        ["Sorting", "Typically O(n log n)", "Useful for ordered issue views."],
        ["Set membership", "Average O(1)", "Useful for labels."],
        ["Network request", "External latency", "Usually dominates local computation."],
        ["Pagination", "Multiple requests", "Controls response size and memory usage."]
    ];

    console.log(
        `${"Operation".padEnd(20)}${"Complexity".padEnd(18)}Reason`
    );

    for (const [operation, complexity, reason] of observations) {
        console.log(
            `${operation.padEnd(20)}` +
            `${complexity.padEnd(18)}` +
            reason
        );
    }
}


// ============================================================================
// 13. AUTOMATION MODEL
// ============================================================================

class AutomationRule {
    constructor(name, trigger, action) {
        if (!String(name).trim()) {
            throw new Error("Automation rule name is required.");
        }

        this.name = name;
        this.trigger = trigger;
        this.action = action;
    }

    describe() {
        return `WHEN ${this.trigger} THEN ${this.action}`;
    }
}

class AutomationEngine {
    constructor() {
        this.rules = [];
    }

    addRule(name, trigger, action) {
        this.rules.push(
            new AutomationRule(name, trigger, action)
        );
    }

    display() {
        for (const rule of this.rules) {
            console.log(
                `${rule.name}: ${rule.describe()}`
            );
        }
    }
}

function automationDemo() {
    console.log("\n" + "=".repeat(80));
    console.log("12. AUTOMATION");
    console.log("=".repeat(80));

    const engine = new AutomationEngine();

    engine.addRule(
        "Issue completion",
        "linked issue is closed",
        "move Project item to Done"
    );

    engine.addRule(
        "Release tracking",
        "release is published",
        "update release-related planning items"
    );

    engine.addRule(
        "Security routing",
        "security label is added",
        "route item to security workflow"
    );

    engine.display();
}


// ============================================================================
// 14. INTEGRATED CASE STUDY
// ============================================================================

class EngineeringWorkspace {
    constructor(repository) {
        this.repository = repository;
        this.issueTracker = new IssueTracker();
        this.project = new ProjectBoard(
            `${repository.name} Delivery Board`
        );
        this.releases = new Map();
    }

    createWorkItem({
        title,
        body,
        priority,
        release,
        labels
    }) {
        const issue = this.issueTracker.createIssue(title, body);

        for (const label of labels) {
            issue.addLabel(label);
        }

        const projectItem = this.project.addItem(
            title,
            priority,
            issue.number
        );

        return {
            issue,
            projectItem,
            release
        };
    }

    addRelease(versionText, name, body) {
        const version =
            SemanticVersion.parse(versionText);

        const release = new Release({
            version,
            name,
            body,
            tagName: version.toString()
        });

        this.releases.set(
            version.toString(),
            release
        );

        return release;
    }

    report() {
        console.log("\n" + "=".repeat(80));
        console.log("13. INTEGRATED CASE STUDY");
        console.log("=".repeat(80));

        console.log(
            `Repository: ${this.repository.fullName}`
        );

        console.log("\nIssues:");

        for (const issue of this.issueTracker.listIssues()) {
            console.log(
                `  #${issue.number} ` +
                `[${issue.state}] ${issue.title}`
            );
        }

        this.project.display();

        console.log("\nReleases:");

        for (const [version, release] of this.releases) {
            console.log(
                `  ${version}: ${release.name}`
            );
        }
    }
}

function integratedCaseStudy() {
    const repository = new Repository({
        owner: "example-owner",
        name: "asset-management-system",
        description: "Asset management platform."
    });

    const workspace =
        new EngineeringWorkspace(repository);

    const database = workspace.createWorkItem({
        title: "Design asset database",
        body: "Create normalized asset tables.",
        priority: 1,
        release: "v1.0.0",
        labels: new Set(["feature", "database"])
    });

    const api = workspace.createWorkItem({
        title: "Implement asset API",
        body: "Create validated asset endpoints.",
        priority: 1,
        release: "v1.0.0",
        labels: new Set(["feature", "api"])
    });

    const security = workspace.createWorkItem({
        title: "Audit authentication flow",
        body: "Review authentication and authorization.",
        priority: 1,
        release: "v1.1.0",
        labels: new Set(["security"])
    });

    workspace.project.moveItem(
        database.projectItem.id,
        ProjectStatus.DONE
    );

    workspace.project.moveItem(
        api.projectItem.id,
        ProjectStatus.IN_PROGRESS
    );

    workspace.project.moveItem(
        security.projectItem.id,
        ProjectStatus.BLOCKED
    );

    const release = workspace.addRelease(
        "v1.0.0",
        "Asset Management Platform 1.0",
        "Initial production release."
    );

    release.addAsset({
        name: "asset-platform-v1.0.0.zip",
        sizeBytes: 12500000,
        contentType: "application/zip"
    });

    workspace.report();
}


// ============================================================================
// 15. TESTS
// ============================================================================

function runTests() {
    console.log("\n" + "=".repeat(80));
    console.log("14. AUTOMATED TESTS");
    console.log("=".repeat(80));

    const repository = new Repository({
        owner: "test-owner",
        name: "test-repository"
    });

    console.assert(
        repository.fullName === "test-owner/test-repository"
    );

    repository.addTopic("JavaScript");

    console.assert(
        repository.topics.has("javascript")
    );

    const tracker = new IssueTracker();

    const issue = tracker.createIssue(
        "Testing issue"
    );

    issue.addLabel("bug");
    issue.assign("tester");
    issue.close();

    console.assert(issue.state === "closed");
    console.assert(issue.labels.has("bug"));
    console.assert(issue.assignees.has("tester"));

    const project = new ProjectBoard("Test Project");
    const item = project.addItem("Testing task", 1);

    console.assert(project.progress() === 0);

    project.moveItem(
        item.id,
        ProjectStatus.DONE
    );

    console.assert(project.progress() === 100);

    const version =
        SemanticVersion.parse("v1.2.3");

    console.assert(version.major === 1);
    console.assert(version.minor === 2);
    console.assert(version.patch === 3);
    console.assert(
        version.bumpPatch().toString() === "v1.2.4"
    );

    console.log("All built-in tests passed.");
}


// ============================================================================
// 16. COMPARISON
// ============================================================================

function comparisonDemo() {
    console.log("\n" + "=".repeat(80));
    console.log("15. GIT VS GITHUB FEATURES");
    console.log("=".repeat(80));

    const rows = [
        ["Git", "Version history", "Commits, branches, merges, tags"],
        ["Repository", "Project hosting", "Code, documentation, settings"],
        ["Issue", "Work tracking", "Bug, feature, task, discussion"],
        ["Project", "Planning", "Views, fields, status, workflow"],
        ["Release", "Published version", "Tag, notes, downloadable assets"],
        ["Pull request", "Code review", "Diff, review, checks, merge"],
        ["Tag", "History marker", "Version or significant commit"]
    ];

    console.log(
        `${"Concept".padEnd(20)}` +
        `${"Purpose".padEnd(22)}` +
        "Examples"
    );

    for (const [concept, purpose, examples] of rows) {
        console.log(
            `${concept.padEnd(20)}` +
            `${purpose.padEnd(22)}` +
            examples
        );
    }
}


// ============================================================================
// 17. COMMON MISTAKES
// ============================================================================

function commonMistakesDemo() {
    console.log("\n" + "=".repeat(80));
    console.log("16. COMMON MISTAKES");
    console.log("=".repeat(80));

    const mistakes = [
        [
            "Unclear issue titles",
            "Use precise titles describing the actual problem or request."
        ],
        [
            "Too many labels",
            "Use a small, understandable taxonomy."
        ],
        [
            "Secrets committed to repositories",
            "Use secure secret-management mechanisms."
        ],
        [
            "Releases without meaningful tags",
            "Maintain a consistent versioning strategy."
        ],
        [
            "Ignoring API pagination",
            "Design API clients around paginated responses."
        ],
        [
            "No request timeout",
            "Abort network operations after a bounded period."
        ],
        [
            "Blind retries",
            "Retry only appropriate transient failures."
        ],
        [
            "Project data disconnected from work",
            "Link planning items to the work they represent."
        ]
    ];

    for (const [mistake, correction] of mistakes) {
        console.log(`\nMistake: ${mistake}`);
        console.log(`Better practice: ${correction}`);
    }
}


// ============================================================================
// 18. MAIN
// ============================================================================

async function runCompleteLesson() {
    explainFundamentals();
    repositoryDemo();
    issueDemo();
    issueTemplateDemo();
    projectDemo();
    releaseDemo();
    searchDemo();
    await apiDemo();
    await retryDemo();
    securityDemo();
    performanceDemo();
    automationDemo();
    integratedCaseStudy();
    runTests();
    comparisonDemo();
    commonMistakesDemo();
}

async function main() {
    const argument = process.argv[2];

    if (argument === "--tests") {
        runTests();
        return;
    }

    await runCompleteLesson();
}

main().catch(error => {
    console.error(
        `Fatal error: ${error.name}: ${error.message}`
    );
    process.exitCode = 1;
});
