#!/usr/bin/env node

/**
 * Software Engineering Project: Build a Small CLI Application with Git
 *
 * This file implements a self-contained Node.js command-line application
 * that manages development tasks inside Git repositories.
 *
 * Examples:
 *   node git-project-cli.js init demo
 *   node git-project-cli.js add-task demo "Implement authentication"
 *   node git-project-cli.js list-tasks demo
 *   node git-project-cli.js complete-task demo 1
 *   node git-project-cli.js status demo
 *   node git-project-cli.js commit demo "Add authentication task"
 *   node git-project-cli.js log demo
 *   node git-project-cli.js branch demo feature-auth
 *   node git-project-cli.js test
 */

"use strict";

const fs = require("fs");
const path = require("path");
const os = require("os");
const { execFileSync } = require("child_process");
const assert = require("assert");

const METADATA_FILE = ".project.json";
const TASKS_FILE = "tasks.json";
const README_FILE = "README.md";
const VERSION = "1.0.0";


function timestamp() {
    return new Date().toISOString();
}


function printError(message) {
    process.stderr.write(`Error: ${message}\n`);
}


/*
 * Git commands are executed with execFileSync rather than a shell command
 * string. This keeps arguments separated and avoids shell interpretation.
 */
function runGit(projectDirectory, args, options = {}) {
    try {
        return execFileSync("git", args, {
            cwd: projectDirectory,
            encoding: "utf8",
            stdio: ["ignore", "pipe", "pipe"],
            ...options
        }).trimEnd();
    } catch (error) {
        const stderr = error.stderr
            ? String(error.stderr).trim()
            : "";

        const detail = stderr || error.message;

        throw new Error(
            `Git command failed: git ${args.join(" ")}\n${detail}`
        );
    }
}


function writeJson(filePath, value) {
    fs.writeFileSync(
        filePath,
        `${JSON.stringify(value, null, 2)}\n`,
        "utf8"
    );
}


function readJson(filePath, defaultValue) {
    if (!fs.existsSync(filePath)) {
        return defaultValue;
    }

    try {
        return JSON.parse(fs.readFileSync(filePath, "utf8"));
    } catch (error) {
        throw new Error(
            `Invalid JSON in ${filePath}: ${error.message}`
        );
    }
}


function ensureDirectory(directory) {
    fs.mkdirSync(directory, { recursive: true });
}


function validateProjectName(projectName) {
    if (!projectName || !projectName.trim()) {
        throw new Error("Project name cannot be empty.");
    }

    if (projectName.length > 100) {
        throw new Error("Project name cannot exceed 100 characters.");
    }

    if (/[<>:"/\\|?*\x00-\x1F]/.test(projectName)) {
        throw new Error("Project name contains invalid path characters.");
    }
}


function validateBranchName(name) {
    if (!name || !name.trim()) {
        throw new Error("Branch name cannot be empty.");
    }

    if (!/^[A-Za-z0-9_/-]+$/.test(name)) {
        throw new Error(
            "Branch name may contain only letters, numbers, '-', '_' and '/'."
        );
    }

    if (name.startsWith("/") || name.endsWith("/")) {
        throw new Error("Branch name cannot start or end with '/'.");
    }
}


class Project {
    constructor(directory) {
        this.directory = path.resolve(directory);
        this.metadataPath = path.join(this.directory, METADATA_FILE);
        this.tasksPath = path.join(this.directory, TASKS_FILE);
        this.readmePath = path.join(this.directory, README_FILE);
    }

    exists() {
        return (
            fs.existsSync(this.directory) &&
            fs.existsSync(this.metadataPath)
        );
    }

    metadata() {
        if (!this.exists()) {
            throw new Error(`Not a managed project: ${this.directory}`);
        }

        const data = readJson(this.metadataPath, {});

        return {
            name: String(data.name),
            createdAt: String(data.createdAt),
            version: String(data.version || VERSION)
        };
    }

    tasks() {
        const data = readJson(this.tasksPath, []);

        if (!Array.isArray(data)) {
            throw new Error("tasks.json must contain an array.");
        }

        return data;
    }

    saveTasks(tasks) {
        writeJson(this.tasksPath, tasks);
    }
}


function createProject(directory) {
    const absoluteDirectory = path.resolve(directory);

    if (fs.existsSync(absoluteDirectory)) {
        const entries = fs.readdirSync(absoluteDirectory);

        if (entries.length > 0) {
            throw new Error(
                "Project directory already exists and is not empty."
            );
        }
    } else {
        ensureDirectory(absoluteDirectory);
    }

    const projectName = path.basename(absoluteDirectory);
    validateProjectName(projectName);

    const project = new Project(absoluteDirectory);

    writeJson(project.metadataPath, {
        name: projectName,
        createdAt: timestamp(),
        version: VERSION
    });

    project.saveTasks([]);

    fs.writeFileSync(
        project.readmePath,
        `# ${projectName}\n\n` +
        "This project is managed by a Git-based CLI application.\n\n" +
        "## Development\n\n" +
        "Use tasks to organize work and Git to record project history.\n",
        "utf8"
    );

    runGit(absoluteDirectory, ["init"]);

    return project;
}


function loadProject(directory) {
    const project = new Project(directory);

    if (!project.exists()) {
        throw new Error(
            `${directory} is not a valid managed project.`
        );
    }

    const gitDirectory = path.join(project.directory, ".git");

    if (!fs.existsSync(gitDirectory)) {
        throw new Error("Project does not contain a Git repository.");
    }

    return project;
}


function addTask(project, title) {
    const cleanTitle = title.trim();

    if (!cleanTitle) {
        throw new Error("Task title cannot be empty.");
    }

    if (cleanTitle.length > 200) {
        throw new Error("Task title cannot exceed 200 characters.");
    }

    const tasks = project.tasks();

    const nextId = tasks.reduce(
        (highest, task) => Math.max(highest, Number(task.id)),
        0
    ) + 1;

    const task = {
        id: nextId,
        title: cleanTitle,
        completed: false,
        createdAt: timestamp()
    };

    tasks.push(task);
    project.saveTasks(tasks);

    return task;
}


function completeTask(project, id) {
    const tasks = project.tasks();
    const task = tasks.find(item => Number(item.id) === id);

    if (!task) {
        throw new Error(`Task ${id} does not exist.`);
    }

    task.completed = true;
    project.saveTasks(tasks);

    return task;
}


function removeTask(project, id) {
    const tasks = project.tasks();
    const filtered = tasks.filter(item => Number(item.id) !== id);

    if (filtered.length === tasks.length) {
        throw new Error(`Task ${id} does not exist.`);
    }

    project.saveTasks(filtered);
}


function displayTasks(project) {
    const tasks = project.tasks();

    if (tasks.length === 0) {
        console.log("No tasks.");
        return;
    }

    for (const task of tasks) {
        const marker = task.completed ? "x" : " ";
        console.log(`[${marker}] ${task.id}: ${task.title}`);
    }
}


function gitStatus(project) {
    return runGit(project.directory, [
        "status",
        "--short",
        "--branch"
    ]);
}


function gitCommit(project, message) {
    if (!message || !message.trim()) {
        throw new Error("Commit message cannot be empty.");
    }

    runGit(project.directory, ["add", "."]);

    return runGit(project.directory, [
        "commit",
        "-m",
        message
    ]);
}


function gitLog(project, limit = 10) {
    if (!Number.isInteger(limit) || limit < 1) {
        throw new Error("Log limit must be a positive integer.");
    }

    return runGit(project.directory, [
        "log",
        `-${limit}`,
        "--date=short",
        "--pretty=format:%h | %ad | %an | %s"
    ]);
}


function createBranch(project, branchName) {
    validateBranchName(branchName);

    return runGit(project.directory, [
        "switch",
        "-c",
        branchName
    ]);
}


function currentBranch(project) {
    return runGit(project.directory, [
        "branch",
        "--show-current"
    ]);
}


function showDiff(project) {
    return runGit(project.directory, ["diff"]);
}


function printHelp() {
    console.log(`
${path.basename(process.argv[1])} - Git-backed project CLI

Commands:
  init <directory>
  add-task <project> <title>
  list-tasks <project>
  complete-task <project> <id>
  remove-task <project> <id>
  status <project>
  commit <project> <message>
  log <project> [limit]
  branch <project> <name>
  diff <project>
  test

Examples:
  node git-project-cli.js init demo
  node git-project-cli.js add-task demo "Write unit tests"
  node git-project-cli.js status demo
  node git-project-cli.js commit demo "Add initial task"
`);
}


function runTests() {
    /*
     * A temporary directory makes tests independent from the developer's
     * real projects. This is an important isolation principle in testing.
     */
    const temporaryDirectory = fs.mkdtempSync(
        path.join(os.tmpdir(), "git-project-cli-")
    );

    try {
        const projectPath = path.join(temporaryDirectory, "demo");
        const project = createProject(projectPath);

        assert.strictEqual(project.exists(), true);
        assert.strictEqual(fs.existsSync(path.join(projectPath, ".git")), true);

        const task = addTask(project, "Write tests");
        assert.strictEqual(task.id, 1);
        assert.strictEqual(task.completed, false);

        const completed = completeTask(project, 1);
        assert.strictEqual(completed.completed, true);

        addTask(project, "Review Git history");
        assert.strictEqual(project.tasks().length, 2);

        removeTask(project, 1);
        assert.strictEqual(project.tasks().length, 1);

        console.log("All JavaScript tests passed.");
    } finally {
        fs.rmSync(temporaryDirectory, {
            recursive: true,
            force: true
        });
    }
}


function main() {
    const args = process.argv.slice(2);

    if (args.length === 0 || args[0] === "help" || args[0] === "--help") {
        printHelp();
        return 0;
    }

    const command = args[0];

    try {
        switch (command) {
            case "init": {
                if (!args[1]) {
                    throw new Error("Usage: init <directory>");
                }

                const project = createProject(args[1]);
                console.log(`Project created: ${project.directory}`);
                console.log("Git repository initialized.");
                return 0;
            }

            case "add-task": {
                if (!args[1] || args.length < 3) {
                    throw new Error(
                        "Usage: add-task <project> <title>"
                    );
                }

                const project = loadProject(args[1]);
                const title = args.slice(2).join(" ");
                const task = addTask(project, title);

                console.log(`Added task ${task.id}: ${task.title}`);
                return 0;
            }

            case "list-tasks": {
                if (!args[1]) {
                    throw new Error("Usage: list-tasks <project>");
                }

                displayTasks(loadProject(args[1]));
                return 0;
            }

            case "complete-task": {
                if (!args[1] || !args[2]) {
                    throw new Error(
                        "Usage: complete-task <project> <id>"
                    );
                }

                const project = loadProject(args[1]);
                const id = Number(args[2]);

                if (!Number.isInteger(id) || id < 1) {
                    throw new Error("Task ID must be a positive integer.");
                }

                const task = completeTask(project, id);
                console.log(`Completed task ${task.id}: ${task.title}`);
                return 0;
            }

            case "remove-task": {
                if (!args[1] || !args[2]) {
                    throw new Error(
                        "Usage: remove-task <project> <id>"
                    );
                }

                const project = loadProject(args[1]);
                const id = Number(args[2]);

                if (!Number.isInteger(id) || id < 1) {
                    throw new Error("Task ID must be a positive integer.");
                }

                removeTask(project, id);
                console.log(`Removed task ${id}.`);
                return 0;
            }

            case "status": {
                if (!args[1]) {
                    throw new Error("Usage: status <project>");
                }

                console.log(gitStatus(loadProject(args[1])));
                return 0;
            }

            case "commit": {
                if (!args[1] || args.length < 3) {
                    throw new Error(
                        "Usage: commit <project> <message>"
                    );
                }

                const project = loadProject(args[1]);
                const message = args.slice(2).join(" ");

                console.log(gitCommit(project, message));
                return 0;
            }

            case "log": {
                if (!args[1]) {
                    throw new Error("Usage: log <project> [limit]");
                }

                const project = loadProject(args[1]);
                const limit = args[2] ? Number(args[2]) : 10;

                console.log(gitLog(project, limit));
                return 0;
            }

            case "branch": {
                if (!args[1] || !args[2]) {
                    throw new Error(
                        "Usage: branch <project> <name>"
                    );
                }

                const project = loadProject(args[1]);
                createBranch(project, args[2]);

                console.log(`Current branch: ${currentBranch(project)}`);
                return 0;
            }

            case "diff": {
                if (!args[1]) {
                    throw new Error("Usage: diff <project>");
                }

                const output = showDiff(loadProject(args[1]));
                console.log(output || "No unstaged changes.");
                return 0;
            }

            case "test":
                runTests();
                return 0;

            default:
                throw new Error(`Unknown command: ${command}`);
        }
    } catch (error) {
        printError(error.message);
        return 1;
    }
}


process.exitCode = main();
