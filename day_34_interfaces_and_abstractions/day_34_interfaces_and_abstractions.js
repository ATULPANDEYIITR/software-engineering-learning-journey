/**
 * Interfaces & Abstractions
 * Contracts, dependency boundaries
 *
 * Node.js-compatible executable demonstration.
 *
 * JavaScript does not have a built-in interface keyword like TypeScript,
 * so this file demonstrates contracts through:
 *   - documented method contracts
 *   - runtime validation
 *   - dependency injection
 *   - factory-created implementations
 *   - event-driven boundaries
 *   - explicit domain/application/infrastructure separation
 */

"use strict";

// -----------------------------------------------------------------------------
// Contract utilities
// -----------------------------------------------------------------------------

function assertNonEmptyString(value, fieldName) {
  if (typeof value !== "string" || value.trim() === "") {
    throw new TypeError(`${fieldName} must be a non-empty string`);
  }
}

function assertFunction(value, fieldName) {
  if (typeof value !== "function") {
    throw new TypeError(`${fieldName} must be a function`);
  }
}

/**
 * Runtime contract for a notification dependency.
 *
 * JavaScript relies on structural expectations rather than nominal interfaces.
 * The application can accept any object exposing the required send method.
 */
function assertNotificationChannel(channel) {
  if (!channel || typeof channel.send !== "function") {
    throw new TypeError(
      "notification channel must expose send(recipient, subject, body)"
    );
  }
}


// -----------------------------------------------------------------------------
// Concrete implementations behind one abstraction
// -----------------------------------------------------------------------------

class ConsoleNotificationChannel {
  async send(recipient, subject, body) {
    assertNonEmptyString(recipient, "recipient");
    assertNonEmptyString(subject, "subject");
    assertNonEmptyString(body, "body");

    console.log(`[notification] ${recipient} <- ${subject}`);
    console.log(body);

    return {
      provider: "console",
      deliveryId: `console-${Date.now()}`
    };
  }
}

class MemoryNotificationChannel {
  constructor() {
    this.messages = [];
  }

  async send(recipient, subject, body) {
    assertNonEmptyString(recipient, "recipient");
    assertNonEmptyString(subject, "subject");
    assertNonEmptyString(body, "body");

    const message = {
      recipient,
      subject,
      body,
      createdAt: new Date().toISOString()
    };

    this.messages.push(message);

    return {
      provider: "memory",
      deliveryId: `memory-${this.messages.length}`
    };
  }
}


// -----------------------------------------------------------------------------
// Dependency injection
// -----------------------------------------------------------------------------

class NotificationService {
  constructor(channel) {
    assertNotificationChannel(channel);
    this.channel = channel;
  }

  async notifyBuildCompleted(recipient, buildId) {
    assertNonEmptyString(recipient, "recipient");
    assertNonEmptyString(buildId, "buildId");

    return this.channel.send(
      recipient,
      "Build completed",
      `Build ${buildId} passed its validation boundary.`
    );
  }
}


// -----------------------------------------------------------------------------
// Event-driven contract
// -----------------------------------------------------------------------------

class DomainEventBus {
  constructor() {
    this.handlers = new Map();
  }

  subscribe(eventType, handler) {
    assertNonEmptyString(eventType, "eventType");
    assertFunction(handler, "handler");

    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, new Set());
    }

    this.handlers.get(eventType).add(handler);

    // Returning an unsubscribe function keeps the subscription boundary
    // explicit and prevents permanent listeners from accumulating.
    return () => {
      this.handlers.get(eventType)?.delete(handler);
    };
  }

  async publish(eventType, payload) {
    const listeners = this.handlers.get(eventType) ?? [];

    for (const listener of listeners) {
      await listener(payload);
    }
  }
}


// -----------------------------------------------------------------------------
// Domain model
// -----------------------------------------------------------------------------

class PullRequest {
  constructor({
    number,
    repository,
    sourceBranch,
    targetBranch,
    author,
    changedFiles,
    statusChecksPassed
  }) {
    if (!Number.isInteger(number) || number <= 0) {
      throw new TypeError("pull request number must be a positive integer");
    }

    assertNonEmptyString(repository, "repository");
    assertNonEmptyString(sourceBranch, "sourceBranch");
    assertNonEmptyString(targetBranch, "targetBranch");
    assertNonEmptyString(author, "author");

    if (!Array.isArray(changedFiles) || changedFiles.length === 0) {
      throw new TypeError("changedFiles must contain at least one file");
    }

    if (typeof statusChecksPassed !== "boolean") {
      throw new TypeError("statusChecksPassed must be boolean");
    }

    this.number = number;
    this.repository = repository;
    this.sourceBranch = sourceBranch;
    this.targetBranch = targetBranch;
    this.author = author;
    this.changedFiles = [...changedFiles];
    this.statusChecksPassed = statusChecksPassed;
  }
}

class Review {
  constructor({ reviewer, state, comment = "" }) {
    assertNonEmptyString(reviewer, "reviewer");

    const validStates = new Set([
      "APPROVED",
      "CHANGES_REQUESTED",
      "COMMENTED"
    ]);

    if (!validStates.has(state)) {
      throw new TypeError(`unsupported review state: ${state}`);
    }

    this.reviewer = reviewer;
    this.state = state;
    this.comment = comment;
  }
}


// -----------------------------------------------------------------------------
// Review repository contract and implementation
// -----------------------------------------------------------------------------

class MemoryReviewRepository {
  constructor() {
    this.reviews = new Map();
  }

  key(repository, pullRequestNumber) {
    return `${repository}#${pullRequestNumber}`;
  }

  save(repository, pullRequestNumber, review) {
    const key = this.key(repository, pullRequestNumber);

    if (!this.reviews.has(key)) {
      this.reviews.set(key, []);
    }

    this.reviews.get(key).push(review);
  }

  findByPullRequest(repository, pullRequestNumber) {
    return [
      ...(this.reviews.get(this.key(repository, pullRequestNumber)) ?? [])
    ];
  }
}


// -----------------------------------------------------------------------------
// Review policy abstraction
// -----------------------------------------------------------------------------

class ReviewPolicy {
  constructor({
    protectedBranch,
    minimumApprovals,
    requirePassingChecks = true,
    disallowAuthorApproval = true
  }) {
    assertNonEmptyString(protectedBranch, "protectedBranch");

    if (!Number.isInteger(minimumApprovals) || minimumApprovals < 0) {
      throw new TypeError("minimumApprovals must be a non-negative integer");
    }

    this.protectedBranch = protectedBranch;
    this.minimumApprovals = minimumApprovals;
    this.requirePassingChecks = requirePassingChecks;
    this.disallowAuthorApproval = disallowAuthorApproval;
  }
}


// -----------------------------------------------------------------------------
// Policy evaluator
// -----------------------------------------------------------------------------

class MergeEligibilityService {
  constructor(reviewRepository) {
    if (
      !reviewRepository ||
      typeof reviewRepository.findByPullRequest !== "function"
    ) {
      throw new TypeError(
        "review repository must expose findByPullRequest(repository, number)"
      );
    }

    this.reviewRepository = reviewRepository;
  }

  evaluate(pullRequest, policy) {
    const failures = [];

    if (pullRequest.targetBranch !== policy.protectedBranch) {
      failures.push("pull request targets a branch outside this policy");
    }

    if (
      policy.requirePassingChecks &&
      !pullRequest.statusChecksPassed
    ) {
      failures.push("required status checks are not passing");
    }

    const reviews = this.reviewRepository.findByPullRequest(
      pullRequest.repository,
      pullRequest.number
    );

    const approvals = new Set();

    for (const review of reviews) {
      if (review.state !== "APPROVED") {
        continue;
      }

      if (
        policy.disallowAuthorApproval &&
        review.reviewer === pullRequest.author
      ) {
        continue;
      }

      approvals.add(review.reviewer);
    }

    if (approvals.size < policy.minimumApprovals) {
      failures.push(
        `requires ${policy.minimumApprovals} approval(s), found ${approvals.size}`
      );
    }

    return {
      allowed: failures.length === 0,
      failures,
      approvals: [...approvals]
    };
  }
}


// -----------------------------------------------------------------------------
// Application service
// -----------------------------------------------------------------------------

class PullRequestMergeController {
  constructor({
    eligibilityService,
    eventBus,
    clock = () => new Date()
  }) {
    if (
      !eligibilityService ||
      typeof eligibilityService.evaluate !== "function"
    ) {
      throw new TypeError("eligibilityService has an invalid contract");
    }

    if (!eventBus || typeof eventBus.publish !== "function") {
      throw new TypeError("eventBus has an invalid contract");
    }

    assertFunction(clock, "clock");

    this.eligibilityService = eligibilityService;
    this.eventBus = eventBus;
    this.clock = clock;
  }

  async evaluate(pullRequest, policy, actor) {
    assertNonEmptyString(actor, "actor");

    const result = this.eligibilityService.evaluate(
      pullRequest,
      policy
    );

    const decision = {
      pullRequest: pullRequest.number,
      repository: pullRequest.repository,
      allowed: result.allowed,
      failures: result.failures,
      approvals: result.approvals,
      evaluatedAt: this.clock().toISOString(),
      evaluatedBy: actor
    };

    await this.eventBus.publish("merge.evaluated", decision);

    return decision;
  }
}


// -----------------------------------------------------------------------------
// Transport boundary
// -----------------------------------------------------------------------------

function serializeDecision(decision) {
  return JSON.stringify(
    {
      pullRequest: decision.pullRequest,
      repository: decision.repository,
      mergeAllowed: decision.allowed,
      blockers: decision.failures,
      approvals: decision.approvals,
      evaluatedAt: decision.evaluatedAt
    },
    null,
    2
  );
}


// -----------------------------------------------------------------------------
// Contract checks
// -----------------------------------------------------------------------------

async function runContractTests() {
  const reviewRepository = new MemoryReviewRepository();

  const pullRequest = new PullRequest({
    number: 42,
    repository: "release-control",
    sourceBranch: "feature/dependency-boundary",
    targetBranch: "main",
    author: "developer",
    changedFiles: [
      "domain/policy.js",
      "application/merge-controller.js"
    ],
    statusChecksPassed: true
  });

  reviewRepository.save(
    pullRequest.repository,
    pullRequest.number,
    new Review({
      reviewer: "security-reviewer",
      state: "APPROVED",
      comment: "Boundary validation reviewed."
    })
  );

  reviewRepository.save(
    pullRequest.repository,
    pullRequest.number,
    new Review({
      reviewer: "platform-reviewer",
      state: "APPROVED",
      comment: "Infrastructure remains outside the domain."
    })
  );

  reviewRepository.save(
    pullRequest.repository,
    pullRequest.number,
    new Review({
      reviewer: "developer",
      state: "APPROVED",
      comment: "Self approval should not count."
    })
  );

  const policy = new ReviewPolicy({
    protectedBranch: "main",
    minimumApprovals: 2,
    requirePassingChecks: true,
    disallowAuthorApproval: true
  });

  const eventBus = new DomainEventBus();
  const emittedEvents = [];

  eventBus.subscribe("merge.evaluated", event => {
    emittedEvents.push(event);
  });

  const controller = new PullRequestMergeController({
    eligibilityService: new MergeEligibilityService(reviewRepository),
    eventBus,
    clock: () => new Date("2026-10-04T12:00:00.000Z")
  });

  const decision = await controller.evaluate(
    pullRequest,
    policy,
    "merge-controller"
  );

  if (!decision.allowed) {
    throw new Error("valid dependency-boundary scenario was rejected");
  }

  if (decision.approvals.length !== 2) {
    throw new Error("author approval incorrectly counted");
  }

  if (emittedEvents.length !== 1) {
    throw new Error("merge evaluation event was not emitted");
  }

  // A failed status check demonstrates that the policy boundary is enforced
  // without modifying the domain object or the review repository.
  const failingPullRequest = new PullRequest({
    number: 43,
    repository: "release-control",
    sourceBranch: "feature/failed-check",
    targetBranch: "main",
    author: "developer",
    changedFiles: ["policy.js"],
    statusChecksPassed: false
  });

  reviewRepository.save(
    failingPullRequest.repository,
    failingPullRequest.number,
    new Review({
      reviewer: "security-reviewer",
      state: "APPROVED"
    })
  );

  reviewRepository.save(
    failingPullRequest.repository,
    failingPullRequest.number,
    new Review({
      reviewer: "platform-reviewer",
      state: "APPROVED"
    })
  );

  const failedDecision = await controller.evaluate(
    failingPullRequest,
    policy,
    "merge-controller"
  );

  if (failedDecision.allowed) {
    throw new Error("failed status checks incorrectly allowed a merge");
  }

  if (
    !failedDecision.failures.includes(
      "required status checks are not passing"
    )
  ) {
    throw new Error("status-check failure was not reported");
  }

  console.log("Contract tests passed.");
}


// -----------------------------------------------------------------------------
// Demonstration of implementation substitution
// -----------------------------------------------------------------------------

async function main() {
  console.log("INTERFACES AND ABSTRACTIONS");
  console.log("===========================");

  // The service depends on the notification contract, not on console output.
  const consoleService = new NotificationService(
    new ConsoleNotificationChannel()
  );

  await consoleService.notifyBuildCompleted(
    "developer@example.com",
    "build-1842"
  );

  // Replacing the concrete dependency requires no change to the service.
  const memoryChannel = new MemoryNotificationChannel();
  const testService = new NotificationService(memoryChannel);

  const delivery = await testService.notifyBuildCompleted(
    "test@example.com",
    "build-test"
  );

  console.log("in-memory delivery:", delivery);
  console.log("stored messages:", memoryChannel.messages.length);

  await runContractTests();

  console.log("\nSerialized decision example:");
  const repository = new MemoryReviewRepository();

  const pr = new PullRequest({
    number: 99,
    repository: "contract-platform",
    sourceBranch: "feature/api-boundary",
    targetBranch: "main",
    author: "engineer",
    changedFiles: ["domain.js", "application.js"],
    statusChecksPassed: true
  });

  repository.save(
    pr.repository,
    pr.number,
    new Review({
      reviewer: "reviewer-one",
      state: "APPROVED"
    })
  );

  const evaluator = new MergeEligibilityService(repository);
  const policy = new ReviewPolicy({
    protectedBranch: "main",
    minimumApprovals: 1
  });

  const eventBus = new DomainEventBus();
  const controller = new PullRequestMergeController({
    eligibilityService: evaluator,
    eventBus
  });

  const decision = await controller.evaluate(
    pr,
    policy,
    "release-controller"
  );

  console.log(serializeDecision(decision));
}

main().catch(error => {
  console.error("Execution failed:", error.message);
  process.exitCode = 1;
});
