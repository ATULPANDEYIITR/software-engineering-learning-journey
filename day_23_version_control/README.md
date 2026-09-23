# Git fundamentals: repositories, commits, and version history

## Topic scope

Git is a distributed version control system used to record changes to files, organize development history, collaborate across branches, and transfer repository history between machines and remote repositories.

This study implementation focuses on three foundational areas:

- Git fundamentals
- repositories
- commits

The implementations also examine the concepts that make these three areas meaningful in practice: the working tree, staging area, snapshots, objects, trees, branches, `HEAD`, commit parents, history graphs, diffs, merging, integrity, and remote-oriented workflows.

The Python program builds an inspectable educational Git model. The JavaScript implementation demonstrates the same domain through JavaScript classes, `Map`, `Buffer`, validation, and executable data processing. The C++ program develops a technical case study around a production configuration repository.

The implementations model important Git behavior for learning. They are not replacements for the actual Git implementation and intentionally omit many production details such as packfiles, the complete Git index format, filesystem-specific behavior, cryptographic SHA-1/SHA-256 implementation, protocol negotiation, hooks, and the full merge machinery.

## Version control

Version control is a system for recording and managing changes to files over time.

Without version control, a project might evolve through manually copied directories such as:

`project-final/`

`project-final-2/`

`project-final-real/`

`project-final-real-new/`

This approach makes it difficult to determine exactly what changed, when a change occurred, why it occurred, and which previous state should be restored.

A version control system provides a structured history.

A useful conceptual model is:

`working state → recorded state → later recorded state → history`

Git makes this history distributed. A normal Git clone contains a local copy of repository history, allowing many operations to be performed without communicating with a server.

## Git terminology

### Repository

A repository is the data structure Git uses to store project history, objects, references, and supporting metadata.

A repository can be created with:

`git init`

An existing repository can be copied with:

`git clone <repository-url>`

A repository normally contains a `.git` directory when using a standard non-bare working repository.

The `.git` directory contains internal information such as object storage, references, configuration, the index, and other metadata.

### Working tree

The working tree is the set of files currently checked out for editing.

For example, a project might contain:

`README.md`

`src/main.py`

`config/settings.json`

When a user edits `src/main.py`, the working tree changes. That change is not automatically a commit.

### Staging area

The staging area, also called the index, represents the content selected for the next commit.

For example:

`git add src/main.py`

stages the current version of that file.

The distinction between the working tree and index is one of the most important Git fundamentals.

A user can modify three files but stage only one. The next commit can therefore contain one selected change rather than every modification currently present in the working directory.

### Commit

A commit is a permanent history object representing a particular project snapshot together with metadata and references to parent commits.

A commit normally contains information such as:

- a tree reference
- zero or more parent references
- author information
- commit message
- other metadata in the actual Git implementation

The Python, JavaScript, and C++ implementations represent these relationships explicitly.

### Branch

A branch is a reference that points to a commit.

The branch itself is not a second physical copy of the entire repository.

If `main` points to commit `A`, and a new commit `B` is created on `main`, the branch reference moves from `A` to `B`.

Conceptually:

`main → B → A`

A second branch can point to the same history:

`feature → A`

After a feature commit:

`feature → C → A`

The two branch names can then identify different tips of related history.

### HEAD

`HEAD` identifies the currently selected point in the repository.

Normally, `HEAD` refers to the current branch, and the branch refers to a commit.

Conceptually:

`HEAD → main → commit`

A detached `HEAD` points directly to a commit rather than to a branch name.

### Parent

A commit normally points to an earlier commit called its parent.

A linear history can therefore be represented as:

`C → B → A`

where `C` is the newest commit.

A merge commit can have two or more parents. This is one reason Git history is naturally modeled as a directed acyclic graph rather than as a simple list.

### Snapshot

A commit represents a project state. This is commonly described as a snapshot.

A simplified snapshot could be:

`README.md → contents`

`src/app.py → contents`

`config.json → contents`

The implementation models this snapshot explicitly.

## The basic Git workflow

A fundamental workflow is:

`git init`

Create or initialize a repository.

`git status`

Inspect the current state.

`git add <file>`

Place selected content into the staging area.

`git commit -m "message"`

Create a commit containing the staged snapshot.

`git log`

Inspect history.

The conceptual sequence is:

`working tree`

↓

`git add`

↓

`index`

↓

`git commit`

↓

`commit`

The important distinction is that `git add` and `git commit` perform different operations.

`git add` prepares content.

`git commit` records the prepared content as repository history.

## Python implementation

The Python program implements an educational repository through the `GitRepository` class.

The repository contains:

- an object database
- a working tree
- an index
- branches
- `HEAD`
- commits
- trees
- blobs

The `Blob` class represents file contents.

The `Tree` class represents a directory-like collection of entries.

The `Commit` class represents a historical snapshot reference and its parent relationships.

### Blob objects

A blob stores file content.

The Python implementation calculates a Git-style object identifier with:

`git_hash("blob", content)`

The hash input includes an object type, content length, separator, and content.

This demonstrates an important property of content-addressable storage: the identifier depends on the content.

If the content changes, the resulting identifier changes.

The educational implementation uses SHA-1 through Python's standard library. Real Git has support for SHA-1 repositories and also supports SHA-256 repositories.

### Trees

A tree connects paths to object identifiers.

For example, a simplified tree can contain:

`README.md → blob-id`

`app.py → blob-id`

The Python `Tree` object serializes its entries deterministically before calculating its identifier.

This illustrates the relationship:

`commit → tree → blobs`

Real Git trees can also represent subdirectories through tree objects and contain file modes and other details.

### Commits

The Python `Commit` class stores:

- `tree_id`
- `parents`
- `author`
- `message`

The first commit in a repository has no parent.

A later commit has one parent in ordinary linear history.

A merge commit can have multiple parents.

The program exposes this through the `parents` tuple.

### Working tree and index

The Python repository maintains:

`working_tree`

and

`index`

as separate dictionaries.

When a file is changed, only the working tree changes.

When the file is staged, the selected working-tree content is copied into the index.

When `commit()` is called, the index becomes the basis for the new snapshot.

This is an important demonstration because it explains why the following sequence matters:

`edit → add → edit`

The second edit is not automatically included in the already-staged version. The file must be staged again if the second edit should enter the next commit.

### Status

The Python `status()` implementation compares:

`HEAD`

against

`index`

and then compares

`index`

against

`working_tree`.

This mirrors the conceptual structure behind `git status`.

Changes between `HEAD` and the index are staged changes.

Changes between the index and working tree are unstaged changes.

### History

The Python `log()` method follows the first parent from the current `HEAD`.

This demonstrates the basic linear history model.

The implementation also provides `ancestors()` and `merge_base()` to reason about a commit graph.

### Diffs

The Python implementation uses `difflib.unified_diff()` to compare text snapshots.

A diff answers a different question from a commit.

A commit answers:

"What project state was recorded?"

A diff answers:

"What changed between two states?"

## JavaScript implementation

The JavaScript implementation models Git through classes and `Map` objects.

It demonstrates how JavaScript can represent a repository as structured application state.

The major classes are:

- `Blob`
- `Tree`
- `Commit`
- `GitRepository`

### JavaScript `Map`

The implementation uses `Map` for:

- repository objects
- branches
- file snapshots

A `Map` is useful because file paths and object identifiers naturally behave as keys.

For example:

`workingTree.set("src/main.js", content)`

associates a path with its current content.

### Buffer

Node.js `Buffer` is used to represent file contents.

This is technically meaningful because repository storage ultimately deals with bytes rather than only JavaScript strings.

The implementation converts textual examples into buffers while retaining readable examples.

### Content hashing

Node's built-in `crypto` module provides the SHA-1 calculation used by the educational object model.

The operation conceptually follows:

`object-id = SHA1(header + content)`

The header identifies the object type and length.

### Repository state

The JavaScript repository keeps:

- `workingTree`
- `index`
- `objects`
- `branches`
- `headBranch`
- `detachedHead`

This makes the relationship between the major Git concepts visible in executable code.

### Branches

`createBranch()` creates a branch reference pointing to a selected commit.

`checkout()` can either:

- select an existing branch, or
- select a commit directly and enter detached `HEAD` state

The implementation demonstrates why a branch is better understood as a reference than as a complete copy of a repository.

### Three-way merge

The JavaScript implementation contains a simplified three-way merge algorithm.

It compares:

- the common base
- our version
- their version

The decision rules are:

If both sides contain the same value, use that value.

If our side is unchanged from the base, use their side.

If their side is unchanged from the base, use our side.

If both sides changed the same path differently, report a conflict.

This is a simplified model. Real Git performs considerably more sophisticated content-level merging.

## C++ case study

The C++ program models a configuration repository used by an engineering team maintaining a production service.

The repository contains configuration such as:

`config/app.conf`

`config/security.conf`

`README.md`

The scenario demonstrates how version control can be applied to a realistic software-engineering workflow.

### Problem being modeled

A configuration repository needs to support:

- reproducible states
- historical records
- isolated development
- reviewable changes
- branch-based work
- conflict detection
- integrity checking

The case study begins with an initial configuration and then evolves through multiple commits.

### Architecture

The repository consists of four major object categories.

#### Blob storage

`Blob` represents file content.

#### Tree storage

`Tree` represents paths and their corresponding blobs.

#### Commit storage

`Commit` represents snapshots and parent relationships.

#### References

The `branches` map associates branch names with commit IDs.

This produces the conceptual architecture:

`branch → commit → tree → blob`

The `HEAD` concept identifies the currently selected branch or commit.

### C++ data structures

The implementation uses:

`std::map`

for deterministic key ordering and simple inspection.

`std::vector`

stores parent commit IDs.

`std::set`

collects unique file paths during status and merge analysis.

`std::queue`

supports breadth-first ancestor traversal.

`std::optional`

represents the difference between an existing file and a missing file.

These choices are appropriate for an educational repository model because they make the state transitions explicit.

### Commit creation

The C++ workflow follows:

1. Write files.
2. Stage selected files.
3. Create a tree.
4. Determine the current parent.
5. Create a commit.
6. Move the current branch reference.
7. Synchronize the working tree with the committed index.

This corresponds conceptually to:

`git add`

followed by

`git commit`

### Branch development

The case study creates:

`main`

and

`feature/security-settings`

The main branch changes the production service port.

The feature branch adds security configuration.

Because the branches originated from a common commit, the history has a shared ancestor.

The repository can identify that common ancestor with `mergeBase()`.

### Three-way merge

The case study compares:

`base`

`main`

`feature`

The algorithm examines each path and determines whether the change can be combined automatically.

A file changed only on one side can generally be taken from that side.

A file unchanged on both sides remains unchanged.

A file changed differently on both sides becomes a conflict.

A conflict does not mean the repository is corrupted. It means the available information is insufficient to choose one of two incompatible changes automatically.

A real Git merge may create conflict markers inside files and records an unresolved merge state until the user resolves and stages the files.

### Conflict example

The conflict case changes:

`settings.txt`

on both branches.

One branch changes:

`timeout=30`

to:

`timeout=60`

The other changes:

`timeout=30`

to:

`timeout=15`

Both changes originate from the same base but produce different results.

The implementation therefore reports the file as a conflict.

This demonstrates why Git cannot always merge two histories without human input.

## Repository objects

A useful conceptual model of Git's object database contains four major object types.

### Blob

Stores file content.

### Tree

Stores directory contents and references to blobs or other trees.

### Commit

References a tree and one or more parent commits.

### Tag

An annotated Git tag is another Git object type that can provide metadata around a referenced object.

The supplied implementations focus on blobs, trees, and commits because these are central to understanding repositories and commits.

## Content-addressable storage

Content-addressable storage identifies an object based on its content.

The conceptual calculation is:

`object identifier = hash(object type + object size + object content)`

This has several important consequences.

Identical content can produce the same object identifier.

Changing content changes its identifier.

A reference can identify an object without depending on a human-readable filename.

Integrity can be checked by recalculating the expected identifier.

The implementations demonstrate this property through `verify_integrity()` in Python, `verifyIntegrity()` in JavaScript, and `verifyIntegrity()` in C++.

## Commit immutability

A commit is treated as immutable.

If the message, tree, author, or parent relationship changes, the serialized representation changes and therefore the identifier changes.

This means a later commit does not modify an earlier commit.

Instead, a new commit is created.

This is a fundamental difference between editing a normal database record and adding a new version to a content-addressed history.

## Commit graph

Git history is a directed acyclic graph.

A simple history:

`C → B → A`

A branch can diverge:

`C → B → A`

`D → B → A`

A merge can produce:

`M → C`

`M → D`

with both `C` and `D` as parents.

The graph structure makes operations such as ancestry checks, merge-base calculation, branch comparison, and history traversal possible.

## Branches versus commits

A branch is not the same thing as a commit.

A commit is an object representing a particular recorded state and its history relationship.

A branch is a reference to a commit.

For example:

`main → abc123`

If a new commit is created:

`main → def456 → abc123`

The older commit still exists.

The branch reference moved.

This distinction is important when understanding why creating branches is inexpensive compared with copying an entire project directory.

## HEAD versus branch

Normally:

`HEAD → main → commit`

When `main` advances, `HEAD` still refers to `main`.

In detached mode:

`HEAD → commit`

There is no branch reference between `HEAD` and the commit.

Detached `HEAD` is useful for inspecting historical states and temporarily experimenting with a particular commit. Work created from detached `HEAD` requires deliberate branch management if it needs a persistent branch name.

## Staging area versus working tree

Consider a project containing:

`app.py`

`config.json`

Suppose both files are edited.

Running:

`git add app.py`

stages only `app.py`.

The next commit can therefore record the selected state of `app.py` without necessarily recording the current `config.json` modification.

This allows developers to construct logically focused commits.

A useful mental model is:

`working tree = what is currently edited`

`index = what is prepared`

`HEAD = what was last committed on the current branch`

## `git status`

`git status` is one of the most important diagnostic commands.

It helps distinguish:

- untracked files
- modified files
- staged changes
- deleted files
- branch information

When Git behavior seems unexpected, checking status before performing another operation is often the most direct way to understand the repository state.

## `git diff`

`git diff`

shows differences between the working tree and the relevant staged state.

`git diff --staged`

shows differences between the staging area and `HEAD`.

This distinction corresponds directly to the three-state model:

`HEAD ↔ index ↔ working tree`

## Commit messages

A commit message should describe the change represented by the commit.

Examples include:

`Add initial project structure`

`Fix configuration validation`

`Add authentication middleware`

`Update production timeout`

A useful commit history should allow another developer to understand what changed without reconstructing the entire project manually.

Commit messages should not claim more than the commit actually contains.

## Small and focused commits

A focused commit generally represents a coherent change.

For example:

`Add password validation`

is easier to inspect than a single commit containing:

- password validation
- unrelated formatting
- database migration
- documentation changes
- renamed directories
- experimental code

The appropriate commit size depends on the project and workflow, but logical cohesion is important.

## Common mistakes

### Treating `git add` as a commit

`git add` stages content. It does not create permanent history.

### Editing after staging

If a file is staged and then edited again, the index may contain an earlier version.

Run `git add` again when the newer state should enter the next commit.

### Assuming a branch is a full copy

A branch is primarily a reference to a commit.

### Working without checking the current branch

Before making important changes, inspect:

`git status`

and confirm the current branch.

### Committing secrets

Passwords, private keys, access tokens, API keys, and other credentials should not be committed to source control.

If a secret is accidentally committed and exposed, simply deleting it in a later commit does not necessarily eliminate it from repository history. Appropriate credential rotation and history-remediation procedures may be necessary.

### Using unsafe repository paths

Applications that process repository paths should validate them carefully. Path traversal such as `../file` can escape an intended repository directory when file operations are performed without proper controls.

The educational implementations reject simple unsafe path patterns.

### Assuming all merges are automatic

Two branches can make incompatible changes to the same content.

A merge conflict is a normal version-control condition, not necessarily a repository failure.

## Edge cases

### Empty repository

A newly initialized repository has no commit until the first successful commit is created.

The first commit therefore has zero parents.

### Empty commit

Real Git supports intentionally empty commits in appropriate situations, but the educational implementations require staged content for simplicity.

This is an intentional modeling decision rather than a complete reproduction of Git.

### File deletion

Deleting a working-tree file does not automatically rewrite history.

The deletion must be represented in the index and recorded in a later commit.

Previous commits continue to contain the earlier version.

### Branch divergence

Two branches can point to commits that share a common ancestor but contain different descendants.

This is the basic condition that makes merging necessary.

### Merge conflict

If both sides modify the same logical content differently relative to the common ancestor, automatic merging may not be able to determine the intended result.

### Detached HEAD

A detached `HEAD` points directly to a commit.

Creating commits in detached mode does not automatically move a named branch.

### Missing objects

A reference to a missing commit represents repository inconsistency.

The integrity checks in the implementations detect this class of problem.

## Error handling

The implementations intentionally validate several operations.

Examples include:

- empty commit messages
- commits with no staged data
- invalid branch names
- missing commits
- invalid repository paths
- missing blobs referenced by trees
- invalid object references
- corrupted content-addressed objects

In production software, errors should be surfaced clearly enough to identify the failed operation without exposing unnecessary sensitive information.

## Performance considerations

Git is designed to handle large repositories efficiently, but the educational implementations are intentionally simpler.

### Hashing

Hashing a file requires processing its content.

For a file of size `n`, content hashing is generally proportional to `O(n)`.

### Snapshot construction

The educational implementations reconstruct snapshots by traversing tree entries.

If there are `F` files in a snapshot, the basic traversal is approximately `O(F)` apart from content-processing costs.

### History traversal

Ancestor discovery uses graph traversal.

For `V` reachable commits and `E` parent relationships, a graph traversal can be described as approximately:

`O(V + E)`

In a normal commit graph, each ordinary commit has one parent, while merge commits may have multiple parents.

### Maps

The C++ implementation uses `std::map`, which provides logarithmic lookup.

A production implementation may use hash-based structures where appropriate.

The JavaScript implementation uses `Map`, whose expected lookup behavior is efficient for typical application workloads.

### Real Git storage

Real Git uses more sophisticated storage mechanisms, including:

- loose objects
- packfiles
- delta compression
- indexes
- efficient object traversal
- filesystem optimizations

The educational programs do not reproduce these mechanisms.

## Security considerations

Git provides integrity properties through content-addressed objects, but Git does not automatically make every development workflow secure.

Important considerations include:

### Secrets

Do not store credentials or private keys in repositories unless a controlled and appropriate mechanism explicitly requires it.

### Repository exposure

A public repository can expose its complete reachable history, not just the latest visible file state.

### History persistence

Deleting a secret from the latest commit does not necessarily remove the secret from every historical object.

### Remote authentication

When using remote repositories, authentication credentials and access tokens should be protected.

### Signed commits

Git supports cryptographic signing of commits and tags. Signing can provide additional assurance about the identity associated with a recorded object, subject to correct key management and verification.

### Integrity versus authenticity

Hashing helps detect changes to content when the expected object identifier is trusted.

A hash alone does not prove who created the object.

Authenticity involves additional mechanisms such as signatures, trusted identities, access controls, and secure transport.

## Git commands corresponding to the implementations

The following commands correspond closely to concepts demonstrated in the programs.

`git init`

Creates a repository.

`git status`

Displays repository state.

`git add file`

Stages a file.

`git add .`

Stages applicable changes under the current directory.

`git commit -m "message"`

Creates a commit.

`git log`

Displays history.

`git show <commit>`

Displays commit information and associated changes.

`git diff`

Displays unstaged differences.

`git diff --staged`

Displays staged differences.

`git branch`

Lists branches.

`git switch -c feature`

Creates and switches to a branch.

`git switch main`

Switches to an existing branch.

`git merge feature`

Attempts to merge another branch into the current branch.

`git restore file`

Restores file content from a Git state.

`git clone <url>`

Creates a local repository from another repository.

`git fetch`

Downloads objects and references from a remote repository without necessarily integrating them into the current branch.

`git pull`

Fetches remote changes and integrates them according to the configured pull behavior.

`git push`

Transfers local commits and references to a remote repository when the operation is permitted.

## Important distinctions

### Git versus GitHub

Git is the version control system.

GitHub is a hosting and collaboration platform that can store Git repositories and provide additional services such as pull requests, issues, Actions, code review, and repository management.

A project can use Git without GitHub.

### Repository versus branch

A repository contains the broader history and object database.

A branch is a reference within that repository.

### Branch versus commit

A commit is an immutable history object.

A branch is a movable reference pointing to a commit.

### Working tree versus index

The working tree contains the currently edited files.

The index contains the selected content prepared for the next commit.

### Commit versus diff

A commit records a project state and its history relationship.

A diff describes differences between states.

### Local repository versus remote repository

A local repository is available on the developer's machine.

A remote is another repository location used for synchronization and collaboration.

## Practical development workflow

A disciplined basic workflow can be represented as:

`git status`

↓

edit files

↓

`git diff`

↓

`git add <selected files>`

↓

`git diff --staged`

↓

`git commit -m "Describe the change"`

↓

`git log`

The exact workflow varies across teams, but the underlying state transitions remain important.

## Implementation limitations

The three programs are educational models.

They do not attempt to implement all of Git.

Important omissions include:

- the complete Git index file format
- real `.git` directory layout
- filesystem permissions and executable modes in full detail
- symbolic links
- submodules
- sparse checkout
- worktrees
- stash internals
- tags in full detail
- reflog persistence
- garbage collection
- packfiles
- delta compression
- SHA-256 repository support
- object negotiation
- Git transport protocols
- authentication
- hooks
- complete merge strategies
- rename detection
- binary merge handling
- Git attributes
- line-ending conversion
- large-file storage mechanisms
- shallow clone semantics
- partial clone mechanisms

These omissions keep the implementations focused on the conceptual foundations of repositories and commits.

## Why the three languages are useful here

Python makes the repository model easy to inspect because dictionaries, dataclasses, exceptions, and standard-library hashing allow the relationships between objects to remain visible.

JavaScript demonstrates the same concepts in a runtime commonly used for application and web development. `Map`, `Buffer`, classes, and the Node.js `crypto` module provide a practical representation of repository state and content processing.

C++ adds a systems-oriented case study. Explicit data structures, object ownership concepts, standard containers, deterministic serialization, graph traversal, validation, and performance considerations make it useful for examining how a version-control model can be structured as a larger technical system.

The three implementations therefore emphasize different aspects while maintaining the same conceptual foundation:

`working tree → index → commit → history graph`

## Core conceptual model

The most important relationships demonstrated by the implementations can be represented as:

`working tree`

`↓`

`index`

`↓`

`tree`

`↓`

`blobs`

and:

`branch`

`↓`

`commit`

`↓`

`parent commit`

A commit connects the snapshot side and history side:

`branch → commit → tree → file contents`

`                 ↓`

`             parent(s)`

Understanding these relationships provides the foundation for more advanced Git behavior such as branching, merging, rebasing, remotes, tags, and repository recovery.
