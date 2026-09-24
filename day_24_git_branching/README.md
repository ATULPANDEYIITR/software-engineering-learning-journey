# Git branching: branches, merge, rebase, conflicts

## Introduction

Git branching is the mechanism used to maintain multiple lines of development inside one repository. A branch is a named reference to a commit. The branch itself is not a second copy of the project. It points to a position in Git's commit graph and normally moves forward when new commits are created.

The three implementations in this repository approach Git branching from different perspectives:

- The Python script operates on a real temporary Git repository and executes actual Git commands.
- The JavaScript file performs similar practical operations through Node.js and the Git executable, with emphasis on scripting and automation.
- The C++ program builds an in-memory repository model that explains the underlying data structures and algorithms without requiring Git itself.

The central concepts are branch creation, branch switching, commit graphs, fast-forward merges, three-way merges, merge conflicts, rebase, rebase conflicts, cherry-pick, detached HEAD, remote-tracking branches, reflog, worktrees, tags, recovery operations, and production branching practices.

## Git's underlying model

Git is fundamentally a content-addressed version-control system organized around objects and references.

Important objects include:

- **Blob**: stores file content.
- **Tree**: represents a directory-like collection of paths and references to blobs or other trees.
- **Commit**: records a project state together with metadata and one or more parent commits.
- **Tag**: a reference to a particular Git object, commonly used to identify releases.
- **Reference**: a named pointer to another object, commonly a commit.

A branch is a reference. For example, a conceptual repository may contain:

    A -- B -- C
              ^
              main

If a feature branch is created at commit C:

    A -- B -- C
              ^\
              | \
              | feature
              main

Both names initially point to the same commit. When a commit is created on `feature`, the feature reference moves:

    A -- B -- C -- D
              ^    ^
              |    feature
              main

The branch names do not contain the commits. They identify positions in the existing commit graph.

## HEAD

`HEAD` identifies the currently checked-out location.

In normal branch operation:

    HEAD -> main -> commit C

When the user switches to another branch:

    HEAD -> feature -> commit D

HEAD therefore provides an indirect path to the current commit.

A detached HEAD has a different structure:

    HEAD -> commit C

There is no branch name between HEAD and the commit. Detached HEAD is useful for inspecting historical states, testing a particular revision, or temporarily experimenting with an old commit.

If meaningful work is created in detached HEAD state, a branch should be created when that work needs a permanent named reference.

## Commit identity

A commit is not simply a message attached to a file.

Conceptually, a commit includes information such as:

- parent commit or commits
- project tree
- author
- committer
- timestamps
- commit message
- other metadata

The commit identifier depends on the commit object and its contents.

This explains an important property of rebase. If a commit originally has:

    A -> B -> C

and C is recreated with a different parent:

    A -> X -> C'

then C' is a different commit object and normally has a different identifier.

## Branch creation

A typical branch creation command is:

    git branch feature/login

To create and immediately switch to the branch:

    git switch -c feature/login

The older `git checkout -b feature/login` syntax performs a similar branch-oriented operation.

Modern Git separates branch switching from many file-restoration operations through `git switch` and `git restore`, making the intent of commands clearer.

## Switching branches

The modern command is:

    git switch main

or:

    git switch feature/login

Before switching branches, inspect the current repository state:

    git status
    git branch --show-current

Git may refuse a switch when local modifications would be overwritten by files from the target branch.

This protects uncommitted work from accidental replacement.

## Branch naming

Useful branch names communicate intent.

Examples include:

- `feature/payment-validation`
- `feature/reporting`
- `bugfix/session-timeout`
- `hotfix/security-patch`
- `release/2.0`
- `experiment/index-optimization`

A branch naming convention should be consistent within a project.

The branch name does not affect the underlying commits. It is primarily an organizational reference.

## Branch deletion

A merged local branch can normally be removed with:

    git branch -d feature/login

The `-d` option performs a safety check.

The stronger form is:

    git branch -D feature/login

`-D` can remove a branch even when Git considers it unmerged.

A branch should not be force-deleted casually because its commits may still be needed.

## Fast-forward merge

Suppose the history is:

    A -- B -- C
              ^
              main
              ^
              feature

After feature receives D:

    A -- B -- C -- D
              ^    ^
              |    feature
              main

If main has not changed, merging feature into main can simply move main from C to D:

    A -- B -- C -- D
                   ^
                 main
                 feature

This is a **fast-forward merge**.

The command is:

    git switch main
    git merge feature

No merge commit is necessary because the target branch is already an ancestor of the source branch.

## Three-way merge

Consider a divergent history:

    A -- B -- C -- M
         \
          D -- E -- F

One branch contains M and another contains F.

Git identifies a common ancestor, often B, and compares:

- the base version
- the current branch version
- the incoming branch version

This is called a **three-way merge**.

If Git can combine the changes safely, it creates a merge result.

A merge commit can have two parents:

    M
    / \
   C   F
    \ /
     B

The exact graph depends on the complete history, but the important property is that a merge commit records multiple parent relationships.

## `--no-ff`

The command:

    git merge --no-ff feature/login

requests a merge commit even when Git could perform a fast-forward.

This can preserve an explicit feature integration point.

The trade-off is that the history contains additional merge commits. Whether this is desirable depends on repository policy and the team's history-management requirements.

## Merge conflicts

A merge conflict occurs when Git cannot determine a safe combined result.

A common example is:

Base:

    timeout=30

Feature branch:

    timeout=60

Main branch:

    timeout=15

Both branches changed the same logical content in incompatible ways.

Git may produce conflict markers such as:

    <<<<<<< HEAD
    timeout=15
    =======
    timeout=60
    >>>>>>> feature/config

The exact markers identify the current and incoming sides.

A conflict is not merely a Git error. It means human or higher-level application knowledge is required to decide what the final state should be.

## Conflict resolution workflow

A practical merge-conflict workflow is:

    git status

Inspect the conflicted files.

Edit them and remove all conflict markers.

Run tests and other validation.

Inspect the result:

    git diff
    git diff --check

Stage resolved files:

    git add config.txt

Complete the merge:

    git commit

Modern Git may also provide merge continuation commands depending on the operation and configuration.

If the merge should be abandoned:

    git merge --abort

The most important part of conflict resolution is not selecting a side mechanically. The resulting application behavior must be correct.

## Rebase

Rebase changes the base of a series of commits.

Suppose:

    A -- B -- C
         \
          D -- E

The feature branch contains D and E, while the main branch contains C.

Rebasing the feature branch onto C conceptually produces:

    A -- B -- C -- D' -- E'

D' and E' contain the changes from D and E, but their parent relationships have changed.

The original D and E are not simply moved. Their changes are replayed into new commits.

A typical command is:

    git switch feature
    git rebase main

The resulting history can be more linear.

## Why rebase changes commit IDs

Commit identifiers depend on commit data and parent relationships.

Original:

    B -> D -> E

After rebase:

    C -> D' -> E'

D' has C as its parent rather than B.

Because the parent relationship is different, D' is normally a different commit from D. The same applies to E and E'.

This is the technical reason rewriting history can affect collaborators.

## Rebase conflict

Rebase can also produce conflicts.

A typical workflow is:

    git rebase main

If a conflict occurs:

    git status

Resolve the affected files.

Stage the resolutions:

    git add <file>

Continue:

    git rebase --continue

If the operation should be abandoned:

    git rebase --abort

The key distinction is that a merge conflict occurs while Git is combining histories, while a rebase conflict generally occurs while Git is replaying one commit at a time.

## Merge versus rebase

| Property | Merge | Rebase |
|---|---|---|
| Basic mechanism | Combines histories | Replays commits onto another base |
| Existing commit identities | Preserved | Replayed commits normally receive new identities |
| Merge commits | May create them | Normally does not create merge commits for the replayed sequence |
| History shape | Can preserve branch topology | Can produce a more linear history |
| Shared-history risk | Lower from rewriting | Higher when already-published commits are rewritten |
| Conflict location | During merge | During individual commit replay |
| Typical use | Integrating divergent histories | Cleaning or updating unpublished feature history |

Neither operation is simply a substitute for the other. They represent different history transformations.

## When merge is useful

Merge is appropriate when preserving existing history and branch topology is important.

Examples include:

- integrating an independently developed feature
- preserving explicit release integration points
- combining divergent shared branches
- avoiding rewriting commits already consumed by other developers

## When rebase is useful

Rebase can be useful when a developer wants to update a local feature branch onto a newer base or clean up unpublished commits.

Examples include:

- updating a feature branch before review
- organizing a series of local commits
- removing accidental intermediate commits
- creating a linear feature history before integration

The important operational distinction is whether other people already depend on the commits being rewritten.

## Interactive rebase

Interactive rebase allows a developer to manipulate a sequence of commits.

Common actions include:

| Action | Purpose |
|---|---|
| `pick` | Keep the commit |
| `reword` | Keep changes and modify the message |
| `edit` | Pause for manual changes |
| `squash` | Combine with the previous commit and edit messages |
| `fixup` | Combine with the previous commit without retaining its message |
| `drop` | Remove the commit |
| `exec` | Execute a command during the sequence |

A common command is:

    git rebase -i HEAD~5

Interactive rebase is powerful because it rewrites history. It should be used carefully on commits that have already been shared.

## Cherry-pick

Cherry-pick applies the changes introduced by a selected commit to the current branch.

The command is:

    git cherry-pick <commit>

A common use case is moving a specific security or bug fix from one development line to another without merging an entire feature branch.

The Python and JavaScript implementations demonstrate actual cherry-pick operations. The C++ case study models the concept by calculating the difference between a selected commit and its parent before applying that change to another branch.

Cherry-pick can produce conflicts when the target branch does not contain the context expected by the selected change.

## Revert

Revert is different from reset.

The command:

    git revert <commit>

creates a new commit that reverses the effect of the selected commit.

This is particularly useful for shared history because it does not require removing the original commit from the branch's ancestry.

Conceptually:

    A -- B -- C

After reverting C:

    A -- B -- C -- R

R contains changes that reverse C.

The original C remains in history.

## Reset

`git reset` can move a branch reference and, depending on the selected mode, change the index and working tree.

Important modes include:

- `--soft`
- `--mixed`
- `--hard`

`--soft` moves the branch reference while preserving changes in the index and working tree.

`--mixed` also resets the index while preserving working-tree changes.

`--hard` resets the working tree as well and can discard uncommitted changes.

Because reset can be destructive, its use requires a clear understanding of the current state.

## Restore

`git restore` is designed for restoring file content.

For example:

    git restore config.txt

This can discard uncommitted modifications to that path by restoring it from the appropriate Git state.

The Python and JavaScript implementations use `git restore` in a controlled temporary repository.

## Detached HEAD

Detached HEAD occurs when HEAD points directly to a commit rather than a branch.

For example:

    HEAD -> C

instead of:

    HEAD -> main -> C

Detached HEAD is useful for:

- inspecting old releases
- testing historical commits
- comparing behavior
- temporary experiments

If permanent development begins in detached HEAD, create a branch:

    git switch -c experiment

This gives the new work a named reference.

## Remote branches

A remote such as `origin` represents a configured remote repository.

A remote-tracking reference may look like:

    origin/main

It represents the last known state of the remote's `main` branch from the local repository's perspective.

The command:

    git fetch origin

updates remote-tracking references and downloads necessary objects without automatically integrating them into the current branch.

This separation is important.

Fetching is not the same as merging.

## Pull

`git pull` combines fetching with an integration operation.

Depending on configuration and options, the integration can use merge or rebase.

Explicit commands are often easier to reason about:

    git fetch origin
    git merge origin/main

or:

    git fetch origin
    git rebase origin/main

The appropriate choice depends on the repository's history policy.

## Upstream tracking

A local branch can track a remote branch.

For example:

    git push -u origin feature/login

The `-u` option establishes upstream tracking.

This information allows commands such as:

    git status
    git branch -vv

to show relationships between local and remote branches.

## Branch comparison

Several commands are particularly useful for understanding branch relationships.

Current branch:

    git branch --show-current

Branch list:

    git branch -vv

Graph:

    git log --graph --oneline --decorate --all

Differences:

    git diff main..feature/login

Common ancestor:

    git merge-base main feature/login

A commit's history:

    git show <commit>

These commands answer different questions. A useful diagnostic workflow combines them rather than relying on one command.

## Merge base

The **merge base** is a common ancestor used as the basis for a three-way merge.

For two commits A and B:

    git merge-base A B

Git searches the ancestry graph for a suitable common ancestor.

The merge base is important because Git needs to distinguish changes made on each side after their histories diverged.

## Commit reachability

A commit is reachable from a reference when Git can follow parent relationships from that reference to the commit.

For example:

    A -- B -- C
              ^
              main

A, B, and C are all reachable from `main`.

When a branch reference is deleted, commits may become unreachable from ordinary branch references even though recovery can still be possible for some period through reflogs and repository object retention.

## Reflog

The reflog records local reference movements.

The command:

    git reflog

can reveal previous positions of HEAD and other references.

This is useful after:

- accidental resets
- rebases
- branch movement
- mistaken local history changes

The reflog is a local recovery mechanism. It is not a substitute for remote backups.

## Worktrees

Git worktrees allow multiple working directories to use one repository.

A typical command is:

    git worktree add ../release release/2.0

This can be useful when a developer needs to keep one feature checkout available while simultaneously working on another branch.

The Python, JavaScript, and conceptual C++ material treat multiple working states as an advanced branching concern.

## Tags versus branches

A branch is normally a moving reference.

A tag normally identifies a particular historical point.

For example:

    git tag v1.0.0

A later commit can move `main`, but `v1.0.0` is normally intended to continue identifying the release commit.

Tags therefore provide stable release references, while branches provide active development references.

## Python implementation

The Python implementation uses the standard library and invokes a real Git executable through `subprocess`.

The script creates a temporary repository and configures a local Git identity so commits can be created without modifying a user's existing repository configuration.

The implementation demonstrates:

- repository initialization
- branch creation
- branch switching
- branch renaming
- branch deletion
- fast-forward merge
- explicit merge commits
- merge conflicts
- conflict resolution
- rebase
- rebase conflict handling
- detached HEAD
- branch diagnostics
- reflog
- restore
- revert
- cherry-pick
- worktrees
- tags
- integration validation

The repository is temporary, so the demonstrations do not intentionally modify an existing project.

The function `run_command` centralizes process execution and checks command exit codes. The `git` helper then provides a repository-specific interface for executing Git commands.

The Python program uses actual Git behavior rather than pretending that branch operations are ordinary file-copy operations.

## JavaScript implementation

The JavaScript implementation uses Node.js built-in modules:

- `fs` for file operations
- `os` for temporary-directory handling
- `path` for platform-independent paths
- `child_process` for executing Git

The script demonstrates how Git can be automated from an application or build script.

The `spawnSync` function is used to execute Git commands and inspect exit codes. This is particularly important for conflict demonstrations because Git communicates failure or an incomplete integration through its process status.

The JavaScript implementation complements the Python implementation by emphasizing process orchestration, runtime automation, error handling, and integration with a Node.js environment.

## C++ case study

The C++ program models a production-oriented repository for a hypothetical service.

The system contains:

- a repository object
- commit objects
- named branches
- snapshots of tracked files
- merge operations
- rebase operations
- cherry-pick operations
- audit events

The program models a workflow involving:

1. feature development
2. independent main-branch progress
3. three-way merging
4. explicit conflict detection
5. conflict resolution
6. rebasing a feature branch
7. cherry-picking a security fix
8. release branches
9. hotfix integration
10. integration validation
11. audit history

This implementation is intentionally not a replacement for Git. Real Git has a substantially more sophisticated storage layer, index, object database, merge machinery, rename detection, conflict algorithms, hashing, reference management, reflogs, packfiles, configuration, hooks, transport protocols, and filesystem integration.

The C++ implementation isolates the core conceptual model so the relationship between branches and commits can be studied directly.

## C++ data structures

The central `Commit` structure contains:

- an identifier
- zero or more parent IDs
- author
- message
- a file snapshot
- generation information

A normal commit contains one parent.

The initial commit has no parent.

A merge commit contains two parents.

The `Repository` class maintains a map of commits and a map of branch names to commit IDs.

Conceptually:

    branches["main"] = "c0010"

This means the `main` reference points to commit `c0010`.

Creating a new commit changes the branch reference:

    branches[currentBranch] = newCommitId

The branch itself remains a lightweight reference.

## Three-way merge algorithm in the C++ model

The C++ model finds a merge base and compares three snapshots:

- base
- ours
- theirs

For a particular path, the simplified algorithm considers these cases:

1. Both sides have identical content.
2. Only the incoming side changed relative to the base.
3. Only the current side changed relative to the base.
4. Both sides changed the same path differently.

The fourth case is reported as a conflict.

This simplified algorithm is useful for understanding the basic decision structure, but real Git can handle considerably more complicated situations.

## Rebase algorithm in the C++ model

The C++ rebase implementation:

1. Identifies the current branch tip.
2. Identifies the target branch tip.
3. Finds their common ancestor.
4. Collects commits unique to the current branch.
5. Reverses their order into chronological order.
6. Creates new commits whose parent starts at the target branch.
7. Updates the current branch reference to the final recreated commit.

This demonstrates why rebase changes history.

Suppose the original feature chain is:

    A -> B -> C

After rebasing onto D:

    A -> D -> C'

C' is recreated with D as its parent.

The simplified model copies snapshots rather than calculating Git's complete patch application behavior.

## Cherry-pick algorithm

A true Git cherry-pick applies the patch introduced by a selected commit relative to its parent.

The C++ case study models this by comparing the selected commit's snapshot with its parent snapshot and applying the resulting changes to the target branch.

This illustrates why cherry-pick is selective: it transfers the effect of a particular commit rather than integrating an entire branch history.

## Conflict handling in the C++ model

The conflict case study intentionally creates:

Base:

    timeout=30

Feature:

    timeout=60

Main:

    timeout=15

The program detects the conflicting path and reports it.

A resolved snapshot is then explicitly supplied:

    timeout=30
    mode=production

The repository creates a merge commit containing the resolved result.

This mirrors the conceptual Git workflow:

1. detect
2. inspect
3. resolve
4. stage
5. test
6. complete integration

## Complexity considerations

The C++ model uses graph traversal to determine ancestry.

If V is the number of reachable commits and E is the number of parent edges, a basic ancestry traversal is approximately:

    O(V + E)

The simplified merge processes P distinct paths using ordered maps. The approximate cost is:

    O(P log P)

where P is the number of paths considered by the snapshot merge.

Rebase processes C commits that need to be replayed. Its overall cost depends on the cost of processing each commit's changes:

    O(C × cost of replay)

These are educational complexity models for the C++ implementation. They are not complete complexity specifications for Git itself.

## Edge cases

### Uncommitted changes

Switching branches can fail if local changes would be overwritten.

The safe approach is to inspect:

    git status

and decide whether the changes should be committed, stashed, discarded, or otherwise handled.

### Untracked files

An untracked file can also prevent a branch switch if the target branch contains a tracked file at the same path.

### Binary conflicts

Line-based conflict resolution does not work for binary content in the same way it works for text.

A human must determine which binary version or generated artifact should be retained.

### Rename conflicts

A file can be renamed on one branch while being modified or renamed differently on another branch.

These situations can require semantic decisions beyond simply selecting one side.

### File-versus-directory conflicts

One branch may contain a file named `config`, while another contains a directory named `config`.

The resulting filesystem structure cannot contain both in the same form.

### Detached HEAD work

Commits created in detached HEAD can become difficult to locate if no branch or tag references them.

### Rewritten remote history

After rebasing a branch that has already been pushed, updating the remote can require a force push.

When a history rewrite is intentionally required, `git push --force-with-lease` provides an additional check compared with an unconditional force push.

## Common mistakes

### Treating branches as folders

A branch is a reference to a commit, not a separate project directory.

### Merging while on the wrong branch

The target of a normal merge is the current branch.

For example:

    git switch main
    git merge feature/login

means that the changes from `feature/login` are integrated into `main`.

### Rebasing shared history without coordination

Rebase rewrites commits. If other developers already use those commits, rewriting them can cause divergence.

### Ignoring repository status

During conflicts, `git status` explains which paths remain unresolved and whether Git is currently performing a merge or rebase.

### Resolving conflicts mechanically

Choosing "ours" or "theirs" without understanding the application can create a technically valid but behaviorally incorrect result.

### Assuming a successful merge means the software works

Git verifies repository history and content relationships. It does not prove application correctness.

Tests and other validation remain necessary.

## Branching strategies

### Short-lived feature branches

A feature branch isolates a focused change and is integrated relatively quickly.

The primary benefit is reduced long-term divergence.

### Release branches

A release branch provides a stabilization line for a particular release.

It can be useful when release preparation needs to proceed independently of ongoing feature development.

### Hotfix branches

A hotfix branch isolates an urgent correction.

The resulting change may need to be integrated into more than one maintenance line.

### Trunk-based development

Trunk-based development emphasizes frequent integration and short-lived branches.

It can reduce large integration gaps but requires reliable automated testing and disciplined development practices.

### Long-lived development branches

Long-lived branches provide stronger isolation but can accumulate significant divergence.

The longer two histories remain separate, the more work may be required to reconcile them.

## Performance considerations

Branch creation is normally inexpensive because a branch is primarily a reference.

Performance costs can arise from:

- large working trees
- large merges
- extensive rebases
- large numbers of changed files
- conflict-heavy integrations
- object transfer
- repository maintenance
- large histories
- inefficient CI workflows

Frequent integration can reduce the size of individual conflict-resolution operations.

Git's object storage, packfiles, commit graph facilities, index, and repository maintenance mechanisms are important for performance in large repositories.

## Security and integrity

Git's object model uses cryptographic object identifiers. These help detect changes to objects because modifying an object's content changes its identifier.

Git also supports signed commits and signed tags for provenance use cases.

Repository security is broader than object hashing.

Important controls include:

- protected branches
- access control
- least-privilege CI permissions
- review requirements
- secure deployment credentials
- dependency management
- secret management
- signed release artifacts
- controlled release processes

A branch being private should not be treated as a secure secret store.

If a credential is committed, deleting the file in a later commit does not necessarily remove the credential from repository history.

## Production workflow

A disciplined feature workflow can look like:

    git switch main
    git pull
    git switch -c feature/payment-validation

Make focused commits.

Inspect the changes:

    git status
    git diff

Run local tests.

Push the branch:

    git push -u origin feature/payment-validation

Review the changes.

Update the branch against the integration target according to repository policy.

Resolve conflicts if necessary.

Run automated CI.

Integrate through the project's approved merge or rebase process.

Delete the obsolete branch when appropriate.

The exact workflow depends on repository governance and deployment requirements.

## CI and branching

Continuous integration complements Git branching.

A branch isolates a change set. CI validates that change set.

A mature pipeline can check:

- formatting
- linting
- static analysis
- unit tests
- integration tests
- builds
- package generation
- security scanning
- dependency policies
- deployment configuration

A branch can therefore be considered part of a larger software-delivery process rather than merely a Git command.

## Remote collaboration

A practical collaborative workflow often distinguishes three states:

1. Local branch
2. Remote-tracking branch
3. Actual remote branch

For example:

    feature/login
    origin/feature/login
    remote repository's feature/login

`origin/feature/login` is a local reference describing the last fetched state of the remote branch.

`git fetch` updates that information.

`git push` sends local reference updates and necessary objects to the remote.

Understanding this distinction prevents the common misconception that `origin/main` is a live remote object inside the local repository.

## Important distinctions

| Concept | Meaning |
|---|---|
| Branch | Movable named reference |
| Commit | Historical project state plus metadata and parent references |
| HEAD | Current checkout reference |
| Merge | Combines histories |
| Fast-forward | Moves a reference without creating a merge commit |
| Rebase | Recreates commits on a different base |
| Conflict | Git cannot safely determine the combined result |
| Cherry-pick | Applies the effect of selected commit(s) |
| Revert | Creates a new reversing commit |
| Reset | Moves/reset references and potentially index/worktree |
| Restore | Restores file content |
| Reflog | Local record of reference movements |
| Tag | Reference normally used for a fixed historical point |
| Remote-tracking branch | Local record of a remote branch's last fetched state |
| Worktree | Additional working directory associated with one repository |

## What the Python implementation demonstrates

The Python program is the most direct operational demonstration because it executes real Git commands.

Its important examples include:

- creating a temporary repository
- configuring an isolated identity
- creating feature branches
- switching branches
- performing fast-forward merges
- forcing merge commits
- creating and resolving merge conflicts
- rebasing branches
- demonstrating rebase conflicts
- inspecting detached HEAD
- inspecting branch relationships
- using reflog
- restoring files
- reverting commits
- cherry-picking fixes
- using worktrees
- creating tags
- validating the repository state

It also demonstrates how a Python program can automate Git safely through process execution and exit-code checking.

## What the JavaScript implementation demonstrates

The JavaScript program provides a Node.js automation perspective.

It demonstrates:

- synchronous Git process execution
- process exit-code inspection
- temporary repository management
- file manipulation
- branch automation
- merge automation
- conflict detection
- rebase automation
- cherry-pick automation
- worktree operations
- release references
- diagnostic commands

Node.js is particularly useful when Git operations form part of a larger JavaScript-based development, build, deployment, or automation system.

## What the C++ implementation demonstrates

The C++ implementation focuses on the internal conceptual structure.

It demonstrates:

- graph-based commit history
- named branch references
- commit parent relationships
- ancestor traversal
- merge-base discovery
- three-way snapshot merging
- conflict detection
- conflict resolution
- commit recreation during rebase
- selective change transfer through cherry-pick
- release and hotfix flows
- audit events
- integration validation
- complexity analysis
- failure modes

This perspective makes the difference between a branch reference and a commit object explicit.

## Practical command reference

### Branches

    git branch
    git branch <name>
    git switch <name>
    git switch -c <name>
    git branch -m <old> <new>
    git branch -d <name>
    git branch -D <name>

### History

    git log --oneline --graph --decorate --all
    git show <commit>
    git rev-parse HEAD
    git merge-base main feature

### Merge

    git merge <branch>
    git merge --no-ff <branch>
    git merge --abort

### Rebase

    git rebase <base>
    git rebase -i HEAD~5
    git rebase --continue
    git rebase --abort

### Conflict inspection

    git status
    git diff
    git diff --check

### Recovery

    git restore <path>
    git reset
    git revert <commit>
    git reflog

### Selective integration

    git cherry-pick <commit>

### Remote operations

    git remote -v
    git fetch origin
    git pull
    git push
    git push -u origin <branch>

### Advanced repository operations

    git worktree list
    git worktree add <path> <branch>
    git tag <name>
    git bisect start

## Final implementation relationship

The three implementations intentionally operate at different abstraction levels.

Python demonstrates real Git behavior through direct command execution.

JavaScript demonstrates Git as an automatable external process inside a Node.js runtime.

C++ demonstrates the underlying conceptual architecture by representing commits as graph nodes, branches as references, and integration operations as graph and snapshot transformations.

Together, these perspectives distinguish Git's user-facing commands from the data structures and algorithms that make branching, merging, rebasing, conflict detection, and history management possible.
