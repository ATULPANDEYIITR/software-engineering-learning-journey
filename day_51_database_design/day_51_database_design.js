"use strict";

/*
 * Repository governance model.
 * Pull Requests describe proposed changes, reviews evaluate them,
 * approvals represent decisions, and branch protection supplies
 * repository-level merge conditions.
 */

const PRState = Object.freeze({
  DRAFT: "draft",
  OPEN: "open",
  CLOSED: "closed",
  MERGED: "merged",
});

const ReviewState = Object.freeze({
  COMMENTED: "commented",
  APPROVED: "approved",
  CHANGES_REQUESTED: "changes_requested",
  DISMISSED: "dismissed",
});

const MergeStrategy = Object.freeze({
  MERGE: "merge_commit",
  SQUASH: "squash",
  REBASE: "rebase",
});

class GovernanceError extends Error {}

class PullRequest {
  constructor(number, sourceBranch, targetBranch, author, title) {
    if (!Number.isInteger(number) || number <= 0) {
      throw new GovernanceError("Pull Request number must be positive.");
    }

    this.number = number;
    this.sourceBranch = sourceBranch;
    this.targetBranch = targetBranch;
    this.author = author;
    this.title = title;
    this.state = PRState.DRAFT;
    this.commits = [];
    this.reviewers = new Set();
    this.reviews = [];
    this.statusChecks = new Map();
    this.conversations = new Map();
    this.mergeStrategy = null;
  }

  addCommit(sha, message, author) {
    if ([PRState.CLOSED, PRState.MERGED].includes(this.state)) {
      throw new GovernanceError("Cannot modify a closed or merged Pull Request.");
    }

    if (!sha || this.commits.some((commit) => commit.sha === sha)) {
      throw new GovernanceError("Commit SHA must be unique and non-empty.");
    }

    this.commits.push({ sha, message, author });
  }

  requestReview(reviewer) {
    if (!reviewer || reviewer === this.author) {
      throw new GovernanceError("A Pull Request author cannot review their own change.");
    }

    this.reviewers.add(reviewer);
  }

  addReview(reviewer, state, commitSha, comments = []) {
    if (!this.reviewers.has(reviewer)) {
      throw new GovernanceError(`${reviewer} is not a requested reviewer.`);
    }

    if (!this.commits.some((commit) => commit.sha === commitSha)) {
      throw new GovernanceError("Review references an unknown commit.");
    }

    if (!Object.values(ReviewState).includes(state)) {
      throw new GovernanceError("Invalid review state.");
    }

    this.reviews.push({
      reviewer,
      state,
      commitSha,
      comments: [...comments],
    });
  }

  setStatusCheck(name, passed) {
    if (!name) {
      throw new GovernanceError("Status-check name is required.");
    }

    this.statusChecks.set(name, {
      name,
      passed: Boolean(passed),
    });
  }

  addConversation(id, resolved = false) {
    if (!Number.isInteger(id) || id <= 0) {
      throw new GovernanceError("Conversation ID must be positive.");
    }

    this.conversations.set(id, Boolean(resolved));
  }

  open() {
    if (this.state !== PRState.DRAFT) {
      throw new GovernanceError("Only draft Pull Requests can be opened.");
    }
    this.state = PRState.OPEN;
  }

  close() {
    if (this.state === PRState.MERGED) {
      throw new GovernanceError("Merged Pull Requests cannot be closed.");
    }
    this.state = PRState.CLOSED;
  }

  reopen() {
    if (this.state !== PRState.CLOSED) {
      throw new GovernanceError("Only closed Pull Requests can be reopened.");
    }
    this.state = PRState.OPEN;
  }

  get latestCommitSha() {
    return this.commits.at(-1)?.sha ?? null;
  }
}

class BranchProtection {
  constructor({
    branch,
    requiredApprovals = 1,
    requiredChecks = [],
    requireResolvedConversations = true,
    requireLinearHistory = false,
    bypassUsers = [],
  }) {
    if (!branch) throw new GovernanceError("Protected branch is required.");
    if (!Number.isInteger(requiredApprovals) || requiredApprovals < 0) {
      throw new GovernanceError("Required approvals must be a non-negative integer.");
    }

    this.branch = branch;
    this.requiredApprovals = requiredApprovals;
    this.requiredChecks = new Set(requiredChecks);
    this.requireResolvedConversations = requireResolvedConversations;
    this.requireLinearHistory = requireLinearHistory;
    this.bypassUsers = new Set(bypassUsers);
  }
}

class RepositoryPolicyEngine {
  constructor(repositoryName) {
    this.repositoryName = repositoryName;
    this.protections = new Map();
  }

  protect(policy) {
    this.protections.set(policy.branch, policy);
  }

  evaluate(pr) {
    const failures = [];

    if (pr.state !== PRState.OPEN) {
      failures.push(`Pull Request must be open; current state is ${pr.state}.`);
    }

    if (pr.commits.length === 0) {
      failures.push("Pull Request has no commits.");
    }

    const policy = this.protections.get(pr.targetBranch);

    if (!policy) {
      failures.push(`No branch-protection policy exists for ${pr.targetBranch}.`);
      return { eligible: false, failures };
    }

    if (policy.bypassUsers.has(pr.author)) {
      return {
        eligible: true,
        failures: [],
        bypassed: true,
      };
    }

    const latestSha = pr.latestCommitSha;

    const approvedReviewers = new Set(
      pr.reviews
        .filter(
          (review) =>
            review.state === ReviewState.APPROVED &&
            review.commitSha === latestSha &&
            pr.reviewers.has(review.reviewer) &&
            review.reviewer !== pr.author
        )
        .map((review) => review.reviewer)
    );

    if (approvedReviewers.size < policy.requiredApprovals) {
      failures.push(
        `Required approvals: ${policy.requiredApprovals}; ` +
        `current approvals: ${approvedReviewers.size}.`
      );
    }

    for (const checkName of policy.requiredChecks) {
      const check = pr.statusChecks.get(checkName);
      if (!check || !check.passed) {
        failures.push(`Required status check failed or missing: ${checkName}.`);
      }
    }

    if (policy.requireResolvedConversations) {
      const unresolved = [...pr.conversations.entries()]
        .filter(([, resolved]) => !resolved)
        .map(([id]) => id);

      if (unresolved.length > 0) {
        failures.push(
          `Unresolved conversations: ${unresolved.join(", ")}.`
        );
      }
    }

    if (
      policy.requireLinearHistory &&
      pr.mergeStrategy === MergeStrategy.MERGE
    ) {
      failures.push("Merge commits violate the linear-history policy.");
    }

    return {
      eligible: failures.length === 0,
      failures,
      bypassed: false,
    };
  }

  async merge(pr, strategy) {
    await Promise.resolve();

    pr.mergeStrategy = strategy;
    const result = this.evaluate(pr);

    if (!result.eligible) {
      throw new GovernanceError(
        "Merge blocked:\n" + result.failures.map((f) => `- ${f}`).join("\n")
      );
    }

    pr.state = PRState.MERGED;

    return {
      number: pr.number,
      strategy,
      state: pr.state,
    };
  }
}

async function runScenario() {
  const engine = new RepositoryPolicyEngine("orders-service");

  engine.protect(
    new BranchProtection({
      branch: "main",
      requiredApprovals: 2,
      requiredChecks: ["unit-tests", "security-scan"],
      requireResolvedConversations: true,
      requireLinearHistory: true,
    })
  );

  const pr = new PullRequest(
    87,
    "feature/order-validation",
    "main",
    "alice",
    "Validate order boundaries"
  );

  pr.addCommit("c100", "Add order validation", "alice");
  pr.addCommit("c101", "Add validation tests", "alice");
  pr.requestReview("bob");
  pr.requestReview("carol");
  pr.open();

  pr.setStatusCheck("unit-tests", true);
  pr.setStatusCheck("security-scan", true);

  pr.addConversation(10, true);
  pr.addConversation(11, false);

  pr.addReview("bob", ReviewState.APPROVED, "c101");

  console.log("Initial evaluation:");
  console.log(engine.evaluate(pr));

  // A new commit changes the commit context used for current approvals.
  pr.addCommit("c102", "Reject invalid quantities", "alice");
  pr.addConversation(11, true);

  console.log("\nAfter base-branch synchronization:");
  console.log(engine.evaluate(pr));

  pr.addReview("bob", ReviewState.APPROVED, "c102");
  pr.addReview("carol", ReviewState.APPROVED, "c102");

  console.log("\nAfter current approvals:");
  console.log(engine.evaluate(pr));

  try {
    const mergeResult = await engine.merge(pr, MergeStrategy.REBASE);
    console.log("\nMerge result:");
    console.log(mergeResult);
  } catch (error) {
    console.error(error.message);
  }
}

runScenario().catch((error) => {
  console.error("Unexpected governance failure:", error.message);
  process.exitCode = 1;
});
