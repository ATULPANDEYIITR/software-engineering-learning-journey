"use strict";

/*
 * Node.js 18+.
 * This model focuses on CRUD-oriented data manipulation while using a
 * repository-governance scenario to make SELECT-like retrieval, INSERT-like
 * creation, UPDATE-like state changes, and DELETE-like cleanup explicit.
 */

class ValidationError extends Error {
  constructor(message) {
    super(message);
    this.name = "ValidationError";
  }
}

class RepositoryStore {
  constructor() {
    this.repositories = new Map();
    this.pullRequests = new Map();
    this.reviews = new Map();
    this.statusChecks = new Map();
    this.nextRepositoryId = 1;
    this.nextPullRequestId = 1;
  }

  async insertRepository(name) {
    return this.#delay(() => {
      if (typeof name !== "string" || !name.trim()) {
        throw new ValidationError("Repository name is required.");
      }

      const repository = {
        id: this.nextRepositoryId++,
        name: name.trim(),
        createdAt: new Date().toISOString(),
      };

      this.repositories.set(repository.id, repository);
      return { ...repository };
    });
  }

  async insertPullRequest(repositoryId, input) {
    return this.#delay(() => {
      if (!this.repositories.has(repositoryId)) {
        throw new ValidationError("Repository does not exist.");
      }

      const { title, sourceBranch, targetBranch, author, draft = false } = input;

      if (!title?.trim() || !sourceBranch?.trim() || !targetBranch?.trim()) {
        throw new ValidationError("Title and branch names are required.");
      }

      if (sourceBranch === targetBranch) {
        throw new ValidationError("Source and target branches must differ.");
      }

      const pullRequest = {
        id: this.nextPullRequestId++,
        repositoryId,
        title: title.trim(),
        sourceBranch: sourceBranch.trim(),
        targetBranch: targetBranch.trim(),
        author: author?.trim() || "unknown",
        draft: Boolean(draft),
        state: "OPEN",
        createdAt: new Date().toISOString(),
      };

      this.pullRequests.set(pullRequest.id, pullRequest);
      this.reviews.set(pullRequest.id, []);
      this.statusChecks.set(pullRequest.id, new Map());

      return { ...pullRequest };
    });
  }

  async selectPullRequests(filter = {}) {
    return this.#delay(() => {
      const results = [...this.pullRequests.values()].filter((pr) => {
        if (
          filter.repositoryId !== undefined &&
          pr.repositoryId !== filter.repositoryId
        ) {
          return false;
        }

        if (filter.state !== undefined && pr.state !== filter.state) {
          return false;
        }

        if (
          filter.targetBranch !== undefined &&
          pr.targetBranch !== filter.targetBranch
        ) {
          return false;
        }

        return true;
      });

      return results.map((pr) => ({ ...pr }));
    });
  }

  async updatePullRequest(id, changes) {
    return this.#delay(() => {
      const current = this.pullRequests.get(id);

      if (!current) {
        throw new ValidationError("Pull request does not exist.");
      }

      if (changes.state !== undefined) {
        if (!["OPEN", "CLOSED", "MERGED"].includes(changes.state)) {
          throw new ValidationError("Invalid pull request state.");
        }

        if (current.state === "MERGED" && changes.state !== "MERGED") {
          throw new ValidationError("Merged pull requests cannot be reopened.");
        }
      }

      if (
        changes.title !== undefined &&
        (!String(changes.title).trim() || String(changes.title).length > 200)
      ) {
        throw new ValidationError("Title must contain 1-200 characters.");
      }

      Object.assign(current, {
        ...changes,
        title:
          changes.title === undefined
            ? current.title
            : String(changes.title).trim(),
      });

      return { ...current };
    });
  }

  async insertReview(pullRequestId, reviewer, state, comment = "") {
    return this.#delay(() => {
      const pr = this.pullRequests.get(pullRequestId);

      if (!pr) {
        throw new ValidationError("Pull request does not exist.");
      }

      if (reviewer === pr.author) {
        throw new ValidationError("Authors cannot approve their own changes.");
      }

      if (!["APPROVED", "CHANGES_REQUESTED", "COMMENTED"].includes(state)) {
        throw new ValidationError("Invalid review state.");
      }

      const reviews = this.reviews.get(pullRequestId);
      const review = {
        reviewer,
        state,
        comment: String(comment).trim(),
        submittedAt: new Date().toISOString(),
      };

      reviews.push(review);
      return { ...review };
    });
  }

  async updateStatusCheck(pullRequestId, checkName, state) {
    return this.#delay(() => {
      if (!this.pullRequests.has(pullRequestId)) {
        throw new ValidationError("Pull request does not exist.");
      }

      if (!["PASSING", "FAILING", "PENDING"].includes(state)) {
        throw new ValidationError("Invalid status-check state.");
      }

      const checks = this.statusChecks.get(pullRequestId);
      checks.set(checkName, state);

      return { checkName, state };
    });
  }

  async deletePullRequest(id) {
    return this.#delay(() => {
      const pr = this.pullRequests.get(id);

      if (!pr) {
        return false;
      }

      if (pr.state === "MERGED") {
        throw new ValidationError("Merged history must not be deleted.");
      }

      this.pullRequests.delete(id);
      this.reviews.delete(id);
      this.statusChecks.delete(id);
      return true;
    });
  }

  async evaluateMerge(id, policy) {
    return this.#delay(() => {
      const pr = this.pullRequests.get(id);

      if (!pr) {
        throw new ValidationError("Pull request does not exist.");
      }

      const reasons = [];

      if (pr.state !== "OPEN") {
        reasons.push("Pull request is not open.");
      }

      if (pr.draft) {
        reasons.push("Draft pull requests cannot be merged.");
      }

      const approvals = new Set(
        this.reviews
          .get(id)
          .filter((review) => review.state === "APPROVED")
          .map((review) => review.reviewer)
      );

      if (approvals.size < policy.requiredApprovals) {
        reasons.push(
          `${policy.requiredApprovals} approval(s) required; ${approvals.size} available.`
        );
      }

      const checks = this.statusChecks.get(id);
      for (const requiredCheck of policy.requiredChecks) {
        if (checks.get(requiredCheck) !== "PASSING") {
          reasons.push(`Required check '${requiredCheck}' is not passing.`);
        }
      }

      return {
        eligible: reasons.length === 0,
        reasons,
      };
    });
  }

  #delay(operation) {
    return new Promise((resolve, reject) => {
      queueMicrotask(() => {
        try {
          resolve(operation());
        } catch (error) {
          reject(error);
        }
      });
    });
  }
}

async function main() {
  const store = new RepositoryStore();

  try {
    // INSERT
    const repository = await store.insertRepository(
      "sql-crud-governance"
    );

    const pullRequest = await store.insertPullRequest(repository.id, {
      title: "Implement CRUD examples",
      sourceBranch: "feature/sql-crud",
      targetBranch: "main",
      author: "developer",
    });

    // UPDATE
    await store.updatePullRequest(pullRequest.id, {
      title: "Implement safe CRUD examples",
    });

    // INSERT review records
    await store.insertReview(
      pullRequest.id,
      "alice",
      "APPROVED",
      "Constraints are appropriate."
    );

    await store.insertReview(
      pullRequest.id,
      "bob",
      "APPROVED",
      "Transaction behavior is clear."
    );

    await store.updateStatusCheck(
      pullRequest.id,
      "unit-tests",
      "PASSING"
    );

    await store.updateStatusCheck(
      pullRequest.id,
      "sql-validation",
      "PASSING"
    );

    // SELECT
    const openPullRequests = await store.selectPullRequests({
      repositoryId: repository.id,
      state: "OPEN",
      targetBranch: "main",
    });

    console.log("Open pull requests:");
    console.table(openPullRequests);

    const decision = await store.evaluateMerge(pullRequest.id, {
      requiredApprovals: 2,
      requiredChecks: ["unit-tests", "sql-validation"],
    });

    console.log("Merge eligibility:", decision);

    // UPDATE
    if (decision.eligible) {
      await store.updatePullRequest(pullRequest.id, {
        state: "MERGED",
      });
    }

    // DELETE is intentionally restricted for merged history.
    try {
      await store.deletePullRequest(pullRequest.id);
    } catch (error) {
      console.log(`Delete rejected: ${error.message}`);
    }

    const finalRecord = await store.selectPullRequests({
      repositoryId: repository.id,
    });

    console.log("Final records:");
    console.table(finalRecord);
  } catch (error) {
    if (error instanceof ValidationError) {
      console.error(`Validation failure: ${error.message}`);
    } else {
      console.error("Unexpected failure:", error);
    }
  }
}

main();
